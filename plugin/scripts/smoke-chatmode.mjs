/**
 * ks-dsh-plugin — scripts/smoke-chatmode.mjs
 *
 * 「📜 查法规模式 / 🔖 仅收藏」离线冒烟（决策 14/16 的 DSH 转生版）。五段：
 *
 *  1. **host 状态与提示词**（src/chatmode.js，纯逻辑）：默认全关；开启后
 *     `forensicPromptFor` 返回取证纪律；按会话隔离；「仅收藏」依附父开关
 *     （父关自动降级）；关掉后不留状态；输入校验（非布尔/空白会话 id）；
 *     `makeChatModeSection` 从 `context.agent.session.id` 取会话 id；**子会话继承**
 *     （单跳、多跳、父关不继承、自环不成环）。
 *  2. **host 路由**（假 req/res 直打真实 handler；同源栅栏由 index.js 的 webCtx
 *     施加，这里直打 handler 故只验业务语义）：400/415/413/405 全边界 + 归一化 +
 *     回显 session 与落盘结果 + `no-store`。
 *  3. **多进程与落盘安全**：合并落盘（别的 dsh 进程写的会话不被抹掉）、本进程关掉的
 *     会话不被磁盘旧值复活、原子写无 .tmp 残骸、坏文件备份后仍可写、非 ENOENT 读错误
 *     → degraded + **拒绝写盘**（绝不用空快照覆盖好数据）。
 *  4. **重启后仍生效**：另起一个 node 进程（同一 KS_CHATMODE_DIR）导入本模块，断言提示段
 *     直接返回纪律 —— 这条是 verifier P0-1 的最小复现（旧实现要等 client 的 GET 才加载
 *     状态，重启后首轮提问会静默丢掉开关）。
 *  5. **client 半**：注册形状（槽名/id/order/disposer 真的退订/槽缺失 warn 一次）；
 *     纯展示组件 `KsChatModeRow` 用 react-dom/server 渲染**全部分支**（加载中/失败+
 *     重试/开启两药丸/关闭只有 📜/未落盘告警）；读取路径 `loadChatModeOnce` 用 stub
 *     fetch 直测（成功交 mode、失败交 err、已 abort 不回调）。
 *     边界（诚实标注）：本仓没有 DOM 测试环境（无 jsdom），所以 React 自身的
 *     effect/事件管线不在此覆盖——由真机点击验收。
 *
 * 用法：node scripts/smoke-chatmode.mjs   （退出码 0 = 全通过）
 */
import { execFile } from 'node:child_process'
import { EventEmitter } from 'node:events'
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { promisify } from 'node:util'

import { build } from 'esbuild'

const run = promisify(execFile)
const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

// 隔离落盘：chatmode 的状态文件目录优先跟随 $KS_CHATMODE_DIR（见 chatModeFilePath）。
// 必须**在导入 src/chatmode.js 之前**设成临时目录，否则冒烟会覆盖真实
// %APPDATA%\KnowledgeStation\ks-chatmode.json（把用户真开着的会话开关冲掉）。
// 刻意不用 $KS_DATA_DIR —— 那会连带把引擎的数据目录/库也指到临时目录。
const dataDir = await mkdtemp(join(tmpdir(), 'ks-chatmode-smoke-'))
process.env.KS_CHATMODE_DIR = dataDir
const statePath = join(dataDir, 'ks-chatmode.json')
const chatModuleUrl = pathToFileURL(join(pluginRoot, 'src', 'chatmode.js')).href

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b)
const throws = (fn) => {
  try { fn(); return false } catch { return true }
}
/**
 * 全关基线的**唯一**来源。
 *
 * 原先这里把 4 个字段的字面量抄了 12 遍，于是 2026-09-17 给 mode 加
 * `materialProjectId/materialProjectName` 两个维度时，14 条断言一起变红——
 * 全是"测试写死了形状"而不是行为出错。改成一个基座 + `mode({...})` 覆盖，
 * 以后再加维度只改这一处。
 */
const ALL_OFF = {
  forensic: false, bookmarksOnly: false, folderId: null, folderName: null,
  materialProjectId: null, materialProjectName: null,
}
/** 期望值构造器：只写**要变的**维度。 */
const mode = (over = {}) => ({ ...ALL_OFF, ...over })
const readState = async () => {
  const text = await readFile(statePath, 'utf8').catch(() => '')
  try { return JSON.parse(text) } catch { return null }
}

/* ================================================ 1. host 状态与提示词 */
const chat = await import(chatModuleUrl)
await chat.ensureLoaded()

check('default mode is all-off', eq(chat.getMode('sess-A'), ALL_OFF))
check('default prompt is empty', chat.forensicPromptFor('sess-A') === '')

const on = chat.setMode('sess-A', { forensic: true })
await on.persist
check('setMode forensic on', eq(on.mode, mode({ forensic: true })))
const promptOn = chat.forensicPromptFor('sess-A')
check('forensic prompt injected after on',
  promptOn.includes('查法规模式') && promptOn.includes('ks_answer'))
// 注意：第 5 条里本来就会提到「未开启『仅收藏』时…」，所以这里断言的是"第 6 条
// （仅收藏专用规则）不在"，而不是"文本里没有『仅收藏』三个字"。
check('bookmarks-only rule (rule 6) absent while 仅收藏 off',
  !promptOn.includes('bookmarks_only = true') && !promptOn.includes('收藏集内无相关条款'))

const both = chat.setMode('sess-A', { bookmarksOnly: true })
await both.persist
check('bookmarksOnly on (parent already on)', eq(both.mode, mode({ forensic: true, bookmarksOnly: true })))
check('bookmarks rule present after 仅收藏 on',
  chat.forensicPromptFor('sess-A').includes('bookmarks_only = true'))
check('bookmarks rule overrides the "库内无此条款" rule (rule 5 vs 6)',
  chat.forensicPromptFor('sess-A').includes('收藏集内无相关条款'))

check('session isolation', chat.forensicPromptFor('sess-OTHER') === '')

const off = chat.setMode('sess-A', { forensic: false })
await off.persist
check('turning parent off demotes child', eq(off.mode, ALL_OFF),
  JSON.stringify(off.mode))
check('prompt empty after off', chat.forensicPromptFor('sess-A') === '')
check('child cannot be on without parent',
  eq(chat.setMode('sess-C', { bookmarksOnly: true }).mode, ALL_OFF))

/* --- 输入校验（verifier P2：非布尔值以前会被静默当成 false 覆盖掉用户已开的开关） --- */
check('setMode rejects empty session', throws(() => chat.setMode('', { forensic: true })))
check('setMode rejects whitespace-only session', throws(() => chat.setMode('   ', { forensic: true })))
chat.setMode('sess-VALIDATE', { forensic: true })
check('setMode rejects non-boolean flag', throws(() => chat.setMode('sess-VALIDATE', { forensic: 'true' })))
check('non-boolean did NOT clobber the open session',
  chat.getMode('sess-VALIDATE').forensic === true)
check('normalizeSessionId accepts imported-session ids (not only session-*)',
  chat.normalizeSessionId('import-claude-3') === 'import-claude-3')
check('normalizeSessionId rejects an over-long id',
  chat.normalizeSessionId('x'.repeat(200)) === '')

/* --- systemPrompt.section 形状 --- */
const section = chat.makeChatModeSection()
check('section name/order are the documented literals',
  section.name === 'ks:forensic-mode' && section.order === 199,
  `${section.name}@${section.order}`)
chat.setMode('sess-SEC', { forensic: false })
check('section text empty when the session is closed (sec)',
  section.text({ agent: { session: { id: 'sess-SEC' } } }) === '')
chat.setMode('sess-SEC', { forensic: true })
check('section text follows the toggle (sec)',
  section.text({ agent: { session: { id: 'sess-SEC' } } }).includes('查法规模式'))
check('section text empty without agent', section.text({}) === '')
check('section text empty for a session that never toggled',
  section.text({ agent: { session: { id: 'sess-untouched' } } }) === '')

