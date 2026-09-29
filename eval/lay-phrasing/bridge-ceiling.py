"""P1 的关键分岔：库内料够不够，还是必须靠外部百科？

背景：实测 1832 条大白话里 **53% 与定义条款零个 2 字重合**（按字找原理上无解）。
但"零重合"有两种，出路完全不同：

  A. 词**在那篇文档里出现过**（只是在别的条款里）⇒ **库内就能桥**（文档级词汇扩展）；
  B. 词**连那篇文档都没有** ⇒ 库里根本没有这个词，**只能靠外部同义词/百科**。

本脚本按**词级**（jieba 切分、去单字与非中文）把 1832 条分成三档并给例子。
只读真库。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")   # 只留**两字以上的纯中文词**（去单字噪声）


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    want = {r["term"] for r in rows}
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    print("第 1 遍：找每个术语的定义条款 + 顺手记下定义条款自己的词表…", flush=True)
    define: dict[str, set[str]] = defaultdict(set)     # term -> clause ids
    term_docs: dict[str, set[str]] = defaultdict(set)  # term -> doc ids
    id_words: dict[str, set[str]] = {}                 # clause id -> 它自己的词表
    need_docs: set[str] = set()
    for cid, doc, txt in conn.execute(
            "SELECT clause_revision_id, doc_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            define[t].add(cid)
            term_docs[t].add(doc)
            need_docs.add(doc)
            id_words[cid] = words(txt)
    print(f"  {len(define)} 个术语有定义；涉及 {len(need_docs)} 篇文档", flush=True)

    print("第 2 遍：取这些文档的全部正文（建文档词表）…", flush=True)
    doc_texts: dict[str, list[str]] = defaultdict(list)
    for doc, txt in conn.execute("SELECT doc_id, content_text FROM clause_revision"):
        if doc in need_docs:
            doc_texts[doc].append(txt or "")
    doc_words: dict[str, set[str]] = {d: words(" ".join(ts)) for d, ts in doc_texts.items()}
    print(f"  已建 {len(doc_words)} 篇文档的词表", flush=True)

    print("第 3 遍：逐条大白话分档…", flush=True)
    stat = Counter()
    ex = defaultdict(list)
    for r in rows:
        t = r["term"]
        cids = define.get(t)
        if not cids:
            continue
        cw: set[str] = set()
        for c in cids:
            cw |= id_words.get(c, set())
        dw: set[str] = set()
        for d in term_docs[t]:
            dw |= doc_words.get(d, set())
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            ws = words(tx)
            if not ws:
                stat["无中文实词"] += 1
                continue
            if ws & cw:
                stat["A 命中定义条款（本来就能对上）"] += 1
            elif ws & dw:
                stat["B 在那篇文档里出现过（**库内可桥**）"] += 1
                if len(ex["B"]) < 6:
                    ex["B"].append((t, tx, sorted(ws & dw)[:4]))
            else:
                stat["C 连那篇文档都没有（**只能靠外部百科**）"] += 1
                if len(ex["C"]) < 6:
                    ex["C"].append((t, tx, sorted(ws)[:5]))

    total = sum(stat.values())
    print()
    print("=" * 78)
    print(f"1832 条大白话的**词级**分档（共 {total} 条）")
    print("=" * 78)
    for k in ("A 命中定义条款（本来就能对上）", "B 在那篇文档里出现过（**库内可桥**）",
              "C 连那篇文档都没有（**只能靠外部百科**）", "无中文实词"):
        n = stat.get(k, 0)
        print(f"  {k:<34}{n:>6}  ({n/max(total,1):>5.1%})")
    print()
    print("  B 的例子（大白话里的词确实在正确文档里出现，只是不在定义条款里）：")
    for t, tx, ws in ex["B"]:
        print(f"    [{t}] {tx[:34]}  重合词={ws}")
    print()
    print("  C 的例子（连正确文档里都没这些词 ⇒ 库里没有可对的东西）：")
    for t, tx, ws in ex["C"]:
        print(f"    [{t}] {tx[:34]}  大白话实词={ws}")
    print()
    b = stat.get("B 在那篇文档里出现过（**库内可桥**）", 0)
    c = stat.get("C 连那篇文档都没有（**只能靠外部百科**）", 0)
    print(f"  ⇒ 53% 那一段里，**库内可桥 {b}** 条、**必须外部 {c}** 条"
          f"（B:C = {b/max(c,1):.2f}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
