/**
 * ks-dsh-plugin — scripts/smoke-ui-scale.mjs
 *
 * **尺度棘轮（只减不增）**：`plugin/client/ksGuideStyles.ts` 的 `KS_STYLES` 里，
 * 凡是"现场拍的" spacing / font-size 字面值，**计数不许超过下面冻结的基线**。
 *
 * ## 为什么要有它（一句话）
 * 第 5 步给 UI 立了 `--ks-*` 尺度 token，但**没有护栏**——5a 收了一批、5b 又漏了 8 处，
 * 5c 才由离屏渲染子代理机械量出来（spacing 17 处不在 4px 网格 + 字号 13 处字面值）。
 * 靠人"记得用 token"已经失败两次 ⇒ 把口径变成脚本，**数字只能往下走**。
 *
 * ## 口径（**必须与 docs/UI-BASELINE.md 第二节一致**，不是另立一套）
 * - spacing：`padding` / `margin` / `gap`（含 `-top`/`-bottom`/`-left`/`-right`/`-inline` 等后缀）
 *   的值里的每个 `Npx`，**不在 4px 网格**（0/4/8/12/16/20/24/32/40）就算一处离网格。
 *   `0` 不写单位，本来就不计入。
 * - font-size：值**不是** `var(--ks-fs-*)` 就算一处现场字号（受限字号表要求走 token）。
 *
 * ## 三条**不许绕过**的解析纪律（否则这个棘轮会变成"永远绿"）
 * 1. **token 定义行不算**：`:root{...}` 里那个整块（`--ks-space-1:4px` / `--ks-fs-*:11px` / …）
 *    是**定义**，不是现场数字 —— 整块剥掉再扫。
 * 2. **注释不算**：`/* ... *\/` 整块剥掉再扫（否则"注释里提一句 13px"就会虚增计数，
 *    那会诱使人去改注释而不是改代码）。
 * 3. **不引第三方解析器**：只用一个正则剥注释/剥 `:root`/扫声明（本仓冒烟一律零依赖）。
 *
 * ## 基线怎么改（**只减不增**）
 * 收获一处就**把基线改成新值**（数字变小），并在 `SHRINK_LOG` 里记一行"哪处、为什么"。
 * **不许**为了让它变绿而把基线调大，也**不许**把例外塞进白名单来绕过——
 * 白名单是给"确有排版理由、且写清了理由"的值用的，见 `EXCEPTIONS`。
 *
 * 用法：`node plugin/scripts/smoke-ui-scale.mjs`（退出码 0 = 没变差）。
 */
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = dirname(here)
const stylesPath = join(pluginRoot, 'client', 'ksGuideStyles.ts')

/* ─────────────────────────── 冻结的基线（只减不增） ─────────────────────────── */
/**
 * spacing：`padding/margin/gap` 里**不在 4px 网格**的 px 字面值计数。
 *
 * 历史：5a/5b 之后 17 → 5c 收到 **0**（2026-09-20）。基线到此为止：**再出现一处就是红**。
 * 谁要突破它，只有两条路：① 改成 4px 网格值；② 在 `EXCEPTIONS` 里加一条**带理由**的例外。
 */
const BASELINE_OFF_GRID_SPACING = 0

/**
 * font-size：值**不是** `var(--ks-fs-*)` 的现场字号计数。
 *
 * 历史：5a/5b 之后 13 → 5c 收到 **0**（2026-09-20）。同上，只减不增。
 */
const BASELINE_RAW_FONT_SIZE = 0

