# I 线：社区与社交媒体实战信号

> 抓取日期：2026-10-25（所有 URL 当日可达）
> **口径**：只收"官方文档不会说的事"——真实语料上的失败模式、百万级实测、中文标准/法规 PDF 的实战、许可证踩坑。
> **档位说明（本线特有，务必按这个读）**：
> - **【一手·issue】** = 我直接读到 GitHub issue / 仓库文件原文（附编号 + 日期 + 提交号）。它证明的是**"用户这么写了"**，不是**"事实如此"**——issue 里的根因分析多半是用户或机器人猜的。
> - **【转述】** = 论坛帖、博客、公众号、聚合文、厂商案例。社交媒体一律此档，**绝不升级为一手**。
> - **本文件无【实测】**：我没有在本机复现任何一个平台的任何一条报告。
> - **比 A 线更严的一条**：本线所有 dosubot / Dosu 的答复**一律不采信**（A 线在 RAGFlow #11822 上已吃过一次亏：机器人说"无流式、要 GPU"，维护者当场否认）。凡我引用到机器人内容，都标注了"机器人"。
> - **Reddit 全线不可达**：`reddit.com/*.json` → **403 Blocked**；`r.jina.ai/old.reddit.com` → **403**；`api.pullpush.io` → 连续 3 次 **429**；`arctic-shift.photon-reddit.com` → **500**。仅第一批 pullpush 查询侥幸返回过 15 条标题（无正文），不足以当证据。**r/Rag、r/LocalLLaMA 的规模贴这轮没读到**，如实记在"待核"。
> - 知乎 → **CAPTCHA 拦截**；CSDN 目标篇 → **404**；V2EX 走 API 可读；掘金可读；linux.do 可读。

## 结论先行（≤15 行）

1. **有一条一手叙事直接打我们的"单文件 SQLite 到百万级"**：一个把 100 万份企业 PDF 灌进 RAG 的人，明确把 SQLite 换成 Postgres，理由是"百万文档 × 多 chunk × 向量库 × 标签互查"不是 SQLite 该干的活【转述，ure.us 2026-04】。这是本线对我们最有杀伤的一条，详见「对我们」第 2 条。
2. **表格丢数据不是"我们没做好"，是这条链路上的系统性断点**：RAGFlow 自己的 Go 解析器把跨页表只输出首页行——同一份文件 Go 192 个单元格 / Python 292 个，27 行 vs 51 行，缺的 24 行全是续页；这块代码在 2026-08 到 2026-10 之间被 6 个 PR 反复改仍回归【一手·issue #18347 + 提交记录】。
3. **"引用能点回原文页/坐标"在开源平台上会因换解析器、换版本而静默失效**：RAGFlow 中文 PDF 的 chunk 位置映射在 0.22.1→0.23.0 回归（#12309），Go 的 Docling 路径干脆丢 page positions、把页数报成文档数（#21215，open）。我们的差异化（点回原文页）在别人那里连"保持不坏"都做不到。
4. **中文 PDF 的老问题是字体映射乱码，不是识别率**：RAGFlow #6787 贴出的抽取结果是一串 "暥暦290暋棽椆棸…"；电网厂商博客给的数字是老旧文档乱码导致向量特征提取失败约 **3.5%**【一手·issue #6787 / 转述】。
5. **内存爆的形态和我们想的不一样：不是"跑不动大文件"，是"一次运行把整台机器和别人一起拖死"**：RAGFlow 一个大页 PDF 让 ingestor 3 小时死 **49 次（33 次 OOM + 16 次 panic）**，且连带杀掉同容器其它任务、导致付费 LLM 步骤重跑 ~16 次【一手·issue #20956】。
6. **MinerU 3.4.4 有"每份文档 RSS 只涨不落"的报告**（#5313，2026-07-22），我们是 3.4.5：**批量入库必须做进程级回收/断点续跑**，否则 10 万份单进程跑必死【一手·issue】。
7. **"真灌过十万"的人存在，但都是绕着走的**：论坛里唯一自报 10 万+ 的人说"10W+ 没啥问题"，紧接着说难点是"原生 DeepDoc 不如 MinerU/合合""还没有语义化分片"；另一个 3 万文件的人说自己 **3 万文件时向量检索 2–3 秒**、靠元数据标签先圈范围【转述，linux.do 2026-02-11】。
8. **"向量库换正规的就快了"是幻觉**：dify+milvus 在 3 万文件上仍是 2–3 秒；Weaviate 在 **120 万向量 / 24GB 内存**上内存缓慢爬满到 OOM（issue 从 2024-06 open 至今）【转述 / 一手·issue #5071】。我们 52.2 万条款 606 ms 在同量级里不算差。
9. **"分桶收窄候选集"在社区里是共识，不是我们的土办法**：自称做过千万级档案馆库的人给的建议是"必须分桶、做分级标签，树最底层桶 200–1000 条"——与我们实测"候选集收到 50 时前 20 = 99%"同向【转述，linux.do】。
10. **许可证这条我们自己的依赖就有坑**：MinerU 在 2026-03-20 至 04-17 六周内 **AGPL-3.0 → Apache-2.0 → AGPLv3 → Apache-2.0 → Apache+附加条款** 翻转四次；现行条款要求"向第三方提供在线服务须显著标注"且设了商业许可门槛。**"MinerU 是 Apache-2.0"这句话现在不准确**【一手·LICENSE.md + PyPI 元数据 + 提交记录】。
11. **"Apache/BSD"这个词已经不能当许可依据**：Weaviate 是 BSD-3 + `wl/` 目录全部权利保留（API 显示 NOASSERTION）；Elasticsearch 是三许可 AGPLv3-only / SSPLv1 / ELv2。按 spdx 字段选型会踩雷【一手·LICENSE 原文】。
12. **国标/条款级这条赛道，中国已经有人做成商品在卖**：中汽（CATARC）"标准法规 AI 智能拆解工具"（国标+行标+UN/ECE，拆条款/树状目录/表格公式图片分抽/三栏联动校对/导出 Markdown+Excel），TextIn xParse 有"国家标准知识库解析"试用页。**我们的形态不是孤例，但公开的技术细节他们一个都没给**【转述】。
13. **社区里跟我最像的公开实现是 jlcbk/standards-intelligence-skills（MIT，0 star）**：它把"疑似字体映射/乱码字符数量"当一等质量指标，条款索引默认只存 `provision_id/clause_number/locator/line_number` 不存正文，并明确"跳过 0 与前导 0 编号""同文件同条号只留首次"来压目录/表格造成的假阳性【一手·仓库文件】。
14. **上下标有可执行的判据，不必只依赖模型**：阿里云那篇给的是"字号比 ≈0.75、基线偏移 ≈0.40em、拆开的下标最多向外跳 8 段找基字、两边都能当基字取左"，并给出真实错例（10⁻³ 被读成"30"、"第-3 20"）【转述】。
15. **反过来说，社区也在质疑"向量"这条路本身**：论坛里有人主张"EMBEDDING 不需要，先把所有文件转 Markdown、靠文件系统分类+摘要"，也有人反驳"检索精度上不去是行业普遍问题"。这条异议必须留着【转述】。

## 逐个点评

按主题分，不按项目分（A 线已按项目评过一遍，本线只补"用户实测"这一面）。

### 2.1 解析错：乱码、错位、表格丢

