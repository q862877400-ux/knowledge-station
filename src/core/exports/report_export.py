"""导出模块（阶段4）：R19 引用格式化导出 + R35/R-L7 Word 报告。

全部本地生成（python-docx），保存到 %APPDATA%/KnowledgeStation/exports/。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from src.core.config import get_settings
from src.core.storage.sqlite_db import get_db_connection, write_transaction


def _exports_dir() -> Path:
    d = get_settings().data_dir / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _templates_dir() -> Path:
    """Task 12.6 导出模板：%APPDATA%/KnowledgeStation/templates/ 下放
    review-report.docx / qa-citations.docx 作为导出基础模板（python-docx Document(template)）。"""
    d = get_settings().data_dir / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _open_document(kind: str):
    """用模板打开 Document；无模板回退新建（保持向后兼容）。"""
    from docx import Document
    tpl = _templates_dir() / f"{kind}.docx"
    if tpl.exists():
        return Document(str(tpl))
    return Document()


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


def export_qa_citations_docx(query: str, evidences: list[dict]) -> Path:
    """R35 问答依据导出为 Word（支持 qa-citations 模板）。"""
    doc = _open_document("qa-citations")
    doc.add_heading("问答依据清单", level=1)
    doc.add_paragraph(f"问题：{query}")
    doc.add_paragraph(f"导出时间：{datetime.now():%Y-%m-%d %H:%M}（本地生成，未外发）")
    doc.add_paragraph()
    for e in evidences:
        p = doc.add_paragraph()
        p.add_run(f"{e.get('standard_no')} {e.get('clause_number')}").bold = True
        p.add_run(f"（第 {e.get('page_start', '?')} 页）")
        content = (e.get("content_text") or "").replace("\n", " ")
        doc.add_paragraph(content[:800])
        doc.add_paragraph()
    out = _exports_dir() / f"问答依据_{_safe_name(query[:20])}_{datetime.now():%Y%m%d_%H%M%S}.docx"
    doc.save(str(out))
    return out


def export_review_report_docx(task_id: str) -> Path:
    """R-L7 合规审查报告导出为 Word（含三色判定与命中法条）。"""
    from docx import Document
    from docx.shared import RGBColor
    conn = get_db_connection()
    task = conn.execute("SELECT * FROM review_task WHERE task_id=?", (task_id,)).fetchone()
    if task is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError(f"审查任务不存在: {task_id}", code="task_not_found")
    points = conn.execute(
        "SELECT * FROM review_point WHERE task_id=? ORDER BY created_at", (task_id,)).fetchall()

    color = {"red": RGBColor(0xB9, 0x1C, 0x1C), "yellow": RGBColor(0xB4, 0x53, 0x09),
             "green": RGBColor(0x15, 0x80, 0x3D)}
    label = {"red": "🔴 违法/无效风险", "yellow": "🟡 风险提示", "green": "🟢 合规"}

    doc = _open_document("review-report")
    doc.add_heading("合规审查报告", level=1)
    completed = task["completed_at"] or f"{datetime.now():%Y-%m-%d %H:%M}"
    doc.add_paragraph(
        f"审查对象：{task['object_name'] or '-'}（{task['review_type']}）")
    doc.add_paragraph(
        f"审查时间：{completed}｜"
        f"违法 {task['red_count']} 项 / 风险 {task['yellow_count']} 项 / 合规 {task['green_count']} 项")
    doc.add_paragraph()

    for i, p in enumerate(points, 1):
        verdict = p["verdict"] or "yellow"
        h = doc.add_heading(f"{i}. [{p['point_type']}] {label.get(verdict, verdict)}", level=2)
        for run in h.runs:
            run.font.color.rgb = color.get(verdict, color["yellow"])
        doc.add_paragraph(f"审查点原文：{(p['point_content'] or '')[:300]}")
        doc.add_paragraph(f"判定理由：{p['verdict_reason'] or '-'}")
        matched_ids = json.loads(p["matched_clause_ids"] or "[]")
        if matched_ids:
            ph = ",".join("?" * len(matched_ids))
            clauses = conn.execute(
                f"SELECT cr.clause_number, cr.content_text, dm.standard_no, cr.page_start"
                f" FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                f" WHERE cr.clause_revision_id IN ({ph})", matched_ids).fetchall()
            for c in clauses:
                para = doc.add_paragraph()
                para.add_run(f"依据：{c['standard_no']} {c['clause_number']}"
                             f"（第 {c['page_start']} 页）").bold = True
                doc.add_paragraph((c["content_text"] or "").replace("\n", " ")[:400])
        doc.add_paragraph()

    doc.add_paragraph("—— 本报告由本地引擎生成，判定基于规则引擎与本地知识库，仅供参考。")
    out = _exports_dir() / f"合规审查报告_{_safe_name(task['object_name'] or task_id[:16])}_{datetime.now():%Y%m%d_%H%M%S}.docx"
    doc.save(str(out))
    with write_transaction() as txn:
        txn.execute("UPDATE review_task SET report_path=? WHERE task_id=?", (str(out), task_id))
    return out
