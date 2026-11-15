# KDD Cup CRAG 两年全量：谁赢了、靠什么赢、哪些能用

> **触发**：业主 2026-11-05 提出「知识库/RAG 最权威规模最大的竞赛是 KDD Cup CRAG（国际）与 CCKS（国内）」，要求调研这一类大规模竞赛历年靠前队伍的技术路径，不局限于这两家。
> **本文件归属**：A 线（国际主赛道 · KDD Cup CRAG 2024 / CRAG-MM 2025）。B 线（TREC RAG / LiveRAG / BioASQ / ToT）、C 线（CCKS 等国内赛）、D 线（KDD Cup 其他赛道 / 企业级 RAG 赛）各住自己的文件。
> **抓取日**：2026-11-05（除另行标注）。

---

## 一、一句话结论

> **两年、六支上榜队、跨越文本与多模态两种形态，赢法只有一条是共通的：把「不知道就拒答」做成一个可训练/可判别的一等模块；检索本身全是现成件拼装（BeautifulSoup + BGE + cross-encoder），谁都没有在检索器上做出别人抄不动的差距。**
>
> 而 CRAG 官方测出的基线数字恰好打在我们身上：**朴素 RAG 只把 truthfulness 从 3.4% 抬到 9.1%，同时把幻觉率从 28.9% 抬到 31.6%**——「加了检索反而更容易编」。这不是我们一家的问题，是整条赛道的共同起点。

---

## 二、先核业主给的两条前提（一条成立、一条不成立）

### 前提 1：「KDD Cup CRAG 是知识库/RAG 领域规模最大的竞赛」——**按队伍数不成立；按「单一榜单的竞争密度」成立**

| 竞赛 | 年份 | 用户数 | 队伍数 | 提交数 | 出处 |
|---|---|---:|---:|---:|---|
| **KDD Cup CRAG** | 2024 | 3,212 | **384** | 6,323 | 【一手】AIcrowd 赛事页统计（`meta-comprehensive-rag-benchmark-kdd-cup-2024`，抓取 2026-11-05） |
| KDD Cup CRAG（官方口径） | 2024 | — | 384 | >5,600 | 【一手】IEEE Data Eng. Bull. 组织者论文，原文「more than 2,500 participants, 384 teams and more than 5,600 submissions」 |
| **KDD Cup CRAG-MM** | 2025 | 1,067 | **256** | 4,927 | 【一手】AIcrowd 赛事页统计（`meta-crag-mm-challenge-2025`） |
| CRAG-MM（官方口径） | 2025 | ≈1,000 | — | ≈5,000 | 【一手】CRAG-MM 基准论文摘要「about 1K participants and 5K submissions」 |
| **CCKS** | 2023 | ≈11,000 人 | **2,771** | — | 【一手】CCKS 2024 评测通知原文「去年，CCKS 2023 评测竞赛…吸引了 2771 支队伍、近 1.1 万人参赛」 |
| **CCKS** | 2024 | ≈5,300 人 | **2,400+** | — | 【一手】CCKS 2025 评测公告英文页「In 2024, CCKS hosted 11 evaluation tasks… attracted over 2,400 teams and nearly 5,300 participants」 |

**读数（这是本节最要紧的一句）**：**CCKS 的队伍数是 CRAG 的 6～7 倍，但 CCKS 是 10～11 条独立赛道分摊，单条赛道约 200～300 队**——CCKS 2023 开放域 KBQA 在天池的公开榜单显示 **281 个团队**（【一手】天池赛事页）。而 **CRAG 的 384 队全部打在同一个榜单、同一份私有测试集、同一套评分上**。

⇒ **「规模最大」看总人数：CCKS 赢；看「同题竞争密度」，CRAG 赢。** 两个说法各有一半对，不能笼统说 CRAG 规模最大。

### 前提 2：「ToT 只是信息检索中『根据模糊记忆找目标』的专项任务，不是知识库竞赛的主流」——**成立**

【一手】TREC 2025 ToT 官方 overview（arXiv `2601.20671`，2026-01-28）：

> "Tip-of-the-tongue (ToT) **known-item retrieval** involves **re-finding an item for which the searcher does not reliably recall an identifier**. ToT information requests (or queries) are verbose and tend to include several complex phenomena… This year, **9 groups** (including the track coordinators) submitted **32 runs**."

- 任务形态：6,407,814 篇维基文章里做 ad-hoc 排序，主指标 **nDCG@10**（【一手】overview §3.1 + DUTH 队伍报告 §4）。
- 规模：**9 组 / 32 runs**。与 CRAG 的 384 队、CCKS 的 2,400+ 队不是一个量级。
- 性质：**它是「已知项再发现」的检索赛道，不是知识库问答/RAG 赛道**——没有结构化知识源、没有答案生成、没有拒答设计。

⇒ **业主的判断成立。ToT 值得参考的是「模糊描述 → 目标排序」这一段，不能把它当成 RAG/知识库竞赛的代表。**

---

## 三、CRAG 2024：全部上榜队与技术路线（文本 · 三任务）

