"""五类**排序**的差异哨兵（§11.0 R6c-4c）：谁的第一候选会因为"按能力排"而变？

**为什么要有这个脚本**（复核 b37 的 A④ 抓到的坑）：我原先把哨兵放在 `var/tmp/r6c5-sim.py`
（**不在版本库里**，只有我这台机器上有），而且它拿 `route_report` 当基准——
可 `route_report` **本身就带排序** ⇒ 自己跟自己比，**恒报 0 处变化**，
那条"改判定表前先跑哨兵"的说明等于没用。

现在这份是**可复现**的：基准是**改动前的链序**（`select_chain` ∩ 能力∩state），
对照是**排序后**的候选序，逐 (号, 类) 打印翻面，并汇总"哪几类会翻"。

用法：
    .venv\\Scripts\\python.exe scripts/five-class-order-diff.py            # 真库抽样（只读）
    .venv\\Scripts\\python.exe scripts/five-class-order-diff.py --limit 40

**判据**：若除 `废止` 之外还有别的类成规模翻面，先停下来想清楚"那是不是判定表过期了"
（历史上 `发布` 就翻过一次，是 R6c-3e 补 `published_date` 之前的事）。
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.config import get_settings  # noqa: E402
from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_answers as ca  # noqa: E402
from src.core.update.channels import question_router as qr  # noqa: E402
from src.core.update.channels.routing import first_route, select_chain  # noqa: E402

LIMIT = 400


def _sample(limit: int) -> list[str]:
    """真库抽样（只读）：按 rowid 等距取，尽量覆盖不同号段。"""
    con = sqlite3.connect(f"file:{Path(get_settings().db_path).as_posix()}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in con.execute(
            "SELECT standard_no FROM doc_meta WHERE TRIM(COALESCE(standard_no,'')) <> ''")]
    finally:
        con.close()
    if len(rows) <= limit:
        return rows
    step = max(1, len(rows) // limit)
    return rows[::step][:limit]


def main() -> int:
    argv = sys.argv[1:]
    limit = LIMIT
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    nos = _sample(limit)
    table = ca.load_answers()
    rows = cr.list_channels()
    flips = Counter()
    examples: dict[tuple[str, str, str], str] = {}
    cells = 0
    for no in nos:
        chain = [qr._to_channel_id(c) for c in select_chain(no)]
        # 基准：**改动前的链序**（能力∩链，**不排序**）
        base = {}
        for cls in ca.CLASSES:
            base[cls] = [cid for cid in chain
                         if cls in (table.get(cid, {}).get("answers") or [])]
        now = qr.channels_for(standard_no=no, table=table, rows=rows)
        for cls in ca.CLASSES:
            cells += 1
            if base[cls] != now[cls]:
                key = (cls, base[cls][0] if base[cls] else "-",
                       now[cls][0] if now[cls] else "-")
                flips[key] += 1
                examples.setdefault(key, no)
    print(f"抽样 {len(nos)} 号 × {len(ca.CLASSES)} 类 = {cells} 格；"
          f"其中**序发生变化**的 {sum(flips.values())} 格")
    for (cls, a, b), n in flips.most_common():
        print(f"  {cls:<5} 第一候选 {a[3:] if a.startswith('ch:') else a} → "
              f"{b[3:] if b.startswith('ch:') else b}   （{n} 格；例：{examples[(cls, a, b)]}）")
    kinds = {cls for (cls, _, _) in flips}
    if kinds - {"废止"}:
        print(f"\n⚠ 除「废止」外还有 {sorted(kinds - {'废止'})} 类在翻 —— "
              f"**先核判定表是不是过期了**（历史上「发布」翻过一次）")
    else:
        print("\n✅ 只有「废止」在翻（这是设计预期：ndls 有废止日期、official_gb 只有状态串）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
