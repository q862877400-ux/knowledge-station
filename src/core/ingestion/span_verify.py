# -*- coding: utf-8 -*-
"""span 坐标入库体检（2026-08-26 新增，P1-③）：

入库后对新文档跑带内文字真值验证，把"新增文档高亮是否错位"从不可见变成可告警：
- ``verify_doc``：单文档抽样验证 → {n, top_only, bottom_only, both, none, verdict, ...}
- ``verify_library``：全库体检汇总
- CLI：``python -m src.core.ingestion.span_verify [--threshold 0.3]``

判定语义（与 span_calibration 同源，复用 band_text_hit）：
- top_only >= 2 且 top_only > bottom_only → ``top_suspect``（坐标疑似顶部原点 → 高亮镜像错位）
- 否则 ``ok``
- bottom_hit_rate = bottom_only / n（底部原点解释的带内命中率，供阈值告警）
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import fitz

from src.core.ingestion.span_calibration import (
    _stratified_sample,
    _text_evidence,
    _span_get,
)


def _db() -> sqlite3.Connection:
    from src.core.config import get_settings
    conn = sqlite3.connect(str(get_settings().db_path))
    conn.row_factory = sqlite3.Row
    return conn


def verify_doc(doc_id: str, pdf_path: str | Path,
               conn: sqlite3.Connection | None = None,
               cap: int = 60) -> dict[str, Any]:
    """抽样验证单文档 span 坐标系。只读，零写库。"""
    if conn is None:
        conn = _db()
    rows = conn.execute(
        "SELECT s.page_number, s.bbox_json, s.sort_order,"
        " cr.clause_revision_id, cr.content_text"
        " FROM source_span s JOIN clause_revision cr"
        " ON cr.clause_revision_id = s.clause_revision_id"
        " WHERE cr.doc_id=? AND cr.content_type='normal' AND s.span_type='text'"
        " ORDER BY s.page_number, s.sort_order, s.rowid",
        (doc_id,)).fetchall()
    if not rows:
        return {"n": 0, "verdict": "no_spans"}
    spans = [{"page_number": r[0], "bbox": json.loads(r[1]),
              "sort_order": r[2] or 0, "clause_revision_id": r[3] or "",
              "head": r[4] or ""} for r in rows]
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return {"n": len(spans), "verdict": "pdf_error", "error": str(e)[:120]}
    try:
        valid = [s for s in spans if 1 <= int(s["page_number"]) <= doc.page_count]
        sampled = _stratified_sample(valid, cap)
        top_only, bottom_only, both, none = _text_evidence(doc, sampled)
        n = len(sampled)
        verifiable = top_only + bottom_only + both
        verdict = "top_suspect" if (top_only >= 2 and top_only > bottom_only) else "ok"
        return {
            "n": n,
            "top_only": top_only, "bottom_only": bottom_only,
            "both": both, "none": none,
            "verifiable_rate": round(verifiable / n, 3) if n else 0,
            "bottom_hit_rate": round(bottom_only / n, 3) if n else 0,
            "verdict": verdict,
        }
    finally:
        doc.close()


def verify_library(conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """全库体检：返回每个有 span 文档的验证结果（含 top_suspect 标记）。"""
    if conn is None:
        conn = _db()
    out = []
    for d in conn.execute(
        "SELECT doc_id, standard_no, file_path FROM doc_meta WHERE file_path IS NOT NULL"
    ).fetchall():
        n = conn.execute(
            "SELECT COUNT(*) FROM source_span s JOIN clause_revision cr"
            " ON cr.clause_revision_id=s.clause_revision_id WHERE cr.doc_id=?",
            (d["doc_id"],)).fetchone()[0]
        if not n:
            continue
        res = verify_doc(d["doc_id"], d["file_path"], conn)
        res["doc_id"] = d["doc_id"]
        res["standard_no"] = d["standard_no"]
        out.append(res)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="span 坐标入库体检")
    ap.add_argument("--threshold", type=float, default=0.3,
                    help="bottom_hit_rate 低于该值且 top_suspect 时告警（默认 0.3）")
    args = ap.parse_args(argv)
    conn = _db()
    results = verify_library(conn)
    conn.close()
    suspect = [r for r in results if r["verdict"] == "top_suspect"]
    for r in results:
        flag = "⚠ top_suspect" if r["verdict"] == "top_suspect" else "✓"
        print(f"{flag} {r['standard_no']:<28} n={r['n']:>3} "
              f"top={r.get('top_only',0):>2} bot={r.get('bottom_only',0):>2} "
              f"both={r.get('both',0):>2} none={r.get('none',0):>2} "
              f"bottom_hit={r.get('bottom_hit_rate',0):.2f}")
    print(f"\n合计 {len(results)} 部文档，top_suspect {len(suspect)} 部"
          + (f" → {[s['standard_no'] for s in suspect]}" if suspect else ""))
    return 1 if suspect else 0


if __name__ == "__main__":
    raise SystemExit(main())
