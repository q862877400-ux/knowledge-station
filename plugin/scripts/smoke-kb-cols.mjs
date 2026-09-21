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
 * 切的（宽档多两列），**单跑一档证明不了另一档**。
 *
 * ## ⚠ 2026-09-21（KB-FOLDER-PLAN 第 3 步）本脚本的第二个主体换了
 * 原来它同时要求 `cardsCheck`（**卡片带**里逐张卡等宽等高 —— 业主点名的"卡片尺寸统一"）。
 * 卡片带已被业主删掉（"原来的大卡片去掉"）⇒ 换成本步的**新几何** `levelCheck`：
 *   ① 左列目录树与右栏**并排**（`.ks-kb-tree` 右缘 ≤ `.ks-main` 左缘）；
 *   ② 同一级里**目录行与文件行**的行高逐字相同（"目录层与文件列表同构"的可量形态）。
 * 纪律**一字未改**：三档每一档都必须 `levelCheck.checked === true` 且 `skipReason === null`
 * （"没判到"照样算失败），`problems` 非空即红。
 *
 * ## 边界（诚实）
 * - ⚠ **2026-09-21（第 4 步）**：「待分类」那一层的列几何与**状态列可见性**（业主"每篇状态
 *   如实显示"）**不在本脚本判** —— 它的取证场景是 `--interact kb-inbox` / `kb-inbox-picked`，
 *   归 `smoke-kb-pad-pixels.mjs` 的矩阵（那里有窄/宽两档 + 一条覆盖面判据）。本脚本三档跑的
 *   仍是**文件层**（`--interact kb-files`）：两层的列模板不同（待分类层 4/5 轨、文件层 3/5 轨），
 *   混在一处量只会得到"表头 != 行"的假红。
 * - 三档宽度按"**容器宽**"选的是**视口宽**：`ui-render-shot.mjs` 的 `#ks-shell` 是定宽
 *   （`--width`），`.ks-main` 的宽度由它推出来 ⇒ 520 / 900 落在窄档、1300 落在宽档。
 * - 本脚本**不进 `smoke-all` 的名单**（有意）：它要 spawn 无头浏览器，而门禁链
 *   （`npm run smoke`）目前**零浏览器依赖** —— 把浏览器塞进门禁链会让"提取树里没有 Chrome"
 *   变成门禁红。⇒ 门禁链的列对齐锚点在 jsdom 那一条（能抓住 M4 这类"两套声明"）；
 *   本脚本是**三档的补充证据 + 一条可复跑的命令**。这条取舍登记在
 *   docs/UI-BASELINE.md 5g（"最该让复核盯的点"与"没做/做不到"两节）。
 *   ⚠⚠ **就地更正（5j-补，2026-09-20；上面那几行原文保留）**：复核 `verify-freeze-5j` 打回 E②
 *   把这条取舍判成**假绿通道** —— "像素断言不在门禁链里"等于它只在我手工跑时才存在。
 *   现在本脚本**已进 `smoke-all.mjs` 名单**（与新增的 `smoke-kb-pad-pixels.mjs` 一起），
 *   于是上面那句"门禁链目前零浏览器依赖"**从 5j-补 起不再成立**：链上现在有两套要真浏览器的脚本，
 *   **没浏览器就是红，不是跳过**（理由见 `smoke-all.mjs` 里那段注释）。本脚本的断言一字未动。
 *   ⚠ 它仍**不是**"批量条折行"的锚点：它固定用 `--interact kb-files`（那场景**没有** `.ks-batch`），
 *   所以复核的 M3（折行）它抓不到 —— 那一条现在由 `smoke-kb-pad-pixels.mjs` 的 `kb-select` 组合判。
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
  // ⚠ **必须带 `--interact kb-files`。**
  //   第 3 步之后 kb 页的**默认态是"最外层"**（只有目录行、没有文件行）⇒ 不先走进去就**没有**
  //   `.ks-list .ks-lhead` / 文件行，`colsCheck` 会走"这一跑没有数据行"的 skip 分支 ⇒
  //   本脚本按**失败**记（"没跑"不能算通过）。
  //   ⚠ 这**不是**放宽断言：`colsCheck.checked === true` 的要求一字未动（下面 still 判它），
  //     只是把"走到文件层"这一步补进调用里 —— 断言判的仍是表头与第一行的列模板逐字相同。
  //   ⚠ `levelCheck` 的两条判据在这一跑**只判得到一条**：文件层有 `.ks-kb-tree` + `.ks-main`
  //     （判"并排"），而"两类行行高相同"需要目录行与文件行同时在 —— `kb-files` 停在
  //     「标准 / P16 工程防火」（这一级**没有**下级目录）⇒ `levelCheck.rowHeightJudged === false`。
  //     ⇒ **没有对象**不算失败（那一半的取证场景是 `--interact kb-level`，归
  //     `smoke-kb-pad-pixels.mjs` 的矩阵；它有一条覆盖面判据要求"至少一跑真的判过行高"）。 */
  const r = spawnSync(process.execPath, [shotScript, '--page', 'kb', '--width', String(width), '--interact', 'kb-files', '--out', outPng], {
    cwd: repoRoot, encoding: 'utf8', timeout: 180_000,
  })
  let payload = null
  try { payload = JSON.parse(r.stdout) } catch { payload = null }
  const cc = payload?.colsCheck ?? null
  const lc = payload?.levelCheck ?? null
  const sc = payload?.stageColCheck ?? null
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
    levelChecked: lc?.checked ?? false,
    levelSkipReason: lc?.skipReason ?? null,
    levelProblems: lc?.problems ?? [],
    rowHeightJudged: lc?.rowHeightJudged === true,
    treeRight: lc?.treeRight ?? null,
    mainLeft: lc?.mainLeft ?? null,
    stageChecked: sc?.checked ?? false,
    stageSkipReason: sc?.skipReason ?? null,
    stageProblems: sc?.problems ?? [],
    stageHead: sc?.head ?? null,
    stageDisplay: sc?.stageDisplay ?? null,
    dateDisplay: sc?.dateDisplay ?? null,
    stageMainWidth: sc?.mainWidth ?? null,
    stageMin: sc?.frozenMin ?? null,
  }
  rows.push(row)
  if (r.status !== 0) {
    failures.push(`width=${width}：ui-render-shot exit=${String(r.status)} —— `
      + ([...row.problems, ...row.levelProblems, ...row.stageProblems].length > 0
        ? [...row.problems, ...row.levelProblems, ...row.stageProblems].join('；')
        : (r.stderr ?? '').trim().split('\n').slice(-3).join(' / ')))
  } else {
    if (!row.checked) {
      failures.push(`width=${width}：列对齐**没判到**（${row.skipReason ?? 'colsCheck 缺失'}）—— "没跑"不能算通过`)
    }
    /* ⚠ 2026-09-21（第 3 步）：这一档原来要求的是 `cardsCheck`（卡片带里逐张卡等宽等高）。
       卡片带已被业主删掉 ⇒ 换成 **`levelCheck`**（左列与右栏并排 + 目录/文件两层行高逐字相同）。
       纪律一字未改：**"判到且通过"**，`skipReason` 非空 / `checked !== true` 都算失败。 */
    if (!row.levelChecked) {
      failures.push(`width=${width}：知识库几何（左列并排 + 两层行高一致）**没判到**`
        + `（${row.levelSkipReason ?? 'levelCheck 缺失'}）—— "没跑"不能算通过`)
    }
    for (const p of row.levelProblems) failures.push(`width=${width}：${p}`)
    /* ⚠⚠ 2026-09-21（第 3 步，**本批自己先证伪出来的洞**）：这一档跑的是 `--interact kb-files`
       ⇒ **一定有文件行** ⇒ `stageColCheck` 必须**判到且通过**。它判的是业主那句
       「所有文件都要显示处理状态」在两档宽度下到底兑没兑现（窄档故意藏、宽档必须看得见）。 */
    if (!row.stageChecked) {
      failures.push(`width=${width}：处理状态列可见性**没判到或判红**`
        + `（${row.stageSkipReason ?? 'stageColCheck 缺失'}${
          row.stageProblems.length > 0 ? '；' + row.stageProblems.join('；') : ''}）—— "没跑"不能算通过`)
    }
    for (const p of row.stageProblems) failures.push(`width=${width}：${p}`)
  }
}

