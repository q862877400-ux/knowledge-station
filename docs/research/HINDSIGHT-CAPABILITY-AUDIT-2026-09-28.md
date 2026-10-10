# Hindsight 官方能力核实 —— 「我们是不是在造轮子」

> **触发**：业主 2026-09-28 质疑「我们可能在造轮子」，并给了一份《亿级知识库召回难题》材料，
> 要求**认真仔细调研 hindsight 的用法、把官网文档通读、一篇一篇分析**。
> **本文是一手核验结果**，不是转述。核验日期 2026-09-28。

## 0. 先说方法与一次"抓到了≠抓对了"

**权威一手件**：Hindsight 官方 OpenAPI —— `https://hindsight.vectorize.io/openapi.json`，
**HTTP 200、603,960 字节、603,960 B**，`info.title = "Hindsight HTTP API"`、**`info.version = 0.10.1`**、**77 条路径 / 99 个操作**。
本机副本 `%TEMP%\hs-docs\openapi.json`；解析脚本 `var/tmp/hs-openapi-dump.py`（端点清单）、`hs-verify-claims.py`（逐条核材料说法）、`hs-find-config.py`（定位配置字段）。

⚠ **一次失败要留痕**：文档站是 SPA，`/docs/developer/api/retain`、`/docs/concepts`、`/docs/guides/templates-hub`
等 5 个路径**全部返回同一个 22,747 B、`<title>` 仅为 "Hindsight" 的壳**（HTTP 200 但不是正文）。
**只有 OpenAPI 与本机那个活的 Hindsight 服务（`http://127.0.0.1:8888`）是可核的一手来源。**

## 1. 业主给的那份材料：真与假（逐条核）

| 材料说法 | 核验结果 | 依据 |
|---|---|---|
| 官方控制面板支持简体中文 | **未核**（与本项目决策无关，未查） | — |
| 有"记忆市场" | **未核** | — |
| ✅ 记忆库可导出/导入/克隆 | **✅ 证实** | `GET /export`（Export bank template）、`POST /import`（Import bank template）、`POST /clone`（Clone a bank，async）、`POST /transfer/export` + `POST /transfer/import`（Export/Import a bank，async）、`POST /document-transfer/export`（Export documents，async） |
| ✅ Templates Hub 分享的是**配置**不是记忆 | **✅ 与官方 API 形状吻合** | `GET /v1/bank-template-schema`（Get bank template JSON Schema）+ 上述 template 导出/导入 |
| ⚠️ `retain` 有 `context` 参数 | **❌ 位置错** | 官方 `RetainRequest` 字段**只有 4 个**：`items` / `async` / `document_tags` / `operation_id`。**没有 `context`** |
| ✅ `retain_mission` 会影响提取 | **✅ 存在，但属银行级配置** | spec 中 `mission` 出现 9 次、`retain_mission` 5 次；`mission` 出现在 `BackgroundResponse` / `BankListItem` / `BankProfileResponse`（银行级字段），**不在单次 retain 请求体** |
| ❌ `retain_extraction_mode`（concise/verbose/custom） | **❌ 不存在** | 整份 spec 中 `extraction_mode` / `retain_extraction` / `concise` / `entity_types` / `custom_instructions` **各 0 次**；`verbose` 仅 2 次（与该参数无关） |
| — | 🔴 **材料漏了、但对我们更要紧的一整块** | 见 §2 |

**⇒ 这份材料是"方向对、细节错"**：它说的能力**大体存在**，但 `retain` 的参数位置讲错、`extraction_mode` 是编的。
**不可直接当依据引用；下面 §1 表格已把它逐条改正。**

## 2. 🔴 我们**确实在造轮子**——官方已有的一整块（我们从没查过）

从 99 个端点里摘出**与我们"派生记忆层/知识库"诉求直接对应**的：

