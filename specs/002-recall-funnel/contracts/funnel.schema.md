# 契约：漏斗记录格式

**Feature**: 002-recall-funnel | **File**: `eval/recall-funnel/funnel-per-query.jsonl`

> **⚠ 2026-10-06 更正（事后实测，本文原「四条测量线」整节作废，原话保留在下面 §0）**
>
> **原说法**：测量线分 `lexical` / `semantic_exact`（不经近似索引的精确计算）/ `semantic_ann`
> （走现在实际在用的近似索引）/ `fused`，并声称「**精确 vs 近似**是本计划最关键的分界线」。
>
> **实测（只读真库 + 源码）**：
> 1. `clause_vec` 的建表语句是
>    `CREATE VIRTUAL TABLE clause_vec USING vec0(clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512])`
>    （`src/core/storage/schema.sql`），检索是 `WHERE embedding MATCH ? AND k = ?`；
>    `sqlite-vec` 的 `vec0` 在本仓**只做暴力精确扫描**，**没有近似索引**。
>    ⇒ **`semantic_exact` 与 `semantic_ann` 是同一个东西**，这条分界线**在本仓不存在**。
> 2. 本仓的检索**不是单路**，是**六条通道**（`hybrid_engine.perform_hybrid_search`），
>    而且其中**四条在"外行用大白话提问"这条路上根本不触发**（详见下表）。
> 3. 契约里写的文件名 `funnel.jsonl` 与实际产物 `funnel-per-query.jsonl` 不一致
>    （原定名从未落地）——本文已改为实际名。
>
> **更正后的影响**：
> - 原判读规则里的 **`ann-only`（"只有近似索引丢"）结构性不可达** —— "调 ANN 参数"不是一条可修的路径；
> - **`not-any` 的判定口径必须重定义**（原定义依赖 `semantic_exact` 这条不存在的线）；
> - 随之 **SC-001 的"四种结论"从四种变三种**（见 [spec.md](../spec.md) 的更正块）。

---

## 0. 原话留痕（作废，不许再引用）

> | 线 | 用哪条通道 | 关键点 |
> |---|---|---|
> | `lexical` | **通道 B（FTS5 全文）** | 只按字找 |
> | `semantic_exact` | **通道 C 的精确计算** | **不经过近似索引**（用于判"模型是不是本来就知道"） |
> | `semantic_ann` | **通道 C 走现在实际在用的近似索引** | 这才是线上真实表现 |
> | `fused` | **六路合并后的结果** | 线上最终给的 |
>
> **⚠ 实现时 MUST 先确认"精确 vs 近似"在本仓怎么分别触发**（sqlite-vec 的暴力 vs 索引路径）。
> **若本仓无法分别触发 ⇒ 这一条 MUST 就地写明"做不到"，不得用近似的数冒充精确的数。**
>
> **回答这句"做不到"**：**做不到，而且不需要做到** —— 本仓没有近似路径，
> 所以不存在"用近似的数冒充精确的数"这个风险；两者本是同一次计算。

---

## 1. 更正后的「测量线」定义

**漏斗逐条记录的是：每一条**实际实现的**召回通道各自把 gold 排到第几名。**

| 线 | 通道 | 生产问答路径会触发吗 | 取回上限（写死在实现里） |
|---|---|---|---|
| `exact` | A 条款号/法条号精确 | **只在提问含条款号时** | **无上限** |
| `fts` | B FTS5 全文 | **恒** | **`LIMIT 20`** |
| `vec` | C sqlite-vec 向量 | **恒**（引擎可用时） | **`k = 20`** |
| `modality` | D 模态 | **只在提问含模态词时** | **无上限** |
| `legal_element` | E 法理要素（`subject`） | 🔴 **恒不触发** —— 生产三个调用点都不传 `subject_filter` | 无上限 |
| `behavior_scope` | F 行为客体 | 🔴 **恒不触发** —— 同上；且 `behavior_scope_segmented` **全库 0 行有值** | **`LIMIT 20`** |
| `fused` | 六路 RRF 融合 + 时效过滤 | 恒 | `cap`（生产问答 = `top_k`） |

**⚠ 两条口径 MUST 分开命名，不许混用**（这是复核打回过的错误）：

| 口径 | 定义 |
|---|---|
| **同预算口径**（`union.same_budget`，**报告主口径**） | 每一路都只取**前 d 条**再取并集，`d ∈ {20,100,1000}` |
| **生产上限口径**（`union.prod_caps`） | 照实现的**真实限量**：A/D/E 取全量、B/C/F 前 20 |