console.log('列对齐三档巡查（每档都跑一遍真 Chrome 的 ui-render-shot）：')
console.log('  宽度   判定    表头 grid-template-columns                 行 grid-template-columns                 gap(表头/行)')
for (const r of rows) {
  const verdict = r.exit !== 0 ? `FAIL(exit ${String(r.exit)})` : (r.checked && r.levelChecked ? 'PASS' : 'SKIP')
  console.log(`  ${String(r.width).padEnd(6)} ${verdict.padEnd(7)} ${String(r.header).padEnd(42)} ${String(r.rowTpl).padEnd(40)} ${String(r.gapHeader)}/${String(r.gapRow)}`)
  for (const p of r.problems) console.log(`         └─ ${p}`)
}
const wide = rows.filter((r) => r.checked).map((r) => `${r.width}:${String(r.header).split(' ').length} 列`)
console.log(`  档位（按表头列数）：${wide.join(' / ') || '(没有判到的档)'}`)
console.log('  知识库几何（2026-09-21 起取代"卡片尺寸统一"；左列右缘 ≤ 右栏左缘）：')
for (const r of rows) {
  console.log(`  ${String(r.width).padEnd(6)} 左列右缘 ${String(r.treeRight)}px ≤ 右栏左缘 ${String(r.mainLeft)}px`
    + `（并排判过=${String(r.levelChecked)}；两层行高这一跑判到=${String(r.rowHeightJudged)}`
    + `${r.rowHeightJudged ? '' : ' —— 这一级没有下级目录，行高那一半归 kb-level 场景'}）`)
  for (const p of r.levelProblems) console.log(`         └─ ${p}`)
}
console.log('  「处理状态」列可见性（业主：所有文件都要显示处理状态；窄档故意藏 / 宽档必须看得见）：')
for (const r of rows) {
  const wide = Number(r.stageMainWidth) >= Number(r.stageMin)
  console.log(`  ${String(r.width).padEnd(6)} 主栏 ${String(r.stageMainWidth)}px `
    + `${wide ? '≥' : '<'} 阈值 ${String(r.stageMin)}px（${wide ? '宽档' : '窄档'}）`
    + ` ⇒ 期望「${wide ? '看得见' : '藏起来'}」，实测「${r.stageHead}」列 display=${JSON.stringify(r.stageDisplay)}`
    + ` / 生效日期 display=${JSON.stringify(r.dateDisplay)}（判过=${String(r.stageChecked)}）`)
  for (const p of r.stageProblems) console.log(`         └─ ${p}`)
}
console.log('')

