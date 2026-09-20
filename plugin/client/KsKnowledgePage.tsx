/**
 * ks-dsh-plugin — client/KsKnowledgePage.tsx
 *
 * 「知识库」tab 的 body（业主 2026-09-19：「干脆直接把 UI 落地，只做 UI 后端先不做」）。
 *
 * ## 本轮的性质（必须先说清，免得后人以为它是完成态）
 * **只有 UI**：库、文件夹、文档、日期、标签**全是本文件内的占位常量**，
 * **一个引擎接口都没调**（没有 `/ks/*`、没有 fetch、没有 token）。
 * 页首有一条黄条把这件事**写在界面上**，不让它冒充可用能力。
 * 但**交互是真的**：勾选、全选、批量动作、增删标签、切换视图都作用在 React 状态上，
 * 所以业主可以真去点、去体验（这正是他说的"我就想体验好了再改项目文件"）。
 * 唯一含有真逻辑的是检索语法解析（`ksSearchSyntax.ts`），它有独立冒烟逐例钉住。
 *
 * ## 这一版按业主 2026-09-19 的 13 条改（逐条对照，免得漏）
 * 1. **收藏 → 标签**、不再做收藏（页内二级 tab 是「文件 / 标签」）；
 * 2. 标签**可跨大文件夹定义**（标签视图里每行显示它覆盖了哪些文件夹）；
 * 3. 标签下**可以直接起对话**（标签行上有「在此标签下提问」，并带检索语法输入）；
 * 4. **知识库界面不做搜索**（这一页没有搜索框；搜索发生在"提问"那一侧）；
 *    ⚠⚠ **2026-09-20 就地翻案（P2 头条，本轮任务书要求）**：本页现在**有**一个搜索框。
 *    留痕（本仓规矩：错话保留 + 更正在后，不许悄悄删）：
 *      · **曾如此**：业主 2026-09-19 的 13 条里第 4 条明确"知识库界面不做搜索"，
 *        当时连**断言**都钉死了（`smoke-kb-page-render.mjs` 的 9 号断言"本页没有搜索框"）。
 *      · **现在**：本轮任务书直接要求"列表上方加一个搜索框（宿主 Input），**必须真的过滤**
 *        （按标准号或名称）"，并给了验收（输入只命中 1 行的串 ⇒ 行数真的变成 1；清空 ⇒ 恢复）。
 *      · **口径的差别（不拿它当挡箭牌，只是把事实写清）**：参照 WeKnora 那个框是
 *        "搜索**文档名称**…"的**本地列表过滤**（只筛已加载的这一列），**不是**语料级检索；
 *        我们做的也是这一种（`useMemo` 里对 `no`/`name` 做 includes，**一个接口都没调**）。
 *      · **旧断言没有"绕过去"，是被换成更强的**：9 号断言（数 placeholder 里有没有"搜索"）
 *        ⇒ 换成"输入只命中 1 行的串，行数真的变 1；清空真的恢复"（行为级）。
 *        见 `plugin/scripts/smoke-kb-page-render.mjs` 的 9/9b/9c 三条。
 *        ⚠⚠ **2026-09-20 P2 复核打回（D5）：上面这句是错的，就地更正（不删原话）。**
 *           **曾如此（错的）**：写的是"该文件里的 **9/9b/9c 三条**"。**实测**：9 号已被删，
 *           新增的是 **3g / 3h**（复核打回前该文件 `check(` 行 33 条、运行时 `PASS (33/33)`；
 *           本批加 2 条后是 **35/35**，里面没有 9/9b/9c 这种编号）。
 *           这句错话与 P2 复核的 D6（"断言条数 26 → 31"实为 **26 → 33**）是同一类错：
 *           数字/编号是**转述**的，没有回文件数一遍。⇒ 更正后的说法就是上面那两个名字。
 *      · ⚠ **需要业主复核 → 2026-09-20 已由业主本人结案（结论：保留）**。
 *        **曾如此**：这里写着"若他不同意，删掉 `.ks-search` 那一段并把断言换回去即可"。
 *        **现在**：业主 2026-09-20 亲口说「**搜索框：保留**」⇒ 本页的搜索框是**业主确认过的**，
 *        不再是"任务书要求、业主未表态"的翻案态；台账 [NOT-DOING 第 13 条](../docs/NOT-DOING.md)
 *        已同步改成"业主 2026-09-20 明确：保留"。退回步骤**保留在台账里**（仍然可执行、仍然不许
 *        把断言换回"本页没有搜索框"那种已证伪的假绿），但**不再是待办**。
 *        ⚠⚠ **2026-09-20 P2 复核打回（C）：上一句"把断言换回去"是**不可执行**的、且换错方向。**
 *           （这段打回针对的是**上面那块被结案的原话**，原话仍保留在上面，不许因为"结案了"就删掉。）
 *           复核逐字走了一遍 ⇒ `ReferenceError: needle is not defined`、smoke exit 1、页面崩：
 *           那段错话漏掉了 5 个落点（`listed` 的 useMemo 里 `hitSearch(d)` 与 `[needle]` 依赖、
 *           空态里的 `search.trim()`、`pickSearch('')`、`.ks-search` 样式、`IconSearchOutline16`
 *           的 import）。**更正**：完整、逐落点、**已亲自走通**的退回步骤在
 *           `docs/NOT-DOING.md` 第 13 条；那里同时写明"**不许**把断言换回'本页没有搜索框'
 *           （那是已证伪的假绿）"，以及搜索框存在/缺席由 `KB_PAGE_SEARCH` 声明 + 断言锚住。
 *   4b. **5i（2026-09-20 收尾批）：搜索框改成"每一层常驻"** —— 业主本轮只说"搜索框：保留"、
 *       **没限定层级** ⇒ 按"保留"的最强解释执行：库根 / 一级目录 / 二级目录 / 文件层**都有**，
 *       且**位置同构**（目录层在目录卡上方、文件层在筛选条与表格之间，都是"紧贴这一层的条目区"）。
 *       目录层过滤**目录名**（不命中给 `没有符合搜索的目录` 空态 + "清除搜索"）；文件层行为不变
 *       （按 `no`/`name` 过滤）。**搜索词的处置口径**（本批自定，写在这里就是唯一所有者）：
 *         · **切库（点另一张卡）⇒ 清空** —— 整棵树都换了，留着是对新库的"幽灵过滤"；
 *         · **同一库内下钻 / 返回上一级 ⇒ 保留** —— 它是**页面级**的一个过滤条件，层级切换后
 *           继续生效（目录层按目录名、文件层按标准号/名称），框里始终看得见那个词；
 *         · **切状态筛选档 ⇒ 保留** —— 筛选与搜索是**AND**关系（`listed` 里两个条件同时过滤），
 *           互不清空；只有**换目录/换库**才清选择（见 `pickFilter`/`pickSearch`/`enterKb`）。
 *       这三条都有渲染级断言（`smoke-kb-page-render.mjs` 2h–2k），不是只写在注释里。
 * 5. 只留**一个「＋ 新建」**按钮（下拉里是"新建文件夹 / 导入文件"）；
 * 6. 「公司制度」这类**自建夹与自带两棵树平级**（三段式布局里排在树下面同一列）；
 * 7. 详情里加**发布日期 / 生效日期 / 废止日期**；
 * 8. **不做"领域标签"自动打标签**（详情里只显示用户自己打的标签）；
 * 9. 文件名前有**选择框**，列表头有**全选**；
 * 10. 选中后出现**悬浮批量条**：已选 X 项 / 取消选择 / 批量打标签 / 移动到目录 / 批量删除；
 * 11. 每行文件名后**常驻「＋标签」**按钮（不是 hover 才出现，只是 hover 时更显眼）；
 * 12. 检索语法 `安全+半导体-冶金`：`+` = 并且，`-` = 屏蔽（在"在此标签下提问"的框里当场解析回显）；
 * 13. 与 DSH 同风格：全部用**宿主自己的原语**（`Button`/`Checkbox`/`Tag`/`Pill`/`Input`/`Menu`），
 *     颜色走活的 `--dsw-alias-*` token ⇒ **深浅两套配色自动跟随**，我不写两套色值。
 *
 * ## 2026-09-20 5h：**信息架构（IA）重构 —— 业主当天亲口定的形态**
 * 业主原话（**这就是验收标准**）：
 *   「搜索框：保留。**B 不分页**（知识库卡片尺寸统一不要展示目录树，我建的（真文件夹；与上面两棵平级）
 *    这种乱七八糟东西删了，然后**所有卡片横在顶端**，**一个小框下面自带一个左右翻页滑动条**，
 *    **下面是文件目录**，**点一个卡片就出来知识库内容**，比如点法律法规，就按目录展示，
 *    **先占上一级目录文件夹，然后点开是二级目录，进入二级目录就自动出现返回上一级的按钮**）」
 * 落成 4 条（逐条对照施工，别自己发挥）：
 *   1. **顶部一条卡片带**：`KNOWLEDGE_BASES`（标准 / 法律法规 / 3 个自建夹）**统一尺寸、横向**排在一个
 *      框（`.ks-kbband`）里，全部卡片一次渲染进一个**原生横向滚动容器**（`.ks-kbband-clip`，
 *      `overflow-x:auto` + `scroll-snap-type:x mandatory`）⇒ 用户能**直接拖那条滑动条**；
 *      框两端各一个箭头（`.ks-kbband-nav`），点一下 `scrollBy` 一屏（≈一张卡）。
 *      到两端时对应箭头 `disabled`；**量不到布局的链**（jsdom 截图链）保持可用
 *      —— 见 `BAND_STEP_PX` / `hasLayout` 的注释（5h-补 把窗口切片换成了真滚动）。
 *   2. **不再展示目录树**：`renderNodes` / `LibCard` / `.ks-kb-tline` 那一套（连同它的展开状态
 *      `open` / `toggle`）**已删**；「我建的（真文件夹；与上面两棵平级）」这句标签**已删**（业主点名的
 *      "乱七八糟东西"）。**删了什么、为什么**记在 docs/UI-BASELINE.md 的 5h。
 *   3. **下面是文件目录**：P2 头条那张真表格（`COLUMNS` + `--ks-cols` + 搜索 + 筛选 + 批量条 + 行尾 ⋮）
 *      **结构一字未改**，只是现在**只出现在"最末一级"**（业主："到最末一级才是文件"）。
 *      ⚠ 搜索框**仍在**（业主今天明确"保留"）。**5i 起它不再只待在文件层**（见上面第 4b 条）：
 *        每一层常驻；文件层这一支的位置与行为**没动**（仍在筛选条与 `.ks-list` 之间，只过滤文件）。
 *        口径与 NOT-DOING 第 13 条同步（业主已确认保留；层级口径 = 每层常驻）。
 *   4. **点卡片 = 进入该库 + 按目录逐级下钻**：`path` 是当前路径（从库根往下的节点 key）；
 *      `path.length === 0` = 库根（显示**一级目录**）；点开某个目录 = 下钻一级；
 *      **进入任何下一级**（`path.length > 0`）就出现「← 返回上一级」按钮 + 面包屑（`.ks-crumb`）；
 *      走到**没有子节点的节点**才是文件表格。
 *      ⚠ **层级以现有占位数据为准，没有新造一级数据**（业主："不许凭空发明新数据"）。实读结果：
 *        · `STD_TREE`：**3 级** —— P 土木、建筑 → P15/19… → P16 工程防火（文件在此）；
 *          C/Z 两支只有 **2 级**（大类 → 区间/类目 = 文件所在层）。
 *        · `LAW_TREE`：**3 级** —— 法律/行政法规 → 宪法与行政法 → 安全生产（文件在此）。
 *        · `USER_FOLDERS`：**1 级** —— 夹子下**直接**是文件，**没有子目录可下钻**（如实说明，不补数据）。
 *      ⇒ 因此本页的下钻是**按真实层级走到底**（业主的"一级 → 二级 → 文件"在 C/Z 两支与用户的
 *        两级数据上逐字成立；P / 法律法规两支是三级 —— 那是数据本来的级数，不是多做了一层）。
 *
 * ## 设计依据（非我杜撰）
 * 业主定调：「**法规标准的几级目录应该是对应知识库文件夹的不同层文件夹名**」。
 * ⇒ 树里每一层**就是**文件夹层级，且层级名来自分类法：标准 = CCS 大类 → CCS 区间 → CCS 类目；
 *   法规 = 效力层级 → 法律部门 → 业务领域。后端 `GET /api/v1/documents/categories` 已在产出
 *   这条路径（`doc_catalog.classify_document`），所以这页将来是**接线**，不是重画分类法。
 *
 * ## 已知的诚实缺口（别当成 bug 去"修"）
 * - 「＋标签」「批量打标签」只是把标签加进本地状态，**没有写进任何库**；
 * - 「导入文件」是不可用的占位项（真入口在 `params.page === 'ingest'` 那页）；
 * - 树里的文档集合是手写的样例，不是真实索引。
 */