### 3.1 榜单（人工评测 · 私有测试集 · 流量加权）

| 任务 | 第 1 | 第 2 | 第 3 |
|---|---|---|---|
| Task 1 检索摘要（5 网页） | **db3 28.40%** | md_dh 24.0% | ElectricSheep 21.8% |
| Task 2 KG + 网页 | **db3 42.7%** | APEX 41.0% | md_dh 31.0% |
| Task 3 端到端（50 网页 + API） | **db3 47.8%** | APEX 44.9% | vslyu-team 25.6% |

【一手】AIcrowd 官方论坛「Final Evaluation Process & Team Scores」（topic 10785，发帖 2024-07-29）。分项冠军另设 7 个题类奖，其中 **dRAGonRAnGers 独揽三任务的 comparison 类第一**、ElectricSheep 独揽 Task 2 五个题类第一、**ETSLab / Future / Riviera4 分别拿下三任务的 false-premise 类第一**（同上）。

### 3.2 一组必须记住的对照数（官方 Table 31，人工评测）

| 方案 | Accuracy | Hallucination | Missing | Truthfulness | 延迟 |
|---|---:|---:|---:|---:|---:|
| LLM-only（Llama 3） | 32.3% | 28.9% | 38.8% | **3.4%** | — |
| **Straightforward RAG**（Llama 3） | 40.6% | **31.6%** | 27.8% | **9.1%** | — |
| LLM-only（GPT-4） | 33.5% | 13.5% | 53.0% | 20.0% | — |
| Straightforward RAG（GPT-4） | 43.6% | 30.1% | 26.3% | 13.5% | — |
| **第 3 名 vslyu-team** | 43% | 24.9% | 30.1% | 18.1% | — |
| **第 2 名 APEX** | 48.6% | 13.7% | 36.3% | 34.9% | — |
| **第 1 名 db3** | 53.3% | 17.1% | 28.0% | **36.2%** | — |
| Perplexity.ai（工业界） | 60.2% | 25.3% | 10.1% | 34.9% | 4,634 ms |
| ChatGPT Plus | 66.5% | 25.0% | 1.9% | 41.5% | 6,195 ms |
| Gemini Advanced | 65.9% | 16.6% | 12.5% | 49.3% | 5,246 ms |
| **Copilot Pro** | 68.5% | 17.9% | 7.8% | **50.6%** | 11,596 ms |

【一手】组织者论文 IEEE Data Eng. Bull. 2024（`sites.computer.org/debull/A24dec/p163.pdf`，本机 curl 拉取 + PyMuPDF 抽文，共 20 页 / 56,842 字符）。

**三条硬读数**：
1. **加了检索不一定变好**：Llama 3 上 accuracy 从 32.3→40.6（+8.3），但幻觉从 28.9→31.6（+2.7），truthfulness 只得 9.1%。
2. **冠军（36.2%）打不过商业系统（50.6%）**，但**冠军的 accuracy（53.3%）明显低于 Copilot（68.5%），真相是「少编」赢的**：db3 幻觉 17.1% vs Copilot 17.9% 相当，db3 的差距全在 missing（28.0% vs 7.8%）。
3. **质量与延迟反向**：truthfulness 最高的 Copilot 延迟 11.6 秒，是 Gemini 的 2.2 倍。

### 3.3 逐队拆解（四段：检索 / 融合重排 / 生成 / 自检拒答）

#### ① db3（北大高军组 + 华为 2012 实验室）——三任务全冠，唯一「两年连续」的队伍

【一手】技术报告 arXiv `2410.00005`（"Winning Solution For Meta KDD Cup' 24"，全文读完）。

| 段 | 做法 | 关键数字 |
|---|---|---|
| 检索 | BeautifulSoup 抽文 → LangChain `CharacterTextSplitter` → **Parent-Child 分块**（child 200 字符检索、parent 700 字符喂模型）→ `bge-base-en-v1.5` 检索 recall_k=50 → `bge-reranker-v2-m3` 精排到 5～10 | parent/child = 700/200；报告称 500/1000/2000 也可接受 |
| **额外一路（别人没有的）** | **「公开数据通路」**：把 Oscar / MovieLens / Grammy / 美股 PE·市值·EPS 预先序列化成自然语言段落（"The [attribute] is [value]."），按实体为键存好，用 LLM 做实体定位后拼进上下文 | 只覆盖 movie / finance / music 三个域 |
| 融合重排 | 两路（网页 + 预置数据）用 `<doc>` 标签拼接，截断到 4000 token | — |
| 生成 | Llama-3-8B-Instruct + LoRA（r=8, alpha=16, 4-bit） | 每任务一个 LoRA，2～3 epoch |
| **自检拒答** | **SFT 标签是构造出来的**：先用 `p_basic` 跑全量 → 用 GPT-4/Llama3 判对错 → 对的用 ground truth；错的再用 `p_context` 判「上下文里能不能推出答案」→ 推不出 ⇒ 标 **"i don't know"**；能推出 ⇒ 仍用 ground truth | 三段式标签构造，见报告 §2.4 |
| KG 那一路 | **把官方 38 个 API 重新封装成「正则化 API」** `get_movie(movie_name, condition)[key_name]`，支持 `eq/neq/ge/le`、`sort`、`AVG`、`len`、`*`（上一次结果），LLM 只做模板选择 + 实体名抽取 | 这是全场唯一被组织者单独点名为「innovative」的做法 |

