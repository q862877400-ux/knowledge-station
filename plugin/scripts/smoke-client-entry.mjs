/**
 * ks-dsh-plugin — scripts/smoke-client-entry.mjs
 *
 * 客户端半 `apply(ctx)` 的**门面契约**冒烟。为什么单独写它（verifier 三轮 P0）：
 * DSH 动态客户端插件拿到的不是内核 cordis ctx，而是
 * `packages/extensions/cordis-client-runner/src/client/guard.ts` 的受限门面——
 *   - 白名单 verb 只有 effect/on/once/provide/timeout/interval/setTimeout/setInterval/
 *     throttle/debounce（`CTX_VERBS`）；
 *   - 读**任何**其它属性（包括 `ctx.betterSidebar` 这种未声明服务、以及 `ctx.inject`
 *     这种不在白名单的框架方法）→ `denyRead` → **直接抛**
 *     `dynamic ctx does not expose "..."`；
 *   - `ctx.get(name)` 是允许的（`readService(name, false)`，不要求声明），读不到返回 undefined。
 * 上一轮整改里我在 `apply()` 里写了 `typeof ctx.inject === 'function'`，在真机门面上
 * 直接抛错 → 整块客户端半（tab + 设置栏目 + 📜 查法规模式开关）全都不激活。
 * 本冒烟用一个**逐条镜像**该门面语义的假 ctx 调 `apply()`，把这类"读了不该读的属性"
 * 变成开发期红灯。
 *
 * 覆盖：
 *   1. 门面语义自证（未声明属性抛、get 返回 undefined、白名单 verb 可用）；
 *   2. better-sidebar **不存在** → apply 不抛；不注册任何 tab；
 *   3. better-sidebar **存在** → apply 不抛；3 个 tab（证据 PDF / 收藏 / settings
 *      卡）+ 设置栏目全部注册（效力报告/入库预览 2026-11 迁入设置栏目，不再是 tab）；
 *   4. `inject` 声明只含官方服务（不把第三方插件当门禁）。
 *
 * 用法：node scripts/smoke-client-entry.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ---------------------------------------------------- 浏览器全局最小桩 */
const docListeners = []
/** 真的记账的 document 桩：add/remove 都按 (type, fn) 记账，才能测"监听器有没有泄漏"。 */
const docHandlers = new Map()
const listenerCount = (type) => (docHandlers.get(type) ?? new Set()).size
globalThis.document = {
  visibilityState: 'visible',
  addEventListener(type, fn) {
    if (!docHandlers.has(type)) docHandlers.set(type, new Set())
    docHandlers.get(type).add(fn)
    docListeners.push(type)
  },
  removeEventListener(type, fn) {
    docHandlers.get(type)?.delete(fn)
  },
}
const windowHandlers = new Map()
globalThis.window = {
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  addEventListener(type, fn) {
    if (!windowHandlers.has(type)) windowHandlers.set(type, new Set())
    windowHandlers.get(type).add(fn)
  },
  removeEventListener(type, fn) { windowHandlers.get(type)?.delete(fn) },
}

/* ---------------------------------------------------- 打包 client/entry */
const entryPath = join(pluginRoot, '.smoke-entry-apply.mjs')
const outPath = join(pluginRoot, '.smoke-entry-apply.bundle.mjs')
const stubDir = await mkdtemp(join(tmpdir(), 'ks-entry-stub-'))
const pdfStubPath = join(stubDir, 'pdfjs-stub.mjs')
// pdf.js 在 import 期就摸浏览器全局（DOMMatrix 等），而本冒烟测的是 **apply() 怎么用 ctx**，
// 不是 PDF 渲染。把 pdfjs-dist 换成桩（同时也让这个冒烟保持毫秒级）。
await writeFile(pdfStubPath, [
  'export const GlobalWorkerOptions = {}',
  'export const version = "0.0.0-smoke-stub"',
  'export const getDocument = () => ({ promise: Promise.reject(new Error("stub")), destroy: () => {} })',
  'export class RenderingCancelledException extends Error {}',
  'export default { GlobalWorkerOptions, version, getDocument, RenderingCancelledException }',
  '',
].join('\n'), 'utf8')
await writeFile(entryPath,
  "export { apply, inject } from './client/entry.ts'\n", 'utf8')
