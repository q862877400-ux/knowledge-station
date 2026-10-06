# 契约：基线快照格式

**Feature**: 002-recall-funnel | **Dir（原定）**: `eval/recall-funnel/baseline-v0/`

> **⚠ 2026-10-06 更正（原定目录从未落地）**
>
> `baseline-v0/` 三件套**一个都没建**。等价内容实际落在三处：
>
> | 原定文件 | 实际落在哪 |
> |---|---|
> | `config.json` | **`eval/recall-funnel/config-inventory.md`**（散文式盘点，不是 JSON） |
> | `results.jsonl` | **`eval/recall-funnel/funnel-per-query.jsonl`**（171 条逐条名次） |
> | `metrics.json` | **`eval/recall-funnel/funnel-summary.json`**（含 `same_budget` / `prod_caps` 两个口径与分母） |
>
> **⇒ 本契约保留为"下次建基线时的格式要求"**；本次是**未按此格式建基线**，不是"按此格式建过"。
> 另：下面示例里的 `"rerank": {"enabled": true, "model": "BAAI/bge-reranker-v2-m3"}` **与代码不符** ——
> `reranker.py` 的常量是 `BAAI/bge-reranker-base`（文件头注释写的是 v2-m3，代码不是）。
> **照代码为准**，这条不一致已登记在 `config-inventory.md` §三。
>
> **实际冻结的配置**（供当基线用，逐项有出处）：见 `config-inventory.md` 全文；
> 代码版本 = 本轮快照 `step-240` / `step-241` 对应的提交。

**三件套**：`config.json` / `metrics.json` / `results.jsonl`
**字段定义**见 [data-model.md](../data-model.md) E2。**本文定"两份快照什么时候算同一套配置"。**

---

## config.json 的必需字段

```json
{
  "captured_at": "2026-10-06T...",
  "embedding_model": "bge-small-zh-v1.5",
  "embedding_dim": 512,
  "has_lexical_channel": true,
  "vector_index": "sqlite-vec v0.1.9",
  "channels": {"A": true, "B": true, "C": true, "D": true, "E": true, "F": true},
  "top_k": 5,
  "rerank": {"enabled": true, "model": "BAAI/bge-reranker-v2-m3"},
  "machine": {"cpu": "i7-14700KF", "cores": 20, "ram_gb": 63.8, "gpu": "RTX 4080 SUPER"},
  "corpus_size": 522021,
  "code_revision": {"head": "<短哈希>", "dirty": false}
}
```

**⇒ `code_revision.dirty = true` 的快照【不得】当作基线** —— 那样别人无法复现。

---

## metrics.json 的必需字段

| 字段 | 说明 |
|---|---|
| `run_id` | 本次运行的标识 |
| `n_total` / `n_used` | 总题数 / 实际计入（**排除库外答案后**） |
| `by_cutoff` | `{"20":…, "100":…, "1000":…, "<更靠后>":…}` |
| `by_channel` | **各召回通道**（A `exact` / B `fts` / C `vec` / D `modality` / E `legal_element` / F `behavior_scope`）+ `fused`，各自命中率。**⚠ 2026-10-06 更正**：原写「四条测量线（按字 / 语义精确 / 语义近似 / 合并后）」—— 本仓无近似索引，"语义精确/近似"是同一条 |
| `by_subset` | 每个子集分别算，**结构同 `by_cutoff`** |
| `denominators` | **每个数字的分母**（本仓既有数字的教训：报数必须带分母） |

---

## results.jsonl 的要求

**每条问题一行**，包含足以复现该题在四条测量线上结果的最小信息（至少：正确答案在各路的**最好名次**）。

**⇒ 验"两次跑是否一致"靠它**：同一配置跑两次，`results.jsonl` 应逐字节相同（或按规范化后相同）。

---

## 三条硬规则

1. **报数必须带分母**（本仓既有教训：分母不同的数字不可比）。
2. **口径变了就换目录名**（`baseline-v0` → `baseline-v1`），**不得原地覆盖**。
3. **同一配置两次跑不一致 ⇒ 先查环境，不当作"结果波动"接受**（SC-002）。
