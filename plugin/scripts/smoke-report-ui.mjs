/**
 * ks-dsh-plugin — scripts/smoke-report-ui.mjs
 *
 * **客户端侧产出接线**的契约冒烟（Phase D-3b：研究报告 / PPT）。
 *
 * ## 为什么必须单独验（不能只靠「产物里有那句文案」）
 * 产出路由与材料路由的**参数位置不同**，客户端这一层最容易写错且**错得很安静**：
 *   · 材料路由：`project_id` 在 **query**（`pickQuery`）；
 *   · 产出路由：`project_id` 在 **body**（`plugin/src/report.js` 从 body 取，
 *     且缺了就 400 `缺少 project_id`）。
 * 把两者写成一样 ⇒ 一个必然 400。另外还有三条同款风险：
 *   · 多发一个主机白名单外的键（`/ks/report/research` 是**白名单转发**，界面不该发明字段）；
 *   · 空串也照发（主机侧 `typeof raw[key] === 'string' && raw[key] !== ''` —— 空串本就不会进，
 *     但界面**发空串**会让"我没有结论"与"我要一份空结论"混起来）；
 *   · `dry_run` 写成字符串 `'false'`（主机侧 `=== true` 判定 ⇒ 永远是 false，
 *     界面以为在预览、其实落了盘）。
 *
 * 用法：node scripts/smoke-report-ui.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

const tmp = await mkdtemp(join(tmpdir(), 'ks-report-ui-'))
const outPath = join(tmp, 'api.bundle.mjs')
await build({
  entryPoints: [join(pluginRoot, 'client', 'api.ts')],
  bundle: true, platform: 'node', format: 'esm', outfile: outPath,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  logLevel: 'warning',
})
const api = await import(pathToFileURL(outPath).href)

let calls = []
let nextResponse = null
/** 默认桩：记录调用并回 `nextResponse`（第 6 节会临时换成自己的桩，收尾必须换回来）。 */
const stubFetch = async (url, init) => {
  calls.push({ url: String(url), init: init ?? {} })
  if (nextResponse === null) throw new Error('（冒烟未设置响应）')
  return nextResponse
}
globalThis.fetch = stubFetch
const jsonRes = (body, { status = 200, ok = true } = {}) =>
  ({ ok, status, async json() { return body } })
const envelope = (data) => jsonRes({ ok: true, data })

const PROJ = 'prj_smoke_report'
const ALLOWED = ['project_id', 'title', 'query', 'conclusion_md', 'limit', 'dry_run']

/* ---------------------------------------------------- 1. 位置与白名单（报告） */
{
  calls = []
  nextResponse = envelope({ title: 'T', markdown: '# x', counts: {}, warnings: [] })
  await api.exportResearchReport(PROJ, { query: '住宿标准是多少', conclusionMd: '结论' })
  const [c] = calls
  check('打到产出的报告路由（路径逐字）', c.url === '/ks/report/research', c.url)
  check('⚠ project_id 在 **body**（材料路由在 query——两者不同，这里正是防"写成一样"）',
    c.url === '/ks/report/research' && !c.url.includes('project_id'), c.url)
  check('方法 POST + JSON 头',
    c.init.method === 'POST'
      && c.init.headers['content-type'] === 'application/json',
    JSON.stringify(c.init.headers))
  const body = JSON.parse(c.init.body)
  check('body 带 project_id / query / conclusion_md',
    body.project_id === PROJ && body.query === '住宿标准是多少' && body.conclusion_md === '结论',
    JSON.stringify(body))
  check('body 的键**全在白名单内**（主机是白名单转发，界面不发明字段）',
    Object.keys(body).every((k) => ALLOWED.includes(k)), JSON.stringify(Object.keys(body)))
}

/* ---------------------------------------------------- 2. 空串不发 / limit / dry_run */
{
  calls = []
  nextResponse = envelope({ markdown: '' })
  await api.exportResearchReport(PROJ, { query: '', title: '', conclusionMd: '' })
  const body = JSON.parse(calls[0].init.body)
  check('空串**不发**（"我没写结论" ≠ "我要一份空结论"）',
    JSON.stringify(Object.keys(body)) === '["project_id"]', JSON.stringify(body))
}
{
  calls = []
  nextResponse = envelope({ markdown: '预览' })
  await api.exportResearchReport(PROJ, { limit: 5, dryRun: true })
  const body = JSON.parse(calls[0].init.body)
  check('limit 是数字、dry_run 是**布尔 true**（写成字符串会让主机永远判成 false）',
    body.limit === 5 && body.dry_run === true
      && typeof body.dry_run === 'boolean', JSON.stringify(body))
}
{
  calls = []
  nextResponse = envelope({ markdown: '' })
  await api.exportResearchReport(PROJ, { dryRun: false })
  check('dry_run:false 也照发（"我要落盘"与"我没说"是两件事）',
    JSON.parse(calls[0].init.body).dry_run === false, calls[0].init.body)
}