**RAGFlow #6787「Corrupt text in chunks」（2025-04-03，closed 2026-09-08）**【一手·issue】
- 用户 stevenguan08 贴的对照：期望是干净中文，实际抽出来是 `第七章美治时期菲华法律和经济地位284 / 第二节美国排华法案引入菲律宾群岛…暥暦290暋棽椆棸…`。
- 复现步骤齐全（上传 → 解析 → 看 chunk），自述"几乎每个 chunk 都有，与内容类型无关"。
- 这是**中文 PDF 字体/编码映射错**的典型脸：不是 OCR 识别错字，是字形到 Unicode 的映射丢了。我们的语料（老国标、扫描存档、地方标准）比这个只多不少。
- 根因未定论：这一串乱码在 CID/ToUnicode 缺失时会整段出现，但**issue 里没有任何人能给出根因**，机器人给的是"两条相似 issue"。

**RAGFlow #12309「Incorrect Chunk Thumbnails and Positioning for Chinese PDFs — Regression from 0.22.1」（2025-12-30，closed 2026-07-08）**【一手·issue】
- 组合：ragflow 0.23.0 + mineru 2.6.6，两条路径（vllm-http-client / pipeline）都中招。
- 症状：chunk 缩略图不对 + **chunk 在原文 PDF 里的位置映射不准**；用户明确说"0.22.1 上基本是对的"。
- 复现步骤：上传中文 PDF → 逐 chunk 看缩略图与位置。这是一条**可直接照抄的验收用例**，我们该有一条同样的回归测试。
- 机器人的归因（非 ASCII 文件名/取坐标逻辑改动）**不算结论**。

**RAGFlow #18347「Go PDF parser: cross-page tables drop continuation-page rows」（2026-08-17，2026-09-07 closed）**【一手·issue + 提交记录】
- 这是一条少见的高质量内部跟踪 issue（作者 xugangqiang），给了文件行号：`table_merge.go:103` 合并跨页表后**没有重算 `TableItem.Grid`**，`table_construct.go:48-49` 读的还是合并前的旧 Grid ⇒ 只输出锚点（首页）的行。
- **量化影响**：`中加纯债` 这份文件，Go 192 cells vs Python 292 cells（51% 命中），Go 27 行 vs Python 51 行，缺的约 24 行是续页。
- 修了多久：`#18362`（同日晚）→ `#18378`（次日）→ `#18416`（08-18）→ `#18516`（08-19）；然后 08-25 `#18688` 修"过度合并"、`#18740` 再把被误拒的合回来、08-27 `#18789` 加"锚点必须在页底"的门槛。**同一个月里这块逻辑被改了 6 次**，2026-10-16 还在提交"Remove RowsToHTML; render PDF tables via canonical RenderTableHTML (#21083)"。
- 结论句：**跨页表是这块的开颅手术，不是配置问题**。任何声称"支持跨页表"的产品，都要问它要比对"Go 192 vs Py 292"这种逐 cell 的差。

**RAGFlow #16008「Tables missing after parsing laws rule DOCX document」（2026-06-15，closed 2026-10-09）**【一手·issue】
- 一句话：**解析"法律法规"DOCX 之后，原来文件里的表格全没了**（v0.26.0）。
- 价值在于"法规"这个词直接出现在标题里——别人也在这类文件上踩，但没有解法记录。

**RAGFlow #16060「MinerU failed to parse the table / DeepDoc layout 识别失败」（2026-06-16，open）**【一手·issue】
- 复现四步：建库选 MinerU → 传 PDF → 解析 → 表格变纯文本并报 `FAILED TO PARSE TABLE`；切回 DeepDoc 后"版面结果很乱、换行过多"。
- **两条路都不行**是这个 issue 的重点：不是选错解析器，是两个解析器各有一半坏。

**FastGPT #8032「单元格含 `|` 时 Markdown 表格错列」（2026-10-19，open）**【一手·issue】
- 给了代码级复现：`htmlTable2Md('<table>…<td>A|B</td><td>$|x|$</td>…')` → 渲染成 4 列，后面整体错位；作者指出论文/试卷表格里带绝对值、条件概率的极常见，入库分块和对话展示都会错。
- 这条对我们直接有用：**"表格转 Markdown"不是无损方案**，转义没做就等于静默改数据。我们的表格存 Markdown 必须做 `|` 转义 + 列数守恒校验。

**Dify #32202「PDF 解析失败率特别高」（2026-02-10，v1.12.1）**【一手·issue】
- 用户用 **MMLongBench** 做评测时"pdf 解析失败率特别高，重传也没用"。注意：这是**自报**，没给具体失败率数字。

### 2.2 引用对不上：换解析器就丢坐标

**RAGFlow #21215「Docling PDF parsing drops page positions and reports page_count as the number of documents」（2026-10-20，open）**【一手·issue】
- 源码级：`internal/parser/parser/pdf_parser_docling.go:24-28` 的 `doclingDocument` 结构体只声明了 `md_content/text_content/json_content`，**没接 Docling 返回的 `prov`（页码+bbox）**。
- 后果：走 Docling 路径的文档，**页位置全丢、页数报成文档数**。同批还有 #21216（OpenDataLoader 路径同类问题）、#17450（Docling 忽略 page range，每个任务都整本重转）。
- **这一条最值得记**：它的失败方式不是"报错"，是"看起来成功了，但引用 quietly 变错"。我们的架构里，只要解析器可以自己决定"给不给 bbox"，就会重演这件事。

**RAGFlow #12309**（见上）：中文 PDF 位置映射回归，是最接近我们语料的证据。

### 2.3 内存爆、卡死、升级破坏

**RAGFlow #20956「大页 PDF 让 Go ingestor panic / 被 OOM kill，连带杀掉所有在飞任务」（2026-10-14，open）**【一手·issue】
- 数字很硬：两份公开 PDF 让 ingestor **约 3 小时内死 49 次（33 次 OOM kill exit 137 + 16 次 panic）**。
- 机理（作者给了文件行号）：216 DPI 下 8504×4252 pt 的海报页 = 25512×12756 px × 4B ≈ **1.30 GB**，超过代码里的 `(*[1<<30]byte)` 数组上限 ⇒ 切片越界 panic；crop 协程没有 `recover()`；页缓存只按**条数**限 64 页，而一页 5102×3968 pt 的 RGBA ≈ **730 MB**，64 页 ≈ **10 GB**。
- 二次伤害：崩溃后 NATS 重投，**其它任务里一个付费 LLM 编译步骤被重跑约 16 次**。
- 对我们：这是"单机批处理"的标准事故链（大页 → 缓存按条数不看字节 → 协程 panic → 整进程死 → 任务重投 → 费用重算）。我们的条款入库也该有"按字节的内存预算"，不是按条数。

**RAGFlow #12917（2026-01-30，open）**：分块阶段 OOM 打死 task_executor（0.23.1 + WSL2 docker）【一手·issue】。

**RAGFlow #8490（2025-06-25，open，18 评论）**：16C128G，**同时解析 4 个文件页面就卡死**；回答全是 dosubot（机器人），说"提高 MEM_LIMIT""限制并发"。**机器人内容不采信**，但提问者的 16C128G / 4 文件这个事实本身可用【一手·issue，结论未取证】。

**MinerU #5313「API RSS grows unbounded across documents until OOM」（2026-07-22，closed）**【一手·issue】
- MinerU **3.4.4** + FastAPI + Docker：**每解析一份文档，内存只涨不落**，最终 OOM 被杀；用户说排查几小时后定位到"堆里没释放"。
- 我们用的是 **3.4.5**（见 `20-parsing.md` §八），版本贴得极近 ⇒ 这条对我们不是"看别人热闹"。

**MinerU 其它同类**（均为【一手·issue】标题级，未逐条读正文）：#4243「minerU-api 本地化部署调用几次后总是 out of memory」（2025-12-24，10 评论）、#5185「3.4.0 在 910b 上频繁 OOM」、#5488「长文档解析崩溃」、#5013「3.1.15 hybrid-auto 疑似内存泄漏」。

