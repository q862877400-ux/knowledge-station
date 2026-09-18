"""冒烟入库脚本（第一阶段造数据用，完整 E1-E7 管线在 T05）。

用法:
    python -m src.core.ingestion.smoke_ingest <pdf_path> [--standard-no GB30871-2022] [--name ...]

流程: Parser Worker 隔离解析 → 简化条款切分(正则) → doc_meta/几何/条款/FTS/向量入库。
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from typing import Literal

from src.core.domain.models import (
    ClauseRevisionModel, MODALITY_STRENGTH, Modality, SourceSpanModel)
from src.core.ingestion.parser_worker import run_parser_isolated
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import init_schema, get_db_connection

# 简化切分: 匹配 "x.y.z" 条款号开头 或 中文条款 "第x条"
_CLAUSE_HEAD = re.compile(r"^\s*(\d+(?:\.\d+){1,4})\s*$|^\s*(\d+(?:\.\d+){1,4})\s+\S")
_LAW_HEAD = re.compile(r"^\s*(第[一二三四五六七八九十百千]+条)\s*")
# 模态词抽取（长词优先）
_MODality_pattern = re.compile("|".join(
    sorted(MODALITY_STRENGTH.keys(), key=len, reverse=True)))


def split_into_clauses(blocks: list[dict]) -> list[dict]:
    """极简条款切分: 以条款号开头的文本块开启新条款，其余并入当前条款。"""
    clauses: list[dict] = []
    for b in blocks:
        text = (b.get("text") or "").strip()
        if not text:
            continue
        m = _CLAUSE_HEAD.match(text) or _LAW_HEAD.match(text)
        if m:
            number = (m.group(1) or m.group(2)) if (m.group(1) or m.group(2)) else m.group(0).strip()
            clauses.append({"number": number, "texts": [text], "spans": [b]})
        elif clauses:
            clauses[-1]["texts"].append(text)
            clauses[-1]["spans"].append(b)
        else:
            clauses.append({"number": "前言", "texts": [text], "spans": [b]})
    return clauses


def _classify(text: str) -> tuple[Literal["data", "rule", "legal"], Modality | None]:
    """冒烟分型：值域与 ClauseRevisionModel Literal 对齐（modality 词表 = MODALITY_STRENGTH 键）。"""
    m = _MODality_pattern.search(text)
    if m:
        word = m.group(0)
        return "rule", word  # type: ignore[return-value]  # word ∈ 正则词表 = Modality 值域（静态不可证）
    if re.search(r"\d+(\.\d+)?\s*(m|MPa|kPa|%|℃|kg|mm)", text):
        return "data", None
    return "rule", None


def ingest_pdf(pdf_path: Path, standard_no: str, standard_name: str,
               short_code: str | None = None) -> dict:
    settings = get_settings()
    if not pdf_path.exists():
        return {"status": "error", "message": f"文件不存在: {pdf_path}"}
    init_schema()
    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    conn = get_db_connection()

    dup = conn.execute("SELECT doc_id FROM doc_meta WHERE file_hash=?", (file_hash,)).fetchone()
    if dup:
        return {"status": "duplicate", "doc_id": dup[0]}

    # R43: 同标准号不同文件 → 返回提示由上层确认覆盖，而不是 IntegrityError 崩溃
    # ⚠ 查重与写入同口径（§11.0 R6c-3d）：都折存储形；不然全角入参会绕过这条护栏、
    #   直接撞 `insert_document` 的 UNIQUE（复核 b33 的次高风险）。
    from src.core.text_utils import store_standard_no
    same_no = conn.execute(
        "SELECT doc_id, file_hash FROM doc_meta WHERE standard_no=?",
        (store_standard_no(standard_no),)).fetchone()
    if same_no and same_no["file_hash"] != file_hash:
        return {"status": "standard_exists", "existing_doc_id": same_no["doc_id"],
                "message": f"标准号 {standard_no} 已存在（hash 不同）。"
                           f"如需版本覆盖更新，请先废弃旧文档或显式传 force。"}

    doc_id = f"doc_{ULID()}"

    # 先解析后入库：解析失败不产生任何残留（R1 原子性）
    result = run_parser_isolated(pdf_path, settings.data_dir / "parse_out" / doc_id)

    conn.execute("BEGIN")
    try:
        clause_repo.insert_document(conn, {
            "doc_id": doc_id, "standard_no": standard_no, "standard_name": standard_name,
            "short_code": short_code or standard_no.replace(" ", "").replace("-", ""),
            "current_revision_id": f"rev_{ULID()}", "domain_tags": ["安全"],
            "file_path": str(pdf_path.resolve()), "file_hash": file_hash,
        })
        clause_repo.insert_page_geometries(conn, doc_id, result["geometries"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    models: list[ClauseRevisionModel] = []
    preface: list[ClauseRevisionModel] = []
    for cl in split_into_clauses(result["blocks"]):
        if cl["number"] == "前言":
            # R65: 前言标记为前置说明，仅参与全文检索，不赋予条款号
            if sum(len(t) for t in cl["texts"]) > 50:
                preface.append(ClauseRevisionModel(
                    clause_revision_id=f"clrev_{ULID()}", doc_id=doc_id,
                    clause_key=clause_repo.make_clause_key(doc_id, f"preface_{len(preface)}"),
                    standard_no=standard_no, clause_number=f"前言{len(preface) + 1}",
                    content_text="\n".join(cl["texts"])[:2000],
                    knowledge_type="rule", page_start=cl["spans"][0]["page_number"],
                    page_end=cl["spans"][-1]["page_number"]))
            continue
        content = "\n".join(cl["texts"])[:2000]
        ktype, modality = _classify(content)
        pages = [s["page_number"] for s in cl["spans"]]
        models.append(ClauseRevisionModel(
            clause_revision_id=f"clrev_{ULID()}",
            doc_id=doc_id,
            clause_key=clause_repo.make_clause_key(doc_id, cl["number"]),
            standard_no=standard_no,
            clause_number=cl["number"],
            content_text=content,
            knowledge_type=ktype,
            modality=modality,
            modality_strength=MODALITY_STRENGTH.get(modality) if modality else None,
            page_start=min(pages), page_end=max(pages),
            source_spans=[SourceSpanModel(
                span_id=f"span_{ULID()}", page_number=s["page_number"], bbox=s["bbox"])
                for s in cl["spans"][:5]],
        ))
    n = clause_repo.insert_clauses(models)
    if preface:
        clause_repo.insert_clauses(preface, content_type="前置说明")
    conn.execute("UPDATE doc_meta SET updated_at=datetime('now') WHERE doc_id=?", (doc_id,))
    conn.commit()
    return {"status": "ok", "doc_id": doc_id, "total_clauses": n,
            "pages_parsed": len(result["geometries"]), "is_ocr": result["is_ocr"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", type=Path)
    ap.add_argument("--standard-no", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--short-code", default=None)
    args = ap.parse_args(argv)
    out = ingest_pdf(args.pdf_path, args.standard_no,
                     args.name or args.standard_no, args.short_code)
    print(out)
    return 0 if out.get("status") in ("ok", "duplicate") else 1


if __name__ == "__main__":
    sys.exit(main())