import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Button, Checkbox, IconArchiveOutline20, IconChecklistOutline14, IconChevronDownOutline14, IconChevronLeftOutline14, IconChevronRightOutline14, IconEllipsisOutline16, IconFolderOpenOutline16, IconInfoOutline14, IconInspectOutline12, IconListPenOutline16, IconPlusOutline16, IconSearchOutline16, IconShieldOutline16, IconTrashOutline16, Input, Menu, Pill } from '@deepseek-ai/dsh-client-ui-primitives'

import { ensureKsStyles } from './ksGuideStyles'
import { KsCapabilityPage } from './KsCapabilityPage'
import { describeKsQuery, parseKsQuery } from './ksSearchSyntax'
import type { KsPaneBodyProps, KsKbInjected } from './ksSidebar'
import { KS_KB_KIND } from './ksSidebar'

/**
 * **本页有没有那个搜索框**（P2 头条，2026-09-20）——这是"搜索框在 / 不在"的**唯一声明**：
 * `plugin/scripts/smoke-kb-page-render.mjs` 断言「DOM 里有没有 `.ks-search input`」与这个值**一致**，
 * 并且**逐层**断言（库根 / 一级目录 / 二级目录 / 文件层各一次）。为什么需要它（复核
 * `verify-freeze-p2` 的 C 条）：旧的 9 号断言（"本页没有搜索框"）被删掉之后，**搜索框的
 * 存在/缺席一度没有任何断言盯着** —— 悄悄删了它不会有任何一条红。
 *
 * ⚠⚠ **5i（2026-09-20 收尾批）改名 + 扩层，就地留痕**：
 *   · **曾如此**：常量名是 `KB_FILE_VIEW_SEARCH`，注释写"**本页文件视图里**有没有那个搜索框"，
 *     并且**只有文件层**渲染它。名字与含义在当时是对的。
 *   · **现在**：业主 2026-09-20 只说"搜索框：保留"、**没限定层级** ⇒ 本批按"保留"的**最强解释**
 *     执行：**每一层常驻**（库根 / 各级目录层 / 文件层），目录层过滤**目录名**、文件层过滤
 *     标准号/名称。⇒ 名字里的 `FILE_VIEW` 已经**不成立**，改名为 `KB_PAGE_SEARCH`（名字 =
 *     含义；这是本批"修注释与代码不符"的同一条纪律）。旧名**不再保留别名**（避免两处声明）。
 *   · 断言落点：jsdom 冒烟在**每一层**都要看到那个框（见该文件 2h–2k），文件层另外还判
 *     "在/不在 == 这个声明"（3g）—— 两个方向都钉住，删了框或悄悄停掉某一层都会红。
 *
 * ⚠ **退回给业主 2026-09-19 的旧设计**（"这一页不做搜索"）时：把这里改成 `false`，
 *   并按 `docs/NOT-DOING.md` 第 13 条那份**可执行**步骤逐条删（本文件 + ksGuideStyles.ts +
 *   渲染级冒烟）；**不要**把断言换回"本页没有搜索框"那种数 placeholder 的写法（已证伪的假绿）。
 */
export const KB_PAGE_SEARCH: boolean = true

/** 效力状态（决定 Tag 的色调 + 详情里的日期口径）。 */
type Status = 'current' | 'upcoming' | 'withdrawn' | 'superseded'

/** 一篇文档（占位）。日期用 ISO 串，方便将来直接接后端字段。 */
interface MockDoc {
  readonly id: string
  /** 所属文件夹的 key（与树/自建夹的 key 对应）。 */
  readonly folder: string
  /** 标准号/文号；法规类没有号就空串。 */
  readonly no: string
  readonly name: string
  readonly status: Status
  readonly published: string
  readonly effective: string
  /** 只有废止/被替代才有；现行件为空串。 */
  readonly withdrawn: string
  /** 用户自己打的标签（**没有自动领域标签**）。 */
  readonly tags: readonly string[]
}

/** 目录节点。`key` 是**全路径**，不是名字 —— 见下面 `hasDuplicateName` 的注释。 */
interface MockNode {
  readonly key: string
  readonly name: string
  readonly children?: readonly MockNode[]
}

/**
 * 效力的**呈现分档**（P1-5，2026-09-20）：状态徽章从宿主的实心 `Tag` 换成我们自己的
 * `.ks-status`（浅底 + 1px 描边 + 同色系文字）。改的原因是实测像素：Tag 量到 **37×13** 的
 * 实心块、**没有任何 1px 边色行**，而参照真机 `23-kb-detail-list-1440.png` 是 **46×20**、
 * 左右各一条 1px 描边（见 docs/research/weknora-ui-vs-ours.md §7.1 的 scan 线）。
 * 三档颜色全部由宿主 `--dsw-alias-state-*` 解出（**没有一个字面色值**）：
 *   ok  = success-tertiary 底 + success-primary 描边/文字
 *   warn= warn-tertiary 底 + warn-label 描边/文字
 *   bad = error-secondary 底 + error-primary 描边/文字
 *   ⚠⚠ **2026-09-20 P2 复核打回（A）：上面这条 bad 是错的，就地更正。**
 *      **曾如此（错的）**：`bad = error-secondary 底 + error-primary 文字`。
 *      **实测（真 Chrome + PNG 数像素）**：dark 下 `state-error-secondary` 与 `-primary`
 *      **解出来是同一条 token**（都 = red-400 `rgb(242,90,90)`）⇒ 徽章是整块纯色，
 *      **可辨文字 0 个**（深色下「已废止」读不出来）；light 也只有 1.37 对比度。
 *      ⇒ 现在 bad 的底走 error 系里**唯一**的浅底 token `--dsw-alias-interactive-bg-hover-danger`
 *      （light 4.14 / dark 4.70）。理由、证据与"这不是 P2 回归、是 P1-5 起就有的"写在
 *      `ksGuideStyles.ts` 的 `.ks-status-bad` 上面（单一所有者，别在这里重抄一遍）。
 * ⚠ **语义一个字没动**（现行/即将实施/已废止/被替代四个词的映射原样保留）。
 */
const STATUS: Record<Status, { cls: string; text: string }> = {
  current: { cls: 'ks-status ks-status-ok', text: '现行' },
  upcoming: { cls: 'ks-status ks-status-warn', text: '即将实施' },
  withdrawn: { cls: 'ks-status ks-status-bad', text: '已废止' },
  superseded: { cls: 'ks-status ks-status-neutral', text: '被替代' },
}

/**
 * 状态筛选档（P1-4，2026-09-20）。
 *
 * ⚠ **克制的边界**：只做"全部 / 现行 / 已废止"三档 —— 因为**只有它们跟页面里真实存在的
 * 占位数据对得上**（`MockDoc.status` 的四个取值）。不许发明我们没有的数据维度
 * （来源 / 类型 / 日期区间都是编的，业主会一眼看出来是假筛选）。
 *
 * ⚠ "已废止"这一档**故意含两个状态**：`withdrawn`（已废止）与 `superseded`（被替代）——
 * 理由写在下面对账表里：后端把这两类都算"不可用"，而分开做两个胶囊在 3 档的克制范围里
 * 会让"现行 / 已废止"的对账看起来多出一档没人用。文案用"已废止"是对齐业主的用词。
 * `test` 返回 true = 这一篇**留在列表里**。
 */
const FILTERS: readonly { readonly id: string; readonly text: string; readonly test: (d: MockDoc) => boolean }[] = [
  { id: 'all', text: '全部', test: () => true },
  { id: 'current', text: '现行', test: (d) => d.status === 'current' },
  { id: 'withdrawn', text: '已废止', test: (d) => d.status === 'withdrawn' || d.status === 'superseded' },
]

/**
 * 表格的**列定义**（P2 头条，2026-09-20）—— 表头与每一行**共用这一份**。
 *
 * 为什么要有这个常量（而不是表头写一遍、行里再写一遍）：P2 头条的验收就是"列对齐"，
 * 而"各写一套"正是列错位的唯一来源。这里 `COLUMNS` 是**列身份**的单一所有者：
 * 表头 `COLUMNS.map(...)`、行 `COLUMNS.map(...)`，两边的 cell 类名序列**必然逐字相同**；
 * 列**宽度**的单一所有者是 `.ks-list` 上的 `--ks-cols`（表头与行都只写
 * `grid-template-columns:var(--ks-cols)`，见 ksGuideStyles.ts）。
 * 渲染级冒烟据此断言"表头 cell 类名序列 === 行 cell 类名序列"（结构性，不是字符串级）。
 *
 * 列**只按页面里真有的字段定**（`MockDoc`），对照参照 WeKnora `23` 的 6 列：
 *   | 参照列 | 我们 | 来自哪个字段 |
 *   |---|---|---|
 *   | 文件名 | ✔ 文件名（两行：名 + 标准号） | `name` / `no` |
 *   | 标签   | ✔ 标签（行内可见 chip） | `tags` |
 *   | 状态   | ✔ 效力 | `status` |
 *   | 更新时间 | ✔ 生效日期（**不冒充"更新时间"**） | `effective` |
 *   | 来源 / 大小 | ✗ **没做**：我们没有这两个字段，不许编 |
 * 发布日期 / 废止日期 仍在详情卡里（那是业主点名要的三个日期，不塞进表里抢宽度）。
 */
const COLUMNS = [
  { key: 'name', cls: 'ks-col-name', head: '文件名' },
  { key: 'status', cls: 'ks-col-status', head: '效力' },
  { key: 'date', cls: 'ks-col-date', head: '生效日期' },
  { key: 'tags', cls: 'ks-col-tags', head: '标签' },
  // 行尾操作列：**没有列头**（参照里它也是 hover 才出现的三个点，不占表头文案）
  { key: 'more', cls: 'ks-col-more', head: '' },
] as const

/** `COLUMNS` 的键联合类型（让 `renderCell` 的 switch 是穷尽的）。 */
type ColKey = (typeof COLUMNS)[number]['key']

/**
 * **目录层**的列定义（业主 2026-09-20 头条：目录视图要**和文件列表同构**、**同一套列表机制**）。
 *
 * 与 `COLUMNS` **同构**（同一种写法、同一种用法）：表头 `DIR_COLUMNS.map(...)`、行
 * `DIR_COLUMNS.map(...)`，两边的 cell 类名序列**必然逐字相同**；列**宽度**的单一所有者仍然是
 * `.ks-list` 上的 `--ks-cols` —— 目录层给 `.ks-list` 一个**自己的** `--ks-cols`
 * （`.ks-list-dirs` 那条规则；**同一机制、不同列数**），`DIR_COLUMNS` 自己**不写宽度**。
 *
 * 列**只按目录真有的字段定** —— 我们的目录（`MockNode`）只有**名称**与**这一棵子树的篇数**
 * （`countUnder`），**没有**更新时间 / 来源 / 大小：
 *   | 列 | 来自哪个字段 | 列头 |
 *   |---|---|---|
 *   | 目录名（两行里的第 1 行 = 名称，第 2 行 = 整条路径） | `name` / `key` | 目录 |
 *   | 这一棵下的篇数 | `countUnder(child)`（真算出来的树计数） | 篇数 |
 *   | 进入提示 | 无字段（固定字形） | （无列头） |
 *
 * ⚠ **列数只有 3**（文件层是 5）—— 这是"同构 ≠ 同宽"的落点：同一种机制、同一套类、
 *   同一条行高 token（看 css），但列模板按**目录真有的字段**给。**不许**为了凑成 5 列
 *   给目录编"更新时间/来源/大小"（我们没有那些字段；编出来就是假数据）。
 * ⚠ 列头里**没有"文件名"那一列**：目录层的第一列叫「目录」（它装的是目录，不是文件）——
 *   借用"文件名"当列头是把事实说错。同样地，第三列的列头是**空串**（参照里那一列也是
 *   无字形的操作位，不占文案），与 `COLUMNS` 的 `more` 列**同一种写法**。
 * ⚠ 列类名与文件层**不重用**（`ks-col-dname` / `ks-col-dcount` / `ks-col-dgo`，
 *   文件层是 `ks-col-name` / `ks-col-status` / `ks-col-date` / `ks-col-tags` / `ks-col-more`）：
 *   两层的行都挂在 `.ks-item` 上，重用类名会让"列身份"在两层之间串味（同一个类在两层
 *   指向不同的东西）—— 那是本仓反复抓过的"身份漂移"。类名不同，机制相同。
 */
const DIR_COLUMNS = [
  { key: 'dname', cls: 'ks-col-dname', head: '目录' },
  { key: 'dcount', cls: 'ks-col-dcount', head: '篇数' },
  // 行尾"进入提示"列：**没有列头**（与 COLUMNS 的 more 列同一种写法）
  { key: 'dgo', cls: 'ks-col-dgo', head: '' },
] as const

