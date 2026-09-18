/**
 * ks-dsh-plugin — src/inspection.js (每日巡检接线, 2026-09, 决策 19)
 *
 * Host-half wiring for the engine's update-inspection ("每日巡检") flow. It
 * owns the OUTER trigger, keep-alive and result-recall responsibilities that
 * the engine cannot cover (the engine runs in a lazily-spawned process that an
 * idle 15-min timer would kill mid-batch; and it has no push channel to the
 * GUI). Design ratified by verifier rollout (score 0.508) + four user
 * decisions — P0 is MANUAL trigger ("今日巡检" button) + catch-up marking;
 * the daily-auto switch exists in settings but stays OFF until P1.
 *
 * Responsibilities (P0):
 *   - `POST /ks/inspection/run`     : ensureLive → engine POST /update/check
 *                                     (tier0) → persist {last} → start the
 *                                     host-side poll loop that keeps the engine
 *                                     alive (touchActivity per tick) and recalls
 *                                     the batch to a terminal state.
 *   - `GET  /ks/inspection/summary` : local state snapshot (settings + last run
 *                                     + overdue days). NEVER spawns the engine.
 *   - `GET/PUT /ks/inspection/settings` : host state file (host cannot read the
 *                                     client prefs doc, and the engine exposes
 *                                     no app_config HTTP surface — the state
 *                                     file is the single trigger truth).
 *   - Startup hand-over (inspectionStartupCheck): a `last.status==='running'`
 *     left over from a previous dsh process is ADOPTED (poll loop resumes when
 *     the engine is healthy and the batch is really running); otherwise it is
 *     flagged `stale_run` so the UI says "上次巡检疑似中断".
 *   - Catch-up: a terminal done batch older than 24h is reported as overdue
 *     days in the summary — the UI shows 已逾期 N 天; the user clicks 今日巡检
 *     to catch up (never auto-replay, never per-day rollback).
 *
 * KNOWN LIMITATIONS (honest, P0): an engine 409 (UPD_BATCH_ALREADY_RUNNING)
 * from a ZOMBIE batch (engine process died mid-batch, DB row still running —
 * e.g. dsh restarted during a run) is surfaced verbatim; we do NOT mutate the
 * engine DB or force-pause the zombie batch in P0 (auto-recovery is P1 work).
 * tier0 batches are short, so the zombie window is small.
 *
 * Only Node builtins + ./engine.js helpers — no cordis import (mirrors
 * engine.js), so the smoke script can load it too.
 */

import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { homedir } from 'node:os'

import { apiGet, apiPost, originUrl, sessionFilePath } from './engine.js'
import { triggerAfterInspection } from './announce.js'

/* ------------------------------------------------------------------ *
 * Constants
 * ------------------------------------------------------------------ */

export const KS_INSPECTION_RUN_PATH = '/ks/inspection/run'
export const KS_INSPECTION_SUMMARY_PATH = '/ks/inspection/summary'
export const KS_INSPECTION_SETTINGS_PATH = '/ks/inspection/settings'
export const KS_INSPECTION_EXPORT_PATH = '/ks/inspection/export'

/** Trigger truth + last-run snapshot, next to the engine session file. */
export function inspectionFilePath() {
  return join(dirname(sessionFilePath()), 'ks-inspection.json')
}

/** P1 默认设置：autoEnabled 拨开 = 每日 time 自动跑 tier0 + dsh 晚开时启动
 *  补当天一次（决策 19「顺延补跑」并入本开关，不再独立 catchup 键）。 */
const DEFAULT_SETTINGS = {
  autoEnabled: false, // P1: 每日 time 自动跑（host 定时器消费）
  time: '08:30', // 自动跑的本机时点（HH:MM，本地时区）
  sundayTier1: false, // P2 占位：周日 tier1 全量滚动（本版本不消费）
}

const POLL_INTERVAL_MS = 1_200
// UI 纵览只需 change_type 分组计数，不落明细行；done 时一次性拉全量事件
// 归组（tier0 关注面是小批；上限 20 万行防失控——超出的仅细分不完整，四色
// 徽标计数仍以引擎 batch counts 为准）。
const CHANGE_FETCH_LIMIT = 200_000
const MAX_STALL_TICKS = 40 // 连续引擎错误 ~48s → 标 failed（别永久空转）
const RUNNING_CAP_MS = 30 * 60 * 1000 // tier0 绝不会跑 30 分钟——超时停轮询标 stale
const BODY_CAP = 65_536
const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

const TERMINAL = new Set(['done', 'failed'])
/** change_type 五类（与引擎 report.py CHANGE_TYPE_LABELS 同口径，UI 纵览用）。 */
const CHANGE_TYPES = ['new_version', 'superseded', 'withdrawn', 'not_found', 'no_change']

