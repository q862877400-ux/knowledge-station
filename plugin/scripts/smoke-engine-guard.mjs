/**
 * ks-dsh-plugin — scripts/smoke-engine-guard.mjs
 *
 * 批3「引擎守护」离线冒烟（问题清单 #3 + #12）。全部纯逻辑/假定时器，不 spawn
 * 真引擎、不碰真实会话文件（$KS_DATA_DIR 指向临时目录）：
 *
 *  1. idle 默认 30min（15→30 批3），配置可覆盖，0/负值=禁用
 *  2. keepalive：钩子返回 true → 不杀、续满窗口；钩子抛错 → 按 false 走正常回收；
 *     钩子只在「杀自己 spawn 的引擎」分支被问到（外部引擎永不被杀）
 *  3. stale 会话：会话文件指向死端口时，ensureLive 前把死会话改名留档
 *     （engine.session.json.stale-<pid>-<ts>），且一次生命周期只留一份
 *  4. 并发合并：两个并发 ensureLive 只 spawn 一次（共享 promise）
 *
 * Run: node scripts/smoke-engine-guard.mjs   (exit 0 = pass)
 */
import { mkdtemp, writeFile, readdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

// 隔离数据目录（engine.session.json 落点）——必须在导入 src/engine.js 之前。
const dataDir = await mkdtemp(join(tmpdir(), 'ks-engine-guard-'))
process.env.KS_DATA_DIR = dataDir

const { EngineManager, sessionFilePath } = await import(
  new URL('../src/engine.js', import.meta.url).href
)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ============================================== 1. idle 默认与覆盖 */
{
  const def = new EngineManager({})
  check('idle default = 30min (批3)', def.idleTimeoutMs === 30 * 60 * 1000,
    `got ${def.idleTimeoutMs}`)

  const custom = new EngineManager({ idleTimeoutMs: 5 * 60 * 1000 })
  check('idle configurable', custom.idleTimeoutMs === 5 * 60 * 1000)

  const off = new EngineManager({ idleTimeoutMs: 0 })
  check('idle 0 = disabled (armIdle no-op)', off.idleTimeoutMs === 0)
  off.armIdle()
  check('disabled idle arms no timer', off._idleTimer === null)
}

/* ============================================== 2. keepalive 分支 */
{
  // 用假 child + ownsCurrent 模拟「我 spawn 的引擎在跑」；idle 窗口压到 20ms。
  const m = new EngineManager({ idleTimeoutMs: 20 })
  m.ownsCurrent = true
  m.child = { pid: 424242 }       // 假进程句柄（killOwned 只在有 pid 时用 killPid，
                                  // 这里手动拦截 killOwned 而不真杀）
  let killed = 0
  m.killOwned = () => { killed += 1; m.ownsCurrent = false; m.child = null }

  // 2a. 钩子说续 → 不杀
  m.keepAliveCheck = () => true
  m.armIdle()
  await new Promise((r) => setTimeout(r, 90))
  check('keepalive=true → engine NOT killed', killed === 0, `killed=${killed}`)
  check('keepalive=true → timer re-armed', m._idleTimer !== null)

  // 2b. 钩子说杀 → 杀
  m.keepAliveCheck = () => false
  await new Promise((r) => setTimeout(r, 90))
  check('keepalive=false → engine killed', killed === 1, `killed=${killed}`)
  check('after kill → timer cleared', m._idleTimer === null)

  // 2c. 钩子抛错 → 按 false（回收照常，绝不因 keepalive 挂掉）
  const m2 = new EngineManager({ idleTimeoutMs: 20 })
  m2.ownsCurrent = true
  m2.child = { pid: 424243 }
  let killed2 = 0
  m2.killOwned = () => { killed2 += 1; m2.ownsCurrent = false; m2.child = null }
  m2.keepAliveCheck = () => { throw new Error('boom') }
  m2.armIdle()
  await new Promise((r) => setTimeout(r, 90))
  check('keepalive throws → treated as false (kill proceeds)', killed2 === 1, `killed=${killed2}`)

  // 2d. 钩子非函数 → 正常回收
  const m3 = new EngineManager({ idleTimeoutMs: 20 })
  m3.ownsCurrent = true
  m3.child = { pid: 424244 }
  let killed3 = 0
  m3.killOwned = () => { killed3 += 1; m3.ownsCurrent = false; m3.child = null }
  m3.keepAliveCheck = 'not a function'
  m3.armIdle()
  await new Promise((r) => setTimeout(r, 90))
  check('keepAliveCheck non-function → normal kill', killed3 === 1, `killed=${killed3}`)

  // 2e. 外部引擎（ownsCurrent=false）→ 钩子根本不该被问、也永不被杀
  const m4 = new EngineManager({ idleTimeoutMs: 20 })
  m4.ownsCurrent = false
  m4.child = null
  let asked = 0
  m4.keepAliveCheck = () => { asked += 1; return true }
  let killed4 = 0
  m4.killOwned = () => { killed4 += 1 }
  m4.armIdle()
  await new Promise((r) => setTimeout(r, 90))
  check('external engine → keepAliveCheck never consulted', asked === 0, `asked=${asked}`)
  check('external engine → never killed', killed4 === 0)
}

/* ============================================== 3. stale 会话留档 */
{
  // 写一份指向死端口的假会话文件；spawnEngine 用假实现（不真起引擎）。
  const sessionFile = sessionFilePath()
  await writeFile(sessionFile, JSON.stringify({
    port: 59999, token: 'tok', pid: 199999, started_at: '2026-09-12T00:00:00',
  }), 'utf8')

  const m = new EngineManager({ probeTimeoutMs: 200 })
  m.spawnEngine = async () => ({ port: 48000, token: 'tok2', pid: 200001, spawnedByUs: true })

  const s1 = await m.ensureLive()
  check('stale session: spawn proceeds', s1.port === 48000)

  const entries = await readdir(dataDir)
  const staleFiles = entries.filter((n) => n.startsWith('engine.session.json.stale-'))
  check('stale session archived once', staleFiles.length === 1,
    `files=${JSON.stringify(staleFiles)}`)
  check('stale archive carries dead pid', /199999/.test(staleFiles[0] ?? ''), staleFiles[0])

  // 第二次（会话文件已不在）→ 不再留档
  await writeFile(sessionFile, JSON.stringify({
    port: 59998, token: 'tok', pid: 199998, started_at: '2026-09-12T00:00:00',
  }), 'utf8')
  await m.ensureLive()
  const entries2 = await readdir(dataDir)
  const stale2 = entries2.filter((n) => n.startsWith('engine.session.json.stale-'))
  check('second stale in one manager lifetime → no extra archive', stale2.length === 1,
    `files=${JSON.stringify(stale2)}`)
}

/* ============================================== 4. 并发合并 */
{
  const m = new EngineManager({})
  let spawns = 0
  m.spawnEngine = async () => {
    spawns += 1
    await new Promise((r) => setTimeout(r, 60))
    return { port: 48001, token: 'tok3', pid: 200002, spawnedByUs: true }
  }
  const [a, b] = await Promise.all([m.ensureLive(), m.ensureLive()])
  check('concurrent ensureLive shares ONE spawn', spawns === 1, `spawns=${spawns}`)
  check('both callers get the session', a.port === 48001 && b.port === 48001)

  // 串行调用（无并发窗口）各自 spawn——语义不变
  const m2 = new EngineManager({})
  let spawns2 = 0
  m2.spawnEngine = async () => { spawns2 += 1; return { port: 48002, token: 't', pid: 1, spawnedByUs: true } }
  await m2.ensureLive()
  m2._spawning = null
  await m2.ensureLive()
  check('sequential ensureLive each spawns (no false sharing)', spawns2 === 2, `spawns=${spawns2}`)
}

/* ============================================== 汇总 */
const failed = results.filter((r) => !r.ok)
console.log(`\n== engine-guard smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} ` +
  `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
