# B 线：文档解析与版面还原

> 抓取日期：2026-10-25（所有 URL 当日可达；论文正文经 `r.jina.ai` 抓 arXiv HTML 版）
> 证据档位：【一手】= 读到官方文档/源码/仓库文件/论文原文（附 URL + 日期）；【转述】= 二手或个人实测帖；【推断】= 我的判断；本文件**无【实测】**——我没有在本机跑过任何一个解析器。
> 元数据（星数/许可证/最后推送/是否归档）统一取自 GitHub API `repos/<owner>/<repo>`，2026-10-25 抓取；PyPI 版本与许可证取自 `pypi.org/pypi/<pkg>/json` 同日抓取。
> **评判尺度**：不是"能不能解析一份 PDF"，是 **10 万+ 份 PDF、百万～千万条款**，且表格/公式/上下标要保结构、要能点回原文。
>
> ⚠ **2026-10-25 Lead 就地更正（原文保留，不删）**：结论 1/2 里**「文档写的是 magic-pdf」成立，「我们在 AGPL 下」不成立**。Lead 同日实测：`pyproject.toml` 的 parser extra 是 **`mineru>=2.0`**；venv 实装 **`mineru 3.4.5`**；`src/core/ingestion/mineru_adapter.py` 主路径走 **`from mineru.cli.common import do_parse`**（第 459 行），`import magic_pdf`（第 319 行）只是**旧名兼容分支**。`magic-pdf 1.3.12`（PyPI 许可证字段 AGPL-3.0）**确实还装在 venv 里**，但不是主路径。
> ⇒ 正确说法三条：① `docs/REQUIREMENTS-v4.3.md` 有三处「magic-pdf `>=0.10.0`」，那是**过时文档**（代码早已换包）；② 我们真正的差距是 **mineru 3.4.5 → 上游 4.0.12**（跨一个大版本）；③ 许可证面**没有紧迫风险**，紧迫的是**版本差带来的能力差**（上下标、`complex_table` 分流、新输出 schema）与**文档失真**。下文结论 2 的"继续留在 magic-pdf 等于继续 AGPL 分发"据此降级为"仅对残留兼容分支成立"。

## 结论先行（≤15 行）

1. **本仓基线已过时两代**：`docs/REQUIREMENTS-v4.3.md` 写"**MinerU (magic-pdf `>=0.10.0`)**"，而上游现在是 **`mineru` 4.0.12**（PyPI，2026-10-11 上传）；`magic-pdf` 这个包名停在 **1.3.12，PyPI 许可证字段 `AGPL-3.0`**【一手，PyPI】。见文末 §对不上的地方 第 1 条。
2. **换名顺带换了许可证（对我们有利）**：当前仓库 `LICENSE.md` 是 **Apache-2.0 + 附加条款**（MAU > 1 亿 或 月营收 > 2000 万美元 须商业许可；对第三方提供在线服务须显著署名 MinerU），不再是 AGPL【一手，LICENSE.md 2026-10-25】。
3. **表格做到"结构级"的只有 4 家**：MinerU、Docling、Paddle、Marker（且 Marker 只在 JSON 里保结构）。其余是"能出文字/能出图"，不是保结构【一手】。
4. MinerU 把"合并单元格"显式化到类型系统里：`table_type` 由 HTML 里有 `colspan`/`rowspan` 或嵌套表数 > 1 判为 `complex_table`，否则 `simple_table`；表格本体是 HTML 字符串【一手，`docs/next/middle-json/structured-content-current.md`】。
5. **Marker 的 Markdown 是 pipe 表**：官方示例输出 58 处 Markdown 表分隔线、0 个 `<table`，合并单元格在 Markdown 路径上丢失；只有 JSON 的 `Table` block 里有完整 HTML【一手，仓库 `data/examples`】。
   - ⚠ **2026-10-25 复核实测更正**：按当前仓库三个官方示例（multicolcnn / switch_trans / thinkpython）实测合计 **28 处**表分隔线（4 / 14 / 10），**不是 58**（58 可能取自更早快照）。**「0 个 `<table`」这个关键事实是对的**，结论「Markdown 落 pipe 表、合并单元格必丢」**不受影响**。
6. **Docling 的 Markdown 序列化器会把嵌套表拍平**（源码注释自述），要结构只能用 HTML 导出或 DoclingDocument JSON【一手，docling-core `serializer/markdown.py`】。
7. Paddle 是唯一**给无框线表格单独训模型**的：表结构识别分 `SLANeXt_wired` / `SLANeXt_wireless` 两套权重【一手，PaddleX `configs/.../SLANeXt_wireless.yaml`】。
8. **上下标**：只有 MinerU 4.0 有显式表达（`superscript`/`subscript` 行内样式，PDF 原生文本按字符几何检测，带单测用真实中文 PDF 做夹具）与 Marker 输出 `<sup>` 标签；其余压平或未取证【一手】。
9. **吞吐三套口径互相打架**（同一批系统，差 4 倍）：MinerU 论文 2.12 页/秒（A100-80G，VLM）；Marker 自测把 MinerU **pipeline** 后端测成 0.54 pg/s（B200，并发态）；docling 社区实测全开只有 0.64 pg/s（L4，189 页）。→ 见 §对不上的地方 第 2 条。
10. 按 100 万页算（10 万份 × 10 页，页数假设是【推断】）：0.54 pg/s ≈ **21 天**；2.12 ≈ **5.5 天**；2.9 ≈ **4 天**；0.09（docling 100 页 1080 s 的个人实测）≈ **129 天**。⇒ 断点续跑是硬需求，不是优化项【推断 + 上面各条出处】。
11. **没有一个项目有中文国标排版处理**（前言/目次/附录/条文说明/强制性条文星号）：18 个项目 0 命中【一手，逐仓库关键词扫描；反向检索见 §反证检索记录】。
12. 表格错误是行业性难题，不是选型能解决的：2026 年 TableParseMap 论文把错误分成 9 类，**合并单元格错误 105 个样本**（结构错误里最多）、公式里**上下标识别错误**单列一类【转述，只读到检索片段，未读全文】。
13. **结论：主干应升级到 MinerU 4.0（许可证反改善），Docling 当第二解析器做交叉校验（MIT 最干净），其余全不抄**。见文末 §对我们。

