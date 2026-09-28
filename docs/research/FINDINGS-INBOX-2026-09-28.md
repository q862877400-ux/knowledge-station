# 收件箱：调研线回传的"可借鉴结果"（我逐条读过并挑出来的）

> **性质**：这是**我这一侧**（开发会话）的筛选台账。调研线（`var/tmp/study/problems/`）交上来的报告里，
> 我把**值得借鉴的**挑出来、把**推翻我们的**挑出来、把**仍然没答案的**挑出来。
> **不是**对策表（还没到那一步），是"读完之后我确认了什么"。
> **读法**：§1 推翻项必须先处理；§2 可抄项是候选（还没排期）；§3 空白是我们自己必须先量的。
> **所有数字都是回一手件核过的**（子代理标 `④` 官方仓库 / `①` 同行评审 / `②` 论文自报 / `⑤` 本机实测）。
> ⚠ **本文件不重复存我们自己的事实**——那在各归属层（计划文档 / 台账 / 开发史）。

---

## §1 🔴 推翻项：四条已经**撤回或更正**的既有结论

> 这一节最要紧。调研线在**回一手源码/issue 原文**时推翻了我们此前给业主的建议。
> 我已在自己那两份文档里**就地更正并留痕**（`agent-memory-systems.md` §2.4 / §6.1、`NEXT-DEV-PLAN-2026-09-28.md` §7.1）。

### 1.1 「要抄 graphiti 的图边时间失效」——**撤回，只抄字段不抄算法** `④官方仓库 + ③项目方自述`

我此前对业主说"要抄旧依据不删、只标失效"。**这一步的做法不能抄。**

| 证据 | 内容 |
|---|---|
| **源码机制**（`graphiti_core/utils/maintenance/edge_operations.py:414`） | 传给 `resolve_edge_contradictions` 的候选来自**空过滤器** `search_filter=SearchFilters()`（隔壁 `:399` 那次才有 `edge_uuids=[...]` 约束）⇒ **候选集 = 该 group 内每一条语义相似的边，不要求与新事实共享任何实体** |
| **上游 issue #1728**（open，2026-08-04） | 约 **3,950 条**事实的生产图里 **41%** 边带 `invalid_at`；人工抽检 4 条 **3 条误伤** |
| **上游 PR #1729**（open，2026-08-04 至今未审） | 修法已经有人写了：候选必须"可能替代"（连**同一对实体**，或**同端点 + 同关系名**）。PR 自己写明取向：宁可留一条过期但可见的事实，也不要静默退役一条真事实 |
| **独立现场报告**（40 例盲判） | **28 例误伤 = 70%**，Wilson 95% CI [54.6%, 81.9%]；作者的护栏"距离干脆关掉失效功能只差 1/40 例" |

**⇒ 对我们的含义**：
1. **可抄的是三列双时态字段**（`valid_at` / `invalid_at` / `expired_at`），形状直接映射我们的「现行/废止/即将实施」。
   **但"用模型判矛盾就盖失效"这一步不能抄** —— 原样照抄等于上线一个**静默删真话的通道**。
2. **审计要查 `expired_at`（事务时间）不是 `invalid_at`（会被回填）** —— 查错列会让可判定集小到 1/4。
3. **我们的场景比它安全一档，但只是一档**：我们是"效力由发布机关决定"。⇒ 派生层的失效判定**必须是显式事件**（某条原文说它废了），**绝不能让模型从语义相似度里推出来**。

### 1.2 「向量通道贡献≈0 ⇒ 无害」——**这一步推错了** `②论文自报 + ①`

我们的消融只证了"**去掉它，问答指标不动**"，我把它推成了"**所以它无害**"。**两件事不是一件。**

三条独立反证，其中一条**正落在我们的语料类型上**：

