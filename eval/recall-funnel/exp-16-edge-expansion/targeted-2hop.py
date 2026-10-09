"""针对性测试 · **两跳**：A→B→C 这种"要扩两次边"的链，扩边能不能一路走通。

## 为什么单独测两跳

`targeted.py` 测的是**一跳**（A 引用了 B）。但库里还有 **3,204 条两跳链**（A→B→C）——
真正"要多跳"的场景是这种。本脚本挑**4 条真链**（A 的正文里确实写了 B 的条号、三条同一文档），
用大白话问 A 管的事，看扩 1 跳 / 2 跳分别把 B / C 带进来没有。

## 判据

* **A 在不在 top-20**（链的起点）；
* **B 在不在【top-20 ∪ 扩 1 跳】**；
* **C 在不在【top-20 ∪ 扩 1 跳 ∪ 扩 2 跳】**。

⚠ 起点 A 若没进 top-20，链就无从走起 —— 那也如实报（不粉饰）。

**只读**：`mode=ro`；不改生产代码、不写库。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DB = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db"))

#: (文档名, A条号, B条号, C条号, 大白话问法)
CHAINS = [
    ("三相同步电机试验方法", "15.2.2", "14.6", "6.4.1",
     "同步电机的直轴同步电抗不饱和值，怎么从空载试验确定？"),
    ("三相异步电动机试验方法", "11.2.2", "11.2.1", "7.9.3",
     "异步电动机规定温度下的定子绕组铜耗怎么算？"),
    ("电力变压器 第6部分：电抗器", "7.4.7", "7.9.3", "7.8.5.3",
     "并联电抗器的线性度有什么要求？"),
    ("额定电压1kV(Um=1.2kV)到35kV(Um=40.5kV)挤包绝缘电力电缆及附件", "19.26", "17.12", "13.7",
     "电缆绕包内衬层和包带垫层的总厚度怎么测量？"),
]


def _id_of(con, std, num):
    """先精确匹配 standard_name，再回退 LIKE（文档名可能带后缀/写法差异）。"""
    for pat, exact in ((std, True), (std + "%", False)):
        q = ("""SELECT cr.clause_revision_id FROM clause_revision cr
                JOIN doc_meta dm ON dm.doc_id = cr.doc_id
                WHERE dm.standard_name %s ? AND cr.clause_number = ?"""
             % ("=" if exact else "LIKE"))
        r = con.execute(q, (pat, num)).fetchone()
        if r:
            return r[0]
    return None


def main() -> int:
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

    con = get_db_connection()
    try:
        load_vec_extension(con)
    except Exception as exc:  # noqa: BLE001
        print("（向量扩展加载失败，向量路缺席）：", exc)

    out = []
    for std, an, bn, cn, query in CHAINS:
        print("=" * 78)
        print("【%s】A=%s → B=%s → C=%s" % (std[:40], an, bn, cn))
        print("  大白话问法：", query)
        a, b, c = _id_of(con, std, an), _id_of(con, std, bn), _id_of(con, std, cn)
        if not (a and b and c):
            print("  ⚠ 有条款找不到（a=%s b=%s c=%s）" % (bool(a), bool(b), bool(c)))
            continue

        res = perform_hybrid_search(query, top_k=20, rerank=False)
        lv = {0: {x.clause_revision_id for x in res}}
        for h in (1, 2):
            cur = sorted(lv[h - 1])
            nxt = set(lv[h - 1])
            for i in range(0, len(cur), 400):
                chunk = cur[i:i + 400]
                q = ("SELECT target_clause_id FROM evidence_edge WHERE status='active'"
                     " AND source_clause_id IN (%s)" % ",".join("?" * len(chunk)))
                nxt |= {t for (t,) in con.execute(q, chunk)}
            lv[h] = nxt

        where = {}
        for tag, cid in (("A", a), ("B", b), ("C", c)):
            where[tag] = next((h for h in (0, 1, 2) if cid in lv[h]), None)
        for tag in ("A", "B", "C"):
            h = where[tag]
            print("  %s 在：%s" % (tag, "✗ 没进来" if h is None else
                                  ("top-20 里" if h == 0 else "扩 %d 跳后才进来" % h)))
        print("  池子大小：top-20 %d → 扩1跳 %d → 扩2跳 %d" % (len(lv[0]), len(lv[1]), len(lv[2])))
        out.append({"chain": f"{std} {an}->{bn}->{cn}", "query": query,
                    "A_at": where["A"], "B_at": where["B"], "C_at": where["C"],
                    "pool": {str(k): len(v) for k, v in lv.items()}})

    print()
    print("=== 汇总（层级：0=top-20 里, 1=扩1跳后, 2=扩2跳后, None=没进来）===")
    for r in out:
        print("  %-42s A=%-4s B=%-4s C=%-4s | 池 %s→%s→%s"
              % (r["chain"][:40], r["A_at"], r["B_at"], r["C_at"],
                 r["pool"]["0"], r["pool"]["1"], r["pool"]["2"]))
    (Path(__file__).resolve().parent / "targeted-2hop.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