/* --- 收藏夹内提问维度（2026-10 收藏目录） --- */
chat.setMode('sess-FD', { forensic: false })
check('folder state defaults off',
  eq(chat.getMode('sess-FD'), ALL_OFF))
const fdOn = chat.setMode('sess-FD', { folderId: 'bmf_TEST01', folderName: '收藏夹一' })
await fdOn.persist
check('folderId implies forensic (夹范围 ⊃ 取证纪律)',
  eq(fdOn.mode, mode({ forensic: true, folderId: 'bmf_TEST01', folderName: '收藏夹一' })),
  JSON.stringify(fdOn.mode))
const fdPrompt = chat.forensicPromptFor('sess-FD')
check('folder prompt injected with the folder name',
  fdPrompt.includes('收藏夹内提问') && fdPrompt.includes('收藏夹一'))
check('folder prompt overrides rule-5 wording (夹内无 ≠ 库内无)',
  fdPrompt.includes('夹内无相关条款') || fdPrompt.includes('内无相关条款'))
check('bookmarks rule 6 absent while folder rule active without bookmarksOnly',
  !fdPrompt.includes('收藏集内无相关条款'))
check('opening a folder without folderName is rejected',
  throws(() => chat.setMode('sess-FD2', { folderId: 'bmf_X' })))
check('a malformed folderId is rejected (not silently dropped)',
  throws(() => chat.setMode('sess-FD2', { folderId: 'has space', folderName: 'x' })))
check('rejected folderId did NOT clobber the open folder',
  chat.getMode('sess-FD').folderId === 'bmf_TEST01')
// 关闭夹范围：显式 null 只清 folder 维度，不动 forensic（用户可能独立开着查法规模式）
const fdKeep = chat.setMode('sess-FD', { folderId: null })
await fdKeep.persist
check('explicit null closes ONLY the folder dimension',
  eq(fdKeep.mode, mode({ forensic: true })),
  JSON.stringify(fdKeep.mode))
check('folder prompt gone after close',
  !chat.forensicPromptFor('sess-FD').includes('收藏夹内提问'))
const fdOff = chat.setMode('sess-FD', { forensic: false, folderId: null })
await fdOff.persist
check('forensic:false + folderId:null fully off',
  eq(fdOff.mode, ALL_OFF))
// forensic:false 但夹还开着 → normalizeMode 把 forensic 拉回 true（夹范围蕴含取证纪律）
const fdForce = chat.setMode('sess-FD3', { folderId: 'bmf_F3', folderName: '夹三' })
const fdConflict = chat.setMode('sess-FD3', { forensic: false })
check('forensic:false cannot silently kill an open folder scope',
  fdConflict.mode.forensic === true && fdConflict.mode.folderId === 'bmf_F3',
  JSON.stringify(fdConflict.mode))
check('closing forensic:false together with folderId:null turns fully off',
  eq(chat.setMode('sess-FD3', { forensic: false, folderId: null }).mode,
    ALL_OFF))
// 夹范围 + 仅收藏同时开：两个附加段都在（引擎侧两过滤同链执行，提示段以夹为主）
const fd5 = chat.setMode('sess-FD4', { folderId: 'bmf_FD4', folderName: '夹四' })
await fd5.persist
const bothScope = chat.setMode('sess-FD4', { bookmarksOnly: true })
check('bookmarksOnly can stack on an open folder scope',
  bothScope.mode.forensic === true && bothScope.mode.bookmarksOnly === true
    && bothScope.mode.folderId === 'bmf_FD4',
  JSON.stringify(bothScope.mode))
const stackedPrompt = chat.forensicPromptFor('sess-FD4')
check('with folder active the folder section wins the prompt (narrower scope narrated)',
  stackedPrompt.includes('收藏夹内提问') && !stackedPrompt.includes('收藏集内无相关条款'))

/* ================================================ 1b. 参考资料项目绑定（2026-09-17 材料平面）
 *
 * 这一维度的存在理由：`material_project_id` 只能由 host 强制传给 ks_answer（模型自传不可信），
 * 而 host 需要一个**会话级真值**——唯一能可靠设置它的就是用户自己（`/materials use`）。
 * 所以这些断言测的是"用户能不能可靠地把项目绑上/解绑，且错了会报错而不是静默不生效"。
 */
{
  // ⚠ **不要**在这里 __resetChatModeForTests() / 覆盖状态文件：脚本后面的
  // "子会话继承"断言依赖前面段落攒下的父会话状态，中途清空会把它们一起打红
  // （本冒烟第一版就这么错过一次）。用不冲突的新会话 id 即可。
  check('material project defaults to unbound',
    chat.getMode('sess-MAT').materialProjectId === null)

  // 绑定蕴含查法规模式（材料只在 ks_answer 这条链上参与作答）
  const matOn = chat.setMode('sess-MAT', {
    materialProjectId: 'prj_TEST01', materialProjectName: '财报分析',
  })
  await matOn.persist
  check('binding a material project implies forensic (材料只在 ks_answer 链上生效)',
    matOn.mode.forensic === true && matOn.mode.materialProjectId === 'prj_TEST01'
      && matOn.mode.materialProjectName === '财报分析',
    JSON.stringify(matOn.mode))

  // 落盘后回读：绑定必须真的在磁盘上（重启 dsh 不该丢）
  const matState = await readState()
  const matDisk = matState?.modes?.['sess-MAT'] ?? matState?.sessions?.['sess-MAT']
    ?? (Array.isArray(matState?.sessions)
      ? matState.sessions.find((s) => (s.session ?? s.id) === 'sess-MAT') : undefined)
  check('binding is persisted to disk (survives a dsh restart)',
    matDisk !== undefined && matDisk !== null
      && (matDisk.materialProjectId ?? matDisk.mode?.materialProjectId) === 'prj_TEST01',
    JSON.stringify(matDisk ?? null))

  check('opening a material scope without a name is rejected (否则回执会显示上一个项目的名字)',
    throws(() => chat.setMode('sess-MAT2', { materialProjectId: 'prj_X' })))
  check('a malformed materialProjectId is rejected (not silently dropped)',
    throws(() => chat.setMode('sess-MAT2',
      { materialProjectId: 'has space', materialProjectName: 'x' })))
  // **最容易踩的坑**：把收藏夹 id 当项目 id 传。静默"开着但永不生效"是最坏结果
  // （用户会以为材料已经参与作答了），故必须报错且指向正确的 id 来源。
  let prefixErr = null
  try {
    chat.setMode('sess-MAT2', { materialProjectId: 'bmf_FOLDER', materialProjectName: '夹' })
  } catch (e) { prefixErr = e }
  check('a folder id used as a project id is REJECTED with a pointer to the right source',
    prefixErr !== null && String(prefixErr.message).includes('prj_')
      && String(prefixErr.message).includes('bmf_'), String(prefixErr?.message))
  check('rejected materialProjectId did not clobber the bound project',
    chat.getMode('sess-MAT').materialProjectId === 'prj_TEST01')

  // 显式 null 只清该维度（与 folderId 同款语义），不动 forensic
  const matKeep = chat.setMode('sess-MAT', { materialProjectId: null })
  await matKeep.persist
  check('explicit null closes ONLY the material dimension (forensic stays on)',
    eq(matKeep.mode, mode({ forensic: true })), JSON.stringify(matKeep.mode))

  // 两个范围维度**互不干扰**：同时开、单独关（每步都先把两个都开上，
  // 否则"关掉 A 后 B 还在"会因为 A 上一步已经被关而变成假断言）
  const both = chat.setMode('sess-MATB', {
    folderId: 'bmf_B', folderName: '夹B',
    materialProjectId: 'prj_B', materialProjectName: '项目B',
  })
  check('folder + material scopes coexist (independent dimensions)',
    both.mode.folderId === 'bmf_B' && both.mode.materialProjectId === 'prj_B',
    JSON.stringify(both.mode))
  const dropMat = chat.setMode('sess-MATB', { materialProjectId: null })
  check('closing the material scope leaves the folder scope intact',
    dropMat.mode.folderId === 'bmf_B' && dropMat.mode.materialProjectId === null,
    JSON.stringify(dropMat.mode))
  const bothAgain = chat.setMode('sess-MATB', {
    materialProjectId: 'prj_B2', materialProjectName: '项目B2',
  })
  check('re-binding material with the folder open keeps both',
    bothAgain.mode.folderId === 'bmf_B' && bothAgain.mode.materialProjectId === 'prj_B2',
    JSON.stringify(bothAgain.mode))
  const dropFolder = chat.setMode('sess-MATB', { folderId: null })
  check('closing the folder scope leaves the material scope intact',
    dropFolder.mode.folderId === null && dropFolder.mode.materialProjectId === 'prj_B2',
    JSON.stringify(dropFolder.mode))

  // 回执 + 提示段：绑定必须**看得见**（否则用户不知道自己绑了没有）
  chat.setMode('sess-MATS', { materialProjectId: 'prj_S', materialProjectName: '制度库' })
  const matSummary = chat.forensicPromptFor('sess-MATS')
  check('material scope adds its own prompt section (starts 另加一个平面，不是"限定检索")',
    matSummary.includes('【参考资料项目】') && matSummary.includes('制度库'),
    matSummary.slice(-120))
  check('material prompt section teaches the two planes and the marker split',
    matSummary.includes('[[m:i]]') && matSummary.includes('[[c:i]]')
    && matSummary.includes('本任务准则') && matSummary.includes('不得单独支撑结论'))
  check('material prompt section is honest about host-side forcing ≠ material actually used',
    matSummary.includes('不能') && matSummary.includes('material_usage'))
  check('material prompt section says review is a hard gate and the tool cannot approve',
    matSummary.includes('review_status') && matSummary.includes('不能代批'))

  // 材料段与夹段**并存**（材料是"另一个平面"，不是"更小的范围"）
  chat.setMode('sess-MATX', {
    folderId: 'bmf_X', folderName: '夹X',
    materialProjectId: 'prj_X', materialProjectName: '项目X',
  })
  const bothSections = chat.forensicPromptFor('sess-MATX')
  check('folder section and material section coexist (independent semantics)',
    bothSections.includes('【收藏夹内提问】') && bothSections.includes('【参考资料项目】'),
    '两者同开时如实给两段')

  check('unbound session gets NO material section',
    !chat.forensicPromptFor('sess-MATU').includes('【参考资料项目】'))
}

