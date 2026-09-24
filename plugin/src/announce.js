/**
 * ks-dsh-plugin — src/announce.js (自定义公告源 · 公告发现, 2026-09, 决策 19 延伸)
 *
 * Host-half wiring for the engine's announcement-discovery flow (语义 C，用户
 * 拍板)：用户在设置栏目添加公告列表页 URL → 引擎随巡检定期"看新公告" → 新公告
 * 轻通知（哪怕库内无该标准号）。设计经 verify_rollout 三路择优（0.512）。
 *
 * 与 inspection.js 的关系：
 *   - 单向依赖：inspection.js finalizeBatch 尾 import 本模块 triggerAfterInspection
 *     （巡检完成 → 自动触发一次扫描）。本模块绝不 import inspection.js（防环）。
 *   - 独立状态文件 ks-announce.json（与 ks-inspection.json 并列）——两个模块各自
 *     全量写各自的文件，互不覆盖。
 *
 * Responsibilities (P0):
 *   - GET  /ks/announce/summary     : 本地快照（last 扫描 + sources_cache 计数）。
 *                                     绝不拉引擎（inspection 同款铁律）。
 *   - POST /ks/announce/scan        : 手动扫描（force=true 代理；409/503 透传）。
 *   - GET/POST /ks/announce/sources : 源清单/新增（纯代理，引擎 app_config 唯一真值）。
 *   - PUT/DELETE /ks/announce/sources/{id} : 部分更新（改 URL 引擎侧重置基线）/删除。
 *   - GET  /ks/announce/ingest/pending : 待入库计数（纯代理；界面写"还有多少条没进库"）。
 *   - POST /ks/announce/ingest         : 批量把已发现公告的**正文**入库（纯代理；
 *     引擎侧受时间预算 + 条数上限封顶，`stopped_early`/`pending_left` 原样回给界面）。
 *   - POST /ks/announce/auto-ingest    : 开/关"扫描完自动入库"（纯本地状态，默认**开**）。
 *   - triggerAfterInspection(ctx, manager) : 巡检 finalizeBatch 后触发（force=false，
 *     引擎侧 6h 时间闸防频繁）→ adoptScanPoll 轮询（touchActivity 保活）→
 *     终态落盘 state.last。
 *   - announceStartupCheck : 上次扫描 running 遗留 → 引擎健康且同 scan 在跑则接管，
 *     否则标 stale_run（UI"上次扫描疑似中断"）。
 *
 * KNOWN LIMITATIONS (honest, P0)：解析失败（WAF/验证码、JS 渲染壳、0 条）在引擎侧
 * per_source 诚实归因，host 原样透传；SSRF 默认禁内网（用户拍板严格版，无豁免）。
 *
 * Only Node builtins + ./engine.js helpers — no cordis import (mirrors engine.js).
 */

import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

import { apiGet, apiPost, originUrl, sessionFilePath } from './engine.js'

/* ------------------------------------------------------------------ *
 * Constants
 * ------------------------------------------------------------------ */

export const KS_ANNOUNCE_SUMMARY_PATH = '/ks/announce/summary'
export const KS_ANNOUNCE_SCAN_PATH = '/ks/announce/scan'
export const KS_ANNOUNCE_SOURCES_PATH = '/ks/announce/sources'
export const KS_ANNOUNCE_EXPORT_PATH = '/ks/announce/export'
/** 2026-09-24（切片②下半）：把已发现的公告**正文入库**（业主："应该入库的怎么没入库"）。 */
export const KS_ANNOUNCE_INGEST_PATH = '/ks/announce/ingest'
export const KS_ANNOUNCE_INGEST_PENDING_PATH = '/ks/announce/ingest/pending'
/** 2026-09-24（§10.194）：自动入库开关（默认**开** —— 业主报的就是"该入库的没入库"）。 */
export const KS_ANNOUNCE_AUTO_INGEST_PATH = '/ks/announce/auto-ingest'
/** 2026-09-24（§10.196/§10.199）：两条**只读**出口——
 *  · `triage`：Jev 给"规则判不收那批"分 clear/review/keep（**删除仍由业主拍板**）；
 *  · `change-signals`：「最近哪些法规标准变了」（业主第一目的：发布/更新/修改/废止）。 */
export const KS_ANNOUNCE_TRIAGE_PATH = '/ks/announce/ingest/triage'
export const KS_ANNOUNCE_CHANGE_SIGNALS_PATH = '/ks/announce/change-signals'
/** 对应的引擎端点。 */
const ENGINE_TRIAGE_PATH = '/api/v1/update/announce-ingest/triage'
const ENGINE_CHANGE_SIGNALS_PATH = '/api/v1/laws/change-signals'