/** 五类**问题**（发布/修订/废止/现行性/编号核验）——⚠ 与上面 `CHANGE_TYPES` **不是一回事**，
 *  所以这里单独命名、单独一组键，别混：
 *    - `CHANGE_TYPES` 是**变更事件类型**（引擎判定的结果：新版/被替代/废止/查无/无变化）；
 *    - `QUESTION_CLASSES` 是**我们问过的五类问题**，证据在 `latest_info.classes`
 *      （引擎 §11.0 R6c-4c 起记录：每类给出 status/reason/channel/completeness）。
 *  面板上"五类结论"这一行回答的是：**这一批号里，每一类各有多少个真的答出来了**，
 *  以及没答出来的**主因**（是"这根渠道没这个字段"，还是"这次没轮到问它"）。 */
const QUESTION_CLASSES = ['发布', '修订', '废止', '现行性', '编号核验']

/** 未答原因 → 人话（键与引擎 `class_outcomes.REASONS` / 我们补的 absent/unreadable 对齐）。
 *  ⚠ 这张表是**给客户端**的口径（宿主只存原始 code，展示翻译归 UI）；宿主这份用于日志。 */
const REASON_LABELS = {
  channel_gave_no_field: '渠道无此字段',
  not_probed: '未轮到问',
  no_capability: '没有渠道能答',
  off_chain: '能答的不在链上',
  all_down: '在链上但全挂',
  absent: '记录里没这一类',
  unknown: '原因未记',
}

function emptyByType() {
  return { new_version: 0, superseded: 0, withdrawn: 0, not_found: 0, no_change: 0 }
}

/** 五类结论的空形态：`total` = **真的记了 `classes`** 的事件数（分母）；`unreadable` = 解析不了/没有该键的条数。 */
export function emptyByClass() {
  const classes = {}
  for (const c of QUESTION_CLASSES) classes[c] = { answered: 0, reasons: {} }
  return { total: 0, unreadable: 0, classes }
}

/** 未答原因的合计（宿主日志只报前几名；UI 自己算展示用的分布）。 */
function reasonTotals(byClass) {
  const out = {}
  for (const name of QUESTION_CLASSES) {
    const b = byClass.classes[name]
    if (!b) continue
    for (const [r, n] of Object.entries(b.reasons)) out[r] = (out[r] ?? 0) + n
  }
  return out
}

/* ------------------------------------------------------------------ *
 * State file (single writer: in-memory object + serialized persist chain)
 * ------------------------------------------------------------------ */

let _state = null // lazy load once per process
let _persistChain = Promise.resolve()

function defaultState() {
  return {
    settings: { ...DEFAULT_SETTINGS },
    last: null, // { batch_id, tier, trigger, status, total, checked, counts,
    //   pause_reason, started_at, finished_at, error, by_type }
    stale_run: false,
  }
}

/** Read the state file (or default when absent/corrupt). Never throws. */
async function loadStateFile() {
  try {
    const raw = await readFile(inspectionFilePath(), 'utf8')
    const parsed = JSON.parse(raw)
    if (parsed !== null && typeof parsed === 'object') {
      const s = defaultState()
      const p = parsed
      if (p.settings && typeof p.settings === 'object') {
        // 只收白名单键：旧状态文件的废弃键（如 catchupOnStart）就地剔除
        for (const key of Object.keys(DEFAULT_SETTINGS)) {
          if (key in p.settings) s.settings[key] = p.settings[key]
        }
      }
      if (p.last && typeof p.last === 'object') s.last = sanitizeLast(p.last)
      if (p.stale_run === true) s.stale_run = true
      return s
    }
  } catch { /* absent or corrupt -> defaults */ }
  return defaultState()
}

