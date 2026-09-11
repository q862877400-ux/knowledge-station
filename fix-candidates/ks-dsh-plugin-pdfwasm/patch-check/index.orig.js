/**
 * ks-dsh-plugin — src/index.js
 *
 * DSH cordis plugin (host half). Registers three model-facing tools that talk
 * to the KnowledgeStation Python engine over its authenticated HTTP API:
 *
 *   ks_ping            -> GET /api/v1/health            (no token)
 *   ks_resolve_clause  -> GET /api/v1/clauses/resolve   (Bearer token)
 *   ks_answer          -> POST /api/v1/ks/answer        (Bearer token, P1b)
 *
 * The engine is launched lazily on first tool call and reused if a healthy
 * instance already exists (single-instance principle: read engine.session.json
 * + probe /health). Every tool call re-reads the session file, because the
 * engine's port/token rotate on every start. Only an engine spawned by this
 * manager is ever stopped (idle timeout + dispoose); a pre-existing healthy
 * instance is reused and never killed.
 *
 * Exports (cordis plugin contract): `name`, `inject`, `apply(ctx, config)`.
 */

import { createRequire } from 'node:module'
import { readFile, readdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import {
  EngineManager,
  apiGet,
  apiPost,
  originUrl,
  HEALTH_PATH,
  KS_ANSWER_PATH,
} from './engine.js'

/** Plugin identity for the cordis.yml row (matches package.json name). */
export const name = 'ks-dsh-plugin'

/** Services required before the plugin mounts. */
export const inject = ['tools', 'webServer']

// P1c-RouteA: 同源路由（client 半经此取引擎会话 / pdf.js worker 与 wasm 资源）
export const KS_SESSION_PATH = '/ks/session'
export const KS_PDF_WORKER_PATH = '/ks/assets/pdf.worker.min.mjs'
export const KS_PDF_WASM_PATH = '/ks/assets/pdf-wasm'

// Defaults consumed by `apply` when config omits them.
const DEFAULTS = {
  engineRoot: undefined, // -> EngineManager default (repo root)
  python: undefined, // -> $KS_PYTHON or repo venv
  startupTimeoutMs: 60_000,
  idleTimeoutMs: 15 * 60 * 1000,
}

// ---------------------------------------------------------------------------
// ks_answer helpers (P1b — trim the engine answer for the model's prompt)
// ---------------------------------------------------------------------------

/** Legal `query_mode` values (engine contract: R9 four-tier). */
const QUERY_MODES = ['default', 'thorough', 'quick', 'guess']

/** Cap for each verification list we hand back to the model. */
const VERIFY_LIST_CAP = 8

/** Cap evidence we keep (the engine already caps at 8; this is a hard belt). */
const EVIDENCE_CAP = 8

/** Coerce any query_mode into one of the four legal values. */
function normalizeQueryMode(raw) {
  const mode = String(raw ?? 'default').trim()
  return QUERY_MODES.includes(mode) ? mode : 'default'
}

/**
 * Sanitize the optional retrieval `params` bucket. Only the three knobs the
 * tool surface exposes are accepted; unknown keys are silently dropped so a
 * stray model field can never reach the engine or blow up the body. Returns
 * null when nothing valid is supplied (the engine treats null as "{}").
 */
function sanitizeParams(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const out = {}
  if (raw.top_k !== undefined) {
    const k = Number(raw.top_k)
    if (Number.isFinite(k) && k > 0) out.top_k = Math.min(Math.floor(k), 50)
  }
  if (raw.bookmarks_only !== undefined) out.bookmarks_only = Boolean(raw.bookmarks_only)
  if (raw.max_evidence !== undefined) {
    const m = Number(raw.max_evidence)
    if (Number.isFinite(m) && m > 0) out.max_evidence = Math.min(Math.floor(m), EVIDENCE_CAP)
  }
  return Object.keys(out).length > 0 ? out : null
}

/** Compact a single verification-list item (string, number, or object). */
function compact(item) {
  if (item === null || item === undefined) return null
  if (typeof item === 'string') return item
  if (typeof item === 'object') {
    try {
      const s = JSON.stringify(item)
      return s.length > 160 ? `${s.slice(0, 157)}…` : s
    } catch {
      return String(item)
    }
  }
  return item
}

/** Truncate a verification list to a bounded, JSON-safe form. */
function shortList(arr, cap = VERIFY_LIST_CAP) {
  if (!Array.isArray(arr) || arr.length === 0) return []
  return arr.slice(0, cap).map(compact)
}

/** Trim one evidence item to the model-relevant fields (no internal `_` fields). */
function trimEvidence(ev) {
  if (!ev || typeof ev !== 'object') return null
  return {
    standard_no: ev.standard_no ?? null,
    clause_number: ev.clause_number ?? null,
    title: ev.title ?? null,
    legal_status: ev.legal_status ?? null,
    legal_hierarchy: ev.legal_hierarchy ?? null,
    page_start: ev.page_start ?? null,
    snippet: typeof ev.snippet === 'string' ? ev.snippet : null,
    doc_id: ev.doc_id ?? null,
    clause_revision_id: ev.clause_revision_id ?? null,
  }
}

/** Trim the verification block: keep the verdict, truncate/compact the lists. */
function trimVerification(v) {
  if (!v || typeof v !== 'object') return null
  return {
    is_valid: !!v.is_valid,
    answer_confidence: v.answer_confidence ?? 'unknown',
    confidence_reasons: shortList(v.confidence_reasons),
    unsupported_clauses: shortList(v.unsupported_clauses),
    unverified_numbers: shortList(v.unverified_numbers),
    modality_violations: shortList(v.modality_violations),
    legal_element_violations: shortList(v.legal_element_violations),
    citation_index_warnings: shortList(v.citation_index_warnings),
  }
}

/** Fold the engine's `_meta` object into a single-line (bounded) summary. */
function metaSummary(meta) {
  if (!meta || typeof meta !== 'object') return ''
  const retr = meta.retrieval && typeof meta.retrieval === 'object' ? meta.retrieval : {}
  const parts = []
  if (meta.evidence_total !== undefined) parts.push(`evidence_total=${meta.evidence_total}`)
  if (retr.result_count !== undefined) parts.push(`result_count=${retr.result_count}`)
  if (retr.expanded_count !== undefined) parts.push(`expanded_count=${retr.expanded_count}`)
  if (retr.vector_engine !== undefined) parts.push(`vector=${retr.vector_engine}`)
  if (retr.rerank !== undefined) {
    const on = retr.rerank && typeof retr.rerank === 'object'
    parts.push(`rerank=${on ? 'on' : String(retr.rerank)}`)
  }
  if (meta.llm_raw_length !== undefined) parts.push(`llm_raw_len=${meta.llm_raw_length}`)
  if (meta.llm_error) parts.push(`llm_error=${String(meta.llm_error)}`)
  return parts.join(' ')
}

/**
 * Trim the engine's forensic answer to what the model actually needs, dropping
 * `_meta` and every oversized/redundant field (the evidence keeps only the
 * citation-relevant fields, the verification lists are truncated + compacted).
 * This keeps a single tool return far under the prompt budget (evidence <= 8,
 * snippet <= 800 chars each are already enforced by the engine).
 */
function trimAnswer(data) {
  if (!data || typeof data !== 'object') return null
  const evidence = (Array.isArray(data.evidence) ? data.evidence : [])
    .map(trimEvidence)
    .filter(Boolean)
    .slice(0, EVIDENCE_CAP)
  return {
    tier: typeof data.tier === 'string' ? data.tier : 'reference',
    evidence,
    derivation: String(data.derivation ?? '').trim(),
    conclusion: String(data.conclusion ?? '').trim(),
    verification: trimVerification(data.verification),
    notes: (Array.isArray(data.notes) ? data.notes : []).map((n) => String(n)),
    meta_summary: metaSummary(data._meta),
  }
}

/** Structured result for a semantically bad request (422) — no throw. */
function validationError(probe, query, queryMode) {
  const body = probe.body
  const message = body && typeof body === 'object' && body.message ? String(body.message) : ''
  const code = body && typeof body === 'object' && body.error ? String(body.error) : 'bad_request'
  return {
    ok: false,
    httpStatus: probe.status,
    tier: null,
    found: false,
    query,
    query_mode: queryMode,
    error: { code, message },
    evidence: [],
    derivation: '',
    conclusion: '',
    verification: null,
    notes: [],
    meta_summary: '',
  }
}

/** Build the `ks_ping` tool definition. */
function makePingTool(manager) {
  return {
    name: 'ks_ping',
    description:
      'Probe the local KnowledgeStation engine. Returns the live engine session ' +
      '(port, pid, reused) and the /api/v1/health payload (status, uptime, db_status, vector_engine, parser_worker). ' +
      'Use it to confirm the engine is up before querying clauses.',
    parameters: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      description: 'No arguments.',
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 20_000,
    async execute(_args, exec) {
      const session = await manager.ensureLive(exec.signal)
      const probe = await apiGet(originUrl(session.port), HEALTH_PATH, {
        signal: exec.signal,
        timeoutMs: 12_000,
      })
      if (probe.status !== 200) {
        throw new Error(
          `ks_ping: /api/v1/health returned HTTP ${probe.status || 'no-response'}${probe.error ? ` (${probe.error})` : ''}`,
        )
      }
      // /api/v1/health 是扁平 JSON（无 {code,status,data} 信封）——不要取 .data，
      // 只取明确字段且全部为标量/布尔，杜绝 undefined 混入（DSH lossless 校验拒绝 undefined）。
      const body = probe.body && typeof probe.body === 'object' ? probe.body : null
      return {
        ok: true,
        httpStatus: probe.status,
        engine: {
          port: session.port,
          pid: session.pid,
          reused: !session.spawnedByUs,
        },
        status: body?.status ?? null,
        uptimeSeconds: body?.uptime_seconds ?? null,
        dbStatus: body?.db_status ?? null,
        vectorEngine: body?.vector_engine ?? null,
        parserWorker: body?.parser_worker ?? null,
      }
    },
  }
}

/** Build the `ks_resolve_clause` tool definition. */
function makeResolveTool(manager) {
  return {
    name: 'ks_resolve_clause',
    description:
      'Resolve a "standard_no + clause_number" citation against the local KnowledgeStation ' +
      'library. Returns the machine evidence the engine found (matched clause ids, titles, ' +
      'text) or an explicit not-found marker. Args are URL-encoded by the tool.',
    parameters: {
      type: 'object',
      properties: {
        standard_no: {
          type: 'string',
          description:
            'Standard / law full number, e.g. "GB 30871-2022" or "个人信息保护法". URL-encoded automatically.',
        },
        clause_number: {
          type: 'string',
          description: 'Clause number, e.g. "5.2.3", "第四百九十六条", "前言N", "表2". URL-encoded automatically.',
        },
      },
      required: ['standard_no', 'clause_number'],
      additionalProperties: false,
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 25_000,
    async execute(args, exec) {
      const standardNo = String((args && args.standard_no) ?? '').trim()
      const clauseNumber = String((args && args.clause_number) ?? '').trim()
      if (!standardNo) throw new Error('ks_resolve_clause: "standard_no" is required and must be a non-empty string')
      if (!clauseNumber) throw new Error('ks_resolve_clause: "clause_number" is required and must be a non-empty string')

      const session = await manager.ensureLive(exec.signal)
      const path =
        `/api/v1/clauses/resolve?standard_no=${encodeURIComponent(standardNo)}` +
        `&clause_number=${encodeURIComponent(clauseNumber)}`
      const probe = await apiGet(originUrl(session.port), path, {
        token: session.token,
        signal: exec.signal,
        timeoutMs: 15_000,
      })

      if (probe.status === 401) {
        throw new Error(
          'ks_resolve_clause: engine rejected the Bearer token (401). The engine session may have rotated; retry.',
        )
      }
      if (probe.status >= 500) {
        throw new Error(`ks_resolve_clause: engine error HTTP ${probe.status}: ${probe.error || probe.text}`)
      }

      const body = probe.body
      const data = body && typeof body === 'object' ? body.data : null
      const isEmpty = data == null || (Array.isArray(data) && data.length === 0) || (typeof data === 'object' && Object.keys(data).length === 0)
      return {
        standard_no: standardNo,
        clause_number: clauseNumber,
        httpStatus: probe.status,
        ok: probe.status === 200,
        found: !isEmpty,
        data,
        envelope: body,
      }
    },
  }
}

/** Build the `ks_answer` tool definition (P1b forensic-answer). */
function makeAnswerTool(manager) {
  return {
    name: 'ks_answer',
    description:
      'Run a forensic (取证) compliance question against the local KnowledgeStation engine and ' +
      'return a trimmed three-part answer: 依据区 evidence -> 推导区 derivation -> 结论区 conclusion, ' +
      'plus tier, verification confidence and notes. The engine runs its OWN DeepSeek inference ' +
      'behind this call, so it can take tens of seconds — the caller timeout is set high (>=120s). ' +
      'Prefer a cheap ks_resolve_clause first when a fast citation lookup is enough; use ks_answer ' +
      'only for a real forensic answer. Only current-effective clauses are cited; upcoming revisions ' +
      'are surfaced in notes. A "reference" tier or empty evidence means the engine found no direct ' +
      'current provision (returned as a structured empty result, not a hard error).',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            'The compliance / regulatory question, e.g. "动火作业怎么分级" or "气体探头装多高". Required.',
        },
        params: {
          type: 'object',
          properties: {
            top_k: {
              type: 'integer',
              description: 'Retrieval top-K for the engine (default 8). Clamped to <=50.',
            },
            bookmarks_only: {
              type: 'boolean',
              description: 'Restrict retrieval to bookmarked clauses only (default false).',
            },
            max_evidence: {
              type: 'integer',
              description: 'Max evidence items to return (default 8; the engine hard-caps at 8).',
            },
          },
          additionalProperties: false,
          description: 'Optional retrieval knobs passed to the engine.',
        },
        query_mode: {
          type: 'string',
          enum: ['default', 'thorough', 'quick', 'guess'],
          description: 'Question-depth / answer mode (default "default").',
        },
      },
      required: ['query'],
      additionalProperties: false,
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 120_000,
    async execute(args, exec) {
      const query = String((args && args.query) ?? '').trim()
      if (!query) throw new Error('ks_answer: "query" is required and must be a non-empty string')
      const params = sanitizeParams(args && args.params)
      const queryMode = normalizeQueryMode(args && args.query_mode)

      const session = await manager.ensureLive(exec.signal)
      const call = (sess, signal) =>
        apiPost(originUrl(sess.port), KS_ANSWER_PATH, {
          token: sess.token,
          signal,
          timeoutMs: 120_000,
          body: { query, params, query_mode: queryMode },
        })

      let probe = await call(session, exec.signal)

      // 401 -> the session file may have rotated (port/token change per engine
      // start). Re-read the session and retry ONCE before surfacing an error.
      if (probe.status === 401) {
        const fresh = await manager.ensureLive(exec.signal)
        if (fresh && (fresh.port !== session.port || fresh.token !== session.token)) {
          probe = await call(fresh, exec.signal)
        }
      }

      if (probe.status === 401) {
        throw new Error(
          'ks_answer: engine rejected the Bearer token (401) even after a session re-read. ' +
            'The engine session may be misconfigured or the token rotated mid-call; retry.',
        )
      }
      if (probe.status === 422) {
        return validationError(probe, query, queryMode)
      }
      if (probe.status >= 500) {
        throw new Error(`ks_answer: engine error HTTP ${probe.status}: ${probe.error || probe.text}`)
      }
      if (probe.status === 0) {
        throw new Error(
          `ks_answer: engine not reachable / timed out (${probe.error || 'no response'}). ` +
            'The engine performs its own LLM inference so it can take >120s; run ks_ping to ' +
            'confirm the engine is up before retrying.',
        )
      }

      const body = probe.body
      const data = body && typeof body === 'object' ? body.data : null
      const trimmed = trimAnswer(data)
      const found = trimmed ? trimmed.evidence.length > 0 : false

      return {
        ok: probe.status === 200,
        httpStatus: probe.status,
        tier: trimmed ? trimmed.tier : null,
        found,
        query,
        query_mode: queryMode,
        evidence: trimmed ? trimmed.evidence : [],
        derivation: trimmed ? trimmed.derivation : '',
        conclusion: trimmed ? trimmed.conclusion : '',
        verification: trimmed ? trimmed.verification : null,
        notes: trimmed ? trimmed.notes : [],
        meta_summary: trimmed ? trimmed.meta_summary : '',
      }
    },
  }
}

