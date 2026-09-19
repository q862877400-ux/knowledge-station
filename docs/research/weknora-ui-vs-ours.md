# 我们 vs WeKnora：知识库管理 UI 差距清单（**只诊断，不改代码**）

**这份文件干什么**：业主原话"我现在看着知识库管理界面还是很丑"。这份清单把"丑"落到**能施工的动作**上：
逐页并排对照 → 最丑的 5 处（现象/根因/改法）→ 别乱改的地方 → 截图判不了的 → 优先级表。

**方法与边界**（先说清，免得把结论用错）：

| 项 | 说明 |
|---|---|
| 参照（真像素） | `D:\AI\WeKnora\docs\images\` 下 30+ 张官方截图（MIT，**只看不搬**）。我逐张看过的：`knowledgebases.png`、`kb-document-list.png`、`answer.png`、`config.png`、`kb-chunk-edit.png`、`knowledges.png`、`settings.png`、`qa.png`、`skill-catalog.png` |
| 参照（数值） | 他们的**源码级尺度**已在本仓读过并落盘：[weknora-kb-ui/02-components-and-visual-language.md](weknora-kb-ui/02-components-and-visual-language.md)（下表凡写"他们=NNpx"都出自那里，附 `文件:行`） |
| 我们（真像素） | `var/tmp/ui-shots/` 的**离屏渲染**截图：`rowh-520.png` / `rowh-1300.png`（最新，5d 修 `box-sizing` 之后）、`5c-kb-520-batch-after.png`（批量条）、`5c-ingest-520-after.png`、`5c-capabilities-900-after.png`、`corr3-dark-520.png` / `corr3-dark-1300.png`（深色）。**同目录的 `*.json` 是量出来的几何真值**（`ui-render-shot.mjs` 的 `measured`） |
| 我们的值 | 都指到代码：`plugin/client/ksGuideStyles.ts`、`KsKnowledgePage.tsx`、`KsCapabilityPage.tsx`、`KsIngestPanel.tsx` |
| ⚠ **不算我们缺陷的** | 离屏渲染**没有宿主外壳**（侧栏/tab 条/宿主字体栈）⇒ 不许把"没有侧栏/没有顶部 tab 条"当我们的锅 |
| ⚠ **不抄的** | 品牌绿 `#07c05f`、多租户/空间切换（[NOT-DOING](../NOT-DOING.md) 第 4 条 + [UI-BASELINE](../UI-BASELINE.md) 的边界） |

---

## 一、逐页并排对比（6 组）

### A. 知识库/文档列表的**类型层级**（他们两张列表页 ↔ 我们同两页）

| 语义 | 他们（出处） | 我们（出处/量值） | 差距（可见） | 可改动作 |
|---|---|---|---|---|
| 页面主标题 | **24px/32px** w600（`KnowledgeBaseList.vue:1600`） | **20px/26px** w600（`ksGuideStyles.ts:93`，量到 `fs=20px lh=26px`） | 差 4px。**但**我们在 ~520px 的宿主侧栏里，24px 偏大 ⇒ **这条只登记不改** | 维持 20px（写进本节，防下一轮有人"照抄 24"） |
| 页副标题 | **14px/20px**，placeholder 色（`:1643`） | 12px/1.5 tertiary（`:94`，量到 `fs=12px`） | 差 2px；与主标题的比例他们是 14/24=.58、我们是 12/20=.60 —— **比例对，绝对档偏小** | `ksGuideStyles.ts:94` → `font-size:var(--ks-fs-base)`（13px）。窄列里 14px 会跟正文一样大 |
| **卡片标题** | **15px/22px** w600 + `letter-spacing:.01em`（`resource-card.less:87-101`） | **13px**（`KsKnowledgePage.tsx:473` 与 `:574` 是行内 `style={{fontSize:13}}`；`KsCapabilityPage.tsx:253` 是 `var(--ks-fs-base)`=13px） | **卡标题 == 正文 == 13px，只靠字重分**。**这是全清单最根本的一条**（详见第二节 #2） | 新增 `.ks-kb-ct{font-size:var(--ks-fs-md);font-weight:600;letter-spacing:.01em}`，把三处 13px 换成它 |
| 卡片描述 | 12px/17px，`line-clamp:2`，secondary（`:172-182`） | `.ks-kb-hint` 12px/1.5 **tertiary**（`:99`） | 字号一致 ✓；差在**颜色更淡**（tertiary vs secondary）且**没有 2 行截断**（描述长了卡就长高） | `ksGuideStyles.ts:99` 加 `-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical`；颜色改 `--dsw-alias-label-secondary` |
| 卡片底部计数/徽标 | **11px**，高 **22px**、`min-width:22px`、`padding:0 5px`、圆角 **5px**（`:207-231`） | `.ks-kb-hint` 12px 纯文字（`KsKnowledgePage.tsx:475`） | 我们的"3 篇"与描述**同字号同颜色**，不读作元数据；他们是一个 22px 高的盒子 | 复用已有 `.ks-kb-badge`（`:121-125`，11px + 圆角）包"3 篇" |
| 分组/区块小标题 | 13px/20px w600 secondary（`:1917`） | `.ks-kb-sec` 12px tertiary（`:109`） | "我建的（真文件夹；与上面两棵平级）"这行 12px 灰字里**塞了括号说明**，读起来像注释不像标题 | `:109` → 13px + `--dsw-alias-label-secondary`；括号说明挪进 `title=` |

