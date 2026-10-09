#!/usr/bin/env node
/**
 * plugin/scripts/ui-badge-pixels.mjs — **状态徽章可读性的像素证据**（2026-09-20，P2 复核打回 A）
 *
 * ## 它解决什么
 * 复核（`verify-freeze-p2`）用像素量出：浅色下「已废止」徽章有 **208 个 `#EC1313` 文字像素**，
 * 深色只有 **6 个 ≈ 0** —— 因为 `.ks-status-bad` 拿 `--dsw-alias-state-error-secondary` 当**底色**，
 * 而它在 dark 下解出来是 `rgb(242,90,90)`，与**同一条 token 当文字色**（`state-error-primary`
 * 在 dark 也是 `rgb(242,90,90)`）**完全同色** ⇒ 深色下那三个字与底糊成一片。
 * 那次是**人**去数像素；这个脚本把同一套量法变成**一条命令 + 退出码**：
 *   ① 用 `ui-render-shot.mjs` 在 light / dark 各渲一次（真 Chrome）；
 *   ② 从产出的 `.json` 里读每个 `.ks-status` 的 rect 与 computed 颜色；
 *   ③ 自解 PNG（node:zlib，零依赖），在**该 rect 内**数"等于文字色的像素数"，
 *      并取 rect 内的**众数色**当**真实渲染出来的底色**（`rgba()` 底色会被合成，
 *      computed 值不等于屏幕像素值 ⇒ 必须从像素里众数取，不能拿 computed 当底）；
 *   ④ 判红：`底色众数 == 文字色`（同色必判红）+ **对比度 < 3.0** + **可辨文字像素 < 50**。
 *
 * ## 为什么"像素数"要配"对比度"一起判（别只数像素）
 * 当文字色与底色**同色**时，"等于文字色的像素数"会把**整个徽章**都算进去（成百上千）
 * ⇒ 光看像素数反而更大、看着更健康。所以口径是：
 *   `textPixels` = 等于文字色的像素数；若 `底色众数 == 文字色`，则**可辨**文字像素记 0
 *   （同色 ⇒ 没有一笔是"可辨的文字"），并直接判红。
 *
 * ## 边界（别把它读成"整页视觉验收"）
 * - 只量**状态徽章**（`.ks-status`）这一个元素类；页面上其它可读性它不管。
 * - 依赖真浏览器（同 `ui-render-shot.mjs`）：找不到浏览器**报错退出**，不静默跳过。
 * - 阈值 3.0 是"机械可辨"的下限（WCAG 大字号 AA 档），**不是**"排版好看"的判据；
 *   red-600 在浅底上的对比度上限本就 ~4.1（错误色族里没有 tertiary 底色 token，
 *   见 docs/UI-BASELINE.md 5g 的留痕）⇒ 数值照实打印，别把 4.1 读成"合格"。
 * - ⚠ **对比度只判「已废止」那一档**（本轮复核打回 A 指的就是它），其余徽章的对比度
 *   **只报告不判**：`.ks-status-ok` 在**浅色**下实测 **2.09**（success-100 底 + success-500 字）
 *   —— 那是宿主自己那一套 tertiary/primary 配对，与"我们给 bad 档选错了 token"是两件事；
 *   把它一并判红会逼着本轮顺手改掉另外三档的观感（超出本轮范围）。⇒ 登记为观察
 *   （UI-BASELINE 5g），不是"合格"。`文字色 == 实渲底色`（整块纯色）与"可辨文字像素 < 50"
 *   这两条**对所有档都判**——它们是绝对的"没有文字"判据，不是偏好。
 *
 * 用法：`node plugin/scripts/ui-badge-pixels.mjs [--width 1300] [--theme light|dark|both]`
 * 退出码：0 = 两套主题的徽章都"有可辨文字"；1 = 有一条不过 / 缺件；2 = 参数错。
 */
