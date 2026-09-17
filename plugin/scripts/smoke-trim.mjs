/**
 * ks-dsh-plugin — scripts/smoke-trim.mjs
 *
 * `ks_answer` 裁剪层回归（Phase B，2026-09-17）。
 *
 * ## 为什么要专门守这一层
 * 审计证实**同类失败已经发生过**：`unsupported_context`（D 线"资格声明"）在引擎里
 * 算出来了、也进了 SSE，**却在 `src/index.js` 的 `trimVerification` 白名单里被静默
 * 丢弃** ⇒ 算出来但没人看得见。失败模式是**静默**的，所以不能靠"记得加"。
 *
 * 本冒烟守两件事：
 *   1. **结构化裁剪不毁内容**：`unsupported_context[].reason` 是这条信息的全部价值
 *      （"属于哪部标准 / 是召回漏了还是模型越界 / 该补什么"）。走通用 `compact()`
 *      （JSON 化后截 160）会把中文原因切断在半句上——正好复现要修掉的那个毛病。
 *   2. **白名单不许漏字段**：直接从引擎源码（`ks_answer.py` 的 verification 字典）
 *      解析出**真实字段集**，逐键探测是否被转发。将来引擎新增字段而桥忘了转发，
 *      本冒烟立刻红——不依赖任何人记得。
 *
 * 为什么可以调真实现：这些函数已抽到零依赖的 `src/trim.js`（见该文件头）。
 * 本脚本**不复制算法**，因此不会与真实现漂移。
 *
 * 用法：node scripts/smoke-trim.mjs   （退出码 0 = 全通过）
 */

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  REASON_CAP,
  VERIFY_LIST_CAP,
  shortList,
  trimUnsupportedContext,
  trimVerification,
} from '../src/trim.js'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO = join(HERE, '..', '..')

/**
 * 读源码并**统一换行为 LF**。
 *
 * ⚠ 为什么必须归一（独立复核 2026-09-17 报的缺陷）：本仓库 `core.autocrlf=true`，
 * **全新 clone 出来是 CRLF**。而本脚本下面用 `}\n` 找字典结尾——CRLF 下匹配不到，
 * `indexOf` 返回 -1，代码会**静默**把"块"扩到文件末尾，键集随之失真；
 * 在 LF 工作树上却全绿。于是同一个提交在不同检出上给出不同结论。
 */
function readSource(rel) {
  return readFileSync(join(REPO, rel), 'utf8').replace(/\r\n/g, '\n')
}

/** 顶层键名：字母/下划线开头，允许数字与大小写（`([a-z_]+)` 会漏 `foo2`/`fooBar`）。 */
const KEY_RE_SRC = '([A-Za-z_][A-Za-z0-9_]*)'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------------------------------------------ *
 * 引擎侧真实字段集：从源码解析，而不是手抄（手抄会随引擎漂移）
 * ------------------------------------------------------------------ */

/** 统一换行为 LF。解析函数**自己**归一，不依赖调用方先读过 `readSource`。 */
const LF = (s) => String(s).replace(/\r\n/g, '\n')

/**
 * 从 `ks_answer.py` 源码文本里取 **verification 字典**的键（工具走的正是这条路径）。
 *
 * 做成"吃文本、返回键数组"的纯函数，是为了能在下面用 **CRLF 变体**自检——
 * 本仓库 `core.autocrlf=true`，全新 clone 是 CRLF，而这条解析一旦对换行敏感就会
 * **静默**给出错误键集（见 `readSource` 的注释）。
 */
function verificationKeysFrom(rawSrc) {
  const src = LF(rawSrc)
  const m = src.match(/return\s*\{\s*\n\s*"is_valid"[\s\S]*?\n\s*\}\n/)
  if (m === null) return []
  return [...m[0].matchAll(new RegExp(`^\\s*"${KEY_RE_SRC}":`, 'gm'))].map((x) => x[1])
}

/**
 * 取 `answer()` 顶层 `return {...}` 的键，**并回报块边界**。
 *
 * 为什么要把 `end` 一起报出来：`}\n` 找不到时 `indexOf` 返回 -1，旧实现会
 * **静默**用"文件剩余部分"当块（键集被污染却仍"看起来通过"）。把边界暴露给断言，
 * 才能把这种静默失效变成一条会红的检查。
 */
function answerKeysFrom(rawSrc) {
  const src = LF(rawSrc)
  const tierLine = src.match(/\n(\s*)"tier": tier,/)
  if (tierLine === null) return { keys: [], start: -1, end: -1 }
  const indent = tierLine[1]
  const start = src.indexOf(tierLine[0])
  const end = src.indexOf(`\n${indent.slice(0, -4)}}\n`, start)
  const block = src.slice(start, end === -1 ? src.length : end)
  const keys = [...block.matchAll(new RegExp(`^${indent}"${KEY_RE_SRC}":`, 'gm'))].map((x) => x[1])
  return { keys, start, end }
}

