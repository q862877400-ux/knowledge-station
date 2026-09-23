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

/**
 * 取一份**已落盘的交付物**（研究报告的 `.md`/`.html`，或其它 xlsx 产物）
 * —— 2026-09-18 用户报障"设置里的导入只接受 PDF，还有 html 呢"。
 *
 * ## 为什么走引擎而不是宿主新开路由
 * 引擎**早就**有这个端点：`GET /api/v1/export/download?name=…`，而"名字必须落在
 * exports 目录内"这条防穿越纪律**由引擎一家所有**（`report_export._exports_dir()`
 * + `base not in target.parents` 判据）。客户端直连引擎（同 `fetchPdf` 的既有通路：
 * 跨源 + Bearer）即可，**不需要**在宿主侧再抄一份路径校验——那会是第二个所有者。
 * 好处还有一条：宿主/引擎都不用重启，改的是纯客户端。
 *
 * ## 边界（诚实写下来）
 * 拿回来的字节**不落盘**（`URL.createObjectURL` 用完要 revoke），所以：
 * · `.html` 可以在新标签里**渲染**（报告本体）；
 * · `.md` 只有 `text/markdown`（浏览器按纯文本显示，别指望排版）；
 * · 非网页形态的产物（如 `.xlsx`）浏览器渲染不了 ⇒ 只能下载一份，或由用户去
 *   `设置里显示的那个绝对路径` 直接打开。想"一键用系统默认程序打开"必须加
 *   宿主路由（要重启宿主），本轮**不做**，如实写在面板文案里。
 *
 * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：`.docx`/`.pptx` 两条交付物通路已拆除
 * （业主否决 Word/PPT 交付物，`docs/NOT-DOING.md` 第 1 条）。
 *
 * @param name 文件名（**只有 basename**，路径分隔符会被引擎判为非法）。
 */
export async function fetchExportBlob(name: string, signal?: AbortSignal): Promise<Blob> {
  const url = (port: number): string =>
    `http://127.0.0.1:${port}/api/v1/export/download?name=${encodeURIComponent(name)}`
  const once = async (): Promise<Response> => {
    const session = await fetchSession(signal)
    return fetch(url(session.engine.port), {
      method: 'GET',
      headers: { Authorization: `Bearer ${session.token}` },
      signal,
    })
  }
  let res: Response = await once()
  if (res.status === 401) {
    clearSession() // 会话轮换：重取一次再试（镜像 fetchPdf 语义）
    res = await once()
  }
  if (res.status === 403) throw new Error('引擎拒绝了这个文件名（只允许 exports 目录内的产物）')
  if (res.status === 404) throw new Error(`产物文件不存在（可能已被清理）：${name}`)
  if (!res.ok) throw new Error(`引擎返回 HTTP ${res.status}`)
  return res.blob()
}

/* ---------------------------------------------------------------- 渠道台账（§11.0 R4b） */

/**
 * 渠道台账走**同源宿主路由**（`/ks/channels`），不直连引擎。
 *
 * 为什么与上面那个"直连引擎取产物"不同：探针会**对外发请求**（访问二十多个政府站），
 * 必须留在宿主侧受控——谁探了哪个站、探几次、带什么 Referer 都由宿主说了算；
 * 浏览器侧发起则完全不受控，且 `Referer/Origin` 会带上 GUI 地址（对反爬是无谓信号）。
 */
export interface KsChannelRecord {
  channel_id: string
  name: string
  /** canonical 类别：law/std_gb/std_hb/std_db/std_tb/std_intl/aggregator/tool/internal/other */
  category: string
  /** 研究文档里的原始写法（证据，可能与 canonical 不同） */
  category_raw?: string | null
  /** 单位性质（2026-09-22）：central/local_congress/local_dept/industry/intl/commercial/tool/other；
   *  null=未分类。台账「文件夹树」分类的那根轴（与 category=标准类型是两回事）。 */
  org_kind?: string | null
  url?: string | null
  fetch_kind?: string | null
  /** 接线状态：wired（在巡检链上）/unwired/broken/user/seed_only */
  wiring: string
  /** 研究期实测结论：verified/unverified/broken */
  verification: string
  /** 运行期健康度：unknown/ok/suspicious/down */
  state: string
  enabled: number
  last_try_at?: string | null
  last_ok_at?: string | null
  last_error?: string | null
  last_error_code?: string | null
  consecutive_failures: number
  latency_ms?: number | null
  note?: string | null
  /**
   * 号段（§11.0 R7）："这条渠道管哪些标准号"，引擎里存成 JSON 字符串数组
   * （如 `'["HJ"]'`、`'["GB 50","GB 55"]'`）。链按它做**加法**（只加尾巴、不改顺序）。
   * ⚠ 是**字符串**（列是 TEXT + JSON），面板负责解析/序列化——别当数组直接用。
   */
  segments_json?: string | null
  /**
   * 是否有探针目标（R6，引擎按探针目标表算）。
   * 只在 `state === 'unknown'` 时有意义，且它只回答"有没有目标"：
   *   `false` = "按设计没有探针"（代码仓库/我方代码通路）；
   *   `true` 还要再看 `last_error_code` —— `no_anchor_configured` 是"探过、只探到连通性，
   *   没配语义期望"（**不算可抓**，也不是欠账），其它才是"配了还没探过"（真欠账）。
   */
  has_probe_target?: boolean
}

/** `summary()` 的形状：**台账条数与能力数刻意分开**（R1 的 G5/G6 教训）。 */
export interface KsChannelSummary {
  total: number
  by_wiring: Record<string, number>
  by_state: Record<string, number>
  enabled: number
}

export interface KsChannelList {
  summary: KsChannelSummary
  items: KsChannelRecord[]
}

/** `GET /ks/channels`（宿主白名单转发；未知参数会被宿主丢弃）。 */
export async function fetchChannels(
  params: {
    category?: string; wiring?: string; state?: string
    enabledOnly?: boolean; limit?: number
  } = {},
  signal?: AbortSignal,
): Promise<KsChannelList> {
  const qs = new URLSearchParams()
  if (params.category) qs.set('category', params.category)
  if (params.wiring) qs.set('wiring', params.wiring)
  if (params.state) qs.set('state', params.state)
  if (params.enabledOnly) qs.set('enabled_only', 'true')
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  const suffix = qs.toString()
  const res = await fetch(`/ks/channels${suffix ? `?${suffix}` : ''}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  return ksJson<KsChannelList>(res, '渠道库')
}

/**
 * 渠道台账的**人工维护**（§11.0 R6f）：新增 / 复核编辑 / 启停 / 删除。
 *
 * ⚠ 三条口径（都在宿主与引擎那一侧钉着，客户端只负责如实发起与如实显示错误）：
 *   - **健康度字段不许人工写**（`state`/`last_*`…）：引擎会 422 并说明"要改它请用探针"；
 *     客户端**不自己拦**——拦住的话用户只会看到"按钮没反应"，而看不到原因；
 *   - 启停走**自己的端点**（语义与留痕都不同），不要塞进 PATCH；
 *   - 删除是高风险动作：界面必须**先让人确认**（`window.confirm`），
 *     但删除**不是抹掉证据**（引擎的审计痕迹里保留删除前整行）。
 */
export async function createChannel(
  body: { name: string; url?: string; note?: string; category?: string } & Record<string, unknown>,
  signal?: AbortSignal,
): Promise<KsChannelRecord> {
  const res = await fetch('/ks/channels', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  return ksJson<KsChannelRecord>(res, '新增渠道')
}

export async function updateChannel(
  channelId: string, patch: Record<string, unknown>, signal?: AbortSignal,
): Promise<KsChannelRecord> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(patch),
    signal,
  })
  return ksJson<KsChannelRecord>(res, '修改渠道')
}

export async function setChannelEnabled(
  channelId: string, enabled: boolean, signal?: AbortSignal,
): Promise<KsChannelRecord> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}/enabled`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ enabled }),
    signal,
  })
  return ksJson<KsChannelRecord>(res, '启停渠道')
}

export async function deleteChannel(
  channelId: string, signal?: AbortSignal,
): Promise<{ deleted: boolean; channel_id: string }> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}`, {
    method: 'DELETE', headers: { accept: 'application/json' }, signal,
  })
  return ksJson<{ deleted: boolean; channel_id: string }>(res, '删除渠道')
}

/** 批C（2026-09-22）：渠道「已知文件测试」——样本 + 最近一次留痕。 */
export interface KsChannelTestCase {
  channel_id: string
  sample_url: string
  expect_no: string
  note?: string | null
  last_result?: string | null
  last_detail?: string | null
  last_run_at?: string | null
}

export async function getChannelTestCase(channelId: string, signal?: AbortSignal): Promise<KsChannelTestCase | null> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}/test-case`, {
    method: 'GET', cache: 'no-store', ...(signal ? { signal } : {}),
  })
  const body = await ksJson<{ test_case?: KsChannelTestCase | null }>(res, '读渠道测试样本')
  return body.test_case ?? null
}

export async function setChannelTestCase(
  channelId: string, sampleUrl: string, expectNo: string, note?: string,
  signal?: AbortSignal,
): Promise<KsChannelTestCase> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}/test-case`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ sample_url: sampleUrl, expect_no: expectNo, ...(note ? { note } : {}) }),
    ...(signal ? { signal } : {}),
  })
  const body = await ksJson<{ test_case?: KsChannelTestCase }>(res, '配渠道测试样本')
  return body.test_case as KsChannelTestCase
}

export async function runChannelTest(
  channelId: string, signal?: AbortSignal,
): Promise<{ result: string; detail: string; got?: string }> {
  const res = await fetch(`/ks/channels/${encodeURIComponent(channelId)}/test`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({}),
    ...(signal ? { signal } : {}),
  })
  return ksJson<{ result: string; detail: string; got?: string }>(res, '渠道已知文件测试')
}

export interface KsChannelProbeResult {
  probed: number
  results: Array<{
    channel_id: string; state: string; error_code?: string | null
    error?: string | null; latency_ms?: number | null; http?: number | null
  }>
  counts: Record<string, number>
  without_target: string[]
  summary: KsChannelSummary
}

/**
 * `POST /ks/channels/probe` —— **立刻探一遍**（人工动作）。
 *
 * ⚠ 省略 `ids` 时只探**配了探针目标的**渠道（今天 28 条），不会盲探 131 条；
 * ⚠ 单条最长 20s、宿主总超时 150s ⇒ 界面侧不要再套更短的超时（那会把慢站点判成失败）。
 */
export async function runChannelProbe(
  ids?: string[], signal?: AbortSignal,
): Promise<KsChannelProbeResult> {
  const res = await fetch('/ks/channels/probe', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(ids && ids.length > 0 ? { ids, persist: true } : { persist: true }),
    signal,
  })
  return ksJson<KsChannelProbeResult>(res, '渠道探测')
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
 * 端点接线（2026-09-13）：文档富文本 + 三图片端点（ZERO→LIVE）
 *
 *   fetchDocClauses  → 跨源 GET /api/v1/documents/{id}/clauses（Bearer）
 *                      每条款 content_html 已由引擎注入 fig-embed / table-embed /
 *                      katex-formula 占位（无 src——图片端点受 token 保护，
 *                      裸 <img src> 必 401；正文视图 effect 逐个拉 blob）。
 *   fetchDocImage    → 同源 GET /ks/doc-image/...（host 代理，token 不出 host）
 *                      返回 objectURL + X-Frac-* 比例头（截图按原版还原）。
 * ------------------------------------------------------------------ */

/** One rich clause row from GET /api/v1/documents/{doc_id}/clauses. */
export interface KsDocClause {
  clause_revision_id: string
  clause_number: string | null
  title: string | null
  content_text: string | null
  content_html: string | null
  page_start: number | null
  page_end: number | null
}

function normalizeDocClause(value: unknown): KsDocClause | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const id = str(o.clause_revision_id)
  if (id === null) return null
  return {
    clause_revision_id: id,
    clause_number: str(o.clause_number),
    title: str(o.title),
    content_text: str(o.content_text),
    content_html: str(o.content_html),
    page_start: num(o.page_start),
    page_end: num(o.page_end),
  }
}

/**
 * 某文档全部条款富文本（正文视图数据源）。引擎 404（无条款）→ 空数组
 * （调用方显示空态，不是错误）；401 → EngineAuthError（会话轮换）。
 */
export async function fetchDocClauses(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
): Promise<KsDocClause[]> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/documents/${encodeURIComponent(docId)}/clauses`,
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
  if (res.status === 404) return []
  if (!res.ok) throw new Error(`引擎返回 HTTP ${res.status}`)
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  // 引擎信封 = {code:200, data:{doc_id, clauses:[…]}}——条款数组在 data.clauses
  // （E2E 实测 2026-09-13；兼容裸数组 data——测试桩/未来形态）。
  const envelope = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>) : null
  const raw = envelope?.data
  const list = raw !== null && typeof raw === 'object'
    && Array.isArray((raw as Record<string, unknown>).clauses)
    ? (raw as Record<string, unknown>).clauses as unknown[]
    : Array.isArray(raw) ? raw : []
  return list
    .map(normalizeDocClause)
    .filter((c): c is KsDocClause => c !== null)
}

/** fetchDocImage 结果：objectURL 交给 <img src>；frac 头按比例还原尺寸。 */
export interface DocImageResult {
  url: string
  frac: { x0: number | null, w: number | null, h: number | null }
}

/**
 * 同源拉一张文档图（经 host /ks/doc-image 代理——引擎 token 只在 host 侧）。
 * 404 → NOT_FOUND（调用方隐藏占位）；其他非 200 抛错。
 * 调用方负责在卸载时 revoke objectURL。
 */
export const DOC_IMAGE_NOT_FOUND: unique symbol = Symbol('ks-doc-image-not-found')
export type FetchDocImageOutcome = DocImageResult | typeof DOC_IMAGE_NOT_FOUND

