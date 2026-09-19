/**
 * plugin/scripts/ui-token-check.mjs — 自包含 HTML 里的 token 覆盖检查（**只读**，2026-09-20 5c 入库）
 *
 * ## 它解决什么（不然"颜色对不对"是说不清的）
 * `ui-render-shot.mjs` 产出的自包含 HTML 里，组件的颜色**全部**来自 `var(--dsw-*)` /
 * `var(--ks-*)`。如果某个 token 在**内联的主题 CSS 里根本没定义**，浏览器会**静默**把它当成
 * 无效声明（`color` 回退到继承/初始值）—— 图上看起来"颜色怪"，但你无法区分
 * "token 名写错了" 和 "这个色本来就长这样"。本脚本逐个 token 核对：
 *   引用集（HTML 里出现过 `var(--x)` 或 `var(--x, 兜底)`）− 定义集（HTML 里出现过 `--x:`）
 *   = **幽灵 token**（该报出来的缺失）。
 *
 * ⚠ 边界：它只查**自包含 HTML 里的静态文本**，不执行 JS、不解析 CSS 层叠
 *   ⇒ "定义了但被后一条规则覆盖" 这类问题它看不见（那要看图）。
 *
 * 用法：`node plugin/scripts/ui-token-check.mjs [shot.html …]`
 *   不给参数 = 扫 `var/tmp/ui-shots/*.html` 全部（`var/` 被 gitignore，截图本就不入库）。
 */
import { readFile, readdir } from 'node:fs/promises'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const shots = resolve(here, '..', '..', 'var', 'tmp', 'ui-shots')

const args = process.argv.slice(2)
const names = args.length > 0
  ? args
  : (await readdir(shots).catch(() => [])).filter((f) => f.endsWith('.html')).sort()

if (names.length === 0) {
  console.error(`❌ 没有可查的 HTML（默认目录 ${shots}）。先用 ui-render-shot.mjs 出一张图。`)
  process.exit(1)
}

let ghostTotal = 0
for (const name of names) {
  const path = name.includes('\\') || name.includes('/') ? resolve(name) : join(shots, name)
  let html
  try {
    html = await readFile(path, 'utf8')
  } catch (e) {
    console.error(`  ⛔ 读不到 ${path}：${e instanceof Error ? e.message : String(e)}`)
    ghostTotal += 1
    continue
  }
  const defined = new Set([...html.matchAll(/(--dsw-[a-z0-9-]+)\s*:/g)].map((m) => m[1]))
  const ksDefined = new Set([...html.matchAll(/(--ks-[a-z0-9-]+)\s*:/g)].map((m) => m[1]))
  // 引用的 token = 出现 var(--x) 或 var(--x, 兜底)
  const referenced = new Set([...html.matchAll(/var\((--dsw-[a-z0-9-]+)\s*[,)]/g)].map((m) => m[1]))
  const ksReferenced = new Set([...html.matchAll(/var\((--ks-[a-z0-9-]+)\s*[,)]/g)].map((m) => m[1]))
  const ghost = [...referenced].filter((t) => !defined.has(t))
  const ksGhost = [...ksReferenced].filter((t) => !ksDefined.has(t))
  // 有兜底值的（即使 token 缺失也不会变成非法声明）
  const withFallback = [...referenced].filter((t) => !defined.has(t) && html.includes(`var(${t},`))
  const ksWithFallback = [...ksReferenced].filter((t) => !ksDefined.has(t) && html.includes(`var(${t},`))
  console.log(`${name}`)
  console.log(`  --dsw-* 引用 ${referenced.size} / 内联定义 ${defined.size} ⇒ 缺失 ${ghost.length}${ghost.length ? ': ' + ghost.join(', ') : ''}`)
  console.log(`  --ks-*  引用 ${ksReferenced.size} / 内联定义 ${ksDefined.size} ⇒ 缺失 ${ksGhost.length}${ksGhost.length ? ': ' + ksGhost.join(', ') : ''}`)
  if (ghost.length) console.log(`  --dsw-* 其中带兜底值的: ${withFallback.length} / ${ghost.length}`)
  if (ksGhost.length) console.log(`  --ks-*  其中带兜底值的: ${ksWithFallback.length} / ${ksGhost.length}`)
  ghostTotal += ghost.length + ksGhost.length
}
if (ghostTotal > 0) {
  console.error(`\n⚠ 共 ${ghostTotal} 个 token 引用了但没定义 —— 颜色会静默回退，别就此下"颜色对了"的结论。`)
}
