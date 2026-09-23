/**
 * ks-dsh-plugin — client/KsKnowledgePage.tsx
 *
 * 「知识库」tab 的 body。**2026-09-21 起它是一页真库**（KB-FOLDER-PLAN §五第 3 步
 * 「界面骨架」）：左边一列目录（按需展开）、右边只显示**当前这一级**、顶上一行路径 +
 * 返回上一层、每一级都能上传、空目录如实说空。数据来自引擎的
 * `/api/v1/kb/*`（第 2 步已合入，`src/core/api/routes_kb_folders.py`），
 * **不再是本文件里的占位常量**。
 *
 * ## 本批（第 3 步）接手时删掉了什么、为什么（逐条可核）
 * 上一版（2026-09-20 的 5h/5i/5j 样板）里有这些东西，本批按"真库"的判据处理：
 *   1. **卡片带**（`.ks-kbband` + `KNOWLEDGE_BASES`/`BAND_STEP_PX`/`scrollBand`/`hasLayout`
 *      /`clipRef`/`bandLeft`）—— 业主 2026-09-21 定案："原来的**大卡片去掉**"，
 *      改成**左边一列真目录**（方案 §一）。连带它的状态与常量**一起删**（不留死代码）。
 *   2. **占位数据**（`SEED_DOCS` 15 篇、`STD_TREE`/`LAW_TREE`/`USER_FOLDERS`/`MockDoc`
 *      /`MockNode`/`subtreeKeys`/`nodeAtPath`/`pathNames`）—— 现在每个字都是后端给的。
 *   3. **只改内存不落库的假动作**（方案 §六最后一条点名的）：`NEW_ITEMS` 里的
 *      「新建文件夹（占位）」、`MOVE_TARGET` + 「移动到目录」、行内/批量「＋标签」、
 *      以及靠它们撑起来的**标签视图**（`.ks-subtabs` + `ks-parse` + `tagRows`）。
 *      **一处不留** —— 留着就是"按下去只改内存"。
 *   4. **文件勾选 + 悬浮批量条**：方案 §五第 3 步的"本批不做"里点明
 *      "文件的移出 / 挪动 / 复制 / **批量选择动作**"不在本批 ⇒ 勾选与批量条一并撤掉
 *      （留着它们要么是假动作，要么就得把"批量删除真删库"这件不可逆的事在这一批顺手做掉，
 *      两样都不该发生）。**这条是"删除"，父代理可复核：`git log -p` 里能逐行看到。**
 *   5. **状态筛选胶囊**（`.ks-filters`/`FILTERS`）：文件列表现在是**后端分页**的
 *      （`limit/offset`，方案 §七的性能红线），而 `/kb/folders/{id}/items` **没有状态筛选参数**
 *      ⇒ 前端只筛"当前这一页"会静默撒谎（"筛出 0 篇"其实后面几页有）。诚实的做法要么加后端参数
 *      （本批**不许改后端**）、要么不做 ⇒ **不做**，登记在报告里。
 *
 * ## 本批（第 4 步，2026-09-21）加了什么、把什么收起来了（逐条可核）
 *
 * 1. **「待分类」层**（左列目录树里的那一行点进去；与目录层同构的列表：勾选 / 文件名 /
 *    状态 / 建议去向 / ⋮）。每篇的状态**如实**来自后端：排队中 / 识别中 / 识别失败（带
 *    失败原因）/ 待确认 + 识别率 —— 标签由 `GET /kb/stage-labels` 下发
 *    （`folder_store.STAGE_LABELS` 是唯一所有者），本文件那份只是**拿不到时的兜底**。
 * 2. **逐篇处置**（行尾 ⋮）：放进某个现有目录（带搜索的目录选择器）/ 按建议归位 /
 *    在建议位置新建目录再放 / **重来一次** / **删掉（要二次确认）**。
 *    ⚠ **没有建议的那一篇**（真库 379 篇兜底桶）**不渲染**「按建议归位 / 在建议位置新建」——
 *    后端对它们会回 422 `no_suggestion`，渲染出来就是死按钮。
 * 3. **真的批量**（第 3 步按"不许留假动作"拆掉的那套**做回来了**，每一条都对应真接口）：
 *    勾选 + 悬浮批量条（接受建议 / 放进同一目录 / 重来一次 / 删除）。
 *    「接受建议」只对**有建议**的那几篇发；没有建议的**如实数出来**（不静默丢）。
 * 4. **导入并进来了**：待分类层上就是导入面板（来源目录 + **先体检（只读）** + 导入），
 *    导入完成后新文件**就出现在这个列表里**、当场能处置。原「文件导入」那个独立页面
 *    （`params.page === 'ingest'` 以前是一页"尚未实现"的占位）**收起来了** —— 现在它
 *    直接落到这一层；设置里那个「入库预览」入口也一并撤掉（功能并入这里）。
 * 5. **「重来一次」的进度如实说**：起手写「识别中」，跑完变「待确认」或「识别失败」；
 *    界面轮询 `GET /kb/inbox/reingest/status`，跑完自动重读这一层。
 *
 * ## 保留下来、一个字没动的
 * - **搜索框**（`KB_PAGE_SEARCH` 是它"在/不在"的唯一声明；`docs/NOT-DOING.md` 第 13 条：
 *   业主 2026-09-20 明确"保留"，层级口径 = **每层常驻**）。本批它**过滤目录名与文件名**
 *   （任务书要求过滤目录名；台账第 13 条记的是"文件列表按标准号/名称过滤"，
 *   两个口径**一起**满足 —— 目录行按名字、文件行按标准号/名称，同一个词）。
 * - **整行可点 → 看这一篇的元数据**（业主 2026-09-21 定；见 `openRowDetail` 的长注释）。
 * - 页面留边（`.ks-page` 容器查询 + `.ks-kb` 吃 token）、宿主原语、`--dsw-alias-*` token。
 * - 每行行尾「⋮」菜单（**只剩「详情」**：＋标签那条是假动作，已拆）。
 *
 * ## 上传（需求 5）的三处事实，写在这里免得下一个人再猜一次
 *   a. 本仓**没有任何"浏览器上传文件"的接口**（全仓 grep `FormData`/`type="file"` = 0 命中）。
 *      这个项目里"导入"= **把 PDF 放进一个磁盘目录，再由引擎批量导入** ⇒ 上传面板给的是
 *      「来源目录」输入框（默认填 host 的**待入库目录**，走同源 `/ks/ingest/inbox-default`）。
 *   b. **真导入**是引擎的 `POST /api/v1/ingest/bulk`（`routes_update.py`），
 *      **不是** `plugin/src/ingest.js` 代理的那套 `/api/v1/ingest/**preview**`
 *      —— 后者是**只读体检（dry-run）**，跑完库里一篇都不会多。
 *   c. 落位：**有当前目录**时调 `POST /kb/inbox/confirm`（`action='existing'`）——
 *      它在同一个事务里"挂进这个目录 **且** `stage='filed'`"⇒ 才真正是业主要的
 *      「上传进当前这一层 = **不进自动识别**」。只调 `/kb/members` 的话
 *      `doc_filing_state` 仍是 `queued`，那篇文件**照样出现在「待分类」**里
 *      （理由与源码证据写在 `api.ts` 的 `fileDocsIntoFolder` 上面）。
 *      在**最外层**时没有可挂的目录（`/kb/members` 的 `folder_id='root'` 会 404，
 *      见 `api.ts` 的 `addKbMembers`），导入的文件就如实留在最外层（= 还没归位），
 *      面板上会**明说**这一点（不许让用户以为它进了某个目录）。
 */

import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { Button, Checkbox, IconChecklistOutline14, IconChevronDownOutline14, IconChevronLeftOutline14, IconChevronRightOutline14, IconCloseOutline16, IconEllipsisOutline16, IconFolderOpenOutline16, IconInfoOutline14, IconPlusOutline16, IconQuestionOutline14, IconRefreshOutline16, IconSearchOutline16, IconTrashOutline16, IconWarningOutline16, Input, Menu } from '@deepseek-ai/dsh-client-ui-primitives'

import {
  addKbMembers,
  askKsAnswer,
  batchDeleteDocs,
  confirmKbInbox,
  copyKbFolder,
  copyKbMembers,
  createKbFolder,
  deleteKbFolder,
  EngineAuthError,
  fetchBulkIngest,
  fetchDocsFlat,
  fetchIngestBatch,
  fetchIngestInboxDefault,
  fetchKbFolderDeletePreview,
  fetchKbFolderItems,
  fetchKbFolders,
  fetchKbFoldersFlat,
  fetchKbInbox,
  fetchKbReingestStatus,
  fetchKbStageLabels,
  fetchSession,
  fileDocsIntoFolder,
  moveKbFolder,
  moveKbMembers,
  reingestKbDocs,
  removeKbMembers,
  renameKbFolder,
  resolveKbScope,
  resumeBulkIngest,
  startBulkIngest,
  /* 「补全分类号」（2026-09-22）：插件自己把没有 CCS 的标准补齐（业主口径"修机制"）。 */
  cancelKbCcsBackfill,
  fetchKbCcsBackfillStatus,
  fetchKbCcsSummary,
  startKbCcsBackfill,
  type KsAnswerResult,
  type KsKbCcsBackfillStatus,
  type KsKbDeletePreview,
  type KsKbFile,
  type KsKbFlatFolder,
  type KsKbFolder,
  type KsKbInboxItem,
  type KsKbMemberItem,
} from './api'
import { ensureKsStyles } from './ksGuideStyles'
import { KsCapabilityPage } from './KsCapabilityPage'
import { KsChannelsPanel } from './KsChannelsPanel'
import { KsIngestPanel } from './KsIngestPanel'
import { KsMaterialsPanel } from './KsMaterialsPanel'

import type { KsPaneBodyProps, KsKbInjected, KsKbPage } from './ksSidebar'
import { KS_EVIDENCE_KIND, KS_KB_KIND } from './ksSidebar'

/**
 * **本页有没有那个搜索框**（"搜索框在 / 不在"的**唯一声明**）。
 *
 * `plugin/scripts/smoke-kb-page-render.mjs` 断言「DOM 里有没有 `.ks-search input`」与这个值
 * **一致**，并且**逐层**断言（最外层 / 每一级目录层各一次）。删掉框（或停掉某一层）都会红。
 *
 * ⚠ 退回给业主 2026-09-19 的旧设计（"这一页不做搜索"）时的**可执行**步骤在
 *   `docs/NOT-DOING.md` 第 13 条（那一节是逐落点、已亲自走通的版本）；
 *   **不许**把断言换回"数 placeholder 里有没有'搜索'"那种已证伪的假绿。
 */
export const KB_PAGE_SEARCH: boolean = true

/** 一页几篇文件（后端 `/kb/folders/{id}/items` 的默认值是 50，这里与它对齐）。 */
const FILE_PAGE_SIZE = 50

/**
 * 效力状态的呈现分档。`legal_status` 的取值域是 `doc_meta` 的 CHECK：
 * `effective | upcoming | superseded | withdrawn`（另加"读不到/为空"这一档如实显示 `—`）。
 */
type Status = 'current' | 'upcoming' | 'withdrawn' | 'superseded' | 'unknown'

const STATUS: Record<Status, { readonly cls: string; readonly text: string }> = {
  current: { cls: 'ks-status ks-status-ok', text: '现行' },
  upcoming: { cls: 'ks-status ks-status-warn', text: '即将实施' },
  withdrawn: { cls: 'ks-status ks-status-bad', text: '已废止' },
  superseded: { cls: 'ks-status ks-status-neutral', text: '被替代' },
  unknown: { cls: 'ks-status ks-status-neutral', text: '—' },
}

function statusOf(raw: string | null): Status {
  if (raw === 'effective') return 'current'
  if (raw === 'upcoming') return 'upcoming'
  if (raw === 'withdrawn') return 'withdrawn'
  if (raw === 'superseded') return 'superseded'
  return 'unknown'
}

/**
 * 文件**处理状态**的中文标签 —— **兜底用**。
 *
 * ⚠ 标签的**唯一所有者**是 `src/core/knowledge/folder_store.py` 的 `STAGE_LABELS`
 *   （五枚举 `queued/recognizing/confirming/filed/failed` 与 `schema.sql` 的 CHECK 一字不差）。
 *   第 4 步起**接口会把标签带下来**（`GET /api/v1/kb/stage-labels`，也随 `/kb/inbox` 的
 *   `stage_label` 一起下发）⇒ 这一份只在"标签接口读不到"时兜底，**不再是第二个所有者**。
 *   业主 2026-09-21："**所有文件**都要显示处理状态"（方案 §一），第 4 步把它做完整
 *   （失败原因/识别率/重来一次）。
 */
const STAGE_LABELS: Record<string, string> = {
  queued: '排队中',
  recognizing: '识别中',
  confirming: '待确认',
  filed: '已归位',
  failed: '识别失败',
}

function stageText(raw: string | null, labels: Record<string, string> = STAGE_LABELS): string {
  if (raw === null || raw === '') return '—'
  return labels[raw] ?? STAGE_LABELS[raw] ?? raw
}

/** 识别率怎么显示（只在真有值时显示；`0.9312` → `93%`）。 */
function confidenceText(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return ''
  const pct = value <= 1 ? value * 100 : value          // 后端存的是 0~1 的比例
  return `${String(Math.round(pct))}%`
}

/**
 * **「待分类」层**的列定义（与文件层/目录层同一种写法：表头与每一行共用这一份）。
 *
 * 业主点名的四样：**文件名 / 状态 / 建议去向 / ⋮**（方案 §四第 4 条 + 任务书）——
 * 勾选列是**控件**（批量选择），没有列头，与「⋮」列同一种待遇。
 * ⚠ 这一层**自己一条 --ks-cols**（`ksGuideStyles.ts` 的 `.ks-list-inbox`）：不复用文件层那五轨
 *   —— 那五轨（效力/生效日期/处理状态）在这一层没有对应的值，硬套就是拿别的层的列冒充。
 */

/** 批E4（业主 2026-09-23）：页面顶条四入口 = 真实文件夹的凸出标签样式（拍板留痕：
 *  文件夹标签=页面切换视觉样式，与已删除的「标签」功能无关）。预览器=打开 PDF（动作）。
 *  次级页（文件导入/备料）不占标签——收在开始页卡的▾里，本条恒显示四枚。 */
function KsTopTabs(props: {
  page: string
  onGo: (p: KsKbPage) => void
  onPdf: () => void
}): React.ReactElement {
  const tabs: Array<{ id: string; label: string; go: () => void }> = [
    { id: 'manage', label: '知识库', go: () => props.onGo('manage') },
    { id: 'channels', label: '渠道库', go: () => props.onGo('channels') },
    { id: 'capabilities', label: '办事台', go: () => props.onGo('capabilities') },
    { id: 'pdf', label: '预览器', go: props.onPdf },
  ]
  return (
    <nav className="ks-tabfolder-strip" aria-label="页面">
      {tabs.map((tb) => (
        <button
          key={tb.id}
          className={'ks-tabfolder' + (props.page === tb.id ? ' ks-tabfolder-on' : '')}
          type="button"
          aria-current={props.page === tb.id ? 'page' : undefined}
          onClick={tb.go}
        >
          {tb.label}
        </button>
      ))}
    </nav>
  )
}



const INBOX_COLUMNS = [
  { key: 'pick', cls: 'ks-col-pick', head: '' },
  { key: 'iname', cls: 'ks-col-iname', head: '文件名' },
  { key: 'istage', cls: 'ks-col-istage', head: '状态' },
  { key: 'idest', cls: 'ks-col-idest', head: '建议去向' },
  { key: 'imore', cls: 'ks-col-imore', head: '' },
] as const

type InboxColKey = (typeof INBOX_COLUMNS)[number]['key']

/** 每页几篇待分类（后端 `MAX_FILE_PAGE=200`；50 与小列表一致就好翻）。 */
const INBOX_PAGE_SIZE = 50

/** **文件层**的列定义（表头与每一行共用这一份 ⇒ 列身份只有一个所有者）。
 *
 * ⚠ 第 5 步加了**勾选列**（`fpick`，无列头 —— 与待分类层同一种待遇：勾选是控件不是字段）。
 *   类名与目录层的 `ks-col-dpick` **不共用**（两层都可能同屏：目录行在前、文件行在后）。
 *   ⚠ 它一加，行内可见控件数从 2 变 3（勾选框 + ⋮ + 只展示的效力徽章）——
 *   `ui-render-shot.mjs` 的 `ROW_CTRLS_EXPECTED` 必须同步改（那里有显式说明）。 */
const COLUMNS = [
  { key: 'fpick', cls: 'ks-col-fpick', head: '' },
  { key: 'name', cls: 'ks-col-name', head: '文件名' },
  { key: 'status', cls: 'ks-col-status', head: '效力' },
  { key: 'date', cls: 'ks-col-date', head: '生效日期' },
  { key: 'stage', cls: 'ks-col-stage', head: '处理状态' },
  // 行尾操作列：**没有列头**（参照里它也是 hover 才出现的三个点，不占表头文案）
  { key: 'more', cls: 'ks-col-more', head: '' },
] as const

type ColKey = (typeof COLUMNS)[number]['key']

/**
 * **目录层**的列定义 —— 与文件层同一种写法、同一种用法，但**列数按目录真有的字段给**：
 * 目录只有「名字」与「这一棵下的篇数」（后端 `file_count_deep`，见 `KS-KB-FOLDER` 契约），
 * **没有**更新时间/来源/大小 ⇒ 不许为凑成 5 列去编。
 * ⚠ 列类名与文件层**不重用**（`ks-col-dname/dcount/dmore`）：两层的行都挂在 `.ks-item` 上，
 *   重用类名会让"列身份"在两层之间串味。
 * ⚠ 第 5 步的两处改动（都是**加**，不是换语义）：
 *   · 加勾选列 `dpick`（批量挪/复制/删目录要用；无列头）；
 *   · 末列 `dgo`（一个只展示的进入箭头）换成 `dmore`（行尾「⋮」菜单：改名/新建下级/挪/复制/删）
 *     —— 目录行因此**不再是 button**（行内要有勾选框与菜单两个真控件；button 里嵌 input 是非法
 *     HTML），"进入这一级"改成名字那一格里的真 button（键盘可达）。
 *   ⇒ `ui-render-shot.mjs` 的 `DIR_COLS_EXPECTED` / `DIR_HEAD_CELLS_EXPECTED` /
 *     两条固定轨的冻结值必须同步（那里逐条写了为什么）。
 */
import { KsListHead } from './kbListUi'
const DIR_COLUMNS = [
  { key: 'dpick', cls: 'ks-col-dpick', head: '' },
  { key: 'dname', cls: 'ks-col-dname', head: '目录' },
  { key: 'dcount', cls: 'ks-col-dcount', head: '篇数' },
  { key: 'dmore', cls: 'ks-col-dmore', head: '' },
] as const

type DirColKey = (typeof DIR_COLUMNS)[number]['key']

/**
 * ⚠⚠ **已删除（业主 2026-09-22）**：原来这里有一对 `docGlyph()` / `docGlyphLabel()`
 * —— 按 `standard_no` 推断"文件类型字形"（盾 / 清单 / 文档+笔 / 归档盒）贴在**文件行**前面。
 * 业主看完真机图后说："文件前面那个莫名其妙的图标可以删除"；同一句里**保留**了目录行前面的
 * 文件夹图标（"文件夹前面一个小文件夹图标做得好"）。
 *
 * 留痕（不是悄悄删）：
 *   · 判据 `smoke-kb-page-render` 的 **E6** 原来判"每一行都有行内文件图标（`.ks-fileico` +
 *     真 svg + 非空 title）"—— 本轮**就地翻过来**：文件行**不许有** `.ks-fileico`、
 *     **目录行必须仍有**文件夹图标（原文留在那条断言里）。
 *   · `docs/KB-FOLDER-PLAN.md` §十六 登记的残余"文件行图标尺寸 14/16/20 三档混用"
 *     **因本次删除而消失**（该文档已就地标注）。
 *   · 类名 `.ks-fileico` 保留（现在只由**目录行**使用）—— 换名会牵动一圈判据，收益只是好看。
 */