export async function fetchDocImage(
  kind: 'figure' | 'formula' | 'table-image',
  parts: { docId: string, no?: string, clause?: string, page?: number, tbl?: number },
  dpi?: number,
  signal?: AbortSignal,
): Promise<FetchDocImageOutcome> {
  const enc = encodeURIComponent
  let path: string
  if (kind === 'figure') {
    path = `/ks/doc-image/${enc(parts.docId)}/figure/${enc(parts.no ?? '')}`
  } else if (kind === 'formula') {
    path = `/ks/doc-image/${enc(parts.docId)}/formula/${enc(parts.no ?? '')}?clause=${enc(parts.clause ?? '')}`
  } else {
    path = `/ks/doc-image/${enc(parts.docId)}/table-image/${parts.page ?? 0}/${parts.tbl ?? 0}`
  }
  const url = path + (typeof dpi === 'number' ? `&dpi=${Math.round(dpi)}` : '')
    // formula 分支已带 ?clause=…，追加用 &；figure/table-image 无 query → ?
    .replace(/^([^?]+)&/, '$1?')
  const res = await fetch(url, { method: 'GET', signal })
  if (res.status === 404) return DOC_IMAGE_NOT_FOUND
  if (!res.ok) throw new Error(`图片代理返回 HTTP ${res.status}`)
  const blob = await res.blob()
  // 引擎未给 Content-Type 时 host 兜底 octet-stream——消费端必须拒绝（不猜类型）。
  const ct = res.headers.get('content-type') ?? ''
  if (!ct.startsWith('image/')) {
    throw new Error(`图片代理返回了非图片内容 (content-type: ${ct || 'unknown'})`)
  }
  const fnum = (v: string | null): number | null => {
    const n = typeof v === 'string' ? Number.parseFloat(v) : NaN
    return Number.isFinite(n) ? n : null
  }
  return {
    url: URL.createObjectURL(blob),
    frac: {
      x0: fnum(res.headers.get('x-frac-x0')),
      w: fnum(res.headers.get('x-frac-w')),
      h: fnum(res.headers.get('x-frac-h')),
    },
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
  folderId?: string | null,
): Promise<{ existed: boolean }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmarks`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ clause_key: clauseKey, ...(folderId != null ? { folder_id: folderId } : {}) }),
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

/** POST a standard-level bookmark by doc_id. Idempotent (existed flag). */
export async function addDocBookmark(
  port: number,
  docId: string,
  token: string,
  signal?: AbortSignal,
  folderId?: string | null,
): Promise<{ existed: boolean }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/doc-bookmarks`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ doc_id: docId, ...(folderId != null ? { folder_id: folderId } : {}) }),
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
 * 收藏夹目录 (2026-10) — /api/v1/bookmark-folders CRUD + tree + move。
 * 一条收藏同一时间只属于一个夹（改选 = 移动）；删夹不删收藏（回未分类）。
 * ------------------------------------------------------------------ */

/** One bookmark folder row (with per-folder counts from the engine). */
export interface KsBookmarkFolder {
  folder_id: string
  folder_name: string
  created_at: string | null
  doc_count: number
  clause_count: number
}

/** 夹内一个文档节点（树端点返回；doc 级收藏=整本入范围，clause 级=单条）。 */
export interface KsFolderDocNode {
  doc_id: string
  doc_bookmark_id: string | null
  standard_no: string | null
  standard_name: string | null
  legal_status: string | null
  doc_bookmarked: boolean
  clause_bookmarks: Array<{
    bookmark_id: string
    clause_key: string
    clause_number: string | null
    title: string | null
    page_start: number | null
  }>
  /** 文件目录同款的分类路径（L1→L2→L3→L4）；无法分类时 null。 */
  path: { l1: string | null; l2: string | null; l3: string | null; l4: string | null } | null
}

/** One folder from the tree endpoint: folder meta + its doc nodes. */
export interface KsFolderTreeFolder {
  folder_id: string | null // null = 未分类 pseudo-folder
  folder_name: string
  created_at: string | null
  doc_count: number
  clause_count: number
  docs: KsFolderDocNode[]
}

function normalizeFolder(value: unknown): KsBookmarkFolder | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const id = str(o.folder_id)
  const name = str(o.folder_name)
  if (id === null || name === null) return null
  return {
    folder_id: id,
    folder_name: name,
    created_at: typeof o.created_at === 'string' ? o.created_at : null,
    doc_count: num(o.doc_count) ?? 0,
    clause_count: num(o.clause_count) ?? 0,
  }
}

function normalizeFolderTreeFolder(value: unknown): KsFolderTreeFolder | null {
  if (value === null || typeof value !== 'object') return null
  const o = value as Record<string, unknown>
  const name = str(o.folder_name)
  if (name === null) return null
  const rawDocs = Array.isArray(o.docs) ? o.docs : []
  const docs: KsFolderDocNode[] = []
  for (const d of rawDocs) {
    if (d === null || typeof d !== 'object') continue
    const dd = d as Record<string, unknown>
    const docId = str(dd.doc_id)
    if (docId === null) continue
    const rawPath = (dd.path !== null && typeof dd.path === 'object')
      ? dd.path as Record<string, unknown>
      : null
    const rawClauseBms = Array.isArray(dd.clause_bookmarks) ? dd.clause_bookmarks : []
    docs.push({
      doc_id: docId,
      doc_bookmark_id: str(dd.doc_bookmark_id),
      standard_no: str(dd.standard_no),
      standard_name: str(dd.standard_name),
      legal_status: str(dd.legal_status),
      doc_bookmarked: dd.doc_bookmarked === true,
      clause_bookmarks: rawClauseBms.flatMap((cb) => {
        if (cb === null || typeof cb !== 'object') return []
        const c = cb as Record<string, unknown>
        const bmId = str(c.bookmark_id)
        const clauseKey = str(c.clause_key)
        if (bmId === null || clauseKey === null) return []
        return [{
          bookmark_id: bmId,
          clause_key: clauseKey,
          clause_number: str(c.clause_number),
          title: str(c.title),
          page_start: num(c.page_start),
        }]
      }),
      path: rawPath === null ? null : {
        l1: str(rawPath.l1),
        l2: str(rawPath.l2),
        l3: str(rawPath.l3),
        l4: str(rawPath.l4),
      },
    })
  }
  return {
    folder_id: str(o.folder_id), // null = 未分类
    folder_name: name,
    created_at: typeof o.created_at === 'string' ? o.created_at : null,
    doc_count: num(o.doc_count) ?? docs.length,
    clause_count: num(o.clause_count) ?? docs.reduce((s, d) => s + d.clause_bookmarks.length, 0),
    docs,
  }
}

/** GET the folder list (no doc nodes). */
export async function fetchBookmarkFolders(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<KsBookmarkFolder[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(`收藏夹列表获取失败(HTTP ${res.status})`)
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON */ }
  return unwrapList(body)
    .map(normalizeFolder)
    .filter((f): f is KsBookmarkFolder => f !== null)
}

/** GET the full folder tree (folder list + per-folder doc nodes). */
export async function fetchBookmarkFolderTree(
  port: number,
  token: string,
  signal?: AbortSignal,
): Promise<KsFolderTreeFolder[]> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders/tree`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(`收藏目录获取失败(HTTP ${res.status})`)
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON */ }
  return unwrapList(body)
    .map(normalizeFolderTreeFolder)
    .filter((f): f is KsFolderTreeFolder => f !== null)
}

/** POST a new folder {folder_name} → conflict surfaces as a typed error. */
export async function createBookmarkFolder(
  port: number,
  folderName: string,
  token: string,
  signal?: AbortSignal,
): Promise<KsBookmarkFolder> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ folder_name: folderName }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (res.status === 409) {
    throw new Error(`收藏夹「${folderName}」已存在`)
  }
  if (!res.ok) throw new Error(`新建收藏夹失败(HTTP ${res.status})`)
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON */ }
  const data = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>).data
    : null
  const folder = normalizeFolder(data)
  if (folder === null) throw new Error('新建收藏夹返回数据异常')
  return folder
}

/** PUT rename a folder. */
export async function renameBookmarkFolder(
  port: number,
  folderId: string,
  folderName: string,
  token: string,
  signal?: AbortSignal,
): Promise<KsBookmarkFolder> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders/${encodeURIComponent(folderId)}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ folder_name: folderName }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (res.status === 409) throw new Error(`收藏夹「${folderName}」已存在`)
  if (!res.ok) throw new Error(`重命名收藏夹失败(HTTP ${res.status})`)
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON */ }
  const data = body !== null && typeof body === 'object'
    ? (body as Record<string, unknown>).data
    : null
  const folder = normalizeFolder(data)
  if (folder === null) throw new Error('重命名收藏夹返回数据异常')
  return folder
}

/** DELETE a folder. Bookmarks inside fall back to 未分类 (never deleted). */
export async function deleteBookmarkFolder(
  port: number,
  folderId: string,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders/${encodeURIComponent(folderId)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(`删除收藏夹失败(HTTP ${res.status})`)
}

/** POST move one clause bookmark to a folder (null = 未分类). */
export async function moveClauseBookmark(
  port: number,
  clauseKey: string,
  folderId: string | null,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders/move-clause`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ clause_key: clauseKey, folder_id: folderId }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(`移动条款收藏失败(HTTP ${res.status})`)
}

/** POST move one doc bookmark to a folder (null = 未分类). */
export async function moveDocBookmark(
  port: number,
  docId: string,
  folderId: string | null,
  token: string,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/bookmark-folders/move-doc`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ doc_id: docId, folder_id: folderId }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(`移动标准收藏失败(HTTP ${res.status})`)
}

/* ------------------------------------------------------------------ *
 * 会话开关（查法规/仅收藏/收藏夹内提问）— host 路由 GET/PUT /ks/chat-mode
 * （host 状态不经引擎；folderId: null 关夹范围，'bmf_…'+folderName 开）
 * ------------------------------------------------------------------ */

/** Normalized chat-mode from the host route. */
export interface KsChatMode {
  forensic: boolean
  bookmarksOnly: boolean
  folderId: string | null
  folderName: string | null
}

/** Read a session's chat-mode from the host route (same-origin, no token). */
export async function fetchChatMode(sessionId: string, signal?: AbortSignal): Promise<KsChatMode> {
  const res = await fetch(`/ks/chat-mode?session=${encodeURIComponent(sessionId)}`, {
    method: 'GET',
    headers: { accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw new Error(`会话开关读取失败(HTTP ${res.status})`)
  const body = await res.json() as {
    mode?: { forensic?: unknown; bookmarksOnly?: unknown; folderId?: unknown; folderName?: unknown }
  }
  const m = body.mode ?? {}
  return {
    forensic: m.forensic === true,
    bookmarksOnly: m.bookmarksOnly === true,
    folderId: typeof m.folderId === 'string' && m.folderId.length > 0 ? m.folderId : null,
    folderName: typeof m.folderName === 'string' && m.folderName.length > 0 ? m.folderName : null,
  }
}

/**
 * Patch a session's chat-mode via the host route. Only the provided fields
 * are updated (partial PUT). Returns the normalized mode + persist health.
 */
export async function patchChatMode(
  sessionId: string,
  patch: {
    forensic?: boolean
    bookmarksOnly?: boolean
    folderId?: string | null
    folderName?: string
  },
  signal?: AbortSignal,
): Promise<{ mode: KsChatMode; persisted: boolean; persistError: string | null }> {
  const res = await fetch('/ks/chat-mode', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ session: sessionId, ...patch }),
    signal,
  })
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json() as { error?: { message?: string } }
      if (body?.error?.message) message = body.error.message
    } catch { /* non-JSON */ }
    throw new Error(`会话开关更新失败: ${message}`)
  }
  const body = await res.json() as {
    mode?: { forensic?: unknown; bookmarksOnly?: unknown; folderId?: unknown; folderName?: unknown }
    persisted?: boolean
    persist_error?: string
  }
  const m = body.mode ?? {}
  return {
    mode: {
      forensic: m.forensic === true,
      bookmarksOnly: m.bookmarksOnly === true,
      folderId: typeof m.folderId === 'string' && m.folderId.length > 0 ? m.folderId : null,
      folderName: typeof m.folderName === 'string' && m.folderName.length > 0 ? m.folderName : null,
    },
    persisted: body.persisted === true,
    persistError: typeof body.persist_error === 'string' ? body.persist_error : null,
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

/** 五类**问题**的结论统计（发布/修订/废止/现行性/编号核验）——
 *  ⚠ 与上面的 `KsInspectionByType`（变更**事件类型**）不是一回事，别混。
 *  数据来自引擎写在每条变更事件 `latest_info.classes` 里的逐类结论（§11.0 R6c-4c），
 *  宿主在批次收尾时归组进来；**这是这份数据第一次被 UI 读到**。 */
export interface KsInspectionClassStat {
  answered: number
  /** 未答原因 → 条数（`channel_gave_no_field` / `not_probed` / `no_capability` / …）。 */
  reasons: Record<string, number>
}

export interface KsInspectionByClass {
  /** 分母：**真的记了 `classes`** 的事件数（不是批次的号数）。 */
  total: number
  /** 没记五类的事件数（引擎未写或旧数据）——如实显示，不当成"答不出来"。 */
  unreadable: number
  classes: Record<string, KsInspectionClassStat>
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
  /** 五类问题的结论统计；旧状态文件或本次没取到 ⇒ null（UI 只说"没取到"，不说"没有欠账"）。 */
  by_class: KsInspectionByClass | null
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
  /** 识别率（各条款 OCR 置信度的中位数）。⚠ **算不出来时是 `null`**（一条条款都没切出来），
   *  不是 `0.0` —— 2026-09-21 第 5 步统一的口径（入库侧 `doc_filing_state.confidence` 同样是 NULL）。
   *  界面必须把 `null` 显示成"算不出来"，**不许**显示成 0%。 */
  doc_confidence: number | null
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
  /** 请求级：本次预览**是否禁用**深度通道。默认 true（不外发）；
   *  仅当调用方显式 `allow_deep=true` 时为 false（2026-09-17 D5 前恒为 true） */
  deep_fallback_disabled?: boolean
  /** 文档级：这份文档真的走到「本该深度分析却被跳过」的分支（无文本层才 true） */
  deep_fallback_skipped: boolean
  /** 外发标注（D5）。`none` = 本次不可能外发（默认）；
   *  `deep_channel` = 本次**允许**了云优先的深度通道（**保守高报**：哪怕该文档恰好有文本层、
   *  深度通道并未真的被调用，也报这个值）。真实外发以 `egress_audit` 落库为准。 */
  egress: 'none' | 'deep_channel'
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
  /** 同 `KsIngestReport.doc_confidence`：**算不出来是 `null`**（不是 0.0）。 */
  doc_confidence: number | null
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
  /** 批量总账的外发标注（同单文件口径，见 `KsIngestPreview.egress`） */
  egress: 'none' | 'deep_channel'
}

/** 同源 host 代理的错误（保留 host/引擎的错误码，UI 才能给出可行动提示）。 */
class KsIngestHttpError extends Error {
  constructor(
    httpStatus: number,
    code: string | null,
    message: string,
  ) {
    super(message)
    this.name = 'KsIngestHttpError'
    this.httpStatus = httpStatus
    this.code = code
  }
  readonly httpStatus: number
  readonly code: string | null
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
  path: string,
  opts: { docType?: string; allowDeep?: boolean; signal?: AbortSignal } = {},
): Promise<KsIngestReport> {
  // allowDeep 只在为真时才发（与 host 桥的严格布尔转发一致）：默认"字段不出现"，
  // 语义与"显式 false"等价，但请求体最小、也不给引擎的严格校验添麻烦。
  const payload: Record<string, unknown> = {
    path, doc_type: opts.docType ?? 'standard',
  }
  if (opts.allowDeep === true) payload.allow_deep = true
  const res = await fetch('/ks/ingest/preview', {
    method: 'POST',
    headers: { accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
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
  req: { dir: string; sample?: number; limitFiles?: number; docType?: string; allowDeep?: boolean },
  signal?: AbortSignal,
): Promise<KsIngestBatch> {
  const payload: Record<string, unknown> = { dir: req.dir }
  if (req.sample !== undefined) payload.sample = req.sample
  if (req.limitFiles !== undefined) payload.limit_files = req.limitFiles
  if (req.docType !== undefined) payload.doc_type = req.docType
  if (req.allowDeep === true) payload.allow_deep = true
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

/** 异步全量预览任务（2026-09-12 L239）：启动/进度/中断三件套。 */
export interface KsIngestJobView {
  job_id: string
  status: 'pending' | 'running' | 'done' | 'aborted' | 'failed'
  total: number
  done: number
  buckets: { ok: number; warn: number; block: number }
  rows: KsIngestBatchRow[]
  rows_count?: number
  /** 外发标注（D5/F3）：与单文件预览同口径——`none` = 不可能外发；
   *  `deep_channel` = 本任务**允许**了云深度通道（保守高报，真实外发见外发审计）。 */
  egress?: 'none' | 'deep_channel'
  error: string | null
  stale?: boolean
}

/** POST /ks/ingest/preview/jobs — 启动异步全量预览（万级；立即返回 job_id）。 */
export async function startIngestJob(
  req: { dir: string; recursive?: boolean; batchSize?: number; docType?: string; allowDeep?: boolean },
  signal?: AbortSignal,
): Promise<KsIngestJobView> {
  const payload: Record<string, unknown> = { dir: req.dir }
  if (req.recursive === true) payload.recursive = true
  if (req.batchSize !== undefined && req.batchSize > 0) payload.batch_size = req.batchSize
  if (req.docType !== undefined) payload.doc_type = req.docType
  if (req.allowDeep === true) payload.allow_deep = true
  const res = await fetch('/ks/ingest/preview/jobs', {
    method: 'POST',
    headers: { accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; data?: KsIngestJobView } | null
  if (body?.ok !== true || body.data === undefined) throw new Error('全量预览启动响应异常')
  return body.data
}

/** GET /ks/ingest/preview/jobs/{id} — 任务进度（引擎 live 值优先，镜像快照兜底）。 */
export async function fetchIngestJob(
  jobId: string,
  opts: { rowsOffset?: number; rowsLimit?: number; signal?: AbortSignal } = {},
): Promise<KsIngestJobView> {
  const qs = new URLSearchParams({
    rows_offset: String(opts.rowsOffset ?? 0),
    rows_limit: String(opts.rowsLimit ?? 200),
  })
  const res = await fetch(`/ks/ingest/preview/jobs/${encodeURIComponent(jobId)}?${qs}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal: opts.signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; data?: KsIngestJobView } | null
  if (body?.ok !== true || body.data === undefined) throw new Error('全量预览进度响应异常')
  return body.data
}

