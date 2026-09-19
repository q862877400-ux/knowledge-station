/**
 * ks-dsh-plugin — scripts/lib/ks-primitives-stub.mjs
 *
 * 宿主 `@deepseek-ai/dsh-client-ui-primitives` 的**共享桩**（**单一所有者**）。
 *
 * ## ⚠ 规矩（一句话）
 * **加一个宿主组件，只需要改 `plugin/client/**` 的源码 —— 不需要动任何冒烟。**
 * 每个"要在 Node 里打包客户端代码"的冒烟都通过本文件拿桩（`ksClientPrimitivesAlias`），
 * 成员名单**从源码派生**（下面 `collectHostPrimitiveImports`），桩由名单生成。
 * **不允许**再在任何冒烟里手写 `export const X = Null` 列表。
 *
 * ## 为什么要有这个文件（同一根因，**第三次**踩）
 * 宿主 ui-primitives 是浏览器端的**基线单例**（`packages/client/web/src/seed.ts` 的 seed 映射之一）
 * ⇒ 在 Node 里跑冒烟时盘上没有这个包，必须 `alias` 到一份桩。桩漏一个成员，esbuild 就是
 * `No matching export in "…/primitives.mjs"` ⇒ 整步 exit 1。前两次：
 *   ① `smoke-settings.mjs` 根本没写 alias ⇒ 构建直接 `Could not resolve`（第 5 步 5c 换宿主 `Button` 时）；
 *   ② `smoke-client-entry.mjs` 的桩漏 4 个新图标（第 5 步 P0 新用 `IconInfoOutline14` 等）；
 *   ③ `smoke-kb-page-render.mjs` 的桩漏 `IconInfoOutline14` / `IconPlusOutline16` /
 *      `IconFolderOpenOutline16`（2026-10 第 5 步 P0）—— 本次修的就是它。
 * 三次的根因同一个：**名单有多个所有者**（每个冒烟自己维护一份）。现在名单只有这一份。
 *
 * ## 派生逻辑（`collectHostPrimitiveImports`）
 * 扫 `plugin/client/**\/*.{ts,tsx}` 里所有
 * `import … from '@deepseek-ai/dsh-client-ui-primitives'`，返回**排序去重后的名字集合**：
 *   - `import { A, B as C }` → 收 `A` 与 **`B`**（桩要导出的是**被导入的那个名字**，
 *     源码里用 `C` 是它自己的事 —— 这条第一版最容易写错）；
 *   - **多行 import** 照收（正则跨行，`[^;'"]` 含换行）；
 *   - `import type { X }` 与内联 `{ type X, Y }` 里的 `X` **不收**（类型在 esbuild 的 ts loader
 *     里被抹掉，运行时不存在这个导出）；
 *   - `import * as NS from '…'` / 默认导入 / `export * from '…'` 这类**无法静态枚举**的写法
 *     ⇒ **当场抛错并点名文件:行**（"识别不了就点名，不许静默漏"）；包**子路径**导入同样点名；
 *   - 注释里的 import 不会被误收（行首是 `//` 或 `*` 的匹配跳过）。
 *
 * ## 桩的形状（判据 = 我们在源码里**怎么用**它，不是猜）
 * `collectHostPrimitiveMembers` 顺带分类（真读 `plugin/client/**`）：
 *   - 当**组件**用（`<X …/>` 出现，或只在值位置出现）⇒ 导出一个组件；
 *     其中我们真的渲染/断言的几个原语（Button/Checkbox/Tag/Pill/Input/Menu/Switch/Modal）
 *     给**按宿主源码形状写的最小实现**（`<button>`/`<input type=checkbox>`/`[role=dialog]`…），
 *     否则渲染级冒烟的 DOM 断言会全部落空；`Icon*` 一律给一枚 `<svg data-host-icon=名字>`；
 *     认不出的组件给 `() => null`。
 *   - 当**函数**用（源码里出现 `X(` 调用）⇒ 给**可调用的最小实现**（文本类工具回 `''`），
 *     不给 `Null` —— 否则 SSR 期间一调用就炸。
 *   - 当**常量/命名空间**用（只出现 `X.`）⇒ 给 `Object.freeze({})`。
 *
 * ## 防复发
 * `primitivesStubGaps(pluginRoot, stubSource)` 把"源码导入集合 − 桩导出集合"算出来；
 * `smoke-settings.mjs`（最便宜的那个）拿它做**一条断言**：缺谁就点名谁。
 * 生成侧也有一道：名单里有无法枚举的写法时 `collectHostPrimitiveImports` 直接抛。
 *
 * ## 边界（诚实）
 * - 桩是"形状"不是宿主实现：它保证**能打包 + 能渲染出可断言的结构**，
 *   **不**保证视觉、不保证宿主组件的内部行为。
 * - 本文件**不**校验"这个名字在真宿主里存不存在"（那是另一件事）。2026-10 逐个核过
 *   `ui-primitives/src/index.ts` 与 `icons/index.tsx`：当前 13 个成员**全部真实存在**
 *   （含 5 个 `Icon*Outline1x`）。要加新成员，仍应先读宿主源码确认导出名。
 */

