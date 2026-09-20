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
import Schema from '@deepseek-ai/schemastery'
import {
  EngineManager,
  apiGet,
  apiPost,
  combineSignals,
  originUrl,
  HEALTH_PATH,
  KS_ANSWER_PATH,
} from './engine.js'
import { guardWebServer } from './trust.js'
// ks_answer 的纯函数裁剪层。单列模块的理由（可测）+ **白名单纪律**见该文件头。
// 特别地：引擎算出的核验字段只有进了 trimVerification 的白名单才到得了模型眼前。
import { trimVerification } from './trim.js'
// 材料平面只读工具（`ks_materials`）。**只读是纪律**：评审是用户的判断，
// 把"批准/拒绝"开成模型工具等于让模型自己发许可（见 materials.js 头注）。
import { makeMaterialsTool } from './materials.js'
import { makeCollectTool } from './collect.js'
import {
  inspectionStartupCheck,
  registerKsInspectionRoutes,
} from './inspection.js'
import {
  announceStartupCheck,
  registerKsAnnounceRoutes,
} from './announce.js'
import { registerKsReportRoutes } from './report.js'
import { registerKsChannelsRoutes } from './channels.js'
import { registerKsMaterialsRoutes } from './materials_routes.js'
import { registerKsSettingsRoutes } from './settings.js'
import { registerKsDocImageRoutes } from './docimage.js'
import { registerKsIngestRoutes, ingestJobStartupCheck } from './ingest.js'
import { effectiveChatMode, ensureLoaded, hasActiveForensicSessions, makeChatModeSection, registerKsChatModeCommands, registerKsChatModeRoutes } from './chatmode.js'

/** Plugin identity for the cordis.yml row (matches package.json name). */
export const name = 'ks-dsh-plugin'

/**
 * Services required before the plugin mounts.
 *
 * ⚠ **这里只放"硬依赖"**：缺了它整块功能就没有意义的服务。可缺省的一律走 `ctx.get(name)`。
 * 复核（2026-09-19）抓到我把这条只做了一半：`agents`/`commands` 已经在代码里改用
 * `ctx.get(...)` 读取，**却还留在 inject 数组里** —— 后果是"真缺服务"时插件永远 PENDING
 * 且什么都不打印，为它们写的那层兜底**永远够不着**（死代码）。
 * ⇒ 现在真的移出去了：`agents`（查法规模式的子会话继承）与 `commands`（斜杠命令注册）
 * 都走 `ctx.get()`，缺了就在调用点**出声**而不是让整个插件挂起。
 * `webServer` 留在 inject：没有它 `/ks/*` 整面路由不存在，那不是"降级"而是"没有插件"。
 */
export const inject = ['tools', 'webServer', 'systemPrompt']

/**
 * 部署配置的 **schema**（官方要求：`Config` 必须是标准 schema）。
 *
 * 出处：官方文档规范与插件契约一致要求「`Config` 必须是 Standard Schema（Schemastery），
 * **导普通对象不会校验**」—— 而同族的陷阱正是**静默**：写错的配置（例如把毫秒数写成字符串）
 * 会一路流进逻辑，没有一处会报错。官方仓库里每个插件都是 `export const Config: Schema<T> =
 * Schema.object({…})`（例：`packages/acp/acp/src/index.ts`），本地可用的实现是
 * `@deepseek-ai/schemastery`（经 dsh-tools/cordis 传递而来，见 `plugin/node_modules`）。
 *
 * 在此之前本插件**没有 `Config`**：`cordis.patch.yml` 里那 5 个键只在注释里说明，
 * 传错没有任何校验。**默认值的唯一所有者就是这个 schema**（2026-09-19 清理：原先在 `apply` 旁边
 * 还手抄了一份 `DEFAULTS` 字面量，两份已经漂移 —— 现在 `apply` 用 `Config({})` 的解析结果兜底），
 * 所以加上它**不改变行为**，只是把"写错配置"从静默变成当场报错。
 *
 * ⚠ **`engineRoot` / `python` 刻意不给 `.default()`**：它们的"未设置"是有意义的状态
 * （分别代表"用 EngineManager 默认根"、"用 `$KS_PYTHON` 或仓内 .venv"），
 * 给默认值会把"没配"伪装成"配了这个值"。
 * ⚠ **但 `trustedHosts` 是拿不到"未设置"的**（复核 2026-09-19 实测把我原先这句写错了）：
 * `Schema.array(...)` 自带 `default: []` ⇒ 它总是得到 `[]`，不是 `undefined`。
 * 行为上 `[]` 与"没配"等价（`trust.js` 用 `Array.isArray` 判），所以这不是缺陷，
 * **只是那句注释说错了**，已更正（冒烟同时钉住五个键各自的默认值）。
 *
 * ## ⚠ 本 schema **只挡类型错，挡不住键名拼错**（实测，别把这两件事混说）
 * 官方仓库的插件确实写 `}).strict()`，但**那来自 zod**（他们用 `z.object({...})` 定义 Config），
 * **不是** schemastery 的能力。我们这份 `@deepseek-ai/schemastery` 3.18.2（宿主 `vendor/`
 * 与我们同一个版本）**没有 `.strict()`**（加上去 ⇒ `TypeError: ... .strict is not a function`，
 * 插件**加载即失败**）；`.loose(false)` 也**照旧保留未知键**（实测 `{typo:2}` 原样通过）。
 * ⇒ 所以"未知键"这件事改由 `apply` 里的显式检查兜住（见 `apply` 开头），
 * 这样类型错与键名错**都能当场报错**，而不是只有一半。
 * （另一条路是改用 zod 的 `.strict()` 让 Loader 自己拒 —— 那要依赖 zod 并验证宿主 cordis
 * 接受 zod schema，**本轮没做**，登记在 [适配审计](docs/DSH-ALIGNMENT-AUDIT.md) 的积压里。）
 *
 * 验证过（本地实测）：`{idleTimeoutMs:'soon'}` ⇒ `$.idleTimeoutMs expected number but got soon`；
 * `{trustedHosts:'1.2.3.4'}` ⇒ `$.trustedHosts expected array but got 1.2.3.4`；
 * `{}` ⇒ **只有带默认值的三个键出现在解析结果里**（`startupTimeoutMs` / `idleTimeoutMs` /
 * `trustedHosts=[]`），`engineRoot`/`python` **整个缺席**（不是 undefined 值 —— 实测
 * `Object.keys(config)` 只有那三个键）。
 */
export const Config = Schema.object({
  engineRoot: Schema.string().description('引擎仓库根目录；不填则用 EngineManager 的默认（本插件所在仓）'),
  python: Schema.string().description('Python 解释器路径；不填则用 $KS_PYTHON 或仓内 .venv'),
  startupTimeoutMs: Schema.number().default(60_000)
    .description('引擎启动超时（毫秒）'),
  idleTimeoutMs: Schema.number().default(30 * 60 * 1000)
    .description('引擎空闲回收窗口（毫秒）；默认 30 分钟'),
  trustedHosts: Schema.array(Schema.string())
    .description('额外可信 authority（局域网部署时声明；默认只认回环 127.0.0.1/localhost/::1）'),
})

/**
 * `Config` 声明的键名（**唯一所有者**：`apply` 的未知键检查与文档都从这里取）。
 * 有了它，"配置里写了个不存在的键"会**当场报错**——见 `Config` 的注释说明
 * （本地 schemastery 版本挡不住这件事）。
 */
export const CONFIG_KEYS = ['engineRoot', 'python', 'startupTimeoutMs', 'idleTimeoutMs', 'trustedHosts']

// P1c-RouteA: 同源路由（client 半经此取引擎会话 / pdf.js worker 与 wasm 资源）
export const KS_SESSION_PATH = '/ks/session'
export const KS_PDF_WORKER_PATH = '/ks/assets/pdf.worker.min.mjs'
export const KS_PDF_WASM_PATH = '/ks/assets/pdf-wasm'
export const KS_BBOX_PATH = '/ks/bbox'
// 端点接线（2026-09-13）：文档图片同源代理前缀由 docimage.js 自持
// （KS_DOC_IMAGE_PATH），client 硬编码同值（api.ts fetchDocImage）——
// 跨半共享常量经 bundle 会翻倍依赖面，保持每半各自声明。

// P1c-RouteA 增强①（编排拼锚点）：证据伪源锚点基址。URL 契约与 client 半
// client/ksEvidence.ts 完全一致：http(s) + pathname /__ks_evidence__ + 非空 doc
// → better-sidebar 认领并开 ks:pdf tab（不导航）。伪源 host 不可达（port 1），
// 点击由链接拦截接管。bbox 参数暂不拼（决策：bbox 黄框推迟到收藏跳转一起做）。
export const KS_EVIDENCE_PATH = '/__ks_evidence__'
export const KS_EVIDENCE_ORIGIN = 'http://127.0.0.1:1'