/**
 * P1c-RouteA host 路由：GET /ks/session（同源，exact）。
 * 调用既有 EngineManager.ensureLive()（懒拉起/复用，与模型工具同一单实例决策）。
 * 成功 200 → {ok, engine:{port,pid,reused}, token}；失败 503 → {ok:false,error}；非 GET 405。
 * token 只交给同源页面（webserver 默认绑 127.0.0.1），等价旧前端 localStorage 信任模型但不持久化。
 */
function registerKsSessionRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_SESSION_PATH,
    handler: async (req, res) => {
      if (req.method !== undefined && req.method !== 'GET') {
        res.writeHead(405, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'method_not_allowed', message: 'GET only' } }))
        return
      }
      try {
        const session = await manager.ensureLive()
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({
          ok: true,
          engine: { port: session.port, pid: session.pid, reused: !session.spawnedByUs },
          token: session.token, // 同源可信页面，仅内存；绝不交给第三方域
        }))
      } catch (error) {
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({
          ok: false,
          error: {
            code: 'ks_engine_unavailable',
            message: error instanceof Error ? error.message : String(error),
          },
        }))
      }
    },
  })
}

/**
 * P1c-RouteA (OPTIONAL)：pdf.js wasm 解码器资源前缀路由。
 * pdf.js v5 解码 JPX(OpenJPEG)/JBIG2/色彩管理需要 wasmUrl 目录（${dir}openjpeg.wasm 等）。
 * 白名单 = 插件 node_modules/pdfjs-dist/wasm 目录的实际文件名（注册时读一次）。
 */
