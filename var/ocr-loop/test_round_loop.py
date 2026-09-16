# -*- coding: utf-8 -*-
"""⚠ **审计方草案的一部分（auditor draft）**——见同目录 `round_loop.py` 顶部横幅。

本测试只覆盖**审计方草案**的行为；所有者若不接管该草案，本文件应一并删除。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import round_loop as R  # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


print("=== ① 分类：problem / known-limit / clean / gap ===")
limits = {"appendix-table-lowconf"}
check("有命中 → problem",
      R.classify_rec({"verdict": "ok", "classes": {"dot-leader": 2}}, limits), "problem")
check("零命中 → clean", R.classify_rec({"verdict": "ok", "classes": {}}, limits), "clean")
check("只命中已知限制 → known-limit",
      R.classify_rec({"verdict": "ok", "classes": {"appendix-table-lowconf": 3}}, limits),
      "known-limit")
check("已知限制 + 真问题 → problem",
      R.classify_rec({"verdict": "ok", "classes": {"appendix-table-lowconf": 1,
                                                   "dot-leader": 1}}, limits), "problem")
check("GAP → gap", R.classify_rec({"verdict": "GAP", "classes": {}}, limits), "gap")
check("ERROR → gap", R.classify_rec({"verdict": "ERROR", "classes": {}}, limits), "gap")
check("表格类带前缀也认（table-text::appendix-table-lowconf）",
      R.classify_rec({"verdict": "ok",
                      "classes": {"table-text::appendix-table-lowconf": 1}}, limits),
      "known-limit")

print("\n=== ② 干净抽样必须确定性、可复现 ===")
clean = [f"GB／T {i}-2020 样品{i}" for i in range(200)]
a1 = R.pick_clean_sample(clean, 30)
a2 = R.pick_clean_sample(list(reversed(clean)), 30)
check("同集合不同顺序 → 同结果（顺序无关）", a1, a2)
check("取满 30 部", len(a1), 30)
check("另一 seed → 不同抽样", R.pick_clean_sample(clean, 30, "x") != a1, True)
check("n=0 → 空", R.pick_clean_sample(clean, 0), [])
check("n 超量 → 全给", R.pick_clean_sample(clean, 999), sorted(
    clean, key=lambda s: __import__("hashlib").sha1(f"ks-round-2026|{s}".encode()).hexdigest()))

print("\n=== ③ 两轮对比：已修复 / 仍问题 / 新冒问题 / 新类 ===")
base = {
    "A": {"verdict": "ok", "classes": {"dot-leader": 3}},          # 修好了
    "B": {"verdict": "ok", "classes": {"spurious-clause-number": 1}},  # 还没修
    "C": {"verdict": "ok", "classes": {}},                          # 一直干净
    "D": {"verdict": "GAP", "classes": {}},                         # 缺产物
}
cur = {
    "A": {"verdict": "ok", "classes": {}},                          # → 已修复
    "B": {"verdict": "ok", "classes": {"spurious-clause-number": 2}},  # → 仍问题
    "C": {"verdict": "ok", "classes": {"formula-flattened": 1}},    # → 新冒问题
    "D": {"verdict": "ok", "classes": {}},                          # GAP 变 ok（不算新问题）
    "E": {"verdict": "ok", "classes": {"toc-ingested-as-clauses": 1}},  # 新文档且有问题
}
d = R.diff_rounds(base, cur, limits)
check("已修复 = [A]", d["fixed"], ["A"])
check("仍问题 = [B]", d["still"], ["B"])
check("新冒问题 = [C, E]", d["new"], ["C", "E"])
check("新出现的类 = [formula-flattened, toc-ingested-as-clauses]",
      d["new_classes"], ["formula-flattened", "toc-ingested-as-clauses"])
check("GAP→ok 不算新问题也不在 fixed 里", "D" in d["fixed"] + d["still"] + d["new"], False)

print("\n=== ④ 台账 append-only：后写覆盖前，坏行不致命 ===")
tmp = Path(tempfile.mkdtemp(prefix="ks-round-"))
led = tmp / "doc_ledger.jsonl"
led.write_text("\n".join([
    json.dumps({"round": "R001", "std_no": "X", "verdict": "ok",
                "classes": {"dot-leader": 1}}, ensure_ascii=False),
    "{坏行 不是 JSON",
    json.dumps({"round": "R002", "std_no": "X", "verdict": "ok",
                "classes": {}}, ensure_ascii=False),
]), encoding="utf-8")
latest = R.load_ledger(led)
check("坏行被跳过、不抛异常", len(latest), 1)
check("取最近一条（R002、零命中）", latest["X"]["round"], "R002")
check("最近一条为 clean", R.classify_rec(latest["X"], limits), "clean")

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
