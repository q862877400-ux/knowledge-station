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
 *      · ⚠ **需要业主复核**：这条翻掉了他的原话，若他不同意，删掉 `.ks-search` 那一段
 *        并把断言换回去即可（改动面：本文件 + ksGuideStyles.ts + 渲染级冒烟）。
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

import { useMemo, useState, type ReactNode } from 'react'
import { Button, Checkbox, IconArchiveOutline20, IconChecklistOutline14, IconChevronDownOutline14, IconEllipsisOutline16, IconFolderOpenOutline16, IconInfoOutline14, IconInspectOutline12, IconListPenOutline16, IconPlusOutline16, IconSearchOutline16, IconShieldOutline16, IconTrashOutline16, Input, Menu, Pill } from '@deepseek-ai/dsh-client-ui-primitives'

import { ensureKsStyles } from './ksGuideStyles'
import { KsCapabilityPage } from './KsCapabilityPage'
import { describeKsQuery, parseKsQuery } from './ksSearchSyntax'
import type { KsPaneBodyProps, KsKbInjected } from './ksSidebar'
import { KS_KB_KIND } from './ksSidebar'

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
 * ⚠ 这里顺带修了一个**真 bug**（原版）：树的展开状态原本以 `node.name` 为键，
 * 而「宪法与行政法」在两棵法律分支下**重名** ⇒ 点一个会把另一个也展开/收起，
 * 且文档会挂到错误的分支。改成以**全路径 key** 为键。
 * 这类"用显示名当身份"的错，官方文档也点过（"Localized display text is never an identity"）。
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

/** 递归渲染树节点。展开状态以**全路径 key** 记，不用显示名（重名会串）。 */
function renderNodes(
  nodes: readonly MockNode[],
  current: string,
  onPick: (key: string) => void,
  open: ReadonlySet<string>,
  toggle: (key: string) => void,
  depth = 0,
): ReactNode {
  return nodes.map((node) => {
    const isOpen = open.has(node.key)
    const kids = node.children ?? []
    const on = current === node.key
    return (
      <div key={node.key}>
        <div
          className="ks-kb-tline"
          role="button"
          tabIndex={0}
          style={{ paddingLeft: 6 + depth * 12, ...(on ? { background: 'var(--dsw-alias-interactive-bg-hover)' } : {}) }}
          onClick={() => { if (kids.length > 0) toggle(node.key); onPick(node.key) }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') { if (kids.length > 0) toggle(node.key); onPick(node.key) }
          }}
        >
          <span className="ks-kb-tw">{kids.length > 0 ? (isOpen ? '▾' : '▸') : '·'}</span>
          <span className="ks-kb-tn" title={node.name}>{node.name}</span>
        </div>
        {isOpen && kids.length > 0 && renderNodes(kids, current, onPick, open, toggle, depth + 1)}
      </div>
    )
  })
}