**它为什么赢 Task 2/3（+4.2 / +6.5 个百分点）**：组织者原话——「First-place winner for all three tasks Db3, as an example, put in significant efforts for improving the results on using the APIs, which gained them large margins in handling those KG-supported questions.」【一手】组织者论文 §D.4。

**它自己的局限（作者原话）**：「This may affect the generalization capability of this system」（指手写 parser）＋「the general-purpose method for selecting and calling APIs」未解决。

#### ② APEX（中科大认知智能国重）——Task 2/3 第二

【一手】arXiv `2409.15337`（"Revisiting the Solution of Meta KDD Cup 2024: CRAG"，全文读完；同文另见 Frontiers of Computer Science 2026 版）。

| 段 | 做法 |
|---|---|
| 路由 | **两个分类器**：Domain Router（finance/sports/music/movie/open）+ **Dynamism Router**（static/slow/fast/real-time），都基于 Llama3-8B + MLP 头 + LoRA 微调，8:1:1 切分 |
| 检索 | HTML 用 **Newspaper** 解析（他们做了 5 种解析器的对照实验：newspaper 11.82 > markdownify 10.94 > trafilatura 10.14 > boilerpy3 9.42 > beautifulsoup 5.11）；Task 3 先用 **BM25 粗筛 top-50 块（1024 token）**→ 再 256 token 切块 `bge-m3` 余弦 top-10 → `bge-m3-v2-reranker` top-5 |
| KG | **逐步拆分式**：LLM 做 NER → 实体匹配（精确 + BM25 兜底）→ 时间抽取（正则 + pytz/datetime）→ **手写规则选 API** → JSON 转 Markdown |
| 融合 | **按域裁剪数据源**：open 域只用网页；movie/music 用网页+API；sports/finance **只用 API**（因为是实时/快变） |
| 生成 | Llama3-70B-Instruct **零样本**（不微调）+ CoT + 分域 few-shot（每个域 2 条 invalid question 示例） |
| **自检拒答** | **后处理规则**：对无实时 API 的域（open/movie/music）里 fast-changing 与 real-time 问题，**直接答 "I don't know"**；需要数值计算（如 "average"）的也直接拒答 |

**它的消融（Table 2，Task 2）**，这是全场最诚实的一组数：

| 去掉什么 | Score | 变化 |
|---|---:|---|
| 完整系统 | 31.22 | — |
| 去 Rerank | 29.17 | −2.05 |
| **去 Entity Match** | 21.44 | **−9.78** |
| **去 Time Info Extract** | 18.45 | **−12.77** |
| 去 Fewshot & CoT | 25.53 | −5.69（幻觉 15.54→26.55） |
| 去 Prerank（Task 3） | 29.53（31.66） | −2.13，但**耗时 68.17s → 5.96s** |

⇒ **两个最大的分差全在「把问题里的实体和时间抠准」上，不在检索器上。** 而 pre-rank 的价值是**延迟 11 倍**，不是准确率。

⚠ **该文有一处自相矛盾**（照抄原文）：「Ablation studies revealed that pre-ranking and re-ranking **marginally reduce** performance, while Entity Match and Time Information Extraction significantly decrease performance. Both pre-ranking and re-ranking **significantly contribute** to the improvement of retrieval quality.」两句对同一件事给了相反判断。**以表格数字为准（rerank −2.05）**，那句 "marginally reduce" 应为笔误。

#### ③ ElectricSheep（北大王选所 / PKU-Anker）——Task 1 第三，Task 2 拿五个题类第一

【一手】arXiv `2408.05141`（"A Hybrid RAG System with Comprehensive Enhancement on Complex Reasoning"，全文读完）。

- **拆成六模块**：网页处理（trafilatura 抽正文 + **表格单独抽成 Markdown**，BeautifulSoup 兜底）→ Attribute Predictor（static/dynamic 二分类）→ Numerical Calculator（**让模型产出一个 Python 表达式**，外部执行）→ **LLM Knowledge Extractor**（先不检索，凭参数知识答一遍）→ KG 模块（function calling 生成 API 调用）→ Reasoning 模块（汇总所有参考 + 另一个 agent 的答案，做二次判断）。
- **自检拒答**：CoT 里**强制三段自问**——「有没有 false premise？」「参考里有没有答案？」「凭现有知识能不能答？」，输出格式用 `===START=== / ===END===` 硬框住；备一个 Summarization Agent 兜底。
- **它的梯度消融（Task 1，官方基线起步）**，这是看懂「分是怎么一点点攒出来的」的最好一张表：