### B. 列表**容器与行**（`kb-document-list.png` ↔ `rowh-1300.png` / `rowh-520.png`）

我在 `kb-document-list.png` 看到的：面包屑 → 一行筛选条（搜索 + 4 个下拉 + 起止日期 + 视图切换 + 一个图标按钮）→ **卡片网格**（3 张并列，每张：✓图标 + 标题 + `…` + 2 行描述 + 一条分隔线 + 时间戳 + `MD` 类型徽标）→ 底部右下角**悬浮批量条**（`已选 3 项 取消选择 | 🔁重建知识 🏷批量打标签 📁移动到目录 🗑批量删除`，删除是红字）→ 左上是他们的外壳侧栏（不算我们的锅）。

| 维度 | 他们 | 我们 | 差距 | 可改动作 |
|---|---|---|---|---|
| 行高 | `min-height:60px`、`padding:0 16px`、表头 40px（`DocumentListView.vue:566`、`:525`、`:540`） | 量到 **44px**、`padding:4px 8px`、`.ks-lhead` **33px**（`rowh-520.json` / `rowh-1300.json`） | 他们行疏一半。**但窄面板用 44 是刻意的**（UI-BASELINE 第二节）⇒ **不改行高**，改的是行内 8px 侧内边距（他们 16px） | `.ks-item`（`ksGuideStyles.ts:138`）`padding: var(--ks-space-1) var(--ks-space-2)` → `... var(--ks-space-3)`（12px） |
| 行的**列结构** | 8 列表格（`:589-602` 单元格 `padding:0 8px`）—— 宽度被列填满 | 一行只有 3 个字段（名字 / 标签 / 两个按钮）。图上（`rowh-1300.png`）名字到 ~470px、标签簇 ~545–665px、`＋标签` ~925px、`详情` ~1010px ⇒ **标签到按钮之间 ~260px 没有内容** | 42% 行宽是"无主空档"，看起来像没排完版 | `.ks-item-tags{margin-left:auto}`（`ksGuideStyles.ts:168`）把标签簇并到操作列，空档变成一个连续的左段；或给行加真列（标准号/发布日期/来源）——**P2** |
| ⚠ 量值自相矛盾 | — | 同一份 `rowh-1300.json` 里 `.ks-item#rows.tagsLeft=234`，而 `.ks-item-tags.x=462` | **工具的两个数不一致**（图上看到的是 ~545） | **先重新量再动手**；这条不许当"已知布局"用 |
| 列表容器 | 卡片网格 + 每张卡有描边/阴影（见 C） | 4 行裸行，无容器、无表头底色、无斑马 | 列表像散落而不是一个列表 | 给 `.ks-main` 的行组加一个 `.ks-list` 容器（.5px 描边 + 圆角 10 + 白底）——**P1** |
| 表头/筛选 | 40px 表头容器 + 一整套筛选条 | `.ks-lhead` 33px，只有全选 + 计数；**页内无搜索**（业主定的） | 不算缺陷（搜索是明确不做） | 不改功能；只把 `.ks-lhead` 高度对齐 `--ks-head-h`（40px，token 已有）——P2 |

### C. **卡片形态**（`knowledgebases.png` / `knowledges.png` ↔ `rowh-520.png` 的 6 张卡）

我在 `knowledgebases.png` 看到：3 张卡（`test` / `图片测试` / `wizard`），每张**大留白**、右上角有**淡色渐变晕染**+`…`、标题下方"无描述"、**一条细横线**、线下左是**彩色类型胶囊**（`问答 (4)` 蓝 / `文档 (54)` 绿）、右是灰时间戳。在 `knowledges.png` 看到：文档卡有 4 行描述 + 底部一行（时间戳 左 / `DOC|DOCX|PDF` 徽标 右），卡与卡**贴得很近**（gap 很小），卡底是极浅灰、有 1px 描边。

