# UI 视觉基线（照 WeKnora 知识库管理复刻）—— 第 5 步的施工依据

**这份文件干什么**：把"照抄 WeKnora"从口号变成**可施工的规格**：① 参照物清单位置；② 一套**尺度系统**（我
上一轮 UI 难看的根因就是没有它）；③ 逐块映射到我们的页面/组件；④ DSH 宿主已提供、我们该用却没用（或手搓了）
的原语；⑤ **截图自检流程**（业主明确要求：测试要自己截图看，不是"我觉得还行"）。

**决策与边界**（[NOT-DOING](../NOT-DOING.md) 第 4 条）：形态/界面**照抄**；**技术栈不引入**（WeKnora 是
Vue + TDesign，我们是 React + 宿主原生组件 ⇒ **照结构/视觉重写**，MIT ⇒ 逐处记出处并随附声明）；
仍然不抄：多租户/空间切换；入口仍是"问题"不是"知识库列表"。
**产出物只出 Markdown**（[NOT-DOING](../NOT-DOING.md) 第 1 条）。

---

## 一、参照物在哪（读过的原料，别重读）

| 内容 | 位置 |
|---|---|
| 知识库**页面与流程**（新建/上传/内容管理/标签/多选） | [weknora-kb-ui/01-pages-and-flows.md](research/weknora-kb-ui/01-pages-and-flows.md)（667 行，带 `文件:行` 与中文原文） |
| 知识库**组件与视觉语言**（尺度、组件、状态） | [weknora-kb-ui/02-components-and-visual-language.md](research/weknora-kb-ui/02-components-and-visual-language.md)（645 行） |
| **问答/引用/预览/产物** | [weknora-ui/01-chat-and-citations.md](research/weknora-ui/01-chat-and-citations.md)（731 行） |
| **外壳/设置/权限/集成/平台页/i18n** | [weknora-ui/02-shell-and-other-pages.md](research/weknora-ui/02-shell-and-other-pages.md)（1474 行） |
| 他们自带的 **DSH 插件**（同宿主现成写法） | [weknora-ui/03-dsh-plugin-reference.md](research/weknora-ui/03-dsh-plugin-reference.md)（575 行） |
| **抄/改着抄/不抄**逐块结论 | [weknora-ui/00-index-and-proposal.md](research/weknora-ui/00-index-and-proposal.md) |
| **真像素参照**（他们仓库自带的界面截图，我逐张看过） | `D:\AI\WeKnora\docs\images\`：`knowledgebases.png`（列表页）、`kb-document-list.png`（文档列表+批量条）、`answer.png`（回答+引用）、`config.png`（设置分区）、`kb-chunk-edit.png`、`knowledges.png`、`settings.png`、`qa.png`、`artifact*.png` 等共 30+ 张 ⚠ MIT 素材：**只作参照，不搬进我们仓库** |

## 二、尺度系统（**本清单最该照抄的一条**；值不要求逐字相同，但**必须成体系**）

| 维度 | WeKnora 的做法（出处见 02 那份） | 我们落地 |
|---|---|---|
| 间距 | **4px 网格**，4/8/12/16/20/24/32/40 | 定成 `--ks-space-*`，禁止再出现 13px/18px 这种现场拍的数字 |
| 字号 | 10/11/12/13/14/15/16/18/20/24 | 页面标题 20–24、区块标题 16、正文 13–14、辅助 11–12 |
| 圆角 | 4/6/8/10/12/999 | 卡片 8、输入/按钮 4–6、胶囊 999 |
| 动效 | 120/150/200/300ms | hover/展开 120–150、弹窗 200 |
| 分隔线 | **0.5px**（卡片底、悬浮面板描边） | 沿用（DSH 侧已是 .5px） |
| 卡片 | 高 136px、圆角 8、内边距 12/14、网格 gap **12**、阴影 `0 1px 3px rgba(0,0,0,.04)`、hover `0 4px 12px` | 知识库列表卡照做 |
| 列表行 | 行高 **60**、表头 40、左右 padding 16、容器圆角 9 | ⚠ **口径分档（2026-09-20 更正，留痕）**：60/16 是 WeKnora **全宽文档列表**的数。我们这里是**右侧栏的窄列**（~300px），实测用 `44px`（`.ks-item` 36 + padding 4/8 + gap 8）。⇒ 窄面板用 `--ks-row-h-narrow:44px`、**全宽**列表才用 60。**别再把"文档写 60、代码是 44"当暗账** —— 这里写明两档各自适用在哪。（此条是对上一条提交消息里"现在写明"的兑现：那句当时只写了计划，本条才把它做实。）<br>⚠ **第三轮更正（复核 ui5 实测 + 本轮修复，2026-09-20 落地）**：上面"实测用 44px"当时**并不成立** —— `.ks-item` 是 **content-box**，`min-height:44px` 只是**内容盒**下限 ⇒ 复核实测真实行高 **52px**、行节距 **60px**，token/文档说的 44 是**暗账**。已给 `.ks-item` 加 **`box-sizing:border-box`**（让 `min-height` 就是边框盒行高）。**修复后本机实测**（`ui-render-shot.mjs` 的 `measured`）：**520px 与 1300px 两态都是 行高 44px / 节距 52px**（节距 44+8 的容器 gap）——见第六节 **5d** 的实测表。 |
| 品牌色 | 他们的绿 `#07c05f` | **不抄** —— 用 DSH 主题 token（明暗两套自动跟随） |

## 三、逐块映射（WeKnora → 我们）

| WeKnora 块 | 我们的落点 | 具体动作 |
|---|---|---|
| 列表页骨架：大标题 + 一行副标题 + 细分隔线 + 卡片网格 | `KsKnowledgePage`（知识库页） | 页头做成"标题 20/24 + 副标题 12/13 灰 + 0.5px 分隔线"，下面才是内容 |
| 知识库卡片（标题/描述/类型胶囊/时间/右上角淡色晕染） | 我们的"目录树 + 列表"混合 | 先把**卡片形态**用在"自建夹/合集"概览上；列表仍用表格（我们 6000+ 行） |
| 文档列表页：面包屑 → 筛选条（搜索 + 4 下拉 + 日期 + 视图切换）→ 卡片/列表双视图 → 右下角悬浮批量条 | `KsKnowledgePage` 的列表区 + 现有批量条 | 筛选条按"搜索(300ms 防抖) + 标签 + 类型 + 状态 + 来源 + 日期"；**筛选一生效就递归搜子树并在面包屑标「含子目录」**；批量条**固定在底部**（他们绝对定位不跟随滚动，长列表会飘走） |
| 上传：全局拖拽 + 三栏确认弹窗 + 右下角进度浮层（四段堆叠条 + 行级 12 状态 + 批量重试） | `KsIngestPanel` + 宿主侧 `/ks/ingest/*` | **优先做这块**（最显专业）：先做"全局拖拽 + 进度浮层 + 行级状态 + 重试"，三栏确认弹窗可后置 |
| 多选：表头 indeterminate、Shift 范围选、"全选已加载"、筛选变化即清空 | 现有行勾选 | 四条都补；**不做**"跨页全选所有结果"这种假承诺 |
| 标签：集中 `KbTagManageDrawer` + 批量预选交集 | 现有标签 | 集中一个管理抽屉；批量语义按**追加 + 单独"移除标签"**（业主未反对即定案；**不抄他们的"替换"**） |
| 详情抽屉（元数据 + 分块分页） | 现有详情页 | 抽屉形态；内容放**我们的**发布/生效/废止日期 + 条款依据 + 红色定位箭头入口 |
| 空态：插图 + 一句可执行的话 + CTA；骨架屏 | 各列表 | 空态统一；加载用骨架（不用转圈） |
| 命令面板（⌘K、⌘1–9、零结果两出口） | 新增 | 功能页到 13 项了，用它替代"往侧栏堆入口" |
| 设置：弹窗 + `?section=` 即位置 + 表单三件契约 + 控件即提交 | 现有 `KsSettingsSection` | 先抄"分区标题（细竖条 + 图标 + 彩色小标题）+ 字段成组 + 必填星号 + 内联校验绿勾 + 禁用时黄底说明为什么不能改" |
| 危险动作：就地确认 + 写清副作用边界；令牌只显示一次 | 删除/拒绝/停用等 | 全站统一措辞模板 |

## 四、DSH 宿主**已经有了**、我们该用却没用（或手搓了）的原语