try {
  await build({
    entryPoints: [entryPath], bundle: true, platform: 'node', format: 'esm',
    outfile: outPath, absWorkingDir: pluginRoot, jsx: 'automatic',
    external: ['react', 'react-dom'],
    alias: { 'pdfjs-dist': pdfStubPath },
    loader: { '.tsx': 'tsx', '.ts': 'ts' }, logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  await rm(entryPath, { force: true })
  await rm(stubDir, { recursive: true, force: true })
  process.exit(1)
}
await rm(entryPath, { force: true })
const entry = await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })
await rm(stubDir, { recursive: true, force: true })

/** guard.ts 的 CTX_VERBS / TIMER_VERBS 逐条镜像。 */
const CTX_VERBS = new Set([
  'effect', 'on', 'once', 'provide', 'timeout', 'interval',
  'setTimeout', 'setInterval', 'throttle', 'debounce',
])
const TIMER_VERBS = new Set(['timeout', 'interval', 'setTimeout', 'setInterval', 'throttle', 'debounce'])

/**
 * 造一个门面 ctx：语义与 cordis-client-runner 的 guard **逐条对齐**——
 *  - 白名单 verb 可读可用，但 **timer verb 需要声明 `timer`**（guard.ts:25/219）；
 *  - `get` 可读（guard.ts:214 `readService(name, false)`，不要求声明）；
 *  - `slots` 服务的 `register` 校验 `name`（guard.ts:104-112 同款）；
 *  - 其余属性（含未声明服务、`inject` 这类框架成员）一律**抛**。
 * 假门面若比真门面宽松，这个冒烟就会漏掉真实违规（verifier 四轮实测出过这类失真）。
 */
function buildFacade({ withBetterSidebar = false, withTimer = false } = {}) {
  const injected = []
  const registered = []
  const slots = {
    inject(key, cb) { injected.push(key); cb(); return () => {} },
    register(options, component) {
      if (typeof options?.name !== 'string' || options.name.length === 0) {
        throw new Error('slots.register options need a string `name`')
      }
      registered.push({ options, component })
      return () => {}
    },
  }
  const declared = new Set(['slots'])
  if (withTimer) declared.add('timer')
  const makeBs = () => ({
    tabs: [],
    registerTab(descriptor) { this.tabs.push(descriptor); return () => {} },
    openTab() {},
    updateTab() {},
    activateTab() {},
    closeTab() {},
    isTabEnabled: () => true,
    getPrefs: () => ({}),
    version: '0.18.0',
    features: ['tabMeta', 'updateTab', 'stateSubscription', 'pluginSettings', 'urlTarget'],
    getSnapshot: () => ({ width: 400, tabs: [] }),
    subscribeState: () => () => {},
  })
  // 可变持有者：用来模拟"better-sidebar 在我们 apply 之后才激活"
  const bsRef = { current: withBetterSidebar ? makeBs() : null }
  const services = { slots }
  const denyRead = (prop) => {
    throw new Error(`dynamic ctx does not expose "${prop}"`)
  }
  const denyTimer = () => {
    throw new Error('service "timer" is not declared by your plugin')
  }
  const effects = []
  const listeners = []
  const facade = new Proxy({}, {
    get(_t, prop) {
      if (prop === 'get') {
        return (name) => {
          if (name === 'betterSidebar') return bsRef.current ?? undefined
          return declared.has(name) ? services[name] ?? undefined : undefined
        }
      }
      if (typeof prop !== 'string') return undefined
      if (CTX_VERBS.has(prop)) {
        return (...args) => {
          // 与 guard.ts:217-223 同构：timer verb 未声明 timer 时**调用即抛**
          if (TIMER_VERBS.has(prop) && !declared.has('timer')) return denyTimer()
          if (prop === 'effect') {
            const disposer = args[0]()
            effects.push(disposer)
            return disposer
          }
          if (prop === 'on') {
            listeners.push(args)
            return () => {}
          }
          if (TIMER_VERBS.has(prop)) return Reflect.apply(setTimeout, globalThis, args)
          return undefined
        }
      }
      if (!declared.has(prop)) denyRead(prop)
      return services[prop]
    },
    has: (_t, prop) => prop === 'get'
      || (typeof prop === 'string'
        && ((CTX_VERBS.has(prop) && (!TIMER_VERBS.has(prop) || declared.has('timer')))
          || declared.has(prop))),
    set: () => { throw new Error('dynamic ctx is read-only') },
  })
  /** 模拟"服务此刻才被提供"：置入服务并发出 cordis 的 internal/service 事件。 */
  const provideBetterSidebar = () => {
    bsRef.current = makeBs()
    for (const [event, listener] of listeners) {
      if (event === 'internal/service') listener('betterSidebar', bsRef.current)
    }
    return bsRef.current
  }
  /** 模拟服务被撤销：cordis 同样发 internal/service，但 value 为 undefined。 */
  const unprovideBetterSidebar = () => {
    bsRef.current = null
    for (const [event, listener] of listeners) {
      if (event === 'internal/service') listener('betterSidebar', undefined)
    }
  }
  return {
    facade, slots, injected, registered, bsHandlers: bsRef, effects, listeners,
    provideBetterSidebar, unprovideBetterSidebar,
  }
}

