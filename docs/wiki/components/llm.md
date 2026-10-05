# llm（模型调用与取证答案）

**位置**：`src/core/llm/`
**一句话**：把「问题 + 证据」送进模型，并把返回的文本装配成可核验的答案。

## 职责

**模型调用的唯一出口**：DeepSeek 流式问答（`deepseek_client.py`）、取证答案三段式（`ks_answer.py` 50.7 KB，本模块最大）、Jev 结构化判断（`jev_client.py`）、隐性合规判定（`jev_guard.py`）、外发登记（`egress_audit.py`）、负反馈转 Few-shot（`fewshot.py`）。

接手的是**已排好序的候选条款**（`retrieval` 交付），交付的是**答案文本 + 核验结果**。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 取证答案（依据 / 推导 / 结论） | `ks_answer.answer()` | `api/server.py` 的 `/api/v1/ks/answer` ⇒ 插件 `ks_answer` 工具 |
| 流式问答 | `deepseek_client.stream_chat_completion()` | `api/server.py` 的 SSE 问答端点 |
| 一次性补全 | `deepseek_client.chat_complete()` | `update/discover.py`（公告抽取） |
| 结构化判断 | `jev_client.system_one()` / `noul()` / `choice()` / `score()` | `jev_guard`、`update/jev_ingest.py` |
| 隐性合规判定 | `jev_guard.judge(text)` | `api/routes_law.py` |
| 外发登记与审计 | `egress_audit.record_egress()` / `query_egress()` / `export_egress()` | `ingestion/mineru_cloud.py`、`jev_client`、`discover`；审计 API |
| 负反馈 → Few-shot | `fewshot.inject_fewshot()` | `deepseek_client` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| DeepSeek API | 外部服务 | 推理；Key 从环境变量 / `settings` 读，未配置抛 `LLMError`，上层降级为占位答案 |
| Jev（TypeSafe System One） | 外部服务 | 结构化判断；带熔断（`breaker_open`） |
| `retrieval` | 上游模块 | `ks_answer` 调 `search_with_details`（检索算法归 `retrieval`） |
| `query/understanding` | 上游模块 | 意图、槽位、查询改写 |
| `verification/typed_verifier` | 同仓 | 证据-答案核验 |
| `knowledge/legal_status` | 上游模块 | `resolve_status` 现行版判定 |

## 明确不做什么

- **不做检索算法**：`ks_answer` 只调用 `retrieval`；通道取舍与排序归 `retrieval`。
- **不做核验判定**：核验结论由 `verification/typed_verifier` 出，本模块只把它放进答案。
- **不做合规差距分析**：义务清单与三色判定在 `compliance`。
- **不做「这次提问算不算合规问题」的触发判定**：词表在 `plugin/src/compliance-sentry.js`，隐性一类在 `llm/jev_guard.py`。
- **不替用户批准材料**：只有 `review_status='approved'` 的材料进提示词；批准是用户的判断。
- **不做外发拦截**：「零外发」红线已于 2026-09-17 撤销，改为「外发可审计」；`egress_audit` 是**唯一登记口**，别处不得自己写外发记录。

## 关键数据

| 表/对象 | 关键字段 | 说明 |
|---|---|---|
| `debug_dump` | `trigger_type='egress'` | 非 chat 云调用（rerank / VLM / 云解析）的登记；问答链路另有 `server.py` 的 `_write_debug_dump` 全量落库 |

## 改了它会影响谁

- **`api` 的问答端点与 SSE**：返回结构直接决定前端与工具回执
- **`ks_answer` 工具**：`plugin/src/index.js` 的 `trimVerification` 是白名单——引擎新增核验字段而白名单没加，就到不了模型眼前
- **答案质量基线**：改提示词或装配 MUST 重跑 Golden Set

## 已知边界（诚实）

- **Jev 三条硬约束**（照做）：Noul 没有 confidence；每个 Noul 必须写 `criteria`；要门控只能用 Choice / Score 的 confidence。
- **提示词最小化是成本与准确性口径，不是外发禁令**：红线已改，读旧文档时别当成「不许外发」。
- ⚠ `fewshot.py` 里旧理由「不做微调是因为零外发下不可行」**已作废**（代码内已就地更正）：不做微调是工程选择。
- **`ks_answer.py` 头注引的 `docs/DSH_REINCARNATION.md` 已不在仓库**（未核：是否已迁到别处）。