## 逐个点评

### MinerU（我们现在的解析器，上游已到 4.0）
- 是什么：PDF/Office/图片 → Markdown / HTML / LaTeX / DOCX / EPUB / PDF / Structured Content 九种渲染目标；四个质量档 `flash`/`basic`/`standard`/`advanced`；本地文档库 + 按页/块续读。谁维护：OpenDataLab（上海 AI Lab）/ 许可证：**NOASSERTION**（GitHub API），实际 `LICENSE.md` = Apache-2.0 + 附加条款 / 最后推送：2026-10-23（**82,430★**）【一手，gh api + LICENSE.md】
- **规模 / 吞吐**：官方文档**不给页/秒**，只说"速度与内存取决于 VLM 引擎、输入尺寸、并发"，规划值"至少 16 GB 系统内存 + 8 GB 显存只是起点不是保证"【一手，`docs/en/usage/tiers.md`】。论文口径（OmniDocBench 1,355 页，vLLM 并发、排除启动开销）：**2.12 页/秒 @A100-80G；1.70 @RTX 4090 48G；4.47 @H200-141G；未优化基线 0.95 页/秒**，2337 tokens/s【一手，arXiv 2509.22186 §3.4 Table 3】。
- **精度**（厂商论文，自评，OmniDocBench）：Overall **90.67**、公式 CDM **88.46**、表格 TEDS **88.22**、朗读顺序 0.044；同表里 PP-StructureV3 86.73 / olmOCR-7B 81.79 / MinerU2-pipeline 75.51 / Marker-1.8.2 71.30【一手，arXiv 2509.22186 Table 5】。
- **表格**：block `type=table`，字段 `html="<table>...</table>"`、`table_type`（`simple_table` = HTML 无 `colspan`/`rowspan` 且嵌套 ≤1；`complex_table` = 有跨度或嵌套 >1）、`table_caption`/`table_footnote`、`image_source`（原图裁剪）。MinerU 2.5 起表格识别改为 **OTSL** 中间表示（结构 token 从 28+ 降到 5，序列长度约减半），再转 HTML【一手，论文 §4.2.2 + middle-json 文档】。跨页：LaTeX 渲染明确"合并跨页续段、续列表和续表"，块上有 `continues_prev` 标记【一手，`docs/next/middle-json/rendering.md`】。
- **公式**：block `equation_interline`/`equation_inline`，`math_type: "latex"`，内容是 LaTeX；LaTeX 导出走 `latex2mathml → mathml2omml → OMML` 保可编辑【一手，同文档】。
- **上下标**：`structured_content` 的行内样式枚举里有 `superscript` / `subscript`；PDF 原生文本路径按字符 bbox/原点几何判定上下标，单测 `tests/unittest/test_pdf_native_script_detection.py` 用真实中文 PDF（"中文论文2.pdf"）做夹具【一手，仓库文件】。**但** PDF 文本 span 只有 `text`/`equation_inline`/`phonetic` 三种，上下标是"样式"而非独立 span ⇒ 下游若只读 content list 会拿到平文本，要读样式字段【一手，`structured-content-current.md` §6.1】。
- **扫描件**：`basic` 档是 ONNX 小模型 OCR（CPU 可跑，模型 ~0.8 GB）；`standard`/`advanced` 是 VLM（llama.cpp / vLLM / LMDeploy）。显存规划：basic ONNX ~2 GB RAM；standard PyTorch+llama.cpp ~16 GB RAM / 8 GB+ 显存【一手，README 硬件表】。
- **断点续跑**：本地库缓存 + `doc:{short_id}/tier:{tier}/page:{n}/block:{n}` 稳定定位 + 按页续读；错误码里 `parse_oom` 直接建议"降档、缩小 `--pages` 或经许可走远端"【一手，README】。**官方无"批量任务队列"证据**（未见 worker/队列实现，只有库缓存）→ 批量调度要我们自己写【推断】。
- **中文/国标**：有 CJK 断行与空格处理（LaTeX/PDF 渲染段），**无** GB 标准的目次/前言/附录/条文说明专门处理，**无** 条款/效力概念【一手，关键词扫描 0 命中】。
- **引用可回溯**：有页码 `page_idx`（0 基）、块序号、bbox、`extensions.docvortex_layout`（页宽高 pt + 图像旋转）【一手，`output_files.md`】——这是它对我们最有价值的部分。
- **对我们**：见文末 §对我们 第 1、2 条。

