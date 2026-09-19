#!/usr/bin/env node
/**
 * 把 DSH 官方文档「原文」按字节灌进 Hindsight 记忆库（`docs/` 英文正本）。
 *
 * 为什么要有这个脚本（而不是继续用 `hindsight_ingest_document`）：
 *   1. 那个工具要我把**全文放进上下文**再吐出去 —— 171 篇 2.8 MB 根本不可行；
 *   2. 手抄实测 2.6% 失真（77 行错 2 处），而**失真读起来是通顺的**，不报错；
 *   3. 子代理被官方插件禁用写记忆（`origin === "subagent"` ⇒ 直接 void），
 *      所以"派一堆子代理并行灌"这条路是不通的。
 *   ⇒ 直连 Hindsight HTTP API（插件自己就是这么写的），内容**从磁盘按字节读**，
 *     不经过我的上下文，也就不可能抄错。
 *
 * ⚠ 这是**写入**操作。按用户级规则必须**先获批**再跑；先 `--dry-run` 看清单。
 *
 * 协议（读自 `@vectorize-io/hindsight-coding-agents/dist/antigravity-hook.js`，非猜测）：
 *   POST {api}/v1/default/banks/{bank}/memories
 *     { items: [{ content, context, document_id, tags, strategy, observation_scopes }], async: true }
 *     → { operation_id }
 *   GET  {api}/v1/default/banks/{bank}/documents?limit=N   → { items:[{id, text_length, ...}], total }
 *   GET  {api}/v1/default/banks/{bank}/operations/{id}     → { status, progress, error_message }
 *   终态 = completed | failed | cancelled | error（取自插件的 TERMINAL 集合）
 *   `update_mode` 默认 `'replace'`：**同 document_id 再灌 = 删旧的、按新内容重跑**
 *     （所以那两篇手抄件可以用原 id 原地覆盖成字节级原文）。
 *   单文档抽取实测 ≈ 9 s / 2.5 K 字符 ⇒ 2.8 MB 大约要**跑几小时**，故必须可续跑。
 *
 * 用法：
 *   node scripts/ingest-dsh-docs-into-memory.mjs --dry-run
 *   node scripts/ingest-dsh-docs-into-memory.mjs --limit 3          # 先小批验一遍
 *   node scripts/ingest-dsh-docs-into-memory.mjs                    # 全量（可反复跑，自动跳过已入的）
 *   node scripts/ingest-dsh-docs-into-memory.mjs --only subsystems/ # 只灌某目录
 */
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '..')