import { existsSync } from 'node:fs'
import { mkdir, readFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { inflateSync } from 'node:zlib'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '..', '..')
const shotScript = join(here, 'ui-render-shot.mjs')

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`)
  if (i !== -1 && process.argv[i + 1] !== undefined && !process.argv[i + 1].startsWith('--')) return process.argv[i + 1]
  return fallback
}
const width = Number(arg('width', '1300'))
const themes = arg('theme', 'both') === 'both' ? ['light', 'dark'] : [arg('theme', 'light')]
const outDir = resolve(arg('out-dir', join(repoRoot, 'var', 'tmp', 'ui-shots')))
if (!Number.isFinite(width) || width <= 0) { console.error(`❌ --width 要是正数（拿到 ${arg('width', '')}）`); process.exit(2) }
if (themes.some((t) => t !== 'light' && t !== 'dark')) { console.error('❌ --theme 只能是 light / dark / both'); process.exit(2) }
if (!existsSync(shotScript)) { console.error(`❌ 找不到 ${shotScript}`); process.exit(1) }

/** 复核实测过的量法：PNG 8-bit RGB/RGBA、非隔行；只用 node:zlib，不引依赖。 */
function decodePng(buf) {
  let off = 8; let w = 0; let h = 0; let bitDepth = 0; let colorType = 0
  const idat = []
  while (off < buf.length) {
    const len = buf.readUInt32BE(off)
    const type = buf.toString('ascii', off + 4, off + 8)
    const data = buf.subarray(off + 8, off + 8 + len)
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); bitDepth = data[8]; colorType = data[9] }
    else if (type === 'IDAT') idat.push(data)
    else if (type === 'IEND') break
    off += 12 + len
  }
  if (bitDepth !== 8 || (colorType !== 2 && colorType !== 6)) {
    throw new Error(`不支持的 PNG：bitDepth=${bitDepth} colorType=${colorType}（本工具只解 8-bit RGB/RGBA 非隔行）`)
  }
  const ch = colorType === 6 ? 4 : 3
  const raw = inflateSync(Buffer.concat(idat))
  const stride = w * ch
  const px = Buffer.alloc(h * stride)
  let p = 0
  for (let row = 0; row < h; row += 1) {
    const filter = raw[p]; p += 1
    const line = raw.subarray(p, p + stride); p += stride
    const cur = px.subarray(row * stride, (row + 1) * stride)
    const prev = row === 0 ? Buffer.alloc(stride) : px.subarray((row - 1) * stride, row * stride)
    for (let i = 0; i < stride; i += 1) {
      const a = i >= ch ? cur[i - ch] : 0
      const b = prev[i]
      const c = i >= ch ? prev[i - ch] : 0
      let v = line[i]
      if (filter === 1) v += a
      else if (filter === 2) v += b
      else if (filter === 3) v += (a + b) >> 1
      else if (filter === 4) {
        const pp = a + b - c
        const pa = Math.abs(pp - a); const pb = Math.abs(pp - b); const pc = Math.abs(pp - c)
        v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c)
      }
      cur[i] = v & 0xff
    }
  }
  return { w, h, ch, stride, px }
}

const parseRgb = (s) => {
  const m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(s ?? '')
  return m === null ? null : [Number(m[1]), Number(m[2]), Number(m[3])]
}
const key = ([r, g, b]) => (r << 16) | (g << 8) | b
const hex = (k) => `#${k.toString(16).padStart(6, '0')}`
const lin = (v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4 }
const luminance = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
const contrast = (a, b) => {
  const la = luminance(a); const lb = luminance(b)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

/** 徽章 rect 内的像素统计：文字色像素数 + 众数色（真实底色）+ 对比度。 */
function measureBadge(img, badge, textRgb) {
  const x0 = Math.max(0, badge.x); const y0 = Math.max(0, badge.y)
  const x1 = Math.min(img.w, badge.x + badge.w); const y1 = Math.min(img.h, badge.y + badge.h)
  const counts = new Map()
  let textPixels = 0
  const want = key(textRgb)
  for (let y = y0; y < y1; y += 1) {
    for (let x = x0; x < x1; x += 1) {
      const i = y * img.stride + x * img.ch
      const k = (img.px[i] << 16) | (img.px[i + 1] << 8) | img.px[i + 2]
      counts.set(k, (counts.get(k) ?? 0) + 1)
      if (k === want) textPixels += 1
    }
  }
  let modeKey = null; let modeN = -1
  for (const [k, n] of counts) if (n > modeN) { modeN = n; modeKey = k }
  const modeRgb = [(modeKey >> 16) & 0xff, (modeKey >> 8) & 0xff, modeKey & 0xff]
  const sameAsText = key(modeRgb) === want
  return {
    rect: `${badge.x},${badge.y} ${badge.w}x${badge.h}`,
    colors: counts.size,
    textPixels,
    // 同色 ⇒ 没有一笔是"可辨的文字"（见文件头"为什么像素数要配对比度"）
    distinctTextPixels: sameAsText ? 0 : textPixels,
    bgMode: hex(modeKey),
    bgModePixels: modeN,
    textRgb: hex(want),
    sameAsText,
    contrast: Number(contrast(textRgb, modeRgb).toFixed(2)),
  }
}

await mkdir(outDir, { recursive: true })
const rows = []
const problems = []
for (const theme of themes) {
  const outPng = join(outDir, `badge-${width}-${theme}.png`)
  // ⚠ **5h（2026-09-20）：必须带 `--interact kb-files`** —— 状态徽章只在**文件表格**里，
  //   而本轮 IA 重构后 kb 页默认停在「卡片带 + 一级目录」（业主："到最末一级才是文件"）
  //   ⇒ 不先下钻就没有 `.ks-status`，本脚本会走"#status 里没有徽章条目"的失败分支
  //   （那是对的：没量到 ≠ 通过）。断言与阈值一个字没改，只是多一步导航。
  const r = spawnSync(process.execPath, [shotScript, '--page', 'kb', '--width', String(width), '--theme', theme, '--interact', 'kb-files', '--out', outPng], {
    // ⚠ `stdio[0]='ignore'`：本机 spawnSync 用 pipe 做 stdin 会恒 EBUSY（见 smoke-all.mjs 头注）。
    cwd: repoRoot, encoding: 'utf8', timeout: 180_000, stdio: ['ignore', 'pipe', 'pipe'],
  })
  if (r.status !== 0) {
    console.error(`❌ ui-render-shot 失败（theme=${theme}，exit=${r.status}）—— 缺件/截图失败/列对齐自检红都走这里：`)
    console.error((r.stderr ?? '').split('\n').slice(-8).join('\n'))
    process.exit(1)
  }
  let payload = null
  try { payload = JSON.parse(r.stdout) } catch { payload = null }
  const items = payload?.measured?.['#status']?.items
  if (!Array.isArray(items) || items.length === 0) {
    console.error(`❌ ${theme}：ui-render-shot 的 measured["#status"] 里没有徽章条目（这条没验到，不是通过）`)
    process.exit(1)
  }
  const img = decodePng(await readFile(outPng))
  for (const badge of items) {
    const textRgb = parseRgb(badge.color)
    if (textRgb === null) { console.error(`❌ ${theme}：解析不出 computed 文字色 ${JSON.stringify(badge.color)}`); process.exit(1) }
    const m = measureBadge(img, badge, textRgb)
    // 「没有文字」判据（所有档都判）+ 对比度（只判「已废止」，理由见文件头边界）
    const contrastJudged = badge.text === '已废止'
    const noText = m.sameAsText || m.distinctTextPixels < 50
    const contrastBad = contrastJudged && m.contrast < 3.0
    const ok = !noText && !contrastBad
    rows.push({ theme, text: badge.text, computedColor: badge.color, computedBg: badge.bg, contrastJudged, ...m, ok })
    if (!ok) {
      problems.push(`${theme}「${badge.text}」：${noText
        ? `没有可辨文字（可辨文字像素 ${m.distinctTextPixels}${m.sameAsText ? '，且文字色==实渲底色' : ''}）`
        : `对比度 ${String(m.contrast)} < 3.0`}`
        + `；文字色 ${m.textRgb} vs 实渲底色 ${m.bgMode}`)
    }
  }
  console.log(`\n══ theme=${theme}  png=${outPng.replace(`${repoRoot}\\`, '')}  ${img.w}x${img.h} ══`)
  for (const row of rows.filter((x) => x.theme === theme)) {
    console.log(`  ${row.ok ? 'PASS' : 'FAIL'}  「${row.text}」 ${row.rect}`
      + `  computed color=${row.computedColor} bg=${row.computedBg}`
      + `  ⇒ 文字像素 ${row.textPixels}（可辨 ${row.distinctTextPixels}）`
      + `  实渲底色 ${row.bgMode}（${row.bgModePixels} px，${row.colors} 种色）`
      + `  对比度 ${String(row.contrast)}${row.contrastJudged ? '' : '（只报告，不判）'}`
      + `${row.sameAsText ? '  ⚠ 文字色==实渲底色' : ''}`)
  }
}

console.log('')
if (problems.length > 0) {
  console.error('❌ 状态徽章可读性判红（P2 复核打回 A 的口径：浅/深各一次，量"文字像素数"）：')
  for (const p of problems) console.error(`   - ${p}`)
  console.error('   ⇒ 徽章的底色不许与文字色同色；`.ks-status-bad` 的做法见 ksGuideStyles.ts')
  console.error('      （底色 = state-error 族里**浅/暗**的那一条，文字/描边 = state-error-primary）。')
  process.exit(1)
}
console.log(`✅ 状态徽章可读性自检通过（${themes.join(' + ')}；width=${width}）`
  + '：所有档都"文字色 ≠ 实渲底色"且可辨文字像素 ≥50；「已废止」另过对比度 ≥3.0。')
