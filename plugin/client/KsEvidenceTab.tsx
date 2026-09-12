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
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import * as pdfjs from 'pdfjs-dist'
import { createPortal } from 'react-dom'
import type { PDFDocumentProxy } from 'pdfjs-dist'

import type { TabComponentProps } from 'dsh-better-sidebar/client/service'
import {
  EngineAuthError,
  addBookmark,
  addDocBookmark,
  clearSession,
  fetchBbox,
  fetchBookmarks,
  fetchClauseMeta,
  fetchDocTree,
  fetchPdf,
  fetchSession,
  removeBookmarkByClauseKey,
  removeDocBookmarkByDoc,
  type KsBookmark,
  type KsClause,
} from './api'
import { configurePdfWorker, PDF_WASM_DIR } from './pdf-configure'
import { backingStoreDpr, fitPageScale, PAGE_PADDING } from './pdfFit'
import {
  restorePanelAfterPdf,
  TOC_COLUMN_WIDTH,
  widenPanelForPdf,
} from './pdfPanel'
import { KsFilesView } from './KsFilesTab'
import {
  evidenceUrlOf,
  KS_EVIDENCE_TAB_ID,
  nextEvidenceClick,
  parseEvidence,
  type KsEvidence,
} from './ksEvidence'

type LoadState =
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


