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
| 列表行 | 行高 60、表头 40、左右 padding 16、容器圆角 9 | 内容列表照做 |
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

### ⚠ 2026-09-20 实测的环境事实：**宿主 GUI 对我们的浏览器自动化是 401**
`browser4-cli` 打开 `http://127.0.0.1:3080` 拿到的是一个 133 字节的 401 残页（`scripts[].length === 0`、
`title` 空）；换 `localhost`、补 `Origin`/`Referer`/`Sec-Fetch-*` 头仍 401（`Invoke-WebRequest` 同样 401）。
⇒ **上面第 2/3 步对"未登录的外部浏览器"走不通**（业主自己的浏览器是已授权的，我们不是）。
**替代路径（已跑通）**：把页面**离屏渲染成自包含 HTML**（jsdom + React，样式内联 `KS_STYLES` + 宿主主题 token），
再用 `browser4-cli goto file:///...` 截图。工具：`var/tmp/ui-render-shot.mjs`（未入库，见下节记录）。
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
- **我（代理）自己看图看到的事实**（逐条，不是"我觉得还行"）：
  1. ✅ 骨架成立：标题 ~20px 粗体 → 12px 灰副标题 → 0.5px 分隔线，层级一眼能分（改前标题与按钮同高）。
  2. ✅ token 生效：卡片内边距、行距、圆角在各处一致，没再出现 7px/9px 那种数字（渲染里量到的是 4 的倍数）。
  3. ❌ **窄宽（520px）下文档行溢出**：徽章组 + 「详情」被挤到第二行，末两行出现「详／情」**竖排折行**
     —— 这是"对齐不齐/挤"那一类难看，必须修（徽章组 `flex:none` + `nowrap`，让**文件名**去截断）。
  4. ❌ **卡片宽度不一致**：同一页里「标准/法律法规」两张卡在 520px 下**通栏**（~490px），
     而「我建的」三张卡只有 ~200px（1300px 下又都一样窄）⇒ 两组卡的容器/网格不是一套。
  5. ⚠ **1300px 下右侧大片留白**：内容没有 max-width，也没有多列网格，宽屏显得没做完。
  6. ⚠ 顶部那条橙色「UI 先行：数据是占位」横幅在页面里**最抢眼**（比标题还显眼）——它是临时告知，
     等接引擎后应降级为一行灰字或去掉。
- **结论**：5a 只做到"有了尺度系统与页面骨架"，**3/4/5 三条留作 5b**（见下）。截图只作"我们自己的块"的证据。

