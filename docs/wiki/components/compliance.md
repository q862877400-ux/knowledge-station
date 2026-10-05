# compliance（合规差距分析）

**位置**：`src/core/compliance/`
**一句话**：把用户上传的制度逐条对回法规义务，指出缺在哪。

## 职责

**制度与法规的差距对照**（`gap_analysis.py`）：制度文本导入（`internal_policy`）→ 法定义务清单（`legal_obligation`，来自库内「应当 / 必须」型条款）→ 逐义务与制度章节关键词比对 → 三色判定 → 落 `gap_analysis`（挂 `review_task`）→ 整改建议与汇总。

判定是**可解释的规则式，不是 LLM**：命中率 ≥ 0.5 或绝对命中 ≥ 3 → green（已覆盖）；命中 ≥ 1 → yellow（不完善）；命中 0 → red（缺失）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 制度文本导入 | `gap_analysis.import_internal_policy(policy_name, policy_text)` | `api/server.py` 的 `POST /api/v1/compliance/policies` |
| 法定义务清单构建 | `gap_analysis.build_obligations(refresh)` | 差距分析前置 |
| 差距分析 | `gap_analysis.run_gap_analysis(policy_id)` | `api/server.py` 的 `POST /api/v1/compliance/gap-analysis` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage` | 上游模块 | 写 `internal_policy` / `legal_obligation` / `gap_analysis` / `review_task`，读库内条款 |
| 库内「应当 / 必须」型条款 | 数据 | 义务清单的来源 |

## 明确不做什么

- **不做「这次提问要不要走合规流程」的触发判定**：那是 `plugin/src/compliance-sentry.js` 的词表闸（`isComplianceTriggered`）与 `llm/jev_guard.py` 的隐性合规判定；本模块不重复实现。
- **不用 LLM 判合规**：判定是可解释的关键词口径；换判据只改本模块，不要去调模型。
- **不做条款检索与排序**：候选条款的找法归 `retrieval`。
- **不生成答案**：自然语言结论归 `llm`。
- **不给法律意见**：只做「你的制度和法规差在哪」的事实对照。
- **不做条款效力判定**：效力档来自 `knowledge/legal_status.resolve_status`。

## 关键数据

| 表/对象 | 关键字段 | 说明 |
|---|---|---|
| `internal_policy` | `policy_id` / `policy_name` / `sections` | 用户上传的制度文本 |
| `legal_obligation` | `obligation_id` / `clause_revision_id` | 法定义务清单，逐条挂到条款 |
| `gap_analysis` | `gap_id` / `task_id` / `legal_obligation_id` | 逐义务的三色结论 |
| `review_task` | `red_count` / `yellow_count` / `green_count` | 汇总，挂在这张任务上 |

## 改了它会影响谁

- **`api/server.py` 的三个端点**：`GET|POST /api/v1/compliance/policies`、`POST /api/v1/compliance/gap-analysis`
- **界面上的评审任务**：`review_task` 的计数与明细
- **三色阈值只写在本模块**：改它只改这一处

## 已知边界（诚实）

- **`legal_obligation` 依赖库内存在「应当 / 必须」型条款**：库里没有这类条款时义务清单为空（未核：是否有兜底提示）。
- **本模块只有 `gap_analysis.py` 一个文件**（7.9 KB）；合规触发的判定代码**不在** `src/core/compliance/` 里，别在这里找。
