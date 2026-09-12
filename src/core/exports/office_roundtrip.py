"""Office 往返编辑会话（Task 12.1，v5 P3 体验顺滑 / D3 落地）。

流程：条款 → 导出临时 docx → 用户本机 Word/WPS 编辑（os.startfile 拉起）→
轮询 mtime+内容哈希（兼容 WPS 保存差异）→ 白名单解析（段落文本/表格行列增删/单元格合并）
→ 差异预览确认 → 走既有补丁 API 落库（PATCHABLE_FIELDS 已覆盖，零 schema 变更）。

红线（P1 裁决）：越界内容（图片/样式/公式对象/文本框）→ 拒绝落库并明示用户改用快速小改。
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from src.core.storage.clause_repo import fetch_full_clause
from src.core.storage.sqlite_db import get_db_connection

_EDIT_DIR_NAME = "edit_sessions"
_locks: dict[str, threading.Lock] = {}


def _edit_dir() -> Path:
    d = get_settings().data_dir / _EDIT_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class EditSession:
    session_id: str
    clause_revision_id: str
    docx_path: Path
    last_mtime: float = 0.0
    last_hash: str = ""
    proposed: dict | None = None      # {field_name, patched_value} 白名单解析结果
    rejected_reason: str | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"session_id": self.session_id,
                "clause_revision_id": self.clause_revision_id,
                "docx_path": str(self.docx_path),
                "has_changes": self.proposed is not None,
                "rejected_reason": self.rejected_reason,
                "proposed": self.proposed}


_sessions: dict[str, EditSession] = {}


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _docx_content_to_text(docx_path: Path) -> tuple[str, list[str]]:
    """docx → (正文纯文本, 表格管道行)。表格并入正文（与 table_md 同源）。"""
    from docx import Document
    doc = Document(str(docx_path))
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    tables: list[str] = []
    for t in doc.tables:
        for row in t.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            tables.append(" | ".join(cells))
    body = "\n".join(paras)
    if tables:
        body += "\n" + "\n".join(tables)
    return body, tables


def _contains_disallowed(docx_path: Path) -> str | None:
    """越界检测：图片/形状/公式对象（简单探测：drawing 元素）。"""
    import zipfile
    from xml.etree import ElementTree
    try:
        with zipfile.ZipFile(str(docx_path)) as z:
            names = z.namelist()
            # 图片部件
            imgs = [n for n in names if n.startswith("word/media/")]
            if imgs:
                return f"检测到 {len(imgs)} 张图片/对象（仅支持文字与表格编辑）"
            # 文本框/形状
            if any(n.endswith("drawing.xml") or "txbxContent" in n for n in names):
                return "检测到文本框/形状（仅支持文字与表格编辑）"
    except Exception:
        return None
    return None


def _launch_office(docx_path: Path, rect: dict | None = None) -> None:
    """拉起本机 Word/WPS 打开临时文档（系统文件关联；WPS 装了会优先用它）。
    模块级函数便于测试 monkeypatch（测试环境不真正打开 Office）。

    rect: 可选 {left, top, width, height}（屏幕坐标，来自前端聊天框位置）。
    窗口就绪后调整到该矩形并置前（前台）——避免 WPS 在后台打开或窗口太大。
    """
    try:
        import os
        os.startfile(str(docx_path))  # Windows only
        if rect:
            _resize_and_foreground(docx_path, rect)
    except Exception:
        pass  # 无关联程序/非 Windows：会话仍登记，前端提示用户手动打开


def _resize_and_foreground(docx_path: Path, rect: dict) -> None:
    """后台线程轮询（最长 ~8s）找到打开了该 docx 的 WPS/Word 主窗口：
    MoveWindow 到 rect + SetForegroundWindow 置前。失败静默（不影响编辑流程）。"""

    def _work():
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            title_hint = docx_path.name.lower()
            deadline = time.time() + 8.0

            def find_hwnd():
                found = []

                @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                def cb(hwnd, lparam):
                    if not user32.IsWindowVisible(hwnd):
                        return True
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length <= 0:
                        return True
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if title_hint in buf.value.lower():
                        found.append(hwnd)
                    return True

                user32.EnumWindows(cb, 0)
                return found[0] if found else None

            hwnd = None
            while time.time() < deadline:
                hwnd = find_hwnd()
                if hwnd:
                    break
                time.sleep(0.5)

            if not hwnd:
                return
            left = max(0, int(rect.get("left", 0)))
            top = max(0, int(rect.get("top", 0)))
            width = max(320, int(rect.get("width", 640)))
            height = max(240, int(rect.get("height", 480)))
            # 恢复非最大化状态再 MoveWindow（避免 WPS 记住上次最大化尺寸）
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.MoveWindow(hwnd, left, top, width, height, True)
            _force_foreground(user32, hwnd)
        except Exception:
            pass

    threading.Thread(target=_work, daemon=True).start()


def _force_foreground(user32, hwnd) -> None:
    """强制窗口到前台。Windows 前台锁定（Foreground Lock）会拒绝后台进程的
    SetForegroundWindow——第一次 WPS 冷启动能成功、再次唤起被浏览器挡住就是它。
    组合拳绕过：AttachThreadInput（正确传 LPDWORD）+ TOPMOST→NOTTOPMOST 翻转 + ALT 键模拟。"""
    import ctypes
    from ctypes import wintypes
    this_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    # GetWindowThreadProcessId 第二参是 LPDWORD（ctypes 传 None 需显式类型）
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    fg_hwnd = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

    # 1) AttachThreadInput：把本线程与前台线程/目标窗口线程挂到同一输入队列，共享前台权限
    attached = []
    try:
        if fg_tid and fg_tid != this_tid:
            if user32.AttachThreadInput(this_tid, fg_tid, True):
                attached.append((this_tid, fg_tid))
        if target_tid and target_tid != this_tid:
            if user32.AttachThreadInput(this_tid, target_tid, True):
                attached.append((this_tid, target_tid))
    except Exception:
        pass
    # 2) TOPMOST→NOTTOPMOST 翻转：把窗口顶到 Z 序最上
    try:
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)   # HWND_TOPMOST
        user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)   # HWND_NOTOPMOST
        user32.BringWindowToTop(hwnd)
    except Exception:
        pass
    # 3) ALT 键模拟：让系统认为有用户输入参与，解除前台锁
    try:
        user32.keybd_event(0x12, 0, 0, 0)          # ALT down
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(0x12, 0, 2, 0)          # ALT up
    except Exception:
        pass
    user32.SetForegroundWindow(hwnd)
    # 解除输入队列挂接
    for a, b in reversed(attached):
        try:
            user32.AttachThreadInput(a, b, False)
        except Exception:
            pass
    # 4) 兜底：SwitchToThisWindow（未公开 API，直接切换）
    try:
        user32.SwitchToThisWindow(hwnd, True)
    except Exception:
        pass


def create_edit_session(clause_revision_id: str, rect: dict | None = None) -> EditSession:
    """导出条款为临时 docx 并登记会话。rect: 可选窗口定位 {left,top,width,height}。"""
    conn = get_db_connection()
    clause = fetch_full_clause(conn, clause_revision_id)
    if clause is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError(f"条款不存在: {clause_revision_id}", code="clause_not_found")

    from docx import Document
    doc = Document()
    from src.core.text_utils import html_unescape, clean_eq_tags
    heading = html_unescape(clean_eq_tags(f"{clause.standard_no} {clause.clause_number}"))
    doc.add_heading(heading, level=1)
    # 2026-09-01 退役 normalize_wraps（排版需求反转）：行界=原文真实折行，
    # WPS 导出按原文行界逐段输出（旧「拼接去回车」是假行界时代补丁，
    # 对存量幂等无影响——存量入库时已洗平，splitlines 段落形态不变）
    for line in html_unescape(clean_eq_tags(clause.content_text)).splitlines():
        doc.add_paragraph(line)
    if clause.content_markdown and "<table>" in clause.content_markdown:
        import re as _re
        from src.core.text_utils import strip_tags, clean_eq_tags
        rows = _re.findall(r"<tr>(.*?)</tr>", clean_eq_tags(clause.content_markdown), _re.S)
        parsed: list[list[str]] = []
        max_cols = 1
        for row in rows:
            # strip_tags 内含 HTML 实体解码（&lt; → < 等，修复 WPS 显示字面 &lt;）
            cells = [strip_tags(c) for c in _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, _re.S)]
            parsed.append(cells)
            max_cols = max(max_cols, len(cells))
        if parsed:
            table = doc.add_table(rows=len(parsed), cols=max_cols)
            table.style = "Table Grid"
            for i, cells in enumerate(parsed):
                for j in range(max_cols):
                    table.cell(i, j).text = cells[j] if j < len(cells) else ""

    sid = f"es_{ULID()}"
    docx_path = _edit_dir() / f"{sid}.docx"
    doc.save(str(docx_path))
    sess = EditSession(session_id=sid, clause_revision_id=clause_revision_id,
                       docx_path=docx_path, last_mtime=0.0, last_hash=_file_hash(docx_path))
    _sessions[sid] = sess
    # 拉起本机 Word/WPS 打开临时文档（系统文件关联；WPS 装了会优先用它）
    _launch_office(docx_path, rect)
    return sess


def poll_edit_session(session_id: str) -> EditSession:
    """轮询保存：mtime/哈希变化 → 白名单解析 → proposed/rejected。"""
    sess = _sessions.get(session_id)
    if sess is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError(f"会话不存在: {session_id}", code="session_not_found")
    if not sess.docx_path.exists():
        return sess
    mtime = sess.docx_path.stat().st_mtime
    if mtime == sess.last_mtime:
        return sess
    sess.last_mtime = mtime
    new_hash = _file_hash(sess.docx_path)
    if new_hash == sess.last_hash:
        return sess
    sess.last_hash = new_hash

    # 越界检测
    reason = _contains_disallowed(sess.docx_path)
    if reason:
        sess.proposed = None
        sess.rejected_reason = reason
        return sess

    # 白名单解析：正文+表格 与 原条款比对
    conn = get_db_connection()
    clause = fetch_full_clause(conn, sess.clause_revision_id)
    body, tables = _docx_content_to_text(sess.docx_path)
    body_flat = body.replace("\n", "").replace(" ", "")
    orig = (clause.content_text or "").replace("\n", "").replace(" ", "")
    if body_flat == orig and not tables:
        sess.proposed = None
        sess.rejected_reason = None
        return sess
    # 表格管道行 → 简易表格 html
    md = None
    if tables:
        rows_html = []
        for line in tables:
            cells = [c.strip() for c in line.split("|")]
            rows_html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        md = "<table>" + "".join(rows_html) + "</table>"
    # proposed 双字段：text=正文段落纯文本、table_html=表格 html（供前端回填编辑器；
    # 保存仍走编辑器的补丁通道——复杂编辑只是"填入简易编辑器"，不直接落库）
    sess.proposed = {"text": body, "table_html": md}
    sess.rejected_reason = None
    return sess


def commit_edit_session(session_id: str) -> dict:
    """确认落库（兼容保留；现行前端流程 = WPS 内容回填编辑器后由用户在编辑器保存）。
    将 proposed 的正文/表格分别落 content_text / content_markdown 补丁。"""
    sess = poll_edit_session(session_id)
    if sess.proposed is None:
        from src.core.exceptions import KnowledgeStationError
        reason = sess.rejected_reason or "无可提交变更（内容未变或仅格式调整）"
        raise KnowledgeStationError(reason, code="office_no_change")
    from src.core.storage import clause_repo
    out = clause_repo.upsert_patch(
        sess.clause_revision_id, "content_text",
        sess.proposed.get("text", ""), patch_reason="office-roundtrip")
    if sess.proposed.get("table_html"):
        clause_repo.upsert_patch(
            sess.clause_revision_id, "content_markdown",
            sess.proposed["table_html"], patch_reason="office-roundtrip(表格)")
    _sessions.pop(session_id, None)
    try:
        sess.docx_path.unlink(missing_ok=True)
    except Exception:
        pass
    return out


def cancel_edit_session(session_id: str) -> bool:
    sess = _sessions.pop(session_id, None)
    if sess is None:
        return False
    try:
        sess.docx_path.unlink(missing_ok=True)
    except Exception:
        pass
    return True
