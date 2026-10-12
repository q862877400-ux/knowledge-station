# Feature Specification: 接上「法规/标准更新通道系统」的三个断点

**Feature Branch**: `011-channel-system-wiring`

**Created**: 2026-10-12

**Status**: Draft

**Input**: 业主 2026-10-12「按照123顺序，设定好目标，按照spec自动开工，我授予你一切权限，一次性把工作干完」＋ 核实报告 `docs/research/CHANNEL-SYSTEM-AUDIT-2026-10-12.md`

---

## 背景：能力做完了，但没接上

业主问：「我不是做了一套自动嗅探各个网站的法规和标准的更新动态，然后根据更新动态去下载
附件区或者去标准网下载最新版本的国标或者法规的通道吗」

**核实结论（2026-10-12，纯读代码 + 读库）：做了，而且比业主记的完整。但有三个断点。**

### 已建成的部分（不是设想，有代码有测试）

| 能力 | 证据 |
|---|---|
| **20 个通道适配器** | `src/core/update/channels/*.py`：`official_gb`（国标全文公开系统）、`std_samr_hb`、`ndls`、`cssn`、`dbba`、`mohurd`、`govcn_announce`、`laws_db`、`mee`、`mem_gov`… |
| **降级链** | `inspector.py`：`official_gb → govcn`，单号探测预算 3 次 |
| **下载附件** | `govcn_announce.archive_pdf()`：**curl_cffi chrome 指纹 + `%PDF` 魔数校验 + 大小 >1024 校验**；测试 `tests/test_govcn_archive.py` |
| **正文入库** | `web_ingest.py`：抓详情页 → 抽正文 → 判效力档 → `law_text.ingest_law_text()` → 进 **`doc_meta`（标准库）** |
| **端点齐备** | `/update/check`、`/update/announce-scan`、`/update/announce-ingest`、`/laws/search`、`/laws/ingest` |

---

## 三个断点（本特性要修的）

### 断点一：那套系统**没有任何东西在自动跑**

`server.py` 的 `run()`（唯一生产启动点）只启动两个后台线程：
`start_write_worker()` 与 `start_law_refresh()`（**法规目录**刷新）。

`src/core/update/scheduler.py` 的 `start()` **全仓无人调用** —— `server.py` L3298 的注释自己写着：

> ⚠ 不走 `update/scheduler.py` —— 那个调度器的 `start()` 全仓无人调用（**死代码**）

**且**：`UpdateScheduler.tick()` **只负责建批**（`inspector.create_inspect_batch`），
**不负责执行** —— 执行在 `routes_update.update_check` 的 `_run()` 里（`inspector.run_batch`）。

⇒ 现状：**巡检只能人工点按钮**。业主记的"自动嗅探"实际是"手动一键"。

### 断点二：通道入库的文档**没有 CCS 标签 ⇒ 不会自动进目录**

实测（生产库只读，按来源）：

| 来源 | 总数 | 有 `CCS:` 标签 | 占比 |
|---|---|---|---|
| 本地文件（`D:\...\标准\`） | 7,173 | 6,838 | **95.3%** |
| `lawrefbook://` | 1,430 | 0 | 0.0% |
| **`web://`（通道/网页入的）** | **380** | **0** | **0.0%** |

**根因（已定位）**：填 CCS 的代码在 `pipeline.py` L2216-2224：

```python
if doc_type == "standard":
    ccs_lookup = resolve_ccs(standard_no, standard_name)
    ccs_tag = ccs_to_tag(ccs_lookup, standard_no)
    if ccs_tag and ccs_tag not in tags: tags.append(ccs_tag)
```

而 `web_ingest` 走的是 **`law_text.ingest_law_text()`** ——
`git grep resolve_ccs -- src/core/ingestion/law_text.py` **空命中**。

目录树是**读时按 `CCS:xxx` 分类**（`/api/v1/documents/categories` → `classify_document`）
⇒ 没有 CCS 的落「其他标准」兜底桶，**不进任何目录**。

### 断点三：`archive_pdf` **从来没被生产调用过**

