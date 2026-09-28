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
> 🔴 **更正（2026-09-28，RH2 组 + 我自己复现）**：上句「**没有工具能扫**」**对 PowerShell 不成立**。
> PSScriptAnalyzer 的 `PSUseDeclaredVarsMoreThanAssignments` 一次命中我们那个"22 条测试全绿零红"的缺陷，
> **且原始件零误报**（我跑的：`var/tmp/verify-pssa-command-layer.ps1`，只读主仓）。
> ⇒ 详见 **§1.13**。**仍成立的部分**：对"恒假条件/检查对象错位"它管不了。**原句留痕不删。**

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
| **7** | ~~**命令层空验证的机械检测**~~ | ~~D 组已证：成熟工具全在测试层；**命令层没有工具能扫**~~ ⇒ 🔴 **已被 §1.13 推翻（对 PowerShell 不成立，我已自己复现）**。仍成立的部分：**恒假条件**（检查对象错位）PSSA 管不了 |

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

### 1.10 🔴 我一直在转述一个**配对错了的数字**，以及 ECHR 那条被高估的强度

> 出处：RA 代理，`var/tmp/study/problems/RA-retrieval.md`（36 KB）。**我已回一手件核**。

#### 1.10.1 ⭐ 更正：「BM25 0.822 打败全部 12 个稠密模型」——**数字配对错了**

| 我此前写的 | **实际**（`raw/RA/bekko-text.txt`） |
|---|---|
| 「BM25 0.822 / **最强稠密 0.740**」 | **0.822 与 0.740 都是 BM25 自己的分**，分属两个基准：NanoLongEmbed **0.822**、NanoMLDR **0.740**（`:3929`）。各基准最强稠密分别是 **0.706 / 0.681**（`:3937` / `:3946`） |

**更要命的是同一篇论文自己给了对照**：短文本 NanoBEIR 上 BM25 = **0.465**，而它逐字写着
**"every dense model beat BM25"**。

⇒ **我们 522,021 条条款是短文本单元** ⇒ 「BM25 打败 12 个稠密模型」**不能搬到我们这儿**。
⇒ **谁要据此主张"别投向量了、回到 BM25"，这个推论是反的。**
⚠ Bekko 自己披露 MLDR 是 **BGE-M3 论文自建、且 BGE-M3 在其上训过** ⇒ 披露诚实，**结论照读、不可外推**。
（等级：③厂商/作者自报）

**这条同时更正了 `F-chunking.md` 与 `B-scale.md` 里同样的措辞**——它们写的是同一句话。

#### 1.10.2 ⚠ ECHR「按相似度排比随机还差」——**强度被我们高估了**

| 项 | 实际 |
|---|---|
| 出处 | arXiv **2606.03728**（ASAIL 2026 **workshop**、**两人**、TUM、**自报**） |
| 引用 | **Sciverse CITATIONS = 0**，**无人复现、无人反驳** |
| 🔴 最要紧 | **Table 3 里根本没有 random 那一行** —— "比随机差"是用 MGR=37.4 对比 top-50 随机期望 25.5 **反推**的，而摘要与结论**当实测事实陈述** |
| 覆盖面 | **只测了 GTR-T5-XL 一个稠密检索器，没有 BM25 路** |

⇒ **方向可用**（与我们"47% 里只有 4.4% 进前五"同病），**强度不可用**。

#### 1.10.3 我们想要的那两条出路（PRF / HyDE）**被独立测出是负的**

| 路线 | 结果 | 出处 |
|---|---|---|
| **常规 PRF**（BM25 + Rocchio） | TREC DL 2019 上**自己就是负的**：MAP 0.2697→**0.2350**、nDCG@1 0.5972→**0.5000**（均显著）。逐字 "weak signals hurt the effectiveness significantly across all metrics, with some losses **even larger than 60%**" | **①SIGIR'22**（`github.com/ielab/Noise-PRF`）⚠ **它故意用 Rocchio 不用 RM3**（为做同策略对照），是同族不是本尊 |
| **HyDE** | 0/159 字面命中的安全公告集上：**BM25 0.641 > HyDE(Llama3.3 **70B**) 0.151 > E5-large 0.069**。逐字 "Adding 70B parameters … **cannot bridge a vocabulary gap that originates in the query itself**" | CAR（**solo 预印本零引用 ⇒ 当强假设不当事实**） |
| ✅ **真解法：结构化** | 「Regex-NER 抽实体后查索引」= **TCA@5 1.000**，且 "requires no fine-tuned embeddings, no cross-encoder reranking, and **no oracle labels**" | CAR |