**Qdrant #4378「OOM when trying to ingest large datasets due to caching」（2024-06-03，open，13 评论）**【一手·issue】
- 开着量化快速灌数据时，**全精度向量进了缓存**，内存远超按量化参数估算的值。作者描述的循环很经典：**OOM → 慢重启 → 手工再触发索引 → 缓存再涨满 → 再 OOM → "Slower Restart + Data Loss"**。
- 注意方向：**量化的宣传是"更快更省内存"，实测在这一步反而更费**。

**Weaviate #5071「Weaviate memory usage increasing gradually over the time」（2024-06-04，open，8 评论）**【一手·issue】
- 复现步骤完整：多租户开启、24 GB 机器、`GOMEMLIMIT=20GB`、`GOGC=60`、**共 120 万向量**（其中一个 class 100 万且 `vectorCacheMaxObjects=10000`），跑读写混合负载，内存缓慢涨到 100% 触发 OOM。
- 到抓取日仍 open，维护者在要 schema 和导入脚本。**"billions of vectors in milliseconds"（它 README 原话）与"120 万就爬满 24 GB"并存，这就是宣传与实测的落差。**

**Milvus**：#40540「streaming node 吃内存易 OOM」（closed 2025-03-11）、#44172「Channel checkpoint lag + etcd 内存 OOM（v2.6.1）」（closed 2025-09-02，19 评论）、#52791（open，2026-08-24）「QueryNode 恢复期 segment-load 预留抖动，而物理 RSS 仍然很低」【一手·issue，标题+状态级】。

**升级破坏数据/功能（这一组单独列，因为它最像"官方文档不会说的事"）**
- RAGFlow #18756（2026-08-25）：v0.26.4→v0.27.0 **原地升级**后，`tenant_llm_id/tenant_embd_id` 等列被建成 **INTEGER**，而代码存 32 位 hex ⇒ 设置默认模型、改数据集全 500【一手·issue】。
- RAGFlow #18755（同期）：`tenant_model.model_type` 升级后建成 **varchar**，代码却用**位运算整数**查 ⇒ 同一批升级事故【一手·issue】。
- RAGFlow #15742（2026-06-08，8 评论）：**v23.1 → v25.6 表格行被合并成一行**——用户贴了对比截图；机器人归因到 PR #12719 的"表格方向自动检测"，**属机器人推测**。同向的还有 #12978【一手·issue】。
- RAGFlow #15859（open）：升到 0.25.6 后**解析明显变慢**；#19103：升 v0.27.1 后 UI 默认模型坏掉【一手·issue】。
- Dify #38518（2026-07-07）：**索引还在跑的时候删知识库** ⇒ 留下孤儿 `segments`/`child_chunks`/pgvector 表；用户明确说场景是"tens of thousands of documents"【一手·issue】。
- MaxKB #7039（2026-09-14）：向量模型 `Dimensions` 参数**必填且无"不发送"选项** ⇒ 自建 vLLM + Qwen3-Embedding 全部向量化 400 失败，只能改库或改模型侧配置【一手·issue】。

### 2.4 到底有没有人真把几十万/几百万灌进去过

**结论：有，但每一个自报者都在"绕"——换库、分桶、云服务、先把 PDF 全转 Markdown。没有一个人拿出可复现的"开箱即用百万级"记录。**

**① linux.do《RAGFlow 能扛住 10万+文件的本地知识库吗？》（2026-01-05 起，49 楼 / 2.0k 浏览 / 200 赞）**【转述，论坛，全部为自报】
这是本轮信息密度最高的一处，逐条摘（保留用户原话要点）：
- 楼主 Hydra58 的需求：**10 万+ 文件**、本地部署、10 分钟出 1.5 万字专业报告。
- **user1794（2026-02-11）**：「2025 年一直在搞 ragflow 研究。**10W+ 的文档没啥问题**，我们是买了 10W+ 的专业知识导入库里」——同一段话紧接难点：「原生的 deepDoc 没有 minerU 和合合」「分片更加了，**都还没有语义化分片**」。⇒ **"能装进去"与"切得对"是两件事，他明说了。**
- **楼主本人（2026-02-11）**：「pdf 的数据真的是非常痛苦，**自己的物理服务器 8 核 16G 完全带不动，解析着解析着就卡死了**」。
- **Dao_er**：约 **3 万文件 / 100 万实体**；"第一次用 weaviate 存的向量给干崩了，后面换成 milvus"；**3 万文件日常占 7 GB，写入时到 12 GB**；**向量检索 2–3 秒**；"目前主要通过文档的元数据标签先圈选范围再进行检索"；"**向量化的时候重建了很多次…有时候量化到一半直接卡住了，一定要分步上传**"。
- **另一楼**：「之前 dify 上搞过上百 G 的知识库，**内存给干崩好几次**，最后换到 qdrant」；「**文档数量上去检索准确度就会下来**…10W+ 只放在一个库里效果肯定不好，检索噪声太多」（建议分主题建库）。
- **另一楼**：「线上用过 zilliz 的 serverless 跑过 **1 亿+ chunk（至少有十万+ 文件）**」，代价是"按请求数收费，请求多了容易掏空钱包"。
- **AlexChu1996（自称做过某地档案馆千万级知识库）**：① "单向量 embedding 的检索能力存在**容量上限**…文档特别多的时候高维空间里的向量会挤在一起，不相关的向量距离也变小，很容易混进 TOP-K"；② "开源那几种按长度切、按字符切、滑窗切"不够，应"按文档树形结构切"；③ "**必须分桶，给每个桶打标签，做一个分级标签体系，树的最底层桶里的数据不要特别多，比如 200–1000 这个量级**"；④ embedding/reranker "一定要微调，微调不微调差距至少 20%"。
- **seanzhao**：「ragflow 和 dify 等等，在我看来**都是用来跑 demo、用来进行业务验证的**…企业级建议还是通过专业流程编排组件配合代码进行定制开发…遇到问题个人很难处理」。
- **void.shum（2026-02-11，被赞 9）**：「优先成本：直接部署 RAGFLOW…**成本最低，但是效果也是最差的**，你可以把它当作基线」；「效果优先：目前最前沿的是 Agent Search…第一步是把所有文件转换成 MARKDOWN…其次文件系统设计（分类 + 每份文档一个 SUMMARY）…**至于 EMBEDDING，不需要**」（引 Anthropic 博文）。⇒ **这是一条对我们"六通道里最贵的那条（向量）"的直接质疑，必须留着。**

**② ure.us《A Million PDFs Won't Organize Themselves》（2026-04）**【转述，个人博客，匿名】
- 语料：**100 万份**企业 PDF（合同、工程报告、合规申报、维保记录、保险凭证），未抽样未清洗。
- **解析**：Docling 跑在 **8×A100** 上，**连续 72 小时**——"只为了拿到干净文本"，而且仍然"满是 artifact、字符识别错、表格结构糊成字汤、页眉粘进每一节第一句"。
- **存储**：原本用 **SQLite3 存元数据索引**（doc id / 路径 / 解析时间 / chunk 偏移），**百万文档 × 多 chunk × 向量库 × 分类标签互查"不是 SQLite 该干的事"**，迁到 PostgreSQL。
- **成本**：在 1M 规模上"换个向量维度重来一次"= **10 小时算力 + $200**；1M 文档做 contextual embedding 要租 **B200 跑 24 小时**（另加前面 3 天的 A100）。
- **最刺的一句**：「按 token 数切出来的 chunk，向量会聚成毫无意义的团…问题不在 embedder，在于我在要求 embedder 从没有结构的文本里造出结构」。