### Docling（IBM）
- 是什么：文档 → DoclingDocument（统一文档模型），再导出 md/html/json 等；解析、版面、阅读顺序、表格结构、公式、图片分类、图表转表；有 OCR 与 VLM 两条管线（Granite-Docling 258M）。谁维护：IBM Research（`docling-project`）/ 许可证：**MIT**（代码；模型各自许可）/ 最后推送：2026-10-23（**69,528★**）【一手，gh api】
- **表格**：DoclingDocument 的 `TableItem` 带结构标注，docling-core 里 `row_span`/`col_span` 是显式字段；HTML 序列化器保留跨度。**但** Markdown 序列化器自述"嵌套表在 `RichTableCell` 里被拍平（flattened）"⇒ Markdown 路径丢嵌套结构【一手，docling-core `serializer/markdown.py` 注释 + `types/doc/items/table/table_data.py`】。
- **公式**：`do_formula_enrichment`（**默认关闭**，额外模型）→ CodeFormula 模型输出 LaTeX；HTML 导出用 MathML 渲染【一手，`docs/usage/enrichments.md`】。
- **上下标**：docling-core 的序列化基类/LaTeX 序列化器里出现 `superscript`/`subscript`（61 处命中）⇒ 模型里有这个概念；Markdown 输出是否保留**未取证**【一手，gh 代码检索 / 未逐行核】。
- **吞吐**：官方文档**不给数字**。社区实测：① issue #2120：100 页扫描件（OCR + 表结构）**1080 秒 ≈ 0.09 页/秒**；② discussion #3442（docling 2.93.0 / L4 24G / 189 页）：OCR 关+VLM 关 **3.3 pg/s**、只开 OCR **1.5**、只开 VLM **0.83**、全开 **0.64**；**batch size 4→256 对吞吐零影响**，GPU 平均利用率 24–29%（峰值 100% 是脉冲）⇒ 瓶颈是流水线阶段，不是 batch【转述，GitHub issue/discussion，2025-08 / 2026-05】。
- **中文/国标**：无【一手】。**分布式**：有 `docling-serve`（异步 API + workers）与 docling-jobkit 路线，官方 FAQ 也指到这个方向【转述，同 discussion/issue 答复】。
- **对我们**：MIT 是全场最干净的许可证 ⇒ 适合当**第二解析器**（交叉校验表格/公式），但别指望它扛 10 万份吞吐（见上 0.09～3.3 pg/s 的现实分布）。

### Marker（Datalab）
- 是什么：PDF → markdown / JSON / chunks / HTML；两种模式 `balanced`（GPU，surya VLM 做版面+OCR+表格）与 `fast`（CPU，rf-detr 版面 + pdftext 抽文本层）。谁维护：Datalab（`datalab-to`）/ 许可证：**代码 Apache-2.0，模型权重是改版 OpenRAIL-M**（研究/个人/营收或融资 < 500 万美元免费，超出须付费）/ 最后推送：2026-10-22（**40,627★**）【一手，README + LICENSE】
- **规模 / 吞吐**（厂商自测，olmocr-bench 1,403 份 PDF，单台 **B200**，**并发稳态**）：balanced **76.0 分 @2.9 pg/s**（有效延迟 341 ms/页）、fast **66.6 @7.4 pg/s**、fast 无 OCR（纯 CPU，20M 版面模型）**43.6 @23.7 pg/s**；同一张表里 MinerU-pipeline 72.7 @**0.54 pg/s**、docling 50.3 @2.1 pg/s【一手，README「Benchmarks」】。
- **表格**：默认从 PDF 文本层重建，扫描件/低置信回退 VLM；**跨页表格合并只在 `--use_llm` 时做**（README 明说 LLM 用来 "merge tables across pages"）【一手】。输出格式：Markdown = **pipe 表**（官方示例 58 处表分隔线、0 个 `<table`）；JSON 的 `Table` block 有完整 HTML（`<table><tbody><tr><th>`，含 `<br/>`）【一手，仓库示例数据】。
- **公式**：balanced 用 VLM OCR 行内/行间公式（arXiv math 83.9）；fast 只从文本层读（23.4）；无 OCR 模式 **0.0**（数学直接为零）【一手，README 分类表】。
- **上下标**：输出保留 `<sup>` 标签（示例里 10 处），代码 `marker/schema/text/span.py`、`marker/providers/pdf.py` 有 subscript 处理【一手】。
- **中文/国标**：无。**引用可回溯**：JSON 有 page/block id 与 bbox；Markdown 里有 `<span id="page-N-M">` 锚点【一手，示例】。
- **对我们**：**不抄**。三条：① 模型权重 OpenRAIL-M 有收入门槛，我们是商业闭源分发；② Markdown 落 pipe 表，合并单元格必丢（我们的国标表格大量跨行跨列）；③ 它速度优势建立在"读文本层 + 选择性 OCR"，对**扫描版国标**（政策文本常见）优势消失。

