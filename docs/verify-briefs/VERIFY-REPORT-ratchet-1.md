# 独立复核报告 —— ratchet-1 批次（复核员 general-purpose-1）

## 0. 冻结与提取树信息

| 项 | 读数 |
|---|---|
| 提取树 | `D:/AI/verify-trees/ratchet-1`（git worktree, detached HEAD） |
| HEAD（复核开始 / 结束） | `c281288cfe2d069195b0313412a364c068bcc946`（两次一致） |
| tag `verify-freeze-ratchet-1` | `c281288cfe2d069195b0313412a364c068bcc946`（= HEAD） |
| `git rev-list --count c281288..verify-freeze-ratchet-1` | **0** ✓ |
| `git status --short` 开始 | 空（干净） |
| `git status --short` 结束（变异全还原后） | 空（干净）✓；仅本报告文件 `VERIFY-REPORT-ratchet-1.md` 为交付物新增未跟踪 |
| 提交改动范围 | 5 文件：`scripts/pssa-guard.ps1`(+8)、`scripts/verify-pssa-command-layer.ps1`、`tests/test_run_gates_ratchet_wiring.py`(+203)、`docs/NEXT-DEV-PLAN-2026-09-28.md`、`docs/RETRIEVAL-LONG-RANGE-PLAN.md` —— 与描述一致 |
| `run-gates.ps1` 复核前后 md5 | `46bc4b16e90cba153c58c54f3c7d785e`（一致，未被污染） |

复核者：**独立重跑取证，未修改主仓 `D:/AI/work space/zcode`**。所有变异件/探针建在系统临时目录 `D:/tmp`。

8 个判定点（1 基行号，代码行；第 9 次出现 `run-gates.ps1:222` 在整行注释里，不计）：
`487, 493, 495, 526, 529, 530, 597, 603`。测试文件共 **7** 条测试函数。

---

## ① 逐处变异表（每次只改一处，改回 `$totalRan`）

跑法：`cd D:/AI/verify-trees/ratchet-1 && <venv>/python -m pytest tests/test_run_gates_ratchet_wiring.py -q`；每次变异后 `git checkout -- scripts/run-gates.ps1` 还原。

| # | 变异行 | 红条数 | 红的是哪条测试 |
|---|---|---|---|
| 1 | 487 | **5** | pristine…all_eight_sites / exactly_eight_code_sites_are_found / every_single_site_mutation_is_caught / detector_is_not_always_true / comment_occurrence_is_excluded_from_the_count |
| 2 | 493 | **5** | 同上 5 条 |
| 3 | 495 | **5** | 同上 5 条 |
| 4 | 526 | **5** | 同上 5 条 |
| 5 | 529 | **5** | 同上 5 条 |
| 6 | 530 | **5** | 同上 5 条 |
| 7 | 597 | **5** | 同上 5 条 |
| 8 | 603 | **5** | 同上 5 条 |
| — | 全改回（8 处） | **5** | 同上 5 条 |
| — | 原样件 | **0** | 7 条全绿（`7 passed`） |

- 8/8 **每一处都至少红 1 条** ⇒ 作者自报结论 1 **复现成立**。
- 作者自报结论 2「原样件 7 条全绿」**复现成立**（`7 passed in 0.06s`）。
- 每次 5 红 / 2 绿：恒绿的两条是 `test_run_gates_exists` 与 `test_all_reads_mutation_is_caught`。
- **补充读数（复核发现）**：8 处变异给出的红名**完全相同**，且主导红来自"计数 8→7"这条断言（`test_exactly_eight_code_sites_are_found` 的 `len(sites)==8`、`test_every_single_site_mutation_is_caught:165` 的前置 `assert len(sites)==EXPECTED_SITES` 等）。即：本测试对"逐处"的敏感度实质等价于**计数检查**，"逐处循环"本身未提供独立判别力。这不推翻"8/8 全红"，仅说明其红因。

---

## ② 假红风险表（作者未量，复核补量）