| 出处 | 原文要点 | 等级 |
|---|---|---|
| arXiv **2606.03728**（ECHR 法律域，AQuAECHR 基准） | "ranking by similarity performs **worse than random selection** at surfacing gold citation paragraphs" | ② |
| arXiv **2607.25180**（Bekko，长文档基准） | **BM25 0.822 打败全部 12 个稠密模型**（最强稠密 0.740）；并点名 BGE-M3 论文自己也报 BM25 远高于 dense | ② |
| arXiv **2608.02112**（荷兰语混合检索） | 强塞静态嵌入通道在**留出折上显著变差**（MRR 掉 0.015–0.036） | ② |

⇒ **在 ECHR 那条被独立复现之前，"默认关掉向量通道"不能当成已证无害的动作。**
⚠ **这直接改了我上一份开发计划里的一条登记事项**——我原本写"⚠ 但这一路恰好是 P1/P2 唯一在用的语义路，在 P2 出结论前不能关"；现在要补一句：**它可能不只是"无害"，而是"有害"**，这需要 E 组核实语料适用性之后再定。

### 1.3 「标准号+条款号可以直接泛化成来源+定位单位」——**方向对，写法是半成品** `①规范原文`

**这一条是本轮最有产品价值的一处纠偏**，有四条证据，其中两条是**规范原文级**：

| # | 证据 | 逐字要点 |
|---|---|---|
| 1 | **W3C 自己说"位置号"脆、原文引文才稳** | `TextPositionSelector` "…is **very brittle** with regards to changes to the resource"；`TextQuoteSelector` 是"describes a textual segment by means of **quoting it, plus passages before or after it**"（`prefix`/`suffix` 冗余） |
| 2 | **IETF 的稳定标识是从编号派生的 ⇒ 结构上会随移动失效** | RFC 7991：`"pn" … always has the format "s-nnn", where "nnn" is **the section number**`；IETF 用 `anchor`（`xml:id`）当主标识正是为了与编号脱钩 |
| 3 | **书目/引用标准全线只到"页"，没有到"段"** | schema.org `ScholarlyArticle` 只有 `pageStart`/`pageEnd` + 自由文本 `pagination` |
| 4 | **PROV 明确把"位置长什么样"划到范围外** | "The properties used to describe instances of `prov:Location` are **outside the scope of PROV-O**"；`qualifiedReference` 在 PROV-DM/PROV-O 里 **0 次命中**（真实存在的是 `prov:qualifiedPrimarySource`） |

**⇒ 修订后的判据：`quote_exact` 为主、`locator_value` 为辅。** 而这与我们的直觉相反——**我们靠"标准号+条款号"这种编号定位，而 W3C 明说编号脆。**

**只做第 1 步（把 5.2.3 换成 3.2）是不够的。** 还缺三样：版本/版次（`prov:specializationOf`）、原文冗余锚点（`TextQuoteSelector`）、定位单位类型的枚举（xml2rfc 的 `s-`/`t-`/`f-`/`i-` 前缀分类）。

⚠ **我们自己对这份"定位单位类型"没有任何抽象** —— 命中判据现在就是硬编码的"标准号+条款号"（`SEARCH_CHANNELS` 里的 `exact` 路）。**这是"必须泛化"那条硬约束真正的卡点**，而它此前没进过任何一份计划文档的显眼位置。

### 1.4 「sqlite-vec 只能暴力扫 / 官方 bench 只到 10^5」——**前提已过期** `④官方仓库`

**我写进 `agent-memory-systems.md` §5.3 的那条，是 2026 年 3 月 31 日之前的状态。**

