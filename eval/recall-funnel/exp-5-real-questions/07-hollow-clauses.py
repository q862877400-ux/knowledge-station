"""查一个**真缺陷**：库里有多少条文是"空壳"（正文只有标题，没有内容）。

## 怎么发现的
建"真问题+官方金标"考卷时，官方答复点名《应急救援员职业资格管理办法（试行）》**第十条**，
该文件**确实在库里**；但按条号去定位，**一条都对不上**。查下去发现：
**那份文件的 37 条条文，正文全都是同一句「第X条 标题：<通知名>」** —— 真正的条文内容没入库。

## 为什么这件事要紧
 · 这类条文**永远答不出任何问题**（正文里没有可检索的内容）；
 · 它会**污染检索**：问什么都可能被这些"标题壳"匹配上，占掉前面的位置；
 · 它同时解释了另一件事：E1/清洗那轮我在考卷里发现的 "q166/q167 条文以『第二十条 标题：』开头"
   —— **那不是个别现象**，是一整类文档的入库缺陷。

本脚本只读真库，量化它。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\07-hollow-clauses.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "hollow-clauses.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 「空壳」判据：正文里带「标题：」且**去掉"第X条 标题："之后没有别的内容**
TITLE_RE = re.compile(r"^\s*第[一二三四五六七八九十百零\d]{1,4}条\s*标题[：:]\s*")


def main() -> int:
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    total = c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]

    rows = c.execute(
        "SELECT cr.clause_revision_id, cr.doc_id, cr.clause_number, cr.content_text"
        " FROM clause_revision cr WHERE cr.content_text LIKE '%标题：%'").fetchall()
    print(f"[hollow] 正文含「标题：」的条文 = {len(rows)} / {total}")

    # 严格：去掉「第X条 标题：」后，剩下的就是文档名（没有实质内容）
    hollow, docs = [], {}
    for cid, did, num, txt in rows:
        t = (txt or "").strip()
        rest = TITLE_RE.sub("", t)
        # 「空壳」= 剩余部分很短（<=80 字）或与文档名高度重合
        if len(rest) <= 80:
            hollow.append((cid, did, num, rest[:60]))
            docs[did] = docs.get(did, 0) + 1
    print(f"[hollow] 其中**空壳**（去掉'第X条 标题：'后 ≤80 字）= {len(hollow)}")

    doc_n = {}
    for did, n in docs.items():
        tot = c.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (did,)).fetchone()[0]
        doc_n[did] = {"hollow": n, "total": tot}
    all_hollow = [d for d, v in doc_n.items() if v["hollow"] == v["total"]]

    print(f"[hollow] 涉及 {len(docs)} 篇文档；其中**整篇都是空壳**的 = {len(all_hollow)} 篇")
    conv = c.execute("SELECT COUNT(*) FROM clause_revision WHERE content_text LIKE '%;%标题%'").fetchone()[0]
    print(f"[hollow] 附件名（供对照）…")

    samples = []
    for did, n in sorted(docs.items(), key=lambda kv: -kv[1])[:10]:
        dm = c.execute("SELECT standard_no, standard_name FROM doc_meta WHERE doc_id=?", (did,)).fetchone()
        samples.append({"doc_id": did, "standard_no": dm[0] if dm else None,
                        "standard_name": (dm[1] or "")[:70] if dm else None,
                        "hollow_clauses": n, "total_clauses": doc_n[did]["total"]})
        print(f"     {n:4d}/{doc_n[did]['total']:4d}  {(dm[1] if dm else '')[:56]}")

    result = {
        "question": "库里有多少条文是『空壳』（正文只有标题、没有内容）？",
        "how_found": ("建『真问题+官方金标』考卷时，官方答复点名一份**在库**文件的第十条，"
                      "按条号定位却一条都对不上 ⇒ 查下去发现那 37 条正文全是同一句标题。"),
        "why_it_matters": [
            "这类条文**永远答不出任何问题**（正文里没有可检索内容）；",
            "它会**污染检索**：可能被任意问题匹配上、占掉前面的位置；",
            "它解释了早前在考卷里发现的 q166/q167『第二十条 标题：』——**那不是个别现象**。",
        ],
        "totals": {"clauses": total,
                   "with_title_marker": len(rows),
                   "hollow": len(hollow),
                   "hollow_pct": round(len(hollow) / total * 100, 3),
                   "docs_affected": len(docs),
                   "docs_entirely_hollow": len(all_hollow)},
        "top_docs": samples,
        "boundary": ["判据是启发式（去掉『第X条 标题：』后 ≤80 字），可能有少量误判；只读真库。"],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "top_docs"}, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