| 维度 | 他们（值出自 02 那份的核心清单） | 我们（`ksGuideStyles.ts:105-107`） | 差距 | 可改动作 |
|---|---|---|---|---|
| 内边距 | KB 卡 `padding:12px 14px`（`resource-card.less:25`）；文档卡 `10px 14px 8px` + 底条 `32px/0 14px` | 量到 `pad=8px 12px` | 竖少 4px、横少 2px；卡显得挤 | `:105` → `padding: var(--ks-space-3)`（12px；**不引入 14px**，那是非网格值） |
| 描边 + 阴影 | `1px solid component-stroke` + `0 1px 3px rgba(0,0,0,.04)`（`:26`、`:29`） | **只有 `.5px solid border-l2`，无阴影**，且底色 `bg-base` 与页面同色 | 我们的卡在 520 图上就是**一层淡描边**，"是不是卡片"要靠猜 | `:105` 加 `box-shadow: var(--dsw-elevation-soft)`（宿主 token，别写字面 rgba） |
| 卡内**分区分隔** | 卡底与内容之间 **0.5px** 实线（`:190`） | **没有** —— 标题/描述/"3 篇"直接叠着 | 卡里三块信息糊成一段 | 加 `.ks-kb-foot{margin-top:var(--ks-space-2);padding-top:var(--ks-space-2);border-top:var(--ks-sep) solid var(--dsw-alias-border-l2)}` 包"3 篇" |
| 卡片高度 | 固定 `height:136px`（`:23-24`） | token `--ks-card-h:136px` **定义了却从未被消费**（全仓只有 `ksGuideStyles.ts:64` 一处，`client.js:32231` 是同一处的产物） | 结果同列 6 张卡**高矮不一**：量到首张（标准树卡）**212px**，而 `rowh-520.png` 里「公司制度」2 行描述 ≈115px、「内部操作规程」1 行 ≈85px | 二选一：① 真用上 `--ks-card-h`（但树卡内容 6 行会溢出）；② **删掉这个死 token**，改用 `align-items:stretch` 让同列卡等高 —— **推荐 ②** |
| 悬停 | 描边→品牌色、阴影 `0 4px 12px`、背景渐变 4%→8%（`:529`） | `.ks-kb-card:hover{border-color: border-l4}`（`:107`） | 有 hover ✓，弱 | 不追品牌色；加 `transition:box-shadow var(--ks-dur-fast)` + hover 换 elevation —— P2 |

### D. **设置/配置的表单语言**（`config.png` + `settings.png` ↔ `5c-ingest-520-after.png`）

我在 `config.png` 看到：左侧「配置导航」白卡（选中项是**绿色实心胶囊**）→ 右侧内容分**区**，每区有"左侧竖条 + 图标 + 彩色标题（16px）"，字段按 **label 左 / 控件右** 成组放在**同一个描边盒**里（`Base URL` + `API Key` 共用一个盒子），错误/前置条件是一条**带图标的黄色单行条**，校验通过是字段右侧一个**绿勾**。
我在 `settings.png` 看到：section 标题 24px 粗体 + 15px 灰副标题 → 每一行：**18px 半粗 label + 15px 灰说明**，控件在右侧（下拉 455px 宽），行与行之间是 1px 浅线，**行距极大（约 125px 高）**。

| 维度 | 他们 | 我们（`KsIngestPanel.tsx`） | 差距 | 可改动作 |
|---|---|---|---|---|
| 表单分区 | 每个功能区是一个描边盒 + 一条 16px 彩色小标题 | 平铺：没有分区盒、没有区标题层级（`.ks-ing-h` 13px / `.ks-ing-sub` 12px） | 整页读下来是**一条长清单**，不是"几个设置区" | 用已有的 `.ks-ing-card`（`:269`）把"目录 / 抽样 / 结果 / 全量预览"各自成盒并加区标题 |
| label 对齐 | label 左列（设置页 ~200px）、控件右列对齐 | 目录/抽样用 `.ks-ing-row` 行内平铺（`KsIngestPanel.tsx:365`、`:398`），**没有 label 列** | 控件左边缘不齐 | 复用 `.ks-knob-label{flex:0 0 118px}`（`:227`）的模式给这两行；或统一到 96/118 一档 |
| 黄色警告 | `config.png` 里是**单行**带图标条 | 我们的等价物是页首 `.ks-kb-banner`：量到 520 下 **92px 高（4–5 行）**、1300 下 **56px**（`rowh-520.json` / `rowh-1300.json`），而页标题只有 **26px** | **警告块的视觉权重 = 标题的 2.2–3.5 倍**，且占页面首位 | 见第二节 #1 |
| 字号档数 | 24 / 15 / 14 / 13 / 12 / 11（6 档，`:287-302`） | 全页 58 处 className 只用 `ks-ing-note`(12px) / `ks-ing-sub`(12px) / `ks-ing-h`(13px) ⇒ **实际只有 2 档** | 长句 + 小字 + 无层级 = "一堵字墙" | 给 `.ks-ing-h` 升到 `--ks-fs-md`(14px)；把 `:342-347` 那条 4 行总述拆成"一行结论 + `title=` 里的细则" |