一手清单：`deepseek-harness/packages/client/ui-primitives/lib/types/index.d.ts`（**这是权威面**，
不是从 README 猜的）。我们目前只声明并用了 `Button`/`Checkbox`/`Switch`/`Tag`/`Pill`/`Input`/`Menu`/
`Modal`/`IconChevronDownOutline14`（见 `plugin/client/ksHostPrimitives.d.ts`）。
⚠ **更正（复核 2026-09-20 打回）**：这里原写"**8 个**"，漏了 `Switch`
（`ksHostPrimitives.d.ts:138` 声明了它，客户端有 13 处使用）⇒ 实数 **9 个**。

| 宿主导出 | 我们现在的做法（手搓） | 该换成 |
|---|---|---|
| `relativeTime` / `RelativeTime` | 自己写 `describeWhen()`（"3 分钟前"） | 直接用官方（省一份时区/措辞维护） |
| `fileSizeText` | 自己拼 KB/MB | 直接用 |
| `writeClipboard` | 自己 `navigator.clipboard` + 兜底 | 直接用（含失败语义） |
| `StateDot`（含 `StateDotState`） | 渠道台账用文字 + 颜色 | 渠道"体检结论"列改成状态点 |
| `Tooltip` / `HoverCard` | 到处 `title=` 原生提示 | 关键按钮/指标用官方 Tooltip；复杂说明用 HoverCard |
| `RiskConfirmation` | 自己 `window.confirm`（面板里） | 危险动作（删除/拒绝/停用）用它（措辞模板见三） |
| `Toast` | 无（我们只有行内红字） | 写操作结果提示 |
| `FileTypeIcon` / `classifyFileType` / `fileExtension` | 自己判断后缀 | 文件行图标与类型判定 |
| `MarkdownText`（markdown/ 下） | 自己渲染或纯文本 | Markdown 交付物/条款正文的呈现 |
| `DisclosureRow` | 自己写折叠 | 折叠区 |
| ~~`FoldToggle`~~（**更正，复核 2026-09-20**） | — | **不可用**：它**不在**上面那一个权威面里（该包 `exports` 只暴露 `.`，`lib/types/index.d.ts` 与 `lib/index.js` 都没有它）⇒ **不可 import**。原文把"文件里存在的内部符号"当成了"可用的导出"，这句转述**不实**。要折叠就用 `DisclosureRow`。 |
| `ConnectionIndicator` | 无 | 引擎/渠道连通状态（**比文字更省地方**） |
| `useAnchoredPosition` / `useAnchoredMaxHeight` / `useDismissOnOutsidePointer` | 自己算浮层位置 | 下拉/浮层定位（渠道面板的标签浮层等） |
| `JsonTree` / `DiffBlock` / `TerminalBlock` / `ReadBlock` / `SearchBlock` | 自己拼 <pre> | 调试/工具结果类呈现（按需） |

⚠ **纪律**（`ksHostPrimitives.d.ts` 里已写、且真实踩过）：这些名字**写错不会构建失败**（它是 external，
esbuild 不校验命名导出）⇒ 只能靠**运行时**和**读宿主源码**确认；**用之前先读那一个 `.d.ts` 或源码**，
并在 `ksHostPrimitives.d.ts` 里补上我们真正调用的成员（"只声明我们调用的"）。

## 五、截图自检流程（**业主明确要求：自己看图，不是"我觉得还行"**）

1. 改完客户端代码 → `cd plugin; npm run build:client`（产物 `plugin/client.js`，必须与"从源码现构建"逐字节一致，
   冒烟 `smoke-client-entry` 会红着提醒）；
2. 让宿主**重载插件**：宿主侧改动走 HMR；客户端产物变了要**刷新页面**（`http://127.0.0.1:3080`）
   —— 若自动重载不可靠，用我写的脚本触发（见 `scripts/` 下的插件重载脚本，第 5 步会补）；
3. 用浏览器自动化（`browser4-cli` 技能）打开对应页面/面板 → **截图存到 `var/tmp/ui-shots/<日期>-<块名>.png`**；
4. 用 `read_image` **自己看图**，对照第一节的参照截图（`D:\AI\WeKnora\docs\images\*`）逐条核：
   间距/字号/圆角/分隔线/卡片高度/空态/加载态/批量条位置/危险确认措辞；
5. **把截图路径写进本轮记录**（否则等于没验）；发现不对就改，改完重截。
⚠ 边界：`var/` 被 gitignore ⇒ 截图**不入库**；入库的是"哪张图、看的是什么、结论是什么"这句话。

> ⚠ **宿主原语桩 = [`plugin/scripts/lib/ks-primitives-stub.mjs`](../plugin/scripts/lib/ks-primitives-stub.mjs)**
> （2026-10）：冒烟在 Node 里打包客户端代码时，宿主 `@deepseek-ai/dsh-client-ui-primitives` 必须 alias
> 到一份桩；**名单从源码派生**（扫 `plugin/client/**` 的具名导入）⇒ **加一个宿主组件只改源码，不必改任何冒烟**。
> 这是同一根因的**第三次**：① `smoke-settings` 漏 alias ⇒ `Could not resolve`；② `smoke-client-entry`
> 的桩漏 4 个图标；③ `smoke-kb-page-render` 的桩漏 3 个图标 ⇒ `No matching export`、`-Full` 的 smoke 步红。
> 防复发断言放在**最便宜**的 `smoke-settings`（桩的导出集合 ⊇ 源码导入集合，缺谁点名谁）。
> 详细记录（改法/变异验证/实跑证据/边界）见 [开发史 §10.142](DEVELOPMENT-HISTORY.md)。

### ⚠ 2026-09-20 实测的环境事实：**宿主 GUI 对我们的浏览器自动化是 401**
`browser4-cli` 打开 `http://127.0.0.1:3080` 拿到的是一个 133 字节的 401 残页（`scripts[].length === 0`、
`title` 空）；换 `localhost`、补 `Origin`/`Referer`/`Sec-Fetch-*` 头仍 401（`Invoke-WebRequest` 同样 401）。
⇒ **上面第 2/3 步对"未登录的外部浏览器"走不通**（业主自己的浏览器是已授权的，我们不是）。
**替代路径（已跑通，2026-09-20 5c 起**入库**）**：把页面**离屏渲染成自包含 HTML**（jsdom + React，样式内联
`KS_STYLES` + 宿主主题 token + 宿主 ui-primitives 的**真** CSS Modules），再用无头浏览器
`--screenshot` 截图。工具已在 `plugin/scripts/`（**不再只躺在 `var/tmp/`**）：

| 工具 | 干什么 | 确切命令 |
|---|---|---|
| `plugin/scripts/ui-render-shot.mjs` | 离屏渲染 + 无头截图（+ 量几何，回传 JSON） | `node plugin/scripts/ui-render-shot.mjs --page kb --width 520 --out var/tmp/ui-shots/kb-520.png` |
| `plugin/scripts/ui-audit.mjs` | 机械口径审计：写死色值 / 字面 `**` / KS_STYLES 尺度分布 | `node plugin/scripts/ui-audit.mjs` |
| `plugin/scripts/ui-token-check.mjs` | 自包含 HTML 里"引用了但没定义"的 token（颜色静默回退） | `node plugin/scripts/ui-token-check.mjs` |
| `plugin/scripts/smoke-ui-scale.mjs` | 尺度**棘轮**（离网格 spacing / 现场字号只减不增；在冒烟全链里） | `node plugin/scripts/smoke-ui-scale.mjs` |

- `--page kb|ingest|capabilities|materials`；`--width <px>`；`--interact kb-detail,kb-select,kb-filter,kb-filter-empty,kb-empty,kb-empty-folder,kb-tags-view,ingest-batch,cap-dialog`；
  `--theme light|dark`；`--viewport <px>`（固定视口高）；`--harness <DSH 检出>`（或 `$KS_HARNESS_DIR`）。
  ⚠ **第五步 P0 给工具补了两处量测**（都是"原来量不到、只能靠肉眼估"的东西）：
  ① `measured['#cards']`（`lh`=**每张卡逐个高度**、`pad`=逐个宽度）—— 判"同列卡等高"用它，
     原来只量首张；② `measured['.ks-batch#fit']`（`w`=最后一个子元素右缘 − 条子右缘，**正数=溢出**；
     `h`=条子高）—— 判"批量条是不是被挤成两行"用它。
  新增的 `--interact kb-empty`（点一个没有文档的树节点 ⇒ 看空态卡）、`kb-tags-view`（切到标签视图）。
