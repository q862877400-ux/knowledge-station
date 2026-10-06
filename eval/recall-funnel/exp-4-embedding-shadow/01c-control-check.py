"""E4 · 步骤 1c：**对照臂自检** —— 删掉那 43 条之后，基线必须仍然复现。

为什么必须有：`01b-align-arms.py` 改动了对照臂的候选集合。
若基线因此变化，说明那 43 条**真的进过某条题的前 1000 名**，那就必须单独说清楚，
不能默默当成"删了没事"。（E1 那轮同样的检查：删完仍是 12 / 21 / 43 条。）

期望（主结果 120 条口径，来自 `funnel-summary.json` / `ab-result.json` 的对照臂）：
  Vector @20 = 0.1000（12 条）/ @100 = 0.1750（21 条）/ @1000 = 0.3583（43 条）

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\01c-control-check.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
OUT = HERE / "control-check.json"
WANT = {20: 12, 100: 21, 1000: 43}


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    head = [it for it in v2 if it["v2"]["bucket"] == "keep"
            and not ({"gold_multi_def", "gold_dup_text"} & set(it["v2"]["flags"]))]
    print(f"[ctrl] 主结果 {len(head)} 条", flush=True)

    hit = {d: 0 for d in WANT}
    for n, it in enumerate(head, 1):
        gold = it["v2"]["gold_cr_id"]
        qv = embedder.embed_query(it["query"])
        cand = [r[0] for r in conn.execute(
            "SELECT clause_revision_id FROM clause_vec"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), 1000))]
        for d in WANT:
            if gold in cand[:d]:
                hit[d] += 1
        if n % 40 == 0:
            print(f"[ctrl] {n}/{len(head)}", flush=True)

    rows, ok_all = [], True
    for d in (20, 100, 1000):
        want = WANT[d]
        got = hit[d]
        ok = got == want
        ok_all &= ok
        rows.append({"depth": d, "want_items": want, "got_items": got,
                     "want_rate": round(want / len(head), 4), "got_rate": round(got / len(head), 4),
                     "ok": ok})
        print(f"[ctrl] @{d:<4d} 副本 {got}（{got/len(head):.4f}）  基线 {want}"
              f"（{want/len(head):.4f}）  {'✅' if ok else '⛔'}")
    result = {"why": "删掉 43 条之后基线必须仍复现（E1 同款检查）",
              "n": len(head), "depths": rows, "ok": ok_all,
              "verdict": "✅ 对照臂复现基线 ⇒ 删那 43 条无副作用" if ok_all
                         else "⛔ 基线变了 ⇒ 那 43 条真的进过某条题的前 1000 名，必须单独说清楚"}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(result["verdict"])
    print(f"已写 {OUT}")
    conn.close()
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