| 一手件 | 内容 |
|---|---|
| 作者 2024 年立的跟踪 issue **#25** | 原文："as of v0.1.0 will be brute-force search only, which slows down on large datasets (**>1M w/ large dimensions**). I want to include some form of approximate nearest neighbors search **before v1**"，并列了 IVF / HNSW / DiskANN 三个候选 + 6 个待答问题 |
| **PR #273**（merged 2026-03-31，commit `0de765f`） | "prepare for the addition of **ANN indexes**"；加 `INDEXED BY flat()` 语法；NEON SIMD |
| **PR #276**（merged 2026-03-31，commit `43982c1`） | 第一个真索引 **`rescore`**：int8 / bit 量化 + oversample + 精排 |
| **PR #277**（merged 2026-03-31） | `ivf`："**experimental**… **not enabled by default**… build it yourself with `SQLITE_VEC_EXPERIMENTAL_IVF_ENABLE`" |
| **PR #278**（merged 2026-03-31） | `diskann`：基于原版 DiskANN + 2023 LM-DiskANN，插入时增量建 Vamana 图 |
| **发布线** | **v0.1.9 = 稳定线**（2026-03-31）；**v0.1.10-alpha.1** 逐字"Initial alpha release of sqlite-vec with new ANN indexes: **rescore, ivf (experimental, not enabled), and DiskANN**"；**alpha.4 = 2026-05-18** |

**⇒ 现在真正的约束不是"没有 ANN"，而是：① ANN 只在 alpha 发布线、② ANN 与分区键/元数据过滤互斥。**

⚠ **但"已合并"目前只有摘要、没有随件一手出处**（子代理存的 `vec0.md`/`api-reference.md`/`CHANGELOG.md` 里搜不到 `rescore`/`diskann`/`quantizer`/`oversample` 任何一个 ⇒ 那是**合并前**的文档）。
⚠ 子代理报的 522k 实测（flat 788.7 ms → rescore int8 458.3 ms → rescore **bit 71.4 ms**）**未复现**，且 bit 档 recall 0.215 是合成数据失真。
⇒ **我已单独派了一个代理去拿权威建表语法 + 在我们 522k 真实数据上重测召回与耗时**（§3 空白第 1 条）。**在那之前不要按"能换 ANN"做任何决定。**

---

## §2 ✅ 可借鉴项：抄哪一处的形状（**尚未排期**）

> 全部来自调研线回一手件的报告。**"能不能抄"那一栏我已独立读过，不是转述。**

### 2.1 引用与定位（G 组）—— 这是**最接近可落地**的一块

| 抄什么 | 具体形状 | 出处 | 等级 | 能不能抄 |
|---|---|---|---|---|
| **来源身份** | `prov:specializationOf` + FRBR 四层（work/expression/manifestation/item） | W3C PROV-DM | ① | ✅ 能 |
| **定位单位** | **Akoma Ntoso（OASIS Standard 2018-08-30）** 的 `eId`，逐字 *"All internal references will thus use this eId."*；定位目标是 *"so that documents … can be **easily cited and cross-referenced**"* | OASIS | ① | ✅ 能（是 OASIS 标准，不是小众库） |
| **定位单位类型枚举** | xml2rfc v3 的 `pn` 前缀分类（`s-nnn` / `t-nnn` / `f-nnn` / `i-ttt-nnn`） | RFC 7991 | ① | ✅ 能 |
| **可校验性** | **W3C Web Annotation `TextQuoteSelector`**（`exact` + `prefix` + `suffix`）+ **ALCE 的 citation recall/precision**（NLI 模型判 entailment） | W3C / ALCE | ① | ✅ 能 |
| ❌ **不能抄** | W3C PROV 当定位抽象 —— 它**主动放弃了**定义位置（`prov:Location` 属性在范围外），`qualifiedReference` **0 次命中** | 同上 | ① | ❌ |

**⇒ 三层拼起来正好覆盖我们泛化要的四类定位单位（标准号 / RFC 章节 / 古籍卷回 / 论文小节）**，而**没有一套标准单独覆盖**。

### 2.2 记忆与派生层（C 组）—— 形状好，算法要重写