/** 一个自带树的外壳（标题 + 层级说明 + 树体）。 */
function LibCard({ title, sub, nodes, current, onPick, open, toggle }: {
  readonly title: string
  readonly sub: string
  readonly nodes: readonly MockNode[]
  readonly current: string
  readonly onPick: (key: string) => void
  readonly open: ReadonlySet<string>
  readonly toggle: (key: string) => void
}): ReactNode {
  return (
    <div className="ks-kb-card">
      <div className="ks-kb-row">
        <strong className="ks-kb-grow ks-kb-ct">{title}</strong>
        <span className="ks-tag">自带</span>
      </div>
      <div className="ks-kb-cd">{sub}</div>
      <div className="ks-kb-tree">{renderNodes(nodes, current, onPick, open, toggle)}</div>
    </div>
  )
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
  const [folder, setFolder] = useState('P16 工程防火')
  const [docs, setDocs] = useState<readonly MockDoc[]>(SEED_DOCS)
  const [selected, setSelected] = useState<ReadonlySet<string>>(() => new Set<string>())
  const [openDoc, setOpenDoc] = useState<string | null>(null)
  /** 行尾「⋮」溢出菜单**同一时刻只开一个**（存的是行的 id，不是布尔）。 */
  const [menuFor, setMenuFor] = useState<string | null>(null)
  /** 状态筛选（P1-4）：真的作用在 `listed` 上，不是画个壳。 */
  const [filter, setFilter] = useState('all')
  /**
   * 列表搜索串（P2 头条，2026-09-20）。
   * ⚠ 这是**本地列表过滤**（只筛当前目录已加载的行，按 `no`/`name` 做 includes），
   *   **不是**语料检索：一个接口都没调。口径与参照 WeKnora 的"搜索文档名称…"一致；
   *   与业主 2026-09-19「知识库界面不做搜索」的关系见本文件顶部第 4 条的**翻案留痕**。
   */
  const [search, setSearch] = useState('')
  const [newOpen, setNewOpen] = useState(false)
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(['P 土木、建筑', 'C 医药、卫生、劳动保护', 'Z 环境保护', '法律', '行政法规']),
  )
  const [query, setQuery] = useState('')

  const toggle = (key: string): void => {
    setOpen((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  /** 当前文件夹里的全部（未筛选）—— 筛选条的计数要用它做分母。 */
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
   */
  const pickSearch = (value: string): void => {
    setSearch(value)
    setSelected(new Set<string>())
  }

  /**
   * 换文件夹（P1-4 的连带修正）：**也要清空选择**。选择按"行 id"存，换了夹子之后
   * 上一条选择里的行已经不在这份列表里，批量动作会作用在**看不见的行**上。
   * 与 pickFilter 是同一个理由（筛选变化即清空）。
   */
  const pickFolder = (key: string): void => {
    setFolder(key)
    setSelected(new Set<string>())
    setOpenDoc(null)
  }

  /** 标签视图的数据**从文档状态推导**（这样"批量打标签"能立刻反映出来，不是死数据）。 */
  const tagRows = useMemo(() => {
    const map = new Map<string, { folders: Set<string>; n: number }>()
    for (const d of inFolder) {
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
  }, [inFolder])

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
    )
  }

  return (
    <div className="ks-kb">
      {/* 页面骨架（照 WeKnora 列表页：大标题 + 一行副标题 + 0.5px 分隔线；见 docs/UI-BASELINE.md 三）
          ⚠ 原来这里是"14px 粗体 + 右边一排按钮"的一行 —— 没有层级，标题和操作挤在同一视线高度上 */}
      <header className="ks-page-head">
        <div className="ks-page-title">知识库</div>
        <div className="ks-page-sub">
          法规/标准的落点：目录树 + 条款 + 标签；颜色一律走宿主主题 token，深浅色自动跟随
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

      {/* 筛选条（P1-4，2026-09-20）：一排**等高胶囊**（高 32px / 字号 12px / 间距 12px）。
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
        <div className="ks-split">
          {/* 左：自带两棵树 + 自建夹（「平级」，同一列依次排下去） */}
          <div className="ks-rail">
            <LibCard
              title="标准" sub="国家标准·行业标准·团体标准"
              nodes={STD_TREE} current={folder} onPick={pickFolder} open={open} toggle={toggle}
            />
            <LibCard
              title="法律法规" sub="法律 / 行政法规 / 部门规章 / 地方性法规"
              nodes={LAW_TREE} current={folder} onPick={pickFolder} open={open} toggle={toggle}
            />
            <div className="ks-kb-sec">我建的（真文件夹；与上面两棵平级）</div>
            <div className="ks-kb-cards">
              {USER_FOLDERS.map((f) => (
                <div
                  className="ks-kb-card"
                  key={f.key}
                  role="button"
                  tabIndex={0}
                  style={folder === f.key ? { borderColor: 'var(--dsw-alias-border-l4)' } : undefined}
                  onClick={() => { pickFolder(f.key) }}
                  onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') pickFolder(f.key) }}
                >
                  <strong className="ks-kb-ct">{f.name}</strong>
                  <div className="ks-kb-cd">{f.desc}</div>
                  <div className="ks-kb-foot">
                    <span className="ks-kb-badge">{docs.filter((d) => d.folder === f.key).length} 篇</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 中：**真表格**（P2 头条，2026-09-20）
              —— 列头 + 列对齐 + 行内文件图标 + 列表上方的搜索框。
              参照 WeKnora `23-kb-detail-list-1440.png` 是一张 6 列真表格（列头 + 行内图标 +
              行内可见 chip + 上方搜索框）；我们**抄结构不抄尺寸**（行高仍 52、表头 40）。
              ⚠ 搜索框这一条的翻案留痕见本文件顶部第 4 条（业主 2026-09-19 曾说"这一页不做搜索"）。 */}
          <div className="ks-main">
            {/* 列表题头：原来挂在 .ks-lhead 里（表头变成**真列头行**之后它就不该再待在那儿，
                否则"文件名"列头与目录名抢同一个格子）。信息一条没少，只是上移一行。 */}
            <div className="ks-list-cap">
              <span className="ks-lhead-name ks-kb-grow" title={folder}>{folder}</span>
              <span className="ks-kb-hint">
                {listed.length} 篇{selected.size > 0 ? `（已选 ${String(selected.size)}）` : ''}
              </span>
            </div>

            {/* 搜索框（P2 头条）：宿主 `Input` + 16px 放大镜（参照那个框左侧就是一个 16px 放大镜）。
                ⚠ 它**真的过滤**：`listed` 由 `useMemo` 按 `no`/`name` 算（见 hitSearch），
                  不是画个壳 —— 验收就是"输入只命中 1 行的串 ⇒ 行数真的变 1；清空 ⇒ 恢复"。
                ⚠ 它是**本地列表过滤**（只筛当前目录已加载的行，一个接口都没调）；
                  与业主"知识库界面不做搜索"的关系见文件顶部第 4 条的翻案留痕。 */}
            <span className="ks-search">
              <Input
                icon={<IconSearchOutline16 />}
                value={search}
                placeholder="搜索标准号或名称…"
                aria-label="在文件列表里按标准号或名称过滤（本地过滤，不检索语料）"
                onChange={(event) => { pickSearch(event.target.value) }}
              />
            </span>

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

          {/* 右：详情（含你要的三个日期） */}
          <div className="ks-detail">
            {current === null ? (
              <div className="ks-kb-card">
                <div className="ks-kb-hint">
                  点每一行行尾的「⋮」→「详情」看这一篇的元数据（含
                  <strong>发布日期 / 生效日期 / 废止日期</strong>）。
                </div>
              </div>
            ) : (
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
            )}
          </div>
        </div>
      )}
    </div>
  )
}
