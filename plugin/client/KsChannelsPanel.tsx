/**
 * ks-dsh-plugin — client/KsChannelsPanel.tsx
 *
 * **渠道台账**面板（§11.0 R4b）——业主原话："前端要能看到各种渠道的链接、有效性、
 * 上次成功查询什么的，方便人工维护渠道"。
 *
 * ## 三列口径（**不许合并**，这是本面板存在的全部意义）
 * | 列 | 含义 | 数据来自 |
 * |---|---|---|
 * | 接线（wiring） | **我们的代码**接没接上：wired 在巡检链上 / unwired 注册了但永不调用 / broken 在链上但实测不工作 | 由 `routing.py` 反查（R2） |
 * | 有效性（state） | **渠道本身**今天能不能抓：ok / suspicious（HTTP 200 但没抓到预期锚点）/ down | R3 语义探针实测 |
 * | 上次成功 | 最近一次**探针成功**的时间 | `last_ok_at`（与"上次尝试"分开） |
 *
 * ⚠ R1 的实测教训（G5/G6）：13 个适配器里**只有 7 个在链上**
 * （`official_gb`/`ndls`/`govcn`/`dbba`/`hbba`/`mee`/`ttbz`）。若把"接线"当"有效性"、
 * 或把"台账条数"当"能力条数"，面板第一版就会虚报覆盖率。所以顶部摘要**两个数都显示**。
 *
 * ⚠ 2026-09-18 更正两处过期说法（§11.0 R5c + R6c-3b，代码变了注释得跟上）：
 * ① 原文说"在链上的 `web`/`govcn` 两根兜底棒恒 miss"——**`web` 已于 R5c 摘出链外**
 *    （它只解 mock 的 dict，真实打的是 bing HTML ⇒ 恒 miss），所以它今天连"在链上"都不是；
 * ② 兜底链现在是 **`official_gb → ndls → govcn`**（R6c-3b 量出来的：按前缀分层抽 10 个真库号，
 *    `official_gb` 4/10、`govcn` **1/10**、`ndls` 6/10）⇒ `govcn` 仍在链上但排最后，
 *    面板里它大概率显示"在链、但基本没被用到"。
 *
 * ## 时间戳是 UTC（诚实标注）
 * `update_channel.last_*` 用 SQLite `datetime('now')` = **UTC**，与库内其它表一致。
 * 面板显式标注 UTC，并在前端换算成"几分钟前"，避免"04:47"被读成凌晨自动跑过。
 */
import * as React from 'react'
import { ensureKsStyles } from './ksGuideStyles'
import { KsCrumb, KsListHead, type KbListCol } from './kbListUi'
import { Fragment, useCallback, useEffect, useState } from 'react'
import { Button, IconChevronDownOutlineRegular, IconChevronRightOutlineRegular, IconFolderOpenOutlineRegular, IconSearchOutlineRegular, Input } from '@deepseek-ai/dsh-client-ui-primitives'

import {
  createChannel,
  deleteChannel,
  fetchAnnounceSummary,
  fetchChannels,
  fetchInspectionSummary,
  getChannelTestCase,
  runChannelProbe,
  runChannelTest,
  setChannelEnabled,
  setChannelTestCase,
  updateChannel,
  type KsChannelList,
  type KsChannelRecord,
} from './api'
import { KsAnnounceSourcesSection, KsInspectionPanel } from './KsSettingsSection'

/** 虚线分隔色（新增表单的框）——与面板其它地方一致地走主题 token。 */
const LINE = 'var(--dsw-alias-border-l2, #ccc)'

export interface KsChannelsPanelProps {
  /** 由 <details onToggle> 驱动——收起 = 挂载但零请求（懒加载门，与其它面板同契约）。 */
  visible: boolean
}

const CATEGORY_LABEL: Record<string, string> = {
  law: '法规', std_gb: '国标', std_hb: '行标', std_db: '地标', std_tb: '团标',
  std_intl: '国际', aggregator: '聚合入口', tool: '工具/Skill',
  internal: '我方通路', other: '其他',
}
const WIRING_LABEL: Record<string, string> = {
  wired: '✅ 已接线', unwired: '⚪ 未接线', broken: '❌ 已知失效',
  user: '👤 用户自加', seed_only: '📋 仅登记',
}
const STATE_LABEL: Record<string, string> = {
  ok: '🟢 可抓', suspicious: '🟡 可疑', down: '🔴 不可抓', unknown: '⚪ 未探',
}

const GRAY = 'var(--dsw-alias-label-secondary, #666)'
const FAINT = 'var(--dsw-alias-label-tertiary, #999)'

/**
 * UTC 时间串 → 人话（"3 分钟前"）。**导出以便离线测**（纯函数，无 DOM 依赖）。
 *
 * ⚠ SQLite 的 `datetime('now')` 是 `YYYY-MM-DD HH:MM:SS`（UTC，无时区标记）——
 * `new Date(该串)` 在多数浏览器会**按本地时区**解析，于是差出 8 小时。
 * 所以这里手工补 `Z` 再解析（这是本函数存在的唯一理由）。
 */