| 抄什么 | 出处 | 等级 | 能不能抄 |
|---|---|---|---|
| **sufficiency router**（判"够不够"不是"像不像"）+ provenance 指针 + verified write-back | **TierMem**（`github.com/FreedomIntelligence/Tiermem`）§1/§2；自报 token **−54.1%**、延迟 **−60.7%**、精度只掉 2.2 点 | ④ | ✅ 能读实现；⚠ **数字是自报，非同行评审** |
| **git 历史当检索源** | **CommitDistill**（arXiv 2605.18284, Microsoft）：1 万次提交抽取 **<4 秒**、θ=2.5 弃答阈值 | ② | ✅ 做法能抄；⚠ 它同时**独立复现了"检索指标 ≠ 答案质量"** ⇒ git 历史**该当检索源，不该指望它改善答案质量** |
| **写入前验证谓词** | **Eywa**（arXiv 2605.30771）§4.1：`V = V_support ∧ V_hard ∧ V_subject ∧ V_act`；实测拒掉 11/132（8.3%），但 **67.4% 候选无任何硬锚点** ⇒ **只覆盖三分之一** | ② | ⚠ 只能抄形状，覆盖面不够 |
| 🔴 **我们独有的那条**（另一组独立得出同一结论） | **全场（graphiti / Zep / PPMF / MAP-Graph）只记"失效了"，不记"谁说它失效了"**。PPMF（arXiv 2607.29167）证明这不是洁癖：LLM 归并中**一条低信任的外部观察会被改写成"看起来像用户历史"**，抹掉限制其权威性的来源（脆弱时 ASR 高达 **1.000**） | ② | ⇒ **派生层必须有 `invalidation_source` + `material_review` 两列，平台维护、模型不可改。** 这是我们相对那批项目的**独有优势** |

### 2.3 长文档与切分（F 组）—— **推翻了我们两个想抄的**

| 结论 | 数字 | 出处 | 等级 |
|---|---|---|---|
| 🔴 **late chunking 现在不该抄** | 在"文档内检索"上**全面变差**：Nomic 平均 **−53.17%**、Jina-v3 **−29.82%**；而结构化切分在 in-document 上比 LLM 引导切分**高 10–30%** | arXiv 2602.16974 §4.2–4.4（有 ACM 出版记录） | ② |
| ⚠ **换长窗口模型的收益（~24%）远大于换切分策略（~4%）** | 同篇：8192 截断 vs 192 截断 平均 **+24.47%**；而 late chunking 自报仅 **+3.63% 相对 / +1.9% 绝对** | arXiv 2409.04701 §4.2/§4.3 | ② |
| ⚠ **"只取头"在标准 benchmark 上成立是假象** | 20+ 长文档模型没有一个稳定超过自己的 FirstP 基线 5% 以上；但作者构造的 MS MARCO FarRelevant（相关段落**放到 512 token 之外**）让**许多模型包括 RankGPT 掉到随机基线** | arXiv 2207.01262 | ② |
| ✅ **"每块存几个向量"有曲线，拐点在 3** | pooling=2（向量数减半）**反而略升**；=3（减 66%）退化 <1%；=4 约 3%；=6 约 10%。存储（TREC-Covid，16-bit 单向量 HNSW 345 MB）：pool 3 **260 MB（0.75×，比单向量还小）**、pool 6 **131 MB（0.38×）** | arXiv 2409.14683 §4.2–4.3 | ② |
| ❌ **jina-v3 许可非商用** | Bekko 论文**明确因此把它排除出比较集** | arXiv 2607.25180 | ① |
| ⚠ **"头+尾"是可抄实现、但没有任何论文实测它对嵌入检索质量的影响** | 唯一可抄实现是 LangChain deepagents 的 `_create_content_preview()`（头 5 行 + 尾 5 行 + 中间省略），用于 **LLM 上下文驱逐**、不是嵌入 | `deepagents/filesystem.py` @ `90a3515` | ④实现 / **没找到**质量实测 |

⚠ **"古籍 30.2% 被切成单字"不是 bug** —— 是 ES 默认 `standard` 分析器按 **UAX#29** 在中文上的正常行为 ⇒ **修法是 `jieba load_userdict` 加自定义词典，不是换分词器**。（G 组，`①规范原文`级）

### 2.4 门禁与棘轮（D 组）—— **我原先的说法被推翻了**

