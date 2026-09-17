/**
 * ks-dsh-plugin — scripts/e2e-sidebar-pdf.mjs
 *
 * **真机端到端回归**（不是离线冒烟）：接一个已开的 CDP 浏览器，驱动右侧栏 PDF 阅读器，
 * 断言三件离线纯函数测不到的事：
 *
 *   A. **翻页模式切换不得卸载文档**（2026-09-17 抓到的 P0）：
 *      从「文件目录」打开的 tab **没有地址**（tab.path 为空）。而 KsEvidenceTab 里那个
 *      "Re-parse evidence" effect 曾在依赖数组里放 `loadEvidence`，其身份随
 *      renderPage←pagingMode/zoom/box 变化 → 点一下「单页」就被无关的身份变化触发 →
 *      重新解析出 ev=null → evidence.current=null → 连 pdfDoc.destroy() 一起把文档卸掉，
 *      阅读器回到空态且切回「连续」也不恢复。修法：该 effect 只依赖 [tab.path, tab.meta]
 *      （它的职责就是"地址变了才重解析"），调用经 loadEvidenceRef 取最新实现。
 *      **这条只能真机测**——离线冒烟里没有 React 渲染与 effect 依赖图。
 *
 *   B. **自适应 = 宽度铺满**：首页 canvas 宽 == 容器内容宽（clientWidth − 24），
 *      且不产生横向溢出（用户 2026-09-17 裁定"宽度铺满，高度不用管"）。
 *
 *   C. **滑块如实反映缩放**：range input 的 value == title 里的百分比（step 必须为 1；
 *      step=5 会把非 5 倍数吸附掉，导致 thumb 与 label 不一致 —— 同日修的 P1）。
 *
 * 依赖：一个开了远程调试的 Chromium（Edge/Chrome）+ 一个已打开的 DSH Web GUI。
 * 默认 CDP 端口 9333、页面 URL 含 3080，可用环境变量覆盖：
 *     KS_E2E_CDP_PORT=9333  KS_E2E_URL_MATCH=3080
 *
 * **没有可连的浏览器时本脚本不算失败**：打印 SKIP 并以 0 退出（保持可选的定位，
 * 不进 `npm run smoke`，避免把真机依赖塞进离线门禁）。
 *
 * 用法：node scripts/e2e-sidebar-pdf.mjs
 */
const PORT = Number(process.env.KS_E2E_CDP_PORT ?? 9333)
const URL_MATCH = process.env.KS_E2E_URL_MATCH ?? '3080'

