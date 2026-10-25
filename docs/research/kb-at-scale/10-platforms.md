# A 线：开源知识库 / RAG 平台

> 抓取日期：2026-10-25（所有 URL 当日可达）
> **评判尺度（业主 2026-10-25 更正）**：不是"能不能装下几千篇"，而是 **10 万+ 份文档、百万～千万条条款**。6,797 篇只是测试子集；真实语料是"中国现行所有法律法规、地方标准、规章制度"，光国标就 3 万多条、每条切几百条。
> 证据档位：【一手】= 读到仓库文件/官方 README（附 URL + 日期）；【转述】= 二手；【推断】= 我的判断；本文件**无【实测】**，我没有在本机跑过任何一个平台。
> 元数据（星数/许可证/最后推送/是否归档）统一取自 GitHub Search API `api.github.com/search/repositories`，2026-10-25 抓取。

## 结论先行（≤15 行）

1. **没有一个平台宣称撑得住 10 万+ 文档**：17 份 README 全文关键词扫描，只有 Infinity 出现数字规模表述（且是向量引擎不是知识库）【一手】。
2. 所有平台的引用粒度上限是**文档 / 页 / 块（chunk）**，没有一个有"条款"这个一级公民；"百万条里定位一条"这件事，市面产品没有对口答案【一手】。
3. 中文法规的**效力状态（现行/废止/被代替）与多版本并存**：18 个项目里 **0 个**有机制，README 一次都没提【一手】。
4. 表格/图/公式/上下标：只有 RAGFlow 在 README 里以"Deep document understanding"名义承载，**没有任何量化指标**；其余 17 个未取证【一手】。
5. **RAGFlow 的 DeepDoc 不要抄**：官方 issue 实测 5 MB / 1,600 页 PDF 在 62 GB 内存机器上 OOM，且无流式、无逐页释放【一手，issue #11822】。⚠ **2026-10-25 独立复核后就地更正（原话保留，不删）**：OOM 数字逐字核实无误（issue 正文 "5 MB size and 1600 pages… almost 62gb ram and it is still not enough"，**state=closed，2026-01-15**）；但"无流式、无逐页释放"出自该线程里 **dosubot 自动回答**，不是维护者结论；"GPU 加速从 v0.22.0 起"同样出自机器人，**维护者 KevinHuSh 明确否认**（"For open-source Deepdoc has nothing to do with GPU."），仓库 README 写 1.0 OSS 的 DeepDoc 用 **CPU 推理**。⇒ **不抄的理由只剩 OOM 本身**（这一条够），GPU 那句作废。
6. RAGFlow 号称 "unlimited tokens / traceable citations"，但它的检索元数据过滤是在 Python 内存里做的，没下推给 Elasticsearch（issue #14412）——这就是"百万级"最先塌的地方【一手】。⚠ **2026-10-25 独立复核后就地更正（原话保留，不删）**：这条**只对 v0.25.0 成立**（issue 正文针对 commit a33d073），**RAGFlow 1.0 改写为 Go 后已实现下推**——`internal/engine/elasticsearch/metadata.go` 的 `FilterDocIdsByMetaPushdown`（不可行时回退内存），另有 `metadata_pushdown_test.go`、`infinity/metadata_pushdown_test.go`；issue 已 closed。⇒ **不能说"这是它当前最先塌的地方"**；它现在未解的是 #11822（解析内存）与 #9647（GraphRAG，仍 open）。
7. Infinity 的 0.1 ms / 15K QPS（百万级向量）、1 ms / 12K QPS（3,300 万文档全文）**是厂商自测**，第三方未复现；且 Windows 只能跑 WSL、CPU 必须 AVX2【一手】。
8. **Verba 已归档**（最后推送 2026-06-08，`archived=true`）；**R2R 最后推送 2025-11-07**（近一年无提交）；**Quivr 已迁仓**到 `The-Vibe-Company/quivr`（旧 `QuivrHQ/quivr` **仍 301 跳转**，不是 404——2026-10-25 复核更正）【一手】。
9. **Morphik 不是开源**：BSL 1.1，生产使用限"月营收 < 2,000 美元"，2029-06-18 才转 Apache-2.0【一手】。
10. **Dify / FastGPT / Open WebUI 都不是纯开源**：Dify 与 FastGPT 是"Apache-2.0 + 附加条件"（禁多租户 SaaS、禁去 LOGO），Open WebUI 是 BSD-3 + 品牌条款（>50 用户不许改名改标）【一手】。
11. 星数不代表规模能力：Open WebUI 15.6 万星，但它是**前端 + 轻知识库**，不是索引引擎；把星数当技术选型依据是错的【推断】。
12. 可抄的只有零件，不是架构：**RAGFlow 的"模板化切分 + 切分结果可视化人工介入"**（Apache-2.0）与我们"条款校对"最贴，其余建议见各条【推断】。
13. A 线的总体答案是"**没有可抄的百万级架构**"：这不是坏消息——它说明我们的"单文件 SQLite + 条款一行 + 精确条款号 0.1 ms"在中文法规这个语料上不是落后，而是别人没做【推断】。

