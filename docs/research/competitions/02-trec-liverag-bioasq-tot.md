# TREC RAG / LiveRAG / BioASQ / TREC ToT：国际主流评测的前列技术路线（B 线）

> **抓取日**：2026-11-05。证据分档：【一手】官方赛道页、官方 overview、队伍技术报告全文、官方代码；【转述】第三方转述；【推断】本文自行判断。查不到的写“未查证”，不补编。
>
> **结论先行**：这条线真正值得抄的不是某一个冠军系统，而是三个可复用的结构：**（1）把“答不答/支不支持”做成生成前的事实抽取与校验层；（2）先拆问题、再检索、最后再筛，同时用 RRF 融合稀疏/稠密/LLM 候选；（3）做模糊检索时不要先猜实体，先把“线索清单”抽出来并用 cue→dense→rerank→LLM rerank 的多阶段管线扩召回。** BioASQ 的头部赛法说明：在专业语料里，**snippet（片段）先抽、再重排、最后生成**比直接把长摘要喂给模型更稳定；TREC RAG/LiveRAG 的头部赛法说明：**nugget（关键事实单位）抽取/覆盖检查 + 引用支援检查**比单纯 rerank 更能改变分数。

---

## 1. 赛道版图：规模、任务与评分

| 竞赛 | 年份 | 规模（官方口径） | 任务/语料 | 关键指标 |
|---|---:|---|---|---|
| **TREC RAG Track** | 2024 | 端到端 RAG **93 runs / 20 groups**；AG **53 runs / 11 groups**；support 研究实际评审 **45 submissions / 36 topics**【一手】Thakur et al., *Support Evaluation for the TREC 2024 RAG Track* | MS MARCO V2.1：10,960,555 篇去重文档 → **113,520,750 passages**；任务分 Retrieval（R）、Augmented Generation（AG）、RAG | nugget 完整性/重要性、逐句 citation 的 weighted precision/recall；support 研究以人工 + GPT-4o 判级【一手】 |
| **TREC RAG Track** | 2025 | **51 RAG runs / 16 groups；25 AG runs / 9 groups；36 RJ runs / 5 groups**；官网称超过 **150 submissions**【一手】TREC 2025 overview | MS MARCO V2.1；105 个长 narrative；任务 R / AG / RAG / Relevance Judgment（RJ） | sub-narrative relevance 0–4；strict vital nugget recall；sub-narrative coverage；weighted precision/recall；RJ 与人工 kappa【一手】 |
| **LiveRAG Challenge 2025** | 2025 | **70 teams / 27 countries** 参加 live day；**40 队入选后 25 队实际提交**；500 题 **2 小时**时限【一手】LiveRAG Challenge Report | FineWeb-10BT（官方报告称 **15M docs 子集**）+ 固定 Falcon3-10B-Instruct；DataMorgana 合成题 | Relevance/Correctness（-1/0/1/2）、Faithfulness（-1/0/1）；随后对头部系统做 Coverage/Relatedness/Quality 人工评审并以 Borda 汇总【一手】 |
| **BioASQ** | 2024 | 全挑战 **37 队 / >700 submissions**；其中 Task 12b **26 队 / 89 systems**；训练题 **5,049**，测试 **340**（4×85）【一手】BioASQ 2024 overview | PubMed/MEDLINE；yes/no、factoid、list、summary；Phase A（检索 docs+snippets）、A+（直接答）、B（gold evidence 再答）；Synergy 四轮 | doc MAP；snippet F1 类指标；yes/no accuracy；factoid MRR；list F1；ideal ROUGE + 人工/专家评【一手】 |
| **BioASQ** | 2025 | 全挑战 **83 队 / >1000 submissions**；Task 13b + Synergy **49 teams / 160 systems**【一手】BioASQ 2025 overview | 同 BioASQ 2024 结构；另有 MultiClinSum、BioNNE-L、ELCardioCC、GutBrainIE 等新任务；Task 13b 4 个批次 | 与 2024 相同；理想答案/事实题常以前五名为“头部”口径【一手】 |
| **TREC ToT** | 2024 | **6 groups / 18 runs**；3,185,450 Wiki 文章；600 test queries；官方指标 NDCG@1000【一手】TREC 2024 ToT overview | 已知项再发现（不能稳定想起 identifier），movie/celebrity/landmark 三域 | NDCG@1000、NDCG@10、Recall、MRR【一手】 |
| **TREC ToT** | 2025 | **9 groups / 32 runs**；6,407,814 Wiki 文章；官方指标 NDCG@1000【一手】TREC 2025 ToT overview | 通用域；MS-ToT + NIST 人工 elicited + LLM synthetic；输出最多 1000 篇排序 | NDCG@1000、NDCG@10、R@1000、MRR【一手】 |