**③ 大厂真实体量（作为反证，不是可借鉴路径）**【转述/厂商】
- 腾讯 ima：知识库**千万级**、ES 侧**接近千亿级**，一套 ES 同时扛全文+向量+混合，BBQ 量化，`bbq_hnsw` / `bbq_disk` 两档（2026-09-20 腾讯云社区，演讲整理）。
- Qdrant 案例：&AI（专利诉讼检索）**10 亿+ 向量、2500 亿 token**、sub-second；解析用 **Reducto**（商业 API），量化最后选 scalar 不用 binary（binary 召回退化太狠，要取几万候选才够）。
⇒ 共同点：**都不是"装个开源知识库"能到达的**，都是"解析外包/自建 + 专用向量库 + 分片 + 有钱"。

### 2.5 中文社区对国标/标准/法规 PDF 的实战

- **MinerU 在中文社区被当成"对付标准/扫描件比 DeepDoc 好"的默认选择**：linux.do user1794 的原话是"原生的 deepDoc 没有 minerU 和合合"（合合 = TextIn）。这解释了为什么 RAGFlow 社区那么多人把 MinerU 挂上去，也解释了 #16114/#16060 那批"接 MinerU 以后 `FAILED TO PARSE TABLE`"的 issue 潮。【转述 + 一手·issue】
- **Dify #39126（2026-07-16）**：1 GB 扫描件、数千页、含跨页表；用户报告两个后果：**MinerU 解析服务容易 OOM**（他称 MinerU 单任务上限 **200MB / 600 页**——**未在官方文档核到，列入待核**）；**跨页段落与表格被切开，检索内容不完整**。他要的是"官方推荐的标准做法"，到抓取日没有官方答复（只有机器人）【一手·issue】。
- **TextIn xParse（合合）的国标解析产品页 + 腾讯云社区文章（2026-08-05）**【转述，商业】给出的判断比技术细节更有价值：「**这类长文档最常见的问题不是 OCR 识别率，而是"怎么切、怎么存、怎么检索"**」；列的五类痛点是：结构丢失、粒度失衡、页眉页脚噪声、表格图片失联、难以溯源；主张"文档解析 + 确定性后处理"（先把结构层做实，再叠模型），输出字段用 `outline_level / page_id / position / image_url`，并明确"页眉页脚过滤、跨页内容关联、原文坐标溯源"。GitHub 样例：`intsig-textin/xparse-sample-projects`。
  ⇒ **这段几乎是把我们 `00-brief §三` 的链路用商业语言重述了一遍**，是个正面的旁证。
- **中汽（CATARC）「标准法规 AI 智能拆解工具」（2025-06-25 公众号）**【转述，商业】：支持国标/行标/UN-ECE/企业文件、可编辑 PDF **与扫描件**；拆成条款级知识单元 + 树状目录；**表格/公式/插图分别独立提取**；"三栏联动校验（左目录树、中原文预览、右结构化结果），点原文段落自动定位对应解析结果"；导出 Markdown / Excel。⇒ **"条款拆解 + 人工三栏校对"是这一行的标准交付形态**，我们的"条款校对界面"不是过度设计。
- **jlcbk/standards-intelligence-skills（GitHub，MIT，2026-05-28，0 star）**【一手·仓库文件】：目前公开的、跟我们思路最接近的实现。要点：
  - 起步方式是 `pdftotext -layout`（不先上模型）；
  - `inspect-corpus` 只出**文件级统计**：行数、字符数、疑似条款编号数量、**"疑似字体映射/乱码字符数量"**，并给 `usable / needs_review / poor` 三档 ⇒ **把乱码当可量化的一等质量指标**；
  - `index-corpus` 默认**不存正文**，只存 `provision_id / source_file / clause_number / locator / line_number / source_quality / text_included=false`；
  - 明确为压假阳性做的规则：跳过 `0` 与前导 `0` 编号；同文件顶层编号只留首次；同文件同条号只留首次；保留 `4.1 / 4.1.1` 层级编号。
  ⇒ 可直接对照我们的条款号抽取：**我们有没有"同文件同条号只留首次"这条**（目录页会重复出现条号）。
- **电网向量库实战（KingbaseES 厂商博客，2026-06-24）**【转述，厂商】：2000 万条历史文档（说明书、故障工单、检修规程），清洗后 1800 万有效；**"部分老旧文档存在乱码，导致向量特征提取失败，占比约 3.5%"**，做法是"建规则过滤、把低质量数据标记归档"。⇒ **3.5% 这个量级值得我们对标**：如果我们的库里有 3% 条款是乱码，百万条就是 3 万条不可检索的假条目。
- **上下标的可执行判据（阿里云开发者社区 2026-10-20，作者团队自述）**【转述】：
  - 真实错例：`初始学习率设置为3×10` / `对于BAS数据集…在第-3 20和第60次迭代…`——**10⁻³ 的 −3 是 9pt、基字 3×10 是 12pt、上移 4.80pt(0.40em)，被排进了下一句**，模型读成"30"；
  - 判据：同行内比较相邻片段，**字号比 ≈0.75、基线偏移 ≈0.40em**，再加上中心偏移与间距条件；
  - 补充规则：拆成几段的下标（如 max 拆成 m/a/x）**最多向外跳 8 段**找基字；两边都能当基字时**取左**（Word 导出的 PDF 里下标离右边的字更近，按距离会错）；标点/列表符号不能带上下标时取右；**矛盾、小字套小字、旋转/竖排不处理**；
  - 正文里的数学统一转 LaTeX。
  ⇒ 这套规则**不需要模型**，可以当我们的"上下标校验器"，用来验证 MinerU 的 LaTeX 输出。

### 2.6 厂商宣传 vs 用户实测（对照清单）

| # | 厂商/README 宣称（出处） | 用户实测（出处） | 差距性质 |
|---|---|---|---|
| 1 | RAGFlow：「Finds "needle in a data haystack" of **literally unlimited tokens**」（README，2026-10-25 抓到） | 5 MB / 1,600 页在 **62 GB** 机器上 OOM（#11822）；大页 PDF 3 小时死 **49 次**（#20956）；分块阶段 OOM（#12917） | 宣传句不是指标；**限制在解析内存，不在检索** |
| 2 | RAGFlow：「traceable citations」 | 中文 PDF 的 chunk **位置映射**从 0.22.1 到 0.23.0 回归（#12309）；Docling 路径**直接丢 page positions**、页数报成文档数（#21215，open） | **可回溯是"默认坏、要修"的状态** |
| 3 | RAGFlow：DeepDoc 表格结构识别（"Deep document understanding"） | 跨页表只输出首页行，Go 192 cells vs Py 292（#18347）；法规 DOCX 表格全丢（#16008）；MinerU 路径 `FAILED TO PARSE TABLE`（#16060/#16114） | 单页表能出，**跨页表是硬缺口** |
| 4 | Weaviate：perform complex semantic searches over **billions of vectors in milliseconds**（README） | **120 万向量 / 24 GB 内存**，GOMEMLIMIT 20GB + GOGC 60 仍爬满到 OOM，issue 2024-06 至今 open（#5071） | 差 3 个数量级的量级仍在爬内存 |
| 5 | Qdrant：标量量化「2x faster, 4x less memory」（官方 benchmark 标题） | 开量化快速灌数据时**全精度向量进缓存**，内存超预期 ⇒ OOM→重启→再灌→再 OOM，且**重启后有数据丢失**（#4378，open） | 量化的收益与"灌数据"这一步无关 |
| 6 | Milvus：fully-distributed / K8s-native、"hundreds to millions of tenants"（README） | streaming node 吃内存易 OOM（#40540）；checkpoint lag + **etcd 内存 OOM**（#44172）；QueryNode 预留抖动（#52791） | 分布式件自己就是 OOM 源 |
| 7 | Dify：开箱即用的知识库/RAG Pipeline | 1 GB 扫描件直接 OOM（#39126）；索引中删除知识库留**孤儿 segments/child_chunks/pgvector 表**（#38518，场景自述"tens of thousands of documents"） | 缺"大文件"与"中断清理"两条工程边界 |
| 8 | MinerU：「国家标准知识库解析」试用页 / 社区默认推荐 | **3.4.4 每份文档 RSS 只涨不落直到 OOM**（#5313）；#4243「调几次就 OOM」；#5488「长文档解析崩溃」；Dify 用户称单任务上限 **200MB/600 页**（待核） | 单份能跑，**批量必漏** |
| 9 | FastGPT：支持表格/文档解析 | 单元格含 `|`（如 `$|x|$`、`P(A|B)`）**一律错列**，`htmlTable2Md` 不转义（#8032，open） | 一行代码的确定性 bug，静默改数据 |
| 10 | Onyx：企业搜索（连接器生态） | File connector **每次索引都全量重嵌**，~5,500 文档 CPU 跑**数小时**（#16461，自述读 `main` 源码后定位到 `doc_updated_at` 被写成 `now()` 击穿两道 skip 门） | "增量索引"缺失，规模第一道闸就漏 |
| 11 | 行业口径：「企业级知识库平台」 | 论坛共识："ragflow 和 dify…**在我看来都是用来跑 demo、用来进行业务验证的**"（linux.do seanzhao）；"原生 DeepDoc 没有 minerU 和合合…还没有语义化分片"（同帖 user1794） | 平台定位与采购预期错位 |

