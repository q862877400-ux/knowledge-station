# 契约：漏斗记录格式

**Feature**: 002-recall-funnel | **File**: `eval/recall-funnel/funnel.jsonl`

**这是本计划的核心产物**：一条问题在每一步"还在不在"。
**字段定义**见 [data-model.md](../data-model.md) E3。**本文定"什么算一条可判读的漏斗记录"。**

---

## 一行长什么样

```json
{"qid":"q001",
 "gold_ids":["clrev_01M..."],
 "per_channel":{
   "lexical":   {"hit_at_1000":true, "hit_at_100":true,  "hit_at_20":false, "rank":47},
   "semantic_exact":{"hit_at_1000":true, "hit_at_100":true,  "hit_at_20":true,  "rank":3},
   "semantic_ann":  {"hit_at_1000":false,"hit_at_100":false, "hit_at_20":false, "rank":null},
   "fused":     {"hit_at_1000":true, "hit_at_100":true,  "hit_at_20":false, "rank":33}},
 "lost_at":"ann-only",
 "evidence":"语义精确第 3 名命中；语义近似前 1000 条里没有 gold"}
```

---

## 「四条测量线」的准确定义（**必须先定，否则数字不可比**）

| 线 | 用哪条通道 | 关键点 |
|---|---|---|
| `lexical` | **通道 B（FTS5 全文）** | 只按字找 |
| `semantic_exact` | **通道 C 的精确计算** | **不经过近似索引**（用于判"模型是不是本来就知道"） |
| `semantic_ann` | **通道 C 走现在实际在用的近似索引** | 这才是线上真实表现 |
| `fused` | **六路合并后的结果** | 线上最终给的 |

**⚠ 实现时 MUST 先确认"精确 vs 近似"在本仓怎么分别触发**（sqlite-vec 的暴力 vs 索引路径）。
**若本仓无法分别触发 ⇒ 这一条 MUST 就地写明"做不到"，不得用近似的数冒充精确的数。**

---

## `lost_at` 的判读规则（对应 SC-001 的四种结论）

按**从后往前**的顺序判，**取最先丢的那一环**：

```text
1. semantic_exact 就找不到        ⇒ lost_at = not-any     （才轮到"表示能力"）
2. semantic_exact 能找到、
   但 semantic_ann 找不到          ⇒ lost_at = ann-only    （只修索引）
3. 各路都能找到、fused 找不到      ⇒ lost_at = fusion-only （只修融合）
4. 上面都不是（多个环节都丢）      ⇒ lost_at = multi-stage
```

**⇒ 关键纪律**：**`not-any` 才是"表示能力不足"的证据。** 只要 `semantic_exact` 能找到，
就**不得**下"换个更好的模型"这个结论（FR-003 的用意）。

---

## 一条记录算"可判读"的三个条件

1. **四条线都填了**（缺一条 ⇒ 无法定位）
2. **`evidence` 里写清了判"丢了"的依据**（不接受只写 `lost_at` 而不写为什么）
3. **`rank` 给了正确条文的最好名次** —— 这是判"是不是排得太靠后"的唯一依据

---

## 汇总表（实现阶段的产出）

按 `lost_at` 归并，得到**一页结论**：

| lost_at | 题数 | 占比 | ⇒ 下一步动哪 |
|---|---|---|---|
| `ann-only` | ? | ? | 索引参数 |
| `fusion-only` | ? | ? | 融合策略 |
| `multi-stage` | ? | ? | 最先丢的那一环 |
| `not-any` | ? | ? | 表示能力 |

**⇒ 再按 E1 的子集切一遍**（短条款 / 零重合 / 带标准号 / 普通），看是不是集中在某一类上。