import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'

/** 宿主原语的模块标识（唯一真源；冒烟的 alias 键就是它）。 */
export const HOST_PRIMITIVES_SPECIFIER = '@deepseek-ai/dsh-client-ui-primitives'

/** 匹配"包根"或"包子路径"（子路径要单独点名，见 `scanClientImports`）。 */
const SPEC_PREFIX_RE = /^@deepseek-ai\/dsh-client-ui-primitives(\/|$)/

/**
 * 一条 `import/export … from '…'` 语句。
 * ⚠ `[^;'"]` 里**含换行** ⇒ 多行 import 照收；非贪婪到 `from` 为止。
 */
const STATEMENT_RE = /(?:^|[\s;}()])(import|export)\s+(type\s+)?([^;'"]*?)\s*from\s*['"]([^'"]+)['"]/g

/** 动态 `import('…')` —— 同样无法静态枚举，点名。 */
const DYNAMIC_IMPORT_RE = /\bimport\s*\(\s*['"]([^'"]*dsh-client-ui-primitives[^'"]*)['"]/g

/** 递归收集 `plugin/client/**\/*.{ts,tsx}`（`.d.ts` 也在此列，代码里注释掉的 import 由注释判据挡掉）。 */
function listSourceFiles(root) {
  const out = []
  const walk = (dir) => {
    let entries
    try {
      entries = readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const p = join(dir, e.name)
      if (e.isDirectory()) {
        if (e.name === 'node_modules') continue
        walk(p)
      } else if (/\.(ts|tsx)$/.test(e.name)) {
        out.push(p)
      }
    }
  }
  walk(root)
  return out.sort()
}

/** 匹配位置是否落在注释里（只看**同行**前缀：`//` 或块注释的 `*`）。 */
function inComment(text, index) {
  const lineStart = text.lastIndexOf('\n', index - 1) + 1
  const prefix = text.slice(lineStart, index).trim()
  return prefix.startsWith('//') || prefix.startsWith('*') || prefix.startsWith('/*') || prefix.startsWith('*/')
}

const lineOf = (text, index) => text.slice(0, index).split('\n').length

/**
 * 扫描客户端源码。
 * @returns {{ entries: Array<{file: string, line: number, imported: string, local: string}>,
 *             blockers: Array<{file: string, line: number, why: string}>,
 *             sources: Map<string, string> }}
 *   `entries` 只关心**运行时真的需要桩导出**的具名导入；
 *   `blockers` 是"识别不了"的写法，调用方**必须**把它们变成异常（不静默漏）。
 */
export function scanClientImports(pluginRoot) {
  const entries = []
  const blockers = []
  const sources = new Map()
  for (const abs of listSourceFiles(join(pluginRoot, 'client'))) {
    const file = relative(pluginRoot, abs).replace(/\\/g, '/')
    const text = readFileSync(abs, 'utf8')
    sources.set(file, text)

    const push = (line, why) => blockers.push({ file, line, why })

    DYNAMIC_IMPORT_RE.lastIndex = 0
    for (const m of text.matchAll(DYNAMIC_IMPORT_RE)) {
      if (inComment(text, m.index)) continue
      push(lineOf(text, m.index), `动态 import('${m[1]}')：无法静态枚举它取用的成员`)
    }

    STATEMENT_RE.lastIndex = 0
    let m
    while ((m = STATEMENT_RE.exec(text)) !== null) {
      const [, keyword, typePrefix, clauseRaw, spec] = m
      if (!SPEC_PREFIX_RE.test(spec)) continue
      if (inComment(text, m.index)) continue
      const line = lineOf(text, m.index)
      if (spec !== HOST_PRIMITIVES_SPECIFIER) {
        push(line, `包子路径导入 '${spec}'：冒烟的 alias 只覆盖包根 ${HOST_PRIMITIVES_SPECIFIER}`)
        continue
      }
      // `import type { … }` / `export type { … }`：整条都是类型，运行时不存在 ⇒ 桩不需要。
      if (typePrefix) continue
      const clause = clauseRaw.trim()
      if (clause === '') continue // 副作用导入（`import '…'`）：无导出需求
      if (clause === '*') {
        push(line, `\`${keyword} * from …\`：无法枚举被转出的成员`)
        continue
      }
      const asNamespace = /^\*\s+as\s+[A-Za-z_$][\w$]*$/.exec(clause)
      if (asNamespace) {
        push(line, `命名空间导入 \`${clause}\`：无法静态知道经它访问了哪些成员 ⇒ 改成具名导入`)
        continue
      }
      const braced = /^\{([\s\S]*)\}$/.exec(clause)
      if (!braced) {
        push(line, `默认导入 / 无法解析的 ${keyword} 子句 \`${clause}\``)
        continue
      }
      for (const raw of braced[1].split(',')) {
        const s = raw.trim()
        if (s === '') continue
        if (/^type\s+/.test(s)) continue // 内联 `type X`
        const sm = /^([A-Za-z_$][\w$]*)(?:\s+as\s+([A-Za-z_$][\w$]*))?$/.exec(s)
        if (!sm) {
          push(line, `无法解析的导入项 \`${s}\``)
          continue
        }
        // ⚠ 收的是 **imported**（`B as C` 里的 `B`）—— 桩要导出的是这个名字。
        entries.push({ file, line, imported: sm[1], local: sm[2] ?? sm[1] })
      }
    }
  }
  return { entries, blockers, sources }
}

function blockersToError(blockers) {
  return new Error(
    '❌ 从源码派生宿主原语名单时遇到**无法枚举**的导入写法（不许静默漏，故当场报错）：\n'
    + blockers.map((b) => `   - ${b.file}:${b.line} — ${b.why}`).join('\n')
    + `\n   → 改成具名导入（\`import { X } from '${HOST_PRIMITIVES_SPECIFIER}'\`）后重跑。`,
  )
}

/**
 * 扫出源码里**真正 import 的**宿主原语成员名（排序去重）。
 * 遇到无法枚举的写法（命名空间/默认/`export *`/子路径/动态 import）**直接抛**，并点名文件:行。
 * @param {string} pluginRoot 插件根（含 `client/`）
 * @returns {string[]}
 */
export function collectHostPrimitiveImports(pluginRoot) {
  const { entries, blockers } = scanClientImports(pluginRoot)
  if (blockers.length > 0) throw blockersToError(blockers)
  return [...new Set(entries.map((e) => e.imported))].sort()
}

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/**
 * 判定每个成员在源码里**被当什么用**（组件 / 函数 / 常量）。
 * 证据顺序：JSX 用法 > 调用 `X(` > 属性访问 `X.` > 裸出现（值位置，按组件算）。
 * 只在该成员**被导入的那个文件**里找用法（避免同名局部变量串味）。
 */
function classifyMembers(entries, sources) {
  /** @type {Map<string, Array<{file: string, local: string}>>} */
  const usesByName = new Map()
  for (const e of entries) {
    if (!usesByName.has(e.imported)) usesByName.set(e.imported, [])
    usesByName.get(e.imported).push({ file: e.file, local: e.local })
  }
  const kinds = new Map()
  for (const [name, uses] of usesByName) {
    const hit = { jsx: false, call: false, prop: false, bare: false }
    for (const u of uses) {
      const text = sources.get(u.file) ?? ''
      const esc = escapeRe(u.local)
      if (!hit.jsx && new RegExp(`<\\s*${esc}(?=[\\s/>])`).test(text)) hit.jsx = true
      if (!hit.call && new RegExp(`(?<![\\w$.])${esc}\\s*\\(`).test(text)) hit.call = true
      if (!hit.prop && new RegExp(`(?<![\\w$])${esc}\\s*\\.`).test(text)) hit.prop = true
      if (!hit.bare && new RegExp(`(?<![\\w$.])${esc}(?![\\w$])`).test(text)) hit.bare = true
    }
    if (hit.jsx) kinds.set(name, 'component')
    else if (hit.call) kinds.set(name, 'function')
    else if (hit.prop) kinds.set(name, 'constant')
    else if (hit.bare) kinds.set(name, 'component') // 值位置（多为当作组件/图标传递）
    else kinds.set(name, 'component') // 只在 import 里出现（当前未用）：按组件给，最小面
  }
  return kinds
}

/**
 * 扫出成员 + 每个成员的用法分类（给 `writePrimitivesStub` 用）。
 * @returns {Array<{name: string, kind: 'component'|'function'|'constant'}>}
 */
export function collectHostPrimitiveMembers(pluginRoot) {
  const { entries, blockers, sources } = scanClientImports(pluginRoot)
  if (blockers.length > 0) throw blockersToError(blockers)
  const names = [...new Set(entries.map((e) => e.imported))].sort()
  const kinds = classifyMembers(entries, sources)
  return names.map((name) => ({ name, kind: kinds.get(name) ?? 'component' }))
}

/* ────────────────────────── 桩的形状（按宿主源码形状写的最小实现） ──────────────────────────
 * ⚠ 这里**只放形状**，不放名单：名单永远从源码派生。
 * ⚠ 这几个 DOM 形状是**渲染级冒烟的断言基础**（`input[type=checkbox]` 计数、`[role=dialog]`、
 *   `button[data-active]`…）⇒ 不能退化成 `() => null`，否则那是"把冒烟改绿"而不是"修根因"。
 *   形状逐字取自宿主 `ui-primitives/src/*.tsx`（Button/Checkbox/Tag/Pill/Input/Menu/Switch/Modal）。
 */
const DOM_SHAPES = {
  Button: [
    "({ variant = 'ghost', size = 'md', icon, className, children, ...rest }) =>",
    "  h('button', { type: 'button', 'data-variant': variant, 'data-size': size, className, ...rest }, icon, children)",
  ],
  Checkbox: [
    '({ checked, onChange, label, disabled, title, className }) =>',
    "  h('label', { className, title },",
    "    h('input', { type: 'checkbox', checked, disabled, onChange: (e) => { onChange(e.target.checked) } }),",
    '    h(\'span\', null, label))',
  ],
  Tag: [
    "({ tone = 'outline', className, children }) =>",
    "  h('span', { 'data-tone': tone, className }, children)",
  ],
  Pill: [
    "({ active = false, className, children, onClick, ...rest }) =>",
    '  onClick',
    "    ? h('button', { type: 'button', 'data-active': String(active), className, onClick, ...rest }, children)",
    "    : h('span', { 'data-active': String(active), className }, children)",
  ],
  Input: [
    "({ icon, className, ...rest }) => h('span', { className }, icon, h('input', rest))",
  ],
  /** Menu 桩：把 items 渲染成按钮（"新建下拉里有什么"可断言），并渲染 anchor。 */
  Menu: [
    "({ open, items, anchor, onSelect, onClose }) =>",
    "  h('span', { 'data-open': String(open) },",
    '    anchor,',
    "    open ? h('div', { role: 'menu' },",
    '      items.map((it) => h(\'button\', {',
    "        key: it.id, type: 'button', role: 'menuitem',",
    '        onClick: () => { onSelect?.(it.id); onClose?.() },',
    '      }, it.label))) : null)',
  ],
  Switch: [
    '({ checked, onChange, label, disabled, title, className }) =>',
    "  h('label', { className, title },",
    "    h('input', { type: 'checkbox', role: 'switch', checked, disabled,",
    '      onChange: (e) => { onChange(e.target.checked) } }),',
    '    h(\'span\', null, label))',
  ],
  /** Modal 桩：open 时渲染成可见容器（"窗里有什么"可断言）。 */
  Modal: [
    '({ open, onClose, title, description, children, footer, closeLabel }) =>',
    "  open === false ? null : h('div', { role: 'dialog', 'aria-label': title, className: 'ks-modal-stub' },",
    "    h('div', { className: 'ks-modal-title' }, title),",
    '    description ? h(\'p\', null, description) : null,',
    "    h('button', { type: 'button', 'aria-label': closeLabel ?? 'close', onClick: () => { onClose?.() } }, '×'),",
    "    h('div', { className: 'ks-modal-body' }, children),",
    "    footer ? h('div', { className: 'ks-modal-footer' }, footer) : null)",
  ],
}

/** 已知**函数**类导出（工具函数）的最小实现 —— 可调用、不抛。 */
const KNOWN_FUNCTIONS = {
  relativeTime: "(_t, _now) => ''",
  fileSizeText: "(_bytes) => ''",
  classifyFileType: "(_name) => ''",
  fileExtension: "(_name) => ''",
  classifyLinkPath: "(_path) => ''",
  extractMarkdownPlainText: "(_md) => ''",
  projectUserText: "(_text, _refs) => ''",
  isDarwinDesktop: '() => false',
  writeClipboard: 'async () => {}',
  diffTotals: '() => ({ added: 0, removed: 0 })',
  rankByName: '(_a, _b) => 0',
}

/** 已知**常量**类导出。 */
const KNOWN_CONSTANTS = {
  FISH_LOGO_PATH: "''",
  FISH_LOGO_VIEWBOX: "'0 0 0 0'",
  DEFAULT_TERMINAL_MAX_LINES: '0',
  DEFAULT_READ_MAX_LINES: '0',
  DEFAULT_DIFF_MAX_LINES: '0',
  DEFAULT_SEARCH_MAX_LINES: '0',
}

/** 把一个成员归一化成 export 语句（多行）。 */
function memberLines(member) {
  const { name, kind = 'component' } = typeof member === 'string' ? { name: member } : member
  if (kind === 'function') {
    return [`export const ${name} = ${KNOWN_FUNCTIONS[name] ?? "((..._args) => '')"}`]
  }
  if (kind === 'constant') {
    return [`export const ${name} = ${KNOWN_CONSTANTS[name] ?? 'Object.freeze({})'}`]
  }
  if (/^Icon[A-Z]/.test(name)) {
    return [
      `export const ${name} = ({ size, className } = {}) =>`
      + ` h('svg', { 'data-host-icon': ${JSON.stringify(name)}, width: size, height: size, className })`,
    ]
  }
  const shape = DOM_SHAPES[name] ?? ['() => null']
  return [`export const ${name} = ${shape[0]}`, ...shape.slice(1)]
}

/**
 * 生成桩源码（纯函数，便于测试/比对）。
 * @param {Array<string|{name: string, kind?: string}>} members
 */
export function renderPrimitivesStubSource(members) {
  const norm = members.map((m) => (typeof m === 'string' ? { name: m, kind: 'component' } : m))
  const header = [
    '/**',
    ' * ⚠ **自动生成，请勿手改** —— 宿主 `@deepseek-ai/dsh-client-ui-primitives` 的桩。',
    ' *',
    ` * 成员名单（${norm.length} 个）由 \`plugin/scripts/lib/ks-primitives-stub.mjs\` **从源码派生**：`,
    ` *   ${norm.map((m) => m.name).join(', ')}`,
    ' *',
    ' * ⇒ **加一个宿主组件，只需要改 `plugin/client/**` 的源码；不需要动任何冒烟。**',
    ' *   （以前每个"要打包客户端代码"的冒烟各维护一份手写名单，漏一个就 No matching export。',
    ' *   同一根因已踩三次：smoke-settings 漏 alias / smoke-client-entry 漏 4 图标 /',
    ' *   smoke-kb-page-render 漏 3 图标。）',
    ' */',
    "import { createElement as h } from 'react'",
    '',
    '/* eslint-disable */',
    '',
  ]
  const body = []
  for (const m of norm) body.push(...memberLines(m))
  return [...header, ...body, ''].join('\n')
}

/**
 * 写一份桩到 `targetPath`（目录不存在则建）。
 * @param {string} targetPath
 * @param {Array<string|{name: string, kind?: string}>} members `collectHostPrimitiveMembers()` 的结果，
 *   或退化形式：成员名数组（此时按名字推断形状：`Icon*` → 图标，其余 → 组件）。
 * @returns {string[]} 实际导出的成员名
 */
export function writePrimitivesStub(targetPath, members) {
  const list = members.map((m) => (typeof m === 'string' ? { name: m, kind: 'component' } : m))
  mkdirSync(dirname(targetPath), { recursive: true })
  writeFileSync(targetPath, renderPrimitivesStubSource(list), 'utf8')
  return list.map((m) => m.name)
}

/** 从桩源码里解析出它**实际导出**的成员名。 */
export function stubExportNames(stubSource) {
  return [...new Set([...stubSource.matchAll(/^export const ([A-Za-z_$][\w$]*)/gm)].map((m) => m[1]))]
}

/**
 * 防复发判据：**桩的导出集合 ⊇ 源码里实际导入的集合**。
 * @returns {string[]} 缺的成员（空数组 = 覆盖完整）
 */
export function primitivesStubGaps(pluginRoot, stubSource) {
  const have = new Set(stubExportNames(stubSource))
  return collectHostPrimitiveImports(pluginRoot).filter((n) => !have.has(n))
}

/**
 * 便捷函数：把"派生 + 写桩"一次做完，返回可直接塞进 esbuild `alias` 的对象。
 * ⚠ 名单无法枚举时**抛**（不静默漏）。
 * @param {string} pluginRoot 插件根（含 `client/`）
 * @param {string} tmpDir 放桩的临时目录（调用方负责清理）
 * @returns {{ [HOST_PRIMITIVES_SPECIFIER]: string }} 例：`{ '@deepseek-ai/dsh-client-ui-primitives': '…/ks-host-primitives.stub.mjs' }`
 */
export function ksClientPrimitivesAlias(pluginRoot, tmpDir) {
  const members = collectHostPrimitiveMembers(pluginRoot)
  const stubPath = join(tmpDir, 'ks-host-primitives.stub.mjs')
  writePrimitivesStub(stubPath, members)
  return { [HOST_PRIMITIVES_SPECIFIER]: stubPath }
}