### PP-StructureV3（飞桨 PaddleOCR 3.x）
- 是什么：版面分析 → 版面检测 → 表格识别 → OCR → 公式识别 → 图表解析 → 阅读顺序的流水线；输出 JSON / Markdown / Word / LaTeX。谁维护：百度 PaddlePaddle / 许可证：**Apache-2.0** / 最后推送：2026-09-16（**91,629★**；星数是本清单最高）【一手，gh api + README】
- **表格**：结构识别有 `SLANeXt_wired`（有线）与 **`SLANeXt_wireless`（无框线）两套权重**，是唯一明着给无框线表专门建模型的项目；版面检测模型分 20/23 类（含"表格标题/表注/印章/公式编号"这类细类）；README 宣称"支持跨页表格自动合并与标题层级识别"【一手，PaddleX `configs/modules/table_structure_recognition/SLANeXt_wireless.yaml` + README】
- **精度**（厂商自报）：PaddleOCR-VL-1.6（0.9B）宣称 OmniDocBench v1.6 **96.3%**；PP-StructureV3 宣称 **94.5%**；"0.13 s on A100 GPU"（**口径未写明：单页还是单图、含不含全部子模型**）【一手，README】。第三方口径：MinerU 论文测 PP-StructureV3 OmniDocBench Overall **86.73** / 表 TEDS 81.68 / 公式 CDM 85.79【一手，arXiv 2509.22186 Table 5】；olmOCR-Bench 上 PaddleOCR-VL **80.0±1.0**（MinerU 2.5.4 75.2、Marker 1.10.1 76.1）【一手，olmOCR README】。
- **公式 / 上下标**：公式识别是独立子线（LaTeX）；上下标有无专门处理**未取证**（未读到证据）。
- **中文**：默认中英双语识别模型，中文场景是它的主场；**但无** GB 排版/条款/效力处理【一手】。
- **对我们**：**依赖不抄（PaddlePaddle 生态重、Windows 打包麻烦），思路要借**：① 有线/无线两套表结构模型 ⇒ 我们该按"有框线/无框线/扫描件"分流解析档，而不是一套档跑全部；② 版面类别里已有"表格标题/表注/公式编号"，这正好对上国标的"表 1/注："结构【推断】。

### olmOCR（AllenAI）
- 是什么：把 PDF "线性化"成干净 Markdown 的工具包（7B VLM，`olmOCR-2-7B-1025-FP8`）；顺带开源了 **olmOCR-Bench**（1,400 份文档 / 7,000+ 测试用例，含表格、公式、多栏、老扫描件）。谁维护：Allen Institute for AI / 许可证：Apache-2.0 / 最后推送：2026-03-25（**19,804★**，7 个月未推送）【一手，gh api + README】
- **吞吐/成本**：README 宣称"**<$200 美元/百万页**"（按 GPU 租用折算的厂商口径，硬件与并发未写明）；本地推理最低 **12 GB 显存**（RTX 4090 / L40S / A100 / H100 测过）【一手，README】
- **表格/公式**：bench 把 Tables、ArXiv math 单列；输出是 Markdown（公式/表格都塞进 Markdown）。结构保真程度：**未取证**（未读它的输出实现）。榜单上它自己的 OSS 模型 7B 在 OmniDocBench 被 MinerU 论文测成 81.79、表 TEDS 68.92（**明显低于 MinerU 的 88.22**）【一手，arXiv 2509.22186 Table 5】。
- **对我们**：**不抄**。它是"训练数据线性化"取向（要的是可读文本，不是可还原结构），表 TEDS 68.92 说明结构不是它的强项；但 **它的 bench 是全领域目前最中立的第三方表**（Marker/MinerU/Paddle/Mistral/Chandra 都在上面被独立跑过），选型时应优先引用它，而不是各家自评。

### Unstructured
- 是什么：文档 → "元素"（Title / NarrativeText / Table / ListItem…），`partition_pdf` 有 fast / hi_res（版面模型）/ ocr_only / vlm 四种策略。谁维护：Unstructured.io / 许可证：Apache-2.0 / 最后推送：2026-10-24（**15,617★**）【一手，gh api + README】
- **表格（厂商自曝的弱项）**：README 用自家 benchmark 对比 OSS 版与商业 Transform API：**OSS 表格单元格内容准确率 0.426**、单元格空间准确率 0.498、文本准确率 0.715（Transform 分别是 0.866 / 0.853 / 0.878）——这是厂商自己放出来的数字，**OSS 版表格只有四成单元格对**【一手，README「NOTE」块；OSS 数据源 unstructured.io/benchmarks 1,000+ 页】。
- **公式 / 上下标**：无专用模型，README 关键词扫描 `formula|LaTeX` **0 命中** ⇒ 不处理【一手，扫描】。
- **吞吐**：无任何数字【一手，README 无】。**对我们**：**不适用**。它的抽象是"元素流"，正好丢我们要的表格跨度与坐标；表格数字已由厂商自己否掉。
- 附注（安全面）：OSS 版**默认上报匿名遥测**（库加载 + 每次 partition 调用，内容/路径/文件名不上报；`DO_NOT_TRACK` / `SCARF_NO_ANALYTICS` 可关）【一手，README】——若引入必须关掉，我们承诺数据不出本地。

### PDF-Extract-Kit（OpenDataLab）
- 是什么：解析模型集合（DocLayout-YOLO / YOLOv8 公式检测 / UniMERNet 公式识别 / PaddleOCR / TableMaster、StructEqTable 表格转 LaTeX/HTML/Markdown），**MinerU 1.x–2.x 的模型上游**。许可证：**AGPL-3.0** / 最后推送：**2025-01-03**（近 21 个月未推送，10,054★）【一手，gh api + README】
- **对我们**：**不抄**。三条：AGPL-3.0；已停更；我们要的能力在它的下游 `mineru` 里已经是维护中的版本。

