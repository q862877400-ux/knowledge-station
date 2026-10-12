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

/* ② 预判据用例。
 * ⚠ 2026-09-24 **就地改判据**（业主管辖："我输入了合规问题聊天，还触发了合规护航：待命，
 *   但其实我们没有在聊需要用法规标准解释的事情"）。旧用例把「应当」「有什么规定」当正例
 *   ——那正是误触发源（"单元测试覆盖率**应当**达到 80% 吗"）。旧口径原文保留在下面一行：
 *     旧：['按安全生产法这个怎么算？', '吊装作业有什么规定', '这台设备要资质吗']
 * 新口径：词表只收**点不出歧义的专名**；泛义务词（必须/应当/不得/禁止）与泛规定词
 * （标准/规范/规定）交给 Jev 护栏判（smoke-jev-guard 钉那一侧），词表不再背这口锅。 */
check('② 词族命中（法规/国标/资质…专名）',
  ['按安全生产法这个怎么算？', '这台设备要资质吗', '危险化学品经营需要审批吗', 'GB 30871 怎么分级']
    .every((s) => matchComplianceSentry(s)))
check('② 全不命中 ⇒ false（零开销前提）',
  ['帮我把这段话改通顺', '今天天气怎么样', '写个排序函数'].every((s) => !matchComplianceSentry(s)))
