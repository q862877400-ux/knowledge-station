# 独立复核报告 —— ratchet-2 批次（复核员 general-purpose-1）

> 独立重跑取证，**未修改主仓 `D:/AI/work space/zcode`**。所有变异件/探针建在系统临时目录 `D:/tmp`，
> 变异均作用于提取树内 `scripts/run-gates.ps1`，每次用 `git checkout -- scripts/run-gates.ps1` 还原。

## 0. 冻结与提取树信息

| 项 | 读数 |
|---|---|
| 提取树 | `D:/AI/verify-trees/ratchet-2`（`git worktree add --detach`, detached HEAD） |
| HEAD（复核开始 / 结束） | `7992f9d8e01fdcf81cbd4261f870356b6e566ead`（两次一致） |
| tag `verify-freeze-ratchet-2` | `7992f9d8e01fdcf81cbd4261f870356b6e566ead`（= HEAD） |
| `git rev-list --count 7992f9d^..verify-freeze-ratchet-2` | **1** ✓ |
| `git status --short` 开始 | 空（干净） |
| `git status --short` 结束（变异全还原后） | 空（干净）✓；仅本报告 `docs/verify-briefs/VERIFY-REPORT-ratchet-2.md` 为交付物新增未跟踪 |
| 提交改动范围（`git show --name-only 7992f9d`） | **仅 1 文件**：`tests/test_run_gates_ratchet_wiring.py`（+76 / −2）—— 与描述一致，**未碰 `scripts/run-gates.ps1`** |
| `scripts/run-gates.ps1` md5（本批） | `46bc4b16e90cba153c58c54f3c7d785e` |
| 同上批报告 md5 比对 | `46bc4b16e90cba153c58c54f3c7d785e` = 上批（ratchet-1 报告第 14 行）⇒ **脚本未变** |

补充核实：
- 测试函数 **10** 条（上版 `7992f9d^` 为 7 条；本批 diff 新增 3 条：`test_anchor_names_are_present_in_code_lines` / `test_anchor_rename_is_caught` / `test_anchor_mixing_is_caught`）。
- 8 个判定点（1 基行号，代码行）：`487, 493, 495, 526, 529, 530, 597, 603`。
- `$totalForRatchet` 计数：全文 9 次 / 代码行 8 次 / 唯一注释命中在 `run-gates.ps1:222`（与 `_code_lines` docstring 一致）。

跑法（cwd = 提取树，解释器 = 主仓 venv）：
`cd "D:/AI/verify-trees/ratchet-2" && "D:/AI/work space/zcode/.venv/Scripts/python.exe" -m pytest tests/test_run_gates_ratchet_wiring.py -q`

---

## ① 三条自报结论逐条复现

| 自报 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 1. 原样件 | `10 passed` | `10 passed in 0.14s` | **复现** |
| 2. fail-closed（`$baseTotal` 全文 → `$ratchetBase`） | 变红 | **`4 failed / 6 passed`**；`git checkout` 还原后 **`10 passed`** | **复现**（数字与作者一致） |
| 3. 判据 3' 有牙（三锚点任一消失 ⇒ 报违规） | 报违规 | 三锚点逐个改名（不含原串）**均报**，见 A1 | **复现** |

自报 2 的红的是这 4 条：
`test_pristine_file_wires_ratchet_at_all_eight_sites` / `test_anchor_names_are_present_in_code_lines` /
`test_anchor_rename_is_caught` / `test_detector_is_not_always_true`。

---

## ② 额外证据 A–I 逐项读数表

说明：`find_violations` 直接探针 = 调用被验模块的检测函数（**报/不报**）；pytest 列 = 变异真实脚本后跑测试的 `failed/passed`。