### Nougat（Meta）
- 是什么：学术 PDF → `.mmd`（Mathpix Markdown 兼容，公式 LaTeX）。许可证：MIT / 最后推送：**2025-02-21**（10,089★）【一手，gh api + README】
- **对我们**：**不适用**。它只为 arXiv 论文训练；表格只出 LaTeX 表环境；无中文/无版面坐标/无续跑；已一年多无提交。

### Chunkr（Lumina）
- 是什么：版面分析 + OCR + **语义分块**的自托管服务，输出结构化 HTML & Markdown，带 bbox；AGPL-3.0 开源版与云版**不同**（README 明写）。最后推送：2026-09-09（4,149★）【一手，gh api + README】
- **对我们**：**不抄代码**（AGPL-3.0，闭源分发即触发）。唯一值得看的是"分块是产品一级公民"这个取向——它和我们的条款切分同题，但我们已有更细的条款口径【推断】。

### Zerox（OmniAI）
- 是什么：把每页渲染成图交给视觉模型（OpenAI/Anthropic/Gemini/Bedrock/Azure…）直接抄成 Markdown，默认并发 10 页。许可证：MIT / 最后推送：**2025-05-20**（17 个月未推送，12,249★）【一手，gh api + README】
- **对我们**：**不适用**。每页一次外部 VLM 调用 ⇒ 100 万页的成本与"数据不出本地"两条都过不去；且它是"抄文字"，不产结构。

### MarkItDown（微软，超出任务书但同类常被推荐）
- 是什么：任意格式 → Markdown 的转换器（191,995★，MIT，最后推送 2026-10-23）【一手，gh api】
- **对我们**：**不适用**。它的目标是"给 LLM 读得懂的文本"，不做版面/表格结构，也不产坐标。

### 商业 1：Mistral OCR
- 技术路径（**今天只读到参数与返回结构**）：`mistral-ocr-latest`；表格输出由 `table_format` 控制，取值 **`null`（表内联进 Markdown）/ `markdown`（表单独出 Markdown）/ `html`（表单独出 HTML）**；返回文本 + 图像 bbox + 文档结构元数据；表格格式化与页眉页脚抽取**需 OCR 2512 或更新**，块级抽取需 **OCR 4 或更新**（版本门控是硬约束）【一手，docs.mistral.ai，2026-10-25】
- **吞吐/价格**：**未取证**（页面只抓到参数页）。**对我们**：**不适用的理由是数据面**——法规/国标 PDF 外发到第三方 API 不可协商（业主约束"数据全在本机"）；技术上学它的"表格格式可选"这个参数设计即可【推断】。

### 商业 2：Reducto
- 技术路径：`r-1` 单次全页模型（文本/表格/图/版面/定位一体）+ 专门模型 + agentic 增强；部署形态含 SaaS / 混合 VPC / 全 VPC / **air-gapped 本地**；宣传点是"面向 RAG 的版面感知分块"【一手，docs.reducto.ai 概览页，2026-10-25】。**吞吐/准确率/价格：未取证**（未读 benchmark 与定价页）。**对我们**：本地化部署形态是唯一可能谈的选项，但闭源且要谈合同 ⇒ **本轮不进入候选**，留作"将来若要买"的对照。

### 商业 3：LlamaParse
- 技术路径：托管解析服务，按模式（preset/mode）出 Markdown/JSON，官方文档把 Tables 单列一节。**本轮只抓到文档站导航**（表格/模式/输出三节标题），正文与数字**未取证**【一手到"存在该文档页"为止】。**对我们**：数据外发 + 按页计费 ⇒ **不适用**；待核清单里保留"它的表格模式怎么描述结构"这一条，仅供对照措辞。

### 商业 4/5/6：Mathpix、Azure Document Intelligence、Google Document AI
- **本轮未抓取任何官方页**（时间预算全给了上面 6 个开源项目与交叉校验）。因此：技术路径、表格/公式/上下标输出载体、吞吐、价格、区域合规**全部未取证**，只登记在 §待核清单。
- 已确定的两条判断（【推断】，不依赖它们的具体实现）：① 三者都是**数据出本地**的云 API（Azure/Google 可谈区域部署，Mathpix 只有云）⇒ 与"国标/法规原件不外发"冲突；② 按页计费 × 百万页 ⇒ 成本量级另说，先被 ① 否掉。

## 对不上的地方（来源互相矛盾处，单列，不抹平）

