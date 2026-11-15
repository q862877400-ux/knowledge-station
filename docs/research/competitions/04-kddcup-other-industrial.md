# KDD Cup 其他赛道 + 企业级 RAG 赛：Amazon KDD Cup 2024 与 TrustBit Enterprise RAG Challenge（D 线）

> **抓取日**：2026-11-05。证据分档：【一手】官方赛道页、官方论文、队伍技术报告、排行榜原文、代码仓库；【转述】机构通稿、二手转述；【推断】本文自行判断。查不到的写“未查证”，不补编。
>
> **结论先行**：这两条线共同给出一个很硬的排序：**Amazon KDD Cup 2024 证明“多任务电商”赢法不是检索，是自建训练集 + 大模型微调 + 多 LoRA 集成与 wise-ft**；**TrustBit Enterprise RAG 证明“企业文档问答”真正的分水岭不是 rerank，而是“路由到正确公司/文档 + 页级证据回链 + 按答案类型路由提示 + 无据 N/A”**。两条线都没有证明“更大候选池”或“更强的 reranker”是胜负手。

---

## 1. 规模对比表

| 竞赛 | 年份 | 用户/参赛者 | 队伍数 | 提交/问题数 | 赛道数 | 出处 |
|---|---:|---:|---:|---:|---:|---|
| KDD Cup CRAG | 2024 | 3,212 | **384** | 6,323 | 3 | 【一手】AIcrowd 赛事页统计（**由 Lead 提供**） |
| KDD Cup CRAG（官方论文口径） | 2024 | >2,500 participants | 384 | >5,600 | 3 | 【一手】组织者论文 IEEE Data Eng. Bull.（**由 Lead 提供**） |
| KDD Cup CRAG-MM | 2025 | 1,067 | **256** | 4,927 | 3 | 【一手】AIcrowd 赛事页统计（**由 Lead 提供**） |
| **Amazon KDD Cup 2024（Shopping MMLU / 多任务购物）** | 2024 | **1,862** | **508** | **9,095**（T1 2,325 / T2 2,086 / T3 2,103 / T4 1,453 / T5 1,128）；ShopBench ≈**20,000 questions / 57 tasks** | **5 tracks** | 【一手】AIcrowd 赛事页统计（HTML 解析）+ CityUHK 通稿（508 teams / 1,499 entrants，官方数字口径不同，见反证）+ NVIDIA 冠军报告 |
| **TrustBit Enterprise RAG Challenge Round 1** | 2024 | 未查证 | 未查证 | 公共池 **7,496 份年报 / ~46GB**；test run **20 files / 40 questions** | 1 | 【一手】官方 GitHub README |
| **TrustBit Enterprise RAG Challenge Round 2** | 2025 | 未查证 | 榜单列 **43 teams**（非正式总榜） | **100 reports**（部分上千页）+ **100 questions**；2.5 小时解析/建库 | 1 | 【一手】官方 GitHub README + TimeToAct leaderboard |
| TrustBit ERC 2025 团队榜（**非正式总榜**） | 2025 | 未查证 | **43** | 含 ground truth 公布后补交的 experiment | 1 | 【一手】TimeToAct 官网写明它包含赛后补交，视为“unofficial overview” |

> **口径提醒**：TrustBit 的 43 队是**网页榜单可见行数**，不是官方最终参赛队伍数；本文不把它当官方规模数字。Amazon 的 508 队与 CityUHK 通稿一致；AICrowd 页 user 数与 CityUHK entrants 口径不同，不能混用。

---

## 2. Amazon KDD Cup 2024：Multi-Task Online Shopping Challenge for LLMs

### 2.1 赛道设置（这不是纯 RAG 赛）

【一手】NVIDIA 冠军报告 arXiv 2408.04658：