#### 1.10.4 ⭐ 建议抄的（按优先级）

| 优先 | 抄什么 | 去哪 |
|---|---|---|
| **P0** | 🔴 **`bge-small-zh-v1.5(512)` → `bge-base-zh-v1.5(768)`**：C-MTEB Retrieval **61.77 → 69.49（+7.72）**，而 large 才 70.46（**只差 0.97**）。**本机现装的正是那个差 8.7 分的 small。** 不需任何新方法 | HF `BAAI/bge-base-zh-v1.5` |
| **P1** | 受控词表路加**可信度闸门**（共识法生成难度标签 + 分类器预测难度，高难走回退） | *Same but Different*（ACM SAC 2019） |
| **P1** | 歧义消解形状：同名候选集 → 取每个候选的**上位类**当义项指示 → 上下文 × 上位类相似度（**法律域已上线**） | **Lynx**（Inf. Systems 2022） |
| **P2** | 结构化路的可行性判据 Δ(q)（Prop 2 / Thm 4） | `github.com/andremir/car-retrieval` |
| **P2** | PRF **开关化而非禁用**：只在反馈信号中/强时开 | `Noise-PRF` 的 strong/moderate/weak 分级 |
| **P3** | 冷启动造评测集：对比对 + 种子查询 + 对比式生成 topicality 标签 + Virtual Judge；**查询长度 KL 0.66 vs InPars 12.03（好 7.5×）**，生产在跑 | **Airbnb**（arXiv 2026-05-20） |

⛔ **明确不要投**：PRF/RM3 全量、HyDE、通用同义词扩展、多向量切片、拿 LLM 裁判分当训练信号。

#### 1.10.5 三条与既有判断的关系（如实分档）

| 关系 | 内容 |
|---|---|
| ✅ **加强了"继续攻零重叠"** | **"评测集造偏了"这个台阶没找到任何支撑**，反而三方独立支持「零重叠是 IR 经典病」：**Furnas 1987** 词面重合只有 **7%**、SIGIR'22 弱反馈下 PRF 掉 20–60%、CAR 零重叠下语义检索崩到 0.07 |
| 🔴 **对我们不利** | CAR 实测 **MTEB 排名越高、参数越多，在零重叠任务上越差**（E5-large 0.069 < MiniLM 0.132 < BM25 0.641），逐字 "a practitioner optimizing for MTEB would select the model that performs worst here"。⇒ **这是对我们"按 C-MTEB 选模型"这个做法本身的一次警告，且与 1.10.4 的 P0 方向相反。** 代理按证据等级记为「**需本机实测验证的假设**」，**没有拿它否定 P0**——这个处理我认同 |
| ✅ 有利 | 已证伪的「多向量切片」在 **KoBankIR（ICAIF'25）独立复现**：BGE-M3 Multi 0.6789 **<** Dense 0.6848，Sparse+Dense 0.7109 最好 |
| ⚠ 弱证据 | 多义词歧义（Carmen et al. 1997）说明 **53% 里有一部分是"提问本身有歧义"，那部分检索修不了**，要澄清式交互。**建议把 53% 拆成「术语不懂」/「说法有歧义」两堆再决策——本轮没有这个拆分数据** |

#### 1.10.6 RA 明确没找到的

ECHR 那条的复现/反驳（0 引用）｜**RM3 本尊**在零重叠上的独立数字（那篇改用了 Rocchio）｜
**中文国标术语级**的公开基准（只有类案检索 IEEE Access、金融 KoBankIR）｜
中文小模型 vs 大模型的**独立第三方**复核（⚠ 「小模型接近大模型」**全部出自 BAAI 自家模型卡③**）｜
国标条款→术语表的现成抽取器（CAR 靠 CVE 这类**规整 ID**，与我们难度不同）。

### 1.11 ⭐⭐ RR 组带回**三条直接改我们判断**的证据（每条我回一手件核过）

> 出处：`var/tmp/study/problems/RR-ranking.md`（27.9 KB）。核验：
> k=60 逐字我从 `raw/RR/cormack2009-rrf.pdf` 抽的；
> STARD 逐字在 `raw/RR/arxiv-2406.15313-STARD-chinese-statute.txt:431`；
> 波兰消融逐字在 `raw/RR/polish-statutory.txt:101`。