| # | 谁在说 | 说 A | 说 B | 我的处理 |
|---|---|---|---|---|
| 1 | 本仓 `REQUIREMENTS-v4.3.md` vs 上游 | "**MinerU (magic-pdf `>=0.10.0`)**"，依赖包名 `magic-pdf` | 上游包名已是 `mineru`（PyPI 4.0.12，2026-10-11）；`magic-pdf` 停在 1.3.12 且许可证字段 AGPL-3.0 | **以 PyPI + 仓库为准**：我们锁的是**旧包名的旧代号**，不是"MinerU 当前版本"。这不是版本号差一位，是**换了产品**（CLI/API/输出 schema 全变，见 `docs/en/reference/migration_4.md`） |
| 2 | MinerU 论文 vs Marker vs docling 社区 | MinerU：**2.12 页/秒**（A100，VLM 档，OmniDocBench 1,355 页，排除 vLLM 启动） | Marker：MinerU **pipeline 后端 0.54 pg/s**（B200，并发）；docling 全开 **0.64 pg/s**（L4，189 页） | **不是同一个东西**：档位不同（VLM vs pipeline）、硬件不同、并发口径不同。对外只能引用"同档同机"的对照；跨来源比较必须写明档位。**任何单一"页/秒"数字都不足以做选型依据** |
| 3 | Marker 自测 vs MinerU 自测（同一批系统） | Marker 表：Marker balanced 76.0 > MinerU-pipeline 72.7 > docling 50.3 | MinerU 表：MinerU2.5 90.67 > dots.ocr 88.41 > PP-Structure 86.73 > Marker-1.8.2 71.30 | 两套 benchmark 不同（olmocr-bench vs OmniDocBench），**排序不可互推**。两家都在自评自选指标，只能"看趋势、不看排序" |
| 4 | Marker 的"结构" | README 说 formats tables / forms / equations | 官方示例 Markdown **0 个 `<table`、58 处 pipe 表**；HTML 只在 JSON 里 | **以产出样例为准**：Markdown 路径不保合并单元格。"支持表格"与"保表格结构"是两件事（本仓吃过这个亏，记下来） |
| 5 | Docling 的"效率" | 技术报告摘要自称 "runs efficiently on commodity hardware in a small resource budget" | 社区实测 100 页 1080 秒（0.09 页/秒）；L4 上全开 0.64 pg/s、GPU 利用率 24–29% | **以实测为准**：它的效率优势在"轻量 CPU 小模型、无 OCR/无 VLM"时成立，一开表结构+OCR 就掉到页/秒 1 以下 |
| 6 | MinerU 的许可证 | 多份二手资料（含 2025 年的工具说明）写"MinerU 是 AGPL-3.0" | 当前仓库 `LICENSE.md` = Apache-2.0 + 附加条款；`magic-pdf` 的 PyPI 许可证字段仍是 AGPL-3.0 | **两者都对，指的不是同一个东西**：AGPL 属于 `magic-pdf` 那个旧包名/旧代号；我们若继续用 `magic-pdf` 就仍在 AGPL 下。**升级即等于换许可证**（见 §对我们） |
| 7 | MinerU 4.0 的表格格式 | README 说九种渲染目标 | 实际每个入口只暴露子集（`mineru parse` 只出 Markdown；`mineru-kit parse` 出 markdown/middle_json/zip；V1 API 才有 structured_content） | **以入口能力表为准**（`output_files.md` 开头那张表）：渲染器能力 ≠ 命令选项 |
| 8 | Paddle 的精度 | README：PP-StructureV3 **94.5%**、PaddleOCR-VL **96.3%**（OmniDocBench） | 第三方：PP-StructureV3 OmniDocBench **86.73**；olmOCR-Bench 上 PaddleOCR-VL **80.0** | 口径不同（OmniDocBench 版本 v1.5/v1.6 不同、评测子集不同）。**自报数字一律减档使用**；"0.13 s on A100"连口径都没写，不采用 |
| 9 | Unstructured 的表格 | 营销层常被列进"支持表格抽取" | 厂商 README 自曝：OSS 版表格单元格内容准确率 **0.426** | **以厂商自曝为准**：这一项的争论可以结束 |
| 10 | "MinerU 2.5 之后是 2.5 Pro / 4.0" | 任务书按"MinerU 2.x"布置 | README 顶部标题是 **MinerU 4.0**，badge 里有 2.5、2.5 Pro 两篇技术报告 | **以仓库现状为准**：2.x 已是上一代；本报告的 MinerU 结论分两栏写（2.5 论文数字 / 4.0 代码与文档事实），不混用 |

## 待核清单（我没读到的）

1. **Mathpix / Azure Document Intelligence / Google Document AI / LlamaParse 的官方页一个都没抓**。它们的表格/公式/上下标输出载体、吞吐、限流、价格、数据驻留条款全部未取证。
2. **MinerU 4.0 的批量调度**：只确认了"库缓存 + 按页续读 + `parse_oom` 错误码"，**没有**多进程/队列/任务持久化的实现证据；10 万份要不要自己写调度器，未定。
3. **MinerU 4.0 的实测吞吐**：论文数字是 2.5 的（2025-09），4.0 改成 DocVortex + 四档后**没有官方页/秒**；我们自己的机器上跑一遍才有我们的数字（本轮没跑，无【实测】）。
4. **Docling 的 Markdown 是否保留上下标**：只确认模型里有 `superscript`，序列化器是否输出未逐行核。
5. **PP-StructureV3 的 Markdown 里表格是 HTML 还是 pipe**：只确认它有 `HtmlMixin`/`MarkdownWriter` 两条通道，具体落到 Markdown 文件的形态未读到样例。
6. **olmOCR 的表格/公式在 Markdown 里的具体标记**（是否 `<math>`/`<table>`）未读实现。
7. **各项目的"断点续跑"**：只有 MinerU 有明确机制证据；Marker 有 worker 并发与 `SURFACE_INFERENCE_URL` 外部推理服务，但任务级恢复未取证；Docling 靠 docling-serve/jobkit，细节未读；其余无。
8. **中文国标的专门处理**：结论"18 个项目 0 命中"来自 README/docs 关键词扫描（`GB/T|国标|条文说明|目次|强制性`），**不等于**代码里绝对没有——但没有任何一家在文档里宣称做过，这一条足够支撑"没有可抄的"。
9. **TableParseMap 论文（arXiv 2608.09842）只读到检索片段**，没读全文；"合并单元格错误 105 样本"这个数字来自片段里的表，未复核全文口径。