| 累加步骤 | Correct | Hallucination | Score |
|---|---:|---:|---:|
| 官方 RAG 基线 | 16.2 | 83.8 | −67.6 |
| + 优化分块抽取 | 23.7 | 76.3 | −52.6 |
| + Llama3-70B-GPTQ | 24.4 | 24.8 | −0.3 |
| + Attribute Predictor | 19.9 | 14.7 | **+5.2** |
| + Table Extractor | 21.3 | 15.2 | +6.1 |
| + Numerical Calculator | 23.7 | 16.6 | +7.2 |
| + Reasoning Module | 20.9 | 11.8 | +9.1 |
| + False Premise Identify | 26.0 | 13.5 | +12.5 |
| + LLM Knowledge Extractor | 27.3 | 13.4 | **+13.9** |

⇒ **换更强底座（−52.6 → −0.3）之后，剩下 +14 分全部来自「拒答/自检/工具」这几件小事**，没有一项来自检索器。

#### ④ md_dh / MARAGS（Darkhive，单人参赛）——Task 1 第二、Task 2 第三

【一手】arXiv `2409.03171`（"MARAGS: A Multi-Adapter System…"，全文读完）。

- **HTML 结构感知分块**：对解析树做 BFS，任一节点（含全部后代）文本 < 2000 字符即作为一个 segment；叶节点超长才按空白切分。
- **检索器四选一实测**（500 条 Task 1 留出集）：

| 检索方式 | Accuracy | CRAG |
|---|---:|---:|
| TF-IDF | 0.2740 | −0.110 |
| Biencoder | 0.310 | −0.132 |
| **Cross-encoder** | **0.328** | −0.116 |
| Ensemble（mean rank） | 0.308 | −0.128 |

⇒ **四种检索器 accuracy 差不到 6 个点，CRAG 分全是负的**——检索器选型在这个任务上不是胜负手。

- **它最有价值的一段是「重标标签」的消融**（同留出集）：

| 模型 | Accuracy | Hallucination | CRAG |
|---|---:|---:|---:|
| Llama 3 8B 原始 | 0.328 | 0.444 | −0.116 |
| + LoRA（原始标签） | **0.398** | **0.602** | **−0.204** |
| + LoRA（重标后） | 0.242 | **0.056** | **+0.186** |

⇒ **直接微调=准确率涨、幻觉也涨、总分更差；把「检索不到答案」的样本重标成 "i don't know"，准确率掉 15.6 个点，幻觉掉 54.6 个点，总分从 −0.204 翻到 +0.186。** 这是全赛最干脆的一组「拒答 > 硬答」证据。

- 作者自述的代价：**灾难性遗忘**——「Who has had a longer musical career, Sharika or Machine Gun Kelly?」这类本来会答的题，LoRA 之后一律 "i don't know"。

#### ⑤ dRAGonRAnGers（POSTECH Data Systems Lab）——三任务 comparison 类第一、Task 1 第二、Task 2/3 第三

⚠ **证据档：【转述】**——我只拿到二手：AIcrowd 官方「Winner Spotlight」帖（topic 17035）与组织者论文的转述，**技术报告本体（OpenReview `G4Ei2QlKnv`）被 Cloudflare 拦下，未读到全文**。

- 据官方 spotlight：**检索门控**（LLM 自评置信度高则跳过检索）+ **生成后验证**（self-consistency 二次判断）+ 微调 LLaMA 变体。
- 据组织者论文 §D.3：**显式置信度推断**这一类，含「让 LLM 自报置信度」与「多次采样看答案一致性」，后者更耗算力。
- 据检索片段（同一篇报告）：三步骤框架，含自一致性投票 `argmax{C_S | S ∈ E}` 与「Florida / Oklahoma / I don't know」三选项再判。

**⇒ 处置：列为「待核」。不给它记技术分。**

#### ⑥ vslyu-team（Task 3 第三，25.6%）

**未查证。** 搜 `"vslyu-team"` / `"vslyu" CRAG` 均未命中任何技术报告或仓库；官方 spotlight 只覆盖 db3 / dRAGonRAnGers / md_dh 三队。**已知遗漏，如实登记。**

---

## 四、CRAG-MM 2025：模态换了，结论没换

### 4.1 榜单

| 任务 | 第 1 | 第 2 | 第 3 |
|---|---|---|---|
| Task 1 单源（图-KG） | **Dianping-Trust-Safety 12.8%** | db3 8.4% | cruise 6.7% |
| Task 2 多源（+网页） | **Team\_NVIDIA 23.3%** | db3 22.1% | AcroYAMALEX 21.4% |
| Task 3 多轮 | **db3 36.8%** | BlackPearl 30.9% | Dianping-Trust-Safety 29.7% |
| **Grand Prize 第一视角总分** | **db3 21.0%**（三任务合计） | — | — |

分项：Simple — NEC\_AI\_ROCKETS 15.9%｜Multi-hop — otonadake 5.9%｜Comparison+Aggregation — gogoogo 3.3%｜Reasoning — otonadake 10.3%。

【一手】AIcrowd 论坛 topic 17308（获奖公告，2025-07-09）+ topic 17313（最终分数表，2025-07-11）。**两处均已用 Discourse JSON 接口取原文**。

