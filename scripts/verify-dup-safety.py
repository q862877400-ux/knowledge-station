# -*- coding: utf-8 -*-
"""A2 深化：重复向量落在哪些条款上？去重是否安全？

只读。要回答三件事：
  1. 重复组里的条款，是不是"同一条内容被存了多份"（那去重零损失）
     还是"不同条款但向量相同"（那去重会丢东西，必须报出来）
  2. 重复组的分布：多大、集中在哪
  3. 去掉冗余后，精确条款号路（0.1 ms、我们唯一的绝对主力）还能不能一一对应
     —— 如果一个向量对应多个不同条款号，去重会破坏引用，必须报出来
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
import sqlite_vec  # noqa: E402

conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)

# hash -> [clause_revision_id, ...]
groups: dict[bytes, list[int]] = defaultdict(list)
for rid, blob in conn.execute("SELECT clause_revision_id, embedding FROM clause_vec"):
    groups[hashlib.blake2b(blob, digest_size=16).digest()].append(rid)

total = sum(len(v) for v in groups.values())
dup = {h: v for h, v in groups.items() if len(v) > 1}
redundant = sum(len(v) - 1 for v in dup.values())

print(f"向量行数           : {total:,}")
print(f"唯一向量           : {len(groups):,}")
print(f"重复组数           : {len(dup):,}")
print(f"可去冗余行         : {redundant:,} ({redundant/total*100:.2f}%)")
print()

# 组大小分布
sizes = Counter(len(v) for v in dup.values())
print("=== 重复组大小分布 ===")
for s in sorted(sizes):
    if s <= 10 or s in (50, 100, 500, 1000, 1165):
        print(f"  组大小 {s:>5}: {sizes[s]:>5} 组")
print()

# 最大组：看这些条款是不是"同内容"
big = max(dup.values(), key=len)
print(f"=== 最大组 {len(big):,} 条，看它们是什么 ===")
q = ",".join("?" * len(big[:5]))
rows = conn.execute(
    f"SELECT cr.clause_revision_id, cr.clause_number, d.standard_no, "
    f"substr(replace(replace(cr.content_text,char(10),' '),char(13),' '),1,60) "
    f"FROM clause_revision cr JOIN doc_meta d ON d.doc_id=cr.doc_id "
    f"WHERE cr.clause_revision_id IN ({q})", big[:5]).fetchall()
for r in rows:
    print(f"  id={r[0]} 条号={r[1]} 标准={r[2]}")
    print(f"     文本: {r[3]!r}")
print()

# 关键安全问题：重复组里是否含**不同 clause_number / 不同 doc**
cross_doc = 0
cross_num = 0
sample = []
for h, ids in dup.items():
    if len(ids) < 2:
        continue
    ph = ",".join("?" * len(ids))
    rs = conn.execute(
        f"SELECT cr.clause_number, d.standard_no FROM clause_revision cr "
        f"JOIN doc_meta d ON d.doc_id=cr.doc_id "
        f"WHERE cr.clause_revision_id IN ({ph})", ids).fetchall()
    nums = {r[0] for r in rs}
    docs = {r[1] for r in rs}
    if len(docs) > 1:
        cross_doc += 1
        if len(sample) < 3:
            sample.append(("跨文档", ids[:4], sorted(docs)[:3], sorted(nums)[:3]))
    if len(nums) > 1:
        cross_num += 1
        if len(sample) < 6:
            sample.append(("跨条号", ids[:4], sorted(docs)[:3], sorted(nums)[:3]))

print("=== 去重安全性：重复组里是否跨文档 / 跨条号 ===")
print(f"跨文档的重复组 : {cross_doc:,} / {len(dup):,}")
print(f"跨条号的重复组 : {cross_num:,} / {len(dup):,}")
for kind, ids, docs, nums in sample:
    print(f"  [{kind}] ids={ids} docs={docs} nums={nums}")
print()
if cross_doc == 0 and cross_num == 0:
    print("结论: 所有重复组都在**同一标准、同一条款号**内 ⇒ 纯冗余，去重零损失。")
else:
    print("结论: **存在跨文档/跨条号的相同向量** ⇒ 去重会合并不同条款，**必须人工看**，不能自动做。")