/** POST /ks/ingest/preview/jobs/{id}/abort — 协作式中断（已完成行保留）。 */
export async function abortIngestJob(jobId: string, signal?: AbortSignal): Promise<KsIngestJobView> {
  const res = await fetch(`/ks/ingest/preview/jobs/${encodeURIComponent(jobId)}/abort`, {
    method: 'POST',
    headers: { accept: 'application/json', 'Content-Type': 'application/json' },
    body: '{}',
    signal,
  })
  if (!res.ok) throw await parseIngestError(res)
  const body = (await res.json().catch(() => null)) as
    { ok?: boolean; data?: KsIngestJobView } | null
  if (body?.ok !== true || body.data === undefined) throw new Error('全量预览中断响应异常')
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

/** 外发审计一条记录（脱敏摘要；形状逐字段抄引擎 `_row_to_audit`，防御式读取）。 */
export interface KsEgressAuditRecord {
  dump_id?: unknown
  created_at?: unknown
  service?: unknown
  endpoint?: unknown
  query?: unknown
  payload_bytes?: unknown
  prompt_preview?: unknown
  [k: string]: unknown
}

export interface KsEgressAudit {
  total: number
  items: KsEgressAuditRecord[]
}

/**
 * S2-a2（2026-09-22）：外发审计**只读**列表（GET /api/v1/egress/audit）。
 * 引擎直连 + Bearer（fetchDocClauses 同一信任模型）；这是外发审计读口**第一次**接到界面
 * （诊断 E：「客户端零调用」——引擎 2026-09-08 就有，界面一直够不着）。
 * 分页：limit/offset（引擎还支持 keyset cursor，界面首版翻页到 50 条够用、如实报 total）。
 */
export async function fetchEgressAudit(
  params: { limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<KsEgressAudit> {
  const { token, engine: { port } } = await fetchSession(signal)
  const qs = new URLSearchParams()
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.offset !== undefined) qs.set('offset', String(params.offset))
  const suffix = qs.toString()
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/egress/audit${suffix ? `?${suffix}` : ''}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw new Error(await engineErrorMessage(res, `外发审计读取失败（HTTP ${res.status}）`))
  const body = (await res.json().catch(() => null)) as { code?: number; data?: KsEgressAudit } | null
  const data = body?.data
  if (data === null || data === undefined || typeof data !== 'object' || !Array.isArray(data.items)) {
    throw new Error('外发审计响应异常（期望 {code:200,data:{total,items}}）——不要把本次当作"没有外发记录"')
  }
  return { total: Number(data.total ?? data.items.length), items: data.items }
}

/**
 * 导出**Markdown**（红线：产出物只出 Markdown）。纯函数：审计行 → MD 文本；
 * 下载动作在界面层。引擎自带的 JSON 导出**保持原样不动**（数据归档用途不同，不冲突）。
 * ⚠ 文本里不许出现字面 `**`（语言规范 §二.6）。
 */
export function buildEgressMarkdown(total: number, items: KsEgressAuditRecord[]): string {
  const str = (v: unknown): string => (typeof v === 'string' ? v : v === null || v === undefined ? '' : String(v))
  const lines: string[] = []
  lines.push('# 外发审计记录')
  lines.push('')
  lines.push(`共 ${String(total)} 条外发（每次调用云端的完整留痕；本表为脱敏摘要）。`)
  lines.push('')
  items.forEach((it, i) => {
    lines.push(`## ${String(i + 1)}. ${str(it.created_at)} · ${str(it.service)}`)
    lines.push('')
    lines.push(`- 端点：${str(it.endpoint) || '—'}`)
    lines.push(`- 请求：${str(it.query) || '—'}`)
    lines.push(`- 外发字节：${str(it.payload_bytes) || '—'}`)
    lines.push(`- 内容摘要：${str(it.prompt_preview) || '—'}`)
    lines.push(`- 留痕编号：${str(it.dump_id) || '—'}`)
    lines.push('')
  })
  return lines.join('\n')
}

/* ============================================================================
   义务清单 / 差距分析（S2-b2，2026-09-22）。契约逐字抄 compliance/obligation.py 与
   gap_analysis.py 的返回：
     POST /api/v1/compliance/obligations {business_description}
       → {list_id, business_description, groups:[{group, items}], count}
       item = {clause_revision_id, standard_no, clause_number, obligation_text, group, checked}
     POST /api/v1/compliance/obligations/{id}/checklist → 同上 + item.question + mode:'checklist'
     POST /api/v1/compliance/obligations/{id}/check {clause_revision_id, checked} → {updated:true}
     POST /api/v1/compliance/policies {policy_name, policy_text} → {policy_id, sections}
     POST /api/v1/compliance/gap-analysis {policy_id}
       → {task_id, counts:{red,yellow,green}, policy_name,
          results:[{obligation, verdict, hit, ratio, suggestion, domain}]}
   ============================================================================ */

export interface KsGapResult {
  task_id: string
  counts: { red: number; yellow: number; green: number }
  results: { obligation?: unknown; verdict?: unknown; hit?: unknown; ratio?: unknown; suggestion?: unknown; domain?: unknown }[]
  policy_name: string
}

async function compliancePost<T>(path: string, body: Record<string, unknown>, what: string, signal?: AbortSignal): Promise<T> {
  const { token, engine: { port } } = await fetchSession(signal)
  const res = await fetch(`http://127.0.0.1:${port}${path}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(await engineErrorMessage(res, `${what}失败（HTTP ${res.status}）`))
  const out = (await res.json().catch(() => null)) as { code?: number; data?: T } | null
  if (out?.data === null || out?.data === undefined) throw new Error(`${what}响应异常`)
  return out.data
}

/** 登记内部制度（差距分析的输入）。 */
export function importInternalPolicy(
  policyName: string, policyText: string, signal?: AbortSignal,
): Promise<{ policy_id: string; sections: string[] }> {
  return compliancePost<{ policy_id: string; sections: string[] }>(
    '/api/v1/compliance/policies', { policy_name: policyName, policy_text: policyText }, '登记制度', signal)
}

/** 差距分析（制度逐条对比法定义务，缺什么/补什么）。 */
export function runGapAnalysis(policyId: string, signal?: AbortSignal): Promise<KsGapResult> {
  return compliancePost<KsGapResult>('/api/v1/compliance/gap-analysis', { policy_id: policyId }, '差距分析', signal)
}

/* ============================================================================
   纠错修订（S2-c，2026-09-22）：条款补丁三口（Task 10.3 的真数据）。
     POST /api/v1/clauses/patches {clause_revision_id, field_name, patched_value, force?}
       → 200 落库；**466** = 防乱警告（前端二次确认后带 force=true 再交）；422 = 拒绝。
     GET /api/v1/clauses/patches?clause_revision_id=&limit= → {data: [patch…]}
     DELETE /api/v1/clauses/patches/{patch_id} = 回退（滚回不可变原始值；content_text
       会重算索引，秒级——引擎 §10.79 口径）。
   ============================================================================ */

export interface KsClausePatch {
  patch_id?: unknown
  clause_revision_id?: unknown
  field_name?: unknown
  patched_value?: unknown
  created_at?: unknown
  [k: string]: unknown
}

/** 列修订（不传 rev = 全部，最近在前）。 */
export async function listClausePatches(
  params: { clauseRevisionId?: string; limit?: number } = {},
  signal?: AbortSignal,
): Promise<KsClausePatch[]> {
  const { token, engine: { port } } = await fetchSession(signal)
  const qs = new URLSearchParams()
  if (params.clauseRevisionId !== undefined) qs.set('clause_revision_id', params.clauseRevisionId)
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  const suffix = qs.toString()
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/clauses/patches${suffix ? `?${suffix}` : ''}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw new Error(await engineErrorMessage(res, `列修订失败（HTTP ${res.status}）`))
  const out = (await res.json().catch(() => null)) as { code?: number; data?: unknown } | null
  if (!Array.isArray(out?.data)) throw new Error('列修订响应异常（期望 {code:200,data:[…]}）')
  return out.data as KsClausePatch[]
}

/**
 * 提交修订（防乱检测的 466 确认流是**引擎设计**：首交 466 带警告 ⇒ 人工确认后带 force 再交）。
 * 返回 `{warned}`（待确认）或 `{patch}`（已落库）——**不静默落库**。
 */
export async function createClausePatch(
  body: { clause_revision_id: string; field_name: string; patched_value: string; force?: boolean },
  signal?: AbortSignal,
): Promise<{ warned: string } | { patch: unknown }> {
  const { token, engine: { port } } = await fetchSession(signal)
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/clauses/patches`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  const out = (await res.json().catch(() => null)) as { code?: number; data?: unknown; error?: { message?: string } } | null
  if (res.status === 466 || out?.code === 466) {
    return { warned: out?.error?.message ?? '引擎提示这条修订可疑，请人工确认后再交（带确认重交）。' }
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `提交修订失败（HTTP ${res.status}）`))
  return { patch: out?.data ?? null }
}

/** 回退一条修订（删补丁 = 滚回原始值；引擎重算索引可能要几秒）。 */
export async function deleteClausePatch(patchId: string, signal?: AbortSignal): Promise<void> {
  const { token, engine: { port } } = await fetchSession(signal)
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/clauses/patches/${encodeURIComponent(patchId)}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (!res.ok) throw new Error(await engineErrorMessage(res, `回退修订失败（HTTP ${res.status}）`))
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
 * /ks/settings/api-config*（引擎写加密存储 DPAPI；host 与前端均不回显 Key）。
 * ------------------------------------------------------------------ */

export interface KsApiChannelStatus {
  configured: boolean
  base_url: string
  /** 仅 mineru_cloud：当前云解析模式（pipeline / vlm / MinerU-HTML）。 */
  model_version?: string
  /** 仅 mineru_cloud：可选模式清单（由引擎给，前端不硬编码）。 */
  model_versions?: string[]
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

/** PUT /ks/settings/api-config — 写入凭据（空字段跳过，留空即保持不变）。
 *  2026-09-15：mineru_cloud 增加 model_version（模式三选一，非密值）。 */
export async function saveApiConfig(
  payload: {
    mineru_cloud?: { api_key?: string; base_url?: string; model_version?: string }
    llm?: { api_key?: string; base_url?: string }
  },
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

/* ------------------------------------------------------------------ *
 * 材料平面（Phase B，2026-09-17）
 *
 * 走 host 的同源代理 `/ks/materials/*`（client 拿不到引擎 Bearer token）。
 * ⚠ **评审只走 `reviewMaterial`**，它的决定值只有 approved/rejected：
 * `pending` 是"还没评"，不是可以"评成"的状态（host 侧会 400 拒掉别的值）。
 * ------------------------------------------------------------------ */

export interface KsMaterialProject {
  project_id: string
  name: string
  note?: string | null
  authority_policy?: Record<string, unknown> | null
  created_at?: string | null
}

export interface KsMaterial {
  material_id: string
  title: string
  origin?: string | null
  kind?: string | null
  /** 轴 A：来源可信度 T0~T4。 */
  source_tier?: string | null
  /** 轴 A 的中文说明（由引擎给，前端不抄一份措辞）。 */
  tier_label?: string | null
  /** 层级的判据来源（'user' = 用户改的，用于留痕）。 */
  tier_source?: string | null
  /** 轴 B：任务内效力（'criterion' = 本任务准则）。 */
  task_role?: string | null
  review_status?: string | null
  chunk_count?: number | null
  url?: string | null
  domain?: string | null
  tier_reason?: string | null
  lifecycle?: string | null
  /** Track L 回指的法条文档 id（入库/回指成功后由引擎写入）。 */
  doc_id?: string | null
  /**
   * 批准时 Track L 的**结果**（引擎在 `data.track_l` 里报告"自动入库"的后果）。
   *
   * ⚠ 为什么界面必须显示它：批准一个采到的标准/法规会**自动写进法条库**——
   * 那是批准的**副作用**，静默通过等于用户不知道自己的法规库里多了东西（方案 §7）。
   * 拒绝时**没有**这个字段（"没决策"与"决策=skip"必须能区分）。
   */
  track_l?: {
    action?: string | null
    imported?: boolean
    linked?: boolean
    doc_id?: string | null
    standard_no?: string | null
    why?: string | null
  } | null
}

export interface KsMaterialChunk {
  chunk_id?: string
  text: string
  char_start: number
  char_end: number
  page?: number | null
}

export interface KsMaterialChunks {
  total: number
  offset: number
  chunks: KsMaterialChunk[]
}

export interface KsMaterialTierDef {
  tier: string
  label: string
}

/** 同源 `/ks/*` 响应信封的统一解包（`{ok:true,data}`，否则抛）。 */
async function ksJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: T } | null
  if (body === null || body.ok !== true || body.data === undefined) {
    throw new Error(`${what}响应异常`)
  }
  return body.data
}

/** GET /ks/materials/projects — 列项目。 */
export async function fetchMaterialProjects(signal?: AbortSignal): Promise<KsMaterialProject[]> {
  const res = await fetch('/ks/materials/projects', {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<KsMaterialProject[]>(res, '参考资料项目')
  return Array.isArray(data) ? data : []
}

/** POST /ks/materials/projects — 新建项目（authority_policy 可声明"本项目以谁为准"）。 */
export async function createMaterialProject(
  name: string,
  opts: { note?: string; authorityPolicy?: Record<string, unknown> | null } = {},
  signal?: AbortSignal,
): Promise<KsMaterialProject> {
  const res = await fetch('/ks/materials/projects', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      name,
      note: opts.note ?? null,
      authority_policy: opts.authorityPolicy ?? null,
    }),
    signal,
  })
  return ksJson<KsMaterialProject>(res, '新建项目')
}

/** GET /ks/materials/list?project_id= — 某项目的材料（**含未批准**：不列出来就没法批）。 */
export async function fetchMaterials(
  projectId: string,
  status?: 'pending' | 'approved' | 'rejected',
  signal?: AbortSignal,
): Promise<KsMaterial[]> {
  const q = new URLSearchParams({ project_id: projectId })
  if (status !== undefined) q.set('status', status)
  const res = await fetch(`/ks/materials/list?${q.toString()}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<KsMaterial[]>(res, '材料列表')
  return Array.isArray(data) ? data : []
}

/** GET /ks/materials/inbox?project_id= — 参考资料文件夹里**尚未登记**的文件。 */
export async function fetchMaterialInbox(
  projectId: string,
  signal?: AbortSignal,
): Promise<{ dir: string; files: { path: string; file_name: string; size: number }[] }> {
  const q = new URLSearchParams({ project_id: projectId })
  const res = await fetch(`/ks/materials/inbox?${q.toString()}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<{ dir?: string; files?: { path: string; file_name: string; size: number }[] }>(
    res, '收件箱')
  return { dir: typeof data.dir === 'string' ? data.dir : '', files: data.files ?? [] }
}

/** POST /ks/materials/scan?project_id= — 扫描收件（登记为**待评审**，不会自动批准）。 */
export async function scanMaterialProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<{ scanned: number; registered: number }> {
  const q = new URLSearchParams({ project_id: projectId })
  const res = await fetch(`/ks/materials/scan?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ origin: 'user' }),
    signal,
  })
  const data = await ksJson<{ scanned?: number; registered?: number }>(res, '扫描收件')
  return { scanned: data.scanned ?? 0, registered: data.registered ?? 0 }
}

/**
 * 自采一次的结果（Phase C-5/D-3 的界面接线）。
 *
 * ⚠ **"抓取失败"不是异常**：引擎刻意用 `HTTP 200 + collected:false + reason` 表达它
 * （原因要**显示给人看**）。所以本类型把 `reason` 放在**正常返回**上，
 * 而不是让 `ksJson` 抛错——抛错会把"没采到"和"引擎挂了"混成同一种红字。
 */
export interface KsCollectOutcome {
  collected: boolean
  /** 抓取时的 HTTP 状态（`collected:false` 时也常有，用来区分 404/403/超时）。 */
  status?: number
  /** **未采到时**的原因（SSRF 拒绝 / HTTP 4xx / 不是文本 / 正文空…）。 */
  reason?: string
  /** 正文是否被截断到上限（真了要说，否则用户以为拿到全文）。 */
  truncated?: boolean
  /** 同内容已在项目里（引擎按内容判重）——**没有**重复登记。 */
  duplicate?: boolean
  material?: {
    material_id?: string
    title?: string
    review_status?: string | null
    source_tier?: string | null
    chunk_count?: number
  } | null
}

/**
 * POST /ks/materials/collect?project_id= — 按 URL **自采一份**材料（登记为**待评审**）。
 *
 * ## 三条与主机/引擎同源的纪律（**不要在界面层另起一套**）
 * 1. **不发 `source_tier`**（连试都不试）：采集者不得自 claim 可信度。轴 A 由系统判据起
 *    （采集默认 T3=仅线索），要改只能由**用户**在界面上改（走 `setMaterialTier`）。
 *    主机侧对 `source_tier` 与任何未知字段**响亮拒绝**（400），静默忽略会让调用方
 *    以为自己设上了。
 * 2. **只收四个键**（`url`/`title`/`note`/`published_at`）——与主机白名单逐字一致；
 *    多传一个键就是 400，不是"被忽略"。本函数因此**只构造这四个**。
 * 3. **一次只采一条**：方案 §11.4 的采集预算未定，**没有**批量入口（不提供 urls 数组）。
 */
export async function collectMaterialUrl(
  projectId: string,
  input: { url: string; title?: string; note?: string },
  signal?: AbortSignal,
): Promise<KsCollectOutcome> {
  const q = new URLSearchParams({ project_id: projectId })
  const body: Record<string, string> = { url: input.url }
  if (input.title !== undefined && input.title !== '') body.title = input.title
  if (input.note !== undefined && input.note !== '') body.note = input.note
  const res = await fetch(`/ks/materials/collect?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  const data = await ksJson<KsCollectOutcome>(res, '自采')
  if (typeof data?.collected !== 'boolean') {
    // 形状不认识 ⇒ **抛**（别把"信封坏了"渲染成"没采到"——那会让人以为换个网址就行）
    throw new Error('自采响应异常：缺少 collected 字段（不要把这次结果当成"已经采到了"）')
  }
  return data
}

/**
 * POST /ks/materials/review?material_id= — **用户的评审决定**（本面板的核心动作）。
 *
 * 只允许 `approved` / `rejected`：`pending` 是"还没评"，不是可以"评成"的状态；
 * host 侧对其它值一律 400（所以这里把类型也收紧成两个字面量，写错编译期就红）。
 */
export async function reviewMaterial(
  materialId: string,
  decision: 'approved' | 'rejected',
  note?: string,
  signal?: AbortSignal,
): Promise<KsMaterial> {
  const q = new URLSearchParams({ material_id: materialId })
  const res = await fetch(`/ks/materials/review?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ decision, note: note ?? null }),
    signal,
  })
  return ksJson<KsMaterial>(res, '评审')
}

/**
 * POST /ks/materials/tier?material_id= — 改**来源可信度**（轴 A，用户可改并留痕）。
 *
 * ⚠ `reason` **要传**：引擎把 `tier_reason` **写成**它，不传就把原判据擦成空
 * （独立复核 2026-09-17 实测的数据丢失）。界面应带"从哪改到哪"。
 */
export async function setMaterialTier(
  materialId: string,
  tier: string,
  reason?: string,
  signal?: AbortSignal,
): Promise<KsMaterial> {
  const q = new URLSearchParams({ material_id: materialId })
  const res = await fetch(`/ks/materials/tier?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ tier, source: 'user', reason: reason ?? null }),
    signal,
  })
  return ksJson<KsMaterial>(res, '设置来源层级')
}

/**
 * POST /ks/materials/role?material_id= — 声明**任务内效力**（轴 B，与轴 A 正交）。
 *
 * `role: null` **是合法的**（撤销声明）——主机路由与引擎都明确支持，不是"没填"。
 */
export async function setMaterialRole(
  materialId: string,
  role: 'criterion' | 'reference' | null,
  signal?: AbortSignal,
): Promise<KsMaterial> {
  const q = new URLSearchParams({ material_id: materialId })
  const res = await fetch(`/ks/materials/role?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ role }),
    signal,
  })
  return ksJson<KsMaterial>(res, '设置任务内效力')
}

/** GET /ks/materials/chunks?material_id= — 切片分页（**评审前必须能读到正文**）。 */
export async function fetchMaterialChunks(
  materialId: string,
  offset = 0,
  limit = 20,
  signal?: AbortSignal,
): Promise<KsMaterialChunks> {
  const q = new URLSearchParams({
    material_id: materialId, offset: String(offset), limit: String(limit),
  })
  const res = await fetch(`/ks/materials/chunks?${q.toString()}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<KsMaterialChunks>(res, '材料切片')
  return { total: data.total ?? 0, offset: data.offset ?? 0, chunks: data.chunks ?? [] }
}

/** GET /ks/materials/tiers — 轴 A 的层定义（**从引擎取**，前端不抄一份措辞）。 */
export async function fetchMaterialTiers(signal?: AbortSignal): Promise<KsMaterialTierDef[]> {
  const res = await fetch('/ks/materials/tiers', {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<KsMaterialTierDef[]>(res, '层定义')
  return Array.isArray(data) ? data : []
}

/* ------------------------------------------------------------------ 引用锚点稳定性
 * （方案 §12 未决第 5 条 = Phase B 必解，§10.48/§10.49）
 *
 * ⚠ 界面这一层**不许**自己解释 status：`ok` 的语义是"**未发现变化**"（不是"保证一致"），
 * `stale` 是"**需要复算**"（不是"已经坏了"），`unknown` 是"**验证不了**"
 * （老材料没记指纹 / PDF 的便宜判据下不了结论）。措辞的唯一所有者在
 * `src/core/materials/locator.py`。
 */

/** 锚点健康度（便宜判据：比指纹 + 比源文件字节，不重解析）。 */
export interface KsLocatorHealth {
  material_id: string
  /**
   * ⚠ `health_error` **不是**健康状态，是"**后端判据跑挂了**"（复核 b9 的 INFO-3 同族）：
   * `locator_health` 永远不会返回它，只有**总览**在单份材料算不出来时才会给（并附 `why`）。
   * 不把它列进来，界面就**必须**在类型上忽略这种情况——而忽略它就等于把"结论没拿到"
   * 渲染成"没有标记"，看起来像全都健康。
   */
  status: 'ok' | 'stale' | 'unknown' | 'no_locators' | 'health_error'
  fingerprint_recorded?: string | null
  fingerprint_current?: string | null
  derived_text_hash_recorded?: string | null
  why: string
}

/** 项目级总览。 */
export interface KsLocatorSummary {
  project_id: string
  counts: Partial<Record<KsLocatorHealth['status'], number>>
  /** 每份材料的状态（一次给全：界面每行都要画标记，逐行发请求会变请求风暴）。 */
  statuses: Record<string, KsLocatorHealth['status']>
  attention: { material_id: string; title?: string; status: string; why: string }[]
  note: string
}

/** **重解析比对**的结果（贵、显式动作）。`mismatch` = 已存区间不再可信。 */
export interface KsReverifyResult {
  material_id: string
  status: 'match' | 'mismatch' | 'unavailable'
  recorded?: string | null
  recomputed?: string | null
  why: string
}

/** GET /ks/materials/locators?material_id= — 单份材料的锚点健康度（便宜）。 */
export async function fetchMaterialLocators(
  materialId: string, signal?: AbortSignal,
): Promise<KsLocatorHealth> {
  const q = new URLSearchParams({ material_id: materialId })
  const res = await fetch(`/ks/materials/locators?${q.toString()}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  return ksJson<KsLocatorHealth>(res, '锚点健康度')
}

/** GET /ks/materials/locators?project_id= — 项目级总览（便宜）。 */
export async function fetchProjectLocators(
  projectId: string, signal?: AbortSignal,
): Promise<KsLocatorSummary> {
  const q = new URLSearchParams({ project_id: projectId })
  const res = await fetch(`/ks/materials/locators?${q.toString()}`, {
    method: 'GET', headers: { accept: 'application/json' }, signal,
  })
  const data = await ksJson<KsLocatorSummary>(res, '锚点总览')
  return { project_id: data.project_id ?? projectId, counts: data.counts ?? {},
           statuses: data.statuses ?? {}, attention: data.attention ?? [],
           note: data.note ?? '' }
}

/**
 * POST /ks/materials/reverify?material_id= — **重解析比对**（会真的重新解析源文件）。
 * ⚠ 用户点了才发（PDF 秒级到分钟级），**不许**挂在加载路径上。
 */
export async function reverifyMaterialLocators(
  materialId: string, signal?: AbortSignal,
): Promise<KsReverifyResult> {
  const q = new URLSearchParams({ material_id: materialId })
  const res = await fetch(`/ks/materials/reverify?${q.toString()}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({}),
    signal,
  })
  return ksJson<KsReverifyResult>(res, '重解析比对')
}

/* ------------------------------------------------------------------ 产出（Phase D-3b）
 *
 * ⚠ 与 `/ks/materials/*` 的**参数位置不同**：产出路由把 `project_id` 放在 **body** 里
 * （材料路由放 query）。这不是笔误——两条路由是不同时间写的，各自的白名单也各自持有
 * （`plugin/src/materials_routes.js` 用 `pickQuery`，`plugin/src/report.js` 从 body 取）。
 * 客户端这一层必须**逐条跟随**，冒烟把位置钉死（`smoke-report-ui`）。
 */

/** 产出物里对"这一轮用了什么"的计数（**界面要如实显示**，尤其 pending）。 */
export interface KsReportCounts {
  approved?: number
  pending?: number
  rejected?: number
}

/** 一份研究报告的组装/落盘结果（`write_` 比 `build_` 多 `files`/`names`）。 */
export interface KsResearchReport {
  title?: string
  query?: string | null
  /** 引用逐条校验的结论（不存在 / 指向仅线索或不可用 ⇒ 进 warnings）。 */
  citations?: {
    checked_material_refs?: number
    bad_material_refs?: number
    unchecked_law_refs?: number
    unknown?: number
  }
  /** ⚠ **必须显示给用户**：引用对不上、或无法核验的法规引用都在这儿。 */
  warnings?: string[]
  counts?: KsReportCounts
  markdown?: string
  html?: string
  /** 落盘的绝对路径（`dry_run` 时没有）。落盘是**两个**：`.md` / `.html`。 */
  files?: string[]
  names?: string[]
}

/**
 * **结论草稿**的返回（Phase D-5a，§10.96）。
 *
 * ⚠ 字段名与引擎**逐字一致**（snake_case）——`ksJson` 只透传、不做命名转换
 * （同 `KsResearchDraft.llm_called` 的先例）。
 * ⚠ `status` 恒为 `unapproved_draft` —— 那是**契约的一部分**，界面必须显示；
 * 草稿**不落盘**（所以这里没有 `files`），是否采用由用户**逐次显式**决定。
 */
export interface KsResearchDraft {
  status?: string
  disclaimer?: string
  /** 草稿正文（Markdown，含 `[[m:i]]`）——**未经批准**，界面要显眼标明。 */
  draft_md?: string
  /** 模型的推导段（草稿为空时看它，判断模型到底说了什么）。 */
  derivation_md?: string
  citations?: {
    material_refs?: number[]
    unknown?: number[]
    not_load_bearing?: Array<{ index: number; group: string }>
    unchecked_law_refs?: number[]
  }
  warnings?: string[]
  counts?: KsReportCounts
  notes?: string[]
  /** 可承重的材料编号（产出物按它拼引用）。 */
  usable_indices?: number[]
  /** false = **一次模型都没调**（没有可承重材料）；界面要如实说，不能显示成"生成失败"。 */
  llm_called?: boolean
}

/** 两个产出端点共用的入参（`limit` 是"按 research 问题检索几条材料"，不是页数）。 */
interface KsReportInput {
  title?: string
  query?: string
  conclusionMd?: string
  limit?: number
  /** true = 只组装不落盘（预览用；返回的 `markdown`/`html` 照样有）。 */
  dryRun?: boolean
}

/** 把界面入参翻成**主机白名单认识**的那几个键（不认识的键一个都不发）。 */
function reportBody(projectId: string, input: KsReportInput): Record<string, unknown> {
  const body: Record<string, unknown> = { project_id: projectId }
  if (input.title !== undefined && input.title !== '') body.title = input.title
  if (input.query !== undefined && input.query !== '') body.query = input.query
  if (input.conclusionMd !== undefined && input.conclusionMd !== '')
    body.conclusion_md = input.conclusionMd
  if (input.limit !== undefined) body.limit = input.limit
  if (input.dryRun !== undefined) body.dry_run = input.dryRun
  return body
}

async function postReport<T>(path: string, projectId: string, input: KsReportInput,
                             what: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(reportBody(projectId, input)),
    signal,
  })
  return ksJson<T>(res, what)
}

/**
 * POST /ks/report/research — **生成研究报告**（Markdown + HTML，本机落盘）。
 *
 * 内容只吃**已批准**的材料（硬门在引擎侧的检索里）；未批准的自会出现在
 * "尚未批准的材料（不会进入任何结论）"一节。`conclusion_md` 里的 `[[m:i]]` 会被
 * 引擎逐条校验，对不上的进 `warnings`——**界面必须显示**，否则用户会以为引用都成立。
 * `files`/`names` 是**两个**（`.md` / `.html`，顺序固定）。
 *
 * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原 `.docx` 落盘与 PPT
 * （`exportResearchSlides`，走 `/ks/report/research/slides`）已拆除
 * ——业主否决 Word/PPT 交付物（`docs/NOT-DOING.md` 第 1 条）。
 */
export async function exportResearchReport(
  projectId: string, input: KsReportInput = {}, signal?: AbortSignal,
): Promise<KsResearchReport> {
  return postReport<KsResearchReport>('/ks/report/research', projectId, input,
    '研究报告', signal)
}

/**
 * POST /ks/report/research/draft — **起草一段结论（草稿）**（Phase D-5a，§10.96）。
 *
 * 系统基于**已批准材料**起一稿；`query` **必填**（起草必须先知道要回答什么）。
 * 返回里的 `status` 恒为 `unapproved_draft`、`draft_md` 是**未经批准**的草稿
 * —— 界面必须显眼标明，且**不得**自动写进结论框（要用户点一下）。
 * `llm_called === false` 表示"没有可承重材料，一次模型都没调"，**不是**失败。
 */
export async function exportResearchDraft(
  projectId: string, input: { query: string; limit?: number }, signal?: AbortSignal,
): Promise<KsResearchDraft> {
  return postReport<KsResearchDraft>('/ks/report/research/draft', projectId, input,
    '结论草稿', signal)
}

/* ------------------------------------------------------------------ *
 * 知识库多级目录（KB-FOLDER-PLAN 第 2 步的接口 → 第 3 步接界面）
 *
 * 接口真源：`src/core/api/routes_kb_folders.py`（**本文件只做 HTTP 外形**，
 * 形状逐字照那里的 docstring + 代码）；返回包装是 `{code,status,data}` ⇒
 * 一律读 `body.data`（与 `batchDeleteDocs` 同一口径）。
 *
 * ⚠ 三条形状上的事实（照源码，不照印象）：
 *   · `GET /kb/folders` **省略 `parent_id` = 顶层**；顶层 `data.folder` 是 `null`，
 *     `data.breadcrumb` 是 `[]`（空数组，不是 null）。
 *   · `GET /kb/folders/{id}/items` 顶层要传 **`folder_id='root'`**（源码里
 *     `root`/`null` 都当顶层）；空目录是 `items: []` 而**不是 404**。
 *   · `POST /kb/members` 的 `folder_id` 必须是一个**真目录 id**（`folder_store._folder_row`
 *     查不到就 404）⇒ **顶层**（`root`）挂不了成员；顶层文件本来就是"还没进任何目录"的那些。
 * ------------------------------------------------------------------ */

/** 一个知识库目录（`folder_store.list_folder` 的子目录条目）。 */
export interface KsKbFolder {
  folder_id: string
  parent_id: string | null
  name: string
  sort: number
  created_at: string | null
  /** 这一级**直接**放的篇数（不含下级）。 */
  file_count_direct: number
  /** 这一棵子树里的篇数（去重：同一篇挂多处只算一次）。 */
  file_count_deep: number
  /** 这一棵子树里的目录数（不含自己）。 */
  folder_count_deep: number
  /** 这一棵子树里文件的**效力四色**总览（green=现行 / red=在用废止·被代 / yellow=即将实施 /
   *  gray=未知；口径 = 引擎 effect_report.STATUS_COLOR）。文件夹行的红绿灯用它（批D2）。 */
  effect_deep: { green: number; red: number; yellow: number; gray: number }
}

/**
 * 这一级**直接**放的一篇文件（`doc_meta` 行 + `doc_filing_state` 的处理状态）。
 *
 * ⚠ 处理状态三个字段是后端 `list_folder` 里 `COALESCE(s.stage,'queued')` 那一组：
 *   `stage` ∈ queued/recognizing/confirming/filed/failed（中文标签的所有者是
 *   `folder_store.STAGE_LABELS`，接口**没有**下发标签 ⇒ 客户端那份镜像在页面里）。
 *   **没有状态行 = 从未处理**，后端按 `queued` 报（不是 null）。
 */
export interface KsKbFile {
  doc_id: string
  standard_no: string | null
  standard_name: string | null
  legal_status: string | null
  legal_hierarchy: string | null
  doc_type: string | null
  ccs_code: string | null
  ccs_name: string | null
  published_at: string | null
  effective_from: string | null
  withdrawn_date: string | null
  superseded_by: string | null
  stage: string | null
  confidence: number | null
  failure_kind: string | null
  suggested_folder_id: string | null
}

/** 分页信封（目录列表与文件列表共用这五个字段，口径见路由模块头）。 */
export interface KsKbPageInfo {
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface KsKbLevel extends KsKbPageInfo {
  /** 本级目录；**顶层是 `null`**（顶层不是一行目录记录）。 */
  folder: KsKbFolder | null
  /** 从顶层到本级的目录链；顶层是 `[]`。 */
  breadcrumb: KsKbFolder[]
  subfolders: KsKbFolder[]
}

export interface KsKbLevelFiles extends KsKbPageInfo {
  folder: KsKbFolder | null
  breadcrumb: KsKbFolder[]
  items: KsKbFile[]
}

function objOf(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null
}

/** `{code,status,data}` 外壳里的 `data`（缺了就当空对象 —— 调用方按字段判）。 */
function dataOf(body: unknown): Record<string, unknown> {
  const wrapped = objOf(body)
  return objOf(wrapped?.data) ?? wrapped ?? {}
}

function intOf(value: unknown, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function normalizeKbFolder(value: unknown): KsKbFolder | null {
  const o = objOf(value)
  const id = str(o?.folder_id)
  if (o === null || id === null) return null
  return {
    folder_id: id,
    parent_id: str(o.parent_id),
    name: str(o.name) ?? id,
    sort: intOf(o.sort, 0),
    created_at: str(o.created_at),
    file_count_direct: intOf(o.file_count_direct, 0),
    file_count_deep: intOf(o.file_count_deep, 0),
    folder_count_deep: intOf(o.folder_count_deep, 0),
    effect_deep: (() => {
      const ef = (o.effect_deep ?? {}) as Record<string, unknown>
      return {
        green: intOf(ef.green, 0), red: intOf(ef.red, 0),
        yellow: intOf(ef.yellow, 0), gray: intOf(ef.gray, 0),
      }
    })(),
  }
}

function normalizeKbFile(value: unknown): KsKbFile | null {
  const o = objOf(value)
  const id = str(o?.doc_id)
  if (o === null || id === null) return null
  return {
    doc_id: id,
    standard_no: str(o.standard_no),
    standard_name: str(o.standard_name),
    legal_status: str(o.legal_status),
    legal_hierarchy: str(o.legal_hierarchy),
    doc_type: str(o.doc_type),
    ccs_code: str(o.ccs_code),
    ccs_name: str(o.ccs_name),
    published_at: str(o.published_at),
    effective_from: str(o.effective_from),
    withdrawn_date: str(o.withdrawn_date),
    superseded_by: str(o.superseded_by),
    stage: str(o.stage),
    confidence: num(o.confidence),
    failure_kind: str(o.failure_kind),
    suggested_folder_id: str(o.suggested_folder_id),
  }
}

/** 引擎错误体 `{error:{code,message}}` 的 message（透传业务失败，见 `batchDeleteDocs`）。 */
async function engineErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const b = await res.json()
    const e = objOf(objOf(b)?.error)
    const m = e?.message
    if (typeof m === 'string' && m !== '') return m
  } catch { /* 保持兜底文案 */ }
  return fallback
}

/**
 * 列**某一级**的下级目录（懒展开用）。
 *
 * @param parentId - 上级目录 id；`null`/省略 = 库的**顶层**（源码里省略 parent_id 就是这个意思）。
 */
export async function fetchKbFolders(
  port: number,
  token: string,
  parentId: string | null,
  opts: { limit?: number; offset?: number; signal?: AbortSignal } = {},
): Promise<KsKbLevel> {
  const qs = new URLSearchParams()
  if (parentId !== null) qs.set('parent_id', parentId)
  if (opts.limit !== undefined) qs.set('limit', String(opts.limit))
  if (opts.offset !== undefined) qs.set('offset', String(opts.offset))
  const suffix = qs.toString() === '' ? '' : `?${qs.toString()}`
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/folders${suffix}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const subs = Array.isArray(data.subfolders) ? data.subfolders : []
  const crumb = Array.isArray(data.breadcrumb) ? data.breadcrumb : []
  return {
    folder: normalizeKbFolder(data.folder),
    breadcrumb: crumb.map(normalizeKbFolder).filter((f): f is KsKbFolder => f !== null),
    subfolders: subs.map(normalizeKbFolder).filter((f): f is KsKbFolder => f !== null),
    total: intOf(data.total, subs.length),
    offset: intOf(data.offset, opts.offset ?? 0),
    limit: intOf(data.limit, opts.limit ?? 200),
    has_more: data.has_more === true,
  }
}

/**
 * 列**某一级直接放**的文件（**不含**下级目录里的），按 `limit/offset` 分页。
 *
 * @param folderId - 目录 id；**顶层传 `'root'`**（源码里 `root`/`null` 都当顶层）。
 */
export async function fetchKbFolderItems(
  port: number,
  token: string,
  folderId: string,
  opts: { limit?: number; offset?: number; signal?: AbortSignal } = {},
): Promise<KsKbLevelFiles> {
  const qs = new URLSearchParams()
  qs.set('limit', String(opts.limit ?? 50))
  qs.set('offset', String(opts.offset ?? 0))
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/kb/folders/${encodeURIComponent(folderId)}/items?${qs.toString()}`,
    {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
      signal: opts.signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const rows = Array.isArray(data.items) ? data.items : []
  const crumb = Array.isArray(data.breadcrumb) ? data.breadcrumb : []
  return {
    folder: normalizeKbFolder(data.folder),
    breadcrumb: crumb.map(normalizeKbFolder).filter((f): f is KsKbFolder => f !== null),
    items: rows.map(normalizeKbFile).filter((f): f is KsKbFile => f !== null),
    total: intOf(data.total, rows.length),
    offset: intOf(data.offset, opts.offset ?? 0),
    limit: intOf(data.limit, opts.limit ?? 50),
    has_more: data.has_more === true,
  }
}

/** `POST /kb/members` 的出参（批量加成员；已在那处的**幂等跳过**）。 */
export interface KsKbAddMembersResult {
  folder_id: string
  added: number
  skipped: number
  total: number
}

/**
 * 把**已存在**的条目加进某目录（上传/挪入的落位接口）。
 *
 * ⚠⚠ **顶层（`root`）挂不了**：`folder_store._add_member_in_tx` 先 `_folder_row(conn, folder_id)`
 *   查这条目录记录，查不到就 404 `folder_not_found`；而"顶层"在库里**不是一行记录**
 *   （`folder.parent_id IS NULL` 的那些才是顶层目录）⇒ 调用方必须自己判"当前在最外层"。
 */
export async function addKbMembers(
  port: number,
  token: string,
  folderId: string,
  items: ReadonlyArray<{ kind: 'file' | 'folder'; id: string }>,
  signal?: AbortSignal,
): Promise<KsKbAddMembersResult> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/members`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ folder_id: folderId, items: items.map((it) => ({ kind: it.kind, id: it.id })) }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  return {
    folder_id: str(data.folder_id) ?? folderId,
    added: intOf(data.added, 0),
    skipped: intOf(data.skipped, 0),
    total: intOf(data.total, items.length),
  }
}

