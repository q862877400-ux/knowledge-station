/**
 * ks-dsh-plugin — scripts/smoke-icon-system.mjs
 *
 * **图标体系判据**（spec 008）：把 `docs/UI-ICON-SYSTEM.md` 里写的规范变成机械检查。
 *
 * ## 为什么要有它
 * 实测（2026-10-10）发现：KS 用到的 17 个图标里，**宿主的默认 size 本身就分两档**
 * ——6 个默认 **14**、10 个默认 **16**（`ui-primitives/lib/index.js` 逐个 artwork 的 `size = N`）。
 * ⇒ 同一排按钮里「返回上一层」(14) 紧挨着「新建下级目录」(16)，**天生不齐**。
 * 这不是谁写错了，是**默认值差异**；但**用户看到的是不齐** ⇒ KS 侧必须统一。
 * 光靠"记得传 size"已经失败过一次（本次实测就是证据）⇒ 变成脚本。
 *
 * ## 三组判据（每组都必须能被打红，见 spec 008 的变异验证）
 * ① **尺寸必须显式**：KS 源码里每个 `<Icon…>` 必须显式给 `size={N}`，
 *    且 `N ∈ {16, 28}`（16 = 官方基准档；28 = 空态大图标的专档）。
 *    ⇒ 不给 size 就会吃宿主的默认值（14 或 16），**不齐就从这儿来**。
 * ② **放法**：`<Button>` 的 children 里**不许**出现 `<Icon…>`
 *    —— 官方 `Button` 有 `icon` prop（JSDoc 逐字：*optional leading 16px icon node*），
 *    走它才会套官方 `.icon`（16×16）槽。
 * ③ **声明一致**：`ksHostPrimitives.d.ts` 的图标集合 == 源码实际调用集合（**双向**）。
 *    该文件头自己写着纪律「只声明我们调用的」—— 声明了没人用就是**死声明**。
 *
 * ⚠ 本脚本**只读源码**（不渲染、不联网、零依赖），与 `smoke-ui-scale.mjs` 同一档。
 * ⚠ 已知边界（**如实写，别当没有**）：
 *   · 判据 ① 只保证"显式给了 size 且值在允许集里"，**不保证**渲染出来真的是那个尺寸
 *     （真渲染尺寸由 `ui-render-shot.mjs` 的 DOM 读数负责，两者分工）；
 *   · `--page settings` 等页面在本脚本里不参与（它判的是源码，不是某一次渲染）。
 *
 * 用法：`node plugin/scripts/smoke-icon-system.mjs`（退出码 0 = 合规）
 */
import { readFile, readdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const clientDir = join(dirname(here), 'client')

/** 允许的图标尺寸档（官方 16 基准 + 空态大图 28）。 */
const ALLOWED_SIZES = new Set([16, 28])

/** 声明文件（我们自己维护的那份）。 */
const DECL_FILE = 'ksHostPrimitives.d.ts'

const files = (await readdir(clientDir)).filter((f) => f.endsWith('.tsx') || f.endsWith('.ts'))

/* ─────────────────── ① 尺寸必须显式且落在允许档 ─────────────────── */
const missingSize = []   // 没给 size
const badSize = []       // 给了但不在允许档

for (const f of files) {
  if (f === DECL_FILE) continue
  const src = await readFile(join(clientDir, f), 'utf8')
  // 抓每个自闭合或开标签的 <IconXxx ...>
  for (const m of src.matchAll(/<(Icon[A-Za-z0-9]+)((?:\s[^>]*)?)\/?>/g)) {
    const name = m[1]
    const attrs = m[2]
    const line = src.slice(0, m.index).split('\n').length
    const size = /\bsize=\{(\d+)\}/.exec(attrs)
    if (size === null) {
      missingSize.push(`${f}:${line}  <${name}> 没有显式 size（会吃宿主默认值 ⇒ 尺寸不齐）`)
    } else if (!ALLOWED_SIZES.has(Number(size[1]))) {
      badSize.push(`${f}:${line}  <${name} size={${size[1]}}> 不在允许档 {16, 28}`)
    }
  }
}

/* ─────────────────── ② Button 的 children 里不许有图标 ───────────────────
 *
 * ⚠⚠ **本段的实现坑（写在这里当留痕）**：第一版用正则 `<Button\b([^>]*?)>([\s\S]*?)</Button>`
 *   去抠 Button 的 children，而 `[^>]*?` 会在**属性值含 `>`** 的地方提前收尾 ——
 *   典型是箭头函数属性 `onClick={() => { … }}`（`=>` 里的 `>`）。
 *   后果：抠出来的"children"里混进了属性尾巴 ⇒ **改写明明生效了，判据仍报 24 处不合规**（假红）。
 *   ⇒ 改成**逐字符扫描**标签边界（跳过 `{}` 表达式与引号字符串里的 `>`），不再用正则猜。
 */
function findButtons(src) {
  const out = []
  let i = 0
  const n = src.length
  for (;;) {
    const j = src.indexOf('<Button', i)
    if (j < 0) break
    const k = j + '<Button'.length
    if (k < n && /[A-Za-z0-9_]/.test(src[k])) { i = k; continue }
    let depth = 0
    let quote = null
    let p = k
    for (; p < n; p += 1) {
      const c = src[p]
      if (quote !== null) {
        if (c === '\\') { p += 1; continue }
        if (c === quote) quote = null
      } else if (c === '"' || c === "'" || c === '`') quote = c
      else if (c === '{') depth += 1
      else if (c === '}') depth -= 1
      else if (c === '>' && depth === 0) break
    }
    if (p >= n) break
    const innerStart = p + 1
    const end = src.indexOf('</Button>', innerStart)
    if (end < 0) break
    out.push({ start: j, attrsStart: k, attrsEnd: p, innerStart, innerEnd: end })
    i = end + '</Button>'.length
  }
  return out
}

const iconInChildren = []
for (const f of files) {
  if (f === DECL_FILE) continue
  const src = await readFile(join(clientDir, f), 'utf8')
  for (const b of findButtons(src)) {
    const attrs = src.slice(b.attrsStart, b.attrsEnd)
    const inner = src.slice(b.innerStart, b.innerEnd)
    if (!/<Icon[A-Za-z0-9]+/.test(inner)) continue
    const line = src.slice(0, b.start).split('\n').length
    const hasIconProp = /\bicon=/.test(attrs)
    const cls = /className="([^"]*)"/.exec(attrs)
    iconInChildren.push(`${f}:${line}  className=${cls === null ? '(无)' : cls[1]}`
      + `  ${hasIconProp ? '（已用 icon prop，但 children 里还有图标）' : '（未用官方 icon prop）'}`)
  }
}

