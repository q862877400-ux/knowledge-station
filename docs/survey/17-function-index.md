# 函数索引（每个符号的职责与引用计数）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

`purpose` = 该函数的 **docstring 第一句**（跳过 `#` 标题行，按 `。`/`；`/换行切，上限 140 字）。**没有 docstring 的函数 purpose 为空** —— 这是记录，不是评价。

`text_hits` = 该名字在扫描面内**全部 `.py` 文本**里出现几次（含定义行）。**这是下界，不是调用图**（getattr / 装饰器注册 / 字符串派发 / pytest 按名收集都看不见）。

## 二、总账

| 项 | 数 |
|---|---:|
| 模块 | 1,271 |
| 符号 | **7,025** |
| 类 | 386 |
| 函数（含方法） | 6,639 |
| 有 docstring | 3,712 |
| 没有 docstring | 3,313 |

## 三、按模块列全部符号

### `eval/bunny-benchmark/run-batch.py`（4 个符号）

> 批量调 bunny 判定 150 条候选：每条独立跑 3 次，收结论。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `call` 函数 | 76 | 17 | — |
| `verdict` 函数 | 95 | 343 | — |
| `one` 函数 | 104 | 57 | — |
| `main` 函数 | 119 | 1131 | — |

### `eval/golden/build_golden.py`（3 个符号）

> Golden Set 构建器（Task 10.1）：从当前知识库抽取/合成问题-答案对，冻结落盘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_real_clauses` 函数 | 21 | 2 | — |
| `build` 函数 | 33 | 80 | — |
| `main` 函数 | 109 | 1131 | — |

### `eval/govqa-label-review/build-review.py`（1 个符号）

> 造「gov-qa 标签复核包」（spec 005 T501 收口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 55 | 1131 | — |

### `eval/lay-phrasing/analyze-gen.py`（5 个符号）

> 分析业主给的两批生成结果（V2 完整 500 / V1 半批 85）+ 上一轮 v1 提示词的旧数据。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 45 | 103 | — |
| `texts_of` 函数 | 60 | 9 | 兼容两种格式：老格式 lay=\["说法"\]。 |
| `has_qmark` 函数 | 71 | 2 | — |
| `subs2` 函数 | 75 | 11 | — |
| `main` 函数 | 79 | 1131 | — |

### `eval/lay-phrasing/bridge-ceiling.py`（2 个符号）

> P1 的关键分岔：库内料够不够，还是必须靠外部百科？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 36 | 90 | — |
| `main` 函数 | 40 | 1131 | — |

### `eval/lay-phrasing/check-lay-50.py`（2 个符号）

> 核验业主给的大白话生成结果 + 量它到底能不能搜到库里的术语定义。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `substrings` 函数 | 37 | 2 | — |
| `main` 函数 | 41 | 1131 | — |

### `eval/lay-phrasing/cooccur-bridge.py`（2 个符号）

> P1 第一刀 · 可行性：**只用库内共现**能不能把大白话接到术语上？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 41 | 90 | — |
| `main` 函数 | 45 | 1131 | — |

### `eval/lay-phrasing/decompose-lay.py`（2 个符号）

> 说法级分解：把"没东西可对"（零字面重合）与"有东西但对不上/排不上"分开。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `subs2` 函数 | 31 | 11 | — |
| `main` 函数 | 35 | 1131 | — |

### `eval/lay-phrasing/gen-lay.py`（5 个符号）

> 用 v2 提示词生成「外行说法」，调 bunny（space-bunny-free）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `extract_prompt` 函数 | 40 | 2 | 从 md 的 ``` 代码块里取出提示词全文（整段复制，末尾接术语清单）。 |
| `call` 函数 | 53 | 17 | — |
| `parse` 函数 | 69 | 119 | 每行一个 JSON 对象。 |
| `one` 函数 | 85 | 57 | — |
| `main` 函数 | 100 | 1131 | — |

### `eval/lay-phrasing/p1-end-to-end.py`（2 个符号）

> P1 端到端：把"语义选出术语"接进检索，到底涨不涨。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 38 | 90 | — |
| `main` 函数 | 42 | 1131 | — |

### `eval/lay-phrasing/p1-fanout-curve.py`（3 个符号）

> P1：扇出宽度的曲线（质量 vs 延迟），并试一种更合理的合并顺序。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 40 | 90 | — |
| `interleave` 函数 | 44 | 6 | 轮转交错合并 + 去重。 |
| `main` 函数 | 55 | 1131 | — |

### `eval/lay-phrasing/p1-literal-baseline.py`（3 个符号）

> P1·改后做法的下限：**纯字面**能不能从 500 个术语里挑对那一个？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 26 | 90 | — |
| `subs2` 函数 | 30 | 11 | — |
| `main` 函数 | 34 | 1131 | — |

### `eval/lay-phrasing/p1-selection-strategies.py`（2 个符号）

> P1 下一刀：攻"选中术语"这一步（当前瓶颈，top-1 仅 16.4%）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 39 | 90 | — |
| `main` 函数 | 43 | 1131 | — |

### `eval/lay-phrasing/p1-semantic-baseline.py`（2 个符号）

> P1 语义基线：把大白话和 500 个术语用**生产同款嵌入模型**比，选得对不对。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 27 | 90 | — |
| `main` 函数 | 31 | 1131 | — |

### `eval/lay-phrasing/p1-semantic-select.py`（3 个符号）

> P1 keystone：**语义**能不能从 500 个术语里挑对那一个？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 39 | 90 | — |
| `cos` 函数 | 43 | 29 | — |
| `main` 函数 | 50 | 1131 | — |

### `eval/lay-phrasing/probe-hier-select.py`（2 个符号）

> 探针：**先选文档、再在文档内选术语**能不能把"选术语"从 8.6% 救回来？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 40 | 90 | — |
| `main` 函数 | 44 | 1131 | — |

### `eval/lay-phrasing/probe-nonA-criterion.py`（2 个符号）

> 探针：把"非 A 子集"的口径**算清楚**——到底是"与术语名重合"还是"与定义条款重合"？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 30 | 90 | — |
| `main` 函数 | 34 | 1131 | — |

### `eval/lay-phrasing/probe-query-instruction.py`（2 个符号）

> 探针：给**查询**加上 bge 官方建议的检索指令前缀，全库候选下的"选术语"能涨多少？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 40 | 90 | — |
| `main` 函数 | 44 | 1131 | — |

### `eval/lay-phrasing/probe-rerank-control.py`（2 个符号）

> 对照实验：同一套两段式重排，在 **A 档**（说法与定义条款**有**实词重合）上是什么结果？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 50 | 90 | — |
| `main` 函数 | 54 | 1131 | — |

### `eval/lay-phrasing/probe-rerank-two-stage.py`（2 个符号）

> 探针：用现成的 `bge-reranker-base` 做两段式，能不能救回"候选集太大"这个瓶颈？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 51 | 90 | — |
| `main` 函数 | 55 | 1131 | — |

### `eval/lay-phrasing/probe-select-rank.py`（2 个符号）

> 探针：把"选术语"这一步**单独**量出来，候选集 500 vs 42,181 各一次。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 41 | 90 | — |
| `main` 函数 | 45 | 1131 | — |

### `eval/lay-phrasing/probe-topk-equivalence.py`（1 个符号）

> 探针：`topk_by_cos` 的 numpy 路径与纯 Python 参照实现，**在真数据上**是否给同一个答案。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `eval/lay-phrasing/repro-endtoend.py`（3 个符号）

> 独立复现另一个 AI 的"P1 端到端：翻译臂前20 3.6% → 16.2%（4.53×）"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 41 | 90 | — |
| `cos` 函数 | 45 | 29 | — |
| `main` 函数 | 52 | 1131 | — |

### `eval/lay-phrasing/repro-fanout.py`（3 个符号）

> 复核另一个 AI 的扇出结论（它没提交、卡在"等第五批复核"上）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 38 | 90 | — |
| `cos` 函数 | 42 | 29 | — |
| `main` 函数 | 49 | 1131 | — |

### `eval/lay-phrasing/two-stage-lean.py`（1 个符号）

> 两段式策略的**轻量版**：抽样 200 个术语，只测 D ∈ {1,3}。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 42 | 1131 | — |

### `eval/lay-phrasing/two-stage.py`（1 个符号）

> 验证「先找对文档、再在文档内定位」这条策略到底成不成。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 36 | 1131 | — |

### `eval/lay-phrasing/validate-gen.py`（1 个符号）

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 4 | 103 | — |

### `eval/real-question-ruler/build.py`（7 个符号）

> 造「真人问答召回尺子」（spec 010）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_official` 函数 | 56 | 4 | — |
| `is_complaint` 函数 | 83 | 3 | — |
| `load_lib` 函数 | 87 | 8 | 标准名 → 标准号（**复用官方 load_lib**，口径不分叉）。 |
| `load_doc_ids` 函数 | 92 | 2 | 标准名（norm 后）→ doc_id，供尺子记录 gold_doc_id。 |
| `doc_text_index` 函数 | 103 | 2 | doc_id → 该文档全部条款正文（拼接，用于"零重合"判据）。 |
| `_bigrams` 函数 | 124 | 4 | 字符二元组（"≥2 字公共子串"的可算近似：有公共二元组 ⇔ 有长度 ≥2 的公共子串）。 |
| `main` 函数 | 130 | 1131 | — |

### `eval/real-question-ruler/verify.py`（2 个符号）

> 独立复算「真人问答召回尺子」（spec 010 T002）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_official` 函数 | 51 | 4 | — |
| `main` 函数 | 59 | 1131 | — |

### `eval/recall-funnel/baseline-v0/build-baseline.py`（5 个符号）

> build-baseline.py —— 把「阶段 0 基线」从既有产物**投影**成契约要求的 `baseline-v0/` 三件套（T023）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_git` 函数 | 83 | 3 | — |
| `build_config` 函数 | 88 | 2 | — |
| `build_metrics` 函数 | 111 | 2 | — |
| `build_results` 函数 | 165 | 2 | — |
| `main` 函数 | 200 | 1131 | — |

### `eval/recall-funnel/build-v2.py`（4 个符号）

> benchmark-v2 构建器：对 `benchmark-171.jsonl` 做**轻清洗**（不重新生成问题、不重判）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ro_conn` 函数 | 39 | 19 | — |
| `_like_escape` 函数 | 47 | 3 | — |
| `head_term` 函数 | 51 | 2 | 定义形态条文的**术语名**：条文正文第二行「术语名 英文名 定义…」的第一个词。 |
| `main` 函数 | 63 | 1131 | — |

### `eval/recall-funnel/clean-v3/01-build-input.py`（1 个符号）

> 清洗 v3 · 步骤 1：**冻结凭证** + 构造**盲输入**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/clean-v3/02-build-bucket-input.py`（1 个符号）

> 清洗 v3 · 步骤 2：构造**失败题四桶盲分**的输入。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/clean-v3/03-merge-tiers.py`（1 个符号）

> 清洗 v3 · 步骤 3：**验收并合并盲分档结果**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 48 | 1131 | — |

### `eval/recall-funnel/clean-v3/04-rescore-by-stratum.py`（1 个符号）

> 清洗 v3 · 步骤 4：用清洗后的金标给 E1 **重打分**（分层汇报，只当探索）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/clean-v3/05-merge-buckets.py`（1 个符号）

> 清洗 v3 · 步骤 5：**验收并合并失败题四桶**，并与其它盲判结果交叉核对。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `eval/recall-funnel/clean-v3/06-build-second-pass.py`（1 个符号）

> 清洗 v3 · 步骤 6：**生成人工二审表**（外部要求：盲模型初分 → 人二审）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 35 | 1131 | — |

### `eval/recall-funnel/clean-v3/07-build-ai-review.py`（1 个符号）

> AI 复核包（**分两半**：事实 / 语言）—— 替代原计划的 40 条人工抽查。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/clean-v3/08-apply-ai-review.py`（2 个符号）

> 08-apply-ai-review.py —— 把「AI 复核」的逐条判定落成机器可读产物（T015 的收口件）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 150 | 125 | — |
| `main` 函数 | 154 | 1131 | — |

### `eval/recall-funnel/determinism.py`（1 个符号）

> 确定性检查：同一套设置跑两次，结果必须逐字一样。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/01-copy-db.py`（1 个符号）

> E1 步骤 1：把真库复制成实验副本（**真库全程只读，绝不覆盖它的 clause_vec**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/02-build-text.py`（3 个符号）

> E1 步骤 2：在副本里生成**实验臂送进模型的那段文本**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `table_of` 函数 | 39 | 2 | — |
| `build_text` 函数 | 43 | 2 | 按变体把四个字段拼成实验臂的输入文本。 |
| `main` 函数 | 59 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/02b-align-arms.py`（1 个符号）

> E1 步骤 2b：**把两个臂的候选集合对齐**（这是止损线里写死的 hard_fail 前置）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/03-embed.py`（2 个符号）

> E1 步骤 3：为实验臂算向量，写进副本的 `clause_vec_ctx`（**断点续跑**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `tables_of` 函数 | 36 | 2 | → (文本表, 向量表)。 |
| `main` 函数 | 43 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/04-ab-eval.py`（5 个符号）

> E1 步骤 4：A/B 对照（**两个臂都在同一份副本上**，语料完全冻结）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `conn_ro` 函数 | 29 | 2 | — |
| `knn` 函数 | 37 | 15 | — |
| `rank_of` 函数 | 45 | 33 | — |
| `rate` 函数 | 52 | 76 | — |
| `main` 函数 | 56 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/04a-control-check.py`（1 个符号）

> E1 步骤 4a：**对照臂自检** —— 在副本上量一次，看能不能复现已知基线。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/05-human-check.py`（1 个符号）

> E1 配套：生成**人工抽查清单**（外部评估要的"质量闸门"，30~50 条）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/06-verdict.py`（4 个符号）

> E1 步骤 6：按**预登记的阈值**机械出判决（FR-014）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `set_check` 函数 | 33 | 2 | **真集合比较**（独立复核 F5）：两臂的 `clause_revision_id` 集合是否完全一致。 |
| `binom_two_sided` 函数 | 64 | 14 | 精确二项检验（p=0.5）双侧 p 值 —— 配对比较就该用它，不该只看百分点。 |
| `min_detectable` 函数 | 73 | 6 | n 对不一致时，达到双侧 p<0.05 所需的净差条数。 |
| `main` 函数 | 87 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/07-wait-and-run.py`（3 个符号）

> E1 步骤 7：**守候并自动出结论** —— 等 `clause_vec_ctx` 齐了就跑 A/B + 判决。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `count` 函数 | 27 | 280 | 读一次行数。 |
| `_target` 函数 | 40 | 2 | — |
| `main` 函数 | 48 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/08-mechanism-diagnostic.py`（1 个符号）

> E1 机制诊断 v2（可复跑）：换文本后，模型是不是更"认文档"、更不"认条文"？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/09-analyze-ab.py`（2 个符号）

> E1 结果拆解：把 `ab-result.json` 拆成"能挂回具体数据"的几块。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `rate` 函数 | 23 | 76 | — |
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/10-significance.py`（3 个符号）

> E1 显著性复核：**这个实验到底能分辨多大的效果**？观测到的差异是不是噪声？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `binom_two_sided` 函数 | 23 | 14 | 精确二项检验（p=0.5）双侧 p 值。 |
| `min_detectable` 函数 | 33 | 6 | n 对不一致时，达到双侧 p<0.05 所需的**净差**。 |
| `main` 函数 | 47 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/11-boilerplate-share.py`（1 个符号）

> 样板占比（可复算版）：上下文占了送进模型的文本多大比例？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 38 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/12-split-diagnostic.py`（1 个符号）

> E1 复核补算 ②：**拆分诊断** —— 金标所在文档被找到了吗？找到后金标在文档内排第几？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/13-cluster-significance.py`（1 个符号）

> E1 复核补算 ①：**簇级**显著性 —— 按"独立条文"重做配对检验与分辨力。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 29 | 1131 | — |

### `eval/recall-funnel/exp-1-contextual/14-power-factcheck.py`（3 个符号）

> 事实核查：检验外部评估关于"分辨力 / 样本量"的两个说法，用我们自己的实测分布重算。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `phi` 函数 | 30 | 3 | — |
| `power` 函数 | 34 | 9 | 真实效应 delta、差值标准误 se 时，双尾 α 检验的把握度（正态近似）。 |
| `main` 函数 | 39 | 1131 | — |

### `eval/recall-funnel/exp-10-p4-feasibility/probe-jev-region.py`（1 个符号）

> P4 可行性实测：Jev（TypeSafe System One）在本机到底能不能用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `rec` 函数 | 53 | 775 | — |

### `eval/recall-funnel/exp-11-rerank-fix/measure-rerank-ab.py`（5 个符号）

> 总纲 P0·0.7 修复前后 A/B：rerank 阶段到底改不改 top-8（只读真库）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ro_conn` 函数 | 58 | 19 | — |
| `load_items` 函数 | 67 | 2 | — |
| `is_headline` 函数 | 71 | 2 | — |
| `mcnemar` 函数 | 76 | 2 | 配对 McNemar 精确检验（双侧）—— b = 翻进（A 不中 B 中）、c = 翻出。 |
| `main` 函数 | 88 | 1131 | — |

### `eval/recall-funnel/exp-12-long-clause-tail/cos-verify.py`（2 个符号）

> P0·0.10 机制复验：尾巴到底进没进向量（余弦）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `cos` 函数 | 41 | 29 | — |
| `main` 函数 | 48 | 1131 | — |

### `eval/recall-funnel/exp-12-long-clause-tail/measure.py`（6 个符号）

> P0·0.10 只读量化：长条款的尾巴到底漏了什么、影响面多大。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_tokenizer` 函数 | 67 | 2 | 真实 bge-small-zh-v1.5 分词器（本地 HF snapshot，零网络）。 |
| `_tokens` 函数 | 77 | 10 | 生产分词器（与 `clause_fts` 建索引口径同源）。 |
| `split_head_tail` 函数 | 85 | 5 | 按**字符**切 head/tail —— 与 `clause_repo.py` 的 `content_text\[:512\]` 同口径。 |
| `tail_only_words` 函数 | 90 | 4 | tail 里"head+title 完全没出现过"的词集（= 向量路看不到、FTS 看得到的那批）。 |
| `token_drop_partition` 函数 | 97 | 9 | 把"被丢掉的 token"拆成两段：`(gain, residual)`。 |
| `main` 函数 | 111 | 1131 | — |

### `eval/recall-funnel/exp-12-long-clause-tail/probe-tail-blindspot.py`（2 个符号）

> P0·0.10 决定性探针：尾巴上的字面信号，向量路够不着、FTS 路够得着。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `pick_phrase` 函数 | 48 | 3 | 从 region 里挑一段 take 字中文串，要求它在 other 里**不出现**。 |
| `main` 函数 | 59 | 1131 | — |

### `eval/recall-funnel/exp-13-query-rewrite/run.py`（13 个符号）

> exp-13：**查询侧改写** A/B/C/D —— 只改查询串，索引一个字不动。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_default_tokenize` 函数 | 66 | 2 | 生产同款分词器（jieba）。 |
| `_is_cjk_word` 函数 | 72 | 2 | 只保留含中文的词（纯数字/标点/英文串不进扩展）。 |
| `arm_queries` 函数 | 77 | 10 | ★ 纯函数：四臂各自的查询串。 |
| `pick_prf_terms` 函数 | 93 | 8 | ★ 纯函数（分词器可注入）：从"伪相关集"文档里挑扩展词。 |
| `rank_of` 函数 | 123 | 33 | 名次 = **严格更优**的条数 + 1（分数越大越好）。 |
| `top_k_indices` 函数 | 128 | 4 | 取分数最高的 k 个下标（降序）。 |
| `mcnemar_exact` 函数 | 135 | 14 | ★ 配对"翻进 b / 翻出 c"的双侧精确二项 p（exp-11 同法）。 |
| `hit_rate` 函数 | 145 | 26 | ranks 里 <= thr 的比例（None = 未召回，算不中）。 |
| `median_rank` 函数 | 152 | 6 | — |
| `flip_counts` 函数 | 157 | 11 | (翻进, 翻出)：base=False→arm=True 的条数 / base=True→arm=False 的条数。 |
| `_headline` 函数 | 166 | 11 | — |
| `_fts_rank` 函数 | 174 | 2 | — |
| `main` 函数 | 196 | 1131 | — |

### `eval/recall-funnel/exp-14-fused-rewrite/determinism.py`（2 个符号）

> exp-14 的**替代仪器对照**（预注册的那条已失效，见 README §五）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 38 | 125 | — |
| `main` 函数 | 46 | 1131 | — |

### `eval/recall-funnel/exp-14-fused-rewrite/run.py`（8 个符号）

> exp-14：把 exp-13 的三条**查询侧改写**接进**完整六路融合**，量 `fused@20`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_e13` 函数 | 65 | 5 | 复用 exp-13 的**纯函数**（不重写第二套）：arm_queries / hit_rate / median_rank /。 |
| `_headline` 函数 | 75 | 11 | — |
| `arm_vec_query` 函数 | 83 | 8 | ★ 纯函数：该臂**送进向量通道**的查询串。 |
| `arm_fts_query` 函数 | 92 | 7 | ★ 纯函数：该臂**送进 FTS 通道**的查询串。 |
| `_run` 函数 | 97 | 73 | — |
| `aggregate_runs` 函数 | 184 | 22 | ★ 纯函数（单测直接喂合成台账）：从逐 `(i, arm)` 台账算聚合。 |
| `_aggregate` 函数 | 239 | 8 | — |
| `main` 函数 | 291 | 1131 | — |

### `eval/recall-funnel/exp-15-pool-depth-fusion/probe-knn-cost.py`（1 个符号）

> exp-15 代价侧小探针：把 `k` 从 20 放大到 1000，向量通道的 KNN 扫描慢多少？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `eval/recall-funnel/exp-15-pool-depth-fusion/run.py`（13 个符号）

> exp-15：深读候选的「池深 × 融合方式」二维对照 —— 深读候选到底能不能进前 20？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 91 | 125 | — |
| `_headline` 函数 | 98 | 11 | headline 120 条切片 —— 与 exp-14 / exp-8 同一判据（不重写第二套）。 |
| `take_doc_diverse` 函数 | 108 | 9 | 按「每篇文档最多 `per_doc` 条」去重后取前 `budget` 条。 |
| `build_rankings` 函数 | 129 | 9 | ★ 纯函数：该臂送进融合的**每路候选列表**。 |
| `oracle_pool` 函数 | 150 | 6 | ★ 纯函数：oracle 池 = exact ∪ modality ∪ fts\[:d\] ∪ vec\[:d\]（上界，不是可实现系统）。 |
| `_hit_rate` 函数 | 158 | 7 | — |
| `_median_rank` 函数 | 162 | 2 | — |
| `arm_rank` 函数 | 167 | 16 | ★ 纯函数：该臂在 `depth` 深度上的 gold 名次（`None` = 未命中 / 该深度无数据）。 |
| `ledger_depths` 函数 | 187 | 6 | ★ 纯函数：台账里**真的存了**哪些深度 —— 决定哪些阈值可以上报（别把没测的当 0%）。 |
| `aggregate_runs` 函数 | 202 | 22 | ★ 纯函数（单测直接喂合成台账）：从逐条台账算聚合。 |
| `_run` 函数 | 291 | 73 | — |
| `_aggregate` 函数 | 401 | 8 | — |
| `main` 函数 | 441 | 1131 | — |

### `eval/recall-funnel/exp-16-edge-expansion/run.py`（2 个符号）

> exp-16：**引用边扩边对检索有没有用**（在**修后**的图上测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `gold_ids` 函数 | 43 | 5 | 把考卷的 (standard_no, clause_number) 解析成 clause_revision_id。 |
| `main` 函数 | 63 | 1131 | — |

### `eval/recall-funnel/exp-16-edge-expansion/targeted-2hop.py`（2 个符号）

> 针对性测试 · **两跳**：A→B→C 这种"要扩两次边"的链，扩边能不能一路走通。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_id_of` 函数 | 44 | 4 | 先精确匹配 standard_name，再回退 LIKE（文档名可能带后缀/写法差异）。 |
| `main` 函数 | 57 | 1131 | — |

### `eval/recall-funnel/exp-16-edge-expansion/targeted.py`（1 个符号）

> 针对性测试：**挑一条真带连接的条款，用大白话问它，看扩边有没有把它该带的东西带进来**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-17-embedding-production-plan/rebuild-shadow.py`（12 个符号）

> exp-17 · 可续跑的「影子向量表」重建脚本（**不动生产**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `display_text` 函数 | 85 | 23 | 生产同款条文文本公式，**一字不改**。 |
| `text_formula_sha` 函数 | 95 | 19 | 把"文本公式"变成可比较的指纹（防止两种公式的向量混进同一张表）。 |
| `ckpt_guard` 函数 | 109 | 4 | 续跑口径守卫：四个字段任一不一致即**抛错**（不是警告）。 |
| `fake_vector` 函数 | 125 | 5 | 确定性假向量（sha256 派生）——只验管道，不验语义。 |
| `real_embedder_factory` 函数 | 142 | 5 | 返回 `embed(list\[str\]) -> list\[list\[float\]\]`（真模型，GPU fp16，逐字复刻 E4 口径）。 |
| `fake_embedder_factory` 函数 | 169 | 5 | — |
| `_open_shadow` 函数 | 179 | 2 | — |
| `_read_ckpt` 函数 | 196 | 2 | — |
| `_write_ckpt` 函数 | 200 | 4 | — |
| `_source_counts` 函数 | 205 | 2 | 返回 (非空正文条数, 全表条数)。 |
| `run` 函数 | 214 | 282 | 执行（或续跑）重建。 |
| `main` 函数 | 306 | 1131 | — |

### `eval/recall-funnel/exp-17-embedding-production-plan/verify-resume.py`（11 个符号）

> exp-17 · 断点续跑 / 幂等 / 口径的**验证脚本**（读数落 `result.json`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_mod` 函数 | 48 | 2 | — |
| `_rows` 函数 | 56 | 33 | — |
| `_table_digest` 函数 | 66 | 7 | — |
| `_py` 函数 | 74 | 1 | — |
| `_db_fingerprint` 函数 | 79 | 3 | — |
| `t1_resume_equals_oneshot` 函数 | 91 | 2 | — |
| `t2_real_kill` 函数 | 114 | 2 | — |
| `t3_idempotent` 函数 | 163 | 2 | — |
| `t4_real_model_bytes` 函数 | 175 | 2 | 用本脚本的嵌入函数重算 N_REAL 条，与 E4 冻结的 `clause_vec_qwen` 比对。 |
| `_fake` 函数 | 251 | 52 | — |
| `main` 函数 | 257 | 1131 | — |

### `eval/recall-funnel/exp-3-query-side/01-build-term-index.py`（1 个符号）

> E3 · 步骤 1：构建/加载**术语索引**（术语桥的离线产物）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `eval/recall-funnel/exp-3-query-side/02-copy-db.py`（1 个符号）

> E3 · 步骤 2：把真库**复制**一份给 E3 用（真库全程只读）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `eval/recall-funnel/exp-3-query-side/03-run-e3.py`（1 个符号）

> E3 · 步骤 3：**跑两臂对照**（唯一变量 = 送进检索的那串字）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 35 | 1131 | — |

### `eval/recall-funnel/exp-3-query-side/04-verdict-e3.py`（3 个符号）

> E3 · 步骤 4：**机械判决**（结论由预登记阈值算出，不许跑完看着数字"感觉一下"）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `binom_two_sided` 函数 | 34 | 14 | — |
| `min_detectable` 函数 | 42 | 6 | — |
| `main` 函数 | 50 | 1131 | — |

### `eval/recall-funnel/exp-3b-query-side-loo/01-run-e3b.py`（1 个符号）

> E3b · 跑两臂对照（**留一法**：选术语前剔除 gold 条款）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/exp-3b-query-side-loo/02-verdict-e3b.py`（3 个符号）

> E3b · 步骤 2：**机械判决**（结论由预登记阈值算出，不许跑完看着数字"感觉一下"）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `binom_two_sided` 函数 | 34 | 14 | — |
| `min_detectable` 函数 | 42 | 6 | — |
| `main` 函数 | 50 | 1131 | — |

### `eval/recall-funnel/exp-3b-query-side-loo/03-extra-endpoints.py`（2 个符号）

> E3b · 附加：给**所有终点**算簇级 bootstrap 置信区间（不只主终点）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `binom_two_sided` 函数 | 28 | 14 | — |
| `main` 函数 | 36 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/00-measure-throughput.py`（2 个符号）

> E4 · 步骤 0：**量真实吞吐**（决定全量重算值不值得做）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 29 | 1131 | — |
| `_has_table` 函数 | 121 | 2 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/01-embed-qwen.py`（3 个符号）

> E4 · 步骤 1：用 **Qwen3-Embedding-0.6B（512 维）** 重算全库条文向量（影子表）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ensure_copy` 函数 | 35 | 2 | — |
| `display_text` 函数 | 52 | 23 | **现役同款公式**（`clause_repo.insert_clauses_in_txn` 实测口径），一字不改。 |
| `main` 函数 | 57 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/01b-align-arms.py`（1 个符号）

> E4 · 步骤 1b：**把两臂的候选集合对齐**（补上我在 E4 里漏掉的 E1 前置步骤）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/01c-control-check.py`（1 个符号）

> E4 · 步骤 1c：**对照臂自检** —— 删掉那 43 条之后，基线必须仍然复现。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/02-ab-eval.py`（1 个符号）

> E4 · 步骤 2：两臂对照（唯一变量 = 嵌入模型）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 38 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/03-verdict-e4.py`（2 个符号）

> E4 · 步骤 3：**机械判决** + 全终点簇级置信区间。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `binom_two_sided` 函数 | 45 | 14 | — |
| `main` 函数 | 53 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/04-rescued.py`（1 个符号）

> E4 · 附加：**救回了多少原本"六路前 1000 都没有"的题**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/04-wait-and-run.py`（2 个符号）

> E4 · 步骤 4：**守候并自动出结论** —— 等 `clause_vec_qwen` 齐了就跑 A/B + 判决。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `count` 函数 | 31 | 280 | ⚠ 读 `vec0` 表**必须**加载 sqlite-vec 扩展（本会话已踩过四次）。 |
| `main` 函数 | 43 | 1131 | — |

### `eval/recall-funnel/exp-4-embedding-shadow/05-fidelity-probe.py`（2 个符号）

> E4 · 步骤 5：**保真探针** —— 证明"只换了模型"，没换文本。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `display_text` 函数 | 34 | 23 | **必须与 `01-embed-qwen.py` 里那一份逐字相同**（这里是它的独立副本，。 |
| `main` 函数 | 40 | 1131 | — |

### `eval/recall-funnel/exp-4b-embedding-round2/10-latency.py`（3 个符号）

> E4 第二轮 · A 臂：**提问侧成本**（单条查询延迟 / 冷启动 / 显存）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `pct` 函数 | 45 | 24 | — |
| `stat` 函数 | 53 | 139 | — |
| `main` 函数 | 64 | 1131 | — |

### `eval/recall-funnel/exp-4b-embedding-round2/11-prefix-ab.py`（1 个符号）

> E4 第二轮 · B 臂：**查询侧指令前缀 A/B**（唯一变量 = 查询串上有没有 Qwen3 官方 instruct 前缀）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-4b-embedding-round2/12-verdict.py`（3 个符号）

> E4 第二轮 · 判定：**按 `stop-loss.json` 里跑前写死的阈值机械算**，不靠看着数字感觉。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_num_of_key` 函数 | 21 | 2 | 从判据键（如 `<= 100 ms` / `>= 10pt`）里抽出数字边界。 |
| `_boundary` 函数 | 29 | 5 | 在一条 decision_rule 里找以 `prefix` 开头的档，抽它的数字边界。 |
| `main` 函数 | 37 | 1131 | — |

### `eval/recall-funnel/exp-4b-embedding-round2/13-cluster-ci.py`（1 个符号）

> E4 第二轮 · B 臂的**簇级置信区间**（与 E4 第一轮同法，便于横向比较）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `eval/recall-funnel/exp-4b-embedding-round2/14-real-db-scan.py`（2 个符号）

> E4 第二轮 · 参照物复测：现有向量路「扫描」耗时 —— **在真库上**量一次。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `scan` 函数 | 38 | 180 | — |
| `main` 函数 | 46 | 1131 | — |

### `eval/recall-funnel/exp-4c-embedding-1024/19-probe-throughput-1024.py`（2 个符号）

> E4c · 步骤 0：**1024 维**吞吐探针（真实条文抽样，GPU fp16）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `display_text` 函数 | 27 | 23 | — |
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/exp-4c-embedding-1024/20-embed-qwen-1024.py`（3 个符号）

> E4c · 步骤 1：用 **Qwen3-Embedding-0.6B（1024 维，原生全维）** 重算全库条文向量（影子表）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `pick_batch` 函数 | 31 | 2 | — |
| `display_text` 函数 | 41 | 23 | **现役同款公式**（与 exp-4 一字不差）。 |
| `main` 函数 | 46 | 1131 | — |

### `eval/recall-funnel/exp-4c-embedding-1024/21-ab-1024.py`（1 个符号）

> E4c · 步骤 2：两臂对照（**唯一变量 = 输出维度 512 → 1024**，同一个 Qwen3-Embedding-0.6B）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 42 | 1131 | — |

### `eval/recall-funnel/exp-4c-embedding-1024/22-cluster-ci.py`（1 个符号）

> E4c · 步骤 3：**簇级置信区间**（与 E4 第一轮 / E4b 第二轮同法，便于横向比较）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `eval/recall-funnel/exp-4c-embedding-1024/23-verdict.py`（2 个符号）

> E4c · 步骤 4：判定 —— **按 `stop-loss.json` 里跑前写死的阈值机械算**，不靠看着数字感觉。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_nums` 函数 | 21 | 4 | — |
| `main` 函数 | 25 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/01-probe-real-questions.py`（5 个符号）

> 真问题探针：业主给的 **11 条真实提问**，量三件事。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 65 | 1131 | — |
| `_rows` 函数 | 120 | 33 | — |
| `_knn` 函数 | 124 | 2 | — |
| `_knn_shadow` 函数 | 131 | 2 | 影子库里用 **Qwen3** 嵌入查询（与 E4 同口径：不加指令前缀）。 |
| `_describe` 函数 | 152 | 3 | — |

### `eval/recall-funnel/exp-5-real-questions/02-topic-coverage.py`（1 个符号）

> 真问题探针 · 第二步：**逐主题查库里的覆盖**（这决定"该不该再加 3 万本"）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 41 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/03-own-question-pool.py`（1 个符号）

> 查「真实提问」在本机攒了多少 —— 这是比爬部委更省的来源。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/04-trial-scrape.py`（1 个符号）

> 部委互动问答 · **20 条试采**：量三个比例，决定这个方案成不成立。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 59 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/05-probe-ministries.py`（1 个符号）

> 部委互动问答 · **入口探测**：找出每家的"问答列表"在哪。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 58 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/06-build-real-bench.py`（2 个符号）

> 部委互动问答 · **第 ② 步：把"在库"的部分做成考卷**（真问题 + 官方金标）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `cn2int` 函数 | 49 | 4 | 把「十」「二十」「三十五」「一百零二」这类中文数字转成 int。 |
| `main` 函数 | 71 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/07-hollow-clauses.py`（1 个符号）

> 查一个**真缺陷**：库里有多少条文是"空壳"（正文只有标题，没有内容）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 35 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/08-ocr-precheck.py`（1 个符号）

> OCR 前置体检：**GB / GBZ 那 1,168 本里，多少是扫描件？**

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 34 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/09-verify-law-repos.py`（1 个符号）

> 核实这几个开源法律库：**数据是不是真的拿得到**（不只看 README 的说法）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/10-where-is-data.py`（1 个符号）

> 把"数据到底在不在仓库里"**点开看** —— 逐个目录列清单，不靠 README 说法。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/11-popular-law-repos.py`（1 个符号）

> 按**星数**搜 GitHub —— 找到真正热门的中国法律法规/判决数据集项目。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 34 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/12-check-popular.py`（1 个符号）

> 核实热门法律项目**到底装了什么** —— 顶层目录、README、数据体积。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 38 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/13-chase-two.py`（1 个符号）

> 追查两个"热门且可能有全量数据"的项目：LawRefBook(2458★) 与 just-laws(781★, MIT)。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/14-fetch-lawrefbook.py`（1 个符号）

> 第 ① 步：把 LawRefBook 的法规数据**下下来**，看清结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/15-fetch-zip-retry.py`（1 个符号）

> 第 ① 步（重试版）：把 `laws.zip` 下下来 —— **三个通道轮着试**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 40 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/16-compare-lawrefbook.py`（3 个符号）

> 第 ② 步：把 LawRefBook 的 1,586 部法律 **与真库里那 386 篇法律/条例比对**，出一张"缺哪些"清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fix` 函数 | 39 | 41 | zip 内文件名被 Python 按 CP437 解出来 ⇒ 还原成原始编码。 |
| `norm` 函数 | 59 | 84 | — |
| `main` 函数 | 67 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/17-compare-strict.py`（3 个符号）

> 第 ② 步（**修正版**）：严格判据下，LawRefBook 与真库的差异。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fix` 函数 | 42 | 41 | zip 内文件名被按 CP437 解出 ⇒ 还原（原编码是 UTF-8。 |
| `norm` 函数 | 56 | 84 | — |
| `main` 函数 | 65 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/18-extract-to-standards.py`（2 个符号）

> 把 LawRefBook 的 8 MB 法规数据**解到 `D:\AI\work space\标准\法律法规`**，保持原目录结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fix` 函数 | 38 | 41 | zip 内文件名按 CP437 解的 ⇒ 还原（原编码 UTF-8）。 |
| `main` 函数 | 52 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/19-ocr-quality-check.py`（1 个符号）

> 体检业主正在产出的 MinerU OCR 结果：**进度 + 质量**（重点看表格与数字）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/20-scan-all-markdown.py`（1 个符号）

> 全量扫一遍已 OCR 的 markdown：**到底有多少含条款号结构**（决定能不能沿用现有切分）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 36 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/21-scan-clauses-fixed.py`（1 个符号）

> 全量扫已 OCR 的 markdown：**有多少含条款号结构**（**修正版**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 37 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/22-table-and-number-check.py`（1 个符号）

> OCR 质量终检：**表格可检索性** + **数字损伤的迹象**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 41 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/23-setup-trial-copy.py`（1 个符号）

> 入库试跑 · 步骤 1：**建一份真库的副本**（用 SQLite 官方 backup API，保证一致性）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/24-ingest-sample.py`（1 个符号）

> 入库试跑 · 步骤 2：**小样本**先跑（法规 + MinerU OCR 的国标），逐步验。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 49 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/25-diagnose-split.py`（1 个符号）

> 诊断：为什么国标 OCR 入库后**切出的条款太少**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 41 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/26-split-damage-scale.py`（1 个符号）

> 量化：**国标 OCR 的切分到底坏到什么程度**（决定这 799 本能不能直接入库）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 38 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/27-real-splitter-on-40.py`（1 个符号）

> 关键实测：**生产切分器（读 `middle_json.json`）在 MinerU 4.0 产物上到底行不行。**

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/28-mineru40-structure.py`（2 个符号）

> 看清 MinerU **4.0** 的 `middle_json` 结构 —— 判断"能不能加一层兼容"还是"必须换解析"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `keytree` 函数 | 27 | 4 | 缩略打印结构：键 → 类型 / 列表长度。 |
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/29-mineru40-blocks.py`（1 个符号）

> MinerU 4.0 `blocks` 的**块类型与块内容**明细 —— 做兼容层要用到的最后一块拼图。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/30-adapter-prototype.py`（5 个符号）

> **原型**：把 MinerU 4.0 的 `middle_json` 适配成 3.4 的形状，喂给**现有的** `load_middle_items`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_as_text` 函数 | 50 | 19 | 4.0 的 `content` 有时是字符串、有时是对象列表 ⇒ 统一取文本。 |
| `_spans_of` 函数 | 61 | 4 | 4.0 的 content 列表 → 3.4 的 `lines\[\].spans\[\]`。 |
| `_text_block` 函数 | 81 | 2 | — |
| `convert` 函数 | 86 | 17 | — |
| `main` 函数 | 162 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/31-verify-adapter-quality.py`（1 个符号）

> 核验适配层原型的**输出质量**：条款号像不像样、条文内容对不对。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/32-regression-after-fix.py`（1 个符号）

> 改后回归：用**生产代码**（不再走原型脚本）把真实 933 本国标跑一遍。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/33-precount-ingest.py`（1 个符号）

> 全量入库前置清点：**要入多少、大概多久、有没有遗漏**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/34-ingest-full.py`（6 个符号）

> 全量入库器：**强制性国标 803 本 + 法律法规 1,563 个**（走生产入口，可续跑）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_done` 函数 | 53 | 6 | — |
| `_append` 函数 | 66 | 3 | — |
| `_guard` 函数 | 72 | 2 | — |
| `collect_gb` 函数 | 82 | 2 | — |
| `collect_law` 函数 | 105 | 2 | — |
| `main` 函数 | 123 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/35-retest-11-questions.py`（1 个符号）

> 入库验收：11 条真问题复测，**两种口径都跑**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 49 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/36-verify-gb-phase.py`（2 个符号）

> 国标阶段核对（目标 ②③ 的国标半）：三个计数 + 质量抽验 + 失配清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `stats` 函数 | 25 | 194 | — |
| `main` 函数 | 49 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/37-measure-law-split.py`（1 个符号）

> 量准法规切分的两个已知问题（修之前先量，不凭印象）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 48 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/38-compare-split-variants.py`（1 个符号）

> 比三种切法，用**已知真实条数**的法律当裁判 —— 挑最准的再改生产代码。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 36 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/39-prep-reingest-laws.py`（1 个符号）

> 重入前的准备：**删掉副本里那批法规**，并把台账里 `law::` 的记录清掉。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 37 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/40-promote-to-prod.py`（3 个符号）

> 把副本推成生产库（**业主已授权**：2026-10-07「现在就方便，你直接干」）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `counts` 函数 | 38 | 300 | — |
| `exclusive_ok` 函数 | 54 | 2 | — |
| `main` 函数 | 63 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/41-verify-law-counts.py`（1 个符号）

> 复核法规重入结果：**条数对不对 + 正文还带不带文件头**（目标第 ② 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 37 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/42-reingest-fallback-laws.py`（1 个符号）

> 重入**走兜底分支的那批法规**（它们的条文还带文件头）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/43-verify-prod-after-push.py`（2 个符号）

> 第 ⑤ 步：**在真库上**（只读）补验推送结果。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `probe` 函数 | 32 | 301 | — |
| `main` 函数 | 54 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/44-probe-qa-apis.py`（1 个符号）

> 部委问答扩采 · 侦察：找出三家的**真实数据接口**（它们的列表页是 JS/接口驱动的）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 46 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/45-mine-qa-js.py`（1 个符号）

> 部委问答扩采 · 第 2 步：抓 JS 文件，**挖出真正的接口 URL 并试调**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 40 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/46-extract-inline-ajax.py`（1 个符号）

> 部委问答扩采 · 第 3 步：**把页面内联 JS 里那段 AJAX 定义挖出来**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 40 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/47-try-was5.py`（1 个符号）

> 部委问答扩采 · 第 4 步：**试调 WAS5 接口**（生态环境部）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 39 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/48-was5-capacity.py`（1 个符号）

> 部委问答扩采 · 第 5 步：**摸清 WAS5 接口的容量与取数方式**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 43 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/49-harvest-mee.py`（2 个符号）

> 部委问答扩采 · 第 6 步：**把生态环境部「常见问题」158 条取下来并量两个比例**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `norm` 函数 | 42 | 84 | — |
| `main` 函数 | 46 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/50-probe-mohurd-samr.py`（1 个符号）

> 部委问答扩采 · 住建部 + 市场监管总局：**先找到问答入口，再找列表接口**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `eval/recall-funnel/exp-5-real-questions/51-try-was5-elsewhere.py`（1 个符号）

> 部委问答扩采 · 第 7 步：**拿 WAS5 这个模式去各部委试**（快路子）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 39 | 1131 | — |

### `eval/recall-funnel/exp-6-cap/freeze.py`（3 个符号）

> P2 实验 #1 · 冻结记录：**改代码之前**把该冻的哈希记下来。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `sha` 函数 | 31 | 4 | — |
| `main` 函数 | 35 | 1131 | — |
| `_write` 函数 | 53 | 36 | — |

### `eval/recall-funnel/exp-6-cap/verdict.py`（4 个符号）

> P2 实验 #1 判决器：**上限 20（对照）vs 上限 100（处理）**，按预登记止损线机械判决。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 30 | 103 | — |
| `per_query` 函数 | 37 | 53 | — |
| `tier` 函数 | 47 | 265 | — |
| `main` 函数 | 59 | 1131 | — |

### `eval/recall-funnel/exp-7-rrm/run.py`（7 个符号）

> 实验 7：融合算子 —— RRF（加权求和） vs RRM（取最大）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ro_conn` 函数 | 60 | 19 | — |
| `fuse` 函数 | 64 | 10 | 六种融合。 |
| `order` 函数 | 96 | 157 | 按融合分降序，套生产同样的时效过滤，取前 top_n。 |
| `rank_of` 函数 | 116 | 33 | — |
| `mcnemar_exact` 函数 | 123 | 14 | 精确 McNemar（双侧）：b/c 是不一致对的两种方向。 |
| `boot_ci` 函数 | 134 | 3 | cluster bootstrap（cluster = gold 文档）。 |
| `main` 函数 | 152 | 1131 | — |

### `eval/recall-funnel/exp-8-fullrank/run.py`（1 个符号）

> F1：**全库名次分解** —— 正确条文在 66 万条里到底排第几？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 52 | 1131 | — |

### `eval/recall-funnel/exp-9-col-prior/measure.py`（3 个符号）

> E9 / P2 诊断·第 1 刀：**候选列能不能当"筛子"，把正确条文从第 4,322 名提上来？**

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clause_shape` 函数 | 73 | 3 | 把条款号归成形态桶（不看具体数字，避免变成身份列）。 |
| `len_bucket` 函数 | 91 | 3 | — |
| `main` 函数 | 107 | 1131 | — |

### `eval/recall-funnel/failure-samples.py`（1 个符号）

> 失败样本留证：从"六路深读 1000 都没召回 gold"的问法里抽最多 50 条，把当时的候选原样存下。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/funnel.py`（9 个符号）

> 六路召回漏斗（只读诊断）：正确条文到底在哪条通道、哪个截断位置丢的。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ro_conn` 函数 | 66 | 19 | — |
| `channel_exact` 函数 | 76 | 15 | — |
| `channel_fts` 函数 | 102 | 22 | — |
| `channel_fts_pool` 函数 | 116 | 2 | 通道 B 的**候选池大小**（MATCH 命中总行数，不限量）。 |
| `channel_vec` 函数 | 132 | 12 | — |
| `channel_modality` 函数 | 142 | 14 | — |
| `rank_of` 函数 | 155 | 33 | — |
| `_prod_kept` 函数 | 162 | 2 | 照生产的结果循环裁前 n 个：`fetch_full_clause` 取不到就跳过，已废止/被替代也跳过。 |
| `main` 函数 | 178 | 1131 | — |

### `eval/recall-funnel/lexical-overlap.py`（1 个符号）

> 字面重叠率（"按字找"的先天天花板）——用本批考卷自己的数字，不引用任何历史数字。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/preprocess-diff.py`（1 个符号）

> 生产问答路径**实际喂给六路通道的查询串**是什么（只读，产出可核的清单）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `eval/recall-funnel/regression-ingest/run-funnel-on.py`（1 个符号）

> 入库回归检查 · 跑分器驱动器：**把现成的 `funnel.py` 指向任意一个库**，跑完把结果写到指定前缀。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `eval/recall-funnel/regression-ingest/run-summarize-on.py`（1 个符号）

> 入库回归检查 · 汇总器驱动器：**把 `summarize.py` 指向指定的逐条文件**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/recall-funnel/regression-ingest/verdict.py`（3 个符号）

> 入库回归检查 · **判决器**：把"入库前"与"入库后"两个汇总按**预先写死的判据**机械判决。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 30 | 103 | — |
| `per_query` 函数 | 37 | 53 | — |
| `main` 函数 | 47 | 1131 | — |

### `eval/recall-funnel/rerun-consistency.py`（1 个符号）

> 全量重跑对照（可复算的产物）：同样的输入跑两遍，逐条通道名次必须一模一样。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `eval/recall-funnel/summarize.py`（2 个符号）

> 漏斗结果汇总：把 `funnel-per-query.jsonl` 折成一张能直接看的表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_pct` 函数 | 37 | 9 | — |
| `main` 函数 | 41 | 1131 | — |

### `eval/reverse-benchmark/generate.py`（5 个符号）

> F 方案 v2：从条文反推外行问法（修了 v1 的提示词缺陷 + 生成换 Gemini）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `call` 函数 | 77 | 17 | — |
| `parse` 函数 | 91 | 119 | — |
| `one` 函数 | 104 | 57 | — |
| `overlap` 函数 | 119 | 17 | — |
| `main` 函数 | 130 | 1131 | — |

### `eval/reverse-benchmark/verify.py`（1 个符号）

> 对 F 方案（反推）的问法做【盲判】：判这一对配得对不对。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `eval/run_benchmark.py`（4 个符号）

> Golden Set 评测器（Task 10.1）：检索指标 + 核验拦截率 + 合规三色准确率。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_hit` 函数 | 34 | 25 | 命中 = 返回里出现了期望的 **(标准号, 条款号)** 对。 |
| `run_benchmark` 函数 | 58 | 7 | — |
| `_run` 函数 | 70 | 73 | — |
| `main` 函数 | 128 | 1131 | — |

### `scripts/_measure_common.py`（2 个符号）

> 测量与修复脚本的共享口径（**只放"必须一致"的东西**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `chunk_text` 函数 | 35 | 23 | 按空行切段，再把相邻段拼到约 `size` 字。 |
| `db_stat` 函数 | 68 | 4 | 当前生产库的 `(路径, 大小, mtime, sha256)`。 |

### `scripts/_stdparse.py`（1 个符号）

> 无副作用的共享模块：文件名 → 标准号/名称提取。供 program_compare / debug_loop_driver 复用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `derive_standard` 函数 | 14 | 12 | 从文件名提取 (standard_no, standard_name)。 |

### `scripts/answers-matrix.py`（1 个符号）

> 五类能力矩阵（§11.0 R6c）：人可读的"哪一类由谁答、它今天活着吗"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `scripts/apply-folder-filing.py`（36 个符号）

> 知识库多级目录 · 对真库执行归位（KB-FOLDER-PLAN §五第 1 步的"落库"那一半）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Abort` 类 | 151 | 21 | 前置条件不成立 ⇒ 中止（退出码 2），**绝不带着问题往下写**。 |
| `_data_dir` 函数 | 157 | 5 | 数据区目录（**不调 get_settings()**：它会 mkdir，预演时不该有副作用）。 |
| `_open_readonly` 函数 | 166 | 7 | **只读**打开（``mode=ro``）——SQLite 保证连一个字节都不写，也不建 -wal/-shm。 |
| `_db_files` 函数 | 174 | 4 | 库本体 + ``-wal`` + ``-shm`` 的大小与 mtime（WAL 模式下只看 .db 会看不出写入）。 |
| `_engine_status` 函数 | 191 | 2 | 引擎会话文件 + "那个端口有没有人听"。 |
| `_strip_sql_comments` 函数 | 220 | 4 | 去掉 SQL 注释后切分成**语句列表**。 |
| `target_ddl` 函数 | 274 | 5 | 从 ``schema.sql`` 里**现取**那三张表的建表/建索引语句（不手抄一份）。 |
| `_schema_fingerprint` 函数 | 312 | 3 | 库里**全部** sqlite_master 对象的 ``type:name → sql``（列改动也会体现在 sql 上）。 |
| `_assert_only_additions` 函数 | 323 | 3 | 既有对象一个都不许改、不许删。 |
| `_split_top_level` 函数 | 357 | 2 | 按**顶层**逗号切分一段 SQL（括号里的逗号不算）。 |
| `_columns_from_create` 函数 | 387 | 2 | ``CREATE TABLE`` 语句里声明的列名（表级约束与虚拟表列自动跳过）。 |
| `declared_objects` 函数 | 417 | 4 | ``schema.sql`` 声明的对象：``{"tables": {名: \[列…\]}, "indexes": {名: 表}}``。 |
| `_live_objects` 函数 | 437 | 2 | 库里的用户对象：``{"tables": {名: \[列…\]}, "indexes": {名: 表}}``（不含 ``sqlite_*``）。 |
| `schema_drift` 函数 | 457 | 12 | 拿 ``schema.sql`` 声明的对象与库里的实际对象**对账**（只读）。 |
| `_entity_tables` 函数 | 501 | 2 | 实体表清单（清点"库有没有被动过"用。 |
| `db_state` 函数 | 514 | 6 | "库有没有被动过"的一个总指纹（给"中止不写"当证据用，只读）。 |
| `ensure_target_tables` 函数 | 538 | 3 | 按 schema.sql 的 DDL 建那三张表（``IF NOT EXISTS``），并证明**没动任何既有东西**。 |
| `_load_docs` 函数 | 574 | 6 | 读全部文档（``catalog_hidden`` 列在才读，与 ``/documents/categories`` 同口径）。 |
| `_table_names` 函数 | 585 | 4 | — |
| `_target_tables_present` 函数 | 590 | 5 | — |
| `_existing_row_counts` 函数 | 595 | 2 | 三张新表里**已经有多少行**（复跑时先看清"是不是干净的白纸"）。 |
| `_existing_folders` 函数 | 602 | 3 | ``(父 id, 名字) → 目录 id`` 的全量索引（判断"复用"用），外加根层名字清单。 |
| `_clause_counts` 函数 | 616 | 3 | "这篇到底有几条条款、几条是正文（content_type='normal'）" —— 写 failure_kind 的证据。 |
| `build_payload` 函数 | 644 | 5 | 把归位计划翻译成"四个顶层 + 标准树（跳过重复层）+ 待分类"的节点/归属/状态。 |
| `align_top_sorts` 函数 | 757 | 2 | 把四个顶层目录的 ``sort`` 对齐到业主手定的值（**只改这四行的 sort 列**）。 |
| `backup_db` 函数 | 777 | 2 | SQLite backup 接口整份备份 + **读回核对**。 |
| `_depth_counts` 函数 | 833 | 2 | 各级目录数（按 ``folder.parent_id`` 递归。 |
| `read_back` 函数 | 847 | 4 | **重新打开真库**读回自证（不看写函数的返回值自说自话）。 |
| `_print_rollback` 函数 | 978 | 8 | 回退办法（确切命令。 |
| `_db_state_diff` 函数 | 995 | 4 | 两次 ``db_state`` 的差异（只报变化项。 |
| `_print_no_write_proof` 函数 | 1015 | 3 | 把"真的一个字节都没写"打印成**可核对的三个数**。 |
| `_print_plan_summary` 函数 | 1034 | 3 | — |
| `_print_read_back` 函数 | 1089 | 2 | — |
| `_main` 函数 | 1145 | 2 | — |
| `_write_report` 函数 | 1333 | 3 | 机器可读报告。 |
| `main` 函数 | 1362 | 1131 | — |

### `scripts/audit-async-endpoints.py`（18 个符号）

> 审计：**哪些 HTTP 端点声明成 `async def`，却在做同步重活？**（§10.71，复核 b12 的教训）

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_funcs_of` 函数 | 75 | 3 | — |
| `_modules_of` 函数 | 83 | 3 | — |
| `_call_names` 函数 | 91 | 2 | 收集调用点：('f', None) 表示 `f(...)`。 |
| `_code_only` 函数 | 105 | 4 | 只留**代码**：删掉 docstring 与注释（§10.78 补的一个**假阳性**来源）。 |
| `_markers_in` 函数 | 124 | 2 | — |
| `_local_aliases` 函数 | 132 | 2 | 函数体**内部** `import` 出来的名字 → 模块 / 函数。 |
| `awaits_like` 函数 | 177 | 11 | 源码里"**会真正让出事件循环**"的三类语法节点总数（§10.86）。 |
| `never_yields` 函数 | 197 | 18 | 这段 `async def` 端点源码**永远不会真正让出控制权**吗？。 |
| `_own_scope_nodes` 函数 | 256 | 4 | `fn` **自己作用域**里的节点（跳过嵌套函数/lambda 的内部）。 |
| `nested_async_gen_without_await` 函数 | 280 | 7 | 端点里那些**没有 await 的 async 生成器**的名字（§10.80 的判据，也走 AST）。 |
| `_endpoint_node` 函数 | 303 | 2 | 源码里的**第一个**函数定义（= 端点自己）。 |
| `_body_read` 函数 | 311 | 2 | — |
| `_call_name` 函数 | 317 | 2 | `f(...)` ⇒ `"f"`。 |
| `_real_suspension` 函数 | 324 | 4 | `fn`（含它**调用的**嵌套助手）在自己的执行路径上有没有**真**挂起点？。 |
| `effective_real_await` 函数 | 351 | 11 | 这条 async 端点**执行路径上**真的会让出控制权吗？（§10.88：名单第二关的判据）。 |
| `_is_local` 函数 | 396 | 3 | 名字是不是这个函数的**局部/闭包变量**（`body.get`、`project_id.strip` 这类）。 |
| `audit_endpoint` 函数 | 408 | 2 | — |
| `main` 函数 | 469 | 1131 | — |

### `scripts/backfill-bbox-units.py`（8 个符号）

> 回填 MinerU 4.0 那批的**坏 bbox**（spec 012 R2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_is_bad` 函数 | 67 | 2 | 该 bbox 是不是"归一化 x + 未乘页高的 y"（= 本缺陷的形状）。 |
| `_lines_of_page` 函数 | 79 | 2 | 该页**全部文本行**的 bbox（按 块序→行序），与 `pipeline` 取行框的顺序一致。 |
| `_table_boxes_of_page` 函数 | 93 | 2 | 该页**表格块**的 bbox（**块级**）。 |
| `_match_line` 函数 | 113 | 3 | 给一条坏 span 找它对应的**那一行**（返回 lines 下标。 |
| `_find_middle_for` 函数 | 171 | 2 | 按 `doc_meta.file_path` 找它的 MinerU 产物（不瞎找：只认同目录同前缀）。 |
| `collect_targets` 函数 | 186 | 2 | 列出**含坏 bbox 的文档**。 |
| `build_updates` 函数 | 209 | 2 | 算一篇文档的更新（不写库）。 |
| `main` 函数 | 281 | 1131 | — |

### `scripts/chain-snapshot.py`（3 个符号）

> 链快照（§11.0 R6c 第一步）：把"今天的链"与"按台账算出来的链"并排打出来。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 39 | 1131 | — |
| `_segments_payload` 函数 | 129 | 4 | 号段报告（`segments_json`，R7）—— **文本段与 `--json` 共用这一个**（别各算一份）。 |
| `_segments_section` 函数 | 147 | 5 | 号段那一段的**人读**打印（数据来自 `_segments_payload`，这里只排版）。 |

### `scripts/channel-anchor-measure.py`（2 个符号）

> 渠道锚点实测器（§11.0 R6）：给一条渠道**量**出可直接粘贴的探针目标。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `anchor_from_html` 函数 | 40 | 2 | 从**原样正文**里取锚点候选：`<title>` 中最长的不含空白片段（≥6 字）。 |
| `main` 函数 | 58 | 1131 | — |

### `scripts/channel-status-report.py`（1 个符号）

> 渠道台账状态快照（§11.0 R3c）：把实机库里的渠道台账导成**人可读**的 Markdown。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 39 | 1131 | — |

### `scripts/check-fixture-leak.py`（1 个符号）

> 生产库卫生检查：**测试夹具不许以「可见文档」身份留在库里**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 51 | 1131 | — |

### `scripts/check-repo-uniformity.py`（19 个符号）

> 仓库统一化尺子 —— 五条指标，一条命令出全部读数，exit code 即判据。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_run` 函数 | 79 | 73 | — |
| `_ruff_available` 函数 | 84 | 3 | — |
| `_pyscn_available` 函数 | 89 | 3 | — |
| `_disp_width` 函数 | 103 | 2 | 按**显示列**算宽度（中文/全角算 2 列）。 |
| `_prose_lines` 函数 | 113 | 2 | 源码里属于注释或字符串的行号集合（用 tokenize，不用正则猜）。 |
| `_ruff_available` 函数 | 130 | 3 | — |
| `_pyscn_available` 函数 | 135 | 3 | — |
| `_ruff_concise` 函数 | 140 | 4 | — |
| `metric_ruff` 函数 | 154 | 3 | 返回 (判据条数, 按规则码计数, 明细行)。 |
| `metric_pyscn_clones` 函数 | 219 | 2 | — |
| `metric_module_docstrings` 函数 | 235 | 3 | 缺模块 docstring 的 `.py` 文件数（`__init__.py` 与 conftest 不算）。 |
| `metric_duplicate_filenames` 函数 | 262 | 3 | 同名的 `.py` 出现在**两个以上不同目录** ⇒ 一个东西两处放。 |
| `metric_ast_dupes` 函数 | 285 | 4 | 调 `scripts/uniformity-ast-dupes.py`（α-等价），返回 (组数, 警告)。 |
| `measure` 函数 | 306 | 95 | — |
| `load_baseline` 函数 | 358 | 2 | — |
| `compare` 函数 | 364 | 20 | 棘轮：读数 ≤ 天花板。 |
| `print_table` 函数 | 384 | 3 | — |
| `_selftest` 函数 | 415 | 4 | 验判据真的会拦：拿一份坏样本，确认 ③④⑤ 都能抓到。 |
| `main` 函数 | 457 | 1131 | — |

### `scripts/convert-library-to-text.py`（3 个符号）

> 把下载的论文/教材转成文本再入库 —— **绕过仓里那条抽不出文字的 PDF 路径**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 39 | 172 | 去连字垃圾、压缩空行、去掉页眉页脚式的孤立短行。 |
| `main` 函数 | 47 | 1131 | — |
| `doc_page_count` 函数 | 107 | 6 | — |

### `scripts/docs/check-links.py`（4 个符号）

> 全仓 markdown 链接检查器。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `is_probably_not_a_link` 函数 | 57 | 2 | 判断一个"链接目标"其实是正文里的示例/正则/占位符。 |
| `iter_markdown` 函数 | 71 | 2 | 仓库里所有受检查的 markdown 文件（遍历时剪枝，不进入依赖与缓存目录）。 |
| `resolve` 函数 | 82 | 671 | 返回 (是否存在, 是按哪种基准找到的)。 |
| `main` 函数 | 97 | 1131 | — |

### `scripts/docs/gen-doc-index.py`（2 个符号）

> 生成 `docs/INDEX.md`（文档的机械索引）——**生成物，勿手改**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `first_desc` 函数 | 15 | 2 | — |
| `lastc` 函数 | 27 | 2 | — |

### `scripts/docs/scan-rename-targets.py`（6 个符号）

> 机械扫描命名违规项（001-project-consolidation T006）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `tracked_files` 函数 | 62 | 6 | 只扫**受版本控制**的文件——未跟踪的本机产物不归规范管（规范 §七）。 |
| `is_under_skipped_dir` 函数 | 78 | 8 | — |
| `doc_filename_violation` 函数 | 84 | 7 | R1：文档文件名用 `-`，不用 `_`。 |
| `dir_name_violation` 函数 | 102 | 5 | R2：目录名全小写 kebab-case。 |
| `scan` 函数 | 121 | 180 | — |
| `main` 函数 | 146 | 1131 | — |

### `scripts/fetch_law.py`（9 个符号）

> 官方法规抓取 CLI（docs/LAW-SOURCE-PLAN.md P1/P3）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_print` 函数 | 29 | 4 | — |
| `cmd_flk_search` 函数 | 33 | 2 | — |
| `cmd_flk_match` 函数 | 45 | 2 | 标题精确匹配（searchType=1）→ 取 sxx=3 有效版第一条入库。 |
| `cmd_flk_ingest` 函数 | 61 | 2 | — |
| `cmd_govcn_search` 函数 | 68 | 2 | — |
| `cmd_govcn_ingest` 函数 | 81 | 2 | — |
| `cmd_updates` 函数 | 88 | 2 | 法规更新检查（只读）：库内官方源文档 vs 官方源现状。 |
| `_tags` 函数 | 102 | 4 | — |
| `main` 函数 | 106 | 1131 | — |

### `scripts/five-class-order-diff.py`（2 个符号）

> 五类**排序**的差异哨兵（§11.0 R6c-4c）：谁的第一候选会因为"按能力排"而变？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_sample` 函数 | 39 | 4 | 真库抽样（只读）：按 rowid 等距取，尽量覆盖不同号段。 |
| `main` 函数 | 53 | 1131 | — |

### `scripts/fix-standard-no-ocr-suffix.py`（6 个符号）

> 一次性维护：把 `doc_meta.standard_no` 尾部的「(OCR采集)」来源标记**搬**到 `source` 字段。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_candidates` 函数 | 67 | 6 | 返回 \[(doc_id, old_no, new_no)\]，只有 new != old 的才算候选。 |
| `check_collisions` 函数 | 84 | 2 | 撞号检查：去后缀后是否与**别的**文档的标准号重复。 |
| `check_source_consistency` 函数 | 105 | 2 | 核实这批候选**确实**都来自 LawRefBook（防止把别的来源一起改了）。 |
| `count_fts_rows` 函数 | 119 | 3 | `clause_fts` 里带后缀的行数（**另一份副本**）。 |
| `source_distribution` 函数 | 125 | 3 | — |
| `main` 函数 | 131 | 1131 | — |

### `scripts/fix_standard_name_suffix.py`（2 个符号）

> 一次性维护：清理 `doc_meta.standard_name` 结尾的**副本后缀**（`…(1)`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_candidates` 函数 | 42 | 6 | 返回 \[(doc_id, old_name, new_name)\]，只有 new != old 的才算候选。 |
| `main` 函数 | 60 | 1131 | — |

### `scripts/gates-tracked-total.py`（4 个符号）

> 门禁棘轮的**口径**：只统计**受版本控制**的用例（`run-gates.ps1` 调它）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_candidate_files` 函数 | 41 | 2 | 点分名 → 候选文件路径，**由长到短**（junit 把类名塞进 classname）。 |
| `_tracked_set` 函数 | 51 | 2 | `git ls-files` 的**仓库相对路径**集合（正斜杠、小写盘符无关，统一成 posix）。 |
| `compute` 函数 | 58 | 8 | — |
| `main` 函数 | 98 | 1131 | — |

### `scripts/ingest-library-text.py`（1 个符号）

> 把「转换好的文献纯文本」入「参考资料」平面（**绕过那条抽不出文字的 PDF 路径**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 49 | 1131 | — |

### `scripts/ingest-rag-study-materials.py`（2 个符号）

> 「全部导入」：把学习材料（教程原文 + 我们自己的笔记）一次性入「参考资料」平面。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_find_or_create_project` 函数 | 52 | 2 | — |
| `main` 函数 | 65 | 1131 | — |

### `scripts/ks-credential-readers-scan.py`（6 个符号）

> 凭据读者排查（整改批 1b / 问题清单第 4 条）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `scan_registry` 函数 | 46 | 2 | — |
| `_findings_in_text` 函数 | 75 | 6 | 文本里出现哪些目标名（值同样不记录）。 |
| `scan_credential_files` 函数 | 84 | 4 | — |
| `scan_live_processes` 函数 | 111 | 2 | 活进程的环境块里谁带着旧名（只记 pid/进程名，绝记值）。 |
| `scan_shell_configs` 函数 | 151 | 3 | — |
| `main` 函数 | 189 | 1131 | — |

### `scripts/ks-credential-reconcile.py`（4 个符号）

> 引擎/DSH 凭据对账（整改批 2c / 问题清单 #6）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_sha` 函数 | 41 | 3 | — |
| `engine_side` 函数 | 45 | 2 | 引擎加密存储里的 {名字: 指纹}（内存解密后哈希，不打印值）。 |
| `dsh_side` 函数 | 57 | 2 | ~/.dsh/.credentials.yaml 里 {名字: 指纹}。 |
| `main` 函数 | 74 | 1131 | — |

### `scripts/ks-credentials-migrate.py`（2 个符号）

> 把 API 密钥从 **Windows 系统层**搬进引擎自己的加密存储（2026-09-11 业主指令：不要动系统层）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_plan` 函数 | 46 | 15 | — |
| `main` 函数 | 67 | 1131 | — |

### `scripts/loop2/driver_v2.py`（21 个符号）

> Bounded self-debug loop orchestrator (loop2 step 5).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_default` 函数 | 93 | 7 | — |
| `_load` 函数 | 97 | 125 | — |
| `_dump` 函数 | 104 | 14 | — |
| `log` 函数 | 109 | 94 | — |
| `list_books` 函数 | 119 | 2 | Deterministic, dedup-by-standard_no enumeration (exclude 体检结果 dirs).。 |
| `build_queue` 函数 | 135 | 3 | — |
| `load_queue` 函数 | 146 | 4 | — |
| `_abs_pdf` 函数 | 150 | 3 | — |
| `next_book` 函数 | 154 | 2 | — |
| `_locate_doc_id` 函数 | 174 | 2 | — |
| `assess` 函数 | 195 | 6 | Wire the deterministic oracle: locate/ingest a doc, then build+score snapshot.。 |
| `record_pass` 函数 | 218 | 11 | — |
| `record_fail` 函数 | 240 | 3 | — |
| `record_blocked` 函数 | 253 | 4 | A book that hit MAX_ROUNDS without passing the oracle goes here (not 'passed').。 |
| `seed_issues` 函数 | 270 | 3 | Seed known_issues.json with the known root-cause taxonomy (count 0 baseline).。 |
| `record_issue` 函数 | 282 | 7 | Three-strike by ROOT-CAUSE class. At 3 it arms an architecture reflection。 |
| `solve_issue` 函数 | 307 | 3 | Clear a root-cause class after a generalised fix (count resets; class solved).。 |
| `is_converged` 函数 | 323 | 6 | — |
| `status` 函数 | 338 | 1664 | — |
| `report` 函数 | 356 | 294 | — |
| `main` 函数 | 371 | 1131 | — |

### `scripts/loop2/oracle_score.py`（9 个符号）

> Deterministic oracle scorer (loop2 step 1).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_threshold` 函数 | 39 | 3 | — |
| `Config` 类 | 46 | 12 | — |
| `_content_pages` 函数 | 53 | 2 | — |
| `_ratio` 函数 | 66 | 14 | — |
| `score_text` 函数 | 74 | 6 | — |
| `score_pagmap` 函数 | 130 | 5 | — |
| `score_objects` 函数 | 149 | 5 | — |
| `score` 函数 | 185 | 85 | — |
| `main` 函数 | 226 | 1131 | — |

### `scripts/loop2/oracle_snapshot.py`（12 个符号）

> Deterministic per-doc structural snapshot builder (loop2 step 1).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_norm` 函数 | 49 | 21 | Light normalization for text-fidelity comparison.。 |
| `_strip_html` 函数 | 65 | 4 | Strip HTML tags from table markdown -> plain cell text (for the text path).。 |
| `_strip_orig_noise` 函数 | 70 | 4 | Remove lines that appear in the PDF text layer but not in the preview's。 |
| `_parse_page_breaks` 函数 | 81 | 7 | page_breaks column is JSON text (or list). Returns None if absent/invalid.。 |
| `_rows_for_clause` 函数 | 100 | 2 | — |
| `_content_pages_for_clause` 函数 | 104 | 1 | Set of PDF pages that carry clauses for one clause.。 |
| `_assign_lines_to_pages` 函数 | 117 | 4 | page -> \[lines\] for one clause, in reading (line) order.。 |
| `_pagelines_map` 函数 | 141 | 4 | whole-doc page -> \[lines\] (reading order across clauses). Includes table text。 |
| `_count_objects_clause` 函数 | 158 | 4 | Best-effort deterministic object counts from stored columns.。 |
| `_pdf_orig` 函数 | 171 | 2 | Per-page original text layer + embedded image count, via PyMuPDF.。 |
| `build_snapshot` 函数 | 194 | 4 | — |
| `main` 函数 | 311 | 1131 | — |

### `scripts/loop2/vlm_check.py`（7 个符号）

> VLM candidate-difference checker (loop2 step 3, design §B).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get_key` 函数 | 52 | 3 | MOONSHOT_API_KEY from HKCU\Environment then env (never printed).。 |
| `_b64` 函数 | 65 | 3 | — |
| `_moonshot_call` 函数 | 70 | 2 | Call the vision model and return the message content text. Raises on failure.。 |
| `_parse_json` 函数 | 82 | 5 | Parse VLM JSON content, tolerating code fences / leading prose.。 |
| `build_payload` 函数 | 98 | 5 | Both images (the fix) + fixed prompt. Returns JSON-serializable payload.。 |
| `vision_check` 函数 | 112 | 5 | Return structured candidate-difference hints for an (orig, prev) pair.。 |
| `main` 函数 | 150 | 1131 | — |

### `scripts/make-seed-db.py`（4 个符号）

> 从生产库切一个**小而全**的种子库，供门禁/开发用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `pick_docs` 函数 | 76 | 2 | 挑样本文档：**先保证缺陷可复现，再保证类型覆盖，最后才按大小补**。 |
| `copy_table` 函数 | 123 | 5 | — |
| `copy_by_temp_table` 函数 | 140 | 6 | 按一列 keys 过滤拷贝 —— 用**临时表 join**，不用 `IN (?,?,…)`。 |
| `main` 函数 | 187 | 1131 | — |

### `scripts/make_handoff_zip.py`（2 个符号）

> 生成交接包：源码+文档+测试+数据库快照，排除可重建的重型目录。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `add_tree` 函数 | 29 | 2 | — |
| `main` 函数 | 42 | 1131 | — |

### `scripts/measure-classical-chinese-segmentation.py`（13 个符号）

> P3.2 尺子：古籍/文言资料上，「切分方式」到底要不要换（字级？领域词典？）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `head` 函数 | 82 | 318 | — |
| `has_cjk` 函数 | 88 | 14 | — |
| `char_seg` 函数 | 93 | 4 | B 口径：每个汉字单独一个 token。 |
| `cjk_runs` 函数 | 110 | 2 | — |
| `ngram_counts` 函数 | 124 | 5 | 统计 n 元汉字串的出现**段数**（不是次数：一个词在同一段里出现 10 次算 1）。 |
| `build` 函数 | 137 | 80 | — |
| `single_ratio` 函数 | 151 | 5 | (全部 token, 单字 token, 中文单字 token) —— 从词表算，不重跑分词。 |
| `search_rows` 函数 | 165 | 2 | — |
| `char_and_expr` 函数 | 178 | 4 | B 口径的查询式：**所有汉字都要出现**（FTS5 多词默认隐式 AND）。 |
| `char_or_expr` 函数 | 191 | 3 | B 口径的松变体（任一字命中即可），只为对照，不采纳。 |
| `no_drop_expr` 函数 | 196 | 5 | A+ 口径：**索引一个字不动**，只把查询侧"丢弃单字符词"那条规则关掉。 |
| `evaluate` 函数 | 207 | 3 | — |
| `main` 函数 | 236 | 1131 | — |

### `scripts/measure-cross-language-fts.py`（9 个符号）

> 量「按字找」在非中文资料上还灵不灵 —— 换一种资料集就能重跑的一把尺子。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `head` 函数 | 84 | 318 | — |
| `load_corpus` 函数 | 91 | 3 | — |
| `build` 函数 | 104 | 80 | — |
| `vocab` 函数 | 115 | 11 | — |
| `search` 函数 | 121 | 782 | — |
| `exists` 函数 | 136 | 338 | 这个段落**能不能**被 q 匹配上（不看排名）。 |
| `variants` 函数 | 148 | 12 | 词尾变化规则。 |
| `has_cjk` 函数 | 162 | 14 | — |
| `main` 函数 | 166 | 1131 | — |

### `scripts/measure-endpoint-blocking.py`（16 个符号）

> **测"端点把事件循环卡住多久"**——「先量 → 再改 → 再量」里那把尺（§10.73）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_pdf_pages` 函数 | 45 | 2 | **实际**页数（复核 b13 的 LOW-3：输出里必须报事实，不能照抄 CLI 参数）。 |
| `make_pdf` 函数 | 55 | 8 | 造一份**文本量可控**的 PDF（不依赖仓库里的任何 fixture，跑在哪都一样）。 |
| `_heartbeat` 函数 | 74 | 2 | — |
| `measure` 函数 | 83 | 95 | 跑一次被测请求，返回耗时与事件循环的空档统计。 |
| `case` 函数 | 128 | 68 | — |
| `ingest_preview` 函数 | 134 | 3 | `POST /ingest/preview`：单文件体检（sha256 + 真解析，文件里自述"负载下可达 135s"）。 |
| `ingest_preview_inbox` 函数 | 141 | 2 | `GET /ingest/preview/inbox`：列目录（`os.walk`，轻但也是同步 I/O）。 |
| `health` 函数 | 148 | 111 | `GET /api/v1/health`。 |
| `health_board` 函数 | 158 | 3 | `GET /api/v1/diagnostics/health-board`：七条 `COUNT(*)` + `mineru_available()`。 |
| `document_figure` 函数 | 169 | 1 | `GET /api/v1/documents/{doc_id}/figure/1`：**真渲染**（PyMuPDF 按题注定位 + 截图）。 |
| `_seed_figure_doc` 函数 | 181 | 3 | 造一份"题注在最后一页"的 PDF + 库内 doc_meta 行（只碰临时库）。 |
| `egress_audit_export` 函数 | 219 | 2 | `GET /api/v1/egress/audit/export`：把外发记录导成 JSON 落盘（§10.76）。 |
| `_seed_egress_audit` 函数 | 234 | 2 | 把 `debug_dump` 的审计行铺 **1000 行**（历史口径，便于与旧数字对比），只碰临时库。 |
| `snapshot_create` 函数 | 254 | 1 | `POST /api/v1/snapshots`：造快照 = 读整个库 + sha256 + 落盘（§10.79）。 |
| `_seed_bulk_clauses` 函数 | 264 | 2 | 往临时库塞一批条款（把"读库+哈希"的代价撑起来。 |
| `main` 函数 | 286 | 1131 | — |

### `scripts/measure-material-bridge.py`（3 个符号）

> 用**新语料**测「翻译层」：把用户的大白话接到这份资料自己的说法上，能抢回多少召回？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean_terms` 函数 | 57 | 4 | 逐级清洗（level 越大越严）。 |
| `extract_terms` 函数 | 83 | 2 | 从一份笔记里机械抽候选术语 → {术语: 它第一次出现的那一行（当"定义正文"）}。 |
| `main` 函数 | 112 | 1131 | — |

### `scripts/measure-material-recall.py`（3 个符号）

> 把学习笔记入「参考资料」平面，并**实测导入后的召回效果**（可复算）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_chunk_containing` 函数 | 58 | 3 | — |
| `_headings` 函数 | 65 | 2 | 取 `## ` / `### ` 小节标题（去掉序号与强调标记），当"术语式"查询。 |
| `main` 函数 | 85 | 1131 | — |

### `scripts/measure-prefix-multiword.py`（2 个符号）

> 入库的尺子：**真实的多词提问**下，提问侧词干前缀是帮忙还是添乱？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `content_words` 函数 | 62 | 2 | 拉丁内容词：≥4 字母、全小写、不含中文。 |
| `main` 函数 | 72 | 1131 | — |

### `scripts/measure-term-aggregation.py`（5 个符号）

> 量「同名多定义怎么合并」的几种算法 —— P1 对齐的第二刀（**总账与个体变差一起看**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 58 | 90 | — |
| `_segment_max` 函数 | 62 | 2 | — |
| `_segment_mean` 函数 | 66 | 2 | — |
| `_segment_top2` 函数 | 71 | 2 | 名前两条的均值。 |
| `main` 函数 | 90 | 1131 | — |

### `scripts/measure-term-bridge.py`（2 个符号）

> 量「术语桥」（第 2 步翻译层）的端到端效果 —— **入库的复算脚本**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 57 | 90 | — |
| `main` 函数 | 61 | 1131 | — |

### `scripts/measure-term-selection.py`（4 个符号）

> 量 P1 的**主判据**：语义有界选择"选对术语"的 top-1 / top-5（**入库的复算脚本**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `words` 函数 | 52 | 90 | — |
| `main` 函数 | 56 | 1131 | — |
| `_keep_all_candidates` 函数 | 170 | 2 | 同名定义全留的候选：返回 `(术语名列表, 逐条目矩阵, 排序后的条目下标, 各名起点, 名数)`。 |
| `_name_level_scores` 函数 | 204 | 2 | 按名取最大相似度。 |

### `scripts/measure-term-victim-side.py`（1 个符号）

> 量「同名定义全留、按名取最大」的**受害侧**，并算出**盈亏平衡点**（P1 决策的关键数）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 69 | 1131 | — |

### `scripts/measure-term-window-coverage.py`（2 个符号）

> 量：术语**定义正文的长短结构**，用来判"多向量/切片"这条改造值不值得做。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 43 | 1131 | — |
| `_ro_conn` 函数 | 102 | 2 | — |

### `scripts/migrate-clause-vec-doc-id.py`（6 个符号）

> spec 003 · 迁移：给真库 `clause_vec` 加 `doc_id` 元数据列（**纯搬运，不重算向量**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_db_path` 函数 | 79 | 8 | — |
| `_conn` 函数 | 84 | 22 | — |
| `_has_doc_id` 函数 | 95 | 2 | — |
| `_count` 函数 | 103 | 17 | — |
| `main` 函数 | 107 | 1131 | — |
| `_print_rollback` 函数 | 237 | 8 | — |

### `scripts/normalize-standard-no-slash.py`（2 个符号）

> R6c-2c：把库内**存量**全角斜杠归一（`standard_no` / `short_code` / `standard_name`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_plan` 函数 | 69 | 15 | 算出变更清单。 |
| `main` 函数 | 125 | 1131 | — |

### `scripts/pick-domain-terms.py`（2 个符号）

> 从本机知识库里**机械**抽出「跨领域的专业术语」清单，给"大白话↔行话"那道翻译用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 75 | 197 | — |
| `main` 函数 | 88 | 1131 | — |

### `scripts/preview-folder-filing.py`（6 个符号）

> 知识库多级目录 · 归位预览（KB-FOLDER-PLAN §五第 1 步；**只读真库，绝不写入**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_close_copy_connections` 函数 | 53 | 3 | 关掉线程局部里缓存的连接。 |
| `_stat_of` 函数 | 67 | 3 | — |
| `_copy_db_readonly` 函数 | 73 | 2 | 只读副本：``mode=ro`` 打开源库（SQLite 保证不写源），backup 到副本。 |
| `_read_docs` 函数 | 89 | 2 | — |
| `_verify_applied` 函数 | 99 | 2 | 落库后**读回来**核对（不靠写函数的返回值自说自话）。 |
| `main` 函数 | 125 | 1131 | — |

### `scripts/probe-recall-latency.py`（2 个符号）

> 临时探针（不入库）：在**真库规模**下量我们三条召回通道的耗时 —— 补一个登记已久的空档。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_med` 函数 | 39 | 6 | — |
| `main` 函数 | 48 | 1131 | — |

### `scripts/question-route.py`（2 个符号）

> 按问题选渠道（§11.0 R6c-3）：给定标准号，打印"五类各由谁答、没答出来是哪一种"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_sample` 函数 | 33 | 4 | 从真库取最近入库的 n 个非空标准号（只读。 |
| `main` 函数 | 51 | 1131 | — |

### `scripts/rebuild-reference-edges.py`（4 个符号）

> 引用边批量重算（诊断 + 修复）—— 2026-10-09 真缺陷的批量修法。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_plan` 函数 | 86 | 15 | 只读：算出「现有边 / 重算边 / 不一致文档」。 |
| `analyze` 函数 | 120 | 7 | — |
| `apply` 函数 | 145 | 156 | — |
| `main` 函数 | 212 | 1131 | — |

### `scripts/repair-missing-standard-no.py`（3 个符号）

> R6c-2e：修**号里没有数字**的坏行（从 `file_path` 的文件名推导真号）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `derive_from_path` 函数 | 64 | 2 | 文件名 → (真号 或 None, 说明)。 |
| `_plan` 函数 | 80 | 15 | — |
| `main` 函数 | 114 | 1131 | — |

### `scripts/repair_patch_watermarks.py`（1 个符号）

> 修复：`clause_patch` 里被 `pypdf_backfill` 越界抽取污染的水印/页眉。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 39 | 1131 | — |

### `scripts/restore_package.py`（4 个符号）

> 数据包离线恢复 CLI（2026-08-26，P2-②：data_package.py TODO(supervisor) 接线）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_sha256` 函数 | 34 | 2 | — |
| `_registry` 函数 | 42 | 16 | — |
| `validate` 函数 | 53 | 7 | 校验包：返回 {db_path, checksum, manifest}。 |
| `main` 函数 | 71 | 1131 | — |

### `scripts/std_bulk_import.py`（7 个符号）

> 国标批量入库 v2（覆盖式）：只入库 CSSN 已成功识别（results.jsonl found=True 且无 error）的国标 PDF。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ensure_scnet_key` 函数 | 59 | 5 | 取 OCR 云通道 Key 注入进程环境（子解析器继承）。 |
| `ensure_gpu_mode` 函数 | 107 | 2 | 本地兜底解析默认走显卡（scnet 失败/低置信回退路径才真正用到）。 |
| `load_cssn_info` 函数 | 112 | 2 | CSSN 体检结果 → 归一号 {标准号: {name, ccs_code, ccs_name}}。 |
| `write_ccs_seed` 函数 | 140 | 4 | 把体检已抓到的 CCS 写成种子文件（fetch_ccs 离线优先命中，免逐本打网络）。 |
| `scan_matching` 函数 | 153 | 2 | 扫目录 PDF，提取标准号并命中 CSSN 已识别集合。 |
| `_classify_text_layer` 函数 | 183 | 3 | 快速文本层判定：与 parse_pdf_with_mineru 用同一个提取函数，口径一致。 |
| `main` 函数 | 201 | 1131 | — |

### `scripts/std_status_check.py`（6 个符号）

> 国标存量状态体检（2026-08-27 改版：openstd 主渠道）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `extract_standard_no` 函数 | 70 | 2 | 从文件名头部提取标准号（如 'GB 1094.1-2013 电力变压器…' → 'GB 1094.1-2013'）。 |
| `looks_like_captcha` 函数 | 79 | 24 | — |
| `_evidence_url` 函数 | 84 | 2 | openstd 行证据链 showInfo:<hcno> → 真实详情页 URL（无则原样返回）。 |
| `probe_one` 函数 | 91 | 2 | 查单号（含被限换 IP 重试）：验证码命中且旋转器可用 → 换 IP + 新 session。 |
| `probe_with_retry` 函数 | 113 | 3 | 查单号状态（退避重试 + 验证码检测），返回可落 jsonl 的结果 dict。 |
| `main` 函数 | 165 | 1131 | — |

### `scripts/std_status_import.py`（2 个符号）

> 国标体检结果回流知识库（2026-08-27）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_norm` 函数 | 28 | 21 | — |
| `main` 函数 | 32 | 1131 | — |

### `scripts/std_status_report.py`（1 个符号）

> 国标体检结果汇总导出（2026-08-26）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 29 | 1131 | — |

### `scripts/survey/00-inventory.py`（7 个符号）

> 检查第 1 步：全仓文件清单（三重账本对账）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `classify` 函数 | 88 | 45 | — |
| `git_ls_files` 函数 | 133 | 2 | — |
| `git_untracked` 函数 | 144 | 2 | — |
| `git_ignored` 函数 | 159 | 2 | 账本丁：被 `.gitignore` 排除、但**确实存在于磁盘上**的路径。 |
| `summarize_ignored` 函数 | 197 | 2 | 把被忽略的路径按「前两级目录」汇总成计数与体积。 |
| `file_record` 函数 | 215 | 2 | — |
| `main` 函数 | 247 | 1131 | — |

### `scripts/survey/01-symbols.py`（8 个符号）

> 检查第 2 步：Python 符号清单 + 引用关系（AST 级，不靠正则）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `iter_py` 函数 | 55 | 6 | — |
| `_first_sentence` 函数 | 68 | 3 | 取 docstring 第一句（跳过 `#` 标题行，按 。 |
| `_sig` 函数 | 83 | 2 | 拼一个人能读的签名（不求完美，求可搜索）。 |
| `_decorators` 函数 | 105 | 3 | — |
| `record_function` 函数 | 115 | 3 | — |
| `scan_file` 函数 | 135 | 2 | — |
| `count_references` 函数 | 201 | 2 | 每个符号名在**扫描面内全部 .py 文本**里出现几次（含定义行本身）。 |
| `main` 函数 | 236 | 1131 | — |

### `scripts/survey/02-surface.py`（7 个符号）

> 检查第 3–7 步：数据形状 / 接口面 / 测试面 / 文档面 / 门禁面。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dump` 函数 | 30 | 51 | — |
| `step3_schema` 函数 | 40 | 3 | — |
| `step4_endpoints` 函数 | 132 | 3 | — |
| `step5_tests` 函数 | 223 | 3 | — |
| `step6_docs` 函数 | 370 | 3 | — |
| `step7_gates` 函数 | 463 | 3 | — |
| `main` 函数 | 509 | 1131 | — |

### `scripts/survey/03-render.py`（21 个符号）

> 检查第 9 步：由 JSON **生成**人可读文档（不手抄）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 44 | 103 | — |
| `cell` 函数 | 51 | 87 | 把任意文本安全放进 markdown 表格单元格。 |
| `mb` 函数 | 71 | 22 | — |
| `write` 函数 | 75 | 406 | — |
| `gen_inventory` 函数 | 82 | 2 | — |
| `gen_code_map` 函数 | 140 | 2 | — |
| `gen_cross_ref` 函数 | 224 | 2 | — |
| `gen_data_shape` 函数 | 284 | 2 | — |
| `gen_api` 函数 | 343 | 2 | — |
| `gen_tests` 函数 | 395 | 2 | — |
| `gen_docs` 函数 | 433 | 2 | — |
| `gen_gates` 函数 | 474 | 2 | — |
| `gen_readme` 函数 | 503 | 2 | — |
| `gen_module_index` 函数 | 574 | 2 | — |
| `gen_config` 函数 | 609 | 2 | — |
| `gen_table_io` 函数 | 641 | 2 | — |
| `gen_test_index` 函数 | 680 | 2 | — |
| `gen_doc_index_content` 函数 | 718 | 2 | — |
| `gen_frontend` 函数 | 747 | 2 | — |
| `gen_function_index` 函数 | 779 | 2 | — |
| `main` 函数 | 824 | 1131 | — |

### `scripts/survey/04-reconcile.py`（2 个符号）

> 检查第 10 步：总对账（九个面各自覆盖到什么程度，可否复核）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 34 | 103 | — |
| `main` 函数 | 41 | 1131 | — |

### `scripts/survey/05-deep.py`（6 个符号）

> 检查第 5 步（深化）：模块职责 / 接口明细 / 配置面 / 表读写关系。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `iter_py` 函数 | 34 | 6 | — |
| `step_modules` 函数 | 48 | 3 | — |
| `step_endpoints_deep` 函数 | 96 | 3 | — |
| `step_config` 函数 | 179 | 3 | — |
| `step_tables_io` 函数 | 262 | 3 | — |
| `main` 函数 | 296 | 1131 | — |

### `scripts/survey/06-content.py`（4 个符号）

> 检查第 6 步（内容层）：测试说了什么 / 文档说了什么 / 前端有什么。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `step_test_content` 函数 | 38 | 3 | — |
| `step_doc_content` 函数 | 85 | 3 | — |
| `step_web_content` 函数 | 145 | 3 | — |
| `main` 函数 | 202 | 1131 | — |

### `scripts/survey/_common.py`（2 个符号）

> 检查器的共用小工具。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `first_sentence` 函数 | 23 | 7 | 取 docstring / 说明文字的第一句。 |
| `dump` 函数 | 53 | 51 | 把一份机器可读数据写进 `docs/survey/data/<name>.json`。 |

### `scripts/survey/run-all.py`（2 个符号）

> 一键重跑：把五个生成器按正确顺序跑到「一致点」。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `run` 函数 | 51 | 282 | — |
| `main` 函数 | 73 | 1131 | — |

### `scripts/uniformity-ast-dupes.py`（16 个符号）

> 跨文件同函数体检测（α-等价）—— 统一化尺子的第 ⑤ 项。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_bound_names` 函数 | 39 | 2 | 收集该函数作用域内**自己绑定**的名字。 |
| `_AlphaNormalizer` 类 | 72 | 2 | 把局部绑定名抹成同一占位符，其余原样保留。 |
| `__init__` 函数 | 75 | 135 | — |
| `visit_Name` 函数 | 78 | 1 | — |
| `visit_arg` 函数 | 83 | 1 | — |
| `visit_FunctionDef` 函数 | 87 | 1 | — |
| `visit_AsyncFunctionDef` 函数 | 91 | 1 | — |
| `visit_ClassDef` 函数 | 95 | 1 | — |
| `_strip_docstring` 函数 | 100 | 2 | — |
| `_body_stmt_count` 函数 | 110 | 3 | 数函数体里真正干活的语句数（不含 docstring）。 |
| `fingerprint` 函数 | 126 | 11 | 返回 α-归一化后的函数体指纹。 |
| `iter_py_files` 函数 | 139 | 2 | — |
| `scan` 函数 | 152 | 180 | 返回 (指纹 -> 出现处列表, 语法错文件列表)。 |
| `cross_file_groups` 函数 | 186 | 3 | 只保留**跨文件**出现的组（同文件多处不算重复实现）。 |
| `_selftest` 函数 | 244 | 4 | — |
| `main` 函数 | 271 | 1131 | — |

### `scripts/verify-answer-citations.py`（2 个符号）

> 能力表（`channel_answers.json`）里的**行号引用校验**哨兵。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_cited` 函数 | 53 | 2 | 该 evidence/note 是否引用过这个行号：`file:N` 或覆盖 N 的 `file:A-B`。 |
| `main` 函数 | 63 | 1131 | — |

### `scripts/verify-engine-uvicorn.py`（4 个符号）

> **在 uvicorn 下**验证引擎（§10.84）——补上"进程内 ASGI 量具"覆盖不到的那一层。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_req` 函数 | 78 | 7 | — |
| `_wait_ready` 函数 | 89 | 2 | — |
| `_make_pdf` 函数 | 101 | 38 | — |
| `main` 函数 | 117 | 1131 | — |

### `scripts/verify-seeds/b1-reingest-e2e.py`（3 个符号）

> B1 的「真机」证据：真引擎 + 真 PDF + **真库副本**，跑一次「重新解析」并确认它仍在原目录。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ro_query` 函数 | 25 | 7 | 只读查询。 |
| `pick_doc` 函数 | 37 | 2 | — |
| `main` 函数 | 62 | 1131 | — |

### `scripts/verify-seeds/b6-faceswitch.patch.py`（1 个符号）

> B6 verify: copy ui-render-shot.mjs and add ONLY a --face switch arg (really clicks the top tabs).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `rep` 函数 | 11 | 358 | — |

### `scripts/verify_highlight.py`（1 个符号）

> 高亮 bbox 离屏验证：把 source_span bbox（**底部原点**，v5 契约）画到 PDF 页，对比框内文本是否是该条款。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `src/core/api/routes_channels.py`（3 个符号）

> 渠道台账端点（§11.0 R2b 只读 + R6d 人工维护）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_new_user_channel_id` 函数 | 38 | 2 | 人工新增的 id：`user:<slug>-<8位hash>`（稳定、可读、可追）。 |
| `_reject_health_and_unknown` 函数 | 50 | 3 | 返回错误说明（None = 通过）。 |
| `register` 函数 | 62 | 42 | — |

### `src/core/api/routes_ingest_preview.py`（2 个符号）

> R27 入库预览（Dry-Run）+ 批量分桶 API 路由——**只读**三端点。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_parse_allow_deep` 函数 | 41 | 4 | 严格取 `allow_deep`：返回 ``(值, 错误消息)``，错误消息非空即应 422。 |
| `register` 函数 | 58 | 42 | — |

### `src/core/api/routes_kb_folders.py`（1 个符号）

> 知识库多级目录 API 路由（KB-FOLDER-PLAN §五第 2 步：**接口接通**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `register` 函数 | 78 | 42 | — |

### `src/core/api/routes_law.py`（1 个符号）

> 官方法规来源 API 路由（2026-08-26，P3-②）：从 server.py create_app 闭包抽出。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `register` 函数 | 29 | 42 | — |

### `src/core/api/routes_materials.py`（2 个符号）

> 材料平面 API 路由（2026-09-17 定位转移 Phase A 第四步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_run_track_l` 函数 | 46 | 2 | 批准后跑 Track L（采到的法规/标准要不要进法条库），**异常也翻成如实结果**。 |
| `register` 函数 | 63 | 42 | — |

### `src/core/api/routes_report.py`（1 个符号）

> 效力报告 API 路由（决策 21 · 用户修订版）：效力报告（只读聚合）+ 材料平面的产出物。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `register` 函数 | 35 | 42 | — |

### `src/core/api/routes_settings.py`（1 个符号）

> 设置模块 API 路由（2026-08-27 立；2026-09-11 改写加密存储）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `register` 函数 | 17 | 42 | — |

### `src/core/api/routes_update.py`（2 个符号）

> 更新模块 API 路由（2026-08-26，P3-②）：从 server.py create_app 闭包抽出。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_upd_error` 函数 | 25 | 14 | UpdateError/KnowledgeStationError → 业务错误响应：。 |
| `register` 函数 | 37 | 42 | — |

### `src/core/api/server.py`（11 个符号）

> FastAPI 服务组装（全量路由）：随机端口 + token 鉴权 + /health + SSE 流式 + 证据/补丁/更新 API。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `bound_threadpool_once` 函数 | 60 | 7 | 把 anyio 默认线程池收窄到 `THREADPOOL_TOKENS`（**按事件循环幂等**。 |
| `_get_heavy_limiter` 函数 | 147 | 8 | 取**本事件循环**的重活闸门（按 loop 缓存：anyio 的 limiter 绑定后端/循环，。 |
| `is_heavy_path` 函数 | 159 | 13 | — |
| `warm_retrieval_stack` 函数 | 165 | 5 | 把检索要用的**两件慢初始化**做掉（**必须在线程里调**，见 §10.94 的调用点）。 |
| `_HeavyGateMiddleware` 类 | 214 | 5 | 重活专用闸门（**纯 ASGI**，不是 `BaseHTTPMiddleware`）。 |
| `__init__` 函数 | 231 | 135 | — |
| `__call__` 函数 | 234 | 12 | — |
| `_clause_number_sort_key` 函数 | 267 | 2 | 条款号自然排序键："5.2.1" → \[5,2,1\]。 |
| `create_app` 函数 | 278 | 43 | — |
| `bind_random` 函数 | 3277 | 5 | 随机空闲端口 + 一次性 token（红线 6）。 |
| `run` 函数 | 3287 | 282 | — |

### `src/core/compliance/gap_analysis.py`（6 个符号）

> R-L11~13 合规差距分析（Phase 7）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `import_internal_policy` 函数 | 33 | 9 | 内部制度文本导入（章节结构切分存入 sections）。 |
| `build_obligations` 函数 | 58 | 10 | 从库内条款构建法定义务清单（legal_obligation），按 clause 去重。 |
| `_keywords` 函数 | 88 | 4 | — |
| `_judge` 函数 | 94 | 2 | — |
| `_suggestion` 函数 | 112 | 2 | — |
| `run_gap_analysis` 函数 | 124 | 7 | 执行差距分析：建 review_task(review_type=gap_analysis) → gap_analysis 落库 → 报告。 |

### `src/core/config.py`（22 个符号）

> 配置中心。敏感值只从「环境变量覆盖 → 引擎加密存储 → 旧系统层兼容」读取，禁止落明文。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_repo_root` 函数 | 26 | 3 | 仓根 —— 从本文件位置算出来（`<仓>/src/core/config.py` ⇒ 往上三级）。 |
| `_default_data_dir` 函数 | 34 | 13 | KS 数据目录 —— **包内优先**，不依赖用户主目录（业主 2026-10-18）。 |
| `_default_models_dir` 函数 | 58 | 6 | 模型目录 —— 同样**包内优先**（`<仓>/var/models/ks`），详见 `_default_data_dir`。 |
| `_read_env_or_registry` 函数 | 77 | 5 | 通用取值链：进程环境变量 → HKCU\Environment（setx 落点）→ default。 |
| `_read_first` 函数 | 91 | 3 | 按顺序逐个走 `_read_env_or_registry`，取第一个非空值（命名空间优先）。 |
| `_read_secret` 函数 | 105 | 17 | 通道取值的**唯一入口**（2026-09-11「不要动系统层」改造后的链条）：。 |
| `_read_api_key` 函数 | 133 | 2 | LLM Key：`KS_LLM_API_KEY` env 覆盖 → 加密存储 → 旧系统层 `DEEPSEEK_API_KEY` 兼容。 |
| `_read_llm_base_url` 函数 | 138 | 2 | — |
| `_read_jev_key` 函数 | 142 | 2 | Jev（TypeSafe System One）Key（2026-09-24）。 |
| `_read_llm_model` 函数 | 153 | 2 | — |
| `_read_llm_max_tokens` 函数 | 157 | 4 | 取证答案的 `max_tokens`（2026-10-19 从硬编码默认值提为可配字段）。 |
| `_read_llm_reasoning_effort` 函数 | 179 | 3 | 思考强度：`low` / `medium` / `high`，空串 = 不传该参数（走上游默认）。 |
| `_read_llm_empty_retries` 函数 | 204 | 3 | 空返回时的重试次数（默认 1 ⇒ 最多试 2 遍）。 |
| `_read_mineru_key` 函数 | 230 | 2 | — |
| `_read_mineru_base_url` 函数 | 234 | 2 | — |
| `_read_mineru_model_version` 函数 | 247 | 7 | 读 MinerU 云模式。 |
| `Settings` 类 | 264 | 14 | — |
| `db_path` 函数 | 297 | 227 | — |
| `models_dir` 函数 | 301 | 16 | 模型权重缓存目录（默认 `<data_dir>/models`）。 |
| `ensure_dirs` 函数 | 321 | 4 | — |
| `get_settings` 函数 | 329 | 188 | — |
| `reset_settings` 函数 | 337 | 111 | 测试用：清理缓存使环境变量生效。 |

### `src/core/domain/models.py`（8 个符号）

> Pydantic 域模型契约（T00 冻结）。对应主计划 v4.3 第 6 节。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `PageGeometryModel` 类 | 30 | 3 | — |
| `SourceSpanModel` 类 | 39 | 16 | — |
| `ClauseRevisionModel` 类 | 48 | 113 | — |
| `DocumentMetaModel` 类 | 117 | 3 | — |
| `EvidenceEdgeModel` 类 | 136 | 3 | — |
| `ReviewPointModel` 类 | 148 | 3 | — |
| `ModalityViolation` 类 | 161 | 8 | — |
| `VerificationResult` 类 | 170 | 6 | — |

### `src/core/exceptions.py`（20 个符号）

> 统一异常体系。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `KnowledgeStationError` 类 | 5 | 239 | 基类。 |
| `__init__` 函数 | 8 | 135 | — |
| `ConfigError` 类 | 13 | 1 | — |
| `__init__` 函数 | 14 | 135 | — |
| `StorageError` 类 | 18 | 5 | — |
| `__init__` 函数 | 19 | 135 | — |
| `DuplicateDocumentError` 类 | 23 | 1 | — |
| `__init__` 函数 | 24 | 135 | — |
| `ParserError` 类 | 28 | 7 | — |
| `__init__` 函数 | 29 | 135 | — |
| `ParserTimeoutError` 类 | 33 | 3 | — |
| `__init__` 函数 | 34 | 135 | — |
| `RetrievalError` 类 | 38 | 1 | — |
| `__init__` 函数 | 39 | 135 | — |
| `VectorEngineOfflineError` 类 | 43 | 7 | — |
| `__init__` 函数 | 44 | 135 | — |
| `LLMError` 类 | 48 | 29 | — |
| `__init__` 函数 | 49 | 135 | — |
| `AuthError` 类 | 53 | 1 | — |
| `__init__` 函数 | 54 | 135 | — |

### `src/core/exports/backlinks.py`（1 个符号）

> 双向溯源（Task 12.2）：条款 → 被谁引用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `query_backlinks` 函数 | 14 | 5 | — |

### `src/core/exports/effect_report.py`（13 个符号）

> 效力报告聚合（决策 21 · 用户修订版，2026-09）：按文件目录分类体系组织的

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_empty_colors` 函数 | 84 | 6 | — |
| `_shift_days` 函数 | 88 | 4 | — |
| `_in_range` 函数 | 92 | 4 | 严格 YYYY-MM-DD 才参与窗口（非法/缺省 → False，诚实不猜）。 |
| `_window_pred` 函数 | 104 | 2 | 窗口谓词工厂（分桶前作用于文档集）。 |
| `_normalize_colors` 函数 | 126 | 6 | color CSV/list → 子集聚合。 |
| `_load_docs` 函数 | 145 | 6 | 单 SELECT 全量可见文档 → resolve + classify（内存纯函数，零 N+1）。 |
| `_collect` 函数 | 167 | 17 | 统一聚合：窗口+色过滤 → (docs, colors_total)。 |
| `_colors_of` 函数 | 180 | 7 | — |
| `_doc_slim` 函数 | 187 | 4 | E2 瘦身行（9 字段）。 |
| `collect_effect_report` 函数 | 196 | 13 | 骨架 + 效力分色统计（tree 到 L4 计数，无文档行——payload 红线见模块头）。 |
| `collect_effect_docs` 函数 | 252 | 11 | 节点明细（瘦身行）：red→yellow→gray→**reference**→green → 标准号升序——问题顶上去。 |
| `collect_effect_by_color` 函数 | 286 | 9 | 全库按色取 top-N 瘦身行（`ks_effect_report` 模型工具的红/黄清单数据源）。 |
| `export_effect_report_xlsx` 函数 | 328 | 5 | 《效力报告》Excel（两 sheet：总览/分类明细全量）到 exports 目录。 |

### `src/core/exports/office_roundtrip.py`（13 个符号）

> Office 往返编辑会话（Task 12.1，v5 P3 体验顺滑 / D3 落地）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_edit_dir` 函数 | 29 | 2 | — |
| `EditSession` 类 | 36 | 5 | — |
| `to_dict` 函数 | 46 | 7 | — |
| `_file_hash` 函数 | 58 | 3 | — |
| `_docx_content_to_text` 函数 | 62 | 2 | docx → (正文纯文本, 表格管道行)。 |
| `_contains_disallowed` 函数 | 78 | 4 | 越界检测：图片/形状/公式对象（简单探测：drawing 元素）。 |
| `_launch_office` 函数 | 96 | 4 | 拉起本机 Word/WPS 打开临时文档（系统文件关联。 |
| `_resize_and_foreground` 函数 | 112 | 2 | 后台线程轮询（最长 ~8s）找到打开了该 docx 的 WPS/Word 主窗口：。 |
| `_force_foreground` 函数 | 168 | 2 | 强制窗口到前台。 |
| `create_edit_session` 函数 | 219 | 6 | 导出条款为临时 docx 并登记会话。 |
| `poll_edit_session` 函数 | 266 | 6 | 轮询保存：mtime/哈希变化 → 白名单解析 → proposed/rejected。 |
| `commit_edit_session` 函数 | 319 | 4 | 确认落库（兼容保留。 |
| `cancel_edit_session` 函数 | 343 | 4 | — |

### `src/core/exports/report_export.py`（3 个符号）

> 导出模块（阶段4）：R19 引用格式化导出 + exports 目录/命名约定。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_exports_dir` 函数 | 26 | 25 | — |
| `_safe_name` 函数 | 32 | 9 | — |
| `build_citation_block` 函数 | 36 | 7 | R19 标准引用代码块（纯文本，供前端一键复制）。 |

### `src/core/exports/research_draft.py`（1 个符号）

> 结论**草稿**（Phase D-5a，§10.96）：系统基于**已批准材料**起草一段结论，**未经用户批准**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `draft_conclusion` 函数 | 57 | 15 | 起草一段结论（**草稿**）。 |

### `src/core/exports/research_report.py`（15 个符号）

> 研究/调研报告导出（Phase D 第一步，2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_exports_dir` 函数 | 53 | 25 | — |
| `_safe_name` 函数 | 60 | 9 | — |
| `_status_marks` 函数 | 64 | 3 | `locator.STATUS_MARKS` 的**惰性**取用（延迟 import：本模块在材料层之上，。 |
| `_material_line` 函数 | 71 | 6 | 参考**材料**条目的一行说明（带两个轴——合成一个"可信度"必错）。 |
| `_attach_locator_status` 函数 | 98 | 7 | 给材料行挂上 `_locator_status`（判据本身不重解析，但**会读一次源文件**。 |
| `_check_citations` 函数 | 131 | 3 | 校验结论里的引用标记（**本函数是唯一判据**）。 |
| `clause_refs` 函数 | 162 | 4 | 文本里出现的**法条**引用编号（`\[\[c:i\]\]`）——**产出侧**判据的唯一所有者（§10.98）。 |
| `assemble_evidence_or_raise` 函数 | 176 | 5 | 装配依据集。 |
| `check_conclusion_citations` 函数 | 201 | 7 | 校验结论文本里的 `\[\[m:i\]\]` 并产出**同一套**警告文案（**判据与措辞的唯一所有者**）。 |
| `build_report_blocks` 函数 | 245 | 12 | 组装报告的**内容块**（`\[(kind, payload)\]`）——**唯一的内容来源**。 |
| `build_research_report` 函数 | 395 | 18 | **内容块 → 两种可交付形态**（Markdown / HTML）。 |
| `write_research_report` 函数 | 412 | 7 | 组装并**落盘**（`.md` + `.html`）。 |
| `_to_markdown` 函数 | 445 | 3 | — |
| `_to_html` 函数 | 466 | 3 | 极简 HTML（**全部转义**，不解析输入里的 HTML——报告是可交付文件，不是网页）。 |
| `track_l_status` 函数 | 492 | 3 | 项目内材料的 Track L 状态（给报告/界面看"哪几条已进法条库"）。 |

### `src/core/exports/xlsx_common.py`（1 个符号）

> xlsx 导出的共用样式与工具（唯一所有者）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `xlsx_header_style` 函数 | 42 | 4 | 给第 `row` 行的前 `cols` 列加表头样式：**加粗 + 浅蓝底 + 垂直居中**。 |

### `src/core/figure_locator.py`（5 个符号）

> 图形区域定位（2026-08-29，GB/T 34406 图1/图A.1/图A.2 实测，语料级通用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_page_lines` 函数 | 29 | 2 | 行级文本收集：\[(y0, y1, x0, x1, dir_y, text)\]，PUA 归一化后。 |
| `locate_figure` 函数 | 49 | 4 | 定位图区。 |
| `locate_middle_figure` 函数 | 99 | 9 | middle.json 兜底（2026-09-01 排版还原 C3）：文字层题注锚定失败时，。 |
| `locate_middle_figure_full` 函数 | 113 | 3 | middle.json 兜底（含几何）：返回 (图片路径, page_no(1-based),。 |
| `locate_middle_caption` 函数 | 184 | 3 | OCR 题注锚定（2026-09-02 C1 统一图对象层第三途径）：题注在 middle.json。 |

### `src/core/figure_redraw.py`（5 个符号）

> 流程图结构化识别与矢量重绘 v2（2026-08-29，GB/T 34406 图1 实测调参，语料级通用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get_ocr` 函数 | 25 | 6 | RapidOCR 惰性单例（模型 ~2s 首载）。 |
| `_render_clip` 函数 | 37 | 2 | clip 区域 300dpi 渲染 → 灰度 ndarray。 |
| `try_redraw` 函数 | 54 | 4 | 对 clip 矩形（fitz.Rect，pt）尝试流程图矢量重绘。 |
| `_esc` 函数 | 222 | 3 | — |
| `_build_svg` 函数 | 227 | 2 | 节点/边 → SVG（pt 坐标）。 |

### `src/core/file_digest.py`（1 个符号）

> 文件级 SHA-256 指纹（唯一实现）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `file_sha256` 函数 | 34 | 10 | 算文件的 SHA-256 十六进制指纹（小写）。 |

### `src/core/formula_locator.py`（5 个符号）

> 公式区域定位（2026-08-29，语料级、零文档特判）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_norm` 函数 | 26 | 21 | NFKC 折叠 + 去空白（全角/半角编号统一）。 |
| `_number_anchor` 函数 | 32 | 2 | 页面上右对齐编号锚 (target) 的 bbox（pt）。 |
| `locate_formula` 函数 | 62 | 4 | 在 page_no（1-based）页定位式(fno) 的 bbox。 |
| `_number_anchor_middle` 函数 | 146 | 1 | middle.json OCR 产物里的右对齐编号锚 (target) bbox（px，MinerU 坐标）。 |
| `locate_eq_by_number` 函数 | 166 | 5 | MinerU 深度解析的独立公式块定位（2026-09-02 全局序策略）。 |

### `src/core/ingestion/bulk.py`（16 个符号）

> 万级批量导入编排器（pipeline/06 + 11 契约落地）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `create_bulk_batch` 函数 | 51 | 26 | 新建 bulk_ingest 批次（running 中批次存在则 409/UPD-2001）。 |
| `load_batch` 函数 | 95 | 23 | — |
| `_reload` 函数 | 109 | 9 | _save_ckpt 刚写完行后的重载——行必存在。 |
| `_batch_status` 函数 | 115 | 4 | 轻量状态读（不做 checkpoint JSON 解析）：供扫描循环高频轮询外部暂停标志。 |
| `_save_ckpt` 函数 | 127 | 17 | 落 checkpoint（可选改状态）。 |
| `_extract_first_page` 函数 | 159 | 4 | PyMuPDF 提取 → (标准号, 名称)。 |
| `_process_pdf` 函数 | 198 | 5 | 单个文件的快扫处理（供线程池并发调用）。 |
| `_known_files` 函数 | 256 | 2 | 既有文档的 (文件大小, 内容哈希) 二元组指纹集（严格防重口径，文件名不参与）。 |
| `fast_scan` 函数 | 272 | 27 | 阶段一：快扫目录建清单（线程池并发，默认 scan_concurrency=2）。 |
| `_write_item_state` 函数 | 349 | 4 | 写队列项的处理状态（走入库侧那一个出口，见 ``pipeline._write_filing_state``）。 |
| `_placeholder_still_there` 函数 | 361 | 4 | 这一项对应的**快扫占位行**还在吗（= 这一项是本次导入自己的占位）？。 |
| `parse_loop` 函数 | 385 | 11 | 逐件调 run_full_ingest。 |
| `pause_batch` 函数 | 463 | 18 | — |
| `abort_batch` 函数 | 473 | 10 | 终止批次（人工清场出口）：pending/running/paused → failed(pause_reason=aborted_by_user)。 |
| `_unscanned_remaining` 函数 | 496 | 2 | R-A：判断扫描目录是否还有未扫文件（现场重列，兼容中断期间新增/删减）。 |
| `resume_batch` 函数 | 506 | 29 | 恢复批次（R-A 语义）：还有未扫文件（paused=扫描中断）→ 先续跑 fast_scan。 |

### `src/core/ingestion/deep_server.py`（18 个符号）

> 常驻深度解析服务（GPU 攒批，2026-08-27）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_job_dir` 函数 | 43 | 13 | — |
| `_heartbeat_path` 函数 | 50 | 2 | 按实例心跳：server-{pid}.json（v5 多 daemon 并存，各自写各自的心跳）。 |
| `_server_alive` 函数 | 55 | 2 | — |
| `_alive_count` 函数 | 59 | 7 | 新鲜心跳的 daemon 数（供多实例目标数判断）。 |
| `_target_workers` 函数 | 75 | 3 | 常驻 daemon 目标数。 |
| `_start_server` 函数 | 85 | 4 | 拉起常驻 daemon（脱离父进程组，随客户端崩溃不连坐）。 |
| `_ensure_server` 函数 | 106 | 4 | 确保常驻 daemon 达到目标数（跨进程单飞）。 |
| `_wait_first_heartbeat` 函数 | 152 | 4 | spawn 后等首个心跳（daemon 首跳前 alive_count=0，会造成超额 spawn）。 |
| `_pid_alive` 函数 | 161 | 2 | 跨平台进程存活探测（孤儿识别用：提交者死了 = 任务无人收割）。 |
| `deep_server_submit` 函数 | 186 | 7 | 只提交不等待（预投递用）：把 PDF 任务写进队列立即返回句柄。 |
| `deep_server_wait` 函数 | 207 | 11 | 等待一个已提交任务的结果（与提交解耦，支持先投递后收割的流水线）。 |
| `deep_server_submit_and_wait` 函数 | 243 | 12 | 提交一个深度任务并等待结果（旧接口，保留给逐本兜底路径）。 |
| `_cleanup` 函数 | 254 | 6 | — |
| `server_main` 函数 | 266 | 4 | — |
| `_try_claim` 函数 | 304 | 2 | 任务文件抢占：非阻塞锁住首字节，抢到返回句柄（保持锁），抢到失败 None。 |
| `_collect_jobs` 函数 | 325 | 5 | — |
| `_run_batch` 函数 | 382 | 2 | — |
| `_mark_error` 函数 | 487 | 8 | — |

### `src/core/ingestion/docx_adapter.py`（3 个符号）

> docx 一等公民入库适配器（Task 11.1，v5 P2 入库便利）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `word_com_available` 函数 | 17 | 2 | — |
| `docx_to_pdf_via_com` 函数 | 25 | 6 | COM 转 PDF（Word FileFormat=17 / WPS 兼容探测）。 |
| `parse_docx_text` 函数 | 71 | 5 | 降级路径 (b)：python-docx 提取大纲 → 条款切分（无 bbox）。 |

### `src/core/ingestion/docx_ingest.py`（2 个符号）

> docx 入库入口（Task 11.1）：COM 转 PDF 走完整管线（有 bbox）；无 Word 走降级直解。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `run_docx_ingest` 函数 | 22 | 13 | docx 入库：优先 COM 转 PDF → run_full_ingest。 |
| `main` 函数 | 77 | 1131 | — |

### `src/core/ingestion/dry_run.py`（10 个符号）

> R27 入库预览报告（Dry-Run）+ 决策 2 批量分桶——**只读**实现。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_parse_lock` 函数 | 85 | 2 | 取 `tmp_dir` 对应的分片锁（同一目录 → 同一把。 |
| `_sha256_file` 函数 | 91 | 5 | — |
| `_looks_like_pdf` 函数 | 99 | 2 | 按**内容魔数**判定是不是 PDF（不是只看扩展名）。 |
| `_dup_probe` 函数 | 115 | 5 | 只读查重（语义镜像 `run_full_ingest`）。 |
| `_identity_guess` 函数 | 133 | 2 | 标准号/名称猜测：复用既有唯一所有者（`bulk._extract_first_page` + `auto_tag`）。 |
| `analyze_preview_report` 函数 | 163 | 48 | 生成 R27 入库预览报告。 |
| `_finalize` 函数 | 411 | 5 | 统一收尾：补 elapsed、一行摘要，并在 status=error 时强制走 verdict 判据。 |
| `scan_preview_dir` 函数 | 426 | 18 | 列出目录下的候选 PDF（字典序，确定性）。 |
| `_stride_sample` 函数 | 437 | 2 | 确定性等距抽样（不用随机，便于测试精确断言与复现）。 |
| `preview_batch` 函数 | 450 | 19 | 批量 Dry-Run（决策 2：总账分桶 ✅/⚠️/❌，⚠️ 集中处理。 |

### `src/core/ingestion/law_text.py`（6 个符号）

> 法条文本直灌通道（阶段3 新增，依据业主输入：法律法规以网页纯文本发布，基本无扫描版）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_strip_law_front_matter` 函数 | 49 | 9 | 剥掉法规正文之前的**文件头**（标题/立法沿革/`<!-- INFO END -->`）。 |
| `split_gb_text` 函数 | 78 | 13 | 按 GB 风格条款号（3.1 / 4.2 / A.1）切分标准文本。 |
| `split_law_text` 函数 | 100 | 30 | 按'第X条'切分法规文本。 |
| `split_law_enum_text` 函数 | 132 | 11 | 按「一、二、三、」切分法规文本（**部分司法解释/规定不用「第X条」**）。 |
| `ingest_law_text` 函数 | 167 | 55 | 法规纯文本 → 切分 → 分型 → 单事务原子入库（无源 PDF，file_path 记录来源标记）。 |
| `main` 函数 | 375 | 1131 | — |

### `src/core/ingestion/material_ingest.py`（15 个符号）

> 材料解析与切片（2026-09-17 定位转移 Phase A 第二步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `scan_project_dir` 函数 | 39 | 4 | 列出项目参考资料文件夹里受支持的文件（按名排序，结果稳定）。 |
| `_pkg_version` 函数 | 48 | 4 | 包的**分发名**取版本（取不到就 `unknown`——不编造）。 |
| `_provenance_fingerprint` 函数 | 57 | 9 | **决定这段派生文本的解析器身份**（引用锚点稳定性的判据，方案 §12 未决第 5 条）。 |
| `_fingerprint_field` 函数 | 85 | 2 | 从解析器指纹里回读一个 `k=v` 字段。 |
| `extract_pages_with_provenance` 函数 | 99 | 8 | `(页文本, 解析器指纹)`。 |
| `extract_pages` 函数 | 133 | 11 | 解析成 `\[(page_number, page_text)\]`（**薄包装**，保留既有调用点与测试）。 |
| `_short_hash` 函数 | 148 | 2 | — |
| `file_hash` 函数 | 152 | 164 | 文件内容 SHA-256（用于查重：同一份材料重复放进来不应重复登记）。 |
| `text_hash` 函数 | 161 | 6 | **派生全文**的 SHA-256（引用锚点稳定性的判据之一，见 `materials/locator.py`）。 |
| `build_document` 函数 | 175 | 13 | 把 `\[(page, text)\]` 拼成**规范全文**，并给出每页在全文中的字符区间。 |
| `page_of` 函数 | 195 | 14 | 字符偏移 → 页号。 |
| `_require_positive_max_chars` 函数 | 212 | 4 | `max_chars` 的**唯一**校验点（参数规则的单一所有者）。 |
| `chunk_text` 函数 | 223 | 23 | 按**段落**聚合成块，保留全文绝对字符区间与页号。 |
| `ingest_material_file` 函数 | 288 | 37 | 把一个文件登记为材料（**默认 pending**）+ 建切片。 |
| `ingest_project_dir` 函数 | 377 | 7 | 收件箱式入库：把项目参考资料文件夹里的受支持文件逐份登记（单份失败不中断整批）。 |

### `src/core/ingestion/middle_locator.py`（2 个符号）

> middle.json 产物定位的统一模式契约（2026-09-14 立）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `iter_middle_files` 函数 | 34 | 8 | 按 MIDDLE_PATTERNS 顺序产出 root 下的 middle 产物文件。 |
| `find_middle_files` 函数 | 52 | 28 | iter_middle_files 的列表版（多数消费者用列表）。 |

### `src/core/ingestion/middle_schema.py`（7 个符号）

> MinerU middle 产物的**结构归一**与未知形状的**大声报错**（2026-10-07 立）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MiddleSchemaError` 类 | 55 | 20 | middle 产物结构无法识别（既不是 3.4 也不是 4.0），或读盘/解析失败。 |
| `_as_text` 函数 | 62 | 19 | 4.0 的 ``content`` 有时候是字符串、有时候是对象列表、还可能**嵌套**。 |
| `detect_schema` 函数 | 77 | 10 | 识别 middle 产物的结构版本。 |
| `_spans_of` 函数 | 98 | 4 | 4.0 的 ``content`` 列表 → 3.4 的 ``lines\[\].spans\[\]``。 |
| `_convert_40_to_34` 函数 | 115 | 6 | MinerU 4.0 结构 → 3.4 结构（``load_middle_items`` 直接可消费）。 |
| `normalize_middle` 函数 | 252 | 37 | 把 middle 产物归一成 3.4 形状（``pdf_info`` 顶层键）。 |
| `load_middle_json` 函数 | 266 | 18 | 读 middle 产物文件并归一成 3.4 形状。 |

### `src/core/ingestion/mineru_adapter.py`（15 个符号）

> MinerU (magic-pdf) 版面解析适配器 + PyMuPDF 几何提取（T03'）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `extract_page_geometries` 函数 | 31 | 4 | 提取每页 PDF 的 Point 宽高、旋转角、CropBox、MediaBox（PyMuPDF）。 |
| `_extract_text_blocks` 函数 | 57 | 5 | PyMuPDF 文本块（含 bbox，已转 PDF 左下原点坐标系）。 |
| `_clean_blocks` 函数 | 99 | 3 | 通用二次清洗（2026-08-29，语料级，GB/T 34406-2017 实测）：。 |
| `_reflow_block` 函数 | 133 | 2 | 对单个 block 的 text 应用行级重排。 |
| `_latin_prose_signals` 函数 | 170 | 10 | 判据四的两个量：`(字母/(字母+标点), 像词串占比)`。 |
| `_looks_unlike_latin_prose` 函数 | 188 | 8 | 这段文字**像不像正常的拉丁文散文**？（不像 ⇒ 倾向判乱码）。 |
| `text_layer_pua_mangled` 函数 | 213 | 30 | 文本层是否为 PUA 错位字体（不可用于条款切分，必须走像素 OCR）。 |
| `_is_weird_char` 函数 | 294 | 5 | 异常区字符：不属于 ASCII/常用汉字/中文标点/常用符号 的字符。 |
| `mineru_available` 函数 | 313 | 14 | — |
| `_gpu_deep_lock` 函数 | 329 | 12 | 跨进程 GPU 排队锁：16GB 显存只容一路 MinerU 深度管线，并发分片。 |
| `_cloud_enabled` 函数 | 376 | 2 | 云解析通道是否可用（2026-09-08 用户修订后的语义）。 |
| `_local_backend` 函数 | 390 | 3 | 本地深度通道的 MinerU backend。 |
| `_pipeline_allowed` 函数 | 408 | 2 | 本次调用是否允许 pipeline 通道（KS_VLM_ONLY=1 时一律不允许）。 |
| `_mineru_deep_analyze` 函数 | 414 | 9 | 深度版面分析（2026-09-08 用户修订：**云优先 → 本地兜底**）。 |
| `parse_pdf_with_mineru` 函数 | 492 | 8 | 标准化解析入口（Parser Worker 子进程中执行）。 |

### `src/core/ingestion/mineru_cloud.py`（16 个符号）

> MinerU 云解析后端（云优先通道；2026-09-01 架构反转，2026-09-08 通道优先级修订）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MineruCloudError` 类 | 38 | 32 | 云解析后端错误（配置/协议/产物守卫失败——大声报错不静默）。 |
| `_resolve_settings` 函数 | 42 | 5 | — |
| `_model_version` 函数 | 50 | 6 | MinerU 云模型版本（2026-09-15 设置项）：pipeline（默认）/ vlm / MinerU-HTML。 |
| `mineru_cloud_available` 函数 | 75 | 5 | (可用?, Base URL 或未配置原因)。 |
| `_headers` 函数 | 85 | 35 | — |
| `_check_api_payload` 函数 | 90 | 4 | — |
| `probe_token` 函数 | 98 | 12 | 活体探测：申请一次签名上传 URL 验证 token（不上传、不启动解析任务）。 |
| `_apply_upload_url` 函数 | 149 | 12 | — |
| `_poll_result` 函数 | 169 | 8 | — |
| `_download_zip` 函数 | 204 | 7 | — |
| `_safe_extract` 函数 | 227 | 9 | 解压（防 zip-slip：每项 resolve 后必须落在 dest 内）。 |
| `_validate_middle` 函数 | 239 | 16 | schema 守卫：云产物 middle.json 必须与本地同构（大声报错不静默）。 |
| `_find_middle` 函数 | 270 | 3 | — |
| `_normalize_landing` 函数 | 287 | 9 | 云产物归一化落位为本地 deep 同构布局。 |
| `_record_egress_safe` 函数 | 317 | 8 | 外发审计登记（红线：云调用必走 egress_audit）。 |
| `mineru_cloud_submit_and_wait` 函数 | 335 | 19 | 云解析全流程（与 deep_server_submit_and_wait 同构语义）。 |

### `src/core/ingestion/parser_worker.py`（2 个符号）

> Parser Worker 隔离（v4.3 第 8.2 节）：MinerU 在独立子进程运行，崩溃不污染主进程。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_parser_worker_main` 函数 | 12 | 2 | — |
| `run_parser_isolated` 函数 | 36 | 44 | 启动子进程解析。 |

### `src/core/ingestion/pipeline.py`（38 个符号）

> T05 完整入库管线：MinerU 深度解析 → middle.json 结构化 → E1-E7 切分

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_frag_key` 函数 | 81 | 2 | 家具片段的比较键 = `号-年`（与 `text_utils.standard_key` 同口径的**号+年**部分）。 |
| `_own_key_of` 函数 | 92 | 10 | 本文档标准号的比较键。 |
| `_middle_cover_blocks` 函数 | 118 | 5 | 2026-09-01（GB/T 24276 实测）扫描版封面日期兜底：扫描 PDF 的 fitz。 |
| `_is_index_entry` 函数 | 222 | 7 | 该块是否像**索引条目**（≥2 行「词条 + 点线 + 小数页码」）。 |
| `_is_toc_entry` 函数 | 231 | 20 | 该块是否为目录条目（点线 + 页码尾，或 ≥2 行「条款号 + 页码尾」）。 |
| `_plausible_clause_head` 函数 | 276 | 32 | E8：判断匹配到的条款号是否是真实条款头（而非表格数值行）。 |
| `_num_segments` 函数 | 332 | 12 | 号 → 可比较段元组。 |
| `_is_continuation_head` 函数 | 350 | 42 | 判断匹配到的号是否是「续行/交叉引用」而非真条款头（2026-09-15）。 |
| `_is_leader_run` 函数 | 393 | 12 | 纯引点填充块判定（索引行特有）。 |
| `_plausible_appendix_head` 函数 | 404 | 16 | 2026-09-13 附录版 E8 闸门：字母章号 "A.1" 的三道防误切护栏。 |
| `_std_type` 函数 | 432 | 7 | 2026-08-29 入库推断 standard_type：此前从不传 → 全库默认 'mandatory'，。 |
| `_hier_from_no` 函数 | 444 | 16 | 2026-08-29 从标准号推导效力层级：此前调用方从不传 → 全库默认 'GB'，。 |
| `MidItem` 类 | 459 | 93 | middle.json 归一化条目（阅读顺序）。 |
| `_spans_rows` 函数 | 481 | 6 | 行级提取底座（2026-09-01 B5）：\[(行文本, 行bbox\|None), ...\]。 |
| `_spans_rows_scored` 函数 | 493 | 5 | _spans_rows 的带分底座：额外收集行内 span score 的 min（2026-09-14。 |
| `_spans_text` 函数 | 541 | 7 | 提取文本块内容（2026-09-01 修假行界 bug：行界=line，行内 span 无缝拼接）。 |
| `_is_figure_legend` 函数 | 570 | 13 | 图例块（标引序号说明 + 'N——标签' 编号清单）判定（2026-09-15 立）。 |
| `_legend_follows_image` 函数 | 589 | 9 | 几何判据：图例块紧邻图（上下任一方向），且横向有交叠。 |
| `load_middle_items` 函数 | 607 | 68 | 解析 middle.json → 阅读顺序条目 + 每页尺寸。 |
| `SplitClause` 类 | 716 | 18 | — |
| `_rows_of` 函数 | 732 | 14 | 文本块 → (行, 页号, 行bbox) 行级序列（B3 页界 / B5 行级高亮数据源）。 |
| `_strip_foreign_frag` 函数 | 743 | 5 | 家具片段剥离（`页码 + 标准号`）的**唯一实现**（2026-09-17 收敛）。 |
| `split_items_into_clauses` 函数 | 759 | 82 | E1-E7 切分主逻辑。 |
| `strip_figure_legend_segment` 函数 | 1138 | 19 | 切掉条款文本里的**图例段**（「标引序号说明」及其条目）。 |
| `_strip_headerless_legend` 函数 | 1204 | 2 | 切掉**无头图例**：条目贴在图题上或紧随图题，没有 `标引序号说明：` 之类的头。 |
| `build_clause_models` 函数 | 1275 | 33 | 切分结果 → Pydantic 模型 + 证据图边（raw，source/target 用条款号表示）。 |
| `resolve_edges` 函数 | 1478 | 7 | 把 raw_edges 解析成可落库的证据边元组（`(edge_type, src_id, dst_id, conf, status)`）。 |
| `analyze_preview` 函数 | 1518 | 10 | R27 入库预览 Dry-Run（Task 11.5）：解析但不落库，输出切分/分型/质量预览。 |
| `load_middle_items_from_blocks` 函数 | 1568 | 12 | blocks（PyMuPDF 文本块）→ MidItem（供 split_items_into_clauses）。 |
| `_cell_html` 函数 | 1621 | 5 | 单元格 HTML：按字形渲染——同视觉行 span 按基线聚类（PDF 常把 '0.43'。 |
| `_grid_html` 函数 | 1748 | 2 | find_tables 表 → 带 rowspan/colspan 的 1:1 HTML 网格。 |
| `_extract_vector_table_items` 函数 | 1805 | 8 | 文本层快路径的表格网格重建（2026-08-28 用户实证驱动）。 |
| `_merge_table_items` 函数 | 1897 | 5 | 表格 MidItem 按阅读顺序落位：仅对含表格的页做位置排序。 |
| `_cached_parse_result` 函数 | 1919 | 2 | 从既有解析产物重建 run_parser_isolated 的等价 result（**零 OCR**）。 |
| `_filing_confidence` 函数 | 1968 | 5 | 入库时算**识别率**（= ``doc_filing_state.confidence``）。 |
| `_write_filing_state` 函数 | 1999 | 16 | 把处理状态写进 ``doc_filing_state``（**入库侧的唯一出口**）。 |
| `run_full_ingest` 函数 | 2021 | 86 | — |
| `main` 函数 | 2420 | 1131 | — |

### `src/core/ingestion/preview_jobs.py`（9 个符号）

> 异步批量预览（全量万级）——进程内任务表 + 三端点（2026-09-12 施工，L239 设计）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_prune_jobs_locked` 函数 | 41 | 2 | 保留最近 _JOBS_KEEP 个任务（terminal 的旧任务先淘汰）。 |
| `create_job` 函数 | 54 | 16 | 创建异步预览任务并立即返回（worker 后台跑）。 |
| `_worker` 函数 | 95 | 12 | 后台 worker：逐件预览，单件失败不中断。 |
| `_candidate_paths` 函数 | 158 | 2 | — |
| `abort_job` 函数 | 162 | 4 | 协作式中断：置 stop_flag。 |
| `_zombie_check` 函数 | 174 | 2 | 僵尸自愈（照 announce.py 口径）：登记 running 而线程已死 → 标 failed。 |
| `get_job` 函数 | 195 | 8 | 读任务状态 + 进度 + 瘦身行分页（万级行表不能一次全量回）。 |
| `_public_view` 函数 | 205 | 7 | 瘦身视图：不带 thread_ref/stop_flag 等内部字段。 |
| `_reset_for_tests` 函数 | 231 | 3 | 测试隔离：清空进程内任务表与暂存路径。 |

### `src/core/ingestion/pypdf_backfill.py`（7 个符号）

> OCR 数字回填（R58 补丁机制）：MinerU 对部分 PDF 的文本层数字提取失败

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_is_terminator` 函数 | 46 | 6 | 该行是否终止当前条款的归并（结构标记/页眉/水印）。 |
| `_pypdf_available` 函数 | 52 | 7 | — |
| `pypdf_page_clauses` 函数 | 64 | 6 | pypdf 提取指定页文本 → 按行首条款号切分 {number: text}。 |
| `_digits` 函数 | 112 | 5 | — |
| `_reindex_fts` 函数 | 116 | 3 | 把补丁后的正文同步进 `clause_fts`（**只 FTS，不碰向量**）。 |
| `backfill_document` 函数 | 137 | 11 | 对单个文档执行回填，返回打补丁条数。 |
| `backfill_all` 函数 | 229 | 4 | 扫描全部含 PDF 原件的文档执行回填。 |

### `src/core/ingestion/reingest.py`（6 个符号）

> 「重来一次」——把**已经在库里的**文件重新解析一遍（KB-FOLDER-PLAN 第 4 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_now` 函数 | 48 | 13 | — |
| `plan_reingest` 函数 | 52 | 7 | **只读**：这一批里哪些能重来、哪些不能（各自为什么）。 |
| `_run` 函数 | 92 | 73 | 后台线程：串行重导每一篇。 |
| `_write_failed` 函数 | 132 | 3 | — |
| `start_reingest` 函数 | 137 | 5 | 起一批「重来一次」：写 ``recognizing`` + 起后台线程，**立刻**返回。 |
| `reingest_status` 函数 | 171 | 6 | 最近一批「重来一次」的进度（**如实**：running/total/done + 逐篇结果）。 |

### `src/core/ingestion/smoke_ingest.py`（4 个符号）

> 冒烟入库脚本（第一阶段造数据用，完整 E1-E7 管线在 T05）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `split_into_clauses` 函数 | 35 | 2 | 极简条款切分: 以条款号开头的文本块开启新条款，其余并入当前条款。 |
| `_classify` 函数 | 54 | 13 | 冒烟分型：值域与 ClauseRevisionModel Literal 对齐（modality 词表 = MODALITY_STRENGTH 键）。 |
| `ingest_pdf` 函数 | 65 | 4 | — |
| `main` 函数 | 150 | 1131 | — |

### `src/core/ingestion/span_calibration.py`（14 个符号）

> span 坐标系通用自动校准（R-B，pipeline/13-round3.md）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `page_line_centers` 函数 | 28 | 5 | fitz words 按 y 聚类成行，返回每行中心 y（顶部原点，升序）。 |
| `_vote_from_centers` 函数 | 51 | 3 | 给定行中心表的投票内核：bbox 中心直读 vs H−y 换算，距最近文字行近者胜。 |
| `vote_origin` 函数 | 64 | 11 | bbox 中心两种解释（直读 / H−y）各找最近文字行距离，近者胜。 |
| `band_text_hit` 函数 | 69 | 4 | 带内文字真值最终裁决 v3（2026-08-25）：。 |
| `_flip_bbox` 函数 | 87 | 6 | 顶部原点 → 底部原点：y'=H−y（端点交换）。 |
| `_span_get` 函数 | 93 | 16 | — |
| `_span_set` 函数 | 99 | 2 | — |
| `_vote_spans` 函数 | 106 | 2 | 全量 span 逐条投票（页级缓存行中心表/页高），返回 (行中心表, 页高, top 票, bottom 票)。 |
| `_stratified_sample` 函数 | 127 | 4 | 均匀分层采样（前/中/后全覆盖），cap 封顶。 |
| `_direction_votes` 函数 | 136 | 3 | 同页多 span 条款的"阅读方向"判别（**无镜像对称**，v2 通解）：。 |
| `_text_evidence` 函数 | 165 | 4 | 带内文字真值统计（镜像不对称的强证据）：。 |
| `_decide_origin` 函数 | 198 | 2 | 三层组合判定 → (verdict, stats)。 |
| `calibrate_new` 函数 | 225 | 19 | 纯函数版校准（不落库）：入库前对内存中 span 列表文档级判定并归一为底部原点。 |
| `calibrate` 函数 | 261 | 13 | 存量校准：读该 doc 全部 span → 逐条 vote 文档级多数决 → 顶部原点则全量翻转。 |

### `src/core/ingestion/span_verify.py`（4 个符号）

> span 坐标入库体检（2026-08-26 新增，P1-③）：

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_db` 函数 | 31 | 11 | — |
| `verify_doc` 函数 | 38 | 5 | 抽样验证单文档 span 坐标系。 |
| `verify_library` 函数 | 80 | 3 | 全库体检：返回每个有 span 文档的验证结果（含 top_suspect 标记）。 |
| `main` 函数 | 101 | 1131 | — |

### `src/core/knowledge/alias_extract.py`（6 个符号）

> 别名/大白话反查（Phase 6：R48）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_alias_clean` 函数 | 21 | 9 | alias 是否为可用的干净大白话（2-8 字纯中文、无虚词/动词碎片）。 |
| `_term_section_span` 函数 | 63 | 6 | 定位**术语章节**的行区间 `\[start, end)`。 |
| `_term_key` 函数 | 95 | 1 | — |
| `extract_terms_from_text` 函数 | 99 | 15 | 从含"术语和定义"章节的文本抽取术语行 → alias_store（幂等 UPSERT）。 |
| `_core_nouns` 函数 | 197 | 6 | 定义中 2-6 字名词候选（去虚词/动作词开头），作 alias 集合。 |
| `expand_with_alias` 函数 | 245 | 20 | 检索扩展：query 中含 alias → 追加对应标准 term（供 FTS OR 扩展）。 |

### `src/core/knowledge/auto_tag.py`（4 个符号）

> 入库自动标签管线（Task 11.3，v5 P2 入库便利）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `AutoTags` 类 | 34 | 4 | — |
| `_normalize_eff` 函数 | 43 | 2 | — |
| `auto_tag` 函数 | 54 | 41 | 对文档封面/前言文本打标签（只产出元数据，调用方负责落 doc_meta）。 |
| `apply_tags_to_doc_meta` 函数 | 87 | 6 | 标签落 doc_meta（红线：绝不触碰 clause_revision 原文）。 |

### `src/core/knowledge/ccs_backfill.py`（17 个符号）

> 「补全分类号」——插件**自己**把没有 CCS 的文件补齐（2026-09-22，业主口径）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_now` 函数 | 114 | 13 | — |
| `_db_path` 函数 | 118 | 8 | 把调用方给的 ``db_path`` 规整成 ``Path``（``None`` 原样返回 = 用配置里的默认库）。 |
| `plan_ccs_backfill` 函数 | 140 | 5 | **只读**：这一批要补哪些篇。 |
| `missing_ccs_count` 函数 | 186 | 8 | 全库还有几篇标准没有分类号（界面显示"待补 N 篇"用。 |
| `missing_ccs_split` 函数 | 194 | 6 | **"还剩几篇"拆开说**（业主点名第②条的诚实性要求。 |
| `_is_network_exc` 函数 | 240 | 2 | 这个异常是不是**传输层**的（决定落台账时算不算"网络失败"）。 |
| `classify_backfill_exception` 函数 | 248 | 3 | 一个异常 ⇒ **落库的 outcome** + 记流水的一行（复核 MED-1：按类型如实归类）。 |
| `_paginate` 函数 | 283 | 2 | 把整批切成**一页 ``MAX_BACKFILL_DOCS`` 篇**（「全部补完」按页串行跑）。 |
| `_wait_between` 函数 | 295 | 2 | 每篇之间歇一下（``pause_s`` 显式给了就用它。 |
| `_run` 函数 | 309 | 73 | 后台线程：**分页串行**补每一篇（状态写 ``_PROGRESS`` + ``doc_ccs_state``）。 |
| `_decide_stop_reason` 函数 | 429 | 9 | **为什么停**（取**一个**值，按优先级。 |
| `_update_counts` 函数 | 453 | 6 | — |
| `_release` 函数 | 460 | 8 | — |
| `_reset_progress` 函数 | 467 | 2 | — |
| `start_ccs_backfill` 函数 | 483 | 33 | 起一批「补全分类号」：**立刻**返回，进度看 :func:`ccs_backfill_status`。 |
| `cancel_ccs_backfill` 函数 | 557 | 4 | 按"停"：置中断标志（线程在**每篇之间**检查）。 |
| `ccs_backfill_status` 函数 | 569 | 22 | 最近一批的进度（**如实**：running/done/total + 逐篇结果 + 失败清单 + 为什么停）。 |

### `src/core/knowledge/ccs_fetcher.py`（28 个符号）

> 入库/补全时查询中国标准分类号（CCS）——**一条链、来源有序、每条都记来源**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_LayerFacts` 类 | 112 | 8 | 一层网络查询跑完后的三个事实（**结论由这三个事实算出来，不靠猜**）。 |
| `__init__` 函数 | 125 | 135 | — |
| `merge_into` 函数 | 130 | 2 | 把本层的事实并进一个**跨层**的累计器（结论在累计器上算一次）。 |
| `_combine_verdict` 函数 | 137 | 3 | 两层网络查询的**全部事实**合成**一个**如实的总结论。 |
| `_seed_key` 函数 | 181 | 5 | 种子键归一（与 std_bulk_import.write_ccs_seed 同一约定）。 |
| `_load_ccs_seed` 函数 | 186 | 2 | 懒加载种子文件。 |
| `_read_seed` 函数 | 205 | 3 | — |
| `clean_standard_no` 函数 | 250 | 3 | 从字段开头抠出**标准号那一段**（去掉尾部杂字）。 |
| `looks_like_standard_no` 函数 | 272 | 5 | 这个字段**像不像一个标准号**？。 |
| `keyword_forms` 函数 | 284 | 11 | 标准号 → **有序**的 ``\[(形式名, 关键词, 匹配目标)\]``（去重且去掉空串）。 |
| `_major_from_code` 函数 | 352 | 2 | CCS 代码首字母 → 大类字母（P16 → P）。 |
| `_split_ccs` 函数 | 357 | 3 | ``"K41变压器"`` → ``("K41", "变压器")``。 |
| `_lookup_dict` 函数 | 369 | 6 | 统一的结果字典（``fetch_ccs`` 的返回形状 = 旧字段 + 来源字段，**只增不改**）。 |
| `empty_lookup` 函数 | 397 | 4 | 没命中时的结果（``found=False``）——**必须**带 outcome 与逐层尝试记录。 |
| `_pick_row` 函数 | 411 | 15 | 按**归一化标准号**精确挑选匹配行。 |
| `_layer_official_api` 函数 | 434 | 2 | ① 官方 JSON 接口：多形式依次试，每形式按归一号精确挑。 |
| `_rows_of` 函数 | 498 | 14 | JSON 应答 → 结果行列表。 |
| `_should_pace` 函数 | 508 | 3 | 两次请求之间该睡多久（0 = 不睡）。 |
| `_pace` 函数 | 525 | 17 | 按上面的规则睡一次（唯一的 sleep 出口）。 |
| `_parse_html_items` 函数 | 545 | 5 | HTML 列表页 → ``\[{"a100", "a298", "ccs"}\]``（按 ``ph_list_title`` 的标准号切块）。 |
| `_layer_web_scrape` 函数 | 568 | 2 | ② 网页抓取：同样多形式依次试，按**归一号精确挑选**条目（事实交回调用方合并）。 |
| `_layer_local_table` 函数 | 630 | 2 | ③a 人工核实表（``LOCAL_CCS``）。 |
| `_layer_seed_file` 函数 | 647 | 2 | ③b 种子文件（``KS_CCS_SEED_FILE``。 |
| `resolve_ccs` 函数 | 670 | 69 | **三层有序链**查 CCS，返回统一结果字典（**永远带 outcome 与逐层尝试记录**）。 |
| `_default_transport` 函数 | 736 | 6 | 默认传输 = 渠道层的唯一所有者（curl_cffi 优先、httpx 兜底且带自检）。 |
| `_reason_text` 函数 | 747 | 2 | 给界面/审计用的一句人话（说清"为什么没有这一篇的分类号"）。 |
| `fetch_ccs` 函数 | 767 | 4 | 按标准号查询 CCS。 |
| `ccs_to_tag` 函数 | 782 | 16 | CCS 结果 → domain_tags 条目（"CCS:P16 工程防火"）。 |

### `src/core/knowledge/ccs_store.py`（11 个符号）

> CCS（中国标准分类号）查询台账的读写层（2026-09-22「补全分类号」）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_err` 函数 | 49 | 62 | — |
| `ccs_tag_of` 函数 | 53 | 8 | ``domain_tags``（JSON 串或 list）里已有的 ``CCS:…`` 条目。 |
| `_as_list` 函数 | 62 | 5 | ``domain_tags`` 统一成 list（库里是 JSON 字符串。 |
| `_as_list_for_write` 函数 | 79 | 3 | **写路径**的严格版：非空却不是 JSON 数组 ⇒ **抛，拒改**（复核 F4，2026-09-24）。 |
| `record_ccs_lookup` 函数 | 106 | 16 | 把一次查询的结论写进台账（幂等 upsert）。 |
| `apply_ccs_tag` 函数 | 140 | 14 | 把 ``CCS:…`` 标签写进 ``doc_meta.domain_tags`` 并记台账（**一个事务**）。 |
| `get_ccs_state` 函数 | 220 | 26 | 某一篇的分类号查询台账（没有这一行 ⇒ None，表示**还没查过**）。 |
| `ccs_states_for` 函数 | 227 | 2 | 批量取台账（`GET /kb/inbox` 一次要几十篇，别一篇一条 SQL）。 |
| `counts_by_outcome` 函数 | 238 | 2 | 台账按结论计数（界面「补全分类号」的结果概览用）。 |
| `state_columns` 函数 | 249 | 1 | 本表列名（给测试与审计对形状用。 |
| `table_exists` 函数 | 254 | 1 | 表在不在（老库没跑过 ``init_schema`` 时给调用方一个判据，不靠猜）。 |

### `src/core/knowledge/ccs_undo.py`（8 个符号）

> 「补全分类号」的**补前精确回退记录**（2026-09-24，业主点名第①条「补之前自动备份一次，留回退说明」）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_err` 函数 | 61 | 62 | — |
| `journal_dir` 函数 | 70 | 6 | 回退记录与快照**同一个备份目录**（唯一所有者：``backup._backups_dir()``）。 |
| `_new_journal_path` 函数 | 80 | 2 | 备份目录下一个新名字：看得出时间 + 进程（同一秒连开两批也不会撞）。 |
| `write_undo_journal` 函数 | 93 | 7 | 把这些篇的**改前样子**写进备份目录（一次，补之前）。 |
| `latest_journal_path` 函数 | 157 | 4 | 备份目录里**最近写的那一份**回退记录（按修改时间。 |
| `load_undo_journal` 函数 | 165 | 2 | 读一份回退记录（``None`` = 取最近那一份）。 |
| `_state_key` 函数 | 190 | 3 | 台账行按**本表列**归一（比较/写回都只认这 11 列）。 |
| `revert_ccs_backfill_journal` 函数 | 197 | 10 | 按回退记录把 ``domain_tags``、``updated_at`` 与 ``doc_ccs_state`` **恢复到改前**（一个事务）。 |

### `src/core/knowledge/classifier.py`（6 个符号）

> 三型知识单元分型 + 法理要素抽取（T05 规则版；LLM 半自动增强在 T06 之后接入）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `extract_modality` 函数 | 34 | 7 | 抽取首个有效模态词（跳过复合词误命中）。 |
| `TypedClause` 类 | 91 | 5 | — |
| `normalize_clause_number` 函数 | 108 | 18 | E6 编号归一：全角→半角、去前导零、去空白。 |
| `strip_revision_marks` 函数 | 117 | 4 | E7 修订标记剥离。 |
| `classify_clause` 函数 | 122 | 24 | — |
| `build_hierarchy_path` 函数 | 179 | 12 | E3 层级路径：5.2.1 → '5 > 5.2'（章-节-条）。 |

### `src/core/knowledge/doc_catalog.py`（6 个符号）

> 文档分类目录（文件目录面板数据源，4 级树，2026-08-23 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ccs_range_of` 函数 | 128 | 3 | CCS 具体类目（如 P16）→ 所属区间 (P15/19, 工程抗震、工程防火、人防工程)。 |
| `_law_tier` 函数 | 202 | 3 | 第一级效力层级：优先 legal_hierarchy 映射。 |
| `_law_dept` 函数 | 215 | 2 | 第二级法律部门：标题+领域标签命中关键词 → A~G。 |
| `_law_domain_doc` 函数 | 226 | 2 | 第三级业务/行业领域：取非 CCS 的领域标签。 |
| `_is_standard_no` 函数 | 255 | 7 | 这个 `standard_no` 是**标准编号**（而不是法规名）吗？见 `_STD_NO_PREFIX` 的注释。 |
| `classify_document` 函数 | 265 | 51 | 文档 → 四级分类路径。 |

### `src/core/knowledge/folder_filing_plan.py`（11 个符号）

> 归位计划：把「现有每一篇按当前显示的分类该落到哪个目录」算出来（KB-FOLDER-PLAN §五第 1 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `tags_of` 函数 | 72 | 3 | ``domain_tags`` 统一成 list（库里是 JSON 字符串。 |
| `path_of` 函数 | 84 | 4 | 分类结果 → 四级目录路径（L1..L4，**分类口径**。 |
| `tree_path_of` 函数 | 90 | 15 | **分类口径路径 → 真树路径**（唯一所有者，理由见上面的常量区注释）。 |
| `show_path` 函数 | 106 | 6 | — |
| `_register` 函数 | 110 | 4 | 给一篇**已分类好**的文档登记目录节点与归属。 |
| `plan_filing` 函数 | 152 | 16 | 算归位计划（**纯函数**：不碰库、不落盘）。 |
| `tree_lines` 函数 | 215 | 4 | 目录树的**给人看**的行（按层级缩进，括号里是"含更深层"篇数）。 |
| `summarize_plan` 函数 | 230 | 6 | 清单要的关键数字（层级计数 + 无分类成因归类 + 异常归类）。 |
| `apply_plan` 函数 | 261 | 4 | 把计划落进**指定的库**（``db_path``）—— 单事务，全成或全败。 |
| `build_report` 函数 | 280 | 3 | 把计划、实测耗时、落库结果、自证拼成**机器可读报告**（清单文本由它渲染）。 |
| `render_text` 函数 | 300 | 4 | 把报告渲染成**给人看**的清单（业主过目用的那一份）。 |

### `src/core/knowledge/folder_store.py`（49 个符号）

> 知识库多级目录的读写层（KB-FOLDER-PLAN 第 1 步：只做「存」的那一层）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_err` 函数 | 122 | 62 | — |
| `pinyin_of` 函数 | 138 | 3 | 名字的拼音键（无拼音库时**原样返回** —— 退化成名字序，不虚构拼音）。 |
| `_name_sort_key` 函数 | 156 | 2 | 目录行的排序键 ``(sort, 拼音, 名)``。 |
| `_sort_key_of_value` 函数 | 161 | 1 | 同一个排序键，但入参是裸值（给"还没进库"的候选目录用）。 |
| `_doc_columns` 函数 | 166 | 6 | doc_meta 的实际列集（不同库版本列数不同 ⇒ 不写 ``SELECT *``）。 |
| `_visible_clause` 函数 | 171 | 4 | "这篇文档在目录里可见"的判据。 |
| `_clean_name` 函数 | 186 | 6 | 目录名校验：非空、有长度上限、不含路径分隔符/控制字符。 |
| `_folder_row` 函数 | 204 | 30 | — |
| `_ancestors` 函数 | 213 | 4 | 从**顶层往下**到 ``folder_id`` 的祖先链（不含自身）。 |
| `_depth_of` 函数 | 230 | 3 | 层级：顶层目录 = 1。 |
| `_path_names` 函数 | 235 | 2 | ``folder_id`` 的完整名字路径（从顶层往下）。 |
| `_folder_edges` 函数 | 243 | 6 | container → 下级目录集合（成员边 ∪ ``parent_id``，两源并集）。 |
| `_file_edges` 函数 | 255 | 3 | container → **直接**放在这一级的文件集合。 |
| `_subtree_ids` 函数 | 264 | 6 | root_ids 及其**所有下级**的目录 id（seen 去重 ⇒ 有环也会终止）。 |
| `_subtree_height` 函数 | 279 | 3 | 子树**高度**（含自己）：只有自己 = 1。 |
| `_subtree_suffix_len` 函数 | 307 | 4 | 子树里最长的一段"从某个下级到末级"的名字片段长度（算完整路径长度用）。 |
| `_assert_path_len` 函数 | 332 | 4 | 新建/改名/挪动后的**完整路径**长度必须在 MAX_PATH_LEN 以内。 |
| `_find_child_by_name` 函数 | 341 | 5 | 这一层里同名的目录 id（没有 = None）。 |
| `_assert_name_free` 函数 | 353 | 5 | 同名同层拒绝（含根层）。 |
| `_unique_name` 函数 | 361 | 2 | 在 parent_id 这一层给 base 找一个不冲突的名字（复制目录用，最多试 99 次）。 |
| `_assert_folder_attach_ok` 函数 | 376 | 4 | 把 child 挂进 container 的共性校验（自挂 / 成环）。 |
| `_check_item_exists` 函数 | 385 | 2 | — |
| `_create_folder_in_tx` 函数 | 393 | 5 | 事务内建目录（调用方已开事务。 |
| `_add_member_in_tx` 函数 | 412 | 7 | 事务内加成员。 |
| `create_folder` 函数 | 429 | 93 | 建目录（在 ``parent_id`` 下。 |
| `rename_folder` 函数 | 436 | 10 | 改目录名（**只改库里的名字**，不动磁盘文件 —— 方案 §二第 1 条）。 |
| `move_folder` 函数 | 450 | 19 | 把目录**从 ``from_parent_id`` 那一处**挪到 ``to_parent_id`` 下（第 2 步修准）。 |
| `copy_folder` 函数 | 543 | 9 | 复制目录：**新建一个目录，装着和原来一样的东西**（方案 §三复制语义）。 |
| `delete_folder` 函数 | 576 | 14 | 删目录（方案 §二第 2 条："先问一句"三个情形）。 |
| `describe_folder_delete` 函数 | 705 | 5 | 删目录**前**"先问一句"要的数字（只读。 |
| `add_member` 函数 | 750 | 47 | 把一个成员（文件或子目录）放进目录。 |
| `remove_member` 函数 | 759 | 4 | **从这一处拿掉**（删一行成员行 —— 不是删文件。 |
| `copy_member` 函数 | 773 | 9 | 把一个成员**再挂到另一处**（同一个 item，多一行成员行）。 |
| `move_member` 函数 | 782 | 3 | 把成员从一处**挪到**另一处（加新行 + 删原行，同一个事务）。 |
| `build_folder_tree` 函数 | 799 | 15 | **一个事务**里把"目录树 + 归属 + 状态"建起来（全成或全败）。 |
| `list_folder` 函数 | 890 | 51 | 列**某一级**的内容：**先下级目录、再这一级直接放的文件**（文件分页）。 |
| `folder_scope` 函数 | 1004 | 31 | 某一级（或**多选若干目录的并集**）**及其所有下级**的集合。 |
| `folder_tree_index` 函数 | 1030 | 4 | 把整棵目录树读成一个纯字典（给"按路径匹配现有目录"用，**不开写事务**）。 |
| `list_all_folders` 函数 | 1081 | 2 | **整棵目录树的扁平清单**（每行带显示路径）—— 「放进哪个目录」的选择器用。 |
| `suggest_folder_for_doc` 函数 | 1115 | 5 | 给一篇**还没归位**的文档算"建议放进哪个**现有**目录"（方案 §一「待分类」）。 |
| `_path_of_id` 函数 | 1186 | 3 | 目录 id → 显示路径（沿 ``parent_id`` 往上。 |
| `confirm_inbox_decisions` 函数 | 1207 | 2 | **批量确认归位**（方案 §一「待分类」：认好放走的文件不再在「待分类」展示）。 |
| `set_filing_state` 函数 | 1291 | 19 | 写文件处理状态（幂等 upsert）。 |
| `get_filing_state` 函数 | 1322 | 42 | — |
| `snapshot_filing_assets` 函数 | 1354 | 7 | **只读**：把一篇的"用户资产"拍成快照 —— 它在哪些目录里 + 它的状态行。 |
| `restore_filing_assets` 函数 | 1369 | 14 | 把 ``snapshot_filing_assets`` 拍下的用户资产落到**新** doc_id 上（重导的第二半）。 |
| `mark_filed` 函数 | 1433 | 6 | 确认归位：把文件**放进**目录 + 状态置 ``filed`` + 记"谁在什么时候放进了哪个目录"。 |
| `list_pending_filing` 函数 | 1455 | 14 | 「待分类」列表：**还没归位**的文件（含从未处理过的：无状态行按 ``queued`` 算）。 |
| `list_document_states` 函数 | 1497 | 2 | **所有文件**的处理状态（方案 §一最后几条：不只待分类，全都要能看状态）。 |

### `src/core/knowledge/law_source/catalog.py`（20 个符号）

> 法规总目录（LAW_CATALOG_ONDEMAND_PLAN.md 任务 1）：flk 全量清单 → 本地 SQLite 目录。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `refresh_days` 函数 | 55 | 10 | 读刷新周期天数。 |
| `sxx_label` 函数 | 70 | 8 | sxx 数字 → 展示文案。 |
| `manifest_path` 函数 | 80 | 5 | — |
| `_now` 函数 | 84 | 13 | — |
| `_read_config` 函数 | 88 | 5 | 读 app_config 单值（延迟导入 inspector，避免 knowledge ⇄ update 顶层成环）。 |
| `_write_config` 函数 | 94 | 2 | — |
| `ensure_catalog_schema` 函数 | 121 | 13 | 幂等迁移建表 law_catalog + 索引。 |
| `_catalog_schema_current` 函数 | 157 | 2 | **六个**前提都齐了吗（表存在 + 两列 + 三条索引）？（**只读**。 |
| `_catalog_migration` 函数 | 169 | 3 | — |
| `_pick` 函数 | 198 | 24 | — |
| `extract_category_leaves` 函数 | 205 | 5 | enum_data() 响应 → \[(叶子code, 名称)\]。 |
| `_load_manifest` 函数 | 250 | 2 | — |
| `_save_manifest` 函数 | 265 | 4 | — |
| `parse_aggregate` 函数 | 281 | 5 | aggregateData 响应 → {分类名或code: 计数}。 |
| `_reconcile_warnings` 函数 | 305 | 2 | — |
| `_norm_sxx` 函数 | 320 | 5 | — |
| `refresh_catalog` 函数 | 329 | 24 | 全量遍历 flk 清单入 law_catalog。 |
| `_parse_last_refresh` 函数 | 465 | 2 | 上次刷新时间串 → UTC aware datetime。 |
| `refresh_catalog_if_due` 函数 | 475 | 13 | 到期才刷新（spec 006 的自动刷新入口）。 |
| `query_catalog` 函数 | 510 | 23 | 本地目录分页查询（标题模糊 + 分类/效力过滤）。 |

### `src/core/knowledge/law_source/convert.py`（5 个符号）

> docx → PDF 转换链（方案 §3）：LibreOffice headless 主选 → WPS/Word COM 回退。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_libreoffice` 函数 | 12 | 9 | 探测 soffice 可执行。 |
| `docx_to_pdf_libreoffice` 函数 | 54 | 4 | LibreOffice headless 转换。 |
| `docx_to_pdf_com` 函数 | 82 | 4 | WPS/Word COM 回退（复用 Task 11.1 docx_adapter）。 |
| `pdf_completeness` 函数 | 91 | 7 | 转换完整性检测：docx 文本量 vs PDF 提取文本量。 |
| `convert_docx_to_pdf` 函数 | 112 | 3 | 转换链：LibreOffice →（完整性校验）→ WPS/Word COM →（校验）→ 空串。 |

### `src/core/knowledge/law_source/flk_client.py`（11 个符号）

> flk.npc.gov.cn 国家法律法规数据库客户端（官方公开 API）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_headers` 函数 | 24 | 35 | — |
| `enum_data` 函数 | 33 | 15 | 全部分类/机关/时效字典（flfgCodeId / zdjgCodeId / sxx 叶子 code 表）。 |
| `search` 函数 | 42 | 782 | 搜索（searchRange 1=标题 2=正文。 |
| `parse_rows` 函数 | 69 | 16 | 搜索结果 rows → 精简列表（title / bbbs / flxz / zdjgName / gbrq / sxrq / sxx）。 |
| `FlkDetail` 类 | 90 | 5 | — |
| `oss_word_path` 函数 | 102 | 1 | — |
| `oss_pdf_path` 函数 | 106 | 1 | — |
| `detail` 函数 | 110 | 406 | — |
| `history` 函数 | 120 | 66 | 一部法规的**历次版本链**（详情接口的 `lsyg` = 历史沿革）。 |
| `download_url` 函数 | 162 | 2 | 返回签名 OSS URL。 |
| `download` 函数 | 172 | 20 | 下载官方 Word/PDF 到 dest。 |

### `src/core/knowledge/law_source/govcn_client.py`（5 个符号）

> gov.cn 国务院政策文件库客户端（官方公开接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `search` 函数 | 33 | 782 | 搜索政策文件库。 |
| `parse_rows` 函数 | 54 | 16 | 搜索响应 → 精简列表（title / pcode 文号 / source 机关 / pubtime / url 详情页）。 |
| `GovDetail` 类 | 77 | 5 | — |
| `fetch_detail` 函数 | 86 | 8 | 抓取政策详情页：标题/正文/日期/来源 + 官方下载链接。 |
| `download` 函数 | 139 | 20 | 下载官方文件（docx/ofd），魔数校验 ZIP。 |

### `src/core/knowledge/law_source/http.py`（9 个符号）

> law_source 共享 HTTP 层：域白名单 / UA / 限速 / 重试 / 文件校验。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_pace` 函数 | 39 | 17 | — |
| `check_host` 函数 | 48 | 14 | 域白名单校验。 |
| `_retry` 函数 | 57 | 8 | 重试包装。 |
| `_looks_like_antibot` 函数 | 92 | 6 | 响应体是不是反爬挑战页。 |
| `_json_or_challenge` 函数 | 110 | 4 | 响应 → dict。 |
| `AntibotChallenge` 类 | 123 | 8 | 官方站返回反爬挑战页（HTTP 200 + HTML）。 |
| `fetch_json` 函数 | 131 | 25 | 白名单内 JSON 请求（搜索/详情/下载链接接口）。 |
| `download_file` 函数 | 179 | 6 | 白名单内文件下载。 |
| `_magic` 函数 | 215 | 6 | — |

### `src/core/knowledge/law_source/ingest.py`（10 个符号）

> 法规入库编排（方案 §4/§5）：官方源 → docx → PDF → 现有 run_full_ingest 管线。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_now_iso` 函数 | 37 | 7 | — |
| `law_source_dir` 函数 | 41 | 5 | — |
| `ensure_schema` 函数 | 45 | 8 | 幂等迁移：doc_meta 增加官方来源溯源列（新库 schema.sql 已含）。 |
| `_write_meta` 函数 | 50 | 2 | — |
| `_update_doc_source` 函数 | 56 | 2 | — |
| `_ingest` 函数 | 65 | 5 | docx → PDF（缓存复用）→ 现有管线入库。 |
| `ingest_law_from_flk` 函数 | 116 | 9 | 按 bbbs 从国家法律法规数据库下载官方 docx → 转 PDF → 入库。 |
| `_build_docx_from_html` 函数 | 154 | 4 | 兜底：详情页无官方下载链接时，用正文 HTML 生成 docx（仍记官方来源 URL）。 |
| `ingest_law_from_govcn` 函数 | 189 | 7 | 按详情页 URL 从国务院政策文件库下载官方 docx → 转 PDF → 入库。 |
| `find_by_source` 函数 | 227 | 6 | 按来源幂等键查库内文档（供重复导入/更新检测）。 |

### `src/core/knowledge/law_source/law_refresh.py`（4 个符号）

> 法规目录定时刷新循环（spec 006）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_run` 函数 | 46 | 73 | 循环体：直到本线程的 stop 被置位。 |
| `start_law_refresh` 函数 | 63 | 19 | 拉起刷新线程。 |
| `stop_law_refresh` 函数 | 77 | 14 | 置位停止并等线程退出。 |
| `is_running` 函数 | 111 | 16 | 线程是否在跑（测试与诊断用）。 |

### `src/core/knowledge/law_source/update.py`（2 个符号）

> 法规更新检查（LAW-SOURCE-PLAN §6）：比对库内官方来源文档与官方源现状。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `check_law_updates` 函数 | 13 | 7 | — |
| `_check_flk` 函数 | 25 | 2 | — |

### `src/core/knowledge/law_source/verify.py`（17 个符号）

> 法规效力「点开即核验」服务（任务 2，docs/REALTIME-VALIDITY-VERIFY-RESEARCH.md §2/§3）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `evidence_url` 函数 | 109 | 56 | 官方证据页链接。 |
| `_now_iso` 函数 | 114 | 7 | — |
| `_is_blank` 函数 | 118 | 3 | — |
| `_norm_sxx` 函数 | 122 | 5 | sxx 归一为 int。 |
| `_result` 函数 | 136 | 5 | 统一载荷形状：核心五字段 + 附加证据字段 + retryable（仅 unverified 为 True）。 |
| `_unverified` 函数 | 160 | 6 | — |
| `_cache_path` 函数 | 167 | 3 | — |
| `_load_disk_locked` 函数 | 172 | 2 | 温启动：进程内首次触达时把落盘缓存里仍未过期的条目装回内存（坏文件静默跳过）。 |
| `_save_disk_locked` 函数 | 195 | 2 | 写穿落盘（best-effort：任何 IO 失败只记日志，绝不影响核验主流程）。 |
| `_cache_get` 函数 | 217 | 3 | 命中返回缓存条目（含 payload/expires_at），过期即清除并返回 None。 |
| `_cache_put` 函数 | 232 | 2 | 写入缓存（payload 剥离 cached 标记后存原始结果）。 |
| `reset_verify_cache` 函数 | 243 | 4 | 清空进程内缓存并复位温启动标记（测试/运维钩子。 |
| `_call_detail` 函数 | 252 | 2 | worker 线程内执行：运行期属性访问 flk_client.detail，保证 monkeypatch 生效。 |
| `_probe_with_budget` 函数 | 258 | 2 | 在剩余预算内调一次官方详情。 |
| `_map_detail` 函数 | 280 | 2 | FlkDetail → (payload, ttl)。 |
| `_sf_lock` 函数 | 309 | 2 | — |
| `verify_law` 函数 | 318 | 31 | 核验单部法规的官方效力状态。 |

### `src/core/knowledge/legal_status.py`（1 个符号）

> 法律/标准效力状态「到期翻转」决议（2026-08-27）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `resolve_status` 函数 | 24 | 43 | 到期/未到期双向惰性翻转（零写库、读取即正确）。 |

### `src/core/llm/deepseek_client.py`（4 个符号）

> DeepSeek 官方 API 流式客户端（openai SDK 协议）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `build_evidence_prompt` 函数 | 47 | 5 | 构造最小必要证据 Prompt（R2 红线：不传全文，正文截断 800 字符，R77）。 |
| `build_messages` 函数 | 71 | 19 | 组装 messages：system（含 R17 Few-shot + 追问禁令）+ 历史文本(截断) + 当前轮。 |
| `stream_chat_completion` 函数 | 99 | 7 | 流式生成回答片段（支持 R60 多轮历史）。 |
| `chat_complete` 函数 | 130 | 4 | 通用非流式补全（结构化调用：找标 LLM 分类/释义等）。 |

### `src/core/llm/egress_audit.py`（5 个符号）

> 统一外发记录助手（Task 10.0：零外发 → 外发可审计）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `record_egress` 函数 | 32 | 46 | 登记一次云端调用。 |
| `_row_to_audit` 函数 | 66 | 2 | debug_dump 行 → 审计条目（脱敏：只给摘要，不给完整 prompt 外发细节）。 |
| `_verification_brief` 函数 | 91 | 2 | — |
| `query_egress` 函数 | 102 | 14 | 审计聚合（只读）。 |
| `export_egress` 函数 | 131 | 5 | 导出全部外发记录为 JSON 文件（exports 目录，供 /export/download 下载）。 |

### `src/core/llm/fewshot.py`（3 个符号）

> R17 轻量版（Task 13.4）：负向反馈聚类 → SYSTEM_PROMPT Few-shot 注入。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `collect_feedback_patterns` 函数 | 21 | 3 | 读取负向反馈（rating<0），按 feedback_type 聚类取高频内容片段。 |
| `build_fewshot_block` 函数 | 55 | 2 | — |
| `inject_fewshot` 函数 | 64 | 5 | 在系统提示词尾部追加 Few-shot 块（无反馈时原样返回）。 |

### `src/core/llm/jev_client.py`（13 个符号）

> Jev（TypeSafe System One）结构化判断客户端（2026-09-24，业主授权接入）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `JevUnavailable` 类 | 60 | 30 | Jev 不可用（未配 Key / 熔断中 / 网络失败 / 响应不合契约）。 |
| `_read_key` 函数 | 67 | 7 | Jev Key：与 LLM Key 同一个唯一入口（`KS_JEV_API_KEY`）。 |
| `breaker_open` 函数 | 73 | 8 | 熔断是否开着（**上次熔断**后还在冷却期内 ⇒ 跳过调用）。 |
| `_note_ok` 函数 | 87 | 2 | — |
| `_note_fail` 函数 | 93 | 3 | — |
| `reset_breaker_for_tests` 函数 | 104 | 21 | 测试用：清熔断状态（生产路径不调用）。 |
| `system_one` 函数 | 110 | 35 | 问一组类型化问题，返回 `{"answers": {...}, "model": ..., "usage": {...}}`。 |
| `_score_levels` 函数 | 153 | 2 | 从提问里取出每道 Score 题的**档位数**（`criteria` 列表长度），供回包值域校验用。 |
| `_validate_body` 函数 | 164 | 3 | **逐题验契约**（独立复核 2026-09-24 MED-2：原先只查 `answers` 存在，于是。 |
| `_record_egress` 函数 | 211 | 5 | 登记**每一次**外发——成功、HTTP 失败、异常都登记（独立复核 2026-09-24 MED-6：。 |
| `noul` 函数 | 240 | 54 | 是非题。 |
| `choice` 函数 | 246 | 36 | 选项题。 |
| `score` 函数 | 251 | 85 | 量表题。 |

### `src/core/llm/jev_guard.py`（1 个符号）

> 合规护栏判定：Jev（TypeSafe System One）那一侧（2026-09-24，业主报障驱动）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `judge` 函数 | 73 | 16 | 判一段用户输入要不要带上合规查库流程。 |

### `src/core/llm/ks_answer.py`（25 个符号）

> P1a 同步「取证答案」能力 ks_answer（pure engine + plugin tool candidate）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clause_to_evidence` 函数 | 116 | 6 | 把一个检索到的 ClauseRevisionModel 转成内部证据 dict。 |
| `attach_bboxes` 函数 | 151 | 28 | 给证据条目补 ``bbox`` / ``bbox_page``（**红箭头定位用**），原地修改。 |
| `_html_to_text_compact` 函数 | 276 | 3 | 表格 html → 紧凑纯文本（供 prompt 附表）。 |
| `_is_effective` 函数 | 294 | 14 | 硬规则①：只保留现行版。 |
| `_filter_effective` 函数 | 299 | 7 | 兜底断言：剔除一切非 effective 条款（含检索漏网的 superseded/withdrawn/upcoming）。 |
| `_dedupe` 函数 | 316 | 9 | 证据去重：先按 clause_revision_id，若为空再按 (doc_id, clause_number) 兜底。 |
| `_cap` 函数 | 336 | 13 | 证据上限（spec 硬规则④：上限 8）。 |
| `_is_substantive` 函数 | 341 | 7 | 判定一条证据是否为「实质」条款（区别于无实质规定的空标题条款）。 |
| `_decide_tier` 函数 | 363 | 8 | tier 三态判定（确定性启发式，取证口径）：。 |
| `_build_evidence_prompt` 函数 | 388 | 2 | 组装用户侧证据 Prompt：每条约 800 字截断 + 附表 300 字，引用标记 \[c:i\]。 |
| `build_messages` 函数 | 414 | 19 | 组装 messages。 |
| `_stream_llm` 函数 | 437 | 18 | 流式生成文本片段。 |
| `_collect_stream` 函数 | 486 | 3 | 把生成器拼成完整文本（同步端点用。 |
| `_strip_code_fences` 函数 | 495 | 2 | — |
| `parse_llm_answer` 函数 | 503 | 17 | 解析 LLM 输出为 {derivation, conclusion} + 校验 warnings。 |
| `_full_evidence_for_verify` 函数 | 587 | 2 | 构造 typed_verifier 期望的 evidence_clauses（content_text 用全量，不截断）。 |
| `answer_confidence` 函数 | 601 | 40 | 答案层置信度分级（high/mid/low）—— **全仓唯一实现**。 |
| `_ev_field` 函数 | 657 | 3 | 从证据字典里取字段，**两种命名都认**（`name` 与 `_name`）。 |
| `_answer_confidence` 函数 | 668 | 10 | **转发别名**（2026-10-24 起）。 |
| `_assemble_verification` 函数 | 677 | 4 | 跑 typed_verifier 并组装 verification 字段。 |
| `_upcoming_notes` 函数 | 709 | 2 | 对 evidence 中各标准（取其基准确则无年份部分），查 doc_meta 是否存在即将生效(upcoming)。 |
| `KbScopeNotFound` 类 | 745 | 10 | 知识库**目录范围**里有不存在的目录（第 6 步）。 |
| `_resolve_kb_scope` 函数 | 754 | 3 | 解析**知识库目录范围**（第 6 步）⇒ `(doc_ids, scope_info)`。 |
| `answer` 函数 | 810 | 667 | 同步取证答案主体。 |
| `_expand_title_clauses` 函数 | 1167 | 8 | 命中纯数字标题条款（内容 <80 字）自动附带其子条款（如 8.1 → 8.1.1~8.1.3），。 |

### `src/core/main.py`（2 个符号）

> 入口：python -m src.core.main

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_normalize_no_proxy` 函数 | 8 | 2 | 启动时把 ``NO_PROXY`` 里的 ``\[::1\]`` 折成 ``::1``（2026-09-24 加）。 |
| `_warmup_figure_ocr` 函数 | 38 | 3 | 后台预热流程图重绘的 RapidOCR 模型（2026-08-29）。 |

### `src/core/materials/authority.py`（5 个符号）

> 材料平面：权威性纪律（Phase B）。把"可信度"从**标签**变成**可执行规则**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_domain_of` 函数 | 73 | 6 | 从 URL 里取**来源域名**（小写、去 scheme/userinfo/端口/路径、去前导 `www.`）。 |
| `_source_identity` 函数 | 92 | 6 | 判"独立来源"的口径：优先 `domain`，其次从 `url` 取域名。 |
| `assemble_evidence` 函数 | 116 | 55 | 在**已批准**材料里检索并**按承重能力分组**。 |
| `render_evidence` 函数 | 248 | 26 | 把分组结果渲染成**给提示词/产出物用的文本**（每条都带两个轴的标注、`\[\[m:i\]\]` 与位置）。 |
| `usable_hits` 函数 | 298 | 20 | **只取能承重的**命中（准则 + 可作依据 + 多源互证的辅证）。 |

### `src/core/materials/collect.py`（7 个符号）

> 材料平面：**自采入口**（Phase C，2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `domain_of` 函数 | 83 | 3 | 从 URL 取域名（与 `authority._domain_of` 同口径的**轻量版**：只取 host）。 |
| `text_hash` 函数 | 100 | 6 | 文本候选的 `content_hash`（sha256 十六进制，与 `file_hash` 同形以便共用列）。 |
| `looks_like_standard` 函数 | 105 | 5 | 认出"这可能是一部法规/标准的正文"（Track L 的**判据入口**）。 |
| `_near_duplicates` 函数 | 119 | 2 | 在同项目**已登记**材料里找内容近似的（返回 material_id 列表，最多几个）。 |
| `_law_name_of` 函数 | 137 | 4 | 从**标题**取法规名（取不到返回 None）。 |
| `looks_like_law` 函数 | 179 | 9 | 认出"这可能是一部**法规**的正文"（Track L 的**法规入口**，Phase C 第八步）。 |
| `collect_text` 函数 | 226 | 68 | 登记一条**自采**材料（文本形态：网页正文/接口返回的正文）。 |

### `src/core/materials/dedup.py`（6 个符号）

> 材料平面：**近重复检测**（Phase C 前置，2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `normalize_text` 函数 | 43 | 10 | 归一化：全角→半角（NFKC）、大小写折叠、**去掉空白与标点**、只留文字与数字。 |
| `_ngrams` 函数 | 53 | 3 | — |
| `similarity` 函数 | 59 | 32 | 归一化后的字符 n-gram Jaccard（0~1）。 |
| `near_duplicate` 函数 | 81 | 7 | 两条文本是否"看起来是同一篇稿子"（相似度 ≥ 阈值）。 |
| `group_by_content` 函数 | 87 | 6 | 把下标按"内容近似"聚成组（**并查集**连通分量），返回组列表。 |
| `independent_source_count` 函数 | 123 | 10 | **独立来源数**：在**域名**上做连通分量，内容近似的域名被并成一组。 |

### `src/core/materials/harvest.py`（7 个符号）

> 材料平面：**网页采集器**（Phase C 第四步，2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `page_title` 函数 | 73 | 4 | 从 `<title>` 取标题（粗。 |
| `_fetch_without_redirects` 函数 | 82 | 4 | 抓一跳，**明确不跟随重定向**（`allow_redirects=False`），并把四样都拿回来。 |
| `_content_type_of` 函数 | 122 | 2 | 从响应头取 Content-Type 的**主类型**（小写。 |
| `_content_type_ok` 函数 | 139 | 3 | 这个 Content-Type 能不能当网页正文？`None`（服务端没给）交给字节判据。 |
| `_https_upgrade` 函数 | 145 | 8 | `http://x/y` → `https://x/y`（**只改协议**）。 |
| `collect_url` 函数 | 161 | 38 | 抓一个 URL 并登记为**待评审**材料。 |
| `_default_transport` 函数 | 263 | 6 | 延后导入：`update.channels.base` 会拉起 curl_cffi/httpx，离线场景不必付这个代价。 |

### `src/core/materials/locator.py`（5 个符号）

> **引用锚点稳定性**（方案 §12 未决第 5 条 = Phase B 必解）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `current_fingerprint_for` 函数 | 70 | 6 | **现在这台机器**会用什么指纹解析这份材料的源文件（取不到就 None）。 |
| `source_bytes_match` 函数 | 92 | 9 | 磁盘上的源文件字节**是否与入库时记的一致**（`None` = 判不了）。 |
| `locator_health` 函数 | 113 | 33 | **便宜**的锚点健康度：比指纹 + 比源文件字节，不重解析。 |
| `reverify_material_locators` 函数 | 202 | 11 | **重解析比对**（贵）：用当前解析器重算派生文本哈希，与入库时记的比。 |
| `project_locator_summary` 函数 | 256 | 4 | 项目级锚点总览（每份材料的状态 + 计数 + 有问题的清单）——给界面/报告用。 |

### `src/core/materials/track_l.py`（10 个符号）

> 材料平面：**Track L —— 采到的法规/标准要怎么进法条库**（Phase C 第二步，2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `track_l_intent` 函数 | 51 | 9 | 从材料里取 Track L 意图（`tier_evidence.track_l`）。 |
| `find_existing_doc` 函数 | 72 | 8 | 库内是否已有这部标准（按比较键 Exact 匹配）→ 返回 `doc_id` 或 `None`。 |
| `find_existing_law` 函数 | 89 | 8 | 库内是否已有这部**法规**（按 `law_name_key` 比对 `standard_no`/`standard_name`）。 |
| `plan_import` 函数 | 111 | 16 | **决策**（不产生任何写入）：这份材料在 Track L 下该做什么。 |
| `apply_link` 函数 | 168 | 7 | 执行 `link` 动作（**唯一会写的操作**，且只写材料平面的 `doc_id` 列）。 |
| `_material_text` 函数 | 182 | 2 | 把材料的切片拼回正文（**切片就是存档副本**——采集件没有源文件）。 |
| `_law_hierarchy` 函数 | 203 | 11 | 法规名 → `legal_hierarchy` 存储值（**保守**。 |
| `_collected_doc_meta` 函数 | 221 | 5 | 采集件入库时要写的**诚实元数据**（2026-09-17 复核 step-31~34 的 MEDIUM）。 |
| `import_to_library` 函数 | 242 | 16 | **Track L 入库**：把已批准、库内没有的标准/法规正文灌进法条库。 |
| `reconcile` 函数 | 331 | 34 | **Track L 的单一入口**：评审之后调用它，由它按决策分派。 |

### `src/core/middle_geo.py`（20 个符号）

> MinerU middle.json 几何缓存（2026-09-02，表格/图片/独立公式 bbox 页级索引）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MiddleGeo` 类 | 35 | 4 | 页级几何索引。 |
| `__init__` 函数 | 38 | 135 | — |
| `page` 函数 | 42 | 1275 | — |
| `size` 函数 | 45 | 180 | — |
| `tables` 函数 | 48 | 121 | — |
| `images` 函数 | 52 | 74 | — |
| `eqs` 函数 | 56 | 16 | — |
| `eq_blocks` 函数 | 60 | 3 | 独立公式块（interline_equation）：bbox px + LaTeX 行（含   ag 编号）。 |
| `text_blocks` 函数 | 65 | 6 | OCR 文本块（type=text，bbox px + 行拼接文本）——纯扫描 PDF 的。 |
| `charts` 函数 | 71 | 7 | 曲线/图表（type=chart）：bbox px + 题注文本（图1-8、图A.2/A.5）。 |
| `chart_by_caption` 函数 | 77 | 4 | 按题注图号（如 '1'、'A.2'）在全部页找 chart，返回 (page_no,。 |
| `chart_by_no` 函数 | 90 | 2 | 数字图号兜底（2026-09-02 图4/6/8）：部分曲线图题注被 OCR 合并进。 |
| `figures` 函数 | 110 | 17 | 统一图对象（2026-09-02 C1 架构根治）：合并 image + chart 版面图，。 |
| `assets` 函数 | 140 | 48 | 全部 image asset（页 + bbox + 文件名），供渲染统一注入。 |
| `image_bbox_by_path` 函数 | 150 | 3 | 按裁剪文件名（images/<sha256>.jpg 的裸名）反查 image bbox。 |
| `image_hit_tables` 函数 | 162 | 3 | 该页「带图表格」序号（tables 列表内索引，升序）。 |
| `frac` 函数 | 178 | 36 | bbox 像素 → (frac_x0, frac_w, frac_h)（页宽/页高比例）。 |
| `_inter_area` 函数 | 189 | 2 | — |
| `_find_middle_jsons` 函数 | 197 | 2 | 定位全部 middle 产物（任意深度，防穿越）。 |
| `load` 函数 | 216 | 103 | 读取并缓存 parse_root 的几何索引。 |

### `src/core/quality/clause_health.py`（3 个符号）

> 条款级体检规则（数据体检 6 标签）——**唯一所有者**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ClauseHealth` 类 | 35 | 7 | 一条条款的体检结论。 |
| `clause_health_html_to_text` 函数 | 43 | 26 | 表格 html → 紧凑纯文本（证据 prompt / table_md 用）。 |
| `clause_health` 函数 | 61 | 21 | 对单条条款跑 6 标签判据（纯函数）。 |

### `src/core/quality/disagreement.py`（8 个符号）

> 阶段2c：低置信条款云二次识别·分歧检测（disagreement-detection ONLY）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `DisagreementItem` 类 | 32 | 4 | — |
| `DisagreementReport` 类 | 44 | 5 | — |
| `score_distribution_collapsed` 函数 | 55 | 6 | O2 fallback 判据：>0.95 的 span 占比 ≥ 95% = 坍缩（信号地基失效）。 |
| `text_similarity` 函数 | 63 | 10 | 文本级相似度（difflib.SequenceMatcher，清洗空白后比较）。 |
| `compare_clause_texts` 函数 | 75 | 5 | 单条款分歧判定：similarity < 1-threshold → disagree。 |
| `select_2c_input` 函数 | 82 | 4 | 2c 输入面选择（O2 fallback 内建）。 |
| `build_disagreement_report` 函数 | 102 | 5 | 对比本地/云文本，出分歧报告（纯函数，不触网）。 |
| `report_to_dict` 函数 | 140 | 3 | 报告 → 可 JSON 化 dict（人工裁决面板消费）。 |

### `src/core/quality/grading.py`（6 个符号）

> 质量分级与裁决——阈值与规则的**唯一所有者**（纯函数，零 IO）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_why` 函数 | 80 | 16 | — |
| `verdict_document` 函数 | 84 | 32 | 依据报告度量给出 (verdict, reasons)。 |
| `grade_document` 函数 | 172 | 20 | 质量分级。 |
| `typing_quality` 函数 | 194 | 23 | 分型预览质量评估（R27 v4.3 新增）。 |
| `legal_element_quality` 函数 | 220 | 6 | 法理要素抽取质量评估（R27 v4.3 新增）。 |
| `one_line_summary` 函数 | 266 | 7 | 批量分桶用的一行摘要（稳定格式，测试锁定）。 |

### `src/core/quality/recognition.py`（8 个符号）

> 识别与版面质量度量（R27 入库预览用）——纯函数 + 只读。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_cjk_ratio` 函数 | 43 | 3 | — |
| `TextLayerMetrics` 类 | 51 | 7 | — |
| `text_layer_metrics` 函数 | 60 | 6 | 文本层整体度量。 |
| `PageLayoutMetrics` 类 | 82 | 6 | — |
| `page_layout_metrics` 函数 | 92 | 6 | 版面度量：每页字符密度、空白页、旋转异常、页面尺寸离群。 |
| `SkewResult` 类 | 137 | 8 | — |
| `measure_skew` 函数 | 145 | 10 | 测量 PDF 文本行的倾斜角（度）。 |
| `clause_ocr_confidence` 函数 | 218 | 17 | 推导单条条款的识别置信度（R27 的 "OCR 置信度"），返回 (置信度, 扣分理由码)。 |

### `src/core/query/understanding.py`（10 个符号）

> Query Understanding Layer（Phase 9.2，R9/R40/R41/R52/R53/R60 基础版）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `classify_intent` 函数 | 29 | 16 | — |
| `detect_theme` 函数 | 51 | 14 | 主题：special_work / building / privacy / general。 |
| `parse_declared` 函数 | 114 | 8 | — |
| `extract_slots` 函数 | 146 | 13 | 主题作用域槽位提取：仅提取当前主题相关的槽位（防跨主题污染）。 |
| `apply_condition_filter` 函数 | 178 | 5 | — |
| `rank_with_hierarchy` 函数 | 207 | 13 | 按"位阶 → 是否强制 → 标准类型是否强制"排序。 |
| `hierarchy_label` 函数 | 227 | 4 | — |
| `sufficiency_note` 函数 | 238 | 6 | — |
| `refine_search_query` 函数 | 254 | 10 | 清洗口语噪音并追加问法关键词，提升检索命中（分级/对比等）。 |
| `detect_correction` 函数 | 271 | 5 | — |

### `src/core/retrieval/embedder.py`（8 个符号）

> 本地向量模型封装（fastembed bge-small-zh-v1.5, CPU/ONNX）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_import_text_embedding` 函数 | 44 | 10 | 加载入口的**唯一缝**：测试拿它当替身，不必真装 fastembed、更不必连网。 |
| `_cooldown_active` 函数 | 50 | 2 | 上次失败是否仍在冷却窗口内（调用方需**已持有** `_lock`，或接受轻微竞态读）。 |
| `_get_model` 函数 | 55 | 17 | 取模型（**会加载**。 |
| `embed_query` 函数 | 87 | 65 | — |
| `embed_batch` 函数 | 92 | 31 | — |
| `is_available` 函数 | 97 | 53 | **会加载**（首次可能几秒并外发一次下载）——只给"真要拿模型"的路径用。 |
| `health` 函数 | 110 | 111 | **廉价**三态：`ok` / `offline` / `unknown`（**不加载模型**，只读已有证据）。 |
| `offline_reason` 函数 | 128 | 8 | — |

### `src/core/retrieval/hybrid_engine.py`（15 个符号）

> 六路混合检索 + RRF 融合（T04，依据主计划 v4.3 第 8.3 节）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_std_key_hits_doc` 函数 | 84 | 17 | 提问里的标准号键 `key` 是否命中这部文档的 `standard_no`。 |
| `_rows_matching_standard_keys` 函数 | 109 | 8 | 把候选行按「提问点名的标准」过滤（判据是 `_std_key_hits_doc` 的词边界包含）。 |
| `_known_standard_keys` 函数 | 124 | 17 | 从提问里抽出的候选键中，**挑出库里真的有对应文档的那些**。 |
| `set_db_override` 函数 | 140 | 16 | 设置/清除检索库路径覆盖（None=恢复默认）。 |
| `_conn` 函数 | 146 | 22 | — |
| `_fts_query` 函数 | 150 | 27 | 构建 FTS5 MATCH 表达式：对每个分词加引号，避免点号/连字符等触发语法错误。 |
| `_catalog_visible_fragment` 函数 | 162 | 16 | `catalog_hidden` 可见性片段（spec 013）——**唯一所有者**。 |
| `_catalog_visible_by_clause` 函数 | 196 | 9 | 同上，但给**没 JOIN `doc_meta`** 的通道用（B/C/F 走 `clause_revision` 中转）。 |
| `perform_hybrid_search` 函数 | 213 | 118 | 六路召回 + RRF(k=60) 融合 + 时效过滤。 |
| `_protect_exception_clauses` 函数 | 562 | 3 | 例外条款保护（P1）：含但书/除外的条款被 rerank 挤出时强制保留。 |
| `_rerank_results` 函数 | 589 | 11 | Task 10.2 rerank 标准阶段：RRF 融合后 top-N → reranker → top-K。 |
| `extract_modality_from_query` 函数 | 620 | 36 | 从用户查询中提取模态词，用于通道 D 过滤。 |
| `expand_query_with_history` 函数 | 642 | 15 | R9 条件追问检索增强：当前问过短、含指代词，或是在补充上一轮提问的回答时。 |
| `expand_evidence_chain` 函数 | 671 | 4 | R5a 证据链扩展：沿 evidence_edge 扩 1~2 跳，防例外/但书/引用遗漏。 |
| `search_with_details` 函数 | 709 | 43 | R31 检索可解释性：返回结果 + 调试元数据。 |

### `src/core/retrieval/reranker.py`（4 个符号）

> 本地 reranker 阶段（Task 10.2）：六通道 RRF 融合后 top-N → rerank → top-K 进 LLM。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `is_available` 函数 | 27 | 53 | — |
| `_get_model` 函数 | 35 | 17 | — |
| `rerank` 函数 | 54 | 116 | 返回与 `texts` **一一对应**的相关性分数：`scores\[i\]` 就是 `texts\[i\]` 的分，**未排序**。 |
| `offline_reason` 函数 | 78 | 8 | — |

### `src/core/retrieval/term_bridge.py`（13 个符号）

> 术语桥（P1 第 2 步"翻译层"的第一版实现）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TermEntry` 类 | 66 | 17 | 一条术语（取自某个术语条款）。 |
| `TermIndex` 类 | 77 | 57 | 术语表 + 它们的向量。 |
| `__len__` 函数 | 91 | 3 | — |
| `_matrix` 函数 | 94 | 22 | 把向量堆成**已归一化**的矩阵（懒建，按条数失效）。 |
| `build` 函数 | 126 | 80 | — |
| `save` 函数 | 136 | 57 | — |
| `load` 函数 | 147 | 103 | — |
| `select` 函数 | 155 | 17 | 语义选出最像的 k 个术语（有界选择）。 |
| `topk_by_cos` 函数 | 165 | 24 | 按余弦相似度取前 `k` 个**下标**（**分数降序。 |
| `extract_term_entries` 函数 | 204 | 11 | 从库里扫出所有术语条款。 |
| `merge_round_robin` 函数 | 245 | 18 | **轮转交错**合并（1,1,1,1,1,2,2,2,…），并去掉重复。 |
| `bridge_search` 函数 | 272 | 3 | 术语桥检索：语义选 k 个术语 → 每个各查一次 → 轮转交错合并。 |
| `_cos` 函数 | 305 | 3 | — |

### `src/core/settings/api_credentials.py`（16 个符号）

> API 凭据存储（2026-08-27；2026-09-01 云解析换组；**2026-09-11 命名空间化**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `UnknownChannel` 类 | 59 | 17 | — |
| `InvalidModelVersion` 类 | 63 | 6 | 云解析模式取值非法（官方契约三选一：pipeline / vlm / MinerU-HTML）。 |
| `set_credential` 函数 | 67 | 54 | 把通道凭据写进**引擎自己的加密存储**（`secret_store`，DPAPI）。 |
| `import_system_layer` 函数 | 110 | 8 | 把系统层里**本通道自己的名字**（同名迁移）搬进加密存储。 |
| `stored_channels` 函数 | 160 | 5 | 存储里各通道已配置了哪些名字（**只报布尔，不解密、不回显**）。 |
| `_read_registry_var` 函数 | 167 | 6 | 读 HKCU\Environment 单值。 |
| `_read_any_var` 函数 | 177 | 6 | 单个变量内部：进程环境变量 → 注册表（与 src.core.config 的同名语义一致）。 |
| `legacy_status` 函数 | 186 | 3 | 旧全局变量的现状：**只报存在性与来源，绝不回显 Key 的值**。 |
| `system_layer_names` 函数 | 205 | 3 | 引擎**曾经**可能写进系统层的全部变量名（含 legacy 与各通道）。 |
| `system_layer_status` 函数 | 215 | 6 | 系统层里这些名字的现状（**只报存在性/长度，绝不回显值**）。 |
| `clean_system_layer` 函数 | 226 | 8 | 删除系统层（HKCU\Environment）里的这些变量 —— **不可逆的破坏性操作**。 |
| `adopt_legacy` 函数 | 254 | 20 | 把旧全局变量的值迁到命名空间名（**返回值只含变量名/布尔，绝不含值**）。 |
| `get_status` 函数 | 348 | 9 | 脱敏状态：只给 configured 布尔与 base_url，绝不回显 Key。 |
| `test_channel` 函数 | 367 | 2 | 活体探测：真实调一次上游，返回 {ok, detail}（不含 Key）。 |
| `_test_mineru_cloud` 函数 | 376 | 2 | 云解析通道探测：申请一次签名上传 URL 验证 token（不上传不启动任务）。 |
| `_test_llm` 函数 | 382 | 2 | — |

### `src/core/settings/secret_store.py`（19 个符号）

> 引擎侧密钥存储（**不再碰系统层**）。2026-09-11 立，业主指令：「不要动系统层」。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `SecretStoreError` 类 | 56 | 13 | 写入/加密失败。 |
| `_resolve_data_dir` 函数 | 63 | 3 | 取 KS 数据目录 —— **直接用 `config` 那一份**（函数内 import，避开环形）。 |
| `store_path` 函数 | 81 | 15 | 密钥文件路径。 |
| `_DATA_BLOB` 类 | 94 | 4 | — |
| `_BlobHolder` 类 | 99 | 5 | 持有源缓冲区，避免 create_string_buffer 被 GC 掉（悬垂指针是真实的坑）。 |
| `__init__` 函数 | 102 | 135 | — |
| `_open_libs` 函数 | 108 | 3 | — |
| `protect` 函数 | 115 | 8 | 明文 → base64(DPAPI 密文)。 |
| `unprotect` 函数 | 139 | 8 | base64(DPAPI 密文) → 明文。 |
| `_load` 函数 | 165 | 125 | 读文件。 |
| `_atomic_write` 函数 | 178 | 2 | — |
| `_Lock` 类 | 196 | 2 | 跨进程串行化（O_EXCL + 陈旧回收）。 |
| `__init__` 函数 | 199 | 135 | — |
| `__enter__` 函数 | 203 | 9 | — |
| `__exit__` 函数 | 221 | 9 | — |
| `read_value` 函数 | 234 | 56 | 读一个值。 |
| `has_value` 函数 | 246 | 5 | 是否存过该名字（**只看有没有密文，不解密**），供迁移/状态显示用。 |
| `write_values` 函数 | 255 | 28 | 合并写入（`None` = 删除该名字）。 |
| `stored_names` 函数 | 281 | 6 | 存储里已有哪些名字（**不解密**）。 |

### `src/core/storage/backup.py`（7 个符号）

> 快照备份与回滚（Task 13.5 / R46·R51，v5 P1 数据保护）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_backups_dir` 函数 | 28 | 14 | 备份目录。 |
| `_secrets_snapshot_path` 函数 | 44 | 4 | — |
| `_snapshot_secrets` 函数 | 48 | 2 | 把 secrets.json 密文原样复制进备份目录。 |
| `create_snapshot` 函数 | 67 | 33 | — |
| `_rollout_auto` 函数 | 90 | 2 | 滚动淘汰：自动快照保留最近 AUTO_KEEP 份。 |
| `list_snapshots` 函数 | 104 | 7 | — |
| `restore_snapshot` 函数 | 111 | 7 | 返回备份文件路径（替换 db 由上层执行：停写→替换→重连，走 supervisor）。 |

### `src/core/storage/channel_repo.py`（17 个符号）

> 渠道台账仓储（`update_channel`，§11.0 R2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_audit` 函数 | 104 | 4 | 人工维护渠道的**留痕**，与改动写在**同一个事务**里（§11.0 R6d）。 |
| `normalize_category` 函数 | 124 | 6 | 原始类别写法 → canonical。 |
| `_json_or_none` 函数 | 129 | 2 | — |
| `check_segments` 函数 | 135 | 11 | 校验并归一**号段**（`segments_json`）的人工输入。 |
| `parse_segments` 函数 | 163 | 10 | 库里的行 → 号段元组。 |
| `classify_org_kind` 函数 | 184 | 4 | 按名称关键词给**单位性质**粗分类（NULL = 分不出、挂「未分类」）。 |
| `backfill_org_kind` 函数 | 222 | 6 | 给**未分类**（org_kind IS NULL）的行回填单位性质（关键词粗分类）。 |
| `upsert_channel` 函数 | 242 | 34 | 插入或更新一条渠道。 |
| `_exists` 函数 | 312 | 6 | — |
| `get_channel` 函数 | 318 | 25 | — |
| `list_channels` 函数 | 324 | 30 | 按筛选条件列出渠道（面板表格的数据源）。 |
| `record_probe` 函数 | 343 | 12 | 运行期探针结果落库（R3 调用）。 |
| `set_enabled` 函数 | 376 | 5 | 人工启停一个渠道（停用的**不删**：历史健康度是要留的证据）。 |
| `delete_channel` 函数 | 398 | 4 | 删除一条渠道。 |
| `summary` 函数 | 416 | 181 | 面板头部用的小结：**能力数**（wiring=wired）与**注册数**分开报。 |
| `load_seed` 函数 | 433 | 18 | 读渠道种子（引擎自有 JSON）。 |
| `seed_channels` 函数 | 443 | 19 | 把种子灌进台账（幂等。 |

### `src/core/storage/clause_repo.py`（27 个符号）

> 条款仓储：写入 clause_revision / source_span / clause_fts / clause_vec。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_standard_body` 函数 | 32 | 9 | 从标准号里抽「主体数字」，**抽不到就返回 None（调用方不兜底）**。 |
| `_std_body_hits` 函数 | 77 | 5 | `body` 是否以**数字边界**出现在 `doc_standard_no` 的主体里。 |
| `make_clause_key` 函数 | 98 | 7 | — |
| `content_hash` 函数 | 102 | 79 | — |
| `_store_form_doc` 函数 | 132 | 2 | 折 doc_meta 里那几列的存储形。 |
| `ensure_law_source_columns` 函数 | 151 | 2 | 官方来源溯源列迁移（docs/LAW-SOURCE-PLAN.md §5）：。 |
| `ensure_content_hash_column` 函数 | 164 | 8 | Task 10.4 迁移：clause_revision 增加 content_hash（快照可验证，红线 v2 #2）。 |
| `ensure_page_breaks_column` 函数 | 189 | 5 | B3 迁移（2026-09-01）：clause_revision 增加 page_breaks（页界 run-start 编码）。 |
| `ensure_figure_html_column` 函数 | 202 | 4 | C2 迁移（2026-09-01）：clause_revision 增加 figure_html（插图占位通道）。 |
| `ensure_catalog_hidden_column` 函数 | 214 | 6 | 目录卫生迁移（2026-08-28）：doc_meta 增加 catalog_hidden。 |
| `ensure_additive_columns` 函数 | 232 | 27 | **追加列**迁移的**唯一入口**：保证"读代码需要的列"都存在（纯 ALTER，**不回填**）。 |
| `_ensure_content_hash_once` 函数 | 264 | 5 | 迁移在进程内只执行一次。 |
| `_seg` 函数 | 280 | 47 | FTS 分词：**委托给 text_utils 的唯一实现**（2026-09-17）。 |
| `insert_document` 函数 | 290 | 88 | 写入 doc_meta 一行。 |
| `insert_page_geometries` 函数 | 329 | 4 | — |
| `insert_clauses` 函数 | 340 | 31 | 批量写入条款 + FTS + 向量索引（独立短事务）。 |
| `insert_clauses_in_txn` 函数 | 347 | 18 | 在调用方事务内写入条款+FTS+向量（T05 管线用：整个入库单事务原子提交）。 |
| `delete_document` 函数 | 418 | 41 | 删除文档并清理其全部数据。 |
| `_serialize_vec` 函数 | 467 | 4 | — |
| `insert_edges_in_txn` 函数 | 475 | 5 | 在调用方事务内写入证据依赖图边。 |
| `_reindex_clause_indexes` 函数 | 494 | 15 | 补丁写入/回滚后同步 FTS 与向量索引（须在调用方事务内执行）。 |
| `upsert_patch` 函数 | 520 | 23 | 创建/更新纠错补丁：补丁 + FTS 重写 + 向量重算 同事务原子提交。 |
| `list_patches` 函数 | 587 | 4 | — |
| `delete_patch` 函数 | 600 | 6 | 删除补丁 = 回滚到不可变原始值（FTS/向量按原文重算）。 |
| `migrate_patches` 函数 | 626 | 4 | Task 10.4 补丁跨修订平移（P1 数据正确性，v5.1 附录 #5）。 |
| `fetch_full_clause` 函数 | 712 | 45 | — |
| `resolve_clause` 函数 | 822 | 34 | 按 标准号+条款号 精确解析条款（引用兜底：LLM 引用未进证据列表的条款时用）。 |

### `src/core/storage/debug_dump_retention.py`（1 个符号）

> `debug_dump` 的**保留策略**（唯一所有者）——两类记录**各自清理**，互不挤占。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `prune` 函数 | 69 | 11 | 只裁**这一类**记录到最新 `keep` 条。 |

### `src/core/storage/doc_delete.py`（1 个符号）

> 文档批量显式级联删除（2026-08-31，用户验收批量删除 UI 后接线）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `delete_documents` 函数 | 34 | 11 | 删除指定文档及全部级联数据。 |

### `src/core/storage/impact.py`（1 个符号）

> R49 影响面分析（Phase 9 完整版）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `analyze_impact` 函数 | 14 | 3 | 旧版被新版替代时的影响面报告。 |

### `src/core/storage/material_repo.py`（22 个符号）

> 材料平面仓库（2026-09-17 定位转移 Phase A）：项目 / 材料 / 切片 的读写。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `materials_root` 函数 | 60 | 3 | 材料原件存放根：`<data_dir>/materials/<project_id>/`。 |
| `materials_dir` 函数 | 68 | 23 | 某个项目的参考资料文件夹（**独立目录**：材料与法规语料分开放，便于各自备份/清理）。 |
| `create_project` 函数 | 76 | 22 | 建项目。 |
| `get_project` 函数 | 91 | 12 | — |
| `list_projects` 函数 | 99 | 10 | — |
| `_project_row` 函数 | 107 | 3 | — |
| `ensure_additive_columns` 函数 | 114 | 27 | **追加列**迁移的唯一入口（本模块的表由本模块自己管）。 |
| `add_material` 函数 | 132 | 50 | 登记一份材料。 |
| `get_material` 函数 | 180 | 42 | — |
| `_material_row` 函数 | 194 | 4 | — |
| `list_materials` 函数 | 205 | 35 | 列材料（**管理/评审界面用**，可以含未批准的）。 |
| `approved_materials` 函数 | 221 | 16 | **硬门**：只有已批准的材料才允许进入检索/分析/引用。 |
| `set_review` 函数 | 231 | 49 | 批准 / 拒绝（用户评审闸门）。 |
| `set_tier` 函数 | 243 | 7 | 改**来源可信度**（用户可改，留痕）。 |
| `set_task_role` 函数 | 262 | 10 | 声明**任务内效力**（轴 B）：`criterion`=本任务准则 / `reference`=参考 / None=未声明。 |
| `set_lifecycle` 函数 | 273 | 6 | `ephemeral`（默认，仅本次任务）↔ `promoted`（用户提名升为长期参考）。 |
| `link_doc` 函数 | 284 | 9 | Track L：评审通过并**入法规库**后，从材料侧回指 `doc_meta.doc_id`（法条链零改动）。 |
| `add_chunks` 函数 | 294 | 23 | 写入切片（并同步 `material_fts`）。 |
| `search_materials` 函数 | 328 | 41 | 在**已批准**材料里做全文检索，返回带**引用所需字段**的命中。 |
| `delete_material` 函数 | 389 | 6 | 删除材料（连同切片与检索索引）。 |
| `material_chunks` 函数 | 398 | 18 | — |
| `chunk_count` 函数 | 407 | 22 | — |

### `src/core/storage/sqlite_db.py`（17 个符号）

> SQLite 连接管理与初始化（WAL + 外键 + busy_timeout + sqlite-vec 扩展）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_register` 函数 | 30 | 4 | — |
| `load_vec_extension` 函数 | 37 | 143 | 加载 sqlite-vec 扩展。 |
| `_configure` 函数 | 49 | 2 | — |
| `get_db_connection` 函数 | 59 | 448 | 线程局部连接。 |
| `write_transaction` 函数 | 74 | 248 | 短事务上下文：由单写者队列调用，普通代码不应直接绕过队列写库。 |
| `init_schema` 函数 | 96 | 68 | — |
| `_ensure_doc_meta_columns` 函数 | 127 | 2 | 给既有知识库 doc_meta 补新增列（CREATE IF NOT EXISTS 不会改已有表）。 |
| `_rename_table_in_ddl` 函数 | 151 | 2 | `CREATE TABLE old (` → `CREATE TABLE new (` —— 只换**表名**那一处，别动列名/约束里的字串。 |
| `_ensure_legal_status_reference` 函数 | 159 | 5 | 幂等：把效力枚举补上 `reference`（返回**重建了几张表**。 |
| `_ensure_bookmark_folder_columns` 函数 | 220 | 3 | 幂等：仅对缺列执行 ALTER TABLE ADD COLUMN。 |
| `_ensure_channel_columns` 函数 | 237 | 2 | 幂等：仅对缺列执行 ALTER TABLE ADD COLUMN（与上面两条同形）。 |
| `list_tables` 函数 | 245 | 11 | — |
| `close_thread_connection` 函数 | 253 | 49 | — |
| `_forget` 函数 | 262 | 2 | 把这份连接从跨线程登记表里摘掉（关掉它的时候调）。 |
| `_conn_db_path` 函数 | 268 | 2 | 连接指向的**主库文件**（拿不到返回 None：连接已关/查询失败）。 |
| `close_connections_under` 函数 | 284 | 5 | 关掉**主库文件落在 ``root`` 之下**的那些连接（**只**关自己那一份库，不碰别人的）。 |
| `close_all_connections` 函数 | 324 | 30 | 把**所有线程**上登记的库连接都关掉，返回关掉的个数。 |

### `src/core/storage/user_data.py`（32 个符号）

> 用户资产层（阶段4）：收藏 R25 / 批注 R33 / 项目清单 R34 / 义务清单 R-L9。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `add_bookmark` 函数 | 17 | 12 | 条款级收藏。 |
| `remove_bookmark` 函数 | 41 | 3 | — |
| `remove_bookmark_by_clause_key` 函数 | 47 | 2 | 按 clause_key 取消收藏（取消收藏 toggle 用。 |
| `list_bookmarks` 函数 | 54 | 9 | — |
| `bookmarked_clause_keys` 函数 | 67 | 13 | — |
| `add_doc_bookmark` 函数 | 75 | 10 | 收藏一本标准（纯书签）。 |
| `remove_doc_bookmark` 函数 | 101 | 3 | — |
| `remove_doc_bookmark_by_doc` 函数 | 109 | 4 | 按 doc_id 取消收藏（顶部按钮 toggle 用）。 |
| `list_doc_bookmarks` 函数 | 117 | 7 | — |
| `bookmarked_doc_ids` 函数 | 127 | 4 | — |
| `_require_folder` 函数 | 135 | 7 | 应用层引用完整性：folder_id 必须已存在（老库补列无表级 FK）。 |
| `create_folder` 函数 | 145 | 93 | 新建收藏夹。 |
| `rename_folder` 函数 | 166 | 10 | — |
| `delete_folder` 函数 | 182 | 14 | 删除收藏夹：**只删夹，收藏回「未分类」**（folder_id 置 NULL），绝不连坐删收藏。 |
| `list_folders` 函数 | 198 | 4 | 全部收藏夹（含计数：doc 收藏数 + 条款收藏数），按创建时间升序。 |
| `get_folder` 函数 | 210 | 1 | — |
| `move_bookmark_to_folder` 函数 | 218 | 1 | 把一条条款收藏移入夹 / 移回未分类（folder_id=None）。 |
| `move_doc_bookmark_to_folder` 函数 | 229 | 1 | 把一条标准收藏移入夹 / 移回未分类（folder_id=None）。 |
| `move_bookmark_by_clause_key` 函数 | 240 | 5 | 按 clause_key 移动条款收藏（新收藏入库时指定夹的 toggle 路径）。 |
| `move_doc_bookmark_by_doc` 函数 | 251 | 3 | 按 doc_id 移动标准收藏（新收藏入库时指定夹的 toggle 路径）。 |
| `folder_scope` 函数 | 262 | 31 | 夹内提问的检索范围（ks_answer 过滤链数据源）。 |
| `add_annotation` 函数 | 291 | 4 | — |
| `list_annotations` 函数 | 303 | 2 | — |
| `delete_annotation` 函数 | 315 | 3 | — |
| `annotations_by_clause_keys` 函数 | 321 | 5 | — |
| `create_project` 函数 | 336 | 22 | — |
| `add_clause_to_project` 函数 | 345 | 4 | — |
| `remove_clause_from_project` 函数 | 361 | 3 | — |
| `list_projects` 函数 | 375 | 10 | — |
| `save_obligation_list` 函数 | 383 | 2 | — |
| `update_obligation_list` 函数 | 394 | 1 | — |
| `get_obligation_list` 函数 | 402 | 1 | — |

### `src/core/storage/versioning.py`（3 个符号）

> 版本替代链与条款对比（Phase 6：R29 替代链 / R42 版本对照 / R49 模态变化清单）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `version_chain` 函数 | 18 | 5 | 沿 superseded_by 双向展开版本链（旧→新，含自己）。 |
| `_clause_index` 函数 | 42 | 5 | — |
| `compare_docs` 函数 | 56 | 17 | 两文档条款对照（R42 版本对照 / R16 跨标准对比共用）。 |

### `src/core/storage/write_queue.py`（11 个符号）

> 单写者队列：所有写操作排队串行执行（短事务），并落 event_log 审计。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `WriteWorker` 类 | 14 | 9 | 后台单写者线程，串行消费 write_queue 表。 |
| `__init__` 函数 | 17 | 135 | — |
| `start` 函数 | 28 | 323 | — |
| `_recover_stale_processing` 函数 | 37 | 2 | 崩溃恢复：上次运行卡在 processing 的任务重置为 pending（启动时无并发写者，安全）。 |
| `stop` 函数 | 48 | 132 | — |
| `_run` 函数 | 57 | 73 | — |
| `_execute_serial` 函数 | 74 | 2 | — |
| `_claim_next` 函数 | 83 | 2 | — |
| `_finish` 函数 | 102 | 3 | — |
| `enqueue` 函数 | 114 | 6 | — |
| `wait_until_drained` 函数 | 124 | 7 | — |

### `src/core/storage/write_queue_bootstrap.py`（4 个符号）

> 单写者队列消费端接线（2026-08-26，P2-①）：引擎启动时启动 WriteWorker，

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ingest_doc` 函数 | 21 | 5 | — |
| `_handle` 函数 | 44 | 2 | — |
| `start_write_worker` 函数 | 53 | 10 | 引擎启动时调用（server.run 内，uvicorn 拉起前）。 |
| `stop_write_worker` 函数 | 63 | 7 | 引擎退出时调用。 |

### `src/core/supervisor.py`（14 个符号）

> Python 侧引擎看门狗（阶段2.1，外部评审 P2 响应 / T09 前置）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ChildHandle` 类 | 25 | 4 | supervisor 对子进程的最小依赖面（测试注入 FakeChild）。 |
| `exitcode` 函数 | 32 | 9 | — |
| `pid` 函数 | 34 | 622 | — |
| `start` 函数 | 36 | 323 | — |
| `join` 函数 | 37 | 732 | — |
| `is_alive` 函数 | 38 | 17 | — |
| `_engine_entry` 函数 | 41 | 2 | — |
| `_mp_child_factory` 函数 | 46 | 3 | — |
| `EngineSupervisor` 类 | 53 | 6 | — |
| `__init__` 函数 | 54 | 135 | — |
| `_heartbeat_ok` 函数 | 66 | 2 | P8 心跳：读 session 文件里的 port，探测 /health。 |
| `run` 函数 | 82 | 282 | 阻塞运行。 |
| `_emit` 函数 | 121 | 7 | — |
| `main` 函数 | 127 | 1131 | — |

### `src/core/text_utils.py`（61 个符号）

> OCR 文本清洗公共模块（2026-08-23 整合）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `strip_formula_leader` 函数 | 125 | 27 | 公式编号引导点线清洗（幂等）：'……………( 1 / 式中：' → ' (1) / 式中：'。 |
| `normalize_pua_latin` 函数 | 142 | 20 | PUA 错位字体文本层 → 可切分文本（幂等。 |
| `normalize_pua_separators` 函数 | 172 | 8 | PUA「分隔符类 / 装饰类」字符处理（2026-09-15 立，当天二次扩容）。 |
| `strip_block_noise` 函数 | 232 | 12 | 行级通用噪音清洗（2026-08-29，GB/T 34406 实测，语料级。 |
| `reflow_sqrt_formulas` 函数 | 255 | 5 | 根号套分式的行序重排（2026-08-29，GB/T 34406 式(1)(2) 实测，语料级）。 |
| `normalize_math_symbols` 函数 | 305 | 3 | 纯文本里的 LaTeX 命令泄漏 → Unicode 符号（幂等。 |
| `_glue_formula_fragments` 函数 | 377 | 2 | 行级粘合公式内无歧义的劈开形态（见上方常量注释）。 |
| `_glue_split_values` 函数 | 389 | 4 | 数值被劈开的合并：'6 10 g'→'610 g'、'1 00 µ'→'100 µ'（单位锚定）。 |
| `_glue_two_letter_units` 函数 | 413 | 2 | 已知 2 字母单位去空格（'m m'→'mm'、'k g'→'kg'、'p H'→'pH'）。 |
| `glue_ocr_spaced_units` 函数 | 434 | 25 | OCR 通道的保守粘合（2026-09-14，OCR 循环轮次 4/7/12 同类问题 3 次达线）。 |
| `glue_spaced_formulas` 函数 | 533 | 10 | 修复"公式字母被拉开"：PDF 文本层逐字符定位 → 提取出 "C a O"、"Y ₂ O ₃"。 |
| `weave_meaning_marks` 函数 | 605 | 10 | 「式中」符号说明行的平均值 bar 织入（2026-08-29，语料级统计记法规则）。 |
| `normalize_wraps` 函数 | 635 | 16 | OCR 折行拼接。 |
| `_find_brace_group` 函数 | 666 | 3 | 从 s\[start\]（应为 '{'）读平衡花括号组。 |
| `_wrap_frac_operand` 函数 | 687 | 3 | \frac 分子/分母含运算符（表达式）→ 括号保护，保语义可读。 |
| `_convert_frac_tag` 函数 | 695 | 2 | \frac{A}{B} → 'A/B'（表达式加括号）。 |
| `_strip_latex_arrays` 函数 | 756 | 3 | LaTeX `array` 环境 → 可读文本（2026-09-15 收敛循环第 5 轮根因）。 |
| `normalize_label_comma` 函数 | 795 | 4 | 标签逗号代点归一：'(D,8)'→'(D.8)'、'表B,4'→'表B.4'。 |
| `latex_to_text` 函数 | 809 | 37 | MinerU <eq> LaTeX → 可读文本。 |
| `_collapse_latex_spacing` 函数 | 884 | 4 | LaTeX 转文本后的逐字符空格归并（2026-09-15，全库公式审计）。 |
| `clean_eq_tags` 函数 | 916 | 22 | 把 content_markdown/content_html 里的 <eq>LaTeX</eq> 转成可读文本（其余标签保留）。 |
| `html_unescape` 函数 | 923 | 11 | HTML 实体解码（&lt; → < 等）。 |
| `strip_tags` 函数 | 931 | 5 | 剥除 HTML 标签 + 解码实体（表格单元格 → 纯文本）。 |
| `strip_embedded_table_text` 函数 | 953 | 7 | 后端版 stripEmbeddedTable：正文里与表格重复的文字块剔除。 |
| `_tex_alpha` 函数 | 1022 | 5 | 单字符 → TeX 可用 ASCII 字母。 |
| `_katex_span` 函数 | 1034 | 3 | — |
| `katex_sym_html` 函数 | 1039 | 12 | 展示 html 的式中说明行符号 token → KaTeX span（幂等。 |
| `pua_bond_dash_html` 函数 | 1086 | 17 | 展示 html 的 PUA 键横线 → em dash（幂等。 |
| `sup_unit_exponents_html` 函数 | 1103 | 9 | 展示 html 的单位负指数 → <sup> 上标（幂等。 |
| `space_clause_numbers_html` 函数 | 1120 | 10 | 展示 html 的段首条款编号补空格（幂等。 |
| `sup_unit_exponents_text` 函数 | 1131 | 7 | 入库清洗：cm-1 → cm⁻¹ Unicode 上标（与 latex_to_text 上标纪律一致，。 |
| `space_clause_numbers_text` 函数 | 1148 | 7 | 入库清洗：段首条款编号补空格（re.M 行首=normalize_wraps 后段首）。 |
| `clean_latex_for_katex` 函数 | 1164 | 4 | MinerU OCR 公式 LaTeX → KaTeX 可渲染（2026-09-02，需求1）。 |
| `normalize_area_subscript` 函数 | 1206 | 9 | 面积下标纠正（出口 reflow，幂等）：'A ° > 1.25 m²' 的 'A°' 实为下标。 |
| `canon_standard_no` 函数 | 1280 | 20 | 标准号归一（**仅供比较**，不用于展示）：全角→半角、统一破折号、去空白与斜杠、大写。 |
| `store_standard_no` 函数 | 1296 | 60 | 标准号的**存储形**：把全角 `／`（U+FF0F）/`－`（U+FF0D）折成半角，**其余一字不动**。 |
| `store_standard_name` 函数 | 1330 | 12 | **名称**列的存储形：只折全角斜杠 `／`→`/`，**一个连字符都不动**。 |
| `_match_std` 函数 | 1341 | 1 | 从页眉判据的匹配里重建标准号（前缀族 + 可选分册字母 + 号 + 年）。 |
| `standard_key` 函数 | 1358 | 48 | 把标准号压成比较键 `号-年`。 |
| `segment_for_fts` 函数 | 1365 | 89 | FTS 用的**唯一**分词实现：jieba `cut_for_search` + 空格连接。 |
| `_porter_stem` 函数 | 1401 | 6 | 取 SQLite **自带** `porter` 分词器给出的词干（带缓存）。 |
| `_plain_case` 函数 | 1440 | 2 | **没有内部大写**：全小写，或只有首字母大写。 |
| `_latin_prefix_token` 函数 | 1453 | 5 | 把拉丁字母词换成 `"词干"*` 前缀查询。 |
| `fts_match_expr` 函数 | 1481 | 118 | FTS5 `MATCH` 表达式的**唯一**构造器（2026-09-17 集中到此处）。 |
| `standard_no_key` 函数 | 1532 | 25 | 标准号的**比较键**（只用于"是不是同一部标准"的判断，**不是**存储格式）。 |
| `law_name_key` 函数 | 1561 | 21 | **法规名**的比较键（只用于"是不是同一部法规"，**不是**存储格式）。 |
| `_inside_unclosed_tag` 函数 | 1615 | 5 | `s\[start:at\]` 里是否有一个**未闭合的标签开头**（⇒ `at` 处的 `<` 在标签内部）。 |
| `_inside_raw_text` 函数 | 1634 | 4 | `at` 是否落在**内容按原样显示**的元素内部（复核 b10 的 LOW-1）。 |
| `_strip_script_style` 函数 | 1680 | 9 | 丢掉 `script`/`style` **及其内容**（含**自闭合**与**未闭合**两种形态）。 |
| `html_to_text` 函数 | 1752 | 72 | HTML → 紧凑纯文本（**页面/表格通用**的规范实现）。 |
| `looks_like_binary` 函数 | 1825 | 13 | 这段"文本"其实是**二进制容器**吗？（**文本入口**用。 |
| `looks_like_binary_bytes` 函数 | 1860 | 9 | **真实字节**是不是二进制容器（采集器在拿到 `resp.content` 时用这个）。 |
| `strip_duplicate_suffix` 函数 | 1888 | 12 | 去掉名称**结尾**的副本后缀 `(1)`/`（2）`（只动结尾，中间的合法括号不动）。 |
| `strip_ocr_source_suffix` 函数 | 1915 | 31 | 剥掉标准号**结尾**的来源后缀 `(OCR采集)`（只此一种，其余一字不动）。 |
| `clean_standard_name` 函数 | 1954 | 13 | 文件名（或原始串）→ **干净的标准名称**（展示用，不改内容）。 |
| `_match_key` 函数 | 1997 | 3 | — |
| `_std_matches` 函数 | 2002 | 5 | 该匹配是否可视为页眉。 |
| `_sub_own_header` 函数 | 2011 | 3 | 只删"号 + 年 == 自家标准号"的行尾页眉，其余原样保留。 |
| `_strip_wm_tokens` 函数 | 2021 | 2 | 剥掉一行里的全部水印 token，返回残留。 |
| `strip_watermark_lines` 函数 | 2040 | 39 | 站点水印行剥离（幂等）：整行删掉，正文行一字不动。 |
| `clean_clause_text` 函数 | 2128 | 17 | **入库文本清洗链的唯一所有者**（次序即契约，2026-09-15 立）。 |

### `src/core/update/announce.py`（27 个符号）

> 公告发现（announcement discovery，2026-09，KS×DSH 决策 19 延伸）：自定义公告源

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `normalize_url` 函数 | 110 | 15 | URL 归一化：scheme/host 小写、去默认端口、path 去尾斜杠（根保留）、。 |
| `url_hash` 函数 | 138 | 19 | 归一化 URL 的 SHA-256 小写 hex（去重键）。 |
| `_host_is_private` 函数 | 143 | 2 | 主机名是否指向内网/保留地址：字面量 IP 直接判。 |
| `is_private_url` 函数 | 169 | 20 | SSRF 检查：仅 http/https。 |
| `_read_json_key` 函数 | 183 | 9 | — |
| `_write_json_key` 函数 | 195 | 12 | — |
| `get_sources` 函数 | 204 | 15 | — |
| `_validate_source_payload` 函数 | 209 | 4 | 新增/编辑源的字段校验：必填、scheme、SSRF（默认禁内网）→ 非法抛 UPD-3008。 |
| `add_source` 函数 | 223 | 20 | — |
| `update_source` 函数 | 239 | 7 | 部分更新：name/enabled/note 可改。 |
| `remove_source` 函数 | 267 | 4 | 删源：announcement_observed 记录保留（历史公告留档，source_name 快照可读）。 |
| `_parse_date` 函数 | 280 | 2 | 列表条目日期解析：取**最后一个**合理年份（1990-2100）的匹配——公告日期。 |
| `looks_like_article` 函数 | 308 | 7 | 这个 URL 像**文章页**（而不是栏目目录/导航）吗？见上面那段说明（只否掉目录型）。 |
| `parse_list_page` 函数 | 314 | 9 | 通用列表页启发式解析：候选 <a> 抽取 → 噪音/静态资源/栏目导航过滤 → 绝对化 →。 |
| `_get_state` 函数 | 361 | 7 | — |
| `_set_state` 函数 | 366 | 5 | — |
| `_min_interval_hours` 函数 | 370 | 2 | — |
| `_scan_soft_cap_s` 函数 | 379 | 2 | 扫描全程软上限（秒）。 |
| `get_scan_state` 函数 | 391 | 5 | 最近一次扫描快照（从未扫过 → status=never，恒可读）。 |
| `request_scan` 函数 | 397 | 18 | 扫描入口（端点调用）：时间闸 + 409 双闸 + 僵尸自愈 → 起 daemon 线程。 |
| `_run_scan_thread` 函数 | 439 | 2 | — |
| `run_announce_scan` 函数 | 458 | 2 | 逐源串行扫描：fetch → parse → 去重落库（每源一个短事务）→ 状态逐源写回。 |
| `discover_next_pages` 函数 | 527 | 5 | 从**当前这一页**找出后续页 URL（不含当前页。 |
| `_unseen_count` 函数 | 584 | 2 | 这一页的条目里，有多少条**还没见过**（用于"连续几页没新东西就提前停"）。 |
| `_scan_one_source` 函数 | 605 | 2 | 单源扫描：抓取（预算内，**逐页**）→ 解析 → 去重落库。 |
| `list_items` 函数 | 736 | 13 | 已见公告查询（host 最近列表/历史展示用）：。 |
| `export_announce_xlsx` 函数 | 769 | 4 | 《公告发现》Excel 到 exports 目录：Sheet1 最近扫描（源状态逐源）+。 |

### `src/core/update/change_repo.py`（8 个符号）

> 变更仓储：update_check_batch / update_change_event 读写（阶段六·批次1）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `create_batch` 函数 | 43 | 5 | 新建巡检批次（status=pending），返回批次行 dict。 |
| `get_batch` 函数 | 66 | 5 | 读单个批次。 |
| `list_batches` 函数 | 74 | 2 | 历史批次（created_at 倒序）。 |
| `update_progress` 函数 | 83 | 2 | 原子累加进度计数（首查自动盖 started_at）。 |
| `append_change` 函数 | 103 | 6 | 写入一条标准变更事件，返回 change_id（``chg_<ULID>``）。 |
| `mark_ack` 函数 | 191 | 12 | 用户确认变更事件（user_ack=0/1），留审计。 |
| `manual_status` 函数 | 239 | 4 | 人工维护法律状态（manual 渠道语义）：校验枚举、原值入审计 before_state。 |
| `_batch_dict` 函数 | 275 | 3 | — |

### `src/core/update/channel_answers.py`（5 个符号）

> 五类能力表（§11.0 R6c）：每条渠道能回答哪几类问题。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load_answers` 函数 | 37 | 17 | 读能力表。 |
| `answers_of` 函数 | 47 | 4 | 这条渠道能答哪几类。 |
| `verdict_of` 函数 | 53 | 4 | 该渠道在该类上的**能力判定**：`"supported"` / `"partial"` / `None`（没有审计记录）。 |
| `channels_for` 函数 | 72 | 44 | 能回答 `cls` 的渠道（按台账顺序）。 |
| `coverage` 函数 | 93 | 90 | 给报告用的小结：每类多少条、每条能答几类、置信与来源分布。 |

### `src/core/update/channel_probe.py`（7 个符号）

> 渠道健康探针（§11.0 R3）：把"这个渠道今天还活着吗"变成**可实测、可落库**的一件事。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_count_links` 函数 | 57 | 4 | 数 HTML 里 `<a>` 标签的个数（R6 的"JS 空壳"判据）。 |
| `_validate_target` 函数 | 77 | 4 | 校验**一条**目标（读表时一次性做掉。 |
| `load_targets` 函数 | 166 | 19 | 读探针目标表。 |
| `_classify` 函数 | 182 | 13 | (state, error_code, error_message)。 |
| `failure_kind` 函数 | 245 | 60 | 失败码 → 人话前缀（面板的失败原因列读的是它）。 |
| `probe_channel` 函数 | 254 | 18 | 探一个渠道，返回 `{state, error_code, error, latency_ms, http, body_head, expect}`。 |
| `probe_channels` 函数 | 319 | 7 | 批量探针：默认**只探配了目标的渠道**。 |

### `src/core/update/channel_test.py`（7 个符号）

> 渠道的「已知文件测试」（批C，2026-09-22 业主定案）：每条渠道配一个**已知文件**

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `default_fetcher` 函数 | 34 | 2 | 默认拉取器：标准库 GET，10s 超时，只收 2xx。 |
| `identify_standard_no` 函数 | 41 | 8 | 从文本里识别标准号（第一个命中）。 |
| `_norm_no` 函数 | 47 | 6 | 比对口径：去空格、破折号归一、统一大写（大小写/横竖线不该决定成败）。 |
| `set_test_case` 函数 | 52 | 6 | 给渠道配/改「已知文件」（样本链接 + 期望标准号）。 |
| `get_test_case` 函数 | 72 | 8 | — |
| `run_channel_test` 函数 | 79 | 8 | 跑这条渠道的「已知文件测试」：拉样本 → 识别标准号 → 比对期望 → 落痕。 |
| `_record` 函数 | 115 | 6 | — |

### `src/core/update/channels/__init__.py`（1 个符号）

> 更新渠道适配器包（可插拔，F-02/F-11/F-12）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_safe_import` 函数 | 28 | 13 | 容错导入子代理正在实现的渠道（未完成/语法错不阻塞整体启动，记 warn）。 |

### `src/core/update/channels/base.py`（31 个符号）

> 更新渠道适配器基座（阶段六·批次1）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `UpdateError` 类 | 54 | 116 | 更新模块专用异常（LlmError 同风格：message + ``UPD-xxxx`` 错误码）。 |
| `__init__` 函数 | 57 | 135 | — |
| `upd_log` 函数 | 78 | 106 | 按 pipeline/05 §1 规约输出一条结构化日志行（引擎日志同格式采集）。 |
| `norm_no` 函数 | 95 | 95 | 标准号归一（**匹配**用）：去空白与斜杠、折各种连字符、大写。 |
| `query_no` 函数 | 115 | 39 | **查询用**写法：把全角斜杠 `／` 换成半角 `/`（其余**原样保留**）。 |
| `strip_year` 函数 | 132 | 10 | 去掉归一号尾部的年代（GBT3608-2008 → GBT3608），用于同主体候选比较。 |
| `pick_row_by_norm` 函数 | 137 | 14 | 按归一号挑选匹配行（mee/hbba/official_gb 三处重复算法的统一收敛）。 |
| `map_state_text` 函数 | 159 | 21 | 中文状态串 → legal_status 枚举。 |
| `derive_change_type` 函数 | 164 | 22 | 确定性推导渠道级 change_type（各适配器共用，保证矩阵逐位可复现）：。 |
| `looks_like_captcha` 函数 | 182 | 24 | 验证码特征检测：body 显式 captcha 标记，或文本含验证码特征词。 |
| `ChannelResult` 类 | 199 | 115 | — |
| `recordable` 函数 | 233 | 9 | 结果是否允许落变更表：captcha 只返回标记，绝不写库（04a INS-C-01）。 |
| `CurlCffiTransport` 类 | 242 | 19 | 浏览器指纹默认传输（ANOM-002 canonical 修复）：curl_cffi impersonate chrome。 |
| `__init__` 函数 | 259 | 135 | — |
| `fetch` 函数 | 263 | 1027 | — |
| `fetch_bytes` 函数 | 280 | 9 | 原始字节下载（公告 PDF 存档用）：返回 (status, content)，不解析。 |
| `fetch_page` 函数 | 288 | 23 | 取回一个**页面**，把同一个响应的四样东西一起给出：。 |
| `HttpxTransport` 类 | 310 | 19 | 回退真实传输（curl_cffi 不可导入时兜底。 |
| `fetch` 函数 | 317 | 1027 | — |
| `fetch_bytes` 函数 | 335 | 9 | 原始字节下载（公告 PDF 存档用）。 |
| `fetch_page` 函数 | 344 | 23 | 同 `CurlCffiTransport.fetch_page`（契约一致：`(status, headers, text, raw)`）。 |
| `httpx_usable` 函数 | 355 | 8 | httpx 在这台机器上**构造**得起来吗？（返回 `(可用, 原因)`）。 |
| `default_transport` 函数 | 378 | 25 | 默认 transport 工厂：curl_cffi 可导入则优先（TLS 指纹模拟），。 |
| `ChannelAdapter` 类 | 401 | 39 | 渠道适配器抽象：probe(standard_no) -> ChannelResult（接口冻结）。 |
| `__init__` 函数 | 408 | 135 | — |
| `probe` 函数 | 412 | 301 | 探测单个标准号的最新官方状态。 |
| `_fetch` 函数 | 416 | 19 | transport 归一调用：超时/异常统一翻成 UpdateError（UPD-1xxx），HTTP 状态不抛。 |
| `_ua` 函数 | 436 | 2 | 抓页面用的 User-Agent 串。 |
| `_fetch_text` 函数 | 440 | 6 | GET 一个页面返回 HTML 文本。 |
| `_log_probe` 函数 | 463 | 22 | 每次探测必落一条结构化日志（含耗时 ms，pipeline/05 §1）。 |
| `_miss` 函数 | 477 | 27 | 统一未命中出口：HTTP 非 200 不抛错，交由降级链决策。 |

### `src/core/update/channels/class_outcomes.py`（4 个符号）

> 五类**结论**的组装（§11.0 R6c-4）：把"这一次探测"翻译成"五类各自答成什么样"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `conclusion_for` 函数 | 62 | 15 | 一根棒的探测结果 → 它对**这一类**的结论。 |
| `_verdict` 函数 | 118 | 2 | 该渠道在该类上的能力判定（来自 b35 的逐条审计）。 |
| `build_classes` 函数 | 129 | 11 | `route_report` + "谁答的" + 那根棒的结果 → 五类结论汇总。 |
| `build_classes_for_miss` 函数 | 165 | 6 | **整条链都没命中**时的五类记录（没有"谁答的"这回事）。 |

### `src/core/update/channels/cssn.py`（9 个符号）

> cssn适配器（2026-08-27 实测定型，全覆盖状态权威）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `CssnAdapter` 类 | 66 | 18 | cssn：标准号级状态探测（全覆盖、无验证码、确定性、离线可测、异常归一）。 |
| `probe` 函数 | 75 | 301 | — |
| `_search_row` 函数 | 86 | 3 | 带空格完整号单次搜索（契约：每渠道恰一次请求）。 |
| `_hit` 函数 | 96 | 25 | 单次搜索后精确挑选匹配行（禁验证码硬闯。 |
| `_pace` 函数 | 121 | 17 | 调用间限速（Jiasule/商业站礼貌速率）。 |
| `_split` 函数 | 127 | 8 | 归一号 → (数字主体, 年份)。 |
| `_pick` 函数 | 136 | 24 | 跨前缀同主体挑选（GB/GB/T/GB/Z 视为同一标准的不同属性/版本）。 |
| `_state_of` 函数 | 175 | 5 | cssn 状态串 → legal_status。 |
| `_from_row` 函数 | 183 | 6 | — |

### `src/core/update/channels/dbba.py`（1 个符号）

> dbba适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `DbbaAdapter` 类 | 23 | 2 | dbba：地方标准信息服务平台（标准号级状态探测，同 hbba 结构）。 |

### `src/core/update/channels/govcn_announce.py`（6 个符号）

> gov.cn 公告检索 + PDF 存档适配器（govcn，F-02 降级链末端 / F-03 公告存档）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_version` 函数 | 32 | 5 | 版本号排版归一：贴着 - / 的空白收敛、多空白合一（比较仍走 norm_no）。 |
| `GovcnAnnounceAdapter` 类 | 45 | 18 | 公告渠道：发布/废止公告即证据。 |
| `__init__` 函数 | 57 | 135 | — |
| `probe` 函数 | 62 | 301 | — |
| `_pick` 函数 | 120 | 24 | 命中规则：**标题或摘要**归一后含标准号。 |
| `archive_pdf` 函数 | 140 | 29 | 归档最近一次命中的公告 PDF 到 <data_dir>/announcements/，返回绝对路径。 |

### `src/core/update/channels/hbba.py`（6 个符号）

> hbba适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_epoch_ms_to_date` 函数 | 50 | 4 | epoch 毫秒 → YYYY-MM-DD（CST）。 |
| `_sacinfo_state` 函数 | 61 | 2 | sacinfo 状态串 → legal_status 枚举。 |
| `_SacinfoQueryAdapter` 类 | 69 | 5 | sacinfo 行业/地方标准查询平台共享实现（hbba/dbba 同构）。 |
| `probe` 函数 | 79 | 301 | — |
| `_pick_row` 函数 | 140 | 15 | 行挑选：精确归一号匹配优先。 |
| `HbbaAdapter` 类 | 145 | 4 | hbba：行业标准信息服务平台（标准号级状态探测，确定性、离线可测、异常归一）。 |

### `src/core/update/channels/laws_db.py`（3 个符号）

> 国家法律法规数据库适配器（laws_db，flk.npc.gov.cn，FRB F-22 真机版）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `LawsDbAdapter` 类 | 28 | 4 | 法律法规渠道（F-22）：标题精确/模糊检索 → 状态映射 → ChannelResult。 |
| `_search` 函数 | 35 | 3 | — |
| `probe` 函数 | 49 | 301 | — |

### `src/core/update/channels/ledger_chain.py`（14 个符号）

> 台账驱动的降级链（§11.0 R6c，第一步**只算不改**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ledger_fallback_chain` 函数 | 48 | 15 | 按台账**过滤**兜底链（纯函数。 |
| `chain_for_number` 函数 | 77 | 30 | 某号**巡检实际会用**的链：`routing.select_chain(no)` 再按台账**过滤 + 按号段加尾巴**。 |
| `_segment_channels` 函数 | 111 | 2 | 按台账**号段**命中本号的渠道（台账顺序，保序去重。 |
| `segments_report` 函数 | 134 | 10 | 号段（`segments_json`）落地情况的报告 —— **给快照脚本与人工维护用**（§11.0 R7）。 |
| `ledger_chain_report` 函数 | 224 | 19 | 给快照脚本用：链、被谁挡住、"可提升为兜底成员的候选"、以及代码/台账不一致。 |
| `_as_tuple` 函数 | 295 | 4 | 名单可以是任何可迭代（类型注解写 tuple，但**传生成器也照收**）。 |
| `_dedupe` 函数 | 305 | 9 | 保序去重（重复成员由 `ledger_chain_report` 的 `roster_duplicates` 点名告警）。 |
| `_adapter_names` 函数 | 321 | 7 | — |
| `_channel_id_of` 函数 | 326 | 4 | — |
| `_name_candidates` 函数 | 330 | 6 | `ch:ndls` ⇒ {ndls}。 |
| `_wiring` 函数 | 337 | 7 | `wiring` 归一（去空白 + 小写）。 |
| `_enabled_off` 函数 | 348 | 3 | `enabled` 是否表示"人工停用"（容忍 `0` / `'0'` / `False`，但**不**把 `None` 当停用）。 |
| `_is_excluded` 函数 | 362 | 7 | — |
| `_exclusion_reason` 函数 | 366 | 3 | 进不了链的原因（**人工意图与已知失效是硬过滤**。 |

### `src/core/update/channels/mee.py`（7 个符号）

> mee 适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_cell_text` 函数 | 59 | 8 | 取表格行内指定 colid 单元格的可见文本（剥标签、unescape、去空白）。 |
| `build_pdf_url` 函数 | 68 | 2 | 逆向 PDF 全文 URL：colid=7 隐藏列内嵌完整下载地址（实测无 token/附加接口）。 |
| `spaced_candidate` 函数 | 91 | 2 | 压缩输入 → 官方空格形态候选（引擎空格敏感）：HJ819-2017 → HJ 819-2017。 |
| `parse_report_page` 函数 | 103 | 3 | 解析报告页 HTML → 记录行列表（标准号/名称/实施时间/摘要/pdf_url）。 |
| `MeeAdapter` 类 | 124 | 2 | mee：标准号级状态探测（确定性、离线可测、异常归一）。 |
| `probe` 函数 | 129 | 301 | — |
| `_pick_row` 函数 | 173 | 15 | 行挑选：精确归一号匹配优先。 |

### `src/core/update/channels/mem_gov.py`（4 个符号）

> mem_gov适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MemGovAdapter` 类 | 34 | 3 | mem_gov：应急管理部 AQ 行业标准（标准号级状态探测，确定性、离线可测、异常归一）。 |
| `probe` 函数 | 39 | 301 | — |
| `_search_announcement` 函数 | 70 | 4 | 在公告列表+详情里找目标标准号，返回 (公告URL, kind\|None)。 |
| `_parse_list_links` 函数 | 105 | 5 | 解析公告列表页 -> \[(href, 标题)\], 仅保留含 废止/批准/发布/标准 的公告项。 |

### `src/core/update/channels/mohurd.py`（4 个符号）

> mohurd适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MohurdAdapter` 类 | 29 | 2 | mohurd：住建部工程建设标准（标准号级状态探测，确定性、离线可测、异常归一）。 |
| `probe` 函数 | 34 | 301 | — |
| `_search_announcement` 函数 | 56 | 4 | — |
| `_parse_list_links` 函数 | 84 | 5 | — |

### `src/core/update/channels/ndls.py`（12 个符号）

> ndls适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `NdlsAdapter` 类 | 67 | 18 | ndls：标准号级状态探测（确定性、离线可测、异常归一）。 |
| `probe` 函数 | 78 | 301 | 探测单号状态。 |
| `_headers` 函数 | 142 | 35 | — |
| `_search_body` 函数 | 153 | 2 | 与站点前端 getSearchData(paramsType=1) 同款 JSON 体（2026-08 实测）。 |
| `_pace` 函数 | 167 | 17 | 真实网络调用间限速（Jiasule WAF 观察模式）。 |
| `_dash_norm` 函数 | 174 | 5 | 标准号匹配归一：长横/短横统一为连字符后再 norm_no（站点数据含 en-dash）。 |
| `_state_of` 函数 | 179 | 5 | ndls 状态串 → legal_status。 |
| `_pick_search_row` 函数 | 187 | 2 | 搜索结果行挑选：code==0 且 results 非空。 |
| `_detail_data` 函数 | 215 | 2 | 详情 JSON → data 字典。 |
| `_from_row` 函数 | 222 | 6 | 搜索行降级结果（详情不可用时）：状态/日期取自列表行，缺废止日期/代替关系。 |
| `_from_detail` 函数 | 249 | 4 | — |
| `_newer_version` 函数 | 288 | 2 | 代替关系中找比请求号更新的同主体标准号（确定性。 |

### `src/core/update/channels/official_gb.py`（6 个符号）

> 国家标准全文公开系统适配器（openstd.samr.gov.cn，F-02 主渠道）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_impl_date` 函数 | 36 | 13 | 结果表一行里的日期格 → **实施日期**（`ChannelResult.effective_date` 的语义）。 |
| `_pub_date` 函数 | 60 | 11 | 同一行的日期格 → **发布日期**（第 1 格，`ChannelResult.published_date`）。 |
| `OfficialGbAdapter` 类 | 71 | 9 | 主渠道：命中即止（降级链 official_gb→web→govcn 由 inspector 编排）。 |
| `probe` 函数 | 81 | 301 | — |
| `_pick_row` 函数 | 154 | 15 | 行挑选：精确归一号匹配优先。 |
| `_pace` 函数 | 158 | 17 | 调用间限速（政府站礼貌速率）。 |

### `src/core/update/channels/proxy_rotate.py`（18 个符号）

> 代理轮换（IP 旋转）与请求间隔随机化（2026-08-27 实测定型）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `random_gap` 函数 | 43 | 5 | 请求间隔随机化：均匀分布 \[min_s, max_s\]（max_s<=min_s 时返回固定值）。 |
| `_decode_chunked` 函数 | 51 | 2 | HTTP chunked transfer 解码（mihomo pipe 响应实测为 chunked）。 |
| `pipe_http` 函数 | 67 | 4 | 经 Windows named pipe 调 mihomo RESTful API。 |
| `ClashRotator` 类 | 106 | 3 | 通过 verge-mihomo named pipe 切换代理节点，换出口 IP。 |
| `__init__` 函数 | 114 | 135 | — |
| `available` 函数 | 124 | 12 | pipe 可达且能拿到代理列表（Clash 运行中）。 |
| `_switch` 函数 | 145 | 3 | 切 group 的当前选择到 target（节点或组）。 |
| `rotate` 函数 | 152 | 13 | 切到下一个国家落地组（round-robin），返回代理出口 URL。 |
| `ProxyListPool` 类 | 186 | 3 | 静态代理列表（数据区文件，每行一个 proxy URL，空行/# 注释忽略）。 |
| `__init__` 函数 | 194 | 135 | — |
| `rotate` 函数 | 205 | 13 | — |
| `__len__` 函数 | 209 | 3 | — |
| `ProxyCurlTransport` 类 | 214 | 6 | 带代理的 curl_cffi transport（新实例 = 新 session = 新 cookie）。 |
| `__init__` 函数 | 220 | 135 | — |
| `fetch` 函数 | 224 | 1027 | — |
| `fetch_bytes` 函数 | 237 | 9 | — |
| `fetch_page` 函数 | 242 | 23 | 与 `base.CurlCffiTransport.fetch_page` 同契约（采集侧要 Content-Type 与真实字节）。 |
| `build_rotator` 函数 | 253 | 3 | 按配置构建旋转器：--proxies 文件优先，否则尝试 Clash。 |

### `src/core/update/channels/question_router.py`（8 个符号）

> 按问题选渠道（§11.0 R6c-3）：把"这一号该问谁"变成可调用的一层，**先只读**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_norm_classes` 函数 | 45 | 3 | 归一类别入参：`None` = 五类全要。 |
| `_to_channel_id` 函数 | 69 | 7 | 台账渠道 id 归一：适配器名 `ndls` ⇒ `ch:ndls`。 |
| `_chain_ids` 函数 | 83 | 3 | 这一号的链（已归一成渠道 id、保序去重）。 |
| `_states` 函数 | 100 | 3 | 渠道 id → 探针 state。 |
| `_order_by_ability` 函数 | 108 | 4 | 同一类里按**能力判定**排：`supported` → 未审计 → `partial`（组内保持链序）。 |
| `channels_for` 函数 | 142 | 44 | 五类 → 候选渠道（**按链的顺序**排）。 |
| `route_report` 函数 | 182 | 24 | 同 `channels_for`，但**每类多给一个原因**（空候选别写成同一个理由）。 |
| `unanswerable_classes` 函数 | 231 | 4 | `route_report` 里候选为空的类（调用方据此写 `unanswerable`，**别写 `not_found`**）。 |

### `src/core/update/channels/routing.py`（6 个符号）

> 渠道适配器索引：新增渠道在此注册，inspector 按标准号特征路由。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_store_form` 函数 | 20 | 4 | 标准号 → 存储形（去空白 + 折半角），供前缀匹配用。 |
| `fallback_chain` 函数 | 62 | 24 | 泛查兜底链的**唯一访问点**（§11.0 R6）。 |
| `first_route` 函数 | 73 | 22 | 这一号的**前缀首选**渠道（没命中任何前缀规则 ⇒ `None`）。 |
| `select_chain` 函数 | 89 | 72 | 按标准号特征返回降级链（首选权威渠道在前，其余兜底在后）。 |
| `_fold_segment` 函数 | 114 | 6 | 号段写法与标准号**共用的折叠口径**（`_store_form` + 去掉所有空白）。 |
| `segment_matches` 函数 | 129 | 7 | 这一号的**存储形**是否落在该号段内（前缀匹配。 |

### `src/core/update/channels/std_samr_hb.py`（4 个符号）

> std_samr_hb适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `StdSamrHbAdapter` 类 | 47 | 2 | std_samr_hb：行业标准目录标准号级状态探测（确定性、离线可测、异常归一）。 |
| `probe` 函数 | 56 | 301 | — |
| `_pick_row` 函数 | 108 | 15 | 行挑选：精确归一号匹配优先。 |
| `_pace` 函数 | 112 | 17 | 调用间限速（政府站礼貌速率）。 |

### `src/core/update/channels/ttzb.py`（12 个符号）

> ttbz适配器（2026-08 实测，巡检时效）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_pick_dates` 函数 | 87 | 10 | 三级回退取（**实施日期, 发布日期**）——两个日期两个槽（§11.0 R6c-3e）。 |
| `_canon` 函数 | 105 | 7 | 归一号 + 破折号归一：平台用长横 U+2014，用户常写 -，两者等价比较。 |
| `_core` 函数 | 110 | 3 | 去年代（兼容 - 与 —）：TZSA328-2026 → TZSA328，供同主体候选比较。 |
| `TtzbAdapter` 类 | 115 | 3 | ttbz：标准号级状态探测（确定性、离线可测、异常归一）。 |
| `probe` 函数 | 120 | 301 | — |
| `_rows_of` 函数 | 142 | 14 | 检索应答 → 行表。 |
| `_pick_row` 函数 | 151 | 15 | 行挑选：精确归一号匹配优先。 |
| `_resolve_detail` 函数 | 166 | 2 | — |
| `_raw_of` 函数 | 220 | 2 | — |
| `_extract_json_ld` 函数 | 239 | 2 | 取 @type=TechArticle 的 JSON-LD 块。 |
| `_extract_portal` 函数 | 250 | 2 | portal-standard-detail-json 结构化字段（含 standardStatusName/各日期）。 |
| `_extract_status_line` 函数 | 261 | 2 | 状态行（全页唯一 el-tag span）：现行/即将实施/被代替/废止。 |

### `src/core/update/channels/web_fallback.py`（3 个符号）

> 网络逐号补漏搜索适配器（web，F-02 降级链第二棒 / F-12 兜底）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_version` 函数 | 35 | 5 | 版本号排版归一：贴着 - / 的空白收敛、多空白合一（比较仍走 norm_no）。 |
| `WebFallbackAdapter` 类 | 42 | 8 | 逐号补漏：标题含完整标准号即视为命中，证据链接随结果返回。 |
| `probe` 函数 | 48 | 301 | — |

### `src/core/update/data_package.py`（9 个符号）

> 全量数据包导出/导入（阶段六·批次4）：F-26 数据打包/还原 + 成功简报。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `brief_counts` 函数 | 92 | 6 | 七项简报计数（逐表 COUNT。 |
| `_connect_ro` 函数 | 99 | 3 | 以只读 URI 打开 sqlite 文件（绝不产生 -wal/-shm 副文件写入）。 |
| `export_package` 函数 | 108 | 10 | 全量打包到 dest_dir 下的 ``ks_data_package_<时间戳>/``，返回 (目录, manifest)。 |
| `_copy_announcement_pdfs` 函数 | 169 | 2 | 拷贝公告存档 PDF 到 files/announcements/。 |
| `_quarantine_listing` 函数 | 192 | 2 | quarantine 隔离区清单（只列条目，不拷损坏件本体）。 |
| `import_package` 函数 | 211 | 11 | 校验数据包并准备导入（整体替换语义），成功返回含导入简报的 manifest。 |
| `_target_nonempty` 函数 | 288 | 2 | — |
| `_load_registry` 函数 | 292 | 3 | — |
| `_append_registry` 函数 | 303 | 2 | — |

### `src/core/update/discover.py`（19 个符号）

> 找标子模块（阶段六·批次3）：口语找标的分类映射、网络检索与待下载清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load_seed` 函数 | 72 | 18 | 加载 CCS 二级种子树（进程内缓存。 |
| `_children_of` 函数 | 84 | 6 | — |
| `_major_name` 函数 | 91 | 4 | — |
| `_validate_rules` 函数 | 236 | 2 | 规则路径必须能落到种子树节点（启动期一次性校验，fail-fast）。 |
| `_candidate` 函数 | 250 | 4 | — |
| `_clean_desc` 函数 | 264 | 7 | 去口语虚词，返回清洗后文本（两轮剥前缀/尾缀，处理嵌套如"帮我找…的标准"）。 |
| `_ccs_enum` 函数 | 295 | 2 | CCS 二级子类紧凑清单（一次生成进程缓存，LLM prompt 用）。 |
| `_parse_llm_json` 函数 | 307 | 6 | 从 LLM 输出容错提取首个 JSON 对象（容忍前后缀/代码块围栏）。 |
| `_validate_ccs_code` 函数 | 319 | 8 | 强校验 LLM 输出的 code ∈ 种子树二级子类。 |
| `_llm_classify` 函数 | 331 | 7 | LLM 按需分类（规则 miss 时调用）。 |
| `classify` 函数 | 384 | 45 | 口语描述 → CCS 路径或一轮追问（协议见模块头注。 |
| `_ask` 函数 | 464 | 5 | 追问出口：单轮 ≤3 问一次问完。 |
| `search` 函数 | 471 | 782 | 按分类路径查网络渠道，返回结果卡片列表（字段见模块头注，F-17）。 |
| `_to_card` 函数 | 541 | 2 | 渠道原始结果行 → 结果卡片。 |
| `_now_iso` 函数 | 571 | 7 | — |
| `_parse_items` 函数 | 575 | 8 | app_config 原始串 → 清单条目。 |
| `download_later_list` 函数 | 590 | 6 | 待下载清单（读 app_config 'discover.download_later'）。 |
| `download_later_add` 函数 | 595 | 7 | 加入清单（幂等：norm_no 相同视为同一标准，重复添加不产生重复条目）。 |
| `download_later_remove` 函数 | 616 | 6 | 移出清单（不存在则为无操作。 |

### `src/core/update/download_gate.py`（4 个符号）

> 下载新版附件的**审批门**（spec 011 第 ③ 条，2026-10-12）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_source_of` 函数 | 44 | 2 | 从 URL 取主机名（问句里给用户看"从哪来"）。 |
| `download_ask_reason` 函数 | 53 | 4 | 弹框问句（**唯一所有者**）：说清**来源 + 形态 + 用途**，不贴全文。 |
| `handle_download` 函数 | 72 | 6 | 按审批结果处置。 |
| `_do_download` 函数 | 101 | 5 | 真正去下（**复用** `govcn_announce.archive_pdf` 的实现与校验）。 |

### `src/core/update/inspector.py`（31 个符号）

> 巡检编排器（阶段六·批次2）：万级分层调度执行引擎。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get_config` 函数 | 90 | 19 | 读 app_config 单值。 |
| `set_config` 函数 | 98 | 18 | upsert app_config 单值（短事务）。 |
| `_today` 函数 | 107 | 8 | 本地日期串（预算按自然日滚动。 |
| `_utcnow` 函数 | 112 | 1 | — |
| `daily_budget_limit` 函数 | 117 | 7 | tier1 全库滚动日预算：app_config inspect.daily_full_sweep_budget 可覆盖。 |
| `budget_used_today` 函数 | 126 | 6 | 今日已消耗额度（跨批次累计。 |
| `budget_remaining` 函数 | 145 | 7 | — |
| `_consume_budget` 函数 | 149 | 2 | 在既有写事务内累加今日消耗（调用方保证 tier1 才调用）。 |
| `_load_batch` 函数 | 159 | 10 | 读 bulk_import_batch 控制面行。 |
| `get_inspect_batch` 函数 | 173 | 10 | 读单个巡检控制面批次。 |
| `_load_checkpoint` 函数 | 181 | 3 | — |
| `select_standard_nos` 函数 | 192 | 16 | 按层取巡检清单：tier0=watch_list∪标准收藏(user_doc_bookmark)∪未首检∪已订阅领域。 |
| `create_inspect_batch` 函数 | 228 | 37 | 新建巡检批次：bulk_import_batch 控制面行 + update_check_batch 同值锚行。 |
| `_transition_status` 函数 | 267 | 8 | 状态迁移双写（控制面 + 锚行）。 |
| `ProbeOutcome` 类 | 293 | 17 | 单号编排结论：judged（已判定）/ failed（预算耗尽）/ captcha（验证码挂起）。 |
| `judge_result` 函数 | 311 | 6 | 渠道结果 → (change_type, 色)。 |
| `_probe_number` 函数 | 334 | 22 | 工作线程入口：单号走降级链，只触网不触 DB，异常归一为 Outcome。 |
| `_classes_info` 函数 | 457 | 3 | 五类结论 → 要并进 `latest_info` 的那几个键（§11.0 R6c-4c）。 |
| `_classes_info_for_miss` 函数 | 485 | 3 | 整链都没命中（灰号）时的五类记录：说清"每一类为什么没答"（§11.0 R6c-4c）。 |
| `_build_adapters` 函数 | 503 | 8 | 构造全部渠道适配器（含 2026-08 新增的权威渠道）。 |
| `_commit_outcome` 函数 | 534 | 6 | 单号原子提交：事件（防重）+ 四色计数 + 断点推进 + 预算消耗，一事务完成。 |
| `_debt_from_events` 函数 | 620 | 3 | 从**本批已落库的事件**里回收结构性欠账（§11.0 R6c-4e，复核 b39 的 B②）。 |
| `_write_captcha_wait` 函数 | 658 | 2 | 验证码聚合告警：一次暂停只落一条 update/captcha_wait（UPD-1002，不逐号刷屏）。 |
| `_RunHandle` 类 | 671 | 3 | — |
| `__init__` 函数 | 672 | 135 | — |
| `request_pause` 函数 | 682 | 8 | 非阻塞暂停请求（可在任意线程调用，含渠道 mock 回调）：置位即返。 |
| `pause_batch` 函数 | 692 | 18 | 暂停批次：运行中 → 块边界落断点后转 paused（阻塞至生效）。 |
| `_merged_checkpoint` 函数 | 718 | 3 | — |
| `resume_batch` 函数 | 727 | 29 | 恢复批次：仅 paused 可恢复（同步续跑到终态并返回摘要）。 |
| `run_batch` 函数 | 746 | 53 | 同步执行巡检批次至终态（done/paused），返回批次行。 |
| `captcha_wait_events` 函数 | 921 | 3 | 待人工过点的验证码告警（前端任务卡片数据源）。 |

### `src/core/update/jev_ingest.py`（2 个符号）

> 公告入库的"Jev 管清"那一层（2026-09-24，B2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `judge_one` 函数 | 78 | 11 | 判**一条**公告标题该不该清。 |
| `judge_many` 函数 | 115 | 2 | 批量判（逐条独立。 |

### `src/core/update/report.py`（3 个符号）

> 更新检查报告导出（阶段六·批次4）：F-05《更新检查结果》Excel 版。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `monthly_trend` 函数 | 93 | 6 | 近 N 天（默认 30）全库变更四色计数，按日分桶。 |
| `collect_batch_report_data` 函数 | 114 | 6 | 聚合单批次报告数据（界面 JSON 与 Word 共用）。 |
| `export_batch_report_xlsx` 函数 | 148 | 11 | 生成《更新检查结果》Excel（.xlsx）到 exports 目录，返回文件路径。 |

### `src/core/update/scheduler.py`（12 个符号）

> 定时巡检调度器（阶段六·批次2）：沿用 watcher/单写者队列的轻量轮询线程模式。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_parse_created_at` 函数 | 32 | 3 | sqlite datetime('now') 串 → UTC aware datetime。 |
| `schedule_days` 函数 | 43 | 18 | 读取调度周期天数。 |
| `schedule_tiers` 函数 | 55 | 5 | 自动建批的层清单。 |
| `UpdateScheduler` 类 | 70 | 26 | 定时巡检轮询线程：start() 后台运行，tick() 可独立注入时钟测试。 |
| `__init__` 函数 | 73 | 135 | — |
| `start` 函数 | 82 | 323 | — |
| `stop` 函数 | 90 | 132 | — |
| `_run` 函数 | 98 | 73 | — |
| `_last_scheduled_created_at` 函数 | 112 | 2 | — |
| `_create_scheduled_batches` 函数 | 119 | 5 | 到期则按 schedule_tiers 各建一个 scheduled 批次，返回新批次 id。 |
| `_resume_budget_paused` 函数 | 135 | 2 | 跨日恢复预算停留批次：仅 budget 原因 + 今日有剩余额度才续跑。 |
| `tick` 函数 | 165 | 42 | 一次调度拍：返回本拍动作 {created:\[...\], resumed:\[...\]}（可注入假时钟）。 |

### `src/core/update/scheduler_runner.py`（8 个符号）

> 更新巡检的定时线程（spec 011 第 ① 条）—— 把「已建成但没接线」的调度器接上生产。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_run_batches` 函数 | 56 | 2 | 把建出来的批逐个**执行**（现状缺口：`tick()` 只建不跑）。 |
| `tick_and_run` 函数 | 78 | 7 | 一拍：建批/恢复 → **执行新批**。 |
| `set_scheduler_factory` 函数 | 98 | 3 | 测试用：替换调度器工厂（生产不调）。 |
| `reset_scheduler_factory` 函数 | 104 | 2 | 测试用：还原调度器工厂。 |
| `_loop` 函数 | 110 | 2 | 循环体：直到本线程的 stop 被置位。 |
| `start_update_scheduler` 函数 | 132 | 14 | 拉起巡检线程。 |
| `stop_update_scheduler` 函数 | 146 | 10 | 置位停止并等线程退出。 |
| `is_running` 函数 | 174 | 16 | 线程是否在跑（测试与诊断用）。 |

### `src/core/update/subscriptions.py`（3 个符号）

> 领域订阅存取（FRB F-13/A15）：app_config 键 update.domain_subscriptions（JSON 数组）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get_subscriptions` 函数 | 21 | 5 | 读取订阅列表。 |
| `set_subscriptions` 函数 | 36 | 7 | 全量替换式保存（幂等）。 |
| `subscriptions_as_tags` 函数 | 52 | 1 | tier0 组装用：订阅 tag 集合（inspector 读取路径，轻量）。 |

### `src/core/update/web_ingest.py`（15 个符号）

> 部委公告/规章 → 知识库**正文**入库（切片②，开发史 §10.189 / §10.190）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_inner_html` 函数 | 50 | 2 | 取开标签之后**配对**的那一段（`<div>` 会嵌套，非贪婪正则会切到别的地方去）。 |
| `classify_change_signal` 函数 | 96 | 15 | 标题 → 变更信号（`draft` / `repealed` / `revised` / `issued` / `None`）。 |
| `classify_status` 函数 | 134 | 13 | 标题 → 效力档：`reference`（参考资料/仅参考）/ `withdrawn` / `effective`。 |
| `classify_hierarchy` 函数 | 148 | 11 | 标题 → 法规树那一档（尽力而为，认不出落"其他"。 |
| `extract_body_text` 函数 | 173 | 4 | 详情页 HTML → 正文纯文本（去脚本/样式/注释，优先内容容器，其次全页文本）。 |
| `page_title` 函数 | 200 | 4 | 详情页 `<title>`（抓不到返回空串）——用于和列表页标题交叉核对。 |
| `classify_scope` 函数 | 222 | 29 | 标题 → `normative`（要入库）/ `non_normative`（与法规标准无关的行政事务，不入库）。 |
| `_observed_rows` 函数 | 237 | 4 | `announcement_observed`（已发现的公告）按发布日期 DESC（新的在前）取行。 |
| `_library_keys` 函数 | 254 | 4 | 库里已经有的**来源 URL** 与**标准号（存储形）**两把钥匙。 |
| `_is_in_library` 函数 | 273 | 4 | — |
| `pending_rows` 函数 | 278 | 4 | 已发现但**正文还没进库**的公告。 |
| `ingest_summary` 函数 | 299 | 8 | 入库进度总览（给界面显示"还有多少条没进库"，**不抓网页**）。 |
| `triage_pending` 函数 | 324 | 6 | 给"规则判不收、但要不要真清"的那批**分档**（2026-09-24 B2）。 |
| `ingest_pending` 函数 | 373 | 16 | 把已发现的公告**批量入正文库**（业主报的"应该入库的没入库"就靠它收口）。 |
| `ingest_announcement` 函数 | 443 | 11 | 抓一条公告的详情页 → 抽正文 → 入库。 |

### `src/core/verification/patch_guard.py`（3 个符号）

> 纠错补丁防乱检测（patch guard，2026-08-23 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ratio_cjk` 函数 | 36 | 3 | — |
| `_nonprintable_ratio` 函数 | 42 | 3 | — |
| `check_patch` 函数 | 53 | 12 | 补丁合理性检测。 |

### `src/core/verification/typed_verifier.py`（5 个符号）

> 分型核验器（T06，依据主计划 v4.3 第 8.4 节）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_canon_pairs` 函数 | 36 | 3 | 提取 (浮点值, 规范化单位) 集合。 |
| `_clause_mention_window` 函数 | 66 | 3 | 取输出中**该条款**被提到之处之后的窗口文本并集。 |
| `_describe_unsupported` 函数 | 143 | 3 | 把一条"证据外条款号"升级为**可操作**的说明（不改拦截，只补证据）。 |
| `_norm_cite` 函数 | 205 | 2 | 引用归一：'第5.2.1条'→'5.2.1'。 |
| `verify_llm_output` 函数 | 215 | 53 | evidence_clauses: \[{clause_revision_id, clause_number, standard_no,。 |

### `src/core/vision/local_vision.py`（6 个符号）

> 本地视觉反查（Task 11.4 落地为本地版，替代云端视觉 API）：

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ocr_worker` 函数 | 22 | 2 | 子进程：调 mineru CLI 对图片 OCR（list args，无 shell）。 |
| `_find_mineru_exe` 函数 | 34 | 2 | — |
| `ocr_image_locally` 函数 | 46 | 2 | 图片 OCR → 返回 markdown 文本路径（mp 子进程隔离 + 超时）。 |
| `_rapidocr_text` 函数 | 70 | 2 | RapidOCR 单图文本（行序拼接）。 |
| `ocr_image_text` 函数 | 79 | 2 | 图片 OCR 文本：**本地 RapidOCR 优先**（单图毫秒级，零外发零预算），。 |
| `vision_locate` 函数 | 100 | 7 | 截图反查：OCR 文本（RapidOCR 优先 → 本地 MinerU 回退）→ 混合检索 → 条款。 |

### `tests/_kb_folder_api_fixtures.py`（9 个符号）

> ``/api/v1/kb/*`` 用例的公共夹具（真库不碰：库是 conftest 的临时库）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `uniq` 函数 | 19 | 63 | 本会话内唯一的目录名（session 级库 ⇒ 名字不能撞）。 |
| `mkdoc` 函数 | 24 | 25 | 插一篇最小可用的文档（目录归属只认 doc_meta 里有这一行）。 |
| `mkdoc_full` 函数 | 29 | 39 | 插一篇文档（可带分类信息 ⇒ 让"建议去向"能算出路径）。 |
| `tops` 函数 | 52 | 36 | 四个顶层目录（业主手定 sort 10/20/30/90）——**按名字复用**，用例间共用。 |
| `ensure_folder_path` 函数 | 74 | 6 | 按名字路径**复用或新建**一串目录，返回 ``{名字: folder_id}``（幂等）。 |
| `std_tree` 函数 | 86 | 10 | 真形状的标准树（CCS P16 那一支）——共用，用例间幂等复用。 |
| `api` 函数 | 91 | 1718 | 带 token 的请求（``json`` / ``params`` 透传）。 |
| `data_of` 函数 | 97 | 84 | — |
| `error_code` 函数 | 104 | 92 | — |

### `tests/conftest.py`（5 个符号）

> pytest 全局夹具。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_isolate_data_dir` 函数 | 31 | 27 | 全量测试的会话级临时数据目录。 |
| `db` 函数 | 79 | 1641 | 初始化好 schema 的库连接（会话级临时库。 |
| `seed_data_dir` 函数 | 110 | 11 | 把**本测试独占**的数据目录灌成种子库（有真实语料的库）。 |
| `client` 函数 | 172 | 566 | 带 token 的 FastAPI TestClient。 |
| `_rerank_offline_for_tests` 函数 | 183 | 2 | 全量测试默认禁用 reranker（模型推理极慢），走 R30 降级路径保持检索快速。 |

### `tests/fixtures/make_law_pdf.py`（1 个符号）

> 生成合成法条 PDF（测试 fixture）：编-章-节-条 结构 + 编号条款。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `make_law_pdf` 函数 | 29 | 4 | — |

### `tests/test_announce_ingest.py`（14 个符号）

> 批量入库（切片②下半，开发史 §10.193）：已发现的公告 → 知识库**正文**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_observed` 函数 | 24 | 1 | 每个用例只看见自己造的公告。 |
| `_FakeTransport` 类 | 46 | 13 | — |
| `__init__` 函数 | 47 | 135 | — |
| `fetch` 函数 | 51 | 1027 | — |
| `_t` 函数 | 81 | 119 | — |
| `_mk_observed` 函数 | 85 | 15 | 塞一条"已发现的公告"（真表。 |
| `test_scope_rules_strong_cue_wins_deny_otherwise` 函数 | 99 | 1 | 范围判定：**强规范性线索压过排除词**。 |
| `test_summary_counts_match` 函数 | 123 | 1 | 进度计数：已发现 / 已入库 / 还差多少 / 跳过多少 —— 四个数互相自洽。 |
| `test_ingest_pending_writes_and_is_idempotent` 函数 | 136 | 1 | 批量入库：真写库 + 分档计数 + 非规范性跳过 + **重复跑不重复入** + pending_left 归零。 |
| `test_reingest_reports_already_in_library_not_ingested` 函数 | 176 | 1 | **已经入过的再点一次**：必须报 `skipped/already_in_library`，不许再报"入库成功"。 |
| `test_force_ingests_named_non_normative` 函数 | 219 | 1 | `force=True` 是**逃生口**：范围判错了时业主不必等改代码（连部门决算也入）。 |
| `test_limit_bounds_and_failures_are_honest` 函数 | 231 | 1 | `limit` 封顶（一次点下去不会抓几百页）+ 取不到页如实报 `failed`，且**不算**成入库。 |
| `test_batch_caps_and_dedupe_have_teeth` 函数 | 260 | 1 | 三条"防跑飞"的机制**各自要有判据**（独立复核 MED-2/3/4：此前只有自然语言宣称，。 |
| `test_routes_pending_and_ingest_wire` 函数 | 314 | 1 | 两个端点的**接线**：待入库计数出得来、入库入参原样转下去、非法 limit 给 422。 |

### `tests/test_answer_confidence.py`（10 个符号）

> `answer_confidence` 的判据（2026-10-24 统一化第五批）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_v` 函数 | 38 | 9 | — |
| `_ev` 函数 | 42 | 39 | 造一条证据。 |
| `test_two_call_sites_are_the_same_function` 函数 | 51 | 1 | `server._answer_confidence` 必须是**转发**，不是第二份实现。 |
| `test_both_field_spellings_agree` 函数 | 96 | 1 | 裸名与下划线名必须给出**同一个档位**。 |
| `test_empty_evidence_is_low_not_high` 函数 | 110 | 1 | **空证据 ⇒ low**。 |
| `test_failed_verification_is_low` 函数 | 122 | 1 | — |
| `test_low_confidence_evidence_is_mid` 函数 | 128 | 1 | — |
| `test_all_high_confidence_is_high` 函数 | 134 | 1 | — |
| `test_threshold_boundary` 函数 | 145 | 1 | — |
| `test_missing_confidence_defaults_to_high` 函数 | 150 | 1 | 没有 `type_confidence` 字段时按 1.0 处理（缺字段 ≠ 低可信）。 |

### `tests/test_answer_materials.py`（36 个符号）

> 材料进答案链（Phase B 第二步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 23 | 575 | — |
| `_add` 函数 | 27 | 81 | — |
| `TestNoScopeIsByteIdentical` 类 | 45 | 1 | **回归保证**：不带项目范围时，提示词一个字都不变。 |
| `test_prompt_unchanged_without_materials` 函数 | 48 | 1 | — |
| `test_none_and_empty_string_are_equivalent` 函数 | 55 | 1 | — |
| `TestMaterialsSection` 类 | 61 | 1 | — |
| `test_materials_appended_as_separate_section` 函数 | 62 | 1 | — |
| `test_addendum_carries_criterion_precedence_and_tier_rules` 函数 | 77 | 1 | 规则文本必须真的说了那四件事（**提示词就是产物**，直接断言文字）。 |
| `TestCitationMarkers` 类 | 88 | 1 | — |
| `test_material_marker_does_not_trip_law_index_check` 函数 | 89 | 1 | `\[\[m:0\]\]` 不能被法条越界校验误判（两个平面各有各的编号空间）。 |
| `test_out_of_range_material_marker_is_flagged` 函数 | 96 | 1 | — |
| `test_imagined_material_marker_is_flagged_when_no_materials` 函数 | 102 | 1 | **没给材料却引材料** = 凭想象引用，必须报出来（默认参数下同样成立）。 |
| `test_law_marker_still_checked` 函数 | 108 | 1 | — |
| `test_negative_indices_are_flagged` 函数 | 117 | 1 | **负数越界必须被抓**（独立复核 2026-09-17 报的缺陷）。 |
| `test_conclusion_is_scanned_too` 函数 | 127 | 1 | **结论区也要扫**：规则 1 要求"每条结论后紧跟引用标记"，而旧实现只扫推导区。 |
| `TestAnswerIntegration` 类 | 139 | 1 | 端到端（LLM 用假生成器）：范围 → 取材料 → 进提示词 → 记录可审计。 |
| `_stub_llm` 函数 | 142 | 18 | — |
| `test_scoped_answer_injects_materials_and_records_usage` 函数 | 148 | 1 | — |
| `test_unscoped_answer_has_no_material_usage` 函数 | 169 | 1 | — |
| `test_unapproved_material_never_reaches_prompt` 函数 | 178 | 1 | **评审硬门在答案链上同样成立**：pending 材料的正文不得出现在提示词里。 |
| `test_unknown_project_is_reported_as_not_found` 函数 | 188 | 1 | — |
| `test_t3_lead_only_is_labelled_in_prompt` 函数 | 196 | 1 | **业主验收点的后半句**：单独一条二手转述必须以"仅线索"进提示词，不得当依据。 |
| `test_material_load_failure_is_not_silent` 函数 | 209 | 1 | 材料取不到时必须说出来——否则会产出一份"看着正常、其实没用上制度"的答案。 |
| `TestNaturalLanguageRecall` 类 | 225 | 2 | **我的答案链测试自己抓出来的检索缺陷**（2026-09-17）：。 |
| `seeded` 函数 | 237 | 40 | — |
| `test_natural_language_question_matches` 函数 | 248 | 1 | **最关键的一条**：用户用自然语言提问，必须能命中材料。 |
| `test_standard_number_query_does_not_silently_fail` 函数 | 254 | 1 | 带连字符的标准号不再触发 FTS 语法错误后静默空结果。 |
| `test_expression_builder_quotes_every_term` 函数 | 259 | 1 | 每个词都加引号 ⇒ 标点不可能被当 FTS 语法。 |
| `test_expression_uses_or_not_implicit_and` 函数 | 265 | 1 | — |
| `test_known_limit_all_single_char_query` 函数 | 269 | 1 | **已知边界（钉住，别当 bug 反复"修"）**：全单字符词的查询无 FTS 表达式。 |
| `TestFtsMatchExprIsTheSingleOwner` 类 | 280 | 2 | `fts_match_expr` 必须与法条侧迁走前的旧实现**逐字等价** ——。 |
| `_old_ref` 函数 | 294 | 4 | — |
| `test_matches_old_law_side_implementation` 函数 | 310 | 1 | — |
| `test_latin_prefix_is_the_documented_exception` 函数 | 317 | 2 | **P3.1 的例外要显式钉住**，不能靠"那 15 条恰好没覆盖到"来蒙。 |
| `test_law_side_delegates_to_the_owner` 函数 | 330 | 1 | — |
| `test_duplicate_query_side_tokenizer_is_gone` 函数 | 335 | 1 | verifier 报的"第三份查询侧分词实现"已随迁移**删除**（不是只记一笔）。 |

### `tests/test_api.py`（6 个符号）

> T07' API 壳测试：随机端口+token、/health、401、SSE 事件顺序。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_health_no_token` 函数 | 9 | 1 | — |
| `test_missing_token_401` 函数 | 18 | 1 | — |
| `test_wrong_token_401` 函数 | 24 | 1 | — |
| `test_sse_event_order` 函数 | 31 | 1 | — |
| `test_resolve_clause_marks_basis_scope` 函数 | 49 | 1 | 定位端点必须把「能否作为依据」做成**机器可读**字段（红线：只引现行版）。 |
| `test_resolve_clause_reference_tier_speaks_chinese` 函数 | 111 | 1 | 新增的 `reference` 档（征求意见稿等**仅参考**件）也必须给**中文**禁令说明。 |

### `tests/test_api_cold_start.py`（5 个符号）

> 引擎**冷启动**：一个全新的库（从未入库过任何文档）也要能服务读取端点。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_fresh_client` 函数 | 32 | 8 | **本用例自己的**空数据目录 + 只走 HTTP 的 TestClient。 |
| `test_effect_report_serves_a_brand_new_db` 函数 | 56 | 1 | 冷启动：效力报告不能 500（这是那个缺陷的精确复现式）。 |
| `test_document_catalog_endpoints_serve_a_brand_new_db` 函数 | 67 | 1 | 同一类读者（`server.py` 里也用 `catalog_hidden`）在空库上同样不能 500。 |
| `test_effect_report_docs_endpoint_serves_a_brand_new_db` 函数 | 75 | 1 | 明细端点也走同一个 `_load_docs()`（避免"只修了汇总"）。 |
| `test_bootstrap_guarantees_the_columns_readers_use` 函数 | 88 | 1 | **契约级**钉子：`init_schema()` + `ensure_additive_columns()` 之后，。 |

### `tests/test_api_config.py`（22 个符号）

> 设置→API 配置（云解析/LLM 双通道）单测：注册表写入注入、脱敏、未知通道拒绝。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_FakeKey` 类 | 15 | 13 | — |
| `__init__` 函数 | 16 | 135 | — |
| `__enter__` 函数 | 19 | 9 | — |
| `__exit__` 函数 | 22 | 9 | — |
| `SetValueEx` 函数 | 25 | 12 | — |
| `DeleteValue` 函数 | 28 | 11 | — |
| `FakeWinreg` 类 | 32 | 8 | — |
| `__init__` 函数 | 38 | 135 | — |
| `CreateKeyEx` 函数 | 41 | 5 | — |
| `SetValueEx` 函数 | 45 | 12 | — |
| `DeleteValue` 函数 | 48 | 11 | — |
| `fake_reg` 函数 | 53 | 96 | — |
| `store_dir` 函数 | 64 | 12 | 把加密存储重定向到 tmp（2026-09-11 起凭据写 `secret_store`，不再是注册表）。 |
| `_clean_env` 函数 | 73 | 3 | 每测清理所有相关变量与设置缓存。 |
| `test_set_credential_writes_both_names` 函数 | 84 | 1 | — |
| `test_set_credential_skips_blank_and_dash_clears` 函数 | 94 | 1 | — |
| `test_cloud_dash_clears_base_url` 函数 | 106 | 1 | — |
| `test_unknown_channel_rejected` 函数 | 114 | 3 | — |
| `test_status_never_leaks_key` 函数 | 121 | 1 | — |
| `test_status_accepts_namespaced_llm_key` 函数 | 135 | 1 | 新名（本机保存后的形态）必须让 configured 为真。 |
| `test_settings_reads_cloud_key_from_env` 函数 | 145 | 1 | — |
| `test_settings_cloud_base_url_default` 函数 | 151 | 1 | — |

### `tests/test_appendix_split.py`（12 个符号）

> 附录细分（2026-09-13）：附录内字母章号子条款切分 + 配套既有 bug 修复的回归。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_clause_appendix_regex_forms` 函数 | 25 | 1 | 字母章号三种排版形态全命中。 |
| `re_strip` 函数 | 37 | 2 | — |
| `test_plausible_appendix_head_gates` 函数 | 42 | 1 | 四道护栏：孤立编号/图表题注/引用句/表格数值行全拒绝。 |
| `test_table_caption_accepts_letter_dot` 函数 | 61 | 1 | _TABLE_CAPTION 扩字母点号：表A.1 / 表A. 1 此前 False（45 处失效）。 |
| `test_hierarchy_path_supports_letters` 函数 | 74 | 1 | 层级路径支持字母首段：A.5.2 → 'A > A.5'（此前恒空串）。 |
| `_annex_items` 函数 | 91 | 2 | 附录A 含 3 个子条款 + 1 个表题注 + 1 条表内引用句（假锚点陷阱）。 |
| `test_split_appendix_sub_clauses` 函数 | 108 | 1 | 附录内 A.1/A.2/A.3/A.4 切成独立子条款。 |
| `test_split_appendix_multiline_block` 函数 | 134 | 1 | 附录内多行块：行首 A.N 同样切分（行级分支）。 |
| `test_appendix_split_does_not_touch_normal` 函数 | 154 | 1 | 附录细分的两处分支只在 in_appendix 生效：正文数字条款口径零变化。 |
| `test_lone_number_block_lookahead` 函数 | 167 | 1 | 编号独行块前瞻（GB/T 1032-2023 重导实测）：MinerU 把术语条目拆成。 |
| `test_exact_channel_prefers_letter_clause_no` 函数 | 201 | 1 | _CLAUSE_NO_APPENDIX_RE：E.5.2 不再被截成 5.2（错标准条款）。 |
| `test_expand_title_clauses_gate_accepts_letters` 函数 | 218 | 1 | _expand_title_clauses 门控正则接纳 E.1（两处同步放宽）。 |

### `tests/test_apply_folder_filing.py`（32 个符号）

> `scripts/apply-folder-filing.py`（对真库落库那一步）的用例。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk` 函数 | 50 | 47 | — |
| `_fixture_docs` 函数 | 57 | 2 | 3 篇能归位的 + 379 篇无分类 + 2 篇解析失败（与真库同形的小复制）。 |
| `_make_db` 函数 | 75 | 5 | 建一个小 fixture 库（生产同一套 schema）。 |
| `fdb` 函数 | 110 | 92 | — |
| `_sql` 函数 | 114 | 15 | — |
| `_one` 函数 | 123 | 34 | — |
| `_folder_id` 函数 | 127 | 5 | — |
| `_expected_l2_names` 函数 | 132 | 2 | 两张卡片的第二层名字 —— **与计划同源**（classify_document），不手抄。 |
| `_run` 函数 | 140 | 73 | — |
| `test_dry_run_writes_nothing` 函数 | 147 | 2 | — |
| `test_dry_run_prints_what_would_happen` 函数 | 159 | 1 | — |
| `test_apply_builds_tops_and_skips_the_redundant_level` 函数 | 171 | 1 | — |
| `test_states_and_members_are_exactly_the_plan` 函数 | 194 | 1 | — |
| `test_hidden_docs_go_to_pending_as_failed` 函数 | 207 | 1 | — |
| `test_hidden_doc_with_real_clauses_gets_an_honest_failure_kind` 函数 | 242 | 1 | 库里**有**正文条款还写着"正文条款为零"就是编 —— 必须换成如实的话。 |
| `test_reused_tops_get_the_hand_set_order` 函数 | 258 | 1 | 早先以 sort=0 建出来的顶层目录，复用后 sort 要对齐到业主手定的。 |
| `test_apply_twice_changes_no_counts` 函数 | 274 | 1 | — |
| `test_missing_tables_are_created_and_nothing_else_is_touched` 函数 | 294 | 1 | — |
| `test_ddl_comes_from_schema_sql` 函数 | 313 | 1 | 建表语句必须是**从 schema.sql 现取的**那三张表的（不手抄一份）。 |
| `test_backup_is_taken_and_verified` 函数 | 327 | 1 | — |
| `test_backup_failure_aborts_before_writing` 函数 | 346 | 1 | 备份目录不可用 ⇒ 退出码 2，**库一个字节都没动、一行都没写**。 |
| `_state` 函数 | 367 | 7 | — |
| `test_apply_aborts_when_an_existing_index_is_missing` 函数 | 371 | 1 | ① 先删掉一个既有索引 ⇒ ``--apply`` 必须非 0 且**零写入**。 |
| `test_apply_aborts_when_an_existing_table_gained_a_column` 函数 | 391 | 1 | ② 给既有表**加**一列 ⇒ **不中止**（只登记）。 |
| `test_apply_aborts_when_a_declared_column_is_missing` 函数 | 413 | 1 | ② 库里少了 ``schema.sql`` 声明的列 ⇒ **中止**。 |
| `test_dry_run_prints_zero_write_proof_and_three_size_numbers` 函数 | 440 | 1 | 预演要**打印三个数**（.db / -wal / 合计）与"零写入证据"（第 2 步的措辞修）。 |
| `test_schema_drift_reports_extras_but_does_not_fail_on_them` 函数 | 449 | 1 | ``schema_drift`` 的四个清单各就各位：多列只登记。 |
| `test_declared_objects_splits_sql_despite_comments_and_semicolons` 函数 | 468 | 1 | ``declared_objects`` 必须真的解析出列。 |
| `test_refuses_when_the_unskipped_tree_is_already_there` 函数 | 492 | 1 | 顶层已经有「国家标准·行业标准·团体标准」⇒ 拒绝，免得建出两棵并存的树。 |
| `test_skipped_level_and_top_names_come_from_one_owner` 函数 | 504 | 1 | 「跳过哪一段 / 真顶层叫什么」只有**一个**所有者（复核 2026-09-21 的①）。 |
| `test_read_back_matches_the_database` 函数 | 523 | 1 | 读回自证的数字必须与**直接查库**的结果一致（不是自说自话）。 |
| `test_engine_running_prints_a_warning_but_does_not_block` 函数 | 569 | 1 | 引擎在跑 ⇒ 打印醒目警告，但**不阻塞**（预演仍然跑完、仍然一个字不写）。 |

### `tests/test_assets_endpoint.py`（5 个符号）

> C1 资产端点：parse_out 图片回源 + 防穿越白名单（2026-09-01 排版还原）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_asset` 函数 | 8 | 2 | — |
| `test_asset_served` 函数 | 18 | 1 | — |
| `test_asset_traversal_and_whitelist_rejected` 函数 | 28 | 1 | — |
| `test_asset_bad_doc_id_rejected` 函数 | 37 | 1 | — |
| `test_asset_missing_404` 函数 | 46 | 1 | — |

### `tests/test_auto_tag.py`（3 个符号）

> Task 11.3 自动标签测试：规则层提取 + 红线（不碰原文）断言。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_auto_tag_standard_and_superseded` 函数 | 5 | 1 | — |
| `test_auto_tag_filename_fallback` 函数 | 20 | 1 | — |
| `test_apply_tags_does_not_touch_clause` 函数 | 27 | 1 | — |

### `tests/test_backup.py`（7 个符号）

> Task 13.5 快照备份测试：创建/校验和/滚动淘汰/恢复校验。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_snapshot_create_and_restore` 函数 | 7 | 1 | — |
| `test_snapshot_rollout_auto_keep_7` 函数 | 26 | 1 | — |
| `test_snapshot_checksum_mismatch` 函数 | 41 | 1 | — |
| `test_snapshot_api` 函数 | 53 | 1 | — |
| `test_snapshot_copies_secrets_json` 函数 | 67 | 1 | 批1整改：快照必须把 secrets.json 密文带进备份目录（密钥安全网）。 |
| `test_snapshot_without_secrets_json` 函数 | 96 | 1 | secrets.json 不存在（当前真机正是此状态）→ secrets_copied=False，快照照常成功。 |
| `test_snapshot_secrets_rollout_cleanup` 函数 | 111 | 1 | 自动快照滚动淘汰时 .secrets.json 副本一起删，不留孤儿密文文件。 |

### `tests/test_batch7_security_hardening.py`（10 个符号）

> 整改批 7 安全加固测试（问题清单 #8 #9 #10）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `data_dir` 函数 | 23 | 165 | — |
| `test_crash_mid_write_keeps_previous_state` 函数 | 33 | 1 | 写入中途崩溃（os.replace 之前死掉）→ 主文件保持上一次完整内容。 |
| `test_crash_after_replace_keeps_new_state` 函数 | 62 | 1 | rename 落地后崩溃 → 新状态完整可见（原子写的另一半保证）。 |
| `test_no_partial_tmp_left_after_crash` 函数 | 72 | 1 | 崩溃后残留 tmp 必须是'可识别的半成品'（.tmp 前缀），主文件无恙。 |
| `test_backup_dir_default_is_data_dir_backups` 函数 | 93 | 1 | — |
| `test_backup_dir_env_redirects_outside_data_dir` 函数 | 101 | 1 | KS_BACKUP_DIR 重定向到外部目录（模拟另一块盘）→ 快照落在外部。 |
| `test_snapshot_lands_in_external_backup_dir` 函数 | 112 | 1 | 端到端：重定向下 create_snapshot 的产物落在外部目录。 |
| `test_backup_dir_empty_env_falls_back` 函数 | 125 | 1 | 空串/纯空白 → 回落默认（显式覆盖必须是有意义的值）。 |
| `test_probe_token_records_egress_on_both_paths` 函数 | 135 | 1 | 探测成功/失败都必须留 egress 痕迹（record_egress 被调）。 |
| `test_probe_token_audit_failure_does_not_block` 函数 | 176 | 1 | 审计自身炸掉 → 探测结果照常返回（审计失败不阻塞业务）。 |

### `tests/test_bookmark_folders.py`（14 个符号）

> 收藏夹目录（2026-10 收藏目录功能）：user_data CRUD / 移动 / folder_scope /

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `folder_db` 函数 | 14 | 21 | 种一部文档两条条款 + 两个收藏夹，供夹功能测试。 |
| `_fid` 函数 | 51 | 8 | — |
| `test_folder_crud` 函数 | 59 | 1 | — |
| `test_folder_delete_keeps_bookmarks` 函数 | 79 | 1 | 删夹 → 收藏回未分类（folder_id NULL），收藏行本身绝不删。 |
| `test_add_bookmark_with_folder_and_move` 函数 | 101 | 1 | 带夹收藏 + 移动（同夹改选 = 移动语义）+ 未分类。 |
| `test_folder_scope_union_semantics` 函数 | 136 | 1 | 范围 = 夹内 doc 收藏（整本）∪ 夹内条款收藏（单条）。 |
| `test_folder_endpoints` 函数 | 164 | 1 | — |
| `_monkeypatch_scope` 函数 | 230 | 5 | — |
| `test_answer_folder_id_filters_by_union` 函数 | 235 | 1 | folder_id → 证据限定在（doc_ids ∪ clause_keys）内，notes 如实说明。 |
| `test_answer_folder_id_clause_only_scope` 函数 | 247 | 1 | 条款级收藏 → 只有那一条入范围（同文档其他条款被滤掉）。 |
| `test_answer_folder_id_missing_folder_degrades_honestly` 函数 | 261 | 1 | 夹不存在（folder_scope → None）→ 过滤不执行，notes 如实说明，不静默全库。 |
| `test_answer_folder_id_scope_query_failure_degrades_honestly` 函数 | 269 | 1 | folder_scope 抛异常 → 同上如实降级。 |
| `test_answer_folder_id_empty_folder_returns_empty_honestly` 函数 | 280 | 1 | 空夹 = 合法空范围 → 证据空 + notes 说明已限定（不是查库失败）。 |
| `test_answer_folder_id_widens_candidate_pool` 函数 | 291 | 1 | 夹范围激活时候选池扩容（同 bookmarks_only 的 BOOKMARKS_MIN_TOP_K）。 |

### `tests/test_bulk_import.py`（17 个符号）

> 万级批量导入编排器测试（pipeline/11 契约验收 1~3）。离线，无真实解析。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_bulk_batches` 函数 | 15 | 1 | session 级共享库：每测后清 bulk_ingest 批次与本次创建的骨架行（C 级 pending 标记），防互相干扰。 |
| `make_pdf` 函数 | 25 | 8 | — |
| `make_src_dir` 函数 | 34 | 7 | — |
| `test_fast_scan_creates_skeleton_rows` 函数 | 42 | 1 | 验收1：快扫 → 骨架行（quality_grade=C、pending_parse 标记）+ 批次清单。 |
| `test_fast_scan_dedup_and_quarantine` 函数 | 62 | 1 | 验收1：重复文件防重跳过。 |
| `test_running_batch_rejected` 函数 | 92 | 1 | pending/running/paused 期间拒绝再建（409/UPD-2001 语义，pending 态即拦截）。 |
| `test_pause_resume_and_budget_pause` 函数 | 101 | 1 | 验收2/3：暂停→恢复续跑。 |
| `test_strict_dedup_new_source_not_skipped` 函数 | 136 | 1 | 严格防重：换源（同内容换文件名 / 同标准号换内容）一律不静默跳过。 |
| `test_bad_dir_rejected` 函数 | 165 | 1 | — |
| `test_fast_scan_concurrent_matches_serial` 函数 | 170 | 1 | 增强1：并发快扫（scan_concurrency=4）6 文件 → 6 骨架行、无异常、结果与串行等价。 |
| `test_extract_name_fallback_full_text` 函数 | 183 | 1 | 增强2：首页无名称时从全文回退（第 2 页 ASCII 名称）。 |
| `test_fast_scan_no_cap_scans_all_450` 函数 | 204 | 1 | R-A 验收①：450 文件 + batch_size=200 → 一次 fast_scan 扫完全部（无 200 截断）。 |
| `test_fast_scan_midway_pause_then_resume_finishes` 函数 | 235 | 1 | R-A 验收②：第 250 个文件时外部置 paused → 扫描就近停止且保持 paused。 |
| `_raises_upd` 类 | 277 | 3 | with 助手：断言 UpdateError 且 code 匹配。 |
| `__init__` 函数 | 280 | 135 | — |
| `__enter__` 函数 | 283 | 9 | — |
| `__exit__` 函数 | 286 | 9 | — |

### `tests/test_catalog_hidden_retrieval.py`（20 个符号）

> spec 013 判据：检索路径必须尊重 `catalog_hidden`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mkdb` 函数 | 27 | 4 | 最小库：`doc_meta` + `clause_revision`（含 `catalog_hidden` 增量列）。 |
| `Test可见性片段` 类 | 50 | 0 | 判据的唯一所有者：两个片段函数。 |
| `test_隐藏文档被排除` 函数 | 53 | 0 | — |
| `test_按条款的片段同口径` 函数 | 63 | 0 | ★ 两处必须**同时**排除同一批文档（结构判据钉住，防只改一处）。 |
| `test_列不存在时不加条件` 函数 | 76 | 0 | ★ `catalog_hidden` 是**增量列**（不在 `schema.sql`）⇒ 老库上没有它。 |
| `test_没有隐藏文档时片段仍然生成` 函数 | 91 | 0 | ★ 反向：片段**不依赖"当前有没有隐藏文档"**。 |
| `_real_db` 函数 | 104 | 3 | 真库路径 —— **只认显式点名的 `KS_REAL_DB`**。 |
| `Test那6篇真标准该挡而不是不该挡` 类 | 127 | 0 | ★ 我 2026-10-12 说错过的一句话：那 6 篇真标准"不该被挡" —— **错了**。 |
| `test_隐藏规则是零normal条款而非零条款` 函数 | 135 | 0 | — |
| `test_那6篇真标准只有附录没有正文` 函数 | 142 | 0 | 若**显式点名真库**，直接核那 6 篇的 `normal` 条数为 0。 |
| `Test假样本不进检索` 类 | 165 | 0 | 端到端：**必须显式指向真库**才跑（见下）。 |
| `test_假样本不在检索结果里` 函数 | 182 | 0 | — |
| `Test守卫真的拼进了各通道SQL` 类 | 210 | 0 | ★ 结构判据：**每一条通道**都必须带可见性片段。 |
| `test_三条join通道都带vis_doc` 函数 | 221 | 0 | — |
| `test_fts两条通道都带vis_clause` 函数 | 231 | 0 | — |
| `test_向量通道在Python里筛隐藏文档` 函数 | 239 | 0 | ★ 通道 C（vec0 虚表）**刻意不拼 SQL**，改用 Python 筛 —— 判据钉住这个决定。 |
| `Test隐藏集合本身被算出来` 类 | 254 | 0 | ★ 变异 M4 的缺口：`hidden_doc_ids` 算不算，端到端在**只有假样本**时看不出。 |
| `test_隐藏集合在片段生效时被算出来` 函数 | 262 | 0 | 片段非空 ⇒ 必须去查隐藏集合（不许用 `if False` 之类把它关掉）。 |
| `test_隐藏集合的行为` 函数 | 274 | 0 | 行为判据：真库可达时，隐藏集合必须**恰好等于** `catalog_hidden=1` 的集合。 |
| `test_片段默认参数与生产别名一致` 函数 | 310 | 0 | ★ 结构判据：片段的默认参数**必须**是 `dm.doc_id`。 |

### `tests/test_ccs_chain.py`（77 个符号）

> CCS 三层链 + 查询台账 + 「补全分类号」自愈机制（2026-09-22 业主口径「修机制不是补数据」）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_own_data_dir` 函数 | 55 | 5 | 本模块私有的临时数据目录（照 `tests/test_ks_answer.py` 的先例。 |
| `_offline_embedder` 函数 | 107 | 4 | 向量引擎强制离线（与 `test_ks_answer` / `test_filing_state_pipeline` 同一手法）。 |
| `_no_real_network` 函数 | 118 | 1 | **默认断网**：真 transport 一旦被用上就当场报错，而不是悄悄去打 cssn。 |
| `FakeTransport` 类 | 134 | 31 | 按 **URL 分派**的假传输（契约同 `channels.base`：`fetch(url, **kw) -> (status, body)`）。 |
| `__init__` 函数 | 141 | 135 | — |
| `fetch` 函数 | 150 | 1027 | — |
| `_api_rows` 函数 | 168 | 17 | 官方 JSON 应答（形状照 `channels/cssn.py` 的 docstring）。 |
| `_row` 函数 | 173 | 112 | — |
| `_html` 函数 | 177 | 97 | HTML 列表页（每条 = (标准号, 标题, CCS 原文)）。 |
| `test_keyword_forms_ordered_full_to_bare` 函数 | 197 | 1 | 形式由**精确到宽泛**、且去重（业主：「完整标准号容易搜不到」⇒ 不许只赌一种）。 |
| `test_keyword_form_target_is_also_cleaned` 函数 | 213 | 1 | **关键词与匹配目标必须一起抠干净**（真机实测抓到的我自己的缺陷，回归哨兵）。 |
| `test_keyword_forms_strip_trailing_junk` 函数 | 235 | 1 | **尾部杂字**要能抠掉（真机 380 篇实测：真库标准号字段混着中文）。 |
| `test_two_digit_year_year4_form_matches` 函数 | 256 | 1 | 两位年代（`GB 228-87` = 1987 版）靠 `year4` 那档命中，且目标也是四位号。 |
| `test_not_a_standard_no_is_not_applicable` 函数 | 265 | 1 | **不像标准号的字段 ⇒ `not_applicable`，而且一次网络都不打。 |
| `test_other_edition_match_is_rejected_not_used` 函数 | 282 | 1 | **年份不同的他版不许当命中**（真机实测抓到的真缺陷，会打错标签）。 |
| `test_official_api_hit_reports_source_and_form` 函数 | 305 | 1 | 正例：官方接口命中 ⇒ `source=official_api` 且**记下**是哪种关键词形式命中的。 |
| `test_official_hit_never_calls_web_scrape` 函数 | 320 | 1 | **反向**：官方接口通了就**不许**再抓网页。 |
| `test_official_empty_falls_back_to_web_scrape` 函数 | 335 | 1 | **官方接口永远返回空 ⇒ 必须回退到网页抓取，且来源记为 `web_scrape`**。 |
| `test_keyword_form_escalates_when_full_form_misses` 函数 | 356 | 1 | 完整号搜不到时**继续试**别的形式，并把**真正中的那种**记下来。 |
| `test_html_block_anchored_on_standard_no_not_title` 函数 | 376 | 1 | 网页块必须按**标准号**（`ph_list_title`）切：号↔标题↔CCS 三者对得上。 |
| `test_local_table_hit_needs_no_network` 函数 | 397 | 1 | 人工核实表命中 ⇒ `source=local_table`，且**一次网络都不打**。 |
| `test_seed_file_hit_needs_no_network` 函数 | 406 | 1 | 种子文件命中 ⇒ `source=seed_file`（批量入库那条路：命中即零网络）。 |
| `test_use_network_false_is_local_only` 函数 | 419 | 1 | `use_network=False` ⇒ 只走本地（批量场景/离线重跑的口径）。 |
| `test_transport_error_is_network_failed_not_not_found` 函数 | 429 | 1 | **三层里网络层全炸 ⇒ `network_failed`**，绝不是"官方查无"。 |
| `test_answered_but_no_such_number_is_not_found` 函数 | 446 | 1 | 站点答了、解得出条目、里面确实没有这个号 ⇒ `not_found`（**不是** network_failed）。 |
| `test_broken_html_structure_is_parse_failed` 函数 | 463 | 1 | **两层都答了、却一层都读不出** ⇒ `parse_failed`，如实说"读不出条目"。 |
| `test_official_answers_clearly_so_not_found_even_if_scrape_broken` 函数 | 477 | 1 | 官方答得清清楚楚（条目列表里没有这个号）⇒ `not_found`，**不因网页那层读不出而改口**。 |
| `test_matched_number_without_ccs_says_so` 函数 | 492 | 1 | 站点**有这个号**、但那一行/那一条**没有分类号** ⇒ `parse_failed` 且原因说清是哪种。 |
| `test_empty_standard_no_is_not_a_network_failure` 函数 | 503 | 1 | 没有标准号 ⇒ 如实说"没有号"，**不许**记成网络失败（那会误导人去查网络）。 |
| `test_lowercase_site_code_becomes_readable_uppercase_tag` 函数 | 510 | 1 | 站点给**小写** ``a825`` 时，写出来的标签必须是**读得出来**的大写码。 |
| `test_record_and_apply_tag_are_idempotent` 函数 | 535 | 1 | 写台账 / 追加标签：**幂等**，且**不动**已有的别的标签。 |
| `test_record_failure_keeps_reason_and_leaves_tags_alone` 函数 | 556 | 1 | 未命中 ⇒ 台账记 `outcome` + `reason` + 流水，**domain_tags 一个字都不动**。 |
| `test_record_rejects_unknown_outcome` 函数 | 571 | 1 | 不认识的结论**当场报错**（不许静默写进一个没定义的状态）。 |
| `test_plan_finds_only_missing_ones` 函数 | 581 | 1 | 候选**算出来**：只挑 `doc_type='standard'` 且 `domain_tags` 里没有 `CCS:` 的。 |
| `test_backfill_writes_through_to_db` 函数 | 598 | 2 | **核心**：自愈跑完 ⇒ `domain_tags` 里**真的多了一条** `CCS:…` + 台账有来源。 |
| `test_backfill_rerun_is_noop` 函数 | 633 | 1 | **可重跑 / 幂等**：已经有分类号的篇不再进候选 ⇒ 再跑一遍 = 0 篇。 |
| `test_backfill_all_layers_dead_records_failure_in_db` 函数 | 649 | 1 | **变异②的口径**：三层全掐掉 ⇒ 台账必须**如实记**失败，而不是"什么都没有"。 |
| `test_backfill_cancel_is_honest` 函数 | 672 | 1 | **可中断**：按停 ⇒ 标志置上、没轮到的进 `skipped_list`，`cancelled` 如实。 |
| `test_backfill_busy_is_refused_not_queued` 函数 | 694 | 1 | **同一时刻只跑一批**：已有批次在跑 ⇒ `RuntimeError('ccs_backfill_busy')`（**不排队**）。 |
| `_api` 函数 | 719 | 14 | — |
| `test_api_ccs_summary_and_plan` 函数 | 724 | 1 | `/kb/ccs/summary` 与 `/kb/ccs/plan`：只读、字段齐、**不联网**。 |
| `test_api_ccs_backfill_runs_and_reports_status` 函数 | 741 | 1 | `POST /kb/ccs/backfill` ⇒ 后台真跑。 |
| `test_api_inbox_reports_ccs_reason` 函数 | 759 | 1 | 「待分类」每篇带 `ccs_outcome` / `ccs_reason` —— 界面「没有建议要写明为什么」的依据。 |
| `test_api_ccs_plan_rejects_bad_limit` 函数 | 781 | 1 | 非法 `limit` ⇒ 422（不许静默按默认值跑）。 |
| `_write_pdf` 函数 | 802 | 23 | — |
| `synthetic_parser` 函数 | 812 | 43 | 把解析器换成合成 blocks（真链路，只有"从 PDF 抠 blocks"这一步是假的）。 |
| `test_ingest_records_ccs_source` 函数 | 826 | 1 | 真跑一次入库 ⇒ 标签进 `domain_tags`、**来源进台账**（"每篇都要能说出是哪一层命中的"）。 |
| `test_ingest_records_failure_not_silence` 函数 | 850 | 1 | **反向（本次重做的核心）**：那条链失败时，台账**必须**留下结论与原因。 |
| `_journals` 函数 | 882 | 3 | 备份目录里现有的 ``ccs-undo-*.json``（按名字排序）。 |
| `test_undo_journal_is_written_before_the_first_write` 函数 | 888 | 1 | **先备份、后写库**：第一次网络查询发生时，回退记录**已经在盘上**、。 |
| `test_undo_journal_honours_ks_backup_dir` 函数 | 937 | 1 | 回退记录落在**既有快照那个备份目录**，并**尊重 ``KS_BACKUP_DIR`` 覆盖**。 |
| `test_backfill_refuses_to_start_when_journal_write_fails` 函数 | 958 | 1 | **回退记录写不成 ⇒ 一篇都不写、当场报错**（"备份失败但照写"是明令禁止的）。 |
| `test_revert_restores_tags_and_ledger_verbatim` 函数 | 992 | 1 | **回退真能退**：``domain_tags`` 与 ``doc_ccs_state`` **逐字**回到改前。 |
| `test_revert_twice_is_safe` 函数 | 1031 | 1 | **回退两次是安全的**（幂等）：第二次一篇都不动，如实记"已经是改前的样子"。 |
| `test_revert_does_not_touch_docs_outside_the_batch` 函数 | 1053 | 1 | **反向判据**：回退只动这一批记录里的篇 —— 没被选中的篇（含"也是缺号"的那些）。 |
| `test_missing_split_partitions_and_tracks_each_bucket` 函数 | 1084 | 1 | ``missing_split`` **五桶之和 == total**，且每一桶按台账 ``outcome`` 如实归类。 |
| `test_stop_reason_limit_selected_done_and_no_candidates` 函数 | 1120 | 1 | **为什么停：各是各的值**（业主要求"不许合并成一个结束"）。 |
| `test_selected_batch_cut_by_limit_says_limit_not_selected_done` 函数 | 1157 | 1 | **F1（复核 MED，2026-09-24 修）**：勾选批次被 ``limit`` 截过 ⇒ 说"到量"，。 |
| `test_decide_stop_reason_truth_table` 函数 | 1190 | 1 | **七个值互斥且各是各的**：决策函数按优先级取一个（不许有"两个都对"的糊账）。 |
| `test_revert_also_restores_updated_at` 函数 | 1229 | 1 | **F2（复核 MED，2026-09-24 修）**：回退要把 ``updated_at`` 也**逐字**退回去。 |
| `test_db_path_is_honoured_by_the_worker_thread` 函数 | 1260 | 1 | **F3（复核 LOW，2026-09-24 修）**：``db_path`` 必须一路传到**干活线程**。 |
| `test_broken_domain_tags_is_refused_not_silently_wiped` 函数 | 1295 | 1 | **F4（复核 LOW，2026-09-24 修）**：``domain_tags`` 非空却不是 JSON 数组 ⇒ **拒改**，。 |
| `test_stop_reason_exhausted_when_plan_had_no_remainder` 函数 | 1328 | 1 | ``exhausted`` = **候选扫完了**（计划里没有剩余候选），不是"全库都补上了"。 |
| `test_all_mode_pages_serially_and_stops_at_hard_cap` 函数 | 1352 | 1 | **「全部补完」**：按 ``MAX_BACKFILL_DOCS`` 一页一页串行，撞硬上限就停，**如实说**。 |
| `test_all_mode_refuses_doc_ids_and_allows_zero_limit` 函数 | 1399 | 1 | ``all`` 与勾选篇目**不能同时用**（两件事）。 |
| `test_apply_ccs_tag_replaces_instead_of_appending` 函数 | 1416 | 1 | **HIGH-1**：同一篇**只许有一条** ``CCS:`` 标签 —— 换号是**替换**（就地），不是追加。 |
| `test_force_refresh_tag_and_tree_read_the_same_code` 函数 | 1442 | 1 | **HIGH-1 的端到端判据**：``force=True``（刷新）之后，**台账与分类树读到同一个码**。 |
| `test_backfill_classifies_exceptions_by_type_not_all_network` 函数 | 1473 | 1 | **MED-1 + MED-2**：异常**按类型如实归类并落台账** —— 代码缺陷**不许**冒充网络问题。 |
| `test_run_loop_error_does_not_wedge_running_and_lock` 函数 | 1512 | 1 | **MED-5**：循环体外的异常**不许**把 ``running`` 与锁永久卡死。 |
| `test_api_ccs_summary_reports_stop_reasons_and_split` 函数 | 1550 | 1 | ``/kb/ccs/summary`` 把"还剩多少（拆开）"与"为什么停"的说法**由后端下发**。 |
| `test_api_ccs_backfill_all_flag` 函数 | 1567 | 1 | ``POST /kb/ccs/backfill {"all": true}``：分页跑到硬上限并**如实**说停在硬上限。 |
| `_seed_doc` 函数 | 1592 | 70 | 直接写一行 `doc_meta`（走**唯一所有者** `clause_repo.insert_document`）。 |
| `_tags_of` 函数 | 1610 | 28 | **从库里读**（不是从内存读）—— 这一条是"只改内存不落库必红"的依据。 |
| `_raw_tags` 函数 | 1618 | 14 | ``domain_tags`` 的**原文**（不解析）—— "逐字回到改前"要按字节比。 |
| `_raw_updated_at` 函数 | 1626 | 4 | ``doc_meta.updated_at`` 的原文（F2：回退的**第三处**也要逐字比）。 |
| `_wait_flag` 函数 | 1634 | 2 | 等一个条件成真（超时抛 —— **不许**用 sleep 假装它成真了）。 |
| `_wait_done` 函数 | 1644 | 40 | 等后台线程跑完（超时就抛 —— **不许**用 sleep 假装跑完了）。 |

### `tests/test_ccs_fetcher.py`（4 个符号）

> CCS 自动分类查询测试（2026-08-23 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_ccs_to_tag_fallback_local` 函数 | 5 | 1 | 网络不可用时回退本地映射表（不阻塞入库）。 |
| `test_ccs_to_tag_live_result` 函数 | 16 | 1 | 有网络结果 → 用实时 CCS。 |
| `test_classify_uses_ccs_tag` 函数 | 23 | 1 | 分类优先用 domain_tags 的 CCS 标签（4 级树）。 |
| `test_law_classify_levels` 函数 | 43 | 1 | 法规分类（三级体系《法律法规分类编码体系》）：效力层级 → 法律部门 → 业务领域。 |

### `tests/test_change_ack.py`（7 个符号）

> 巡检确认闭环测试（2026-08-26）：mark_ack 确认废止/被替代时同步写回 doc_meta。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_doc` 函数 | 14 | 31 | — |
| `_mk_change` 函数 | 24 | 5 | — |
| `test_mark_ack_applies_withdrawn_to_doc_meta` 函数 | 37 | 1 | 确认废止变更 → doc_meta.legal_status 同步为 withdrawn + 审计两条。 |
| `test_mark_ack_applies_superseded` 函数 | 52 | 1 | — |
| `test_mark_ack_not_applied_for_new_version` 函数 | 61 | 1 | new_version 变更只确认不落状态（引导导入新版而非改写现行状态）。 |
| `test_mark_ack_cancel_does_not_apply` 函数 | 71 | 1 | 取消确认（ack=False）不落库。 |
| `test_mark_ack_missing_change_raises` 函数 | 81 | 1 | — |

### `tests/test_change_signal.py`（10 个符号）

> **变更信号**（§10.195 目标"实时获取发布/更新/修改/废止"）：判定规则 + 落库。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_change_signal_detected` 函数 | 41 | 1 | — |
| `test_no_signal_when_title_does_not_say_it` 函数 | 46 | 1 | 标题没写变化 ⇒ `None`（**宁漏不猜**：标了没写的＝误导人）。 |
| `test_bare_verb_without_standard_object_is_not_a_signal` 函数 | 66 | 1 | **只有动词、没有“标准/规范/目录/条例”这类对象 ⇒ 不是法规标准的变化**。 |
| `test_real_signals_survive_the_object_requirement` 函数 | 74 | 1 | 加了“必须有对象词”这道闸之后，**真正的信号一条都不能被误杀**。 |
| `test_signal_priority_draft_beats_repealed` 函数 | 88 | 1 | 一条标题可能同时命中多个（「修订征求意见稿」含"修订"、"征求"）⇒ 取优先级最高的。 |
| `test_change_signal_orthogonal_to_legal_status` 函数 | 96 | 1 | **正交**：文件自己现行有效（effective），同时是"某法规被废止"的证据（repealed）。 |
| `test_change_signal_column_exists_and_is_written` 函数 | 103 | 1 | 落库：`doc_meta.change_signal` 列在，且 `ingest_law_text(change_signal=...)` 会写进去。 |
| `test_insert_document_writes_optional_columns_it_lists` 函数 | 122 | 1 | **防回潮（窄口径）**：`insert_document` 的 INSERT 清单里列出来的可空列，得真能写进去。 |
| `test_change_signal_not_written_when_caller_omits` 函数 | 147 | 1 | 不给 `change_signal` ⇒ **不写这列**（既有调用方行为一字不变，`__default__` 哨兵）。 |
| `test_real_db_backfilled_values_match_rule` 函数 | 162 | 1 | **真库回填后逐条复算**（只读。 |

### `tests/test_channel_answers.py`（18 个符号）

> 五类能力表测试（`src/core/update/channel_answers.py` + `channel_answers.json`，§11.0 R6c）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_channel_table` 函数 | 27 | 3 | — |
| `table` 函数 | 34 | 488 | — |
| `Test覆盖与词表` 类 | 38 | 0 | — |
| `test_台账每一条都有声明` 函数 | 39 | 0 | — |
| `test_只许出现五类词` 函数 | 45 | 0 | — |
| `test_每条都有出处与置信` 函数 | 51 | 0 | — |
| `test_五类就是设计稿那五个` 函数 | 57 | 0 | — |
| `Test口径` 类 | 61 | 0 | — |
| `test_mock才供数的字段不算能力` 函数 | 62 | 0 | R6c-1 口径①：`discover.py` 卡片契约读 `item\["status"\]`，但只有 mock 会填。 |
| `test_工具类一律不参与五类` 函数 | 72 | 0 | 口径②：代码仓库/工具不是采集通路——它们是**规则判空**或**逐条判空**，不是"我们没查"。 |
| `test_r1_那批是调研期声明_标_medium` 函数 | 88 | 0 | — |
| `Test查询` 类 | 94 | 0 | — |
| `test_channels_for_错误类名要抛` 函数 | 95 | 0 | — |
| `test_能答现行性的渠道包含真实通路` 函数 | 99 | 0 | — |
| `test_未登记的渠道返回空而不抛` 函数 | 104 | 0 | — |
| `test_only_ok_会滤掉探针判死的渠道` 函数 | 107 | 0 | 能力与可用性是两根轴：声明不改，但选渠道时要能滤。 |
| `test_coverage_小结` 函数 | 116 | 0 | — |
| `test_真库默认路径能读` 函数 | 122 | 0 | — |

### `tests/test_channel_probe.py`（37 个符号）

> 渠道健康探针测试（`src/core/update/channel_probe.py`，§11.0 R3）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `FakeTransport` 类 | 22 | 31 | 假传输：记录调用并回放预设的 `(status, body)` 或抛预设异常。 |
| `__init__` 函数 | 25 | 135 | — |
| `fetch` 函数 | 30 | 1027 | — |
| `_clean` 函数 | 38 | 172 | — |
| `TestClassify` 类 | 44 | 1 | 判据表：这一组就是"有效性"三个字的定义。 |
| `test_判据表` 函数 | 64 | 0 | — |
| `test_正文报错的措辞要提示先怀疑请求体` 函数 | 68 | 0 | 实测教训：flk 的 500 是我**请求体**不对，不是渠道坏 —— 措辞必须能分开这两件事。 |
| `TestMinLinks` 类 | 74 | 1 | R6 新增判据：**页面里有没有内容链接**（JS 空壳的照妖镜）。 |
| `test_链接数不足判可疑并点名` 函数 | 82 | 0 | — |
| `test_链接数够且锚点在则通过` 函数 | 88 | 0 | — |
| `test_两个期望可以叠加_任一不满足即不算通过` 函数 | 92 | 0 | 锚点对、但页面没链接（或反之）都不算过——消息要把两条都列出来。 |
| `test_链接计数大小写与换行都算` 函数 | 99 | 0 | — |
| `test_只配_url_不配期望仍记_unknown` 函数 | 103 | 0 | — |
| `test_429_是限流不是死` 函数 | 106 | 0 | R6a 实测：GitHub 上两条被 429，判 down 会让业主以为该换渠道。 |
| `test_坏_min_links_在读表时就要抛` 函数 | 113 | 0 | `probe_channel` 的契约是**不抛异常**——所以配置错误必须在读表时响亮报错。 |
| `test_目标形状坏也在读表时抛` 函数 | 155 | 0 | 独立复核 b28 / b28-fix 的发现：原先只校验 `min_links` ⇒ 字符串 target **静默过表**，。 |
| `test_大写_scheme_的_url_不该被误拒` 函数 | 166 | 0 | 反向：`startswith("http")` 会把合法的 `HTTP://e.com` 误拒（b28-fix 的 N2）。 |
| `test_合法_url_仍然照过` 函数 | 179 | 0 | 收紧 netloc/端口校验时最容易顺手误伤合法写法——这条钉住"12 个合法 URL 全照过"里的代表。 |
| `test_JSON_顶层数组允许` 函数 | 185 | 0 | `json` 只允许 dict 会把"发一个数组"误拒（b28-fix 的 N4）。 |
| `test_响应体不可序列化也不抛` 函数 | 192 | 0 | S1（b28-fix）：`json.dumps` 原先在 try 之外 ⇒ 怪响应体会从 probe_channel 逃出去，。 |
| `test_空_expect_若绕过校验就是假绿` 函数 | 204 | 0 | 把"为什么必须在读表时拒"钉成可执行的证据：空串锚点判恒真。 |
| `TestProbeChannel` 类 | 210 | 1 | — |
| `test_成功路径带延迟与证据头` 函数 | 211 | 0 | — |
| `test_dict_正文会被序列化后判锚点` 函数 | 218 | 0 | — |
| `test_超时与传输异常都分级不抛` 函数 | 223 | 0 | — |
| `test_没有_url_的渠道记_unknown_而不是_失败` 函数 | 231 | 0 | — |
| `test_POST_的_method_必须真的传下去` 函数 | 235 | 0 | ⚠ dry-run 实测缺陷：漏传 `method` ⇒ transport 走 GET，而 flk/dbba **两层都回 200**。 |
| `test_POST_json_体与_headers_都传下去` 函数 | 245 | 0 | — |
| `TestProbeChannels` 类 | 255 | 1 | — |
| `_seed` 函数 | 256 | 20 | — |
| `test_persist_true_写台账_persist_false_一个字都不写` 函数 | 264 | 0 | — |
| `test_没配目标的渠道不在默认探测集里` 函数 | 280 | 0 | — |
| `test_指定不存在的渠道要抛` 函数 | 286 | 0 | — |
| `test_目标表格式坏要抛` 函数 | 291 | 0 | — |
| `TestShippedProbes` 类 | 298 | 1 | 随包发布的探针目标表（`src/core/update/channel_probes.json`）的契约。 |
| `test_每个目标都有_url_与出处` 函数 | 301 | 0 | — |
| `test_目标指向的渠道都在种子里` 函数 | 308 | 0 | 探针目标不许指向一个台账里不存在的渠道（否则永远探不到、也没人发现）。 |

### `tests/test_channel_repo.py`（62 个符号）

> 渠道台账仓储测试（`src/core/storage/channel_repo.py`，§11.0 R2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_channel_table` 函数 | 22 | 3 | 每个用例先清空 `update_channel`。 |
| `Test号段列与读写` 类 | 37 | 0 | §11.0 R7：`segments_json`（号段）必须**真的在表里**、能写能读、且列进补列清单。 |
| `test_表里真的有号段列` 函数 | 45 | 0 | — |
| `test_补列清单必须包含号段列` 函数 | 49 | 0 | — |
| `test_写入读回_并归一` 函数 | 53 | 0 | — |
| `test_写入坏形状要抛且不动原值` 函数 | 59 | 0 | — |
| `test_种子导入也能带号段` 函数 | 66 | 0 | 种子（`_DESCRIPTIVE`）与人工写走同一条校验 ⇒ 不允许多一条绕过路径。 |
| `TestCategoryNormalization` 类 | 71 | 1 | 30 种原始写法 → canonical。 |
| `test_已知写法都能归一` 函数 | 86 | 0 | — |
| `test_未知写法落_other_且调用方保留原文` 函数 | 89 | 0 | — |
| `TestCrud` 类 | 98 | 1 | — |
| `test_插入_读取_列出_删除` 函数 | 99 | 0 | — |
| `test_拼错字段要抛而不是静默丢` 函数 | 110 | 0 | — |
| `test_非法类别要抛` 函数 | 114 | 0 | — |
| `test_缺_name_的新建要抛` 函数 | 118 | 0 | — |
| `test_更新保留未提到的字段` 函数 | 122 | 0 | — |
| `test_启停不删数据` 函数 | 128 | 0 | — |
| `TestHealthSemantics` 类 | 137 | 1 | 三态 + 计数：这一组的语义直接决定面板上"有效性"三个字是什么意思。 |
| `test_ok_清零失败计数并记_last_ok` 函数 | 140 | 0 | — |
| `test_suspicious_也算失败` 函数 | 148 | 0 | R1 的 G14：应急部标准页 465B、bzw 列表页"共0条" —— **200 不等于有数据**。 |
| `test_unknown_只记尝试` 函数 | 157 | 0 | — |
| `test_非法状态与不存在的渠道都要抛` 函数 | 164 | 0 | — |
| `test_summary_把注册数与能力数分开报` 函数 | 171 | 0 | 本模块最重要的一条口径：total 是台账条数，by_wiring\['wired'\] 才是能干活条数。 |
| `TestSeed` 类 | 181 | 1 | 种子导入：幂等 + **不覆盖运行期健康度**。 |
| `_seed_file` 函数 | 184 | 2 | — |
| `test_导入幂等且不覆盖健康度` 函数 | 193 | 0 | — |
| `test_显式_overwrite_health_才覆盖` 函数 | 206 | 0 | `overwrite_health=True` = 允许 payload 里的健康度字段落库（默认一律不落）。 |
| `test_种子文件缺失或格式坏要抛` 函数 | 221 | 0 | — |
| `TestApi` 类 | 230 | 1 | `/api/v1/channels`（R2b，只读）。 |
| `_hdr` 函数 | 239 | 11 | — |
| `test_列表带_summary_且能按类别筛选` 函数 | 242 | 0 | — |
| `test_非法筛选值要_422_而不是空结果` 函数 | 253 | 0 | — |
| `test_limit_越界要_422` 函数 | 261 | 0 | — |
| `test_单条详情_不存在要_404` 函数 | 267 | 0 | — |
| `test_每条都带_has_probe_target` 函数 | 274 | 0 | R6：面板要能分开「⚪ 无探针」与「⚪ 还没探过」——否则灰行读不出该不该动手。 |
| `test_探测端点_不存在的_id_要_404` 函数 | 293 | 0 | `POST /api/v1/channels/probe`：ids 里有台账里没有的 → 404（不是静默跳过）。 |
| `test_探测端点_ids_类型不对要_422` 函数 | 301 | 0 | — |
| `test_探测端点_只探配了目标的渠道` 函数 | 308 | 0 | ⚠ 关键口径：不传 ids 时**只探有探针目标的**（今天 28 条），绝不盲探 131 条。 |
| `TestShippedSeed` 类 | 322 | 1 | 随包发布的种子（`src/core/update/channel_seed.json`）本身的契约。 |
| `test_种子可读且_id_唯一` 函数 | 325 | 0 | — |
| `test_兜底链现状_web_已摘除_govcn_已换棒` 函数 | 333 | 0 | R1 的 G6 抓出**两根**死兜底棒。 |
| `test_降级链里不再有已知失效的渠道` 函数 | 347 | 0 | 链上的每一棒都必须是"能用"的：`broken` 在种子里应为 0。 |
| `test_接线名字不一致的渠道已在种子里记明` 函数 | 359 | 0 | R2 发现 G23（注册表键 `ttzb` vs 适配器名 `ttbz`）。 |
| `test_能力数远小于台账条数` 函数 | 373 | 0 | 口径用例：如果哪天这两个数相等，说明有人把"调研到"当成了"能干活"。 |
| `test_种子号段形状与大小写` 函数 | 394 | 0 | 每条的 `segments_json` 必须是**非空字符串数组**、无前后空白/重复。 |
| `test_已声明号段不许是死号段` 函数 | 425 | 0 | 拿**真库形状**的号表量每一个已声明的号段：一个号都不命中 ⇒ 红。 |
| `Test单位性质` 类 | 442 | 0 | 单位性质（org_kind，2026-09-22 业主定）：台账「文件夹树」分类的那根轴。 |
| `test_表里真的有单位性质列` 函数 | 448 | 0 | — |
| `test_补列清单必须包含单位性质列` 函数 | 452 | 0 | — |
| `test_枚举校验_坏值出声拒绝` 函数 | 456 | 0 | — |
| `test_关键词粗分类回填` 函数 | 468 | 0 | — |
| `test_人工标的永不被回填覆盖` 函数 | 490 | 0 | — |
| `test_回填幂等` 函数 | 496 | 0 | — |
| `Test渠道已知文件测试` 类 | 501 | 0 | 批C 判据（2026-09-22）：「试一试」= 拉已知文件 → 识别标准号 → 比对 → **留痕**。 |
| `_mk` 函数 | 507 | 47 | — |
| `test_配样本与读回` 函数 | 511 | 0 | — |
| `test_没配样本直接说没配` 函数 | 519 | 0 | — |
| `test_拉到并认出_比对通过_留痕_ok` 函数 | 525 | 0 | — |
| `test_认出但对不上_留痕_fail` 函数 | 534 | 0 | — |
| `test_拉取失败与没认出_都留痕_fail` 函数 | 543 | 0 | — |
| `test_识别口径_常见号都能认_大小写横竖线比对归一` 函数 | 557 | 0 | — |
| `test_classify_org_kind_second_pass_on_real_names` 函数 | 567 | 1 | 分类补准判据（2026-09-22 第二轮）：60 条首版未命中真名的代表例逐条归位。 |

### `tests/test_channel_system_wiring.py`（35 个符号）

> spec 011 更新通道系统三个断点的回归判据。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Test自动巡检已接线` 类 | 29 | 0 | A1：`server.run()` 必须**真的调用**启动函数（不是只 import）。 |
| `test_run_真的调用_start_update_scheduler` 函数 | 38 | 0 | — |
| `test_run_真的调用_stop_update_scheduler` 函数 | 46 | 0 | — |
| `test_启动失败不阻塞引擎` 函数 | 54 | 0 | `start_update_scheduler()` 必须在 try/except 里 —— 线程起不来不该让引擎起不来。 |
| `Test调度器幂等与生命周期` 类 | 66 | 0 | A2：重复 start 不起第二个线程。 |
| `_no_db_scheduler` 函数 | 78 | 1 | 替身调度器：tick 立刻返回空，不碰数据库。 |
| `test_重复_start_只起一个线程` 函数 | 91 | 0 | — |
| `test_stop_后_is_running_为假` 函数 | 99 | 0 | — |
| `test_未跑时_stop_幂等` 函数 | 106 | 0 | — |
| `test_stop_后能再_start` 函数 | 111 | 0 | — |
| `Test建批后真的执行` 类 | 119 | 0 | A3：**这是本特性修的核心缺口** —— `tick()` 只建批不跑。 |
| `test_tick_and_run_会执行建出来的批` 函数 | 122 | 0 | 注入假 tick：返回一个"建了"的批 ⇒ 必须去跑它。 |
| `test_没建批时不去跑` 函数 | 142 | 0 | — |
| `test_单批失败不拖累其余批` 函数 | 158 | 0 | — |
| `Test调度开关` 类 | 181 | 0 | A4/A5：未到期不建批。 |
| `test_关闭时_tick_不建批` 函数 | 189 | 0 | `schedule_days()` 返回 0（关闭）⇒ `_create_scheduled_batches` 直接返回空。 |
| `test_接线没有绕过_scheduler_的_tick` 函数 | 202 | 0 | 结构判据：`tick_and_run` 必须**调 `tick()`**，不许自己另写建批逻辑。 |
| `Test入库补CCS` 类 | 218 | 0 | B1/B2：入库后带 `CCS:` 标签。 |
| `test_标准入库会查_CCS_并写标签` 函数 | 221 | 0 | 判据：`ingest_law_text` 对 standard 类型会调 `resolve_ccs`。 |
| `test_与_pipeline_同一所有者` 函数 | 234 | 0 | B4：CCS 判据**只有一个所有者**（`ccs_fetcher`），不许另写一份解析。 |
| `test_查不到_CCS_不阻塞入库` 函数 | 251 | 0 | B2：`resolve_ccs` 抛异常/返回 None 时，入库**必须仍成功**。 |
| `Test绝不自动下载` 类 | 280 | 0 | C1：**反向断言** —— 判定 `new_version` 后不许有文件被下载。 |
| `test_巡检代码里没有自动下载调用` 函数 | 287 | 0 | `inspector.py`（巡检执行体）里不许直接调 `archive_pdf`。 |
| `test_判定_new_version_不触发下载` 函数 | 295 | 0 | 结构判据：`new_version` 分支里不许出现下载动作。 |
| `Test识别占位回退` 类 | 307 | 0 | ★ C4c：**真站点实测发现的缺陷**（2026-10-12）。 |
| `test_占位回退被判为失败` 函数 | 327 | 0 | 模拟 `archive_pdf` 写了占位 ⇒ `download_gate` 必须报失败。 |
| `test_真文件被判为成功` 函数 | 352 | 0 | 对照：真下到东西（比占位大）⇒ 报成功。 |
| `test_占位阈值引用唯一所有者` 函数 | 374 | 0 | 结构判据：不许自己抄一份占位字节数（判据分叉）。 |
| `Test下载走审批门` 类 | 385 | 0 | C2/C3：同意才下、拒绝不下。 |
| `test_审批门问句说清来源与形态` 函数 | 388 | 0 | FR-010：问句必须含"来源 + 形态"（业主口径：不让用户读全文）。 |
| `test_拒绝则不下载` 函数 | 399 | 0 | — |
| `test_同意则下载` 函数 | 410 | 0 | — |
| `Test下载校验非PDF` 类 | 421 | 0 | C4：站点返回 HTML 错误页时必须拒收（复用 archive_pdf 的 `%PDF` 校验）。 |
| `test_archive_pdf_校验_PDF_魔数` 函数 | 424 | 0 | **复用**既有校验，不另写一份 —— 结构判据。 |
| `test_download_gate_不另写校验` 函数 | 433 | 0 | C4b：download_gate **不许**自己写一份 `%PDF` 校验（判据分叉）。 |

### `tests/test_channels_write_api.py`（14 个符号）

> 渠道台账**人工维护**的写侧（§11.0 R6d）：新增 / 复核编辑 / 启停 / 删除 + 留痕。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_audit_rows` 函数 | 22 | 7 | — |
| `_create` 函数 | 28 | 9 | — |
| `Test人工新增` 类 | 36 | 0 | — |
| `test_新增成功_默认值正确_并留一条痕迹` 函数 | 37 | 0 | — |
| `test_缺name与非法字段都出声拒绝` 函数 | 55 | 0 | — |
| `test_新增的渠道出现在列表与小结里` 函数 | 87 | 0 | — |
| `Test人工复核编辑` 类 | 100 | 0 | — |
| `test_改描述性字段_留痕带改前改后` 函数 | 101 | 0 | — |
| `test_编辑不许碰健康度_启停要走去自己的端点` 函数 | 118 | 0 | — |
| `test_号段可人工维护_坏形状出声拒绝` 函数 | 135 | 0 | §11.0 R7：**号段是业主可维护的事实**，所以它必须是可写字段。 |
| `test_探针跑过之后人工改链接不清空健康度` 函数 | 156 | 0 | 人工改的是"描述性字段"，**不许**顺手把实测状态抹掉（`overwrite_health=False`）。 |
| `Test人工启停与删除` 类 | 171 | 0 | — |
| `test_启停留痕` 函数 | 172 | 0 | — |
| `test_删除留痕带删除前整行快照` 函数 | 188 | 0 | — |

### `tests/test_class_outcomes.py`（21 个符号）

> 五类结论组装测试（`src/core/update/channels/class_outcomes.py`，§11.0 R6c-4）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_rep` 函数 | 20 | 12 | 造一份 `route_report` 形状：{类: {channels, reason, ...}}。 |
| `Test结论抽取` 类 | 39 | 0 | — |
| `test_发布要发布日期_没有就不算答` 函数 | 40 | 0 | ⚠ 不许拿实施日期顶发布——那正是 R6c-3c/3e 修掉的错标。 |
| `test_修订三态都算答了` 函数 | 49 | 0 | **否定的结论也是结论**：`no_change` = "没有被代替"，是 `修订` 类的答案。 |
| `test_废止_现行也是结论_非废止时无废止日期` 函数 | 61 | 0 | ⚠ 这一条是**拿真机演示改出来的**：我第一版只在 `withdrawn` 时才算答了，。 |
| `test_现行性与编号核验` 函数 | 84 | 0 | — |
| `test_非法类名要抛` 函数 | 91 | 0 | — |
| `Test组装` 类 | 96 | 0 | — |
| `test_答的棒在候选里才算answered` 函数 | 97 | 0 | — |
| `test_候选在但没轮到它_记not_probed而不是答不出来` 函数 | 107 | 0 | 第一棒命中了 ⇒ 这一类的候选**根本没被问过**。 |
| `test_答的棒在候选里但没给字段_记channel_gave_no_field` 函数 | 127 | 0 | 对照上一条：候选里**有**答的这根棒，所以是"问了、没给"，不是"没问"。 |
| `test_问了但没给这一类要的字段` 函数 | 141 | 0 | `mee` 对"发布"答不了：它的列是**实施时间**，而这一条**不许拿实施日期顶发布**。 |
| `test_渠道给了否定结论也算answered` 函数 | 152 | 0 | 对照上一条：`official_gb` 说"现行" ⇒ `废止` 类**答了**（否定的答案），带 partial。 |
| `test_空候选的原因原样带出` 函数 | 164 | 0 | — |
| `test_三类结构性原因都算unanswerable` 函数 | 171 | 0 | — |
| `test_真表跑一遍_结论与判定都对得上` 函数 | 177 | 0 | 用**真能力表**跑一次（不注入 table）：`completeness` 应当来自 b35 的审计。 |
| `test_词表封闭` 函数 | 192 | 0 | — |
| `Test整链都没命中` 类 | 198 | 0 | `build_classes_for_miss`：`not_found`（灰）也要能说清"五类各自为什么没答"。 |
| `test_候选在_记not_probed` 函数 | 201 | 0 | — |
| `test_结构性缺口照样进unanswerable` 函数 | 208 | 0 | — |
| `test_没有channel与conclusion字段` 函数 | 214 | 0 | 没有"谁答的"这回事——所以不许出现 `channel`/`conclusion`（免得下游误读成答过）。 |

### `tests/test_classical_segmentation_ruler.py`（6 个符号）

> P3.2 尺子（`scripts/measure-classical-chinese-segmentation.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 31 | 125 | — |
| `test_char_seg_gives_one_token_per_cjk_char` 函数 | 49 | 1 | B 口径：每个汉字一个 token。 |
| `test_char_level_requires_relaxing_the_single_char_drop` 函数 | 55 | 2 | ★ 这条路的核心代价：**字级查询不能复用 `fts_match_expr`**。 |
| `test_no_drop_expr_differs_from_production_only_by_the_single_char_rule` 函数 | 73 | 1 | A+ 口径：**索引不动**，只关掉"丢弃单字符词"这条规则。 |
| `test_single_ratio_counts_occurrences_not_documents` 函数 | 89 | 1 | ★ 单字占比必须按**出现次数**（`cnt`）算。 |
| `test_ngram_counts_segments_not_occurrences` 函数 | 109 | 2 | n-gram 的计数单位是**段**：一个词在同一段里出现 5 次只算 1。 |

### `tests/test_clause_head_gates.py`（38 个符号）

> 条款头闸门契约测试（2026-09-15，「重复条款号」根因修复配套）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fake` 类 | 20 | 23 | — |
| `__init__` 函数 | 21 | 135 | — |
| `TestNumSegments` 类 | 25 | 1 | — |
| `test_numeric` 函数 | 26 | 1 | — |
| `test_appendix_letter` 函数 | 29 | 1 | — |
| `test_numeric_before_appendix` 函数 | 33 | 1 | — |
| `test_unorderable` 函数 | 36 | 1 | — |
| `TestContinuationShape` 类 | 41 | 1 | ① 形态判据：续行标点/连接词/数字起头。 |
| `test_right_paren` 函数 | 44 | 1 | — |
| `test_tilde_range` 函数 | 48 | 1 | — |
| `test_sentence_period` 函数 | 52 | 1 | — |
| `test_connector_word` 函数 | 56 | 1 | — |
| `test_dot_leading_rest` 函数 | 60 | 1 | — |
| `test_real_head_not_flagged` 函数 | 64 | 1 | — |
| `TestContinuationOrder` 类 | 69 | 1 | ② 序性判据：号 ≤ 最近已产出号。 |
| `test_duplicate_number_rejected` 函数 | 72 | 1 | — |
| `test_lower_number_rejected` 函数 | 77 | 1 | — |
| `test_increasing_accepted` 函数 | 81 | 1 | — |
| `test_parent_then_child_accepted` 函数 | 85 | 1 | — |
| `test_appendix_duplicate_rejected` 函数 | 88 | 1 | — |
| `test_appendix_progression_accepted` 函数 | 94 | 1 | — |
| `test_prefix_ignored` 函数 | 97 | 1 | — |
| `TestDepthCap` 类 | 102 | 1 | — |
| `test_deep_number_full_capture` 函数 | 103 | 1 | — |
| `TestUnitBracketGate` 类 | 111 | 1 | 闸门 4（2026-09-15 收敛循环首轮，GB/T 12706.4-2020 实测）。 |
| `test_unit_then_paren_rejected` 函数 | 119 | 1 | — |
| `test_spaced_unit_then_paren_rejected` 函数 | 123 | 1 | — |
| `test_title_starting_with_latin_kept` 函数 | 127 | 1 | — |
| `TestCascadeResistance` 类 | 133 | 1 | 假头不得毒化其后真头（2026-09-15 收敛循环首轮实测的塌缩机制）。 |
| `test_real_head_after_false_head` 函数 | 140 | 1 | — |
| `test_connector_needs_reference` 函数 | 145 | 1 | — |
| `_mk` 函数 | 157 | 47 | — |
| `TestIntegration` 类 | 168 | 4 | — |
| `test_continuation_does_not_duplicate` 函数 | 169 | 1 | — |
| `test_deep_number_kept_distinct` 函数 | 177 | 1 | — |
| `test_normal_progression_unaffected` 函数 | 185 | 1 | — |
| `test_false_head_does_not_collapse_document` 函数 | 192 | 1 | — |
| `test_unit_wrapped_title_not_clause` 函数 | 203 | 1 | — |

### `tests/test_contract.py`（34 个符号）

> T00 契约冒烟测试：模型可实例化、SSE 事件与通道枚举冻结、DDL 可执行。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_sse_event_order_frozen` 函数 | 11 | 1 | — |
| `test_search_channels_frozen` 函数 | 15 | 1 | — |
| `test_modality_strength_dict_frozen` 函数 | 20 | 1 | — |
| `test_models_instantiate` 函数 | 29 | 1 | — |
| `test_invalid_knowledge_type_rejected` 函数 | 55 | 1 | — |
| `test_schema_all_tables` 函数 | 63 | 1 | — |
| `test_bookmark_folder_schema` 函数 | 80 | 1 | 收藏夹目录（2026-10）契约：夹表 + 两张收藏表的 folder_id 列 + 夹名 UNIQUE。 |
| `test_doc_bookmark_columns` 函数 | 93 | 1 | user_doc_bookmark（标准级书签）契约：列集 + doc_id UNIQUE + FK 级联。 |
| `test_egress_audit_contract` 函数 | 104 | 1 | Task 10.0 契约（v5 红线 #4 外发可审计）：debug_dump 必须承载外发审计所需字段。 |
| `test_clause_revision_page_breaks_column` 函数 | 123 | 1 | B3 页界列：clause_revision.page_breaks TEXT 可空（run-start 编码。 |
| `test_clause_revision_figure_html_column` 函数 | 139 | 1 | C2 插图通道列：clause_revision.figure_html TEXT 可空（fig-strip 占位。 |
| `test_update_tables_exist` 函数 | 153 | 1 | 29/30 号表存在性（pipeline/02 §2 数据契约增量）。 |
| `test_update_tables_ulid_pk_style` 函数 | 161 | 1 | 29/30 表主键为 ULID 风格 TEXT 主键，DDL 注释声明 upd_/chg_ 前缀。 |
| `test_update_batch_check_enums` 函数 | 175 | 1 | update_check_batch：trigger_type 二枚举、status 五枚举 CHECK。 |
| `test_update_event_change_type_enum` 函数 | 192 | 1 | update_change_event：change_type 恰好五枚举。 |
| `test_update_event_legal_status_and_nullable_doc` 函数 | 205 | 1 | current_legal_status 四枚举且可空。 |
| `test_update_event_fk_cascade` 函数 | 233 | 1 | batch_id 外键：孤儿事件插入被拒、删批次级联删事件。 |
| `test_bulk_import_batch_exists_and_columns` 函数 | 252 | 1 | 31 号表存在性 + 巡检侧最小列集（tier/checkpoint_json 是编排器刚需）。 |
| `test_bulk_import_batch_ulid_pk_style` 函数 | 266 | 1 | 主键为 ULID 风格 TEXT 主键，DDL 注释声明 bul_ 前缀。 |
| `test_bulk_import_batch_check_enums_and_defaults` 函数 | 277 | 1 | CHECK 枚举（batch_kind/trigger_type/status/tier）+ 默认值（status/计数/tier）。 |
| `test_announce_table_exists` 函数 | 306 | 1 | announcement_observed（32 号表）存在。 |
| `test_announce_observed_columns` 函数 | 312 | 1 | announcement_observed 契约：列集完备。 |
| `test_announce_dedup_unique` 函数 | 322 | 1 | 去重键 UNIQUE(source_id, url_hash)：重复 (source_id,url_hash) 写入被拒。 |
| `test_announce_ulid_pk_style` 函数 | 337 | 1 | observed_id 须为 TEXT 主键且 DDL 带 ann_ 前缀注释（ULID 风格契约）。 |
| `test_folder_tables_exist` 函数 | 349 | 1 | folder / folder_member / doc_filing_state 三张表存在（方案 §3 定死的形状）。 |
| `test_folder_columns` 函数 | 357 | 1 | — |
| `test_folder_ulid_pk_style` 函数 | 362 | 1 | folder_id 须为 TEXT 主键且 DDL 带 fld_ 前缀注释（与 30/32 号表同款契约）。 |
| `test_folder_member_columns_and_pk` 函数 | 372 | 1 | — |
| `test_doc_filing_state_columns_and_stage_enum` 函数 | 380 | 1 | — |
| `test_folder_member_kind_enum_and_pk_rejects_dup` 函数 | 394 | 1 | item_kind 只有 folder/file。 |
| `test_folder_same_name_same_level_rejected_by_indexes` 函数 | 408 | 1 | 同名同层拒绝**必须**含根层：`parent_id IS NULL` 时表级 UNIQUE 无效（NULL 互不相等），。 |
| `test_clause_vec_doc_id_metadata_column` 函数 | 444 | 1 | `clause_vec` 必须有 `doc_id` **元数据列**（范围下推修复）。 |
| `test_clause_repo_writes_doc_id_into_clause_vec` 函数 | 467 | 1 | spec 003 · FR-009：写向量的**两处**都必须带 `doc_id`（**静态锚点**）。 |
| `test_clause_repo_write_path_sets_doc_id` 函数 | 482 | 1 | spec 003 · FR-009 / SC-005（**端到端**）：真经写侧跑一条 ⇒ `clause_vec.doc_id` 必须对。 |

### `tests/test_cover_dates.py`（10 个符号）

> 封面发布/实施日期提取测试（2026-08-29，通用修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_iso_compact_cover` 函数 | 22 | 1 | GB 封面实测形态：ISO 连排 + 换行分隔。 |
| `test_cjk_year_month_day` 函数 | 31 | 1 | 行标常见"2025年3月16日发布"排版 → 归一化 2025-03-16。 |
| `test_spaced_and_slash_variants` 函数 | 37 | 1 | 带空格 / 斜杠分隔 / 全角括注容忍。 |
| `test_body_mention_not_cover_only_scope` 函数 | 44 | 1 | 正则只认"数字+发布/实施"连排。 |
| `test_no_false_hit_on_clause_numbers` 函数 | 50 | 1 | 条款号/标准号不误触发（"GB 25596-2025"无发布/实施词）。 |
| `test_missing_leaves_none` 函数 | 56 | 1 | 无封面日期 → 诚实留空（不猜测）。 |
| `test_middle_cover_blocks_fallback` 函数 | 61 | 1 | 扫描版兜底：fitz 文本层为空时，从 middle.json 前 2 页提取封面块。 |
| `_nfkc` 函数 | 91 | 3 | — |
| `test_middle_cover_blocks_missing_file` 函数 | 96 | 1 | middle.json 缺失/坏件 → 空表（诚实留空）。 |
| `test_gate3_value_unit_wrap_not_clause_head` 函数 | 101 | 1 | E8 闸门 3（2026-09-01）：正文折行后行首"1.5m时，为了计算…"是量值+单位。 |

### `tests/test_credential_readers_scan.py`（7 个符号）

> 凭据读者排查脚本回归测试（整改批 1b）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_findings_in_text_finds_old_and_new_names` 函数 | 24 | 1 | — |
| `test_findings_in_text_empty` 函数 | 30 | 1 | — |
| `test_old_new_name_lists_are_disjoint` 函数 | 35 | 1 | — |
| `test_scan_credential_files_reports_presence` 函数 | 40 | 1 | — |
| `test_scan_credential_files_missing_home` 函数 | 54 | 1 | — |
| `test_scan_shell_configs_autorun_absent` 函数 | 62 | 1 | — |

### `tests/test_credential_reconcile.py`（6 个符号）

> ks-credential-reconcile.py 对账工具单测（批 2c）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `reconcile` 函数 | 20 | 34 | — |
| `_write_dsh_creds` 函数 | 31 | 3 | — |
| `test_same_key_reports_consistent` 函数 | 38 | 1 | — |
| `test_forked_key_reports_divergence` 函数 | 51 | 1 | — |
| `test_missing_dsh_file_is_honest` 函数 | 64 | 1 | — |
| `test_engine_only_side` 函数 | 73 | 1 | — |

### `tests/test_credentials_migrate_script.py`（30 个符号）

> `scripts/ks-credentials-migrate.py` 单测（破坏性工具，必须测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_FakeKey` 类 | 30 | 13 | — |
| `__init__` 函数 | 31 | 135 | — |
| `__enter__` 函数 | 34 | 9 | — |
| `__exit__` 函数 | 37 | 9 | — |
| `SetValueEx` 函数 | 40 | 12 | — |
| `DeleteValue` 函数 | 43 | 11 | — |
| `FakeWinreg` 类 | 47 | 8 | — |
| `__init__` 函数 | 53 | 135 | — |
| `CreateKeyEx` 函数 | 56 | 5 | — |
| `OpenKey` 函数 | 59 | 9 | — |
| `QueryValueEx` 函数 | 62 | 11 | — |
| `SetValueEx` 函数 | 68 | 12 | — |
| `DeleteValue` 函数 | 71 | 11 | — |
| `fake_reg` 函数 | 76 | 96 | — |
| `store_dir` 函数 | 84 | 12 | — |
| `_clean_env` 函数 | 92 | 3 | — |
| `migrate` 函数 | 102 | 46 | — |
| `test_dry_run_writes_nothing` 函数 | 112 | 2 | — |
| `test_nothing_to_migrate_is_clean_noop` 函数 | 123 | 1 | — |
| `test_clean_system_without_apply_refused` 函数 | 129 | 1 | — |
| `test_force_without_clean_system_refused` 函数 | 136 | 1 | — |
| `test_apply_migrates_into_encrypted_store_and_keeps_system_layer` 函数 | 143 | 1 | — |
| `test_apply_writes_no_plaintext` 函数 | 154 | 1 | — |
| `test_clean_system_deletes_verified_entries` 函数 | 162 | 1 | — |
| `test_clean_system_two_pass_deletes_previously_migrated` 函数 | 174 | 1 | 批2 真实踩到的回归：先 --apply（第一遍搬完），再 --apply --clean-system（第二遍）。 |
| `test_clean_system_reports_env_only_entries` 函数 | 193 | 1 | 只在进程环境变量里的条目删不掉 —— 必须如实上报，不谎报已清理。 |
| `test_clean_system_never_deletes_when_store_has_other_value` 函数 | 203 | 1 | verifier P1 的脚本层回归：存储里已有新 Key → 不覆盖，且不删冲突的系统层旧值。 |
| `test_force_discards_conflicting_system_layer_value` 函数 | 216 | 1 | — |
| `test_import_does_not_run_main` 函数 | 226 | 1 | — |
| `test_script_documents_dsh_restart_and_rollback` 函数 | 232 | 1 | 文档级守卫：这几句不许被删（verifier 指出旧版全仓库都没写"必须重启 DSH"）。 |

### `tests/test_credentials_namespace.py`（51 个符号）

> 凭据存储的结构守卫与读取链单测（2026-09-11 「不要动系统层」改造后）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_iter_code_files` 函数 | 69 | 3 | — |
| `_FakeKey` 类 | 85 | 13 | — |
| `__init__` 函数 | 86 | 135 | — |
| `__enter__` 函数 | 89 | 9 | — |
| `__exit__` 函数 | 92 | 9 | — |
| `SetValueEx` 函数 | 95 | 12 | — |
| `DeleteValue` 函数 | 98 | 11 | — |
| `FakeWinreg` 类 | 102 | 8 | 够 api_credentials（模块属性替换）与 config（sys.modules 替换）两处用。 |
| `__init__` 函数 | 110 | 135 | — |
| `CreateKeyEx` 函数 | 113 | 5 | — |
| `OpenKey` 函数 | 116 | 9 | — |
| `QueryValueEx` 函数 | 119 | 11 | — |
| `SetValueEx` 函数 | 125 | 12 | — |
| `DeleteValue` 函数 | 128 | 11 | — |
| `fake_reg` 函数 | 133 | 96 | 假 HKCU（读旧系统层 / 迁移源用）。 |
| `store_dir` 函数 | 142 | 12 | 把加密存储重定向到 tmp —— 本文件任何测试都碰不到真实 %APPDATA%。 |
| `_clean_env` 函数 | 151 | 3 | — |
| `test_every_channel_name_is_namespaced` 函数 | 161 | 1 | 所有通道的所有变量名必须带 KS_ 前缀（这次事故的形态就是漏了前缀）。 |
| `test_legacy_names_disjoint_from_write_names` 函数 | 169 | 1 | 旧名不能同时是写入名（否则等于一边叫它旧、一边继续用它）。 |
| `test_llm_reader_order_namespaced_first` 函数 | 177 | 1 | — |
| `test_no_source_writes_a_legacy_name_or_registry` 函数 | 186 | 1 | 源码级扫描：**全仓库代码**里没有任何文件把旧全局名/注册表当写入目标。 |
| `test_legacy_names_appear_only_in_reviewed_files` 函数 | 210 | 2 | 旧名出现的位置白名单化：新增引用会红，逼一次人工复核（防偷偷搬回裸名）。 |
| `test_set_credential_writes_encrypted_store_not_registry` 函数 | 232 | 1 | — |
| `test_write_path_does_not_touch_winreg_at_all` 函数 | 240 | 1 | 最强结构断言：把 winreg 换成"一碰就炸"，保存仍必须成功。 |
| `test_dash_clears_store_value` 函数 | 255 | 1 | — |
| `test_blank_value_skips_without_clobbering` 函数 | 264 | 1 | — |
| `test_unknown_channel_rejected` 函数 | 271 | 3 | — |
| `test_stored_channels_reports_booleans_only` 函数 | 277 | 1 | — |
| `test_store_value_is_read` 函数 | 288 | 1 | — |
| `test_env_override_beats_store` 函数 | 295 | 1 | — |
| `test_store_beats_legacy_system_layer` 函数 | 303 | 1 | 存储是权威：系统层里还有旧值也不该压过它（否则"设置页改了不生效"）。 |
| `test_legacy_system_layer_still_readable_for_backward_compat` 函数 | 313 | 1 | **关键兼容断言**：没迁移的老机器（系统层里只有旧名）必须照旧能跑。 |
| `test_legacy_env_still_readable` 函数 | 320 | 1 | — |
| `test_env_beats_legacy_registry_for_same_name` 函数 | 326 | 1 | — |
| `test_base_url_and_model_chain` 函数 | 333 | 1 | — |
| `test_cloud_channel_reads_from_store` 函数 | 348 | 1 | — |
| `test_defaults_when_nothing_configured` 函数 | 357 | 1 | — |
| `test_system_layer_status_reports_presence_without_values` 函数 | 367 | 1 | — |
| `test_legacy_status_reports_presence_without_values` 函数 | 378 | 1 | — |
| `test_adopt_legacy_moves_into_store_and_keeps_system_layer_by_default` 函数 | 387 | 1 | — |
| `test_adopt_legacy_delete_removes_registry_after_verify` 函数 | 400 | 1 | — |
| `test_adopt_legacy_never_clobbers_existing_store_value` 函数 | 413 | 1 | verifier P1 回归：存储里已有值（用户在设置页刚存的新 Key）绝不能被旧值冲掉。 |
| `test_adopt_legacy_delete_refuses_to_drop_conflicting_legacy` 函数 | 426 | 1 | — |
| `test_adopt_legacy_force_discards_conflicting_legacy` 函数 | 436 | 1 | — |
| `test_adopt_legacy_invalidates_settings_cache` 函数 | 446 | 1 | 迁移后必须失效进程内缓存（verifier mut6 曾证明此处空洞）。 |
| `test_adopt_legacy_noop_when_nothing_legacy` 函数 | 456 | 1 | — |
| `test_adopt_legacy_unknown_channel_rejected` 函数 | 462 | 1 | — |
| `test_import_system_layer_moves_same_named_vars` 函数 | 468 | 1 | 同名搬家：KS_MINERU_CLOUD_API_KEY 从系统层搬进加密存储。 |
| `test_import_system_layer_keeps_existing_store_value` 函数 | 479 | 1 | — |
| `test_clean_system_layer_deletes_only_named_targets` 函数 | 489 | 1 | — |
| `test_clean_system_layer_reports_env_untouched` 函数 | 499 | 1 | — |

### `tests/test_debug_dump_retention.py`（15 个符号）

> `debug_dump` 的**保留策略**：外发审计的量**不许**把提问证据挤掉（2026-09-25 真缺陷回归）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_new_id` 函数 | 34 | 5 | — |
| `_insert` 函数 | 38 | 7 | — |
| `_fill_egress` 函数 | 47 | 6 | 灌 n 条外发审计（模拟每天 ~110 条写满窗口）。 |
| `_count` 函数 | 57 | 17 | — |
| `_reset` 函数 | 63 | 7 | 清空这张表。 |
| `_prune_whole_table` 函数 | 74 | 2 | **旧行为**（缺陷本体），只在本测试里当"反向"对照用——生产代码里已不存在。 |
| `test_egress_volume_cannot_evict_question_evidence` 函数 | 86 | 1 | **正向**：灌满审计窗口之后，提问证据必须一条不少。 |
| `test_the_whole_table_prune_would_evict_them` 函数 | 102 | 1 | **反向**：同一批数据喂给旧的"全表裁"，提问证据**必须**被挤掉。 |
| `test_pruning_one_type_leaves_the_other_alone` 函数 | 121 | 1 | 按类型清理**只裁自己那一类**（这条是修复的全部要点）。 |
| `test_keep_bound_is_respected_and_returns_the_count` 函数 | 135 | 1 | `keep` 生效、且返回删掉的条数（调用方可据此观测）。 |
| `test_the_newest_are_the_ones_kept` 函数 | 145 | 1 | 留下的是**最新**的（同一秒内插入时靠 rowid 兜底成全序）。 |
| `test_question_evidence_outlives_the_audit_window` 函数 | 156 | 1 | **意图**要写进断言：提问证据的保留上限必须**大于**审计的——。 |
| `test_record_egress_call_site_prunes_its_own_type_with_its_own_cap` 函数 | 169 | 1 | `record_egress` 必须裁 **egress**、且用**它自己的上限**。 |
| `test_debug_dump_has_the_type_created_index_and_the_paging_query_uses_it` 函数 | 189 | 1 | 索引必须在，且**分页查询真的用得上它**。 |
| `test_init_schema_recreates_the_index_on_an_existing_db` 函数 | 212 | 1 | **已有库**（缺这条索引）在 `init_schema` 时会被**自动补建** —— 这是"不必写迁移函数"的依据。 |

### `tests/test_deep_server.py`（11 个符号）

> deep_server 任务协议测试（假 daemon 线程，不启动真 GPU 进程）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_job_env` 函数 | 19 | 1 | — |
| `_fake_daemon` 函数 | 26 | 6 | 监视任务目录，攒批窗口后直接写 done/error（不碰 mineru）。 |
| `_bypass_alive` 函数 | 70 | 5 | — |
| `test_提交_攒批_返回_output_dir` 函数 | 76 | 0 | — |
| `test_任务失败_返回_None_回退信号` 函数 | 89 | 0 | — |
| `test_无服务超时_返回None并清理任务文件` 函数 | 115 | 0 | — |
| `test_开关关闭_不提交任务` 函数 | 125 | 0 | — |
| `test_提交与等待拆分_先投后收` 函数 | 135 | 0 | — |
| `test_开关关闭_submit返回None` 函数 | 160 | 0 | — |
| `test_并发冷启动_按目标数拉起不超额` 函数 | 168 | 0 | 单飞锁：多客户端同时发现 daemon 不足，只补足 KS_DEEP_WORKERS 个，。 |
| `test_任务抢占_两个收集者不重叠` 函数 | 201 | 0 | v5 抢占锁：daemon A 领走的任务，daemon B 的 _collect_jobs 拿不到。 |

### `tests/test_disagreement.py`（24 个符号）

> 阶段2c 分歧检测单测（纯函数面：O2 fallback / 相似度 / 报告装配）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestO2Fallback` 类 | 17 | 1 | — |
| `test_collapsed_when_dominant_high` 函数 | 18 | 1 | — |
| `test_not_collapsed_when_mixed` 函数 | 22 | 1 | — |
| `test_empty_scores_is_collapsed` 函数 | 26 | 1 | — |
| `test_select_2c_input_score_mode` 函数 | 29 | 1 | — |
| `test_select_2c_input_legacy_when_collapsed` 函数 | 36 | 1 | — |
| `TestSimilarity` 类 | 45 | 2 | — |
| `test_identical` 函数 | 46 | 1 | — |
| `test_whitespace_insensitive` 函数 | 49 | 1 | — |
| `test_totally_different` 函数 | 52 | 1 | — |
| `test_empty_both` 函数 | 55 | 1 | — |
| `test_empty_one_side` 函数 | 58 | 1 | — |
| `test_partial` 函数 | 61 | 1 | — |
| `TestCompare` 类 | 66 | 1 | — |
| `test_agree` 函数 | 67 | 1 | — |
| `test_disagree` 函数 | 70 | 1 | — |
| `test_threshold_semantics` 函数 | 74 | 1 | — |
| `TestReport` 类 | 80 | 1 | — |
| `_pair` 函数 | 81 | 6 | — |
| `test_assembly_counts` 函数 | 85 | 1 | — |
| `test_report_dict_roundtrip` 函数 | 96 | 1 | — |
| `test_disagree_item_captures_both_heads` 函数 | 105 | 1 | — |
| `TestConstants` 类 | 115 | 1 | — |
| `test_disagree_ratio_sane` 函数 | 116 | 1 | — |

### `tests/test_doc_batch_delete.py`（7 个符号）

> 批量删除文档测试（2026-08-31，随 POST /api/v1/documents/batch-delete 端点新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_seed_doc` 函数 | 16 | 70 | 最小可用文档：doc_meta + geometry + watch_list + 条款（span/patch/obligation/fts/vec）。 |
| `_seed_edge` 函数 | 58 | 2 | — |
| `_seed_change_event` 函数 | 65 | 3 | — |
| `test_batch_delete_cascades_all_tables` 函数 | 76 | 1 | — |
| `test_batch_delete_requires_confirm` 函数 | 125 | 1 | — |
| `test_batch_delete_validates_input` 函数 | 136 | 1 | — |
| `test_batch_delete_missing_only_leaves_db_untouched` 函数 | 147 | 1 | — |

### `tests/test_doc_catalog_std_no.py`（3 个符号）

> `_is_standard_no` 的**边界形态普查**（复核 b9 的 LOW-1/LOW-2，2026-09-18）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_forms_that_must_count_as_standard` 函数 | 51 | 1 | — |
| `test_forms_that_must_not_count_as_standard` 函数 | 56 | 1 | — |
| `test_classify_document_uses_the_same_judgement` 函数 | 60 | 1 | **接线断言**：`classify_document` 必须走这条判据（不能自己再写一份判断）。 |

### `tests/test_doc_render_api.py`（14 个符号）

> 图/公式/表图三条**渲染端点**的 HTTP 契约（§10.78 补 §10.75 登记的缺口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_make_pdf` 函数 | 30 | 38 | — |
| `_write_middle` 函数 | 40 | 3 | 写一份最小可用的 middle.json（`parse_out/<doc>/…/x_middle.json`）。 |
| `render_doc` 函数 | 57 | 10 | 种一行 doc_meta（指向真 PDF）+ 写 middle.json。 |
| `TestTableImage` 类 | 80 | 1 | — |
| `test_渲染成功_带比例还原头` 函数 | 81 | 0 | 有 middle.json + 页码/序号合法 ⇒ 200 + PNG + 三个 X-Frac-* 头。 |
| `test_无深度产物_错误码是_table_geo_not_found` 函数 | 91 | 0 | 删掉 middle.json ⇒ 404 `table_geo_not_found`（前端按码隐藏占位）。 |
| `test_序号越界_错误码是_table_not_found` 函数 | 105 | 0 | — |
| `test_未知文档_错误码是_doc_not_found` 函数 | 111 | 0 | — |
| `TestFormula` 类 | 118 | 1 | — |
| `test_未知文档` 函数 | 119 | 0 | — |
| `test_条款不存在` 函数 | 125 | 0 | — |
| `test_渲染成功_返回_PNG` 函数 | 131 | 0 | 有 middle.json 的 `interline_equation` 块 ⇒ fno=1 **真的渲染成功**。 |
| `test_公式序号不存在_错误码是_formula_not_found` 函数 | 146 | 0 | 不存在的公式序号（99）⇒ 明确 404（前端按码隐藏占位）。 |
| `test_缺_clause_参数是_422` 函数 | 153 | 0 | `clause` 是必填查询参数：漏传应当是 422（不是 500、也不是 200）。 |

### `tests/test_docx_ingest.py`（4 个符号）

> Task 11.1 docx 入库测试：降级直解路径（无 Word 环境可测）+ 条款切分 + 表格保真。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `docx_fixture` 函数 | 8 | 6 | — |
| `test_parse_docx_text` 函数 | 28 | 1 | — |
| `test_run_docx_ingest_direct` 函数 | 37 | 1 | — |
| `test_run_docx_ingest_missing` 函数 | 59 | 1 | — |

### `tests/test_dry_run_concurrency.py`（9 个符号）

> `dry_run` 的**同文件解析串行**（§10.77）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_stripe_of` 函数 | 25 | 3 | — |
| `_FakeParser` 类 | 30 | 4 | 替身解析器：记录并发峰值与调用次数，每次停 `hold` 秒。 |
| `__init__` 函数 | 33 | 135 | — |
| `__call__` 函数 | 40 | 12 | — |
| `_make_pdf` 函数 | 53 | 38 | 造一份**真 PDF**（假字节过不了体检里的 fitz 解析，第一步就抛）。 |
| `tmp_pdfs` 函数 | 65 | 5 | — |
| `_run_pair` 函数 | 74 | 2 | 两个线程同时预览两份文件，返回替身解析器的统计。 |
| `test_同一份源文件的并发预览被串行化` 函数 | 99 | 0 | 同一 content ⇒ 同一 `<hash16>` 目录 ⇒ 必须串行（并发峰值 = 1）。 |
| `test_不同文件的并发预览允许并行` 函数 | 108 | 0 | **反向断言**：不同文件（分片不同）不许被一把全局锁串起来。 |

### `tests/test_dryrun.py`（3 个符号）

> Task 11.5 Dry-Run 预览测试：解析不落库 + 统计输出。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_make_pdf` 函数 | 6 | 38 | — |
| `test_analyze_preview_no_write` 函数 | 18 | 1 | — |
| `test_analyze_preview_missing` 函数 | 34 | 1 | — |

### `tests/test_dryrun_batch.py`（22 个符号）

> D 组 + F 组（只读端点）：批量分桶语义与 HTTP 契约。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `batch_dir` 函数 | 37 | 33 | 5 本好 + 1 本稀疏(block) + 1 个非法文件(block) + 1 本扫描(warn)。 |
| `test_batch_buckets_conserve` 函数 | 52 | 1 | — |
| `test_batch_single_failure_does_not_abort` 函数 | 65 | 1 | 把坏文件排到第 2 位，后面 6 个仍必须全部被评估。 |
| `test_batch_sample_is_deterministic_stride` 函数 | 82 | 1 | sample=5 抽 5 本，且两次跑结果完全相同（确定性等距）。 |
| `test_batch_sample_zero_or_none_means_all` 函数 | 95 | 1 | — |
| `test_batch_no_db_write` 函数 | 101 | 1 | — |
| `test_batch_limit_files_truncates` 函数 | 112 | 1 | — |
| `test_batch_rows_are_thin` 函数 | 119 | 1 | 每行只有摘要字段（不回传全文——payload 红线）。 |
| `test_batch_scan_preview_dir_missing` 函数 | 128 | 1 | — |
| `test_batch_scan_preview_dir_sorted_and_filtered` 函数 | 133 | 1 | — |
| `test_batch_never_asks_for_deep` 函数 | 144 | 1 | **批量路径默认不外发**：不传 deep_fallback 时每个文件都必须以 False 解析。 |
| `test_batch_deep_switch_defaults_off_and_optin_really_wires_through` 函数 | 170 | 1 | D5 后的新契约（**替代**原 `test_batch_preview_batch_has_no_deep_switch`）。 |
| `test_batch_limit_files_negative_is_clamped` 函数 | 214 | 1 | 负的 limit_files 不得静默"从尾部砍"（审计 P2-2）：夹到 0 → 一个都不评估。 |
| `test_api_preview_ok_envelope` 函数 | 225 | 1 | — |
| `test_api_preview_bad_requests` 函数 | 247 | 1 | — |
| `test_api_preview_requires_token` 函数 | 262 | 1 | — |
| `test_api_blocked_doc_is_200_not_5xx` 函数 | 270 | 1 | 坏文档 → HTTP 200 + verdict=block（不是 500，也不是 4xx）。 |
| `test_api_preview_allow_deep_is_wired_and_reported` 函数 | 281 | 1 | D5：`allow_deep=true` 从"422 拒绝"改为**真接线 + 如实标注**（替代原。 |
| `test_api_preview_allow_deep_non_bool_is_rejected` 函数 | 311 | 1 | `allow_deep` 必须**严格布尔**，且**只有真布尔 true 才开启**（独立复核 F4）。 |
| `test_api_preview_accepts_extensionless_pdf` 函数 | 335 | 1 | **无扩展名的 PDF 必须被接受**（真机发现）：DSH 附件是哈希文件名。 |
| `test_api_preview_rejects_non_pdf_content` 函数 | 350 | 1 | 内容是垃圾、后缀也不是 .pdf → 请求级 422（判定权在 dry_run，路由不重复实现）。 |
| `test_api_batch_and_inbox` 函数 | 360 | 1 | — |

### `tests/test_dryrun_report.py`（56 个符号）

> C 组 + B 组：R27 预览的拦截与只读。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_save` 函数 | 37 | 8 | — |
| `_mk_good_pdf` 函数 | 43 | 27 | 5 页、40 条规范条款（含模态词与数值）——不应被判 block。 |
| `_mk_pua_prefix_pdf` 函数 | 67 | 2 | GB 出版 PDF 的 PUA 错位形态（封面 '犌犅／犜' + 正文条款）。 |
| `_mk_skewed_pdf` 函数 | 85 | 4 | 逐字排版制造真实倾角（每字 dx=6pt，dy 按 tan(deg) 递增）。 |
| `_mk_sparse_pdf` 函数 | 106 | 6 | 6 页、每页仅 5 字 → 近乎空白。 |
| `_mk_fragmented_pdf` 函数 | 116 | 2 | 大量 3 字碎片行：文本层有 200+ 字，但切不出条款（全部按 <4 字丢弃）。 |
| `_mk_scan_pdf` 函数 | 130 | 6 | 只有图片、无文本层 → 应当是 warn（W1），不是 block（不许误伤扫描件）。 |
| `_mk_broken_file` 函数 | 146 | 5 | — |
| `fake_parse` 函数 | 156 | 17 | 把解析换成受控返回值。 |
| `_block` 函数 | 176 | 9 | — |
| `test_verdict_pua_mangled_blocks` 函数 | 181 | 1 | 乱码（适配器判定的 PUA 错位不可修复）→ block B1。 |
| `test_verdict_collapse_blocks` 函数 | 191 | 1 | 正文 ≥2000 字却切不出条款 → block B2（坍缩）。 |
| `test_verdict_weird_ratio_blocks` 函数 | 202 | 1 | 异常字符占比 ≥30%（采样窗口之外的乱码，适配器采样不到）→ block B5。 |
| `test_verdict_replacement_ratio_blocks` 函数 | 214 | 1 | 替换字符 U+FFFD 占比 ≥5% → block B6（与 B5 不同：FFFD 属正常区符号）。 |
| `test_verdict_preview_never_asks_for_deep` 函数 | 224 | 1 | **零外发**的关键断言：预览必须传 deep_fallback=False 且 force_deep=False。 |
| `test_verdict_scan_warn_when_deep_skipped` 函数 | 232 | 1 | — |
| `test_blk_severe_skew` 函数 | 246 | 1 | — |
| `test_blk_sparse_pages` 函数 | 255 | 1 | — |
| `test_blk_fragmented_not_blocked` 函数 | 262 | 1 | 碎片化文本（120 行 3 字词）**不判 block**——它切出一条「前置说明」，字数也没到坍缩线。 |
| `test_blk_broken_file` 函数 | 272 | 1 | — |
| `test_blk_missing_file` 函数 | 279 | 1 | — |
| `test_blk_wrong_suffix` 函数 | 285 | 1 | — |
| `test_blk_good_doc_not_blocked` 函数 | 296 | 1 | — |
| `test_blk_pua_recovered_not_blocked` 函数 | 306 | 1 | 可归一化修复的 PUA 错位必须被救回（否则白走 OCR 丢字）。 |
| `test_blk_scanned_is_warn_not_block` 函数 | 314 | 1 | 扫描件（无文本层）应当是 warn + 零外发，不是 block。 |
| `test_blk_multipage_scan_is_warn_not_block` 函数 | 325 | 1 | **多页**扫描件同样只 warn：B4「近乎空白」不得对"无文本层"开火。 |
| `test_blk_straight_not_flagged` 函数 | 341 | 1 | 正排（θ=0）不许出现倾斜判据。 |
| `test_blk_mild_skew_warns_not_blocks` 函数 | 348 | 1 | 2° 轻度倾斜 → warn（W2），不 block。 |
| `_report` 函数 | 359 | 26 | 一份"干净"报告底稿。 |
| `test_verdict_clean_is_ok` 函数 | 379 | 1 | — |
| `test_verdict_mixed_skew_blocked_by_page_ratio` 函数 | 384 | 1 | B3 第二支：文档中位倾角未到 3°，但**多数页各自严重倾斜** → 仍须拦。 |
| `test_verdict_skew_boundary_2_9_warns_3_0_blocks` 函数 | 394 | 1 | 倾斜阈值边界：2.9° → warn(W2)。 |
| `test_verdict_missing_metric_never_blocks` 函数 | 404 | 1 | 缺失度量不得触发 block（docstring 承诺）：无 chars_per_page 时 B4 不得开火。 |
| `test_verdict_weird_ratio_boundary` 函数 | 413 | 1 | 异常字符率边界：29.9% 不拦。 |
| `test_verdict_replacement_boundary_and_zero` 函数 | 426 | 1 | 替换字符率边界：0% 不拦、4.99% 不拦、5% 拦。 |
| `test_verdict_collapse_boundary` 函数 | 436 | 1 | 坍缩边界：chars=1999 不拦、2000 且 clauses=1 拦、2000 且 clauses=2 不拦。 |
| `test_verdict_sparse_pages_boundary` 函数 | 446 | 1 | 近乎空白边界：4 页不拦（下限 5）、5 页且 19.9 字/页拦、20 字/页不拦。 |
| `test_verdict_w3_suspect_ratio` 函数 | 456 | 1 | W3 可疑条款占比（verifier 审计：原无覆盖）。 |
| `test_verdict_w5_low_type_confidence` 函数 | 465 | 1 | W5 分型置信度偏低（原无覆盖）。 |
| `test_verdict_w10_low_clause_density` 函数 | 476 | 1 | W10 条款密度异常偏低（原无覆盖）。 |
| `test_verdict_duplicate_warns` 函数 | 483 | 1 | W6 与库内重复 → warn（不 block：重复是可覆盖的正常情形）。 |
| `test_grade_boundaries` 函数 | 490 | 1 | 分级边界（R13 契约）：0.95→A、0.85→B、0.8499→C。 |
| `test_clause_ocr_confidence_units` 函数 | 499 | 1 | 条款级置信度的扣分项（含原不可达的 tiny 与不可打印字符）。 |
| `test_clause_head_is_raw_prefix` 函数 | 513 | 1 | `head` 必须**逐字符**等于原文前 80 字（证据文本不可变红线。 |
| `_mk_table_pdf` 函数 | 534 | 3 | 带**矢量框线表**的 PDF（fitz 画线 + 单元格文字）。 |
| `test_preview_table_tags_are_live` 函数 | 560 | 1 | **表格类体检标签在预览里可达**（verifier 审计 P0-3 的回归网）。 |
| `test_preview_table_pipeline_runs_on_real_pdf` 函数 | 591 | 1 | 真 PDF 层：合成框线表必须被预览的表格重建捕获（不再只走文本层）。 |
| `test_preview_doc_type_changes_typing` 函数 | 597 | 1 | `doc_type` 必须**真的影响分型**（不是参数回显）。 |
| `test_tail_samples_when_fewer_than_n` 函数 | 614 | 1 | 条款数 ≤ N 时尾部样本退回全部（原实现给空数组。 |
| `_table_snapshot` 函数 | 630 | 3 | — |
| `test_dry_no_row_written_any_table` 函数 | 638 | 1 | — |
| `test_dry_no_new_table` 函数 | 653 | 1 | — |
| `test_dry_temp_dir_under_data_dir_and_hash_isolated` 函数 | 663 | 1 | 临时产物必须落在 data_dir/dryrun/tmp/<hash16>/，且不同文件互不覆盖。 |
| `test_dry_no_pdf_copy` 函数 | 678 | 1 | 预览不得复制/移动用户文件（源文件与目录清单不变）。 |
| `test_dry_analyze_preview_contract_frozen` 函数 | 687 | 2 | 既有 `analyze_preview` 的返回键集合不得变化（它是被别处依赖的老接口）。 |
| `test_dry_typing_uses_doc_type` 函数 | 696 | 1 | F8 修复的证据：预览分型必须把 doc_type 传下去（法规类文档要出现 legal）。 |

### `tests/test_effect_report.py`（20 个符号）

> 效力报告测试（决策 21 · 用户修订版）：状态四色映射/惰性翻转口径/分类树同构/

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_doc_meta` 函数 | 12 | 2 | 同文件用例共享库：每用例前后清本文件种下的文档。 |
| `_mk_doc` 函数 | 30 | 31 | — |
| `world` 函数 | 51 | 15 | 混合文档世界：标准树/法规树/各状态/翻转边界/隐藏文档/无 CCS 兜底。 |
| `test_eff_01_colors_and_flip` 函数 | 102 | 1 | 五色映射 + resolve_status 双向翻转口径（复用不复制）。 |
| `test_eff_01b_reference_is_its_own_filterable_category` 函数 | 119 | 1 | 🔵 仅参考**能单独筛出来**（业主要的就是"在有效性里作为单独的一个类别"），。 |
| `test_eff_02_flip_doc_lands_in_green_bucket` 函数 | 132 | 1 | 实施日已到的 upcoming → 报告行 status=effective（惰性翻转复用）。 |
| `test_eff_03_tree_shape_two_tops_no_mixed` 函数 | 144 | 1 | 两棵树不混排：std（CCS 大类→区间→类目）与 law（效力等级→部门/领域）。 |
| `test_eff_04_windows` 函数 | 161 | 1 | 窗口四档：upcoming90（2099 不入）/recent90（含今天边界）/retired90 只认。 |
| `test_eff_05_color_filter` 函数 | 180 | 1 | color 子集过滤：只看红色清单。 |
| `test_eff_06_docs_endpoint_validation` 函数 | 188 | 1 | top/l2 必填 422 语义。 |
| `test_eff_07_docs_limit_offset` 函数 | 207 | 1 | limit/offset 分页。 |
| `test_eff_08_export_xlsx_reopenable` 函数 | 221 | 1 | xlsx 落 exports、openpyxl 重开：sheet 名/总览数字/明细行数与层级列。 |
| `test_eff_09_export_empty_db` 函数 | 245 | 2 | 空库：出文件、汇总全 0、明细仅表头（镜像"空批次同样出报告"）。 |
| `test_eff_10_no_hidden_docs` 函数 | 262 | 1 | catalog_hidden=1 在聚合/明细/导出三处全部缺席。 |
| `test_eff_11_by_color_topn` 函数 | 271 | 1 | 全库按色取 top-N：只含该色、色内按标准号、limit 截断、count 为过滤后总数。 |
| `test_eff_12_by_color_per_color_multi` 函数 | 287 | 1 | verifier F4：多色一次聚合（per_color=True）每色各取 n 条。 |
| `TestExportEndpointBody` 类 | 308 | 1 | `POST /report/effect/export` 的 **HTTP 层**契约（2026-09-18，§10.71）。 |
| `test_no_body_still_exports` 函数 | 322 | 1 | 完全没有 body（host 侧老调用点就是这么发的）⇒ 照常出文件。 |
| `test_explicit_window_body` 函数 | 329 | 1 | — |
| `test_malformed_json_is_422_not_silently_empty` 函数 | 335 | 1 | 非法 JSON：**422**（不是"当成空 body 照常出文件"）——这是 §10.71 的有意收紧。 |

### `tests/test_egress.py`（7 个符号）

> Task 10.0 外发审计测试：record_egress 落库 / chat 链路自动记录 / 审计 API / 导出。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_record_egress_writes_dump` 函数 | 7 | 1 | — |
| `test_chat_flow_leaves_egress_record` 函数 | 24 | 1 | chat 链路每次提问自动落外发记录（user_export，含 prompt/llm_output）。 |
| `test_egress_audit_api` 函数 | 42 | 1 | — |
| `test_egress_query_keyset_cursor` 函数 | 58 | 1 | keyset 深翻页（2026-08-26）：按 (created_at, dump_id) 键集翻页无重复无遗漏。 |
| `test_egress_audit_export` 函数 | 81 | 1 | — |
| `test_ks_answer_leaves_audit_record` 函数 | 100 | 1 | D2 红线回归：取证端点 `/ks/answer` 也必须落 debug_dump（user_export）。 |
| `test_ks_answer_record_is_not_evicted_by_egress_volume` 函数 | 140 | 1 | **服务端那个写入者**必须裁「提问证据」这一类（2026-09-26 复核 MED-1 的另半边）。 |

### `tests/test_embedder_health.py`（14 个符号）

> 向量引擎的**健康语义**与**失败冷却**（§10.74）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean_embedder` 函数 | 21 | 11 | 把 embedder 的单例状态清干净，并在测试后恢复（模块级全局，必须自己收尾）。 |
| `TestHealthIsCheap` 类 | 29 | 1 | `health()` 三态**只读证据**，且**绝不触发加载**。 |
| `test_从没试过时是_unknown_而不是去加载` 函数 | 32 | 0 | — |
| `test_加载成功过才是_ok` 函数 | 43 | 0 | — |
| `test_最近一次失败是_offline` 函数 | 47 | 0 | — |
| `TestFailureCooldown` 类 | 57 | 1 | 失败**进冷却窗口**：窗口内不重试，窗口过去后允许再试（不永久拉黑）。 |
| `test_窗口内不重试` 函数 | 60 | 0 | — |
| `test_窗口过去后允许再试一次` 函数 | 74 | 0 | — |
| `test_成功之后清掉上次失败` 函数 | 89 | 0 | 先失败、冷却过去、再成功 ⇒ `_load_error` 必须被清掉，`health()` 变 ok。 |
| `test_窗口长度是个正数秒的常量` 函数 | 113 | 0 | — |
| `TestHealthEndpointsDoNotLoad` 类 | 117 | 1 | **HTTP 层**：健康类端点不许触发模型加载（判据 = 替身没被调用）。 |
| `test_健康端点不加载向量模型` 函数 | 121 | 0 | — |
| `test_health_的_vector_engine_取值在三态之内` 函数 | 134 | 0 | — |
| `test_健康看板的_vector_同样在三态之内` 函数 | 139 | 0 | — |

### `tests/test_embedding_rebuild_resume.py`（22 个符号）

> exp-17 影子向量表重建脚本（`eval/recall-funnel/exp-17-embedding-production-plan/rebuild-shadow.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 60 | 125 | — |
| `test_display_text_matches_production_formula` 函数 | 75 | 3 | — |
| `test_production_source_still_has_the_same_formula` 函数 | 88 | 1 | 静态锚点：生产源码里必须仍有 `title or ''` + `content_text\[:512\]` 的 f-string。 |
| `test_text_formula_sha_is_stable_and_sensitive` 函数 | 98 | 1 | — |
| `test_ckpt_guard_allows_matching` 函数 | 113 | 1 | — |
| `test_ckpt_guard_rejects_each_mismatch` 函数 | 125 | 1 | — |
| `_make_source` 函数 | 137 | 7 | — |
| `_fake` 函数 | 154 | 52 | — |
| `_rows` 函数 | 160 | 33 | — |
| `test_fake_vector_is_deterministic_and_normalized` 函数 | 170 | 2 | — |
| `test_resume_is_row_identical_to_one_shot` 函数 | 179 | 3 | — |
| `test_resume_with_limit_below_total_writes_exactly_target` 函数 | 201 | 2 | ★ **`limit < 非空总数` + 续跑**时必须只补缺口（`LIMIT max(0, target - done)`）。 |
| `_open` 函数 | 232 | 3 | 打开影子库（**必须加载 vec0 扩展**，否则连 `COUNT(*)` 都报 `no such module`）。 |
| `test_checkpoint_never_drifts_from_data` 函数 | 240 | 2 | `ckpt.done` 必须恒等于影子表行数 —— 这是"checkpoint 与数据同事务"的可观测不变量。 |
| `test_rerun_is_idempotent` 函数 | 255 | 2 | — |
| `test_stop_after_batches_boundary_is_inclusive` 函数 | 267 | 2 | `--stop-after-batches N` 必须**恰好跑 N 批**（边界是 `>=`，不是 `>`）。 |
| `test_ckpt_records_all_guard_keys` 函数 | 281 | 1 | — |
| `test_instruct_prefix_is_the_official_string` 函数 | 296 | 2 | 官方原串，逐字。 |
| `test_real_embedder_source_keeps_e4_pooling_and_truncation` 函数 | 306 | 2 | **静态锚点**：真嵌入函数必须仍是 E4 的口径 —— EOS 池化 + MRL 截断 + 重新 L2 归一化。 |
| `test_shadow_dim_matches_production_schema` 函数 | 339 | 2 | 影子表维度必须 = 生产 `clause_vec` 的维度 ⇒ 换表**不需要改 schema**。 |
| `test_ckpt_and_data_are_committed_in_the_same_transaction` 函数 | 365 | 1 | **静态锚点**：提交块里 `_write_ckpt(...)` 必须**先于**唯一的 `conn.commit()`。 |
| `test_module_has_no_write_path_to_source` 函数 | 383 | 1 | 只读承诺的机械检查：脚本源码里不许出现对 `--source` 的写语句。 |

### `tests/test_fewshot.py`（2 个符号）

> Task 13.4 R17 轻量版测试：负向反馈聚类 → Few-shot 注入。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_fewshot_injection_from_feedback` 函数 | 5 | 1 | — |
| `test_fewshot_empty_no_change` 函数 | 31 | 1 | — |

### `tests/test_figure_legend.py`（19 个符号）

> 图例归图契约测试（2026-09-15，figure-neighborhood 类跨 3 文档达线根因修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestLegendDetect` 类 | 16 | 1 | — |
| `test_header_standard` 函数 | 17 | 1 | — |
| `test_header_garbled_ocr` 函数 | 20 | 1 | — |
| `test_single_line_multi_items` 函数 | 24 | 1 | — |
| `test_two_item_lines` 函数 | 28 | 1 | — |
| `test_normal_clause_not_legend` 函数 | 31 | 1 | — |
| `test_mention_without_items_not_legend` 函数 | 35 | 1 | — |
| `test_empty` 函数 | 38 | 4 | — |
| `TestLegendGeometry` 类 | 43 | 1 | — |
| `test_adjacent_below_top_origin` 函数 | 44 | 1 | — |
| `test_adjacent_above_image_accepted` 函数 | 48 | 1 | — |
| `test_far_block_rejected` 函数 | 52 | 1 | — |
| `test_x_far_rejected` 函数 | 55 | 1 | — |
| `test_missing_bbox` 函数 | 58 | 1 | — |
| `_mj_with_image_and_legend` 函数 | 63 | 4 | — |
| `TestIntegration` 类 | 77 | 4 | — |
| `test_legend_attached_to_figure_not_clause` 函数 | 78 | 1 | — |
| `test_far_legend_stays_text` 函数 | 92 | 1 | — |
| `test_clause_text_kept` 函数 | 102 | 1 | — |

### `tests/test_figure_legend_strip.py`（10 个符号）

> 图例段切除契约测试（2026-09-15，收敛循环第 6 轮根因）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestLegendSegmentStripped` 类 | 12 | 1 | — |
| `test_real_artifact_shape` 函数 | 13 | 1 | — |
| `test_caption_terminates_segment` 函数 | 26 | 2 | — |
| `test_two_segments_in_one_block` 函数 | 34 | 1 | — |
| `test_idempotent` 函数 | 44 | 7 | — |
| `TestLegendReverseControls` 类 | 50 | 1 | 反向对照：不得误切没有图例实体的正文。 |
| `test_head_without_entries_kept` 函数 | 53 | 1 | — |
| `test_dash_line_without_head_kept` 函数 | 58 | 1 | — |
| `test_plain_text_untouched` 函数 | 62 | 2 | — |
| `test_empty` 函数 | 66 | 4 | — |

### `tests/test_file_digest.py`（5 个符号）

> `src/core/file_digest.py` 的判据（2026-10-23 统一化第二批）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_empty_file_digest` 函数 | 32 | 1 | 空文件的 SHA-256 是标准常量 —— 算错说明初始化/循环写错了。 |
| `test_known_content_digest` 函数 | 44 | 1 | `b"abc"` 的 SHA-256 是公开标准值。 |
| `test_chunk_boundaries_match_whole_file_hash` 函数 | 59 | 1 | 跨分块边界时，分块算法必须与「一次读全」得到同一个指纹。 |
| `test_two_call_sites_share_one_implementation` 函数 | 71 | 1 | 两个历史调用点必须**指向同一个函数对象**（防有人又各写一份）。 |
| `test_chunk_size_is_frozen` 函数 | 84 | 1 | 分块大小是**历史指纹的契约**，不许改。 |

### `tests/test_filing_state_pipeline.py`（32 个符号）

> 入库管线**写处理状态** + 「重来一次」+ `catalog_hidden` 复位（KB-FOLDER-PLAN 第 4 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_own_data_dir` 函数 | 48 | 5 | **本模块私有的临时数据目录**（跑完即弃，其他模块零影响）。 |
| `_write_pdf` 函数 | 101 | 23 | 一页真实 PDF（只为了让 `run_full_ingest` 的前置检查与 `measure_skew` 有文件可开）。 |
| `synthetic_parser` 函数 | 112 | 43 | 把 `run_parser_isolated` 换成**给定 blocks 的合成结果**（真链路，只有解析这一步是假的）。 |
| `_uniq_no` 函数 | 134 | 13 | 本会话唯一的标准号（`doc_meta.standard_no` 有唯一约束，临时库是会话级的）。 |
| `_inbox_rows` 函数 | 139 | 7 | 把「待分类」**翻页读全**（每页上限 200，按 offset 走到 has_more 为假）。 |
| `_offline_embedder` 函数 | 162 | 4 | 向量引擎强制离线（与 `test_ks_answer` 同一手法）。 |
| `test_real_ingest_writes_filing_state` 函数 | 176 | 1 | 正例：真跑一次入库 ⇒ `doc_filing_state` 有这一行、`stage` 与识别率**真的被写**。 |
| `test_reverse_without_the_hook_no_state_row` 函数 | 194 | 1 | **反向哨兵**：把"写状态"这个出口打断 ⇒ 状态行**必须**不出现。 |
| `test_zero_clause_ingest_is_failed_and_still_visible_in_inbox` 函数 | 213 | 1 | 一条正文条款都没提出来 ⇒ `failed` + 失败原因 + `catalog_hidden=1`，**但仍在「待分类」里**。 |
| `test_reverse_good_doc_is_hidden_zero` 函数 | 232 | 1 | 反向：提出真条款的那一篇 ⇒ `catalog_hidden` 必须是 **0**（显式复位那条语句）。 |
| `test_reingest_parses_the_same_file_again_and_resets_hidden` 函数 | 250 | 1 | 「重来一次」：同一篇（先被隐藏）重导后 ⇒ 新行 `catalog_hidden=0` + 状态 `confirming`。 |
| `test_reingest_endpoint_marks_recognizing_and_parses` 函数 | 287 | 1 | **端点级**：`POST /kb/inbox/reingest` 立刻返回 + 真的把这一篇重导了（另起后台线程）。 |
| `test_reingest_endpoint_skips_missing_source_and_rejects_empty` 函数 | 324 | 1 | 边界：源文件不在磁盘上 ⇒ **如实跳过并说明**。 |
| `test_bulk_import_really_parses_and_writes_states` 函数 | 345 | 1 | 批量导入：`resume` 之后**真的有条款** + 占位行的状态从 `recognizing` 走到终态。 |
| `test_bulk_import_batch_flag_is_declared_and_default_false` 函数 | 382 | 1 | 批次开关：`create_bulk_batch(..., reingest=True)` 落在 checkpoint 里。 |
| `test_bulk_terminal_state_carries_files_whose_state_was_not_written` 函数 | 397 | 1 | 把"写状态"这个出口打断 ⇒ **批次终态**里要带出"哪几篇的状态没写进去"。 |
| `test_bulk_terminal_state_is_empty_when_states_were_written` 函数 | 429 | 1 | **反向**：状态正常写进去时，那一份清单必须是**空的**、接口报 0（不许恒报"有文件没写"）。 |
| `test_confidence_none_means_uncomputable_on_both_sides` 函数 | 449 | 1 | 识别率**算不出来**时：入库侧写 NULL、预览侧给 `None` —— **都不是 0.0**。 |
| `test_grading_tells_the_truth_when_confidence_is_uncomputable` 函数 | 518 | 1 | `grade_document(None)`：档位仍是 C（结果不变），但**理由**必须说"算不出来"。 |
| `test_bulk_endpoint_passes_force_and_reingest` 函数 | 531 | 1 | 接口层：`POST /ingest/bulk` 的 `reingest` / `force` 都要真的传下去（两个名字同义）。 |
| `test_abort_is_sticky_against_worker_resurrection` 函数 | 564 | 1 | 乙1 判据（2026-09-22）：中止后的终态**不许**被工作线程的状态写复活。 |
| `test_filed_doc_failure_writeback_flips_and_shows_in_inbox` 函数 | 594 | 1 | 乙3 判据（2026-09-22）：预标 `filed`（上传即归位）的文档，解析失败的回写必须。 |
| `test_flat_folders_supports_search_and_depth` 函数 | 621 | 1 | `GET /kb/folders/flat`：整棵树带路径、可按名字/路径搜、`depth` 是路径段数。 |
| `test_stage_labels_endpoint_is_the_single_owner` 函数 | 639 | 1 | 标签由**接口**下发（界面上那份镜像不再是唯一所有者）。 |
| `test_failure_kind_vocabulary_matches_the_migration_script` 函数 | 649 | 1 | 失败原因的**中文字面量**只有一个所有者：迁移脚本那份必须与 `folder_store` 逐字相同。 |
| `test_inbox_payload_carries_new_suggestion_fields` 函数 | 661 | 1 | 「待分类」每一项都带 `stage_label` / `suggest_new_parent_id` / `suggest_new_name` / `catalog_hidden`。 |
| `test_inbox_suggest_new_names_the_missing_segment` 函数 | 681 | 1 | 分类口径比命中的现有目录**更深** ⇒ 给出"在 XXX 下新建 XXX"的两个真值。 |
| `test_inbox_hidden_but_failed_doc_is_listed` 函数 | 713 | 1 | `catalog_hidden=1` 且 `stage='failed'` 的那一篇**必须**在列表里（§十七的硬要求）。 |
| `test_reingest_busy_is_409_not_a_queue` 函数 | 734 | 1 | 同一时刻只跑一批：锁被占 ⇒ **409 `reingest_busy`**（不许"排队等"）。 |
| `test_reingest_rejects_too_many_docs` 函数 | 749 | 1 | 边界：一次点太多 ⇒ 422（后台线程是串行的，防"手一抖选 379 篇"）。 |
| `test_reingest_plan_is_read_only` 函数 | 759 | 1 | `plan_reingest` 是**只读**的：它不许写状态、不许动库。 |
| `test_json_marker_file_path_is_skipped_honestly` 函数 | 774 | 1 | 快扫/异常行的 `file_path` 是标记 JSON ⇒ 如实跳过（不许拿它去 open）。 |

### `tests/test_folder_filing_plan.py`（14 个符号）

> 归位计划与预览清单的用例（KB-FOLDER-PLAN §五第 1 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `nm` 函数 | 17 | 150 | — |
| `doc` 函数 | 21 | 666 | — |
| `paths_of` 函数 | 30 | 3 | — |
| `test_plan_uses_the_same_classification_as_the_catalog` 函数 | 36 | 1 | **接线断言**：计划给的路径必须就是 `classify_document` 那四级，。 |
| `test_plan_puts_unclassified_into_pending_without_folders` 函数 | 50 | 1 | — |
| `test_plan_excludes_hidden_docs` 函数 | 72 | 1 | — |
| `test_plan_deep_and_direct_counts` 函数 | 81 | 1 | — |
| `test_plan_records_anomalies_instead_of_guessing` 函数 | 92 | 1 | 值为空 / 名字超上限 ⇒ 进 anomalies，**不**静默塞进某个目录。 |
| `test_plan_duplicate_and_missing_ids_are_anomalies` 函数 | 111 | 1 | — |
| `test_plan_is_repeatable` 函数 | 121 | 1 | — |
| `_insert` 函数 | 131 | 7 | — |
| `test_apply_plan_on_small_fixture_db` 函数 | 141 | 1 | 小 fixture 库上真跑一遍：目录树、归属、状态、含更深层计数都读得回来。 |
| `_report` 函数 | 181 | 26 | — |
| `test_render_text_has_the_sections_the_owner_asked_for` 函数 | 193 | 1 | — |

### `tests/test_folder_store.py`（36 个符号）

> 多级目录存储层用例（KB-FOLDER-PLAN 第 1 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `nm` 函数 | 27 | 150 | 本次会话内唯一的目录名（db fixture 是 session 级 ⇒ 名字不能撞）。 |
| `mkdoc` 函数 | 32 | 25 | — |
| `expect_code` 函数 | 42 | 36 | — |
| `test_create_and_same_name_same_level_rejected` 函数 | 51 | 1 | — |
| `test_rename_folder_and_conflict` 函数 | 62 | 1 | — |
| `test_name_and_depth_limits_have_readable_errors` 函数 | 72 | 1 | — |
| `test_folder_name_allows_slash` 函数 | 82 | 1 | ⚠ CCS 区间名自带斜杠（P15/19）⇒ 目录名必须允许 `/`，否则真实分类树建不出来。 |
| `test_one_file_in_two_folders` 函数 | 90 | 1 | — |
| `test_add_member_is_idempotent_and_unknown_doc_rejected` 函数 | 104 | 1 | — |
| `test_move_member_between_folders` 函数 | 114 | 1 | — |
| `test_copy_folder_shares_members_and_is_independent` 函数 | 126 | 1 | — |
| `test_copy_folder_into_own_subtree_rejected` 函数 | 155 | 1 | — |
| `test_copy_folder_rejects_its_own_subtree` 函数 | 161 | 1 | 第 2 步补：``copy_folder`` 自己也要拒环。 |
| `test_top_level_order_is_sort_then_pinyin` 函数 | 178 | 1 | 四个顶层（标准 10 / 法律法规 20 / 公司制度 30 / 待分类 90）必须按 **sort** 排。 |
| `test_move_folder_rejects_cycle` 函数 | 207 | 1 | — |
| `_kids` 函数 | 232 | 10 | — |
| `test_move_folder_by_from_to_updates_main_position_when_from_is_main` 函数 | 236 | 1 | — |
| `test_move_folder_defaults_to_the_main_position` 函数 | 254 | 1 | 省略 ``from_parent_id`` = 挪"这个目录本身"（旧调用的行为一字不变）。 |
| `test_move_folder_from_a_copy_to_a_third_place_adds_the_new_edge` 函数 | 267 | 1 | ③ 从**复制出来的那一处**挪到**第三处** ⇒ 删源边 **+ 补新边**（业主裁定以代码为准）。 |
| `test_move_folder_from_a_copy_to_the_top_really_lands_at_the_top` 函数 | 295 | 1 | ④ ``to_parent_id=None``（挪到顶层）⇒ **真的到顶层**，不是"删条边 + 回 moved=true"。 |
| `test_move_folder_from_a_place_that_does_not_hold_it` 函数 | 317 | 1 | — |
| `test_move_folder_to_the_same_place_is_a_noop` 函数 | 327 | 1 | — |
| `test_move_folder_name_conflict_at_target` 函数 | 335 | 1 | — |
| `test_delete_empty_folder_ok` 函数 | 348 | 1 | — |
| `test_delete_nonempty_requires_mode` 函数 | 355 | 1 | — |
| `test_delete_reparent_moves_members_to_parent` 函数 | 367 | 1 | — |
| `test_delete_reparent_rejects_top_level_folder` 函数 | 396 | 1 | 业主点名的边界①：一级目录没有上一层 ⇒ reparent 必须报可读中文错，。 |
| `test_delete_purge_keeps_docs_present_elsewhere` 函数 | 415 | 1 | 业主点名的边界②：purge 时**还挂在别的目录里**的文件只是丢归属，**不真删**。 |
| `test_purge_uses_given_db_path` 函数 | 449 | 2 | ⚠ 安全用例：purge 的真删**必须**落在传进来的那个库上。 |
| `test_describe_folder_delete_numbers` 函数 | 486 | 1 | 「先问一句」要的数字：一级目录 reparent 不可用。 |
| `test_list_folder_pagination_and_deep_counts` 函数 | 515 | 1 | — |
| `test_list_root_shows_toplevel_folders_and_unfiled_docs` 函数 | 541 | 1 | — |
| `test_folder_scope_includes_deeper_levels_and_unions` 函数 | 554 | 1 | — |
| `test_build_folder_tree_batch_atomic` 函数 | 583 | 1 | — |
| `test_build_folder_tree_reuse_existing_is_idempotent` 函数 | 617 | 1 | ``reuse_existing=True`` ⇒ 同一批 nodes 重复跑**不建重复目录**（一次性归位脚本要的幂等）。 |
| `test_filing_state_lifecycle_and_lists` 函数 | 646 | 1 | — |

### `tests/test_formula_fragment_glue.py`（21 个符号）

> 公式内无歧义劈开的行级粘合契约测试（2026-09-15，收敛循环第 7 轮）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestDotSplit` 类 | 15 | 1 | — |
| `test_digit_dot_digit_glued` 函数 | 16 | 1 | — |
| `test_decimal_untouched` 函数 | 19 | 1 | — |
| `test_dot_with_one_side_space` 函数 | 22 | 1 | — |
| `TestAttachedDigitPair` 类 | 28 | 1 | — |
| `test_after_open_paren` 函数 | 29 | 1 | — |
| `test_after_cjk` 函数 | 34 | 1 | — |
| `test_after_cjk_with_unit` 函数 | 39 | 1 | — |
| `test_multi_char_tokens_not_merged` 函数 | 44 | 1 | — |
| `TestAlnumTail` 类 | 52 | 1 | — |
| `test_upper_pair_after_digit_glued` 函数 | 53 | 1 | — |
| `test_single_upper_letter_after_digit_kept` 函数 | 59 | 1 | — |
| `test_mixed_run_glued` 函数 | 64 | 1 | — |
| `TestTwoLetterUnitInch` 类 | 69 | 1 | — |
| `test_inch_glued` 函数 | 70 | 1 | — |
| `TestReverseControls` 类 | 75 | 2 | — |
| `test_variable_product_kept` 函数 | 76 | 1 | — |
| `test_legit_value_unit_space_kept` 函数 | 79 | 1 | — |
| `test_thousands_separator_kept` 函数 | 84 | 1 | — |
| `test_plain_text_untouched` 函数 | 87 | 2 | — |
| `test_idempotent` 函数 | 91 | 7 | — |

### `tests/test_formula_leader.py`（15 个符号）

> 公式编号引导点线清洗契约测试（2026-09-15 全库审计 dot-leader 类达线修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestNumberedLeader` 类 | 16 | 1 | — |
| `test_long_u2026_leader_with_broken_number` 函数 | 17 | 1 | — |
| `test_short_u2026_leader` 函数 | 21 | 1 | — |
| `test_ascii_dots_with_number` 函数 | 25 | 1 | — |
| `test_closing_paren_already_present` 函数 | 28 | 1 | — |
| `TestBareLeader` 类 | 32 | 1 | — |
| `test_ascii_dots_run_removed` 函数 | 33 | 1 | — |
| `test_long_u2026_run_removed` 函数 | 36 | 1 | — |
| `TestProsePreserved` 类 | 40 | 1 | — |
| `test_two_char_ellipsis_survives` 函数 | 41 | 1 | — |
| `test_plain_text_unchanged` 函数 | 45 | 2 | — |
| `test_empty` 函数 | 48 | 4 | — |
| `TestIdempotent` 类 | 53 | 1 | — |
| `test_idempotent_numbered` 函数 | 54 | 1 | — |
| `test_idempotent_bare` 函数 | 58 | 1 | — |

### `tests/test_formula_leader_appendix.py`（9 个符号）

> 附录字母号公式引导点线契约测试（2026-09-15，VLM 通道下 dot-leader 复测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestAppendixLetterLeader` 类 | 10 | 1 | — |
| `test_letter_number_normalized` 函数 | 11 | 1 | — |
| `test_multiple_letter_numbers` 函数 | 16 | 1 | — |
| `test_dotted_letter_number` 函数 | 20 | 1 | — |
| `test_plain_digit_still_works` 函数 | 24 | 1 | — |
| `test_idempotent` 函数 | 28 | 7 | — |
| `TestProseEllipsisSurvives` 类 | 34 | 1 | 反向对照：正文省略号必须存活（只能≤2 个 '…'）。 |
| `test_two_ellipsis_kept` 函数 | 37 | 1 | — |
| `test_normal_text_untouched` 函数 | 41 | 1 | — |

### `tests/test_fts_latin_prefix.py`（19 个符号）

> P3.1：英文词形变化那道缺口的判据（提问侧"词干 + 前缀"，**索引零改动**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_chinese_and_standard_numbers_are_byte_identical_under_both_modes` 函数 | 42 | 1 | 默认口径（开前缀）**不许**动到中文查询与标准号查询。 |
| `test_chinese_expression_contains_no_prefix_star` 函数 | 51 | 1 | — |
| `_table_with` 函数 | 57 | 5 | — |
| `_matches` 函数 | 64 | 5 | — |
| `test_english_inflection_is_findable_only_with_the_prefix_mode` 函数 | 69 | 1 | 同段只有 `extinguisher`，用 `extinguishers` 搜：。 |
| `test_english_plural_and_gerund_and_past_are_all_covered` 函数 | 79 | 1 | 三个方向各测一次（复数 / 进行式 / 过去式），别只测一个就下"英文能搜了"的结论。 |
| `test_the_reverse_direction_also_works` 函数 | 91 | 1 | 文档是**长形**、提问是**词干形**时也要能中（前缀查询天生覆盖这一向）。 |
| `test_acronyms_and_identifiers_are_not_expanded` 函数 | 98 | 1 | 全大写缩写、哈希、配置键都不许被改写（`porter` 在这些东西上是**破坏性**的，。 |
| `test_short_function_words_are_not_expanded` 函数 | 106 | 1 | `the`/`and`/`to` 这类虚词做前缀查询只会灌候选池，判据里明确放过它们。 |
| `test_short_stems_are_not_expanded` 函数 | 112 | 1 | **词干太短**的不扩写（词面够长也不行）。 |
| `test_internal_capitals_are_not_expanded` 函数 | 124 | 1 | **有内部大写**的标识符/缩写不扩写（`camelCase`/`backgroundColor`/`MAYBECAPS`）。 |
| `test_sentence_initial_capital_is_still_expanded` 函数 | 141 | 1 | 句首大写的普通词**要**放行（否则英文提问一半都白搭）。 |
| `test_known_false_hit_proper_noun_is_pinned` 函数 | 148 | 1 | **钉住一个已知的误命中，并用一条 xfail 留出"规则变好"的出口。 |
| `test_known_false_hit_actually_happens_end_to_end` 函数 | 167 | 1 | **钉害处**，不只钉表达式形状（复核 2026-09-25 建议）。 |
| `test_mixed_query_keeps_chinese_intact_and_expands_only_the_english_word` 函数 | 195 | 1 | — |
| `test_expression_is_always_valid_fts5_syntax` 函数 | 207 | 1 | 口径错的典型症状是**静默无命中**（报错被兜底 except 吞掉），。 |
| `test_prefix_star_only_ever_follows_a_quoted_token` 函数 | 232 | 1 | `"abc"*` 是合法前缀查询。 |
| `test_stem_helper_is_usable_from_many_threads` 函数 | 241 | 2 | **判据（不是普通用例）**：本函数由 FastAPI 的**同步路由**调用，那些路由跑在。 |
| `test_stem_helper_itself_is_thread_safe` 函数 | 264 | 1 | 直接压那条取词干的路径（不经过 jieba），把它单独钉住。 |

### `tests/test_fused_rewrite_ruler.py`（16 个符号）

> exp-14 融合侧改写尺子（`eval/recall-funnel/exp-14-fused-rewrite/run.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 47 | 125 | — |
| `test_b1_c1_only_touch_vector_channel` 函数 | 65 | 2 | ★ B1/C1 是**指令前缀**：只改向量通道的嵌入输入，FTS 必须保持原样。 |
| `test_d1_touches_vector_and_fts` 函数 | 76 | 2 | ★ D1 是**内容扩展**：向量与 FTS 都该用扩展串（精确/模态通道不走这两个钩子）。 |
| `test_a0_touches_nothing` 函数 | 82 | 2 | ★ A0 = 生产口径：两个通道都用原样提问。 |
| `test_headline_excludes_multi_def_and_dup` 函数 | 90 | 2 | ★ headline 必须真的剔掉 `gold_multi_def`/`gold_dup_text`（否则与 exp-8/exp-13 不同卷）。 |
| `_mk_items` 函数 | 107 | 19 | — |
| `_mk_runs` 函数 | 113 | 18 | — |
| `test_fused_top20_is_inclusive_at_boundary` 函数 | 122 | 2 | ★ 名次恰等于 20 算命中。 |
| `test_flip_side_treats_boundary_20_as_hit` 函数 | 131 | 1 | ★ 翻转统计那一侧也必须把**名次恰等于 20** 当命中 ——。 |
| `test_flip_and_delta_direction_on_asymmetric_sample` 函数 | 143 | 2 | ★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的**方向**：净改善必须读成正 Δ。 |
| `test_missing_cell_raises_instead_of_silently_filling` 函数 | 156 | 2 | ★ 缺一格必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。 |
| `test_by_subset_top20_partitions_by_label_and_is_inclusive` 函数 | 170 | 2 | ★ 副终点 `by_subset_top20` 必须**按 subset label 分组**、且组内阈值同样闭区间（`r<=20`）。 |
| `test_fused_hit_n_counts_non_none_ranks` 函数 | 186 | 2 | ★ 副终点 `fused_hit_n`（池内召回条数）必须数"名次非 None"，且与 `@20` 口径可分。 |
| `test_pool_median_definition_is_pinned` 函数 | 198 | 3 | ★ 上报的 `pool_median` 定义（偶数条取**上中位** `sorted\[n//2\]`）必须钉住 ——。 |
| `test_production_hook_points_still_exist` 函数 | 212 | 2 | ★ 三个钩子（只读连接注入 + 两个改写调用点）必须仍在生产代码里。 |
| `test_stop_loss_preregistered_contract` 函数 | 221 | 2 | ★ 预注册文件必须在，且主终点是 `fused@20`（不是向量路）。 |

### `tests/test_gate_baseline_whitelist.py`（6 个符号）

> 门禁基线里的"跳过节点"必须**真的还在**（2026-09-24，审计 B5）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_module_candidates` 函数 | 45 | 1 | junit 形态的点分名（**可能带类名**）⇒ 候选文件路径，由长到短。 |
| `_split_entry` 函数 | 55 | 2 | `tests.test_x.TestY::test_z\[p\]` → ('tests.test_x.TestY', 'test_z')。 |
| `alive_static` 函数 | 66 | 5 | **静态**判一条 nodeid 还在不在：模块文件在、**类段在**、且那个 def 在。 |
| `_session_keys` 函数 | 93 | 2 | 这一跑真收集到的节点，折成与基线同一形状（**补充**证据，不是主体判据）。 |
| `test_gate_baseline_skip_lists_have_no_vanished_nodes` 函数 | 112 | 1 | 两份名单里的每一条都必须还在。 |
| `test_the_alive_checker_itself_is_not_a_tautology` 函数 | 136 | 1 | 判据自己要被验：三种情形各断言一次（缺一不可，否则"什么都判在/判不在"看不出来）。 |

### `tests/test_gates_tracked_total.py`（7 个符号）

> 棘轮口径助手（`scripts/gates-tracked-total.py`）的判据：**只减掉未跟踪用例**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_junit` 函数 | 38 | 6 | 写一份最小 junit：`entries` = \[(classname, name), …\]。 |
| `_git_repo` 函数 | 46 | 5 | 临时 git 仓库（**受控**：tracked / untracked 各一个测试文件）。 |
| `test_only_untracked_tests_are_excluded` 函数 | 64 | 1 | **正向**：tracked 的照算、untracked 的那 2 条被扣掉。 |
| `test_the_reverse_the_naive_total_would_count_them` 函数 | 79 | 1 | **反向**：不扣减的口径（= 旧行为）会把 untracked 的算进去 ⇒ 两个数必须不同。 |
| `test_unmappable_names_are_not_subtracted` 函数 | 96 | 1 | **保守**：认不出文件的条目**不许扣**（宁可少扣，不可多扣）。 |
| `test_class_based_and_parametrised_names_map_to_the_file` 函数 | 111 | 1 | 类里的用例（junit 把类名塞进 classname）与参数化（`name\[param\]`）都要认得出。 |
| `test_helper_raises_instead_of_guessing_when_git_is_unavailable` 函数 | 122 | 1 | **调用方的安全网**：没有 git（如 `git archive` 提取树没有 `.git`）时**必须抛**，。 |

### `tests/test_glue_ocr_units.py`（30 个符号）

> glue_ocr_spaced_units 契约测试（OCR 循环轮次 12 根因修复配套）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestSplitValue` 类 | 12 | 1 | 2026-09-15 全库文本审计新增：'单字符数字 + 多字符数字' 劈开形态。 |
| `test_split_value_with_unit` 函数 | 16 | 1 | — |
| `test_split_value_micrometre` 函数 | 20 | 1 | — |
| `test_three_digit_split` 函数 | 24 | 1 | — |
| `test_no_unit_no_glue` 函数 | 27 | 1 | — |
| `test_idempotent_split_value` 函数 | 31 | 1 | — |
| `TestSubscriptResidue` 类 | 36 | 1 | 2026-09-15 残留修复：初版单字符集只有 ASCII → 下标型公式变量漏粘。 |
| `test_subscript_joins_letter` 函数 | 40 | 1 | — |
| `test_multi_subscript_variable` 函数 | 43 | 1 | — |
| `test_product_variables` 函数 | 46 | 1 | — |
| `test_superscript_on_unit` 函数 | 50 | 1 | — |
| `test_greek_variable` 函数 | 54 | 1 | — |
| `test_leading_subscript_not_merged_forward` 函数 | 57 | 1 | — |
| `test_no_cross_type_still` 函数 | 61 | 1 | — |
| `TestGlue` 类 | 66 | 1 | — |
| `test_decimal_digits` 函数 | 67 | 1 | — |
| `test_two_digit_group` 函数 | 71 | 1 | — |
| `test_letter_units_min` 函数 | 74 | 1 | — |
| `test_letter_units_mm` 函数 | 78 | 1 | — |
| `test_letter_units_ssu` 函数 | 83 | 1 | — |
| `test_type_boundary_no_cross_glue` 函数 | 86 | 1 | — |
| `test_superscript_joins_segment` 函数 | 90 | 1 | — |
| `test_normal_line_unchanged` 函数 | 95 | 1 | — |
| `test_chinese_unchanged` 函数 | 100 | 1 | — |
| `test_letter_pair_not_glued_unless_unit` 函数 | 103 | 1 | — |
| `test_digit_pair_glues` 函数 | 109 | 1 | — |
| `test_idempotent` 函数 | 112 | 7 | — |
| `test_multiline` 函数 | 117 | 1 | — |
| `test_empty_and_none` 函数 | 120 | 2 | — |
| `test_leading_dash_number` 函数 | 125 | 1 | — |

### `tests/test_golden_criterion.py`（16 个符号）

> 钉住评测器的命中判据：必须是 **(标准号, 条款号) 对**，不能只比条款号。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_same_clause_number_in_another_standard_is_not_a_hit` 函数 | 28 | 1 | **核心用例**：同一条款号、不同标准 ⇒ 必须判不中。 |
| `test_matching_pair_is_a_hit` 函数 | 35 | 1 | — |
| `test_any_expected_answer_counts` 函数 | 39 | 1 | 金标一条题可以有多个可接受答案，命中任一即可。 |
| `test_empty_expect_is_never_a_hit` 函数 | 45 | 1 | — |
| `test_order_of_returned_pairs_does_not_matter` 函数 | 49 | 1 | — |
| `test_standard_key_normalisation_equates_case_and_dashes` 函数 | 56 | 1 | — |
| `test_key_matches_standard_no_with_trailing_chinese` 函数 | 62 | 1 | 真库 4 篇 `standard_no` 尾部带中文 ⇒ 判据必须允许"键是前缀部分"。 |
| `test_key_does_not_match_a_longer_number_that_merely_ends_with_it` 函数 | 73 | 1 | **核心反例**：裸「包含」过头——`2033-2008` 是 `GBT12033-2008` 的子串。 |
| `test_empty_key_never_matches` 函数 | 88 | 1 | — |
| `test_row_filter_helper_is_boundary_based_not_bare_containment` 函数 | 105 | 1 | **打在行筛函数上**（第四轮复核的"残余 1"）。 |
| `test_known_standard_keys_drops_what_the_library_does_not_have` 函数 | 127 | 1 | **库里没有的标准号不许筛**（否则会把权重最高的通道 A 整条清空）。 |
| `test_unknown_standard_in_query_behaves_exactly_like_no_standard` 函数 | 138 | 1 | **打在调用点上**：删掉引擎里那道守卫，本用例会红。 |
| `test_row_filter_actually_scopes_to_the_named_standard` 函数 | 175 | 1 | **行筛**本身也要有覆盖（第三轮复核的变异 C 盲区）。 |
| `test_regex_finds_real_standard_numbers` 函数 | 233 | 1 | — |
| `test_regex_does_not_treat_clause_numbers_or_years_or_doc_numbers_as_standards` 函数 | 238 | 1 | 条款号 / 年份 / 文号 / 表号 / 日期区间都不许被当成标准号。 |
| `test_regex_alone_is_not_the_defence_for_lookalike_tokens` 函数 | 245 | 1 | **诚实登记**：`FY2021-2022` 这种"字母+4位数字+连字符+4位数字"**形态上确实像**标准号，。 |

### `tests/test_golden_gate.py`（5 个符号）

> Golden Set CI 门禁（Task 10.1，红线 v2 #6）：任何检索/核验改动不得回退。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_baseline_tracked_by_git` 函数 | 26 | 2 | 基线是否被 git 跟踪。 |
| `current` 函数 | 42 | 111 | — |
| `test_golden_gate_baseline_present` 函数 | 64 | 2 | 门禁前置：基线必须存在（**不得**由本测试自行重建）。 |
| `test_golden_gate_no_regression` 函数 | 87 | 2 | — |
| `test_golden_gate_minimums` 函数 | 105 | 1 | 硬底线：核心指标不得低于可接受线（防集体塌方式缓慢劣化）。 |

### `tests/test_golden_set.py`（2 个符号）

> T11 Golden Set：标准问答（GB30871 真实库）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_qa_retrieval_hits_golden` 函数 | 23 | 1 | 对真实库做检索命中基准（库含 GB30871 时启用）。 |
| `test_golden_qa_api_structure` 函数 | 42 | 1 | 问答 API 结构基准（不依赖真实库内容）。 |

### `tests/test_govcn_archive.py`（9 个符号）

> govcn_announce.archive_pdf 真实下载测试（2026-08-26，P2-②）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `MockBytesTransport` 类 | 14 | 4 | — |
| `__init__` 函数 | 15 | 135 | — |
| `fetch` 函数 | 22 | 1027 | — |
| `fetch_bytes` 函数 | 25 | 9 | — |
| `announce` 函数 | 31 | 186 | — |
| `_hit` 函数 | 38 | 25 | — |
| `test_archive_downloads_real_pdf` 函数 | 43 | 1 | — |
| `test_archive_falls_back_placeholder_on_bad_content` 函数 | 54 | 1 | — |
| `test_archive_falls_back_placeholder_without_url` 函数 | 63 | 1 | — |

### `tests/test_govqa_label_review.py`（29 个符号）

> gov-qa 标签复核包的回归判据（spec 005 T501 收口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `summary` 函数 | 43 | 181 | — |
| `fact_rows` 函数 | 49 | 13 | — |
| `lang_rows` 函数 | 54 | 9 | — |
| `Test产物存在且规模对` 类 | 58 | 0 | — |
| `test_四份产物都在` 函数 | 59 | 0 | — |
| `test_两半条数相同且与源一致` 函数 | 63 | 0 | — |
| `test_与源_CSV_条数一致` 函数 | 66 | 0 | — |
| `test_两半的_qid_集合相同` 函数 | 74 | 0 | — |
| `test_qid_不重复` 函数 | 77 | 0 | — |
| `Test两半必须分开` 类 | 82 | 0 | ⚠ 这是本特性的核心判据 —— 语言半拿到标签就退化成一半。 |
| `test_语言半不含_label_字段` 函数 | 85 | 0 | — |
| `test_语言半字段恰好是_qid_与_question` 函数 | 90 | 0 | — |
| `test_事实半含_label_与_label_source` 函数 | 94 | 0 | — |
| `test_语言半的_md_条目区不出现_现标字样` 函数 | 98 | 0 | — |
| `test_事实半的_md_每条都有现标` 函数 | 103 | 0 | — |
| `Test标注为_AI_判定而不是人工确认` 类 | 109 | 0 | ⚠ NOT-DOING 第 23 条的硬约束。 |
| `test_事实半标注了_AI_判定` 函数 | 112 | 0 | — |
| `test_语言半标注了_AI_判定` 函数 | 117 | 0 | — |
| `test_摘要的_kind_是_AI_判定` 函数 | 122 | 0 | — |
| `test_摘要声明了规格原文没改` 函数 | 126 | 0 | — |
| `test_不声称已满足规格` 函数 | 130 | 0 | 产物里**不许**把"已满足 FR-004/SC-003"当成**结论**说出来。 |
| `Test不声称准确率` 类 | 147 | 0 | T501 的完成判据是"复核包就绪"，不是"准确率已知"。 |
| `test_摘要的_accuracy_是_null` 函数 | 150 | 0 | — |
| `test_产物里不出现具体准确率数字` 函数 | 155 | 0 | — |
| `Test标签口径` 类 | 161 | 0 | — |
| `test_摘要的标签全集是_11_类` 函数 | 162 | 0 | — |
| `test_摘要的标签分布合计等于条数` 函数 | 165 | 0 | — |
| `test_摘要的_label_source_分布合计等于条数` 函数 | 168 | 0 | — |
| `test_事实半的标签都在全集内` 函数 | 171 | 0 | — |

### `tests/test_head_unit_fragment_gate.py`（16 个符号）

> 闸门 5：数值片段不得冒充条款头（2026-09-15，收敛循环第 9 轮根因）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestValueFragmentRejected` 类 | 18 | 1 | — |
| `_rej` 函数 | 19 | 8 | — |
| `test_unit_slash_unit` 函数 | 22 | 1 | — |
| `test_unit_with_cjk_punct` 函数 | 25 | 1 | — |
| `test_compound_unit_slash` 函数 | 28 | 1 | — |
| `test_inequality_expression` 函数 | 31 | 1 | — |
| `test_unit_times_cjk` 函数 | 34 | 1 | — |
| `test_unit_space_cjk` 函数 | 37 | 1 | — |
| `test_conc_mmol` 函数 | 40 | 1 | — |
| `test_value_only_line` 函数 | 43 | 1 | — |
| `TestReverseControls` 类 | 47 | 2 | 反向对照：合法条款头不得被误拒。 |
| `test_english_abbrev_title_kept` 函数 | 50 | 1 | — |
| `test_latin_started_title_kept` 函数 | 54 | 1 | — |
| `test_type_label_kept` 函数 | 59 | 1 | — |
| `test_cjk_title_kept` 函数 | 63 | 1 | — |
| `test_tabular_rest_still_rejected` 函数 | 67 | 1 | — |

### `tests/test_index_guard.py`（20 个符号）

> 索引页护栏契约测试（2026-09-15，GB/T 1008-2008 154 组重复号根因修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fake` 类 | 17 | 23 | — |
| `__init__` 函数 | 18 | 135 | — |
| `TestLeaderRun` 类 | 22 | 1 | — |
| `test_zeros_run` 函数 | 23 | 1 | — |
| `test_dots_run` 函数 | 26 | 1 | — |
| `test_short_not_leader` 函数 | 30 | 1 | — |
| `test_number_with_other_digits_not_leader` 函数 | 34 | 1 | — |
| `test_text_not_leader` 函数 | 38 | 1 | — |
| `test_stripped` 函数 | 42 | 1 | — |
| `TestOrderingOnBareNumber` 类 | 46 | 1 | 序性判据的**现**契约（2026-09-15 收敛循环首轮修正）。 |
| `test_same_parent_backward_rejected` 函数 | 57 | 1 | — |
| `test_duplicate_rejected` 函数 | 62 | 1 | — |
| `test_cross_parent_backward_accepted` 函数 | 65 | 1 | — |
| `test_body_progression_accepted` 函数 | 71 | 1 | — |
| `test_no_history_accepted` 函数 | 76 | 1 | — |
| `_blocks` 函数 | 80 | 4 | triples: \[(页号, 文本)\] → fitz 风格 blocks。 |
| `TestIntegration` 类 | 89 | 4 | — |
| `test_index_rows_not_clauses` 函数 | 90 | 2 | — |
| `test_bare_number_with_title_still_clause` 函数 | 102 | 1 | — |
| `test_leader_content_not_lost` 函数 | 112 | 1 | — |

### `tests/test_jev_cn_baseline.py`（5 个符号）

> **中文域准确率基线**：目标里"用项目自己的样本持续盯"的那一条。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_rows` 函数 | 27 | 33 | — |
| `test_cn_baseline_file_is_self_consistent` 函数 | 36 | 1 | **硬断言**：基线文件自洽（20 条 / 三档合法 / 每条三���分数都在 / 模型名钉版本）。 |
| `test_cn_baseline_covers_implicit_compliance` 函数 | 54 | 1 | 基线必须**覆盖 8 条隐性合规**（官方蓝本里最值钱的一档：词表看不见的那些）。 |
| `test_live_checker_exists_and_is_not_wired_into_judgments` 函数 | 72 | 1 | 真机对照脚本必须在（它是"持续盯"的载体），且**不得**被 pytest 当判据调用。 |
| `test_scores_in_plausible_range` 函数 | 99 | 1 | 概率类分数必须在 0~1（**severity 例外**：它是档位下标 0..档数−1）。 |

### `tests/test_jev_guard.py`（26 个符号）

> 合规护栏（jev_guard）回归用例：**2026-09-24 真机实测的 20 条中文样本**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_breaker` 函数 | 46 | 1 | 熔断状态是**模块级全局**（生产就该如此）⇒ 每个用例前后各清一次，。 |
| `_fake_scores` 函数 | 65 | 2 | 按**实测过的分数**回放，让判据在没有网络时也能验"阈值切在哪"。 |
| `fake_jev` 函数 | 103 | 12 | — |
| `test_guard_triggers_on_all_ten_measured_hits` 函数 | 112 | 1 | 该触发的 10 条**一条不漏**（含 8 条隐性合规——词表对它们 1/8）。 |
| `test_guard_silent_on_all_ten_technical_messages` 函数 | 122 | 1 | **不该触发的 10 条技术话一条都不许"触发"**（词表瘦身前 9/9 误触发）。 |
| `test_guard_three_technical_ones_land_in_review` 函数 | 136 | 1 | 实测的三条**中间档**：不静默、不触发——这正是"review 阈值"存在的理由。 |
| `test_guard_review_band_does_not_trigger` 函数 | 148 | 1 | 中间档：分数落在 review 与 action 之间 ⇒ review，**不**触发。 |
| `test_guard_severity_escalates_review_to_trigger` 函数 | 159 | 1 | 严重度越线 ⇒ 把 review 升级成触发（官方护栏蓝本的 severity 通道）。 |
| `test_guard_degrades_to_none_when_jev_unavailable` 函数 | 170 | 1 | **Jev 挂 ⇒ 返回 None（调用方退回词表）**，绝不让合规护航整体失效。 |
| `test_guard_degrades_when_key_missing` 函数 | 179 | 1 | 没配 Key ⇒ 直接 None（不联网、不报错）。 |
| `test_guard_rejects_malformed_answer` 函数 | 185 | 1 | 响应不合契约（缺 noul / 类型不对）⇒ 当不可用，**不猜**。 |
| `test_guard_questions_all_have_criteria` 函数 | 193 | 1 | **每道 Noul 都必须带 criteria**（官方硬要求。 |
| `test_client_pins_model_version` 函数 | 204 | 1 | **模型名钉死版本**，不用会漂移的别名（官方：调过阈值就别用别名）。 |
| `_resp` 函数 | 235 | 2 | — |
| `_patch_post` 函数 | 247 | 10 | — |
| `test_client_rejects_bad_values` 函数 | 254 | 1 | **坏值不许当判定**（独立复核 MED-2：`True` / `1.1` / 模型别名都曾被当合法）。 |
| `test_client_score_range_is_levels_not_unit_interval` 函数 | 274 | 1 | ⚠ **Score 不是 0~1**（2026-09-24 真机踩到：我的校验把三个字段一起按 0~1 判，。 |
| `test_client_score_range_unknown_scale_does_not_reject` 函数 | 302 | 1 | **量表档数拿不到时，不判 `score` 的值域**（独立复核 2026-09-24 MED 抓到的假严）。 |
| `test_client_rejects_bad_confidence` 函数 | 335 | 1 | Choice 的 `confidence` 必须在 0~1（`jev_ingest` 的 clear/review 门控靠它）。 |
| `test_breaker_reopens_after_cooldown` 函数 | 347 | 1 | **冷却一过、下一次失败会重新开熔断**（独立复核 MED-1 实测的洞：。 |
| `test_every_egress_is_audited` 函数 | 375 | 1 | **每一次外发都审计**（独立复核 MED-6：原先只有成功路径登记 ⇒ HTTP 503 那次查不到）。 |
| `test_audit_failure_does_not_break_decision` 函数 | 412 | 1 | 审计写失败**不反噬**判断结果（审计比判断重要，但不能让外部服务把护栏带崩）。 |
| `test_compliance_guard_endpoint_contract` 函数 | 423 | 1 | 端点契约（独立复核 MED-5：禁掉 `if verdict is None` 那支，26 条测试仍全绿 ⇒ 没钉住）。 |
| `test_change_signals_endpoint_contract` 函数 | 448 | 1 | `/laws/change-signals` 的契约（2026-09-24 真机核查时补的）。 |
| `test_compliance_guard_is_heavy_path` 函数 | 476 | 1 | 2s 外网 ⇒ 吃重活令牌（MED-3。 |
| `test_client_breaker_trips_after_repeated_failures` 函数 | 485 | 1 | 连续失败到阈值 ⇒ 熔断，后续**不再发请求**（省掉每条消息一次超时）。 |

### `tests/test_jev_ingest.py`（9 个符号）

> 公告入库"Jev 管清"回归用例（2026-09-24 真机实测分数回放，零联网零花费）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fake_jev` 函数 | 62 | 12 | — |
| `test_ingest_judges_all_samples` 函数 | 78 | 1 | 13 条逐条判对：clear 只给"够确信是行政事务"的，灰区与规范一律 keep。 |
| `test_ingest_never_clears_change_signal` 函数 | 89 | 1 | 变更信号**永远不清**——哪怕 choice 判成 admin、confidence 也很高。 |
| `test_ingest_low_confidence_admin_stays_keep` 函数 | 103 | 1 | **不够确信 ⇒ 留着**（官方分类范式：报更粗的标签，而不是丢掉）。 |
| `test_ingest_degrades_to_none_when_unavailable` 函数 | 115 | 1 | Jev 挂 ⇒ `None`（调用方按规则原样处理，绝不因为外部服务挂了就误清库）。 |
| `test_ingest_rejects_malformed` 函数 | 124 | 1 | 响应不合契约 ⇒ None（不猜）。 |
| `test_ingest_asks_both_questions_in_one_call` 函数 | 137 | 1 | **一次调用问两题**（官方 parallel_questions：打包更便宜更快）。 |
| `test_triage_pending_is_read_only_and_buckets` 函数 | 163 | 1 | `triage_pending`：只读分档——清/灰/留三个桶 + 每条带判据（choice/confidence）。 |
| `test_rule_passes_through_several_admin_documents` 函数 | 226 | 1 | **已证事实的登记用例**：规则（强线索词优先）会漏放这几条行政事务。 |

### `tests/test_kb_folder_api.py`（35 个符号）

> ``/api/v1/kb/*`` 接口用例（KB-FOLDER-PLAN 第 2 步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_new` 函数 | 30 | 51 | — |
| `test_list_top_level_order_is_the_hand_set_order` 函数 | 39 | 1 | **顶层实际顺序**必须是 标准 → 法律法规 → 公司制度 → 待分类（不只比 sort 值）。 |
| `test_list_empty_folder_gives_empty_array_not_error` 函数 | 49 | 1 | — |
| `test_list_unknown_folder_is_404` 函数 | 58 | 1 | — |
| `test_list_subfolders_sorted_by_sort_then_pinyin` 函数 | 65 | 1 | 同级排序 = (sort, 拼音, 名)：``A 综合`` 按拼音是 a…，必须排在 ``安全`` 前。 |
| `test_list_pagination_boundary` 函数 | 81 | 1 | — |
| `test_subfolder_deep_file_count` 函数 | 102 | 1 | — |
| `test_items_empty_and_pagination` 函数 | 119 | 1 | — |
| `test_items_unknown_folder_is_404` 函数 | 137 | 1 | — |
| `test_create_folder_under_parent_and_errors` 函数 | 145 | 1 | — |
| `test_rename_and_conflict` 函数 | 169 | 1 | — |
| `test_move_folder_from_to` 函数 | 187 | 1 | — |
| `test_move_a_two_places_folder_leaves_the_other_place_alone` 函数 | 200 | 1 | **第 2 步修准的那处语义**：同时挂在两处的目录，挪一处**不再**把另一处带走。 |
| `test_move_from_a_copy_to_the_top_really_lands_at_the_top` 函数 | 234 | 1 | ④ ``to_parent_id=null`` ⇒ **真的挪到顶层**（复核 2026-09-21 打回的假成功）。 |
| `test_move_from_a_place_that_does_not_hold_it_is_409` 函数 | 267 | 1 | — |
| `test_move_rejects_own_subtree` 函数 | 276 | 1 | — |
| `test_copy_folder_shares_members` 函数 | 293 | 1 | — |
| `test_copy_into_own_subtree_is_422` 函数 | 311 | 1 | — |
| `test_delete_empty_folder_directly` 函数 | 322 | 1 | — |
| `test_delete_nonempty_without_mode_is_409` 函数 | 332 | 1 | — |
| `test_delete_top_level_reparent_rejected_when_nonempty` 函数 | 352 | 1 | — |
| `test_delete_purge_keeps_files_present_elsewhere` 函数 | 370 | 1 | — |
| `test_delete_preview_numbers` 函数 | 394 | 1 | — |
| `test_delete_unknown_folder_is_404` 函数 | 425 | 1 | — |
| `test_members_add_is_idempotent` 函数 | 433 | 1 | — |
| `test_members_add_errors` 函数 | 446 | 1 | — |
| `test_members_remove_move_copy` 函数 | 466 | 1 | — |
| `test_inbox_lists_unfiled_with_suggestion_only_from_existing` 函数 | 499 | 1 | **只匹配现有目录，绝不自行新建**：真形状的树里命中 ⇒ 给**正确的那个**目录。 |
| `test_inbox_suggestion_is_null_when_the_tree_has_no_such_folder` 函数 | 529 | 1 | 反向用例：树里**没有**对应的目录 ⇒ **必须** None，不许瞎指一个（哪怕「标准」在）。 |
| `test_inbox_confirm_accept_existing_new` 函数 | 541 | 1 | — |
| `test_inbox_confirm_errors_are_atomic` 函数 | 574 | 1 | 整批全成或全败：中间一条非法 ⇒ 前面的也不许落。 |
| `test_scope_resolve_union_and_deeper` 函数 | 608 | 1 | — |
| `test_scope_resolve_unknown_is_404_not_empty` 函数 | 630 | 1 | ⚠ 绝不静默返回空范围（空范围会让"在此范围内提问"悄悄变成全库提问）。 |
| `test_all_kb_endpoints_require_token` 函数 | 641 | 1 | — |
| `test_folder_effect_deep_counts` 函数 | 656 | 1 | 批D2 判据（2026-09-22）：目录行的**效力分色灯**数据 —— `effect_deep` 按子树聚合。 |

### `tests/test_kb_scope_retrieval.py`（20 个符号）

> 第 6 步「按目录范围提问」：**检索层**的范围过滤（六条通道）+ 答案层的范围契约。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_own_data_dir` 函数 | 39 | 5 | 本模块私有的临时数据目录（跑完即弃。 |
| `_offline_embedder` 函数 | 107 | 4 | 向量引擎强制离线（与 `test_ks_answer` 同一手法）：不加载模型、不去下模型。 |
| `_clause` 函数 | 114 | 38 | — |
| `scope_db` 函数 | 127 | 14 | 两篇文档：`in_doc`（**范围内**）与 `out_doc`（**范围外**），各带六条通道要用的条款。 |
| `_ids` 函数 | 185 | 19 | — |
| `test_answer_is_findable_only_inside_the_scope` 函数 | 191 | 1 | 范围 = 范围内那篇 ⇒ 命中。 |
| `test_unrestricted_search_still_sees_both` 函数 | 201 | 1 | 反向哨兵：不给范围（`doc_ids=None`）时**两篇都能查到** —— 证明上一条不是"检索坏了"。 |
| `test_scope_filter_is_in_retrieval_not_post_filter` 函数 | 208 | 2 | **核心判据**：范围过滤必须发生在**检索层**。 |
| `test_every_channel_is_restricted` 函数 | 240 | 1 | 六条召回通道**逐条**验证：范围外的那篇在任何一条通道上都进不来。 |
| `test_vec_channel_is_restricted_without_the_model` 函数 | 262 | 1 | **向量通道**也要被堵住 —— 直接塞假向量，模型离线也能验。 |
| `test_vec_scope_holds_with_more_than_one_document` 函数 | 369 | 1 | **范围里有 ≥2 篇文档**时，向量通道也必须整体下推（spec 003 · FR-003）。 |
| `test_empty_scope_returns_nothing_never_the_whole_kb` 函数 | 436 | 1 | `doc_ids=\[\]` = "范围内一篇都没有" ⇒ **一条都不返回**（绝不退化成全库）。 |
| `kb_folders` 函数 | 449 | 10 | 知识库目录：顶层「甲」挂着 in_doc，顶层「乙」挂着 out_doc（返回两个 id）。 |
| `test_answer_scope_is_echoed_and_restricts_retrieval` 函数 | 459 | 2 | `ks_answer.answer(kb_folder_ids=\[甲\])`：检索被限定（范围外那篇的证据进不来）+ 范围如实回显。 |
| `test_answer_still_answers_when_out_of_scope_hits_saturate_topk` 函数 | 479 | 2 | **"在取回后筛"必红的那一条**（`top_k` 被范围外命中吃光的情形）。 |
| `test_answer_rejects_unknown_folder_instead_of_falling_back` 函数 | 512 | 1 | 目录不存在 ⇒ **报错**（`KbScopeNotFound`），绝不静默当成"没给范围"全库检索。 |
| `test_answer_with_empty_doc_scope_does_not_search` 函数 | 523 | 1 | 空范围（目录存在但里面一篇没有）⇒ **不检索**、如实说"范围内没有"，且**不调 LLM 拿全库编答案**。 |
| `test_bookmark_folder_and_kb_scope_are_two_different_things` 函数 | 544 | 1 | 两种"夹"不混：`folder_id`（收藏夹）**不动检索**（只后置过滤证据），`kb_folder_ids` 才限定检索。 |
| `test_api_returns_404_for_unknown_kb_folder` 函数 | 574 | 1 | 端点级：`POST /api/v1/ks/answer` 带不存在的目录 ⇒ **404**（不是 200 + 空答案）。 |
| `test_two_endpoints_agree_on_too_many_folders` 函数 | 586 | 1 | **同一条件两个端点必须给同一个状态码**（复核 LOW-3 打回）。 |

### `tests/test_ks_answer.py`（38 个符号）

> P1a 取证答案 ks_answer 单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_isolate_and_offline` 函数 | 48 | 3 | module 级私有临时库：只在本模块运行期间生效，结束后还原。 |
| `_offline_engines` 函数 | 74 | 1 | — |
| `_clause` 函数 | 113 | 38 | — |
| `_seed_db` 函数 | 124 | 4 | 初始化临时库并插入四份文档的条款（clause_fts 由 insert_clauses 自动填充）。 |
| `_seeded` 函数 | 171 | 1 | — |
| `_fake_stream` 函数 | 191 | 2 | — |
| `_patch_llm` 函数 | 198 | 16 | — |
| `_ev` 函数 | 207 | 39 | — |
| `test_filter_effective_drops_non_effective_and_keeps_effective` 函数 | 222 | 1 | — |
| `test_reference_clause_never_reaches_the_basis_list` 函数 | 232 | 1 | **征求意见稿（`reference`）绝不能当依据**（业主 2026-09-24：那种只能"仅参考"）。 |
| `test_dedupe_by_revision_id_and_on_pairs` 函数 | 246 | 1 | — |
| `test_cap_enforces_upper_bound_8` 函数 | 258 | 1 | — |
| `test_tier_three_states` 函数 | 266 | 1 | — |
| `test_is_substantive` 函数 | 276 | 1 | — |
| `test_clause_public_evidence_has_spec_fields_and_no_underscore` 函数 | 283 | 1 | — |
| `test_parse_llm_answer_json_with_citation` 函数 | 302 | 1 | — |
| `test_parse_llm_answer_code_fence_and_bare_text_fallback` 函数 | 311 | 1 | — |
| `test_parse_llm_answer_out_of_range_index` 函数 | 323 | 1 | — |
| `test_answer_direct_tier_returns_full_struct` 函数 | 333 | 1 | — |
| `test_answer_effective_exclusive_and_upcoming_note` 函数 | 357 | 1 | 跨版本 5.2.1（现行2022/即将2025/已废止2018）→ 只保留现行，notes 说明即将生效。 |
| `test_answer_synthesis_tier` 函数 | 372 | 1 | — |
| `test_answer_reference_tier_and_verification_marks` 函数 | 382 | 1 | — |
| `test_answer_verification_flags_unsupported_clause` 函数 | 393 | 1 | — |
| `test_answer_degrades_gracefully_when_llm_unavailable` 函数 | 402 | 1 | — |
| `test_build_messages_includes_system_and_c_marks` 函数 | 413 | 1 | — |
| `test_answer_rejects_empty_query` 函数 | 422 | 1 | — |
| `_enable_bookmarks` 函数 | 431 | 9 | 把 user_data.bookmarked_clause_keys 钉成给定集合（不碰真实收藏表）。 |
| `_break_bookmarks` 函数 | 437 | 2 | — |
| `test_answer_marks_every_evidence_item_with_bookmarked` 函数 | 444 | 1 | 逐条透出 bookmarked（宿主与提示词据此判断"范围过滤是否真的生效"）。 |
| `test_answer_bookmarks_only_filters_and_says_so` 函数 | 459 | 1 | bookmarks_only=True 且收藏集可用 → 只返回收藏条款，并在 notes 如实说明。 |
| `test_answer_bookmarks_only_with_empty_collection_returns_nothing` 函数 | 471 | 1 | — |
| `test_answer_bookmarks_only_zero_hits_is_not_a_query_failure` 函数 | 483 | 1 | 收藏集查询成功、但**检索本身 0 命中** → 必须仍然声明"已限定"，绝不能输出。 |
| `test_answer_marks_bookmarked_unknown_when_collection_returns_none` 函数 | 498 | 1 | 查询函数返回 None（而非抛错）同样表示"未知"，不得当成空收藏集。 |
| `test_answer_bookmarks_only_filters_before_the_evidence_cap` 函数 | 510 | 1 | 上限**只在收藏集内**生效（verifier 六轮 P1）：先 `_cap` 再过滤时，收藏集条款。 |
| `test_answer_bookmarks_only_widens_the_candidate_pool` 函数 | 524 | 1 | 仅收藏时检索候选池被放大（默认 k=8 时收藏条款几乎进不了候选）。 |
| `test_answer_bookmarks_only_zero_hits_note_does_not_blame_the_collection` 函数 | 543 | 1 | 空结果时的措辞：不得断言"收藏集里没有相关条款"（可能只是没被检索到）。 |
| `test_answer_marks_bookmarked_unknown_when_collection_query_fails` 函数 | 557 | 1 | 收藏集查询失败：**不得**把"查不到"当成 False（那会让模型误报"过滤未生效"），。 |
| `test_answer_without_bookmarks_only_still_flags` 函数 | 570 | 1 | 未开仅收藏：仍透出真值（不写 notes 的范围声明）。 |

### `tests/test_ks_answer_bbox.py`（30 个符号）

> spec 009 的引擎侧判据（**红箭头第①环**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_FakeRow` 类 | 25 | 2 | sqlite3.Row 支持按列名取值。 |
| `_FakeCursor` 类 | 29 | 2 | — |
| `__init__` 函数 | 30 | 135 | — |
| `fetchall` 函数 | 33 | 291 | — |
| `_FakeConn` 类 | 37 | 2 | — |
| `__init__` 函数 | 38 | 135 | — |
| `execute` 函数 | 42 | 1645 | — |
| `fake_db` 函数 | 48 | 37 | 把 get_db_connection 换成受控连接。 |
| `_row` 函数 | 60 | 112 | — |
| `test_attach_bboxes_fills_bbox_and_page` 函数 | 67 | 1 | — |
| `test_attach_bboxes_prefers_page_start` 函数 | 78 | 1 | — |
| `test_attach_bboxes_falls_back_to_first_when_page_start_missing` 函数 | 89 | 1 | — |
| `test_attach_bboxes_skips_when_no_span_on_page_start` 函数 | 99 | 1 | `page_start=5` 但该条款的 span 只在第 9 页 ⇒ **留空**，不许退化到 spans\[0\]。 |
| `test_attach_bboxes_uses_page_start_span_when_cross_page` 函数 | 114 | 1 | 跨页条款：只要 `page_start` 那一页**有** span，就取它（不取 sort_order 第一个）。 |
| `test_attach_bboxes_leaves_absent_when_no_span` 函数 | 129 | 1 | — |
| `test_attach_bboxes_never_writes_zero_placeholder` 函数 | 137 | 1 | **假证据**防线：0 兜底会让前端在页面左上角画一个错箭头。 |
| `test_attach_bboxes_skips_malformed_bbox` 函数 | 145 | 1 | — |
| `test_attach_bboxes_rejects_non_finite` 函数 | 157 | 1 | — |
| `test_attach_bboxes_survives_db_error` 函数 | 168 | 1 | — |
| `test_attach_bboxes_survives_missing_connection` 函数 | 181 | 1 | — |
| `test_attach_bboxes_noop_on_empty` 函数 | 196 | 1 | — |
| `test_attach_bboxes_noop_when_no_revs` 函数 | 202 | 1 | — |
| `test_attach_bboxes_handles_multiple_revs` 函数 | 208 | 1 | — |
| `test_attach_bboxes_rejects_degenerate_box` 函数 | 227 | 1 | **退化框必须拒收** —— 真库实测 `GB 17681-2024` 全篇 370/370 条都是这种碎片。 |
| `test_attach_bboxes_rejects_thin_box` 函数 | 241 | 1 | 只满足一个维度也不许 —— 宽 200pt 但高 0.5pt 的"一条线"同样看不见。 |
| `test_attach_bboxes_rejects_narrow_box` 函数 | 249 | 1 | 高 13pt（正常）但宽 2pt 的窄条也不许（画出来是一根看不见的竖线）。 |
| `test_attach_bboxes_accepts_normal_line` 函数 | 257 | 1 | **正常正文行必须通过**（防"阈值太松把正常行也拒了"）—— 用真库实测的中位量级。 |
| `test_degenerate_thresholds_are_the_documented_values` 函数 | 266 | 1 | 阈值是**规范值**（有实测依据），不许随手改。 |
| `test_attach_bboxes_skips_degenerate_but_keeps_normal` 函数 | 283 | 1 | 同一条款有多个 span 时：退化框被跳过，**正常框仍被采用**（不是整条丢弃）。 |
| `test_attach_bboxes_all_degenerate_leaves_empty` 函数 | 295 | 1 | 该条款的 span **全是**退化框 ⇒ 留空（不许拿任意一个凑数）。 |

### `tests/test_label_gap_not_jev.py`（5 个符号）

> **B3-⑦「6797 篇打层级标签」为什么不由 Jev 填**（2026-09-24 量测结论，附事实）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ro` 函数 | 65 | 3 | — |
| `_require_real_db` 函数 | 69 | 3 | **真库不在就显式 skip，不许静默通过**（独立复核 2026-09-24 指出 `if not exists(): return`。 |
| `test_facts_still_hold` 函数 | 84 | 1 | 量测结论的前提是这些事实。 |
| `test_change_signal_column_exists_after_migration` 函数 | 120 | 1 | `change_signal` 列：真库已 ALTER 补上（2026-09-24），全新库由 schema.sql 直接带。 |
| `test_decision_recorded` 函数 | 135 | 1 | 本文件是**决策留痕**（不是待办）：B3-⑦ 不由 Jev 填，理由=单一真源/既有机制已有归属。 |

### `tests/test_latex_array.py`（11 个符号）

> LaTeX ``array`` 环境泄漏修复契约测试（2026-09-15，收敛循环第 5 轮根因）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestArrayEnvironment` 类 | 16 | 1 | — |
| `test_full_env_no_residue` 函数 | 17 | 1 | — |
| `test_row_break_becomes_separator` 函数 | 29 | 1 | — |
| `test_bare_leak_from_real_artifact` 函数 | 37 | 1 | — |
| `test_column_spec_variants` 函数 | 46 | 1 | — |
| `test_thin_space_commands` 函数 | 52 | 1 | — |
| `TestArrayReverseControls` 类 | 58 | 1 | 反向对照：不得误伤合法内容。 |
| `test_word_containing_array_untouched` 函数 | 61 | 1 | — |
| `test_variable_product_preserved` 函数 | 67 | 1 | — |
| `test_normal_digits_preserved` 函数 | 70 | 1 | — |
| `test_frac_still_converted` 函数 | 73 | 1 | — |

### `tests/test_latex_frac_tag.py`（15 个符号）

> latex_to_text 的 

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestFrac` 类 | 12 | 1 | — |
| `test_simple_frac` 函数 | 13 | 1 | — |
| `test_frac_with_subscripts` 函数 | 16 | 1 | — |
| `test_expression_operands_parenthesized` 函数 | 23 | 1 | — |
| `test_nested_frac` 函数 | 29 | 1 | — |
| `test_chained_fracs` 函数 | 33 | 1 | — |
| `TestTag` 类 | 39 | 1 | — |
| `test_tag_number_extracted_with_close_paren` 函数 | 40 | 1 | — |
| `test_empty_tag_removed` 函数 | 44 | 1 | — |
| `test_tag_plain_number` 函数 | 47 | 1 | — |
| `test_no_tag_unchanged` 函数 | 50 | 1 | — |
| `TestNoRegression` 类 | 54 | 3 | — |
| `test_plain_symbol_mapping_still_works` 函数 | 55 | 1 | — |
| `test_subsup_outside_frac` 函数 | 59 | 1 | — |
| `test_real_10401_formula` 函数 | 63 | 2 | — |

### `tests/test_latex_spacing.py`（20 个符号）

> latex_to_text 逐字符空格归并契约测试（2026-09-15 全库公式审计根因修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestDigitRuns` 类 | 18 | 1 | — |
| `test_three_single_digits_merged` 函数 | 19 | 1 | — |
| `test_two_digit_run_merged_with_unit_anchor` 函数 | 22 | 1 | — |
| `test_plain_number_run` 函数 | 25 | 1 | — |
| `test_two_tokens_protected` 函数 | 28 | 1 | — |
| `TestLetterRuns` 类 | 33 | 1 | — |
| `test_three_letter_run_merged` 函数 | 34 | 1 | — |
| `test_kpa_merged` 函数 | 37 | 1 | — |
| `test_variable_product_protected` 函数 | 40 | 1 | — |
| `test_two_letter_unit_not_merged` 函数 | 44 | 1 | — |
| `TestAttachments` 类 | 49 | 1 | — |
| `test_superscript_attaches` 函数 | 50 | 1 | — |
| `test_micro_prefix_attaches` 函数 | 53 | 1 | — |
| `test_subscript_chain_attaches` 函数 | 56 | 1 | — |
| `test_percent_escape` 函数 | 59 | 1 | — |
| `TestNoRegression` 类 | 63 | 3 | — |
| `test_symbol_mapping_intact` 函数 | 64 | 1 | — |
| `test_frac_still_semantic` 函数 | 69 | 1 | — |
| `test_real_10401_formula` 函数 | 73 | 2 | — |
| `test_idempotent` 函数 | 80 | 7 | — |

### `tests/test_law_catalog.py`（16 个符号）

> 法规总目录测试（LAW_CATALOG_ONDEMAND_PLAN.md 任务 1）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_rows` 函数 | 19 | 11 | — |
| `_patch_flk` 函数 | 36 | 6 | patch flk_client.enum_data/search。 |
| `_patch_aggregate` 函数 | 56 | 6 | — |
| `_by_cat` 函数 | 69 | 3 | 库内 `law_catalog` 按分类计数（**与生产同一句 SQL**，用来取"基线"）。 |
| `test_extract_category_leaves_skips_placeholder_and_dedups` 函数 | 89 | 1 | — |
| `test_sxx_label_mapping` 函数 | 98 | 1 | — |
| `test_parse_aggregate_tolerant_shapes` 函数 | 107 | 1 | — |
| `test_refresh_full_crawl_dedup_and_result` 函数 | 119 | 2 | — |
| `test_reconcile_mismatch_records_warning` 函数 | 184 | 1 | — |
| `test_single_category_failure_degrades_to_warning` 函数 | 195 | 1 | — |
| `test_aggregate_fetch_failure_is_silent_and_catalog_usable` 函数 | 221 | 1 | aggregateData 端点已核实不返回 JSON（SPA HTML/405）。 |
| `test_query_pagination_filters_and_order` 函数 | 240 | 1 | — |
| `test_manifest_incremental_skip_and_sxx_change` 函数 | 284 | 1 | — |
| `test_progress_events_shape` 函数 | 317 | 1 | — |
| `test_并发ensure_catalog_schema在缺列旧表上不抛异常` 函数 | 330 | 0 | §10.87（独立复核 b16 的 INFO-3）：32 线程并发建表/补列，不许抛 `duplicate column name`。 |
| `test_稳态下ensure_catalog_schema不拿写锁` 函数 | 392 | 0 | §10.87：表/列/索引都齐（**稳态**）时，它必须走**只读快路径**，不碰写锁。 |

### `tests/test_law_catalog_refresh.py`（18 个符号）

> 法规目录定时刷新测试（spec 006 T013）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_set_cfg` 函数 | 23 | 10 | — |
| `cfg` 函数 | 36 | 59 | 清掉刷新相关配置，用例自己设（避免会话级共享库里的残留）。 |
| `_fake_refresh` 函数 | 45 | 8 | — |
| `test_refresh_days_default_is_one` 函数 | 55 | 1 | 未设 ⇒ 缺省 1 天。 |
| `test_refresh_days_values` 函数 | 62 | 1 | — |
| `test_due_when_never_refreshed` 函数 | 69 | 1 | 从没刷过 ⇒ 视为到期，触发刷新并写 last_refresh_at。 |
| `test_skips_when_not_due` 函数 | 80 | 1 | 刚刷过（1 天内）⇒ 跳过，且**不碰网络**。 |
| `test_due_again_after_period` 函数 | 90 | 1 | 超过周期 ⇒ 再次触发。 |
| `test_disabled_when_zero` 函数 | 100 | 1 | 周期 ≤0 ⇒ 关闭，不触发。 |
| `test_naive_last_refresh_treated_as_utc` 函数 | 110 | 1 | 历史值无时区 ⇒ 按 UTC 解释，不得抛 TypeError。 |
| `test_failure_does_not_stamp_last_refresh` 函数 | 119 | 1 | ★ 刷新失败 MUST NOT 写 last_refresh_at —— 否则一整个周期不再重试。 |
| `test_start_is_idempotent_and_stop_cleans` 函数 | 131 | 1 | start 两次只起一个线程。 |
| `test_loop_survives_exception` 函数 | 143 | 1 | 循环体抛异常不得终止线程（后台线程必须存活）。 |
| `test_restart_after_stop_runs_again` 函数 | 162 | 1 | stop 后能再 start，且新线程**真的在跑**（每次新 Event，旧线程不得复活）。 |
| `test_stop_timeout_does_not_lie_or_double_start` 函数 | 190 | 1 | ★ join 超时后：`is_running()` 不得假阴，`start` 不得再起第二个线程。 |
| `test_stop_returns_true_when_clean` 函数 | 230 | 1 | 正常退出 ⇒ stop 返回 True（与超时分支可区分）。 |
| `test_run_starts_and_stops_law_refresh` 函数 | 242 | 1 | ★ 生产启动点 `server.run()` 必须真的**调用** start / stop 刷新线程。 |
| `test_refresh_module_is_not_the_dead_scheduler` 函数 | 264 | 1 | ★ 反向断言：刷新线程**不依赖**那个死调度器（它的 start() 无人调用）。 |

### `tests/test_law_enum_split.py`（14 个符号）

> 「一、二、三、」式法规切分契约测试（2026-10-07 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestEnumSplit` 类 | 56 | 1 | — |
| `test_splits_enum_numbering` 函数 | 57 | 1 | — |
| `test_body_kept` 函数 | 61 | 1 | — |
| `test_subitem_not_split` 函数 | 66 | 2 | 「（一）（二）」是子项，不是条款 —— 必须留在所属条目正文里。 |
| `test_enum_number_not_matched_mid_line` 函数 | 72 | 1 | 行内出现的「一、」不算条款头（要求行首）。 |
| `test_law_text_finds_nothing_here` 函数 | 77 | 1 | — |
| `test_article_doc_unaffected_by_enum_splitter` 函数 | 81 | 1 | — |
| `test_halfwidth_paren_form` 函数 | 87 | 1 | 半角 `(一)` 做**顶层编号**：老规范（《保护海底电缆规定》）如此。 |
| `test_markdown_heading_prefix` 函数 | 92 | 1 | 编号在 markdown 标题里：`## 二、爱卫会的组织`（《爱国卫生运动委员会…规定》如此）。 |
| `test_fullwidth_paren_still_not_split` 函数 | 97 | 1 | **全角 `（一）` 是子项**，不许被当成条款（否则一条法规会被切碎）。 |
| `TestEndToEnd` 类 | 103 | 3 | — |
| `test_enum_doc_ingests` 函数 | 104 | 2 | 端到端：这种文件**必须能入库**，而不是回退成"未识别到条文"。 |
| `test_article_doc_still_uses_article_splitter` 函数 | 110 | 1 | — |
| `test_unparseable_still_errors` 函数 | 115 | 1 | 两种编号都没有 ⇒ 仍须**如实报错**，不许静默当一条。 |

### `tests/test_law_history.py`（12 个符号）

> 法规历次版本链测试（spec 006 US2 / T032）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_detail_with` 函数 | 18 | 7 | 造一个 detail 替身（history 只读 raw\['lsyg'\]）。 |
| `test_history_sorted_desc` 函数 | 27 | 1 | 多版本 ⇒ 按 gbrq 降序。 |
| `test_history_null_gbrq_sinks` 函数 | 38 | 1 | ★ gbrq 实测可为 null ⇒ 必须沉底且不抛错。 |
| `test_history_highlight_normalised` 函数 | 49 | 1 | 官方字段名是 highLight（驼峰）⇒ 输出归一成 highlight。 |
| `test_history_empty_when_no_lsyg` 函数 | 58 | 1 | 没有 lsyg ⇒ 空列表（这是"确实没有历次版本"，不是失败）。 |
| `test_history_tolerates_non_list` 函数 | 65 | 1 | lsyg 不是 list（接口结构变了）⇒ 返空，不炸。 |
| `test_history_skips_non_dict_items` 函数 | 71 | 1 | 链上混进非 dict 项 ⇒ 跳过该项，其余照常。 |
| `test_history_raises_on_network_failure` 函数 | 79 | 1 | ★ 网络失败 MUST 抛异常 —— 绝不用 \[\] 冒充"无版本"（spec FR-007）。 |
| `test_history_endpoint_missing_bbbs` 函数 | 90 | 1 | — |
| `test_history_endpoint_ok` 函数 | 98 | 1 | — |
| `test_history_endpoint_502_on_failure` 函数 | 110 | 1 | ★ 官方不可达 ⇒ 502，**不是** 200 + 空链（否则前端无法区分）。 |
| `test_history_endpoint_empty_is_200` 函数 | 123 | 1 | 确实无历次版本 ⇒ 200 + 空链（与 502 明确区分）。 |

### `tests/test_law_source.py`（14 个符号）

> 官方来源管线测试（docs/LAW-SOURCE-PLAN.md P1）：

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_whitelist_accepts_official_hosts` 函数 | 15 | 1 | — |
| `test_whitelist_rejects_third_party` 函数 | 22 | 1 | — |
| `test_magic_checks` 函数 | 30 | 1 | — |
| `test_flk_search_payload` 函数 | 46 | 1 | — |
| `test_govcn_parse_rows` 函数 | 78 | 1 | — |
| `test_govcn_fetch_detail_extracts_official_download` 函数 | 92 | 1 | — |
| `test_convert_probe_never_raises` 函数 | 128 | 2 | — |
| `test_find_libreoffice_honours_KS_SOFFICE` 函数 | 143 | 1 | `$KS_SOFFICE` 显式覆盖（2026-10-18 加）—— 便携场景要能指定**包内**的 LibreOffice。 |
| `test_pdf_completeness_detects_truncation` 函数 | 171 | 1 | LibreOffice 截断检测：docx 文本量远大于 PDF → 判截断（False）。 |
| `test_flk_level_map` 函数 | 202 | 1 | — |
| `test_law_source_dir_sanitizes` 函数 | 211 | 1 | — |
| `test_build_docx_from_html` 函数 | 218 | 1 | — |
| `test_find_by_source_roundtrip` 函数 | 233 | 1 | — |
| `test_check_law_updates_status_change` 函数 | 259 | 1 | — |

### `tests/test_law_source_api.py`（10 个符号）

> 官方法规来源 API 测试（LAW-SOURCE-PLAN P2）：sources / search / ingest（mock 网络）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_law_sources_lists_whitelist` 函数 | 5 | 1 | — |
| `test_law_search_flk` 函数 | 13 | 1 | — |
| `test_law_search_govcn` 函数 | 33 | 1 | — |
| `test_law_search_rejects_third_party` 函数 | 50 | 1 | 白名单外域被拒（403），不静默放行。 |
| `test_law_ingest_flk` 函数 | 65 | 1 | — |
| `test_law_ingest_requires_bbbs_or_url` 函数 | 84 | 1 | — |
| `test_law_catalog_query_shape_and_filter` 函数 | 94 | 1 | GET /api/v1/laws/catalog 返回分页形状。 |
| `test_law_catalog_refresh_mocked` 函数 | 120 | 1 | POST /api/v1/laws/catalog/refresh 透传 refresh_catalog 结果（mock 网络）。 |
| `test_law_verify_passthrough` 函数 | 135 | 1 | GET /api/v1/laws/verify?bbbs= 透传 verify_law 载荷（mock 网络）。 |
| `test_law_verify_missing_bbbs` 函数 | 152 | 1 | — |

### `tests/test_law_source_http_antibot.py`（16 个符号）

> law_source HTTP 层的反爬挑战处理测试（spec 006）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Resp` 类 | 23 | 20 | 最小响应替身：只要 status_code / headers / text / json()。 |
| `__init__` 函数 | 26 | 135 | — |
| `raise_for_status` 函数 | 31 | 24 | — |
| `json` 函数 | 35 | 3581 | — |
| `test_looks_like_antibot_detects_challenge` 函数 | 40 | 1 | — |
| `test_looks_like_antibot_ignores_json` 函数 | 44 | 1 | Content-Type 是 json 就不该被当挑战（即使正文里恰好含那串字）。 |
| `test_looks_like_antibot_ignores_normal_html` 函数 | 50 | 1 | 非 JSON 声明的响应一律视为被挡（站点有时返回别的 HTML 页，无特征串）。 |
| `test_looks_like_antibot_empty_body_is_blocked` 函数 | 56 | 1 | 空正文也算没拿到数据 ⇒ 走重试，而不是当场 JSONDecodeError。 |
| `test_json_or_challenge_raises_antibot` 函数 | 61 | 1 | — |
| `test_json_or_challenge_passes_json` 函数 | 66 | 1 | — |
| `test_fetch_json_retries_through_challenge` 函数 | 71 | 1 | ★ 挑战页之后成功 ⇒ fetch_json 应当**穿过挑战**拿到 JSON（不是直接失败）。 |
| `test_fetch_json_uses_long_backoff_for_challenge` 函数 | 89 | 1 | ★ 挑战页必须走**秒级**退避（亚秒退避对它无效）——断言 sleep 参数。 |
| `test_fetch_json_still_raises_on_real_error` 函数 | 105 | 1 | 真 5xx 不该被当挑战处理（保持既有语义：抛 RuntimeError）。 |
| `test_mixed_failure_still_uses_long_backoff` 函数 | 114 | 1 | ★ 混合失败序列（挑战、挑战、连接错）**必须仍走长退避轮**。 |
| `test_pure_network_error_does_not_use_antibot_backoff` 函数 | 143 | 1 | ★ 反向：全程都不是挑战（纯连接错）⇒ **不该**拖进分钟级长退避。 |
| `test_whitelist_rejection_not_retried` 函数 | 155 | 1 | 非白名单域必须**当场拒绝**、不重试（策略拒绝语义透传）。 |

### `tests/test_law_split_quality.py`（15 个符号）

> 法规切分质量契约测试（2026-10-07 两处修正）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestFrontMatterStripped` 类 | 50 | 1 | — |
| `test_front_matter_not_in_body` 函数 | 51 | 2 | — |
| `test_first_chapter_heading_kept_as_context` 函数 | 57 | 1 | **首个**章标题要留（那才是上下文该带的东西）。 |
| `test_later_heading_not_in_first_clause` 函数 | 69 | 1 | 前一条不该带上**后面**章节的标题。 |
| `test_strip_returns_text_after_marker` 函数 | 74 | 1 | — |
| `test_strip_without_marker_falls_back` 函数 | 78 | 1 | — |
| `TestLineStartSplit` 类 | 83 | 1 | — |
| `test_reference_does_not_split` 函数 | 84 | 2 | **本修正的核心**：句子中间的「第X条」是引用，不是新条款。 |
| `test_reference_stays_in_body` 函数 | 90 | 1 | — |
| `test_line_start_clause_splits` 函数 | 95 | 1 | — |
| `test_bold_form_still_splits` 函数 | 99 | 1 | — |
| `TestEnumStillWorks` 类 | 104 | 1 | — |
| `test_enum_doc_unaffected` 函数 | 105 | 1 | 修正只动「第X条」这条路，枚举那条路不受影响。 |
| `TestFallbackAlsoStripsFrontMatter` 类 | 112 | 1 | 兜底分支（整篇作一条）**也必须**剥文件头。 |
| `test_fallback_clause_has_no_front_matter` 函数 | 130 | 1 | — |

### `tests/test_law_text_edges.py`（5 个符号）

> `ingest_law_text` 的证据边**归属**契约（2026-10-09 真缺陷的回归判据）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `two_refer_doc` 函数 | 51 | 7 | — |
| `_edges_of` 函数 | 57 | 4 | — |
| `test_edge_source_is_the_referring_clause` 函数 | 70 | 1 | 边的 source 必须是**引用别人的那一条**，不是"文档的最后一条"。 |
| `test_last_clause_has_no_outgoing_edges` 函数 | 77 | 1 | 反向：被引用的**最后一条**不该凭空多出任何出边（缺陷的签名就是它）。 |
| `test_edge_count_matches_reference_sites` 函数 | 84 | 1 | 边的**条数**也要对：该文档共 2 处引用 ⇒ 恰好 2 条边（不多不少）。 |

### `tests/test_law_verify.py`（23 个符号）

> 「点开即核验」verify_law 单测（任务 2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `FakeDetail` 类 | 20 | 18 | FlkDetail 形状的最小替身（raw 默认非空 = 详情正常返回）。 |
| `__init__` 函数 | 23 | 135 | — |
| `vcache` 函数 | 33 | 54 | 每用例隔离：清内存缓存 + 删落盘文件（conftest 已把 data_dir 重定向到临时目录）。 |
| `_mock_detail` 函数 | 45 | 18 | 安装 flk_client.detail 替身并统计调用（verify.py 运行期属性访问，补丁必生效）。 |
| `_ttl_of` 函数 | 58 | 4 | — |
| `_expire` 函数 | 63 | 3 | 白盒把条目拨到已过期（避免真实 sleep 24h）。 |
| `test_effective_mapping_payload_contract` 函数 | 72 | 1 | — |
| `test_status_mapping_strict` 函数 | 93 | 1 | — |
| `test_sxx_string_form_normalized` 函数 | 100 | 1 | 官方偶发字符串形态（"3"）也应归一映射，不误判为未知。 |
| `test_graded_ttl_by_status` 函数 | 118 | 1 | — |
| `test_unmarked_uses_12h_ttl` 函数 | 124 | 1 | 详情非空但官方未标注时效 → unmarked，不从可访问性推断。 |
| `test_not_found_negative_cache_60s` 函数 | 134 | 1 | 详情 data 为空 → 查无。 |
| `test_minimal_mock_without_raw_treated_as_not_found` 函数 | 151 | 1 | 无 raw 属性且无 sxx 的最小对象 → 无可判定信息，按查无处理（不猜）。 |
| `test_exception_degrades_to_unverified_never_cached` 函数 | 168 | 1 | — |
| `test_timeout_degrades_within_budget` 函数 | 181 | 1 | 上游卡死 > 单请求超时 → 截断降级 unverified（总耗时受预算约束）。 |
| `test_unknown_sxx_warns_and_does_not_guess` 函数 | 200 | 1 | 未知 sxx → unverified + WARN 告警，不猜测、不缓存。 |
| `test_bool_sxx_is_not_mapped` 函数 | 210 | 1 | bool 是 int 子类：True/False 不得误判成 1/0 映射。 |
| `test_empty_bbbs_no_network` 函数 | 217 | 1 | — |
| `test_cache_hit_second_call_skips_network` 函数 | 229 | 1 | — |
| `test_ttl_expiry_refetches` 函数 | 240 | 1 | — |
| `test_disk_persistence_warm_restart` 函数 | 249 | 1 | 落盘写穿 + 进程重启模拟（清内存）：温启动后仍命中缓存、不打接口。 |
| `test_corrupt_cache_file_is_cold_start` 函数 | 262 | 1 | — |
| `test_singleflight_merges_concurrent_calls` 函数 | 272 | 1 | 同 bbbs 并发 N 路 → 上游只被打一次，全部拿到同一结论。 |

### `tests/test_layout_fidelity.py`（17 个符号）

> 排版还原 B3/B5 管线测试：页界入库 + 行级 bbox + 行级 span。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_middle_multiline` 函数 | 17 | 3 | 合成 3 页 middle.json（行框齐全）：条款 5.2.1 跨页 0→1，5.2.2 在页 1，。 |
| `_built` 函数 | 70 | 9 | load → split → build 一次，供多个用例复用。 |
| `test_load_middle_items_line_boxes_aligned` 函数 | 80 | 1 | B5 底座：MidItem.line_boxes 与 text 行序列一一对齐（行界=line）。 |
| `test_split_rows_page_attribution` 函数 | 91 | 1 | B3 采集：SplitClause.rows 逐行携带 0-based 页号（跨页拼接行页号正确）。 |
| `test_build_page_breaks_run_start` 函数 | 104 | 1 | B3 页界编码：run-start \[\[行号, PDF页\], ...\]，行号 = content_text 0-based。 |
| `test_build_row_pipeline_furniture_strip` 函数 | 120 | 2 | 家具剥离在 rows 上做：整行标准号丢弃后行号收缩，页界编码仍与。 |
| `test_build_line_spans_full_no_cap` 函数 | 131 | 1 | B5：行级 span 全量入库（退役 \[:8\] 封顶），bbox=折行行框、sort_order。 |
| `test_build_spans_fallback_when_line_boxes_missing` 函数 | 148 | 1 | 行框整体缺失（旧 middle.json 无 line.bbox）→ 回退块级 span（宁粗不高灭），。 |
| `test_build_truncation_rowwise` 函数 | 162 | 1 | \[:4000\] 截断在 rows 上做：整行入账、末行可截半，截断后行号/页界不漂移。 |
| `test_build_uncaptioned_table_identity` 函数 | 183 | 1 | B4：无题注表格条款（绑定全失配落单）不被 <4 守卫整表丢弃，。 |
| `test_storage_roundtrip_page_breaks` 函数 | 201 | 1 | 存储面：insert_clauses 写 page_breaks JSON → fetch_full_clause 读回一致。 |
| `test_api_page_break_divider` 函数 | 235 | 1 | 渲染面：page_breaks 非空 → 页号切换处插 <div class="page-break"。 |
| `_mk_middle_with_image` 函数 | 287 | 2 | 合成含 image 块的 middle.json：页 0 首块 = 无题注插图（current None →。 |
| `test_pipeline_image_load_bind_figure_html` 函数 | 326 | 1 | C2：image 块进 MidItem。 |
| `test_locate_middle_figure_fallback` 函数 | 353 | 1 | C3：/figure 文字层锚定失败 → middle.json image_caption 匹配图号取。 |
| `test_locate_middle_figure_bare_image_path` 函数 | 392 | 1 | 24276 实测回归：image_path 裸文件名（无 images/ 前缀）、物理文件在。 |
| `test_strip_keeps_caption_lines_with_table_tokens` 函数 | 421 | 1 | 24276 实测回归：图题行 token（不带通风口/有效散热面积/1,25）与系数表。 |

### `tests/test_ledger_chain.py`（58 个符号）

> 台账驱动的降级链测试（`src/core/update/channels/ledger_chain.py`，§11.0 R6c）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_row` 函数 | 22 | 112 | — |
| `_clean_channel_table` 函数 | 29 | 3 | 真库用例要一张干净的表（测试库 data_dir 是**会话级**的，模块之间会互相污染——。 |
| `Test过滤` 类 | 37 | 0 | — |
| `test_人工停用不进链` 函数 | 38 | 0 | — |
| `test_known_broken_不进链` 函数 | 42 | 0 | — |
| `test_探针说_down_也不过滤` 函数 | 46 | 0 | R6a 实测：down 的 13 条里混着瞬时/WAF/我方 TLS 指纹 ⇒ 按一次探针踢渠道会让链抖动。 |
| `test_台账里没有的成员保留_fail_open` 函数 | 52 | 0 | 没 seed 的库不该让巡检失去整条链。 |
| `test_顺序就是名单顺序` 函数 | 57 | 0 | — |
| `Test成员资格不是wired` 类 | 62 | 0 | — |
| `test_wired_不等于兜底成员` 函数 | 63 | 0 | 核心回归：`wiring='wired'` 的专用渠道**不许**被自动塞进兜底链。 |
| `test_候选要被报出来而不是被悄悄提升` 函数 | 69 | 0 | — |
| `Test一致性报告` 类 | 77 | 0 | — |
| `test_名单里有代码里没有的适配器要报出来且不进链` 函数 | 78 | 0 | 独立复核 b29 抓到的欠账：`known` 参数原先承诺过却没用（`_ = known` 是死代码）。 |
| `test_名单重复成员去重且要告警` 函数 | 91 | 0 | 复核 b29-fix 的 a：不去重的话链里会出现两次同名（巡检白跑一遍）而没人知道。 |
| `test_名单成员在台账里没有行要提一句` 函数 | 99 | 0 | 复核 b29-fix 的 b：按设计 fail-open 保留，但不能一个字都不说。 |
| `test_写法差异也要被挡住` 函数 | 109 | 0 | 复核 b29-fix 的 c：`BROKEN` / `'0'` 这类写法差异过去会让"已知失效"照旧留在链里。 |
| `test_这些不算停用` 函数 | 119 | 0 | `None`（没写）/`True`/`1`/`'1'` 都不是"停用"——别把缺失读成人工意图。 |
| `test_生成器名单也照收` 函数 | 124 | 0 | 复核 b29-fix2 的坑：生成器只能消费一次，而 report 要遍历它好几遍 ⇒ 入口先固化。 |
| `test_重复成员的报告不重复列` 函数 | 132 | 0 | — |
| `test_台账说wired但代码里没有适配器要报出来` 函数 | 139 | 0 | — |
| `test_非适配器渠道不参与缺失判定` 函数 | 145 | 0 | `seed:law-cn:*` / `tool:*` 本来就不是适配器名，不该被报成"台账/代码不一致"。 |
| `test_wired_且探针_down_要报出来` 函数 | 153 | 0 | — |
| `Test真库` 类 | 161 | 0 | 一条真库用例：缺省 roster（=今天的兜底链）在真库上应当**无差异**。 |
| `test_缺省名单下真库过滤后等于今天的链` 函数 | 164 | 0 | — |
| `test_真库报告里不含种子外的噪音` 函数 | 168 | 0 | — |
| `test_专用渠道在候选里而不在链里` 函数 | 175 | 0 | 前缀专用渠道（DB→dbba、行标→hbba）**不在泛查兜底链里**，所以是"可提升候选"。 |
| `test_ndls_已毕业进兜底链` 函数 | 189 | 0 | R6c-3b：`ndls` 从"可提升候选"变成"链上成员"，这条正面钉住它别再被挪走。 |
| `Test巡检真的按台账走` 类 | 197 | 0 | §11.0 R6h：把台账接进**巡检**（在这之前 `ledger_chain` 只被快照脚本用，巡检不读它）。 |
| `test_人工停用让巡检不再问它` 函数 | 204 | 0 | `enabled=0` ⇒ 该渠道**从巡检的链里消失**（不只是面板上显示停用）。 |
| `test_known_broken_让巡检不再问它` 函数 | 211 | 0 | — |
| `test_前缀首选也受台账管` 函数 | 215 | 0 | 前缀首选（HJ→`mee`）同样受过滤：人工停用它，HJ 号就退回泛查链。 |
| `test_没有台账行时不过滤也不读库` 函数 | 226 | 0 | `rows=None` ⇒ 原样返回 `select_chain`（**不读库、不 I/O**）。 |
| `test_台账缺该行则保留_fail_open` 函数 | 245 | 0 | 台账里**查不到**某成员 ⇒ 保留（fail-open）：没 seed 的库不该让巡检失去整条链。 |
| `test_不做加法_只做减法` 函数 | 250 | 0 | 台账 `wired` 但**不在** `select_chain` 里的渠道，不会因为这个函数进链。 |
| `Test号段加法` 类 | 262 | 0 | §11.0 R7（2026-09-19）：**号段→渠道**成为台账里可维护的事实，链按它做加法。 |
| `_seg` 函数 | 275 | 47 | — |
| `test_号段命中就多一根尾巴` 函数 | 279 | 0 | `mee` 声明 `GB` ⇒ GB 号在泛查链之后多问一根 `mee`（今天它一条 GB 号都到不了）。 |
| `test_只加尾巴_路由链顺序不动` 函数 | 285 | 0 | — |
| `test_号段不许把人工停用的渠道加回来` 函数 | 290 | 0 | **加法与过滤的正确交互**：`ndls` 被停用、但它也声明了 `GB` ⇒ 不许被加回链尾巴。 |
| `test_号段不命中就没尾巴` 函数 | 302 | 0 | — |
| `test_代码里没有的适配器不进链` 函数 | 306 | 0 | — |
| `test_已经在前缀首选里的渠道不会重复出现` 函数 | 313 | 0 | `HJ` 号本来就首选 `mee`，`mee` 又声明 `HJ` ⇒ 链里只出现一次（去重）。 |
| `test_rows_None_时也不做加法且不读库` 函数 | 319 | 0 | 没有台账行 ⇒ 既不过滤也不加法（fail-open 的同一条口径）。 |
| `test_号段匹配口径` 函数 | 340 | 0 | — |
| `test_号段顺序确定_同一库上可复现` 函数 | 346 | 0 | 尾巴顺序 = 台账顺序（`list_channels` 的 ORDER BY category,name）⇒ 链不抖。 |
| `Test号段报告` 类 | 357 | 0 | 号段的三类欠账必须**被算出来**（写错与没写的现场表现都是静默）。 |
| `_seg` 函数 | 360 | 47 | — |
| `test_死号段被点名` 函数 | 364 | 0 | 写了 `T/` 而真库里一个 T/ 号都没有 ⇒ 必须报出来（否则"渠道永不进链"没人知道）。 |
| `test_没给号表就说判不准_不假装没欠账` 函数 | 381 | 0 | **不给号表**（`\[\]`）⇒ `dead`/`gained` 一律不下结论，并在 `note` 里说清。 |
| `test_有适配器却到不了也没号段要列成待办` 函数 | 394 | 0 | 这就是 R6g 那 10 条的形状：有适配器、今天任何号都到不了、也没声明号段。 |
| `test_号段带来的号数按号去重` 函数 | 401 | 0 | 多个号段命中同一个号只算一次（否则"带来多少号"虚高）。 |
| `test_被排除的行不计入带来多少号` 函数 | 409 | 0 | 人工停用的渠道不该在"带来多少号"里贡献数字（那是虚高）。 |
| `Test号段形状校验` 类 | 416 | 0 | — |
| `test_非数组被拒` 函数 | 417 | 0 | — |
| `test_空项或非字符串被拒` 函数 | 422 | 0 | — |
| `test_归一_去空白_保序去重` 函数 | 426 | 0 | — |
| `test_None_表示清空` 函数 | 429 | 0 | — |
| `test_读路径容错_坏值给空元组而不是抛` 函数 | 432 | 0 | 库里的历史脏数据不许把巡检弄炸（写路径拒绝、读路径容错）。 |

### `tests/test_legal_status.py`（12 个符号）

> legal_status 到期翻转决议测试（2026-08-27）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_today` 函数 | 14 | 8 | — |
| `test_upcoming_past_date_flips_to_effective` 函数 | 18 | 1 | upcoming + 实施日期在昨天 → 翻成 effective。 |
| `test_upcoming_today_flips_to_effective` 函数 | 24 | 1 | upcoming + 实施日期就是今天 → 翻成 effective（今天起施行）。 |
| `test_upcoming_future_date_stays` 函数 | 29 | 1 | upcoming + 实施日期在未来 → 仍 upcoming。 |
| `test_upcoming_missing_date_stays` 函数 | 35 | 1 | upcoming + 缺实施日期 → 保持 upcoming（不猜）。 |
| `test_upcoming_malformed_date_stays` 函数 | 41 | 1 | upcoming + 非 YYYY-MM-DD → 保持 upcoming。 |
| `test_effective_untouched` 函数 | 47 | 1 | — |
| `test_effective_future_date_flips_to_upcoming` 函数 | 52 | 1 | effective + 实施日期在未来 → 即将实施（2026-08-29 反向翻转：入库从封面。 |
| `test_effective_today_stays_effective` 函数 | 60 | 1 | effective + 实施日期就是今天 → 现行（今天起施行）。 |
| `test_effective_malformed_date_stays` 函数 | 65 | 1 | effective + 非 YYYY-MM-DD → 保持（不猜）。 |
| `test_superseded_withdrawn_untouched` 函数 | 70 | 1 | — |
| `test_none_untouched` 函数 | 75 | 1 | — |

### `tests/test_legal_status_reference.py`（4 个符号）

> 效力档新增值 `reference`（**参考资料·仅参考**）的**库结构迁移**测试（开发史 §10.192）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_legacy_ddl` 函数 | 31 | 2 | 真 `schema.sql` **只把 doc_meta 的枚举退回四值**——其余一字不改。 |
| `_mk_doc` 函数 | 49 | 31 | — |
| `test_ref_migration_rebuilds_doc_meta` 函数 | 58 | 1 | 四值 ⇒ 五值：迁移前写不进、迁移后写得进。 |
| `test_ref_migration_leaves_other_enum_alone` 函数 | 123 | 1 | **不动** `update_change_event.current_legal_status`（四值）—— 它没有生产者要写 reference。 |

### `tests/test_llm_empty_retry.py`（6 个符号）

> 空返回自动重试 —— 判据（2026-10-19）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_patch_stream` 函数 | 33 | 4 | 把 `_stream_llm` 换成一串预设输出。 |
| `_patch_retrieve` 函数 | 49 | 4 | 检索固定返回一条证据，把 LLM 之外的因素全部钉死。 |
| `_FakeClause` 类 | 59 | 2 | — |
| `test_empty_then_good_retries_and_succeeds` 函数 | 94 | 1 | 第一次空、第二次有 ⇒ 用第二次结果，不标 llm_unavailable。 |
| `test_always_empty_degrades_honestly` 函数 | 111 | 1 | 一直空 ⇒ 诚实降级，且说明重试过。 |
| `test_llm_error_not_retried` 函数 | 126 | 1 | 配置类错误不重试 —— 否则 Key 错时会白等 max_attempts 倍。 |

### `tests/test_long_clause_tail_ruler.py`（8 个符号）

> P0·0.10 尺子（`eval/recall-funnel/exp-12-long-clause-tail/measure.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 30 | 125 | — |
| `test_head_tail_split_is_512_chars` 函数 | 42 | 2 | 按字符切在 512：短于 512 ⇒ tail 为空。 |
| `test_production_still_uses_the_512_char_cap` 函数 | 52 | 2 | ★ 契约锚：尺子的 512 必须**真的**对应生产代码里的截断点。 |
| `test_tail_only_excludes_head_and_title` 函数 | 64 | 2 | `tail_only` = tail 词 − head 词 − title 词（title 也在向量里，必须一起扣）。 |
| `test_token_drop_partition_adds_up` 函数 | 76 | 2 | ★ 两段账：`gain`（去掉代码上限能白捡）+ `residual`（模型窗口仍挡）= 总丢量。 |
| `test_token_drop_partition_never_negative` 函数 | 88 | 1 | 边界：head 自己就超窗口（实测 2/4000）⇒ gain 不能为负。 |
| `test_model_window_is_pinned_to_512` 函数 | 94 | 1 | ★ 第二道截断点（**模型窗口**）必须被钉住 —— 独立复核 P2-1 实测：。 |
| `test_model_window_matches_local_tokenizer_config` 函数 | 107 | 1 | 契约锚：本机若有 bge-small-zh 的 `tokenizer_config.json`，其 `model_max_length` 必须 == MODEL_WINDOW。 |

### `tests/test_loop2_driver.py`（7 个符号）

> Unit tests for the bounded loop orchestrator (driver_v2).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_fresh` 函数 | 19 | 6 | — |
| `test_consecutive_only_on_round1_pass` 函数 | 32 | 1 | — |
| `test_fail_and_blocked_reset_consecutive` 函数 | 43 | 1 | — |
| `test_three_strike_arms_and_solve_clears` 函数 | 56 | 1 | — |
| `test_converged_requires_5_round1_and_no_blocked` 函数 | 72 | 1 | — |
| `test_build_queue_dedups` 函数 | 82 | 1 | — |
| `test_seed_issues_populates_classes` 函数 | 94 | 1 | — |

### `tests/test_loop2_oracle.py`（12 个符号）

> Unit tests for the loop2 structural oracle (scoring + pure page-mapping helpers).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk` 函数 | 24 | 47 | Build a snapshot dict in the form loaded from snapshot.json (string keys).。 |
| `test_ratio_basic` 函数 | 48 | 1 | — |
| `test_parse_page_breaks_roundtrip` 函数 | 56 | 1 | — |
| `test_json_str_key_roundtrip_no_false_missing` 函数 | 63 | 1 | — |
| `test_missing_content_forces_fail` 函数 | 78 | 1 | — |
| `test_scan_na_non_blocking` 函数 | 89 | 1 | — |
| `test_pagmap_aligned_and_misaligned` 函数 | 100 | 1 | — |
| `test_table_text_included_in_preview` 函数 | 110 | 1 | — |
| `test_strip_html_and_orig_noise` 函数 | 121 | 1 | — |
| `test_object_expected_figures_missing` 函数 | 130 | 1 | — |
| `test_object_expected_figures_na_without_middle` 函数 | 149 | 1 | — |
| `test_mode_textlayer_vs_scan` 函数 | 161 | 1 | — |

### `tests/test_loop2_vlm.py`（5 个符号）

> Unit tests for the VLM candidate-difference checker (loop2 step 3).

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_images` 函数 | 21 | 4 | — |
| `test_both_images_sent_and_structured` 函数 | 29 | 1 | — |
| `test_retry_on_transient_error` 函数 | 53 | 1 | — |
| `test_no_key_degrades_not_raises` 函数 | 69 | 1 | — |
| `test_parse_json_tolerates_fences` 函数 | 77 | 1 | — |

### `tests/test_material_api.py`（66 个符号）

> 材料平面 API 测试（Phase A 第四步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_txt` 函数 | 25 | 28 | — |
| `project` 函数 | 31 | 575 | — |
| `TestAuthAndValidation` 类 | 38 | 1 | — |
| `test_requires_token` 函数 | 39 | 2 | — |
| `test_create_project_needs_name` 函数 | 43 | 1 | — |
| `test_authority_policy_must_be_object` 函数 | 49 | 1 | — |
| `test_unknown_project_is_404` 函数 | 55 | 2 | — |
| `test_bad_status_filter_is_422` 函数 | 62 | 1 | — |
| `test_tiers_endpoint_lists_all` 函数 | 68 | 2 | — |
| `TestEndToEnd` 类 | 74 | 3 | — |
| `test_scan_review_read_then_searchable` 函数 | 75 | 1 | 建项目 → 丢文件 → scan → 读切片 → 搜到。 |
| `test_inbox_lists_dropped_files` 函数 | 128 | 1 | — |
| `test_reject_removes_from_search` 函数 | 138 | 1 | — |
| `TestAxesAndLifecycle` 类 | 153 | 1 | — |
| `test_tier_change_is_用户可改_and_recorded` 函数 | 154 | 0 | — |
| `test_bad_tier_is_422` 函数 | 168 | 1 | — |
| `test_role_criterion_is_settable_and_searchable` 函数 | 180 | 1 | 公司制度例走 API：来源层级不高，但**是本任务的准则**。 |
| `test_bad_role_is_422` 函数 | 195 | 1 | — |
| `test_lifecycle_promote` 函数 | 205 | 2 | — |
| `test_delete_removes_material` 函数 | 218 | 1 | — |
| `site` 函数 | 237 | 207 | 极简本地站点：`/ok` 正常页、`/pdf` 二进制。 |
| `allow_local` 函数 | 272 | 34 | 把 SSRF 判据换成"公网"以便打本地站点（**生产代码里没有这个开关**）。 |
| `_collect` 函数 | 278 | 17 | — |
| `TestCollectEndpoint` 类 | 282 | 1 | — |
| `test_unknown_project_is_404` 函数 | 283 | 2 | — |
| `test_missing_or_blank_url_is_422` 函数 | 287 | 1 | — |
| `test_source_tier_is_refused_loudly_and_registers_nothing` 函数 | 294 | 1 | **采集者不得自 claim 可信度**（轴 A 只能由系统判据起或用户改）。 |
| `test_unknown_body_keys_are_refused_not_ignored` 函数 | 310 | 1 | **未知字段一律拒绝**（2026-09-17 复核 A 的 MEDIUM）。 |
| `test_ssrf_refusal_is_a_reason_not_an_error_code` 函数 | 324 | 1 | SSRF 拒绝对是**本次**抓取的结果，不是"你的请求写错了"⇒ 200 + 原因。 |
| `test_fetch_registers_pending_then_approval_makes_it_searchable` 函数 | 338 | 1 | 端到端：**采集 → 待评审 → 检索不到 → 批准 → 检索到**。 |
| `test_binary_response_is_refused_over_the_route` 函数 | 369 | 1 | "不是网页正文"在**路由层**也挡住了（两条判据：Content-Type 白名单 + 真实字节）。 |
| `test_mislabeled_binary_is_refused_by_real_bytes` 函数 | 380 | 1 | Content-Type 撒谎（说自己是 html）也挡得住——判据落在**真实字节**上。 |
| `test_route_does_not_offer_a_batch_entry` 函数 | 389 | 1 | **结构性约束**：不得存在批量采集入口（预算/频率上限未定，方案 §11.4）。 |
| `_list` 函数 | 403 | 8 | — |
| `track_l_docs` 函数 | 409 | 3 | 登记本类测试往**法条链**写的 doc_id，**测完删干净**（同 `test_material_track_l`）。 |
| `_collect_text_material` 函数 | 436 | 5 | 用**采集门**登记一份文本材料（走 `collect_text` 的公共入口，不经网络）。 |
| `TestApprovalTriggersTrackL` 类 | 446 | 1 | **批准 → Track L 自动跑**（业主裁定 J5："采到库内没有的法规标准，评审通过后自动入库"）。 |
| `test_standard_material_is_imported_on_approval` 函数 | 454 | 1 | — |
| `test_plain_material_is_skipped_on_approval` 函数 | 474 | 1 | — |
| `test_rejection_does_not_run_track_l` 函数 | 486 | 1 | 拒绝**不触发**：返回体里连 `track_l` 键都不该有（"没决策"与"决策=skip"是两回事）。 |
| `test_track_l_failure_is_reported_not_raised` 函数 | 496 | 1 | Track L 抛错**不改写评审结果**，但必须在 `data.track_l` 里如实报出来。 |
| `TestSlowEndpointsAreDeclaredSync` 类 | 517 | 6 | **结构性约束**：做同步重活的端点必须声明成 `def`（Starlette 才会丢进线程池）。 |
| `test_declared_sync` 函数 | 639 | 1 | 这条路径上**这个 HTTP 方法**的端点必须是 `def`（线程池），不能是 `async def`。 |
| `test_async端点必须在显式名单里` 函数 | 691 | 0 | **通则（§10.87）**：`/api/` 路由上的每条 `async def` 端点都必须在 `_ASYNC_ENDPOINTS`。 |
| `_unbounded_pool_calls` 函数 | 766 | 9 | 在一段端点源码里找出"把同步活丢进**无界**池"的写法（§10.93）。 |
| `test_端点上不许用_asyncio_to_thread` 函数 | 803 | 0 | **通则之三（§10.93）**：`/api/` 端点不许用 `asyncio.to_thread` / `run_in_executor`。 |
| `test_名单里的_async_端点要么量过要么写明不可量` 函数 | 886 | 0 | **量具接名单（第二层，§10.94）**：名单里的每条 async 端点，要么被**量**过，。 |
| `test_T1_零await的async端点必须是def` 函数 | 988 | 0 | **通则之一（§10.86，修复核 b15 的 MEDIUM-1）**：`async def` 且源码里**没有任何。 |
| `test_async_endpoints_that_only_read_body_are_not_heavy` 函数 | 1061 | 1 | **通则之三（T2）**：`async def` 端点若**唯一的 `await` 只是读 body**（或没有 await），。 |
| `test_名单第二关的判据_effective_real_await` 函数 | 1138 | 0 | §10.88：名单第二关的判据在**六种形状**上都必须判对（b17 的 MEDIUM-2 + MEDIUM-3）。 |
| `test_def端点返回StreamingResponse仍然真流式` 函数 | 1203 | 0 | §10.89（独立复核 b18 的 MEDIUM-1）：**`def` 端点也能真流式** —— 这是判据的前提。 |
| `test_内联递归的深度上限被唯一钉住` 函数 | 1294 | 0 | §10.90/§10.91（独立复核 b19 的 N4 + b20 的 N2）："深度上限 = 4" 必须被**唯一**钉住。 |
| `test_判据本体的边界样本` 函数 | 1339 | 0 | §10.86：两条判据的**边界形状**（b15 的 INFO-1 / INFO-3）。 |
| `test_nested_async_generators_without_await_are_rejected` 函数 | 1376 | 1 | **通则之二**：端点里嵌套的 `async def` **生成器**若**一个 `await` 都没有** ⇒ 红。 |
| `test_没有函数叠着两个_docstring` 函数 | 1416 | 0 | **结构判据**：一个函数/类体里不许**连着两个字符串常量语句**（b14 的 LOW-3）。 |
| `test_两条通则的判据走_AST_不会被注释骗` 函数 | 1448 | 0 | §10.85：判据本身也要验——**注释不是行为**（独立复核 b14 的 MEDIUM-2）。 |
| `test_嵌套生成器判据只数自己作用域` 函数 | 1489 | 0 | §10.86 自查：`yield`/`await` 必须只数**该函数自己作用域**里的。 |
| `test_module_has_no_async_endpoint` 函数 | 1553 | 1 | **文件级**闸门：这些模块注册的端点，**一个都不许是 `async def`**。 |
| `TestEndpointIndexMatchesReality` 类 | 1581 | 1 | 模块 docstring 的**端点索引**必须与真实注册的路由**逐条对齐**。 |
| `test_docstring_index_equals_registered_routes` 函数 | 1592 | 1 | — |
| `TestLocatorEndpoints` 类 | 1620 | 1 | 引用锚点稳定性的三个端点（方案 §12 未决第 5 条，§10.48）。 |
| `_ingest` 函数 | 1623 | 5 | — |
| `test_project_summary_and_single_health` 函数 | 1632 | 1 | ⚠ **不抓网**：材料直接用 `collect_text` 造（离线也要能验端点形状）。 |
| `test_old_material_shows_up_as_unknown_in_the_summary` 函数 | 1659 | 1 | 老材料（入库时没记指纹）在总览里算 **unknown** ——**不假装 ok**。 |
| `test_unknown_material_is_404` 函数 | 1673 | 1 | — |
| `test_reverify_reports_unavailable_without_a_source_file` 函数 | 1678 | 1 | **没有留存源文件** ⇒ `unavailable`（不是 match）——这条语义必须在端点上如实。 |

### `tests/test_material_authority.py`（42 个符号）

> 材料权威性纪律测试（Phase B 第一步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 21 | 575 | — |
| `_add` 函数 | 25 | 81 | — |
| `TestBehaviourTable` 类 | 37 | 1 | — |
| `test_every_tier_has_a_behaviour` 函数 | 38 | 1 | — |
| `test_t4_is_excluded_t3_needs_corroboration` 函数 | 41 | 1 | — |
| `TestRules` 类 | 48 | 1 | — |
| `test_t0_t1_t2_are_usable` 函数 | 49 | 1 | — |
| `test_single_source_t3_is_LEAD_ONLY` 函数 | 58 | 1 | **核心纪律**：一篇网络文章**不得**支撑结论。 |
| `test_two_independent_domains_promote_t3_to_corroborated` 函数 | 69 | 1 | — |
| `test_same_domain_twice_is_NOT_corroboration` 函数 | 83 | 1 | **最常见的假互证**：同一站点转载两篇，只有一个来源。 |
| `test_t4_never_usable_and_is_disclosed` 函数 | 93 | 1 | — |
| `test_t4_with_many_sources_still_excluded` 函数 | 103 | 1 | T4 **多源也不放行**——"不可回溯"是来源性质问题，不是数量问题。 |
| `test_criterion_is_listed_and_not_downgraded_by_tier` 函数 | 111 | 1 | 公司制度例（轴 B 独立于轴 A）：来源层级低，但**是本任务的准绳**。 |
| `test_criterion_t3_single_source_still_governs` 函数 | 122 | 1 | 用户把一份二手转述**指定为准绳**时，轴 B 优先——但标注仍说实话（T3）。 |
| `test_unapproved_material_never_reaches_assembly` 函数 | 132 | 1 | 评审硬门在检索层就已经挡住 ⇒ 装配层看不到未批准材料（这里再确认一次）。 |
| `test_no_hits_yields_honest_note` 函数 | 141 | 1 | — |
| `TestRendering` 类 | 147 | 1 | — |
| `test_render_carries_both_axes_and_a_locator` 函数 | 148 | 1 | — |
| `test_render_shows_declared_role_label` 函数 | 161 | 1 | 声明了轴 B 之后，渲染里出现的是「本任务准则」而不是「未声明效力」。 |
| `test_render_shows_lead_only_section_separately` 函数 | 171 | 1 | — |
| `test_render_includes_excluded_section` 函数 | 178 | 1 | — |
| `TestT4BeatsAxisB` 类 | 185 | 1 | **T4 优先于轴 B**（独立复核 2026-09-17 报的 MEDIUM）。 |
| `test_t4_declared_criterion_is_NOT_load_bearing` 函数 | 192 | 1 | — |
| `test_t4_criterion_is_visibly_marked_in_both_notes_and_text` 函数 | 202 | 1 | — |
| `test_t3_criterion_still_governs` 函数 | 214 | 1 | 轴 B 的**正常**用法不能被上一条误伤：T3 单一来源当准则仍然算准则。 |
| `TestCorroborationIsFalsifiable` 类 | 224 | 1 | **身份未知不能互证**（独立复核 2026-09-17 报的 MEDIUM）。 |
| `test_two_copies_without_any_source_identity_do_NOT_corroborate` 函数 | 232 | 1 | — |
| `test_url_provides_identity_so_two_domains_corroborate` 函数 | 243 | 1 | — |
| `test_url_identity_normalizes_scheme_www_and_case` 函数 | 253 | 1 | `A.COM` / `www.a.com` / `http://a.com` 是**同一个**来源（旧口径算 3 个）。 |
| `test_unknown_identity_does_not_drag_down_known_corroboration` 函数 | 263 | 1 | 混合场景：两个已知域名互证 ⇒ 那两条升为辅证。 |
| `TestSameStoryIsNotIndependentSources` 类 | 277 | 2 | **一稿多发不是多源互证**（2026-09-17 加近重复检测后钉住）。 |
| `test_identical_text_on_two_domains_is_ONE_source` 函数 | 284 | 1 | — |
| `test_copy_with_reworded_punctuation_is_still_ONE_source` 函数 | 295 | 1 | 只改标点/空白/全半角的"转载"仍是同一篇（归一化后相等）。 |
| `test_same_domain_two_articles_is_still_ONE_source` 函数 | 306 | 1 | 同一家媒体的两篇不同文章 = 一个来源（这是域名图的节点语义）。 |
| `test_syndicated_pair_plus_one_real_second_source` 函数 | 317 | 1 | `a.com` X + `b.com` 转载 X + `c.com` **另一篇** ⇒ 合并后是 **2** 个来源 ⇒ 可互证。 |
| `TestNoSingleScoreSorting` 类 | 331 | 1 | — |
| `test_module_exposes_no_tier_sorting_helper` 函数 | 332 | 1 | **两轴不可压成一个分数**：本模块不得提供"按层级/综合分排序材料"的函数。 |
| `test_usable_order_follows_groups_not_tiers` 函数 | 344 | 1 | **行为级**两轴护栏：承重集合的顺序按"组"（准则在前）而**不是**按层级。 |
| `TestCitationIndices` 类 | 366 | 1 | `\[\[m:i\]\]` 编号：模型的引用标记靠它，编号一漂移引用就全指错 ⇒ 钉死。 |
| `test_indices_are_contiguous_across_groups_in_group_order` 函数 | 369 | 1 | — |
| `test_render_marks_every_hit_with_its_index` 函数 | 386 | 1 | — |
| `test_index_matches_usable_hits_order` 函数 | 397 | 1 | `usable_hits()` 的返回顺序必须与编号一致（下游按它拼引用，不一致就错位）。 |

### `tests/test_material_collect.py`（43 个符号）

> 自采入口测试（`src/core/materials/collect.py`，Phase C 第一步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 21 | 575 | — |
| `_review_violations` 函数 | 31 | 5 | 在源码里找"能设置评审状态"的代码路径（AST，不看注释/docstring）。 |
| `TestAlwaysPendingAndEphemeral` 类 | 51 | 1 | — |
| `test_collected_material_is_pending` 函数 | 52 | 1 | — |
| `test_collected_material_never_enters_retrieval_before_review` 函数 | 59 | 1 | 硬门在采集路径上同样成立：未批准 → 搜不到。 |
| `test_default_lifecycle_is_ephemeral` 函数 | 66 | 1 | 业主裁定：其它资料默认**当前任务一次性**。 |
| `test_module_exposes_no_way_to_approve` 函数 | 72 | 1 | **结构性约束**：本模块不得提供任何能设置评审状态的**代码路径**。 |
| `test_the_structural_detector_itself_works` 函数 | 88 | 1 | **检测器的自测**：否则上面那条"结构性约束"可能是空转的。 |
| `TestSourceProvenance` 类 | 103 | 1 | — |
| `test_url_is_recorded_and_domain_extracted` 函数 | 104 | 1 | — |
| `test_no_url_means_unknown_identity` 函数 | 111 | 1 | 没有 url/domain ⇒ 身份未知 ⇒ 按 authority 的纪律**不能互证**。 |
| `test_collected_defaults_to_T3_not_trusted` 函数 | 118 | 1 | 不给层级时"网上找来的"从 T3 起——**默认不可信，靠证据升级**。 |
| `test_caller_can_set_a_higher_tier_with_evidence` 函数 | 124 | 1 | 调用方有证据时可以给更高层级（判据是"有没有证据"，不是"谁采的"）。 |
| `test_note_lands_in_tier_reason_for_the_reviewer` 函数 | 131 | 1 | — |
| `TestDeduplication` 类 | 138 | 1 | — |
| `test_identical_text_is_not_registered_twice` 函数 | 139 | 1 | — |
| `test_near_duplicate_is_registered_but_flagged` 函数 | 147 | 1 | 近似（改了标点）**仍然登记**，但标注 `near_duplicate_of` 给评审人看。 |
| `test_different_articles_are_not_flagged` 函数 | 162 | 1 | — |
| `TestTrackL` 类 | 172 | 1 | — |
| `test_standard_text_is_recognised_and_only_recorded` 函数 | 173 | 1 | 认出疑似标准正文 ⇒ 只**记录意图**，不在采集路径上入库（入库在评审通过之后）。 |
| `test_non_standard_text_is_other` 函数 | 193 | 1 | — |
| `test_caller_can_override_kind` 函数 | 199 | 1 | — |
| `TestLawRecognition` 类 | 206 | 3 | **法规识别**（2026-09-17，Phase C 第八步）：让 Track L 也覆盖法规。 |
| `test_law_text_is_recognized_with_name_and_clause_count` 函数 | 219 | 1 | — |
| `test_direct_recognizer_thresholds` 函数 | 232 | 1 | 四条证据都要齐：标题/法规名 + **从第一条起** + **立法句式** + 条数门槛。 |
| `test_a_single_clause_citation_is_not_a_law` 函数 | 253 | 1 | **零误伤方向**：正文里顺口引用一条"第X条"的文章不许被当成法规。 |
| `test_standard_number_wins_over_law_shape` 函数 | 262 | 1 | **优先级**：同时像标准与法规时，走**标准**那一支（标准号判据更精确）。 |
| `TestLawRecognitionFalsePositives` 类 | 288 | 1 | **误伤方向**：新闻 / 合同 / 判决书都不许被认成法规（复核 step-31~34 的 MEDIUM-HIGH）。 |
| `test_news_quoting_law_names_is_not_a_law` 函数 | 297 | 1 | 新闻：标题正常、正文引了《…》+ 几条法条 ⇒ **不许**认成法规。 |
| `test_contract_is_not_a_law` 函数 | 310 | 1 | 合同：有第一条/第二条、有《设备采购合同》⇒ **不许**认成法规。 |
| `test_judgment_is_not_a_law` 函数 | 319 | 1 | 判决书：正文引《合同法》，但自称"本院"而不是"本法"⇒ **不许**认成法规。 |
| `test_law_without_the_recital_phrase_is_still_refused` 函数 | 329 | 1 | 缺**立法句式**（"本法"/"本条例"）就不算——这是四条证据之一，不是装饰。 |
| `test_must_start_at_article_one` 函数 | 336 | 1 | 引用的条号**不从第一条开始** ⇒ 是节选/引用，不是法规全文。 |
| `test_law_name_is_never_taken_from_the_body` 函数 | 345 | 1 | **根因钉子**：法规名**只能**来自标题——正文里的 `《…》` 一律不算。 |
| `TestInputValidation` 类 | 370 | 1 | — |
| `test_blank_title_is_refused` 函数 | 371 | 1 | — |
| `test_blank_text_is_refused` 函数 | 375 | 1 | 没有正文的采集件不该登记——那会让评审人对着空白"批准"（盲签）。 |
| `test_chunks_keep_the_fidelity_invariant` 函数 | 380 | 1 | 采集件的切片也要满足**逐字取回**（引用点回原文的地基）。 |
| `test_bad_max_chars_is_refused_by_the_shared_guard` 函数 | 390 | 1 | `max_chars` 的校验只有一处所有者（`material_ingest`），采集路径也要吃到它。 |
| `test_binary_container_is_refused_at_the_door` 函数 | 395 | 1 | **唯一的采集门**自己就要挡住二进制（不能只靠采集器自觉）。 |
| `test_binary_signature_in_the_middle_is_not_refused` 函数 | 412 | 1 | 保守：签名只在**开头**算——正文中间提到 `%PDF-` 的文章不该被误杀。 |
| `TestDomainHelper` 类 | 420 | 1 | — |
| `test_domain_of` 函数 | 429 | 1 | — |

### `tests/test_material_dedup.py`（32 个符号）

> 近重复检测测试（`src/core/materials/dedup.py`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestNormalize` 类 | 15 | 1 | — |
| `test_punctuation_and_whitespace_are_dropped` 函数 | 16 | 1 | — |
| `test_fullwidth_folds_to_halfwidth` 函数 | 20 | 1 | — |
| `test_case_folds` 函数 | 24 | 1 | — |
| `test_empty_inputs_are_empty` 函数 | 27 | 1 | — |
| `TestSimilarity` 类 | 32 | 2 | — |
| `test_identical_is_one` 函数 | 33 | 1 | — |
| `test_punctuation_only_change_is_near_one` 函数 | 36 | 1 | — |
| `test_one_word_changed_stays_a_near_duplicate` 函数 | 41 | 1 | 改一两个词仍是"同一篇稿子"（**判据是阈值，不是 0.9**）。 |
| `test_different_wording_is_low` 函数 | 53 | 1 | **改写过的独立报道必须被判为不同**（否则会掐掉真互证）。 |
| `test_unrelated_text_is_low` 函数 | 59 | 1 | — |
| `test_short_texts_fall_back_to_equality` 函数 | 62 | 1 | 短文本（< 3n）不做 n-gram：相等=1，不等=0（样本太短，Jaccard 不稳定）。 |
| `test_one_side_empty_is_zero_except_both_empty` 函数 | 67 | 1 | — |
| `test_empty_against_empty_normalized` 函数 | 72 | 1 | — |
| `test_threshold_is_configurable` 函数 | 76 | 1 | 阈值可调，且**行为随阈值单调**（用实测相似度定位，不靠我猜具体数值）。 |
| `TestGroupByContent` 类 | 90 | 1 | — |
| `test_identical_texts_group_together` 函数 | 91 | 1 | — |
| `test_distinct_texts_stay_separate` 函数 | 94 | 1 | — |
| `test_output_is_deterministic` 函数 | 101 | 1 | — |
| `test_empty_input` 函数 | 105 | 1 | — |
| `TestIndependentSourceCount` 类 | 109 | 1 | **域名图**的连通分量（不是内容分组的个数——那是第一版的错）。 |
| `test_syndicated_pair_counts_as_one` 函数 | 112 | 1 | — |
| `test_two_genuinely_different_reports_count_as_two` 函数 | 119 | 1 | — |
| `test_same_domain_two_articles_is_ONE_source` 函数 | 126 | 1 | 同一家媒体的两篇不同文章 = 一个来源（节点语义，不是内容分组数）。 |
| `test_syndicated_pair_plus_a_second_real_source` 函数 | 135 | 1 | — |
| `test_unknown_identity_is_excluded` 函数 | 143 | 1 | 无域名的条目**不参与**（它们本来就不能互证，判据在 authority 那一层）。 |
| `test_all_unknown_gives_zero` 函数 | 150 | 1 | — |
| `test_transitivity_is_handled_by_components` 函数 | 153 | 1 | 近似关系不传递（A≈B、B≈C 但 A≉C）——连通分量把它们并成一组（可复现的定义）。 |
| `TestHonestLimits` 类 | 164 | 1 | — |
| `test_heavy_rewrite_is_not_detected` 函数 | 165 | 1 | **已知边界**：把通稿大改一遍后重发，本模块**抓不到**（判据只是"文字近似"）。 |
| `test_threshold_is_documented` 函数 | 175 | 1 | — |
| `test_never_raises_on_missing_input` 函数 | 181 | 1 | — |

### `tests/test_material_harvest.py`（72 个符号）

> 网页采集器测试（`src/core/materials/harvest.py`，Phase C 第四步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 32 | 575 | — |
| `site` 函数 | 47 | 207 | 极简本地站点：正常页 / 各种"不是网页正文"的形态 / 302 / 无 Content-Type。 |
| `page_transport` 函数 | 109 | 11 | 把 `fn(url, **kw) -> (status, text)` 包成一个**最小 transport 替身**。 |
| `allow_local` 函数 | 131 | 34 | 把 SSRF 判据换成"公网"以允许打本地站点。 |
| `TestSsrfGate` 类 | 140 | 1 | — |
| `test_loopback_is_refused_and_nothing_is_fetched` 函数 | 141 | 1 | **最重要的一条**：内网地址在**抓取之前**就被拒，且不建材料。 |
| `test_private_and_non_http_are_refused` 函数 | 162 | 1 | — |
| `test_blank_url` 函数 | 167 | 1 | — |
| `TestHappyPath` 类 | 171 | 2 | — |
| `test_fetches_and_registers_as_pending` 函数 | 172 | 1 | — |
| `test_title_comes_from_the_page` 函数 | 187 | 1 | — |
| `test_caller_title_wins` 函数 | 191 | 1 | — |
| `test_script_and_style_do_not_become_content` 函数 | 195 | 1 | 页面里的 JS/CSS **不能**进正文（采集最脏的来源）。 |
| `test_note_records_the_fetch` 函数 | 204 | 1 | — |
| `test_same_page_twice_is_a_duplicate` 函数 | 209 | 1 | — |
| `test_injected_transport_is_used` 函数 | 216 | 1 | 不需要真网络：注入一个假 transport 就能测通路。 |
| `test_content_type_is_recorded_for_the_reviewer` 函数 | 224 | 1 | Content-Type 进 `tier_reason`：判据**可见**，评审人能自己复核白名单判得对不对。 |
| `test_missing_content_type_is_stated_honestly` 函数 | 229 | 1 | 服务端没给 Content-Type ⇒ 放行，但**如实写明"未给"**（不是假装检查过）。 |
| `test_text_plain_page_is_accepted` 函数 | 235 | 1 | 纯文本通知（`text/plain`）是**合法**的资料来源，白名单必须放它。 |
| `TestNotAPageIsRefused` 类 | 243 | 1 | **独立复核 2026-09-17 的 MEDIUM**：以前 JS/CSS/JSON 接口会被当成网页正文登记。 |
| `test_non_page_content_types_are_refused` 函数 | 258 | 1 | — |
| `test_real_bytes_gate_catches_a_mislabeled_png` 函数 | 264 | 1 | **Content-Type 撒谎说自己是 html**：只有真实字节能认出 PNG。 |
| `test_real_bytes_gate_catches_a_mislabeled_pdf` 函数 | 275 | 1 | — |
| `test_the_type_gate_is_not_bypassed_by_a_title` 函数 | 280 | 1 | 调用方给了 title 也不能让"不是网页"的东西变成材料（标题不是通行证）。 |
| `test_content_type_header_key_case_does_not_skip_the_gate` 函数 | 285 | 1 | 响应头的**键名大小写**不许决定白名单是否生效（2026-09-17 复核 E 的 LOW）。 |
| `TestTransportContractIsStrict` 类 | 304 | 1 | — |
| `test_transport_without_fetch_page_is_refused_loudly` 函数 | 305 | 1 | **严格**契约：只有 `fetch`（拿不到 Content-Type/真实字节）的 transport ⇒ 拒绝。 |
| `TestFailsLoudlyAndRegistersNothing` 类 | 322 | 1 | — |
| `test_bad_responses_do_not_create_material` 函数 | 329 | 1 | — |
| `test_transport_exception_is_reported_not_raised` 函数 | 335 | 1 | — |
| `test_404_does_not_register` 函数 | 344 | 1 | — |
| `TestTruncation` 类 | 349 | 1 | — |
| `test_long_page_is_truncated_and_says_so` 函数 | 350 | 1 | — |
| `TestNoProductionBypass` 类 | 361 | 1 | — |
| `test_collect_url_has_no_private_allow_switch` 函数 | 362 | 1 | **结构性约束**：不得存在"允许内网"之类的参数（那是给严格版开后门）。 |
| `test_it_calls_the_ssrf_owner_exactly_once_per_url` 函数 | 373 | 2 | **行为**断言（不是"源码里有这个字符串"）：判据真的被调、且每跳都调。 |
| `test_the_ssrf_verdict_actually_gates` 函数 | 395 | 1 | 判据的结论**真的**决定结果：换成"一律拒绝"的替身 ⇒ 连公网地址也不抓。 |
| `test_no_second_address_judgement_in_the_module` 函数 | 412 | 1 | 粗护栏（**不是**上面那条行为断言的替代品）：本模块不自己解析地址。 |
| `TestRedirectsAreNotFollowed` 类 | 426 | 1 | **独立复核 2026-09-17 的 HIGH**：默认传输跟随 302，实测可把请求引向内网。 |
| `test_contract_forwards_allow_redirects_false` 函数 | 436 | 1 | `allow_redirects=False` 是**承重**的（`page_transport` 内部就断言了这一点，。 |
| `test_http_is_retried_on_https_same_host` 函数 | 451 | 1 | — |
| `test_redirect_after_upgrade_is_refused_not_followed` 函数 | 468 | 1 | — |
| `test_https_url_that_redirects_is_refused` 函数 | 475 | 1 | https 没有可升级的空间 ⇒ 直接拒绝（不给"再试一次"的假动作）。 |
| `test_https_upgrade_only_changes_the_scheme` 函数 | 487 | 1 | — |
| `test_real_transport_does_not_follow_a_redirect` 函数 | 495 | 1 | **真实传输**下的证明：本地 302（Location 指向内网元数据端点）拿到的是 **302 本身**。 |
| `TestEmptyReasonDistinguishesTwoKinds` 类 | 514 | 1 | 两种"空"必须能区分（复核 2026-09-17 的归因误导）。 |
| `test_original_body_empty` 函数 | 517 | 1 | **原文本身为空**（连标签都没有）→ 原因串说"响应为空"。 |
| `test_tag_only_body_is_reported_as_converted_empty` 函数 | 523 | 1 | **原文非空但转换后为空**（只有标签）→ 原因串必须说清是"转换后"为空。 |
| `test_nonempty_body_that_becomes_empty_after_conversion` 函数 | 534 | 1 | — |
| `TestHtmlToTextOwner` 类 | 541 | 1 | — |
| `test_equivalent_to_clause_health_without_script_or_style` 函数 | 542 | 1 | 规范实现与既有 `clause_health_html_to_text` 逐字符等价——**除两条有意差异**。 |
| `test_deliberate_difference_on_uppercase_table_tags` 函数 | 560 | 1 | **有意差异②**：大写 `</TD>`/`</TR>` 在本函数里照样转表格分隔。 |
| `test_deliberate_difference_on_script_and_style` 函数 | 573 | 1 | **有意不同**：本函数丢掉 script/style 的**内容**（那三份不会）。 |
| `TestScriptStyleStrippingEdges` 类 | 586 | 1 | `_strip_script_style` 的边角语义（**两轮复核**都在这里抓到问题，故钉得细）。 |
| `test_html5_semantics_slash_does_not_self_close` 函数 | 597 | 1 | **HTML5**：`<script src="a.js"/>` 里的 `/` 被忽略 ⇒ 到 `</script>` 之间是**脚本**。 |
| `test_style_self_closing_slash_also_does_not_self_close` 函数 | 612 | 1 | 同一条语义的 style 版：`<style/>` 之后的可见文字**属于样式内容**，浏览器不显示。 |
| `test_html_comment_does_not_hide_a_script_from_the_sweep` 函数 | 618 | 1 | **OVERKILL-1**（复核 D②）：注释里的 `<script>` **不是标签**，不许吞掉其后正文。 |
| `test_end_tag_with_junk_is_recognized` 函数 | 626 | 1 | **OVERKILL-2**：`</script foo>` 是浏览器接受的结束标签，第一版认不出 ⇒ 吞掉其后正文。 |
| `test_literal_script_inside_an_attribute_is_not_a_tag` 函数 | 632 | 1 | **OVERKILL-3**：属性值里的字面 `<script>` 不是标签（否则其后正文被吞）。 |
| `test_literal_script_in_an_UNQUOTED_attribute_is_not_a_tag_either` 函数 | 639 | 1 | **OVERKILL-4**（2026-09-17 复核 LOW 顺带实测，v3 修）：**无引号**属性值同理。 |
| `test_a_bare_less_than_in_the_text_does_not_disable_the_sweep` 函数 | 654 | 1 | **上面那条守卫的风险方向**：正文里的裸 `<` **不许**让真 `<script>` 变成文本。 |
| `test_the_guard_runs_on_the_ORIGINAL_string_not_a_rewritten_one` 函数 | 670 | 1 | **顺序是承重的**（2026-09-17 独立复核 b7 的 MEDIUM）。 |
| `test_only_the_raw_text_families_browsers_hide_are_stripped` 函数 | 689 | 1 | **真机裁决**：这一族里只有三个是"浏览器不显示"的（复核 b8 的 LOW-5 → b9 的 MEDIUM-4）。 |
| `test_script_inside_raw_text_elements_is_text_not_a_tag` 函数 | 723 | 1 | **raw text 元素里的字面 `<script>` 是文字**（复核 b10 的 LOW-1，2026-09-18 修）。 |
| `test_raw_text_guard_is_not_opened_by_attribute_values_or_nesting` 函数 | 745 | 1 | **守卫不许被打开**：两种形状里那个"raw text 元素"都不是真元素（复核 b12 的 MEDIUM-1）。 |
| `test_real_script_outside_raw_text_is_still_stripped` 函数 | 765 | 1 | **反向对照**：元素**外面**的 `<script>`/`<style>` 仍必须剥掉。 |
| `test_guard_requirement_one_is_load_bearing` 函数 | 779 | 1 | 守卫的**要求①**（`<` 之后必须紧跟字母或 `/`）是**承重的**，必须有正面用例。 |
| `test_unclosed_script_swallows_the_tail_like_a_browser` 函数 | 800 | 1 | 未闭合 ⇒ 其后全部是脚本文本（HTML5），**不得**把 JS 当正文留下来。 |
| `test_unclosed_style_swallows_the_tail` 函数 | 811 | 1 | — |
| `test_uppercase_and_mixed_case_tags` 函数 | 815 | 1 | **大小写敏感性要有钉子**（独立复核 M3 变异体 GREEN：原先零覆盖）。 |
| `test_close_tag_inside_a_script_string` 函数 | 822 | 1 | 脚本里的字符串含 `</p>` 这类片段**不能**骗过剥离（用闭合标签本身定位）。 |
| `test_normal_closed_tags_still_work` 函数 | 827 | 1 | — |

### `tests/test_material_ingest.py`（42 个符号）

> 材料解析与切片测试（Phase A 第二步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 19 | 575 | — |
| `_make_txt` 函数 | 23 | 15 | — |
| `_make_docx` 函数 | 28 | 3 | — |
| `_make_pdf` 函数 | 37 | 38 | — |
| `TestChunking` 类 | 49 | 1 | — |
| `test_offsets_round_trip_exactly` 函数 | 50 | 1 | **保真不变量（最强口径）**：全文\[块.start:块.end\] **逐字**等于块文本。 |
| `test_chunk_spanning_blank_line_keeps_original_separators` 函数 | 65 | 1 | 跨空行/跨页的块必须**原样保留**原文分隔符（2026-09-17 被验收测试抓到的 bug：。 |
| `test_short_lines_pack_into_one_chunk` 函数 | 74 | 1 | — |
| `test_max_chars_splits` 函数 | 79 | 1 | — |
| `test_overlong_single_line_is_hard_split` 函数 | 88 | 1 | — |
| `test_blank_text_yields_nothing` 函数 | 96 | 1 | — |
| `test_page_mapping` 函数 | 99 | 1 | — |
| `test_build_document_spans_self_consistent` 函数 | 108 | 1 | — |
| `TestExtract` 类 | 117 | 1 | — |
| `test_txt` 函数 | 118 | 1 | — |
| `test_docx_is_page_1` 函数 | 122 | 1 | — |
| `test_pdf_keeps_page_numbers` 函数 | 128 | 1 | — |
| `test_empty_txt_gives_no_pages` 函数 | 133 | 1 | — |
| `TestIngest` 类 | 139 | 1 | — |
| `test_txt_becomes_approved_by_birth_with_offsets` 函数 | 140 | 1 | S3-b1 对账（业主裁定 NOT-DOING #15）：人工上传**免评审**，出生即 approved。 |
| `test_title_strips_duplicate_suffix` 函数 | 157 | 1 | — |
| `test_duplicate_content_is_not_registered_twice` 函数 | 162 | 1 | — |
| `test_file_outside_project_dir_is_copied_in` 函数 | 172 | 1 | 材料平面要自包含：外面来的文件复制进项目目录（独立存储）。 |
| `test_file_already_in_project_dir_is_referenced_in_place` 函数 | 180 | 1 | — |
| `test_unparsable_pdf_is_registered_but_flagged` 函数 | 186 | 2 | 扫描件（无文本层）：**仍登记**（用户得看得见），但如实说明没解析出文本。 |
| `test_judged_garbled_pdf_is_not_reported_as_scanned` 函数 | 201 | 1 | **成因要分开回显**（2026-09-25 复核 P-4）：文本层被判乱码 ≠ 没有文本层。 |
| `test_empty_txt_does_not_guess_a_cause` 函数 | 244 | 1 | **取不到文本层状态时不许臆测原因**（2026-09-25 第 2 轮复核 Q4：这条分支无测试）。 |
| `test_unsupported_suffix_rejected` 函数 | 263 | 1 | — |
| `test_project_dir_ingest_is_batch_and_ok` 函数 | 269 | 1 | — |
| `test_scan_is_stable_and_filtered` 函数 | 279 | 1 | — |
| `test_ingested_material_gate_closes_and_reopens` 函数 | 287 | 1 | 端到端串一遍硬门（免评审口径，裁定 #15）：收件 ⇒ 出生即可用 ⇒。 |
| `TestPhaseAAcceptance` 类 | 305 | 1 | 方案 §9 的 Phase A 验收：**放一份 PDF → 评审通过 → 提问 → 引用能点回该 PDF 的位置**。 |
| `test_pdf_gate_search_and_citation_point_back` 函数 | 321 | 1 | — |
| `test_pdf_citation_is_exact_without_strip` 函数 | 360 | 1 | 引用区间必须**逐字**取回（不是"去掉空白后相等"）。 |
| `test_page_of_contract_on_separator` 函数 | 381 | 1 | `page_of` 的精确契约：落在**页间分隔符**上返回**最后一页**（不是上一页）。 |
| `TestMaxCharsGuard` 类 | 397 | 1 | verifier 报的 **MEDIUM** 缺陷回归：`max_chars<=0` 曾让硬切循环**死循环**。 |
| `test_chunk_text_rejects_non_positive` 函数 | 405 | 1 | — |
| `test_rejected_even_when_text_is_empty` 函数 | 410 | 1 | **同一参数只能有一种命运**：空文本早退也不得放过非法参数。 |
| `test_bool_is_rejected` 函数 | 415 | 1 | `True` 是 int 的子类但不是合法块大小——别把它当 1 悄悄接受。 |
| `test_ingest_file_rejects_before_touching_content` 函数 | 421 | 1 | 公开入口同样拒绝——**即使该文件解析不出文本**（那时 `chunk_text` 不会被调用）。 |
| `test_legal_small_value_still_works` 函数 | 431 | 1 | 合法小值照常硬切（修复不能把正常能力一起砍掉）。 |
| `test_scan_pdf_needs_explicit_deep_and_is_flagged` 函数 | 437 | 1 | 扫描件（无文本层）在**默认不外发**下拿不到内容 —— 但材料仍登记并如实标注。 |

### `tests/test_material_locator.py`（30 个符号）

> 引用**锚点稳定性**测试（`src/core/materials/locator.py`，方案 §12 未决第 5 条）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 25 | 575 | — |
| `_txt` 函数 | 29 | 28 | — |
| `TestIngestRecordsTheProvenance` 类 | 35 | 1 | — |
| `test_file_material_records_hash_and_fingerprint` 函数 | 36 | 1 | 入库必须记下**派生全文哈希 + 解析器指纹**（否则锚点无从判定）。 |
| `test_web_material_records_the_collect_fingerprint` 函数 | 51 | 1 | 网页材料的指纹是**采集通道**那一个（它没有源文件可重解析）。 |
| `test_no_text_means_no_derived_hash` 函数 | 59 | 1 | 解析不出文本 ⇒ `derived_text_hash` 存 **NULL**（不是"空文本的哈希"）。 |
| `TestCheapHealth` 类 | 67 | 1 | — |
| `test_untouched_material_is_ok_but_the_wording_is_honest` 函数 | 68 | 1 | — |
| `test_old_material_without_provenance_is_unknown_not_ok` 函数 | 75 | 1 | 2026-09-17 之前的材料没有这两列 ⇒ **unknown**（不假装 ok）。 |
| `test_changed_fingerprint_is_stale` 函数 | 84 | 1 | 指纹变了 ⇒ `stale`（**不是**"已经坏了"——要说清要复算）。 |
| `test_no_chunks_means_no_locators` 函数 | 94 | 1 | — |
| `test_no_chunks_with_text_says_which_cause` 函数 | 102 | 1 | `no_locators` 的**另一种**成因：有派生文本、但切块没产出（INFO-5）。 |
| `test_missing_content_hash_is_not_a_missing_file` 函数 | 112 | 1 | **文件在、但没有字节哈希** ≠ **文件不在**（复核 b10 的 LOW-3）。 |
| `test_pdf_cheap_check_refuses_to_claim_ok` 函数 | 129 | 1 | PDF 的完整指纹含**只有解析后才知道**的 text_layer/ocr ⇒ 便宜比对**不许说 ok**。 |
| `TestSourceFileIdentity` 类 | 150 | 1 | **输入**这一轴（独立复核 b9 的 MEDIUM-1，2026-09-18 修）。 |
| `test_deleted_source_file_is_not_ok` 函数 | 159 | 1 | — |
| `test_replaced_source_file_is_stale_not_ok` 函数 | 168 | 1 | 换成另一份同名文件 ⇒ `stale`，且**说清是源文件变了**（不是"解析器变了"）。 |
| `test_replaced_pdf_is_stale_not_unknown` 函数 | 179 | 1 | PDF 也一样：**字节变了就是 stale**，不许因为"指纹前缀相同"停在 unknown。 |
| `test_unchanged_source_still_ok` 函数 | 195 | 1 | **反向对照**：文件真的没变时必须仍然给 `ok`。 |
| `test_web_material_has_no_source_axis` 函数 | 207 | 1 | 网页件没有源文件 ⇒ 这一轴**不参与**（不是"源文件不在"的告警）。 |
| `TestStrongReverify` 类 | 216 | 1 | — |
| `test_unchanged_source_matches` 函数 | 217 | 1 | 源文件没变 ⇒ 重解析**逐字节一致**（这才是真正的保证）。 |
| `test_changed_parser_output_is_a_mismatch` 函数 | 225 | 1 | **解析器变了**（模拟：重解析得到不同文本）⇒ `mismatch`，且措辞点明"区间已失效"。 |
| `test_web_material_cannot_be_reverified` 函数 | 236 | 1 | 没有留存源文件 ⇒ `unavailable`（**不是 ok**）。 |
| `test_text_then_blank_reparse_is_a_mismatch` 函数 | 245 | 1 | 入库时**有**文本、现在重解析**一个字都得不到** ⇒ **确定的失效**。 |
| `test_missing_material_raises` 函数 | 260 | 1 | — |
| `TestProjectSummary` 类 | 265 | 1 | — |
| `test_one_crashing_material_does_not_kill_the_whole_overview` 函数 | 266 | 1 | **一份材料的判据挂掉，不该毁掉整个项目总览**（INFO-3 的同型问题，2026-09-18 修）。 |
| `test_counts_and_attention_list` 函数 | 294 | 1 | — |
| `test_bootstrap_guarantees_the_material_columns` 函数 | 305 | 1 | **引导契约**：`init_schema()` + 两个 ensure 之后，两张表的追加列都在。 |

### `tests/test_material_repo.py`（46 个符号）

> 材料平面仓库测试（2026-09-17 定位转移 Phase A）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 20 | 575 | — |
| `TestProject` 类 | 25 | 1 | — |
| `test_create_and_get` 函数 | 26 | 1 | — |
| `test_list_contains_created` 函数 | 34 | 1 | — |
| `test_get_unknown_is_none` 函数 | 40 | 1 | — |
| `TestMaterialDefaults` 类 | 45 | 1 | — |
| `test_new_material_born_status_by_origin` 函数 | 46 | 1 | S3-b（2026-09-22 业主裁定 NOT-DOING #15）：出生评审状态**按来源**——。 |
| `test_user_material_defaults_to_t1_system` 函数 | 59 | 1 | 用户自有原件默认 T1（对其自身内容是初级证据），由 system 判。 |
| `test_collected_material_is_not_trusted_by_default` 函数 | 65 | 1 | **自采默认不可信**（T3 起）：网上找来的在没证据前不该默认可信。 |
| `test_invalid_enums_rejected` 函数 | 70 | 1 | — |
| `test_tier_evidence_roundtrips` 函数 | 78 | 1 | — |
| `TestReviewGate` 类 | 86 | 1 | — |
| `test_approved_materials_is_the_hard_gate` 函数 | 87 | 1 | 硬门核原样：自采未经批准不得进作答。 |
| `test_collected_pending_is_not_in_gate` 函数 | 107 | 1 | 自采出生 pending ⇒ 不在门内（硬门前提原样）。 |
| `test_review_note_and_timestamp_recorded` 函数 | 114 | 1 | — |
| `test_set_review_unknown_id_returns_false` 函数 | 122 | 1 | — |
| `test_invalid_status_rejected` 函数 | 125 | 1 | — |
| `TestTwoAxes` 类 | 132 | 1 | — |
| `test_task_role_is_independent_of_source_tier` 函数 | 133 | 1 | 公司制度例：**来源层级低**但**是本任务的准则**——两轴必须能并存。 |
| `test_user_can_override_tier_and_it_is_recorded` 函数 | 147 | 1 | 业主明说"用户可以改效力层级"⇒ 改完要能看出是**人**定的（留痕）。 |
| `test_invalid_tier_and_role_rejected` 函数 | 156 | 1 | — |
| `test_lifecycle_promote` 函数 | 165 | 2 | — |
| `test_tier_labels_cover_all_tiers` 函数 | 173 | 1 | — |
| `TestChunks` 类 | 178 | 1 | — |
| `test_chunks_keep_char_offsets_and_order` 函数 | 179 | 1 | — |
| `test_empty_text_chunks_are_skipped` 函数 | 192 | 1 | — |
| `test_char_end_defaults_to_text_length` 函数 | 197 | 1 | — |
| `TestSearch` 类 | 205 | 1 | — |
| `_seed` 函数 | 206 | 20 | — |
| `test_search_only_returns_approved` 函数 | 216 | 1 | **硬门写在 SQL 里**：未批准的材料不可能被搜出来。 |
| `test_rejected_material_is_not_searchable` 函数 | 229 | 1 | — |
| `test_search_returns_citation_fields` 函数 | 235 | 1 | 命中的每一项都要带"能标注 + 能点回原文"的字段（可见性硬需求）。 |
| `test_search_labelling_shows_both_axes` 函数 | 247 | 1 | — |
| `test_search_is_project_scoped` 函数 | 255 | 1 | A 项目的材料不该出现在 B 项目的检索结果里。 |
| `test_search_junk_query_does_not_raise` 函数 | 261 | 1 | — |
| `test_limit_respected` 函数 | 267 | 1 | — |
| `test_bad_arguments_raise_instead_of_silently_finding_nothing` 函数 | 276 | 1 | **坏参数不许静默变成"没有命中"**（verifier 2026-09-17 报的 LOW）。 |
| `test_real_sql_failure_is_loud_not_empty` 函数 | 295 | 1 | **表/SQL 真坏了必须留痕**，不能伪装成"材料里没有命中"。 |
| `test_programming_error_is_not_swallowed` 函数 | 316 | 1 | **非 sqlite 异常必须冒出来**（这是从兜底 `Exception` 收窄的全部意义）。 |
| `TestDelete` 类 | 330 | 1 | — |
| `test_delete_material_removes_chunks_and_index` 函数 | 331 | 1 | — |
| `TestLawChainIsolation` 类 | 345 | 1 | — |
| `test_material_ops_do_not_touch_law_chain` 函数 | 346 | 1 | **行为级**证明零耦合：材料操作前后，法条链三张表行数完全不变。 |
| `test_link_doc_only_writes_material_side` 函数 | 371 | 1 | Track L 的回指**写在材料侧**（doc_id 列），不改 doc_meta。 |
| `TestStorageLocation` 类 | 379 | 1 | — |
| `test_materials_dir_is_under_data_dir_and_per_project` 函数 | 380 | 1 | 材料原件放数据区（代码树零运行产物），且**按项目分目录**。 |

### `tests/test_material_track_l.py`（49 个符号）

> Track L 决策测试（`src/core/materials/track_l.py`，Phase C 第二步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 23 | 575 | — |
| `law_docs` 函数 | 28 | 30 | 登记本测试往**法条链**写的 doc_id，**测完删干净**。 |
| `_std_body` 函数 | 49 | 2 | 一份**像真的**标准正文。 |
| `_collect_standard` 函数 | 71 | 19 | 采一条"疑似标准正文"。 |
| `_seed_doc` 函数 | 82 | 70 | 往法条链塞一条最小 doc_meta（模拟"库内已有"），返回 doc_id。 |
| `TestGates` 类 | 111 | 1 | — |
| `test_missing_material_is_skip` 函数 | 112 | 1 | — |
| `test_unapproved_material_is_BLOCKED` 函数 | 115 | 2 | **评审硬门没有例外**：未批准的材料绝不可能进法条库。 |
| `test_rejected_material_is_also_blocked` 函数 | 124 | 1 | — |
| `test_non_standard_material_is_skip_even_if_approved` 函数 | 130 | 1 | — |
| `test_approved_standard_without_library_copy_needs_import` 函数 | 139 | 1 | — |
| `TestLinkWhenLibraryAlreadyHasIt` 类 | 149 | 1 | — |
| `test_approved_standard_already_in_library_links_only` 函数 | 150 | 1 | — |
| `test_apply_link_points_the_material_at_the_doc` 函数 | 159 | 1 | — |
| `test_apply_link_on_import_does_NOTHING_and_says_so` 函数 | 168 | 1 | `import` 动作下 **什么都不写**，且返回值必须让人看到"还没入库"。 |
| `test_apply_link_refuses_when_blocked` 函数 | 181 | 1 | 未批准时 `apply_link` 也必须**拒绝**（不能因为"只是回指"就放行）。 |
| `TestStandardNoKey` 类 | 189 | 1 | 比较键：把库内写法与采集侧写法归一到同一把尺子。 |
| `test_equivalent_writings_share_a_key` 函数 | 199 | 1 | — |
| `test_different_standards_do_not_collide` 函数 | 208 | 1 | — |
| `test_empty_is_empty` 函数 | 212 | 2 | — |
| `test_find_existing_doc_matches_across_writings` 函数 | 217 | 1 | 库内写 `GB 10146-2015`，采集侧给 `GB10146-2015` —— 必须能匹配上。 |
| `TestLawNameKey` 类 | 224 | 1 | 法规比较键：**保留版本/修正标记**（与标准号键的方向**相反**）。 |
| `test_the_amendment_year_is_part_of_the_identity` 函数 | 235 | 1 | — |
| `test_same_law_in_different_writings_shares_a_key` 函数 | 247 | 1 | — |
| `test_empty_is_empty` 函数 | 251 | 2 | — |
| `test_find_existing_law_does_not_point_a_new_amendment_at_an_old_one` 函数 | 256 | 1 | 库里只有 **2014 修正版**时，**2021 修正版**必须判成"库内没有"。 |
| `TestIntentParsing` 类 | 271 | 1 | — |
| `test_intent_is_read_from_tier_evidence` 函数 | 272 | 1 | — |
| `test_non_standard_has_no_intent` 函数 | 278 | 1 | — |
| `test_broken_json_evidence_does_not_raise` 函数 | 284 | 1 | — |
| `test_actions_constant_is_the_single_definition` 函数 | 290 | 1 | — |
| `TestImportToLibrary` 类 | 294 | 1 | Track L 的**入库**那一半：走既有 `law_text.ingest_law_text`（不重写切分/分型/建边）。 |
| `test_unapproved_never_touches_the_law_chain` 函数 | 297 | 1 | **最要紧的一条**：未批准时入库函数必须彻底不动法条链。 |
| `test_approved_standard_is_imported_and_linked` 函数 | 314 | 1 | — |
| `test_imported_standard_is_resolvable_by_the_law_chain` 函数 | 343 | 1 | 入库之后，法条链**自己**的查询要能找到它（否则"入库"没有意义）。 |
| `test_second_import_of_same_material_is_idempotent` 函数 | 355 | 1 | 再跑一次不该造出第二部标准（既有管线的查重会让它退化为回指）。 |
| `test_reconcile_dispatches_link_and_never_writes_for_blocked` 函数 | 377 | 1 | `reconcile` 的分派：link 走回指。 |
| `test_material_without_chunks_refuses_to_import` 函数 | 393 | 1 | 没有正文的采集件不得入库——那会造出一部空标准。 |
| `test_unparsable_body_fails_loudly_instead_of_silently` 函数 | 405 | 2 | 切不出条款时必须**如实报错**，不能静默"成功"或造出一部空标准。 |
| `test_collected_LAW_text_is_now_recognized_and_imported` 函数 | 426 | 1 | **法规正文现在能走通了**（2026-09-17 起）。 |
| `test_import_of_law_without_a_name_refuses_loudly` 函数 | 471 | 1 | 法规名没取到 ⇒ **拒绝入库**（没有名字就没法在库里认它，宁可不入）。 |
| `test_hierarchy_and_clause_type_are_honest` 函数 | 487 | 1 | 复核 step-31~34 的两条 MEDIUM：**标准条款的类型**与**采集件的效力/质量默认值**。 |
| `test_imported_standard_clauses_are_rules_not_legal` 函数 | 499 | 1 | 标准入库后，条款的 `knowledge_type` 必须是 `rule`（不是 `legal`）。 |
| `test_imported_collected_doc_is_marked_unknown_not_effective` 函数 | 516 | 1 | 采集件落库后：效力**未知**（不是 effective）、质量 **C**、类型**不声明**。 |
| `test_collected_standard_lands_in_the_standard_tree` 函数 | 559 | 1 | **进对树**：`auto_tag` 的归一形 `GB12321-2021`（无空格）也要被认成标准。 |
| `test_law_hierarchy_is_conservative_and_says_undecided` 函数 | 582 | 1 | 层级推断**只用不会错的规则**，其余一律 `未定`（**不假装知道位阶**）。 |
| `TestTreeClassificationOfStandardNumbers` 类 | 601 | 1 | `doc_catalog._STD_NO_PREFIX` 的判据要容纳**无空格写法**（复核 step-31~34 的 MEDIUM）。 |
| `test_standard_numbers_go_to_the_standard_tree` 函数 | 617 | 1 | — |
| `test_law_names_do_not_become_standards` 函数 | 626 | 1 | 反方向也不能错：法规名不许被当成标准号（白名单**不是**"任何带数字的东西"）。 |

### `tests/test_measure_harness.py`（5 个符号）

> **量具自己的闸门**：`scripts/measure-endpoint-blocking.py` 必须真的分得开

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_synthetic_app` 函数 | 32 | 2 | — |
| `app` 函数 | 51 | 297 | — |
| `test_尺能量出_async_def_把事件循环堵住` 函数 | 55 | 0 | — |
| `test_尺能量出_def_没有把事件循环堵住` 函数 | 64 | 0 | — |
| `test_两条端点的耗时同量级_证明尺量的是谁被占住而不是谁慢` 函数 | 73 | 0 | — |

### `tests/test_middle_bbox_units.py`（14 个符号）

> spec 012 R1 判据：MinerU 4.0 的**归一化 bbox** 必须换算成**绝对点**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_40` 函数 | 28 | 10 | 造一份最小的 MinerU 4.0 产物（形状照真产物）。 |
| `Test归一化bbox换算成点` 类 | 52 | 0 | ★ 核心判据：4.0 的比例 bbox ⇒ 输出必须是点。 |
| `test_比例bbox被换算成页尺寸量级` 函数 | 55 | 0 | 喂 `\[0.116, 0.138, 0.937, 0.176\]`（比例）⇒ 出 `\[285, 477, 2301, 608\]`（点）。 |
| `test_换算后通过退化闸门` 函数 | 67 | 0 | ★ 这是**用户可见的效果**：换算后箭头才画得出来（不再被当碎片丢掉）。 |
| `test_坐标落在页尺寸内` 函数 | 81 | 0 | 换算后 x 必须 ≤ 页宽、y ≤ 页高（不越界）。 |
| `test_页尺寸不同则换算结果不同` 函数 | 91 | 0 | 防"写死 595/841"：同一比例在 600×800 与 2456×3456 上结果必须不同。 |
| `Test已是点的bbox不被重复缩放` 类 | 100 | 0 | ★ 反向判据：本来就 >1 的坐标**不许**再乘一次页宽。 |
| `test_绝对值bbox原样保留` 函数 | 107 | 0 | 喂 `\[285, 477, 2301, 608\]`（已经是点）⇒ 不许再乘。 |
| `test_混合值不被缩放` 函数 | 116 | 0 | 只要有一个值 >1，整条**原样返回**（不猜、不部分缩）。 |
| `test_空bbox不炸` 函数 | 125 | 0 | — |
| `Test行级bbox也换算` 类 | 133 | 0 | ★ 行级 bbox 是**真正画箭头用的那个**（`pipeline` 优先取 line.bbox）。 |
| `test_行级bbox也乘页尺寸` 函数 | 139 | 0 | — |
| `Test3_4产物行为不变` 类 | 149 | 0 | ★ 回归护栏：3.4 产物**原样返回**，既有行为一字不变。 |
| `test_34产物原样返回` 函数 | 155 | 0 | — |

### `tests/test_middle_locator.py`（18 个符号）

> middle_locator 契约测试（OCR 循环轮次 1 根因修复配套）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk` 函数 | 15 | 47 | — |
| `TestPatterns` 类 | 22 | 1 | — |
| `test_pattern_order_legacy_first` 函数 | 23 | 1 | — |
| `test_layout_in_patterns` 函数 | 27 | 1 | — |
| `TestFind` 类 | 31 | 1 | — |
| `test_finds_legacy_middle` 函数 | 32 | 1 | — |
| `test_finds_layout_cloud_rename` 函数 | 36 | 1 | — |
| `test_finds_bare_middle` 函数 | 42 | 1 | — |
| `test_all_three_coexist_deduped` 函数 | 46 | 1 | — |
| `test_legacy_first_when_both` 函数 | 52 | 1 | — |
| `test_empty_or_missing_root` 函数 | 57 | 1 | — |
| `test_sorted_within_pattern` 函数 | 61 | 1 | — |
| `test_iter_yields_same_as_find` 函数 | 67 | 1 | — |
| `test_nested_depth` 函数 | 71 | 1 | — |
| `test_non_json_ignored` 函数 | 75 | 1 | — |
| `test_finds_mineru40_middle_json` 函数 | 80 | 1 | 4.0 的产物名 `middle_json.json` 必须被识别。 |
| `test_finds_stemmed_middle_json` 函数 | 90 | 1 | — |
| `test_legacy_preferred_over_40_when_both` 函数 | 94 | 1 | — |

### `tests/test_middle_schema.py`（37 个符号）

> middle_schema 契约测试（MinerU 4.0 结构变更根因修复配套，2026-10-07）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mj34` 函数 | 24 | 5 | — |
| `_mj40` 函数 | 31 | 16 | 一本最小但要覆盖各块型的 MinerU 4.0 产物。 |
| `TestDetect` 类 | 79 | 1 | — |
| `test_detects_34` 函数 | 80 | 1 | — |
| `test_detects_40` 函数 | 83 | 1 | — |
| `test_pdf_info_wins_when_both` 函数 | 86 | 1 | — |
| `test_unknown_shape_raises` 函数 | 91 | 3 | — |
| `test_non_dict_raises` 函数 | 95 | 1 | — |
| `test_empty_object_raises` 函数 | 99 | 1 | — |
| `TestNormalize34` 类 | 104 | 1 | — |
| `test_identity_same_object` 函数 | 105 | 1 | — |
| `test_no_mutation_of_input` 函数 | 109 | 1 | — |
| `TestConvert40` 类 | 116 | 2 | — |
| `test_root_key_is_pdf_info` 函数 | 117 | 1 | — |
| `test_page_size_from_docvortex_layout` 函数 | 122 | 1 | — |
| `test_discarded_blocks_excluded_from_para_blocks` 函数 | 126 | 1 | — |
| `test_title_types_mapped` 函数 | 132 | 1 | — |
| `test_inline_equation_kept` 函数 | 137 | 1 | — |
| `test_standalone_equation_block` 函数 | 146 | 1 | — |
| `test_nested_content_flattened` 函数 | 152 | 1 | — |
| `test_table_caption_and_html` 函数 | 159 | 1 | — |
| `test_image_body_path` 函数 | 166 | 1 | — |
| `test_chart_caption_kept` 函数 | 172 | 1 | — |
| `test_empty_pages_ok` 函数 | 177 | 1 | — |
| `test_missing_docvortex_falls_back` 函数 | 181 | 1 | — |
| `TestLoadJson` 类 | 186 | 1 | — |
| `test_reads_and_normalizes_40` 函数 | 187 | 1 | — |
| `test_missing_file_raises` 函数 | 192 | 1 | — |
| `test_bad_json_raises` 函数 | 196 | 1 | — |
| `test_unknown_shape_raises` 函数 | 202 | 3 | — |
| `TestGuard` 类 | 209 | 2 | **本修复的验收路径**：4.0 能被消费，未知结构大声报错（不静默返回空）。 |
| `test_load_middle_items_consumes_40` 函数 | 212 | 1 | — |
| `test_load_middle_items_splits_40_into_clauses` 函数 | 221 | 1 | — |
| `test_load_middle_items_raises_not_silent` 函数 | 233 | 2 | 未知结构必须**抛**，不许像修复前那样 `mj.get("pdf_info", \[\])` 静默给空。 |
| `test_cloud_guard_accepts_40` 函数 | 241 | 1 | — |
| `test_cloud_guard_rejects_unknown` 函数 | 247 | 1 | — |
| `test_cloud_guard_rejects_empty_pdf_info` 函数 | 254 | 1 | — |

### `tests/test_mineru_channel.py`（12 个符号）

> 深度解析通道选择测试（2026-09-08 用户修订：云优先 → 本地兜底）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `stub` 函数 | 22 | 31 | 打桩四件事：本地可用性 / 云可用性 / 云提交 / 本地提交。 |
| `_run` 函数 | 72 | 73 | — |
| `test_no_cloud_key_goes_local_only` 函数 | 78 | 1 | 未配置云 Key → 纯本地，绝不触云。 |
| `test_cloud_key_prefers_cloud` 函数 | 86 | 1 | 配置了云 Key → 云优先（本地不被调用）。 |
| `test_cloud_failure_falls_back_to_local` 函数 | 93 | 1 | 云失败 → 本地兜底。 |
| `test_cloud_disabled_env_forces_local` 函数 | 101 | 1 | KS_MINERU_CLOUD=0 → 显式禁用云（即使 Key 已配置）。 |
| `test_cloud_fail_and_local_disabled_returns_none` 函数 | 109 | 1 | KS_MINERU_LOCAL=0 且云失败 → 无更多通道（None），不抛异常。 |
| `test_deep_disabled_skips_everything` 函数 | 117 | 1 | KS_MINERU_DEEP=0 → 整体跳过（云与本地都不触）。 |
| `test_local_failure_after_cloud_failure_returns_none` 函数 | 124 | 1 | 云失败 + 本地也失败 → None（不抛出，入库继续走文本层降级）。 |
| `test_cloud_silent_none_falls_back_to_local` 函数 | 132 | 1 | P0 门禁（verifier F1）：云解析**返回 None**（网络/超时/HTTP 类失败的真实。 |
| `test_cloud_none_and_local_disabled_returns_none` 函数 | 142 | 1 | 云返回 None + KS_MINERU_LOCAL=0 → 无更多通道（None），不抛异常。 |
| `test_cloud_and_local_both_disabled_returns_none` 函数 | 150 | 1 | KS_MINERU_CLOUD=0 + KS_MINERU_LOCAL=0 → 两通道皆关（calls 为空、返回 None）。 |

### `tests/test_mineru_cloud.py`（28 个符号）

> 云解析后端（mineru_cloud）单测：schema 守卫、归一化落位、zip-slip 防护、分发链。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_env_only_credentials` 函数 | 19 | 1 | 凭据只从环境变量读（屏蔽 HKCU 注册表回退），且 settings 不跨用例缓存。 |
| `_ok_middle` 函数 | 40 | 5 | — |
| `test_validate_middle_passes` 函数 | 46 | 1 | — |
| `test_validate_middle_rejects_bad_json` 函数 | 52 | 1 | — |
| `test_validate_middle_rejects_missing_pdf_info` 函数 | 64 | 1 | — |
| `test_validate_middle_rejects_empty_pages` 函数 | 71 | 1 | — |
| `test_validate_middle_rejects_missing_page_idx` 函数 | 78 | 1 | — |
| `test_normalize_landing_copies_and_prefixes` 函数 | 86 | 1 | — |
| `test_normalize_landing_keeps_existing_prefix` 函数 | 100 | 1 | — |
| `test_normalize_landing_no_middle_raises` 函数 | 111 | 1 | — |
| `test_safe_extract_rejects_zip_slip` 函数 | 119 | 1 | — |
| `test_safe_extract_normal` 函数 | 129 | 1 | — |
| `test_available_false_without_key` 函数 | 140 | 1 | — |
| `test_submit_and_wait_end_to_end` 函数 | 149 | 1 | — |
| `test_submit_and_wait_guard_failure_raises` 函数 | 204 | 1 | — |
| `test_submit_and_wait_network_failure_returns_none` 函数 | 228 | 1 | — |
| `test_probe_token_ok` 函数 | 245 | 1 | — |
| `test_probe_token_bad_auth` 函数 | 266 | 1 | — |
| `test_adapter_uses_cloud_when_local_missing` 函数 | 281 | 1 | 本地未装 MinerU + 配了云 Key → 走云兜底（产物路径透传）。 |
| `test_adapter_no_local_no_key_returns_none` 函数 | 297 | 1 | — |
| `test_adapter_no_key_uses_local_and_skips_cloud` 函数 | 307 | 1 | 未配置云 Key → 纯本地，云绝不被调用（2026-09-08 修订后语义）。 |
| `test_adapter_ks_mineru_local_zero_forces_cloud` 函数 | 334 | 1 | KS_MINERU_LOCAL=0（用户机器跑不动）→ 即使本地装了也直接走云。 |
| `test_egress_recorded_when_guard_fails_after_upload` 函数 | 351 | 1 | P0 门禁（verifier F2）：PDF 字节已外发后产物守卫失败 → 仍登记外发审计。 |
| `test_egress_recorded_when_poll_fails_after_upload` 函数 | 380 | 1 | 上传成功但轮询超时（网络类失败 → 返回 None）同样必须留审计。 |
| `test_429_backs_off_and_retries_once` 函数 | 405 | 1 | **限流 429 要原地退避重试一次**，而不是直接当网络失败返回 None。 |
| `test_429_backoff_is_not_infinite` 函数 | 454 | 1 | **429 持续存在时不许无限重试**——退避一次后仍失败就返回 None（交上层换 key）。 |
| `test_non_429_network_error_does_not_backoff` 函数 | 486 | 1 | **反向对照：非 429 的网络错误不许退避**（它们不是速率问题，退避无益且白等）。 |
| `test_explicit_api_key_overrides_global` 函数 | 517 | 1 | **显式 `api_key` 必须覆盖全局 settings 的 key**（竞态治本的关键）。 |

### `tests/test_mineru_cloud_mode.py`（18 个符号）

> MinerU 云解析「模式」设置项契约测试（2026-09-15 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean_env` 函数 | 23 | 5 | 清掉 env 覆盖，保证读写只看存储。 |
| `TestReadNormalization` 类 | 31 | 1 | — |
| `test_default_is_pipeline` 函数 | 32 | 1 | — |
| `test_case_insensitive` 函数 | 36 | 1 | — |
| `test_illegal_falls_back` 函数 | 40 | 1 | — |
| `test_vm_html_kept` 函数 | 44 | 1 | — |
| `TestWriteValidation` 类 | 49 | 1 | — |
| `test_illegal_raises` 函数 | 50 | 1 | — |
| `test_llm_channel_rejects_mode` 函数 | 54 | 1 | — |
| `test_unknown_channel_rejected` 函数 | 58 | 3 | — |
| `TestStatusExposure` 类 | 63 | 1 | — |
| `test_status_has_mode_and_choices` 函数 | 64 | 1 | — |
| `TestRequestBody` 类 | 72 | 1 | 本改动的核心断言：云请求体真的带上了所选模式。 |
| `_capture` 函数 | 75 | 5 | — |
| `test_upload_url_body_carries_vlm` 函数 | 104 | 1 | — |
| `test_upload_url_body_carries_pipeline` 函数 | 110 | 1 | — |
| `test_model_version_helper_reads_settings` 函数 | 114 | 1 | — |
| `test_model_version_helper_sanitizes` 函数 | 123 | 1 | — |

### `tests/test_mineru_gpu_lock.py`（4 个符号）

> GPU 深度解析排队锁（_gpu_deep_lock）行为测试。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_lock_env` 函数 | 18 | 1 | — |
| `test_gpu_lock_互斥_第二持锁者等待期间抢不到` 函数 | 24 | 0 | — |
| `test_gpu_lock_释放后_可再次获取` 函数 | 33 | 0 | — |
| `test_gpu_lock_禁用开关_KS_GPU_LOCK_0_直通` 函数 | 40 | 0 | — |

### `tests/test_modality_window_false_positive.py`（3 个符号）

> 核验器模态窗口误报 —— 判据（2026-10-19）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_correct_keke_not_reported_as_strengthened` 函数 | 86 | 1 | 模型正确复述「可」时，不许报 strengthened（2026-10-19 真机误报）。 |
| `test_real_weakened_still_intercepted` 函数 | 106 | 1 | 真问题必须还在：把「不应」写成「应」时，仍要拦截。 |
| `test_correct_buneng_passes` 函数 | 118 | 1 | 模型正确保留「不应」时，不许误报。 |

### `tests/test_models_dir_override.py`（5 个符号）

> `KS_MODELS_DIR` 覆盖：模型缓存可重定向，且**只**重定向模型缓存。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_models_dir_defaults_inside_the_bundle` 函数 | 26 | 1 | ⚠ 2026-10-18 契约变更：默认从 `<data_dir>/models` 改成**包内**。 |
| `test_models_dir_does_not_follow_data_dir_anymore` 函数 | 38 | 1 | 反向钉子：换 `KS_DATA_DIR` **不再**带着模型目录跑。 |
| `test_models_dir_honours_override` 函数 | 49 | 1 | — |
| `test_models_override_does_not_move_data_or_db` 函数 | 56 | 1 | — |
| `test_models_override_dir_is_created_by_ensure_dirs` 函数 | 65 | 1 | — |

### `tests/test_naming_convention_scanner.py`（10 个符号）

> `scripts/docs/scan-rename-targets.py`（命名规范机械扫描器）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 29 | 125 | — |
| `test_tracked_files_returns_real_paths_not_escaped` 函数 | 41 | 1 | 非 ASCII 路径必须是**真路径**，不能是 `\345\271\277` 这种八进制转义。 |
| `test_non_ascii_paths_survive_round_trip` 函数 | 55 | 1 | 带中文的路径必须是**真路径**（转义形态 `\345\271\277` 必然不是）。 |
| `test_govqa_data_dir_is_excluded` 函数 | 83 | 2 | 采集数据目录必须被剪掉——它由另一个自动化拥有，不归本命名规范管。 |
| `test_code_files_are_not_flagged_for_underscores` 函数 | 92 | 1 | **R3 的核心**：Python 的 `snake_case.py` 是**正确写法**，不是违规。 |
| `test_current_tree_has_zero_violations` 函数 | 102 | 2 | 当前树必须零违规——这是这条规范**已经被执行过**的机械证据。 |
| `test_scanner_has_teeth_on_doc_filename` 函数 | 108 | 1 | **变异验证（R1 有牙）**：`foo_bar.md` 必须被判违规，`foo-bar.md` 必须放过。 |
| `test_code_filenames_are_exempt_from_R1` 函数 | 122 | 1 | **R1 的边界**：`snake_case.py` **不许**被判违规（这是 v1 被推翻的直接原因）。 |
| `test_scanner_has_teeth_on_dir_name` 函数 | 129 | 1 | **变异验证（R2 有牙）**：含大写的目录名必须被判违规，全小写必须放过。 |
| `test_skip_dir_check_handles_nested_and_prefix_paths` 函数 | 140 | 1 | 剪枝判据本身要正确：嵌套目录要剪、正常文档不能误剪。 |

### `tests/test_normalize_std_slash.py`（11 个符号）

> 存量全角斜杠回填脚本的用例（`scripts/normalize-standard-no-slash.py`，§11.0 R6c-2c/2d）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `mod` 函数 | 27 | 299 | — |
| `_db` 函数 | 35 | 11 | 最小 doc_meta。 |
| `test_普通行会被归一` 函数 | 49 | 0 | — |
| `test_与已存在的行撞车必须跳过` 函数 | 61 | 0 | 同一标准的两个文件：一条已是半角、一条是全角 ⇒ 全角那条要**跳过**（不制造重复）。 |
| `test_计划内自撞也要跳过` 函数 | 74 | 0 | ⚠ 复核 b32 的 4.4：两行全角、归一到**同一个尚不存在**的目标。 |
| `test_清单内列与目标值不重复` 函数 | 93 | 0 | 清单级断言（上面那条是行为级）——防以后改坏判重逻辑。 |
| `test_没有全角就不产生变更` 函数 | 102 | 0 | — |
| `test_standard_name_里的全角也归一` 函数 | 107 | 0 | — |
| `Test单事务语义` 类 | 113 | 0 | 复核 b32 的 4.5：中断要回滚，且"写后核对"不能读未提交状态。 |
| `test_中断会回滚` 函数 | 116 | 0 | `write_transaction` 必须对 `BaseException` 也回滚。 |
| `test_同进程第二次调用不炸` 函数 | 134 | 0 | 旧代码 `conn2.close()` 会把线程局部共享连接关掉 ⇒ 第二次 `ProgrammingError`。 |

### `tests/test_ocr_regression_fixtures.py`（32 个符号）

> 0b · 9 历史文档 OCR 错误回归 fixture（执行计划 v3 阶段 0b，2026-09-14）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestLeqslantLeak` 类 | 36 | 1 | — |
| `test_positive_clean` 函数 | 37 | 1 | 修复形态：泄漏形态归一到 ≤。 |
| `test_negative_leaked_form` 函数 | 41 | 1 | 负向：清洗产物不得含 ≤slant / ≥slant。 |
| `test_eq_tag_path` 函数 | 47 | 1 | 行内公式 <eq>…</eq> 全链路同样不泄漏（入库路径）。 |
| `TestWideSpacedDigits` 类 | 57 | 1 | — |
| `test_property_digit_glue` 函数 | 58 | 1 | 性质：数字间单空格形态应被粘合（宽字距还原）。 |
| `TestPuaNormalize` 类 | 71 | 1 | — |
| `test_positive_recover` 函数 | 72 | 1 | 修复形态：犬部+数字平移整体还原。 |
| `test_property_no_pua_residue` 函数 | 78 | 1 | 性质：任何 PUA 输入归一化后无犬部码位残留。 |
| `test_positive_sqrt_body` 函数 | 85 | 1 | 修复形态：根号 PUA 替身 '槡' → '√'（34406 公式区实测）。 |
| `test_property_ascii_digits_restored` 函数 | 89 | 1 | 性质：0x21-0x2A 平移区字符全部还原为数字（无一漏网）。 |
| `TestAreaSubscript` 类 | 101 | 1 | — |
| `test_positive_sub` 函数 | 102 | 1 | 修复形态：面积判据（>数值）下 A° → Aₑ。 |
| `test_positive_area_context` 函数 | 108 | 1 | 修复形态：'有效散热面积'上下文同样转换。 |
| `test_negative_angle_untouched` 函数 | 114 | 1 | 负向（防误伤）：无面积判据的角度 A° 不转。 |
| `TestChemBondDash` 类 | 124 | 1 | — |
| `test_positive_bond` 函数 | 125 | 1 | 修复形态：PUA 键 → em dash。 |
| `test_negative_no_raw_pua` 函数 | 131 | 1 | 负向：键线产物不得残留  原码位。 |
| `TestMeaningMarks` 类 | 141 | 1 | — |
| `test_positive_hat_bar` 函数 | 142 | 1 | — |
| `TestWatermarkStrip` 类 | 155 | 1 | — |
| `test_positive_wm_url_gone` 函数 | 156 | 1 | — |
| `test_negative_inline_url_untouched` 函数 | 160 | 1 | 负向（防误伤）：行中合法 URL 引用不剥（仅整行水印语义才剥）。 |
| `test_property_pageno_forms_covered` 函数 | 166 | 1 | 性质：全角/罗马页码形态剥后不留。 |
| `TestSymbolTable2026Additions` 类 | 176 | 1 | — |
| `test_symbols_present` 函数 | 182 | 1 | 正向：24276 实测缺漏的符号全部可转换。 |
| `test_property_word_boundary_no_eat` 函数 | 186 | 1 | 性质：词边界防前缀误吃（\pm 不吃 \pmb。 |
| `test_long_key_priority` 函数 | 190 | 1 | 性质：长键优先（\leqslant 先于 \leq，否则被前缀吞掉）。 |
| `TestShiftedDigitGuard` 类 | 201 | 1 | — |
| `test_negative_normal_text_not_mangled` 函数 | 205 | 1 | 负向（防误伤核心）：正常文本（正常标点 + 正常数字占比）判 False。 |
| `test_positive_shifted_digits_detected` 函数 | 211 | 1 | 正向：真数字平移型（!-* 密集 + 正常数字≈0）仍判 True。 |
| `test_property_digit_ratio_gate` 函数 | 218 | 1 | 性质：判据二的数字占比门槛——含足量正常数字的文本不触发整体平移判定。 |

### `tests/test_patch_guard.py`（7 个符号）

> 纠错补丁防乱检测（patch guard）测试，2026-08-23 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_ok_minor_fix` 函数 | 9 | 1 | 正常 OCR 纠错（局部小改）→ ok。 |
| `test_reject_unrelated_paste` 函数 | 16 | 1 | 贴完全无关内容 → reject。 |
| `test_reject_garbage` 函数 | 23 | 1 | 大量不可打印字符（乱码/二进制）→ reject。 |
| `test_warning_length_grow` 函数 | 30 | 1 | 长度暴增 3 倍以上 → warning（疑似贴了多余内容）。 |
| `test_warning_length_shrink` 函数 | 38 | 1 | 长度骤减到 1/3 以下 → warning（疑似误删大段）。 |
| `test_warning_language_shift` 函数 | 46 | 1 | 中文占比骤降（贴英文代码）→ warning。 |
| `test_short_original_skips_similarity` 函数 | 53 | 1 | 原文太短（<12 字）跳过相似度检查。 |

### `tests/test_patch_migration.py`（7 个符号）

> Task 10.4 补丁跨修订平移测试：(a)平移 (b)冲突入队 (c)孤儿入队 + content_hash 回填。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_uniq` 函数 | 9 | 27 | — |
| `_mk_doc` 函数 | 13 | 31 | — |
| `_mk_clause` 函数 | 24 | 16 | — |
| `test_migrate_patches_three_branches` 函数 | 37 | 1 | — |
| `test_content_hash_backfill` 函数 | 82 | 1 | content_hash 列迁移 + 存量回填（幂等）。 |
| `test_content_hash_on_insert` 函数 | 102 | 1 | — |
| `test_migrate_patches_api` 函数 | 119 | 1 | — |

### `tests/test_patches.py`（12 个符号）

> 阶段2.1 纠错补丁机制测试（外部评审响应）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `seeded` 函数 | 6 | 40 | 一条可打补丁的条款（幂等：清掉本测试的历史数据再建）。 |
| `test_patch_overlay_and_immutability` 函数 | 30 | 1 | — |
| `test_patch_fts_resync` 函数 | 52 | 1 | — |
| `test_patch_rollback` 函数 | 63 | 1 | — |
| `test_patch_upsert_overrides` 函数 | 73 | 1 | — |
| `test_patch_validation` 函数 | 88 | 1 | — |
| `test_patch_audit_log` 函数 | 99 | 1 | — |
| `test_patch_api_crud` 函数 | 109 | 1 | — |
| `test_content_markdown_patch_drives_table_md` 函数 | 143 | 1 | 表格修改必须落 content_markdown 补丁 → 卡片/检索读的 table_md 立即生效。 |
| `test_rich_html_patch_roundtrip` 函数 | 168 | 1 | 富文本补丁（上下标/加粗/表格 → content_markdown）必须被 _content_html 完整返回。 |
| `test_content_html_joins_ocr_wraps` 函数 | 196 | 1 | _content_html 对旧数据（正文含 OCR 折行）必须先拼折行再转 <p>——否则卡片出现多余回车。 |
| `test_patch_guard_fail_closed_on_exception` 函数 | 228 | 1 | 防乱检测内部异常时必须 fail-closed：422 拒绝且不落库，绝不 fail-open 放行脏补丁。 |

### `tests/test_phase10_blindspots.py`（8 个符号）

> Task 10.6 P1 测试盲区补齐：R3 表格保真 / R47 质量复核 / R62 特殊字符 / R71 多栏 / R55 引用完整 / R-L2 效力层级。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_uniq` 函数 | 9 | 27 | — |
| `_seed` 函数 | 13 | 20 | — |
| `test_r3_table_fidelity` 函数 | 28 | 1 | R3 表格/公式保真：content_markdown 表格与 table_summary 落库不丢失。 |
| `test_r47_quality_review_flag` 函数 | 47 | 1 | R47 质量评分/待复核：is_suspicious 标记 + 纠错联动转可信。 |
| `test_r62_special_chars` 函数 | 66 | 1 | R62 特殊字符保真：℃/≥/m² 等入库不被破坏。 |
| `test_r71_multi_column_order` 函数 | 84 | 1 | R71 多栏验证：MinerU 阅读顺序块按页序稳定输出（load_middle_items 顺序保持）。 |
| `test_r55_reference_integrity` 函数 | 105 | 1 | R55 引用完整性：cross_refs 引用应能解析到库内存在条款。 |
| `test_rl2_effectiveness_ranking` 函数 | 132 | 1 | R-L2 效力层级排序：法律效力高的文档条款应排前（rank_with_hierarchy）。 |

### `tests/test_phase12.py`（4 个符号）

> Phase 12 测试：Office 往返 / 双向溯源 / 批量问答。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_seed_clause` 函数 | 6 | 4 | — |
| `test_office_roundtrip_full_cycle` 函数 | 26 | 1 | 12.1：创建会话 → 模拟编辑（改写 docx）→ 轮询检出 → 提交落库 → 撤销/清理。 |
| `test_backlinks` 函数 | 82 | 1 | 12.2：条款被 收藏/义务清单/审查点 引用时全量召回。 |
| `test_phase12_api` 函数 | 100 | 1 | — |

### `tests/test_phase13_blindspots.py`（4 个符号）

> Task 13.3 盲区补齐（免费路径 4 项）：R13 质量分级 / R44 离线开关 / R59 覆盖范围 / R67 过渡期。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_r13_quality_grade_tag` 函数 | 6 | 1 | R13 质量分级标签：doc_meta.quality_grade 落库与校验约束。 |
| `test_r44_offline_flag_exists` 函数 | 23 | 1 | R44 离线模式：app_config 离线开关存在性与默认值（功能隐藏由前端门控）。 |
| `test_r59_coverage_mode_switch` 函数 | 35 | 1 | R59 覆盖范围模式：include_superseded 开关影响检索时效过滤。 |
| `test_r67_transition_both_valid` 函数 | 62 | 1 | R67 过渡期并行有效：upcoming 与 effective 文档同时存在时不互斥。 |

### `tests/test_phase4.py`（10 个符号）

> 阶段4 "能用"档测试：收藏/批注/项目/义务清单/导出/目录树/检索加权。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `rich_db` 函数 | 6 | 9 | 种入两部文档条款（一部现行、一部即将实施）供各功能测试。 |
| `test_bookmark_crud_and_boost` 函数 | 44 | 1 | — |
| `test_annotation_crud` 函数 | 69 | 1 | — |
| `test_project_crud` 函数 | 78 | 1 | — |
| `test_document_tree` 函数 | 90 | 1 | — |
| `test_clauses_by_prefix` 函数 | 111 | 1 | 目录展开 API：前缀查子条款（点 ▸ 懒加载该标题下所有条款，2026-08-23 新增）。 |
| `test_exports` 函数 | 131 | 1 | R19 引用块（**纯文本**）。 |
| `test_export_download_guard` 函数 | 146 | 1 | — |
| `test_sse_time_warnings_and_enrichment` 函数 | 156 | 1 | 证据事件应带时效警示（upcoming 文档）与收藏/置信度富化字段。 |
| `test_doc_bookmark_crud` 函数 | 178 | 1 | 标准级书签（user_doc_bookmark）：幂等、列表带 doc_meta、按 id/doc 删除、。 |

### `tests/test_phase5.py`（7 个符号）

> Phase 5 测试：多轮对话（R60）/ 追问增强（R9）/ 核验器窗口并集 / 答案置信度（R24）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_build_messages_history_order_and_cap` 函数 | 12 | 1 | — |
| `test_build_messages_truncates_long_history` 函数 | 32 | 1 | — |
| `test_expand_query_with_history` 函数 | 42 | 1 | — |
| `test_modality_window_union_fixes_false_positive` 函数 | 59 | 1 | 4.10 场景：条款号两次出现，首个窗口无模态词，第二窗口含"不应"。 |
| `test_modality_weakened_still_caught_with_union` 函数 | 75 | 1 | 窗口并集后，真实减弱（应→宜）仍必须拦截。 |
| `test_sse_accepts_history_and_confidence` 函数 | 89 | 1 | — |
| `test_llm_history_forwarded_with_mock` 函数 | 109 | 1 | mock LLM：确认 history 真正传到流式客户端（不真调 API）。 |

### `tests/test_phase6.py`（18 个符号）

> Phase 6 测试：版本替代链（R29）/ 条款对照与模态变化（R42/R49）/

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `version_db` 函数 | 7 | 12 | 三部文档：旧版(已废止)→现行→即将实施 链 + 模态变化条款。 |
| `test_version_chain` 函数 | 55 | 1 | — |
| `test_compare_docs_with_modality_change` 函数 | 62 | 1 | — |
| `test_compare_added_removed` 函数 | 74 | 1 | — |
| `test_compare_removed_lists_only_truly_absent` 函数 | 85 | 1 | 反向对照：新版→旧版时只列出「新版有而旧版无」的条款。 |
| `test_compare_paired_and_removed_are_disjoint` 函数 | 97 | 1 | 不变量：任何被 paired 的条款号都不得出现在 removed 里。 |
| `test_cross_doc_compare_same_key` 函数 | 111 | 1 | R16 跨标准：相同 clause_key 的条款可对照（不同标准号）。 |
| `test_operation_log_after_ingest` 函数 | 120 | 1 | R8：真实入库路径应写 operation_log（走 law_text 直灌）。 |
| `test_operation_log_api` 函数 | 133 | 1 | R8/R11：时间线 API 聚合 operation_log + event_log。 |
| `test_alias_extract_and_expand` 函数 | 149 | 1 | — |
| `test_alias_two_line_format` 函数 | 166 | 1 | GB 风格：术语行 + 下一行定义（无冒号）。 |
| `test_alias_three_line_format` 函数 | 181 | 1 | MinerU 三行式：编号行 / 术语行 / 定义行。 |
| `test_alias_endpoint` 函数 | 198 | 1 | — |
| `test_alias_does_not_extract_foreword_or_toc` 函数 | 222 | 1 | **前言/目录不许被当成术语抽走**（2026-10-10 实测缺陷的回归判据）。 |
| `test_alias_section_span_requires_a_real_boundary` 函数 | 272 | 1 | 区间定位的**边界语义**：`3.1 动火作业：…` 是术语条目，**不是**章节边界。 |
| `test_alias_no_span_means_no_extraction` 函数 | 288 | 1 | **区间定位不到 ⇒ 一条都不抽**（2026-10-10 实测缺陷的回归判据）。 |
| `test_alias_does_not_sliding_window_long_definitions` 函数 | 324 | 1 | **散文式长定义不许被滑窗切成碎片**（2026-10-10 实测缺陷的回归判据）。 |
| `test_alias_expand_ignores_dirty_aliases` 函数 | 378 | 1 | `expand_with_alias` 不许把**脏别名**并进查询（现有防御的判据）。 |

### `tests/test_phase7.py`（7 个符号）

> Phase 7 测试：差距分析（R-L11~13）/ 义务导出（R-L10）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `gap_db` 函数 | 6 | 8 | 种入义务条款（应当型，两个领域）+ 一份覆盖一半义务的制度。 |
| `test_import_policy_sections` 函数 | 50 | 1 | — |
| `test_build_obligations` 函数 | 57 | 1 | — |
| `test_gap_analysis_verdicts` 函数 | 65 | 1 | — |
| `test_gap_analysis_red_when_no_coverage` 函数 | 82 | 1 | — |
| `test_gap_api_flow` 函数 | 93 | 1 | — |
| `test_export_citations_body_contract` 函数 | 113 | 1 | `POST /export/citations` 的 **HTTP 层**契约（§10.76）。 |

### `tests/test_phase8.py`（4 个符号）

> Phase 8 测试：健康看板 / Debug Trace / session 文件 / 一键启动相关。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_health_board` 函数 | 7 | 1 | — |
| `test_debug_trace_recorded_by_default` 函数 | 18 | 1 | P9.4：每次提问默认落 Debug Trace，含各阶段 trace 数据，无需显式参数。 |
| `test_debug_trace_clarify_recorded` 函数 | 42 | 1 | R9 v2：追问由 LLM 单次自判。 |
| `test_session_file_written` 函数 | 61 | 1 | 引擎 run() 应写 engine.session.json（用 create_app 前先验证函数存在性）。 |

### `tests/test_pipeline.py`（21 个符号）

> T05 管线测试：切分/分型/边/坐标翻转（合成 fixture）+ 真实 middle.json 集成。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_middle` 函数 | 42 | 4 | 合成一份 2 页 middle.json：封面/前言 + 2 条款(跨页拼接) + 但书 + 表绑定 + 附录。 |
| `test_load_middle_items_drops_discarded` 函数 | 84 | 1 | — |
| `test_split_clauses_and_table_binding` 函数 | 94 | 1 | — |
| `test_split_rejects_table_value_clause_heads` 函数 | 107 | 1 | E8 表格数值防误判（2026-08-28 生产实测）：成分表数据行不得切成 0.x/伪章号条款。 |
| `test_pua_detector_catches_cid_garbage_without_pua_glyphs` 函数 | 135 | 1 | E9 cid 乱码变体（2026-08-28 GB/T 20529.2-2010 实测）：文本层不含。 |
| `test_pua_detector_catches_ascii_mapped_garbage` 函数 | 147 | 1 | E9b 判据四：cid 错位第四形态——汉字被映射为 ASCII（GB/T 35210.1-2023。 |
| `TestNonChineseTextIsNotMangled` 类 | 161 | 1 | **非中文文档不许被判成 PUA 乱码**（2026-09-25 修 P0.11）。 |
| `test_english_paper_text_is_not_mangled` 函数 | 188 | 1 | — |
| `test_garbled_ascii_mapped_chinese_is_still_mangled` 函数 | 194 | 1 | 对照：**原来的真乱码案例仍须判中**（别为了修误伤把这条判据废掉）。 |
| `test_the_two_signals_separate_english_from_garbled_ascii` 函数 | 201 | 1 | 把判据背后的**两个量**单独钉住（这样以后谁改了阈值，能看出动的是哪一条）。 |
| `TestLatinProseThresholdIsAnchored` 类 | 208 | 2 | **阈值 0.70 不许是拍的**（2026-09-25 复核 P-2 打回后补，第 2 轮又被打回后重写）。 |
| `test_real_english_excerpt_stays_above_both_thresholds` 函数 | 265 | 1 | 活锚：真语料里较难的一段，两个量都还高过阈值**且留有余量**。 |
| `test_thresholds_sit_inside_the_measured_gap` 函数 | 277 | 1 | 阈值不许贴住真英文下界（这一条杀"改严"：0.70→0.90 就死在这里）。 |
| `test_every_repo_garbled_fixture_is_still_caught` 函数 | 288 | 1 | **行为不变量**：仓里每一条乱码夹具都必须仍被判中（这一条杀"改宽"）。 |
| `test_letter_ratio_side_has_no_repo_fixture_lower_bound` 函数 | 318 | 2 | **诚实登记**：字母/标点那一侧的**下界在本仓钉不住**——别假装钉住了。 |
| `test_delete_document_uses_bulk_fts_delete` 函数 | 351 | 1 | E10 性能根因（2026-08-28 试点实测）：clause_fts.clause_revision_id 是。 |
| `test_build_models_classification_and_edges` 函数 | 398 | 1 | — |
| `test_classifier_details` 函数 | 418 | 1 | — |
| `test_real_middle_json_integration` 函数 | 431 | 1 | — |
| `test_interline_equation_restored` 函数 | 442 | 1 | 2026-09-01 独立公式行（interline_equation）不再蒸发（GB/T 24276。 |
| `test_resolve_edges_reports_unresolved` 函数 | 476 | 1 | 未解析引用必须留痕（iteration-6 自查 §8.2，代码级核实）。 |

### `tests/test_pool_depth_ruler.py`（27 个符号）

> exp-15 池深 × 融合方式尺子（`eval/recall-funnel/exp-15-pool-depth-fusion/run.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 56 | 125 | — |
| `_deep` 函数 | 69 | 5 | — |
| `test_exact_and_modality_are_never_truncated` 函数 | 76 | 2 | ★ 每一条臂里 `exact`/`modality` 都必须**原样全量**（唯一变量只有 fts/vec 的池深）。 |
| `test_a0_prod_replicates_production_caps` 函数 | 85 | 2 | ★ A0_prod = 生产：fts/vec 各 20 条（它是仪器对照臂，不许漂）。 |
| `test_pool_depth_arms_take_declared_depth` 函数 | 93 | 1 | ★ 池深臂按各自声明取数（100 / 1000）。 |
| `test_take_doc_diverse_caps_per_doc_and_budget` 函数 | 103 | 2 | ★ 每篇文档最多 `per_doc` 条、总数不超过 `budget`，且**保序**。 |
| `test_take_doc_diverse_skips_unknown_docs` 函数 | 113 | 2 | ★ 查不到文档的 id 必须跳过（与生产 `fetch_full_clause` 取不到就跳过同向）。 |
| `test_doc3_arm_uses_doc_diverse_not_plain_truncation` 函数 | 118 | 1 | ★ `P1000_doc3` 的 fts/vec 必须走**文档去重**（预算 20），不是简单取前 20。 |
| `test_oracle_pool_is_union_then_truncate_per_channel` 函数 | 134 | 2 | ★ oracle 池 = `exact ∪ modality ∪ fts\[:d\] ∪ vec\[:d\]`（**逐路截断**再并集）。 |
| `_mk_items` 函数 | 144 | 19 | — |
| `_mk_runs` 函数 | 150 | 18 | `ranks` = **rank20**（top-20 名单里的名次）。 |
| `_ranks` 函数 | 183 | 14 | — |
| `_mk_legacy_runs` 函数 | 187 | 2 | 造**旧形状**台账（第 15 轮初版）：`arms\[臂\]` 只有 `rank` + `hit@100`，**没有** `rank100/rank1000`。 |
| `test_hit_rate_is_inclusive_at_boundary` 函数 | 204 | 2 | ★ 名次恰等于 20 算命中。 |
| `test_flip_and_delta_direction` 函数 | 213 | 2 | ★ 非对称样本上 `(翻进 b, 翻出 c)` 与 Δ 的方向：净改善必须读成正 Δ。 |
| `test_missing_item_raises` 函数 | 226 | 2 | ★ 缺一条必须抛错，不许静默补 0（补 0 会让 @20 的分母错而读数看不出来）。 |
| `test_oracle_aggregation_counts_booleans` 函数 | 238 | 1 | ★ oracle 聚合必须数 `True` 的比例（写成数非空会让它恒 100%）。 |
| `test_instrument_check_counts_identical` 函数 | 247 | 1 | ★ 仪器对照读数必须数 `check_identical`（它不是装饰，是整批作废的开关）。 |
| `test_pool_median_definition_is_pinned` 函数 | 257 | 3 | ★ `pool_median` 取**上中位** `sorted\[n//2\]`：排序后 \[10,20,30,1000\] ⇒ 30（≠ 下中位 20）。 |
| `test_fused_hit_n_and_median_are_defined_on_top20` 函数 | 265 | 2 | ★ `fused_hit_n` / `fused_median_rank` **定义在 @20 上**（与冻结版逐位一致）。 |
| `test_arm_rank_reads_both_ledger_shapes` 函数 | 284 | 2 | ★ `arm_rank()` 必须同时吃**新台账**（`rank20/100/1000`）与**旧台账**（`rank` + `hit@100`）。 |
| `test_top100_and_top1000_are_not_copies_of_top20` 函数 | 296 | 2 | ★ **第 15 轮复核 P1-1 的回归判据**：`@100`/`@1000` 必须用**对应深度的名次**算。 |
| `test_legacy_ledger_reports_only_measured_depths` 函数 | 314 | 2 | ★ **第 15 轮复核 P1-1 的修法判据**：旧台账（只有 `rank` + `hit@100`）下，。 |
| `test_by_subset_top20_partitions_by_label` 函数 | 330 | 1 | ★ `by_subset_top20` 按 label 分组 + 组内闭区间。 |
| `test_production_caps_and_exp7_reuse_points_still_exist` 函数 | 347 | 2 | ★ 生产的两处硬编码上限（A0_prod 复刻的对象）+ exp-7 的复用点必须仍在。 |
| `test_ledger_stores_three_depths_separately` 函数 | 358 | 2 | ★ 台账必须**分别存** `rank20`/`rank100`/`rank1000`（第 15 轮复核 P1-1 的根因锚点）。 |
| `test_stop_loss_preregistered_contract` 函数 | 370 | 2 | ★ 预注册文件必须在，主终点 = `fused@20`，臂表与代码一致。 |

### `tests/test_preview_jobs.py`（24 个符号）

> 异步批量预览（preview_jobs）引擎侧测试——L239 设计的验收网。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_isolate_jobs` 函数 | 21 | 1 | — |
| `_wait_terminal` 函数 | 27 | 12 | 轮询到 terminal（done/aborted/failed）或超时——返回最后一次视图。 |
| `_make_pdf` 函数 | 41 | 38 | 造一个最小可解析 PDF（pypdf/fitz 都能开）。 |
| `TestStateMachine` 类 | 52 | 1 | — |
| `test_create_returns_pending_view_with_total` 函数 | 53 | 1 | — |
| `test_full_run_reaches_done_and_buckets_conserved` 函数 | 62 | 1 | — |
| `test_batch_size_truncates` 函数 | 71 | 1 | — |
| `test_single_file_failure_does_not_break_batch` 函数 | 79 | 1 | — |
| `TestAbort` 类 | 91 | 1 | — |
| `test_abort_on_terminal_is_idempotent_noop` 函数 | 92 | 1 | — |
| `test_abort_running_marks_aborted_keeps_done_rows` 函数 | 100 | 1 | — |
| `TestZombie` 类 | 132 | 1 | — |
| `test_zombie_running_thread_dead_becomes_failed` 函数 | 133 | 1 | 伪造僵尸：直接往任务表塞 status=running + thread_alive=False。 |
| `test_alive_thread_not_zombie` 函数 | 148 | 1 | thread_alive=False 但 thread_ref 活着（正常切换间隙）→ 不误杀。 |
| `TestRetentionPolicy` 类 | 168 | 1 | — |
| `test_prune_keeps_recent_jobs` 函数 | 169 | 1 | — |
| `TestPagination` 类 | 178 | 1 | — |
| `test_rows_pagination` 函数 | 179 | 1 | — |
| `TestConfidenceIsNeverFaked` 类 | 196 | 1 | 识别率"算不出来"在**异步全量预览**里也必须是 `None`，**不是 `0.0`**（2026-09-21 第 5 步复核 R4）。 |
| `test_crashed_item_is_none_not_zero` 函数 | 207 | 1 | — |
| `test_uncomputable_report_keeps_none_and_normal_keeps_number` 函数 | 222 | 1 | — |
| `TestEgressContract` 类 | 249 | 1 | 异步路径的外发口径（2026-09-17 D5）：。 |
| `test_default_job_is_no_egress` 函数 | 257 | 1 | — |
| `test_explicit_optin_reaches_parser_and_is_recorded` 函数 | 279 | 1 | — |

### `tests/test_pua_separators.py`（10 个符号）

> PUA 分隔符还原契约测试（2026-09-15 全库文本审计根因修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `TestSeparatorRestore` 类 | 15 | 1 | — |
| `test_date_separator_becomes_hyphen` 函数 | 16 | 1 | — |
| `test_name_separator_becomes_space` 函数 | 19 | 1 | — |
| `test_value_prefix_separator_becomes_space` 函数 | 22 | 1 | — |
| `test_consecutive_codepoints_all_handled` 函数 | 25 | 1 | — |
| `TestNoRegression` 类 | 30 | 3 | — |
| `test_plain_text_unchanged` 函数 | 31 | 2 | — |
| `test_empty` 函数 | 36 | 4 | — |
| `test_other_pua_untouched` 函数 | 40 | 1 | — |
| `test_idempotent` 函数 | 45 | 7 | — |

### `tests/test_pypdf_backfill.py`（12 个符号）

> `pypdf_backfill` 的回归测试（2026-09-16 新建）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_terminator_hits_structural_markers` 函数 | 21 | 1 | 表/图/附录编号、页眉、工具水印 → 必须终止归并。 |
| `test_terminator_does_not_hit_body_text` 函数 | 37 | 1 | **反向对照**：普通正文与条款号不得被当成边界（否则正文被腰斩）。 |
| `test_page_clauses_stops_at_table_anchor` 函数 | 51 | 1 | **核心回归**：条款正文在表编号处收口，不再吞下页尾。 |
| `test_page_clauses_next_clause_still_splits` 函数 | 74 | 1 | 终止锚不得破坏原有的"下一条款切分"行为。 |
| `test_page_clauses_appendix_anchor` 函数 | 85 | 1 | 附录编号行也必须终止（实测 `表E.4`/`附录A` 是越界的主要来源之一）。 |
| `_mem_conn` 函数 | 97 | 4 | 内存库 + 最小 schema（backfill_document 碰 clause_revision / clause_patch /。 |
| `_fts_conn` 函数 | 116 | 3 | 带 clause_fts 的内存库 + 已就位的一行正文（用于验证 FTS 同步）。 |
| `test_backfill_syncs_fts_with_patched_text` 函数 | 138 | 1 | **核心回归**：回填后 `clause_fts` 必须反映**补丁正文**，而不是补丁前原文。 |
| `test_backfill_fts_untouched_when_rejected` 函数 | 162 | 1 | 反向对照：回填被拒（越界）时**不得**动 FTS（否则索引指向不存在的正文）。 |
| `test_backfill_rejects_oversized_text` 函数 | 179 | 1 | 回填若把文本撑成原文的 3 倍以上（越界抽取的直接特征）→ 拒绝打补丁。 |
| `test_backfill_accepts_reasonable_text` 函数 | 204 | 2 | **反向对照**：长度合理且数字更多的回填必须被接受（护栏不得打掉真修复）。 |
| `_clauses_from_text` 函数 | 228 | 4 | 复用生产切分逻辑，但喂入给定文本（绕过 pypdf 读取）。 |

### `tests/test_quality_rules.py`（12 个符号）

> A 组：反熵与既有行为不变（`src/core/quality/` 抽取的差分锁定）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_legacy_html_to_text` 函数 | 25 | 4 | — |
| `_legacy_tags` 函数 | 39 | 2 | — |
| `test_qh_01_clause_health_diff_vs_inline` 函数 | 135 | 1 | 两件事一起锁：。 |
| `test_qh_04_html_to_text_byte_identical` 函数 | 159 | 1 | 表格 html→文本 必须与冻结副本**逐字符相等**（含 None/空/无表格）。 |
| `test_qh_04b_html_to_text_custom_limit` 函数 | 164 | 1 | limit 参数语义保持（旧签名有 limit 参数）。 |
| `test_qh_05_table_md_400_prefix_semantics` 函数 | 171 | 1 | `ClauseHealth.table_md` 保持"先 400 字截断"的既有语义（长表格漏检是已知缺陷，不在此修）。 |
| `test_qh_07_no_second_regex` 函数 | 178 | 1 | 反熵：`src/core/quality/` 里不得出现第二套标准号/文件名正则，也不得 import scripts/。 |
| `_mk_doc` 函数 | 206 | 31 | — |
| `_mk_clause` 函数 | 219 | 16 | — |
| `qworld` 函数 | 230 | 3 | 播 5 条命中条款（跨 2 文档）+ 2 条干净条款。 |
| `test_qh_02_quality_issues_endpoint_shape` 函数 | 260 | 2 | 端点响应形状/键集合/截断长度必须与抽取前一致（FAIL：键多/少，或截断长度不符）。 |
| `test_qh_03_quality_issues_limit_break` 函数 | 280 | 1 | limit 早停语义 + SQL 排序保持（FAIL：返回 >limit 条，或不是排序后的前 N 条）。 |

### `tests/test_query_rewrite_ruler.py`（19 个符号）

> exp-13 查询侧改写尺子（`eval/recall-funnel/exp-13-query-rewrite/run.py`）的单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 44 | 125 | — |
| `_stub_tokenize` 函数 | 56 | 7 | 替身分词器：按空白切（测试要脱离 jieba）。 |
| `test_d1_without_terms_equals_baseline` 函数 | 61 | 2 | ★ 没扩到词 ⇒ D1 与 A0 **逐字相同**（空扩展不是一次改写）。 |
| `test_prefix_arms_are_exact` 函数 | 72 | 1 | B1/C1 的前缀必须与常量逐字一致（否则测的不是那一条前缀）。 |
| `test_prf_df_is_document_frequency_not_term_frequency` 函数 | 81 | 2 | ★ df 是文档频率：同一篇里重复 5 次只算 1 次 ⇒ 达不到 min_df=3。 |
| `test_prf_excludes_query_terms_and_non_cjk_and_short` 函数 | 93 | 1 | 提问里已有的词、非中文串、单字都不许被扩进来。 |
| `test_prf_ordering_is_deterministic_by_df_then_length_then_lex` 函数 | 104 | 1 | 排序：df 降序 → 词长降序 → 字典序（确定性，重跑逐字节相同）。 |
| `test_prf_respects_top_m` 函数 | 116 | 1 | — |
| `test_rank_of_counts_strictly_better_only` 函数 | 123 | 2 | ★ 名次 = 严格更优的条数 + 1。 |
| `test_top_k_indices_is_descending_and_bounded` 函数 | 133 | 1 | — |
| `test_hit_rate_counts_none_as_miss` 函数 | 140 | 2 | ★ 未召回（None）算不中，不许从分母里摘掉。 |
| `test_hit_rate_threshold_is_inclusive_at_boundary` 函数 | 148 | 2 | ★ 边界：名次**恰等于**阈值算命中（`r <= thr`，不是 `<`）。 |
| `test_median_rank_ignores_none_and_is_deterministic` 函数 | 161 | 1 | — |
| `test_mcnemar_exact_matches_known_values` 函数 | 166 | 1 | ★ McNemar 双侧精确二项：b=2,c=0 ⇒ 0.5。 |
| `test_flip_counts` 函数 | 175 | 1 | — |
| `test_flip_counts_direction_is_b_then_c_on_asymmetric_sample` 函数 | 182 | 2 | ★ 方向：返回 `(翻进 b, 翻出 c)` —— b = base=False→arm=True，c = base=True→arm=False。 |
| `test_frozen_constants_are_pinned` 函数 | 198 | 1 | 口径常量被钉住（改了要显式改测试，不许静默漂移）。 |
| `test_stoploss_registered_with_expected_endpoint_and_thresholds` 函数 | 208 | 1 | 契约锚：预注册止损线在盘上，且主终点/阈值与代码口径一致。 |
| `test_still_uses_production_embedder_and_model` 函数 | 217 | 2 | ★ 契约锚：本尺子用的必须是**生产**的向量入口与**生产**的模型名。 |

### `tests/test_question_router.py`（33 个符号）

> 按问题选渠道测试（`src/core/update/channels/question_router.py`，§11.0 R6c-3）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `table` 函数 | 31 | 488 | — |
| `_rows` 函数 | 35 | 33 | — |
| `Test规则` 类 | 39 | 0 | — |
| `test_缺省就是五类_顺序按词表` 函数 | 40 | 0 | — |
| `test_候选顺序就是链的顺序` 函数 | 44 | 0 | 前缀专用渠道天然排在兜底棒前面（T/ 号 → ttbz 第一）。 |
| `test_不在链上的渠道不进候选` 函数 | 55 | 0 | `ch:cssn` 声明能答"废止"，但它不在任何链上 ⇒ 候选里没有它，声明里还有它。 |
| `test_only_ok_滤掉判死_但不动声明` 函数 | 65 | 0 | 设计稿验收 2：台账判死 ⇒ 从候选消失。 |
| `test_unknown_与无探针不滤` 函数 | 75 | 0 | 没有证据说它死了 ⇒ 不能滤（滤掉等于凭空缩链）。 |
| `test_tool_永不出现` 函数 | 82 | 0 | 规则 5：`tool:` 的 `answers` 本来就是空的（规则 1 排除它）。 |
| `test_链注入两种写法都认` 函数 | 88 | 0 | `ndls` 与 `ch:ndls` 是同一根棒（换链源那天不会因一个前缀判成"不在链上"）。 |
| `test_链保序去重` 函数 | 94 | 0 | — |
| `Test空候选三种原因` 类 | 100 | 0 | 设计稿验收 3：某类没渠道能答 ⇒ 空列表 + **原因分开**（调用方据此写 unanswerable）。 |
| `test_no_capability` 函数 | 103 | 1 | — |
| `test_off_chain` 函数 | 109 | 1 | — |
| `test_all_down` 函数 | 115 | 1 | — |
| `test_有候选就是ok且不算unanswerable` 函数 | 122 | 0 | — |
| `test_unanswerable_classes只点名空的那些` 函数 | 127 | 0 | — |
| `Test入参` 类 | 132 | 0 | — |
| `test_非法类别抛` 函数 | 133 | 0 | — |
| `test_传单个字符串要说清楚` 函数 | 137 | 0 | `"废止"` 会被逐字拆成 `'废'`/`'止'`，报"不是五类之一"很费解 ⇒ 单独拦。 |
| `test_重复类别去重` 函数 | 148 | 0 | — |
| `test_空类别列表返回空dict` 函数 | 153 | 0 | — |
| `Test真机对照` 类 | 157 | 0 | 设计稿验收 1/4/5：真实号 + 独立复算（不调本模块的内部函数）。 |
| `test_废止候选非空且无tool` 函数 | 162 | 0 | — |
| `test_与独立复算逐条一致` 函数 | 168 | 0 | 独立复算：直接读 JSON + `select_chain` + `first_route`，**不用**本模块的内部函数。 |
| `test_废止类会先问真拿得到废止日期的那根` 函数 | 192 | 0 | §11.0 R6c-4c 的**全部收益**就在这一条上：`废止` 类把 `ndls` 排到 `official_gb` 之前。 |
| `test_前缀专门渠道不被能力排序降级` 函数 | 204 | 0 | ⚠ 我第一版按判定**全局**排序，结果 HJ 号的"发布"先去问 `official_gb`——**把专门渠道降级**。 |
| `test_注入链也要保专门渠道在先` 函数 | 215 | 0 | ⚠ 复核 b37 的 A①：我第一版只在 `chain is None` 时算 `keep_first`，。 |
| `test_注入同一条链结果必须逐位相同` 函数 | 227 | 0 | **注入链不变式**（复核 b38 的开放项⑤）：把自然链原样注入，结果必须一字不差。 |
| `test_未审计的棒不越过partial` 函数 | 241 | 0 | ⚠ 复核 b37 的 A②：我第一版把"没审计（None）"与 `supported` 同键，。 |
| `test_已知缺口已被兜底链补掉_HJ不再一判死就丢两类` 函数 | 257 | 0 | **记录型用例：它按设计红过一次，这里是红过之后**有意**改成的样子。 |
| `Test人用脚本` 类 | 276 | 0 | `scripts/question-route.py` 是给人看的入口——它坏了不会有人发现，所以用一条用例钉住。 |
| `test_json_模式能跑通且是合法json` 函数 | 284 | 0 | — |

### `tests/test_r5a.py`（3 个符号）

> 阶段3 R5a 测试：放宽的内部引用抽取 + 证据链扩展检索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_loosened_internal_refs` 函数 | 5 | 1 | — |
| `test_expand_evidence_chain` 函数 | 18 | 1 | — |
| `test_search_with_details_expansion` 函数 | 49 | 1 | — |

### `tests/test_rag_gate_not_adopted.py`（3 个符号）

> **检索闸（Jev 对 top-5 逐段判相关/有答案/与前提矛盾）为什么暂不接进链路**（2026-09-24 量测结论）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_require_measure` 函数 | 63 | 3 | **缺量测数据就显式 skip，不许静默通过**（独立复核 2026-09-24 指出：。 |
| `test_measure_file_exists_and_has_all_queries` 函数 | 74 | 1 | — |
| `test_low_score_does_not_mean_irrelevant_documented` 函数 | 86 | 1 | **决策钉死**：前两组 top-5 的「相关」分全低，但它们**命中的法规是对的**。 |

### `tests/test_real_corpus_retrieval.py`（8 个符号）

> **真语料**上的检索与条款定位判据（种子库驱动）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `repo` 函数 | 32 | 75 | 拿到已灌种子库的 `clause_repo`。 |
| `test_seed_fixture_actually_has_corpus` 函数 | 38 | 1 | 先证明 fixture 里真有语料 —— 否则后面每条断言都会"通过"，但什么都没验。 |
| `test_real_clause_is_resolvable` 函数 | 57 | 1 | 真条款能按「标准号 + 条款号」定位到 —— **空库上验不出来**（空库返回 None）。 |
| `test_real_clause_carries_source_spans` 函数 | 66 | 1 | 真条款带**位置片段**（可点链接要用）—— 空库上没有 span 可查。 |
| `test_absent_clause_returns_none_not_a_wrong_standard` 函数 | 76 | 1 | **查不到的条款号必须返回 None**，不许串到别家标准。 |
| `test_standard_number_disambiguates_between_documents` 函数 | 103 | 1 | 同一个条款号在不同标准下必须是不同条款（不许串号）。 |
| `test_hybrid_search_finds_real_methanol_clause` 函数 | 115 | 1 | **六路检索**在真语料上能召回到甲醇条款。 |
| `test_fts_channel_works_on_real_corpus` 函数 | 134 | 1 | FTS 通道在真语料上能查到中文词。 |

### `tests/test_real_question_ruler.py`（34 个符号）

> 真人问答召回尺子的回归判据（spec 010）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ruler` 函数 | 35 | 79 | — |
| `stats` 函数 | 41 | 194 | — |
| `Test规模与结构` 类 | 46 | 0 | — |
| `test_恰好_500_条` 函数 | 47 | 0 | — |
| `test_每条都有必填字段` 函数 | 50 | 0 | — |
| `test_gold_std_不为空` 函数 | 57 | 0 | — |
| `test_q_len_与实际长度一致` 函数 | 61 | 0 | — |
| `Test不把测不出来的算进分数` 类 | 66 | 0 | SC-002 —— 这三条是这个尺子"有没有意义"的底线。 |
| `test_没有投诉举报类` 函数 | 69 | 0 | — |
| `test_没有超长问句` 函数 | 74 | 0 | — |
| `test_没有过短问句` 函数 | 78 | 0 | — |
| `test_stats_也如实声明` 函数 | 82 | 0 | — |
| `Test不偏科` 类 | 87 | 0 | SC-003。 |
| `test_最大单一来源不超过_10_百分比` 函数 | 90 | 0 | — |
| `test_覆盖至少_20_个来源` 函数 | 95 | 0 | — |
| `test_stats_与复算一致` 函数 | 98 | 0 | — |
| `Test可追溯` 类 | 104 | 0 | SC-006。 |
| `test_trace_key_格式正确` 函数 | 107 | 0 | — |
| `test_trace_key_不重复` 函数 | 111 | 0 | — |
| `test_url_允许为空但不允许错` 函数 | 116 | 0 | — |
| `Test可复现` 类 | 122 | 0 | SC-004。 |
| `test_种子被记录` 函数 | 125 | 0 | — |
| `test_输入规模被记录` 函数 | 128 | 0 | — |
| `test_五道过滤计数齐全` 函数 | 132 | 0 | — |
| `Test分层如实` 类 | 151 | 0 | 分层必须如实记录 —— 尤其 `zero_overlap` 很少这件事实。 |
| `test_分层计数与复算一致` 函数 | 154 | 0 | — |
| `test_zero_overlap_很少是已知事实` 函数 | 158 | 0 | ⚠ 这条**故意断言它很少** —— 防止有人把 0.8% 说成"大白话损耗很小"。 |
| `Test新分层有区分度` 类 | 171 | 0 | `layering_v2`（问句 vs **官方答复** 的分级重合）—— 2026-10-12 新增。 |
| `test_各档合计等于条数` 函数 | 188 | 0 | — |
| `test_至少四档非空` 函数 | 193 | 0 | — |
| `test_最大一档不超过七成` 函数 | 197 | 0 | 若某一档占了绝大多数，说明分层退化成"一档独大" ⇒ 又没区分度了。 |
| `test_overlap_值在_0_到_1_之间` 函数 | 203 | 0 | — |
| `test_overlap_中位与_stats_一致` 函数 | 208 | 0 | — |
| `test_答复原文没被写进产物` 函数 | 212 | 0 | 答复原文受版权/使用条款约束（README 已写明），**不入库**。 |

### `tests/test_reingest_keeps_filing.py`（19 个符号）

> 重导（「重来一次」）**不许把用户的整理成果弄丢**（2026-09-24 审计 A1，P0）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_own_data_dir` 函数 | 50 | 5 | **本模块私有的临时数据目录**（跑完即弃，其他模块零影响）。 |
| `_write_pdf` 函数 | 89 | 23 | 一页真实 PDF（只为了让 ``run_full_ingest`` 的前置检查有文件可开）。 |
| `synthetic_parser` 函数 | 100 | 43 | 把 ``run_parser_isolated`` 换成**给定 blocks 的合成结果**（真链路，只有解析这一步是假的）。 |
| `_offline_embedder` 函数 | 117 | 4 | 向量引擎强制离线（不打的实测后果：真加载会去 huggingface **下模型**，用例挂在网络等待里）。 |
| `_uniq_no` 函数 | 127 | 13 | 本模块唯一的标准号（``doc_meta.standard_no`` 有唯一约束）。 |
| `_mkfolder` 函数 | 132 | 14 | 建一个本模块唯一的目录（同名同层会被两条部分唯一索引拒绝）。 |
| `_new_pdf` 函数 | 137 | 6 | — |
| `_members_of` 函数 | 141 | 15 | — |
| `_file_member_rows` 函数 | 147 | 7 | 全库"文件挂在哪"的行（用于反向判据：不许动不属于它的那些）。 |
| `test_reingest_moves_every_membership_and_touches_nothing_else` 函数 | 155 | 1 | 重导一篇归在两个目录里的文件 ⇒ 新 doc_id 的归属集合 == 旧集合。 |
| `_mv_doc` 函数 | 220 | 11 | 插一篇最小可用的文档行（只为了有归属主体）。 |
| `test_both_delete_paths_clear_membership_and_state` 函数 | 233 | 1 | ``clause_repo.delete_document``（单篇）与 ``doc_delete.delete_documents``（批量）。 |
| `test_reingest_keeps_failed_old_state_from_smearing_a_success` 函数 | 278 | 1 | 旧行是 ``failed``、这次解析成功 ⇒ 新行**不许**还是 ``failed``（也不许停在 recognizing）。 |
| `test_reingest_of_failed_parse_marks_failed_even_when_membership_carried` 函数 | 295 | 1 | 已归位的那篇这次解析**失败**（正文为零）⇒ ``failed``（不假装成功），归属照旧搬过去。 |
| `test_no_carry_without_an_old_document` 函数 | 315 | 1 | **反向哨兵**：没有旧文档可替换（全新标准号 / 普通入库）⇒ 一条都不搬。 |
| `test_restore_refuses_a_missing_target_and_is_idempotent` 函数 | 325 | 1 | 原地判 ``restore_filing_assets``：目标文档不存在 ⇒ ``doc_not_found``（**且什么都没写**）。 |
| `test_carry_failure_is_reported_not_silent` 函数 | 353 | 1 | 搬运**失败**必须与"没有旧文档要搬"分得开（``filing_assets_carry_error`` 非空）。 |
| `test_restore_skips_folders_deleted_after_the_snapshot` 函数 | 389 | 1 | 拍快照之后、落盘之前目录被删掉 ⇒ **不插**那条悬空挂靠。 |
| `test_restore_says_the_truth_when_every_folder_was_deleted` 函数 | 420 | 1 | 快照里的目录**全被删** ⇒ 一条都没搬成 ⇒ **不许**说它还归位在某个目录里。 |

### `tests/test_reranker.py`（11 个符号）

> Task 10.2 reranker 测试：降级路径 + 集成（模型可用时）+ 例外保护 + 合规 K=8。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_FakeModel` 类 | 12 | 6 | 只回固定分数（按输入顺序）的假模型 —— 用来把"对齐"这件事与真实模型解耦。 |
| `__init__` 函数 | 15 | 135 | — |
| `rerank` 函数 | 19 | 116 | — |
| `_clauses` 函数 | 24 | 5 | — |
| `test_reranker_scores_align_with_input` 函数 | 31 | 2 | 判据：返回的分数必须与 `texts` **一一对应**，不许替调用方排序。 |
| `test_reranker_rejects_length_mismatch` 函数 | 46 | 1 | 判据：分数个数与候选条数不匹配时必须**当场抛错**（fail-closed），不许静默错位。 |
| `test_reranker_pipeline_reorders_by_score` 函数 | 54 | 2 | 判据（端到端）：`_rerank_results` 真的会**按分数改顺序**。 |
| `test_rerank_offline_degrades_to_original` 函数 | 72 | 1 | 模型不可用时（monkeypatch 加载失败）→ 原序返回 + rerank_offline=true。 |
| `test_rerank_exception_clause_kept` 函数 | 98 | 2 | 含但书的例外条款即使被 rerank 挤出也必须保留（P1 例外保护）。 |
| `test_rerank_integration_smoke` 函数 | 115 | 1 | rerank 接入 perform_hybrid_search：模型离线时返回原序不抛错（R30 降级）。 |
| `test_reranker_real_model_reorders` 函数 | 132 | 1 | 真实模型单测：**正确条款（下标 1）应得最高分**（机制有效性证明）。 |

### `tests/test_research_draft.py`（24 个符号）

> **结论草稿**测试（`src/core/exports/research_draft.py` + `POST /report/research/draft`，§10.96）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 25 | 575 | — |
| `_add` 函数 | 29 | 81 | — |
| `_stub_llm` 函数 | 41 | 18 | 替身：记录 messages 并**一次**产出 `text`（零真实 LLM 消耗）。 |
| `TestGuards` 类 | 49 | 1 | — |
| `test_只装配一次` 函数 | 50 | 0 | **同源不变量的门禁**（§10.98，复核 b25 的 LOW-3）：起草全流程只能装配**一次**。 |
| `test_材料装配失败时报可操作错误码` 函数 | 77 | 0 | §10.98（复核 b25 的 MEDIUM-1）：依据集取不到 ⇒ 500 `materials_load_failed`。 |
| `test_项目不存在仍然按_ValueError_放行` 函数 | 96 | 0 | ⚠ 翻错误码**只翻"意外的失败"**：项目不存在那类 `ValueError` 必须照原样放行。 |
| `test_没有可承重材料时一次_LLM_都不调` 函数 | 108 | 0 | 只有 T3 单一来源（仅线索）⇒ 可承重集合为空 ⇒ **不许**调模型。 |
| `test_项目不存在时_ValueError` 函数 | 123 | 0 | — |
| `test_LLM_不可用时报可操作的错误` 函数 | 127 | 0 | — |
| `test_空输出不是成功` 函数 | 141 | 0 | — |
| `TestHappyPath` 类 | 152 | 2 | — |
| `test_草稿带未批准标记且引用校验与报告同源` 函数 | 153 | 0 | — |
| `test_提示词里材料另起一节且编号与校验同一套` 函数 | 174 | 0 | **同源不变量**：提示词里的 `\[\[m:i\]\]` 编号必须与校验用的 assembled 是同一个。 |
| `TestCitationWarnings` 类 | 189 | 1 | — |
| `test_不存在的编号_草稿原样保留且两层都报警` 函数 | 190 | 0 | — |
| `test_引用仅线索的材料会被列出来` 函数 | 204 | 0 | 可作依据的 T1 在前面、仅线索的 T3 在后面 ⇒ 引用后者必须被点名。 |
| `test_不喂法条时不该冒噪声警告_但出现法条编号要明说` 函数 | 220 | 0 | §10.98（复核 b25 的 LOW-2）：**噪声警告换成准确的那一条**。 |
| `TestEndpoint` 类 | 250 | 2 | — |
| `test_缺少_query_是_422` 函数 | 251 | 0 | — |
| `test_缺少_project_id_是_422` 函数 | 258 | 0 | — |
| `test_项目不存在_404` 函数 | 263 | 0 | — |
| `test_正常路径_200_且带未批准标记` 函数 | 270 | 0 | — |
| `test_LLM_不可用_500_llm_unavailable` 函数 | 285 | 0 | — |

### `tests/test_research_report.py`（40 个符号）

> 研究报告导出测试（`src/core/exports/research_report.py`，Phase D 第一步）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `project` 函数 | 29 | 575 | — |
| `_approved_article` 函数 | 33 | 10 | — |
| `TestBuild` 类 | 39 | 1 | — |
| `test_sections_and_counts` 函数 | 40 | 1 | — |
| `test_grouping_reuses_the_authority_owner` 函数 | 56 | 1 | **结构性约束**：分组标题必须来自 `authority.GROUP_ORDER`（不许自己再写一套）。 |
| `test_pending_is_never_silently_dropped` 函数 | 65 | 1 | — |
| `test_no_approved_materials_says_so` 函数 | 72 | 1 | — |
| `test_missing_project_raises` 函数 | 77 | 1 | — |
| `test_html_is_escaped` 函数 | 81 | 1 | 标题/结论里的 HTML 必须**转义**（报告是可交付文件，不是网页）。 |
| `TestCitationChecking` 类 | 91 | 1 | — |
| `test_unknown_index_is_warned` 函数 | 92 | 1 | — |
| `test_valid_index_is_not_warned` 函数 | 100 | 1 | — |
| `test_law_refs_are_counted_but_not_pretended_verified` 函数 | 108 | 1 | `\[\[c:i\]\]` 本次**无法校验** ⇒ 如实计数（不假装查过）。 |
| `test_conclusion_without_query_is_declared_unchecked` 函数 | 115 | 1 | 不给 `query` 就没有依据集可比 ⇒ **必须**说出来（不许默默放过引用）。 |
| `test_negative_index_is_caught` 函数 | 128 | 1 | 负数编号也要被抓（历史缺陷：提示词侧曾漏掉 `\[\[m:-1\]\]`）。 |
| `TestAnchorVisibility` 类 | 136 | 1 | **引用锚点**要在报告里看得见（方案 §12 未决第 5 条，§10.48）。 |
| `test_fresh_material_has_no_anchor_noise` 函数 | 144 | 1 | 刚入库的材料锚点 `ok` ⇒ **不许**加标记（标记得只在有问题时出现，否则人人无视）。 |
| `test_health_crash_is_not_reported_as_unverified` 函数 | 152 | 1 | **健康度算不出来 ≠ 材料未验证**（复核 b9 的 INFO-3）。 |
| `test_old_material_is_marked_unverified` 函数 | 178 | 1 | 入库时没记指纹的老材料 ⇒ 标记 + warning（措辞必须是"未经验证"，不是"有问题"）。 |
| `test_changed_fingerprint_is_marked_needing_recompute` 函数 | 191 | 1 | 指纹变了 ⇒ 「⚠锚点需复算」+ warning（措辞："需要复算"，不是"已经坏了"）。 |
| `TestEvidenceAnchorMarks` 类 | 214 | 2 | **锚点标记要出现在"引用行"上**（复核 b11 的 INFO-4，2026-09-18 收）。 |
| `test_report_marks_the_evidence_lines` 函数 | 224 | 1 | 报告「三、依据」的**引用行**上必须看得到锚点标记（这条就是验收条件）。 |
| `test_without_the_map_the_rendering_is_unchanged` 函数 | 244 | 1 | **P1 保证**：不传 map（= 答案链那条路）时，渲染里**不许**出现任何锚点标记。 |
| `test_marks_vocabulary_has_one_owner` 函数 | 264 | 1 | 三个短标记的措辞**只有一份**（`locator.STATUS_MARKS`），两处都从它取。 |
| `TestEvidenceAssemblyGate` 类 | 272 | 1 | **报告侧的"依据集取不到"门禁**（§10.100，复核 b27 的 LOW-4）。 |
| `test_报告侧装配失败翻成可操作错误码` 函数 | 282 | 0 | — |
| `test_报告侧项目不存在仍按_ValueError_放行` 函数 | 297 | 0 | — |
| `test_落盘路径同样走那个唯一入口` 函数 | 307 | 0 | `write_research_report`（真正落盘那条）也必须经过它——否则"先渲染后落盘"的。 |
| `TestWrite` 类 | 331 | 1 | — |
| `test_files_are_written_and_named` 函数 | 332 | 1 | — |
| `test_unsafe_title_is_sanitised` 函数 | 343 | 1 | — |
| `TestTrackLStatus` 类 | 351 | 1 | — |
| `test_lists_track_l_targets_without_writing` 函数 | 352 | 1 | `track_l_status` 只读（不得往法条链写任何东西）。 |
| `TestEndpoint` 类 | 366 | 2 | — |
| `test_export_writes_files_and_returns_them` 函数 | 367 | 1 | — |
| `test_dry_run_does_not_write` 函数 | 381 | 1 | — |
| `test_missing_project_is_404` 函数 | 392 | 1 | — |
| `test_missing_project_id_is_422` 函数 | 397 | 1 | — |
| `test_wrong_types_are_422` 函数 | 401 | 1 | — |
| `test_requires_token` 函数 | 409 | 2 | — |

### `tests/test_resolve_clause_normalization.py`（12 个符号）

> `resolve_clause` 条款号输入归一的回归（2026-09-17）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `seeded` 函数 | 18 | 40 | 两份文档：GB/T 10029-2010（含 5.2.1 / 06 / 6 / 表引用）与对照标准。 |
| `_num` 函数 | 62 | 13 | — |
| `test_fullwidth_clause_number_resolves` 函数 | 66 | 1 | 全角条款号必须能解析到半角那条（原实现返回 None）。 |
| `test_whitespace_and_leading_zero_tolerated` 函数 | 74 | 1 | — |
| `test_exact_form_wins_over_normalized_form` 函数 | 80 | 2 | **这条是修法的护栏**：库里同时有 '06' 与 '6' 时，查 '06' 必须命中 '06'。 |
| `test_table_reference_with_space_resolves` 函数 | 91 | 1 | 「表 2」中间带空格也要进表格引用 fallback（归一后为「表2」）。 |
| `test_no_false_positive_for_absent_clause` 函数 | 98 | 1 | 归一不能把不存在的条款号"变"出来。 |
| `test_standard_number_still_disambiguates` 函数 | 105 | 1 | 同一条款号在不同标准下不得串号（原样优先不应破坏精确匹配）。 |
| `test_resolve_route_accepts_fullwidth` 函数 | 114 | 1 | 走真端点的同一路径（客户端可能把全角原样送上来）。 |
| `test_superscript_input_does_not_crash` 函数 | 128 | 1 | R3（**曾在生产端点打 500**）：`str.isdigit()` 对上标/下标等 128 个码点为 True，。 |
| `test_verbatim_lookup_is_tried_first` 函数 | 148 | 1 | R1：库里若真存在**带空白**的条款号，原样查询必须仍能命中它。 |
| `test_table_reference_is_consistent_with_and_without_spaces` 函数 | 166 | 1 | R2：`'表2'` 与 `' 表2 '` 必须给出**同一个**结果。 |

### `tests/test_retrieval.py`（17 个符号）

> T04 检索测试：六通道命中、RRF 排序、时效过滤、向量检索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clause` 函数 | 9 | 38 | — |
| `seeded_db` 函数 | 23 | 16 | — |
| `test_exact_channel_hit` 函数 | 76 | 1 | — |
| `test_exact_superseded_excluded` 函数 | 82 | 1 | — |
| `test_null_legal_status_is_not_silently_excluded` 函数 | 93 | 1 | **NULL（未核验）≠ 已废止**：它也要能被精确命中抓到。 |
| `test_unverified_clause_does_not_outrank_an_effective_one` 函数 | 129 | 1 | **未核验不许在通道内占优**（复核 b9 的 LOW-3，2026-09-18 修）。 |
| `test_modality_channel_ranks_verified_before_unverified` 函数 | 165 | 1 | 模态通道（D）的**通道内名次**必须是确定的，且未核验不占优（复核 b9 的 INFO-6）。 |
| `test_legal_element_channel_order_is_deterministic` 函数 | 211 | 1 | 法理要素通道（E）**同族缺陷、自查发现**：它原先也没有 ORDER BY。 |
| `test_legal_element_channel_ranks_verified_before_unverified` 函数 | 242 | 1 | 法理要素通道（E）也要"未核验沉底 + 确定"（§10.65 补齐。 |
| `test_fts_channel` 函数 | 278 | 1 | — |
| `test_modality_channel` 函数 | 284 | 1 | — |
| `test_legal_element_channel` 函数 | 291 | 1 | — |
| `test_behavior_scope_channel` 函数 | 298 | 1 | — |
| `test_vec_channel` 函数 | 306 | 2 | — |
| `test_rrf_exact_beats_fts` 函数 | 317 | 1 | — |
| `test_query_modality_extraction` 函数 | 324 | 1 | — |
| `test_search_with_details` 函数 | 330 | 1 | — |

### `tests/test_run_gates_ratchet_wiring.py`（18 个符号）

> `run-gates.ps1` 棘轮的**接线**测试：8 处判定点必须接 `$totalForRatchet`，不许退回 `$totalRan`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_read` 函数 | 100 | 13 | — |
| `_code_lines` 函数 | 104 | 5 | 去掉**整行注释**后的代码行。 |
| `find_violations` 函数 | 113 | 11 | 返回违规说明。 |
| `_site_line_indices` 函数 | 171 | 4 | 8 个判定点所在的**行号**（0 基。 |
| `_mutate_line` 函数 | 180 | 3 | 把第 `line_index` 行里的 `$totalForRatchet` 改回 `$totalRan`。 |
| `test_run_gates_exists` 函数 | 190 | 1 | — |
| `test_pristine_file_wires_ratchet_at_all_eight_sites` 函数 | 195 | 1 | 原样件必须零违规 —— 否则下面的自验没有意义。 |
| `test_exactly_eight_code_sites_are_found` 函数 | 201 | 1 | 8 个判定点必须都能被**逐处**定位（自验的地基）。 |
| `test_every_single_site_mutation_is_caught` 函数 | 210 | 1 | **核心判据**：把 8 处**任意一处**改回 `$totalRan` ⇒ 必须报违规。 |
| `test_all_reads_mutation_is_caught` 函数 | 230 | 1 | 7 个读取点全改回（PSSA 唯一抓得住的那一种）也必须被本检测器报出。 |
| `test_anchor_names_are_present_in_code_lines` 函数 | 243 | 2 | 三个锚点必须各自出现在**至少一行代码**里（缺一 ⇒ 判据 3 静默失效）。 |
| `test_anchor_rename_is_caught` 函数 | 257 | 2 | **核心**：把任一锚点全文改名（只改名、语义不变）⇒ 必须报违规。 |
| `test_anchor_mixing_is_caught` 函数 | 276 | 2 | 注入一行「锚点 + `$totalRan`」混用 ⇒ 必须报出（证明判据 3 不是空转）。 |
| `test_detector_is_not_always_true` 函数 | 292 | 1 | 反向自验：无关改动（改注释、改无关标识符）必须**零报** —— 防「扫描器恒真」。 |
| `test_comment_occurrence_is_excluded_from_the_count` 函数 | 301 | 1 | 文档化那第 9 次出现（注释）**不算**判定点 —— 防止有人把注释删掉就以为少了一处。 |
| `test_base_total_primary_source_exists` 函数 | 313 | 1 | 原样件里 `$baseTotal` 的首选来源**恰有一处**（判据 5 的地基）。 |
| `test_deleting_base_total_source_is_caught` 函数 | 319 | 2 | **C2 的核心**：删掉 `$baseTotal = \[int\]$base.pytest_total` 那一行 ⇒ **必须报违规**。 |
| `test_base_total_source_swap_is_caught` 函数 | 337 | 2 | 把首选来源**换成别的字段**（语义变了但行还在）⇒ 也必须报。 |

### `tests/test_scnet_readchain.py`（17 个符号）

> std_bulk_import.py 的 SCNET 读链测试（整改批 4，问题清单 #5）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_ensure_scnet_key` 函数 | 30 | 2 | — |
| `ensure_key` 函数 | 43 | 11 | — |
| `_FakeKey` 类 | 53 | 13 | — |
| `__init__` 函数 | 54 | 135 | — |
| `__enter__` 函数 | 57 | 9 | — |
| `__exit__` 函数 | 60 | 9 | — |
| `QueryValueEx` 函数 | 63 | 11 | — |
| `FakeWinreg` 类 | 69 | 8 | — |
| `__init__` 函数 | 75 | 135 | — |
| `QueryValueEx` 函数 | 79 | 11 | — |
| `OpenKey` 函数 | 82 | 9 | — |
| `_use_fake_winreg` 函数 | 90 | 5 | — |
| `test_reads_from_encrypted_store_first` 函数 | 95 | 1 | — |
| `test_env_var_wins_without_store` 函数 | 106 | 1 | — |
| `test_registry_fallback_still_works` 函数 | 111 | 1 | 加密存储没有 → 注册表覆盖链仍可用（只读，为 CI/老 setx 值保底）。 |
| `test_missing_everywhere_returns_false` 函数 | 121 | 1 | — |
| `test_ks_namespace_alias_in_store` 函数 | 126 | 1 | 加密存储里若用的是 KS_ 命名空间名，同样能取到（并存注入）。 |

### `tests/test_secret_store.py`（21 个符号）

> 引擎侧密钥存储（`src/core/settings/secret_store.py`）单测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `data_dir` 函数 | 23 | 165 | 把存储重定向到临时目录（KS_DATA_DIR 是 config 与 secret_store 共用的开关）。 |
| `ExplodingWinreg` 类 | 32 | 3 | 任何属性访问都抛错：证明某条代码路径**一行 winreg 都没碰**。 |
| `__getattr__` 函数 | 35 | 2 | — |
| `test_store_path_matches_config_data_dir` 函数 | 40 | 2 | 存储路径规则必须与 config._default_data_dir 一致（两份规则，一条断言钉住）。 |
| `test_store_path_matches_config_WITHOUT_override` 函数 | 48 | 1 | ⚠ **缺口钉子（2026-10-18 补）**：**不设 `KS_DATA_DIR`** 时两边也必须一致。 |
| `test_protect_roundtrip_and_no_plaintext` 函数 | 69 | 1 | — |
| `test_unprotect_wrong_entropy_returns_empty` 函数 | 75 | 1 | 别的程序（换 entropy）拿到密文也解不开 —— 但我们得**降级**而不是崩。 |
| `test_unprotect_garbage_returns_empty` 函数 | 81 | 1 | — |
| `test_empty_plaintext_roundtrip` 函数 | 87 | 1 | — |
| `test_protect_rejects_non_str` 函数 | 91 | 1 | — |
| `test_oversize_value_rejected` 函数 | 96 | 1 | — |
| `test_file_contains_names_but_no_plaintext` 函数 | 103 | 1 | — |
| `test_write_is_merge_and_delete` 函数 | 114 | 1 | — |
| `test_write_zero_values_is_noop` 函数 | 124 | 1 | — |
| `test_no_temp_files_left_behind` 函数 | 129 | 1 | — |
| `test_corrupt_file_degrades_to_empty` 函数 | 136 | 1 | — |
| `test_wrong_shape_json_degrades` 函数 | 145 | 1 | — |
| `test_unwritable_dir_raises_on_write_but_read_still_safe` 函数 | 150 | 1 | 写失败必须**吵**（不能静默丢 Key）。 |
| `test_concurrent_writes_do_not_lose_values` 函数 | 161 | 1 | 两个线程各写一个通道名：锁必须让两个名字都留下（不能后写覆盖前写）。 |
| `test_stale_lock_is_reclaimed` 函数 | 183 | 1 | 崩溃遗留的锁文件不能永久卡死写入。 |
| `test_write_path_never_touches_winreg` 函数 | 199 | 1 | 把 winreg 换成"一碰就炸"，写入仍然成功 ⇒ 写路径一行 winreg 都没有。 |

### `tests/test_seed_db_guard.py`（8 个符号）

> 种子库的回归护栏 —— 把「它能复现已知缺陷」这件事钉住。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `seed_db` 函数 | 39 | 15 | — |
| `test_seed_db_exists_and_size_is_sane` 函数 | 47 | 1 | 规模合理：不能是空库，也不能膨胀到没法进版本控制。 |
| `test_seed_db_has_all_required_standards` 函数 | 53 | 1 | 缺陷现场必须完整 —— 少一部标准，那条 bug 就复现不了。 |
| `test_seed_db_fts_is_populated` 函数 | 65 | 1 | FTS 必须是**真插入**过的，不是空壳。 |
| `_resolve_on_seed` 函数 | 84 | 4 | 在**种子库副本**上跑真的 `resolve_clause`（不碰生产库）。 |
| `test_cross_standard_false_hit_is_fixed` 函数 | 111 | 1 | **跨标准误命中已修**（wiki §四 #2，2026-10-23）。 |
| `test_all_victim_standards_no_longer_cross_hit` 函数 | 132 | 1 | 那 **9 部受害标准**逐个验：查不存在的条款号**一律不许串到别家**。 |
| `test_year_tolerance_forward_path_still_works` 函数 | 147 | 1 | 年份宽容的**正向**路径：旧版号要能宽松到现行版（修兜底时不能改坏）。 |

### `tests/test_selfcheck_fixes.py`（4 个符号）

> 第一阶段自检修复的回归测试（phase1-selfcheck.md 对应）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_query_modality_compound_guard` 函数 | 5 | 1 | — |
| `test_write_queue_stale_processing_recovered` 函数 | 13 | 1 | — |
| `test_same_standard_different_hash_blocked` 函数 | 29 | 1 | R43: 同标准号不同 hash 不崩溃，返回 standard_exists 供上层确认。 |
| `test_ingest_missing_file` 函数 | 47 | 1 | — |

### `tests/test_span_calibration.py`（11 个符号）

> span 坐标系通用自动校准测试（R-B，pipeline/13-round3.md）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_make_pdf` 函数 | 23 | 38 | 构造测试 PDF：每页写已知 ASCII 文本行（fitz 顶部原点，基线 y = base_y + i*step）。 |
| `test_page_line_centers_and_vote_top_bottom_none` 函数 | 38 | 1 | ①两页 PDF 三行已知文本：top-origin bbox 判 top。 |
| `test_calibrate_new_idempotent` 函数 | 66 | 1 | ②纯函数版：顶部原点翻为底部原点后二次调用零变化。 |
| `test_calibrate_new_supports_source_span_model` 函数 | 94 | 1 | pipeline 接入形态：SourceSpanModel 对象同样原地归一为底部原点。 |
| `test_fragment_vote_no_split_50140_style` 函数 | 111 | 1 | ③50140 复验式：条款块中段碎片 bbox 用最近行投票一致判定，不再分裂。 |
| `test_calibrate_db_rowid_update_and_audit` 函数 | 155 | 1 | ④存量路径（带内真值裁决）：rowid 精确 UPDATE + event_log 审计。 |
| `test_calibrate_dry_run_and_empty_safe` 函数 | 187 | 1 | ⑤dry-run 只报告零写库。 |
| `_mk_conn` 函数 | 215 | 3 | 内存库：content 挂两条款（clrev_1/clrev_2），spans=\[(cid, page, y0, y1, sort)\]。 |
| `test_calibrate_both_hit_uses_direction_no_double_flip` 函数 | 227 | 1 | v2 回归：采样 span 落在镜像对称区（两种解释都命中）时，已正确的文档**不得**被翻转。 |
| `test_calibrate_direction_vote_flips_when_text_unverifiable` 函数 | 259 | 1 | v2 回归：无文字层页（模拟乱码/纯扫描件）带内文字无法判定 → 阅读方向证据兜底：。 |
| `test_calibrate_new_uses_direction_with_groups` 函数 | 284 | 1 | pipeline 形态：calibrate_new 传入条款分组后，方向判别生效（无文字层也能翻）。 |

### `tests/test_sqlite_conn_registry.py`（3 个符号）

> `sqlite_db` 的**跨线程连接登记/关闭**（2026-09-22 为了"临时目录真能删掉"而加）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_close_all_connections_reaches_another_thread_and_keeps_it_usable` 函数 | 27 | 1 | ① 别的线程那份被关掉（文件能删）。 |
| `test_close_thread_connection_forgets_its_registry_entry` 函数 | 77 | 1 | ③ `close_thread_connection()` 关掉之后，登记表里**不许**再留着那条死登记。 |
| `test_close_all_connections_is_safe_when_nothing_is_registered` 函数 | 90 | 1 | ④ 空表/重复调用都不许炸（两个 fixture 收尾都会调它）。 |

### `tests/test_standard_body.py`（7 个符号）

> `_standard_body` / `_std_body_hits` 的单元判据（2026-10-23 修跨标准误命中时补）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `body` 函数 | 24 | 1611 | — |
| `hits` 函数 | 30 | 338 | — |
| `test_extracts_standard_body_not_year` 函数 | 65 | 1 | — |
| `test_returns_none_when_no_body` 函数 | 77 | 1 | — |
| `test_body_hits_respects_numeric_boundary` 函数 | 83 | 1 | `GBZ 24-2025` 的主体 `24` **不许**命中 `GB/T 13537-2024`。 |
| `test_body_hits_accepts_exact_and_prefixed` 函数 | 96 | 1 | 边界判据不许把**该命中**的挡掉。 |
| `test_body_hits_handles_none` 函数 | 105 | 1 | — |

### `tests/test_standard_no_ocr_suffix.py`（28 个符号）

> 标准号「(OCR采集)」来源后缀剥离的回归判据（spec 009）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Test剥来源后缀` 类 | 28 | 0 | A1：带后缀的必须剥掉。 |
| `test_剥掉半角括号后缀` 函数 | 31 | 0 | — |
| `test_剥掉全角括号后缀` 函数 | 34 | 0 | — |
| `test_剥掉后两侧空白` 函数 | 37 | 0 | — |
| `test_真库样例_带书名号截断的那种` 函数 | 40 | 0 | — |
| `test_连续两个后缀` 函数 | 47 | 0 | — |
| `Test不动合法括号` 类 | 52 | 0 | A2：合法括号名一字不动 —— 判据写宽就会被咬住。 |
| `test_合法括号_聚丙烯PP树脂` 函数 | 55 | 0 | — |
| `test_合法括号_湿式非金属类` 函数 | 58 | 0 | — |
| `test_合法括号_结尾也是括号` 函数 | 62 | 0 | — |
| `test_副本后缀不动_那是另一个判据` 函数 | 66 | 0 | — |
| `Test不动官方标准尾部中文` 类 | 71 | 0 | A3：官方标准的标准号尾部带中文，是内容不是标记。 |
| `test_官方标准_食品安全国家标准` 函数 | 74 | 0 | — |
| `test_官方标准_术语` 函数 | 78 | 0 | — |
| `test_四篇里的每一篇都不动` 函数 | 82 | 0 | — |
| `Test不动以中文括号结尾的名字` 类 | 93 | 0 | A4（2026-10-12 变异自验补）：**以中文括号结尾**的名字必须一字不动。 |
| `test_刑法修正案_中文括号结尾` 函数 | 110 | 0 | — |
| `test_规则试行_中文括号结尾` 函数 | 113 | 0 | — |
| `test_公告_中文括号结尾` 函数 | 117 | 0 | — |
| `test_已废止_中文括号结尾` 函数 | 121 | 0 | — |
| `test_测试夹具_中文括号结尾` 函数 | 125 | 0 | — |
| `test_真库那_88_条的形态都不动` 函数 | 129 | 0 | 把真库实测的 88 条形态**逐条**过一遍（这是从库里抄下来的，不是编的）。 |
| `Test边界` 类 | 149 | 0 | — |
| `test_空串` 函数 | 150 | 0 | — |
| `test_None` 函数 | 153 | 1 | — |
| `test_只有后缀_剥成空` 函数 | 156 | 0 | — |
| `test_幂等` 函数 | 159 | 0 | — |
| `test_中间的OCR采集不动` 函数 | 163 | 0 | — |

### `tests/test_storage.py`（4 个符号）

> T02 存储层测试：PRAGMA、外键级联、FTS5/vec 可用、单写者队列串行化。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_pragmas` 函数 | 7 | 1 | — |
| `test_foreign_key_cascade` 函数 | 15 | 1 | — |
| `test_fts5_and_vec_tables` 函数 | 37 | 1 | — |
| `test_write_queue_serializes` 函数 | 64 | 1 | — |

### `tests/test_store_standard_no.py`（22 个符号）

> 标准号"存储形"收口测试（§11.0 R6c-2d）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Test存储形` 类 | 30 | 0 | — |
| `test_全角折半角_其余一字不动` 函数 | 31 | 0 | — |
| `test_不动空格大小写与年份` 函数 | 37 | 0 | — |
| `test_空值不炸` 函数 | 41 | 0 | — |
| `test_不改变是不是同一部标准` 函数 | 45 | 0 | 1:1 换形状的**全部意义**：`norm_no` 前后必须相等（否则就动了语义）。 |
| `test_与比较键的分工没被搞混` 函数 | 51 | 0 | `canon_standard_no`/`standard_no_key` 是**比较键**（去空格去斜杠），存储形**不**那样做。 |
| `_doc` 函数 | 62 | 14 | — |
| `Test写入收口` 类 | 70 | 0 | ⚠ 这些用例**必须自己清理**：`db` fixture 是**会话级同一个库**（`_isolate_data_dir` 整场只建一次），。 |
| `_tidy` 函数 | 78 | 1 | — |
| `test_insert_document折不折三个列` 函数 | 85 | 0 | — |
| `test_名称里的全角连字符不许折` 函数 | 95 | 0 | ⚠ 复核 b33 的最高风险：**名称里的全角 `－` 是文字，不是形状**。 |
| `test_普通号一字不动` 函数 | 110 | 0 | — |
| `test_不改调用方的dict` 函数 | 116 | 0 | 调用方常复用同一个 dict（pipeline 里就复用）——被就地改掉会很难查。 |
| `test_折完撞车会报IntegrityError而不是静默写第二行` 函数 | 122 | 0 | ⚠ **行为变化**（有意）：以前全角/半角是两个不同的串，所以"同一标准两份文件"能并存。 |
| `test_裸INSERT入口_bulk_也折` 函数 | 141 | 0 | `bulk.py` 用自己的 INSERT（不过收口）——源码级检查它确实调了对应折法。 |
| `test_UPDATE入口_auto_tag_也折` 函数 | 155 | 0 | — |
| `test_查重侧也要折_全角号能查到半角行` 函数 | 162 | 0 | §11.0 R6c-3d（复核 b33 的次高风险）：**写入折了、查重不折** ⇒ 全角重复件会绕过护栏、。 |
| `test_入口清单与实现一致` 函数 | 177 | 0 | 入口清单要"能逐条核"（b32 就是靠逐条点名找到漏口的），且清单本身要**承认不完备**。 |
| `TestOCR循环脚本` 类 | 208 | 0 | `var/ocr-loop/ingest_from_manifest.py`（**已入库 53 个跟踪文件之一**，不是随手脚本）。 |
| `_mod` 函数 | 218 | 3 | — |
| `test_GBZ_T_不再退化成裸前缀` 函数 | 228 | 0 | — |
| `test_普通号与GB分支不变` 函数 | 234 | 0 | — |

### `tests/test_supervisor.py`（8 个符号）

> 阶段2.1 supervisor 测试：用假子进程模拟崩溃/恢复/熔断，不启动真引擎。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `FakeChild` 类 | 7 | 5 | 按脚本依次决定退出码的假引擎进程。 |
| `__init__` 函数 | 10 | 135 | — |
| `start` 函数 | 16 | 323 | — |
| `join` 函数 | 19 | 732 | — |
| `is_alive` 函数 | 24 | 17 | — |
| `test_supervisor_restarts_then_clean_exit` 函数 | 28 | 1 | — |
| `test_supervisor_circuit_break` 函数 | 40 | 1 | — |
| `test_supervisor_no_restart_on_clean` 函数 | 51 | 1 | — |

### `tests/test_t06.py`（13 个符号）

> T06 测试：分型核验器三型拦截 + Prompt 构造 + SSE 核验事件（mock LLM）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_pass_through` 函数 | 23 | 1 | — |
| `test_modality_weakened_intercepted` 函数 | 31 | 1 | — |
| `test_modality_strengthened_warns_not_blocks` 函数 | 41 | 1 | — |
| `test_number_tampered_intercepted` 函数 | 49 | 1 | — |
| `test_number_pdf_space_artifact_not_flagged` 函数 | 57 | 1 | 2026-09-06 真机回归（GB 30871-2022 §9.1 吊装分级实测）：PDF 宽字距数字。 |
| `test_mention_only_clause_not_modality_missing` 函数 | 74 | 1 | 2026-09-06 真机回归第二轮（吊装答案引用 §5.1.1 仅作区分）：条款号出现在。 |
| `test_number_selective_quote_not_flagged` 函数 | 107 | 1 | E2E 真实案例回归：证据同时含 10m/30m/60m，LLM 只引用 10m —— 不是篡改。 |
| `test_numeric_semantic_equivalence_passes` 函数 | 118 | 1 | 阶段2.1 评审 P1 案例回归：语义等价的数值变体不应误拦。 |
| `test_numeric_real_tamper_still_blocked` 函数 | 136 | 1 | 防回退：百分比容差方案会放过真篡改，浮点严格相等必须仍拦截。 |
| `test_fabricated_clause_intercepted` 函数 | 152 | 1 | — |
| `test_legal_exception_missing_intercepted` 函数 | 160 | 1 | — |
| `test_evidence_prompt_minimal` 函数 | 169 | 1 | — |
| `test_sse_verification_event_with_mock_llm` 函数 | 178 | 1 | SSE 全链路：mock 掉 LLM 流（无 Key 场景走占位答案），核验事件带真实结果。 |

### `tests/test_table_binding.py`（7 个符号）

> E5 表格绑定「物理就近优先」规则测试（2026-09-02，契约更新）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_t` 函数 | 20 | 119 | — |
| `_cl` 函数 | 25 | 23 | — |
| `test_caption_number_must_not_steal_chapter_clauses` 函数 | 29 | 1 | 回归核心（物理就近语义）：题注"表1/表2"不得撞号挂到章级条款 1/2。 |
| `test_table_follows_physical_position_over_reference` 函数 | 51 | 1 | 物理就近优先于引用（新语义）：表5 物理落在章"4"之后（4其他 独立成章、。 |
| `test_appendix_table_binds_appendix_clause` 函数 | 66 | 1 | 附录表（表A.1）挂附录条款。 |
| `test_word_boundary_no_false_reference` 函数 | 80 | 1 | 引用判定词边界："表1.1"不算引用"表1"。 |
| `test_multi_table_same_clause_append` 函数 | 94 | 1 | 同一条款多张表（正表+续表）保持追加语义，不覆盖。 |

### `tests/test_table_position_render.py`（4 个符号）

> 2026-09-01 表格归位渲染（"表格到处跑"修复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_seed` 函数 | 20 | 20 | conftest 库为 session 级共享 → 每次先删旧档再种（幂等）。 |
| `test_tables_interleaved_back_to_source_pages` 函数 | 51 | 1 | 表甲（第10页）插在第10页两行之后、12页页界之前。 |
| `test_tables_tail_append_without_spans` 函数 | 63 | 1 | 无表格 span（存量文档）→ 旧末尾追加行为，零变化。 |
| `test_tables_tail_append_on_span_count_mismatch` 函数 | 69 | 1 | span 数与 <table> 数不对齐（旧库部分 span 丢失）→ 宁可缀尾不可错位。 |

### `tests/test_term_bridge.py`（25 个符号）

> 术语桥（P1 第 2 步）的单元判据。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_term_entry_re_splits_number_name_english_and_definition` 函数 | 37 | 1 | — |
| `test_term_entry_re_accepts_unnumbered_and_dotted_numbering` 函数 | 44 | 1 | — |
| `test_term_entry_re_rejects_full_width_paren_numbering_and_that_is_measured` 函数 | 53 | 1 | 全角括号编号（`（3）危险作业 …`）**收不下** —— 这是**有意的边界，不是洞**。 |
| `test_term_entry_re_rejects_rows_without_an_english_name` 函数 | 66 | 1 | 没有英文名的行**不是**术语条款 —— 拒掉才不会把正文句子当成术语。 |
| `test_term_entry_re_requires_a_chinese_definition_after_the_english_name` 函数 | 72 | 1 | 英文名后面必须还有中文 —— 否则只是一行英文标题。 |
| `test_merge_round_robin_interleaves_rather_than_concatenates` 函数 | 78 | 1 | **这条是 P1 扇出收益的机制**：轮转必须让第二份的第一条**插在**第一份的第二条前面。 |
| `test_merge_round_robin_dedups_keeping_first_occurrence` 函数 | 89 | 1 | — |
| `test_merge_round_robin_tolerates_empty_and_missing_lists` 函数 | 94 | 1 | — |
| `test_topk_by_cos_numpy_path_agrees_with_the_python_reference` 函数 | 101 | 1 | — |
| `test_topk_by_cos_ties_break_by_smallest_index_on_both_paths` 函数 | 112 | 1 | 同分必须**按下标**定序，否则两条实现会在边界上给出不同答案。 |
| `test_topk_by_cos_ties_break_by_smallest_index_even_when_unsorted_prefix` 函数 | 125 | 1 | 并列 + `argpartition` 前缀乱序时，仍必须按小下标取。 |
| `test_topk_by_cos_head_is_sorted_and_that_assertion_is_not_vacuous` 函数 | 138 | 2 | **返回的头必须是降序**——而且这条用例的前提本身要被机械检查。 |
| `test_topk_by_cos_caps_k_at_the_number_of_candidates` 函数 | 164 | 1 | — |
| `test_topk_by_cos_zero_vector_is_not_a_crash` 函数 | 169 | 1 | — |
| `test_term_index_save_load_round_trip` 函数 | 174 | 1 | — |
| `test_term_index_select_returns_empty_without_vectors` 函数 | 187 | 1 | — |
| `test_term_index_matrix_cache_invalidates_when_the_length_changes` 函数 | 192 | 1 | — |
| `test_term_index_matrix_cache_invalidates_when_the_candidate_set_is_replaced` 函数 | 200 | 1 | **等长换集**也必须失效（复核 2026-09-25 抓到的洞）。 |
| `test_term_index_matrix_is_normalised` 函数 | 214 | 1 | — |
| `_fake_conn` 函数 | 221 | 6 | — |
| `test_extract_term_entries_keeps_only_the_first_clause_per_term` 函数 | 230 | 1 | — |
| `test_extract_term_entries_keep_all_exposes_the_dropped_same_name_entries` 函数 | 242 | 1 | `keep_all=True` 把**同名**的其余定义也取出来 —— 把"有损"变成可实验的东西。 |
| `test_extract_term_entries_strips_wrapping_punctuation_and_folds_whitespace` 函数 | 267 | 1 | — |
| `test_extract_term_entries_skips_non_term_rows` 函数 | 274 | 1 | — |
| `test_saved_cache_keeps_the_field_names_the_script_expects` 函数 | 280 | 1 | `measure-term-bridge.py` 按字段名读缓存。 |

### `tests/test_text_utils.py`（41 个符号）

> OCR 折行清洗公共模块测试（2026-08-23）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_join_plain_wrap` 函数 | 5 | 1 | 普通折行（CJK 直连）→ 拼接。 |
| `test_keep_para_boundary` 函数 | 10 | 1 | 句末标点 + 下一行是编号/条款 → 保留段落断行。 |
| `test_ascii_space` 函数 | 16 | 1 | 字母数字跨界拼接补空格。 |
| `test_idempotent` 函数 | 22 | 7 | 幂等：已清洗文本再执行无变化。 |
| `test_empty_and_none` 函数 | 30 | 2 | — |
| `test_katex_hat_and_bar` 函数 | 39 | 1 | 说明行 ^Ci→\hat{C}_{i}、C̄i→\bar{C}_{i}。 |
| `test_katex_body_zero_touch` 函数 | 49 | 1 | 正文段（无 ——— 说明行）e^x 零误伤。 |
| `test_katex_idempotent` 函数 | 55 | 1 | 幂等：已处理段不再嵌套。 |
| `test_katex_weave_pipeline` 函数 | 62 | 1 | weave → katex 全链路：34406 3.7 原文形态。 |
| `test_hier_from_no` 函数 | 75 | 1 | 标准号 → 效力层级：GB/T、GB/Z 推导。 |
| `test_std_type_by_hierarchy` 函数 | 85 | 1 | 层级 → standard_type：推荐性/指导性/强制。 |
| `test_pua_bond_dash` 函数 | 97 | 1 | PUA 键横线 → em dash：34406 §4 原文形态。 |
| `test_sup_unit_exponents` 函数 | 109 | 1 | 单位负指数 → <sup> 上标：cm-1 波数形态。 |
| `test_space_clause_numbers` 函数 | 121 | 1 | 段首条款编号补空格：4原理→4 原理。 |
| `test_ingest_trio_text` 函数 | 134 | 1 | 入库路三件套（纯文本形态，GB/T 34406 §4 原文）：—/cm⁻¹/编号空格 + 幂等。 |
| `test_exit_ingest_form_converged` 函数 | 149 | 1 | 形态收敛：入库路产出的干净形态过出口重放零变化（新旧文档渲染同形）。 |
| `test_strip_formula_leader_label_inner_space` 函数 | 160 | 1 | 缺陷证据：VLM 把 'C.3' 识别成 'C. 3'，编号捕获紧排 → 整条不匹配、点线原样落库。 |
| `test_strip_formula_leader_bare_threshold_aligned` 函数 | 171 | 1 | 裸点线阈值与检测器对齐：6 个 ASCII 点即剥（原 7 点 → 差一处就漏网）。 |
| `test_strip_formula_leader_reverse_controls` 函数 | 183 | 1 | 反向对照（修复纪律要求）：正文合法形态必须存活，不许被引导线规则误伤。 |
| `test_strip_formula_leader_idempotent` 函数 | 196 | 1 | 幂等：清洗后文本不再命中两条规则。 |
| `test_clean_clause_text_is_single_owner` 函数 | 205 | 1 | `clean_clause_text` = 入库与评估共用的**唯一**清洗次序。 |
| `test_clean_clause_text_shape_invariants` 函数 | 234 | 1 | 行数与长度不变形、空输入安全、幂等——入库靠行号定位页界，字形不得改行数。 |
| `test_strip_watermark_lines_removes_pirate_site_headers` 函数 | 249 | 1 | 盗版站水印行整行删除（裸 URL 与"短标签+URL"两族）。 |
| `test_strip_watermark_lines_keeps_real_citations` 函数 | 264 | 1 | **反向对照（关键）**：正文里的合法 URL 与参考文献引用必须一字不动。 |
| `test_strip_watermark_lines_rejects_bare_domain_pattern` 函数 | 290 | 1 | **回归护栏**：判据不得放宽为裸域名，否则普通条款被误判成 URL。 |
| `test_strip_watermark_lines_removes_aspose_tool_watermark` 函数 | 317 | 1 | 工具水印（无 URL）必须清除——旧守卫只认 URL 载体，使整族漏网。 |
| `test_strip_watermark_lines_drops_header_tail_but_keeps_body_intact` 函数 | 334 | 1 | **行尾页眉**（不锚行首）必须剥掉，且正文一字不动。 |
| `test_strip_watermark_lines_aspose_strips_inline_but_keeps_body` 函数 | 351 | 1 | **关键**：水印被拍进长单行中间时，只删水印、**正文一字不动**。 |
| `test_strip_watermark_lines_keeps_standard_refs_in_body` 函数 | 364 | 1 | **反向对照（关键）**：正文里的标准号引用/表数据不得被当成页眉删掉。 |
| `test_strip_watermark_lines_aspose_idempotent` 函数 | 382 | 1 | 幂等：重复清洗结果不变（清洗链可重入的前提）。 |
| `test_clean_clause_text_strips_watermark_in_chain` 函数 | 390 | 1 | 水印剥离已接入清洗链（`clean_clause_text`），入库与评估同源生效。 |
| `test_pua_decor_stripped_to_space` 函数 | 402 | 1 | 装饰类 PUA（项目符号/表格分隔/版权页位标）→ 空格。 |
| `test_pua_meaningful_codepoints_survive` 函数 | 421 | 1 | **反向对照（关键）**：有语义、但拿不到确定真值的码点必须原样保留。 |
| `test_pua_separator_original_cases_intact` 函数 | 438 | 1 | 首轮两个分隔符码点的原有行为不得回归。 |
| `test_strip_duplicate_suffix_only_touches_the_tail` 函数 | 460 | 1 | 只吃**结尾**的 `(数字)`。 |
| `test_clean_standard_name_strips_prefix_and_dup_suffix` 函数 | 484 | 1 | 文件名 → 干净名：剥开头标准号 + 去结尾副本后缀。 |
| `test_derive_standard_keeps_cleaned_name` 函数 | 506 | 1 | `scripts/_stdparse.derive_standard`：清理过的名**不许**被原始 stem 覆盖回去。 |
| `test_looks_like_binary_bytes_is_the_real_byte_path` 函数 | 532 | 1 | **字节**入口才认得出 PNG/JPEG（文本入口那些签名是死分支）。 |
| `test_looks_like_binary_bytes_only_reads_the_head` 函数 | 552 | 1 | 签名必须在**开头**。 |
| `test_looks_like_binary_text_path_reaches_only_ascii_heads_and_nul` 函数 | 561 | 1 | **文本**入口的诚实边界（复核指出原测试制造了假信心）。 |
| `test_looks_like_binary_known_false_positives_are_documented` 函数 | 585 | 1 | **已知误伤**（复核 2026-09-17 的 LOW）：不再声称"零误伤"，而是把它们钉成事实。 |

### `tests/test_threadpool_bound.py`（17 个符号）

> 线程池容量必须**显式有界**（§10.81，独立复核 b13 的 MEDIUM-1）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_收窄函数真的把线程池设成常量` 函数 | 22 | 0 | — |
| `test_线程池收窄是按事件循环的` 函数 | 38 | 0 | §10.88（独立复核 b17 的 MEDIUM-1）：**第二个事件循环**也必须被收窄到 16。 |
| `test_常量不会比默认值更大` 函数 | 67 | 0 | — |
| `test_每个请求都会尝试收窄` 函数 | 73 | 0 | 挡"有人把中间件里那一行删了"：拿替身记录它被调用过。 |
| `TestHeavyGate` 类 | 85 | 1 | 重活闸门：**重活路径**上必须 acquire/release，**轻活路径**不许碰它。 |
| `test_重活路径表覆盖了那些被量出秒级的端点` 函数 | 93 | 0 | — |
| `test_laws_里两条廉价端点不被关进闸门` 函数 | 114 | 0 | §10.93：`/laws/*` **只逐条列重活**，不用前缀——否则会顺手把两条廉价端点也关起来。 |
| `test_asyncio_to_thread_绕过_anyio_闸门` 函数 | 131 | 0 | **§10.93 的立论**：`asyncio.to_thread` 不受 anyio 那道 16 令牌的约束（所以禁用）。 |
| `test_轻活路径不占重活闸门` 函数 | 195 | 0 | — |
| `test_重活路径会_acquire_并_release` 函数 | 215 | 0 | — |
| `test_廉价的前缀例外不被关在闸门里` 函数 | 237 | 0 | `/ingest/preview/inbox` 只是列目录 ⇒ 必须在 `HEAVY_SKIP` 里（**闸门自己不许造排队**）。 |
| `test_重活闸门真的把并发卡在_HEAVY_TOKENS` 函数 | 244 | 0 | **行为级**：真发 `HEAVY_TOKENS * 3` 条并发重活请求，并发峰值必须**恰好**是 `HEAVY_TOKENS`。 |
| `_spy` 函数 | 309 | 6 | 一个记账替身 limiter + 让它成为闸门用的 limiter。 |
| `test_流式响应的令牌要等响应体发完才放` 函数 | 332 | 0 | **为什么闸门必须是纯 ASGI**（b14 的 MEDIUM-1）。 |
| `test_异常或截断路径也必须释放且只放一次` 函数 | 383 | 0 | `app` 中途抛错（或从不发最后一块）⇒ `finally` 兜底释放，**且只放一次**。 |
| `test_闸门缓存不会把死循环留在字典里` 函数 | 417 | 0 | LOW-4：缓存键必须是**循环对象**（弱引用字典），不是 `id(loop)`。 |
| `test_非重活路径在中间件这一层就不碰闸门` 函数 | 444 | 0 | 轻活路径连 `acquire` 都不该调（不是"调了又立刻放"——那也会排队）。 |

### `tests/test_toc_ingest.py`（16 个符号）

> 目录页摄入修复（2026-09-15）：`toc-ingested-as-clauses` 头部类根因回归。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_t` 函数 | 28 | 119 | — |
| `test_toc_entry_predicate_positives` 函数 | 35 | 1 | 目录条目四种实测形态全命中（含并块）。 |
| `test_toc_entry_predicate_reverse_controls` 函数 | 44 | 1 | **反向对照**：不带点线页码尾的正文/章头/表格数值行一律不认。 |
| `test_toc_entry_regex_requires_page_tail` 函数 | 60 | 1 | — |
| `test_toc_page_not_ingested_as_clauses` 函数 | 80 | 1 | **缺陷现场重放**：目录页整页不得产出任何条款。 |
| `test_toc_single_entry_blocks_not_ingested` 函数 | 101 | 1 | 逐行成块的目录条目（GB/T 28853-2012 形态）不得成为条款。 |
| `test_toc_no_dots_block_is_toc_entry` 函数 | 133 | 1 | 无点线目录块命中第二签名（实测原文）。 |
| `test_toc_no_dots_reverse_controls` 函数 | 138 | 1 | **反向对照**：正文多行块不得被第二签名吃掉。 |
| `test_toc_no_dots_then_dots_block_not_ingested` 函数 | 152 | 1 | **缺陷现场重放**：无点线目录块 + 其后的点线目录块都不得成为条款。 |
| `test_index_entry_predicate` 函数 | 184 | 1 | 索引条目签名（词条 + 点线 + **小数页码**），且单行不认。 |
| `test_untitled_index_entries_not_absorbed` 函数 | 206 | 1 | **索引没有标题块**时，条目也不得进正文（`_is_index_entry` 的用途）。 |
| `test_index_head_predicate` 函数 | 222 | 1 | 只有"整块恰为索引"才算索引起始（含空格变体）。 |
| `test_index_head_accepts_prefixed_titles` 函数 | 236 | 1 | 前缀白名单：`中文索引`/`英文索引`/`术语索引` 也是索引起始。 |
| `test_prefixed_index_section_not_absorbed` 函数 | 256 | 1 | 前缀索引标题之后的词条也不得进条款（缺陷现场重放，GB/T 13964-2008 形态）。 |
| `test_index_section_not_absorbed_into_clause` 函数 | 280 | 1 | **缺陷现场重放**：索引小节不得并入前一条款，正文必须保留。 |
| `test_index_section_does_not_eat_preceding_clauses` 函数 | 303 | 1 | 反向对照：索引**之前**的条款必须完好（索引态不得提前置位）。 |

### `tests/test_understanding.py`（17 个符号）

> Phase 9.2 Query Understanding Layer 测试（R9/R40/R41/R52/R53/R60）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_intent_classification` 函数 | 7 | 1 | — |
| `test_slot_extraction_and_declared` 函数 | 16 | 1 | — |
| `test_v1_slot_table_removed` 函数 | 26 | 1 | Task 13.1 死代码清除：v1 槽位表函数已删除（追问 v2 由 LLM 自判）。 |
| `test_clarify_event_when_missing` 函数 | 33 | 1 | R9 v2：不再用规则槽位表预先追问——统一先检索，由 LLM 单次自判（问还是答）。 |
| `test_no_clarify_when_slots_full` 函数 | 44 | 1 | R9 免追问：带前置声明 \[甲类/高层\] → 直接出答案。 |
| `test_condition_filter_and_rank` 函数 | 64 | 1 | — |
| `test_rank_with_hierarchy_gbt_is_a_national_standard` 函数 | 84 | 1 | **`GB/T` 必须与国家标准的位阶相符**（2026-09-17 实测补漏，§10.51）。 |
| `test_standard_type_is_a_real_sort_term_not_a_dead_one` 函数 | 111 | 1 | `standard_type` 那一项**曾经是死项**（2026-09-17 独立复核 b7 的 MEDIUM-4）。 |
| `test_fetch_full_clause_fills_standard_type` 函数 | 142 | 1 | `fetch_full_clause` 必须把 `doc_meta.standard_type` 带出来（否则排序项又成死项）。 |
| `test_sufficiency_note` 函数 | 171 | 1 | — |
| `test_special_work_theme_no_clarify` 函数 | 178 | 1 | R9 追问合理性：高处作业分级是规则查询，不追问建筑参数，直接检索。 |
| `test_theme_missing_slots` 函数 | 189 | 1 | — |
| `test_theme_scoped_slots` 函数 | 198 | 1 | 通用主题作用域：特殊作业不提取建筑高度槽位（不做死标签）。 |
| `test_grade_question_is_rule_query` 函数 | 216 | 1 | — |
| `test_refine_search_query` 函数 | 223 | 1 | — |
| `test_title_clause_expansion` 函数 | 230 | 1 | 命中标题条款（8.1 作业分级）应附带子条款（8.1.1 分级内容）。 |
| `test_correction_detection` 函数 | 273 | 1 | — |

### `tests/test_unsupported_context.py`（7 个符号）

> `unsupported_context` 回归测试（D 线"资格声明"，2026-09-16 新建）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ev` 函数 | 26 | 39 | — |
| `test_same_standard_not_retrieved_is_actionable` 函数 | 39 | 1 | 情形 a：引用了**同一部标准**里未被检索的条款 → 应报"检索未召回"。 |
| `test_outside_evidence_standard_is_distinguished` 函数 | 54 | 1 | 情形 b：引用**本轮未讨论**的标准 → 应报 `outside_evidence_standard`。 |
| `test_no_standard_nearby_reports_unknown_never_guesses` 函数 | 66 | 1 | 情形 c：附近没有标准号 → 必须报 `unknown`，**不得猜**。 |
| `test_evidence_clause_produces_no_context_entry` 函数 | 79 | 1 | 反向对照：证据**内**的条款号不得产生任何 context 条目（不是告警对象）。 |
| `test_context_length_matches_unsupported_length` 函数 | 87 | 1 | 结构不变量：两条列表**一一对应**（消费方可以按下标配对）。 |
| `test_blocking_behaviour_unchanged` 函数 | 98 | 1 | **边界**：分类只增信息，**不放行**——证据外条款仍使 is_valid=False。 |

### `tests/test_update_announce.py`（28 个符号）

> 公告发现测试（契约增量见 pipeline/03「公告发现」节）：URL 归一化/SSRF/解析启发式/

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean_announce_state` 函数 | 22 | 1 | 同文件用例共享库：每用例前后清空源配置/扫描状态/已见公告，防串扰。 |
| `_FakeTransport` 类 | 36 | 13 | 按 URL 返回固定页面。 |
| `__init__` 函数 | 39 | 135 | — |
| `fetch` 函数 | 43 | 1027 | — |
| `_page` 函数 | 48 | 29 | 拼一个最小列表页：<a href>text</a> 序列。 |
| `_wait_done` 函数 | 54 | 40 | 轮询等待 daemon 扫描线程到终态（done/failed），返回最终 state。 |
| `test_ann_n01_normalize_url_variants` 函数 | 66 | 1 | 尾斜杠/默认端口/大写 host/追踪参数/fragment 归一为同串 → 同 hash。 |
| `test_ann_n02_private_url_rejected` 函数 | 90 | 1 | SSRF：内网 IP/loopback/.local/非 http(s) → True。 |
| `test_ann_n03_parse_normal_page_with_date_and_stdno` 函数 | 116 | 1 | 正常页：条目抽取/相对链接绝对化/日期变体归一/标准号识别/噪音过滤。 |
| `test_ann_n03b_directory_links_are_not_announcements` 函数 | 148 | 1 | **栏目导航链接不是公告**（2026-09-24 真机缺陷的判据）。 |
| `test_ann_n04_parse_empty_and_js_shell` 函数 | 178 | 1 | 空页 → parse_empty 语义交由调用方。 |
| `test_ann_n05_parse_item_cap_50` 函数 | 190 | 1 | 每页条目上限 50（truncated 标记）——防导航页误判成万条目。 |
| `test_ann_n06_parse_illegal_date_left_blank` 函数 | 198 | 1 | 非法日期（2026-13-45）诚实留空，不猜测。 |
| `test_ann_n07_source_crud_validation` 函数 | 206 | 1 | CRUD 校验矩阵：缺字段/内网拒绝 → UPD-3008。 |
| `test_ann_n08_no_source_cap` 函数 | 250 | 1 | **源数量不设上限**（2026-10-08 删 `SOURCES_MAX`）：加 60 条都应成功。 |
| `_mk_scan_world` 函数 | 271 | 11 | 造源 + fake transport：返回 (transport, urls)。 |
| `test_ann_n09_scan_baseline_then_dedup` 函数 | 281 | 1 | 首扫基线（不计新）→ 二扫去重 0 新 → 换源同 URL 两行隔离。 |
| `test_ann_n10_scan_new_items_and_recent` 函数 | 333 | 1 | 列表页新增条目 → new_count 与 recent（≤5）正确。 |
| `test_ann_n11_scan_failure_honesty` 函数 | 361 | 1 | 失败诚实：http 500 / 验证码页 / JS 壳 / 空 parse —— 每源 failed+reason，。 |
| `test_ann_n12_scan_409_running_gate` 函数 | 391 | 1 | 409 双闸：进程内已有扫描登记 → request_scan 抛 UPD-2006。 |
| `test_ann_n13_scan_stale_recovered` 函数 | 406 | 1 | 僵尸扫描自愈：state running 但进程内无登记 → 新扫描照常开（记审计）。 |
| `test_ann_n14_disabled_source_skipped` 函数 | 421 | 1 | 禁用源不抓取（不进 per_source 清单也不发 HTTP）。 |
| `test_ann_x15_export_reopenable` 函数 | 435 | 1 | xlsx 落 exports、openpyxl 重开：源状态 sheet（逐源行）+ 明细全量行数。 |
| `test_ann_x16_export_empty` 函数 | 464 | 1 | 空库/从未扫描：同样出文件，明细仅表头。 |
| `test_ann_n17_discover_next_pages_js_pager` 函数 | 476 | 1 | **JS 拼的翻页**（应急管理部那种）：原始 HTML 里没有真 `<a>`，只有。 |
| `test_ann_n18_discover_next_pages_real_links_and_none` 函数 | 494 | 1 | **真 `<a>` 翻页链**收同目录的"下一页"。 |
| `test_ann_n19_scan_walks_pages` 函数 | 509 | 1 | **翻页真的翻**：列表 3 页（第 2/3 页由 `index_1/index_2.shtml` 拼）。 |
| `test_ann_n20_scan_stops_when_caught_up` 函数 | 537 | 1 | **追上历史就提前停**：所有条目都见过时，不许把预算页数全翻完。 |

### `tests/test_update_api.py`（13 个符号）

> 阶段六·批次5：更新模块 API 接线测试（pipeline/02 §3 端点契约）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_update_endpoints_require_token` 函数 | 46 | 1 | 无 token 一律 401（除 health 外全站口径），错误体 unauthorized。 |
| `test_classify_hit_and_broad_two_modes` 函数 | 57 | 1 | classify 正常态（唯一 leaf 命中给路径）/ 过泛态（一轮追问 ≤3 问）。 |
| `test_search_drill_level_over_limit_error_code` 函数 | 79 | 1 | drill_level=4 → 422 / UPD-3002（校验层冻结码。 |
| `test_pause_resume_and_get_missing_batch_404` 函数 | 91 | 1 | 批次不存在：GET 进度 / pause / resume 均 404 + UPD-2003。 |
| `test_watchlist_add_list_remove_idempotent_chain` 函数 | 109 | 1 | F-18 幂等链：add → list → 重复 add 不翻倍 → remove → 空 → 再 remove 无操作。 |
| `test_report_missing_batch_business_error` 函数 | 148 | 1 | report 对不存在批次 → 404 业务错误码 UPD-2003（不产出文件）。 |
| `test_manual_illegal_status_422_module_frozen_code` 函数 | 165 | 1 | manual 非法 legal_status → 422。 |
| `test_ack_missing_change_404` 函数 | 184 | 1 | ack 对不存在变更事件 → 404 / UPD-2002。 |
| `test_batches_and_changes_listing_shape` 函数 | 193 | 1 | 历史批次与变更明细列表端点：包裹格式正确、返回 list（空库亦然）。 |
| `test_subscriptions_get_default_all_enabled` 函数 | 208 | 1 | 订阅 GET：缺省全开（vocab 全量 enabled=True）。 |
| `test_subscriptions_put_save_and_get_consistent` 函数 | 220 | 1 | 订阅 PUT：全量替换保存后 GET 一致。 |
| `test_subscriptions_illegal_tag_422` 函数 | 238 | 1 | 订阅 PUT：非法 tag → 422/UPD-3001，且不落库（GET 仍为全开或上次状态）。 |
| `test_doc_full_clauses_returns_rich_text_with_page` 函数 | 249 | 1 | 2026-08-27 全文富文本预览接口：某文档全部条款含 content_html 与 page_start。 |

### `tests/test_update_channels.py`（57 个符号）

> 更新渠道适配器表驱动测试（pipeline/04a §2 INS-B 系列；全部离线零联网）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_cases` 函数 | 37 | 2 | — |
| `MockChannelTransport` 类 | 46 | 4 | 表驱动 mock 传输（零联网）：respond 按 seq 弹出、耗尽复用末条。 |
| `__init__` 函数 | 49 | 135 | — |
| `_next` 函数 | 55 | 2 | — |
| `fetch` 函数 | 62 | 1027 | — |
| `ProbeOutcome` 类 | 78 | 17 | 单轮探测结果：ChannelResult 或归一异常（UPD-1xxx），附上游调用数。 |
| `_probe_once` 函数 | 87 | 6 | 用该 case 的 mock 矩阵独立构建适配器并探测一次（每轮全新实例）。 |
| `_bucket_of` 函数 | 99 | 4 | 结果 → 四色桶（04a §4 映射）。 |
| `_expect_bucket` 函数 | 114 | 2 | fixture expect 子集 → 同口径期望桶。 |
| `_assert_expect_subset` 函数 | 132 | 2 | — |
| `test_每个链上的渠道名都能在适配套表里查到` 函数 | 144 | 0 | **接线不变量**：`routing.select_chain()` 返回的每个渠道名，都必须在。 |
| `test_ttzb_那一个渠道的键与名不一致要按名建表` 函数 | 171 | 0 | 具体到那个不一致的渠道：字典里必须能按 `ttbz`（链里的名字）取到。 |
| `test_httpx_自检能看出本机是否可用` 函数 | 181 | 0 | `httpx_usable()` 必须**既**能报可用、也能把不可用的原因变成一句人话。 |
| `test_两个栈都不可用时日志点名原因` 函数 | 191 | 0 | `curl_cffi` 缺 + httpx 构造失败 ⇒ **ERROR 且点名**，而不是一条 WARN 就回退。 |
| `test_httpx_可用时只打_WARN` 函数 | 218 | 0 | — |
| `_govcn_body` 函数 | 235 | 3 | 真接口响应形状（`searchVO.catMap.*.listVO`）——与 `law_source.govcn_client.parse_rows`。 |
| `_StubTransport` 类 | 244 | 4 | — |
| `__init__` 函数 | 245 | 135 | — |
| `fetch` 函数 | 250 | 1027 | — |
| `test_govcn_真接口命中_按摘要里的标准号` 函数 | 255 | 0 | **换棒的实证**（R1 的 G6：旧实现只解 mock dict ⇒ 真实网络恒 miss）。 |
| `test_govcn_真接口空结果算_miss_不算命中` 函数 | 280 | 0 | — |
| `test_govcn_旧的_mock_契约仍然可用` 函数 | 288 | 0 | 离线 fixture 走的是 mock 分支（`{"announcements": \[...\]}`）——换棒**不许**把它弄坏。 |
| `test_fixture_matrix_contract` 函数 | 300 | 1 | fixture 自检：≥12 行组合（INS-B-07 口径）、key 唯一、渠道与必填段齐全。 |
| `test_channel_matrix_deterministic_and_idempotent` 函数 | 311 | 1 | INS-B-07：逐组合断言字段唯一确定 + 两轮重跑逐位一致。 |
| `_combo_tuple_from_expect` 函数 | 344 | 2 | — |
| `test_combo_tuple_stable_across_rounds` 函数 | 349 | 1 | 全矩阵遍历：(channel, change_type, 色) 元组两轮恒等，无不确定场景。 |
| `test_captcha_marker_only_never_writes_db` 函数 | 366 | 1 | INS-C-01：captcha 结果只返回标记。 |
| `test_live_openstd_homepage_default_transport_200` 函数 | 415 | 1 | RUN_LIVE=1 时经新默认 transport（curl_cffi 指纹优先）GET openstd 首页断言 200。 |
| `test_official_gb_parses_real_openstd_html` 函数 | 459 | 1 | ANOM-003 回归：真实 HTML 结果表 → ChannelResult 正确（现行→effective/no_change、被代替→superseded）。 |
| `TestOfficialGb实施日期` 类 | 494 | 0 | R6c-3c：结果表里两个日期格，取**实施日期**（第 2 格）。 |
| `test_两个日期格取第二个` 函数 | 497 | 0 | — |
| `test_只有一个日期格时不猜` 函数 | 502 | 0 | ⚠ 一格时发布/实施**不可区分** ⇒ 两个槽都留空（§11.0 R6c-3f）。 |
| `test_没有日期格` 函数 | 514 | 0 | — |
| `test_多出第三格时仍取实施日期而不是最后一个` 函数 | 519 | 0 | 为什么取 `\[1\]` 而不是 `\[-1\]`：列**追加**比**重排**常见。 |
| `Test发布日期槽` 类 | 529 | 0 | §11.0 R6c-3e：`published_date`（发布）与 `effective_date`（实施）是两个槽。 |
| `test_official_gb_发布取第1格` 函数 | 536 | 0 | — |
| `test_official_gb_只有一格时发布留空` 函数 | 541 | 0 | ⚠ **不许把唯一那格当发布**：此时发布/实施不可区分，宁缺勿错。 |
| `test_ttzb_实施与发布各归各的槽` 函数 | 548 | 0 | b34 的真机反例：T/CECS 2350-2026 发布 2026-06-12、实施 2026-12-01。 |
| `test_ttzb_只有发布时实施留空` 函数 | 556 | 0 | 旧实现会把这个发布日期填进 `effective_date` —— 那正是要修的形态。 |
| `test_ttzb_三级回退顺序` 函数 | 562 | 0 | — |
| `TestNormNoFullWidth` 类 | 572 | 1 | §11.0 R6c-2a 实测的根因：真库 **92%** 的标准号写全角斜杠 `／`，而站点返回半角 `/`。 |
| `test_全角与半角斜杠归一到同一个号` 函数 | 580 | 0 | — |
| `test_按归一号挑行时全角目标能命半角行` 函数 | 588 | 0 | 这条是"匹配失手"的最小复现：目标写全角、站点返回半角。 |
| `TestNdlsRefererIsAscii` 类 | 596 | 1 | §11.0 R6c-2a（独立复核 b30 定位）：`ndls` 把**原始标准号**拼进 Referer，。 |
| `test_全角号不再让请求发出前就炸` 函数 | 613 | 0 | — |
| `test_referer_是纯_ascii_且关键词被转义` 函数 | 620 | 0 | — |
| `TestQueryUsesHalfWidthForm` 类 | 632 | 1 | §11.0 R6c-2b：适配器**查询**必须用半角规范形（`query_no`）。 |
| `test_送出去的请求里没有全角斜杠` 函数 | 664 | 0 | — |
| `test_query_no_不打乱既有写法` 函数 | 681 | 0 | `query_no` 只换字符形状：**空格必须保留**（cssn/mee 实测"带空格完整号"才排第一）。 |
| `test_ndls_搜索体与_web_的_q_也必须用规范形` 函数 | 689 | 0 | b31 的反例：`ndls` 的 **JSON 搜索体**（可达渠道！）与 `web` 的 `q` 仍是原始全角。 |
| `TestNormNoDashes` 类 | 708 | 1 | 独立复核 b31 抓到的**真失配**：`norm_no` 原先**不折连字符**，而 `query_no` 与。 |
| `test_各种连字符都折成半角减号` 函数 | 715 | 0 | — |
| `test_与_canon_standard_no_在这些输入上一致` 函数 | 719 | 0 | — |
| `Test废止日期落自己的槽` 类 | 726 | 0 | §11.0 R6c-7：`withdrawn_date` 是**一等字段**（与 `doc_meta.withdrawn_date` 对齐）。 |
| `test_ndls_详情_实施与废止分槽` 函数 | 736 | 0 | — |
| `test_ndls_降级档_没有a206就不填废止日期` 函数 | 745 | 0 | ⚠ 不知道 ≠ 拿实施日期顶（这正是"按能力判定兜住"失败的现场）。 |
| `test_hbba_废止行_两个日期分槽` 函数 | 754 | 0 | — |

### `tests/test_update_discover.py`（22 个符号）

> 找标子模块测试（阶段六·批次3；pipeline/02 §1、F-15~F-18）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_no_llm_in_classify` 函数 | 38 | 1 | classify 默认禁用 LLM 兜底（测试确定性。 |
| `_load_fixture` 函数 | 46 | 5 | — |
| `DiscoverMockTransport` 类 | 50 | 5 | 表驱动 mock 传输（零联网）：按 params.q 包含 case.key 匹配应答。 |
| `__init__` 函数 | 53 | 135 | — |
| `fetch` 函数 | 57 | 1027 | — |
| `test_seed_tree_shape` 函数 | 67 | 1 | 24 大类齐全，每类 3~8 个二级子类，全部节点 source=seed 待扩充。 |
| `test_classify_broad_safety_asks_questions` 函数 | 83 | 1 | 「我要下载安全的国标」→ 一轮追问 ≤3 问，绝不硬选大类。 |
| `test_classify_fire_hits_unique_path` 函数 | 95 | 1 | 「消防」→ 唯一命中路径 C/C80 消防。 |
| `test_classify_leaf_shadows_branch_keyword` 函数 | 103 | 1 | 「消防安全」由 leaf 词遮蔽 branch 词，直接命中不追问。 |
| `test_classify_multi_hit_and_miss_both_ask` 函数 | 109 | 1 | 多 leaf 命中与完全未识别都走一轮追问，绝不猜测续跑。 |
| `test_classify_labor_protection_hits_c60` 函数 | 122 | 1 | 「劳保穿戴/劳动保护用品」→ 唯一命中 C/C60 劳动安全（2026-08-26 实测修复：。 |
| `test_classify_cleans_colloquial_noise` 函数 | 132 | 1 | 口语虚词清洗只作用于关键词匹配，不破坏既有语义。 |
| `test_llm_classify_hit_when_rules_miss` 函数 | 140 | 1 | 规则 miss 时 LLM 兜底：返回合法路径即采用（开放说法不再依赖词表穷举）。 |
| `test_validate_ccs_code_rejects_bad_codes` 函数 | 149 | 1 | LLM 输出的 code 必须 ∈ 种子树二级子类。 |
| `test_parse_llm_json_tolerates_noise` 函数 | 158 | 1 | LLM 输出容错：代码块围栏/前后缀不影响 JSON 提取。 |
| `test_llm_classify_caches_repeat` 函数 | 166 | 1 | 同描述重复分类只调一次 LLM（LRU 缓存，重复问零成本）。 |
| `test_search_rejects_drill_level_over_limit` 函数 | 190 | 1 | drill_level=4 拒绝：UpdateError 且错误码 UPD-3002（校验层）。 |
| `test_search_mock_three_cards_fields_complete` 函数 | 198 | 1 | mock 三条结果：卡片字段完整且与 fixture expect 逐位一致。 |
| `test_search_dedupes_and_skips_unparseable_rows` 函数 | 223 | 1 | 同号重复行去重保序。 |
| `test_search_http_miss_returns_empty_not_raise` 函数 | 234 | 1 | HTTP 非 200 不抛错返回 \[\]（与 channels._miss 同语义）。 |
| `test_search_transport_failure_normalized_to_upd1xxx` 函数 | 241 | 1 | 传输层异常归一：超时→UPD-1001，其余→UPD-1004。 |
| `test_download_later_add_idempotent_then_remove` 函数 | 266 | 1 | 加两次只一条（幂等）。 |

### `tests/test_update_inspector.py`（69 个符号）

> 巡检编排器测试（pipeline/04a §1 巡检编排 / §3 验证码 / §4 三色判定 + 批次2万级分层预算）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `InspectTransport` 类 | 42 | 7 | (channel, standard_no) 路由的表驱动 mock：seq 弹出、耗尽复用末条。 |
| `__init__` 函数 | 45 | 135 | — |
| `configure` 函数 | 53 | 62 | — |
| `_route` 函数 | 57 | 3 | — |
| `_parse_no` 函数 | 65 | 2 | — |
| `starts` 函数 | 72 | 55 | — |
| `fetch` 函数 | 78 | 1027 | — |
| `bump_year` 函数 | 114 | 4 | 仅换尾部年代（同主体新版）：GB/T X 0001-2020 → GB/T X 0001-2025。 |
| `r_eff` 函数 | 120 | 23 | — |
| `r_new` 函数 | 126 | 1 | — |
| `r_upcoming` 函数 | 133 | 3 | — |
| `r_state` 函数 | 140 | 6 | — |
| `add_doc` 函数 | 151 | 37 | — |
| `seed_inspected` 函数 | 170 | 6 | 预置一次历史巡检事件（使 doc 归入 tier1 / 已首检集合）。 |
| `mk_items` 函数 | 182 | 30 | — |
| `cfg_all` 函数 | 187 | 7 | — |
| `event_rows` 函数 | 194 | 8 | — |
| `change_events` 函数 | 211 | 20 | — |
| `t` 函数 | 217 | 3019 | — |
| `test_ins_a_01_smoke_five_effective_done` 函数 | 222 | 1 | /INS-A-01 5 号全现行：pending→running→done，checked=total=5，green=5 余 0。 |
| `test_ins_a_02_concurrency_two_pairwise` 函数 | 250 | 1 | /INS-A-02 峰值并发恒=2，按清单序两两成组推进。 |
| `test_ins_a_03_pause_resume_monotonic` 函数 | 277 | 1 | /INS-A-03 running 中 pause → paused → resume 续跑，checked 单调不回退。 |
| `test_ins_a_04_resume_from_checkpoint_no_dup_events` 函数 | 303 | 1 | /INS-A-04 跑到 3/10 断点（模拟进程重启），resume 自第 4 号续扫且无重复事件。 |
| `test_ins_a_05_timeout_retry3_then_failed` 函数 | 337 | 1 | /INS-A-05 单号 delay31>30s：预算 3 次耗尽记 failed，不阻塞他号、不误降级。 |
| `test_ins_a_06_resume_missing_batch_404` 函数 | 364 | 1 | /INS-A-06 不存在的 batch_id：UPD-2003 且零副作用。 |
| `test_ins_a_07_chaos_persistent_error_reaches_terminal` 函数 | 374 | 1 | /INS-A-07 第 2 号持续异常：终态 done+finished_at，无挂死，审计齐全。 |
| `test_ins_a_08_sqlite_exception_isolated` 函数 | 393 | 1 | /INS-A-08 中途注入一次 SQLite 异常：异常号隔离，其余照跑，批次可达 done。 |
| `test_ins_a_09_terminal_batch_refuses_restart` 函数 | 425 | 1 | /INS-A-09 终态批次：check/resume 拒绝重启，重复 pause 幂等返回同状态。 |
| `test_anom001_all_channels_unreachable_failed_not_done` 函数 | 447 | 1 | /ANOM-001 回归：三渠道全程不可达（生产 SSL EOF 场景）→ 批次终态 failed，。 |
| `_captcha_scene` 函数 | 481 | 5 | — |
| `test_ins_c_01_captcha_pauses_not_gray` 函数 | 493 | 1 | /INS-C-01 captcha=true：批次 paused、该号不计 gray/failed、聚合告警落库。 |
| `test_ins_c_02_resume_retries_same_number_first` 函数 | 512 | 1 | /INS-C-02 过点后 resume：同一号优先补查成功，批次续跑至 done。 |
| `test_ins_c_03_scheduler_never_auto_resumes_captcha` 函数 | 531 | 1 | /INS-C-03 paused 批次等一个调度周期：定时器不得自动 resume 验证码/人工暂停。 |
| `test_ins_c_04_three_captchas_one_aggregated_pause` 函数 | 548 | 1 | /INS-C-04 连续 3 号验证码：合并单次暂停一条告警。 |
| `test_ins_c_05_interleaved_pause_resume_state_machine` 函数 | 573 | 1 | /INS-C-05 交错 pause×2 / resume×2：无非法迁移，resume 生效一次不重复扫描。 |
| `test_ins_d_01_effective_green` 函数 | 589 | 1 | /INS-D-01 现行 → green，current_legal_status='effective' 落库。 |
| `test_ins_d_02_upcoming_treated_current` 函数 | 605 | 1 | /INS-D-02 upcoming 有新版：legal_status 如实 'upcoming'，不触废止对比流程。 |
| `test_ins_d_03_superseded_red_per_directive` 函数 | 622 | 1 | /INS-D-03 被代替(superseded) → 红（批次2指令：废止/替代→red。 |
| `test_ins_d_04_withdrawn_red` 函数 | 638 | 1 | /INS-D-04 废止 → red + change_type=withdrawn。 |
| `test_四棒链的最后一棒不被预算截断` 函数 | 652 | 0 | §11.0 R6c-3e：**链长 4 > MAX_ATTEMPTS(3) 时最后一棒以前永远探不到**（复核 b34 实测）。 |
| `test_单根链的重试预算不变` 函数 | 685 | 0 | 改预算是 `max(MAX_ATTEMPTS, len(链))` ⇒ **短链行为一字不变**（单根链仍有 3 次预算）。 |
| `test_某根棒抛异常不挤掉后面的棒` 函数 | 709 | 0 | §11.0 R6c-3f（复核 b36 的 D-新问题）：**全链共享重试池**会让异常吃掉后面的棒。 |
| `test_台账停用的渠道巡检不再问它` 函数 | 748 | 0 | §11.0 R6h：台账里 `enabled=0` 的渠道**真的不会被问**。 |
| `test_号段声明的渠道巡检真的会问它` 函数 | 781 | 0 | §11.0 R7：台账里**号段**声明的渠道，巡查**真的会去问**（接线，不是助手）。 |
| `test_全链都抛异常才算failed` 函数 | 817 | 0 | 每根棒各自重试到上限。 |
| `test_五类结论记进同一条事件` 函数 | 838 | 0 | §11.0 R6c-4c：**五类结论记进那一条事件的 `latest_info`**（不新增列、不写 ×5 条）。 |
| `test_灰号的五类记录说清为什么没答` 函数 | 870 | 0 | 整链都没命中（灰）也要能回答"五类各自为什么没答"（§11.0 R6c-4c）。 |
| `test_台账记down但真答了_五类仍如实记answered` 函数 | 887 | 0 | ⚠ 复核 b37 的 C 项（它列为最高风险）：**归因不能看台账 state**。 |
| `test_台账读失败要出声` 函数 | 916 | 0 | ⚠ 复核 b37 的 B 项：台账读失败时**零告警** ⇒ 与"本来就不该记"不可区分。 |
| `test_结构性unanswerable_不算done` 函数 | 943 | 0 | §11.0 R6c-4d：五类里有**结构性答不出来**（`no_capability`/`off_chain`）的号 ⇒ 批次不算 done。 |
| `test_提交后被杀_欠账从事件行收回` 函数 | 973 | 0 | §11.0 R6c-4e：**已提交号**的结构性欠账，在"进程被杀 → pause → resume"后仍要算数。 |
| `test_only_not_probed_不出现在unanswerable` 函数 | 1017 | 0 | ⚠ **`not_probed` 不许算进 `classes_unanswerable`**：那是"这次没轮到问"，不是"答不出来"。 |
| `test_ins_d_05_all_channels_miss_gray` 函数 | 1048 | 1 | /INS-D-05 三渠道查无 → gray，legal_status 保持 NULL，末渠道 govcn 兜底。 |
| `test_ins_d_06_illegal_enum_rejected_not_silent` 函数 | 1064 | 1 | /INS-D-06 非法枚举：CHECK 拒绝+回滚零脏行。 |
| `test_ins_d_07_replay_dedup_counts_not_doubled` 函数 | 1089 | 1 | /INS-D-07 相同 mock 序列重放判定：跨批同 doc 同结论跳过建行，计数不翻倍。 |
| `test_ins_d_08_mixed_twenty_identity` 函数 | 1108 | 1 | /INS-D-08 20 号混合四态：恒等式成立，已知样本判定全部正确。 |
| `test_retry_within_channel_before_degrade` 函数 | 1149 | 1 | /INS-B-06 编排层复核：前 2 次异常第 3 次命中 → 不提前降级仍由 official_gb 完成。 |
| `test_tier_selection_watch_and_first_check` 函数 | 1166 | 1 | tier0 = watch_list ∪ 未首检。 |
| `test_tier_selection_doc_bookmark` 函数 | 1181 | 1 | 增强③遗留（B 方案）：user_doc_bookmark（标准收藏）并入 tier0 高频巡检。 |
| `test_budget_override_stop_and_next_day_resume` 函数 | 1209 | 1 | 万级预算：覆盖值=3，当日达预算停留待次日，次日调度器恢复续跑。 |
| `test_budget_default_500_when_unconfigured` 函数 | 1245 | 1 | 默认 daily_full_sweep_budget=500（35k ÷ 500 ≈ 70 天一轮）。 |
| `_make_iso` 函数 | 1259 | 3 | 与 sqlite `datetime('now')` 同形的 UTC 串（`YYYY-MM-DD HH:MM:SS`）。 |
| `_backdate_all_scheduled` 函数 | 1268 | 4 | 把 scheduled 批次回拨到「**测试自己的现在（T0）**」之前。 |
| `test_scheduler_creates_due_batches_once` 函数 | 1291 | 1 | schedule_days 到期自动建批（scheduled），周期内不重复建。 |
| `test_scheduler_backdated_due_again` 函数 | 1308 | 1 | 距上次 scheduled 建 ≥N 天再次到期。 |
| `test_scheduler_disabled_when_zero` 函数 | 1323 | 1 | schedule_days≤0 视为关闭调度。 |
| `test_scheduler_thread_lifecycle` 函数 | 1331 | 1 | 轮询线程 start/stop 存活冒烟（2s 模式，测试用 50ms 加速）。 |
| `test_tier0_includes_subscribed_domain_docs` 函数 | 1341 | 1 | F-13/A15：订阅'消防'后，已首检的消防域标准被重新提入 tier0。 |
| `test_inspect_lists_exclude_laws` 函数 | 1374 | 1 | 法规（doc_type='法律法规'）不进查号巡检（无国标号，时效走 flk 溯源检查）。 |

### `tests/test_update_package.py`（8 个符号）

> 批次4：全量数据包导出/导入测试（F-26；pipeline/02 §1 data_package.py）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_seed_world` 函数 | 24 | 7 | 种一套最小业务数据：文档×2（含公告）/条款/批注/收藏/义务/变更事件。 |
| `test_pkg_01_export_brief_counts_match_direct_count` 函数 | 62 | 1 | 导出简报计数与直接 COUNT 一致。 |
| `test_pkg_02_announcement_pdf_and_quarantine_list` 函数 | 87 | 1 | 公告存档 PDF 随包拷贝。 |
| `test_pkg_03_tampered_checksum_rejected_zero_side_effect` 函数 | 114 | 1 | 篡改 checksum → 拒绝且零副作用：不建保护快照、不写台账。 |
| `test_pkg_04_manifest_missing_or_corrupt_rejected` 函数 | 134 | 1 | manifest 缺失 / 目录无 manifest / JSON 损坏 → 一律 package_manifest_missing。 |
| `test_pkg_05_non_empty_target_rejected_upd3003` 函数 | 155 | 1 | /UPD-3003 目标库非空拒绝。 |
| `test_pkg_06_strict_import_prepared_then_same_checksum_rejected` 函数 | 171 | 1 | strict 空库成功准备（含自动快照+简报）。 |
| `test_pkg_07_unknown_mode_rejected` 函数 | 203 | 1 | 未知导入模式在触碰任何文件前拒绝。 |

### `tests/test_update_report.py`（5 个符号）

> 批次4：更新检查结果 Excel 导出测试（F-05；pipeline/02 §1 report.py）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_mk_batch` 函数 | 27 | 3 | 建批 + 走 change_repo 公共写路径逐事件落库并同步四色计数。 |
| `test_rep_04_tier_grouping_and_trend_window` 函数 | 45 | 1 | tier 分组取自 bulk_import_batch 锚行。 |
| `test_rep_05_xlsx_export_reopenable_with_key_content` 函数 | 93 | 1 | Excel 版落盘 exports、openpyxl 可重开。 |
| `test_rep_06_xlsx_empty_batch_still_exports` 函数 | 139 | 1 | 空批次（total=0、零事件）也能出 xlsx：汇总全 0、明细仅表头。 |
| `test_rep_07_xlsx_missing_batch_upd2003_zero_side_effect` 函数 | 156 | 1 | 批次不存在：抛 UPD-2003 且不在 exports 目录产生任何 .xlsx。 |

### `tests/test_update_routing.py`（13 个符号）

> 渠道路由测试（2026-08 巡检渠道升级）：select_chain 按标准号特征正确路由。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_route_aq_to_ndls` 函数 | 22 | 1 | — |
| `test_route_engineering_to_ndls` 函数 | 31 | 1 | — |
| `test_route_group_to_ttbz` 函数 | 36 | 1 | — |
| `test_route_hj_to_mee` 函数 | 40 | 1 | — |
| `test_route_local_to_dbba` 函数 | 44 | 1 | — |
| `test_route_other_gb_to_ndls` 函数 | 48 | 1 | — |
| `test_全角号与半角号同链` 函数 | 59 | 0 | §11.0 R6c-3b：`select_chain` 是**第 7 个读原始号的站点**（R6c-2b 统一 6 个查询点漏了它）。 |
| `test_前缀首选要问路由本身` 函数 | 78 | 0 | R6c-3b：`first_route` 是"前缀首选"的**唯一来源**。 |
| `test_兜底链第二棒是状态权威而不是政策库` 函数 | 95 | 0 | R6c-3b 的核心断言（量出来的）：`ndls` 在 `govcn` 之前。 |
| `test_route_industry_to_hbba` 函数 | 111 | 1 | — |
| `test_route_no_feature_falls_back` 函数 | 116 | 1 | — |
| `test_route_foreign_prefix_no_match` 函数 | 121 | 1 | — |
| `test_降级链只有一个所有者` 函数 | 126 | 0 | §11.0 R6：兜底链**只有一份**，且 inspector 拿到的就是 routing 那个对象。 |

### `tests/test_vision.py`（4 个符号）

> Task 11.4 本地视觉反查测试：截图 OCR → 检索（本地 MinerU，零云端）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_image` 函数 | 9 | 6 | 生成含规范文字的小图（复用 var/vision_test.png 或现场生成）。 |
| `test_vision_locate_ocr_and_retrieve` 函数 | 27 | 1 | 端到端：图片 OCR 文本应能检索到库内条款（GB30871 5.2.x 系列）。 |
| `test_vision_locate_missing_image` 函数 | 50 | 1 | — |
| `test_vision_api` 函数 | 57 | 1 | — |

### `tests/test_watermark_own_standard.py`（20 个符号）

> 水印剥离的**上下文消歧**回归（2026-09-17 修，原为 strict xfail 缺口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_table_last_cell_survives_with_own_standard` 函数 | 65 | 1 | 传了自家标准号 → 表格末格（别人的标准号）不再被当成页眉删掉。 |
| `test_own_header_tail_is_still_removed` 函数 | 78 | 1 | 自家的行尾页眉仍必须删干净 —— 修缺口不等于把真页眉一起放过。 |
| `test_own_header_line_is_still_removed` 函数 | 85 | 1 | 整行即页眉（`^…$` 族）同样只按自家标准号判定。 |
| `test_foreign_standard_only_line_is_kept` 函数 | 91 | 1 | 整行只有**别的**标准号时，不再整行删除（那可能是一格独立成行的数据）。 |
| `test_own_standard_fullwidth_still_matches` 函数 | 97 | 1 | 库里的标准号可能是**全角斜杠**（实测 `GB／T 10067.6-2023`）。 |
| `test_header_written_without_slash_t_is_still_removed` 函数 | 107 | 1 | **页眉常把 `GB/T` 印成 `GB`**（实测 226 行属此类）→ 比较键必须只认"号 + 年"。 |
| `test_different_number_same_family_is_kept` 函数 | 122 | 1 | 同一个前缀族但**号不同** → 是别人的标准，必须保住（表格里的引用）。 |
| `test_different_part_same_number_is_kept` 函数 | 129 | 1 | 分册号不同（10029.2 vs 10029）→ 不同分册，必须保住。 |
| `test_fullwidth_slash_inside_text_is_not_matched` 函数 | 135 | 1 | **已知限制（有意保留，不修）**：正文里的全角斜杠标准号不被页眉判据识别。 |
| `test_legitimate_text_still_survives_with_own_standard` 函数 | 155 | 1 | 传 own_standard_no 不得削弱原有的"合法引用必存活"保证。 |
| `test_watermark_tokens_still_removed_with_own_standard` 函数 | 160 | 1 | URL / 工具水印两族与 own_standard_no 无关，仍应照删。 |
| `test_without_own_standard_behaviour_is_unchanged` 函数 | 173 | 1 | **不传 own_standard_no 时保持历史行为**（表格末格仍会被删）。 |
| `test_canon_standard_no` 函数 | 196 | 1 | — |
| `_middle_with_table_cell` 函数 | 202 | 6 | 一页 middle.json：正文里既有**自家页眉**（应删）又有**表格末格**（别人的标准号，应留）。 |
| `test_ingest_wiring_passes_own_standard` 函数 | 227 | 1 | **端到端接线**：`build_clause_models(doc_id, standard_no, …)` 必须把文档自己的。 |
| `test_ingest_removes_own_header_end_to_end` 函数 | 255 | 1 | 自家页眉（页码 + 本文档标准号）在真链路里仍被删掉。 |
| `test_ingest_inline_furniture_keeps_foreign_standard` 函数 | 268 | 1 | **行内**家具片段也已接上下文：引用**别的**标准的片段（表格末格）不再被剥掉。 |
| `test_ingest_short_block_keeps_foreign_standard` 函数 | 289 | 1 | **短块**（≤80 字）走切分层的家具剥离 —— 传了标准号后同样不再误删。 |
| `test_splitter_without_standard_keeps_historic_behaviour` 函数 | 307 | 1 | **向后兼容**：不传 `standard_no` 时，切分层的家具剥离仍是历史行为（一律剥掉）。 |
| `test_own_key_of_rejects_placeholder` 函数 | 321 | 1 | `_own_key_of` 必须把"看着不像标准号"的占位符挡回 None。 |

### `tests/test_web_ingest.py`（8 个符号）

> 部委公告 → 知识库正文入库（切片②）测试：效力档判定 / 正文抽取 / 真入库 / 去重 / 诚实归因。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_FakeTransport` 类 | 10 | 13 | — |
| `__init__` 函数 | 11 | 135 | — |
| `fetch` 函数 | 15 | 1027 | — |
| `test_web_i01_classify_status_priority` 函数 | 42 | 1 | 效力档判定：**先认"征求意见稿"**（标题里同时出现"办法"也要判成仅参考），。 |
| `test_web_i02_extract_body_text_drops_chrome` 函数 | 65 | 1 | 正文抽取：**去掉导航/脚本/页脚**，只留正文，且段落之间保留换行。 |
| `test_web_i03_ingest_writes_document_with_source_url` 函数 | 76 | 1 | 真入库：**令/规章**那种有"第X条"的正文走 `law_text` 通道，。 |
| `test_web_i04_no_clause_announcement_uses_single_clause` 函数 | 107 | 1 | **没有"第X条"的公告**（政府站常见）也要能入库：整篇作一条（编号"全文"），。 |
| `test_web_i05_draft_ingested_as_reference_and_failures` 函数 | 123 | 1 | **征求意见稿必须入库**（业主 2026-09-24 更正），但效力档是 `reference`（参考资料/仅参考）——。 |

### `tests/test_write_queue_bootstrap.py`（3 个符号）

> write_queue 消费端接线测试（2026-08-26，P2-①）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean_queue` 函数 | 14 | 3 | — |
| `test_worker_consumes_ingest_doc_and_skips_unknown` 函数 | 22 | 1 | — |
| `test_ingest_doc_missing_file_fails_cleanly` 函数 | 54 | 1 | 真实 handler：文件不存在 → failed（不悬挂、不抛穿线程）。 |

### `tools/gov-qa/adapters/__init__.py`（1 个符号）

> 政务问答采集 · 站点适配器登记处。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 524 | 103 | 按 key 载入适配器模块（延迟导入，免得没装的依赖拦住别的站）。 |

### `tools/gov-qa/adapters/_gd_hdjlpt_common.py`（6 个符号）

> 广东省级厅局「互动交流平台」（hdjlpt）· 共用采集引擎。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 54 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供增量续采，与 `_igi_common.existing_ids` 同义）。 |
| `_text` 函数 | 74 | 144 | — |
| `_ts` 函数 | 79 | 22 | — |
| `_post_list` 函数 | 85 | 13 | — |
| `_xsrf_token` 函数 | 98 | 6 | 从落地页响应里取 XSRF-TOKEN（优先响应 cookie，兜底 set-cookie 头）。 |
| `harvest_gd` 函数 | 114 | 99 | 按统一记录格式返回某广东厅局 hdjlpt 的留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/_hunan_hd_common.py`（2 个符号）

> 湖南全省统一互动平台（hd.hunan.gov.cn）· 共用采集基座。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 41 | 144 | — |
| `harvest_hunan` 函数 | 46 | 65 | 按统一记录格式返回该部门在湖南统一互动平台上的全部公开答复。 |

### `tools/gov-qa/adapters/_igi_common.py`（5 个符号）

> IGI 平台公共基座（`/IGI/nbhd/openGovmsgbox.do`）——**多省共用**的留言信箱开放接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 38 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供适配器做**续采**用，可选）。 |
| `_real` 函数 | 59 | 123 | 清洗后**只保留真实内容** —— 把 `null` / `None` / 空串一律当"没有"。 |
| `clean` 函数 | 73 | 197 | 去标签 + **还原 HTML 实体** + 压空白（答复正文是 HTML 片段）。 |
| `ts` 函数 | 93 | 61 | 毫秒时间戳 → `YYYY-MM-DD HH:MM:SS`。 |
| `harvest_igi` 函数 | 102 | 232 | 翻页取列表（仅已答复），逐条取明细拿答复正文，返回统一记录。 |

### `tools/gov-qa/adapters/_igi_multi.py`（2 个符号）

> IGI **多 siteId 适配器**的公共构造器（2026-10-09 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `strip_constant_geo` 函数 | 32 | 5 | 剥离**恒定**地域（= 门户/站点默认值），保留逐信变化的地域。 |
| `make_harvest` 函数 | 59 | 4 | 造一个遍历 `SITE_IDS` 的 `harvest(fetch, *, limit=None)`。 |

### `tools/gov-qa/adapters/_jact_common.py`（6 个符号）

> 江苏省级厅局「统一咨询投诉 / 咨询建言」平台（jact）· 共用采集引擎。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 101 | 197 | 去标签 + 压空白 + 解码 HTML 实体（答复正文是 HTML 片段）。 |
| `parse_list` 函数 | 113 | 5 | 解析列表响应（JS 文本）→ (totalRecord, \[每行 {tid,title,num,date}\])。 |
| `parse_detail` 函数 | 142 | 18 | 解析明细页 HTML → {规范标签: 值}（label/value 是相邻两个单元格）。 |
| `_post_list` 函数 | 171 | 13 | — |
| `existing_ids` 函数 | 190 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供增量续采）。 |
| `harvest_jact` 函数 | 224 | 62 | 按统一记录格式返回某江苏厅局 jact 信箱的留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/_jpaas_jact_common.py`（5 个符号）

> jpaas-jact 平台（`api-gateway/jpaas-jact-web-server`）· 共用采集引擎——**多市共用**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 40 | 197 | 去标签 + 压空白（答复正文可能是 HTML 片段）。 |
| `_field` 函数 | 47 | 10 | 从 `transact.transactData\[\]` 里按 fieldName 取值。 |
| `_answer` 函数 | 55 | 7 | 取答复：`transactOpinion\[\]` 中**最后一个非占位项** → (正文, 单位, 时间)。 |
| `_list_page` 函数 | 69 | 6 | — |
| `harvest_jpaas` 函数 | 81 | 6 | 翻页取某 jpaas-jact 栏目的已答复留言（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/_jpaas_jact_html_common.py`（5 个符号）

> jpaas-jact「留言选登」变体 · **列表 JSON + 明细 HTML** 公共引擎（多市共用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_cell_text` 函数 | 60 | 8 | — |
| `_norm` 函数 | 66 | 21 | 标签归一：**去掉全部空白 + 去尾部冒号**（扬州用「标 题：」「答复内容：」）。 |
| `parse_detail_html` 函数 | 74 | 2 | 解析明细 HTML：`<td>标签</td><td>值</td>` 相邻两格 → {规范键: 值}。 |
| `_env_page_from` 函数 | 95 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。 |
| `harvest_jpaas_html` 函数 | 104 | 5 | 翻页取某 jpaas-jact 栏目的已答复留言（问题 + 答复原文，明细为 HTML）。 |

### `tools/gov-qa/adapters/_liuyan_common.py`（6 个符号）

> 人民网「领导留言板」（liuyan.people.com.cn）· 共用采集基座。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_md5` 函数 | 78 | 2 | — |
| `_envelope` 函数 | 82 | 26 | 按逆向出的算法构造请求封套（返回 JSON 字符串）。 |
| `_headers` 函数 | 90 | 35 | — |
| `_clean` 函数 | 95 | 172 | 留言/答复正文以纯文本为主。 |
| `_ts` 函数 | 103 | 22 | — |
| `harvest_liuyan` 函数 | 109 | 10 | 抓版块（`stream="df"` 地方 / `"bw"` 部委）的**已办理**留言 + 官方答复。 |

### `tools/gov-qa/adapters/_post_list_common.py`（5 个符号）

> 「静态 `content/post_<id>.html` 列表」族 · 共用采集引擎（2026-10-10 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 48 | 197 | 去标签 + 还原实体 + 压空白（顺序沿用本仓既有教训：先去标签、再还原实体）。 |
| `parse_detail` 函数 | 55 | 18 | 把明细页的 `<th>/<td>` 对解析成字段 dict。 |
| `list_items` 函数 | 72 | 13 | 取第 `page` 页的 `\[(id, url, title)\]`。 |
| `harvest_post_list` 函数 | 87 | 3 | 翻列表页 + 逐条取明细，返回统一记录。 |
| `existing_ids` 函数 | 162 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供续采，与 `_igi_common.existing_ids` 同义）。 |

### `tools/gov-qa/adapters/_sczwfw_common.py`（2 个符号）

> 四川政务服务网「政民互动」平台基座（**全省按 areaCode 过滤，绕过瑞数 WAF**）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 41 | 172 | — |
| `harvest_sczwfw` 函数 | 47 | 45 | 遍历 咨询/建议/投诉 三类工单 → 逐条详情解析问答。 |

### `tools/gov-qa/adapters/_sd_jact.py`（2 个符号）

> 山东地市 jact 基座（**http**；列表支持 POST/GET 两种）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_env_page_from` 函数 | 30 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（把超长源分块采）。 |
| `harvest_jact_sd` 函数 | 39 | 16 | 采山东某市 jact 信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/_sd_jact_gw.py`（4 个符号）

> 山东地市 **jpaas-jact 网关** 基座（济南/烟台同款）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 31 | 172 | — |
| `_detail` 函数 | 37 | 6 | — |
| `_env_page_from` 函数 | 50 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（把超长源分块采）。 |
| `harvest_jact_gateway` 函数 | 59 | 5 | 采某市 jpaas-jact 网关信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/_was5_common.py`（2 个符号）

> TRS WAS5 检索中间件 · 共用采集逻辑（部级/省级站通用基座）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_pick` 函数 | 50 | 24 | — |
| `harvest_was5` 函数 | 58 | 4 | 按统一记录格式返回该站全部频道的问答。 |

### `tools/gov-qa/adapters/_zj_mhww_common.py`（2 个符号）

> 浙江「民呼我为统一平台」**地市级**共用引擎（`zxts.zjzwfw.gov.cn`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 43 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供**续采**，避免第二轮恒 0 新增）。 |
| `harvest_area` 函数 | 58 | 25 | 采某地市「民呼我为·办理公开」（问题 + 答复原文，字体混淆自动还原）。 |

### `tools/gov-qa/adapters/ah_kb.py`（4 个符号）

> 适配器：**安徽省直部门 · 共享问答知识库**（全省站群聚合，跨厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 52 | 144 | — |
| `_parse_items` 函数 | 56 | 8 | 从列表片段抠 (明细URL, 标题, 日期)。 |
| `_parse_detail` 函数 | 68 | 60 | — |
| `harvest` 函数 | 91 | 501 | 按 pageIndex 翻页取全省共享知识库列表，再逐条取各厅明细（按 id 去重）。 |

### `tools/gov-qa/adapters/ah_sthjt.py`（3 个符号）

> 适配器：**安徽省生态环境厅 · 问答知识库**（列表翻页 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 54 | 144 | — |
| `_parse_detail` 函数 | 58 | 60 | — |
| `harvest` 函数 | 85 | 501 | 按分类（默认 / 综合政务 401 / 生态保护 411）翻页取列表，再逐条取明细（按 id 去重）。 |

### `tools/gov-qa/adapters/ay_zmhd.py`（4 个符号）

> 适配器：**安阳市·政民互动**（`leader-mail/list`，市长信箱/连线政府/市长电话）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 71 | 172 | — |
| `_real` 函数 | 83 | 123 | — |
| `_norm_dt` 函数 | 88 | 7 | `2026/10/9 10:38:35` → `2026-10-09 10:38:35`（本模块统一格式）。 |
| `harvest` 函数 | 100 | 501 | 翻 3 个 `systemType` 的全部页。 |

### `tools/gov-qa/adapters/baoji_igi.py`（2 个符号）

> 适配器：**宝鸡市·政民互动信箱（IGI 平台，49 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 57 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 82 | 501 | 遍历宝鸡各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/baotou_igi.py`（2 个符号）

> 适配器：**包头市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 7 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 46 | 47 | 剥离**恒定**地域（= 门户/站点默认值）。 |
| `harvest` 函数 | 72 | 501 | 遍历包头各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/bb_hdjl.py`（7 个符号）

> 适配器：**蚌埠市·政民直通车·信件选登**（安徽第 5 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 109 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（增量续采用）。 |
| `_clean` 函数 | 142 | 172 | — |
| `_real` 函数 | 155 | 123 | — |
| `_get` 函数 | 160 | 16 | 带指数退避重试的取页（429/5xx 重试）。 |
| `_parse_list` 函数 | 181 | 18 | 列表 HTML 片段 → `\[{id, title, dept, date, url}\]`（去重、保序）。 |
| `_parse_detail` 函数 | 201 | 60 | 明细页 → `{question, answer, asked_at, answered_at, msg_type, dept, doc_num}`。 |
| `harvest` 函数 | 224 | 501 | 翻列表 HTML（pageIndex **0 起**）+ 逐条取明细。 |

### `tools/gov-qa/adapters/bj_hdjl.py`（5 个符号）

> 适配器：**北京市·政民互动·信件选登**（首都之窗门户信件库，Struts2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_parse_js_obj` 函数 | 55 | 3 | 把 `{page: {...}, result: \[{a:'x'}\]}` 这类 **JS 对象字面量**转成 Python dict。 |
| `_clean` 函数 | 69 | 172 | 去标签 + 压空白（正文是 HTML 片段），并还原 HTML 实体（`&#40;`→`(`）。 |
| `_sections` 函数 | 79 | 3 | 取所有被 `start`/`end` 注释夹住的片段（可能多段，如多个答复单位）。 |
| `_parse_detail` 函数 | 93 | 60 | 从明细 HTML 抽出 {question, answer, dept, answered_at}。 |
| `harvest` 函数 | 122 | 501 | 翻页取「信件选登」列表，逐条取明细拿问题/答复正文，返回统一记录。 |

### `tools/gov-qa/adapters/bz_hdjl.py`（7 个符号）

> 适配器：**亳州市·信件选登**（`/InFeedback/`，安徽第 3 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 71 | 172 | — |
| `_real` 函数 | 85 | 123 | — |
| `_parse_list` 函数 | 90 | 18 | 列表页 → `\[{id, title, url}\]`（去重、保序）。 |
| `_parse_total` 函数 | 106 | 6 | — |
| `_fields` 函数 | 118 | 3 | 从表格式详情里抽 `{字段名: 值}`。 |
| `_parse_detail` 函数 | 142 | 60 | 详情页 → 统一记录字段。 |
| `harvest` 函数 | 163 | 501 | 翻列表（服务端渲染）+ 逐条取详情。 |

### `tools/gov-qa/adapters/changzhi_igi.py`（2 个符号）

> 适配器：**长治市·政民互动信箱（IGI 平台，15 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 45 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 67 | 501 | 遍历长治各 siteId 取已答复信件。 |

### `tools/gov-qa/adapters/chifeng_igi.py`（2 个符号）

> 适配器：**赤峰市·政民互动信箱（IGI 平台，53 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 55 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 80 | 501 | 遍历赤峰各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/cq_hdjl.py`（4 个符号）

> 适配器：**重庆市·互动交流·留言选登**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 44 | 144 | — |
| `_cell` 函数 | 48 | 46 | 取明细表里 `键 → 值` 单元格的纯文本（th/td 通用）。 |
| `_parse_detail` 函数 | 54 | 60 | — |
| `harvest` 函数 | 70 | 501 | 翻完所有列表页，逐条取明细（按 URL 去重）。 |

### `tools/gov-qa/adapters/cq_igi.py`（1 个符号）

> 适配器：**重庆市人民政府·政民互动（IGI 平台，多 site）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 134 | 501 | 遍历重庆市门户 IGI 各 siteId，取已答复信件（含答复原文与归属）。 |

### `tools/gov-qa/adapters/cz_hdjl.py`（6 个符号）

> 适配器：**池州市·市长信箱·留言选登**（`/InFeedback/`，安徽第 2 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 68 | 172 | — |
| `_real` 函数 | 82 | 123 | — |
| `_parse_list` 函数 | 87 | 18 | 列表页 → `\[{id, title, url}\]`（去重、保序）。 |
| `_parse_total` 函数 | 105 | 6 | 从 `<pagination … pagecount="13" total="128">` 取总数与页数。 |
| `_parse_detail` 函数 | 118 | 60 | 详情页 → `{question, answer, asked_at, answered_at, msg_type, title}`。 |
| `harvest` 函数 | 178 | 501 | 翻列表（服务端渲染）+ 逐条取详情。 |

### `tools/gov-qa/adapters/danzhou_igi.py`（2 个符号）

> 适配器：**儋州市·政民互动信箱（IGI 平台，20 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 52 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 78 | 501 | 遍历儋州各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/fj_hdjl.py`（2 个符号）

> 适配器：**福建省人民政府门户 · 互动交流（12345 诉求公开 / 信件选登）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_reply` 函数 | 46 | 2 | 取一条明细的答复三要素。 |
| `harvest` 函数 | 63 | 501 | 按 `current` 翻列表，再逐条取答复（按 uid 去重）。 |

### `tools/gov-qa/adapters/gd_amr.py`（1 个符号）

> 适配器：**广东省市场监督管理局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_chaozhou.py`（1 个符号）

> 适配器：**潮州市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_com.py`（1 个符号）

> 适配器：**广东省商务厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_coop.py`（1 个符号）

> 适配器：**广东省供销合作联社**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_czt.py`（1 个符号）

> 适配器：**广东省财政厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_dara.py`（1 个符号）

> 适配器：**广东省农业农村厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_dfz.py`（1 个符号）

> 适配器：**广东省人民政府地方志办公室**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_drc.py`（1 个符号）

> 适配器：**广东省发展和改革委员会**（hdjlpt 同款平台）。年窗 8 条（2026-10-07 实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 19 | 501 | 按统一记录格式返回该委留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_dva.py`（1 个符号）

> 适配器：**广东省退役军人事务厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_edu.py`（1 个符号）

> 适配器：**广东省教育厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_eea.py`（1 个符号）

> 适配器：**广东省教育厅**（hdjlpt 同款平台）。年窗 14 条（2026-10-07 实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 19 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gbdsj.py`（1 个符号）

> 适配器：**广东省广播电视局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdaudit.py`（1 个符号）

> 适配器：**广东省审计厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdcss.py`（1 个符号）

> 适配器：**广东省人民政府参事室**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdgrain.py`（1 个符号）

> 适配器：**广东省粮食和物资储备局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdii.py`（1 个符号）

> 适配器：**广东省工业和信息化厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdjyj.py`（1 个符号）

> 适配器：**广东省监狱管理局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdstc.py`（1 个符号）

> 适配器：**广东省科学技术厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdwsxf.py`（1 个符号）

> 适配器：**广东省信访局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gdyjzx.py`（1 个符号）

> 适配器：**广东省人民政府发展研究中心**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_gzw.py`（1 个符号）

> 适配器：**广东省人民政府国有资产监督管理委员会**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_hrss.py`（1 个符号）

> 适配器：**广东省人力资源和社会保障厅**（hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_hsa.py`（1 个符号）

> 适配器：**广东省医疗保障局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_huizhou.py`（4 个符号）

> 适配器：**惠州市·民意直通车（县区信箱 + 局长信箱）** —— 惠州自己的 Spring Boot 平台。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 76 | 197 | 去标签 + 还原实体 + 压空白（答复正文可能含 HTML）。 |
| `existing_ids` 函数 | 84 | 100 | — |
| `_post_json` 函数 | 98 | 3 | — |
| `harvest` 函数 | 107 | 501 | 翻列表 + 逐条取明细，返回统一记录。 |

### `tools/gov-qa/adapters/gd_jgsw.py`（1 个符号）

> 适配器：**广东省机关事务管理局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_jiangmen.py`（1 个符号）

> 适配器：**江门市人民政府·网民留言及答复**（静态 `content/post_<id>.html` 列表）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 按统一记录格式返回江门「网民留言及答复」全文。 |

### `tools/gov-qa/adapters/gd_jieyang.py`（1 个符号）

> 适配器：**揭阳市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_jt.py`（1 个符号）

> 适配器：**广东省交通运输厅**（hdjlpt 同款平台）。年窗 40 条（2026-10-07 实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 19 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_lyj.py`（1 个符号）

> 适配器：**广东省林业局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_maoming.py`（1 个符号）

> 适配器：**茂名市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_mpa.py`（1 个符号）

> 适配器：**广东省药品监督管理局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_nr.py`（1 个符号）

> 适配器：**广东省自然资源厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_shanwei.py`（1 个符号）

> 适配器：**汕尾市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_shenzhen.py`（1 个符号）

> 适配器：**深圳市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_smzt.py`（1 个符号）

> 适配器：**广东省民政厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_stats.py`（1 个符号）

> 适配器：**广东省统计局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_sthj.py`（1 个符号）

> 适配器：**广东省生态环境厅**「互动交流平台」（hdjlpt）留言选登。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_szyyj.py`（1 个符号）

> 适配器：**广东省中医药局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_tyj.py`（1 个符号）

> 适配器：**广东省体育局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_whly.py`（1 个符号）

> 适配器：**广东省文化和旅游厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_wsjkw.py`（1 个符号）

> 适配器：**广东省卫生健康委员会**（hdjlpt 同款平台）。年窗 89 条（2026-10-07 实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 19 | 501 | 按统一记录格式返回该委留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_yangjiang.py`（1 个符号）

> 适配器：**阳江市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_yjgl.py`（1 个符号）

> 适配器：**广东省应急管理厅**「互动交流平台」（hdjlpt）留言选登。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 24 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_yunfu.py`（1 个符号）

> 适配器：**云浮市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_zfcxjst.py`（1 个符号）

> 适配器：**广东省住房和城乡建设厅**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_zfsg.py`（1 个符号）

> 适配器：**广东省政务服务和数据管理局**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 23 | 501 | 按统一记录格式返回该单位留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_zhanjiang.py`（1 个符号）

> 适配器：**湛江市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gd_zhaoqing.py`（1 个符号）

> 适配器：**肇庆市人民政府·政民互动**（广东 hdjlpt 同款平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该市留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/gs_baiyin.py`（1 个符号）

> 适配器：**白银市·政民互动（jpaas-jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 31 | 501 | 翻页取白银政民互动已答复留言（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/gs_dingxi.py`（1 个符号）

> 适配器：**定西市·政民互动（万户 hanweb jact 平台，多 sysid）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 46 | 501 | 遍历定西两个 sysid，取已答复留言（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/gs_linxia.py`（1 个符号）

> 适配器：**临夏回族自治州·政民互动（书记选登 / 州长选登，jpaas-jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 42 | 501 | 取临夏书记/州长选登的已答复留言（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/gs_longnan.py`（2 个符号）

> 适配器：**陇南市·市长信箱（龙讯 CMS，label 8888）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 45 | 197 | 去标签 + 压空白（答复正文是 HTML 片段）。 |
| `harvest` 函数 | 52 | 501 | 翻页取陇南市长信箱已答复留言（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/gs_tianshui.py`（5 个符号）

> 适配器：**天水市·政民互动（书记留言板 / 市长留言板，万户 leadermail）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 61 | 197 | 去标签 + 压空白（正文是 HTML 片段）。 |
| `_norm` 函数 | 68 | 21 | — |
| `parse_detail` 函数 | 72 | 18 | 解析详情页 → {规范标签: 值}（label/value 相邻两个 <td>。 |
| `existing_ids` 函数 | 87 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（供增量续采，避免重取明细）。 |
| `harvest` 函数 | 110 | 501 | 遍历聚合列表 PAGENUM，逐条取详情，返回已答复留言（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/gs_zhangye.py`（1 个符号）

> 适配器：**张掖市·政民互动（IGI 平台，多 siteId）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 40 | 501 | 遍历张掖 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/gx_igi.py`（1 个符号）

> 适配器：**广西壮族自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 57 | 501 | 遍历广西各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/gx_mailbox.py`（1 个符号）

> 适配器：**广西壮族自治区·自治区人民政府信箱（留言选登）**——IGI 平台（与宁夏/山西/贵州/吉林同族）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 40 | 501 | 按 IGI 基座采广西自治区人民政府信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_atcm.py`（1 个符号）

> 适配器：**贵州省中医药管理局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_czt.py`（1 个符号）

> 适配器：**贵州省财政厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_dsj.py`（1 个符号）

> 适配器：**贵州省大数据发展管理局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_fgw.py`（1 个符号）

> 适配器：**贵州省发展和改革委员会·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_gxt.py`（1 个符号）

> 适配器：**贵州省工业和信息化厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_gzw.py`（1 个符号）

> 适配器：**贵州省国有资产监督管理委员会·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_igi.py`（2 个符号）

> 适配器：**贵州省·人民政府门户·政民互动（IGI 平台，全量 siteId）**——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 57 | 47 | 剥离**恒定**地域（= 站点默认值），保留逐信变化的地域。 |
| `harvest` 函数 | 83 | 501 | 遍历贵州门户 IGI 各 siteId（33 个）取已答复信件。 |

### `tools/gov-qa/adapters/gz_invest.py`（1 个符号）

> 适配器：**贵州省投资促进局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_jdglj.py`（1 个符号）

> 适配器：**贵州省戒毒管理局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_jkj.py`（1 个符号）

> 适配器：**贵州省疾病预防控制局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_jyglj.py`（1 个符号）

> 适配器：**贵州省监狱管理局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_jyt.py`（1 个符号）

> 适配器：**贵州省教育厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_kjt.py`（1 个符号）

> 适配器：**贵州省科学技术厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_lshwzcb.py`（1 个符号）

> 适配器：**贵州省粮食和物资储备局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_lyj.py`（1 个符号）

> 适配器：**贵州省林业局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_mwr.py`（1 个符号）

> 适配器：**贵州省水利厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_mzt.py`（1 个符号）

> 适配器：**贵州省民政厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_mzw.py`（1 个符号）

> 适配器：**贵州省民族宗教事务委员会·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_nynct.py`（1 个符号）

> 适配器：**贵州省农业农村厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_portal.py`（1 个符号）

> 适配器：**贵州省·人民政府门户·政民互动（IGI 平台，多 site）**——IGI 中间件。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 43 | 501 | 遍历贵州省门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/gz_rst.py`（1 个符号）

> 适配器：**贵州省人力资源社会保障厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_sft.py`（1 个符号）

> 适配器：**贵州省司法厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_sjt.py`（1 个符号）

> 适配器：**贵州省审计厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_sthjt.py`（1 个符号）

> 适配器：**贵州省生态环境厅 · 厅长信箱（信件公示）**——IGI 平台，带省/市/区三级归属。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 公共基座采贵州厅长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_stjj.py`（1 个符号）

> 适配器：**贵州省统计局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_stymj.py`（1 个符号）

> 适配器：**贵州省生态移民局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_swt.py`（1 个符号）

> 适配器：**贵州省商务厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_tyj.py`（1 个符号）

> 适配器：**贵州省体育局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_tyjrswt.py`（1 个符号）

> 适配器：**贵州省退役军人事务厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_whhly.py`（1 个符号）

> 适配器：**贵州省文化和旅游厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_wjw.py`（1 个符号）

> 适配器：**贵州省卫生健康委员会 · 厅长信箱**——IGI 平台（贵州省内第二个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 31 | 501 | 按 IGI 基座采贵州省卫健委厅长信箱的已答复信件。 |

### `tools/gov-qa/adapters/gz_wsb.py`（1 个符号）

> 适配器：**贵州省人民政府外事办公室·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_wsg.py`（1 个符号）

> 适配器：**贵州省文史研究馆·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_yjgl.py`（1 个符号）

> 适配器：**贵州省应急管理厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_ylbzj.py`（1 个符号）

> 适配器：**贵州省医疗保障局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_zfcx.py`（1 个符号）

> 适配器：**贵州省住房城乡建设厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/gz_zrzy.py`（1 个符号）

> 适配器：**贵州省自然资源厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/hb_hdjl.py`（1 个符号）

> 适配器：**湖北省人民政府·政民互动（IGI 平台，多 site）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 53 | 501 | 遍历湖北省门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/hb_rst.py`（3 个符号）

> 适配器：**湖北省人力资源和社会保障厅·政务咨询留言（留言公开）**——TRS 静态列。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 39 | 172 | — |
| `_parse_detail` 函数 | 45 | 60 | 从明细页取 问题 / 答复 / 承办单位 / 咨询时间 / 答复时间。 |
| `harvest` 函数 | 71 | 501 | — |

### `tools/gov-qa/adapters/hb_rst_igi.py`（1 个符号）

> 适配器：**湖北省人力资源和社会保障厅·互动交流（IGI 平台，多 site）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 67 | 501 | 遍历湖北省人社厅 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/hb_wjw.py`（1 个符号）

> 适配器：**湖北省卫生健康委员会·互动交流（IGI 平台，多 site）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 67 | 501 | 遍历湖北省卫健委 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/hb_wuhan.py`（1 个符号）

> 适配器：**武汉市人民政府·市长信箱/12345（IGI 平台，多 site）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 44 | 501 | 遍历武汉市门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/heb_czt.py`（5 个符号）

> 适配器：**河北省财政厅 · 互动交流 · 群众信箱**（静态型，小体量）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 48 | 144 | — |
| `_norm_date` 函数 | 52 | 2 | `2026年09月29日` → `2026-09-29`。 |
| `_block_items` 函数 | 60 | 2 | 只在『留言回复列表』标题后的第一个 <ul> 里取 (href, title, date)。 |
| `_parse_detail` 函数 | 75 | 60 | — |
| `harvest` 函数 | 95 | 501 | 翻完所有列表页，逐条取明细（按 URL 去重）。 |

### `tools/gov-qa/adapters/heb_szj.py`（4 个符号）

> 适配器：**河北省数据和政务服务局 · 互动交流 · 留言公开**（EWB 平台接口型）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 61 | 172 | 去标签 + 压空白（答复是 HTML 片段）。 |
| `_post` 函数 | 68 | 13 | EWB 约定：POST + form 单字段 params=<JSON 串>（可带 Authorization）。 |
| `_get_token` 函数 | 74 | 2 | — |
| `harvest` 函数 | 81 | 501 | 取匿名 token → 翻页列表 → 逐条取明细拿答复全文。 |

### `tools/gov-qa/adapters/hi_zcwd.py`（3 个符号）

> 适配器：**海南省人民政府 · 政策问答**（接口型）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 51 | 144 | — |
| `_parse_detail` 函数 | 55 | 60 | — |
| `harvest` 函数 | 76 | 501 | 按 curPage 翻页取政策问答列表，再逐条抓明细（按 URL 去重）。 |

### `tools/gov-qa/adapters/hlj_hdjl.py`（5 个符号）

> 适配器：**黑龙江省人民政府门户 · 政民互动（留言选登）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 97 | 144 | — |
| `_parse_detail` 函数 | 101 | 60 | — |
| `_meta_map` 函数 | 121 | 3 | 把 `domainMetaList\[0\].resultList` 摊平成 {中文名: 值}。 |
| `_clean_meta` 函数 | 140 | 12 | `value` 里偶有字符串 `"null"`（实测「评价」字段）⇒ 归一成 None。 |
| `harvest` 函数 | 148 | 501 | 翻列表接口直接取全量（**不再逐条抓明细页**）。 |

### `tools/gov-qa/adapters/hn_hdjl.py`（4 个符号）

> 适配器：**河南省人民政府门户 · 互动交流（网上咨询）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 52 | 144 | — |
| `_cell` 函数 | 56 | 46 | — |
| `_parse_detail` 函数 | 61 | 60 | — |
| `harvest` 函数 | 76 | 501 | 逐页取列表（首页静态地址，其余 index_{n}.html），再逐条取明细（按明细 url 去重）。 |

### `tools/gov-qa/adapters/hunan_agri.py`（1 个符号）

> 适配器：**湖南省农业农村厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_amr.py`（1 个符号）

> 适配器：**湖南省市场监督管理局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_czt.py`（1 个符号）

> 适配器：**湖南省财政厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_fgw.py`（1 个符号）

> 适配器：**湖南省发展和改革委员会**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_gat.py`（1 个符号）

> 适配器：**湖南省公安厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_gxt.py`（1 个符号）

> 适配器：**湖南省工业和信息化厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_gzw.py`（1 个符号）

> 适配器：**湖南省人民政府国有资产监督管理委员会**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_jgswj.py`（1 个符号）

> 适配器：**湖南省机关事务管理局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_jtt.py`（1 个符号）

> 适配器：**湖南省交通运输厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_jyt.py`（1 个符号）

> 适配器：**湖南省教育厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_kjt.py`（1 个符号）

> 适配器：**湖南省科学技术厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_lshwzcbj.py`（1 个符号）

> 适配器：**湖南省粮食和物资储备局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_lyj.py`（1 个符号）

> 适配器：**湖南省林业局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_mpa.py`（1 个符号）

> 适配器：**湖南省药品监督管理局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_mzt.py`（1 个符号）

> 适配器：**湖南省民政厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_mzw.py`（1 个符号）

> 适配器：**湖南省民族宗教事务委员会**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_rst.py`（1 个符号）

> 适配器：**湖南省人力资源和社会保障厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_sft.py`（1 个符号）

> 适配器：**湖南省司法厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_sjt.py`（1 个符号）

> 适配器：**湖南省审计厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_slt.py`（1 个符号）

> 适配器：**湖南省水利厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_sthjt.py`（1 个符号）

> 适配器：**湖南省生态环境厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 27 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_swt.py`（1 个符号）

> 适配器：**湖南省商务厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_tjj.py`（1 个符号）

> 适配器：**湖南省统计局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_tyj.py`（1 个符号）

> 适配器：**湖南省体育局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_tyjrswt.py`（1 个符号）

> 适配器：**湖南省退役军人事务厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_whhlyt.py`（1 个符号）

> 适配器：**湖南省文化和旅游厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_wjw.py`（1 个符号）

> 适配器：**湖南省卫生健康委员会**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_xfj.py`（1 个符号）

> 适配器：**湖南省信访局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_ybj.py`（1 个符号）

> 适配器：**湖南省医疗保障局**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_yjt.py`（1 个符号）

> 适配器：**湖南省应急管理厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_zjt.py`（1 个符号）

> 适配器：**湖南省住房和城乡建设厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/hunan_zrzyt.py`（1 个符号）

> 适配器：**湖南省自然资源厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅问答（详见 _hunan_hd_common）。 |

### `tools/gov-qa/adapters/jingzhou_igi.py`（2 个符号）

> 适配器：**荆州市·政民互动信箱（IGI 平台，29 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 47 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 69 | 501 | 遍历荆州各 siteId 取已答复信件。 |

### `tools/gov-qa/adapters/jiujiang_igi.py`（1 个符号）

> 适配器：**九江市·政民互动信箱（IGI 平台，siteId=72）**——2026-10-09 第 10 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 49 | 501 | 取九江市已答复信件（`limit` 为本轮新增上限）。 |

### `tools/gov-qa/adapters/jl_czt.py`（1 个符号）

> 适配器：**吉林省财政厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_fgw.py`（1 个符号）

> 适配器：**吉林省发展和改革委员会·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_gat.py`（1 个符号）

> 适配器：**吉林省公安厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_gbdsj.py`（1 个符号）

> 适配器：**吉林省广播电视局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_gfdy.py`（1 个符号）

> 适配器：**吉林省国防动员办公室·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_ggzy.py`（1 个符号）

> 适配器：**吉林省公共资源交易中心·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_gxj.py`（1 个符号）

> 适配器：**吉林省工业和信息化厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_gzw.py`（1 个符号）

> 适配器：**吉林省国有资产监督管理委员会·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_hrss.py`（1 个符号）

> 适配器：**吉林省人力资源社会保障厅·厅长信箱（问政列表）**——IGI 平台，带省/市/区三级归属。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 34 | 501 | 按 IGI 公共基座采吉林人社厅长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_jgsw.py`（1 个符号）

> 适配器：**吉林省机关事务管理局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_jt.py`（1 个符号）

> 适配器：**吉林省交通运输厅·厅长信箱（问政列表）**——IGI 平台，带省/市/区三级归属。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 公共基座采吉林交通运输厅长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_jyj.py`（1 个符号）

> 适配器：**吉林省监狱管理局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_kjt.py`（1 个符号）

> 适配器：**吉林省科学技术厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_lsj.py`（1 个符号）

> 适配器：**吉林省粮食和物资储备局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_lyj.py`（1 个符号）

> 适配器：**吉林省林业和草原局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_mzt.py`（1 个符号）

> 适配器：**吉林省民政厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_mzw.py`（1 个符号）

> 适配器：**吉林省民族事务委员会·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_nyj.py`（1 个符号）

> 适配器：**吉林省能源局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_nynct.py`（1 个符号）

> 适配器：**吉林省农业农村厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_scjd.py`（1 个符号）

> 适配器：**吉林省市场监督管理厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_sft.py`（1 个符号）

> 适配器：**吉林省司法厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_sjt.py`（1 个符号）

> 适配器：**吉林省审计厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_slt.py`（1 个符号）

> 适配器：**吉林省水利厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_sthjt.py`（3 个符号）

> 适配器：**吉林省生态环境厅 · 厅长信箱（留言选登）**——省/市/区**三级归属**的问答源。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 51 | 172 | — |
| `_ts` 函数 | 57 | 22 | — |
| `harvest` 函数 | 67 | 501 | 翻页取列表（只要已答复的），再逐条取明细拿答复正文。 |

### `tools/gov-qa/adapters/jl_swt.py`（1 个符号）

> 适配器：**吉林省商务厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_tjj.py`（1 个符号）

> 适配器：**吉林省统计局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_tyj.py`（1 个符号）

> 适配器：**吉林省体育局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_tyjr.py`（1 个符号）

> 适配器：**吉林省退役军人事务厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_wjw.py`（1 个符号）

> 适配器：**吉林省卫生健康委员会 · 厅长信箱**——IGI 平台（同一省内的另一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 34 | 501 | 按 IGI 基座采吉林省卫健委厅长信箱的已答复信件。 |

### `tools/gov-qa/adapters/jl_wlt.py`（1 个符号）

> 适配器：**吉林省文化和旅游厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_wsb.py`（1 个符号）

> 适配器：**吉林省外事办公室·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_xmy.py`（1 个符号）

> 适配器：**吉林省畜牧业管理局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_ybj.py`（1 个符号）

> 适配器：**吉林省医疗保障局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_yjt.py`（1 个符号）

> 适配器：**吉林省应急管理厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_ypj.py`（1 个符号）

> 适配器：**吉林省药品监督管理局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_zfcx.py`（1 个符号）

> 适配器：**吉林省住房和城乡建设厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_zrzy.py`（1 个符号）

> 适配器：**吉林省自然资源厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/jl_zyy.py`（1 个符号）

> 适配器：**吉林省中医药管理局·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/js_credit.py`（1 个符号）

> 适配器：**江苏省·信用(credit)咨询建言**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_czt.py`（1 个符号）

> 适配器：**江苏省财政厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_czt2.py`（1 个符号）

> 适配器：**江苏省财政厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_da.py`（1 个符号）

> 适配器：**江苏省药品监督管理局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_da2.py`（1 个符号）

> 适配器：**江苏省药品监督管理局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_doc.py`（1 个符号）

> 适配器：**江苏省商务厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_fzggw.py`（1 个符号）

> 适配器：**江苏省发展和改革委员会**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_gxt.py`（1 个符号）

> 适配器：**江苏省工业和信息化厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_gxt2.py`（1 个符号）

> 适配器：**江苏省工业和信息化厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsdk.py`（1 个符号）

> 适配器：**江苏省地质局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsgd.py`（1 个符号）

> 适配器：**江苏省广播电视局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsip.py`（1 个符号）

> 适配器：**江苏省知识产权局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsip2.py`（1 个符号）

> 适配器：**江苏省知识产权局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsstyj.py`（1 个符号）

> 适配器：**江苏省体育局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jsstyj2.py`（1 个符号）

> 适配器：**江苏省体育局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jssxfj.py`（1 个符号）

> 适配器：**江苏省信访局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jswater.py`（1 个符号）

> 适配器：**江苏省水利厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jtyst.py`（1 个符号）

> 适配器：**江苏省交通运输厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jtyst2.py`（1 个符号）

> 适配器：**江苏省交通运输厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jyt.py`（1 个符号）

> 适配器：**江苏省教育厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_jyt2.py`（1 个符号）

> 适配器：**江苏省教育厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_mzt.py`（1 个符号）

> 适配器：**江苏省民政厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_nanjing.py`（2 个符号）

> 适配器：**南京市·政民互动·政府信箱·案例公开（szxx SPA prod-api/wsxf/algk）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_day` 函数 | 43 | 9 | — |
| `harvest` 函数 | 48 | 501 | 翻页取南京政府信箱案例公开（列表自带问题 + 答复全文）。 |

### `tools/gov-qa/adapters/js_nantong.py`（3 个符号）

> 适配器：**南通市·政民互动·市长信箱（truecms getMessageByCondition）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 45 | 172 | 答复正文是富文本：<br> 换行，其余标签剔除、实体反转义（保留文字逐字不变）。 |
| `_jd` 函数 | 56 | 4 | Jackson Java date 对象 {year,month,date,…} → 'YYYY-MM-DD'。 |
| `harvest` 函数 | 69 | 501 | 翻页取南通市长信箱（列表自带问题 + 答复全文）。 |

### `tools/gov-qa/adapters/js_nynct.py`（1 个符号）

> 适配器：**江苏省农业农村厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_sthjt.py`（1 个符号）

> 适配器：**江苏省生态环境厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_suqian.py`（2 个符号）

> 适配器：**宿迁市·政民互动·留言查询/部门信箱（ajaxlist，列表自带答复）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ts` 函数 | 40 | 22 | — |
| `harvest` 函数 | 48 | 501 | 翻页取宿迁留言（列表自带问题 + 答复全文）。 |

### `tools/gov-qa/adapters/js_suzhou.py`（2 个符号）

> 适配器：**苏州市·政民互动·部门信箱（consultfront bmxxCommonlist）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_dt` 函数 | 43 | 3 | — |
| `harvest` 函数 | 48 | 501 | 翻页取苏州部门信箱（列表自带答复全文）。 |

### `tools/gov-qa/adapters/js_taizhou.py`（1 个符号）

> 适配器：**泰州市·政民互动·留言选登（jpaas-jact）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 38 | 501 | 采泰州市「留言选登」（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/js_tj.py`（1 个符号）

> 适配器：**江苏省统计局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_tj2.py`（1 个符号）

> 适配器：**江苏省统计局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_wuxi.py`（2 个符号）

> 适配器：**无锡市·政民互动·市长信箱/12345 信件查询（mailbox letter/search）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_day` 函数 | 39 | 9 | — |
| `harvest` 函数 | 44 | 501 | 翻页取无锡市长信箱信件（列表自带问题 + 答复全文）。 |

### `tools/gov-qa/adapters/js_xuzhou.py`（3 个符号）

> 适配器：**徐州市·政民互动·来信选登（EWB 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 50 | 172 | — |
| `_post` 函数 | 57 | 13 | — |
| `harvest` 函数 | 62 | 501 | 翻页取徐州来信选登（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/js_yancheng.py`（1 个符号）

> 适配器：**盐城市·政民互动·市长信箱（jact 平台，多 sysid）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 36 | 501 | 遍历盐城 jact 各 sysid，取已答复信件（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/js_yangzhou.py`（1 个符号）

> 适配器：**扬州市·政民互动·信件选登（jpaas-jact）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 32 | 501 | 采扬州市「信件选登」（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/js_ybj.py`（1 个符号）

> 适配器：**江苏省医疗保障局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_ybj2.py`（1 个符号）

> 适配器：**江苏省医疗保障局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 26 | 501 | 按统一记录格式返回该厅留言选登（问题+答复全文）。 |

### `tools/gov-qa/adapters/js_zhenjiang.py`（2 个符号）

> 适配器：**镇江市·政民互动·12345 在线·信件公示**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 38 | 172 | — |
| `harvest` 函数 | 46 | 501 | 翻页取镇江 12345 信件公示（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/jx_gzw_lyxd.py`（5 个符号）

> 适配器：**江西省国资委 · 留言选登**（数融站群 webSiteCode=jxsgzw, channelCode=lyxd）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 58 | 144 | — |
| `_date` 函数 | 63 | 6 | — |
| `_grab` 函数 | 70 | 7 | — |
| `_one` 函数 | 75 | 34 | — |
| `harvest` 函数 | 118 | 501 | — |

### `tools/gov-qa/adapters/jx_zf.py`（3 个符号）

> 适配器：**江西省人民政府 · 数融互动**（我向省长建言 + 政策问答库）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 57 | 144 | — |
| `_one` 函数 | 63 | 34 | — |
| `harvest` 函数 | 132 | 501 | 按栏目翻页取数融互动问答（列表已带全文，无需再抓明细）。 |

### `tools/gov-qa/adapters/jz_zxhf.py`（5 个符号）

> 适配器：**焦作市·咨询回复**（`/zmhd/zxhf/`，政民互动咨询选登）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 60 | 172 | — |
| `_real` 函数 | 72 | 123 | — |
| `_parse_list` 函数 | 77 | 18 | 列表页 → `\[{id, title, url}\]`（去重、保序）。 |
| `_parse_detail` 函数 | 95 | 60 | 详情页 → `{question, answer, asked_at, answered_at, dept}`。 |
| `harvest` 函数 | 131 | 501 | 翻列表（服务端渲染）+ 逐条取详情。 |

### `tools/gov-qa/adapters/kf_hdjl.py`（4 个符号）

> 适配器：**开封市·政民互动·信件公开**（`/uapi/mail/`，河南第 5 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 83 | 172 | — |
| `_real` 函数 | 97 | 123 | — |
| `_dept_of` 函数 | 102 | 14 | `metadataList` 是 JSON 字符串，找 `name == '答复单位'` 的那条。 |
| `harvest` 函数 | 120 | 501 | 翻列表（GET JSON）+ 逐条取详情。 |

### `tools/gov-qa/adapters/ln_8890.py`（8 个符号）

> 适配器：**辽宁省·12345 民心智慧听**（省政务服务网 `lnzwfw.gov.cn/8890`，JeecgBoot 前端 + 公开 JSON 接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 59 | 197 | — |
| `_parts` 函数 | 65 | 2 | — |
| `_int_env` 函数 | 70 | 3 | — |
| `_get_json` 函数 | 77 | 3 | GET + JSON，失败返回 None（绝不抛异常冒泡）。 |
| `_page` 函数 | 91 | 29 | 取一页，返回 (records, total, err)。 |
| `_harvest_kb` 函数 | 100 | 2 | 知识库：列表即含问答，逐页收。 |
| `_harvest_qa` 函数 | 161 | 2 | 咨询投诉：翻列表拿 id，再逐条取答复。 |
| `harvest` 函数 | 249 | 501 | 采「12345 民心智慧听」公开语料：知识库 + 咨询投诉。 |

### `tools/gov-qa/adapters/ln_sthjt.py`（3 个符号）

> 适配器：**辽宁省生态环境厅 · 历史咨询服务**（问答内联在列表页）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 46 | 144 | — |
| `_parse_page` 函数 | 50 | 2 | — |
| `harvest` 函数 | 69 | 501 | 逐页取（首页用静态地址，其余页用 eportal 分页地址），按 标题+问题 去重。 |

### `tools/gov-qa/adapters/mee_gov.py`（2 个符号）

> 适配器：**生态环境部**「常见问题 / 留言选登」（WAS5 检索接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_looks_like_question` 函数 | 52 | 2 | 判断 `answer` 是否其实是问题原文（该接口个别条目的字段装错）。 |
| `harvest` 函数 | 64 | 501 | 按统一格式返回该站问答。 |

### `tools/gov-qa/adapters/mem_gov.py`（2 个符号）

> 适配器：**应急管理部**「互动答复」列表（静态列表页）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 63 | 144 | 去脚本/样式/注释后再去标签 —— 不复用旧版整页兜底（那会把 JS 当答复，已踩坑）。 |
| `harvest` 函数 | 71 | 501 | 按统一格式返回该站问答。 |

### `tools/gov-qa/adapters/nanjing_igi.py`（2 个符号）

> 适配器：**南京市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 8 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 57 | 47 | 剥离**空/恒定**地域（= 门户默认值或缺失）。 |
| `harvest` 函数 | 83 | 501 | 遍历南京各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/nanning_igi.py`（1 个符号）

> 适配器：**南宁市·政民互动信箱（IGI 平台，siteId=8）**——2026-10-09 第 7 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 51 | 501 | 取南宁市已答复信件（`limit` 为本轮新增上限）。 |

### `tools/gov-qa/adapters/nat_cma.py`（4 个符号）

> 适配器：**中国气象局·回应关切（常见问题）**（静态列表 + 明细页，答复在明细里）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 42 | 144 | — |
| `_parse_detail` 函数 | 52 | 60 | — |
| `_list_page` 函数 | 74 | 6 | — |
| `harvest` 函数 | 86 | 501 | 取中国气象局回应关切（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_cnipa.py`（7 个符号）

> 适配器：**国家知识产权局·留言咨询（已答问题）**（jact 平台，多 sysid）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_env_page_from` 函数 | 46 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。 |
| `_env_sysids` 函数 | 54 | 2 | 只采指定 sysid：环境变量 `GOVQA_CNIPA_SYSIDS`（逗号分隔），空则返回 None（=全部）。 |
| `_field_re` 函数 | 99 | 6 | — |
| `_text` 函数 | 110 | 144 | — |
| `_parse_detail` 函数 | 119 | 60 | — |
| `_list_page` 函数 | 134 | 6 | — |
| `harvest` 函数 | 150 | 501 | 遍历各 sysid 的「已答问题」，逐条取明细拿答复原文。 |

### `tools/gov-qa/adapters/nat_forestry.py`（1 个符号）

> 适配器：**国家林业和草原局·互动留言**（JEECMS 站内 JSON 接口，答复内联）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 45 | 501 | 取国家林草局互动留言（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_moa.py`（2 个符号）

> 适配器：**农业农村部·留言回复**（部长信箱·网上信访，站内静态 JSON，答复内联）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 38 | 144 | — |
| `harvest` 函数 | 49 | 501 | 取农业农村部留言回复（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_mohurd.py`（4 个符号）

> 适配器：**住房和城乡建设部·政务咨询（留言选登）**（jpaas 静态构建接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 68 | 144 | — |
| `_parse_items` 函数 | 77 | 8 | 把一页 list HTML 拆成记录。 |
| `_fetch_page` 函数 | 133 | 2 | — |
| `harvest` 函数 | 149 | 501 | 翻页取住建部政务咨询（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_most.py`（3 个符号）

> 适配器：**科学技术部·公众问答**（`app.most.gov.cn/ac_gzcy_app/gzwd`，RuoYi 后台接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_post_list` 函数 | 42 | 13 | — |
| `_row` 函数 | 50 | 112 | — |
| `harvest` 函数 | 79 | 501 | 取科技部公众问答四个分类的问答（答复内联，无需明细）。 |

### `tools/gov-qa/adapters/nat_mot.py`（4 个符号）

> 适配器：**交通运输部·留言咨询**（`qa.mot.gov.cn/mapplys`，自研 JSON 列表 + HTML 明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_env_page_from` 函数 | 40 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。 |
| `_text` 函数 | 86 | 144 | 去脚本/样式/注释后去标签、压空白。 |
| `_parse_detail` 函数 | 96 | 60 | 从明细 HTML 抽 (question, answer, asked_at, answered_at, dept)。 |
| `harvest` 函数 | 130 | 501 | 翻页取列表，逐条取明细拿答复原文，返回统一记录。 |

### `tools/gov-qa/adapters/nat_nea.py`（3 个符号）

> 适配器：**国家能源局·留言选登**（新华「Xhwpage」伪数据源 + 服务端渲染明细页）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 45 | 144 | — |
| `_parse_detail` 函数 | 54 | 60 | — |
| `harvest` 函数 | 100 | 501 | 取国家能源局留言选登（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_nhsa.py`（1 个符号）

> 适配器：**国家医疗保障局·交流公开**（自研 Vue 应用 + JSON 接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 46 | 501 | 取国家医保局交流公开（问题 + 答复原文）。 |

### `tools/gov-qa/adapters/nat_tax.py`（4 个符号）

> 适配器：**国家税务总局·12366 纳税服务平台·网上留言**（自研接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_env_page_from` 函数 | 39 | 12 | 起始页号：环境变量 `GOVQA_PAGE_FROM`（用于把超长源分块采）。 |
| `_text` 函数 | 75 | 144 | — |
| `_parse_detail` 函数 | 84 | 60 | — |
| `harvest` 函数 | 98 | 501 | 翻页取列表，逐条取明细拿答复原文。 |

### `tools/gov-qa/adapters/nmg_igi.py`（2 个符号）

> 适配器：**内蒙古自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 58 | 47 | 剥离**恒定**地域（= 门户/站点默认值）。 |
| `harvest` 函数 | 85 | 501 | 遍历内蒙古各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/nmg_xinxiang.py`（2 个符号）

> 适配器：**内蒙古自治区·政民互动·反馈回应**（`xinxiang` 自建接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ts` 函数 | 43 | 22 | ISO 时间（`2026-09-23T09:52:21.000+08:00`）→ `2026-09-23 09:52:21`。 |
| `harvest` 函数 | 51 | 501 | 翻页取反馈回应列表，逐条取明细拿问题/答复正文，返回统一记录。 |

### `tools/gov-qa/adapters/nx_igi.py`（1 个符号）

> 适配器：**宁夏回族自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 54 | 501 | 遍历宁夏各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/nx_zxxx.py`（1 个符号）

> 适配器：**宁夏回族自治区·主席信箱**——IGI 平台（与贵州/吉林同族）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 38 | 501 | 按 IGI 基座采宁夏主席信箱的已答复信件（含答复正文与三级归属）。 |

### `tools/gov-qa/adapters/people_liuyan.py`（1 个符号）

> 适配器：**人民网「领导留言板」· 部委版块**（媒体平台来源，非政府官网）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 33 | 501 | 按统一记录格式返回部委版块带官方答复的问答（详见 _liuyan_common）。 |

### `tools/gov-qa/adapters/people_liuyan_df.py`（1 个符号）

> 适配器：**人民网「领导留言板」· 地方版块**（省/市/区县，全国覆盖）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 38 | 501 | 按统一记录格式返回地方版块带官方答复的问答（详见 _liuyan_common）。 |

### `tools/gov-qa/adapters/people_liuyan_fid.py`（2 个符号）

> 适配器：**人民网领导留言板 · 定向版块**（按 fid 深采某省/某市/某领导的留言）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_fids` 函数 | 44 | 2 | — |
| `harvest` 函数 | 65 | 501 | 按映射表**轮转**采若干版块（每个版块采满已办理且有官方答复的留言）。 |

### `tools/gov-qa/adapters/people_liuyan_prov.py`（2 个符号）

> 适配器：**人民网领导留言板 · 按省定向**（全国 31 个省级单位，逐个采省委书记/省长版块）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_provinces` 函数 | 40 | 2 | — |
| `harvest` 函数 | 61 | 501 | 逐省采（每省两个版块：省委书记 / 省长），配额均分、带版块游标与省份轮转。 |

### `tools/gov-qa/adapters/qh_wsxf.py`（4 个符号）

> 适配器：**青海省·互动交流·群众诉求回应**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 60 | 144 | — |
| `_page_url` 函数 | 66 | 4 | — |
| `_parse_detail` 函数 | 75 | 60 | — |
| `harvest` 函数 | 94 | 501 | 翻完全部静态分页，逐条取明细（按明细 URL 去重）。 |

### `tools/gov-qa/adapters/rd_common.py`（3 个符号）

> 适配器：**地方人大·法规草案征求意见**（M4 人大系统，2026-10-10 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_plain` 函数 | 116 | 4 | — |
| `_items` 函数 | 126 | 13 | — |
| `harvest_rd` 函数 | 149 | 31 | 抓某省人大的法规草案征求意见（标题 + 正文）。 |

### `tools/gov-qa/adapters/rd_gd.py`（1 个符号）

> 适配器：**广东省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_hb.py`（1 个符号）

> 适配器：**河北省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_hn.py`（1 个符号）

> 适配器：**河南省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_jl.py`（1 个符号）

> 适配器：**吉林省人大·法规草案意见征集**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_js.py`（1 个符号）

> 适配器：**江苏省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_ln.py`（1 个符号）

> 适配器：**辽宁省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_npc.py`（1 个符号）

> 适配器：**全国人大·法律草案征求意见**（人大系统·法律草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_sd.py`（1 个符号）

> 适配器：**山东省人大·法规草案征求意见**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/rd_tj.py`（1 个符号）

> 适配器：**天津市人大·立法公开**（人大系统·法规草案征求意见）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 22 | 501 | — |

### `tools/gov-qa/adapters/sc_aba.py`（2 个符号）

> 适配器：**阿坝州·互动交流·领导信箱（通信平台 /communication/api-mailbox）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 46 | 172 | — |
| `harvest` 函数 | 56 | 501 | 翻页取阿坝领导信箱。 |

### `tools/gov-qa/adapters/sc_aba_zwfw.py`（1 个符号）

> 适配器：**阿坝藏族羌族自治州·政民互动（四川政务服务网平台，areaCode=513200000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_bazhong.py`（3 个符号）

> 适配器：**巴中市·政民互动·书记/市长信箱（服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 53 | 172 | — |
| `_decode` 函数 | 64 | 36 | 响应头无 charset，统一按 utf-8 解码（见站点事实）。 |
| `harvest` 函数 | 72 | 501 | 遍历 市长/书记 两栏翻页。 |

### `tools/gov-qa/adapters/sc_bazhong_zwfw.py`（1 个符号）

> 适配器：**巴中市·政民互动（四川政务服务网平台，areaCode=511900000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_chengdu.py`（1 个符号）

> 适配器：**成都市·政民互动（四川政务服务网平台，绕过瑞数 WAF）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_dazhou.py`（4 个符号）

> 适配器：**达州市·政民互动·书记市长信箱（市长信箱 JSON API，ThinkPHP）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 43 | 172 | — |
| `_ts` 函数 | 49 | 22 | unix 秒 → 'YYYY-MM-DD HH:MM:SS'。 |
| `_dept` 函数 | 61 | 13 | — |
| `harvest` 函数 | 67 | 501 | 翻页取列表（JSON）→ 逐条取详情（JSON）拼答复。 |

### `tools/gov-qa/adapters/sc_dazhou_zwfw.py`（1 个符号）

> 适配器：**达州市·政民互动（四川政务服务网平台，areaCode=511700000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_deyang.py`（3 个符号）

> 适配器：**德阳市·互动交流·书记/市长信箱（appeal 模块，服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_td` 函数 | 44 | 16 | — |
| `_fetch_detail` 函数 | 56 | 2 | — |
| `harvest` 函数 | 67 | 501 | 遍历 市长/书记 两个信箱，逐页取 id → 逐条取详情解析答复。 |

### `tools/gov-qa/adapters/sc_deyang_zwfw.py`（1 个符号）

> 适配器：**德阳市·政民互动（四川政务服务网平台，areaCode=510600000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_ganzi.py`（2 个符号）

> 适配器：**甘孜州·政民互动·12345 信件公开（interact-service）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 42 | 172 | — |
| `harvest` 函数 | 52 | 501 | 翻页取甘孜 12345 信件公开。 |

### `tools/gov-qa/adapters/sc_ganzi_zwfw.py`（1 个符号）

> 适配器：**甘孜藏族自治州·政民互动（四川政务服务网平台，areaCode=513300000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_guangan.py`（3 个符号）

> 适配器：**广安市·互动交流·书记市长信箱（数融 /api/mail）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 48 | 172 | — |
| `_dept` 函数 | 58 | 13 | — |
| `harvest` 函数 | 68 | 501 | 翻页取广安书记市长信箱。 |

### `tools/gov-qa/adapters/sc_guangan_zwfw.py`（1 个符号）

> 适配器：**广安市·政民互动（四川政务服务网平台，areaCode=511600000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_guangyuan.py`（4 个符号）

> 适配器：**广元市·市长信箱·信件公开（Spring Boot + layui table JSON）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 54 | 172 | — |
| `_decode` 函数 | 65 | 36 | — |
| `_token` 函数 | 72 | 7 | 取 CSRF token（内嵌在 /ldxx/szxx/s/public 页面。 |
| `harvest` 函数 | 83 | 501 | 翻页取列表（layui POST）→ 逐条详情（服务端渲染 HTML）解析问答。 |

### `tools/gov-qa/adapters/sc_guangyuan_zwfw.py`（1 个符号）

> 适配器：**广元市·政民互动（四川政务服务网平台，areaCode=510800000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_leshan.py`（4 个符号）

> 适配器：**乐山市·政民互动·信件选登（服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 44 | 172 | — |
| `_cell` 函数 | 55 | 46 | — |
| `_decode` 函数 | 60 | 36 | — |
| `harvest` 函数 | 67 | 501 | 翻页取乐山信件选登。 |

### `tools/gov-qa/adapters/sc_leshan_zwfw.py`（1 个符号）

> 适配器：**乐山市·政民互动（四川政务服务网平台，areaCode=511100000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_liangshan.py`（3 个符号）

> 适配器：**凉山州·12345 政务服务便民热线·信件选登（慧兰 eportal portlet）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 46 | 172 | — |
| `_dept` 函数 | 57 | 13 | — |
| `harvest` 函数 | 71 | 501 | 翻页取凉山 12345 信件选登。 |

### `tools/gov-qa/adapters/sc_liangshan_zwfw.py`（1 个符号）

> 适配器：**凉山彝族自治州·政民互动（四川政务服务网平台，areaCode=513400000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_luzhou.py`（2 个符号）

> 适配器：**泸州市·互动交流·书记市长信箱（信件公开，服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_td` 函数 | 41 | 16 | 取 `<td class="tdName">label</td><td ...>值</td>` 的值（去标签）。 |
| `harvest` 函数 | 55 | 501 | 翻列表页拿 id → 逐条取详情解析答复。 |

### `tools/gov-qa/adapters/sc_luzhou_zwfw.py`（1 个符号）

> 适配器：**泸州市·政民互动（四川政务服务网平台，areaCode=510500000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_meishan.py`（4 个符号）

> 适配器：**眉山市·政民互动·来信选登（服务端渲染 HTML / WCM 西部数通站群）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_field` 函数 | 68 | 10 | — |
| `_clean` 函数 | 73 | 172 | — |
| `_decode` 函数 | 84 | 36 | — |
| `harvest` 函数 | 91 | 501 | 遍历 来信选登 列表翻页 → 逐条详情解析问答。 |

### `tools/gov-qa/adapters/sc_meishan_zwfw.py`（1 个符号）

> 适配器：**眉山市·政民互动（四川政务服务网平台，areaCode=511400000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_mianyang.py`（4 个符号）

> 适配器：**绵阳市·互动交流·书记市长信箱（通信平台 /communication/api-mailbox）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_enc` 函数 | 54 | 4 | — |
| `_sign` 函数 | 61 | 6 | 复刻 hd_common.js getKeyVal：key = 按名排序 name+JSON.stringify(value)，sign=AES(timestamp+key)。 |
| `_clean` 函数 | 74 | 172 | — |
| `harvest` 函数 | 84 | 501 | 翻页取绵阳书记市长信箱。 |

### `tools/gov-qa/adapters/sc_mianyang_zwfw.py`（1 个符号）

> 适配器：**绵阳市·政民互动（四川政务服务网平台，areaCode=510700000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_nanchong.py`（1 个符号）

> 适配器：**南充市·政民互动·市长信箱（IGI 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 38 | 501 | 遍历南充 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/sc_nanchong_zwfw.py`（1 个符号）

> 适配器：**南充市·政民互动（四川政务服务网平台，areaCode=511300000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_neijiang.py`（4 个符号）

> 适配器：**内江市·互动交流·书记市长网上政务信箱（通信平台 /communication/api-mailbox）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_enc` 函数 | 53 | 4 | — |
| `_sign` 函数 | 60 | 6 | 复刻 getKeyVal：key = 按名排序 name+JSON.stringify(value)，sign=AES(timestamp+key)。 |
| `_clean` 函数 | 73 | 172 | — |
| `harvest` 函数 | 83 | 501 | 翻页取内江书记市长信箱。 |

### `tools/gov-qa/adapters/sc_neijiang_zwfw.py`（1 个符号）

> 适配器：**内江市·政民互动（四川政务服务网平台，areaCode=511000000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_panzhihua.py`（2 个符号）

> 适配器：**攀枝花市·12345 政务服务便民热线（webapp api-letter 接口）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_day` 函数 | 40 | 9 | — |
| `harvest` 函数 | 45 | 501 | 翻页取攀枝花 12345 便民热线工单（列表自带问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sc_panzhihua_zwfw.py`（1 个符号）

> 适配器：**攀枝花市·政民互动（四川政务服务网平台，areaCode=510400000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_sthjt.py`（3 个符号）

> 适配器：**四川省生态环境厅 · 政务服务互动交流知识库**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 50 | 144 | — |
| `_parse_detail` 函数 | 54 | 60 | — |
| `harvest` 函数 | 91 | 501 | 抓四川厅互动知识库的问答（列表去重后逐条取明细）。 |

### `tools/gov-qa/adapters/sc_suining.py`（3 个符号）

> 适配器：**遂宁市·互动交流·市长信箱（来信选登，服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 44 | 172 | — |
| `_cell` 函数 | 54 | 46 | — |
| `harvest` 函数 | 59 | 501 | 翻页取遂宁来信选登。 |

### `tools/gov-qa/adapters/sc_suining_zwfw.py`（1 个符号）

> 适配器：**遂宁市·政民互动（四川政务服务网平台，areaCode=510900000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_yaan.py`（5 个符号）

> 适配器：**雅安市·政民互动·党政领导信箱（服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 76 | 172 | — |
| `_decode` 函数 | 87 | 36 | 响应头无 charset，统一按 utf-8 解码（见站点事实）。 |
| `_cell` 函数 | 95 | 46 | — |
| `_uuids` 函数 | 100 | 2 | — |
| `harvest` 函数 | 116 | 501 | 遍历全部部门信箱 → 翻页取列表 → 逐条详情解析问答。 |

### `tools/gov-qa/adapters/sc_yaan_zwfw.py`（1 个符号）

> 适配器：**雅安市·政民互动（四川政务服务网平台，areaCode=511800000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_yibin.py`（3 个符号）

> 适配器：**宜宾市·12345 市民服务平台·办件摘编（服务端渲染 HTML）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 45 | 172 | — |
| `_cell` 函数 | 56 | 46 | — |
| `harvest` 函数 | 61 | 501 | 翻页取宜宾 12345 办件摘编。 |

### `tools/gov-qa/adapters/sc_yibin_zwfw.py`（1 个符号）

> 适配器：**宜宾市·政民互动（四川政务服务网平台，areaCode=511500000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_zigong.py`（3 个符号）

> 适配器：**自贡市·互动交流·市长信箱/来信选登（数融 /api/mail）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 51 | 172 | — |
| `_dept` 函数 | 61 | 13 | — |
| `harvest` 函数 | 70 | 501 | 翻页取自贡来信选登。 |

### `tools/gov-qa/adapters/sc_zigong_zwfw.py`（1 个符号）

> 适配器：**自贡市·政民互动（四川政务服务网平台，areaCode=510300000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sc_ziyang.py`（3 个符号）

> 适配器：**资阳市·互动交流·书记市长信箱（数融 /api/mail）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 51 | 172 | — |
| `_dept` 函数 | 61 | 13 | — |
| `harvest` 函数 | 72 | 501 | 翻页取资阳书记市长信箱。 |

### `tools/gov-qa/adapters/sc_ziyang_zwfw.py`（1 个符号）

> 适配器：**资阳市·政民互动（四川政务服务网平台，areaCode=512000000000）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | — |

### `tools/gov-qa/adapters/sd_12345.py`（2 个符号）

> 适配器：**山东省·12345 政务服务便民热线·典型留言**（JSON 接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_one` 函数 | 41 | 34 | — |
| `harvest` 函数 | 78 | 501 | 翻页取「典型留言」列表，逐条取明细拿答复正文。 |

### `tools/gov-qa/adapters/sd_binzhou.py`（1 个符号）

> 适配器：**滨州市·政民互动·领导信箱（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 28 | 501 | 采滨州市 jact 领导信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_dezhou.py`（4 个符号）

> 适配器：**德州市·政民互动·回应关切（服务端渲染列表 + 明细页）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 48 | 197 | — |
| `_label` 函数 | 54 | 10 | — |
| `parse_detail` 函数 | 58 | 18 | — |
| `harvest` 函数 | 67 | 501 | 采德州回应关切（17 页列表 + 逐条明细）。 |

### `tools/gov-qa/adapters/sd_dongying.py`（1 个符号）

> 适配器：**东营市·政民互动·网上民生（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 30 | 501 | 采东营市 jact 网上民生（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_heze.py`（2 个符号）

> 适配器：**菏泽市·政民互动·咨询选登（山东一体化 CMS，hdjl-service 接口）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 52 | 197 | — |
| `harvest` 函数 | 58 | 501 | 采菏泽咨询选登（列表 + 逐条 find 取答复）。 |

### `tools/gov-qa/adapters/sd_jinan.py`（1 个符号）

> 适配器：**济南市·互动交流·回应关切（jpaas-jact 网关，JSON 接口）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 采济南「回应关切」（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_jining.py`（1 个符号）

> 适配器：**济宁市·政民互动·我要写信（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 27 | 501 | 采济宁市 jact 信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_liaocheng.py`（2 个符号）

> 适配器：**聊城市·政民互动·网上信箱（api.min.js 接口，列表自带答复）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 40 | 197 | — |
| `harvest` 函数 | 46 | 501 | 采聊城网上信箱（列表自带答复，逐页翻）。 |

### `tools/gov-qa/adapters/sd_linyi.py`（4 个符号）

> 适配器：**临沂市·政民互动·网上信箱（服务端渲染 JSP）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 54 | 197 | 去标签 + 还原实体 + 压空白。 |
| `_label` 函数 | 61 | 10 | — |
| `parse_detail` 函数 | 65 | 18 | 把 `titlestyle/contentstyle` 相邻 `<td>` 解析成 标签→值 字典。 |
| `harvest` 函数 | 75 | 501 | 采临沂网上信箱（服务端渲染，含答复原文）。 |

### `tools/gov-qa/adapters/sd_rizhao.py`（1 个符号）

> 适配器：**日照市·政民互动·市长信箱（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 27 | 501 | 采日照市 jact 市长信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_weihai.py`（1 个符号）

> 适配器：**威海市·政民互动·市长信箱（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 27 | 501 | 采威海市 jact 市长信箱（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_yantai.py`（1 个符号）

> 适配器：**烟台市·互动交流·网上民声（jpaas-jact 网关，JSON 接口）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 29 | 501 | 采烟台「网上民声」（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sd_zaozhuang.py`（1 个符号）

> 适配器：**枣庄市·政民互动·市长信箱（IGI 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 35 | 501 | 采枣庄市 IGI 市长信箱（含答复原文）。 |

### `tools/gov-qa/adapters/sd_zibo.py`（1 个符号）

> 适配器：**淄博市·政民互动·我要咨询（jact 平台）**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 31 | 501 | 采淄博市 jact 我要咨询（问题 + 答复全文）。 |

### `tools/gov-qa/adapters/sh_12345.py`（3 个符号）

> 适配器：**上海市 · 12345 市民服务热线「诉求公开」**（办结诉求公示）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_decrypt_hex` 函数 | 66 | 2 | AES-128-ECB(hex) → 明文（PKCS7 去填充）。 |
| `_page` 函数 | 75 | 29 | 取第 page 页并解密 → {count, list}。 |
| `harvest` 函数 | 88 | 501 | 按 startPage 翻页取「诉求公开」（列表已带问题+答复全文，无需再抓明细）。 |

### `tools/gov-qa/adapters/shannan_igi.py`（1 个符号）

> 适配器：**山南市·政民互动信箱（IGI 平台，7 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 50 | 501 | 取山南市已答复信件（`limit` 为本轮新增上限）。 |

### `tools/gov-qa/adapters/shenyang_igi.py`（2 个符号）

> 适配器：**沈阳市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 8 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 55 | 47 | 剥离**恒定**地域（= 门户/站点默认值）。 |
| `harvest` 函数 | 81 | 501 | 遍历沈阳各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/sn_igi.py`（1 个符号）

> 适配器：**陕西省·我向省长说句话·留言选登（门户 IGI 平台）**——IGI 中间件。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 45 | 501 | 采陕西省门户 IGI 留言选登（含答复原文）。 |

### `tools/gov-qa/adapters/sn_lyxd.py`（4 个符号）

> 适配器：**陕西省·我向省长说句话·留言选登**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 57 | 144 | — |
| `_view` 函数 | 61 | 3 | — |
| `_parse_detail` 函数 | 66 | 60 | — |
| `harvest` 函数 | 95 | 501 | 翻完所有列表页，逐条取明细（按 URL 去重）。 |

### `tools/gov-qa/adapters/sq_szxx.py`（6 个符号）

> 适配器：**商丘市·市长信箱**（`/Petition/list?petitionLetterBoxId=13`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 81 | 172 | 去标签 + 还原实体 + 压空白。 |
| `_real` 函数 | 96 | 123 | 清洗后只保留真实内容（`null`/空串一律当没有）。 |
| `_cell` 函数 | 102 | 46 | — |
| `_parse_list` 函数 | 107 | 18 | 从列表页抽条目（只读，不落库）。 |
| `_parse_detail` 函数 | 134 | 60 | 从详情页抽答复正文（`trResults` 区块）。 |
| `harvest` 函数 | 157 | 501 | 翻列表 + 逐条取详情。 |

### `tools/gov-qa/adapters/sx_igi.py`（2 个符号）

> 适配器：**山西省·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 108 | 47 | ① 丢弃「答复==问题」的占位记录。 |
| `harvest` 函数 | 127 | 501 | 遍历山西各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。 |

### `tools/gov-qa/adapters/sx_szxx.py`（1 个符号）

> 适配器：**山西省·省长信箱**——IGI 平台（与宁夏/贵州/吉林同族）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 36 | 501 | 按 IGI 基座采山西省长信箱的已答复信件。 |

### `tools/gov-qa/adapters/tj_enorth.py`（7 个符号）

> 适配器：**天津市·政民零距离**（北方网 enorth 平台，55 部门/区县）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_dec` 函数 | 142 | 3 | gb2312 解码（该站 Content-Type 为 GBK，但历史页可能混杂。 |
| `_text` 函数 | 153 | 144 | — |
| `_parse_list` 函数 | 157 | 18 | 从 list9a.jsp 表格里取每行：明细 URL / id / 标题 / 日期 / 是否已回复。 |
| `_parse_detail` 函数 | 176 | 60 | 从明细页取 问题/答复/发表人/提问时间/回复部门/回复时间。 |
| `_selected_depts` 函数 | 214 | 2 | 按 TJ_ENORTH_DEPTS 过滤（空 = 全部 55 个）。 |
| `_cap` 函数 | 222 | 13 | — |
| `harvest` 函数 | 229 | 501 | 逐部门翻列表 + 逐条抓明细，取「已回复」问答。 |

### `tools/gov-qa/adapters/tj_hdjl.py`（3 个符号）

> 适配器：**天津市·政民互动·留言选登**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 51 | 144 | — |
| `_parse_detail` 函数 | 55 | 60 | 从明细页取 问题 / 答复 / 回复单位 / 发布时间。 |
| `harvest` 函数 | 82 | 501 | 翻完所有列表页，逐条取明细（按 URL 去重）。 |

### `tools/gov-qa/adapters/tl_hdjl.py`（4 个符号）

> 适配器：**铜陵市·政民互动·信件公开**（`/api/mail/`，安徽第 1 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 91 | 172 | — |
| `_real` 函数 | 105 | 123 | — |
| `_dept_of` 函数 | 110 | 14 | 从 `metadataList` 取「答复单位」。 |
| `harvest` 函数 | 143 | 501 | 翻列表（GET JSON）+ 逐条取详情。 |

### `tools/gov-qa/adapters/tongliao_igi.py`（2 个符号）

> 适配器：**通辽市·政民互动信箱（IGI 平台，39 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 48 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 70 | 501 | 遍历通辽各 siteId 取已答复信件。 |

### `tools/gov-qa/adapters/wh_hdjl.py`（8 个符号）

> 适配器：**芜湖市·12345 政务服务便民热线·信件选登**（安徽第 4 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 138 | 100 | 读 `data/<site_key>-*.jsonl` 已有 id（增量续采用）。 |
| `_clean` 函数 | 161 | 172 | — |
| `_real` 函数 | 174 | 123 | — |
| `_norm_type` 函数 | 179 | 3 | 站方标签归一化：「我要咨询」→「咨询」（去掉前缀，保留语义）。 |
| `_parse_list` 函数 | 187 | 18 | 列表响应 → `(items, meta)`。 |
| `_parse_detail` 函数 | 220 | 60 | 详情页 → `{answer, asked_at, answered_at, msg_type, dept, title, question}`。 |
| `_get` 函数 | 244 | 16 | 带退避重试的取页。 |
| `harvest` 函数 | 272 | 501 | 翻列表 JSON（pageIndex **1 起**）+ 逐条取明细。 |

### `tools/gov-qa/adapters/xianyang_igi.py`（2 个符号）

> 适配器：**咸阳市·政民互动信箱（IGI 平台，17 个 siteId）**——2026-10-09 第 11 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `postprocess` 函数 | 52 | 47 | 剥离**恒定**地域（= 门户默认值）。 |
| `harvest` 函数 | 77 | 501 | 遍历咸阳各 siteId 取已答复信件。 |

### `tools/gov-qa/adapters/xining_igi.py`（1 个符号）

> 适配器：**西宁市·政民互动信箱（IGI 平台，siteId=43/4）**——2026-10-09 第 8 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 57 | 501 | 取西宁市已答复信件（`limit` 为本轮新增上限）。 |

### `tools/gov-qa/adapters/xj_dchs.py`（4 个符号）

> 适配器：**新疆维吾尔自治区·互联网+督查·督查回声**（静态列表 + 静态明细）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 58 | 144 | — |
| `_page_url` 函数 | 66 | 4 | — |
| `_parse_detail` 函数 | 70 | 60 | — |
| `harvest` 函数 | 87 | 501 | 翻完督查回声列表页，逐条取明细（按明细 URL 去重）。 |

### `tools/gov-qa/adapters/xz_igi.py`（1 个符号）

> 适配器：**西藏自治区·人民政府门户 IGI 信箱（多 site）**——IGI 平台。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 48 | 501 | 遍历西藏门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。 |

### `tools/gov-qa/adapters/xz_lasa.py`（4 个符号）

> 适配器：**拉萨市·来信选登**（`/communication/api-mailbox/frontMail/mailList`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 83 | 172 | — |
| `_body` 函数 | 92 | 17 | — |
| `fetch_detail` 函数 | 101 | 8 | 取一条来信的详情（**答复正文在这里**）。 |
| `harvest` 函数 | 145 | 501 | 翻页取拉萨来信选登：**列表取元数据 + 逐条取详情补答复**。 |

### `tools/gov-qa/adapters/yn_xf.py`（4 个符号）

> 适配器：**云南省网上信访平台 · 案例选登**（网络问政公开问答）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 67 | 144 | — |
| `_split_qa` 函数 | 72 | 2 | 把 `{日期}网民反映：{问} {日期}{单位}回复：{答}` 拆成 (问, 答, 问日, 答日, 单位)。 |
| `_one` 函数 | 123 | 34 | — |
| `harvest` 函数 | 154 | 501 | 翻页取「案例选登」公开问答（列表已含全文，无需再抓明细）。 |

### `tools/gov-qa/adapters/zhangye_igi.py`（1 个符号）

> 适配器：**张掖市·政民互动信箱（IGI 平台，8 个 siteId）**——2026-10-09 第 10 轮新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 54 | 501 | 取张掖市已答复信件（`limit` 为本轮新增上限）。 |

### `tools/gov-qa/adapters/zj_hangzhou.py`（1 个符号）

> 适配器：**杭州市·民呼我为统一平台·办理公开**（`code=330100`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采杭州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_huzhou.py`（1 个符号）

> 适配器：**湖州市·民呼我为统一平台·办理公开**（`code=330500`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采湖州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_jiaxing.py`（1 个符号）

> 适配器：**嘉兴市·民呼我为统一平台·办理公开**（`code=330400`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采嘉兴市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_jinhua.py`（1 个符号）

> 适配器：**金华市·民呼我为统一平台·办理公开**（`code=330700`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采金华市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_lishui.py`（1 个符号）

> 适配器：**丽水市·民呼我为统一平台·办理公开**（`code=331100`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采丽水市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_mhww.py`（5 个符号）

> 适配器：**浙江省 · 民呼我为统一平台「办理公开」**（zxts.zjzwfw.gov.cn）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_existing_ids` 函数 | 69 | 2 | 读本适配器**自己已落盘**的 `data/zj-mhww-*.jsonl`，取出已有 storeid。 |
| `_glyph_char` 函数 | 90 | 2 | glyph 名 → 真字。 |
| `_font_map` 函数 | 108 | 2 | — |
| `_decode` 函数 | 124 | 36 | 解 `#<fid>otltag…<text>#FontTag`。 |
| `harvest` 函数 | 136 | 501 | 翻页取「来件选登」，逐条取明细拿问题+答复（明细文字需按 woff 字体解码）。 |

### `tools/gov-qa/adapters/zj_ningbo.py`（1 个符号）

> 适配器：**宁波市·民呼我为统一平台·办理公开**（`code=330200`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采宁波市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_quzhou.py`（1 个符号）

> 适配器：**衢州市·民呼我为统一平台·办理公开**（`code=330800`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采衢州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_shaoxing.py`（1 个符号）

> 适配器：**绍兴市·民呼我为统一平台·办理公开**（`code=330600`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采绍兴市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_taizhou.py`（1 个符号）

> 适配器：**台州市·民呼我为统一平台·办理公开**（`code=331000`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采台州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_wenzhou.py`（1 个符号）

> 适配器：**温州市·民呼我为统一平台·办理公开**（`code=330300`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采温州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zj_zhoushan.py`（1 个符号）

> 适配器：**舟山市·民呼我为统一平台·办理公开**（`code=330900`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `harvest` 函数 | 37 | 501 | 采舟山市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。 |

### `tools/gov-qa/adapters/zk_zxsq.py`（4 个符号）

> 适配器：**周口市·政民互动·咨询受理**（`/front/mailbox/`，河南第 4 个可采市级源）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 73 | 172 | — |
| `_real` 函数 | 85 | 123 | — |
| `_parse_detail` 函数 | 90 | 60 | 详情页 → `{question, answer, asked_at, answered_at, dept}`。 |
| `harvest` 函数 | 124 | 501 | 取 token → 翻列表（POST）→ 逐条取详情。 |

### `tools/gov-qa/channel.py`（10 个符号）

> 通道（Channel）—— 从现有 331 个 adapter 自动构建的通道清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Channel` 类 | 48 | 26 | 一个可采集的数据来源。 |
| `__init__` 函数 | 54 | 135 | — |
| `__repr__` 函数 | 67 | 3 | — |
| `infer_watermark_type` 函数 | 73 | 2 | 按 adapter 特征猜水位类型（T010）。 |
| `infer_region` 函数 | 105 | 9 | 从 SITE 解析 (level, region)（T011）。 |
| `_city_from_name` 函数 | 139 | 10 | 从名字开头提取市名（如「宝鸡市·政民互动」→「宝鸡市」）。 |
| `_province_from_name` 函数 | 157 | 8 | 从名字里提取省级行政区名。 |
| `_region_from_name` 函数 | 177 | 1 | （保留给旧调用方）按 level 提取地区名。 |
| `load_channels` 函数 | 186 | 24 | 从 `adapters.ADAPTERS` 构建全部通道（T009）。 |
| `group_by_level` 函数 | 222 | 3 | 按层级分组，供覆盖销号表用。 |

### `tools/gov-qa/common.py`（12 个符号）

> 公共工具层 —— 可运维化特性（spec 004）的基础设施。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `ascii_kv` 函数 | 35 | 30 | 输出 `KEY=VALUE` 形式的**纯 ASCII** 机器可读结果。 |
| `safe_print` 函数 | 57 | 65 | 打印，**绝不因控制台编码抛异常**。 |
| `human` 函数 | 80 | 116 | 给人看的输出（可用中文）。 |
| `atomic_append_jsonl` 函数 | 104 | 7 | 单行 JSON 追加写入。 |
| `iter_records` 函数 | 120 | 13 | 流式读 jsonl，**跳过坏行**（不因一行坏掉就整个文件读不了）。 |
| `LockBusy` 类 | 142 | 10 | 抢锁失败 —— **不是失败**，是「有人在跑」。 |
| `file_lock` 函数 | 147 | 10 | 基于 `O_CREAT\|O_EXCL` 的跨进程文件锁。 |
| `label_key_of` 函数 | 203 | 3 | 返回这条记录**实际带标签的那个键名**，没有则 `None`。 |
| `has_label` 函数 | 217 | 7 | 这条记录算不算「有类型标签」。 |
| `now_iso` 函数 | 231 | 10 | 本地时间 ISO 串（秒精度）。 |
| `load_json` 函数 | 236 | 3 | 读 JSON。 |
| `save_json` 函数 | 245 | 4 | 写 JSON（先写临时文件再 rename，避免写一半损坏）。 |

### `tools/gov-qa/coverage-report.py`（4 个符号）

> 覆盖销号表 CLI —— spec 004 的 US2。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_missing_cities_detail` 函数 | 44 | 7 | 算「334 市全名单里，数据口径下零记录的有哪些」。 |
| `_missing_city_count` 函数 | 72 | 2 | 只要总数（给 `--quiet` 用）。 |
| `_scope_filter` 函数 | 80 | 2 | 口径过滤器（FR-034）。 |
| `main` 函数 | 96 | 1131 | — |

### `tools/gov-qa/coverage.py`（16 个符号）

> 覆盖单元（CoverageUnit）—— 覆盖销号表的计算核心。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `CoverageUnit` 类 | 58 | 23 | 一个行政区或机构。 |
| `__init__` 函数 | 97 | 135 | — |
| `recompute` 函数 | 112 | 10 | 按当前数据算状态与缺口（**状态是算出来的，不是存下来的**）。 |
| `to_dict` 函数 | 138 | 7 | — |
| `__repr__` 函数 | 150 | 3 | — |
| `count_by_source` 函数 | 157 | 7 | 统计每个来源的落盘条数。 |
| `norm_city` 函数 | 177 | 12 | 归一化市名：去空白。 |
| `channel_city_map` 函数 | 192 | 7 | `{通道 key: 归一化市名}` —— 只含 `level == "city"` 且有 region 的通道。 |
| `known_cities` 函数 | 205 | 8 | **本表收录的 334 项**地级行政区全称集合（来自 `regions.PROVINCE_CITIES`）。 |
| `count_by_city` 函数 | 222 | 14 | **数据口径**：按记录归属的地级市统计条数（见 `CoverageUnit.data_records`）。 |
| `merge_city_data` 函数 | 258 | 4 | 把**数据口径**的市并入覆盖单元：已存在的填 `data_records`，缺失的**新建**。 |
| `_count_for_channel` 函数 | 282 | 7 | 某通道的数据量 = 它自己 + 所有以 `它-` 开头的子 source。 |
| `_attribute_counts` 函数 | 306 | 4 | 把 `counts` 里每个 source 归给「最长匹配的通道 key」，返回本通道拿到的合计。 |
| `build_units` 函数 | 327 | 22 | 把通道 + 条数聚合成覆盖单元。 |
| `_province_of_city` 函数 | 424 | 3 | 由市名反查所属省。 |
| `uncovered_for` 函数 | 463 | 7 | 列出该单元**尚未建立来源的渠道**（FR-010）。 |

### `tools/gov-qa/harvest.py`（3 个符号）

> 政务问答采集 · 统一入口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_done` 函数 | 50 | 6 | — |
| `_safe` 函数 | 73 | 11 | 把字符串转成当前控制台能打印的形式（非 GBK 字符替换掉，绝不抛异常）。 |
| `main` 函数 | 85 | 1131 | — |

### `tools/gov-qa/health.py`（7 个符号）

> 健康结论 —— spec 004 的 US4（FR-017 ~ FR-021 / SC-009 ~ SC-011）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_count_lines` 函数 | 57 | 1 | — |
| `count_empty_adapters` 函数 | 68 | 6 | 数「零数据适配器」。 |
| `count_adapters` 函数 | 98 | 2 | — |
| `count_duplicate_ids` 函数 | 106 | 5 | 全库重复 id 行数 —— **按 `(source, id)` 全局计数**。 |
| `collect` 函数 | 138 | 73 | 一次遍历收集全部判据（**一次运行检出全部故障**，SC-009）。 |
| `build_checks` 函数 | 180 | 9 | 把实测值判成 `(名称, 是否通过, 详情)` 列表。 |
| `main` 函数 | 200 | 1131 | — |

### `tools/gov-qa/measure-locate-rate.py`（4 个符号）

> 政务问答 · 把采集到的问答切成**两类资产**（考卷 / 补料清单）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `norm` 函数 | 65 | 84 | — |
| `load_lib` 函数 | 69 | 8 | — |
| `find_std` 函数 | 79 | 11 | — |
| `main` 函数 | 89 | 1131 | — |

### `tools/gov-qa/poll.py`（8 个符号）

> 增量轮询调度器 —— spec 004 的 US1（P1，MVP）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `existing_ids` 函数 | 58 | 100 | 读该通道已落盘的全部 id（幂等的基础，T017）。 |
| `data_path_for` 函数 | 99 | 10 | 该通道的落盘路径。 |
| `poll_one` 函数 | 107 | 32 | 轮询一个通道。 |
| `_should_stop` 函数 | 243 | 3 | 判断是否可以停止翻页（R1 的「翻到已知位置就停」）。 |
| `_next_value` 函数 | 261 | 3 | 算新水位值。 |
| `_make_fetch` 函数 | 286 | 2 | 构造 fetch 函数（复用 harvest.py 的会话策略）。 |
| `main` 函数 | 303 | 1131 | — |
| `_run` 函数 | 327 | 73 | — |

### `tools/gov-qa/probe-ministries.py`（2 个符号）

> 国家部委互动栏目 · **批量核验器**（把业主给的清单逐条探一遍，机器分类）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `classify` 函数 | 104 | 45 | — |
| `main` 函数 | 130 | 1131 | — |

### `tools/gov-qa/query.py`（4 个符号）

> 政务问答语料 · 筛选/导出工具。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `province_of` 函数 | 62 | 9 | 判省 —— **直接复用 `recon/coverage-matrix.py` 的 `province_of(rec)`**，别自己重写。 |
| `iter_records` 函数 | 75 | 13 | 遍历全部 jsonl。 |
| `show_stats` 函数 | 87 | 2 | — |
| `main` 函数 | 118 | 1131 | — |

### `tools/gov-qa/recon/ah-column-raw.py`（1 个符号）

> 看安徽问答知识库栏目的原始 HTML：条目链接写法与翻页方式（不猜，直接看源码）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/ah-detail-debug.py`（2 个符号）

> 看安徽问答知识库明细页结构（写解析器前必须先看真实标记）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 19 | 197 | — |
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/ah-gap-diagnose.py`（1 个符号）

> 诊断安徽问答知识库「列表有、采不到」的那批条目：抽样看明细页到底缺什么。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/ah-ln-probe.py`（2 个符号）

> 探安徽「问答知识库」与辽宁「咨询服务/历史咨询服务」两处的规模与结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 26 | 197 | — |
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/ah-page-diagnose.py`（1 个符号）

> 逐条统计安徽某一页的明细抓取结果（200? 解析成功?），定位 59 条丢失的真实原因。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/anhui-column-probe.py`（1 个符号）

> 安徽省生态环境厅 · public/column 型 CMS 列表页探测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/answer-authenticity-review.py`（1 个符号）

> 同类风险复查：湖南统一平台 / 广东 hdjlpt 的 answer 字段是不是真官方答复。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/answer-pollution-scan.py`（1 个符号）

> 量化抽查：各源 answer 字段的污染面。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/audit-coverage.py`（8 个符号）

> 数据落盘核查 —— 对每个已登记适配器，核对它的数据文件里到底有多少条。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `safe_print` 函数 | 41 | 65 | 打印，**绝不因控制台编码抛异常**（spec 005 T108，2026-10-10 修）。 |
| `count_lines` 函数 | 62 | 4 | 数有效行（跳过采集进行中的半行）。 |
| `show_fields` 函数 | 72 | 2 | 各字段非空率 —— 用来发现「整列全空」的静默数据缺陷。 |
| `show_answers` 函数 | 117 | 2 | 答复长度分布 —— 用来发现「答复被截断」这类静默缺陷。 |
| `show_dups` 函数 | 220 | 4 | 重复 id 检测 —— 用来发现「并发写导致重复落盘」。 |
| `show_targets` 函数 | 278 | 2 | 对比「枚举/接口自报总量」vs「实际落盘量」—— 发现「采了但远未达目标」。 |
| `show_gate` 函数 | 331 | 9 | 给 `check.sh` 用的**纯 ASCII 机器可读输出**。 |
| `main` 函数 | 410 | 1131 | — |

### `tools/gov-qa/recon/audit-igi-new.py`（1 个符号）

> 抽查 2026-10-08 四个新 IGI 通道（贵州商务 / 贵州自然资源 / 吉林人社 / 吉林交通运输）的 answer 质量。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/audit-igi-prov.py`（1 个符号）

> 按**来源前缀**抽查 IGI 整省源的 answer 质量与三级归属覆盖（通用版）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/audit-prov-fid.py`（1 个符号）

> 抽查新增通道（分省 / 定向）的 answer 质量：有没有"问题当答复"、跟帖串位、空答复。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/build-city-domains.py`（4 个符号）

> 构建 **city → 门户域名** 映射（M4 的根阻塞）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `core_name` 函数 | 66 | 3 | 取「专名」：`昌吉回族自治州` → `昌吉`。 |
| `candidates` 函数 | 84 | 52 | 返回 `\[(候选域名, via)\]`。 |
| `probe` 函数 | 102 | 301 | 实测域名是否可达。 |
| `main` 函数 | 115 | 1131 | — |

### `tools/gov-qa/recon/build-fid-map.py`（1 个符号）

> 从已采的留言板数据生成「省市 → fid」映射表（供 people-liuyan-fid 定向采集）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/build-netizen-asset.py`（1 个符号）

> 把「网友跟帖」（`extra.netizen_comments`）抽成**独立标注资产**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/bw-review-export.py`（1 个符号）

> 把部委流 30 条记录的问答导出成文本，人工判定「答复」是不是官方口吻。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 12 | 1131 | — |

### `tools/gov-qa/recon/check-locate-rate-caliber.py`（4 个符号）

> 核 `locate-rate.json` 的口径：**A=3,868 这个数有多少是靠"宽松兜底"来的？**

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `norm` 函数 | 35 | 84 | — |
| `load_lib` 函数 | 39 | 8 | — |
| `find_std2` 函数 | 49 | 2 | 返回 (命中号, 哪一级)：exact / loose / miss。 |
| `main` 函数 | 60 | 1131 | — |

### `tools/gov-qa/recon/city-coverage-from-data.py`（2 个符号）

> 用**数据本身**量「地级市覆盖」，而不是只看「注册了多少个 city 通道」。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_norm` 函数 | 40 | 21 | 归一化市名：去空白、去「地区/自治州/盟」后缀差异尽量保留，缺「市」则补。 |
| `main` 函数 | 53 | 1131 | — |

### `tools/gov-qa/recon/city-js-hunt.py`（2 个符号）

> 江苏 13 地市门户「政民互动」入口侦察。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `links` 函数 | 42 | 142 | — |
| `main` 函数 | 53 | 1131 | — |

### `tools/gov-qa/recon/city-js-jact-scan.py`（1 个符号）

> jact 站 sysid 枚举器（地市通用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe10.py`（1 个符号）

> stage10：苏州/无锡 分页参数名 + 南通 siteId + 南京 huifuxuandeng。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe11.py`（1 个符号）

> stage11：苏州 main.js 参数 + 无锡完整项 + 南京 SPA JS。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe12.py`（1 个符号）

> stage12：无锡 resultAnswer 确认 + 苏州分页参数穷举（GET/POST form/json）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe13.py`（2 个符号）

> stage13：苏州 main.js 里 bmxxCommonlist 调用点 + 参数构造。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe14.py`（2 个符号）

> stage14：定位苏州 bmxxCommonlist 调用点（RB 常量使用处）+ totalcount。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe15.py`（2 个符号）

> stage15：苏州 bmxxCommonlist 正确分页参数 currpage/pagesize 验证。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe16.py`（2 个符号）

> stage16：苏州 getBmxxDetail 明细端点参数 + 内容（补全问题正文）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe17.py`（2 个符号）

> stage17：连云港明细定位 + 南通 getInteractiveJson 字段 + 常州列表接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe18.py`（2 个符号）

> stage18：南通 getInteractiveJson 字段 + 常州 ajax.php(https) 列表结构 + 连云港重试。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe19.py`（2 个符号）

> stage19：常州明细页结构 + 南通互动页真实接口 + 南京 SPA 接口定位。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe2.py`（1 个符号）

> 江苏地市「政民互动」二级页指纹侦察（stage2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 44 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe20.py`（2 个符号）

> stage20：南通 xxList.do 调用参数 + 南京 SPA 资源接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe21.py`（2 个符号）

> stage21：南通 messageController/getMessageByCondition.do 实测（市长信箱列表）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe22.py`（2 个符号）

> stage22：南京 SPA 回复选登接口定位（grep 全部 chunk）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe23.py`（2 个符号）

> stage23：南京 app.js 里回复选登组件的 API 路径。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe24.py`（2 个符号）

> stage24：南京 全 chunk 扫 API 路径（baseURL=/prod-api/）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe25.py`（2 个符号）

> stage25：南京 /prod-api/wsxf/* 接口实测（回复选登候选）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe26.py`（2 个符号）

> stage26：南京 定位「回复选登」chunk + algk/listPage 字段。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 14 | 1460 | — |
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe27.py`（2 个符号）

> stage27：常州 明细获取路径（主域 ajax detail / 子域 show / 列表是否含答复）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe28.py`（2 个符号）

> stage28：淮安门户找互动入口 + 连云港重试。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe29.py`（2 个符号）

> stage29：淮安 互动栏目深挖（导航全链接 + 候选 URL）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe3.py`（1 个符号）

> 江苏地市互动列表页深挖（stage3）：抓列表页 → 报告 iframe/JSON/分页接口线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 35 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe4.py`（2 个符号）

> 江苏剩余 7 市深挖（stage4）：苏州 SPA / 无锡 / 南通 / 连云港 / 南京 / 淮安 / 常州。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dig` 函数 | 25 | 42 | — |
| `main` 函数 | 72 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe5.py`（2 个符号）

> 江苏剩余市接口实测（stage5）：苏州/无锡/连云港/南通/南京。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `show` 函数 | 20 | 75 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe6.py`（1 个符号）

> 苏州/无锡/连云港 明细与结构实测（stage6）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 16 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe7.py`（1 个符号）

> 苏州/无锡/连云港 明细接口定位（stage7）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe8.py`（1 个符号）

> stage8：苏州答复字段完整性 + 无锡/连云港明细接口定位。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-probe9.py`（1 个符号）

> stage9：苏州/无锡 完整字段 + 连云港 letterView 内容 + 南通/南京。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/city-js-zj-zjmhww-probe.py`（1 个符号）

> 浙江「民呼我为统一平台」地市码探测：验证 code=33xx00 是否返回该市来件。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe1.py`（3 个符号）

> city-sc-probe1：四川前 6 市门户首页 → 互动栏目入口提取。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 25 | 1460 | — |
| `fetch` 函数 | 32 | 1027 | — |
| `main` 函数 | 42 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe10.py`（3 个符号）

> city-sc-probe10：攀枝花 letterListJson 实测 / 自贡 collect_list.js 全文 / 绵阳 nav 源。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe11.py`（3 个符号）

> city-sc-probe11：攀枝花 letterListJson 正确参数 / 自贡 szxx ajaxUrl 配置。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe12.py`（3 个符号）

> city-sc-probe12：攀枝花 searchLetterPager 调用实参 / 自贡 szxx 页尾脚本。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe13.py`（3 个符号）

> city-sc-probe13：自贡 来信选登 lxxd API / 攀枝花 500 详情 / 泸州分页确认。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe14.py`（2 个符号）

> city-sc-probe14：绵阳 my.gov.cn / 德阳 / 攀枝花 session 流。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe15.py`（3 个符号）

> city-sc-probe15：德阳 appeal 模块 / 绵阳互动栏目定位。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe16.py`（2 个符号）

> city-sc-probe16：成都 全头/备域 / 攀枝花 channelId 与 POST 试。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe17.py`（3 个符号）

> city-sc-probe17：四川第 7~21 市门户首页 → 互动入口（扫 href 全集，含短域名回退）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 32 | 1460 | — |
| `fetch` 函数 | 39 | 1027 | — |
| `main` 函数 | 50 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe18.py`（3 个符号）

> city-sc-probe18：四川第 7~21 市 互动入口深挖（扒 script/接口常量/中间件指纹）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 56 | 1460 | — |
| `get` 函数 | 63 | 6333 | — |
| `main` 函数 | 71 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe19.py`（3 个符号）

> city-sc-probe19：扒 JS 常量 —— 广安/资阳(config.js+commonApi+zmhd)、内江(zw_mailbox)、雅安(mail.js)、乐山(hdjl.js)、阿坝/广元。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 32 | 1460 | — |
| `get` 函数 | 39 | 6333 | — |
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe2.py`（3 个符号）

> city-sc-probe2：成都(http/412) / 自贡重试 / 泸州LetterBox / 攀枝花+绵阳 hdcy / 德阳 nav。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe20.py`（3 个符号）

> city-sc-probe20：第 7~21 市 首页/互动页 找「数融 pc/list.html」模板与 API 线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 33 | 1460 | — |
| `get` 函数 | 40 | 6333 | — |
| `main` 函数 | 47 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe21.py`（3 个符号）

> city-sc-probe21：第 7~21 市 互动落地页深挖 —— 列 script、条目链接、api 线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 33 | 1460 | — |
| `get` 函数 | 40 | 6333 | — |
| `main` 函数 | 47 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe22.py`（5 个符号）

> city-sc-probe22：广元互动入口 + 乐山/巴中/阿坝/凉山/宜宾/达州/眉山 API 线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 15 | 1460 | — |
| `get` 函数 | 22 | 6333 | — |
| `scan_href` 函数 | 29 | 2 | — |
| `raw_scan` 函数 | 49 | 9 | — |
| `main` 函数 | 68 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe23.py`（5 个符号）

> city-sc-probe23：乐山/宜宾/阿坝/广元/凉山 深挖（JS 常量 + 入口页结构）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dump_js` 函数 | 27 | 5 | — |
| `dump_html_hrefs` 函数 | 44 | 3 | — |
| `main` 函数 | 64 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe24.py`（5 个符号）

> city-sc-probe24：南充 IGI siteId 枚举(1..30) + 乐山/宜宾/广元/凉山 入口深挖。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `igi_enum` 函数 | 27 | 4 | — |
| `hrefs` 函数 | 45 | 17 | — |
| `main` 函数 | 70 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe25.py`（5 个符号）

> city-sc-probe25：南充 IGI siteId 枚举(修正) + 宜宾来信选登/巴中/凉山/广元 深挖。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 14 | 1460 | — |
| `get` 函数 | 21 | 6333 | — |
| `igi_enum` 函数 | 31 | 4 | — |
| `inspect` 函数 | 49 | 108 | — |
| `main` 函数 | 78 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe26.py`（3 个符号）

> city-sc-probe26：广元真域名试探 + 宜宾/巴中/凉山/乐山 列表 API 深挖。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe27.py`（4 个符号）

> city-sc-probe27：宜宾12345/雅安/眉山/达州/乐山 是否有公开信件列表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `probe` 函数 | 30 | 301 | — |
| `main` 函数 | 56 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe28.py`（3 个符号）

> city-sc-probe28：宜宾 DoExcerpts/List + 雅安 leader/detail + 乐山 wdzsk 问答库。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe29.py`（4 个符号）

> city-sc-probe29：乐山信箱页定位 + 凉山/雅安/眉山/达州 复核。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `text_of` 函数 | 30 | 5 | — |
| `main` 函数 | 36 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe3.py`（3 个符号）

> city-sc-probe3：泸州 LetterBox 数据接口 / 德阳 iList / 攀枝花+绵阳 首页接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 29 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe30.py`（3 个符号）

> city-sc-probe30：乐山详情复核 + 凉山12345信件选登 + 雅安 mail 列表 API。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe31.py`（5 个符号）

> city-sc-probe31：雅安 信箱列表 + 详情字段结构 + 分页 + 眉山/达州 复核。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dec` 函数 | 30 | 86 | — |
| `strip` 函数 | 37 | 1470 | — |
| `main` 函数 | 41 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe32.py`（4 个符号）

> city-sc-probe32：雅安详情页原始 HTML 片段（信件内容/办理情况容器）+ 分页总数。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dec` 函数 | 30 | 86 | — |
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe33.py`（5 个符号）

> city-sc-probe33：眉山 / 达州 互动栏目深挖（首页链接 + 候选接口）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dec` 函数 | 30 | 86 | — |
| `links` 函数 | 37 | 142 | — |
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe34.py`（4 个符号）

> city-sc-probe34：眉山 互动交流 / 达州 民议征集 深挖。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dec` 函数 | 30 | 86 | — |
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe35.py`（4 个符号）

> city-sc-probe35：达州 ThinkPHP 民议征集 JSON + 眉山 WCM 来信选登。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 14 | 1460 | — |
| `get` 函数 | 21 | 6333 | — |
| `dec` 函数 | 31 | 86 | — |
| `main` 函数 | 38 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe36.py`（4 个符号）

> city-sc-probe36：达州 xinxiang/ + hdjl 列表结构；眉山 WCM 分页/详情。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `dec` 函数 | 30 | 86 | — |
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe37.py`（5 个符号）

> city-sc-probe37：达州 /xinxiang/ 内容；眉山 list_ldxx.jsp 表单+行结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `post` 函数 | 30 | 506 | — |
| `dec` 函数 | 40 | 86 | — |
| `main` 函数 | 47 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe38.py`（5 个符号）

> city-sc-probe38：达州 xinxiang 原始 HTML；眉山 list_content_ldxxnew.jsp 翻页+详情。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `post` 函数 | 30 | 506 | — |
| `dec` 函数 | 40 | 86 | — |
| `main` 函数 | 47 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe39.py`（3 个符号）

> city-sc-probe39：达州 xinxiang 子页 letter-city.html；眉山 Session 翻页。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `dec` 函数 | 20 | 86 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe4.py`（3 个符号）

> city-sc-probe4：泸州列表结构+分页 / 攀枝花·绵阳 hdcy 子栏目 / 德阳找信箱。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe40.py`（3 个符号）

> city-sc-probe40：达州 xinxiang 子页枚举；眉山 GET 方式详情/翻页。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `dec` 函数 | 20 | 86 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe41.py`（3 个符号）

> city-sc-probe41：眉山详情页原始 HTML 片段（标题/诉求/办理结果容器）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `dec` 函数 | 20 | 86 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe42.py`（5 个符号）

> city-sc-probe42：成都 / 广元（瑞数 412）替代入口试探。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 15 | 1460 | — |
| `get` 函数 | 22 | 6333 | — |
| `dec` 函数 | 33 | 86 | — |
| `probe` 函数 | 40 | 301 | — |
| `main` 函数 | 57 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe43.py`（3 个符号）

> city-sc-probe43：广元市长信箱突破口（qgj.cngy.gov.cn:9050 绕过瑞数）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 15 | 1460 | — |
| `dec` 函数 | 22 | 86 | — |
| `main` 函数 | 29 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe44.py`（3 个符号）

> city-sc-probe44：四川政务服务网「政民互动」平台（可覆盖成都及全省，绕过瑞数）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 16 | 1460 | — |
| `dec` 函数 | 23 | 86 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe45.py`（2 个符号）

> city-sc-probe45：四川政务服务网「政民互动」——全省 21 市州 areaCode 总量普查。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 24 | 1460 | — |
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe5.py`（3 个符号）

> city-sc-probe5：泸州详情 / 攀枝花信箱接口 / 绵阳重测 / 德阳互动入口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe6.py`（3 个符号）

> city-sc-probe6：攀枝花 mailbox 全部接口 / 成都 API / 绵阳备域 / 自贡重试。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe7.py`（4 个符号）

> city-sc-probe7：攀枝花信箱列表接口 / 自贡zg.gov.cn / 绵阳my.gov.cn / 成都备域。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 13 | 1460 | — |
| `get` 函数 | 20 | 6333 | — |
| `links` 函数 | 31 | 142 | — |
| `main` 函数 | 40 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe8.py`（3 个符号）

> city-sc-probe8：攀枝花 mailbox.js / 自贡 yjzj API / 绵阳 nav 全链接。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/city-sc-probe9.py`（3 个符号）

> city-sc-probe9：自贡 szxx API / 绵阳 nav 源 / 攀枝花 mailbox.js ajax。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `w` 函数 | 12 | 1460 | — |
| `get` 函数 | 19 | 6333 | — |
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/coverage-by-level.py`（3 个符号）

> 省市县**三级覆盖**统计：按 `pForumNames` 归属链的层级统计，回答"市县到了没有"。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_is_province` 函数 | 23 | 7 | — |
| `level_of` 函数 | 27 | 2 | — |
| `main` 函数 | 38 | 1131 | — |

### `tools/gov-qa/recon/coverage-matrix.py`（3 个符号）

> 全国覆盖矩阵：把 data/ 里全部语料按**省级归属 × 来源**汇总成一张表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_is_province` 函数 | 68 | 7 | — |
| `province_of` 函数 | 76 | 9 | — |
| `main` 函数 | 95 | 1131 | — |

### `tools/gov-qa/recon/dedup-data.py`（1 个符号）

> 数据去重 —— 清理重复的 `(source, id)` 行。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 45 | 1131 | — |

### `tools/gov-qa/recon/dept-hd-dig.py`（2 个符号）

> 通用「厅局互动栏目」挖掘：对给定站点找互动入口 → 挖列表接口线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dig` 函数 | 40 | 42 | — |
| `main` 函数 | 73 | 1131 | — |

### `tools/gov-qa/recon/dept-hd-links.py`（1 个符号）

> 把 dept-hd-dig.json 里各站的互动入口列出来，供挑选下一步适配器目标。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 12 | 1131 | — |

### `tools/gov-qa/recon/df-datatype-diagnose.py`（6 个符号）

> 诊断：地方流（df）详情 contentList 里，哪种 dataType 才是【官方答复】。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_W` 类 | 26 | 8 | — |
| `__init__` 函数 | 27 | 135 | — |
| `post` 函数 | 30 | 506 | — |
| `fetch_detail` 函数 | 34 | 8 | — |
| `dump` 函数 | 44 | 51 | — |
| `main` 函数 | 52 | 1131 | — |

### `tools/gov-qa/recon/df-fid-target-test.py`（1 个符号）

> 验证：df 流是否支持按 fid 定向（拿某个地方领导版块的全部已办理留言）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/df-loop.py`（2 个符号）

> 无人值守循环 · 人民网领导留言板·地方时间流（people-liuyan-df）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `log` 函数 | 30 | 94 | — |
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/df-verify-fixed.py`（1 个符号）

> 核对修好后的 df（地方流）数据：省市归属 + 答复是否为官方口吻。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 13 | 1131 | — |

### `tools/gov-qa/recon/dig-hd-pages.py`（2 个符号）

> 省级站侦察第二步：定向挖掘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dig_page` 函数 | 33 | 2 | 从一个页面里挖出全部接口线索。 |
| `main` 函数 | 47 | 1131 | — |

### `tools/gov-qa/recon/dig2-js.py`（1 个符号）

> 省级站侦察第三步：追外部 JS 里的 channelid / 接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/field-audit.py`（1 个符号）

> 字段体检 —— spec 004 的 US3。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 43 | 1131 | — |

### `tools/gov-qa/recon/fix-mohurd-ids.py`（1 个符号）

> 重算 nat-mohurd 的 id —— 修 59 条 id 碰撞。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/fix-rd-reg.py`（1 个符号）

> 修正 rd-* 登记位置 —— 上一次误插进了 SITE 字典，应插进 ADAPTERS 字典。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/fujian-detail-link.py`（1 个符号）

> 福建省生态环境厅 · wyzx 页明细链接形态挖掘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/fujian-html-grep.py`（1 个符号）

> 从已存的福建 wyzx 整页 HTML 里找：列名 / 明细链接 / list 模块 JS 地址。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 14 | 1131 | — |

### `tools/gov-qa/recon/fujian-list-module.py`（1 个符号）

> 福建 sthj_2020.min.js → requirejs paths → 'list' 模块定位。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/fujian-tzxx-dig.py`（1 个符号）

> 福建省生态环境厅 · 厅长信箱/网上咨询 接口挖掘（WAS5 指纹已确认存在）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 38 | 1131 | — |

### `tools/gov-qa/recon/gate-quality.py`（11 个符号）

> 数据质量闸门 —— **四项静默缺陷判据的唯一数字源**（spec 005 / T102）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_p` 函数 | 131 | 25 | 把字符串转成当前控制台能打印的形式（**绝不抛异常**）。 |
| `_norm` 函数 | 144 | 21 | 归一化文本用于内容比较：去掉所有空白。 |
| `parse_time` 函数 | 158 | 9 | 把各站各式的日期串解析成 `datetime`。 |
| `_iter_all` 函数 | 195 | 2 | 流式读全部数据文件，yield `(path, rec)`。 |
| `collect` 函数 | 211 | 73 | 一次遍历算出四项判据（**一次运行检出全部**，不给闸门加多次全表扫描）。 |
| `verdicts` 函数 | 323 | 14 | 把实测值判成 `(名称, 是否通过, 详情)` —— **闸门只读这个**。 |
| `ratchet` 函数 | 343 | 15 | 棘轮判据：与基线比，**每个来源的缺陷率只许变好不许变坏**。 |
| `_per_source_rates` 函数 | 416 | 2 | `{source: {total, dup_rate}}` —— 棘轮的比较单位。 |
| `_load_baseline` 函数 | 421 | 12 | — |
| `_save_baseline` 函数 | 428 | 6 | 记基线。 |
| `main` 函数 | 465 | 1131 | — |

### `tools/gov-qa/recon/gd-dept-probe.py`（1 个符号）

> 广东厅局 hdjlpt 平台批量探测（_gd_hdjlpt_common 引擎的多租户扩展侦察）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/gd-dir-page.py`（1 个符号）

> 抓广东省政府厅局名录页（/zwgk/szfjg/）的完整子域清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `tools/gov-qa/recon/gd-domain-harvest.py`（5 个符号）

> 从广东省政府门户抓厅局真实域名清单 → 逐个探测 hdjlpt 平台。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_W` 类 | 37 | 8 | — |
| `__init__` 函数 | 38 | 135 | — |
| `post` 函数 | 41 | 506 | — |
| `collect_domains` 函数 | 45 | 2 | 域名 → 部门名（从门户页面链接锚文本取）。 |
| `main` 函数 | 70 | 1131 | — |

### `tools/gov-qa/recon/gd-portal-nav.py`（1 个符号）

> 在 gd.gov.cn 首页里找「省政府部门/政府机构」名录页的真实地址，并抓全清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/gen-channel-table.py`（6 个符号）

> 生成 `SITE-REGISTRY.md` 的**通道台账表**（spec 004 T052）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `landed_counts` 函数 | 53 | 2 | 每个通道**实际落盘**多少条（按文件名前缀归到最长匹配的通道 key）。 |
| `render` 函数 | 72 | 24 | — |
| `_stable_part` 函数 | 107 | 7 | 把「已落盘」一列抹掉后的表 —— `--check` 的比对基准。 |
| `splice` 函数 | 126 | 4 | 把受管区块换掉，**区块之外一个字不动**。 |
| `main` 函数 | 135 | 1131 | — |
| `_block_of` 函数 | 160 | 5 | 取出受管区块的内容（不含标记行）。 |

### `tools/gov-qa/recon/gen-gd-adapters.py`（1 个符号）

> 从 gd-dept-domains-probed.json 机械生成广东厅局薄壳适配器 + 重写 ADAPTERS 登记表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 54 | 1131 | — |

### `tools/gov-qa/recon/gen-gd-city-adapters.py`（1 个符号）

> 从 `probe-gd-city-hdjlpt.py` 的实测结果，生成**广东地级市** hdjlpt 薄壳适配器。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 82 | 1131 | — |

### `tools/gov-qa/recon/gen-gz-igi-adapters.py`（1 个符号）

> 按表生成贵州 IGI 厅局适配器（薄壳）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 125 | 1131 | — |

### `tools/gov-qa/recon/gen-jl-igi-adapters.py`（1 个符号）

> 按表生成吉林 IGI 厅局适配器（薄壳）——**34 个厅局**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 110 | 1131 | — |

### `tools/gov-qa/recon/gen-sc-zwfw-city-adapters.py`（1 个符号）

> 生成四川 20 个市州的「省政务服务网·政民互动」薄适配器（共用 `_sczwfw_common`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 77 | 1131 | — |

### `tools/gov-qa/recon/gen-zj-mhww-city-adapters.py`（1 个符号）

> 生成浙江 11 个地级市的「民呼我为统一平台」适配器（薄适配器，共用 _zj_mhww_common）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 76 | 1131 | — |

### `tools/gov-qa/recon/gs-hb-hub-probe.py`（1 个符号）

> GS/HB 站点侦察：探测门户/子域/中间件指纹的可达性（GS 与 HB）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 49 | 1131 | — |

### `tools/gov-qa/recon/gs-lx-direct.py`（4 个符号）

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `F` 类 | 13 | 200 | — |
| `__init__` 函数 | 14 | 135 | — |
| `__call__` 函数 | 17 | 12 | — |
| `post` 函数 | 20 | 506 | — |

### `tools/gov-qa/recon/gs-more-probe.py`（2 个符号）

> 甘肃剩余市州侦察：天水 / 临夏（worker-gansu）。只读探测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 15 | 6333 | — |
| `main` 函数 | 29 | 1131 | — |

### `tools/gov-qa/recon/gs4-baiyin-deep.py`（2 个符号）

> 甘肃白银接口深探：比较变体、dump 字段、确认分页语义。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dump` 函数 | 16 | 51 | — |
| `main` 函数 | 39 | 1131 | — |

### `tools/gov-qa/recon/gs4-baiyin-detail.py`（1 个符号）

> 白银详情页实测：抓一条 iid 看问答结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 16 | 1131 | — |

### `tools/gov-qa/recon/gs4-dingxi-zhangye.py`（3 个符号）

> 定西（jact, http）与张掖（IGI, http）实测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dingxi` 函数 | 14 | 11 | — |
| `zhangye` 函数 | 33 | 32 | — |
| `main` 函数 | 48 | 1131 | — |

### `tools/gov-qa/recon/gs4-longnan-cmp.py`（3 个符号）

> 陇南：分页语义 + 列表答复 vs 详情答复 完整性对比。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 15 | 197 | — |
| `list_url` 函数 | 19 | 20 | — |
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/gs4-longnan-deep.py`（1 个符号）

> 陇南深探：列表 JSON 结构 + 详情页结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/gs4-probe.py`（4 个符号）

> 甘肃 4 源实测探针（worker-gansu）。只做只读探测，不改任何东西。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `show` 函数 | 15 | 75 | — |
| `probe_baiyin` 函数 | 21 | 2 | — |
| `probe_longnan` 函数 | 36 | 2 | — |
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/gz-xjgs.py`（2 个符号）

> 探贵州厅「信件公示」（/hdjl/tzxx/xjgs/）：列表形态、是否含答复、翻页方式。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 22 | 197 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/haiyun-spread-probe.py`（1 个符号）

> 探其他省是否也部署了吉林同款「海云/信箱开放接口」平台。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/handover-inventory.py`（1 个符号）

> 交接盘点：注册适配器清单 + 各来源条数 + 关键产物路径，输出给交接文档用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 13 | 1131 | — |

### `tools/gov-qa/recon/heb-adapters-probe.py`（4 个符号）

> 河北两条线 · 适配器落地前实测探针（general-purpose-1, 2026-10-08）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 28 | 197 | — |
| `probe_szj` 函数 | 32 | 2 | — |
| `probe_czt` 函数 | 76 | 2 | — |
| `main` 函数 | 130 | 1131 | — |

### `tools/gov-qa/recon/heb-adapters-selftest.py`（6 个符号）

> 自测：直接 import adapters.heb_szj / heb_czt 调 harvest()（不登记 __init__.py）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fetcher` 类 | 24 | 29 | — |
| `__init__` 函数 | 25 | 135 | — |
| `__call__` 函数 | 28 | 12 | — |
| `post` 函数 | 31 | 506 | — |
| `_safe` 函数 | 35 | 11 | — |
| `main` 函数 | 43 | 1131 | — |

### `tools/gov-qa/recon/heb-hi-probe.py`（2 个符号）

> 河北 + 海南 问答平台侦察（阶段一）：门户可达性 + 互动栏目发现。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `save` 函数 | 31 | 57 | — |
| `main` 函数 | 35 | 1131 | — |

### `tools/gov-qa/recon/heb-probe2.py`（1 个符号）

> 河北 阶段二：探信访来信查询 + 12345 SPA。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/heb-probe3.py`（1 个符号）

> 河北 阶段三：抓 JS 找接口路径。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/heb-probe4.py`（1 个符号）

> 河北 阶段四：探省直部门 + 市级门户的公开问答/留言选登。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/heb-probe5.py`（1 个符号）

> 河北 阶段五：深挖 沧州互动平台 / 省市场监管留言 / 省财政厅互动。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/heb-probe6.py`（1 个符号）

> 河北 阶段六：扫省直部门 /hdjl/qzxx/ 同款群众信箱。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/hi-probe2.py`（1 个符号）

> 海南 阶段二：抓问答候选栏目 + 业务知识库明细，判断是否 Q&A。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/hi-probe3.py`（1 个符号）

> 海南 阶段三：实测 /u/search/ajaxlist 政策问答接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/hi-probe4.py`（1 个符号）

> 海南 阶段四：抓政策问答明细页，确认答复全文与依据。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/hunan-verify.py`（2 个符号）

> 湖南统一互动平台（hd.hunan.gov.cn）验证：deptId + 答复覆盖率 + 状态分布。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `mail_list` 函数 | 34 | 7 | — |
| `main` 函数 | 43 | 1131 | — |

### `tools/gov-qa/recon/igi-chunked-harvest.py`（6 个符号）

> 按 siteId 分片、逐片落盘的 IGI 采集驱动。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fetcher` 类 | 47 | 29 | 与 harvest.py 的 _Fetcher 同协议（可调用 = GET，另有 .post）。 |
| `__init__` 函数 | 50 | 135 | — |
| `__call__` 函数 | 53 | 12 | — |
| `post` 函数 | 56 | 506 | — |
| `load_done` 函数 | 60 | 2 | — |
| `main` 函数 | 71 | 1131 | — |

### `tools/gov-qa/recon/igi-chunked.py`（10 个符号）

> IGI 多 siteId **分片增量**采集驱动（2026-10-09 新增，为山西 `sx-igi` 写）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fetcher` 类 | 52 | 29 | 与 harvest.py 的 _Fetcher 同协议（可调用 = GET，另有 .post）。 |
| `__init__` 函数 | 55 | 135 | — |
| `__call__` 函数 | 58 | 12 | — |
| `post` 函数 | 61 | 506 | — |
| `main` 函数 | 65 | 1131 | — |
| `_abs_pages` 函数 | 231 | 2 | 该 siteId 的**绝对页数上界**。 |
| `_page_windows` 函数 | 243 | 2 | 把 `1..abs_pages` 切成页窗口。 |
| `_load_progress` 函数 | 256 | 2 | 读跨轮页进度。 |
| `_save_progress` 函数 | 268 | 2 | 先写临时文件再 replace（避免被杀时留下半截 JSON 让下轮全丢进度）。 |
| `_load_done` 函数 | 276 | 6 | — |

### `tools/gov-qa/recon/igi-city-probe.py`（2 个符号）

> 城市门户 IGI **可采性 + id 重叠** 只读探针（2026-10-09 第 7 轮新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_existing` 函数 | 53 | 2 | — |
| `main` 函数 | 65 | 1131 | — |

### `tools/gov-qa/recon/igi-dig-2.py`（2 个符号）

> IGI 深挖第 2 轮：贵州市场监管 / 自然资源 的信箱参数不在首页（首页的 siteId/appId

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_params` 函数 | 35 | 7 | — |
| `main` 函数 | 42 | 1131 | — |

### `tools/gov-qa/recon/igi-dig.py`（3 个符号）

> IGI 深挖：对「指纹已中但 n=0 / 参数不足」的站点，从**信箱页 + 页面 JS** 里找真实参数。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_params` 函数 | 45 | 7 | — |
| `try_api` 函数 | 52 | 4 | — |
| `main` 函数 | 72 | 1131 | — |

### `tools/gov-qa/recon/igi-geo-sample.py`（1 个符号）

> IGI 城市门户 **地域真伪**抽样（只读，不落盘语料）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 41 | 1131 | — |

### `tools/gov-qa/recon/igi-hunt.py`（3 个符号）

> IGI 厅局自动搜寻：抓站点 → 抠 siteId/appId/groupId → **直接调接口验证**是否可用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `scan_js` 函数 | 56 | 2 | 抓指纹页链出的同域 .js（至多 3 个），把其中的 IGI 参数并入。 |
| `try_api` 函数 | 84 | 4 | 对该参数组合试各个候选 base，返回第一个 200 且含 datas 的结果。 |
| `main` 函数 | 104 | 1131 | — |

### `tools/gov-qa/recon/igi-other-depts.py`（1 个符号）

> 探吉林/贵州**其他厅局**是否也用 IGI 平台（若是，县级覆盖可成片扩）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/igi-portal-sweep.py`（1 个符号）

> 省 / 省会门户 IGI 平台**横向普查**（2026-10-09 新增）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 107 | 1131 | — |

### `tools/gov-qa/recon/igi-siteid-scan.py`（2 个符号）

> IGI `siteId` 全域枚举（含 appId 过滤语义）——2026-10-09 新增。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `probe` 函数 | 68 | 301 | — |
| `main` 函数 | 84 | 1131 | — |

### `tools/gov-qa/recon/igi-spread-scan.py`（1 个符号）

> 扫可达省份的厅局站是否也用 IGI 平台（指纹：openGovmsgbox / /IGI/ / listGovmsgboxs）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/jl-ajax-full.py`（1 个符号）

> 打印吉林 ajax 脚本全文（5KB，小），找 contextPath/siteId/appId 的真实取值。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/jl-api-call.py`（1 个符号）

> 调吉林真实接口（haiyun.jl.gov.cn/IGI/nbhd/openGovmsgbox.do），看字段与规模。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/jl-groupid-roster.py`（2 个符号）

> IGI 吉林：扫 groupId 出一张「厅局花名册」（groupId → 厅局名 + 信件总数）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `url` 函数 | 46 | 1553 | — |
| `main` 函数 | 54 | 1131 | — |

### `tools/gov-qa/recon/jl-lyxd-api-call.py`（1 个符号）

> 调吉林厅「留言选登」开放接口，看返回格式与字段。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/jl-lyxd-api.py`（2 个符号）

> 取吉林留言选登列表页与它的 ajax 脚本，找出数据接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 21 | 197 | — |
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/jl-lyxd.py`（2 个符号）

> 找吉林厅「留言选登」的入口与列表形态（WAS5 通道也可达，两条路都查）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 22 | 197 | — |
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/jl-nx-probe.py`（2 个符号）

> 探吉林与宁夏两家厅局站的互动栏目可用性。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 30 | 197 | — |
| `main` 函数 | 35 | 1131 | — |

### `tools/gov-qa/recon/jx-dept-probe.py`（3 个符号）

> 江西数融站群 —— 省直部门站点（webSiteCode）× 候选栏目（channelCode）探测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load_depts` 函数 | 37 | 4 | — |
| `query` 函数 | 46 | 621 | — |
| `main` 函数 | 63 | 1131 | — |

### `tools/gov-qa/recon/jx-dept-sample.py`（2 个符号）

> 江西省直部门站点命中栏目 —— **结构核验**（2026-10-09）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `page` 函数 | 49 | 1275 | — |
| `main` 函数 | 59 | 1131 | — |

### `tools/gov-qa/recon/jx-hygz-diag.py`（3 个符号）

> 江西 hygz 丢弃原因 + zxft 栏目结构（2026-10-09）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fetch_page` 函数 | 31 | 23 | — |
| `why` 函数 | 40 | 238 | 复算 jx_zf._one 的每一步，返回 (原因, 详情)。 |
| `main` 函数 | 74 | 1131 | — |

### `tools/gov-qa/recon/jx-hygz-probe.py`（2 个符号）

> 江西数融互动 —— hygz 解析缺口 + 其它 channelCode/webSiteCode 探测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `query` 函数 | 38 | 621 | — |
| `main` 函数 | 54 | 1131 | — |

### `tools/gov-qa/recon/jx-mailbox-probe.py`（4 个符号）

> 江西数融站群 —— 信箱接口 `/api/mail/list` 打通探测（2026-10-09）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load_depts` 函数 | 46 | 4 | — |
| `get_form` 函数 | 55 | 2 | — |
| `try_list` 函数 | 71 | 2 | — |
| `main` 函数 | 100 | 1131 | — |

### `tools/gov-qa/recon/label-accuracy.py`（5 个符号）

> 标签真实准确率 —— spec 004 的 US3（FR-014 / SC-007）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_label` 函数 | 54 | 10 | — |
| `_source` 函数 | 65 | 2 | — |
| `cmd_sample` 函数 | 69 | 2 | 分层抽样：按 (标签, 标签来源) 分层，保证每层都有样本。 |
| `cmd_score` 函数 | 119 | 2 | 读人工核对结果，算真实准确率。 |
| `main` 函数 | 179 | 1131 | — |

### `tools/gov-qa/recon/label-classify.py`（10 个符号）

> 内容分类器 v2 —— 服务 GOAL.md 的 M3（把内容的标签分好）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `normalize_label` 函数 | 73 | 3 | — |
| `raw_label` 函数 | 85 | 3 | — |
| `read_all` 函数 | 96 | 4 | — |
| `doc_text` 函数 | 108 | 3 | 只用 question —— answer 是政府生成的，对「提问类型」信号弱且会引噪声。 |
| `_jieba_cut` 函数 | 113 | 2 | jieba 分词（**必须是模块级函数**）。 |
| `build_model` 函数 | 124 | 4 | 返回 (vectorizer, clf, X_texts, y) —— 用全部已标注数据训练。 |
| `do_validate` 函数 | 161 | 2 | — |
| `load_or_train` 函数 | 199 | 2 | 返回已拟合的 pipeline。 |
| `do_apply` 函数 | 230 | 2 | — |
| `main` 函数 | 300 | 1131 | — |

### `tools/gov-qa/recon/label-coverage.py`（3 个符号）

> 标签覆盖率体检 + 闸门 —— 服务 GOAL.md 的 M3（把内容的标签分好）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `read_all` 函数 | 49 | 4 | — |
| `msg_type` 函数 | 61 | 49 | — |
| `main` 函数 | 72 | 1131 | — |

### `tools/gov-qa/recon/liuyan-band-read.py`（1 个符号）

> 把 fid 分层扫描结果写成可读清单（供人工核对层级归属）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 12 | 1131 | — |

### `tools/gov-qa/recon/liuyan-chunk-map.py`（1 个符号）

> 从 app.js 的 webpack chunk 映射里取「地方领导页」懒加载 chunk 的真实文件名。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 14 | 1131 | — |

### `tools/gov-qa/recon/liuyan-city-band-scan.py`（1 个符号）

> 稀疏探 fid 800~4000：找「地级市」版块的编号区间。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/liuyan-cursor-probe.py`（1 个符号）

> 人民网留言板 · 全站流翻页行为探测（带退避重试）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/liuyan-fid-band-scan.py`（1 个符号）

> 稀疏扫描 fid 601~735：识别第二层（市级/直辖市辖区）版块分布。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/liuyan-fid-dense-scan.py`（2 个符号）

> 留言板 fid **密集**扫描 —— 枚举全国所有版块（省/市/县）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `probe` 函数 | 64 | 301 | 探一个 fid。 |
| `main` 函数 | 98 | 1131 | — |

### `tools/gov-qa/recon/liuyan-fid-inventory.py`（1 个符号）

> 汇总已采留言板数据里出现过的全部版块（fid + 归属 + 承办单位），看编号分层结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 15 | 1131 | — |

### `tools/gov-qa/recon/liuyan-fid-map-build.py`（1 个符号）

> 把多路 fid 密集扫描的结果合并成**全国版块地图**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/liuyan-js-fetch.py`（1 个符号）

> 人民网领导留言板 · JS 包下载与签名算法挖掘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `tools/gov-qa/recon/liuyan-js-fetch2.py`（1 个符号）

> 人民网领导留言板 · 签名算法挖掘（第二轮：全量 JS 引用，不只 <script src>）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/liuyan-province-fid-map.py`（2 个符号）

> 补全省级版块 fid 扫描（556~600），产出「省 → 书记/省长 fid」映射表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fetch_one` 函数 | 27 | 2 | — |
| `main` 函数 | 43 | 1131 | — |

### `tools/gov-qa/recon/liuyan-province-fid-scan.py`（1 个符号）

> 验证「省级版块 fid 连续编号」假设：试 fid=541..550，看返回哪个省。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/liuyan-province-fid.py`（1 个符号）

> 找「地方领导」页并抠出各省 fid（若能按省 fid 采，df 就从随机采样变定向覆盖）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 22 | 1131 | — |

### `tools/gov-qa/recon/liuyan-province-fids-build.py`（1 个符号）

> 把「省级版块 fid 映射」补全到 31 个省：已扫描命中的标 confirmed，其余按规律标 inferred。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/liuyan-province-filter-probe.py`（1 个符号）

> 试 df 列表是否支持「按省过滤」（能的话，一个省的地市数据可成片取）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 30 | 1131 | — |

### `tools/gov-qa/recon/liuyan-substation-probe.py`（1 个符号）

> 试 /v1/forum/substation —— 拿地方分站（省/市）清单与 fid。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/liuyan-substation-probe2.py`（1 个符号）

> 试 `/v1/forum/substation` 带参数：能否拿到某省下的地市/区县版块清单。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `tools/gov-qa/recon/ln-lsxfw-raw.py`（2 个符号）

> 看辽宁「历史咨询服务」列表页结构：条目链接/内联内容/翻页方式。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 20 | 197 | — |
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/mem-detail-inspect.py`（1 个符号）

> 看应急管理部明细页的结构：答复正文在哪个容器里，好修 mem 适配器的抽取。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/mem-structure-locate.py`（2 个符号）

> 从已存的 mem 明细页 HTML 里定位「咨询/回复」正文区（修适配器抽取用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `strip_scripts` 函数 | 11 | 2 | — |
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/mem-verify-fix.py`（1 个符号）

> 核对修好后的 mem 抽取质量（不写盘，直接打印）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 15 | 1131 | — |

### `tools/gov-qa/recon/migrate-mohurd-q.py`（3 个符号）

> 迁移：修复 nat-mohurd 的 230 条 `question` 为空。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_key` 函数 | 42 | 6 | 匹配键：**不含 question**（那正是要修的字段）。 |
| `_new_id` 函数 | 49 | 5 | 与 adapter 一致的新 id 算法（含 question）。 |
| `main` 函数 | 59 | 1131 | — |

### `tools/gov-qa/recon/missing-cities.py`（1 个符号）

> 看「哪些地级市还没有来源」—— 这才是最大的覆盖缺口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/mw-summary.py`（1 个符号）

> 按省汇总 `recon/city-middleware.json` 的中间件归类 —— 挑下一批要打的市。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/nat-cnipa-probe.py`（2 个符号）

> 侦察：国家知识产权局 jact 各 sysid 的「已答问题」列表与明细（worker-national 自用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `txt` 函数 | 26 | 964 | — |
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/nat-smoke.py`（5 个符号）

> 抽验脚本（worker-national 自用）：直接调用 adapters.nat_* 的 harvest，打印前几条。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `F` 类 | 26 | 200 | — |
| `__init__` 函数 | 27 | 135 | — |
| `__call__` 函数 | 30 | 12 | — |
| `post` 函数 | 33 | 506 | — |
| `main` 函数 | 37 | 1131 | — |

### `tools/gov-qa/recon/other-province-hdjlpt-probe.py`（1 个符号）

> 测其他省份的厅局域名下是否也存在广东同款 `/hdjlpt` 平台。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 42 | 1131 | — |

### `tools/gov-qa/recon/probe-ah-wuhu.py`（3 个符号）

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 21 | 6333 | — |
| `dump` 函数 | 32 | 51 | — |
| `show_home` 函数 | 57 | 3 | — |

### `tools/gov-qa/recon/probe-city-api2.py`（2 个符号）

> 探针：实测三市的**候选接口**，看哪个真能出数据（GOAL.md #6：判死前必须实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_head` 函数 | 40 | 3 | — |
| `main` 函数 | 44 | 1131 | — |

### `tools/gov-qa/recon/probe-city-hd-api.py`（3 个符号）

> 探针（通用）：给一批「互动栏目 URL」，dump 出**可能的列表接口**。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_t` 函数 | 44 | 119 | — |
| `dump_one` 函数 | 48 | 2 | — |
| `main` 函数 | 93 | 1131 | — |

### `tools/gov-qa/recon/probe-city-interact.py`（1 个符号）

> 探针：三市「互动/咨询」栏目的**真实列表结构** —— 找可复用的中间件。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 61 | 1131 | — |

### `tools/gov-qa/recon/probe-city-middleware.py`（5 个符号）

> 把「已知域名的地级市门户」**按中间件归类** —— 为「一个适配器覆盖一片」做准备。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 84 | 144 | — |
| `classify` 函数 | 88 | 45 | — |
| `find_hd_link` 函数 | 96 | 2 | 从页面里抽「互动类」栏目入口（绝对化）。 |
| `work` 函数 | 112 | 121 | — |
| `main` 函数 | 145 | 1131 | — |

### `tools/gov-qa/recon/probe-endpoint.py`（3 个符号）

> 通用端点测试器：GET/POST 一个 URL，dump 状态码 + Content-Type + 响应头 600 字符。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 44 | 172 | — |
| `one` 函数 | 48 | 57 | — |
| `main` 函数 | 91 | 1131 | — |

### `tools/gov-qa/recon/probe-gansu-waf.py`（1 个符号）

> 探针：绕过甘肃 WAF（HTTP 412）+ 探西藏政务服务网。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 50 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-12345.py`（2 个符号）

> 探针：广东 5 市「真正的公开留言栏目」实测（2026-10-10 第 8 轮）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_probe` 函数 | 74 | 11 | — |
| `main` 函数 | 111 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-city-hdjlpt.py`（4 个符号）

> 实测：广东各**地级市**的 hdjlpt 能不能采（GOAL.md #6：判死/判活前必须实测）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 50 | 144 | — |
| `_token` 函数 | 54 | 7 | — |
| `probe_city` 函数 | 62 | 2 | — |
| `main` 函数 | 111 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-hd-403.py`（2 个符号）

> 探针：广东「带 hdjlpt 指纹但落地页 403」的市 —— 403 是 WAF 还是真的没部署？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_hd_links` 函数 | 58 | 2 | 从首页 HTML 里挑出「疑似互动栏目」的链接。 |
| `main` 函数 | 81 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-hd-entries.py`（2 个符号）

> 探针：中山/河源 hdjlpt 模块在但 `pubList` total=0 —— 找它们**真正的**公开留言栏目。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_links` 函数 | 57 | 2 | 返回 (href, 锚文本)。 |
| `main` 函数 | 80 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-hd-params.py`（3 个符号）

> 探针：中山/河源 pubList 返 `errcode:0` 但 `total:0` —— 是参数错还是真没数据？

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_token` 函数 | 72 | 7 | — |
| `_try` 函数 | 86 | 2 | — |
| `main` 函数 | 128 | 1131 | — |

### `tools/gov-qa/recon/probe-gd-hd-publist.py`（3 个符号）

> 探针：对「hdjlpt 端点存在（pubList 返 405）但落地页非 200」的市，

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_token_from` 函数 | 53 | 2 | — |
| `_post_list` 函数 | 66 | 13 | — |
| `main` 函数 | 111 | 1131 | — |

### `tools/gov-qa/recon/probe-igi-cities.py`（1 个符号）

> 探针：找「洛阳 / 芜湖 / 宜昌」的 IGI siteId。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 49 | 1131 | — |

### `tools/gov-qa/recon/probe-igi-context.py`（2 个符号）

> 探针：把「洛阳 / 芜湖 / 宜昌」页面里 **IGI 的真实上下文** dump 出来。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_ctx` 函数 | 61 | 2 | — |
| `main` 函数 | 67 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-api.py`（1 个符号）

> 探针：拉萨来信选登 API `/lasa-comment/email/findDetailByQuery.do`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 29 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-api2.py`（1 个符号）

> 提取拉萨 `hd_mailbox.js` 里 `mailList` 函数的完整 URL。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 15 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-api3.py`（1 个符号）

> 找 `ipUrl` 的定义（在 head.js 或页面内联），并**直接试调**拉萨来信列表 API。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-js.py`（1 个符号）

> 找拉萨来信选登页面的 API 调用方式（`.do` 路径 404，需看真实调用）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 17 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-js2.py`（1 个符号）

> 查拉萨 `hd_mailbox.js` —— 确认有无公开的来信列表接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/probe-lasa-lxxd.py`（1 个符号）

> 探针：拉萨「来信选登」列表结构（`/lasa/lxxd/hd_mailbox.shtml`）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 25 | 1131 | — |

### `tools/gov-qa/recon/probe-longxun-cities.py`（5 个符号）

> 探针：龙讯科技 CMS 的市 —— 提取 label 参数并**实测**列表接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_num` 函数 | 59 | 13 | — |
| `_strv` 函数 | 64 | 3 | — |
| `_text` 函数 | 69 | 144 | — |
| `probe` 函数 | 73 | 301 | — |
| `main` 函数 | 143 | 1131 | — |

### `tools/gov-qa/recon/probe-missing-cities.py`（1 个符号）

> 探针：抽查几个「缺来源」的地级市门户，看它们用不用同一套中间件。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 63 | 1131 | — |

### `tools/gov-qa/recon/probe-mohurd-q.py`（2 个符号）

> 探针：找出 nat-mohurd 列表页里 `Q_RE` 匹配失败的条目，看实际 HTML 结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fetch_page` 函数 | 28 | 23 | — |
| `main` 函数 | 41 | 1131 | — |

### `tools/gov-qa/recon/probe-npc.py`（1 个符号）

> 探人大系统的「征求意见」栏目 —— M4 用。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 31 | 1131 | — |

### `tools/gov-qa/recon/probe-npc2.py`（1 个符号）

> 探人大「征求意见」栏目的列表结构 —— 判断能否批量采。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/probe-post-list.py`（2 个符号）

> 探针：广东「`content/post_<id>.html` 静态列表」这一族怎么翻页、怎么取正文。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_t` 函数 | 67 | 119 | — |
| `main` 函数 | 71 | 1131 | — |

### `tools/gov-qa/recon/probe-province-city-links.py`（3 个符号）

> 探针：从**省政府门户**里挖出「地市门户」的链接 —— 建 city→域名 映射。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_text` 函数 | 68 | 144 | — |
| `_host` 函数 | 72 | 4 | — |
| `main` 函数 | 77 | 1131 | — |

### `tools/gov-qa/recon/probe-provinces.py`（4 个符号）

> 省级政府站批量侦察（第一步）：WAS5 指纹 + 问答栏目链接 + channelid 挖掘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_get` 函数 | 104 | 16 | GET 一个 URL。 |
| `_status` 函数 | 113 | 6 | — |
| `mine_channelid` 函数 | 117 | 2 | — |
| `main` 函数 | 126 | 1131 | — |

### `tools/gov-qa/recon/probe-thin-provinces.py`（1 个符号）

> 探针：西藏 / 甘肃 省政府门户的政民互动入口（补 `none` 单元）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/probe-tianshui-page.py`（1 个符号）

> 探针：天水聚合列表页里「总页数」到底怎么表达。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 27 | 1131 | — |

### `tools/gov-qa/recon/probe-tianshui.py`（1 个符号）

> 探针：甘肃·天水「政民互动」栏目结构（补甘肃的 `none` 单元）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 35 | 1131 | — |

### `tools/gov-qa/recon/probe-tianshui2.py`（2 个符号）

> 探针：天水「政民互动」详情页结构 + 分页（WAS5 leadermail）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_plain` 函数 | 23 | 4 | — |
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/probe-tianshui3.py`（1 个符号）

> 看天水详情页的**原始 HTML**，找正文在哪（可能 JS 加载）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/probe-ts-lasa.py`（1 个符号）

> 探针：天水 / 拉萨 门户的政民互动栏目（补甘肃、西藏两个 `none` 单元）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 32 | 1131 | — |

### `tools/gov-qa/recon/probe-xizang-xf.py`（1 个符号）

> 探针：西藏信访平台 `xzxf.xizang.gov.cn` 是否有公开的来信选登。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 22 | 1131 | — |

### `tools/gov-qa/recon/prov-platform-probe.py`（3 个符号）

> 侦察：省级门户「一片式」互动平台探测（湖南 hd.hunan.gov.cn 模式能否复制）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `fetch` 函数 | 89 | 1027 | — |
| `scan` 函数 | 98 | 180 | — |
| `main` 函数 | 113 | 1131 | — |

### `tools/gov-qa/recon/province-platform-hunt-dig.py`（5 个符号）

> 24 省互动平台重探 —— 阶段二：对指定互动栏目页深挖接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_get` 函数 | 57 | 16 | — |
| `fp_of` 函数 | 64 | 3 | — |
| `links_of` 函数 | 75 | 2 | — |
| `dig` 函数 | 87 | 42 | — |
| `main` 函数 | 131 | 1131 | — |

### `tools/gov-qa/recon/province-platform-hunt-raw.py`（1 个符号）

> 抓单页原始 HTML 并打印含指定关键词的 JS 片段（用于看清 IGI 列表函数真实参数）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/province-platform-hunt-test.py`（2 个符号）

> 24 省互动平台重探 —— 阶段三：实测候选接口（通/不通都要落证据）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `show` 函数 | 21 | 75 | — |
| `main` 函数 | 28 | 1131 | — |

### `tools/gov-qa/recon/province-platform-hunt.py`（6 个符号）

> 24 省（无适配器省份）问答/互动平台系统性重探 —— 阶段一：门户可达性 + 互动栏目发现。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_get` 函数 | 88 | 16 | — |
| `_st` 函数 | 95 | 11 | — |
| `_text` 函数 | 99 | 144 | — |
| `find_links` 函数 | 103 | 3 | — |
| `fingerprint` 函数 | 118 | 11 | — |
| `main` 函数 | 127 | 1131 | — |

### `tools/gov-qa/recon/reg-gansu.py`（1 个符号）

> 登记 `gs-tianshui`（并行 agent 已写模块但未注册）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 21 | 1131 | — |

### `tools/gov-qa/recon/reg-lasa.py`（1 个符号）

> 把 xz-lasa 登记进 adapters/__init__.py 的 ADAPTERS 字典。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 19 | 1131 | — |

### `tools/gov-qa/recon/reg-rd-adapters.py`（1 个符号）

> 把 rd-* 4 个人大适配器登记进 adapters/__init__.py 的 ADAPTERS 字典。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 24 | 1131 | — |

### `tools/gov-qa/recon/repair-empty-questions.py`（3 个符号）

> 修复「问题为空但答复有内容」的记录 —— 按 `url` 重取明细，回填 `question`。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_clean` 函数 | 65 | 172 | — |
| `extract` 函数 | 70 | 18 | 从明细页里抠问题正文。 |
| `main` 函数 | 80 | 1131 | — |

### `tools/gov-qa/recon/sc-detail-debug.py`（2 个符号）

> 调试四川知识库明细页：把清洗后文本的前后段落打出来，看解析标记到底长什么样。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `clean` 函数 | 22 | 197 | — |
| `main` 函数 | 26 | 1131 | — |

### `tools/gov-qa/recon/sc-knowledge-detail.py`（1 个符号）

> 看四川知识库明细页结构与列表翻页方式（决定适配器写法）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 20 | 1131 | — |

### `tools/gov-qa/recon/sc-mailbox-probe.py`（1 个符号）

> 看四川厅「领导信箱」与「回应关切」列表的规模与明细形态。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 23 | 1131 | — |

### `tools/gov-qa/recon/sc-two-lists.py`（1 个符号）

> 看四川省生态环境厅「回应关切」与「互动知识库」两个列表页的形态。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 28 | 1131 | — |

### `tools/gov-qa/recon/sc-wenzheng-probe.py`（1 个符号）

> 探「问政四川」（wz.sc.gov.cn）—— 四川省统一问政平台，看有没有公开问答列表与接口。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 33 | 1131 | — |

### `tools/gov-qa/recon/sd-city-hunt.py`（2 个符号）

> 山东地市级门户「政民互动」入口侦察（前 5 市：济南/青岛/淄博/枣庄/东营）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `links` 函数 | 35 | 142 | — |
| `main` 函数 | 46 | 1131 | — |

### `tools/gov-qa/recon/sd-city-probe2.py`（3 个符号）

> 山东地市 第二轮：jact 端点实测 + 青岛/淄博/枣庄互动页抓取。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 24 | 6333 | — |
| `post` 函数 | 34 | 506 | — |
| `main` 函数 | 45 | 1131 | — |

### `tools/gov-qa/recon/sd-city-probe3.py`（2 个符号）

> 山东地市 第三轮：枣庄 IGI 实测 + 淄博 jact 实测 + 济南/青岛 接口挖掘。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `jact_list` 函数 | 23 | 3 | — |
| `main` 函数 | 39 | 1131 | — |

### `tools/gov-qa/recon/sd-city-probe4.py`（2 个符号）

> 山东地市 第四轮：淄博/济南 jact 真实接口 + 青岛 mailboxpage/qdgov-web。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `grab` 函数 | 21 | 22 | — |
| `main` 函数 | 39 | 1131 | — |

### `tools/gov-qa/recon/sd-city2-hunt.py`（2 个符号）

> 山东地市 6–16 市入口侦察：抓门户首页（http+https）→ 抠互动链接 + 中间件指纹。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `links` 函数 | 39 | 142 | — |
| `main` 函数 | 50 | 1131 | — |

### `tools/gov-qa/recon/sd-city2-probe.py`（2 个符号）

> 山东地市 6–16 第二轮：jact 族实测 + 烟台 jpaas-jact + 其余市互动页深挖。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `jact_total` 函数 | 47 | 2 | — |
| `main` 函数 | 66 | 1131 | — |

### `tools/gov-qa/recon/sd-city3-probe.py`（2 个符号）

> 山东剩余 6 市（潍坊/泰安/临沂/德州/聊城/菏泽）第三轮：验证服务端渲染列表 + 详情答复字段。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `find_items` 函数 | 38 | 2 | 返回 (绝对链接, 锚文本) 列表。 |
| `main` 函数 | 50 | 1131 | — |

### `tools/gov-qa/recon/sh-zj-probe.py`（2 个符号）

> 上海/浙江问答平台侦察 · 第一轮可达性 + 形态探测。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `probe` 函数 | 53 | 301 | — |
| `main` 函数 | 70 | 1131 | — |

### `tools/gov-qa/recon/sh-zj-verify.py`（6 个符号）

> 上海/浙江适配器实测：用 harvest.py 同款 _Fetcher 跑 harvest(limit=3) 并打印记录。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `load` 函数 | 20 | 103 | — |
| `_Fetcher` 类 | 27 | 29 | — |
| `__init__` 函数 | 28 | 135 | — |
| `__call__` 函数 | 31 | 12 | — |
| `post` 函数 | 34 | 506 | — |
| `main` 函数 | 38 | 1131 | — |

### `tools/gov-qa/recon/verify-idempotent.py`（11 个符号）

> 幂等验证器（spec 004 T028 / SC-002、SC-003）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Isolated` 类 | 46 | 14 | 把 `poll.DATA_DIR` 指到临时目录 —— **与 `tests/test_poll.py` 同法**。 |
| `__init__` 函数 | 56 | 135 | — |
| `__enter__` 函数 | 60 | 9 | — |
| `__exit__` 函数 | 66 | 9 | — |
| `ReplayAdapter` 类 | 70 | 3 | 把**已落盘的记录**当"上游返回"重放。 |
| `__init__` 函数 | 82 | 135 | — |
| `harvest` 函数 | 86 | 501 | — |
| `records_for` 函数 | 91 | 2 | 读某个通道已落盘的记录（按文件名前缀匹配）。 |
| `verify_one` 函数 | 111 | 2 | 验一个通道：跑两遍 `poll_one`，第二遍必须 0 新增。 |
| `_count_dups` 函数 | 142 | 2 | 落盘文件里重复 (source, id) 的条数。 |
| `main` 函数 | 162 | 1131 | — |

### `tools/gov-qa/recon/waf-igi-probe.py`（3 个符号）

> WAF 放行探测：已知被 412/403 拦 / 未通的省份，逐一试 /IGI/ 与其它中间件接口路径。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `probe` 函数 | 67 | 301 | — |
| `main` 函数 | 85 | 1131 | — |
| `deep_probe` 函数 | 146 | 2 | 对 IGI 放行的站点枚举 siteId，记录哪些有数据。 |

### `tools/gov-qa/recon/waf-igi-sites.py`（3 个符号）

> 阶段二：对「IGI 返回 statusCode=200 空列表（siteId=1 无数据）」的站点，

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `total` 函数 | 40 | 1316 | — |
| `enumerate_sites` 函数 | 57 | 2 | — |
| `main` 函数 | 69 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-adapt-test.py`（5 个符号）

> 直测新适配器（不改 __init__.py）：gx_mailbox / sd_12345 / qh_wsxf。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_Fetcher` 类 | 20 | 29 | — |
| `__init__` 函数 | 21 | 135 | — |
| `__call__` 函数 | 24 | 12 | — |
| `post` 函数 | 27 | 506 | — |
| `run` 函数 | 31 | 282 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-dig.py`（2 个符号）

> 深挖鲁/桂/青/新/藏 候选互动栏目页，存原始 HTML 并扫描问答/接口线索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 39 | 6333 | — |
| `main` 函数 | 45 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-fetch.py`（4 个符号）

> 抓鲁/桂/青门户首页 + 新疆/西藏信访页原始 HTML，打印互动/问答相关链接与 JS 片段。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 26 | 6333 | — |
| `save` 函数 | 32 | 57 | — |
| `scan_links` 函数 | 45 | 6 | — |
| `main` 函数 | 57 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-js.py`（2 个符号）

> 抓 JS 与明细样本：青海/广西/新疆/山东。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `get` 函数 | 30 | 6333 | — |
| `main` 函数 | 36 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-probe.py`（3 个符号）

> 鲁/桂/青 三省可达性重探 + 新疆/西藏信访页抓取（证据：recon/xj-xz-sd-gx-qh-hunt.txt）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `dns` 函数 | 23 | 4 | — |
| `probe` 函数 | 30 | 301 | — |
| `main` 函数 | 45 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-test.py`（2 个符号）

> 接口实测：广西 IGI、新疆信访端点、青海静态分页。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `show` 函数 | 16 | 75 | — |
| `main` 函数 | 22 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-test2.py`（1 个符号）

> 实测：山东 12345 API、山东反馈回应列表、青海分页变体。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/xj-xz-sd-gx-qh-test3.py`（1 个符号）

> 最终验证：山东 dataproxy 分页+明细、广西 IGI 明细、青海页区分、西藏替代路径。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/recon/zj-dept-probe.py`（4 个符号）

> 浙江省 · 厅局真实域名 + 互动平台指纹批量侦察（广东打法的复制）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_W` 类 | 35 | 8 | — |
| `__init__` 函数 | 36 | 135 | — |
| `post` 函数 | 39 | 506 | — |
| `main` 函数 | 43 | 1131 | — |

### `tools/gov-qa/recon/zj-dir-inspect.py`（1 个符号）

> 看浙江名录页（col/col1544854）里部门链接的真实形态。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 18 | 1131 | — |

### `tools/gov-qa/regions.py`（2 个符号）

> 中国地级行政区 → 所属省级行政区的映射表。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `province_of_city` 函数 | 117 | 3 | 由市名反查所属省。 |
| `total_cities` 函数 | 148 | 9 | **本表收录数**（334，含省直辖县级市济源市）。 |

### `tools/gov-qa/run-real-recall.py`（1 个符号）

> 真实提问召回测试（D1）—— 用**官方答复点名的真实问题**考我们的检索。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `main` 函数 | 50 | 1131 | — |

### `tools/gov-qa/state.py`（17 个符号）

> 水位（Watermark）—— 增量轮询的核心数据结构。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `Watermark` 类 | 43 | 15 | 单通道的水位。 |
| `__init__` 函数 | 49 | 135 | — |
| `to_dict` 函数 | 64 | 7 | — |
| `from_dict` 函数 | 76 | 3 | — |
| `__repr__` 函数 | 87 | 3 | — |
| `WatermarkStore` 类 | 95 | 23 | 水位存储。 |
| `__init__` 函数 | 102 | 135 | — |
| `_load` 函数 | 108 | 125 | — |
| `save` 函数 | 127 | 57 | — |
| `get` 函数 | 132 | 6333 | — |
| `needs_full` 函数 | 135 | 4 | 该通道是否必须全量采（无水位 / 文件损坏）。 |
| `__contains__` 函数 | 139 | 1 | — |
| `__len__` 函数 | 142 | 3 | — |
| `ensure` 函数 | 147 | 22 | 取或建（不落盘）。 |
| `mark_success` 函数 | 160 | 9 | **采集成功后**前移水位（FR-003）。 |
| `mark_failure` 函数 | 171 | 5 | 采集失败：**只累加计数，不动 value**（FR-003）。 |
| `_trim` 函数 | 179 | 3 | `idset` 型做 LRU 裁剪（上限 `IDSET_MAX`）。 |

### `tools/gov-qa/tests/test_ay_zmhd.py`（7 个符号）

> 测试：`ay-zmhd`（安阳市·政民互动）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_systems_cover_the_three_observed_types` 函数 | 25 | 1 | 实测只有 3 个非空 `systemType`（0/1/2），第 4 个是空的。 |
| `test_clean_keeps_chinese_angle_brackets` 函数 | 35 | 4 | **反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。 |
| `test_real_treats_literal_null_as_absent` 函数 | 41 | 7 | — |
| `test_norm_dt_converts_the_slash_format` 函数 | 48 | 1 | 站点给 `2026/10/9 10:38:35`，本模块统一 `2026-10-09 10:38:35`。 |
| `test_page_size_is_bounded` 函数 | 61 | 2 | **站点约束**：一页最多取多少条（防止把站点拖垮 / 自己内存爆）。 |
| `test_pause_is_not_aggressive` 函数 | 70 | 1 | **站点约束**：请求间隔不得为 0（本模块在商丘因 1.0s 触发过全站 403）。 |

### `tools/gov-qa/tests/test_bz_hdjl.py`（8 个符号）

> 测试：`bz-hdjl`（亳州市·信件选登）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_parse_list_dedupes_and_keeps_order` 函数 | 57 | 3 | — |
| `test_parse_total_reads_pagination_attrs` 函数 | 65 | 2 | 站点自报 `pagecount=14 total=163`。 |
| `test_fields_pairs_tit_with_item` 函数 | 74 | 1 | **核心判据**：`u-tit`（字段名）必须与**紧邻的** `u-item`/`u-desc`（值）配对。 |
| `test_parse_detail_extracts_question_and_answer` 函数 | 89 | 2 | 必须抽出**信件内容**与**回复内容** —— 这是"可采"的判据。 |
| `test_pagination_starts_at_one` 函数 | 102 | 1 | 分页从 1 起（与池州同族，与焦作相反）。 |
| `test_clean_strips_comments_and_keeps_brackets` 函数 | 108 | 3 | — |
| `test_real_treats_literal_null_as_absent` 函数 | 115 | 7 | — |

### `tools/gov-qa/tests/test_channel.py`（8 个符号）

> 测试：通道层（T013）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_channels_cover_all_adapters` 函数 | 16 | 1 | **关键**：通道清单必须覆盖 `adapters.ADAPTERS` 里的每一个。 |
| `test_every_channel_has_valid_watermark_type` 函数 | 29 | 1 | — |
| `test_unknown_adapter_load_failure_still_registered` 函数 | 35 | 1 | 加载失败的 adapter 也要登记 —— 否则零数据检测会漏掉它。 |
| `test_infer_region_province` 函数 | 41 | 1 | — |
| `test_infer_region_national` 函数 | 47 | 1 | — |
| `test_infer_region_explicit_level_wins` 函数 | 52 | 1 | — |
| `test_group_by_level` 函数 | 57 | 1 | — |
| `test_provinces_list_is_complete` 函数 | 65 | 1 | 31 个省级行政区 + 港澳台 = 34。 |

### `tools/gov-qa/tests/test_channel_table.py`（6 个符号）

> 测试：`SITE-REGISTRY.md` 的**通道台账表**（spec 004 T052 / M1）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_gen` 函数 | 25 | 3 | — |
| `_table_rows` 函数 | 33 | 3 | — |
| `test_registry_has_a_generated_channel_table` 函数 | 40 | 1 | 表必须存在且**覆盖全部通道**。 |
| `test_channel_table_registers_watermark_type` 函数 | 51 | 1 | **M1 判据**：每一行都要登记水位类型（增量靠什么）。 |
| `test_channel_table_is_up_to_date` 函数 | 65 | 1 | **结构判据**：表必须与脚本重算的结果一致（防手改后不更新）。 |
| `test_generator_preserves_everything_outside_the_block` 函数 | 83 | 1 | **关键反向判据**：生成器**只动受管区块**，区块外一个字不改。 |

### `tools/gov-qa/tests/test_child_source_attribution.py`（5 个符号）

> 测试：子 source 的数据必须被归集到父通道（spec 005 T602）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_child_source_counts_into_parent` 函数 | 27 | 1 | `sx-igi-24` 的条数必须计入 `sx-igi`（**24 不是通道**，只是数据里的 source）。 |
| `test_exact_key_still_works` 函数 | 34 | 1 | **反向用例**：没有子 source 时不得多算。 |
| `test_longest_prefix_wins_no_double_count` 函数 | 40 | 1 | **关键**：`gx-igi` 与 `gx-igi-293` **都是通道**时，子 source 只能算一次。 |
| `test_unrelated_prefix_is_not_swallowed` 函数 | 55 | 1 | **反向用例**：`mee` 不得吞掉 `meeting-notes` 这种无关键。 |
| `test_real_corpus_has_no_unattributed_source` 函数 | 61 | 1 | **端到端**：真实语料里不应有「有数据但没有任何通道能归集它」的 source。 |

### `tools/gov-qa/tests/test_city_caliber.py`（4 个符号）

> 测试：地级行政区的**口径**必须只有一套说法（spec 005 T603）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_total_cities_is_334_and_documented_as_such` 函数 | 28 | 1 | `total_cities()` 是**本表收录数**，实测 334。 |
| `test_strict_prefecture_count_is_333` 函数 | 33 | 1 | **严格意义的地级行政区**是 333（不含省直辖县级市济源市）。 |
| `test_the_difference_is_exactly_one_province_direct_city` 函数 | 38 | 1 | 两个数的差**恰好 1**，且那一个是济源市 —— 把差异钉成可执行的证据。 |
| `test_no_module_doc_claims_333_as_the_table_size` 函数 | 50 | 1 | **结构判据**：`regions.py` 模块文档不得再把"本表有 333 项"当结论说。 |

### `tools/gov-qa/tests/test_coverage.py`（21 个符号）

> 测试：覆盖销号表（US2）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_province_list_is_31` 函数 | 21 | 1 | **SC-004**：31 个省级行政区，一个不能少。 |
| `test_all_provinces_get_a_row` 函数 | 26 | 1 | **SC-004**：每个省级行政区都有销号行 —— 哪怕一条数据都没有。 |
| `test_province_without_channel_is_none` 函数 | 36 | 1 | 无来源的省 ⇒ status=none（**硬缺口**，不是深度问题）。 |
| `test_gap_calculation` 函数 | 45 | 1 | **SC-005**：缺口 = max(0, 达标线 - 落盘量)，且 落盘量 + 缺口 ≥ 达标线。 |
| `test_meets_threshold_is_ok` 函数 | 56 | 1 | — |
| `test_threshold_is_adjustable` 函数 | 65 | 1 | 达标线可调 ⇒ 所有 gap 同步变化（FR-033）。 |
| `test_ratio_to_median_is_same_level` 函数 | 83 | 1 | **R4**：比值必须**同级比同级**，不跨级。 |
| `test_uncovered_lists_missing_channels` 函数 | 104 | 1 | **SC-006**：能列出该地区**尚未建源的渠道**（不只是"数据少"）。 |
| `test_uncovered_exhausted_is_explicit` 函数 | 115 | 1 | **关键**：渠道全部覆盖时返回 `已穷尽`，**不留空** ——。 |
| `test_city_extraction` 函数 | 132 | 1 | 市级通道的名字不含省名 ⇒ 必须能独立提出市名（**实测踩过的坑**）。 |
| `test_municipality_not_counted_as_city` 函数 | 139 | 1 | 北京/天津/上海/重庆 是**省级**，不能算成地级市。 |
| `test_province_extraction` 函数 | 145 | 1 | — |
| `test_infer_region_city_level` 函数 | 151 | 1 | — |
| `test_norm_city` 函数 | 162 | 1 | 市名归一化：补「市」，但**自治州/地区/盟不得被补成市**。 |
| `test_known_cities_covers_334` 函数 | 174 | 1 | 334 个地级行政区的名单要能读到（`count_by_city` 用它过滤占位值）。 |
| `test_data_records_drive_city_status` 函数 | 182 | 1 | ★ 核心修复：省级平台通道带 `extra.city` ⇒ 该市**不得**被判 `none`。 |
| `test_data_records_thin_when_below_threshold` 函数 | 199 | 1 | 数据口径同样走达标线判定 —— 低于线是 `thin`，不是 `ok`。 |
| `test_merge_city_data_creates_units_for_data_only_cities` 函数 | 208 | 1 | 只靠省级通道覆盖的市要被**补建**为市级单元，且 `total_records` 仍为 0。 |
| `test_merge_does_not_inflate_province_total` 函数 | 223 | 1 | ★ 防重复计数：补建市级单元**不得**改变省级 `total_incl_cities`。 |
| `test_count_by_city_filters_placeholder_and_falls_back` 函数 | 242 | 1 | 数据口径归属：优先 `extra.city`。 |
| `test_count_by_city_extra_city_wins_over_channel` 函数 | 265 | 1 | `extra.city` 优先于通道兜底 —— 否则省级通道会把记录全算到一个市上。 |

### `tools/gov-qa/tests/test_coverage_report_consistency.py`（9 个符号）

> 测试：`coverage-report.py` 的两个入口必须给出**一致的**缺口结论。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 34 | 125 | — |
| `test_shared_helper_exists_and_is_the_only_source` 函数 | 41 | 1 | **结构判据**：`--missing-cities` 分支不得再自己算一遍。 |
| `_run` 函数 | 61 | 73 | — |
| `_quiet_run` 函数 | 74 | 6 | — |
| `_missing_run` 函数 | 80 | 3 | — |
| `test_quiet_reports_missing_from_334` 函数 | 86 | 1 | `--quiet` 必须打出 `CITY_MISSING_FROM_334` —— 否则读者只看到 `CITY_NONE=0`。 |
| `test_two_entrypoints_agree_on_missing_count` 函数 | 92 | 1 | **核心判据**：两个入口报出的缺失数必须**相等**。 |
| `test_both_entrypoints_return_the_same_exit_code` 函数 | 102 | 1 | **核心判据**：退出码也必须一致（实测原来是 0 vs 1）。 |
| `test_missing_count_matches_an_independent_recount` 函数 | 108 | 1 | **关键补强（独立复核发现 6）**：一致性不等于正确性。 |

### `tools/gov-qa/tests/test_cz_hdjl.py`（7 个符号）

> 测试：`cz-hdjl`（池州市·留言选登）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_parse_list_dedupes_and_keeps_order` 函数 | 56 | 3 | 列表页：**去重**且保序（实测同一详情链接可能出现两次）。 |
| `test_parse_total_reads_pagination_attrs` 函数 | 66 | 2 | **站点自报**：从 `<pagination … pagecount="13" total="128">` 取。 |
| `test_parse_detail_extracts_question_and_answer` 函数 | 75 | 2 | 详情页必须抽出**留言正文**与**回复正文** —— 这是"可采"的判据。 |
| `test_pagination_starts_at_one_not_zero` 函数 | 87 | 1 | **分页形态不能照抄别市**（2026-10-10 实测对照）。 |
| `test_clean_strips_comments_and_keeps_brackets` 函数 | 102 | 3 | — |
| `test_real_treats_literal_null_as_absent` 函数 | 109 | 7 | — |

### `tools/gov-qa/tests/test_dup_detection.py`（8 个符号）

> 测试：重复 id 判据必须**跨文件**也生效（spec 005 T203 之二）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_audit` 函数 | 23 | 3 | — |
| `_rec` 函数 | 30 | 72 | — |
| `_write` 函数 | 34 | 36 | — |
| `_data_dir` 函数 | 39 | 5 | `show_gate()` 读的是 `<ROOT>/data/*.jsonl` —— 所以语料要放 `data/` 子目录。 |
| `test_duplicate_id_across_two_files_is_detected` 函数 | 50 | 1 | **跨文件**的同 `(source,id)` 必须被数出来。 |
| `test_no_duplicate_when_ids_differ` 函数 | 73 | 1 | **反向用例**：id 不同不得误报（判据不能恒真）。 |
| `test_source_implementations_use_global_counting` 函数 | 90 | 1 | **结构判据**：`show_gate` 与 `show_dups` 都不得把 per-file 状态放回文件循环内。 |
| `test_health_py_has_the_same_fix` 函数 | 122 | 1 | **兄弟文件判据**：`health.py` 的重复 id 判据也必须是**全局**口径。 |

### `tools/gov-qa/tests/test_gate_quality.py`（38 个符号）

> 测试：数据质量闸门（spec 005 T102/T111）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_python` 函数 | 29 | 2 | 解释器路径。 |
| `_load_gate` 函数 | 43 | 2 | 按路径加载 `recon/gate-quality.py`（文件名带连字符，不能直接 import）。 |
| `_write` 函数 | 55 | 36 | — |
| `_rec` 函数 | 60 | 72 | — |
| `_Data` 类 | 69 | 22 | 把 `gate-quality.DATA` 指到临时目录。 |
| `__init__` 函数 | 72 | 135 | — |
| `__enter__` 函数 | 76 | 9 | — |
| `__exit__` 函数 | 81 | 9 | — |
| `test_empty_answer_is_detected` 函数 | 88 | 1 | **答复为空必须被数出来** —— `xz-lasa` 那种「条数正常、内容是空」。 |
| `test_single_source_with_all_empty_answers_fails` 函数 | 97 | 1 | **单个源大面积为空要指名道姓** —— 只报全库平均会被大源稀释掉。 |
| `test_content_duplicate_with_different_ids_is_detected` 函数 | 112 | 1 | **id 不同但内容相同必须被数出来** —— 旧闸门只比 id，这一项完全看不见。 |
| `test_whitespace_differences_do_not_hide_duplicates` 函数 | 125 | 1 | 归一化必须吃掉空白 —— 否则「加个换行」就能绕过重复检测。 |
| `test_distinct_content_is_not_flagged` 函数 | 136 | 1 | **反向用例**：不同内容不得被误判成重复（判据不能恒真）。 |
| `test_time_inversion_is_detected` 函数 | 146 | 1 | **答复早于提问必须被数出来** —— `ln-8890` 实测 7,807 条如此。 |
| `test_date_only_answered_at_same_day_is_not_inverted` 函数 | 157 | 1 | **同一天、`answered_at` 只精确到天 ⇒ 不算倒置**（2026-10-10 第 3 次修）。 |
| `test_date_only_answered_at_across_days_IS_inverted` 函数 | 174 | 1 | **反向用例**：`answered_at` 是纯日期但**跨天更早** ⇒ 仍须判倒置。 |
| `test_full_timestamp_same_day_hours_earlier_is_inverted` 函数 | 185 | 1 | **反向用例**：两个都是完整时间戳、答复早几小时 ⇒ 仍判倒置。 |
| `test_midnight_answered_at_is_treated_as_day_precision` 函数 | 196 | 1 | `answered_at` 恰为 **00:00:00** 也按"只到天"处理（2026-10-10 第 4 次修）。 |
| `test_midnight_answered_at_across_days_IS_inverted` 函数 | 212 | 1 | **反向用例**：午夜整点但**跨天更早** ⇒ 仍判倒置。 |
| `test_non_midnight_same_day_hours_earlier_is_inverted` 函数 | 224 | 1 | **反向用例**：同一天但答复**不是**午夜（真实时刻）⇒ 仍判倒置。 |
| `test_missing_dates_are_not_counted_as_inverted` 函数 | 233 | 1 | 缺字段**不算**倒置 —— 否则「没数据」会被误报成「数据错」。 |
| `test_java_date_string_is_not_a_false_inversion` 函数 | 246 | 1 | **`Thu Oct 19` vs `Fri Oct 20` 不是倒置** —— 字母序 `Fri` < `Thu`。 |
| `test_minute_truncation_is_not_a_false_inversion` 函数 | 259 | 1 | `15:02:00` vs `15:02` 是同一分钟，**不算倒置**（容忍 60 秒）。 |
| `test_chinese_date_string_is_parsed_correctly` 函数 | 268 | 1 | `2026年09月7日` 早于 `2026年09月09日` —— 裸比字符串会判反。 |
| `test_real_inversion_in_chinese_format_is_caught` 函数 | 276 | 1 | **反向用例**：中文格式下真倒置必须被抓住（解析不能把判据变恒假）。 |
| `test_unparsable_dates_are_counted_separately` 函数 | 284 | 1 | 两个字段都有值但解析不了 ⇒ 计入 `unparsed_time`，**不当倒置也不当没事**。 |
| `test_parse_time_handles_all_three_observed_formats` 函数 | 293 | 1 | 三种实测格式都要能解析（ISO / 中文 / Java toString）。 |
| `test_label_coverage_counts_only_clean_key` 函数 | 306 | 1 | 覆盖率只认 `msg_type_norm`（干净 9 分类），**不认原始脏 `msg_type`**。 |
| `test_ratchet_compares_rate_not_absolute_count` 函数 | 328 | 1 | **棘轮比的是率不是条数** —— 并行采集会持续加数据。 |
| `test_ratchet_flags_a_real_rate_regression` 函数 | 345 | 1 | **反向用例**：率真的变坏必须报红（棘轮不能恒真）。 |
| `test_ratchet_is_silent_without_baseline` 函数 | 357 | 1 | 没有基线时不判红（否则第一跑就红，没人会去建基线）。 |
| `test_save_baseline_key_mapping_does_not_crash` 函数 | 363 | 1 | `--update-baseline` 不得因键名不一致而崩（实测踩过）。 |
| `test_ratchet_skips_sources_still_being_harvested` 函数 | 380 | 1 | **采集中**的来源不判恶化（样本还在长，不下结论）。 |
| `test_ratchet_still_flags_a_settled_source` 函数 | 408 | 1 | **反向用例**：样本量**没怎么变**（已采完）的来源，重复率变坏 ⇒ 必须报红。 |
| `test_save_baseline_refuses_regression` 函数 | 426 | 1 | **反向用例**：**已有来源**的重复率变坏时必须**拒绝**写基线。 |
| `test_save_baseline_allows_a_new_high_dup_source` 函数 | 447 | 1 | **新来源**即使重复率高也**不算恶化**（它没有基线可比）。 |
| `test_quiet_output_is_pure_ascii` 函数 | 471 | 1 | `--quiet` 是**给闸门读的**，必须纯 ASCII（GBK 控制台会崩）。 |
| `test_quiet_output_has_the_expected_keys` 函数 | 517 | 1 | **补强**：`--quiet` 必须打出闸门要解析的那些键。 |

### `tools/gov-qa/tests/test_gbk_safety.py`（2 个符号）

> 测试：`audit-coverage.py` 的**每个**子命令都不得因 GBK 控制台崩掉。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_every_subcommand_survives_gbk_console` 函数 | 30 | 1 | **每个子命令**都必须 rc 0 或 1（1 = 它自己的"发现问题"退出码），**不得是 2**。 |
| `test_no_adapter_prints_emoji_through_bare_print` 函数 | 48 | 1 | **结构判据**：适配器里的 `print(...)` 不得直接含 emoji/箭头。 |

### `tools/gov-qa/tests/test_health.py`（9 个符号）

> 测试：字段体检 + 健康结论（US3 / US4）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_field_audit_detects_both_empty` 函数 | 21 | 1 | **SC-008**：能检出「问题与答复同时为空」。 |
| `test_field_audit_detects_q_empty_a_ok` 函数 | 41 | 1 | 能单独列出「问题为空但答复有内容」（nat-mohurd 的实际问题）。 |
| `test_field_audit_exit_code_on_both_empty` 函数 | 59 | 1 | 有问题与答复同时为空 ⇒ 退出码 1（可被闸门用）。 |
| `test_label_accuracy_refuses_without_human_check` 函数 | 76 | 1 | **宪法 III**：未人工核对时必须输出「明确未做」，**不给数字**。 |
| `test_label_accuracy_scores_after_human_check` 函数 | 111 | 1 | 人工填完后能算准确率，并按标签来源分层（**关键：模型标的那部分**）。 |
| `test_health_reports_usable` 函数 | 139 | 1 | **SC-011**：可用时一句话结论 + VERDICT=usable。 |
| `test_health_detects_all_three_faults` 函数 | 165 | 3 | **SC-009**：一次运行检出全部故障（重复 id + 覆盖不足）。 |
| `test_health_quiet_is_pure_ascii` 函数 | 190 | 1 | **R5**：机器可读输出必须纯 ASCII。 |
| `test_health_trace_appends` 函数 | 208 | 1 | **FR-019**：能追加执行轨迹。 |

### `tools/gov-qa/tests/test_health_checks.py`（10 个符号）

> 测试：`health.py` 的四项判据必须被**各自的**测试钉住。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_health` 函数 | 24 | 6 | — |
| `_isolate` 函数 | 31 | 6 | — |
| `_rec` 函数 | 36 | 72 | — |
| `_write` 函数 | 44 | 36 | — |
| `_checks` 函数 | 49 | 1 | 跑 collect() 并返回 {判据名: 是否通过}。 |
| `test_empty_adapter_alone_makes_unusable` 函数 | 57 | 1 | **只有「零数据适配器」这一项坏** ⇒ 必须判不可用。 |
| `test_duplicate_ids_alone_makes_unusable` 函数 | 75 | 1 | **只有「重复 id」这一项坏** ⇒ 必须判不可用。 |
| `test_floor_breach_alone_makes_unusable` 函数 | 89 | 1 | **只有「数据总数低于地板」这一项坏** ⇒ 必须判不可用。 |
| `test_low_label_coverage_alone_makes_unusable` 函数 | 103 | 1 | **只有「标签覆盖率不足」这一项坏** ⇒ 必须判不可用。 |
| `test_all_good_is_usable` 函数 | 118 | 1 | **反向用例**：四项全好必须判可用（判据不能恒假）。 |

### `tools/gov-qa/tests/test_igi_null.py`（5 个符号）

> 测试：IGI 引擎不得把字面 `"null"` 当正文（spec 005 T205）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load_igi` 函数 | 24 | 5 | — |
| `test_real_treats_literal_null_as_absent` 函数 | 33 | 7 | `_real("null")` 必须是空串 —— 否则 `or` 不会回落到真标题。 |
| `test_real_keeps_genuine_content` 函数 | 44 | 1 | **反向用例**：真内容不得被吃掉（判据不能恒空）。 |
| `test_nullish_falls_through_to_title` 函数 | 51 | 1 | 复现原始 bug 形态：`_real(...) or _real(...) or title` 必须回落到标题。 |
| `test_old_clean_would_have_failed` 函数 | 59 | 1 | **反证**：用旧的 `clean(...) or ...` 写法确实会拿到 `'null'`。 |

### `tools/gov-qa/tests/test_jz_zxhf.py`（6 个符号）

> 测试：`jz-zxhf`（焦作市·咨询回复）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_parse_list_dedupes_and_keeps_order` 函数 | 42 | 3 | 列表页：**去重**且保序（实测页面里同一个详情链接会出现两次）。 |
| `test_parse_detail_extracts_answer_and_meta` 函数 | 51 | 1 | 详情页必须抽出**答复正文**与日期/部门 —— 这是"可采"的判据。 |
| `test_clean_keeps_chinese_angle_brackets` 函数 | 62 | 4 | **反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。 |
| `test_pagination_suffix_matches_the_js` 函数 | 68 | 1 | **分页判据**：从 `paging.js` 的 `goto` 抄到的规则是**页号从 0 起**。 |
| `test_page_count_is_items_not_pages` 函数 | 83 | 1 | **站点约束**：`pagecount=34` 是**总条数**不是总页数。 |

### `tools/gov-qa/tests/test_kf_hdjl.py`（6 个符号）

> 测试：`kf-hdjl`（开封市·信件公开）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 18 | 125 | — |
| `test_site_id_param_is_qd_id_not_site_id` 函数 | 26 | 1 | **核心判据**：列表的 `siteId` 参数传的是 **`qdId`**。 |
| `test_clean_strips_html_comments_and_keeps_brackets` 函数 | 41 | 1 | `content` / `replyContent` 都是 HTML ⇒ 必须剥标签，且两个都不能少。 |
| `test_dept_of_reads_metadata_list` 函数 | 54 | 1 | `metadataList` 是 **JSON 字符串**，要从里面取「答复单位」。 |
| `test_real_treats_literal_null_as_absent` 函数 | 65 | 7 | — |
| `test_page_size_and_pause_are_reasonable` 函数 | 72 | 2 | 站点约束：分页大小与请求间隔都要克制。 |

### `tools/gov-qa/tests/test_output_filename.py`（4 个符号）

> 测试：**落盘文件名必须过滤非法字符**（2026-10-10 实测的真缺陷）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `test_poll_data_path_for_strips_illegal_chars` 函数 | 29 | 1 | `poll.data_path_for` 必须过滤非法字符（这是既有行为，钉住不许退）。 |
| `test_harvest_module_actually_sanitises` 函数 | 39 | 1 | **核心判据（真的读 harvest.py 的源码来判）**。 |
| `test_harvest_and_poll_agree_on_the_filename` 函数 | 59 | 1 | **判据**：`harvest.py` 的过滤规则与 `poll.py` 必须**逐字符一致**。 |
| `test_no_adapter_name_breaks_the_path` 函数 | 76 | 1 | **全量判据**：任何适配器的 `SITE\['name'\]` 都不得在落盘路径里出问题。 |

### `tools/gov-qa/tests/test_poll.py`（25 个符号）

> 测试：增量轮询（T023–T027 + 本轮增量验证）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `FakeAdapter` 类 | 31 | 22 | 可控假 adapter。 |
| `__init__` 函数 | 39 | 135 | — |
| `harvest` 函数 | 48 | 501 | — |
| `_ch` 函数 | 68 | 21 | — |
| `_rec` 函数 | 73 | 72 | — |
| `_Isolated` 类 | 78 | 14 | 把 `poll.DATA_DIR` 指到临时目录的上下文管理器。 |
| `__init__` 函数 | 84 | 135 | — |
| `__enter__` 函数 | 88 | 9 | — |
| `__exit__` 函数 | 94 | 9 | — |
| `test_idempotent_second_run_adds_zero` 函数 | 101 | 3 | **SC-002**：连续两次轮询，第二次必须新增 0 条。 |
| `test_idempotent_no_duplicate_ids_on_disk` 函数 | 118 | 1 | SC-002 落盘侧：连续两次后文件里不得有重复 id。 |
| `test_incremental_stops_at_known_page` 函数 | 141 | 1 | **核心验证**：翻到「本页全部已见过」就停，不把后面的页也翻完。 |
| `test_incremental_restores_page_env` 函数 | 173 | 1 | `GOVQA_PAGE_FROM` 用完必须恢复 —— 不能污染调用方环境。 |
| `test_failure_isolated` 函数 | 187 | 1 | **SC-012**：一个通道失败，不影响其他通道，且不抛异常。 |
| `test_failure_does_not_advance_watermark` 函数 | 204 | 1 | **FR-003**：失败路径绝不能前移水位。 |
| `test_broken_watermark_degrades_not_crash` 函数 | 222 | 1 | **FR-006**：水位损坏时不崩溃，且标记退化。 |
| `test_lock_blocks_second_runner` 函数 | 239 | 1 | **R7**：抢不到锁时抛 LockBusy（调用方映射成退出码 3）。 |
| `test_lock_released_after_use` 函数 | 253 | 1 | — |
| `test_atomic_append_writes_immediately` 函数 | 264 | 1 | **T016/R3**：每条写入立即落盘（不是「跑完才写」）。 |
| `test_ascii_kv_is_pure_ascii` 函数 | 279 | 2 | **T004/R5**：机器可读输出必须纯 ASCII（4 层 bug 的教训）。 |
| `test_page_watermark_is_actually_read` 函数 | 293 | 1 | **T303**：`page` 型水位必须被**读** —— 不是只写不读的摆设。 |
| `test_idset_watermark_still_starts_at_page_one` 函数 | 315 | 1 | **反向用例**：`idset` 型不靠页码（靠 `seen` 去重）⇒ 仍从第 1 页起。 |
| `test_next_value_page_records_real_page_not_increment` 函数 | 334 | 1 | **T303**：`page` 型水位记的是**本轮实际翻到的页号**，不是"每批 +1"。 |
| `test_existing_ids_reads_sub_source_records` 函数 | 341 | 1 | **子源**记录也必须被 `existing_ids` 读到（2026-10-10 修的真 bug）。 |
| `test_poll_one_is_idempotent_for_sub_source_records` 函数 | 372 | 1 | **SC-002 的端到端判据（子源形态）**：第二次必须 0 新增。 |

### `tools/gov-qa/tests/test_sq_szxx.py`（6 个符号）

> 测试：`sq-szxx`（商丘市·市长信箱）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 18 | 125 | — |
| `test_parse_list_extracts_all_fields` 函数 | 64 | 1 | 列表页必须抽出 id / 标题 / 部门 / 状态 / 日期 / 点击数。 |
| `test_parse_detail_extracts_answer` 函数 | 78 | 2 | 详情页必须抽出**答复正文** —— 这是"可采"的判据。 |
| `test_clean_keeps_chinese_angle_brackets` 函数 | 88 | 4 | **反向用例**：`《出生证明》` 这类中文尖括号不得被当 HTML 标签吃掉。 |
| `test_real_treats_literal_null_as_absent` 函数 | 98 | 7 | `null` 一律当"没有"（IGI 那次的教训，这里统一用 `_real`）。 |
| `test_site_rate_limit_is_respected` 函数 | 106 | 1 | **站点约束判据**：`PAUSE` 必须 > 1 秒。 |

### `tools/gov-qa/tests/test_state.py`（10 个符号）

> 测试：水位层（T012）。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_store` 函数 | 21 | 20 | — |
| `test_serialize_roundtrip` 函数 | 25 | 1 | — |
| `test_invalid_type_rejected` 函数 | 33 | 1 | — |
| `test_success_moves_watermark` 函数 | 41 | 1 | — |
| `test_failure_does_not_move_watermark` 函数 | 51 | 1 | **FR-003 的核心**：失败绝不能前移水位。 |
| `test_broken_file_degrades_safely` 函数 | 65 | 1 | **FR-006**：水位文件损坏时不得抛异常，且要标记需要全量。 |
| `test_missing_file_is_not_broken` 函数 | 78 | 1 | 文件不存在 ≠ 损坏（首次运行是正常状态）。 |
| `test_idset_lru_cap` 函数 | 86 | 1 | idset 型必须有上限，否则 JSON 无限膨胀。 |
| `test_type_change_invalidates_value` 函数 | 99 | 1 | adapter 改造导致水位类型变化 ⇒ 值作废，退回全量（宁可慢不可漏）。 |
| `test_persistence` 函数 | 109 | 1 | — |

### `tools/gov-qa/tests/test_tl_hdjl.py`（8 个符号）

> 测试：`tl-hdjl`（铜陵市·信件公开）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_api_prefix_has_no_u` 函数 | 25 | 1 | **核心判据**：铜陵的接口前缀是 `/api/mail/`（**不带 `u`**）。 |
| `test_uses_own_site_id_not_kf_qd_id` 函数 | 37 | 1 | 铜陵**没有 `qdId`**，列表 `siteId` 参数用 `useObj.siteId`。 |
| `test_dept_of_handles_python_style_single_quotes` 函数 | 49 | 1 | **实测的坑**：`metadataList` 的键值用**单引号**（Python 字面量风格），。 |
| `test_clean_strips_comments_and_keeps_brackets` 函数 | 63 | 3 | — |
| `test_clean_strips_site_side_stray_closing_tags` 函数 | 70 | 1 | **实测的坑**：站方原始 HTML 末尾带**孤立闭合标签**。 |
| `test_real_treats_literal_null_as_absent` 函数 | 91 | 7 | — |
| `test_page_size_and_pause_are_reasonable` 函数 | 98 | 2 | — |

### `tools/gov-qa/tests/test_zk_zxsq.py`（6 个符号）

> 测试：`zk-zxsq`（周口市·咨询受理）适配器的解析与站点约束。

| 符号 | 行 | 引用 | 职责 |
|---|---:|---:|---|
| `_load` 函数 | 17 | 125 | — |
| `test_token_regex_handles_value_before_id` 函数 | 39 | 1 | **核心判据**：`loadMailboxsDataToken` 的 `value` 在 `id` **之前**。 |
| `test_parse_detail_extracts_answer` 函数 | 51 | 2 | 详情页必须抽出**答复正文**与回复时间 —— 这是"可采"的判据。 |
| `test_clean_strips_html_comments` 函数 | 60 | 1 | **HTML 注释必须被剥掉**（2026-10-10 实测的真缺陷）。 |
| `test_clean_keeps_chinese_angle_brackets` 函数 | 73 | 4 | **反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。 |
| `test_page_size_is_bounded` 函数 | 79 | 2 | — |
