#!/usr/bin/env node
/**
 * plugin/scripts/smoke-kb-cols.mjs — **列对齐的三档巡查**（P2 复核打回 B，2026-09-20）
 *
 * ## 它解决什么
 * "列对齐"是 P2 头条的验收之一，而它曾经只有**报告值**：`ui-render-shot.mjs` 量了
 * `#cols`（表头与第一行的 computed `grid-template-columns`）却**没有任何断言** ⇒ 复核的变异 M4
 * （表头 `416px 100px …` vs 行 `444px 72px …`）当时 smoke 33/33 绿、ui-render-shot exit 0。
 * 现在两个地方一起判：① `smoke-kb-page-render.mjs`（jsdom，门禁链里）判"两条声明同不同"；
 * ② `ui-render-shot.mjs` 自己判（真 Chrome 里量**解析后**的像素列模板）—— 本脚本把 ② 按
 * **三档宽度**跑一遍，任一档红即红。为什么必须三档：列档是 `@container (min-width:660px)`
 * 切的（宽档 5 列 / 窄档 3 列），**单跑一档证明不了另一档**。
 *
 * ## 边界（诚实）
 * - 三档宽度按"**容器宽**"选的是**视口宽**：`ui-render-shot.mjs` 的 `#ks-shell` 是定宽
 *   （`--width`），`.ks-main` 的宽度由它推出来 ⇒ 520 / 900 落在窄档、1300 落在宽档。
 * - 本脚本**不进 `smoke-all` 的名单**（有意）：它要 spawn 无头浏览器，而门禁链
 *   （`npm run smoke`）目前**零浏览器依赖** —— 把浏览器塞进门禁链会让"提取树里没有 Chrome"
 *   变成门禁红。⇒ 门禁链的列对齐锚点在 jsdom 那一条（能抓住 M4 这类"两套声明"）；
 *   本脚本是**三档的补充证据 + 一条可复跑的命令**。这条取舍登记在
 *   docs/UI-BASELINE.md 5g（"最该让复核盯的点"与"没做/做不到"两节）。
 * - 依赖 `ui-render-shot.mjs` 的 `colsCheck`（它会因为缺件/截图失败/列对齐红而非零退出）：
 *   本脚本把它当**失败**转达（"没跑"≠"通过"）。
 *
 * 用法：`node plugin/scripts/smoke-kb-cols.mjs [--widths 520,900,1300]`
 * 退出码：0 = 三档都判过且都对齐；1 = 任一档红/没判到；2 = 参数错。
 */
import { spawnSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '..', '..')
const shotScript = join(here, 'ui-render-shot.mjs')

const i = process.argv.indexOf('--widths')
const raw = i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : '520,900,1300'
const widths = raw.split(',').map((s) => Number(s.trim()))
if (widths.length === 0 || widths.some((w) => !Number.isFinite(w) || w <= 0)) {
  console.error(`❌ --widths 要是逗号分隔的正数（拿到 ${JSON.stringify(raw)}）`)
  process.exit(2)
}

const outDir = join(repoRoot, 'var', 'tmp', 'ui-shots')
await mkdir(outDir, { recursive: true })

const rows = []
const failures = []
for (const width of widths) {
  const outPng = join(outDir, `cols-${width}.png`)
  const r = spawnSync(process.execPath, [shotScript, '--page', 'kb', '--width', String(width), '--out', outPng], {
    cwd: repoRoot, encoding: 'utf8', timeout: 180_000,
  })
  let payload = null
  try { payload = JSON.parse(r.stdout) } catch { payload = null }
  const cc = payload?.colsCheck ?? null
  const row = {
    width,
    exit: r.status,
    checked: cc?.checked ?? false,
    skipReason: cc?.skipReason ?? null,
    header: cc?.header ?? null,
    rowTpl: cc?.row ?? null,
    gapHeader: cc?.gapHeader ?? null,
    gapRow: cc?.gapRow ?? null,
    problems: cc?.problems ?? [],
  }
  rows.push(row)
  if (r.status !== 0) {
    failures.push(`width=${width}：ui-render-shot exit=${String(r.status)} —— `
      + (row.problems.length > 0 ? row.problems.join('；') : (r.stderr ?? '').trim().split('\n').slice(-3).join(' / ')))
  } else if (!row.checked) {
    failures.push(`width=${width}：列对齐**没判到**（${row.skipReason ?? 'colsCheck 缺失'}）—— "没跑"不能算通过`)
  }
}

console.log('列对齐三档巡查（每档都跑一遍真 Chrome 的 ui-render-shot）：')
console.log('  宽度   判定    表头 grid-template-columns                 行 grid-template-columns                 gap(表头/行)')
for (const r of rows) {
  const verdict = r.exit !== 0 ? `FAIL(exit ${String(r.exit)})` : (r.checked ? 'PASS' : 'SKIP')
  console.log(`  ${String(r.width).padEnd(6)} ${verdict.padEnd(7)} ${String(r.header).padEnd(42)} ${String(r.rowTpl).padEnd(40)} ${String(r.gapHeader)}/${String(r.gapRow)}`)
  for (const p of r.problems) console.log(`         └─ ${p}`)
}
const wide = rows.filter((r) => r.checked).map((r) => `${r.width}:${String(r.header).split(' ').length} 列`)
console.log(`  档位（按表头列数）：${wide.join(' / ') || '(没有判到的档)'}`)
console.log('')

if (failures.length > 0) {
  console.error('❌ 列对齐巡查判红（P2 头条"列对齐"的验收；变异 M4 走的就是这条路）：')
  for (const f of failures) console.error(`   - ${f}`)
  console.error('   ⇒ 表头（.ks-lhead）与数据行（.ks-item）必须共用同一条 --ks-cols 模板，')
  console.error('      见 plugin/client/ksGuideStyles.ts 的 `.ks-lhead,.ks-item{grid-template-columns:var(--ks-cols)}`。')
  process.exit(1)
}
console.log(`✅ 列对齐巡查通过：${widths.join(' / ')} 三档的表头与第一行逐字相同（gap 也相同）。`)