**读数**：**同一个任务包里，最简单的题型 15.9%，最难的（比较/聚合）3.3%——差 4.8 倍。** 而全部 6 个奖里的最高分（Task 3 36.8%）仍低于 2024 年文本版冠军（47.8%）。

### 4.2 主办方自测的基线（这是本报告最该被记住的一段）

【一手】CRAG-MM 基准论文（arXiv `2510.26160`，全文 HTML 读完）Table 4：

| 设置 | 最佳模型 | Accuracy | Missing | Hallucination | Truthfulness |
|---|---|---:|---:|---:|---:|
| 单轮 · 纯 MM-LLM | GPT-5 Mini | 37.4 | 43.7 | 19.0 | 18.4 |
| 单轮 · Task 1 朴素 RAG | GPT-5 Mini | 39.3 | 43.9 | 16.8 | 22.5 |
| 单轮 · Task 2 朴素 RAG | GPT-5 Mini | 48.7 | 34.1 | 17.2 | **31.5** |
| 多轮 · Task 3 朴素 RAG | GPT-5 Mini | 61.0 | 22.5 | 16.5 | 42.5 |
| 工业界 SOTA（GPT-5 / Gemini 2.5 Pro / Claude Sonnet 4） | — | — | — | — | 32%～45% |

论文原话：「straightforward RAG approaches achieve only **32% and 43%** truthfulness on CRAG-MM single- and multi-turn QA… whereas state-of-the-art industry solutions have **similar quality (32%/45%)**」。

⇒ **工业界最强系统，和一套朴素 RAG，成绩几乎一样。** 这条与 2024 年「商业系统 50.6% vs 朴素 RAG 9.1%」不矛盾：两年测的东西不同（2024 给的是固定语料，2025 给的是受限 10 秒 + L40S 单卡），但两边的结论都指向同一件事——**这个任务上「多花钱」换不来「少编」。**

### 4.3 逐队拆解

#### ① db3（第二年，联合华为）——Task 3 第一 + Grand Prize

【一手】arXiv `2509.09681v2`（全文读完）。

| 段 | 做法 | 效果（作者自述） |
|---|---|---|
| 路由 | 8 类域分类器（Llama 3.2-VL 微调）：vehicle/plant/local/math/science/food/animal/other | 验证集 91.17% |
| **图像检索** | CLIP 图检索本身很差（ego 图与维基图分布差太大）→ 用 **Grounding-DINO** 先裁出查询图里的目标物体再检索 → 再用 VLM **图-图同一实体判定**重排 | 强 VLM 重排 **+10%**；蒸馏到 Llama 3.2-VL 只剩 **+2%**（因收益太小，未进最终方案） |
| **查询改写（本场最大的单项收益）** | VLM 把（图 + 问）改写成**不依赖图片的自足文本 query**，再去文本索引检索 | 见下表 |
| 检索 | 预切好的网页块 + `bge-large-en-v1.5` + `BGE-reranker-v2-m3` | — |
| **自检拒答** | SFT → DPO → GRPO 三段；奖励 `+k / 0 / −1`（对 / 不知道 / 错），k=1 时期望回报恰等于赛事评分 | DPO 更保守（missing 70–90%）、GRPO 更敢答（60–80%）、**两者按域/等价类 ensemble** |
| 多轮 | **只用 last-step context**（作者实测：给 ground-truth QA 时，单步上下文与全上下文效果几乎一样） | — |

**查询改写的四个版本对照（Task 2 上下文「能答对」的潜在分）**：

| 改写方式 | 潜在正确率 |
|---|---:|
| 不改写 | ≈33% |
| Llama 3.2-VL 改写 | ≈40% |
| **GPT-4o 改写** | **≈46%** |
| GPT-4o 改写（作弊版：把标准答案喂进去） | **≈60%** |
| 蒸馏后的 Llama（SFT） | ≈44% |

⇒ **「把图片信息写进 query」这一件事值 7～13 个点，是它所有工程里收益最大的单项。** 而它想做的 RL 版改写**失败了**（作者原话：DPO / GRPO 都没超过 SFT 检查点，因为「due to the lack of sufficient internal knowledge, the space for further improvement through RL is limited」）。

**它自己写的失败**（这段比成功更值钱）：
- checkpoint ensemble 本地大幅提升、**线上崩**：「Our enumeration results show huge improvements locally, while it turns out to be heavily overfitting… the less selection is made, the less overfitting is observed.」
- OCR 没能落地：VLM 做 OCR 生成 token 太多超时；PaddleOCR 在 ego 图上质量不行 ⇒ 最终**不含 OCR**。
- OCR/细粒度实体识别是它自认的两大遗留问题（车品牌型号、植物学名，「state-of-the-art VLMs still can't recall their names」；GPT-4o 只认对 40%，Llama 3.2-VL 只有 20%）。

#### ② Dianping-Trust-Safety（美团）——Task 1 第一（领先第 2 名 52.38%）

