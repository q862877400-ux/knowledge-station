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

---

## 六、第二轮：把 PDF 下到本机读（2026-09-30）

> 首轮 `r.jina.ai` 被 401 限流、`web_fetch` 不支持 PDF。
> **解法：用 `curl` 带浏览器 UA 下到本机，再用本机 `read_pdf` 读**（`trec.nist.gov` 可直连）。
> 下到本机：`SRCB.mllm.tot.pdf`（118,267 字节，冠军）、`UAmsterdam.tot.pdf`（256,212 字节）。

### 6.1 🏆 冠军 SRCB（NDCG@1000 = 0.6824）到底怎么做的

**管线**：稠密检索取 **top 2000** → 重排。主干 **Qwen3-Embedding 系列**。

**检索侧四招**：

1. **先把问题变成"线索清单"（cue list）**，用 DeepSeek-V3——
   > "transform each original query into a **refined list of cues** … removes redundant or noisy content,
   > highlights information that is most useful for retrieval, and **corrects typos and grammatical errors**.
   > **All modules take cue lists as input rather than raw queries.**"

   **提示词原文（Table 4，我读到图了）**关键几句：
   > "Your task is to **extract a list of cues** from the user's input. Cues are any meaningful pieces of
   > information that may help in identifying the intended entity."
   > 十类线索：外观/内容/特征、情节片段/场景/事件/引语、**感官细节**、**情绪或氛围**、
   > 经历场景（"小时候看的"/"在意大利旅行时"）、年代、语言/地区/文化、相关人物群体物、
   > **类比（"感觉像 X 和 Y 的混合"）**、其他任何细节。
   > **"Directly output the list, and do not attempt to guess the actual entity—just extract the cues."**

   ⇒ 🔴 **这跟 DS@GT 的改写是两种路子**：DS@GT 把问题压成**关键词检索式**；
   **SRCB 只抽线索、明确"不许猜实体"**。
   ⚠ **对本库的含义**：本纲 P1 走的是"**从库的术语表里选**"——那是"猜实体"那条路。
   SRCB 提示了一条**第三种可能：不选术语，只抽线索，让线索去撞**。**未测，登记。**

2. **用 Wikidata 过滤语料**：**640 万 → 约 50 万篇**（12.8 倍）。
   做法：算每个实体的 "instance of" 属性嵌入与 "Movie" 嵌入的余弦相似度，取最高者当领域相关分，低于阈值者滤掉。
   ⇒ ⚠ **这是"按域缩窄"，但缩的是【语料】不是【查询侧候选】，且离线做一次。**
   **与我此前否掉的"按领域缩窄术语候选"不是同一件事**（那个要一个前置分类器，已实测无效）。
   ⇒ 本库语料只有 **6,797 篇**，已经不大了；此招对我们的适用性**未判**。

3. **微调稠密检索器**（Qwen3-Retriever-8B，索引取每篇前 512 token）
   训练数据 = 官方训练集 + dev1 + **外部 1,000 条**（Webis 的 ToT Known-Item Search Triplets）
   **三种数据增强**（每条训练样本造三个变体）：
   * **删一条线索**：删掉"不重要"的那条——重要性 = 该线索与金标文档的余弦相似度；
   * **换同义词**：把一条线索换成同义说法；
   * **换误导性说法**：故意改成**改变语义**的说法。
   ⇒ ⚠ **这三种增强正好对应 ToT 的三种现象（漏线索、换说法、假记忆）——可直接借鉴为造训练数据的配方。**

4. **拿大模型当检索器**：提示 DeepSeek-R1 与 GPT-5 **直接回忆条目名/URL**，取并集前 10，
   再用 URL 或 Wikimedia API 对齐回语料。
   ⇒ 🔴 **这就是"用大模型的世界知识当检索路"。对我们的场景不可抄**（答案必须出自那条原文）。

**重排侧三招**：微调 pointwise 重排器（受控负采样）→ 大模型 listwise 重排 → 同义词替换 + 排序集成。

### 6.2 🔴 两篇论文是**两套对立的路子**，这决定我们选哪条

| | **DS@GT（0.4106）** | **SRCB 冠军（0.6824）** |
|---|---|---|
| 外部知识库 | ❌ **明确不用**："Such coupling is incompatible with realistic ToT scenarios" | ✅ **用 Wikidata** 过滤语料 |
| 领域微调 | ❌ 全 zero-shot："no task-specific finetuning" | ✅ **检索器与重排器都微调** |
| 大模型世界知识 | ❌ 严格接地："No external knowledge" | ✅ **用它当一条检索路** |
| 自述适用范围 | 开放世界、私有语料、领域未知 | 固定语料、领域已知 |

**TREC 总览也印证了这一点**：
> "**The top four runs leveraged a combination of provided and other datasets for training.**"

⇒ **我们的位置**：本库语料**固定且已知**（6,797 篇 / 522,001 条）——
**DS@GT「不要耦合语料」的理由对我们不成立** ⇒ **SRCB 那条路的前提是成立的**。
⇒ ⚠ **但 SRCB 的两个主力杠杆，一个我们不能抄（世界知识），一个被本纲 §7 挡着（学习式）**——见 6.3。

