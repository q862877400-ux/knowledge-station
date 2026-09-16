/**
 * ks-dsh-plugin — client/KsEvidenceTab.tsx
 *
 * The ks:pdf tab. Renders the engine's evidence PDF page and draws the
 * citation bbox (if any) as a yellow rectangle. Given a TabComponentProps:
 *   - `tab.path`    = the clicked /__ks_evidence__ href (landed by the
 *                     better-sidebar builtin openTab({ type, url, title }));
 *                     OR
 *   - `tab.meta`    = a pre-decoded { doc, page, bbox, rev } if openTab is
 *                     called directly with meta.
 *
 * State machine: loading -> ready | error. Always re-fetches /ks/session on
 * every (re)load because the engine port + token rotate per start.
 *
 * The render environment here is a real React tree (built-in tab components
 * such as BrowserView use hooks), so hooks are safe.
 */

import * as React from 'react'
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import * as pdfjs from 'pdfjs-dist'
import { createPortal } from 'react-dom'
import type { PDFDocumentProxy } from 'pdfjs-dist'

import type { KsEvidenceProps } from './ks-evidence-props'
import {
  EngineAuthError,
  addBookmark,
  addDocBookmark,
  clearSession,
  createBookmarkFolder,
  fetchBbox,
  fetchBookmarkFolders,
  fetchBookmarks,
  fetchClauseMeta,
  fetchDocTree,
  fetchPdf,
  fetchSession,
  removeBookmarkByClauseKey,
  removeDocBookmarkByDoc,
  type KsBookmark,
  type KsBookmarkFolder,
  type KsClause,
} from './api'
import { configurePdfWorker, PDF_WASM_DIR } from './pdf-configure'
import {
  backingStoreDpr,
  continuousViewportHeight,
  fitPageScale,
  MANUAL_MAX_PERCENT,
  MANUAL_MIN_PERCENT,
  PAGE_PADDING,
  ZOOM_PRESET_PERCENTS,
  zoomForAutoFit,
  zoomForManual,
  zoomScale,
  type ZoomState,
} from './pdfFit'
import {
  restorePanelAfterPdf,
  TOC_COLUMN_WIDTH,
  widenPanelForPdf,
} from './pdfPanel'
import { KsFilesView } from './KsFilesTab'
import { KsBookmarksView, type KsBookmarkJump } from './KsBookmarksTab'
import { KsDocTextView } from './KsDocTextView'
import {
  evidenceUrlOf,
  parseEvidence,
  type KsEvidence,
} from './ksEvidence'

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; pages: number }
  | { status: 'error'; message: string }

/** One "recently opened evidence" record in the in-tab history. */
interface HistoryEntry {
  /** The href used to (re)open this evidence; always non-null for a valid ev. */
  url: string
  /** The parsed evidence — `page` here is the page actually rendered. */
  ev: KsEvidence
}

const EMPTY_EVIDENCE: KsEvidence | null = null
/** 上限：保留最近打开的 ~20 条证据。 */
const HISTORY_CAP = 20
/**
 * 抖动抑制死区（相对缩放变化）：同一页缩放变化小于它就不重绘。
 * 与 SCROLLBAR_NOISE_PX 配合，双重保证"滚动条 → 重绘 → 滚动条"不会自激。
 */
const SCALE_EPSILON = 0.03
/** 滚动条噪声死区（px）：小于它的容器尺寸变化一律视为滚动条出现/消失。 */
const SCROLLBAR_NOISE_PX = 20
/**
 * 无过渡时的兜底测量延迟（ms）。真正的延迟由 `readSlowTransitionMs()` 运行时从
 * `--ds-transition-duration-slow` 读出（verifier P1-4：该 token 是可被主题/Skin
 * 覆盖的，写死 360 会在主题调大时长后失效——定时器抢在动画中途到点，原 bug 回归）。
 */
const DEFAULT_SETTLE_MS = 360
/** 窗口 resize / 最大化 / 浏览器缩放：没有 CSS 宽度过渡与之竞争，用短档保响应。 */
const RESIZE_SETTLE_MS = 120
/**
 * 连续（瀑布）模式下"提前绘制"的上下余量（px）：可视区上下各预留这么多，
 * 滚动时页面已经在旁边画好了，而不是滚到才开始解码。
 */
const CONTINUOUS_MARGIN_PX = 400

/** 读 `--ds-transition-duration-slow`（兼容 `0.3s` / `300ms`）；读不到回退 300。 */
function readSlowTransitionMs(): number {
  if (typeof window === 'undefined' || typeof document === 'undefined') return 300
  try {
    const raw = window.getComputedStyle(document.documentElement)
      .getPropertyValue('--ds-transition-duration-slow').trim()
    const n = raw.endsWith('ms') ? parseFloat(raw)
      : raw.endsWith('s') ? parseFloat(raw) * 1000
        : NaN
    return Number.isFinite(n) && n > 0 ? Math.round(n) : 300
  } catch {
    return 300
  }
}