/*
 * ── 目录/文件的「建 / 改名 / 挪 / 复制 / 删」（KB-FOLDER-PLAN 第 5 步）──────────
 *
 * ⚠ 形状全部照 `src/core/api/routes_kb_folders.py` 的代码读出来（**不是**印象）：
 *   · `POST /kb/folders` 的 `parent_id` 省略/`null`/`'root'` **都当顶层**；同名同层 ⇒ 409，
 *     空名/超长 ⇒ 422，上级不存在 ⇒ 404。
 *   · `PUT /kb/folders/{id}` **只改库里的名字**（绝不动磁盘文件，方案 §二第 1 条）。
 *   · `POST /kb/folders/{id}/move` 的 `from_parent_id` 省略 = 取当前主位置（"把这个目录挪走"）；
 *     `to_parent_id: null` = **真的挪到顶层**（改 `parent_id`）。挪进自己/自己的下级 ⇒ 409/422 报错。
 *   · `POST /kb/folders/{id}/copy` **共享成员**（同一批 item_id），**不拷文件、不拷下级目录副本**；
 *     `name` 省略时后端自动取"原名 (副本)"；`to_parent_id: null` = 复制到顶层。
 *   · `GET /kb/folders/{id}/delete-preview` 是**只读**的"先问一句"数字；
 *     `reparent_available=false` ⇔ 一级目录（没有上一层 ⇒ 只给 purge 与取消）。
 *   · `DELETE /kb/folders/{id}?mode=reparent|purge`：空目录**直接删**（返回 `mode='empty'`）；
 *     非空不给 `mode` ⇒ 409 `folder_delete_mode_required`（后端**不替调用方选**）；
 *     一级目录 + `reparent` ⇒ 409 `folder_top_level_no_parent`（不静默降级）；
 *     `purge` 只真删"在所有目录里都不再出现"的文件，还挂在别处的**只丢归属**。
 *   · `POST /kb/members/{remove,move,copy}` 的文件操作：**只动归属行，不删文件**
 *     （`remove` 只从这一处拿掉；`move` 需要 `from_folder_id` + `to_folder_id`；
 *     `copy` 只是"多一处位置"，不需要来源）。
 */

