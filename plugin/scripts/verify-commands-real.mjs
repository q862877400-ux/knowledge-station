/**
 * verify-commands-real.mjs — 用 **DSH 自己的 CommandRuntime** 验证两条斜杠命令（真机前最后一道离线闸）
 *
 * 为什么不能只靠 smoke-effect-tool：那里的 `ctx.commands` 是假桩，无法证明 host 侧
 * `normalizeDefinition` 会接受我的定义。而 `register()` 校验失败是**抛异常**，被
 * registerKsChatModeCommands 的逐条兜底接住后只留一条 console.error —— 也就是说
 * 定义写错的症状是「菜单里静悄悄没有这条命令」，靠点界面才发现。所以这里挂真实注册表。
 *
 * 覆盖：
 *   1. 真实 register() 接受两条定义（disposer 数 = 2，且没有触发任何兜底日志）
 *   2. ctx.commands.list(agent) —— 即 `/` 菜单的数据源 —— 恰好含 forensic / bookmarks
 *   3. 真实派发 ctx.commands.execute(agent, '/forensic …')：开关语义 + 会话级状态
 *   4. 会话日志出现 command/run + command/done（证明命令不进模型、不产生对话消息）
 *   5. dispose 后两条命令从表里消失（不泄漏）
 *
 * 运行（必须从 DSH 检出根目录跑，让 tsx 读到 tsconfig.base.json 的 paths）：
 *   cd "D:\AI\DSH\deepseek-harness"
 *   npx tsx "D:\AI\work space\zcode\plugin\scripts\verify-commands-real.mjs"
 */

import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

// 状态隔离：绝不碰 %APPDATA%\KnowledgeStation\ks-chatmode.json（真实用户状态）
process.env.KS_CHATMODE_DIR = await mkdtemp(join(tmpdir(), 'ks-cmd-real-'))

const { Context } = await import('@deepseek-ai/cordis')
const { default: CommandRuntime } = await import('@deepseek-ai/dsh-commands')
const { default: SessionStore, SessionId } = await import('@deepseek-ai/dsh-session')
const { createScope } = await import('@deepseek-ai/dsh-scope')

const chatmodeUrl = pathToFileURL('D:/AI/work space/zcode/plugin/src/chatmode.js').href
const { registerKsChatModeCommands, getMode, effectiveChatMode, forensicPromptFor } =
  await import(chatmodeUrl)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

// 捕获兜底日志：真机上它意味着「命令静默缺失」，这里必须为空
const guardLogs = []
const realError = console.error
console.error = (...args) => { guardLogs.push(args.map(String).join(' ')); realError(...args) }

console.log('=== 真实 CommandRuntime 验证：/forensic · /bookmarks · /materials ===\n')

const ctx = new Context()
await ctx.plugin(SessionStore)
await ctx.plugin(CommandRuntime)

const session = ctx.sessions.create(SessionId('verify-commands-real'))
const agent = { id: session.id, session }
let scope
await ctx.plugin(Object.assign((inner) => { scope = createScope(inner, agent) }, { inject: ['commands'] }))

// 走插件真正的那段注册代码（含逐条兜底）
const disposers = registerKsChatModeCommands(ctx, { parentSessionOf: () => undefined })

// 期望条数**跟着声明走**，别写死 2：加命令时这里不该变红，
// 该红的是新命令自己的那组断言（2026-09-17 加 /materials 时踩过一次）。
const expectedNames = ['bookmarks', 'forensic', 'materials']
check('real register() accepted EVERY declared definition',
  disposers.length === expectedNames.length, `${disposers.length} disposers`)
check('no guard fallback fired (no silently-missing command)', guardLogs.length === 0,
  guardLogs.join(' | ') || 'clean')

const listed = ctx.commands.list(agent)
const names = listed.map((d) => d.name)
check('the ` / ` menu source lists every declared command', names.join(',') === expectedNames.join(','),
  names.join(',') || '(none)')
check('every descriptor carries a description and an input hint',
  listed.length === expectedNames.length && listed.every((d) => typeof d.description === 'string'
    && d.description.length > 0 && typeof d.input?.hint === 'string' && d.input.hint.length > 0),
  JSON.stringify(listed.map((d) => ({ n: d.name, hint: d.input?.hint }))))

const signal = new AbortController().signal
const fire = (line) => ctx.commands.execute(agent, line, [], signal)

// ---------------------------------------------------------------- 真实派发
const on = await fire('/forensic')
check('/forensic (no arg) toggles ON and reports success',
  on?.result?.kind === 'success' && /已开启/.test(on.result.text ?? ''), String(on?.result?.text).slice(0, 70))
check('state really flipped in the session-scoped store', getMode(session.id).forensic === true)

