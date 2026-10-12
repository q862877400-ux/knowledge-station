# Feature Specification: 标准号「(OCR采集)」显示污染清理

**Feature Branch**: `009-standard-no-ocr-suffix`

**Created**: 2026-10-12

**Status**: Draft

**Input**: 业主 2026-10-11 后的自主任期授权（「你直接开始施工，设定好目标，按照 spec 的规范自动施工，完全做完前不要停下」）＋ 既有登记项 `docs/PLAN-REAL-QUESTION-RULER.md` §九

---

## 背景：为什么需要这个特性

### 现象（用户可见）

用户在证据卡片上看到的**标准号**长这样：

```
野生动物保护法(OCR采集)
人体损伤程度鉴定标准(OCR采集)
刑法修正案（七）(OCR采集)
```

`(OCR采集)` 是**入库时的来源标记**，不是标准号的一部分。

### 实测（2026-10-12，生产库只读）

| 项 | 实测 |
|---|---|
| `doc_meta.standard_no` 含 `(OCR采集)` | **1,430** 篇 / 8,983 篇（**15.9%**） |
| 后缀形态 | `(OCR采集)` **1,429** 处 + 被文本截断的 **1** 处 |
| 出现位置 | **只在 `standard_no`**；`standard_name` / `short_code` **均为 0** |
| 会不会影响检索 | **不会** —— `canon_standard_no` 是词边界包含匹配，实测命中正常 |
| 会不会显示给用户 | **会** —— `plugin/client/KsTurnTab.tsx` 直接渲染 `{str(ev.standard_no)}` |

### 这批文档的来路（已查明）

| 项 | 实测 |
|---|---|
| `file_path` 前缀 | `lawrefbook://` —— **1,430 篇全部** |
| `source_url` | `https://github.com/RanKKI/LawRefBook` —— **1,430 篇全部有** |
| 入库时间 | `created_at` 全部是 **2026-10-07** |
| 对照：其余法律法规文档 | 380 篇，`file_path` 是 `web://www.mem.gov.cn`（官方站） |

⇒ 这 1,430 篇来自 **LawRefBook**（GitHub 上一个第三方 iOS 法规 App 的语料），
**不是**从官方站（flk / gov.cn）抓的。

### ⚠ 本特性的真正难点：后缀是**唯一的"非官方"标记**

实测这 1,430 篇的其余字段**全部按"官方现行"登记**：

| 字段 | 值 | 问题 |
|---|---|---|
| `quality_grade` | **`A`**（1,430/1,430） | `A` 的契约是"清晰度/OCR 识别率 ≥0.95"（`quality/grading.py`），而第三方 OCR **没有这个证据** |
| `legal_status` | **`effective`**（1,430/1,430） | 直接当"现行有效"用 |
| `standard_type` | **`mandatory`**（1,430/1,430） | 直接当"强制性"用 |
| `source` | **`NULL`**（1,430/1,430） | 来源字段空着 |

⇒ **如果只把 `standard_no` 的后缀抹掉，就等于把这 1,430 篇的来路信息彻底删干净**
—— 用户再也看不出它们不是官方来源，而系统会把它们当"现行强制性"用。

⇒ **所以本特性不是"删后缀"，是"把来源标记从标准号搬到它该在的字段"。**

---

## 目标

**把「非官方来源」这件事，从标准号里搬到数据模型的来源字段上，且搬完以后信息量不减少。**

三件必须同时成立：

1. **用户看到的标准号干净**（`刑法` 而不是 `刑法(OCR采集)`）；
2. **来路信息还在**，且落在**按设计该放它的字段**里（`doc_meta.source`，其契约见 `schema.sql`：`官方来源: flk | govcn`）；
3. **检索不受影响**（`clause_fts.standard_no` 是**另一份副本**，必须同步，否则两条通道看到的标准号不一致）。

---

## User Scenarios & Testing

### User Story 1 - 证据卡片上的标准号干净（Priority: P1）