- **ShopBench** 含 **57 tasks / 约 20,000 questions**，只给参赛者 **96 个开发问题（18 个 task）**；测试集隐藏，模型在 **4× T4 16GB** 上运行。
- **Track 1 购物概念理解**：品牌/产品线/属性等。
- **Track 2 购物知识推理**：产品包总量、互补/替代关系等。
- **Track 3 用户行为对齐**：点击流等隐性行为信息。
- **Track 4 多语言能力**：概念理解与行为对齐跨语言。
- **Track 5 Overall**：全量综合。
- 题型：多选（accuracy）、排序（nDCG）、NER（Micro-F1）、检索（Hit@3）、生成（ROUGE-L/BLEU/embedding cosine）。
- Phase 2 题目更难，GPU 从 2×T4 提到 4×T4；每个 track 时限：**70 / 20 / 30 / 20 / 140 分钟**。

### 2.2 头部榜单（最终分）

【一手】NVIDIA 报告 Table 3、CityUHK 官方通稿、AIcrowd 获奖公告：

| 队 | Final（名次和，越小越好） | T1 | T2 | T3 | T4 | T5 | 名次 |
|---|---:|---:|---:|---:|---:|---:|---|
| **Team_NVIDIA** | **5** | **0.833** | **0.791** | **0.746** | **0.761** | **0.788** | 5 tracks 全部第一 |
| **AML_Lab@CityU / AML666** | 13 | 0.825 | 0.781 | 0.728 | 0.715 | 0.782 | T1/T5 第二；T2/T3/T4 第三 |
| **shimmering...** | 18 | 0.824 | 0.747 | 0.713 | 0.735 | 0.763 | 次级头部 |
| CM_RLLM | 29 | 0.823 | 0.728 | 0.722 | 0.690 | 0.773 | 次级头部 |
| ZJU_AI4H | 33 | 0.791 | 0.784 | 0.694 | 0.706 | 0.746 | 次级头部 |

### 2.3 第一名 Team_NVIDIA：赢法是“没有训练集，就把训练集做出来”

【一手】冠军报告全文：

**四段拆解**

| 段 | 做法 |
|---|---|
| **检索** | 不是本赛制核心。许多任务本身就是“给定候选列表内做检索/排序/多选”，候选在 prompt 里；没有跨文档检索器。 |
| **融合重排** | 用 **task type 提示**做路由 + **Logits Processors** 约束输出（多选/排序/检索只许数字与逗号；NER 强化 prompt token 的 logit）。多 LoRA adapter 集成：v7/v8/v7b/v9b 两个 adapter 按 track 加权合并。 |
| **生成** | **Qwen2-72B-Instruct** 按 track 单模型；系统提示里标注当前 5 类 task type，用规则分类器在推理时填入；训练只算 answer token loss。 |
| **自检/拒答** | 无拒答模块。**自检由“wise-ft”承担**：`W_wise = W_base + alpha * W_A * W_B`，插值 base/finetuned，alpha 逐 track 调优，抗分布漂移。 |

**训练集构建（冠军最值得抄的部分）**：

1. 把 Amazon-M2、Amazon Reviews 2023、NingLab/ECInstruct、ESCI-data、MMLU、Alpaca-Cleaned 等**公开数据改造成 ShopBench 格式**；
2. 用 **LLaMA 3 70B** 和 **GPT-4** 做数据增广/合成（补 product type、category、attributes 等标签）；
3. 明确造了 26+ 种 synthetic/新任务，包括“反向 ESCI”（给定 product 选 query）等；
4. 总训练量约 **502,435**（附录表逐项汇总），主 adapter 417k/462k。

**微调与推理**

- 8×A100 80GB，QLoRA 4-bit，bf16，训练约 500k example/24 小时；超参 LR 2e-4、cosine、QLoRA r=64/alpha=32/dropout=0.05。
- 4-bit AWQ 量化（用 96 个 dev questions 校准）+ vLLM 压进 4×T4 16GB。
- 消融：Qwen2-72B 零样本已能拿 T5 第 4（0.7486）；微调后 **0.7883**，逐 track 提升明显；**双 adapter 集成再 +0.001~0.004**。
- **论文自己的反证**：adapter 集成与 wise-ft 的增益“在 T1/T3/T5 明显，在 T2/T4 较弱”；Logits Processor 在 Phase 2（更大模型）重要性下降。

> **定位**：这是“多任务 LLM 能力赛”，不是 RAG 赛。NVIDIA 冠军路线对知识库/RAG 的直接可迁移性低；可借的只有 **“把私有任务形态反向构造成公开数据 + 输出格式约束（Logits Processor 相当于本仓的‘条文号只输出标准号格式’）”**。

