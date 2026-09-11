/**
 * ks-dsh-plugin — client/api.ts
 *
 * Data transport for the ks:pdf tab. Two calls:
 *   1. fetchSession()  -> same-origin GET /ks/session. Lazily ensures the engine
 *      is live (spawn or reuse) and returns { port, pid, reused, token }. The
 *      engine port and token rotate per start, so EVERY load / click re-fetches
 *      this (never cached across loads).
 *   2. fetchPdf(port, doc, token) -> cross-origin GET
 *        http://127.0.0.1:<port>/api/v1/documents/<doc>/file
 *      with a Bearer token, returning an ArrayBuffer of PDF bytes.
 *
 * SECURITY / TRUST:
 *   - The token is held ONLY in a module-scoped in-memory variable in this
 *     bundle (the page). It is never written to localStorage, never put in a
 *     URL, and never sent to any third-party origin. The only consumers are:
 *       (a) the same-origin DSH web host (via /ks/session), and
 *       (b) the loopback engine (127.0.0.1:<engine_port>).
 *   - This is exactly the trust model the old frontend used (token in
 *     localStorage on the same GUI origin), minus the persistence.
 */

/** Stack of module-scoped state — the token lives here in page memory only. */
const memory = {
  /** Bearer token minted by the current engine session (or null). */
  token: null as string | null,
  /** Last engine port we saw (for a clearer stale-port error). */
  port: null as number | null,
}

/** Reset the in-memory session (called when the engine was seen to rotate). */
export function clearSession(): void {
  memory.token = null
  memory.port = null
}

export interface EngineSession {
  ok: boolean
  engine: {
    port: number
    pid: number
    reused: boolean
  }
  token: string
}

/**
 * fetchSession never returns an error object — on a non-200 it THROWS (the
 * caller shows the message + retry). The "error" shape is only produced by the
 * HOST route's 503 body; we surface it as a thrown Error instead.
 */
export async function fetchSession(signal?: AbortSignal): Promise<EngineSession> {
  const res = await fetch('/ks/session', {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body (e.g. 404 from the SPA fallback) */
  }
  const parsed = body && typeof body === 'object' ? (body as Record<string, unknown>) : null
  if (res.status === 200 && parsed && parsed.ok === true) {
    const engine = parsed.engine as Record<string, unknown> | undefined
    const token = typeof parsed.token === 'string' ? parsed.token : ''
    const port = typeof engine?.port === 'number' ? engine.port : NaN
    if (token.length === 0 || Number.isNaN(port)) {
      throw new Error('引擎会话不完整：/ks/session 缺少 token 或 port')
    }
    // Hand the token to the engine-data fetch path (memory only).
    memory.token = token
    memory.port = port
    return {
      ok: true,
      engine: {
        port,
        pid: typeof engine?.pid === 'number' ? engine.pid : 0,
        reused: engine?.reused === true,
      },
      token,
    }
  }
  const err = parsed?.error as Record<string, unknown> | undefined
  throw new Error(
    `引擎未就绪(${res.status}): ${typeof err?.message === 'string' ? err.message : res.statusText}`,
  )
}

/**
 * Fetch the raw PDF bytes for one document from the engine (cross-origin,
 * Bearer-authenticated). The engine must be live (fetchSession first) so we
 * have a current port + token; the engine's CORS allows the same-machine
 * origin (127.0.0.1:<web-port>) to read this with an Authorization header.
 *
 * @returns the PDF bytes as an ArrayBuffer.
 */
export async function fetchPdf(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  const url = `http://127.0.0.1:${port}/api/v1/documents/${encodeURIComponent(docId)}/file`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/pdf' },
    signal,
  })
  if (res.status === 401) {
    clearSession() // session rotated — the caller should re-fetch /ks/session.
    throw new Error('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (res.status === 404) {
    throw new Error(`文档不存在或 PDF 原件不可用(404): ${docId}`)
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  const ct = res.headers.get('content-type') ?? ''
  if (!ct.includes('pdf')) {
    throw new Error(`引擎返回了非 PDF 内容 (content-type: ${ct || 'unknown'})`)
  }
  return res.arrayBuffer()
}

export interface BboxSpan {
  page_number: number
  bbox: number[]
}

export interface FetchBboxResult {
  found: boolean
  spans: BboxSpan[]
}

/**
 * fetchBbox never returns an error object — on a non-200 or non-JSON body it
 * THROWS (the KsEvidenceTab caller shows nothing and keeps the no-box jump).
 * This is a same-origin GET via the host proxy (/ks/bbox) — the engine token
 * never leaves the host; the page only passes the clause_revision_id. The 401
 * semantics mirror fetchSession (session-rotation is transparent: the host
 * re-reads the session and retries once before forwarding an error).
 */
export async function fetchBbox(rev: string, signal?: AbortSignal): Promise<FetchBboxResult> {
  const res = await fetch('/ks/bbox?rev=' + encodeURIComponent(rev), {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body (e.g. the SPA fallback) */
  }
  const parsed = body && typeof body === 'object' ? (body as Record<string, unknown>) : null
  if (res.status === 200 && parsed && parsed.ok === true) {
    const spansRaw = parsed.spans
    const spans = Array.isArray(spansRaw)
      ? (spansRaw as unknown[]).filter(
          (s): s is BboxSpan => {
            if (s === null || typeof s !== 'object') return false
            const o = s as Record<string, unknown>
            const box = o.bbox
            return typeof o.page_number === 'number' && Array.isArray(box) && box.length === 4
          },
        )
      : []
    return { found: parsed.found === true && spans.length > 0, spans }
  }
  const err = parsed?.error as Record<string, unknown> | undefined
  throw new Error(
    `bbox 获取失败(${res.status}): ${typeof err?.message === 'string' ? err.message : res.statusText}`,
  )
}

/** A 401 from the engine — the session file may have rotated; re-fetch /ks/session. */
export class EngineAuthError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'EngineAuthError'
  }
}

