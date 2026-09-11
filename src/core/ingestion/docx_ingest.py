"""docx 入库入口（Task 11.1）：COM 转 PDF 走完整管线（有 bbox）；无 Word 走降级直解。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from src.core.domain.models import ClauseRevisionModel
from src.core.exceptions import KnowledgeStationError
from src.core.ingestion.docx_adapter import docx_to_pdf_via_com, parse_docx_text
from src.core.ingestion.pipeline import run_full_ingest
from src.core.knowledge.classifier import classify_clause
from src.core.storage import clause_repo
from src.core.storage.sqlite_db import get_db_connection, init_schema, write_transaction


def run_docx_ingest(docx_path: Path, standard_no: str, standard_name: str,
                    short_code: str | None = None, doc_type: str = "standard",
                    domain_tags: list[str] | None = None,
                    legal_hierarchy: str = "GB") -> dict:
    """docx 入库：优先 COM 转 PDF → run_full_ingest；降级直解入库。"""
    if not docx_path.exists():
        return {"status": "error", "message": f"文件不存在: {docx_path}"}
    init_schema()
    file_hash = hashlib.sha256(docx_path.read_bytes()).hexdigest()
    conn = get_db_connection()
    if conn.execute("SELECT doc_id FROM doc_meta WHERE file_hash=?", (file_hash,)).fetchone():
        return {"status": "duplicate"}

    # (a) COM 转 PDF 优先（原生保真 + 有 bbox）
    pdf_candidate = docx_path.with_suffix(".pdf")
    if docx_to_pdf_via_com(docx_path, pdf_candidate):
        return run_full_ingest(pdf_candidate, standard_no, standard_name,
                               short_code, doc_type, domain_tags, legal_hierarchy)

    # (b) 降级直解（无 bbox，前端显示"原文为 Word 文档"）
    clauses_raw = parse_docx_text(docx_path)
    if not clauses_raw:
        return {"status": "error", "message": "docx 未识别到任何条款"}
    doc_id = f"doc_{ULID()}"
    models: list[ClauseRevisionModel] = []
    for i, c in enumerate(clauses_raw):
        no = c["number"]
        tc = classify_clause(c["text"], doc_type=doc_type)
        cid = f"clrev_{ULID()}"
        models.append(ClauseRevisionModel(
            clause_revision_id=cid, doc_id=doc_id,
            clause_key=clause_repo.make_clause_key(doc_id, no),
            standard_no=standard_no, clause_number=no,
            content_text=c["text"],
            knowledge_type=tc.knowledge_type, type_confidence=tc.type_confidence,
            modality=tc.modality, modality_strength=tc.modality_strength,
            subject=tc.subject, exception=tc.exception,
            cross_refs=tc.cross_refs, is_suspicious=tc.is_suspicious,
            page_start=1, page_end=1))  # 无原页（docx 直解），source_spans 空
    normal = [m for m in models if not m.clause_number.startswith("前置")]
    preface = [m for m in models if m.clause_number.startswith("前置")]
    with write_transaction() as txn:
        clause_repo.insert_document(txn, dict(
            doc_id=doc_id, standard_no=standard_no, standard_name=standard_name,
            short_code=short_code or standard_no.replace(" ", "").replace("-", ""),
            current_revision_id=f"rev_{ULID()}", doc_type=doc_type,
            legal_hierarchy=legal_hierarchy, domain_tags=domain_tags or [],
            file_path=str(docx_path.resolve()), file_hash=file_hash))
        n = clause_repo.insert_clauses_in_txn(txn, normal)
        if preface:
            clause_repo.insert_clauses_in_txn(txn, preface, content_type="前置说明")
    return {"status": "ok", "doc_id": doc_id, "total_clauses": n,
            "pages_parsed": 0, "mode": "docx-direct"}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("docx_path", type=Path)
    ap.add_argument("--standard-no", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--doc-type", default="standard", choices=["standard", "法律法规"])
    ap.add_argument("--domain-tags", default="")
    args = ap.parse_args(argv)
    out = run_docx_ingest(args.docx_path, args.standard_no, args.name or args.standard_no,
                          doc_type=args.doc_type,
                          domain_tags=[t for t in args.domain_tags.split(",") if t])
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
    sys.stdout.flush()
    os._exit(0 if out.get("status") in ("ok", "duplicate") else 1)


if __name__ == "__main__":
    sys.exit(main())
