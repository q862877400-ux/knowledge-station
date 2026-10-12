/**
 * ks-dsh-plugin — client/ksEvidence.ts
 *
 * The "evidence anchor" URL contract and its parser. This is shared by
 *   - the tab descriptor's `urlTarget` (claim the pseudo-evidence link), and
 *   - the tab component (parse { doc, page, bbox, rev } out of `tab.path`).
 *
 * Contract (see NOTES.md §link-format):
 *   http://127.0.0.1:1/__ks_evidence__?doc=<doc_id>&page=<n>&bbox=<x0,y0,x1,y1>&rev=<clause_revision_id>
 *   - doc  REQUIRED
 *   - page / bbox / rev  OPTIONAL
 *   - http(s) protocol, unreachable pseudo host (port 1). The GUI never
 *     navigates to it: better-sidebar's link interception claims it (via our
 *     urlTarget) and routes the open to a ks:pdf tab.
 *
 * The sentinel path `/__ks_evidence__` is the claim signal: urlTarget returns
 * true for ANY http(s) URL whose pathname is exactly `/__ks_evidence__` and
 * that carries a non-empty `doc`, regardless of host. This keeps the claim
 * precise (no foreign link is hijacked) while not depending on the literal
 * `127.0.0.1:1` host (which changes if the GUI origin ever matches it).
 */

export interface KsEvidence {
  /** Required: the engine document id (doc_meta.doc_id). */
  doc: string
  /** 1-based page to jump to. Absent -> 1. */
  page?: number
  /** PDF user-space bbox (bottom-left origin): [x0, y0, x1, y1].
   *  本 tab 现在只用它承载"箭头锚行"（该条款在目标页的首行 span），
   *  渲染层在其左缘画红色右箭头（不再画黄框矩形）。 */
  bbox?: [number, number, number, number]
  /** 箭头/bbox 应显示的页（渲染时仅当 current page === 此页才画）。 */
  bboxPage?: number
  /** Optional clause revision id (annotated in the tab header). */
  rev?: string
  /**
   * **同一轮里也被引用的其他条款**（业主 2026-10-12 要求）。
   *
   * 业主原话：「在一个文件里面，它现在有 6 个条文都和它相关，那么我随便点哪一处…
   * 都可以跳到对应的原文的位置。同时呢，我点的那一条条目它的箭头是红的，
   * 其他同一个文件里面其他的被引用上的条目，就变成半透明…把透明度降低一点的这个箭头。」
   *
   * ⇒ 本 tab 打开时：**点开的那条**画实心红箭头，**这些**画半透明红箭头
   * （让人一眼看出"这一轮还引用了同一份文件的哪几处"）。
   *
   * 编码：URL 上重复的 `also=<page>,<x0>,<y0>,<x1>,<y1>`（`URLSearchParams.getAll`）。
   * 用重复参数而不是自定义分隔符串：值里不必再转义，`getAll` 天然给数组。
   * ⚠ 只收**同一份文档**的其他条款（跨文档的箭头没有意义 —— 本 tab 只显示一份 PDF）。
   */
  siblings?: KsEvidenceSibling[]
}

/** 同轮同文档的"其他被引用条款"（画半透明箭头用）。 */
export interface KsEvidenceSibling {
  /** 1-based 页。 */
  page: number
  /** PDF 用户空间 bbox（底部原点）。 */
  bbox: [number, number, number, number]
}

export const EVIDENCE_PATH = '/__ks_evidence__'

/**
 * Decide whether an external http(s) URL is one of OUR evidence links.
 *
 * 2026-09-16 官方 sidebar 迁移后，它的**调用方**从"better-sidebar 的
 * `TabDescriptor.urlTarget` 认领谓词"变成"entry.ts 的 document 级 capture 监听"
 * （官方右侧栏没有声明式认领外部链接的面）。语义不变：只认本插件的
 * `/__ks_evidence__` 且必须带 `doc`。
 *
 * @param url - 从锚点 href 解析出的 URL。
 * @returns true 表示这是我们的证据锚点。
 */
