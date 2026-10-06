# Phase 1 数据模型：召回漏斗诊断

**Feature**: 002-recall-funnel | **Date**: 2026-10-06

> **四个实体。本周期全部落 JSONL 文件，不建数据库表**（见 plan.md 的 Complexity Tracking）。

---

## E1 基准题（Benchmark Item）

**是什么**：一条提问 + 一个或多个**经人工确认的**正确答案。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qid` | string | ✅ | 稳定标识，如 `q001`。**一旦分配不得复用** |
| `query` | string | ✅ | **提问原话**（外行人怎么说的，不改写） |
| `gold_clause_ids` | string[] | ✅ | 正确条文的标识。**允许一条问题多个答案**（同一术语在多份文件里各有定义） |
| `gold_notes` | string | — | 人工确认时的备注（为什么这几条算对） |
| `subsets` | string[] | ✅ | 难度子集标签，取值见下 |
| `answer_out_of_corpus` | bool | ✅ | **答案不在库内** ⇒ 统计时排除，**不算系统失败** |
| `source` | string | ✅ | 提问从哪来（`lay-phrasing` / 人工构造 / …） |
| `confirmed_by` | string | ✅ | **谁确认的答案**（本规格要求人工确认，此处留痕） |
| `confirmed_at` | date | ✅ | 确认日期 |

**`subsets` 取值**（对应 spec 的 FR-005）：
- `short-clause` —— 正确答案是 <40 字的短条款
- `zero-overlap` —— 提问与正确条文**无任何 2 字重合**
- `with-standard-no` —— 提问里含明确标准号
- `plain` —— 以上都不是

**校验规则**：
- `gold_clause_ids` 非空，**除非** `answer_out_of_corpus = true`
- 每条 `gold_clause_id` MUST 能在库里查到（**防止标注时抄错**）
- `query` MUST 是原话，**不得**为了好检索而改写

---

## E2 基线快照（Baseline Snapshot）

**是什么**：一次冻结下来的系统状态。**以后所有实验的对照物。**

**落 `eval/recall-funnel/baseline-v0/` 三件套：**

### `config.json`
| 字段 | 说明 |
|---|---|
| `captured_at` | 采集时间 |
| `embedding_model` / `embedding_dim` | 语义模型与维度（实测 512） |
| `has_lexical_channel` | 有没有按字检索通道 |
| `vector_index` | 近似索引类型与版本（实测 sqlite-vec v0.1.9） |
| `channels` | **六条通道各自是否启用** |
| `top_k` | 默认取回数 |
| `rerank` | 重排器开关与模型 |
| `machine` | CPU / 内存 / GPU |
| `corpus_size` | 库内条文数（实测 522,021） |
| `code_revision` | **代码版本（git 短哈希 + 是否有未提交改动）** |

### `metrics.json`
| 字段 | 说明 |
|---|---|
| `by_cutoff` | 前 20 / 前 100 / 前 1000 / 更靠后各截断位置的命中率 |
| `by_channel` | **四条测量线**（按字 / 语义精确 / 语义近似 / 合并后）各自命中率 |
| `by_subset` | 按 E1 的每个子集分别算 |
| `n_used` | 实际计入的题数（**排除库外答案后**）、以及各自的分母 |
| `run_id` | 本次运行的标识，用于验"两次跑是否一致" |

### `results.jsonl`
**每条问题一行**，含该问题在四条测量线上的完整返回（或足以复现的最小信息）。

---

## E3 漏斗记录（Funnel Record）

**是什么**：**一条问题在每一步"还在不在"。** 这是本计划的核心产物。

| 字段 | 类型 | 说明 |
|---|---|---|
| `qid` | string | 对应 E1 |
| `gold_ids` | string[] | 该题的正确条文 |
| `per_channel` | object | 四个测量线各自：`hit_at_1000` / `hit_at_100` / `hit_at_20` / `rank`（正确条文的最好名次） |
| `lost_at` | enum | **在哪一步丢的**：见下 |
| `evidence` | string | 判"丢了"的依据（比如"该通道前 1000 条里没有 gold"） |

**`lost_at` 取值**（对应 spec 的 SC-001 四种结论）：
| 值 | 含义 | 下一步该动哪 |
|---|---|---|
| `ann-only` | 语义精确能找到，**语义近似找不到** | **只修近似索引**（换 embedding 无用） |
| `fusion-only` | 各路都能找到，**合并后丢了** | **只修融合策略** |
| `multi-stage` | 多个环节都丢 | 按最先丢的那一环动 |
| `not-any` | **连语义精确都找不到** | ⇒ 才轮到"表示能力"这条线 |

---

## E4 改进实验（Improvement Experiment）

**是什么**：一次**只改一处**的 A/B。

| 字段 | 说明 |
|---|---|
| `exp_id` | 如 `exp-1-retrieval-text` |
| `changed` | **改了什么（只允许一项）** |
| `frozen` | **逐项列出没动的东西**（模型 / 按字检索 / 索引参数 / 取回数 / 融合 / 提问文本） |
| `stop_loss` | **开跑前定好的**：放弃阈值 / 观察阈值 / 推广阈值 |
| `before_metrics` / `after_metrics` | 同口径的前后对比 |
| `verdict` | `放弃` / `保留观察` / `推广` |
| `verdict_reason` | 一句话，**MUST 挂回具体数字** |

**校验规则**：
- `changed` MUST 只有一项（对应 FR-013）
- `stop_loss` MUST 在跑之前写入（**跑完再补无效**）
- `verdict` MUST 能从 `before/after` 直接读出（**不接受"感觉变好了"**）

---

## 实体关系

```text
E1 基准题 ──(qid)──▶ E3 漏斗记录 ──(对比)──▶ E4 改进实验
                          ▲
E2 基线快照 ──────────────┘
   （E2 是 E4 的 before 侧；E4 的 after 侧 = 改一处后重跑 E3）
```

**⇒ 数据流向**：E1 立好 ⇒ 跑出 E2（冻结）⇒ 跑出 E3（定位）⇒ 依 E3 的 `lost_at` 决定改哪 ⇒ E4 验一次。