实测：
- `update_change_event.archived_pdf_path` 非空 = **0 / 6,471**
- `%APPDATA%\KnowledgeStation\announcements\` = **空目录**
- `archive_pdf` 的调用点**只有测试**（`tests/test_govcn_archive.py`）

巡检发现"有新版本"后只写一条 `update_change_event`（实测 `new_version` 3 条），**不下载**。

⚠ **这条碰红线**：`docs/NOT-DOING.md` 第 20 条写死
「**不许**演化成"自动下载"或"默认同意"」⇒ **必须改成"下载前弹框问人"**。

---

## 目标

**把做好的能力接上生产链路，不新建能力。三条按 ①②③ 顺序做。**

| # | 要做的 | 判据 |
|---|---|---|
| **①** | 自动巡检接进 `server.run()`，且**建批后真的执行** | 引擎启动后，到期能自动建批 + 自动跑 |
| **②** | `law_text.ingest_law_text()` 补 CCS（复用 `ccs_fetcher`） | 通道入的库带 `CCS:` 标签 ⇒ 自动出现在目录树 |
| **③** | 「有新版本」时**弹框问人**再下载附件（复用 `archive_pdf`） | 弹框 → 同意才下载；拒绝不下载；**绝不自动下载** |

---

## User Scenarios & Testing

### User Story 1 - 自动巡检（Priority: P1）

引擎跑着的时候，到日子了**自己**去查标准有没有新版。

**Why this priority**：这是业主记的"自动嗅探"的核心。没有它，通道系统等于一个手动的查询工具。

**Independent Test**：注入假时钟，验证到期建批 + 批被执行（不只是建了躺那儿）。

**Acceptance Scenarios**：

1. **Given** 距上次 scheduled 巡检 ≥ `update.schedule_days` 天，**When** 调度拍一次，**Then** 建出批次**且被执行**（状态离开 `pending`）。
2. **Given** 距上次不足 N 天，**When** 调度拍一次，**Then** **不建批**（幂等，不重复建）。
3. **Given** `update.schedule_days` 设为 0，**When** 调度拍一次，**Then** 关闭调度、不建批。
4. **Given** 引擎启动，**When** 读 `server.run()` 的 AST，**Then** 有**真的调用** `start_update_scheduler()`（不是只 import）。

---

### User Story 2 - 通道入库的文档能进目录（Priority: P1）

从网上通道入的标准，跟本地文件一样**自动出现在目录树里**。

**Why this priority**：不修它，通道入库的东西就是"库里有、界面上找不到"——等于白入。

**Independent Test**：造一个 `web://` 来源的标准，入库后查它的 `domain_tags` 有 `CCS:`，
且 `classify_document()` 不给它「其他标准」兜底桶。

**Acceptance Scenarios**：

1. **Given** 一个能查到 CCS 的标准号，**When** 走 `ingest_law_text()` 入库，**Then** `domain_tags` 含 `CCS:xxx`。
2. **Given** 查不到 CCS 的标准号，**When** 入库，**Then** **不报错、不阻塞**（降级照旧），且留痕。
3. **Given** 入库完成，**When** 调 `classify_document()`，**Then** 落进标准树的真实分类（不是「其他标准」）。
4. **Given** 已有的 380 篇 `web://` 文档，**When** 跑回填，**Then** 能补上 CCS 的补上。

---

### User Story 3 - 下载附件前问人（Priority: P1）

巡检发现"有新版本"，**弹框问你要不要下载**，同意才下。

**Why this priority**：`archive_pdf` 已做好但没接线；接线的**唯一合规方式**是弹框（NOT-DOING 第 20 条）。

**Independent Test**：判定 `new_version` 时，**不自动下载**；走审批门，同意后才调 `archive_pdf`。

**Acceptance Scenarios**：

1. **Given** 巡检判定 `new_version`，**When** 该批跑完，**Then** **没有**文件被下载（`archived_pdf_path` 仍为空）。
2. **Given** 用户点"同意下载"，**When** 审批通过，**Then** 调 `archive_pdf()`，且**校验 `%PDF` 魔数**。
3. **Given** 用户拒绝，**When** 拒绝，**Then** 不下载，且如实记"用户拒绝"（不静默）。
4. **Given** 下载到的不是 PDF（站点返回 HTML 错误页），**When** 校验，**Then** **拒收**并如实报错。

---

### Edge Cases

- **调度器重复启动**：`start()` 必须幂等（已在跑就不动）。
- **批执行失败**：后台线程吞异常存活，不拖垮引擎。
- **CCS 查询超时/失败**：**降级不阻塞入库**（照 `pipeline.py` 既有口径），但要留痕。
- **CCS 查询被墙**：`ccs_fetcher` 三级链（官方接口 → 网页 → 本地兜底），全失败返回 None。
- **`domain_tags` 是坏值**：`ccs_store` 已有"写路径拒改"保护（防冲掉别的标签）。
- **验证码暂停的批**：调度器**绝不自动 resume**（既有纪律 INS-C-03），本特性不动它。
- **弹框超时/没人答**：视为"不下载"（不猜用户意图）。

