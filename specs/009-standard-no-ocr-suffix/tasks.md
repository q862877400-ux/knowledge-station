# Tasks: 标准号「(OCR采集)」显示污染清理

**Input**: Design documents from `/specs/009-standard-no-ocr-suffix/`

**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: 本特性**包含测试任务** —— 宪法 III「证据优于断言」要求判据有牙。

**Organization**: 按 Phase 分组。Phase 1 是 MVP（判据 + 回归测试），其余一切的前提。

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- 所有路径相对仓库根 `D:/AI/work space/zcode/`

## 硬约束（每个任务都适用）

1. **写生产库必须先快照**（`create_snapshot("manual")`，手动快照永不被自动清理）。
2. **一次只跑一个门禁**（锁文件；退出码 3 = 有人在跑，不是失败）。
3. **不碰 `tools/gov-qa/**`**（另一条在途工作线）。
4. **判据只有一个所有者** —— 剥后缀的判据写在 `text_utils`，脚本与测试都调它，不各写一份。

---

## Phase 1: 判据与回归测试（MVP —— 其余一切的前提）

- [x] **T001** 在 `src/core/text_utils.py` 新增 `strip_ocr_source_suffix()`：
  只剥尾部 `(OCR采集)`，docstring 写明**为什么不复用 `strip_duplicate_suffix`**（那个剥 `(数字)`，判据不同）。
  ⚠ **实现时被自己的断言抓到一处**：只剥一次会漏双重后缀 `(OCR采集)(OCR采集)`
  —— 与 `strip_duplicate_suffix` 当年同一个坑。已改成**循环剥到稳定**。

- [x] **T002** [P] 源码级核实「`lawrefbook` 作 `source` 取值安全」：
  全仓搜 `doc_meta.source` 的读取点，**只有 `knowledge/law_source/update.py`** 一处
  （判据 `== "flk"`）；`channel_answers.py` / `ccs_store.py` 读的是**别的表**的同名列。
  UI 侧 `plugin/client/*.tsx` 的 `source` 全是 `zoom.source` / `tier_source`，与 `doc_meta` 无关。
  ⇒ **新取值不会进 FLK 巡检，也不会触发任何分支**。

- [x] **T003** 新增 `tests/test_standard_no_ocr_suffix.py`，四组断言（各自有牙）：
  - **A1** 带后缀必须剥（含全角括号 / 两侧空白 / 真库截断形态 / 双重后缀）
  - **A2** 合法括号名不动（`聚丙烯(PP)树脂` / 结尾就是 `)` 的 `额定电压1kV(Um=1.2kV)`）
  - **A3** 官方标准尾部中文不动（实测那 4 篇）
  - **A4**（**变异自验后补**，见 T009）以**中文括号**结尾的名字不动（真库 88 条形态）

- [x] **T004** 跑 T003：**23 passed**。

**Checkpoint**：判据与回归测试就绪。

---

## Phase 2: 回填脚本

- [x] **T005** 新增 `scripts/fix-standard-no-ocr-suffix.py`：
  默认 dry-run / `--apply` 先快照 / 单事务做三件事（改 `doc_meta` + 写 `source` + 同步 `clause_fts`）
  / 每行 `operation_log` / 写后复验 / 幂等 / **写前撞号检查**。

- [x] **T006** dry-run 跑一次，读数与 spec **逐项对上**：
  `doc_meta` 候选 = **1,430** · `clause_fts` 待同步 = **58,536** · 撞号 = **0** ·
  来源一致性 = **1,430/1,430 全是 LawRefBook**。

**Checkpoint**：脚本可跑，读数与 spec 一致。

---

## Phase 3: 执行与验证

- [x] **T007** `--apply` 执行。快照 `snap_01M4PXMTWRER3KTAVSY8ZNGA2M`
  （checksum `ccf275699bf02baa…`，手动快照永不被自动清理）。写后复验 **0 / 0**。

- [x] **T008** 写后复验，逐条对 SC：**12 项全过 / 0 失败**（见下"读数"）。

