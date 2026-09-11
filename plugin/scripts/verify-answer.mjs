/**
 * ks-answer-p1b — verify-answer.mjs
 *
 * Self-check helper for the P1b ks_answer candidate. It does NOT call the
 * engine and does NOT invoke /api/v1/ks/answer (that would spend real LLM
 * quota). It only proves two things locally:
 *   1. The real `apply()` registers a `ks_answer` tool with the expected
 *      parameters schema and a >=120s timeoutMs.
 *   2. The trimming logic (a verbatim copy of the private helpers in index.js,
 *      which are not exported) folds a representative engine payload into a
 *      bounded, model-safe shape (no `_meta`, evidence capped, verification
 *      lists truncated/compacted).
 */
import { apply } from './src/index.js'

// ---- 1. Registration path (real index.js) -------------------------------
const registered = []
const fakeCtx = {
  effect: () => () => {},
  tools: { register: (t) => registered.push(t) },
}
apply(fakeCtx)
const names = registered.map((t) => t.name)
const answer = registered.find((t) => t.name === 'ks_answer')
console.log('[register] tools =', names.join(', '))
console.log('[register] ks_answer present =', !!answer)
console.log('[register] ks_answer.timeoutMs =', answer && answer.timeoutMs)
console.log('[register] required =', JSON.stringify(answer && answer.parameters.required))
console.log('[register] query_mode enum =',
  JSON.stringify(answer && answer.parameters.properties.query_mode.enum))
console.log('[register] render sample =',
  answer && answer.output.render(null, { ok: true }).length === 1 ? 'ok' : 'FAIL')

if (!answer) throw new Error('ks_answer tool was not registered')
if (answer.timeoutMs < 120000) throw new Error('timeoutMs must be >= 120s')
if (!answer.parameters.required.includes('query')) throw new Error('query must be required')

// ---- 2. Trimming logic (verbatim copy of index.js private helpers) ------
const QUERY_MODES = ['default', 'thorough', 'quick', 'guess']
const VERIFY_LIST_CAP = 8
const EVIDENCE_CAP = 8
function normalizeQueryMode(raw) {
  const mode = String(raw ?? 'default').trim()
  return QUERY_MODES.includes(mode) ? mode : 'default'
}
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
function shortList(arr, cap = VERIFY_LIST_CAP) {
  if (!Array.isArray(arr) || arr.length === 0) return []
  return arr.slice(0, cap).map(compact)
}
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

// Representative engine payload for tier=synthesis with 8 evidence + big verification.
const ev = (i) => ({
  clause_revision_id: `clrev_${i}`,
  doc_id: `doc_${i}`,
  standard_no: 'GB 30871-2022',
  clause_number: `6.${i}`,
  title: `特殊作业要求 ${i}`,
  legal_status: 'effective',
  legal_hierarchy: 'GB',
  page_start: 8 + i,
  snippet: 'x'.repeat(900), // >800, engine would cap; we keep as-is (<=800 guarantee)
  _clause_key: 'x',
  _full_text: 'x'.repeat(5000),
})
const bigPayload = {
  tier: 'synthesis',
  evidence: Array.from({ length: 12 }, (_, i) => ev(i)),
  derivation: '由[[c:0]][[c:1]]得出，[1]',
  conclusion: '应分级管理。',
  verification: {
    is_valid: true,
    answer_confidence: 'high',
    confidence_reasons: Array.from({ length: 30 }, (_, i) => `reason-${i}`),
    unsupported_clauses: ['5.9', '5.10', ...Array.from({ length: 20 }, (_, i) => `c${i}`)],
    unverified_numbers: ['25.0%', '4.0%'],
    modality_violations: Array.from({ length: 20 }, (_, i) => ({
      clause_number: `6.${i}`, actual_modality: '应', expected_modality: '宜',
    })),
    legal_element_violations: ['缺少适用条件'],
    citation_index_warnings: ['citation_index_out_of_range: [[c:99]]'],
  },
  notes: ['【即将生效】GB 30871-2023 将于 2026-01-01 施行，届时更新…'],
  _meta: {
    query: '动火作业怎么分级', search_query: '动火作业 分级',
    intent: 'rule_query', theme: 'special_work', tier_rule: 'synthesis',
    evidence_total: 8, retrieval: { result_count: 12, expanded_count: 3, vector_engine: 'sqlite-vec', rerank: { used: true } },
    llm_error: null, llm_raw_length: 4321, cite_warnings: ['citation_index_out_of_range: [[c:99]]'],
  },
}

const trimmed = trimAnswer(bigPayload)
const json = JSON.stringify(trimmed)
console.log('\n-- trimAnswer on synthesis payload --')
console.log('tier                 =', trimmed.tier)
console.log('evidence count       =', trimmed.evidence.length, '(input had 12 -> capped at 8)')
console.log('reason list length   =', trimmed.verification.confidence_reasons.length, '(input 30 -> capped 8)')
console.log('modality_violations  =', trimmed.verification.modality_violations.length, '(input 20 -> capped 8)')
console.log('has _meta?           =', Object.prototype.hasOwnProperty.call(trimmed, '_meta'))
console.log('has _full_text?      =', trimmed.evidence.some((e) => Object.prototype.hasOwnProperty.call(e, '_full_text')))
console.log('meta_summary         =', trimmed.meta_summary)
console.log('total JSON bytes     =', Buffer.byteLength(json, 'utf8'))

if (trimmed.evidence.length !== 8) throw new Error('evidence should be capped at 8')
if (trimmed.verification.confidence_reasons.length > 8) throw new Error('reasons not truncated')
if (Object.prototype.hasOwnProperty.call(trimmed, '_meta')) throw new Error('_meta leaked')
if (trimmed.evidence.some((e) => Object.prototype.hasOwnProperty.call(e, '_full_text'))) throw new Error('_full_text leaked')

// reference / empty-evidence path (查无)
const emptyTrim = trimAnswer({ tier: 'reference', evidence: [], derivation: '依据不足。',
  conclusion: '', verification: { is_valid: false, answer_confidence: 'low', confidence_reasons: ['无有效现行证据支撑'] },
  notes: [], _meta: { evidence_total: 0, retrieval: { result_count: 0 }, llm_error: 'DEEPSEEK_API_KEY 未配置' } })
console.log('\n-- trimAnswer on reference/empty payload --')
console.log('tier       =', emptyTrim.tier)
console.log('evidence   =', emptyTrim.evidence.length)
console.log('derivation =', JSON.stringify(emptyTrim.derivation))
console.log('meta_summary =', JSON.stringify(emptyTrim.meta_summary))

// params sanitize
console.log('\n-- sanitizeParams --')
console.log('valid   =>', JSON.stringify(sanitizeParams({ top_k: 100, bookmarks_only: true, max_evidence: 50, junk: 'x' })))
console.log('junk-only=>', JSON.stringify(sanitizeParams({ junk: 'x' })))
console.log('nothing =>', JSON.stringify(sanitizeParams(undefined)))
console.log('mode chk=>', normalizeQueryMode('thorough'), '/', normalizeQueryMode('nonsense'))

console.log('\n== VERIFY-ANSWER PASS ==')
