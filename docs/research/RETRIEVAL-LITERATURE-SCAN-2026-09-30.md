# 检索文献调研（2026-09-30）：我们这个问题在学界叫什么、已经做到哪一步

> **触发**：业主指示「总纲的事情你去论文网站和 RAG 相关论坛找找看有没有什么思路」。
> **范围**：只找**与本纲主线（大白话 53% 零重合 + 排不上来）同构**的工作，不做泛读。
> **方法**：`web_search` 定位 → `ar5iv` 取正文（`r.jina.ai` 被 401 限流，PDF 直取不支持）。
> ⚠ **本文件是"外部参考材料"，不是待办**；要不要采纳由业主定（沿用本仓对"新材料"的口径）。

---

## 一、先说最重要的：我们这个问题，学界有正式赛道

**TREC 2025 Tip-of-the-Tongue（话到嘴边想不起来）赛道**。
总览：[arXiv 2601.20671](https://arxiv.org/abs/2601.20671)（作者含 UNC / CMU / Jena）。

**它的任务定义与本纲主线的重合度**：

| TREC ToT 的说法 | 本纲的对应 |
|---|---|
| "re-finding an item for which the searcher **does not reliably recall an identifier**" | 用户说不出术语名 |
| "**language phenomena that simple keyword-matching algorithms are not equipped to handle**" | §1.2 那 53% 零重合 |
| "**Current IR systems are not well-suited to resolve ToT information needs**" | §1.2「按字找、按意思找都试过，6.8% / 5.8%」 |
| 用户靠社区问答（Reddit r/tipofmytongue 等）解决 | 我们的产品就是这个角色 |

⇒ **结论：这不是我们独有的难题，而是一个有两年赛道、有基准、有 9 组参赛的正式研究问题。**
⇒ **好处**：别人的失败和成功都能直接查，不必自己试错。

---

## 二、硬数字（TREC 2025 官方结果表）

任务：6,407,814 篇维基文章，622 条查询，输出 1000 条排序，官方指标 NDCG@1000。
查询构成：172 条真实社区（MS-ToT 电影）+ 150 条**真人诱导**（NIST）+ **300 条大模型合成**。

| 方案 | NDCG@1000 | NDCG@10 | Recall@1000 |
|---|---|---|---|
| **最佳（SRCB，含外部数据训练）** | **0.6824** | 0.6576 | 0.9051 |
| 次档（DS@GT，重排 500） | 0.4106 | 0.3831 | 0.6559 |
| webis（BM25+gpt-oss） | 0.3689 | 0.3078 | **0.7637** |
| **官方 BM25 基线** | **0.1700** | 0.1223 | 0.4855 |
| **官方稠密向量基线** | **🔴 0.0514** | 0.0189 | 0.2653 |

### 三条直接可用的读数

1. **🔴 纯向量（0.0514）比纯关键词（0.1700）差 3 倍。**
   ⇒ **与本库实测"按字找 6.8% / 按意思找 5.8%——无差别"同向**。
   ⇒ **"上向量就能解决"是错的**，这是第三方大样本的同一结论。
2. **最佳（0.6824）是基线（0.1700）的 4 倍** ⇒ **有路子，但不是"多接一条检索路"。**
3. **`webis` 那行是"排不上来"的活标本**：Recall@1000 **0.7637**（很高）但 NDCG@10 只 **0.3078**。
   ⇒ **找到得多、排不上来**——与本纲 P1「41.6% 在返回集里、只 4.5% 进前五」是同一种病。

### 一条与我们直觉相反的官方发现

> "The different performance metrics ... seem to be well correlated to each other,
> **except R@1000 which seemed to be less-correlated with other metrics**."

⇒ 官方结论：**召回（R@1000）与排序指标（NDCG/MRR）相关性较弱** ⇒ **提召回 ≠ 提排序，两者要分开治。**

---

## 三、那篇标题就是"我们两个阶段"的论文

**[Single-Turn LLM Reformulation Powered Multi-Stage Hybrid Re-Ranking for ToT Known-Item Retrieval](https://arxiv.org/abs/2602.10321)**
（Mukhopadhyay / Ghosh / Chatterjee，2026-02；代码 <https://github.com/debayan1405/TREC-TOT-2025>）

**它的两阶段 = 本纲的 P1（改写问题）+ P2（排序）。**

### 3.1 🔴 最重要的一条：**召回是硬天花板**

论文 §5.2.3 的标题就是 **"The Recall Ceiling Phenomenon"**：

> "This is a structural consequence of our **'Sparse-First Cascade'** design. The dense models were
> configured to re-rank the top-1000 candidates provided by BM25 rather than retrieving from the
> full corpus. Consequently, **the previous stage recall was mathematically capped by the sparse
> stage recall.**"

§5.1：

> "**The primary failure mode occurs at the first retrieval stage, where Recall@1000 drops by
> 20.67%.** Specifically, the BM25+KL configuration achieves a maximum Recall@1000 of **0.5225**
> using the original queries, compared to **0.6302** when operating on Mistral-rewritten queries.
> **This substantial loss of candidate coverage prevents downstream re-rankers from recovering
> relevant documents, since they are constrained to re-ranking only the top-1000 results produced
> by the initial retriever.**"

**⇒ 这两段就是我们那个问题的答案（也回答业主"提高召回率"那句）：**
* **召回是第一级的硬上限**，重排只能在给它的那堆里重排 ⇒ **召回不够，后面全白干**；
* 但**拉起召回的手段不是"多取一些"，是"改问题"**（改写让 Recall@1000 从 0.5225 回到 0.6302）；
* 且**越难的问题，改写捞回的召回越多**（难测集 +20.67%，容易开发集只 +1.7%）。

### 3.2 它的逐级增益（NDCG@10）

| 级 | 做法 | NDCG@10 |
|---|---|---|
| 1 | BM25（改写后的问题） | 基线 |
| 2 | ColBERTv2 + Contriever + E5-large-v2 三路 **RRF（k=60）** 融合 | 0.2338 |
| 3 | **Cross-Encoder（monoT5-large）** | **0.3110**（**单级最大跳跃，+33%**） |
| 4 | 72B 大模型 listwise 重排 | **0.3706**（再 +19%） |
| — | **合计** | **比稀疏基线 +113.21%**；**比"同一套管线用原问题" +33.88%** |

### 3.3 ✅ 四条可以直接借鉴的

1. **"混合输入池"（Hybrid Input Pooling）**——给交叉编码器喂**并集**而不是一路：
   > "Rather than re-ranking only the dense output, we constructed a union pool consisting of the
   > **top-100 candidates from the sparse BM25 stage and the top-100 candidates from the RRF** ...
   > This ensured that the Cross-Encoder had access to **both exact keyword matches and semantic matches**."
   ⇒ ⚠ **本库要核一件事**：我们那个重排器看到的是**一路的输出还是各路并集**？若是前者，**召回被那一路封死**。
2. **候选深度按 Recall@K 调，不按 NDCG 调**：
   > "Unlike standard approaches that optimize for nDCG, we **optimized for Recall@1000 again to ensure
   > the relevant document was retained for the downstream stages**."
   并给了**抗过拟合的聚合口径**：`S_K = μ(R@K) − α·σ(R@K)`，α=0.5（跨 split 稳定性惩罚）。
   ⇒ 附带一个省算力的做法：**"Virtual Tuning"**——先跑一次 top-5000，小 K 用切片模拟。
3. **RRF 常数 k=60 得到第三个独立来源确认**
   （本纲 §1.5 已记"与外部方案 Jev-Mem 完全相同，收敛不是抄"；这是第三处）。
   ⇒ 并且它验证了**集成优于任何单模型**："producing a final list (0.2338) that **outperformed
   even the best single model (E5)**, justifying the computational overhead of the ensemble."
4. **改写提示词的"严格接地"条款**（可直接抄的骨架）：
   > "**Strict grounding rule: Do NOT introduce any information, entities, attributes, or assumptions
   > that are not present in the input query.** Every token ... must be **traceable to the original
   > text** or to safe lexical transformations (e.g., synonyms). **No external knowledge.**
   > ... If unsure, **do not expand**."
   ⇒ 与本纲 P1「不再'生成翻译'，改成**从库自己的术语表里有界地选**」**是同一个思路**。

### 3.4 🔴 三条**不要抄**的（对我们有害）

1. **第 5 条准则"删掉否定与不确定"**——原话："Remove negative constraints or uncertainty unless crucial"。
   ⇒ ⚠ **我们的法规里"不得/严禁/不应"就是命门**（本纲金标 43/96 条属 `modality`）。
   **照抄会把"不应"改写没了**。⇒ **必须反向：模态词一个都不许动。**
2. **第 4 阶段的 72B 大模型重排靠"世界知识"**——原话："leveraging the model's **world knowledge** ... rescued hard cases"。
   ⇒ ⚠ **对我们的场景这是致命方向**：**答案必须来自那条原文，不许来自模型的常识。**
   我们那条"未核验不得承重"的语义正是挡这个的。⇒ **第 4 级不能照抄。**
3. **它删掉"否定约束"的同一条逻辑还体现在**：该文把"不确定表达"当噪声。
   我们的"大白话"里恰恰可能有**效力、适用条件**等关键限定。⇒ **删之前先判。**

### 3.5 🔴 它独立复现了**我们那次失败的同一个机制**

论文开头解释**为什么经典伪相关反馈（PRF）在这里失效**：

> "...where Pseudo-Relevance Feedback (PRF) based expansion methods are rendered ineffective,
> **due to poor first stage Recall and Ranking using the raw queries, resulting in expansion using
> the incorrect documents.**"

它的实测（BM25，dev3）：

| 问题版本 | nDCG@10 | Recall@1000 |
|---|---|---|
| 原始 | 0.3366 | 0.7705 |
| **RM3 + BM25**（经典 PRF） | **0.2704 ⬇变差** | **0.5093 ⬇** |
| Bo1 + BM25 | 0.3034 ⬇ | 0.7295 ⬇ |
| KL + BM25 | 0.3093 ⬇ | 0.7332 ⬇ |
| **大模型改写（Qwen）** | 0.3720 ⬆ | 0.7836 ⬆ |
| **大模型改写（Llama）** | **0.3889 ⬆** | 0.7836 ⬆ |

⇒ **三种经典扩展法全部把结果弄差**，原因就是"用错文档去扩展"。
⇒ **这就是本纲 P1 已实测的「先选文档再在文档内选术语」无效（前1 只 9.1%）的同一个机制。**
⇒ **我们那次失败不是我们做错了，是这条路本身在这种任务上就不成立**——现在有第三方大样本佐证。

### 3.6 一条对"选哪个向量模型"的提示

> "ColBERTv2 (0.1361) and Contriever (0.1458): These models **underperformed the sparse baseline**.
> This suggests a **'semantic drift'** ... retrieved documents that were topically related but factually incorrect."
> "**E5-Large (0.2253): The E5 model significantly outperformed its peers**, single-handedly driving the
> success of the dense stage. Its **strong instruction-following capabilities** likely aligned better
> with the structure of the rewritten queries."

⇒ ⚠ **同为稠密模型，差距 0.1361 vs 0.2253（1.65 倍）**，归因是**指令跟随能力**。
⇒ **对本库的含义**：P1 用的是「生产同款 `bge-small-zh-v1.5`、同样无查询指令前缀」，而本纲已实测
"查询加 bge 官方检索指令前缀：500 候选 47.3%→46.2%、全库 8.6%→8.4% ⇒ 无差别"。
⇒ **本库那次测的是"前缀"这一种形式**；这篇提示的是**换更强的指令跟随模型**（不是改前缀）可能有用。**未测。**

---

## 四、另外两条背景（不是方法，但影响判断）

1. **合成语料可用的实证依据**（ToT 总览）：
   > "The system performances on **MS-ToT queries and synthetic queries are fairly well correlated
   > (Kendall's Tau=0.847)**, while the performance on NIST queries was relatively less correlated
   > with that on MS-ToT queries (Tau=0.703) and synthetic queries (Tau=0.737). This finding
   > **supports the use of diverse query generation approaches, including synthetic query generation
   > and manual topic development**, for retrieval evaluation for ToT information needs."
   ⇒ **它的测试集近一半（300/622）是模型合成的问题**，且与真实社区问题排序一致（Tau 0.847）。
   ⇒ ✅ **对我们 §1.2 那 1,832 条合成说法是有利证据**（合成语料不是"自欺欺人"）。
   ⚠ **但也给了限度**：**真人诱导的那批与两者相关性都更低**（0.703/0.737）⇒ **合成不能替代真人**，
   这正是本纲 §1.4「真实提问记录：没有」那条的独立依据。
   ⚠ 它给了一套**可抄的真人诱导流程**（四阶段：Recognizability → Retrievability → Elicitation → Confirmation），
   见总览 §3.2 —— **建"真实提问"语料时可以照这个做，不必自己发明。**
2. **"Agentic Gap"警示**（BLUR 基准，转引自上述论文）：
   > "complex agent frameworks frequently **only slightly outperformed the base LLMs they wrapped**"
   且人 98% vs 最好系统 ≈56%。⇒ **加智能体层的收益可能远小于预期**（与本纲 P4 的取舍相关）。

---

## 五、明确**未核**的（不得当结论）

- **冠军方案 SRCB（0.6824）到底怎么做的——未读。**
  `trec.nist.gov/pubs/trec34/papers/SRCB.mllm.tot.pdf` PDF 取不了、`r.jina.ai` 被 401、
  Semantic Scholar 页无正文。**它与次档差 0.27（1.66 倍），这一篇最值得读。**
- **[Hedge Removal, Query Drift, and the Simulation Gap in ToT Retrieval](https://trec.nist.gov/pubs/trec34/papers/UAmsterdam.tot.pdf)（UvA）——未读。**
  标题里的 "Simulation Gap" 与本库"合成语料 vs 真实提问"直接相关。
- **[Yale NLP at TREC 2024 ToT](https://trec.nist.gov/pubs/trec33/papers/yalenlp.tot.pdf)**、
  **[IISERK@ToT 2024（查询重构+分层检索）](https://trec.nist.gov/pubs/trec33/papers/IISER-K.tot.pdf)** —— 未读。
- **[BLUR 基准](https://arxiv.org/abs/2504.05651)**（Wang et al.）—— 只从转引里看到数，**原文未读**。
- **以上全部是英文/多语言工作，有没有人做过中文——未查。**
- ⚠ **本文件全部是"读别人的结论"，我一次都没有在本库上复现它们。**