> **口径提醒**：LiveRAG 报告正文别处曾把语料描述为 FineWeb-10BT；其 leaderboard 队名并非某个“冠军”而是 25 支实际答题队。TREC RAG 没有通常意义的“冠军”，只有任务/指标榜单；本线按**最高分 runs + 队伍原话方法**记录。

---

## 2. TREC RAG Track：头部系统靠什么赢

### 2.1 官方基线：三段式强融合管线

【一手】NIST 2024 appendix + Ragnarök 论文：官方基线第一阶段为 **BM25 + Rocchio + Snowflake Embed L/M + GTE Large 的 RRF**；第二阶段 **monoT5-3B**；第三阶段 **RankZephyr**；生成用 GPT-4o / Llama-3.1-70B / Command R Plus 各跑一个版本。

这条基线本身已经说明：TREC RAG 的“主流答案”不是单模型，而是 **sparse+dense+cross-encoder/LLM rerank 的多段融合**。但真正冲到头部的是在此基础上做了**结构与生成控制**的队伍。

### 2.2 头部生成/引用系统

#### 1. IITD-IRL `ag_rag_gpt35_expansion_rrf_20`：用官方 top-20 证据 + 结构化输出控制引用

- 名次/分数：在 support 研究的 **manual from scratch** 表中，weighted precision/recall **0.793**，为全表最高；GPT-4o 判级 **0.868**，亦为最高或并列最高【一手】Thakur et al. support study。任务为端到端 RAG，不是 AG。
- 做法：基线检索取 top-20 segments，GPT-3.5 生成；用 **Pydantic schema** 约束输出；每句尽量短、每句后加 IEEE 风格引用；作者称小模型生成时句子组织与引用不稳定，所以坚持大模型【一手】NIST appendix run description。
- 四段拆解：
  - 检索：不自建检索，直接复用官方 fs4 基线 top-20。
  - 融合/重排：不做；收益来自上游强基线。
  - 生成：结构化 JSON schema + 简洁句子。
  - 自检拒答：没有拒答模块。**这是它最容易被误抄的一点：它赢在“短答+引用严”，不是赢在“能拒答”。**
- 可迁移：**“固定证据列表 + schema 约束 + 短句单引”**。对本仓就是“每个结论句配一个条文号，句子只写一个事实”。

#### 2. TREMA-UNH：迭代事实抽取与验证（RAG 场景里最值得抄的一条）

- 分数：`Ranked_Iterative_Fact_Extraction_and_Refinement` 人工 precision/recall **0.709**，GPT-4o **0.861**；`Enhanced_..._and_Prioritization` 人工 **0.777**，GPT-4o **0.846**，均为头部【一手】support study 表。
- 方法：先从最高分文档里抽 key facts，再拿事实去其余文档里找 supporting sentences 做验证；再从剩余文本补抽事实；用规则去重；最后做 smoothing 让句子流动【一手】NIST appendix。
- 四段拆解：
  - 检索：常规检索。
  - 融合：**把文档变成“事实”再排优先级**，不是直接堆 passage。
  - 生成：基于已被验证的事实集合。
  - 自检拒答：没有明确拒答，但“抽事实→跨文档验证→去重”的链条本身会丢掉无依据事实。
- 可迁移：**先把回答拆成 nuggets/facts，再验证每个 fact 是否有多文档互证**。这比 CoT 更适合法规/标准问答。

#### 3. WaterlooClarke / H2OLOO：LLM 做 relevance 判据与 RRF 融合的“生成在环”检索

- 分数：H2OLOO 的 AG runs `listgalore_gpt4o_ragnarokv4_top20` 人工 precision **0.610**、recall **0.487**；`listgalore_l31-70b` recall **0.532**【一手】support study。Waterloo 的 AG `UWCrag` 人工 **0.717**、GPT-4o **0.841**，为 AG 任务头部【一手】。
- 方法：Waterloo 检索侧把 15 个 runs、6 种 ranking stacks 融合；`query2doc` 扩 query；用 GPT-4o 对基线 top-25 做 graded relevance 判断，再把判断当主排序、`uwc0` 当 tie-break；`monster` 为 uwc1+uwc2 的 RRF【一手】NIST retrieval appendix。
- H2OLOO：top-3K 用 **BM25+Rocchio、Snowflake Embed L/M、GTE Large 融合**；top-3K 再过 **monoT5-3B**；top-100 用 RankGPT4-o / RankLLaMA3.1-70B / RankZephyr 融合【一手】。
- 四段拆解：检索/重排为强项；生成是 Ragnarök v4 模板；自检拒答无。
- 可迁移：**LLM 不只在最后生成，也可前置做 relevance 判据、扩 query、做 RRF 权重调节**。但算力高；本仓更适合只在“初筛 top-50 后”使用。

