# Quickstart：跑通召回漏斗

> **⚠ 这份是给【动手实现的人】看的验证清单，不是给业主看的。**
> **业主版本（大白话，说清"这个计划要干什么、怎么算做成"）→ [读我-大白话版.md](读我-大白话版.md)**
> **涉及需要业主拍板的地方，一律以那份为准。**

**Feature**: 002-recall-funnel | **Date**: 2026-10-06

> **这是一份"怎么证明它通了"的验证指南**，不是实现说明。
> 格式契约见 [contracts/](contracts/)；字段定义见 [data-model.md](data-model.md)。

---

## 前置条件

| 项 | 要求 | 怎么确认 |
|---|---|---|
| 真库可读 | `knowledge.db` 存在且能只读打开 | `sqlite3` 用 `mode=ro` 打开不报错 |
| 代码干净 | **git 工作区没有未提交改动** | `git status --short` 为空 |
| 基准文件 | `eval/recall-funnel/benchmark-v2.jsonl` 存在，且过了校验 | 见下 V1 |
| 语料规模 | 与基线一致（实测 522,021） | 数一遍 `clause_revision` |

> **⚠ 2026-10-06 更正（文件名）**：原写的是 `eval/recall-funnel/benchmark.jsonl`。
> 实际产出是 `benchmark-v2.jsonl`（考卷来自 `eval/reverse-benchmark/benchmark-171.jsonl` 的轻清洗）。
> **以实际名为准** —— 原定名从未落地。

---

## V1：基准文件合格（**不跑检索，秒级**）

**做什么**：按 [contracts/benchmark.schema.md](contracts/benchmark.schema.md) 的四条检查走一遍。

**期望**：

```
qid 唯一            ✅   → 实际产物用 i（批次内唯一序号）；实测 171 条无重复
gold_clause_ids 全部可查  ✅   → 实测 171/171 全部可查，0 条对不上、0 条命中多行
subsets 非空且取值合法    ✅   → 实际是 flags（gold_multi_def / gold_dup_text / has_subclauses）
query 与原始来源逐字一致  ✅
```

**⇒ 这一条不过，后面全部无意义。**

---

## V2：漏斗在 20 条上跑通（**第一次真跑**）

**做什么**：拿基准的前 20 条，跑**六条通道 + 融合后**，产出 `funnel-per-query.jsonl`。

> **⚠ 2026-10-06 更正**：原写「四条测量线…产出 `funnel.jsonl`」。
> 实测**不存在"精确 vs 近似"两条线**（本仓无近似索引，见 [contracts/funnel.schema.md](contracts/funnel.schema.md)），
> 实际是**六条通道各自取前 d 条 + 融合后**；文件名实际为 `funnel-per-query.jsonl`。

**期望**：

1. **20 条每条都有一行**，且**每条通道都填了** `n` / `gold_rank` / `fires`（缺一条就是没跑通）
2. **未触发（`fires=false`）与"触发了但没命中"（`fires=true, gold_rank=null`）分得开**
3. **能按 `lost_at` 归并出一张三类的表**（`not-any` / `truncated` / `fusion-only`，另加 `multi-stage` 兜底）
4. **自带一致性校验**：每条问法当场把"通道副本"与生产 `perform_hybrid_search(单通道)` 的前 20 逐个比，
   写进 `replica_check`（不一致 ⇒ 仪器坏了，结论作废）
   ⚠ **覆盖面**：只覆盖 A/B/C/D 四路、只比前 20；**深读名次不在这层自检里**（另抽验）。

**⇒ 这一步【不改任何检索代码】**（FR-016）。各角度全部是对已有能力的**分别调用**。

**✅ 已解决的已知风险**：原写「`semantic_exact`（不经近似索引）本仓能不能单独触发还没确认」。
**回答：本仓没有近似索引路径 ⇒ 这条线不存在，不需要单独触发。**
（"若做不到就写明做不到，不得用近似的数冒充"这条纪律**已无对象**，但保留在此以示留痕。）

---

## V3：两次跑一致（**SC-002 的验收**）

**做什么**：同一配置、同一批 20 条，连跑两次，比对 `results.jsonl`。

**期望**：**逐条一致。** 不一致 ⇒ **先查环境**（并发、缓存、随机种子），
**不得当作"结果波动"接受**。

---

## V4：按子集切片（**SC-001 的前置**）

**做什么**：按 `subsets` 把 20 条切成 短条款 / 零重合 / 带标准号 / 普通。

**期望**：每类都能单独出数，**且每个数都带分母**（本仓既有教训）。

