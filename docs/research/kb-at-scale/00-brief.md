# 大规模知识库技术路线调研 · 任务书与统一口径

> **本文件是所有调研子任务唯一的目标说明。** 各研究线的产出文件在 `docs/research/kb-at-scale/` 下，文件编号见 §七。
> 数据行写进 `docs/research/kb-at-scale/data/<线号>-<名>.jsonl`（机器可读，父代理只读这个）。
> **业主原话（2026-10-24）**：「我们要调研一下市面上现有产品的技术路径有什么，然后参照学习一下别人，来修改一下我们的技术路线。」
> 附带约束：「那种小的、几百条文档就用的那种就不用调研了」；「所谓开源知识库项目，能够适用于几百万条文档规模的」。

---

## 一、我们要回答的问题（不是"市面上有什么"，是"我们改不改、改哪儿"）

按重要性排序。**每条都要在产出文件里给出结论句**，不许只堆资料：

1. **几百万篇文档**这个量级，市面上的开源项目靠什么撑住的？（分批入库？分布式索引？对象存储？分区？还是压根没到过这个量级，只是宣传语）
2. **表格、图、公式、上下标**这四类特殊内容，谁真正做对了？做到什么程度（保结构 / 保语义 / 只保文字）？代价是什么？
3. **条款级引用 + 点回原文**（我们的命门）：有没有别人的做法比我们更省力、更准？
4. **中文法规/国标**这种"条款编号强、字面重复高（大量"3 术语和定义"）、现行版会废止"的语料，别人有没有专门处理？
5. **我们该抄谁、抄哪一段、不抄谁**。凡建议引入的第三方组件，必须写清 **许可证**（AGPL 之类要单独标出来）。
6. **我们的技术路线哪些地方是错的/过时的/已成包袱**，要有反证，不要客套。

---

## 二、规模目标（业主 2026-10-25 亲口更正，**此条覆盖任何旧假设**）

我在提问时把 6,797 篇当成了"当前规模"，业主当场更正（原话）：

> 「当然是百万，现在 6797 篇是测试的一个用例啊，你看看这六千多篇是对应多少个国标，我们一共有 3 万多条国标，每一条国标切出来几百条，那就是几百万了，而且这还只是国标呢，法律法规还没算呢」

> 「中国现行的所有法律法规、地方标准、规章制度」

**所以真实目标是**：

| 项 | 目标 | 备注 |
|---|---|---|
| 国家标准 | **3 万+ 条**（业主口述；实际条数待核） | 每条切数百条条款 ⇒ **百万～千万级条款** |
| 法律法规 | 中国现行**全部** | 法律、行政法规、部门规章、地方性法规、司法解释等 |
| 地方标准 | 中国现行**全部** | DB 系列，格式极不统一 |
| 规章制度 | 现行全部 | 含团体标准/企业制度类 |
| 现在库里的 6,797 篇 | **只是测试子集**，不是规模上限 | 不要拿它当验收口径 |

**这直接改写了三个前提，各研究线按新口径重算**：
1. **向量检索必须换掉**：sqlite-vec 是逐行暴力比对，52 万条 606 ms ⇒ 千万条按线性推是**分钟级**，不可用。C 线重点变成"千万级条款怎么做到百毫秒内"。
2. **解析是一次性大工程**：10 万+ 份 PDF（数 TB），MinerU 单机跑要按**天/周**算。B 线必须回答吞吐、显存、并行、断点续跑。
3. **"拷走就能用"与百万级是矛盾的**：单文件 SQLite 撑不到这个量级。要么承认"整库便携"只对小库成立，要么换存法。这是**要业主裁决的代价**，不是技术细节。

**已核到的硬约束冲突**（必须在结论里正面回答）：`docs/REQUIREMENTS-v4.3.md` 写"向量 p95 ≤ 20 ms **@ 1 万条**"，而目标是千万级条款 —— 差三个数量级。旧验收数字不能直接沿用。

---

## 三、我们现在的做法（对照基线，供每条研究线对齐）

**已成型的一条链路**（细节归属：`docs/REQUIREMENTS-v4.3.md` 第 74 行一段话总述；检索验收另见 `docs/RETRIEVAL-LONG-RANGE-PLAN.md`）：

