"""量「术语桥」（第 2 步翻译层）的端到端效果 —— **入库的复算脚本**。

为什么要有这个脚本（2026-09-25）：本会话有一条分支由另一个 AI 接手，
它把"翻译臂前 20 涨 4.53 倍"写进了文档，**但没提交任何实现**，那些数字
**不能从仓里复算**。本脚本 + `src/core/retrieval/term_bridge.py` 把这件事补齐。

量什么（非 A 子集＝与术语定义条款**没有词级重合**的那些大白话，它们才是要救的）：
  A 基线    ：大白话直接按字找
  B 桥·顺序 ：语义选 k 个术语 → 各查一次 → **顺序拼接**
  B 桥·轮转 ：同上，但**轮转交错**合并（`merge_round_robin`）
并同时给**术语级**（任一说法命中即算）。

⚠ **两个分母都印**（非 A 子集 / 全部说法）：非 A 的基线按定义接近 0 ⇒ 倍数被放大，
只报一个就是把最难子集当整体（另一条分支漏了这句，把 2.76× 写成了 4.53×）。

⚠ **候选集大小是主要变量，必须指明**：不传 `--all` 时把候选术语收窄到"说法文件里出现过的那些"
（通常 500 个，**是乐观上界**）；传 `--all` 用**全库术语**（实测 42,181 个，**真实口径**）。
同一批说法上前 20 从 32.6% 掉到 8.4% —— 报数不写候选集大小，等于报了一个不存在的结论。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-term-bridge.py <说法 JSONL> [--all]
说法 JSONL 每行 `{"term": ..., "lay": [{"text": ...}, ...]}`。
只读真库。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.retrieval.term_bridge import (  # noqa: E402
    TermIndex, bridge_search, merge_round_robin,
)
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")
K_TERMS, PER_TERM = 5, 20


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    # ⚠ 本机控制台默认 GBK：报告里那些箭头/全角符号会把 `print` **在收尾处**炸掉
    #   （实测：算完全部指标、打印到最后一行时 UnicodeEncodeError ⇒ 前面几分钟白跑）。
    #   统一改成 UTF-8，重定向到文件时也是 UTF-8。
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover - 环境相关
            pass
    src = Path(sys.argv[1])
    use_all = "--all" in sys.argv
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    # 术语表**缓存到磁盘**：全库 42,181 条的嵌入实测要 ~540s，别每次重算。
    cache = REPO / "var" / "tmp" / "term-index-full.json"
    t0 = time.time()
    if cache.exists():
        index = TermIndex.load(cache)
        print(f"术语表：从缓存读入 {len(index)} 条（{time.time()-t0:.0f}s）", flush=True)
    else:
        index = TermIndex.build(conn)
        index.save(cache)
        print(f"术语表：建成 {len(index)} 条并缓存（扫库+嵌入 {time.time()-t0:.0f}s）", flush=True)
    if not use_all:
        # ⚠ 默认把候选集收窄到"说法里出现过的那些术语"——
        #   暂存区的实验用的是 500 个候选；全库是 42,181 个（**84 倍**），两者不可混比。
        keep = [i for i, e in enumerate(index.entries) if e.term in wanted]
        index.entries = [index.entries[i] for i in keep]
        index.vectors = [index.vectors[i] for i in keep]
        print(f"  候选集收窄到说法里出现过的 {len(index)} 条（`--all` 可改用全库）", flush=True)

    by_term: dict[str, set[str]] = {e.term: {e.clause_revision_id} for e in index.entries}
    # ⚠ **靶子口径**：一个术语在库里可能有多条定义条款（实测最多 40 条）。
    # 只拿 `TermIndex` 里那条（每术语去重后的**第一条**）当靶子会**严得多**，
    # 与暂存区那批实验（用"该术语全部定义条款"）**不可比**。
    # 这里扫一遍把**全部**定义条款收齐，与既有口径对齐。
    from src.core.retrieval.term_bridge import TERM_ENTRY_RE as _RE
    want = {e.term for e in index.entries}
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = _RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            by_term.setdefault(t, set()).add(cid)
    tw = {e.term: words(e.term) for e in index.entries}

    cases = []          # (term, text, is_nonA)
    for r in rows:
        t = r["term"]
        if t not in by_term:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx:
                cases.append((t, tx, not (words(tx) & tw[t])))
    nonA = [c for c in cases if c[2]]
    print(f"说法 {len(cases)} 条，其中非 A（要救的那些）{len(nonA)} 条", flush=True)

    def fts_ids(text: str, k: int) -> list[str]:
        expr = fts_match_expr(text)
        if not expr.strip():
            return []
        try:
            return [r[0] for r in conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()]
        except sqlite3.OperationalError:
            return []

    n = len(nonA)
    # ⚠ **两个分母都报**（2026-09-25 复核另一条分支时立的规矩）：
    #   非 A 子集的基线按定义接近 0 ⇒ 倍数被放大；全部说法上倍数小得多。
    #   只报一个分母，读的人会把"最难子集的倍数"当成"整体倍数"
    #   （那条分支就把 2.76× 写成了 4.53×）。所以脚本自己把两个都印出来。
    res = {g: {"A5": 0, "A20": 0, "seq5": 0, "seq20": 0, "rr5": 0, "rr20": 0, "recall": 0}
           for g in ("nonA", "all")}
    term_lvl = {"A": defaultdict(bool), "rr": defaultdict(bool)}
    t0 = time.time()
    for i, (t, tx, isn) in enumerate(cases, 1):
        tgt = by_term[t]
        a = fts_ids(tx, PER_TERM)
        merged, picked = bridge_search(conn, index, tx, k_terms=K_TERMS, per_term=PER_TERM)
        # 同一批候选，只换合并顺序 → 隔离"合并顺序"这一个变量
        lists = []
        for e in picked:
            lists.append(fts_ids(e.term, PER_TERM))
        seq = [c for L in lists for c in L]
        # A 档说法只进 "all" 这一组（它按定义就是基线能对上的那些）
        for g in (("nonA", "all") if isn else ("all",)):
            r = res[g]
            r["A5"] += int(bool(set(a[:5]) & tgt))
            r["A20"] += int(bool(set(a[:20]) & tgt))
            r["seq5"] += int(bool(set(seq[:5]) & tgt))
            r["seq20"] += int(bool(set(seq[:20]) & tgt))
            r["rr5"] += int(bool(set(merged[:5]) & tgt))
            r["rr20"] += int(bool(set(merged[:20]) & tgt))
            r["recall"] += int(bool(set(merged) & tgt))
        if isn:                                  # 术语级只对非 A 有意义（见下）
            term_lvl["A"][t] |= bool(set(a[:20]) & tgt)
            term_lvl["rr"][t] |= bool(set(merged[:20]) & tgt)
        if i % 300 == 0:
            print(f"  {i}/{len(cases)}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"术语桥端到端（k={K_TERMS} 术语 × 每术语前 {PER_TERM} 条）")
    print("=" * 78)
    for g, label, gn in (("nonA", f"非 A 子集（要救的那些）{n} 条", n),
                         ("all", f"全部说法 {len(cases)} 条（含基线本来就能对上的）",
                          len(cases))):
        r = res[g]
        print(f"── {label}")
        print(f"   {'臂':<24}{'前5':>9}{'前20':>9}")
        print(f"   {'A 基线（大白话直接搜）':<24}{r['A5']/gn:>9.1%}{r['A20']/gn:>9.1%}")
        print(f"   {'B 桥·顺序拼接':<24}{r['seq5']/gn:>9.1%}{r['seq20']/gn:>9.1%}")
        print(f"   {'B 桥·轮转交错':<24}{r['rr5']/gn:>9.1%}{r['rr20']/gn:>9.1%}")
        print(f"   桥的命中集合/召回：{r['recall']/gn:.1%}"
              f"（答案常在返回集里、只是排不进前 20）")
    print()
    terms_seen = len({t for t, _x, isn in cases if isn})
    for label, key in (("A 基线", "A"), ("B 桥·轮转", "rr")):
        v = sum(1 for t in term_lvl[key] if term_lvl[key][t])
        print(f"  术语级（非 A 里任一说法命中即算该术语命中）：{label} 前20 "
              f"{v}/{terms_seen} = {v/max(terms_seen,1):.1%}")
    print()
    print("  ⚠ **两个分母都印出来了，引用时必须带一个**：非 A 子集的基线按定义接近 0")
    print("     ⇒ 倍数被放大；全部说法上倍数小得多。只报一个就是把最难子集当整体。")
    print("     （另一条分支漏了这句，把 2.76× 写成了 4.53×。）")
    print("  ⚠ **轮转交错不牺牲前 5**：实测量到的前 5 也略好，收益主要落在前 20。")
    print("     （这里曾有第三条错话——「轮转会牺牲前 5」——那是**靶子口径写错**时的假象：")
    print("      当时只拿每术语的**第一条**定义条款当靶子，严得多。口径改正后假象消失。）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