check('② **泛义务词/泛规定词不再误触发**（2026-09-24 瘦身后的核心判据）',
  ['这个函数必须先排序再二分', '重构这段代码不得引入新的依赖，怎么做',
    '单元测试覆盖率必须达到 80% 吗', '这个 API 的标准错误码应该怎么设计',
    '文档里禁止使用 emoji，这是什么规范', '数据库事务隔离级别设错了会怎样，必须怎么配',
    '用 git 不得在主干上直接提交，这条规范对吗', '前端路由必须懒加载，否则首屏白屏',
    'Python 里 list 应当用生成器还是列表推导？']
    .every((s) => !matchComplianceSentry(s)),
  '这 9 条在瘦身前 9/9 全误触发（真机实测，业主报障同源）')
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
   autocrlf 检出（提取树/任何 CRLF checkout）不许把判据弄成恒红（复核 A/B 实证）。
   ⚠ 2026-09-24 **独立复核 HIGH（门禁阻塞）**：`split('---\n')` 在 CRLF 检出里**切不开**
   （文件里是 `---\r\n`）⇒ 整份（含 front-matter）被当正文 ⇒ 比对必红。
   ⇒ **先归一换行再切 front-matter**（顺序：normalize → split，不是反过来）。 */
{
  const norm = (s) => s.replace(/\r\n/g, '\n').trim()
  const file = await readFile(join(repoRoot, '.dsh', 'skills', 'compliance-qa', 'SKILL.md'), 'utf8')
  const body = norm(file).split('---\n').slice(2).join('---\n').trim()
  check('④ SKILL.md 正文 == COMPLIANCE_SKILL_BODY（CRLF 归一后比——防两边漂移）',
    body === norm(COMPLIANCE_SKILL_BODY), `文件 ${String(body.length)} 字 / 常量 ${String(norm(COMPLIANCE_SKILL_BODY).length)} 字`)
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

/* 本插件在 v4 下的生产者身份。单一常量，判据与断言都从这里取（避免字面量散落）。 */
const KS_PRODUCER_KIND = 'plugin:ks-dsh-plugin'

/* v4 源契约判据（模块作用域，⑨ 与 ⑩ 共用）。
   ⚠ v4 契约（2026-09-28 对齐 DSH 校验原文，非猜测；复核 `verify-v4-source` 独立核过）：
     【准入规则】`packages/session/session-format-v3-to-v4/src/message-sources.ts:9` 逐字
       拒收 `kind === 'plugin'`（**只查 kind，完全不管 plugin 字段**；同规则另见 developer.ts:26）。
     【迁移行为】同包 `sources.ts` 的 `rewritePluginSource` 文档字符串逐字："kind is the producer's
       own kind and whose `plugin` field is dropped" ⇒ **v4 迁移会丢弃 `plugin` 字段**。
     ⚠ 依据分工要说清：**"不带 plugin 字段"的依据是迁移行为（sources.ts），不是准入规则
       （message-sources.ts 那条对该字段根本不看）**。复核指出我原先把它挂在准入规则名下、依据链有一环虚，
       此处更正。结论不变（该删），且本判据比 DSH 准入**更严**（DSH 允许留 plugin 字段）——方向是安全的。
     全 DSH `packages/session` 扫 `source['plugin']` 共 16 处，全在 v0-to-v1/v2-to-v3 旧迁移包，
     **v4 读路径零消费者** ⇒ 删掉不丢信息（复核实测）。
   钉住**三件承重条件**：kind 非退休值、带我们的生产者名、不带遗留 plugin 字段。
   🔴 更正留痕（复核打回）：我原先在这里写「刻意**不**只硬编码整串、那样换生产者名就假红」——**那句是假的**，
   实现就是硬编码 KS_PRODUCER_KIND。复核用变异 M2 实测：改成 `plugin:other-producer` ⇒ FAIL(32/34) exit 1。
   **改名时门禁会红，是故意的**（钉死身份正是本判据的目的），不是缺陷。此处改为如实描述。 */
const v4SourceOk = (s) =>
  typeof s?.kind === 'string' && s.kind.length > 0
  && s.kind !== 'plugin'                      // ① v4 拒收的退休值
  && s.kind === KS_PRODUCER_KIND              // ② 我们的生产者身份（刻意钉死）
  && s.plugin === undefined;                 // ③ v4 迁移会丢弃该字段（依据见上）

/* ⑨ P0-1/F3 形状判据（假桩比真件宽松 = 漏检根因——本块按真宿主必填面钉）：
   ① 段声明的 order 必须是**有限数**（缺 = 真宿主拒整段 ⇒ 整插件不激活）；
   ② deferContext 消息必填 id（唯一）+ source 的 v4 生产者合约。 */
{
  const section = buildComplianceSection()
  check('⑨ 段声明含**有限数 order**（缺 order ⇒ 真宿主拒整段 ⇒ 整插件不激活——P0-1 回归牙）',
    typeof section.order === 'number' && Number.isFinite(section.order),
    `order=${String(section.order)}`)
  const m1 = complianceNextStepMessage()
  const m2 = complianceNextStepMessage()
  check('⑨ deferContext 消息必填 id（唯一不撞）+ source 合约形状（F3 回归牙·v4）',
    typeof m1.id === 'string' && m1.id.startsWith('ks-compliance-') && m1.id !== m2.id
    && v4SourceOk(m1.source),
    JSON.stringify({ id: m1.id, source: m1.source }))
  // 回归牙：kind 退回退休值 'plugin' 必须被本断言抓住（v4 下会让消息落不了盘、回合第一步就死）
  check('⑨ 源契约回归牙：kind 退回 "plugin" 必判不合格',
    v4SourceOk({ kind: 'plugin', plugin: 'ks-dsh-plugin' }) === false,
    'v4 拒收 kind==="plugin"，断言必须能抓住它')
  // 回归牙组（复核建议③）：把 M4/M5/M6 三种"形状坏"钉成常驻断言，
  // 使 v4SourceOk 的**三件承重条件逐条**都有反例覆盖（此前只有 kind==='plugin' 一条）。
  check('⑨ 源契约回归牙组：source 缺失 / 类型错 / kind 空串 / 遗留 plugin 字段 必判不合格',
    v4SourceOk(undefined) === false            // M4 缺失
    && v4SourceOk('plugin:ks-dsh-plugin') === false  // M5 类型错（非对象）
    && v4SourceOk({ kind: '' }) === false       // M6 kind 空串
    && v4SourceOk({ kind: KS_PRODUCER_KIND, plugin: 'ks-dsh-plugin' }) === false, // M3 带回遗留字段
    '四种坏形状都必须判不合格')
  check('⑨ 源契约正向对照：合规形状（kind=生产者名、无 plugin 字段）必判**合格**',
    v4SourceOk({ kind: KS_PRODUCER_KIND }) === true
    && v4SourceOk(m1.source) === true,
    '防止判据退化成恒假（那样上面的反例就全被抓、但真件也过不了）')
}

/* ⑨b v4 源契约**反漂移牙**（复核建议②，2026-09-28）。
   `v4SourceOk` 是手抄 DSH 规则的镜像：DSH 改了规则、本仓不会自动知道。
   仿 ⑥ 的成熟范式（读引擎/宿主源码逐词比对），这里直接读 DSH 校验原文，
   断言它**仍拒收 kind==='plugin'**。
   ⚠ 读不到该文件 ⇒ **判 skipped，绝不判 passed**（本仓纪律：依赖不可用不得伪装成通过）。 */
{
  let dsh = null
  let dshErr = ''
  // 依次尝试：环境变量显式指定 → 从仓根上溯（../DSH/…）→ 本机已知检出位置 D:\AI\DSH\…
  const roots = [process.env.KS_DSH_ROOT, join(repoRoot, '..', 'DSH', 'deepseek-harness'), 'D:\\AI\\DSH\\deepseek-harness']
  for (const base of roots) {
    if (!base) continue
    const p = join(base, 'packages', 'session', 'session-format-v3-to-v4', 'src', 'message-sources.ts')
    try {
      dsh = await readFile(p, 'utf8'); break
    } catch (e) { dshErr = String(e && e.code || e) }
  }
  if (dsh === null) {
    check('⑨b v4 源契约反漂移：DSH 校验原文可读（读不到 ⇒ 判**未验证**、不判通过）', false,
      `读不到 message-sources.ts（最后错误 ${dshErr}）；设 KS_DSH_ROOT 指向 DSH 检出可恢复本条`)
  } else {
    check('⑨b v4 源契约反漂移：DSH 校验原文**仍拒收** kind==="plugin"（v4SourceOk 是它的镜像）',
      /kind['"]\s*\)?\s*===\s*'plugin'/.test(dsh) || /===\s*'plugin'/.test(dsh),
      'DSH 若不再拒收退休值，本仓这条判据的依据就变了，须复核')
  }
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
  let registerCompliance = () => {}
  // ⚠ manager 在**注册时**被闭包捕获 ⇒ 要换 manager 必须重新注册一次路由。
  let activeMgr = null
  registerCompliance = (mgr) => {
    activeMgr = mgr
    registerKsComplianceRoutes(
      { webServer: { register: (d) => { routeShape = d; return () => {} } } },
      mgr,
    )
  }
  registerCompliance(null)
  const out = { status: null, body: null }
  const res = { writeHead(s) { out.status = s }, end(t) { try { out.body = JSON.parse(t) } catch { out.body = t } } }
  await routeShape.handler({ method: 'GET', url: '/ks/compliance/ping' }, res)
  check('⑦ ping 路由 exact/无尾斜杠 + 非 POST → 405（只判不写）',
    routeShape.kind === 'exact' && routeShape.path === '/ks/compliance/ping' && out.status === 405,
    `${routeShape.kind} ${routeShape.path} → ${String(out.status)}`)

  /* ⑦b Jev 接线（2026-09-24）：词表命中直达；未命中才问引擎；引擎/Jev 挂了回落词表。 */
  const { EventEmitter } = await import('node:events')

  const ping = async (text, manager) => {
    if (manager !== activeMgr) registerCompliance(manager)
    const o = { status: null, body: null }
    const r = {
      writeHead(s) { o.status = s },
      end(t) { try { o.body = JSON.parse(t) } catch { o.body = t } },
    }
    const req = new EventEmitter()
    req.method = 'POST'
    req.url = '/ks/compliance/ping'
    queueMicrotask(() => {
      req.emit('data', Buffer.from(JSON.stringify({ text, session: 'probe' }), 'utf8'))
      req.emit('end')
    })
    await routeShape.handler(req, r)
    return o.body?.data
  }
  // 词表命中 ⇒ 零网络直达（不 manager 也要能用）
  const direct = await ping('按安全生产法这个怎么算？', null)
  check('⑦b 词表命中 ⇒ 直达触发（零网络，且不依赖 manager）',
    direct?.triggered === true && direct?.verdict === 'trigger' && direct?.source === 'wordlist',
    JSON.stringify(direct))
  // 无 manager ⇒ 静默回落词表（判 false），不报错
  const noMgr = await ping('写个排序函数', null)
  check('⑦b 无 manager / Jev 不可用 ⇒ 静默回落词表（不报错、不阻塞输入）',
    noMgr?.triggered === false && noMgr?.source === 'wordlist', JSON.stringify(noMgr))

  // 词表没命中 + 引擎回 verdict ⇒ 真按 Jev 的判（拦截 fetch 打桩，零网络）
  const realFetch = globalThis.fetch
  const seen = []
  const stub = (payload) => {
    globalThis.fetch = async (url) => {
      seen.push(String(url))
      return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }
  }
  const mgr = { ensureLive: async () => ({ port: 9, token: 't' }) }
  try {
    // 隐性合规：词表看不见，Jev 说 trigger ⇒ host 必须触发
    stub({ code: 200, status: 'success', data: { available: true, verdict: 'trigger' } })
    const jevHit = await ping('我想让程序自动帮用户点『已阅读并同意』的服务协议', mgr)
    check('⑦b 词表漏掉的隐性合规 ⇒ Jev 说触发就触发（且真的问了引擎）',
      jevHit?.triggered === true && jevHit?.verdict === 'trigger' && jevHit?.source === 'jev'
      && seen.some((u) => u.includes('/api/v1/laws/compliance-guard')),
      `${JSON.stringify(jevHit)} calls=${JSON.stringify(seen)}`)
    // Jev 说静默 ⇒ 不触发
    stub({ code: 200, status: 'success', data: { available: true, verdict: 'silent' } })
    const jevSilent = await ping('帮我写个快速排序', mgr)
    check('⑦b Jev 说静默 ⇒ 不触发', jevSilent?.triggered === false && jevSilent?.source === 'jev',
      JSON.stringify(jevSilent))
    // Jev 不可用（available=false）⇒ 回落词表
    stub({ code: 200, status: 'success', data: { available: false, verdict: 'unknown' } })
    const jevDown = await ping('帮我写个快速排序', mgr)
    check('⑦b Jev 不可用（available=false）⇒ 回落词表（不当作"不触发"的真相）',
      jevDown?.triggered === false && jevDown?.source === 'wordlist', JSON.stringify(jevDown))
    // 引擎报错 ⇒ 回落，不把错误抛给输入坞
    globalThis.fetch = async () => { throw new Error('engine down') }
    const engineDown = await ping('帮我写个快速排序', mgr)
    check('⑦b 引擎不可达 ⇒ 静默回落词表（绝不让护栏变成打断输入的错误源）',
      engineDown?.triggered === false && engineDown?.source === 'wordlist', JSON.stringify(engineDown))
  } finally {
    globalThis.fetch = realFetch
  }
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
    ks_collect: (await import('../src/collect.js')).makeCollectTool(stub, () => ({})).description.length,
    ks_materials: (await import('../src/materials.js')).makeMaterialsTool(stub).description.length,
  }
  check('⑩ 说明书字数上限（防回涨）：ks_answer ≤1000、其余 ≤600',
    sizes.ks_answer <= 1000
    && ['ks_resolve_clause', 'ks_ping', 'ks_effect_report', 'ks_collect', 'ks_materials']
      .every((k) => sizes[k] <= 600),
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
  check('⑩ 回执消息必填形状（id 唯一 + source 合约——F3 内建防重演·v4）',
    got.every((m) => typeof m.id === 'string' && m.id.startsWith('ks-detail-')
      && v4SourceOk(m.source)),
    JSON.stringify(got.map((m) => ({ id: m.id, source: m.source }))))
  firstUseReceipt({ agent: { session: { id: 'sess-r3' } } }, 'ks_answer')
  check('⑩ deferContext 缺席 ⇒ 探针降级不炸（可缺省面纪律）', true)
}

/* ============================================================================
   ⑪ 界面零展示 + 后台判断仍在（2026-10-12，业主裁定 A）
   ----------------------------------------------------------------------------
   业主原话：「这个自动检测哨兵，你后台可以继续这样判断，但我不需要你在前台展示，
   也不要搞任何展示，就把它定回去，直接把展示相关的逻辑删掉就好了。」
   ⇒ 钉两件事，**必须同时成立**（少任一都是做错）：
     · ① 界面**一个合规字样都没有**（徽章 / 提示都不许有）；
     · ② 后台判断**仍活着** —— `KsScopeChip` 照发 `POST /ks/compliance/ping`
          （它**不是展示**，是宿主打会话标记的**唯一触发点**；删了就一起死）。
   ============================================================================ */
{
  const chipSrc = await readFile(join(pluginRoot, 'client', 'KsScopeChip.tsx'), 'utf8')
  /* ⚠ 计数前剥注释（本仓纪律）：源码注释里会**引用旧文案作留痕**
     （本次就写着「删掉『⚖ 合规护航：待命』徽章」）⇒ 朴素 grep 会把留痕算成"还在显示"。 */
  const chipCode = chipSrc
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/^\s*\/\/.*$/gm, ' ')

  check('⑪ 界面零展示：代码里没有「合规护航：待命」徽章字面',
    !chipCode.includes('合规护航：待命'))
  check('⑪ 界面零展示：代码里没有合规徽章的 DOM 钩子（data-ks-compliance-marker）',
    !chipCode.includes('data-ks-compliance-marker'))
  check('⑪ 界面零展示：代码里没有那句中间档提示',
    !chipCode.includes('可能要用法规依据'))
  check('⑪ 界面零展示：组件里没有 sentry 状态（没有可显示的合规状态）',
    !/\bsentry\b/.test(chipCode))
  /* ★ ② 后台判断仍在：这次 fetch 是**唯一触发点**，必须在。 */
  check('⑪ ★ 后台判断仍在：KsScopeChip 照发 POST /ks/compliance/ping（删了后台就一起死）',
    chipCode.includes("'/ks/compliance/ping'") && chipCode.includes("method: 'POST'"))
  check('⑪ 后台判断仍在：发的 body 带 session + text（宿主据此判并打会话标记）',
    chipCode.includes('session: sessionId') && chipCode.includes('text: draft'))
  /* ⚠ 发请求但**不消费回执**（界面不需要任何状态）—— 钉住"只发不读"。 */
  check('⑪ 只发不读：不再解析回执（没有 .then 读 triggered）',
    !chipCode.includes('triggered'))
  /* 宿主侧三件（哨句 / 打标记 / 段文两态）**必须仍在** —— 后台判断的另一半。 */
  const sentrySrc = await readFile(join(pluginRoot, 'src', 'compliance-sentry.js'), 'utf8')
  check('⑪ ★ 后台判断仍在：宿主侧仍打会话标记（markComplianceTriggered 调用点在场）',
    sentrySrc.includes('markComplianceTriggered(sessionId, verdict ==='),
    '宿主打标记的调用点')
  check('⑪ ★ 后台判断仍在：段文仍是两态（未触发=只哨句 / 触发=哨句+L1）',
    sentrySrc.includes('return triggered ? `${KS_COMPLIANCE_SENTRY}\\n\\n${extractL1()}` : KS_COMPLIANCE_SENTRY'))
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== compliance-sentry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