const status = await fire('/forensic status')
check('/forensic status reports without changing',
  status?.result?.kind === 'success' && /已开启/.test(status.result.text ?? '')
  && getMode(session.id).forensic === true, String(status?.result?.text).slice(0, 60))

const bm = await fire('/bookmarks')
check('/bookmarks turns on BOTH flags (child depends on its parent)',
  bm?.result?.kind === 'success' && getMode(session.id).bookmarksOnly === true
  && getMode(session.id).forensic === true, String(bm?.result?.text).slice(0, 50))
check('host-side effective mode reflects it (single source of truth)',
  effectiveChatMode(session.id).forensic === true && effectiveChatMode(session.id).bookmarksOnly === true)

const bmOff = await fire('/bookmarks off')
check('/bookmarks off clears only the child flag',
  bmOff?.result?.kind === 'success' && getMode(session.id).bookmarksOnly === false
  && getMode(session.id).forensic === true, String(bmOff?.result?.text).slice(0, 50))

const zh = await fire('/forensic 关闭')
check('/forensic accepts a Chinese argument', getMode(session.id).forensic === false, String(zh?.result?.text).slice(0, 40))

const bad = await fire('/forensic maybe')
check('an unknown argument is a loud error, never a silent no-op',
  bad?.result?.kind === 'error' && /无法识别/.test(bad.result.text ?? ''), String(bad?.result?.text).slice(0, 60))

// ------------------------------------------------- /materials（2026-09-17 材料平面）
const matStatus0 = await fire('/materials status')
check('/materials status on an unbound session says so (no silent success)',
  matStatus0?.result?.kind === 'success'
  && /未绑定/.test(matStatus0.result.text ?? ''), String(matStatus0?.result?.text).slice(0, 60))

const matUse = await fire('/materials use prj_REAL 真实项目')
check('/materials use binds the session-scoped store',
  matUse?.result?.kind === 'success' && getMode(session.id).materialProjectId === 'prj_REAL'
  && getMode(session.id).materialProjectName === '真实项目', String(matUse?.result?.text).slice(0, 60))
check('binding a project implies forensic in the effective mode (single source of truth)',
  effectiveChatMode(session.id).materialProjectId === 'prj_REAL'
  && effectiveChatMode(session.id).forensic === true)
check('the host prompt section carries the material rules when bound',
  forensicPromptFor(session.id).includes('【参考资料项目】')
  && forensicPromptFor(session.id).includes('真实项目'))

const matWrong = await fire('/materials use bmf_FOLDER')
check('/materials rejects a folder id as a project id (actionable, not silent)',
  matWrong?.result?.kind === 'error' && /prj_/.test(matWrong.result.text ?? ''),
  String(matWrong?.result?.text).slice(0, 70))

const matOff = await fire('/materials off')
check('/materials off unbinds the session',
  matOff?.result?.kind === 'success' && getMode(session.id).materialProjectId === null,
  String(matOff?.result?.text).slice(0, 50))
check('the material prompt section disappears after unbinding',
  !forensicPromptFor(session.id).includes('【参考资料项目】'))

// 所有派发收进一个列表：生命周期事件数**由它推**，加命令时不用改魔数
const dispatched = [on, status, bm, bmOff, zh, bad,
  matStatus0, matUse, matWrong, matOff]

// ------------------------------------------------- 命令不进模型（会话日志证据）
// ⚠ DSH 0.1.6 把 Session 上的 `events` 数组换成了 `ownEvents()`（`events` 变 undefined，
//   于是本闸在升级后直接 TypeError 崩掉 —— 2026-09-17 实测）。这里做兼容读取：
//   0.1.6+ 用 ownEvents()（本会话自己的事件，不含 fork 继承），旧版回退到 events。
const sessionEvents = typeof session.ownEvents === 'function' ? session.ownEvents() : session.events
const lifecycle = sessionEvents.filter((e) => e.type === 'command/run' || e.type === 'command/done')
check('every dispatch logged command/run + command/done (host-side, no model turn)',
  lifecycle.length === dispatched.length * 2 && sessionEvents.every((e) => e.type !== 'turn/start'),
  `${lifecycle.length} lifecycle events for ${dispatched.length} dispatches`)

// ---------------------------------------------------------------- 不泄漏
for (const dispose of disposers) dispose()
check('dispose removes every command from the registry',
  ctx.commands.list(agent).length === 0, String(ctx.commands.list(agent).length))
check('a disposed command no longer dispatches',
  (await fire('/forensic')) === undefined)

console.error = realError

const failed = results.filter((r) => !r.ok)
console.log(`\n== ${results.length - failed.length}/${results.length} passed ==`)
if (failed.length > 0) {
  for (const f of failed) console.log(`FAILED: ${f.name}`)
  process.exitCode = 1
}