## 逐个点评

### RAGFlow
- 是什么：RAG 引擎（**已改写为 Go**，四个服务 `--admin/--ingestor/--syncer/--api`）/ 谁维护：InfiniFlow / 许可证：Apache-2.0 / 最后推送：2026-10-24（92,815★）
- **规模**：README **没有任何文档数或吞吐数字**，只写 "a data haystack of literally unlimited tokens"——这是营销句不是指标【一手】。实际架构靠外部件扛量：Elasticsearch（需 `vm.max_map_count=262144`）+ MySQL + MinIO + NATS + kvrocks；官方建议 **4 核 / 16 GB / 50 GB 盘** 起步【一手，README 部署节】。
- **表格 / 图 / 公式 / 上下标**：README 只有 "Deep document understanding" 一句，**无量化、未说明四类分别怎么处理**【一手】。反向证据：DeepDoc 把全部页面当高分辨率图驻留内存、中途不释放，1,600 页 PDF 在 62 GB 机器上 OOM（issue #11822）⇒ "能解析"与"能批量入库"是两件事【一手】。（⚠ **2026-10-25 复核更正**：OOM 与"驻留内存"成立；"中途不释放/无流式"与 GPU 那句出自 dosubot 机器人，维护者否认 GPU 说法，见结论 5 的更正。）
- **中文法规/国标**：无。【一手】
- **引用可回溯**：README 写 "traceable citations" + "visualization of text chunking to allow human intervention"，粒度是 **chunk**；**有没有页码/坐标字段：未取证**（未读源码）。【一手 README / 未取证】
- **对我们**：抄 **"模板化切分（Template-based chunking）+ 切分结果可视化给人改"** 这两点设计（Apache-2.0，抄代码需保留版权声明；只借鉴设计不涉许可）——它正好对上我们"按文档类型配切分规则 + 条款校对界面"。**不抄解析**（OOM 反证），**不抄 ES 那一套**（我们是单文件 SQLite，见 §六换底座已判死）。代价：切分模板要我们按国标/法规分别写，工作量在语料侧不在代码侧。

### Infinity（RAGFlow 的检索引擎）
- 是什么：向量 + 全文检索引擎，单二进制亦可 Python 内嵌 / 谁维护：InfiniFlow / 许可证：Apache-2.0 / 最后推送：2026-10-17（4,742★）
- **规模**：宣称"**百万级向量数据集 0.1 ms 查询、15K+ QPS**""**3,300 万文档全文检索 1 ms、12K+ QPS**"，口径是向量条数与文档数【一手，README】。**但这组数是厂商自跑 benchmark**（`infiniflow.org/docs/dev/benchmark`），**第三方复现：未取证**。
- **表格 / 图 / 公式 / 上下标**：不适用（它是索引层，不解析文档）。它融合 **dense + sparse + tensor + 全文 + 过滤**，重排器给了 **RRF / 加权和 / ColBERT** 三种【一手，README L46】——RRF 我们已经在用。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：不适用（不产引用，只吐行）。
- **对我们**：**不抄**。三条硬理由：①交付是 Electron 单机，Windows 上它只能跑 **WSL**（README 明写），等于给用户装半台 Linux；②CPU 必须 **AVX2**，老机器直接不启动；③"换向量底座"已在 §六判死。**唯一保留的可能**：如果将来 52 万条款 → 千万条款，sqlite-vec 606 ms 线性增长到 10 s 级不可接受时，再拿它当候选（届时要重估 WSL/AVX2 代价）。

