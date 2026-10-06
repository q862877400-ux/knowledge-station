"""E1 步骤 2：在副本里生成**实验臂送进模型的那段文本**（`retrieval_text_ctx`）。

**关键取舍（本仓 spec FR-015 要求「保留分字段存储以便后续单独调权重」）**：
不把「标准名 + 路径 + 条款号 + 正文」拼成一个"源文本"写回 `clause_revision` ——
它只是**检索表示层**的实验字段，落在副本的独立表里，逐条可审、可重算、可换拼法重跑。

拼接公式（与 README §二 一致）：
    {standard_name}
    > {hierarchy_path}        ← 空则整行省略
    > {clause_number}
    {content_text[:512]}

⚠ 不含标准号（那是标识符，留给 E1b 单独测）。
⚠ 正文按现役口径截 512 字（对齐对照臂），不额外截。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\02-build-text.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"

DDL = """
CREATE TABLE IF NOT EXISTS retrieval_text_ctx (
    clause_revision_id TEXT PRIMARY KEY,
    standard_name      TEXT,
    hierarchy_path     TEXT,
    clause_number      TEXT,
    body               TEXT,          -- content_text[:512]（与对照臂同一截断口径）
    retrieval_text     TEXT NOT NULL, -- 拼好的、真正送进 embedding 的那段
    n_chars            INTEGER
)
"""


def build_text(standard_name: str | None, hp: str | None, no: str | None, body: str) -> str:
    """把四个字段拼成实验臂的输入文本。"""
    lines = [standard_name or ""]
    if (hp or "").strip():
        lines.append("> " + hp.strip())
    lines.append("> " + (no or "").strip())
    lines.append(body)
    return "\n".join(lines)


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension  # noqa: F401
    conn = sqlite3.connect(str(EXP))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(DDL)
    conn.commit()

    done = conn.execute("SELECT COUNT(*) FROM retrieval_text_ctx").fetchone()[0]
    if done:
        print(f"[skip] retrieval_text_ctx 已有 {done} 行；要重建先 DROP TABLE")

    rows = conn.execute(
        "SELECT cr.clause_revision_id, cr.clause_number, cr.hierarchy_path, cr.content_text,"
        "       dm.standard_name"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.content_text IS NOT NULL AND trim(cr.content_text) <> ''"
        " ORDER BY cr.rowid").fetchall()
    print(f"[build] 待生成 {len(rows)} 条（跳过空正文的）")

    t0 = time.perf_counter()
    batch = []
    n_over = 0          # 上下文 + 正文 超过 512 字的条数（会挤掉正文尾部，如实计）
    with conn:
        for i, (cid, no, hp, body, sname) in enumerate(rows, 1):
            body = (body or "")[:512]
            txt = build_text(sname, hp, no, body)
            if len((hp or "")) + len(no or "") + len(body) + len(sname or "") > 512:
                n_over += 1
            batch.append((cid, sname, (hp or ""), (no or ""), body, txt, len(txt)))
            if len(batch) >= 5000:
                conn.executemany(
                    "INSERT OR REPLACE INTO retrieval_text_ctx"
                    " (clause_revision_id, standard_name, hierarchy_path, clause_number,"
                    "  body, retrieval_text, n_chars) VALUES (?,?,?,?,?,?,?)", batch)
                batch.clear()
                print(f"[build] {i}/{len(rows)}  {time.perf_counter()-t0:.0f}s", flush=True)
        if batch:
            conn.executemany(
                "INSERT OR REPLACE INTO retrieval_text_ctx"
                " (clause_revision_id, standard_name, hierarchy_path, clause_number,"
                "  body, retrieval_text, n_chars) VALUES (?,?,?,?,?,?,?)", batch)

    n = conn.execute("SELECT COUNT(*) FROM retrieval_text_ctx").fetchone()[0]
    lens = [r[0] for r in conn.execute("SELECT n_chars FROM retrieval_text_ctx").fetchall()]
    lens.sort()
    print(f"[build] 落盘 {n} 行，用时 {time.perf_counter()-t0:.0f}s")
    print(f"[build] 文本长度 中位 {lens[len(lens)//2]} / 90 分位 {lens[int(len(lens)*0.9)]} / 最大 {lens[-1]}")
    print(f"[build] 文本 >512 字的 {n_over}/{n} = {n_over/n:.2%}")
    print("[build] 样本（取 2 条）：")
    for r in conn.execute("SELECT retrieval_text FROM retrieval_text_ctx LIMIT 2"):
        print("   -----")
        for ln in r[0].splitlines():
            print("   |", ln[:88])
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