/** 详情里的一行字段（日期用同一套排版，免得每个字段各写一遍）。 */
function Field({ label, value, mono = false }: { readonly label: string; readonly value: string; readonly mono?: boolean }): ReactNode {
  return (
    <div className="ks-field">
      <span className="ks-field-k">{label}</span>
      <span className={mono ? 'ks-field-v ks-field-v-mono' : 'ks-field-v'}>{value === '' ? '—' : value}</span>
    </div>
  )
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const sleep = async (ms: number): Promise<void> => new Promise((resolve) => { setTimeout(resolve, ms) })

/* ══════════════ 第 5 步：目录/文件的「建 / 改名 / 挪 / 复制 / 删」 ══════════════ */

/**
 * 勾选用的 **key**：`f:<doc_id>` / `d:<folder_id>`。
 *
 * ⚠ 为什么带前缀：**同一层里目录与文件都会进勾选集合**（批量条要能同时处置"选中的 2 个目录
 *   + 3 篇文件"）⇒ 裸 id 撞车时分不清是哪一层的东西。「待分类」层只有文件，但也用**同一套**
 *   key（不许为它单开一套 —— 那正是"复制出第二套"）。
 */
const PICK_FILE = 'f:'
const PICK_DIR = 'd:'
const pickFileKey = (docId: string): string => PICK_FILE + docId
const pickDirKey = (folderId: string): string => PICK_DIR + folderId
const idsOfKind = (keys: Iterable<string>, prefix: string): string[] =>
  [...keys].filter((k) => k.startsWith(prefix)).map((k) => k.slice(prefix.length))
/** 勾选集合里的**文件** id（顺序照 Set 的插入序）。 */
const docIdsOf = (keys: Iterable<string>): string[] => idsOfKind(keys, PICK_FILE)
/** 勾选集合里的**目录** id。 */
const folderIdsOf = (keys: Iterable<string>): string[] => idsOfKind(keys, PICK_DIR)
/** 勾选集合 → 接口要的 `{kind,id}` 条目（`members/*` 那一族共用这一份）。 */
const memberItemsOf = (keys: Iterable<string>): KsKbMemberItem[] => [
  ...docIdsOf(keys).map((id) => ({ kind: 'file' as const, id })),
  ...folderIdsOf(keys).map((id) => ({ kind: 'folder' as const, id })),
]
/** 扁平清单里的路径（找不到就退回 id —— **不许**编一个假路径）。 */
const pathOfFolder = (rows: readonly KsKbFlatFolder[], folderId: string): string =>
  rows.find((f) => f.folder_id === folderId)?.path ?? folderId

/**
 * 一个批量动作的结果：**逐件跑、逐件记**。
 * ⚠ 为什么不是 `try` 包一整个循环：目录操作是**逐条真落库**的（后端没有批事务），
 *   第 2 件失败时第 1 件**已经生效**了 —— 谎报"全都失败"或"全都成功"都是假话。
 */
interface OpOutcome { readonly done: number; readonly failed: ReadonlyArray<{ label: string; message: string }> }

/** 把 `OpOutcome` 说成人话（成功几件 / 失败几件 + 每一件的原话）。 */
function outcomeText(verb: string, out: OpOutcome): string {
  const bad = out.failed.map((f) => `${f.label}：${f.message}`).join('；')
  if (out.failed.length === 0) return `${verb} ${String(out.done)} 件。`
  return `${verb} ${String(out.done)} 件；有 ${String(out.failed.length)} 件没成：${bad}`
}

/**
 * 第 6 步：**提问的范围** —— 业主口径是「目录树就是提问范围的唯一载体」（不要单独的收藏夹/集合）。
 *
 * ⚠⚠ 与**收藏夹**（书签夹，`params.folder_id`）**不是一回事**，名字刻意不同防歧义：
 *   · 收藏夹范围在引擎里**只对证据后置打标/过滤**，**不动检索**；
 *   · 这里的范围是**在检索层**生效的（六条召回通道全部限定）—— 范围内没有**就是没有**，
 *     绝不会拿范围外的命中来凑。两者同时给出时，引擎侧的有效证据语义是**交集**。
 */
interface AskScope {
  /** 知识库目录 id：引擎展开成"它们**及其所有下级**"；多个 = **并集**（业主口径）。 */
  readonly folderIds: readonly string[]
  /** 显式文件 id：**「待分类」**那一层那些还没进任何目录的文件只能这样限定。 */
  readonly docIds: readonly string[]
  /** 范围的**人话名字**（只说"选了什么"；**篇数一律以引擎回显为准**，不自己编）。 */
  readonly label: string
}

/**
 * 勾选的 key（`f:`/`d:`）→ 提问范围。
 *
 * ⚠ 一件都没勾 ⇒ `null`（**不许**退化成"空范围"或"全库"：两者会被引擎当成不同的东西，
 *   前者一次检索都不做、后者是全库检索）。
 */
function askScopeOf(keys: readonly string[], rows: readonly KsKbFlatFolder[]): AskScope | null {
  const folderIds = folderIdsOf(keys)
  const docIds = docIdsOf(keys)
  if (folderIds.length === 0 && docIds.length === 0) return null
  const names = folderIds.map((id) => `「${pathOfFolder(rows, id)}」`)
  let label: string
  if (folderIds.length > 0 && docIds.length > 0) {
    label = `${String(folderIds.length)} 个目录 + ${String(docIds.length)} 篇文件的并集`
  } else if (folderIds.length > 1) {
    label = `${String(folderIds.length)} 个目录的并集（${names.join('、')}）`
  } else if (folderIds.length === 1) {
    label = `${names[0]}及其全部下级`
  } else {
    label = `${String(docIds.length)} 篇文件`
  }
  return { folderIds, docIds, label }
}

/** 范围 chip / 面板抬头上的那句"在**哪儿**提问"（业主口径里"多选取并集"的那句话就在这儿）。 */
function askWhereText(scope: AskScope): string {
  const nf = scope.folderIds.length
  const nd = scope.docIds.length
  if (nf > 0 && nd > 0) {
    return `在这 ${String(nf)} 个目录 + ${String(nd)} 篇文件的并集里提问`
  }
  if (nf > 1) return `在这 ${String(nf)} 个目录的并集里提问`
  if (nf === 1) return `在${scope.label}里提问`
  return `在这 ${String(nd)} 篇文件里提问`
}

/** 加载相位（只有"整个页面/某一级"的加载走它；翻页另有自己的忙标记）。 */
type LoadPhase = 'loading' | 'ready' | 'error'

/** 上传面板的相位。 */
type UpPhase = 'idle' | 'running' | 'done' | 'error'

/** 目录树里一个节点的"孩子"缓存（key = `'root'` 或 folder_id）。 */
interface TreeNode {
  readonly kids?: readonly KsKbFolder[]
  readonly loading?: boolean
  readonly error?: string
}

/**
 * 知识库 tab 的 body。
 *
 * @param props - 框架给的运行时 props（含 `useTabInfo`）与本插件注入的面。
 * @returns 知识库页；`params.page` 指向尚未实现的页时给**诚实的占位**。
 */
export function KsKnowledgePage({ useTabInfo }: KsPaneBodyProps & KsKbInjected): ReactNode {
  ensureKsStyles()
  const { tab } = useTabInfo()
  /* 批·P0（2026-09-23）：换页走**页内状态**（业主报障「点到别的就黑屏」——根因：
     tab.actions.openTab(replaceTab) 在自己页签里拆自己；navigation 只读、无原地换参
     接口（ksSidebar 真签名核实）。页内切换零宿主交互=绝不自拆）。 */
  const [pageOverride, setPageOverride] = useState<string | null>(null)
  const page = pageOverride ?? (tab.navigation.params as { page?: string } | undefined)?.page ?? 'manage'

  /** 当前这一级：`id === null` = **最外层**（库里 `parent_id IS NULL` 的那些目录 + 还没归位的文件）。 */
  const [levelId, setLevelId] = useState<string | null>(null)
  /** 当前这一级**直接**放的子目录 / 文件 / 文件总数（全部来自后端，顺序照后端给的）。 */
  const [subs, setSubs] = useState<readonly KsKbFolder[]>([])
  const [files, setFiles] = useState<readonly KsKbFile[]>([])
  const [filesTotal, setFilesTotal] = useState(0)
  const [fileOffset, setFileOffset] = useState(0)
  const [filesMore, setFilesMore] = useState(false)
  /** 从顶层到当前这一级的目录链（后端 `data.breadcrumb`；最外层是 `[]`）。 */
  const [crumb, setCrumb] = useState<readonly KsKbFolder[]>([])
  const [phase, setPhase] = useState<LoadPhase>('loading')
  const [errMsg, setErrMsg] = useState('')
  /** 只用于翻页（不整页转圈）：翻页时禁掉分页按钮。 */
  const [busy, setBusy] = useState(false)

  /** 左列目录树：展开集合 + 每个节点的孩子缓存（**按需展开，一次只拉一层**）。 */
  const [tree, setTree] = useState<Record<string, TreeNode>>({})
  /**
   * `tree` 的**同步镜像**（只读）。
   * ⚠ 为什么需要它：`loadLevel` 里"祖先链上哪几级的孩子还没拉过"必须**当场读**，
   *   而 `tree` 是异步 state（同一轮里连改几次读到的是旧值）⇒ 读 state 会重复拉或漏拉。
   *   写入永远走 `setTree`，这里只跟着镜像（见 `putTree`）。
   */
  const treeRef = useRef<Record<string, TreeNode>>({})
  const putTree = useCallback((next: Record<string, TreeNode>): void => {
    treeRef.current = next
    setTree(next)
  }, [])
  const [treeOpen, setTreeOpen] = useState<ReadonlySet<string>>(() => new Set<string>(['root']))

  const [search, setSearch] = useState('')
  const [openDoc, setOpenDoc] = useState<string | null>(null)
  /** 行尾「⋮」菜单**同一时刻只开一个**（存的是行 id，不是布尔）。 */
  const [menuFor, setMenuFor] = useState<string | null>(null)

  /**
   * 当前这一层是**目录层**还是**「待分类」层**（第 4 步）。
   *
   * ⚠ 业主"不要两个页面"的落点就在这里：导入不再是一页单独的东西，而是**这一层的面板**；
   *   `params.page === 'ingest'`（开始页 ▾ 菜单里的「文件导入」）进来也是**直接落到这一层**。
   */
  const [layer, setLayer] = useState<'folder' | 'inbox'>(page === 'ingest' ? 'inbox' : 'folder')

  /** 「待分类」这一层的数据（分页口径与后端 `/kb/inbox` 的 limit/offset 一致）。 */
  const [inbox, setInbox] = useState<readonly KsKbInboxItem[]>([])
  const [inboxTotal, setInboxTotal] = useState(0)
  /** 那一层**读没读过**（没读过就不显示篇数 —— 显示 `0 篇待分类` 是撒谎）。 */
  const [inboxKnown, setInboxKnown] = useState(false)
  const [inboxOffset, setInboxOffset] = useState(0)
  const [inboxMore, setInboxMore] = useState(false)
  /** 勾选的 doc_id（批量动作的对象；翻页/换层都**不清**，但离开这一层时会清）。 */
  const [picked, setPicked] = useState<ReadonlySet<string>>(() => new Set<string>())
  /**
   * 行尾 ⋮ 菜单 / 工具栏打开的那个动作面板（第 5 步把它扩成"**一套**面板、多种动作"）：
   *   · `place`     —— 「待分类」层：把这批文件放进某个**现有**目录（confirm `action='existing'`）
   *   · `new`       —— 「待分类」层：在建议位置**新建**一个目录再放进去（confirm `action='new'`）
   *   · `del`       —— 「待分类」层：真删文档（**不可逆**；二次确认）
   *   · `mkdir`     —— 在当前这一级**新建下级目录**
   *   · `rename`    —— 目录**改名**（只改库里的名字，**绝不动磁盘文件**）
   *   · `move`      —— 把选中的目录/文件**挪到**某个目录（`folders/{id}/move` + `members/move`）
   *   · `copy`      —— 把选中的目录/文件**复制到**某个目录（多一处位置，**不是**多一份文件）
   *   · `add`       —— 把**最外层**那批文件挂进某个目录（`members`；顶层文件没有来源目录）
   *   · `remove`    —— 把选中的文件**从这一层拿掉**（只删归属行，**不删文件**）
   *   · `folder-del` —— 删目录（**先**拉 `delete-preview` 把影响如实列出来，再二选一）
   * `targets` 是勾选 key（`f:`/`d:`）—— 逐条 = 一个 key；批量 = 勾选的那些。
   */
  const [action, setAction] = useState<
    { kind: 'place' | 'new' | 'del' | 'mkdir' | 'rename' | 'move' | 'copy' | 'add'
      | 'remove' | 'folder-del'; targets: readonly string[] } | null>(null)
  /** 删目录的**真实影响**（逐个 `delete-preview` 拉回来的；`null` = 还在读）。 */
  const [delPreview, setDelPreview] = useState<readonly KsKbDeletePreview[] | null>(null)
  /** 上传面板里那份**逐篇只读预览**是否展开（复活的 `KsIngestPanel`，见 §4① 的裁定）。 */
  const [upPreview, setUpPreview] = useState(false)
  /** 选择器里挑中的目录（`'place'` 与 `'new'` 的父目录）。 */
  const [pickFolder, setPickFolder] = useState<string>('')
  const [pickQuery, setPickQuery] = useState('')
  /** 新建目录的名字（默认 = 后端给的缺的那一段）。 */
  const [newName, setNewName] = useState('')
  /** 一次动作的结果/失败原话（如实显示，不美化）。 */
  const [actMsg, setActMsg] = useState('')
  /** 记录目录选择器用的**整棵树的扁平清单**（懒加载一次；1127 个目录约 80KB）。 */
  const [flatFolders, setFlatFolders] = useState<readonly KsKbFlatFolder[]>([])
  /** 后端下发的处理状态中文标签（拿不到就用本文件那份兜底）。 */
  const [stageLabels, setStageLabels] = useState<Record<string, string>>(STAGE_LABELS)
  /** 「重来一次」是否在跑（跑的时候轮询状态，跑完自动重读这一层）。 */
  const [reingesting, setReingesting] = useState(false)

  /* ── 「补全分类号」（2026-09-22 自愈机制）──
     业主口径：「这 380 篇**不要手动去补**……要修的是**机制**，让插件**自己能靠自己的机制
     完成工作**。」⇒ 这一层就是那个机制的入口：按一下，后台逐篇查、逐篇补，进度与
     **失败清单**都如实显示。
     ⚠ `ccsMissing === null` = **还没读到**（不许拿本地已知的数字冒充 —— 与 `inboxSeen`
       同一条纪律）。 */
  const [ccsMissing, setCcsMissing] = useState<number | null>(null)
  /** 最近一批的进度（null = 还没问过）。 */
  const [ccsStatus, setCcsStatus] = useState<KsKbCcsBackfillStatus | null>(null)
  /** 这一批是否在跑（跑的时候轮询，跑完自动重读这一层）。 */
  const [ccsRunning, setCcsRunning] = useState(false)

  /* ── 第 6 步：按目录范围提问（范围 chip + 提问面板 + 答案区）──
     ⚠ `askScope === null` = **还没选范围**（这时提问入口是禁用的，不许悄悄变成全库提问）。 */
  const [askScope, setAskScope] = useState<AskScope | null>(null)
  const [askOpen, setAskOpen] = useState(false)
  const [askQ, setAskQ] = useState('')
  const [askPhase, setAskPhase] = useState<'idle' | 'running' | 'done' | 'error'>('idle')
  const [askMsg, setAskMsg] = useState('')
  const [askRes, setAskRes] = useState<KsAnswerResult | null>(null)
  /**
   * 范围的**权威规模**（`POST /kb/scope/resolve`；篇数 = 目录子树里的 ∪ 显式文件）。
   * `null` = 还没读到（不许拿本地已知的数字冒充）。
   */
  const [askCounts, setAskCounts] = useState<{ folder_count: number; doc_count: number } | null>(null)
  /** 数不出来时的**原话**（例如目录不存在 ⇒ 引擎 404 的原话；点出来就能看见）。 */
  const [askCountErr, setAskCountErr] = useState('')

  /** 上传面板。 */
  const [upOpen, setUpOpen] = useState(false)
  const [upDir, setUpDir] = useState('')
  const [upPhase, setUpPhase] = useState<UpPhase>('idle')
  const [upMsg, setUpMsg] = useState('')
  /** 导入前的**只读体检**（原「入库预览」那页的能力，第 4 步并进这里）。 */
  const [upCheck, setUpCheck] = useState('')
  /**
   * 导入时是否**覆盖重导**（`/ingest/bulk` 的 `reingest`）。
   * ⚠ 默认 **false**：它会删掉同标准号的旧文档再建新的 ⇒ 必须由人显式打开。
   */
  const [upReingest, setUpReingest] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  /** 第 6 步：范围规模的**请求序号**（换了范围 ⇒ 旧请求的结果作废，不许挂在新的范围上）。 */
  const askSeqRef = useRef(0)

  /**
   * 拿一次会话（`fetchSession` 同源 `/ks/session`）跑 `fn`；**401 自愈一次**
   * （token 每次起引擎都轮换，镜像 `KsFilesView.fetchTreeData` 的既有写法）。
   */
  const withSession = useCallback(async <T,>(
    fn: (port: number, token: string) => Promise<T>, signal?: AbortSignal,
  ): Promise<T> => {
    let session = await fetchSession(signal)
    try {
      return await fn(session.engine.port, session.token)
    } catch (error) {
      if (error instanceof EngineAuthError && signal?.aborted !== true) {
        session = await fetchSession(signal)
        return await fn(session.engine.port, session.token)
      }
      throw error
    }
  }, [])

  /**
   * 载入**某一级**（目录列表 + 这一级直接放的文件那一页）。
   *
   * ⚠ 两次请求都**只拉这一级**（方案 §七的性能红线：不许一次把全库 1127 个目录/3 万篇拉进来）。
   */
  const loadLevel = useCallback(async (id: string | null, offset: number, opts: { silent?: boolean } = {}): Promise<void> => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    if (opts.silent !== true) { setPhase('loading'); setErrMsg('') }
    setBusy(true)
    try {
      const [level, items] = await withSession(async (port, token) => {
        const l = await fetchKbFolders(port, token, id, { signal: ctrl.signal })
        // ⚠ 最外层要传 `'root'`（源码里 `root`/`null` 都当顶层；路由路径参数不能为空）。
        const p = await fetchKbFolderItems(port, token, id ?? 'root', {
          limit: FILE_PAGE_SIZE, offset, signal: ctrl.signal,
        })
        return [l, p] as const
      }, ctrl.signal)
      if (ctrl.signal.aborted) return
      const crumbs = level.breadcrumb.length > 0 ? level.breadcrumb : items.breadcrumb
      setSubs(level.subfolders)
      setCrumb(crumbs)
      setFiles(items.items)
      setFilesTotal(items.total)
      setFileOffset(items.offset)
      setFilesMore(items.has_more)
      setPhase('ready')
      /* 左列树：把这一级的子目录缓存进树（**这一级的下一层**就是它），
         并把它自己展开（用户点进来就是要看里面）。 */
      const key = id ?? 'root'
      const withLevel: Record<string, TreeNode> = { ...treeRef.current, [key]: { kids: level.subfolders } }
      if (id !== null) setTreeOpen((prev) => new Set([...prev, id]))
      /* 面包屑上**每一级的下一层**都补进树缓存（面包屑是后端给的 ⇒ 不用自己推路径），
         这样"直接深链到某一级 / 从深链返回"时左列能一路展开到它、也不会有空壳节点。
         ⚠ 每一级只拉它**自己那一层**（不是整棵树）。 */
      const ancestors: string[] = crumbs
        .map((node) => node.folder_id)
        .filter((fid) => withLevel[fid]?.kids === undefined)
      putTree(withLevel)
      for (const fid of ancestors) {
        const kids = await withSession(async (port, token) =>
          (await fetchKbFolders(port, token, fid, { signal: ctrl.signal })).subfolders, ctrl.signal)
        if (ctrl.signal.aborted) return
        putTree({ ...treeRef.current, [fid]: { kids } })
      }
    } catch (error) {
      if (ctrl.signal.aborted) return
      setPhase('error')
      setErrMsg(errorText(error))
    } finally {
      if (!ctrl.signal.aborted) setBusy(false)
    }
  }, [withSession])

  /** 当前这一级的显示名（最外层是「知识库」）。 */
  const currentFolder = levelId === null ? null : crumb.find((f) => f.folder_id === levelId) ?? null
  const levelName = currentFolder?.name ?? '知识库'

  /**
   * 展开/收起树里一个节点（**按需拉它那一层**）。
   * ⚠ key 用 `'root'` 表示最外层 —— 树的第一行就是它。
   */
  const toggleTree = useCallback(async (key: string): Promise<void> => {
    if (treeOpen.has(key)) {
      setTreeOpen((prev) => { const next = new Set(prev); next.delete(key); return next })
      return
    }
    setTreeOpen((prev) => new Set([...prev, key]))
    const known = treeRef.current[key]
    if (known?.kids !== undefined || known?.loading === true) return
    putTree({ ...treeRef.current, [key]: { ...known, loading: true, error: undefined } })
    try {
      const kids = await withSession(async (port, token) =>
        (await fetchKbFolders(port, token, key === 'root' ? null : key, {})).subfolders)
      putTree({ ...treeRef.current, [key]: { kids } })
    } catch (error) {
      putTree({ ...treeRef.current, [key]: { loading: false, error: errorText(error) } })
    }
  }, [putTree, treeOpen, withSession])

  /** 进某一级（左列树点名字 / 右侧点目录行 / 面包屑点某一节都走这里）。 */
  const goto = useCallback((id: string | null): void => {
    setLayer('folder')
    setLevelId(id)
    setOpenDoc(null)
    setMenuFor(null)
    setAction(null)
    /* ⚠ 换层就**清掉勾选**（第 6 步补）：勾选是"对这一层那几条东西"的选择，
       带着它跨层会把两个层的语义混起来 —— 尤其第 6 步的「在此范围内提问」会拿勾选当范围
       （在「法律法规」这一级里点提问，却问了上一层的「标准」—— 那不是惊喜，是 bug）。 */
    setPicked(new Set())
    /* ⚠ 搜索串**不清**（沿用 5i 的既有口径：搜索是**页面级**的一个过滤条件，换层后继续生效 ——
       目录层按目录名、文件层按标准号/名称）。框里始终看得见那个词，不会变成"幽灵过滤"；
       真被筛空时给的是**搜索空态**（含「清除搜索」），不会假装"这一层本来就没东西"。 */
    void loadLevel(id, 0)
  }, [loadLevel])

  /** 返回上一层（最外层没有上一层 ⇒ 按钮置灰，见渲染；「待分类」层的上一层是最外层）。 */
  const goUp = useCallback((): void => {
    if (layer === 'inbox') { goto(null); return }
    if (levelId === null) return
    const parent = crumb.length >= 2 ? crumb[crumb.length - 2] : null
    goto(parent === null ? null : parent.folder_id)
  }, [crumb, goto, layer, levelId])

  /** 翻到文件的另一页（只重拉文件那一页，不动目录层）。 */
  const goPage = useCallback((offset: number): void => {
    if (offset < 0) return
    void loadLevel(levelId, offset, { silent: true })
  }, [levelId, loadLevel])

  // ══════════════════ 第 4 步：「待分类」这一层 ══════════════════

  /**
   * 载入「待分类」的那一页（`GET /kb/inbox`）。
   * ⚠ 与目录层**同一个 `phase`**（整页加载态只有一处，界面上不会出现"两个转圈"）。
   */
  const loadInbox = useCallback(async (offset: number, opts: { silent?: boolean } = {}): Promise<void> => {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    if (opts.silent !== true) { setPhase('loading'); setErrMsg('') }
    setBusy(true)
    try {
      const [page, labels] = await withSession(async (port, token) => {
        const p = await fetchKbInbox(port, token, {
          limit: INBOX_PAGE_SIZE, offset, signal: ctrl.signal,
        })
        /* 标签由后端下发（唯一所有者）；读不到就保持本文件那份兜底 —— 如实降级，不静默改成空。 */
        let lb: { labels: Record<string, string> } | null = null
        try {
          lb = await fetchKbStageLabels(port, token, ctrl.signal)
        } catch { lb = null }
        return [p, lb] as const
      }, ctrl.signal)
      if (ctrl.signal.aborted) return
      if (labels !== null && Object.keys(labels.labels).length > 0) setStageLabels(labels.labels)
      setInbox(page.items)
      setInboxTotal(page.total)
      setInboxKnown(true)
      setInboxOffset(page.offset)
      setInboxMore(page.has_more)
      setPhase('ready')
    } catch (error) {
      if (ctrl.signal.aborted) return
      setPhase('error')
      setErrMsg(errorText(error))
    } finally {
      if (!ctrl.signal.aborted) setBusy(false)
    }
  }, [withSession])

  /**
   * 只取「待分类」的**篇数**（左列那一行要显示它）。
   * ⚠ 用 `limit=1` 拉一页（`total` 是后端给的**全量**部数，不是这一页的行数）——
   *   不为一个数字把 381 篇都拉下来。
   */
  const refreshInboxBadge = useCallback(async (): Promise<void> => {
    try {
      const page = await withSession((port, token) => fetchKbInbox(port, token, { limit: 1 }))
      setInboxTotal(page.total)
      setInboxKnown(true)
    } catch { /* 读不到就不显示篇数（如实留白），不打断目录层 */ }
  }, [withSession])

  /** 进「待分类」这一层（左列那一行 / `params.page==='ingest'` / 导入完成后都走这里）。 */
  const gotoInbox = useCallback((): void => {
    setLayer('inbox')
    setOpenDoc(null)
    setMenuFor(null)
    setAction(null)
    setActMsg('')
    /* 同 `goto`：换层清勾选（否则"在待分类里勾了一篇"会带着上一层的目录勾选一起进范围）。 */
    setPicked(new Set())
    void loadInbox(0)
  }, [loadInbox])

  // 挂载即载入（引擎 port/token 每次启动轮换 ⇒ 不缓存跨次会话）。
  // ⚠ 这一段**必须放在 `loadInbox` / `refreshInboxBadge` 声明之后**（它们都是 const，
  //   提前引用是 TDZ 报错 —— 本批第一版就把它放在前面，tsc 当场红）。
  useEffect(() => {
    /* ⚠ `params.page === 'ingest'`（开始页 ▾ 菜单里的「文件导入」）**直接落到「待分类」这一层**：
      业主"不要两个页面" ⇒ 导入不再是单独一页，它就是这一层上的一个面板。 */
    if (page === 'ingest') {
      void loadInbox(0)
      return () => { abortRef.current?.abort() }
    }
    void loadLevel(null, 0)
    /* 左列那一行要显示「待分类」有多少篇 ⇒ 顺手取一次部数（不带页面转圈）。 */
    void refreshInboxBadge()
    return () => { abortRef.current?.abort() }
  }, [loadInbox, loadLevel, page, refreshInboxBadge])

  /**
   * 目录选择器的数据（**懒加载一次**）：整棵树的扁平清单，供"按名字找目录"。
   * ⚠ 只在真要选目录时才拉（业主日常浏览这一页不需要它）。
   */
  const ensureFlatFolders = useCallback(async (): Promise<void> => {
    if (flatFolders.length > 0) return
    try {
      const rows = await withSession((port, token) => fetchKbFoldersFlat(port, token))
      setFlatFolders(rows)
    } catch (error) {
      setActMsg(`读不到目录清单：${errorText(error)}`)
    }
  }, [flatFolders.length, withSession])

  /* ══════════════════ 第 6 步：按目录范围提问 ══════════════════
   * 三件事各自有**唯一所有者**：
   *   ① `loadAskCounts` —— 范围的**权威规模**（引擎 `/kb/scope/resolve`，不自己猜篇数）；
   *   ② `openAsk` / `askHere` / `clearAsk` —— 范围从哪来（勾选 / 当前这一级 / 清掉）；
   *   ③ `runAsk` —— 真发一次问（`POST /ks/answer`，**带上范围**），把答案/原话落进 state。
   */

  /**
   * 读一次范围的规模（**发问之前**就把 chip 上的篇数写成引擎给的权威数字）。
   * ⚠ 篇数 = 目录子树里的文件 ∪ 显式文件（去重后计数 —— 一篇挂多处只算一次，
   *   与 `/kb/scope/resolve` 的口径一致）。⚠ 任一目录不存在 ⇒ 引擎 404，**原话**显示出来。
   */
  const loadAskCounts = useCallback(async (scope: AskScope): Promise<void> => {
    askSeqRef.current += 1
    const seq = askSeqRef.current
    setAskCounts(null)
    setAskCountErr('')
    try {
      const r = scope.folderIds.length > 0
        ? await withSession((port, token) => resolveKbScope(port, token, scope.folderIds))
        : { doc_ids: [] as string[], folder_count: 0 }
      /* ⚠ 期间又换了范围 ⇒ 这次的结果**作废**（否则 chip 会把 A 的篇数挂在 B 上）。 */
      if (askSeqRef.current !== seq) return
      const docs = new Set<string>([...r.doc_ids, ...scope.docIds])
      setAskCounts({ folder_count: r.folder_count, doc_count: docs.size })
    } catch (error) {
      if (askSeqRef.current !== seq) return
      setAskCountErr(errorText(error))
    }
  }, [withSession])

  /**
   * 范围 chip / 面板抬头要写**目录名** —— 名字从"这一页**已经读到的**那些"取：
   * 面包屑（祖先链）+ 这一级的子目录（路径照面包屑拼）。
   *
   * ⚠ 为什么不顺手再拉一份全库扁平清单（`/kb/folders/flat`，真库 ~1127 个目录 / ~80KB）：
   *   勾选与"当前这一级"能指到的目录**只可能**来自这两处（换层会清勾选），为几个名字
   *   拉整棵树是白花的流量；两处都找不到时才退回 **id**（`pathOfFolder` 的既有兜底 ——
   *   **不许**编一个假名字）。
   */
  const folderRowsForAsk = useMemo((): readonly KsKbFlatFolder[] => {
    const rows: KsKbFlatFolder[] = []
    const seen = new Set<string>()
    const push = (id: string, name: string, parentId: string | null, path: string): void => {
      if (seen.has(id)) return
      seen.add(id)
      rows.push({ folder_id: id, parent_id: parentId, name, path, depth: 1 })
    }
    crumb.forEach((node, i) => {
      push(node.folder_id, node.name, node.parent_id, crumb.slice(0, i + 1).map((n) => n.name).join(' › '))
    })
    const base = crumb.map((n) => n.name).join(' › ')
    for (const kid of subs) {
      push(kid.folder_id, kid.name, levelId, base === '' ? kid.name : `${base} › ${kid.name}`)
    }
    return rows
  }, [crumb, levelId, subs])

  /** 打开提问面板并把范围设成 `keys`（勾选的那些；一件都没有 ⇒ 什么也不做）。 */
  const openAsk = useCallback((keys: readonly string[]): void => {
    const scope = askScopeOf(keys, folderRowsForAsk)
    if (scope === null) return
    /* ⚠ 换范围 ⇒ **领一个新号**：正在飞的那次问答/数篇数回来时会被判作废
       （否则"问 A（慢）→ 换成 B → A 后回"会把 A 的答案挂到 B 的范围上，见 `runAsk`）。 */
    askSeqRef.current += 1
    setAskScope(scope)
    setAskOpen(true)
    setAskRes(null)
    setAskMsg('')
    setAskPhase('idle')
    void loadAskCounts(scope)
  }, [folderRowsForAsk, loadAskCounts])

  /** 清掉范围（**同时收起提问面板**）—— 清掉之后**没有**"不限定范围的提问"这条路：
   *  这一页的提问入口永远是"在某个范围里问"，全库提问是别处的事（不许在这里悄悄发生）。 */
  const clearAsk = useCallback((): void => {
    askSeqRef.current += 1
    setAskScope(null)
    setAskOpen(false)
    setAskRes(null)
    setAskMsg('')
    setAskPhase('idle')
    setAskCounts(null)
    setAskCountErr('')
  }, [])

  /**
   * 「在此范围内提问」按下去时的范围：**勾选的并集优先**（业主：多选几个目录 = 取并集），
   * 没有勾选时用**当前这一级**（它 + 全部下级）；最外层/「待分类」又没勾选 ⇒ 没有范围。
   *
   * ⚠ 为什么"勾选优先"：勾选是用户**显式**做的选择，批量条上就写着「已选 N 个目录」；
   *   忽略它反而会让"我选了三个目录，点提问却只在一个目录里问"变成一个说不清的惊喜。
   *   最终到底在什么范围里问，**按钮的 title 与范围 chip 都会写出来**（不是靠猜）。
   */
  const askHereKeys = useMemo((): readonly string[] => {
    if (picked.size > 0) return [...picked]
    if (layer === 'folder' && levelId !== null) return [pickDirKey(levelId)]
    return []
  }, [layer, levelId, picked])

  /** 上面那批 key 展开成的范围（按钮 title 上写的**就是这个**，点之前就说清会问到哪儿）。 */
  const askHereScope = useMemo(() => askScopeOf(askHereKeys, folderRowsForAsk),
    [askHereKeys, folderRowsForAsk])

  /** 这一级**为什么**没有可问的范围（禁用的原话；有范围时是空串）。 */
  const askHereWhy = askHereScope !== null ? ''
    : (layer === 'inbox'
      ? '「待分类」不是目录：先勾选要问的那几篇（可多选），再点这里'
      : '你在最外层 —— 最外层就是整个知识库，没有范围可言：进到某个目录里再问，或先勾选几个目录（多选=并集）')

  /**
   * 真问一次。⚠ 范围**一定**随请求发出去（`params.kb_folder_ids` / `kb_doc_ids`），
   * 回参里的 `scope` 是引擎的权威回显 —— 答案区照它显示"这次到底在什么范围里检索的"。
   *
   * ⚠⚠ **2026-09-21（复核 MEDIUM-2 打回后补）**：`askSeqRef` 以前**只护 chip 的篇数**
   * （`loadAskCounts`），答题这一路**没有新鲜度检查** —— 而 `openAsk`/`clearAsk` 会把
   * `askPhase` 重置回 `idle`，于是"问 A（慢）→ 换范围再问 B → B 先回 → A 后回"时，
   * **A 的答案会盖在 B 的范围上**（chip 写的是 B）。现在给结果与相位**同款序号守卫**：
   * 发起时领一个号，回来后号变了就**整个丢弃**（连相位都不动，免得把 B 的 'done' 打回 'running'）。
   */
  const runAsk = useCallback(async (): Promise<void> => {
    const text = askQ.trim()
    if (text === '' || askScope === null) return
    askSeqRef.current += 1
    const seq = askSeqRef.current
    setAskPhase('running')
    setAskMsg('')
    try {
      const out = await withSession((port, token) => askKsAnswer(port, token, text, {
        kbFolderIds: askScope.folderIds,
        kbDocIds: askScope.docIds,
      }))
      if (askSeqRef.current !== seq) return   // 期间换了范围/又问了别的 ⇒ 这次作废
      setAskRes(out)
      setAskPhase('done')
    } catch (error) {
      if (askSeqRef.current !== seq) return
      setAskRes(null)
      setAskPhase('error')
      setAskMsg(errorText(error))
    }
  }, [askQ, askScope, withSession])

  /**
   * **第 6 步的提问入口**（业主 2026-09-22 定了它的位置）：「在此范围内提问」+ 范围 chip
   * 放在**当前文件夹名那一行**（`.ks-list-cap`，搜索框**上面**那一行）——
   * 业主原话："按钮改到搜索栏上面显示文件夹名称的 bar 上，这样就很清楚是在这个文件夹内进行搜索"。
   *
   * ⚠ 目录层与「待分类」层**共用这一个片段**（不许各写一套，否则"位置"就有了两个所有者）。
   * ⚠ 范围 chip **没打开提问面板时也必须看得见**（按钮搬出工具栏之后尤其重要：不然用户不知道
   *   自己正被限定在一个范围里）—— 这一行挤不下就**折行**（`.ks-list-cap{flex-wrap:wrap}`），
   *   不许把 chip 挤没、也不许让它溢出右缘（真浏览器侧由 `askCheck` 量）。
   * ⚠ 禁用 + 原因（最外层 / 「待分类」没勾选）的行为**一字不变**：**不给**"悄悄变成全库提问"的路。
   */
  const askEntry = (
    <>
      <Button
        variant="outline"
        size="sm"
        className="ks-ask-open"
        aria-expanded={askOpen}
        disabled={askHereScope === null}
        title={askHereScope !== null
          ? `在${askHereScope.label}里提问（只在这个范围里检索；多选=并集）`
          : askHereWhy}
        onClick={() => { void openAsk(askHereKeys) }}
      >
        {/* 图标语义（诊断 J1，2026-09-22）：这里原来是**放大镜**——那是"搜索"的字面义，
            挂在"提问"按钮上会把用户带偏（第一眼都当搜索框）。换成问号 = 提问的字面义。
            宿主图标全集核过（ui-primitives/lib/types/icons/*.d.ts）：无对话气泡类，问号最贴。 */}
        <IconQuestionOutline14 />
        在此范围内提问
      </Button>
      {/* 范围 chip（业主："发起前/发起后都要能看出当前范围是什么"）：目录名 + 篇数 + 可清掉。
          ⚠ 篇数**只认引擎的数**：读中就说"正在数…"，读不到就把**原话**显示出来（含 404）。 */}
      {askScope === null ? null : (
        <span className="ks-ask-chip" data-ks-ask-chip="on" title={askWhereText(askScope)}>
          <span className="ks-ask-chip-tag">范围</span>
          <span className="ks-ask-chip-name">{askScope.label}</span>
          <span className="ks-ask-chip-n">
            {askCountErr !== ''
              ? `数不出来：${askCountErr}`
              : (askCounts === null
                ? '正在数…'
                : `${String(askCounts.folder_count)} 个目录 · ${String(askCounts.doc_count)} 篇`)}
          </span>
          <button
            type="button"
            className="ks-ask-chip-x"
            aria-label="清掉范围"
            title="清掉范围（连提问面板一起收起；清掉之后这一页不会做「不限定范围」的提问）"
            onClick={clearAsk}
          >
            <IconCloseOutline16 />
          </button>
        </span>
      )}
    </>
  )

  /** 勾/取消一条（批量选择）。`key` 是 `f:`/`d:` key（见 `pickFileKey`）。 */
  const togglePick = useCallback((key: string, next: boolean): void => {
    setActMsg('')
    setPicked((prev) => {
      const out = new Set(prev)
      if (next) out.add(key)
      else out.delete(key)
      return out
    })
  }, [])

  /**
   * 打开某个动作的面板（逐条 = 一个 key；批量 = 勾选的那些）。
   *
   * ⚠ 第 5 步：删目录（`folder-del`）要**先拉影响数字**再问 —— 面板打开时就去读
   *   `GET /kb/folders/{id}/delete-preview`（每个选中的目录一条，逐个如实列出来），
   *   **不许**前端自己猜"大概有 N 篇"（任务书 §3 第 2 条）。
   */
  const openAction = useCallback((
    kind: 'place' | 'new' | 'del' | 'mkdir' | 'rename' | 'move' | 'copy' | 'add'
      | 'remove' | 'folder-del',
    targets: readonly string[],
  ): void => {
    if (kind !== 'mkdir' && targets.length === 0) return
    setActMsg('')
    setAction({ kind, targets })
    setPickQuery('')
    setDelPreview(null)
    if (kind === 'place' || kind === 'new' || kind === 'move' || kind === 'copy'
        || kind === 'add') {
      setPickFolder('')
      void ensureFlatFolders()
    }
    if (kind === 'new') {
      /* 默认父目录 = 后端给的"建议新建的父目录"（那一篇/那一批里**第一个有建议的**）。 */
      const withSug = inbox.filter((r) => targets.includes(pickFileKey(r.doc_id))
        && r.suggest_new_parent_id !== null && r.suggest_new_name !== null)
      const first = withSug[0]
      setPickFolder(first?.suggest_new_parent_id ?? '')
      setNewName(first?.suggest_new_name ?? '')
    }
    if (kind === 'rename') {
      /* 改名：预填当前名字（从当前这一级的目录行里取；取不到就空着，让用户自己填）。 */
      const fid = folderIdsOf(targets)[0] ?? ''
      setNewName(subs.find((f) => f.folder_id === fid)?.name ?? '')
    }
    if (kind === 'mkdir') setNewName('')
    if (kind === 'folder-del') {
      setDelPreview(null)
      void (async () => {
        const ids = folderIdsOf(targets)
        const out: KsKbDeletePreview[] = []
        const bad: string[] = []
        for (const fid of ids) {
          try {
            out.push(await withSession((port, token) =>
              fetchKbFolderDeletePreview(port, token, fid)))
          } catch (error) {
            bad.push(`${fid}：${errorText(error)}`)
          }
        }
        setDelPreview(out)
        if (bad.length > 0) setActMsg(`有目录的影响读不到：${bad.join('；')}`)
      })()
    }
  }, [ensureFlatFolders, inbox, subs, withSession])

  /** 把一批文件放进某个目录（`POST /kb/inbox/confirm` 的 `action='existing'`）。 */
  const placeInto = useCallback(async (targets: readonly string[], folderId: string): Promise<void> => {
    if (folderId === '') { setActMsg('先选一个目录'); return }
    setBusy(true)
    try {
      const res = await withSession((port, token) => confirmKbInbox(port, token,
        targets.map((docId) => ({
          doc_id: docId, action: 'existing' as const,
          target_folder_id: folderId, placed_by: 'kb-inbox-manual',
        }))))
      setActMsg(`已放进「${flatFolders.find((f) => f.folder_id === folderId)?.path ?? folderId}」`
        + `${String(res.confirmed)} 篇（从「待分类」拿掉 ${String(res.removed_from_pending)} 篇）。`)
      setAction(null)
      setPicked(new Set())
      await loadInbox(inboxOffset, { silent: true })
    } catch (error) {
      setActMsg(`没放成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [flatFolders, inboxOffset, loadInbox, withSession])

  /** 在指定父目录下**新建**一个目录再把这一批放进去（`action='new'`）。 */
  const placeIntoNew = useCallback(async (targets: readonly string[], parentId: string,
                                        name: string): Promise<void> => {
    const clean = name.trim()
    if (parentId === '' || clean === '') { setActMsg('父目录与新目录名都要填'); return }
    setBusy(true)
    try {
      const res = await withSession((port, token) => confirmKbInbox(port, token,
        targets.map((docId) => ({
          doc_id: docId, action: 'new' as const,
          new_parent_id: parentId, new_name: clean, placed_by: 'kb-inbox-new',
        }))))
      const parentPath = flatFolders.find((f) => f.folder_id === parentId)?.path ?? parentId
      setActMsg(`已在「${parentPath}」下新建「${clean}」并放进 `
        + `${String(res.confirmed)} 篇（新目录 ${String(res.created)} 个）。`)
      setAction(null)
      setPicked(new Set())
      await loadInbox(inboxOffset, { silent: true })
    } catch (error) {
      setActMsg(`没放成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [flatFolders, inboxOffset, loadInbox, withSession])

  /**
   * **按系统建议归位**（`action='accept'`）。
   *
   * ⚠ 只对**真有建议**的那几篇发：后端对没有建议的会回 422 `no_suggestion`，而 `confirm`
   *   是**一个事务**（一条坏 ⇒ 整批全败）⇒ 必须先把它们挑出去，并**如实数出来**告诉业主。
   */
  const acceptSuggestions = useCallback(async (targets: readonly string[]): Promise<void> => {
    const ok = targets.filter((docId) => (inbox.find((r) => r.doc_id === docId)?.suggested_folder_id ?? null) !== null)
    const skipped = targets.length - ok.length
    if (ok.length === 0) {
      setActMsg(`这 ${String(targets.length)} 篇系统都没给出建议（认不出该放哪）——`
        + '请用「放进某个目录」自己指定去处。')
      return
    }
    setBusy(true)
    try {
      const res = await withSession((port, token) => confirmKbInbox(port, token,
        ok.map((docId) => ({ doc_id: docId, action: 'accept' as const, placed_by: 'kb-inbox-accept' }))))
      setActMsg(`按建议归位 ${String(res.confirmed)} 篇`
        + (skipped > 0 ? `；${String(skipped)} 篇系统没给建议，没有动它们（它们只能手动指定去处）` : '')
        + `（从「待分类」拿掉 ${String(res.removed_from_pending)} 篇）。`)
      setAction(null)
      setPicked(new Set())
      await loadInbox(inboxOffset, { silent: true })
    } catch (error) {
      setActMsg(`没归位成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [inbox, inboxOffset, loadInbox, withSession])

  /** **重来一次**：让引擎重新解析这几篇（后台线程；进度看状态列）。 */
  const runReingest = useCallback(async (targets: readonly string[]): Promise<void> => {
    setBusy(true)
    try {
      const res = await withSession((port, token) => reingestKbDocs(port, token, targets))
      const skipped = res.skipped.map((s) => `${s.doc_id}：${s.reason}`).join('；')
      setActMsg(`已开始重来一次：${String(res.queued)} 篇排队重新解析`
        + '（状态列会从「识别中」变成「待确认」或「识别失败」，跑完自动刷新）。'
        + (skipped === '' ? '' : ` —— 这些没重来：${skipped}`))
      setAction(null)
      setReingesting(res.queued > 0)
      await loadInbox(inboxOffset, { silent: true })
    } catch (error) {
      setActMsg(`没能开始重来：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [inboxOffset, loadInbox, withSession])

  /**
   * **删掉**（不可逆）。逐篇与批量走同一条；调用点必须已经过**二次确认**（`action.kind==='del'`）。
   * ⚠ 走引擎既有的 `POST /documents/batch-delete`（`confirm:true`）：条款/向量/证据级联删，
   *   用户资产（收藏/批注）不删 —— 那是引擎的口径，界面**照实**转述。
   */
  const removeDocs = useCallback(async (targets: readonly string[]): Promise<void> => {
    setBusy(true)
    try {
      await withSession((port, token) => batchDeleteDocs(port, [...targets], token))
      setActMsg(`已删除 ${String(targets.length)} 篇（条款/向量/证据一并删除；收藏与批注是用户资产，不删）。`)
      setAction(null)
      setPicked(new Set())
      await loadInbox(inboxOffset, { silent: true })
    } catch (error) {
      setActMsg(`没删成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [inboxOffset, loadInbox, withSession])

  /* ══════════ 第 5 步：目录/文件的「建 / 改名 / 挪 / 复制 / 删」的真出口 ══════════
   * 全部是**真接口**（`routes_kb_folders.py` 第 2 步就做完了的那 10 个）；没有任何一处只改内存。 */

  /** 逐件跑、逐件记（见 `OpOutcome` 的注释：后端没有批事务，第 2 件失败时第 1 件已经生效）。 */
  const runOps = useCallback(async (
    jobs: ReadonlyArray<{ label: string; run: () => Promise<number> }>,
  ): Promise<OpOutcome> => {
    const failed: { label: string; message: string }[] = []
    let done = 0
    for (const job of jobs) {
      try {
        done += await job.run()
      } catch (error) {
        failed.push({ label: job.label, message: errorText(error) })
      }
    }
    return { done, failed }
  }, [])

  /**
   * 一个批量动作做完后的**统一收尾**：清空勾选 + 关掉面板 + **重读当前这一层**。
   * ⚠ 任务书 §3 第 3 条：不许"看起来成功了但列表没变"。
   */
  const afterAction = useCallback(async (): Promise<void> => {
    setAction(null)
    setDelPreview(null)
    setPicked(new Set())
    if (layer === 'inbox') await loadInbox(inboxOffset, { silent: true })
    else await loadLevel(levelId, fileOffset, { silent: true })
  }, [fileOffset, inboxOffset, layer, levelId, loadInbox, loadLevel])

  /** **建目录**：建在**当前这一级**下面（最外层 = 顶层目录；后端同名同层会拒成 409）。 */
  const runMkdir = useCallback(async (name: string): Promise<void> => {
    const clean = name.trim()
    if (clean === '') { setActMsg('先给新目录起个名字'); return }
    setBusy(true)
    try {
      const made = await withSession((port, token) =>
        createKbFolder(port, token, levelId, clean))
      setActMsg(`已建目录「${made.name}」`
        + (levelId === null ? '（顶层目录）' : `（建在「${levelName}」下面）`)
        + '——这一层已经重读，它就在列表里。')
      await afterAction()
    } catch (error) {
      setActMsg(`没建成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, levelId, levelName, withSession])

  /** **目录改名**：只改库里的名字（后端 `PUT /kb/folders/{id}` 的语义就是这条）。 */
  const runRename = useCallback(async (folderId: string, name: string): Promise<void> => {
    const clean = name.trim()
    if (folderId === '' || clean === '') { setActMsg('目录名不能空'); return }
    setBusy(true)
    try {
      const got = await withSession((port, token) =>
        renameKbFolder(port, token, folderId, clean))
      setActMsg(`已把目录改名为「${got.name}」（只改库里的名字，磁盘上的文件一个字都没动）。`)
      await afterAction()
    } catch (error) {
      setActMsg(`没改成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, withSession])

  /**
   * **挪到**某个目录（目录走 `folders/{id}/move`、文件走 `members/move`）。
   * ⚠ **最外层的文件挪不了**：`members/move` 要 `from_folder_id`，而顶层在库里**不是一行目录记录**
   *   （顶层那些文件本来就是"还没进任何目录"的）⇒ 那一层给的是「加进目录」，不是「挪」。
   */
  const runMove = useCallback(async (targets: readonly string[],
                                    destId: string): Promise<void> => {
    if (destId === '') { setActMsg('先选一个去处'); return }
    const folderIds = folderIdsOf(targets)
    const docIds = levelId === null ? [] : docIdsOf(targets)
    const destPath = pathOfFolder(flatFolders, destId)
    setBusy(true)
    try {
      const out = await runOps([
        ...folderIds.map((fid) => ({
          label: `目录 ${subs.find((f) => f.folder_id === fid)?.name ?? fid}`,
          run: async (): Promise<number> => {
            const r = await withSession((port, token) => moveKbFolder(port, token, fid, destId))
            return r.moved ? 1 : 0
          },
        })),
        ...(docIds.length === 0 ? [] : [{
          label: `${String(docIds.length)} 篇文件`,
          run: async (): Promise<number> => {
            const r = await withSession((port, token) => moveKbMembers(port, token,
              docIds.map((id) => ({ kind: 'file' as const, id })), levelId ?? '', destId))
            return r.moved
          },
        }]),
      ])
      setActMsg(`${outcomeText('已挪动', out)}到「${destPath}」`
        + '（挪动只改"挂在哪"，文件本身与磁盘文件都没动；一个文件可以同时属于多个目录）。')
      await afterAction()
    } catch (error) {
      setActMsg(`没挪成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, flatFolders, levelId, runOps, subs, withSession])

  /**
   * **复制到**某个目录（目录走 `folders/{id}/copy`、文件走 `members/copy`）。
   * ⚠ 复制的语义是**多一处位置**：文件只有一份、不拷副本；复制出来的目录**共享成员**
   *   （不是一棵独立的副本树）—— 界面上必须照实说，别让业主以为库里多了一份。
   */
  const runCopy = useCallback(async (targets: readonly string[],
                                    destId: string): Promise<void> => {
    if (destId === '') { setActMsg('先选一个去处'); return }
    const folderIds = folderIdsOf(targets)
    const docIds = docIdsOf(targets)
    const destPath = pathOfFolder(flatFolders, destId)
    setBusy(true)
    try {
      const out = await runOps([
        ...folderIds.map((fid) => ({
          label: `目录 ${subs.find((f) => f.folder_id === fid)?.name ?? fid}`,
          run: async (): Promise<number> => {
            await withSession((port, token) => copyKbFolder(port, token, fid, destId))
            return 1
          },
        })),
        ...(docIds.length === 0 ? [] : [{
          label: `${String(docIds.length)} 篇文件`,
          run: async (): Promise<number> => {
            const r = await withSession((port, token) => copyKbMembers(port, token,
              docIds.map((id) => ({ kind: 'file' as const, id })), destId))
            return r.added
          },
        }]),
      ])
      setActMsg(`${outcomeText('已复制', out)}到「${destPath}」`
        + '（只是多了一处位置：文件还是那一份、磁盘上没多出文件；复制出来的目录与原目录共享同一批内容，'
        + '原位后来加的东西不会跟着变）。')
      await afterAction()
    } catch (error) {
      setActMsg(`没复制成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, flatFolders, runOps, subs, withSession])

  /**
   * **加进目录**（最外层那批"还没进任何目录"的文件用这一条）。
   * ⚠ 走 `POST /kb/members`（`_add_member_in_tx`）：已经在该目录里的**幂等跳过**（如实报 skipped）。
   *   这里**不**改 `doc_filing_state` —— 它只是"挂进目录"，不是"归位确认"（归位走「待分类」层）。
   */
  const runAdd = useCallback(async (targets: readonly string[],
                                    destId: string): Promise<void> => {
    if (destId === '') { setActMsg('先选一个去处'); return }
    const docIds = docIdsOf(targets)
    const destPath = pathOfFolder(flatFolders, destId)
    setBusy(true)
    try {
      const r = await withSession((port, token) => addKbMembers(port, token, destId,
        [...docIds.map((id) => ({ kind: 'file' as const, id })),
          ...folderIdsOf(targets).map((id) => ({ kind: 'folder' as const, id }))]))
      setActMsg(`已放进「${destPath}」：新增 ${String(r.added)} 件`
        + (r.skipped > 0 ? `，${String(r.skipped)} 件本来就在那儿（跳过，没加重复行）` : '')
        + '。最外层的文件放进目录后就不在最外层了（文件只有一份；别处还挂着的照旧）。')
      await afterAction()
    } catch (error) {
      setActMsg(`没放进去：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, flatFolders, withSession])

  /** **移出**（业主 2026-09-22 定的词）= 只删这一处的归属行，**文件不删**；别处还挂着的照旧。 */
  const runRemove = useCallback(async (targets: readonly string[]): Promise<void> => {
    if (levelId === null) {
      setActMsg('最外层的文件不属于任何目录，「移出」在这里没有对象。')
      return
    }
    const docIds = docIdsOf(targets)
    if (docIds.length === 0) { setActMsg('选中的里面没有文件'); return }
    setBusy(true)
    try {
      const r = await withSession((port, token) => removeKbMembers(port, token, levelId,
        docIds.map((id) => ({ kind: 'file' as const, id }))))
      /* ⚠ 动作完成后**再如实说一遍**"文件没有删"（业主：这个动作的真相必须留在一处；
         菜单项文字被压成两个字之后，这里是唯一每次都看得见的地方）。 */
      setActMsg(`已从「${levelName}」移出 ${String(r.removed)} 篇`
        + '（只去掉这一处的归属，文件没有删；还挂在别的目录里的照旧在那里）。')
      await afterAction()
    } catch (error) {
      setActMsg(`没移出：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [afterAction, levelId, levelName, withSession])

  /**
   * **删目录**（不可逆）。`mode` 由**面板**按 `delete-preview` 的真数字给：
   *   `'reparent'` = 只删这个目录、里面的东西移到上一层；`'purge'` = 连里面的目录/文件一起删；
   *   `null` = 空目录直接删（后端对空目录忽略 mode）。
   * ⚠ 逐条跑、逐条记：第 2 个目录失败时第 1 个**已经真删了**（后端没有批事务）——
   *   消息里如实报"成了几件、哪件没成、原话"。
   */
  const runFolderDelete = useCallback(async (
    mode: 'reparent' | 'purge' | null,
  ): Promise<void> => {
    const ids = folderIdsOf(action?.targets ?? [])
    const preview = delPreview ?? []
    if (ids.length === 0) { setActMsg('没有要删的目录'); return }
    setBusy(true)
    try {
      const out = await runOps(ids.map((fid) => {
        const row = preview.find((p) => p.folder?.folder_id === fid)
        return {
          label: `目录 ${row?.folder?.name ?? fid}`,
          run: async (): Promise<number> => {
            const r = await withSession((port, token) => deleteKbFolder(port, token, fid,
              row?.is_empty === true ? null : mode))
            return r.removed ? 1 : 0
          },
        }
      }))
      setActMsg(`${outcomeText('已删目录', out)}`
        + '（"连里面的文件一起删"也只真删在所有目录里都不再出现的那些；'
        + '还挂在别处的只丢这里的归属。）')
      await afterAction()
    } catch (error) {
      setActMsg(`没删成：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [action, afterAction, delPreview, runOps, withSession])

  /** 「重来一次」跑的时候轮询状态，跑完**自动重读**这一层（不编进度条，只报真实的 done/total）。 */
  useEffect(() => {
    if (!reingesting) return undefined
    let stopped = false
    const timer = setInterval(() => {
      void (async () => {
        try {
          const st = await withSession((port, token) => fetchKbReingestStatus(port, token))
          if (stopped) return
          if (st.running) {
            setActMsg(`重来一次进行中：${String(st.done)} / ${String(st.total)} 篇跑完…`)
            return
          }
          setReingesting(false)
          const failed = st.results.filter((r) => r.status !== 'ok').length
          setActMsg(`重来一次完成：${String(st.done)} 篇跑完`
            + (failed > 0 ? `，其中 ${String(failed)} 篇仍没成（状态列里写明了原因）` : '')
            + '。下面这一层已按最新状态重读。')
          await loadInbox(inboxOffset, { silent: true })
        } catch (error) {
          if (!stopped) { setReingesting(false); setActMsg(`查重来一次进度失败：${errorText(error)}`) }
        }
      })()
    }, 3000)
    return () => { stopped = true; clearInterval(timer) }
  }, [inboxOffset, loadInbox, reingesting, withSession])

  /* ══════════════════ 「补全分类号」（自愈机制，2026-09-22）══════════════════
   *
   * 业主原话：「这 380 篇**不要手动去补**……你要找的是**修机制**，然后让插件**自己能靠
   * 自己的机制完成工作**。」「网页抓取要留着作为**备选**（有时候官方接口可能不返回一些
   * 老标准的数据）。」
   *
   * 界面这一层只做**三件事**，判据全在后端：
   *   ① 说清现在**还缺几篇**（`GET /kb/ccs/summary` 的 `missing`，**现算的**；
   *      读不到就显示"—"，不拿本地数字冒充）；
   *   ② 给一个**按一下就能补**的入口（`POST /kb/ccs/backfill`，后台跑、立刻返回）；
   *   ③ 进度与**失败清单**如实显示（`GET /kb/ccs/backfill/status` 的
   *      done/total 与 `failures`，失败逐篇带原因 —— 不合并成一句"部分失败"）。
   *
   * ⚠ **不编进度条**：只报后端给的 done/total；`running` 还是 true 就**不许**说"已完成"。
   */

  /** 读一次「还缺几篇 + 台账计数 + 最近一批进度」（只读、零网络）。 */
  const loadCcsSummary = useCallback(async (): Promise<void> => {
    try {
      const s = await withSession((port, token) => fetchKbCcsSummary(port, token))
      setCcsMissing(s.missing)
      setCcsStatus(s.backfill)
      setCcsRunning(s.backfill.running)
    } catch {
      /* 读不到就保持"—"：状态行不该因为一次读失败变成一句谎话（0 篇 ≠ 读不到）。 */
    }
  }, [withSession])

  /** **补全分类号**：让插件自己按三层链逐篇补（后台线程，立刻返回）。 */
  const runCcsBackfill = useCallback(async (): Promise<void> => {
    setBusy(true)
    try {
      const res = await withSession((port, token) => startKbCcsBackfill(port, token, {}))
      if (res.queued === 0) {
        setActMsg('没有要补的：库里每一篇标准都已经有分类号了。')
        await loadCcsSummary()
        return
      }
      setActMsg(`已开始补全分类号：${String(res.queued)} 篇排队`
        + `（共 ${String(res.plan.total)} 篇待补${res.plan.truncated ? '，这一批先补一部分' : ''}；`
        + '一篇一到几秒，跑完自动刷新）。')
      setCcsRunning(true)
    } catch (error) {
      setActMsg(`没能开始补全分类号：${errorText(error)}`)
    } finally {
      setBusy(false)
    }
  }, [loadCcsSummary, withSession])

  /** 按「停」：**跑完当前这一篇**才停；这一刻**不谎报**"已停止"。 */
  const stopCcsBackfill = useCallback(async (): Promise<void> => {
    try {
      const r = await withSession((port, token) => cancelKbCcsBackfill(port, token))
      setActMsg(r.running
        ? `已请求停止：跑完当前这一篇就停（已完成 ${String(r.done)} / ${String(r.total)} 篇）。`
        : '这一批已经跑完了，没什么可停的。')
    } catch (error) {
      setActMsg(`没能请求停止：${errorText(error)}`)
    }
  }, [withSession])

  /** 补全在跑的时候轮询；跑完**自动重读**这一层（状态列/建议会跟着变）。 */
  useEffect(() => {
    if (!ccsRunning) return undefined
    let stopped = false
    const timer = setInterval(() => {
      void (async () => {
        try {
          const st = await withSession((port, token) => fetchKbCcsBackfillStatus(port, token))
          if (stopped) return
          setCcsStatus(st)
          setCcsMissing(st.missing)
          if (st.running) {
            setActMsg(`补全分类号进行中：${String(st.done)} / ${String(st.total)} 篇跑完`
              + `（已补到 ${String(st.found)} 篇，没补到 `
              + `${String(st.not_found + st.network_failed + st.parse_failed + st.not_applicable)} 篇）…`)
            return
          }
          setCcsRunning(false)
          const bad = st.not_found + st.network_failed + st.parse_failed + st.not_applicable
          setActMsg(`补全分类号结束：${String(st.done)} 篇跑完，补到 ${String(st.found)} 篇`
            + (bad > 0
              ? `，${String(bad)} 篇没补到（逐篇原因见下面那张清单；不是失败就是查无）`
              : '')
            + (st.cancelled ? '。这一批是你按停的，剩下的还没跑。' : '。')
            + ' 下面这一层已按最新状态重读。')
          await loadInbox(inboxOffset, { silent: true })
          await loadCcsSummary()
        } catch (error) {
          if (!stopped) { setCcsRunning(false); setActMsg(`查补全进度失败：${errorText(error)}`) }
        }
      })()
    }, 3000)
    return () => { stopped = true; clearInterval(timer) }
  }, [ccsRunning, inboxOffset, loadCcsSummary, loadInbox, withSession])

  /* 进这一页就读一次"还缺几篇"（只读、零网络；失败就留"—"）。 */
  useEffect(() => {
    void (async () => { await loadCcsSummary() })()
  }, [loadCcsSummary])

  /** 搜索词（大小写不敏感）。目录按**名字**、文件按**标准号/名称**命中 —— 同一个词。 */
  const needle = search.trim().toLowerCase()
  const dirsShown = useMemo(
    () => (needle === '' ? subs : subs.filter((f) => f.name.toLowerCase().includes(needle))),
    [subs, needle],
  )
  const filesShown = useMemo(() => {
    if (needle === '') return files
    return files.filter((f) =>
      (f.standard_no ?? '').toLowerCase().includes(needle)
      || (f.standard_name ?? '').toLowerCase().includes(needle))
  }, [files, needle])

  /** 这一级**本来**就是空的（目录与文件都没有）—— 与"被搜索筛没了"是两回事。 */
  const levelEmpty = subs.length === 0 && files.length === 0 && filesTotal === 0
  const nothingShown = dirsShown.length === 0 && filesShown.length === 0

  const pageNo = Math.floor(fileOffset / FILE_PAGE_SIZE) + 1
  const pageMax = Math.max(1, Math.ceil(filesTotal / FILE_PAGE_SIZE))

  const current = files.find((f) => f.doc_id === openDoc) ?? null

  /**
   * **整行可点 ⇒ 打开详情**（业主 2026-09-21 亲口定：「勾选框只管勾选；点名字或行内任意处 →
   * 打开详情」）。
   *
   * ⚠ 本批**勾选框已经撤掉**（批量动作不在本批），分流规则因此只剩两条：
   *   ① `button`/`a`/菜单（含行尾「⋮」与它 portal 出去的 `[role=menuitem]`）⇒ 不处理；
   *   ② 其余任意处（图标 / 名字 / 标准号 / 日期 / 空白）⇒ 切换详情（再点同一行 = 收起）。
   * 键盘路径不变：「⋮ → 详情」（`aria-haspopup=menu` 的真 button，Tab 可达、Enter 激活）。
   */
  const openRowDetail = (doc: KsKbFile, e: ReactMouseEvent<HTMLDivElement>): void => {
    const target = e.target as (HTMLElement | null)
    if (target === null || typeof target.closest !== 'function') return
    if (target.closest('button,a,[role=menuitem],[role=menu]') !== null) return
    setOpenDoc((prev) => (prev === doc.doc_id ? null : doc.doc_id))
  }

  /**
   * 打开上传面板：默认把来源目录填成 host 的**待入库目录**
   * （`/ks/ingest/inbox-default`，同源；host 按需创建并回传绝对路径）。
   */
  const openUpload = useCallback(async (): Promise<void> => {
    const next = !upOpen
    setUpOpen(next)
    if (!next || upDir !== '') return
    try {
      const dir = await fetchIngestInboxDefault()
      setUpDir(dir)
    } catch (error) {
      setUpMsg(`取不到默认的「待入库」目录：${errorText(error)}（可以手填一个绝对路径）`)
    }
  }, [upDir, upOpen])

  /**
   * **导入到这一层**（需求 5 的落地）。四步全部是对引擎的真调用（见文件顶部"上传"那一段）：
   *   ① 记下导入前的文档 id 集合（`GET /api/v1/documents`）；
   *   ② `POST /api/v1/ingest/bulk` 建批次 + `POST .../resume` 开始解析，轮询 `GET .../bulk/{id}`；
   *   ③ 再取一次文档列表 ⇒ **差集**就是这一批新进来的；
   *   ④ 有当前目录 ⇒ `POST /kb/inbox/confirm`（`action='existing'`）把它们**挂进这一级并标成已归位**；
   *      在**最外层** ⇒ 不调它（没有可挂的目录），并如实说明文件留在最外层。
   * ⚠ 诚实边界：`/api/v1/documents` **一次返回全库可见文档**（无分页）⇒ 本函数要拉两次。
   *   真库 6417 篇时约 10 MB/次、本机回环（方案 §七记着"整库元数据 ~9.7MB"）。
   *   这是现有接口下**唯一**能算出"这一批新增了哪些"的办法；换更省的路需要后端加参数。
   * ⚠ **第 4 步补**：在**「待分类」这一层**导入时**不落位**（这里本来就是"还没归位"的地方）
   *   —— 导入完成后**就在这个列表里**刷新出来，当场可以处置（业主："不要两个页面"）。
   */
  const runUpload = useCallback(async (): Promise<void> => {
    const dir = upDir.trim()
    if (dir === '' || upPhase === 'running') return
    setUpPhase('running')
    setUpMsg('正在读取导入前的库快照…')
    try {
      const before = await withSession((port, token) => fetchDocsFlat(port, token))
      const beforeIds = new Set(before.map((d) => d.doc_id))
      const started = await withSession((port, token) =>
        startBulkIngest(port, token, dir, { reingest: upReingest }))
      /* ⚠⚠ **两段式握手（2026-09-21 第 5 步，副本库端到端实测出来的真缺陷）**：
         `POST /ingest/bulk` 只是**起一个后台快扫**（建占位行 + 排队），
         `POST .../resume` 的 docstring 明写「**快扫完成后调用**」——
         而旧代码**紧跟着就调 resume**。实测后果（真 PDF，副本库）：
           ① resume 路由进来先调一次幂等的 `pause_batch` ⇒ 正在跑的**快扫被暂停**；
           ② `resume_batch` 见"还有没扫完的"⇒ 又跑一遍快扫；这一遍把上一遍**自己建的占位行**
              当成 `duplicate_file`（`_known_files` 按"文件大小+哈希"认重）⇒ 新队列可能是空的；
           ③ 于是解析循环拿到**空队列**、直接落 `done`：批次报 `parsed=0`，界面（旧代码还会
              当场跳出轮询）对业主说"这一批没有新增文件" —— 而文件其实一份条款都没进去。
         ⚠⚠ **措辞更正（2026-09-21 第 5 步复核，留痕不许删）**：这里我原来写的是"**上传根本不会解析**"
            —— 复核在两个独立新库上实测，**一次复现**（`parsed=0/queue=0/clause_revision=0`）、
            **一次没复现**（`parsed=1/clause_revision=1`）⇒ 机制成立（**两次 `fast_scan` 抢写 checkpoint**），
            但它是**竞态（有时会）**，不是"必然不解析"。绝对措辞一律降级成"竞态"。
         ⇒ 现在按接口自己的契约走：**先等快扫完成（`pause_reason='scan_complete'`）再 resume**。
         ⚠ 后端那条"续扫会覆盖队列"的行为**不在本批改**（跨轮次发现只登记）——
            见 `docs/KB-FOLDER-PLAN.md` §二十.5 里那条挂账。 */
      setUpMsg(`批次 ${started.batch_id} 已建，正在快扫来源目录（建清单，还没开始解析）…`)
      let last = started.total
      let scanDone = false
      for (let i = 0; i < 300; i += 1) {
        const st = await withSession((port, token) => fetchBulkIngest(port, token, started.batch_id))
        last = st.total
        setUpMsg(`正在快扫：已看 ${st.scanned} / ${st.total} 个文件`
          + `${st.errors > 0 ? `（其中 ${st.errors} 个进了隔离/重复）` : ''}…`)
        if (st.status === 'done' || st.status === 'failed') { scanDone = true; break }
        if (st.pause_reason === 'scan_complete') { scanDone = true; break }
        await sleep(1000)
      }
      if (!scanDone) {
        setUpPhase('done')
        setUpMsg(`快扫这一步等了 5 分钟还没结束（已看 ${String(last)} 个文件）——`
          + '不接着往下点「开始解析」了（那样会打断快扫，实测会把已排好的清单丢掉）。'
          + '可以稍后再点一次「导入到这一层」。')
        return
      }
      await withSession((port, token) => resumeBulkIngest(port, token, started.batch_id))
      setUpMsg(`快扫完成，开始逐件解析`
        + `${upReingest ? '（覆盖重导：同号旧文档会被替换）' : ''}…`)
      let parsed = 0
      /* ⚠ ③a（2026-09-21 第 5 步）：`filing_state_missing` = 这批里**处理状态没写进库**的文件数。
         原来它只进 `checkpoint.errors`（排障杂项）⇒ 界面上完全看不出"这批里有文件的状态没库"。
         现在随批次终态一起报，这里就**如实说**：它们会在「待分类」里显示成"排队中"（那是谎），
         所以必须点名（后端给了前 5 个文件名样本）。 */
      let stateMissing = 0
      let stateMissingSample: readonly string[] = []
      /* ⚠⚠ **2026-09-21 第 5 步实测修掉的一个真缺陷**（副本库端到端跑出来的）：
         `POST .../resume` 进来先调一次幂等的 `pause_batch` ⇒ **刚 resume 完那一瞬批次是
         `paused`**（过渡态）。旧代码 `if (st.status !== 'running' && st.status !== 'pending') break`
         会**当场跳出**，紧接着去比对导入前后的文档列表 ⇒ 新文件还没解析 ⇒ 界面报
         "这一批没有新增文件" —— 那是对业主说的**假话**（文件其实马上就会进去，实测：
         跳出时 parsed=0/pending=1，几十秒后条款就进库了）。
         现在：**只有 `done`/`failed` 是终态**；`paused` 只在真的停下时才算
         （`daily_budget_reached` / `aborted_by_user`）；跑满上限要如实说"还在跑"，不许假装完成。 */
      let settled: 'done' | 'failed' | 'stopped' | 'timeout' = 'timeout'
      for (let i = 0; i < 300; i += 1) {
        const st = await withSession((port, token) => fetchBulkIngest(port, token, started.batch_id))
        last = st.total
        parsed = st.parsed
        stateMissing = st.filing_state_missing
        stateMissingSample = st.filing_state_missing_sample
        const pausedReal = st.status === 'paused'
          && (st.pause_reason === 'daily_budget_reached' || st.pause_reason === 'aborted_by_user')
        setUpMsg(`已解析 ${parsed} / ${last} 篇${st.errors > 0 ? `（失败 ${st.errors}）` : ''}`
          + `${st.status === 'paused' && !pausedReal ? '（引擎刚接过这一批，正在起解析）' : ''}`
          + `${stateMissing > 0 ? `；其中 ${String(stateMissing)} 篇的处理状态没写进库` : ''}…`)
        if (st.status === 'done' || st.status === 'failed') { settled = st.status as 'done' | 'failed'; break }
        if (pausedReal) { settled = 'stopped'; break }
        await sleep(2000)
      }
      if (settled === 'timeout') {
        setUpPhase('done')
        setUpMsg(`还在跑：已解析 ${parsed} / ${last} 篇（等了 10 分钟没等到结束）`
          + '——引擎那边还在干活，数字以它为准；可以点右上角刷新重读这一层，稍后再看。')
        return
      }
      if (settled === 'stopped') {
        setUpPhase('done')
        setUpMsg(`这一批停住了（已解析 ${parsed} / ${last} 篇）：`
          + '引擎说达到了当天的解析预算上限（或这批被终止）——剩下的文件不会自己继续，'
          + '可以到「待分类」层对着那几篇点「重来一次」。')
        await loadLevel(levelId, 0, { silent: true })
        return
      }
      const missingNote = stateMissing === 0 ? '' :
        `；⚠ 这批里有 ${String(stateMissing)} 篇的处理状态没写进库`
        + `（样例：${stateMissingSample.join('、')}${stateMissing > stateMissingSample.length ? ' 等' : ''}）`
        + '—— 它们在「待分类」里会显示成"排队中"，点「重来一次」可再试一次'
      const after = await withSession((port, token) => fetchDocsFlat(port, token))
      const fresh = after.filter((d) => !beforeIds.has(d.doc_id)).map((d) => d.doc_id)
      /* ⚠⚠ **2026-09-21 第 5 步副本库端到端实测出来的第二处真缺陷**：
         `GET /api/v1/documents`（`fetchDocsFlat` 用的那条）**看不到 `catalog_hidden=1` 的文档**
         —— 而"正文条款为零"的那一类正好被 pipeline 标成 hidden（目录卫生）。实测：批次
         `parsed=1`、`clause_revision` 真进库 1 条，而 `fresh` 是**空的** ⇒ 旧代码会对业主说
         "这一批没有新增文件"，**那是假话**（文件真的进来了，只是不在目录里）。
         ⇒ 现在按**批次自己的数字**说话：`parsed` 是引擎报的，`fresh` 只是"能挂进这一层的那些"；
         两者对不上时如实说明它们去哪了（「待分类」里看得到，可以点「重来一次」）。 */
      if (fresh.length === 0) {
        setUpPhase('done')
        if (parsed > 0) {
          setUpMsg(`这一批解析报成功 ${parsed} 篇，但它们没出现在目录清单里`
            + '（正文条款为零的那一类会被挡在目录外）——去「待分类」层就能看到它们，'
            + '在那儿可以对它们点「重来一次」。' + missingNote)
        } else {
          setUpMsg(`这一批没有解析出任何文档（共看了 ${last} 个，成功 0 个`
            + `${last > 0 ? `，失败 ${String(last - parsed)} 个` : ''}；库里已有的不会重复进）。`
            + missingNote)
        }
        return
      }
      const placeNote = parsed > fresh.length
        ? `；另有 ${String(parsed - fresh.length)} 篇解析报成功但不在目录清单里`
          + '（正文条款为零的那一类被挡在目录外，去「待分类」层看得到）'
        : ''
      if (layer === 'folder' && levelId !== null) {
        const res = await withSession((port, token) =>
          fileDocsIntoFolder(port, token, levelId, fresh))
        setUpMsg(`导入完成：这一批解析 ${parsed} 篇，其中能挂的 ${fresh.length} 篇已放进「${levelName}」`
          + `${res.confirmed} 篇（从「待分类」拿掉 ${res.removed_from_pending} 篇）`
          + `${placeNote}。` + missingNote)
        setUpPhase('done')
        await loadLevel(levelId, 0, { silent: true })
        return
      }
      if (layer === 'inbox') {
        setUpMsg(`导入完成：这一批解析 ${parsed} 篇，其中能挂的 ${fresh.length} 篇就排在下面这个列表里`
          + `（状态如实显示）——在这儿直接处置${placeNote}。` + missingNote)
      } else {
        setUpMsg(`导入完成：这一批解析 ${parsed} 篇，其中能挂的 ${fresh.length} 篇。`
          + '你现在停在最外层 ⇒ 它们留在最外层（还没归位，会出现在「待分类」里；'
          + `进一个目录再上传才会直接落进那个目录）${placeNote}。` + missingNote)
      }
      setUpPhase('done')
      await loadLevel(levelId, 0, { silent: true })
    } catch (error) {
      setUpPhase('error')
      setUpMsg(`导入失败：${errorText(error)}`)
    }
  }, [layer, levelId, levelName, loadLevel, upDir, upPhase, upReingest, withSession])

  /**
   * **先体检（只读）**：把原「入库预览」那一页的能力并进这里
   * （`POST /api/v1/ingest/preview/batch`，**不写库**；默认不外发，云深度解析要显式开）。
   * 结果只报三个真数字：能进 / 要留意 / 进不了。
   */
  const runCheck = useCallback(async (): Promise<void> => {
    const dir = upDir.trim()
    if (dir === '') { setUpCheck('先填一个来源目录'); return }
    setUpCheck('正在体检（只读，不写库）…')
    try {
      /* ⚠ 走 host 的只读代理（`fetchIngestBatch` → 同源 `/ks/ingest/preview/batch`），
         不是引擎的 `/kb/*`；`allowDeep:false` = **不外发**（云深度解析要人显式开）。 */
      const rep = await fetchIngestBatch({ dir, sample: 5, allowDeep: false })
      const b = rep.buckets
      setUpCheck(`体检完（只读，库里一篇都没多）：能进 ${String(b.ok)} 篇 / 要留意 ${String(b.warn)} 篇 /`
        + ` 进不了 ${String(b.block)} 篇（看了 ${String(rep.evaluated)} 篇，外发：${rep.egress}）。`)
    } catch (error) {
      setUpCheck(`体检失败：${errorText(error)}`)
    }
  }, [upDir])

  // ── 「能力」页有自己的组件（业主指定的"一功能一卡一窗"） ──
  /* ── 修 React #300（2026-09-23）：以下两个 useMemo 原在早退分支**之后**，切页早退时
     挂钩数比上次少 ⇒ slot 崩 ⇒ 黑屏。上移到所有早退之前=挂钩顺序恒定。 ── */






  /** 「待分类」层的搜索（同一个词、同一个框：按标准号/名称/建议路径过滤）。 */
  const inboxShown = useMemo(() => {
    if (needle === '') return inbox
    return inbox.filter((r) =>
      (r.standard_no ?? '').toLowerCase().includes(needle)
      || (r.standard_name ?? '').toLowerCase().includes(needle)
      || (r.suggested_path ?? '').toLowerCase().includes(needle))
  }, [inbox, needle])

  /**
   * 选择器的**可选去处**：把"挪/复制自己或自己的下级"排除掉。
   * ⚠ 后端会拒（`folder_cycle`/`folder_attach_cycle`），但那是个**必然失败**的选项 ⇒
   *   不让它出现在列表里（不是替调用方兜底，是去掉一个点下去只会报错的死选项）。
   */
  const pickBase = useMemo(() => {
    const banned = new Set<string>()
    for (const fid of folderIdsOf(action?.targets ?? [])) {
      const self = flatFolders.find((f) => f.folder_id === fid)
      if (self === undefined) continue
      for (const other of flatFolders) {
        if (other.folder_id === fid || other.path.startsWith(`${self.path} › `)) banned.add(other.folder_id)
      }
    }
    return flatFolders.filter((f) => !banned.has(f.folder_id))
  }, [action, flatFolders])

  if (page === 'capabilities') {
    return (
      <div className="ks-page">
        <KsTopTabs page={page} onGo={(pp) => { setPageOverride(pp) }} onPdf={() => { tab.actions.openTab(KS_EVIDENCE_KIND) }} />
        <KsCapabilityPage />
      </div>
    )
  }

  if (page === 'materials') {
    /* S5：备料（原设置「参考资料」）迁此 —— 业主动词表里的一级动作「备料」。 */
    return (
      <div className="ks-page">
        <div className="ks-kb">
          <KsTopTabs page={page} onGo={(pp) => { setPageOverride(pp) }} onPdf={() => { tab.actions.openTab(KS_EVIDENCE_KIND) }} />
          <header className="ks-page-head">
            <div className="ks-page-title">备料</div>
            <div className="ks-page-sub">上传的财报/制度/文章逐份就位；人工上传免评审，自采的要人批。</div>
          </header>
          <div className="ks-page-rule" />
          <KsMaterialsPanel visible />
        </div>
      </div>
    )
  }

  // ── S5-c（2026-09-22 业主重定）：渠道台账 = 渠道管理 + 顶部常驻「最新动态」栏；
  //    巡检/公告并入它的折叠详情（"每日巡检就是立即探测，留一个按钮"）；旧三节布局撤。 ──
  if (page === 'channels') {
    return (
      <div className="ks-page">
        <div className="ks-kb">
          <KsTopTabs page={page} onGo={(pp) => { setPageOverride(pp) }} onPdf={() => { tab.actions.openTab(KS_EVIDENCE_KIND) }} />
          <header className="ks-page-head">
            <div className="ks-page-title">渠道库</div>
            <div className="ks-page-sub">知识来源渠道的管理库：分类、体检、维护。顶部常驻最新动态。</div>
          </header>
          <div className="ks-page-rule" />
          <KsChannelsPanel visible />
        </div>
      </div>
    )
  }

  // ── 其余非「知识库管理」页：诚实的占位（真入口，空内容） ──
  // ⚠ **`ingest` 不在这里了**（第 4 步）：那一条以前落到"这一页尚未实现"，而业主说
  //   "不要两个页面" ⇒ 现在它**直接落到「待分类」那一层**（看上面 `layer` 的初值与挂载副作用）。
  if (page !== 'manage' && page !== 'ingest') {
    const LABELS: Record<string, string> = { channels: '渠道库' }
    return (
      // ⚠ 外面这一层 `.ks-page` **只做 container-type**（页面留边的宽/窄两档靠它切；
      //    CSS 里容器不能用自己的宽度查自己，所以留边必须落在它的后代 `.ks-kb` 上）。
      <div className="ks-page">
        <div className="ks-kb">
          <div className="ks-kb-banner" title="本页只落了入口与外壳，内容还没有。">
            <IconInfoOutline14 />
            <strong>这一页尚未实现</strong>
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
   * 本页只有**一处**渲染点：右栏当前这一层的条目区上方（**每层都在同一位置**，
   * 包括「待分类」那一层 —— "每层常驻"是台账第 13 条的口径）。
   * 它同时过滤目录名与文件名（见 `needle` 的注释），在待分类层过滤标准号/名称。
   */
  const searchBox = KB_PAGE_SEARCH ? (
    <span className="ks-search">
      <Input
        icon={<IconSearchOutline16 />}
        value={search}
        placeholder="搜索目录名或标准号/名称…"
        aria-label="在当前这一层按目录名或文件标准号/名称过滤（本地过滤，不检索语料）"
        onChange={(event) => {
          setSearch(event.target.value)
          setOpenDoc(null)
        }}
      />
    </span>
  ) : null

  /**
   * 左列树的一行（递归渲染；**点名字 = 进这一级，点箭头 = 展开/收起**）。
   *
   * `before`（第 4 步加）是**插在这一行之后、它的下级之前**的额外节点 —— 「待分类」那一行
   * 就靠它出现在最外层下面、四个顶层目录之前（它不在 `folder` 表里，是页面上的一层）。
   */
  const renderTreeRow = (
    key: string, name: string, count: number | null, depth: number, isCurrent: boolean,
    before?: ReactNode,
  ): ReactNode => {
    const node = tree[key]
    const expanded = treeOpen.has(key)
    const hasKids = (node?.kids?.length ?? 0) > 0 || node?.kids === undefined
    return (
      <div className="ks-tree-node" key={key}>
        <div
          className="ks-tree-row"
          data-on={isCurrent ? 'true' : 'false'}
          data-depth={depth}
          aria-current={isCurrent ? 'true' : undefined}
        >
          {hasKids ? (
            <button
              type="button"
              className="ks-tree-caret"
              aria-label={`${expanded ? '收起' : '展开'}「${name}」的下级目录`}
              aria-expanded={expanded}
              title={expanded ? '收起' : '展开'}
              onClick={() => { void toggleTree(key) }}
            >
              {expanded ? <IconChevronDownOutline14 /> : <IconChevronRightOutline14 />}
            </button>
          ) : (
            <span className="ks-tree-caret ks-tree-caret-leaf" aria-hidden="true" />
          )}
          <button
            type="button"
            className="ks-tree-name"
            title={`${name}${count === null ? '' : `（这一棵下共 ${String(count)} 篇）`}`}
            onClick={() => { goto(key === 'root' ? null : key) }}
          >
            <IconFolderOpenOutline16 />
            <span className="ks-tree-label">{name}</span>
          </button>
          {count === null ? null : <span className="ks-tree-count">{count}</span>}
        </div>
        {before}
        {node?.loading === true ? <div className="ks-tree-hint">正在读取这一层…</div> : null}
        {node?.error !== undefined
          ? <div className="ks-tree-hint ks-tree-err">读不到下一层：{node.error}</div>
          : null}
        {expanded && node?.kids !== undefined
          ? node.kids.map((kid) => renderTreeRow(
            kid.folder_id, kid.name, kid.file_count_deep, depth + 1, kid.folder_id === levelId))
          : null}
      </div>
    )
  }

  /**
   * 「待分类」这一层的**左列那一行**（它不在 `folder` 表里，是页面上的一层）。
   * 篇数只在**真读过**那一层之后才显示（没读过就留白，不许写 `0 篇`）。
   */
  const inboxTreeRow = (
    <div className="ks-tree-node ks-tree-inbox" key="__inbox">
      <div
        className="ks-tree-row"
        data-on={layer === 'inbox' ? 'true' : 'false'}
        data-depth={1}
        aria-current={layer === 'inbox' ? 'true' : undefined}
      >
        <span className="ks-tree-caret ks-tree-caret-leaf" aria-hidden="true" />
        <button
          type="button"
          className="ks-tree-name ks-tree-name-inbox"
          title={inboxKnown
            ? `待分类：还没归位的文件 ${String(inboxTotal)} 篇（含识别失败的那一批）`
            : '待分类：还没归位的文件'}
          onClick={gotoInbox}
        >
          <IconChecklistOutline14 />
          <span className="ks-tree-label">待分类</span>
        </button>
        {inboxKnown ? <span className="ks-tree-count ks-tree-count-inbox">{inboxTotal}</span> : null}
      </div>
    </div>
  )


  const pickedRows = inbox.filter((r) => picked.has(pickFileKey(r.doc_id)))
  /** 选中的里面**真有建议**的篇数（「接受建议」只对它们发；0 篇时那个按钮禁用 + 说清原因）。 */
  const pickedWithSuggestion = pickedRows.filter((r) => r.suggested_folder_id !== null).length
  /* ── 第 5 步：勾选集合里的两层东西（批量条按它决定给哪些动作） ── */
  /** 选中的**文件**篇数（key `f:`）。 */
  const pickedDocIds = docIdsOf(picked)
  /** 选中的**目录**个数（key `d:`）。 */
  const pickedFolderIds = folderIdsOf(picked)
  /** 批量条上那句"已选 N…"：只有文件（含「待分类」层）就说**篇**，混着就两层都报清楚。 */
  const batchLabel = pickedFolderIds.length === 0
    ? `已选 ${String(pickedDocIds.length)} 篇`
    : (pickedDocIds.length === 0
      ? `已选 ${String(pickedFolderIds.length)} 个目录`
      : `已选 ${String(pickedDocIds.length + pickedFolderIds.length)} 项`
        + `（${String(pickedDocIds.length)} 篇文件 / ${String(pickedFolderIds.length)} 个目录）`)
  const pickPathOf = pathOfFolder(flatFolders, pickFolder)
  /** 选择器里显示的那一截（1127 个目录不一次铺满 DOM：超过 60 行就截断并**如实说**）。 */
  const PICK_ROWS_MAX = 60
  const pickNeedle = pickQuery.trim().toLowerCase()
  const pickMatched = pickNeedle === ''
    ? pickBase
    : pickBase.filter((f) => f.path.toLowerCase().includes(pickNeedle))
  const flatShown = pickMatched.slice(0, PICK_ROWS_MAX)
  const flatHidden = pickMatched.length - flatShown.length

  /**
   * 「没有建议」那一格**怎么写**（业主 2026-09-22：「没有建议要写明**为什么**」）。
   *
   * ⚠ 三条分支的依据**全部来自后端**（`doc_ccs_state` 台账；`ccs_store` / `ccs_fetcher`
   * 是中文说法的唯一所有者），界面**不自己推断**：
   *
   * 1. **已经有分类号**却仍没有建议 ⇒ 这不是分类号的问题（分类树里没有对应那一层，
   *    或落进了兜底桶）—— 明说"已经有分类号"，免得业主去补一个已经有的东西。
   * 2. **还没查过**（`ccs_outcome` 为 null）⇒ 说"还没查过"，并指向「补全分类号」。
   * 3. **查过了没查到** ⇒ 照念后端那句 `ccs_outcome_label`（查无 / 查询失败 / 读不出来），
   *    `title` 里放 `ccs_reason`（一句人话，含"两个站点一个都没答上"这类细节）。
   *
   * ⚠ 文案里**必须**留着「没有建议」四个字：`smoke-kb-page-render.mjs` 的 N5 断言
   *   「没有建议的那两篇显示「没有建议」」数的是这个串。
   */
  const noSuggestText = (doc: KsKbInboxItem): { short: string; why: string } => {
    if (doc.ccs_tag !== null && doc.ccs_tag !== '') {
      return {
        short: '没有建议（有分类号，但树里没有对应的那一层）',
        why: `这一篇已经有分类号（${doc.ccs_tag}），问题在于现有目录里没有对应的那一层`
          + ' —— 只能手动指定去处。',
      }
    }
    if (doc.ccs_outcome === null || doc.ccs_outcome === '') {
      return {
        short: '没有建议（还没查过分类号）',
        why: '这一篇还没有查过分类号（CCS）。点上面的「补全分类号」查一次，'
          + '查到了就会按分类号给出去向。',
      }
    }
    const label = doc.ccs_outcome_label ?? doc.ccs_outcome
    return {
      short: `没有建议：这一篇没有分类号（${label}）`,
      why: doc.ccs_reason !== null && doc.ccs_reason !== ''
        ? doc.ccs_reason
        : label,
    }
  }

  /** 一篇「待分类」行（勾选 / 文件名 / 状态 / 建议去向 / ⋮）。 */
  const renderInboxRow = (doc: KsKbInboxItem): ReactNode => {
    const isOpen = menuFor === doc.doc_id
    const sugLabel = doc.suggested_path ?? ''
    /* ⚠ **没有建议就不渲染那两条**：后端对它们会回 422 `no_suggestion`（死按钮）。
       真库 379 篇兜底桶全是这样。 */
    const menuItems: { id: string; label: string }[] = [
      { id: 'place', label: '放进某个目录…' },
      ...(doc.suggested_folder_id !== null
        ? [{ id: 'accept', label: `按建议归位（${sugLabel}）` }] : []),
      ...(doc.suggest_new_parent_id !== null && doc.suggest_new_name !== null
        ? [{ id: 'new', label: `在建议位置新建「${doc.suggest_new_name}」` }] : []),
      /* 第 6 步：这一篇**还没进任何目录** ⇒ 只能用**显式文件范围**（`kb_doc_ids`）问。
         ⚠ **2026-09-22 业主改的文案**：在**单个文件**上点开三个点 ⇒ 写「在此文件中提问」
         （原话："在此范围内提问——如果是在**单个文件**上点开三个点，那就应该展示**在此文件中提问**"）。
         行为**一字未变**（还是只问这一篇）。 */
      { id: 'ask', label: '在此文件中提问' },
      { id: 'retry', label: '重来一次（重新解析）' },
      /* ⚠ **2026-09-22 业主**："「从这一层拿掉」是啥意思，删除就说删除" ——
         这一条是**真删文档**（不可逆，后面有二次确认面板）⇒ 文案就是「删除」。
         原文（留痕）：`{ id: 'delete', label: '删掉…' }` */
      { id: 'delete', label: '删除' },
    ]
    const cell = (key: InboxColKey): ReactNode => {
      switch (key) {
        case 'pick':
          return (
            <span className="ks-pick">
              <Checkbox
                className="ks-pick-cb"
                checked={picked.has(pickFileKey(doc.doc_id))}
                onChange={(next) => { togglePick(pickFileKey(doc.doc_id), next) }}
                /* ⚠ `label` 是**可访问名**（宿主 Checkbox 把它渲染成 `<span>`）：
                   这里传文件名，样式上把它做成 sr-only（视觉上不重复显示第二遍名字）。 */
                label={doc.standard_name ?? doc.doc_id}
                title={`选中「${doc.standard_name ?? doc.doc_id}」（选中后下面会出现批量处置条）`}
              />
            </span>
          )
        case 'iname':
          return (
            <>
              {/* ⚠⚠ **业主 2026-09-22**："文件前面那个莫名其妙的图标可以删除" ⇒
                  文件行**不再有**行内图标（目录行的文件夹图标保留，业主说那个做得好）。
                  判据 `E6` 已**翻过来**（文件行不许有 `.ks-fileico`、目录行必须有）。 */}
              <span className="ks-item-name" title={doc.standard_name ?? doc.doc_id}>
                {doc.standard_name ?? doc.doc_id}
              </span>
              <span className="ks-item-sub">
                <span className="ks-item-meta">
                  {doc.standard_no === null || doc.standard_no === '' ? '—' : doc.standard_no}
                </span>
              </span>
            </>
          )
        case 'istage':
          /* 状态**如实**：档位 + 失败原因 + 识别率；正文为零的那篇还要说清"不在目录里"
             （业主："好发现哪些文件要人工修"）。 */
          return (
            <span className="ks-stage" data-stage={doc.stage}>
              <span className={`ks-stage-tag ks-stage-${doc.stage}`}>
                {doc.stage_label !== '' ? doc.stage_label : stageText(doc.stage, stageLabels)}
              </span>
              {doc.failure_kind === null || doc.failure_kind === '' ? null : (
                <span className="ks-stage-why" title={doc.failure_kind}>（{doc.failure_kind}）</span>
              )}
              {confidenceText(doc.confidence) === '' ? null : (
                <span className="ks-stage-conf" title="识别率（与入库预览同一个数）">
                  识别率 {confidenceText(doc.confidence)}
                </span>
              )}
              {doc.catalog_hidden === 1 ? (
                <span className="ks-stage-hidden"
                  title="正文条款为零 ⇒ 这篇不在目录里，只能在「待分类」里看到">
                  不在目录里
                </span>
              ) : null}
            </span>
          )
        case 'idest':
          /* ⚠ **业主 2026-09-22 口径**：「待分类里**没有建议**要写明**为什么**」
             （原文：「这一篇没有分类号：查询失败 / 官方查无」）。
             依据**全在后端**（`doc_ccs_state` 台账，`ccs_store` 是唯一所有者），
             界面只照念 —— 见 `noSuggestText` 的三条分支，**不自己推断**。 */
          return sugLabel === '' ? (
            <span className="ks-kb-hint" title={noSuggestText(doc).why}>
              {noSuggestText(doc).short}
            </span>
          ) : (
            <span className="ks-dest" title={`系统建议放进：${sugLabel}`}>
              <span className="ks-dest-path">{sugLabel}</span>
              {doc.suggest_new_name === null ? null : (
                <span className="ks-dest-new">＋新建「{doc.suggest_new_name}」</span>
              )}
            </span>
          )
        case 'imore':
          return (
            <span className="ks-item-more">
              <Menu
                open={isOpen}
                portal
                autoFocus
                align="end"
                items={menuItems}
                onClose={() => { setMenuFor(null) }}
                onSelect={(id) => {
                  setMenuFor(null)
                  const key = pickFileKey(doc.doc_id)
                  if (id === 'place') openAction('place', [key])
                  else if (id === 'accept') void acceptSuggestions([doc.doc_id])
                  else if (id === 'new') openAction('new', [key])
                  else if (id === 'ask') void openAsk([key])
                  else if (id === 'retry') void runReingest([doc.doc_id])
                  else if (id === 'delete') openAction('del', [key])
                }}
                anchor={(
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-haspopup="menu"
                    aria-expanded={isOpen}
                    aria-label={`${doc.standard_name ?? doc.doc_id} 的处置操作`}
                    title="处置这一篇（放进目录 / 按建议归位 / 重来一次 / 删除）"
                    onClick={() => { setMenuFor(isOpen ? null : doc.doc_id) }}
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
      <div className="ks-item ks-inbox-row" key={doc.doc_id} data-doc-id={doc.doc_id}>
        {INBOX_COLUMNS.map((col) => (
          <div className={`ks-cell ${col.cls}`} key={col.key}>{cell(col.key)}</div>
        ))}
      </div>
    )
  }

  /**
   * 批量条（**真的**：每条都对应真接口）。
   *
   * ⚠ 第 5 步：**一套**批量条、按**层**给动作（`layer === 'inbox'` 一套；目录/文件层另一套）——
   *   不许为目录层复制出第二个批量条组件（任务书 §1 明写"别复制出第二套"）。
   *   目录层与文件层的动作本身也不同（目录走 `folders/{id}/*`、文件走 `members/*`），
   *   所以按钮的**出现条件**按"选中的里面有没有这一层的东西"判（`pickedDocIds`/`pickedFolderIds`）。
   *
   * ⚠ **删除**：目录层**不许**顺手删文档（不可逆；任务书 §2 第 6 条）⇒ 这里的「删掉目录…」
   *   删的是**目录**（先拉 `delete-preview` 把影响列出来）；真删**文档**的入口只有「待分类」层
   *   那一个（`action.kind === 'del'`，走 `/documents/batch-delete` + 二次确认）。
   */
  const batchBar = picked.size === 0 ? null : (
    <div className="ks-batch" role="toolbar" aria-label="批量处置选中的条目">
      <span className="ks-batch-n">{batchLabel}</span>
      {layer === 'inbox' ? (
        <>
          <Button
            variant="outline"
            size="sm"
            className="ks-batch-btn"
            disabled={pickedWithSuggestion === 0}
            title={pickedWithSuggestion === 0
              ? '选中的这些系统都没给出建议（认不出该放哪）——请用「放进同一目录」自己指定'
              : `只对其中 ${String(pickedWithSuggestion)} 篇有建议的归位；没建议的不会被动`}
            onClick={() => { void acceptSuggestions(pickedDocIds) }}
          >
            接受建议{pickedWithSuggestion === 0 ? '' : `（${String(pickedWithSuggestion)}）`}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="ks-batch-btn"
            onClick={() => { openAction('place', [...picked]) }}
          >
            放进同一目录
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="ks-batch-btn"
            title="让引擎把这批重新解析一遍（后台跑，状态列会跟着变）"
            onClick={() => { void runReingest(pickedDocIds) }}
          >
            <IconRefreshOutline16 />
            重来一次
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="ks-batch-btn ks-danger"
            title="删除是不可撤销的（条款/向量/证据一并删；收藏与批注不删）"
            onClick={() => { openAction('del', [...picked]) }}
          >
            <IconTrashOutline16 />
            删除
          </Button>
        </>
      ) : (
        <>
          {/* 最外层那些文件"还没进任何目录" ⇒ 这里给的是「加进目录」（不是挪：它们没有来源目录）。 */}
          {levelId === null && pickedDocIds.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-batch-btn"
              title="把选中的文件放进某个目录（放进去之后它们就不在最外层了；文件只有一份）"
              onClick={() => { openAction('add', [...picked]) }}
            >
              放进目录…
            </Button>
          ) : null}
          {pickedFolderIds.length + (levelId === null ? 0 : pickedDocIds.length) > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-batch-btn"
              title="移动到某个目录（只改挂在哪：目录走 folders/{id}/move、文件走 members/move；磁盘文件不动）"
              onClick={() => { openAction('move', [...picked]) }}
            >
              移动到…
            </Button>
          ) : null}
          {pickedFolderIds.length + pickedDocIds.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-batch-btn"
              title="复制到某个目录（多一处位置：文件还是那一份；复制出来的目录与原目录共享同一批内容）"
              onClick={() => { openAction('copy', [...picked]) }}
            >
              复制到…
            </Button>
          ) : null}
          {levelId !== null && pickedDocIds.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-batch-btn"
              title="移出：只去掉这些文件在「当前这一层」的归属 —— 文件不会删除（还在库里），别处还挂着的照旧"
              onClick={() => { void runRemove([...picked]) }}
            >
              移出
            </Button>
          ) : null}
          {pickedFolderIds.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-batch-btn ks-danger"
              title="删目录（不是删文档）：先读这几个目录的真实影响，再让你二选一"
              onClick={() => { openAction('folder-del', [...picked]) }}
            >
              <IconTrashOutline16 />
              删掉目录…
            </Button>
          ) : null}
        </>
      )}
      <Button variant="ghost" size="sm" className="ks-batch-btn" onClick={() => { setPicked(new Set()) }}>
        取消选择
      </Button>
    </div>
  )

  /**
   * 动作面板：目录选择器（放进某处 / 在建议位置新建）、以及**删除的二次确认**。
   * ⚠ 删除的确认**不是** `window.confirm`（那在 jsdom/无头里点不到、也没法断言）——
   *   是页面上的一个真面板，`确认删除` 是第二个按钮。
   */
  /**
   * 动作面板（**一套**，按 `action.kind` 换主体）。
   *
   * 三种形态：
   *   ① 文档删除的**二次确认**（`del`）—— 不是 `window.confirm`（那在 jsdom/无头里点不到、
   *      也没法断言）；`确认删除` 是第二个按钮。
   *   ② **目标目录选择器**（`place`/`new`/`move`/`copy`/`add` 共用同一份扁平清单 + 搜索框）。
   *   ③ 建目录（`mkdir`）/ 目录改名（`rename`）：一个名字输入框。
   *   ④ 删目录（`folder-del`）：**先**把 `delete-preview` 的真数字列出来，再二选一。
   */
  const actWhat = pickedFolderIds.length > 0 && pickedDocIds.length > 0
    ? `${String(pickedFolderIds.length)} 个目录 + ${String(pickedDocIds.length)} 篇文件`
    : (pickedFolderIds.length > 0
      ? `${String(pickedFolderIds.length)} 个目录`
      : `${String(pickedDocIds.length)} 篇文件`)
  /** 选择器那一段的动词（面板标题与"将…到"都用它，一处定义别处不重写）。
   *  ⚠ **2026-09-22 业主改的文案**：`move` 由「挪到」改成「**移动到**」
   *  （原话："挪到某个目录直接写**移动到**"）。`copy` 本来就是「复制到」✓。 */
  const pickVerb: Record<string, string> = {
    place: '放进', new: '放进', move: '移动到', copy: '复制到', add: '放进',
  }
  /** 选择器里为空时的原因（分得清"还没读到"与"被排除了"，不是一句"没有匹配"）。 */
  const pickEmptyHint = flatFolders.length === 0
    ? '正在读目录清单…'
    : (pickBase.length === 0
      ? '没有可选的目的地：唯一的那几个目录就是你正在移动/复制的目录自己（不能移进自己的下级）'
      : '没有匹配的目录')
  const actionPanel = action === null ? null : (
    <div
      className={action.kind === 'del' || action.kind === 'folder-del'
        ? 'ks-act ks-act-del' : 'ks-act'}
      role="group"
      aria-label={action.kind === 'del' || action.kind === 'folder-del'
        ? '删除确认' : '选择目标目录'}
    >
      {action.kind === 'del' ? (
        <>
          <span className="ks-act-head">
            <IconWarningOutline16 />
            <strong>确认删除 {action.targets.length} 篇？</strong>
          </span>
          <span className="ks-act-hint">
            删除不可撤销：条款、向量、证据一起删（收藏与批注是用户资产，不删）。
          </span>
          <div className="ks-act-row">
            <Button variant="outline" size="sm" onClick={() => { setAction(null) }}>取消</Button>
            {/* ⚠ 不可逆动作的按钮**不用 primary 底色**（2026-09-21 真机实测）：light 主题下
                primary 的底色/字色压过 `.ks-danger` 的红字 ⇒ 一个「确认删除」看起来跟普通主按钮
                一模一样。改成 `outline` + `ks-danger`（与批量条里的「删除」同一种呈现：
                红字红描边），一眼看得出是危险动作。 */}
            <Button
              variant="outline"
              size="sm"
              className="ks-act-go ks-danger"
              onClick={() => { void removeDocs(docIdsOf(action.targets)) }}
            >
              <IconTrashOutline16 />
              确认删除
            </Button>
          </div>
        </>
      ) : action.kind === 'folder-del' ? (
        <>
          <span className="ks-act-head">
            <IconWarningOutline16 />
            <strong>删掉这 {folderIdsOf(action.targets).length} 个目录？</strong>
            <Button variant="ghost" size="sm" title="关掉这个面板" onClick={() => { setAction(null) }}>
              <IconCloseOutline16 />
            </Button>
          </span>
          {delPreview === null ? (
            <span className="ks-act-hint">正在读这几个目录的真实影响（只读，还没动任何东西）…</span>
          ) : (
            <>
              {/* 影响数字**全部来自 `delete-preview`**（任务书 §3 第 2 条：不许前端猜）。 */}
              <div className="ks-act-list ks-act-list-del">
                {delPreview.map((p) => (
                  <div className="ks-act-delrow" key={p.folder?.folder_id ?? 'unknown'}>
                    <span className="ks-act-item-name">{p.folder?.name ?? p.folder?.folder_id ?? '(读不到)'}</span>
                    <span className="ks-act-item-path">
                      {p.is_empty
                        ? '空目录（里面没有下级目录，也没有文件）'
                        : `${String(p.direct_subfolder_count)} 个下级目录 · ${String(p.direct_file_count)} 篇直接放在这里`}
                    </span>
                    {p.is_empty ? null : (
                      <span className="ks-act-item-path">
                        整棵子树：{String(p.subtree_folder_count)} 个目录 / {String(p.subtree_file_count)} 篇文件；
                        连文件一起删时，其中 {String(p.files_would_be_deleted)} 篇会**真的删掉**，
                        {String(p.files_kept_elsewhere)} 篇还挂在别处（只丢这里的归属）；
                        {p.reparent_available
                          ? '移到上一层：里面的东西原样上去。'
                          : '⚠ 这是一级目录，没有上一层（只能连文件一起删，或取消）。'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              {delPreview.length < folderIdsOf(action.targets).length ? (
                <span className="ks-act-hint">
                  有 {folderIdsOf(action.targets).length - delPreview.length} 个目录的影响没读到
                  （上面那条消息里写了原话）—— 它们不会被删。
                </span>
              ) : null}
              <span className="ks-act-hint">
                删目录**不是**删文档：只有"在所有目录里都不再出现"的文件才会被真删。
              </span>
              <div className="ks-act-row">
                <Button variant="outline" size="sm" onClick={() => { setAction(null) }}>取消</Button>
                {delPreview.length > 0 && delPreview.every((p) => p.is_empty) ? (
                  /* 空目录也是不可逆动作 ⇒ 同样 outline + ks-danger（理由见上面「确认删除」那条注释）。 */
                  <Button
                    variant="outline"
                    size="sm"
                    className="ks-act-go ks-danger"
                    onClick={() => { void runFolderDelete(null) }}
                  >
                    <IconTrashOutline16 />
                    删除这些空目录
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      className="ks-act-go"
                      disabled={delPreview.every((p) => !p.reparent_available)}
                      title={delPreview.every((p) => !p.reparent_available)
                        ? '选中的目录里有一级目录 —— 它没有上一层，移不上去（只能"连里面的文件一起删"或取消）'
                        : '只删这些目录，里面的下级目录与文件移到上一层（文件本身一份都不删）'}
                      onClick={() => { void runFolderDelete('reparent') }}
                    >
                      只删目录，里面的东西移到上一层
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="ks-act-go ks-danger"
                      title="连里面的下级目录一起删；文件只从这些目录里拿掉，不会再出现在任何目录里的才真删"
                      onClick={() => { void runFolderDelete('purge') }}
                    >
                      <IconTrashOutline16 />
                      连里面的文件一起删
                    </Button>
                  </>
                )}
              </div>
            </>
          )}
        </>
      ) : action.kind === 'mkdir' || action.kind === 'rename' ? (
        <>
          <span className="ks-act-head">
            <strong>
              {action.kind === 'mkdir'
                ? `在「${levelName}」下面新建一个目录`
                : `把目录「${subs.find((f) => f.folder_id === folderIdsOf(action.targets)[0])?.name ?? ''}」改成什么名字？`}
            </strong>
            <Button variant="ghost" size="sm" title="关掉这个面板" onClick={() => { setAction(null) }}>
              <IconCloseOutline16 />
            </Button>
          </span>
          <div className="ks-act-row">
            <span className="ks-act-label">{action.kind === 'mkdir' ? '新目录名' : '新名字'}</span>
            <Input
              className="ks-act-name"
              value={newName}
              placeholder={action.kind === 'mkdir' ? '新目录的名字' : '新的目录名'}
              aria-label={action.kind === 'mkdir' ? '新建目录的名字' : '目录的新名字'}
              onChange={(event) => { setNewName(event.target.value) }}
            />
          </div>
          <span className="ks-act-hint">
            {action.kind === 'mkdir'
              ? '建在当前这一级下面；同级同名会被拒（后端 409，原话会显示在这里）。'
              : '改名只改库里的名字，磁盘上的文件一个字都不会动。'}
          </span>
          <div className="ks-act-row">
            <Button variant="outline" size="sm" onClick={() => { setAction(null) }}>取消</Button>
            <Button
              variant="primary"
              size="sm"
              className="ks-act-go"
              disabled={newName.trim() === ''}
              onClick={() => {
                void (action.kind === 'mkdir'
                  ? runMkdir(newName)
                  : runRename(folderIdsOf(action.targets)[0] ?? '', newName))
              }}
            >
              {action.kind === 'mkdir' ? '建这个目录' : '改名字'}
            </Button>
          </div>
        </>
      ) : (
        <>
          <span className="ks-act-head">
            <strong>
              {action.kind === 'new'
                ? `在选中的目录下新建「${newName.trim() === '' ? '…' : newName.trim()}」再放 ${String(pickedDocIds.length)} 篇`
                : `把 ${actWhat}${pickVerb[action.kind] ?? '放进'}哪个目录？`}
            </strong>
            <Button variant="ghost" size="sm" title="关掉这个面板" onClick={() => { setAction(null) }}>
              <IconCloseOutline16 />
            </Button>
          </span>
          {action.kind === 'new' ? (
            <div className="ks-act-row">
              <span className="ks-act-label">新目录名</span>
              <Input
                className="ks-act-name"
                value={newName}
                placeholder="新目录的名字"
                aria-label="新建目录的名字"
                onChange={(event) => { setNewName(event.target.value) }}
              />
            </div>
          ) : null}
          <div className="ks-act-row">
            <span className="ks-act-label">找目录</span>
            <Input
              className="ks-act-search"
              value={pickQuery}
              placeholder="按名字或路径找，例如 工程防火"
              aria-label="按名字或路径过滤目录清单"
              onChange={(event) => { setPickQuery(event.target.value) }}
            />
          </div>
          <div className="ks-act-list">
            {flatShown.map((f) => (
              <button
                type="button"
                key={f.folder_id}
                className="ks-act-item"
                data-on={pickFolder === f.folder_id ? 'true' : 'false'}
                data-depth={f.depth}
                title={f.path}
                onClick={() => { setPickFolder(f.folder_id) }}
              >
                <IconFolderOpenOutline16 />
                <span className="ks-act-item-name">{f.name}</span>
                <span className="ks-act-item-path">{f.path}</span>
              </button>
            ))}
            {flatShown.length === 0 ? (
              <span className="ks-act-hint">{pickEmptyHint}</span>
            ) : null}
            {flatHidden > 0 ? (
              <span className="ks-act-hint">
                还有 {flatHidden} 个没列出来（一共 {flatFolders.length} 个目录）—— 用上面的搜索缩小范围。
              </span>
            ) : null}
          </div>
          <div className="ks-act-row">
            <span className="ks-act-hint">
              即将{pickVerb[action.kind] ?? '放进'}：
              {pickPathOf === '' ? '（还没选）' : pickPathOf}
            </span>
            <Button
              variant="primary"
              size="sm"
              className="ks-act-go"
              disabled={pickFolder === '' || (action.kind === 'new' && newName.trim() === '')}
              onClick={() => {
                if (action.kind === 'move') void runMove(action.targets, pickFolder)
                else if (action.kind === 'copy') void runCopy(action.targets, pickFolder)
                else if (action.kind === 'add') void runAdd(action.targets, pickFolder)
                else if (action.kind === 'new') void placeIntoNew(docIdsOf(action.targets), pickFolder, newName)
                else void placeInto(docIdsOf(action.targets), pickFolder)
              }}
            >
              {action.kind === 'new'
                ? '新建并放进去'
                : `${pickVerb[action.kind] ?? '放进'}「${pickPathOf.split(' › ').slice(-1)[0]}」`}
            </Button>
          </div>
        </>
      )}
    </div>
  )

  /** 「待分类」层的右栏（与目录层同一套 `.ks-list/.ks-lhead/.ks-item` 机制）。 */
  const inboxMain = (
    <>
      <div className="ks-list-cap">
        <span className="ks-lhead-name ks-kb-grow" title="知识库 / 待分类">待分类</span>
        {/* 业主 2026-09-22：提问入口就在**这一行**（文件名那一条 bar 上） */}
        {askEntry}
        {/* ══ 「补全分类号」（自愈机制，2026-09-22）═══════════════════════════════
            这是**插件自己的入口**（业主口径：机制必须在产品里，不许靠人手动改库）。
            按钮上的数字是后端**现算的**"全库还缺几篇标准没有分类号"；读不到就显示"—"
            （**不许**拿本地已知数字冒充 —— 那会把"读不到"说成"0 篇"）。
            跑的时候按钮变「停止」；下面显示真实的 done/total 与失败清单。 */}
        <Button
          variant="outline"
          size="sm"
          className="ks-ccs-btn"
          disabled={busy}
          title={ccsMissing === null
            ? '读不到还缺几篇（接口没答上来）——点一下仍然可以试着补'
            : `插件自己按「官方接口 → 网页抓取 → 本地对照表」逐篇查缺的分类号`
              + `（全库还缺 ${String(ccsMissing)} 篇；一篇一到几秒，后台跑）`}
          onClick={() => { void (ccsRunning ? stopCcsBackfill() : runCcsBackfill()) }}
        >
          {ccsRunning ? '停止补全分类号' : '补全分类号'}
          {ccsMissing === null ? '（—）' : `（还缺 ${String(ccsMissing)} 篇）`}
        </Button>
        <span className="ks-kb-hint">
          {inboxTotal} 篇还没归位
          {needle === '' ? '' : `（本页筛出 ${inboxShown.length} 篇）`}
        </span>
      </div>
      {/* 补全的**进度与失败清单**（只在真跑过之后出现；没跑过不占地方）。
          ⚠ 数字**逐类分开**：补到 / 查无 / 查询失败 / 读不出来 —— 不许合并成"部分失败"。 */}
      {ccsStatus === null || (ccsStatus.total === 0 && ccsStatus.done === 0) ? null : (
        <div className="ks-ccs-bar" role="status" data-ccs-running={ccsRunning ? '1' : '0'}>
          <span className="ks-ccs-line">
            补全分类号：已跑 {ccsStatus.done} / {ccsStatus.total} 篇
            · 补到 {ccsStatus.found} 篇（其中新写标签 {ccsStatus.applied} 篇）
            · 查无 {ccsStatus.not_found} 篇
            · 查询失败 {ccsStatus.network_failed} 篇
            · 读不出来 {ccsStatus.parse_failed} 篇
            · 不适用 {ccsStatus.not_applicable} 篇
            {ccsStatus.skipped > 0 ? ` · 跳过 ${ccsStatus.skipped} 篇` : ''}
            {ccsStatus.cancelled ? ' · 这一批是手动停的' : ''}
          </span>
          {ccsStatus.failures.length === 0 ? null : (
            <details className="ks-ccs-fails">
              <summary>
                没补到的 {ccsStatus.failures.length} 篇（逐篇原因）
              </summary>
              <ul className="ks-ccs-fail-list">
                {ccsStatus.failures.slice(0, 50).map((f) => (
                  <li key={f.doc_id}>
                    <span className="ks-ccs-fail-no">{f.standard_no === '' ? f.doc_id : f.standard_no}</span>
                    <span className="ks-ccs-fail-why">
                      {f.reason !== undefined && f.reason !== '' ? f.reason : f.outcome}
                    </span>
                  </li>
                ))}
              </ul>
              {ccsStatus.failures.length > 50 ? (
                <span className="ks-kb-hint">（这里只列前 50 篇；接口里是完整的。）</span>
              ) : null}
            </details>
          )}
        </div>
      )}
      {searchBox}
      {batchBar}
      {actionPanel}
      {actMsg === '' ? null : (
        <div className="ks-ib-msg" role="status">{actMsg}</div>
      )}
      {inbox.length > 0 ? (
        <div className="ks-list ks-list-inbox ks-inbox">
          <KsListHead cols={INBOX_COLUMNS} />
          {inboxShown.map(renderInboxRow)}
        </div>
      ) : null}
      {inbox.length === 0 ? (
        <div className="ks-empty-card">
          <span className="ks-empty-ico"><IconChecklistOutline14 size={28} /></span>
          <span className="ks-empty-t">没有排队等归位的文件</span>
          <span className="ks-empty-d">
            库里每一篇都已经归位了。用上面的「上传到这一层」把新文件导进来，
            它们会先排队等在这里。
          </span>
        </div>
      ) : null}
      {inbox.length > 0 && inboxShown.length === 0 && needle !== '' ? (
        <div className="ks-empty-card">
          <span className="ks-empty-ico"><IconSearchOutline16 size={28} /></span>
          <span className="ks-empty-t">这一层没有符合搜索的条目</span>
          <span className="ks-empty-d">
            本页 {inbox.length} 篇里没有标准号/名称含「{search.trim()}」的。
            （只筛已经读出来的这一页；翻页后可能还有。）
          </span>
          <Button variant="outline" size="sm" title="清空搜索串" onClick={() => { setSearch('') }}>
            清除搜索
          </Button>
        </div>
      ) : null}
      {inboxTotal > INBOX_PAGE_SIZE ? (
        <div className="ks-pager">
          <Button
            variant="outline"
            size="sm"
            className="ks-pager-btn"
            disabled={busy || inboxOffset <= 0}
            title="上一页"
            onClick={() => { void loadInbox(Math.max(0, inboxOffset - INBOX_PAGE_SIZE), { silent: true }) }}
          >
            <IconChevronLeftOutline14 />
          </Button>
          <span className="ks-pager-n">
            第 {Math.floor(inboxOffset / INBOX_PAGE_SIZE) + 1} / {Math.max(1, Math.ceil(inboxTotal / INBOX_PAGE_SIZE))} 页
            · 共 {inboxTotal} 篇
          </span>
          <Button
            variant="outline"
            size="sm"
            className="ks-pager-btn"
            disabled={busy || !inboxMore}
            title="下一页"
            onClick={() => { void loadInbox(inboxOffset + INBOX_PAGE_SIZE, { silent: true }) }}
          >
            <IconChevronRightOutline14 />
          </Button>
        </div>
      ) : null}
    </>
  )

  return (
    <div className="ks-page">
      <div className="ks-kb">
        <KsTopTabs page={page} onGo={(pp) => { setPageOverride(pp) }} onPdf={() => { tab.actions.openTab(KS_EVIDENCE_KIND) }} />
        <header className="ks-page-head">
          <div className="ks-page-title">知识库</div>
        </header>
        <div className="ks-page-rule" />

        {/* ⚠⚠ **业主 2026-09-22 点名删掉两处"AI 味很重、也没啥实际功能"的描述**（原话）：
              「这种话为什么要放进来，AI 味很重；还有这个 `真库：左边目录、右边当前这一层`
                这个放在这里干什么。把这种 AI 味道很重的、也没啥实际功能的描述都去掉。」
            ① **标题下那行副标题**（原文，留痕）：
               `法规/标准的落点：知识库 → 目录 → 条款；颜色一律走宿主主题 token，深浅色自动跟随`
               —— 讲的是**实现细节**（主题 token）与**设计说明**（"落点"），不是给用户看的信息；
            ② **顶上那条 ⓘ 告知条**（原文，留痕）：`真库：左边目录、右边当前这一层`
               （外加一长串挂 title 的接口名/版式描述）—— **描述版式 = 说废话**。
            ⇒ 两处**连同容器与图标一起删干净**（不留空壳）。`.ks-page-sub` / `.ks-kb-banner`
               这两个类**没删**：能力页（`KsCapabilityPage`）与本页"尚未实现"的占位条仍在用。
            ⚠ 判据同步翻成**负向**（`smoke-client-entry` 的在场字面量表 + jsdom 的 K 段），
               原文与理由留在那些断言里。 */}
        {/* 顶上一行：返回上一层 + 逐级可点的路径 + 上传/刷新 */}
        <div className="ks-kb-row">
          <Button
            variant="outline"
            size="sm"
            className="ks-back"
            disabled={layer === 'folder' && levelId === null}
            title={layer === 'inbox'
              ? '回到最外层（离开「待分类」）'
              : (levelId === null
                ? '你已经是最外层，没有上一级可回'
                : `回到上一层（现在在：${['知识库', ...crumb.map((f) => f.name)].join(' / ')}）`)}
            onClick={goUp}
          >
            <IconChevronLeftOutline14 />
            返回上一层
          </Button>
          <span
            className="ks-crumb"
            title={`当前路径：${layer === 'inbox'
              ? '知识库 / 待分类'
              : ['知识库', ...crumb.map((f) => f.name)].join(' / ')}`}
          >
            <span className="ks-crumb-path">
              <span className="ks-crumb-item">
                {layer === 'folder' && levelId === null ? (
                  <span
                    className="ks-crumb-here"
                    aria-current="page"
                    data-current="true"
                    title="你现在在这一级（不可点）"
                  >
                    知识库
                  </span>
                ) : (
                  <button
                    type="button"
                    className="ks-crumb-go"
                    aria-label="回到最外层"
                    title="回到最外层"
                    onClick={() => { goto(null) }}
                  >
                    知识库
                  </button>
                )}
              </span>
              {/* 「待分类」是这一页自己的一层（不是库里的目录）—— 面包屑照样逐段如实。 */}
              {layer === 'inbox' ? (
                <Fragment key="__inbox">
                  <span className="ks-crumb-sep" aria-hidden="true">/</span>
                  <span className="ks-crumb-item">
                    <span
                      className="ks-crumb-here"
                      aria-current="page"
                      data-current="true"
                      title="你现在在「待分类」（不可点）"
                    >
                      待分类
                    </span>
                  </span>
                </Fragment>
              ) : null}
              {layer === 'inbox' ? null : crumb.map((node, i) => {
                const here = i === crumb.length - 1
                /* ⚠ 分隔符是**条目的兄弟**（不是塞进条目里）——`.ks-crumb-item` 的 textContent
                   因此**只等于那一级的名字**（渲染级冒烟与 ui-render-shot 都按它逐段比对；
                   本批一开始把 sep 放进 item 里，实测面包屑变成「知识库//标准」，当场红）。 */
                return (
                  <Fragment key={node.folder_id}>
                    <span className="ks-crumb-sep" aria-hidden="true">/</span>
                    <span className="ks-crumb-item">
                      {here ? (
                        <span
                          className="ks-crumb-here"
                          aria-current="page"
                          data-current="true"
                          title="你现在在这一级（不可点）"
                        >
                          {node.name}
                        </span>
                      ) : (
                        <button
                          type="button"
                          className="ks-crumb-go"
                          aria-label={`回到「${node.name}」这一级`}
                          title={`回到「${node.name}」`}
                          onClick={() => { goto(node.folder_id) }}
                        >
                          {node.name}
                        </button>
                      )}
                    </span>
                  </Fragment>
                )
              })}
            </span>
            {/* 顶层**如实说**"你在最外层"（需求 3）；在目录里则报这一级的条目数；
                「待分类」层报**还没归位**的篇数。 */}
            <span className="ks-crumb-n">
              {layer === 'inbox'
                ? `还没归位 ${String(inboxTotal)} 篇`
                : (levelId === null
                  ? '你在最外层'
                  : `${subs.length} 个子目录 · ${filesTotal} 篇文件`)}
            </span>
          </span>
          <div className="ks-kb-grow" />
          {/* ⚠ **业主 2026-09-22 定的位置**：「在此范围内提问」+ 范围 chip **不在这一行**了 ——
              它们搬到了**当前文件夹名那一行**（`.ks-list-cap`，搜索框上面，见下面的 `askEntry`）。
              业主原话："按钮改到搜索栏上面显示文件夹名称的 bar 上，这样就很清楚是在这个文件夹内进行搜索"。
              ⚠ 判据也跟着搬：`ui-render-shot` 的 `#ask` 量点会**报出这个按钮在哪一行**，
                不是那一行就红（不许"挪回去也能过"）。 */}
          {/* 第 5 步：**建目录**的入口（建在当前这一级下面；最外层就是顶层目录）。
              「待分类」层不建目录（它不是库里的目录；那里是处置文件的地方）。 */}
          {layer === 'folder' ? (
            <Button
              variant="outline"
              size="sm"
              className="ks-mkdir-open"
              title={levelId === null
                ? '在最外层建一个顶层目录（同名同层会被后端拒，原话显示在面板里）'
                : `在「${levelName}」下面建一个下级目录`}
              onClick={() => { openAction('mkdir', []) }}
            >
              <IconPlusOutline16 />
              新建下级目录
            </Button>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            className="ks-upload-open"
            aria-expanded={upOpen}
            title={layer === 'inbox'
              ? '把「来源目录」里的文件导进来（就在这个列表里排队，等你处置）'
              : (levelId === null
                ? '把「来源目录」里的文件导入知识库（你现在在最外层 ⇒ 它们会留在最外层，还没归位）'
                : `把「来源目录」里的文件导入并直接放进「${levelName}」`)}
            onClick={() => { void openUpload() }}
          >
            <IconPlusOutline16 />
            上传到这一层
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="ks-refresh"
            title="重新读取当前这一层"
            onClick={() => {
              if (layer === 'inbox') void loadInbox(inboxOffset, { silent: true })
              else void loadLevel(levelId, fileOffset, { silent: true })
            }}
          >
            <IconRefreshOutline16 />
          </Button>
        </div>

        {/* 上传面板（需求 5）：来源目录 + 导入按钮 + 如实的过程/结果说明 */}
        {upOpen ? (
          <div className="ks-upload">
            <div className="ks-upload-row">
              <span className="ks-upload-label">来源目录</span>
              <Input
                className="ks-upload-dir"
                value={upDir}
                placeholder="放 PDF 的目录（绝对路径）"
                aria-label="要导入的 PDF 所在的目录（绝对路径）"
                onChange={(event) => { setUpDir(event.target.value) }}
              />
              <Button
                variant="primary"
                size="sm"
                className="ks-upload-go"
                disabled={upPhase === 'running' || upDir.trim() === ''}
                title={layer === 'inbox'
                  ? '导入这些文件；它们就排在「待分类」这个列表里等你处置'
                  : (levelId === null
                    ? '导入这些文件；你在最外层 ⇒ 它们会留在最外层（会出现在「待分类」里）'
                    : `导入这些文件并直接放进「${levelName}」（不进自动识别）`)}
                onClick={() => { void runUpload() }}
              >
                {upPhase === 'running' ? '导入中…' : '导入到这一层'}
              </Button>
            </div>
            {/* 只读体检（原「入库预览」那一页的能力，第 4 步并到这里）：不写库、不外发。 */}
            <div className="ks-upload-row">
              <span className="ks-upload-label">先看一眼</span>
              <Button
                variant="outline"
                size="sm"
                className="ks-upload-check"
                disabled={upDir.trim() === ''}
                title="只读体检（抽样 5 篇）：能进 / 要留意 / 进不了；不写库、不调云解析"
                onClick={() => { void runCheck() }}
              >
                <IconChecklistOutline14 />
                先体检（只读）
              </Button>
              <span className="ks-upload-hint">
                {upCheck === '' ? '体检只是看一眼，库里一篇都不会多。' : upCheck}
              </span>
              {/* 第 5 步 §4① 的裁定：`KsIngestPanel`（**逐篇**只读预览 + 全量异步预览）**复活**
                  到这里 —— 上面那个按钮只报三个总账数字，要看**每一篇**的分级/裁决/前后样例/
                  识别与版面指标就得有这一个面板。也正因为产品里真挂得上它，`ui-render-shot.mjs`
                  的 `PAGES.ingest` 与 `smoke-kb-pad-pixels.mjs` 的 `.ks-ing` 那些条目才不是
                  "只照着测试脚本活着的组件"（选它而不是删它的理由写在文件头 §4①）。 */}
              <Button
                variant="ghost"
                size="sm"
                className="ks-upload-preview-open"
                aria-expanded={upPreview}
                title="逐篇只读预览（分级/裁决/样例/识别与版面指标；不写库、默认不外发）"
                onClick={() => { setUpPreview(!upPreview) }}
              >
                <IconChevronDownOutline14 />
                逐篇看
              </Button>
            </div>
            {upPreview ? (
              <div className="ks-upload-preview">
                {/* ⚠ `initialDir` 用上面那个「来源目录」框的值；面板里换了目录会**同步回来**
                    （一个来源目录、一处可改 —— 不许出现两个各说各话的目录框）。 */}
                <KsIngestPanel
                  visible={upPreview}
                  initialDir={upDir}
                  onDirChange={setUpDir}
                />
              </div>
            ) : null}
            {/* 覆盖重导（引擎的 `reingest`）：会**删掉同标准号的旧文档**再建新的 ⇒ 必须人显式开。 */}
            <div className="ks-upload-row">
              <span className="ks-upload-label">覆盖</span>
              <Checkbox
                checked={upReingest}
                onChange={(next) => { setUpReingest(next) }}
                label="覆盖重导（同标准号的旧文档会被替换）"
                title="打开后：这次导入明知库里已有同号/同文件的登记也重新解析一遍，旧文档会被删掉再建。"
              />
            </div>
            <div className="ks-upload-note">
              {layer === 'inbox'
                ? '你在「待分类」：导入的文件就排在下面这个列表里（还没归位），当场就能处置。'
                : (levelId === null
                  ? '你在最外层：导入的文件会留在最外层（还没归位，会出现在「待分类」里）。'
                  : `导入完成后，新文件会直接放进「${levelName}」，不会进自动识别。`)}
              {' '}扫描件/大文件解析要等一会儿，下面的进度说的是库里真的解析了多少篇。
            </div>
            {upMsg === '' ? null : (
              <div className={upPhase === 'error' ? 'ks-upload-msg ks-upload-msg-bad' : 'ks-upload-msg'}>
                {upMsg}
              </div>
            )}
          </div>
        ) : null}

        {/* 第 6 步：**按范围提问**的面板（范围在 chip 上、提问与答案在这里）。
            诚实边界（写在明面上）：
              · 范围**一定**随请求发出去，引擎**在检索层**限定六条召回通道 ⇒ 范围内没有就是没有；
              · 答案区显示引擎回显的**实际范围**；若回显说"没限定范围"而这次明明带了范围，
                会**当众标红**（不许静默当没发生）；
              · 这一页**不提供**"不限定范围的提问"（清掉范围就收起面板）。 */}
        {askOpen && askScope !== null ? (
          <div className="ks-ask" data-ks-ask="open">
            <div className="ks-ask-head">
              <span className="ks-ask-where">{askWhereText(askScope)}</span>
              <span className="ks-ask-count">
                {askCountErr !== ''
                  ? `数不出来：${askCountErr}`
                  : (askCounts === null
                    ? '正在数这个范围里有多少篇…'
                    : `${String(askCounts.folder_count)} 个目录 · ${String(askCounts.doc_count)} 篇`)}
              </span>
              <div className="ks-kb-grow" />
              <Button variant="ghost" size="sm" className="ks-ask-close" title="收起提问面板（范围留着）"
                onClick={() => { setAskOpen(false) }}>
                <IconChevronDownOutline14 />
                收起
              </Button>
              <Button variant="ghost" size="sm" className="ks-ask-clear" title="清掉范围并收起面板" onClick={clearAsk}>
                <IconCloseOutline16 />
                清掉范围
              </Button>
            </div>
            <div className="ks-ask-row">
              <span className="ks-ask-label">问题</span>
              <Input
                className="ks-ask-q"
                value={askQ}
                placeholder="要在这个范围里问什么？（例：动火作业怎么分级）"
                aria-label="要在选定的知识库目录范围里问的问题"
                onChange={(event) => { setAskQ(event.target.value) }}
              />
              <Button
                variant="primary"
                size="sm"
                className="ks-ask-go"
                disabled={askPhase === 'running' || askQ.trim() === ''}
                title={`只在这个范围里检索：${askScope.label}`}
                onClick={() => { void runAsk() }}
              >
                {askPhase === 'running' ? '在问…' : '问一问'}
              </Button>
            </div>
            <div className="ks-ask-hint">
              只在你选定的这个范围里检索；范围内没有就直说 —— 不会拿范围外的内容冒充。
            </div>
            {askMsg === '' ? null : (
              <div className="ks-ask-msg ks-ask-msg-bad" role="alert">{askMsg}</div>
            )}
            {askRes === null ? null : (
              <div className="ks-ask-res" data-ks-ask-res="on">
                {/* 发起**之后**如实说这次到底在什么范围里检索的（引擎回显，不是前端自己写的）。 */}
                {askRes.scope === null ? (
                  <div className="ks-ask-msg ks-ask-msg-bad">
                    注意：这次带了范围（{askScope.label}），可引擎回显说**没有限定范围** ——
                    这份答案可能来自整个知识库，**不要**当成范围内检索的结果。
                  </div>
                ) : (
                  <div className="ks-ask-echo">
                    引擎回显：这次实际范围 = {String(askRes.scope.folder_count)} 个目录 ·
                    {' '}{String(askRes.scope.doc_count)} 篇
                    {askRes.scope.empty ? '（范围内一篇都没有 ⇒ 引擎一次检索都没做）' : ''}
                  </div>
                )}
                <div className="ks-ask-tier">档次：{askRes.tier}</div>
                {askRes.scope !== null && askRes.scope.empty ? (
                  <div className="ks-ask-empty">
                    <strong>范围内没有</strong>
                    <span>你选的范围里一篇文件都没有，所以没有任何依据可引用 —— 这不是"库里没有"。</span>
                  </div>
                ) : null}
                {askRes.conclusion === '' ? null : (
                  <div className="ks-ask-conc"><span className="ks-ask-h">结论</span>{askRes.conclusion}</div>
                )}
                {askRes.derivation === '' ? null : (
                  <div className="ks-ask-der"><span className="ks-ask-h">推导</span>{askRes.derivation}</div>
                )}
                {/* 依据区：逐条列出**这次真的用到的**条款（范围外的条款不可能出现在这里）。 */}
                <div className="ks-ask-ev">
                  <span className="ks-ask-h">依据（{String(askRes.evidence.length)} 条）</span>
                  {askRes.evidence.length === 0 ? (
                    <div className="ks-ask-empty">
                      <strong>范围内没有</strong>
                      <span>这个范围里没有找到可引用的现行条款；换几个目录，或把范围放大一点再问。</span>
                    </div>
                  ) : askRes.evidence.map((ev, i) => (
                    <div className="ks-ask-evrow" key={String(ev.clause_revision_id ?? i)}>
                      <span className="ks-ask-evno">
                        {String(ev.standard_no ?? '—')} {String(ev.clause_number ?? '')}
                      </span>
                      <span className="ks-ask-evtitle">{String(ev.title ?? '')}</span>
                      <span className="ks-ask-evtext">{String(ev.snippet ?? '')}</span>
                    </div>
                  ))}
                </div>
                {askRes.notes.length === 0 ? null : (
                  <div className="ks-ask-notes">
                    <span className="ks-ask-h">说明</span>
                    {askRes.notes.map((nt, i) => (
                      <div className="ks-ask-note" key={`n${String(i)}`}>{nt}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}

        {phase === 'error' ? (
          <div className="ks-kb-err" role="alert">
            <strong>读不到知识库</strong>
            <span className="ks-kb-hint">{errMsg}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (layer === 'inbox') void loadInbox(inboxOffset)
                else void loadLevel(levelId, 0)
              }}
            >
              重试
            </Button>
          </div>
        ) : null}

        <div className="ks-split">
          {/* ══ 左列：真目录树（按需展开，一次只拉一层） ══ */}
          <div className="ks-kb-tree">
            <div className="ks-tree-head">目录</div>
            <div className="ks-tree-body">
              {/* ⚠ **只调一次** `renderTreeRow('root', …)`：它自己会把展开的子节点递归渲染出来
                  （外面再 map 一遍 rootKids 就是双份 —— 本批实测：树上出现两份一级目录）。
                  「待分类」那一行靠第 6 个参数插在最外层**之后、四个顶层目录之前**。 */}
              {renderTreeRow('root', '最外层', null, 0,
                layer === 'folder' && levelId === null, inboxTreeRow)}
              {tree.root?.loading === true ? <div className="ks-tree-hint">正在读取…</div> : null}
            </div>
          </div>

          {/* ══ 右栏：**只显示当前这一层** ══
              · 「待分类」层：`inboxMain`（勾选 / 文件名 / 状态 / 建议去向 / ⋮ + 批量条 + 导入）；
              · 目录层：下级目录在前、这一级直接放的文件在后（顺序照后端给的）。 */}
          <div className="ks-main">
            {layer === 'inbox' ? inboxMain : (
              <>
            <div className="ks-list-cap">
              <span className="ks-lhead-name ks-kb-grow" title={['知识库', ...crumb.map((f) => f.name)].join(' / ')}>
                {/* 批D2-2：效力总览的导出入口归位（菜单页已撤；能力不丢）。 */}
                <button type="button" style={{ marginLeft: 8, fontSize: 11, cursor: 'pointer' }}
                  title="导出《效力总览》Excel（全库四色效力现状）"
                  onClick={() => {
                    void (async () => {
                      try {
                        const { exportEffectReport } = await import('./api')
                        await exportEffectReport('all', undefined, undefined)
                      } catch {
                        /* 导出失败：面板口径=如实报错；这里最小化为无动作（重试即可见） */
                      }
                    })()
                  }}>导出效力总览</button>
                {levelName}
              </span>
              {/* 业主 2026-09-22：提问入口搬到**当前文件夹名这一行**（搜索框上面那条 bar）——
                  这样一眼就知道"是在这个文件夹里搜"。 */}
              {askEntry}
              <span className="ks-kb-hint">
                {subs.length} 个子目录 · {filesTotal} 篇文件
                {needle === '' ? '' : `（本页筛出 ${dirsShown.length} 个目录 / ${filesShown.length} 篇）`}
              </span>
            </div>

            {searchBox}

            {/* 第 5 步：目录/文件层与「待分类」层**共用同一个批量条与同一个动作面板**
                （`batchBar` / `actionPanel` 各只有一处定义，按层给动作 —— 不许复制出第二套）。 */}
            {batchBar}
            {actionPanel}
            {actMsg === '' ? null : (
              <div className="ks-ib-msg" role="status">{actMsg}</div>
            )}

            {/* 目录层：**与文件列表同构**的列表（同一套 .ks-list/.ks-lhead/.ks-item 机制，
                只换一份列定义 DIR_COLUMNS 与一条自己的 --ks-cols）。 */}
            {subs.length > 0 || dirsShown.length > 0 ? (
              <div className="ks-list ks-list-dirs ks-dirs">
                <KsListHead cols={DIR_COLUMNS} />
                {dirsShown.map((child) => {
                  const isOpen = menuFor === pickDirKey(child.folder_id)
                  /* 目录行的 ⋮ 菜单（第 5 步）：改名 / 新建下级 / 挪 / 复制 / 删。
                     ⚠ **2026-09-22 业主改的文案**：`挪到某个目录…` ⇒ **`移动到`**、
                     `复制到某个目录…` ⇒ **`复制到`**（原话："挪到某个目录直接写移动到；复制到某个目录，直接就写复制到"）。
                     「在此范围内提问」**目录行保持原样**（问的是那一棵目录）；
                     `删掉这个目录…` 是**真删目录**（先拉 delete-preview 再二选一）⇒ 保持。 */
                  const dirMenu: { id: string; label: string }[] = [
                    { id: 'rename', label: '改名…' },
                    { id: 'mkdir', label: '在这个目录下新建…' },
                    { id: 'move', label: '移动到' },
                    { id: 'copy', label: '复制到' },
                    /* 第 6 步：在**这一个目录**（它 + 全部下级）里提问。 */
                    { id: 'ask', label: '在此范围内提问' },
                    { id: 'delete', label: '删掉这个目录…' },
                  ]
                  const dirCell = (key: DirColKey): ReactNode => {
                    switch (key) {
                      case 'dpick':
                        return (
                          <span className="ks-pick">
                            <Checkbox
                              className="ks-pick-cb"
                              checked={picked.has(pickDirKey(child.folder_id))}
                              onChange={(next) => { togglePick(pickDirKey(child.folder_id), next) }}
                              label={child.name}
                              title={`选中目录「${child.name}」（选中后下面会出现批量条：移动到… / 复制到… / 删掉目录…）`}
                            />
                          </span>
                        )
                      case 'dname':
                        /* ⚠ 「进入这一级」是**这一格里的真 button**（行本身是 div：行内要有
                           勾选框与 ⋮ 两个真控件，button 里嵌 input 是非法 HTML）。
                           批D2（业主 2026-09-22）：名字右侧空白处放**该夹效力四色灯**。 */
                        return (
                          <>
                            <button
                              type="button"
                              className="ks-dir-open"
                              title={`进入「${child.name}」（这一棵目录下共 ${child.file_count_deep} 篇）`}
                              aria-label={`进入目录「${child.name}」，这一棵目录下共 ${child.file_count_deep} 篇`}
                              onClick={() => { goto(child.folder_id) }}
                            >
                              <span className="ks-fileico" title="目录"><IconFolderOpenOutline16 /></span>
                              <span className="ks-dir-name" title={child.name}>{child.name}</span>
                              <span className="ks-dir-go"><IconChevronRightOutline14 /></span>
                            </button>
                            <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 8,
                              fontSize: 11, whiteSpace: 'nowrap', color: 'var(--dsw-alias-label-secondary)' }}
                              title={`「${child.name}」这一棵里：🟢 现行 ${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).green} · 🟡 即将实施 ${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).yellow} · 🔴 废止/被代 ${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).red} · ⚪ 未知 ${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).gray}`}>
                              {(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).red ? `🔴${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).red} ` : ''}
                              {(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).yellow ? `🟡${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).yellow} ` : ''}
                              {(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).green ? `🟢${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).green}` : ''}
                              {(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).gray ? ` ⚪${(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).gray}` : ''}
                              {(child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).red + (child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).yellow + (child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).green + (child.effect_deep ?? { green: 0, red: 0, yellow: 0, gray: 0 }).gray === 0
                                ? '—' : ''}
                            </span>
                          </>
                        )
                      case 'dcount':
                        // ⚠ 「篇数」= 这一**棵**下的篇数（后端 `file_count_deep`，含更深层）
                        return <span className="ks-kb-badge">{child.file_count_deep} 篇</span>
                      case 'dmore':
                        return (
                          <span className="ks-item-more">
                            <Menu
                              open={isOpen}
                              portal
                              autoFocus
                              align="end"
                              items={dirMenu}
                              onClose={() => { setMenuFor(null) }}
                              onSelect={(id) => {
                                setMenuFor(null)
                                const key = pickDirKey(child.folder_id)
                                if (id === 'rename') openAction('rename', [key])
                                else if (id === 'mkdir') openAction('mkdir', [])
                                else if (id === 'move') openAction('move', [key])
                                else if (id === 'copy') openAction('copy', [key])
                                else if (id === 'ask') void openAsk([key])
                                else if (id === 'delete') openAction('folder-del', [key])
                              }}
                              anchor={(
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-haspopup="menu"
                                  aria-expanded={isOpen}
                                  aria-label={`目录「${child.name}」的操作`}
                                  title="处置这个目录（改名 / 新建下级 / 移动到 / 复制到 / 删）"
                                  onClick={() => { setMenuFor(isOpen ? null : pickDirKey(child.folder_id)) }}
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
                    /* ⚠ 第 5 步：**div**（原来是 button）—— 行内现在有勾选框与 ⋮ 两个真控件。
                       整行可点 = 进入这一级（与文件行"整行可点 = 打开详情"同一种做法）。 */
                    <div
                      key={child.folder_id}
                      className="ks-item ks-dir-row"
                      data-dir-id={child.folder_id}
                      onClick={(e) => {
                        const t = e.target as (HTMLElement | null)
                        if (t === null || typeof t.closest !== 'function') return
                        if (t.closest('button,input,a,[role=menuitem],[role=menu]') !== null) return
                        goto(child.folder_id)
                      }}
                    >
                      {DIR_COLUMNS.map((col) => (
                        <div className={`ks-cell ${col.cls}`} key={col.key}>{dirCell(col.key)}</div>
                      ))}
                    </div>
                  )
                })}
              </div>
            ) : null}

            {/* 空态（需求 6）：分清**本来就没东西**与**被搜索筛没了** */}
            {levelEmpty ? (
              <div className="ks-empty-card">
                <span className="ks-empty-ico"><IconFolderOpenOutline16 size={28} /></span>
                <span className="ks-empty-t">这一层还没有东西</span>
                <span className="ks-empty-d">
                  这一层里既没有下级目录，也没有直接放在这里的文件。
                  {levelId === null
                    ? '用上面的「上传到这一层」把文件导进来。'
                    : '用上面的「上传到这一层」把文件导进这个目录。'}
                </span>
              </div>
            ) : null}
            {!levelEmpty && nothingShown && needle !== '' ? (
              <div className="ks-empty-card">
                <span className="ks-empty-ico"><IconSearchOutline16 size={28} /></span>
                <span className="ks-empty-t">这一层没有符合搜索的条目</span>
                <span className="ks-empty-d">
                  本页 {subs.length} 个目录 / {files.length} 篇文件里，没有名字或标准号含「{search.trim()}」的。
                  （只筛已经读出来的这一页；翻页后可能还有。）
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  title="清空搜索串"
                  onClick={() => { setSearch('') }}
                >
                  清除搜索
                </Button>
              </div>
            ) : null}

            {/* 文件层：这一级**直接**放的文件（分页）。 */}
            {files.length > 0 ? (
              <div className="ks-list">
                <KsListHead cols={COLUMNS} />
                {filesShown.map((doc) => {
                  const st = STATUS[statusOf(doc.legal_status)]
                  const isOpen = menuFor === doc.doc_id
                  const fileKey = pickFileKey(doc.doc_id)
                  /**
                   * 文件行的 ⋮ 菜单（第 5 步）—— **按"这一篇现在挂在哪"给动作**：
                   *   · 最外层那些文件**还没进任何目录**（后端 `list_folder(None)` 的语义）⇒
                   *     给的是「加进某个目录…」（`members`）；"移动"在这里没有来源目录，不给死按钮。
                   *   · 在某个目录里 ⇒ 「移动到」（`members/move`，来源 = 当前这一级）、
                   *     「复制到」（多一处位置）、「移出」（只删归属行，**不删文件**）。
                   *   · **删文档**（不可逆）**不在这里** —— 只有「待分类」层那一个入口。
                   *
                   * ⚠⚠ **2026-09-22 业主改的文案**（原话："挪到某个目录直接写移动到；复制到某个目录，
                   *   直接就写复制到"；"「从这一层拿掉」是啥意思，删除就说删除"）：
                   *   `挪到某个目录…` ⇒ **`移动到`**；`复制到某个目录…` ⇒ **`复制到`**；
                   *   `从这一层拿掉` ⇒ **`移出`**（业主选定的词）。
                   *   ⚠ **"移出"的真相必须留在一处**：这个动作**只把这一篇从当前目录移出，
                   *   文件本身不删**（还在库里，别处挂着的照旧）。宿主 `MenuItem` **没有 `title` 字段**
                   *   （`ui-primitives/src/Menu.tsx` 的 `MenuItem` 只有 id/label/disabled/icon/danger/submenu
                   *   —— 源码读过）⇒ 没法给菜单项本身挂悬停说明；改成挂在**这一行的 ⋮ 触发按钮**上
                   *   （见下面那行 title）+ 批量条「移出」的 title + 动作完成后 `actMsg` 里如实说明。
                   */
                  const fileMenu: { id: string; label: string }[] = [
                    { id: 'detail', label: '详情' },
                    /* 第 6 步：**这一篇**的范围（`kb_doc_ids`）—— 与"这一级"的范围是两回事。
                       ⚠ 2026-09-22 业主：**单个文件**上点开三个点 ⇒ 文案是「在此文件中提问」。 */
                    { id: 'ask', label: '在此文件中提问' },
                    ...(levelId === null
                      ? [{ id: 'add', label: '放进某个目录…' }]
                      : [{ id: 'move', label: '移动到' },
                        { id: 'copy', label: '复制到' },
                        { id: 'remove', label: '移出' }]),
                  ]
                  const cellFor = (key: ColKey): ReactNode => {
                    switch (key) {
                      case 'fpick':
                        return (
                          <span className="ks-pick">
                            <Checkbox
                              className="ks-pick-cb"
                              checked={picked.has(fileKey)}
                              onChange={(next) => { togglePick(fileKey, next) }}
                              label={doc.standard_name ?? doc.doc_id}
                              title={`选中「${doc.standard_name ?? doc.doc_id}」（选中后下面会出现批量条）`}
                            />
                          </span>
                        )
                      case 'name':
                        return (
                          <>
                            {/* ⚠⚠ **业主 2026-09-22**：文件行前面那个图标**删掉**（目录行的文件夹图标保留）。 */}
                            <span className="ks-item-name" title={doc.standard_name ?? doc.doc_id}>
                              {doc.standard_name ?? doc.doc_id}
                            </span>
                            <span className="ks-item-sub">
                              <span className="ks-item-meta">{doc.standard_no === null || doc.standard_no === '' ? '—' : doc.standard_no}</span>
                            </span>
                          </>
                        )
                      case 'status':
                        return <span className={st.cls}>{st.text}</span>
                      case 'date':
                        return <span className="ks-kb-hint">{doc.effective_from === null || doc.effective_from === '' ? '—' : doc.effective_from}</span>
                      case 'stage':
                        return (
                          <span
                            className="ks-kb-hint"
                            title={doc.confidence === null ? undefined : `识别率 ${String(doc.confidence)}`}
                          >
                            {stageText(doc.stage)}
                            {doc.failure_kind === null || doc.failure_kind === '' ? '' : `（${doc.failure_kind}）`}
                          </span>
                        )
                      case 'more':
                        return (
                          <span className="ks-item-more">
                            <Menu
                              open={isOpen}
                              portal
                              autoFocus
                              align="end"
                              items={fileMenu}
                              onClose={() => { setMenuFor(null) }}
                              onSelect={(id) => {
                                setMenuFor(null)
                                if (id === 'detail') setOpenDoc(openDoc === doc.doc_id ? null : doc.doc_id)
                                else if (id === 'ask') void openAsk([fileKey])
                                else if (id === 'add') openAction('add', [fileKey])
                                else if (id === 'move') openAction('move', [fileKey])
                                else if (id === 'copy') openAction('copy', [fileKey])
                                else if (id === 'remove') void runRemove([fileKey])
                              }}
                              anchor={(
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-haspopup="menu"
                                  aria-expanded={isOpen}
                                  aria-label={`${doc.standard_name ?? doc.doc_id} 的更多操作`}
                                  title="更多操作（详情 / 移动到 / 复制到 / 移出）——「移出」只把这一篇从当前目录移出，文件不会删除"
                                  onClick={() => { setMenuFor(isOpen ? null : doc.doc_id) }}
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
                    /* 整行可点（业主 2026-09-21）：分流规则在 `openRowDetail` 里，唯一所有者。
                       ⚠ 它是 **div**（不是 button）：行内已经有「⋮」这个真控件，
                         把行做成按钮会嵌套交互元素（HTML 非法 + 读屏器读成两个控件）。 */
                    <div
                      className={openDoc === doc.doc_id ? 'ks-item ks-file-row ks-item-on' : 'ks-item ks-file-row'}
                      key={doc.doc_id}
                      onClick={(e) => { openRowDetail(doc, e) }}
                    >
                      {COLUMNS.map((col) => (
                        <div className={`ks-cell ${col.cls}`} key={col.key}>{cellFor(col.key)}</div>
                      ))}
                    </div>
                  )
                })}
              </div>
            ) : null}

            {/* 分页（后端 `limit/offset/has_more`；只翻文件那一页） */}
            {filesTotal > FILE_PAGE_SIZE ? (
              <div className="ks-pager">
                <Button
                  variant="outline"
                  size="sm"
                  className="ks-pager-btn"
                  disabled={busy || fileOffset <= 0}
                  title="上一页"
                  onClick={() => { goPage(Math.max(0, fileOffset - FILE_PAGE_SIZE)) }}
                >
                  <IconChevronLeftOutline14 />
                </Button>
                <span className="ks-pager-n">
                  第 {pageNo} / {pageMax} 页 · 共 {filesTotal} 篇
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="ks-pager-btn"
                  disabled={busy || !filesMore}
                  title="下一页"
                  onClick={() => { goPage(fileOffset + FILE_PAGE_SIZE) }}
                >
                  <IconChevronRightOutline14 />
                </Button>
              </div>
            ) : null}
              </>
            )}
          </div>

          {/* 右：详情（点开某一行才出现；**不是**台账第 14 条点名删掉的那张提示卡）。
              ⚠ 只在**目录层**出现：「待分类」层的每一篇要显示的东西（状态/建议/识别率）
                已经在行里了，再挂一张卡只会把窄栏挤掉。 */}
          {layer === 'folder' && current !== null ? (
            <div className="ks-detail">
              <div className="ks-kb-card">
                <div className="ks-kb-row" style={{ marginBottom: 6 }}>
                  <strong className="ks-kb-grow ks-kb-ct" title={current.standard_name ?? current.doc_id}>
                    {current.standard_name ?? current.doc_id}
                  </strong>
                  <span className={STATUS[statusOf(current.legal_status)].cls}>
                    {STATUS[statusOf(current.legal_status)].text}
                  </span>
                </div>
                <div className="ks-fields">
                  <Field label="标准号" value={current.standard_no ?? ''} mono />
                  <Field label="发布日期" value={current.published_at ?? ''} />
                  <Field label="生效日期" value={current.effective_from ?? ''} />
                  <Field label="废止日期" value={current.withdrawn_date ?? ''} />
                  <Field label="被替代为" value={current.superseded_by ?? ''} mono />
                  <Field label="所属目录" value={levelName} />
                  <Field label="处理状态" value={stageText(current.stage, stageLabels)} />
                  <Field
                    label="识别率"
                    value={current.confidence === null ? '' : String(current.confidence)}
                  />
                </div>
                {/* ⚠⚠ **2026-09-22 业主点名删掉这一类**（"这种 AI 味道很重的、也没啥实际功能的描述都去掉"）：
                    这一行原文（留痕）：`这里的每个字都来自库里这一篇的真实字段；没有的字段显示「—」，**不编**。`
                    两处都踩在口径上 —— "来自库里这一篇的真实字段" 是**讲实现/数据来源**，
                    "**不编**" 是**自夸**（而且 `**` 在 JSX 里根本不渲染成粗体，屏幕上就是两颗星，
                    更难看）。上面的字段自己会说话（没有的值显示「—」），不需要这段旁白。 */}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