### Dify
- 是什么：LLM 应用开发平台（工作流画布 / Agent / LLMOps）/ 谁维护：LangGenius / 许可证：**修改版 Apache-2.0**（禁多租户 SaaS、前端禁去 LOGO）/ 最后推送：2026-10-25（159,448★，全库最高活跃）
- **规模**：README **无任何规模数字**；最小系统要求 **2 核 / 4 GiB / Docker Compose v2.24+**【一手】⇒ 这是"给小团队自建"的配置量级，不是 10 万文档的设计目标【推断】。
- **表格 / 图 / 公式 / 上下标**：README 只有 "RAG Pipeline ... text extraction from PDFs, PPTs, and other common document formats"——**"能抽文字"级别，未提表格结构、公式、上下标**【一手】。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：**未取证**（README 无页码/块坐标描述）。
- **对我们**：**不抄产品形态**（它是应用平台，我们是法规库）。唯一可看的：它的 RAG Pipeline 抽象（抽取→切分→索引→召回的插件位）当**分层命名的参考**，不是抄代码。许可证附加条件不影响"读它、照它的分层思路写我们自己的代码"。

### FastGPT
- 是什么：知识库问答 / 工作流平台 / 谁维护：Labring（sealos 团队）/ 许可证：**Apache-2.0 + 附加条件**（多租户 SaaS 需商业授权、禁去 LOGO）/ 最后推送：2026-10-24（29,907★）
- **规模**：README **无数值**【一手】。本轮**只做关键词扫描，未逐节细读** ⇒ 入库吞吐、分片机制、集群方案**全部未取证**。
- **表格 / 图 / 公式 / 上下标**：未取证（README 命中"表格/图"相关词 9 处，但未读到具体处理方式）。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：未取证（命中"引用"1 处，未细读）。
- **对我们**：国内同类里唯一值得后续补一轮细读的（中文语料意识最强、国内部署量大）。**本轮结论：待核，别据此下判断。**

### MaxKB （1Panel）
- 是什么：企业级智能体平台 / 谁维护：飞致云（1Panel 团队）/ 许可证：**GPL-3.0** / 最后推送：2026-10-23（23,031★）
- **规模**：README 无数值【一手】；入库吞吐、分片未取证。
- **表格 / 图 / 公式 / 上下标**：未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：未取证。
- **对我们**：**GPL-3.0 ⇒ 一行代码都不要抄进我们的闭源分发**。这是我们这条线上许可证风险最高的一个（比 AGPL 更容易被忽略：它是 GPL 不是"开源随便用"）。只可读思路，不可复制代码。

### AnythingLLM
- 是什么：桌面/自托管 RAG 应用（工作区隔离、可插拔向量库）/ 谁维护：Mintplex Labs / 许可证：MIT / 最后推送：2026-10-24（67,523★）
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：命中"公式"2 处，未细读 ⇒ 未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：命中"引用"1 处，未细读 ⇒ 未取证。
- **对我们**：**不适用**于 10 万级（桌面单机 + 单进程嵌入，架构就是"个人知识库"）。MIT 许可证是全库最干净的之一，若将来要抄 UI 交互可优先看，但本轮没读到可抄的具体实现。

### Onyx（原 Danswer）
- 是什么：企业搜索/助手（连接器生态是它的强项）/ 谁维护：DanswerAI, Inc.（现 Onyx）/ 许可证：**MIT，但 `ee/` 目录是 Onyx Enterprise License**（混合许可）/ 最后推送：2026-10-24（32,955★）
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：未取证。
- **对我们**：**不适用**。它解决的是"公司内 100 个 SaaS 的搜索"，连接器生态对我们零价值（我们的语料是本地法规 PDF）。混合许可证意味着抄 `ee/` 会踩坑，抄之前必须按目录确认。