export function KsEvidenceTab(props: KsEvidenceProps): JSX.Element {
  const { tab, visible, scope, prefs, panel, onUpdateTitle, onOpenEvidence, tabOpen } = props
  /** 侧栏宽度让位/恢复按会话记账（见 pdfPanel.ts）。 */
  const sessionId = scope?.sessionId

  // 「法规标准知识库」设置：是否显示红箭头。官方右侧栏无共享 side-card prefs
  // （旧模型读 `pluginSettings['ks:settings']`），改由宿主以 props 注入；
  // 省略时缺省开（与旧行为一致）。
  const showArrowPref = prefs?.showArrow !== false
  // 供 useCallback([]) 的 renderPage 读取（闭包锁首值问题 → 用 ref 存当前偏好）
  const showArrowRef = useRef<boolean>(true)
  showArrowRef.current = showArrowPref

  // 面板当前宽度（CSS px）：目录列经 portal 固定在"面板左缘向左"的位置。
  // 官方右侧栏不提供宽度面 → `panel` 省略时为 0（目录列退化为悬浮覆盖，
  // 与旧行为"store 不可读"分支一致）。
  const panelWidth = panel?.getWidth() ?? 0

  const evidence = useRef<KsEvidence | null>(EMPTY_EVIDENCE)
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const bboxRef = useRef<HTMLDivElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  /**
   * 每页各自的 RenderTask（连续模式必需）：单 canvas 时代用一个共享的 ref
   * "先取消上一帧"是对的，但连续模式**多页并发渲染**——共享它会让第 2 页把第 1 页
   * 的渲染取消掉，两页都画不出来（表现为空白页）。
   * 所以取消只针对"这一页自己上一帧"。
   */
  const tasksByPageRef = useRef<Map<number, pdfjs.RenderTask>>(new Map())
  /**
   * 文档世代号：**只在换文档 / 重载时**递增。异步帧回来后若世代不符，说明它属于
   * 上一份文档，必须丢弃（否则旧文档的页会画进新文档的 canvas）。
   *
   * 刻意**不用**它做页间互斥：连续模式多页并发绘制，任何"又开了一帧"式的全局递增
   * 都会让相邻页互相作废（两页一起白屏）。页内的过期判断见 pageTokenRef。
   */
  const docEpochRef = useRef(0)
  /** 每页的绘制令牌：同一页的新一帧会把旧帧作废（换页/缩放/尺寸连续变化时）。 */
  const pageTokenRef = useRef<Map<number, number>>(new Map())
  /** 单调递增的令牌发号器。 */
  const tokenSeqRef = useRef(0)

  /**
   * 最近一次**成功**绘制所用的 (页, 缩放, dpr)——用于抖动抑制。
   * 连续模式是多 canvas（每页一个），故按页号分别记账。
   */
  const lastFitRef = useRef<Map<number, { scale: number; dpr: number }>>(new Map())
  // ---- 连续（瀑布）模式的多 canvas 记账（2026-09-16）----
  /** 页号 → 该页的 canvas 元素（连续模式下由 ref 回调登记）。 */
  const pageCanvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map())
  /** 当前**已提交渲染**的页号序列（1..N）；单页模式只含当前页。 */
  const pageOrderRef = useRef<number[]>([])
  /**
   * 已取消的页号：这些页的 canvas 可能带着半张旧图。重新进入可视区时必须**强制**
   * 重绘（否则缩放死区会把重绘吃掉，留下半张页）。
   */
  const cancelledPagesRef = useRef<Set<number>>(new Set())
  /** 当前在（接近）可视区内的页号——只有这些页才画，滚动进出即增删。 */
  const visiblePagesRef = useRef<Set<number>>(new Set())
  /** 连续模式的绘制签名（页序|缩放|dpr|尺寸）：变了才重画全部可见页。 */
  const paintSigRef = useRef<string>('')
  /**
   * 当前缩放状态的 ref 镜像：renderPage 是 useCallback（按依赖重建），而绘制
   * 常常由"滚动/尺寸"这类绕过 React 的路径触发，读 ref 才不会拿到旧闭包。
   */
  const zoomRef = useRef<ZoomState>({ source: 'autoFit' })
  /** 单页 → 连续切换时要滚进视野的目标页（交接给滚动 effect；null = 无需滚动）。 */
  const pendingScrollPageRef = useRef<number | null>(null)
  /**
   * 文档第 1 页在 scale=1 下的原始尺寸（pt）：只喂给底部栏的百分比回显（autoFit
   * 下要算"自适应 = 多少 %"）。真正的绘制用每页自己的尺寸，不看这个值。
   */
  const firstPageBaseSizeRef = useRef<{ width: number; height: number } | null>(null)
  /** 几何冻结截止时间（ms epoch）：我们自己发起的布局动画期间不重绘。 */
  const renderFreezeUntilRef = useRef(0)
  /** 冻结期间是否发生过"想重绘"——冻结结束后补测一次。 */
  const pendingRenderRef = useRef(false)
  const freezeTimerRef = useRef<number | null>(null)
  /** 增强③-B: 去重历史 + 当前载入的原始 href（parse 前存的）。 */
  const historyRef = useRef<HistoryEntry[]>([])
  const pathHrefRef = useRef<string | null>(null)

  const [load, setLoad] = useState<LoadState>({ status: 'idle' })
  const [page, setPage] = useState<number>(1)
  const [pageInput, setPageInput] = useState<string>('1')
  const [engineHint, setEngineHint] = useState<string>('')
  // 已收藏条款下拉选择状态（'' = 未选；onChange 跳转后复位）
  const [selBm, setSelBm] = useState<string>('')
  const [selHistory, setSelHistory] = useState<string>('')
  // 条款收藏（箭头下按钮）：idle/busy/done（done=本会话已收藏该条款）
  const [bmState, setBmState] = useState<'idle' | 'busy' | 'done'>('idle')
  // 标准收藏（顶部按钮）：false=未收藏, true=已收藏；busyDoc=请求中
  const [docBookmarked, setDocBookmarked] = useState<boolean>(false)
  const [docBusy, setDocBusy] = useState<boolean>(false)
  // 当前条款的 doc_id（meta 取回后填充，顶部按钮需要）
  const [curDocId, setCurDocId] = useState<string | null>(null)
  // 当前条款的 clause_key（取消收藏 toggle 需要）
  const [curClauseKey, setCurClauseKey] = useState<string | null>(null)
  // 箭头锚行几何（条款收藏小按钮据此贴在行首左缘外侧；null=无箭头隐藏）
  const [arrowPos, setArrowPos] = useState<{
    rowLeft: number
    arrowLeft: number
    top: number
    height: number
  } | null>(null)
  // refreshMeta 的引用（loadEvidence 在函数定义前调用它）
  const refreshMetaRef = useRef<((rev: string) => void) | null>(null)
  // 本文档已收藏条款（顶部「已收藏条款」下拉数据源）
  const [docClauseBms, setDocClauseBms] = useState<KsBookmark[]>([])
  // 标题目录（B）：已载入文档的目录树 + 列可见性。
  const [loadedDocId, setLoadedDocId] = useState<string | null>(null)
  const [toc, setToc] = useState<KsClause[] | null>(null) // null=加载中; []=空树(隐藏列)
  // 标题目录列默认**收起**（用户 2026-09-09：默认收起，把宽度让给 PDF 阅读器）。
  // 用户在本次 tab 生命周期内手动展开后不再被换文档重置——切证据时保留选择。
  const [tocOpen, setTocOpen] = useState<boolean>(false)   // 收起 → 纯 PDF 全宽
  // （2026-09-10 决定性简化）：目录列不再"顶开侧栏"——改面板宽度要跟上游
  // .panel 的 300ms CSS 过渡做像素级锁步，四轮都没能根除黑闪。现改为**纯悬浮
  // overlay**：绝对定位浮在 PDF 左缘之上，用 transform 滑入/滑出。目录列开合
  // 完全不改变 PDF 的布局尺寸 → 不可能再黑/闪/动。侧栏宽度只在"打开文档让位"时改。
  const tocAbortRef = useRef<AbortController | null>(null)
  // 左列视图模式：'toc'=标题目录（默认） / 'files'=文件目录（库浏览，同列切换）
  // / 'bookmarks'=收藏目录（2026-10：夹树 + 💡夹内提问，同列第三模式）
  const [leftMode, setLeftMode] = useState<'toc' | 'files' | 'bookmarks'>('toc')
  // 目录常驻（2026-10-27）：无证据直开 tab → 左列默认落在文件目录（可切收藏目录）。
  // 只在「本 tab 从未有过证据」时引导一次；用户手动切过模式（或已有文档）不覆盖。
  const leftModeTouchedRef = useRef(false)
  // 目录统一搜索（2026-10-28 四宫格）：一个搜索词作用于当前目录模式——
  // 文件目录过滤分类树、收藏目录过滤夹树、标题目录过滤章/小节。
  const [dirQuery, setDirQuery] = useState('')
  // 搜索输入框是否展开（🔍 搜索按钮切换；收起时清词）。
  const [searchOpen, setSearchOpen] = useState(false)
  // 正文视图（2026-09-13 端点接线）：'pdf'=canvas 原样（默认） / 'text'=条款富文本
  // （content_html + fig-embed/table-embed/katex-formula 占位经 /ks/doc-image 接线）。
  // 换文档时回到 PDF 视图（正文按需再开）。
  const [viewMode, setViewMode] = useState<'pdf' | 'text'>('pdf')

  // ---- 翻页模式 + 缩放来源（2026-09-16 用户需求，底部常驻栏）----
  /**
   * 翻页模式：'continuous' = **瀑布式**（滚动连续浏览多页，**打开即默认**）；
   * 'single' = 单页（一次只画一页）。两者互斥。
   *
   * 与下面的 zoom 是**两个独立状态**（用户 2026-09-16 明确要求不要混成一个）：
   * 单页也能量手动缩放，连续也能自适应。
   */
  const [pagingMode, setPagingMode] = useState<'continuous' | 'single'>('continuous')
  /**
   * 缩放来源状态机（纯函数在 pdfFit.ts，离线可测）：
   *   { source:'autoFit' }            = 自适应窗口（默认）——跟容器走；
   *   { source:'manual', percent }    = 手选百分比/拖过滑块——**不再**跟容器走，
   *                                     只有再点「自适应窗口」才恢复。
   */
  const [zoom, setZoom] = useState<ZoomState>({ source: 'autoFit' })
  /** 「浏览比例」下拉是否展开（**向上**弹出，见 bottomBar 的浮层）。 */
  const [zoomMenuOpen, setZoomMenuOpen] = useState(false)
  /** 下拉锚点矩形（视口坐标）：按钮位置一变就重算，null = 未展开。 */
  const [zoomAnchor, setZoomAnchor] = useState<{
    left: number
    bottom: number
    width: number
  } | null>(null)

  // ---- 收藏夹选夹（2026-10 收藏目录）----
  // 收藏时若已有收藏夹 → 弹出选夹菜单（现有夹 / 新建 / 未分类）；
  // 还没有任何夹 → 一键直收（不弹菜单，收藏回未分类，用户建夹后可在收藏目录里移动）。
  // picker 为 null = 关闭；'doc' = 标准收藏选夹；'clause' = 条款收藏选夹。
  const [folderPicker, setFolderPicker] = useState<'doc' | 'clause' | null>(null)
  // 夹列表（点击收藏那一刻懒加载；成功收藏后下次点击重拉）。
  const [folderList, setFolderList] = useState<KsBookmarkFolder[] | null>(null)
  const [folderLoading, setFolderLoading] = useState(false)
  // 选夹菜单里的「新建夹」内联输入（空串 = 未启用）。
  const [folderNewName, setFolderNewName] = useState('')
  // clause 选夹前的 pending clause_key（菜单确认后才发 POST）。
  const pendingClauseKeyRef = useRef<string | null>(null)
  // 选夹确认后 refreshMeta 需要的 clause_revision_id（存 pending 期间的 rev）。
  const pendingRevRef = useRef<string | null>(null)

  /**
   * Render one page of the loaded PDF into an explicit canvas（单页 = 唯一那块；
   * 连续 = 该页自己那块），缩放取自底部栏的缩放状态机（zoomScale），并 overlay
   * 该页的 bbox（若有）为红箭头。尺寸每次都现读容器（不用缓存值），窗口最大化/
   * 侧栏拖宽/浏览器缩放都通过下方测量 effect 触发重绘。
   *
   * @param opts.force  绕过"同页同缩放跳过"的死区（缩放/尺寸/DPI 真变了时用）
   * @param opts.bbox   是否画红箭头 + 回填 arrowPos（只有单页模式需要；连续模式
   *                    下多页共享一个 arrowPos 状态会互相覆盖，故不画）
   */
  const renderPage = useCallback(async (
    doc: PDFDocumentProxy,
    target: number,
    canvasArg?: HTMLCanvasElement | null,
    opts?: { force?: boolean; bbox?: boolean },
  ) => {
    const canvas = canvasArg ?? canvasRef.current
    const container = containerRef.current
    if (canvas === undefined || canvas === null || container === null) return
    const ctx = canvas.getContext('2d')
    if (ctx === null) return

    const clamped = Math.max(1, Math.min(target, doc.numPages))

    // 同一 canvas 上并发 render 会抛 "Cannot use the same canvas during multiple
    // render() operations"（翻页快连点 + 尺寸变化同时发生时必现）。取消**这一页**
    // 自己的上一帧即可——连续模式各页并发渲染，共享一个任务槽会互相取消（见
    // tasksByPageRef 注释）。
    const previous = tasksByPageRef.current.get(clamped)
    if (previous !== undefined) {
      try { previous.cancel() } catch { /* ignore */ }
      tasksByPageRef.current.delete(clamped)
    }
    // 本帧的身份：文档世代（换文档即失效）+ 本页令牌（同页更新的一帧把我作废）。
    const epoch = docEpochRef.current
    const token = ++tokenSeqRef.current
    pageTokenRef.current.set(clamped, token)

    const pdfPage = await doc.getPage(clamped)
    // 过期帧自行退出：换过文档，或同一页又有更新的一帧开画了。
    if (epoch !== docEpochRef.current || pageTokenRef.current.get(clamped) !== token) return

    // 缩放：底部栏的缩放状态机（pdfFit.zoomScale）。autoFit 走既有「铺满 + 溢出
    // 预算」；manual 直接用用户选的百分比，**不看容器尺寸**（窗口拉伸不改缩放）。
    // 连续模式把"逻辑可视高"抬高（continuousViewportHeight），让同一套规则退化成
    // 宽度适配——堆叠多页时不该由可视高给单页定标（见 pdfFit.ts 注释）。
    const base = pdfPage.getViewport({ scale: 1 })
    const availWidth = container.clientWidth - PAGE_PADDING
    const availHeight = pagingMode === 'single'
      ? container.clientHeight - PAGE_PADDING
      : continuousViewportHeight(availWidth)
    const view = zoomScale(zoomRef.current, {
      availWidth,
      availHeight,
      pageWidth: base.width,
      pageHeight: base.height,
    })
    // 容器还没布局（tab 隐藏 / 0 尺寸）→ 本次不画，等测量 effect 重触发。
    // 手动缩放有确定值，不受此限（zoomScale 在 manual 下恒有值）。
    if (view.source === 'autoFit' && view.basis === null) return
    const viewport = pdfPage.getViewport({ scale: view.scale })
    const dpr = backingStoreDpr(
      viewport.width, viewport.height,
      typeof window !== 'undefined' ? window.devicePixelRatio : 1,
    )

    const last = lastFitRef.current.get(clamped)

    // 几何冻结（用户 2026-09-09：「目录弹出的时候 PDF 界面会黑一下」）：
    // canvas 的尺寸赋值会**先把画布清空**，真重绘要几十到几百毫秒——所以只要在
    // 我们自己发起的几何动画（目录列 0↔190、面板 ±190 的 0.3s 过渡）期间发生了
    // 一次重绘，用户就会先看到一块黑底再看到页面。而 0/190 与 ±190 两段过渡
    // 即便同参同帧启动，采样点落在动画中段时容器仍可能瞬时差出 190px（比例 >3%
    // 会穿透下面的死区）。故：动画期间**只标记待办、不重绘**，冻结结束后补测一次
    // ——尺寸真变了才画，没变就什么都不做（这才是"无感"）。
    if (Date.now() < renderFreezeUntilRef.current && last !== undefined) {
      pendingRenderRef.current = true
      return
    }

    // 抖动抑制：同页 + 同 dpr + 缩放变化 < 3% → 跳过重绘。滚动条出现/消失会改变
    // clientWidth/Height，在"页面刚好略超容器"的边界上会自激成无限重绘循环；
    // 测量侧的 SCROLLBAR_NOISE_PX 已挡住主要来源，这里是第二道闸。
    // dpr 不同则必须重绘——否则跨屏/缩放后 canvas 停在旧 dpr 上（发糊），
    // 而这种情况尺度往往没变，会被缩放死区误吞。
    // force：缩放/尺寸/DPI 明确变了（或该页曾被取消渲染）时绕过死区。
    if (opts?.force !== true && last !== undefined && last.dpr === dpr
      && Math.abs(view.scale - last.scale) / last.scale < SCALE_EPSILON) {
      return
    }

    canvas.width = Math.floor(viewport.width * dpr)
    canvas.height = Math.floor(viewport.height * dpr)
    canvas.style.width = `${Math.floor(viewport.width)}px`
    canvas.style.height = `${Math.floor(viewport.height)}px`

    const renderContext = {
      canvas,
      canvasContext: ctx,
      viewport,
      // pdfjs 类型 transform 为 any[]|undefined（不收 null）；undefined 与
      // 运行时默认值 transform=null 等价（pdf.mjs 解构默认），dpr=1 时省略。
      transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
    }
    const task = pdfPage.render(renderContext)
    tasksByPageRef.current.set(clamped, task)
    try {
      await task.promise
    } catch (error) {
      // 被下一次绘制取消 = 正常路径（不是错误），静默返回。本页的 canvas 此刻
      // 停在半张图上 → 记入 cancelledPages，下次进入可视区强制重画。
      if (error instanceof Error && error.name === 'RenderingCancelledException') {
        cancelledPagesRef.current.add(clamped)
        return
      }
      // 渲染真失败：canvas 已被上面的尺寸赋值清空，必须让后续同尺寸重试能进来
      // （否则死区会把重试也吃掉 → 永久空白），并把失败暴露到界面上。
      lastFitRef.current.delete(clamped)
      cancelledPagesRef.current.add(clamped)
      setEngineHint(`渲染失败：${error instanceof Error ? error.message : String(error)}（可切页/重试）`)
      throw error
    } finally {
      // 只有仍指向本帧时才摘（否则会把新一帧的登记删掉）。
      if (tasksByPageRef.current.get(clamped) === task) {
        tasksByPageRef.current.delete(clamped)
      }
    }
    // 本帧已被更新的请求取代 → 不要记录缩放、也不要画箭头（否则旧帧的
    // setArrowPos 会覆盖新帧的箭头位置）。
    if (epoch !== docEpochRef.current || pageTokenRef.current.get(clamped) !== token) return
    // 只在**成功**绘制后记录，这样被取消的那一帧不会污染抖动抑制的死区。
    lastFitRef.current.set(clamped, { scale: view.scale, dpr })
    cancelledPagesRef.current.delete(clamped)

    // Draw the red arrow marker at the anchor row's left edge (CSS-pixel
    // space, aligned with the canvas box). The arrow points right INTO the
    // cited row and is about one text line tall. Shown only when the rendered
    // page is the evidence's target page.
    // 连续模式下多页共享同一个 arrowPos 状态会互相覆盖 → 只有单页模式画箭头。
    if (opts?.bbox === false) return
    const box = bboxRef.current
    if (box !== null) {
      const anchor = evidence.current?.bbox
      const onPage = evidence.current?.page === undefined || evidence.current.page === clamped
      // 设置项「显示红色定位箭头」关闭 → 不画箭头也不出收藏按钮（仅跳页）。
      if (anchor !== undefined && onPage && showArrowRef.current) {
        const [bx0, by0, bx1, by1] = anchor
        // FIX(verifier 定案 2026-09-05)：convertToViewPoint 是 pdfjs 上不存在
        // 的方法名 → 运行时 TypeError 被 render effect 的 .catch 吞掉 → 箭头
        // 永不绘制（黄框同源 bug）。真实方法为 convertToViewportPoint（与老
        // 前端 PdfViewer 的 convertToViewportRectangle 同族）。坐标契约：
        // bbox 为 PDF 底部原点（左下 y 向上），convertToViewportPoint 期望的
        // 正是这套坐标，直接传入，禁止再做 H−y 翻转（双重翻转会镜像）。
        const [vx0, vy0] = viewport.convertToViewportPoint(bx0, by0)
        const [vx1, vy1] = viewport.convertToViewportPoint(bx1, by1)
        const rowLeft = Math.min(vx0, vx1)
        const rowTop = Math.min(vy0, vy1)
        const rowBottom = Math.max(vy0, vy1)
        const rowH = Math.max(rowBottom - rowTop, 1)
        // Arrow height ≈ one text line, never tiny/huge. Width kept slim
        // (1.4×height, head-dominant) so the vertical bookmark label can sit
        // in the page's left margin next to it without overlapping the arrow
        // or the body text (page-left margin is narrow on scanned GB PDFs).
        const arrowH = Math.max(10, Math.min(rowH, 56))
        const arrowW = Math.max(14, Math.min(arrowH * 1.4, 40))
        // Arrow occupies x ∈ [arrowLeft, rowLeft-2]; arrowLeft ≥ 18 leaves the
        // left 2..16px strip free for the bookmark label.
        const left = Math.max(18, rowLeft - arrowW - 2)
        const top = rowTop + (rowH - arrowH) / 2
        box.style.left = `${left}px`
        box.style.top = `${top}px`
        box.style.width = `${arrowW}px`
        box.style.height = `${arrowH}px`
        box.style.display = 'block'
        // 条款收藏按钮锚点：竖排文字列固定在最左 2..16px 边注带，
        // 垂直中心对齐条款行——与箭头左右分离（互不重叠、不压正文）。
        setArrowPos({
          rowLeft,
          arrowLeft: left,
          top: rowTop,
          height: rowH,
        })
      } else {
        box.style.display = 'none'
        setArrowPos(null)
      }
    }
  }, [pagingMode])

  /**
   * 增强③-B: 记录一次成功载入的证据。优先用 tab.path 的原始 href；若该 href
   * 落点页 ≠ 实际渲染页（链接无 page 参数、由 bbox span 自动定页），则改为用
   * effEv 重建一个带正确页的锚点 URL，保证"跳回"忠实落页。同 URL 去重置顶。
   */
  const pushHistory = useCallback((rawHref: string | null, effEv: KsEvidence) => {
    let url: string | null = rawHref
    if (url !== null) {
      const parsed = parseEvidence(url)
      if (parsed !== null && effEv.page !== undefined && (parsed.page ?? 1) !== effEv.page) {
        url = evidenceUrlOf(effEv)
      }
    } else {
      url = evidenceUrlOf(effEv)
    }
    if (url === null) return
    const rest = historyRef.current.filter((h) => h.url !== url)
    rest.unshift({ url, ev: effEv })
    if (rest.length > HISTORY_CAP) rest.length = HISTORY_CAP
    historyRef.current = rest
  }, [])

  /** 增强③-A: 拉取 meta 刷新收藏真值（doc + clause），并刷新本文档条款收藏列表。 */
  const refreshMeta = useCallback(async (rev: string) => {
    const controller = new AbortController()
    try {
      const session = await fetchSession(controller.signal)
      if (controller.signal.aborted) return
      const meta = await fetchClauseMeta(session.engine.port, rev, session.token, controller.signal)
      if (controller.signal.aborted) return
      const docId = meta.doc_id
      setCurDocId(docId.length > 0 ? docId : null)
      setCurClauseKey(meta.clause_key.length > 0 ? meta.clause_key : null)
      setDocBookmarked(meta.doc_bookmarked === true)
      setBmState(meta.clause_bookmarked === true ? 'done' : 'idle')
      // 本文档已收藏条款列表（下拉数据源；供从收藏 tab 删除后同步）
      if (docId.length > 0) {
        const all = await fetchBookmarks(session.engine.port, session.token, controller.signal)
        if (controller.signal.aborted) return
        setDocClauseBms(all.filter((b) => b.doc_id === docId))
      } else {
        setDocClauseBms([])
      }
    } catch (error) {
      if (controller.signal.aborted) return
      console.warn('[ks:pdf] refreshMeta failed (bookmark state unknown)', error)
    }
  }, [])
  refreshMetaRef.current = refreshMeta

  /** Load the doc + render the requested page. Aborts in-flight work on re-run. */
  const loadEvidence = useCallback(async (ev: KsEvidence | null) => {
  // 打开文档即让位（用户 2026-09-09 需求）：点证据链接/从文件目录打开文档 →
  // 把侧栏拉到"文档友好宽度"，保证 PDF 可读；宽度在关闭本 tab 时由卸载 effect 恢复。
  //
  // ⚠ 2026-09-16 迁移：该特性依赖旧 better-sidebar 的 `state.width` 读写，官方右侧栏
  // **无对应面**（它是可分屏/浮动的 dock 列）。故改为经可选的 `panel` 能力端口：
  // 宿主不提供（当前官方主机即如此）→ 整条路径静默跳过，PDF 按当前列宽铺满。
  // 特性本身记为**可复议项**（用户已裁定）。
  if (panel !== undefined) widenPanelForPdf(panel, sessionId)
    // 这次让位同样是一段 0.3s 宽度过渡 → 期间冻结重绘，等它停稳再按最终尺寸画一次。
    freezeRender(settleMsRef.current + 60)
    // Abort anything in flight.（连续模式下可能有多页在画，逐页取消。）
    abortRef.current?.abort()
    for (const task of tasksByPageRef.current.values()) {
      try { task.cancel() } catch { /* ignore */ }
    }
    tasksByPageRef.current.clear()
    // 换文档/重载 → 抖动抑制的基准失效（新 PDF 页尺寸可能不同），清零。
    lastFitRef.current.clear()
    cancelledPagesRef.current.clear()
    visiblePagesRef.current.clear()
    pageTokenRef.current.clear()
    paintSigRef.current = ''
    // 文档世代 +1：所有仍在飞的帧（旧文档的解码/绘制）回来即自我作废。
    docEpochRef.current += 1
    const controller = new AbortController()
    abortRef.current = controller
    setLoad({ status: 'loading' })
    setEngineHint('')

    if (ev === null) {
      // 2026-10 目录常驻：tab 直接打开（无证据链接）不再是错误——进入 idle 态，
      // 左列默认展开文件目录，用户从目录点任意国标即读（见 body idle 分支）。
      setLoad({ status: 'idle' })
      return
    }

    let session
    try {
      // Every load re-fetches the session: port/token rotate per engine start.
      session = await fetchSession(controller.signal)
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
      return
    }

    let bytes: ArrayBuffer
    try {
      bytes = await fetchPdf(session.engine.port, ev.doc, session.token, controller.signal)
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
      return
    }

    // P1c-RouteA bbox 增强：锚点带 rev 且无 bbox → 经 host 代理取该 rev 的
    // spans，用"目标页首行 span"作箭头锚行（红色右箭头，高=一行高）。
    // 必须在 setLoad(ready) 前完成：renderPage 首绘由 ready 后 effect 驱动，
    // 若在此之后写入，箭头会晚一拍。bbox 缺失 / 请求失败 → 静默跳过，维持
    // 无箭头跳页现状，绝不阻塞 PDF 渲染。
    if (ev.rev !== undefined && ev.bbox === undefined) {
      try {
        const bboxRes = await fetchBbox(ev.rev, controller.signal)
        if (controller.signal.aborted) return
        if (bboxRes.found && bboxRes.spans.length > 0) {
          const targetPage = ev.page !== undefined
            ? ev.page
            : bboxRes.spans[0].page_number
          const pageSpans = bboxRes.spans.filter((s) => s.page_number === targetPage)
          const anchor = pageSpans.length > 0 ? pageSpans[0] : bboxRes.spans[0]
          const row: [number, number, number, number] = [
            anchor.bbox[0], anchor.bbox[1], anchor.bbox[2], anchor.bbox[3],
          ]
          // 以已证非空的 ev 为基（spread evidence.current 时其 null 分支会
          // 把 doc 变 optional → TS2322）：targetPage 语义 = 跳页后的当前页，
          // 箭头绘制读的正是 evidence.current.page（见 renderPage 的 onPage）。
          evidence.current = { ...ev, bbox: row, page: targetPage }
        }
      } catch (error) {
        // 静默降级：bbox 取回失败 → 保持无箭头，仅跳页；留痕便于排查。
        console.warn('[ks:pdf] fetchBbox failed', error)
        if (controller.signal.aborted) return
      }
    }

    // 增强③-A: 预取 meta（doc_id + 收藏真值）。不阻塞 PDF 渲染；
    // 失败只影响收藏按钮初始显示，静默降级。
    if (ev.rev !== undefined) {
      void refreshMetaRef.current?.(ev.rev)
    }

    try {
      // First render in a tab: wire the worker once (worker + JPX/JBIG2 wasm dir).
      configurePdfWorker()
      const wasmUrl = new URL(PDF_WASM_DIR, window.location.origin).href
      const doc = await pdfjs.getDocument({ data: new Uint8Array(bytes), wasmUrl }).promise
      // 底下栏的百分比回显要用第 1 页的 scale=1 尺寸；失败不影响渲染（只是数字
      // 回落到 default viewport 的近似值）。
      try {
        const firstPage = await doc.getPage(1)
        const bv = firstPage.getViewport({ scale: 1 })
        firstPageBaseSizeRef.current = { width: bv.width, height: bv.height }
      } catch (error) {
        firstPageBaseSizeRef.current = null
        console.warn('[ks:pdf] first page base size unavailable', error)
      }
      // verifier P1-4：换文档必须销毁旧 PDFDocumentProxy。只在 [tab.path,tab.meta]
      // 的 cleanup 里 destroy 是不够的——"文件目录打开文档"与"重试"都直接调
      // loadEvidence（tab.path/meta 不变 → cleanup 不执行），旧 doc 连同 worker
      // 侧的字体/图片/算子表与源字节会被反复泄漏。
      const previous = pdfDocRef.current
      pdfDocRef.current = doc
      if (previous !== null && previous !== doc) {
        void previous.destroy().catch(() => { /* 已废弃文档，销毁失败无需上报 */ })
      }
      // 目标页：锚点 page 优先；bbox 增强后 evidence.current.page 可能被刷成
      // 首条 span 所在页（ev.page 缺省时），故以 evidence.current.page 为准。
      const target = evidence.current?.page !== undefined ? evidence.current.page : 1
      // 不在 ready 前内联 renderPage：canvas 只在 ready 分支挂载，
      // 提前渲染时 canvasRef 仍为 null（曾导致"10/31 但正文空白"）。
      // 挂载后由下方 effect（deps: [load.status, page]）触发首绘。
      if (controller.signal.aborted) return
      setPage(target)
      setPageInput(String(target))
      // 增强③-B: 成功载入后记入历史（ev 以实际渲染页为准）。
      pushHistory(pathHrefRef.current, { ...ev, page: target })
      // 标题目录（B）：记下当前文档 id，供目录列 effect 拉 /tree。
      setLoadedDocId(ev.doc)
      setLoad({ status: 'ready', pages: doc.numPages })
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
    }
  }, [pushHistory, renderPage])

  // Re-parse evidence whenever the tab's path/meta changes, then load.
  useEffect(() => {
    const rawPath = typeof (tab as { path?: unknown }).path === 'string'
      ? (tab as { path: string }).path
      : null
    pathHrefRef.current = rawPath
    const ev = parseEvidence(rawPath)
      ?? parseEvidence((tab as { meta?: KsEvidence }).meta)
    evidence.current = ev
    // 增强③-A: 新证据（path/meta 变化）→ 收藏状态重置（不沿用上一条的"已收藏"）。
    setBmState('idle')
    setCurDocId(null)
    setCurClauseKey(null)
    setDocClauseBms([])
    setDocBookmarked(false)
    setArrowPos(null)
    // 标题目录（B）：换文档/重载 → 重置目录数据（loadedDocId 在 ready 时再写入）。
    // tocOpen **不重置**：默认收起，用户手动展开后应在本 tab 生命周期内保持选择
    // （换文档/连点证据链接不该把它又收起来）。
    setLoadedDocId(null)
    setToc(null)
    // 正文视图随换文档回到 PDF（新文档的正文要用户主动再看）。
    setViewMode('pdf')
    // 目录常驻（2026-10-27）：本 tab 从未有过证据（无问答直接打开）→ 左列引导到
    // 文件目录，用户可即刻浏览/点开国标阅读。有过证据或用户已手动切换则不动。
    if (ev === null && !leftModeTouchedRef.current) {
      setLeftMode('files')
    }
    if (ev !== null) {
      setPageInput(String(ev.page ?? 1))
      // 旧模型靠 better-sidebar 的 `updateTab` 把标签从主机名派生的标题改成页号；
      // 官方模型下 tab 记录自带 title，由宿主经 `onUpdateTitle` 注入改法（可省略）。
      const label = `PDF 查看器${ev.page !== undefined ? ` · 第${ev.page}页` : ''}`
      try { onUpdateTitle?.(label) } catch { /* ignore */ }
    }
    void loadEvidence(ev)
    return () => {
      abortRef.current?.abort()
      for (const task of tasksByPageRef.current.values()) {
        try { task.cancel() } catch { /* ignore */ }
      }
      tasksByPageRef.current.clear()
      void pdfDocRef.current?.destroy()
      pdfDocRef.current = null
    }
  }, [tab.path, tab.meta, loadEvidence])

  // 增强③-A: tab 重新可见（如从 🔖 收藏 tab 删除后切回）→ 重拉 meta 刷新收藏真值，
  // 避免"已在收藏 tab 删除但这里仍显示已收藏"的跨 tab 状态漂移。
  useEffect(() => {
    if (!visible) return
    const ev = evidence.current
    if (ev !== null && ev.rev !== undefined) {
      void refreshMetaRef.current?.(ev.rev)
    }
  }, [visible])

  // 标题目录（B）：doc 就绪后拉 /api/v1/documents/{doc}/tree。失败/404/空 → 静默降级
  // 为无目录（隐藏列，PDF 全宽）；换 doc 重新拉。
  useEffect(() => {
    const docId = loadedDocId
    tocAbortRef.current?.abort()
    if (docId === null) {
      setToc(null)
      return
    }
    const controller = new AbortController()
    tocAbortRef.current = controller
    setToc(null) // 加载中
    void (async () => {
      let session
      try {
        session = await fetchSession(controller.signal)
      } catch (error) {
        if (controller.signal.aborted) return
        console.warn('[ks:pdf] toc: fetchSession failed', error)
        setToc([]) // 静默降级：隐藏目录列
        return
      }
      let list: KsClause[]
      try {
        list = await fetchDocTree(session.engine.port, docId, session.token, controller.signal)
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof EngineAuthError) {
          try {
            session = await fetchSession(controller.signal)
            list = await fetchDocTree(session.engine.port, docId, session.token, controller.signal)
          } catch (error2) {
            if (controller.signal.aborted) return
            console.warn('[ks:pdf] toc fetch failed (2)', error2)
            setToc([])
            return
          }
        } else {
          console.warn('[ks:pdf] toc fetch failed', error)
          setToc([])
          return
        }
      }
      if (controller.signal.aborted) return
      setToc(list)
    })()
    return () => { controller.abort() }
  }, [loadedDocId])

  /**
   * 左列是否占位。**只跟"意图"和"本文档有没有目录"有关，绝不跟 load.status 走**
   * （verifier P0-2：带上 ready 后每换一次文档都会先塌陷再展开 ±190px，而面板的
   * +190 还在 → PDF 被撑宽一段 >360ms → 防抖到期真的重绘一次再还原，正是用户看到
   * 的"闪一下、动一下、再恢复原来尺寸"）。
   * `toc === null` = 目录还在加载（未知）→ 按"有目录"处理，避免加载期间抖动。
   */
  const docHasToc = toc === null ? true : toc.length > 0
  const showLeftCol = leftMode !== 'toc' || (tocOpen && docHasToc)

  // 标题目录统一搜索（2026-10-28 四宫格）：按编号/标题/页码过滤章/小节。
  const tocQ = dirQuery.trim().toLowerCase()
  const tocFiltered = useMemo(() => {
    if (toc === null || tocQ === '') return toc
    return toc.filter((t) =>
      (t.clause_number ?? '').toLowerCase().includes(tocQ)
      || (t.title ?? '').toLowerCase().includes(tocQ)
      || String(t.page_start ?? '').includes(tocQ))
  }, [toc, tocQ])

  // ---- 目录列宽度与面板宽度**同步过渡**（用户 2026-09-09：不够丝滑，要无感弹出）----
  // 面板宽度是 CSS 过渡（0.3s），若目录列瞬时出现 → 动画期间
  // 「面板宽(t) − 目录列宽(t)」先缩 190px 再涨回来，PDF 被重排（闪一下再恢复）。
  // 做法：**目录列永远挂载**，宽度只用同一组过渡变量在 0↔190 之间动，并由下面的
  // layout effect 在同一帧把面板宽度 ±190 —— 构造性和恒定，PDF 全程不变。
  // （verifier P0-1：早先用"挂载状态机 + rAF 补起点"会晚一帧启动过渡，最快处单帧
  //  位移可达 ~29px，且 rAF 抢跑时整列会 190px 瞬跳。永久挂载从根上消灭该竞态。）
  const [reduceMotion, setReduceMotion] = useState(() => (
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false
  ))
  // 系统「减少动态效果」是**活的**媒体查询：上游 CSS 会因此关掉面板过渡
  // （verifier P2-7），本列必须跟着变，否则一边瞬时一边动画 → 又不恒定。
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return undefined
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (): void => setReduceMotion(mql.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])
  const tocTransition = reduceMotion ? 'none' : $tocSlideTransition

  /**
   * 冻结重绘 ms 毫秒（我们自己的几何动画期间），并在冻结结束后补测一次：
   * 尺寸真的变了才重绘（例如面板确实变宽了），没变就一次都不画。
   * 用 ref 间接调用 measureNow —— 本助手必须定义在 push/pull layout effect 之前，
   * 而 measureNow 在后面的测量块里（measureNowRef 在那里赋值）。
   */
  const measureNowRef = useRef<((force?: boolean) => void) | null>(null)
  const freezeRender = useCallback((ms: number) => {
    renderFreezeUntilRef.current = Math.max(renderFreezeUntilRef.current, Date.now() + ms)
    if (freezeTimerRef.current !== null) window.clearTimeout(freezeTimerRef.current)
    freezeTimerRef.current = window.setTimeout(() => {
      freezeTimerRef.current = null
      if (!pendingRenderRef.current) return
      pendingRenderRef.current = false
      measureNowRef.current?.(true)
    }, ms + 40)
  }, [])


  // ---- 布局测量（2026-09-09 用户反馈「PDF 默认太小，要高度尽可能高」）----
  // 旧实现只在 [load.status, page, showLeftCol] 变化时重绘 → 窗口最大化/还原、
  // 侧栏拖宽、浏览器缩放（Ctrl+±）都不会重算，窄侧栏下页面小且纵向留白。
  // 现在统一由容器实测尺寸驱动：ResizeObserver（侧栏拖拽/最大化/布局变化）+
  // window.resize + visualViewport.resize（浏览器缩放/移动端可视视口）+
  // matchMedia 分辨率监听（跨显示器 DPI 变化）。拖拽期间用 120ms 防抖，
  // 避免每一帧都重渲染整页 PDF。
  const [box, setBox] = useState<{ w: number; h: number } | null>(null)
  const measureTimer = useRef<number | null>(null)
  // 长档延迟 = 面板宽度过渡时长 + 余量（无动画/减少动态效果时压到短档）。
  const reduceMotionRef = useRef(false)
  reduceMotionRef.current = reduceMotion
  const settleMsRef = useRef(DEFAULT_SETTLE_MS)
  settleMsRef.current = reduceMotion ? RESIZE_SETTLE_MS : Math.max(RESIZE_SETTLE_MS, readSlowTransitionMs() + 80)
  /** devicePixelRatio 世代号：纯 DPI 变化（跨屏 / 浏览器缩放）不改布局尺寸，
   *  必须靠它单独触发一次重绘，否则 canvas 后备位图停在旧 dpr 上（发糊）。 */
  const [dprEpoch, setDprEpoch] = useState(0)

  const measureNow = useCallback((force = false) => {
    const el = containerRef.current
    if (el === null) return
    const w = el.clientWidth
    const h = el.clientHeight
    setBox((prev) => {
      // force：冻结结束时无条件换一个新对象，逼渲染 effect 重跑一次
      // （否则"冻结期间 box 已经被更新过"会让 effect 不再触发 → PDF 停在旧尺寸）。
      if (force && prev !== null) return { w, h }
      if (prev === null) return { w, h }
      // 尺寸死区（verifier P0-1）：滚动条出现/消失会改变 clientWidth/Height 约
      // 15px，若照单全收就会形成「重绘 → 滚动条变化 → 再重绘」的无限循环
      // （15px 在 400px 侧栏上是 4%，比 3% 缩放死区还大）。20px 以下的变化一律
      // 视为滚动条抖动，不更新 box；真实拖拽会累积超过阈值后一次性生效。
      if (Math.abs(prev.w - w) < SCROLLBAR_NOISE_PX && Math.abs(prev.h - h) < SCROLLBAR_NOISE_PX) {
        return prev
      }
      return { w, h }
    })
  }, [])

  measureNowRef.current = measureNow

  const scheduleMeasure = useCallback((delay = settleMsRef.current) => {
    if (measureTimer.current !== null) window.clearTimeout(measureTimer.current)
    measureTimer.current = window.setTimeout(() => {
      measureTimer.current = null
      measureNow()
    }, delay)
  }, [measureNow])

  useEffect(() => {
    measureNow() // 首帧立即量一次，不等防抖
    const el = containerRef.current
    const ro = typeof ResizeObserver !== 'undefined' && el !== null
      ? new ResizeObserver(() => scheduleMeasure())
      : null
    if (ro !== null && el !== null) ro.observe(el)
    // 视口变化（最大化/浏览器缩放/屏幕旋转）没有 CSS 宽度过渡参与 → 短档保响应；
    // 容器尺寸变化（侧栏拖拽/目录列顶开）走长档，等过渡结束再量一次（verifier P1-5）。
    const onViewportChange = () => scheduleMeasure(RESIZE_SETTLE_MS)
    window.addEventListener('resize', onViewportChange)
    window.visualViewport?.addEventListener('resize', onViewportChange)
    return () => {
      ro?.disconnect()
      window.removeEventListener('resize', onViewportChange)
      window.visualViewport?.removeEventListener('resize', onViewportChange)
      if (measureTimer.current !== null) {
        window.clearTimeout(measureTimer.current)
        measureTimer.current = null
      }
      if (freezeTimerRef.current !== null) {
        window.clearTimeout(freezeTimerRef.current)
        freezeTimerRef.current = null
      }
    }
  }, [measureNow, scheduleMeasure])

  // 跨显示器 DPI 变化 / 浏览器缩放（devicePixelRatio 变了但布局没变）→ 单独
  // 递增 dprEpoch 触发重绘（verifier P1-3：只靠"尺寸变化"这条路，纯 DPI 变化
  // 时 box 引用不变、effect 根本不重跑，canvas 会一直停在旧 dpr 上发糊）。
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    let mql: MediaQueryList | null = null
    let stopped = false
    const onChange = (): void => {
      setDprEpoch((n) => n + 1)
      scheduleMeasure(0)
      bind()
    }
    const bind = (): void => {
      if (stopped) return
      const previous = mql
      const dpr = window.devicePixelRatio || 1
      mql = window.matchMedia(`(resolution: ${dpr}dppx)`)
      mql.addEventListener('change', onChange)
      // 换绑时摘掉旧 MQL 上的监听，避免每次 DPI 变化都留一个活引用。
      previous?.removeEventListener('change', onChange)
    }
    bind()
    return () => {
      stopped = true
      mql?.removeEventListener('change', onChange)
    }
  }, [scheduleMeasure])

  // 关闭 PDF 查看器 → 恢复打开前的侧栏宽度（用户 2026-09-09 需求：不该看完 PDF
  // 还要手动把侧栏拖回去）。"关闭"的判据是 **tab 已从会话状态里消失**——不能只看
  // 卸载：切会话/面板重挂载也会卸载组件，但 tab 还活着（tabOpen 为真），
  // 那种情况必须保留宽度。恢复与让位都在 pdfPanel 模块级 Map 里配对（幂等）。
  // 同 §loadEvidence：无 `panel` 能力时整条跳过（官方主机）。
  useEffect(() => {
    return () => {
      if (panel === undefined) return
      let stillOpen = true
      try {
        stillOpen = sessionId === undefined || tabOpen === undefined
          ? true
          : tabOpen(sessionId, tab.id)
      } catch {
        stillOpen = true // 探不到状态就当作"仍打开"，绝不误改用户宽度
      }
      if (!stillOpen) restorePanelAfterPdf(panel, sessionId)
    }
    // 只在卸载时执行一次：panel/tab.id/sessionId 对一个 tab 实例是稳定的。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---- 绘制管线（2026-09-16 重构：单页 / 连续共用一套）----
  /**
   * 当前绘制签名：翻页模式 | 总页数 | 缩放 | 容器实测尺寸 | dpr 世代 | 首块 canvas
   * 实测宽 | 箭头开关 | 目录列开关。签名变了 → 可见页全部**强制**重画（越过 3%
   * 抖动死区）；签名没变 → 交给死区，滚动进出可视区时不重复解码同一页。
   */
  const paintSignature = useCallback((): string => {
    const doc = pdfDocRef.current
    const first = pageCanvasRefs.current.get(1)
    return [
      pagingMode,
      doc?.numPages ?? 0,
      zoom.source === 'manual' ? `m${zoom.percent}` : 'auto',
      box?.w ?? 0,
      box?.h ?? 0,
      dprEpoch,
      first?.clientWidth ?? 0,
      showArrowPref ? 1 : 0,
      showLeftCol ? 1 : 0,
    ].join('|')
  }, [pagingMode, zoom, box, dprEpoch, showArrowPref, showLeftCol])

  /**
   * 画所有"接近可视区"的页（连续模式）；每页各自独立 render，互不取消。
   * 滚动离开可视区的页不再重画——一屏只维护几张位图，几百页的国标也不吃光内存。
   */
  const paintVisiblePages = useCallback((force = false): void => {
    const doc = pdfDocRef.current
    if (doc === null) return
    const forceAll = force || paintSigRef.current !== paintSignature()
    paintSigRef.current = paintSignature()
    const onFail = (error: unknown): void => {
      // 2026-09-05：曾因 pdfjs 方法名写错（convertToViewPoint）在此被静默吞掉
      // 数月无感 → 至少留痕，避免渲染层错误继续隐身。
      console.warn('[ks:pdf] renderPage failed', error)
    }
    for (const p of pageOrderRef.current) {
      const el = pageCanvasRefs.current.get(p)
      if (el === undefined) continue
      if (!visiblePagesRef.current.has(p)) continue
      // 曾被取消渲染的页（进出可视区高速滚动）可能停在半张旧图上 → 强制重画。
      const pageForce = forceAll || cancelledPagesRef.current.has(p)
      void renderPage(doc, p, el, { force: pageForce, bbox: false }).catch(onFail)
    }
  }, [paintSignature, renderPage])
  /** ref 回调（挂载时机）要用的最新引用——effect 还没跑时它也得能画。 */
  const paintVisiblePagesRef = useRef(paintVisiblePages)
  paintVisiblePagesRef.current = paintVisiblePages

  /**
   * 单页 mode → 唯一的 canvas；连续 mode → 每页一块 canvas 各自登记。
   * 用 ref 回调而不是"状态里存数组"，避免额外的 render 轮次。
   *
   * registerPageCanvas **必须**用 refForPage 缓存成"每页一个稳定函数"：
   * React 在每次 render 时都会用 null 回调旧的 ref、再用新函数回调元素（只要函数
   * 身份变了）。若直接传内联箭头函数，每一次重渲染（滚动、量尺寸、改缩放…）都会
   * 把全部 canvas 注销再登记一遍 —— 缓存被清空、可见页集合被清空、每页都被强制
   * 重绘，瀑布流会疯狂闪烁。稳定身份 = 只在元素真的挂载/卸载时才动。
   */
  const pageRefCallbacks = useRef<Map<number, (el: HTMLCanvasElement | null) => void>>(new Map())
  const registerPageCanvas = useCallback((p: number, el: HTMLCanvasElement | null): void => {
    if (el === null) {
      pageCanvasRefs.current.delete(p)
      visiblePagesRef.current.delete(p)
      lastFitRef.current.delete(p)
      cancelledPagesRef.current.delete(p)
      return
    }
    pageCanvasRefs.current.set(p, el)
    el.dataset.ksPage = String(p)
    // 新挂上来的那块 canvas 先画一次：IO 的首轮回调是异步的，不能等它。
    const root = containerRef.current
    if (root === null) return
    const rootRect = root.getBoundingClientRect()
    const r = el.getBoundingClientRect()
    if (r.bottom >= rootRect.top - CONTINUOUS_MARGIN_PX
      && r.top <= rootRect.bottom + CONTINUOUS_MARGIN_PX) {
      visiblePagesRef.current.add(p)
      paintVisiblePagesRef.current(false)
    }
  }, [])
  const refForPage = useCallback((p: number) => {
    const hit = pageRefCallbacks.current.get(p)
    if (hit !== undefined) return hit
    const fn = (el: HTMLCanvasElement | null): void => registerPageCanvas(p, el)
    pageRefCallbacks.current.set(p, fn)
    return fn
  }, [registerPageCanvas])

  // 首绘/翻页/尺寸变化/DPI 变化/缩放变化统一由本 effect 驱动：canvas 挂载完成
  // （ready）后再画，避免"canvas 尚未存在就渲染"的空白。page 变化 → 重绘；
  // box 变化 → 按新尺寸重绘；dprEpoch 变化 → 按新 dpr 重绘（清晰度）；zoom 变化
  // → 按新缩放重绘；visible 变化 → 隐藏时不画，重新可见时补画。
  useEffect(() => {
    if (load.status !== 'ready' || !visible) return
    const doc = pdfDocRef.current
    if (doc === null) return
    // 当前缩放状态的 ref 镜像（见 zoomRef 注释）。
    zoomRef.current = zoom

    if (pagingMode === 'single') {
      const canvas = canvasRef.current
      if (canvas === null) return
      // 单页：缩放/尺寸/DPI/翻页任一变化都必须真重画（越过 3% 抖动死区），
      // 否则"手动选了个和当前自适应很接近的百分比"会被死区吞掉 → 看着没反应。
      void renderPage(doc, page, canvas, { force: true }).catch((error) => {
        console.warn('[ks:pdf] renderPage failed', error)
      })
      return
    }

    pageOrderRef.current = Array.from({ length: doc.numPages }, (_, i) => i + 1)
    paintVisiblePages(false)
  }, [load.status, page, renderPage, showLeftCol, showArrowPref, box, dprEpoch, visible,
    pagingMode, zoom, paintVisiblePages])

  // 连续模式：可见页集合（IntersectionObserver，root = 滚动容器）。滚动到哪就画哪。
  useEffect(() => {
    if (pagingMode !== 'continuous' || load.status !== 'ready' || !visible) return
    const root = containerRef.current
    if (root === null || typeof IntersectionObserver === 'undefined') return
    const observed = new Set<Element>()
    const io = new IntersectionObserver((entries) => {
      let changed = false
      for (const entry of entries) {
        const el = entry.target as HTMLElement
        const p = Number(el.dataset.ksPage ?? '')
        if (!Number.isFinite(p) || p < 1) continue
        if (entry.isIntersecting) {
          if (!visiblePagesRef.current.has(p)) {
            visiblePagesRef.current.add(p)
            changed = true
          }
        } else if (visiblePagesRef.current.delete(p)) {
          changed = true
        }
      }
      // 进出可视区才需要动作；同一批里既有进也有出 → 一次画完。
      if (changed) paintVisiblePagesRef.current(false)
    }, {
      root,
      // 上下各预留约一屏：手感像"已经在旁边画好了"，而不是滚到才出现。
      rootMargin: `${CONTINUOUS_MARGIN_PX}px 0px`,
    })

    const attach = (): void => {
      let added = false
      for (const [p, el] of pageCanvasRefs.current) {
        if (observed.has(el)) continue
        observed.add(el)
        io.observe(el)
        added = true
        void p
      }
      if (added) paintVisiblePagesRef.current(false)
    }
    attach()
    // rAF 补一次：ref 回调可能在本 effect 之前就跑完了，attach 兜住时序。
    const raf = window.requestAnimationFrame(attach)
    return () => {
      window.cancelAnimationFrame(raf)
      io.disconnect()
    }
  }, [pagingMode, load.status, visible, paintVisiblePages])

  // Page navigation.（只改状态；实际绘制由上方 effect 触发）
  const goTo = useCallback((n: number) => {
    const doc = pdfDocRef.current
    if (doc === null) return
    const target = Math.max(1, Math.min(n, doc.numPages))
    setPage(target)
    setPageInput(String(target))
  }, [])

  /**
   * 切翻页模式（底部常驻栏的「单页 / 连续」）后的**阅读位置保持**：
   *   · 连续 → 单页：以"当前在视野里的那一页"为准回填页码，否则切过去会跳回旧的
   *     单页页码，读者瞬间丢失位置；
   *   · 单页 → 连续：下一帧把当前页滚进视野（由 SP scroll 那段 effect 完成），
   *     否则从"第 200 页单页"切连续会落在第 1 页顶上，页码控件与画面立刻对不上。
   */
  const setPagingModeAndSync = useCallback((next: 'single' | 'continuous') => {
    setZoomMenuOpen(false)
    if (next === pagingMode) return
    if (next === 'single') {
      // 连续 → 单页：取"最靠近滚动容器顶部的已挂载页"作当前页，否则切过去会跳回
      // 旧的单页页码，读者瞬间丢失位置。
      const container = containerRef.current
      if (container !== null) {
        const rootTop = container.getBoundingClientRect().top
        let best: number | null = null
        let bestDist = Number.POSITIVE_INFINITY
        for (const [p, el] of pageCanvasRefs.current) {
          const d = Math.abs(el.getBoundingClientRect().top - rootTop)
          if (d < bestDist) { bestDist = d; best = p }
        }
        if (best !== null) {
          pendingScrollPageRef.current = null
          setPage(best)
          setPageInput(String(best))
        }
      }
    } else {
      // 单页 → 连续：把当前页交给滚动 effect（等它挂载后滚入视野），否则从
      // "第 200 页单页"切连续会落在第 1 页顶上，页码控件与画面立刻对不上。
      pendingScrollPageRef.current = page
    }
    setPagingMode(next)
  }, [pagingMode, page])

  /**
   * 连续 → 单页：把目标页滚进视野。延迟一帧，等滚动容器换成单页那块 canvas。
   */
  const singleSyncPendingRef = useRef(false)
  useEffect(() => {
    if (pagingMode !== 'single') return
    singleSyncPendingRef.current = true
  }, [pagingMode])
  useEffect(() => {
    // 只在这一页**绘制成功后**做一次对齐（否则量到的是旧尺寸）；且只在刚切成
    // 单页那一次——不能每次翻页都重排滚动位置（用户手动滚过就该尊重）。
    if (!singleSyncPendingRef.current) return
    if (pagingMode !== 'single' || load.status !== 'ready' || !visible) return
    const container = containerRef.current
    const canvas = canvasRef.current
    if (container === null || canvas === null) return
    const raf = window.requestAnimationFrame(() => {
      const rootTop = container.getBoundingClientRect().top
      const r = canvas.getBoundingClientRect()
      if (r.height <= 0) return
      singleSyncPendingRef.current = false
      // 页面比容器高：对齐页顶；比容器矮：垂直居中。差得不多就不动，避免把用户的
      // 横向滚动位置抖掉。
      const delta = r.height > container.clientHeight
        ? r.top - rootTop
        : r.top - rootTop - (container.clientHeight - r.height) / 2
      if (Math.abs(delta) > 2) container.scrollTop += delta
    })
    return () => window.cancelAnimationFrame(raf)
  }, [pagingMode, load.status, visible, page, box, dprEpoch])

  /**
   * 单页 → 连续：把当前页滚进视野。要在**那块 canvas 挂载之后**做，所以由
   * pendingScrollPageRef 交接、在模式与 box 变化后重试到成功为止。
   */
  useEffect(() => {
    const want = pendingScrollPageRef.current
    if (want === null) return
    if (pagingMode !== 'continuous' || load.status !== 'ready' || !visible) return
    const container = containerRef.current
    if (container === null) return
    const el = pageCanvasRefs.current.get(want)
    if (el === undefined) return
    const raf = window.requestAnimationFrame(() => {
      pendingScrollPageRef.current = null
      const containerTop = container.scrollTop
      const delta = el.getBoundingClientRect().top - container.getBoundingClientRect().top
      container.scrollTop = Math.max(0, containerTop + delta)
    })
    return () => window.cancelAnimationFrame(raf)
  }, [pagingMode, load.status, visible, page, box, dprEpoch])

  /** 手动设比例（拖滑块 / 选下拉）→ 退出自适应（纯函数 zoomForManual）。 */
  const applyManualZoom = useCallback((percent: number) => {
    setZoom(zoomForManual(percent))
  }, [])

  /** 点「自适应窗口」→ 恢复自适应（此后再次跟随窗口尺寸）。 */
  const applyAutoZoom = useCallback(() => {
    setZoom(zoomForAutoFit())
    setZoomMenuOpen(false)
  }, [])

  /** 打开/收起「浏览比例」下拉（**向上**弹出），并记下按钮位置作锚点。 */
  const toggleZoomMenu = useCallback((anchorEl: HTMLElement | null) => {
    if (zoomMenuOpen) {
      setZoomMenuOpen(false)
      return
    }
    if (anchorEl === null) return
    const r = anchorEl.getBoundingClientRect()
    setZoomAnchor({ left: r.left, bottom: r.bottom, width: r.width })
    setZoomMenuOpen(true)
  }, [zoomMenuOpen])

  // 下拉展开期间：点别处 / 滚动 / 改窗口尺寸 → 收起（否则浮层会漂在旧位置）。
  useEffect(() => {
    if (!zoomMenuOpen) return
    const close = (): void => setZoomMenuOpen(false)
    const onKey = (e: KeyboardEvent): void => { if (e.key === 'Escape') close() }
    window.addEventListener('resize', close)
    window.addEventListener('scroll', close, true)
    document.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('resize', close)
      window.removeEventListener('scroll', close, true)
      document.removeEventListener('keydown', onKey)
    }
  }, [zoomMenuOpen])

  const onInput = (raw: string): void => {
    const n = parseInt(raw, 10)
    if (!Number.isNaN(n) && n >= 1) void goTo(n)
  }

  /**
   * 开/关标题目录列。overlay 版本只改"是否显示"，PDF 布局纹丝不动。
   */
  const toggleToc = useCallback((open: boolean) => {
    setTocOpen(open)
  }, [])

  /** 标题目录（B）：点任意条目 → PDF 跳到该页（复用 goTo；仅跳页，不做箭头定位）。 */
  const tocJump = useCallback((t: KsClause) => {
    const n = typeof t.page_start === 'number' && Number.isFinite(t.page_start) ? t.page_start : null
    if (n === null) return
    goTo(n)
  }, [goTo])

  /** 文件目录模式：点文档 → 本 tab 直接加载该文档 PDF（首页），并切回标题目录。 */
  const onFilesOpenDoc = useCallback((docId: string) => {
    const ev: KsEvidence = { doc: docId, page: 1 }
    evidence.current = ev
    setLeftMode('toc') // 加载后左列回到标题目录（展示新文档目录）
    void loadEvidence(ev)
  }, [loadEvidence])

  /** 收藏目录模式：点文档/条款叶 → 本 tab 直接加载该证据（页码直达），保持收藏目录。 */
  const onBookmarkJump = useCallback((jump: KsBookmarkJump) => {
    const ev: KsEvidence = { doc: jump.doc, page: jump.page, rev: jump.rev }
    evidence.current = ev
    // 不切模式：浏览收藏目录时连续点多个文档/条款是主用例。
    void loadEvidence(ev)
  }, [loadEvidence])

  const retry = useCallback(() => {
    clearSession()
    void loadEvidence(evidence.current)
  }, [loadEvidence])

  /** 增强③-B: 从历史跳到某条证据（沿用现有 [tab.path, tab.meta] 重载 effect）。 */
  const jumpHistory = useCallback((href: HistoryEntry) => {
    const title = `PDF 查看器${href.ev.page !== undefined ? ` · 第${href.ev.page}页` : ''}`
    if (href.url) {
      try {
        // 旧模型靠 better-sidebar 的 `updateTab({path, meta:{ksClick}})` 覆写单例 tab：
        // meta 里的共享单调 nonce 让"path 与上次相同"也能触发 [tab.path, tab.meta] effect。
        // 官方模型里等价物是**再导航一次**——`tabDomain.navigate` 每次把
        // `navigation.revision` +1（见 ksSidebar.ts 文件头映射表），宿主经
        // `onOpenEvidence` 注入该动作，由 KsEvidenceHost 转成 openResource。
        if (onOpenEvidence !== undefined) {
          onOpenEvidence(href.url, title)
          return
        }
      } catch { /* 导航失败 → 下方本地重载兜底 */ }
    }
    // 拿不到 URL（异常态）或无宿主注入：本地直接重载，仍能跳页。
    evidence.current = href.ev
    void loadEvidence(href.ev)
  }, [onOpenEvidence, loadEvidence])

  /** 拉收藏夹列表（401 自愈一次）；失败返回 null（调用方按"无夹"处理并提示）。 */
  const loadFolders = useCallback(async (): Promise<KsBookmarkFolder[] | null> => {
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      try {
        return await fetchBookmarkFolders(session.engine.port, session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          return await fetchBookmarkFolders(session.engine.port, session.token, controller.signal)
        }
        throw error
      }
    } catch (error) {
      setEngineHint(`收藏夹列表获取失败：${error instanceof Error ? error.message : String(error)}（收藏将进入未分类）`)
      return null
    }
  }, [])

  /** 收藏确认（选夹后）：标准级。folderId null = 未分类。 */
  const confirmDocBookmark = useCallback(async (folderId: string | null) => {
    const docId = curDocId
    if (docId === null) return
    setFolderPicker(null)
    setDocBusy(true)
    setEngineHint('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      try {
        await addDocBookmark(session.engine.port, docId, session.token, controller.signal, folderId)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          await addDocBookmark(session.engine.port, docId, session.token, controller.signal, folderId)
        } else {
          throw error
        }
      }
      setDocBookmarked(true)
      setFolderList(null) // 收藏成功 → 下次点击重拉夹列表（计数变了）
      setEngineHint(folderId === null ? '已收藏本标准（未分类）' : '已收藏本标准')
    } catch (error) {
      if (controller.signal.aborted) return
      setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setDocBusy(false)
    }
  }, [curDocId])

  /** 顶部按钮：收藏/取消收藏本标准（toggle）。收藏时经选夹菜单（无夹时一键直收）。
   *  取消收藏不需要选夹。失败显示在 engineHint。 */
  const toggleDocBookmark = useCallback(async () => {
    if (docBusy) return
    const docId = curDocId
    if (docId === null) return
    if (docBookmarked) {
      // 取消收藏：原路径不动
      setDocBusy(true)
      setEngineHint('')
      const controller = new AbortController()
      try {
        let session = await fetchSession(controller.signal)
        try {
          await removeDocBookmarkByDoc(session.engine.port, docId, session.token, controller.signal)
        } catch (error) {
          if (error instanceof EngineAuthError) {
            session = await fetchSession(controller.signal)
            await removeDocBookmarkByDoc(session.engine.port, docId, session.token, controller.signal)
          } else {
            throw error
          }
        }
        setDocBookmarked(false)
        setEngineHint('已取消收藏本标准')
      } catch (error) {
        if (controller.signal.aborted) return
        setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
      } finally {
        setDocBusy(false)
      }
      return
    }
    // 收藏：懒加载夹列表 → 有夹弹选夹菜单 / 无夹一键直收
    setFolderLoading(true)
    const folders = await loadFolders()
    setFolderLoading(false)
    if (folders === null || folders.length === 0) {
      await confirmDocBookmark(null)
      return
    }
    setFolderList(folders)
    setFolderNewName('')
    setFolderPicker('doc')
  }, [docBusy, docBookmarked, curDocId, loadFolders, confirmDocBookmark])

  /** 收藏确认（选夹后）：条款级。folderId null = 未分类。rev 用于收藏后刷新 meta。 */
  const confirmClauseBookmark = useCallback(async (clauseKey: string, folderId: string | null, rev: string) => {
    setFolderPicker(null)
    setBmState('busy')
    setEngineHint('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      try {
        await addBookmark(session.engine.port, clauseKey, session.token, controller.signal, folderId)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          await addBookmark(session.engine.port, clauseKey, session.token, controller.signal, folderId)
        } else {
          throw error
        }
      }
      setBmState('done')
      setCurClauseKey(clauseKey)
      setFolderList(null)
      setEngineHint(folderId === null ? '已收藏本条款（未分类）' : '已收藏本条款')
      void refreshMetaRef.current?.(rev)
    } catch (error) {
      if (controller.signal.aborted) return
      setBmState('idle')
      setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }, [])

  /** 竖排按钮：收藏/取消收藏本条款（toggle）。收藏经 meta 取 clause_key → 选夹菜单
   *  （无夹一键直收）→ POST；取消经 clause_key → DELETE by-clause。幂等。 */
  const clauseBookmark = useCallback(async () => {
    const ev = evidence.current
    if (ev === null || ev.rev === undefined) return
    if (bmState === 'busy') return
    // 取消：原路径不动
    if (bmState === 'done') {
      setBmState('busy')
      setEngineHint('')
      const controller = new AbortController()
      try {
        let session = await fetchSession(controller.signal)
        const clauseKey = curClauseKey
        if (clauseKey === null) {
          const meta0 = await fetchClauseMeta(session.engine.port, ev.rev, session.token, controller.signal)
          await removeBookmarkByClauseKey(session.engine.port, meta0.clause_key, session.token, controller.signal)
        } else {
          try {
            await removeBookmarkByClauseKey(session.engine.port, clauseKey, session.token, controller.signal)
          } catch (error) {
            if (error instanceof EngineAuthError) {
              session = await fetchSession(controller.signal)
              await removeBookmarkByClauseKey(session.engine.port, clauseKey, session.token, controller.signal)
            } else {
              throw error
            }
          }
        }
        setBmState('idle')
        setEngineHint('已取消收藏本条款')
        void refreshMetaRef.current?.(ev.rev)
      } catch (error) {
        if (controller.signal.aborted) return
        setBmState('done')
        setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
      }
      return
    }
    // 收藏：取 clause_key → 懒加载夹列表 → 有夹弹选夹 / 无夹一键直收
    setBmState('busy')
    setEngineHint('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      let meta
      try {
        meta = await fetchClauseMeta(session.engine.port, ev.rev, session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          meta = await fetchClauseMeta(session.engine.port, ev.rev, session.token, controller.signal)
        } else {
          throw error
        }
      }
      setFolderLoading(true)
      const folders = await loadFolders()
      setFolderLoading(false)
      if (folders === null || folders.length === 0) {
        await confirmClauseBookmark(meta.clause_key, null, ev.rev)
      } else {
        pendingClauseKeyRef.current = meta.clause_key
        pendingRevRef.current = ev.rev
        setFolderList(folders)
        setFolderNewName('')
        setFolderPicker('clause')
        setBmState('idle') // 等菜单确认；期间按钮可再点（关菜单）
      }
    } catch (error) {
      if (controller.signal.aborted) return
      setBmState('idle')
      setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }, [bmState, curClauseKey, loadFolders, confirmClauseBookmark])

  const total = load.status === 'ready' ? load.pages : 0

  /**
   * 底部栏要回显的缩放（与画布共用同一份真值，见 pdfFit.zoomScale）：
   * autoFit 下按容器实测尺寸现算（所以数字会随窗口变化跳动 = 用户看得见"在自适应"）；
   * manual 下就是用户选的那个百分比。容器还没量到尺寸时用 box 的上一帧值。
   */
  const zoomView = useMemo(() => {
    const container = containerRef.current
    // 用 box（已测量）而非 container.clientWidth：首次渲染时 ref 还没挂。
    const availWidth = (box?.w ?? container?.clientWidth ?? 0) - PAGE_PADDING
    const availHeightRaw = (box?.h ?? container?.clientHeight ?? 0) - PAGE_PADDING
    const availHeight = pagingMode === 'single'
      ? availHeightRaw
      : continuousViewportHeight(availWidth)
    // 页尺寸：拿已加载文档第 1 页的 viewport（scale=1）。取不到就用 A4 兜底，只为
    // 让百分比数字有个显示值；真正绘制时用的是每页自己的尺寸（renderPage 内）。
    const base = firstPageBaseSizeRef.current
    return zoomScale(zoom, {
      availWidth,
      availHeight,
      pageWidth: base?.width ?? 595.28,
      pageHeight: base?.height ?? 841.89,
    })
  }, [zoom, box, pagingMode, dprEpoch, load.status])
  /** 滑块当前值：manual 下是用户百分比，autoFit 下是自适应算出的百分比。 */
  const sliderPercent = Math.max(MANUAL_MIN_PERCENT,
    Math.min(MANUAL_MAX_PERCENT, zoomView.percent))

  // 增强③-B: 与当前 doc 相同、且不是当前页的历史条目（空 → 控件隐藏）。
  const currentDoc = evidence.current?.doc ?? null
  const historyOptions = (currentDoc !== null)
    ? historyRef.current.filter((h) => h.ev.doc === currentDoc && (h.ev.page ?? 1) !== page)
    : []
  const historyLabel = (h: HistoryEntry): string => {
    const pg = h.ev.page !== undefined ? h.ev.page : 1
    return `第${pg}页`
  }

  // 增强③-A: 从「已收藏条款」下拉跳到某条已收藏条款（复用 [tab.path,tab.meta] 重载）。
  const jumpToBookmark = useCallback((b: KsBookmark) => {
    const doc = typeof b.doc_id === 'string' && b.doc_id.length > 0 ? b.doc_id : null
    const page = typeof b.page_start === 'number' && b.page_start >= 1 ? Math.floor(b.page_start) : null
    if (doc === null || page === null) return
    const ev: KsEvidence = { doc, page, rev: b.clause_revision_id ?? undefined }
    const url = evidenceUrlOf(ev)
    if (url === null) return
    const title = `PDF 查看器 · 第${page}页`
    // 官方模型：一次导航即"打开或复用"该资源地址；同一地址再次导航靠
    // `navigation.revision` 递增触发重载（旧模型需要 openTab + updateTab 两步）。
    try { onOpenEvidence?.(url, title) } catch { /* ignore */ }
  }, [onOpenEvidence])

  // 下拉项标签：条款号 + 页（同页多条也能区分）
  const bookmarkOptionLabel = (b: KsBookmark): string => {
    const no = typeof b.clause_number === 'string' && b.clause_number.length > 0 ? b.clause_number : '?'
    const pg = typeof b.page_start === 'number' && b.page_start >= 1 ? b.page_start : '?'
    return `§${no} · 第${pg}页`
  }

  // ---- 选夹菜单 handlers（2026-10）----

  /** 选一个已有夹 / 未分类 → 按收藏类型确认。 */
  const pickFolder = useCallback(async (folderId: string | null) => {
    if (folderPicker === 'doc') {
      await confirmDocBookmark(folderId)
    } else if (folderPicker === 'clause') {
      const clauseKey = pendingClauseKeyRef.current
      const rev = pendingRevRef.current
      if (clauseKey !== null && rev !== null) await confirmClauseBookmark(clauseKey, folderId, rev)
    }
  }, [folderPicker, confirmDocBookmark, confirmClauseBookmark])

  /** 选夹菜单里「新建夹」→ 建夹后立即用它收藏。 */
  const pickNewFolder = useCallback(async () => {
    const name = folderNewName.trim()
    if (name.length === 0) return
    setFolderLoading(true)
    try {
      const controller = new AbortController()
      let session = await fetchSession(controller.signal)
      let folder
      try {
        folder = await createBookmarkFolder(session.engine.port, name, session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          folder = await createBookmarkFolder(session.engine.port, name, session.token, controller.signal)
        } else {
          throw error
        }
      }
      setFolderLoading(false)
      setFolderNewName('')
      await pickFolder(folder.folder_id)
    } catch (error) {
      setFolderLoading(false)
      setEngineHint(`新建收藏夹失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }, [folderNewName, pickFolder])

  /** 关闭选夹菜单（点遮罩 / ✕）。未确认 → 本次收藏放弃。 */
  const closeFolderPicker = useCallback(() => {
    setFolderPicker(null)
    setFolderNewName('')
    pendingClauseKeyRef.current = null
  }, [])

  return (
    <>
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, fontSize: 12 }}>
      {/* header: title + page nav + engine hint */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>PDF 查看器</span>
        {/* 增强③-A: 顶部按钮 = 收藏本标准（整本 PDF），换色区分 + hover 提示。
            已收藏 → 金色高亮（可点击取消）；未收藏 → 常规色。需 curDocId（meta 预取）。 */}
        {load.status === 'ready' && curDocId !== null && (
          <button
            type="button"
            disabled={docBusy}
            onClick={() => void toggleDocBookmark()}
            title={docBookmarked ? '取消收藏本标准' : '收藏本标准'}
            style={{
              ...$btnStyle,
              ...(docBookmarked
                ? { color: '#fff', background: 'var(--dsw-alias-warn, #b8860b)', borderColor: 'var(--dsw-alias-warn, #b8860b)' }
                : { color: 'var(--dsw-alias-link, #1565c0)', borderColor: 'var(--dsw-alias-link, #1565c0)' }),
            }}
          >
            {docBusy ? '…' : docBookmarked ? '★ 已收藏本标准' : '☆ 收藏本标准'}
          </button>
        )}
        {/*
          目录（2026-10-28 四宫格）：常驻按钮，开关整个悬浮目录列（列头三模式
          自由切换）。不再只绑定标题目录、不再要求本文档有目录——idle（无文档）
          时同样可开（文件/收藏目录可进）。收起后回到纯 PDF 全宽。
        */}
        <button
          type="button"
          onClick={() => {
            if (showLeftCol) {
              // 收起 = 回标题目录模式并合上（保持语义简单：下次点开还在标题目录）。
              setLeftMode('toc')
              toggleToc(false)
            } else {
              // 展开：当前模式内容不可用（无文档 / 本文档无目录的标题目录）→
              // 直接给文件目录（能点东西）；否则按既有模式展开。
              if ((load.status === 'idle' || !docHasToc) && leftMode === 'toc' && !leftModeTouchedRef.current) {
                setLeftMode('files')
              }
              toggleToc(true)
            }
          }}
          title={showLeftCol
            ? '收起目录列（回到纯 PDF 全宽）'
            : '展开目录列：文件目录 / 收藏目录 / 标题目录三模式自由切换'}
          style={{ ...$btnStyle, ...(showLeftCol ? $tocBtnStyle : {}) }}
        >
          📑 目录{'\u00A0'}{showLeftCol ? '▾' : '▸'}
        </button>
        {/* 正文视图切换（2026-09-13 端点接线）：PDF 原样 ↔ 条款富文本
            （图片/公式/带图表格经 /ks/doc-image 同源代理接线）。
            有 doc id 即可切——正文只依赖 clauses 端点，不依赖 PDF 字节。 */}
        {evidence.current !== null && (
          <button
            type="button"
            onClick={() => setViewMode(viewMode === 'pdf' ? 'text' : 'pdf')}
            title={viewMode === 'pdf'
              ? '切换到正文视图：条款富文本 + 原版图/公式/带图表格截图'
              : '切换回 PDF 视图（原页渲染）'}
            style={{ ...$btnStyle, ...(viewMode === 'text' ? { borderColor: 'var(--dsw-alias-link, #1565c0)', color: 'var(--dsw-alias-link, #1565c0)' } : {}) }}
          >
            {viewMode === 'pdf' ? '📄 正文' : '📑 PDF'}
          </button>
        )}
        {load.status === 'ready' && viewMode === 'pdf' && (
          <>
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => goTo(page - 1)}
              style={$btnStyle}
            >
              ◀
            </button>
            <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>
              <input
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={(e) => onInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onInput(pageInput) }}
                style={{ width: 42, textAlign: 'center', ...$inputStyle }}
                aria-label="页码"
              />
              {' / '}{total}
            </span>
            <button
              type="button"
              disabled={page >= total}
              onClick={() => goTo(page + 1)}
              style={$btnStyle}
            >
              ▶
            </button>
          </>
        )}
        {/* 增强③-B: 最近打开证据的紧凑跳转下拉 */}
        {load.status === 'ready' && historyOptions.length > 0 && (
          <select
            value={selHistory}
            onChange={(e) => {
              const v = e.target.value
              setSelHistory('')
              const hit = historyOptions.find((h) => h.url === v)
              if (hit !== undefined) jumpHistory(hit)
            }}
            style={{ ...$inputStyle, maxWidth: 220 }}
            aria-label="最近打开的证据"
            title="最近打开的证据"
          >
            <option value="">最近证据…</option>
            {historyOptions.map((h) => (
              <option key={h.url} value={h.url}>{historyLabel(h)}</option>
            ))}
          </select>
        )}
        {/* 增强③-A: 本文档已收藏条款下拉（点选跳转对应位置）；收藏 tab 删除后自动同步 */}
        {load.status === 'ready' && docClauseBms.length > 0 && (
          <select
            value={selBm}
            onChange={(e) => {
              const v = e.target.value
              setSelBm('')
              const hit = docClauseBms.find((b) => b.clause_revision_id === v)
              if (hit !== undefined) jumpToBookmark(hit)
            }}
            style={{ ...$inputStyle, maxWidth: 240, color: 'var(--dsw-alias-warn, #b8860b)' }}
            aria-label="本文档已收藏条款"
            title="已收藏条款（点选跳转）"
          >
            <option value="">已收藏条款（{docClauseBms.length}）…</option>
            {docClauseBms.map((b) => (
              <option key={b.clause_revision_id ?? b.bookmark_id} value={b.clause_revision_id ?? ''}>
                {bookmarkOptionLabel(b)}
              </option>
            ))}
          </select>
        )}
        <span style={{ marginLeft: 'auto', color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>
          {engineHint}
        </span>
      </div>

      {/* 收藏夹选夹菜单（2026-10）：portal 到 document.body 的居中浮层。
          打开条件 = folderPicker 非 null（收藏时已有夹）。选已有夹 / 新建并选用 /
          未分类 / ✕ 放弃。 */}
      {folderPicker !== null && typeof document !== 'undefined' && createPortal(
        <div
          onClick={closeFolderPicker}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.18)', zIndex: 9000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: 320, maxWidth: '90vw', background: 'var(--dsw-alias-bg-layer-1, #fff)', border: '1px solid var(--dsw-alias-border-l2, #ccc)', borderRadius: 8, padding: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.25)' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>
                {folderPicker === 'doc' ? '收藏本标准到…' : '收藏本条款到…'}
              </span>
              <button type="button" onClick={closeFolderPicker} style={{ marginLeft: 'auto', border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 14, lineHeight: 1 }} title="放弃本次收藏">×</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 260, overflow: 'auto' }}>
              {(folderList ?? []).map((f) => (
                <button
                  key={f.folder_id}
                  type="button"
                  disabled={folderLoading}
                  onClick={() => void pickFolder(f.folder_id)}
                  style={$folderOpt}
                >
                  📁 {f.folder_name}
                  <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 10, marginLeft: 'auto', whiteSpace: 'nowrap' }}>
                    {f.doc_count > 0 ? `${f.doc_count}档` : ''}{f.clause_count > 0 ? `${f.clause_count}条` : ''}{f.doc_count === 0 && f.clause_count === 0 ? '空' : ''}
                  </span>
                </button>
              ))}
              <button type="button" disabled={folderLoading} onClick={() => void pickFolder(null)} style={{ ...$folderOpt, color: 'var(--dsw-alias-label-secondary, #666)' }}>
                📋 未分类
                <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 10, marginLeft: 'auto', whiteSpace: 'nowrap' }}>不进任何夹</span>
              </button>
            </div>
            <div style={{ display: 'flex', gap: 4, marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--dsw-alias-border-l1, #eee)' }}>
              <input
                value={folderNewName}
                onChange={(e) => setFolderNewName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void pickNewFolder() }}
                placeholder="新建收藏夹名称…"
                style={{ ...$inputStyle, flex: 1 }}
              />
              <button type="button" onClick={() => void pickNewFolder()} disabled={folderLoading || folderNewName.trim().length === 0} style={{ ...$btnStyle, whiteSpace: 'nowrap' }}>
                新建并收藏
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}

      {/* body：右侧 canvas。目录列经 createPortal 挂到 document.body，浮在侧栏
          左侧的对话框区域上——不遮 PDF，也不被 .paneContent 的 overflow:hidden 裁掉。 */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <div ref={containerRef} style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: 12 }}>
        {load.status === 'idle' && viewMode === 'pdf' && evidence.current === null && (
          <div style={{ ...$center, flexDirection: 'column', gap: 8 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 13 }}>
              从左侧目录点开任意国标/法规即可阅读
            </div>
            <div style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11.5, maxWidth: 420, textAlign: 'center', lineHeight: 1.6 }}>
              📚 文件目录 = 库内全部文档按分类浏览 · 🔖 收藏目录 = 你的收藏夹 ·
              📖 标题目录 = 打开文档后的章/小节目录。目录列可在头部三按钮间随时切换。
            </div>
          </div>
        )}
        {load.status === 'loading' && viewMode === 'pdf' && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>载入证据 PDF…（首次可能启动引擎，需要数秒）</div>
          </div>
        )}
        {load.status === 'error' && viewMode === 'pdf' && (
          <div style={{ ...$center, flexDirection: 'column', gap: 10 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', maxWidth: 480, textAlign: 'center', wordBreak: 'break-word' }}>
              {load.message}
            </div>
            <button type="button" onClick={retry} style={$btnPrimary}>重试</button>
          </div>
        )}
        {/* 正文视图只依赖 doc id（clauses 端点），不依赖 PDF 字节——PDF 加载
            失败/进行中的文档也能看正文（verifier 复审第 7 项）。 */}
        {viewMode === 'text' && evidence.current !== null && (
          <KsDocTextView
            docId={evidence.current.doc}
            currentPage={page}
            onJumpPage={(p) => { goTo(p) }}
          />
        )}
        {load.status === 'ready' && viewMode === 'pdf' && pagingMode === 'single' && (
          <div style={{ position: 'relative', display: 'inline-block', contain: 'paint' }}>
            {/* display:block 消除 inline 元素的行框基线沉降（约 4px）——否则
                "刚好铺满高度"时底部会被切掉并常驻一条竖向滚动条。
                translateZ(0) 把 canvas 提升为独立合成层：面板宽度过渡（父级
                contain:layout 重排）就不会再触发这块大位图的重光栅化/黑闪。 */}
            <canvas ref={canvasRef} style={{ display: 'block', transform: 'translateZ(0)' }} />
            <div
              ref={bboxRef}
              aria-hidden="true"
              style={{
                position: 'absolute',
                display: 'none',
                pointerEvents: 'none',
                // 红色实心右箭头（data-URI SVG，2:1），指向条款行左缘。
                backgroundImage: `url("data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
                  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><path d="M0 4h11V1l9 4-9 4V6H0z" fill="#e02020"/></svg>',
                )}")`,
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 100%',
              }}
            />
            {/* 增强③-A: 条款收藏按钮——竖版文字「收藏本条款」，固定在页面左边注带
                （2..18px），垂直居中条款行；与红箭头左右分离互不遮挡。
                悬停 title 补充说明。 */}
            {arrowPos !== null && evidence.current?.rev !== undefined && (
              <button
                type="button"
                disabled={bmState === 'busy'}
                onClick={() => void clauseBookmark()}
                title={bmState === 'done' ? '已收藏本条款，点此取消' : '收藏本条款'}
                style={{
                  position: 'absolute',
                  // 左边注带固定位置（与箭头分开）
                  left: 2,
                  // 垂直居中于条款行区（clamp 顶部不越界）
                  top: Math.max(0, arrowPos.top + Math.max(0, arrowPos.height / 2 - $bmFloatHeight / 2)),
                  ...$bmFloatStyle,
                  ...(bmState === 'done' ? $bmDoneStyle : {}),
                }}
              >
                {bmState === 'busy' ? '…' : bmState === 'done' ? '已收藏' : '收藏本条款'}
              </button>
            )}
          </div>
        )}
        {/*
          连续（瀑布）模式 —— 默认模式（2026-09-16 用户需求）：
          **每一页一块 canvas 纵向堆叠**，滚动连续浏览。尺寸未知前（还没量到容器 /
          还没解码）先给固定高度占位，避免"先塌成 0 高、解码完再撑开"导致滚动位置
          乱跳（这正是 PDF 瀑布流最经典的抖动来源）。
          只绘制"接近可视区"的那几页（IntersectionObserver，见上方的绘制管线），
          所以几百页的国标也只占几张位图的显存。
          红箭头/条款收藏按钮仍只在**单页**模式显示：多页共享一个 arrowPos 状态会
          相互覆盖（本页的箭头会被隔壁页的重绘清掉）。
        */}
        {load.status === 'ready' && viewMode === 'pdf' && pagingMode === 'continuous' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
            {Array.from({ length: total }, (_, i) => i + 1).map((p) => (
              <canvas
                key={p}
                ref={refForPage(p)}
                style={{
                  // 尺寸由 renderPage 在**绘制成功后**按真实 viewport 覆写（width 的
                  // 内联值与这里同为 '100%' 时 React 不会重写，故覆写能保住）。
                  // 写死 100% × aspect-ratio 只是"未绘制前"的占位：给一个**接近真实
                  // 页面**的高度，首帧的布局就是对的——否则全是 240px 的矮盒子，
                  // "可视区附近"会一次性圈进十几页，白白解码一堆马上要丢的位图。
                  display: 'block',
                  width: '100%',
                  aspectRatio: '1 / 1.414',
                  background: 'var(--dsw-alias-bg-layer-2, #fff)',
                  boxShadow: '0 1px 5px rgba(0, 0, 0, 0.16)',
                  transform: 'translateZ(0)',
                }}
              />
            ))}
          </div>
        )}
        </div>
      </div>

      {/*
        底部常驻工具栏（2026-09-16 用户需求）：与顶部栏**同构**（同一条 border、
        同样常驻，不随 PDF 滚动消失——它在滚动容器之外，是 flex 列的最后一格）。
        承载：单页/连续 模式切换 · 10%–500% 拖动式缩放滑块 · 向上弹出的浏览比例下拉。
      */}
      <div style={$bottomBar}>
        <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>翻页</span>
        {/* 单页 / 连续：互斥的模式切换（两个按钮一组，选中态描边高亮）。 */}
        <div style={$segGroup} role="group" aria-label="翻页模式">
          <button
            type="button"
            onClick={() => setPagingModeAndSync('single')}
            aria-pressed={pagingMode === 'single'}
            title="单页：一次只显示一页（◀ ▶ 翻页）"
            style={{ ...$segBtn, ...(pagingMode === 'single' ? $segBtnOn : {}) }}
          >
            ▭ 单页
          </button>
          <button
            type="button"
            onClick={() => setPagingModeAndSync('continuous')}
            aria-pressed={pagingMode === 'continuous'}
            title="连续：滚动连续浏览多页（默认）"
            style={{ ...$segBtn, ...(pagingMode === 'continuous' ? $segBtnOn : {}) }}
          >
            ☰ 连续
          </button>
        </div>

        <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11, marginLeft: 6 }}>缩放</span>
        {/* 拖动式缩放滑块：最左 = 10%（最小可读值，0% 会渲染成空白页——已与用户
            确认取 10%），最右 = 500%。拖动即退出自适应（zoomForManual）。 */}
        <input
          type="range"
          min={MANUAL_MIN_PERCENT}
          max={MANUAL_MAX_PERCENT}
          step={5}
          value={sliderPercent}
          onChange={(e) => applyManualZoom(Number(e.target.value))}
          disabled={load.status !== 'ready' || viewMode !== 'pdf'}
          aria-label="缩放百分比"
          title={`缩放 ${sliderPercent}%（拖动即退出自适应；最左 ${MANUAL_MIN_PERCENT}%、最右 ${MANUAL_MAX_PERCENT}%）`}
          style={$zoomSlider}
        />
        {/* 浏览比例：**向上**弹出的自定义下拉（原生 select 的方向由浏览器决定，
            不能保证向上），最下方一项固定是「自适应窗口」。 */}
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            onClick={(e) => toggleZoomMenu(e.currentTarget)}
            disabled={load.status !== 'ready' || viewMode !== 'pdf'}
            aria-haspopup="listbox"
            aria-expanded={zoomMenuOpen}
            title="浏览比例（弹层向上展开，最下方是「自适应窗口」）"
            style={{ ...$btnStyle, minWidth: 92, textAlign: 'left', display: 'inline-flex', alignItems: 'center', gap: 4 }}
          >
            <span style={{ flex: 1 }}>
              {zoom.source === 'autoFit' ? '自适应窗口' : `${zoomView.percent}%`}
            </span>
            <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 9 }}>
              {zoom.source === 'autoFit' ? `≈${zoomView.percent}%` : ''} ▲
            </span>
          </button>
          {zoomMenuOpen && zoomAnchor !== null && typeof document !== 'undefined' && createPortal(
            <>
              {/* 点空白处即收起（透明遮罩，不吃滚动容器的交互——滚动自行关闭）。 */}
              <div
                onClick={() => setZoomMenuOpen(false)}
                style={{ position: 'fixed', inset: 0, zIndex: 8990, background: 'transparent' }}
              />
              <div
                role="listbox"
                aria-label="浏览比例"
                style={{
                  position: 'fixed',
                  // **向上弹**：菜单底边贴在按钮顶边上方 4px。
                  left: zoomAnchor.left,
                  bottom: Math.max(4, (typeof window === 'undefined' ? 0 : window.innerHeight)
                    - zoomAnchor.bottom + 4),
                  width: Math.max(zoomAnchor.width, 112),
                  maxHeight: 260,
                  overflowY: 'auto',
                  zIndex: 9000,
                  background: 'var(--dsw-alias-bg-layer-1, #fff)',
                  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
                  borderRadius: 6,
                  boxShadow: '0 -6px 20px rgba(0,0,0,0.22)',
                  padding: 4,
                }}
              >
                {ZOOM_PRESET_PERCENTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    role="option"
                    aria-selected={zoom.source === 'manual' && zoomView.percent === p}
                    onClick={() => applyManualZoom(p)}
                    style={{
                      ...$zoomMenuItem,
                      ...(zoom.source === 'manual' && zoomView.percent === p ? $zoomMenuItemOn : {}),
                    }}
                  >
                    {p}%
                  </button>
                ))}
                <div style={{ height: 1, background: 'var(--dsw-alias-border-l1, #eee)', margin: '4px 2px' }} />
                {/* 最下方一项：自适应窗口（默认状态）。 */}
                <button
                  type="button"
                  role="option"
                  aria-selected={zoom.source === 'autoFit'}
                  onClick={applyAutoZoom}
                  title="按窗口宽度自适应（默认；选中后窗口变化会重新计算缩放）"
                  style={{
                    ...$zoomMenuItem,
                    ...(zoom.source === 'autoFit' ? $zoomMenuItemOn : {}),
                  }}
                >
                  🪟 自适应窗口
                </button>
              </div>
            </>,
            document.body,
          )}
        </div>

        {/* 右侧：当前缩放的来由（自适应 / 手动）——用户一眼知道自己是否还在自适应。 */}
        <span style={{ marginLeft: 'auto', color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>
          {zoom.source === 'autoFit'
            ? '缩放：自适应窗口（随窗口变化）'
            : `缩放：手动 ${zoomView.percent}%（窗口变化不再改变）`}
        </span>
      </div>
    </div>
    {createPortal(
      <div
        style={{
          position: 'fixed',
          top: 0,
          bottom: 0,
          right: panelWidth,
          width: TOC_COLUMN_WIDTH,
          zIndex: 50,
          background: 'var(--dsw-alias-bg-layer-2, #fff)',
          boxShadow: '-2px 0 10px rgba(0, 0, 0, 0.18)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          opacity: showLeftCol ? 1 : 0,
          transform: showLeftCol ? 'translateX(0)' : 'translateX(-8px)',
          pointerEvents: showLeftCol ? 'auto' : 'none',
          transition: tocTransition,
        }}
      >
        {showLeftCol && (
          <div style={$tocColumnInner}>
            {/* 四宫格列头（2026-10-28）：两行×两个，宽度不增。
                第一行 📚文件目录 + 📖标题目录（附 ◀ 收起）；第二行 🔖收藏目录 + 🔍搜索。
                搜索 = 在**当前目录模式**内过滤（文件→分类树 / 收藏→夹树 / 标题→章节），
                点开在宫格下出现内联输入框。 */}
            <div style={$tocColumnHeader}>
              <button
                type="button"
                style={{ ...$modeBtn, ...(leftMode === 'files' ? $modeBtnOn : {}) }}
                onClick={() => { leftModeTouchedRef.current = true; setLeftMode('files') }}
                title="库内文档分类（点文档打开）"
              >
                📚 文件目录
              </button>
              <button
                type="button"
                style={{ ...$modeBtn, ...(leftMode === 'toc' ? $modeBtnOn : {}) }}
                onClick={() => { leftModeTouchedRef.current = true; setLeftMode('toc') }}
                title="当前文档的章/小节目录（点击跳页）"
              >
                📖 标题目录
              </button>
              {/* idle（无文档）时 ◀ 不显示：目录列是唯一入口，收起它 = 空屏。 */}
              {load.status !== 'idle' && (
                <button
                  type="button"
                  style={$tocCollapseBtn}
                  onClick={() => { setLeftMode('toc'); toggleToc(false) }}
                  title="收起目录（回到纯 PDF 全宽）"
                >◀</button>
              )}
              <button
                type="button"
                style={{ ...$modeBtn, ...(leftMode === 'bookmarks' ? $modeBtnOn : {}) }}
                onClick={() => { leftModeTouchedRef.current = true; setLeftMode('bookmarks') }}
                title="收藏夹目录（收藏管理 + 夹内提问）"
              >
                🔖 收藏目录
              </button>
              <button
                type="button"
                style={{ ...$modeBtn, ...(searchOpen ? $modeBtnOn : {}) }}
                onClick={() => { setSearchOpen((s) => !s); if (searchOpen) setDirQuery('') }}
                title={leftMode === 'toc'
                  ? '在标题目录内搜索章/小节'
                  : leftMode === 'files'
                    ? '在文件目录内搜索标准号/名称'
                    : '在收藏目录内搜索夹名/标准号/标准名/条款号'}
              >
                🔍 搜索{dirQuery.trim() !== '' ? '·' : ''}
              </button>
            </div>
            {searchOpen && (
              <div style={$dirSearchRow}>
                <input
                  value={dirQuery}
                  onChange={(e) => setDirQuery(e.target.value)}
                  placeholder={leftMode === 'toc'
                    ? '🔍 搜索章/小节（编号/标题/页码）'
                    : leftMode === 'files'
                      ? '🔍 搜索标准号/名称'
                      : '🔍 搜索夹名/标准号/标准名/条款号'}
                  autoFocus
                  style={$dirSearchInput}
                />
                {dirQuery.length > 0 && (
                  <button type="button" onClick={() => setDirQuery('')} style={$dirSearchClear} title="清空">×</button>
                )}
              </div>
            )}
            {leftMode === 'files' ? (
              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <KsFilesView active={showLeftCol} onOpenDoc={onFilesOpenDoc} query={dirQuery} onQueryChange={setDirQuery} />
              </div>
            ) : leftMode === 'bookmarks' ? (
              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <KsBookmarksView active={showLeftCol} sessionId={sessionId ?? null} onOpenEvidence={onBookmarkJump} query={dirQuery} />
              </div>
            ) : (
              <div style={$tocList}>
                {loadedDocId === null && load.status !== 'loading' ? (
                  <div style={{ ...$tocHint, textAlign: 'center', paddingTop: 18 }}>
                    {load.status === 'idle'
                      ? '尚未打开文档——从 📚 文件目录 或 🔖 收藏目录 点一个国标开始阅读'
                      : '当前文档没有章/小节目录'}
                  </div>
                ) : toc === null ? (
                  <div style={$tocHint}>加载中…</div>
                ) : (tocFiltered ?? []).length === 0 ? (
                  <div style={{ ...$tocHint, textAlign: 'center', paddingTop: 18 }}>
                    没有匹配「{dirQuery.trim()}」的章/小节
                  </div>
                ) : (
                  (tocFiltered ?? []).map((t) => {
                    const no = tocNoClause(t)
                    const tt = tocTitleSplitClause(t)
                    const lvl1 = t.level === 1
                    return (
                      <div
                        key={(t.clause_number ?? '') + '|' + (t.title ?? '') + '|' + (t.page_start ?? '')}
                        onClick={() => tocJump(t)}
                        style={{ ...$tocItem, ...(lvl1 ? $tocItemL1 : $tocItemL2) }}
                        title={t.page_start != null ? `跳至 第${t.page_start}页` : '无页码'}
                      >
                        {tt.hidden ? <span style={{ display: 'none' }}>{tt.hidden}</span> : null}
                        <span style={$tocNo}>{t.clause_number || no}</span>
                        <span style={$tocTitle}>{tt.rest.slice(0, 24)}</span>
                        <span style={$tocPage}>p{t.page_start ?? '?'}</span>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        )}
      </div>,
      document.body,
    )}
    </>
  )
}

// ---- TOC 标题处理 helpers (照原项目 App.tsx :1183-1206 / renderHelpers.tsx) ----

/** 从目录条目提取编号：优先 clause_number，缺省则从标题开头抓 "N" 或 "N.N"。 */
function tocNoClause(t: KsClause): string {
  if (t.clause_number) return t.clause_number.trim()
  const m = (t.title ?? '').match(/^(\d{1,2}(?:\.\d{1,2})?)(?:\s+|(?=[\u4e00-\u9fff（(《]))/)
  return m ? m[1] : ''
}

function escDupNoLocal(no: string): string {
  return no.split('').map((c, i) => {
    const esc = c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return i < no.length - 1 ? esc + '\\s*' : esc
  }).join('')
}

/** 判定 text 是否以编号 no 开头（返回编号段 match，不匹配返回 null）。 */
function dupNoMatchesLocal(text: string | null | undefined, no: string | null | undefined): RegExpMatchArray | null {
  if (!no || !text) return null
  return text.trim().match(new RegExp('^(' + escDupNoLocal(no) + ')(?![\\d.])'))
}

/** 标题去重（App.tsx :1188-1197）：书签/标题自带条款号 → 已被编号徽章渲染，
 *  重复前缀用 display:none 包住（不硬删字符）；编号不一致 → 原样完整展示。 */
function tocTitleSplitClause(t: KsClause): { hidden: string; rest: string } {
  const no = tocNoClause(t)
  const title = (t.title ?? '').trim()
  const m = dupNoMatchesLocal(title, no)
  if (!m) return { hidden: '', rest: title }
  return { hidden: m[1], rest: title.slice(m[1].length).trimStart() || title }
}

// ---- small inline styles -------------------------------------------------

const $center: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  minHeight: 160,
}

const $btnStyle: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '2px 8px',
  cursor: 'pointer',
}

const $inputStyle: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  padding: '2px 4px',
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
}

// ---- 底部常驻工具栏（2026-09-16 用户需求）----
/** 与顶部栏同构：同一条上边框、同样常驻（在滚动容器之外，不随 PDF 滚动消失）。 */
const $bottomBar: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 10px',
  borderTop: '1px solid var(--dsw-alias-border-l1, #eee)',
  flexWrap: 'wrap',
  flexShrink: 0,
}

/** 单页/连续 的互斥分段控件容器。 */
const $segGroup: React.CSSProperties = {
  display: 'inline-flex',
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  overflow: 'hidden',
}

const $segBtn: React.CSSProperties = {
  border: 'none',
  borderRight: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  padding: '2px 8px',
  cursor: 'pointer',
  fontSize: 12,
}

/** 选中的那一半：描边高亮 + 淡底（与顶栏「目录」按钮的选中态同一套色）。 */
const $segBtnOn: React.CSSProperties = {
  background: 'var(--dsw-alias-bg-layer-1, #eef4ff)',
  color: 'var(--dsw-alias-link, #1565c0)',
  fontWeight: 600,
}

/** 拖动式缩放滑块：占满中间可伸缩空间，最左 10% / 最右 500%（见 pdfFit）。 */
const $zoomSlider: React.CSSProperties = {
  flex: 1,
  minWidth: 90,
  maxWidth: 280,
  height: 18,
  cursor: 'pointer',
}

/** 浏览比例下拉的菜单项（浮层向上弹出，见底部栏的 createPortal）。 */
const $zoomMenuItem: React.CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  border: 'none',
  background: 'transparent',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '4px 8px',
  cursor: 'pointer',
  fontSize: 12,
}

const $zoomMenuItemOn: React.CSSProperties = {
  background: 'var(--dsw-alias-bg-layer-1, #eef4ff)',
  color: 'var(--dsw-alias-link, #1565c0)',
  fontWeight: 600,
}

// 选夹菜单的夹选项按钮（横向：名称 + 右侧计数徽标）
const $folderOpt: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 6,
  padding: '6px 10px',
  cursor: 'pointer',
  fontSize: 12,
  textAlign: 'left',
  width: '100%',
}

const $btnPrimary: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '4px 14px',
  cursor: 'pointer',
}

// 条款收藏竖排按钮（页面左边注带：宽 16，文字竖排，与箭头左右分离）
const $bmFloatWidth = 16
const $bmFloatHeight = 72
const $bmFloatStyle: React.CSSProperties = {
  fontSize: 11,
  lineHeight: 1.3,
  width: $bmFloatWidth,
  height: $bmFloatHeight,
  writingMode: 'vertical-rl',
  textOrientation: 'mixed',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid rgba(200, 200, 200, 0.7)',
  background: 'rgba(255, 255, 255, 0.9)',
  color: '#1565c0',
  borderRadius: 4,
  padding: '3px 1px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
}

const $bmDoneStyle: React.CSSProperties = {
  color: '#fff',
  background: 'rgba(184, 134, 11, 0.92)',
  borderColor: 'rgba(184, 134, 11, 0.92)',
}

// 目录列经 createPortal 挂到 document.body（内联样式见返回处），这里只留内容容器。

/**
 * 目录列滑入/滑出过渡：只用 transform + opacity（合成器属性，不触发布局/重绘），
 * 与 PDF 完全无关，因此不存在"锁步""黑闪"问题。
 */
const $tocSlideTransition = 'transform var(--ds-transition-duration-slow, 0.3s) var(--ds-ease-in-out, cubic-bezier(0.4, 0, 0.2, 1)), opacity var(--ds-transition-duration, 0.2s) var(--ds-ease-in-out, cubic-bezier(0.4, 0, 0.2, 1))'
/** 内容容器固定最终宽度：动画期间只被外层裁剪，避免文字重折行。 */
const $tocColumnInner: React.CSSProperties = {
  width: TOC_COLUMN_WIDTH,
  minWidth: TOC_COLUMN_WIDTH,
  flex: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
}

const $tocColumnHeader: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  // 四宫格（2026-10-28）：第一行 文件+标题(+◀)，第二行 收藏+搜索。
  // wrap + 每钮 flexBasis 50% → 两个一行；◀ 不参与折行（窄按钮跟在第一行尾）。
  flexWrap: 'wrap',
  gap: 4,
  padding: '6px 8px',
  borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)',
}

