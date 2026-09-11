/**
 * ks-dsh-plugin — scripts/smoke-bs-contract.mjs
 *
 * better-sidebar 契约冒烟（用户 2026-09-09：「我们这一套建立在 better-sidebar 上，
 * 万一人家更新了怎么办」）。
 *
 * 本插件客户端半重度依赖第三方 `dsh-better-sidebar`（tab 注册、外链接管、单例
 * path 覆写、侧栏宽度/偏好读写、tab 生命周期）。上游升级可能改名/删方法/改 state
 * 形状——运行时的 `?.` 只能保证不崩，不会告诉你"哪块功能静默退化了"。
 *
 * 这个脚本对**已安装版本**的类型声明做同源断言：把我们真正用到的方法、字段、
 * 常量、能力名逐条查一遍。上游一升级就 `npm run smoke` 报红，而不是等用户点开
 * PDF 才发现。找不到安装包时打印 SKIP（不失败）——本机没装 DSH profile 也能跑。
 *
 * 用法：node scripts/smoke-bs-contract.mjs
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const PKG = 'dsh-better-sidebar'

/** 候选安装位置：DSH profile（真实运行位置）→ 插件/仓库本地。 */
function candidates() {
  const home = process.env.DSH_HOME || join(homedir(), '.dsh')
  const profilesDir = join(home, 'profiles')
  const out = []
  const profile = process.env.DSH_PROFILE
  if (profile) out.push(join(profilesDir, profile, 'node_modules', PKG))
  try {
    for (const name of readdirSync(profilesDir)) {
      out.push(join(profilesDir, name, 'node_modules', PKG))
    }
  } catch { /* 没有 profiles 目录 */ }
  out.push(join(pluginRoot, 'node_modules', PKG))
  out.push(join(pluginRoot, '..', 'node_modules', PKG))
  return out
}

/** 递归找出包内所有 .d.ts（上游可能把类型放在 lib/types 或 dist）。 */
function findDts(dir, acc = [], depth = 0) {
  if (depth > 6) return acc
  let entries
  try { entries = readdirSync(dir, { withFileTypes: true }) } catch { return acc }
  for (const e of entries) {
    const p = join(dir, e.name)
    if (e.isDirectory()) {
      if (e.name === 'node_modules') continue
      findDts(p, acc, depth + 1)
    } else if (e.name.endsWith('.d.ts')) {
      acc.push(p)
    }
  }
  return acc
}

const found = candidates().find((p) => existsSync(join(p, 'package.json')))
if (found === undefined) {
  console.log(`SKIP  ${PKG} 未安装（本机没有 DSH profile 或未装该插件）——契约冒烟跳过`)
  process.exit(0)
}

const pkg = JSON.parse(readFileSync(join(found, 'package.json'), 'utf8'))
const dtsFiles = findDts(found)
const serviceDts = dtsFiles.filter((p) => /service\.d\.ts$/.test(p))
const stateDts = dtsFiles.filter((p) => /state\.d\.ts$/.test(p))
const readAll = (files) => files.map((p) => readFileSync(p, 'utf8')).join('\n')
const serviceText = readAll(serviceDts)
const stateText = readAll(stateDts)
/** 全部 .d.ts 的并集：prefs（pluginSettings）等字段声明在第三个文件里。 */
const allText = readAll(dtsFiles)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
const has = (text, needle) => text.includes(needle)

console.log(`=== better-sidebar contract smoke (${pkg.name}@${pkg.version}) ===`)
console.log(`install: ${found}`)
console.log(`types:   ${serviceDts.length} service / ${stateDts.length} state .d.ts\n`)

// ---- 1. 我们注册/调用服务方法（entry.ts、KsEvidenceTab、KsBookmarksTab、KsReportTab）
check('service.d.ts found', serviceDts.length > 0)
check('state.d.ts found', stateDts.length > 0)
for (const [name, needle] of [
  ['registerTab', 'registerTab('],
  ['openTab', 'openTab('],
  ['updateTab', 'updateTab('],
  ['getSnapshot', 'getSnapshot()'],
  ['subscribeState', 'subscribeState('],
  ['closeTab', 'closeTab('],
  ['isTabEnabled', 'isTabEnabled('],
  ['features (capability list)', 'features:'],
  ['version (service version)', 'version:'],
]) {
  check(`service.${name}`, has(serviceText, needle))
}

// ---- 2. TabDescriptor 字段（entry.ts 的注册面 + 生命周期/设置）
for (const [name, needle] of [
  ['TabDescriptor', 'interface TabDescriptor'],
  ['descriptor.urlTarget', 'urlTarget?'],
  ['descriptor.single', 'single?'],
  ['descriptor.dedupeKey', 'dedupeKey?'],
  ['descriptor.component', 'component:'],
  ['descriptor.settings', 'settings?'],
  ['settings.pluginToggles', 'pluginToggles'],
  ['TabComponentProps.visible', 'visible: boolean'],
  ['TabComponentProps.scope', 'scope: SessionScope'],
  ['TabComponentProps.store', 'store: SidebarStore'],
]) {
  check(`service.${name}`, has(serviceText, needle))
}

// ---- 3. 我们读写的 SidebarState 面（pdfPanel.ts / KsEvidenceTab / KsSettingsSection）
for (const [name, needle] of [
  ['SidebarState.width', 'width: number'],
  ['PANEL_MAX', 'PANEL_MAX'],
  ['FloatWindow', 'FloatWindow'],
]) {
  check(`state.${name}`, has(stateText, needle))
}
// prefs 形状（pluginSettings 声明在 prefs-shared.d.ts，不在 state.d.ts）
check('prefs.pluginSettings (any .d.ts)', has(allText, 'pluginSettings'))
check('store.update(draft)', has(stateText, 'update(mutator'))
check('store.tabOpen(sessionId, tabId)', has(stateText, 'tabOpen('))

// ---- 4. 我们做能力门控的能力名必须还在（上游承诺只增不减）
const featureNames = ['tabMeta', 'updateTab', 'stateSubscription', 'pluginSettings', 'urlTarget']
for (const f of featureNames) {
  check(`feature:${f}`, has(serviceText, `"${f}"`))
}

// ---- 5. 版本与插件记录的验证版本比对（只提示，不判失败）
const TESTED = '0.18.0'
if (pkg.version !== TESTED) {
  console.log(`\nNOTE  已安装版本 ${pkg.version} ≠ 本插件验证版本 ${TESTED}；若上面全绿可放心，`
    + '否则请按失败项调整 client/（bsContract.ts 的 BS_TESTED_VERSION 同步更新）。')
} else {
  console.log(`\nNOTE  版本与本插件验证版本一致（${TESTED}）。`)
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== bs-contract smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
