# llm（模型调用与作答）

**位置**：`src/core/llm/`
**一句话**：把证据交给模型，拿回一段只依据证据的答案。

## 职责

**产品那一句「问题进，带依据的结论出」的后半截**：`ks_answer.py` 50.7 KB 是取证答案的引擎侧实现；`deepseek_client.py` 是 DeepSeek 官方 API 流式客户端；`jev_client.py` + `jev_guard.py` 是 Jev（TypeSafe System One）结构化判断通道与合规护栏。

**它不负责**：不检索（`retrieval`）、不核验数值（`verification`）、不导出交付物（`exports`）。

## 对外提供什么

| 取证答案 | `ks_answer.py` | `api` 的 `/ks/answer`、插件 `ks_answer` 工具 |
| DeepSeek 流式客户端 | `deepseek_client.py` | `ks_answer` |
| Jev 结构化判断 | `jev_client.py` | 合规触发链路 |
| Jev 合规护栏 | `jev_guard.py` | 作答门 |

## 依赖什么

| DeepSeek API | 外部 | 模型调用 |
| Jev（TypeSafe System One） | 外部 | 结构化判断 |
| `retrieval` | 上游模块 | 候选证据 |
| 凭据 | `settings/secret_store.py` | 密钥 |

## 明确不做什么

- **不许凭记忆作答**：LLM 只接收**问题 + 本地检索出的证据片段**，没有机会编造（这是产品红线）。
- **不做数值/模态/法理核验**：那是 `verification` 与 `quality` 的活。
- **不做合规判断**：该不该管这次提问由 `compliance` 决定，`llm` 只负责在其放行后作答。
- **不做交付物渲染**：报告/PPT 在 `exports`。

## 已知边界（诚实）

- **外发纪律**：外发 prompt 仅含问题 + 最小必要证据；完整 payload 落库追责。
- **Jev 是 2026-09-24 业主授权接入的**，业主报障驱动；它那一侧有独立护栏 `jev_guard.py`。
- ⚠ **字段描述 ≠ 运行时语义**：本仓曾照 OpenAPI 描述当根因被复核推翻。契约里的行为以代码为准。