/** `DIR_COLUMNS` 的键联合类型（让目录行的 `switch` 是穷尽的）。 */
type DirColKey = (typeof DIR_COLUMNS)[number]['key']

/**
 * 行内**文件图标**（P2 头条）：从**已有字段 `no`** 推出来的呈现档 ——
 * **没有新字段、没有编数据**（不是"来源/大小"那种我们没有的东西）：
 *   `no === ''`      → 法律法规（法律/行政法规本来就没有标准号）→ 盾
 *   `no` 以 GB 开头  → 国家标准/行业标准（一份条款清单）        → 清单
 *   `no` 以 KS- 开头 → 公司制度 / 内部规程（写出来的文本）      → 文档+笔
 *   其余（QR-…）     → 资料 / 记录（归档件）                    → 归档盒
 * ⚠ 四个字形都是**宿主的真实导出**，逐个在检出 `ui-primitives/lib/index.js` 里核过
 *   "const 定义 + export 列表"都在（这个包是 external，名字写错**不会构建失败**、
 *   只会运行时 undefined ⇒ 必须读产物确认，见 ksHostPrimitives.d.ts 的那条边界）。
 * ⚠ 它是**装饰性**的（同一目录下常常四行同形 —— 参照的三行也同形），作用是扫读锚点，
 *   不是"靠图标区分类型"；类型文字在 `title=` 里，鼠标停一下能看到。
 */
function docGlyph(no: string): ReactNode {
  if (no === '') return <IconShieldOutline16 />
  if (/^GB/i.test(no)) return <IconChecklistOutline14 />
  if (/^KS-/i.test(no)) return <IconListPenOutline16 />
  return <IconArchiveOutline20 />
}

/** 图标档的**中文说明**（挂在 `title=` 上，不占用行内一列宽度）。 */
function docGlyphLabel(no: string): string {
  if (no === '') return '法律法规'
  if (/^GB/i.test(no)) return '标准'
  if (/^KS-/i.test(no)) return '公司制度 / 规程'
  return '资料 / 记录'
}

/** 自带「标准」树（层级名取自 `doc_catalog.py` 的权威 CCS 表，不是编的）。 */const STD_TREE: readonly MockNode[] = [
  {
    key: 'P 土木、建筑',
    name: 'P 土木、建筑',
    children: [{
      key: 'P 土木、建筑/P15/19 工程抗震、工程防火、人防工程',
      name: 'P15/19 工程抗震、工程防火、人防工程',
      children: [{ key: 'P16 工程防火', name: 'P16 工程防火' }],
    }],
  },
  {
    key: 'C 医药、卫生、劳动保护',
    name: 'C 医药、卫生、劳动保护',
    children: [{ key: 'C65/74 劳动安全技术', name: 'C65/74 劳动安全技术' }],
  },
  {
    key: 'Z 环境保护',
    name: 'Z 环境保护',
    children: [{ key: 'Z60/79 污染物排放标准', name: 'Z60/79 污染物排放标准' }],
  },
]

/** 自带「法律法规」树（效力层级 → 法律部门 → 业务领域）。 */
const LAW_TREE: readonly MockNode[] = [
  {
    key: '法律',
    name: '法律',
    children: [{
      key: '法律/宪法与行政法',
      name: '宪法与行政法',
      children: [{ key: '安全生产', name: '安全生产' }],
    }],
  },
  {
    key: '行政法规',
    name: '行政法规',
    children: [{
      key: '行政法规/宪法与行政法',
      name: '宪法与行政法',
      children: [{ key: '行政法规/宪法与行政法/安全生产', name: '安全生产' }],
    }],
  },
]

/**
 * 自建夹（业主例子「公司制度」）；与上面两棵树**平级**。
 *
 * ⚠ 这里原来写着一条**与代码不符**的断言（5i 2026-09-20 收尾批核实后就地更正，
 *   原话保留在下面，不许悄悄删）：
 *
 *   **曾如此（错话，原文）**：「这里顺带修了一个**真 bug**（原版）：树的展开状态原本以
 *   `node.name` 为键，而「宪法与行政法」在两棵法律分支下**重名** ⇒ 点一个会把另一个也展开/收起，
 *   且文档会挂到错误的分支。改成以**全路径 key** 为键。」
 *
 *   **实测（读数据 + 读用键的每一处）**：
 *   · "以 `key` 为身份、不再以 `name` 为身份" —— **这半句是真的**：`nodeAtPath`/`pathNames`
 *     （按 `child.key` 找）、`enterKb`/`enterDir`/`goUp`（`path` 存 key）、`folder = node.key`
 *     与 `MockDoc.folder` 的对应，全部只认 `key`。重名确实因此被化解：两处「宪法与行政法」的
 *     key 不同（`法律/宪法与行政法` vs `行政法规/宪法与行政法`），两处「安全生产」的 key 也不同
 *     （`安全生产` vs `行政法规/宪法与行政法/安全生产`）—— 现有数据里**没有一对 key 相等**。
 *   · "**全路径** key" —— **这半句是假的**：key 的形态**不统一**。`STD_TREE` 的**叶子**全是裸名
 *     （`P16 工程防火` / `C65/74 劳动安全技术` / `Z60/79 污染物排放标准`），`LAW_TREE` 的
 *     「法律」支叶子也是裸名（`安全生产`），只有「行政法规」支的叶子写成全路径
 *     （`行政法规/宪法与行政法/安全生产`）；中间层才是全路径（`P 土木、建筑/P15/19 …`）。
 *   · **为什么叶子是裸名**：`folder = node.key` 要**直接等于** `MockDoc.folder`
 *     （`SEED_DOCS` 里 d1..d15 的 `folder` 就是这些裸名）。⇒ 把叶子 key 改成全路径**会同时
 *     打断 15 篇占位文档的挂载**（要连同 `SEED_DOCS` 的 `folder` 一起改），而**功能上没有任何收益**
 *     （key 只要在**本库内唯一**即可 —— 叶子之间本来就不互相嵌套，裸名不会撞车）。
 *   · 另外「树的展开状态」这个 bug 描述的是**已经不存在的 UI**：目录树连同它的展开状态
 *     （`open`/`toggle`）在 5h 已被业主点名删除（见本文件顶部 5h 第 2 条）。⇒ 那段描述**是史话**，
 *     不是当前代码的说明。
 *   ⇒ **结论：改注释（不是改代码）**，并且从此把这条契约写成可核的原话：
 *     「`key` 是**身份**（本库内唯一），**不保证是全路径**；叶子的 key 必须逐字等于
 *      `MockDoc.folder`。」动手改叶子 key 前先看这条。
 *   这类"用显示名当身份"的错，官方文档也点过（"Localized display text is never an identity"）。
 */
const USER_FOLDERS: readonly { readonly key: string; readonly name: string; readonly desc: string }[] = [
  { key: '公司制度', name: '公司制度', desc: '集团安全管理制度、责任制、考核办法' },
  { key: '内部操作规程', name: '内部操作规程', desc: '各车间岗位操作规程与作业指导书' },
  { key: '供应商资料', name: '供应商资料', desc: '供应商资质与检测报告' },
]

/** 占位文档集（含日期；`withdrawn` 只有废止/被替代才有值）。 */
const SEED_DOCS: readonly MockDoc[] = [
  { id: 'd1', folder: 'P16 工程防火', no: 'GB 50016-2014', name: '建筑设计防火规范', status: 'current', published: '2014-08-27', effective: '2015-05-01', withdrawn: '', tags: ['消防', '重点'] },
  { id: 'd2', folder: 'P16 工程防火', no: 'GB 55037-2022', name: '建筑防火通用规范', status: 'current', published: '2022-12-27', effective: '2023-06-01', withdrawn: '', tags: ['消防'] },
  { id: 'd3', folder: 'P16 工程防火', no: 'GB 50084-2017', name: '自动喷水灭火系统设计规范', status: 'current', published: '2017-05-27', effective: '2018-01-01', withdrawn: '', tags: ['消防', '水系统'] },
  { id: 'd4', folder: 'P16 工程防火', no: 'GB 50016-2006', name: '建筑设计防火规范（2006 版）', status: 'withdrawn', published: '2006-09-26', effective: '2006-12-01', withdrawn: '2015-05-01', tags: ['消防'] },
  { id: 'd5', folder: 'C65/74 劳动安全技术', no: 'GB 30871-2022', name: '危险化学品企业特殊作业安全规范', status: 'current', published: '2022-03-15', effective: '2022-10-01', withdrawn: '', tags: ['危化', '特殊作业', '重点'] },
  { id: 'd6', folder: 'Z60/79 污染物排放标准', no: 'GB 8978-1996', name: '污水综合排放标准', status: 'current', published: '1996-10-04', effective: '1998-01-01', withdrawn: '', tags: ['环保'] },
  { id: 'd7', folder: 'Z60/79 污染物排放标准', no: 'GB 3095-2012', name: '环境空气质量标准', status: 'upcoming', published: '2012-02-29', effective: '2026-01-01', withdrawn: '', tags: ['环保'] },
  { id: 'd8', folder: '安全生产', no: '', name: '中华人民共和国安全生产法', status: 'current', published: '2021-06-10', effective: '2021-09-01', withdrawn: '', tags: ['法律', '重点'] },
  { id: 'd9', folder: '安全生产', no: '', name: '中华人民共和国消防法', status: 'current', published: '2021-04-29', effective: '2021-04-29', withdrawn: '', tags: ['法律', '消防'] },
  { id: 'd10', folder: '行政法规/宪法与行政法/安全生产', no: '', name: '危险化学品安全管理条例', status: 'current', published: '2013-12-07', effective: '2013-12-07', withdrawn: '', tags: ['法规', '危化'] },
  { id: 'd11', folder: '公司制度', no: 'KS-AQ-001', name: '安全生产责任制管理办法', status: 'current', published: '2025-01-06', effective: '2025-02-01', withdrawn: '', tags: ['制度', '重点'] },
  { id: 'd12', folder: '公司制度', no: 'KS-AQ-014', name: '特殊作业审批与监护规定', status: 'current', published: '2025-03-18', effective: '2025-04-01', withdrawn: '', tags: ['制度', '特殊作业'] },
  { id: 'd13', folder: '公司制度', no: 'KS-AQ-003', name: '承包商安全管理规定', status: 'superseded', published: '2019-05-20', effective: '2019-06-01', withdrawn: '2025-04-01', tags: ['制度'] },
  { id: 'd14', folder: '内部操作规程', no: 'KS-CZ-021', name: '动火作业操作规程', status: 'current', published: '2025-02-11', effective: '2025-03-01', withdrawn: '', tags: ['规程', '特殊作业'] },
  { id: 'd15', folder: '供应商资料', no: 'QR-2025-018', name: '某检测机构资质与检测报告', status: 'current', published: '2025-06-02', effective: '2025-06-02', withdrawn: '', tags: ['供应商'] },
]

/** 「新建」下拉的项（文件夹是真的能做，导入走另一页）。 */
const NEW_ITEMS = [
  { id: 'folder', label: '新建文件夹（占位）' },
  { id: 'ingest', label: '导入文件…（去「文件导入」页）' },
] as const

/** 批量操作里"移动到"的目标（真实实现里应由后端给目录列表）。 */
const MOVE_TARGET = '公司制度'

/**
 * 卡片带**箭头一次滚多远**：一张卡的宽度（`.ks-kbband-clip` 的 `scrollBy` 步长）。
 *
 * ⚠ 这里**不再有"每屏几张"的常量**。业主 2026-09-20 原话是「一个小框下面自带一个**左右翻页
 *   滑动条**」，上一版把它实现成了**状态式翻页**（`BAND_WINDOW=3` + 窗口下标）：那一版**诚实标注**
 *   过"框内没有原生横向拖拽/滚动"，理由是要让箭头置灰态在 **jsdom**（离屏截图链，没有布局，
 *   `scrollWidth` 恒 0）里也确定。业主要的是**真的能拖/能滚** ⇒ 现在改成原生滚动容器：
 *     · 全部卡片一次渲染进 `.ks-kbband-clip`（`overflow-x:auto` + `scroll-snap-type:x mandatory`），
 *       每张卡固定宽度 `--ks-band-card-w`（"每屏几张"彻底从 CSS 里去掉，见 ksGuideStyles.ts）；
 *     · 箭头 = `scrollBy`（一屏/一张），**不再重渲染窗口**；
 *     · 置灰判据分两种环境（见 `hasLayout` 的注释）：**有布局**时按 `scrollLeft` 判两端；
 *       **没布局**（jsdom 截图链）时**保持可用** —— 那是渲染链限制，不是无脑放行。
 *   ⚠ 步长数 `184` 是"一张卡 + 一个 gap"（`--ks-band-card-w` 172 + `--ks-card-gap` 12）在 JS 侧的
 *     镜像 —— CSS 里**只有一个**卡宽定义（`.ks-kbband .ks-kb-card{flex:0 0 var(--ks-band-card-w)}`），
 *     这里只镜像它的**数值**、不再是"每屏几张"那种窗口口径。
 */
