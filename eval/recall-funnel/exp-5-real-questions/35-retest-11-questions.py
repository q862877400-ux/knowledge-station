"""入库验收：11 条真问题复测，**两种口径都跑**。

## 为什么要两种口径
 · **口径 A｜纯向量近邻**：与 `real-questions-result.json`（入库前基线）**同一种做法**
   （`embed_query` + `clause_vec` KNN）⇒ **同口径可比**，回答"新入的文档有没有被捞到"；
 · **口径 B｜六路融合**（`perform_hybrid_search`，生产实际用的）⇒ 回答"用户真问会看到什么"。
 ⚠ 两个口径**不能互相比较**，只能各自与自己的基线比。

## 注意（我自己踩的）
`perform_hybrid_search` 返回的是 **`List[ClauseRevisionModel]`**（列表），
带 `"results"` 键的字典在 **`search_with_details`** —— 第一版按字典取字段，11 条全部 AttributeError。

只读副本；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\35-retest-11-questions.py
"""
from __future__ import annotations

import array
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "retest-11-questions-after-ingest.json"
TRIAL_DB = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"
BEFORE = HERE / "real-questions-result.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(ROOT))

QUESTIONS = [
    ("r1", "我要做高处作业了，我不知道我这个作业是到底算几级，我应该遵守那些规定"),
    ("r2", "我们买了一个有毒气体的探头，但是安装我不知道装什么位置比较合适"),
    ("r3", "我们厂现在打算去重新修一个厂房，但是我不知道修这个厂房需要考虑哪些法律法规或者国家标准上的问题"),
    ("r4", "我们施工的时候能不能关闭消防报警系统呢？那个国标法规上是怎么要求的"),
    ("r5", "我们这个易制毒化学品仓库，到底要符合哪些要求才行？我怎么去自查有没有违规项"),
    ("r6", "我们企业是一般工贸企业，光刻机制造企业，在手续证照方面，我们要办哪些手续？安全环保的手续都要说"),
    ("r7", "我们工厂里的岗位，哪些岗位要做职业健康体检，哪些不用这个东西，我怎么去判断"),
    ("r8", "我们公司有些人，他不愿意参加职业健康体检，但是法律法规要求公司必须要给他们做体检，那这种情况冲突了怎么去解决呢"),
    ("r9", "如果说这个我们公司因为一些工艺调整，现在要增加一个职业危害因素，那我应该怎么做才能保证不管是从现场还是体检还是其他方面都能合规呢"),
    ("r10", "我要签租房合同，里面说这个我要半年一付，然后还要付一个月押金，如果我没有租满一年的话，押金不退，像这种条款是不是合法呢"),
    ("r11", "我看到有的企业和供应商签的安全协议里面说，如果是供应商因为自己违章导致的事故的，那甲方不负任何责任，这到底合不合法"),
]


def main() -> int:
    if not TRIAL_DB.exists():
        print(f"⛔ 副本库不在：{TRIAL_DB}")
        return 1
    from src.core.retrieval import embedder, hybrid_engine
    from src.core.storage.sqlite_db import load_vec_extension

    hybrid_engine.set_db_override(TRIAL_DB)
    conn = sqlite3.connect(f"file:{TRIAL_DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    n_docs = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    n_cl = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    print(f"[retest] 副本：doc_meta={n_docs} clause_revision={n_cl}", flush=True)

    before = {}
    if BEFORE.exists():
        for x in json.loads(BEFORE.read_text(encoding="utf-8"))["questions"]:
            before[x["id"]] = [r["std"] for r in x.get("old_model_top5", [])]

    def name_of(no: str) -> str:
        r = conn.execute("SELECT standard_name FROM doc_meta WHERE standard_no=? LIMIT 1",
                         (no,)).fetchone()
        return (r[0] or "")[:28] if r else ""

    def vec_top5(q: str) -> list[dict]:
        """口径 A：与入库前基线**同一种做法**（纯向量近邻）。"""
        qv = embedder.embed_query(q)
        rows = conn.execute(
            "SELECT clause_revision_id FROM clause_vec WHERE embedding MATCH ? AND k = 5"
            " ORDER BY distance", (array.array("f", qv).tobytes(),)).fetchall()
        out = []
        for (cid,) in rows:
            # ⚠ `standard_no` 在 doc_meta，不在 clause_revision（第一版直接取 cr.standard_no ⇒
            #   `no such column`）。必须 JOIN。
            r = conn.execute(
                "SELECT dm.standard_no, cr.clause_number, substr(cr.content_text,1,60)"
                " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                " WHERE cr.clause_revision_id=?", (cid,)).fetchone()
            if r:
                out.append({"std": r[0] or "", "name": name_of(r[0] or ""),
                            "clause": r[1], "text": (r[2] or "").replace("\n", " ")})
        return out

    rows_out = []
    for qid, q in QUESTIONS:
        a = vec_top5(q)                                  # 口径 A
        try:
            hits = hybrid_engine.perform_hybrid_search(q, top_k=5)   # 口径 B（返回列表）
            b = [{"std": getattr(h, "standard_no", "") or "",
                  "clause": getattr(h, "clause_number", "") or "",
                  "name": name_of(getattr(h, "standard_no", "") or "")} for h in (hits or [])[:5]]
        except Exception as e:                                              # noqa: BLE001
            b = [{"error": f"{type(e).__name__}: {e}"}]
        base = before.get(qid, [])
        new_in_a = [x["std"] for x in a if x["std"] and x["std"] not in base]
        rows_out.append({"id": qid, "query": q, "before_top5_std": base,
                         "A_vec_top5": a, "B_hybrid_top5": b, "newly_appearing_vs_before": new_in_a})
        print(f"\n[{qid}] {q[:50]}", flush=True)
        print(f"   入库前(纯向量)  ：{base}", flush=True)
        print(f"   入库后(纯向量)  ：{[x['std'] for x in a]}", flush=True)
        if new_in_a:
            print(f"   ★ 新出现        ：{new_in_a}", flush=True)
        print(f"   入库后(六路融合)：{[(x.get('std'), x.get('clause')) for x in b]}", flush=True)

    OUT.write_text(json.dumps({
        "why": "入库验收：11 条真问题复测（两种口径，各自与自己的基线比）",
        "db": str(TRIAL_DB), "doc_meta": n_docs, "clause_revision": n_cl,
        "correction": "第一版误把 perform_hybrid_search 当字典用（它返回列表），11 条全 AttributeError；已修。",
        "A_baseline": "纯向量近邻，与 real-questions-result.json 同口径",
        "B_baseline": "无（六路融合本次首跑）",
        "rows": rows_out,
        "boundary": ["只看头部条目是否变化，未逐条判定'答对'；",
                     "副本仍用现役 bge-small 向量（E4 的换模型结论尚未上生产）。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