### 2.7 许可证陷阱（社区踩坑 + 我们自己的依赖）

**① MinerU —— 本轮最该记住的一条：许可证会变，而且变得很快**【一手·LICENSE.md + 提交记录 + PyPI】
- 提交记录（`gh api repos/opendatalab/MinerU/commits?path=LICENSE.md`）：
  `2026-03-20` AGPL-3.0 → Apache-2.0；`2026-03-28` Apache-2.0 → AGPLv3；`2026-04-14` AGPLv3 → Apache-2.0；`2026-04-17` 两次提交加"附加条款 + 商业使用与署名义务"。**六周内四次改口。**
- 现行 `LICENSE.md` 原文要点：Apache-2.0 **+ 附加条款**；商业用途免许可，但若"合并口径 **MAU > 1 亿** 或 **月收入 > 2000 万美元**"须另购商业许可；**"如基于 MinerU 向第三方提供在线服务，必须在产品或公开文档显著位置标明使用了 MinerU"**；违反即**自动终止**，无须通知。
- PyPI 元数据：`mineru 4.0.12` / `3.4.5` 的 `license_expression` = **`LicenseRef-MinerU-Open-Source-License`**（非标准 SPDX）；`mineru 2.1.0` 还是 `AGPL-3.0`；`magic-pdf 1.3.12` 仍是 `AGPL-3.0`。GitHub API 对 MinerU 返回 `license=NOASSERTION`。
- **对我们**：单机离线分发给终端用户，不构成"向第三方提供在线服务"，署名义务大概率不触发；商业许可门槛离我们极远。**但**：① 不能再写"MinerU 是 Apache-2.0"；② 必须**锁版本 + 把当版 LICENSE.md 原文随包**（许可变了要能证明我们用的是哪一版）；③ `magic-pdf` 那个包还是 AGPL，别混用。
- ⚠ 这条**同时更正**了 `20-parsing.md` §八里"我们代码走的是 `mineru` 包（非 magic-pdf/AGPL）"这句话的隐含结论：确实不是 AGPL，但**也不是纯 Apache**。

**② 其它许可证原文核对（都是 A 线没展开的）**【一手·LICENSE 原文，2026-10-25】
- **Weaviate**：仓库 `LICENSE` 写的是 BSD-3-Clause **+** `wl/` 目录及其子目录"Copyright Weaviate BV 2026-present, **all rights reserved**，仅企业许可可得"。GitHub API 显示 `NOASSERTION`。⇒ **抄 Weaviate 必须按目录看**，`wl/` 一行都不能碰。
- **Elasticsearch**：`LICENSE.txt` 原文是被 **(i) AGPLv3-only / SSPLv1 / Elastic License 2.0 三重许可**，(ii) Apache-2.0 兼容，(iii) 仅 ELv2，逐文件看头部；**仓库默认是三重许可**。⇒ "ES 是 Apache/开源"这句话是错的；而且它给出的选项里**包含 AGPL**。
- **MinIO**：`AGPL-3.0`（RAGFlow 全家桶的依赖之一）。RAGFlow 自身 Apache-2.0、Infinity Apache-2.0。
- 其余本轮核过的：Qdrant / Milvus / Infinity / Chroma / sqlite-vec = **Apache-2.0**；Docling = **MIT**；Ollama = **MIT**；MinIO = **AGPL-3.0**；Morphik = BSL 1.1、MaxKB = GPL-3.0、Khoj = AGPL-3.0（A 线已列，本轮只复核了性质未变）。
- **AGPL 的"理论风险"在社区有实例**（HN 头条级）：BambuStudio 被指自 2021 起违反 PrusaSlicer 的 AGPL（2026-05-23，407 分 / 165 评论）；Square 的服务条款曾**禁止在其网店里使用 AGPL 软件**（2019，232 分）；Octotree 的 Firefox 扩展被指含 AGPL 代码（2020，332 分 / 249 评论）【转述，HN 标题+分数】。⇒ **AGPL 的代价不是"要开源"，是"整条分发链被拖进来"。**

### 2.8 值得长期追的博客/作者

只列我**实际读到正文**的，并写清理由和它的局限。

| 谁 | 链接 | 为什么值得追 | 局限 |
|---|---|---|---|
| linux.do 用户 **AlexChu1996**（帖内 id `alexchu1996`） | https://linux.do/t/topic/1407408 | 唯一一个把"向量容量上限 → 必须分桶 → 底层桶 200–1000 条 → embedding 要微调"讲成一条链的人，且给了 3 篇论文/博客出处 | 只有论坛帖，**没有任何可核数字**；"千万级档案馆"是自报 |
| **ure.us** | https://ure.us/articles/a-million-pdfs-wont-organize-themselves/ | 少见地把"百万 PDF 的工程账"写成账单：8×A100/72h、$200 一次维度实验、SQLite→Postgres 的决策理由 | 匿名作者，无仓库无数据，"early results say yes" 但**拒绝公布数字** |
| **Shaped 博客**（The Vector Bottleneck 系列） | https://www.shaped.ai/blog/the-vector-bottleneck-limitations-of-embedding-based-retrieval | 被上面那位当理论依据引用的原始论述；做 relevance DB 的公司在卖自己的观点，但论证可读 | **我只读到标题与转引，未读正文** |
| **jlcbk/standards-intelligence-skills** | https://github.com/jlcbk/standards-intelligence-skills | 与我们同题（标准/法规条款级索引 + 溯源 + 版本安全），MIT，代码/文档都能读，`source_quality` 与"乱码计数"设计可直接对照 | 0 star、单人、更新停在 2026-05-28；**没有任何精度/规模数据** |
| **腾讯云开发者社区（ima 千亿级 ES 实践）** | https://cloud.tencent.com.cn/developer/article/2747411 | 大厂唯一公开讲"一套 ES 同时扛 BM25+向量+混合、千万级知识库、千亿级索引、BBQ 两档"的材料，能看清"真上规模长什么样" | 厂商软文，**无一条失败率/延迟的原始数据**，结论必然是"买我们" |
| **HN 用户 `etiennedi`**（Weaviate 工程师） | https://news.ycombinator.com/item?id=37402956 | 讲 hybrid 检索性能时说"it's complicated…one does not always scale better than the other"，是少见的**不吹自家**的厂商工程师发言 | 立场仍是 Weaviate；只此一条 |
| **Anthropic Contextual Retrieval** | （本线只见到 linux.do 与 ure.us 的转引） | "先给 chunk 补上下文再嵌入"是目前被独立复述最多的单点改进 | **本轮未读原文**，归 D 线 |