/* ---------------------------------------------------- 1. 门面语义自证 */
{
  const { facade } = buildFacade({})
  let threw = null
  try { void facade.inject } catch (error) { threw = error }
  check('facade mirror: reading an undeclared/framework property really throws',
    threw !== null && /does not expose "inject"/.test(String(threw?.message)),
    String(threw?.message ?? 'no throw').slice(0, 60))
  check('facade mirror: ctx.get on an absent service returns undefined (no throw)',
    facade.get('betterSidebar') === undefined)
  check('facade mirror: whitelisted verbs are callable',
    typeof facade.effect === 'function' && typeof facade.on === 'function')
  check('facade mirror: `in` does not advertise undeclared properties',
    !('inject' in facade) && !('betterSidebar' in facade))
  // timer verb 必须声明 timer（guard.ts:25/219）——旧假门面在这里比真门面宽松，
  // 会把"没声明 timer 却用了 ctx.setTimeout"这类真机会抛的写法放过去
  let timerThrew = null
  try { facade.setTimeout(() => {}, 1); } catch (error) { timerThrew = error }
  check('facade mirror: timer verbs throw without declaring timer',
    timerThrew !== null && /timer/.test(String(timerThrew?.message)),
    String(timerThrew?.message ?? 'no throw').slice(0, 50))
  check('facade mirror: `in` hides timer verbs without declaring timer',
    !('setTimeout' in facade))
  let regThrew = null
  try { facade.slots.register({}, () => null) } catch (error) { regThrew = error }
  check('facade mirror: slots.register rejects a missing name (guard.ts:104-112)',
    regThrew !== null && /name/.test(String(regThrew?.message)),
    String(regThrew?.message ?? 'no throw').slice(0, 50))
}

/* ---------------------------------------------------- 2. 无 better-sidebar */
{
  const built = buildFacade({})
  let error = null
  try { entry.apply(built.facade) } catch (e) { error = e }
  check('apply() does NOT throw when better-sidebar is absent (P0 regression guard)',
    error === null, String(error?.message ?? '').slice(0, 90))
  check('the client half no longer touches the input dock (dock UI deleted 2026-10)',
    !built.injected.includes('conversation.input.dock'),
    built.injected.join(',') || '(none)')
  check('no tab and no settings column are registered without better-sidebar',
    built.registered.length === 0,
    built.registered.map((r) => String(r.options?.id)).join(',') || '(none)')
}

