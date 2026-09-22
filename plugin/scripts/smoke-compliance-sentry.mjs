/**
 * ks-dsh-plugin — scripts/smoke-compliance-sentry.mjs
 *
 * 合规护航三件套 C1 判据（2026-09-22，省 token 硬约束）。六条全有牙：
 *   ① 哨句**字面全库只此一处**（plugin/src + plugin/client 扫字面，唯一常量所有者）；
 *   ② 预判据三组用例：词族命中 / 全不命中 / 标准号模式（GB/T、DB11/T、T/CECS 形）；
 *   ③ 未触发 ⇒ 段文**逐字等于哨句**（零增量）；触发 ⇒ 哨句开头 + L1 在场；
 *   ④ SKILL.md 正文**字节 ==** COMPLIANCE_SKILL_BODY（生成物与常量防漂移）；
 *   ⑤ L1 每行 ⊆ SKILL_BODY（单一出处结构断言——L1 是抽出来的不是第二份手写）；
 *   ⑥ 标准号前缀表与引擎 `doc_catalog.py` 的 `_STD_NO_PREFIX` **逐词同步**（跨语言防漂移）。
 *
 * 用法：node scripts/smoke-compliance-sentry.mjs   （退出码 0 = 全通过）
 */
import { readFile, readdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  COMPLIANCE_SKILL_BODY,
  KS_COMPLIANCE_SENTRY,
  STD_NO_PREFIXES,
  buildComplianceNextStep,
  buildComplianceSection,
  complianceNextStepMessage,
  extractL1,
  isComplianceTriggered,
  markComplianceTriggered,
  matchComplianceSentry,
  registerComplianceAskGate,
  registerKsComplianceRoutes,
} from '../src/compliance-sentry.js'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const repoRoot = resolve(pluginRoot, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ① 哨句字面**跨文件唯一**（唯一所有者 = compliance-sentry.js；该文件内合法 2 处：
   常量定义 + SKILL_BODY 第五节引用它——单一出处的"一处定义、一处引用"）。 */
{
  let outside = 0
  let outsideWhere = ''
  let inOwner = 0
  for (const dir of ['src', 'client']) {
    for (const f of await readdir(join(pluginRoot, dir))) {
      if (!/\.(js|ts|tsx)$/.test(f)) continue
      const text = await readFile(join(pluginRoot, dir, f), 'utf8')
      const n = text.split(KS_COMPLIANCE_SENTRY).length - 1
      if (n === 0) continue
      if (f === 'compliance-sentry.js' && dir === 'src') inOwner += n
      else { outside += n; outsideWhere += `${dir}/${f}×${String(n)} ` }
    }
  }
  check('① 哨句字面**跨文件只此一处所有者**（文件内 = 常量定义 + 技能正文引用，恰 2 处）',
    outside === 0 && inOwner === 2, `文件外 ${String(outside)} 处：${outsideWhere} / 文件内 ${String(inOwner)} 处`)
}

/* ② 预判据三组用例。 */
check('② 词族命中（法规/应当/制度…宽进）',
  ['按安全生产法这个怎么算？', '吊装作业有什么规定', '这台设备要资质吗'].every((s) => matchComplianceSentry(s)))
check('② 全不命中 ⇒ false（零开销前提）',
  ['帮我把这段话改通顺', '今天天气怎么样', '写个排序函数'].every((s) => !matchComplianceSentry(s)))
check('② 标准号模式命中（GB/T 3608 / GB30871 / DB11/T 1234 / AQ 3009 形）',
  ['GB/T 3608-2008 怎么说', '按 GB30871 第 4 条', 'DB11/T 1234-2020 适用吗', 'AQ 3009-2004 呢']
    .every((s) => matchComplianceSentry(s)),
  '含 doc_catalog 同源前缀表；⚠ T/CECS（协会标准）暂不在引擎前缀表——登记差异、不自造第二份')

/* ③ 段文两态（provider 同步语义）。 */
{
  const section = buildComplianceSection()
  const off = section.text({ agent: { session: { id: 's1' } } })
  check('③ 未触发 ⇒ 段文**逐字等于哨句**（每轮零增量——省 token 硬约束底线）',
    off === KS_COMPLIANCE_SENTRY, `长度 ${String(off.length)}`)
  const sectionOn = buildComplianceSection({ isTriggered: () => true })
  const on = sectionOn.text({ agent: { session: { id: 's1' } } })
  check('③ 触发 ⇒ 哨句开头 + L1 在场（按需才付上下文成本）',
    on.startsWith(KS_COMPLIANCE_SENTRY) && on.includes('作答铁律') && on.length > off.length * 3,
    `长度 ${String(on.length)}`)
}

/* ④ SKILL.md 字节同步（生成物 vs 常量）。⚠ F1 修复：**换行归一**后比——
   autocrlf 检出（提取树/任何 CRLF checkout）不许把判据弄成恒红（复核 A/B 实证）。 */
{
  const norm = (s) => s.replace(/\r\n/g, '\n').trim()
  const file = await readFile(join(repoRoot, '.dsh', 'skills', 'compliance-qa', 'SKILL.md'), 'utf8')
  const body = file.split('---\n').slice(2).join('---\n')
  check('④ SKILL.md 正文 == COMPLIANCE_SKILL_BODY（CRLF 归一后比——防两边漂移）',
    norm(body) === norm(COMPLIANCE_SKILL_BODY), `文件 ${String(norm(body).length)} 字 / 常量 ${String(norm(COMPLIANCE_SKILL_BODY).length)} 字`)
}

/* ⑤ L1 每行 ⊆ SKILL_BODY + **覆盖方向**（F2 修复：单向 ⊆ 会被"少抄铁律"钻过——M6c 实证）：
   铁律 1~8 **一条不少** + 段文与独立重算抽取件**逐字节相等**。 */
{
  const l1 = extractL1()
  const bodyLines = COMPLIANCE_SKILL_BODY.split('\n').map((s) => s.trim()).filter((s) => s.length > 0)
  const WRAPPERS = ['合规护航（轻量前置判据命中 ⇒ 本段按需注入）：', '完整规范见 compliance-qa 技能（唯一出处）。']
  const orphans = l1.split('\n').map((s) => s.trim())
    .filter((s) => s.length > 0 && !bodyLines.includes(s) && !WRAPPERS.includes(s))
  check('⑤ L1 段文每行都出自 SKILL_BODY（L1=抽取件；包装语仅两行且白名单点名）',
    orphans.length === 0,
    `游离行 ${JSON.stringify(orphans)}`)
  const ruleLines = l1.split('\n').map((s) => s.trim()).filter((s) => /^\d+\./.test(s))
  check('⑤ 覆盖方向：L1 里铁律**恰好 8 条**（少抄即红——M6c 的补法）',
    ruleLines.length === 8, `实到 ${String(ruleLines.length)} 条`)
  const assembled = buildComplianceSection({ isTriggered: () => true }).text({ agent: { session: { id: 'sx' } } })
  check('⑤ 组装文 == 哨句 + 独立重算抽取件（**逐字节**——手写漂移双向堵死）',
    assembled === `${KS_COMPLIANCE_SENTRY}\n\n${extractL1()}`, `组装 ${String(assembled.length)} 字`)
}

/* ⑨ P0-1/F3 形状判据（假桩比真件宽松 = 漏检根因——本块按真宿主必填面钉）：
   ① 段声明的 order 必须是**有限数**（缺 = 真宿主拒整段 ⇒ 整插件不激活）；
   ② deferContext 消息必填 id（唯一）+ source={kind:'plugin',…}。 */
{
  const section = buildComplianceSection()
  check('⑨ 段声明含**有限数 order**（缺 order ⇒ 真宿主拒整段 ⇒ 整插件不激活——P0-1 回归牙）',
    typeof section.order === 'number' && Number.isFinite(section.order),
    `order=${String(section.order)}`)
  const m1 = complianceNextStepMessage()
  const m2 = complianceNextStepMessage()
  check('⑨ deferContext 消息必填 id（唯一不撞）+ source 合约形状（F3 回归牙）',
    typeof m1.id === 'string' && m1.id.startsWith('ks-compliance-') && m1.id !== m2.id
    && m1.source?.kind === 'plugin' && m1.source?.plugin === 'ks-dsh-plugin',
    JSON.stringify({ id: m1.id, source: m1.source }))
}

/* ⑥ 前缀表与引擎 _STD_NO_PREFIX 逐词同步。 */
{
  const py = await readFile(join(repoRoot, 'src', 'core', 'knowledge', 'doc_catalog.py'), 'utf8')
  const m = py.match(/_STD_NO_PREFIX = re\.compile\(\s*r"\^\(([^)]+)\)/)
  const pyPrefixes = m === null ? [] : m[1].split('|')
  check('⑥ 标准号前缀表与引擎 doc_catalog.py `_STD_NO_PREFIX` **逐词同步**',
    pyPrefixes.length === STD_NO_PREFIXES.length && pyPrefixes.every((p, i) => p === STD_NO_PREFIXES[i]),
    `引擎 ${JSON.stringify(pyPrefixes)} / 插件 ${JSON.stringify(STD_NO_PREFIXES)}`)
}

/* ⑦ C2-a 触发标记：命中⇒标记开（L1 跟进）/ 清除⇒关 / TTL 过期⇒关 / 路由 405 守卫。 */
{
  markComplianceTriggered('s9', true, Date.now())
  check('⑦ 命中 ⇒ 会话标记开 ⇒ 提示段带 L1（三件套串起来）',
    isComplianceTriggered('s9', Date.now()) === true
    && buildComplianceSection({ isTriggered: isComplianceTriggered })
      .text({ agent: { session: { id: 's9' } } })
      .includes('作答铁律'),
    'mark → isTriggered → section')
  markComplianceTriggered('s9', true, 1000) // 自己的时间线（上一条用真钟打过标——用例间时钟隔离）
  check('⑦ TTL 过期 ⇒ 自动关（120s 后不再带 L1——按需才付成本）',
    isComplianceTriggered('s9', 1000 + 120_001) === false)
  markComplianceTriggered('s9', false, 2000)
  check('⑦ 清除（草稿不再命中）⇒ 立即关', isComplianceTriggered('s9', 2000) === false)
  let routeShape = null
  registerKsComplianceRoutes({ webServer: { register: (d) => { routeShape = d; return () => {} } } })
  const out = { status: null, body: null }
  const res = { writeHead(s) { out.status = s }, end(t) { try { out.body = JSON.parse(t) } catch { out.body = t } } }
  await routeShape.handler({ method: 'GET', url: '/ks/compliance/ping' }, res)
  check('⑦ ping 路由 exact/无尾斜杠 + 非 POST → 405（只判不写）',
    routeShape.kind === 'exact' && routeShape.path === '/ks/compliance/ping' && out.status === 405,
    `${routeShape.kind} ${routeShape.path} → ${String(out.status)}`)
}

/* ⑧ C2-b 采集审批门：ks_collect **每次**都 ask（人话问句逐字）；其余工具原样放行。 */
{
  const listeners = []
  registerComplianceAskGate({ on: (name, fn) => { listeners.push({ name, fn }); return () => {} } })
  check('⑧ 审批门注册在 tools/pre-execute', listeners.length === 1 && listeners[0].name === 'tools/pre-execute')
  const asked = []
  const next = async () => ({ kind: 'allow' })
  for (const call of [1, 2]) {
    const d = await listeners[0].fn({ name: 'ks_collect', arguments: { title: '某法规汇编', url: 'https://example.gov/x' } }, next)
    asked.push(d)
  }
  check('⑧ ks_collect **每次**都 {kind:ask}（两次两问——"每次都先问"，无白名单旁路）',
    asked.every((d) => d.kind === 'ask') && asked.length === 2, JSON.stringify(asked.map((d) => d.kind)))
  check('⑧ 问句人话逐字（要把《X》（来源：…）下载进知识库吗？）',
    String(asked[0].reason).includes('要把《某法规汇编》')
    && String(asked[0].reason).includes('来源：https://example.gov/x')
    && String(asked[0].reason).includes('下载进知识库吗？'),
    String(asked[0].reason))
  const other = await listeners[0].fn({ name: 'ks_answer', arguments: {} }, next)
  check('⑧ 其余工具原样放行（不动别人一个字）', other.kind === 'allow')
  const step = buildComplianceNextStep()
  check('⑧ 按步指引短（≤120 字）且核心纪律词「先征求同意」在场',
    step.length <= 120 && step.includes('先征求同意') && complianceNextStepMessage().content[0].text === step,
    `${String(step.length)} 字`)
}

/* ⑩ 批3-c：工具说明瘦身两件——① 四件说明书**字数上限**（防回涨：ks_answer ≤1000、其余 ≤600，
   原文 2156/596/516/360 = 成绩单"前"字）；② 首用回执**每会话每工具恰一次** + UserMessage
   必填形状（id 唯一 + source 合约——F3 教训内建）。 */
{
  const idx = await import('../src/index.js')
  const stub = {}
  const sizes = {
    ks_answer: idx.makeAnswerTool(stub, () => ({})).description.length,
    ks_resolve_clause: idx.makeResolveTool(stub, () => ({})).description.length,
    ks_ping: idx.makePingTool(stub).description.length,
    ks_effect_report: idx.makeEffectReportTool(stub, () => ({})).description.length,
  }
  check('⑩ 说明书字数上限（防回涨）：ks_answer ≤1000、其余 ≤600',
    sizes.ks_answer <= 1000 && sizes.ks_resolve_clause <= 600 && sizes.ks_ping <= 600
    && sizes.ks_effect_report <= 600,
    JSON.stringify(sizes))
  const { firstUseReceipt, KS_ANSWER_DETAIL } = await import('../src/tool-details.js')
  const got = []
  const exec = {
    agent: { session: { id: 'sess-r' } },
    deferContext: (m) => { got.push(m) },
  }
  firstUseReceipt(exec, 'ks_answer')
  firstUseReceipt(exec, 'ks_answer')
  firstUseReceipt({ ...exec, agent: { session: { id: 'sess-r2' } }, deferContext: (m) => { got.push(m) } }, 'ks_answer')
  check('⑩ 首用回执：每会话每工具**恰一次**（同会话二调不重发、异会话各发）',
    got.length === 2 && got[0].content[0].text === KS_ANSWER_DETAIL,
    `发出 ${String(got.length)} 份`)
  check('⑩ 回执消息必填形状（id 唯一 + source 合约——F3 内建防重演）',
    got.every((m) => typeof m.id === 'string' && m.id.startsWith('ks-detail-')
      && m.source?.kind === 'plugin' && m.source?.plugin === 'ks-dsh-plugin'),
    JSON.stringify(got.map((m) => m.id)))
  firstUseReceipt({ agent: { session: { id: 'sess-r3' } } }, 'ks_answer')
  check('⑩ deferContext 缺席 ⇒ 探针降级不炸（可缺省面纪律）', true)
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== compliance-sentry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