/* ------------------------------------------------------------------ *
 * Bookmarks (增强③-A) — GET /api/v1/bookmarks + DELETE /api/v1/bookmarks/{id}
 * (browser-side cross-origin calls, Bearer, same trust model as fetchPdf)
 * ------------------------------------------------------------------ */

/** One bookmark, normalized from the engine's GET /api/v1/bookmarks item.
 *  The engine joins user_bookmark/clause_revision/doc_meta, so a bookmark may
 *  lack doc/page when its clause_revision was removed. */
export interface KsBookmark {
  bookmark_id: string
  clause_key: string | null
  remark: string | null
  created_at: string | null
  clause_revision_id: string | null
  clause_number: string | null
  title: string | null
  content_text: string | null
  doc_id: string | null
  page_start: number | null
  standard_no: string | null
  legal_status: string | null
}

function str(v: unknown): string | null {
  return typeof v === 'string' && v.length > 0 ? v : null
}

function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

/** Extract an array out of the engine envelope ({data:[...]}) or a bare array. */
function unwrapList(body: unknown): unknown[] {
  if (Array.isArray(body)) return body
  if (body !== null && typeof body === 'object') {
    const o = body as Record<string, unknown>
    for (const key of ['data', 'bookmarks', 'items']) {
      const v = o[key]
      if (Array.isArray(v)) return v
    }
  }
  return []
}

/** Normalize one raw bookmark row (drop rows without an id). */
function normalizeBookmark(value: unknown): KsBookmark | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const id =
    str(o.bookmark_id) ??
    (typeof o.bookmark_id === 'number' ? String(o.bookmark_id) : null)
  if (id === null) return null
  return {
    bookmark_id: id,
    clause_key: str(o.clause_key),
    remark: str(o.remark),
    created_at: typeof o.created_at === 'string' ? o.created_at : null,
    clause_revision_id: str(o.clause_revision_id),
    clause_number: str(o.clause_number),
    title: str(o.title),
    content_text: typeof o.content_text === 'string' ? o.content_text : null,
    doc_id: str(o.doc_id),
    page_start: num(o.page_start),
    standard_no: str(o.standard_no),
    legal_status: str(o.legal_status),
  }
}

/**
 * fetchBookmarks — cross-origin GET for the bookmark list. On a 401 it clears
 * the in-memory session and throws EngineAuthError (the caller re-fetches
 * /ks/session and retries once). Non-200 -> a plain Error.
 */
export async function fetchBookmarks(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<KsBookmark[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmarks`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body */
  }
  return unwrapList(body)
    .map(normalizeBookmark)
    .filter((b): b is KsBookmark => b !== null)
}

/**
 * deleteBookmark — cross-origin DELETE. On a 401 it clears the session and
 * throws EngineAuthError. Any non-ok status throws a plain Error.
 */
export async function deleteBookmark(
  port: number,
  bookmarkId: string,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/bookmarks/${encodeURIComponent(bookmarkId)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`DELETE 收藏失败(HTTP ${res.status})`)
  }
}

/** Meta needed to bookmark one clause (the engine keys bookmarks by clause_key). */
export interface ClauseMeta {
  clause_revision_id: string
  clause_key: string
  doc_id: string
  page_start: number | null
  clause_number: string | null
  title: string | null
  standard_no: string | null
  /** 所属标准是否已被标准级收藏（顶部「收藏本标准」初始态）。 */
  doc_bookmarked?: boolean
  /** 本条款当前是否已收藏（PDF tab 可见性刷新用）。 */
  clause_bookmarked?: boolean
  /** 本条款收藏的 bookmark_id（取消收藏 toggle 用；未收藏时 null）。 */
  clause_bookmark_id?: string | null
}

/**
 * fetchClauseMeta — cross-origin GET /api/v1/clauses/{rev}/meta. 401 clears the
 * session + throws EngineAuthError; 404 throws a plain Error ("条款不存在").
 */
export async function fetchClauseMeta(
  port: number,
  rev: string,
  token: string,
  signal?: AbortSignal,
): Promise<ClauseMeta> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/clauses/${encodeURIComponent(rev)}/meta`,
    {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (res.status === 404) {
    throw new Error(`条款不存在或不可收藏(404): ${rev}`)
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body */
  }
  const data = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>).data
    : null
  if (data === null || typeof data !== 'object') {
    throw new Error(`条款元数据响应异常`)
  }
  const d = data as Record<string, unknown>
  const clause_key = typeof d.clause_key === 'string' ? d.clause_key : ''
  if (clause_key.length === 0) {
    throw new Error(`条款缺少 clause_key，无法收藏`)
  }
  return {
    clause_revision_id: rev,
    clause_key,
    doc_id: typeof d.doc_id === 'string' ? d.doc_id : '',
    page_start: typeof d.page_start === 'number' ? d.page_start : null,
    clause_number: typeof d.clause_number === 'string' ? d.clause_number : null,
    title: typeof d.title === 'string' ? d.title : null,
    standard_no: typeof d.standard_no === 'string' ? d.standard_no : null,
    doc_bookmarked: d.doc_bookmarked === true,
    clause_bookmarked: d.clause_bookmarked === true,
    clause_bookmark_id: typeof d.clause_bookmark_id === 'string' ? d.clause_bookmark_id : null,
  }
}

/**
 * addBookmark — cross-origin POST /api/v1/bookmarks {clause_key}. Idempotent on
 * the engine side (add_bookmark returns existed:true for a duplicate). On a 401
 * it clears the session + throws EngineAuthError; non-ok throws a plain Error.
 */
export async function addBookmark(
  port: number,
  clauseKey: string,
  token: string,
  signal?: AbortSignal,
): Promise<{ existed: boolean }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmarks`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ clause_key: clauseKey }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`收藏失败(HTTP ${res.status})`)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body */
  }
  const data = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>).data
    : null
  return { existed: !!(data && typeof data === 'object' && (data as Record<string, unknown>).existed === true) }
}

/* ------------------------------------------------------------------ *
 * Doc bookmarks (增强③-A 标准级书签) — GET/POST/DELETE /api/v1/doc-bookmarks
 * ------------------------------------------------------------------ */

/** One standard-level bookmark (user_doc_bookmark joined with doc_meta). */
export interface DocBookmark {
  doc_bookmark_id: string
  doc_id: string
  remark: string | null
  created_at: string | null
  standard_no: string | null
  standard_name: string | null
  doc_type: string | null
  legal_status: string | null
}

function normalizeDocBookmark(value: unknown): DocBookmark | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const id = str(o.doc_bookmark_id)
  const doc = str(o.doc_id)
  if (id === null || doc === null) return null
  return {
    doc_bookmark_id: id,
    doc_id: doc,
    remark: str(o.remark),
    created_at: typeof o.created_at === 'string' ? o.created_at : null,
    standard_no: str(o.standard_no),
    standard_name: str(o.standard_name),
    doc_type: str(o.doc_type),
    legal_status: str(o.legal_status),
  }
}

/** GET the standard-level bookmark list. 401 → EngineAuthError. */
export async function fetchDocBookmarks(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<DocBookmark[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/doc-bookmarks`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch { /* non-JSON body */ }
  return unwrapList(body)
    .map(normalizeDocBookmark)
    .filter((b): b is DocBookmark => b !== null)
}