/* ---------------------------------------------------- 3. 成功形状（报告） */
{
  nextResponse = envelope({
    title: '住宿标准研究', markdown: '# 报告', html: '<h1>报告</h1>',
    files: ['D:\\exports\\研究报告-x.md', 'D:\\exports\\研究报告-x.html',
      'D:\\exports\\研究报告-x.docx'],
    names: ['研究报告-x.md', '研究报告-x.html', '研究报告-x.docx'],
    counts: { approved: 3, pending: 2, rejected: 1 },
    warnings: ['结论里的 [[m:9]] 在本次依据集里不存在'],
    citations: { checked_material_refs: 4, bad_material_refs: 1, unchecked_law_refs: 2 },
  })
  const out = await api.exportResearchReport(PROJ, {})
  check('成功：markdown/files/counts **原样带出**（界面要显示落盘路径与计数）',
    out.markdown === '# 报告' && out.files?.length === 3 && out.counts?.pending === 2,
    JSON.stringify({ files: out.files, counts: out.counts }))
  check('三形态（.md/.html/.docx）都带出——界面逐条显示落盘路径（§10.92）',
    out.files?.[2]?.endsWith('.docx') === true, JSON.stringify(out.files))
  check('⚠ warnings 带出（引用对不上**不许**静默——界面必须显示）',
    Array.isArray(out.warnings) && out.warnings.length === 1, JSON.stringify(out.warnings))
  check('引用核验计数带出（含"本次无法核验"的法规引用）',
    out.citations?.unchecked_law_refs === 2 && out.citations?.checked_material_refs === 4,
    JSON.stringify(out.citations))
}

/* ---------------------------------------------------- 4. PPT 成功与依赖缺失 */
{
  calls = []
  nextResponse = envelope({ path: 'D:\\exports\\研究报告-x.pptx', name: '研究报告-x.pptx',
                            slide_count: 4, warnings: [], counts: { approved: 1 } })
  const out = await api.exportResearchSlides(PROJ, { query: 'Q' })
  check('打到 PPT 路由（路径逐字）',
    calls[0].url === '/ks/report/research/slides', calls[0].url)
  check('PPT：path / name / slide_count 带出',
    out.path?.endsWith('.pptx') === true && out.slide_count === 4, JSON.stringify(out))

  nextResponse = jsonRes({ error: { code: 'ppt_unavailable',
    message: '缺少 python-pptx：pip install python-pptx' } }, { status: 500, ok: false })
  let msg = ''
  try { await api.exportResearchSlides(PROJ, {}) } catch (err) { msg = String(err?.message ?? err) }
  check('缺 PPT 依赖 ⇒ **抛**并带出可操作的错误（不假装导出成功）',
    msg.includes('python-pptx'), msg)

  nextResponse = jsonRes({ error: { code: 'materials_not_found', message: '项目不存在: prj_x' } },
    { status: 404, ok: false })
  msg = ''
  try { await api.exportResearchReport(PROJ, {}) } catch (err) { msg = String(err?.message ?? err) }
  check('项目不存在 ⇒ 抛并带出引擎的 404 原因（同源错误，不翻成"生成失败"）',
    msg.includes('项目不存在'), msg)
}