#### 1.11.1 `k=60` 的出处查到了，**而且论文自己说"无关紧要"**

逐字（Cormack, SIGIR 2009）：
> "**k = 60 was fixed during a pilot investigation**"；"four pilot experiments, each combining the
> results of 30 configurations of Wumpus Search applied to four different TREC collections"；
> "indicated that **k = 60 was near-optimal, but that the choice was not critical**"

**Table 1（pilot 那组）**：k=0 → .2072 ｜ 20 → .2134 ｜ 50 → .2144 ｜ 60 → .2145 ｜ **70 → .2146（实际最高）** ｜ 100 → .2142 ｜ 500 → .2098
⇒ **k∈[20,100] 的极差只有 0.0013 MAP（≈0.6% 相对）**；**k 是一片平坦高原，不是调出来的点**；陡坡只在 `k<10` 与 `k>100`。
论文给的机制：`The constant k mitigates the impact of high rankings by outlier systems.`

⚠ **但 k<20 那一段论文没测，Qdrant 官方文档测了**：单目标场景最佳 k 是 **2 或 5**；CodeSearchNet（1 相关/查询）
k=5=0.6580 vs k=61=0.6258，**差 0.0322**；**`k=2` 与 `k=61` 在 WANDS 上 42% 的查询换掉了 top-1**。
⇒ **我们是单目标场景**（专家直接输术语的上限 68.8%）⇒ **优先扫 k∈{2,5}**，但**必须实测，不许直接改**。

#### 1.11.2 🔴 推翻我预期的一条：**法规语料上 rerank 被独立实测为正，而且是全study最大效应**

**波兰成文法**（arXiv 2608.30929，**82,508 条法条 / 1,133 部法 / 300 道波兰律师资格考试真题**，单目标标签）：
**去掉 reranker，Hit@1 72.3% → 44.7%（−27.6 pp，p<0.001）**，MRR 0.764 → 0.524。
逐字：**"Reranking acts on ordering rather than on candidate coverage"**（Hit@20 只掉 9.5 pp）。

⚠ **三条折扣必须一起记，否则会误用**：
1. 它用 **listwise LLM over 40 候选**，**不是 cross-encoder** ⇒ **不能直接推给我们的 `bge-reranker-base`**；
2. 🔴 **增益完全没传到答案层**：citation accuracy 67.3% vs BM25 66.0%（p=0.61）/ RRF 67.7%（p=1.00）/ dtf 70.3%（p=0.19）**全无统计差异**。逐字 "the generator is tolerant of position within the retrieved context but sensitive to presence"；
3. **作者自曝覆盖率混淆**：代理标注只覆盖 27.0% 语料却 100% 命中金标；原话是 "some unknown share of their rank-one advantage is attributable to that asymmetry rather than to the retrieval design. **We did not measure… we do not have an experiment that separates the two.**"

⇒ **改写我们既有说法**：我此前写「修好 rerank 大概没收益」——**部分被推翻**。
我们唯一的实测是「**术语候选上为负**」，而那**确实不是条款级** ⇒ **不能外推**。
另有一条机制补全：那次为负**很可能只是拿默认/手调融合当分母**（见 1.11.4 第 2 条）。

#### 1.11.3 ⭐⭐⭐ **同语言、同"外行问法"、同"按条检索"的尺子：零样本 BM25 打赢全部神经模型**

**STARD**（arXiv 2406.15313，MIT；**1,543 条真实法律咨询外行问题 / 55,348 条中文法规**）逐字：
> "Under the zero-shot setting, traditional lexical matching techniques **surpass both general and
> legal-domain pre-trained language models**"

| 方法 | R@5 |
|---|---|
| **BM25** | **0.3349** |
| Chinese-RoBERTa | 0.3216 |
| Lawformer | 0.2411 |
| SEED | 0.2897 |
| SAILER | 0.2330 |
| coCondenser | 0.1120 |
| 🔴 **Dense-CAIL**（**在法考数据上训的**） | **0.0887 —— 比 BM25 差 3.8 倍** |
| ✅ Dense-STARD（**本域微调**） | **0.5206** |

**独立复现**：bBSARD（arXiv 2412.07462，22,417 条比利时法条 + 公民真实提问）逐字
"zero-shot dense models only fully outperforming it **starting from 300 million parameters**"；
法/荷双语 BM25 nDCG@10 21.54/20.07，而微调小模型 FlauBERT-base(138M) 46.69 / CamemBERT-base(111M) 44.25。

