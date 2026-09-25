# -*- coding: utf-8 -*-
"""量「同名定义全留、按名取最大」的**受害侧**，并算出**盈亏平衡点**（P1 决策的关键数）。

## 为什么要有它（接 P1 第三刀）

那套评测基准**说不出**"对典型目标会怎样"——基准里 500 个答案术语
**100% 是多定义的**（平均 2.97 条），而真实库里只有 **9.0%** 的名字有 ≥2 条定义
⇒ 基准上量到的涨幅（前5 8.6% → 12.8%）**不可外推**，决策卡住。

**换加权解决不了**：要按总体分布加权，就得有"答案术语只有 1 条定义"那一层的数，
而基准里**那一条都没有**（0 条）。

## 本办法：反事实，**不需要任何新语料**

对**同一批真问题**（仓库外的说法集）算三个名次：

* `default`：每名只用**第一条**定义的分数 —— 现状。
* `keepall`：每名取**名下所有条目的最大值** —— 被量出的那个改动。
* `victim`：**假设目标只有一条定义**（它的分数固定 = 第一条定义的分数，**一点好处都拿不到**），
  而**对手**仍用「取最大」。

⇒ `victim` 把"目标无法受益、只有对手被抬高"这一侧单独拎出来；它与 `default` 的差
**就是纯粹的害处**，且与查询难度无关（同一条问题、同一批对手）。
⇒ 这正是真实里**约 91% 的目标**所处的情形。

⚠ 内部一致性（脚本不打印、但结论依赖它）：因为目标分数不变、对手分数只升，
  `victim` 的名次**不可能比 `default` 好** ⇒ 若出现"变好"，说明实现错了。

## 结论（2026-09-25 实测，1,832 条说法）

* 受害侧：前5 **9.7% → 9.1%**、前50 **27.9% → 27.0%**、中位名次 **322 → 346**；
  逐条 **变好 0 / 不变 255 / 变差 1,577（86%）**，最差掉 **527 名**。
* **盈亏平衡点**：真实目标里"多条定义"的比例要到 **前5 s≈11.2% / 前20 9.6% / 前50 10.5%**
  这个改动才不亏；而两个候选加权是 **按名字 9.0%** 与 **按条目 20.9%** —— **平衡点正好卡在中间**。
* ⇒ **正负号取决于一个没量过的量**（真实用户问的目标里有多少是多定义的）。
  **现有数据回答不了它，这正是必须重建评测集（或先攒真实提问分布）的理由。**

⚠ **它不预测生产命中率**：它回答"这个改动对拿不到好处的目标会不会害、害多少"。
⚠ 单条那一档的数来自**反事实**（基准里 0 条单条目标），属**假设 + 实测对手**，
  不是实测的单条目标表现——引用时必须带上这句。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-term-victim-side.py
只读术语向量缓存（`var/tmp/term-index-keepall.json`；没有就先跑
`measure-term-selection.py <说法集> --keep-all` 把它建出来）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]      # 本脚本住在 scripts/ ⇒ 上一级是仓库根
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np                                          # noqa: E402

from src.core.retrieval import embedder                      # noqa: E402
from src.core.retrieval.term_bridge import TermIndex         # noqa: E402

CACHE_ALL = REPO / "var" / "tmp" / "term-index-keepall.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"
KS = (1, 5, 10, 20, 50)
BATCH = 128


def main() -> int:
    idx = TermIndex.load(CACHE_ALL)
    entries = idx.entries
    M = np.asarray(idx._matrix())
    names = sorted({e.term for e in entries})
    name_to_i = {n: i for i, n in enumerate(names)}
    name_id = np.asarray([name_to_i[e.term] for e in entries])
    counts = np.bincount(name_id, minlength=len(names))
    order = np.argsort(name_id, kind="stable")
    starts = np.searchsorted(name_id[order], np.arange(len(names)))
    _, first_of = np.unique(name_id, return_index=True)

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [(r["term"], x.get("text") if isinstance(x, dict) else x)
             for r in rows for x in (r.get("lay") or [])]
    cases = [(t, tx) for t, tx in cases if t in name_to_i and tx]
    gold = np.asarray([name_to_i[t] for t, _ in cases])
    gcount = counts[gold]

    n1 = int((counts == 1).sum())
    pop_name_w = 1.0 - int((counts >= 2).sum()) / len(counts)
    pop_entry_w = n1 / float(counts.sum())
    print(f"总体：术语名 {len(names):,}，条目 {counts.sum():,}")
    print(f"  按**名字**加权：单条定义的名字占 {pop_name_w:.1%}（于是多条占 {1-pop_name_w:.1%}）")
    print(f"  按**条目**加权（= 若提问均匀落在条款上）：单条占 {pop_entry_w:.1%}"
          f"（多条占 {1-pop_entry_w:.1%}）")
    print(f"本批问题 {len(cases):,} 条；其中答案术语**只有 1 条定义**的："
          f"{int((gcount == 1).sum())} 条")
    print()

    R_default, R_keep, R_victim = [], [], []
    t0 = time.time()
    for i in range(0, len(cases), BATCH):
        qs = [tx for _t, tx in cases[i:i + BATCH]]
        Q = np.asarray([embedder.embed_query(q) for q in qs], dtype=np.float64)
        Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
        sim = Q @ M.T
        mx = np.maximum.reduceat(sim[:, order], starts, axis=1)
        first = sim[:, first_of]
        R_keep.append(mx)
        R_default.append(first)
        # 反事实：gold 的分**固定成第一条定义**的分，但对手的分数用"取最大"
        # 做法：把矩阵整体换成 mx，再把 gold 那一列换回它的第一条定义分
        v = mx.copy()
        idx_b = np.arange(len(qs))
        v[idx_b, gold[i:i + BATCH]] = first[idx_b, gold[i:i + BATCH]]
        R_victim.append(v)

    Rk = np.vstack(R_keep)
    Rd = np.vstack(R_default)
    Rv = np.vstack(R_victim)
    n = len(cases)
    ar = np.arange(n)

    def rank(R):
        return (R > R[ar, gold][:, None]).sum(axis=1) + 1

    rk, rd, rv = rank(Rk), rank(Rd), rank(Rv)

    print("=" * 92)
    print(f"{'口径':<26}{'前1':>7}{'前5':>7}{'前10':>7}{'前20':>7}{'前50':>7}{'中位':>8}")
    print("=" * 92)
    for lab, r in (("现状（每名首条定义）", rd),
                   ("全留·按名取最大", rk),
                   ("**反事实：目标拿不到好处**", rv)):
        line = "".join(f"{np.mean(r <= K):7.1%}" for K in KS)
        print(f"{lab:<26}{line}{int(np.median(r)):>8}")

    print()
    print("相对现状的名次变化（正=变差）：")
    for lab, r in (("全留·按名取最大", rk), ("反事实：拿不到好处", rv)):
        d = r - rd
        print(f"  {lab:<20} 变好 {int((d < 0).sum()):>5} / 不变 {int((d == 0).sum()):>5} / "
              f"变差 {int((d > 0).sum()):>5}  最差 {int(d.max()):>5} 名  中位变化 {int(np.median(d)):>4}")

    print()
    print("=" * 92)
    print("**加权到总体**（把两档按真实比例混合；反事实那一档代表单条定义的目标）")
    print("=" * 92)
    for lab, w_single in (("按名字加权（单条占 %.1f%%）" % (pop_name_w * 100), pop_name_w),
                          ("按条目加权（单条占 %.1f%%）" % (pop_entry_w * 100), pop_entry_w)):
        # 基准：所有目标都用现状口径
        # 改动：单条目标用反事实、多条目标用全留 —— 但本批问题里**没有单条目标**，
        #       所以单条那一档的数**只能来自反事实**（assumption，已标注）
        print(f"  {lab}")
        for K in (5, 20, 50):
            base_hit = float(np.mean(rd <= K))
            new_hit = (w_single * float(np.mean(rv <= K))
                       + (1 - w_single) * float(np.mean(rk <= K)))
            print(f"    前{K:<3} 现状 {base_hit:5.1%} → 加权后 {new_hit:5.1%}"
                  f"（变化 {new_hit - base_hit:+.1%}）")
    print()
    print("=" * 92)
    print("**盈亏平衡点**：真实目标里要有多少比例是「多条定义」，这个改动才不亏？")
    print("=" * 92)
    # 设真实目标里"多条定义"的比例为 s：单条那一档用反事实、多条那一档用全留
    for K in (5, 20, 50):
        single_hit = float(np.mean(rv <= K))
        multi_hit = float(np.mean(rk <= K))
        base_hit = float(np.mean(rd <= K))
        denom = (multi_hit - single_hit)
        if abs(denom) < 1e-12:
            continue
        s_be = (base_hit - single_hit) / denom
        print(f"  前{K:<3} 单条档 {single_hit:5.1%} / 多条档 {multi_hit:5.1%} / 现状 {base_hit:5.1%}"
              f" ⇒ **盈亏平衡在 s ≈ {s_be:5.1%}**")
    print()
    print("  两个已知的候选加权：按**名字**加权 s=9.0%；按**条目**加权 s=20.9%。")
    print("  ⇒ 若平衡点落在两者**之间**，那么「该不该上」**取决于一个我们没量过的量**"
          "（真实用户问的目标里有多少是多条的）——")
    print("     **现有数据回答不了它，而这正是必须重建评测集的理由。**")
    print()
    print("⚠ 读法：**单条定义那一档的数来自反事实**（本批问题里 0 条单条目标），"
          "属**假设 + 实测对手**，不是实测的单条目标表现。")
    print("⚠ 它回答的是「对拿不到好处的目标会不会害、害多少」，"
          "**不是**「生产命中率会是多少」。")
    print(f"（{time.time()-t0:.0f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
