/**
 * ks-dsh-plugin — scripts/smoke-draft-ui.mjs
 *
 * **结论草稿**（§10.97 / §10.99）在面板这一层的判据，逐条**真的调用**（不是找字符串）。
 *
 * ## 为什么重写成这样（复核 b26 的 F1，HIGH）
 * 第一版用两条**字符串级**判据守"绝不自动填"：① `onDraftConclusion` 的源码切片里找
 * `setConclusionMd`；② 全文件数 `setConclusionMd(` 出现几次。b26 **构造出了绕过**：
 * 把 setter 赋给一个**声明在切片之外**的别名、再在起草响应里调用它 ⇒ 本冒烟 **19/19 全绿**，
 * 而"自动填"**真的发生了**。⇒ 那对判据钉的是**写法**，不是**性质**。
 *
 * 现在的判据是**函数语义**（面板把四个动作抽成了导出的纯函数，见 `DraftFlow`）：
 *   · `draftArrived(prev, out)`：**响应到达** ⇒ `conclusionMd` **必须原样**（"绝不自动填"）；
 *   · `requestApplyDraft`：空框 ⇒ 填；**非空 ⇒ 只进入待确认、不覆盖**（复核 b26 的 F3）；
 *   · `confirmApplyDraft`：**唯一**写入路径；
 *   · `cancelApplyDraft` / `userTypedConclusion`：各归各位。
 * 这些断言**没法用别名绕过**——它们问的是"这个动作之后结论框是什么"，不是"源码里有没有某个词"。
 *
 * ⚠ **仍然诚实的边界（写在代码里，不许含糊）**：本冒烟**挡不住**"面板里用别名或 `useEffect`
 * 偷偷写状态"——那需要 jsdom 或真机 E2E（本仓**没装 jsdom**，属需决策项）。
 * 所以下面仍保留**一条**源码级检查，但它**只是写法约定**（防止"多出一个结论框写入点"），
 * check 名字里明写"写法级"，**不再声称它守住了 P1**。
 *
 * 用法：node scripts/smoke-draft-ui.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

import { ksClientPrimitivesAlias } from './lib/ks-primitives-stub.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const panelPath = join(pluginRoot, 'client', 'KsMaterialsPanel.tsx')

// 宿主 `@deepseek-ai/dsh-client-ui-primitives` 的桩：**从源码派生**（lib/ks-primitives-stub.mjs，
// 单一所有者）。KsMaterialsPanel **今天**还没 import 宿主原语 ⇒ alias 目前惰性；接上它只为
// "下次谁在这个面板里用宿主组件，不用回来补 alias/补桩"（同一根因已踩三次）。
const primStubDir = await mkdtemp(join(tmpdir(), 'ks-draft-prim-'))
const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, primStubDir)

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
    alias: { ...primitivesAlias },
    logLevel: 'warning',
  })
} catch (err) {
  console.error('面板打包失败：' + (err && err.message ? err.message : String(err)))
  process.exit(1)
}
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

const DRAFT = { status: 'unapproved_draft', draft_md: '每晚不超过五百元 [[m:0]]', llm_called: true }
const EMPTY = { status: 'unapproved_draft', draft_md: '', llm_called: true }
const NO_LLM = { status: 'unapproved_draft', draft_md: '', llm_called: false }

/* ------------------------------ 1. canApplyDraft（能填的唯一条件） */
{
  const f = mod.canApplyDraft
  check('面板导出了 canApplyDraft（能填的唯一判据）', typeof f === 'function')
  if (typeof f === 'function') {
    check('还没起草过（null）⇒ 不许填', f(null) === false)
    check('引擎一次模型都没调（llm_called=false）⇒ 不许填', f(NO_LLM) === false)
    check('草稿是空串 ⇒ 不许填', f(EMPTY) === false)
    check('草稿只有空白 ⇒ 不许填', f({ draft_md: '   \n ' }) === false)
    check('有真草稿 ⇒ 允许填', f(DRAFT) === true)
    check('缺 llm_called 字段但有草稿 ⇒ 允许填（保守方向不是"拒填一切"）', f({ draft_md: 'x' }) === true)
  }
}

