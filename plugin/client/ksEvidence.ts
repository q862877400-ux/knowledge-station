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
      rev: typeof input.rev === 'string' && input.rev.length > 0 ? input.rev : undefined,
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

  const rev = url.searchParams.get('rev') ?? undefined

  return { doc, page, bbox, rev }
}

/** Validate a numeric bbox array [x0, y0, x1, y1]. */
export function isBbox(value: unknown): value is [number, number, number, number] {
  return (
    Array.isArray(value)
    && value.length === 4
    && value.every((n) => typeof n === 'number' && Number.isFinite(n))
  )
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