const ENGINE_KEYS = verificationKeysFrom(readSource('src/core/llm/ks_answer.py'))

/* ------------------------------------------------------------------ *
 * 样本：与引擎 `_describe_unsupported` 真实产出同形（含长中文 reason）
 *
 * ⚠ 长度事实（2026-09-17 实测，勿凭印象改）：这条真实 reason 是 **94 字符**，
 * 单独看并没超 160。**让通用 compact 路径失效的不是 reason 长度，而是整条
 * JSON 化后的长度（~191）**——键名+标点就占掉近百字符，留给 reason 的余量不足。
 * 下面的对照用真代码算，不依赖这个数。
 * ------------------------------------------------------------------ */

/** 与 `typed_verifier._describe_unsupported` 的 `same_standard_not_retrieved` 同文。 */
const REAL_REASON =
  '该条款号属于本轮证据内的标准 GB 30871-2022，但这一条**未被检索出来**'
  + '——属检索召回问题（可扩大检索范围/补该条），不是模型编造。'
  + '本次仍不作为依据（规则：只引证据内条款）。'

const ENGINE_PAYLOAD = {
  is_valid: false,
  answer_confidence: 'mid',
  confidence_reasons: ['存在证据外条款号引用'],
  unsupported_clauses: ['5.2.3'],
  unsupported_context: [{
    clause_number: '5.2.3',
    standard_no: 'GB 30871-2022',
    verdict: 'same_standard_not_retrieved',
    reason: REAL_REASON,
  }],
  unverified_numbers: [{ original: '2.0h', output: '3h', violation: 'number_tampered' }],
  modality_violations: [],
  legal_element_violations: [],
  citation_index_warnings: ['未找到条款 5.2.3 的索引'],
}

/* ------------------------------------------------------------------ *
 * 1. 长 reason 必须完整到达（这是本文件存在的头号理由）
 * ------------------------------------------------------------------ */

{
  const entry = ENGINE_PAYLOAD.unsupported_context[0]

  // 对照**用真代码**（shortList 就是通用路径本身），不靠手算、不靠复刻：
  // 通用路径把整条 JSON 化再截 160 ⇒ 中文 reason 的尾巴必然丢。
  const generic = shortList(ENGINE_PAYLOAD.unsupported_context)[0]
  const GENERIC_TAIL = '只引证据内条款'      // 真实 reason 的结尾
  check('通用 compact 路径确实会丢内容（真代码对照，证明本模块的必要性）',
    typeof generic === 'string' && !generic.includes(GENERIC_TAIL),
    typeof generic === 'string' ? `len=${generic.length}` : typeof generic)
  check('通用路径条目被截到 160 以内', typeof generic === 'string' && generic.length <= 160,
    typeof generic === 'string' ? String(generic.length) : '')
  check('JSON 化后 >160（通用路径容不下这一条）',
    JSON.stringify(entry).length > 160, `jsonLen=${JSON.stringify(entry).length}`)

  const out = trimVerification(ENGINE_PAYLOAD)
  check('trimVerification 非空（契约前提）', out !== null)

  const ctx = out.unsupported_context
  check('unsupported_context 被转发（不是静默丢弃）', Array.isArray(ctx) && ctx.length === 1,
    JSON.stringify(ctx))

  const one = (ctx && ctx[0]) || {}
  check('四条键齐全（clause_number/standard_no/verdict/reason）',
    one.clause_number === '5.2.3' && one.standard_no === 'GB 30871-2022'
    && one.verdict === 'same_standard_not_retrieved' && typeof one.reason === 'string',
    JSON.stringify(one))

  check('reason 未被截断（原文一字不差）', one.reason === REAL_REASON,
    `len=${(one.reason || '').length} vs ${REAL_REASON.length}`)
  check('reason 不是被 JSON 化的整对象（结构化透出，不 stringify）',
    typeof one.reason === 'string' && !one.reason.startsWith('{'),
    String(one.reason).slice(0, 40))
}

/* ------------------------------------------------------------------ *
 * 2. 超 REASON_CAP 才截断，且**显式标出**截断（不假装完整）
 * ------------------------------------------------------------------ */

{
  const huge = '甲'.repeat(REASON_CAP + 50)
  const out = trimUnsupportedContext([{ clause_number: '1', standard_no: 'X',
    verdict: 'unknown', reason: huge }])
  const r = out[0].reason
  check('超长 reason 被截断到 REASON_CAP 附近', r.length < huge.length,
    `len=${r.length}`)
  check('截断**显式可辨**（带 [已截断] 标记）', r.includes('[已截断]'), r.slice(-12))
  const exact = '乙'.repeat(REASON_CAP)
  check('恰好等于上限时不截断、不加标记',
    trimUnsupportedContext([{ reason: exact }])[0].reason === exact)
}

