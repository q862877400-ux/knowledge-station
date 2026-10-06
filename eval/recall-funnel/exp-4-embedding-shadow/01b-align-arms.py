"""E4 · 步骤 1b：**把两臂的候选集合对齐**（补上我在 E4 里漏掉的 E1 前置步骤）。

## 为什么必须有这一步
 · 对照臂 `clause_vec` = **522,021** 行；
 · 实验臂 `clause_vec_qwen` = **521,978** 行 —— 因为 `01-embed-qwen.py` 只处理**正文非空**的条文
   （库里有 **43 条正文为空**，它们的 title 都是 `图(未识别题注，第1页)`，
   按现役入库公式 `title + "\\n" + content_text[:512]`，输入是 `图(未识别题注，第1页)\\n`）。

两臂候选集合不一致 ⇒ **名次不可比**，而且**少 43 个干扰项会让实验臂看起来更好**
——这与"换模型"毫无关系。**E1 那一轮已经踩过并被 `02b-align-arms.py` 修过，E4 这次是我漏了。**

## 做法（与 E1 完全一致）
**从副本里删掉那 43 条对照臂向量**（只在 E4 自己的副本上删，**真库一个字节不碰**），
使两臂都只在"有正文的 521,978 条"上排名。删完必须**复验对照臂仍复现基线**
（向量 @20/@100/@1000 = 0.1000 / 0.1750 / 0.3583，120 条口径）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\01b-align-arms.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    conn = sqlite3.connect(str(EXP))
    conn.execute("PRAGMA busy_timeout=120000")
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1

    n_base = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    n_ctx = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    print(f"[align] clause_vec={n_base}  clause_vec_qwen={n_ctx}  差={n_base - n_ctx}")

    ids = [r[0] for r in conn.execute(
        "SELECT clause_revision_id FROM clause_vec v WHERE NOT EXISTS ("
        "  SELECT 1 FROM clause_vec_qwen q WHERE q.clause_revision_id = v.clause_revision_id)")]
    only_ctx = conn.execute(
        "SELECT COUNT(*) FROM clause_vec_qwen q WHERE NOT EXISTS ("
        "  SELECT 1 FROM clause_vec v WHERE v.clause_revision_id = q.clause_revision_id)"
    ).fetchone()[0]
    print(f"[align] 仅对照臂有 = {len(ids)}；仅实验臂有 = {only_ctx}（后者应为 0）")
    if only_ctx:
        print("⛔ 实验臂有对照臂没有的条目 ⇒ 不是「正文为空」这一类，停下来查")
        return 1

    if ids:
        ph = ",".join("?" * len(ids))
        bad = conn.execute(
            f"SELECT COUNT(*) FROM clause_revision WHERE clause_revision_id IN ({ph})"
            "   AND content_text IS NOT NULL AND trim(content_text) <> ''", ids).fetchone()[0]
        print(f"[align] 这 {len(ids)} 条里**有正文**的 = {bad}（应为 0）")
        if bad:
            print("   ⇒ 不是「空正文」这一类，停下来别删")
            return 1
        with conn:
            conn.executemany("DELETE FROM clause_vec WHERE clause_revision_id=?",
                             [(x,) for x in ids])
        print(f"[align] 已从**副本**删除 {len(ids)} 条")
    else:
        print("[align] 两臂集合已经一致，无需处理")

    a = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    b = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    print(f"[align] 现在 clause_vec={a} / clause_vec_qwen={b} "
          f"{'✅ 一致' if a == b else '⛔ 仍不一致'}")
    print("[align] ⚠ 下一步必须复验对照臂仍复现基线（0.1000 / 0.1750 / 0.3583，120 条口径）")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