⇒ **这两把尺子比 Bekko 那条更适合我们对标**（同语言、同"外行问法"、同"按条检索"）。
⇒ **两条对我们直接生效的推论**：
**① 域内微调是唯一真拉开差距的手段**（0.5206 vs 0.3349），零样本换模型基本白换 ——
**这与 §1.10.4 的 P0（换 bge-base-zh）方向一致、互为加强**；
**② 但"在法考数据上训的 Dense-CAIL"反而最差（0.0887）** ⇒ **微调数据必须同分布，训错分布比不训更糟**。

#### 1.11.4 🔴 对我们六路融合的**直接警告**（这条最该进方案）

波兰文逐字：**`oracle-doc`**（给对法、篇内**随机**条文）citation **37.7%**，
**比闭卷 47.0% 还低 9.3 pp，p<0.001**，原话：
> **"Plausible but incorrect provisions displace correct parametric knowledge."**

⇒ **把"不像的条款"塞进前五，可能比不塞更糟。** 这直接关系到我们六路加权：
四路中若有近似但错误的候选，**它们会挤掉真正的那条**。
⇒ 这是"要不要继续加检索路"的一个**新约束**（此前我们只论证了"加路有用但不够"）。

**另一条把我们的 4.4% 变成上界**：波兰文引 Smyński-Pohl (2025) 测到
"问题**由目标条文导出**"与"**老百姓提问**"两类数据集之间**约 45 个 nDCG@10 的差距**，
并警告前者 `too optimistic`。**我们那"47% 有字面重合"的批次正是"前者"** ⇒ **4.4% 是上界。**

#### 1.11.5 建议抄的参数（按优先级）

| 优先 | 抄什么 | 依据 |
|---|---|---|
| **P0** | **候选数从 10 起，不要 50/100** | Qdrant 逐字：10 候选 CPU 上 `47 to 156 ms per query`；而 100 候选 0.5–5 s/query，我们 `bge-reranker-base` CPU 16–45 docs/s ⇒ **0.2–0.5 查询/秒**，与我们第二路预取 0.6–1.5 ms **差 3 个数量级** |
| **P0** | 🔴 **rerank 的分母必须换成"调过的融合"** | Qdrant 实测 WANDS：`rerank +0.039 over default RRF`，但 **`−0.008 vs tuned fusion`**；`tuned fusion beat all four models at every candidate count`。**我们若拿 k=60+手调权重当分母，很可能复现这个 +0.039 假阳性** |
| **P1** | **权重是绝对值且必须与 k 绑定** | 逐字 "The pair is absolute, so (1,2) and (2,4) are two different settings"、"Settle k first, since a pair is only valid for the k you tested it with" ⇒ 我们的 `exact`=2.0 **必须和 k 一起报、一起扫** |
| **P1** | **先核我们 k 的下标口径**（纯代码事实） | 1-based `r`+k=60 ⇒ 等价 Qdrant k=61（与 Cormack 口径一致）；0-based+60 ⇒ 等价 k=59、**偏 1** |
| **P1** | rerank 前跑两个机械诊断 | ① 用 reranker 的 tokenizer 量 query-doc 对的 **p95 长度** vs 模型窗口（512）；② 核模型卡的语言/领域。Qdrant 说这两条解释了它表里 "every loss" |
| **P2** | 客户端 `(-score, +doc_id)` 二次排序 | ⚠ Qdrant 实测 k=61 下并列只 2.8%，**优先级低**；真问题是**同号条款**（业务上真等价）⇒ 走 **grouping**（每 `(标准号,条号)` 组只回一条），不是 tie |
| **P2** | BM25 `b` 值得扫（`b∈{0,0.4,0.6,0.75}`，k1 固定 1.2） | ⚠ **转述**：波兰文引 Louis & Spanakis (2022) 对法条调出 `k1=1.0, b=0.6`。**代理未回核原文，标为转述** |
| ⛔ **不抄** | `jina-reranker-v2`（**CC-BY-NC-4.0 非商用**）；DBSF | DBSF 前提不成立：我们 4 个元数据路输出的是**布尔/计数**不是连续分，它要的"分数分布"没有 |
| ⛔ **不抄** | 「长片段天然吃亏」这个假设 | **方向被说反了**：波兰文逐字 `Max-pooling gives longer articles more opportunities to score`；法条均长仅 143 词 |

