"""P2「排序」诊断（第 1 步）：**先量"为什么排不上去"，不改任何东西**。

## 依据（总纲 §P2 原文）
> **要解决的事**：有东西可对，但排不上去。
> **证据**：47.0% 的说法与原文有重合，**只有 4.4% 进前五**（38/861）。
> **做什么**：**先诊断、后改法**。按可能性排查：通道权重（`exact=2.0` 是六路最高，会不会压过其他路）
> → RRF 常数 → BM25 参数 → 片段长度差异（长条款天然吃亏？）→ 同号条款过多时的次序。

## 本脚本量什么（全部来自**已落盘的逐条结果**，不碰跑分器、不碰库）
 ① **L2 那批**（六路 1000 条并集里**有** gold，但**融合后进不了前 20**）到底有多少、gold 落在第几名；
 ② 这些案子里**哪些通道命中了**（含独家命中）—— 用来验"通道权重压过其他路"这个假设；
 ③ 三个假设的**初步可检信号**：
    · **片段长度**：L2 的 gold 条款是不是比 L0（进得了前 8）的更长？长条款在 RRF 里天然吃亏？
    · **同号条款**：gold 的标准号在库里是不是有很多同号文档（"同号条款过多时的次序"）？
    · **候选池大小**：L2 的 FTS 候选池是不是特别大（池大 ⇒ 名次被稀释）？

⚠ 本脚本**只读**，不写库、不改代码。输出供下一步写止损线用。

用法： .venv\\Scripts\\python.exe tools\\p2-diagnose.py [--data eval/recall-funnel/regression-ingest/funnel-per-query-before.jsonl]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "eval" / "recall-funnel" / "regression-ingest" / "funnel-per-query-before.jsonl"
OUT = ROOT / "eval" / "recall-funnel" / "p2-diagnose.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    rows_all = [json.loads(l) for l in Path(args.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[p2] 读入 {len(rows_all)} 条逐条结果：{Path(args.data).name}")

    # ⚠ **子集也要照 `summarize.py` 的口径**：报告里的分诊是 **headline 120 条**，不是全部 171。
    #   差在这里：我第一版拿 171 条算得 L1=104/L2=48，与报告的 L1=72/L2=33 对不上 ——
    #   **是子集不同，不是定义不同**。原式见 `eval/recall-funnel/summarize.py`：
    #     headline = [r for r in rows if r["bucket"]=="keep"
    #                 and not ({"gold_multi_def","gold_dup_text"} & set(r["flags"]))]
    _EXCLUDE = {"gold_multi_def", "gold_dup_text"}
    rows = [r for r in rows_all
            if r.get("bucket") == "keep" and not (_EXCLUDE & set(r.get("flags") or []))]
    print(f"[p2] headline 子集 = {len(rows)} 条（全部 {len(rows_all)} 条）"
          f" —— **报告里的分诊用的是这个子集**")

    # ⚠ **分档必须用 `summarize.py` 的原定义，不许自己另立一套**
    #   （本仓最忌"同一概念两个数"。我第一版用 `fused.hit@20` 分 L0/L2，
    #    算出 L2=4/L3=48，与报告里的 L2=33/L3=4 对不上 —— 那就是我另立了口径。）
    #   原定义（`eval/recall-funnel/summarize.py`）：
    #     deep1000 = union.same_budget["@1000"]   ← 并集口径，不是融合口径
    #     same20   = union.same_budget["@20"]
    #     fused20  = fused.hit@20
    #     rank8    = fused.gold_rank 不为空且 <= 8
    L0, L1, L2, L3, L4 = [], [], [], [], []
    for r in rows:
        u = r["union"]["same_budget"]
        deep1000 = bool(u.get("@1000"))
        same20 = bool(u.get("@20"))
        fused20 = bool(r["fused"].get("hit@20"))
        gr = r["fused"].get("gold_rank")
        rank8 = gr is not None and gr <= 8
        if not deep1000:
            L1.append(r)
        elif not same20:
            L2.append(r)
        elif not fused20:
            L3.append(r)
        elif not rank8:
            L4.append(r)
        else:
            L0.append(r)
    print(f"[p2] 分档（**照 `summarize.py` 原定义**）：")
    print(f"      L0 进得了用户看的 8 条   = {len(L0)}")
    print(f"      L1 六路深读1000都没召回  = {len(L1)}")
    print(f"      L2 要读到20条以外才够得着 = {len(L2)}   ← ★ 并用集口径")
    print(f"      L3 并集里有_融合后掉了    = {len(L3)}   ← ★")
    print(f"      L4 融合前20但没进8条      = {len(L4)}")
    target = L2 + L3 + L4
    print(f"[p2] ★ 本次诊断对象 = L2+L3+L4 = **{len(target)} 条**"
          f"（占 {len(target)/max(1,len(rows)):.1%}）—— 它们**已经在候选池里**，只差排上去")

    if not target:
        print("[p2] 没有可诊断的对象")
        return 0

    # ① gold 在融合里的名次分布
    ranks = [r["fused"]["gold_rank"] for r in target if r["fused"].get("gold_rank")]
    if ranks:
        print(f"\n[①] gold 在融合结果里的名次：中位 {int(st.median(ranks))}、"
              f"最小 {min(ranks)}、最大 {max(ranks)}")
        for lo, hi in ((21, 50), (51, 100), (101, 500), (501, 10**9)):
            n = sum(1 for x in ranks if lo <= x <= hi)
            if n:
                print(f"      {lo}~{hi if hi < 10**9 else '∞':>4} 名：{n} 条")

    # ② 哪些通道命中（含独家）
    ch_cnt = Counter()
    exclusive = Counter()
    for r in target:
        hit = r.get("hit_channels") or []
        for c in hit:
            ch_cnt[c] += 1
        if len(hit) == 1:
            exclusive[hit[0]] += 1
    print(f"\n[②] 这些案子里各通道命中次数（一条可多路命中）：")
    for c, n in ch_cnt.most_common():
        print(f"      {c:16s} {n:4d}")
    print(f"    独家命中（只有这一路有）：{dict(exclusive)}")

    # ③ 候选池大小
    # ⚠ `fts_pool` 在逐条结果里是**整数**（不是 dict）——第一版按 dict 取 median 报了
    #   `TypeError: 'int' object is not subscriptable`。就地更正。
    pools = [r["fts_pool"] for r in target if isinstance(r.get("fts_pool"), int)]
    allp = [r["fts_pool"] for r in rows if isinstance(r.get("fts_pool"), int)]
    if pools:
        print(f"\n[③] FTS 候选池中位数：目标组 {int(st.median(pools))}"
              f"  vs  全体 {int(st.median(allp))}（池越大，名次越容易被稀释）")

    # ④ 每一路各自的名次（看是不是"被某一路压住"）
    print(f"\n[④] 目标组里，每一路自己给出的 gold 名次（中位；None=该路没有）")
    for c in ("exact", "fts", "vec", "modality", "legal_element", "behavior_scope"):
        arr = []
        for r in target:
            d = (r.get("channels") or {}).get(c) or {}
            g = d.get("gold_rank")
            if g:
                arr.append(g)
        if arr:
            print(f"      {c:16s} 有 gold 的 {len(arr):3d}/{len(target)}  中位名次 {int(st.median(arr))}")
        else:
            print(f"      {c:16s} 全部没有")

    OUT.write_text(json.dumps({
        "why": "P2 排序诊断第 1 步：量'为什么排不上去'，不改任何东西",
        "data": str(args.data),
        "triage": {"L0": len(L0), "L1": len(L1), "L2": len(L2), "L3": len(L3)},
        "targets": [{"i": r["i"], "gold_std": r["gold_std"], "gold_clause": r["gold_clause"],
                     "query": r["query"][:80],
                     "fused_rank": r["fused"].get("gold_rank"),
                     "hit_channels": r.get("hit_channels")} for r in target],
        "channel_hits": dict(ch_cnt), "exclusive": dict(exclusive),
        "boundary": ["只读已落盘结果；未改代码、未写库。",
                     "这批数据是**入库前**的库（522k 条）；入库后再量一遍看有没有变。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[p2] 已写 {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