if (failures.length > 0) {
  console.error('❌ 列对齐/知识库几何巡查判红（P2 头条"列对齐" + 第 3 步"左列目录与右栏并排"）：')
  for (const f of failures) console.error(`   - ${f}`)
  console.error('   ⇒ 列对齐：表头（.ks-lhead）与数据行（.ks-item）必须共用同一条 --ks-cols 模板，')
  console.error('      见 plugin/client/ksGuideStyles.ts 的 `.ks-lhead,.ks-item{grid-template-columns:var(--ks-cols)}`。')
  console.error('   ⇒ 几何：左列宽/主栏最小宽见 `.ks-kb-tree{flex:0 0 168px}` 与 `.ks-main{min-width:260px}`；')
  console.error('      两层行高都吃 `.ks-item{min-height:var(--ks-row-h-list)}`。')
  process.exit(1)
}
console.log(`✅ 列对齐 + 知识库几何巡查通过：${widths.join(' / ')} 三档的表头与第一行逐字相同（gap 也相同）、`
  + `左列目录与右栏**并排**（${widths.join('/')} 三档都判到）。`
  + `⚠ 这一跑停在文件层（那一级没有下级目录）⇒ "目录行与文件行行高一致"这一条**不在本脚本判**，`
  + `取证场景是 \`--interact kb-level\`，归 smoke-kb-pad-pixels.mjs 的矩阵（它有一条覆盖面判据）。`)
