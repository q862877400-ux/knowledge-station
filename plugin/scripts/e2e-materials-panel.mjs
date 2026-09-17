/**
 * ks-dsh-plugin — scripts/e2e-materials-panel.mjs
 *
 * **真机端到端回归（材料面板）**：接一个已开的 CDP 浏览器，驱动 DSH Web GUI 的
 * 「设置 → 法规标准知识库 → 参考资料」，断言三件离线纯函数/离线冒烟**测不到**的事：
 *
 *   A. **面板真的能挂进设置界面并且不炸**：材料面板是首次被真实浏览器渲染的组件
 *      （它在设置侧栏里、与被批准的硬门绑在一起）。离线冒烟只跑得到纯函数与路由表，
 *      没有 React 渲染。A 断言：类目展开后 `参考资料项目` 控件出现，且整个过程
 *      **没有** `console.error` / 未捕获异常（崩了会把整个设置界面带走）。
 *
 *   B. **口子与硬门文案在位**：`评审是硬门` 必须出现在面板上——这句话是
 *      "谁批准了才进结论"的**用户可见承诺**，它一旦被改掉/删掉，用户会以为
 *      材料可以自动进结论。
 *
 *   C. **失败必须如实说（本脚本最重要的一条）**：材料面板的每个数据请求
 *      （`/ks/materials/*`）要么拿到 2xx，要么**界面上必须出现** `role="alert"`
 *      的 `操作失败：…`。**禁止**的组合是「请求失败 + 界面干净」——那等于把
 *      "读不到"伪装成"没有材料"，用户会照着空列表做判断（违反 P1 准确性）。
 *      这条在**主机路由未挂载**（DSH 进程启动早于本插件改动）时尤其重要：
 *      今天真机上就是这种状态（下面 D 会把它如实打印出来）。
 *
 *   D. **打印本次真机观察到的路由状态**（不是断言，是诊断）：`/ks/materials/*`
 *      逐条 URL + HTTP 状态。它直接告诉人"要重启哪一扇门"。
 *
 * 依赖：一个开了远程调试的 Chromium（Edge/Chrome）+ 一个已打开的 DSH Web GUI。
 * 默认 CDP 端口 9333、页面 URL 含 3080，可用环境变量覆盖：
 *     KS_E2E_CDP_PORT=9333  KS_E2E_URL_MATCH=3080  KS_E2E_NO_RELOAD=1
 *
 * ⚠ **本脚本按设计是只读的**：它只**打开**面板并观察渲染/网络，**绝不点**
 * 「新建项目」「扫描收件」「自采一条」「生成研究报告」「生成 PPT」——那些会写进
 * 用户**真实的知识库**（本项目拒绝为了测试去污染生产数据）。所以它**不覆盖 happy path**：
 * 端到端写路径由引擎侧测试（`tests/test_material_api.py` 的
 * `采集 → 待评审 → 检索不到 → 批准 → 检索到`）与离线替身 fetch 冒烟负责。
 * 要真机跑写路径，只能在**另建的数据目录**里跑一个独立实例，不在这里。
 *
 * **没有可连的浏览器时本脚本不算失败**：打印 SKIP 并以 0 退出（与 e2e-sidebar-pdf 同款，
 * 不进 `npm run smoke`，避免把真机依赖塞进离线门禁）。
 *
 * 用法：node scripts/e2e-materials-panel.mjs
 */
const PORT = Number(process.env.KS_E2E_CDP_PORT ?? 9333)
const URL_MATCH = process.env.KS_E2E_URL_MATCH ?? '3080'
const NO_RELOAD = process.env.KS_E2E_NO_RELOAD === '1'

const skip = (why) => { console.log(`SKIP  e2e-materials-panel: ${why}`); process.exit(0) }

let targets = null
try {
  const res = await fetch(`http://127.0.0.1:${PORT}/json/list`)
  targets = await res.json()
} catch (err) {
  skip(`CDP 端口 ${PORT} 连不上（${err && err.message ? err.message : String(err)}）`)
}
const page = (targets ?? []).find((t) => t.type === 'page' && String(t.url).includes(URL_MATCH))
if (!page) skip(`CDP 端口 ${PORT} 上没有 URL 含 "${URL_MATCH}" 的页面 target`)