/** `POST /kb/folders` 的出参（建目录）。 */
export interface KsKbCreatedFolder {
  folder_id: string
  name: string
  parent_id: string | null
}

/** `PUT /kb/folders/{id}` 的出参（改名）。 */
export interface KsKbRenamedFolder {
  folder_id: string
  name: string
  parent_id: string | null
}

/** `POST /kb/folders/{id}/move` 的出参。 */
export interface KsKbMovedFolder {
  folder_id: string
  name: string
  parent_id: string | null
  from_parent_id: string | null
  to_parent_id: string | null
  /** `parent_id`（主位置）这次有没有真的变 —— 后端如实报，不是"挪了就一定变"。 */
  updated_main_position: boolean
  moved: boolean
  reason?: string
}

/** 复制目录的出参（= 新目录那一行 + `copied_members`）。 */
export interface KsKbCopiedFolder extends KsKbCreatedFolder {
  sort: number
  copied_members: number
  copied_from: string
}

/** `GET /kb/folders/{id}/delete-preview` —— 删目录**前**要的数字（只读）。 */
export interface KsKbDeletePreview {
  folder: KsKbFolder | null
  is_empty: boolean
  direct_subfolder_count: number
  direct_file_count: number
  subtree_folder_count: number
  subtree_file_count: number
  /** `false` ⇔ 一级目录（没有上一层 ⇒ 只给"连里面的文件一起删"与取消）。 */
  reparent_available: boolean
  /** purge 之后**只丢归属**的篇数（它们还挂在别的目录里）。 */
  files_kept_elsewhere: number
  /** purge 之后**真的会被删掉**的篇数。 */
  files_would_be_deleted: number
}