/* ------------------------------------------------------------------ *
 * 3. 不造字段、不编默认值（缺失一律如实）
 * ------------------------------------------------------------------ */

{
  const out = trimUnsupportedContext([{ clause_number: '9' }])
  check('引擎没给的字段一律 null（不推断）',
    out[0].standard_no === null && out[0].verdict === null && out[0].reason === null,
    JSON.stringify(out[0]))

  const v = trimVerification({ is_valid: true, unsupported_context: [{}] })
  check('verification 缺 answer_confidence 时退到 unknown（既有约定不变）',
    v.answer_confidence === 'unknown')
  check('verification 缺各列表时给空数组（不是 undefined）',
    Array.isArray(v.unsupported_clauses) && v.unsupported_clauses.length === 0)
}

/* ------------------------------------------------------------------ *
 * 4. 非对象/空输入不抛
 * ------------------------------------------------------------------ */

{
  check('trimVerification(null/undefined/"x") === null',
    trimVerification(null) === null && trimVerification(undefined) === null
    && trimVerification('x') === null)
  check('unsupported_context 非数组 → []（不抛、不造）',
    trimUnsupportedContext(null).length === 0
    && trimUnsupportedContext('x').length === 0
    && trimUnsupportedContext([null, 'x']).length === 0)
}

/* ------------------------------------------------------------------ *
 * 5. 有界性：列表按 VERIFY_LIST_CAP 截断（移动前后行为不变）
 * ------------------------------------------------------------------ */

{
  const many = Array.from({ length: VERIFY_LIST_CAP + 5 }, (_, i) => `n${i}`)
  check('shortList 按 VERIFY_LIST_CAP 截断', shortList(many).length === VERIFY_LIST_CAP)
  const manyCtx = Array.from({ length: VERIFY_LIST_CAP + 5 }, (_, i) => ({ clause_number: String(i) }))
  check('unsupported_context 同样按 VERIFY_LIST_CAP 截断',
    trimUnsupportedContext(manyCtx).length === VERIFY_LIST_CAP)
  check('空列表 → []', shortList([]).length === 0 && shortList(null).length === 0)
}

/* ------------------------------------------------------------------ *
 * 6. **白名单不许漏字段**：逐键探测引擎真实字段集
 * ------------------------------------------------------------------ */

{
  check('从 ks_answer.py 解析到引擎字段集',
    ENGINE_KEYS.length >= 8, `${ENGINE_KEYS.length} keys: ${ENGINE_KEYS.join(',')}`)

  // **CRLF 自检**（独立复核 2026-09-17 报的脆弱点）：本仓库 core.autocrlf=true，
  // 全新 clone 出来是 CRLF。若解析对换行敏感，键集会**静默**变成空/错，
  // 于是"漏转发检测"看起来通过而实际瞎了。这里用 CRLF 变体对照，永久钉住。
  {
    const lf = readSource('src/core/llm/ks_answer.py')
    const crlf = lf.replace(/\n/g, '\r\n')
    check('verification 键解析对 CRLF 免疫',
      verificationKeysFrom(crlf).join(',') === ENGINE_KEYS.join(','),
      `crlf=${verificationKeysFrom(crlf).length} lf=${ENGINE_KEYS.length}`)
  }

  // 逐键探测：把该键单独喂进去，看裁剪结果里还在不在。
  const dropped = ENGINE_KEYS.filter((k) => {
    const probe = { [k]: k === 'is_valid' ? true : [{ x: 1 }] }
    const out = trimVerification(probe)
    return out === null || !(k in out)
  })
  check('引擎 verification 的每个字段都被转发（无静默丢弃）',
    dropped.length === 0, dropped.length === 0 ? 'none' : `DROPPED: ${dropped.join(',')}`)

  // 反向：白名单里不该有引擎根本不发的键（死转发 = 误导下一个人）。
  const known = new Set(ENGINE_KEYS)
  const extra = Object.keys(trimVerification(
    Object.fromEntries(ENGINE_KEYS.map((k) => [k, k === 'is_valid' ? true : []]))),
  ).filter((k) => !known.has(k))
  check('白名单没有引擎不发的键（SSE 专属字段另行处理）',
    extra.length === 0, extra.length === 0 ? 'none' : `EXTRA: ${extra.join(',')}`)
}

