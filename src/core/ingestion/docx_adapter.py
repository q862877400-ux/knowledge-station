"""docx 一等公民入库适配器（Task 11.1，v5 P2 入库便利）。

两档路径：
  (a) 本机装有 Word/WPS → COM 转 PDF（FileFormat=17）→ 复用 MinerU 管线（原生保真 + 有 bbox），优先；
  (b) 无 Word → python-docx 直接解析大纲结构入库（无页面/bbox，source_span 为空，前端降级提示）。
无 OCR、无 bbox 语义：表格转管道 Markdown（与 table_md 同源），条款号复用 law_text 层级逻辑。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.core.exceptions import KnowledgeStationError


def word_com_available() -> bool:
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def docx_to_pdf_via_com(docx_path: Path, out_pdf: Path) -> bool:
    """COM 转 PDF（Word FileFormat=17 / WPS 兼容探测）。失败返回 False 走降级。"""
    import os
    # ⚠⚠ 2026-10-09（第 17 轮）：**先查输入文件在不在**，不在就直接返回 —— 不许去起 COM。
    #   实测代价：本机 Word/WPS 的 COM 服务器不可用时，`win32com.client.Dispatch('Word.Application')`
    #   抛的是 **Windows 致命异常 0x800706BA（RPC_E_SERVER_UNAVAILABLE）**；那是 **SEH 级**异常，
    #   **Python 的 try/except 抓不住** ⇒ 整个进程当场死、连 pytest 的汇总行都打不出来。
    #   `tests/test_law_source.py::test_convert_probe_never_raises` 传的正是一个**不存在的路径**
    #   （`nope.docx`）⇒ 全量 pytest 跑到 ~69% 直接崩 ⇒ **门禁棘轮判"没跑出 passed 数字"**、
    #   `-Full` 连续多轮跑不完（本轮才查到真因）。
    #   语义上也对：没有输入文件就没有可转的东西，没必要去碰 COM。
    if not Path(docx_path).exists():
        return False
    if not word_com_available():
        return False
    try:
        import win32com.client  # type: ignore[import-not-found]  # pywin32 仅 Windows；非 Windows 检查环境防御
        import pythoncom  # type: ignore[import-not-found]  # 同上：pywin32 仅 Windows
        pythoncom.CoInitialize()
        for progid in ("Word.Application", "Kwps.Application", "wps.Application"):
            try:
                app = win32com.client.Dispatch(progid)
                app.Visible = False
                try:
                    doc = app.Documents.Open(str(docx_path.resolve()))
                    doc.SaveAs2(str(out_pdf.resolve()), FileFormat=17)
                    doc.Close(False)
                finally:
                    app.Quit()
                return True
            except Exception:
                continue
        return False
    except Exception:
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.M)
_LAW_SPLIT = re.compile(r"(?=第[一二三四五六七八九十百千零]+条)")


def parse_docx_text(docx_path: Path) -> list[dict[str, str]]:
    """降级路径 (b)：python-docx 提取大纲 → 条款切分（无 bbox）。

    返回 [{number, text}]；标题（Heading 样式）作为章节上下文并入条文。
    """
    from docx import Document
    try:
        doc = Document(str(docx_path))
    except Exception as e:
        raise KnowledgeStationError(f"docx 解析失败: {e}", code="docx_parse_error") from e

    blocks: list[tuple[str, str]] = []  # (style_name, text)
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name if para.style is not None else "") or ""
        blocks.append((style, text))

    # 表格块 → 管道 Markdown（并入其所在章节）
    tables_md: list[str] = []
    for table in doc.tables:
        rows = []
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            rows.append(" | ".join(cells))
        if rows:
            tables_md.append("\n".join(rows))

    # 组装正文 + 表格（表格附加在文档尾部章节上下文，简化处理）
    body_parts = [t for _, t in blocks if not _HEADING_RE.match(t) or len(t) > 6]
    body_text = "\n".join(body_parts)
    if tables_md:
        body_text += "\n" + "\n".join(tables_md)

    # 条款切分（复用 law_text 的 第X条 分割 + 标题行作为章节前缀）
    clauses: list[dict[str, str]] = []
    chapter_ctx = ""
    for part in _LAW_SPLIT.split(body_text):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(第[一二三四五六七八九十百千零]+条)", part)
        if m:
            clauses.append({"number": m.group(1),
                            "text": f"{part}"[:4000]})
        else:
            if len(part) < 40:
                chapter_ctx = part[:40]
            elif clauses:
                clauses[-1]["text"] += "\n" + part
            else:
                clauses.append({"number": f"前置{len(clauses) + 1}",
                                "text": part[:4000]})
    if chapter_ctx and clauses:
        clauses[0]["text"] = f"{chapter_ctx}\n{clauses[0]['text']}"
    return clauses