export function sanitizeLast(raw) {
  const last = { ...raw }
  last.batch_id = typeof last.batch_id === 'string' ? last.batch_id : ''
  last.status = typeof last.status === 'string' ? last.status : 'unknown'
  last.total = Number(last.total) || 0
  last.checked = Number(last.checked) || 0
  const counts = last.counts && typeof last.counts === 'object' ? last.counts : {}
  last.counts = {
    red: Number(counts.red) || 0,
    yellow: Number(counts.yellow) || 0,
    green: Number(counts.green) || 0,
    gray: Number(counts.gray) || 0,
  }
  // by_type：change_type 五类细分计数（新字段；旧状态文件无 → 空）。
  const bt = last.by_type && typeof last.by_type === 'object' ? last.by_type : {}
  last.by_type = emptyByType()
  for (const t of CHANGE_TYPES) {
    if (typeof bt[t] === 'number' && Number.isFinite(bt[t])) last.by_type[t] = Math.max(0, Math.floor(bt[t]))
  }
  // by_class：五类**问题**的结论统计（R6c-4c 的数据第一次被 UI 读；旧文件无 → null）。
  const bc = last.by_class && typeof last.by_class === 'object' ? last.by_class : null
  if (bc === null) {
    last.by_class = null
  } else {
    const clean = emptyByClass()
    clean.total = Math.max(0, Math.floor(Number(bc.total) || 0))
    clean.unreadable = Math.max(0, Math.floor(Number(bc.unreadable) || 0))
    const src = bc.classes && typeof bc.classes === 'object' ? bc.classes : {}
    for (const name of QUESTION_CLASSES) {
      const s = src[name]
      if (!s || typeof s !== 'object') continue
      clean.classes[name].answered = Math.max(0, Math.floor(Number(s.answered) || 0))
      const rs = s.reasons && typeof s.reasons === 'object' ? s.reasons : {}
      for (const [r, n] of Object.entries(rs)) {
        const v = Math.max(0, Math.floor(Number(n) || 0))
        if (v > 0) clean.classes[name].reasons[r] = v
      }
    }
    last.by_class = clean
  }
  last.auto = raw.auto === true // P1: 该批由每日定时触发（UI 显示"今日自动巡检"）
  delete last.changes // 明细行不再落盘（纵览统计替代），旧文件残留字段剔除
  return last
}

/** Current state (memory). Call after `await initInspectionState()` at boot. */
function getState() {
  if (_state === null) _state = defaultState()
  return _state
}

/** Persist the CURRENT in-memory state; serialized so writes never interleave. */
function schedulePersist() {
  _persistChain = _persistChain
    .then(() => writeFile(inspectionFilePath(), JSON.stringify(getState(), null, 2), 'utf8'))
    .catch(() => { /* best-effort — state is memory-truth */ })
  return _persistChain
}

/** Boot: load the state file once. */
async function initInspectionState() {
  if (_state === null) _state = await loadStateFile()
  return _state
}

/** Mutate state in memory and enqueue a persist. */
function update(fn) {
  const s = getState()
  const out = fn(s)
  void schedulePersist()
  return out
}

/* ------------------------------------------------------------------ *
 * Poll loop — recalls a running batch to a terminal state, keeps the
 * engine alive (touchActivity per tick) so the idle timer never fires.
 * ------------------------------------------------------------------ */

let _poll = null // { batchId, stopped } — one loop at a time per process

function stopPoll() {
  if (_poll) _poll.stopped = true
  _poll = null
}