### E. **能力卡 ↔ 技能卡**（`skill-catalog.png` ↔ `5c-capabilities-900-after.png`）

我在 `skill-catalog.png` 看到：一个居中弹窗（圆角 12、右上 `×`）里 **2 列等宽卡**，每张卡 = **图标 + 16px 标题**（同一行）、右上角一个书签按钮、2 行 13px 灰描述、左下角一个灰胶囊（`已安装到 E2B_DEMO ⌄`）；第 4 格是**虚线"＋ 添加技能"空位卡**，把网格补满。

| 维度 | 他们 | 我们 | 差距 | 可改动作 |
|---|---|---|---|---|
| 卡头 | 图标 + 标题同一行；操作（书签）在右上 | 只有 13px 粗体名 + 右上 `.ks-kb-hint`/`Tag`「N 个旋钮」（`KsCapabilityPage.tsx:252-255`） | 无图标；"旋钮数"放在卡头右侧，与"设置"动作分家 | 卡头加图标位（宿主 ui-primitives 有 `FileTypeIcon`/状态点可借）；"N 个旋钮"改放卡底（见下） |
| 内边距 | 卡约 16px（`skill-catalog.png` 目测） | 量到 `pad=8px 12px`、首张 `284×124`、`radius=10`、列内 gap 4（`5c-capabilities-900-after.json`） | 竖向内边距只有一半 | `ksGuideStyles.ts:218-219` → `padding: var(--ks-space-3)` |
| 卡内 CTA | 灰胶囊（下拉），**不是按钮** | 一张**通栏 `设置…` 按钮**（`:271`），占掉卡底一整行 | 一页 8 张卡 = 8 个通栏按钮，视觉上很吵 | 保持可点卡（`role=button`）+ 用 `Tag`/胶囊做"旋钮数"，按钮降级为 ghost —— P1 |
| 网格 | 固定 2 列，空位用**虚线"＋"卡**补满 | `repeat(auto-fill,minmax(230px,1fr))`（`:339`）⇒ 900px 下 3 列；分组 4/3/1 ⇒ **「文件导入」「材料评审」各自孤零零占 1/3 宽**，右边 2/3 空 | 每次分组都剩孤行卡；一页两个 widow | ① 末组补一张虚线"＋"空位卡（照 `skill-catalog.png` 第 4 格）；② 或把断点定成固定 2 列 —— P1 |
| 引擎状态 | — | `.ks-cap-engine` 11px（`:222`，量到 `fs=11px`）放在描述与按钮之间 | 11px 是"辅助"档，位置在卡中部，读起来像第二段描述 | 与"旋钮数"合并到卡底一行 —— P2 |

### F. **空态 / 加载态**（他们的 `EmptyState.vue` ↔ 我们的 `.ks-empty`）

| 维度 | 他们（02 那份 §4.1，`:395`、`:299`） | 我们（`ksGuideStyles.ts:209`） | 差距 | 可改动作 |
|---|---|---|---|---|
| 空态 | 图标 30px 装在 **64px 圆**里 + 15px/22px w600 标题 + 13px/20px 描述（`max-width:360px`）+ **可选主按钮**（"暂无知识库"→ 有「新建知识库」） | `.ks-empty`：`padding:16px 8px` + **12px 居中灰字**，一句话（`KsKnowledgePage.tsx:537-539`） | 我们只有一个居中句子，没有图标、没有标题/描述分层、没有 CTA | 新建 `.ks-empty-card`：64px 圆 + 图标（30px）+ 15px 标题 + 13px 描述 + 主按钮；`.ks-empty` 保留给行内小空态 |
| 加载态 | 骨架/`t-loading`；卡片上是 52px 块的"生成摘要中…"（02 那份 `:442`） | 纯文字：`加载 {detailName} 的报告…`（`KsIngestPanel.tsx:533`） | 无骨架 | 用宿主 `Skeleton`（若有）/自绘 3 行灰块 —— P2 |
| 数据少时的页面 | 3 条数据仍被卡片网格（136px 高）+ 底部批量条撑住 | 量到 `.ks-main` 高 **241px**（1300 下 y=193→434），**下面 476px 全空**，没有任何占位（`rowh-1300.json`） | 一眼"没做完" | 让空态/骨架填进列表区（`.ks-main` 给 `min-height` 或让空态卡占满） —— P1 |

