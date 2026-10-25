# 调研总目录（十条线 · 对象数 · 文件 · 结论）

> 2026-10-25。**这是本调研的唯一索引**：每条线查了多少对象、分布是什么、结论落在哪份文件。
> 统计口径见 §三（**268 是「登记对象数」，不是「读过的文档数」**）。

## 一、总表

| # | 线 | 文件 | 登记对象 | 分布 | 结论档位（借鉴/可选/不适用/待核） | 正文行数 |
|---|---|---|---:|---|---|---:|
| A | 开源知识库/RAG 平台 | `10-platforms.md` | **19** | 平台 15 + 框架 4 | 2 / 3 / 12 / 2 | 188 |
| B | 文档解析与版面 | `20-parsing.md` | **18** | 开源 12 + 商业 6 | 1 / 3 / 8 / 6 | 200 |
| C | 检索底座与索引 | `30-indexing.md` | **21** | 搜索引擎 5、向量库 3、嵌入式 3、重排 3、迟交互 2、其他 5 | 4 / 2 / 13 / 2 | 213 |
| D | 论文前沿 + 竞赛冠军 | `40-papers.md` | **26** | 竞赛/排行榜 14 + 方法论文 12 | 12 / 3 / 7 / 4 | 269 |
| E | 商业产品 | `50-commercial.md` | **20** | 云 RAG 4、法律 AI 4、云搜索 3、中文法律库 3、其他 6 | 9 / 7 / 3 / 1 | 214 |
| F | 中文/法律/图谱专用 | `60-cn-legal-kg.md` | **16** | 开源 9、数据集 2、论文 2、榜单 1、政务数据 1、标准 1 | 7 / 1 / 6 / 2 | 240 |
| G | 竞赛与评测赛道 | `70-competitions.md` | **44** | 持续榜 25 + 单次比赛 19 | 16 / 11 / 13 / 4 | 307 |
| H | 工业界生产实践 | `75-industry-practice.md` | **35** | 公司博客 12、厂商案例 5、公司论文 4、演讲 4、产品文档/营销 6、其他 4 | 15 / 14 / 3 / 3 | 324 |
| I | 社区与社交媒体信号 | `78-community-signals.md` | **45** | GitHub issue 22、论坛 5、厂商案例 5、博客 4、HN 6、仓库 3 | 32 / 0 / 7 / 6 | 319 |
| J | 学术前沿扩面 | `80-academic-frontier.md` | **24** | 论文 24 | 13 / 7 / 3 / 1 | 313 |
| — | **合计** | 10 份正文 + 10 份 jsonl | **268** | — | **111 / 51 / 75 / 31** | **2,587** |
| — | 复核总账 | `AUDIT-2026-10-25.md` | **88 条复核** | 确认 74 / **错误 11** / 无法核实 3 | — | 340 |
| — | 综合判断 | `90-synthesis.md` | — | 20 条结论 + 10 项改动形状 + 5 条自我更正 | — | 258 |

## 二、每条线具体查了什么

### A · 开源平台（19）
RAGFlow、Infinity、Dify、FastGPT、MaxKB、AnythingLLM、Onyx(Danswer)、Verba、Quivr、Khoj、Kotaemon、Open WebUI、R2R、Morphik、WeKnora、LangChain、LlamaIndex、Haystack、txtai。
**最硬的一条**：18 个平台里 **0 个**有"条款"这个一级公民，引用粒度上限是文档/页/chunk；中文法规效力状态 **0 个**有机制。

### B · 解析（18）
MinerU（含 4.0）、Docling、Marker、PP-StructureV3、olmOCR、Unstructured（以上深读）+ PDF-Extract-Kit、Nougat、Chunkr、Zerox、MarkItDown、DeepSeek-OCR（简评）+ 商业 Mistral OCR、Reducto、LlamaParse、Mathpix、Azure DI、Google DA。
**最硬的一条**：只有 MinerU/Docling/Paddle/Marker 四家做到"结构级"表格；**18 个项目 0 个**做中文国标排版。