- 解析：本地 **MinerU (magic-pdf ≥0.10.0)** 做版面分析，抽多栏正文、跨页表格转 Markdown、公式转 LaTeX、★强制性条文标记、页面几何（Rotation/CropBox/MediaBox）与 bbox；
- 存储：**单文件 SQLite**（WAL + 单写者队列），条款级一行一条；
- 索引：**六通道并行召回 + RRF 融合**（精确条款号 / FTS5 / 向量 / 模态 / 法理要素 / 行为客体），向量用 **sqlite-vec**；
- 生成：用户自配 DeepSeek API Key 或本地 LM Studio，受控流式；
- 前端：Electron + React + pdfjs-dist，点击引用徽章跳 PDF 对应页（**红色定位箭头**，不是高亮框——见 `docs/NOT-DOING.md` 第 2 条）。

**实测数字（都来自本仓实测，不是转述）**：

| 事实 | 数字 | 出处 |
|---|---|---|
| 语料规模 | 约 6,797 篇 / 522,021 条条款 / 2,246.0 MiB | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` §1.1 |
| 精确条款号检索 | **0.1 ms**（不随条数涨） | 同上 §1（J2） |
| FTS5 检索 | **35.6 ms**（52.2 万行上） | 同上 |
| 向量检索 | **606.0 ms**，随条数**线性**（sqlite-vec 自述 brute-force only） | 同上（J1） |
| 大白话提问 | 53.0%（971/1832）与原文**零字面重叠**；有重叠的那 47% 只有 4.4% 进前 5 | 同上 §1.2 |
| 候选集是瓶颈 | 全库 42,181 术语里选对：前 20 = 21.0%，前 50 = 33.0%；候选集收到 50 时前 20 = 99.0% | `docs/research/TECH-PATH-2026-09-28.md` §1（J5） |
| 证据边（条款互引） | 22,992 条，**跨文档 0 条**，有边条款仅 4.93% | 长周期计划 §1.1 |

**已经判死的方向（不要再提，除非有新反证）**：见 §六。

---

## 三·附、证据档位（每条结论必须标）

沿用本仓既有档位（`docs/research/TECH-PATH-2026-09-28.md` 文件头）：

- **【实测】** = 在本机跑过，附命令/输出。
- **【一手】** = 读到了官方文档/源码/仓库文件/论文原文，附 URL + 抓取日期。
- **【转述】** = 来自二手介绍/聚合文章/评测博文，**没读一手**。
- **【推断】** = 我们的判断，无实验支持。

**硬规矩**：
- 每个数字后面写清"谁说的、在哪、哪一天抓的"。查不到就写 **未查证**，不许编。
- 论文没读到正文就写"只读到摘要"。仓库没读到源码就写"只读到 README"。
- **字段描述 ≠ 运行时行为**（本仓吃过这个亏）：OpenAPI/README 说"支持表格"不能当成"表格保结构"。
- 严禁把"聚合对比文章"当一手。中文技术号、CSDN、知乎贴一律【转述】。

---

## 四、每条研究线的固定产出格式

每份文件 ≤ 400 行，中文，**结论先行**。结构：

```markdown
# <线名>
> 抓取日期：2026-10-25（所有 URL 当日可达）
## 结论先行（≤15 行，每条一句话，带档位）
## 逐个点评
### <项目名>
- 是什么 / 谁维护 / 许可证 / 最后提交
- **规模**：它自己宣称多少、有没有实测/基准证据（写清口径：文档数 or 块数）
- **表格 / 图 / 公式 / 上下标**：分别怎么处理，证据是什么
- **中文法规/国标**：有没有专门处理（条款号、效力状态、多版本）
- **引用可回溯**：能不能点回原文页/坐标
- **对我们**：抄哪一段 / 不抄 / 代价（工作量、依赖、许可证风险）
## 对不上的地方（来源互相矛盾处，单列，不抹平）
## 待核清单（我没读到的）
## 反证检索记录（搜了什么词、搜出什么）
```

**对抗性检索（必做，出自本机 `research-protocol` 技能，不强求形式但必须做）**：
- 每个主要结论，**至少搜一次反证**：把结论写成问句 + `争议` / `被高估` / `复现失败` / `limitations` / `benchmark 质疑` 搜一次。
- 报告里**必须有一节「对不上的地方」**，把来源之间的矛盾**单列**写清，不许揉成一个统一说法。
- 「来源说」和「我判断」分开写。事实类取共识（有来源不符就写"未确认"）；判断类取多数但**异议要留着**。
- 报告末尾附一行：**搜了哪些反证词、搜出什么**。

**禁止事项**：
- 不许提议做 Word/PPT 交付物（`docs/NOT-DOING.md` 第 1 条）。
- 不许提议 bbox 高亮框（同上第 2 条，已是红色定位箭头）。
- 不许提"通用层自己手搓"（同上第 6 条：通用层纯借鉴，有现成的就抄）。
- 不许写"建议引入大模型重排"这类没名字没许可证的空话。

---

## 五、机器可读行格式（每条项目/论文一行，写进 `data/<线号>-*.jsonl`）

```json
{"id":"ragflow","kind":"oss","url":"https://github.com/infiniflow/ragflow","license":"Apache-2.0","last_commit":"2026-10-xx","scale_claim":"...","scale_evidence":"【一手】docs/xxx","tables":"...","figures":"...","formulas":"...","subsup":"...","cn_legal":"...","clause_citation":"...","verdict":"借鉴|可选|不适用|待核","verdict_what":"具体抄哪一段","evidence_url":"...","fetched":"2026-10-24","notes":"..."}
```
`verdict` 只允许四个值：`借鉴`（拿它的做法/代码）／`可选`（可作为某个零件）／`不适用`（规模或语料不合）／`待核`（证据不够）。

---

## 六、已判死 / 已作废（不要再提，除非拿出新反证）

| 方向 | 裁决与依据 |
|---|---|
| 向量去重 | **测翻取消**：跨文档 9,506/10,060 组、跨条号 1,107/10,060，去了会毁掉可点引用（`TECH-PATH-2026-09-28.md` A2） |
| 多接一条检索路 | **明确死路**：`docs/archive/research-process/PROJECT-STATUS-2026-10-05.md` |
| 换向量底座 / 照抄 TREC ToT 冠军的外部数据 | 同上"不再走"清单 |
| 手搓通用层 | `docs/NOT-DOING.md` 第 6 条 |
| Word/PPT 交付物 | 同上第 1 条 |
| bbox 高亮框 | 同上第 2 条（是红色定位箭头） |

**已做过的调研，不要重复**（要引用就引它，写清"已有结论见 X"）：
`docs/research/substitute-scan.md`（谁已经交付同样价值）、`TECH-PATH-2026-09-28.md`（检索路径定稿）、
`HANDOFF-external-solutions.md`、`solutions-for-open-problems.md`、`RETRIEVAL-LITERATURE-SCAN-2026-09-30.md`、
`rag-encyclopedia-study.md`、`weknora-assessment.md`、`SURVEY-*` 系列（四轮学术调研）。

---

## 七、研究线划分（文件与责任人）

| 线 | 文件 | 范围 |
|---|---|---|
| A | `10-platforms.md` | 开源知识库/RAG 平台：RAGFlow、Dify、FastGPT、MaxKB、AnythingLLM、Onyx(Danswer)、Verba、Quivr、Khoj、Kotaemon、Open WebUI、R2R、Morphik、WeKnora(已有评估，只补规模面)、RAGFlow 的 Infinity 引擎、LangChain/LlamaIndex/Haystack/txtai 作为框架 |
| B | `20-parsing.md` | 解析：MinerU 2.x、Docling(IBM)、Marker、PP-StructureV3、Unstructured、pdf-extract-kit、Nougat、olmOCR、Chunkr、Zerox、以及商业 LlamaParse/Reducto/Mathpix/Azure Document Intelligence/Google Document AI（只取技术路径） |
| C | `30-indexing.md` | 检索底座与索引：Elasticsearch/OpenSearch、Vespa、Milvus、Qdrant、Weaviate、pgvector、LanceDB、Typesense、Meilisearch、Tantivy/Quickwit、SQLite FTS5/sqlite-vec、以及晚交互（ColBERT/ColPali/ColQwen）与重排器 |
| D | `40-papers.md` | 论文前沿：Contextual Retrieval(Anthropic)、Late Chunking(Jina)、RAPTOR、GraphRAG/LightRAG/HippoRAG、Sufficient Context、表格检索(OTT-QA/FeTaQA)、公式检索、法律检索(COLIEE/LeCaRD)、中文法条检索、RAG 综述；**外加各年度检索/知识库竞赛冠军**（TREC ToT **2023–2025** 各年冠军与论文——⚠ **2022 年没有 ToT 赛道**，2026-10-25 已核：TREC 31 议程页无该总览、ToT 官网 Previous editions 只列 2023/2024/2025；另有 CCKS、CCF BDCI、KDD Cup CRAG、COLIEE、NeurIPS 相关挑战赛） |
| E | `50-commercial.md` | 商业产品技术路径：Azure AI Search / Vertex AI Search / AWS Bedrock KB+Kendra / Elastic / Glean / Cohere / Pinecone / Harvey / LexisNexis Protégé / CoCounsel / Spellbook / 北大法宝 / 威科先行 / 工标库 / 秘塔 / 得理法搜 / 云厂商 KB |
| F | `60-cn-legal-kg.md` | 中文/法律/图谱专用工程：KAG(OpenSPG)、QAnything、BISHENG、ChatLaw/LaWGPT 等法律开源、COLIEE/LeCaRD/CAIL 数据集与做法、条款级知识图谱。**只写 A~E 没评过的**；GraphRAG/LightRAG 的方法论文归 D 线 |
| G | `70-competitions.md` | **竞赛与评测赛道全景**（业主 2026-10-25 追加：「既然还有其他的比赛，那你完全可以多参考参考」）。TREC 系（Deep Learning / NeuCLIR / CAsT / ToT / FTS / Clinical Trials / Interactive-KB）、NTCIR 系、CLEF 系（CLEF-IP、JURISIN 相关）、SemEval、KDD Cup、NeurIPS/ICLR 挑战赛、MS MARCO、**BEIR / BRIGHT / MTEB / C-MTEB 排行榜**、CRAG、RAGTruth、**文档解析榜 OmniDocBench / olmOCR-Bench**、法律赛道 **COLIEE / LeCaRD / CAIL / 中国法研杯 / LegalBench / LEXTREME**、中文系 CCKS / CCIR / NLPCC / CCF BDCI / 天池 / DataFountain / 讯飞 A.I. 开发者大赛。**每条写：赛道问的是什么、冠军/榜首用什么路线、指标多少、能不能迁到"条款级中文法规"** |
| H | `75-industry-practice.md` | **工业界生产实践**（公司工程博客与生产案例）：谁真做过千万级检索/知识库、怎么分片、怎么控成本、怎么保证引用可回溯、踩过什么坑。候选：Pinterest / Notion / Slack / GitHub / Atlassian / Microsoft / Google / Meta / Airbnb / Shopify / Stripe / 字节 / 阿里 / 腾讯 / 小红书 的搜索与 RAG 工程博客；Elastic/Vespa/Qdrant/Milvus 官方案例；法律科技公司（Harvey、Robin AI、Luminance）的技术分享 |
| I | `78-community-signals.md` | **社区与社交媒体实战信号**（业主：「社交媒体上面啥的也可以参考，百无禁忌」）：HN / Reddit(r/LocalLLaMA, r/MachineLearning, r/RAG) / Lobsters / V2EX / 知乎 / 公众号 / GitHub Discussions 与 issue 区 / 独立评测博文。**主题**：各国开源知识库在真实语料上的失败模式、百万级实测反馈、表格/公式解析的真实吐槽、各家许可证陷阱、以及"厂商宣传 vs 用户实测"的差距清单。**一律标【转述】，不许当一手** |

**交叉规则**：同一条事实只在一条线里写细，其它线写"见 X 线"。**不许两条线重复评同一个项目**（WeKnora 只在 A 线补规模面，其它线不写）。G/H/I 三条线是 2026-10-25 追加的扩面，**不与 A~F 重复评同一对象**：G 只写比赛与榜单，H 只写公司生产实践，I 只写社区信号。

---

## 八、现状与交接（2026-10-25 第二轮接手时写，每轮更新这一节）

| 线 | 文件 | 状态 | 说明 |
|---|---|---|---|
| 任务书 | `00-brief.md` | ✅ | 本轮修掉重号（两个「三」） |
| A | `10-platforms.md` + `data/10-platforms.jsonl` | ✅ 已落盘，**待复核** | 17 个平台 + 4 框架；元数据已用 `gh api` 逐个回核（星数/推送日/许可证/归档），与文内一致 |
| B | `20-parsing.md` + `data/20-parsing.jsonl` | ✅ 已落盘（190 行 / 18 项目） | 结论：主干从 `mineru 3.4.5` 升上游 4.0.12、Docling 当第二解析器、抄 complex_table 分流与 locator 语法。⚠ Lead 已就地更正一处：我们代码走的是 `mineru` 包（非 magic-pdf/AGPL），错话保留原文 |
| C | `30-indexing.md` + `data/30-indexing.jsonl` | ✅ 已落盘，**待复核** | 12 个底座 + 迟交互/重排器；结论=两段式，不改单机无外部服务。⚠ 本轮已补两处：512 维实测口径更正、嵌入式 ANN 候选（FAISS/USearch/hnswlib/Chroma） |
| D | `40-papers.md` + `data/40-papers.jsonl` | ✅ 已落盘（269 行 / 26 行 jsonl） | 三年冠军（2023 CMU-LTI 0.5554 / 2024 h2oloo 0.8159 / 2025 SRCB 0.6824）+ 12 篇方法论文。⚠ 已更正两处：TREC ToT 没有 2022 年；"我们没有重排器"与代码不符（有，且已实测判不接生产） |
| E | `50-commercial.md` + `data/50-commercial.jsonl` | ✅ 已落盘，**复核后已更正 2 处** | 20 家商业产品；E-3（Azure 1,000 是通配符限制）、E-8（Kendra 已生效）已改 |
| F | `60-cn-legal-kg.md` + `data/60-cn-legal-kg.jsonl` | ✅ 已落盘（238 行 / 16 行 jsonl） | 总判断："投，但只投薄的那一半"；英国 effects 字段可整段照抄；GB/T 46686.1 库内没有，未入库前不得当依据 |
| 复核 | `data/audit-2026-10-25.md` + `.jsonl` | ✅ 已落盘 | 核 37 条：确认 30 / **错误 6** / 无法核实 1 / 引证指错页 2；6 条错误已由 Lead 就地更正并留痕 |
| 综合 | `90-synthesis.md` | ✅ 已落盘（扩面后 197→242 行） | **业主真正要的东西**：20 条结论 + 代码级现状 + P0/P1/P2/P3 改动形状（**调研结论，不是待办**；业主 2026-10-25 明确"你只是调研员，不要讨论实施"） |
| G 竞赛/榜单 | `70-competitions.md` + `data/70-competitions.jsonl` | ✅ 已落盘（307 行 / 44 行） | **42 个对象**；两处任务书前提错（无 FTS 赛道、DL 是 2019–2023）；补上被漏掉的 **TREC Legal**；中文国标条款级检索"无比赛、只有数据集" |
| H 工业实践 | `75-industry-practice.md` + `data/75-industry-practice.jsonl` | ✅ 已落盘（272 行 / 35 行） | **35 个案例**；瓶颈顺序 内存→过滤→索引构建→解析；引用上限"段落+页/URL"；单机 10⁷ 可撑、10⁹ 必须集群 |
| I 社区信号 | `78-community-signals.md` + `data/78-community-signals.jsonl` | ✅ 已落盘（278+ 行 / 45 行） | **两条否证**（SQLite→Postgres 的 100 万 PDF 实践、中文国标非无人区）+ 三条验证；中文社区零信号（Reddit 403 / 知乎反爬），如实记 |
| J 学术扩面 | `80-academic-frontier.md` + `data/80-academic-frontier.jsonl` | ✅ 已落盘（311 行 / 24 行） | 24 篇；**两条我们没考虑过的范式**（doc2query 文档侧扩展、GAR 重排期图扩展）；德国民法典实测"按条/按款切最好" |

**复核口径（本轮由独立复核线执行，结论写 `data/audit-2026-10-25.md`）**：只核**能被外部来源判真假的**条目（引用的 issue 号/原话/配额数字/许可证），不核【推断】类判断；每条给「确认 / 错误 / 无法核实」三态之一，**错的地方由 Lead 就地更正并留痕，不许悄悄删**。

---

## 九、给所有调研子代理的工具纪律（2026-10-25 Lead 定，踩过坑）

1. **联网只用 `web_fetch` / `web_search` 这两个工具**，它们已经配好 DeepSeek 官方的 Tools key（进程环境里的 `DEEPSEEK_TOOLS_API_KEY`，与模型 provider 是**两套凭据**）。
2. **不要自己拼 HTTP 请求去打 DeepSeek 官方接口**（`api.deepseek.com` 之类），也不要把当前会话模型 provider 的 key 拿去发请求 —— 那条路上游不认，会白跑。
3. 抓页面用 `web_fetch`；要 markdown 全文可试 `https://r.jina.ai/<url>`（第三方，免 key）；GitHub 元数据用 `gh api`（已登录）。
4. 工具报错就**如实写 `fetch_failed` 并换源**，不许自己另找 key、也不许把失败说成"查过了没有"。
5. **子代理只写自己那两个文件**（md + jsonl），不 commit、不动别人的写盘范围。
