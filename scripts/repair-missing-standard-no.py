"""R6c-2e：修**号里没有数字**的坏行（从 `file_path` 的文件名推导真号）。

## 为什么要它（真证据，2026-09-18）
`var/ocr-loop/ingest_from_manifest.py` 的 `split_std` 前缀表漏了 `GBZ／T`，于是
`GBZ／T 160.27-2004 工作场所空气有毒物质测定硼及其化合物.pdf` 入库时
`standard_no` 被压成**裸 `GBZ／T`**（真库现存 `doc_01M2MA6VWVFF01BXJPE58BB02D`）。
这个号**查不出来**：按号检索 `GBZ/T 160.27-2004` 找不到它，
而 `standard_name` 里还留着 `160.27-2004` 这段号。独立复核 b32 就是靠这一行
认定"该脚本确实往生产库写过脏号"。

## 与"全角斜杠回填"的分工
`normalize-standard-no-slash.py` 只换**字符形状**（`／`→`/`），不补内容；
本脚本是**内容修复**（把残缺的号补成真号）。两者都会写库 ⇒ 各自 dry-run、各自出清单。

## 判定规则（保守：宁可漏，不可错）
候选 = `standard_no` **不含任何数字** 的行；对每一行：
  1. 取 `file_path` 的 stem 并折存储形（`／`→`/`）——语料文件名普遍带全角斜杠；
  2. 按空格切两段，**第一段必须在前缀白名单里**（`GB`/`GB/T`/`GBZ/T`/`AQ`/`HJ`…）；
  3. 拼出的号必须匹配 `^[A-Z]{1,4}(/[A-Z]{1,2})? \\d`（真的要是个号）；
  4. `standard_no` / `short_code` **不能与库里已有值撞车**；
不满足的**一律跳过并说明原因**（法规行就是靠 2/3 被排除的——它们的号本来就是法规名）。

用法：
    .venv\\Scripts\\python.exe scripts/repair-missing-standard-no.py            # dry-run
    .venv\\Scripts\\python.exe scripts/repair-missing-standard-no.py --apply    # 真写
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ⚠ 让 `_measure_common` 能被导入：**必须把本文件所在的 scripts/ 放进搜索路径**。
#   只在 cwd=仓根、以 `python scripts/xxx.py` 方式跑时才能直接 import；
#   而 `tests/test_classical_segmentation_ruler.py` 是用 `spec_from_file_location`
#   **按文件路径**加载本脚本的 —— 那时 cwd 与 sys.path 都不是 scripts/，
#   直接 import 会 ModuleNotFoundError（2026-10-23 被门禁的 pytest 步当场抓到）。
#   全仓另 10 个脚本用同样的写法处理 `src`，这里照抄同一模式。
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _measure_common import db_stat as _db_stat  # noqa: E402
from ulid import ULID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402
from src.core.text_utils import clean_standard_name, store_standard_no  # noqa: E402

OUT_DIR = ROOT / "var" / "backup"
#: 前缀白名单（与 `var/ocr-loop/ingest_from_manifest.py::split_std` **同源**；
#: 这里补上了 `GBZ／T`/`GBZ/T`——正是那一处漏掉它们才产生的坏号）
HEAD = ("GB", "GB/T", "GB/Z", "GBZ", "GBZ/T", "GBT",
        "AQ", "AQ/T", "HJ", "MT", "YB", "JB", "DB", "T/CECS")
#: 拼出来的"号"必须长这样（宁可判不出，也不要瞎补）
SHAPE = re.compile(r"^[A-Z]{1,4}(?:/[A-Z]{1,2})?\s?\d")



def derive_from_path(file_path: str | None) -> tuple[str | None, str]:
    """文件名 → (真号 或 None, 说明)。规则见模块 docstring。"""
    if not file_path:
        return None, "没有 file_path"
    stem = store_standard_no(Path(str(file_path)).stem)
    toks = stem.split(" ")
    if len(toks) < 2:
        return None, f"文件名只有一段（{stem[:30]!r}）"
    if toks[0] not in HEAD:
        return None, f"文件名首段 {toks[0]!r} 不在前缀白名单（法规/素材）"
    cand = f"{toks[0]} {toks[1]}"
    if not SHAPE.match(cand):
        return None, f"拼出的号形状不对（{cand!r}）"
    return cand, f"由文件名推出 {cand!r}"


def _plan(conn) -> tuple[list[dict], list[dict]]:
    rows = conn.execute(
        "SELECT doc_id, standard_no, short_code, standard_name, file_path FROM doc_meta "
        "WHERE standard_no IS NULL OR standard_no NOT GLOB '*[0-9]*'").fetchall()
    existing_no = {r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
    existing_short = {r[0] for r in conn.execute(
        "SELECT short_code FROM doc_meta WHERE short_code IS NOT NULL")}
    changes: list[dict] = []
    skipped: list[dict] = []
    planned: set[str] = set()
    for r in rows:
        new_no, why = derive_from_path(r["file_path"])
        if new_no is None:
            skipped.append({"doc_id": r["doc_id"], "standard_no": r["standard_no"], "why": why})
            continue
        if new_no in existing_no or new_no in planned:
            skipped.append({"doc_id": r["doc_id"], "standard_no": r["standard_no"],
                            "why": f"{new_no!r} 已存在（或本次计划内已占位）⇒ 跳过，不制造重复"})
            continue
        new_short = new_no.replace(" ", "").replace("-", "")
        if new_short in existing_short:
            skipped.append({"doc_id": r["doc_id"], "standard_no": r["standard_no"],
                            "why": f"short_code {new_short!r} 已存在 ⇒ 跳过"})
            continue
        new_name = clean_standard_name(r["standard_name"] or Path(str(r["file_path"])).stem,
                                       standard_no=new_no)
        planned.add(new_no)
        changes.append({"doc_id": r["doc_id"], "standard_no": {"old": r["standard_no"], "new": new_no},
                        "short_code": {"old": r["short_code"], "new": new_short},
                        "standard_name": {"old": r["standard_name"], "new": new_name},
                        "why": why})
    return changes, skipped


def main() -> int:
    apply = "--apply" in sys.argv
    conn = get_db_connection()
    print("integrity_check(前):", conn.execute("PRAGMA integrity_check").fetchone()[0])
    changes, skipped = _plan(conn)
    print(f"\n计划修复 {len(changes)} 行；跳过 {len(skipped)} 行")
    for c in changes:
        print(f"  ✔ {c['standard_no']['old']!r} → {c['standard_no']['new']!r}"
              f"（short_code {c['short_code']['new']!r}）")
        print(f"      name: {c['standard_name']['old']!r} → {c['standard_name']['new']!r}")
    for s in skipped:
        print(f"  ⚠ 跳过 {s['standard_no']!r}: {s['why']}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    plan_path = OUT_DIR / f"r6c2e-repair-missing-no-{stamp}.json"
    before = _db_stat() if apply else None
    plan_path.write_text(json.dumps({"generated_at": stamp, "apply": apply,
                                     "db_before": before, "changes": changes,
                                     "skipped": skipped}, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print("清单:", plan_path.relative_to(ROOT))
    if not apply:
        print("\n（dry-run：未写库。加 --apply 才写。）")
        return 0
    with write_transaction() as w:
        for c in changes:
            for col in ("standard_no", "short_code", "standard_name"):
                v = c[col]
                cur = w.execute(
                    f"UPDATE doc_meta SET {col}=? WHERE doc_id=? AND {col}=?",
                    (v["new"], c["doc_id"], v["old"]))
                if cur.rowcount != 1:
                    raise RuntimeError(f"现值与计划不一致（{c['doc_id']} {col}: "
                                       f"期望 {v['old']!r}）⇒ 整批回滚")
        w.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type, target_id, metadata)"
            " VALUES (?,?,?,?,?,?)",
            (f"evt_{ULID()}", "standard_no_repaired_from_filename",
             "script:repair-missing-standard-no", "doc_meta", stamp,
             json.dumps({"repaired": len(changes), "skipped": len(skipped),
                         "plan": plan_path.name}, ensure_ascii=False)))
    left = conn.execute("SELECT COUNT(*) FROM doc_meta "
                        "WHERE standard_no NOT GLOB '*[0-9]*'").fetchone()[0]
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error as e:
        print("（wal_checkpoint 跳过：", e, "）")
    after = _db_stat()
    plan_path.write_text(json.dumps({"generated_at": stamp, "apply": True,
                                     "db_before": before, "db_after": after,
                                     "integrity_check": integrity,
                                     "remaining_no_digit_rows": left,
                                     "changes": changes, "skipped": skipped},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n写库完成。剩余「号里没有数字」的行:", left)
    print("integrity_check(后):", integrity)
    print("库指纹(写后):", {k: after[k] for k in ("size", "mtime", "sha256")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
