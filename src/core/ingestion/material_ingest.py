# -*- coding: utf-8 -*-
"""材料解析与切片（2026-09-17 定位转移 Phase A 第二步）。

## 它做什么
把"放进项目参考资料文件夹"的文件解析成**带字符区间与页号的切片**，登记进材料平面
（**默认 `pending`** —— 未评审不得使用，硬门在 `material_repo.approved_materials()`）。

## 与法条入库的根本区别（**不要复用条款切分**）
法规入库要按**条款号**切成三型知识单元（`split_items_into_clauses`），因为要逐条取证；
**材料不是条文**（财报、公告、帖子、研报），硬套条款切分只会切出一堆碎片且丢掉上下文。
故这里按**段落**聚合成块，只保留"能指回原文位置"的最小契约：`char_start/char_end/page`。

## 默认不外发
PDF 解析走 `run_parser_isolated(..., deep_fallback=False)` —— **无文本层就不解析**，
如实报 `text_layer_state`，绝不因为"用户只是丢了个文件进来"就把它传上去。需要云深度解析
时必须**显式**传 `deep_fallback=True`（与 D5 的口径一致：默认安全、可显式开启、如实标注）。

## 存储
材料原件放 `<data_dir>/materials/<project_id>/`（按项目分目录，与法规语料分开）。
文件若已在项目目录内则**原地引用**；在外面的会**复制进来**，保证材料平面自包含。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.storage import material_repo as mr
from src.core.text_utils import strip_duplicate_suffix

#: 支持的收件后缀。**故意保守**：只收能拿到纯文本的格式；暂不收图片（要走 OCR 另议）。
SUPPORTED_SUFFIXES = (".pdf", ".docx", ".txt", ".md")

#: 单块目标字数（超长段落会被硬切）。材料检索不像法条那样逐条取证，块大一点上下文更完整。
DEFAULT_MAX_CHARS = 900


def scan_project_dir(project_id: str) -> list[Path]:
    """列出项目参考资料文件夹里受支持的文件（按名排序，结果稳定）。"""
    d = mr.materials_dir(project_id)
    out = [p for p in sorted(d.iterdir())
           if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES]
    return out


# ------------------------------------------------------------------ 解析（页 → 文本）
def extract_pages(path: Path, *, deep_fallback: bool = False,
                  work_dir: Path | None = None) -> list[tuple[int, str]]:
    """解析成 `[(page_number, page_text)]`。

    - PDF：走既有解析器（子进程隔离），按 `page_number` 聚合 blocks；**默认不外发**
      （`deep_fallback=False`：无文本层就如实返回空文本，不偷偷上云）；
    - DOCX：用 python-docx 取段落，**整体算第 1 页**（docx 本身没有页的概念——
      不要假装有页号，那是编造）；
    - TXT/MD：整体第 1 页。
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from src.core.ingestion.parser_worker import run_parser_isolated
        out_dir = (work_dir or (get_settings().data_dir / "material_tmp")) / _short_hash(path)
        result = run_parser_isolated(path, out_dir, force_deep=False,
                                     deep_fallback=deep_fallback)
        blocks = result.get("blocks") or []
        by_page: dict[int, list[str]] = {}
        for b in blocks:
            page = int(b.get("page_number") or 1)
            text = (b.get("text") or "").strip()
            if text:
                by_page.setdefault(page, []).append(text)
        return [(p, "\n".join(by_page[p])) for p in sorted(by_page)]

    if suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return [(1, "\n".join(paras))] if paras else []

    # txt / md：按 utf-8 读，容错替换（bad bytes 不该让整份材料消失）
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(1, text)] if text.strip() else []


def _short_hash(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]