/* ---------------------------------------------------- 3. 有 better-sidebar */
{
  const built = buildFacade({ withBetterSidebar: true })
  let error = null
  try { entry.apply(built.facade) } catch (e) { error = e }
  const bsHandlers = built.bsHandlers.current
  check('apply() does not throw when better-sidebar is present',
    error === null, String(error?.message ?? '').slice(0, 90))
  check('nothing is injected into the input dock (slash commands replaced it)',
    !built.injected.includes('conversation.input.dock'), built.injected.join(','))
  check('three tabs registered (PDF / 收藏 / settings card; 效力报告+入库预览已迁设置)',
    bsHandlers.tabs.length === 3,
    bsHandlers.tabs.map((t) => t.id).join(','))
  check('the PDF tab claims ks evidence links via urlTarget',
    typeof bsHandlers.tabs[0]?.urlTarget === 'function'
    && bsHandlers.tabs[0].urlTarget(new URL('http://127.0.0.1:1/__ks_evidence__?doc=x')) === true)
  check('设置栏目 (settings.section) registered too',
    built.injected.includes('settings.section'), built.injected.join(','))
  check('the click interception is installed globally (evidence links)',
    docListeners.includes('click'))
  check('tab ids are the documented ones (no ks:report / ks:ingest — migrated into settings)',
    bsHandlers.tabs.map((t) => t.id).join(',') === 'ks:pdf,ks:bookmarks,ks:settings',
    bsHandlers.tabs.map((t) => t.id).join(','))
  check('the probe registered a disposer (timer can be cleaned on dispose)',
    built.effects.filter((fn) => typeof fn === 'function').length >= 2,
    `disposers=${built.effects.filter((fn) => typeof fn === 'function').length}`)
}

/* ---------------------------- 4. better-sidebar 迟到：事件驱动重探（本轮新机制） */
{
  const built = buildFacade({})
  entry.apply(built.facade)
  check('late better-sidebar: nothing registered while it is absent',
    built.registered.length === 0, `registered=${built.registered.length}`)
  check('late better-sidebar: the probe subscribed to internal/service',
    built.listeners.some(([event]) => event === 'internal/service'),
    built.listeners.map(([e]) => String(e)).join(','))
  const bs = built.provideBetterSidebar() // 服务此刻才提供 → 触发 internal/service
  check('late better-sidebar: tabs register the moment the service appears',
    bs.tabs.length === 3 && built.injected.includes('settings.section'),
    `tabs=${bs.tabs.length} injected=${built.injected.join(',')}`)
  check('late better-sidebar: the settings column is registered exactly once',
    built.registered.filter((r) => r.options?.id === 'ks-dsh-plugin').length === 1,
    built.registered.map((r) => String(r.options?.id)).join(','))

  // 服务被撤销（better-sidebar 卸载/热重载）→ 复位；再提供时 tab 必须重新出现
  // （verifier 五轮 P2-4：旧实现 tabsRegistered 一旦置位永不回退）
  // 注意 click 监听的绝对条数含**别的用例块**留下的，所以这里只比对本次 cycle 的增量。
  const clicksBefore = listenerCount('click')
  built.unprovideBetterSidebar()
  check('service unprovide: the old surfaces effect is disposed (no leaked click listener)',
    listenerCount('click') === clicksBefore - 1,
    `before=${clicksBefore} after=${listenerCount('click')}`)
  const again = built.provideBetterSidebar()
  check('service re-provide: tabs come back after an unprovide/re-provide cycle',
    again.tabs.length === 3, `tabs=${again.tabs.length}`)
  check('service re-provide: exactly one click listener again (no accumulation)',
    listenerCount('click') === clicksBefore, `clicks=${listenerCount('click')}`)
}

/* ---------------------------- 4b. probe cleanup: dispose 后事件不再注册任何东西 */
{
  const built = buildFacade({})
  entry.apply(built.facade)
  const before = built.registered.length
  // 跑掉探针登记的 disposer（模拟 fiber 撤销）
  for (const fn of built.effects) if (typeof fn === 'function') fn()
  const late = built.provideBetterSidebar() // 撤销之后再发 internal/service
  check('after dispose the probe registers nothing on a late service event',
    late.tabs.length === 0 && built.registered.length === before,
    `tabs=${late.tabs.length} registered=${built.registered.length}`)
}

/* ---------------------------------------------------- 5. inject 声明 */
check('inject declares only official services (no third-party hard gate)',
  Array.isArray(entry.inject) && entry.inject.length === 1 && entry.inject[0] === 'slots',
  JSON.stringify(entry.inject))

const failed = results.filter((r) => !r.ok)
console.log(`\n== client-entry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
