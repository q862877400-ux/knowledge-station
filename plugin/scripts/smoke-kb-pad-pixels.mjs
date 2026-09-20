#!/usr/bin/env node
/**
 * plugin/scripts/smoke-kb-pad-pixels.mjs — **「页面留边」的像素断言巡查**（5j-补，2026-09-20）
 *
 * ## 它解决什么（复核 `verify-freeze-5j` 打回 E②）
 * 5j 把 `#kspad` 从报告值升级成了真断言（`ui-render-shot.mjs` 的 `ksPadCheck`，变异 M1/M2 打红），
 * 但复核量出一件要害：**这条像素断言根本不在任何门禁链里** ——
 * `smoke-all.mjs` 的名单不含 `smoke-kb-cols.mjs` / `ui-badge-pixels.mjs`（唯二会 spawn
 * `ui-render-shot` 的脚本），`run-gates.ps1` 也不含 ⇒ "5j 在门禁内的实际保护只有 jsdom 那 5 条"。
 * 同一份复核还用变异 M3 证明：`.ks-batch`"不许挤成两行"这条**只有 `--interact kb-select` 那条路**
 * 会触发，而 `smoke-kb-cols.mjs` 固定用 `kb-files`（那个场景没有批量条）⇒ 折行回归**没有任何脚本抓得到**。
 * 本脚本把 `ksPadCheck` 按**一组冻死的 (page, width, interact) 组合**跑一遍，任一条红即红；
 * 它**进 `smoke-all.mjs` 名单**（见那里的注释与 docs/UI-BASELINE.md 5j-补 的取舍登记）。
 *
 * ## 边界（诚实，别把它读成"整页视觉验收"）
 * - 只判 `ksPadCheck`：**留边几何**（元素外缘到 shell 内容边的距离、档位、批量条折行）
 *   与**存在性**（规范点名的适用面这一跑必须量到 —— 复核 E① 的 M6 就是"元素消失也不红"）。
 *   其余视觉问题（对比度、排版、hover/focus）它不管。
 * - 要真浏览器（同 `ui-render-shot.mjs`）：找不到无头浏览器 ⇒ `ui-render-shot` 自己**报错退出**，
 *   本脚本按失败转达（"没跑"≠"通过"）。⚠ 这意味着**门禁链从 5j-补 起需要本机有 Chromium/Edge**
 *   —— 这是**有意的取舍**，理由与代价登记在 docs/UI-BASELINE.md 5j-补（别再当成疏漏）。
 * - 组合表**是冻死的**：少跑一组就等于少保护一组。改表要同时改本文件与
 *   `ui-render-shot.mjs` 的 `PAD_REQUIRED`（那一侧判"声明 ↔ 实际"）。
 *
 * 用法：`node plugin/scripts/smoke-kb-pad-pixels.mjs`（无参数；没有开关 = 没有绕过路）
 * 退出码：0 = 每一组都判过且都合规；1 = 任一组红/没判到；2 = 参数错（本脚本不收参数）。
 */
import { spawnSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '..', '..')
const shotScript = join(here, 'ui-render-shot.mjs')

if (process.argv.slice(2).length > 0) {
  console.error(`❌ 本脚本不收参数（拿到 ${JSON.stringify(process.argv.slice(2))}）—— 组合表在文件里冻死，`)
  console.error('   防止"少跑一组"被当成通过。要改覆盖面就改 MATRIX 与 ui-render-shot 的 PAD_REQUIRED。')
  process.exit(2)
}

/**
 * **冻死的组合表**（唯一所有者）。每组都要满足：
 *   ① `ui-render-shot` exit 0（缺件/截图失败/任何自检红都在那里变非零）；
 *   ② `ksPadCheck.skipReason === null`（"这一跑不判"不算通过）；
 *   ③ `ksPadCheck.checked === true`；
 *   ④ `ksPadCheck.coverageDeclared === true`（这一组在 `PAD_REQUIRED` 里声明了期望元素，
 *      否则存在性没判 —— 那正是复核 E① 的假绿通道）；
 *   ⑤ `problems` 空（贴边 / 档位错 / 批量条折行 / 适用面消失，都在这里报）。
 * 覆盖要求（下面还会独立判一次）：**窄档与宽档都必须至少有一组**。
 *   ⚠ `interact` 空串 = 用 `ui-render-shot` 里 PAGES 的默认场景（kb 是 []、ingest 是 ingest-batch）。
 */