## 反证检索记录（搜了什么词、搜出什么）

- 搜「**MinerU 国标 标准 PDF 前言 目次 条文 解析 不好**」→ **没有**任何项目/文章讨论国标特有版式（目次、条文说明、强制性条文星号）的解析处理；返回的是通用 PDF 解析对比。⇒ 支撑结论 11「没有可抄的中文国标处理」。
- 搜「**MinerU table recognition failure 复现失败 表格 高估 问题**」→ 得到三类硬反证：① 2026 年 TableParseMap 论文（arXiv 2608.09842）把表格解析错误分成 9 类，**合并单元格错误 105 个样本**是结构错误里最多的，公式错误 154 个样本里明确包含"上下标识别错"；② MinerU Discussion #4621：中文账单表格里"单号与两行日期重叠"，**docker 默认 pipeline 后端解析失败、改用 VLM 后端才成功**，且调 `sorted_ocr_boxes` 阈值无效（代码里 hardcode 0.4）；③ 中文技术博客（腾讯云开发者社区，【转述】）：120 页财报 PDF 峰值内存 4.2 GB，低 DPI 扫描件在 flash 档识别率掉到 67%。⇒ 支撑结论 12，且说明**我们换档（pipeline/VLM）比换工具更关键**。
- 搜「**docling slow performance limitations large scale PDF batch criticism**」→ 得到 docling 的两条实测反证（issue #2120 的 1080 秒/100 页；discussion #3442 的 L4 上 0.64–3.3 pg/s + "batch size 零影响 + GPU 24–29%"）。**"docling 快"这个通行印象在开 OCR/表结构后不成立。**
- 代码级反证（比文章硬）：`gh api search/code` 逐仓库查 `superscript`/`subscript`/`row_span`/`<table`，据此判定"谁真的在代码里有这个概念、谁只是 README 说了"；并用官方示例输出（marker 的 `data/examples`）反向核对 README 的措辞。
- 许可证反证（推翻三条通行说法）：MinerU 现行 `LICENSE.md` 不是 AGPL；Marker 的**模型权重**不是 Apache（OpenRAIL-M + 500 万美元门槛）；Unstructured 的 OSS 表格精度由厂商自己写成 0.426。
- **没做的事（如实记）**：没有跑任何一个解析器（无【实测】）；没有做中文评测站（CSDN/知乎）的独立评测检索（按任务书不能当一手）；没有读 Mathpix/Azure/Google/LlamaParse 的任何官网页。

---

## 对我们（结论落点：改哪儿、抄哪一段、代价、明确不抄）

> ⚠ **2026-10-25 增量补充（用 `research-protocol` 工具矩阵的下载量口径做的，详见 `85-incremental-skill-tools.md` §一）**：
> PyPI 月下载实测（`pypistats.org`，2026-10-25）：**docling 2,909,751 / unstructured 2,462,836 / marker-pdf 116,251 / mineru 109,382 / magic-pdf 14,341**。
> ⇒ ① 「magic-pdf 是旧包名」**加强为**「依赖已基本没人用」（1.4 万 vs mineru 10.9 万，差 7.6 倍）；
> ② 「Docling 当第二解析器」**加强**——它的生态采用度是 MinerU 的 **26.6 倍**，遇到问题有地方查，正好补 MinerU issue 区冷清的短板；
> ③ 但**下载量 ≠ 能力验证**：docling 的 290 万里有大量"顺手装的"。**主结论不变**：合并单元格/上下标/LaTeX 仍是 MinerU 唯一做全的。

### 0. 必须立刻登记的事实冲突（先于任何方案）

本仓 `docs/REQUIREMENTS-v4.3.md` 两处把解析器写成 **"MinerU (magic-pdf `>=0.10.0`)"**、依赖表写 `magic-pdf >=0.10.0`、并把"magic-pdf 版本对齐"列为 v4.3 的修复项。上游事实：包名是 **`mineru`**（PyPI 4.0.12，2026-10-11），`magic-pdf` 停在 1.3.12 且 `license` 字段是 **AGPL-3.0**；4.0 的 CLI 已换成 `mineru parse` / `mineru-kit parse`，旧 `mineru -p`、`mineru-gradio`、`-m all` 全部改名（`docs/en/reference/migration_4.md`）。⇒ "我们用的是 MinerU"这句话现在指两个不同的产品，文档、打包脚本、验收口径都要跟着改。

### 1. 主干：把 `magic-pdf` 换成 `mineru 4.0`（建议）