#### 1.11.6 验收尺子**必须加答案层指标**

1.11.2 那条已经演示了：**rerank 赢 27.6 pp 排序指标，答案层 p=0.61 无差异。**
⇒ **我们若只测"前五精度"，会得出"rerank 有效"而下游一分为零。**

#### 1.11.7 「其余四路 ≈0」这条要**改读法**（不是推翻，是限定）

- **强支持**：波兰实测 **RRF 61.7% 与 BM25-raw 61.7% 完全相同**（加权 RRF 对最强单路**零增益**），dense 52.3% 反而低于 BM25。STARD / bBSARD / Bekko 三方独立佐证。
- ⚠ **但方法学上是下界**：FunnelAudit（arXiv 2609.06964）在九路漏斗上实测
  `single-control ablation recovers only 0.36–7.45%` ⇒ **路间重叠互相遮蔽**。
- ⇒ **「≈0」应读作"单路消融测不出"，不等于"真为 0"。** 这一句要写进我们的判据说明。

#### 1.11.8 RR 明确没找到的

「先融合再 rerank」vs「先 rerank 再融合」的**受控对照**（搜完 arXiv API 全量 86 命中 + 4 组 web 搜；
最接近的波兰 ASCR-H vs DTF **成本结构不同**、不是单变量对照）｜中文 cross-encoder 在**中文法律文本**上的
第三方实测数字（C-MTEB 榜单抓不到表，`C_MTEB/leaderboard.csv` **404**）｜BM25 k1/b 在**中文短文本条款**上的
公开结论（STARD 直接用 Pyserini 默认、**根本没报数值**）｜「加一条弱路会不会让 RRF 掉分」的直接实验。

### 1.12 🔴 RE 组收工：解开一个硬约束，但**它的 ALCE 数字我用错了列**

> 出处：`var/tmp/study/problems/RE-eval.md`（52.5 KB / 11 节）。**这一节包含一条我自己核出的实质错误。**

#### 1.12.1 ⚠ 先记本轮的**核验缺口**（不是我推责，是事实）

- RE 组**经 ar5iv 读了 6 篇全文但没落盘**（它自己在收工信里声明了"反限流纪律"）⇒ **那 6 篇的数字目前是"经代理转述"，我不能独立复核**。
- 我核 `raw/RE/`：唯一的全文件是 `2605.07313.txt`；`arxiv-2305.14627-html.html` **其实是 arXiv 的 404 错误页**（逐字 `No document for '2305.14627v3'`），
  而 abs 页里**没有** 38.3/40.4/32.9/20.8 ⇒ **ALCE 那组数字在盘上根本无从核**。
- ⇒ 我**自己去 ar5iv 取了 ALCE 原文**（480,329 B，标题逐字 *Enabling Large Language Models to Generate Text with Citations*）逐格重核 —— 见下。

#### 1.12.2 🔴 更正：ALCE 那组数字**我用错了列，两个结论的方向都被带偏**

代理报的是：「ASQA 上 ClosedBook **38.3** → 检索 **40.4**（**只买 2.1 pp**）；QAMPARI 上 ClosedBook **32.9** → 检索 **20.8**（**检索有害**）」。

**我回原文逐格重核（`alce-ar5iv.html`）**——那张表是**四列**，代理在 ASQA 用了「引用召回」列、
在 QAMPARI 用了「正确性」列，**列不一致**：

| 基准 | **正确性 Correct.** | 引用召回 Cit. Rec. | 引用精度 Cit. Prec. |
|---|---|---|---|
| **ASQA**（GPT-4 行） | 闭卷 **52.7** → ChatGPT+5psg **66.6** ⇒ **检索帮助很大（+13.9）** | 38.3 → 40.4（+2.1） | 26.7 → **73.6** |
| **QAMPARI**（ChatGPT 行） | 闭卷 **32.9** → 检索 **20.8** ⇒ **检索有害（−12.1）** | 19.8 → 20.8 | 10.0 → **20.5** |

**正确的读法**：
- **ASQA 上检索是有大帮助的**（正确性 +13.9，引用精度从 26.7 拉到 73.6）；「只买 2.1 pp」是**引用召回**这一列、且闭卷基线本来就低（它几乎不引）。
- **QAMPARI 上检索确实有害**（正确性 −12.1）。
⇒ **两句话都要说、且必须标清是哪一列。** 代理那版会让人以为"检索在 ASQA 上也基本没用"——**那是错的**。

