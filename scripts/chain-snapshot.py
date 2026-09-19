"""链快照（§11.0 R6c 第一步）：把"今天的链"与"按台账算出来的链"并排打出来。

**这一步不改巡检行为**——它只是让"改动会带来什么差异"在动手前就看得见。
用法：
    .venv\\Scripts\\python.exe scripts\\chain-snapshot.py [--json]

⚠ **`--json` 里也有 `segments`**（复核 `verify-freeze-corr3` A2，2026-09-20 修）：改前 `--json`
分支在 print 之后就 `return` 了 ⇒ `_segments_section` **永不执行** ⇒ `--json` 输出里根本没有号段那一段，
而 R7（号段）的**全部证据**都在那一段 ⇒ "机器可读中间产物"对号段是缺的。现在 `--json` 的
`segments` 与文本段的 `seg` 是**同一个对象**（同一处算、同一个键名口径）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 控制台是 GBK；统一成 UTF-8

from src.core.update.channels import ledger_chain as lc  # noqa: E402
from src.core.update.channels.routing import first_route, select_chain  # noqa: E402

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
        # ⚠ 改前这里 print 完就 `return 0`，`_segments_section(...)` 在它**后面** ⇒ 号段那一段
        #   **永不执行**（复核 corr3 A2 实跑：`--json` 里连 `segments` 键都没有）。现在把号段
        #   一起算出来放进**同一个 JSON 文档**（不再另 print 一份 JSON，那样是两个文档拼在一起）。
        payload = {"ledger_rows": len(rows),
                   "fallback_today": list(today), "fallback_from_ledger": list(ledger),
                   **report, "segments": _segments_payload(rows)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"台账 {len(rows)} 条")
    print(f"今天的兜底链      : {' → '.join(today)}")
    print(f"按台账**过滤**后    : {' → '.join(ledger)}"
          + ("   ✅ 无差异（今天没有 enabled=0 / known-broken 的兜底成员）"
             if tuple(ledger) == tuple(today) else "   ⚠ 有差异（接入前要看清）"))
    print(f"   ⚠ 成员资格是**显式名单**（缺省=今天的兜底名单）：台账只负责"
          f"①过滤（enabled=0 / known-broken）②报告候选 —— 不把 wiring=wired 全塞进来"
          f"（第一版这么写，快照显示 9/9 个样例都变，见 ledger_chain.py 的 docstring）")
    print()
    print("逐号对照（前缀规则不变，兜底链按过滤后的名单）：")
    changed = 0
    for no, why in SAMPLES:
        a = select_chain(no)
        # ⚠ **前缀首选要问路由本身**（`first_route`），不能靠"不在兜底名单里"反推：
        #   R6c-3b 把 ndls 插进名单后，GB/AQ 这类"以 ndls 打头"的号会被反推成"没有前缀首选"，
        #   于是快照报出**假差异**（我实测到 3 个样例被误报 ⚠ 变）。
        first = first_route(no)
        b = ((first,) if first else ()) + tuple(c for c in ledger if c != first)
        mark = "" if a == b else "  ⚠ 变"
        changed += a != b
        print(f"  {no:<20} {why:<28} 今天 {'/'.join(a):<28} → {mark or '不变'}")
    print(f"  ⇒ {len(SAMPLES)} 个样例里 {changed} 个会变")
    print()
    # ── §11.0 R6h：**巡检实际用的链**（本步新接的：台账过滤已进 inspector）──
    # 这一段是"接线"的审计面：它算的正是 `inspector._probe_number` 会拿到的那条链。
    # 与上一段的区别：上一段是"如果按过滤后的**兜底名单**重算"，这一段是"**巡检真的会用**什么"。
    print("巡检实际会用的链（`ledger_chain.chain_for_number` = select_chain + 台账硬过滤）：")
    wired_changed = 0
    for no, why in SAMPLES:
        raw = select_chain(no)
        eff = lc.chain_for_number(no, rows)
        same = raw == eff
        wired_changed += not same
        note = "不变" if same else f"⚠ 台账过滤掉了 {'/'.join(c for c in raw if c not in eff)}"
        print(f"  {no:<20} {why:<28} {'/'.join(eff):<28} {note}")
    print(f"  ⇒ {len(SAMPLES)} 个样例里 {wired_changed} 个因**台账过滤**而与裸路由不同"
          + ("（今天 0 条 enabled=0/known-broken 命中链上成员，所以为 0）" if wired_changed == 0 else ""))
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
    rm = report["roster_missing_in_code"]
    print(f"兜底名单里有、代码里没有的适配器（{len(rm)} 条）—— **没进链**，名单要修：")
    for r in rm:
        print(f"  {r['adapter']:<20} {r['why']}")
    if report["roster_duplicates"]:
        print(f"⚠ 名单里有重复成员（{report['roster_duplicates']}）——链已去重，但请修名单")
    nil = report["roster_not_in_ledger"]
    if nil:
        print(f"⚠ 名单成员在台账里没有行（{len(nil)} 条）—— 保留（fail-open）但其 enabled/broken 无从过滤：")
        for r in nil:
            print(f"  {r['adapter']}")
    dead = report["wired_but_probe_down"]
    print()
    print(f"⚠ 探针说 down 但**本步不过滤**的渠道（{len(dead)} 条）——链随探针抖动是另一件事，需单独决策：")
    for r in dead:
        print(f"  {r['channel_id']:<44} {r['state']} {r['last_error_code']} 连续{r['consecutive_failures']}次")

    _segments_section(_segments_payload(rows))
    return 0


def _segments_payload(rows) -> dict:
    """号段报告（`segments_json`，R7）—— **文本段与 `--json` 共用这一个**（别各算一份）。

    为什么号段必须在快照里（而不是只在用例里）：号段加法是**行为改变**
    （每号可能多问一根棒 = 更多请求），而 R6c 的教训是"提升是行为改变，必须带快照差异"。
    这里的口径：拿**真库**里全部标准号当样本，逐条算号段命中 ⇒ 差异是**量出来的**，不是估的。

    ⚠ 改前这段逻辑长在 `_segments_section(rows, as_json)` 里，而 `--json` 分支**提前 return**
    ⇒ 机器可读产物里没有号段（复核 corr3 A2）。拆出这个函数是为了让两条通路**不可能再漂开**。
    """
    # 号表在 doc_meta；只取标准号列（只读，不发请求）。
    from src.core.storage.sqlite_db import get_db_connection
    nos = [str(r["standard_no"]) for r in get_db_connection().execute(
        "SELECT DISTINCT standard_no FROM doc_meta WHERE standard_no IS NOT NULL"
    ).fetchall()]
    return lc.segments_report(rows, nos)


def _segments_section(seg: dict) -> None:
    """号段那一段的**人读**打印（数据来自 `_segments_payload`，这里只排版）。"""
    print()
    print(f"号段（`segments_json`）——真库 {seg['sample_size']} 个号全量算：")
    if not seg["declared"]:
        print("  台账里**还没有任何**号段声明 ⇒ 加法今天带来 0 个号（零行为漂移）")
    for d in seg["declared"]:
        n = seg["gained"].get(d["adapter"] or "", 0)
        flag = "（已被人工停用/known-broken ⇒ 不进链）" if d["excluded"] else ""
        print(f"  {d['channel_id']:<44} 号段={d['segments']} 带来 {n} 个号{flag}")
    if seg["dead"]:
        print(f"  ⚠ **死号段**（写了但一个真号都不命中，{len(seg['dead'])} 条）")
        print("     —— 写法错会让渠道永不进链；号段今天没料则如实标注「为未来保留」：")
        for d in seg["dead"]:
            print(f"     {d['channel_id']:<42} {d['segment']!r} {d['name']}")
    un = seg["unreachable_no_segments"]
    if un:
        print(f"  ⚠ **有适配器但今天到不了、也没声明号段**（{len(un)} 条）——这是待办清单，不是「没问题」：")
        for u in un:
            print(f"     {u['channel_id']:<42} 适配器={u['adapter']:<12} {u['name']}")
    if seg["note"]:
        print(f"  ⚠ {seg['note']}")


if __name__ == "__main__":
    raise SystemExit(main())