## 对不上的地方（来源互相矛盾处，单列，不抹平）

| # | 谁在说 | 说 A | 说 B | 我的处理 |
|---|---|---|---|---|
| 1 | 我们自己 vs ure.us | 52.2 万条款 / 2.2 GB / 单文件 SQLite，实测能用 | 100 万份文档的人**明确把 SQLite 元数据索引换成 Postgres**，理由是"不是 SQLite 该干的事" | **两者都对，量级不同**：他是"100 万文档 × 多 chunk × 向量库 × 标签互查"的联合查询；我们是"条款一行 + 精确条号"。**但他这句必须原样递给业主**，因为它正好落在我们要跨的那条线上 |
| 2 | 华为云那篇 sqlite-vector 评测 vs 我们的实测 | sqlite-vec 在 **10 万 × 384 维**上全扫 **67.84 ms** | 我们 52.2 万条款 **606 ms** | **不冲突**：67.84 × 5.22 ≈ 354 ms，同数量级（维数/机器不同）。两边都说明 sqlite-vec 是**线性暴力**，差别只在常数 |
| 3 | 同一篇（竞品自测）vs 上一条 | `sqlite-vector`（另一家）"量化 + 预加载"在 10 万条上 **3.97 ms** | sqlite-vec 同规模 67.84 ms | **竞品自测，未复现**；且"预加载到内存"本质是把代价挪到内存占用（37 MB/10 万条 → 千万条就是 3.7 GB）。**不当结论，只当候选** |
| 4 | 一条 GitHub issue 里的经验值 vs 我们 | `retrieval-skill#3` 引 AGENTS.md：「<100K chunks 全扫 ~10 ms」 | 华为云实测 100K 是 **67.84 ms**；我们外推 52 万是 606 ms | **差 7 倍，未确认**。10 ms 那句没有说明维度、机器、是否预热；**不采信** |
| 5 | linux.do 里的两派 | 一派：RAGFlow/DeepDoc 能用，10W+ 没问题 | 另一派：dify/ragflow "都是跑 demo 的"，且"不必用 embedding，全转 Markdown 走 Agent Search" | **两派都留着**。前者有"10W+ 导入"的事实，后者有"上线后难维护"的抱怨；**"不需要 embedding"是异议，不是结论** |
| 6 | RAGFlow 官方 vs 社区 | README："traceable citations"、"表格结构识别" | #12309 位置回归、#18347 跨页表丢续页、#21215 丢 page positions | **以 issue 为准**（有文件行号、有逐 cell 对比）；README 那句话在"单页 + 英文 + 不换解析器"的前提下可能成立 |
| 7 | RAGFlow 自己内部 | Python 版 DeepDoc 跨页表**保留全部续页行**（#18347 作者原话，附源码行号） | Go 重写版**只保留首页行** | **同产品两个实现不一致**，且 Go 版是新的那条路。⇒ "换语言重写"会静默丢能力 |
| 8 | 关于 MinerU 的单任务上限 | Dify 用户：MinerU **200MB / 600 页**上限 | MinerU 官方 README/文档：**未核到该限制** | **未确认**。列待核；不能用它做容量规划 |
| 9 | 社区对 MinerU 的评价 | 中文社区："DeepDoc 不如 MinerU/合合"（推荐上 MinerU） | RAGFlow 里接 MinerU 后 `FAILED TO PARSE TABLE` 的 issue 成批（#16114 13 评论 / #16060） | **不矛盾但要注意**：MinerU 强在版面，弱在"表格解析失败时要静默降级成纯文本"——**失败不报错，只是变差** |
| 10 | 文档/资料说"Dify 开源" | 各处口径不一 | LICENSE 是 Apache-2.0 + 附加条件（多租户 SaaS / 去 LOGO） | 以 `10-platforms.md` 结论为准，本线只复核未变 |
| 11 | MinerU 的许可证 | 大量二手资料写 "AGPL-3.0"（因为 2024 年确实是） | 2026-04-17 起是 **Apache-2.0 + 附加条款** | **两边都不完整**：现行不是 AGPL，也不是纯 Apache。**写"AGPL"和写"Apache-2.0"都错** |
| 12 | 向量到底要不要 | AlexChu1996：向量有容量上限，但仍是主力，需分桶+微调 | void.shum：「EMBEDDING 不需要」 | **异议保留**。前者给了机制（高维空间拥挤），后者只给了主张（引 Anthropic） |

## 待核清单（我没读到 / 读到了但不算数）

1. **MinerU "200MB / 600 页"单任务上限**：只有 Dify 一个用户这么说，MinerU 文档/源码未核。**这条会直接影响我们的批处理切分策略，必须自行验证。**
2. **MinerU 3.4.5 是否还带 #5313 的内存不释放**：#5313 报的是 3.4.4、已 closed，**close 不等于修好**；需要我们在本机跑 20 份文档看 RSS 曲线。
3. **r/Rag、r/LocalLLaMA 的规模贴**：Reddit 全线 403/429/500，**这轮完全没读到**。规模类结论缺了英文社区那一半。
4. **知乎**：CAPTCHA，未读到。**CSDN** 目标篇 404。**公众号**只读到转载摘要（中汽那篇），原文未取。
5. **所有 dosubot / Dosu 的答复**：RAGFlow、Dify、MinerU 三个仓库的自动回答**一条都不能用**。本轮凡引用到的地方都标了"机器人"。
6. **RAGFlow #12309 的根因**：机器人说是"非 ASCII 文件名 + 坐标抽取改动"，**未证**。
7. **RAGFlow #8490 的"并发卡死"**：只有 dosubot 说"这是已知问题"，无维护者结论。
8. **Qdrant &AI 案例 / 腾讯 ima 千亿级**：**厂商材料**，不是用户实测，我无法验证。
9. **Shaped 博客正文**：只读到标题与转引，未读正文。
10. **Anthropic Contextual Retrieval 原文**：未读（归 D 线）。
11. **ure.us 的作者**：匿名，无仓库、无数据；他说"early results say yes"但拒绝给数字，**不能当"验证过"**。
12. **"10W+ 没啥问题"这句话的实际含义**：user1794 没说清是"导入成功"还是"检索可用"，**这是两个不同的结论**。

## 反证检索记录（搜了什么词、搜出什么）

**对结论 1（没人公开证明过百万级）做反证**：
- 搜「千万级知识库 落地 成功 案例 向量检索」「RAGFlow million documents 成功」→ **确实搜到了**：腾讯 ima 千万级/千亿级 ES、Qdrant &AI 10 亿向量、灵犀医疗 3.5 亿数据/千万级向量、电网 2000 万条。⇒ **"没人做到"是错的，应改成"没有小团队/单机能复现的公开记录"**。结论已按此改写。
- 搜「RAGFlow million documents」在 HN → **0 条**；HN 最大的相关帖是 `Ask HN: How would you architect a RAG system for 10M+ documents today?`（2025-11-21，23 分 9 评论），**里面没有任何人说"我做过 1000 万"**，只有一个人问"pgvector+tsvector 在 10M 行能不能 <200ms"，没人回答。⇒ **英语社区对"我自己做过"这件事比中文社区更沉默**。