#### 1.12.3 ⭐⭐ 本轮最大的一条放松：**「没有标注数据」这个硬约束被解开了**

**Sufficient Context**（arXiv 2411.06037）—— 我核到**摘要**逐字：
> "we develop a new notion of sufficient context, along with **a method to classify instances that have
> enough information to answer the query**"；"the prompts used in our **autorater** analysis are available
> on our github"

⇒ **它用的是「autorater」（模型判上下文够不够），不是金标。**
⚠ **未核到盘上的两句**：代理报的逐字 "**does not require a ground truth answer**" 与 **Gemini-1.5-Pro 判别器 Acc 0.930（115 条人工标注，Table 1）** 都在正文，**而正文没落盘** ⇒ **这两句我标为「经代理转述、未独立复核」**，不当作已核。

⇒ **对我们的意义**：这条一旦成立，**评测不必等金标修好**就能先开一条轴
（判"检索到的条款够不够回答"，不需要知道正确答案是什么）。
⚠ 但要连着 1.6 那条一起看：**Sufficient Context 同时证明大模型"该不答时硬答"** ⇒ 充分性判据必须与派生层可信度解耦。

#### 1.12.4 建议抄的位置（可核性已标注）

| 抄什么 | 在哪 | 可核性 |
|---|---|---|
| **三成因①/② 判据**（把 k 从 10 抬到 50 看金标落点） | ECHO §VI-C 逐字 "A post-gate **Top-50 diagnostic places many gold turns at ranks 16–41, implicating candidate coverage and ranking rather than ingestion**" | ✅ 已核（`:1527`） |
| **单轮规模尺**：文档按**是否含答案**切 positive/negative，扫**噪声比 {0,.2,.4,.6,.8}** | RGB（`2309.01431`，AAAI 2024，中英双语）。**它给了明确门槛**：噪声比 **>0.8** 简单题显著下降、**>0.4** 需整合多文档的题就崩（α=0.05） | ⚠ 经转述 |
| **答案片段字段**：ALCE §3.2 三分支（EM 子串 / recall-5 饱和 / **LLM 生成 3 条 sub-claims 再做蕴含**）；最后一条**不需要标准号存在于真库** ⇒ 绕开 70/90 失效的已发表形状 | ALCE `2305.14627` | ⚠ 经转述（我只核到表，没核 §3.2 正文） |
| **CoF 流水线**（管住引用漂移）：Self-Instruct 造题 → **128-token 块级序号引用 `[k]`（序号不漂移）** → 块内选句 → **丢弃引用数不足的样本**；可借 **LongCite-45k（44,600 条中英双语）** | LongCite `2409.02897`（ACL Findings 2025） | ⚠ 经转述 |
| **更准的判据**：LongCite 逐字点名 ALCE 不够准（"may overlook partially supporting cases due to the limited capacity of the NLI model"）⇒ recall 改 **0/0.5/1 三值**、precision 放宽为「至少部分支持」、裁判换 GPT-4o | 同上 | ⚠ 经转述 |
| **裁判去偏**：`2406.07791` 的 RS/PC/PF 三公式；两条方法论比数字重要——**「RS 是 PC 的前置」**（Gemini-1.5-flash RS 0.04 却 PC 0.92 = 假的高一致）、**「k 候选 → k 个排列、每个候选各占一次首位」**。换边 18%–45% 判断翻转 | Dartmouth | ⚠ 经转述 |
| **规模边界（长上下文那条）**：`2409.01666`(NVIDIA) 逐字声明其量程：每题一篇 15 万词文档、候选 ≤~1,170 块、全文 117K–196K token、sweet point **16K–48K** ⇒ **全部「检索打败长上下文」证据都在这个量程内，比我们小 2–3 个数量级、不可套** | 同上 | ⚠ 经转述（但与我们的量级差是算术，可信） |
| **省钱否定结论** | 顺序保持类优化**只在 k≈100 块时才有收益、k=8 无差别** ⇒ **我们 k=5/20 不必做** | ⚠ 经转述 |

#### 1.12.5 对我们既有判断的四条影响

