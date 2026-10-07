"""重入**走兜底分支的那批法规**（它们的条文还带文件头）。

## 背景
`ingest_law_text` 的 `fallback_single_clause` 分支（整篇作一条，编号「全文」）原先
**不经过 `_strip_law_front_matter`** ⇒ 文件头进了条文（实测 `刑法修正案（二）`）。
生产代码已修（在 `ingest_law_text` 里统一剥一次），本脚本把**已经用旧逻辑入过的那批**
删掉重入 —— 只删「只有一条、且条号是『全文』、且来源是 lawrefbook://」的法规。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\42-reingest-fallback-laws.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "reingest-fallback-laws.json"
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
JOURNAL = ROOT / "var" / "tmp" / "ingest-full" / "journal.jsonl"
os.environ["KS_DATA_DIR"] = str(TRIAL)
os.environ.setdefault("KS_MODELS_DIR", str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"))
sys.path.insert(0, str(ROOT))


def main() -> int:
    from src.core.config import get_settings
    dbp = get_settings().db_path.resolve()
    if TRIAL.resolve() not in dbp.parents:
        print("⛔ 目标不在副本下 —— 拒绝执行")
        return 2
    print(f"[guard] ✅ 在副本下：{dbp}", flush=True)

    c = sqlite3.connect(str(dbp))
    c.execute("PRAGMA busy_timeout=60000")
    rows = c.execute(
        "SELECT dm.doc_id, dm.standard_name FROM doc_meta dm"
        " JOIN clause_revision cr ON cr.doc_id = dm.doc_id"
        " WHERE dm.file_path LIKE 'lawrefbook://%'"
        " GROUP BY dm.doc_id HAVING COUNT(*) = 1 AND MAX(cr.clause_number) = '全文'").fetchall()
    print(f"[re] 走兜底分支的法规 = {len(rows)} 篇", flush=True)
    for did, nm in rows[:12]:
        body = c.execute("SELECT substr(content_text,1,60) FROM clause_revision WHERE doc_id=?",
                         (did,)).fetchone()
        print(f"    [{(nm or '')[:24]}] {(body[0] if body else '').replace(chr(10),' ')[:56]}", flush=True)
    c.close()

    from src.core.storage import clause_repo
    ok = 0
    for did, _ in rows:
        try:
            clause_repo.delete_document(did)
            ok += 1
        except Exception as e:                                              # noqa: BLE001
            print(f"    ⛔ {did} {type(e).__name__}: {str(e)[:60]}", flush=True)
    print(f"[re] 已删 {ok}/{len(rows)}", flush=True)

    # 清台账里这些 key（按标准号对不上，直接按名字清比较稳：删掉所有 law:: 里 status=ok
    # 且其 doc_id 在删除集里的行）—— 简单做法：把 law:: 行里 (name) 命中这些名字的清掉
    names = {nm for _, nm in rows}
    if JOURNAL.exists():
        shutil.copy2(JOURNAL, JOURNAL.with_suffix(".jsonl.bak-before-fallback-reingest"))
        kept, dropped = [], 0
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:                                               # noqa: BLE001
                kept.append(line)
                continue
            if str(r.get("key", "")).startswith("law::") and r.get("name") in names:
                dropped += 1
            else:
                kept.append(line)
        JOURNAL.write_text("\n".join(kept) + "\n", encoding="utf-8")
        print(f"[re] 台账清掉 {dropped} 行", flush=True)

    OUT.write_text(json.dumps({
        "why": "重入走兜底分支的法规（旧逻辑未剥文件头）",
        "fallback_docs": [{"doc_id": d, "name": n} for d, n in rows],
        "deleted": ok, "journal_lines_dropped": dropped if JOURNAL.exists() else 0,
        "boundary": ["只删『单条且条号=全文且来源=lawrefbook://』的法规；不动国标、不动真库。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
