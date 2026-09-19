/**
 * plugin/scripts/ui-audit.mjs — 机械口径的样式审计（**只读**，不渲染、不改任何文件）
 *
 * 它回答三个"靠眼睛看不出来"的问题（第 5 步 5c 入库；之前只在 var/tmp 里）：
 *   A. 哪些客户端源文件里还有**写死的十六进制颜色**（官方口径：颜色走活 token，
 *      否则深色主题下不跟随）。附 `var(--dsw-*)`/`var(--ks-*)` 的引用数做对照。
 *      ⚠ 与 `scripts/smoke-client-entry.mjs` 的"主题债务棘轮"同源，但那是**门禁**（只减不增），
 *        这里只**打印分布**（看的时候不该因为超基线就看不到表）。
 *   B. JSX 文本里**字面**的 Markdown 星号（`**粗体**` 当纯文本画出来 = 真 bug，见 5c 的 (b)）。
 *      ⚠ 会**跳过注释行**，但仍会把 JSX 里的多行注释块算进来 —— 那部分是良性噪声
 *        （注释不上屏），所以 B 段只用来**定位**，不许当"缺陷数"。
 *      ⚠ 本文件头**曾经**因为把"JSX 注释的开闭符号"照抄进注释而提前结束块注释、
 *        直接 SyntaxError（同一晚 ui-render-shot.mjs 也栽在写字体通配符上）。
 *        教训：注释里**不要写**星号紧跟斜杠那两个字符。
 *   C. `ksGuideStyles.ts` 的 `KS_STYLES` 里 spacing / 字号是否成体系（4px 网格 + 受限字号表）。
 *      ⚠ 这条**只是显示**；真正的判据/计数口径在 `scripts/smoke-ui-scale.mjs`（棘轮，只减不增）。
 *
 * 用法：`node plugin/scripts/ui-audit.mjs`
 */
import { readFile, readdir } from 'node:fs/promises'
import { join, dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const clientDir = resolve(here, '..', 'client')
const files = (await readdir(clientDir)).filter((f) => f.endsWith('.tsx') || f.endsWith('.ts'))

console.log('=== A. 引号里的十六进制色值（硬编码颜色；官方口径：不许写死色值）===')
const rows = []
for (const f of files) {
  const t = await readFile(join(clientDir, f), 'utf8')
  const hex = t.match(/['"]#[0-9a-fA-F]{3,8}['"]/g) ?? []
  const dsw = t.match(/var\(--dsw-[a-z0-9-]+/g) ?? []
  const ks = t.match(/var\(--ks-[a-z0-9-]+/g) ?? []
  if (hex.length > 0) rows.push({ f, hex: hex.length, dsw: dsw.length, ks: ks.length, sample: [...new Set(hex)].slice(0, 6).join(' ') })
}
rows.sort((a, b) => b.hex - a.hex)
for (const r of rows) console.log(`  ${r.f.padEnd(26)} 硬编码 ${String(r.hex).padStart(3)}  var(--dsw-*) ${String(r.dsw).padStart(3)}  var(--ks-*) ${String(r.ks).padStart(3)}   e.g. ${r.sample}`)
if (rows.length === 0) console.log('  （没有）')

console.log('\n=== B. JSX 文本里**字面**的 Markdown 星号（** 会被当普通文字画出来）===')
for (const f of files) {
  const lines = (await readFile(join(clientDir, f), 'utf8')).split('\n')
  const hits = []
  lines.forEach((line, i) => {
    if (/^\s*(\*|\/\/|\/\*)/.test(line)) return          // 跳过注释行（块注释内部仍会被算，见文件头说明）
    for (const m of line.matchAll(/\*\*[^*"'<>{}]{2,40}\*\*/g)) hits.push(`${i + 1}: ${m[0]}`)
  })
  if (hits.length > 0) {
    console.log(`  --- ${f}: ${hits.length} 处 ---`)
    for (const h of hits.slice(0, 6)) console.log(`        ${h}`)
  }
}

console.log('\n=== C. KS_STYLES 的 spacing / font-size 是否成体系（4px 网格 + 受限字号表）===')
{
  const src = await readFile(join(clientDir, 'ksGuideStyles.ts'), 'utf8')
  const mm = /export const KS_STYLES = `([\s\S]*?)`\n/.exec(src)
  if (mm === null) {
    console.log('  ❌ 抠不出 KS_STYLES（模板字符串被截断了？注释里出现反引号是已知踩坑）')
  } else {
    // 口径与 smoke-ui-scale.mjs 一致：剥注释 + 剥 :root token 定义块
    const noComments = mm[1].replace(/\/\*[\s\S]*?\*\//g, '')
    const body = noComments.replace(/:root\s*\{[\s\S]*?\n\}/, '')
    const grid = [0, 4, 8, 12, 16, 20, 24, 32, 40]
    const hist = new Map()
    for (const d of body.matchAll(/\b(padding|margin|gap)(-[a-z]+)?\s*:\s*([^;{}]+);/g)) {
      for (const n of d[3].matchAll(/(?<![\w.-])(\d+(?:\.\d+)?)px/g)) {
        const v = Number(n[1]); hist.set(v, (hist.get(v) ?? 0) + 1)
      }
    }
    let on = 0, off = 0
    for (const [v, c] of hist) { if (grid.includes(v)) on += c; else off += c }
    const sorted = [...hist.entries()].sort((a, b) => a[0] - b[0])
    console.log(`  在 4px 网格上 ${on} 处 / 不在网格上 ${off} 处`)
    console.log(`  分布: ${sorted.map(([v, c]) => `${v}px×${c}${grid.includes(v) ? '' : '(off)'}`).join('  ')}`)
    const fsHist = new Map()
    for (const d of body.matchAll(/\bfont-size\s*:\s*([^;{}]+);/g)) {
      const k = d[1].trim(); fsHist.set(k, (fsHist.get(k) ?? 0) + 1)
    }
    console.log(`  font-size: ${[...fsHist.entries()].map(([k, c]) => `${k}×${c}`).join('  ')}`)
  }
}