/* ------------------------------ 2. **绝不自动填**：响应到达之后结论框必须原样（行为级） */
{
  const { draftArrived, emptyDraftFlow } = mod
  check('面板导出了 draftArrived / emptyDraftFlow（状态机的入口）',
    typeof draftArrived === 'function' && typeof emptyDraftFlow === 'object')
  if (typeof draftArrived === 'function') {
    const USER = '这是我自己写的结论，不能被系统改掉'
    const before = { draft: null, conclusionMd: USER, pendingOverwrite: false }
    const after = draftArrived(before, DRAFT)
    check('⚠ **响应到达**：结论框**原样**（这就是"绝不自动填"的行为判据）',
      after.conclusionMd === USER, JSON.stringify({ before: USER, after: after.conclusionMd }))
    check('响应到达：草稿被记下（否则界面没得显示）', after.draft === DRAFT)
    check('响应到达：清掉"待确认覆盖"（上一次没确认完的状态不许留）',
      draftArrived({ ...before, pendingOverwrite: true }, DRAFT).pendingOverwrite === false)
    check('空结论框时响应到达也**不**自动填（同一份语义）',
      draftArrived(emptyDraftFlow, DRAFT).conclusionMd === '', '空框也不是"自动填的理由"')
  }
}

/* ------------------------------ 3. 「用这段」：空框直接填 / 非空**只进待确认**（F3） */
{
  const { requestApplyDraft, confirmApplyDraft, cancelApplyDraft } = mod
  const empty = { draft: DRAFT, conclusionMd: '', pendingOverwrite: false }
  const filled = { draft: DRAFT, conclusionMd: '用户自己写的字', pendingOverwrite: false }

  const a = requestApplyDraft(empty)
  check('空结论框 ⇒ 点一下直接填进去', a.conclusionMd === DRAFT.draft_md)
  check('空结论框 ⇒ 不进待确认', a.pendingOverwrite === false)

  const b = requestApplyDraft(filled)
  check('⚠ 结论框**非空** ⇒ 点一下**不覆盖**（复核 b26 的 F3：原先静默覆盖且不可撤销）',
    b.conclusionMd === '用户自己写的字', JSON.stringify(b))
  check('非空 ⇒ 进入"待确认覆盖"状态', b.pendingOverwrite === true)

  const c = confirmApplyDraft(b)
  check('用户**确认**之后才写（且这是唯一写入路径）', c.conclusionMd === DRAFT.draft_md)
  check('确认后退出待确认', c.pendingOverwrite === false)

  const d = cancelApplyDraft(b)
  check('用户**取消** ⇒ 他写的字一个都不丢', d.conclusionMd === '用户自己写的字')
  check('取消后退出待确认', d.pendingOverwrite === false)

  for (const [name, draft] of [['没起草过', null], ['引擎没调模型', NO_LLM], ['空草稿', EMPTY]]) {
    const s = { draft, conclusionMd: '', pendingOverwrite: false }
    check(`${name} ⇒ 点按钮什么都不发生`, requestApplyDraft(s) === s)
    check(`${name} ⇒ 确认覆盖也不发生`, confirmApplyDraft(s) === s)
  }
}

/* ------------------------------ 4. 用户打字那条路（与草稿无关） */
{
  const { userTypedConclusion, draftReducer } = mod
  const s = userTypedConclusion({ draft: DRAFT, conclusionMd: '', pendingOverwrite: true }, '手写的')
  check('用户打字 ⇒ 只改结论框', s.conclusionMd === '手写的')
  check('用户打字 ⇒ 不动草稿、清掉待确认', s.draft === DRAFT && s.pendingOverwrite === false)
  // 动作集（封闭）：`dispatch({type:'arrived'})` 这条**正确**动作也绝不自动填（与纯函数同步）
  if (typeof draftReducer === 'function') {
    const USER = '用户手写的字'
    const r = draftReducer({ draft: null, conclusionMd: USER, pendingOverwrite: false },
      { type: 'arrived', out: DRAFT })
    check('reducer：`arrived` 动作**不动结论框**（动作集里的语义与纯函数一致）',
      r.conclusionMd === USER && r.draft === DRAFT)
  } else {
    check('面板导出了 draftReducer（封闭动作集）', false)
  }
}