【一手】arXiv `2508.10337v2`（全文读完）。

- **底座**：Llama 3.2-11B-Vision-Instruct + LoRA。
- **SFT**：用 **GPT-4.1 蒸馏**——把标准答案喂给 GPT-4.1，让它输出「这题可不可答 + CoT + 答案」，不可答就输出明确拒绝及理由；强制 `<think></think><answer></answer>` 格式。
- **RL**：GRPO（VisualRFT 框架）+ **课程学习**，奖励 = 格式分 + 答案分（1 / 0 / −1，由 GPT-4o-mini 判）。
- **课程三阶段**（这是它赢的地方）：把训练样本按「GPT-4.1 在同样评分协议下能否答对」分 easy/hard，先纯 easy → 再 1:1 → 最后 1:2（贴合真实分布）。
- **检索**：放弃图像检索（作者实测「image search introduced significant noise, sometimes even worse than not using it at all」），只留网页检索；粗排 = `bge-large-en-v1.5` + BM25 + TF-IDF 三路融合 → `bge-reranker-v2-m3` 精排 → top-5。

**它的消融（Table 2，单轮本地集）——全赛唯一把「拒答训练」拆到分子级的表**：

| SFT | RL | 课程 | RAG | Acc | Missing | Halluc | Truthfulness |
|---|---|---|---|---|---|---|---|
| ✗ | ✗ | ✗ | ✗ | 0.197 | 0.085 | 0.718 | **−0.520** |
| ✓ | ✗ | ✗ | ✗ | 0.262 | 0.237 | 0.501 | −0.238 |
| ✓ | ✓ | ✗ | ✗ | **0.059** | **0.909** | **0.032** | +0.027 |
| ✓ | ✓ | ✓ | ✗ | 0.190 | 0.713 | 0.097 | +0.093 |
| ✓ | ✓ | ✓ | ✓ | **0.282** | 0.587 | 0.131 | **+0.151** |

**三阶段逐段（Table 3）**：

| 阶段 | Acc | Missing | Halluc | Truthfulness |
|---|---|---|---|---|
| stage 1（纯 easy） | 0.349 | 0.056 | **0.595** | −0.246 |
| stage 2（1:1） | 0.338 | 0.360 | 0.302 | +0.036 |
| stage 3（1:2，真实分布） | 0.282 | 0.587 | **0.131** | **+0.151** |

⇒ **不加课程学习的 RL 会掉进「奖励黑洞」：准确率从 0.262 崩到 0.059，missing 冲到 0.909**——模型学会了「全部拒答」来避免扣分。作者原话：「a missing rate as high as 90%」。**这是所有想做「让模型学会说不知道」的人必须先看的坑。**

#### ③ Team\_NVIDIA——Task 2 第一

【一手·源码】仓库 `github.com/rbiswasfc/crag-mm` README（2025-07-23 最后更新）：200 行内可读完。
【转述】NTT docomo 开发者博客（2025-12-17）对其方法的复述。

- **VLM 同时当三件工具**：查询改写、重排、VQA——通过**把三个任务拼成一个数据集做多任务微调**（一个 Llama-3.2-11B-Vision 模型），8×A100 训练 1.5 小时。
- **后处理拒答**：VLM 输出的首个 token 若为 “I” 的概率超过阈值，就强制输出 “I don't know”（【转述】docomo 博客；README 未写这条，**待核**）。
- **秘密武器**：用 NVIDIA 自研的 **RAGAS**（RAG 专用开源评测库）搭本地评测，先与线上人工评分对齐再调参（【转述】docomo 博客）。
- 公开产物：微调模型 `rbiswasfc/aicrowd-kddcup-v9`、SFT 数据集 `rbiswasfc/kddcup-sft-datamix`、图片集 `rbiswasfc/kddcup-sft-images`。

#### ④ cruise / CRUISE（UNSW）——Task 1 第三，**全程不训练**

【一手·摘要+仓库】arXiv `2507.20136` 摘要 + README（全文 HTML 未取到，**只读到摘要**）。

四段式，**核心是验证而非检索**：轻量路由（判断要不要外部检索，省时）→ 查询感知的检索与摘要 → **双路生成**（RAG 接地路径 + 纯模型先验路径，两路互校）→ **验证与定稿**（self-consistency + 结构化 **Chain-of-Verification**）。
作者自述定位：「prioritizing factual accuracy and truthfulness over completeness」「training-free framework with no additional training or fine-tuning」。

⇒ **这条最值得抄的是「training-free 也能拿牌」**：在幻觉罚分重的评分下，**保守的验证流程可以替代训练**。

#### ⑤ y3h2（电通大）——第 5 名，方法最「异类」

【一手】arXiv `2510.14330v2`（全文读完）。

