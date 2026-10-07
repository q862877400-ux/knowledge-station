"""国标阶段核对（目标 ②③ 的国标半）：三个计数 + 质量抽验 + 失配清单。

只读副本；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\36-verify-gb-phase.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "verify-gb-phase.json"
sys.path.insert(0, str(ROOT))
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"
#: 真库（只读）—— 用于算"入库前有多少本强制国标"
REAL = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def stats(db: Path, label: str) -> dict:
    import sqlite3 as s
    c = s.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=30000")
    out = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ("doc_meta", "clause_revision")}
    try:
        from src.core.storage.sqlite_db import load_vec_extension
        load_vec_extension(c)
        out["clause_vec"] = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    except Exception as e:                                                  # noqa: BLE001
        out["clause_vec"] = f"未取到:{type(e).__name__}"
    # 强制国标（GB 开头但不是 GB/T、GB/Z）本数
    out["mandatory_gb_docs"] = c.execute(
        "SELECT COUNT(*) FROM doc_meta WHERE UPPER(standard_no) LIKE 'GB %'"
        " AND UPPER(standard_no) NOT LIKE 'GB/T%' AND UPPER(standard_no) NOT LIKE 'GB/Z%'"
    ).fetchone()[0]
    out["gb_family_docs"] = c.execute(
        "SELECT COUNT(*) FROM doc_meta WHERE UPPER(standard_no) LIKE 'GB%'").fetchone()[0]
    print(f"[{label}] {out}", flush=True)
    c.close()
    return out


def main() -> int:
    before = stats(REAL, "真库(入库前)")
    after = stats(TRIAL, "副本(现在)")

    c = sqlite3.connect(f"file:{TRIAL.as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=30000")

    # ⚠ 更正：第一版按 `file_path LIKE 'D:\AI\work space\标准\%'` 筛"本次入的"，
    #   结果把**库里原有**的源文档也捞进来了（7,163 本）⇒ 抽样抽到老文档。
    #   正确做法：用**台账（journal）里本次 ok 的 doc_id** 来界定"本次入的"。
    journal_path = ROOT / "var" / "tmp" / "ingest-full" / "journal.jsonl"
    j_rows = [json.loads(x) for x in journal_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    new_ids = {r.get("doc_id") for r in j_rows
               if r.get("kind") == "gb" and r.get("status") == "ok" and r.get("doc_id")}
    new_docs = []
    for did in new_ids:
        r = c.execute("SELECT standard_no, standard_name FROM doc_meta WHERE doc_id=?",
                      (did,)).fetchone()
        if r:
            new_docs.append((did, r[0], r[1]))
    print(f"\n[gb] 本次入的国标文档 = {len(new_docs)} 本（按台账 doc_id 界定）", flush=True)
    per = []
    for did, no, nm in new_docs:
        n = c.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (did,)).fetchone()[0]
        per.append({"std_no": no, "name": (nm or "")[:40], "clauses": n})
    per.sort(key=lambda x: x["clauses"])
    print(f"     条款数：中位 {per[len(per)//2]['clauses'] if per else 0} / "
          f"最小 {per[0]['clauses'] if per else 0} / 最大 {per[-1]['clauses'] if per else 0} / "
          f"合计 {sum(x['clauses'] for x in per):,}", flush=True)

    # 质量抽验：抽 3 本看条文
    samples = []
    for pick in per[:1] + per[len(per)//2:len(per)//2 + 1] + per[-1:]:
        r = c.execute("SELECT doc_id FROM doc_meta WHERE standard_no=? LIMIT 1",
                      (pick["std_no"],)).fetchone()
        if not r:
            continue
        rows = c.execute(
            "SELECT clause_number, substr(content_text,1,76) FROM clause_revision"
            " WHERE doc_id=? ORDER BY rowid LIMIT 3", (r[0],)).fetchall()
        samples.append({"std_no": pick["std_no"], "name": pick["name"],
                        "clauses": pick["clauses"],
                        "head": [{"no": a, "text": b.replace("\n", " ")} for a, b in rows]})
        print(f"\n     抽验 {pick['std_no']}（{pick['clauses']} 条）：", flush=True)
        for a, b in rows:
            print(f"        [{a}] {b.replace(chr(10),' ')[:76]}", flush=True)

    # 失配清单：源目录里有产物、但库里查不到
    journal = ROOT / "var" / "tmp" / "ingest-full" / "journal.jsonl"
    last = {}
    for line in journal.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            last[r["key"]] = r
    gb = [v for v in last.values() if v["kind"] == "gb"]
    missing, skipped = [], Counter()
    have = {r[0] for r in c.execute("SELECT standard_no FROM doc_meta")}
    for v in gb:
        skipped[v["status"]] += 1
        if v["status"] in ("error", "exception"):
            missing.append(v)
        elif v["status"] == "ok" and v["std_no"] not in have:
            missing.append({**v, "why": "台账记 ok 但库里查不到（需人工核）"})

    result = {
        "why": "国标阶段核对（目标 ②③ 的国标半）",
        "db_before_real": before, "db_after_trial": after,
        "delta": {k: (after[k] - before[k]) if isinstance(after.get(k), int)
                  and isinstance(before.get(k), int) else None
                  for k in ("doc_meta", "clause_revision", "clause_vec",
                            "mandatory_gb_docs", "gb_family_docs")},
        "gb_docs_ingested_this_run": len(new_docs),
        "gb_clause_stats": {
            "median": per[len(per)//2]["clauses"] if per else 0,
            "min": per[0]["clauses"] if per else 0,
            "max": per[-1]["clauses"] if per else 0,
            "total": sum(x["clauses"] for x in per)},
        "journal_status_counts": dict(skipped),
        "mismatch": missing[:50],
        "mismatch_n": len(missing),
        "samples": samples,
        "boundary": ["只读；条款数只证明'切出来了'，不等于内容与 PDF 逐字一致。",
                     "`mandatory_gb_docs` 按 standard_no 前缀判，是全库口径不是本次口径。"],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[gb] 台账状态分布 = {dict(skipped)}")
    print(f"[gb] **失配清单 = {len(missing)} 条**")
    print(f"[gb] 库变化 = {result['delta']}")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