- [x] **T009** 变异自验（SC-008）：三种坏实现
  - `strip_any_tail_paren`（剥任意尾部括号）→ **10 failed**
  - `never`（不剥）→ **6 failed**
  - `strip_cjk_tail_paren`（剥尾部含中文的括号）→ **6 failed**
  ⚠ **第三种子第一次跑时"17 passed 存活"** —— 即原测试**没牙**。
  查真库确认它会真伤数据：`standard_no` 以「含中文的括号」结尾的 **88** 条里
  `(OCR采集)` 占 **0** 条，其余 88 条**全是合法名字**（`刑法修正案（七）`、
  `人民检察院刑事诉讼规则（试行）`、`个人信息保护法(测试)` …）。
  ⇒ **补 A4 断言**（把真库那 88 条的形态抄进测试）⇒ 再跑，**6 failed**（有牙了）。

- [x] **T010** 端到端：那篇出度最高的文档（开发史 §10.223 点名过）现在是
  `最高人民法院关于适用《民事诉讼法》的解释`，`source=lawrefbook`，**后缀已消失**。

**Checkpoint**：清理完成且可复算。

---

## Phase 4: 收口

- [x] **T011** `docs/PLAN-REAL-QUESTION-RULER.md` §九 **就地更正**（留痕，不删原话）。

- [x] **T012** 门禁 `pwsh -File scripts/run-gates.ps1 -Full` ⇒ **N/N · exit=0**。

- [x] **T013** 小提交 + 快照。

**Checkpoint**：本特性收口。

---

## 读数（T008，2026-10-12 实测）

| 判据 | 实测 | 期望 |
|---|---|---|
| SC-001 `doc_meta` 带后缀 | **0** | 0 |
| SC-002 `clause_fts` 带后缀 | **0** | 0 |
| SC-003 `source='lawrefbook'` | **1,430** | 1,430 |
| SC-004 `source='flk'` / `'govcn'` | **0 / 0**（写前也是 0） | 与写前相等 |
| SC-005 总行数 / 条款数 | **8,983 / 663,634** | 不变 |
| SC-006 幂等（第二次运行） | **0 行** | 0 |
| SC-008 变异自验 | **三种坏实现各自变红** | 必须红 |
| `operation_log` 条数 | **1,430** | 1,430 |
| lawrefbook 且 `source_url` 指向 LawRefBook | **1,430** | 1,430 |

### ⚠ 一条**判据本身写错**的记录（如实留痕）

我最初的 US3 判据写的是「全库 `clause_fts.standard_no` == `doc_meta.standard_no`」，
跑出 **462,286 不一致**。**我没有当成"我改坏了"，而是先查** ——
结论：**那是既存形态，与本特性无关**。三条证据：

1. 我改过的那 1,430 篇：fts 不一致 **0** 篇；
2. 那 462,286 行**全部**来自**非** lawrefbook 的文档；
3. **写前快照里也是 462,286**（逐数相等）⇒ 我只可能让它变好，不可能变坏。

根因：`clause_fts.standard_no` 对**别的**文档存的是**截断前缀**
（如 `GBZ／T`，而 `doc_meta` 是 `GBZ/T 160.27-2004`）—— 抽样 3,000 条**全是**这个形态。

⇒ 判据已改成"**本特性范围内**必须一致"（那 1,430 篇），并加一条"差异行里 fts 仍带
`(OCR采集)` 的必须为 0"。**原判据是错的，不是数据是错的。**

---

## Dependencies & Execution Order

- **Phase 1**：无依赖，立即开始。**阻塞**后续全部（判据没牙则后面全白做）。
- **Phase 2**：依赖 T001（脚本要调判据函数）。
- **Phase 3**：依赖 Phase 2（脚本就绪）。T007 **不可回退地写生产库** ⇒ 必须 T006 对账通过。
- **Phase 4**：依赖 Phase 3。

### Within Each Phase

- 判据 → 测试 → 脚本 → dry-run → apply → 复验 → 变异 → 门禁 → 提交

## Notes

- [P] 任务 = 不同文件、无依赖
- 每个 Phase 结束都可独立验证
- **不许跳过 T006 的 dry-run 直接 apply**