/* --- 子会话继承（verifier P1-7） --- */
const childCtx = (id, parent) => ({ agent: { session: { id, header: { parentSession: parent } } } })
check('child session inherits the parent toggle',
  section.text(childCtx('sess-child', 'sess-SEC')).includes('查法规模式'))
check('inherited prompt is labelled',
  section.text(childCtx('sess-child', 'sess-SEC')).includes('继承自父会话'))
check('child of a closed session does not inherit',
  section.text(childCtx('sess-child', 'sess-nowhere')) === '')
check('a child with no parentSession does not inherit',
  section.text({ agent: { session: { id: 'sess-orphan', header: {} } } }) === '')

const chain = { 'sess-grandchild': 'sess-mid', 'sess-mid': 'sess-SEC' }
const sectionHops = chat.makeChatModeSection({ parentSessionOf: (id) => chain[id] ?? null })
check('multi-hop inheritance via parentSessionOf',
  sectionHops.text(childCtx('sess-grandchild', 'sess-mid')).includes('查法规模式'))
const sectionCycle = chat.makeChatModeSection({ parentSessionOf: (id) => (id === 'sess-loop' ? 'sess-loop' : null) })
check('a self-parenting session does not loop forever (and does not self-inherit)',
  sectionCycle.text(childCtx('sess-loop', 'sess-loop')) === '')
const sectionThrows = chat.makeChatModeSection({ parentSessionOf: () => { throw new Error('no registry') } })
check('a throwing parentSessionOf degrades to no inheritance',
  sectionThrows.text(childCtx('sess-child-throw', 'sess-SEC')) === '')

/* --- effectiveChatMode：提示层与工具层共用的唯一真值（verifier 二轮 P1 的锁） --- */
{
  chat.setMode('eff-parent', { forensic: true, bookmarksOnly: true })
  const resolver = (id) => (id === 'eff-child' ? 'eff-parent' : id === 'eff-grand' ? 'eff-child' : null)
  const own = chat.effectiveChatMode('eff-parent', { parentSessionOf: resolver })
  const child = chat.effectiveChatMode('eff-child', { parentSessionOf: resolver })
  const grand = chat.effectiveChatMode('eff-grand', { parentSessionOf: resolver })
  const stranger = chat.effectiveChatMode('eff-stranger', { parentSessionOf: resolver })
  check('effectiveChatMode: own session → source=session',
    own.forensic === true && own.bookmarksOnly === true && own.source === 'session',
    JSON.stringify(own))
  check('effectiveChatMode: child inherits (source=parent) — the tool layer uses THIS',
    child.forensic === true && child.bookmarksOnly === true && child.source === 'parent',
    JSON.stringify(child))
  check('effectiveChatMode: grandchild inherits too',
    grand.bookmarksOnly === true && grand.source === 'parent', JSON.stringify(grand))
  check('effectiveChatMode: unrelated session stays off',
    stranger.forensic === false && stranger.source === 'none', JSON.stringify(stranger))
  // 用只在**规则 6** 出现的标记判断漂移（"仅收藏"三个字在规则 5 里就有 → 恒真，测不出东西）
  const childPrompt = chat.forensicPromptFor('eff-child', { parentSessionOf: resolver })
  check('effectiveChatMode and forensicPromptFor agree (no prompt/tool drift)',
    childPrompt.includes('收藏集内无相关条款') === (child.bookmarksOnly === true)
    && chat.forensicPromptFor('eff-stranger', { parentSessionOf: resolver }) === '',
    `bookmarksOnly=${child.bookmarksOnly} rule6=${childPrompt.includes('收藏集内无相关条款')}`)
  // 反向：仅收藏**关着**时，提示词里绝不能出现规则 6 的独有标记
  chat.setMode('eff-parent', { forensic: true, bookmarksOnly: false })
  check('rule 6 is absent when 仅收藏 is off (the other direction of the same equality)',
    !chat.forensicPromptFor('eff-child', { parentSessionOf: resolver }).includes('收藏集内无相关条款')
    && chat.effectiveChatMode('eff-child', { parentSessionOf: resolver }).bookmarksOnly === false)
  chat.setMode('eff-parent', { forensic: true, bookmarksOnly: true })
  chat.setMode('eff-parent', { forensic: false })
  check('closing the parent stops the child from inheriting',
    chat.effectiveChatMode('eff-child', { parentSessionOf: resolver }).forensic === false)
}

/* ================================================ 2. host 路由 */
function fakeReq({
  method = 'GET',
  headers = { host: '127.0.0.1:3080', 'content-type': 'application/json' },
  body = '',
  url = '/',
} = {}) {
  const req = new EventEmitter()
  req.method = method
  req.headers = headers
  req.url = url
  req.destroy = () => { req.destroyed = true }
  process.nextTick(() => {
    if (body) req.emit('data', Buffer.from(body, 'utf8'))
    req.emit('end')
  })
  return req
}
function fakeRes() {
  return {
    status: 0,
    headers: null,
    body: null,
    writeHead(status, headers) {
      this.status = status
      this.headers = headers ?? null
    },
    end(text) {
      try { this.body = text ? JSON.parse(text) : null } catch { this.body = text }
    },
  }
}
const routes = new Map()
chat.registerKsChatModeRoutes({
  webServer: { register(route) { routes.set(route.path, route.handler); return () => {} } },
})
const handler = routes.get(chat.KS_CHAT_MODE_PATH)
check('chat-mode route registered', typeof handler === 'function')
const call = async (opts) => {
  const res = fakeRes()
  await handler(fakeReq(opts), res)
  return res
}
const putBody = (obj) => JSON.stringify(obj)