/** `DELETE /kb/folders/{id}` 的出参（`mode='empty'` = 空目录直接删）。 */
export interface KsKbFolderDeleteResult {
  folder_id: string
  mode: 'empty' | 'reparent' | 'purge'
  removed: boolean
  new_parent_id?: string | null
  reparented_subfolders: number
  reparented_files: number
  purged_folders: number
  unfiled_docs: number
  deleted_docs?: number
}

/** `POST /kb/members/remove|move|copy` 的出参（只动归属行）。 */
export interface KsKbMemberResult {
  folder_id: string
  to_folder_id: string
  from_folder_id: string
  added: number
  skipped: number
  removed: number
  moved: number
  total: number
}

/** 成员操作的条目（`{kind, id}` —— 与 `POST /kb/members` 同一形状）。 */
export interface KsKbMemberItem {
  kind: 'file' | 'folder'
  id: string
}

/** 所有 KB 写操作的公共外形（401 自愈口径与其余 KB 函数逐字一致）。 */
async function kbWrite(
  url: string, method: string, token: string, body: unknown, signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  const res = await fetch(`http://127.0.0.1:${url}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
      accept: 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let parsed: unknown = null
  try { parsed = await res.json() } catch { /* non-JSON body */ }
  return dataOf(parsed)
}

/** 建目录（`parentId: null` = 顶层；建完**当前这一级刷新**就能看见它）。 */
export async function createKbFolder(
  port: number, token: string, parentId: string | null, name: string,
  signal?: AbortSignal,
): Promise<KsKbCreatedFolder> {
  const d = await kbWrite(`${String(port)}/api/v1/kb/folders`, 'POST', token,
    { parent_id: parentId, name }, signal)
  return {
    folder_id: str(d.folder_id) ?? '',
    name: str(d.name) ?? name,
    parent_id: str(d.parent_id),
  }
}

/** 目录改名（**只改库里的名字**，不动磁盘上的文件）。 */
export async function renameKbFolder(
  port: number, token: string, folderId: string, name: string, signal?: AbortSignal,
): Promise<KsKbRenamedFolder> {
  const d = await kbWrite(
    `${String(port)}/api/v1/kb/folders/${encodeURIComponent(folderId)}`, 'PUT', token,
    { name }, signal)
  return {
    folder_id: str(d.folder_id) ?? folderId,
    name: str(d.name) ?? name,
    parent_id: str(d.parent_id),
  }
}

/** 挪目录（`toParentId: null` = 挪到**顶层**；`fromParentId` 省略 = 取当前主位置）。 */
export async function moveKbFolder(
  port: number, token: string, folderId: string, toParentId: string | null,
  opts: { fromParentId?: string | null; signal?: AbortSignal } = {},
): Promise<KsKbMovedFolder> {
  const d = await kbWrite(
    `${String(port)}/api/v1/kb/folders/${encodeURIComponent(folderId)}/move`, 'POST', token,
    { from_parent_id: opts.fromParentId ?? null, to_parent_id: toParentId }, opts.signal)
  return {
    folder_id: str(d.folder_id) ?? folderId,
    name: str(d.name) ?? '',
    parent_id: str(d.parent_id),
    from_parent_id: str(d.from_parent_id),
    to_parent_id: str(d.to_parent_id),
    updated_main_position: d.updated_main_position === true,
    moved: d.moved === true,
    reason: str(d.reason) ?? undefined,
  }
}

/** 复制目录到某处（**共享成员**：不拷文件、不拷下级目录的副本）。 */
export async function copyKbFolder(
  port: number, token: string, folderId: string, toParentId: string | null,
  opts: { name?: string; signal?: AbortSignal } = {},
): Promise<KsKbCopiedFolder> {
  const d = await kbWrite(
    `${String(port)}/api/v1/kb/folders/${encodeURIComponent(folderId)}/copy`, 'POST', token,
    { to_parent_id: toParentId, name: opts.name ?? null }, opts.signal)
  return {
    folder_id: str(d.folder_id) ?? '',
    name: str(d.name) ?? '',
    parent_id: str(d.parent_id),
    sort: intOf(d.sort, 0),
    copied_members: intOf(d.copied_members, 0),
    copied_from: str(d.copied_from) ?? folderId,
  }
}

/** 删目录**前**的影响数字（只读；界面照这些数字问业主，**不许自己猜**）。 */
export async function fetchKbFolderDeletePreview(
  port: number, token: string, folderId: string, signal?: AbortSignal,
): Promise<KsKbDeletePreview> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/kb/folders/${encodeURIComponent(folderId)}/delete-preview`,
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
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const d = dataOf(body)
  return {
    folder: normalizeKbFolder(d.folder),
    is_empty: d.is_empty === true,
    direct_subfolder_count: intOf(d.direct_subfolder_count, 0),
    direct_file_count: intOf(d.direct_file_count, 0),
    subtree_folder_count: intOf(d.subtree_folder_count, 0),
    subtree_file_count: intOf(d.subtree_file_count, 0),
    reparent_available: d.reparent_available === true,
    files_kept_elsewhere: intOf(d.files_kept_elsewhere, 0),
    files_would_be_deleted: intOf(d.files_would_be_deleted, 0),
  }
}

/**
 * 删目录。`mode`：
 *   `null` = 空目录直接删（非空会被后端拒成 409）；`'reparent'` = 只删这个目录、
 *   里面的东西移到**上一层**；`'purge'` = 连里面的目录/文件一起删。
 * ⚠ 一级目录 + `'reparent'` 后端**明确报错**（不静默降级）⇒ 界面必须先看 `reparent_available`。
 */
export async function deleteKbFolder(
  port: number, token: string, folderId: string,
  mode: 'reparent' | 'purge' | null, signal?: AbortSignal,
): Promise<KsKbFolderDeleteResult> {
  const qs = mode === null ? '' : `?mode=${mode}`
  const d = await kbWrite(
    `${String(port)}/api/v1/kb/folders/${encodeURIComponent(folderId)}${qs}`, 'DELETE',
    token, undefined, signal)
  return {
    folder_id: str(d.folder_id) ?? folderId,
    mode: (str(d.mode) ?? 'empty') as KsKbFolderDeleteResult['mode'],
    removed: d.removed === true,
    new_parent_id: str(d.new_parent_id),
    reparented_subfolders: intOf(d.reparented_subfolders, 0),
    reparented_files: intOf(d.reparented_files, 0),
    purged_folders: intOf(d.purged_folders, 0),
    unfiled_docs: intOf(d.unfiled_docs, 0),
    deleted_docs: intOf(d.deleted_docs, 0),
  }
}

/** 批量成员操作的三条出口（`remove` / `move` / `copy`）—— 只动归属行，**不删文件**。 */
export async function removeKbMembers(
  port: number, token: string, folderId: string,
  items: readonly KsKbMemberItem[], signal?: AbortSignal,
): Promise<KsKbMemberResult> {
  const d = await kbWrite(`${String(port)}/api/v1/kb/members/remove`, 'POST', token,
    { folder_id: folderId, items: items.map((it) => ({ kind: it.kind, id: it.id })) }, signal)
  return memberResult(d, folderId, '', '')
}

export async function moveKbMembers(
  port: number, token: string, items: readonly KsKbMemberItem[],
  fromFolderId: string, toFolderId: string, signal?: AbortSignal,
): Promise<KsKbMemberResult> {
  const d = await kbWrite(`${String(port)}/api/v1/kb/members/move`, 'POST', token,
    {
      from_folder_id: fromFolderId, to_folder_id: toFolderId,
      items: items.map((it) => ({ kind: it.kind, id: it.id })),
    }, signal)
  return memberResult(d, fromFolderId, toFolderId, fromFolderId)
}

export async function copyKbMembers(
  port: number, token: string, items: readonly KsKbMemberItem[],
  toFolderId: string, signal?: AbortSignal,
): Promise<KsKbMemberResult> {
  const d = await kbWrite(`${String(port)}/api/v1/kb/members/copy`, 'POST', token,
    { to_folder_id: toFolderId, items: items.map((it) => ({ kind: it.kind, id: it.id })) }, signal)
  return memberResult(d, '', toFolderId, '')
}

function memberResult(
  d: Record<string, unknown>, folderId: string, toFolderId: string, fromFolderId: string,
): KsKbMemberResult {
  return {
    folder_id: str(d.folder_id) ?? folderId,
    to_folder_id: str(d.to_folder_id) ?? toFolderId,
    from_folder_id: str(d.from_folder_id) ?? fromFolderId,
    added: intOf(d.added, 0),
    skipped: intOf(d.skipped, 0),
    removed: intOf(d.removed, 0),
    moved: intOf(d.moved, 0),
    total: intOf(d.total, 0),
  }
}

/*
 * ── 「待分类」那一层（KB-FOLDER-PLAN 第 4 步）────────────────────────────────
 *
 * ⚠ 三条事实（照 `src/core/api/routes_kb_folders.py` 的代码读出来，不是印象）：
 *   · `GET /kb/inbox` 每项带 `stage` / `stage_label`（**后端下发的中文标签**，
 *     `folder_store.STAGE_LABELS` 是唯一所有者）/ `confidence` / `failure_kind` /
 *     `suggested_folder_id` / `suggested_path` / `suggest_new_parent_id` /
 *     `suggest_new_name` / `catalog_hidden`。
 *   · `suggested_folder_id` 与 `suggest_new_parent_id` **都是 null** 时，界面上**不许**
 *     渲染「按建议归位 / 在建议位置新建」—— `POST /kb/inbox/confirm` 的 `action='accept'`
 *     对没有建议的那一篇会回 **422 `no_suggestion`**（兜底桶那 379 篇全是这样）。
 *   · 「重来一次」是 `POST /kb/inbox/reingest`，**立刻返回**（后台线程真解析）；
 *     进度看每一篇的 `stage`，另有一条 `GET /kb/inbox/reingest/status`。
 */

/** 「待分类」列表里的一篇（还没归位的文件）。 */
export interface KsKbInboxItem {
  doc_id: string
  standard_no: string | null
  standard_name: string | null
  /** queued / recognizing / confirming / failed（filed 不会出现在这里）。 */
  stage: string
  /** 后端下发的中文标签（`folder_store.STAGE_LABELS` 是唯一所有者）。 */
  stage_label: string
  /** 识别率（与入库预览同一个数），没有就是 null。 */
  confidence: number | null
  failure_kind: string | null
  suggested_folder_id: string | null
  suggested_path: string | null
  /** 「在 XXX 下新建 XXX」的父目录；没有建议时是 null。 */
  suggest_new_parent_id: string | null
  suggest_new_name: string | null
  /** 1 = 这篇**不在目录里**（正文条款为零，pipeline 的目录卫生）。 */
  catalog_hidden: number | null
  /*
   * ── 分类号（CCS）这条线的底细（2026-09-22「补全分类号」）────────────────────
   *
   * ⚠ **为什么「没有建议」要带这几个字段**（业主 2026-09-22 口径「**界面把原因说清**」）：
   *   "没有建议"至少有**三种完全不同的原因**，界面上不能都写成同一句"没有建议"——
   *   ① 已经有分类号、但现有目录里没有对应那一层（树的问题，不是分类号的问题）；
   *   ② 还没有查过分类号（`ccs_outcome === null`，点「补全分类号」查一次就知道）；
   *   ③ 查过了、没查到（`ccs_outcome` 是 not_found / network_failed / parse_failed）。
   *   这三句的**依据**全在后端（`doc_ccs_state` 台账，`ccs_store` 是唯一所有者），
   *   界面只负责照念，**不自己推断**。
   */
  /** 已有的分类号标签（`CCS:P16 工程防火`）；null = 这一篇没有分类号。 */
  ccs_tag: string | null
  /** found / not_found / network_failed / parse_failed；null = **还没查过**。 */
  ccs_outcome: string | null
  /** 后端下发的中文说法（`ccs_fetcher.OUTCOME_LABELS` 是唯一所有者）。 */
  ccs_outcome_label: string | null
  /** 一句人话（为什么没有 / 是哪一层命中的），后端给。 */
  ccs_reason: string | null
  /** 命中的是哪一层（official_api / web_scrape / local_table / seed_file）。 */
  ccs_source: string | null
  ccs_checked_at: string | null
}

export interface KsKbInbox extends KsKbPageInfo {
  items: KsKbInboxItem[]
}

function normalizeKbInboxItem(value: unknown): KsKbInboxItem | null {
  const o = objOf(value)
  const id = str(o?.doc_id)
  if (o === null || id === null) return null
  return {
    doc_id: id,
    standard_no: str(o.standard_no),
    standard_name: str(o.standard_name),
    stage: str(o.stage) ?? 'queued',
    stage_label: str(o.stage_label) ?? '',
    confidence: num(o.confidence),
    failure_kind: str(o.failure_kind),
    suggested_folder_id: str(o.suggested_folder_id),
    suggested_path: str(o.suggested_path),
    suggest_new_parent_id: str(o.suggest_new_parent_id),
    suggest_new_name: str(o.suggest_new_name),
    catalog_hidden: num(o.catalog_hidden),
    ccs_tag: str(o.ccs_tag),
    ccs_outcome: str(o.ccs_outcome),
    ccs_outcome_label: str(o.ccs_outcome_label),
    ccs_reason: str(o.ccs_reason),
    ccs_source: str(o.ccs_source),
    ccs_checked_at: str(o.ccs_checked_at),
  }
}

/** `GET /api/v1/kb/inbox` —— 还没归位的文件（含"识别失败"那一批，即使它不在目录里）。 */
export async function fetchKbInbox(
  port: number,
  token: string,
  opts: { limit?: number; offset?: number; signal?: AbortSignal } = {},
): Promise<KsKbInbox> {
  const qs = new URLSearchParams()
  qs.set('limit', String(opts.limit ?? 50))
  qs.set('offset', String(opts.offset ?? 0))
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/inbox?${qs.toString()}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const rows = Array.isArray(data.items) ? data.items : []
  return {
    items: rows.map(normalizeKbInboxItem).filter((r): r is KsKbInboxItem => r !== null),
    total: intOf(data.total, rows.length),
    offset: intOf(data.offset, opts.offset ?? 0),
    limit: intOf(data.limit, opts.limit ?? 50),
    has_more: data.has_more === true,
  }
}

/** 一条归位决定（`POST /kb/inbox/confirm` 的 `decisions[i]`）。 */
export interface KsKbInboxDecision {
  doc_id: string
  action: 'accept' | 'existing' | 'new'
  target_folder_id?: string
  new_parent_id?: string
  new_name?: string
  placed_by?: string
}

/** `POST /kb/inbox/confirm` —— 批量确认归位（**一个事务**：整批全成或全败）。 */
export async function confirmKbInbox(
  port: number,
  token: string,
  decisions: readonly KsKbInboxDecision[],
  signal?: AbortSignal,
): Promise<{ confirmed: number; removed_from_pending: number; created: number }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/inbox/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ decisions }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const created = Array.isArray(data.created) ? data.created.length : 0
  return {
    confirmed: intOf(data.confirmed, 0),
    removed_from_pending: intOf(data.removed_from_pending, 0),
    created,
  }
}