### Verba（Weaviate）
- 是什么：Weaviate 官方 RAG 演示应用 / 谁维护：Weaviate / 许可证：BSD-3-Clause / **仓库已归档（archived=true），最后推送 2026-06-08**（7,692★）
- **规模 / 表格 / 公式 / 引用 / 中文法规**：README 只剩 Weaviate Cloud 连接的环境变量说明（`WEAVIATE_URL_VERBA` / `WEAVIATE_API_KEY_VERBA`）⇒ 无任何技术内容可评【一手】。
- **对我们**：**已死项目，从候选里划掉**。任何"参考 Verba"的说法过期（这是本轮一个确定的结论，可以省掉别人再查一遍）。

### Quivr
- 是什么：个人/团队"第二大脑"式 RAG / 谁维护：**The Vibe Company**（原 StanGirard 个人项目）/ 许可证：MIT / 最后推送：2026-10-21（**39,602★，在 `The-Vibe-Company/quivr`**）
- **⚠ 事实更正**：`QuivrHQ/quivr` 这个地址 GitHub 已 404，迁仓到 `The-Vibe-Company/quivr`。任何指向旧地址的引用都会失效【一手，本轮查证】。
  - ⚠ **2026-10-25 独立复核再更正（原话保留，不删）**：迁仓属实，但**旧地址不是 404**——`gh api repos/QuivrHQ/quivr` 返回 200 且 `full_name` 已是 `The-Vibe-Company/quivr`，`https://github.com/QuivrHQ/quivr` 返回 **301 跳转**（GitHub 改名行为）。⇒ 旧链接**照常可用**，只是应更新为新地址。
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：命中"表格"4 处、"图"12 处，未细读 ⇒ 未取证。
- **中文法规/国标**：无。**注意**：README 出现"废止/失效"类词 1 次，但那是**通用版本管理语境**（"多版本"命中 30 次，多为 API version），**不是法规效力状态**——不要误读成它做了法规版本管理【一手，关键词扫描 + 未逐句核】。
- **引用可回溯**：命中"引用"2 处，未细读 ⇒ 未取证。
- **对我们**：**不适用**（产品定位是个人笔记脑图式 RAG，不是条款库）。但 30 次"version"提醒我们：**"多版本"在别人那里是软件 API 版本，在我们这里是法规版本——同名不同物，评审时容易被误导**。

### Khoj
- 是什么：个人 AI 助手（笔记/文档/网页检索）/ 谁维护：Khoj AI / 许可证：**AGPL-3.0** / 最后推送：2026-08-02（37,813★，三个月未推送）
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：未取证。
- **对我们**：**AGPL-3.0，单独标出**——内部自用可以，**绝不能做成对外提供的网络服务**；我们是单机 Electron 分发，AGPL 风险点在"分发"与"网络服务"两处，抄代码即触发。**不抄**。

### Kotaemon（Cinnamon）
- 是什么：文档问答 RAG UI（Gradio）/ 谁维护：Cinnamon（日本）/ 许可证：Apache-2.0 / 最后推送：2026-07-14（25,829★）
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：未取证。README 提供 `main-full` / `main-ollama`（内置 Ollama，本地私有） / `main-lite` 三种镜像，`linux/amd64` + `linux/arm64`【一手】。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：README 命中"引用/citation"5 处（**本线除 RAGFlow 外最多的一个**），但未细读 ⇒ **未取证，值得补一轮**。
- **对我们**：**待核**。它是"本地私有 RAG UI"最接近我们形态的开源实现（Gradio 而非 Electron，需重写）；citation 相关表述最多，是唯一值得再花时间读源码的候选。

### Open WebUI
- 是什么：LLM 前端（含轻量知识库/文档上传）/ 谁维护：Open WebUI Inc. / 许可证：**"Open WebUI License" = BSD-3-Clause + 品牌条款**（≤50 用户可改品牌，超过必须保留）/ 最后推送：2026-10-25（**156,667★**）
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：命中"公式"2 处，未细读 ⇒ 未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：未取证。
- **对我们**：**不适用**。它是聊天前端 + 轻检索，不是索引引擎；15.6 万星是"好用"不是"能装"。许可证第 4 条（品牌条款）足以否掉"抄它的 UI"这条路。