const $tocCollapseBtn: React.CSSProperties = {
  marginLeft: 'auto',
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  color: 'var(--dsw-alias-label-secondary, #666)',
  borderRadius: 4,
  padding: '2px 6px',
  cursor: 'pointer',
  fontSize: 11,
  whiteSpace: 'nowrap',
}

const $tocList: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '6px 4px',
}

const $tocHint: React.CSSProperties = {
  padding: '4px 8px',
  fontSize: 11,
  color: 'var(--dsw-alias-label-tertiary, #999)',
}

const $tocItem: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: '2px 4px',
  fontSize: 11.5,
  cursor: 'pointer',
  borderRadius: 4,
  alignItems: 'center',
  lineHeight: 1.4,
  color: 'var(--dsw-alias-label-secondary, #666)',
}

const $tocItemL1: React.CSSProperties = {
  fontWeight: 700,
  color: 'var(--dsw-alias-label-primary, #111)',
  marginTop: 2,
}

const $tocItemL2: React.CSSProperties = {
  paddingLeft: 10,
  fontWeight: 400,
}

const $tocNo: React.CSSProperties = {
  color: 'var(--dsw-alias-link, #1565c0)',
  fontWeight: 600,
  fontVariantNumeric: 'tabular-nums',
  whiteSpace: 'nowrap',
  minWidth: 'auto',
}