/** POST a standard-level bookmark by doc_id. Idempotent (existed flag). */
export async function addDocBookmark(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
): Promise<{ existed: boolean }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/doc-bookmarks`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ doc_id: docId }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (res.status === 404) {
    throw new Error(`文档不存在，无法收藏(404): ${docId}`)
  }
  if (!res.ok) {
    throw new Error(`标准收藏失败(HTTP ${res.status})`)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch { /* non-JSON body */ }
  const data = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>).data
    : null
  return { existed: !!(data && typeof data === 'object' && (data as Record<string, unknown>).existed === true) }
}

/** DELETE a standard-level bookmark by doc_id (toggle off). No-op when absent. */
export async function removeDocBookmarkByDoc(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/doc-bookmarks/by-doc/${encodeURIComponent(docId)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`取消标准收藏失败(HTTP ${res.status})`)
  }
}

/** DELETE a clause bookmark by clause_key (toggle off). No-op when absent. */
export async function removeBookmarkByClauseKey(
  port: number,
  clauseKey: string,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/bookmarks/by-clause/${encodeURIComponent(clauseKey)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`取消条款收藏失败(HTTP ${res.status})`)
  }
}
/* ------------------------------------------------------------------ *
 * 文件目录 (A) — 分类树 GET /documents/categories、批量删除 POST
 * batch-delete、平铺列表 GET /documents、标题目录 GET /{doc}/tree
 * (browser-side cross-origin calls, Bearer, same trust model as fetchPdf)
 * ------------------------------------------------------------------ */

/** One document row (doc_meta) normalized from the engine. The flat list
 *  GET /api/v1/documents and every leaf doc in the categories tree carry the
 *  same doc_meta fields. */
export interface KsDoc {
  doc_id: string
  standard_no: string | null
  standard_name: string | null
  legal_status: string | null
  legal_hierarchy: string | null
  ccs_code: string | null
  ccs_name: string | null
  published_at: string | null
  effective_from: string | null
  withdrawn_date: string | null
  superseded_by: string | null
  doc_type: string | null
  domain_tags: string | null
}

/** One category node in the /categories tree. Leaf docs are in `docs`.
 *  标准分支: L1 -> L2(CCS 大类) -> L3(区间) -> L4(具体类目), 叶文档在 L4.docs,
 *  L3.docs 为空. 法规分支: L1 -> L2(效力等级) -> L3(领域), 叶文档直接在 L3.docs
 *  (法规无 L4), L3.items 为空. 空分类不返回. */
export interface KsCategoryNode {
  name: string
  items: KsCategoryNode[]
  docs: KsDoc[]
}

/** One clause row from GET /api/v1/documents/{doc_id}/tree (标题目录). */
export interface KsClause {
  clause_number: string | null
  title: string | null
  page_start: number | null
  /** 1 = 章, 2 = 小节 (含附录条目). */
  level: number | null
  source: string | null
}

/** POST /api/v1/documents/batch-delete result. */
export interface BatchDeleteResult {
  deleted_docs: number
  deleted_clauses: number
  missing: string[]
}

function normalizeDoc(value: unknown): KsDoc | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const id = str(o.doc_id) ?? (typeof o.doc_id === 'number' ? String(o.doc_id) : null)
  if (id === null) return null
  return {
    doc_id: id,
    standard_no: str(o.standard_no),
    standard_name: str(o.standard_name),
    legal_status: str(o.legal_status),
    legal_hierarchy: str(o.legal_hierarchy),
    ccs_code: str(o.ccs_code),
    ccs_name: str(o.ccs_name),
    published_at: str(o.published_at),
    effective_from: str(o.effective_from),
    withdrawn_date: str(o.withdrawn_date),
    superseded_by: str(o.superseded_by),
    doc_type: str(o.doc_type),
    domain_tags: str(o.domain_tags),
  }
}

function normalizeCategory(value: unknown): KsCategoryNode | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const name = str(o.name)
  if (name === null) return null
  const items = Array.isArray(o.items) ? (o.items as unknown[]) : []
  const docs = Array.isArray(o.docs) ? (o.docs as unknown[]) : []
  return {
    name,
    items: items.map(normalizeCategory).filter((n): n is KsCategoryNode => n !== null),
    docs: docs.map(normalizeDoc).filter((d): d is KsDoc => d !== null),
  }
}

function normalizeClause(value: unknown): KsClause | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  return {
    clause_number: str(o.clause_number),
    title: str(o.title),
    page_start: num(o.page_start),
    level: num(o.level),
    source: str(o.source),
  }
}

/** 分类树. 401 → EngineAuthError (caller 重新 fetchSession 一次再试). */
export async function fetchCategories(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<KsCategoryNode[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/documents/categories`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  return unwrapList(body)
    .map(normalizeCategory)
    .filter((n): n is KsCategoryNode => n !== null)
}

