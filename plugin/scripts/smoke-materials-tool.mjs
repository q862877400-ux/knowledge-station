/**
 * ks-dsh-plugin — scripts/smoke-materials-tool.mjs
 *
 * `ks_materials`（材料平面只读工具，Phase B 第二步配套）回归。
 *
 * ## 为什么用**桩引擎**而不是真引擎
 * 本工具的价值全在"路径拼对没、状态过滤有没有透传、异常信封会不会被伪装成空结果"
 * ——这些都是**确定性**的映射问题，桩引擎能把每个分支都覆盖到（真引擎反而只能覆盖
 * 它当前恰好有的数据），且不依赖引擎是否已重启加载新路由。
 * 真引擎通道由 `smoke-effect-tool.mjs` 那类脚本覆盖；这里刻意做成零依赖。
 *
 * 跑法：node scripts/smoke-materials-tool.mjs   （退出码 0 = 全通过）
 */

import { createServer } from 'node:http'

import { makeMaterialsTool } from '../src/materials.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------- 桩引擎 ------------------------------- */

const seen = []          // 记录每次请求的 path + Authorization
// 响应器统一返回 `{ http?, body }`：**别用 `status` 当 HTTP 状态**——信封里已有一个
// 同名 `status:'success'` 字段，混用会让桩服务器写出非法状态码（本冒烟第一版就踩了）。
let responder = () => ({ body: { code: 200, status: 'success', data: [] } })

