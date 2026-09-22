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
  buildComplianceSection,
  extractL1,
  matchComplianceSentry,
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

/* ④ SKILL.md 字节同步（生成物 vs 常量）。 */
{
  const file = await readFile(join(repoRoot, '.dsh', 'skills', 'compliance-qa', 'SKILL.md'), 'utf8')
  const body = file.split('---\n').slice(2).join('---\n')
  check('④ SKILL.md 正文 == COMPLIANCE_SKILL_BODY（防两边漂移）',
    body.trim() === COMPLIANCE_SKILL_BODY.trim(), `文件 ${String(body.trim().length)} 字 / 常量 ${String(COMPLIANCE_SKILL_BODY.trim().length)} 字`)
}

/* ⑤ L1 每行 ⊆ SKILL_BODY（单一出处结构断言；仅允许**两行包装语**——头指路 + 尾指路）。 */
{
  const l1 = extractL1()
  const bodyLines = COMPLIANCE_SKILL_BODY.split('\n').map((s) => s.trim()).filter((s) => s.length > 0)
  const WRAPPERS = ['合规护航（轻量前置判据命中 ⇒ 本段按需注入）：', '完整规范见 compliance-qa 技能（唯一出处）。']
  const orphans = l1.split('\n').map((s) => s.trim())
    .filter((s) => s.length > 0 && !bodyLines.includes(s) && !WRAPPERS.includes(s))
  check('⑤ L1 段文每行都出自 SKILL_BODY（L1=抽取件；包装语仅两行且白名单点名）',
    orphans.length === 0,
    `游离行 ${JSON.stringify(orphans)}`)
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

const failed = results.filter((r) => !r.ok)
console.log(`\n== compliance-sentry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