---

## 二、**最丑的 5 处**（按"业主一眼看到就皱眉"排序）

### #1 三页最抢眼的都是那条**橙色横幅**
- **现象**：`rowh-520.png` / `rowh-1300.png` / `5c-capabilities-900-after.png` 三页首位都是同一块橙底长句。量值：`.ks-kb-banner` **520 下 92px 高（496×92）**、**1300 下 56px 高**、**900 下 54px**；而 `.ks-page-title` 只有 **26px** —— **警告块是标题的 2.2–3.5 倍高**，也是全页**唯一的大色块**。
- **根因**：① 取色用了 `state-warn-tertiary` 整块铺底 + `state-warn-label` 文字（`ksGuideStyles.ts:87-89`），语义是"警告"而不是"临时告知"；② 位置在 `ks-page-rule` 之后、所有内容之前（`KsKnowledgePage.tsx:363`）；③ 内容是 4 行 12px 解释性长句（"……你可以直接点着体验。层级名取自 doc_catalog 的权威 CCS 表；将来这页接 GET /api/v1/documents/categories 即可，不必重画分类法。"）—— 把"实现细节"当成首屏正文。
- **改法**：`plugin/client/ksGuideStyles.ts:87-89` 把 `.ks-kb-banner` 降级为**一行灰字**：去掉 `background` 与 `border`、`padding: 0`、`color: var(--dsw-alias-label-tertiary)`；`KsKnowledgePage.tsx:363` 那段的文案缩到 ≤20 字（结论），细则挪进 `title=` 或帮助浮层。参照的等价物是 `config.png` 里那条**单行**带图标的黄条 —— 我们是它的 4 倍高。

### #2 字号层级被碾平：**卡标题 == 正文 == 13px**，描述与计数**同为 12px 同色**
- **现象（像素事实）**：`rowh-520.json` 量到全页只有三档字号 —— `.ks-page-title` **20px**、`#ks-shell`/`.ks-item`/`.ks-item-tags`/`.ks-kb-tn` 全 **13px**、`.ks-kb-banner`/`.ks-item-add` **12px**。代码里卡标题写死在 13px：`KsKnowledgePage.tsx:473`（`style={{fontSize:13}}`）、`:574`（同）、`KsCapabilityPage.tsx:253`（`var(--ks-fs-base)`=13px）。描述与"3 篇"**用的是同一个类**（`:474`/`:475` 都是 `.ks-kb-hint` = 12px tertiary）。⇒ **卡标题与正文差 0px，描述与计数差 0px**。
- **根因**：缺"卡标题"这一档 —— 受限字号表里有 `--ks-fs-md:14px` 和 `--ks-fs-lg:16px`（`ksGuideStyles.ts:49-50`），但列表卡一处都没用；同时 `--ks-card-h:136px`（`:64`）**定义了却从未被消费**（全仓唯一出现处就是定义本身）⇒ 卡片既没有高度约束、也没有标题档，于是"内容多高就多高、字一样大"。
- **改法**：① 新增 `.ks-kb-ct{font-size:var(--ks-fs-md);font-weight:600;letter-spacing:.01em}`（对照他们 15px/22px w600，`resource-card.less:87-101`），把 `KsKnowledgePage.tsx:473`/`:574`/`KsCapabilityPage.tsx:253` 三处的 13px 换掉；② `.ks-kb-hint` 加 2 行截断并改 `--dsw-alias-label-secondary`（`ksGuideStyles.ts:99`）；③ "N 篇 / N 个旋钮"改用已有的 `.ks-kb-badge`（11px、`:121`），并放进 `.ks-kb-foot`（0.5px 上分隔线）；④ **删掉死 token `--ks-card-h`**（`ksGuideStyles.ts:64`）或真的用上它 —— 不要留着"文档说 136、实际 85/115/212"的暗账。