export function describeWhen(utcText: string | null | undefined, nowMs?: number): string {
  if (!utcText) return '—'
  const iso = /Z|[+-]\d\d:\d\d$/.test(utcText) ? utcText : `${utcText.replace(' ', 'T')}Z`
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return utcText
  const now = nowMs ?? Date.now()
  const mins = Math.max(0, Math.round((now - t) / 60000))
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.round(hours / 24)} 天前`
}

/** 一行的"体检结论"是否算**问题**（用于把有问题的排前面）。导出以便离线测。 */
export function needsAttention(row: KsChannelRecord): boolean {
  return row.wiring === 'broken' || row.state === 'down' || row.state === 'suspicious'
    || row.consecutive_failures > 0
}

/** 排序：有问题的在前，其次按类别+名称（稳定）。导出以便离线测。 */
export function sortChannels(rows: KsChannelRecord[]): KsChannelRecord[] {
  return [...rows].sort((a, b) => {
    const na = needsAttention(a) ? 0 : 1
    const nb = needsAttention(b) ? 0 : 1
    if (na !== nb) return na - nb
    if (a.category !== b.category) return a.category < b.category ? -1 : 1
    return a.name < b.name ? -1 : a.name > b.name ? 1 : 0
  })
}

/**
 * 号段（§11.0 R7）——引擎存的是 **JSON 字符串**（列是 TEXT），面板负责解析。
 * 导出以便离线测：坏值一律当"没填"，**绝不让一个脏字段把整张表渲染炸掉**。
 */
export function parseSegments(raw: string | null | undefined): string[] {
  if (!raw) return []
  try {
    const v = JSON.parse(raw)
    return Array.isArray(v) ? v.filter((s): s is string => typeof s === 'string' && s !== '') : []
  } catch {
    return []
  }
}

/** 渠道搜索筛选（业主 2026-09-22：「可以搜网站名字也可以搜网站域名」）：纯函数，判据直接钉。
 *  口径：不区分大小写；名字/整链接/域名主机 三处任一包含即命中；空查询 = 全部。 */
export function filterChannels(rows: readonly KsChannelRecord[], q: string): KsChannelRecord[] {
  const needle = q.trim().toLowerCase()
  if (needle === '') return [...rows]
  return rows.filter((r) => {
    const name = (r.name ?? '').toLowerCase()
    const url = (r.url ?? '').toLowerCase()
    let host = ''
    try {
      host = url !== '' ? new URL(url.split(/[（\s]/)[0]).hostname.toLowerCase() : ''
    } catch { /* 坏链接当无主机 */ }
    return name.includes(needle) || url.includes(needle) || (host !== '' && host.includes(needle))
  })
}

/** 顶部常驻栏「最新动态」人话生成（业主 2026-09-22 给的语气模板："最新的标准和法规是
 *  上个月几号某部门发文废除了一批标准，已在我们的库里同步标记"）。纯函数：有公告用公告、
 *  有巡检变更给同步标记句、都没有就说没有——**不夸大、不编**。 */
export function generateNewsLine(input: {
  announce?: { date?: string | null; title?: string | null } | null
  changes?: { newVersion?: number; retired?: number; replaced?: number; totalChecked?: number } | null
  now?: Date
}): string {
  const parts: string[] = []
  const a = input.announce
  if (a && (a.title ?? '') !== '') {
    parts.push(`最新：${a.date ? String(a.date) + ' ' : ''}「${String(a.title).slice(0, 40)}」`)
  }
  const c = input.changes
  if (c) {
    const bits: string[] = []
    if (c.newVersion) bits.push(`新版 ${String(c.newVersion)}`)
    if (c.retired) bits.push(`废止 ${String(c.retired)}`)
    if (c.replaced) bits.push(`替代 ${String(c.replaced)}`)
    if (bits.length > 0) {
      parts.push(`巡检发现 ${bits.join('、')}——已在库里同步标记`)
    } else if (c.totalChecked) {
      parts.push(`上次巡检共查 ${String(c.totalChecked)} 项，全部无变化`)
    }
  }
  return parts.length > 0 ? `📢 ${parts.join('；')}。` : '📢 最近没有新动态。'
}

/** 目录层列（与知识库目录层同款 4 轨：占位/名称/条数/›——模板就是 .ks-list-dirs 那条）。 */
const DIR_COLS: readonly KbListCol[] = [
  { key: 'dpick', head: '' }, { key: 'dname', head: '名称' },
  { key: 'dcount', head: '条数' }, { key: 'dmore', head: '' },
]
/** 渠道文件层列（.ks-list-chans 自己那条 --ks-cols 的 5 轨；标签列已删 = NOT-DOING #17）。 */
const CH_COLS: readonly KbListCol[] = [
  { key: 'chan', head: '渠道' },
  { key: 'cstate', head: '能不能用' }, { key: 'cdate', head: '上次好用' },
  { key: 'cissue', head: '问题' }, { key: 'cact', head: '操作' },
]

/** 「网站」一级分组（业主 2026-09-23：同站多页归一个网站文件夹、单页站直接当行——
 *  与知识库"文件夹和文件共存"同一逻辑）。纯函数，判据直接钉：同 host 多行 ⇒ 一个
 *  site 组（=文件夹）；单行 host ⇒ solo 行。host 取 url 的域名（去 www. 前缀）。 */
export function groupRowsBySite(rows: readonly KsChannelRecord[]): {
  sites: Array<{ host: string; label: string; rows: KsChannelRecord[] }>
  solos: KsChannelRecord[]
} {
  const byHost = new Map<string, KsChannelRecord[]>()
  for (const r of rows) {
    let host = ''
    try {
      host = (r.url ?? '') !== '' ? new URL(String(r.url).split(/[（\s]/)[0]).hostname.toLowerCase().replace(/^www\./, '') : ''
    } catch { host = '' }
    const key = host !== '' ? host : `（无链接）${r.name}`
    const arr = byHost.get(key)
    if (arr !== undefined) arr.push(r)
    else byHost.set(key, [r])
  }
  const sites: Array<{ host: string; label: string; rows: KsChannelRecord[] }> = []
  const solos: KsChannelRecord[] = []
  for (const [host, grp] of byHost) {
    if (grp.length > 1) sites.push({ host, label: host, rows: grp })
    else solos.push(grp[0])
  }
  sites.sort((a, b) => a.host.localeCompare(b.host))
  return { sites, solos }
}

/** 单位性质的用户叫法（树的组名；与引擎 ORG_KIND 同序）。 */
export const ORG_KIND_LABEL: Record<string, string> = {
  central: '国家部委/总局', local_congress: '地方人大', local_dept: '地方厅局',
  industry: '行业机构', intl: '国际组织', commercial: '商业/聚合',
  tool: '工具/代码', other: '其他', '': '未分类',
}

/** 按**单位性质**分组（业主 2026-09-22 定案：分类=主办单位性质，文件夹树）。
 *  组序 = ORG_KIND_LABEL 声明序，未分类收尾；组内保持传入顺序（注意力序）。 */
export function groupRowsByOrgKind(
  rows: readonly KsChannelRecord[],
): Array<{ key: string; label: string; rows: KsChannelRecord[] }> {
  const order = Object.keys(ORG_KIND_LABEL)
  const groups = new Map<string, KsChannelRecord[]>()
  for (const r of rows) {
    const k = r.org_kind ?? ''
    const arr = groups.get(k) ?? []
    arr.push(r)
    groups.set(k, arr)
  }
  const keys = [...groups.keys()].sort((a, b) => {
    const ia = order.indexOf(a)
    const ib = order.indexOf(b)
    return (ia < 0 ? order.length : ia) - (ib < 0 ? order.length : ib) || a.localeCompare(b)
  })
  return keys.map((k) => ({ key: k, label: ORG_KIND_LABEL[k] ?? k, rows: groups.get(k) ?? [] }))
}

/** 「AI 一键解决」提示词生成（业主 2026-09-22）：点按钮复制一段提示词，用户粘到对话框，
 *  AI 自己去诊断所有渠道为什么失败、怎么修、怎么长期有效、要人帮什么、用什么工具。
 *  纯函数：喂台账真数据、出自足提示词（agent 看不到本会话，一切要写进词里）。 */
export function buildChannelFixPrompt(
  rows: readonly KsChannelRecord[],
  s?: { total: number; by_state: Record<string, number>; by_wiring: Record<string, number> },
): string {
  const bad = rows.filter((r) => r.state !== 'ok' || r.wiring === 'broken' || r.consecutive_failures > 0)
  const line = (r: KsChannelRecord): string =>
    `- 【${r.name}】类别=${CATEGORY_LABEL[r.category] ?? r.category}；接线=${r.wiring}；`
    + `有效性=${STATE_LABEL[r.state] ?? r.state}${r.enabled === 0 ? '（已停用）' : ''}；`
    + `链接=${r.url ?? '（无）'}；号段=${parseSegments(r.segments_json).join('/') || '（无）'}；`
    + `上次错误=${r.last_error_code ?? '—'} ${r.last_error ?? ''}`.trimEnd()
    + `；连续失败=${r.consecutive_failures}；备注=${r.note ?? '—'}`
  return [
    '请接手「法规/标准巡检渠道台账」的失效渠道修复。台账是渠道能不能抓到法规/标准更新的账本；',
    '下面先给台账现状与问题清单，然后是你的任务。',
    '',
    '## 台账现状',
    s ? `共 ${s.total} 条（有效 ${s.by_state.ok ?? 0} / 可疑 ${s.by_state.suspicious ?? 0} / 失效 ${s.by_state.down ?? 0} / 未探 ${s.by_state.unknown ?? 0}；`
      + `接线 ${s.by_wiring.wired ?? 0}、已知失效 ${s.by_wiring.broken ?? 0}）` : `共 ${rows.length} 条`,
    '',
    `## 问题渠道（${bad.length} 条）`,
    ...(bad.length > 0 ? bad.map(line) : ['（当前没有状态异常的渠道——请核对"可疑/失效/未探"里有没有漏网）']),
    '',
    '## 你的任务（对每条问题渠道逐条做，别只给泛泛而谈）',
    '1. 诊断为什么失败：用 web_fetch 实测链接现状（HTTP 码/落地页/是否改版/是否要登录或验证码）；',
    '   再读我们的适配器代码判断是"站点变了"还是"我们的解析器坏了"（两者修法完全不同）。',
    '2. 怎么修才行：给具体方案——换端点/改解析/改请求头/换适配策略，说明改动会落在哪个文件。',
    '3. 怎么长期有效：修完怎么防止再坏（语义探针期望、回归用例、探测告警口径、负缓存）。',
    '4. 需要用户怎么协助：如实列出只有人能做的事（人工验证/注册账号/过验证码/授权/确认口径）——不要自己替用户决定。',
    '5. 修复时用什么工具：web_search/web_fetch（实测）、引擎探测端点 `POST /api/v1/channels/probe`（语义探针）、',
    '   测试 `tests/test_channel_repo.py` / `tests/test_ledger_chain.py`、门禁 `pwsh -File scripts/run-gates.ps1 -Quick`。',
    '',
    '## 边界与纪律',
    '- 先读 `docs/CHANNEL-COVERAGE-PLAN.md`（渠道覆盖方案与轮次台账）再动手；适配器在 `src/core/laws/`（按渠道分文件）。',
    '- 修不动/证据不足的如实说修不动，登记原因，不要硬编一个"应该能用"的方案。',
    '- 每步小提交，消息写清"改了什么/为什么/边界"；产出物只出 Markdown。',
    '- 顺带把「未分类」的渠道标注单位性质（org_kind：central/local_congress/local_dept/industry/intl/commercial/tool/other），给出建议值表让我确认。',
    '- 有不确定的先问用户，不要默默替他做决定。',
  ].join('\n')
}

