"""量 P1 的**主判据**：语义有界选择"选对术语"的 top-1 / top-5（**入库的复算脚本**）。

为什么要有这个脚本（2026-09-25，独立复核指出）：
计划的 P1 把「从术语表有界选择选对术语的比例（top-1/top-5）」定成**主判据**，
命令却指向 `measure-term-bridge.py --all` —— 而**那个脚本根本不产出这个量**
（它只印条款级命中与术语级命中）。⇒ 主判据当时**不能从仓里复算**，只有
gitignored 的探针支撑。这个脚本把它补上。

量什么：对每一条大白话，算**真术语**在语义排序里的名次
（名次 = 比它分高的候选个数 + 1），分两档候选集报：
  · `500`      = 说法文件里出现过的那些术语（**就是那 500 个答案术语本身**，最乐观上界）
  · `全库`     = 库内全部术语（实测 42,181，**真实口径**）
并给 top-1 / top-5 / top-10 / top-20 / top-50 与中位名次。

⚠ **候选集是这条判据的主要变量**：500 → 42,181 之间 top-5 从 47.3% 掉到 8.6%。
   报这个数**必须**同时说候选集多大，否则等于报了一个不存在的结论。

⚠ 同时按**两个档位口径**分组（都在 `--group` 里印）：
  · `nonName` 非**术语名**重合（1,651）—— 复算脚本一直用的口径
  · `nonDef`  非**定义条款正文**重合（1,078）—— 真正的零重合集
  两者不是一回事（实测 573 条只被后者判为重合），分组数会不一样。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-term-selection.py <说法 JSONL> [--limit N]
只读真库。术语向量从缓存读（`var/tmp/term-index-full.json`），没有就现场重建（约 531s）。
"""
from __future__ import annotations

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
CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover - 环境相关
            pass
    src = Path(sys.argv[1])
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    keep_all = "--keep-all" in sys.argv

    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    t0 = time.time()
    if CACHE.exists():
        index = TermIndex.load(CACHE)
        print(f"术语表：缓存读入 {len(index)} 条（{time.time()-t0:.0f}s）", flush=True)
    else:
        index = TermIndex.build(conn)
        index.save(CACHE)
        print(f"术语表：建成 {len(index)} 条并缓存（{time.time()-t0:.0f}s）", flush=True)

    terms = [e.term for e in index.entries]
    names_set = set(terms)          # 分组阶段只判"在不在"，不用名次（名次在下面按候选表示定）

    # 两个档位口径：与**术语名**重合 / 与**定义条款正文**重合
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
        if t not in names_set or t not in def_words:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            name_hit = bool(words(tx) & tw[t])
            def_hit = bool(words(tx) & def_words[t])
            groups["all"].append((t, tx))
            if not name_hit:
                groups["nonName"].append((t, tx))
            if not def_hit:
                groups["nonDef"].append((t, tx))
    if limit:
        for g in groups:
            groups[g] = groups[g][:limit]
    print("；".join(f"{g} {len(v)} 条" for g, v in groups.items()), flush=True)

    # ── 候选表示：默认＝每术语名一个向量（**首条定义**）；`--keep-all`＝同名定义全留 ──
    # 为什么要这个开关（2026-09-25 独立标签审计点名）：本脚本判"选对没有"时，
    # **靶子**（分组用的 `def_words`）聚合了该术语**全部同名定义**的用词，而**向量**只用了
    # **第一条**定义 ⇒ **靶子比向量宽，两个数不是一把尺子量的**。
    # `--keep-all` 把同名条目全当候选、**按术语名取最大相似度**（不是 oracle 偷看答案，
    # 是让"哪条定义更贴这句话"由相似度自己决定）⇒ 靶子与向量同宽。
    if keep_all:
        cand_terms, M, vec_order, starts, n_names = _keep_all_candidates(conn)
    else:
        cand_terms, M, vec_order, starts, n_names = list(terms), None, None, None, len(terms)
    pos_of = {t: i for i, t in enumerate(cand_terms)}
    narrow = np.asarray([i for i, t in enumerate(cand_terms) if t in wanted])
    print(f"候选集：收窄 {len(narrow)} 条 / 全库 {len(cand_terms)} 条"
          f"{'（同名定义全留，按名取最大）' if keep_all else ''}", flush=True)

    # 一次矩阵乘算完全部名次：真术语的名次 = 比它分高的候选个数 + 1
    for g, cs in groups.items():
        if not cs:
            continue
        t1 = time.time()
        Q = np.asarray([embedder.embed_query(tx) for _t, tx in cs], dtype=np.float64)
        Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
        if keep_all:
            R = _name_level_scores(Q, M, vec_order, starts, n_names)
        else:
            R = Q @ index._matrix().T
        gold = np.asarray([pos_of[t] for t, _tx in cs])
        gs = R[np.arange(len(cs)), gold]
        print()
        print("=" * 78)
        print(f"选对术语的名次（组={g}，{len(cs)} 条说法）")
        print("=" * 78)
        for label, cols in (("500 口径（500 个答案术语）", narrow),
                            (f"全库口径（{len(cand_terms)} 个术语）", None)):
            sub = R if cols is None else R[:, cols]
            n_c = len(cand_terms) if cols is None else len(cols)
            rank = (sub > gs[:, None]).sum(axis=1) + 1
            line = "  ".join(f"前{k} {np.mean(rank <= k):5.1%}" for k in (1, 5, 10, 20, 50))
            print(f"  {label:<28}{line}")
            print(f"  {'':<28}中位名次 {int(np.median(rank))} / {n_c}"
                  f"（随机 {n_c//2}）")
        print(f"  （嵌入+排序 {time.time()-t1:.0f}s）")
    print()
    print('  ⚠ 引用时**必须**带上「哪一档候选集 + 哪一组分母」，两个都会把结论差出一个量级。')
    return 0