🔴 **我说"基线是手工维护的孤例"——不成立。** **baseline-as-suppression-list 才是通行范式**：

| 工具 | 做法 |
|---|---|
| `falsegreen`（`pip install`，零依赖纯 AST，59 码） | `--write-baseline` 写 `.falsegreen-baseline.json`；README 逐字"**A finding is fingerprinted by relative path, code, detail, and normalized source line — not line number, so prepending code does not re-trigger a baselined finding**"；退出码契约 `0` 干净 / `10` 仅低置信 / `20` 至少一条高置信（**"Block the build on 20"**） |
| `realitylint` | `--write-baseline` 生成 `.realitylint-baseline.json`；"**Existing findings are suppressed; new documentation drift still fails CI**" |
| `no-mistakes` | suppression 清单 |

**⇒ 我缺的不是"持久化"，是"条目化"**（fingerprint 按**归一化源码行**、不按行号）。**这一步同时让"总账 ≥ 基线"和 skip-nodeid 两条判据都变成冗余的旁证。**

⚠ **但这两个工具带着我们担心的同一个洞**（⑤ 推断）：基线里某条 finding 对应的测试**被删掉后，那条基线记录变成孤儿，工具不会因此报红**。**我们已做的"过度扣减防护"是这批工具都没有的 —— 这一点上我们领先，不要因为"用现成工具"把它丢掉。**

**一条统计上的硬事实**（`①ICSE 2014` / `①FSE 2015`）：
- 「**断言数**才是与测试套件有效性最强相关的因子」——摘要原文：**6,700 个测试套件、24,000 条断言、5 个真实 Java 项目**。⇒ **"数用例"从一开始就是错的统计量，"数断言"才是。** ⚠ 但它**不能替代**"断言被换成恒真"的检测（换成恒真**数量不变**）——两件事要分开做。
- 「覆盖率与有效性没有共识」——ICSE 2014 原文我只核到**出版方摘要**（全文三个渠道都拿不到：Unpaywall `is_oa=False`、Semantic Scholar `CLOSED`、作者主页 403）⇒ **不引用任何相关系数**。
- 差分覆盖（`diff-cover`，⚠ PyPI 名与仓库 owner 不同名，核过才对）：口径是"**你这次改的这些行有没有测试**"，比"用例总数"贴近我们 D4 的问题。**抄思路不抄工具。**

⚠ **一条结构性洞察（比它给的工具更有用）**：**所有这些工具都在测试层。** 而我们的 D4（一次 `-UpdateBaseline` 就把 6 条保护测试变可删、棘轮不红）和"参数没被读却退出 0"是**命令层**空验证 ⇒ **没有工具能扫**，唯一现成解法就是我们在用的手动变异。**别用工具假装它被自动化了。**

### 2.5 🔴 我们自己的一个活 bug（F 组实测，**优先级最高因为它最便宜**）

`src/core/retrieval/reranker.py:59-64` 返回**已按分降序**的分数表，而 `hybrid_engine.py:466-470` 又拿这张表当"按候选下标对齐"的分数再排一次 ⇒ **恒等置换**（子代理机械复算过：`ordered == [0,1,2,3] → True`），且 `debug["rerank_score"]` 贴错了。

**上游 fastembed 本来就是对的**（`TextCrossEncoder.rerank` docstring 写 "Iterable of scores for each document"，即**与输入顺序对齐**）⇒ **删掉我们自己的包装层排序即可，是恢复契约不是改契约。**

⇒ **重排层现在完全空转。** 修好它之前，"要不要重排"这个讨论没有意义。

---

## §3 还没答案的空白（**我们自己必须先量的，不是查文献能解决的**）