/* ---------------------------------------- 6. 交付物取回（§10.100，客户端接线） */
// 用户报障："设置里的导入只接受 PDF，还有 html 呢" —— 真实缺口是**产物拿不到手**。
// 取回走引擎既有的 `/api/v1/export/download`（路径穿越纪律由引擎一家所有），
// 所以这里要钉住：① 打的是那条路径、② 名字必须 encode、③ Bearer 在场、
// ④ 403/404 如实抛出（不静默当成"没有产物"）。
{
  const session = (port = 51234) => jsonRes({ ok: true, engine: { port, pid: 1, reused: true }, token: 'tk-smoke' })
  const blobRes = (size = 3) => {
    const bytes = new Uint8Array(size)
    return { ok: true, status: 200, blob: async () => new Blob([bytes], { type: 'text/html' }) }
  }

  // 6a 正常路径
  calls = []
  let phase = 0
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init: init ?? {} })
    phase += 1
    return phase === 1 ? session() : blobRes()
  }
  const blob = await api.fetchExportBlob('研究报告-x.html')
  const dl = calls[1]
  check('取产物打到引擎既有的 /api/v1/export/download（**不新增宿主路由**）',
    dl.url === 'http://127.0.0.1:51234/api/v1/export/download?name=%E7%A0%94%E7%A9%B6%E6%8A%A5%E5%91%8A-x.html',
    dl.url)
  check('名字必须 URL-encode（中文文件名原样发会 400/丢名）',
    dl.url.includes('name=%E7%A0%94%E7%A9%B6') && !dl.url.includes('报告-x.html'), dl.url)
  check('带 Bearer（引擎端点要鉴权，和 fetchPdf 同一条通路）',
    dl.init.headers && dl.init.headers.Authorization === 'Bearer tk-smoke',
    JSON.stringify(dl.init.headers))
  check('返回 Blob 本体（界面拿它做 blob URL）',
    blob && typeof blob.size === 'number' && blob.size === 3, String(blob && blob.size))

  // 6b 403 / 404：必须**抛**且带出原因
  const fail = async (status, body, name) => {
    calls = []
    phase = 0
    globalThis.fetch = async (url, init) => {
      calls.push({ url: String(url), init: init ?? {} })
      phase += 1
      return phase === 1 ? session() : jsonRes(body, { status, ok: false })
    }
    let m = ''
    try { await api.fetchExportBlob(name) } catch (err) { m = String(err?.message ?? err) }
    return m
  }
  const m403 = await fail(403, { error: { code: 'forbidden', message: '非法路径' } }, '../../secrets.json')
  check('越权路径（含 ../）⇒ 抛"只允许 exports 目录内的产物"（不静默）',
    m403.includes('exports'), m403)
  const m404 = await fail(404, { error: { code: 'file_not_found', message: '文件不存在' } }, '研究报告-x.html')
  check('产物被清理 ⇒ 抛并带出文件名（点按钮没反应是最坏的结果）',
    m404.includes('研究报告-x.html'), m404)

  // 6c 401 自愈一次（会话轮换）
  calls = []
  phase = 0
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init: init ?? {} })
    phase += 1
    if (phase === 1) return session(51234)      // 第一次会话
    if (phase === 2) return jsonRes({ error: { code: 'unauthorized', message: 'x' } }, { status: 401, ok: false })
    if (phase === 3) return session(51235)      // 轮换后的会话
    return blobRes(7)
  }
  const blob2 = await api.fetchExportBlob('a.docx')
  check('401 ⇒ 重取会话再试一次（四个请求：session/download/session/download）',
    calls.length === 4 && blob2.size === 7, `calls=${calls.length} size=${blob2 && blob2.size}`)

  // ⚠ 收尾：把默认桩换回来（本节自己的桩不认识 nextResponse，留给第 5 节会炸）
  globalThis.fetch = stubFetch
}

/* ---------------------------------------- 5. 结论草稿（§10.96，客户端接线） */
{
  const DRAFT_ALLOWED = ['project_id', 'query', 'limit']
  calls = []
  nextResponse = envelope({ status: 'unapproved_draft', draft_md: '每晚不超过五百元 [[m:0]]。',
    citations: { material_refs: [0] }, warnings: [], llm_called: true, usable_indices: [0] })
  const out = await api.exportResearchDraft(PROJ, { query: '住宿标准', limit: 4 })
  const [c] = calls
  check('打到草稿路由（路径逐字）', c.url === '/ks/report/research/draft', c.url)
  const dbody = JSON.parse(c.init.body)
  check('草稿 body 只带 project_id/query/limit（**title/conclusion_md/dry_run 一个都不发**）',
    Object.keys(dbody).every((k) => DRAFT_ALLOWED.includes(k))
    && dbody.project_id === PROJ && dbody.query === '住宿标准' && dbody.limit === 4,
    JSON.stringify(dbody))
  check('`unapproved_draft` 与草稿正文带出（界面必须能看出**未经批准**）',
    out.status === 'unapproved_draft' && String(out.draft_md).includes('[[m:0]]'),
    JSON.stringify({ status: out.status, has_draft: Boolean(out.draft_md) }))
  check('草稿**不落盘**：返回里没有 files（与报告/PPT 的关键区别）',
    out.files === undefined, JSON.stringify(Object.keys(out)))

  nextResponse = jsonRes({ error: { code: 'llm_unavailable',
    message: '起草结论失败：调模型出错（未配置 Key）' } }, { status: 500, ok: false })
  let dmsg = ''
  try { await api.exportResearchDraft(PROJ, { query: 'Q' }) } catch (err) {
    dmsg = String(err?.message ?? err)
  }
  check('LLM 不可用 ⇒ **抛**并带出可操作的错误（不假装起草成功）',
    dmsg.includes('调模型出错'), dmsg)
}

await rm(tmp, { recursive: true, force: true })

const failed = results.filter((r) => !r.ok)
console.log(`\n== report-ui smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