#### 4. UIS-IAI 的 GINGER：模块化 nugget 管线（分数一般，但结构最值得抄）

- 分数不高：`baseline_top_5` 人工 **0.522**；`ginger_top_5` 人工 **0.367**【一手】support study。但作者自称在 AG 任务曾为 top performing systems 之一【一手】队伍报告。**不要按分数抄它，按结构抄它。**
- 方法：**Grounded Information Nugget-based GEneration of Conversational Information-Seeking Responses**：detect nuggets → cluster nuggets → rank nuggets → summarize top clusters → generate follow-up questions for uncovered sub-spaces【一手】UIS-IAI 报告。
- 结构是最干净的“先事实、后回答”实现：它先把信息单位抽出来、聚类、排优先级，再生成；未覆盖的子空间还会反问追问。

#### 5. SoftBank-Meisei：稀疏+稠密+LLM 的朴素强融合（中段）

- 分数：`agtask-bm25-colbert_faiss-gpt4o-llama70b` 人工 **0.516**、GPT-4o **0.633**【一手】support study。
- 方法：BM25 + ColBERT/FAISS 混合检索；GPT-4o 或 Llama-70B 生成【一手】NIST appendix + 队伍报告。
- 这类队伍证明：**不做 nugget 化、不做显式校验，仍能进中上段**；差距不在检索器，而在生成与引用的结构化程度。

### 2.3 TREC 2025：长 narrative 把“覆盖面”抬成主指标

【一手】TREC 2025 overview：105 条 narrative；参考 top-k 由 **SPLADE-v3 + Arctic-Embed-L 首检 RRF**，再经 **RankLLM → RankQwen3-32B** 级联，最终 top-100。

#### 头部 runs（fully manual：post-edited nuggets + manual assignment）

| run | group | 任务 | strict vital | sub-narr coverage |
|---|---|---:|---:|---:|
| `LAS-agentic-RAG-agent` | ncsu-las | RAG | **0.500** | 0.800 |
| `no-decomp` | MITLL | RAG | 0.500 | 0.770 |
| `r_4method_ag_gpt41` | UTokyo | RAG | 0.490 | **0.810** |
| `gpt41` | UTokyo | AG | 0.480 | **0.810** |
| `Kun-Third` | RMIT-IR | RAG | 0.480 | 0.760 |
| `rag25_qwen3_50_ag` / `rag25_test_qwen3_50` | coordinators | AG/RAG | 0.470 | 0.800/0.810 |
| `r_2method_ag_gpt41` | UTokyo | RAG | 0.470 | **0.820** |
| `hltcoe-gpt5.searcher` | hltcoe-rerank | RAG | 0.470 | 0.810 |

#### 头部方法

- **UTokyo**【一手】队伍报告：Query 预处理用 **HyDE + keyword expansion（GPT-4.1）**；稀疏 **BM25 + SPLADE**；稠密 **BGE-small + Qwen3-Embedding-0.6B**；四路 **RRF（k=60）**；重排用 **GPT-4.1 sliding window** 并额外喂 document URL context。作者称这是其核心增益。
- **NITA_R_JH_HY**：BM25 + DPR dense 混合 + **cross-encoder/ms-marco-MiniLM-L-12-v2** 精排；为官方 R 任务头部之一：nDCG@30 **0.4778**、nDCG@100 **0.3774**【一手】TREC 2025 overview R 表 + 队伍报告。
- **LAS agentic**：2025 队伍报告描述为 planner/researcher/writer/reviewer 多 agent 循环；selector 路由决定到 planner→researcher→writer→reviewer 的顺序，全部 agent 用 GPT-4.1；用 miniblame 做 citation attribution【一手】队伍报告。长 narrative 场景下它拿了 fully manual 的 strict vital 第一梯队。
- **HLTCOE** 的 `hltcoe-gpt5.searcher`：RAG strict vital 0.470 / coverage 0.810；也属第一梯队，方法公开度低于 UTokyo。

