/**
 * ks-dsh-plugin — scripts/smoke-turn-routes.mjs
 *
 * 「本轮」只读口（S1-b）的路由回归。钉四件事：
 *   ① 路由注册为 **exact** 且路径**无尾斜杠**（channels 死按钮的教训：真派发器
 *      判据 `pathname === prefix || startsWith(prefix + '/')` —— 这里用 exact 更严）；
 *   ② 暂存语义：每会话**最近一次**（后写覆盖先写）；
 *   ③ 会话隔离：?session= 别家 ⇒ null；不带 session ⇒ 全局最近（回执带 session）；
 *   ④ 方法守卫：非 GET → 405。
 *
 * ⚠ 桩与真派发器**同判据**（smoke-channels-routes 的教训：桩比真的宽松 = 替 bug 作证）。
 * 用法：node scripts/smoke-turn-routes.mjs   （退出码 0 = 全通过）
 */
import { KS_TURN_LAST_PATH, recordKsTurn, registerKsTurnRoutes } from '../src/turn.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ---- 与真派发器同构的两张表 + 假 req/res（同 smoke-channels-routes 的形状） ---- */
const exactRoutes = new Map()
const prefixRoutes = new Map()
const ctx = {
  webServer: {
    register(def) {
      (def.kind === 'prefix' ? prefixRoutes : exactRoutes).set(def.path, def)
      return () => {}
    },
  },
}
function resolveRoute(path) {
  const exact = exactRoutes.get(path)
  if (exact !== undefined) return exact
  let best = null
  for (const [p, def] of prefixRoutes) {
    if (p !== path && !path.startsWith(`${p}/`)) continue
    if (best === null || p.length > best.path.length) best = { path: p, def }
  }
  return best === null ? undefined : best.def
}

function makeRes() {
  const out = { status: null, body: null }
  return {
    out,
    writeHead(status) { out.status = status },
    end(text) { try { out.body = JSON.parse(text) } catch { out.body = text } },
  }
}
async function invoke(path, method = 'GET') {
  // ⚠ 真派发器按 **pathname** 认路由（query 不参与匹配）——桩同判据（我第一版
  // 拿整条 URL 去匹配 ⇒ `?session=s1` 全部"路由未注册"，桩自己先炸了）。
  const def = resolveRoute(path.split('?')[0])
  if (def === undefined) throw new Error(`路由未注册: ${path}`)
  const req = { method, url: path, destroy: () => {} }
  const res = makeRes()
  await def.handler(req, res)
  return { status: res.out.status, body: res.out.body }
}

const disposer = registerKsTurnRoutes(ctx)

check('路由注册为 exact 且唯一（无前缀路由、无第二张表）',
  exactRoutes.size === 1 && prefixRoutes.size === 0 && exactRoutes.has(KS_TURN_LAST_PATH),
  [...exactRoutes.keys()].join(','))
check('路径字面 = /ks/turn/last 且**无尾斜杠**（死按钮教训的防呆）',
  KS_TURN_LAST_PATH === '/ks/turn/last' && !KS_TURN_LAST_PATH.endsWith('/'))
check('返回 disposer（随 fiber 撤销）', typeof disposer === 'function')

{
  const empty = await invoke(KS_TURN_LAST_PATH)
  check('空暂存 ⇒ data:null（如实说"还没有"，不编造）',
    empty.status === 200 && empty.body.ok === true && empty.body.data === null,
    JSON.stringify(empty.body))

  recordKsTurn('s1', {
    query: 'Q1',
    evidence: [{ standard_no: 'GB 1', clause_number: '4.2' }],
    notes: ['N1'],
    verification: { is_valid: true },
    mode: { forensic: true, bookmarksOnly: false, folderId: null, folderName: null, materialProjectName: null },
  })
  const got = await invoke(`${KS_TURN_LAST_PATH}?session=s1`)
  // ⚠ 复核 M7：断言名曾写"整包透传"却只钉 2 字段（冒领）——现钉 **5 字段**并按实命名。
  check('暂存后按会话取回（query/evidence/notes/verification/mode 五字段原样透传）',
    got.body.data?.turn?.query === 'Q1' && got.body.data.turn.evidence[0].standard_no === 'GB 1'
    && got.body.data?.turn?.notes?.[0] === 'N1'
    && got.body.data?.turn?.verification?.is_valid === true
    && got.body.data?.turn?.mode?.forensic === true,
    JSON.stringify(got.body).slice(0, 80))
  check('回执带 seq（S1-c 自动切达轮询的判据字段，缺了它客户端只能瞎猜）',
    typeof got.body.data?.seq === 'number' && got.body.data.seq > 0,
    JSON.stringify(got.body.data?.seq))

  const other = await invoke(`${KS_TURN_LAST_PATH}?session=s2`)
  check('会话隔离：别家的会话取不到（不串会话）',
    other.body.data === null, JSON.stringify(other.body))

  recordKsTurn('s1', { query: 'Q2', evidence: [] })
  const again = await invoke(`${KS_TURN_LAST_PATH}?session=s1`)
  check('每会话只留**最近一次**（Q1 被 Q2 覆盖）',
    again.body.data?.turn?.query === 'Q2', JSON.stringify(again.body.data?.turn?.query))

  recordKsTurn('s2', { query: 'Q3', evidence: [] })
  const latest = await invoke(KS_TURN_LAST_PATH)
  check('不带 session ⇒ 全局最近一次（回执带 session，能看出读的是谁）',
    latest.body.data?.turn?.query === 'Q3' && latest.body.data.session === 's2',
    JSON.stringify({ q: latest.body.data?.turn?.query, s: latest.body.data?.session }))

  const put = await invoke(KS_TURN_LAST_PATH, 'PUT')
  check('非 GET → 405（只读口没有写面）', put.status === 405, JSON.stringify(put.body))
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== turn-routes smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