/** 某文档的标题目录 (章/小节)。失败/404/空树 → 调用方静默降级为无目录。 */
export async function fetchDocTree(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
): Promise<KsClause[]> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/documents/${encodeURIComponent(docId)}/tree`,
    {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  return unwrapList(body)
    .map(normalizeClause)
    .filter((c): c is KsClause => c !== null)
}

/** 批量删除文档 (必须 confirm:true)。引擎显式级联删条款/向量/证据, 用户资产
 *  (收藏/批注) 不删。401 → EngineAuthError; 非 ok → 透传引擎 error.message。 */
export async function batchDeleteDocs(
  port: number,
  docIds: string[],
  token: string,
  signal?: AbortSignal,
): Promise<BatchDeleteResult> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/documents/batch-delete`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ doc_ids: docIds, confirm: true }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    let msg = `批量删除失败(HTTP ${res.status})`
    try {
      const b = await res.json()
      const e = b !== null && typeof b === 'object'
        ? (b as Record<string, unknown>).error : null
      if (e !== null && typeof e === 'object' && typeof (e as Record<string, unknown>).message === 'string') {
        msg = (e as Record<string, unknown>).message as string
      }
    } catch { /* keep default */ }
    throw new Error(msg)
  }
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const wrapped = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>) : null
  const data = (wrapped !== null && wrapped.data !== null && typeof wrapped.data === 'object')
    ? (wrapped.data as Record<string, unknown>)
    : (wrapped ?? {})
  return {
    deleted_docs: typeof data.deleted_docs === 'number' ? data.deleted_docs : 0,
    deleted_clauses: typeof data.deleted_clauses === 'number' ? data.deleted_clauses : 0,
    missing: Array.isArray(data.missing) ? (data.missing as unknown[]).map(String) : [],
  }
}

