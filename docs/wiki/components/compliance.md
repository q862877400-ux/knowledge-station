# compliance（合规触发与差距分析）

**位置**：`src/core/compliance/`
**一句话**：判断这次提问该不该走合规流程，并做制度与法规的差距分析。

## 职责

**合规门**：差距分析（`gap_analysis.py`，R-L11~13，Phase 7）——把用户上传的制度/文档逐条对回法规要求，找出缺口。
（**触发判断**在别处：`plugin/src/compliance-sentry.js` 是「这次提问是不是合规问题」的闸。）

**它不负责**：不检索条款（`retrieval`）、不生成答案（`llm`）、不做数值核验（`verification`）。

## 对外提供什么

| 合规差距分析 | `gap_analysis.py` | `api` 的 `/compliance/gap-analysis` |
| 合规策略 | 见 `api` 的 `/compliance/policies` | 界面 |

## 依赖什么

| `retrieval` | 上游模块 | 取法规条款 |
| `materials` | 同仓 | 取用户材料 |

## 明确不做什么

- **不做「这次提问要不要管」的判断**：那是 `plugin/src/compliance-sentry.js` 的闸（`isComplianceTriggered`），本模块不重复实现。
- **不判定法律效力**：效力档来自 `storage` 里的官方状态，不是本模块算的。
- **不给法律意见**：只做「你的制度和法规差在哪」的事实对照。

## 已知边界（诚实）

- **触发面是待扩的**：现在只对「合规问题」触发；**业主 2026-10-05 要求把它扩到「任何需要查大文档原文的时候」**（查技术文档也算），**未做**。
- 该扩口的登记见 `docs/CHANNEL-COVERAGE-PLAN.md` 与本周期的会话记录。