### C · 索引底座（21）
Elasticsearch、OpenSearch、Vespa、Milvus、Qdrant、Weaviate、pgvector、LanceDB、Typesense、Meilisearch、Tantivy/Quickwit、SQLite FTS5/sqlite-vec、迟交互（ColBERT/ColPali/ColQwen2）、重排器（bge/jina/Cohere）、FAISS、USearch、hnswlib、Chroma。
**最硬的一条**：换库换不来正确性；出路是两段式（先收窄候选，再算精确距离），不是换底座。

### D · 论文与竞赛（26）
TREC ToT 2023/2024/2025 三届冠军 + YaleNLP / IISER-K / Webis×2 / UAmsterdam / DS@GT 五份参赛论文 + KDD Cup CRAG / COLIEE / LeCaRDv2 / CCKS / CCF BDCI + 12 篇方法论文（Contextual Retrieval、Late Chunking、RAPTOR、GraphRAG、LightRAG、HippoRAG、Sufficient Context、OTT-QA、FeTaQA、ALCE、GuRE、公式检索）。
**最硬的一条**：冠军三年换了两茬路线，共同点只有"检索前先加工查询"；**只有方法零件可迁，评测口径不可迁**。

### E · 商业产品（20）
Azure AI Search、Vertex AI Search、AWS Bedrock KB、Kendra、Elastic、Cohere、Pinecone、Glean、Harvey、LexisNexis Protégé、CoCounsel、Spellbook、北大法宝、威科先行、工标库、秘塔、得理法搜、阿里云百炼、腾讯云 ADP、华为云 AgentArts。
**最硬的一条**：**所有规模数字都是配额，不是实测**；最值得看的是工标库的条文级废止三件套。

### F · 中文/法律/图谱（16）
KAG、KAG-Thinker、QAnything、BISHENG、ChatLaw、LaWGPT、DISC-LawLLM、智海-录问、LeCaRD、LeCaRDv2、STARD+GCSR、CAIL、legislation.gov.uk effects、LegalLPP、GB/T 46686.1-2025、verified-chinese-law-kb。
**最硬的一条**：「图谱」投，但**只投薄的那一半**——关系边与状态值钱，通用图数据库与逻辑求解器不值钱。

### G · 竞赛与榜单（44）
TREC（Deep Learning 2019-23、NeuCLIR 2022-24、CAsT、iKAT、RAG 2024-25、RAGTIME 2025、Clinical Trials、**Legal 2006-11**）、NTCIR-18、CLEF、KDD Cup CRAG/CRAG-MM、COLIEE 2025；榜单 BEIR、BRIGHT、MTEB/C-MTEB、MIRACL、OmniDocBench、olmOCR-Bench、DocLayNet、CRAG、RAGTruth、RGB、CRUD-RAG、LongBench、∞Bench、LegalBench、LEXTREME、LEXam、LawBench、CLaw、Legal-DC、SAR、SCT-aerospace、GB/T-Bench；中文赛事 CCIR Cup、CAIL、CCKS、CCF BDCI、天池 AFAC、讯飞、NLPCC。
**最硬的一条**：**TREC Legal 官方结论「多数参赛系统大幅高估自己的召回」**；且「中文国标 × 百万条款 × 引用齐全」这个组合**全世界没有比赛也没有榜单**。

### H · 工业实践（35）
Pinterest、GitHub（Blackbird + Elastic 两案）、Notion+turbopuffer、Uber、Airbnb、LinkedIn、Meta、Microsoft（SPANN/Bing + 金融文档 RAG）、Slack、Atlassian、Shopify、Stripe（查过无）、Sourcegraph、Wikimedia、小红书、阿里×2、字节×2、美团、腾讯、百度、Elastic/Qdrant/Pinecone/Zilliz/Vespa 五家厂商案例、Harvey/Robin/Spellbook/CoCounsel/Luminance、Octus。
**最硬的一条**：瓶颈顺序是**内存 → 过滤 → 索引构建 → 解析**；引用可回溯的行业上限是「段落+页/URL」，**无人做到条款+坐标**。

