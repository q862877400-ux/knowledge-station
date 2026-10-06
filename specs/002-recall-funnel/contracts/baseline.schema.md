# 契约：基线快照格式

**Feature**: 002-recall-funnel | **Dir**: `eval/recall-funnel/baseline-v0/`

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
| `by_channel` | **四条测量线**（按字 / 语义精确 / 语义近似 / 合并后）各自命中率 |
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
