"""核验业主给的大白话生成结果 + 量它到底能不能搜到库里的术语定义。

三件事：
  ① 规矩核验：生成的说法有没有偷用原术语（或术语的 ≥2 字连续片段）。
  ② 真搜：把每条大白话用**生产口径**（fts_match_expr + clause_fts bm25）拿到真库上搜，
     看该术语的**定义条款**有没有进前 5 / 前 20。
  ③ 对照上限：行内人直接用**术语本身**去搜，同样量命中率。两者之差 = 这道桥必须补回来的量。

⚠ 只测"按字找"这一路（生产主力），不测向量那一路；只读真库。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
LAYS = Path(r"D:\AI\work space\zcode\var\tmp\lay-50.jsonl")
TERMS = Path(r"D:\AI\work space\zcode\var\tmp\terms-50.txt")

# 与 scripts/pick-domain-terms.py 同一形态（定义条款的识别）
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)


def substrings(t: str, n: int = 2) -> set[str]:
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def main() -> int:
    terms = [l.strip() for l in TERMS.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for line in LAYS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    print("=" * 78)
    print("⓪ 手抄校验（防我把你给的内容抄错）")
    print("=" * 78)
    print(f"  清单术语 {len(terms)} 个 / 生成结果 {len(rows)} 条")
    got = [r["term"] for r in rows]
    assert len(rows) == 50, f"应有 50 条，实际 {len(rows)}"
    assert len(set(got)) == 50, "有重复术语"
    missing = set(terms) - set(got)
    extra = set(got) - set(terms)
    print(f"  与 terms-50.txt 比对：缺 {missing or '无'} / 多 {extra or '无'}")
    assert not missing and not extra, "术语集合与清单不一致 —— 我抄错了"
    print("  ✅ 一致")
    total_lay = sum(len(r["lay"]) for r in rows)
    print(f"  生成的说法共 {total_lay} 条（平均 {total_lay / len(rows):.1f} 条/术语）")

    print()
    print("=" * 78)
    print("① 规矩核验：有没有偷用原术语")
    print("=" * 78)
    viol = []
    short = []
    for r in rows:
        t = r["term"]
        subs = substrings(t, 2)
        for s in r["lay"]:
            hit_sub = subs & set(s[i:i + 2] for i in range(len(s) - 1))
            if t in s or hit_sub:
                viol.append((t, s, t in s, sorted(hit_sub)[:4]))
        if len(r["lay"]) < 2:
            short.append(t)
    if viol:
        print(f"  ⚠ 命中 {len(viol)} 条（含术语本体的 {sum(1 for v in viol if v[2])} 条，"
              f"只撞 2 字片段的 {sum(1 for v in viol if not v[2])} 条）")
        for t, s, whole, subs in viol:
            tag = "整词" if whole else "片段"
            print(f"    [{tag}] {t} -> {s[:44]}  {subs}")
    else:
        print("  ✅ 没有偷用原术语，也没有撞上 ≥2 字连续片段")
    print(f"  只给 1 条说法的术语：{short or '无'}")

    print()
    print("=" * 78)
    print("② 找术语的定义条款（真库）")
    print("=" * 78)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    define: dict[str, set[str]] = defaultdict(set)
    clause_texts: dict[str, str] = {}
    want = set(terms)
    n = 0
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        n += 1
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            define[t].add(cid)
            clause_texts[cid] = txt or ""
    print(f"  扫描 {n:,} 条；{len(define)} 个术语在库里找到了定义条款"
          f"（缺 {sorted(want - set(define)) or '无'}）")
    print(f"  定义条款数分布：最少 {min(len(v) for v in define.values())} / "
          f"最多 {max(len(v) for v in define.values())} / "
          f"合计 {sum(len(v) for v in define.values()):,}")

    def topk(q: str, k: int) -> tuple[list[str], int]:
        expr = fts_match_expr(q)
        ntok = len([x for x in expr.split(" OR ") if x.strip()])
        if not expr.strip():
            return [], 0
        try:
            cur = conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k))
            return [r[0] for r in cur.fetchall()], ntok
        except sqlite3.OperationalError:
            return [], ntok

    def phrase_topk(q: str, k: int) -> list[str]:
        """整词短语查询：把 jieba 切分后的整串当成一个短语，不做 OR 展开。
        用来把「索引里根本没有」与「查询构造把它搅坏了」分开。"""
        seg = segment_for_fts(q)
        if not seg.strip():
            return []
        try:
            cur = conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (f'"{seg}"', k))
            return [r[0] for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    print()
    print("=" * 78)
    print("③ 真搜：大白话能不能找到那条定义（对照：直接用术语搜）")
    print("=" * 78)
    arms = {
        "术语本身·生产口径（OR 展开）": {"5": 0, "20": 0, "n": 0},
        "术语本身·整词短语（不展开）": {"5": 0, "20": 0, "n": 0},
        "大白话（外行）": {"5": 0, "20": 0, "n": 0},
    }
    per_term = []
    zero_tok = 0
    for r in rows:
        t = r["term"]
        tgt = define.get(t, set())
        if not tgt:
            continue
        # 上限臂一：生产口径
        ids5, _ = topk(t, 5)
        ids20, _ = topk(t, 20)
        a = arms["术语本身·生产口径（OR 展开）"]
        a["n"] += 1
        a["5"] += int(bool(tgt & set(ids5)))
        a["20"] += int(bool(tgt & set(ids20)))
        # 上限臂二：整词短语
        p5 = phrase_topk(t, 5)
        p20 = phrase_topk(t, 20)
        c = arms["术语本身·整词短语（不展开）"]
        c["n"] += 1
        c["5"] += int(bool(tgt & set(p5)))
        c["20"] += int(bool(tgt & set(p20)))
        # 大白话臂：任一条命中即算该术语命中
        lay5 = lay20 = False
        for s in r["lay"]:
            i5, ntok = topk(s, 5)
            i20, _ = topk(s, 20)
            if ntok == 0:
                zero_tok += 1
            lay5 = lay5 or bool(tgt & set(i5))
            lay20 = lay20 or bool(tgt & set(i20))
        b = arms["大白话（外行）"]
        b["n"] += 1
        b["5"] += int(lay5)
        b["20"] += int(lay20)
        per_term.append((t, bool(tgt & set(ids5)), lay5, lay20))

    for name, a in arms.items():
        if a["n"]:
            print(f"  {name:<26} 前5 {a['5']:>2}/{a['n']} = {a['5']/a['n']:.0%}"
                  f"   前20 {a['20']:>2}/{a['n']} = {a['20']/a['n']:.0%}")
    print(f"  大白话里有 {zero_tok} 条**一个词都没剩下**（生产口径会把纯单字查询判成空 ⇒ 必然 0 命中）")

    # 词汇钩子：大白话与定义条款之间**有没有任何 ≥2 字的重合**。
    # 若一条都没有 ⇒ 这是纯词汇差距（只能靠换词/语义补），不是检索的 bug。
    hookless = 0
    for r in rows:
        t = r["term"]
        tgt = define.get(t, set())
        if not tgt:
            continue
        texts = [txt for cid, txt in clause_texts.items() if cid in tgt]
        hooked = False
        for s in r["lay"]:
            ss = {s[i:i + 2] for i in range(len(s) - 1)}
            for txt in texts:
                if ss & {txt[i:i + 2] for i in range(len(txt) - 1)}:
                    hooked = True
                    break
            if hooked:
                break
        if not hooked:
            hookless += 1
    print(f"  大白话与定义条款**一个 2 字重合都没有**的术语：{hookless}/50"
          f" ⇒ 这些是纯词汇差距，按字找原理上无解")

    miss = [t for t, t5, l5, l20 in per_term if not l20]
    ok = [t for t, t5, l5, l20 in per_term if l5]
    print()
    print(f"  大白话**前5就搜到**的术语 {len(ok)} 个：{ok}")
    print()
    print(f"  大白话**前20都搜不到**的术语 {len(miss)} 个：{miss}")

    out = Path(r"D:\AI\work space\zcode\var\tmp\lay-50-result.md")
    lines = ["| 术语 | 术语直接搜进前5 | 大白话进前5 | 大白话进前20 |", "|---|---|---|---|"]
    for t, t5, l5, l20 in per_term:
        lines.append(f"| {t} | {'✅' if t5 else '❌'} | {'✅' if l5 else '❌'} | {'✅' if l20 else '❌'} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  逐条明细已写 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