> **2025 的新结论**：没有单一“冠军系统”；长问题最怕的是**只答主线漏子线**。官方叙事就是证据：sub-narrative coverage 与 strict vital nugget recall 是两套指标；最强系统往往是“先拆 sub-narratives → 证明每个子问题都有独立证据 → 再拼回答”。

---

## 3. LiveRAG 2025：固定模型后，检索/提示/校验的差别成为全部

【一手】LiveRAG Challenge Report：固定 **FineWeb-10BT** 与 **Falcon3-10B-Instruct**；所有队 2 小时内在线生成；LLM-as-a-judge，先测 Correctness 与 Faithfulness，再对头部 13 队做 Coverage/Relatedness/Quality 人工评审并 Borda 汇总。人工最终前列：

| 人工名次 | 队 | Borda | Coverage | Relatedness | Quality | LLM Correctness（105 题） |
|---:|---|---:|---:|---:|---:|---:|
| 1 | RMIT-ADMS | 7.707 | 1.615 | 1.885 | 1.673 | 1.121 |
| 2 | RAGtifier | 7.351 | 1.558 | 1.817 | 1.558 | 1.140 |
| 3 | UDInfo | 7.240 | 1.510 | 1.856 | 1.548 | 1.110 |
| 4 | Magikarp | 7.077 | 1.452 | 1.875 | 1.567 | 1.122 |

Session 在线 Correctness：Session1 第一 **RMIT-ADMS 1.199 / Faithfulness 0.477**；Session2 第一 **Magikarp 1.232 / 0.656**【一手】报告 Table 3、Table 4、Table 8。

### 3.1 RMIT-ADMS：GRAG（Hypothetical Answer + Hybrid RRF + LLM pointwise rerank）

【一手】队伍报告 arXiv 2506.14516：

- **检索**：OpenSearch **BM25** + Pinecone dense（E5-base 512 维）→ **RRF k=60** 三路融合。
- **问题增强**：最终选 **GRAG** —— 先生成 hypothetical answer，当作搜索 query 与原问并联。
- **重排**：LLM pointwise 判断 doc 是否含答案，P(Yes) < **0.5** 丢弃。
- **生成**：官方约束下做大量 prompt/config 的 GoP+ANOVA 系统搜索；发现**“拒答提示”变的 Medium/Advanced prompt 并没有成为最终提交**，最终用的是 Naive prompt。
- 结果：Session1 第一（Correctness 1.199 / Faithfulness 0.477）；人工总排名第一。
- 可迁移：**固定便宜模型时，query 变体/hypothetical answer + RRF + pointwise LLM filter** 三件套最稳。以及它的教训：拒答 prompt 不是万能，naive prompt 反而在该约束下胜出。

### 3.2 Magikarp：知识感知多样性重排（Knowledge-Aware Diverse Reranking）

【一手】队伍报告 arXiv 2506.20476：

- **召回**：sparse+dense **交错合并（interleave）**，保留各自次序并去重；召回上限 R@2k 达 0.90，优于任一单路。
- **初排**：jina-reranker-m0。
- **核心发明**：用微调后的 Falcon 做 **Knowledge Element Declaration** —— 把 top docs 逐篇拆成问题需要的 knowledge elements；再把这些元素**汇总**成两个互补的知识表示（core / sum0 / sum1）；用 `M_rank(Q, E_qsum_i, D)` 对两个表示分别重排，再 interleave 合并。**目的就是防止单文档把“一个子问题”吃满，其他子问题没位子。**
- **参数**：`N_know = 5` 最优；jina-reranker-m0 本身在多文档下 R@5 0.42 → 加本方法 **0.44**；同时不伤单文档。
- **它自己承认的失败**：query rewriting 用 Falcon 微调后**没有超过原 query + hybrid**；更细的 reranker 微调、LLM CoT rerank、knowledge-gap rerank 也未胜出，故未进最终方案。
- 结果：Session2 在线 Correctness **1.232 / Faithfulness 0.656**，均为全场最高；人工总排名第 4（靠 Borda 聚合被 RMIT 拉开）。
- 可迁移：**“多子问题多样性重排”是解决多文档问题的解法**。对本仓：多跳/多要点问题，先拆子问，再对每子问各拿候选、做交错合并，而不是只按整题一次排。

### 3.3 RAGtifier：InstructRAG 去噪 + Pinecone@200 + BGE@5 + 逆序上下文