const MATRIX = [
  { page: 'kb', width: 520, interact: '', note: '默认态：卡片带 + 一级目录' },
  { page: 'kb', width: 1300, interact: '', note: '默认态（宽档）' },
  { page: 'kb', width: 520, interact: 'kb-select', note: '文件表 + 批量条' },
  { page: 'kb', width: 520, interact: 'kb-files', note: '文件表（无批量条；smoke-kb-cols 也跑这一档）' },
  { page: 'kb', width: 1300, interact: 'kb-select', note: '文件表 + 批量条（宽档）' },
  { page: 'kb', width: 520, interact: 'kb-empty-files', note: '空态卡' },
  { page: 'capabilities', width: 520, interact: '', note: '能力页' },
  { page: 'ingest', width: 520, interact: '', note: '入库面板' },
  { page: 'materials', width: 1300, interact: '', note: '资料面板' },
]

const outDir = join(repoRoot, 'var', 'tmp', 'ui-shots')
await mkdir(outDir, { recursive: true })

const rows = []
const failures = []
/** 缺浏览器是**全局**一件事（八组都会因此拿不到 JSON）⇒ 单独归一条，别刷屏八遍。 */
let sawNoBrowser = false
for (const c of MATRIX) {
  const args = [shotScript, '--page', c.page, '--width', String(c.width),
    '--out', join(outDir, `padpixels-${c.page}-${String(c.width)}${c.interact === '' ? '' : `-${c.interact}`}.png`)]
  if (c.interact !== '') args.push('--interact', c.interact)
  const r = spawnSync(process.execPath, args, { cwd: repoRoot, encoding: 'utf8', timeout: 240_000 })
  const label = `${c.page}|${c.interact === '' ? '(默认场景)' : c.interact}@${String(c.width)}`
  let j = null
  let parseErr = null
  try { j = JSON.parse(r.stdout ?? '') } catch (e) { parseErr = String(e) }
  if (j === null) {
    /* ⚠⚠ **5j-补-补（2026-09-20，复核 `verify-freeze-5jb` 打回的缺陷①）**：这条分支**必须把行对象
       补全**。原来只 push 了 `{label,note,exit,problems,checked}`，而下面的表格打印要读
       `r.required.length` ⇒ **无浏览器时（八组都拿不到 JSON）脚本会在打印表格中途崩掉**
       （`TypeError: Cannot read properties of undefined (reading 'length')`，栈顶本文件 :109），
       "❌ …判红"那段**永远打不出来**。缺浏览器=红这条**代价**是对的，但它的诊断路径坏在崩上。
       ⇒ 现在：字段补全 + 表格打印用 `?? '-'` 兜底 + 缺浏览器单独归一条失败行（见下面 `noBrowser`）。 */
    const stderrTail = (r.stderr ?? '').split('\n').filter(Boolean).slice(-3).join(' / ') || '(空)'
    const noBrowser = /找不到无头浏览器|no such file|--browser|\$KS_BROWSER/i.test(`${r.stderr ?? ''}${r.stdout ?? ''}`)
    rows.push({
      label, note: c.note, exit: r.status, checked: false,
      comboKey: null, tier: null, expect: null, pageW: null, required: null, missingSubjects: null,
      allSubjects: null, declaredCombos: null,
      problems: [`量不出 JSON（${String(parseErr)}）`],
    })
    failures.push(`${label}：ui-render-shot 没吐出 JSON（exit=${String(r.status)}）⇒ 这一组**没判**`
      + `（stderr 尾部：${stderrTail}）`)
    if (noBrowser) sawNoBrowser = true
    continue
  }
  const pad = j.ksPadCheck ?? {}
  const problems = []
  if (r.status !== 0) problems.push(`ui-render-shot exit=${String(r.status)}`)
  if (pad.skipReason !== null && pad.skipReason !== undefined) problems.push(`skipReason 非空（这一跑不判）：${String(pad.skipReason)}`)
  if (pad.checked !== true) problems.push('ksPadCheck.checked !== true')
  if (pad.coverageDeclared !== true) {
    problems.push(`这一组没在 PAD_REQUIRED 里声明期望元素（comboKey=${String(pad.comboKey)}）`
      + ' ⇒ 存在性没判（复核 E① 的假绿通道）')
  }
  for (const p of pad.problems ?? []) problems.push(p)
  rows.push({
    label, note: c.note, exit: r.status, checked: pad.checked === true,
    comboKey: pad.comboKey ?? null,
    tier: pad.tier ?? null, expect: pad.expect ?? null, pageW: pad.pageW ?? null,
    required: pad.required ?? null, missingSubjects: pad.missingSubjects ?? null,
    allSubjects: pad.allSubjects ?? null, declaredCombos: pad.declaredCombos ?? null, problems,
  })
  for (const p of problems) failures.push(`${label}：${p}`)
}