def file_hash(path: Path) -> str:
    """文件内容 SHA-256（用于查重：同一份材料重复放进来不应重复登记）。"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ 切片
def build_document(pages: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int, int]]]:
    """把 `[(page, text)]` 拼成**规范全文**，并给出每页在全文中的字符区间。

    返回 `(text, [(page_start, page_end, page_number)])`。页与页之间用 `"\n\n"` 连接
    （切块时它也是天然的段落边界）。**这些偏移量是"引用可点回原文位置"的唯一依据**，
    所以必须与 `text` 严格自洽（有测试逐块回验 `text[start:end]`）。
    """
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for i, (page, ptext) in enumerate(pages):
        if i:
            parts.append("\n\n")
            cursor += 2
        parts.append(ptext)
        spans.append((cursor, cursor + len(ptext), page))
        cursor += len(ptext)
    return "".join(parts), spans


def page_of(offset: int, spans: list[tuple[int, int, int]]) -> int | None:
    """字符偏移 → 页号。

    ⚠ 精确契约（2026-09-17 被 verifier 抓过：旧 docstring 写的是"归上一页"，与代码**不符**）：
    - 偏移**落在某页区间内** → 该页页号；
    - 偏移落在**页间连接符上**（空白，不属于任何页区间）→ 返回**最后一页**的页号，而不是上一页；
    - `spans` 为空 → `None`。

    **为什么没影响**：切片起点经 `emit()` 收紧到非空白字符上，永远不会落在页间分隔符里。
    docstring 改准是为了下一个人别照着错契约推行为（无行为变更）。
    """
    for start, end, page in spans:
        if start <= offset < end:
            return page
    return spans[-1][2] if spans else None


def _require_positive_max_chars(max_chars: int) -> None:
    """`max_chars` 的**唯一**校验点（参数规则的单一所有者）。

    `max_chars <= 0` 会让硬切循环的指针不前进（`seg_end == off`）⇒ **死循环**。
    两个公开入口（`chunk_text` / `ingest_material_file`）都调本函数，
    避免"空文本早退就不校验"这种**同一参数两种命运**的漏洞。
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError(f"max_chars 必须是 >= 1 的整数（收到 {max_chars!r}）")


def chunk_text(text: str, spans: list[tuple[int, int, int]],
               *, max_chars: int = DEFAULT_MAX_CHARS) -> list[dict[str, Any]]:
    """按**段落**聚合成块，保留全文绝对字符区间与页号。

    **不变量（最强口径）**：`text[块.char_start:块.char_end] == 块.text`，**逐字相等**
    （不是"去掉空白后相等"）。做法是**从原文切片**得到块文本，而不是把行 `join` 回去——
    2026-09-17 被 Phase A 验收测试抓到：跨页块原先用 `"\\n".join(...)` 重建，而规范全文的
    页间分隔是 `"\\n\\n"`，于是块文本与区间**对不上**（这正是"引用点回原文"会失真的地方）。

    规则：
    - 逐行累加；再加一行会超 `max_chars` 就先落一块（**不跨越超限**）；
    - 单行本身超 `max_chars` 时**硬切**（否则一行几万字的材料只出一块，检索粒度退化）；
    - 空行只是分隔符（不进块首尾），但**块区间内的原始分隔符原样保留**。

    ⚠ `max_chars < 1` **直接抛 `ValueError`**（2026-09-17 修）：硬切循环里
    `seg_end = min(off + max_chars, line_end)`，当 `max_chars <= 0` 时 `seg_end == off`
    ⇒ 指针**不前进**、**死循环**。verifier 用 subprocess+12s 超时实测：
    `max_chars=0/-5` 均不终止（`100→1` 块、`1→10` 块正常）。
    这里**抛错而不夹紧到 1**：静默夹紧会把调用方的参数 bug 藏起来，而本层的纪律是
    "宁可显式拒绝，不假装正常"。校验放在**最前面**——否则空文本会先走早退分支，
    把非法参数放过去（同一个参数两种命运）。规则本体见 `_require_positive_max_chars`。
    """
    _require_positive_max_chars(max_chars)
    blocks: list[dict[str, Any]] = []
    if not text.strip():
        return blocks

    def emit(start: int, end: int) -> None:
        """把 `[start,end)` 这段原文落成一块；区间收紧到 strip 后的实际内容。"""
        raw = text[start:end]
        body = raw.strip()
        if not body:
            return
        lead = len(raw) - len(raw.lstrip())
        s = start + lead
        blocks.append({"text": body, "char_start": s, "char_end": s + len(body),
                       "page": page_of(s, spans)})

    lines: list[tuple[int, int]] = []       # 当前缓冲里各非空行的 (start, end)
    cursor = 0
    for raw_line in text.split("\n"):
        line_start, line_end = cursor, cursor + len(raw_line)
        cursor = line_end + 1               # +1 吃掉换行符
        if not raw_line.strip():
            continue
        if len(raw_line) > max_chars:       # 超长单行：先落缓冲，再硬切
            if lines:
                emit(lines[0][0], lines[-1][1])
                lines = []
            off = line_start
            while off < line_end:
                seg_end = min(off + max_chars, line_end)
                emit(off, seg_end)
                off = seg_end
            continue
        if lines and (line_end - lines[0][0]) > max_chars:
            emit(lines[0][0], lines[-1][1])
            lines = []
        lines.append((line_start, line_end))
    if lines:
        emit(lines[0][0], lines[-1][1])
    return blocks