const skip = (why) => { console.log(`SKIP  e2e-sidebar-pdf: ${why}`); process.exit(0) }

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
const check = (name, ok, detail) => { results.push({ name, ok: ok === true, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail !== undefined ? ` — ${detail}` : ''}`) }

let nextId = 0
const pending = new Map()
const consoleErrs = []
const ws = new WebSocket(page.webSocketDebuggerUrl)
ws.addEventListener('message', (e) => {
  const m = JSON.parse(typeof e.data === 'string' ? e.data : String(e.data))
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    consoleErrs.push(m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 200))
  }
  if (m.method === 'Runtime.exceptionThrown') consoleErrs.push('exception: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 200))
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

// ---------------------------------------------------------------- 页面探针片段
const COL = `[...document.body.children].find(d => /📚 文件目录/.test(d.textContent||'') && /共 \\d+ 部/.test(d.textContent||''))`
const OPEN = `(() => { const b=[...document.querySelectorAll('button,[role="button"]')].find(x=>x.offsetParent!==null && /打开右侧边栏/.test(x.getAttribute('aria-label')||x.getAttribute('title')||'')); if(!b) return 'already'; b.click(); return 'opened' })()`
const CAPSULE = `(() => { const el=document.querySelector('[data-sidebar-right-guide-entry="ks-evidence"]'); if(!el) return 'no-capsule'; el.click(); return 'clicked' })()`
const EXPAND = `(() => {
  const col = ${COL}; if (!col) return 'no-column'
  const collapsed = [...col.querySelectorAll('div,span,button')].filter(e => (e.textContent||'').trim() === '▸')
  if (!collapsed.length) return 'none-collapsed'
  const row = collapsed[0].closest('div') || collapsed[0]
  row.click(); return 'expanded'
})()`
const CLICK_DOC = `(() => {
  const col = ${COL}; if (!col) return 'no-column'
  const cands = [...col.querySelectorAll('div,span,button,li')].filter(e => {
    const r = e.getBoundingClientRect(); const t = (e.textContent||'').trim()
    return r.width > 100 && r.height > 14 && r.height < 44 && e.children.length === 0
      && /^(GB|GBZ|GB\\/T|GB／T|AQ|DB|JGJ|CJJ|TSG|中华人民共和国|民法典|安全生产法)/.test(t)
  })
  const target = cands[0]; if (!target) return 'no-candidate'
  const txt = (target.textContent||'').replace(/\\s+/g,' ').trim().slice(0, 40)
  ;(target.closest('[role="button"],button,li') || target).click()
  return 'clicked: ' + txt
})()`
const SET_MODE = (label) => `(() => {
  const b = [...document.querySelectorAll('button')].find(x => (x.textContent||'').trim().startsWith(${JSON.stringify(label)}))
  if (!b) return 'not-found'
  if (b.getAttribute('aria-pressed') === 'true') return 'already'
  b.click(); return 'clicked'
})()`
const STATE = `(() => {
  const cs = [...document.querySelectorAll('canvas')]
  const vis = cs.filter(c => c.offsetParent !== null)
  const c = vis.sort((a,b)=>b.getBoundingClientRect().height - a.getBoundingClientRect().height)[0]
  let box = c ? c.parentElement : null
  for (; box; box = box.parentElement) { const s = getComputedStyle(box); if (s.overflowY === 'auto' || s.overflowY === 'scroll') break }
  const sl = document.querySelector('input[type="range"][aria-label="缩放百分比"]')
  const label = sl ? Number((sl.getAttribute('title')||'').match(/(\\d+)%/)?.[1]) : null
  const cr = c ? c.getBoundingClientRect() : null
  return JSON.stringify({
    canvasVisible: vis.length,
    canvasTotal: cs.length,
    containerContentW: box ? box.clientWidth - 24 : null,
    firstCanvasW: cr ? Math.round(cr.width*100)/100 : null,
    horizontalOverflow: box ? box.scrollWidth - box.clientWidth : null,
    sliderValue: sl ? sl.value : null,
    sliderLabel: label,
    sliderStep: sl ? sl.getAttribute('step') : null,
  })
})()`

// ---------------------------------------------------------------- 驱动
await call('Page.reload', { ignoreCache: true })
await wait(9000)
await ev(OPEN); await wait(2500)
await ev(CAPSULE); await wait(7000)
let loaded = false
for (let i = 0; i < 8 && !loaded; i++) {
  const e = await ev(EXPAND)
  if (e === 'none-collapsed' && i > 1) break
  await wait(1800)
  const r = await ev(CLICK_DOC)
  if (String(r).startsWith('clicked')) { loaded = true; console.log(`      loaded: ${r}`) }
}
if (!loaded) {
  console.log('SKIP  e2e-sidebar-pdf: 目录里没点到可打开的文档（库可能为空或目录结构不同）')
  ws.close(); process.exit(0)
}
await wait(14000)

const cont = JSON.parse(await ev(STATE))
check('A0 连续模式下文档已渲染（多 canvas）', cont.canvasVisible > 1, `canvasVisible=${cont.canvasVisible}`)

// A. 切「单页」不得卸载文档
consoleErrs.length = 0
check('A1 点「单页」', (await ev(SET_MODE('▭ 单页'))) !== 'not-found')
await wait(9000)
const single = JSON.parse(await ev(STATE))
check('A2 单页模式文档仍在（这正是 2026-09-17 的 P0）', single.canvasVisible >= 1,
  `canvasVisible=${single.canvasVisible}（0 = 文档被卸载）`)
check('A3 单页模式恰好 1 块可见 canvas', single.canvasVisible === 1, `canvasVisible=${single.canvasVisible}`)

// B. 宽度铺满（单页）
check('B1 单页：canvas 宽 == 容器内容宽（宽度铺满）',
  single.firstCanvasW !== null && single.containerContentW !== null
  && Math.abs(single.firstCanvasW - single.containerContentW) <= 8.5,
  `canvas=${single.firstCanvasW} 内容宽=${single.containerContentW}`)
check('B2 单页：无横向溢出', single.horizontalOverflow === 0, `overflow=${single.horizontalOverflow}`)

// C. 滑块如实反映
check('C1 缩放滑块 step = 1（否则百分比会被吸附）', single.sliderStep === '1', `step=${single.sliderStep}`)
check('C2 滑块 value == label 百分比', single.sliderLabel !== null && String(single.sliderLabel) === single.sliderValue,
  `value=${single.sliderValue} label=${single.sliderLabel}`)

// 切回连续：文档同样不得丢
check('A4 点「连续」', (await ev(SET_MODE('☰ 连续'))) !== 'not-found')
await wait(9000)
const back = JSON.parse(await ev(STATE))
check('A5 切回连续后文档仍在', back.canvasVisible > 1, `canvasVisible=${back.canvasVisible}`)
check('B3 连续：canvas 宽 == 容器内容宽',
  back.firstCanvasW !== null && back.containerContentW !== null
  && Math.abs(back.firstCanvasW - back.containerContentW) <= 0.6,
  `canvas=${back.firstCanvasW} 内容宽=${back.containerContentW}`)
check('C3 连续：滑块 value == label 百分比', back.sliderLabel !== null && String(back.sliderLabel) === back.sliderValue,
  `value=${back.sliderValue} label=${back.sliderLabel}`)
check('D  切换期间无 console.error', consoleErrs.length === 0, consoleErrs.slice(0, 2).join(' | ') || 'none')

ws.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n== e2e-sidebar-pdf ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
