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

## 判据（四条 + 一条守卫，互为对照）

1. **计数**：代码行（去掉**整行注释**）里 `$totalForRatchet` 恰好 8 次。
2. **赋值点唯一且是口径算式**：
   `$totalForRatchet = if ($caliberOk) { $totalRan - $trackedExcluded } else { $totalRan }`。
3. **不许混用**：含 `$baseTotal`（比较基准）/ `$totalToRecord`（记账）/ `$prevPassed`（派生）
   的代码行，**不得**出现 `$totalRan`。
   ⚠ 这一条是**前瞻式**的，别误读成"原样件在它上面成立"：原样件里**没有任何代码行**同时含锚点与
   `$totalRan`（全脚本唯一同现处在 `run-gates.ps1:180` 的**注释**里，且注释已被剥掉）
   ⇒ 它的价值是"**将来**有人写出混用行时抓住"，不是"当下有东西可抓"。
   本文件用**注入行**把它钉住（`test_anchor_mixing_is_caught`）—— 那是它唯一可测的形态。
3'. **锚点存在性（判据 3 的前置守卫，2026-10-09 补）**：`$baseTotal` / `$totalToRecord` /
   `$prevPassed` **必须各自出现在至少一行代码里**；缺一即报。
   为什么必须有：判据 3 是**同现式**检查 —— 锚点名一改，就没有任何行再含它 ⇒ **静默失效**。
4. **判据自己要被验**（否则「扫描器恒真」就是新的假绿）：把 8 处**逐处**改回 `$totalRan`，
   每一处都必须被本检测器报出；原样件必须零报；无关改动必须零报。
5. **`$baseTotal` 的首选来源恰有一处**（`$baseTotal = [int]$base.pytest_total`）——
   **2026-10-09 第 18 轮补，治审计 C2**。为什么单列：这一行**不含** `$totalForRatchet`
   ⇒ 判据 1 的计数不变；它后面还有 5 行含 `$baseTotal` ⇒ 判据 3' 的"存在性"也过；
   判据 3 是同现式 ⇒ 同样不报。**实测「只删这一行 ⇒ 零报」**（第 3 轮复核 B1 指出，一直挂着）。
   删/改它 ⇒ 棘轮比较基准会**悄悄**退成 `passed+skipped`（靠第 492 行的 `-le 0` 兜底），
   而**没有任何一条判据会提醒**。配套 `test_deleting_base_total_source_is_caught` /
   `test_base_total_source_swap_is_caught`。

## 边界（如实说，不许超出证据）

- 这是**接线**测试（静态），**不是算术**测试：它证明「判定点接的是棘轮口径」，
  **不**证明口径算式本身对（那由 `tests/test_gates_tracked_total.py` 与真跑兜）。