/** 一次扫描完成后**自动**入库最多几条（引擎侧上限也是 20）。
 *  ⚠ 有界是刻意的：这件事在**无人值守**时也会跑（每天巡检之后），
 *  一次抓几百页不是"更努力"，是把宿主挂住。剩下的留给下一次扫描。 */
const AUTO_INGEST_LIMIT = 20

const ENGINE_SCAN_PATH = '/api/v1/update/announce-scan'
const ENGINE_SCAN_LAST_PATH = '/api/v1/update/announce-scan/last'
const ENGINE_SOURCES_PATH = '/api/v1/update/announce-sources'
const ENGINE_EXPORT_PATH = '/api/v1/update/announce-export'
const ENGINE_INGEST_PATH = '/api/v1/update/announce-ingest'
const ENGINE_INGEST_PENDING_PATH = '/api/v1/update/announce-ingest/pending'
const ENGINE_DOWNLOAD_PATH = '/api/v1/export/download'

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/** 独立状态文件（与 ks-inspection.json 并列，各自全量写互不覆盖）。 */
export function announceFilePath() {
  return join(dirname(sessionFilePath()), 'ks-announce.json')
}

const POLL_INTERVAL_MS = 1_200
const BODY_CAP = 65_536

/* ------------------------------------------------------------------ *
 * State file（last = 引擎 scan_state 白名单清洗快照；进程单写者）
 * ------------------------------------------------------------------ */

let _state = null
/**
 * 状态文件**读没读过**（2026-09-24 §10.194 修的真缺陷）。
 *
 * 为什么不能只看 `_state === null`：`getState()` 在未加载时会给**内存默认值**并把 `_state` 填上，
 * 于是"从没读过盘"这个事实被抹掉了 —— `initAnnounceState()` 是 `if (_state === null)`，
 * 第二次调用直接 no-op。真机形态：**宿主重启后第一次扫描**时，开关是"关"（磁盘上写着），
 * 但内存里是默认的"开" ⇒ **业主明明关了，还照样往库里入库**。
 * 子进程判据 D5 实测过这条（改动前 calls=1）。现在只有 `initAnnounceState()` 能置位，
 * 且它会把盘上的值**覆盖**掉那层默认值（磁盘是首次加载时的真值）。 */
let _stateLoaded = false
let _persistChain = Promise.resolve()
/** 卸载代数：disposer 递增 ⇒ await 窗口里的启动收尾整段作废（见 announceStartupCheck）。 */
let _announceEpoch = 0

function defaultState() {
  return {
    last: null, // 引擎 scan_state 快照（白名单清洗后），终态/最近一次
    stale_run: false, // 上次 running 遗留且无法接管
    // 2026-09-24（§10.194）：扫描完成后**自动**把新公告正文入库。默认**开**——
    // 业主的原话是"有大量应该入库但是放过了的东西"，靠"记得手动点按钮"正是会漏的原因。
    // 他在界面上可以随时关掉；关掉之后行为回到"只发现、不入库"。
    auto_ingest: true,
  }
}

async function loadStateFile() {
  try {
    const raw = await readFile(announceFilePath(), 'utf8')
    const parsed = JSON.parse(raw)
    if (parsed !== null && typeof parsed === 'object') {
      const s = defaultState()
      const p = parsed
      if (p.last && typeof p.last === 'object') s.last = sanitizeLast(p.last)
      if (p.stale_run === true) s.stale_run = true
      if (typeof p.auto_ingest === 'boolean') s.auto_ingest = p.auto_ingest
      return s
    }
  } catch { /* absent or corrupt -> defaults */ }
  return defaultState()
}

/** scan_state 白名单清洗（引擎数据 → host 快照；结构漂移安全网）。 */
function sanitizeLast(raw) {
  const perSource = Array.isArray(raw.per_source)
    ? raw.per_source.filter((p) => p && typeof p === 'object').map((p) => ({
        id: typeof p.id === 'string' ? p.id : '',
        name: typeof p.name === 'string' ? p.name : '',
        status: typeof p.status === 'string' ? p.status : 'unknown',
        reason: typeof p.reason === 'string' ? p.reason : null,
        items: Number(p.items) || 0,
        new_items: Number(p.new_items) || 0,
        baseline_items: Number(p.baseline_items) || 0,
      }))
    : []
  const recent = Array.isArray(raw.recent)
    ? raw.recent.filter((r) => r && typeof r === 'object').slice(0, 5).map((r) => ({
        title: typeof r.title === 'string' ? r.title : '',
        url: typeof r.url === 'string' ? r.url : '',
        published_date: typeof r.published_date === 'string' ? r.published_date : null,
        source_name: typeof r.source_name === 'string' ? r.source_name : '',
        first_seen: typeof r.first_seen === 'string' ? r.first_seen : null,
      }))
    : []
  return {
    scan_id: typeof raw.scan_id === 'string' ? raw.scan_id : '',
    status: typeof raw.status === 'string' ? raw.status : 'unknown',
    trigger: typeof raw.trigger === 'string' ? raw.trigger : null,
    started_at: typeof raw.started_at === 'string' ? raw.started_at : null,
    finished_at: typeof raw.finished_at === 'string' ? raw.finished_at : null,
    sources_total: Number(raw.sources_total) || 0,
    sources_done: Number(raw.sources_done) || 0,
    items_seen: Number(raw.items_seen) || 0,
    new_count: Number(raw.new_count) || 0,
    baseline_count: Number(raw.baseline_count) || 0,
    per_source: perSource,
    recent,
    error: typeof raw.error === 'string' ? raw.error : null,
    // 自动入库的**结果**（无人值守也会发生的事，必须留痕给人看）：
    // `{tried, ingested, skipped, failed, pending_left, stopped_early}` 或 `{error: "…"}`
    ingest: sanitizeIngest(raw.ingest),
  }
}