| # | 空白 | 为什么文献解决不了 |
|---|---|---|
| **1** | 🔴 **`sqlite-vec` ANN 的权威建表语法 + 在我们 522k 真实数据上的召回与耗时** | 合并已确认（四个 PR 的 merged 日期与 commit 都有），但**"已合并"只有摘要、没有随件一手出处**；子代理存的文档是**合并前**的。已派代理专查（§1.4） |
| **2** | 🔴 **P1 的盈亏平衡点那个"没量过的量"** | 真实目标里"多条定义"的比例要到前五 ≈11.2% / 前二十 9.6% / 前五十 10.5% 才不亏；而两个候选加权是**按名字 9.0% / 按条目 20.9%** ⇒ **正负号卡在中间，现有数据回答不了** ⇒ 必须重建评测集（那批 gold 全是重名的，且"gold 只有 1 条定义"的样本三组里都是 0 条） |
| **3** | 🔴 **ECHR 那条"按相似度比随机还差"的适用边界** | 它是②论文自报；**我们的语料类型（法规条款，定义高度同构）比 ECHR 案卷更接近同型**，但也可能是"只有它那么极端"。⚠ 在这条被独立复现前不能据此砍向量路（§1.2） |
| **4** | **"检索不如长上下文直读"的分界点** | 所有这类结论都在 ≤1.5M token 内测的；我们是 522k 条条款，**远超任何长上下文** ⇒ 不可套用（已派 E 组查边界） |
| **5** | **古籍 / 技术文档 / 法律条文上的分词器公开对比** | G 组明确写「**没找到 —— 我不敢下结论，建议本仓自己实测**」 |
| **6** | **"自动语料类型检测 → 分词器/索引路由"的现成框架** | G 组核过 ES/Lucene 官方文档，**确认不存在**（ES 只有按字符组分流） |
| **7** | **命令层空验证的机械检测** | D 组已证：成熟工具全在测试层；**命令层没有工具能扫**。已派代理专查（这是 H 组第一优先项） |

### 1.6 🔴🔴 RC2 带回的**最重一条**：我们设想的默认形状**有一个已知的攻击面**

> 出处：RC2 代理，`var/tmp/study/problems/RC2-derived.md`（23 KB）。**我已回一手件核标题**：
> `raw/RC2/01__arxiv-2503.03704.txt:41` 的 `citation_title` 逐字 =
> **"Memory Injection Attacks on LLM Agents via Query-Only Interaction"**（MINJA）。

**逐字**：攻击者 *"injects malicious records into the memory bank by **only interacting with the agent
via queries and output observations**"*；*"MINJA enables **any user** to influence agent memory"*。

**这直接打在我们设想的默认形状上**：我们的派生层**由提问生成** ⇒ **提问流就是写入通道，默认是开放的。**
⇒ 之前我说"派生层要加 `invalidation_source` + `material_review` 两列"时，**把它当成了"好实践"**。
**RC2 指出它其实是"必需"**——不是防幻觉，是**防投毒**。

**第二条独立证据，同向**（Sufficient Context，arXiv 2411.06037，标题已核）：
大模型**"该不答时硬答"**（输出错答案而不是 abstain）。
⇒ 若把"**已答过**"当作充分性信号，**会让系统更倾向去用最脏的那层作答**。
⇒ **充分性判据必须与派生层可信度解耦**，不能合成一个信号。

**⇒ 方案要改的一处**：派生层的写入**默认不能开**。至少要区分
「这条派生记录是谁产生的」（平台 / 模型 / 用户提问）与「谁能改它」，并且**提问产生的记录默认不可直接承重**。

### 1.7 一条**削弱**（不是加强）我们判断的证据 —— 如实记

**Zeta Alpha 这类已上线商业产品**（③厂商）：记忆层**没有提问记录层、没有失效/推翻机制**、
`inject_context` 默认 true 把**全部记忆无上限注入提示词**、写侧只有白名单闸且**不公开任何阈值**。

⇒ 我们的候选层**在商业产品里确无对应物**（对我们是利好：没人占位）。
⚠ **但同一件事的另一面是**：**市场也没证明它有价值**（对我们是风险）。
⇒ **支持"先做最小可查询集"，不支持"按完整三层一次做完"。**

### 1.8 TierMem：**sufficiency router 不可机械判**，但它旁边那块能抄