/** 文档平铺列表 (含全部 doc_meta 字段), 删除后刷新用。401 → EngineAuthError。 */
export async function fetchDocsFlat(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<KsDoc[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/documents`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    throw new Error(`引擎返回 HTTP ${res.status}`)
  }
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  return unwrapList(body)
    .map(normalizeDoc)
    .filter((d): d is KsDoc => d !== null)
}

/* ------------------------------------------------------------------ *
 * 每日巡检（决策 19, P0=手动触发）— 全部同源走 host 代理
 * (/ks/inspection/{run,summary,settings})：host 负责引擎保活/轮询/落盘，
 * client 永不直连引擎、不经手 token。
 * ------------------------------------------------------------------ */

export interface KsInspectionSettings {
  /** P1：拨开 = 每日 time 自动跑 tier0 + dsh 晚开时启动补当天一次。 */
  autoEnabled: boolean
  /** 每日自动时点（本地 HH:MM）。 */
  time: string
  /** P2 占位：周日 tier1 全量滚动（host 本版本不消费）。 */
  sundayTier1: boolean
}

/** change_type 五类细分计数（引擎 report.py 同口径；UI 纵览统计用，
 *  明细行不进 UI 不进状态文件——需要明细时导出 Excel）。 */
export interface KsInspectionByType {
  new_version: number
  superseded: number
  withdrawn: number
  not_found: number
  no_change: number
}

export interface KsInspectionCounts {
  red: number
  yellow: number
  green: number
  gray: number
}

export interface KsInspectionLast {
  batch_id: string
  tier: string
  trigger: string
  /** running | done | failed | paused */
  status: string
  total: number
  checked: number
  counts: KsInspectionCounts
  pause_reason: string | null
  started_at: string | null
  finished_at: string | null
  error: string | null
  by_type: KsInspectionByType | null
  /** P1：该批由每日定时触发（UI 显示「今日自动巡检」）。 */
  auto?: boolean
}

export interface KsInspectionSummary {
  ok: boolean
  settings: KsInspectionSettings
  last: KsInspectionLast | null
  /** done 且距今超 24h 的天数（0 = 未逾期）；从未跑过 last=null。 */
  overdue_days: number
  /** 上次 running 遗留且无人接管（dsh 重启中断）→ UI 提示疑似中断。 */
  stale_run: boolean
}

/** HTTP 错误 with 服务端 code（UI 区分「已在跑」409 等场景）。 */
/* ------------------------------------------------------------------ *
 * R27 入库预览（Dry-Run）+ 批量分桶 —— 同源 host 代理 /ks/ingest/*
 *
 * 与 inspection/announce 的区别：**纯代理零缓存**。host 侧只列目录 + 转发，
 * 所有解析与体检都在引擎做（`src/core/ingestion/dry_run.py`）。
 * 客户端永远不直接跟引擎说话（token 不出 host；见 fetchSession 的信任模型）。
 * ------------------------------------------------------------------ */

export interface KsIngestInboxFile {
  file_name: string
  size: number
  path: string
  mtime?: number
}

export interface KsIngestInbox {
  dir: string
  count: number
  files: KsIngestInboxFile[]
  /** host 兜底列表时的降级标记（引擎不可用，仍能看到有哪些文件） */
  degraded?: string
}

export interface KsIngestClauseSample {
  ordinal: number
  number: string
  page_start: number | null
  page_end: number | null
  text_len: number
  head: string
  knowledge_type: string
  type_confidence: number | null
  modality: string | null
  modality_strength: number | null
  suspicious: boolean
  ocr_confidence: number
  reasons: string[]
}

export interface KsIngestReport {
  schema_version: number
  status: 'ok' | 'error'
  source: { path: string; file_name: string; file_size: number; file_hash: string | null }
  pages: number
  total_clauses: number
  clauses_dropped_tiny: number
  grade: 'A' | 'B' | 'C' | 'D'
  grade_reasons: string[]
  doc_confidence: number
  verdict: 'ok' | 'warn' | 'block'
  verdict_reasons: Array<{ code: string; reason: string }>
  head_samples: KsIngestClauseSample[]
  tail_samples: KsIngestClauseSample[]
  ocr_suspects: KsIngestClauseSample[]
  ocr_suspects_truncated: boolean
  knowledge_type_distribution: Record<string, number>
  typing_quality: Record<string, unknown>
  legal_elements: Record<string, unknown>
  recognition: {
    text_layer_state: string
    weird_ratio: number
    replacement_ratio: number
    skew_deg: number | null
    skew_measured: boolean
    skew_pages_ratio: number
    measured_lines?: number
  }
  layout: {
    pages: number
    chars: number
    chars_per_page: number
    pages_no_text: number
    clauses_per_1000chars: number
    tables_rebuilt?: number
  }
  collected_signals: Record<string, unknown>
  standard_no_guess: { value: string | null; source?: string; confidence?: number }
  standard_name_guess: { value: string | null; source?: string }
  duplicate: { kind: string; doc_id?: string | null; message?: string }
  quarantine_candidate: boolean
  /** 请求级：本次预览禁用了深度通道（恒 true——深度通道云优先 = 外发） */
  deep_fallback_disabled?: boolean
  /** 文档级：这份文档真的走到「本该深度分析却被跳过」的分支（无文本层才 true） */
  deep_fallback_skipped: boolean
  egress: 'none' | 'mineru_cloud'
  elapsed_ms: number
  error_code: string | null
  error_message: string | null
  one_line?: string
}

export interface KsIngestBatchRow {
  path: string
  file_name: string
  verdict: 'ok' | 'warn' | 'block'
  grade: string
  pages: number
  total_clauses: number
  doc_confidence: number
  one_line: string
  reasons: string[]
  error: string | null
}

export interface KsIngestBatch {
  total_candidates: number
  truncated: boolean
  limit_files: number
  sampled: number
  unprocessed: number
  evaluated: number
  sample_requested: number
  buckets: { ok: number; warn: number; block: number }
  by_bucket: Record<string, KsIngestBatchRow[]>
  files: KsIngestBatchRow[]
  conservation_ok: boolean
  elapsed_ms: number
  doc_type: string
  egress: 'none'
}

/** 同源 host 代理的错误（保留 host/引擎的错误码，UI 才能给出可行动提示）。 */
export class KsIngestHttpError extends Error {
  constructor(
    public readonly httpStatus: number,
    public readonly code: string | null,
    message: string,
  ) {
    super(message)
    this.name = 'KsIngestHttpError'
  }
}

async function parseIngestError(res: Response): Promise<KsIngestHttpError> {
  let code: string | null = null
  let message = `HTTP ${res.status}`
  try {
    const body = (await res.json()) as { error?: { code?: string; message?: string } }
    if (body && typeof body.error === 'object' && body.error !== null) {
      if (typeof body.error.code === 'string') code = body.error.code
      if (typeof body.error.message === 'string' && body.error.message) message = body.error.message
    }
  } catch { /* 非 JSON 响应保持默认文案 */ }
  return new KsIngestHttpError(res.status, code, message)
}

/** GET /ks/ingest/inbox-default — 「待入库」目录（host 按需创建并回传绝对路径）。 */
export async function fetchIngestInboxDefault(signal?: AbortSignal): Promise<string> {
  const res = await fetch('/ks/ingest/inbox-default', {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: { dir?: string } } | null
  const dir = body?.data?.dir
  if (body?.ok !== true || typeof dir !== 'string' || dir === '') {
    throw new Error('待入库目录响应异常')
  }
  return dir
}

/** GET /ks/ingest/inbox?dir= — 列候选 PDF（引擎不可用时 host 降级列表）。 */
export async function fetchIngestInbox(
  dir: string, signal?: AbortSignal,
): Promise<KsIngestInbox> {
  const qs = new URLSearchParams({ dir }).toString()
  const res = await fetch(`/ks/ingest/inbox?${qs}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; degraded?: string; data?: Partial<KsIngestInbox> } | null
  if (body?.ok !== true) throw new Error('待入库目录列表响应异常')
  return {
    dir: body.data?.dir ?? dir,
    count: typeof body.data?.count === 'number' ? body.data.count : 0,
    files: Array.isArray(body.data?.files) ? (body.data.files as KsIngestInboxFile[]) : [],
    degraded: body.degraded,
  }
}