| 项 | 变异 | 期望 | 实测 failed/passed | 红的是哪条 / 报出内容 |
|---|---|---|---|---|
| **A1** | `$baseTotal→$ratchetBase`、`$totalToRecord→$totalToPersist`、`$prevPassed→$previousPassed`（逐个子串不含原串） | 每处必报 | 探针：**3/3 均 REPORT**（各 1 条「锚点…一次都没出现」） | 报「锚点 X 在代码行里一次都没出现 ⇒ 判据 3 静默失效」 |
| **A2** | `$baseTotal→$baseTotal2`、`$totalToRecord→$totalToRecordX`、`$prevPassed→$prevPassedNew`（**含原串**） | 设计边界，如实记 | 探针：**3/3 均 CLEAN（零报）** | 无。子串匹配下「含原串」仍算存在 ⇒ 已知边界，**不打回** |
| **B1** | 只删第 491 行 `$baseTotal = [int]$base.pytest_total` | 任务书期望「必须报」 | pytest：**`0 failed / 10 passed`（零报）** ⚠ | 见下方「非阻塞发现-1」 |
| **B2** | 删掉**所有**含 `$baseTotal` 的代码行 | 必报 | 探针：**REPORT（2 条）** | ① 计数 `$totalForRatchet` 3 次（应 8）② 锚点 `$baseTotal` 缺失 |
| **C** | 末尾注入 `if ($baseTotal -lt $totalRan) { }` | 必报，且须报「混用」 | pytest：**`2 failed / 8 passed`** | 红：`test_pristine_file_wires_ratchet_at_all_eight_sites`、`test_detector_is_not_always_true`；报出条目为**「同一行既用 $baseTotal 又用 $totalRan」** ✓；计数类条目 = 0（注入行不含 token）✓ |
| **D** | 机械核 docstring 事实断言 | 成立 | 全文含锚点且含 `$totalRan` 的行 **只有第 180 行**，且是注释；**代码行同现 = 0** | **成立** ✓（docstring 所述 `run-gates.ps1:180` 注释唯一同现，正确） |
| **E①** | 追加注释行（含 `$totalForRatchet` / `$totalRan`） | 零红 | pytest：**`0 failed / 10 passed`** | 无误伤 ✓ |
| **E②** | 无关标识符改名 `$slowBudget → $stepBudget`（脚本内 3 处，296–298） | 零红 | pytest：**`0 failed / 10 passed`** | 无误伤 ✓（非空转：`$slowBudget` 确实存在 3 次） |
| **E③** | 含锚点代码行整体逆序重排（内容不变） | 零红 | pytest：**`0 failed / 10 passed`** | 无误伤 ✓ |
| **E④** | 判定点第 487 行加尾随空格 | 零红 | pytest：**`0 failed / 10 passed`** | 无误伤 ✓ |
| **F** | 反向自验（防扫描器恒真/恒绿） | 能构造零报与有报两种 | 零报样本：原样件 → `CLEAN`；有报样本：混用注入 → `REPORT`；全文 `$totalForRatchet→$totalForRatchetX` → `REPORT`（计数 0 + 赋值点 0） | **两个方向均可构造** ✓（非恒真、非恒绿） |
| **G** | 8 处判定点逐处改回 `$totalRan` | 8/8 全红 | **8/8 全红，每处 `5 failed / 5 passed`**；全改回亦 `5 failed / 5 passed` | 红名固定 5 条（见下）；红因见「非阻塞发现-2」 |
| **H** | PSSA 覆盖面 | md5 一致则沿用 | 本批 md5 = 上批 md5（一致）⇒ **沿用上批三行读数：原样 0 / 逐处 0 / 全改 1** | **未重跑**（脚本未变，按任务书授权沿用；见「未做清单」） |
| **I** | 改动面核实 | 仅 1 文件、仅 `tests/` | `git show --stat 7992f9d`：`tests/test_run_gates_ratchet_wiring.py \| 78 ++\| 1 file changed, 76 insertions(+), 2 deletions(-)` | **成立** ✓ |

**G 的固定 5 条红名**（8 处 + 全改，完全一致）：
`test_pristine_file_wires_ratchet_at_all_eight_sites` / `test_exactly_eight_code_sites_are_found` /
`test_every_single_site_mutation_is_caught` / `test_detector_is_not_always_true` /
`test_comment_occurrence_is_excluded_from_the_count`。
恒绿的 5 条含 `test_all_reads_mutation_is_caught`。

**G 的逐处违规类型矩阵**（`find_violations` 直接探针，`计数`=8→7 / `赋值`=赋值点消失 / `混用`=同现锚点+`$totalRan`）：

| 行(1基) | 计数 | 赋值 | 混用 | 原行片段 |
|---|---|---|---|---|
| 487 | ✔ | ✔ | — | `$totalForRatchet = if ($caliberOk) { … }` |
| 493 | ✔ | — | ✔ | `if ($totalForRatchet -lt $baseTotal) {` |
| 495 | ✔ | — | ✔ | `$totalForRatchet, $baseTotal, …` |
| 526 | ✔ | — | ✔ | `$msg = "   pytest 总账 $totalForRatchet ≥ 基线 $baseTotal …` |
| 529 | ✔ | — | ✔ | `if ($totalForRatchet -gt $baseTotal) {` |
| 530 | ✔ | — | ✔ | `Write-Host ("   （比基线多 $($totalForRatchet - $baseTotal) …` |
| 597 | ✔ | — | ✔ | `$totalToRecord = $totalForRatchet` |
| 603 | ✔ | — | ✔ | `$prevPassed = [int]$totalForRatchet - …` |

---

## ③ 假红风险表