/** 收到基线时**逐条**记下来（"哪处、为什么"），供后来者核对口径没被偷偷放宽。 */
const SHRINK_LOG = [
  '2026-09-20（5c）spacing 17→0：2px×3 / 3px×1 / 5px×1 / 6px×5 / 7px×1 / 9px×1 / 10px×2 / 14px×3 全部换成 --ks-space-* 或 4px 网格值。',
  '2026-09-20（5c）font-size 13→0：10px×1 → 新增 --ks-fs-2xs（理由写在 token 注释里）；11px×2 → --ks-fs-xs；'
    + '12px×4 / 13px×3 → --ks-fs-sm / --ks-fs-base；15px×1 → --ks-fs-lg；'
    + '11.5px×2 → **没有**为它加 token，直接收进 --ks-fs-sm（它本来就是"辅助行比正文小一档 ~1px"的位置，'
    + '12px 对 13px 正好差一档；为 0.5px 单开一档会让字号表变成"越大越细"）。',
]

/**
 * **允许的例外**：逐条列出、每条**必须**带理由，且**必须**解释"为什么它不在 4px 网格/受限字号表上"。
 * 例外的键是 `spacing` 或 `font-size`，值是 `{ 字面值: 理由 }`。
 *
 * ⚠ 例外**不是**为了让脚本变绿的后门：能被 token 表达的一律进 token。
 *    只有在"token 表达不了、且硬掰成网格值会说不清为什么"时才登记。
 */
const EXCEPTIONS = {
  spacing: {
    // 例：'3px': '……理由……',
  },
  'font-size': {
    // 例：'11.5px': '……理由……',
  },
}

/* ─────────────────────────────── 解析 ─────────────────────────────── */
const src = await readFile(stylesPath, 'utf8')

// ⚠ 行尾容错 `\r?\n`（复核 ui5 2026-09-20）：`core.autocrlf=true` 下 `git worktree` 提取树是 CRLF，
//   写死 `\n` 会在这条**棘轮**上假报"抠不出 KS_STYLES"（看着像交付件坏了，其实只是行尾）。
const m = /export const KS_STYLES = `([\s\S]*?)`\r?\n/.exec(src)
if (m === null) {
  console.error(`❌ 从 ${stylesPath} 里抠不出 KS_STYLES（行尾已容错 CRLF/LF ⇒ 多半是模板字符串被截断；注释里出现反引号是已知踩坑）`)
  process.exit(1)
}
const rawBody = m[1]

