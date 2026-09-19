/**
 * ks-dsh-plugin — client/KsDocTextView.tsx
 *
 * 文档正文视图（2026-09-13 端点接线）：KsEvidenceTab 的「正文」模式渲染面。
 *
 * 数据源：引擎 GET /api/v1/documents/{doc}/clauses（fetchDocClauses）——每条款
 * content_html 已由引擎注入三类占位：
 *   - <img class="fig-embed" data-fig="图号">          → /ks/doc-image figure
 *   - <img class="table-embed" data-page data-tbl>     → /ks/doc-image table-image
 *   - <span class="katex-formula" data-fno data-clause data-tex> → /ks/doc-image formula
 *     （KaTeX 未引入插件——正文视图对公式统一呈现**引擎原图截图**（同源 PNG），
 *      data-tex 留作 title 提示；正文文本兜底在截图 404 时自动还原。）
 *
 * 安全纪律（XSS）：content_html 是引擎自产 HTML，但入库链路多（OCR / DOCX /
 * 用户编辑补丁都汇进 content_markdown）——渲染前经 sanitizeDocHtml 结构白名单
 * 消毒：剥 script/style 等非白名单节点（保留子内容）与全部 on* 事件属性，
 * img src/srcset 直剥（占位接线只认 class+data-* 域，绝不直挂外链）。
 * 过滤不变量：元素属性过滤只发生在它被 pop 时（入栈路径有三——白名单孩子/
 * 剥壳上移孙节点/根——但过滤点唯一），保证剥壳上移的节点必被过滤。
 *
 * 图片懒接线：渲染后 effect 扫 img.fig-embed / img.table-embed /
 * span.katex-formula（class 域选择器——class 必须在白名单里存活）→
 * fetchDocImage（同源 host 代理）→ objectURL 填 src；404 → 隐藏该占位
 * （引擎契约「定位失败前端隐藏，无图文档零破图」）。
 */

import * as React from 'react'
import { useEffect, useMemo, useRef, useState } from 'react'

import {
  DOC_IMAGE_NOT_FOUND,
  fetchDocClauses,
  fetchDocImage,
  fetchSession,
  EngineAuthError,
  type KsDocClause,
} from './api'

/* ------------------------------------------------------------------ *
 * 1. HTML 消毒（结构白名单）
 * ------------------------------------------------------------------ */

/** 允许原样保留的标签（引擎自产 HTML 的实际集合 + 少量排版标签）。 */
const ALLOWED_TAGS = new Set([
  'p', 'br', 'b', 'strong', 'i', 'em', 'u', 'sub', 'sup', 'span',
  'div', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'caption',
  'img', 'figure', 'figcaption', 'blockquote', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre', 'code',
])

/** 每标签允许的属性白名单（data-* 前缀另行放行——占位标记全在 data- 域）。 */
const ALLOWED_ATTRS: Record<string, Set<string>> = {
  // class 必须保留：引擎占位标记（fig-embed/table-embed/katex-formula）都挂在
  // class 上，接线选择器按 class 命中（verifier P0-2：剥 class = 永不接线）。
  img: new Set(['alt', 'loading', 'class']),
  span: new Set(['class']),
  table: new Set(['class']),
  div: new Set(['class']),
  p: new Set(['class']),
  td: new Set(['colspan', 'rowspan']),
  th: new Set(['colspan', 'rowspan']),
}

/**
 * 结构白名单消毒 content_html。
 *
 * 在 <template> 里解析（不进文档流、不执行脚本），然后按白名单重建。
 *
 * verifier P0-1 修复：剥壳上移的子节点不在 children 快照里，旧实现"外层循环
 * 自然继续"不成立——上移的 <img onerror>/<a href=javascript:> 永不被属性过滤，
 * 直接进活文档（存储型 XSS）。现改为**待处理栈**：白名单节点就地过滤属性后
 * 子节点入栈；非白名单节点把子节点上移**并全部入栈**——每个节点必被访问
 * 一次，属性过滤无遗漏面。
 *
 * img.src / img.srcset 一律剥除（引擎占位本就无 src；将来带 src 的
 * content_html 一律走占位接线，绝不直挂——外链 src 是 XSS/外发信道）。
 * 非白名单标签**保留其子内容**（剥壳不剥内容——正文文字不能丢）。
 */
