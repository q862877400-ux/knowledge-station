/**
 * ks-dsh-plugin — scripts/smoke-draft-ui.mjs
 *
 * **结论草稿**（§10.97）在面板这一层的三条纪律，逐条用**行为**验（不是只找字符串）：
 *
 * 1. **绝不自动填**：`onDraftConclusion`（响应回来那一段）里**不许出现** `setConclusionMd`
 *    —— 否则"用户点了起草"就等于"结论被系统改掉"，那是把"用户批准"这个动作**偷走**。
 *    判据是**源码切片**（切出那个 useCallback 的 body 再看），不是"全文里有没有这个词"。
 * 2. **能填的唯一条件**：`canApplyDraft(draft)` —— 导出成纯函数，这里**真的调用**它，
 *    逐档断言：没起草过 / 引擎一次模型都没调 / 空草稿 ⇒ **false**；有草稿 ⇒ **true**。
 * 3. **未批准要说出来**：面板里必须有「未批准草稿」「用这段填进结论框」「起草结论（草稿）」
 *    三处文案，且 `llm_called === false` 有**单独分支**（"没起草"不是"失败"）。
 *
 * ⚠ 产物↔源码一致由 `smoke-client-entry.mjs` 管（它扫 `plugin/client.js`）；这里管**行为**。
 * 用法：node scripts/smoke-draft-ui.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const panelPath = join(pluginRoot, 'client', 'KsMaterialsPanel.tsx')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

// ⚠ 临时产物必须落在 plugin/ 里（react 是 external ⇒ Node 要沿自身路径找根 node_modules）
const outfile = join(pluginRoot, '.draft-ui.smoke.mjs')
try {
  await build({
    entryPoints: [panelPath],
    bundle: true, platform: 'node', format: 'esm', outfile,
    absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
    external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
    logLevel: 'warning',
  })
} catch (err) {
  console.error('面板打包失败：' + (err && err.message ? err.message : String(err)))
  process.exit(1)
}
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

/* ------------------------------------------------ 1. canApplyDraft（真的调用它） */
{
  const f = mod.canApplyDraft
  check('面板导出了 canApplyDraft（填不填的唯一判据）', typeof f === 'function')
  if (typeof f === 'function') {
    check('还没起草过（null）⇒ 不许填', f(null) === false, String(f(null)))
    check('引擎一次模型都没调（llm_called=false）⇒ 不许填', f({ llm_called: false, draft_md: 'x' }) === false)
    check('草稿是空串 ⇒ 不许填', f({ draft_md: '' }) === false)
    check('草稿只有空白 ⇒ 不许填', f({ draft_md: '   \n ' }) === false)
    check('有真草稿 ⇒ 允许填', f({ draft_md: '每晚不超过五百元 [[m:0]]' }) === true)
    check('缺 llm_called 字段时有草稿也算允许（保守方向不是"拒填一切"）',
      f({ draft_md: 'x' }) === true)
  }
}

/* ------------------------------------------------ 2. 「绝不自动填」的源码切片判据 */
{
  const src = await readFile(panelPath, 'utf8')
  const start = src.indexOf('const onDraftConclusion = useCallback(')
  check('找得到 onDraftConclusion 的定义（切片判据的前提）', start >= 0)
  if (start >= 0) {
    const end = src.indexOf('}, [projectId, researchQuery, run])', start)
    check('找得到 onDraftConclusion 的结尾（切片没有跑飞）', end > start)
    const body = src.slice(start, end)
    check('⚠ 起草响应那一段里**不许**出现 setConclusionMd（否则等于自动填）',
      !body.includes('setConclusionMd'), body.slice(0, 120))
    check('起草响应里确实要求了 query（起草必须先有研究问题）',
      body.includes('researchQuery') && body.includes('研究问题'))
    check('起草响应里对 llm_called === false 有**单独**分支（"没起草"≠失败）',
      body.includes('llm_called === false'))
  }
  const hits = src.split('setConclusionMd(').length - 1
  check('`setConclusionMd(` 恰好两处：结论框自己的 onChange + 「用这段」按钮',
    hits === 2, `实测 ${hits} 处`)
  check('「用这段填进结论框」按钮的 onClick 是**唯一**写草稿的地方',
    src.includes('onClick={() => setConclusionMd(draft.draft_md ?? \'\')}'))
}

/* ------------------------------------------------ 3. 三处文案（未批准要说出来） */
{
  const src = await readFile(panelPath, 'utf8')
  for (const text of ['起草结论（草稿）', '未批准草稿', '用这段填进结论框']) {
    check(`面板里有文案「${text}」`, src.includes(text))
  }
  check('「未批准草稿」那一段明说"不得作为依据"', src.includes('不得作为依据'))
  check('草稿块用 role="status"（可被无障碍读到）', src.includes('role="status"'))
}

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-draft-ui: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\n== draft-ui smoke PASS (${results.length}/${results.length}) ==`)
