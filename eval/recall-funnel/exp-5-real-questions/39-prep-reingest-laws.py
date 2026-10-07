"""重入前的准备：**删掉副本里那批法规**，并把台账里 `law::` 的记录清掉。

## 为什么必须删
入库器按台账跳过"已完成"的件；那批法规在台账里是 `ok` ⇒ 直接重跑会被全部跳过，
新切分器不会生效。所以要**先删库里的旧法规、再清台账对应行**，然后重跑。

## 删的是什么
只删**来源标记为 `lawrefbook://`** 的文档（即本次从 `标准\\法律法规` 入的那批），
**不动国标、不动真库里原有的任何文档**。

## 安全
 · 硬护栏：断言引擎指向副本，否则退出；
 · 真库仍只读（本脚本连真库都不开）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\39-prep-reingest-laws.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "prep-reingest-laws.json"
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
JOURNAL = ROOT / "var" / "tmp" / "ingest-full" / "journal.jsonl"
os.environ["KS_DATA_DIR"] = str(TRIAL)
os.environ.setdefault("KS_MODELS_DIR", str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"))
sys.path.insert(0, str(ROOT))


def main() -> int:
    from src.core.config import get_settings
    dbp = get_settings().db_path.resolve()
    print(f"[guard] 引擎将写入：{dbp}", flush=True)
    if TRIAL.resolve() not in dbp.parents:
        print("[guard] ⛔ 目标不在副本下 —— 拒绝执行")
        return 2
    print("[guard] ✅ 在副本下", flush=True)

    c = sqlite3.connect(str(dbp))
    c.execute("PRAGMA busy_timeout=60000")
    ids = [r[0] for r in c.execute(
        "SELECT doc_id FROM doc_meta WHERE file_path LIKE 'lawrefbook://%'")]
    print(f"[prep] 副本里的法规文档 = {len(ids)} 篇", flush=True)
    c.close()
    if not ids:
        print("[prep] 没有可删的（可能已经清过）")

    # 删文档（走生产既有的删除通道：它同时清 clause_revision / fts / vec / 边）
    from src.core.storage import clause_repo
    ok = fail = 0
    t0 = time.perf_counter()
    for i, did in enumerate(ids, 1):
        try:
            clause_repo.delete_document(did)
            ok += 1
        except Exception as e:                                              # noqa: BLE001
            fail += 1
            print(f"    ⛔ {did} {type(e).__name__}: {str(e)[:70]}", flush=True)
        if i % 200 == 0:
            print(f"    …{i}/{len(ids)}", flush=True)
    dt = time.perf_counter() - t0
    print(f"[prep] 删除完成：成功 {ok} / 失败 {fail}，用时 {dt:.0f}s", flush=True)

    # 清台账里 law:: 的行（保留 gb::）
    kept, dropped = [], 0
    if JOURNAL.exists():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:                                               # noqa: BLE001
                kept.append(line)
                continue
            if str(r.get("key", "")).startswith("law::"):
                dropped += 1
            else:
                kept.append(line)
        backup = JOURNAL.with_suffix(".jsonl.bak-before-law-reingest")
        shutil.copy2(JOURNAL, backup)
        JOURNAL.write_text("\n".join(kept) + "\n", encoding="utf-8")
        print(f"[prep] 台账：删掉 law:: 行 {dropped} 行，保留 {len(kept)} 行"
              f"（原台账已备份到 {backup.name}）", flush=True)

    # 复核
    c = sqlite3.connect(f"file:{dbp.as_posix()}?mode=ro", uri=True)
    from src.core.storage.sqlite_db import load_vec_extension
    load_vec_extension(c)
    counts = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("doc_meta", "clause_revision", "clause_vec")}
    left = c.execute("SELECT COUNT(*) FROM doc_meta WHERE file_path LIKE 'lawrefbook://%'").fetchone()[0]
    c.close()
    print(f"[prep] 复核：{counts}；剩余法规 {left}（应 0）", flush=True)

    OUT.write_text(json.dumps({
        "why": "重入法规前：删旧法规 + 清台账 law:: 行（新切分器才生效）",
        "deleted": ok, "delete_failed": fail, "seconds": round(dt, 1),
        "journal_lines_dropped": dropped, "journal_lines_kept": len(kept),
        "counts_after": counts, "law_docs_left": left,
        "boundary": ["只删来源标记为 lawrefbook:// 的文档；不动国标、不动真库。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