export function sanitizeDocHtml(html: string): string {
  const tpl = document.createElement('template')
  tpl.innerHTML = html
  const holder = document.createElement('div')
  holder.append(tpl.content)
  // 核心不变量：**一个元素的属性过滤只发生在它被 pop 的那一刻**——
  // 「过滤」与「入栈」解耦：入栈路径有三（白名单孩子 / 剥壳上移的孙节点 /
  // 根），但过滤点唯一（pop）。若把过滤放在「父节点循环里遇到 child」时做，
  // 剥壳上移的节点会错过父节点本轮 children 快照（上移发生在快照之后），
  // 而它 pop 出来时我们只遍历它的 children——自身属性永不被过滤（真实漏洞：
  // <unknown-tag><img onerror>…</unknown-tag> 剥壳后 onerror 存活）。
  const filterAttrs = (el: Element): void => {
    const tag = el.tagName.toLowerCase()
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase()
      // src/srcset 直剥（引擎占位本就无 src；外链 src 是 XSS/外发信道，
      // 且不落 data-ks-src 断头占位——占位接线只认 class+data-* 域）。
      if (tag === 'img' && (name === 'src' || name === 'srcset')) {
        el.removeAttribute(attr.name)
        continue
      }
      const keep = (ALLOWED_ATTRS[tag]?.has(name) ?? false)
        || (name.startsWith('data-') && name !== 'data-src')
      if (!keep) el.removeAttribute(attr.name)
    }
  }
  const stack: Element[] = [holder]
  while (stack.length > 0) {
    const node = stack.pop()
    if (node === undefined) continue
    // 过滤自身属性；root（holder）不在返回树里、无属性，过滤是 no-op。
    filterAttrs(node)
    // 快照当前 children：剥壳上移的新节点不进本轮 for，靠入栈保证访问。
    for (const child of Array.from(node.children)) {
      const tag = child.tagName.toLowerCase()
      if (ALLOWED_TAGS.has(tag)) {
        stack.push(child)
      } else {
        // 非白名单标签：子节点上移 + 入栈（pop 时过滤属性），然后剥壳。
        // 无 children 的危险标签（<script>/<style> 文本）随之丢弃。
        const parent = child.parentElement
        if (parent === null) continue
        for (const grandchild of Array.from(child.children)) {
          parent.insertBefore(grandchild, child)
          stack.push(grandchild)
        }
        // 非元素子节点（文本）也上移；script/style 的文本内容不留。
        if (tag !== 'script' && tag !== 'style') {
          while (child.firstChild !== null) {
            parent.insertBefore(child.firstChild, child)
          }
        }
        parent.removeChild(child)
      }
    }
  }
  return holder.innerHTML
}

/* ------------------------------------------------------------------ *
 * 2. 占位图接线 effect（fig-embed / table-embed / katex-formula）
 * ------------------------------------------------------------------ */

/** 给一个 DOM 占位元素算 fetchDocImage 参数。 */
function imageParamsOf(el: Element):
  { kind: 'figure' | 'formula' | 'table-image', no?: string, clause?: string, page?: number, tbl?: number } | null {
  if (el instanceof HTMLImageElement) {
    if (el.classList.contains('fig-embed')) {
      const no = el.getAttribute('data-fig')
      return no !== null && no.length > 0 ? { kind: 'figure', no } : null
    }
    if (el.classList.contains('table-embed')) {
      const pg = Number.parseInt(el.getAttribute('data-page') ?? '', 10)
      const tbl = Number.parseInt(el.getAttribute('data-tbl') ?? '', 10)
      return Number.isFinite(pg) && Number.isFinite(tbl)
        ? { kind: 'table-image', page: pg, tbl } : null
    }
    // 其他 img（asset-embed 等）暂不接线（assets 走 sha256 白名单端点，后续批次）。
    return null
  }
  if (el instanceof HTMLElement && el.classList.contains('katex-formula')) {
    const fno = el.getAttribute('data-fno')
    const clause = el.getAttribute('data-clause')
    return fno !== null && fno.length > 0 && clause !== null && clause.length > 0
      ? { kind: 'formula', no: fno, clause } : null
  }
  return null
}

