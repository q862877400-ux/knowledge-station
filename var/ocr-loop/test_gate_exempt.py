# -*- coding: utf-8 -*-
"""达线闸门**豁免机制**的契约测试（2026-09-16 立）。

**为什么必须有**：豁免直接决定"什么情况下推进链会停"。这个机制一旦写错，
后果是**真缺陷被放行**（比多停几次严重得多）。故用测试钉死四条不变量：

  ① **默认零豁免**：没有任何类带 `gate_exempt` 时，`over` 与 `over_line` 完全一致
     （即改动前后行为相同）；
  ② **豁免是逐类 opt-in**：只有带该字段的类被移出 `over`；
  ③ **真缺陷照拦**：未标字段的类（哪怕它也被登记过）**仍然进 `over`**；
  ④ **豁免不隐藏证据**：被豁免的类必须出现在 `over_exempt` 里，不许悄悄消失。

外加：`前缀::类名` 形态（`table-text::split-value`）也要能匹配。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import batch_advance as B  # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


def judge_with(over_line: list[str], ledger: dict) -> dict:
    """用假的台账 + 假的 scout.json 跑一遍 `scout_and_judge` 的策略段。

    只替换两个输入（台账文件、scout.json），**不改被测代码**。
    """
    tmp = Path(tempfile.mkdtemp(prefix="ks-gate-"))
    (tmp / "fixed_classes.json").write_text(
        json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    ev = tmp / "evolve"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "scout.json").write_text(json.dumps({
        "docs_evaluated": 10, "skipped_pipeline": 0, "total_hits": 5,
        "over_line": over_line, "source_kinds": {}}, ensure_ascii=False),
        encoding="utf-8")
    old_here, old_ev = B.HERE, B.EV
    B.HERE, B.EV = tmp, ev
    try:
        # 直接调策略段（绕开 subprocess 跑 scout）：复刻 scout_and_judge 的读法
        sc = json.loads((ev / "scout.json").read_text(encoding="utf-8"))
        over_raw = [str(c) for c in (sc.get("over_line") or [])]
        exempt = B._gate_exempt_classes()
        over = [c for c in over_raw if not B._class_in(c, exempt)]
        over_exempt = [c for c in over_raw if B._class_in(c, exempt)]
        return {"over": over, "over_exempt": over_exempt, "exempt": exempt}
    finally:
        B.HERE, B.EV = old_here, old_ev


print("=== ① 默认零豁免：台账无人标字段 → over 与 over_line 完全一致 ===")
r = judge_with(["dot-leader", "toc-ingested-as-clauses"],
               {"dot-leader": {"date": "x"}, "toc-ingested-as-clauses": {}})
check("豁免名单为空", r["exempt"], set())
check("两个类都仍达线（行为与改动前相同）",
      sorted(r["over"]), ["dot-leader", "toc-ingested-as-clauses"])
check("无豁免类被报出", r["over_exempt"], [])

print("\n=== ② 逐类 opt-in：只移出标了字段的那个类 ===")
r = judge_with(["appendix-table-lowconf", "dot-leader"],
               {"appendix-table-lowconf": {"gate_exempt": True},
                "dot-leader": {"date": "x"}})
check("只豁免 appendix-table-lowconf", r["exempt"], {"appendix-table-lowconf"})
check("→ 它不再算达线", r["over"], ["dot-leader"])
check("→ 但它**被报出来**（不隐藏证据）",
      r["over_exempt"], ["appendix-table-lowconf"])

print("\n=== ③ 真缺陷照拦：有登记但**无** gate_exempt 的类仍达线 ===")
r = judge_with(["toc-ingested-as-clauses"],
               {"toc-ingested-as-clauses": {"date": "x", "note": "已知限制…固有歧义"}})
check("登记过但未标豁免 → 仍达线（不会被误放行）",
      r["over"], ["toc-ingested-as-clauses"])
check("未进豁免名单", r["over_exempt"], [])

print("\n=== ④ `前缀::类名` 形态也能匹配（如 table-text::split-value）===")
r = judge_with(["table-text::split-value"], {"split-value": {"gate_exempt": True}})
check("前缀形态被识别为豁免", r["over_exempt"], ["table-text::split-value"])
check("→ 不再达线", r["over"], [])
r2 = judge_with(["table-text::split-value"], {"split-value": {}})
check("未标豁免时前缀形态仍达线", r2["over"], ["table-text::split-value"])

print("\n=== ⑤ 台账损坏（非法 JSON）→ 退回零豁免，不误放行 ===")
tmp = Path(tempfile.mkdtemp(prefix="ks-gate-bad-"))
(tmp / "fixed_classes.json").write_text("{ not json", encoding="utf-8")
old_here = B.HERE
B.HERE = tmp
try:
    check("读不到台账 → 空豁免名单（保守）", B._gate_exempt_classes(), set())
finally:
    B.HERE = old_here

print("\n=== ⑥ 真实台账现状：只应有 1 个类被豁免 ===")
real = B._gate_exempt_classes()
print(f"     实际豁免名单：{real}")
check("当前只有 appendix-table-lowconf 被豁免",
      real, {"appendix-table-lowconf"})
d = json.loads((HERE / "fixed_classes.json").read_text(encoding="utf-8"))
check("被豁免的类必须写明理由（防无理由豁免）",
      bool(str(d.get("appendix-table-lowconf", {}).get("gate_exempt_reason") or "").strip()),
      True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