- **它回传几何真值**（JSON：`measured`），所以"间距/字号/行高/死白"是**量出来的**，不是看图猜的。
  5c 就是靠 `.ks-item#rows[].deadGap` 把"标签簇被推到最右、中间空 285~390px"量出来的。
- ⚠ **已知失真**（照旧，别据此下结论）：**没有宿主外壳**（侧栏/tab 条/宿主字体栈）；
  **只有浅色一套**（默认 `body{}`，深色要 `--theme dark` 且宿主实际还有别的主题变量）；
  **KaTeX 字体被抹掉**（`--loader:.woff2=empty`）⇒ 公式渲染不可信；
  **ingest 的数据是手写 `fetch` 桩**（形状照 `api.ts` 类型，不是真引擎返回）⇒ 那页只能判排版/配色；
  **全页截图看不出 `position:sticky`**，且 `--screenshot` 在固定视口下也是"整页截图"、
  **滚动位置不进产物**（5c 实测试过 `window.scrollTo` 后只剩空白）⇒ **批量条位置只能在真宿主页面里看**。
- **入库前修掉的两个真问题**（5c 的记录，供后人核对"搬进来时改了什么"）：
  ① 临时版在 JSDoc 注释里写了 `` `.woff*/.ttf` `` —— 那个 `*/` 提前结束了块注释 ⇒ `node` 直接
     `SyntaxError`（**本次搬入第一次跑就炸**，已改成 `.woff` / `.woff2` / `.ttf`）；
  ② 中间产物原来写在仓内 `var/tmp/.ui-render-work`，改成**系统临时目录**（`os.tmpdir()`），
     并给 `--keep` 加了说明 —— 本仓"代码树零运行产物"。
**这条路径的边界**：它渲的是**我们的组件 + 真样式**，但**没有宿主外壳**（侧栏、tab 条、宿主自己的间距/字体栈），
所以只用来判"我们自己的块"（字号层级/间距/圆角/分隔线/对齐/溢出），**不能**据此判宿主集成效果。

## 六、第 5 步落地记录（**每块都要有这一节的一行**：改了什么 / 截图路径 / 我看到了什么 / 结论）

### 5a 尺度系统 + 页面骨架（2026-09-20）
- **改了什么**：`ksGuideStyles.ts` 立了 `--ks-*` token（4px 网格间距 / 受限字号·圆角·动效表 / 0.5px 分隔线 /
  卡片·列表几何），KB 页 13 处现场数字换成 token；新增 `.ks-page-head/.ks-page-title/.ks-page-sub/.ks-page-rule`
  页面骨架；`KsKnowledgePage.tsx` 把「14px 粗体 + 右侧一排按钮」那一行拆成"标题 + 副标题 + 0.5px 分隔线"，
  tab 行只留 tab 与「＋ 新建」。
- **截图（`var/tmp/ui-shots/`，不入库）**：`2026-09-20-kb-sidebar-520.png`（520px 侧栏宽）、
  `2026-09-20-kb-wide-1300.png`（1300px）、`2026-09-20-kb-sidebar-520-batchbar.png`（批量条可见）、
  `2026-09-20-ingest-520.png`、`2026-09-20-capabilities-900.png`。
  ⚠⚠ **证据指针更正（复核 ui5 2026-09-20）——这 5 张图不是"5a 当时"的状态**：本机实测
  `2026-09-20-kb-sidebar-520.png` 与 5b 的 `2026-09-20-kb5b-520.png` **逐字节相同**
  （SHA256 `1dedbe62ec5d814a83ff63268e59c5267498d2b0a9b86f30c4099ebe2113697b`，均 80268B，
  与 5c 里那个"同输入两次渲染逐字节一致"的 sha 是同一个）⇒ 它们是**5b 修好之后**重截的，
  **不能**当成 5a 当时（溢出还在）的证据。归属如下，别再把指针指向修好之后：
  | 图 | 实际状态 | 能证明什么 |
  |---|---|---|
  | `kb-sidebar-520.png` / `kb-wide-1300.png` / `kb-sidebar-520-batchbar.png` / `ingest-520.png` / `capabilities-900.png` | **5b 之后**（= `kb5b-520.png` 同一份渲染） | 只证明"**今天** kb/ingest/capabilities 三页长这样"，**不是** 5a 当时的样子 |
  | `2026-09-20-kb5b-520.png` / `kb5b-900.png` | 5b（`0fbe6af`） | 竖排「详／情」已消失 |
  ⇒ 5a **当时**的状态只能看下面第 3 条那段**字面记录**（"窄宽下……竖排折行"），**没有**当时状态的截图；
  5a 的"骨架成立 / token 生效"两条（1、2）由**今天的**截图 + 渲染量出的 4 的倍数支撑，仍成立。
- **我（代理）自己看图看到的事实**（逐条，不是"我觉得还行"）：
  1. ✅ 骨架成立：标题 ~20px 粗体 → 12px 灰副标题 → 0.5px 分隔线，层级一眼能分（改前标题与按钮同高）。
  2. ✅ token 生效：卡片内边距、行距、圆角在各处一致，没再出现 7px/9px 那种数字（渲染里量到的是 4 的倍数）。
  3. ❌ **窄宽（520px）下文档行溢出**：徽章组 + 「详情」被挤到第二行，末两行出现「详／情」**竖排折行**
     —— 这是"对齐不齐/挤"那一类难看，必须修（徽章组 `flex:none` + `nowrap`，让**文件名**去截断）。
  4. ~~❌ **卡片宽度不一致**：同一页里「标准/法律法规」两张卡在 520px 下**通栏**（~490px），
     而「我建的」三张卡只有 ~200px（1300px 下又都一样窄）⇒ 两组卡的容器/网格不是一套。~~
     ⚠ **撤回（复核 ui5 2026-09-20 实测不复现）**：复核在 520px 与 1300px 两态、**六张卡上实测全部 208px**
     —— 没有"通栏 ~490px"这回事。上面那句**不成立**，故划掉（原话保留，不悄悄删）。
     ⚠ **本轮我自己复核的量**（`ui-render-shot.mjs` 的 `measured['.ks-kb-card']`）：两态都是
     **n=6 张、首张 w=208px**（我只逐张量了首张，其余五张依复核的"全 208"——**抽样，不是普查**）。
     5b 的"留给 5c ①卡片宽度不一致"因此**失去依据**（见 5b 段与 5c 段的相关条目）。
  5. ⚠ **1300px 下右侧大片留白**：内容没有 max-width，也没有多列网格，宽屏显得没做完。
  6. ⚠ 顶部那条橙色「UI 先行：数据是占位」横幅在页面里**最抢眼**（比标题还显眼）——它是临时告知，
     等接引擎后应降级为一行灰字或去掉。
- **结论**：5a 只做到"有了尺度系统与页面骨架"，**3/4/5 三条留作 5b**（见下）。截图只作"我们自己的块"的证据。


### 5b 行内溢出修复（2026-09-20，承接 5a 第 3 条）
- **改了什么**：`.ks-item` 钉 `nowrap + min-width:0`（文件名去截断，行不许换行）；`.ks-item-tags` 改 `flex:0 1 46%`
  （标签自己内部换行，但不参与挤压按钮）；**新增 `.ks-item-btn{flex:none;white-space:nowrap}`** 并给
  「＋标签」「详情」挂上；顺手把 `.ks-batch`/`.ks-detail` 里还现场拍的数收进 token；`client.js` 重建。
- **截图**：`var/tmp/ui-shots/2026-09-20-kb5b-520.png`（520px）、`2026-09-20-kb5b-900.png`（900px）。
- **我看到的**：四行文档**全部单行** —— 文件名截断成 `GB 50016-2014 建筑设计…` + `现行/消防/重点` 徽章
  + 淡色「＋标签」+ `详情`；**竖排「详／情」消失**，行高一致、左右对齐都回来了。
- **另看的**：`2026-09-20-ingest-520.png`（入库面板）**没查出缺陷**（路径行/文件列表/抽样行/三色分级行/
  全量预览段，层级与对齐成体系）。
- ⚠ **踩坑（第四次）**：CSS 注释里写了反引号 ⇒ 模板字符串被截断 ⇒ `tsc TS1005`。该文件本就有"注释里不许出现
  反引号"的警告，这次是**绕过警告又踩**；已把反引号换成「」，并把"本轮已踩四次"写进那行注释。