【一手】队伍报告 arXiv 2506.14412：

- 比较了 5 种生成（Naïve / TrustRAG / InstructRAG / Astute / IterDRAG）、2 检索器、2 reranker。
- 稠密 Pinecone 快于 OpenSearch（@k=50 时 0.58s vs OpenSearch 更慢），且 gold doc recall 最高值都在 @k=50 以上。
- **Rank-R1 不可用**：单题可达 **100 秒**。
- 最优：**Pinecone@200 + BGE rerank@5 + inverted context order**（最相关 doc 放最后紧贴问题）。
- InstructRAG = 先让 LLM 识别相关信息生成 rationale，再显式去噪；最终取它胜过 IterDRAG。作者还给了一组外部对照：IterDRAG 在线 Faithfulness **0.73** vs InstructRAG 同设置 **0.93**（内部测值）。
- 可迁移：**InstructRAG 的 rationale 是可迁移的“生成前去噪”小模块**；它能否赢 IterDRAG 的关键不是更长上下文，而是“先归纳再生成”。

### 3.4 UDInfo：人工第三，但方法未公开

- 名次：人工 Borda 第三（7.240），Session2 在线 Correctness 1.201 / Faithfulness 0.623，接近最高。
- 方法：**未查证**（无公开技术报告）。

---

## 4. BioASQ：专业领域头部系统——文档/片段先行，答案后置

> BioASQ 不只有一个“最强系统”：它的榜单按 batch 与 question type 分开，同一个队可有多个 systems。以下写**头部系统群**和**有方法报告的头部队**，不硬凑一个“冠军”。

### 4.1 2024（Task 12b：26 队 / 89 systems）

官方 overview 列出的方法谱系【一手】：

| 队（Phase A/A+/B 全参加） | 路线 |
|---|---|
| MQU | Llama-2/3、Gemini、Phi-3 + query expansion + re-ranking + RAG |
| BSRC（Fleming） | sparse/dense/hybrid 检索 + 开源 LLM；Yes/No 用多个模型 jury majority vote |
| MiBi (Jena) | BM25（标题/摘要/MeSH）+ bi-encoder/cross-encoder rerank；snippet 用 GPT-3.5 CoT few-shot 抽或标题+≤3 句启发式 |
| UA (Aveiro) | BM25 首检 → PubMedBERT/BioLinkBERT rerank；BGE-M3 + RRF 融合 |
| CUHK-AIH | Pyserini BM25 → BM25+vector ensemble；Llama2-chat-7B LoRA 微调 |
| Gatech | Mixtral/GPT-J/GPT-4/Llama2 + prompt few-shot，关键词抽取→PubMed query→长短答案 |
| Fudan-Atypon | LLM 抽关键词扩 query；四模型融合；student-major 角色提示 |

**BSRC 的 “farm of open LLMs”**【一手】Zenodo 报告：dense/hybrid 法在 MAP 上胜过纯 sparse；Yes/No 用多模型多数投票；Ideal Answer 用 Mixtral。结果：Synergy 拿 **1st/2nd exact** 多轮、**2nd documents**、**2nd ideal**；Task B snippets **1st（一轮）**。

### 4.2 2025（Task 13b + Synergy：49 队 / 160 systems）

#### UniTor@BioASQ：当前最完整、可抄的头部实现之一

【一手】队伍报告 CEUR（全文）：

- **检索**：BM25/Solr + dense（SentenceBERT）→ RRF(multiplicative fusion) + transformer reranker。作者做 grid search 优化 MAP。
- **snippet**：任务适配 LLM 微调抽取片段；用**合成的 plausible candidate snippets** 作为语义锚点喂给 reranker。
- **生成**：统一的多任务答案生成器（yes/no、factoid、list、summary 四类共用一个模型，输入同时含 abstracts + highlighted snippets）。
- 结果：ideal 与 factoid 生成长期稳定 **top five**；ideal 在 4 个批次里 **2 次第一**；snippet 抽取 **top ten**；即便用的都是紧凑开源模型。
- 关键消融：
  - 合成 snippet 做 rerank 锚点：**稳定但小幅**提升检索。
  - PRF 扩 query：**在部分 batch 提 recall，但不稳定**。
  - 把 snippet extraction 当硬过滤器：**precision 上升、recall 掉**。
  - 多任务生成用 snippets+abstracts：一贯优于只用其一。

#### Fleming Reczko（Synergy 2025）