const noSession = await call({ method: 'GET', url: '/ks/chat-mode' })
check('GET without session → 400', noSession.status === 400
  && noSession.body?.error?.code === 'missing_session', `status=${noSession.status}`)
const blankSession = await call({ method: 'GET', url: '/ks/chat-mode?session=%20%20' })
check('GET with a blank session → 400', blankSession.status === 400, `status=${blankSession.status}`)

chat.setMode('sess-ROUTE', { forensic: true, bookmarksOnly: true })
const got = await call({ method: 'GET', url: '/ks/chat-mode?session=sess-ROUTE' })
check('GET returns the open mode',
  got.status === 200 && got.body?.mode?.forensic === true && got.body?.mode?.bookmarksOnly === true,
  JSON.stringify(got.body?.mode))
check('GET echoes the session id (client self-check)', got.body?.session === 'sess-ROUTE',
  String(got.body?.session))
check('GET is Cache-Control: no-store',
  String(got.headers?.['Cache-Control'] ?? '') === 'no-store', String(got.headers?.['Cache-Control']))

const put = await call({
  method: 'PUT',
  body: putBody({ session: 'sess-W', forensic: true, bookmarksOnly: true }),
})
check('PUT writes and normalizes', put.status === 200
  && eq(put.body?.mode, mode({ forensic: true, bookmarksOnly: true })), JSON.stringify(put.body?.mode))
check('PUT reports persisted:true', put.body?.persisted === true)
check('PUT took effect in module state', chat.getMode('sess-W').forensic === true)
check('PUT response is on disk before it returns', (await readState())?.sessions?.['sess-W']?.forensic === true)

const putOff = await call({ method: 'PUT', body: putBody({ session: 'sess-W', forensic: false }) })
check('PUT off clears both', putOff.status === 200
  && eq(putOff.body?.mode, ALL_OFF), JSON.stringify(putOff.body?.mode))

const putFolder = await call({
  method: 'PUT',
  body: putBody({ session: 'sess-WF', folderId: 'bmf_ROUTE1', folderName: '路由夹' }),
})
check('PUT opens a folder scope (implies forensic)', putFolder.status === 200
  && putFolder.body?.mode?.folderId === 'bmf_ROUTE1' && putFolder.body?.mode?.forensic === true,
  JSON.stringify(putFolder.body?.mode))
check('folder scope took effect in module state',
  chat.getMode('sess-WF').folderName === '路由夹')
const putFolderOff = await call({
  method: 'PUT',
  body: putBody({ session: 'sess-WF', folderId: null }),
})
check('PUT folderId:null closes only the folder dimension', putFolderOff.status === 200
  && putFolderOff.body?.mode?.folderId === null && putFolderOff.body?.mode?.forensic === true,
  JSON.stringify(putFolderOff.body?.mode))
chat.setMode('sess-WF', { forensic: false })
const putFolderNoName = await call({
  method: 'PUT',
  body: putBody({ session: 'sess-WF', folderId: 'bmf_NONAME' }),
})
check('PUT folderId without folderName → 400 (host cannot render prompts without it)',
  putFolderNoName.status === 400, `status=${putFolderNoName.status}`)

const badJson = await call({ method: 'PUT', body: '{not json' })
check('PUT malformed JSON → 400', badJson.status === 400
  && badJson.body?.error?.code === 'bad_request', `status=${badJson.status}`)
const putNoSession = await call({ method: 'PUT', body: putBody({ forensic: true }) })
check('PUT without session → 400', putNoSession.status === 400, `status=${putNoSession.status}`)
const putBadType = await call({ method: 'PUT', body: putBody({ session: 'sess-ROUTE', forensic: 'true' }) })
check('PUT non-boolean flag → 400 (not a silent overwrite)',
  putBadType.status === 400 && putBadType.body?.error?.code === 'bad_request', `status=${putBadType.status}`)
check('the rejected non-boolean PUT did not change state',
  chat.getMode('sess-ROUTE').forensic === true)
const putBadId = await call({ method: 'PUT', body: putBody({ session: 'has space', forensic: true }) })
check('PUT malformed session id → 400', putBadId.status === 400, `status=${putBadId.status}`)
const putNoCt = await call({
  method: 'PUT', headers: { host: '127.0.0.1:3080' },
  body: putBody({ session: 'sess-ROUTE', forensic: true }),
})
check('PUT without application/json → 415', putNoCt.status === 415, `status=${putNoCt.status}`)
const hugeReq = fakeReq({ method: 'PUT', body: putBody({ session: 'sess-ROUTE', pad: 'x'.repeat(8_000) }) })
const hugeRes = fakeRes()
await handler(hugeReq, hugeRes)
check('PUT oversized body → 413 (not 400, and no socket destroy)',
  hugeRes.status === 413 && hugeRes.body?.error?.code === 'body_too_large', `status=${hugeRes.status}`)
check('oversized-body path did not destroy the socket',
  hugeReq.destroyed !== true, String(hugeReq.destroyed))
const del = await call({ method: 'DELETE' })
check('other methods → 405', del.status === 405, `status=${del.status}`)

/* ================================================ 3. 多进程与落盘安全 */
// 3a. 合并落盘：磁盘上是"另一个 dsh 进程"写的会话，本进程只动 sess-MINE
await writeFile(statePath, JSON.stringify({
  sessions: { 'sess-OTHER-PROC': { forensic: true, bookmarksOnly: false } },
}, null, 2), 'utf8')
await chat.setMode('sess-MINE', { forensic: true }).persist
const mergedState = await readState()
check('merge keeps the other process\'s sessions',
  mergedState?.sessions?.['sess-OTHER-PROC']?.forensic === true,
  JSON.stringify(Object.keys(mergedState?.sessions ?? {})))
check('merge keeps this process\'s sessions',
  mergedState?.sessions?.['sess-MINE']?.forensic === true)

// 3b. 本进程关掉的会话不会被磁盘旧值"复活"；**已释放所有权**的会话也不会被后续写入复活
//     （verifier 三轮：原用例测的是同进程关闭，即使删掉 `_touched` 释放逻辑也照样通过，
//      所以它没覆盖"跨进程被关掉后被本进程旧内存复活"这个真实缺陷）
{
  await chat.setMode('sess-RELEASE', { forensic: true }).persist
  await chat.setMode('sess-RELEASE', { forensic: false }).persist // 关掉并释放所有权
  await chat.setMode('sess-RELEASE', { forensic: true }).persist  // 再开一次（此刻拥有所有权）
  // 模拟"另一个 dsh 进程把它关了"：磁盘上不再有它
  const before = await readState()
  const stripped = { sessions: { ...(before?.sessions ?? {}) } }
  delete stripped.sessions['sess-RELEASE']
  await writeFile(statePath, JSON.stringify(stripped, null, 2), 'utf8')
  // 本进程写**别的**会话（不该把 sess-RELEASE 用旧内存复活）
  await chat.setMode('sess-OTHER-WRITE', { forensic: true }).persist
  const afterOtherWrite = await readState()
  check('a session closed elsewhere is not resurrected by an ownership-free write',
    afterOtherWrite?.sessions?.['sess-RELEASE'] === undefined,
    JSON.stringify(Object.keys(afterOtherWrite?.sessions ?? {})))
  // 但"本进程刚关掉的会话"在同一轮合并里必须仍然被删掉（所有权语义的另一面）
  await writeFile(statePath, JSON.stringify({
    sessions: { ...(afterOtherWrite?.sessions ?? {}), 'sess-GONE': { forensic: true, bookmarksOnly: false } },
  }, null, 2), 'utf8')
  chat.setMode('sess-GONE', { forensic: true })
  await chat.setMode('sess-GONE', { forensic: false }).persist
  const afterDelete = await readState()
  check('a session closed by this process is not resurrected from disk',
    afterDelete?.sessions?.['sess-GONE'] === undefined,
    JSON.stringify(Object.keys(afterDelete?.sessions ?? {})))
}

