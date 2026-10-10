# Tasks: 法规目录补齐与定时刷新 + 历次版本链

**Feature**: `006-law-catalog-refresh` ｜ **Spec**: [spec.md](./spec.md) ｜ **Plan**: [plan.md](./plan.md)

**Created**: 2026-10-10

---

## 阶段 0：基线取证

- [x] **T001** 记录刷新前基线到 `specs/006-law-catalog-refresh/baseline.json`
  —— 字段：`law_catalog_rows`、`sxx_drift_count`、`rows_2026_08`、`max_gbrq`、
  `max_updated_at`、`remote_total`、`measured_at`。
  - **判据**：文件存在且 `law_catalog_rows == 29764`（与实测一致才继续；
    若已不同，说明有人先跑了刷新，就地更新 spec 的现状数字）。
  - 依赖：无。

- [x] **T002** 抽样核对 `sxx` 字段语义（**SC-001a 的前提，未过则 SC-001a 作废**）
  —— 用 KS 自己的 `flk_client.detail()` 抽 ≥10 条漂移条目（含"标有效实为已废止"类），
  逐条比对详情接口返回的 `sxx`。
  - **判据**：抽样一致率 100% 才继续；任一不一致 ⇒ 停止并就地更正 spec。
  - **留痕**：抽样命令 + 输出写进 `research.md`。**这是抽样，不是全部。**
  - 依赖：无。

## 阶段 1：刷新可自动触发（US1 / P1 MVP）

- [x] **T010** `catalog.py` 新增配置键常量与读取函数
  —— `LAW_REFRESH_DAYS_KEY = "law.catalog_refresh_days"`、`LAW_LAST_REFRESH_KEY =
  "law.catalog_last_refresh_at"`、`DEFAULT_REFRESH_DAYS = 1`、`refresh_days() -> int`
  （缺省 1；非法/≤0 返回 0 表示关闭，与 `scheduler.schedule_days` 同构）。
  - **判据**：非法值返回 0；未设返回 1。
  - 依赖：T001。

- [x] **T011** `catalog.py` 新增 `refresh_catalog_if_due(*, now=None) -> dict`
  —— 读周期 + 上次时间；未到期返回 `{"skipped": True, "reason": "not_due", ...}`；
  到期则调 `refresh_catalog()` 并在成功后写 `LAW_LAST_REFRESH_KEY`。
  - **判据**：到期触发 / 未到期跳过 / 周期 ≤0 关闭，三条都要有测试。
  - **约束**：失败时 **MUST NOT** 更新 `last_refresh_at`（否则失败会被当成"刷过了"）。
  - 依赖：T010。

- [x] **T012** **新建** `src/core/knowledge/law_source/law_refresh.py`
  —— 后台 daemon 线程（`start_law_refresh()` / `stop_law_refresh()`），
  轮询 `refresh_catalog_if_due()`。
  - **判据**：`start` 幂等（重复调不重复起线程）；`stop` 能干净关停。
  - **约束**：轮询周期与"刷新周期"是两个概念——前者是线程唤醒间隔（秒级），
    后者是 `law.catalog_refresh_days`（天级）。
  - **⚠ 就地更正**：原任务写"改 `scheduler.py` 的 `tick()`"，实测该调度器
    **生产中从未被启动**（`start()` 无人调用）⇒ 接进去刷新永不执行。改为自建线程。
  - 依赖：T011。

- [x] **T012a** `src/core/api/server.py` 的 `run()` 里启动该线程
  —— 照抄 `write_queue_bootstrap.start_write_worker()` 先例
  （`try/except` 包住，失败不阻塞引擎启动）；`finally` 里 `stop`。
  - **判据**：`run()` 里有 start 与 stop 两处调用；异常不冒泡到启动路径。
  - 依赖：T012。

- [x] **T013** 单元测试 `tests/test_law_catalog_refresh.py`
  —— mock 网络；覆盖：到期触发、未到期跳过、关闭、失败不写 `last_refresh_at`、
  线程 start 幂等 / stop 干净、**启动点确实调了 start**（可 patch 后断言）。
  - **判据**：全部通过；且**变异测试有牙**（把"未到期跳过"改成恒触发 ⇒ 必有测试红；
    把 `run()` 里的 start 删掉 ⇒ 必有测试红）。
  - 依赖：T012a。

## 阶段 2：跑一次真实全量刷新（US1 收口）