/**
 * 扫描容器内全部占位 → fetchDocImage → objectURL 写 src。
 * 幂等：已接线（data-ks-done）跳过；404 → display:none（引擎契约）。
 * 返回清理函数：卸载时 revoke 本轮创建的全部 objectURL（含 aborted 早退分支
 * 里已创建未使用的 URL——verifier P2-11）。
 * objectURL/HTML 直写 DOM，不经 React 状态——无需进度回调。
 */
function wirePlaceholders(
  root: HTMLElement, docId: string, signal: AbortSignal,
): () => void {
  const urls: string[] = []
  const pending: Array<Promise<void>> = []
  const placeholders = root.querySelectorAll(
    'img.fig-embed, img.table-embed, span.katex-formula',
  )
  placeholders.forEach((el) => {
    if (el.getAttribute('data-ks-done') === '1') return
    const params = imageParamsOf(el)
    if (params === null) {
      el.setAttribute('data-ks-done', '1')
      return
    }
    el.setAttribute('data-ks-done', '1')   // 先占坑防并发重复接线
    pending.push((async () => {
      try {
        const got = await fetchDocImage(params.kind,
          { docId, no: params.no, clause: params.clause, page: params.page, tbl: params.tbl },
          144, signal)
        if (signal.aborted) {
          // abort 时 fetch 实际走 catch（此分支不可达的防御位）；真到此处，
          // 清理函数已同步跑完 revoke——就地撤销，绝不宣称后续登记。
          if (got !== DOC_IMAGE_NOT_FOUND) URL.revokeObjectURL(got.url)
          return
        }
        if (got === DOC_IMAGE_NOT_FOUND) {
          // 公式：截图缺失 → 保留原文本（span 自带线性公式内容），仅去占位样式。
          if (params.kind === 'formula') {
            el.classList.remove('katex-formula')
            return
          }
          el.setAttribute('data-ks-miss', '1')
          if (el instanceof HTMLElement) el.style.display = 'none'
          return
        }
        urls.push(got.url)
        if (el instanceof HTMLImageElement) {
          el.src = got.url
          el.style.maxWidth = '100%'
          el.style.height = 'auto'
        } else {
          // katex-formula span → 截图替换内容（保留 title=LaTeX 提示）。
          const img = document.createElement('img')
          img.src = got.url
          img.alt = el.textContent ?? ''
          img.style.maxWidth = '100%'
          img.style.verticalAlign = 'middle'
          el.replaceChildren(img)
        }
      } catch (error) {
        if (signal.aborted) return
        console.warn('[ks:text] doc-image wiring failed', params, error)
      }
    })())
  })
  return () => {
    for (const u of urls) URL.revokeObjectURL(u)
  }
}

/* ------------------------------------------------------------------ *
 * 3. 组件
 * ------------------------------------------------------------------ */

export interface KsDocTextViewProps {
  /** 当前文档 id（evidence.doc）。 */
  docId: string
  /** PDF 视图当前页——页块高亮锚点（联动）。 */
  currentPage: number
  /** 点击页块 → PDF 视图跳页（联动回写）。 */
  onJumpPage: (page: number) => void
}

type TextLoad =
  | { status: 'loading' }
  | { status: 'ready', clauses: KsDocClause[] }
  | { status: 'error', message: string }

