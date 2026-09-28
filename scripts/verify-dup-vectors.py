# -*- coding: utf-8 -*-
"""独立核一条关于我们数据的事实：向量表里有多少是逐字节相同的重复向量。

只读打开生产库，只 SELECT，不写。
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"

t0 = time.perf_counter()
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

# clause_vec 是 vec0 虚拟表，PRAGMA/SELECT 都必须先加载扩展
import sqlite_vec  # type: ignore

conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)
print("sqlite_vec 已加载:", conn.execute("SELECT vec_version()").fetchone()[0])

cols = [r[1] for r in conn.execute("PRAGMA table_info(clause_vec)")]
print("clause_vec 列:", cols)
print("（注意：有没有 metadata / partition key 列，决定 ANN 能不能与过滤共存）")

total = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
print(f"向量行数: {total:,}")

hashes: Counter[str] = Counter()
vec_col = "embedding" if "embedding" in cols else cols[1]
for (blob,) in conn.execute(f"SELECT {vec_col} FROM clause_vec"):
    hashes[hashlib.blake2b(blob, digest_size=16).digest()] += 1

dup_groups = sum(1 for c in hashes.values() if c > 1)
dup_rows = sum(c for c in hashes.values() if c > 1)
redundant = dup_rows - dup_groups
largest = max(hashes.values())
elapsed = time.perf_counter() - t0

print()
print("=== 重复向量（逐字节相同）===")
print(f"唯一向量(哈希)数        : {len(hashes):,}")
print(f"落在重复组里的行数      : {dup_rows:,}  ({dup_rows/total*100:.2f}% of {total:,})")
print(f"重复组个数              : {dup_groups:,}")
print(f"可去掉的冗余行(组内多出来的): {redundant:,}  ({redundant/total*100:.2f}%)")
print(f"最大一组完全相同的条数  : {largest:,}")
print(f"(耗时 {elapsed:.1f}s，全程只读)")
