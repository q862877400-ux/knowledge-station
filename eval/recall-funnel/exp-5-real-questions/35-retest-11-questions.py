"""入库验收：拿业主那 **11 条真实提问**复测，与"入库前"对照。

## 为什么这是验收标准（目标 ④）
光有条款数不算数。业主最初的 11 条真问题里，有好几条**当时的库里根本没有对应资料**
（例：职业病防治法、环境保护法、行政处罚法、特种设备安全法、社会保险法**全部不在库**；
易制毒化学品条例、职业危害评价类标准也缺）。**只有在这些问题上答得出来，才算真补上了。**

## 对照基线
`real-questions-result.json`（入库前跑的那次，真库只读）记录了每题的 `old_model_top5`。
本次在**副本**上跑同一套检索，比较"返回的标准号是否变了、缺的那本有没有出现"。

## 走生产检索
`hybrid_engine.set_db_override(副本)` + `perform_hybrid_search(q)` —— 与生产同一套六路融合，
**不是另写一套**。

只读副本；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\35-retest-11-questions.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "retest-11-questions-after-ingest.json"
TRIAL_DB = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"
BEFORE = HERE / "real-questions-result.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(ROOT))

#: 与 01-probe-real-questions.py 同一批（业主原话，一字不改）
QUESTIONS = [
    ("r1", "我要做高处作业了，我不知道我这个作业是到底算几级，我应该遵守那些规定", ["GB 30871", "高处作业"]),
    ("r2", "我们买了一个有毒气体的探头，但是安装我不知道装什么位置比较合适", ["气体探测", "报警"]),
    ("r3", "我们厂现在打算去重新修一个厂房，但是我不知道修这个厂房需要考虑哪些法律法规或者国家标准上的问题", ["GB 50016", "建设项目"]),
    ("r4", "我们施工的时候能不能关闭消防报警系统呢？那个国标法规上是怎么要求的", ["火灾自动报警", "消防"]),
    ("r5", "我们这个易制毒化学品仓库，到底要符合哪些要求才行？我怎么去自查有没有违规项", ["易制毒"]),
    ("r6", "我们企业是一般工贸企业，光刻机制造企业，在手续证照方面，我们要办哪些手续？安全环保的手续都要说", ["安全评价", "排污许可"]),
    ("r7", "我们工厂里的岗位，哪些岗位要做职业健康体检，哪些不用这个东西，我怎么去判断", ["GBZ 188"]),
    ("r8", "我们公司有些人，他不愿意参加职业健康体检，但是法律法规要求公司必须要给他们做体检，那这种情况冲突了怎么去解决呢", ["GBZ 188"]),
    ("r9", "如果说这个我们公司因为一些工艺调整，现在要增加一个职业危害因素，那我应该怎么去做才能保证不管是从现场还是体检还是其他方面都能合规呢", ["职业病危害", "危害因素"]),
    ("r10", "我要签租房合同，里面说这个我要半年一付，然后还要付一个月押金，如果我没有租满一年的话，押金不退，像这种条款是不是合法呢", ["民法典"]),
    ("r11", "我看到有的企业和供应商签的安全协议里面说，如果是供应商因为自己违章导致的事故的，那甲方不负任何责任，这到底合不合法", ["安全生产法", "民法典"]),
]


def main() -> int:
    if not TRIAL_DB.exists():
        print(f"⛔ 副本库不在：{TRIAL_DB}")
        return 1
    import sqlite3
    from src.core.retrieval import hybrid_engine
    from src.core.storage.sqlite_db import load_vec_extension

    # 生产检索指向副本（eval 专用开关）
    hybrid_engine.set_db_override(TRIAL_DB)
    conn = sqlite3.connect(f"file:{TRIAL_DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    print(f"[retest] 副本：doc_meta={conn.execute('SELECT COUNT(*) FROM doc_meta').fetchone()[0]} "
          f"clause_revision={conn.execute('SELECT COUNT(*) FROM clause_revision').fetchone()[0]}", flush=True)

    before = {}
    if BEFORE.exists():
        for x in json.loads(BEFORE.read_text(encoding="utf-8"))["questions"]:
            before[x["id"]] = [r["std"] for r in x.get("old_model_top5", [])]

    rows = []
    for qid, q, hints in QUESTIONS:
        try:
            res = hybrid_engine.perform_hybrid_search(q, top_k=5)
            hits = res.get("results") or res.get("hits") or []
        except Exception as e:                                              # noqa: BLE001
            print(f"    {qid} ⛔ {type(e).__name__}: {e}", flush=True)
            rows.append({"id": qid, "query": q, "error": f"{type(e).__name__}: {e}"})
            continue
        # ⚠ `perform_hybrid_search` 返回的是 `List[ClauseRevisionModel]`（**对象**，不是 dict），
        #   所以用 getattr；标准名要另查 doc_meta（条款模型上没有）。
        now = []
        for h in hits[:5]:
            no = getattr(h, "standard_no", None) or ""
            cn = getattr(h, "clause_number", None) or ""
            nm = ""
            if no:
                r = conn.execute("SELECT standard_name FROM doc_meta WHERE standard_no=? LIMIT 1",
                                 (no,)).fetchone()
                nm = (r[0] or "")[:30] if r else ""
            now.append({"std": no, "name": nm, "clause": cn,
                        "text": (getattr(h, "content_text", "") or "")[:70].replace("\n", " ")})
        b = before.get(qid, [])
        new_std = [x["std"] for x in now if x["std"] and x["std"] not in b]
        rows.append({"id": qid, "query": q, "hints": hints, "before_top5_std": b,
                     "after_top5": now, "std_newly_appearing": new_std})
        print(f"\n[{qid}] {q[:52]}", flush=True)
        print(f"    入库前：{b}", flush=True)
        print(f"    入库后：{[x['std'] for x in now]}", flush=True)
        if new_std:
            print(f"    ★ 新出现的：{new_std}", flush=True)

    OUT.write_text(json.dumps({
        "why": "入库验收：11 条真问题复测（对照入库前）",
        "db": str(TRIAL_DB),
        "note": "走生产检索 hybrid_engine（set_db_override 指向副本），不是另写一套。",
        "rows": rows,
        "boundary": ["只看返回的头部条目是否变化，未逐条判定'是否答对'；",
                     "检索质量另受 E4 那个'换嵌入模型'结论影响（本副本仍是现役 bge-small 向量）。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
