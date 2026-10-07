"""P2 诊断第 2 步：**"并集里有、融合里没有" —— 是不是被时效过滤丢了？**

## 为什么查这个
第 1 步量出（headline 120 条，入库前库）：
 · 档位 = L0 8 / L1 72 / **L2 33** / **L3 4** / L4 3；
 · 那 40 条（L2+L3+L4）**已经在六路并集里**，但 **gold 在融合结果里的名次中位 21、最大才 29，
   而只有 4 条落在这个区间** ⇒ **另外 36 条在融合结果里根本找不到**（`gold_rank = None`）。
 · **并集有、融合没** ⇒ 融合这一步**丢东西**。而 `funnel.py` 写明融合 = **RRF + 时效过滤**。
 ⇒ 假设：**是时效过滤把 gold 丢掉的**（`doc_meta.legal_status` 不是 `effective` 的文档被滤掉）。

## 本脚本怎么验（只读）
 对那 40 条的 gold 条款，去库里查它所属文档的 `legal_status`，与
 **L0（进得了前 8 的那 8 条）**、**全体** 对比。
 · 若 L2 的 `legal_status` 明显异于 L0 ⇒ **假设立住**（这更像**产品决策**，不是调参题）；
 · 若两者分布一样 ⇒ **假设推翻**，回去查 RRF 常数/权重。

⚠ 只读；不改库、不改代码。

用法： .venv\\Scripts\\python.exe tools\\p2-check-status.py [--data ...] [--db ...]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "eval" / "recall-funnel" / "regression-ingest" / "funnel-per-query-before.jsonl"
#: 与"入库前"那一跑同源（那次用的是这个备份）
DEFAULT_DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "backups" / "knowledge-20261007-102406.db"
OUT = ROOT / "eval" / "recall-funnel" / "p2-status-check.json"

_EXCLUDE = {"gold_multi_def", "gold_dup_text"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--db", default=str(DEFAULT_DB))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"⛔ 库不在：{db}")
        print("   （可传 --db 指向别的库；生产库也行，只读）")
        return 1
    rows_all = [json.loads(l) for l in Path(args.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows_all if r.get("bucket") == "keep"
            and not (_EXCLUDE & set(r.get("flags") or []))]

    def tier(r) -> str:
        u = r["union"]["same_budget"]
        if not u.get("@1000"):
            return "L1"
        if not u.get("@20"):
            return "L2"
        if not r["fused"].get("hit@20"):
            return "L3"
        gr = r["fused"].get("gold_rank")
        return "L0" if (gr is not None and gr <= 8) else "L4"

    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    print(f"[s] 对照库 = {db.name}")

    def status_of(r) -> dict:
        """gold 条款所属文档的 legal_status / 是否在金标里。"""
        row = c.execute(
            "SELECT dm.legal_status, dm.doc_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
            " WHERE dm.standard_no=? AND cr.clause_number=? LIMIT 1",
            (r["gold_std"], r["gold_clause"])).fetchone()
        if not row:
            # 标准号可能以 `(OCR采集)` 之类后缀存着，退化为模糊匹配
            row = c.execute(
                "SELECT dm.legal_status, dm.doc_id FROM clause_revision cr"
                " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                " WHERE dm.standard_no LIKE ? AND cr.clause_number=? LIMIT 1",
                (r["gold_std"] + "%", r["gold_clause"])).fetchone()
        return {"legal_status": (row[0] if row else "**库里找不到该 gold**"),
                "doc_id": (row[1] if row else None)}

    by_tier: dict[str, list] = {}
    for r in rows:
        by_tier.setdefault(tier(r), []).append(r)

    report = {"db": str(db), "n_headline": len(rows), "tiers": {}}
    for t in ("L0", "L2", "L3", "L4", "L1"):
        grp = by_tier.get(t) or []
        if not grp:
            continue
        cnt = Counter()
        gold_rank_none = 0
        for r in grp:
            st = status_of(r)
            cnt[st["legal_status"]] += 1
            if r["fused"].get("gold_rank") is None:
                gold_rank_none += 1
        report["tiers"][t] = {"n": len(grp), "legal_status": dict(cnt),
                              "融合里找不到 gold 的条数": gold_rank_none}
        top = "，".join(f"{k}×{v}" for k, v in cnt.most_common(4))
        print(f"\n[{t}] {len(grp)} 条")
        print(f"     gold 文档的 legal_status：{top}")
        print(f"     融合结果里找不到 gold：{gold_rank_none}/{len(grp)}")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[s] 已写 {OUT}")
    print("[s] 判读：若 L2 的 legal_status 明显异于 L0 ⇒ 时效过滤是嫌疑人（偏产品决策，不是调参）；")
    print("    若分布一样 ⇒ 假设推翻，回去查 RRF 常数 / 通道权重。")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