### #3 窄宽下**左轨吃掉 42% 宽度，文件名被截断**
- **现象**：`rowh-520.png` 里文件名叫 `GB 50016-2014 建筑设计防…`。量值（`rowh-520.json`）：行宽 **496**、`.ks-rail` **208px**、`#rows[0].nameW = **192px**`、`nameRight=200`、`tagsLeft=208`。⇒ **左侧目录轨比文件名的可用宽度还宽 16px**；`.ks-main` 只剩 280px（`:131` 的 `flex:1 1 320px` 被 `min-width:280px` 压住），而 `.ks-detail`（232px）在 520 下**换行掉到列表下面**（图上详情卡确实在底部）。
- **根因**：三列弹性（`ksGuideStyles.ts:129-132`：rail `flex:0 1 208px` / main `1 1 320px` / detail `0 1 232px`）在 520px 里必然溢出换行；rail 是**固定档**，只有 main 承担压缩。名字又是**列表里最需要宽度**的字段。
- **改法**：`ksGuideStyles.ts:130` 的 `.ks-rail` 在窄容器下缩到 `min-width:140px;flex:0 1 160px`（加 `@container`/媒体查询或直接用 `flex-basis:clamp(140px,34%,208px)`），把省下的 48–68px 给 `.ks-main`；同时 `.ks-item .ks-check{max-width:40%}`（`:160`）在 520 下提到 `min-width:0` 之外再加 `flex:1 1 auto`，让名字吃满剩余宽度。**别改行高**（44px 是四态量过的真值）。

### #4 卡片是"**描边幽灵**"，同列里三档高度
- **现象**：`rowh-520.png` 左轨 6 张卡只有一层极淡描边（`.5px border-l2`）+ 与页面同色的白底、**没有阴影、没有内部分隔线**；同一列里高度分别是 **212px**（标准树卡，量值 `.ks-kb-card h=212`）、≈115px（公司制度，2 行描述）、≈85px（内部操作规程/供应商资料，1 行）—— **高矮不齐且没有规律**。
- **根因**：`.ks-kb-card`（`ksGuideStyles.ts:105-107`）只有描边，**没有**参照的 `0 1px 3px rgba(0,0,0,.04)` 阴影、没有参照的"内容/页脚之间 0.5px 分隔线"（`resource-card.less:29`、`:190`）、内边距只有 **8/12**（参照 12/14）、也没用上 136px 的固定高度。信息只有三块（名/描述/计数）却**没有任何分隔手段**，于是卡与卡之间看不出边界、卡内三块糊在一起。
- **改法**：`ksGuideStyles.ts:105` 一次改到位 —— `padding: var(--ks-space-3)`（12px）、加 `box-shadow: var(--dsw-elevation-soft)`、卡内加 `.ks-kb-foot`（`.5px` 上分隔线）；`.ks-kb-cards`（`:108`）加 `align-items:stretch` 让同列卡等高。**不要写死 `rgba()`**（宿主 token 才是深浅色自动跟随的根）。

### #5 数据一少，页面就"空掉"；分组一不满，就剩**孤行卡**
- **现象**：`rowh-1300.png` 里 `.ks-main` 高 **241px**、y 从 193 到 434，**下面 476px（占视口 52%）完全是白底**，没有任何空态/骨架/占位；同图 `.ks-detail` 只有 **66px 高**的一小块浮在右上（内容是一句 12px 灰字，换行成 3 行）。`5c-capabilities-900-after.png` 里「文件导入」单独占第 2 行、**「材料评审」单独占最后一行**，右边 2/3（约 600px）全空。批量条（`5c-kb-520-batch-after.png`）是 **4 个无图标文字按钮 + 一行括号说明**，被 `flex-wrap` 挤成**两行（496×68）**，且"批量删除"与其它按钮**同色**（参照是红字+垃圾桶图标）。
- **根因**：① 列表区**没有"数据少"的设计**（`.ks-empty` 只覆盖 0 行，1–5 行时既没有空态也没有最小高度，`ksGuideStyles.ts:209`）；② 能力页网格 `repeat(auto-fill,minmax(230px,1fr))`（`KsCapabilityPage.tsx:339`）没有"补满末行"的手段；③ `.ks-batch`（`:184-189`）把解释性括号文本当作第 5 个 flex 项，并把 4 个动作平权。
- **改法**：① `.ks-empty` 升级为"图标 64px 圆 + 15px 标题 + 13px 描述 + 主按钮"（照他们 `EmptyState.vue`，02 那份 `:299`/`:395`），并让列表行数 <6 时显示它；② `KsCapabilityPage.tsx:339` 的分组末尾补一张虚线"＋"空位卡（照 `skill-catalog.png` 第 4 格）或把断点定成固定 2 列；③ `KsKnowledgePage.tsx:558` 那个 `（都作用在页面状态上…）` 挪进 `title=`，`.ks-batch` 加 `flex-wrap:nowrap`，`批量删除` 挂 `--dsw-alias-state-error-primary`，四个动作补宿主图标。

