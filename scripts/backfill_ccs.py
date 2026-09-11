# -*- coding: utf-8 -*-
"""CCS 专用回填（backfill_meta 的网络阶段单跑版）：
   前一轮日期/层级/类型已回填完毕，这里只查 ccs_code 为空的行，
   不再逐个 fitz.open 扫 PDF——直接 SQL 圈定 → fetch → 限速写库。
   dry-run 缺省，--apply 写库 + event_log 审计。"""
import sys, io, json, sqlite3, time, argparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\AI\work space\zcode")

DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--delay", type=float, default=0.5)
ap.add_argument("--limit", type=int, default=0, help="本轮最多处理 N 条（0=不限）")
a = ap.parse_args()

db = sqlite3.connect(DB)
db.execute("PRAGMA busy_timeout=5000")
rows = db.execute(
    "SELECT doc_id, standard_no, standard_name FROM doc_meta "
    "WHERE ccs_code IS NULL OR ccs_code = '' ORDER BY doc_id"
).fetchall()
if a.limit:
    rows = rows[:a.limit]
print(f"CCS 待回填: {len(rows)} 条（apply={a.apply}, delay={a.delay}s）", flush=True)

from src.core.knowledge.ccs_fetcher import fetch_ccs

ok = fail = 0
t0 = time.time()
for idx, (doc_id, sno, sname) in enumerate(rows):
    try:
        ccs = fetch_ccs(sno, sname)
    except Exception as e:
        print(f"  [fail] {sno}: {e}", flush=True)
        ccs = None
        fail += 1
    code = getattr(ccs, "code", None) or (ccs.get("code") if isinstance(ccs, dict) else None)
    name = getattr(ccs, "name", None) or (ccs.get("name") if isinstance(ccs, dict) else None)
    if code:
        ok += 1
        if a.apply:
            db.execute(
                "UPDATE doc_meta SET ccs_code=?, ccs_name=?, updated_at="
                "datetime('now','localtime') WHERE doc_id=?",
                (code, name, doc_id))
            db.execute(
                "INSERT INTO event_log (event_type, actor, target_type, target_id,"
                " metadata) VALUES ('backfill_meta','script','doc',?,?)",
                (doc_id, json.dumps({"ccs_code": code}, ensure_ascii=False)))
            db.commit()
        print(f"  [{'回填' if a.apply else '待回填'}] {sno}: {code} {name}", flush=True)
    if a.delay and idx % 20 == 19:
        eta = (time.time() - t0) / (idx + 1) * (len(rows) - idx - 1)
        print(f"  … 进度 {idx+1}/{len(rows)}，ok={ok} fail={fail}，ETA {eta/60:.0f} 分钟", flush=True)
    if a.delay:
        time.sleep(a.delay)

db.commit()
db.close()
print(f"完成：命中 {ok}，失败 {fail}，共 {len(rows)}，用时 {(time.time()-t0)/60:.0f} 分钟", flush=True)