### R2R（SciPhi）
- 是什么：RAG API 服务（生产化 RAG 后端）/ 谁维护：SciPhi AI / 许可证：MIT / **最后推送 2025-11-07（近一年无提交）**
- **规模**：README 无数值【一手】；未取证。
- **表格 / 图 / 公式 / 上下标**：未取证。
- **中文法规/国标**：无。【一手】
- **引用可回溯**：命中"引用"1 处，未细读 ⇒ 未取证。
- **对我们**：**不适用（半死）**。8,043★ 的"活跃项目"印象与"11 个月无提交"冲突，任何依赖它的方案都有维护风险。

### Morphik
- 是什么：多模态文档 RAG（主打图/表/公式与大规模多模态检索）/ 谁维护：Morphik, Inc.（Delaware）/ 许可证：**Business Source License 1.1（不是开源）** / 最后推送：2026-10-21（3,719★，仓库 `morphik-org/morphik-core`）
- **规模**：README 未取到（`morphik-ai/morphik-core`、`morphik-ai/morphik` 均 404，**本轮未读到它的 README**）⇒ **未取证**。
- **表格 / 图 / 公式 / 上下标**：未取证（"多模态/ColPali 类"能力是**行业口碑，不是本轮读到的证据**，我不据此下结论）。
- **中文法规/国标**：无（未读到）。【未取证】
- **引用可回溯**：未取证。
- **对我们**：**许可证直接否掉**：BSL 1.1 的 Additional Use Grant 是"月毛收入 < US$2,000 才可生产使用"，Change Date 2029-06-18 后才转 Apache-2.0。**它的思路可以读，代码一行不能用**（我们的产品有商业分发）。这是本线第二个必须单独标出的许可证（第一个是 MaxKB 的 GPL-3.0）。

### WeKnora（腾讯）—— 只补规模面
- 已有完整评估见 `docs/research/weknora-assessment.md`（§五含"该抄什么/不该抄什么/许可证义务"），**本线不重复评**。许可证：**MIT 除第三方组件**，`LICENSE` 抬头为 `Copyright (C) 2026 Tencent`（比既有评估里写的 2025 晚一年，以仓库文件为准）。最后推送 2026-10-24（35,314★）。
- **规模（本轮要补的这一面）**：**README 里没有任何文档数、吞吐或基准数字**⇒"宣称规模"= 无宣称【一手】。架构上它把"扛量"完全外包给外部件：Postgres（ParadeDB）+ Redis，向量库可选 qdrant / milvus / weaviate / doris，图库 neo4j，对象存储 minio——**即"要上 10 万级必须补齐这一整套，Lite 模式（`DB_DRIVER=sqlite` + 内置 sqlite-vec + 去掉 `REDIS_ADDR`）只是单机小规模形态"**【一手，评估文档 + 仓库配置】。
- **对我们**：规模面结论 = **它也没有到过 10 万级**，只是"能接集群件"。这修正了一个可能的误读："腾讯开源 + 一堆向量库后端"不等于"验证过百万级"。

### LangChain / LlamaIndex / Haystack / txtai（框架，不是知识库）
- **共同点**：四个都是**零件库**，谁都不提供"条款级引用 + 效力状态"，用"规模"评判它们是错位的；它们的价值是"我们缺某个零件时去拿"。【一手】
- **LangChain**（MIT，148,399★，2026-10-24）/ **LlamaIndex**（MIT，52,647★，2026-10-23）/ **Haystack**（Apache-2.0，26,831★，2026-10-24）/ **txtai**（Apache-2.0，13,033★，2026-10-22）：README 全部**无规模数字**；Haystack README 的商业信息（Airbus/Lufthansa/LEGO 等客户）是"企业版卖得动"不是"能装多少"【一手】。
- **对我们**：**都不抄整体**（§六：手搓通用层已死，但也别引入一个通用框架当底座——我们已有成型链路）。
  - **Haystack 的"Pipeline 并发执行 + 组件可替换"** 是命名参考，Apache-2.0 干净。
  - **txtai** 是四个里唯一把 **SQLite 当一等公民**（内容存 SQLite、向量可换 faiss/hnswlib/pgvector）的，与我们"单文件 SQLite"同路数，Apache-2.0 ⇒ **将来若要补"向量+关键词混合打分"的现成实现，先读 txtai 而不是自己写**。
  - **LlamaIndex** 的节点解析器族（按句子窗口/按层级切）对我们的"条款切分"有参考价值，但**本轮未读到具体实现 ⇒ 未取证**。