/** 拼一条证据锚点 URL（供编排把 ks_answer 证据变成可点 PDF 链接）。
 * @param {{doc_id?:unknown, page_start?:unknown, clause_revision_id?:unknown}} ev
 * @returns {string|null} doc 缺失/非法 → null（宁缺毋滥：无 doc 的链接点开也没用）。
 */
export function evidenceAnchor(ev) {
  if (!ev || typeof ev !== 'object') return null
  const doc = typeof ev.doc_id === 'string' && ev.doc_id.length > 0 ? ev.doc_id : null
  if (doc === null) return null
  const qs = new URLSearchParams()
  qs.set('doc', doc)
  const page = typeof ev.page_start === 'number' && Number.isFinite(ev.page_start)
    && ev.page_start >= 1 ? Math.floor(ev.page_start) : null
  if (page !== null) qs.set('page', String(page))
  const rev = typeof ev.clause_revision_id === 'string' && ev.clause_revision_id.length > 0
    ? ev.clause_revision_id : null
  if (rev !== null) qs.set('rev', rev)
  return `${KS_EVIDENCE_ORIGIN}${KS_EVIDENCE_PATH}?${qs.toString()}`
}

//: `apply` 在 config 省略某键时的兜底 —— **默认值的唯一所有者是 `Config` schema 本身**
//: （解析 `{}` 得到的就是带默认值的那几个键）。**别再手抄一份字面量**：
//: 2026-09-19 清理前这里与 schema 是两份（改一处漏一处）；而且手抄那份把 `trustedHosts`
//: 写成 `undefined`，schema 的 `Schema.array(...)` 却自带 `default: []` —— 两份**已经不一致**
//: （下游 `trust.js` 用 `Array.isArray` 判，行为等价，但这正是"双份默认值"的典型症状）。
//: ⚠ 没默认值的两个键（`engineRoot`/`python`）在解析结果里**缺席** ⇒ 这里取到 `undefined`，
//: 与"未设置"同义（分别回落到 EngineManager 默认根 / `$KS_PYTHON` 或仓内 venv）。
const CONFIG_DEFAULTS = Config({})

// ---------------------------------------------------------------------------
// ks_answer helpers (P1b — trim the engine answer for the model's prompt)
// ---------------------------------------------------------------------------

/** Legal `query_mode` values (engine contract: R9 four-tier). */
const QUERY_MODES = ['default', 'thorough', 'quick', 'guess']

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
  // folder_id（2026-10 收藏目录）：形态校验同 chatmode 的 normalizeFolderId——
  // 非空、无空白、≤64 字符。host 强制值永远覆盖模型自传值（见 makeAnswerTool）。
  if (typeof raw.folder_id === 'string' && raw.folder_id.length > 0 && raw.folder_id.length <= 64
      && !/[\s\u0000-\u001f]/.test(raw.folder_id)) {
    out.folder_id = raw.folder_id
  }
  // material_project_id（2026-09-17 材料平面）：**必须在这里**，否则本白名单会静默丢弃它，
  // 而工具 schema 却向模型承诺了这个参数 —— 那正是本战役反复打的"算出来没人看得见"的
  // **输入端**版本（独立复核 2026-09-17 实测：sanitizeParams({material_project_id}) === null，
  // 即整条材料链在插件这一层是死的、且不报错）。
  // 形态校验与 chatmode 的 normalizeMaterialProjectId 同口径；`prj_` 前缀在这里**不强制**
  // （前缀的权威判定在引擎的仓库层与 chatmode 的会话绑定处，这里只做"不像 id 就丢"）。
  // host 强制值永远覆盖模型自传值（见 makeAnswerTool）。
  if (typeof raw.material_project_id === 'string' && raw.material_project_id.length > 0
      && raw.material_project_id.length <= 64
      && !/[\s\u0000-\u001f]/.test(raw.material_project_id)) {
    out.material_project_id = raw.material_project_id
  }
  if (raw.max_evidence !== undefined) {
    const m = Number(raw.max_evidence)
    if (Number.isFinite(m) && m > 0) out.max_evidence = Math.min(Math.floor(m), EVIDENCE_CAP)
  }
  return Object.keys(out).length > 0 ? out : null
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
    // P1c 增强①：可直接粘成 Markdown 链接的证据锚点（doc+page+rev，无 bbox）。
    // 模型把答案里对该证据的引用写成 [依据](evidence_url) 即得可点 PDF 跳转。
    evidence_url: evidenceAnchor(ev),
    // verifier 四轮 P1：这里**绝不能造字段**。引擎的 evidence 只有在真给了布尔时才透出
    // 该值；字段缺失（旧引擎/异常路径）必须是 null，而不是强转出来的 false——否则
    // "answer_scope.bookmarks_only=true + evidence[].bookmarked=false" 会让模型每次
    // 都误报"范围过滤未生效"（把 host 的转换 bug 变成模型的事实性虚假陈述）。
    bookmarked: typeof ev.bookmarked === 'boolean' ? ev.bookmarked : null,
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
 *
 * ⚠ **白名单纪律（与 `trimVerification` 同一条）**：引擎 `answer()` 返回的键若没进
 * 本函数，就等于没算——`unsupported_context` 与 `material_usage` 都栽过/差点栽在这里。
 * 导出它是为了让 `scripts/smoke-trim.mjs` 能**调用真函数**逐键核对（不是字符串匹配）。
 */
export function trimAnswer(data) {
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
    // 材料平面使用记录（引擎侧 Phase B）。**必须转发**：模型要能如实说出
    // "本次用了哪个项目的哪几条参考资料、哪些只算线索"，否则又是一个"算出来没人看得见"。
    // 没给项目范围时引擎给 null —— "没用材料"与"用了但没命中"必须能区分。
    material_usage: data.material_usage ?? null,
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

/* ------------------------------------------------------------------ *
 * 第 6 步 §1：`output.schema` 的"可空 / 引擎自带块"形状（一份定义，四处 schema 共用）
 *
 * 两条**实测**硬约束（`docs/research/STEP6-WORKORDER.md` §1 的【实测】表）：
 *   ① 可空**不能**写 `type:['string','null']` —— register 期直接被拒
 *      （`schema.type must be a single type string`），取值期还会 THROW；
 *      只能用 `oneOf:[{type:'<T>'},{type:'null'}]`。
 *   ② `additionalProperties:false` 时，**条件性出现的键也必须列进 `properties`**：
 *      它出现的那一次就是 `"value.x" is not a declared property`。
 *
 * 为什么 schema 要精确到这一步（这是 6 条里唯一有真实回归风险的）：宿主**注册期**
 * `assertSupportedJsonSchema(output.schema)`（(DSH) `packages/core/tools/src/index.ts:1062`）
 * 不通过 ⇒ 抛错 ⇒ **整个插件挂不上**；**取值期** `validateJsonSchemaValue`
 * （同文件 `:1813-1816`）不通过 ⇒ **每次调用都 isError**。故 schema 只能描述**真实**形状，
 * **严禁**为了过门禁回退成 `additionalProperties:true` 或裁掉返回字段。
 * ------------------------------------------------------------------ */
/** 可空标量：null 是**有意义的值**（"引擎没给"），不是缺字段。 */
const NULLABLE_STRING = { oneOf: [{ type: 'string' }, { type: 'null' }] }
const NULLABLE_NUMBER = { oneOf: [{ type: 'number' }, { type: 'null' }] }
const NULLABLE_BOOLEAN = { oneOf: [{ type: 'boolean' }, { type: 'null' }] }
/** 引擎自带的 JSON 块（命中体 / 四色计数 / 原始信封）：形状不归本仓定义，故只钉"是对象"。 */
const NULLABLE_OBJECT = { oneOf: [{ type: 'object' }, { type: 'null' }] }

/** `ks_effect_report` 的红/黄清单（`makeEffectReportTool` 的 `out.red_list`/`out.yellow_list` 同形）。 */
const EFFECT_COLOR_LIST = {
  type: 'object',
  additionalProperties: false,
  properties: {
    count: { type: 'number' },
    docs: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          doc_id: NULLABLE_STRING,
          standard_no: NULLABLE_STRING,
          standard_name: NULLABLE_STRING,
          status: NULLABLE_STRING,
          effective_from: NULLABLE_STRING,
          superseded_by: NULLABLE_STRING,
          withdrawn_date: NULLABLE_STRING,
          evidence_url: NULLABLE_STRING,
        },
        required: ['doc_id', 'standard_no', 'standard_name', 'status',
          'effective_from', 'superseded_by', 'withdrawn_date', 'evidence_url'],
      },
    },
  },
  required: ['count', 'docs'],
}