### 2.4 第二名 AML_Lab@CityU：只有摘要可查

【一手】官方通稿与 OpenReview 摘要：
- 5 赛道全部前三，总排名第二（2/508），T1/T5 第二，T2/T3/T4 第三；
- 技术路线摘要只写三部分：**base model selection、pre-trained model quantization、prompt design**；
- 因此**不得据此说它用了 RAG/检索/重排**——证据只够支撑“模型选择 + 量化 + prompt 设计”这一层。

### 2.5 规模判断

- 508 队 / 1,499 entrants（CityUHK 通稿）；AIcrowd 页显示 **1,862 users / 508 teams / 9,095 submissions**。
- 按**单赛道队伍数**它与 CRAG 的 384 队同量级；按“任务种类”则 ShopBench 的 57 tasks 是全场最宽的。
- **不是知识库/RAG 竞赛主体**：候选在题内、问题在题面、无外部检索库。它对“工业界广泛关注”的意义在于：**LLM 多任务能力赛的封顶形态**。

---

## 3. TrustBit Enterprise RAG Challenge：真正与本仓最贴的“工业文档赛”

### 3.1 赛道规则（先看规则，再看方案）

【一手】官方 GitHub README：

- 语料：公开年报 PDF；公共池 **7,496 files / ~46GB**，带公司名和 sha1。比赛时按 drand 公共随机种子抽 subset，并用题生成器随机出题——保证无人提前知道文件与题目。
- 流程：系统先 ingest（几小时窗口），再收到问题列表并回答。
- **答案必须带页级引用**：`SourceReference{ pdf_sha1, page_index }`，其中 `page_index` 是 **PDF 物理页号（zero-based）**。这是本赛制最关键的约束：**不是“引用了某文档”，而是“必须指到第几页”**。
- 题型四类：`number`、`name`、`names`、`boolean`；允许 `N/A`。若公司不在 PDF 里、或题无意义、或上下文不够真人也答不了，**必须 `N/A`**。README 原文：“If company data is not available…system must respond with `N/A`。”“A bad RAG system will hallucinate a plausible answer, a good RAG system will respond with ‘N/A’.”
- **计分**：`Score = G + R/3`，理论上限 **133.3**；`R` = 引用页号与 ground truth 的匹配，`G` = 答案与 ground truth 的匹配。**检索分数与生成分数分开**（R 满分约 33.3，G 满分 100）。【一手】TimeToAct 排行榜说明。

### 3.2 头部榜单（2025，含赛后补交实验）

【一手】TimeToAct 团队榜「R&D Experiments」列；网页明确说明该榜是**非正式总览**（含 ground truth 公布后提交的 experiment），但**是当前唯一公开的前列技术档案**：

| 名次 | 团队 | Experiment | Time | R | G | Score | 模型/一句话架构 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | **Ilya Ris** | Dense Retrieval; Router; LLM reranking; o3-mini | **49 min** | 83.8 | **81.8** | **123.7** | Docling 改版解析 + 每公司独立 FAISS + LLM 重排 + 路由 + SO CoT |
| 2 | **Emil Shagiev** | **LLM_Search** | 55 min | **86.3** | 78.5 | 121.6 | **不用向量**：query 扩写 → 快速 LLM 检索 → 强 LLM 回答 → finalize |
| 3 | **Dmitry Buykin** | Dynamic Structured Output with SEC EDGAR Ontologies | 8 hours | 81.4 | 76.8 | 117.5 | **不用向量**：ontologies 做 query 扩写 + CBOW 多次运行多数选择 |
| 4 | Sergey Nikonov | main v2 | 30 hours | 85.1 | 73.9 | 116.4 | 每题把**全部页面**喂给 gpt-4o |
| 5 | ScrapeNinja.net | fixed multiple companies search | 23 hours | 82.6 | 71.2 | 112.5 | Node.js + pgvector |

### 3.3 第一名 Ilya Ris：完整四段（这条直接抄）

【一手】冠军本人长文（abdullin.com，2025-03-25）+ 其 GitHub `IlyaRice/RAG-Challenge-2`：

