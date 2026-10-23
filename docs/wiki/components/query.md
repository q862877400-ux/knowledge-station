# query（查询理解）

**位置**：`src/core/query/`
**一句话**：在检索之前，先把用户那句话拆成意图、主题与槽位。

## 职责

**问句 → 可检索条件的预处理层**（`understanding.py` 13.1 KB）：意图分类（`classify_intent`）、主题识别（`detect_theme`）、用户已声明的参数（`parse_declared`）、槽位抽取（`extract_slots`）、条件过滤（`apply_condition_filter`）、效力层级置顶（`rank_with_hierarchy` / `hierarchy_label`）、证据是否够的提示（`sufficiency_note`）、检索式改写（`refine_search_query`）、纠错识别（`detect_correction`）。

槽位 Schema 是两族：**工程参数**（建筑类型 / 火灾危险性 / 耐火等级 / 高度）+ **法律要素**（主体 / 客体 / 行为 / 同意状态）。追问严格基于 Schema。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 意图 / 主题 / 槽位 | `understanding.classify_intent()` / `detect_theme()` / `extract_slots()` | `api/server.py`、`llm/ks_answer.py` |
| 检索式改写 | `understanding.refine_search_query()` / `parse_declared()` | 同上 |
| 条件过滤与层级置顶 | `understanding.apply_condition_filter()` / `rank_with_hierarchy()` | 同上 |
| 证据充分性提示 | `understanding.sufficiency_note()` | 作答链路 |
| 纠错识别 | `understanding.detect_correction()` | 作答链路 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| 标准库 `re` / `typing` | 标准库 | 全部判定都是规则式 |

**实测没有任何外部或同仓依赖**：不调模型、不读库、不联网。

## 明确不做什么

- **不做检索算法**：通道选择与排序归 `retrieval`；本模块只做预处理与条件过滤，`rank_with_hierarchy` 的置顶规则归本模块。
- **不做术语桥**：大白话 → 术语的翻译在 `retrieval/term_bridge.py`；两处**MUST NOT** 各写一套。
- **不生成答案**：归 `llm`。
- **不调模型做解析**：槽位与意图都是规则式判定，不消耗 LLM。
- **不编造槽位**：追问严格基于 Schema；Schema 里没有的参数不追问、不猜。

## 关键数据

不持有表；只吃问句字符串与条款对象。

## 改了它会影响谁

- **`llm/ks_answer.py`**：先调本模块做意图与槽位，再据结果检索——改判定会直接改检索式
- **`api/server.py`** 的两处调用
- **`retrieval`**：拿到的查询串与本模块的改写结果


## 规模与覆盖（2026-10-23 实测）

| 项 | 数字 |
|---|---|
| 文件数 | **1** 个 `.py` |
| 行数 | **280** |
| 提到本子系统的测试文件 | **1** 个 |

**只有 1 个文件、1 个测试文件提到它**

> 数字口径：`rglob("*.py")` 排除 `__pycache__`；测试覆盖 = 在 `tests/*.py` 里出现过 `src.core.<本子系统>` 的文件数（**只是「提到」，不等于「被测」**）。

## 已知边界（诚实）

- ⚠ **与 `retrieval/term_bridge.py` 的分工要小心**：两者都在「把大白话变成能查的东西」。改任一处 MUST 先确认另一处做什么，否则会长出两套翻译逻辑。
- **本模块只有一个文件**（`understanding.py`），没有包级导出：调用方按 `from src.core.query import understanding` 使用。
- **槽位 Schema 写死在本模块**：扩参数只能改这里，改了要同步 `api` 与 `ks_answer` 两侧的追问话术。