/** 自动/手动入库结果的白名单清洗（结构漂移安全网；误差一律留痕，不静默）。 */
function sanitizeIngest(raw) {
  if (!raw || typeof raw !== 'object') return null
  if (typeof raw.error === 'string') return { error: raw.error }
  const n = (v) => Number(v) || 0
  const bs = raw.by_status && typeof raw.by_status === 'object' ? raw.by_status : {}
  return {
    tried: n(raw.tried),
    ingested: n(raw.ingested),
    skipped: n(raw.skipped),
    failed: n(raw.failed),
    by_status: { effective: n(bs.effective), reference: n(bs.reference), withdrawn: n(bs.withdrawn) },
    pending_left: n(raw.pending_left),
    stopped_early: raw.stopped_early === true,
  }
}

function getState() {
  if (_state === null) _state = defaultState()
  return _state
}

function schedulePersist() {
  _persistChain = _persistChain
    .then(() => writeFile(announceFilePath(), JSON.stringify(getState(), null, 2), 'utf8'))
    .catch(() => { /* best-effort */ })
  return _persistChain
}

async function initAnnounceState() {
  if (!_stateLoaded) {
    _state = await loadStateFile()
    _stateLoaded = true
  }
  return _state
}

function update(fn) {
  const s = getState()
  const out = fn(s)
  void schedulePersist()
  return out
}

/* ------------------------------------------------------------------ *
 * Scan poll — 轮询引擎至终态 + touchActivity 保活 + 快照落盘
 * ------------------------------------------------------------------ */

let _poll = null // { scanId, stopped }