/* ------------------------------ 5. 文案（**这一层就是字符串级的，如实标注**） */
{
  const src = await readFile(panelPath, 'utf8')
  for (const text of ['起草结论（草稿）', '未批准草稿', '用这段填进结论框', '确认覆盖', '取消（保留我写的）']) {
    check(`面板里有文案「${text}」`, src.includes(text))
  }
  check('「未批准草稿」那一段明说"不得作为依据"', src.includes('不得作为依据'))
  check('草稿块用 role="status"（可被无障碍读到）', src.includes('role="status"'))
  // ⚠ 下面这几条是**写法级窄判据**（§10.99）：面板现在只能通过 `dispatch(动作)` 改这份状态，
  //   而**动作集是封闭的**（`DraftAction`）⇒ "写一个对象字面量"那条绕过被 `tsc` 堵死
  //   （复核 b26 的别名绕过**编译不过**）。剩下能绕过的是"在到达路径上伪造 `confirmApply`"，
  //   所以这里钉的是**动作名**——比"某个 setter 字符串在不在"窄得多，但仍是**写法级**：
  //   它**不**证明"用户真的点过那一下"（那要 jsdom / 真机 E2E）。
  const verifyCalls = src.split('setFlow(').length - 1
  check('写法级：没有直接的 `setFlow(` 调用（状态只能经 `dispatch(动作)` 改）',
    verifyCalls === 0, `实测 ${verifyCalls} 处`)
  check('写法级：结论框的字装在那个状态机里（`useReducer(draftReducer, emptyDraftFlow)`）',
    src.includes('useReducer(draftReducer, emptyDraftFlow)'))
  for (const action of ['arrived', 'requestApply', 'confirmApply', 'cancelApply', 'typed']) {
    check(`写法级：动作 \`${action}\` 在面板里被用到`, src.includes(`type: '${action}'`))
  }
  // ⚠ **到达路径只许出现 `arrived`**（窄判据）：伪造 `confirmApply`/`requestApply`/`typed`
  //   是最后一种绕过（写对象字面量已被 `tsc` 堵死）⇒ 这里把"哪个动作出现在哪个回调里"钉住。
  //   仍然只是**写法级**：它挡不住别名 `const d = dispatch; d({type:'confirmApply'})`——
  //   那条要 jsdom / E2E 才能验（已登记）。
  const s0 = src.indexOf('const onDraftConclusion = useCallback(')
  // ⚠ 结束锚点**不用**字面 deps 数组（复核 b26 的 F5：给这个回调加依赖就会断，虽然 fail-safe
  //   但会误导）——改成"下一个 handler 的开头"，与依赖数组内容无关。
  const s1 = src.indexOf('const onReview = useCallback(', s0)
  const arrival = s0 >= 0 && s1 > s0 ? src.slice(s0, s1) : ''
  check('写法级：切片取到了 onDraftConclusion（否则下面的判据无意义）', arrival !== '')
  check("写法级：到达路径用的是 `arrived` 动作", arrival.includes("type: 'arrived'"))
  for (const forbidden of ["type: 'confirmApply'", "type: 'requestApply'", "type: 'typed'",
    'conclusionMd']) {
    check(`写法级：到达路径里**不出现** ${forbidden}`,
      !arrival.includes(forbidden), forbidden)
  }
}

await rm(primStubDir, { recursive: true, force: true })

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-draft-ui: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\n== draft-ui smoke PASS (${results.length}/${results.length}) ==`)