| 抄什么 | 出处 | 等级 | 判断 |
|---|---|---|---|
| ❌ **sufficiency router 本体** | 线上默认走 LLM 提示词；机械版阈值全是手调常数（`s_max<0.3`、`熵>1.5`、threshold 0.5），**源码无注释、论文无依据** | ⑤ | **不能当尺子搬** |
| ✅ **证据链接的确定性化** | `_link_facts_to_pages`：模型只出 `(fact, evidence_quote)`，**`source_pages` 由确定性子串匹配决定**（兜底 = 关键词半数阈值） | ④ | **最值得抄的一条**——把"模型引条款"变成"子串核条款原文"，**幻觉链接被结构性消灭**，不需要额外评审 |
| ✅ **写侧 ID 机械校验后回落** | `_is_valid_memory_id` 校验后回落 ADD | ④ | 能抄 |
| ✅ **「答案必须逐字在原文里，否则不走摘要」** | router.py:600 | ④ | **机械可判**，正对上我们实测的 53% 零字面重合 |
| ⛔ **反着抄**：失败方向 | 两个 router 失败方向相反——训练版异常时 fail-closed，**线上版空响应/解析失败 fail-open** | ⑤ | **我们必须把默认设成「不答」** |

**许可**：`FreedomIntelligence/Tiermem` 根 LICENSE 逐字 = `MIT License` / `Copyright (c) 2025 FreedomIntelligence`（④）。

### 1.9 许可证陷阱又坐实一次（这一条是**方法**，不只是结论）

`joelparkerhenderson/architecture-decision-record` —— 看着最像通用 ADR 模板、README 被广为引用，
根 `LICENSE.md` 逐字是 **CC BY-NC-SA（含非商用）**。⇒ **不可抄。**
其余（读根文件原文、非 API 字段）：`npryce/adr-tools` = **GPL-3.0-or-later** ⚠；`thomvaill/log4brains` = **Apache-2.0** ✅；`ThakiCloud/SKILLRET` 根 LICENSE **404** ❌；另有 **7 个仓 ROOT LICENSE NOT RETRIEVED**。

⚠ **方法论两条**：
1. **GitHub API 已从本机 IP 限流**（盘上两个抓取件内容就是 `API rate limit exceeded`）⇒ **许可证核验必须走 `raw.githubusercontent.com`**。
2. **"广为引用"不代表可抄** —— 引用量与许可无关。

---

## §1.5 ⭐ 续上后拿到的一条**省掉一整轮返工**的结论：`s*` 不能直接套，且给了绕法

> 出处：RE 代理，`var/tmp/study/problems/RE-eval.md`（**我已回一手件逐条核过**：
> `s*` 定义见 `raw/RE/2605.07313.txt:202`、α=0.7 见 `:223`/`:409`、单位见 `:207`；
> Top-50 那句见 `raw/RE/arxiv-2608.21755-html.html:1527`/`:1936`；敏感性区间见 `:1590`）。

### 1.5.1 `s*`（arXiv 2605.07313）**不能**直接抄成我们的验收指标

逐字定义（Def 4）：`s*_α(A,M;B) := N_irr(s_j)`，α=0.7；若无则记 `s* > N_irr(s_4)`。
阶梯（Table 4）：s0=0 / s1=100 / s2=200 / s3=300 / **s4=400** 条**无关会话**，等距。

**四条不套的理由**：