| 官方能力 | 端点（一手） | 对我们的意义 |
|---|---|---|
| **知识库页面**（建/读/改名移动/删除） | `POST /knowledge-base/pages`、`GET /knowledge-base/pages/{page_id}`、`PATCH`+`DELETE /knowledge-base/nodes/{node_id}` | **业主要的"知识库"官方已有** |
| **知识库目录树** | `GET /knowledge-base/tree`、`POST /knowledge-base/folders` | 我们自研的"多级目录"官方也有 |
| **知识库混合检索** | `GET /knowledge-base/search` —— 摘要逐字：**"Hybrid search over knowledge pages (BM25 + vector)"** | **官方早就在做 BM25+向量混合** |
| **知识库整包导出为 markdown** | `GET /knowledge-base/export`（"Export the knowledge base as a markdown bundle"） | 与我们的材料平面思路重叠 |
| **银行级导出/导入/克隆** | 见 §1 表 | 记忆"带走/重建"官方已解决 |
| **文档整批转记忆** | `POST /files/retain`（"Convert files to memories"） | 我们"材料 → 派生层"官方有一等公民 |
| **归并（consolidation）全套** | `POST /consolidate`、`POST /consolidation-strategies/preview`、`POST /consolidation/recover` | 我们上一轮纠结的"归并从未跑过"，官方有 preview/recover |
| **知识页**（agent 常驻答案） | `GET/POST /mental-models`、`/refresh`、`/dry-run-refresh`、`/history`、`/clear` | 这是 Hindsight 的"常驻答案层" |
| **指令层**（注入提示词） | `GET/POST/PATCH/DELETE /directives` | 上一轮我建的那条"最高指令"就是它 |
| **审计与用量可观测** | `/audit-logs`、`/audit-logs/stats`、`/llm-requests`、`/llm-requests/stats`、`/stats`、`/stats/memories-timeseries`、`/metrics` | 我们的"垃圾率/成本"监控，官方已有全套 |
| **变更史（可回溯）** | `GET /memories/{id}/history`、`/mental-models/{id}/history`、`/operations/{id}/retry` | 上一轮我担心"派生层被洗掉"，官方有 history + retry |
| **试运行（不落库）** | `POST /memories/dry-run-extract`、`POST /prompts/preview`、`/mental-models/{id}/dry-run-refresh` | **官方支持"先看不写"** |
| **Webhook 事件** | `/webhooks`、`/webhooks/{id}/deliveries` | 可做"结论被推翻时通知" |
| **别名**（bank 改名/多标识） | `/aliases`（list/add/remove/patch） | 命名演化，官方有一等支持 |

**⇒ 结论一（先于任何判断）**：业主的直觉是对的。**"知识库 + 记忆统一管理"这件事，官方 v0.10.1 已经有
约 20 个端点在做了**，而我上一轮做的整轮外部调研（记忆系统家族 + 技能进化 + 派生层）**基本没查官方 API 本身**——
这是我的方法论失误，不是个案失误。

**⇒ 结论二（同样重要）**：这**不等于**我们该换成 Hindsight。理由见 §4。

## 3. 我们的用法 vs 官方能力：差在哪（本机服务实测 vs 官方 schema）

我们本机那个 Hindsight（`http://127.0.0.1:8888`，bank `coding-agent::zcode`）上一轮实测：
114,970 条事实、5,337,849 条边、**`pending_consolidation: 114970`（全部）、`total_observations: 0`、
`last_consolidated_at: null`** ⇒ **归并从未跑过**；知识页 8 篇（全在 Initiatives 文件夹）。

对照官方能力，我们**不是"缺功能"，而是"开了功能没用"**：
- 归并没跑（配置没开，不是没有这个能力）；
- 8 个知识页只是 agent 随手记的，没当"常驻答案层"用；
- 从没碰过 `directives`（上一轮我建了第一条，但那是**我手工建的**）；
- 从没用过 `audit-logs` / `stats` / `llm-requests` 来管"垃圾率"。

## 4. 🔴 造轮子的账，怎么算才诚实（三条，都不是"那就不用"）

| # | 事实 | 判读 |
|---|---|---|
| **A** | 官方有 knowledge-base（pages/tree/search/export）、bank 导出导入克隆、files→memories、consolidation、mental-models、directives、audit-logs | **我们自研的这些应当停**。这违反本仓"通用层纯借鉴、不造轮子"的既定纪律（`AGENTS.md`）。**我上一轮没先查官方 API 就去外部找论文，是方法论失误。** |
| **B** | 官方一切以 **bank 为隔离单元**（`/v1/default/banks/{bank_id}/...` 全部挂在 bank 下），而 bank 之间的索引扇出、bank 数量上限，是**我们上一轮已实测的墙** | **官方形态正是"一个项目一个记忆库"**。我们要做的是"一套库装全部资料 + 跨项目派生记忆"，**与 bank 隔离模型方向相反** |
| **C** | 官方 `knowledge-base/search` 是 **BM25 + vector 混合**，而我们已实测向量通道随条数线性、官方自述 brute-force only | **我们要解决的"亿级召回"，官方方案里没有现成答案**（他们用 Postgres+pgvector，量级未知）；这块**不是造轮子，是真问题** |

**⇒ 一句话**：**能停的轮子很多（我们的记忆层/知识库/审计基本重复），但"亿级召回"那块没有现成轮子可骑**。

## 5. 我没核的（如实）

- 文档站**正文**没读到（SPA 壳，见 §0）——所以"面板支持中文""Templates Hub 实际内容"等**未核**；
- 没读 `bank template JSON Schema` 的实际内容（只知它存在）；
- 没核官方**规模指标**（多少条记忆 / 多少 QPS / 延迟）——OpenAPI 里没有；
- 没核 `knowledge-base/search` 的**参数与返回形状**（只知摘要说 BM25+vector）；
- 本机 Hindsight 的实际版本是否与 0.10.1 一致（未核 `/version`）。