function stopPoll() {
  if (_poll) _poll.stopped = true
  _poll = null
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** 接管/启动一个扫描的轮询。 */
function adoptScanPoll(manager, ctx, scanId) {
  if (_poll && _poll.scanId === scanId && !_poll.stopped) return
  stopPoll()
  _poll = { scanId, stopped: false }
  void runScanPoll(manager, ctx, scanId)
}

async function runScanPoll(manager, ctx, scanId) {
  let stall = 0
  while (_poll && !_poll.stopped && _poll.scanId === scanId) {
    manager.touchActivity() // 扫描在引擎进程内跑；轮询即保活（idle 15min 杀不到）
    let sess = null
    try {
      sess = await manager.ensureLive()
    } catch { /* stall below */ }
    if (!sess) {
      stall += 1
      if (stall >= 40) {
        update((s) => {
          if (s.last && s.last.scan_id === scanId) {
            s.last.status = 'failed'
            s.last.error = '扫描期间引擎不可达（已停止轮询）'
          }
          return s
        })
        ctx.logger?.warn?.(`ks-announce: scan ${scanId} 轮询中止（引擎不可达）`)
        stopPoll()
        return
      }
      await sleep(POLL_INTERVAL_MS)
      continue
    }
    const probe = await apiGet(originUrl(sess.port), ENGINE_SCAN_LAST_PATH,
      { token: sess.token, timeoutMs: 10_000 })
    if (probe.status !== 200 || !probe.body || typeof probe.body !== 'object') {
      stall += 1
      if (stall >= 40) {
        update((s) => {
          if (s.last && s.last.scan_id === scanId) {
            s.last.status = 'failed'
            s.last.error = `扫描状态查询持续失败（HTTP ${probe.status}）`
          }
          return s
        })
        stopPoll()
        return
      }
      await sleep(POLL_INTERVAL_MS)
      continue
    }
    stall = 0
    const data = probe.body.data ?? {}
    const status = String(data.status ?? '')
    if (status === 'running') {
      await sleep(POLL_INTERVAL_MS)
      continue
    }
    // 终态（done/failed/never）：清洗落盘。「最近公告」= 库内最近见过 5 条
    // （含首扫基线条目——用户直觉是"看到了什么"，而非仅"新增了什么"；
    // scan_state.recent 只装新增，首扫后会是空的）。拉取失败降级用快照。
    let finalData = data
    try {
      const items = await apiGet(
        originUrl(sess.port),
        '/api/v1/update/announce-items?limit=5',
        { token: sess.token, timeoutMs: 10_000 },
      )
      if (items.status === 200 && items.body && Array.isArray(items.body.data?.items)) {
        finalData = { ...data, recent: items.body.data.items }
      }
    } catch { /* 保留 scan_state.recent（仅新增语义） */ }
    update((s) => {
      s.last = sanitizeLast(finalData)
      s.stale_run = false
      return s
    })
    ctx.logger?.info?.(`ks-announce: scan ${scanId} ${status}（新 ${data.new_count ?? 0} 条）`)
    // 2026-09-24（§10.194）：扫完之后**自动把新公告正文入库**（默认开，可在界面关）。
    // ⚠ 只对**成功收尾**的扫描做（failed/never 时没有"新公告"可言）；
    //   整段有界（一次最多 AUTO_INGEST_LIMIT 条）+ 结果留痕（失败也留，不静默）。
    if (status === 'done') {
      // ⚠ 先确保状态文件**读过**再判开关：`getState()` 在未加载时给的是**内存默认值**（开），
      //   那会让"业主已经关掉了"这一事实被忽略（他会以为关掉了、其实还在入库）。
      await initAnnounceState()
      if (getState().auto_ingest !== false) await autoIngestTail(ctx, sess)
    }
    stopPoll()
    return
  }
}

/**
 * 扫描收尾后的自动入库（fire-and-forget 的尾巴，但**await 住**——它决定本轮的落盘快照）。
 *
 * 为什么放在 host 而不是引擎：引擎的扫描线程不该顺带带货（各干一件事）；
 * 而"要不要自动入库"是**产品策略**，策略归 host，能力（抓正文入库）归引擎。
 * ⚠ 失败**不许静默**：把 `{error}` 写进 `last.ingest`，界面与状态文件都看得到。
 */
async function autoIngestTail(ctx, sess) {
  let out = null
  try {
    const res = await apiPost(originUrl(sess.port), ENGINE_INGEST_PATH,
      { token: sess.token, timeoutMs: 120_000, body: { limit: AUTO_INGEST_LIMIT } })
    if (res.status === 200 && res.body && typeof res.body === 'object') {
      out = res.body.data ?? {}
    } else {
      out = { error: `自动入库失败：引擎 HTTP ${res.status} ${res.error || ''}`.trim() }
    }
  } catch (err) {
    out = { error: `自动入库异常：${err instanceof Error ? err.message : String(err)}` }
  }
  const clean = sanitizeIngest(out) ?? { error: '自动入库：引擎未返回可读结果' }
  update((s) => {
    if (s.last) s.last.ingest = clean
    return s
  })
  if ('error' in clean) {
    ctx.logger?.warn?.(`ks-announce: ${clean.error}`)
  } else {
    ctx.logger?.info?.(
      `ks-announce: 自动入库 抓${clean.tried} 入${clean.ingested} 跳${clean.skipped} `
      + `失败${clean.failed} 剩${clean.pending_left}`)
  }
  return clean
}

/* ------------------------------------------------------------------ *
 * 触发（巡检尾）+ 启动接管
 * ------------------------------------------------------------------ */

/**
 * 巡检收尾触发（inspection.js finalizeBatch 尾调用，fire-and-forget）：
 * POST /announce-scan {force:false} —— 引擎侧 6h 时间闸防频繁；skipped →
 * 直接拿最新快照落盘；started → 轮询；409 → 已有扫描在跑，接管轮询。
 * 不做 host 侧源数判断（0 源时引擎秒级 done，比维护可能算错的缓存便宜）。
 */
export async function triggerAfterInspection(ctx, manager) {
  // ⚠ 先读盘再动状态（见 `_stateLoaded` 的说明）：否则"开关=关"会在重启后的第一次扫描里失效。
  await initAnnounceState()
  let session
  try {
    session = await manager.ensureLive()
  } catch (err) {
    ctx.logger?.warn?.('ks-announce: 巡检后触发扫描失败（引擎不可达）',
      err instanceof Error ? err.message : String(err))
    return
  }
  const probe = await apiPost(originUrl(session.port), ENGINE_SCAN_PATH,
    { token: session.token, timeoutMs: 20_000, body: { force: false } })
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    const data = probe.body.data ?? {}
    if (data.status === 'skipped') {
      // 时间闸内跳过：保留已有快照（含 items 版 recent）；仅从未落盘时记基线快照
      update((s) => {
        if (!s.last && data.last && typeof data.last === 'object') {
          s.last = sanitizeLast(data.last)
        }
        return s
      })
      return
    }
    if (typeof data.scan_id === 'string' && data.scan_id) {
      adoptScanPoll(manager, ctx, data.scan_id)
    }
    return
  }
  if (probe.status === 409) {
    // 已有扫描在跑 → 接管轮询（拿 last 的 scan_id）
    const last = await apiGet(originUrl(session.port), ENGINE_SCAN_LAST_PATH,
      { token: session.token, timeoutMs: 10_000 })
    const scanId = last.status === 200 && last.body?.data?.scan_id
      ? String(last.body.data.scan_id) : null
    if (scanId) adoptScanPoll(manager, ctx, scanId)
    return
  }
  ctx.logger?.warn?.(`ks-announce: 巡检后触发扫描异常（HTTP ${probe.status}）`)
}

