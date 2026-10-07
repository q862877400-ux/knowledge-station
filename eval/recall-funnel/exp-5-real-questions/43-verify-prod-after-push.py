"""第 ⑤ 步：**在真库上**（只读）补验推送结果。

## 为什么必须补验
推送脚本 `40-promote-to-prod.py` 漏了 `sys.path` 注入 ⇒ `load_vec_extension` 导入失败
⇒ **向量计数没验到**（日志里是 `clause_vec: '未取到:ModuleNotFoundError'`）。
向量要是丢了，检索的"按意思找"那一路就废了 ⇒ **必须在真库上单独核一次**。

本脚本对**真库**只读：
 ① 三个计数（含 `clause_vec`，需加载 vec 扩展）；
 ② `PRAGMA integrity_check`；
 ③ 抽一部法律看条文（确认不是空壳、不带文件头）；
 ④ 与副本逐项对照（应完全一致）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\43-verify-prod-after-push.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "verify-prod-after-push.json"
sys.path.insert(0, str(ROOT))
REAL = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
COPY = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"


def probe(db: Path, label: str) -> dict:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=30000")
    load_vec_extension(c)                       # ← 推送脚本漏了这一步
    out = {
        "doc_meta": c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0],
        "clause_revision": c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0],
        "clause_vec": c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0],
        "integrity": c.execute("PRAGMA integrity_check").fetchone()[0],
        "mandatory_gb": c.execute(
            "SELECT COUNT(*) FROM doc_meta WHERE UPPER(standard_no) LIKE 'GB %'"
            " AND UPPER(standard_no) NOT LIKE 'GB/T%' AND UPPER(standard_no) NOT LIKE 'GB/Z%'"
        ).fetchone()[0],
        "law_docs": c.execute(
            "SELECT COUNT(*) FROM doc_meta WHERE file_path LIKE 'lawrefbook://%'").fetchone()[0],
    }
    print(f"[{label}] {out}", flush=True)
    c.close()
    return out


def main() -> int:
    real = probe(REAL, "真库(已更新)")
    copy = probe(COPY, "副本")

    # 抽样：在真库上抽一部法律看条文
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{REAL.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)
    samples = []
    for name in ("劳动合同法", "职业病防治法", "易制毒化学品管理条例"):
        r = c.execute(
            "SELECT dm.doc_id, dm.standard_name FROM doc_meta dm"
            " WHERE dm.standard_name = ? OR dm.standard_name LIKE ? LIMIT 1",
            (name, f"{name}(%)")).fetchone()
        if not r:
            samples.append({"name": name, "found": False})
            continue
        n = c.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (r[0],)).fetchone()[0]
        body = c.execute(
            "SELECT clause_number, substr(content_text,1,80) FROM clause_revision"
            " WHERE doc_id=? ORDER BY rowid LIMIT 1", (r[0],)).fetchone()
        samples.append({"name": name, "found": True, "clauses": n,
                        "first_no": body[0], "first_text": (body[1] or "").replace("\n", " ")})
        print(f"\n[真库抽验] {name}：{n} 条\n    [{body[0]}] {(body[1] or '').replace(chr(10),' ')[:80]}",
              flush=True)
    c.close()

    same = all(real.get(k) == copy.get(k)
               for k in ("doc_meta", "clause_revision", "clause_vec",
                         "mandatory_gb", "law_docs"))
    print(f"\n[prod] 真库与副本逐项一致：{'✅ 是' if same else '⛔ 否'}")
    print(f"[prod] 真库 integrity = {real['integrity']}")
    print(f"[prod] **clause_vec = {real['clause_vec']:,}**（这才是推送脚本没验到的那一项）")

    OUT.write_text(json.dumps({
        "why": "第⑤步：在真库上补验推送结果（推送脚本漏验了 clause_vec）",
        "real": real, "copy": copy, "match": same, "samples": samples,
        "note": "推送脚本 40 的 clause_vec 一栏报 ModuleNotFoundError（漏 sys.path 注入），故单独补验。",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0 if (same and real["integrity"] == "ok") else 1


if __name__ == "__main__":
    sys.exit(main())