**对结论 2（表格是系统性断点）做反证**：
- 查 RAGFlow #18347 的关闭原因 → **不是"不修"，是修了很多次**：`#18362/#18378/#18416/#18516/#18688/#18740/#18789` + 2026-10-16 的 `#21083`。⇒ 结论从"没人做对"改成"**反复修仍在回归**"，更准确也更难听。
- 搜「docling 表格 效果好」「table extraction SOTA」→ 确实有 Rd-TableBench 这类评测（HN，2024-11-05，29 分 6 评论）和 OmniDocBench（归 G 线）。⇒ **"表格抽取有进步"成立**，但"进生产后在中文标准上不丢结构"仍无证据。

**对结论 3（引用会静默失效）做反证**：
- 搜「RAGFlow citation 页码 定位 跳回原文」→ 只回到 README 措辞与 chunk 可视化，**没找到任何"页码字段"的证据**；`10-platforms.md` 的 17 份 README 关键词矩阵里 `页码|page number|pagination` **全库 0 命中**（A 线已做）。⇒ 反证没找到，**结论保留**。

**对结论 6（MinerU 许可会变）做反证**：
- 直接查 `LICENSE.md` 提交历史 + PyPI 三个版本的 `license_expression` + GitHub API `license` 字段，**四路互相印证**：现在是 `LicenseRef-MinerU-Open-Source-License`（Apache+附加），2.1.0 是 AGPL。⇒ **不是误读，是事实**。

**对结论"单机 SQLite 到不了百万"做反证**：
- 搜「sqlite 百万行 向量检索 性能」「sqlite vector search million」→ 一线证据**自相矛盾**：华为云那篇给 100K=67.84 ms（与我们的线性一致），`retrieval-skill#3` 说 100K≈10 ms（差 7 倍，未确认）；另有一篇腾讯云信息页说 "Chroma 底层 duckDB+sqlite-vec，10 万条以下很流畅，几十万开始明显变慢，百万别想了"【转述】。
- 结论：**"SQLite 在百万级"本身没被证伪**（是暴力扫描被证伪），但**没有一个实践者在百万级继续用单文件 SQLite 做联合查询**——ure.us 那位是唯一给了理由的。**这条留作待裁决，不是结论。**

**对结论"向量该不该继续投"做反证**：
- HN `Ask HN: How would you architect a RAG system for 10M+ documents today?`（46000077，2025-11-21）里最高赞的答复是「先做 Hybrid（Vector + Keyword）基线，等基线在具体 query 上失败了再加复杂度」；另一条是「docs 小（1–2 页）就不需要切分，一页一向量就行」。
- HN `Everyone's trying vectors and graphs for AI memory. We went back to SQL`（2025-09-22，136 分 63 评论）——**标题本身就是对我们"往回走"的旁证**（未读正文）。
- 反方向上，论坛「EMBEDDING 不需要」**没有**给出任何可复现对比。⇒ **结论：继续用向量，但把它降级为"补充通道"更站得住**；这与我们"六通道 + RRF"的现状一致，**但"向量必须是主通道"没有社区支持**。

## 对我们（这些社区信号验证了哪几条、否证了哪几条）

| # | 我们的判断（来源） | 社区信号 | 结论 |
|---|---|---|---|
| 1 | **表格/公式可回溯**：条款一行一条、带 bbox 与页码、点回原文页（`REQUIREMENTS-v4.3` / `00-brief §三`） | ① 别人**连保持不坏都做不到**：#12309 中文 PDF 位置映射回归、#21215 换解析器直接丢 page positions、#18347 跨页表丢 24 行；② 但**没有一条信号说"条款级 + 坐标溯源是错的/多余的"**，反而 TextIn、CATARC、jlcbk 三家都在做同一件事（页码/路径/坐标、locator、三栏对照） | **验证**。方向对，且是差异化。**但加一条硬约束**：page/bbox 必须是解析器的**强制输出字段**，缺失应当**报错而不是静默通过**——RAGFlow 的失败模式正是"看起来成功"。 |
| 2 | **百万级可行性**：单文件 SQLite（WAL）+ 条款一行 + sqlite-vec（`00-brief §二/§三`） | ① **否证中最强的一条**：ure.us 在 100 万文档上把 SQLite 元数据索引**换成 Postgres**，理由是联合查询；② 华为云 benchmark 与我们的实测**同数量级、同随条数线性增长**（100K 67.84 ms；按线性外推 522K ≈ 354 ms，我们实测 606 ms，差 1.7 倍），说明**瓶颈是暴力扫描，不是 SQLite 本身**；③ 论坛实证"分桶 + 底层桶 200–1000 条"与我们"候选集收到 50 时前 20=99%"同向 | **部分否证**。**"单文件 SQLite 撑到千万条款"这句话不能再当成已验证**：它验证过的是 52 万（实测），不是千万。建议口径改成：**"条款表 + FTS5 + 精确条号可以留在 SQLite；只有向量通道在超过某个量级后需要外部件，且允许它变慢而不是摧毁整库便携性"**。这是要给业主裁决的**代价**，不是技术细节。 |
| 3 | **许可证风险**：MinerU 走 `mineru` 包规避 AGPL（`20-parsing.md §八`） | MinerU 六周内许可翻转四次，现行是 **Apache-2.0 + 附加条款**（在线服务署名 + 商业门槛），PyPI 表达式是 `LicenseRef-MinerU-Open-Source-License`；`magic-pdf` 仍是 AGPL | **验证了"要盯许可"，同时更正了一条事实**：我们**确实不是 AGPL**，但也**不是纯 Apache**；且这是一个"半年改三次"的依赖 ⇒ **锁版本 + 随包附当版 LICENSE + 不写死"Apache-2.0"**。另外：Weaviate（BSD+`wl/` 专有）、Elasticsearch（三许可含 AGPL）说明**不能按 spdx 字段判许可**。 |
| 4 | **单机便携**：Electron + 单文件库"拷走就能用"（`AGENTS.md` 便携硬约束） | ① ure.us 被迫上 Postgres + Neo4j + 两套 GPU 集群；② 论坛 3 万文件就要 7–12 GB 内存、2–3 秒检索；③ MinerU 3.4.4 **RSS 只涨不落**（批量必死）；④ Onyx 不变文档也全量重嵌 | **否证**："便携"与"百万级"在别人那里也是**二选一**。**技术上的可行解不是没有**：单机批处理做**进程级回收 + 断点续跑**（对 MinerU 那条是必需的），索引侧做**分桶收窄**（论坛共识 + 我们实测）。但"一个文件拷走 = 千万条款全带走"这句必须由业主裁决。 |
| 5 | **六通道 + RRF**（`RETRIEVAL-LONG-RANGE-PLAN`） | ① HN 高赞建议"先做 Hybrid 基线，基线失败再加复杂度"——我们已经是六通道，**复杂度在基线之上**；② 论坛有人主张"不需要 embedding"；③ AlexChu1996：向量有容量上限，"各种 BM25、图谱、关键词筛选大多都是在弥补这个问题" | **验证了一半，质疑了一半**。社区**支持"多路互补"**，但**不支持"向量当主通道"**。⇒ 如果我们的排序实际上让向量占主导，这条该重新看；若向量只是六分之一，与社区共识一致。**这条要看代码里的实际权重，不是看设计文档。** |
| 6 | **条款校对界面**（我们已有） | CATARC 的"三栏联动校验、点原文段落定位解析结果"、RAGFlow 的 "visualization of text chunking to allow human intervention" | **验证**。而且是买方视角的验证：商业产品也是这么交付的。 |
| 7 | **"我们的语料别人没做过"** | 反例出现：CATARC（汽车行业标准法规拆解）、TextIn（国家标准知识库解析）、jlcbk（GB 条款索引开源骨架）、yeslon（1200 条标准条文检索 + 引用绑定） | **部分否证**。**"中文国标条款级"不是无人区**，而是"有人做、但技术细节全不公开"。⇒ 差异化要落在**可核的精度与可回溯**上，不能落在"只有我们做"。 |