/** 「重来一次」的出参（`POST /kb/inbox/reingest`；后台线程，立刻返回）。 */
export interface KsKbReingestStart {
  queued: number
  started: readonly { doc_id: string; path: string; standard_no: string }[]
  /** 没法重来的（源文件不在磁盘上 / 库里没有这一篇），**逐条给原因**。 */
  skipped: readonly { doc_id: string; reason: string }[]
}

export async function reingestKbDocs(
  port: number,
  token: string,
  docIds: readonly string[],
  signal?: AbortSignal,
): Promise<KsKbReingestStart> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/inbox/reingest`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ doc_ids: docIds }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  // 409 = 已经有一批在跑（**不是失败**）：把引擎的原话交给调用方去如实显示。
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const started = Array.isArray(data.started) ? data.started : []
  const skipped = Array.isArray(data.skipped) ? data.skipped : []
  return {
    queued: intOf(data.queued, 0),
    started: started.map((s) => {
      const o = objOf(s) ?? {}
      return { doc_id: str(o.doc_id) ?? '', path: str(o.path) ?? '', standard_no: str(o.standard_no) ?? '' }
    }).filter((s) => s.doc_id !== ''),
    skipped: skipped.map((s) => {
      const o = objOf(s) ?? {}
      return { doc_id: str(o.doc_id) ?? '', reason: str(o.reason) ?? '' }
    }),
  }
}

/** `GET /kb/inbox/reingest/status` —— 最近一批「重来一次」的进度（如实）。 */
export interface KsKbReingestStatus {
  running: boolean
  total: number
  done: number
  results: readonly { doc_id: string; status?: string; total_clauses?: number; filing_stage?: string; error?: string }[]
  started_at: string | null
  finished_at: string | null
}

export async function fetchKbReingestStatus(
  port: number, token: string, signal?: AbortSignal,
): Promise<KsKbReingestStatus> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/inbox/reingest/status`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const results = Array.isArray(data.results) ? data.results : []
  return {
    running: data.running === true,
    total: intOf(data.total, 0),
    done: intOf(data.done, 0),
    results: results.map((r) => {
      const o = objOf(r) ?? {}
      return { doc_id: str(o.doc_id) ?? '', status: str(o.status) ?? undefined,
               total_clauses: num(o.total_clauses) ?? undefined,
               filing_stage: str(o.filing_stage) ?? undefined,
               error: str(o.error) ?? undefined }
    }),
    started_at: str(data.started_at),
    finished_at: str(data.finished_at),
  }
}

/*
 * ── 「补全分类号」（CCS 自愈机制，2026-09-22）────────────────────────────────
 *
 * 业主原话：「这 380 篇**不要手动去补**……你要找的是**修机制**，然后让插件
 * **自己能靠自己的机制完成工作**。」⇒ 这一族就是那个机制的服务端外形：
 *   · `GET  /kb/ccs/summary`           还缺几篇 + 台账各结论各几篇（只读）
 *   · `GET  /kb/ccs/plan`              **只读预览**：这一批会补哪些篇（不联网）
 *   · `POST /kb/ccs/backfill`          起一批（后台线程，**立刻返回**）
 *   · `GET  /kb/ccs/backfill/status`   进度 + 失败清单（**如实**）
 *   · `POST /kb/ccs/backfill/cancel`   按停（跑完当前这一篇就停）
 * ⚠ 与「重来一次」**不共用**那把锁：查分类号（几秒一篇）与重新解析（几十分钟一篇）
 *   该能各自跑。已有批次在跑 ⇒ 409 `ccs_backfill_busy`（**不排队**）。
 */

/** `GET /kb/ccs/summary` —— 分类号这件事的现状（只读，零网络）。 */
export interface KsKbCcsSummary {
  /** 全库还有几篇标准没有分类号（**现算的**，不是计数器）。 */
  missing: number
  /** 台账按结论计数（found / not_found / network_failed / parse_failed）。 */
  by_outcome: Record<string, number>
  max_batch: number
  default_batch: number
  outcome_labels: Record<string, string>
  source_labels: Record<string, string>
  sources: readonly string[]
  backfill: KsKbCcsBackfillStatus
}

/** 一行候选（`GET /kb/ccs/plan` 的 `candidates[i]`）。 */
export interface KsKbCcsPlanRow {
  doc_id: string
  standard_no: string
  standard_name: string
}

export interface KsKbCcsPlan {
  candidates: readonly KsKbCcsPlanRow[]
  total: number
  already_have: number
  limit: number
  truncated: boolean
}

/** 一篇的补全结果（`status.results[i]` / `status.failures[i]`）。 */
export interface KsKbCcsResultRow {
  doc_id: string
  standard_no: string
  standard_name?: string
  /** found / not_found / network_failed / parse_failed / not_applicable / skipped。 */
  outcome: string
  code?: string
  sub?: string
  source?: string
  keyword_form?: string
  matched_no?: string
  reason?: string
  tag?: string
  applied?: boolean
}

/** `GET /kb/ccs/backfill/status` —— 最近一批的进度（如实）。 */
export interface KsKbCcsBackfillStatus {
  running: boolean
  total: number
  done: number
  found: number
  not_found: number
  network_failed: number
  parse_failed: number
  /** 这一篇的号不像标准号（如被标成 standard 的法规）⇒ 分类号对它不适用。 */
  not_applicable: number
  applied: number
  skipped: number
  cancel_requested: boolean
  cancelled: boolean
  started_at: string | null
  finished_at: string | null
  /** **现算的**"全库还缺几篇"（补完自己会降，不靠计数器对齐）。 */
  missing: number | null
  results: readonly KsKbCcsResultRow[]
  /** 没补到的那一批（每篇带 outcome 与 reason）—— 业主/审计靠它看"还剩哪些、为什么"。 */
  failures: readonly KsKbCcsResultRow[]
  skipped_list: readonly KsKbCcsResultRow[]
}

function normalizeCcsResultRows(value: unknown): KsKbCcsResultRow[] {
  const rows = Array.isArray(value) ? value : []
  return rows.map((r) => {
    const o = objOf(r) ?? {}
    return {
      doc_id: str(o.doc_id) ?? '',
      standard_no: str(o.standard_no) ?? '',
      standard_name: str(o.standard_name) ?? undefined,
      outcome: str(o.outcome) ?? '',
      code: str(o.code) ?? undefined,
      sub: str(o.sub) ?? undefined,
      source: str(o.source) ?? undefined,
      keyword_form: str(o.keyword_form) ?? undefined,
      matched_no: str(o.matched_no) ?? undefined,
      reason: str(o.reason) ?? undefined,
      tag: str(o.tag) ?? undefined,
      applied: o.applied === true,
    }
  })
}

function normalizeCcsBackfillStatus(data: Record<string, unknown>): KsKbCcsBackfillStatus {
  return {
    running: data.running === true,
    total: intOf(data.total, 0),
    done: intOf(data.done, 0),
    found: intOf(data.found, 0),
    not_found: intOf(data.not_found, 0),
    network_failed: intOf(data.network_failed, 0),
    parse_failed: intOf(data.parse_failed, 0),
    not_applicable: intOf(data.not_applicable, 0),
    applied: intOf(data.applied, 0),
    skipped: intOf(data.skipped, 0),
    cancel_requested: data.cancel_requested === true,
    cancelled: data.cancelled === true,
    started_at: str(data.started_at),
    finished_at: str(data.finished_at),
    missing: num(data.missing),
    results: normalizeCcsResultRows(data.results),
    failures: normalizeCcsResultRows(data.failures),
    skipped_list: normalizeCcsResultRows(data.skipped_list),
  }
}

/** `GET /kb/ccs/summary` —— 还缺几篇 + 台账计数 + 最近一批进度（**只读，零网络**）。 */
export async function fetchKbCcsSummary(
  port: number, token: string, signal?: AbortSignal,
): Promise<KsKbCcsSummary> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/ccs/summary`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const byOutcome = objOf(data.by_outcome) ?? {}
  const by: Record<string, number> = {}
  for (const [k, v] of Object.entries(byOutcome)) by[k] = intOf(v, 0)
  const labels = objOf(data.outcome_labels) ?? {}
  const srcLabels = objOf(data.source_labels) ?? {}
  const outLabels: Record<string, string> = {}
  for (const [k, v] of Object.entries(labels)) { const s = str(v); if (s !== null) outLabels[k] = s }
  const outSrc: Record<string, string> = {}
  for (const [k, v] of Object.entries(srcLabels)) { const s = str(v); if (s !== null) outSrc[k] = s }
  const srcArr = Array.isArray(data.sources) ? data.sources : []
  return {
    missing: intOf(data.missing, 0),
    by_outcome: by,
    max_batch: intOf(data.max_batch, 0),
    default_batch: intOf(data.default_batch, 0),
    outcome_labels: outLabels,
    source_labels: outSrc,
    sources: srcArr.map((s) => str(s) ?? '').filter((s) => s !== ''),
    backfill: normalizeCcsBackfillStatus(objOf(data.backfill) ?? {}),
  }
}

/** `GET /kb/ccs/plan` —— **只读预览**：这一批会补哪些篇（不写库、不联网、不起线程）。 */
export async function fetchKbCcsPlan(
  port: number, token: string,
  opts: { limit?: number; force?: boolean; signal?: AbortSignal } = {},
): Promise<KsKbCcsPlan> {
  const qs = new URLSearchParams()
  qs.set('limit', String(opts.limit ?? 0))
  if (opts.force === true) qs.set('force', 'true')
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/ccs/plan?${qs.toString()}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const rows = Array.isArray(data.candidates) ? data.candidates : []
  return {
    candidates: rows.map((r) => {
      const o = objOf(r) ?? {}
      return { doc_id: str(o.doc_id) ?? '', standard_no: str(o.standard_no) ?? '',
               standard_name: str(o.standard_name) ?? '' }
    }).filter((r) => r.doc_id !== ''),
    total: intOf(data.total, rows.length),
    already_have: intOf(data.already_have, 0),
    limit: intOf(data.limit, 0),
    truncated: data.truncated === true,
  }
}

/** `POST /kb/ccs/backfill` 的出参（后台线程，**立刻返回**）。 */
export interface KsKbCcsBackfillStart {
  queued: number
  started: readonly { doc_id: string; standard_no: string }[]
  skipped: readonly { doc_id: string; reason: string }[]
  plan: KsKbCcsPlan
}

export async function startKbCcsBackfill(
  port: number, token: string,
  opts: { docIds?: readonly string[]; limit?: number; force?: boolean; signal?: AbortSignal } = {},
): Promise<KsKbCcsBackfillStart> {
  const payload: Record<string, unknown> = {}
  if (opts.docIds !== undefined) payload.doc_ids = [...opts.docIds]
  if (opts.limit !== undefined) payload.limit = opts.limit
  if (opts.force === true) payload.force = true
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/ccs/backfill`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(payload),
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  // 409 = 已经有一批在跑（**不是失败**）：把引擎的原话交给调用方如实显示。
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const started = Array.isArray(data.started) ? data.started : []
  const skipped = Array.isArray(data.skipped) ? data.skipped : []
  const planRaw = objOf(data.plan) ?? {}
  const planRows = Array.isArray(planRaw.candidates) ? planRaw.candidates : []
  return {
    queued: intOf(data.queued, 0),
    started: started.map((s) => {
      const o = objOf(s) ?? {}
      return { doc_id: str(o.doc_id) ?? '', standard_no: str(o.standard_no) ?? '' }
    }).filter((s) => s.doc_id !== ''),
    skipped: skipped.map((s) => {
      const o = objOf(s) ?? {}
      return { doc_id: str(o.doc_id) ?? '', reason: str(o.reason) ?? '' }
    }),
    plan: {
      candidates: planRows.map((r) => {
        const o = objOf(r) ?? {}
        return { doc_id: str(o.doc_id) ?? '', standard_no: str(o.standard_no) ?? '',
                 standard_name: str(o.standard_name) ?? '' }
      }).filter((r) => r.doc_id !== ''),
      total: intOf(planRaw.total, planRows.length),
      already_have: intOf(planRaw.already_have, 0),
      limit: intOf(planRaw.limit, 0),
      truncated: planRaw.truncated === true,
    },
  }
}