/** 启动/接管一个批次的轮询。批次已 terminal → 直接收尾（不轮询）。 */
function adoptBatch(manager, ctx, batchId, initialStatus) {
  if (_poll && _poll.batchId === batchId && !_poll.stopped) return
  stopPoll()
  _poll = { batchId, stopped: false }
  void runPollLoop(manager, ctx, batchId, initialStatus)
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isoNow() {
  return new Date().toISOString()
}

async function runPollLoop(manager, ctx, batchId, initialStatus) {
  let stall = 0
  const startedAt = Date.now()
  const tick = () => {
    return !_poll || _poll.stopped || _poll.batchId !== batchId
  }

  // Already terminal at adopt time (startup hand-over of a done batch).
  if (TERMINAL.has(initialStatus)) {
    await finalizeBatch(manager, ctx, batchId, initialStatus)
    stopPoll()
    return
  }

  while (!tick()) {
    // Idle keep-alive: every progress poll counts as engine activity, so the
    // 15-min idle kill never fires mid-batch (EngineManager.touchActivity).
    manager.touchActivity()

    if (Date.now() - startedAt > RUNNING_CAP_MS) {
      update((s) => {
        if (s.last && s.last.batch_id === batchId) {
          s.last.error = '运行超时（30 分钟），已停止轮询；批次可能已中断'
        }
        s.stale_run = true
        return s
      })
      ctx.logger?.warn?.(`ks-inspection: batch ${batchId} 轮询超时停止`)
      stopPoll()
      return
    }

    let sess = null
    try {
      sess = await manager.ensureLive()
    } catch { /* engine down — stall below */ }
    if (!sess) {
      stall += 1
      if (stall >= MAX_STALL_TICKS) {
        await markFailed(batchId, '巡检期间引擎不可达（已停止轮询）')
        stopPoll()
        return
      }
      await sleep(POLL_INTERVAL_MS)
      continue
    }

    const probe = await apiGet(
      originUrl(sess.port),
      `/api/v1/update/batch/${encodeURIComponent(batchId)}`,
      { token: sess.token, timeoutMs: 10_000 },
    )
    if (probe.status === 404) {
      // 引擎活着但库内无此批（库被换/清过）→ 无法继续。
      await markFailed(batchId, '批次不存在（引擎返回 404）')
      stopPoll()
      return
    }
    if (probe.status !== 200) {
      stall += 1
      if (stall >= MAX_STALL_TICKS) {
        await markFailed(batchId, `引擎批次查询持续失败（HTTP ${probe.status}）`)
        stopPoll()
        return
      }
      await sleep(POLL_INTERVAL_MS)
      continue
    }

    stall = 0
    const data = probe.body && typeof probe.body === 'object'
      ? (probe.body.data ?? {}) : {}
    const status = String(data.status ?? '')
    const checked = Number(data.checked) || 0
    const total = Number(data.total) || 0

    update((s) => {
      if (!s.last || s.last.batch_id !== batchId) return s
      s.last.status = status
      s.last.checked = checked
      s.last.total = total
      s.last.counts = {
        red: Number(data.red_count) || 0,
        yellow: Number(data.yellow_count) || 0,
        green: Number(data.green_count) || 0,
        gray: Number(data.gray_count) || 0,
      }
      s.last.pause_reason = typeof data.pause_reason === 'string' ? data.pause_reason : null
      s.stale_run = false
      return s
    })

    if (TERMINAL.has(status)) {
      await finalizeBatch(manager, ctx, batchId, status)
      stopPoll()
      return
    }
    if (status === 'paused') {
      // tier0 不消耗预算；若真到 paused（预算/captcha）则停轮询，等人工 resume。
      ctx.logger?.warn?.(`ks-inspection: batch ${batchId} 暂停（${data.pause_reason ?? 'unknown'}），停止轮询`)
      stopPoll()
      return
    }
    await sleep(POLL_INTERVAL_MS)
  }
}

/**
 * Fetch the change events of one batch and reduce to per-change_type counts.
 * Returns null when the engine is unreachable or errors (caller keeps old data).
 */
async function fetchChangeSummaries(manager, batchId) {
  let sess = null
  try {
    sess = await manager.ensureLive()
  } catch {
    return null
  }
  const probe = await apiGet(
    originUrl(sess.port),
    `/api/v1/update/changes?batch_id=${encodeURIComponent(batchId)}&limit=${CHANGE_FETCH_LIMIT}`,
    { token: sess.token, timeoutMs: 30_000 },
  )
  if (probe.status !== 200 || !probe.body || !Array.isArray(probe.body.data)) return null
  const byType = emptyByType()
  const byClass = emptyByClass()
  for (const c of probe.body.data) {
    const t = c && typeof c === 'object' ? c.change_type : null
    if (typeof t === 'string' && t in byType) byType[t] += 1
    reduceOneClassRow(byClass, c)
  }
  return { by_type: byType, by_class: byClass }
}

/**
 * 把**一条**变更事件的 `latest_info.classes` 并进五类统计（就地改 `byClass`）。
 *
 * ⚠ 三条口径（都不是想当然选的）：
 *   1. `classes` 键**不存在** ⇒ 计入 `unreadable`，**不进** `total`：那是"这批没记五类"
 *      （R6c-4c 之前写的事件、或引擎侧读台账失败降级），与"记了但没答出来"**不是一回事**；
 *   2. 某类**缺项** ⇒ 记 `absent`（不是 `not_probed`）：引擎的 route_report 覆盖五类，
 *      真缺项说明记录不完整，不该冒充"没轮到问"；
 *   3. `total` 只数**有 classes 的条数**——UI 上的分母必须是"真的记了五类的号数"，
 *      否则一句"发布 3/500"会让人以为"几乎所有号都答不出发布"，而真相是"只有 3 个号有记录"。
 */
export function reduceOneClassRow(byClass, row) {
  let info = null
  if (row && typeof row === 'object') {
    const raw = row.latest_info_json
    if (typeof raw === 'string' && raw !== '') {
      try {
        info = JSON.parse(raw)
      } catch {
        info = null
      }
    } else if (raw && typeof raw === 'object') {
      info = raw
    }
  }
  const cls = info && typeof info === 'object' ? info.classes : null
  if (!cls || typeof cls !== 'object') {
    byClass.unreadable += 1
    return
  }
  byClass.total += 1
  for (const name of QUESTION_CLASSES) {
    const entry = cls[name]
    if (!entry || typeof entry !== 'object') {
      bumpReason(byClass.classes[name], 'absent')
      continue
    }
    if (entry.status === 'answered') {
      byClass.classes[name].answered += 1
    } else {
      bumpReason(byClass.classes[name],
                 typeof entry.reason === 'string' && entry.reason ? entry.reason : 'unknown')
    }
  }
}

function bumpReason(bucket, reason) {
  if (!bucket) return
  bucket.reasons[reason] = (bucket.reasons[reason] ?? 0) + 1
}

function byTypeAllZero(byType) {
  if (!byType) return true
  return CHANGE_TYPES.every((t) => (byType[t] ?? 0) === 0)
}

/** 五类统计是不是"没数据"（旧状态文件没有该字段时的形态）。 */
export function byClassEmpty(byClass) {
  if (!byClass || typeof byClass !== 'object') return true
  if (Number(byClass.total) > 0) return false
  const cls = byClass.classes && typeof byClass.classes === 'object' ? byClass.classes : {}
  return QUESTION_CLASSES.every((c) => !(cls[c] && cls[c].answered > 0)
    && !(cls[c] && cls[c].reasons && Object.keys(cls[c].reasons).length > 0))
}

/**
 * Terminal recall: fetch the change events ONCE, reduce to per-change_type
 * counts (the UI shows a 纵览统计, never a row list), persist the snapshot.
 * The full Excel detail export is produced engine-side on demand (export
 * route) — the host never stores detail rows.
 */
async function finalizeBatch(manager, ctx, batchId, status) {
  // 一次拉取、两份归组（change_type 计数 + 五类结论）——两次请求会出现两个口径不同的分母。
  const summaries = await fetchChangeSummaries(manager, batchId)
  const byType = summaries === null ? null : summaries.by_type
  const byClass = summaries === null ? null : summaries.by_class
  if (summaries === null) {
    ctx.logger?.warn?.(`ks-inspection: batch ${batchId} changes 拉取失败，细分计缺省`)
  }
  update((s) => {
    if (s.last && s.last.batch_id === batchId) {
      s.last.status = status
      s.last.finished_at = isoNow()
      s.last.by_type = byType ?? emptyByType()
      // 五类结论：拉不到就留 `null`（UI 不说"没有欠账"，只说"这次没取到"）
      s.last.by_class = byClass
      s.last.error = null
      if (status === 'failed') s.last.error = '巡检批次失败（引擎内错误，详见导出/报告）'
    }
    s.stale_run = false
    return s
  })
  const seen = byType ?? emptyByType()
  const changed = seen.superseded + seen.withdrawn + seen.new_version + seen.not_found
  ctx.logger?.info?.(`ks-inspection: batch ${batchId} ${status}（其中变化 ${changed}）`)
  if (byClass && byClass.unreadable > 0) {
    ctx.logger?.warn?.(`ks-inspection: ${byClass.unreadable} 条事件没有五类记录`
      + `（引擎未写或旧数据）——五类分母只算有记录的 ${byClass.total} 条`)
  }
  if (byClass && byClass.total > 0) {
    // 五类各答出多少 + 未答主因（人看着日志就能判断"是渠道缺字段，还是这次没轮到问"）
    const per = QUESTION_CLASSES
      .map((c) => `${c} ${byClass.classes[c]?.answered ?? 0}/${byClass.total}`)
      .join(' · ')
    const totals = Object.entries(reasonTotals(byClass)).sort((a, b) => b[1] - a[1])
    const top = totals.slice(0, 3)
      .map(([r, n]) => `${REASON_LABELS[r] ?? r} ${n}`).join(' / ')
    ctx.logger?.info?.(`ks-inspection: batch ${batchId} 五类结论 ${per}`
      + (totals.length > 0 ? `（未答主因：${top}）` : '（全部答出）'))
  }
  // 公告发现随巡检顺带触发（决策 19 延伸，语义 C）：引擎侧 6h 时间闸防频繁；
  // fire-and-forget，不阻塞巡检收尾。任何终态都触发（含空转批）。
  void triggerAfterInspection(ctx, manager).catch((err) => {
    ctx.logger?.warn?.('ks-inspection: 公告扫描触发异常',
      err instanceof Error ? err.message : String(err))
  })
}

async function markFailed(batchId, message) {
  update((s) => {
    if (s.last && s.last.batch_id === batchId) {
      s.last.status = 'failed'
      s.last.finished_at = isoNow()
      s.last.error = message
    }
    s.stale_run = false
    return s
  })
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

/** Drain + JSON.parse a request body (cap BODY_CAP). Rejects on oversize. */
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

const SETTINGS_KEYS = {
  autoEnabled: (v) => typeof v === 'boolean',
  time: (v) => typeof v === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(v),
  sundayTier1: (v) => typeof v === 'boolean',
}

/** Settings PUT: accept only whitelisted keys with validated values. */
function sanitizeSettingsPatch(raw) {
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null
  const out = {}
  for (const [key, validate] of Object.entries(SETTINGS_KEYS)) {
    if (key in raw) {
      if (!validate(raw[key])) return null // one bad key → whole patch rejected
      out[key] = raw[key]
    }
  }
  return out
}

function overdueDaysOf(last) {
  if (!last || last.status !== 'done' || !last.finished_at) return 0
  const t = Date.parse(last.finished_at)
  if (!Number.isFinite(t)) return 0
  const age = Date.now() - t
  return age > 86_400_000 ? Math.floor(age / 86_400_000) : 0
}

/* ------------------------------------------------------------------ *
 * Route handlers
 * ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ *
 * Run core — shared by the manual route and the daily-auto timer (P1)
 * ------------------------------------------------------------------ */

/**
 * Start one tier0 inspection run. Returns
 *   { ok: true, batch_id } on success, or
 *   { ok: false, http, code, message } mapped 1:1 onto the route's errors.
 * `auto` marks the run as daily-timer-triggered (state.last.auto → UI shows
 * 「今日自动巡检」; the engine still receives trigger='manual' — its only
 * channel — so the Word/Excel report keeps saying 手动一键, which is honest
 * at the engine layer).
 */
async function startInspectionRun(ctx, manager, { auto = false } = {}) {
  const s = getState()
  // Local double-gate: a batch we are already polling / marked running.
  if (s.last && s.last.status === 'running' && _poll && !_poll.stopped) {
    return { ok: false, http: 409, code: 'inspection_running', message: `巡检已在运行中（批次 ${s.last.batch_id}）` }
  }
  let session
  try {
    session = await manager.ensureLive()
  } catch (err) {
    return { ok: false, http: 503, code: 'engine_unavailable', message: err instanceof Error ? err.message : String(err) }
  }
  const probe = await apiPost(
    originUrl(session.port),
    '/api/v1/update/check',
    { token: session.token, timeoutMs: 25_000, body: { tier: 'tier0' } },
  )
  if (probe.status === 409) {
    // 引擎闸拒绝（DB running 或引擎进程内 _upd_runs）→ 透传引擎 message。
    // P0 不做僵尸批自动恢复（见文件头 KNOWN LIMITATIONS）。
    const msg = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message)
      : '引擎内已有运行中的巡检批次'
    return { ok: false, http: 409, code: 'engine_batch_running', message: msg }
  }
  if (probe.status !== 200) {
    return { ok: false, http: 502, code: 'engine_error', message: `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}` }
  }
  const data = probe.body && typeof probe.body === 'object' ? (probe.body.data ?? {}) : {}
  const batchId = typeof data.batch_id === 'string' ? data.batch_id : ''
  if (!batchId) {
    return { ok: false, http: 502, code: 'engine_bad_response', message: '引擎未返回 batch_id' }
  }
  update((st) => {
    // 引擎建批后 status='pending'，run_batch 线程随即转 running——对 UI 统一按 running 展示。
    const rawStatus = typeof data.status === 'string' ? data.status : 'pending'
    st.last = {
      batch_id: batchId,
      tier: 'tier0',
      trigger: 'manual',
      auto,
      status: rawStatus === 'pending' ? 'running' : rawStatus,
      total: Number(data.total) || 0,
      checked: 0,
      counts: { red: 0, yellow: 0, green: 0, gray: 0 },
      pause_reason: null,
      started_at: isoNow(),
      finished_at: null,
      error: null,
      by_type: emptyByType(),
    }
    st.stale_run = false
    return st
  })
  adoptBatch(manager, ctx, batchId, 'running')
  return { ok: true, batch_id: batchId }
}

function registerRunRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INSPECTION_RUN_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      const out = await startInspectionRun(ctx, manager, { auto: false })
      if (out.ok) {
        jsonResponse(res, 200, { ok: true, batch_id: out.batch_id, status: 'running' })
      } else {
        jsonResponse(res, out.http, errorBody(out.code, out.message))
      }
    },
  })
}