## 对不上的地方（来源互相矛盾处，单列，不抹平）

| # | 谁在说 | 说 A | 说 B | 我的处理 |
|---|---|---|---|---|
| 1 | RAGFlow README vs 官方 issue | "literally unlimited tokens"、"traceable citations" | issue #11822：5 MB / 1,600 页 PDF 在 62 GB 内存上 OOM；无流式解析、无逐页释放 | **以 issue 为准**：宣传句不算指标。"能解析"≠"能批量入库" |
| 2 | RAGFlow README 的"规模" | 无任何数字 | 生产部署要 ES + MySQL + MinIO + NATS + kvrocks 五件套 | 不冲突但矛盾于"轻量"印象：**它其实很重**，只是没写规模 |
| 3 | RAGFlow 检索 | 主打"多路召回 + 融合重排" | issue #14412：元数据过滤在 Python 内存里做（`common/metadata_utils.py`），没下推 ES | ⚠ **2026-10-25 复核后改判**：该描述只对 **v0.25.0** 成立；**1.0（Go）已实现下推**（`internal/engine/elasticsearch/metadata.go::FilterDocIdsByMetaPushdown`，不可行时回退内存），issue 已 closed。⇒ 不再算"最先塌的地方"；未解的是 #11822 解析内存与 #9647 GraphRAG |
| 4 | RAGFlow GraphRAG | README 列为主打能力 | issue #7957 / #9647：36 小时、$200 未跑完；批量化 PR #15982 **已关闭、未合并**（2026-06-23） | 记为"**已知不可用**"，不当作能力 |
| 5 | Infinity | 0.1 ms / 15K QPS（百万级向量） | 同一份 README 承认是自家 benchmark 页 | **厂商自测，非独立复现**；引用时必须带这句 |
| 6 | Verba | 多篇评测/文章推荐它做 RAG 基线 | GitHub `archived=true`，最后推送 2026-06-08 | **以 archived 为准**：已死 |
| 7 | Quivr | 老文章都写 `QuivrHQ/quivr` | 该地址 404，实际在 `The-Vibe-Company/quivr` | ⚠ **2026-10-25 复核后改判**：迁仓属实，但旧地址是 **301 跳转**不是 404（`gh api repos/QuivrHQ/quivr` 返回 200）。⇒ 旧链接照常可用，只应更新地址 |
| 8 | Morphik | 常被归入"开源 RAG" | `LICENSE` = BSL 1.1，生产用途限营收 < $2,000/月 | **以 LICENSE 为准**：非开源 |
| 9 | Dify / FastGPT | 都被称作"开源" | `LICENSE` 是 Apache-2.0 **+ 附加条件**（禁多租户 SaaS、禁去 LOGO） | GitHub API 的 `license=NOASSERTION` 正是这个原因 |
| 10 | Open WebUI | "BSD-3"（多数二手资料） | `LICENSE` 是 "Open WebUI License" = BSD-3 + 第 4 条品牌条款 | **以 LICENSE 文件为准**；API 显示 NOASSERTION |
| 11 | 星数 vs 能力 | Open WebUI 156,667★ > RAGFlow 92,815★ | 前者是聊天前端 + 轻检索，后者是 RAG 引擎 | **星数不做技术选型依据** |
| 12 | R2R | 8,043★，常见于"生产级 RAG"清单 | 最后推送 2025-11-07 | 记为"半死"，需另行确认是否转移 |
| 13 | Quivr 的"多版本"命中 30 次 | 看上去像做了版本管理 | 逐词看是 API version / 通用版本语境 | **不得当成法规效力管理**（本轮关键词扫描的陷阱，记下来防复发） |
| 14 | WeKnora | "腾讯开源 + 支持 qdrant/milvus/weaviate/doris" 容易被读成"验证过百万级" | README 无任何规模数字 | **能接 ≠ 验证过**；规模面结论 = 未宣称 |