const BAND_STEP_PX = 184

/**
 * 顶层**知识库卡**——业主 2026-09-20：「**所有卡片横在顶端**」「**点一个卡片就出来知识库内容**」。
 *
 * ⚠ **全部来自现有占位数据，一个新库都没造**（业主："不许凭空发明新数据"）：
 *   · 标准     = `STD_TREE`（CCS：大类 → 区间/类目 → 类目）
 *   · 法律法规 = `LAW_TREE`（效力层级 → 法律部门 → 业务领域）
 *   · 剩下三张 = `USER_FOLDERS` 里**每一个**真文件夹各成一张卡（业主原话里的"各'我建的'合集"）
 * ⚠ 原来那句「**我建的（真文件夹；与上面两棵平级）**」的分组标签**已按业主原话删掉** ——
 *   所有库在卡片带里**同一种卡**，不再分"自带的"和"我建的"两组。
 */
interface KnowledgeBase {
  readonly id: string
  readonly name: string
  readonly desc: string
  /**
   * 这棵库的根节点。`key` 只用于遍历（文件层级用的是**节点自己的 key**，与 `MockDoc.folder` 同口径）。
   * ⚠ 两个自带库的根 `key` 写成 `kb:std` / `kb:law`（**没有任何文档挂在这两个 key 上**）——
   *   它们只是"根"，不是一个文件夹。
   */
  readonly root: MockNode
}

const KNOWLEDGE_BASES: readonly KnowledgeBase[] = [
  { id: 'std', name: '标准', desc: '国家标准·行业标准·团体标准', root: { key: 'kb:std', name: '标准', children: STD_TREE } },
  { id: 'law', name: '法律法规', desc: '法律 / 行政法规 / 部门规章 / 地方性法规', root: { key: 'kb:law', name: '法律法规', children: LAW_TREE } },
  ...USER_FOLDERS.map((f) => ({ id: f.key, name: f.name, desc: f.desc, root: { key: f.key, name: f.name } })),
]

/** 一个节点**自己 + 全部后代**的 key（用来数"这个目录下共有多少篇文件"）。 */
function subtreeKeys(node: MockNode): string[] {
  return [node.key, ...(node.children ?? []).flatMap((child) => subtreeKeys(child))]
}

/** 顺着 `path`（全路径 key 数组）走到当前节点；走不通就回落到当前位置（状态不该出现"走不通"）。 */
function nodeAtPath(root: MockNode, path: readonly string[]): MockNode {
  let node = root
  for (const key of path) {
    const next = (node.children ?? []).find((child) => child.key === key)
    if (next === undefined) return node
    node = next
  }
  return node
}

/**
 * 面包屑上要显示的**目录名**（不是 key）。
 * ⚠ 必须另走一遍取 `name`：`MockNode.key` 是"父/子"全路径（`法律/宪法与行政法`），
 *   直接展示会把面包屑弄成一串路径分隔符 —— 而且它正是当初修掉的"用显示名当身份"的反面病。
 */
function pathNames(root: MockNode, path: readonly string[]): string[] {
  const names: string[] = []
  let node = root
  for (const key of path) {
    const next = (node.children ?? []).find((child) => child.key === key)
    if (next === undefined) break
    names.push(next.name)
    node = next
  }
  return names
}

/** 详情里的一行字段（日期用同一套排版，免得每个字段各写一遍）。 */
function Field({ label, value, mono = false }: { readonly label: string; readonly value: string; readonly mono?: boolean }): ReactNode {
  return (
    <div className="ks-field">
      <span className="ks-field-k">{label}</span>
      <span className={mono ? 'ks-field-v ks-field-v-mono' : 'ks-field-v'}>{value === '' ? '—' : value}</span>
    </div>
  )
}

/**
 * 知识库 tab 的 body。
 *
 * @param props - 框架给的运行时 props（含 `useTabInfo`）与本插件注入的面。
 * @returns 知识库页；`params.page` 指向尚未实现的页时给**诚实的占位**。
 */