/* ------------------------------------------------------------------ 参数 */
function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`)
  if (i === -1) return fallback
  const v = process.argv[i + 1]
  return v === undefined || v.startsWith('--') ? true : v
}
const CHECKOUT = String(arg('checkout', 'D:\\AI\\DSH\\deepseek-harness'))
const API = String(arg('api', 'http://127.0.0.1:8888'))
const BANK = String(arg('bank', 'coding-agent::zcode'))
const LIMIT = Number(arg('limit', 0)) || 0
const ONLY = arg('only', null)
const CONCURRENCY = Number(arg('concurrency', 4)) || 4
const DRY = Boolean(arg('dry-run', false))
/**
 * 语料根（相对检出）。默认 `docs`；要灌 `.agents/notes` 等别的语料就传 `--root`。
 * 有了它，"要不要灌决策记录"就变成**一条命令**，而不是一次重新写脚本。
 */
const ROOT = String(arg('root', 'docs'))
/** 只要匹配这条正则的（相对 ROOT 的路径）。默认：所有 `.md`，但**排除 `*.zh.md`**。 */
const MATCH = String(arg('match', '(?<!(\\.zh))\\.md$'))
/** doc_id 前缀。默认 `dsh-docs`（沿用既有 171 篇的命名）。 */
const ID_PREFIX = String(arg('id-prefix', 'dsh-docs'))
/** 额外标签（逗号分隔）——**用来给不同语料分域**，将来 reflect 可用 `tags` 只在该域里找。 */
const EXTRA_TAGS = String(arg('tag', '')).split(',').map((s) => s.trim()).filter(Boolean)
const slugRoot = ROOT.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '')
// 账本/状态**按语料分开**，否则灌 zh 会把 docs 的账本覆盖成半份
const STATE_FILE = String(arg('state', join(repoRoot, `docs/research/dsh-official/ingest-state-${slugRoot}.json`)))
const LEDGER = String(arg('ledger', join(repoRoot, `docs/research/dsh-official/INGEST-LEDGER-${slugRoot}.md`)))

/**
 * 手抄件占了这两个 id：**用原 id 原地覆盖**（update_mode 默认 replace），
 * 而不是新建一个 id —— 否则库里会同时留着"手抄版"和"字节版"两份同文，
 * 检索时命中哪份全看运气。这是本项目"不许留两份互相矛盾的事实"的直接推论。
 *
 * ⚠ 这两个 id 是**从库里逐字读出来的**（`GET /documents`），不是凭记忆写的。
 *   我第一版就是凭记忆写，把 AGENTS.md 那个 id 少写了一段（真库里 `agents-md-` 是**重复**的），
 *   结果"覆盖"静默变成了"新增一份" —— 一次凭记忆的抄写就足以制造重复事实。
 *   若哪天想把这个丑 id 洗成 `dsh-docs-agents-md-the-documentation-standard`：
 *   先按新 id 灌、核对无误后再 `DELETE /documents/<旧id>`（该端点存在，插件自己也在用）。
 */
const ID_OVERRIDES = new Map([
  ['docs/web-styling.md', 'dsh-docs-web-styling-md-web-ui-style-reference'],
  ['docs/AGENTS.md', 'dsh-docs-agents-md-agents-md-the-documentation-standard'],
])

// 去掉开头的 `docs/` 再拼前缀，否则 id 会长成 `dsh-docs-docs-xxx`（第一版就长这样）
const slug = (rel) => `${ID_PREFIX}-` + rel
  .replace(new RegExp(`^${ROOT.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/`), '')
  .replace(/\.md$/i, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/-zh$/, '')   // `foo.zh.md` 已经带了 zh，别再拼一次（否则 id 是 `...-foo-zh-zh`）
  .replace(/^-|-$/g, '')

const docIdFor = (rel) => ID_OVERRIDES.get(rel) ?? slug(rel)

/* -------------------------------------------------------------- 文档清单 */
/** 递归收集语料目录下的**所有** `.md`（含 `.zh.md`）。
 *  ⚠ 这里**不做**"排除 zh"的过滤 —— 那件事归 `MATCH` 正则管。
 *    我第一版把排除写在遍历函数里，结果 `--match '\.zh\.md$'` 永远扫不到东西
 *    （幸好"空集即报错"那条护栏当场把它拦下了，没有静默地"灌了 0 篇还报成功"）。 */
function walkDocs(dir, out = []) {
  for (const name of readdirSync(dir).sort()) {
    const p = join(dir, name)
    const st = statSync(p)
    if (st.isDirectory()) walkDocs(p, out)
    else if (name.endsWith('.md')) out.push(p)
  }
  return out
}

function gitRef() {
  try {
    return execFileSync('git', ['-C', CHECKOUT, 'rev-parse', '--short', 'HEAD'], { encoding: 'utf8' }).trim()
  } catch {
    return 'unknown'
  }
}

const rootDir = join(CHECKOUT, ROOT)
if (!existsSync(rootDir)) {
  console.error(`❌ 找不到语料目录：${rootDir}（--checkout / --root 对不对？）`)
  process.exit(1)
}
const matchRe = new RegExp(MATCH)

let files = walkDocs(rootDir)
  .filter((abs) => matchRe.test(relative(CHECKOUT, abs).split(sep).join('/')))
  .map((abs) => {
  const rel = relative(CHECKOUT, abs).split(sep).join('/')
  const raw = readFileSync(abs)                       // Buffer：按**字节**读
  const content = raw.toString('utf8')
  return {
    rel,
    abs,
    id: docIdFor(rel),
    bytes: raw.length,
    // 用**码点**数（不是 JS 的 UTF-16 长度）：DB 侧 text_length 是码点语义，
    // 星形平面字符（emoji 等）两者会差 1，用 length 会造出假的不一致。
    chars: [...content].length,
    sha256: createHash('sha256').update(raw).digest('hex'),
    content,
  }
})

if (ONLY) files = files.filter((f) => f.rel.includes(String(ONLY)))

// ⚠ 空集必须显式报警：扫不到 ≠ 通过（我在 order 检查里就踩过这个坑）
if (files.length === 0) {
  console.error('❌ 一篇都没扫到 —— 这几乎肯定是**扫描本身坏了**，不是"没有文档"。不继续。')
  process.exit(1)
}

/* ------------------------------------------------------ 已有文档（幂等用） */
async function api(path, init) {
  const url = `${API}/v1/default/banks/${encodeURIComponent(BANK)}${path}`
  const r = await fetch(url, { ...init, headers: { 'content-type': 'application/json' } })
  if (r.status === 429) {
    const wait = Math.min(60_000, Math.max(10_000, Number(r.headers.get('retry-after') ?? 15) * 1000))
    throw Object.assign(new Error('rate limited'), { rateLimited: true, wait })
  }
  if (!r.ok) throw new Error(`${init?.method ?? 'GET'} ${path} -> ${r.status} ${await r.text()}`)
  return r.json()
}

const existing = new Map()
// 只读枚举：干跑也要取，否则干跑**看不到**"这篇已经在库里、长度不一样"这个关键事实
for (let offset = 0; ; offset += 200) {
  const page = await api(`/documents?limit=200&offset=${offset}`)
  for (const it of page.items ?? []) existing.set(it.id, it)
  if (existing.size >= (page.total ?? 0) || (page.items ?? []).length === 0) break
}

const todo = files.filter((f) => {
  const cur = existing.get(f.id)
  // 已存在**且长度一致**才算入过；长度不一致 ⇒ 内容变了（或当初就是手抄的）⇒ 重灌
  return !(cur && cur.text_length === f.chars)
})

console.log('===============================================================')
console.log(' DSH 官方文档 → Hindsight 原文入库')
console.log('===============================================================')
console.log(`检出      : ${CHECKOUT}  @ ${gitRef()}`)
console.log(`记忆库    : ${BANK}   （API ${API}）`)
console.log(`文档      : ${files.length} 篇 / ${files.reduce((s, f) => s + f.bytes, 0).toLocaleString()} 字节`)
console.log(`已在库且长度一致（跳过）: ${files.length - todo.length} 篇`)
console.log(`本次要灌  : ${todo.length} 篇`)
console.log(`模式      : ${DRY ? 'DRY-RUN（不写任何东西）' : `真写，并发 ${CONCURRENCY}`}`)
console.log('')

if (DRY) {
  // 已经在库、但长度不一致的：这些是**会被原地覆盖**的（update_mode 默认 replace）
  const willReplace = files.filter((f) => existing.has(f.id) && existing.get(f.id).text_length !== f.chars)
  if (willReplace.length > 0) {
    console.log('⚠ 以下 id 已在库里、但长度与磁盘不一致 ⇒ 会被**原地覆盖**（不是新增一份）：')
    for (const f of willReplace) {
      const cur = existing.get(f.id)
      console.log(`  ${f.rel}\n    id=${f.id}  库里 ${cur.text_length.toLocaleString()} → 磁盘 ${f.chars.toLocaleString()} 字符（差 ${(f.chars - cur.text_length).toLocaleString()}）`)
    }
    console.log('')
  }
  for (const f of todo.slice(0, LIMIT || todo.length)) {
    console.log(`  ${f.rel}\n    id=${f.id}  ${f.chars.toLocaleString()} 字符  sha256=${f.sha256.slice(0, 16)}`)
  }
  if (LIMIT && todo.length > LIMIT) console.log(`  …（只显示前 ${LIMIT} 篇）`)
  console.log('\nDRY-RUN 结束，没有写入。')
  process.exit(0)
}

/* ------------------------------------------------------------------ 入库 */
// 语料标签：**显式给了 --tag 就用它，不再自动加**（否则中英两份会落进同一个标签域，
// 将来没法用 `tags` 把它们分开检索）。
const TAGS = ['source:upload', 'harness:dsh',
  ...(EXTRA_TAGS.length > 0 ? [] : [ROOT === 'docs' ? 'dsh-official-docs' : `corpus:${slugRoot}`]),
  ...EXTRA_TAGS]
const ref = gitRef()
const state = existsSync(STATE_FILE) ? JSON.parse(readFileSync(STATE_FILE, 'utf8')) : { results: {} }

async function withRetry(fn) {
  for (let attempt = 0; ; attempt++) {
    try { return await fn() } catch (e) {
      if (!e.rateLimited || attempt >= 5) throw e
      console.log(`  ⏳ 被限流，等 ${Math.round(e.wait / 1000)}s`)
      await new Promise((r) => setTimeout(r, e.wait))
    }
  }
}

/** 把一批 async 任务按并发上限跑完（不让宿主被突发请求按 429 掐掉）。 */
async function pool(items, limit, worker) {
  const out = []
  let i = 0
  const runners = Array.from({ length: Math.min(limit, items.length || 1) }, async () => {
    while (i < items.length) {
      const idx = i++
      out[idx] = await worker(items[idx], idx)
    }
  })
  await Promise.all(runners)
  return out
}

const batch = LIMIT ? todo.slice(0, LIMIT) : todo
console.log(`── 第 1 步：提交 ${batch.length} 篇（并发 ${CONCURRENCY}）──`)

const opIds = []
await pool(batch, CONCURRENCY, async (f) => {
  try {
    const res = await withRetry(() => api('/memories', {
      method: 'POST',
      body: JSON.stringify({
        async: true,
        items: [{
          content: f.content,
          context: `DSH 官方文档原文：${f.rel}（检出 ${ref}）`,
          document_id: f.id,
          tags: TAGS,
          strategy: 'document',
          // 与插件一致地显式带上，免得"作用域"变成取决于服务端版本的隐式属性
          observation_scopes: 'shared',
        }],
      }),
    }))
    if (res.operation_id) opIds.push({ op: res.operation_id, f })
    state.results[f.id] = { rel: f.rel, chars: f.chars, sha256: f.sha256, op: res.operation_id ?? null, status: 'submitted' }
    console.log(`  ✓ 提交 ${f.rel}`)
  } catch (e) {
    state.results[f.id] = { rel: f.rel, chars: f.chars, sha256: f.sha256, status: 'submit_failed', error: String(e.message) }
    console.log(`  ✗ 提交失败 ${f.rel} — ${e.message}`)
  }
})

/* -------------------------------------------------------- 等抽取真的做完 */
console.log(`\n── 第 2 步：等 ${opIds.length} 个抽取任务到终态（实测 ≈9s/2.5K 字符，别催）──`)
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'error'])
let pending = opIds.slice()
let lastLog = 0
while (pending.length > 0) {
  const still = []
  await pool(pending, CONCURRENCY, async ({ op, f }) => {
    try {
      const r = await withRetry(() => api(`/operations/${encodeURIComponent(op)}`))
      const status = String(r.status ?? '').toLowerCase()
      if (!TERMINAL.has(status)) { still.push({ op, f }); return }
      const facts = r.progress?.detail?.facts_committed ?? null
      state.results[f.id] = { ...state.results[f.id], status, facts, error: r.error_message ?? null }
      console.log(`  ${status === 'completed' ? '✓' : '✗'} ${f.rel} — ${status}${facts ? ` (${facts} 条事实)` : ''}${r.error_message ? ` — ${r.error_message}` : ''}`)
    } catch (e) {
      // 查不到 ≠ 失败：先当作还没完，下一轮再问（避免把网络抖动当业务失败）
      still.push({ op, f })
      state.results[f.id] = { ...state.results[f.id], status: 'poll_error', error: String(e.message) }
    }
  })
  pending = still
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))          // 每轮落盘 ⇒ 中断可续
  if (pending.length > 0) {
    const now = Date.now()
    if (now - lastLog > 30_000) { console.log(`  …还剩 ${pending.length} 个未到终态`); lastLog = now }
    await new Promise((r) => setTimeout(r, 15_000))
  }
}

/* ------------------------------------------------------------ 账本 + 复核 */
// 「长度一致」只是**必要条件**（排掉漏灌/截断/灌错文件）。要真证明"库里存的 = 磁盘那份"，
// 得把正文取回来算哈希 —— `GET /documents/<id>` 会返回 `original_text`，实测可用。
// 这一步是本脚本与"提交成功就算完"的分界线，故默认执行（`--no-roundtrip` 才跳过）。
console.log('\n── 第 3 步：跟库对账（不信"提交成功"，只信库里读回来的正文哈希）──')
const verify = new Map()
for (let offset = 0; ; offset += 200) {
  const page = await api(`/documents?limit=200&offset=${offset}`)
  for (const it of page.items ?? []) verify.set(it.id, it)
  if (verify.size >= (page.total ?? 0) || (page.items ?? []).length === 0) break
}

const ROUNDTRIP = !process.argv.includes('--no-roundtrip')
const textHash = (s) => createHash('sha256').update(Buffer.from(s, 'utf8')).digest('hex')

let ok = 0          // 哈希逐字一致
let lenOnly = 0     // 长度一致但哈希不同
const bad = []
if (ROUNDTRIP) {
  const roundTrips = await pool(files, CONCURRENCY, async (f) => {
    try {
      const d = await withRetry(() => api(`/documents/${encodeURIComponent(f.id)}`))
      return { f, text: typeof d.original_text === 'string' ? d.original_text : null, len: d.text_length }
    } catch (e) {
      return { f, text: null, len: null, err: String(e.message) }
    }
  })
  for (const r of roundTrips) {
    const f = r.f
    if (r.text !== null && textHash(r.text) === f.sha256) {
      ok++
      state.results[f.id] = { ...state.results[f.id], status: 'verified_verbatim', verified_chars: r.text.length }
    } else if (r.len === f.chars) {
      lenOnly++
      bad.push({ f, got: r.len, status: 'length_ok_hash_differs' })
      state.results[f.id] = { ...state.results[f.id], status: 'length_ok_hash_differs' }
    } else {
      bad.push({ f, got: r.len ?? r.err ?? null, status: r.err ? 'fetch_failed' : 'mismatch' })
      state.results[f.id] = { ...state.results[f.id], status: r.err ? 'fetch_failed' : 'mismatch' }
    }
  }
} else {
  for (const f of files) {
    const cur = verify.get(f.id)
    if (cur && cur.text_length === f.chars) ok++
    else bad.push({ f, got: cur?.text_length ?? null, status: 'length_only_check' })
  }
}
writeFileSync(STATE_FILE, JSON.stringify(state, null, 2))

const rows = files.map((f) => {
  const s = state.results[f.id] ?? {}
  const st = s.status === 'verified_verbatim' ? '✅ 逐字一致'
    : s.status === 'length_ok_hash_differs' ? '⚠ 长度一致但**哈希不同**'
      : s.status === 'skipped_pre_verified' ? '✅ 逐字一致（先前已核）'
        : `⚠ ${s.status ?? '未知'}`
  // 带上源文件 sha256（前 16 位）：账本要能自己说明"灌进去的是哪几个字节"，
  // 否则只有状态文件知道，账本就成了半份证据。
  return `| \`${f.rel}\` | \`${f.id}\` | ${f.chars.toLocaleString()} | ${f.sha256.slice(0, 16)} | ${st} | ${s.facts ?? ''} |`
})
writeFileSync(LEDGER, [
  '# DSH 官方文档原文入库账本',
  '',
  '> 由 `scripts/ingest-dsh-docs-into-memory.mjs` 生成，**不要手改**（改状态文件请用脚本重跑）。',
  `> 检出：\`${CHECKOUT}\` @ \`${ref}\`　记忆库：\`${BANK}\`　生成时间：${new Date().toLocaleString('sv-SE')}（本地时间）`,
  '',
  `- 文档总数：**${files.length}** 篇 / ${files.reduce((s, f) => s + f.bytes, 0).toLocaleString()} 字节`,
  `- **逐字一致（库里 \`original_text\` 的 sha256 = 磁盘文件的 sha256）：${ROUNDTRIP ? ok : '未做往返核对'}**${ROUNDTRIP ? ` / ${files.length}` : ''}`,
  ...(ROUNDTRIP && lenOnly > 0 ? [`- ⚠ 长度一致但**哈希不同**：**${lenOnly}** 篇（见下表，这是必须解释的异常，不是通过）`] : []),
  `- 不一致 / 缺失 / 取不回：**${bad.length}** 篇`,
  '',
  `核对方式：${ROUNDTRIP
    ? '对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。'
    : '只比对了 `text_length`（**必要条件，不是逐字证明**）—— 本次用了 `--no-roundtrip`。'}`,
  '',
  '⚠ 哈希一致证明"库里存的正文与磁盘那份逐字节相同（按 UTF-8 文本口径）"，',
  '**不**证明服务端抽取出的事实条数/质量正确，也不覆盖 `.agents/notes/`、`.zh.md` 译本等未纳入本账本的语料。',
  '⚠ 「抽取事实数」为空 = 本次跑**没有重新灌它**（它先前已入且逐字一致，被跳过），不是"抽取出了 0 条"。',
  '',
  '| 文档 | document_id | 字符 | 源 sha256(16) | 核对 | 抽取事实数 |',
  '|---|---|---|---|---|---|',
  ...rows,
  '',
].join('\n'))

console.log(`\n核对结果：逐字一致 ${ok}/${files.length}${lenOnly ? `（其中长度一致但哈希不同 ${lenOnly}）` : ''}；异常 ${bad.length} 篇`)
for (const b of bad.slice(0, 20)) console.log(`  ⚠ ${b.f.rel} — 库里 ${b.got ?? '无'} / 磁盘 ${b.f.chars}（${b.status}）`)
console.log(`\n账本已写：${relative(repoRoot, LEDGER)}`)
console.log(`状态文件（续跑用）：${relative(repoRoot, STATE_FILE)}`)
process.exit(bad.length === 0 && opIds.length === batch.length ? 0 : 1)
