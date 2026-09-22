# 已否决 / 已作废台账（**提任何新待办、计划、设计之前先对一遍这份**）

**为什么要这份文件**：2026-09-19 我连续两次把**业主早就否掉**的东西重新端上来当待办 ——
先是"Word/PPT 交付物"，再是"bbox 高亮"（实际早就改成**红色定位箭头**）。
根因不是记性差，是**这些裁定散落在各文档里、没有任何一处要求"提案前先核一遍"**。
这份台账就是那道闸：**任何新提案/新待办/新设计，先在这里查有没有被否过**；否过的**不许再提**。

**规矩**（写进 [AGENTS.md](../AGENTS.md)）：
1. 提新的待办/计划/设计前，先搜这份台账；命中 ⇒ 不许再提（要翻案请业主明说）。
2. 任何"业主否决/裁定"**必须**登记到这里（一行），并在其**归属层**留下正文与理由。
3. 作废的旧计划/旧说法**直接删掉**，只在**开发史**里留一句"曾如此、何时作废"——
   不留"半作废"的句子（那种句子我下次一定会误读）。

| # | 事项 | 裁决 | 日期 / 业主原话要点 | 归属（正文在哪 / 该怎么做） |
|---|---|---|---|---|
| 1 | **Word/PPT 交付物**（研究/巡检报告落 `.docx`、PPT 生成、Office 往返） | ⛔ **否决**：产出物**只出 Markdown** | 2026-09-19「Word / PPT 这类交付物这个我不是说了吗，不要，就输出 markdown」「早就否定了又在说」 | [交互设计 §九](INTERACTION-DESIGN.md)：**不做 PPT/多形态分发**。✅ **已实施拆除（本轮，2026-09-19，[EXECUTION-PLAN](EXECUTION-PLAN.md) 第 4 步）**：`slide_export.py` 与 `/report/research/slides` 删除、研究报告的 `.docx` 形态与 `_to_docx`/`_docx_template_path` 删除、`report_export` 的两条 Word 导出（问答依据/审查报告）与 `_open_document`/`_templates_dir` 删除、更新检查报告 Word 版与 `/update/report/{batch_id}` 删除、义务清单 Word 导出删除、`python-pptx` 依赖删除（`python-docx` **保留**：输入侧解析与 `office_roundtrip` 要用）、UI 的「生成 PPT」按钮与 `exportResearchSlides` 删除。**仍在的**：`.md`（交付物本体）/ `.html`（界面预览形态）/ `.xlsx`（裁决没碰 Excel）/ `office_roundtrip`（编辑工具，不是交付 Word 文件）。⇒ 从此**不许**再把它当"功能"介绍，**也不许**把它写回待办 |
| 2 | **取证呈现用 bbox 高亮框** | ⛔ **否决**：改成**红色定位箭头** | 早于 2026-09-19（本次复核时业主重申） | [交互设计 §三](INTERACTION-DESIGN.md)：`[点开原文] ← 跳 PDF 对应页 + **红箭头**高亮`；§"保留，不动"一表亦写明**红箭头高亮**；实现在 `plugin/client/KsEvidenceTab.tsx`（`bbox` 只是**定位坐标**，呈现是箭头）。⇒ **不许**再说"bbox 高亮/跳页高亮"，说**红色定位箭头** |
| 3 | **真机录屏 / GIF 证据** | ⛔ **不做** | 2026-09-19 | 只有这条裁定，无正文（DSH 适配清单里已移出） |
| 4 | **照抄 WeKnora 的形态**（曾裁定"不照抄"） | 🔄🔄 **再翻案（2026-09-22，以本条最新裁定为准）**：**骨架不再照抄 WeKnora** —— 业主原话要点：WeKnora 那套「是我自己没思路的时候参考的」，现在**按助手自己的设计意见来做**（业主信任其前端设计能力）；**细节遵循 DSH 设计规范**；**结构性大改先问业主**。⚠ 补充口径（2026-09-22 业主同日追加）：「**这种小改动你直接改，大的结构化变化再问我**」——小改（图标/用词/样式/文案/单点缺陷）**不必请示**、照旧小提交+截图；只有**结构性大改**才来问 |⚠ 历史留痕（不许删）：2026-09-19 曾翻案为「形态与界面照抄（知识库管理那套）；技术栈仍不引入」，UI-BASELINE/INTERACTION-DESIGN 中以 WeKnora 为骨架的段落将按本裁定重写 | 2026-09-22「骨架不要照抄weknora了，那是我自己没思路的时候参考的，现在你来了，你可以按照你的意见来做，我还是相信你的前端设计的能力的，细节遵循DSH的设计规范没问题。不过如果要结构性大改，那还是先问问我」；历史裁定 2026-09-19「我想让照抄 weknora 的部分 UI」「你先把人家这块儿的东西读明白」 | 抄什么/不抄什么见 [weknora-ui 清单](research/weknora-ui/00-index-and-proposal.md)；理由与边界见 [交互设计 §九](INTERACTION-DESIGN.md)（**该节已按新裁定更正**）：我们是 React + 宿主原生组件，**照结构/视觉重写**，不搬 Vue/TDesign 代码 |
| 5 | **客户端文案多语言（locale 化）** | ⏸ **缓办**（不是否决） | 2026-09-19「多语言先不管」 | DSH 适配清单里标「缓办」，不许当"下一步"；**但**"文案集中 + 漏键门禁"这条小得多的路可以做（见 weknora-ui 清单 i18n 行） |
| 6 | **通用层自己设计/手搓** | ⛔ **否决**（造轮子） | 2026-09-19「通用层不要再投…如果有现成项目和思路，抄一下就能实现很好的效果，那还是可以投…**通用层现在要纯借鉴**」 | [WeKnora 影响评估 §五第 0 条](research/weknora-assessment.md)：有现成的 ⇒ 读它抄它；只能从零设计并长期维护 ⇒ 不做 |
| 7 | **`peerDependencies` 必须声明** | ⚰ **已作废**（官方 alpha.2 取消该校验） | — | [ERRATA-alpha.2 §I](research/dsh-official/ERRATA-alpha.2.md) |
| 8 | **插件改动必须重启宿主** | ⚰ **已作废**（热重载；只有引导/静态装配/壳要重建） | — | [ERRATA-alpha.2](research/dsh-official/ERRATA-alpha.2.md) |
| 9 | **`priority` 是数字** | ⚰ **已作废**（是 band 字面量） | — | 同上 |
| 10 | **`reflect` 的 `max_tokens` 是 4096 上限** | ⚰ **已作废**（真实上限在服务端配置 `reflect_max_completion_tokens`，默认 None） | — | [REALIGN §五之二](research/dsh-official/REALIGN.md) + 开发史 §10.131① |
| 11 | **布局只在内存里** | ⚰ **已作废**（会话级持久化 + provider 恢复） | — | [errata/开发史记录](DEVELOPMENT-HISTORY.md) |
| 12 | **`schemastery` 有 `.strict()`** | ⚰ **已作废**（本地 3.18.2 没有；官方那些 `.strict()` 来自 **zod**） | — | 开发史 §10.136 四 + `plugin/src/index.js` 的 Config 注释 |
| 13 | **知识库页内的搜索框**（文件列表按标准号/名称过滤） | ✅ **业主 2026-09-20 明确：保留**（原话：「**搜索框：保留**」）—— 这条翻案**已结案**，不再是"待业主确认"。**历史（原话与更正都保留，不许悄悄删）**：2026-09-19  业主 13 条里第 4 条曾明确"知识库界面不做搜索（这一页没有搜索框；搜索发生在'提问'那一侧）"，当时连渲染级断言都钉死了；**2026-09-20 第 5 步 P2 头条任务书**先要求"列表上方加一个搜索框（宿主 Input），必须真的过滤"⇒ 按任务书施工过一轮（当时业主未表态）；**同日业主本人结案：保留** | 2026-09-20「搜索框：保留」（结案）／历史依据：2026-09-19「知识库界面不做搜索」、2026-09-20 任务书（P2 头条第 3 条） | 归属层：[KsKnowledgePage.tsx](../plugin/client/KsKnowledgePage.tsx) 顶部第 4 条的**翻案留痕**（旧原话保留 + 更正框 + 2026-09-20 结案行）+ [UI-BASELINE 5h](UI-BASELINE.md)。**若将来业主要退回**：按下面「[第 13 条的退回步骤（可执行版）](#第-13-条的退回步骤可执行版2026-09-20-p2-复核打回-c-补)」逐条走 —— ⚠ 本节原来那句"删 `.ks-search` 那一段与 `search`/`pickSearch`/`hitSearch`，再把 3g/3h 换回'本页没有搜索框'"**不可执行**（实测 `ReferenceError: needle is not defined`、smoke exit 1、页面崩），而且会把**已证伪的假绿**装回去；错话原文与更正都在那一节里。⚠ **5h（2026-09-20）后搜索框的位置**：它跟着**文件表格**走（只在"最末一级"渲染）—— 它过滤的是文件，目录层没有可筛的文件；"在/不在"仍由 `KB_FILE_VIEW_SEARCH` 声明 + 渲染级断言锚住。⚠⚠ **5i（2026-09-20 收尾批）就地更正上面这一句**：**层级口径：每层常驻**（业主 2026-09-20 只说保留、未限定层级，按最强解释执行）⇒ 库根 / 一级目录 / 二级目录 / 文件层**都有**这个框，目录层过滤**目录名**（不命中给「没有符合搜索的目录」空态）、文件层过滤标准号/名称；声明常量同时改名为 **`KB_PAGE_SEARCH`**（旧名 `KB_FILE_VIEW_SEARCH` 里的 `FILE_VIEW` 已不成立）。搜索词处置口径：切库清空 / 同库内下钻与返回上级保留 / 切筛选保留（AND）。**证据**：[UI-BASELINE 5i](UI-BASELINE.md)（逐层条目数 + 目录层截图）+ `smoke-kb-page-render.mjs` 的 2h–2o 八条断言 |
| 14 | **知识库文件层右栏那张「详情」提示卡**（写着「点每一行行尾的「⋮」→「详情」看这一篇的元数据（含发布日期 / 生效日期 / 废止日期）」的占位卡） | ⛔ **业主 2026-09-20 明确：删除** —— **已拆**（不是隐藏、不是改文案） | 2026-09-20 原话照抄：「点每一行行尾的「⋮」→「详情」看这一篇的元数据（含发布日期 / 生效日期 / 废止日期）。 这个卡片删除掉」 | 归属层：[KsKnowledgePage.tsx](../plugin/client/KsKnowledgePage.tsx) 右栏那一处注释（含"**没选中任何一行时整栏不渲染**"这个**我定的**取舍 + 一行可逆法）+ 开发史 §10.147。⇒ **不许**再把这张提示卡加回来（"未选中时该显示什么"不是本条的口子；真要提示就换位置，且先问业主） |
| 15 | **人工上传材料的"待评审"步骤** | ⛔ **裁定：免评审**（2026-09-22，范围收窄）——用户亲手上传的材料（公司制度/文档/自创规则）**传完直接能用**，不再有"批准"步骤；只留一个小选择「**必须遵守 / 仅供参考**」（默认必须遵守，它决定该材料在答案里说话的分量）。**"待评审"只保留给网上抓取/系统自采的材料**（来路是别人的，能不能信由用户判）。旧口径"所有材料都过人工批准（硬门）"**作废至此范围** | 2026-09-22「我既然人工上传公司制度或者什么开发文档或者我自创规则设定了，那肯定我知道我上传的是什么啊」 | 归属：[MATERIALS-PLANE-PLAN](MATERIALS-PLANE-PLAN.md)（评审门适用范围）+ [交互设计](INTERACTION-DESIGN.md) + S3 原型 v2；自采材料的评审硬门**原样保留** |
| 16 | **合同审查 / 义务清单→检查表 / 批量问答 / 取证问答（办事台指路页）/ 条款释义 —— 五件套整体删除，前后端都删** | 业主（2026-09-22）："…全部删除，前后端都删除，没用"（「制度差距分析 / 纠错修订 / 外发审计」**不在**删除单上，三件保留；差距分析依赖的数据表随之**保留**） | ⚠ **口径留痕**：「取证问答」= 办事台那行"去对话里提问"的**指路页**（删）；对话取证引擎（ks_answer / ks_resolve_clause）**保留**——它是「本轮证据」与合规护航的地基。若业主本意连对话问答一并删，**见此条即说** |

> ⚠ **这份台账本身也要守规矩**：翻案（如第 4 条）必须**就地改写**，不许新旧两说并存 ——
> 两说并存正是"翻旧账"的温床。

## 第 13 条的退回步骤（可执行版；2026-09-20 P2 复核打回 C 补）

**先说错话（原文保留，更正在后 —— 本仓规矩）**：

> **曾如此（不可执行的退回步骤）**：删 `.ks-search` 那一段（1 个 `<span>` + 1 个 `Input`）
> 与 `search`/`pickSearch`/`hitSearch`，再把 `smoke-kb-page-render.mjs` 的 3g/3h 换回"本页没有搜索框"
> （旧写法的样子留在该文件注释里）

复核（`verify-freeze-p2`）**逐字走了一遍**，结果是：`ReferenceError: needle is not defined`、
smoke exit 1、页面崩。两个毛病：

1. **漏了 5 个落点**（只删那三处 ⇒ 编译/运行时必炸）：`listed` 的 useMemo 里 `hitSearch(d)` 调用
   **与 `[needle]` 依赖**、空态里的 `search.trim()`、空态按钮的 `pickSearch('')`、
   `ksGuideStyles.ts` 的 `.ks-search` 三条样式、以及 import 列表里的 `IconSearchOutline16`。
2. **方向是错的**："把 3g/3h 换回'本页没有搜索框'"等于**把一条已证伪的假绿装回去** ——
   旧断言跑在**标签视图**（文件视图的框即使存在也没挂载）且只数 `placeholder` 里有没有"搜索"
   两个字 ⇒ 文件视图有没有搜索框它都 PASS。

**更正（逐落点、按顺序；本批**亲自按它走了一遍**，走查证据在下一节）**：

1. `KsKnowledgePage.tsx`：`export const KB_FILE_VIEW_SEARCH: boolean = true` → **`false`**
   （这是"搜索框在/不在"的**唯一声明**，渲染与否由它决定）。
2. 删掉 `{KB_FILE_VIEW_SEARCH && (<span className="ks-search"> … </span>)}` 整块（含它上面的注释）。
3. 删掉 `const [search, setSearch] = useState('')`（连它上面那段"列表搜索串"注释）。
4. 删掉 `const needle = search.trim().toLowerCase()` 与 `const hitSearch = …`（连注释）。
5. `listed` 的 useMemo：
   `inFolder.filter((d) => filterTest(d) && hitSearch(d))` → `inFolder.filter(filterTest)`；
   依赖数组 `[inFolder, filterTest, needle]` → `[inFolder, filterTest]`。**`[needle]` 这一处最容易漏**。
6. 删掉 `const pickSearch = (value: string): void => { setSearch(value); setSelected(new Set<string>()) }`（连注释）。
7. 空态卡（"被筛没了"那一支）三处：
   · `没有符合筛选或搜索的文件` → `没有符合筛选的文件`；
   · 描述里的 `? <>，搜索「{search.trim()}」一篇都没命中。</> : <>，当前筛选「…」与搜索一篇都没留下。</>`
     → 只留 `，当前筛选「{FILTERS.find(…)}」一篇都没留下。`（**`search.trim()` 在这里**）；
   · 按钮 `onClick={() => { pickFilter('all'); pickSearch('') }}` → `{ pickFilter('all') }`，
     文案 `清除筛选与搜索` → `清除筛选`、`title` 去掉"并清空搜索串"（**`pickSearch('')` 在这里**）。
8. import 列表：去掉 `IconSearchOutline16`。
9. `ksGuideStyles.ts`：删 `.ks-search{…}` / `.ks-search>span{…}` / `.ks-search input{…}` 三条与注释。
10. `plugin/scripts/smoke-kb-page-render.mjs`：删掉 **3g / 3h 那一个 `if (searchBox === null) … else …` 块**
    （行为级断言随功能一起走），**保留**它前面那条
    「文件视图的搜索框"在 / 不在"与声明 `KB_FILE_VIEW_SEARCH` 一致」——
    退回后它断言的正是"**必须真的不在**"，所以**覆盖缺口是关掉的，不是取舍**。
    ⚠ **不许**再加一条"本页没有搜索框"那种数 `placeholder` 的断言。
11. `node scripts/build-client.mjs`（重建交付产物 `plugin/client.js`）。

**⚠ 5i（2026-09-20 收尾批）对上面这份退回步骤的两处更新**（不动上面的原话，只在这里补）：
- 上面第 1 / 10 步里的 `KB_FILE_VIEW_SEARCH` **已改名为 `KB_PAGE_SEARCH`**（框现在是**每层常驻**，
  旧名里的 `FILE_VIEW` 与事实不符）⇒ 走这份步骤时按**新名**读。
- **新增落点**（5i 起的搜索框）：`searchBox` 那个常量（一份定义、两处渲染：文件层在
  `.ks-filters` 与 `.ks-list` 之间、**目录层在 `.ks-dirs` 之前**）、`hitDirName` / `kidsShown`
  （目录名过滤，`useMemo`）、目录层的 `没有符合搜索的目录` 空态卡与「清除搜索」按钮、
  面包屑右侧「筛出 X / 共 Y 个子目录」那一支、以及 `smoke-kb-page-render.mjs` 的 **2h–2o 八条**
  逐层断言（删框时它们会红，这是**设计成红**的 —— 不许把它们改成"数 placeholder"的假绿）。

**走查证据（2026-09-20，本批亲跑；变异脚本 `var/tmp/c-rollback-walkthrough.mjs`，不入库，跑完自动还原）**

- **变异 C-1**（只删搜索框、声明仍 `true`）⇒ `smoke-kb-page-render` **FAIL 31/34, exit 1**，
  红的三条是：声明一致性（`声明 KB_FILE_VIEW_SEARCH=true；DOM 里 .ks-search input 不存在`）、
  搜索真的过滤、搜索即清空选择；**进程没有崩**（旧写法会 `TypeError` 崩，现在有可诊断的 FAIL 行）。
- **完整 11 步退回** ⇒ `tsc --noEmit -p client` **exit 0**、`smoke-kb-page-render` **PASS 32/32, exit 0**
  （32 = 35 − 3：3g/3h 那三条随功能删掉，声明那条留下并断言"缺席"）⇒ **能干净退回、不崩**。
- 走查结束后四个被改文件（`KsKnowledgePage.tsx` / `ksGuideStyles.ts` / `smoke-kb-page-render.mjs` /
  `client.js`）**逐字节还原**（脚本末尾按 sha256 核对，`git status` 干净）。