console.log('页面留边巡查（每组都跑一遍真 Chrome 的 ui-render-shot，判 ksPadCheck）：')
console.log('  组合                                        档位   期望  页面根宽  声明元素  判定')
for (const r of rows) {
  const verdict = r.checked && r.problems.length === 0 ? 'PASS' : 'FAIL'
  console.log(`  ${String(r.label).padEnd(42)} ${String(r.tier ?? '-').padEnd(6)} `
    + `${String(r.expect ?? '-').padEnd(5)} ${String(r.pageW ?? '-').padEnd(9)} `
    + `${String(r.required == null ? '-' : r.required.length).padEnd(9)} ${verdict}`)
  for (const p of r.problems) console.log(`         └─ ${p}`)
}
const tiers = new Set(rows.filter((r) => r.problems.length === 0).map((r) => r.tier))
console.log(`  判过的档位：${[...tiers].join(' / ') || '(一组都没判过)'}`)
console.log('')

/* 覆盖面的**独立**四条（别只信上面逐组的结果）：
   ① 窄/宽两档都必须至少有一组通过 —— 只跑窄档会让"宽档 24 从没被验过"变成静默缺口；
   ② 规范点名的适用面必须**每一类**都至少出现在**真跑过**那些组的 required 里；
   ③ ⚠⚠ **`PAD_REQUIRED` 声明的组合必须真被本巡查跑过**（5j-补-补-补，复核 `verify-freeze-5jbb` 的反例）：
      复核造过一个反例 —— 往 规范适用面 + `PAD_SUBJECTS_ALL` + **一个谁都不跑的新键**
      `PAD_REQUIRED['kb|kb-detail']` 里各塞一个 `.ks-fake` ⇒ 本巡查 **exit 0、全组 PASS**，
      还照样打印"10 类适用面每一类都至少有一组在判"。根因：下面 ② 的并集是**"声明"的并集**，
      不是**"真跑过的组合"的并集** ⇒ "声明了但没人跑"= 零保护。
      ④ 本脚本的 `SPEC_SUBJECTS`（第四份副本）必须与 `ui-render-shot.mjs` 的 `PAD_SUBJECTS_ALL` **逐字一致**。
   ⚠⚠ **5j-补×4（2026-09-20，复核 `verify-freeze-5jbbb` 打回 G/C）：声明集合改成"读活对象"，不再正则读源码。**
      复核实测：上一版用正则从 `ui-render-shot.mjs` 源码抠键 ⇒ ① 键写成**双引号**就漏读，"声明了但没人跑"
      的洞原样复现（exit 0、零诊断）；② 冒号换行 ⇒ 静默少读一个键；③ 表里写一句含 `'x':` 的**合法注释**
      ⇒ 假红。⇒ 现在 `ui-render-shot` 自己把 `allSubjects` / `declaredCombos`（`Object.keys(PAD_REQUIRED)`）
      放进 `ksPadCheck` 报出来，本脚本直接从**实测 JSON** 读 —— 引号风格、换行、注释都影响不了它。
      下面的判据也从"解析是否为 0"升级成**双向集合相等**（声明 ⊆ 真跑过、真跑过 ⊆ 声明），
      部分漏读也会被抓到（漏读会让 `真跑过 ⊆ 声明` 那一侧红）。 */
const SPEC_SUBJECTS = ['.ks-kb', '.ks-ing', '.ks-mat', '.ks-kbband', '.ks-list', '.ks-batch',
  '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-empty-card']