---

## 三、我们**明显做对、别乱改**的地方

1. **颜色全走宿主 token ⇒ 深浅色自动跟随**。全站取色是 `var(--dsw-alias-*)`（如 `ksGuideStyles.ts:87-89` 的 state-warn 三件套、`:105` 的 border-l2/bg-base），并配了 `ui-token-check.mjs`（"引用了但没定义"）与 `ui-audit.mjs`（写死色值）两条机械口径；`corr3-dark-520.png`/`corr3-dark-1300.png` 是深色实证。**参照反倒是写死的品牌绿 `#07c05f` + TDesign 固定色。** ⇒ 任何"照抄得更像"的改动都**不许**引入字面色值（`ui-audit` 会红）。
2. **尺度系统 + 只减不增的棘轮**。4px 网格间距与受限字号/圆角表在 `ksGuideStyles.ts:46-64`，`smoke-ui-scale.mjs` 是棘轮（离网格字面值 17→0、现场字号 13→0）。⇒ 别为了逐字对齐参照的 `padding:12px 14px`、行高 60 就把 **14px / 60px** 塞回 CSS；窄面板的 44/52 是 **520/1300 × 明/暗四态量出来的真值**（UI-BASELINE 5d 表）。全宽列表真要 60 就**显式加一档**。
3. **`.ks-batch` 用 elevation 阴影、不用"描边 + 阴影"的禁止配对**（`ksGuideStyles.ts:178-189`，注释里写明这是官方硬规则）。⇒ 视觉上它也许"不够明显"，但**改回 `border` 就是违规**，要加权重请换 `--dsw-elevation-prominent`。
4. **行内"永不折字"的正面约束**：`.ks-item` 的 `box-sizing:border-box` + `flex-wrap:nowrap` + `min-width:0`（`:138-139`）与 `.ks-item-btn{flex:none;white-space:nowrap}`（`:171`）是一组，修掉过「详情」竖排折行。**动 #3 的列宽时不要撤掉任何一条。**
5. **卡片网格 gap 12px 已与参照一致**（`.ks-kb-cards` 用 `--ks-card-gap`=12，`:108` vs `resource-card.less:13`）。这条不用动。
6. **0.5px 分隔线口径**（`--ks-sep:.5px`，`:95` 的 `.ks-page-rule` 用 `border-top` 而不是 `height:1px`）—— 1x 屏上等于参照的一半，是对的。

---

## 四、**不能靠这批截图判断**（需另法验证）

| 待验 | 为什么截图判不了 | 建议方法 |
|---|---|---|
| hover / focus-visible / 动效（120/150/200ms） | 离屏渲染只有静态帧 | 真宿主页面里看；或看 `ksGuideStyles.ts:59` 的 duration token 是否真被引用 |
| 键盘可达性 / tab 序 / Esc / 焦点环 | 截图没有焦点态 | 真机键盘走一遍 |
| `.ks-batch` 的 `position:sticky` 钉底 | 离屏是**整页截图**，滚动位置不进产物（UI-BASELINE 已实测 `window.scrollTo` 无效） | **只能在真宿主页里看** |
| 真实数据密度（6000+ 行） | demo 只有 4 篇文档 / 8 张能力卡 / 6 张卡 | 用真库跑一遍（含虚拟滚动与否） |
| 宿主外壳集成（侧栏真宽、tab 条、宿主字体栈与行高） | 离屏渲染**没有外壳** | 真机页面 |
| 深色下 ingest / capabilities / 材料页 | 深色只跑了 kb 页（`corr3-dark-*`） | `--theme dark` 各页补跑 |
| KaTeX 公式渲染 | `--loader:.woff2=empty` 把字体抹了 | 真机页面 |
| ingest 的数据口径 | 数据是手写 `fetch` 桩，不是真引擎返回 | 真引擎返回时再看 |
| 触屏 / `hover:none` 下按钮常驻 | 参照有 `@media (hover:none)` 常驻逻辑，我们的未知 | 移动端/触屏模拟 |
| 行内分布的**列结构** | 同一份 `rowh-1300.json` 里两个量值自相矛盾（`#rows.tagsLeft=234` vs `.ks-item-tags.x=462`；图上看到 ~545） | **重新量**再决定是否加 `margin-left:auto` |
| 我们的设置页（`KsSettingsSection`） | 本次**没有**它自己的离屏截图 ⇒ 与 `settings.png` 的对比**只能给结构差异，不能给像素结论** | 补一次 `--page`（若工具支持）或真机截 |

