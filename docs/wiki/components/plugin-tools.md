# plugin-tools（插件对 agent 暴露的工具）

**位置**：`plugin/src/`（注册在 `index.js` 的 `apply()`）
**一句话**：引擎能力对 agent 的入口——四个读、一个只读、一个写。

## 职责

插件把引擎的 HTTP 能力包成**模型可见的工具**。实测注册 **6 个**（`ctx.tools.register` × 6）：

| 工具 | 定义位置 | 落地端点 |
|---|---|---|
| `ks_ping` | `index.js` `makePingTool` | `GET /api/v1/health`（**无 token**） |
| `ks_resolve_clause` | `index.js` `makeResolveTool` | `GET /api/v1/clauses/resolve`（Bearer） |
| `ks_answer` | `index.js` `makeAnswerTool` | `POST /api/v1/ks/answer`（Bearer） |
| `ks_effect_report` | `index.js` `makeEffectReportTool` | `/api/v1/report/effect`（Bearer） |
| `ks_materials` | `materials.js` `makeMaterialsTool` | 引擎材料端点（**只读**） |
| `ks_collect` | `collect.js` `makeCollectTool` | 引擎采集端点（**写**） |

## 逐工具：用途 / 参数 / 返回 / 边界

**`ks_ping`** —— 用途：查引擎在不在、端口 / 进程 / 组件状态。参数：无。返回：`ok` / `httpStatus` / `engine{port,pid,reused}` / `status` / `uptimeSeconds` / `dbStatus` / `vectorEngine` / `parserWorker`。边界：`vectorEngine` 是**便宜的三态**（ok = 曾加载成功 / offline = 上次加载失败 / unknown = 从没试过），**不是压测**；20 秒超时；可并行。

**`ks_resolve_clause`** —— 用途：按「标准号 + 条款号」取原文。参数：`standard_no`、`clause_number`（都必填，工具自己 URL 编码）。返回：命中条款（含 `legal_status`、可点 PDF 锚 `evidence_url`、`bookmarked`）或明确的查无此条标记。边界：查法规模式 / 收藏夹模式下，范围外命中带 `bookmarks_scope` / `folder_scope: "outside"`——**只能用于定位，不得写入依据区**；非 effective 的只能作历史沿革或预告。

**`ks_answer`** —— 用途：取证问答。参数：`query`（必填）；`params` 可选 `top_k`（≤50）、`bookmarks_only`、`folder_id`、`max_evidence`、`material_project_id`、`kb_folder_ids`、`kb_doc_ids`。返回：依据 / 推导 / 结论三段式 + `tier` + `verification` + `notes` + `answer_scope`。边界：引擎自带推理，**可超 120 秒**；**空数组 ≠ 「没给范围」**——引擎回 422 且一次检索都不做，绝不退化成全库；`verification.unsupported_context` 列出的引用 MUST 如实披露；**不声明可并行**（走 exclusive）。

**`ks_effect_report`** —— 用途：库内效力现状。参数：`include_attention`（默认 true）、`limit`（默认 10，上限 20）。返回：五色统计（🔴 在用已废止 / 被代替 · 🟡 即将实施 · 🟢 现行有效 · ⚪ 状态未知 · 🔵 参考资料·仅参考）+ 标准树 / 法规树分计 + 红黄清单 top-N。边界：**只读聚合、零 LLM**；host 侧裁剪，**绝不回传全量分类树**；`attention_error` 非空 = 清单没取到（统计仍有效，**别当成「没有废止文件」**）；可并行。引擎侧实现在 [exports](exports.md) 的 `effect_report.py`。

**`ks_materials`** —— 用途：找项目 id、看材料评审状态。参数：`action`（`projects` 默认 / `materials` / `inbox`）、`project_id`、`status`（`pending` / `approved` / `rejected`）。返回：项目、材料（评审三态、来源层级 T0~T4、任务效力、切片数）、未登记文件。边界：**只读是纪律**——没有批准 / 拒绝路径；只有 `approved` 的材料会进 `ks_answer` 提示词；有 pending 就如实说「未批准、不进结论」。

**`ks_collect`** —— 用途：抓一个 URL 的正文，登记成该项目的待评审材料。参数：`url`（必填，内网 / 保留地址会被拒）、`project_id`、`title`、`note`。返回：登记后的材料与 `review_status`，以及本次已用 / 上限。边界：**只能登记 `pending`**，发不出批准；**不发 `source_tier`**（不得自 claim 可信度）；**一次一条**，会话内上限**暂定 20**、超出**响亮报错**；**不声明可并行**。

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| 引擎 HTTP API | 本地服务 | 全部工具的落地；Bearer token 从引擎 session 文件读 |
| DSH 宿主 | 外部 | 工具注册（随 fiber 释放）与界面容器 |

## 明确不做什么

- **不直连数据库、不读本地数据文件**：全部经引擎的鉴权 HTTP API；能力必须先在引擎侧有端点，插件只当入口之一。
- **不替用户评审材料**：读一个工具、写一个工具，**名字即权限**；写的那一个也只能登记 pending。
- **不做检索排序、不生成答案、不做核验**：这些在引擎侧（`retrieval` / `llm` / `verification`）。
- **不把「取不到」说成「没有」**：HTTP 200 但信封缺 `data` 一律**抛错**，不许当成空结果。
- **不做范围参数的最终裁决**：host 会强制覆盖模型的 `folder_id` / `material_project_id` / `kb_folder_ids`；回执里的 `answer_scope` 只证明 **host 传了参**，**不证明引擎侧过滤生效**。

## 关键数据

无自有表：数据全在引擎侧。只读引擎 session 文件（端口 / token，每次启动轮换）。

## 改了它会影响谁

- **agent 的实际行为**：工具描述每轮随工具表进上下文（`ks_answer` 因此压到 ≤10 行，完整用法只在**首次调用回执**里给）
- **引擎端点契约**：改工具参数即改对引擎的调用面
- **`chatmode.js` 的强制范围**：会话级收藏夹 / 项目由 host 注入 `ks_answer`

## 已知边界（诚实）

- **引擎按需拉起并复用**：只有本插件拉起的实例才会被它停；已存在的健康实例只复用、不杀。
- **`ks_collect` 的会话上限 20 是暂定值**（采集预算未定案），不是产品决定；插件重载后计数归零（它是刹车，不是账本）。
- ⚠ **`plugin/src/*.bak-20260927-*` 是别人的未提交件**，不许动。