/** 复制文本到剪贴板（剪贴板 API 不可用时回退 textarea+execCommand）。 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch { /* 落到回退路 */ }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    ta.remove()
    return ok
  } catch {
    return false
  }
}

export function KsChannelsPanel(props: KsChannelsPanelProps): JSX.Element {
  const { visible } = props
  ensureKsStyles()
  const [data, setData] = useState<KsChannelList | null>(null)
  const [error, setError] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [probeBusy, setProbeBusy] = useState<boolean>(false)
  const [notice, setNotice] = useState<string>('')
  const [cat, setCat] = useState<string>('')
  const [state, setState] = useState<string>('')
  // 人工维护（R6f）：新增表单 + 一次性动作的 busy 闸
  const [adding, setAdding] = useState<boolean>(false)
  const [newName, setNewName] = useState<string>('')
  const [newUrl, setNewUrl] = useState<string>('')
  const [newNote, setNewNote] = useState<string>('')
  const [mutating, setMutating] = useState<boolean>(false)
  const [orgSel, setOrgSel] = useState<string | null>(null)
  const [siteSel, setSiteSel] = useState<string | null>(null)
  /** 左树「展开了哪些单位性质」——与知识库左树同一套交互（caret 展开/收起，点名字＝选中该层）。
   *  ⚠ 选中某一类时**自动展开**它（老行为：点一类就看它的站点），caret 只负责展开/收起。 */
  const [openKinds, setOpenKinds] = useState<Set<string>>(new Set())
  const toggleKind = useCallback((key: string): void => {
    setOpenKinds((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])
  const [q, setQ] = useState<string>('')
  const [news, setNews] = useState<string>('')
  const [showDetail, setShowDetail] = useState<boolean>(false)

  const load = useCallback(async (signal?: AbortSignal): Promise<void> => {
    setBusy(true)
    setError('')
    try {
      const out = await fetchChannels(
        { category: cat || undefined, state: state || undefined, limit: 300 }, signal)
      if (!signal?.aborted) setData(out)
    } catch (e) {
      if (!signal?.aborted) setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (!signal?.aborted) setBusy(false)
    }
  }, [cat, state])

  // 懒加载门：收起时零请求（与其它面板同契约）
  useEffect(() => {
    if (!visible) return undefined
    const controller = new AbortController()
    void load(controller.signal)
    // 顶部常驻栏「最新动态」：公告最近一条 + 巡检变更计数 → 一句人话（快照口，零引擎拉起）。
    void (async () => {
      try {
        const [ann, insp] = await Promise.all([
          fetchAnnounceSummary(controller.signal).catch(() => null),
          fetchInspectionSummary(controller.signal).catch(() => null),
        ])
        if (controller.signal.aborted) return
        const recent = ann?.last?.recent?.[0]
        const last = insp?.last
        setNews(generateNewsLine({
          announce: recent ? {
            date: (recent as { published_at?: string | null }).published_at ?? null,
            title: recent.title,
          } : null,
          changes: last ? {
            newVersion: last.by_type?.new_version ?? 0,
            retired: last.by_type?.withdrawn ?? 0,
            replaced: last.by_type?.superseded ?? 0,
            totalChecked: last.total ?? 0,
          } : null,
        }))
      } catch { /* 动态栏拿不到就说没有（generateNewsLine 兜底），不打断主面 */ }
    })()
    return () => controller.abort()
  }, [visible, load])

  const probe = useCallback((): void => {
    if (probeBusy) return
    setProbeBusy(true)
    setNotice('')
    void (async () => {
      try {
        const out = await runChannelProbe()
        const c = out.counts ?? {}
        setNotice(`探测完成：共 ${out.probed} 条 —— 🟢 ${c.ok ?? 0} / `
          + `🟡 ${c.suspicious ?? 0} / 🔴 ${c.down ?? 0} / ⚪ ${c.unknown ?? 0}`
          + `（未配探针的 ${out.without_target.length} 条不参与）`)
        await load()
      } catch (e) {
        setNotice(`探测失败：${e instanceof Error ? e.message : String(e)}`)
      } finally {
        setProbeBusy(false)
      }
    })()
  }, [load, probeBusy])

  const rows = data ? sortChannels(data.items) : []
  const s = data?.summary
  // 当前该显示哪些渠道：搜索态=跨组平铺命中（找渠道一步到位）；组视图=该组的行。
  const viewRows = q.trim() !== ''
    ? filterChannels(rows, q)
    : (groupRowsByOrgKind(rows).find((g) => g.key === orgSel)?.rows ?? [])
  // 面包屑计数：树层=总条数（修「0 条」bug：orgSel=null 时 find 空组）；组/搜索=viewRows。
  const crumbN = q.trim() !== '' ? viewRows.length
    : orgSel === null ? rows.length : viewRows.length

  /** 人工维护动作的统一外壳：一次只允许一个动（`mutating`）、错误**如实显示**原文。
   *  ⚠ 不把引擎的错误码翻译掉：`illegal_channel_field` / `channel_name_required` /
   *  `illegal_enabled` 这些码本身就是给用户看的（它们说明了"为什么不行、该去用哪个入口"）。 */
  const runMutation = useCallback(async (label: string, fn: () => Promise<unknown>,
  ): Promise<void> => {
    if (mutating) return
    setMutating(true)
    setNotice('')
    try {
      await fn()
      setNotice(`${label}：已生效（引擎已记审计痕迹）`)
      await load()
    } catch (e) {
      setNotice(`${label}失败：${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setMutating(false)
    }
  }, [load, mutating])

  const submitCreate = useCallback(async (): Promise<void> => {
    const name = newName.trim()
    if (name === '') return
    await runMutation('新增渠道', async () => {
      await createChannel({
        name,
        ...(newUrl.trim() !== '' ? { url: newUrl.trim() } : {}),
        ...(newNote.trim() !== '' ? { note: newNote.trim() } : {}),
      })
      setNewName(''); setNewUrl(''); setNewNote(''); setAdding(false)
    })
  }, [newName, newUrl, newNote, runMutation])

  const toggleEnabled = useCallback(async (r: KsChannelRecord): Promise<void> => {
    await runMutation(r.enabled === 0 ? '启用渠道' : '停用渠道',
      () => setChannelEnabled(r.channel_id, r.enabled === 0))
  }, [runMutation])

  // （「改号段」处理器已随号段撤出用户面删除（NOT-DOING #17 同族，业主 2026-09-22）：
  //  号段=后台维护事实，需要改走引擎 API/维护通道，不在用户面开口。）

  const editOrgKind = useCallback(async (r: KsChannelRecord): Promise<void> => {

    const kinds = Object.entries(ORG_KIND_LABEL)
    const next = window.prompt(
      '改分类（单位性质）——输入序号：\n' + kinds.map(([k, v], i) => `${i + 1}. ${v}`).join('\n'),
      String(kinds.findIndex(([k]) => k === (r.org_kind ?? '')) + 1))
    if (next === null) return
    const idx = Number(next) - 1
    const kind = kinds[idx] ? kinds[idx][0] : null
    await runMutation('改分类', () => updateChannel(r.channel_id, { org_kind: kind === '' ? null : kind }))
  }, [runMutation])

  /** 批C：「试一试」——未配样本先引导配（样本链接+期望标准号），配完直接跑；已配直接跑。
   *  结果回执进 notice（ok/fail 人话）；留痕在引擎（last_result/last_detail）。 */
  const tryChannel = useCallback(async (r: KsChannelRecord): Promise<void> => {
    await runMutation(`试一试（${r.name}）`, async () => {
      let tc = await getChannelTestCase(r.channel_id)
      if (tc === null) {
        const u = window.prompt(
          `给「${r.name}」配一个已知文件——样本链接\n（一个你确信能从这条渠道拿到的文件/页面地址）：`)
        if (u === null || u.trim() === '') throw new Error('没配样本（已取消）')
        const n = window.prompt('期望的标准号（从那个文件里抄一个，例：GB/T 10561-2005）：')
        if (n === null || n.trim() === '') throw new Error('没配期望标准号（已取消）')
        tc = await setChannelTestCase(r.channel_id, u.trim(), n.trim())
      }
      const out = await runChannelTest(r.channel_id)
      throw new Error(`${out.result === 'ok' ? '✅ 成功' : '❌ 未通过'}：${out.detail}`)
    })
  }, [runMutation])

  const remove = useCallback(async (r: KsChannelRecord): Promise<void> => {
    // 删除是高风险动作：先说清代价，再让人确认（默认建议用「停用」——它保留历史健康度）
    const ok = window.confirm(
      `确定删除「${r.name}」？\n\n`
      + `· 审计痕迹里会保留删除前那一行（删得掉条目，删不掉证据）；\n`
      + `· 如果只是暂时不用，建议「停用」——历史健康度会留着。\n\n`
      + `渠道 id：${r.channel_id}`)
    if (!ok) return
    await runMutation('删除渠道', () => deleteChannel(r.channel_id))
  }, [runMutation])

  return (
    /* ⚠ **2026-09-24 统一（开发史 §10.188 第二步）**：改前这里内联写死 `fontSize: 12` 与 `gap: 8`
       ⇒ 这个面里所有"继承字号"的文字都比知识库那面**小一号**（外壳与知识库内容是 13px）。
       现在字号**不再自己定**（继承外壳 `.ks-kb` 的 `--ks-fs-base`），间距走同一套 token。
       ⚠ 这一层 div 留着（没有 `.ks-kb >` 直接子选择器，多这一层不影响观感；
         知识库那面的内容也在这同一层之下）。 */
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--ks-space-2)' }}>
      {/* 顶部常驻栏（业主 2026-09-22：「就在渠道台账顶部做一个常驻栏，就展示最新情况」）：
          一句人话动态 + 一个钮收详情（巡检/公告/导出都进折叠，默认合上——主面零字墙）。
          ⚠ **2026-09-24 统一（§10.188 第二步）**：改前这里自己画框（0.5px 边框 + 圆角 6 +
          内联内边距 + 内联小钮），与知识库那面的提示行（.ks-kb-banner）不是一套；
          现在用**同一个类** + 宿主 Button（size=sm，与知识库那面的按钮同高）。 */}
      <div className="ks-kb-banner">
        <span style={{ flex: 1, minWidth: 0 }}>{news === '' ? '📢 读取最新动态…' : news}</span>
        <Button variant="outline" size="sm" onClick={() => setShowDetail((v) => !v)}>
          {showDetail ? '收起详情' : '巡检与公告详情'}
        </Button>
      </div>
      {showDetail && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* 巡检与公告合一（业主："每日巡检不就是立即探测吗…留一个按钮"）：
              主面工具行的「立即巡检」=唯一动作钮；这两块是它的**详情面**（自动巡检开关、
              关注标准三色明细、公告源管理、导出），默认收起不占地方。 */}
          <details open={false}>
            <summary style={{ cursor: 'pointer' }}>巡检详情（自动巡检开关 · 关注标准三色 · 导出）</summary>
            <KsInspectionPanel openedOnce={showDetail} />
          </details>
          <details open={false}>
            <summary style={{ cursor: 'pointer' }}>公告详情（公告源管理 · 最近公告 · 导出）</summary>
            <KsAnnounceSourcesSection openedOnce={showDetail} />
          </details>
        </div>
      )}
      {/* 工具行：筛选 + 动作钮。
          ⚠ **2026-09-24 统一（§10.188 第二步）**：改前是自己写的一排内联样式按钮
          （11.5px 字号、自定内边距 ⇒ 比知识库那面的按钮小一圈）。现在容器用**知识库那面同一个类**
          `.ks-kb-row`、按钮一律走宿主 `Button size="sm"`、两个原生下拉走**共用类** `.ks-sel`
          （原生下拉没有宿主原语，见样式表里那段说明）。 */}
      <div className="ks-kb-row">
        <select className="ks-sel" value={cat} onChange={(e) => setCat(e.target.value)}
          title="按类别筛选（服务端筛选）">
          <option value="">全部类别</option>
          {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="ks-sel" value={state} onChange={(e) => setState(e.target.value)}
          title="按有效性筛选（服务端筛选）">
          <option value="">全部有效性</option>
          {Object.entries(STATE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <Button variant="outline" size="sm" disabled={busy} onClick={() => void load()}>
          {busy ? '读取中…' : '⟳ 刷新'}
        </Button>
        <Button variant="outline" size="sm" disabled={probeBusy} onClick={probe}
          title="立即巡检：对配了检查口径的渠道各探一遍，实测今天能不能抓（约 10–30 秒）。与每日自动巡检是同一件事——这是立刻跑一次">
          {probeBusy ? '巡检中…（约 10–30 秒）' : '🩺 立即巡检'}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setAdding((v) => !v)}
          title="人工加一条渠道：引擎侧已落（R6d），界面侧这一步是 R6f">
          {adding ? '× 取消新增' : '＋ 新增渠道'}
        </Button>
        <Button variant="outline" size="sm" data-ks-channels-ai-fix onClick={() => {
          const prompt = buildChannelFixPrompt(data?.items ?? rows, data?.summary)
          void copyTextToClipboard(prompt).then((ok) => {
            setNotice(ok
              ? '提示词已复制——粘到对话框发出去，AI 会逐条诊断失效原因、给修法、说清要你帮什么。'
              : '复制失败：浏览器拒绝了剪贴板权限。请手动全选下方提示词复制。')
          })
        }}
          title="生成一段诊断提示词并复制：粘到对话框发出去，AI 会诊断每条失效渠道为什么坏、怎么修、怎么长期有效、要你帮什么、用什么工具修">
          🤖 AI 一键解决
        </Button>
      </div>

      {/* 人工新增：只收「人能知道」的三样（名称/链接/备注）。
          类别、接线、健康度**不在表单里**——那些要么由引擎判定、要么由探针产出；
          人在这里填了只会得到 422（引擎的 loud 拒绝），不如不摆这个坑。
          ⚠ **2026-09-24 统一（§10.188 第二步）**：改前三个输入框是原生 `<input>` + 自己那套内联样式
          （字号 11、自定内边距），提交钮也是自己画的小钮 ⇒ 与知识库那面的
          "新建/改名"面板（宿主 Input + 宿主 Button size=sm）不是一个观感。
          现在一律走宿主原语（`.ks-kb-hint` 是提示文字那一档）。 */}
      {adding && (
        <div className="ks-kb-row" style={{ border: '1px dashed var(--dsw-alias-border-l2)',
                                            borderRadius: 'var(--ks-r-md)', padding: 'var(--ks-space-2)' }}>
          <Input value={newName} onChange={(e) => setNewName(e.target.value)}
            placeholder="渠道名称（必填，例如：某省住建厅公告）" style={{ minWidth: 220 }}
            aria-label="渠道名称" />
          <Input value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
            placeholder="链接（https://…）" style={{ minWidth: 240 }}
            aria-label="渠道链接" />
          <Input value={newNote} onChange={(e) => setNewNote(e.target.value)}
            placeholder="备注（为什么加它 / 谁维护）" style={{ minWidth: 200 }}
            aria-label="备注" />
          <Button variant="primary" size="sm" disabled={mutating || newName.trim() === ''}
            onClick={() => void submitCreate()}>
            {mutating ? '提交中…' : '提交'}
          </Button>
          <span className="ks-kb-hint">
            新增的渠道默认：接线 `user`（是人加的）、有效性 `unverified`（人工录入≠已核实）、
            探针状态 `unknown`（还没探过）。
          </span>
        </div>
      )}

      {notice !== '' && (
        <p role="status" style={{ margin: 0, color: GRAY }}>{notice}</p>
      )}
      {error !== '' && (
        <p role="alert" style={{ margin: 0, color: '#c0392b' }}>
          读取失败：{error}
          <br />
          <span style={{ color: FAINT }}>
            （渠道库端点要宿主/引擎重启后才在线；若刚更新过而没重启，这里就会报错。）
          </span>
        </p>
      )}

      {data && rows.length === 0 && <p style={{ color: GRAY, margin: 0 }}>没有符合条件的渠道。</p>}

      {/* 正装（2026-09-22 业主打回手搓后改）：**与知识库管理同一套机制**——
          目录层直接用 .ks-list-dirs（同列同格同款行按钮），文件层=第四层 .ks-list-chans
          （复用 .ks-list/.ks-lhead/.ks-item，只给一条自己的 --ks-cols），面包屑=kbListUi 共用件。 */}
      {rows.length > 0 && (
        <div className="ks-split">
          {/* 批E2（2026-09-23 业主点单）：左侧目录树——左边逐层点开看、要操作才用右边。
              ⚠ **2026-09-24 统一（开发史 §10.188 第二步）**：改前这里用的是自己那套
              `.ks-tree-item/.ks-tree-sub/.ks-tree-on`（样式表里另有一段"渠道库左树的行样式"，
              行高 28px、字号 12px、选中拿边框色当背景），与知识库左树的
              `.ks-tree-row`（行高 44px、字号继承 13px、选中走宿主 interactive 底色 + 2px 标记条、
              data-depth 缩进 token、带 caret）**长得不一样**。现在**逐字用知识库那一套 markup 与类**，
              那三个自己造的行类随之删除（样式表里也删掉，不留死样式）。
              树=单位性质→网站两级；点叶即达（右侧跟着换层）。 */}
          <aside className="ks-kb-tree" aria-label="渠道库目录">
            <div className="ks-tree-node">
              <div className="ks-tree-row"
                data-on={orgSel === null && siteSel === null ? 'true' : 'false'}
                data-depth={0}
                aria-current={orgSel === null && siteSel === null ? 'true' : undefined}>
                <span className="ks-tree-caret ks-tree-caret-leaf" aria-hidden="true" />
                <button type="button" className="ks-tree-name"
                  title={`渠道库（全部 ${String(rows.length)} 条）`}
                  onClick={() => { setOrgSel(null); setSiteSel(null) }}>
                  <IconFolderOpenOutlineRegular size={16} />
                  <span className="ks-tree-label">渠道库</span>
                </button>
                <span className="ks-tree-count">{rows.length}</span>
              </div>
            </div>
            {groupRowsByOrgKind(rows).map((g) => {
              const sites = groupRowsBySite(g.rows).sites
              /* 有的站点是"同站多页"⇒ 它下面还有一层；全是单页站 ⇒ 这一类没有下级（caret 用叶子位）。 */
              const hasKids = sites.length > 0
              const expanded = openKinds.has(g.key) || orgSel === g.key
              const on = orgSel === g.key && siteSel === null
              return (
                <div className="ks-tree-node" key={g.key}>
                  <div className="ks-tree-row"
                    data-on={on ? 'true' : 'false'}
                    data-depth={1}
                    aria-current={on ? 'true' : undefined}>
                    {hasKids ? (
                      <button type="button" className="ks-tree-caret"
                        aria-label={`${expanded ? '收起' : '展开'}「${g.label}」下面的站点`}
                        aria-expanded={expanded}
                        title={expanded ? '收起' : '展开'}
                        onClick={() => { toggleKind(g.key) }}>
                        {expanded ? <IconChevronDownOutlineRegular size={16} /> : <IconChevronRightOutlineRegular size={16} />}
                      </button>
                    ) : (
                      <span className="ks-tree-caret ks-tree-caret-leaf" aria-hidden="true" />
                    )}
                    <button type="button" className="ks-tree-name"
                      title={`${g.label}（${String(g.rows.length)} 条）`}
                      onClick={() => {
                        setOrgSel(g.key); setSiteSel(null)
                        setOpenKinds((prev) => new Set(prev).add(g.key))
                      }}>
                      <IconFolderOpenOutlineRegular size={16} />
                      <span className="ks-tree-label">{g.label}</span>
                    </button>
                    <span className="ks-tree-count">{g.rows.length}</span>
                  </div>
                  {expanded && sites.map((s) => {
                    const son = siteSel === s.host && orgSel === g.key
                    return (
                      <div className="ks-tree-row" key={s.host}
                        data-on={son ? 'true' : 'false'}
                        data-depth={2}
                        aria-current={son ? 'true' : undefined}>
                        <span className="ks-tree-caret ks-tree-caret-leaf" aria-hidden="true" />
                        <button type="button" className="ks-tree-name"
                          title={`${s.label}（${String(s.rows.length)} 条）`}
                          onClick={() => { setOrgSel(g.key); setSiteSel(s.host) }}>
                          <span className="ks-tree-label">{s.label}</span>
                        </button>
                        <span className="ks-tree-count">{s.rows.length}</span>
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </aside>
          <div className="ks-main">
          <KsCrumb
            items={q.trim() !== ''
              ? [{ name: '渠道库' }, { name: `搜索「${q.trim()}」` }]
              : orgSel === null
                ? [{ name: '渠道库' }]
                : siteSel === null
                  ? [{ name: '渠道库', onGo: () => setOrgSel(null) },
                     { name: ORG_KIND_LABEL[orgSel] ?? orgSel }]
                  : [{ name: '渠道库', onGo: () => { setOrgSel(null); setSiteSel(null) } },
                     { name: ORG_KIND_LABEL[orgSel] ?? orgSel, onGo: () => { setSiteSel(null) } },
                     { name: siteSel }]}
            n={crumbN} />
          {/* 摘要行 + 搜索框：**位置与知识库那一面逐字对齐** —— 面包屑下面先是这一行，
              再是 `.ks-search` 搜索框，然后才是列表。
              ⚠ **2026-09-24 统一（§10.188 第二步）**：改前这两样都在右栏**外面**——
              摘要是一行灰字、搜索框横跨整页且只有 21px 高（知识库那面的搜索框在右栏里、
              带放大镜图标、34px 高）⇒ 两个面一眼就不一样。
              ⚠ 这一行**不是** `.ks-list-cap`：那个类是"当前文件夹名 + 导出效力总览 + 在此范围内提问 +
              计数"专用的，跑起来有一条"这一行必须有控件、且成员不许互相压字"的判据
              （业主那次"导出效力总览压在知识库上"就是它抓的）。渠道库这行是两个纯文字片段，
              套上去会**当场假红**（实测：ctrlCount=0 判"什么都没量到" + span 与内层 b 被判压字）
              ⇒ 用 `.ks-kb-banner`（知识库那面提示行的类）。 */}
          {s && (
            /* ⚠ 四个数**保持 `<b>` 加粗**：`smoke-catalog-ui.mjs` 有一条源码级判据钉着
               "能用 <b>{s.by_state.ok…" 这一组字面量（"摘要＝用户语言四态、旧接线话术回潮就红"）。
               本批只是把这一行搬进右栏 + 换共用类，**不动那条判据**（动它要另开一笔并说明理由）。 */
            <div className="ks-kb-banner">
              <span>
                台账 <b>{s.total}</b> 条 · 能用 <b>{s.by_state.ok ?? 0}</b> 条 ·
                不太行 <b>{s.by_state.suspicious ?? 0}</b> 条 ·
                不能用 <b>{s.by_state.down ?? 0}</b> 条 ·
                没试过 <b>{s.by_state.unknown ?? 0}</b> 条
              </span>
              <span style={{ marginLeft: 'auto' }}>
                {q.trim() !== ''
                  ? `命中 ${String(viewRows.length)} 条`
                  : '左边按「单位性质」分类；点一类看它的渠道。'}
              </span>
            </div>
          )}
          <span className="ks-search">
            <Input icon={<IconSearchOutlineRegular size={16} />} value={q}
              placeholder="搜网站名字 / 网站域名…"
              aria-label="搜渠道（名字或域名）"
              onChange={(e) => { setQ(e.target.value) }} />
          </span>
          {/* 批E1-2（2026-09-23）：「网站」一层——同站多页=网站文件夹（点开看站内页面行），
              单页站=下方普通行（文件夹与行共存，同知识库逻辑）。 */}
          {orgSel !== null && siteSel === null && q.trim() === '' && (
            <div className="ks-list ks-list-dirs ks-dirs">
              <KsListHead cols={DIR_COLS} />
              {groupRowsBySite(viewRows).sites.map((s) => (
                <div key={s.host} className="ks-item ks-dir-row"
                  onClick={(e) => {
                    const t = e.target as (HTMLElement | null)
                    if (t === null || typeof t.closest !== 'function') return
                    if (t.closest('button,input,a,[role=menuitem],[role=menu]') !== null) return
                    setSiteSel(s.host)
                  }}>
                  <div className="ks-cell ks-col-dpick" />
                  <div className="ks-cell ks-col-dname">
                    <button type="button" className="ks-dir-open"
                      title={`进入网站「${s.label}」（这个网站有 ${String(s.rows.length)} 个页面）`}
                      aria-label={`进入网站「${s.label}」，共 ${String(s.rows.length)} 个页面`}
                      onClick={() => setSiteSel(s.host)}>
                      <span className="ks-fileico" title="网站"><IconFolderOpenOutlineRegular size={16} /></span>
                      <span className="ks-dir-name" title={s.label}>{s.label}</span>
                      <span className="ks-dir-go"><IconChevronRightOutlineRegular size={16} /></span>
                    </button>
                  </div>
                  <div className="ks-cell ks-col-dcount">
                    <span className="ks-kb-badge">{s.rows.length} 页</span>
                  </div>
                  <div className="ks-cell ks-col-dmore" />
                </div>
              ))}
            </div>
          )}
          {orgSel === null && q.trim() === '' ? (
            <div className="ks-list ks-list-dirs ks-dirs">
              <KsListHead cols={DIR_COLS} />
              {groupRowsByOrgKind(rows).map((g) => (
                /* 逐格照抄知识库 dirCell 真身：进入钮=真 button + 文件夹图标 + 图标箭头、
                   条数=ks-kb-badge 胶囊、行=div 整行可点。勾选框/⋮ 未搬：分组没有对应动作，
                   摆上去就是假按钮（红线）——要它们先定动作（如批量停用）。 */
                <div key={g.key} className="ks-item ks-dir-row"
                  onClick={(e) => {
                    const t = e.target as (HTMLElement | null)
                    if (t === null || typeof t.closest !== 'function') return
                    if (t.closest('button,input,a,[role=menuitem],[role=menu]') !== null) return
                    setOrgSel(g.key)
                  }}>
                  <div className="ks-cell ks-col-dpick" />
                  <div className="ks-cell ks-col-dname">
                    <button type="button" className="ks-dir-open"
                      title={`进入「${g.label}」（共 ${String(g.rows.length)} 条）`}
                      aria-label={`进入分类「${g.label}」，共 ${String(g.rows.length)} 条`}
                      onClick={() => setOrgSel(g.key)}>
                      <span className="ks-fileico" title="分类"><IconFolderOpenOutlineRegular size={16} /></span>
                      <span className="ks-dir-name" title={g.label}>{g.label}</span>
                      <span className="ks-dir-go"><IconChevronRightOutlineRegular size={16} /></span>
                    </button>
                  </div>
                  <div className="ks-cell ks-col-dcount">
                    <span className="ks-kb-badge">{g.rows.length} 条</span>
                  </div>
                  <div className="ks-cell ks-col-dmore" />
                </div>
              ))}
            </div>
          ) : (
            <div className="ks-list ks-list-chans">
              <KsListHead cols={CH_COLS} />
              {(siteSel !== null
                ? (groupRowsBySite(viewRows).sites.find((s) => s.host === siteSel)?.rows ?? [])
                : (orgSel !== null && q.trim() === '' ? groupRowsBySite(viewRows).solos : viewRows)
              ).map((r) => (
                <div key={r.channel_id} className="ks-item">
                  <span className="ks-cell ks-col-chan">
                    <span className="ks-chan-name" title={r.note ?? undefined}>
                      {r.name}{r.enabled === 0 ? '（已停用）' : ''}
                    </span>
                    {r.url
                      ? <a className="ks-chan-open" href={r.url.split(/[（\s]/)[0]} target="_blank"
                          rel="noreferrer noopener">打开</a>
                      : null}
                  </span>
                  <span className="ks-cell ks-col-cstate">{STATE_LABEL[r.state] ?? r.state}
                    {r.state === 'unknown' && r.has_probe_target === false
                      ? <span style={{ color: FAINT }}>（没配测试）</span>
                      : null}
                  </span>
                  <span className="ks-cell ks-col-cdate" title={r.last_ok_at ?? ''}>
                    {describeWhen(r.last_ok_at)}
                  </span>
                  <span className="ks-cell ks-col-cissue"
                    style={{ color: r.last_error ? '#c0392b' : FAINT }}>
                    {r.last_error ? r.last_error.slice(0, 40) : '—'}
                  </span>
                  <span className="ks-cell ks-col-cact">
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void toggleEnabled(r)}>
                      {r.enabled === 0 ? '启用' : '停用'}
                    </button>
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void editOrgKind(r)}>改分类</button>
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void tryChannel(r)}
                      title="试一试：拉这条渠道的「已知文件」（样本链接+期望标准号）——真下载/识别出来=渠道算数。首次点击会先配样本">
                      试一试
                    </button>
                    <button type="button" disabled={mutating} style={{ ...$mini, color: '#c0392b' }}
                      onClick={() => void remove(r)}>删除</button>
                  </span>
                </div>
              ))}
            </div>
          )}
          </div>
        </div>
      )}

      {/* 字墙拆了（业主 2026-09-22："字还很多根本搞不懂"）：语义解释收进默认合上的
          「这些标记是什么意思？」，全换人话；主面零解释文字。 */}
      <details style={{ color: FAINT }}>
        <summary style={{ cursor: 'pointer' }}>这些标记是什么意思？</summary>
        <ul style={{ margin: '4px 0 0', paddingLeft: 18, lineHeight: 1.7 }}>
          <li>🟢 能抓 / 🟡 不太行 / 🔴 不能用 / ⚪ 没试过：这是今天实测的结果，不是永久标签。</li>
          <li>「没试过」= 还没测过，不等于没问题；想测就点「立即巡检」。</li>
          <li>「（没配测试）」= 这条渠道按设计就不用测（比如代码仓库类）。</li>
          <li>「上次好用」列是北京时间；鼠标放上去看准确时刻。</li>
        </ul>
      </details>
    </div>
  )
}

/** 行内维护按钮（比工具行的按钮更小：一列三颗，不能撑破表格）。 */
const $mini: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 3, padding: '1px 6px', fontSize: 11, cursor: 'pointer', marginRight: 3,
}

/* ⚠ `$select` 与 `$btn` **已删（2026-09-24 统一，§10.188 第二步）**：工具行与新增表单都换成了
   宿主的 Button(size=sm) / Input 与共用类 `.ks-sel` ⇒ 这两个自定样式对象不再有使用者。
   留着"没人用的样式对象"正是下次有人照抄出一套新观感的入口。
   ⚠ 同文件里 `$th` / `$td` / `$trWarn` 是**早先**（表格改 `.ks-list` 之前）留下的死对象，
   不是本批造成的 —— 只登记，不在本批顺手删（跨轮次发现只登记）。 */

const $th: React.CSSProperties = {
  borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)',
  padding: '3px 6px', whiteSpace: 'nowrap', fontWeight: 600,
}

const $td: React.CSSProperties = {
  borderBottom: '1px solid var(--dsw-alias-border-l1, #f2f2f2)',
  padding: '3px 6px', verticalAlign: 'top',
}

const $trWarn: React.CSSProperties = {
  background: 'var(--dsw-alias-bg-layer-1, #fff8f8)',
}

export default KsChannelsPanel
