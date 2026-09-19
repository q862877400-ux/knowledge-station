#!/usr/bin/env node
/**
 * 宽问题版的 reflect：直连 Hindsight API，可指定**可见长度目标**与**标签作用域**。
 *
 * ## ⚠ 为什么会有这个脚本，以及我一开始把根因说错了（已更正，2026-09-19）
 *
 * 插件工具 `hindsight_reflect(query)` **只暴露 `query`**（`dsh.js:16966-16977`，
 * 且它固定用 `budget: 'high'`）⇒ 你没法传标签、也没法调长度目标。
 *
 * 我最初把这个脚本的用途写成"把输出上限从 4096 调大"，**那是错的**。独立复核 + 我自己复核
 * 服务端源码后确认（0.10.0，`hindsight_api`）：
 *
 * - `ReflectRequest.max_tokens`（默认 4096）**不是 provider 的输出上限**，而是
 *   **"想要的可见长度"**，以 **prompt 指令**形式下达
 *   （`engine/reflect/agent.py:794-798`、`:542-547`，注释明说 "NOT passed as the provider's
 *   max_completion_tokens"）。
 * - **真正的传输层上限**是服务端配置 **`reflect_max_completion_tokens`**
 *   （`config.py:1819` 默认 `None` ⇒ 不传该参数、用 provider 默认；env
 *   `HINDSIGHT_API_REFLECT_MAX_COMPLETION_TOKENS`，见 `config.py:968/4924`）。
 * - 那个 500 只在 **`finish_reason == 'length'`**（真的被截断）时抛
 *   （`providers/openai_compatible_llm.py:372-376`）。
 * - **实测反证**：本库唯一一条 reflect 失败记录是 `output_tokens=8192` —— 也就是说
 *   它是在 **8192** 上被截断的，而那次调用是 **split-synthesis 的 map 调用**
 *   （拿的是 `reflect_max_completion_tokens`，**从来不是**请求里的 `max_tokens`）。
 *   ⇒ 我之前"改成 8192 就成功了"是**巧合**，不是修好了。
 *
 * 所以：**要真正放宽那个上限，得改服务端配置**（见 `REALIGN.md` §五之三）；
 * 这个脚本能做的、也确实有用的两件事是：
 *   ① **标签作用域**（`--tags` + `--tags-match`，默认 `any_strict` = 只在该域里找、排除未打标签）；
 *   ② **budget**（喂给 reflect 的数据量越少，越不容易撞上限）。
 *
 * ## 用法
 *   node scripts/hindsight-reflect.mjs "你的问题"
 *   node scripts/hindsight-reflect.mjs --tags dsh-official-docs-zh "只在中译本里找"
 *   node scripts/hindsight-reflect.mjs --tags dsh-official-docs --tags-match all_strict "英文原文里找"
 *   node scripts/hindsight-reflect.mjs --budget low "省点钱/少喂数据"
 *   node scripts/hindsight-reflect.mjs --visible-tokens 8192 --json "机器可读"
 */
const API = 'http://127.0.0.1:8888'
const BANK = process.env.KS_HINDSIGHT_BANK ?? 'coding-agent::zcode'

const argv = process.argv.slice(2)

/** 取 `--flag value` 的值。**值缺失、或值本身是另一个 flag ⇒ 返回 true 让调用方报错**。 */
function flag(name) {
  const i = argv.indexOf(`--${name}`)
  if (i === -1) return undefined
  const v = argv[i + 1]
  if (v === undefined || v.startsWith('--')) return true   // ⚠ 别把下一个 flag 当值吃掉
  return v
}
const sw = (name) => argv.includes(`--${name}`)

/** 带值的 flag（缺值就报错退出，不静默取默认值）。 */
function valued(name, fallback) {
  const v = flag(name)
  if (v === undefined) return fallback
  if (v === true) {
    console.error(`❌ --${name} 后面缺值。`)
    process.exit(2)
  }
  return String(v)
}