| # | 关系 | 内容 |
|---|---|---|
| **F1** | ⚠ **加强金标问题，但要改我一句** | Sufficient Context 逐字点名 "**the ground truth answer conflicts with the answer provided in the source**" ⇒ 我们的 70/90 是**已发表的公认病**。**但天花板不是 20/90**——因为 **35–62% 的题在上下文不足时仍靠参数知识答对** ⇒ **那部分既不能算检索的功劳，也不能算充分性的功劳**。我此前说"检索已经打在天花板上"**要改口** |
| **F2** | ⭐ **推翻** | 「没有标注数据是硬约束」——见 1.12.3 |
| **F4** | ⚠ **削弱**「多轮/迭代检索是要走的路」 | ALCE 迭代检索**不涨反跌**（ASQA 32.4<40.4、QAMPARI 17.2<20.8）。⚠ **口径必带**：他们的迭代**只在已取回的 top-100 内搜** ⇒ **不能据此说"全库迭代无用"** |
| **F7** | 🔴 **收紧**「LLM 裁判可用」 | 换边 **18%（GPT-4）到 45%（listwise）** 判断翻转；⚠ **质量差距越小偏置越强** ⇒ **我们那 90 条里"两系统都半对"的题，正是裁判最不可靠的题** |

#### 1.12.6 RE 明确没找到的

「超出 ≤1.5M token 后结论反转」的**明文声明 —— NOT FOUND**（搜过 RAG vs long-context boundary / context rot 等）
⇒ 能拿到的**最强负面证据**是 ECHO 的 BEAM 新鲜门：同配置、**1 个 history → 5 个预注册 history**，
三道预注册门槛**全不达标**（事件排序切片 Hit@10 掉到 **40.0%**），且作者明说 **"does not characterize BEAM-1M/10M"**。
另：中文法规条款 + 抽取式答案片段的公开数据集（NOT FOUND，LongCite-45k 领域不匹配）｜自我偏好量级与 PriDe 实测（未查实）｜
零样本重排「bubble 退化」数值（存疑未核）。

### 1.13 🔴🔴 RH2 推翻**我自己写进这份文件的话**：命令层空验证**有工具能扫**

> 出处：`var/tmp/study/problems/RH2-verification.md`（12 节）。
> ⚠ **我此前在 §2.4 写的是**：「**所有这些工具都在测试层。** 而我们的 D4 缺陷……是**命令层**空验证
> ⇒ **没有工具能扫**」——**这句是错的，就 PowerShell 而言。**

#### 1.13.1 ⭐⭐ 我自己复现了（脚本 `var/tmp/verify-pssa-command-layer.ps1`，只读主仓）

`PSScriptAnalyzer` 的 `PSUseDeclaredVarsMoreThanAssignments` 规则：

| | 命中数 |
|---|---|
| **原始** `scripts/run-gates.ps1`（`$totalForRatchet` 出现 **8** 次） | **0 条** |
| **变异件**（7 处读取改回 `$totalRan`、只留第 475 行赋值 ⇒ 只剩 **1** 次） | **1 条**：`Line 475: The variable 'totalForRatchet' is assigned but never used.` |

⇒ **成立**：原始件零误报、变异件一次命中。
**那个"把 8 处逐字改回、22 条相关测试全绿零红"的缺陷，一条静态规则就抓到。**

**可直接用的门禁命令**（代理给出，我未跑门禁形态、只跑了规则本身）：
```powershell
$guard = @('PSUseDeclaredVarsMoreThanAssignments','PSReviewUnusedParameter')
Invoke-ScriptAnalyzer -Path scripts -Recurse |
  Where-Object { $_.RuleName -in $guard } | Tee-Object -Variable d
if ($d) { exit 1 }
```
⚠ 本机 PSSA **未装**（`Get-Module -ListAvailable` = 未安装）；子代理装在 `var/tmp/study/r2-pssa/`，**我用的就是那一份**。
⇒ **要不要装进本机、如何进 `pyproject`/门禁，属未定的实现决策，本文件不排期。**

#### 1.13.2 ⚠ 它同时**实测否定了 PSSA 能管什么**（这半也要记）

- 🔴 **PSSA 看不见恒假条件** ⇒ 缺陷②（"检查对象错位"：只查"文案在场"）**它管不了**；
- 🔴 `PSAvoidUsingComputerNameHardcoded` **只匹配 `-ComputerName` 这类 cmdlet 参数**，
  对 UNC、`$env:COMPUTERNAME`、**硬编码 `D:\...` 绝对路径全部 miss**
  ⇒ 我们"硬编码主仓绝对路径"那条**不被它覆盖**。

#### 1.13.3 其余可抄项（按优先级；能直接用的命令优先）