**1）解析（这是分水岭）**

- 试了约 24 种 PDF parser，最终选 **Docling**；但**改了它源码**，保留页号与全部元数据，输出 JSON 再二次拼 Markdown（表格转 HTML 结构保留合并单元格与子标题）。
- 清洗用十几条正则处理乱码；凯撒密码式字体编码乱码直接走 OCR。
- GPU 加速：4090 按小时租，100 份报告（约 15,000 页）**40 分钟**解析完。
- **表格序列化**他试了（把大表变成“subject_core_entity + information_block”独立句组），但**最终获胜配置没有用它**，因为 Docling 解析后检索与 LLM 已能处理表格，再加文本反而降 SNR。⇒【推断】“表格序列化好”不是普遍真理，这场它的实测是负的。

**2）索引与检索**

- 切分：**递归 splitter，300 tokens/chunk，overlap 50 tokens**，每个 chunk 带 `page_index` 元数据。
- **每公司一个独立库（100 dbs，1 doc = 1 db）**，用 FAISS **IndexFlatIP**（不压缩、暴搜，精度最大）；embedding `text-embedding-3-large`。
- 检索：query 向量化 → 每库 top-30 chunks → **去重映射回整页**（parent-page retrieval）→ LLM 重排页面。
- **LLM reranking**：GPT-4o-mini 每批 3 页一次打 `relevance_score`（0.0–1.0，带 reasoning 字段的 Structured Output）；最终分 = `0.3 * vector + 0.7 * llm`；只保留 **top-10 pages**。他说成本 < 0.01 美元/题。
- 他明确**放弃了 hybrid BM25+向量**（“在最简实现里常降质”）和 cross-encoder reranker（API 渠道麻烦）；但这是他的取舍，不是普遍结论（第 6 名 xsl777 用 multi-query + hybrid 反而拿到 110.9）。

**3）生成（路由是关键，不是模型）**

- **按公司路由**：用 `re.search()` 在已知公司名列表里匹配问题→选库。库从 100→1，搜索空间缩小 100 倍。
- **按答案类型路由提示词**：`number / name / names / boolean` 四套提示分开，**一条提示里规则越少越好**（“8 条规则已危险”）。数字题里专门写了货币/千/百万换算（4970.5 in thousands → 4970500）、括号负数、币种不一致→`N/A` 等指令。
- **比较题拆子题**：先问 LLM 生成子问题（每公司一问），分别走正常管线，再把两个数值带回原题。
- **SO CoT（Structured Output + CoT）**：schema 固定四字段 `step_by_step_analysis / reasoning_summary / relevant_pages / final_answer`；few-shot one-shot 例尤其重推理结构；写 SO Reparser（schema.model_validate 失败就回炉），把 8B 模型 schema 合规率打满。
- **拒答**：把“指标是否兼容”的判断写进 CoT 指令（context 里是 net property 而问题要 cost → N/A），而不是只靠“要谨慎”的劝诫。他说“劝模型谨慎”不稳定，**教模型从不同角度核对指标兼容性**才稳。

**4）成绩与消融**

- R 83.8 / G 81.8 / Score **123.7** / **49 分钟**。
- 同模型（Llama 3.3 70B）只差**几分**；Llama 3.1 8B 也能进前 80%。⇒【推断】在这场，**提示与管线 > 模型大小**。

### 3.4 第二名 Emil Shagiev：不用向量也进前二

【一手】TimeToAct 榜单架构说明：`LLM_Search` =
query 扩写 → 用快速廉价 LLM 检索相关页 → 强 LLM 回答 → finalize。**没有 embedding/vector DB**。
R **86.3（全榜最高）**、G 78.5、Score 121.6。⇒【推断】在“每题必到页号”的评分结构下，**R 分对“页选择”敏感而非“向量质量”**；只要能稳定定位页，生成侧补强即可。

### 3.5 第三名 Dmitry Buykin：ontology 扩写 + 多次运行 CBOW 投票

