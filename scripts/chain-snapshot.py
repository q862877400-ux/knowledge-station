"""链快照（§11.0 R6c 第一步）：把"今天的链"与"按台账算出来的链"并排打出来。

**这一步不改巡检行为**——它只是让"改动会带来什么差异"在动手前就看得见。
用法：
    .venv\\Scripts\\python.exe scripts\\chain-snapshot.py [--json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 控制台是 GBK；统一成 UTF-8

from src.core.update.channels import ledger_chain as lc  # noqa: E402
from src.core.update.channels.routing import select_chain  # noqa: E402

#: 覆盖每一条前缀规则 + 一条无特征（走兜底）的样例号
SAMPLES = [
    ("GB 30871-2022", "国标/危化"),
    ("GB 50493-2019", "工程建设国标（前缀规则命中 ndls）"),
    ("GB/T 30871-2022", "推荐性国标（无前缀规则 → 走兜底）"),
    ("AQ 3028-2008", "应急行业标准"),
    ("HJ 1234-2020", "生态环境"),
    ("DB11/T 3031-2022", "地方标准"),
    ("MT/T 1000-2019", "行业标准"),
    ("T/CECS 2350-2026", "团体标准"),
    ("ISO 9001:2015", "无特征（纯兜底）"),
]


def main() -> int:
    as_json = "--json" in sys.argv
    rows = lc.cr.list_channels()
    today = lc.fallback_chain()
    ledger = lc.ledger_fallback_chain(rows)
    report = lc.ledger_chain_report(rows)

    if as_json:
        print(json.dumps({"fallback_today": list(today), "fallback_from_ledger": list(ledger),
                          **report}, ensure_ascii=False, indent=2))
        return 0

    print(f"台账 {len(rows)} 条")
    print(f"今天的兜底链      : {' → '.join(today)}")
    print(f"按台账**过滤**后    : {' → '.join(ledger)}"
          + ("   ✅ 无差异（今天没有 enabled=0 / known-broken 的兜底成员）"
             if tuple(ledger) == tuple(today) else "   ⚠ 有差异（接入前要看清）"))
    print(f"   ⚠ 成员资格是**显式名单**（缺省=今天那两棒）：台账只负责"
          f"①过滤（enabled=0 / known-broken）②报告候选 —— 不把 wiring=wired 全塞进来"
          f"（第一版这么写，快照显示 9/9 个样例都变，见 ledger_chain.py 的 docstring）")
    print()
    print("逐号对照（前缀规则不变，兜底链按过滤后的名单）：")
    changed = 0
    for no, why in SAMPLES:
        a = select_chain(no)
        first = a[0] if a and a[0] not in today else None
        b = ((first,) if first else ()) + tuple(c for c in ledger if c != first)
        mark = "" if a == b else "  ⚠ 变"
        changed += a != b
        print(f"  {no:<20} {why:<28} 今天 {'/'.join(a):<28} → {mark or '不变'}")
    print(f"  ⇒ {len(SAMPLES)} 个样例里 {changed} 个会变")
    print()
    print(f"被硬过滤挡住的渠道（{len(report['excluded'])} 条）—— 只看人工意图与 known-broken：")
    for r in report["excluded"]:
        print(f"  {r['channel_id']:<44} {str(r['reason'])[:40]}（wiring={r['wiring']}, enabled={r['enabled']}）")
    print()
    cand = report["roster_candidates"]
    print(f"**可提升为兜底成员的候选**（{len(cand)} 条）—— 台账 wired + 代码里有适配器，但不在名单里；")
    print("  提升是行为改变（泛查链变长 = 每号更多请求），要单独一步决定，不在这里顺手做：")
    for r in cand:
        print(f"  {r['channel_id']:<44} 适配器={r['adapter']:<12} {r['name']}")
    print()
    md = report["missing_in_code"]
    print(f"台账说 wired 但代码里没有该适配器（{len(md)} 条）—— 接入时必须**报错而不是静默跳过**：")
    for r in md:
        print(f"  {r['channel_id']:<44} {r['why'][:70]}")
    dead = report["wired_but_probe_down"]
    print()
    print(f"⚠ 探针说 down 但**本步不过滤**的渠道（{len(dead)} 条）——链随探针抖动是另一件事，需单独决策：")
    for r in dead:
        print(f"  {r['channel_id']:<44} {r['state']} {r['last_error_code']} 连续{r['consecutive_failures']}次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
