# 愿景对照矩阵：**我们的每一块愿景，谁已经实现了**

> **用途**（两种，都很实际）：
> ① **自己用得爽**——找出哪些件可以**直接拿来组装**，不重复造；
> ② **认清差距**——别人已经实现到哪一步，我们自研还剩什么。
> **口径**：只写我**读过一手材料**的；没读过的列入 §四"待验证"。厂商自述会标注。
> 与 `substitute-scan.md` 的分工：那份按"**替代品/威胁**"组织，这份按"**我们的愿景组件**"组织。

## 一、愿景组件 × 谁实现了 × 能不能直接用

| # | 我们的愿景组件 | 已实现者（一手证据） | 实现到什么程度 | 能不能直接拿来用 |
|---|---|---|---|---|
| 1 | **PDF/扫描件/Office/网页解析**，产物带坐标 | **MinerU**（[横/纵逐行 bbox、表格单元格结构化](https://github.com/opendatalab/MinerU/discussions/4869)）、Docling、PaddleOCR-VL、MarkItDown、OpenDataLoader | 解析层**完全成熟**，且输出坐标 | ✅ **直接用**（我们引擎里的 MinerU 就是这条） |
| 2 | **条款级切片 + 引用点回原文并高亮** | **Obsidian PDF++**（MIT）：`[[file.pdf#page=1&selection=4,0,5,20&color=red]]` ⇒ 点链接**跳页 + 高亮选区**；反向把 backlinks 高亮进 PDF；hover 预览/同步；按页过滤 backlinks | **"个人用着最爽"的标杆**：本地、纯 markdown、不改 PDF 也能用 | ✅ **直接用/直接抄体验**（它是选区+页级，**不是条款语义**）<br>⇒ 引用定位的**四级阶梯**见 §五.1（L1 页级 → L4 bbox+裁图） |
| 3 | 标准元数据 + 现行/废止/被代替 + 全文下载 | **GBMCP**（MIT，[标准 MCP 服务器](https://github.com/LoyDgIk/GBMCP)）：国标/行标/地标/团标/ISO/DIN 元数据；`status=现行/即将实施/废止`；**`replaced_standard_no`（被代替标准）**；下载 openstd GB 全文 PDF、CFSA 食品、MEE 环境、NHC 卫生、**MEM 应急管理**、RESMEA 计量、ITU；**带配套 skill**（`skills/gbmcp-standards`）；批下载、验证码 OCR、缓存 | **≈ 我们的 13 个渠道适配器 + 五类数据里的一大半**，而且是 MCP 形态（agent 直接用） | ✅ **直接用**（省掉大量适配器维护） |
| 4 | 法规全文 + 效力/时效 + **条文核验** | **北大法宝 MCP Skill**（v4.0.0）：10 工具，含**法规名识别/案号验真/条文原文对照**、**条级锚点超链**、时效强制标注 | 商业、权威、计费跑通 | ⚠ **要钱**（积分制）；且**不含国标** |
| 5 | 通用知识库问答 + 引用 + 多格式 + 本地 | **WeKnora**（MIT）：解析/检索/引用/多租户/**DSH 插件**/Lite 单二进制/桌面版 | 工程远深于我们（见 `weknora-assessment.md`） | ✅ **可直接自部署**（或只借它的检索层） |
| 6 | 标准**条款级**检索/跳转/强条聚合/条文说明/版本对比 | **工标库**（中国发展改革出版社）：全（条）文检索、**一键直连废止条文**、强条聚合、条文说明整合、标准对比、**标准追踪（短信）**、AI 检索、智能审校 | 商业、正版库、有"法律法规"栏目（**已跨域**） | ⚠ 要买（且是**它的**在线库，不是你的文件） |
| 7 | **"条文级溯源/版本追溯/引用错误检测"** | **WPS 黑马校对**（行标条文核对）、**WPS PDF**（OCR+双层 PDF，毫秒级定位合同条款） | 已是办公软件内置功能 | ⚠ 商业；入口/装机量碾压 |
| 8 | **规范条文自动检查**（合规核查自动化） | **施工图智能审查**：广联达 BIM、中设数字、**政府侧**（上海住建委智能审查流程） | 行业成熟品类，政府推动 | ❌ 不自研（BIM 域，重） |
| 9 | **巡检 / 变更监控 / 告警** | 商业：工标库（短信追踪）、中国标准在线（行业推送+标准跟踪）；开源：**changedetection.io / urlwatch / Huginn**（R1 已代码级拆解，见 `oss-decomposition.md`） | 开源监控**通用**（"页面变了没"），标准语义要自己做 | ✅ 开源件可用（我们已自研同构的巡检） |
| 10 | 义务清单 / 检查表 / 整改闭环 / 培训 | **赛为 AI 合规智审**、**Benchmark Gensuite**（RegTracker + CAPA + LMS + Genny AI/MCP） | 成熟品类，通常**软件+咨询+培训**打包 | ❌ 不自研（我们的子集，且是管理流程） |
| 11 | 个人知识库体验（收藏/笔记/双链/术语）**+ 台账/数据库** | **思源(SiYuan) 46419★**：块级引用+双向链接、**PDF 注释锚点 `assets/x.pdf?page=2&box=<id>`**、**属性视图(数据库)一整套 `/api/av/*`**、**自带 CLI（无需服务、可搜 PDF 内部）**；Obsidian / Logseq；工标库（收藏+笔记+术语库 10 万） | 极成熟，且**连"可维护台账"都是现成的** | ✅ **直接用**；⚠ 思源是 **AGPL-3.0**——自用无碍，嵌进要卖的交付物有义务（见 §六.1） |
| 12 | 交付物（报告 / PPT） | Marp / Slidev / python-pptx（**待验证**）；WeKnora 有 Wiki 生成 | 通用件成熟 | ✅ 通用件可用 |
| 13 | 检索质量评估（基线门禁） | **RAGAS / DeepEval / TruLens**（**待验证**）；WeKnora 有评估页 | 通用件 | ✅ 通用件可用 |
| 14 | **只引现行版 + 数值/条款核对 + 三段式取证 + 未核验不得承重 + 外发留痕** | **部分**：北大法宝 MCP 有"禁止凭记忆/时效标注/核验闭环"；**数值级核对**（如 ≥12m vs GB 51283 第 4.2.9 条 ≥25m）**没找到专门产品** | 纪律类，散落在各家 | ⚠ **这一块仍是我们最该守的**（见 §三） |
| 15 | **自有材料 + 评审硬门 + 权威两轴（T0–T4 × 任务效力）** | 工标库只有"收藏+个人笔记"；WeKnora 有知识库但**无"未批准不得承重"**；**没找到等价物** | **没找到等价物** | ⚠ **仍是我们最该守的**（见 §三） |
| 16 | **法规全文 + 逐条结构化 + 现行性 + 可引用链接** | **`chinese-law-corpus`（自称 CC0）+ `chinese-law-mcp`（MIT）+ 法脉 LawPulse**（§五.2，已核实存在与结构）：412 部现行法律/司法解释、26,000+ 条、稳定条文 id、编/章/节/条层级、效力状态与施行日期、**逐条可引用静态页** | **法规侧已经做完且公开**，自研是重复劳动 | ✅ **直接用**（`npx` 即用）；但**不含标准（GB/行标）**，且 CC0 声明未法律闭合 |

> ⚠ **更正（2026-09-24，一手核）——上表第 3 行 GBMCP 的「被代替标准」是错的，"✅ 直接用"要降级。**
>
> **错话原文保留在上表第 3 行**：那里写它提供 **`replaced_standard_no`（被代替标准）**，并判 **✅ 直接用**。
> **事实**：2026-09-24 实取它的 `src/gbmcp/models.py` —— `StandardItem` / `StandardDetail` 里
> **根本没有这个字段**；`replaced_standard_no` 只是某工具的**入参**（筛选用），不是输出能力。
> 仓库另有许可瑕疵：README 与 `pyproject.toml` 都写 MIT，但**根目录没有 LICENSE 文件**
> （GitHub API `license: null`、★1、最后提交 2026-06-05，约 3.5 个月无提交 —— 这几项来自子代理的 API 实读；
> 我自己复核该项时被 GitHub 限流 403，**故如实标注来源**，但"没有该字段"是我本机实取源码得出的）。
> ⇒ **改判**：GBMCP 的价值是「**哪个 URL、读哪个字段**」的接口知识，**不是可采纳的代码或数据源**；
> §二第 1、2 条（"GBMCP 值得先接""维护一个 MCP 依赖"）**据此不再成立**。
> 这是"**字段描述 ≠ 运行时语义**"第二次打我们（上一次是 reflect 的 `max_tokens`）。

> ⚠ **补（同日，本机实测）——「被代替」在官方源里是反向指针。**
>
> `GET https://std.samr.gov.cn/gb/search/gbAdvancedSearchPage?typeRadio=std-param&tid=2&std_p4=<号>`（**JSON、无验证码**，实测 200）：
>
> ```
> GB 18030-2022 | STATE=现行 | ACT_DATE=2023-08-01 | TOTAL_REPE=GB 18030-2005
> GB 18030-2005 | STATE=废止 | ACT_DATE=2006-05-01 | TOTAL_REPE=GB 18030-2000
> ```
>
> ⇒ **`TOTAL_REPE` = "本标准代替了谁"（向后指针）**，不是"被谁代替"。
> 要填 `superseded_by` **必须反查全目录**（或读废止公告）。
> **这解释了本库 `superseded_by` 为什么 0 行** —— 不只是"巡检只发现不回写"，
> **上游这个字段的方向本来就跟我们存的方向相反**。
>
> 另：**我们自己的 `std_samr_hb` 适配器早就在打这台机器**（`std.samr.gov.cn/hb/search/hbPage` → JSON，
> 行含 `STATE` 且取值包含「被代替」），且早就解掉了"必须传归一号否则后端退化成 match-all"那个坑
> （见 [std_samr_hb.py](../../src/core/update/channels/std_samr_hb.py) 文件头 1–22 行）
> ⇒ **行标侧已有现成件；国标侧缺的是同款的 JSON 走法**（我们现在走 openstd 的 HTML + 验证码）。

## 二、三条立即可执行的结论（对"自己用着爽"）

1. **最小可用组装方案已经存在**：
   `MinerU（解析+坐标） + Obsidian/PDF++（引用定位与阅读体验） + GBMCP（标准元数据/状态/下载）
   + changedetection（变更监控） + 一个本地 RAG（WeKnora Lite 或自研检索）`
   —— **这套不写代码也能用到七成**；我们自研的价值必须落在它们都不做的那三件事上（§三）。
2. **GBMCP 值得先接**（MIT、MCP 形态、带 skill、正好覆盖我们 13 个适配器想做的大半）：
   接它 = 我们的"渠道覆盖"从"自己维护 13 个适配器"变成"**维护一个 MCP 依赖 + 自己的差异层**"。
3. **Obsidian PDF++ 是"引用体验"的现成参照**：它证明"**点引用 → 跳页 → 高亮**"这件事
   在本地 markdown 生态里已经做得比我们顺（而且不锁格式、不用 PDF 坐标契约）。
   ⇒ 我们的坐标契约（bbox 底部原点）要先回答一个问题：**它比"页 + 选区"多买到什么？**
   （我的答案候选：**条款语义**——`GB 51283-2020 第4.2.9条` 是可引用的单位，而选区不是。）

## 三、盘点之后，**仍然只有我们这三件事**没人做

1. **"只引现行版 + 数值/条款级核对"**——把结论里出现的**规定值**（≥25m / 间距 / 浓度）
   逐条对回**现行版条款**，错了就拦下。（北大法宝管"法条对不对"，不管"数值对不对"；
   WPS 管"文本校对"，不管"效力"；工标库管"库内阅读"，不管"你的结论"。）
   ⚠ **§九 已更正**：数值核对**并非无人做**——消防审图、UpCodes Plan Review、LIMS 都在做，
   空白只在于「**引用驱动**」这一范式。本节「没人做」应读作「**没人用引用驱动的方式做**」。
2. **"自有材料也能当依据，但要过评审门 + 权威两轴"**——未批准的材料**不得承重**。
   （所有替代品都只服务"他们的权威库"，没有一家处理"**你的**材料当依据"的纪律。）
3. **"可核验的覆盖率"**——台账里每条渠道的**链接/有效性/上次成功/失败原因**，人工可维护。
   （商业件只是"宣称我覆盖全"，没有一家把**渠道健康度**摊开给你看。）

⇒ 这三件事恰好是**"取证/举证"**而不是"查库/管理"。**如果我们要做产品，护城河在这里；
如果只是自己用着爽，这三件事就是我们自研的全部理由。**

## 四、待验证清单（下一轮继续，按价值排序）

| 项目 | 要验证什么 | 为什么重要 |
|---|---|---|
| **RAGFlow**（InfiniFlow，开源） | 它的"**引用溯源/可解释性**"到底是**块级还是页/坐标级**；深文档解析（表格/版面）质量 | 它是最像我们"通用层"的开源对手，且主打可溯源 |
| **思源/SiYuan、Obsidian+ZotLit** | 块引用 + PDF 标注 + 引用的**可迁移性**；能不能当"条款级"容器 | "自己用着爽"的宿主候选 |
| **Open WebUI / AnythingLLM / Khoj** | 本地知识库的**引用形态**与"点回原文"能力 | 个人自用的一体化宿主 |
| **Dify / FastGPT / MaxKB** | 同上（它们更偏应用编排） | 交付形态参照 |
| **Zotero (+ZotLit / Better BibTeX)** | 学术场景的"引用 → 定位 → 反向链接"完整度 | 与 PDF++ 同类但更"引用管理" |
| **MCP 生态**：zotero-mcp / pdf-mcp / obsidian-mcp / 其他标准类 MCP | 有没有已经把"条款级引用 + 本地文件"做通的 MCP | 决定我们是**接**还是**做** |
| **RAGAS / DeepEval** | 能否直接作为我们 Golden Set 的替代（省自研） | 减自研面 |
| **Marp / Slidev** | 报告→PPT 的现成链路 | 交付物是否还需自研 |
| **aihse.cn**（EHS 网的 AI 产品） | 它做到哪一步（是否已含标准引用核对） | 垂直 AI 的直接对手 |

> **第五轮已一手关闭**：RAGFlow（§五.1 L4）、Open WebUI（§五.1 L1+L2）、AnythingLLM（§五.3）、
> Zotero MCP 生态四家（§五.4），以及**新发现**的 `chinese-law-mcp` / `chinese-law-corpus` / 法脉 LawPulse（§五.2）。
> **第六轮已一手关闭**：思源 SiYuan 当宿主（§六.1）、RAGAS 指标可用面（§六.2）、Marp/Slidev/python-pptx 交付链（§六.3）、
> aihse.cn（正文抓不到，但赛道形态已看清，§六.4）。
> **仍未验证**：ZotLit、Dify/FastGPT/MaxKB、DeepEval（RAGAS 的替代/补充）。

## 五、第五轮一手验证：引用定位粒度 + 法规侧 + MCP 生态

### 1. 引用定位粒度：不是二选一，而是**四级阶梯**（全部一手源码/组件）

| 级 | 定位能力 | 谁这么做（一手证据） | 代价 |
|---|---|---|---|
| L1 | **页级**：跳到 PDF 第 N 页 | Open WebUI（`.../files/{file_id}/content#page={page+1}`，读的是 `metadata.page`，0-based）；**我们现在的 `evidence_url` 就在这一级** | 免费，只能到页 |
| L2 | **页 + 文本片段高亮**（浏览器原生 `#:~:text=首词,尾词`） | **Open WebUI 正在用**：`CitationModal.svelte` 的 `getTextFragmentUrl()` 取 chunk 首尾词拼 `#:~:text=` | 纯前端、零解析成本；扫描件/双栏/断行会失效 |
| L3 | **引文反查坐标**：给一段引文，反查它在 PDF 里的位置（容忍换行与连字符） | **Zoteus** 的 `zotero_annotate`：quote 一段话 → 定位到所占行 → 锚定批注，原话是「so no page coordinates are needed」 | 需要文本层；**这是"回写/批注"方向的正解** |
| L4 | **页 + bbox 多矩形 + 服务端裁图** | **RAGFlow**：chunk 存 `position_int`/`page_num_int`/`top_int`，坐标形如 `[[page,left,right,top,bottom],…]`（**可多段**）；`_crop_pdf_preview()` 按坐标裁图（dim 上下文 + 3× zoom）贴到答案旁 | 需要版面解析；**扫描件也有效**，且能把图直接给模型看 |

⇒ 回答我上一轮留给自己的问题「bbox 比页+选区多买到什么」：**买到的是多区域定位（跨栏/跨页）+ 服务端裁图（扫描件可用）**。
但若只要「点得准」，**L2/L3 是零成本或低成本**，其中 L3 正是 RAGFlow 那条重路线的廉价替代。
**我们最短的一步升级是 L1 → L2**：纯 URL 拼接，不需要重新解析任何语料。

### 2. 法规侧：**已经被人做完了，而且是公开语料**（这条削弱了我一个假设）

`chinese-law-mcp`（MIT，`npx` 即用）背后是 `chinese-law-corpus`——我**逐项核实过**（`gh api` 拉 tree：未截断、1139 个文件、8.5 MB）：

- **412 部现行有效法律与司法解释、26,000+ 条逐条结构化**：含稳定条文 id（`civil-code-0577`）、条号、正文、
  **编/章/节层级**、公布日期/施行日期/效力状态/发布机关；
- **+278 件最高法指导性案例 +445 件公报案例**（裁判要点/基本案情/裁判理由分字段）；
- 来源是国家法律法规数据库 `flk.npc.gov.cn` 的官方 docx，**逐部人工核对**；LICENSE 首行与 README 双处声明
  **CC0 1.0**（⚠ 非 SPDX 识别文件，GitHub 元数据标 `NOASSERTION`；见 §八 最大风险）；
- 它的 README 里已经写出了我上一轮当作「候选护城河」的那句话：**「一条 = 一个法条，天然的 chunk 边界」**；
- 基于它已经有人在做产品：**法脉 LawPulse**（律师向、本地优先桌面、离线法律库 + 法条笔记 +
  **引用可核实的合同审查**），并把 27,000+ 页条文做成**逐条可引用的静态网页**（`/laws/<slug>/<n>.html`）——
  比我们的「PDF 页锚点」更适合当可引用链接。

⇒ 三条推论：

1. **法规（法律/司法解释）的「采集 + 逐条结构化 + 现行性」是零护城河**：成本是 `git clone` 级别。
   我们若还自己爬 `flk.npc.gov.cn`，是纯重复劳动；应改为**直接消费公开语料**。
2. 它**不含**地方性法规，**完全没有标准（GB/行标）**——**与我们 6417 个标准号语料零重叠**。
   所以这条削弱的是「法规侧」，不是「标准侧」。
3. 「逐条结构化 + 可引用链接」本身**可被复制**，不构成护城河；护城河仍在 §三 那三件事上。

### 3. 本地宿主的引用形态：**都不是条款级**（一手读组件源码）

| 宿主 | 引用数据结构 | 点回原文能力 |
|---|---|---|
| **Open WebUI** | `citation = { source:{name,url}, document:[逐段], metadata:[逐段], distances:[逐段] }` | 页级 + `#:~:text=`（L1+L2）；相关性按 distance 百分比上色 |
| **AnythingLLM** | `sources = [{id,title,text,chunkSource,score}]`，按 title 合并并计 `references` 次数 | **PDF 只能到文档**：`parseChunkSource()` 只认 `link://`/`obsidian://`/`paperless-ngx://` 等 URI 前缀，普通上传件返回 `nullResponse`（无链接、无页码）；正文里塞 `<document_metadata>` 头（显示前用 `omitChunkHeader` 剥掉） |

⇒ 两家都停在**块级 + 文档/页级**，**没有一家做条款级**。与 §三 判断一致。

### 4. Zotero MCP 生态：**四条可直接借的技术**（一手读 README 与工具表）

| 项目 | 星 | 一手能力 | 对我们 |
|---|---|---|---|
| `54yyyu/zotero-mcp`（`zotero-mcp-server`） | 5078 | 读 PDF **page ranges**；原文说「text extraction garbles math, figures, tables 时给 **page images**」；批注是「highlights and **area boxes placed on the exact words**」；`[pdf]` 额外含 outlines/页面布局/页面图像（PyMuPDF） | **页范围读取 + 图像兜底**正是我们解析兜底该有的形状 |
| `cookjohn/zotero-mcp`（Zotero 插件） | 1164 | **29 工具**；`search_annotations` 按**颜色/tags/类型**（note/highlight/annotation/ink/text/image）检索；内容抽取四档 `minimal/preview/standard/complete` | **批注按颜色/标签检索**是「自有材料」最好的入口（人已经标过色了） |
| `oscardvs/zoteus`（TS/MIT，本地优先） | 40 | **引文反查坐标**（§五.1 的 L3）；passages **带 page locator**；把**自己的笔记与 PDF 批注**也索引进检索（`ZOTEUS_INDEX_OWN_WORDS`）；BM25 开箱可用、向量 opt-in，且**不可用时会明说**而不静默返回空 | 「**明说不可用**」与我们「不得静默降级」同源，可当参照 |
| `kujenga/zotero-mcp` / `swairshah/zotero-mcp-server` / `X-T-E-R/Zotero-MCP-Neo` | 162/29/15 | 轻量封装 Zotero API；Neo 是**插件内嵌 MCP**（6 工具、读写均支持） | 形态参照：**把 MCP server 嵌进宿主**本身是一种分发方式 |

⚠ **一条关于 MCP 成本的一手数据**：`54yyyu/zotero-mcp` 自己算过账——一个 **38 工具的 MCP server
每个请求要发送 13,448 tokens 的 schema**；它因此额外提供 **skill 形态，仅占 98 tokens**。
⇒ 直接印证我们应优先做 **skill / 命令**，而不是「工具越多越好」的 MCP。

### 5. 这一轮对 §三 三件事的影响

- **没有被动摇**：数值/条款级核对、自有材料评审门 + 权威两轴、可核验覆盖率——本轮**仍然一家都没找到**。
- **新增一条压力**：法规侧的「逐条结构化 + 每条约可引用链接」已被公开语料 + 静态站点做掉，
  它**不是**护城河，**不要把「法规逐条结构化」当卖点**。
- **新增一条自用捷径**：个人使用时，法规可直接 `npx chinese-law-mcp` 接进 DSH，
  **不写一行采集代码**就能得到 412 部法律逐条 + 可引用链接（标准侧仍需 GBMCP 或我们自研）。

## 六、第六轮一手验证：思源当宿主 / RAGAS 当门禁 / 交付链 / aihse

### 1. 思源（SiYuan）：**"自用宿主"最强候选，而且它把"台账"也做完了**

一手事实（读 README、`docs/API.zh-CN.md` 2905 行、`docs/SKILL-MANAGER.zh-CN.md`、仓库测试断言；未安装未运行）：

| 事实 | 证据 |
|---|---|
| 46419★、**AGPL-3.0**、TypeScript、2026-09-18 仍在更新；自述「隐私优先、自托管的知识工作空间，让人与智能体协作」 | `gh api repos/siyuan-note/siyuan` |
| **块级引用 + 双向链接**、自定义属性、**PDF 注释链接**、数据库（属性视图） | 仓库 README 功能清单 |
| **PDF 注释锚点格式 = `assets/x.pdf?page=2&box=<boxID>`** | `kernel/model/asset_reference_test.go`：`TextMarkAHref: "assets/link.pdf?page=2&box=20260812000000-source0"`；`{MAsset: []*av.ValueAsset{{Content: "assets/file.pdf?page=3&box=" + sourceBoxID}}}` |
| **属性视图是一整套 API**：`getAttributeView`/`addAttributeViewBlocks`/`removeAttributeViewBlocks`/`addAttributeViewKey`/`removeAttributeViewKey`/`setAttributeViewBlockAttr`/`searchAttributeView`/`setAttributeViewFilters`/`setAttributeViewSorts`/`setAttrViewGroup`/`renderAttributeView`/`getAttributeViewPrimaryKeyValues` | `docs/API.zh-CN.md` 的 `/api/av/*` 清单 |
| 另有 `/api/query/sql`（对块直接 SQL）、`/api/attr/setBlockAttrs`、`/api/block/getBlockKramdown`、`/api/asset/upload` | 同上 |
| **自带 CLI，无需运行服务**：`siyuan search "phrase" --asset --ext pdf --ext docx -w ~/SiYuan`（**能搜 PDF 内部**）、`siyuan export md --id <block-id>`，内容组含 `block`/`attr`/`outline`/`database` | README 的 CLI 段 |
| 公开/内部 API 有明确边界：只有文档里单列的接口算公开 API，其余内核路由与 `/api/transactions` 不承诺稳定；路由声明由 `app/src/types/api/index.d.ts` 生成 | `docs/API.zh-CN.md` + `docs/API-CONTRACTS.md` |
| **技能管理**：管理工作空间 `data/storage/ai/agent/skills/<目录>/SKILL.md`，并把 **`~/.agents/skills` 的外部技能列为只读可启用** | `docs/SKILL-MANAGER.zh-CN.md` |

⇒ 三条对我们的直接后果：

1. **目标②（台账可见 + 人工可维护）不需要自研 UI**：思源的属性视图 = 带类型键、过滤、排序、分组的原生表格，
   而且**一整排 API 都能程序化写**；一行还能装 `assets/x.pdf?page=3&box=<id>` 这种**页+框锚点**。
   我们的「渠道台账」字段（链接/有效性/上次成功/失败原因）**逐列对应一个 key**。
2. **`~/.agents/skills` 是跨工具约定**：思源会把自己的工作空间技能和 `~/.agents/skills` 的外部技能并列管理；
   我们给 DSH 写的 skill，思源**本来就能发现**——技能资产是可迁移的。
3. **AGPL-3.0 是"卖出去"的硬约束**：把思源嵌进交付物会触发 AGPL 义务。
   若要走商业化，思源只能作为**用户自装的宿主**，我们交付 skill / 插件 / 数据（数据本身不是思源的衍生作品）。

### 2. RAGAS：指标很全，但**能当"门禁"的只有确定性那一半**

一手（官方文档 Available Metrics 目录页）：LLM 裁判类含 `Faithfulness`、`Context Precision/Recall`、
`Context Entities Recall`、`Noise Sensitivity`、`Response Relevancy`、`Factual Correctness`、
`Rubrics Based Scoring`、`Aspect Critic`、`Topic Adherence`、`Tool Call Accuracy/F1`、`Agent Goal Accuracy`；
**确定性非 LLM 类**含 `Non-LLM String Similarity`、`BLEU`、`CHRF`、`ROUGE`、`String Presence`、`Exact Match`；
另有 Test Data Generation（RAG testset / KG 构建 / 场景生成）与 Optimizers。

⇒ 对号入座：我们最硬的「**数值/条款级核对**」本质是 **String Presence / Exact Match**（确定性、可复现、**能当门禁**）；
而「三段式取证」更像 `Rubrics Based Scoring` / `Aspect Critic`（**LLM 裁判，不确定，只能当评测不能当硬门禁**）。
所以 RAGAS **不能整体替代**我们的 Golden Set：它是评测工具，不是判定权威。

### 3. 交付链（§四 那几行可以关闭）

`marp-team/marp-cli` 3826★ MIT；`slidevjs/slidev` 48735★ MIT；`scanny/python-pptx` 3535★ MIT。
**报告→PPT 是 MIT 通用件，无需自研。**

### 4. aihse.cn：**静态抓取取不到正文**，但赛道形态看清楚了

- Jina Reader 只返回标题「首页-AI·HSE环健安智慧平台」，正文为空（SPA）；该域可索引内容很弱。
- 用 Exa 搜同主题，头部结果是**赛为安全**（`safewaynt.com`）的方案页，一手读到它的能力构成：
  EHS 知识库（覆盖安全生产规范/隐患排查标准/应急处置流程/典型事故案例）+ AI 问答、**AI 一键生成风险/培训/隐患分析报告**、
  **视频与 AI 识别 → 隐患治理闭环**、心理健康监测、证照 OCR 录入、有限空间作业监测、智能安全带监测；
  并引用《关于深入实施"人工智能+"行动的意见》（国发〔2025〕11号）。
⇒ 这个赛道的能力重心是 **IoT/视频 + 报告生成 + 隐患闭环**（卖的是硬件+管理流程），
**没有条款级引用核对**——对 §三 三件事**没有新增压力**。

### 5. 本轮对结论的影响

- **目标②的"自研台账 UI"可以降级为"接思源属性视图"**（但商业路径受 AGPL 限制，见 §六.1）。
- RAGAS 只借用其**确定性指标**做回归门禁；LLM 裁判类只能当评测面板。
- §三 三件事**继续未被撼动**：本轮依然没有一家做数值/条款级核对、材料评审门、可核验覆盖率。

## 七、边界（诚实）

- 本矩阵里"已实现者"只有 §一 那些**我亲自读过一手材料**的；
  标"待验证"的一律**没读**，不得当成结论引用；
- GBMCP 我只读了它的 README（**没读代码**），其"能下到什么"是**作者自述**；
- Obsidian PDF++ 我读了 README（**没装**），"用着爽"是它的宣示 + 我的判断；
- 工标库/赛为/WPS/北大的能力均为**厂商自述**（工标库、法宝我读过功能页，赛为读的是产品文）。
- §五 里 RAGFlow/Open WebUI/AnythingLLM/Zotero 四条，我读的是**组件与源码的一手文本**（未运行、未装）；
  我说的是「它们**怎么写的**」，不是「它们**跑起来怎样**」。
- `chinese-law-corpus` 我核实的是**存在性与结构**（tree/README/示例 JSON），**没有逐条抽查条文正确性**；
  它的 CC0 自我声明与 GitHub 的 `NOASSERTION` 并存，**法律上未闭合**，商用前需自行确认。
- Zotero 生态的四条能力也全部是 **README/工具表自述**，我没装任何一家、没跑过一个工具。
- §六 的思源部分：我读的是 README / `docs/API*.md` / `docs/SKILL-MANAGER*.md` / 仓库测试断言，
  **没装、没跑、没连过它的 API**；`?page=&box=` 的语义来自仓库里的**测试断言**，未在真实 PDF 上验证。
- §六 的 RAGAS 部分只读了官方文档的**指标目录页**，没读实现、没跑过任何指标；
  「LLM 裁判类 vs 确定性类」是我按指标定义归的类，不是文档里的原文分类。
- aihse.cn 我**没能读到正文**（SPA，Jina 返回空）；该条结论来自同主题搜索命中的赛为页面，
  属**厂商自述**，不能当作 aihse.cn 自身能力的证据。

## 八、独立验证记录（b43）

派了独立验证者去**证伪** §五/§六 的五条头条结论；它自己取一手文本（`gh api tree` + raw）,不用我的转述。

**结论：5 条全部成立，未发现捏造**；1 处数字需正名：

| # | 声明 | 判定 | 关键补强 |
|---|---|---|---|
| 1 | `chinese-law-corpus` 真实且逐条结构化 | 成立 | ⚠ `laws/` 下 .json 实为 **413**（412 部 + `laws/index.json`）。**「412」经独立复算仍正确**：300 部法律（65 具名 + 233 law-hash + civil-code + constitution）+ 112 件 `sfjs-*` 司法解释。`civil-code.json` 真实字段 `id/officialId/title/issuingAuthority/promulgationDate/effectiveDate/status/source/articleCount/sections/articles`，条文号段 `id/articleNumber/displayNumber/path/text/order`；`civil-code-0577` 确为第五百七十七条 |
| 2 | Open WebUI 用 `#:~:text=` 且 page 为 0-based | 成立 | 行号坐实：`CitationModal.svelte:67/90-94` 拼片段、`:73`/`:116` 用 `#page=${page + 1}`；**0-based 找到源头**：`backend/open_webui/retrieval/loaders/main.py:283-284` 的 `'page': page_idx` 配 `enumerate()` |
| 3 | AnythingLLM 的 PDF 只能到文档层 | 成立 | 白名单 14 项**确无 `file://`**；补上最后一环：`collector/processSingleFile/convert/asPDF/index.js:69` 是 `chunkSource: metadata.chunkSource \|\| ""` —— 空串不进白名单 ⇒ 必返回 `nullResponse` |
| 4 | RAGFlow 坐标形状与裁图常量 | 成立 | `pdf_chunk_metadata.py:62-63` 注释原文即该形状；`:150-174` 返回三字段、`:126-147` 可合并多来源（**多段坐标**成立）、`:208` 裁图、`:29-31` 三个常量逐一对应 |
| 5 | Zoteus 引文反查 + MCP token 成本 | 成立 | `zoteus README.md:54` 原句含「anchors the annotation to the lines it occupies, wrapping and hyphenation included, so no page coordinates are needed」；`zotero-mcp README.md:98/102/103` 的 13,448 与 98 三处数字一致 |

基线（均 2026-09-18 取回，`truncated=false`）：`chinese-law-corpus@ce5e48b`、`open-webui@0a7c158`、
`anything-llm@da66855`、`ragflow@302ada2`、`zoteus@e24f97b`、`zotero-mcp@8778e62`。

**最大风险（原文）**：CC0 仅是仓库内 LICENSE/README 的**文件级自我声明**（GitHub `license=NOASSERTION`，
SPDX 未识别），**机器可读的授权保证缺失，下游合规流水线不能据此放行**；
13,448 / 98 tokens 是仓库自报测量值，**未独立复算**；五条结论**绑定 2026-09-18 的 HEAD**，上游一推进即需复检。

验证报告：`var/tmp/VERIFY-b43.md`（临时件，不进库）。

## 九、定向调查：数值/条款核对到底有没有人做（本轮的结论）

问题只问一件事：把**标准条款里的数值**对回你写的结论/报告，有没有人在做、有没有人在卖？

**答案：技术内核不但有人做，还有成熟商业产品；但全部是「预置规则/限值 × 特定对象」的范式，
没有人做「引用驱动」的核对。** 四层证据（均一手读到）：

1. **这个领域有正式名字与分级框架。** 清华林佳瑞团队《建筑工程标准数字化与智能化：现状与未来》（2025-02）
   把标准数字化分 **0–4 级**：1 级 PDF 可检索 / 2 级章节条款结构化 / 3 级条文语义标注 / 4 级融合 BIM 生成机器可解析代码。
   同一团队《建筑工程标准规范智能解译关键技术及应用》自述条文解译准确率 **>95%**、BIM 审查效率提升约 **40 倍**；
   其 **LLM-FuncMapper**（2025-10）定义 **66 个基元函数**，用 LLM 把条文的计算逻辑自动组合成**可执行代码**，
   论文举的例子正是我们的场景：GB 50016—2014「舞台与观众厅之间的隔墙耐火极限不低于 3.00 h」
   → `IF exists(舞台) AND exists(观众厅) AND connected(舞台,观众厅) THEN requires(防火隔墙.耐火极限≤3.00 h)`。
2. **中国消防审图已产业化，且已覆盖「文本」。** 图智 2.0（清华软件学院 + 清大东方，`next.tuzhi.ai`）：
   整套图纸（建筑/电气/给排水/暖通）**加设计说明文件**的消防信息提取与**规范符合性审查**，
   面向预置的 **6 本消防旧规 + 2 本消防新规部分条文**规则库；论文自述已用于幼儿园、学校、住宅的实际图审项目。
3. **美国商业平台是同一条链路。** **UpCodes Plan Review**（2026-06 发布，自述 80 万 AEC 从业者）：
   上传图纸 → 按属地采用的规范分析 → 输出**按严重度分组的问题，每条链接到图纸页与对应规范条款**，
   并自动标出**图纸与规格说明（specifications）不一致**；可筛选/评论/指派/跟踪/导出报告；
   规范库为 **1100 万条地方采用条文、6000+ 部规范**。
4. **LIMS（检测实验室系统）早就在做「数值对回标准限值」，而且是成熟商业功能。**
   以重庆壹博 LIMS 的评价标准管理为例（功能页一手）：标准档案含标准编号/名称/**标准状态（现行/废止）**/
   发布实施日期/**标准文件附件**；用**指标子表单**逐项配置限值；录入实测值后自动匹配限值并判定合格；
   支持**一检多标**（同一参数绑 GB / 欧盟 / 日本三套限值并排比对分别标注符合性）；
   报告提交前校验**结论与限值逻辑一致**（结果 0.3 > 限值 0.2 ⇒ 应判不合格）**不通过则阻止提交**；
   并为满足 **CNAS-CL01:2018 第 7.8.3 条**，记录标准生命周期状态、关联原始 PDF 作证据、判定全程留痕可审计。

| 层次 | 谁在做 | 程度 |
|---|---|---|
| 条文 → 可执行规则（标准数字化） | 清华两个团队、图智、0–4 级分级框架 | 学术热点 + 商用，自述 >95% 解译准确率 |
| 合规检查（对象 = 图纸/BIM） | 图智、UpCodes Plan Review、Solibri 一类 | 成熟商业产品，「问题 → 图纸页 + 规范条款」 |
| 合规检查（对象 = 文本说明） | 图智 2.0 的设计说明审查 | 有，但限于预置的 8 本规范的部分条文 |
| 数值对回限值（对象 = 检测数据） | **LIMS 厂商（一大批）** | **成熟商业功能**：限值表 + 自动判定 + 一检多标 + 逻辑一致性校验 + 现行/废止状态 + 原始 PDF 证据 + 留痕 |
| **数值对回标准原文（对象 = 任意带引用的文档）** | **没找到** | **空白** |

**⇒ 我下调上一轮的判断（在位的诚实更正）**：不是「没人做数值核对」（§三 的措辞过于绝对），
而是**「没人用引用驱动的方式做」**。已有产品都是**人工把规范编译成规则库或限值表**，
因此只能覆盖少数高频规范 × 特定对象类型，成本结构是重资产；
而「从你引用的那一条原文现场取数值再比」这条路，我没找到实施者。

**可直接抄的（本轮最大收获）**：

1. **0–4 级数字化分级**可用来给我们自己定位：我们有 6417 条标准号元数据 + 全文 PDF + 证据链接
   ⇒ 处在 **1 级偏 2 级**（尚无条文级结构）。
2. **66 个基元函数 + 条文→可执行代码**，是「条文规则化」的现成技术路线。
3. **LIMS 的指标子表单 + 判定留痕 + 现行/废止状态 + 原始 PDF 证据**，正是我们台账与取证纪律要的产品形态范本。
4. **UpCodes 的「问题 → 图纸页 + 规范条款 + 导出报告」**交互，是「三段式取证」的商用参照。

**对「卖」的判断（更悲观一点）**：这条赛道已有做得很深的人（LIMS 厂商、审图厂商、UpCodes 这类平台），
他们卖的是「把规范编译成规则库」的重资产。我们要么做**他们的补充**（引用驱动、任意文本、轻量、便宜），
要么就**当个人工具**——本轮**没有**找到「我们已经明显比他们强」的证据。

**边界**：图智、壹博 LIMS、UpCodes 三条均为**厂商功能页/新闻稿自述**，我没有安装、没有实测；
两篇论文的性能指标（>95%、40 倍）是**作者自述**，未独立复算；
「没找到引用驱动的实现」是**检索结论**（Exa + GitHub），不等于「不存在」，只能说明它不在公开可见面上。
