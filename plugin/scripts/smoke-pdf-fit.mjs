/**
 * ks-dsh-plugin — scripts/smoke-pdf-fit.mjs
 *
 * PDF 缩放规则离线冒烟（用户反馈「默认打开 PDF 太小」）。
 *
 * pdfFit.ts 是纯函数（零 DOM），用 esbuild 打包成 node 可执行 ESM 后直接断言
 * 真实 A4 尺寸下的缩放结果：自适应一律**宽度铺满**（2026-09-17 用户裁定"高度不用管"）、
 * 高度不参与定标、上下限钳制、未布局返回 null、后备位图 dpr 不超预算。
 *
 * 用法：node scripts/smoke-pdf-fit.mjs   （退出码 0 = 全通过）
 */
import { build } from 'esbuild'
import { rm, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const entry = `
export {
  fitPageScale, backingStoreDpr, PAGE_PADDING, MIN_SCALE, MAX_SCALE, MAX_BACKING_PIXELS,
  zoomScale, zoomForManual, zoomForAutoFit, clampManualPercent,
  ZOOM_AUTO, MANUAL_MIN_PERCENT, MANUAL_MAX_PERCENT, ZOOM_PRESET_PERCENTS,
} from './client/pdfFit.ts'
`
const entryPath = join(pluginRoot, '.smoke-pdf-fit-entry.mjs')
await writeFile(entryPath, entry, 'utf8')
const outPath = join(pluginRoot, '.smoke-pdf-fit-bundle.mjs')

try {
  await build({
    entryPoints: [entryPath],
    bundle: true,
    platform: 'node',
    format: 'esm',
    outfile: outPath,
    absWorkingDir: pluginRoot,
    loader: { '.ts': 'ts' },
    logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  await rm(entryPath, { force: true })
  process.exit(1)
}
await rm(entryPath, { force: true })

const mod = await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })

const {
  fitPageScale, backingStoreDpr, PAGE_PADDING, MAX_SCALE,
  zoomScale, zoomForManual, zoomForAutoFit, clampManualPercent,
  ZOOM_AUTO, MANUAL_MIN_PERCENT, MANUAL_MAX_PERCENT, ZOOM_PRESET_PERCENTS,
} = mod

/** A4（GB 标准正文版心常用）在 scale=1 下的 pdf.js viewport 尺寸。 */
const A4 = { pageWidth: 595.28, pageHeight: 841.89 }

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
const near = (a, b, eps = 1e-6) => Math.abs(a - b) <= eps

// ---- 1. 默认 400px 侧栏（可视宽 376）→ **宽度铺满**：页宽 == 可视宽，右侧不再被切
//    （2026-09-17 规则变更：用户裁定"宽度铺满，高度不用管"，见 pdfFit.fitPageScale）
const narrow = fitPageScale({ availWidth: 400 - PAGE_PADDING, availHeight: 900 - PAGE_PADDING, ...A4 })
check('narrow panel: the page fills the visible width exactly (nothing cut off)',
  narrow !== null && near(A4.pageWidth * narrow.scale, 400 - PAGE_PADDING, 0.5),
  `pageW=${(A4.pageWidth * narrow.scale).toFixed(1)} vs avail ${400 - PAGE_PADDING}`)
check('narrow panel: no horizontal overflow at all',
  narrow !== null && A4.pageWidth * narrow.scale <= (400 - PAGE_PADDING) + 0.5,
  `pageW=${(A4.pageWidth * narrow.scale).toFixed(1)}`)
check('narrow panel: basis is always width now (height no longer decides the scale)',
  narrow !== null && narrow.basis === 'width' && narrow.cappedByBudget === false,
  `basis=${narrow?.basis} capped=${narrow?.cappedByBudget}`)

// ---- 2. 面板拉满 640 → 同样只按宽度定标（旧的"按高度拉满"已退休）
const maxPanel = fitPageScale({ availWidth: 640 - PAGE_PADDING, availHeight: 900 - PAGE_PADDING, ...A4 })
check('640 panel: still width-driven (height is ignored)',
  maxPanel !== null && near(A4.pageWidth * maxPanel.scale, 616, 0.5),
  `pageW=${(A4.pageWidth * maxPanel.scale).toFixed(1)} vs avail 616`)
check('640 panel: 高度不再参与 —— 同宽不同高必须给出同一个 scale', (() => {
  const tall = fitPageScale({ availWidth: 616, availHeight: 876, ...A4 })
  const short = fitPageScale({ availWidth: 616, availHeight: 200, ...A4 })
  return tall !== null && short !== null && near(tall.scale, short.scale)
})(), 'height ignored')

// ---- 3. 宽窗口 → 横向铺满（不产生横向滚动）
const wide = fitPageScale({ availWidth: 1200 - PAGE_PADDING, availHeight: 700 - PAGE_PADDING, ...A4 })
check('wide window: fit-width basis', wide !== null && wide.basis === 'width', `basis=${wide?.basis}`)
check('wide window: page fills the width', wide !== null
  && near(Math.round(A4.pageWidth * wide.scale), 1176, 1),
  `pageW=${Math.round(A4.pageWidth * wide.scale)} vs avail 1176`)

// ---- 4. 极窄（目录列展开时 PDF 区只剩 ~186px）→ 受 MIN_SCALE 兜底，与旧行为一致
const tinyCol = fitPageScale({ availWidth: 186 - PAGE_PADDING, availHeight: 876, ...A4 })
check('tiny column: clamped by MIN_SCALE, no worse than legacy',
  tinyCol !== null && near(tinyCol.scale, 0.5) && tinyCol.clamped === true,
  `scale=${tinyCol?.scale}`)

// ---- 5. 上下限钳制
const huge = fitPageScale({ availWidth: 3000, availHeight: 3000, ...A4 })
check('huge container: clamped to MAX_SCALE',
  huge !== null && near(huge.scale, MAX_SCALE) && huge.clamped === true,
  `scale=${huge?.scale} clamped=${huge?.clamped}`)
const tiny = fitPageScale({ availWidth: 100, availHeight: 100, ...A4 })
check('tiny container: clamped to MIN_SCALE',
  tiny !== null && near(tiny.scale, 0.5) && tiny.clamped === true,
  `scale=${tiny?.scale}`)

// ---- 6. 未布局 → null（调用方跳过绘制，绝不按 0 尺寸算出畸形缩放）
check('zero size → null', fitPageScale({ availWidth: 0, availHeight: 800, ...A4 }) === null)
check('negative size → null', fitPageScale({ availWidth: 400, availHeight: -5, ...A4 }) === null)
check('zero page size → null',
  fitPageScale({ availWidth: 400, availHeight: 800, pageWidth: 0, pageHeight: 0 }) === null)

// ---- 7. 后备位图 dpr 预算
const small = backingStoreDpr(620, 876, 2)
check('dpr: normal page keeps device dpr', near(small, 2), `dpr=${small}`)
const mid = backingStoreDpr(3000, 4000, 3)
check('dpr: mid-range budget scales down proportionally (1 < dpr < 3)',
  mid > 1 && mid < 3, `dpr=${mid.toFixed(3)}`)
const big = backingStoreDpr(5000, 7000, 3)
check('dpr: oversized canvas downgrades but stays >= 1', big >= 1 && big < 3,
  `dpr=${big.toFixed(3)}`)
check('dpr: invalid device dpr falls back to 1', backingStoreDpr(600, 800, NaN) === 1)

// ---- 8. 缩放状态机（2026-09-16 底部常驻栏：滑块 + 浏览比例下拉）----
// 容器 A = 默认 400px 侧栏（内容宽 376 / 高 876）；容器 B = 同一面板被拉宽到 700。
const fitA = { availWidth: 400 - PAGE_PADDING, availHeight: 900 - PAGE_PADDING, ...A4 }
const fitB = { availWidth: 700 - PAGE_PADDING, availHeight: 900 - PAGE_PADDING, ...A4 }
const autoA = zoomScale(ZOOM_AUTO, fitA)
const autoB = zoomScale(ZOOM_AUTO, fitB)

// 8.1 默认 = 自适应，且与既有 fitPageScale 结果逐位一致（未破坏原规则）
check('zoom: default state is autoFit', ZOOM_AUTO.source === 'autoFit'
  && autoA.source === 'autoFit'
  && autoA.scale === fitPageScale(fitA).scale,
  `scale=${autoA.scale.toFixed(4)} fit=${fitPageScale(fitA).scale.toFixed(4)}`)
check('zoom: autoFit still follows the container (窗口变化 → 缩放变)',
  autoB.scale !== autoA.scale,
  `${autoA.scale.toFixed(4)} → ${autoB.scale.toFixed(4)}`)

// 8.2 手选 125% → 退出自适应
const manual = zoomForManual(125)
check('zoom: choosing 125% leaves autoFit', manual.source === 'manual' && manual.percent === 125)
const manA = zoomScale(manual, fitA)
check('zoom: manual 125% applies exactly 1.25', near(manA.scale, 1.25),
  `scale=${manA.scale}`)

// 8.3 退出自适应后，容器（窗口）变化**不再**改缩放
const manB = zoomScale(manual, fitB)
check('zoom: manual is immune to container changes (拉伸窗口不改缩放)',
  manB.scale === manA.scale && near(manB.scale, 1.25),
  `A=${manA.scale} B=${manB.scale}`)
check('zoom: manual ignores even a drastic resize',
  zoomScale(manual, { availWidth: 2000, availHeight: 200, ...A4 }).scale === 1.25)
check('zoom: manual state is unchanged by re-derivation (no drift)',
  zoomScale(zoomScale(manual, fitB).source === 'manual' ? manual : ZOOM_AUTO, fitA).percent === 125)

// 8.4 选「自适应窗口」→ 恢复自适应（又跟着窗口走）
const backToAuto = zoomForAutoFit()
check('zoom: 自适应窗口 restores autoFit', backToAuto.source === 'autoFit')
const backA = zoomScale(backToAuto, fitA)
const backB = zoomScale(backToAuto, fitB)
check('zoom: after restore the scale follows the container again',
  backA.scale === autoA.scale && backB.scale === autoB.scale && backB.scale !== backA.scale,
  `${backA.scale.toFixed(4)} → ${backB.scale.toFixed(4)}`)

// 8.5 手动值钳制：[10, 500]（左端 10% = 最小可读值，用户已确认；0% 会渲染空白）
check('zoom: manual floor is 10% (0% would render blank)',
  clampManualPercent(0) === MANUAL_MIN_PERCENT && MANUAL_MIN_PERCENT === 10,
  `floor=${MANUAL_MIN_PERCENT}`)
check('zoom: 0% collapses onto the readable floor, never scale 0',
  zoomScale(zoomForManual(0), fitA).scale === 0.1
  && zoomScale(zoomForManual(-40), fitA).scale === 0.1)
check('zoom: manual ceiling is 500%', clampManualPercent(9999) === MANUAL_MAX_PERCENT
  && near(zoomScale(zoomForManual(9999), fitA).scale, 5))
check('zoom: slider ends map to exactly 10% and 500%',
  zoomScale(zoomForManual(MANUAL_MIN_PERCENT), fitA).percent === 10
  && zoomScale(zoomForManual(MANUAL_MAX_PERCENT), fitA).percent === 500)
check('zoom: NaN falls back to the floor instead of poisoning the canvas',
  clampManualPercent(NaN) === MANUAL_MIN_PERCENT)
check('zoom: preset list is the documented one, ascending, inside the range',
  ZOOM_PRESET_PERCENTS.join(',') === '25,50,75,100,125,150'
  && ZOOM_PRESET_PERCENTS.every((p) => p > MANUAL_MIN_PERCENT && p < MANUAL_MAX_PERCENT))

// 8.6 单页 / 连续**定标相同**（2026-09-17：自适应不再读高度，旧版那个
//     `continuousViewportHeight()` 抬高逻辑高的适配已随规则一起退休）
//
// ⚠ 这里**有意删掉**了一对旧断言，不是漏了：
//   · `continuous mode sits exactly on the width budget` / `… never exceeds the budget`
//     —— 它们断言的"允许溢出 ×1.25"正是用户这次否掉的规则；
//   · `single mode still lets the visible height drive the scale (规则未被破坏)`
//     —— 它守护的是"单页模式按高度定标"这一行为，而该行为就是本次要删的东西。
//   三者的替代断言是**反向**的（"同宽不同高必须给出同一个 scale" + "页宽 == 可视宽"），
//   所以断言数从 41 降到 37 是契约收窄的结果，覆盖面没有下降。
const singleTall = fitPageScale({ ...fitA, availHeight: 876, ...A4 })
const singleShort = fitPageScale({ ...fitA, availHeight: 200, ...A4 })
const contLike = fitPageScale({ ...fitA, availHeight: 4000, ...A4 })
check('zoom: the visible height no longer decides the scale (三者同值)',
  singleTall !== null && singleShort !== null && contLike !== null
  && near(singleTall.scale, singleShort.scale) && near(singleShort.scale, contLike.scale),
  `${singleTall?.scale.toFixed(4)} / ${singleShort?.scale.toFixed(4)} / ${contLike?.scale.toFixed(4)}`)
check('zoom: autoFit sits exactly on the visible width',
  singleTall !== null && near(singleTall.scale, fitA.availWidth / A4.pageWidth, 1e-9),
  `scale=${singleTall?.scale.toFixed(4)}`)
check('zoom: autoFit never exceeds the visible width (右侧不会被切)',
  singleTall !== null && A4.pageWidth * singleTall.scale <= fitA.availWidth + 0.5)

// 8.7 未布局（容器 0 尺寸）时手动仍有确定值、自适应不装懂
check('zoom: manual survives an unlaid-out container',
  zoomScale(manual, { availWidth: 0, availHeight: 0, ...A4 }).scale === 1.25)
check('zoom: autoFit on an unlaid-out container reports clamped, never NaN',
  Number.isFinite(zoomScale(ZOOM_AUTO, { availWidth: 0, availHeight: 0, ...A4 }).scale)
  && zoomScale(ZOOM_AUTO, { availWidth: 0, availHeight: 0, ...A4 }).clamped === true)

const failed = results.filter((r) => !r.ok)
console.log(`\n== pdf-fit smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