- **完全不用外部检索**，就在官方 baseline 上加一个**幻觉检测过滤器**：取 VLM 每层的 hidden_state 与每个 attention head 输出，各训一个**逻辑回归**判「是不是幻觉」，按 F1>0.5 筛出 7 个 hidden state + 58 个 head（共 65 个），取均值集成；非幻觉概率 < 0.65 就强制输出 "I don't know"。
- 结果（单轮）：基线 Acc 0.207 / Halluc 0.735 / Truth −0.528 ⇒ 加过滤器后 Acc **0.082**（−61%）、Halluc **0.045**（−94%）、Truth **+0.036**。
- 它试过并被否掉的：Answerability Check（−0.039）、logprob 阈值（−0.021）。

⇒ **这是「宁可全拒答也要不编」的极端标本**：准确率砍六成，靠幻觉砍九成翻正。**它的存在证明：在这套评分下，拒答的收益远大于答对。**

---

## 五、跨两年的技术路线归纳（这次调研的主产物）

把六支上榜队 + 官方基线摆在一起，**赢法只有 5 条**，其余全是现成件：

| # | 路线 | 谁在用 | 有多大用（有数的才写数） |
|---|---|---|---|
| **1** | **拒答 / 可答性判别**（训练式：SFT 重标、DPO、GRPO+课程、幻觉探针；非训练式：CoT 三段自问、self-consistency、阈值过滤） | db3(24/25)、MARAGS、Dianping、y3h2、cruise、APEX、dRAGonRAnGers | **最大单项**：MARAGS 重标让 CRAG 分从 −0.204 → +0.186；Dianping 课程学习让 truthfulness 从 +0.027 → +0.151；y3h2 幻觉率 −94% |
| **2** | **查询改写 / 把多模态信息写进 query** | db3(25) 的 merged query rewrite；Dianping 的 LLM 选查询；ToT 各队 | db3：33% → 46%（GPT-4o）→ 44%（蒸馏后可用版） |
| **3** | **结构化源的正则化封装**（把官方 API 包成带条件/排序/聚合的一层） | db3(24) 独有；APEX 的「逐步拆分」是它的反面（手工规则） | db3 靠这一项拿走 Task 2/3 的 +4.2 / +6.5；APEX 去掉实体匹配 −9.78、去掉时间抽取 −12.77 |
| **4** | **按域/按动态性路由，不同域接不同数据源** | APEX（sports/finance 只用 API）、db3(24)、db3(25) 8 域分类器 | APEX：sports/finance 直接答「不知道」以止损 |
| **5** | **分块与解析的工程细节**（parent-child / HTML 树 BFS / 表格单独抽 / 5W1H 找问题句） | db3、md_dh、ElectricSheep | APEX 解析器对照：newspaper 11.82 vs beautifulsoup 5.11（**2.3 倍差**）；ElectricSheep 优化的分块抽取把分从 −67.6 抬到 −52.6 |
| — | **检索器选型 / 重排模型选型** | 全员 | **不是胜负手**：MARAGS 四种检索器 accuracy 0.274～0.328；APEX 去 rerank 只 −2.05 |

### 5.1 一条贯穿两年的反向结论

> **没有任何一支上榜队做了端到端训练。** 组织者原文：「**No team trained the overall pipeline in an end-to-end fashion.** Instead, each component is optimized separately, where sub-systems are tailored to the specific tasks or question types.」【一手】组织者论文 §D。

### 5.2 组织者自己总结的四条拒答手法（原文照抄）

「The main strategies that the winning solutions adapt to reduce hallucinations are a combination of **chain-of-thought prompting, explicit confidence estimation, supervised fine-tuning, and manual rules**.」
其中 manual rules 的解释值得抄进我们的设计原则：「Some teams opt to **avoid answering dynamic questions all together** to prevent getting penalized with hallucinated answers.」

### 5.3 官方承认的评测漏洞（这是「能不能信这些分数」的前提）

【一手】组织者论文 §E.3：
- Phase 1 用公开测试集做榜，**很快被刷到 100% 准确**——有人把 (query, answer) 建了映射表。后改用私有集。
- **有队伍攻击 auto-eval 提示词**，「we also noticed some submissions that tried to fool the auto-evaluator achieved very high scores」。
- 对策：私有测试集 + 隐藏 auto-eval 提示词 + 推理时断网。
- auto-eval 与人工的一致性：**前十名 9 队里有 6 队重合**（即 1/3 不一致）；auto-eval 本身准确率 Llama-3-70B 99%、GPT-3.5 94.5%。

⇒ **读这些榜单时的正确姿势**：名次可信（最终由人工定），但**具体分数不可跨年直接比较**（评分口径、语料、硬件每年都变）。

---

## 六、反证检索（强制）

**搜了什么词**（2026-11-05）：
1. `RAG 竞赛 被高估 质疑 benchmark 刷分 CRAG leaderboard criticism`
2. `KDD Cup CRAG 比赛 方案 过拟合 leaderboard 不可复现`
3. `"KDD Cup CRAG" 2024 "2,500 participants" OR "384 teams" OR "5,600 submissions"`（用于交叉核对规模数字）