| 变异 | 类别 | failed/passed | 判定 |
|---|---|---|---|
| E① 追加注释（含两 token） | 良性 | 0 / 10 | 无误伤 ✓ |
| E② 无关标识符改名 `$slowBudget→$stepBudget` | 良性 | 0 / 10 | 无误伤 ✓ |
| E③ 锚行整体重排（内容不变） | 良性 | 0 / 10 | 无误伤 ✓ |
| E④ 判定点行加尾随空格 | 良性 | 0 / 10 | 无误伤 ✓ |
| **`$baseTotal → $ratchetBase` 全文改名** | **本批故意变红** | **4 / 6** | **预期行为，不是假红** |

- **本批故意变红的那一类说明**：上一批（ratchet-1）把「`$baseTotal` 改名」判为**良性/零红**，并据此打回
  「docstring 声称 fail-closed 与实测相反（实为 fail-open）」。本批修复的目标正是把这一类从 fail-open 翻转为
  **fail-closed** ⇒ 现在改名**变红是预期结果**，与「良性改动被误伤」的假红**性质相反**，**不计入假红**。
- 4 类真良性改动（E①–E④）全部 `0 failed / 10 passed`，**零误伤**。

---

## 5. 总判：**通过**

- 三条自报结论**全部独立复现**：① 原样件 `10 passed`；② `$baseTotal` 改名 ⇒ `4 failed / 6 passed`，还原 ⇒ `10 passed`；
  ③ 三锚点任一改名（不含原串）均报违规。
- 核心修复目标达成：`$baseTotal` 改名由上一批的 **fail-open（照绿）** 翻转为 **fail-closed（变红）**，且无良性误伤。
- 改动面干净：仅 1 文件、仅 `tests/`；`run-gates.ps1` md5 与上批一致（未改）。
- **非阻塞发现 2 条**（不影响本批验收，供 team-lead 参考）：

### 非阻塞发现-1：B1「只删锚点赋值行」零报（与任务书 B 期望不符）
- **怎么复现**：在提取树里删掉 `scripts/run-gates.ps1` 第 491 行 `$baseTotal = [int]$base.pytest_total`，跑
  `"D:/AI/work space/zcode/.venv/Scripts/python.exe" -m pytest tests/test_run_gates_ratchet_wiring.py -q`。
- **期望**：任务书 B 说「必须报（要么报锚点缺失、要么报别的）」。
- **实际**：`0 failed / 10 passed`（零报）。原因：判据 3' 的契约是「锚点必须**出现在至少一行代码里**」；删掉一行后
  `$baseTotal` 仍出现在其余 8 行 ⇒ 存在性仍成立 ⇒ 不报。**B2**（删掉所有含锚点的代码行）则正常报出。
- **定级**：**非打回级**。判据 3' 是「锚点存在性」守卫（专治改名导致锚点整体消失），删单行不改变存在性，属契约内的
  正确行为；「变量被使用但未赋值」应由 PSSA/PowerShell 严格模式兜，非本静态接线测试职责。**仅记录任务书 B 期望偏强**。

### 非阻塞发现-2：G 的红因细化（部分推翻上一批「无独立判别力」的措辞）
- 上一批结论：「逐处变异红因实质是『计数 8→7』，逐处循环无独立判别力」。
- 本批实测：**8/8 全红成立**；红因**不止计数**——`487` 红因 = 计数 + **赋值点消失**；其余 **7 处**红因 = 计数 +
  **判据 3「混用」命中**（这 7 行原位含锚点，改回 `$totalRan` 后成同现行）。即在 `find_violations` 层面，
  7/8 处存在**独立于计数的混用信号**；但**测试函数** `test_every_single_site_mutation_is_caught` 只断言「非空」，
  其红名仍被计数类断言主导 ⇒ 「红名无独立判别力」在**测试层面**成立，在**检测函数层面**不成立。如实记录。

---

## 6. 明确未做清单

- **未**重跑 PSSA（`Invoke-ScriptAnalyzer`）：因本批 `run-gates.ps1` md5 与上批完全一致，按任务书授权**沿用上批三行读数（0/0/1）**，
  未在本机重新执行 `pssa-guard`/`Invoke-ScriptAnalyzer`。
- **未**跑 `scripts/run-gates.ps1` 真实门禁（会抢门禁锁，任务书禁止）。
- **未**跑全仓测试套件；**未**核 `tests/test_gates_tracked_total.py` 的口径算术正确性（超出本批范围）。
- **未**触碰主仓 `docs/`、`tools/gov-qa/**`、`src/core/update/announce.py`、`plugin/client/api.ts` 等未提交件。
- **未**验证 B1 场景在 PowerShell 运行时是否报错（仅测本静态测试是否变红）。
- A2「含原串新名」的边界属**已知设计边界**，未作为打回依据（任务书已说明）。