/** POST /ks/ingest/preview — 单本 R27 完整体检报告（只读、零外发）。 */
export async function fetchIngestPreview(
  path: string, opts: { docType?: string; signal?: AbortSignal } = {},
): Promise<KsIngestReport> {
  const res = await fetch('/ks/ingest/preview', {
    method: 'POST',
    headers: { accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, doc_type: opts.docType ?? 'standard' }),
    signal: opts.signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; data?: KsIngestReport } | null
  if (body?.ok !== true || body.data === undefined) throw new Error('入库预览响应异常')
  return body.data
}

/** POST /ks/ingest/preview/batch — 目录批量预览 + ✅/⚠️/❌ 分桶（决策 2）。 */
export async function fetchIngestBatch(
  req: { dir: string; sample?: number; limitFiles?: number; docType?: string },
  signal?: AbortSignal,
): Promise<KsIngestBatch> {
  const payload: Record<string, unknown> = { dir: req.dir }
  if (req.sample !== undefined) payload.sample = req.sample
  if (req.limitFiles !== undefined) payload.limit_files = req.limitFiles
  if (req.docType !== undefined) payload.doc_type = req.docType
  const res = await fetch('/ks/ingest/preview/batch', {
    method: 'POST',
    headers: { accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; data?: KsIngestBatch } | null
  if (body?.ok !== true || body.data === undefined) throw new Error('批量预览响应异常')
  return body.data
}

// KS_INGEST_PATH_MARKER_R27
export class InspectionHttpError extends Error {
  constructor(
    public readonly httpStatus: number,
    public readonly code: string | null,
    message: string,
  ) {
    super(message)
    this.name = 'InspectionHttpError'
  }
}

async function parseInspectionError(res: Response): Promise<InspectionHttpError> {
  let code: string | null = null
  let message = `HTTP ${res.status}`
  try {
    const b = (await res.json()) as { error?: { code?: string; message?: string } } | null
    if (b?.error) {
      if (typeof b.error.code === 'string') code = b.error.code
      if (typeof b.error.message === 'string' && b.error.message.length > 0) message = b.error.message
    }
  } catch { /* keep default */ }
  return new InspectionHttpError(res.status, code, message)
}

/** GET /ks/inspection/summary — 本地状态快照；绝不拉起引擎。 */
export async function fetchInspectionSummary(signal?: AbortSignal): Promise<KsInspectionSummary> {
  const res = await fetch('/ks/inspection/summary', {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as Partial<KsInspectionSummary> | null
  if (body === null || body.ok !== true) throw new Error('巡检状态响应异常')
  return {
    ok: true,
    settings: body.settings ?? { autoEnabled: false, time: '08:30', sundayTier1: false },
    last: body.last ?? null,
    overdue_days: typeof body.overdue_days === 'number' ? body.overdue_days : 0,
    stale_run: body.stale_run === true,
  }
}

/** POST /ks/inspection/run — 手动触发 tier0 巡检（host 负责保活与结果回收）。 */
export async function runInspection(signal?: AbortSignal): Promise<{ batch_id: string; status: string }> {
  const res = await fetch('/ks/inspection/run', {
    method: 'POST',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; batch_id?: string; status?: string } | null
  if (body === null || body.ok !== true || typeof body.batch_id !== 'string') {
    throw new Error('巡检启动响应异常')
  }
  return { batch_id: body.batch_id, status: typeof body.status === 'string' ? body.status : 'running' }
}

/** PUT /ks/inspection/settings — 白名单键部分合并（host 校验）。 */
export async function updateInspectionSettings(
  patch: Partial<KsInspectionSettings>,
  signal?: AbortSignal,
): Promise<KsInspectionSettings> {
  const res = await fetch('/ks/inspection/settings', {
    method: 'PUT',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(patch),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; settings?: KsInspectionSettings } | null
  if (body === null || body.ok !== true || body.settings === undefined) {
    throw new Error('设置保存响应异常')
  }
  return body.settings
}

/** 从 Content-Disposition 提取文件名（filename*=UTF-8''… 或 filename="…"）。 */
function filenameFromDisposition(value: string | null): string | null {
  if (!value) return null
  const star = /filename\*=UTF-8''([^;]+)/i.exec(value)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1])
    } catch { /* fall through */ }
  }
  const plain = /filename="?([^";]+)"?/i.exec(value)
  return plain?.[1] ? plain[1] : null
}

/**
 * POST /ks/inspection/export — 导出「上一次巡检结果」为 Excel（引擎生成
 * xlsx，host 代理回传）。浏览器侧：取 blob → 触发下载（文件名取服务端
 * Content-Disposition，缺省「更新检查结果.xlsx」）。非 ok 抛 InspectionHttpError。
 */