/* ------------------------------------------------------------------ *
 * 7. 转发还不够——**提示词必须告诉模型拿它做什么**
 *
 * 只把字段送到模型眼前、却不指示它做什么，等于把"静默丢弃"换成"静默不理会"。
 * 提示词文本本身就是产物，故这里直接对源码断言（不是复刻算法）。
 * ------------------------------------------------------------------ */

{
  const src = readSource('plugin/src/index.js')
  const m = src.match(/name: 'ks_answer',[\s\S]*?parameters:/)
  const desc = m === null ? '' : m[0]
  check('ks_answer 描述提到 unsupported_context', desc.includes('unsupported_context'))
  check('描述给出两种 verdict 的**含义**（模型要照实说）',
    desc.includes('same_standard_not_retrieved')
    && desc.includes('outside_evidence_standard'))
  check('描述要求"必须披露"而不是"可以忽略"',
    desc.includes('MUST disclose') && desc.includes('Never present such a citation as support'))
}

/* ------------------------------------------------------------------ *
 * 8. 答案层（`trimAnswer`）不许漏字段——**同一个失败模式，上一层**
 *
 * `trimVerification` 漏字段的症状是"模型看不到核验结论"；`trimAnswer` 漏字段的症状
 * 更外面一层：整个 `material_usage`（材料平面用了什么）在工具返回值里**消失**。
 * 所以这里直接**调真函数**（index.js 顶层没有 DSH import，node 可以 import），
 * 并拿引擎源码解析出的键逐个核对。
 * ------------------------------------------------------------------ */

{
  const { trimAnswer } = await import('../src/index.js')

  // 引擎 `answer()` 真实返回的键（含 `_meta`，它在桥侧被折成 meta_summary）。
  //
  // ⚠ 必须**按缩进**只取顶层键：这个 `return {...}` 里的 `_meta` 是**嵌套字典**，
  // 用 `^\s*"key":` 会把 `_meta` 的子键（query/intent/…）一并抓进来，于是断言会
  // 误报"这些字段被丢弃"——本冒烟第一版就是这么红了一次（是测试的错，不是代码的错）。
  const src = readSource('src/core/llm/ks_answer.py')
  const { keys: answerKeys } = answerKeysFrom(src)
  check('从 ks_answer.py 解析到答案字段集（仅顶层键）', answerKeys.length >= 7,
    `${answerKeys.length} keys: ${answerKeys.join(',')}`)
  check('嵌套的 _meta 子键未被误当顶层字段',
    !answerKeys.includes('query') && !answerKeys.includes('intent'), answerKeys.join(','))
  // CRLF 自检（同上）：块边界必须真找得到——找不到时旧实现会静默扩到文件末尾。
  {
    const lf = readSource('src/core/llm/ks_answer.py')
    const crlf = lf.replace(/\n/g, '\r\n')
    const a = answerKeysFrom(lf)
    const b = answerKeysFrom(crlf)
    check('答案块边界在 CRLF 下也找得到（避免静默扩块）',
      a.end !== -1 && b.end !== -1 && a.keys.join(',') === b.keys.join(','),
      `lfEnd=${a.end} crlfEnd=${b.end}`)
  }

  // `_meta` 是唯一**有意**不直接转发的键（折成 meta_summary）；其余必须逐个在场。
  const INTENTIONAL = new Set(['_meta'])
  const probe = Object.fromEntries(answerKeys.map((k) => [
    k, k === '_meta' ? {} : (k === 'material_usage' ? { project_id: 'p', counts: {} } : null)]))
  const out = trimAnswer(probe)
  const missing = answerKeys.filter((k) => !INTENTIONAL.has(k) && !(k in (out ?? {})))
  check('引擎答案字段全部被转发（含 material_usage）',
    missing.length === 0, missing.length === 0 ? 'none' : `DROPPED: ${missing.join(',')}`)

  // 有意的映射必须在场（否则 `_meta` 的丢弃就没有替代物 = 审计信息丢失）。
  check('_meta 被折成 meta_summary（不是简单丢弃）', out !== null && 'meta_summary' in out)

  // 真值语义：material_usage 缺席 → null（"没用材料"与"用了没命中"要能区分）
  const bare = trimAnswer({ tier: 'reference', notes: [] })
  check('material_usage 缺席时给 null（不造、不省略）',
    bare !== null && bare.material_usage === null)
  // 给了就要原样带上（不被裁剪、不被丢）
  const withMat = trimAnswer({ material_usage: { project_id: 'prj_x', counts: { total: 2 } } })
  check('material_usage 给定时原样转发',
    withMat.material_usage?.project_id === 'prj_x' && withMat.material_usage.counts.total === 2)
  check('trimAnswer(null/"x") === null 不抛', trimAnswer(null) === null && trimAnswer('x') === null)
}

/* ------------------------------------------------------------------ */

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-trim: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-trim: ${results.length}/${results.length} PASS`)