---

## 2. `lost_at` 的判读规则（**已更正**；对应 SC-001 的三种结论）

按**从后往前**的顺序判，**取最先丢的那一环**：

```text
1. 六路各自前 1000 名里都没有            ⇒ lost_at = not-any      （表示能力/排序够不着）
2. 前 1000 名里有、但每路前 20 名里没有   ⇒ lost_at = truncated     （被"只出 20 条"截断）
3. 同预算并集 @20 里有、fused 里没有      ⇒ lost_at = fusion-only   （只修融合）
4. 上面都不是（多个环节都丢）             ⇒ lost_at = multi-stage
```

**⇒ 已退役的取值**：`ann-only`（本仓无近似索引 ⇒ 结构性不可达）。
**⇒ 已退役的纪律句**："只要 `semantic_exact` 能找到，就不得下'换个更好的模型'这个结论" ——
它依赖一条不存在的线。**更正后的对应纪律**：

> **`not-any` 才是"够不着"的证据；`truncated` 是**截断**问题（改上限就能拿回来），
> 与"表示能力"无关。两者 MUST 分开报，不许合并成一句"召不回"。**
> ⚠ 且 `not-any` **只说明"排到了 1000 名以外"**，**不等于**"模型不认识这个意思" ——
> 要区分这两件事，需要另一把尺子（本口径给不出来，MUST 如实这么写）。

---

## 3. 一条记录算"可判读"的三个条件

1. **每条通道都填了**（`n` / `gold_rank` / `deep_n` / `deep_gold_rank` / `fires`）；
   通道"未触发"与"触发了但没命中"**MUST 分开**（前者 `fires=false`）。
2. **`evidence` 里写清判"丢了"的依据**（不接受只写 `lost_at` 而不写为什么）。
3. **`rank` 给了正确条文的最好名次** —— 这是判"是不是排得太靠后"的唯一依据。

---

## 4. 一行长什么样（实际产物，截自 `funnel-per-query.jsonl`）

```json
{"i":131,"bucket":"keep","flags":[],"kind":"定义",
 "query":"车间里那个直径30公分的喷气圆环上下套着布袋吹灰叫什么？",
 "gold_std":"GB/T XXXX","gold_clause":"3.x","modality_filter":null,
 "channels":{
   "exact":{"n":0,"gold_rank":null,"deep_n":0,"deep_gold_rank":null,"fires":false},
   "fts":{"n":20,"gold_rank":null,"deep_n":1000,"deep_gold_rank":855,"fires":true},
   "vec":{"n":20,"gold_rank":1,"deep_n":1000,"deep_gold_rank":1,"fires":true},
   "modality":{"n":0,...},"legal_element":{"n":0,...},"behavior_scope":{"n":0,...}},
 "union":{"same_budget":{"@20":true,"@100":true,"@1000":true,"pool@1000":1316},
          "prod_caps":{"pool":40,"hit":true}},
 "fused":{"n":40,"gold_rank":2,"hit@20":true,"hit@100":true,"hit@1000":true},
 "hit_channels":["vec"],"hit_in_deep_union":true,"fts_pool":...,
 "replica_check":"ok","elapsed_s":5.6}
```

**`replica_check` 是什么**：漏斗自带六路 SQL 副本（因为生产函数**不返回**单通道候选列表），
每条问法都当场把副本的前 20 与 `perform_hybrid_search(单通道)` 逐个比。
**覆盖面**：只覆盖 A/B/C/D 四路、只比前 20；**深读名次不在这层自检里**。

---

## 5. 汇总表（**已产出**，实际数字见 `eval/recall-funnel/funnel-summary.json` 与 `REPORT.md`）

按 `lost_at` 归并（全量 171 条实测）：

| lost_at | 题数 | ⇒ 下一步动哪 |
|---|---|---|
| `not-any` | **104（60.8%）** | 表示能力 / 排序深度（**不再等于"模型不认识"**） |
| `truncated` | **48（28.1%）** | 取回上限（"只出 20 条"） |
| `fusion-only` | **4** | 融合策略 |
| `multi-stage` + `进得了前 8` | **15**（其中 9 条进得了用户看的 8 条） | — |
| `ann-only` | **0（结构性不可达）** | —— |

**⇒ 再按子集切一遍**（短条款 / 零重合 / 带标准号 / 普通）：实测**按类型没有实质差别**
（定义 `not-any` 82/136、要求 22/35），**按"字面零重合"切片差别很大**
（132/171 零重合 ⇒ 通道 B 结构上不可能召回）。