// 3c. 原子写：不留 .tmp 残骸
const leftovers = (await readdir(dataDir)).filter((n) => n.endsWith('.tmp'))
check('atomic write leaves no .tmp file', leftovers.length === 0, leftovers.join(','))

// 3d. 坏文件：备份为 .corrupt-*、按空处理、之后仍能正常写（可恢复）
await writeFile(statePath, '{ this is not json', 'utf8')
chat.__resetChatModeForTests()
await chat.ensureLoaded()
check('corrupt state file is reported as degraded',
  chat.stateStatus().degraded === 'corrupt_state_file', String(chat.stateStatus().degraded))
check('corrupt state file is backed up',
  (await readdir(dataDir)).some((n) => n.includes('.corrupt-')),
  (await readdir(dataDir)).join(','))
const afterCorrupt = await chat.setMode('sess-AFTER-CORRUPT', { forensic: true }).persist
check('writes still work after a corrupt file (recovery path)',
  afterCorrupt.persisted === true
  && (await readState())?.sessions?.['sess-AFTER-CORRUPT']?.forensic === true,
  JSON.stringify(afterCorrupt))

// 3e. 读失败（非 ENOENT）：degraded + 拒绝写盘（绝不用空快照覆盖磁盘上的好数据）
const goodState = await readFile(statePath, 'utf8')
{
  await rm(statePath, { force: true })
  await mkdir(statePath) // 用目录冒充文件 → 读错误（EISDIR），且"磁盘上的好数据"仍在别处
  try {
    chat.__resetChatModeForTests()
    await chat.ensureLoaded()
    const status = chat.stateStatus()
    const persist = await chat.setMode('sess-BLOCKED', { forensic: true }).persist
    check('read failure (non-ENOENT) is reported as degraded',
      typeof status.degraded === 'string' && status.degraded.startsWith('read_failed'),
      String(status.degraded))
    check('read failure blocks writes (no empty-snapshot overwrite)',
      persist.persisted === false && chat.stateStatus().writes_blocked === true,
      JSON.stringify(persist))
    check('the in-memory toggle still works while degraded',
      chat.getMode('sess-BLOCKED').forensic === true)
  } finally {
    await rm(statePath, { recursive: true, force: true })
    await writeFile(statePath, goodState, 'utf8')
  }
}
check('the pre-existing good state was left byte-identical', (await readFile(statePath, 'utf8')) === goodState)

// 3g. 多进程并发落盘（verifier 二轮实测的失败场景）：两个进程各写 N 个会话到同一份
//     状态文件。**核心不变量**：任何一次报 persisted:true 的写入都必须真的在盘上
//     （旧实现里 A 侧 54 次报成功、磁盘上 A 的会话 0/60）。
{
  const N = 12
  const childProgram = (prefix) => `import(${JSON.stringify(chatModuleUrl)}).then(async (m) => {`
    + '  await m.ensureLoaded();'
    + `  const prefix = ${JSON.stringify(prefix)};`
    + `  const out = [];`
    + `  for (let i = 0; i < ${N}; i += 1) {`
    + '    const r = m.setMode(prefix + i, { forensic: true });'
    + '    const res = await r.persist;'
    + '    out.push([prefix + i, res.persisted === true]);'
    + '  }'
    + "  process.stdout.write('RESULT:' + JSON.stringify(out))"
    + ' })'
  const spawnWriter = (prefix) => run(process.execPath, ['-e', childProgram(prefix)], {
    env: { ...process.env, KS_CHATMODE_DIR: dataDir },
    cwd: pluginRoot,
    maxBuffer: 4 * 1024 * 1024,
  })
  await writeFile(statePath, JSON.stringify({ sessions: {} }, null, 2), 'utf8')
  const [a, b] = await Promise.all([spawnWriter('mp-a-'), spawnWriter('mp-b-')])
  const parseClaims = (stdout) => {
    const at = stdout.indexOf('RESULT:')
    return at < 0 ? [] : JSON.parse(stdout.slice(at + 'RESULT:'.length))
  }
  const claims = [...parseClaims(a.stdout), ...parseClaims(b.stdout)]
  const finalState = (await readState())?.sessions ?? {}
  const claimedDurable = claims.filter(([, ok]) => ok).map(([sid]) => sid)
  const broken = claimedDurable.filter((sid) => finalState[sid]?.forensic !== true)
  check('two concurrent writers: every write reported persisted:true is really on disk',
    claims.length === N * 2 && broken.length === 0,
    `claims=${claims.length} durable=${claimedDurable.length} missing=${broken.length}`)
  check('two concurrent writers: no writer lost its whole batch',
    claimedDurable.length === N * 2,
    `durable=${claimedDurable.length}/${N * 2}`)
  check('two concurrent writers: the merged file holds both sets',
    Object.keys(finalState).filter((k) => k.startsWith('mp-a-')).length === N
    && Object.keys(finalState).filter((k) => k.startsWith('mp-b-')).length === N,
    `a=${Object.keys(finalState).filter((k) => k.startsWith('mp-a-')).length}`
    + ` b=${Object.keys(finalState).filter((k) => k.startsWith('mp-b-')).length}`)
  check('two concurrent writers: no .tmp/.steal litter left behind',
    (await readdir(dataDir)).filter((n) => n.endsWith('.tmp') || n.includes('.steal-')).length === 0,
    (await readdir(dataDir)).join(','))
  check('two concurrent writers: the write lock is released (no .lock litter)',
    (await readdir(dataDir)).filter((n) => n.endsWith('.lock')).length === 0,
    (await readdir(dataDir)).join(','))
}

// 3f-2. verifier 五轮 P2-2：磁盘**损坏**时 reload 也不得清空内存态（与"读失败不动内存"同一原则）
{
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({
    sessions: { 'A-from-clean-disk': { forensic: true, bookmarksOnly: false } },
  }, null, 2), 'utf8')
  await chat.ensureLoaded()
  check('clean load: the on-disk toggle is in memory and ownership released',
    chat.getMode('A-from-clean-disk').forensic === true)
  // 先制造一次真实读错误（状态路径变成目录）→ 才可能走到"允许重载"，这是生产里的唯一路径
  await rm(statePath, { force: true })
  await mkdir(statePath)
  const duringOutage = await chat.setMode('B-outage-2', { forensic: true }).persist
  check('the outage really degraded the reader', duringOutage.persisted === false
    && chat.stateStatus().writes_blocked === true)
  // 趁降级把磁盘换成**损坏内容**，再允许重载 → ensureLoaded 走损坏分支
  const namesBeforeCorrupt = new Set(await readdir(dataDir))
  // 残骸清理必须由**损坏这条加载路径本身**触发（round-6 P2-1：提前 return 会让它整个进程
  // 生命周期一次都不跑）。放一个 mtime 25h 前的自有残骸 + 一个新鲜的，走完损坏加载后断言：
  // 旧的被清、新（<24h）的留下。注意不能直接调 __sweepArtifactsForTests —— 那测的是函数
  // 本身，不是这条路径。
  const { utimes } = await import('node:fs/promises')
  const staleArtifact = join(dataDir, 'ks-chatmode.json.999999.1.tmp')
  const freshArtifact = join(dataDir, 'ks-chatmode.json.999999.2.tmp')
  await writeFile(staleArtifact, 'stale', 'utf8')
  await writeFile(freshArtifact, 'fresh', 'utf8')
  const longAgo = new Date(Date.now() - 25 * 60 * 60 * 1000)
  await utimes(staleArtifact, longAgo, longAgo)
  await rm(statePath, { recursive: true, force: true })
  await writeFile(statePath, '{ broken json', 'utf8')
  chat.allowStateReload()
  await chat.ensureLoaded()
  check('a CORRUPT reload does not wipe the in-memory toggles (round-5 P2-2)',
    chat.getMode('A-from-clean-disk').forensic === true,
    JSON.stringify(chat.getMode('A-from-clean-disk')))
  // 备份断言必须看**新增**的名字：只看"目录里有没有 .corrupt-"是空转（更早的用例已经留下过）
  const newBackups = (await readdir(dataDir))
    .filter((n) => n.includes('.corrupt-') && !namesBeforeCorrupt.has(n))
  check('a corrupt reload creates exactly one NEW backup of the damaged file',
    newBackups.length === 1, newBackups.join(',') || '(none)')
  await new Promise((resolve) => { setTimeout(resolve, 80) }) // sweep 是 fire-and-forget
  const namesNow = await readdir(dataDir)
  check('the corrupt load path reaches the artifact sweep (round-6 P2-1)',
    !namesNow.includes('ks-chatmode.json.999999.1.tmp'), namesNow.join(','))
  check('the sweep respects the 24h threshold (keeps fresh artifacts)',
    namesNow.includes('ks-chatmode.json.999999.2.tmp'), namesNow.join(','))
  await rm(freshArtifact, { force: true })
  // 关键：磁盘上现在**没有**状态文件（损坏那份已被改名移走）。写一个无关会话后，
  // 内存里仍开着的 A 必须被**物化回磁盘**（verifier 六轮 P2-2：否则用户看到开着、重启变关）。
  await chat.setMode('C-after-corrupt', { forensic: true }).persist
  const afterCorruptReload = (await readState())?.sessions ?? {}
  check('a memory-only toggle from the corrupt window is re-materialised on disk',
    afterCorruptReload['A-from-clean-disk']?.forensic === true
    && afterCorruptReload['C-after-corrupt']?.forensic === true,
    Object.keys(afterCorruptReload).join(','))
}

