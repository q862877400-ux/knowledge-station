/**
 * ks-dsh-plugin — scripts/smoke-pdf-panel.mjs
 *
 * 侧栏「让位 / 恢复 / 目录列顶开」协调器冒烟（用户 2026-09-09 需求）：
 *   1. 打开文档 → 侧栏拉到文档友好宽度，并记住"打开前宽度"；
 *   2. 关闭 PDF 查看器 → 还原打开前宽度（幂等，不覆盖之后的手动拖拽）；
 *   3. 打开标题目录 → 侧栏**向左扩张** TOC_COLUMN_WIDTH（PDF 阅读区不变）；
 *      面板顶到 PANEL_MAX 扩不动 → 返回 false（调用方改悬浮覆盖）；
 *   4. store 不可写/无活跃会话 → 全部静默降级为 false，绝不抛。
 *
 * pdfPanel.ts 不碰 DOM（store 由调用方注入），用 esbuild 打包后直接断言。
 * 用法：node scripts/smoke-pdf-panel.mjs   （退出码 0 = 全通过）
 */
import { build } from 'esbuild'
import { rm, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const entry = `
export {
  widenPanelForPdf, restorePanelAfterPdf, hasPendingPanelRestore,
  growPanelForToc, shrinkPanelAfterToc,
  pdfPanelTargetWidth, PANEL_MAX_WIDTH, PANEL_MIN_WIDTH, TOC_COLUMN_WIDTH, TOC_PUSH_MAX_WIDTH,
} from './client/pdfPanel.ts'
`
const entryPath = join(pluginRoot, '.smoke-pdf-panel-entry.mjs')
await writeFile(entryPath, entry, 'utf8')
const outPath = join(pluginRoot, '.smoke-pdf-panel-bundle.mjs')

try {
  await build({
    entryPoints: [entryPath], bundle: true, platform: 'node', format: 'esm',
    outfile: outPath, absWorkingDir: pluginRoot, loader: { '.ts': 'ts' }, logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  await rm(entryPath, { force: true })
  process.exit(1)
}
await rm(entryPath, { force: true })

const m = await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/**
 * 假**宽度端口**：与 `pdfPanel.ts` 的 `PanelWidthPort` 同形（2026-09-16 迁移后）。
 *
 * 旧版假的是 better-sidebar 的 store（`getSnapshot()` 读 / `update(draft)` 写）；
 * 该包已被官方 `dsh-client-ui-sidebar-right` 取代，且官方列**没有**宽度面，
 * 故 pdfPanel 解耦为可选端口。本 fake 同步跟进，断言保持不变——**这正是冒烟的价值**：
 * 端口契约一变，它立刻报红而不是静默退化。
 */
function fakeStore(width) {
  let w = width
  let writes = 0
  return {
    get width() { return w },
    get writes() { return writes },
    getWidth: () => w,
    setWidth: (px) => { w = px; writes += 1; return true },
  }
}

/** pdfPanel 读真实 window.innerWidth；Node 下注入一个假 window 控制视口。 */
function setViewport(px) { globalThis.window = { innerWidth: px } }
setViewport(1920)

// ---- 1. 目标宽度：窗口宽 ×42%，夹在 [400, 640]
check('target: 1920 → 上限 640', m.pdfPanelTargetWidth(1920) === 640)
check('target: 1200 → 504', m.pdfPanelTargetWidth(1200) === 504, `${m.pdfPanelTargetWidth(1200)}`)
check('target: 800 → 下限 400', m.pdfPanelTargetWidth(800) === 400, `${m.pdfPanelTargetWidth(800)}`)
check('target: 非法尺寸 → 兜底 1440×0.42=604', m.pdfPanelTargetWidth(NaN) === 604,
  `${m.pdfPanelTargetWidth(NaN)}`)

// ---- 2. 打开文档：让位 + 记住原宽度 + 关闭恢复
setViewport(1920)
const s1 = fakeStore(400)
check('widen: writes the target', m.widenPanelForPdf(s1, 'sess-A') === true && s1.width === 640,
  `width=${s1.width}`)
check('widen: pending restore recorded', m.hasPendingPanelRestore('sess-A') === true)
m.widenPanelForPdf(s1, 'sess-A') // 第二次点证据：重新拉宽，但不覆盖"打开前宽度"
check('widen: second call keeps the original', s1.width === 640)
check('restore: back to the pre-open width',
  m.restorePanelAfterPdf(s1, 'sess-A') === true && s1.width === 400, `width=${s1.width}`)
check('restore: idempotent (no double restore)',
  m.restorePanelAfterPdf(s1, 'sess-A') === false && s1.width === 400, `width=${s1.width}`)
check('restore: marker cleared', m.hasPendingPanelRestore('sess-A') === false)

// ---- 3. 目录列顶开：有富余时精确扩 TOC_COLUMN_WIDTH，PDF 区不变
const s2 = fakeStore(400)
const before2 = s2.width
const pushed = m.growPanelForToc(s2, 'sess-B')
check('toc grow: width += TOC width', pushed === true
  && s2.width === before2 + m.TOC_COLUMN_WIDTH, `width=${s2.width}`)
check('toc shrink: exactly the recorded amount',
  m.shrinkPanelAfterToc(s2, 'sess-B') === true && s2.width === before2, `width=${s2.width}`)
check('toc shrink: idempotent', m.shrinkPanelAfterToc(s2, 'sess-B') === false)

// ---- 4. 顶到 PANEL_MAX 仍能继续顶开（640→830，PDF 阅读区寸土不失）
setViewport(1920)
const s3 = fakeStore(m.PANEL_MAX_WIDTH)
check('toc grow beyond drag cap: pushes leftward',
  m.growPanelForToc(s3, 'sess-C') === true
  && s3.width === m.PANEL_MAX_WIDTH + m.TOC_COLUMN_WIDTH, `width=${s3.width}`)
check('toc shrink from beyond-cap: returns to the drag cap',
  m.shrinkPanelAfterToc(s3, 'sess-C') === true && s3.width === m.PANEL_MAX_WIDTH,
  `width=${s3.width}`)

// ---- 4b. 空间不够（窗口太窄，对话区要保底 480）→ 全有或全无：回滚 + 报 false
setViewport(900)
const s3b = fakeStore(380)
check('toc grow without room: reports false and rolls back',
  m.growPanelForToc(s3b, 'sess-C2') === false && s3b.width === 380, `width=${s3b.width}`)
check('toc grow without room: nothing left to shrink',
  m.shrinkPanelAfterToc(s3b, 'sess-C2') === false && s3b.width === 380, `width=${s3b.width}`)

// ---- 4c. 上游若硬钳制宽度 → 读回校验发现并回报 false（不假装成功）
setViewport(1920)
const clamped = {
  _w: 640,
  get width() { return this._w },
  getSnapshot() { return { state: { width: this._w } } },
  // 模拟"上游把宽度夹回 640"：写入被吞掉
  update(mutator) { const draft = { width: this._w }; mutator(draft); this._w = Math.min(draft.width, 640) },
}
check('upstream clamp detected via read-back → false',
  m.growPanelForToc(clamped, 'sess-C3') === false && clamped.width === 640,
  `width=${clamped.width}`)

// ---- 5. 部分富余：只扩到硬上限 → 全有或全无（回滚 + 报 false → 调用方悬浮）
setViewport(1920)
const s4 = fakeStore(m.TOC_PUSH_MAX_WIDTH - 30)
check('toc grow partial: rolls back to the original width',
  m.growPanelForToc(s4, 'sess-D') === false && s4.width === m.TOC_PUSH_MAX_WIDTH - 30,
  `width=${s4.width}`)
check('toc grow partial: nothing left to shrink',
  m.shrinkPanelAfterToc(s4, 'sess-D') === false && s4.width === m.TOC_PUSH_MAX_WIDTH - 30,
  `width=${s4.width}`)

// ---- 6. 多会话互不串账
setViewport(1920)
const a = fakeStore(400)
const b = fakeStore(500)
m.widenPanelForPdf(a, 'sess-X')
m.widenPanelForPdf(b, 'sess-Y')
m.restorePanelAfterPdf(a, 'sess-X')
check('multi-session: A restored, B untouched',
  a.width === 400 && b.width === 640, `A=${a.width} B=${b.width}`)
m.restorePanelAfterPdf(b, 'sess-Y')

// ---- 7. store 不可用 → 静默降级（绝不抛、绝不改任何东西）
const broken = { getSnapshot: () => { throw new Error('boom') } }
const noWrite = { getSnapshot: () => ({ state: { width: 400 } }) }
check('no update(): widen → false', m.widenPanelForPdf(noWrite, 'sess-Z') === false)
check('no update(): toc grow → false', m.growPanelForToc(noWrite, 'sess-Z') === false)
check('throwing getSnapshot(): degrade to false',
  m.widenPanelForPdf(broken, 'sess-Z') === false
  && m.growPanelForToc(broken, 'sess-Z') === false
  && m.restorePanelAfterPdf(broken, 'sess-Z') === false)
check('undefined store: degrade to false',
  m.widenPanelForPdf(undefined, undefined) === false
  && m.growPanelForToc(undefined, undefined) === false)

// ---- 8. 已足够宽时不写（避免无谓的 persist churn）
const wide = fakeStore(640)
check('already wide: no write', m.widenPanelForPdf(wide, 'sess-W') === false
  && wide.writes === 0, `writes=${wide.writes}`)

// ---- 9. 关掉 PDF 查看器时目录列记账一并作废（否则重复累加收不回去）
setViewport(1920)
const s5 = fakeStore(400)
m.widenPanelForPdf(s5, 'sess-E')          // 400 → 640
m.growPanelForToc(s5, 'sess-E')           // 640 → 830（目录列顶开）
check('pdf+doc: width is pushed up', s5.width === 830, `width=${s5.width}`)
m.restorePanelAfterPdf(s5, 'sess-E')      // 关闭 PDF 查看器 → 回到 400
check('pdf close restores before doc records', s5.width === 400, `width=${s5.width}`)
m.widenPanelForPdf(s5, 'sess-E')          // 重新打开 PDF → 640
m.growPanelForToc(s5, 'sess-E')           // 再开目录列
m.shrinkPanelAfterToc(s5, 'sess-E')
check('reopen: doc record does not double-count', s5.width === 640, `width=${s5.width}`)

const failed = results.filter((r) => !r.ok)
console.log(`\n== pdf-panel smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