/**
 * 启动接管（apply effect 内调用一次，fire-and-forget）：上次扫描 running 遗留
 * → 引擎健康且同 scan 在跑则重新轮询接管；否则标 stale_run。
 * 同时加载状态文件（announce.js 状态在此惰性初始化）。
 *
 * ⚠ fire-and-forget + 多个 `await`：卸载落在窗口里时，disposer 已经 `stopPoll()` 过
 * （那时 `_poll` 还是 null），本函数继续跑就会在 dispose 之后 `adoptScanPoll` 装一个
 * 持有已死 ctx 的活轮询。`_announceEpoch` 让这种收尾整段作废。
 */
export async function announceStartupCheck(ctx, manager) {
  const epoch = _announceEpoch
  const s = await initAnnounceState()
  if (epoch !== _announceEpoch) return
  const last = s.last
  if (!last || last.status !== 'running') return
  try {
    const sess = await manager.ensureLive()
    const probe = await apiGet(originUrl(sess.port), ENGINE_SCAN_LAST_PATH,
      { token: sess.token, timeoutMs: 10_000 })
    if (epoch !== _announceEpoch) return
    if (probe.status === 200 && probe.body?.data) {
      const status = String(probe.body.data.status ?? '')
      const scanId = String(probe.body.data.scan_id ?? '')
      if (status === 'running' && scanId === last.scan_id) {
        ctx.logger?.info?.(`ks-announce: 接管上次未完成扫描 ${scanId}`)
        adoptScanPoll(manager, ctx, scanId)
        return
      }
      if (status !== 'running') {
        // 已终态（可能在我们离线期间完成）→ 回收快照
        update((st) => { st.last = sanitizeLast(probe.body.data); st.stale_run = false; return st })
        return
      }
    }
  } catch { /* engine unavailable -> stale below */ }
  if (epoch !== _announceEpoch) return
  s.stale_run = true
  void schedulePersist()
  ctx.logger?.warn?.('ks-announce: 上次扫描疑似中断（无法接管）')
}

/* ------------------------------------------------------------------ *
 * HTTP helpers
 * ------------------------------------------------------------------ */

function jsonResponse(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(body))
}

function errorBody(code, message) {
  return { ok: false, error: { code, message } }
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    let done = false
    const fail = (err) => {
      if (done) return
      done = true
      reject(err)
    }
    req.on('data', (chunk) => {
      if (done) return
      size += chunk.length
      if (size > BODY_CAP) {
        fail(new Error('request body too large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (done) return
      done = true
      try {
        const text = Buffer.concat(chunks).toString('utf8')
        resolve(text.length === 0 ? {} : JSON.parse(text))
      } catch (err) {
        reject(err)
      }
    })
    req.on('error', fail)
  })
}

/** 通用引擎请求（GET/POST/PUT/DELETE；apiGet/apiPost 只覆盖 GET/POST）。
 *  返回与 apiPost 同形：{status, body, error?}。 */
async function engineRequest(method, base, path, { token, timeoutMs = 20_000, body } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = { accept: 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['content-type'] = 'application/json'
  try {
    const res = await fetch(`${base}${path}`, {
      method,
      headers,
      signal: controller.signal,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    let parsed = null
    try { parsed = await res.json() } catch { /* non-JSON */ }
    return { status: res.status, body: parsed, text: '' }
  } catch (error) {
    return {
      status: 0,
      body: null,
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
  }
}

/** GET one binary resource through the engine（导出文件下载；engineRequest 会
 *  JSON.parse，二进制走独立 helper——同 inspection.js fetchBinary 模式）。 */
async function fetchBinary(base, path, { token, timeoutMs = 30_000 } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, { headers, signal: controller.signal })
    const buffer = await res.arrayBuffer()
    return { status: res.status, ok: res.ok, buffer }
  } catch (error) {
    return {
      status: 0,
      ok: false,
      buffer: null,
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
  }
}

/* ------------------------------------------------------------------ *
 * Routes
 * ------------------------------------------------------------------ */

function registerSummaryRoute(ctx) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_ANNOUNCE_SUMMARY_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const s = getState()
      jsonResponse(res, 200, {
        ok: true,
        last: s.last,
        stale_run: s.stale_run === true,
        // 2026-09-24（§10.194）：自动入库开关也从这个快照出去（界面用它画勾选框；
        // 这一条**不拉起引擎**的纪律不变）。
        auto_ingest: s.auto_ingest !== false,
      })
    },
  })
}

function registerScanRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_ANNOUNCE_SCAN_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      const probe = await apiPost(originUrl(session.port), ENGINE_SCAN_PATH,
        { token: session.token, timeoutMs: 20_000, body: { force: true } })
      if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
        const data = probe.body.data ?? {}
        if (typeof data.scan_id === 'string' && data.scan_id) {
          adoptScanPoll(manager, ctx, data.scan_id)
        }
        jsonResponse(res, 200, { ok: true, data })
        return
      }
      if (probe.status === 409) {
        const msg = probe.body && typeof probe.body === 'object' && probe.body.message
          ? String(probe.body.message) : '已有公告扫描在运行中'
        jsonResponse(res, 409, errorBody('announce_scan_running', msg))
        return
      }
      jsonResponse(res, 502, errorBody('engine_error',
        `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}`))
    },
  })
}

/** 源 CRUD 纯代理：引擎 app_config 是唯一真值，host 不存副本（防两真值漂移）。
 *  UI 侧「源管理」默认收起、展开才请求——打开设置页不拉起引擎。 */
function registerSourcesRoutes(ctx, manager) {
  const proxy = async (res, method, enginePath, body) => {
    let session
    try {
      session = await manager.ensureLive()
    } catch (err) {
      jsonResponse(res, 503, errorBody('engine_unavailable',
        err instanceof Error ? err.message : String(err)))
      return
    }
    const probe = await engineRequest(method, originUrl(session.port), enginePath,
      { token: session.token, timeoutMs: 20_000, body })
    if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
      jsonResponse(res, 200, { ok: true, data: probe.body.data ?? {} })
      return
    }
    // 引擎错误语义透传（422 UPD-3008 / 404 UPD-2005 / 409 …）
    const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
    const message = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message) : `引擎返回 HTTP ${probe.status}`
    jsonResponse(res, probe.status === 404 ? 404
      : probe.status === 422 ? 422
      : probe.status === 409 ? 409 : 502,
      errorBody(typeof code === 'string' ? code : 'engine_error', message))
  }

  const disposers = [
    ctx.webServer.register({
      kind: 'exact',
      path: KS_ANNOUNCE_SOURCES_PATH,
      handler: async (req, res) => {
        if (req.method === 'GET') {
          await proxy(res, 'GET', ENGINE_SOURCES_PATH)
          return
        }
        if (req.method === 'POST') {
          let raw
          try {
            raw = await readJsonBody(req)
          } catch {
            jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
            return
          }
          await proxy(res, 'POST', ENGINE_SOURCES_PATH, raw)
          return
        }
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET or POST'))
      },
    }),
    ctx.webServer.register({
      kind: 'prefix',
      // ⚠⚠ **不许带尾斜杠**（2026-09-22 修，UI 批0，与 channels.js 同病同修）：
      // 真派发器判据是 `pathname === prefix || pathname.startsWith(prefix + '/')`，
      // 带尾斜杠 ⇒ `/ks/announce/sources/{id}` 一条都配不上 ⇒ 源的启停/删除整排死按钮。
      path: KS_ANNOUNCE_SOURCES_PATH,
      handler: async (req, res) => {
        // /ks/announce/sources/{id}：PUT/DELETE 透传到引擎同构路径
        const rest = (req.url || '').split('?')[0]
        const id = rest.slice(KS_ANNOUNCE_SOURCES_PATH.length + 1)
        if (!id || /[^\w-]/.test(id)) {
          jsonResponse(res, 400, errorBody('bad_request', '非法源 id'))
          return
        }
        const enginePath = `${ENGINE_SOURCES_PATH}/${encodeURIComponent(id)}`
        if (req.method === 'PUT') {
          let raw
          try {
            raw = await readJsonBody(req)
          } catch {
            jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
            return
          }
          await proxy(res, 'PUT', enginePath, raw)
          return
        }
        if (req.method === 'DELETE') {
          await proxy(res, 'DELETE', enginePath)
          return
        }
        jsonResponse(res, 405, errorBody('method_not_allowed', 'PUT or DELETE'))
      },
    }),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}

