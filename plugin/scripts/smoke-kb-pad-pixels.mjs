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
    rows.push({ label, note: c.note, exit: r.status, problems: [`量不出 JSON（${String(parseErr)}）`], checked: false })
    failures.push(`${label}：ui-render-shot 没吐出 JSON（exit=${String(r.status)}）⇒ 这一组**没判**`
      + `（stderr 尾部：${(r.stderr ?? '').split('\n').filter(Boolean).slice(-3).join(' / ') || '(空)'}）`)
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
    tier: pad.tier ?? null, expect: pad.expect ?? null, pageW: pad.pageW ?? null,
    required: pad.required ?? null, missingSubjects: pad.missingSubjects ?? null, problems,
  })
  for (const p of problems) failures.push(`${label}：${p}`)
}

console.log('页面留边巡查（每组都跑一遍真 Chrome 的 ui-render-shot，判 ksPadCheck）：')
console.log('  组合                                        档位   期望  页面根宽  声明元素  判定')
for (const r of rows) {
  const verdict = r.checked && r.problems.length === 0 ? 'PASS' : 'FAIL'
  console.log(`  ${String(r.label).padEnd(42)} ${String(r.tier ?? '-').padEnd(6)} `
    + `${String(r.expect ?? '-').padEnd(5)} ${String(r.pageW ?? '-').padEnd(9)} `
    + `${String(r.required === null ? '-' : r.required.length).padEnd(9)} ${verdict}`)
  for (const p of r.problems) console.log(`         └─ ${p}`)
}
const tiers = new Set(rows.filter((r) => r.problems.length === 0).map((r) => r.tier))
console.log(`  判过的档位：${[...tiers].join(' / ') || '(一组都没判过)'}`)
console.log('')

/* 覆盖面的**独立**两条（别只信上面逐组的结果）：
   ① 窄/宽两档都必须至少有一组通过 —— 只跑窄档会让"宽档 24 从没被验过"变成静默缺口；
   ② 规范点名的适用面必须**每一类**都至少出现在一组的 required 里（真正"有人在判"）。 */
const SPEC_SUBJECTS = ['.ks-kb', '.ks-ing', '.ks-mat', '.ks-kbband', '.ks-list', '.ks-batch',
  '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-empty-card']
const coveredSubjects = new Set(rows.flatMap((r) => r.required ?? []))
const uncovered = SPEC_SUBJECTS.filter((s) => !coveredSubjects.has(s))
if (uncovered.length > 0) {
  failures.push(`规范点名的适用面这些类**没有任何一组在判**：[${uncovered.join(' ')}] ⇒ 给它们各加一组组合`)
}
if (!tiers.has('narrow')) failures.push('**窄档一组都没判过**（留边 16 这一档没有证据）')
if (!tiers.has('wide')) failures.push('**宽档一组都没判过**（留边 24 这一档没有证据）')

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