用户提问 → 系统给出证据卡片 → 卡片上的标准号**不再带 `(OCR采集)`**。

**Why this priority**：这是业主肉眼能看见的缺陷，也是本特性的直接触发点。

**Independent Test**：对任一来自 LawRefBook 的文档做一次检索，断言返回证据的 `standard_no` 不含 `(OCR采集)`。

**Acceptance Scenarios**：

1. **Given** 库里有一篇 `standard_no = '刑法(OCR采集)'`，**When** 用户问「刑法的适用范围」，**Then** 证据卡片显示 `刑法`，**不显示** `刑法(OCR采集)`。
2. **Given** 清理已完成，**When** 再跑一次清理脚本，**Then** 报 **0 行**（幂等）。

---

### User Story 2 - 来路信息不丢，且落在该在的字段（Priority: P1）

清理后，这 1,430 篇仍能被识别为"来自 LawRefBook 的第三方语料"。

**Why this priority**：与 US1 **同等重要**。只做 US1 = 删掉唯一的来路标记，把一个"显示缺陷"升级成一个"合规缺陷"（用户看不出这不是官方来源）。

**Independent Test**：清理后按 `source='lawrefbook'` 能精确数出 1,430 篇，且每一篇的 `source_url` 仍指向 LawRefBook。

**Acceptance Scenarios**：

1. **Given** 清理完成，**When** 查 `source='lawrefbook'`，**Then** 恰好 **1,430** 行。
2. **Given** 清理完成，**When** 查 `source='flk'`，**Then** 行数**与清理前一致**（没被误改）。
3. **Given** 清理完成，**When** 跑法规时效巡检 `check_law_updates()`，**Then** 这 1,430 篇**不进入** FLK 巡检（它们没有 FLK 的 `source_id`）。

---

### User Story 3 - 检索两条通道看到的标准号一致（Priority: P2）

`clause_fts.standard_no` 与 `doc_meta.standard_no` 不再分叉。

**Why this priority**：`clause_fts` 是 FTS5 表，**自己存了一份** `standard_no`（实测 58,536 行带后缀）。只改 `doc_meta` 会让两条通道给出不同的标准号。

**Independent Test**：清理后，`clause_fts` 里带 `(OCR采集)` 的行数为 **0**，且逐条与 `doc_meta` 同 `doc_id` 的行一致。

**Acceptance Scenarios**：

1. **Given** 清理完成，**When** 查 `clause_fts WHERE standard_no LIKE '%(OCR采集)%'`，**Then** **0** 行。
2. **Given** 清理完成，**When** 抽查任一来自 LawRefBook 的文档，**Then** 它的 `clause_fts.standard_no` == 它的 `doc_meta.standard_no`。

---

### Edge Cases

- **`short_code` 怎么办**：实测带后缀 **0** 行 ⇒ 不用动。（它是从 `standard_no` **派生**的，但派生发生在入库时；本次是回填，不重跑派生。）
- **`standard_name` 怎么办**：实测带后缀 **0** 行 ⇒ 不用动。
- **会不会撞号**：实测**不会** —— 去后缀后重复标准号 **0** 个（现状也是 0 个）。
- **那 1 处形态不同的**：`…(八)》时间效力问题的解释(OCR采集)` 是**标准号被文本截断**导致，去掉后缀后仍是它自己的名字，不撞任何号。
- **幂等**：第二次运行必须报 0 行。
- **可回滚**：写前必须做快照（手动快照永不被自动清理）。

---

## Requirements

### Functional Requirements

