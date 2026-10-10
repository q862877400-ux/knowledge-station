"""临时：打印 automations 表的列与我们的任务行（键值对）。"""
import json
import sqlite3

DB = "C:/Users/Zegel/.workbuddy-ai/workbuddy.db"
TASK = "1b206fd3-357f-47a1-bf5b-e17ec5c419a3"

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cols = [r[1] for r in con.execute("PRAGMA table_info(automations)")]
print("COLS:", cols)
print()
row = con.execute(
    "select * from automations where id = ?", (TASK,)
).fetchone()
if row:
    d = dict(zip(cols, row))
    for k, v in d.items():
        s = str(v)
        print(f"{k} = {s[:160]}")
con.close()