- [x] **T020** 对真库跑 `refresh_catalog()`，量 SC-001 / SC-001a
  —— 跑前确认备份存在（`%APPDATA%\KnowledgeStation\backups\`）。
  - **判据**：`law_catalog_rows >= 30900`、`rows_2026_08 >= 600`、`sxx_drift_count == 0`
    （口径：两库都有且官方 `sxx` 非空的 `bbbs`）。
  - **诚实边界**：耗时约 12 分钟且依赖外网。**若官方不可达 ⇒ 标"明确未做"，
    读数留空，MUST NOT 伪造。**
  - **✅ 实测（2026-10-10）**：行数 29,764 → **30,953**（≥30,900 ✅）；
    2026-08 26 → **702**（≥600 ✅）；漂移 1,130 → **1**（⚠ 未达 0）；
    缺失 1,187 → **1**。实际写入 2,338 行。
  - **⚠ SC-002 活体未做**：连续猛打后站点长封禁，二次刷新的活体读数拿不到；
    幂等由单测覆盖（**明确标注：单测证据，非活体证据**）。
  - 残余 1 条缺失 / 1 条漂移已逐条定性（research.md R1b），**不追**。
  - 依赖：T013。

- [x] **T021** 把 T020 的前后读数写进 `research.md` 与 `docs/DEVELOPMENT-HISTORY.md`
  - **判据**：数字与实测一致，标注测量时间。
  - 依赖：T020。

## 阶段 3：历次版本链（US2 / P2）

- [x] **T030** `flk_client.py` 新增 `history(bbbs) -> list[dict]`
  —— 调详情接口，解析 `lsyg` → `[{"bbbs","title","gbrq","highLight"}]`，按 `gbrq` 降序。
  - **判据**：无 `lsyg` ⇒ 返回 `[]`；网络失败 ⇒ **抛异常**（MUST NOT 返回 `[]` 冒充）。
  - 依赖：T013。

- [x] **T031** HTTP 端点 `GET /api/v1/laws/history?bbbs=`
  —— 缺 `bbbs` ⇒ 422；官方不可达 ⇒ 502；正常 ⇒ 200 + 版本列表。
  - **判据**：三条分支都有测试；端点是 `def` 不是 `async def`（见 `routes_law.py` 头 §10.93）。
  - 依赖：T030。

- [x] **T032** 单元测试补进 `tests/test_law_source.py`（或新文件）
  —— 多版本降序 / 无 `lsyg` 返空 / 网络失败返 502 / 缺参返 422。
  - **判据**：全过；变异（把失败也返回 `[]`）⇒ 测试红。
  - 依赖：T031。

## 阶段 4：知识并入（US3 / P3）

- [x] **T040** `docs/LAW-SOURCE-PLAN.md` 增补四条接口事实 + 出处
  —— `highSearch` 端点、offset 30,000 墙、`codeId≠id`、`xgzl` 文号。
  - **判据**：`grep -n "highSearch\|30000\|codeId\|xgzl" docs/LAW-SOURCE-PLAN.md` 均有命中。
  - **来源标注**：写明来自 `D:/AI/std-law-watch`（独立项目，非本仓实测），
    **MUST NOT 冒充为本仓实测结论**。
  - 依赖：无（可与阶段 3 并行）。

- [x] **T041** 记录 `download/pc` 全文下载的**结论冲突**
  —— KS 记"主路径"（`flk_client.py` + `ENCYCLOPEDIA.md`）vs std-law-watch 记"判死"；
  并列 + 标"未实测仲裁"。
  - **判据**：两处（`ENCYCLOPEDIA.md`、`LAW-SOURCE-PLAN.md`）都能看到冲突，
    且**不得**单方面改成判死或改成可用。
  - 依赖：T040。

- [x] **T042** 记录 std-law-watch 目录处置口径
  —— 保留只读、只并知识不并代码、不并入 64 站注册表（会破坏 5 域白名单）。
  - **判据**：口径写进归属文档；`NOT-DOING.md` 登记一行"不并入其代码/注册表"。
  - 依赖：T040。

## 阶段 5：门禁与收工

- [x] **T050** `pwsh -File scripts/run-gates.ps1 -Quick` → **exit 0**
  - **判据**：退出码 0；测试基线只涨不跌（`-UpdateBaseline` 仅在全绿后）。
  - 依赖：T013、T032、T042。

- [x] **T051** 小提交 + 快照
  —— 提交消息写清"改了什么 / 为什么 / 边界"；
  `& .\scripts\snapshot-project.ps1 -Label law-catalog-refresh`。
  - 依赖：T050。

- [x] **T052** spec 收口：更新 `spec.md` 的 Status 与 SC 实测读数
  - **判据**：每条 SC 后面有实测值或"明确未做"。
  - 依赖：T051。

---

## 依赖图

```
T001 ─┬─ T010 ─ T011 ─ T012 ─ T012a ─ T013 ─┬─ T020 ─ T021 ──┐
T002 ─┘                                     │                │
                                            ├─ T030 ─ T031 ─ T032 ─┤
T040 ─ T041 ─ T042 ─────────────────────────┼──────────────────────┤
                                                              ↓
                                                        T050 ─ T051 ─ T052
```

## 并行机会

- **T040–T042（文档）与 T010–T013（代码）可并行**：写集不重叠
  （`docs/*.md` vs `src/core/**`）。
- **T001/T002（取证）必须先于 T020**，否则 SC 无基线可比。

## 写集（避免并发写冲突）

| 任务 | 写集 |
|---|---|
| T010–T011 | `src/core/knowledge/law_source/catalog.py` |
| T012 | `src/core/knowledge/law_source/law_refresh.py`（新） |
| T012a | `src/core/api/server.py` |
| T013 | `tests/test_law_catalog_refresh.py`（新） |
| T030 | `src/core/knowledge/law_source/flk_client.py` |
| T031 | `src/core/api/routes_law.py` |
| T032 | `tests/test_law_source.py` |
| T040–T042 | `docs/LAW-SOURCE-PLAN.md`、`docs/ENCYCLOPEDIA.md`、`docs/NOT-DOING.md` |

⚠ `catalog.py` 被 T010/T011 共用 ⇒ **同一写者顺序做**，不并行。
⚠ `server.py` 是**共享热点文件**（另一 Agent 的 gov-qa 也在改本仓）⇒
T012a 只加最小 diff（两处调用），改前 `git status` 确认无人正在写它。