const visibleTokens = Number(valued('visible-tokens', '4096'))
const budget = valued('budget', 'high')          // ⚠ 与插件工具对齐（它固定 high），否则两个入口行为不一致
const tags = (() => {
  const raw = flag('tags')
  if (raw === undefined) return undefined
  if (raw === true) { console.error('❌ --tags 后面缺值。'); process.exit(2) }
  return String(raw).split(',').map((s) => s.trim()).filter(Boolean)
})()
/**
 * 标签匹配方式。**默认 `any_strict`**：OR 且**排除未打标签的**。
 * 服务端默认是 `any`（包含未打标签）⇒ 那**不是**"只在这个域里找"，与本文档的说法不符，
 * 所以这里刻意改成严格的（复核 C8 指出了这个不一致）。
 */
const TAGS_MATCH = new Set(['any', 'all', 'any_strict', 'all_strict', 'exact'])
const tagsMatch = valued('tags-match', 'any_strict')
const asJson = sw('json')

if (!TAGS_MATCH.has(tagsMatch)) {
  console.error(`❌ --tags-match 只能是 ${[...TAGS_MATCH].join(' / ')}，收到 ${tagsMatch}`)
  process.exit(2)
}
if (!Number.isFinite(visibleTokens) || visibleTokens <= 0) {
  console.error(`❌ --visible-tokens 必须是正数，收到 ${String(flag('visible-tokens'))}`)
  process.exit(2)
}
if (tagsMatch !== 'any' && tags === undefined) {
  console.error('❌ --tags-match 只在给了 --tags 时才有意义。')
  process.exit(2)
}

// query = 去掉所有 --flag 及其取值之后剩下的部分
const consumed = new Set()
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith('--')) {
    consumed.add(i)
    const next = argv[i + 1]
    if (next !== undefined && !next.startsWith('--')) consumed.add(i + 1)
  }
}
const query = argv.filter((_, i) => !consumed.has(i)).join(' ').trim()
if (query === '') {
  console.error('用法：node scripts/hindsight-reflect.mjs [--tags a,b] [--tags-match any_strict] '
    + '[--budget low|mid|high] [--visible-tokens N] [--json] "问题"')
  process.exit(2)
}

const body = { query, budget, max_tokens: visibleTokens }
if (tags !== undefined) { body.tags = tags; body.tags_match = tagsMatch }

const url = `${API}/v1/default/banks/${encodeURIComponent(BANK)}/reflect`
const started = Date.now()
const res = await fetch(url, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
})
const elapsed = ((Date.now() - started) / 1000).toFixed(1)

if (!res.ok) {
  const detail = await res.text()
  // ⚠ 别再写"加大 --max-tokens 就好" —— 那不是这个错误的旋钮（见文件头）。
  const hint = detail.includes('exceeded token limits')
    ? '\n⇒ 这是**服务端传输层上限**撞了（`reflect_max_completion_tokens`），'
      + '**不是**请求里的 `max_tokens`/`--visible-tokens` 能调的。\n'
      + '   可行办法：① 把问题问窄；② 降 `--budget`（少喂数据）；'
      + '③ 用 `--tags` 圈小范围；④ 改服务端 `HINDSIGHT_API_REFLECT_MAX_COMPLETION_TOKENS` 后重启（见 REALIGN §五之三）。'
    : ''
  console.error(`❌ reflect 失败 HTTP ${res.status}（${elapsed}s）\n${detail}${hint}`)
  process.exit(1)
}

const json = await res.json()
const text = typeof json.text === 'string' ? json.text : JSON.stringify(json, null, 2)

if (asJson) {
  console.log(JSON.stringify({ ...json, _elapsed_s: Number(elapsed) }, null, 2))
} else {
  console.log(text)
  const usage = json.usage ?? {}
  const parts = [
    `${elapsed}s`,
    `budget=${budget}`,
    `可见长度目标=${visibleTokens}`,
    tags === undefined ? '无标签域（全库）' : `tags=${tags.join(',')}（${tagsMatch}）`,
    usage.total_tokens !== undefined ? `用量=${JSON.stringify(usage)}` : null,
    // 注意：`based_on` 常常是 null —— 别把"没有出处列表"当成"没用记忆"。
    Array.isArray(json.based_on) ? `基于 ${json.based_on.length} 条` : '（响应不带出处列表；要看出处查 /llm-requests 审计）',
  ].filter(Boolean)
  console.error(`\n── ${parts.join(' · ')}`)
}
