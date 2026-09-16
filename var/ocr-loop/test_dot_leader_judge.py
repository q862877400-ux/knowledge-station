# -*- coding: utf-8 -*-
r"""`audit_text.dot-leader` 判据的**同源口径**契约测试（2026-09-16 立）。

**为什么必须有**：这个判据是**达线闸门**的输入——它一报，`batch_advance` 就
停下整条推进链等修复。批次 13 它报了 `dot-leader` 达线（3 部 / 占全部命中
42.9%），而那 **3 条全部是误报**（见下）。误报的代价是**整条链停摆**
（实测停了约 1 小时 50 分，直到人工介入），所以它必须被测试钉住。

**根因（口径错位，本仓库已犯过两次）**：检测器要求"省略号 + 左括号"，
而**所有者层** `src/core/text_utils.strip_formula_leader` 明确要求括号内是
**编号**，注释写死理由「只放宽空格，不放宽字符类——避免把正文括号内容误当编号」。
→ 检测器报"缺陷"，所有者层**按设计不清洗**，于是同一处文本永远报缺陷。
`text_utils` 注释里已修过同类两处（`…{3,}`、`\.{6,}`），本条是漏掉的第三处。

本测试钉三件事：
  ① 真缺陷两形态仍被捕获（防"为了消警把判据改瞎"）；
  ② 实测的 3 条误报形态不再被捕获；
  ③ **同源口径契约**：凡被分支①（括号形态）命中的文本，所有者层
     `strip_formula_leader` **必须真的会改动它**——否则就是新的口径错位。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import audit_text as A                                    # noqa: E402
from src.core.text_utils import strip_formula_leader      # noqa: E402

FAIL: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'OK ' if ok else 'FAIL'} {name}: {got!r}"
          f"{'' if ok else f'（期望 {want!r}）'}")
    if not ok:
        FAIL.append(name)


CHECKS = dict(A.CHECKS) if isinstance(A.CHECKS, dict) else dict(A.CHECKS)
PAT = CHECKS["dot-leader"]
#: 只取分支①（括号形态），用于同源口径交叉核对
PAREN = re.compile(r"…{2,}\s*[（(]\s*[A-Za-z]?\.?\s?\d{1,3}")


def hits(t: str) -> bool:
    return bool(PAT.search(t))


print("=== ① 真缺陷两形态：必须仍被捕获（防把判据改瞎）===")
TRUE_CASES = {
    "公式编号-纯数字（短引导线）": "A ₚ /A ₀ ……( 7 / 式中：",
    "公式编号-全角括号": "x ……（3）。",
    "公式编号-附录字母号": "V2 ………( B.6 / 式中：",
    "公式编号-字母点空格": "y ……(C. 3 / 式中：",
    "ASCII 点线连排": "W / = / P / S ..............................",
    "省略号连排(≥3)": "标引…………………………………后文",
}
for name, t in TRUE_CASES.items():
    check(f"捕获：{name}", hits(t), True)

print("\n=== ② 实测误报形态：不得再被捕获（批次 13 的 3 条原文）===")
FALSE_CASES = {
    "GB 2099.5-2008   '……（正在考虑中）'":
        "隙结构符号 …… μ\n——半导体转换器件的符号 ……（正在考虑中）\n在第 3 个注后增加 ²) ：\n注",
    "GB／T 14315-2008 '……（省略）'":
        "堵油、密封式…… M\n直通式或非堵油式、非密封式……（省略）\n4.2 产品表示方法",
    "GB／T 39398-2020 '……（公式）'":
        "广播的 TGD 误差,统计误差序列得 RMS。\n……（\nD TGD, ᵢ = D brd, ᵢ - D",
}
for name, t in FALSE_CASES.items():
    check(f"不捕获：{name}", hits(t), False)

print("\n=== ②' 合法正文省略号：一律不得被捕获 ===")
for t in ["见下文……也就是说", "……", "……等等", "前文……（见 4.2）若无异议"]:
    check(f"不捕获正文省略号：{t[:16]}", hits(t), False)

print("\n=== ③ 同源口径契约：分支①命中 ⇒ 所有者层必须真的会清洗 ===")
# 这是防"未来再漂移"的核心：检测器的括号形态分支必须是所有者层的**子集**。
CONTRACT = list(TRUE_CASES.values()) + [
    "m × 10 - ⁴ ……………( 1 / 式中：", "V1 / V2 ....(12)", "z ……(D.8",
]
for t in CONTRACT:
    if PAREN.search(t):
        cleaned = strip_formula_leader(t)
        changed = cleaned != t
        check(f"分支①命中⇒所有者会清洗：{t[:22]!r}", changed, True)
    else:
        print(f"  --  分支①未命中（由其他分支负责）：{t[:24]!r}")

print("\n=== ③' 反向：所有者层不清洗的文本，分支①必须不命中（误报根因）===")
for name, t in FALSE_CASES.items():
    check(f"所有者不动它⇒分支①不命中：{name[:26]}",
          PAREN.search(t) is None, True)

print()
if FAIL:
    print(f"❌ {len(FAIL)} 项失败：{FAIL}")
    sys.exit(1)
print("✅ 全部通过")