- **FR-001**：`doc_meta.standard_no` 尾部**只**剥离 `(OCR采集)` 这一种后缀，**不得**动其他括号内容（实测库内存在**合法**括号名，如 `聚丙烯(PP)树脂`）。
- **FR-002**：剥离**必须**在同一个事务里，为每行写一条 `operation_log`（operation = `fix_standard_no_ocr_suffix`，detail 记 `旧值 → 新值`）。
- **FR-003**：同一事务里**必须**把 `doc_meta.source` 从 `NULL` 改为 `lawrefbook` —— **这是本特性的核心**，不是可选项（否则 = 删除来路信息）。
- **FR-004**：同一事务里**必须**同步 `clause_fts.standard_no`（按 `doc_id` 关联到 `clause_revision.clause_revision_id`）。
- **FR-005**：脚本**默认 dry-run**，`--apply` 才写；`--apply` 前**必须**做快照。
- **FR-006**：脚本**必须幂等** —— 第二次运行报 0 行。
- **FR-007**：脚本**必须**在写后复验（同一判据再跑一次，应为 0），并把读数写进报告。
- **FR-008**：`doc_meta.quality_grade` 与 `legal_status` **本次不动** —— 改它们会改变检索的"现行/参考"判定，超出本特性范围；但**必须**在归属文档里写明"这 1,430 篇的 `A` / `effective` 是**未经核验的默认值**"。
- **FR-009**：必须有一条**回归判据**：任何 `standard_no` 都不许以 `(OCR采集)` 结尾（防止将来重新入库时再带进来）。
- **FR-010**：`src/core/retrieval/hybrid_engine.py` 的 `_std_key_hits_doc` 注释里「真库有 **4 篇** `standard_no` 尾部带中文」**不动** —— 实测那是**另一个判据**（标准号+年份后紧跟中文，实测 4 篇，与这 1,430 篇**交集为 0**）。

### Key Entities

- **`doc_meta`**：文档元数据。本特性改 `standard_no`（去后缀）与 `source`（记来源）。
- **`clause_fts`**：FTS5 虚拟表，**自存一份** `standard_no`。本特性要同步它。
- **`operation_log`**：可追责记录。本特性每行写一条。

---

## Success Criteria

### Measurable Outcomes

- **SC-001**：清理后 `doc_meta` 里 `standard_no LIKE '%(OCR采集)%'` 的行数 = **0**。
- **SC-002**：清理后 `clause_fts` 里 `standard_no LIKE '%(OCR采集)%'` 的行数 = **0**。
- **SC-003**：清理后 `source='lawrefbook'` 的行数 = **1,430**（信息量不减少）。
- **SC-004**：清理后 `source='flk'` 与 `source='govcn'` 的行数与清理前**逐项相等**。
- **SC-005**：清理前后**总行数不变**（8,983），**条款数不变**（663,634）。
- **SC-006**：第二次运行报 **0 行**（幂等）。
- **SC-007**：`scripts/run-gates.ps1 -Full` **N/N · exit=0**。
- **SC-008**：回归判据在"故意塞回一条带后缀的记录"时**必须变红**（变异自验）。

---

## Assumptions

- **假设 1**：`lawrefbook` 作为 `source` 取值**安全** —— 实测 `source` 只在 `knowledge/law_source/update.py` 里被读一次，判据是 `== "flk"`，新取值不会进入 FLK 巡检。**本假设已被源码核实**（见 tasks T002）。
- **假设 2**：这 1,430 篇的内容**不重新核验**（本特性只搬来源标记，不判内容对错）。
- **假设 3**：业主 2026-10-07 裁定「放弃人工审核，改用外部 AI 复核」（`NOT-DOING` 第 23 条）⇒ 本特性**不引入**人工核对步骤。

## 明确不做（Anti-Scope）

- **不改 `quality_grade` / `legal_status` / `standard_type`** —— 会改变检索判定，且"这 1,430 篇到底算不算 A 级"需要内容核验，超出本特性。
- **不重新入库 / 不重跑派生** —— 只做回填。
- **不删任何文档** —— 只改字段值。
- **不动那 4 篇**（`GB 5009.12-2023食品安全国家标准` 等）—— 它们是另一个判据，且是**官方标准**，`standard_no` 尾部带中文的原因不同。