- **留给 5c**：① "我建的"卡片与"标准/法律法规"卡在窄宽下宽度不一致（且 1300px 右侧留白）；
  ② 顶部橙色"数据是占位"横幅比标题抢眼（接引擎后降级/去掉）；③ 上传的**进度浮层 + 行级状态 + 批量重试**。
  ⚠ **① 已撤回（复核 ui5 2026-09-20）**：卡片宽度不一致**复核实测不复现**（两态六张卡全 208px，
  见 5a 第 4 条）。1300px 右侧留白那半条仍在（另见 5c 第四条）。

### 5c 待办（来自离屏渲染子代理 2026-09-20 的独立发现；**它同时独立复现了 5b 的修复**）
子代理钉在 `0fbe6af`，同输入两次渲染**逐字节一致**（sha `1dedbe62…`），并确认第一版的「详情竖排」在 `0fbe6af`
已消失 ⇒ 5b 的修复被独立复现。它另给出下列**新发现**（我全部采信为待办，逐条给处置）：

| # | 发现（它的原话要点） | 我的处置 |
|---|---|---|
| 1 | **入库面板整页 0 个 `var(--dsw-*)`/`var(--ks-*)`、21 处硬编码色值、按钮 6px 直角方框**（宿主 Button 是 18px 胶囊）⇒ 与 kb 页"不像同一套" | **5c 第一条**：把 `KsIngestPanel` 的颜色/圆角/间距全量换成宿主 token + `--ks-*`。这正是业主抱怨的"不像一个产品" |
| 2 | **能力页渲染出 4 处字面 `**`**（`**一个功能一张卡**`、`**交互是真的**`、`**不单独开窗**`）——Markdown 粗体标记当纯文本显示了 | **5c 第二条**（真 bug）：改成 `<strong>` 或去掉标记；顺带它的页标题是 inline 14px，而 kb 页走 `.ks-page-title` 20px ⇒ 两页页头**不同级**，统一到页面骨架 |
| 3 | `KS_STYLES` 机械口径：spacing 字面值 **17 处不在 4px 网格**（2/3/5/6/7/9/10/14px），另有 **11.5px 字号 ×2** 不在受限字号表 | **5c 第三条 + 立一条护栏**：把它们收进 token，并加一个**只减不增**的冒烟（"离网格字面值计数"棘轮），否则下次又会漂回去 |
| 4 | 行节距**实测 44px**（`.ks-item` h=36 + padding 4/8 + gap 8），而本文档第二节自己写的是"行高 **60** / 左右 padding **16**" | **改文档 + 给窄面板变体**：60px 是 WeKnora **全宽文档列表**的数；我们这里是 **~300px 的侧栏列**，44px 是刻意的密度选择 ⇒ 在第二节写明"窄面板用 `--ks-row-h-narrow:44px`，全宽列表才用 60"，**不留一处"文档说 60、代码是 44"的暗账**。⚠ **5c 复核更正**：离屏渲染**量到的是节距 60px / 行高 52px**，不是 44 —— `.ks-item` 的 `min-height:44px` 只是**下限**，宿主 `Checkbox` 的行高把它撑过了；见下面 5c 记录的实测表 |
| 5 | kb@1300：`.ks-check{flex:1}` 把标签簇推到最右，doc 名与标签之间空 ~350px；列表区只 205px 高而左轨 705px ⇒ 大片死白、重心偏左 | **5c 第四条**：窄容器里让文件名占据更合理的比例（或给标签簇 `margin-left:auto`+上限），并让左轨/列表的高度关系自然 |
| 6 | 截图方式的假象（**不是** UI 缺陷）：全页截图（窗口高=内容高）看不出 `position:sticky`，批量条于是落在列表末尾 | **5c 更正（我原来写"用视口高固定的截图"是错的）**：无头 `--screenshot` 在固定视口下**仍是整页截图**，`window.scrollTo` 也不进产物（实测只剩空白）⇒ **批量条位置只能在真宿主页面里看**；`--viewport` 只用来判"定高下会不会截断/首屏看到什么" |

