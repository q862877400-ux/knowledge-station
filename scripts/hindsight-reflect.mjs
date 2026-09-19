#!/usr/bin/env node
/**
 * 宽问题版的 reflect：直连 Hindsight API，**可以指定输出上限**。
 *
 * ## 为什么需要它（真根因，2026-09-19 查到）
 * 插件工具 `hindsight_reflect(query)` **只暴露 `query`**，于是永远吃服务端默认值：
 * `ReflectRequest.max_tokens = 4096`（OpenAPI 原文："Maximum tokens for the response"）。
 * 一旦回答超过 4096 token，服务端**选择报错而不是截断**：
 *
 *   500 {"detail":"LLM output exceeded token limits (openai/deepseek-flash, scope=reflect).
 *        Input may need to be split into smaller chunks."}
 *
 * 那句话的后半句（"把输入拆小"）**是误导**：问题不在输入，在**输出上限**。
 * 实测：同一个"又宽又多问"的查询，`max_tokens: 8192` ⇒ **成功**（47 s）。
 *
 * ⇒ 所以宽问题用这个脚本，窄问题照旧用 `hindsight_reflect` 工具。
 *
 * ## 用法
 *   node scripts/hindsight-reflect.mjs "你的问题"
 *   node scripts/hindsight-reflect.mjs --max-tokens 16384 "更宽的问题"
 *   node scripts/hindsight-reflect.mjs --budget high "要挖得更深"
 *   node scripts/hindsight-reflect.mjs --tags dsh-official-docs "只在官方原文里找"
 *   node scripts/hindsight-reflect.mjs --json "机器可读"
 */
const API = 'http://127.0.0.1:8888'
const BANK = process.env.KS_HINDSIGHT_BANK ?? 'coding-agent::zcode'

const argv = process.argv.slice(2)
/** 取一个 `--flag value` 形式的值；没给就是 undefined。 */
function flag(name) {
  const i = argv.indexOf(`--${name}`)
  return i === -1 ? undefined : argv[i + 1]
}
/** 取一个 `--flag` 布尔开关。 */
function sw(name) {
  return argv.includes(`--${name}`)
}
const maxTokens = Number(flag('max-tokens') ?? 8192)
const budget = flag('budget') ?? 'low'
const tags = flag('tags') ? String(flag('tags')).split(',').map((s) => s.trim()).filter(Boolean) : undefined
const asJson = sw('json')

// query = 去掉所有 --flag 及其取值之后剩下的部分（这样问题里出现 `-` 也不会被吃掉）
const consumed = new Set()
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith('--')) {
    consumed.add(i)
    if (['--max-tokens', '--budget', '--tags'].includes(argv[i])) consumed.add(i + 1)
  }
}
const query = argv.filter((_, i) => !consumed.has(i)).join(' ').trim()
if (query === '') {
  console.error('用法：node scripts/hindsight-reflect.mjs [--max-tokens N] [--budget low|mid|high] [--tags a,b] "问题"')
  process.exit(2)
}

if (!Number.isFinite(maxTokens) || maxTokens <= 0) {
  console.error(`--max-tokens 必须是正数，收到 ${String(flag('max-tokens'))}`)
  process.exit(2)
}

const body = { query, budget, max_tokens: maxTokens }
if (tags) body.tags = tags

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
  // 把"到底是哪个上限"直接印出来，免得再误判成"问得太多"
  const hint = detail.includes('exceeded token limits')
    ? `\n⇒ 这是**输出上限**撞了（当前 --max-tokens ${maxTokens}）。加大它，或把问题拆窄。`
    : ''
  console.error(`❌ reflect 失败 HTTP ${res.status}（${elapsed}s）\n${detail}${hint}`)
  process.exit(1)
}

const json = await res.json()
const text = typeof json.text === 'string' ? json.text : JSON.stringify(json, null, 2)

if (asJson) {
  console.log(JSON.stringify({ ...json, _elapsed_s: Number(elapsed), _max_tokens: maxTokens }, null, 2))
} else {
  console.log(text)
  const usage = json.usage ?? {}
  const parts = [
    `${elapsed}s`,
    `max_tokens=${maxTokens}`,
    `budget=${budget}`,
    tags ? `tags=${tags.join(',')}` : null,
    usage.total_tokens !== undefined ? `用量=${JSON.stringify(usage)}` : null,
    Array.isArray(json.based_on) ? `基于 ${json.based_on.length} 条` : null,
  ].filter(Boolean)
  console.error(`\n── ${parts.join(' · ')}`)
}