【一手】机构通稿：Synergy 2025 拿 **2 个第一（exact、ideal）+ 5 个第二（documents、snippets、exact、ideal）**。方法与 2024 的 farm 路线连续（开源 LLM ensemble + hybrid 检索）。

> **BioASQ 对本仓的意义不是“抄它哪个模型”，而是抄它的任务分层**：Phase A 检索（doc+snippet）→ Phase A+ 直接答 → Phase B 给 gold evidence 再答。它天然把“检索对不对”和“生成对不对”分开打分，是本仓自带评测集时最值得借的骨架。

---

## 5. TREC ToT：根据模糊记忆找目标——本线最“对味”的一条

> **本节即业主说的“ToT”**：它**不是 RAG/知识库竞赛**，而是 known-item retrieval——用户不稳定记得 identifier，只能给场景、印象、碎片描述。**这正是本仓“大白话提问 53% 零字面重叠”的同构问题。**

### 5.1 赛道判据（组织者原话）

- “Tip-of-the-tongue (ToT) known-item retrieval involves **re-finding an item for which the searcher does not reliably recall an identifier**.’【一手】TREC 2025 overview 摘要。
- “ToT information requests… are verbose and **tend to include several complex phenomena**, making them especially difficult for existing information retrieval systems.”【一手】
- “**Current IR systems are not well-suited to resolve ToT information needs**.”【一手】
- 2024 官方指标 **NDCG@1000**；2025 官方指标 **NDCG@1000**，并列报 NDCG@10、R@1000、MRR【一手】。

### 5.2 2025 官方结果表（32 runs）——头部与基线对比

| run | group | NDCG@1000 | NDCG@10 | R@1000 | 备注 |
|---|---|---:|---:|---:|---|
| `scrb-tot-04` | SRCB | **0.6824** | 0.6576 | 0.9051 | 头部；含外部数据 |
| `scrb-tot-03` | SRCB | 0.6787 | 0.6547 | 0.9051 | 同上 |
| `scrb-tot-02` | SRCB | 0.6700 | 0.6449 | 0.9051 | 同上 |
| `scrb-tot-01` | SRCB | 0.6458 | 0.6162 | 0.8955 | 同上 |
| `gmn-rerank-500` | DS@GT | 0.4106 | 0.3831 | 0.6559 | Gemini-2.5-Flash 实体生成 + PyTerrier BM25 + BGE-M3 dense + Gemini listwise rerank |
| `webis-bm25-gpt-oss` | webis | 0.3689 | 0.3078 | **0.7637** | LLM 删词 query relaxation + BM25；Recall 极高但 NDCG@10 低 |
| `runid4` | ufmg | 0.2771 | 0.2136 | 0.6752 | DPO/ToT 改写 + GPT-5-nano 集成 |
| `pyterrier-bm25*` | coordinators | 0.1700 | 0.1223 | 0.4855 | 官方 BM25 基线 |
| `lightning-ir-dense*` | coordinators | **0.0514** | 0.0189 | 0.2653 | 官方 dense 基线 |

三条直接读数：
1. **纯向量 0.0514 < 纯 BM25 0.1700（差 3 倍）**。对本仓“按意思找 5.8% / 按字找 6.8%”同向。
2. **SRCB 是基线的 4.0 倍**（0.6824 / 0.1700）。
3. **webis 的 recall@1000 0.7637 很高但 NDCG@10 只有 0.3078**——“找得到、排不上来”是 ToT 的典型病。

### 5.3 头部方法

#### 1. SRCB：cue 抽取 + 修配式负样本 + LLM 检索补位 + 三段 listwise 重排

【一手】队伍报告：

- **Query preprocessing**：DeepSeek-V3 把模糊长 query 抽成 10 类 cue 清单（内容、情节/场景/引语、感官、情绪、体验语境、时间、语言/地区/文化、关联人/物、比较等），**直接输出，不猜实体**。
- **Dense retriever**：Qwen3-Embedding-8B，top-2000 候选。电影域用微调模型：训练 = train + dev1 + Webis triplets 1000 条，**三类数据增强**（删一个低重要 cue、同义词替换、误导 cue 替换，模拟模糊/错误记忆）。
- **Re-ranker**：Qwen3-Reranker-8B LoRA 微调；负样本按难度三段 **1 : 3 : 3**（hard/medium/easy）。
- **LLM retrieval 补位**：DeepSeek-R1 + GPT-5 直接“回忆”10 个 Wiki 实体，取 top-10，与 reranker 结果交错插入（rank 6 或 11–20）。
- **最终重排**：DeepSeek-V3 listwise 在 top-20 / top-10 上，GPT-5 再对 top-4 精排。
- 结果：`tot-01` 0.6458 → `tot-02` 0.6700（加 LLM 检索）→ `tot-03` 0.6787（加三段重排）→ `tot-04` **0.6824**（电影/非电影不同 reranker 微调）。

