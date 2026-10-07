"""量 STARD 的 1,543 条问题**在我们库里能对上多少**（决定它能不能当考卷）。

## 为什么要量这一刀
`STARD`（arXiv 2406.15313，MIT）是**中文、真实非专业提问、1,543 条 + 55,348 条文**的法条检索数据集。
但它**不是我们的库**【业主的库以国标为主体、法规约 1,500 部】。
⇒ **必须先量"它的问题在我们库里的在库率"**，否则拿它当考卷会像上次那样：
题目问的条文我们库里根本没有，测出来只反映"库里没有"，不反映"检索好不好"。

## 量什么（三档，从松到紧）
 · **A 法律在库**：`match_name` 里的**法律名**在我们 `doc_meta` 里能找到（模糊匹配）；
 · **B 条文在库**：该法律**且该条号**都能对上；
 · **C 逐问题**：一条问题的**全部**金标法条都在库 ⇒ 这条题才**可当考卷**。

## 口径（写清楚，免得事后说不清）
 · 用**法条名去判**，不靠语义：`match_name[i]` 形如「中华人民共和国民法典第五十四条」；
 · 法律名与条号的分割：**从末尾剥掉「第…条」**（含「之一/之二」等），剩下的当法律名；
 · 法律名匹配：先精确、再**归一化后精确**（去空格/书名号），最后**双向包含**（≥6 字才允许）。

只读：**不写库、不改任何东西**；STARD 数据只读 `var/tmp`。

用法： .venv\\Scripts\\python.exe tools\\measure-stard-overlap.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "research" / "STARD-在库率.json"
QUERIES = ROOT / "var" / "tmp" / "stard-queries.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 「第…条」在末尾（允许「之一」「之二」这类）
CLAUSE_TAIL = re.compile(r"第[一二三四五六七八九十百千零〇\d]+条(?:之[一二三四五六七八九十]+)?\s*$")
#: 常见的前缀噪声
NOISE = re.compile(r"^中华人民共和国")


def norm(s: str) -> str:
    return re.sub(r"[\s《》（）()·•・]", "", s or "")


def split_name(full: str) -> tuple[str, str]:
    """「中华人民共和国民法典第五十四条」→ (法律名, 条号)。"""
    m = CLAUSE_TAIL.search(full)
    if not m:
        return full.strip(), ""
    return full[: m.start()].strip(), m.group(0).strip()


def main() -> int:
    if not QUERIES.exists():
        print(f"⛔ 缺 {QUERIES}（先下载 STARD 的 queries.json）")
        return 1
    rows = json.loads(QUERIES.read_text(encoding="utf-8"))
    print(f"[s] STARD 问题 = {len(rows)} 条")

    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    lib_docs = {}
    for no, nm in c.execute("SELECT standard_no, standard_name FROM doc_meta"):
        if nm:
            lib_docs[norm(nm)] = no
    n_docs = c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    print(f"[s] 我们库 = {n_docs} 篇 / 可匹配的标准名 {len(lib_docs)} 个")

    def find_law(name: str) -> str | None:
        k = norm(name)
        if not k:
            return None
        if k in lib_docs:
            return lib_docs[k]
        k2 = norm(NOISE.sub("", k))
        if k2 and k2 in lib_docs:
            return lib_docs[k2]
        # 双向包含（≥6 字才允许，避免"法"这种字命中一片）
        for n, no in lib_docs.items():
            if len(k2) >= 6 and (k2 in n or n in k2):
                return no
        return None

    laws = Counter()
    A = B = 0
    clause_total = 0
    per_q = []
    for r in rows:
        names = r.get("match_name") or []
        hits, miss = [], []
        for full in names:
            law, cl = split_name(full)
            laws[law] += 1
            clause_total += 1
            no = find_law(law)
            if no:
                A += 1
                hits.append({"full": full, "law": law, "clause": cl, "lib_no": no})
                # 条文级：库里该篇文档有没有这个条号
            else:
                miss.append(full)
        all_in = bool(names) and not miss
        if all_in:
            B += 1
        per_q.append({"query_id": r.get("query_id"), "问题": (r.get("问题") or "")[:60],
                      "n_gold": len(names), "hit": len(hits), "miss": miss,
                      "all_in_lib": all_in})

    print(f"\n[s] 金标法条总数 = {clause_total}")
    print(f"[s] A 法律在库 = {A}/{clause_total} = {A/max(1,clause_total):.1%}")
    print(f"[s] C 整条问题**全部**金标都在库 = {B}/{len(rows)} = {B/max(1,len(rows)):.1%}")
    print(f"\n[s] 被点名最多的前 15 部法律：")
    for law, n in laws.most_common(15):
        inlib = "✅" if find_law(law) else "❌"
        print(f"     {inlib} {law[:34]:36s} 被 {n} 条问题点名")

    out = {
        "why": "量 STARD 的 1,543 条问题在我们库里的在库率（决定它能否当考卷）",
        "source": "https://github.com/oneal2000/STARD (MIT); arXiv 2406.15313",
        "our_db": {"path": str(DB), "n_docs": n_docs, "n_lib_names": len(lib_docs)},
        "n_queries": len(rows), "n_gold_clauses": clause_total,
        "A_law_in_lib": A, "C_all_gold_in_lib": B,
        "A_rate": round(A / max(1, clause_total), 4),
        "C_rate": round(B / max(1, len(rows)), 4),
        "top_laws": [{"law": l, "n": n, "in_lib": bool(find_law(l))}
                     for l, n in laws.most_common(30)],
        "per_query": per_q,
        "boundary": ["只判'法律名在不在库'，未判'条号对不对'（下一步可加）",
                     "只读；未写库、未改任何生产件"],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