### 5c 落地记录（2026-09-20；**照上表逐条闭环，含两条就地更正**）
- **改了什么**（4 个源文件 + 2 个冒烟 + 1 份本文档）：
  ① `plugin/client/KsIngestPanel.tsx` **整页重写取色/取间距**：21 处硬编码色值 → 0，行内样式 → `ks-ing-*`
     类（色全走 `var(--dsw-alias-*)`，三色分级走 `--dsw-alias-state-{success,warn,error}-*`），
     4 个动作按钮换成宿主 `Button`（`primary`/`outline` + `size="sm"` = 28px/**14px 圆角胶囊**）。
     ⚠ 三色分级（可入库/需人工确认/不建议入库）**语义一字未动**，只换了取色方式。
     连带把 `scripts/smoke-client-entry.mjs` 的"主题债务棘轮"基线 `KsIngestPanel.tsx: 22 → 0`。
  ② `plugin/client/KsCapabilityPage.tsx`：4 处字面 `**` → `<strong>`（强调保留），页头换成
     `.ks-page-head/.ks-page-title/.ks-page-sub/.ks-page-rule`（**与知识库页同一套**；副标题是新写的
     一句，否则骨架少一格）。`KsCapabilitiesPage`（复数）**不存在** —— `grep KsCapabilit` 只有单数那个文件。
  ③ `plugin/client/ksGuideStyles.ts`：spacing 离网格 **17 → 0**、现场字号 **13 → 0**；
     新增 `--ks-fs-2xs:10px`（**唯一**不在受限表里的字号，理由写在 token 注释：徽章/树箭头/分子分母专档）；
     `11.5px ×2` **没有**为它开 token，直接收进 `--ks-fs-sm`（理由写在 `SHRINK_LOG`）。
     新增 `plugin/scripts/smoke-ui-scale.mjs`（棘轮）并加进 `smoke-all.mjs` 的 SUITES。
  ④ `plugin/client/KsKnowledgePage.tsx`：顺带修掉 **5 处**同类字面 `**`（真 bug，同一页同一种病）。
     ⚠ **更正（复核 ui5 2026-09-20）**：这一页**没有清干净** —— `ui-audit.mjs` 的 B 段当时仍报
     **2 处**（`KsKnowledgePage.tsx`）；5c 的缺陷清单**漏登记了它们**。第三轮已补：
     两处都在 **JSX 注释块**里（`{/* 左：自带两棵树 + 自建夹（**平级**…） */}` 与
     `{/* Checkbox 的 label **就是文件名**：… */}`）⇒ **不上屏**（不是渲染缺陷），但它们是
     `ui-audit` B 段那个"含 JSX 注释块噪声"的**上界计数**里的一份，留着会让下一位读到"还有 2 处"。
     已把 `**` 改成「」（**只动注释措辞，不改行为**）；`ui-audit.mjs` B 段的 `KsKnowledgePage.tsx` 计数应归 0。
  ⑤ 截图三件套入库到 `plugin/scripts/`：`ui-render-shot.mjs`（+ 量几何）、`ui-audit.mjs`、`ui-token-check.mjs`。
- **截图（`var/tmp/ui-shots/`，不入库）**：`5c-kb-1300-after.png`、`5c-kb-520-after.png`、
  `5c-kb-520-batch-after.png`、`5c-ingest-520-after.png`、`5c-capabilities-900-after.png`。
- **我（代理）自己看图 + 量数看到的事实**：
  1. ✅ **kb@1300**：页标题 20px 粗体 / 副标题 12px 灰 / 0.5px 分隔线层级清楚；黄条里
     `但交互是真的` 是**粗体**（不再是 `**`）；4 行文件名 + `现行/消防/重点` 徽章紧挨着，
     `＋标签`（淡）与 `详情` 在右侧一列；右侧详情卡显示三个日期 + 标签，页面**没有竖排折字**。
  2. ✅ **死白量（JSON 量出来的，不是看着顺眼）**：kb@1300 行宽 820px 下 deadGap
     **348/390/285/309 → 8/8/8/8**；kb@520 行宽 496px 下也是 **8px**。左边轨 705px 高、列表区
     273px 高的关系**没动**（本次只改行内布局，克制）。
  3. ✅ **kb@520**：文件名截断成 `GB 50016-2014 建筑设计防…`，徽章紧跟其后，按钮在行尾；
     三张「我建的」卡片、两棵树、批量条都成体系（批量条 496×68，圆角 10，四按钮 + 一行说明）。
  4. ✅ **ingest@520**：正文灰字 → 目录行（等宽输入 + 「刷新列表」**白胶囊**）→ PDF 清单（名字 + 灰尺寸）
     → 「开始预览」**深色胶囊**（宿主 primary）→ 三色胶囊总账（✅3/⚠️1/❌1）→ 每行文件（✅/⚠️/❌ 图标
     按语义着色）→ 虚线分出的「全量预览（异步，万级可用）」段；**整页没有一个直角方框**。
  5. ✅ **capabilities@900**：页标题 20px + 副标题 + 分隔线（与 kb 页同级）；黄条里两处粗体正常；
     内联卡上的「（旋钮少于 3 个：按约定**不单独开窗**，就地设置）」里"不单独开窗"是粗体、无星号；
     卡片圆角 10 / 内边距 8×12；8 张卡 3+3+2 排布。
- **没做到/留给下一轮**（诚实边界）：
  1. **同一类"字面 `**`"在其他面板还有约 50 处**（`ui-audit.mjs` B 段的机械口径，**含 JSX 注释块的噪声**，
     所以是上界）：`KsMaterialsPanel.tsx` 37、`KsEvidenceTab.tsx` 9、`KsChannelsPanel.tsx` 2、
     `KsSettingsSection.tsx` 2（都在**会上屏的 JSX 文本/template string** 里，如
     `已登记「x」（… 来源层级 **T3=仅线索**）`、`（需复算**不代表已经坏了**。）`）。
     本轮的 (b) 只清了**能力页**，顺手清了**知识库页**；其余属于"同一种病、别处也犯"，
     **未做**（不在本轮任务书范围内）—— 要么下一轮按同一口径清完，要么给 `ui-audit` 的 B 段加棘轮。
     ⚠ **更正（复核 ui5 2026-09-20）**：上面这句"顺手清了知识库页"**不完整** —— `ui-audit` B 段当时
     仍报 `KsKnowledgePage.tsx` **2 处**（都在 **JSX 注释块**里、不上屏）。**第三轮已清**（改成「」），
     见 5c 落地记录 ④ 的更正。⇒ 这张清单当时**漏了 2 处**，不是 0 处。
  2. **行节距实测 60px，而 `--ks-row-h-narrow` 是 44px**（见上表第 4 行的更正）：
     44px 只是 `.ks-item` 的 `min-height`**下限**，宿主 `Checkbox` 的行高把它撑到 52px（节距 60px）。
     ⇒ 文档与代码的"暗账"**换了个地方**（44 是下限、实际 60），本轮只是**量清并写下来**，
     **没有**改行高（改它要动宿主原语的行高，属于重做密度，不是 5c 的范围）。
     ⚠ **第三轮已修（2026-09-20，见 5d）**：根因不是"宿主原语的行高"，而是 **`.ks-item` 是 content-box**
     —— 加 `box-sizing:border-box` 后 `min-height` 就是真实行高，**实测 44px / 节距 52px**。
     所以上面那句"改它要动宿主原语的行高"是**误判**（原话保留）：一行 CSS 就够。
  3. **能力页 900px 下第一组 4 张卡排成 3+1**、末张孤零零一行（`minmax(230px,1fr)` + 12px gap ⇒
     900px 只容得下 3 列）；**未做**（改列宽/断点是布局调整，且有 A/B 两种口味，留给人拍）。
  4. **批量条 `position:sticky` 在本渲染链里验不了**（见上表第 6 行的更正）：`--viewport` 也救不了。
     ⇒ "批量条钉在底部"目前**只有 5a 的一次真机观察**，没有可复现的离线证据。
  5. **换肤/深色**只跑了 `--theme light`（`--theme dark` 没跑）⇒ "颜色跟着 token 走"是**机制上成立** +
     浅色实测，**没有**深色截图证据。


### 5d 复核打回第三轮：**行高 token 与实测对齐**（2026-09-20；A3）
- **被复核打回的事实（ui5）**：`.ks-item` 是 **content-box** ⇒ `min-height:44px` 只是**内容盒**下限，
  加上 padding（`4px 8px`）后**真实行高 52px、行节距 60px**，而文档/token 都写 44 —— **暗账**。
- **改了什么**：给 `.ks-item` 加 **`box-sizing:border-box`**（一行；`plugin/client/ksGuideStyles.ts`），
  让 `min-height` 就是**边框盒**行高（与 token 同口径）。**没有**改 `--ks-row-h-narrow` 的值，
  也**没有**改成"token=52 / pitch=60"那一支 —— 因为改完实测**与设计意图一致**（窄面板 44），
  所以不必走"改文档迁就实测"的备选方案。
- **实测（`ui-render-shot.mjs` 的 `measured`，改后；同一台机器）**：

  | 页面/宽度 | `.ks-item` 行高 | `.ks-item#pitch` 节距 | padding | 结论 |
  |---|---|---|---|---|
  | kb @520（窄面板） | **44px** | **52px** | `4px 8px` | token 44 **兑现**；节距 = 44 + 8（`.ks-main` 的 gap） |
  | kb @1300（全宽） | **44px** | **52px** | `4px 8px` | 同上（全宽列表若要 60，得另配，别靠"撑大"） |
  | **kb @520 · 深色** | **44px** | **52px** | `4px 8px` | **深色与浅色同值**（本轮 corr3 B5 自己量的，见下） |
  | **kb @1300 · 深色** | **44px** | **52px** | `4px 8px` | 同上 |
  | 改前（ui5 复核 / 5c 记录） | 52px | 60px | `4px 8px` | content-box 的暗账 |

- **命令（可复现）**：`node plugin/scripts/ui-render-shot.mjs --page kb --out var/tmp/ui-shots/rowh-520.png --width 520`
  ⇒ 读 stdout JSON 的 `measured[".ks-item"].h` 与 `measured[".ks-item#pitch"].h`（`var/` 不入库）。
  ⚠ **深色那一档要显式加 `--theme dark`**（默认 `light`）：`node plugin/scripts/ui-render-shot.mjs
  --page kb --width 520 --theme dark --out var/tmp/ui-shots/corr3-dark-520.png`。
- **边界（抽样）**：这是 **kb 页两个宽度 × 两套主题（浅/深）** 的实测，不是全站 `.ks-item` 的普查；
  其他用到 `.ks-item` 的列表未逐页量。
- ⚠ **披露更正（复核 `verify-freeze-corr3` B5，2026-09-20）**：上面这条边界原写"只量 kb **两态**（抽样）"，
  **没写"深色未量"** —— 而当时那两态其实**全是浅色**（表格第 3/4 行是本轮补的）。复核替它补量深色
  （@520/@1300 也是 **44/52**），本轮**自己又量了一遍**（上表最后两行，同一台机器、同一条命令 + `--theme dark`），
  结论一致 ⇒ 现已把"**深色已量**（同样 44/52）"写进表里。**深色下截图**也在 `var/tmp/ui-shots/`
  （`corr3-dark-520.png` / `corr3-dark-1300.png`，不入库）。


### 5e 第 5 步 UI 的第一批 P0 修复（2026-09-20；依据 [weknora-ui-vs-ours](research/weknora-ui-vs-ours.md)）

**改了什么**（`plugin/client/` 三个源文件 + 两个脚本 + 本文档；可搜原文见括号）

| # | 动作 | 落点（可搜原文） |
|---|---|---|
| P0-1 | 橙色横幅降级为**一行灰字 + ⓘ 图标**（去底色/去描边/padding 收 0/走 `label-tertiary`），细则进 `title=`（诚实告知**一字未删**） | `ksGuideStyles.ts` 的「诚实告知条（**降级版**）」；`KsKnowledgePage.tsx` 的 `title={\`交互是真的：` 与 `UI 先行，后端未接`；`KsCapabilityPage.tsx` 的 `UI 先行：旋钮是占位，后端未接` |
| P0-2 | 立**卡标题档** `.ks-kb-ct`(14px/600/ls .01em/单行省略) 替掉 3 处写死 13px；描述独立成 `.ks-kb-cd`(12px secondary + 2 行截断)；计数改 `.ks-kb-badge` 徽章；卡底 `.ks-kb-foot`(0.5px 上分隔线)；**死 token `--ks-card-h` 真的用起来**（`.ks-kb-cards>*{min-height:var(--ks-card-h)}`） | `ksGuideStyles.ts` 的「卡片标题档（P0-2」/「卡片页脚」；`KsKnowledgePage.tsx` 的 `ks-kb-ct`（4 处）；`KsCapabilityPage.tsx` 的 `ks-kb-ct` |
| P0-3 | 卡片 `padding` → **12px**（网格值）、`border:0` + `box-shadow:var(--dsw-elevation-soft)`（**宿主 elevation 档**，描边由阴影里的 `--dsw-elevation-stroke` 画、颜色重绑成 `border-l2`）；hover 提一档描边色 + `--dsw-elevation-panel` | `ksGuideStyles.ts` 的「卡片（P0-3」与 `.ks-cap-card` 同段 |
| P0-4 | 文件名上限 `max-width` **40% → 46%**（**不是**改左轨：见下面的"被实测推翻"） | `ksGuideStyles.ts` 的「P0-4（2026-09-20）：上限 40% → 46%」 |
| P0-5 | 空态升级为 `.ks-empty-card`（64px 圆 + 28px 图标 + 16px 标题 + 13px 描述 + 主按钮）；能力页每组补一张**虚线「＋ 添加能力」**补位卡（`grid-column:auto / -1`）；批量条：括号说明进 `title=`、删除挂 `.ks-danger`(state-error)、三个动作补宿主图标 | `ksGuideStyles.ts` 的「空态卡（P0-5」/「补位卡（P0-5」/`.ks-batch .ks-danger`；`KsKnowledgePage.tsx` 的 `ks-empty-card` 与 `import { ... IconTrashOutline16`；`KsCapabilityPage.tsx` 的 `ks-cap-card-add` |