#### 2. DS@GT：Gemini 实体生成 + BM25 + BGE-M3 三路融合重排

【一手】NIST run description：Gemini-2.5-Flash 生成 20 个实体 + 官方 PyTerrier BM25 top-500 + BGE-M3 dense top-500 → 合并 1020 → Gemini-2.5-Flash listwise（rank_llm）重排。NDCG@1000 **0.4106**。

#### 3. Webis：query relaxation（删词）——便宜但只提召回

【一手】队伍报告：用 LLM 指令删掉“可能降低检索效果”的词，再跑 PyTerrier BM25。`gpt-oss` 版 R@1000 **0.7637**、NDCG@10 0.3078；`llama` 版 0.6785 / 0.1968。
  → **对“提召回有用、对提早序帮助有限”**，并且 gpt-oss 比 llama 好很多。

#### 4. UFMG：DPO 改写（把“哪种改写更快排到目标”做成偏好对）

【一手】队伍报告：用 dense 与 cross-encoder 的检索分数自动造偏好对，训 DPO；Tree-of-Thoughts 推理 + GPT-5-nano 集成；NDCG@1000 **0.277**（NIST 表中 0.2771）。**教训**：高成本改写只拿到 0.277，远低于 SRCB 的 0.6824——说明在 ToT 上“改写精排”不是主矛盾，**“把候选集扩成 2000 并靠 reranker 守住头部”** 才是。

#### 5. DUTH：纯词法融合（一个反例，说明无神经也行）

【一手】队伍报告：BM25 + DFR 变体 + QL 模型，RM3 伪反馈 + RRF；正式提交**不用任何神经模型**（开发期试过 Sentence-BERT + MiniLM cross-encoder，效果好但未提交）。官方结果 NDCG@1000 ≈ **0.154**，与 BM25 基线 0.170 同级。**作用：证明 SRCB 的跃升不是“多加一个神经模型”，而是“压测→增强→负采样→LLM 补位”的组合。**

---

## 6. 跨赛道归纳：能直接下手的 6 条

| 条 | 出处 | 抄什么（到机构级） |
|---|---|---|
| **1. 多语言、多源在召回阶段就要融合** | TREC RAG 官方基线；LiveRAG Magikarp、RMIT；ToT SRCB | 第一检出必须至少含 **sparse + dense + LLM 实体/假设** 三路，合并用 RRF 或交错合并。只靠一路，在 ToT 上纯 dense 仅 0.0514。 |
| **2. 查询改写不是单一静态 prompt** | RMIT（hypothetical answer）、UFMG（DPO + ToT）、LiveRAG（query variants） | 改写用于“生成可检索的第二 query”；RMIT 的 ANOVA 指向“问题增强”是最显著因子，UFMG 的 DPO 相对 prompt tuning 亦有增益。但要收敛：它救不了纯 dense 基线。 |
| **3. 重排的趋势：点对点 LLM 打分 → listwise LLM 重排** | LiveRAG RMIT（pointwise 0.5 阈值）、Magikarp（jina + 知识多样性）、ToT SRCB（DeepSeek listwise + GPT-5 精排）、TREC 2025 UTokyo（GPT-4.1 sliding window） | 小规模（top-50）用 cross-encoder；top-20 精排再上 LLM listwise。LLM rerank 必须控制延迟：LiveRAG 实测 Rank-R1 单题 100 秒被否决。 |
| **4. 事实抽取与引用支持检查是“生成后可执行”的模块** | TREC RAG TREMA-UNH；GINGER；LiveRAG InstructRAG | 生成前先“抽 nuggets/facts→跨文档验证→去重”，或在生成后对每句做 support 判定。TREC support 研究里，GPT-4o 与人工在 run-level Kendall **>0.79**，说明该层可自动化且与人工排序一致。 |
| **5. 多文档、多子问题：不要一次排满，要保证子问题各有位子** | Magikarp（Knowledge-Aware Diverse Reranking，N_know=5）；GINGER（cluster + follow-up）；TREC 2025 sub-narratives | 把问题拆子问/子叙事，对每个分配候选片段，再交错合并。Magikarp 在多文档场景 R@5 0.42→0.44，且单文档不降。 |
| **6. 专业领域（BioASQ）先“抽 snippet”再回答** | UniTor（snippet 先抽 + rerank 锚点 + 多任务生成）；BSRC（多模型 jury） | 门槛低、收益稳：snippet 抽取是 precision/recall 的阀门；把 snippet extraction 当硬过滤器会掉 recall。官方 Phase A/A+/B 的分离打分（MAP / exact / ideal）值得本仓评测集借。 |