// 3f-3. verifier 五轮 P2-1：**写**失败型降级也必须进 degraded（否则前端显示"已保存"）
{
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({ sessions: {} }, null, 2), 'utf8')
  await chat.ensureLoaded()
  // 把状态文件换成一个"无法写入"的位置：父路径是文件 → rename/write 必失败
  const blockedDir = join(dataDir, 'blocked-parent')
  await writeFile(blockedDir, 'not a directory', 'utf8')
  const savedDir = process.env.KS_CHATMODE_DIR
  process.env.KS_CHATMODE_DIR = join(blockedDir, 'nested')
  try {
    const failed = await chat.setMode('D-write-fail', { forensic: true }).persist
    const status = chat.stateStatus()
    check('a WRITE failure is reported as degraded, not just persisted:false',
      failed.persisted === false && typeof status.degraded === 'string'
      && status.degraded.startsWith('persist_failed'), JSON.stringify({ failed, status }))
    check('a write failure does NOT set writes_blocked (no self-lock)',
      status.writes_blocked === false)
    check('the in-memory toggle still works while writes fail',
      chat.getMode('D-write-fail').forensic === true)
  } finally {
    process.env.KS_CHATMODE_DIR = savedDir
    await rm(blockedDir, { force: true })
  }
  // 换回可写位置后，一次成功落盘必须把 degraded 清掉（它是"最近一次"状态，不是永久污点）
  const recovered2 = await chat.setMode('D-write-fail', { forensic: true }).persist
  check('a successful persist clears the degraded marker',
    recovered2.persisted === true && chat.stateStatus().degraded === null,
    JSON.stringify(chat.stateStatus()))
}

// 3g-2. 锁的两种边界
{
  // 3e 的读失败把本进程置成 degraded（拒绝写盘）；这里显式恢复——生产路径上这一步
  // 由 PUT 路由的 allowStateReload() 做，冒烟里没有路由调用，所以自己来。
  chat.allowStateReload()
  await chat.ensureLoaded()
  const { utimes } = await import('node:fs/promises')
  const lockPath = `${statePath}.lock`
  // (a) 陈旧锁（mtime 20 秒前）→ 必须被抢走，写入照常成功
  await writeFile(lockPath, '999999\n', 'utf8')
  const old = new Date(Date.now() - 20_000)
  await utimes(lockPath, old, old)
  const stolen = await chat.setMode('stale-lock-session', { forensic: true }).persist
  check('a stale lock (crashed holder) is stolen, not a permanent deadlock',
    stolen.persisted === true
    && (await readState())?.sessions?.['stale-lock-session']?.forensic === true,
    JSON.stringify(stolen))
  check('the stolen lock is cleaned up', !(await readdir(dataDir)).some((n) => n.endsWith('.lock')))
  // (b) 活跃锁占着 → 写入必须**等**它，而不是无视锁直接写；锁一释放就完成。
  //     （长时间占着不放的锁最终会因 mtime 变旧被判为"持有者已崩溃"而被抢走——
  //      这是刻意的自愈，所以这里测的是"等的语义"，不是"永远失败"。）
  await writeFile(lockPath, '888888\n', 'utf8')
  let settled = null
  const pending = chat.setMode('lock-wait-session', { forensic: true }).persist
    .then((res) => { settled = res; return res })
  await new Promise((resolve) => { setTimeout(resolve, 1_000) })
  const stillWaiting = settled === null
  await rm(lockPath, { force: true })
  const waited = await pending
  check('a live lock is respected: the write waits, then proceeds once it is free',
    stillWaiting && waited.persisted === true
    && (await readState())?.sessions?.['lock-wait-session']?.forensic === true,
    `waitedWithoutLock=${stillWaiting} result=${JSON.stringify(waited)}`)
}

// 3h. 合并路径也必须遵守"读失败不照写 + 损坏要备份"（verifier 二轮 P2）
{
  // 先让本进程正常加载一次（模拟"进程已经跑起来了"）
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({ sessions: { 'keep-me': { forensic: true, bookmarksOnly: false } } }, null, 2), 'utf8')
  await chat.ensureLoaded()
  // 磁盘随后损坏 → 下一次落盘必须备份而不是静默覆盖
  const corrupted = '{ not json at all'
  await writeFile(statePath, corrupted, 'utf8')
  const round = await chat.setMode('merge-after-corrupt', { forensic: true }).persist
  const backups = (await readdir(dataDir)).filter((n) => n.includes('.corrupt-'))
  check('a corrupt file discovered during the merge step is backed up, not silently clobbered',
    backups.length >= 1 && round.persisted === true, `backups=${backups.length} ${JSON.stringify(round)}`)
  check('the corrupt bytes are preserved in the backup',
    (await Promise.all(backups.map((n) => readFile(join(dataDir, n), 'utf8'))))
      .some((text) => text === corrupted))
  check('after the corrupt-merge the new write landed',
    (await readState())?.sessions?.['merge-after-corrupt']?.forensic === true)
}

// 3i. 降级可恢复（verifier 二轮 P2：旧实现 _writesBlocked 永久、只能重启 dsh）
{
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({ sessions: { 'pre-degrade': { forensic: true, bookmarksOnly: false } } }, null, 2), 'utf8')
  const saved = await readFile(statePath, 'utf8')
  await rm(statePath, { force: true })
  await mkdir(statePath)
  let blocked = null
  try {
    await chat.ensureLoaded()
    blocked = await chat.setMode('degraded-1', { forensic: true }).persist
  } finally {
    await rm(statePath, { recursive: true, force: true })
    await writeFile(statePath, saved, 'utf8')
  }
  check('a read failure refuses the write (nothing was clobbered)',
    blocked?.persisted === false && chat.stateStatus().writes_blocked === true,
    JSON.stringify(blocked))
  // 磁盘修好后：一次 allowStateReload（PUT 路由每轮都做）就应该恢复可写
  check('degradation is recoverable (allowStateReload resets the block)',
    chat.allowStateReload() === true)
  // verifier 三轮 P2：allowStateReload **不得**丢掉降级期间用户已开、且已被告知
  // "仅内存生效"的开关（旧实现清空 _modes → 提示层与工具层一起悄悄变回关闭）
  check('allowStateReload keeps the in-memory toggles (no silent fail-open)',
    chat.getMode('degraded-1').forensic === true,
    JSON.stringify(chat.getMode('degraded-1')))
  await chat.ensureLoaded()
  check('the toggle survives the reload merge',
    chat.getMode('degraded-1').forensic === true)
  const recovered = await chat.setMode('recovered-1', { forensic: true }).persist
  check('writes work again after recovery', recovered.persisted === true
    && (await readState())?.sessions?.['recovered-1']?.forensic === true,
    JSON.stringify(recovered))
  check('the pre-degrade state survived the whole episode',
    (await readState())?.sessions?.['pre-degrade']?.forensic === true)
}