#: `--keep-all` 的向量缓存（**与默认那份分开存**，别把默认口径的缓存覆盖掉）
CACHE_KEEP_ALL = REPO / "var" / "tmp" / "term-index-keepall.json"


def _keep_all_candidates(conn):
    """同名定义全留的候选：返回 `(术语名列表, 逐条目矩阵, 排序后的条目下标, 各名起点, 名数)`。

    计分口径：**术语名的分数 = 它名下所有条目相似度的最大值**——即"让相似度自己挑
    哪条定义更贴这句话"。⚠ 这**不是**审计里的 oracle 上界（那个挑定义时看了答案）。
    """
    from src.core.retrieval import embedder
    from src.core.retrieval.term_bridge import extract_term_entries

    if CACHE_KEEP_ALL.exists():
        idx = TermIndex.load(CACHE_KEEP_ALL)
        entries = idx.entries
        vecs = np.asarray(idx.vectors)
    else:
        entries = extract_term_entries(conn, keep_all=True)
        # ⚠ 精度**对齐默认路径**（那份是 `embed_batch` 的 float32）——否则两跑不可比
        vecs = np.asarray(embedder.embed_batch([e.definition for e in entries]))
        TermIndex(entries=entries, vectors=vecs.tolist()).save(CACHE_KEEP_ALL)
    names = sorted({e.term for e in entries})
    # ⚠ 必须走字典：`names.index(...)` 是每条 O(名数)，48,524 × 42,181 ≈ 20 亿次（实测会卡死）
    name_to_i = {n: i for i, n in enumerate(names)}
    name_id = np.asarray([name_to_i[e.term] for e in entries])
    order = np.argsort(name_id, kind="stable")
    starts = np.searchsorted(name_id[order], np.arange(len(names)))
    print(f"同名定义全留：条目 {len(entries):,} → 术语名 {len(names):,}"
          f"（默认口径丢掉 {len(entries)-len(names):,} 条同名定义）", flush=True)
    return names, vecs, order, starts, len(names)


def _name_level_scores(Q, vecs, order, starts, n_names, batch=256):
    """按名取最大相似度。**分批算**：全量一次是 (1832 × 48k) 的 float64，会吃掉 GB 级内存。"""
    out = np.empty((len(Q), n_names), dtype=np.float64)
    for i in range(0, len(Q), batch):
        sim = Q[i:i + batch] @ vecs[order].T                  # (b, 条目数)
        out[i:i + batch] = np.maximum.reduceat(sim, starts, axis=1)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