---

## 7. 反证

**搜了什么词**：
1. `TREC RAG benchmark 被高估 质疑 复现失败 limitations`
2. `LiveRAG challenge 争议 LLM-as-a-judge 偏差`
3. `BioASQ challenge winner 刷榜 overfitting`
4. `Tip of the Tongue TREC 局限 争议 benchmark 质疑`

**搜出什么**：
- **TREC support 评测本身的证据链**：在 45 个 submissions / 36 topics 上，GPT-4o 与人工在完全一致率上从 scratch 只有 **56%**，post-editing 才到 **72%**；虽然 run-level Kendall **>0.79**，narrative-level 的散点明显【一手】support study。→ **不要把自动 judge 分数当成人工真值。**
- **LiveRAG 自己的伦理声明**：作者明确写了 LLM-judge 局限，“Higher Relevance and Faithfulness scores do not necessarily mean higher user satisfaction”【一手】RMIT 报告 §5。
- **BioASQ 的格局**：总队数 2024 **37** → 2025 **83（全任务）**，但 Task b/Synergy 本身 49 队且换手率高（新队约 80%）【一手】BioASQ 2025 overview。规模在涨，**但它仍是“专家出题、专家评”的小池子**，不能据此推断工业界 ROI。
- **ToT 的反证**：UFMG 用了 LoRA + DPO + ToT + 集成，NDCG@1000 只有 **0.277**，显著低于 SRCB 0.6824；DUTH 用纯 lexical 也能到 0.154。→ **“大模型改写/重排”不是 ToT 的充分条件，候选池搭建与负采样设计更关键。** 本线未搜到针对 SRCB 方法的独立复现失败报告，记 0 条。

---

## 8. 未查证清单

| 项 | 状态 | 原因 |
|---|---|---|
| UDInfo（LiveRAG 人工第 3）的具体方法 | 未查证 | 无公开技术报告 |
| TREC RAG 2024 的单一下单“冠军队” | 不存在 | 官方不设单一冠军，只有任务/指标榜单 |
| TREC RAG 2024 retrieval 任务的精确 top-scoring run 与分数 | 未查证 | NIST appendix 公开的是 run 描述表，公开的 trec_eval 输出为全量排序文件，未在本文解析为榜单 |
| BioASQ 2025 Task 13b 的官方名次表细节 | 只到头部描述 | 官方按 batch 名次分散，本文只用队伍报告自报的“top five / first in 2 of 4 batches” |
| BioASQ 2024 落地 ROI（工业实际落地） | 未查证 | 官方没有 ROI 数据 |
| TREC ToT 2024 的官方 NDCG@1000 完整榜单 | 未查证 | overview 摘要只给任务定义与规模，未开完整表；本文只引用已核实的 2025 表 |

---

## 9. 边界与 depth 分布

- **方法上**：TREC RAG/LiveRAG 的“前列”以官方分数表 + 队伍全文报告为准；LiveRAG 队名以官方 leaderboard 为准（纠正了“SignalRAG”等口头误名）；BioASQ 不硬凑冠军，按头部系统群记录。
- **depth 分布（本线 md + jsonl 机器可查）**：
  - `fulltext`：LiveRAG 报告、RMIT、RAGtifier、Magikarp、TREC RAG support study、TREC 2025 overview、ToT 2024/2025 overview、SRCB、UFMG、Webis、BioASQ 2025 overview、UniTor。
  - `source`：TREC 2024 NIST appendix（run descriptions）。
  - `readme`：BioASQ Fleming 通稿、官方赛道页（仅规模口径）。
  - `metadata`：UDInfo（仅名次）。
  - `tested`：0（本线未对任何系统在本机复跑）。
- **不承诺什么**：各赛道语料与评分彼此不可比；ToT 是 known-item retrieval，不是知识库 RAG 竞赛；LiveRAG 的“使用固定模型”是赛制，不是生产约束。