const $tocTitle: React.CSSProperties = {
  color: 'var(--dsw-alias-label-secondary, #666)',
  flex: 1,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  fontSize: 11.5,
}

const $tocPage: React.CSSProperties = {
  color: 'var(--dsw-alias-label-tertiary, #999)',
  fontSize: 10.5,
  fontVariantNumeric: 'tabular-nums',
  whiteSpace: 'nowrap',
}

const $tocBtnStyle: React.CSSProperties = {
  color: 'var(--dsw-alias-link, #1565c0)',
  borderColor: 'var(--dsw-alias-link, #1565c0)',
}

// 目录四宫格模式按钮（2026-10-28）：flexBasis 50% → 头部两行各两个，列宽不增。
const $modeBtn: React.CSSProperties = {
  flex: '1 1 46%',
  border: '1px solid transparent',
  background: 'transparent',
  color: 'var(--dsw-alias-label-secondary, #666)',
  borderRadius: 4,
  padding: '3px 6px',
  cursor: 'pointer',
  fontSize: 11,
  whiteSpace: 'nowrap',
  textAlign: 'center',
}

const $modeBtnOn: React.CSSProperties = {
  color: 'var(--dsw-alias-label-primary, #111)',
  background: 'var(--dsw-alias-interactive-bg-active, #e8f0fe)',
  fontWeight: 600,
}

// 四宫格下的内联搜索行（🔍 展开时出现在宫格与列表之间）。
const $dirSearchRow: React.CSSProperties = {
  position: 'relative',
  padding: '0 8px 6px',
}

const $dirSearchInput: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  padding: '4px 20px 4px 8px',
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  fontSize: 12,
  outline: 'none',
}

const $dirSearchClear: React.CSSProperties = {
  position: 'absolute',
  right: 12,
  top: '50%',
  transform: 'translateY(-50%)',
  border: 'none',
  background: 'transparent',
  color: 'var(--dsw-alias-label-tertiary, #999)',
  cursor: 'pointer',
  fontSize: 14,
  lineHeight: 1,
  padding: '0 4px',
  fontWeight: 600,
}