### 6.3 🔴 一处**撞车，必须报业主**（按台账规矩我不提，只报）

本纲 §7「明确不做」里有一条：

> | **学习式排序 / 学习式稀疏**（**没有标注数据**） | 同上 |

**但两件事变了**：
1. **我本轮刚入库的 `eval/lay-phrasing/gen-V2.jsonl` 就是 1,832 条（外行说法 → 术语）配对**——
   对 **P1 的"选中术语"这一步**而言，**那是标注数据**。
   ⚠ 但它**不是条款级标注**（标签是术语，不是条文）⇒ **对"条款排序"确实仍无标注数据。**
2. **SRCB 的三种数据增强（删线索/换同义/换误导）是"没有标注也能自己造"的配方**，
   且它明确写了"**construct three augmented variants for each training sample**"。

⇒ **所以"没有标注数据"这个理由，对"P1 的术语选择"这一步可能已经过时；对"条款级排序"仍然成立。**
⇒ **要翻案请你明说**；不说就维持 §7 现状，本条只作留痕。

### 6.4 ⭐ UvA 那篇：冲着"合成语料"来的，有一组数字**直接打我们**

**《[Hedge Removal, Query Drift, and the Simulation Gap in ToT Retrieval](https://trec.nist.gov/pubs/trec34/papers/UAmsterdam.tot.pdf)》**（Sotic & Kamps，阿姆斯特丹大学）

**摘要里的三条硬结论（原话）**：

1. 🔴 **模拟差距**：
   > "Our experiments reveal a **substantial divergence between LLM-simulated development data and the
   > official test set.** Hedge removal yielded large gains on verbose synthetic queries
   > (**+25.4% NDCG on dev3**), but **minimal improvement on sparse human queries (+2.7% on test,
   > not significant)**."
   ⇒ ⚠⚠ **这就是对我们那 1,832 条合成语料的直接警告**：
   **一个在合成数据上看着大涨（+25.4%）的手法，在真人数据上只有 +2.7% 且不显著。**
2. **"Negation penalties produced no measurable effect across all conditions."**
   ⇒ 与 DS@GT 的"删否定"警告方向一致但更强：**加否定惩罚根本没用**。
3. **"Pseudo-Relance Feedback (RM3) consistently degraded performance, amplifying query drift
   rather than resolving vocabulary mismatch."**
   ⇒ **这是第三个独立来源说 PRF 在这里有害**（DS@GT 的 Table 6 也是 RM3 变差；本篇说"一致地变差"）。

**并且它给了一个独立的召回瓶颈数**：
> "Analysis of the recall pool reveals a fundamental bottleneck: **only 32% of target documents
> appeared among the top 100 BM25 results on the test set.**"

⇒ **三个独立来源的"第一级召回天花板"**：
| 来源 | 数 |
|---|---|
| DS@GT | 原问题 Recall@1000 = **0.5225** |
| TREC 总览（BM25 基线） | Recall@1000 = **0.4855** |
| **UvA** | 目标落在 BM25 **前 100** 只 **32%** |

**⭐ 最有行动价值的一条**：
> "hybrid dense reranking **improved early precision by 10.6% on hard queries where lexical matching
> failed**, but **degraded performance on queries with strong term overlap**."

⇒ 🔴 **这正是本纲 P4「检索分类闸」要的东西，而且它给了一个可测的路由信号：词面重叠强弱。**
⇒ **本纲 §1.2 已经把问题天然分成两半**（**53.0% 零重合** / **47.0% 有重合**）——
**那两半正好就是"该开稠密"与"该开词面"的分界。**
⇒ ⚠ **按"通用层纯借鉴"的口径，这是可以直接抄的现成做法**（别人实测过的信号）。

**一条工程细节（与我们硬件相近）**：作者只有 **16GB 内存 + 单张消费级 GPU**，
用**字节偏移查表**在原始 JSONL 上做常数时间取文档正文，避免把 20GB 语料装进内存。

**结论原话**：
> "systems optimized on LLM-simulated ToT data risk **overfitting to synthetic linguistic patterns
> that do not reflect the sparse, fragmented nature of real human memory retrieval**."

### 6.5 本轮**仍未读**的（不得当结论）

- **SRCB 的第 3.2 节与结果表**（PDF 共 8 页，我读到第 5 页）；它的**负采样细节**未读。
- **UvA 的第 3–5 节**（合成数据结果、真人数据结果、分析）——**只读了摘要与引言**。
  它的 RQ1/RQ2/RQ3 逐项结果、以及"混合重排 10.6%"的**条件细节**都在那里。
- **DS@GT 的 PDF 文件名没猜对**（下到 276 字节的 404）⇒ 该篇**仍只有 arXiv 摘要与正文网页版**。
- 仍未读：Yale@TREC2024、IISERK@TREC2024、BLUR 基准原文、**CLEF Social Book Search（2011–2016，"Name that Book"）**。
- **有没有中文工作——仍未查。**
- ⚠ **以上全部仍是"读别人的结论"，我一次都没有在本库复现。**