/** 从**成功的实测 JSON** 里取声明集合（任一组报到即可 —— 它们来自同一个 `ui-render-shot` 进程）。 */
const declaredSubjects = rows.map((r) => r.allSubjects).find((v) => Array.isArray(v)) ?? null
const declaredCombos = rows.map((r) => r.declaredCombos).find((v) => Array.isArray(v)) ?? null
const runKeys = new Set(rows.map((r) => r.comboKey).filter((k) => typeof k === 'string' && k !== ''))
if (declaredSubjects === null) {
  failures.push('这一跑**没有一组**从 `ui-render-shot` 拿到声明集合（`allSubjects`）—— 读不到就不算验过')
} else {
  const onlyHere = SPEC_SUBJECTS.filter((s) => !declaredSubjects.includes(s))
  const onlyThere = declaredSubjects.filter((s) => !SPEC_SUBJECTS.includes(s))
  if (onlyHere.length > 0 || onlyThere.length > 0) {
    failures.push('本脚本的 `SPEC_SUBJECTS` 与 `ui-render-shot.mjs` 的 `PAD_SUBJECTS_ALL` 不一致：'
      + `只在巡查里=[${onlyHere.join(' ')}]、只在脚本里=[${onlyThere.join(' ')}]（两边必须逐字一致）`)
  }
}
if (declaredCombos === null) {
  failures.push('这一跑**没有一组**报出 `PAD_REQUIRED` 的键（`declaredCombos`）—— 读不到就不算验过')
} else {
  const neverRun = declaredCombos.filter((k) => !runKeys.has(k))
  if (neverRun.length > 0) {
    failures.push(`**PAD_REQUIRED 声明了这些组合、本巡查却一次都不跑**：[${neverRun.join(' ')}]`
      + ' ⇒ 那些组等于**没人判**（"声明了但没人跑"=零保护，复核 `verify-freeze-5jbb` 的反例就是这条路）。'
      + '要么把它们加进 MATRIX，要么把声明删掉。')
  }
  const notDeclared = [...runKeys].filter((k) => !declaredCombos.includes(k))
  if (notDeclared.length > 0) {
    /* 这一侧兜"自报的声明集合比真跑过的还少"（例如自报被截断/漏项）—— 双向相等才算对得上。 */
    failures.push(`本巡查**真跑过**的组合里这些**不在自报的 PAD_REQUIRED 键**中：[${notDeclared.join(' ')}]`
      + ' ⇒ 自报的声明集合不可信（漏项/被截断），这一条棘轮不算验过')
  }
}
const coveredSubjects = new Set(rows.flatMap((r) => r.required ?? []))
const uncovered = SPEC_SUBJECTS.filter((s) => !coveredSubjects.has(s))
if (uncovered.length > 0) {
  failures.push(`规范点名的适用面这些类**没有任何一组在判**：[${uncovered.join(' ')}] ⇒ 给它们各加一组组合`)
}
if (!tiers.has('narrow')) failures.push('**窄档一组都没判过**（留边 16 这一档没有证据）')
if (!tiers.has('wide')) failures.push('**宽档一组都没判过**（留边 24 这一档没有证据）')
if (sawNoBrowser) {
  failures.push('**这一跑起不来无头浏览器**（八组都没拿到 JSON）—— 门禁链从 5j-补 起需要本机有'
    + ' Chromium/Edge（`--browser` 或 `$KS_BROWSER` 可指路径）。**缺浏览器就是红，不是跳过**：'
    + '把这两套脚本拿掉、或改成"没浏览器就放行"，等于把复核打回（`verify-freeze-5j` E②）的假绿通道开回来。')
}

if (failures.length > 0) {
  console.error('❌ 「页面留边」像素断言判红（业主 2026-09-20：「窗口四周要留点边啊」）：')
  for (const f of failures) console.error(`   - ${f}`)
  console.error('   ⇒ 规范见 docs/UI-BASELINE.md 第二节；实现见 plugin/client/ksGuideStyles.ts 的')
  console.error('      `--ks-page-pad-x-narrow/wide` + `.ks-page` 容器 + `@container (min-width:660px)`。')
  console.error('   ⇒ 期望元素表（这一跑该量到哪些）见 ui-render-shot.mjs 的 PAD_REQUIRED；')
  console.error('      "元素被改名/删掉"会以"根本没量到"的形态在这里红 —— 那是设计，不是误报。')
  process.exit(1)
}
console.log(`✅ 页面留边巡查通过：${MATRIX.length} 组（窄档与宽档都有），`
  + `规范点名的 ${SPEC_SUBJECTS.length} 类适用面每一类都至少有一组在判。`)