function registerSummaryRoute(ctx) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INSPECTION_SUMMARY_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const s = getState()
      // 启动时发现 running 但无人接管 → 提示疑似中断（见 startupCheck）。
      const stale = s.stale_run === true
      jsonResponse(res, 200, {
        ok: true,
        settings: s.settings,
        last: s.last,
        overdue_days: overdueDaysOf(s.last),
        stale_run: stale,
      })
    },
  })
}

/** GET one binary resource through the engine (e.g. /export/download file).
 *  Same shape family as apiGet but returns an ArrayBuffer (never JSON-parsed). */
async function fetchBinary(base, path, { token, signal, timeoutMs = 30_000 } = {}) {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onAbort, { once: true })
  }
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
    if (signal) signal.removeEventListener('abort', onAbort)
  }
}

/**
 * POST /ks/inspection/export — 导出「上一次巡检结果」为 Excel。
 * 生成在引擎侧（openpyxl，三 sheet：汇总/明细全量/趋势），host 代理两步：
 * 1) POST 引擎 /update/report-xlsx/{batch_id}（同 docx 报告通道，批次 404 透传）；
 * 2) 经引擎 /export/download 取字节 → 同源以 attachment 回传浏览器。
 * 仅导出「已完成」批次：last 缺失 / 仍在跑 → 409。
 */
function registerExportRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INSPECTION_EXPORT_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      const s = getState()
      const last = s.last
      if (!last || !last.batch_id) {
        jsonResponse(res, 409, errorBody('no_completed_batch', '还没有完成过巡检'))
        return
      }
      if (last.status === 'running') {
        jsonResponse(res, 409, errorBody('inspection_running', '巡检进行中，完成后方可导出'))
        return
      }
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable', err instanceof Error ? err.message : String(err)))
        return
      }
      // 1) 引擎生成 xlsx（openpyxl 全量明细可能耗时：给足超时）。
      const build = await apiPost(
        originUrl(session.port),
        `/api/v1/update/report-xlsx/${encodeURIComponent(last.batch_id)}`,
        { token: session.token, timeoutMs: 90_000 },
      )
      if (build.status === 404) {
        jsonResponse(res, 404, errorBody('batch_not_found', '该批次在引擎库中已不存在（可能已清理）'))
        return
      }
      if (build.status !== 200) {
        jsonResponse(res, 502, errorBody('engine_error', `引擎导出失败 HTTP ${build.status}: ${build.error || build.text || 'no response'}`))
        return
      }
      const data = build.body && typeof build.body === 'object' ? (build.body.data ?? {}) : {}
      const name = typeof data.name === 'string' ? data.name : ''
      if (!name) {
        jsonResponse(res, 502, errorBody('engine_bad_response', '引擎未返回导出文件名'))
        return
      }
      // 2) 取字节回传（token 只在 host→引擎段）。
      const dl = await fetchBinary(
        originUrl(session.port),
        `/api/v1/export/download?name=${encodeURIComponent(name)}`,
        { token: session.token, timeoutMs: 90_000 },
      )
      if (dl.status !== 200 || !dl.buffer) {
        jsonResponse(res, 502, errorBody('download_failed', `下载导出文件失败（HTTP ${dl.status}）`))
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

function registerSettingsRoutes(ctx) {
  const disposers = [
    ctx.webServer.register({
      kind: 'exact',
      path: KS_INSPECTION_SETTINGS_PATH,
      handler: async (req, res) => {
        const s = getState()
        if (req.method === 'GET') {
          jsonResponse(res, 200, { ok: true, settings: s.settings })
          return
        }
        if (req.method !== 'PUT') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'GET or PUT'))
          return
        }
        let raw
        try {
          raw = await readJsonBody(req)
        } catch {
          jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
          return
        }
        const patch = sanitizeSettingsPatch(raw)
        if (patch === null) {
          jsonResponse(res, 400, errorBody('bad_settings', 'settings 含未知键或非法值'))
          return
        }
        update((st) => {
          st.settings = { ...st.settings, ...patch }
          return st
        })
        jsonResponse(res, 200, { ok: true, settings: getState().settings })
      },
    }),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}