---

## 补充：Lead 2026-10-25 追加的 5 条信号（本轮并行抓取，未与上文重复）

> 这四条是 Lead 在同日独立检索时抓到、上文未覆盖的；补充进来是为了不留缺口。档位同上：GitHub issue 为【一手·issue】，HN 为【转述】。

**补 1 · RAGFlow #21220（open，2026-10-22）· MinerU 坐标空间错**
标题原话：*"MinerU PDF positions are emitted in the service's normalized bbox space instead of PDF page space"*。
- **为什么这条对我们最要紧**：我们在 `src/core/ingestion/pipeline.py` 顶部留过**两次同型事故**的留痕（曾误判为左上原点 → 加 `_flip_bbox` → 前端又 H−y → 双重翻转、黄标垂直镜像；`_flip_bbox` 已删除，契约改为"PDF 底部原点、原样直存、前端直接用 pdfjs 映射"）。
- **意义**：① 这是"别人的失败验证我们已经解决"的少数实例；② 但它同时说明 **MinerU 的坐标语义本身是易错源** ⇒ 升级 MinerU 大版本时，坐标必须当一等验收项（B 线的升级建议必须带上这条）。

**补 2 · RAGFlow #20841（open，2026-10-12）· 引用跨轮复用**
标题原话：*"Go: in follow-up turns the model reuses the previous answer's [ID:n] markers, so citations open the wrong passages"*。
- **意义**：这正是"红箭头点过去对不上"的同型故障。我们的引用是"条款号 + 页 + bbox"不是 `[ID:n]`，但风险同源：**只要引用编号由模型生成而非检索结果绑定，多轮就会串**。⇒ 支持 D 线"引用必须确定性绑定"。

**补 3 · RAGFlow #21095（open，2026-10-17）· 溯源字段被静默丢**
标题原话：*"SearchDataset response drops source_doc_ids on dataset-level compiled chunks, breaking provenance attribution"*。
- **意义**：溯源字段在中间层被静默丢弃，是"引用功能存在但不可信"的典型成因。我们的 `evidence_url` 是拼出来的 ⇒ 要检查中间层有没有同类静默丢弃（只作提醒，不是结论）。

**补 4 · HN：PageIndex「Vectorless RAG」192 分 / 128 评论**【转述】
- 它是什么：不建向量索引，用 LLM 在"章节摘要树"上做推理式导航，决定该读哪一段。
- 社区最高赞的质疑（原话）：*"When you have a question and you don't know which of the million documents in your dataspace contains the answer — I'm not sure how this approach will perform."*；另有 *"it goes over every possible document with an LLM each time someone performs a search?"*（质疑延迟/成本）；也有人认可它的场景：*"Great for manuals, documentation and larger content."*
- **意义（本轮最有价值的一条社区信号）**：它代表"结构 + 推理"路线的最激进形态，而社区划出的边界**正好落在我们身上**——小集合里结构导航很好，**百万文档必须先有"是哪一份文档"这一层**，而那一层正是我们的标准号/条款号精确通道（0.1 ms，不随行数涨）。⇒ 反证"纯结构导航可替代编号定位"，支持我们"先按编号收窄文档空间，再谈结构理解"的架构。

**补 5 · HN：Wikipedia 离线向量检索 325 分**，评论原话 *"It's incredibly impressive for what it does, but the results don't seem very good"*，并给失败例（问"奇怪的猴子"返回 `Pet monkey` / `List of individual monkeys`）。
⇒ 纯稠密检索的失败**用户能立刻感知**，支持我们"精确条款号通道权重最高（2.0）"的设定。

## 对我们（收尾：把补充 1–5 归位到上面 §对我们 的判决里）

> 上面 §对我们 的 7 条判决**不因补充 1–5 改变**，只被加强或加注。三条 RAGFlow issue（#21220 / #20841 / #21095）本轮我已逐个回核过标题与状态（均 open，2026-10-12～10-22），**是这几条的编号与用语不是转述**。

| 补充 | 归到哪一条 | 判决变化 |
|---|---|---|
| 补 1 RAGFlow #21220：MinerU 的 positions 用的是服务自己的**归一化 bbox 空间**，不是 PDF 页空间 | 对我们的第 1 条（表格/公式可回溯） | **加强**。"page/bbox 必须是强制字段"之外再加一层：**坐标空间的原点与单位也必须是契约的一部分**。我们历史上吃过两次同型事故（右上下翻转、前端再 H−y 造成垂直镜像，`_flip_bbox` 已删），这条 issue 证明这个坑不是我们独有的失误，而是**跨产品共性**⇒ 坐标应作为升级 MinerU 大版本时的一等验收项，写进 B 线的升级清单。 |
| 补 2 RAGFlow #20841：多轮对话里模型复用上一轮的 `[ID:n]` 标记，**引用点开是错的段落** | 对我们的第 1 条（可回溯） | **加强，且是新的失败形态**：我们不是 `[ID:n]`，是"条款号 + 页 + bbox"，但只要引用标识由**模型生成**而不是**检索结果绑定**，多轮必然串。⇒ 这不是"别人有 bug"，是"我们的架构里必须有一条：引用只能来自检索结果，不许模型续写编号"。 |
| 补 3 RAGFlow #21095：SearchDataset 在 dataset 级 compiled chunks 上**静默丢掉 source_doc_ids**，溯源断链 | 对我们的第 1 条（可回溯） | **加强**。"引用功能存在但不可信"的成因多半是**中间层静默丢字段**，而不是最后一步渲染错。⇒ 我们的导出/检索响应要有"溯源字段守恒"断言（进入多少条、带 source 出来多少条）。 |
| 补 4 HN：PageIndex「Vectorless RAG」192 分 / 128 评论，社区最高赞质疑是"百万文档里你根本不知道是哪一份含答案" | 对我们的第 5 条（六通道 + RRF）与第 2 条（规模） | **这是本线最有力的一条正向反证**：社区的边界正好划在"必须先有'是哪一份文档'这一层"，而那一层是我们的**精确条款号通道（0.1 ms，不随行数涨）**。⇒ **"先用编号把文档空间收窄，再谈结构/语义"这条路，社区给了独立支持**；同时也说明"用 LLM 在摘要树上导航"在我们这个量级**不能替代**编号通道。 |
| 补 5 HN：Wikipedia 离线向量检索 325 分，评论"impressive，但结果不太好"，失败例（问猴子返回 `Pet monkey` / `List of individual monkeys`） | 对我们的第 5 条（向量权重） | **加强"向量降级为补充通道"**。纯稠密检索的失败是**用户能当场感知**的（答非所问而非报错），这类失败最伤信任。⇒ 支持我们现行的"精确条款号权重最高"；但**反过来也提醒**：我们的向量通道若单独出结果，必须有阈值兜底，宁可不给。 |

**一句话收尾**：补充 1–3 说的是"**引用会在你看不见的地方坏掉**"（坐标空间、编号复用、字段静默丢弃），补充 4–5 说的是"**没有编号那一层，语义检索在这个量级撑不住**"。两条合起来，正好把我们"精确条款号 0.1 ms + 条款一行 + 点回原文页"钉成**不是优化项而是地基**；而前面 §对我们 第 2 条（单机 SQLite 到千万条款未经证实）仍然是本轮**唯一需要业主裁决**的地方。