- **为什么是它**：表格（HTML + `simple_table`/`complex_table` 的合并单元格判据）、公式（`math_type=latex`）、上下标（`superscript`/`subscript` 样式 + PDF 原生几何检测）、页/块稳定定位（`doc:{id}/tier:{tier}/page:{n}/block:{n}`）、库缓存续跑——**我们需要的五项它全有，且都在同一套 schema 里**，不用东拼西凑。
- **抄哪一段（文件级，可直接依赖）**：`mineru-kit parse --format middle_json` 产出的 **MiddleJson（`schema: docvortex.middle`, 2.0）**，以及 `structured_content()`；我们在 Parser Worker 里只消费这两个，不再碰旧 `PymuDocDataset`。
- **代价**：① 接口全换，我们现有的 MinerU Worker 解析代码要重写（工作量按"一个模块重写+回归"计，不是改参数）；② 运行时 Python ≥3.10、<3.15，模型下载约 2–3 GB，`standard`/`advanced` 要 8 GB+ 显存、16 GB 内存（`basic` 可纯 CPU）；③ **许可证变体要看懂**：Apache-2.0 + 附加条款，触发条件是 MAU > 1 亿 或 月营收 > 2000 万美元，以及对第三方提供在线服务须显著署名——**对"本地单机分发"的我们不触发商业授权**，但"在线服务署名"这一条要在打包的分发说明里留位置；④ 4.0 是 2026 年的大改（DocVortex），**升级后头一轮要按"新解析器"验收，不是按"版本升级"验收**。
- **反向风险（必须写进方案）**：4.0 的吞吐没有官方页/秒数字，2.5 论文的 2.12 页/秒不能直接搬到 4.0 上；升级前应在我们的机器上跑 100 份国标做基线（本轮没跑，无实测）。

### 2. 结构化落库：抄 MinerU 的三个"做法"，不抄实现

- ① **`complex_table` 判据**（有 `colspan`/`rowspan` 或嵌套表 > 1 ⇒ complex）：我们入库时就该按这个分流——`simple_table` 进"表格结构化行"，`complex_table` 只存原图 + bbox + caption（今天我们没有这个分流，一律 Markdown，等于把合并单元格的错静默吞掉）【推断，依据见结论 4】。
- ② **页/块 locator 语法**：`doc:{id}/tier:{tier}/page:{n}/block:{n}` 与我们"点引用徽章 → 红色箭头跳到 PDF 对应页"的现有交互是同一件事，直接照抄这个字符串格式，省掉自己发明 ID 体系。
- ③ **结构化错误码**（`parse_oom` 等）：批量跑 10 万份时，"单份失败原因可枚举"比"日志里翻异常"重要；`parse_oom` 直接给出"降档 / 缩小 `--pages` / 走远端"三条处置，正好是我们要的三态。

### 3. Docling 当第二解析器（可选，成本最低的一步）

- MIT 许可证，是全场唯一"抄代码不心虚"的。建议**不是换主干**，而是**交叉校验**：同一批国标，双跑 MinerU 与 Docling，**只比表格单元格数与跨页表识别结果**，差异大的文档转人工。它的 `TableData`（`row_span`/`col_span` + cell bbox）字段设计可以直接抄进我们的 SQLite 表格表结构。
- **代价**：多一套依赖（torch + 表结构模型 + 可选 OCR 模型），磁盘与安装体积上升；**别指望它扛吞吐**（社区实测全开 0.64 pg/s，见 §对不上的地方 第 5 条），只在小批量校验里用。

### 4. 明确不抄（逐条给理由，避免下一轮重新讨论）

| 项目 | 不抄的理由 |
|---|---|
| Marker | 模型权重 OpenRAIL-M，营收/融资 > 500 万美元即需付费（我们闭源分发）；Markdown 落 pipe 表，合并单元格必丢 |
| PP-StructureV3 | Apache-2.0 可抄，但 PaddlePaddle 依赖重、Windows 打包成本高，且能力与 MinerU 重叠；**只借"有线/无线两套表结构模型"这个思路**，用来设计我们的"有框线/无框线/扫描件"分流 |
| PDF-Extract-Kit | AGPL-3.0 + 近 21 个月未推送 + 是 MinerU 的上游，能力已在下游获得 |
| Chunkr | AGPL-3.0（开源版与云版还不同），一行代码都不能进闭源分发 |
| Nougat / Zerox | 都是 2025 年停更（17–21 个月无提交）；Nougat 只认学术论文，Zerox 每页一次外部 VLM 调用（成本 + 数据外发两否） |
| Unstructured | 厂商自曝 OSS 表格单元格准确率 0.426；无公式/上下标；默认上报遥测（需关） |
| MarkItDown | 定位是"转成 LLM 读得懂的文本"，不产结构、不产坐标 |
| olmOCR | 结构不是它的强项（表 TEDS 68.92 vs MinerU 88.22）；但**它的 bench 是唯一中立第三方表**，选型引用它 |
| 商业 API（Mistral OCR / Reducto / LlamaParse / Mathpix / Azure DI / Google Document AI） | 法规与国标原件**外发不可协商**（业主约束：数据全在本机）；其中 Mistral OCR 的 `table_format: null/markdown/html` 参数设计值得学，其余仅留作"将来若买"的对照 |

### 5. 吞吐与规模：给业主的一句话口径

按 10 万份 × 10 页 ≈ **100 万页**（页数是【推断】，未统计我们真实语料的平均页数）：单机单卡按 0.54～2.12 页/秒 = **21 天～5.5 天**连续跑；按 docling 全开那种 0.09 页/秒 = **129 天**。⇒ 结论：**"解析一次"在这个量级上是按周计的一次性大工程**，方案里必须有"分批 + 断点续跑 + 失败可枚举 + 可换档重跑"，缺一个都会变成"跑到第 6 天崩了、从零开始"。