// 3i-2. verifier 四轮 P1-B：降级期开的开关，遇到**再次失败的** reload，绝不能因此
//       被清出内存（会连带让下一次成功落盘把它当成"用户关掉了"从磁盘删掉）。
{
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({
    sessions: { 'A-on-disk': { forensic: true, bookmarksOnly: false } },
  }, null, 2), 'utf8')
  await chat.ensureLoaded()
  let onDiskBefore = await readFile(statePath, 'utf8')
  await rm(statePath, { force: true })
  await mkdir(statePath)
  let outage = null
  try {
    outage = await chat.setMode('B-during-outage', { forensic: true, bookmarksOnly: true }).persist
  } finally {
    await rm(statePath, { recursive: true, force: true })
    await writeFile(statePath, onDiskBefore, 'utf8')
  }
  check('outage: the toggle is refused but kept in memory',
    outage?.persisted === false && chat.getMode('B-during-outage').forensic === true,
    JSON.stringify(outage))
  // 再来一次**失败**的 reload（把磁盘重新变回读不到），模拟"用户又点了一下"
  await rm(statePath, { force: true })
  await mkdir(statePath)
  chat.allowStateReload()
  await chat.ensureLoaded() // 读失败 → 不得清空内存态
  check('a FAILED reload does not wipe the in-memory toggles (round-4 P1-B)',
    chat.getMode('B-during-outage').forensic === true
    && chat.getMode('A-on-disk').forensic === true,
    JSON.stringify({ B: chat.getMode('B-during-outage'), A: chat.getMode('A-on-disk') }))
  // 磁盘恢复 → 写**无关**会话：读失败的会话不得被当成"用户关掉了"而从磁盘删除
  await rm(statePath, { recursive: true, force: true })
  await writeFile(statePath, onDiskBefore, 'utf8')
  chat.allowStateReload()
  await chat.ensureLoaded()
  const unrelated = await chat.setMode('C-unrelated', { forensic: true }).persist
  const after = (await readState())?.sessions ?? {}
  check('a failed reload cannot turn memory-loss into a disk DELETE',
    unrelated.persisted === true && after['A-on-disk']?.forensic === true,
    `${JSON.stringify(unrelated)} keys=${Object.keys(after).join(',')}`)
  check('the outage-time toggle ends up on disk once the disk recovers',
    after['B-during-outage']?.forensic === true, Object.keys(after).join(','))
}

/* ================================================ 3f. 条目上限
 * （放在多进程/锁用例之后：它会把状态填满，先跑会让后面的块撞上限）
 */
await writeFile(statePath, JSON.stringify({ sessions: {} }, null, 2), 'utf8')
chat.__resetChatModeForTests()
await chat.ensureLoaded()
for (let i = 0; i < chat.MAX_SESSIONS - 1; i += 1) chat.setMode(`sess-cap-${i}`, { forensic: true })
check('sessions fill up to one below the cap', chat.stateStatus().sessions === chat.MAX_SESSIONS - 1,
  `sessions=${chat.stateStatus().sessions}`)
check('the last slot is still usable', !throws(() => chat.setMode('sess-cap-last', { forensic: true })))
check('session count is capped (refuses to grow unbounded)',
  throws(() => chat.setMode('sess-cap-overflow', { forensic: true })),
  `MAX_SESSIONS=${chat.MAX_SESSIONS}`)
check('a capped-out session can still be turned OFF (no lock-in)',
  eq(chat.setMode('sess-cap-0', { forensic: false }).mode, ALL_OFF))
check('turning one off frees a slot',
  !throws(() => chat.setMode('sess-cap-overflow', { forensic: true })))

/* ================================================ 4. 重启后仍生效（P0-1 复现） */
{
  // 上限用例把状态填满了，先腾出位置（cap-0 已在上一段关掉，这里关 cap-1）
  chat.setMode('sess-cap-1', { forensic: false })
  await chat.setMode('sess-RESTART', { forensic: true }).persist
  // 模拟重启：清掉进程内存态（磁盘状态保持不动）
  chat.__resetChatModeForTests()
  await chat.ensureLoaded()
  check('after a restart the persisted session is loaded in-process',
    chat.forensicPromptFor('sess-RESTART').includes('查法规模式'))
  // 真·另一个进程：不经过任何 client GET，直接看提示段
  chat.__resetChatModeForTests()
  const probe = `import(${JSON.stringify(chatModuleUrl)}).then(async (m) => {`
    + '  await m.ensureLoaded();'
    + "  const on = m.forensicPromptFor('sess-RESTART');"
    + "  const off = m.forensicPromptFor('sess-never-toggled');"
    + "  process.stdout.write((on.includes('查法规模式') && off === '') ? 'RESTART_OK' : 'RESTART_BAD:' + on.length + '/' + off.length)"
    + ' })'
  const { stdout } = await run(process.execPath, ['-e', probe], {
    env: { ...process.env, KS_CHATMODE_DIR: dataDir },
    cwd: pluginRoot,
  })
  check('a fresh process sees the persisted toggle with no client GET',
    stdout.includes('RESTART_OK'), stdout.trim().slice(0, 140))
}