/* ------------------------------------------------------------------ *
 * Boot hand-over + route registration entry
 * ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ *
 * P1 每日自动巡检（决策 19 完整语义）
 *
 * autoEnabled 拨开 → 每日本机 time 时点自动跑 tier0；dsh 晚开/没开时，
 * 启动后第一个 tick 发现 now 已过今日时点且今日未跑 → 补跑一次（顺延
 * 补跑，不逐日回放）。手动跑过的当天照常视为"今日已跑"（定时目标 =
 * 每天至少一次）。
 * ------------------------------------------------------------------ */

let _autoTimer = null
let _autoFiring = false
let _autoLastAttempt = 0

/** 今日时点的本地 Date（today @ HH:MM）。 */
function todayAtTime(hhmm) {
  const parts = hhmm.split(':')
  const hh = Number(parts[0])
  const mm = Number(parts[1])
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), hh, mm, 0, 0)
}

/** 今日已跑判定：last 的开始/完成时刻（本地）>= 今日时点。 */
function ranTodaySince(settings, last) {
  if (!last) return false
  const stamp = last.started_at || last.finished_at
  if (!stamp) return false
  const t = Date.parse(stamp)
  if (!Number.isFinite(t)) return false
  return t >= todayAtTime(settings.time).getTime()
}

async function autoInspectionTick(ctx, manager) {
  const s = getState()
  if (s.settings.autoEnabled !== true) return
  if (_autoFiring) return
  if (_poll && !_poll.stopped) return
  if (s.last && s.last.status === 'running') return
  if (Date.now() < todayAtTime(s.settings.time).getTime()) return
  if (ranTodaySince(s.settings, s.last)) return
  // 失败防抖：一次尝试失败后 60s 内不重试（引擎起不来时别每 30s 刷日志）。
  if (Date.now() - _autoLastAttempt < 60_000) return
  _autoLastAttempt = Date.now()
  _autoFiring = true
  try {
    const out = await startInspectionRun(ctx, manager, { auto: true })
    if (out.ok) {
      _autoLastAttempt = 0
      ctx.logger?.info?.(`ks-inspection: 每日自动巡检已触发（${s.settings.time}，批次 ${out.batch_id}）`)
    } else {
      ctx.logger?.warn?.(`ks-inspection: 每日自动巡检触发失败（${out.code}）：${out.message}`)
    }
  } catch (err) {
    ctx.logger?.warn?.('ks-inspection: 每日自动巡检触发异常', err)
  } finally {
    _autoFiring = false
  }
}

