"""导出模块（阶段4）：R19 引用格式化导出 + exports 目录/命名约定。

**只剩纯文本引用块 + 落盘目录约定**（2026-09-19，EXECUTION-PLAN 第 4 步）：
业主早已否决 Word/PPT 交付物（见 `docs/NOT-DOING.md` 第 1 条：产出物只出 Markdown），
本模块原先是四条 Word 导出的公共底座（`_open_document` / `_templates_dir` +
`export_qa_citations_docx` / `export_review_report_docx`），**整条 Word 产出通路已拆除**。
留下的两件东西仍被多处复用，不是残留：

- `build_citation_block()`：R19 标准引用**纯文本**块（前端一键复制，从来不是 Word）；
- `_exports_dir()` / `_safe_name()`：**落盘目录与命名约定**的单一所有者
  （效力报告 xlsx、更新检查结果 xlsx、公告发现 xlsx、数据包、`/export/download` 的
  穿越防护都引用它俩）。

⚠ **`python-docx` 仍在依赖里**，因为**输入侧**（`docx_adapter` / `docx_ingest` /
`material_ingest` / `law_source`）与**编辑工具** `office_roundtrip` 都用它——被撤的只是
"把 Word 当交付物输出"这条通路。
"""
from __future__ import annotations

import re
from pathlib import Path

from src.core.config import get_settings


def _exports_dir() -> Path:
    d = get_settings().data_dir / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name)[:60]


def build_citation_block(evidences: list[dict]) -> str:
    """R19 标准引用代码块（纯文本，供前端一键复制）。"""
    lines = []
    for e in evidences:
        no = e.get("standard_no") or ""
        cn = e.get("clause_number") or ""
        title = e.get("title") or ""
        head = f"• {no} {cn}"
        if title:
            head += f"【{title}】"
        head += f"（第 {e.get('page_start', '?')} 页）"
        lines.append(head)
        content = (e.get("content_text") or "").strip().replace("\n", " ")
        if content:
            lines.append(f"  条文：{content[:160]}{'…' if len(content) > 160 else ''}")
    return "\n".join(lines)