---

## 五、优先级表

| 级别 | 做什么（一句） | 指向 |
|---|---|---|
| **P0 立刻改** | 橙色横幅降级为一行灰字（去底色/描边，细则进 `title=`） | `ksGuideStyles.ts:87-89`、`KsKnowledgePage.tsx:363`、`KsCapabilityPage.tsx:324` |
| **P0 立刻改** | 立"卡标题"档：新增 `.ks-kb-ct`(14px/600) 替掉三处写死的 13px，描述改 2 行截断 + secondary | `ksGuideStyles.ts:49/99`、`KsKnowledgePage.tsx:473/574`、`KsCapabilityPage.tsx:253` |
| **P0 立刻改** | 卡片补 `padding:12px` + `--dsw-elevation-soft` + 卡底 0.5px 分隔线；同列卡等高 | `ksGuideStyles.ts:105-108` |
| **P1 本轮改** | 窄宽下左轨缩到 140–160px，把宽度还给文件名 | `ksGuideStyles.ts:130`、`:160` |
| **P1 本轮改** | 空态升级为"64px 圆图标 + 15px 标题 + 13px 描述 + 主按钮"，并覆盖"行数很少"的情形 | `ksGuideStyles.ts:209`、`KsKnowledgePage.tsx:537` |
| **P1 本轮改** | 能力页末组补虚线"＋"空位卡（或固定 2 列），消掉孤行卡 | `KsCapabilityPage.tsx:338-339` |
| **P1 本轮改** | 批量条：`nowrap`、括号说明进 `title=`、删除挂 error 色、四动作补图标 | `KsKnowledgePage.tsx:544-559`、`ksGuideStyles.ts:184-190` |
| **P1 本轮改** | 列表行加一层容器（`.5px` 描边 + 圆角 10 + 白底），别再裸行 | `ksGuideStyles.ts:131` + `KsKnowledgePage.tsx:496` |
| **P1 本轮改** | 删掉从未被消费的死 token `--ks-card-h`（或真的用上），消掉"文档 136 / 实际 85–212"的暗账 | `ksGuideStyles.ts:64` |
| **P2 有空再说** | 行内补真列（标准号/发布日期/来源）或 `.ks-item-tags{margin-left:auto}` 收掉 ~260px 空档（**先重新量**） | `ksGuideStyles.ts:168`、`KsKnowledgePage.tsx:496-535` |
| **P2 有空再说** | ingest 表单分区成盒 + label 列对齐 + `.ks-ing-h` 升到 14px | `KsIngestPanel.tsx:365/398`、`ksGuideStyles.ts:269-271` |
| **P2 有空再说** | 能力卡：卡头加图标、"N 个旋钮"移卡底、通栏 `设置…` 按钮降级 | `KsCapabilityPage.tsx:251-271` |
| **P2 有空再说** | 悬停/过渡补 `--ks-dur-fast`；加载态用骨架替代"加载…"文字 | `ksGuideStyles.ts:105-107`、`KsIngestPanel.tsx:533` |
| **P2 有空再说** | `.ks-lhead` 高度对齐 `--ks-head-h`(40px)；`.ks-kb-sec` 升到 13px + secondary | `ksGuideStyles.ts:134`、`:109` |
| **不做（记录在案）** | 页标题 20→24px（窄侧栏里偏大）、品牌绿、多租户/空间切换、页内搜索 | 本文第一节 A + `docs/NOT-DOING.md` 第 4 条 + `docs/UI-BASELINE.md` |

> ⚠ 本文所有"他们 = NNpx"的值都来自本仓已读的源码清单（[weknora-kb-ui/02](weknora-kb-ui/02-components-and-visual-language.md)），截图只作**结构与形态**佐证；
> 本文所有"我们 = NNpx"都是 `var/tmp/ui-shots/*.json` 的 `measured` 或代码行号 —— 两者都没有靠"感觉更现代"下结论。
> ⚠ 边界：本次**只诊断，未改任何代码**；截图是**离屏渲染**（无宿主外壳），`var/` 不入库。
