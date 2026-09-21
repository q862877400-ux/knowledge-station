"""知识库多级目录 · 归位预览（KB-FOLDER-PLAN §五第 1 步；**只读真库，绝不写入**）。

它做什么（一次性讲清）：

1. 用 ``sqlite3`` 的 backup 接口把真库**只读地**复制到 ``%TEMP%`` 下一个**本次进程独有**
   的目录（路径带 pid 与随机后缀）；
2. 在副本上建目录表 → 用 ``doc_catalog.classify_document`` 算出"现有每一篇按当前显示的
   分类该落到哪个目录" → 在副本里真的把目录树与归属建出来；
3. 产出一份**给人看的清单**（每个目录多少篇、无分类的逐篇列出、异常、耗时）与一份
   机器可读的 JSON；
4. **自证不碰真库**：真库文件的大小与修改时间在跑前跑后各记一次，不一致就当场报错退出。

跑法::

    .venv\\Scripts\\python.exe scripts\\preview-folder-filing.py
    .venv\\Scripts\\python.exe scripts\\preview-folder-filing.py --source D:\\x\\knowledge.db
    .venv\\Scripts\\python.exe scripts\\preview-folder-filing.py --keep-copy

输出默认落在**数据区**（``%APPDATA%\\KnowledgeStation\\preview\\``），不污染代码树。
可重复跑：每次都用新副本、覆盖同名的输出文件。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.core.knowledge import folder_filing_plan as plan_mod  # noqa: E402

#: 真库默认位置（Windows 数据区）
DEFAULT_SOURCE = Path(os.path.expandvars(
    r"%APPDATA%\KnowledgeStation\database\knowledge.db"))
#: 输出默认位置（数据区，不在代码树里）
DEFAULT_OUT_DIR = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\preview"))

#: 归位要读的列（与 /documents/categories 同口径；catalog_hidden 可能不存在，读取时自适应）
_DOC_COLS = ("doc_id", "standard_no", "standard_name", "legal_hierarchy", "doc_type",
             "domain_tags")


def _close_copy_connections() -> None:
    """关掉线程局部里缓存的连接。

    ⚠ 不关就删不掉副本：Windows 上 SQLite 还开着那个 2.2 GB 的文件句柄，
    ``rmtree`` 会失败 —— 而第一次实测里 ``ignore_errors=True`` 把失败吞了，
    报告却写着"用完已删"。那是**假话**，所以现在先关连接、再删、再问磁盘。
    """
    try:
        from src.core.storage.sqlite_db import close_thread_connection
        close_thread_connection()
    except Exception as e:                      # 关不掉也要继续删（并让事实说话）
        print(f"[提示] 关连接时报错（继续尝试删副本）: {e}", file=sys.stderr)


def _stat_of(p: Path) -> dict:
    st = p.stat()
    return {"path": str(p), "size": st.st_size, "mtime_ns": st.st_mtime_ns,
            "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


def _copy_db_readonly(src: Path, dest: Path) -> float:
    """只读副本：``mode=ro`` 打开源库（SQLite 保证不写源），backup 到副本。"""
    t0 = time.time()
    uri = "file:" + str(src).replace("\\", "/") + "?mode=ro"
    src_conn = sqlite3.connect(uri, uri=True)
    try:
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()
    return time.time() - t0


def _read_docs(conn: sqlite3.Connection) -> list[dict]:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()]
    sel = [c for c in _DOC_COLS if c in cols]
    if "catalog_hidden" in cols:
        sel.append("catalog_hidden")
    rows = conn.execute(f"SELECT {', '.join(sel)} FROM doc_meta ORDER BY standard_no").fetchall()
    keys = sel
    return [dict(zip(keys, r)) for r in rows]


def _verify_applied(conn: sqlite3.Connection, plan: dict,
                    key_to_id: dict[str, str]) -> dict:
    """落库后**读回来**核对（不靠写函数的返回值自说自话）。"""
    folders = conn.execute("SELECT COUNT(*) FROM folder").fetchone()[0]
    files = conn.execute(
        "SELECT COUNT(*) FROM folder_member WHERE item_kind='file'").fetchone()[0]
    filed = conn.execute(
        "SELECT COUNT(*) FROM doc_filing_state WHERE stage='filed'").fetchone()[0]
    queued = conn.execute(
        "SELECT COUNT(*) FROM doc_filing_state WHERE stage='queued'").fetchone()[0]
    # 抽查 20 个目录：直接成员数是否与计划一致（**按 folder_id 精确比**，不按名字）
    mismatch: list[str] = []
    for n in plan["nodes"][:20]:
        fid = key_to_id.get(n["key"])
        got = conn.execute(
            "SELECT COUNT(*) FROM folder_member WHERE item_kind='file' AND folder_id=?",
            (fid,)).fetchone()[0]
        if got != n["docs_direct"]:
            mismatch.append(f"{n['key']}: 库里 {got} ≠ 计划 {n['docs_direct']}")
    return {"folders_in_db": folders, "planned_folders": len(plan["nodes"]),
            "file_members_in_db": files, "planned_members": plan["planned_docs"],
            "stage_filed": filed, "planned_filed": len(plan["assignments"]),
            "stage_queued": queued, "planned_queued": len(plan["no_class"]),
            "sampled_dirs": min(20, len(plan["nodes"])), "sample_mismatch": mismatch}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="知识库多级目录归位预览（只读真库）")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="真库路径")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="输出目录（默认数据区）")
    ap.add_argument("--keep-copy", action="store_true", help="保留副本（默认跑完删掉本进程的副本）")
    ap.add_argument("--temp-dir", default=None, help="副本放哪（默认 %%TEMP%%）")
    ap.add_argument("--print-lines", type=int, default=90,
                    help="控制台打印清单的前几行（完整清单在文件里；0 或负数 = 全打）")
    args = ap.parse_args(argv)

    src = Path(args.source)
    if not src.exists():
        print(f"[FAIL] 真库不存在: {src}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    temp_root = Path(args.temp_dir) if args.temp_dir else Path(
        os.environ.get("TEMP") or os.environ.get("TMP") or ".")
    work = temp_root / f"ks-folder-preview-{os.getpid()}-{random.randrange(16**6):06x}"
    work.mkdir(parents=True, exist_ok=False)
    copy_db = work / "knowledge.copy.db"

    before = _stat_of(src)
    print(f"真库   : {src}（{before['size']:,} 字节，mtime {before['mtime']}）")
    print(f"本次副本: {copy_db}")

    timing: dict[str, float] = {}
    try:
        timing["copy"] = round(_copy_db_readonly(src, copy_db), 2)

        from src.core.storage.sqlite_db import init_schema, get_db_connection
        t0 = time.time()
        init_schema(copy_db)
        # ⚠ **不调用** clause_repo.ensure_additive_columns()：它**不吃 db_path**，
        #   内部走 get_db_connection() = **默认库** ⇒ 在这里调用等于去 ALTER 真库。
        #   副本本来就从真库复制的，列已经在了；万一某个老库没有 catalog_hidden，
        #   folder_store._visible_clause 会自适应（不按它过滤），不需要迁移。
        timing["init_schema"] = round(time.time() - t0, 2)

        conn = get_db_connection(copy_db)
        t0 = time.time()
        docs = _read_docs(conn)
        timing["read_docs"] = round(time.time() - t0, 2)

        t0 = time.time()
        plan = plan_mod.plan_filing(docs)
        timing["classify"] = round(time.time() - t0, 2)

        t0 = time.time()
        apply_result = plan_mod.apply_plan(copy_db, plan)
        timing["apply"] = round(time.time() - t0, 2)

        t0 = time.time()
        verify = _verify_applied(conn, plan, apply_result.get("key_to_id") or {})
        timing["verify"] = round(time.time() - t0, 2)
        timing["est_real_seconds"] = round(
            timing["read_docs"] + timing["classify"] + timing["apply"], 2)

        after = _stat_of(src)
        untouched = (before["size"] == after["size"]
                     and before["mtime_ns"] == after["mtime_ns"])

        # ⚠ 先清副本、**再**写报告：`copy_removed` 必须是"真的没了"这个事实，
        #   不是"我打算删"这个意图（第一次实测就撒了谎：连接还开着 ⇒ Windows 删不掉
        #   那个 2.2 GB 的副本，而报告写着已删）。所以先关连接、再删、再问磁盘。
        if not args.keep_copy:
            _close_copy_connections()
            shutil.rmtree(work, ignore_errors=True)
        copy_removed = not work.exists()

        report = plan_mod.build_report(
            plan, generated_at=datetime.now().isoformat(timespec="seconds"),
            real_db={**before, "mtime_before": before["mtime"],
                     "mtime_after": after["mtime"], "untouched": untouched},
            copy_db=str(copy_db), copy_removed=copy_removed,
            timing=timing, apply_result={
                k: v for k, v in apply_result.items() if k != "key_to_id"},
            verify=verify)

        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "folder-filing-preview.json"
        text_path = out_dir / "folder-filing-preview.txt"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        text_path.write_text(plan_mod.render_text(report), encoding="utf-8")

        text = plan_mod.render_text(report)
        lines = text.splitlines()
        if args.print_lines and args.print_lines > 0 and len(lines) > args.print_lines:
            print("\n".join(lines[:args.print_lines]))
            print(f"…（清单全文共 {len(lines)} 行，剩下的在下面的文件里）")
        else:
            print(text)
        print(f"清单：{text_path}")
        print(f"机器可读：{json_path}")
        if args.keep_copy:
            print(f"[保留副本] {copy_db}")
        elif copy_removed:
            print(f"[已清副本] {work}")
        else:
            print(f"[警告] 副本没删掉（本次自己建的那一份）：{work}", file=sys.stderr)
        # ── 自证：真库必须一个字节都没变（这条不通过就是 FAIL，不是警告）──
        if not untouched:
            print(f"[FAIL] 真库被改动了！before={before} after={after}", file=sys.stderr)
            return 3
        print("[OK] 真库未被改动（大小与 mtime 前后一致）")
        return 0
    finally:
        if not args.keep_copy and work.exists():
            # 出错路径的兜底：只删**本次自己刚建的那一份**
            # （AGENTS.md：宽通配清 %TEMP% 误删过别人的几十个目录）
            _close_copy_connections()
            shutil.rmtree(work, ignore_errors=True)
            if work.exists():
                print(f"[警告] 副本仍没删掉：{work}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