/** `GET /kb/ccs/backfill/status` —— 最近一批的进度（如实：进度 + 失败清单）。 */
export async function fetchKbCcsBackfillStatus(
  port: number, token: string, signal?: AbortSignal,
): Promise<KsKbCcsBackfillStatus> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/ccs/backfill/status`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  return normalizeCcsBackfillStatus(dataOf(body))
}

/** `POST /kb/ccs/backfill/cancel` —— 按停（**跑完当前这一篇**才停；别谎报"已停止"）。 */
export async function cancelKbCcsBackfill(
  port: number, token: string, signal?: AbortSignal,
): Promise<{ cancel_requested: boolean; running: boolean; done: number; total: number }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/ccs/backfill/cancel`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  return {
    cancel_requested: data.cancel_requested === true,
    running: data.running === true,
    done: intOf(data.done, 0),
    total: intOf(data.total, 0),
  }
}

/** 目录选择器用的一行：`folder_id` + 完整显示路径 + 层级深度。 */
export interface KsKbFlatFolder {
  folder_id: string
  parent_id: string | null
  name: string
  path: string
  depth: number
}

/**
 * `GET /api/v1/kb/folders/flat` —— **整棵目录树的扁平清单**（每行带路径）。
 *
 * ⚠ 为什么不是"一层层点"：真库 **1127 个目录**，而业主在"这一篇放哪儿"这一刻需要的是
 * **按名字找**。整棵树约 **80KB**（方案 §七那条红线管的是**文件**元数据 ~9.7MB，不是目录清册）。
 */
export async function fetchKbFoldersFlat(
  port: number,
  token: string,
  opts: { q?: string; signal?: AbortSignal } = {},
): Promise<KsKbFlatFolder[]> {
  const qs = new URLSearchParams()
  if (opts.q !== undefined && opts.q !== '') qs.set('q', opts.q)
  const suffix = qs.toString() === '' ? '' : `?${qs.toString()}`
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/folders/flat${suffix}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const rows = Array.isArray(data.items) ? data.items : []
  return rows.map((r) => {
    const o = objOf(r) ?? {}
    return {
      folder_id: str(o.folder_id) ?? '',
      parent_id: str(o.parent_id),
      name: str(o.name) ?? '',
      path: str(o.path) ?? '',
      depth: intOf(o.depth, 1),
    }
  }).filter((f) => f.folder_id !== '')
}

/**
 * `GET /api/v1/kb/stage-labels` —— 处理状态的中文标签（**后端是唯一所有者**）。
 *
 * ⚠ 第 3 步界面里抄了一份镜像（`KsKnowledgePage.tsx` 的 `STAGE_LABELS`）⇒ 后端改了档位
 * 文字界面不跟着变、还没有东西会响。第 4 步改成"接口下发、界面只在拿不到时兜底"。
 */
export async function fetchKbStageLabels(
  port: number, token: string, signal?: AbortSignal,
): Promise<{ labels: Record<string, string>; stages: readonly string[] }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/stage-labels`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, accept: 'application/json' },
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const raw = objOf(data.labels) ?? {}
  const labels: Record<string, string> = {}
  for (const [k, v] of Object.entries(raw)) if (typeof v === 'string') labels[k] = v
  const stages = Array.isArray(data.stages) ? data.stages.filter((s): s is string => typeof s === 'string') : []
  return { labels, stages }
}

/**
 * `POST /kb/inbox/confirm` 的 `action='existing'` —— **把这批文件放进某个目录并标成已归位**。
 *
 * ⚠ 为什么上传落位走**这一条**而不是只调 `addKbMembers`（两处形状都是照源码读出来的）：
 *   · `add_member` **只写 `folder_member`**，不碰 `doc_filing_state`；
 *   · 「待分类」的口径是 `COALESCE(s.stage,'queued') IN (queued,recognizing,confirming,failed)`
 *     （`folder_store.list_pending_filing`）⇒ **刚导入的文件没有状态行 = `queued`**，
 *     只挂目录的话它**照样出现在「待分类」里**（= 进了自动识别那条线）。
 *   · `confirm_inbox_decisions(action='existing', target_folder_id=…)` 在**同一个事务**里
 *     做三件事：`_add_member_in_tx(target,'file',doc_id)`、`stage='filed'`、
 *     记 `placed_folder_id/placed_by/placed_at`，并把该文件从「待分类」那一处拿掉。
 *   ⇒ 业主那句「**上传进当前这一层 = 不进自动识别**」在现有接口里**只有这一条**能如实表达。
 */
export async function fileDocsIntoFolder(
  port: number,
  token: string,
  folderId: string,
  docIds: readonly string[],
  signal?: AbortSignal,
): Promise<{ confirmed: number; removed_from_pending: number }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/kb/inbox/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({
      decisions: docIds.map((docId) => ({
        doc_id: docId, action: 'existing', target_folder_id: folderId, placed_by: 'kb-upload',
      })),
    }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  return {
    confirmed: intOf(data.confirmed, 0),
    removed_from_pending: intOf(data.removed_from_pending, 0),
  }
}

/*
 * ── 第 6 步：按**知识库目录范围**提问（`POST /api/v1/ks/answer`）──────────────────
 *
 * ⚠ 与收藏夹那条**不是一回事**（名字刻意不同，防歧义）：
 *   · `params.folder_id` = **收藏夹**（书签夹）—— 引擎里只对**证据**做后置过滤，**不动检索**；
 *   · `params.kb_folder_ids` = **知识库目录**（本步新增）—— 引擎**在检索层**把六条召回通道
 *     全部限定在"这些目录及其所有下级"的文档里；多选 = **并集**；
 *   · `params.kb_doc_ids` = 显式文件范围（「待分类」那一层用：那批文件还没进任何目录）。
 * ⚠ 空范围（目录里一篇都没有）⇒ 引擎**一次检索都不做**，如实说"范围内没有"，**绝不**退化成全库。
 * ⚠ 回参里的 `scope` 是"这一次到底限定在哪"的权威数字（`folder_count`/`doc_count`/`empty`），
 *   界面上的范围 chip **必须**用它，不要拿"选了几个目录"自己编篇数。
 */

/** `POST /api/v1/ks/answer` 里我们关心的那几个字段（其余原样透传给调用方渲染）。 */
export interface KsAnswerScope {
  kind: string
  folder_ids: string[]
  folder_count: number
  doc_count: number
  empty: boolean
}

export interface KsAnswerResult {
  tier: string
  evidence: Array<Record<string, unknown>>
  derivation: string
  conclusion: string
  notes: string[]
  /** 知识库目录范围的回显；**没给范围时是 `null`**（"没限定"与"限定了但范围内没有"可区分）。 */
  scope: KsAnswerScope | null
  [k: string]: unknown
}

function normalizeAnswerScope(value: unknown): KsAnswerScope | null {
  const o = objOf(value)
  if (o === null) return null
  return {
    kind: str(o.kind) ?? 'kb',
    folder_ids: Array.isArray(o.folder_ids)
      ? o.folder_ids.filter((x): x is string => typeof x === 'string') : [],
    folder_count: intOf(o.folder_count, 0),
    doc_count: intOf(o.doc_count, 0),
    empty: o.empty === true,
  }
}

/**
 * 问一次（取证答案）。范围三选一：`kbFolderIds`（知识库目录，多选=并集）/
 * `kbDocIds`（显式文件范围）/ 都不给 = 全库。
 */
export async function askKsAnswer(
  port: number, token: string, query: string,
  opts: {
    kbFolderIds?: readonly string[]
    kbDocIds?: readonly string[]
    topK?: number
    signal?: AbortSignal
  } = {},
): Promise<KsAnswerResult> {
  const params: Record<string, unknown> = {}
  if (opts.kbFolderIds !== undefined && opts.kbFolderIds.length > 0) {
    params.kb_folder_ids = [...opts.kbFolderIds]
  }
  if (opts.kbDocIds !== undefined && opts.kbDocIds.length > 0) {
    params.kb_doc_ids = [...opts.kbDocIds]
  }
  if (opts.topK !== undefined) params.top_k = opts.topK
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/ks/answer`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
      accept: 'application/json',
    },
    body: JSON.stringify({ query, params }),
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) {
    /* 404 `kb_scope_not_found` 等由引擎原话透传（端点会把"目录不存在"如实报出来，
       绝不静默当成全库）。 */
    throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  }
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const d = dataOf(body)
  return {
    ...d,
    tier: str(d.tier) ?? 'reference',
    evidence: Array.isArray(d.evidence)
      ? d.evidence.filter((x): x is Record<string, unknown> => objOf(x) !== null) : [],
    derivation: str(d.derivation) ?? '',
    conclusion: str(d.conclusion) ?? '',
    notes: Array.isArray(d.notes) ? d.notes.filter((x): x is string => typeof x === 'string') : [],
    scope: normalizeAnswerScope(d.scope),
  }
}

/** `POST /api/v1/kb/scope/resolve` 的返回：这些目录**及其所有下级**的集合。 */
export interface KsKbScope {
  folder_ids: string[]
  doc_ids: string[]
  folder_count: number
  doc_count: number
  roots: string[]
}

/**
 * 把"选中的几个目录"展开成"它们**及其所有下级**里到底有哪些文档"。
 *
 * ⚠ 这是**发问之前**把范围 chip 上的篇数写成**权威数字**用的；任一个目录不存在 ⇒
 * 引擎 **404**（原话抛出，绝不静默返回空范围 —— 空范围会让"在此范围内提问"悄悄变成全库提问）。
 */
export async function resolveKbScope(
  port: number, token: string, folderIds: readonly string[], signal?: AbortSignal,
): Promise<KsKbScope> {
  const d = await kbWrite(`${String(port)}/api/v1/kb/scope/resolve`, 'POST', token,
    { folder_ids: [...folderIds] }, signal)
  const ids = (v: unknown): string[] => Array.isArray(v)
    ? v.filter((x): x is string => typeof x === 'string') : []
  return {
    folder_ids: ids(d.folder_ids),
    doc_ids: ids(d.doc_ids),
    folder_count: intOf(d.folder_count, ids(d.folder_ids).length),
    doc_count: intOf(d.doc_count, ids(d.doc_ids).length),
    roots: ids(d.roots),
  }
}

/*
 * ── 上传用的**真导入**通路（引擎侧，不是 host 代理的那套「预览」）──
 *
 * ⚠ 事实核对（写在这里免得下一个人再猜一次）：
 *   · `plugin/src/ingest.js` 代理的是 `/api/v1/ingest/**preview**` 一族 —— 那是
 *     **只读体检（dry-run）**，不建文档；
 *   · **真导入**是引擎的 `POST /api/v1/ingest/bulk`（`src/core/api/routes_update.py`
 *     `bulk_ingest_start` → 后台线程 `fast_scan` → `resume` 逐件解析建 `doc_meta`），
 *     host **没有**给它做代理；本文件按既有范式（`fetchSession` 拿 port+token 后直连
 *     回环引擎，见 `fetchDocTree`）直接调它。
 */

/** 一个批量导入批次的进度（`GET /api/v1/ingest/bulk/{batch_id}`）。 */
export interface KsBulkIngestStatus {
  batch_id: string
  /** running / done / failed / paused（`bulk_import_batch.status`）。 */
  status: string
  total: number
  scanned: number
  parsed: number
  pending: number
  errors: number
  pause_reason: string | null
  /** 这一批里**处理状态没写进库**的文件数（2026-09-21 第 5 步挂账 ③a）。
   *  ⚠ 它们照样出现在「待分类」里（那里"没有状态行 = 排队中"），但界面必须**能看出**
   *  这批里有文件的状态没落库 —— 否则业主看到的"排队中"是假的。 */
  filing_state_missing: number
  /** 上面那批文件的前 5 个**文件名**（样本，用来如实指名道姓）。 */
  filing_state_missing_sample: string[]
  /** 这一批是不是「覆盖重导」（同号旧文档会被替换）。 */
  reingest: boolean
}

/** `POST /api/v1/ingest/bulk` —— 启动批量导入，立即返回 `batch_id`（后台快扫）。
 *
 * `opts.reingest`（= 界面上的「覆盖重导」）透传到引擎的 `reingest`/`force`：**明知库里已有
 * 同号/同文件的登记也覆盖重导**（默认 false = 不覆盖）。⚠ 它会**删掉同标准号的旧文档再建新的**
 * ⇒ 界面上必须由人显式勾选，不许替业主默认打开。 */
export async function startBulkIngest(
  port: number, token: string, srcDir: string,
  opts: { reingest?: boolean; signal?: AbortSignal } = {},
): Promise<{ batch_id: string; total: number }> {
  const res = await fetch(`http://127.0.0.1:${port}/api/v1/ingest/bulk`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
    body: JSON.stringify({ src_dir: srcDir, reingest: opts.reingest === true }),
    signal: opts.signal,
  })
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const batchId = str(data.batch_id)
  if (batchId === null) throw new Error('批量导入响应里没有 batch_id')
  return { batch_id: batchId, total: intOf(data.total, 0) }
}

/** `POST /api/v1/ingest/bulk/{id}/resume` —— 快扫完成后开始逐件解析（后台线程）。 */
export async function resumeBulkIngest(
  port: number, token: string, batchId: string, signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/ingest/bulk/${encodeURIComponent(batchId)}/resume`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', accept: 'application/json' },
      body: '{}',
      signal,
    },
  )
  if (res.status === 401) {
    clearSession()
    throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')
  }
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
}

/** `GET /api/v1/ingest/bulk/{id}` —— 批次进度（快扫 checked/total + 解析队列统计）。 */
export async function fetchBulkIngest(
  port: number, token: string, batchId: string, signal?: AbortSignal,
): Promise<KsBulkIngestStatus> {
  const res = await fetch(
    `http://127.0.0.1:${port}/api/v1/ingest/bulk/${encodeURIComponent(batchId)}`,
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
  if (!res.ok) throw new Error(await engineErrorMessage(res, `引擎返回 HTTP ${res.status}`))
  let body: unknown = null
  try { body = await res.json() } catch { /* non-JSON body */ }
  const data = dataOf(body)
  const sample = Array.isArray(data.filing_state_missing_sample)
    ? data.filing_state_missing_sample.filter((s): s is string => typeof s === 'string')
    : []
  return {
    batch_id: str(data.batch_id) ?? batchId,
    status: str(data.status) ?? 'unknown',
    total: intOf(data.total, 0),
    scanned: intOf(data.scanned, 0),
    parsed: intOf(data.parsed, 0),
    pending: intOf(data.pending, 0),
    errors: intOf(data.errors, 0),
    pause_reason: str(data.pause_reason),
    filing_state_missing: intOf(data.filing_state_missing, 0),
    filing_state_missing_sample: sample,
    reingest: data.reingest === true,
  }
}