| # | 理由 |
|---|---|
| **R1** | **它是「干扰物密度尺」，不是「语料规模尺」**：干预是往**固定的** `E(q)` 旁边加无关会话，`E(q)` 全程不变 ⇒ 测的是"已知答案在噪声里还能否被找到"；我们问的是"522k 条里那条对不对"——**方向相反** |
| **R2** | 它要求逐查询证据标注（构造 `ℋ^(s)(q)` 必须先 identify `E(q)`）⇒ **我们没有标注数据**，整套阶梯构造不出来 |
| **R3** | 🔴 **预算轴在我们这儿结构上恒为常数**：`R(τ)=Σ1[a_t∈A_ext(M)]` 按轨迹检索调用次数计（B=2/3/5）；**我们是单轮多路 ⇒ R≡1 ⇒ `p_exh`≡0 ⇒ `Pass@B` 退化成 `Pass`，整根预算轴携带零信息** |
| **R4** | **量程差约 1300 倍**：全篇最大格 = 401.2 会话 / 1.03M token；我们是 **522,021 条** ⇒ 任何 `s*` 数值对我们无意义 |

### 1.5.2 ✅ 但给了**绕过 R2 的唯一合法路径**

**evidence-preserving 原则**——只要求金标条款**始终在库内**，**不要求它在 top-k 内**。

⇒ 于是规模尺子可以这样造：**同题、语料逐级扩容、且保证金标条款始终在库内**。
**代理据此给的单轮版定义**（`⑤推断`，我核过逻辑自洽、还没实测）：

```
N*_α = min{ N : r(N) < α }        # N = 库里的条款数
ρ*_α = N*_α / N_min                # 语料倍数，可跨库比较
```

### 1.5.3 ⭐ 顺手捡到一条**最直接可抄**的东西：四臂归因阶梯

**ECHO §VI-C 末段逐字**：
> "A post-gate **Top-50 diagnostic places many gold turns at ranks 16–41, implicating candidate coverage and ranking rather than ingestion.**"

⇒ **这是"检索失败三成因"的现成机械判据**，而且**只要一个数**：

> **门失败后立刻把 k 从 10 抬到 50，看金标落在第几名**
> · 落 **16–41** ⇒ **进了候选集、没排上** ⇒ 修**排序层**
> · 落**不进 50** ⇒ **压根没召回** ⇒ 修**召回层**

**我们前五 6.8% / 前二十 24.5% 的现成数据正好可以这么再切一刀**（拉到前五十看落点）⇒ **零新语料、零新标注就能跑。**

**代理给的四臂版本**（可机械分出三种成因，用嵌套差值）：
`A 真跑` / `B 候选集强插金标` / `C 上下文置入金标` / `D 只给金标`
⇒ ①不在候选 ②排序噪声 ③干扰伤害。

### 1.5.4 ⚠ 同时核到一条**引用时必须带的话**

ECHO 那 91 题**只来自 8 个 history**，作者自己给了**簇级敏感性区间 `[−25.5, +25.0]`（跨零）**，
逐字结论是 "we therefore conclude only that Mem0 is stronger on…"。

⇒ **"检索指标 ≠ 答案质量"这个结论方向成立，但**那一组具体数字的置信区间跨零**，引用必须带这句。**

**另一条规模证据**（ECHO Table V 预注册门）：同一冻结配置，1 个 history（开发行）→ 5 个预注册 history（新鲜门），
三道检索门槛全不达标，事件排序切片掉到 Hit@10 **40.0%** / turn recall **14.71%** / session recall **21.57%**，
且作者明说该结果 **"does not characterize BEAM-1M/10M"**（未测到更大规模）。

---

## §4 顺手记下的一条元教训

**"两个测量如果共用同一个函数，它就是一个测量。"** —— 上面 §1.1 那位作者的第二次测量（1.7% 误伤代价）就是这么废掉的，**他自己撤回了**。

⇒ 这与我自己踩的坑同型：今天我纠正总纲 A5 时，也是因为**"effective 521,984"这个数来自一处查询口径**，而真库实算是按 `doc_meta` 分组。**数字没错，错的是把条款行的数当成了文档行的数。**

---

> **边界**：本文件**不排期、不改任何判据**。§2 的"可借鉴"仍是候选（要不要做、什么时候做由业主定）。
> 调研线仍在跑（我这一侧另派了 6 个代理，见会话记录），回齐后本文件继续追加，**最终汇总成一张三栏对策表**（抄哪一处 / 不抄哪一处 / 我们独有的那一条）。