**搜出什么**：
- **命中且被采纳**：组织者自己承认的刷榜与提示词攻击（见 §5.3）——**这是最硬的一条反证，且来自官方**。
- **命中且被采纳**：db3 2025 自己承认 checkpoint ensemble「locally huge improvements / online heavily overfitting」。
- **命中但未采信**：一篇 2026 年博客「CRAG Two Years On: The Score That Scores Silence Above a Wrong Answer」批评该评分「奖励沉默胜过正确答案」。**观点与我独立算出的读数一致（y3h2 砍掉六成准确率仍翻正），但它本身是二手评论，只作旁证，不作依据。**
- **未命中**：没有找到任何一份对 CRAG 榜单的正式复现失败报告；也没有找到对 db3 / APEX / MARAGS 方法的公开质疑。**这一项如实记为「0 条」。**
- **规模数字的口径差异（已核实并保留）**：官方论文写 5,600+ submissions，AIcrowd 赛事页计 6,323——**两者都对，只是抓取时点不同**（论文在赛后不久定稿）。此类差异不抹平。

---

## 七、未查证清单（明确没做到的）

| 项 | 状态 | 原因 |
|---|---|---|
| vslyu-team（2024 Task 3 第三）的技术路线 | **未查证** | 无任何公开报告/仓库；官方 spotlight 未覆盖 |
| dRAGonRAnGers 报告全文 | **只到二手** | OpenReview PDF 被 Cloudflare 拦（`openreview.net/pdf?id=G4Ei2QlKnv` 与 `api2.openreview.net` 均 403/需人机验证） |
| Team\_NVIDIA 的「首 token 概率阈值拒答」 | **待核** | 只见于 docomo 技术博客（转述），README 未载 |
| cruise 报告的完整方法与数字 | **只读到摘要** | arXiv HTML 未取；仅摘要 + README |
| CRAG-MM 2025 各队「人工评测 vs 自动评测」的分差 | **只到榜单分** | 官方未公布逐队人工明细，仅公布最终名次与总分 |
| AcroYAMALEX / BlackPearl / otonadake / NEC\_AI\_ROCKETS 等分项冠军的方法 | **未查证** | 本轮未展开；若有需要单列一轮 |

---

## 八、两面账（规矩五）

### 账一：覆盖自查

| 问题 | 数字 |
|---|---|
| 候选池有多少？ | CRAG 2024 上榜队 **12 队**（3 任务 × 前 3，去重后 7 队）+ CRAG-MM 2025 上榜队 **≥10 队** + 分项冠军 **≥7 队** ⇒ 约 **24 队** |
| 我登记了几个？ | 本文详评 **9 队**（db3×2、APEX、ElectricSheep、md_dh、dRAGonRAnGers、Dianping、Team\_NVIDIA、cruise、y3h2） |
| `depth` 分布 | `fulltext` **6**（db3×2、APEX、ElectricSheep、MARAGS、Dianping、y3h2 中的 6 篇全文）｜`source` **1**（NVIDIA=README+代码仓）｜`readme` **2**（cruise、dRAGonRAnGers）｜`metadata` **1**（vslyu=仅名次） |
| 已知遗漏 | vslyu-team、BlackPearl、AcroYAMALEX、otodonadake、gogoogo、NEC\_AI\_ROCKETS、dummy_model、bumblebee7、Future、StarTeam、Riviera4、ETSLab —— **12 队** |
| 反证命中几条 | 3 条（官方自承刷榜/提示词攻击、db3 自承过拟合、二手博客的评分批评），正式复现失败报告 **0 条** |

### 账二：复核总账（抽查 ≥10%）

抽查了 **14 条**关键事实（占全文可核数字约 60 条的 23%）：

| 结论 | 条数 |
|---|---|
| 复核后确认 | **13** |
| 复核后发现错 | **1** |
| 无法核实 | **0** |

**唯一一条错**：初稿据搜索摘要写「CCKS 2024 吸引 2,400+ 队伍、近 5,300 人」并打算与 CRAG 的 2,500+ 参赛者直接对比；复核发现官方原文「2,400+ teams and nearly 5,300 **participants**」——**2,400 是队伍数、5,300 是人数**，与 CRAG「2,500+ participants / 384 teams」的「participants」口径不同。**已按 team 对齐重写 §二表格。**
⇒ **本轮错误率 1/14 ≈ 7.1%。**

---

## 九、边界声明

- **不保证运行时行为**：所有「它的方法是什么」均据论文方法节或 README，**没有一队在本地复跑**（`depth: tested` = 0）。
- **不保证数字全读过原文**：cruise 只读摘要、dRAGonRAnGers 只读二手、NVIDIA 的拒答阈值只读博客转述，已在 §七逐条标明。
- **跨年不可比**：2024 与 2025 的语料、硬件（4×T4 30 秒 vs L40S 10 秒）、评分（多轮加早停）都变了，**分数只在同年内可比**。
- **2025 榜单存在官方承认的登记混乱**：论坛里 AcroYAMALEX 与 Dianping 两队当场指出 task2/task3 提交号疑似错位，组织者答复「Task 2 and 3 have different number of interactions, so it's unlikely these two are mis-placed as the total counts did match」。**该争议未闭环，本文沿用官方最终表。**