/** `ks_answer` 的证据条目（`trimEvidence` 的形状，搜 `function trimEvidence`）。 */
const ANSWER_EVIDENCE = {
  type: 'object',
  additionalProperties: false,
  properties: {
    standard_no: NULLABLE_STRING,
    clause_number: NULLABLE_STRING,
    title: NULLABLE_STRING,
    legal_status: NULLABLE_STRING,
    legal_hierarchy: NULLABLE_STRING,
    page_start: NULLABLE_NUMBER,
    snippet: NULLABLE_STRING,
    doc_id: NULLABLE_STRING,
    clause_revision_id: NULLABLE_STRING,
    evidence_url: NULLABLE_STRING,
    bookmarked: NULLABLE_BOOLEAN,
  },
  required: ['standard_no', 'clause_number', 'title', 'legal_status', 'legal_hierarchy',
    'page_start', 'snippet', 'doc_id', 'clause_revision_id', 'evidence_url', 'bookmarked'],
}

/** `ks_answer` 的核验块（`trimVerification` 的形状，`src/trim.js` 的 `export function trimVerification`）。 */
const ANSWER_VERIFY_LIST = {
  type: 'array',
  items: { oneOf: [{ type: 'string' }, { type: 'number' }, { type: 'boolean' }, { type: 'null' }] },
}
const ANSWER_VERIFICATION = {
  type: 'object',
  additionalProperties: false,
  properties: {
    is_valid: { type: 'boolean' },
    answer_confidence: { type: 'string' },
    confidence_reasons: ANSWER_VERIFY_LIST,
    unsupported_clauses: ANSWER_VERIFY_LIST,
    unsupported_context: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          clause_number: NULLABLE_STRING,
          standard_no: NULLABLE_STRING,
          verdict: NULLABLE_STRING,
          reason: NULLABLE_STRING,
        },
        required: ['clause_number', 'standard_no', 'verdict', 'reason'],
      },
    },
    unverified_numbers: ANSWER_VERIFY_LIST,
    modality_violations: ANSWER_VERIFY_LIST,
    legal_element_violations: ANSWER_VERIFY_LIST,
    citation_index_warnings: ANSWER_VERIFY_LIST,
  },
  required: ['is_valid', 'answer_confidence', 'confidence_reasons', 'unsupported_clauses',
    'unsupported_context', 'unverified_numbers', 'modality_violations',
    'legal_element_violations', 'citation_index_warnings'],
}

/** `ks_answer` 的 `answer_scope` 回显块（搜 `const scope = {`）——**只有**正常路径有它。 */
const ANSWER_SCOPE = {
  type: 'object',
  additionalProperties: false,
  properties: {
    forensic: { type: 'boolean' },
    bookmarks_only: { type: 'boolean' },
    folder: { type: 'boolean' },
    folder_id: NULLABLE_STRING,
    folder_name: NULLABLE_STRING,
    material: { type: 'boolean' },
    material_project_id: NULLABLE_STRING,
    material_project_name: NULLABLE_STRING,
    source: { type: 'string', enum: ['session', 'parent', 'none'] },
  },
  required: ['forensic', 'bookmarks_only', 'folder', 'folder_id', 'folder_name',
    'material', 'material_project_id', 'material_project_name', 'source'],
}

/**
 * `material_usage`（材料平面使用记录，引擎侧算、本工具**必须转发**）——
 * ⚠ 2026-09-20（第 6 步 §1 顺带抓到、本批修）：这个键**算出来了却没进返回值**
 * （`trimAnswer` 里有、`execute` 的 `return` 漏抄），而 `params.material_project_id.description`
 * 明写 "The result carries material_usage" ⇒ **工具对自己的承诺不成立**。
 * 形状逐字段抄引擎（`src/core/llm/ks_answer.py:685-701` 两条分支的并集）：
 *   正常：`{project_id, project_found, counts, notes, usable_indices}`
 *   失败：`{project_id, counts: null, notes: [], usable_indices: [], error}`
 * ⇒ 共有的 4 键进 `required`，`project_found`（只正常分支）与 `error`（只失败分支）只列不 required；
 * `counts` 是**引擎自有的字典**（键随 `assemble_evidence` 变），这里按"**可空的开放 object**"声明，
 * 不替引擎做主，也**不**假装它是我们定的形状。
 *
 * ⚠⚠ **2026-09-20 就地更正（复核 `verify-freeze-step6-1` 打回 A，这是我的错）**：上面那段注释里我自己
 * 写着失败分支是 `counts: null`，而下面第 474 行却写成 `counts: {type:'object'}` **且放进 `required`**
 * —— **抄漏了那一支的可空性**。后果不是"少个校验"，而是**真机 isError**：复核用**真
 * `@deepseek-ai/dsh-tools` 的 `ToolRuntime.execute`** 实测（引擎失败分支的 payload）⇒
 * `isError:true`、`ToolOutputError`、`INVALID_TOOL_OUTPUT`「"value.material_usage" must match exactly
 * one oneOf branch (matched 0)」；父提交那 6 处都是 `additionalProperties:true` 且当时**根本没转发**
 * `material_usage` ⇒ **这条 isError 是我这一批新引入的**。
 * 漏网原因：17 组冒烟里 `ks_answer` 只有正常分支（`full-answer`）/422/空信封，**没有引擎失败分支那一组**
 * —— ⇒ 已补一组 `material-usage-engine-error`（`counts:null` + `error`），并把它钉进 required 的语义：
 * `counts` 要在（**可以**是 null），而不是"必须在"。
 */
const ANSWER_MATERIAL_USAGE = {
  oneOf: [
    {
      type: 'object',
      additionalProperties: false,
      properties: {
        project_id: { type: 'string' },
        project_found: { type: 'boolean' },
        counts: { oneOf: [{ type: 'object' }, { type: 'null' }] },
        notes: { type: 'array', items: { type: 'string' } },
        usable_indices: { type: 'array', items: { type: 'integer' } },
        error: { type: 'string' },
      },
      required: ['project_id', 'counts', 'notes', 'usable_indices'],
    },
    { type: 'null' },
  ],
}

/**
 * Build the `ks_effect_report` tool definition (P1, 2026-09-08).
 *
 * 会话内效力报告：库内标准/法规的现行快照总览。host 侧裁剪——只回统计、
 * 两树前 3 类目与红/黄清单 top-N（≤20），**绝不回传全量分类树**（万级库
 * payload 红线，见 effect_report.py 模块头）；完整清单与 Excel 导出引导到
 * 「📋 效力报告」标签页。只读聚合，零 LLM 消耗。
 */
