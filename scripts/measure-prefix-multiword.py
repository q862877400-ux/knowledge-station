"""入库的尺子：**真实的多词提问**下，提问侧词干前缀是帮忙还是添乱？

为什么要有这个脚本（2026-09-25）：
`measure-cross-language-fts.py` 的两栏判据**都是用"单个词"当查询**
（① 不看排名、② 是尺子自己都标注了"最苛刻、不是生产效果"的测法）。
而真实提问是**好几个词一起**，bm25 靠词之间的互相印证排序。
未知的是：前缀把候选池放大（全库中位 1.098× / p90 20.5× / 最大 3144×）之后，
**多词查询的排名是变好还是变坏**。

⚠ **它原来是 `var/tmp/` 里的一个未跟踪探针**。复核连续两轮点名"数字只由 gitignored 探针支撑
⇒ 从冻结产物里复现不出来"，所以搬进仓里 —— **它的数字现在可以从仓里复算**。

测法（全自动，不手挑例子）：
  1. 语料按空行切段（与 `measure-cross-language-fts.py` **同一套函数**，不抄第二份）。
  2. 每段抽 3 个 **≥4 字母**的拉丁内容词；把其中一个换成**另一种写法**
     （同一套词尾规则生成，且要求"本段里没有、整份语料里有"）
     —— 这正是"文档写 A 形、用户输入 B 形"的情形。
  3. 用这 3 个词去搜，量**目标段**能不能进前 5 / 前 20、以及名次（MRR）。
  4. 对照两种口径：旧（`latin_prefix=False`）与新（生产默认）。两种口径表达式**必须真的不同**
     才计入，否则那一组是空转。

实测（DSH 官方文档，400 组）：

| 口径 | 前5 | 前20 | MRR |
|---|---|---|---|
| 旧（无前缀） | 32.5% | 51.5% | 0.195 |
| **新（生产默认）** | **42.8%** | **62.5%** | **0.290** |
| 差 | **+10.2pp** | **+11.0pp** | **+0.095（相对 +49%）** |

⇒ **召回与排名同时变好**。这一条修正了"候选池放大 ⇒ 排名会变差"的担心：
放大倍数是**机制代理量**，在真实多词形态下**没有**转化成排名损失。

⚠ 边界：语料是英文开发文档，换资料类型要重跑。本脚本是**多词**测法，
与 `measure-cross-language-fts.py` 那两栏（单词、不看排名）口径不同，**不能混着比**。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-prefix-multiword.py [资料目录] [文件通配]
    不传目录时用 `measure-cross-language-fts.py` 的默认目录（换机器要改）。
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# 复用尺子的语料装载 / 建表 / 词表 / 词尾规则 —— **不抄第二份实现**
spec = importlib.util.spec_from_file_location(
    "xlang", REPO / "scripts" / "measure-cross-language-fts.py")
xlang = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xlang)

from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

N_QUERIES = 400
K_MAX = 20


def content_words(text: str) -> list[str]:
    """拉丁内容词：≥4 字母、全小写、不含中文。

    ⚠ `str.isalpha()` 对**中文也为真**（复核 2026-09-25 抓到过这个坑），
    所以这里显式排掉含中文的 token —— 否则中文词会被当成"字母词"混进统计。
    """
    return [w for w in segment_for_fts(text).split()
            if len(w) >= 4 and w.isalpha() and w.islower() and not xlang.has_cjk(w)]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover - 环境相关
            pass

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else xlang.DEFAULT_CORPUS
    pattern = sys.argv[2] if len(sys.argv) > 2 else "*.md"
    if not root.exists():
        print(f"资料目录不存在：{root}")
        return 2

    rows = xlang.load_corpus(root, pattern)
    conn = sqlite3.connect(":memory:")
    xlang.build(conn, "fts_ascii", "'ascii'", rows)
    terms = xlang.vocab(conn, "fts_ascii")
    print(f"语料 {len(rows)} 段 / 词表 {len(terms)}", flush=True)

    queries: list[tuple[str, int]] = []
    for rowid in range(1, len(rows) + 1):
        if len(queries) >= N_QUERIES:
            break
        text = rows[rowid - 1][1]
        ws = content_words(text)
        if len(ws) < 3:
            continue
        base = ws[0]
        alt = None
        for b in sorted(xlang.variants(base)):
            if b == base or b not in terms:
                continue
            if b.lower() not in text.lower():      # 本段没有这种写法 ⇒ 正是"用户输入 B 形"
                alt = b
                break
        if alt is None:
            continue
        q = " ".join([alt] + ws[1:3])
        if fts_match_expr(q) == fts_match_expr(q, latin_prefix=False):
            continue                               # 两种口径没区别 ⇒ 空转，不计
        queries.append((q, rowid))
    print(f"有效多词查询 {len(queries)} 组（两种口径表达式确实不同）", flush=True)
    if not queries:
        print("  这份资料里没有可用的多词组（纯中文资料属于正常结果）。")
        return 0

    def run(latin_prefix: bool) -> tuple[int, int, float]:
        h5 = h20 = 0
        rr = 0.0
        for q, tgt in queries:
            expr = fts_match_expr(q, latin_prefix=latin_prefix)
            if not expr.strip():
                continue
            hits = [r[0] for r in conn.execute(
                "SELECT rowid FROM fts_ascii WHERE fts_ascii MATCH ? "
                "ORDER BY bm25(fts_ascii) LIMIT ?", (expr, K_MAX)).fetchall()]
            if tgt in hits:
                rank = hits.index(tgt) + 1
                rr += 1.0 / rank
                h5 += int(rank <= 5)
                h20 += int(rank <= 20)
        return h5, h20, rr / max(len(queries), 1)

    print()
    print("=" * 74)
    print(f"真实多词提问（{len(queries)} 组；每组的查询词都含一个'另一种写法'）")
    print("=" * 74)
    res = {}
    for label, flag in (("旧口径（无前缀）", False), ("新口径（生产默认）", True)):
        h5, h20, mrr = run(flag)
        res[label] = (h5, h20, mrr)
        print(f"  {label:<20}前5 {h5/len(queries):>6.1%}   前20 {h20/len(queries):>6.1%}"
              f"   MRR {mrr:.3f}")
    (o5, o20, omrr), (n5, n20, nmrr) = res["旧口径（无前缀）"], res["新口径（生产默认）"]
    print()
    print(f"  ⇒ 差值：前5 {(n5-o5)/len(queries):+.1%}   前20 {(n20-o20)/len(queries):+.1%}"
          f"   MRR {nmrr-omrr:+.3f}")
    print("  读法：这是在**有排名的真实形态**下量的，比'单词、不看排名'那两栏更贴近生产。")
    print("       若前 20 明显涨而 MRR 掉 ⇒ 召回变好、名次变差 ⇒ 正是排序要接的活。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