export function KsDocTextView(props: KsDocTextViewProps): JSX.Element {
  const { docId, currentPage, onJumpPage } = props
  const [state, setState] = useState<TextLoad>({ status: 'loading' })
  const rootRef = useRef<HTMLDivElement | null>(null)

  // 数据加载：docId 变化重拉；401 重试一次（会话轮换）。
  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading' })
    void (async () => {
      let session
      try {
        session = await fetchSession(controller.signal)
      } catch (error) {
        if (controller.signal.aborted) return
        setState({ status: 'error', message: error instanceof Error ? error.message : String(error) })
        return
      }
      try {
        const clauses = await fetchDocClauses(
          session.engine.port, docId, session.token, controller.signal)
        if (controller.signal.aborted) return
        setState({ status: 'ready', clauses })
      } catch (error) {
        if (controller.signal.aborted) return
        if (error instanceof EngineAuthError) {
          try {
            const fresh = await fetchSession(controller.signal)
            const clauses = await fetchDocClauses(
              fresh.engine.port, docId, fresh.token, controller.signal)
            if (controller.signal.aborted) return
            setState({ status: 'ready', clauses })
            return
          } catch (error2) {
            if (controller.signal.aborted) return
            setState({ status: 'error', message: error2 instanceof Error ? error2.message : String(error2) })
            return
          }
        }
        setState({ status: 'error', message: error instanceof Error ? error.message : String(error) })
      }
    })()
    return () => { controller.abort() }
  }, [docId])

  // 渲染 + 占位接线：state.clauses 变化 → sanitize → innerHTML → wire。
  const renderedHtml = useMemo(
    () => (state.status === 'ready'
      ? state.clauses.map((c) => c.content_html ?? '').join('\n')
      : ''),
    [state],
  )
  useEffect(() => {
    if (state.status !== 'ready') return
    const root = rootRef.current
    if (root === null) return
    const controller = new AbortController()
    root.innerHTML = sanitizeDocHtml(renderedHtml)
    // 渲染后立即接线（占位已在 DOM）；abort + revoke 都在 cleanup。
    const revoke = wirePlaceholders(root, docId, controller.signal)
    return () => {
      controller.abort()
      revoke()
    }
  }, [renderedHtml, docId, state.status])

  // 按 page_start 聚合「页块」导航（与 PDF 翻页联动）。
  const pages = useMemo(() => {
    if (state.status !== 'ready') return [] as Array<{ page: number, items: KsDocClause[] }>
    const map = new Map<number, KsDocClause[]>()
    for (const c of state.clauses) {
      const pg = c.page_start
      if (pg === null || !Number.isFinite(pg) || pg < 1) continue
      const key = Math.floor(pg)
      const bucket = map.get(key)
      if (bucket !== undefined) bucket.push(c)
      else map.set(key, [c])
    }
    return Array.from(map.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([page, items]) => ({ page, items }))
  }, [state])

  if (state.status === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--dsw-alias-label-secondary, #666)' }}>
        载入正文条款…（首次可能启动引擎）
      </div>
    )
  }
  if (state.status === 'error') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--dsw-alias-state-error-primary)' }}>
        正文加载失败：{state.message}
      </div>
    )
  }

  const $pageNav: React.CSSProperties = {
    position: 'sticky', top: 0, zIndex: 1,
    display: 'flex', flexWrap: 'wrap', gap: 4,
    padding: '6px 10px',
    background: 'var(--dsw-alias-bg-layer-1, #fff)',
    borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)',
  }
  const $pageBtn = (active: boolean): React.CSSProperties => ({
    border: '1px solid var(--dsw-alias-border-l2, #ccc)',
    background: active ? 'var(--dsw-alias-link, #1565c0)' : 'transparent',
    color: active ? '#fff' : 'var(--dsw-alias-link, #1565c0)',
    borderRadius: 4, padding: '1px 8px', fontSize: 11, cursor: 'pointer',
  })

  return (
    <div style={{ height: '100%', overflow: 'auto', fontSize: 13, lineHeight: 1.75 }}>
      {/* 页块导航：点击跳 PDF 对应页（双向联动）；当前 PDF 页高亮。 */}
      {pages.length > 1 && (
        <div style={$pageNav}>
          {pages.map((p) => (
            <button
              key={p.page}
              type="button"
              style={$pageBtn(p.page === currentPage)}
              onClick={() => onJumpPage(p.page)}
              title={`第 ${p.page} 页 · ${p.items.length} 个条款`}
            >
              {p.page}
            </button>
          ))}
        </div>
      )}
      {/* 正文容器：engine HTML（已消毒）直挂。 */}
      <div
        ref={rootRef}
        style={{ padding: '10px 14px', maxWidth: 860 }}
        className="ks-doc-text"
      />
    </div>
  )
}