/** 导出供 `scripts/smoke-wire-contract.mjs` 直接驱动（第 6 步 §5 wire fixture 回放）。 */
export function makeEffectReportTool(manager) {
  return {
    name: 'ks_effect_report',
    description:
      '库内标准/法规的效力现状总览（效力报告）：四色统计（🔴在用已废止/被替代 · 🟡即将实施 · ' +
      '🟢现行有效 · ⚪状态未知）、标准树与法规树分计、各树主要分类，以及红色/黄色清单（各 top 10，' +
      '每行含 standard_no/名称/实施日期/被代替为/废止日期/doc_id/evidence_url）。当用户问' +
      '"库里标准还有效吗/有没有已废止的/哪些标准即将实施/效力报告"时调用。' +
      '若返回里出现非空 attention_error，表示红/黄清单这次没取到（统计数字仍然有效），' +
      '别把它当成"库里没有废止文件"。' +
      '若要在回答里列出某条已废止标准，请把它的 evidence_url 写成 Markdown 链接，用户点开即看原 PDF。' +
      '完整分类清单与 Excel 导出在「📋 效力报告」标签页。只读，零 LLM。',
    parameters: {
      type: 'object',
      properties: {
        include_attention: {
          type: 'boolean',
          description: '是否附红/黄清单（默认 true）。只想要统计数字时传 false。',
        },
        limit: {
          type: 'integer',
          description: '红/黄清单每色条数（默认 10，上限 20）。',
        },
      },
      additionalProperties: false,
      description: '可选：include_attention / limit。',
    },
    output: {
      // 第 6 步 §1：精确形状 —— 逐字段抄 `execute` 的 `const out = {...}`（本文件，搜
      // `const out = {` 下面那个字面量）＋ 三处条件增补（`out.window` / `out.attention_error`
      // / `out.red_list`+`out.yellow_list`，都搜得到）。那 4 个**条件性出现**的键也必须列进
      // `properties`：`additionalProperties:false` 下没列的键一旦出现就是违规。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          generated_at: NULLABLE_STRING,
          total: { type: 'number' },
          colors: {
            type: 'object',
            additionalProperties: false,
            properties: {
              red: { type: 'number' },
              yellow: { type: 'number' },
              green: { type: 'number' },
              gray: { type: 'number' },
            },
            required: ['red', 'yellow', 'green', 'gray'],
          },
          std_total: { type: 'number' },
          law_total: { type: 'number' },
          trees: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              properties: {
                top: NULLABLE_STRING,
                name: NULLABLE_STRING,
                colors: NULLABLE_OBJECT,
                categories: {
                  type: 'array',
                  items: {
                    type: 'object',
                    additionalProperties: false,
                    properties: { name: NULLABLE_STRING, colors: NULLABLE_OBJECT },
                    required: ['name', 'colors'],
                  },
                },
              },
              required: ['top', 'name', 'colors', 'categories'],
            },
          },
          // 以下 4 个键**只在特定分支出现**（非默认窗口 / 清单失败 / 清单成功），故不 required。
          window: { type: 'string' },
          attention_error: { type: 'string' },
          red_list: EFFECT_COLOR_LIST,
          yellow_list: EFFECT_COLOR_LIST,
        },
        required: ['ok', 'generated_at', 'total', 'colors', 'std_total', 'law_total', 'trees'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    // verifier F3：summary + 红黄清单共 2 次引擎调用，每次内层 15s 上限 →
    // 外层必须 > 2×15s，否则内层还没超时外层先被杀，报错信息误导。
    timeoutMs: 90_000,
    // 第 6 步 §3：**可并行**。官方契约（(DSH) `docs/subsystems/tools.md:66-70`）问的是
    // "会不会动父级状态"，不是"快不快"：本工具只有 2 次只读 GET，全部落点都是 `out`（局部），
    // 不碰任何模块级可变状态；引擎侧 `/report/effect*` 是纯聚合读。
    isConcurrencySafe: () => true,
    async execute(args, exec) {
      // verifier P1-2：外层 90s 必须装得下 ensureLive（冷启动最长 60s）+ 2 次内层
      // 调用，而 401 自愈会再调一次 ensureLive（最坏 60+15+60+15=150s > 90s，仍会
      // 被 DSH 硬杀成"tool call timed out"）。所以内部设 80s 总 deadline 并传给
      // 每一次 await——超时由我们自己明确报错，不再命中 DSH 的通用超时。
      const deadline = AbortSignal.timeout(80_000)
      // 第 6 步 §4B-1：`combineSignals` 返回 `{ signal, dispose }`（不再是裸 signal）。
      // 它往 `exec.signal` 上加了一个 abort 监听，**必须**由本调用方在结束时摘掉——
      // 旧实现返回裸 signal，于是那个监听直到 exec.signal 被 GC 才消失（实测 added=1/removed=0，
      // 见 `plugin/scripts/smoke-cancel.mjs` 的 D1）。
      const fused = combineSignals(exec.signal, deadline)
      const signal = fused.signal
      try {
        const session = await manager.ensureLive(signal)
        // verifier F14：引擎重启会轮换 port/token → 401 时重读会话重试一次
        let current = session
        const get = async (path) => {
          const call = (sess) => apiGet(originUrl(sess.port), path, {
            token: sess.token, signal, timeoutMs: 15_000,
          })
          let probe = await call(current)
          if (probe.status === 401) {
            const fresh = await manager.ensureLive(signal)
            if (fresh && (fresh.port !== current.port || fresh.token !== current.token)) {
              current = fresh
              probe = await call(current)
            }
          }
          if (probe.status === 401) {
            throw new Error('ks_effect_report: 引擎拒绝 Bearer token(401)，重读会话后仍失败')
          }
          if (probe.status === 0 && deadline.aborted) {
            throw new Error(
              'ks_effect_report: 引擎响应超时（内部 80s deadline 到点）。'
              + '请先 ks_ping 确认引擎状态后重试。')
          }
          return probe
        }
        const summary = await get('/api/v1/report/effect')
        // verifier F5：200 但信封缺失/无 data（反代、旧版引擎、非 JSON）绝不
        // 伪装成"全 0 报告"——那会让模型断言库里没有废止文件（P1 准确性）。
        const env = summary.status === 200 && summary.body && typeof summary.body === 'object'
          ? summary.body : null
        if (!env || env.code !== 200 || !env.data || typeof env.data !== 'object') {
          throw new Error(
            'ks_effect_report: /api/v1/report/effect 响应异常 '
            + `HTTP ${summary.status || 'no-response'} ${summary.error || ''} `
            + '(期望 {code:200,data:{...}})。请先 ks_ping 确认引擎版本。')
        }
        const d = env.data
        const colors = d.colors && typeof d.colors === 'object' ? d.colors : {}
        const out = {
          ok: true,
          generated_at: d.generated_at ?? null,
          total: d.total ?? 0,
          colors: {
            red: colors.red ?? 0, yellow: colors.yellow ?? 0,
            green: colors.green ?? 0, gray: colors.gray ?? 0,
          },
          std_total: d.std?.total ?? 0,
          law_total: d.law?.total ?? 0,
          trees: Array.isArray(d.tree) ? d.tree.map((t) => ({
            top: t.top ?? null,
            name: t.name ?? null,
            colors: t.colors ?? null,
            categories: Array.isArray(t.items)
              ? t.items.slice(0, 3).map((l2) => ({ name: l2.name ?? null, colors: l2.colors ?? null }))
              : [],
          })) : [],
        }
        // verifier F16：window 恒为 "all"（本工具不暴露窗口参数）→ 只在非默认时回传
        if (typeof d.window === 'string' && d.window !== 'all') out.window = d.window
        if (args?.include_attention !== false) {
          const n = Math.max(1, Math.min(Number(args?.limit) || 10, 20))
          // verifier F4：红+黄一次聚合（per_color=1 → 每色各取 n 条，
          // 而非全局 top-n 被红色吃满），省掉一次全量聚合。
          const probe = await get(
            `/api/v1/report/effect/color?color=red,yellow&per_color=1&limit=${n}`)
          const data = probe.status === 200 && probe.body && probe.body.code === 200
            ? probe.body.data : null
          if (!data || !Array.isArray(data.docs)) {
            // verifier F6：清单失败要显式告诉模型"清单没拿到"，不能静默 null
            const why = probe.error || (probe.body && probe.body.message) || ''
            out.attention_error =
              `红/黄清单获取失败: HTTP ${probe.status || 'no-response'} ${why}`.trim()
          } else {
            const buckets = { red: [], yellow: [] }
            for (const x of data.docs) {
              const bucket = buckets[x.color]
              if (!bucket) continue
              bucket.push({
                doc_id: x.doc_id ?? null,
                standard_no: x.standard_no ?? null,
                standard_name: x.standard_name ?? null,
                status: x.status ?? null,
                effective_from: x.effective_from ?? null,
                superseded_by: x.superseded_by ?? null,
                withdrawn_date: x.withdrawn_date ?? null,
                // verifier F18：给可点 PDF 锚点，模型据此写出可点链接
                evidence_url: evidenceAnchor(x),
              })
            }
            const totalOf = (c) => (colors[c] ?? data.colors?.[c] ?? buckets[c].length)
            out.red_list = { count: totalOf('red'), docs: buckets.red.slice(0, n) }
            out.yellow_list = { count: totalOf('yellow'), docs: buckets.yellow.slice(0, n) }
          }
        }
        return out
      } finally {
        // 异常路径也要摘（throw 在 `get` 里很常见：401/信封坏）。
        fused.dispose()
      }
    },
  }
}