/** POST /ks/announce/export — 导出《公告发现》Excel（两步代理：引擎生成
 *  openpyxl（最近扫描源状态 + 公告明细全量）→ /export/download 取字节 →
 *  同源 attachment 回传，token 只在 host→引擎段；镜像 inspection export）。 */
function registerExportRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_ANNOUNCE_EXPORT_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      const build = await apiPost(originUrl(session.port), ENGINE_EXPORT_PATH,
        { token: session.token, timeoutMs: 90_000, body: {} })
      if (build.status !== 200) {
        jsonResponse(res, 502, errorBody('engine_error',
          `引擎导出失败 HTTP ${build.status}: ${build.error || build.text || 'no response'}`))
        return
      }
      const name = build.body?.data?.name
      if (typeof name !== 'string' || !name) {
        jsonResponse(res, 502, errorBody('engine_bad_response', '引擎未返回导出文件名'))
        return
      }
      const dl = await fetchBinary(originUrl(session.port),
        `${ENGINE_DOWNLOAD_PATH}?name=${encodeURIComponent(name)}`,
        { token: session.token, timeoutMs: 90_000 })
      if (dl.status !== 200 || !dl.buffer) {
        jsonResponse(res, 502, errorBody('download_failed',
          `下载导出文件失败（HTTP ${dl.status}）`))
        return
      }
      const asciiFallback = name.replace(/[^\x20-\x7e]/g, '_')
      res.writeHead(200, {
        'Content-Type': XLSX_MIME,
        'Content-Length': dl.buffer.byteLength,
        'Content-Disposition': `attachment; filename="${asciiFallback}"; filename*=UTF-8''${encodeURIComponent(name)}`,
      })
      res.end(Buffer.from(dl.buffer))
    },
  })
}

/** 公告**正文入库**（2026-09-24 切片②下半，开发史 §10.193）。
 *
 * 两条路由，都是**纯代理**（引擎是唯一真值，host 不存任何计数副本）：
 *   · `GET  /ks/announce/ingest/pending` → 待入库计数（界面写一句实话："还有 27 条没进库"）；
 *   · `POST /ks/announce/ingest`         → 批量入库（`{limit?, source_id?, force?}`）。
 *
 * ⚠ 超时按**引擎侧自己的预算**给：引擎单次最多跑 `web_ingest.INGEST_BUDGET_S`（45s）+ 收尾，
 *   所以这里给 120s（比预算宽一倍多，让"引擎自己说没做完"永远比"host 先掐断"先发生 ——
 *   掐断会得到一个没有原因的失败，而我们要的是那句 `stopped_early`/`pending_left`）。
 * ⚠ 不当成"可缓存/可重试"的 GET：这条**真写库**（POST 语义），别让任何一层替它重放。
 */