【一手】TimeToAct 榜单：**不用 embeddings/vector DB**；SO/CoT + **SEC EDGAR ontologies 做 query expansion**；**CBOW similarity 做多次运行的多数选择**；对 PDF 质量启发式做 OCR 输入优化；用 synthetic tags 稳定页检测。
R 81.4 / G 76.8 / Score 117.5。⇒【推断】**ontology 扩写与“多次运行取多数”可替代向量检索**，尤其适合本仓「法规/标准」这种强本体场景。

### 3.6 而他为什么能赢：四条机制（本仓可直接建立）

| 机制 | 证据 | 本仓对应 |
|---|---|---|
| **按公司/文档路由**（regex 匹配实体→选库） | Ilya：“搜索空间缩小 100 倍” | 按法域/标准体系/文件路由，而不是全库混检 |
| **父页检索**（chunk 命中→回整页） | Ilya：top chunks 只作指针，整页进上下文 | chunk 命中→回条文整页/整表 |
| **LLM 重排按 0.3 向量 + 0.7 LLM 加权** | Ilya 权重；升级到 0.7 侧重语义判断 | top-30 出池后 LLM 精排，阈值实测 |
| **无据 N/A + 指标兼容性 CoT** | README + Ilya 文章示例 | 无据拒答 + 口径核对（本仓已有“口径核查”） |

---

## 4. 反证

**搜了什么词**：
1. `Enterprise RAG Challenge 被高估 质疑 争议`
2. `Amazon KDD Cup 2024 刷榜 overfitting 不可复现`
3. `TrustBit Enterprise RAG 2025 参赛规模 submissions 队伍数`

**搜出什么**：
- **Amazon**：NVIDIA 报告自承 LoRA 集成增益只有 **+0.001~0.004**，且 Logits Processor 在 Phase 2 重要性下降——“拼技巧”空间已收窄；AML 报告只给摘要，三部分（base model selection / quantization / prompt design）**无法拆细到检索/生成归因**，只能记名次。
- **TrustBit**：官方榜单自承包含 ground truth 公布后补交的 experiment，**不可作正式名次**；且 Emil 的 `LLM_Search` 证明“向量不是必需”，Dmitry 的 ontology 路也证明同一结论。⇒ **这场不能用“用了向量/没用向量”评价系统，只能看 R/G 分。**
- **规模的反证**：TrustBit 公共池 7,496 份/46GB 是**可的全集**，但实际 test 是**抽 100 份 / 100 题**，所以它的强度是“小规模严进严出”的，不可外推到十万文档。

**未搜到**：针对 Ilya 方案的公开复现失败报告（0 条）。

---

## 5. 未查证清单

| 项 | 状态 | 原因 |
|---|---|---|
| TrustBit ERC 2025 官方正式名次/提交数 | 未查证 | 当前公开榜自承含赛后补交，属非正式总览 |
| TrustBit ERC 2024 正式榜单 | 未查证 | Round1 文件夹在仓库内，未单独提取名次表 |
| Amazon KDD Cup 2024 第二名 AML 的细粒度方法 | 只到摘要 | OpenReview PDF 被人机验证挡下，仅摘要可读 |
| Amazon KDD Cup 2024 总参赛“提交数” | 未查证 | 官方只给 508 teams / 1,499 entrants 与题量，未给 submissions |
| TrustBit 的“两个奖金类”（small vs full）技术细节 | 未查证 | 冠军博客称赢了 both prize categories，但榜单页未对应解释 |

---

## 6. 边界声明与 depth 分布

- **depth 分布（本线）**：`fulltext`(Amazon 冠军报告全文、TrustBit 冠军长文+官方 README)、`source`(TimeToAct 榜单逐队架构+实验日志)、`readme`(Ilya GitHub README)、`metadata`(AML 第二名只到名次与摘要)、`tested`=0。
- **不承诺**：Amazon 的“无训练集”设定不可外推到有训练集场景；TrustBit 的 100 份文档不可外推到大规模企业知识库；Amazon 的 leaderboard 增益小于 0.004 的部分已在反证中标注。
- **本仓可用性**：TrustBit 的 **页级回链 + 无据 N/A + 路由** 与本仓“条文级定位 + 拒答”同构；Amazon 的**输出约束（Logits Processor）**对应本仓“条号只输出标准号格式”。