**改前 → 改后（`ui-render-shot.mjs` 的 `measured`，同一台机器，不是看图估的）**

| 量什么 | 改前 | 改后 |
|---|---|---|
| `.ks-kb-banner` 高 @520 / @1300 / @900 | **92 / 56 / 54px** | **18 / 18 / 18px**（页标题 26px ⇒ 权重从 3.5 倍降到 0.69 倍） |
| 卡片内边距 / 逐张高度 | `8px 12px`；6 张 = **212 / (树) / 115 / 85 / 85 / 66** | `12px`；**224 / 192 / 136 / 136 / 136 / 72**（"我建的"三张**全是 136**，不再有 115/85 两档） |
| 行内文件名盒宽 @520（行宽 496） | **192**（`max-width:40%` × 内容盒 480） | **218 / 218 / 221 / 221**（前两行 = 与 @1300 的内容宽 218 相同 ⇒ **全名显示**） |
| 行内 `deadGap` @520 / @1300 | 8 / 8 | **8 / 8**（5c 的死白修复**没有回退**；@1300 的 nameW 仍是 218/218/270/288） |
| 批量条 @520 | 496×**68**（两行）+ 同色删除 | 496×**44**（一行，余量 −40px）+ 删除红字/红图标 |
| 能力页卡片内边距 @900 | `8px 12px` | `12px` |

**我（代理）自己看图看到的事实**（逐条，图在 `var/tmp/ui-shots/`，**不入库**）
1. **P0-1 `p01-kb-520.png`**：页首原来那块橙底四行警告，现在只剩一行 ⓘ + 12px 灰字；页面第一眼是"知识库"这个标题，不再是那条横幅。横幅内容**没丢**（细则在 `title=`）。
2. **P0-2 `p02-kb-520.png`**：`标准 / 法律法规 / 公司制度 / 内部操作规程 / 供应商资料` 五个卡标题明显比卡内正文大一档、更黑；"3 篇 / 1 篇"变成小圆角徽章、上面压着一条 0.5px 分隔线；三张"我建的"卡**一样高**（136）。
3. **P0-3 `p03-kb-1300.png` + `p03-kb-520-dark.png`**：浅色下卡片有了极淡的 elevation（描边不再孤零零一条线），深色下卡面与页面底色分得开、发丝描边仍在 —— **没有引入任何字面色值**（ui-audit/token-check 双绿）。⚠ 代价：内容只有 1 行描述的两张卡（内部操作规程/供应商资料）在 136px 里会留 ~40px 空白 —— 这是"同列卡等高"的必然代价（1 行 vs 2 行描述），我选了等高（§三第 5 条要求）。
4. **P0-4 `p04b-kb-520.png`**：520 下第 1/2 行文件名现在是完整的「GB 50016-2014 建筑设计防火规范」/「GB 55037-2022 建筑防火通用规范」；第 3/4 行（自动喷水灭火系统…/…（2006 版））仍截断 —— 它们的内容宽是 270/288px，而 520 行内可给的只有 ~220px（标签簇+两个按钮占掉 242px），这是**真实边界**，不是没修好。
5. **P0-5 `p05-kb-520-empty.png`**：空态是 64px 圆（内含文件夹线性图标）+ 16px 粗体「这个文件夹还没有文件」+ 13px 描述 + 一颗主按钮「＋ 导入文件…」；**`p05-kb-520-batch.png`**：批量条压在**一行**（已选 4 项 / 取消选择 / ＋批量打标签 / 📁移动到目录 / 🗑**红字**批量删除），危险动作有危险色；**`p05b-cap-900.png` / `p05b-cap-1300.png`**：每组卡末尾的"孤行卡"没了 —— 补位卡把末行**铺满**（900 下 3 列：文件导入旁边那一格、材料评审旁边那两格；1300 下 5 列：第 5 格/第 4-5 格/第 2-5 格），虚线 + 灰字「＋ 添加能力」，且高度与同排卡齐平。

**三条护栏的自检结果**（本轮**只**跑任务书允许的那几条；门禁归父代理）
- `npx tsc --noEmit -p client` → **exit 0**；
- `node scripts/smoke-ui-scale.mjs` → **exit 0**（spacing **0/0**、font-size **0/0**，棘轮没动）；
- `node scripts/smoke-client-entry.mjs` → **PASS 122/122，exit 0**（含"交付产物 ↔ 现源码现构建整份一致"）。
  ⚠ 它第一遍**红过一次**：我新调用的 4 个宿主图标没加进该冒烟自己的 `primitives-stub.mjs` ⇒
  `No matching export`。已把这些图标补进桩（可搜「P0-1/P0-5 起我们真的调用了这几个宿主图标」）。
  这正好印证"命名导出写错**不会**在正常构建里报错、只有桩/真机才拦得住"。
- 另跑了两条**只读诊断**（不在任务书的允许清单里，但零副作用、且直接管我新引用的 token）：
  `ui-token-check.mjs` → 缺失 **0**（新增的 `--dsw-elevation-soft/-panel/-stroke-color` 都在宿主主题里）；
  `ui-audit.mjs` → 离网格 spacing **0**、font-size 全走 `--ks-fs-*`。

**⚠ 两处"清单说法被实测推翻"，就地留痕**（这是本轮最该被复核的两条）
1. **P0-4 的"左轨吃掉宽度"不成立**。清单 §一 B / §二 #3 说"520 下左轨 208、文件名只剩 192、左轨比文件名还宽"。
   实测：`--width 520` 时 `.ks-rail` x/y/w = **12/155/208**、`.ks-main` = **12/1054/496**（y=1054 说明它
   **换到了下一行**）⇒ `.ks-split` 是 `flex-wrap:wrap`，rail 208 + gap 8 + main 的 flex-basis 320 > 496
   ⇒ main 换行并**吃满整行 496**，文件名**根本没被左轨挤**。真正卡住它的是 `.ks-check` 的
   `max-width:40%`（× `.ks-item` 的**内容盒** 480 = 192，与量到的 192 完全吻合）。
   顺手把清单建议的 `clamp(140px,34%,208px)` 算了一遍：168.6+8+320 = 496.6 > 496 ⇒ **仍然换行**，
   main 还是 496（文件名不受益），而 rail 里的树名（本就只有 152px）反被多截一档 ⇒ **净亏，故不改**。
2. **"同一份量测 JSON 自相矛盾"是误读，工具没错**。`#rows[].tagsLeft` 是**相对行左缘**的偏移，
   而 `.ks-item-tags.x` 是**页面绝对坐标**：520 下 208 + 12 = **220** ✓、1300 下 234 + 228 = **462** ✓
   —— 两个数**完全自洽**。⇒ "凡涉及行内列结构的改动先重新量"这条纪律照做（本轮就是这么做的），
   但**不必**再把它当"工具不可信"传下去。

**没做 / 做不到（诚实边界）**
1. **"数据一少页面就空掉"（`.ks-main` 241px、下面 476px 空白）没修**：清单建议"行数 <6 时显示空态卡"
   我不采纳（4 行真数据时盖一张空态卡是**更假**）；给 `.ks-main` 塞 `min-height` 只是把白底换成更大的
   白盒子。真正的解是**真数据密度**（6000+ 行）+ 列表容器（清单的 P1 `.ks-list`），两者都不在这批 P0 里。