---

## V5：漏斗结论可判读（**本计划的交付物**）

**做什么**：看 V2 的汇总表。

**期望**：**能明确说出三档结论之一**（`not-any` / `truncated` / `fusion-only`，另加 `multi-stage` 兜底），
**而不是"好像哪都不行"**。

**⚠ 判读纪律**（写在 funnel 契约里，此处再强调）：

> **`not-any` 只说明"排到了 1000 名以外"，不等于"模型不认识这个意思"** ——
> 要区分这两件事需要另一把尺子，本口径给不出来，**MUST 如实这么写**。
> **`truncated`（前 1000 名里有、前 20 名里没有）是"改上限就能拿回来"的一类，不许与"够不着"混为一谈。**

**⚠ 2026-10-06 更正**：原纪律句是「只要 `semantic_exact` 能找到，就不得下"换个更好的模型"这个结论」——
它依赖一条**不存在的线**（本仓无近似索引），已作废。

---

## V6：一次改进实验（**只在 V5 之后做**）

**做什么**：**只改一处**，重跑同一批，对照**开跑前就写好的**止损线。

**期望**：
1. `changed` 只有一项，其余逐项冻结且可核对（FR-013）
2. `stop_loss` 在跑之前已写入（**跑完再补无效**）
3. `verdict` 能从前后数字直接读出（不接受"感觉变好了"）

---

## 跑完之后该有什么

**实际产出**（2026-10-06 阶段 0 体检已完成，逐项可点）：

```text
eval/recall-funnel/
├── benchmark-v2.jsonl        # V1（171 条轻清洗；主结果 120 条）
├── benchmark-v2-stats.json   # V1 的统计（唯一条款 79 / 唯一文档 72 / 票型 / 移出原因）
├── config-inventory.md       # FR-001 的配置盘点（含"无 ANN"的实测证据）
├── funnel-per-query.jsonl    # V2（核心产物，171 条逐条名次 + replica_check）
├── funnel-summary.json       # V5 的汇总表（含 same_budget / prod_caps 两个口径）
├── failure-samples.jsonl     # 六路前 1000 名都没命中的 50 条留证
├── lexical-overlap.json      # 字面重合率（132/171 零重合）
├── query-preprocess.json     # 生产实际喂给通道的查询串（13 条与原始问法不同）
├── determinism.json          # V3（抽 12 条跑两遍一致）
├── rerun-consistency.json    # V3 加强（全量 171 条重跑对照，0 处差异）
├── REPORT.md                 # ★ 结论报告（A 考卷 / B 六路 / C 并集漏斗 / D 贡献 / E 失败样本 / F 配置）
├── README.md                 # 口径说明与复跑方法（一个事实一个归属层）
└── *.py                      # 6 个可复跑脚本
```

> **⚠ 2026-10-06 更正（原定 vs 实际）**：原计划树写的是
> `benchmark.jsonl` / `baseline-v0/{config,metrics,results}` / `funnel.jsonl` / `exp-1-<改动名>/`。
> **实际一个都没落地成那个名字**。差异与原因：
> 1. 基准来自 `eval/reverse-benchmark/` 的现成考卷（**不是**自建的"人工确认"基准）⇒ 叫 `benchmark-v2`；
> 2. 基线没有拆成 `baseline-v0/` 三件套，而是**并入 `funnel-per-query.jsonl` + `config-inventory.md`**
>    （配置与逐条结果都在，只是没按原定的三个文件切）；
> 3. `funnel.jsonl` → `funnel-per-query.jsonl`；
> 4. `exp-1-<改动名>/` **完全没有**（改进实验一步都没跑，见 [tasks.md](tasks.md)）。

---

## 三条最容易走歪的地方（写在最显眼处）

1. **拿旧数字当基线** —— 它们的**分母不一致**，且最关键那个（41.6%）**所依赖的条件已作废**
   （见 [research.md](research.md) R1/R2）。**必须自建口径统一的基准。**
2. **把"精确 vs 近似"当成关键分界线** —— **本仓没有近似索引**（`vec0` 暴力精确扫描），
   这条线不存在；原纪律句「`semantic_exact` 能找到就不得换模型」**已作废**。
   更正后该防的是另一件事：**把 `truncated`（截断）说成 `not-any`（够不着）** ——
   前者改上限就能拿回来，与模型无关。**⚠ 2026-10-06 更正。**
3. **盲跑** —— 本仓实测过"只看进度条、不看成功数，白跑半小时"。
   **任何批量跑 MUST 先跑 1 条校验成功再发车。**