const server = createServer((req, res) => {
  const chunks = []
  req.on('data', (c) => chunks.push(c))
  req.on('end', () => {
    seen.push({ path: req.url, auth: req.headers.authorization ?? null })
    const r = responder(req.url)
    res.writeHead(r.http ?? 200, { 'content-type': 'application/json' })
    res.end(JSON.stringify(r.body ?? r))
  })
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const PORT = server.address().port

const fakeManager = { ensureLive: async () => ({ port: PORT, token: 'tok_stub' }) }
const tool = makeMaterialsTool(fakeManager)
const call = (args) => tool.execute(args, { signal: new AbortController().signal })

/* --------------------------- 1. 工具契约 --------------------------- */

{
  check('工具名是 ks_materials', tool.name === 'ks_materials', tool.name)
  check('action 枚举与描述一致', Array.isArray(tool.parameters.properties.action.enum)
    && tool.parameters.properties.action.enum.join(',') === 'projects,materials,inbox')
  check('描述说明"只读、不代批"', tool.description.includes('只读')
    && tool.description.includes('评审是**用户**的判断'))
  check('描述说明材料只有经 material_project_id 才进作答',
    tool.description.includes('material_project_id'))
}

/* --------------------------- 2. projects --------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: {
      code: 200, status: 'success',
      data: [
        { project_id: 'prj_a', name: '财报分析', authority_policy: { criterion: ['公司制度'] } },
        { project_id: 'prj_b', name: '宿舍改造', authority_policy: null },
      ],
    },
  })
  const out = await call({})            // 不传 action → 默认 projects
  check('默认 action=projects', out.action === 'projects' && out.ok === true)
  check('打到 /api/v1/materials/projects', seen[0].path === '/api/v1/materials/projects',
    seen[0]?.path)
  check('带 Bearer token', seen[0].auth === 'Bearer tok_stub', String(seen[0].auth))
  check('返回项目 id/name/策略', out.count === 2 && out.projects[0].project_id === 'prj_a'
    && out.projects[0].name === '财报分析', JSON.stringify(out.projects))
  responder = () => ({ body: { code: 200, data: [] } })
  const empty = await call({})
  check('空项目集给出可执行的 hint',
    empty.count === 0 && empty.hint.includes('还没有任何参考资料项目'), empty.hint)
}

/* --------------------------- 3. materials --------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: {
      code: 200, status: 'success',
      data: [
        { material_id: 'mat_1', title: '年度报告', source_tier: 'T1', tier_label: '用户自有原始件',
          tier_source: 'user', task_role: 'criterion', review_status: 'approved', chunk_count: 12,
          origin: 'user', kind: 'other', url: null, domain: null, tier_reason: null,
          content_hash: 'SHOULD_NOT_APPEAR', raw_path: 'D:\\secret\\path.pdf' },
        { material_id: 'mat_2', title: '待审稿', source_tier: 'T3', tier_label: '二手转述',
          review_status: 'pending', chunk_count: 3 },
        { material_id: 'mat_3', title: '被否稿', source_tier: 'T4', tier_label: '不可回溯',
          review_status: 'rejected', chunk_count: 1 },
      ],
    },
  })
  const out = await call({ action: 'materials', project_id: 'prj_a' })
  check('打到项目的 materials 路径',
    seen[0].path === '/api/v1/materials/projects/prj_a/materials', seen[0]?.path)
  check('评审计数正确', out.review_counts.approved === 1 && out.review_counts.pending === 1
    && out.review_counts.rejected === 1, JSON.stringify(out.review_counts))
  check('两个轴**分开**透出（source_tier 与 task_role 并存）',
    out.materials[0].source_tier === 'T1' && out.materials[0].task_role === 'criterion'
    && out.materials[0].tier_label === '用户自有原始件')
  check('pending 有如实提示（且指明不代批）',
    typeof out.note === 'string' && out.note.includes('尚未评审') && out.note.includes('用户'))
  // 内部/敏感字段不得外泄给模型（raw_path 是服务器本机路径；content_hash 是内部查重键）
  const dumped = JSON.stringify(out)
  check('不透出 raw_path / content_hash 等内部字段',
    !dumped.includes('SHOULD_NOT_APPEAR') && !dumped.includes('secret'), dumped.slice(0, 120))

  // status 过滤必须**透传**（否则"只看已批准"会静默变成"看全部"）
  seen.length = 0
  await call({ action: 'materials', project_id: 'prj_a', status: 'approved' })
  check('status 过滤透传到查询串',
    seen[0].path === '/api/v1/materials/projects/prj_a/materials?status=approved',
    seen[0]?.path)

  // 项目 id 必须编码（防注入到路径里）
  seen.length = 0
  await call({ action: 'materials', project_id: 'prj_a/../b?x=1' })
  check('project_id 被 URL 编码（不拼进路径结构）',
    seen[0].path.startsWith('/api/v1/materials/projects/prj_a%2F..%2Fb%3Fx%3D1/'),
    seen[0]?.path)
}

/* ----------------------------- 4. inbox ----------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: {
      code: 200, status: 'success',
      data: { dir: 'D:\\data\\materials\\prj_a', files: [{ file_name: 'a.pdf', size: 10 }] },
    },
  })
  const out = await call({ action: 'inbox', project_id: 'prj_a' })
  check('打到 inbox 路径',
    seen[0].path === '/api/v1/materials/projects/prj_a/inbox', seen[0]?.path)
  check('未登记文件如实标注"尚未登记 ⇒ 不会进作答"',
    out.count === 1 && out.hint.includes('尚未登记') && out.hint.includes('不会进入作答'))
}

/* --------------------------- 5. 失败不伪装 --------------------------- */

{
  // 缺 project_id：必须**报错**而不是替用户猜一个项目
  let threw = null
  try { await call({ action: 'materials' }) } catch (e) { threw = e }
  check('缺 project_id 时明确报错（不猜项目）',
    threw !== null && String(threw.message).includes('project_id'), String(threw?.message))

  // 信封异常（200 但没有 data）：必须抛，**不得**伪装成"这个项目没有材料"
  responder = () => ({ body: { code: 200, status: 'success' } })   // 无 data
  let threw2 = null
  try { await call({ action: 'materials', project_id: 'prj_a' }) } catch (e) { threw2 = e }
  check('信封缺 data 时抛错（不伪装"没有材料"）',
    threw2 !== null && String(threw2.message).includes('响应异常'), String(threw2?.message))

  // 非 200（旧引擎 404）：同样抛，且提示先 ks_ping
  responder = () => ({ http: 404, body: { code: 404, status: 'error', error: 'not_found' } })
  let threw3 = null
  try { await call({}) } catch (e) { threw3 = e }
  check('404 时抛错并建议 ks_ping',
    threw3 !== null && String(threw3.message).includes('ks_ping'), String(threw3?.message))

  // data 为 null（合法 JSON null）也必须当异常——不能当空列表
  responder = () => ({ body: { code: 200, data: null } })
  let threw4 = null
  try { await call({ action: 'materials', project_id: 'prj_a' }) } catch (e) { threw4 = e }
  check('data 为 null 时抛错（不当空列表）',
    threw4 !== null && String(threw4.message).includes('期望数组'), String(threw4?.message))

  // 形状不符（期望数组收到对象）同样抛——只查"有没有 data"不够
  responder = () => ({ body: { code: 200, data: { unexpected: true } } })
  let threw5 = null
  try { await call({ action: 'projects' }) } catch (e) { threw5 = e }
  check('projects 收到对象（形状不符）时抛错',
    threw5 !== null && String(threw5.message).includes('期望数组'), String(threw5?.message))

  // inbox 期望对象：收到数组也要抛
  responder = () => ({ body: { code: 200, data: [] } })
  let threw6 = null
  try { await call({ action: 'inbox', project_id: 'prj_a' }) } catch (e) { threw6 = e }
  check('inbox 收到数组（形状不符）时抛错',
    threw6 !== null && String(threw6.message).includes('期望对象'), String(threw6?.message))
}

server.close()

/* ------------------------------------------------------------------ */

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-materials-tool: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-materials-tool: ${results.length}/${results.length} PASS`)