// 纪律 2：先剥**注释**（整块），免得注释里的数字被算成现场值。
const withoutComments = rawBody.replace(/\/\*[\s\S]*?\*\//g, '')

// 纪律 1：剥掉 `:root{...}` 那一整块（token **定义**，不是现场数字）。
const rootBlocks = [...withoutComments.matchAll(/:root\s*\{[\s\S]*?\n\}/g)]
if (rootBlocks.length !== 1) {
  console.error(`❌ 期望恰好 1 个 :root{...} token 定义块，实测 ${rootBlocks.length} 个`
    + '（多了/少了说明本脚本的剥除口径已与文件结构脱节，必须先修口径再谈计数）')
  process.exit(1)
}
const rootBlock = rootBlocks[0][0]
const body = withoutComments.replace(rootBlock, '')

/** 4px 网格（与 UI-BASELINE 第二节的 4/8/12/16/20/24/32/40 逐个对齐；0 不带单位故天然不在扫描里）。 */
const GRID = new Set([4, 8, 12, 16, 20, 24, 32, 40])

const offGrid = [] // {value, decl}
const rawFontSize = [] // {value, decl}

// spacing：padding/margin/gap 及其方向后缀。⚠ 不匹配 `--ks-space-*` 这种自定义属性名，
// 因为那行的属性名以 `-` 开头、且这里要求以 padding/margin/gap **开头**。
const spaceDecl = /\b(padding|margin|gap)(-[a-z]+)?\s*:\s*([^;{}]+);/g
for (const d of body.matchAll(spaceDecl)) {
  const value = d[3]
  for (const n of value.matchAll(/(?<![\w.-])(\d+(?:\.\d+)?)px/g)) {
    const v = Number(n[1])
    const key = `${n[1]}px`
    if (GRID.has(v)) continue
    if (EXCEPTIONS.spacing[key] !== undefined) continue
    offGrid.push({ value: key, decl: `${d[1]}${d[2] ?? ''}: ${value.trim()}` })
  }
}

// font-size：值必须是 var(--ks-fs-*)，否则算现场字号。
const fsDecl = /\bfont-size\s*:\s*([^;{}]+);/g
for (const d of body.matchAll(fsDecl)) {
  const value = d[1].trim()
  if (/^var\(--ks-fs-[a-z0-9-]+\)$/.test(value)) continue
  if (EXCEPTIONS['font-size'][value] !== undefined) continue
  rawFontSize.push({ value, decl: `font-size: ${value}` })
}

/* ─────────────────────────────── 断言 ─────────────────────────────── */
const lines = []
lines.push(`样式源：${stylesPath}`)
lines.push(`剥除：注释 ${(rawBody.length - withoutComments.length)} 字符 / :root token 定义 ${rootBlock.length} 字符`
  + ` ⇒ 现场扫描体 ${body.length} 字符`)
lines.push('')
lines.push(`① spacing 离 4px 网格：${offGrid.length} 处（基线 ${BASELINE_OFF_GRID_SPACING}，只减不增）`)
for (const r of offGrid) lines.push(`     - ${r.value}  来自  ${r.decl}`)
lines.push(`② font-size 未走 --ks-fs-*：${rawFontSize.length} 处（基线 ${BASELINE_RAW_FONT_SIZE}，只减不增）`)
for (const r of rawFontSize) lines.push(`     - ${r.value}  来自  ${r.decl}`)
lines.push('')
lines.push('基线来历（只减不增）：')
for (const s of SHRINK_LOG) lines.push(`   · ${s}`)

const failures = []
if (offGrid.length > BASELINE_OFF_GRID_SPACING) {
  failures.push(`spacing 离网格 ${offGrid.length} 处 > 冻结基线 ${BASELINE_OFF_GRID_SPACING} 处`)
}
if (rawFontSize.length > BASELINE_RAW_FONT_SIZE) {
  failures.push(`font-size 现场值 ${rawFontSize.length} 处 > 冻结基线 ${BASELINE_RAW_FONT_SIZE} 处`)
}

if (failures.length > 0) {
  console.error(lines.join('\n'))
  console.error('')
  console.error('❌ 尺度棘轮变差了（这不是"要不要修"的问题：UI-BASELINE 第二节要求成体系的尺度）：')
  for (const f of failures) console.error(`   - ${f}`)
  console.error('   ⇒ 把新增的字面值换成 --ks-* token（4px 网格间距 / --ks-fs-* 字号）。')
  console.error('   ⇒ 确有排版理由而 token 表达不了的，**先在 ksGuideStyles.ts 里加 token 并写清理由**，')
  console.error('      不要往本脚本的 EXCEPTIONS 里塞（那是给"字面值本身必须保留"的极少数情况）。')
  process.exit(1)
}

// 变好也要说清：基线该跟着往下走（否则棘轮松了，下次漂回去不会红）。
const better = []
if (offGrid.length < BASELINE_OFF_GRID_SPACING) {
  better.push(`spacing 已是 ${offGrid.length} 处 < 基线 ${BASELINE_OFF_GRID_SPACING}`)
}
if (rawFontSize.length < BASELINE_RAW_FONT_SIZE) {
  better.push(`font-size 已是 ${rawFontSize.length} 处 < 基线 ${BASELINE_RAW_FONT_SIZE}`)
}

console.log(lines.join('\n'))
if (better.length > 0) {
  console.log('')
  console.log('⚠ 比基线更好了 —— **请把脚本顶部的 BASELINE_* 改成新值并在 SHRINK_LOG 记一行**：')
  for (const b of better) console.log(`   - ${b}`)
}
console.log('')
console.log(`✅ 尺度棘轮未变差（spacing ${offGrid.length}/${BASELINE_OFF_GRID_SPACING}，`
  + `font-size ${rawFontSize.length}/${BASELINE_RAW_FONT_SIZE}）`)
