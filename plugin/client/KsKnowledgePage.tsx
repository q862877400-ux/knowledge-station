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

import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { Button, IconArchiveOutline20, IconChecklistOutline14, IconChevronDownOutline14, IconChevronLeftOutline14, IconChevronRightOutline14, IconEllipsisOutline16, IconFolderOpenOutline16, IconInfoOutline14, IconListPenOutline16, IconPlusOutline16, IconRefreshOutline16, IconSearchOutline16, IconShieldOutline16, Input, Menu } from '@deepseek-ai/dsh-client-ui-primitives'

import {
  EngineAuthError,
  fetchBulkIngest,
  fetchDocsFlat,
  fetchIngestInboxDefault,
  fetchKbFolderItems,
  fetchKbFolders,
  fetchSession,
  fileDocsIntoFolder,
  resumeBulkIngest,
  startBulkIngest,
  type KsKbFile,
  type KsKbFolder,
} from './api'
import { ensureKsStyles } from './ksGuideStyles'
import { KsCapabilityPage } from './KsCapabilityPage'
import type { KsPaneBodyProps, KsKbInjected } from './ksSidebar'

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
 * 文件**处理状态**的中文标签。
 *
 * ⚠ 标签的**唯一所有者**是 `src/core/knowledge/folder_store.py` 的 `STAGE_LABELS`
 *   （五枚举 `queued/recognizing/confirming/filed/failed` 与 `schema.sql` 的 CHECK 一字不差）。
 *   接口**不下发标签**（`/kb/folders/{id}/items` 只给 `stage` 原值）⇒ 这里是一份**镜像**。
 *   业主 2026-09-21："**所有文件**都要显示处理状态"（方案 §一），第 4 步把它做完整
 *   （失败类型/识别率/重来一次），本批先把这一列**如实**摆出来（值全部来自后端，不编）。
 */
const STAGE_LABELS: Record<string, string> = {
  queued: '排队中',
  recognizing: '识别中',
  confirming: '待确认',
  filed: '已归位',
  failed: '识别失败',
}

function stageText(raw: string | null): string {
  if (raw === null || raw === '') return '—'
  return STAGE_LABELS[raw] ?? raw
}

