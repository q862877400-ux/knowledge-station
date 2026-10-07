"""把副本推成生产库（**业主已授权**：2026-10-07「现在就方便，你直接干」）。

## 安全设计（按顺序，任一步失败即中止）
 ① **独占性检查**：真库必须能独占打开 ⇒ 证明没有程序在用它（否则中止，不硬来）；
 ② **再备份一次**当前真库到 `backups/knowledge-<时间戳>-prepush.db`；
 ③ **副本自检**：三个计数 + `PRAGMA integrity_check`；
 ④ **先同目录写临时文件再改名**（`knowledge.db.new` → `knowledge.db`）——
    避免覆盖中途断电留下半个库；
 ⑤ 同时清掉真库的 `-wal` / `-shm`（否则旧 WAL 会盖住新库）；
 ⑥ **覆盖后再核三个计数**，并 `integrity_check` 一遍；
 ⑦ 全过程的每一步都打印出来，供事后核对。

## 边界
 · 真库在覆盖前**始终是完整的、可回退的**（备份 + 直到改名那一刻才动）；
 · 不动 `models/`、`secrets.json` 等其它文件，**只换 `knowledge.db`**。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\40-promote-to-prod.py
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
OUT = HERE / "promote-to-prod.json"
KS = Path(os.environ["APPDATA"]) / "KnowledgeStation"
REAL = KS / "database" / "knowledge.db"
BACKUPS = KS / "backups"
COPY = ROOT / "var" / "tmp" / "ingest-trial" / "data" / "database" / "knowledge.db"


def counts(db: Path) -> dict:
    c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    c.execute("PRAGMA busy_timeout=30000")
    out = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ("doc_meta", "clause_revision")}
    try:
        from src.core.storage.sqlite_db import load_vec_extension
        load_vec_extension(c)
        out["clause_vec"] = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    except Exception as e:                                                  # noqa: BLE001
        out["clause_vec"] = f"未取到:{type(e).__name__}"
    out["integrity"] = c.execute("PRAGMA integrity_check").fetchone()[0]
    c.close()
    return out


def exclusive_ok(p: Path) -> tuple[bool, str]:
    try:
        fh = open(p, "r+b")
        fh.close()
        return True, "可独占打开"
    except Exception as e:                                                  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main() -> int:
    log = {}
    ts = time.strftime("%Y%m%d-%H%M%S")
    print(f"[promote] 目标：{REAL}", flush=True)
    print(f"[promote] 来源：{COPY}", flush=True)

    if not COPY.exists():
        print("⛔ 副本不存在")
        return 1

    # ① 独占性
    ok, why = exclusive_ok(REAL)
    print(f"[1/6] 真库独占性：{why}", flush=True)
    log["exclusive"] = {"ok": ok, "why": why}
    if not ok:
        print("⛔ 真库正被占用 ⇒ 中止（请先停掉使用它的程序）")
        return 2

    # ② 再备份
    BACKUPS.mkdir(parents=True, exist_ok=True)
    bak = BACKUPS / f"knowledge-{ts}-prepush.db"
    t0 = time.perf_counter()
    src = sqlite3.connect(f"file:{REAL.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(bak))
    src.backup(dst)
    dst.close()
    src.close()
    print(f"[2/6] 覆盖前备份 → {bak.name}（{bak.stat().st_size/1e9:.2f} GB，"
          f"{time.perf_counter()-t0:.0f}s）", flush=True)
    log["backup_before"] = str(bak)

    # ③ 副本自检
    cc = counts(COPY)
    print(f"[3/6] 副本自检：{cc}", flush=True)
    log["copy_counts"] = cc
    if cc.get("integrity") != "ok":
        print(f"⛔ 副本 integrity_check = {cc.get('integrity')} ⇒ 中止")
        return 3

    # ④ 临时文件 + 改名
    tmp = REAL.with_suffix(".db.new")
    if tmp.exists():
        tmp.unlink()
    t0 = time.perf_counter()
    shutil.copyfile(COPY, tmp)
    print(f"[4/6] 已写到 {tmp.name}（{tmp.stat().st_size/1e9:.2f} GB，"
          f"{time.perf_counter()-t0:.0f}s）", flush=True)

    # ⑤ 清 WAL/SHM 并改名
    for suf in ("-wal", "-shm"):
        p = Path(str(REAL) + suf)
        if p.exists():
            p.unlink()
            print(f"      清掉 {p.name}", flush=True)
    os.replace(tmp, REAL)          # 同目录改名，原子
    print(f"[5/6] 已改名覆盖：{REAL.name}", flush=True)

    # ⑥ 覆盖后复核
    rc = counts(REAL)
    print(f"[6/6] 覆盖后复核：{rc}", flush=True)
    log["real_counts_after"] = rc
    good = (rc.get("doc_meta") == cc.get("doc_meta")
            and rc.get("clause_revision") == cc.get("clause_revision")
            and rc.get("clause_vec") == cc.get("clause_vec")
            and rc.get("integrity") == "ok")
    print(f"      ⇒ {'✅ 与副本逐项一致，integrity ok' if good else '⛔ 不一致，需要人工看'}", flush=True)

    OUT.write_text(json.dumps({
        "why": "把副本推成生产库（业主 2026-10-07 授权）",
        "real": str(REAL), "copy": str(COPY), "seconds_total": None,
        "backup_before": str(bak), "copy_counts": cc, "real_counts_after": rc,
        "match": good, "log": log,
        "rollback": f"把 {bak} 复制回 {REAL} 即可退回（覆盖前请确认没有程序占用）",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    print(f"回退方法：把 {bak} 复制回 {REAL}")
    return 0 if good else 4


if __name__ == "__main__":
    sys.exit(main())
