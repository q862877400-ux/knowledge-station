# Tasks: 接上更新通道系统的三个断点

**Input**: Design documents from `/specs/011-channel-system-wiring/`

**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: 本特性**包含测试任务** —— 宪法 III「证据优于断言」要求判据有牙。

**Organization**: 按业主要求的 **①②③ 顺序**（自动巡检 → 补 CCS → 下载前弹框）。

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- 所有路径相对仓库根 `D:/AI/work space/zcode/`

## 硬约束（每个任务都适用）

1. **不新增依赖** —— 能复用就复用（本特性全部是"接线"，不该有新包）。
2. **判据只有一个所有者** —— CCS 判据在 `ccs_fetcher`，下载校验在 `archive_pdf`，**不另写一份**。
3. **不碰 `NOT-DOING` 第 20 条** —— 下载**必须**经审批门，**绝不自动下载**。
4. **写前确认另一条线收工**（实测 2026-10-12 有另一条线在写 spec 009 UI）。
5. **一次只跑一个门禁**。

---

## Phase ①: 自动巡检（Priority: P1）

- [x] **T001** 新增 `src/core/update/scheduler_runner.py`：
  照 `law_refresh.py` 先例（单 daemon 线程 + 每线程自己的 `Event` + start 幂等 + stop 不谎报），
  循环体调 `UpdateScheduler.tick()`，**并补上"建批后执行"**
  （现状 `tick()` 只建批不跑 ⇒ 批会躺在 `pending`）。
  执行部分照 `routes_update.update_check` 的 `_run()` 口径（`inspector.run_batch`）。

- [x] **T002** 改 `src/core/api/server.py` 的 `run()`：
  启动 `start_update_scheduler()`（try/except 不阻塞引擎启动）+ 在 finally 里关停。

- [x] **T003** 新增 `tests/test_channel_system_wiring.py` 的第 ① 组判据（A1–A5）：
  - **A1** `server.run()` 的 **AST** 里有真的 Call（不是只 import）—— 照
    `test_law_catalog_refresh.py` 的既有 AST 判据先例
  - **A2** `start()` 幂等（连调两次只有一个线程）
  - **A3** 到期建批**且被执行**（批状态离开 `pending`）
  - **A4** 未到期不建批
  - **A5** `schedule_days=0` ⇒ 关闭

- [x] **T004** 第 ① 组变异自验：把 `start_update_scheduler()` 调用换成 `pass` ⇒ A1 红；
  去掉 tick 后的执行 ⇒ A3 红。

**Checkpoint**：引擎启动后能自动巡检。

---

## Phase ②: 通道入库补 CCS（Priority: P1）

- [x] **T005** 改 `src/core/ingestion/law_text.py`：
  `doc_type == 'standard'` 时查 CCS 写 `domain_tags`，判据**复用 `ccs_fetcher`**
  （与 `pipeline.py` L2216-2224 同一所有者，**不另写一份**）；
  失败**降级不阻塞**，照 `ccs_store.record_ccs_lookup` 留痕。

- [x] **T006** 回填入口：给已有 **380 篇** `web://` 文档补 CCS
  （复用 `ccs_backfill.py` 既有能力，不新写）。

- [x] **T007** 第 ② 组判据（B1–B4）：
  - **B1** 入库后 `domain_tags` 含 `CCS:`
  - **B2** CCS 查不到 ⇒ **入库仍成功**
  - **B3** `classify_document()` 不落「其他标准」兜底桶
  - **B4** 结构判据：不出现第二份 CCS 解析实现

- [x] **T008** 第 ② 组变异：删掉 CCS 调用 ⇒ B1 红；查不到就抛 ⇒ B2 红。

**Checkpoint**：通道入的库自动进目录。

---

## Phase ③: 下载附件前弹框（Priority: P1，碰安全面）

- [x] **T009** 新增下载审批门：
  - 服务端：判定 `new_version` 时**不下载**，只登记"可下载"（`update_change_event` 已有 `evidence_url`）
  - 宿主侧：走既有审批门（`tools/pre-execute` → `{kind:'ask'}`），问句**说清来源 + 形态 + 用途**
  - 同意 ⇒ 调 `archive_pdf()`（**复用**，含 `%PDF` 魔数 + 大小校验）；拒绝 ⇒ 不下载 + 留痕

- [x] **T010** 第 ③ 组判据（C1–C4）：
  - **C1** 判定 `new_version` 后 `archived_pdf_path` **仍为空**（没自动下载）
  - **C2** 审批门返回 `kind:'ask'` 且问句含来源 + 形态
  - **C3** 同意 ⇒ 调 `archive_pdf`；拒绝 ⇒ 不调
  - **C4** 非 PDF（HTML）⇒ 拒收

- [x] **T011** 第 ③ 组变异：把审批门改成直接下载 ⇒ C1+C2 红；去掉 `%PDF` 校验 ⇒ C4 红。

**Checkpoint**：下载能力接上，且合规（弹框）。

---

## Phase ④: 收口

- [x] **T012** 门禁 `pwsh -File scripts/run-gates.ps1 -Full` ⇒ **N/N · exit=0**。
- [x] **T013** 小提交 + 快照；把核实报告链接进归属层。

---

## Dependencies & Execution Order

- **Phase ①**：无依赖，先做（业主要求的顺序）。
- **Phase ②**：无依赖（不同文件），可紧随。
- **Phase ③**：依赖 ①（要有"发现新版本"这个动作才能谈下载）；碰安全面，最后做。

## Notes

- [P] 任务 = 不同文件、无依赖
- 每个 Phase 结束都可独立验证
- **不许跳过变异自验**（SC-009）
