"""清洗 v3 · 步骤 1：**冻结凭证** + 构造**盲输入**。

做两件事（都必须在任何标注结果产生之前完成）：
 1. 记录 `RULES-FROZEN.md` 的 sha256 与时间 → `rules-hash.txt`（证明规则先冻结、后执行）。
 2. 为"要求类三档"构造盲输入 `tier-input.jsonl`：**只有 `id` 与条文原文**。
    ⚠ 不许带 flags / bucket / overlap / kind 之外的任何元数据，更不许带任何分臂信息 —— 执行者必须盲。

条文原文取自**真库**（只读）：`clause_revision.content_text`，按 `gold_cr_id` 取。
范围：`kind == "要求"` 的 gold（171 条里 35 条）—— 口径与理由见 `RULES-FROZEN.md` §三。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\01-build-input.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
RULES = HERE / "RULES-FROZEN.md"
OUT_HASH = HERE / "rules-hash.txt"
OUT_INPUT = HERE / "tier-input.jsonl"


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension

    raw = RULES.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    OUT_HASH.write_text(
        f"file: {RULES.name}\nsha256: {digest}\nbytes: {len(raw)}\nfrozen_at: {stamp}\n"
        f"meaning: 本文件之外的任何标注输出都晚于此刻 ⇒ 规则先冻结、后执行\n",
        encoding="utf-8")
    print(f"[freeze] {RULES.name} sha256 = {digest}  于 {stamp}")

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    req = [(r["i"], r["v2"]["gold_cr_id"], r["gold_std"], r["gold_clause"])
           for r in v2 if r["kind"] == "要求"]
    print(f"[input] kind=要求 的 gold 共 {len(req)} 条")

    db = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)

    rows, missing = [], []
    for i, cid, std, no in req:
        r = conn.execute("SELECT content_text FROM clause_revision WHERE clause_revision_id=?",
                         (cid,)).fetchone()
        if r is None or not (r[0] or "").strip():
            missing.append(i)
            continue
        # ⚠ 只给 id 与原文。`id` 用 `q{i}` 形式，避免让执行者看出"这是第几条/在哪个子集里"。
        rows.append({"id": f"q{i}", "text": r[0]})
    conn.close()

    with OUT_INPUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[input] 已写 {OUT_INPUT.name}：{len(rows)} 行"
          f"{('；取不到原文 ' + str(missing)) if missing else ''}")
    print("[input] 每行只有 id 与 text —— 无 flags / bucket / overlap / 分臂信息")
    return 0


if __name__ == "__main__":
    sys.exit(main())
