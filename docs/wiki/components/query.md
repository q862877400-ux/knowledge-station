# query（查询理解）

**位置**：`src/core/query/`
**一句话**：在检索之前，先把用户那句话读懂。

## 职责

**Query Understanding Layer**（`understanding.py` 13.1 KB，Phase 9.2 / R9·R40·R41·R52·R53·R60）——把用户的自然语言问句解析成检索能用的条件。

**它不负责**：不检索（`retrieval`）、不生成答案（`llm`）。

## 对外提供什么

| 查询理解 | `understanding.py` | `retrieval` |

## 依赖什么

| `domain` | 同仓 | 对象形状 |
| LLM（可选） | 外部 | 需要模型辅助解析时 |

## 明确不做什么

- **不做检索排序**：它只**预处理问句**，把结果交给 `retrieval`。
- **不做术语桥**：术语桥在 `retrieval/term_bridge.py`（P1 翻译层第一版）——两处**MUST NOT** 各写一套。

## 已知边界（诚实）

- ⚠ **与 `retrieval/term_bridge.py` 的分工要小心**：两者都在「把大白话变成能查的东西」。
  **改任意一处 MUST 先确认另一处做什么**，否则会出现两套翻译逻辑。