/* ─────────────────── ③ 声明集合 == 调用集合（双向） ─────────────────── */
const used = new Set()
for (const f of files) {
  if (f === DECL_FILE) continue
  const src = await readFile(join(clientDir, f), 'utf8')
  for (const m of src.matchAll(/\b(Icon[A-Za-z0-9]+)\b/g)) used.add(m[1])
}

const declSrc = await readFile(join(clientDir, DECL_FILE), 'utf8')
const declared = new Set()
/* ⚠⚠ **只认真正的 `export const IconXxx` 声明行**（2026-10-10 修，留痕）：
 *   第一版扫的是"文件里出现的所有 `IconXxx` 字样" ⇒ 把**注释里提到的名字**
 *   （如"删掉 IconQueueOutlineRegular 的调用点"这种留痕句）也算成"声明了" ⇒
 *   报出 12 条**并不存在**的死声明（假红）。
 *   ⇒ 改成只匹配 `export const <名字>`，注释里的名字不再计入。
 *   ⚠ 这不是"放宽判据"：真正的声明**一个都没漏**（真声明行必然是 `export const`），
 *     而被排除的是**注释**，它本来就不构成声明。 */
for (const m of declSrc.matchAll(/^\s*export\s+const\s+(Icon[A-Za-z0-9]+)\b/gm)) declared.add(m[1])

/* ⚠ `IconProps` 是**类型**不是图标 —— 从两边的集合里排除（否则它会永远算"声明了没人用"）。 */
used.delete('IconProps')
declared.delete('IconProps')

const usedNotDeclared = [...used].filter((n) => !declared.has(n)).sort()
const declaredNotUsed = [...declared].filter((n) => !used.has(n)).sort()

/* ─────────────────────────────── 报告 ─────────────────────────────── */
const lines = []
lines.push(`客户端源：${clientDir}（${files.length} 个文件）`)
lines.push(`允许的图标尺寸档：${[...ALLOWED_SIZES].join(' / ')}`)
lines.push('')
lines.push(`① 没显式给 size：${missingSize.length} 处`)
for (const r of missingSize) lines.push(`     - ${r}`)
lines.push(`   给了但不在允许档：${badSize.length} 处`)
for (const r of badSize) lines.push(`     - ${r}`)
lines.push(`② Button 的 children 里嵌图标：${iconInChildren.length} 处`)
for (const r of iconInChildren) lines.push(`     - ${r}`)
lines.push(`③ 声明一致性：调用 ${used.size} 个 / 声明 ${declared.size} 个`)
lines.push(`   调用了但没声明：${usedNotDeclared.length} 个`)
for (const n of usedNotDeclared) lines.push(`     - ${n}`)
lines.push(`   声明了但没人用（死声明）：${declaredNotUsed.length} 个`)
for (const n of declaredNotUsed) lines.push(`     - ${n}`)

const failures = []
if (missingSize.length > 0) failures.push(`① 有 ${missingSize.length} 个图标没显式给 size`)
if (badSize.length > 0) failures.push(`① 有 ${badSize.length} 个图标的 size 不在允许档`)
if (iconInChildren.length > 0) failures.push(`② 有 ${iconInChildren.length} 处 Button 的 children 里嵌了图标`)
if (usedNotDeclared.length > 0) failures.push(`③ 有 ${usedNotDeclared.length} 个图标调用了但没声明`)
if (declaredNotUsed.length > 0) failures.push(`③ 有 ${declaredNotUsed.length} 个死声明`)

if (failures.length > 0) {
  console.error(lines.join('\n'))
  console.error('')
  console.error('❌ 图标体系不合规（规范见 docs/UI-ICON-SYSTEM.md）：')
  for (const f of failures) console.error(`   - ${f}`)
  console.error('   ⇒ ① 每个 <Icon…> 显式给 size，值用 16（基准）或 28（空态大图）；')
  console.error('      ② 进 Button 的图标走官方 icon prop，不要塞 children；')
  console.error('      ③ ksHostPrimitives.d.ts 只声明真正调用的（文件头自己写着这条纪律）。')
  process.exit(1)
}

console.log(lines.join('\n'))
console.log('')
console.log(`✅ 图标体系合规（尺寸显式 ${used.size - missingSize.length - badSize.length}/${used.size}`
  + ` ｜ Button 内嵌 0 ｜ 死声明 0）`)