## 待核清单（我没读到的）

1. **全部 18 个平台的"10 万份 PDF 入库要多久"**：一个都没给数字，README 也都没有。要答只能读各自的 docs 站或自己跑（本轮都没做）。
2. **FastGPT / MaxKB / AnythingLLM / Onyx / Quivr / Kotaemon / R2R / Morphik 的 README 只做了关键词扫描，未逐节细读**——尤其 FastGPT（国内、中文语料意识最强）和 Kotaemon（citation 词频最高）两个值得再补一轮。
3. **Morphik 的 README 根本没读到**（两个候选仓库路径均 404，最终只确认了 `morphik-org/morphik-core` 存在 + 许可证）。它的表格/公式/多模态能力**一条证据都没有**。
4. **表格 / 公式 / 上下标的实际处理方式**：除 RAGFlow 的 DeepDoc（且是反证）外，**没有任何平台读到了具体做法**。全部未取证。
5. **引用粒度是否含页码/坐标**：RAGFlow 只有 README 措辞，**源码未读**；其余更没读。→ 这一条直接决定"我们能不能抄别人的点回原文"，值得单独补。
6. **Infinity 的 benchmark 硬件口径与数据集规模**（`infiniflow.org/docs/dev/benchmark` 未抓取）。
7. **各平台的分布式/分片机制**（RAGFlow 的 ingestor 如何分片、Onyx 的索引并行度）：未读源码，全部未取证。
8. **MaxKB / Khoj / Morphik 的许可证全文**只读到抬头（GPL-3.0 / AGPL-3.0 / BSL 1.1），未逐条读完附加条款。

## 反证检索记录（搜了什么词、搜出什么）

- 搜「**RAGFlow 大规模文档 性能 局限 被高估**」「**RAGFlow scalability limitations million documents benchmark criticism**」→ 没搜到独立第三方压测；**搜到的是仓库自己的 issue**，比任何评测都硬：DeepDoc OOM（#11822）、元数据过滤走内存（#14412）、GraphRAG 跑不完（#7957 / #9647）。**结论：RAGFlow 的"规模"问题不在向量层，在解析与元数据过滤。**
- 搜「**RAGFlow table extraction accuracy problems DeepDoc layout**」→ 连带出 #11822 的完整线程（62 GB 内存不够、无流式、GPU 加速要 v0.22.0 之后且官方无基准）。**表格识别精度：仍未拿到任何量化数字。**
- 搜「**RAGFlow 引用 页码 定位 跳回原文**」→ 只回到 README 级别的 "traceable citations" / "chunk 可视化"，**没有页码字段的证据**。
- 关键词矩阵扫描（17 份 README 全文，正则计数）→ **只有 Infinity 有数字规模表述**；`废止|失效|效力` 只在 Quivr 命中 1 次且是通用语境；`页码|page number|pagination` **全库 0 命中**——这条最值得记：**没有一家在 README 里提页码引用**，我们的"点回原文页"在宣传层面都是差异化。
- 元数据核查（GitHub Search API）推翻了三条**通行说法**：Verba 已归档、R2R 近一年停更、Quivr 已迁仓。
- 许可证核查（逐个抓 `LICENSE` 原文）推翻了三条**通行说法**：Morphik 不是开源（BSL）、Dify/FastGPT 是"Apache + 附加条件"、Open WebUI 不是纯 BSD-3。
- **没做的事**（如实记）：没有做"某某平台被高估"的独立中文评测检索（CSDN/知乎按任务书不能当一手，且本轮预算优先给了许可证与 issue）；没有跑任何一个平台；没有读任何平台源码。
