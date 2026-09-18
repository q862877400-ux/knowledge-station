"""按问题选渠道（§11.0 R6c-3）：给定标准号，打印"五类各由谁答、没答出来是哪一种"。

用法：
    .venv\\Scripts\\python.exe scripts\\question-route.py "GB 18218-2018" "HJ 1234-2020"
    .venv\\Scripts\\python.exe scripts\\question-route.py --sample 5     # 从真库取最近的 5 个号
    .venv\\Scripts\\python.exe scripts\\question-route.py --json "GB 18218-2018"

**只读**：不写库、不改任何声明。这里是给人看的"这一号今天会问谁"，
与 `scripts/answers-matrix.py`（人看的"哪一类有多少条渠道声明"）是一对：
matrix 是**全局能力**的上限，本脚本是**具体某一号**路由后的结果（= 上限 ∩ 链，再按 `only_ok` 滤死）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_answers as ca  # noqa: E402
from src.core.update.channels import question_router as qr  # noqa: E402
from src.core.update.channels.routing import select_chain  # noqa: E402

STATE = {"ok": "🟢", "suspicious": "🟡", "down": "🔴", "unknown": "⚪"}
REASON_CN = {"ok": "有候选", "no_capability": "没有任何渠道声明能答这一类",
             "off_chain": "有渠道能答，但都不在这一号的链上",
             "all_down": "能答的都在链上，但今天全被判死"}


def _sample(n: int) -> list[str]:
    """从真库取最近入库的 n 个非空标准号（只读；用于真机对照）。

    ⚠ 表名是 `doc_meta`（不是 `documents`——我第一版就写错了）；
    并且**用只读连接**（`mode=ro`），免得"人看一眼"的脚本意外触发建库/迁移。
    """
    import sqlite3
    from src.core.config import get_settings
    con = sqlite3.connect(f"file:{Path(get_settings().db_path).as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT standard_no FROM doc_meta WHERE TRIM(COALESCE(standard_no,'')) <> '' "
            "ORDER BY rowid DESC LIMIT ?", (n,)).fetchall()
    finally:
        con.close()
    return [str(r[0]) for r in rows]


def main() -> int:
    argv = [a for a in sys.argv[1:]]
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if "--sample" in argv:
        i = argv.index("--sample")
        n = int(argv[i + 1]) if i + 1 < len(argv) else 5
        del argv[i:i + 2]
        argv.extend(_sample(n))
    nos = argv or ["GB 18218-2018", "HJ 1234-2020", "T/CECS 1000-2021"]

    rows = cr.list_channels()
    state = {str(r["channel_id"]): r.get("state") for r in rows}
    table = ca.load_answers()

    if as_json:
        out = {no: qr.route_report(standard_no=no, rows=rows, table=table) for no in nos}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"台账 {len(rows)} 条 · 能力表 {len(table)} 条 · 五类 {list(ca.CLASSES)}")
    print()
    for no in nos:
        chain = [qr._to_channel_id(x) for x in select_chain(no)]
        print(f"【{no or '(空号)'}】链 = {chain}")
        rep = qr.route_report(standard_no=no, rows=rows, table=table)
        for cls, it in rep.items():
            flags = " ".join(f"{STATE.get(str(state.get(c)), '?')}{c}" for c in it["channels"])
            print(f"   {cls:<5} {it['reason']:<14} 候选 {len(it['channels'])} 条: {flags or '（空）'}")
            if it["reason"] != "ok":
                print(f"          ↳ {REASON_CN.get(it['reason'], it['reason'])}"
                      f"（声明能答这类共 {len(it['declared'])} 条，链上 {len(it['on_chain'])} 条，"
                      f"判死 {len(it['dropped_down'])} 条）⇒ 记 `unanswerable`")
        print()
    print("⚠ 读法：候选 = 「能力表声明能答这一类」∩「这一号的链」，再按 `only_ok` 滤掉探针判死的。")
    print("⚠ 有候选 ≠ 真能答：能力表 68 条是调研期声明（medium），要升 high 得看适配器解析。")
    print("⚠ 某类没候选 ⇒ 写 `unanswerable`，不是 `not_found`"
          "（后者的意思是：问了权威源，它说没有这个号）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