const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok: ok === true, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail !== undefined ? ` — ${detail}` : ''}`)
}

let nextId = 0
const pending = new Map()
const consoleErrs = []
const ksRequests = []          // { url, status }
const ws = new WebSocket(page.webSocketDebuggerUrl)
ws.addEventListener('message', (e) => {
  const m = JSON.parse(typeof e.data === 'string' ? e.data : String(e.data))
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    consoleErrs.push(m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 200))
  }
  if (m.method === 'Runtime.exceptionThrown') consoleErrs.push('exception: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 200))
  if (m.method === 'Network.responseReceived') {
    const r = m.params.response
    if (/\/ks\/materials/.test(r.url)) ksRequests.push({ url: r.url.replace(/^https?:\/\/[^/]+/, ''), status: r.status })
  }
  if (m.id !== undefined && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id); pending.delete(m.id)
    m.error ? reject(new Error(m.error.message)) : resolve(m.result)
  }
})
await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j) })
const call = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++nextId; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params }))
})
const ev = async (expr) => {
  const r = await call('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 300))
  return r.result.value
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
await call('Runtime.enable')
// ⚠ **必须**禁缓存：插件 bundle 是 `import('/plugins/??…&rev=…')` 动态取的，
// `Page.reload({ ignoreCache: true })` 对它是**不够**的——2026-09-18 实测：
// 重新构建 `client.js` 后 reload，页面仍在跑**旧 bundle**，于是新加的断言假红
// （C3 找不到新文案），而真实原因只是浏览器内存缓存。禁掉之后当场变绿。
await call('Network.enable')
await call('Network.setCacheDisabled', { cacheDisabled: true })

// ---------------------------------------------------------------- 页面探针片段
const CLICK_SETTINGS = `(() => {
  const b = [...document.querySelectorAll('button')].find(x => x.offsetParent !== null
    && (x.getAttribute('aria-label') === '设置' || (x.textContent || '').trim() === '设置'))
  if (!b) return 'not-found'
  b.click(); return 'clicked'
})()`
const CLICK_KS_NAV = `(() => {
  const b = [...document.querySelectorAll('button,[role="button"],a')].find(x => x.offsetParent !== null
    && (x.textContent || '').replace(/\\s+/g, '').trim() === '法规标准知识库')
  if (!b) return 'not-found'
  b.click(); return 'clicked'
})()`
const OPEN_MATERIALS = `(() => {
  const s = [...document.querySelectorAll('summary')].find(x => x.offsetParent !== null
    && /^参考资料/.test((x.textContent || '').trim()))
  if (!s) return 'not-found'
  const d = s.parentElement
  if (d && d.tagName === 'DETAILS' && d.open) return 'already'
  s.click(); return 'clicked'
})()`
const PANEL_STATE = `(() => {
  const sel = document.querySelector('select[aria-label="参考资料项目"]')
  const alert = [...document.querySelectorAll('[role="alert"]')].filter(x => x.offsetParent !== null)
  const alerts = alert.map(x => (x.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160))
  const statuses = [...document.querySelectorAll('[role="status"]')].filter(x => x.offsetParent !== null)
    .map(x => (x.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160))
  const body = document.querySelector('[class*="settingsArea"]') || document.body
  const text = (body.textContent || '').replace(/\\s+/g, ' ')
  return JSON.stringify({
    panelMounted: sel !== null,
    optionCount: sel ? sel.options.length : 0,
    hardGate: text.includes('评审是硬门'),
    pickFirst: text.includes('先选一个项目'),
    alerts,
    statuses,
    hasNewProject: text.includes('新建项目'),
  })
})()`
const CLOSE_SETTINGS = `(() => {
  const b = [...document.querySelectorAll('button')].find(x => x.offsetParent !== null
    && (x.getAttribute('aria-label') === '设置' || (x.textContent || '').trim() === '设置'))
  if (b) { b.click(); return 'closed' }
  return 'not-found'
})()`

// ---------------------------------------------------------------- 驱动
if (!NO_RELOAD) {
  await call('Page.reload', { ignoreCache: true })
  await wait(9000)
}
consoleErrs.length = 0
ksRequests.length = 0

const opened = await ev(CLICK_SETTINGS)
if (opened !== 'clicked') { console.log(`SKIP  e2e-materials-panel: 找不到「设置」按钮（${opened}）`); ws.close(); process.exit(0) }
await wait(2500)

const nav = await ev(CLICK_KS_NAV)
check('A1 设置界面里有「法规标准知识库」入口', nav === 'clicked', nav)
await wait(2500)

const cat = await ev(OPEN_MATERIALS)
check('A2 能展开「参考资料」类目', cat === 'clicked' || cat === 'already', cat)
await wait(3500)

const state = JSON.parse(await ev(PANEL_STATE))
check('A3 参考资料面板已在真机渲染（参考资料项目控件出现）', state.panelMounted,
  `panelMounted=${state.panelMounted} optionCount=${state.optionCount}`)
check('B1 硬门文案在位（「评审是硬门」）', state.hardGate)
check('B2 新入口在位（「新建项目」/「先选一个项目」至少其一）', state.hasNewProject || state.pickFirst,
  `新建项目=${state.hasNewProject} 先选项目=${state.pickFirst}`)

// C. 失败必须如实说：任何 /ks/materials 请求失败 ⇒ 界面必须有 role="alert"
const failed = ksRequests.filter((r) => r.status >= 400)
const honest = state.alerts.some((t) => t.startsWith('操作失败：'))
check('C1 失败的请求没有被伪装成"没有材料"（界面出现 操作失败：…）',
  failed.length === 0 || honest,
  `失败请求 ${failed.length} 条 / 可见 alert ${state.alerts.length} 条`)
const succeeded = ksRequests.filter((r) => r.status >= 200 && r.status < 300)
check('C2 成功的项目列表请求确实喂进了下拉框（有项目时可选项 > 1）',
  succeeded.length === 0 || state.optionCount > 1 || honest,
  `2xx ${succeeded.length} 条 / optionCount=${state.optionCount}`)

// C3 是本战役"静默降级"那一族在**真机**上的护栏（2026-09-18 由本脚本抓出来）：
// `/ks/materials/tiers` 失败时，层级下拉只剩"当前值"一个选项。若面板不说话，
// 用户看到的是"这份材料只有一个层级可选"——请求失败被渲染成"功能就是这样"。
const tiersFailed = ksRequests.some((r) => /\/ks\/materials\/tiers/.test(r.url) && r.status >= 400)
const tiersHonest = state.statuses.some((t) => t.includes('来源层级清单'))
check('C3 层级清单失败没有被静默降级（界面出现「来源层级清单…没读到」）',
  !tiersFailed || tiersHonest,
  `tiers 失败=${tiersFailed} / 可见 status=${state.statuses.length} 条`)
if (tiersFailed && !tiersHonest) {
  console.log('      排查提示：先看 `Network.setCacheDisabled` 那段——')
  console.log('      若浏览器还在跑**旧 bundle**，C3 会假红（改的是代码、测的是缓存）。')
}

check('D  操作期间无 console.error / 未捕获异常', consoleErrs.length === 0,
  consoleErrs.slice(0, 2).join(' | ') || 'none')

await ev(CLOSE_SETTINGS)
ws.close()

// ---------------------------------------------------------------- 诊断打印（非断言）
console.log('\n-- 真机观察到的 /ks/materials 路由状态（诊断，非断言）--')
if (ksRequests.length === 0) console.log('   （面板本次没有发出任何 /ks/materials 请求）')
for (const r of ksRequests) console.log(`   ${String(r.status).padEnd(4)} ${r.url}`)
const bad = ksRequests.filter((r) => r.status >= 400)
if (bad.length > 0) {
  console.log('   ↑ 404 说明**主机那半没有挂载**（plugin/src 是 DSH 进程启动时载入的）：')
  console.log('     要重启 DSH 进程（本插件的宿主）才会注册 /ks/materials* 路由。')
}

const failedChecks = results.filter((r) => !r.ok)
console.log(`\n== e2e-materials-panel ${failedChecks.length === 0 ? 'PASS' : 'FAIL'} (${results.length - failedChecks.length}/${results.length}) ==`)
process.exit(failedChecks.length === 0 ? 0 : 1)
