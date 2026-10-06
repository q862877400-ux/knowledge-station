"""E1 步骤 2：在副本里生成**实验臂送进模型的那段文本**。

**关键取舍（本仓 spec FR-015 要求「保留分字段存储以便后续单独调权重」）**：
不把「标准名 + 路径 + 条款号 + 正文」拼成一个"源文本"写回 `clause_revision` ——
它只是**检索表示层**的实验字段，落在副本的独立表里，逐条可审、可重算、可换拼法重跑。

## 变体（`--variant`）

| 变体 | 拼法 | 状态 |
|---|---|---|
| **`e1a`**（默认） | `标准名 / > 路径 / > 条款号 / 正文` | **正在跑的那个**（外部评估给的方案） |
| `e1b` | `标准名 / 正文` | 备选：去掉两段**纯数字**样板（保留唯一有语义的信号） |
| `e1c` | `标准名 / > 路径 / 正文` | 备选：去掉条款号 |
| `e1d` | `正文 / 标准名 / > 路径 / > 条款号` | 备选：正文前置（检验"前置把正文挤出模型窗口"） |

**⚠ 纪律**：备选臂**只在 E1a 跑完后**才跑；每次仍只改文本这一处，且各自单独写止损线。
表名规则：`e1a` → `retrieval_text_ctx`（与首次跑一致）；其余 → `retrieval_text_<变体>`。

用法：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\02-build-text.py
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\02-build-text.py --variant e1b
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"

VARIANTS = ("e1a", "e1b", "e1c", "e1d")


def table_of(variant: str) -> str:
    return "retrieval_text_ctx" if variant == "e1a" else f"retrieval_text_{variant}"


def build_text(variant: str, sname: str | None, hp: str | None,
               no: str | None, body: str) -> str:
    """按变体把四个字段拼成实验臂的输入文本。"""
    sname, hp, no = sname or "", (hp or "").strip(), (no or "").strip()
    ctx = [sname] + (["> " + hp] if hp else []) + (["> " + no] if no else [])
    if variant == "e1a":
        return "\n".join(ctx + [body])
    if variant == "e1b":
        return "\n".join([sname, body])
    if variant == "e1c":
        return "\n".join([sname] + (["> " + hp] if hp else []) + [body])
    if variant == "e1d":
        return "\n".join([body] + ctx)
    raise ValueError(variant)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, default="e1a")
    args = ap.parse_args()
    tbl = table_of(args.variant)

    conn = sqlite3.connect(str(EXP))
    conn.execute("PRAGMA journal_mode=WAL")
    # ⚠ 必须等写锁：向量生成进程每约 46 秒提交一次（同一份副本），
    #   不设超时会在 CREATE TABLE 这一步直接报「database is locked」（实测踩到）。
    conn.execute("PRAGMA busy_timeout=120000")
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {tbl} (
            clause_revision_id TEXT PRIMARY KEY,
            standard_name      TEXT,
            hierarchy_path     TEXT,
            clause_number      TEXT,
            body               TEXT,
            retrieval_text     TEXT NOT NULL,
            n_chars            INTEGER
        )""")
    conn.commit()

    done = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    if done:
        print(f"[skip] {tbl} 已有 {done} 行；要重建先 DROP TABLE")
        return 0

    rows = conn.execute(
        "SELECT cr.clause_revision_id, cr.clause_number, cr.hierarchy_path, cr.content_text,"
        "       dm.standard_name"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.content_text IS NOT NULL AND trim(cr.content_text) <> ''"
        " ORDER BY cr.rowid").fetchall()
    print(f"[build:{args.variant}] 待生成 {len(rows)} 条 → 表 {tbl}")

    t0 = time.perf_counter()
    batch, n_over = [], 0
    with conn:
        for i, (cid, no, hp, body, sname) in enumerate(rows, 1):
            body = (body or "")[:512]
            txt = build_text(args.variant, sname, hp, no, body)
            if len(hp or "") + len(no or "") + len(body) + len(sname or "") > 512:
                n_over += 1
            batch.append((cid, sname, (hp or ""), (no or ""), body, txt, len(txt)))
            if len(batch) >= 5000:
                conn.executemany(
                    f"INSERT OR REPLACE INTO {tbl} (clause_revision_id, standard_name,"
                    " hierarchy_path, clause_number, body, retrieval_text, n_chars)"
                    " VALUES (?,?,?,?,?,?,?)", batch)
                batch.clear()
                print(f"[build:{args.variant}] {i}/{len(rows)}  {time.perf_counter()-t0:.0f}s", flush=True)
        if batch:
            conn.executemany(
                f"INSERT OR REPLACE INTO {tbl} (clause_revision_id, standard_name,"
                " hierarchy_path, clause_number, body, retrieval_text, n_chars)"
                " VALUES (?,?,?,?,?,?,?)", batch)

    n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    lens = sorted(r[0] for r in conn.execute(f"SELECT n_chars FROM {tbl}"))
    print(f"[build:{args.variant}] 落盘 {n} 行，用时 {time.perf_counter()-t0:.0f}s")
    print(f"[build:{args.variant}] 文本长度 中位 {lens[len(lens)//2]} / 最大 {lens[-1]}"
          f"；>512 字的 {n_over}/{n} = {n_over/n:.2%}")
    print(f"[build:{args.variant}] 样本：")
    for r in conn.execute(f"SELECT retrieval_text FROM {tbl} LIMIT 1"):
        for ln in r[0].splitlines():
            print("   |", ln[:88])
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