---

## Requirements

### Functional Requirements

- **FR-001**：`server.run()` **必须**启动更新调度线程（照 `law_refresh` 既有先例），且**必须**在 AST 判据里可验（不是只 import）。
- **FR-002**：调度器**必须**在到期时**建批 + 执行**（现状只建不跑）。执行部分照 `routes_update` 的 `_run()` 口径。
- **FR-003**：调度器**必须**幂等 —— 重复 `start()` 不起第二个线程（照 `law_refresh.stop()` 的"不谎报已停"纪律）。
- **FR-004**：`law_text.ingest_law_text()` **必须**在 `doc_type == 'standard'` 时查 CCS 并写入 `domain_tags`，判据与 `pipeline.py` **同一所有者**（`ccs_fetcher`），不另写一份。
- **FR-005**：CCS 查询失败**必须**降级不阻塞入库，且**必须**留痕（照 `ccs_store.record_ccs_lookup`）。
- **FR-006**：**必须**提供回填入口，给已有的 380 篇 `web://` 文档补 CCS。
- **FR-007**：下载附件**必须**先经审批门（`kind:'ask'`），**绝不自动下载**（NOT-DOING 第 20 条）。
- **FR-008**：下载**必须**复用 `govcn_announce.archive_pdf()` 的 `%PDF` 魔数 + 大小校验，**不另写一份**。
- **FR-009**：下载结果**必须**如实回报（成功/拒绝/失败各自留痕），**不静默**。
- **FR-010**：审批门的问句**必须**说清"来源 + 形态 + 用途"（业主口径：不让用户读全文）。

### Key Entities

- **`bulk_import_batch`**：批次控制面（`batch_kind='inspect'`）。调度器建批、执行器跑批。
- **`update_change_event`**：变更事件（`change_type` / `archived_pdf_path`）。本特性要填 `archived_pdf_path`。
- **`doc_meta.domain_tags`**：CCS 标签的落点。目录树按它分类。
- **`doc_ccs_state`**：CCS 查询审计表（现 806 行：found 801 / not_found 2 / parse_failed 3）。

---

## Success Criteria

### Measurable Outcomes

- **SC-001**：引擎启动后，调度线程**在跑**（可观测，非"我以为"）。
- **SC-002**：到期时**自动建批且批被执行**（状态离开 `pending`）。
- **SC-003**：重复 `start()` 不产生第二个线程（计数断言）。
- **SC-004**：通道入库的标准**带 `CCS:` 标签** ⇒ `classify_document()` **不落**「其他标准」兜底桶。
- **SC-005**：CCS 查不到时**入库仍成功**（降级不阻塞），且 `doc_ccs_state` 有留痕。
- **SC-006**：判定 `new_version` 时**没有文件被下载**（`archived_pdf_path` 保持空）。
- **SC-007**：用户同意后下载成功，且**非 PDF 被拒收**。
- **SC-008**：`scripts/run-gates.ps1 -Full` **N/N · exit=0**。
- **SC-009**：每条判据**有牙** —— 变异自验（把实现改坏，判据必须变红）。

---

## Assumptions

- **假设 1**：`scheduler.py` 的编排逻辑（建批/恢复）**本身是对的**，只是没被启动 ⇒ 本特性**只接线，不改它的编排语义**。
- **假设 2**：`ccs_fetcher` 可用（三级链）。若外部站不可达，走本地兜底。
- **假设 3**：`archive_pdf` 的实现**是对的**（有测试）⇒ **复用，不重写**。
- **假设 4**：业主已授予全部权限（2026-10-12「我授予你一切权限，一次性把工作干完」），
  但 `NOT-DOING` 的红线**不因授权而放宽** —— 故第 ③ 条**必须**是弹框版。

## 明确不做（Anti-Scope）

- **不做"自动下载"** —— NOT-DOING 第 20 条禁止。必须弹框。
- **不修 `scheduler.py` 的编排逻辑** —— 它是对的，只是没被启动。
- **不重写 `archive_pdf`** —— 已有实现 + 测试，复用。
- **不重写 `ccs_fetcher`** —— 三级链已有。
- **不动验证码暂停的批** —— 既有纪律（绝不自动 resume）。
- **不改 `ks_collect`**（宿主侧那个采集工具）—— 它是另一条线（材料平面），本特性不碰。
