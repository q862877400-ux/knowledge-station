# retrieval（检索）

**位置**：`src/core/retrieval/`
**一句话**：把用户的问句变成一组候选条款，并按该排在前面的顺序排出来。

## 职责

**从问句到"能给答案用的候选原文"**，是产品三条总判据（换词可对 / 排得上去 / 换资料类型不塌）的
**执行层**。它接手的是**已经切好的条款**，交付的是**排好序的候选与它们的原文位置**。

**它不负责**：切条款（那是 `ingestion`）、存条款（`storage`）、判断合不合规（`compliance`）、
把结果讲成答案（`llm` + `api`）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 六路混合检索 + RRF 融合 | `hybrid_engine.py` | `api`（问答端点）、`compliance` |
| 术语桥（翻译层第一版） | `term_bridge.py` | `hybrid_engine` |
| 本地向量化 | `embedder.py`（fastembed `bge-small-zh-v1.5`，CPU/ONNX） | `hybrid_engine` |
| 重排阶段 | `reranker.py`（六路 RRF 融合后 top-N → rerank → top-K） | `hybrid_engine` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage`（`clause_repo` / `sqlite_db`） | 上游模块 | 取条款与 `clause_fts` / `clause_vec` |
| fastembed + ONNX | 外部库 | 本地向量化，**不联网** |
| jieba | 外部库 | 中文切词 |

## 明确不做什么

- **不做条款切分**：输入假定已是条款粒度。段落切分与坐标提取由 `ingestion` 负责。
- **不做合规判断**：检索出候选就交差；"该不该管这次提问"由 `compliance` 决定。
- **不生成答案**：不给结论、不做推理。那是 `llm` + `api` 的事。
- **不做数值/条款号核对**：核验在 `verification`。检索只管"找得到排得上"，不管"对不对"。
- **不做渠道巡检**：那是 `update`。

## 关键数据

| 表/对象 | 关键字段 | 说明 |
|---|---|---|
| `clause_fts` | 全文索引 | 词面路 |
| `clause_vec` | 向量（`sqlite-vec`） | 语义路；**暴力扫，与条数线性** |

## 改了它会影响谁

- **`api` 的问答端点**：候选质量直接决定答案质量
- **`compliance`**：合规触发后的取证依赖它
- **门禁的检索质量基线**：改检索 MUST 重跑 Golden Set（`eval/golden/`）

## 已知边界（诚实）

- **语义路代价与收益已实测**：在问答场景**贡献≈0**，却每次付 ~0.6 秒
  （来源：`docs/NEXT-DEV-PLAN-2026-09-28.md`）。
  ⚠ **但它同时是 P1/P2 唯一在用的语义路**，在 P2 出结论前**不能关**。
- **`sqlite-vec` 是暴力扫**（官方自述 brute-force only），**随条数线性**。
  **换索引是另一个战场**，已登记未做。