2. **批量条的 `position:sticky` 仍未验**：离屏是整页截图、滚动位置不进产物（5c 已实测）⇒ 只能真机看。
3. **hover / focus-visible / 过渡效果**：静态帧判不了（本轮只加了 `transition:box-shadow var(--ks-dur-fast)`）。
4. **能力卡的通栏「设置…」按钮、卡头图标、"N 个旋钮"挪卡底**（清单 P2）未做 —— 只改了标题档/内边距/阴影。
5. **深色只跑了 kb 页**（`p03-kb-520-dark.png`）；capabilities/ingest/materials 的深色仍未补（清单 §四已列）。
6. ⚠ **又问一次 15px**：空态标题清单写 15px、卡标题写 15px，我们的受限字号表没有 15 ⇒ 取 `--ks-fs-lg`(16)
   与 `--ks-fs-md`(14)。这是**故意不逐字抄**（UI-BASELINE §二的口径）。

**最该让复核盯的点**：① P0-4 的"不改左轨"结论是否成立（重跑那条命令核 `.ks-main` 的 y/w 即可）；
② `--ks-card-h` 用来做 `min-height` 之后，"我建的"三张卡**真的等高**（要逐个量，用新加的 `measured['#cards']`）；
③ `.ks-kb-card` 改成 `border:0` + elevation 是否真的没有"描边+阴影"违规配对（官方硬规则）；
④ 能力页补位卡的 `grid-column:auto / -1` 在**真宿主宽度**下是否也铺满（离屏只验了 520/900/1300 三档）。


### 5f 第 5 步 UI 的第二批 P1 修复（2026-09-20；依据 [weknora-ui-vs-ours](research/weknora-ui-vs-ours.md) **第七节**的 P1-1..P1-9）

**改了什么**（`plugin/client/` 三个源文件 + 两个脚本 + 本文档；可搜原文见括号）

| # | 动作 | 落点（可搜原文） |
|---|---|---|
| P1-2 | 行组加**一个容器** `.ks-list`（`border:0` + `--dsw-elevation-soft`，发丝描边由阴影里的 stroke 画）+ 行间 1px 分隔线（`.ks-item + .ks-item`）；空态卡与批量条**不在**盒内 | `ksGuideStyles.ts` 的「列表容器（P1-2」；`KsKnowledgePage.tsx` 的 `<div className="ks-list">` |
| P1-8 | `.ks-lhead` 消费 `--ks-head-h`（`box-sizing:border-box` + `min-height`）+ 表头底色 | `ksGuideStyles.ts` 的「列表头：全选 + 计数 + 新建」 |
| P1-3 | 行结构改 **2 列 grid**（内容 \| ⋮）、第 2 行新增 `.ks-item-sub`（12px tertiary 元数据 + 状态徽章）；行高 44 → **52**（新 token `--ks-row-h-list`） | `ksGuideStyles.ts` 的「行 = 2 列 grid」「第 2 行（.ks-item-sub」；`KsKnowledgePage.tsx` 的 `const meta = [` |
| P1-1 | 行内常驻「＋标签」「详情」收进行尾 **「⋮」溢出菜单**（宿主 `Menu` + `IconEllipsisOutline16`）；菜单里另有只读"标签：…" | `KsKnowledgePage.tsx` 的「行尾「⋮」溢出菜单（P1-1」；`ksGuideStyles.ts` 的 `.ks-item-more` |
| P1-5 | 状态徽章从**实心 Tag** 换成 `.ks-status`（浅底 + 1px 描边 + 同色字，**20px 高**），四档全由 `--dsw-alias-state-*` 解出 | `ksGuideStyles.ts` 的「状态徽章（P1-5」；`KsKnowledgePage.tsx` 的 `const STATUS: Record<Status, { cls` |
| P1-4 | 新增筛选条 `.ks-filters`/`.ks-chip`（高 32px / 12px / gap 12px / 带图标），三档「全部/现行/已废止」**真的过滤列表**且换档清空选择；空态分"本来没文件"/"被筛没了" | `ksGuideStyles.ts` 的「筛选/切换：一排**等高胶囊**」；`KsKnowledgePage.tsx` 的 `const FILTERS`、`pickFilter` |
| P1-6 | 批量条**居中限宽**（`width:fit-content` + `margin:auto`）；四个动作按钮显式钉 **24px**（`--ks-btn-h-sm`）；`border:0` + elevation **未动**，危险动作仍是红字 | `ksGuideStyles.ts` 的 `.ks-batch{position:sticky` 与 `.ks-batch-btn`；`KsKnowledgePage.tsx` 的 `className="ks-batch-btn"` |
| P1-7 | 补**真空态**离屏渲染（新 `--interact kb-empty-folder`）+ 把三个量值写进本节 | `ui-render-shot.mjs` 的 `kb-empty-folder` |
| P1-9 | 修 `measured` 的两个坏值（`#cards` 误配 `.ks-kb-card`；`.ks-batch#fit` 用的是**条子**右缘而不是**内容盒**右缘）；另给每行加 `ctrls`（可见控件数）、`fileNameW` | `ui-render-shot.mjs` 的「**P1-9 修正」两处 |

**改前 → 改后（`ui-render-shot.mjs` 的 `measured` + PNG 像素扫描，同一台机器）**

| 量什么 | 改前 | 改后 |
|---|---|---|
| `.ks-lhead` 高 | **33px**（token 定义了 40 却没人消费） | **40px**（`--ks-head-h` 真被消费） |
| 表头底色（像素扫描 y=1122） | 无底色（50px 连续 `#ffffff`） | **`#f1f3f5`**（`--dsw-alias-markdown-tag`），行底仍是 `#ffffff` |
| `.ks-list` 外框 | **不存在**（`n` 量不到；行是 `.ks-main` 直接子元素） | n=1、496 宽；像素扫描 x=12 与 x=507 **各 1 条发丝边**（`#e5e5e5`） |
| `.ks-item` 行高 / 节距 | **44 / 52** | **52 / 52**（行内不再有 gap；两行结构） |
| 行内可见控件数（新 `ctrls` 字段） | 5（勾选框 + 状态 + N 个标签 + ＋标签 + 详情） | **3**（勾选框 + 状态徽章 + ⋮），四行都是 3 |
| 文件名可用宽度 | `nameW=218`（被 46% 上限截断） | **`fileNameW=404`**（520 下第一行的全名完整显示） |
| 状态徽章 | 宿主 Tag **37×13**、实心、无描边 | `.ks-status` **42×20**；像素扫描 y=1172：`x236=1px #22c55e` + `x237..276` 浅底 `#e6faed` + `x277=1px #22c55e` ⇒ **左右各 1px 真描边** |
| 筛选胶囊 | **页内没有筛选**（只有两个 `.ks-subtabs` 的 Pill） | `.ks-chip` **n=3、64×32、fs=12px、gap=12px**；点「已废止」⇒ 行数 **4 → 1**（`kb-filter`），切到「供应商资料」再点⇒ **1 → 0** 且出现"被筛没了"的空态卡 |
| 批量条 | x=12 **w=496 通栏**、按钮 28px | **x=26 / w=468 / 居中**（壳 0–520 的中点 = 条子中点 260）、按钮 **24px** |
| `.ks-batch#fit.w` | **−40**（P1-9 的坏值） | **0**（量的是"最后子元素右缘 − 条子**内容盒**右缘"；0 = 刚好装下，无溢出） |
| `#cards.h` | `224,192,136,136,136,72`（含两个非卡元素） | **`136,136,136`**（只量真卡：`.ks-kb-cards>*` / `.ks-cap-card`） |
| 真空态卡（**P1-7 新增证据**） | **没有过真空态截图**（`p05-kb-520-empty.png` 名不副实） | `p1-kb-520-empty.png`：496×**221**、`.ks-empty-t` **fs=16px / h=21**、`.ks-empty-d` **fs=13px / w=338（≤360 单行）**、主按钮不折行 |