function registerPdfWasmRoute(ctx) {
  let baseDir = null
  let allow = null
  try {
    const require = createRequire(import.meta.url)
    const pkg = require.resolve('pdfjs-dist/package.json')
    baseDir = join(dirname(pkg), 'wasm')
    allow = new Set(readdirSyncSafe(baseDir))
  } catch {
    baseDir = null
    allow = null
  }
  return ctx.webServer.register({
    kind: 'prefix',
    path: KS_PDF_WASM_PATH,
    handler: async (req, res) => {
      if (baseDir === null || allow === null || allow.size === 0) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable', message: 'pdfjs-dist wasm dir not resolvable' } }))
        return
      }
      let name = ''
      try {
        name = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname).slice(KS_PDF_WASM_PATH.length + 1)
      } catch {
        name = ''
      }
      if (name.length === 0 || name.includes('/') || name.includes('..') || !allow.has(name)) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_not_found', message: `unknown asset: ${name}` } }))
        return
      }
      try {
        const bytes = await readFile(join(baseDir, name))
        const type = name.endsWith('.wasm') ? 'application/wasm' : 'text/javascript; charset=utf-8'
        res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
        res.end(bytes)
      } catch (error) {
        res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_read_failed', message: error instanceof Error ? error.message : String(error) } }))
      }
    },
  })
}

