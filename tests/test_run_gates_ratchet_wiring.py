"""`run-gates.ps1` 棘轮的**接线**测试：8 处判定点必须接 `$totalForRatchet`，不许退回 `$totalRan`。

## 这一组在守什么

`scripts/run-gates.ps1` 的「只涨不跌」棘轮，判据用的总账必须是**只算受版本控制的用例**的那个数：

    $totalForRatchet = 实测总数($totalRan) − 未跟踪用例数($trackedExcluded)

助手是 `scripts/gates-tracked-total.py`。2026-09-26 复核（MED-1「定时炸弹」）把它搬进代码
（`25c5c97`），但**剩下一半没收**：把 8 处 `$totalForRatchet` 逐字改回 `$totalRan`
⇒ 22 条相关测试**全绿零红** —— 因为本脚本自身没有单测、全仓对它的引用全是注释。

## 已有那道门禁抓不住「任意一处」

`scripts/pssa-guard.ps1`（PSSA 规则 `PSUseDeclaredVarsMoreThanAssignments`）**只抓得住
「把 7 个读取点全改回去」那一种**。本机实测（PSSA 1.25.0，2026-10-09）：

| 变异 | PSSA 命中 |
|---|---|
| 原样件 | 0 |
| **任意一处**单独改回 `$totalRan`（8 处逐处试过） | **0** |
| 7 个读取点全改回、只留赋值点 | 1 |

⇒ 验收要求的「**任意一处**改坏 ⇒ 有测试变红」**当时并不成立**。本文件补上这一条。

## 判据（四条，互为对照）

1. **计数**：代码行（去掉**整行注释**）里 `$totalForRatchet` 恰好 8 次。
2. **赋值点唯一且是口径算式**：
   `$totalForRatchet = if ($caliberOk) { $totalRan - $trackedExcluded } else { $totalRan }`。
3. **不许混用**：含 `$baseTotal`（比较基准）/ `$totalToRecord`（记账）/ `$prevPassed`（派生）
   的代码行，**不得**出现 `$totalRan`。
4. **判据自己要被验**（否则「扫描器恒真」就是新的假绿）：把 8 处**逐处**改回 `$totalRan`，
   每一处都必须被本检测器报出；原样件必须零报；无关改动必须零报。

## 边界（如实说，不许超出证据）

- 这是**接线**测试（静态），**不是算术**测试：它证明「判定点接的是棘轮口径」，
  **不**证明口径算式本身对（那由 `tests/test_gates_tracked_total.py` 与真跑兜）。
- 它按**标识符**锚定，**不按行号**（本仓已因「行号随编辑位移」吃过假红）。
  改标识符名（如把 `$baseTotal` 改名）⇒ 本测试要同步改，这是**有意**的 fail-closed。
- 跑在 `pytest` 里 ⇒ 属 `-Full` 档；`-Quick` 档仍由 `pssa-guard` 兜「全改」那一种。
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_GATES = REPO / "scripts" / "run-gates.ps1"
CALIBER_HELPER = REPO / "scripts" / "gates-tracked-total.py"

#: 棘轮口径的判定变量（2026-09-26 复核 MED-1 修复 `25c5c97` 引入）。
TOKEN = "$totalForRatchet"
#: 修复前的旧写法（实测总数）—— 判定点退回它就是这次要防的缺陷。
LEGACY = "$totalRan"
#: 判定点数量。⚠ 与 `run-gates.ps1:222` 的注释同口径；改了那边要同步这里。
EXPECTED_SITES = 8

_OCC = re.compile(r"\$totalForRatchet\b")
#: 赋值点必须是口径算式（`$caliberOk` 为假时退回实测总数 —— 那是**有意的**降级，不是缺陷）。
_ASSIGN = re.compile(
    r"^\s*\$totalForRatchet\s*=\s*if\s*\(\s*\$caliberOk\s*\)\s*"
    r"\{\s*\$totalRan\s*-\s*\$trackedExcluded\s*\}\s*else\s*\{\s*\$totalRan\s*\}\s*$"
)
#: 三处「必须接棘轮口径」的语义锚（含它就不得再出现旧写法）。
_ANCHORS = ("$baseTotal", "$totalToRecord", "$prevPassed")


def _read() -> str:
    return RUN_GATES.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """去掉**整行注释**后的代码行。

    本文件里 `$totalForRatchet` 共出现 9 次，第 9 次在 `run-gates.ps1:222` 的**注释**里
    （"本文件 8 处 $totalForRatchet …"）⇒ 不剥注释就会把 8 数成 9。
    """
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def find_violations(text: str) -> list[str]:
    """返回违规说明；**空列表 = 接线正确**。"""
    code = _code_lines(text)
    problems: list[str] = []

    # 判据 1：计数
    n = sum(len(_OCC.findall(ln)) for ln in code)
    if n != EXPECTED_SITES:
        problems.append(
            f"代码行里 {TOKEN} 出现 {n} 次，应为 {EXPECTED_SITES} 次"
            f"（少 = 某处判定点退回了 {LEGACY}）"
        )

    # 判据 2：赋值点唯一且是口径算式
    assigns = [ln for ln in code if re.match(r"^\s*\$totalForRatchet\s*=", ln)]
    if len(assigns) != 1:
        problems.append(f"{TOKEN} 赋值点有 {len(assigns)} 处，应为 1 处")
    elif not _ASSIGN.match(assigns[0]):
        problems.append(
            "赋值点不是棘轮口径算式（应为 "
            f"`{TOKEN} = if ($caliberOk) {{ $totalRan - $trackedExcluded }} else {{ $totalRan }}`）："
            + assigns[0].strip()
        )

    # 判据 3：不许混用（比较基准 / 记账 / 派生 三处所在行不得出现旧写法）
    for anchor in _ANCHORS:
        for ln in code:
            if anchor in ln and LEGACY in ln:
                problems.append(
                    f"同一行既用 {anchor} 又用 {LEGACY}"
                    f"（判定点退回了实测总数）：{ln.strip()}"
                )

    return problems


def _site_line_indices(text: str) -> list[int]:
    """8 个判定点所在的**行号**（0 基；只算代码行）。"""
    return [
        i
        for i, ln in enumerate(text.splitlines())
        if not ln.lstrip().startswith("#") and TOKEN in ln
    ]


def _mutate_line(text: str, line_index: int) -> str:
    """把第 `line_index` 行里的 `$totalForRatchet` 改回 `$totalRan`。"""
    lines = text.splitlines(keepends=True)
    lines[line_index] = _OCC.sub(LEGACY, lines[line_index], count=1)
    return "".join(lines)


# ───────────────────────── 判据 4：接线正确 + 判据自验 ─────────────────────────


def test_run_gates_exists() -> None:
    assert RUN_GATES.is_file(), f"找不到门禁脚本：{RUN_GATES}"
    assert CALIBER_HELPER.is_file(), f"找不到棘轮口径助手：{CALIBER_HELPER}"


def test_pristine_file_wires_ratchet_at_all_eight_sites() -> None:
    """原样件必须零违规 —— 否则下面的自验没有意义。"""
    problems = find_violations(_read())
    assert problems == [], "run-gates.ps1 的棘轮接线被改动：\n  - " + "\n  - ".join(problems)


def test_exactly_eight_code_sites_are_found() -> None:
    """8 个判定点必须都能被**逐处**定位（自验的地基）。"""
    sites = _site_line_indices(_read())
    assert len(sites) == EXPECTED_SITES, (
        f"代码行里定位到 {len(sites)} 个判定点，应为 {EXPECTED_SITES} 个："
        f"行号 {[i + 1 for i in sites]}"
    )


def test_every_single_site_mutation_is_caught() -> None:
    """**核心判据**：把 8 处**任意一处**改回 `$totalRan` ⇒ 必须报违规。

    ⚠ 这一条正是 PSSA 门禁抓不住的那一半（本机实测：逐处变异命中全 0）。
    """
    text = _read()
    sites = _site_line_indices(text)
    assert len(sites) == EXPECTED_SITES, "前置不成立：判定点数不是 8"

    missed: list[int] = []
    for idx in sites:
        problems = find_violations(_mutate_line(text, idx))
        if not problems:
            missed.append(idx + 1)
    assert missed == [], (
        "以下判定点被单独改回 $totalRan 却**没被报出**（本测试已失效）："
        f"行 {missed}"
    )


def test_all_reads_mutation_is_caught() -> None:
    """7 个读取点全改回（PSSA 唯一抓得住的那一种）也必须被本检测器报出。"""
    text = _read()
    sites = _site_line_indices(text)
    mutated = text
    for idx in sites:
        mutated = _mutate_line(mutated, idx)
    assert find_violations(mutated), "全改回的变异件没被报出"


def test_detector_is_not_always_true() -> None:
    """反向自验：无关改动（改注释、改无关标识符）必须**零报** —— 防「扫描器恒真」。"""
    text = _read()
    # ① 只动注释：注释里的 token 不该被计入
    assert find_violations(text + "\n# 顺手加一行注释：$totalForRatchet / $totalRan\n") == []
    # ② 无关标识符改名
    assert find_violations(text.replace("$slowBudget", "$stepBudget")) == []


def test_comment_occurrence_is_excluded_from_the_count() -> None:
    """文档化那第 9 次出现（注释）**不算**判定点 —— 防止有人把注释删掉就以为少了一处。"""
    text = _read()
    total = len(_OCC.findall(text))
    code = sum(len(_OCC.findall(ln)) for ln in _code_lines(text))
    assert code == EXPECTED_SITES
    assert total >= code, "全文出现次数不该少于代码行里的次数"
