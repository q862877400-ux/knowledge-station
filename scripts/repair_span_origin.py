"""存量 source_span 坐标系校准 CLI（R-B：投票/翻转实现已收敛到
src/core/ingestion/span_calibration.py，本脚本只负责遍历文档与报告输出）。

对每个有 PDF 的文档调用 span_calibration.calibrate：全量 span 最近行投票判定该文档
坐标系，判为顶部原点的文档 → 全部 span 翻转 (y'=H−y) + event_log 审计。

用法：
  python scripts/repair_span_origin.py            # dry-run：只报告判定结果
  python scripts/repair_span_origin.py --apply    # 实际翻转 + 审计
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.ingestion.span_calibration import calibrate  # noqa: E402

DB = str(Path.home() / "AppData/Roaming/KnowledgeStation/database/knowledge.db")


def main(apply: bool = False) -> int:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    docs = db.execute(
        "SELECT doc_id, standard_no, file_path FROM doc_meta WHERE file_path IS NOT NULL"
    ).fetchall()
    print(f"文档总数: {len(docs)}")
    flipped = ok = skipped = 0
    for d in docs:
        n_spans = db.execute(
            "SELECT COUNT(*) FROM source_span s JOIN clause_revision cr"
            " ON cr.clause_revision_id=s.clause_revision_id WHERE cr.doc_id=?",
            (d["doc_id"],)).fetchone()[0]
        if not n_spans:
            continue
        try:
            fitz.open(d["file_path"]).close()
            res = calibrate(d["doc_id"], d["file_path"], db, apply=apply)
        except Exception:
            print(f"[skip] {d['standard_no']}: PDF 打不开")
            skipped += 1
            continue
        verdict = res.get("verdict", "unknown")
        smp = res.get("samples", {})
        if verdict == "top_flip":
            print(f"[需翻转→已翻转] {d['standard_no']}: 带内真值 top 命中 {smp.get('top_hits')}/{smp.get('n')}"
                  f"（span {n_spans} 条）")
            if apply:
                flipped += 1
        elif verdict == "bottom_keep":
            print(f"[ok] {d['standard_no']}: 底部原点正确（带内真值命中 {smp.get('bottom_hits')}/{smp.get('n')}）")
            ok += 1
        else:
            print(f"[skip] {d['standard_no']}: 带内真值无法判定（top {smp.get('top_hits')}/"
                  f"bottom {smp.get('bottom_hits')} of {smp.get('n')}）→ 保持原样待人工")
            skipped += 1
    db.commit()
    db.close()
    print(f"\n完成：翻转 {flipped}，正确 {ok}，跳过 {skipped}，apply={apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(apply="--apply" in sys.argv))