export function KsKnowledgePage({ useTabInfo, dataSource }: KsPaneBodyProps & KsKbInjected): ReactNode {
  ensureKsStyles()
  const { tab } = useTabInfo()
  const page = (tab.navigation.params as { page?: string } | undefined)?.page ?? 'manage'

  const [view, setView] = useState<'files' | 'tags'>('files')
  /**
   * 当前选中的知识库卡（业主："**点一个卡片就出来知识库内容**"）。
   * ⚠ 默认选中**第一张（标准）**并在它的**库根**（显示一级目录）：这样"下面是文件目录"从第一屏
   *   就是有内容的，而不是一块空白 —— 与 P2 及以前"默认停在某个目录"的行为一致（只是层级上移了一层）。
   */
  const [cardId, setCardId] = useState(KNOWLEDGE_BASES[0].id)
  /**
   * 目录下钻的**当前路径**（从库根往下的节点 key 数组）。业主原话：
   * 「先占上一级目录文件夹，然后点开是二级目录，进入二级目录就自动出现返回上一级的按钮」。
   * ⚠ `path.length === 0` = 库根（显示**一级目录**）；**没有子节点的节点** = 文件表格。
   */
  const [path, setPath] = useState<readonly string[]>([])
  /**
   * 卡片带那个**横向滚动容器**（`.ks-kbband-clip`）——箭头就是对它 `scrollBy`。
   * ⚠ 5h-补（2026-09-20）：原来这里是 `bandStart`（窗口起始下标 + `BAND_WINDOW` 切片）。
   *   业主原话要的是"**滑动条**"（真的能拖/能滚），所以窗口切片与那个下标**一起删了**：
   *   滚动位置是 DOM 自己的状态，React 侧只留一份"要不要置灰"的镜像（`bandLeft`）。
   */
  const clipRef = useRef<HTMLDivElement | null>(null)
  /**
   * 滚动位置的**镜像**（只在 `onScroll` 里更新，用来算箭头置灰）。
   * ⚠ 它**不是**布局的真源：真源是 DOM 的 `scrollLeft`（拖滚动条也会触发 `onScroll`）。
   */
  const [bandLeft, setBandLeft] = useState(0)
  /**
   * **这条渲染链有没有布局**。jsdom（`plugin/scripts/ui-render-shot.mjs` 的离屏截图链）没有布局引擎
   * ⇒ `scrollWidth`/`clientWidth` 恒为 0。判据写成"**有布局且真的溢出**才谈两端置灰"：
   *   · **有布局**（`scrollWidth > clientWidth`）：`scrollLeft <= 0` ⇒ 左箭头置灰；
   *     `scrollLeft >= scrollWidth - clientWidth - 1` ⇒ 右箭头置灰。**这是真机的判据**。
   *   · **没布局**（`scrollWidth === 0`）：**保持可用**。这是**渲染链限制**（量不出溢出方向），
   *     不是"无脑放行"——上一版为了绕开它才退化成窗口下标，代价是**框内根本不能滚**（业主否了）。
   *     截图链上箭头因此是**可用态**；置灰只能在**真宿主页**里看到。
   * ⚠ 写成"第一次量到布局就锁存"的 state 而不是每次渲染现读 DOM：现读的话，**没有后续重渲染时
   *   箭头会停在旧值上**（量完 DOM 就把它换掉，React 不会因为你换了 getter 就再渲染一次）。
   *   锁存之后 `hasLayout` 只会 false → true，永不回退（真机不会"布局突然消失"）。
   */
  const [hasLayout, setHasLayout] = useState(false)
  const measureBand = (): void => {
    setHasLayout((prev) => prev || (clipRef.current?.scrollWidth ?? 0) > 0)
  }
  const bandAtStart = hasLayout && bandLeft <= 0
  const bandAtEnd = hasLayout && clipRef.current !== null
    && bandLeft >= clipRef.current.scrollWidth - clipRef.current.clientWidth - 1
  /**
   * **挂载后探一次布局**：把上面那个锁存从 false 翻成 true（首帧 ref 还没挂上、布局也还没算完）。
   * ⚠ 在 jsdom（截图链）上探到的仍是 0 ⇒ 停在"没布局 ⇒ 箭头可用"那一支（见 `hasLayout` 的注释）。
   */
  useEffect(() => {
    measureBand()
  }, [])
  const [docs, setDocs] = useState<readonly MockDoc[]>(SEED_DOCS)
  const [selected, setSelected] = useState<ReadonlySet<string>>(() => new Set<string>())
  const [openDoc, setOpenDoc] = useState<string | null>(null)
  /** 行尾「⋮」溢出菜单**同一时刻只开一个**（存的是行的 id，不是布尔）。 */
  const [menuFor, setMenuFor] = useState<string | null>(null)
  /** 状态筛选（P1-4）：真的作用在 `listed` 上，不是画个壳。 */
  const [filter, setFilter] = useState('all')
  /**
   * 列表搜索串（P2 头条，2026-09-20）。
   * ⚠ 这是**本地列表过滤**（只筛当前层级已加载的条目）——**不是**语料检索：一个接口都没调。
   *   · **文件层**：按 `no`/`name` 做 includes（口径与参照 WeKnora 的"搜索文档名称…"一致）；
   *   · **目录层（5i 2026-09-20 起）**：按**目录名** `MockNode.name` 做 includes（见 `hitDirName`）。
   * ⚠ **业主 2026-09-20 明确"搜索框：保留"**（未限定层级）⇒ 它不再是"任务书要求、业主未表态"的
   *   翻案态；**层级口径 = 每一层常驻**（`KB_PAGE_SEARCH` 那一段有完整留痕）。
   * ⚠ **搜索词的处置口径**（唯一所有者在文件顶部第 4b 条）：切库清空 / 同库内下钻与返回上级保留 /
   *   切状态筛选保留。这三条各有渲染级断言，不许只改注释。
   */
  const [search, setSearch] = useState('')
  const [newOpen, setNewOpen] = useState(false)
  const [query, setQuery] = useState('')

  /* ── 当前库 / 当前节点 / 当前层级（全部**推导**出来，不另存一份 —— 免得两处状态打架） ── */
  const kb = KNOWLEDGE_BASES.find((card) => card.id === cardId) ?? KNOWLEDGE_BASES[0]
  const node = nodeAtPath(kb.root, path)
  const kids = node.children ?? []
  /**
   * **到最末一级了吗**：没有子目录的节点才是文件。
   * 业主："到最末一级才是文件（表格）"⇒ 有子目录时**只显示目录**，不把文件铺出来。
   * ⚠ 现有占位数据里**没有"既有子目录又有文件"的节点**（文件都挂在叶子上）；
   *   真有那种节点时这里会只显示目录 —— 登记为 5h 的诚实边界，不假装支持。
   */
  const atFiles = kids.length === 0
  /** 文件层级的目录 key —— 与 `MockDoc.folder` 同一口径（叶子节点的 key 就是文件夹名）。 */
  const folder = node.key
  /** 面包屑（库名 + 逐级目录名）。 */
  const crumb = [kb.name, ...pathNames(kb.root, path)].join(' / ')
  /**
   * 面包屑的**逐级条目**（业主 2026-09-20：「这种路径要**每一级都能点击跳转**」）。
   * `depth` 就是这个条目对应的 `path` 前缀长度：点它就 `enterDepth(depth)` ⇒
   *   第 0 条（库名）= 库根；第 k 条 = 第 k 级目录。
   * ⚠ 末条（`depth === path.length`）是**当前所在层级** ⇒ 渲染成**不可点的 `<span>`**
   *   （不是 disabled button：那仍是一个"按不动的按钮"，而它本来就不是按钮）。
   *   `.ks-crumb-item` 这一层是**所有条目共有**的类（渲染级冒烟按它逐级数、并判
   *   "只有末条不可点"）—— 点与不点因此是**同一份列表**里的两态，不是两套结构。
   */
  const crumbItems = [kb.name, ...pathNames(kb.root, path)]
    .map((name, depth) => ({ name, depth, current: depth === path.length }))

  /** 一个节点（含后代）下共有多少篇 —— 卡片/目录上的「N 篇」都用它。 */
  const countUnder = (target: MockNode): number => {
    const keys = new Set(subtreeKeys(target))
    return docs.filter((d) => keys.has(d.folder)).length
  }

  /**
   * 箭头：**一次滚一屏（≈一张卡）**，步长 `BAND_STEP_PX`（卡宽 + gap）。
   * ⚠ 先试 `clip.scrollBy`（宿主浏览器 / 真机都有，带 `behavior:smooth` 走 CSS 的动效档位）；
   *   **没有 `scrollBy` 的链**（jsdom 的 Element 没实现它，硬调会抛 "Not implemented"）⇒ 直接写
   *   `scrollLeft`。两条路都**真的改了滚动位置**，区别只在有没有平滑动画。
   * ⚠⚠ **目标位置自己夹到 [0, maxScroll]**：真机的 `scrollBy` 会自己夹住两端，但**不能指望**这一点
   *   （jsdom 那类实现不夹 ⇒ 连点右箭头会把 `scrollLeft` 累加到远大于可滚距离，图上/断言里都是假数）。
   *   量不出几何（`scrollWidth === 0`，jsdom）时**不滚**并**明确返回 false** —— 截图上"箭头点了没反应"
   *   本来就是这个环境的事实，不该伪造成"滚了很远"。
   */
  const scrollBand = (dir: -1 | 1): boolean => {
    const clip = clipRef.current
    if (clip === null) return false
    const max = clip.scrollWidth - clip.clientWidth
    if (max <= 0) return false
    const target = Math.max(0, Math.min(max, clip.scrollLeft + dir * BAND_STEP_PX))
    if (typeof clip.scrollBy === 'function') {
      clip.scrollBy({ left: target - clip.scrollLeft, behavior: 'smooth' })
    } else {
      clip.scrollLeft = target
    }
    setBandLeft(clip.scrollLeft)
    return true
  }

  /**
   * 点一张卡 = **进入该知识库**（业主原话），回到它的库根（一级目录），
   * 并把上一层的遗留状态清掉：选择 / 详情 / **搜索串** / 筛选档。
   * ⚠ **搜索串在这里清空**（5i 口径：**切库清空**）：整棵树都换了，留着就是对**新库**的幽灵过滤。
   *   同一库内下钻/返回上级**不清**（见 `enterDir` / `goUp`）—— 那是**页面级**的一个过滤条件。
   * ⚠ 不重置的是**卡片带的滚动位置**：用户刚点过的那张卡就在当前视野里，跳回最左会让卡片"跑掉"。
   */
  const enterKb = (id: string): void => {
    setCardId(id)
    setPath([])
    setSelected(new Set<string>())
    setOpenDoc(null)
    setSearch('')
    setFilter('all')
  }

  /** 进入一个子目录（下钻一级）—— 这是"点开是二级目录"那一步。搜索串**保留**（同库内）。 */
  const enterDir = (key: string): void => {
    setPath((prev) => [...prev, key])
    setSelected(new Set<string>())
    setOpenDoc(null)
  }

  /**
   * 「← 返回上一级」（业主："进入二级目录就自动出现返回上一级的按钮"）。
   * ⚠ 搜索串**保留**（5i 口径）：返回后它按**那一层的条目**继续过滤（目录层比目录名、文件层比
   *   标准号/名称）。代价是"上一层可能被这个词筛成空"—— 所以目录层给了明确的
   *   `没有符合搜索的目录` 空态 + 「清除搜索」，不装作那一层本来就没目录。
   */
  const goUp = (): void => {
    setPath((prev) => prev.slice(0, -1))
    setSelected(new Set<string>())
    setOpenDoc(null)
  }

  /**
   * 点**面包屑的第 i 级** ⇒ 直接跳回那一层（业主 2026-09-20：「这种路径要**每一级都能点击跳转**」）。
   *   · `i === 0` = 库名那一级 = **回到库根**（`path` 清空）、丢掉整条下钻路径；
   *   · `i === k`（k ≥ 1）= 回到第 k 级目录（保留前 k 段的 key）。
   * 口径与 `enterDir` / `goUp` **逐字一致**：清选择 + 清详情（换层后上一条选择里的行
   * 已经不在这份列表里，批量动作会作用在看不见的行上）、**保留搜索串**（5i：搜索是**页面级**
   * 的一个过滤条件，同库内下钻/返回都保留）。
   * ⚠ **只 slice、不信任 `i` 的边界**：`prev.slice(0, i)` 对负数与超长都不会抛
   *   （负数从末尾数、超长取整条）—— 但调用方只会在 `0..path.length` 上用它（见下面的渲染）。
   * ⚠ **当前所在那一级不渲染成按钮**（它是"你现在在这"）：见下面的 `crumbItems`。
   */
  const enterDepth = (i: number): void => {
    setPath((prev) => prev.slice(0, i))
    setSelected(new Set<string>())
    setOpenDoc(null)
  }

  /**
   * 当前**库**下的全部文件（标签视图用）。
   * ⚠ 标签是"**跨知识库文件夹定义**的"（业主 2026-09-19 第 2 条）⇒ 它统计**整个库**，
   *   而不是当前那一层目录里的文件。
   */
  const kbDocs = useMemo(() => {
    const keys = new Set(subtreeKeys(kb.root))
    return docs.filter((d) => keys.has(d.folder))
  }, [docs, kb])

  /** 当前**目录**（最末一级）里的全部文件 —— 筛选条的计数要用它做分母。 */
  const inFolder = useMemo(() => docs.filter((d) => d.folder === folder), [docs, folder])
  /** 筛选应用在它基础上（P1-4 的"真的作用在页面状态上"就是这个 useMemo）。 */
  const filterTest = (FILTERS.find((f) => f.id === filter) ?? FILTERS[0]).test
  /**
   * 搜索串（P2 头条）：**大小写不敏感**、按 `no` **或** `name` 命中（任务书的验收口径）。
   * 空白串 = 不筛（用户清空输入框就恢复全部）。
   */
  const needle = search.trim().toLowerCase()
  /** 搜索真的作用在**页面状态**上：行数跟着变（渲染级冒烟按"行数"断言，不按有没有那个框）。 */
  const hitSearch = (d: MockDoc): boolean => needle === ''
    || d.no.toLowerCase().includes(needle) || d.name.toLowerCase().includes(needle)
  const listed = useMemo(
    () => inFolder.filter((d) => filterTest(d) && hitSearch(d)),
    [inFolder, filterTest, needle],
  )
  /**
   * **目录层**的过滤（5i 2026-09-20）：按**目录名**（`MockNode.name`，用户看得见的那一串）
   * 命中，**不**拿 `key`/整条路径去比 —— 拿 key 比会让"搜 `P16`"在一个名字完全无关的层级上
   * 意外命中（`key` 里含父路径），那不是用户在找的东西。
   * ⚠ 它和文件层的 `hitSearch` 共用**同一个** `needle`（同一个搜索框、同一个词）。
   */
  const hitDirName = (name: string): boolean => needle === '' || name.toLowerCase().includes(needle)
  const kidsShown = useMemo(() => kids.filter((child) => hitDirName(child.name)), [kids, needle])
  const current = listed.find((d) => d.id === openDoc) ?? null

  /**
   * 换筛选档 ⇒ **清空选择**（P1-4 的"筛选变化即清空"）。
   * 为什么必须清：选择是按行 id 存的，筛选换一档后"已选 3 项"里可能有 2 项已经不在列表里，
   * 批量动作会作用在**看不见的行**上 —— 那是假动作。
   */
  const pickFilter = (id: string): void => {
    setFilter(id)
    setSelected(new Set<string>())
  }

  /**
   * 改搜索串 ⇒ **也清空选择**（P2 头条；任务书原话"搜索/筛选变化即清空选择"）。
   * 与 pickFilter 同一个理由：搜索把行筛没了之后，选择还指着看不见的行。
   * ⚠ 这里**不清 `openDoc`**（与 pickFilter 保持一致）：详情卡自己按 `listed` 取
   *   `current`，行被筛掉时它自然回落到"点 ⋮ → 详情"的提示，不需要额外状态。
   * ⚠ 也**不清状态筛选档`filter`**（5i 口径）：搜索与筛选是 AND 关系，两个条件同时留在 `listed` 上
   *   （清掉任一个都等于"用户没说过的重置"）。谁跟谁组合，渲染级冒烟有断言。
   */
  const pickSearch = (value: string): void => {
    setSearch(value)
    setSelected(new Set<string>())
  }

  /**
   * 换目录（下钻 / 返回上一级）**也要清空选择**。选择按"行 id"存，换了夹子之后
   * 上一条选择里的行已经不在这份列表里，批量动作会作用在**看不见的行**上。
   * 与 pickFilter 是同一个理由（筛选变化即清空）。
   * ⚠ 这段原叫 `pickFolder`（旧 IA 里点树节点换夹子）；新 IA 里换目录的两条路是
   *   `enterDir`（下钻）与 `goUp`（返回上一级），两者各自清选择 + 详情，见上面的定义。
   */

  /** 标签视图的数据**从文档状态推导**（这样"批量打标签"能立刻反映出来，不是死数据）。 */
  const tagRows = useMemo(() => {
    const map = new Map<string, { folders: Set<string>; n: number }>()
    for (const d of kbDocs) {
      for (const t of d.tags) {
        const row = map.get(t) ?? { folders: new Set<string>(), n: 0 }
        row.folders.add(d.folder)
        row.n += 1
        map.set(t, row)
      }
    }
    return [...map.entries()]
      .map(([name, row]) => ({ name, folders: [...row.folders], n: row.n }))
      .sort((a, b) => b.n - a.n || a.name.localeCompare(b.name))
  }, [kbDocs])

  const parsed = parseKsQuery(query)
  const parsedText = describeKsQuery(parsed)

  const allChecked = listed.length > 0 && listed.every((d) => selected.has(d.id))
  const toggleAll = (next: boolean): void => {
    setSelected((prev) => {
      const set = new Set(prev)
      for (const d of listed) {
        if (next) set.add(d.id)
        else set.delete(d.id)
      }
      return set
    })
  }
  const toggleOne = (id: string, next: boolean): void => {
    setSelected((prev) => {
      const set = new Set(prev)
      if (next) set.add(id)
      else set.delete(id)
      return set
    })
  }

  // 批量动作都作用在**本地状态**上（后端未接）。这样业主能真看到结果，而不是点了没反应。
  const tagSelected = (): void => {
    setDocs((prev) => prev.map((d) => (selected.has(d.id) && !d.tags.includes('待归类')
      ? { ...d, tags: [...d.tags, '待归类'] }
      : d)))
  }
  const moveSelected = (): void => {
    setDocs((prev) => prev.map((d) => (selected.has(d.id) ? { ...d, folder: MOVE_TARGET } : d)))
    setSelected(new Set<string>())
  }
  const deleteSelected = (): void => {
    setDocs((prev) => prev.filter((d) => !selected.has(d.id)))
    setSelected(new Set<string>())
    setOpenDoc(null)
  }

  // ── 「能力」页有自己的组件（业主指定的"一功能一卡一窗"） ──
  if (page === 'capabilities') {
    return <KsCapabilityPage />
  }

  // ── 其余非「知识库管理」页：诚实的占位（真入口，空内容） ──
  if (page !== 'manage') {
    const LABELS: Record<string, string> = { ingest: '文件导入', report: '效力报告', channels: '渠道台账' }
    return (
      // ⚠ 5j（2026-09-20）：外面这一层 `.ks-page` **只做 container-type**（页面留边的宽/窄两档
      //    靠它切；CSS 里容器不能用自己的宽度查自己，所以留边必须落在它的后代 `.ks-kb` 上）。
      //    它零内边距、零外边距 ⇒ 不是"盒子套盒子"，可用宽 = 页面根宽 − 2×留边，一分不多。
      //    ⚠ 里面的 JSX 缩进**保持原样**：本批只加这一层，不去重排既有代码的缩进（否则回读全是噪声）。
      <div className="ks-page">
      <div className="ks-kb">
        <div className="ks-kb-banner" title="本页只落了入口与外壳，数据是页面内的占位常量。">
          <IconInfoOutline14 />
          <strong>UI 先行，后端未接</strong>
        </div>
        <div className="ks-kb-card">
          <strong className="ks-kb-ct">{LABELS[page] ?? page}</strong>
          <div className="ks-kb-hint" style={{ marginTop: 6 }}>
            这一页尚未实现。它会落在同一个 tab 类型里（按 <code>params.page</code> 分发），
            所以入口现在是<strong>真的</strong>、内容是<strong>空的</strong>——而不是一个假按钮。
          </div>
        </div>
      </div>
      </div>
    )
  }

  /**
   * **那个搜索框**（`KB_PAGE_SEARCH` 是它存在与否的唯一声明）。
   *
   * ⚠ 5i（2026-09-20 收尾批）：**一份定义、两处渲染**（目录层在目录卡上方、文件层在筛选条与
   *   `.ks-list` 之间）—— 两处的**控件本体**是同一个 JSX 片段，所以"同一层只可能有一个框"、
   *   "两层不可能长得不一样"。占位/无障碍名**随层级变**（目录层搜目录名、文件层搜标准号/名称），
   *   因为同一个框在不同层过滤的东西**不是一回事**，用同一句 placeholder 就是骗用户。
   * ⚠ 为什么不做成"渲染一次、用 CSS 挪位置"：两处的位置分别由各自那一层的流决定（目录层在
   *   `.ks-dirs` 之前、文件层在 `.ks-filters` 之后），用绝对定位那套会把两个层的版式耦合起来 ——
   *   而本批的纪律是"文件层的版式一个字都不动"（5h 的图与实测值才还成立）。
   */
  const searchBox = KB_PAGE_SEARCH ? (
    <span className="ks-search">
      <Input
        icon={<IconSearchOutline16 />}
        value={search}
        placeholder={atFiles ? '搜索标准号或名称…' : '搜索目录名…'}
        aria-label={atFiles
          ? '在文件列表里按标准号或名称过滤（本地过滤，不检索语料）'
          : '在当前目录层按目录名过滤（本地过滤，不检索语料）'}
        onChange={(event) => { pickSearch(event.target.value) }}
      />
    </span>
  ) : null

  return (
    // ⚠ 5j（2026-09-20）：外面这一层 `.ks-page` **只做 container-type**（页面留边的宽/窄两档
    //    靠它切；CSS 里容器不能用自己的宽度查自己 ⇒ 留边落在它的后代 `.ks-kb` 上）。
    //    零内边距零外边距 ⇒ 不是"盒子套盒子"，可用宽 = 页面根宽 − 2×留边。
    //    ⚠ 里面 600 行的 JSX 缩进**保持原样**：本批只加这一层，不重排既有代码的缩进。
    <div className="ks-page">
    <div className="ks-kb">
      {/* 页面骨架（照 WeKnora 列表页：大标题 + 一行副标题 + 0.5px 分隔线；见 docs/UI-BASELINE.md 三）
          ⚠ 原来这里是"14px 粗体 + 右边一排按钮"的一行 —— 没有层级，标题和操作挤在同一视线高度上 */}
      <header className="ks-page-head">
        <div className="ks-page-title">知识库</div>
        <div className="ks-page-sub">
          法规/标准的落点：知识库 → 目录 → 条款 + 标签；颜色一律走宿主主题 token，深浅色自动跟随
        </div>
      </header>
      <div className="ks-page-rule" />

      {/* 诚实告知条（**降级版**，2026-09-20 P0-1）：它原来是 4 行橙底警告块，实测 520 下 92px 高、
          而页标题只有 26px ⇒ 抢戏。内容**一个字没删**（诚实告知），长句压成一行、细则全进 title=。
          参照等价物是 WeKnora config.png 那条单行带图标条。 */}
      <div
        className="ks-kb-banner"
        title={`交互是真的：勾选 / 全选 / 批量动作 / 打标签都作用在页面状态上，可以直接点着体验。`
          + `层级名取自 doc_catalog 的权威 CCS 表；将来这页接 GET /api/v1/documents/categories 即可，`
          + `不必重画分类法。dataSource=${dataSource}`}
      >
        <IconInfoOutline14 />
        <strong>UI 先行：数据是占位，后端接口未接</strong>
      </div>

      {/* 页内二级 tab（文件 / 标签）+ 唯一的「＋ 新建」（标题已上移到页面骨架） */}
      <div className="ks-kb-row">
        <div className="ks-subtabs">
          <Pill active={view === 'files'} onClick={() => { setView('files') }}>文件</Pill>
          <Pill active={view === 'tags'} onClick={() => { setView('tags') }}>标签</Pill>
        </div>
        <div className="ks-kb-grow" />
        <Menu
          open={newOpen}
          portal
          autoFocus
          align="end"
          items={NEW_ITEMS.map((item) => ({ id: item.id, label: item.label }))}
          onClose={() => { setNewOpen(false) }}
          onSelect={(id) => {
            setNewOpen(false)
            if (id === 'ingest') tab.actions.openTab(KS_KB_KIND, { replaceTab: true, params: { page: 'ingest' } })
          }}
          anchor={(
            <Button
              variant="primary"
              size="sm"
              aria-haspopup="menu"
              aria-expanded={newOpen}
              onClick={() => { setNewOpen((value) => !value) }}
            >
              ＋ 新建
              <IconChevronDownOutline14 />
            </Button>
          )}
        />
      </div>

      {/* ══ 顶部**卡片带**（业主 2026-09-20：「**所有卡片横在顶端**」「**一个小框下面自带一个
          左右翻页滑动条**」）══
          一个框（.ks-kbband）里：左箭头 + **横向滚动容器** + 右箭头。卡片来自 KNOWLEDGE_BASES
          （标准 / 法律法规 / 3 个自建夹），**同一种卡、同一尺寸**（`.ks-kbband .ks-kb-card` 一处
          钉死 `flex:0 0 var(--ks-band-card-w)` + 容器 `align-items:stretch` ⇒ 同排等宽等高）。
          ⚠ 5h-补（2026-09-20）：**全部卡片一次渲染**（不再 `slice` 窗口）⇒ 容器 `overflow-x:auto`
             + `scroll-snap-type:x mandatory` ⇒ 用户可以**直接拖/滚**那条滚动条（业主点名的"滑动条"）。
          ⚠ 箭头是**普通 button**（与 .ks-chip 同一个先例）：宽度要能钉成 `--ks-band-nav`(24px)，
            宿主 Button 的档位会被内容撑开（P1-6 量到过 28px），钉不住就量不出"翻页控件宽度"。
          ⚠ 能**量到布局**时按 `scrollLeft` 判两端置灰（`bandAtStart` / `bandAtEnd`）；
            量不到（jsdom 截图链，`scrollWidth === 0`）时**保持可用** —— 理由与边界见 `hasLayout` 的注释。 */}
      <div className="ks-kbband" role="group" aria-label="知识库（左右滚动切换）">
        <button
          type="button"
          className="ks-kbband-nav"
          aria-label="上一张知识库卡片"
          title={bandAtStart ? '已经在最左边' : '向左滚动一屏'}
          disabled={bandAtStart}
          onClick={() => { scrollBand(-1) }}
        >
          <IconChevronLeftOutline14 />
        </button>
        {/* ``tabIndex={0}`` + ``aria-label``：键盘用户能聚焦到这条**真的滚动条**上用 ←/→ 滚
            （原生滚动容器默认不可聚焦）——业主点名的"滑动条"要能被键盘也够到。 */}
        <div
          className="ks-kbband-clip"
          ref={clipRef}
          tabIndex={0}
          role="group"
          aria-label={`知识库卡片，共 ${KNOWLEDGE_BASES.length} 张，可左右滚动`}
          onScroll={(event) => {
            // ⚠ 每次滚动都顺手锁存"这条链有布局"：真机上第一帧布局就有值，这里只是把状态翻过来；
            //   jsdom 上永远是 0 ⇒ 箭头保持可用（见 `hasLayout` 的注释）。
            measureBand()
            setBandLeft(event.currentTarget.scrollLeft)
          }}
        >
          <div className="ks-kb-cards">
            {KNOWLEDGE_BASES.map((card) => {
              const on = card.id === kb.id
              return (
                <button
                  key={card.id}
                  type="button"
                  className="ks-kb-card"
                  data-on={on}
                  aria-pressed={on}
                  title={`进入「${card.name}」—— ${card.desc}`}
                  onClick={() => { enterKb(card.id) }}
                >
                  <span className="ks-kb-ct">{card.name}</span>
                  <span className="ks-kb-cd">{card.desc}</span>
                  <span className="ks-kb-foot">
                    <span className="ks-kb-badge">{countUnder(card.root)} 篇</span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>
        <button
          type="button"
          className="ks-kbband-nav"
          aria-label="下一张知识库卡片"
          title={bandAtEnd ? '已经在最右边' : '向右滚动一屏'}
          disabled={bandAtEnd}
          onClick={() => { scrollBand(1) }}
        >
          <IconChevronRightOutline14 />
        </button>
      </div>
      {/* 口径与事实一致：说的是**总张数**与两种滚法，**不再**报"第几张到第几张"（那是旧的窗口切片口径）。 */}
      <div className="ks-kb-hint">
        共 {KNOWLEDGE_BASES.length} 张 · 可左右滑动或点箭头翻页
      </div>

      {view === 'tags' ? (
        // ── 标签视图（取代收藏）：标签跨大文件夹；可在标签下直接起对话 ──
        <div className="ks-main" style={{ flex: '1 1 auto' }}>
          <div className="ks-lhead">
            <span className="ks-lhead-name ks-kb-grow">标签（跨知识库文件夹定义）</span>
            <span className="ks-kb-hint">{tagRows.length} 个</span>
          </div>
          <div className="ks-kb-hint">
            标签是<strong>你自己的分组</strong>，不属于任何一棵树；同一个标签可以同时覆盖「公司制度」和某个 CCS 类目。
          </div>
          <div className="ks-kb-card">
            <div className="ks-parse" style={{ marginBottom: 6 }}>
              <span>在此标签下提问的检索语法：</span>
              <code>安全+半导体-冶金</code>
              <span>（<code>+</code> 并且、<code>-</code> 屏蔽）</span>
            </div>
            <div className="ks-parse">
              <Input
                className="ks-parse-in"
                value={query}
                placeholder="安全+半导体-冶金"
                aria-label="检索语法输入（占位：仅演示解析，不发起检索）"
                onChange={(event) => { setQuery(event.target.value) }}
              />
              <span>{parsedText === '' ? '（还没输入）' : parsedText}</span>
            </div>
          </div>
          {tagRows.map((row) => (
            <div className="ks-tagrow" key={row.name}>
              <span className="ks-tag">{row.n}</span>
              <div className="ks-tagrow-main">
                <span className="ks-tagrow-name">{row.name}</span>
                <span className="ks-tagrow-scope">覆盖：{row.folders.join('、')}</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                title="占位：将来带着这个标签的范围发起一次对话"
                onClick={() => { setQuery(row.name) }}
              >
                在此标签下提问
              </Button>
            </div>
          ))}
          {tagRows.length === 0 && (
            /* 空态卡（同上）；标签视图的这一支没有可点的动作 ⇒ 只给图标/标题/描述 */
            <div className="ks-empty-card">
              <span className="ks-empty-ico"><IconPlusOutline16 size={28} /></span>
              <span className="ks-empty-t">还没有标签</span>
              <span className="ks-empty-d">
                在文件列表里给文档点「＋标签」，标签会汇总到这里，并显示它覆盖了哪些文件夹。
              </span>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* ══ 面包屑 + 「← 返回上一级」（业主："进入二级目录就自动出现返回上一级的按钮"）══
              ⚠ 按钮的出现条件是 **path.length > 0**（= 已经离开库根，进了下一级），
                库根（path 为空）没有"上一级"可回 ⇒ 不显示。</> */}
          <div className="ks-crumb">
            {path.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="ks-back"
                title={`回到上一级（现在在：${crumb}）`}
                onClick={goUp}
              >
                <IconChevronLeftOutline14 />
                返回上一级
              </Button>
            )}
            {/* 面包屑**逐级可点**（业主 2026-09-20：「这种路径要**每一级都能点击跳转**」）：
                知识库名 / 一级 / 二级 / 三级 —— 点第 i 级就回到那一层（i=0 = 回库根）。
                ⚠ **当前所在那一级不可点**（`depth === path.length`）：渲染成 `<span aria-current="page">`
                  **不是**按钮 —— "你现在在这"不该是一个按不动的假按钮。
                ⚠ 结构：外层 `.ks-crumb-path`（仍然在，且仍然是**测量锚点**，见 ui-render-shot.mjs 的
                  `.ks-crumb-path` 几何项）里面是 `item / 分隔符 / item / …`。
                  **分隔符与条目是兄弟**（不是把 `/` 塞进条目里）：条目的 textContent 因此
                  **只等于那一级的名字**（渲染级冒烟按它逐级比对，不会被 `/` 污染）。
                  ⚠ 分隔符**没有空白字符**（`/` 就一个字符）：两条目之间若插一个纯文本空格，
                  在 flex 行里会多出一个匿名文本项、在段之间顶出空隙 —— 那是版式 bug，
                  所以段间空隙一律交给 `.ks-crumb-sep` 的 `padding`。
                ⚠ 整条仍必须**收敛**（520 档是硬约束）：它还是 `.ks-crumb` 那个 nowrap flex 行，
                  条目 `flex:0 1 auto` 可缩、`overflow:hidden` 由 `.ks-crumb` 兜 ⇒ 窄窗下尾巴被裁掉、
                  不会被撑破（见 ksGuideStyles.ts 的 `.ks-crumb*` 那一段）。 */}
            <span className="ks-crumb-path" title={`当前路径（知识库 / 各级目录）：${crumb}`}>
              {crumbItems.map((c, i) => (
                <Fragment key={`${String(c.depth)}:${c.name}`}>
                  {i > 0 && <span className="ks-crumb-sep" aria-hidden="true">/</span>}
                  <span className="ks-crumb-item">
                    {c.current ? (
                      <span
                        className="ks-crumb-here"
                        aria-current="page"
                        data-current="true"
                        title="你现在在这一级（不可点）"
                      >
                        {c.name}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="ks-crumb-go"
                        aria-label={c.depth === 0 ? `回到「${c.name}」的知识库根目录` : `回到「${c.name}」这一级`}
                        title={c.depth === 0 ? `回到「${c.name}」根目录` : `回到「${c.name}」`}
                        onClick={() => { enterDepth(c.depth) }}
                      >
                        {c.name}
                      </button>
                    )}
                  </span>
                </Fragment>
              ))}
            </span>
            <div className="ks-kb-grow" />
            {/* 目录层给"几个子目录"；**文件层不在这里再报一次篇数** —— 列表题头（.ks-list-cap）
                已经写着「N 篇」，筛选条也写着「共 N 篇」，三处同数是噪音（5h 的第一版就是三处）。
                ⚠ 5i：目录层接上了搜索 ⇒ 有词时写成「筛出 X / 共 Y 个子目录」（与筛选条同一口径），
                  用户不用自己去数剩下几张卡。 */}
            {!atFiles && (
              <span className="ks-crumb-n">
                {needle === '' ? `${kids.length} 个子目录` : `筛出 ${kidsShown.length} / 共 ${kids.length} 个子目录`}
              </span>
            )}
          </div>

          {atFiles ? (
            <div className="ks-split">
              {/* 中：**真表格**（P2 头条，2026-09-20）
                  —— 列头 + 列对齐 + 行内文件图标 + 列表上方的搜索框。
                  参照 WeKnora `23-kb-detail-list-1440.png` 是一张 6 列真表格（列头 + 行内图标 +
                  行内可见 chip + 上方搜索框）；我们**抄结构不抄尺寸**（行高仍 52、表头 40）。
                  ⚠ 5h 起它只出现在**最末一级**（业主："到最末一级才是文件"）；结构一字未改。
                  ⚠ 搜索框这一条的翻案留痕见本文件顶部第 4 条、**层级口径见第 4b 条**
                    （业主 2026-09-20 已明确"保留"；5i 起每一层常驻）。 */}
              <div className="ks-main">
                {/* 列表题头：原来挂在 .ks-lhead 里（表头变成**真列头行**之后它就不该再待在那儿，
                    否则"文件名"列头与目录名抢同一个格子）。信息一条没少，只是上移一行。 */}
                <div className="ks-list-cap">
                  <span className="ks-lhead-name ks-kb-grow" title={crumb}>{node.name}</span>
                  <span className="ks-kb-hint">
                    {listed.length} 篇{selected.size > 0 ? `（已选 ${String(selected.size)}）` : ''}
                  </span>
                </div>

                {/* 筛选条（P1-4，2026-09-20；5h 从页级搬进"文件层"——它筛的是**文件**）。
                    一排**等高胶囊**（高 32px / 字号 12px / 间距 12px）。
                    参照真机 22/23 是 5 个 140×32 的等高胶囊；我们原来页内**没有任何筛选**。
                    范围克制到"只有跟页面里真实占位数据对得上的三档"（见 FILTERS 的注释），
                    并且**真的作用在 listed 上**（换档即清空选择，见 pickFilter）。
                    计数写成「筛出 X 篇 / 共 Y 篇」：筛选生效时用户不用回表头换算。
                    ⚠ 图标只给"全部"那一枚（语义是"这一排是筛选"）；13 个宿主图标成员里逐个核过，
                      IconInspectOutline12 是真的（ui-primitives 的 icons 导出，名字写错不会构建失败、
                      只有真机会 undefined —— 所以这是查过才用的）。 */}
                <div className="ks-filters" role="group" aria-label="按效力状态筛选">
                  {FILTERS.map((f, i) => {
                    const on = filter === f.id
                    return (
                      <button
                        key={f.id}
                        type="button"
                        className={on ? 'ks-chip ks-chip-on' : 'ks-chip'}
                        aria-pressed={on}
                        title={i === 0 ? '不筛任何状态' : `只看「${f.text}」的文件`}
                        onClick={() => { pickFilter(f.id) }}
                      >
                        {i === 0 && <IconInspectOutline12 />}
                        {f.text}
                      </button>
                    )
                  })}
                  <span className="ks-kb-hint">
                    {filter === 'all'
                      ? `共 ${String(inFolder.length)} 篇`
                      : `筛出 ${String(listed.length)} 篇 / 共 ${String(inFolder.length)} 篇`}
                  </span>
                </div>

            {/* 搜索框（P2 头条；**5i 起每一层都有** —— 控件本体在上面的 `searchBox` 常量里，
                这里只是**文件层**那一处渲染点：位置与行为与本批之前**逐字相同**）。
                ⚠ 它**真的过滤**：`listed` 由 `useMemo` 按 `no`/`name` 算（见 hitSearch），
                  不是画个壳 —— 验收就是"输入只命中 1 行的串 ⇒ 行数真的变 1；清空 ⇒ 恢复"。
                ⚠ 它是**本地列表过滤**（只筛当前目录已加载的行，一个接口都没调）。
                ⚠ 渲染与否由 **`KB_PAGE_SEARCH`** 这一个声明决定（退回时改它，见该常量注释）：
                  两个方向都有断言盯着（在场 ⇒ 每一层都在且能过滤；缺席 ⇒ 必须真的没有）——
                  这是复核 verify-freeze-p2 的 C 条要的"存在/缺席与某处声明一致"。 */}
            {searchBox}

            {/* ── 列表 = **一个容器**（P1-2/P1-8，2026-09-20；P2 头条把它变成真表格） ──
                容器里是"**列头行 + 全部行**"，两者共用 `.ks-list` 上的 `--ks-cols`
                （列宽的唯一所有者）⇒ 列必然对齐。
                ⚠ 空态卡、搜索框、批量条**不在**这个盒子里。 */}
            <div className="ks-list">
            {/* 列头行：**一行 5 个 cell**，与行同构（同一份 `COLUMNS`） */}
            <div className="ks-lhead">
              {COLUMNS.map((col) => (
                <div className={`ks-cell ${col.cls}`} key={col.key}>
                  {col.key === 'name' ? (
                    <Checkbox
                      checked={allChecked}
                      onChange={toggleAll}
                      label={allChecked ? '取消全选' : '全选'}
                      title={`全选本文件夹的 ${String(listed.length)} 篇`}
                    />
                  ) : null}
                  {col.head === '' ? null : <span className="ks-lhead-col">{col.head}</span>}
                </div>
              ))}
            </div>

            {listed.map((doc) => {
              const st = STATUS[doc.status]
              const isOpen = menuFor === doc.id
              /**
               * 一个 cell 的内容（`COLUMNS.map` 逐列取）。**列身份**由 `COLUMNS` 定义、
               * 列宽由 `.ks-list` 的 `--ks-cols` 定义 ⇒ 表头与行的对齐是**结构保证**的。
               */
              const cellFor = (key: ColKey): ReactNode => {
                switch (key) {
                  case 'name':
                    return (
                      <>
                        {/* 行内**文件图标**（P2 头条）：从 `no` 推出的呈现档，见 docGlyph 的注释。
                            ⚠ 位置只能在勾选框**之前**：文件名**就是**宿主 Checkbox 的 label
                              （Checkbox.tsx 原文"visible and accessible label"）⇒ 名字与勾选框
                              是同一个元素，图标插不进它们中间。参照是 [勾选][图标][名字]，
                              我们是 [图标][勾选+名字] —— 这是宿主原语给的形状，不是没做。 */}
                        <span className="ks-fileico" title={docGlyphLabel(doc.no)}>{docGlyph(doc.no)}</span>
                        {/* 文件名**就是** Checkbox 的 label（可访问名 = 文件名，且只渲染一次）。
                            ⚠ **整行可点：未做（不是做不了）** —— 2026-09-20 复核打回更正（B6）：
                              可见 label 只否掉了"整行无差别再吃一次 click"这一种写法（会与
                              "点勾选框 = 勾选"打架）；正当做法至少三条：① 行 onClick +
                              event.target.closest('label,input,button') 排除；② onClick 只绑文件名列；
                              ③ Checkbox 传 sr-only label + 独立的文件名元素（③ 未核宿主是否支持）。
                              代价见 docs/UI-BASELINE.md 5f 三处留痕第 1 条；登记在
                              docs/research/weknora-ui-vs-ours.md §8.1 的 P2-2。 */}
                        <Checkbox
                          className="ks-check"
                          checked={selected.has(doc.id)}
                          onChange={(next) => { toggleOne(doc.id, next) }}
                          label={doc.name}
                          title={doc.no === '' ? doc.name : `${doc.no} ${doc.name}`}
                        />
                        {/* 文件名列的第 2 行 = **标准号**（真字段 `no`；法规没有号就按全站约定给破折号）。
                            ⚠ 参照的文件名列也是两行（文件名 + 描述）；我们**没有描述字段**
                              ⇒ 第 2 行只复述已有的 `no`，不编一句像描述的话。 */}
                        <span className="ks-item-sub">
                          <span className="ks-item-meta">{doc.no === '' ? '—' : doc.no}</span>
                        </span>
                      </>
                    )
                  case 'status':
                    return <span className={st.cls}>{st.text}</span>
                  case 'date':
                    return <span className="ks-kb-hint">{doc.effective}</span>
                  case 'tags':
                    /**
                     * 标签列 = **行内可见的 chip**（P2 头条要的"行内可见 chip"）。
                     * ⚠ 只显示前 2 个 + `＋N`（多出来的用计数，不换行、不撑列）；
                     *   全部标签仍在 `⋮ → 标签：…`（只读项）与右侧详情卡里。
                     * ⚠ chip 是**纯展示 span**（不是 button）：做成可点会把行内可见控件从 3 提到 4，
                     *   而"≤3"是一条**真控件口径**的护栏（复核变异 M2 证明过旧口径可绕过）
                     *   ⇒ 不为了好看去放宽它。加标签的入口仍在行尾「⋮」（见菜单项"＋标签"）。
                     */
                    return doc.tags.length === 0 ? <span className="ks-kb-hint">—</span> : (
                      <>
                        {doc.tags.slice(0, 2).map((t) => <span className="ks-tag" key={t}>{t}</span>)}
                        {doc.tags.length > 2 && <span className="ks-kb-hint">＋{doc.tags.length - 2}</span>}
                      </>
                    )
                  case 'more':
                    return (
                      /* 行尾「⋮」溢出菜单（P1-1）：常驻的「＋标签」与「详情」收进这里
                         ⇒ 行内可见控件保持 **3 个**（勾选框 + 状态徽章 + ⋮）。 */
                      <span className="ks-item-more">
                        <Menu
                          open={isOpen}
                          portal
                          autoFocus
                          align="end"
                          items={[
                            { id: 'detail', label: '详情' },
                            { id: 'tag', label: '＋标签' },
                            { id: 'tags', label: `标签：${doc.tags.length === 0 ? '（无）' : doc.tags.join('、')}`, disabled: true },
                          ]}
                          onClose={() => { setMenuFor(null) }}
                          onSelect={(id) => {
                            setMenuFor(null)
                            if (id === 'detail') setOpenDoc(openDoc === doc.id ? null : doc.id)
                            if (id === 'tag') {
                              setDocs((prev) => prev.map((d) => (d.id === doc.id && !d.tags.includes('待归类')
                                ? { ...d, tags: [...d.tags, '待归类'] }
                                : d)))
                            }
                          }}
                          anchor={(
                            <Button
                              variant="ghost"
                              size="sm"
                              aria-haspopup="menu"
                              aria-expanded={isOpen}
                              aria-label={`${doc.name} 的更多操作`}
                              title="更多操作（详情 / 加标签）"
                              onClick={() => { setMenuFor(isOpen ? null : doc.id) }}
                            >
                              <IconEllipsisOutline16 />
                            </Button>
                          )}
                        />
                      </span>
                    )
                }
              }
              return (
                <div className={openDoc === doc.id ? 'ks-item ks-item-on' : 'ks-item'} key={doc.id}>
                  {COLUMNS.map((col) => (
                    <div className={`ks-cell ${col.cls}`} key={col.key}>{cellFor(col.key)}</div>
                  ))}
                </div>
              )
            })}
            </div>

            {listed.length === 0 && (
              /* 空态卡（P0-5）：64px 圆图标 + 标题 + 描述 + 主按钮（照 WeKnora EmptyState）。
                  文案里的"真实实现里应显示导入到此处"这句诚实边界没删 —— 挪进 title=。
                  ⚠ P1-4（2026-09-20）：要**分清两种空** —— 这个夹子本来就没文件（给导入 CTA），
                    还是被筛选/搜索筛没了（给"清除"，不给导入按钮；否则是在骗用户去导入）。
                  ⚠ P2 头条（2026-09-20）：把"搜索"也算进第二种空里（否则搜不到东西时会
                    显示"这个文件夹还没有文件"——那是假的，"清除"按钮也要一并清掉搜索串）。 */
              <div className="ks-empty-card">
                <span className="ks-empty-ico"><IconFolderOpenOutline16 size={28} /></span>
                {inFolder.length > 0 ? (
                  <>
                    <span className="ks-empty-t">没有符合筛选或搜索的文件</span>
                    <span className="ks-empty-d">
                      这个目录里共 {inFolder.length} 篇
                      {filter === 'all'
                        ? <>，搜索「{search.trim()}」一篇都没命中。</>
                        : <>，当前筛选「{FILTERS.find((f) => f.id === filter)?.text ?? ''}」与搜索一篇都没留下。</>}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      title="回到「全部」并清空搜索串，选择也会一并清空"
                      onClick={() => { pickFilter('all'); pickSearch('') }}
                    >
                      清除筛选与搜索
                    </Button>
                  </>
                ) : (
                  <>
                    <span className="ks-empty-t">这个文件夹还没有文件</span>
                    <span className="ks-empty-d">
                      导入文件后，条款会落到这个目录下。这里现在只是占位。
                    </span>
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<IconPlusOutline16 />}
                      title="真实实现里这里是「导入到此处」；当前入口在「文件导入」页"
                      onClick={() => { tab.actions.openTab(KS_KB_KIND, { replaceTab: true, params: { page: 'ingest' } }) }}
                    >
                      导入文件…
                    </Button>
                  </>
                )}
              </div>
            )}

            {/* 悬浮批量条：有选中才出现。
                ⚠ P0-5：括号说明（原第 5 个 flex 项）挪进 title= ⇒ 不再把条子挤成两行；
                   「批量删除」挂宿主 state-error 色（危险动作要有危险色）；三个动作补宿主图标。
                   ⚠ 括号里那句诚实边界没删，只是换成 hover 才看。 */}
            {selected.size > 0 && (
              <div className="ks-batch" title="这些动作都作用在页面状态上，不会写进库。">
                <span className="ks-batch-n">已选 {selected.size} 项</span>
                {/* P1-6（2026-09-20）：四个动作按钮显式钉 24px 高（--ks-btn-h-sm）。
                    原来实测 28px —— 那是 align-items:center 加图标把它撑起来的，不是宿主档位。
                    ⚠ border:0 + elevation 的配对**没动**（官方硬规则）；危险动作仍是红字。 */}
                <Button className="ks-batch-btn" variant="ghost" size="sm" onClick={() => { setSelected(new Set<string>()) }}>
                  取消选择
                </Button>
                <Button
                  className="ks-batch-btn"
                  variant="outline"
                  size="sm"
                  icon={<IconPlusOutline16 />}
                  title="占位：给选中的都加一个标签"
                  onClick={tagSelected}
                >
                  批量打标签
                </Button>
                <Button
                  className="ks-batch-btn"
                  variant="outline"
                  size="sm"
                  icon={<IconFolderOpenOutline16 />}
                  title={`占位：移动到「${MOVE_TARGET}」`}
                  onClick={moveSelected}
                >
                  移动到目录
                </Button>
                <Button
                  className="ks-danger ks-batch-btn"
                  variant="outline"
                  size="sm"
                  icon={<IconTrashOutline16 />}
                  title="占位：只从页面状态里删掉"
                  onClick={deleteSelected}
                >
                  批量删除
                </Button>
              </div>
            )}
          </div>

          {/* 右：详情（含你要的三个日期）
              ⚠⚠ **2026-09-20 业主：「点每一行行尾的「⋮」→「详情」看这一篇的元数据（含发布日期 / 生效日期 /
              废止日期）。 这个卡片删除掉」** ⇒ 那张**提示卡**已删。
              删卡后"没选中任何一行"时右栏怎么处理，是我定的（业主只说了删卡）：
              **整栏不渲染** —— 否则会留一条 200px 的**空栏**（`.ks-detail` 有 `min-width:200px`），
              那比提示卡更难看；选中一行时右栏才出现、表格随之变窄（主从式布局的常见行为）。
              **可逆**：要回到"始终留栏、空白就空白"，把 `current !== null &&` 去掉、里面那支留空即可。
              ⚠ 这一栏的**空态文案**没有任何断言依赖它（`smoke-kb-page-render.mjs` 判的是行为与结构，
              `ui-render-shot.mjs` 的留边适用面里也没有 `.ks-detail`）—— 删它不需要改判据。 */}
          {current !== null && (
          <div className="ks-detail">
            <div className="ks-kb-card">
                <div className="ks-kb-row" style={{ marginBottom: 6 }}>
                  <strong className="ks-kb-grow ks-kb-ct" title={current.name}>{current.name}</strong>
                  <span className={STATUS[current.status].cls}>{STATUS[current.status].text}</span>
                </div>
                <div className="ks-fields">
                  <Field label="标准号" value={current.no} mono />
                  <Field label="发布日期" value={current.published} />
                  <Field label="生效日期" value={current.effective} />
                  <Field label="废止日期" value={current.withdrawn} />
                  <Field label="所属目录" value={current.folder} />
                </div>
                <div className="ks-kb-row" style={{ marginTop: 8, flexWrap: 'wrap' }}>
                  <span className="ks-kb-hint">标签</span>
                  {current.tags.map((t) => <span className="ks-tag" key={t}>{t}</span>)}
                  <Button
                    variant="ghost"
                    size="sm"
                    title="占位：只加到页面状态"
                    onClick={() => {
                      setDocs((prev) => prev.map((d) => (d.id === current.id && !d.tags.includes('待归类')
                        ? { ...d, tags: [...d.tags, '待归类'] }
                        : d)))
                    }}
                  >
                    ＋标签
                  </Button>
                </div>
                <div className="ks-kb-hint" style={{ marginTop: 6 }}>
                  这里<strong>只显示你自己打的标签</strong>——按你的要求，取消了"领域标签"那套自动打标签。
                </div>
            </div>
          </div>
          )}
            </div>
          ) : (
            /* ══ 目录层（一级/二级/三级…）：**只显示子目录**，不铺文件 ══
               业主："先占上一级目录文件夹，然后点开是二级目录"；"到最末一级才是文件"。
               ⚠ 每个目录行上的「N 篇」是**这一棵子树**里的文件数（`countUnder`，含更深层）——
                 用户不用点进去就知道下面有没有东西。
               ⚠ 现有占位数据里 `USER_FOLDERS`（公司制度/内部操作规程/供应商资料）**没有子目录**，
                 所以点那三张卡会**直接**落到文件表格（`atFiles`）—— 那是数据本来的层级，不是漏做。
               ⚠ 5i（2026-09-20 收尾批）：这一层**也常驻搜索框**（`searchBox`，过滤**目录名**）——
                 位置与文件层同构：都是"紧贴这一层的条目区上方"。没命中时给**专门的**空态
                 `没有符合搜索的目录`（+「清除搜索」），**不**复用文件层那句"没有符合筛选或搜索的文件"
                 （那是文件的话；在目录层说"文件"会把用户引到错的地方）。
               ⚠⚠ **2026-09-20 头条（业主：「把子目录文件夹的视图，做成和文件列表一样的视图」）**：
                 目录层从**卡片网格**（`.ks-dirs` grid + `.ks-dir` 卡片按钮）改成**与文件列表同构的列表**：
                   容器 = `.ks-list`（**同一套类**）+ 一条**它自己的** `--ks-cols`（`ksGuideStyles.ts`
                     里的 `.ks-list-dirs`；列模板仍然只有 `.ks-list` 那一处所有者，行/表头都只写
                     `grid-template-columns:var(--ks-cols)`）；
                   表头 = 同一个 `.ks-lhead` + `DIR_COLUMNS.map(...)`；行 = 同一个 `.ks-item` +
                     `DIR_COLUMNS.map(...)` ⇒ 两侧 cell 类名序列**必然逐字相同**（与文件层同一条断言口径）；
                   行高 = 同一个 `--ks-row-h-list`（52px，与文件行一致）。
                 ⚠ `.ks-dirs` 这个类**留在容器上**（它被三处外部锚点按名引用：`ui-render-shot.mjs` 的
                   `#kspad` 留边适用面、`PAD_SUBJECTS_ALL`、`smoke-kb-pad-pixels.mjs` 的 `SPEC_SUBJECTS`
                   —— 且那三处要求逐字一致）。它**不再**是网格：新几何由 `.ks-list-dirs` 给
                   （`ksGuideStyles.ts` 里 `.ks-list-dirs` 那条 `display:block` 覆盖掉旧的
                   `display:grid` + `grid-template-columns:repeat(auto-fill,minmax(220px,1fr))`）。
                 ⚠ **整行可点**（业主：「每一级都能点击跳转」的同一条诉求；文件行那边"整行可点"仍是
                   未做项，因为文件名**就是**宿主 Checkbox 的可见 label —— 目录行**没有勾选框**，
                   所以"行本身就是 `<button>`"这条路在目录层**没有那个冲突**，可以直接做）。
                   键盘可达：它是原生 `<button>`（Tab 聚焦 + Enter/Space 激活，不用手写 keydown）；
                   焦点可见由 `ksGuideStyles.ts` 的 `.ks-list-dirs .ks-item:focus-visible` 给
                   （inset 环 —— 容器是 `overflow:hidden`，外扩环会被裁掉）。
                 ⚠ 空态卡（"没有符合搜索的目录"）**在列表盒子之外**，与文件层同一手法：
                   盒子只装"列头 + 行"（`smoke-kb-page-render.mjs` 判 `.ks-list` 的**直接子元素**）。 */
            <>
            {searchBox}
            {kidsShown.length === 0 && (
              <div className="ks-empty-card">
                <span className="ks-empty-ico"><IconFolderOpenOutline16 size={28} /></span>
                <span className="ks-empty-t">没有符合搜索的目录</span>
                <span className="ks-empty-d">
                  这一层共 {kids.length} 个子目录，搜索「{search.trim()}」一个都没命中。
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  title="清空搜索串，选择也会一并清空（与文件层那个「清除筛选与搜索」同一口径）"
                  onClick={() => { pickSearch('') }}
                >
                  清除搜索
                </Button>
              </div>
            )}
            <div className="ks-list ks-list-dirs ks-dirs">
              {/* 列头行：与目录行**同构**（同一份 `DIR_COLUMNS`），cell 类名序列因此逐字相同。 */}
              <div className="ks-lhead">
                {DIR_COLUMNS.map((col) => (
                  <div className={`ks-cell ${col.cls}`} key={col.key}>
                    {col.head === '' ? null : <span className="ks-lhead-col">{col.head}</span>}
                  </div>
                ))}
              </div>
              {kidsShown.map((child) => {
                const n = countUnder(child)
                /**
                 * 一个 cell 的内容（`DIR_COLUMNS.map` 逐列取）。列身份由 `DIR_COLUMNS` 定义、
                 * 列宽由 `.ks-list` / `.ks-list-dirs` 的 `--ks-cols` 定义 ⇒ 表头与行的对齐是
                 * **结构保证**的（与文件层的 `cellFor` 同一口径）。
                 */
                const dirCell = (key: DirColKey): ReactNode => {
                  switch (key) {
                    case 'dname':
                      return (
                        <>
                          <span className="ks-fileico" title="目录"><IconFolderOpenOutline16 /></span>
                          <span className="ks-dir-name" title={child.key}>{child.name}</span>
                          <span className="ks-item-sub">
                            <span className="ks-item-meta">{child.key}</span>
                          </span>
                        </>
                      )
                    case 'dcount':
                      return <span className="ks-kb-badge">{n} 篇</span>
                    case 'dgo':
                      return <span className="ks-dir-go"><IconChevronRightOutline14 /></span>
                  }
                }
                return (
                  <button
                    key={child.key}
                    type="button"
                    className="ks-item ks-dir-row"
                    title={`进入「${child.name}」（这一棵目录下共 ${String(n)} 篇）`}
                    aria-label={`进入目录「${child.name}」，这一棵目录下共 ${String(n)} 篇`}
                    onClick={() => { enterDir(child.key) }}
                  >
                    {DIR_COLUMNS.map((col) => (
                      <div className={`ks-cell ${col.cls}`} key={col.key}>{dirCell(col.key)}</div>
                    ))}
                  </button>
                )
              })}
            </div>
            </>
          )}
        </>
      )}
    </div>
    </div>
  )
}