/** 启动定时器（startupCheck 尾部调用——此时状态文件已加载）。 */
function startAutoInspectionTimer(ctx, manager) {
  if (_autoTimer !== null) return
  _autoTimer = setInterval(() => {
    void autoInspectionTick(ctx, manager)
  }, 30_000)
  if (typeof _autoTimer.unref === 'function') _autoTimer.unref()
}

function stopAutoInspectionTimer() {
  if (_autoTimer !== null) {
    clearInterval(_autoTimer)
    _autoTimer = null
  }
}

/**
 * 启动接管 + 逾期/僵尸检测（apply 的 effect 内调用一次，fire-and-forget）：
 *   - last.status==='running' 且引擎健康且批真在跑 → 重新 adopt（host 曾崩，
 *     引擎若还活着就能接回轮询）；
 *   - 否则标 stale_run → UI 提示"疑似中断"。
 *   - done 且超 24h 的逾期天数在 summary 现算（overdueDaysOf），不落盘。
 *   - 尾部启动 P1 每日定时器（30s tick：到点/顺延补跑判定见 autoInspectionTick）。
 */
export async function inspectionStartupCheck(ctx, manager) {
  const s = await initInspectionState()
  const last = s.last
  if (!last) return

  // 细分自愈：旧版本状态文件落盘的 done 批次没有 by_type（全 0）——现场
  // 补一次归组写回，之后不再触发（写盘后不再是全 0）。引擎因此被拉起一次
  // 是预期内的（仅此一处启动路径允许拉引擎，summary 路由绝不拉）。
  // ⚠ 五类统计（by_class）走**同一次**拉取自愈：分开拉会出现两个口径不同的分母。
  if (last.status === 'done' && last.total > 0
      && (byTypeAllZero(last.by_type) || byClassEmpty(last.by_class))) {
    const summaries = await fetchChangeSummaries(manager, last.batch_id)
    if (summaries) {
      update((st) => {
        if (st.last && st.last.batch_id === last.batch_id) {
          st.last.by_type = summaries.by_type
          st.last.by_class = summaries.by_class
        }
        return st
      })
      ctx.logger?.info?.(`ks-inspection: 旧批次 ${last.batch_id} 细分计数已自愈补齐`
        + `（五类分母 ${summaries.by_class.total} 条）`)
    }
  }

  startAutoInspectionTimer(ctx, manager)

  if (last.status !== 'running') return
  // Running from a previous process: try to adopt; anything but a live
  // healthy batch marks the run stale.
  try {
    const sess = await manager.ensureLive()
    const probe = await apiGet(
      originUrl(sess.port),
      `/api/v1/update/batch/${encodeURIComponent(last.batch_id)}`,
      { token: sess.token, timeoutMs: 10_000 },
    )
    if (probe.status === 200 && probe.body && probe.body.data) {
      const status = String(probe.body.data.status ?? '')
      if (status === 'running' || status === 'pending') {
        ctx.logger?.info?.(`ks-inspection: 接管上次未完成批次 ${last.batch_id}（${status}）`)
        adoptBatch(manager, ctx, last.batch_id, 'running')
        void schedulePersist()
        return
      }
      // Terminal since we last saw it → recall the final state.
      if (TERMINAL.has(status)) {
        ctx.logger?.info?.(`ks-inspection: 上次批次 ${last.batch_id} 已 ${status}，回收结果`)
        await finalizeBatch(manager, ctx, last.batch_id, status)
        void schedulePersist()
        return
      }
      // paused → leave as-is for the UI to show.
      void schedulePersist()
      return
    }
  } catch { /* engine unavailable -> stale below */ }
  s.stale_run = true
  void schedulePersist()
  ctx.logger?.warn?.(`ks-inspection: 上次批次 ${last.batch_id} 疑似中断（无法接管）`)
}

/** Register all four inspection routes; returns the combined disposer. */
export function registerKsInspectionRoutes(ctx, manager) {
  const disposers = [
    registerRunRoute(ctx, manager),
    registerSummaryRoute(ctx),
    registerSettingsRoutes(ctx),
    registerExportRoute(ctx, manager),
  ]
  return () => {
    stopAutoInspectionTimer()
    for (const dispose of disposers) dispose()
  }
}