export function isKsEvidenceUrl(url: URL): boolean {
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
  if (url.pathname !== EVIDENCE_PATH) return false
  const doc = url.searchParams.get('doc')
  return typeof doc === 'string' && doc.length > 0
}

/**
 * Parse one evidence link. Accepts either the absolute href (the value the
 * better-sidebar builtin openTab lands in `tab.path`) or an already-decoded
 * meta object. Returns null when it is not a valid evidence link or `doc` is
 * missing.
 *
 * @param input - the raw string (href) OR a metas-object with { doc, page, bbox, rev }.
 */
export function parseEvidence(input: string | KsEvidence | undefined | null): KsEvidence | null {
  if (input === undefined || input === null) return null

  if (typeof input === 'object') {
    const doc = typeof input.doc === 'string' && input.doc.length > 0 ? input.doc : null
    if (doc === null) return null
    return {
      doc,
      page: typeof input.page === 'number' && input.page >= 1 ? Math.floor(input.page) : undefined,
      bbox: isBbox(input.bbox) ? input.bbox : undefined,
      /* ⚠ 2026-10-10（spec 009）：补 `bboxPage` —— 原来**对象形态也不解析它**，
         于是"箭头该显示在哪一页"这个信息在这一步就丢了。 */
      bboxPage: typeof input.bboxPage === 'number' && input.bboxPage >= 1
        ? Math.floor(input.bboxPage)
        : undefined,
      rev: typeof input.rev === 'string' && input.rev.length > 0 ? input.rev : undefined,
      siblings: Array.isArray(input.siblings) ? input.siblings : undefined,
    }
  }

  let url: URL
  try {
    url = new URL(input)
  } catch {
    return null
  }
  if (!isKsEvidenceUrl(url)) return null

  const doc = url.searchParams.get('doc') ?? ''
  if (doc.length === 0) return null

  const pageRaw = url.searchParams.get('page')
  const page = pageRaw !== null && /^\d+$/.test(pageRaw) ? Math.max(1, parseInt(pageRaw, 10)) : undefined

  const bboxRaw = url.searchParams.get('bbox')
  const bbox = bboxRaw !== null ? parseBbox(bboxRaw) : undefined

  /* ⚠ 2026-10-10（spec 009）：补 `bboxPage` 的 URL 侧解析 —— 与上面的对象形态同口径
     （非数字 / <1 ⇒ undefined，不许变成 NaN 或 0）。 */
  const bboxPageRaw = url.searchParams.get('bboxPage')
  const bboxPage = bboxPageRaw !== null && /^\d+$/.test(bboxPageRaw)
    ? Math.max(1, parseInt(bboxPageRaw, 10))
    : undefined

  const rev = url.searchParams.get('rev') ?? undefined

  /* ⚠ 2026-10-12（spec 012 R4）：同轮其他条款（画半透明箭头用）。
     用**重复参数** `also=…`（`getAll` 天然给数组），形状不对的整条丢掉。 */
  const siblings = url.searchParams.getAll('also')
    .map(parseSibling)
    .filter((s): s is KsEvidenceSibling => s !== null)

  return { doc, page, bbox, bboxPage, rev, siblings: siblings.length > 0 ? siblings : undefined }
}

/** Validate a numeric bbox array [x0, y0, x1, y1]. */
export function isBbox(value: unknown): value is [number, number, number, number] {
  return (
    Array.isArray(value)
    && value.length === 4
    && value.every((n) => typeof n === 'number' && Number.isFinite(n))
  )
}

/** 解析一条 `also=<page>,<x0>,<y0>,<x1>,<y1>`（同轮其他条款）。形状不对 ⇒ null。 */
function parseSibling(raw: string): KsEvidenceSibling | null {
  const parts = raw.split(',').map((s) => Number(s.trim()))
  if (parts.length !== 5 || parts.some((n) => !Number.isFinite(n))) return null
  const [page, x0, y0, x1, y1] = parts
  if (page < 1) return null
  return {
    page: Math.floor(page),
    bbox: [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)],
  }
}