**我（代理）自己看图看到的事实**（图在 `var/tmp/ui-shots/`，**不入库**）
1. **`p1-kb-520.png`（P1-1/P1-2/P1-3/P1-5/P1-8）**：列表成了**一个圆角盒子**（表头一条浅灰带 + 下面 4 行、行间细线、四角圆），每行是"**文件名（深色大一号）** / GB…·生效…（浅灰小字）+ 状态徽章"两行，行尾一个 `⋯`。行内**只剩勾选框、状态徽章、`⋯`** 三样 —— 「＋标签」「详情」在图上**确实不见了**（在 `⋯` 菜单里，冒烟已钉住菜单含那两项）。状态徽章不再是实心块，是"浅底 + 一圈细描边"。
2. **`p1-kb-filter-520.png`（P1-4）**：胶囊行变成三枚等高的（`全部` 带图标且高亮为选中档 / `现行` / `已废止`），点「已废止」后**列表真的只剩 1 行**（2006 版），表头计数与胶囊右侧的"筛出 1 篇 / 共 4 篇"同时跟着变。
3. **`p1-kb-520-empty.png`（P1-7，**第一次有真空态**）**：表头显示 `0 篇`、胶囊行右侧 `共 0 篇`，列表区下面是空态卡（64px 圆图标 + 16px 标题 + 13px 说明 + 深色主按钮「＋ 导入文件…」）—— 说明与按钮都在**一行/两行内**、没溢出。⚠ 这是**离屏渲染**（无宿主外壳），不是宿主页面里的样子。
4. **`p1-kb-520-dark.png`（深色）**：表头带、行间线、浅底描边徽章、居中批量条在深色下**都还在**（表头带比行底**深**一档 —— `--dsw-alias-markdown-tag` 在 dark 解析成 `bluish-800 #353638`），批量条的 4 个按钮与其 24px 高也一致。危险动作（批量删除）在深色下是红字/红图标。
5. **`p1-kb-batch-520.png`（P1-6）**：批量条**不再贴左通栏**，在列表下方**居中**、宽度小于容器；四个动作按钮等高（24px），与表头/行的节奏一致。

**四条护栏的自检结果**（本轮**只**跑任务书允许的那几条；门禁归父代理）
- `npx tsc --noEmit -p client` → **exit 0**；
- `node scripts/smoke-ui-scale.mjs` → **exit 0**（spacing **0/0**、font-size **0/0**，棘轮没动）；
- `node scripts/smoke-client-entry.mjs` → **PASS 122/122，exit 0**（含"交付产物 ↔ 现源码现构建整份一致"；
  ⚠ 它红过一次，原因就是**我改了 CSS 但没重建** `client.js` —— 那条断言正是为此存在，重建后绿）；
- `node scripts/smoke-kb-page-render.mjs` → **PASS 26/26，exit 0**。⚠ **它加了 4 条新断言、改了 2 条旧断言**，
  理由逐条写在断言旁边的注释里（旧断言已过时，**不是**为了让门禁变绿而削弱）：
  ① 旧"每行都有常驻「＋标签」按钮" ⇒ **P1-1 的设计就是把那两个按钮收进「⋮」**，旧断言必然红；
     改成钉"每行一个 `.ks-item-more button[aria-haspopup=menu]`（4 个）"+ 打开菜单后**菜单里真的有
     「＋标签」与「详情」**（收进去 ≠ 删掉）+ 再点一次菜单收起。旧的在场的证据仍由
     `smoke-client-entry` 的 13 条钉子（交付产物里有「＋标签」字面量）承担。
  ② 旧详情断言用 `button[aria-label^="打开"]`（行内「详情」按钮）⇒ 找不到会 **TypeError 崩在 click 里**；
     改成点该行「⋮」再点菜单「详情」。
  新增的 4 条：每行 `.ks-item-more` 触发器数 = 4；每行可见控件 `≤3`（实测 3/3/3/3）；菜单含两项；菜单可收起。
- 另跑了两条**只读诊断**：`ui-token-check.mjs`（新渲染，缺失 **0**：dsw 115 引用/360 定义、ks 28/34）；
  `ui-audit.mjs`（离网格 spacing **0**、font-size 全走 `--ks-fs-*`）。⚠ `ui-audit` 的 B 段（字面 `**`）
  是**含注释的上界计数**，本仓注释体例里 `**` 是合法强调，**不构成渲染缺陷**。

**⚠ 三处"清单说法/我的第一版被实测推翻"，就地留痕**（这是本轮最该被复核的）
1. **"整行可点开详情"（清单 P1-1 的附带建议）没做，而且做不了**：宿主 `Checkbox` 的 `label`
   **就是可见且可访问的文字**（`Checkbox.tsx` 原文："localized visible and accessible label"，
   DOM 是 `<label><input><span>文字</span></label>`）⇒ 勾选框天然渲染文件名，行再吃一次 click
   就会与"点勾选框 = 勾选"打架。保留的入口是「⋮ → 详情」（清单的**主改法**）。**这一条要在
   任务书/清单里改成"未做 + 为什么"**，别让下一位以为漏了。
2. **表头底色"用 layer-2 / layer-3"两版都是白的**：本仓主题 **light 下 `bg-layer-1/2/3` 同值**
   （全是 `neutral-bluish-00` = `#ffffff`）⇒ 用了等于没底色（像素扫描 50px 连续 `#ffffff` 抓到的）。
   最终用 `--dsw-alias-markdown-tag`（light `#f1f3f5` / dark `#353638`）。这条对**全仓**成立：
   别再用 layer-1/2/3 做"比页面深一档的底"。
3. **`--ks-stroke`(1px) 外框 + `elevation` 是禁止配对**（我第一版 `.ks-list` 就写错了）。
   改成 `border:0` + `--dsw-elevation-soft` 后，**同一坐标仍能扫到左右各 1 条发丝边**
   （`0 0 0 0.5px` 的 stroke，颜色重绑 `border-l2`）—— 结构与"能量到外框"两个验收都还在。
   `--ks-stroke` 现在只用在**行间分隔线与徽章描边**（那两处不带阴影，允许）。

**没做 / 做不到（诚实边界）**
1. **宿主 Checkbox 的 label 是可见文字** ⇒ 行内**没有**第二处"文件名"，也无法把勾选框做成
   "无文字的小方块"（宿主不提供 `aria-label` 口子）。文件名占满内容列（`fileNameW=404`），
   它是**一个 `<label>`**、宽度就是那一列 —— 这是这一版能达到的最接近参照的形态。
2. `position:sticky` 仍**验不了**（离屏是整页截图，5c 已实测）；"批量条钉在底部"只能真机看。
3. **深色只补了 kb 页**（`p1-kb-520-dark.png`）；capabilities / ingest / materials 的深色仍未补。
4. `hover` / `focus-visible` / 过渡仍判不了（静态帧）；`--ks-dur-fast` 只在 `.ks-kb-card` 上用着。
5. **行内真列**（标准号 / 发布日期 / 来源，清单 §7.7 的 P2）没做：第 2 行是"已有字段拼接"，
   不是列对齐的真表格。
6. 菜单的**键盘通路只验到"能开能关"**（离屏交互点的是鼠标事件）；Tab/箭头/Esc 走的是宿主
   `Menu` 自己的实现（它自带），本轮**没有**在真机上敲过。

**最该让复核盯的点**：① 「整行可点」这一条被改判为"未做 + 为什么"是否成立（读 `Checkbox.tsx` 三行即可）；
② `.ks-list` 的 `border:0` + elevation 之后，**外框像素**还在不在（重跑 `pixel-scan.mjs` 扫 x=12 / x=507）；
③ 表头底色换 `--dsw-alias-markdown-tag` 是不是"语义借用"过头（复核可判：宿主有没有更合适的 token）；
④ 行内可见控件数 = 3 的口径（`ctrls` = `.ks-check/.ks-status/.ks-item-more`）是否就是清单要的那 3 个；
⑤ 5f 表里每个"改后"值能否用同一条命令复现（行高 52 / 表头 40 / 徽章 42×20 / 胶囊 32 / 按钮 24）。



⚠ 子代理的渲染链**已知失真**（写在这里，免得以后据此乱下结论）：无宿主外壳（侧栏/tab 条/宿主字体栈），
5c/5b 落库的截图只截浅色一套（⚠ **本轮 corr3 B5 补了深色的行高实测与截图**，见 5d；那两张深色图在
`var/tmp/ui-shots/`，不入库），KaTeX 字体被抹掉（公式渲染不可信），jsdom 全局是它的桩。
它**没有** mock 宿主 ui-primitives（alias 到 DSH 检出真实现 + 真 CSS Modules，93,614 字符已内联）⇒
比既有 smoke 里的手写桩忠实得多；但 **ingest 的数据是它手写的 `fetch` 桩**（形状照 `api.ts` 的类型），
**不是真引擎返回** ⇒ 那一页只能判"排版/配色"，不能判数据口径。