export function KsEvidenceTab(props: TabComponentProps): JSX.Element {
  const { ctx, tab, visible, store, scope } = props
  /** 侧栏宽度让位/恢复按会话记账（见 pdfPanel.ts）。 */
  const sessionId = (scope as { sessionId?: string } | undefined)?.sessionId

  // 「法规标准知识库」设置：是否显示红箭头（settings.pluginSettings['ks:settings'].showArrow）。
  // 响应式订阅 shared side-card prefs（store.subscribe）——设置页改了这个键，
  // 本组件随即重渲染，开关即时生效。缺省开。
  const showArrowPref = useSyncExternalStore(
    useCallback((cb: () => void) => store?.subscribe(cb) ?? (() => {}), [store]),
    () => {
      try {
        const blob = store?.getSnapshot().prefs.pluginSettings?.['ks:settings'] as Record<string, unknown> | undefined
        return (blob?.showArrow as boolean | undefined) !== false
      } catch {
        return true
      }
    },
  )
  // 供 useCallback([]) 的 renderPage 读取（闭包锁首值问题 → 用 ref 存当前偏好）
  const showArrowRef = useRef<boolean>(true)
  showArrowRef.current = showArrowPref

  // 侧栏面板当前宽度（CSS px）：目录列经 portal 固定在"面板左缘向左"的位置；
  // 面板右锚定 → 左缘 = right: panelWidth。面板宽会随"打开文档让位"变化，
  // 用 useSyncExternalStore 订阅，让目录列始终紧跟面板左缘。
  const panelWidth = useSyncExternalStore(
    useCallback((cb: () => void) => store?.subscribe(cb) ?? (() => {}), [store]),
    () => {
      try {
        const w = store?.getSnapshot?.().state?.width
        return typeof w === 'number' && Number.isFinite(w) ? w : 0
      } catch {
        return 0
      }
    },
  )

  const evidence = useRef<KsEvidence | null>(EMPTY_EVIDENCE)
  const pdfDocRef = useRef<PDFDocumentProxy | null>(null)
  const taskRef = useRef<pdfjs.RenderTask | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const bboxRef = useRef<HTMLDivElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  /** 绘制世代号：过期的一帧在 await 返回后自行退出（见 renderPage）。 */
  const renderSeqRef = useRef(0)
  /** 最近一次**成功**绘制所用的 (页, 缩放, dpr)——用于抖动抑制。 */
  const lastFitRef = useRef<{ page: number; scale: number; dpr: number } | null>(null)
  /** 几何冻结截止时间（ms epoch）：我们自己发起的布局动画期间不重绘。 */
  const renderFreezeUntilRef = useRef(0)
  /** 冻结期间是否发生过"想重绘"——冻结结束后补测一次。 */
  const pendingRenderRef = useRef(false)
  const freezeTimerRef = useRef<number | null>(null)
  /** 增强③-B: 去重历史 + 当前载入的原始 href（parse 前存的）。 */
  const historyRef = useRef<HistoryEntry[]>([])
  const pathHrefRef = useRef<string | null>(null)

  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
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
  const [leftMode, setLeftMode] = useState<'toc' | 'files'>('toc')

  /**
   * Render one page of the loaded PDF to the canvas, filling the container
   * (纵向拉满优先，见 pdfFit.ts)，and overlay the bbox (if present) as a red
   * arrow. 尺寸每次都现读容器（不用缓存值），窗口最大化/侧栏拖宽/浏览器缩放
   * 都通过下方测量 effect 触发重绘。
   */
  const renderPage = useCallback(async (doc: PDFDocumentProxy, target: number) => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (canvas === null || container === null) return
    const ctx = canvas.getContext('2d')
    if (ctx === null) return

    // 同一 canvas 上并发 render 会抛 "Cannot use the same canvas during
    // multiple render() operations"（翻页快连点 + 尺寸变化同时发生时必现）。
    // cancel() 只作用于**已登记**的 task；上一帧若还停在 getPage 的 await 里，
    // taskRef 仍是 null——所以再加世代号，让过期帧在 await 返回后自行退出。
    if (taskRef.current !== null) {
      try { taskRef.current.cancel() } catch { /* ignore */ }
      taskRef.current = null
    }
    const seq = ++renderSeqRef.current

    const clamped = Math.max(1, Math.min(target, doc.numPages))
    const pdfPage = await doc.getPage(clamped)
    if (seq !== renderSeqRef.current) return

    // 铺满容器（带横向溢出预算，见 pdfFit.ts）：侧栏够宽时纵向拉满。
    const base = pdfPage.getViewport({ scale: 1 })
    const fit = fitPageScale({
      availWidth: container.clientWidth - PAGE_PADDING,
      availHeight: container.clientHeight - PAGE_PADDING,
      pageWidth: base.width,
      pageHeight: base.height,
    })
    // 容器还没布局（tab 隐藏 / 0 尺寸）→ 本次不画，等测量 effect 重触发。
    if (fit === null) return
    const viewport = pdfPage.getViewport({ scale: fit.scale })
    const dpr = backingStoreDpr(
      viewport.width, viewport.height,
      typeof window !== 'undefined' ? window.devicePixelRatio : 1,
    )

    const last = lastFitRef.current

    // 几何冻结（用户 2026-09-09：「目录弹出的时候 PDF 界面会黑一下」）：
    // canvas 的尺寸赋值会**先把画布清空**，真重绘要几十到几百毫秒——所以只要在
    // 我们自己发起的几何动画（目录列 0↔190、面板 ±190 的 0.3s 过渡）期间发生了
    // 一次重绘，用户就会先看到一块黑底再看到页面。而 0/190 与 ±190 两段过渡
    // 即便同参同帧启动，采样点落在动画中段时容器仍可能瞬时差出 190px（比例 >3%
    // 会穿透下面的死区）。故：动画期间**只标记待办、不重绘**，冻结结束后补测一次
    // ——尺寸真变了才画，没变就什么都不做（这才是"无感"）。
    if (Date.now() < renderFreezeUntilRef.current && last !== null && last.page === clamped) {
      pendingRenderRef.current = true
      return
    }

    // 抖动抑制：同页 + 同 dpr + 缩放变化 < 3% → 跳过重绘。滚动条出现/消失会改变
    // clientWidth/Height，在"页面刚好略超容器"的边界上会自激成无限重绘循环；
    // 测量侧的 SCROLLBAR_NOISE_PX 已挡住主要来源，这里是第二道闸。
    // dpr 不同则必须重绘——否则跨屏/缩放后 canvas 停在旧 dpr 上（发糊），
    // 而这种情况尺度往往没变，会被缩放死区误吞。
    if (last !== null && last.page === clamped && last.dpr === dpr
      && Math.abs(fit.scale - last.scale) / last.scale < SCALE_EPSILON) {
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
    taskRef.current = task
    try {
      await task.promise
    } catch (error) {
      // 被下一次绘制取消 = 正常路径（不是错误），静默返回。
      if (error instanceof Error && error.name === 'RenderingCancelledException') return
      // 渲染真失败：canvas 已被上面的尺寸赋值清空，必须让后续同尺寸重试能进来
      // （否则死区会把重试也吃掉 → 永久空白），并把失败暴露到界面上。
      lastFitRef.current = null
      setEngineHint(`渲染失败：${error instanceof Error ? error.message : String(error)}（可切页/重试）`)
      throw error
    }
    // 本帧已被更新的请求取代 → 不要记录缩放、也不要画箭头（否则旧帧的
    // setArrowPos 会覆盖新帧的箭头位置）。
    if (seq !== renderSeqRef.current) return
    // 只在**成功**绘制后记录，这样被取消的那一帧不会污染抖动抑制的死区。
    lastFitRef.current = { page: clamped, scale: fit.scale, dpr }

    // Draw the red arrow marker at the anchor row's left edge (CSS-pixel
    // space, aligned with the canvas box). The arrow points right INTO the
    // cited row and is about one text line tall. Shown only when the rendered
    // page is the evidence's target page.
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
  }, [])

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
    // 打开文档即让位（用户 2026-09-09）：点证据链接/从文件目录打开文档 →
    // 立刻把侧栏拉到"文档友好宽度"，保证 PDF 可读；宽度会在关闭本 tab 时
    // 由卸载 effect 恢复。store 不可写时静默降级（PDF 仍按当前宽度铺满）。
    widenPanelForPdf(store, sessionId)
    // 这次让位同样是一段 0.3s 宽度过渡 → 期间冻结重绘，等它停稳再按最终尺寸画一次。
    freezeRender(settleMsRef.current + 60)
    // Abort anything in flight.
    abortRef.current?.abort()
    if (taskRef.current !== null) {
      try { taskRef.current.cancel() } catch { /* ignore */ }
      taskRef.current = null
    }
    // 换文档/重载 → 抖动抑制的基准失效（新 PDF 页尺寸可能不同），清零。
    lastFitRef.current = null
    renderSeqRef.current += 1
    const controller = new AbortController()
    abortRef.current = controller
    setLoad({ status: 'loading' })
    setEngineHint('')

    if (ev === null) {
      setLoad({ status: 'error', message: '无效的证据链接：缺少 doc 参数' })
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
    if (ev !== null) {
      setPageInput(String(ev.page ?? 1))
      // Cosmetic: better-sidebar's builtin openTab sets a hostname-derived title
      // ("127.0.0.1") for a claimed URL. Refine it to a user-friendly page label.
      const label = `PDF 查看器${ev.page !== undefined ? ` · 第${ev.page}页` : ''}`
      try { ctx.betterSidebar?.updateTab?.(tab.id, { title: label }) } catch { /* ignore */ }
    }
    void loadEvidence(ev)
    return () => {
      abortRef.current?.abort()
      if (taskRef.current !== null) {
        try { taskRef.current.cancel() } catch { /* ignore */ }
      }
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
  const showLeftCol = leftMode === 'files' || (tocOpen && docHasToc)

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
  // 卸载：切会话/面板重挂载也会卸载组件，但 tab 还活着（store.tabOpen 为真），
  // 那种情况必须保留宽度。恢复与让位都在 pdfPanel 模块级 Map 里配对（幂等）。
  useEffect(() => {
    return () => {
      let stillOpen = true
      try {
        stillOpen = sessionId === undefined ? true : store.tabOpen(sessionId, tab.id)
      } catch {
        stillOpen = true // 探不到状态就当作"仍打开"，绝不误改用户宽度
      }
      if (!stillOpen) restorePanelAfterPdf(store, sessionId)
    }
    // 只在卸载时执行一次：store/tab.id/sessionId 对一个 tab 实例是稳定的。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 首绘/翻页/尺寸变化/DPI 变化统一由本 effect 驱动：canvas 挂载完成（ready）
  // 后再画，避免"canvas 尚未存在就渲染"的空白。page 变化 → 重绘；box 变化 →
  // 按新尺寸重绘；dprEpoch 变化 → 按新 dpr 重绘（清晰度）；visible 变化 →
  // 隐藏时不画，重新可见时补画。
  useEffect(() => {
    if (load.status !== 'ready') return
    if (!visible) return
    const doc = pdfDocRef.current
    if (doc === null || canvasRef.current === null) return
    void renderPage(doc, page).catch((error) => {
      // 2026-09-05：曾因 pdfjs 方法名写错（convertToViewPoint）在此被静默吞掉
      // 数月无感 → 至少留痕，避免渲染层错误继续隐身。
      console.warn('[ks:pdf] renderPage failed', error)
    })
  }, [load.status, page, renderPage, showLeftCol, showArrowPref, box, dprEpoch, visible])

  // Page navigation.（只改状态；实际绘制由上方 effect 触发）
  const goTo = useCallback((n: number) => {
    const doc = pdfDocRef.current
    if (doc === null) return
    const target = Math.max(1, Math.min(n, doc.numPages))
    setPage(target)
    setPageInput(String(target))
  }, [])

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

  const retry = useCallback(() => {
    clearSession()
    void loadEvidence(evidence.current)
  }, [loadEvidence])

  /** 增强③-B: 从历史跳到某条证据（沿用现有 [tab.path, tab.meta] effect 重载）。 */
  const jumpHistory = useCallback((href: HistoryEntry) => {
    const title = `PDF 查看器${href.ev.page !== undefined ? ` · 第${href.ev.page}页` : ''}`
    if (href.url) {
      try {
        // meta 带共享单调 nonce：即便 path 与上次相同，tab.meta 引用也变化 →
        // [tab.path, tab.meta] effect 必然触发重载跳页。
        ctx.betterSidebar?.updateTab?.(tab.id, {
          path: href.url,
          title,
          meta: { ksClick: nextEvidenceClick() },
        })
        return
      } catch { /* updateTab 失败 → 下方本地重载兜底 */ }
    }
    // 拿不到 URL（异常态）：本地直接重载，仍能跳页。
    evidence.current = href.ev
    void loadEvidence(href.ev)
  }, [ctx, tab.id, loadEvidence])

  /** 顶部按钮：收藏/取消收藏本标准（toggle）。需要 doc_id——经 meta 端点取回
   *  （curDocId / docBookmarked 初始态也由 meta 提供）。失败显示在 engineHint。 */
  const toggleDocBookmark = useCallback(async () => {
    if (docBusy) return
    const docId = curDocId
    if (docId === null) return
    setDocBusy(true)
    setEngineHint('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      if (docBookmarked) {
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
      } else {
        try {
          await addDocBookmark(session.engine.port, docId, session.token, controller.signal)
        } catch (error) {
          if (error instanceof EngineAuthError) {
            session = await fetchSession(controller.signal)
            await addDocBookmark(session.engine.port, docId, session.token, controller.signal)
          } else {
            throw error
          }
        }
        setDocBookmarked(true)
        setEngineHint('已收藏本标准')
      }
    } catch (error) {
      if (controller.signal.aborted) return
      setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setDocBusy(false)
    }
  }, [docBusy, docBookmarked, curDocId])

  /** 竖排按钮：收藏/取消收藏本条款（toggle）。收藏经 meta 取 clause_key →
   *  POST；取消经 clause_key → DELETE by-clause。幂等。失败显示在 engineHint。 */
  const clauseBookmark = useCallback(async () => {
    const ev = evidence.current
    if (ev === null || ev.rev === undefined) return
    if (bmState === 'busy') return
    setBmState('busy')
    setEngineHint('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      // 取消：需要 clause_key（meta 里已预取 curClauseKey；保险起见仍可重取）
      if (bmState === 'done') {
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
        return
      }
      // 收藏：取 clause_key → add
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
      setCurClauseKey(meta.clause_key)
      try {
        await addBookmark(session.engine.port, meta.clause_key, session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          await addBookmark(session.engine.port, meta.clause_key, session.token, controller.signal)
        } else {
          throw error
        }
      }
      setBmState('done')
      setEngineHint('已收藏本条款')
      void refreshMetaRef.current?.(ev.rev)
    } catch (error) {
      if (controller.signal.aborted) return
      setBmState(bmState === 'done' ? 'done' : 'idle')
      setEngineHint(`操作失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }, [bmState, curClauseKey])

  const total = load.status === 'ready' ? load.pages : 0

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
    try {
      ctx.betterSidebar.openTab({ type: KS_EVIDENCE_TAB_ID, url, title })
      ctx.betterSidebar?.updateTab?.(tab.id, {
        path: url,
        title,
        meta: { ksClick: nextEvidenceClick() },
      })
    } catch { /* ignore */ }
  }, [ctx, tab.id])

  // 下拉项标签：条款号 + 页（同页多条也能区分）
  const bookmarkOptionLabel = (b: KsBookmark): string => {
    const no = typeof b.clause_number === 'string' && b.clause_number.length > 0 ? b.clause_number : '?'
    const pg = typeof b.page_start === 'number' && b.page_start >= 1 ? b.page_start : '?'
    return `§${no} · 第${pg}页`
  }

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
          标题目录（B）：PDF ready 且本文档有目录 → 显示收起/展开切换。
          收起后回到纯 PDF 全宽（列隐藏）；再点重新展开。无目录(空树/加载失败)时禁用。
        */}
        {load.status === 'ready' && (
          <button
            type="button"
            disabled={toc === null || toc.length === 0}
            onClick={() => toggleToc(!tocOpen)}
            title={tocOpen
              ? '收起标题目录（收回侧栏宽度）'
              : '展开标题目录：侧栏向左扩张，不压缩 PDF 阅读区'}
            style={{ ...$btnStyle, ...(toc !== null && toc.length > 0 ? $tocBtnStyle : {}) }}
          >
            📖 标题目录{'\u00A0'}{toc !== null && toc.length > 0 ? (tocOpen ? '▾' : '▸') : '·'}
          </button>
        )}
        {load.status === 'ready' && (
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

      {/* body：右侧 canvas。目录列经 createPortal 挂到 document.body，浮在侧栏
          左侧的对话框区域上——不遮 PDF，也不被 .paneContent 的 overflow:hidden 裁掉。 */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <div ref={containerRef} style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: 12 }}>
        {load.status === 'loading' && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>载入证据 PDF…（首次可能启动引擎，需要数秒）</div>
          </div>
        )}
        {load.status === 'error' && (
          <div style={{ ...$center, flexDirection: 'column', gap: 10 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', maxWidth: 480, textAlign: 'center', wordBreak: 'break-word' }}>
              {load.message}
            </div>
            <button type="button" onClick={retry} style={$btnPrimary}>重试</button>
          </div>
        )}
        {load.status === 'ready' && (
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
        </div>
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
            <div style={$tocColumnHeader}>
              <button
                type="button"
                style={{ ...$modeBtn, ...(leftMode === 'files' ? $modeBtnOn : {}) }}
                onClick={() => setLeftMode('files')}
                title="库内文档分类（点文档打开）"
              >
                📚 文件目录
              </button>
              <button
                type="button"
                style={{ ...$modeBtn, ...(leftMode === 'toc' ? $modeBtnOn : {}) }}
                onClick={() => setLeftMode('toc')}
                title="当前文档的章/小节目录（点击跳页）"
              >
                📖 标题目录
              </button>
              {leftMode === 'toc' && (
                <button type="button" style={$tocCollapseBtn} onClick={() => toggleToc(false)} title="收起目录（回到纯 PDF 全宽）">◀</button>
              )}
            </div>
            {leftMode === 'files' ? (
              <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <KsFilesView active={showLeftCol} onOpenDoc={onFilesOpenDoc} />
              </div>
            ) : (
              <div style={$tocList}>
                {toc === null ? (
                  <div style={$tocHint}>加载中…</div>
                ) : (
                  toc.map((t) => {
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
  gap: 6,
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

// 左列模式分段切换按钮（标题目录 ⇄ 文件目录）
const $modeBtn: React.CSSProperties = {
  flex: 1,
  border: '1px solid transparent',
  background: 'transparent',
  color: 'var(--dsw-alias-label-secondary, #666)',
  borderRadius: 4,
  padding: '2px 6px',
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