/* ================================================ 5. 斜杠命令（2026-09-10 新增）
 * 用户反馈：输入框上方的按钮太丑 → 删掉 dock，改成 / 调用。命令走 host 的
 * `ctx.commands`（不进模型、不产生对话消息），状态与提示段/工具层共用同一份真值。
 */
{
  chat.__resetChatModeForTests()
  await writeFile(statePath, JSON.stringify({ sessions: {} }, null, 2), 'utf8')
  await chat.ensureLoaded()

  const commands = chat.makeChatModeCommands()
  // 命令条数**跟着声明走**（而不是写死 2）：新增一条命令时这里不该变红，
  // 该红的是"新命令自己那组断言"。故断言的是"声明的每条都在、且命名合法"。
  const expectedNames = [chat.FORENSIC_COMMAND, chat.BOOKMARKS_COMMAND, chat.MATERIALS_COMMAND]
  check('slash commands are declared (lowercase ASCII per DSH contract)',
    commands.length === expectedNames.length
    && commands.map((c) => c.name).join(',') === expectedNames.join(',')
    && commands.every((c) => /^[a-z][a-z0-9_-]*$/.test(c.name)),
    commands.map((c) => '/' + c.name).join(', '))
  check('both commands carry a description + input hint (discoverable in the / panel)',
    commands.every((c) => typeof c.description === 'string' && c.description.length > 8
      && typeof c.input?.hint === 'string' && c.input.hint.length > 0))

  const inv = (raw, sid) => ({ agent: { session: { id: sid, header: {} } }, rawInput: raw })
  const forensic = commands[0]
  const bookmarks = commands[1]

  const on = await forensic.handler(inv('', 'cmd-1'))
  check('/forensic toggles ON for the calling session',
    on.kind === 'success' && chat.getMode('cmd-1').forensic === true
    && on.text.includes('已开启'), on.text)
  const off = await forensic.handler(inv('off', 'cmd-1'))
  check('/forensic off turns it off', off.kind === 'success'
    && chat.getMode('cmd-1').forensic === false && off.text.includes('已关闭'), off.text)
  const toggleAgain = await forensic.handler(inv('', 'cmd-1'))
  check('/forensic with no argument toggles back ON', toggleAgain.kind === 'success'
    && chat.getMode('cmd-1').forensic === true)

  // 中文也认（用户是中文用户；命令名受 DSH 契约限制，但参数可以宽松）
  const offCn = await forensic.handler(inv('关闭', 'cmd-1'))
  check('/forensic accepts a Chinese argument (关闭/开启)',
    offCn.kind === 'success' && chat.getMode('cmd-1').forensic === false, offCn.text)

  const statusOff = await forensic.handler(inv('status', 'cmd-1'))
  check('/forensic status reports the current state without changing it',
    statusOff.kind === 'success' && statusOff.text.includes('已关闭')
    && chat.getMode('cmd-1').forensic === false, statusOff.text)

  const bm = await bookmarks.handler(inv('', 'cmd-2'))
  check('/bookmarks turns on 仅收藏 AND its parent (with an explanation)',
    bm.kind === 'success' && chat.getMode('cmd-2').forensic === true
    && chat.getMode('cmd-2').bookmarksOnly === true
    && bm.text.includes('已同时开启查法规模式'), bm.text)
  const bmOff = await bookmarks.handler(inv('off', 'cmd-2'))
  check('/bookmarks off clears only the child flag',
    bmOff.kind === 'success' && chat.getMode('cmd-2').bookmarksOnly === false
    && chat.getMode('cmd-2').forensic === true, bmOff.text)

  // 命令 → 状态 → 提示段 是同一条链（命令只改状态，提示段照旧实时求值）
  await bookmarks.handler(inv('on', 'cmd-2'))
  check('the prompt section reflects the command-driven state',
    chat.forensicPromptFor('cmd-2').includes('收藏集内无相关条款')
    && chat.forensicPromptFor('cmd-3') === '')

  const badArg = await forensic.handler(inv('maybe', 'cmd-3'))
  check('an unknown argument is rejected with usage (no silent no-op)',
    badArg.kind === 'error' && badArg.text.includes('用法'), JSON.stringify(badArg))
  const noAgent = await forensic.handler({ rawInput: '' })
  check('a command without an agent fails loudly instead of guessing a session',
    noAgent.kind === 'error', JSON.stringify(noAgent))

  // 命令的落盘结果要如实回执（写失败时明确告知"重启会丢"，而不是假装成功）
  {
    const blockedDir = join(dataDir, 'cmd-blocked-parent')
    await writeFile(blockedDir, 'not a directory', 'utf8')
    const savedDir = process.env.KS_CHATMODE_DIR
    process.env.KS_CHATMODE_DIR = join(blockedDir, 'nested')
    try {
      const failedCmd = await forensic.handler(inv('on', 'cmd-4'))
      check('/forensic reports a failed persist honestly (mode still active in memory)',
        failedCmd.kind === 'success' && failedCmd.text.includes('未能落盘')
        && chat.getMode('cmd-4').forensic === true, failedCmd.text)
    } finally {
      process.env.KS_CHATMODE_DIR = savedDir
      await rm(blockedDir, { force: true })
    }
  }

  // 注册面：每个声明的命令都要真的进命令表，且 disposer 可撤销
  {
    const registered = []
    const disposers = chat.registerKsChatModeCommands({
      commands: { register(def) { registered.push(def); return () => {} } },
    })
    check('registerKsChatModeCommands registers every declared command into the host table',
      registered.length === expectedNames.length && typeof disposers[0] === 'function',
      registered.map((d) => d.name).join(','))
    check('the client half no longer touches the input dock (dock UI was deleted)',
      !(await readFile(join(pluginRoot, 'client', 'entry.ts'), 'utf8')).includes('registerKsChatModeDock'))
  }

  /* ---- /materials：用户绑定参考资料项目（2026-09-17 材料平面） ---- */
  {
    const materials = commands.find((c) => c.name === chat.MATERIALS_COMMAND)
    check('/materials is registered with a discoverable description',
      materials !== undefined && materials.description.includes('参考资料')
      && materials.input.hint.includes('prj_id'), JSON.stringify(materials?.input ?? null))

    // 未绑定时看状态：必须明说"不会使用任何项目材料"
    const before = await materials.handler(inv('', 'cmd-mat'))
    check('/materials (no args) reports unbound honestly',
      before.kind === 'success' && before.text.includes('未绑定')
      && before.text.includes('不会使用任何项目材料'), before.text)

    // 绑定
    const bound = await materials.handler(inv('use prj_CMD 测试项目', 'cmd-mat'))
    check('/materials use <prj_id> <name> binds the session',
      bound.kind === 'success' && chat.getMode('cmd-mat').materialProjectId === 'prj_CMD'
      && chat.getMode('cmd-mat').materialProjectName === '测试项目', bound.text)
    check('binding via command implies forensic (so ks_answer is the path used)',
      chat.getMode('cmd-mat').forensic === true)

    // 状态回显名字
    const status = await materials.handler(inv('status', 'cmd-mat'))
    check('/materials status echoes the bound project name',
      status.kind === 'success' && status.text.includes('测试项目')
      && status.text.includes('prj_CMD'), status.text)

    // 换项目时若不改名字，回执不能显示上一个项目的名字（prefix 校验的同族问题）
    const rebound = await materials.handler(inv('use prj_CMD2', 'cmd-mat'))
    check('/materials use without a name falls back to the id (not the stale name)',
      rebound.kind === 'success' && chat.getMode('cmd-mat').materialProjectName === 'prj_CMD2',
      rebound.text)

    // **最容易踩的坑**：拿收藏夹 id 当项目 id → 必须是 error 且指向正确来源
    const wrongKind = await materials.handler(inv('use bmf_FOLDER', 'cmd-mat'))
    check('/materials rejects a folder id with an actionable message',
      wrongKind.kind === 'error' && wrongKind.text.includes('prj_')
      && wrongKind.text.includes('bmf_'), wrongKind.text)

    // 解绑：只清该维度
    const off = await materials.handler(inv('off', 'cmd-mat'))
    check('/materials off unbinds (and does not silently keep the old binding)',
      off.kind === 'success' && chat.getMode('cmd-mat').materialProjectId === null, off.text)

    // 参数缺失/无法识别 → 明确报错（不静默什么都不做）
    const noId = await materials.handler(inv('use', 'cmd-mat'))
    check('/materials use without an id is an error with usage',
      noId.kind === 'error' && noId.text.includes('用法'), noId.text)
    const unknown = await materials.handler(inv('approve mat_1', 'cmd-mat'))
    check('/materials cannot approve/reject — 评审是用户的判断，不是命令',
      unknown.kind === 'error' && unknown.text.includes('无法识别'), unknown.text)

    // 会话 id 缺失时的兜底（与其它命令同款）
    const noSession = await materials.handler({ rawInput: 'status' })
    check('/materials without a resolvable session fails loudly',
      noSession.kind === 'error' && noSession.text.includes('会话'), noSession.text)
  }
}
/* --- 落盘隔离自检（比的是 chatModeFilePath() 的真值，不是局部常量） --- */
check('state path follows $KS_CHATMODE_DIR (the isolation mechanism itself works)',
  chat.chatModeFilePath() === statePath, chat.chatModeFilePath())
check('without $KS_CHATMODE_DIR the default path is the real %APPDATA%\\KnowledgeStation',
  (() => {
    const saved = process.env.KS_CHATMODE_DIR
    delete process.env.KS_CHATMODE_DIR
    const fallback = chat.chatModeFilePath()
    process.env.KS_CHATMODE_DIR = saved
    return fallback.endsWith(join('KnowledgeStation', 'ks-chatmode.json'))
      && !fallback.startsWith(dataDir)
  })(), chat.chatModeFilePath())

const failedChecks = results.filter((r) => !r.ok)
await rm(dataDir, { recursive: true, force: true })
console.log(`\n== chatmode smoke ${failedChecks.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failedChecks.length}/${results.length}) ==`)
process.exit(failedChecks.length === 0 ? 0 : 1)