| 变异 | 类别 | failed / passed | 判定 |
|---|---|---|---|
| (a) 追加一行注释（含 `$totalForRatchet` 与 `$totalRan` 字样） | 良性 | **0 / 7（绿）** | 无误伤 ✓ |
| (b) 无关标识符改名 `$slowBudget` → `$stepBudget`（`run-gates.ps1:296-298`） | 良性 | **0 / 7（绿）** | 无误伤 ✓ |
| (c) 锚行 `493/495/597/603` 整体重排（反转顺序，不改内容） | 良性 | **0 / 7（绿）** | 无误伤 ✓ |
| (d) `$baseTotal` → `$ratchetBase`（仅改名、语义不变，全文替换） | 良性 | **0 / 7（绿）** | 无误伤 ✓ |

- (c)(d) **均未变红** ⇒ 不存在"良性重构被误伤"的假红。
- **复核发现（文档过度声称）**：测试文件 `tests/test_run_gates_ratchet_wiring.py:41` 的 docstring 写「改标识符名（如把 `$baseTotal` 改名）⇒ 本测试要同步改，这是**有意**的 fail-closed」。实测 (d) 为**绿**，该句**与实测不符**：把 `$baseTotal` 改名后 `_ANCHORS` 里那条"不许混用"检查**静默失效**（无任何行再含 `$baseTotal`），测试照绿。方向上这不是 fail-closed，而是该锚点的 **fail-open（静默失去保护）**。因 `$baseTotal` 改动不影响 8 处计数与赋值点，其他断言不兜它。
  - 严重度：低（`$baseTotal` 极少被重命名，且非本批次三条自报结论之一）。**不作为打回依据，仅记录为 docstring 与行为不符。**

---

## ③ PSSA 覆盖面复算

- `Invoke-ScriptAnalyzer` 版本：**PSScriptAnalyzer 1.25.0**（`C:\Users\Zegel\Documents\PowerShell\Modules\PSScriptAnalyzer\1.25.0`，CurrentUser 候选存在）。
- 跑法：`pwsh -NoProfile -File D:/tmp/pssa_probe.ps1`，按 `verify-pssa-command-layer.ps1` 同规则（`PSUseDeclaredVarsMoreThanAssignments`）对变异件调 `Invoke-ScriptAnalyzer`；变异件全部建在 `D:/tmp/pssa-probe`（未写提取树/主仓）。
- 原件 SHA256 前 16 位：`D7BA23DD004316EA`。

| 变异 | PSSA 命中 |
|---|---|
| 原样件 | **0** |
| 8 处代码点**逐处**单独改回（另含注释点 i=0） | **逐处均为 0**（合计 0） |
| 7 个读取点全改回、只留赋值点 | **1**（`Line 487: The variable 'totalForRatchet' is assigned but never used.`） |

**结论**：作者那句「`pssa-guard` 只抓得住『7 个读取点全改回』那一种」**成立**。原样件 0 命中 / 任意一处单独改回 0 命中 / 全改 1 命中，三行读数与作者自报**完全一致**。

---

## 5. 总判：**通过**

- 三条自报结论**全部独立复现**：① 8/8 逐处变异全红（每处 5 红）；② 原样件 7 条全绿；③ PSSA 仅抓"全改"那一种（0/0/1）。
- 4 类良性改动（含注释、无关改名、锚行重排、`$baseTotal` 改名）**全部保持绿**，无假红。
- **非阻塞发现 2 条**（不影响本批验收）：
  1. 逐处变异的红因实质是"计数 8→7"，逐处循环未提供独立判别力（① 补充读数）；
  2. `tests/test_run_gates_ratchet_wiring.py:41` 关于 `$baseTotal` 改名的 "fail-closed" 表述与实测相反（实为静默 fail-open），属 docstring 过度声称。

---

## 6. 明确未做清单

- **未**核 `docs/NEXT-DEV-PLAN-2026-09-28.md`、`docs/RETRIEVAL-LONG-RANGE-PLAN.md` 两处文档内容与措辞（仅核对提交 stat 的文件清单）。
- **未**跑全仓测试套件 / `run-gates.ps1` 真实门禁（本任务只要求上述三块证据）。
- **未**验证 `gates-tracked-total.py` 口径算式的算术正确性（超出本批范围，属 `tests/test_gates_tracked_total.py` 职责）。
- **未**在干净机/无 PSSA 环境下验证门禁降级行为。
- PSSA 部分为**逐处穷举**（8 代码点 + 1 注释点，全覆盖），非抽样。