/** 导出供 `scripts/smoke-wire-contract.mjs` 直接驱动（第 6 步 §5 wire fixture 回放）。 */
export function makePingTool(manager) {
  return {
    name: 'ks_ping',
    description:
      'Probe the local KnowledgeStation engine. Returns the live engine session ' +
      '(port, pid, reused) and the /api/v1/health payload (status, uptime, db_status, vector_engine, parser_worker). ' +
      'vector_engine is CHEAP tri-state and is NOT a load test: "ok" = this process really loaded the ' +
      'vector model at least once, "offline" = the last load attempt failed, "unknown" = never attempted ' +
      '(the engine deliberately does NOT load the model just to answer a health check). ' +
      'Use it to confirm the engine is up before querying clauses.',
    parameters: {
      type: 'object',
      properties: {},
      additionalProperties: false,
      description: 'No arguments.',
    },
    output: {
      // 第 6 步 §1：逐字段抄 `execute` 的 `return {...}`（搜 `uptimeSeconds`）。
      // `/api/v1/health` 是**扁平 JSON**（无信封），可空字段全是 `body?.x ?? null`。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          httpStatus: { type: 'number' },
          engine: {
            type: 'object',
            additionalProperties: false,
            properties: {
              port: { type: 'number' },
              pid: { type: 'number' },
              reused: { type: 'boolean' },
            },
            required: ['port', 'pid', 'reused'],
          },
          status: NULLABLE_STRING,
          uptimeSeconds: NULLABLE_NUMBER,
          dbStatus: NULLABLE_STRING,
          vectorEngine: NULLABLE_STRING,
          parserWorker: NULLABLE_STRING,
        },
        required: ['ok', 'httpStatus', 'engine', 'status', 'uptimeSeconds',
          'dbStatus', 'vectorEngine', 'parserWorker'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 20_000,
    // 第 6 步 §3：**可并行**。只读：`ensureLive` + `GET /health`，落点全是局部对象；
    // 唯一共享的是 `EngineManager`，而它的并发入口 `ensureLive` 已在本步 §4B-3 改成
    // "共享一段工作、各自取消各自"（内部 signal），并发调用**不再互相连坐**。
    isConcurrencySafe: () => true,
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

/**
 * Build the `ks_resolve_clause` tool definition.
 *
 * 导出供 `scripts/smoke-wire-contract.mjs` 直接驱动（第 6 步 §5 wire fixture 回放）。
 */
export function makeResolveTool(manager, chatModeOf) {
  return {
    name: 'ks_resolve_clause',
    description:
      'Resolve a "standard_no + clause_number" citation against the local KnowledgeStation ' +
      'library. Returns the machine evidence the engine found (matched clause ids, titles, ' +
      'text) or an explicit not-found marker. Args are URL-encoded by the tool. ' +
      'The hit carries legal_status, an evidence_url (clickable PDF anchor) and bookmarked; ' +
      'when 查法规模式 is on, a hit outside the user\'s bookmark collection reports ' +
      'bookmarks_scope:"outside" and must only be used for locating, never as a 依据. ' +
      'When 在本收藏夹内提问 is active, a hit outside the folder likewise reports ' +
      'folder_scope:"outside" with the same locating-only ban.',
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
      // 第 6 步 §1：逐字段抄 `execute` 的 `return {...}`（搜 `envelope: body`）。三个键
      // （`scope_notice`/`folder_name`/`folder_notice`）**只在特定范围标记下展开**，故不 required。
      // `data` 直接来自引擎 `body.data`：`isEmpty` 自己判了 `Array.isArray(data)` ⇒ 它可能是
      // **数组**（查无此条时引擎可能给 `[]`），所以类型是 object|array|null，不是 object|null。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          standard_no: { type: 'string' },
          clause_number: { type: 'string' },
          httpStatus: { type: 'number' },
          ok: { type: 'boolean' },
          found: { type: 'boolean' },
          data: { oneOf: [{ type: 'object' }, { type: 'array' }, { type: 'null' }] },
          evidence_url: NULLABLE_STRING,
          bookmarked: NULLABLE_BOOLEAN,
          legal_status: NULLABLE_STRING,
          bookmarks_scope: {
            oneOf: [{ type: 'string', enum: ['inside', 'outside'] }, { type: 'null' }],
          },
          scope_notice: { type: 'string' },
          folder_scope: {
            oneOf: [{ type: 'string', enum: ['inside', 'outside', 'unknown'] }, { type: 'null' }],
          },
          folder_name: NULLABLE_STRING,
          folder_notice: { type: 'string' },
          // 原始信封（`body`）——排障要能看到引擎到底回了什么，故原样带出。
          envelope: NULLABLE_OBJECT,
        },
        required: ['standard_no', 'clause_number', 'httpStatus', 'ok', 'found', 'data',
          'evidence_url', 'bookmarked', 'legal_status', 'bookmarks_scope', 'folder_scope', 'envelope'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 25_000,
    // 第 6 步 §3：**可并行**。只读 GET；`:573-590` 只做参数拼接、读 chatmode（
    // `effectiveChatMode` 是**同步**纯读 + 读穿缓存，无 await 间隙 ⇒ 事件循环里原子）
    // 与拼一个局部返回体。不写任何父级状态。
    isConcurrencySafe: () => true,
    async execute(args, exec) {
      const standardNo = String((args && args.standard_no) ?? '').trim()
      const clauseNumber = String((args && args.clause_number) ?? '').trim()
      if (!standardNo) throw new Error('ks_resolve_clause: "standard_no" is required and must be a non-empty string')
      if (!clauseNumber) throw new Error('ks_resolve_clause: "clause_number" is required and must be a non-empty string')

      // 收藏夹内提问（2026-10）：夹范围激活时把 folder_id 带给引擎，让引擎对命中体
      // 打夹范围标记（inside/outside）——host 据此对夹外条款打明文禁令（与
      // bookmarks_scope 同款不抛错设计：resolve 是定位工具，抛错会让模型误判"查无"）。
      const chatMode0 = chatModeOf(exec)
      const folderActive = typeof chatMode0.folderId === 'string' && chatMode0.folderId.length > 0

      const session = await manager.ensureLive(exec.signal)
      const path =
        `/api/v1/clauses/resolve?standard_no=${encodeURIComponent(standardNo)}` +
        `&clause_number=${encodeURIComponent(clauseNumber)}` +
        (folderActive ? `&folder_id=${encodeURIComponent(chatMode0.folderId)}` : '')
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
      // 「仅收藏」也要覆盖这条定位路径（verifier 二轮 P1：只圈 ks_answer 时，模型
      // 用 resolve 就能拿到库内任意条款并写进依据区）。这里**不抛错**——resolve 是
      // 定位工具，抛错会让模型误判"查无"，而是打标 + 给出明文禁令。
      // 收藏夹范围（2026-10）同款：folder_scope 引擎标记 + 夹外禁令。
      const hit = data && typeof data === 'object' && !Array.isArray(data) ? data : null
      const chatMode = chatModeOf(exec)
      const bookmarked = hit?.bookmarked === true
      const outsideScope = chatMode.bookmarksOnly && hit !== null && !bookmarked
      // 夹范围真值：引擎侧 inside/outside（夹不存在时引擎回 null → 如实透出 unknown）
      const engineFolderScope = hit?.folder_scope === 'inside' ? 'inside'
        : hit?.folder_scope === 'outside' ? 'outside' : null
      const folderKnown = folderActive && engineFolderScope !== null
      const outsideFolder = folderActive && engineFolderScope === 'outside'
      return {
        standard_no: standardNo,
        clause_number: clauseNumber,
        httpStatus: probe.status,
        ok: probe.status === 200,
        found: !isEmpty,
        // verifier P1-4：引擎 404 体没有 data 键 → `body.data` 是 undefined，
        // DSH 的 lossless 校验会整条工具输出判 INVALID_TOOL_OUTPUT。必须兜 null。
        data: data ?? null,
        // 命中体自带 doc_id/page_start/clause_revision_id（引擎 _ev_dict）→ 直接给可点链接，
        // 免得模型自己拼 PDF 锚点（拼出来是坏链接，落在"证据必须能点开原件"的信任面上）。
        evidence_url: hit === null ? null : evidenceAnchor(hit),
        bookmarked: hit === null ? null : bookmarked,
        legal_status: hit?.legal_status ?? null,
        // verifier 三轮 P2：查无此条（found:false，hit=null）时**不能**回 "inside"——
        // 那等于对一条根本不存在的条款断言"它在你的收藏集内"。没命中就没有范围可谈。
        bookmarks_scope: chatMode.bookmarksOnly === true && hit !== null
          ? (outsideScope ? 'outside' : 'inside')
          : null,
        ...(outsideScope
          ? {
            scope_notice:
              '该条款不在用户收藏集内：本轮「仅收藏」已开启，它**只能用于定位/核对条款号**，'
              + '不得写入依据区，也不得作为结论依据。',
          }
          : {}),
        // 夹范围标记（2026-10）：inside=夹内；outside=夹外（禁令见 folder_notice）；
        // unknown=夹范围激活但引擎未给判定（旧引擎/查询失败——不得据此断言在夹内）；
        // null=夹范围未激活。真值来自引擎（doc_ids ∪ clause_keys），不是 host 猜的。
        folder_scope: folderActive
          ? (engineFolderScope ?? 'unknown')
          : null,
        ...(folderKnown ? { folder_name: chatMode.folderName ?? hit?.folder_name ?? null } : {}),
        ...(outsideFolder
          ? {
            folder_notice:
              `该条款不在收藏夹「${chatMode.folderName ?? chatMode.folderId}」内：本轮「在本收藏夹内提问」已开启，`
              + '它**只能用于定位/核对条款号**，不得写入依据区，也不得作为结论依据。',
          }
          : {}),
        envelope: body,
      }
    },
  }
}

/**
 * Build the `ks_answer` tool definition (P1b forensic-answer).
 *
 * 导出它是为了**可测**：`scripts/smoke-materials-tool.mjs` 用桩引擎直接驱动本工具，
 * 断言"会话级范围（收藏夹 / 参考资料项目）确实被 host 强制写进了请求体"——
 * 这条链是"用户以为在用公司制度、其实没用"最容易静默失效的地方，不能只靠读代码相信。
 */
export function makeAnswerTool(manager, chatModeOf) {
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
      'current provision (returned as a structured empty result, not a hard error). ' +
      'When citing an evidence item in your answer, render its evidence_url as a clickable ' +
      'Markdown link, e.g. [依据：<standard_no> <clause_number>](<evidence_url>) — the GUI ' +
      'opens the original PDF at that page when the user clicks it. ' +
      'IMPORTANT — verification.unsupported_context: if it lists a clause number you cited, ' +
      'that citation is NOT supported and you MUST disclose it in your own words rather than ' +
      'silently dropping it: name the standard, then say which case it is — ' +
      'same_standard_not_retrieved means the clause belongs to a standard that IS in the ' +
      'evidence but the clause itself was not retrieved (a retrieval gap, not a fabrication); ' +
      'outside_evidence_standard means it points at a standard outside the retrieved evidence ' +
      '(out of scope, or possibly invented). Never present such a citation as support, and ' +
      'never omit the fact that it was raised.',
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
            folder_id: {
              type: 'string',
              description:
                'Restrict retrieval to one bookmark folder (bmf_… id). Host force-overrides this ' +
                'from the session chat-mode when 在本收藏夹内提问 is active. Default absent.',
            },
            max_evidence: {
              type: 'integer',
              description: 'Max evidence items to return (default 8; the engine hard-caps at 8).',
            },
            material_project_id: {
              type: 'string',
              description:
                'Scope this ask to one 参考资料 project (prj_… id) so the answer also uses that ' +
                'project\'s APPROVED materials. Omitted = materials are not consulted at all ' +
                '(the prompt is then byte-identical to a plain law-only ask). Materials arrive ' +
                'in a separate 参考资料 section with their own [[m:i]] citations, grouped by ' +
                'how much weight they may carry: 本任务准则 (declared criterion, outranks the ' +
                'statutes for this task), 可作依据, 已获多源互证的辅证, 仅作线索 (must NOT ' +
                'support a conclusion on its own), 已知不可用 (must NOT be used in the ' +
                'conclusion). Unapproved material is never included. The result carries ' +
                'material_usage so you can report what was actually used.',
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
      // 第 6 步 §1：**两条**返回路径都要装得下 —— 正常路径（搜 `answer_scope: scope`）与
      // 422 路径 `validationError()`（搜 `error: { code, message }`）。两条共有的 12 个键
      // 进 `required`；`answer_scope`（只正常路径有）与 `error`（只 422 有）**必须列进
      // `properties` 但不 required**：漏列的后果是那条路径每次调用都 isError。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          httpStatus: { type: 'number' },
          answer_scope: ANSWER_SCOPE,
          tier: NULLABLE_STRING,
          found: { type: 'boolean' },
          query: { type: 'string' },
          query_mode: { type: 'string' },
          error: {
            type: 'object',
            additionalProperties: false,
            properties: { code: { type: 'string' }, message: { type: 'string' } },
            required: ['code', 'message'],
          },
          evidence: { type: 'array', items: ANSWER_EVIDENCE },
          derivation: { type: 'string' },
          conclusion: { type: 'string' },
          verification: { oneOf: [ANSWER_VERIFICATION, { type: 'null' }] },
          notes: { type: 'array', items: { type: 'string' } },
          meta_summary: { type: 'string' },
          // 2026-09-20：`params.material_project_id.description` 承诺 "The result carries
          // material_usage" —— 这个键只正常路径有（422 路径没有）⇒ 列进 properties、**不 required**。
          material_usage: ANSWER_MATERIAL_USAGE,
        },
        required: ['ok', 'httpStatus', 'tier', 'found', 'query', 'query_mode', 'evidence',
          'derivation', 'conclusion', 'verification', 'notes', 'meta_summary'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 120_000,
    // 第 6 步 §3：**可并行**（但见下）。判据同官方契约（"must not mutate parent-owned
    // state"）：一次 `POST /ks/answer` 是**查询**语义，`:758-880` 的落点全是局部变量
    // （`scope`/`trimmed`/返回值），不碰模块级可变状态，也不写父级状态。
    //
    // ⚠ **这一行是本条唯一的判断分歧点**（施工单 §3 风险 2 的建议更保守：先只给
    // `ks_ping`/`ks_resolve_clause`/`ks_materials`，把 ks_answer/ks_effect_report 留到
    // e2e 有墙钟数据再加）。保留 `true` 的理由：①判据是"会不会改父级状态"而不是"会不会更快"；
    // ②引擎是单进程，串行只是**慢**，不是**错**；③施工单的验收表 C1 明写"除 ks_collect 外
    // 5 个"。
    // 已知**未实测**的代价：它最慢（内层 120s、引擎里还要跑一次 LLM）。若同一轮模型连发两条
    // ks_answer，并行会把它们同时压进引擎；引擎若串行处理，第二条会**在排队期间**消耗自己的
    // 120s 预算。这是"慢"不是"错"，但复核时应盯这一点（想更保守就把本行删掉，C1 同步改成 4）。
    isConcurrencySafe: () => true,
    async execute(args, exec) {
      const query = String((args && args.query) ?? '').trim()
      if (!query) throw new Error('ks_answer: "query" is required and must be a non-empty string')
      const requested = sanitizeParams(args && args.params)
      const queryMode = normalizeQueryMode(args && args.query_mode)

      // 查法规模式（决策 16）：会话开了「🔖 仅收藏」时**由 host 强制**限定检索范围，
      // 不信任模型是否记得传参（verifier P1-4：只靠提示词会被漏传/覆盖而静默失效）。
      // 判定走 `chatModeOf`（= effectiveChatMode，含**子会话继承**）——与提示段同一真值，
      // 否则子 agent 会拿到"提示词说已限收藏集、实际全库检索"的组合（二轮审计 P1）。
      // 强制值覆盖在 sanitizeParams 的**已校验**结果之上，故 top_k/max_evidence 的
      // 上限仍然生效（不存在绕过白名单的通道）。
      //
      // 收藏夹内提问（2026-10）：folderId 非空 → host 强制传 folder_id（引擎按
      // doc_ids ∪ clause_keys 并集过滤），同样不信任模型自传值。注意**先夹后收藏**：
      // 夹范围激活时 bookmarksOnly 若也开着则两个强制参数都带（引擎侧 folder 过滤
      // 在 bookmarks 过滤之后同链执行——双重收紧，语义不冲突）。
      const chatMode = chatModeOf(exec)
      const folderActive = typeof chatMode.folderId === 'string' && chatMode.folderId.length > 0
      let params = requested
      if (folderActive) {
        params = { ...(params ?? {}), folder_id: chatMode.folderId }
      }
      // 参考资料项目（2026-09-17 材料平面，`/materials use <prj_id>` 设的会话级真值）：
      // 同样**由 host 强制**传给引擎，不信任模型自传值——理由与收藏夹完全一致：
      // 只靠提示词会被漏传/覆盖而**静默失效**，而"以为在用公司制度、其实没用"是
      // 本战役反复打的失真。引擎侧只把 review_status='approved' 的材料送进提示词，
      // 故 host 传参**不等于**绕过评审（评审硬门在引擎的 SQL 里）。
      const materialActive = typeof chatMode.materialProjectId === 'string'
        && chatMode.materialProjectId.length > 0
      if (materialActive) {
        params = { ...(params ?? {}), material_project_id: chatMode.materialProjectId }
      }
      if (chatMode.bookmarksOnly) {
        params = { ...(params ?? {}), bookmarks_only: true }
      }
      const scope = {
        forensic: chatMode.forensic === true,
        bookmarks_only: params?.bookmarks_only === true,
        // 收藏夹范围（2026-10）：host 强制传参的真值——folder/folder_name 在夹范围
        // 激活时非 null；folder=false 且未激活。与 bookmarks_only 一样，这是"host 是否
        // 强制传参"的回显，不是"引擎侧过滤一定生效"的证明（引擎 notes 会如实说明）。
        folder: folderActive,
        folder_id: folderActive ? chatMode.folderId : null,
        folder_name: folderActive ? (chatMode.folderName ?? null) : null,
        // 参考资料项目（2026-09-17）：同款回显——material=false 且未绑定时明确是
        // false/null，而不是"不确定"。**这不是"材料一定进了提示词"的证明**：
        // 项目里可能一条已批准材料都没有，引擎的 notes/material_usage 才是真值。
        material: materialActive,
        material_project_id: materialActive ? chatMode.materialProjectId : null,
        material_project_name: materialActive ? (chatMode.materialProjectName ?? null) : null,
        // 生效来源（session=本会话开的 / parent=继承自父会话）——审计与模型都可自证
        source: chatMode.source,
      }

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
      // verifier P1-8：200 但信封缺 data 时，旧代码会产出 ok:true / found:false /
      // verification:null —— 模型（尤其在查法规模式下）会把它说成「库内无此条款」，
      // 而真相是工具失败（反代/旧引擎/非 JSON 响应）。与 ks_effect_report 同款加固：
      // 信封不符就抛错，绝不伪装成"查无此条"。
      if (data === null || typeof data !== 'object') {
        throw new Error(
          `ks_answer: 响应信封异常（HTTP ${probe.status}，期望 {code:200,data:{…}} 但未取到 data）。`
            + '这通常意味着引擎版本不匹配或中间层改写了响应；请先 ks_ping 确认引擎可用，'
            + '不要把本次结果当作"库内无此条款"。',
        )
      }
      const trimmed = trimAnswer(data)
      const found = trimmed ? trimmed.evidence.length > 0 : false

      return {
        ok: probe.status === 200,
        httpStatus: probe.status,
        // 本次检索的实际范围（host 强制后的真值）——供模型与审计核对"仅收藏"是否生效
        answer_scope: scope,
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
        // ⚠ 2026-09-20：这一行**原来漏了** —— `trimAnswer` 算出了 `material_usage`，而这里没转发，
        // 于是 `material_project_id` 的 description 承诺的 "the result carries material_usage" 是句空话，
        // 模型永远看不到"本次到底用了哪个项目的哪几条材料、哪些只算线索"（白名单纪律的反面例子）。
        // 没给项目范围时引擎给 `null`（"没用材料"与"用了但没命中"必须可区分）。
        material_usage: trimmed ? trimmed.material_usage : null,
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
 * P1c-RouteA bbox host 路由：GET /ks/bbox?rev=<clause_revision_id>（同源，exact）。
 * 转发引擎只读 GET /api/v1/clauses/<rev>/spans，把 bbox spans 交给 client；
 * token 只在 host→引擎这段，绝不回传页面（同 /ks/session 信任模型）。
 * 成功 200 → { ok:true, found:true, spans }; 引擎 404（条款不存在）→
 * { ok:true, found:false, spans:[] }（client 无框降级，不是错误）；
 * 自身失败 → 503 { ok:false, error }；非 GET → 405；缺 rev → 400。
 */
function registerKsBboxRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_BBOX_PATH,
    handler: async (req, res) => {
      if (req.method !== undefined && req.method !== 'GET') {
        res.writeHead(405, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'method_not_allowed', message: 'GET only' } }))
        return
      }
      const u = new URL(req.url ?? '/', 'http://localhost')
      const rev = u.searchParams.get('rev')
      if (!rev) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'bad_request', message: 'rev required' } }))
        return
      }
      try {
        const session = await manager.ensureLive()
        const call = (sess, signal) => apiGet(
          originUrl(sess.port),
          '/api/v1/clauses/' + encodeURIComponent(rev) + '/spans',
          { token: sess.token, signal, timeoutMs: 15_000 },
        )
        let probe = await call(session)
        // 401 -> session file may have rotated (port/token change per engine
        // start). Re-read the session and retry ONCE before surfacing an error.
        if (probe.status === 401) {
          const fresh = await manager.ensureLive()
          if (fresh && (fresh.port !== session.port || fresh.token !== session.token)) {
            probe = await call(fresh)
          }
        }
        if (probe.status === 401) {
          throw new Error('引擎拒绝了 Bearer token(401)，重读会话后仍失败')
        }
        // 引擎 404 = 该 rev 条款不存在（无 bbox 可给）→ 无框降级，不是错误。
        if (probe.status === 404) {
          res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
          res.end(JSON.stringify({ ok: true, found: false, spans: [] }))
          return
        }
        if (probe.status !== 200) {
          throw new Error(`引擎返回 HTTP ${probe.status}: ${probe.error || probe.text}`)
        }
        const spans = probe.body && probe.body.data && Array.isArray(probe.body.data.spans)
          ? probe.body.data.spans
          : []
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: true, found: spans.length > 0, spans }))
      } catch (error) {
        res.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({
          ok: false,
          error: {
            code: 'ks_bbox_unavailable',
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
  let allowLoading = null
  try {
    const require = createRequire(import.meta.url)
    const pkg = require.resolve('pdfjs-dist/package.json')
    baseDir = join(dirname(pkg), 'wasm')
  } catch {
    baseDir = null
  }
  return ctx.webServer.register({
    kind: 'prefix',
    path: KS_PDF_WASM_PATH,
    handler: async (req, res) => {
      if (baseDir === null) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable', message: 'pdfjs-dist wasm dir not resolvable' } }))
        return
      }
      // Lazy + memoized whitelist read on first request. Await unwraps the
      // fs.promises.readdir Promise to string[] so `new Set(...)` is valid; a
      // read failure degrades to an empty set (clean 404) instead of wedging.
      if (allow === null) {
        if (allowLoading === null) allowLoading = readdir(baseDir).catch(() => [])
        allow = new Set(await allowLoading)
      }
      if (allow.size === 0) {
        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable', message: 'pdfjs-dist wasm dir empty' } }))
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
        if (req.method === 'HEAD') {
          res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store', 'Content-Length': bytes.length })
          res.end()
          return
        }
        res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
        res.end(bytes)
      } catch (error) {
        res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' })
        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_read_failed', message: error instanceof Error ? error.message : String(error) } }))
      }
    },
  })
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
  // ⚠ **未知配置键 ⇒ 当场报错**。本地的 `@deepseek-ai/schemastery`(3.18.2) 没有 `.strict()`、
  //   `.loose(false)` 也照旧保留未知键（都实测过），所以"键名拼错"这件事 schema 挡不住。
  //   而静默忽略一个拼错的键 = 部署方**以为改了行为、其实没有** —— 正是官方点名的静默失效。
  const unknownKeys = Object.keys(config).filter((k) => !CONFIG_KEYS.includes(k))
  if (unknownKeys.length > 0) {
    throw new Error(
      `ks-dsh-plugin 配置里有未知键：${unknownKeys.join('、')}。`
      + `可用键：${CONFIG_KEYS.join('、')}（拼错的键会被静默忽略，所以这里直接报错）`,
    )
  }
  const opts = {
    engineRoot: config.engineRoot ?? CONFIG_DEFAULTS.engineRoot,
    python: config.python ?? CONFIG_DEFAULTS.python,
    startupTimeoutMs: config.startupTimeoutMs ?? CONFIG_DEFAULTS.startupTimeoutMs,
    idleTimeoutMs: config.idleTimeoutMs ?? CONFIG_DEFAULTS.idleTimeoutMs,
    trustedHosts: config.trustedHosts ?? CONFIG_DEFAULTS.trustedHosts,
  }
  const manager = new EngineManager(opts)

  // 批3 keepalive（问题清单#12）：查法规模式有会话开着时，引擎空闲回收
  // 前续命（否则下一次 ks_answer/ks_resolve_clause 要吃 20s+ 冷启动——载入
  // embedding 模型）。钩子只读 chatmode 内存态，绝不拉引擎、不落盘。
  manager.keepAliveCheck = () => hasActiveForensicSessions()

  // Dispose lifecycle: arm the idle auto-kill and tear down on fiber dispose.
  ctx.effect(() => {
    manager.armIdle()
    return () => {
      void manager.dispose()
    }
  })

  // 「📜 查法规模式」的**唯一真值来源**（决策 14/16）：提示段与工具层必须共用同一个
  // 判定，否则会出现"提示词说已按收藏集检索、工具层其实没强制"的打脸组合
  // （verifier 二轮实测：子会话提示词声称已强制、ks_answer 实际全库检索）。
  //
  // 子会话继承：子 agent 是新会话（origin:'subagent'），自身查不到父会话开关。
  // 用 `agents` 服务沿 header.parentSession 向上解析（≤4 跳）；服务不可用/父会话已被回收
  // → 静默退化为不继承。
  //
  // ⚠ **`agents` 是"可缺省"的服务，所以不走 `inject` 而走 `ctx.get()`**（2026-09-19 整改）：
  //   官方 `docs/cordis-tutorial/03-services.md`「`inject` is for hard requirements. For a
  //   capability the plugin can live without, skip `inject` and probe at the use site」；
  //   并明确点名了错法的代价：「the consumer stays PENDING and prints nothing」——
  //   声明成硬依赖后，真正缺服务时**整个插件永不 mount 且不打任何日志**，
  //   而下面这段兜底代码**永远不会被执行**（我们此前就是这样：兜底是死代码）。
  //   官方事故复盘 `docs/postmortem/0001-…md` 给的读法也是 `ctx.get(name)`，**不是** `ctx.<name>`。
  const parentSessionOf = (sessionId) => {
    try {
      const parent = ctx.get('agents')?.get?.(sessionId)?.session?.header?.parentSession
      return typeof parent === 'string' ? parent : null
    } catch {
      return null
    }
  }
  const chatModeOf = (exec) =>
    effectiveChatMode(exec?.agent?.session?.id ?? '', { parentSessionOf })

  // Registration is effect-based: disposing the fiber unregisters all tools.
  ctx.tools.register(makePingTool(manager))
  ctx.tools.register(makeResolveTool(manager, chatModeOf))
  ctx.tools.register(makeAnswerTool(manager, chatModeOf))
  ctx.tools.register(makeEffectReportTool(manager))
  // 材料平面只读工具：让模型能按名字**发现**项目 id（否则 `material_project_id`
  // 只能靠用户手抄），并看清每份材料的评审状态。只读——评审是用户的判断。
  ctx.tools.register(makeMaterialsTool(manager))
  // 采集工具（**写**）：业主裁定"采集默认开、但必须经用户判断或系统评审"。
  // 与 ks_materials 分成两个工具是**权限边界**：读一个、写一个，名字即权限。
  // 它只能登记 pending，发不出批准；也不发 source_tier（不得自 claim 可信度）。
  ctx.tools.register(makeCollectTool(manager, chatModeOf))

  // 提示段：**根上下文注册一次**，text provider 每次组装提示时按 `context.agent.session.id`
  // 现查开关 —— 开关一打开，下一轮请求就带上取证纪律（无需重启会话）。与 plan-mode 的
  // `plan:policy` 同款姿势。
  //
  // verifier P0-1：段 provider 是同步函数、不能 await，只靠 client 的 GET 触发懒加载
  // 会让"落盘真值"在没有该 GET 的场景（CLI/ACP、dock 未挂载、GET 失败）静默失效，
  // 所以这里在 apply() 阶段**显式预热**一次（磁盘读，毫秒级）。
  void ensureLoaded().catch(() => { /* 读失败已降级为内存态，不阻断插件启动 */ })
  ctx.effect(() => ctx.systemPrompt.section(makeChatModeSection({ parentSessionOf })),
    'ks-dsh-plugin: 查法规模式提示段')

  // 「/forensic」「/bookmarks」两条**斜杠命令**（用户 2026-09-10：输入框上方的按钮太丑，
  // 改成 / 调用）。命令走 host 命令表，不进模型、不产生对话消息，结果由 composer 直接渲染；
  // 状态与提示段/工具层共用同一份会话级真值。
  ctx.effect(() => {
    // 爆炸半径护栏在 registerKsChatModeCommands 内部（唯一一处、可测）：ctx.commands
    // 缺失或单条命令校验失败都只降级为「该命令没注册」并吼日志，绝不冒出 apply()。
    const disposers = registerKsChatModeCommands(ctx, { parentSessionOf })
    return () => {
      for (const dispose of disposers) {
        try { dispose?.() } catch { /* 命令表可能已随 fiber 撤销 */ }
      }
    }
  }, 'ks-dsh-plugin: 查法规模式斜杠命令')

  // P1c-RouteA: 同源路由（client 半取引擎会话 + pdf.js worker/wasm 资源）。worker/wasm OPTIONAL。
  //
  // ⚠ `webServer` 是**硬依赖**（2026-09-19 整改）：没有它，整个 `/ks/*` 路由面（证据 PDF、
  //   client 取引擎会话、巡检/公告/导入写路由）全部消失，插件等于不可用。
  //   ⇒ 它**留在 `inject` 里**（官方：`inject` is for hard requirements），
  //   但**下面那层"可缺省"兜底被删掉了** —— 官方点名过那种写法的代价：
  //   真缺服务时插件永远 PENDING、**什么都不打印**，而兜底分支**永远不执行**（死代码），
  //   于是 `ctx.webServer` 为假这件事**永远不会有人知道**。
  //   现在缺服务 ⇒ 在 `inject` 层就 PENDING（官方语义），或在这里**当场抛错**（响亮），
  //   两种都比"静默跳过 + 一行永远打不出来的警告"好。
  if (!ctx.webServer || typeof ctx.webServer.register !== 'function') {
    throw new Error('ks-dsh-plugin 需要 webServer 服务（/ks/* 路由面全靠它）；'
      + '它已声明在 inject 里，出现这句话说明宿主组合变了 —— 请检查 profile 是否还挂 webserver。')
  }
  {
    // verifier P0-1：信任栅栏必须盖住**全部** /ks 路由。只给凭据三条加守卫时，
    // 恶意页仍可经 /ks/session 同源读走引擎 Bearer token、经巡检/公告写路由改本地
    // 状态（实测伪造 Host 的 GET /ks/session 返回 200+token）。这里用一个 webServer
    // 门面统一套栅栏——以后新增路由自动继承，不会再漏。
    // 注意：门面只代理 webServer + logger（各 register* 只用到这两样）。
    const webCtx = {
      webServer: guardWebServer(ctx.webServer, { trustedHosts: opts.trustedHosts }),
      logger: ctx.logger,
    }
    ctx.effect(() => {
      const disposeSession = registerKsSessionRoute(webCtx, manager)
      const disposeWorker = registerPdfWorkerRoute(webCtx)
      const disposeWasm = registerPdfWasmRoute(webCtx)
      const disposeBbox = registerKsBboxRoute(webCtx, manager)
      // 每日巡检接线（决策 19, P0=手动）：host 侧 run/summary/settings 三路由 +
      // 启动接管（上次 running 批 adopt / 逾期 stale 标记）。fire-and-forget，
      // 不阻塞 apply；引擎只在确有遗留批次时被 ensureLive 拉起。
      const disposeInspection = registerKsInspectionRoutes(webCtx, manager)
      void inspectionStartupCheck(ctx, manager).catch((error) => {
        ctx.logger?.warn?.('ks-dsh-plugin: inspection startup check failed', error)
      })
      // 公告发现（语义 C）：源 CRUD/手动扫描/摘要路由 + 巡检尾自动触发接线在
      // inspection.js finalizeBatch 内。启动接管同 inspection 模式。
      const disposeAnnounce = registerKsAnnounceRoutes(webCtx, manager)
      void announceStartupCheck(ctx, manager).catch((error) => {
        ctx.logger?.warn?.('ks-dsh-plugin: announce startup check failed', error)
      })
      // 效力报告（决策 21 修订版）：纯代理零缓存零状态文件——即时聚合快照。
      const disposeReport = registerKsReportRoutes(webCtx, manager)
      // 渠道台账（§11.0 R4a，2026-09-18）：只读列表 + 人工「立刻探一遍」。
      // 与「大字体直连引擎取产物」不同：探针**对外发请求**（访问二十多个政府站），
      // 必须留在宿主侧受控；列表也走宿主，口径统一。
      const disposeChannels = registerKsChannelsRoutes(webCtx, manager)
      // 材料平面（Phase B 第五步）：**界面用**的同源读写通道。
      // 与 ks_materials（模型工具，只读）**分工明确**：批准/拒绝只能从这里进来，
      // 因为它的调用者是用户界面，而评审是**用户的判断**（方案 §6 硬门）。
      const disposeMaterials = registerKsMaterialsRoutes(webCtx, manager)
      // 文档图片同源代理（2026-09-13 端点接线）：/ks/doc-image/<doc>/(figure|formula|table-image)/…
      // → 引擎 PNG + X-Frac-* 透传。figure/formula/table-image 三端点自此 ZERO→LIVE。
      const disposeDocImage = registerKsDocImageRoutes(webCtx, manager)
      // API 配置（2026-09-08）：云 OCR / LLM 凭据代理——引擎写加密存储（DPAPI，
      // 2026-09-12 迁移整改后注册表只读覆盖、绝不写），host 不落盘不回显（纯代理）。
      const disposeApiSettings = registerKsSettingsRoutes(webCtx, manager)
      // 查法规模式开关（决策 14/16）：纯 host 状态（不碰引擎），落盘 ks-chatmode.json；
      // 上面的 systemPrompt 段读同一份状态。栅栏由 webCtx 统一施加。
      const disposeChatMode = registerKsChatModeRoutes(webCtx)
      // R27 入库预览 / 批量分桶（2026-09-11）：纯代理零缓存——引擎做解析与体检，
      // host 只列目录 + 转发（含默认「待入库」目录的按需创建）。**只读**：不移动/不改写文件。
      // 异步全量预览（2026-09-12 L239）：状态文件 ks-ingest.json + adopt/poll——
      // 浏览器关掉后仍由 host 权威推进；引擎重启丢进程内任务 → 如实标 failed。
      const disposeIngest = registerKsIngestRoutes(webCtx, manager)
      void ingestJobStartupCheck(ctx, manager).catch((error) => {
        ctx.logger?.warn?.('ks-dsh-plugin: ingest job startup check failed', error)
      })
      return () => {
        disposeSession()
        disposeWorker()
        disposeWasm()
        disposeBbox()
        disposeInspection()
        disposeAnnounce()
        disposeMaterials()
        disposeReport()
        for (const d of disposeChannels) d()
        disposeDocImage()
        disposeApiSettings()
        disposeChatMode()
        disposeIngest()
      }
    })
  }
}