### I · 社区信号（45）
GitHub issue 22 条（RAGFlow / MinerU / Weaviate / Qdrant / Milvus / Dify / FastGPT / MaxKB / Onyx）、HN 6 条（含 PageIndex 192 分、Wikipedia 向量检索 325 分、sqlite-vec 314 分）、linux.do 论坛、V2EX、掘金、云厂商社区、ure.us 博客、CATARC/TextIn/jlcbk 等中文竞品。
**最硬的一条**：RAGFlow 自己也踩了我们踩过的两个坑（MinerU 坐标空间、引用跨轮复用）；**问"能装多少"的 issue 至今无人答**。

### J · 学术扩面（24）
BRIGHT、Search-R1、GAR 复现、MUVERA、StructRAG、SPLADE-v3、ACID、doc2query 系；RAG-or-LC、DOS RAG、NoLiMa、Dense Contexts；LongCite、ALiiCE、RAGTruth；C-Pack/C-MTEB；LePaRD、LegalBench-RAG、SG-LegalCite、**德国民法典切分实测**；Semantic Chunking 成本、DenseX、AutoSchemaKG、Chunking Methods 评测。
**最硬的一条**：**两条我们没考虑过的范式**——文档侧扩展（doc2query）、重排期沿相似图扩候选（GAR）。

## 三、统计口径（必须看，否则会误读这张表）

1. **268 是「登记对象数」，不是「读过的文档数」**。同一个对象可能只做了元数据检查（README / `gh api`），也可能全文读过——**深度不均**，各线正文的「待核清单」逐条写了哪些只到元数据级。
2. **包含"明确未取到"的占位行**：G 线 44 行里有占位（如 CCKS 冠军方案未取得），如实登记而不是删掉。
3. **`kind` 字段的粒度不统一**：D 线 26 条 `kind` 为空（论文/竞赛混排），C 线按底座类型细分到 12 种——这是各线作者自行判定的，**不能横向比较**。
4. **结论档位是"对我们"的判定，不是对象本身的质量**：`不适用` 多数是"规模或语料不合"，不代表它做得差。
5. **268 个对象一共只核了 88 条外部事实**（见 `AUDIT-2026-10-25.md`）——**错误率 12.5%**。也就是说：**表里每个数字背后，平均还有约 3/4 没被独立复核过**。

## 三、覆盖自查（2026-10-25 按 `research-protocol` 的 L3 硬门槛做，发现 5 处不够透彻）

> 业主指示「用最新的调研 skill 把已经调研的东西过一遍，看有没有不够透彻的地方」。逐条按 skill 的自检清单跑，**结论：结构都齐，但覆盖与深度不均匀，有 5 处实质缺口**。

### 3.1 结构自检（都过）

十份正文全部具备：结论先行 / 逐条点评 / 对不上的地方 / 待核清单 / **反证检索记录**。证据档位标记齐全。✅

### 3.2 缺口一：**三重账本对账我此前完全没做**（skill 的 L3 硬门槛）

skill 要求「可枚举对象必须做到：来源甲条数 + 来源乙条数 == 我的清单条数，且无重复」。补做结果：

| 账本 | 方法 | 结果 |
|---|---|---|
| 甲 | `gh search repos --topic rag` + `"knowledge base"` 前 40 各取并集 | **80 个候选**，我的 A 线 19 个里只覆盖 **10 个** |
| 乙 | 中文关键词（知识库 RAG / 本地知识库 / 大模型 知识库） | 59 个候选，3000 星以上 5 个 |

**账本甲里真正漏掉、且值得评的**（逐个 `gh api` 核过星数与许可证）：