/** Pseudo host used to RECONSTRUCT an evidence anchor URL (matches the host's
 *  KS_EVIDENCE_ORIGIN in src/index.js). */
export const EVIDENCE_ORIGIN = 'http://127.0.0.1:1'

/**
 * Rebuild an evidence anchor URL from a parsed KsEvidence. Returns null only
 * when `doc` is missing (an un-linkable evidence). `page`/`rev` are optional
 * (a missing page or rev is simply omitted from the query). Shared by:
 *   - the bookmarks tab: row -> link,
 *   - the ks:pdf in-tab history: rebuild the href when the tab was opened
 *     from a meta/object instead of a path.
 */
export function evidenceUrlOf(ev: KsEvidence | null | undefined): string | null {
  if (!ev) return null
  const doc = typeof ev.doc === 'string' && ev.doc.length > 0 ? ev.doc : null
  if (doc === null) return null
  const params = new URLSearchParams()
  params.set('doc', doc)
  const page =
    typeof ev.page === 'number' && Number.isFinite(ev.page) && ev.page >= 1
      ? Math.floor(ev.page)
      : null
  if (page !== null) params.set('page', String(page))
  const rev = typeof ev.rev === 'string' && ev.rev.length > 0 ? ev.rev : null
  if (rev !== null) params.set('rev', rev)
  /* ⚠⚠ 2026-10-10（spec 009，**红箭头不出现的决定性一环**）：
     本函数**原来只编 `doc` / `page` / `rev`，从不编 `bbox`** ——
     而 `parseEvidence` 早就实现了 `parseBbox`（能**解析** bbox）⇒ 结果是
     **bbox 只进不出**：任何调用方把 bbox 放进 `KsEvidence` 目标，都会在编码这一步被丢掉，
     于是证据 tab 里 `evidence.current?.bbox` 永远 undefined ⇒ **箭头永远不画**。
     （这正是业主实测到的"能跳转但没箭头"的最后一环；前两环见
      `KsTurnTab.tsx` 的 `turnEvidenceHref` 与引擎的 `_clause_to_evidence`。）
     ⚠ 只在这一项**存在且是 4 个有限数**时才编 —— **不许编空参**（编空串会让
     `parseBbox` 得到 NaN、反而画出错位置的箭头）。 */
  if (isBbox(ev.bbox)) {
    params.set('bbox', ev.bbox.map((n) => String(n)).join(','))
    if (typeof ev.bboxPage === 'number' && Number.isFinite(ev.bboxPage) && ev.bboxPage >= 1) {
      params.set('bboxPage', String(Math.floor(ev.bboxPage)))
    }
  }
  /* ⚠ 2026-10-12（spec 012 R4，业主要求）：同轮**其他**被引用的条款也要带上
     —— 渲染层据此画半透明红箭头（点开的那条是实心红）。
     ⚠ 只在形状合法时编；**编了 bbox 才编 siblings**（没有主箭头就没有"其他"可言）。 */
  if (isBbox(ev.bbox) && Array.isArray(ev.siblings)) {
    for (const s of ev.siblings) {
      if (s === null || typeof s !== 'object') continue
      if (!(typeof s.page === 'number' && Number.isFinite(s.page) && s.page >= 1)) continue
      if (!isBbox(s.bbox)) continue
      params.append('also', `${Math.floor(s.page)},${s.bbox.map((n) => String(n)).join(',')}`)
    }
  }
  return `${EVIDENCE_ORIGIN}${EVIDENCE_PATH}?${params.toString()}`
}

/** Parse "x0,y0,x1,y1" (comma-separated, PDF points, bottom-left origin). */
function parseBbox(raw: string): [number, number, number, number] | undefined {
  const parts = raw.split(',').map((s) => Number(s.trim()))
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return undefined
  // Normalize so x0<=x1 and y0<=y1 (the component draws the enclosing rect).
  const x0 = Math.min(parts[0], parts[2])
  const x1 = Math.max(parts[0], parts[2])
  const y0 = Math.min(parts[1], parts[3])
  const y1 = Math.max(parts[1], parts[3])
  return [x0, y0, x1, y1]
}
