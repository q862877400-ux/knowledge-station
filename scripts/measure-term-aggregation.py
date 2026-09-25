"""量「同名多定义怎么合并」的几种算法 —— P1 对齐的第二刀（**总账与个体变差一起看**）。

为什么需要这个脚本（2026-09-25）：上一批量出"同名定义全留、按名取**最大**"能把总账抬起来
（nonName 前5 8.6% → 12.8%、前50 25.7% → 33.4%、中位名次 386 → 186），
但**独立复核把它打回**了：我写的"数学上必然不劣"是**错的**——`max(A∪B) ≥ max(A)` 只管
**gold 的分数**，而该机制把**对手名的分数也一起抬高**⇒**名次会掉**。实测
**601/1,651（36.4%）变差、最差恶化 504 名**。⇒ 结论：**这是一次"总体涨、三成个体跌"的取舍**，
不能只看总账。

**本脚本就是给那次取舍要一个交代**，同时量两件事：
  · **总账**（前1/5/10/20/50、中位名次）——是否比默认好；
  · **个体**（相对默认：变好 / 不变 / 变差 条数、最差恶化多少名）——代价有多大。
并**按 gold 名下条目数分层**：**只有 1 条定义的说法**是干净的"受害侧"测量
（那些 gold 根本无法从合并里受益，名次只可能持平或掉）。

顺带治一个**已知的机制**：IR 里的老办法叫**长度归一化**——条目多的名字会有更高的"最大值机会"
（跟长文档在 BM25 里被抬高是同一件事）。所以除了 `max`，还量：
  · `mean`（名下条目的平均）
  · `top2`（名前两条的均值）
  · `max-log`（`max − α·ln(条目数)`，α 扫几个值，**扫一条曲线而不是挑一个数**——挑一个就是 p-hacking）

⚠ **不变量（脚本自己会校验）**：默认口径那一条向量 = 该名字在 keep-all 里的**第一条**条目
（2026-09-25 复核机械验过：余弦 1.000000000000）⇒ 本脚本的默认分**直接从同一个矩阵里取那一列**
算出，并从**默认缓存**再算一遍做**交叉对账**；两路不一致就报错（否则后面所有对比都不成立）。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-term-aggregation.py <说法 JSONL> [--batch 128]
只读真库 + 两份术语向量缓存。
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np                                          # noqa: E402

from src.core.retrieval import embedder                      # noqa: E402
from src.core.retrieval.term_bridge import (                  # noqa: E402
    TERM_ENTRY_RE, TermIndex,
)
from src.core.text_utils import segment_for_fts               # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
CACHE_FIRST = REPO / "var" / "tmp" / "term-index-full.json"      # 每名一条（首条定义）
CACHE_ALL = REPO / "var" / "tmp" / "term-index-keepall.json"     # 同名定义全留
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")
KS = (1, 5, 10, 20, 50)


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def _segment_max(sim, order, starts):
    return np.maximum.reduceat(sim[:, order], starts, axis=1)


def _segment_mean(sim, order, starts, counts):
    tot = np.add.reduceat(sim[:, order], starts, axis=1)
    return tot / counts


def _segment_top2(sim, order, starts, counts):
    """名前两条的均值。用"取最大 → **只掩掉取到最大值的那些位置** → 再取最大"两步做，避免整块排序。

    ⚠⚠ **这里写错过一次，而且错得很隐蔽**（2026-09-25 我自己发现的）：
    第一版写成 `mask = np.repeat(m1, counts) >= s`，即"最大值 ≥ 每条"——**恒为真**，
    于是把**所有**条目都掩掉了，`m2` 退化成 `-inf` 被 `m1` 兜住 ⇒ **`top2` 恒等于 `max`**。
    当时的输出里 `top2` 那一列与 `max` **每一格完全相同**——正是这个"太整齐"让我起了疑。
    ⚠ 教训：**一条规则与另一条规则给出逐格相同的结果，先怀疑自己的实现，别当成"这条规则没用"。**
    正确写法：掩掉 `s == m1` 的位置（比较方向反过来）。
    """
    s = sim[:, order]
    m1 = np.maximum.reduceat(s, starts, axis=1)
    mask = s >= np.repeat(m1, counts, axis=1)      # ← 只有取到最大值的那些位置
    s2 = np.where(mask, -np.inf, s)
    m2 = np.maximum.reduceat(s2, starts, axis=1)
    m2 = np.where(np.isfinite(m2), m2, m1)         # 单条名字 ⇒ 第二次没有可取的 ⇒ 用 m1
    return (m1 + m2) / 2.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("--batch", type=int, default=128)
    args = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover
            pass

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    idx_all = TermIndex.load(CACHE_ALL)
    idx_first = TermIndex.load(CACHE_FIRST)
    entries = idx_all.entries
    M = np.asarray(idx_all._matrix())                    # (n_entries, d) 已归一化
    names = sorted({e.term for e in entries})
    name_to_i = {n: i for i, n in enumerate(names)}
    name_id = np.asarray([name_to_i[e.term] for e in entries])
    counts = np.bincount(name_id, minlength=len(names))
    order = np.argsort(name_id, kind="stable")
    starts = np.searchsorted(name_id[order], np.arange(len(names)))
    # 每个名字的**首条**条目（= 默认口径用的那一条）
    _, first_of = np.unique(name_id, return_index=True)
    # ⚠⚠ 这里踩过一次坑（2026-09-25，由本脚本自己的对账抓住）：`first_of` 是按
    # **排序后的名字下标**排的，而**默认缓存**的条目是**库序** ⇒ 不能拿名字下标直接去索引它。
    # ⇒ 建"名字 → 默认缓存里的列号"映射，并对账换成**更强**的判据：**同一条条款**。
    first_pos = {e.term: i for i, e in enumerate(idx_first.entries)}
    print(f"候选：条目 {len(entries):,} → 术语名 {len(names):,}"
          f"（默认口径用每名首条，共 {len(idx_first)} 条）", flush=True)
    mismatched = [n for n in names
                  if first_pos.get(n) is None
                  or idx_first.entries[first_pos[n]].clause_revision_id
                  != entries[first_of[name_to_i[n]]].clause_revision_id]
    if mismatched:
        print(f"  ⛔ 不变量破了：{len(mismatched)} 个名字在「全留缓存的首条」与"
              f"「默认缓存的那条」之间**不是同一条条款**（例：{mismatched[:3]}）"
              f" —— 后面的对比不成立，停在这里")
        return 1
    print("  ✓ 不变量：每名的「首条」与默认缓存里那一条**是同一条条款**"
          f"（{len(names):,} 个名字全过）", flush=True)

    rows = [json.loads(l) for l in Path(args.cases).read_text(
        encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}
    def_words: dict[str, set[str]] = {}
    for (txt,) in conn.execute("SELECT content_text FROM clause_revision"):
        m = TERM_ENTRY_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in wanted:
            def_words.setdefault(t, set()).update(words(txt))
    tw = {r["term"]: words(r["term"]) for r in rows}
    groups: dict[str, list[tuple[str, str]]] = {"all": [], "nonName": [], "nonDef": []}
    for r in rows:
        t = r["term"]
        if t not in name_to_i or t not in def_words:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            groups["all"].append((t, tx))
            if not (words(tx) & tw[t]):
                groups["nonName"].append((t, tx))
            if not (words(tx) & def_words[t]):
                groups["nonDef"].append((t, tx))
    print("；".join(f"{g} {len(v)} 条" for g, v in groups.items()), flush=True)

    def rules_of(sim):
        """一批查询 → {规则名: (n_q, n_names) 分数矩阵}"""
        out = {"default": sim[:, first_of],
               "max": _segment_max(sim, order, starts),
               "mean": _segment_mean(sim, order, starts, counts),
               "top2": _segment_top2(sim, order, starts, counts)}
        mx = out["max"]
        for a in (0.01, 0.02, 0.04, 0.08):
            out[f"max-log(a={a})"] = mx - a * np.log(counts)[None, :]
        return out

    for g, cs in groups.items():
        if not cs:
            continue
        t0 = time.time()
        Q = np.asarray([embedder.embed_query(tx) for _t, tx in cs], dtype=np.float64)
        Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
        gold = np.asarray([name_to_i[t] for t, _tx in cs])
        gcount = counts[gold]

        acc: dict[str, list[np.ndarray]] = {}
        ref_default: list[np.ndarray] = []
        for i in range(0, len(Q), args.batch):
            sim = Q[i:i + args.batch] @ M.T
            for k, v in rules_of(sim).items():
                acc.setdefault(k, []).append(v)
            # 交叉对账：默认分从**默认缓存**再算一遍
            ref_default.append(Q[i:i + args.batch] @ np.asarray(idx_first._matrix()).T)
        R = {k: np.vstack(v) for k, v in acc.items()}
        Rref = np.vstack(ref_default)
        d1 = R["default"][np.arange(len(cs)), gold]
        gold_ref = np.asarray([first_pos[t] for t, _ in cs])      # 默认缓存里的**列号**
        d2 = Rref[np.arange(len(cs)), gold_ref]
        if not np.allclose(d1, d2, atol=1e-6):
            print(f"  ⛔ 交叉对账失败：默认分两路不一致（max|Δ|={np.abs(d1-d2).max():.3e}）"
                  f" —— 后面的对比不成立，停在这里")
            return 1
        rank = {k: (v > v[np.arange(len(cs)), gold][:, None]).sum(axis=1) + 1
                for k, v in R.items()}
        base = rank["default"]

        print()
        print("=" * 100)
        print(f"组={g}，{len(cs)} 条说法   （候选＝全库 {len(names):,} 个术语名；"
              f"交叉对账 max|Δ|={np.abs(d1-d2).max():.2e} ✓）")
        print("=" * 100)
        print(f"{'合并算法':<18}{'前1':>7}{'前5':>7}{'前10':>7}{'前20':>7}{'前50':>7}"
              f"{'中位':>7}  {'变好':>6}{'不变':>6}{'变差':>7}{'最差恶化':>9}")
        for k in R:
            r = rank[k]
            line = "".join(f"{np.mean(r <= K):7.1%}" for K in KS)
            if k == "default":
                print(f"{k:<18}{line}{int(np.median(r)):>7}  {'—':>6}{'—':>6}{'—':>7}{'—':>9}")
                continue
            better = int((r < base).sum())
            same = int((r == base).sum())
            worse = int((r > base).sum())
            worst = int((r - base).max())
            print(f"{k:<18}{line}{int(np.median(r)):>7}  {better:>6}{same:>6}{worse:>7}{worst:>9}")

        # 分层：gold 名下只有 1 条定义的那些 —— 干净的"受害侧"
        for lo, hi, lab in ((1, 1, "gold 只有 1 条定义"), (2, 3, "gold 2~3 条"),
                            (4, 7, "gold 4~7 条"), (8, 10 ** 9, "gold 8+ 条")):
            sel = (gcount >= lo) & (gcount <= hi)
            if not sel.any():
                continue
            print(f"  --- {lab}（{int(sel.sum())} 条）")
            for k in ("max", "mean", "top2", "max-log(a=0.02)"):
                r = rank[k][sel]
                b = base[sel]
                print(f"      {k:<16} 前5 {np.mean(r <= 5):5.1%}（默认 {np.mean(b <= 5):5.1%}）"
                      f"  变好 {int((r < b).sum()):>4} / 变差 {int((r > b).sum()):>4}"
                      f"  最差 {int((r - b).max()):>4} 名")
        print(f"  （{time.time()-t0:.0f}s）")

    print()
    print("  ⚠ 读法：**总账与个体一起看**。一个「总账涨、三成个体跌」的算法不能只报总账；")
    print("     本仓对「只报总账」是有先例教训的。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