/** **文件层**的列定义（表头与每一行共用这一份 ⇒ 列身份只有一个所有者）。 */
const COLUMNS = [
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
 * ⚠ 列类名与文件层**不重用**（`ks-col-dname/dcount/dgo`）：两层的行都挂在 `.ks-item` 上，
 *   重用类名会让"列身份"在两层之间串味。
 */
const DIR_COLUMNS = [
  { key: 'dname', cls: 'ks-col-dname', head: '目录' },
  { key: 'dcount', cls: 'ks-col-dcount', head: '篇数' },
  { key: 'dgo', cls: 'ks-col-dgo', head: '' },
] as const

type DirColKey = (typeof DIR_COLUMNS)[number]['key']

/**
 * 行内**文件图标**：从**已有字段 `standard_no`** 推出来的呈现档（没有新字段、没有编数据）：
 *   `''`      → 法律法规（法律/行政法规本来就没有标准号）→ 盾
 *   `GB` 开头 → 国家标准/行业标准                          → 清单
 *   `KS-` 开头 → 公司制度 / 内部规程                        → 文档+笔
 *   其余      → 资料 / 记录                                 → 归档盒
 * ⚠ 四个字形都是宿主的真实导出（逐个在检出 `ui-primitives/lib/index.js` 里核过）；
 *   它是**装饰性**的扫读锚点，类型文字挂在 `title=` 上。
 */
function docGlyph(no: string | null): ReactNode {
  const v = no ?? ''
  if (v === '') return <IconShieldOutline16 />
  if (/^GB/i.test(v)) return <IconChecklistOutline14 />
  if (/^KS-/i.test(v)) return <IconListPenOutline16 />
  return <IconArchiveOutline20 />
}

function docGlyphLabel(no: string | null): string {
  const v = no ?? ''
  if (v === '') return '法律法规 / 无标准号'
  if (/^GB/i.test(v)) return '标准'
  if (/^KS-/i.test(v)) return '公司制度 / 规程'
  return '资料 / 记录'
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

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const sleep = async (ms: number): Promise<void> => new Promise((resolve) => { setTimeout(resolve, ms) })

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
export function KsKnowledgePage({ useTabInfo, dataSource }: KsPaneBodyProps & KsKbInjected): ReactNode {
  ensureKsStyles()
  const { tab } = useTabInfo()
  const page = (tab.navigation.params as { page?: string } | undefined)?.page ?? 'manage'

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

  /** 上传面板。 */
  const [upOpen, setUpOpen] = useState(false)
  const [upDir, setUpDir] = useState('')
  const [upPhase, setUpPhase] = useState<UpPhase>('idle')
  const [upMsg, setUpMsg] = useState('')

  const abortRef = useRef<AbortController | null>(null)

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

  // 挂载即载入最外层（引擎 port/token 每次启动轮换 ⇒ 不缓存跨次会话）。
  useEffect(() => {
    void loadLevel(null, 0)
    return () => { abortRef.current?.abort() }
  }, [loadLevel])

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
    setLevelId(id)
    setSearch('')
    setOpenDoc(null)
    setMenuFor(null)
    void loadLevel(id, 0)
  }, [loadLevel])

  /** 返回上一层（最外层没有上一层 ⇒ 按钮置灰，见渲染）。 */
  const goUp = useCallback((): void => {
    if (levelId === null) return
    const parent = crumb.length >= 2 ? crumb[crumb.length - 2] : null
    goto(parent === null ? null : parent.folder_id)
  }, [crumb, goto, levelId])

  /** 翻到文件的另一页（只重拉文件那一页，不动目录层）。 */
  const goPage = useCallback((offset: number): void => {
    if (offset < 0) return
    void loadLevel(levelId, offset, { silent: true })
  }, [levelId, loadLevel])

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
   *   这是现有接口下**唯一**能算出"这一批新增了哪些"的办法；换更省的路需要后端加参数（本批不许改）。
   */
  const runUpload = useCallback(async (): Promise<void> => {
    const dir = upDir.trim()
    if (dir === '' || upPhase === 'running') return
    setUpPhase('running')
    setUpMsg('正在读取导入前的库快照…')
    try {
      const before = await withSession((port, token) => fetchDocsFlat(port, token))
      const beforeIds = new Set(before.map((d) => d.doc_id))
      const started = await withSession((port, token) => startBulkIngest(port, token, dir))
      await withSession((port, token) => resumeBulkIngest(port, token, started.batch_id))
      setUpMsg(`批次 ${started.batch_id} 已开始（共 ${started.total} 个文件），等待解析…`)
      let last = started.total
      let parsed = 0
      for (let i = 0; i < 300; i += 1) {
        await sleep(2000)
        const st = await withSession((port, token) => fetchBulkIngest(port, token, started.batch_id))
        last = st.total
        parsed = st.parsed
        setUpMsg(`已解析 ${parsed} / ${last} 篇${st.errors > 0 ? `（失败 ${st.errors}）` : ''}…`)
        if (st.status !== 'running' && st.status !== 'pending') break
        if (st.pending === 0 && st.scanned >= st.total && st.total > 0) break
      }
      const after = await withSession((port, token) => fetchDocsFlat(port, token))
      const fresh = after.filter((d) => !beforeIds.has(d.doc_id)).map((d) => d.doc_id)
      if (fresh.length === 0) {
        setUpPhase('done')
        setUpMsg(`这一批没有新增文件（共看了 ${last} 个，已解析 ${parsed} 个；库里已有的不会重复进）。`)
        return
      }
      if (levelId !== null) {
        const res = await withSession((port, token) =>
          fileDocsIntoFolder(port, token, levelId, fresh))
        setUpMsg(`导入完成：新入库 ${fresh.length} 篇，已放进「${levelName}」${res.confirmed} 篇`
          + `（从「待分类」拿掉 ${res.removed_from_pending} 篇）。`)
      } else {
        setUpMsg(`导入完成：新入库 ${fresh.length} 篇。你现在停在**最外层** ⇒ 它们留在最外层`
          + `（还没归位，会出现在「待分类」里；进一个目录再上传才会直接落进那个目录）。`)
      }
      setUpPhase('done')
      await loadLevel(levelId, 0, { silent: true })
    } catch (error) {
      setUpPhase('error')
      setUpMsg(`导入失败：${errorText(error)}`)
    }
  }, [levelId, levelName, loadLevel, upDir, upPhase, withSession])

  // ── 「能力」页有自己的组件（业主指定的"一功能一卡一窗"） ──
  if (page === 'capabilities') {
    return <KsCapabilityPage />
  }

  // ── 其余非「知识库管理」页：诚实的占位（真入口，空内容） ──
  if (page !== 'manage') {
    const LABELS: Record<string, string> = { ingest: '文件导入', report: '效力报告', channels: '渠道台账' }
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
   * 本页只有**一处**渲染点：右栏当前这一级的条目区上方（**每层都在同一位置**）。
   * placebo 随层级不变（它同时过滤目录名与文件名，见 `needle` 的注释）。
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

  /** 左列树的一行（递归渲染；**点名字 = 进这一级，点箭头 = 展开/收起**）。 */
  const renderTreeRow = (
    key: string, name: string, count: number | null, depth: number, isCurrent: boolean,
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

  const rootKids = tree.root?.kids ?? []

  return (
    // ⚠ 外面这一层 `.ks-page` **只做 container-type**（页面留边的宽/窄两档靠它切 ⇒ 留边落在 `.ks-kb`）。
    <div className="ks-page">
      <div className="ks-kb">
        <header className="ks-page-head">
          <div className="ks-page-title">知识库</div>
          <div className="ks-page-sub">
            法规/标准的落点：知识库 → 目录 → 条款；颜色一律走宿主主题 token，深浅色自动跟随
          </div>
        </header>
        <div className="ks-page-rule" />

        {/* 诚实告知条：这一页**现在接的是真库**（不再是占位）。文案只说事实，
            细则（接口名/边界）挂在 title= 里，正文不堆黑话。 */}
        <div
          className="ks-kb-banner"
          title={'数据来自本机知识库引擎（/api/v1/kb/*）。左边一列是目录，右边只显示“当前这一层”；'
            + '每一级都能上传，上传进某一级就落在那一级（不再进自动识别）。'
            + `dataSource=${dataSource}`}
        >
          <IconInfoOutline14 />
          <strong>真库：左边目录、右边当前这一层</strong>
        </div>

        {/* 顶上一行：返回上一层 + 逐级可点的路径 + 上传/刷新 */}
        <div className="ks-kb-row">
          <Button
            variant="outline"
            size="sm"
            className="ks-back"
            disabled={levelId === null}
            title={levelId === null
              ? '你已经是最外层，没有上一级可回'
              : `回到上一层（现在在：${['知识库', ...crumb.map((f) => f.name)].join(' / ')}）`}
            onClick={goUp}
          >
            <IconChevronLeftOutline14 />
            返回上一层
          </Button>
          <span
            className="ks-crumb"
            title={`当前路径：${['知识库', ...crumb.map((f) => f.name)].join(' / ')}`}
          >
            <span className="ks-crumb-path">
              <span className="ks-crumb-item">
                {levelId === null ? (
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
              {crumb.map((node, i) => {
                const here = i === crumb.length - 1
                return (
                  <span className="ks-crumb-item" key={node.folder_id}>
                    <span className="ks-crumb-sep" aria-hidden="true">/</span>
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
                )
              })}
            </span>
            {/* 顶层**如实说**"你在最外层"（需求 3）；在目录里则报这一级的条目数。 */}
            <span className="ks-crumb-n">
              {levelId === null
                ? '你在最外层'
                : `${subs.length} 个子目录 · ${filesTotal} 篇文件`}
            </span>
          </span>
          <div className="ks-kb-grow" />
          <Button
            variant="outline"
            size="sm"
            className="ks-upload-open"
            aria-expanded={upOpen}
            title={levelId === null
              ? '把「来源目录」里的文件导入知识库（你现在在最外层 ⇒ 它们会留在最外层，还没归位）'
              : `把「来源目录」里的文件导入并直接放进「${levelName}」`}
            onClick={() => { void openUpload() }}
          >
            <IconPlusOutline16 />
            上传到这一层
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="ks-refresh"
            title="重新读取当前这一级"
            onClick={() => { void loadLevel(levelId, fileOffset, { silent: true }) }}
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
                title={levelId === null
                  ? '导入这些文件；你在最外层 ⇒ 它们会留在最外层（会出现在「待分类」里）'
                  : `导入这些文件并直接放进「${levelName}」（不进自动识别）`}
                onClick={() => { void runUpload() }}
              >
                {upPhase === 'running' ? '导入中…' : '导入到这一层'}
              </Button>
            </div>
            <div className="ks-upload-note">
              {levelId === null
                ? '你在最外层：导入的文件会留在最外层（还没归位，会出现在「待分类」里）。'
                : `导入完成后，新文件会直接放进「${levelName}」，不会进自动识别。`}
              {' '}扫描件/大文件解析要等一会儿，下面的进度说的是库里真的解析了多少篇。
            </div>
            {upMsg === '' ? null : (
              <div className={upPhase === 'error' ? 'ks-upload-msg ks-upload-msg-bad' : 'ks-upload-msg'}>
                {upMsg}
              </div>
            )}
          </div>
        ) : null}

        {phase === 'error' ? (
          <div className="ks-kb-err" role="alert">
            <strong>读不到知识库</strong>
            <span className="ks-kb-hint">{errMsg}</span>
            <Button variant="outline" size="sm" onClick={() => { void loadLevel(levelId, 0) }}>重试</Button>
          </div>
        ) : null}

        <div className="ks-split">
          {/* ══ 左列：真目录树（按需展开，一次只拉一层） ══ */}
          <div className="ks-kb-tree">
            <div className="ks-tree-head">目录</div>
            <div className="ks-tree-body">
              {renderTreeRow('root', '最外层', null, 0, levelId === null)}
              {treeOpen.has('root') ? rootKids.map((kid) => renderTreeRow(
                kid.folder_id, kid.name, kid.file_count_deep, 1, kid.folder_id === levelId)) : null}
              {tree.root?.loading === true ? <div className="ks-tree-hint">正在读取…</div> : null}
            </div>
          </div>

          {/* ══ 右栏：**只显示当前这一级**（下级目录在前、这一级直接放的文件在后；顺序照后端给的） ══ */}
          <div className="ks-main">
            <div className="ks-list-cap">
              <span className="ks-lhead-name ks-kb-grow" title={['知识库', ...crumb.map((f) => f.name)].join(' / ')}>
                {levelName}
              </span>
              <span className="ks-kb-hint">
                {subs.length} 个子目录 · {filesTotal} 篇文件
                {needle === '' ? '' : `（本页筛出 ${dirsShown.length} 个目录 / ${filesShown.length} 篇）`}
              </span>
            </div>

            {searchBox}

            {/* 目录层：**与文件列表同构**的列表（同一套 .ks-list/.ks-lhead/.ks-item 机制，
                只换一份列定义 DIR_COLUMNS 与一条自己的 --ks-cols）。 */}
            {subs.length > 0 || dirsShown.length > 0 ? (
              <div className="ks-list ks-list-dirs ks-dirs">
                <div className="ks-lhead">
                  {DIR_COLUMNS.map((col) => (
                    <div className={`ks-cell ${col.cls}`} key={col.key}>
                      {col.head === '' ? null : <span className="ks-lhead-col">{col.head}</span>}
                    </div>
                  ))}
                </div>
                {dirsShown.map((child) => {
                  const dirCell = (key: DirColKey): ReactNode => {
                    switch (key) {
                      case 'dname':
                        return (
                          <>
                            <span className="ks-fileico" title="目录"><IconFolderOpenOutline16 /></span>
                            <span className="ks-dir-name" title={child.name}>{child.name}</span>
                          </>
                        )
                      case 'dcount':
                        // ⚠ 「篇数」= 这一**棵**下的篇数（后端 `file_count_deep`，含更深层）
                        return <span className="ks-kb-badge">{child.file_count_deep} 篇</span>
                      case 'dgo':
                        return <span className="ks-dir-go"><IconChevronRightOutline14 /></span>
                    }
                  }
                  return (
                    <button
                      key={child.folder_id}
                      type="button"
                      className="ks-item ks-dir-row"
                      title={`进入「${child.name}」（这一棵目录下共 ${child.file_count_deep} 篇）`}
                      aria-label={`进入目录「${child.name}」，这一棵目录下共 ${child.file_count_deep} 篇`}
                      onClick={() => { goto(child.folder_id) }}
                    >
                      {DIR_COLUMNS.map((col) => (
                        <div className={`ks-cell ${col.cls}`} key={col.key}>{dirCell(col.key)}</div>
                      ))}
                    </button>
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
                <div className="ks-lhead">
                  {COLUMNS.map((col) => (
                    <div className={`ks-cell ${col.cls}`} key={col.key}>
                      {col.head === '' ? null : <span className="ks-lhead-col">{col.head}</span>}
                    </div>
                  ))}
                </div>
                {filesShown.map((doc) => {
                  const st = STATUS[statusOf(doc.legal_status)]
                  const isOpen = menuFor === doc.doc_id
                  const cellFor = (key: ColKey): ReactNode => {
                    switch (key) {
                      case 'name':
                        return (
                          <>
                            <span className="ks-fileico" title={docGlyphLabel(doc.standard_no)}>
                              {docGlyph(doc.standard_no)}
                            </span>
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
                              items={[{ id: 'detail', label: '详情' }]}
                              onClose={() => { setMenuFor(null) }}
                              onSelect={(id) => {
                                setMenuFor(null)
                                if (id === 'detail') setOpenDoc(openDoc === doc.doc_id ? null : doc.doc_id)
                              }}
                              anchor={(
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  aria-haspopup="menu"
                                  aria-expanded={isOpen}
                                  aria-label={`${doc.standard_name ?? doc.doc_id} 的更多操作`}
                                  title="更多操作（详情）"
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
          </div>

          {/* 右：详情（点开某一行才出现；**不是**台账第 14 条点名删掉的那张提示卡）。 */}
          {current !== null ? (
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
                  <Field label="处理状态" value={stageText(current.stage)} />
                  <Field
                    label="识别率"
                    value={current.confidence === null ? '' : String(current.confidence)}
                  />
                </div>
                <div className="ks-kb-hint" style={{ marginTop: 6 }}>
                  这里的每个字都来自库里这一篇的真实字段；没有的字段显示「—」，**不编**。
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