# ------------------------------------------------------------------ 收件入库
def ingest_material_file(project_id: str, path: Path, *, origin: str = "user",
                         deep_fallback: bool = False,
                         source_tier: str | None = None,
                         max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:
    """把一个文件登记为材料（**默认 pending**）+ 建切片。

    - **查重**：同项目内 `content_hash` 已存在 → 直接返回既有材料并标 `duplicate=True`
      （重复放同一份文件不该产生两份材料）；
    - **自包含存储**：文件不在项目目录内就复制进来（材料平面要能被独立备份/清理）；
    - 解析不出文本（扫描件且未开云深度解析）→ **仍登记材料**，但 `chunk_count=0` 且
      在 `tier_reason`/返回里如实说明原因——**不能假装它可用**，也不能因此把它丢掉
      （用户得看得见"这份没解析出文字"）。
    """
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(f"材料文件不存在: {src}")
    if src.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持的材料格式 {src.suffix!r}（支持 {SUPPORTED_SUFFIXES}）")
    # 先校验参数，再碰文件：否则"解析不出文本"时 `chunk_text` 根本不会被调用
    # （见下方 `if text.strip() else []`），非法 max_chars 就会被**静默放过**。
    _require_positive_max_chars(max_chars)

    content_hash = file_hash(src)
    for existing in mr.list_materials(project_id):
        if existing["content_hash"] == content_hash:
            existing["duplicate"] = True
            existing["chunk_count"] = mr.chunk_count(existing["material_id"])
            return existing

    # 自包含：项目目录外的文件复制进来
    target_dir = mr.materials_dir(project_id)
    stored = src
    if src.parent.resolve() != target_dir.resolve():
        stored = target_dir / src.name
        if not stored.exists() or file_hash(stored) != content_hash:
            stored.write_bytes(src.read_bytes())

    pages = extract_pages(stored, deep_fallback=deep_fallback)
    text, spans = build_document(pages)
    chunks = chunk_text(text, spans, max_chars=max_chars) if text.strip() else []

    note = None
    if not chunks:
        note = ("未解析出文本（可能是扫描件）；默认不走云深度解析，"
                "如需云解析请显式允许（allow_deep）后再试")
    mat = mr.add_material(
        project_id,
        strip_duplicate_suffix(stored.stem),
        origin=origin,
        kind="other",
        source_tier=source_tier,
        content_hash=content_hash,
        raw_path=str(stored),
        mime=stored.suffix.lower().lstrip("."),
        tier_reason=note,
        tier_evidence={"from_file": str(src.name), "pages": len(pages)},
    )
    n = mr.add_chunks(mat["material_id"], chunks)
    out = mr.get_material(mat["material_id"]) or mat
    out["chunk_count"] = n
    out["duplicate"] = False
    out["parsed_pages"] = len(pages)
    return out


def ingest_project_dir(project_id: str, *, origin: str = "user",
                       deep_fallback: bool = False) -> list[dict[str, Any]]:
    """收件箱式入库：把项目参考资料文件夹里的受支持文件逐份登记（单份失败不中断整批）。"""
    out: list[dict[str, Any]] = []
    for p in scan_project_dir(project_id):
        try:
            out.append(ingest_material_file(project_id, p, origin=origin,
                                            deep_fallback=deep_fallback))
        except Exception as e:  # noqa: BLE001 — 单份失败不得中断整批（与批量预览同范式）
            out.append({"raw_path": str(p), "status": "error",
                        "error": f"{type(e).__name__}: {e}"})
    return out