- 它按**标识符**锚定，**不按行号**（本仓已因「行号随编辑位移」吃过假红）。
  ⚠ **就地更正（2026-10-09，独立复核 `verify-freeze-ratchet-1` 打回这条措辞）**：
  **原话（保留，不删）**：「改标识符名（如把 `$baseTotal` 改名）⇒ 本测试要同步改，这是**有意**的 fail-closed。」
  **实测与它相反**：把 `$baseTotal` 全文改名成 `$ratchetBase`（只改名、语义不变）⇒ 本文件
  **照绿 `7 passed`**（复核在冻结树里跑，我自己在主仓也复现过一次）。原因是 `_ANCHORS` 那条
  「不许混用」检查**没有任何行再含 `$baseTotal`** ⇒ **静默失效**，即该锚点是
  **fail-open（静默失去保护）**，**不是** fail-closed。真正有牙的是**计数检查**（8 处变 7 处必红）。
  ⇒ 改这三个锚点名字时**不会有任何测试提醒你**，得自己记得同步本文件；
  想把它变成 fail-closed，须补一条「三个锚点必须都出现在代码行里」的前置断言。
  ✅ **2026-10-09（第 3 轮）已补** —— 见 `find_violations` 里「判据 3'」那一段，配套两条测试
  `test_anchor_names_are_present_in_code_lines` / `test_anchor_rename_is_caught`。
  实测：`$baseTotal` 全文改名成 `$ratchetBase` 后，本文件**由 `7 passed` 变红**（fail-closed 成立）。
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
#: 判据 5（2026-10-09 第 18 轮补，治审计 **C2**）：`$baseTotal` 的**首选来源**必须是基线的
#: `pytest_total`。**为什么必须单独钉**：那一行**不含** `$totalForRatchet`
#: ⇒ 删了它**不改判据 1 的计数**；而它后面还有 5 行含 `$baseTotal`
#: ⇒ **判据 3'（锚点存在性）也不报**；判据 3 是"同现式"，同样不报。
#: ⇒ 实测「只删 `$baseTotal = [int]$base.pytest_total` ⇒ **零报**」（第 3 轮复核 B1 已指出，一直挂着）。
_BASE_ASSIGN = re.compile(r"^\s*\$baseTotal\s*=\s*\[int\]\$base\.pytest_total\s*$")


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

    # 判据 3'（**判据 3 的前置守卫**，2026-10-09 补）：三个锚点必须**都还在代码行里**。
    # ⚠ 为什么必须有：判据 3 是**同现式**检查 —— 锚点名一改，就没有任何行再含它 ⇒
    #   **静默失效（fail-open）**。实测（独立复核 `verify-freeze-ratchet-1` 打回 + 我在主仓复现）：
    #   把 `$baseTotal` 全文改名成 `$ratchetBase`（只改名、语义不变）⇒ 原实现照绿 `7 passed`。
    #   ⇒ 锚点缺一即报；真改了名就**必须**同步本文件的 `_ANCHORS`（这条把它变成 fail-closed）。
    for anchor in _ANCHORS:
        if not any(anchor in ln for ln in code):
            problems.append(
                f"锚点 {anchor} 在代码行里一次都没出现 ⇒ 判据 3（不许混用）**静默失效**（fail-open）；"
                f"若确实改了名，请同步本文件的 `_ANCHORS`"
            )

    # 判据 3：不许混用（比较基准 / 记账 / 派生 三处所在行不得出现旧写法）
    for anchor in _ANCHORS:
        for ln in code:
            if anchor in ln and LEGACY in ln:
                problems.append(
                    f"同一行既用 {anchor} 又用 {LEGACY}"
                    f"（判定点退回了实测总数）：{ln.strip()}"
                )

    # 判据 5（2026-10-09 第 18 轮补，治审计 C2）：`$baseTotal` 的**首选来源**必须恰有一处。
    # ⚠ 删掉/改掉它 ⇒ 棘轮比较基准会**悄悄**退成"passed+skipped"（第 492 行的 `-le 0` 兜底），
    #   而判据 1/2/3/3' **一条都不会报** —— 那正是 C2 说的"没牙"。
    n_base = sum(1 for ln in code if _BASE_ASSIGN.match(ln))
    if n_base != 1:
        problems.append(
            f"`$baseTotal = [int]$base.pytest_total` 有 {n_base} 处，应为 1 处"
            "（删了/改了它 ⇒ 棘轮比较基准悄悄换掉，而计数与锚点检查都不会报）"
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


# ─────────────── 判据 3'：锚点存在性（判据 3 的 fail-closed 守卫）───────────────


def test_anchor_names_are_present_in_code_lines() -> None:
    """三个锚点必须各自出现在**至少一行代码**里（缺一 ⇒ 判据 3 静默失效）。

    ⚠ 这是 2026-10-09 独立复核打回后补的守卫：原实现里锚点名一改，
    同现式检查**没有任何行再含它** ⇒ 静默失效（fail-open），而本文件**照绿**。
    """
    code = _code_lines(_read())
    missing = [a for a in _ANCHORS if not any(a in ln for ln in code)]
    assert missing == [], (
        "以下锚点在代码行里一次都没出现 ⇒ 判据 3（不许混用）会静默失效（fail-open）："
        f"{missing}；若确实改名了，请同步本文件的 `_ANCHORS`"
    )


def test_anchor_rename_is_caught() -> None:
    """**核心**：把任一锚点全文改名（只改名、语义不变）⇒ 必须报违规。

    ⚠ 变异用**不含原锚点子串**的新名（如 `$baseTotal` → `$ratchetBase`）：
    若用 `$baseTotal2` 这类"含原串"的名字，子串检查仍会命中，测不出这条守卫。
    """
    text = _read()
    renames = {
        "$baseTotal": "$ratchetBase",
        "$totalToRecord": "$totalToPersist",
        "$prevPassed": "$previousPassed",
    }
    for anchor, new_name in renames.items():
        mutated = text.replace(anchor, new_name)
        assert mutated != text, f"前置不成立：脚本里找不到 {anchor}"
        problems = find_violations(mutated)
        assert problems, f"{anchor} 改名成 {new_name} 后**没被报出**（fail-open 复现）"


def test_anchor_mixing_is_caught() -> None:
    """注入一行「锚点 + `$totalRan`」混用 ⇒ 必须报出（证明判据 3 不是空转）。

    ⚠ 原样件里没有任何**代码行**同时含两者（唯一同现处在 `run-gates.ps1:180` 的注释里，
    已被剥掉）⇒ 这一条不靠原样件成立，靠"将来有人写出混用行时抓住"。
    这里用**注入行**把它钉住 —— 那是判据 3 唯一可测的形态。
    """
    text = _read()
    injected = text + "\nif ($baseTotal -lt $totalRan) { }\n"
    problems = find_violations(injected)
    assert problems, "锚点行混用没被报出（判据 3 空转）"
    assert any("$baseTotal" in p and "$totalRan" in p for p in problems), (
        "报出的不是「混用」那一条：\n  - " + "\n  - ".join(problems)
    )


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


# ───────────────── 判据 5 的自验（治审计 C2："只删 $baseTotal 赋值 ⇒ 零报"）─────────────────


def test_base_total_primary_source_exists() -> None:
    """原样件里 `$baseTotal` 的首选来源**恰有一处**（判据 5 的地基）。"""
    n = sum(1 for ln in _code_lines(_read()) if _BASE_ASSIGN.match(ln))
    assert n == 1, f"`$baseTotal = [int]$base.pytest_total` 应恰 1 处，实测 {n} 处"


def test_deleting_base_total_source_is_caught() -> None:
    """**C2 的核心**：删掉 `$baseTotal = [int]$base.pytest_total` 那一行 ⇒ **必须报违规**。

    ⚠ 为什么单独一条：这一行**不含** `$totalForRatchet`（判据 1 不报）、
    它后面还有 5 行含 `$baseTotal`（判据 3' 不报）、判据 3 是同现式（不报）
    ⇒ **不补判据 5 时，删它零报**（第 3 轮复核 B1 指出、一直挂着的 C2）。
    """
    text = _read()
    lines = text.splitlines(keepends=True)
    idx = next((i for i, ln in enumerate(lines) if _BASE_ASSIGN.match(ln)), None)
    assert idx is not None, "找不到 `$baseTotal = [int]$base.pytest_total`（锚点变了）"
    mutated = "".join(lines[:idx] + lines[idx + 1:])
    problems = find_violations(mutated)
    assert any("baseTotal" in p for p in problems), (
        "删掉 `$baseTotal` 的首选来源行竟然**零报** ⇒ 判据 5 没牙（审计 C2 未闭合）"
    )


def test_base_total_source_swap_is_caught() -> None:
    """把首选来源**换成别的字段**（语义变了但行还在）⇒ 也必须报。"""
    text = _read()
    lines = text.splitlines(keepends=True)
    idx = next((i for i, ln in enumerate(lines) if _BASE_ASSIGN.match(ln)), None)
    assert idx is not None, "找不到首选来源行（锚点变了）"
    # ⚠ 逐行替换：`_BASE_ASSIGN` 用 `^…$` 但**没开 MULTILINE**，对整篇 `sub` 不会命中
    #   （判据里是**逐行** `match`，所以那里是对的）。
    lines[idx] = lines[idx].replace("pytest_total", "pytest_passed")
    problems = find_violations("".join(lines))
    assert any("baseTotal" in p for p in problems), (
        "把首选来源从 `pytest_total` 换成 `pytest_passed` 竟然零报 ⇒ 判据 5 没牙"
    )