function readdirSyncSafe(dir) {
  return readdir(dir)
}

/**
 * P1c-RouteA (OPTIONAL)：pdf.js worker 资源同源路由。
 * 从插件自身 node_modules 读 pdfjs-dist worker（需 pnpm add pdfjs-dist），
 * 缺失时 404（client 端有备用 Blob 方案）。返回 disposer。
 */
function registerPdfWorkerRoute(ctx) {
  let workerPath = null
  try {
    const require = createRequire(import.meta.url)
    workerPath = require.resolve('pdfjs-dist/build/pdf.worker.min.mjs')
  } catch {
    workerPath = null
  }
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_PDF_WORKER_PATH,
    handler: async (_req, res) => {
      if (workerPath === null) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'worker_unavailable', message: 'pdfjs-dist worker not resolvable' } }))
        return
      }
      try {
        const bytes = await readFile(workerPath)
        res.writeHead(200, { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'no-store' })
        res.end(bytes)
      } catch (error) {
        res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'worker_read_failed', message: error instanceof Error ? error.message : String(error) } }))
      }
    },
  })
}

/**
 * Plugin body.
 * @param ctx  - cordis context (tools provided via `inject`).
 * @param config - optional deployment config (engineRoot / python / timeouts).
 */
export function apply(ctx, config = {}) {
  const opts = {
    engineRoot: config.engineRoot ?? DEFAULTS.engineRoot,
    python: config.python ?? DEFAULTS.python,
    startupTimeoutMs: config.startupTimeoutMs ?? DEFAULTS.startupTimeoutMs,
    idleTimeoutMs: config.idleTimeoutMs ?? DEFAULTS.idleTimeoutMs,
  }
  const manager = new EngineManager(opts)

  // Dispose lifecycle: arm the idle auto-kill and tear down on fiber dispose.
  ctx.effect(() => {
    manager.armIdle()
    return () => {
      void manager.dispose()
    }
  })

  // Registration is effect-based: disposing the fiber unregisters all tools.
  ctx.tools.register(makePingTool(manager))
  ctx.tools.register(makeResolveTool(manager))
  ctx.tools.register(makeAnswerTool(manager))

  // P1c-RouteA: 同源路由（client 半取引擎会话 + pdf.js worker/wasm 资源）。worker/wasm OPTIONAL。
  if (ctx.webServer && typeof ctx.webServer.register === 'function') {
    ctx.effect(() => {
      const disposeSession = registerKsSessionRoute(ctx, manager)
      const disposeWorker = registerPdfWorkerRoute(ctx)
      const disposeWasm = registerPdfWasmRoute(ctx)
      return () => {
        disposeSession()
        disposeWorker()
        disposeWasm()
      }
    })
  } else {
    // 无 webserver 服务（非常规 profile）：跳过路由，不阻断工具注册。
    ctx.logger?.warn?.('ks-dsh-plugin: ctx.webServer 不可用，跳过 /ks/session 路由（client 证据 PDF 将不可用）')
  }
}