export async function exportInspectionResult(signal?: AbortSignal): Promise<void> {
  const res = await fetch('/ks/inspection/export', {
    method: 'POST',
    headers: { accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const blob = await res.blob()
  const name = filenameFromDisposition(res.headers.get('content-disposition')) ?? '更新检查结果.xlsx'
  const url = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }
}



/* ------------------------------------------------------------------ *
 * 公告发现（语义 C：自定义公告源 → 随巡检定期"看新公告" → 轻通知）
 * 全部同源走 host 代理 /ks/announce/*；引擎 app_config 为源清单唯一真值。
 * ------------------------------------------------------------------ */

export interface KsAnnounceSource {
  id: string
  name: string
  url: string
  enabled: boolean
  note?: string
  first_scan_done?: boolean
  added_at?: string
  rebaselined?: boolean
}

export interface KsAnnounceRecentItem {
  title: string
  url: string
  published_date: string | null
  source_name: string
  first_seen: string | null
}

export interface KsAnnouncePerSource {
  id: string
  name: string
  status: string
  reason: string | null
  items: number
  new_items: number
  baseline_items: number
}

export interface KsAnnounceLast {
  scan_id: string
  /** running | done | failed | never | unknown */
  status: string
  trigger: string | null
  started_at: string | null
  finished_at: string | null
  sources_total: number
  sources_done: number
  items_seen: number
  new_count: number
  baseline_count: number
  per_source: KsAnnouncePerSource[]
  recent: KsAnnounceRecentItem[]
  error: string | null
}

export interface KsAnnounceSummary {
  ok: boolean
  last: KsAnnounceLast | null
  /** 上次扫描 running 遗留且无人接管（dsh 重启中断）→ UI 提示疑似中断。 */
  stale_run: boolean
}

/** GET /ks/announce/summary — 本地快照；绝不拉起引擎。 */
export async function fetchAnnounceSummary(signal?: AbortSignal): Promise<KsAnnounceSummary> {
  const res = await fetch('/ks/announce/summary', {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as Partial<KsAnnounceSummary> | null
  if (body === null || body.ok !== true) throw new Error('公告发现状态响应异常')
  return { ok: true, last: body.last ?? null, stale_run: body.stale_run === true }
}

/** POST /ks/announce/scan — 手动扫描（force=true，无视引擎 6h 时间闸）。 */
export async function scanAnnounceSources(signal?: AbortSignal): Promise<KsAnnounceLast | null> {
  const res = await fetch('/ks/announce/scan', {
    method: 'POST',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: { last?: KsAnnounceLast } | KsAnnounceLast } | null
  if (body === null || body.ok !== true) throw new Error('公告扫描启动响应异常')
  const data = body.data as { last?: KsAnnounceLast } | KsAnnounceLast | undefined
  if (data && typeof data === 'object' && 'last' in data) return (data as { last?: KsAnnounceLast }).last ?? null
  return (data as KsAnnounceLast) ?? null
}

/** GET /ks/announce/sources — 源清单（纯代理引擎；UI 展开「源管理」时才调用）。 */
export async function fetchAnnounceSources(signal?: AbortSignal): Promise<{ sources: KsAnnounceSource[]; total: number; enabled_count: number }> {
  const res = await fetch('/ks/announce/sources', {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: { sources?: KsAnnounceSource[]; total?: number; enabled_count?: number } } | null
  if (body === null || body.ok !== true || body.data === undefined) throw new Error('公告源清单响应异常')
  return {
    sources: body.data.sources ?? [],
    total: body.data.total ?? 0,
    enabled_count: body.data.enabled_count ?? 0,
  }
}

/** POST /ks/announce/sources — 新增源（引擎校验：必填/http(s)/公网/去重/上限 50）。 */
export async function addAnnounceSource(name: string, url: string, note = '', signal?: AbortSignal): Promise<KsAnnounceSource> {
  const res = await fetch('/ks/announce/sources', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ name, url, note }),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: { source?: KsAnnounceSource } } | null
  if (body === null || body.ok !== true || body.data?.source === undefined) throw new Error('公告源添加响应异常')
  return body.data.source
}

/** PUT /ks/announce/sources/{id} — 部分更新（name/enabled/note/url；改 URL 重置基线）。 */
export async function updateAnnounceSource(id: string, patch: Partial<Pick<KsAnnounceSource, 'name' | 'enabled' | 'note' | 'url'>>, signal?: AbortSignal): Promise<KsAnnounceSource> {
  const res = await fetch(`/ks/announce/sources/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(patch),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: { source?: KsAnnounceSource } } | null
  if (body === null || body.ok !== true || body.data?.source === undefined) throw new Error('公告源更新响应异常')
  return body.data.source
}

/** POST /ks/announce/export — 导出《公告发现》Excel（最近扫描源状态 + 明细全量，
 *  两步代理 → blob 下载）。 */
export async function exportAnnounceDiscovery(signal?: AbortSignal): Promise<void> {
  const res = await fetch('/ks/announce/export', {
    method: 'POST',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const blob = await res.blob()
  const name = filenameFromDisposition(res.headers.get('content-disposition')) ?? '公告发现.xlsx'
  const url = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }
}
/** DELETE /ks/announce/sources/{id} — 删除源（引擎侧历史公告记录保留）。 */
export async function removeAnnounceSource(id: string, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`/ks/announce/sources/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
}

/* ------------------------------------------------------------------ *
 * 效力报告（决策 21 · 用户修订版：按文件目录分类体系，永不混排）
 * 全部同源走 host 代理 /ks/report/*（纯代理零缓存——即时聚合快照）。
 * ------------------------------------------------------------------ */

export interface KsEffectColors {
  red: number
  yellow: number
  green: number
  gray: number
}

export interface KsEffectTreeNode {
  top?: string
  name: string
  colors: KsEffectColors
  items?: KsEffectTreeNode[]
  count?: number
}

export interface KsEffectReport {
  generated_at: string
  window: string
  colors: KsEffectColors
  total: number
  std: { total: number; colors: KsEffectColors }
  law: { total: number; colors: KsEffectColors }
  tree: KsEffectTreeNode[]
}

export interface KsEffectDoc {
  doc_id: string | null
  standard_no: string | null
  standard_name: string | null
  status: string | null
  color: 'red' | 'yellow' | 'green' | 'gray'
  effective_from: string | null
  published_at: string | null
  superseded_by: string | null
  withdrawn_date: string | null
}

export interface KsEffectDocs {
  colors: KsEffectColors
  count: number
  offset: number
  docs: KsEffectDoc[]
}

export type KsEffectWindow = 'all' | 'upcoming90' | 'recent90' | 'retired90'

function qsOf(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

/** GET /ks/report/effect — 骨架 + 四色统计（秒级同步聚合）。
 *  color：可选 CSV 子集（如 "red" 或 "red,yellow"）→ 全局色清单视图。 */
export async function fetchEffectReport(
  window: KsEffectWindow = 'all',
  signal?: AbortSignal,
  color?: string,
): Promise<KsEffectReport> {
  const res = await fetch(`/ks/report/effect${qsOf({ window, color })}`, {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: KsEffectReport } | null
  if (body === null || body.ok !== true || body.data === undefined) throw new Error('效力报告响应异常')
  return body.data
}

/** GET /ks/report/effect/docs — 节点明细（瘦身行；未知名路径 → 200 空集）。 */
export async function fetchEffectDocs(
  params: { top: string; l2: string; l3?: string; l4?: string; window: KsEffectWindow; color?: string },
  signal?: AbortSignal,
): Promise<KsEffectDocs> {
  const res = await fetch(`/ks/report/effect/docs${qsOf(params)}`, {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: KsEffectDocs } | null
  if (body === null || body.ok !== true || body.data === undefined) throw new Error('效力报告明细响应异常')
  return body.data
}

/** POST /ks/report/export — 导出《效力报告》Excel（两步代理 → blob 下载）。 */
export async function exportEffectReport(
  window: KsEffectWindow = 'all',
  signal?: AbortSignal,
  color?: string,
): Promise<void> {
  const res = await fetch('/ks/report/export', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(color ? { window, color } : { window }),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const blob = await res.blob()
  const name = filenameFromDisposition(res.headers.get('content-disposition')) ?? '效力报告.xlsx'
  const url = URL.createObjectURL(blob)
  try {
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }
}

/* ------------------------------------------------------------------ *
 * API 配置（2026-09-08）：云 OCR / LLM 凭据——同源走 host 代理
 * /ks/settings/api-config*（引擎写 HKCU 注册表；host 与前端均不回显 Key）。
 * ------------------------------------------------------------------ */

export interface KsApiChannelStatus {
  configured: boolean
  base_url: string
}

export interface KsApiConfigStatus {
  mineru_cloud: KsApiChannelStatus
  llm: KsApiChannelStatus
}

export type KsApiChannel = 'mineru_cloud' | 'llm'

/** GET /ks/settings/api-config — 脱敏状态（绝不回显 Key）。 */
export async function fetchApiConfig(signal?: AbortSignal): Promise<KsApiConfigStatus> {
  const res = await fetch('/ks/settings/api-config', {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as (Partial<KsApiConfigStatus> & { ok?: boolean }) | null
  if (body === null || body.ok !== true) throw new Error('API 配置状态响应异常')
  return {
    mineru_cloud: body.mineru_cloud ?? { configured: false, base_url: '' },
    llm: body.llm ?? { configured: false, base_url: '' },
  }
}

/** PUT /ks/settings/api-config — 写入凭据（空字段跳过，留空即保持不变）。 */
export async function saveApiConfig(
  payload: { mineru_cloud?: { api_key?: string; base_url?: string }; llm?: { api_key?: string; base_url?: string } },
  signal?: AbortSignal,
): Promise<KsApiConfigStatus> {
  const res = await fetch('/ks/settings/api-config', {
    method: 'PUT',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as (Partial<KsApiConfigStatus> & { ok?: boolean }) | null
  if (body === null || body.ok !== true) throw new Error('API 配置保存响应异常')
  return {
    mineru_cloud: body.mineru_cloud ?? { configured: false, base_url: '' },
    llm: body.llm ?? { configured: false, base_url: '' },
  }
}

/** POST /ks/settings/api-config/test — 活体探测（真实调上游，不含 Key）。 */
export async function testApiChannel(
  channel: KsApiChannel,
  signal?: AbortSignal,
): Promise<{ ok: boolean; detail: string }> {
  const res = await fetch('/ks/settings/api-config/test', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ channel }),
    signal,
  })
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; result?: { ok?: boolean; detail?: string } } | null
  if (body === null || body.ok !== true) throw new Error('连通性测试响应异常')
  return {
    ok: body.result?.ok === true,
    detail: typeof body.result?.detail === 'string' ? body.result.detail : '',
  }
}
