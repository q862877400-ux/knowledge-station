/**
 * ks-dsh-plugin — scripts/smoke-tool-concurrency.mjs
 *
 * 第 6 步 §3「`isConcurrencySafe`」的**离线**冒烟（施工单
 * [docs/research/STEP6-WORKORDER.md](../../docs/research/STEP6-WORKORDER.md) §3「怎么验」的 C1/C2/C3）。
 *
 * 为什么值得单测：官方只把**恰好 `true`** 当并行，其余（缺省/异常/非 true/false）**全部**
 * 当 exclusive —— 所以"漏声明"和"声明成恒假"**都不会报错**，只会静默退回全串行，
 * 是典型的不红而白做。反过来，给**写**工具声明 `true` 也不报错，只会让并发登记材料
 * 撞上限额判断（TOCTOU）。两种都只能靠断言钉住。
 *
 * 怎么做到的：用最小假 cordis ctx 调 `apply()`，把 6 个工具定义**原样捕获**下来
 * （与 `smoke-effect-tool.mjs` 同款桩）。数据目录指到临时目录，启动自检读到空状态即返回，
 * 全程**不 spawn 引擎、不碰用户数据**。
 *
 * ⚠ C4（真宿主 `executionMode({name:'ks_ping',arguments:{}})` 返回 `{kind:'parallel'}`）
 * **不在这里**：它要真 `ToolRuntime`，属第 6 条 e2e。本文件钉的是"声明写对了"，
 * **不是**"宿主真的会并行"——两者之间的差（桩里 true / 真机被参数校验降级）这里测不到。
 *
 * Run: node scripts/smoke-tool-concurrency.mjs   (exit 0 = all checks pass)
 */
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

process.env.KS_DATA_DIR = await mkdtemp(join(tmpdir(), 'ks-tool-conc-'))
process.env.KS_CHATMODE_DIR = await mkdtemp(join(tmpdir(), 'ks-tool-conc-mode-'))

const { apply } = await import(new URL('../src/index.js', import.meta.url).href)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ---------------------------------------------------- 假 cordis ctx（照 smoke-effect-tool） */
const tools = new Map()
const services = {
  tools: { register(tool) { tools.set(tool.name, tool) } },
  webServer: { register() { return () => {} } },
  systemPrompt: { section() { return () => {} } },
  agents: { get() { return undefined } },
  commands: { register() { return () => {} } },
  logger: { info() {}, warn() {}, error() {} },
}
const ctx = {
  ...services,
  get(name) { return services[name] },
  effect(fn) { return fn() },
}

// `idleTimeoutMs: 0`：不装 30min 空闲定时器（否则这个进程要靠 process.exit 才走）。
apply(ctx, { idleTimeoutMs: 0 })

/* ---------------------------------------------------- C0 六个工具都在 */
const EXPECTED = ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report', 'ks_materials', 'ks_collect']
const READ_ONLY = ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report', 'ks_materials']
const WRITE_TOOL = 'ks_collect'

check('C0 exactly the 6 model tools were registered',
  [...tools.keys()].sort().join(',') === [...EXPECTED].sort().join(','),
  `got ${[...tools.keys()].sort().join(',')}`)

/* ---------------------------------------------------- C1 只读工具声明可并行 */
for (const name of READ_ONLY) {
  const t = tools.get(name)
  const declared = t !== undefined && typeof t.isConcurrencySafe === 'function'
  let verdict
  try { verdict = declared ? t.isConcurrencySafe({}) : undefined } catch { verdict = 'threw' }
  check(`C1 ${name} declares concurrency safety (=== true)`,
    declared && verdict === true, `typeof=${typeof t?.isConcurrencySafe} value=${String(verdict)}`)
}

/* ---------------------------------------------------- C2 写工具保持 exclusive */
{
  const t = tools.get(WRITE_TOOL)
  check(`C2 ${WRITE_TOOL} stays exclusive (no classifier at all)`,
    t !== undefined && t.isConcurrencySafe === undefined,
    `typeof=${typeof t?.isConcurrencySafe}`)
  check(`C2 ${WRITE_TOOL} does NOT carry a fake ()=>false classifier`,
    t !== undefined && !Object.prototype.hasOwnProperty.call(t, 'isConcurrencySafe'))
}

/* ---------------------------------------------------- C3 classifier 对任何参数都不抛 */
{
  const JUNK = [{}, null, undefined, { x: 1 }, { include_attention: 'yes' }, [], 42, 'str',
    { __proto__: { polluted: true } }]
  for (const name of READ_ONLY) {
    const t = tools.get(name)
    let threw = null
    const verdicts = []
    for (const arg of JUNK) {
      try { verdicts.push(t.isConcurrencySafe(arg)) } catch (error) { threw = error }
    }
    check(`C3 ${name} classifier never throws and always opts in`,
      threw === null && verdicts.length === JUNK.length && verdicts.every((v) => v === true),
      threw === null ? `all ${verdicts.length} true` : `threw ${threw?.message}`)
  }
  // 官方读法：`concurrencySafe === true ? parallel : exclusive`。返回 thenable 会被静默降级成
  // exclusive ⇒ 断言"同步布尔"，别让一个 async classifier 悄悄把并行关掉。
  const asyncish = READ_ONLY.filter((name) => {
    const v = tools.get(name).isConcurrencySafe({})
    return typeof v !== 'boolean'
  })
  check('C3b classifiers are synchronous booleans (a Promise would silently mean exclusive)',
    asyncish.length === 0, asyncish.length === 0 ? 'all boolean' : `non-boolean: ${asyncish.join(',')}`)
}

/* ---------------------------------------------------- C4 未声明面：schemas 不外泄 */
{
  // 施工单 §3 风险 4：官方 `schemas()` 会把 `isConcurrencySafe` 从模型可见面剔除。
  // 我们无法在这层断言宿主行为，只能断言"我们没把它写进 description/parameters"
  // （写进去就是对模型承诺了一件调度器才有的事）。
  const leaked = EXPECTED.filter((name) => {
    const t = tools.get(name)
    const blob = `${t.description ?? ''}${JSON.stringify(t.parameters ?? {})}`
    return /concurren|parallel|并行/i.test(blob)
  })
  check('C4 concurrency is not promised to the model in description/parameters',
    leaked.length === 0, leaked.length === 0 ? 'clean' : `leaked in: ${leaked.join(',')}`)
}

/* ---------------------------------------------------- 汇总 */
const failed = results.filter((r) => !r.ok)
console.log(`\n== tool-concurrency smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} ` +
  `(${results.length - failed.length}/${results.length}) ==`)
if (failed.length > 0) console.log(`FAILED: ${failed.map((f) => f.name).join(' | ')}`)
process.exit(failed.length === 0 ? 0 : 1)