function registerIngestRoutes(ctx, manager) {
  const probe = async (res, method, enginePath, body) => {
    let session
    try {
      session = await manager.ensureLive()
    } catch (err) {
      jsonResponse(res, 503, errorBody('engine_unavailable',
        err instanceof Error ? err.message : String(err)))
      return
    }
    const out = method === 'GET'
      ? await apiGet(originUrl(session.port), enginePath,
        { token: session.token, timeoutMs: 120_000 })
      : await apiPost(originUrl(session.port), enginePath,
        { token: session.token, timeoutMs: 120_000, body })
    relayEngine(res, out)
  }

  /** **只读** GET 探针：triage 每条要问一次 Jev。
   *  ⚠ 超时按**实测**给，不是我拍的（2026-09-24 `var/tmp/measure-triage-latency.py`）：
   *    真库 125 条待清 × **0.46s/条 = 57.6s**。第一版给 30s ⇒ 这批**必然超时失败**
   *    （且是白等 30s 才发现）。这里给 180s：留 3 倍余量，且**上限有界**（不挂死）。
   *    界面同时写"约 0.5 秒一条、请稍候"，让用户知道要等。
   *  ⚠ 4xx 语义透传（非法 `signal` 之类）——照 `probe` 那条的口径，不吞成 200。 */
  const probeRead = async (res, enginePath) => {
    let session
    try {
      session = await manager.ensureLive()
    } catch (err) {
      jsonResponse(res, 503, errorBody('engine_unavailable',
        err instanceof Error ? err.message : String(err)))
      return
    }
    relayEngine(res, await apiGet(originUrl(session.port), enginePath,
      { token: session.token, timeoutMs: 180_000 }))
  }

  /** 引擎响应 → host 响应：200 透出 data；4xx（422 等）透传；其余归 502。 */
  const relayEngine = (res, out) => {
    if (out.status === 200 && out.body && typeof out.body === 'object') {
      jsonResponse(res, 200, { ok: true, data: out.body.data ?? {} })
      return
    }
    // 422（limit 非法）等语义透传，其余归 502（镜像 sources 那条代理的口径）
    const code = out.body && typeof out.body === 'object' ? out.body.error : null
    const message = out.body && typeof out.body === 'object' && out.body.message
      ? String(out.body.message) : `引擎返回 HTTP ${out.status}`
    jsonResponse(res, out.status === 422 ? 422 : 502,
      errorBody(typeof code === 'string' ? code : 'engine_error', message))
  }

  return [
    ctx.webServer.register({
      kind: 'exact',
      path: KS_ANNOUNCE_INGEST_PENDING_PATH,
      handler: async (req, res) => {
        if (req.method !== 'GET') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
          return
        }
        await probe(res, 'GET', ENGINE_INGEST_PENDING_PATH, undefined)
      },
    }),
    ctx.webServer.register({
      kind: 'exact',
      path: KS_ANNOUNCE_INGEST_PATH,
      handler: async (req, res) => {
        if (req.method !== 'POST') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
          return
        }
        const body = await readJsonBody(req).catch(() => undefined)
        if (body === undefined) {
          jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
          return
        }
        await probe(res, 'POST', ENGINE_INGEST_PATH, body ?? {})
      },
    }),
    // 2026-09-24：两条**只读**出口（此前有引擎端点、界面完全没接 ⇒ 业主看不到 = 白做）。
    //   · `GET /ks/announce/ingest/triage` → 「规则判不收、但要不要真清」那批的
    //     clear/review/keep 清单（Jev 判"清"，**删除仍由业主拍板**，host 与引擎都不删）。
    //   · `GET /ks/announce/change-signals` → 「最近哪些法规标准变了」（业主第一目的）。
    // 两条都是 GET + **只读**：不写库、不抓正文；超时给 30s（triage 每条要问一次 Jev）。
    ctx.webServer.register({
      kind: 'exact',
      path: KS_ANNOUNCE_TRIAGE_PATH,
      handler: async (req, res) => {
        if (req.method !== 'GET') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
          return
        }
        await probeRead(res, ENGINE_TRIAGE_PATH)
      },
    }),
    ctx.webServer.register({
      kind: 'exact',
      path: KS_ANNOUNCE_CHANGE_SIGNALS_PATH,
      handler: async (req, res) => {
        if (req.method !== 'GET') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
          return
        }
        await probeRead(res, ENGINE_CHANGE_SIGNALS_PATH)
      },
    }),
  ]
}

/** 自动入库开关（2026-09-24，§10.194）：`POST {enabled: boolean}`。
 *
 * 为什么要有这个开关：这件事**无人值守**也会跑（每天巡检尾 → 扫描 → 入库），
 * 而"哪些公告该进库"是**业主的判断**（他已经亲手圈过一遍该/不该）。
 * 默认开（他报的毛病就是"该入库的没入库"），但他一句话就能关掉。
 * 纯本地状态（`ks-announce.json`），不碰引擎、不碰库。
 */
function registerAutoIngestRoute(ctx) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_ANNOUNCE_AUTO_INGEST_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      const body = await readJsonBody(req).catch(() => undefined)
      if (body === undefined || typeof body.enabled !== 'boolean') {
        jsonResponse(res, 400, errorBody('bad_request', 'body 必须是 {"enabled": true|false}'))
        return
      }
      update((s) => {
        s.auto_ingest = body.enabled
        return s
      })
      ctx.logger?.info?.(`ks-announce: 自动入库已${body.enabled ? '开启' : '关闭'}`)
      jsonResponse(res, 200, { ok: true, data: { auto_ingest: body.enabled } })
    },
  })
}

/** Register all announce routes; returns the combined disposer. */
export function registerKsAnnounceRoutes(ctx, manager) {
  const disposers = [
    registerSummaryRoute(ctx),
    registerScanRoute(ctx, manager),
    registerSourcesRoutes(ctx, manager),
    registerExportRoute(ctx, manager),
    registerAutoIngestRoute(ctx),
    ...registerIngestRoutes(ctx, manager),
  ]
  return () => {
    // 递增代数是必须的（作废仍在飞的启动收尾）；"放在 stopPoll 之前"不是必须的
    // ——disposer 体全同步，两条语句之间不可能插入续体（复核实测：对调不改变结果）。
    // 保持"先递增"是给将来加 `await` 留的安全侧。这条更正见开发史 §10.135 六。
    _announceEpoch += 1
    stopPoll()
    for (const dispose of disposers) dispose()
  }
}