| 优先 | 抄什么 | 命令 / 出处 | 治哪条 |
|---|---|---|---|
| **P0** | **esbuild metafile 断言源文件真的在产物里** | `npx esbuild <entry> --bundle --metafile=var/tmp/meta.json --outfile=plugin/client.js` → 断 `meta.outputs['./plugin/client.js'].inputs['./plugin/client/KsX.tsx'].bytesInOutput > 0` | 缺陷② **检查对象错位**（PSSA 管不了的那条） |
| **P1** | `PSUseCompatibleSyntax` | `-Settings @{Rules=@{PSUseCompatibleSyntax=@{Enable=$true;TargetVersions=@('5.1','6.0')}}}` ⇒ 代理**实测抓到 2 条**（`??=`、三元） | pwsh 7 语法漏到 5.1 单机 |
| **P1** | 依赖语义三件套 | `pytest -rxXs` 的形状：**独立 skip 计数 + 原因字符串 + 强制展开** | 缺陷⑤（**别用 `-UpdateBaseline` 躲开**） |
| **P1** | typescript-eslint 穷尽规则 | ⚠ **必须**把 `allowDefaultCaseForExhaustiveSwitch` 设为 `false`（默认 `true` ⇒ 有 default 就不报） | union 非穷尽（那半） |
| **P2** | `knip` 的 `enumMembers` | `npx knip --include enumMembers`（**默认不报**，须显式 include；只对 enum 形态，纯 type union 未核实） | union 非穷尽（另一半） |

**Go testscript 的一条关键设计**（值得单独抄思想）：
`skip [message]` = skipped，而 **`stop [message]` = "marking it as passing"**
⇒ **Go 自己把"跳过"和"通过"拆成两个结果。**
⇒ 我们那 5 条缺 artifact 的测试，语义正确做法是 **skip + 写明缺什么**，**绝不能当通过**。

**Go 那边的答案形状**（能抄形状、不能抄执行器）：
`-coverpkg` 逐字 "For a build that targets package 'main' … apply coverage analysis to each package whose import path matches the patterns"；
`GOCOVERDIR` 逐字 "Directory into which to write code coverage data files generated by running a `go build -cover` binary"
⇒ **形状 = 跑真命令、落盘覆盖率**；**执行器抄不了**（Go 有插桩编译器 `go build -cover`，PowerShell 没有）。

#### 1.13.4 它纠正的**我任务书里的两处错**（如实记）

| 我写的 | 实际 |
|---|---|
| `q1-pssa-about.html` 是「KDE 的 **Python** 静态分析框架 PSA」 | **是 PowerShell / PSScriptAnalyzer（微软）**。⚠ 我这个错标签很可能让上一轮**放弃了对最对症工具的利用** |
| `q1-go-cmd.html` 与 `q1-go-cover2.html` 是「Go 的命令覆盖率工具」两页 | **两者字节完全相同**（同一份 256,715 B，都是 `pkg.go.dev/cmd/go`），**都不是覆盖率专页**；`q1-go-cover3.html` 是 Rob Pike《The cover story》(2013-12-02)，讲**覆盖率算法**不是 main 包测试 |

#### 1.13.5 ⚠ 它诚实报的**抓取失败**（本轮共有 5 例"HTTP 200 但没抓对"）

`go.dev/doc/tutorial/cover` 正文是 "file does not exist"｜`pester.dev` 是客户端渲染 SPA｜`diff-cover` readthedocs "Project not found"｜
`knip` README 404（真实仓库是 `webpro-nl/knip`）｜**`ts-exhaustive` 与 `codeinvest` 在 npm 上根本不存在**（若之前有结论引用请撤回）。

#### 1.13.6 RH2 明确没找到的

Pester 5 `-Skip` 官方原文（本机只有 Pester 3.4.0）｜**编码检测"谁实测过、准确率多少"**与
**阈值法 vs 旁证式判据的系统对比/失效案例**（charset_normalizer 的 FAQ/CLI 页都是 200 但 404 壳）｜
PDF 字体 ToUnicode 缺失检测｜AST 级产物↔源码比较的成熟工具｜CLI 参数覆盖率专门工具｜
**`ts-exhaustive` 与 `codeinvest` 在 npm 不存在**｜**metamorphic testing 综述原文**（这是"无 oracle"的标准答案，值得下一轮补）｜Adam Tornhill 行为变更分析原文。

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