| 项目 | 星 | 最后推送 | 许可证 | 为什么是漏项 |
|---|---:|---|---|---|
| **chatchat-space/Langchain-Chatchat** | **38,705** | 2025-11-10 | Apache-2.0 | 国内最知名的离线 RAG 之一；**F 线还写过 DISC-LawLLM 的检索件就是外借它**，却没在 A 线评 |
| **FlowiseAI/Flowise** | **55,525** | 2026-08-13 | NOASSERTION | 低代码 RAG/Agent 平台，活跃度高 |
| **outline/outline** | **41,059** | 2026-10-25 | NOASSERTION | 团队知识库（非 RAG，但同赛道） |
| **VectifyAI/PageIndex** | **39,658** | 2026-10-24 | MIT | "无向量 RAG"代表，I 线只在社区信号里提了一句，A 线没评 |
| **getzep/graphiti** | 32,194 | 2026-10-25 | Apache-2.0 | F 线只提了它的失效算法缺陷，没作为项目评 |

### 3.3 缺口二：**B 线漏了一个 3 万星的解析器**（已在 `20-parsing.md` 补记）

`opendataloader-pdf`（29,993★，Apache-2.0）——带 bbox、local/hybrid 两档可切、Java 11+ 依赖。它自带的 benchmark 把「MinerU 表格最高」这句**推翻了**（docling 0.887 > mineru 0.873）。**这是本次自查最实质的一条。**

### 3.4 缺口三：**证据深度严重不均**

| 线 | 对象数 | 标了"未取证/fetch_failed"的对象 | 有基准数字的 |
|---|---:|---:|---:|
| **A 平台** | 19 | **10（过半！）** | 2 |
| **E 商业** | 20 | **8（40%）** | **0** |
| F 中文法律 | 16 | 3 | 2 |
| H 工业实践 | 35 | 4 | 1 |

⇒ **A 线有一半对象的"表格/公式/引用粒度"根本没查**，只有 README 关键词扫描；**E 线 20 家商业产品零基准数字**（全是配额与功能页）。这两条线的"结论"应当按"概览级"读，不是"已核实"。

### 3.5 缺口四：**反证做得薄的两条线**

| 线 | 反证节体量 | 真命中 | 问题 |
|---|---:|---:|---|
| **F 中文法律** | 1,430 字符 | **0** | 整节没有一条"命中反证"的记录，等于只做了形式 |
| **J 学术** | 1,111 字符 | 1 | 24 篇论文只做了一次反证检索 |

### 3.6 缺口五：**动态榜的"当日榜首"全部没读到**

G 线 44 个对象里，MTEB / C-MTEB / OmniDocBench / olmOCR-Bench / LegalBench / LEXTREME / LawBench 都**只读到口径与时序，没读到榜表**（HF Space 动态渲染、官方站 404）。替代源（Papers with Code、HF 数据集卡片）**没试**。

### 3.7 自查后仍未补的（如实登记）

- **A 线 5 个漏项只补了清单，没逐个评**（README 未读）。
- **F / J 线的反证没补做**。
- **动态榜没换源重试**。

> 恰恰说明一件事：**268 个对象里只复核了 88 条（错误率 12.5%），而这次自查又在"没复核的那 3/4"里挖出 5 处实质缺口。** 覆盖广度不等于深度。

---

## 四、文件清单

```
docs/research/kb-at-scale/
├─ 00-brief.md                  任务书（口径/证据档位/分线）
├─ 10-platforms.md              A 线正文
├─ 20-parsing.md                B 线正文
├─ 30-indexing.md               C 线正文
├─ 40-papers.md                 D 线正文
├─ 50-commercial.md             E 线正文
├─ 60-cn-legal-kg.md            F 线正文
├─ 70-competitions.md           G 线正文
├─ 75-industry-practice.md      H 线正文
├─ 78-community-signals.md      I 线正文
├─ 80-academic-frontier.md      J 线正文
├─ 90-synthesis.md              综合判断（20 条结论 + 改动形状 + 自我更正）
├─ AUDIT-2026-10-25.md          复核总账（统一一份，88 条）
├─ AUDIT-2026-10-25.jsonl       同上，机器可读
└─ data/                        各线机器可读数据（10 份 jsonl，268 行）
```

外部原件按主题分类存放：`../papers/`（TREC ToT 9 份 + DS@GT 2 份，索引见其 README）。
