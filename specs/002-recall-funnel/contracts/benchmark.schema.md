# 契约：基准题文件格式

**Feature**: 002-recall-funnel | **File**: `eval/recall-funnel/benchmark-v2.jsonl`

> **⚠ 2026-10-06 更正（原定名 vs 实际产物，以及**一条实质未满足项**）**
>
> **原写文件名**：`eval/recall-funnel/benchmark.jsonl`。**实际产物是 `benchmark-v2.jsonl`**
> （来源：`eval/reverse-benchmark/benchmark-171.jsonl` 的轻清洗）。**以实际名为准。**
>
> **🔴 字段与本契约第二条第 2 款不符（不许含糊过去）**：
> 本契约要求 `confirmed_by` **必须是人**（"不得用自动生成的答案…自动答案会让整份诊断失效"）。
> **实际这批 171 条的 gold 不是人工确认的** —— 它是
> **"从条文反推问法"生成 + 另一个模型盲判 3 次取多数**（见 `eval/reverse-benchmark/README.md`）。
> ⇒ **FR-004 / SC-003（"150～200 条且每条答案经人工确认"）在本批上【未满足】**。
> 它带来的已知偏差（循环论证、使召回率虚高）已写进
> `eval/recall-funnel/REPORT.md` §八 第 1 条。**使用本基准时 MUST 连带引用那条限制。**
>
> **实际字段**（与下面示例的差异）：`i`（批次内唯一序号，代替 `qid`）、`query`、`kind`（定义/要求）、
> `register`、`gold_std` + `gold_clause`（代替 `gold_clause_ids`）、`gold_text`、`confidence`、`votes`、
> `overlap`，以及清洗时加的 `v2.{bucket,flags,flag_detail,gold_cr_id,gold_doc_id}`。

---

## 一行长什么样（**原定契约，留痕**）

```json
{"qid":"q001","query":"敲击仪表外壳指针晃动超过半小格允许出厂吗？","gold_clause_ids":["clrev_01M..."],"gold_notes":"轻敲位移的限值条款","subsets":["short-clause"],"answer_out_of_corpus":false,"source":"lay-phrasing","confirmed_by":"业主","confirmed_at":"2026-10-06"}
```

---

## 读取方可以依赖的五条

1. **`qid` 唯一且稳定**。重跑、补题都不得改动已有 `qid`。
2. **`query` 是原话**。任何工具 MUST NOT 在读取时改写它。
3. **`answer_out_of_corpus = true` 的题，`gold_clause_ids` 允许为空**；其余题**必定非空**。
4. **`subsets` 至少有一项**（无特殊标签时为 `["plain"]`）。
5. **`gold_clause_ids` 里的每个 id 都能在真库查到** —— 这是**入库前必须验的门**，不是读取时的假设。

---

## 写入方必须守的三条

1. **不得手抄 id**。gold 的 id MUST 从库里程序化取出（本仓有"手抄 77 行错 2 处"的实测）。
2. **不得用自动生成的答案**。`confirmed_by` 必须是人。**这是本规格的核心约束 —— 自动答案会让整份诊断失效。**
3. **一题多答案时全部列出**。只列一条会让"系统找到了另一条"被判失败，**系统性低估命中率**。

---

## 校验（实现阶段要有脚本）

| 检查 | 失败意味着 |
|---|---|
| `qid` 唯一 | 后面所有按 qid 的关联都会错位 |
| `gold_clause_ids` 可查询 | 标注时抄错了，或库已变 |
| `subsets` 非空且取值合法 | 切片统计会漏掉这些题 |
| `query` 与原始来源逐字一致 | 有人改写过提问，口径被污染 |
