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
import { Fragment, useCallback, useEffect, useState } from 'react'

import {
  createChannel,
  deleteChannel,
  fetchChannels,
  runChannelProbe,
  setChannelEnabled,
  updateChannel,
  type KsChannelList,
  type KsChannelRecord,
} from './api'

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

/** 按类别分组（分类批，2026-09-22）：组序 = CATEGORY_LABEL 声明序，未知类别收尾。
 *  组内保持传入顺序（= sortChannels 的注意力序）。纯函数，判据直接钉。 */
export function groupRowsByCategory(
  rows: readonly KsChannelRecord[],
): Array<{ key: string; label: string; rows: KsChannelRecord[] }> {
  const order = Object.keys(CATEGORY_LABEL)
  const groups = new Map<string, KsChannelRecord[]>()
  for (const r of rows) {
    const arr = groups.get(r.category) ?? []
    arr.push(r)
    groups.set(r.category, arr)
  }
  const keys = [...groups.keys()].sort((a, b) => {
    const ia = order.indexOf(a)
    const ib = order.indexOf(b)
    return (ia < 0 ? order.length : ia) - (ib < 0 ? order.length : ib) || a.localeCompare(b)
  })
  return keys.map((k) => ({ key: k, label: CATEGORY_LABEL[k] ?? k, rows: groups.get(k) ?? [] }))
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
    '1. **诊断为什么失败**：用 web_fetch 实测链接现状（HTTP 码/落地页/是否改版/是否要登录或验证码）；',
    '   再读我们的适配器代码判断是"站点变了"还是"我们的解析器坏了"（两者修法完全不同）。',
    '2. **怎么修才行**：给具体方案——换端点/改解析/改请求头/换适配策略，说明改动会落在哪个文件。',
    '3. **怎么长期有效**：修完怎么防止再坏（语义探针期望、回归用例、探测告警口径、负缓存）。',
    '4. **需要用户怎么协助**：如实列出只有人能做的事（人工验证/注册账号/过验证码/授权/确认口径）——不要自己替用户决定。',
    '5. **修复时用什么工具**：web_search/web_fetch（实测）、引擎探测端点 `POST /api/v1/channels/probe`（语义探针）、',
    '   测试 `tests/test_channel_repo.py` / `tests/test_ledger_chain.py`、门禁 `pwsh -File scripts/run-gates.ps1 -Quick`。',
    '',
    '## 边界与纪律',
    '- 先读 `docs/CHANNEL-COVERAGE-PLAN.md`（渠道覆盖方案与轮次台账）再动手；适配器在 `src/core/laws/`（按渠道分文件）。',
    '- 修不动/证据不足的**如实说修不动**，登记原因，不要硬编一个"应该能用"的方案。',
    '- 每步小提交，消息写清"改了什么/为什么/边界"；产出物只出 Markdown。',
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

  const editNote = useCallback(async (r: KsChannelRecord): Promise<void> => {
    const next = window.prompt(`改备注（${r.name}）\n留空则清空该字段：`, r.note ?? '')
    if (next === null) return                      // 取消
    await runMutation('改备注', () => updateChannel(r.channel_id, { note: next }))
  }, [runMutation])

  /** 改号段（§11.0 R7）：**号段→渠道**是业主可维护的事实——链按它做加法（只加尾巴）。 */
  const editSegments = useCallback(async (r: KsChannelRecord): Promise<void> => {
    const next = window.prompt(
      `改号段（${r.name}）——这条渠道管哪些标准号前缀？\n`
      + `多个用逗号分开；号段里的空格有意义，别用空格当分隔符（例：HJ, GB 50, T/）\n`
      + `注意：区分大小写（写 hj 不会命中 HJ），写错会静默失效\n`
      + `留空则清空（= 不靠号段进链）：`,
      parseSegments(r.segments_json).join(', '))
    if (next === null) return                      // 取消
    // ⚠ **只用逗号/顿号分隔，不用空白**：`GB 50` 里的空格是号段的一部分，
    //   按空白拆会把一个号段拆成两个（`GB` + `50`），而 `50` 会命中一堆无关的号。
    const parts = next.split(/[,，、]+/).map((s) => s.trim()).filter((s) => s !== '')
    await runMutation('改号段',
      () => updateChannel(r.channel_id, { segments_json: parts }))
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
      {/* 摘要：**两个数都显示**（台账条数 ≠ 能力条数）*/}
      {s && (
        <div style={{ color: GRAY, lineHeight: 1.7 }}>
          台账 <b>{s.total}</b> 条 · 能干活（已接线）<b>{s.by_wiring.wired ?? 0}</b> 条 ·
          已知失效 <b>{s.by_wiring.broken ?? 0}</b> 条 · 仅登记 <b>{s.by_wiring.seed_only ?? 0}</b> 条
          <br />
          已实测有效性：🟢 {s.by_state.ok ?? 0} · 🟡 {s.by_state.suspicious ?? 0} · 🔴 {s.by_state.down ?? 0} · ⚪ 未探 {s.by_state.unknown ?? 0}
          <br />
          <span style={{ color: FAINT }}>
            ⚠「接线」是我们的代码接没接上（巡检会不会调用它）；「有效性」是渠道本身今天能不能抓。
            两者是两根轴：站点活着而我们的解析器坏了（或反之）都会发生，所以分列显示。
          </span>
        </div>
      )}

      {/* 工具行：筛选 + 立刻探测 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={cat} onChange={(e) => setCat(e.target.value)} style={$select}
          title="按类别筛选（服务端筛选）">
          <option value="">全部类别</option>
          {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={state} onChange={(e) => setState(e.target.value)} style={$select}
          title="按有效性筛选（服务端筛选）">
          <option value="">全部有效性</option>
          {Object.entries(STATE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button type="button" onClick={() => void load()} disabled={busy} style={$btn}>
          {busy ? '读取中…' : '⟳ 刷新'}
        </button>
        <button type="button" onClick={probe} disabled={probeBusy} style={$btn}
          title="对配了探针目标的渠道各发一次请求，实测它们今天能不能抓（约 10–30 秒）">
          {probeBusy ? '探测中…（约 10–30 秒）' : '🩺 立即探测'}
        </button>
        <button type="button" onClick={() => setAdding((v) => !v)} style={$btn}
          title="人工加一条渠道：引擎侧已落（R6d），界面侧这一步是 R6f">
          {adding ? '× 取消新增' : '＋ 新增渠道'}
        </button>
        <button type="button" data-ks-channels-ai-fix onClick={() => {
          const prompt = buildChannelFixPrompt(data?.items ?? rows, data?.summary)
          void copyTextToClipboard(prompt).then((ok) => {
            setNotice(ok
              ? '提示词已复制——粘到对话框发出去，AI 会逐条诊断失效原因、给修法、说清要你帮什么。'
              : '复制失败：浏览器拒绝了剪贴板权限。请手动全选下方提示词复制。')
          })
        }} style={{ ...$btn, borderColor: 'var(--dsw-alias-state-business-primary, #1565c0)' }}
          title="生成一段诊断提示词并复制：粘到对话框发出去，AI 会诊断每条失效渠道为什么坏、怎么修、怎么长期有效、要你帮什么、用什么工具修">
          🤖 AI 一键解决
        </button>
      </div>

      {/* 人工新增：只收「人能知道」的三样（名称/链接/备注）。
          类别、接线、健康度**不在表单里**——那些要么由引擎判定、要么由探针产出；
          人在这里填了只会得到 422（引擎的 loud 拒绝），不如不摆这个坑。 */}
      {adding && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center',
                      border: `1px dashed ${LINE}`, borderRadius: 6, padding: 6 }}>
          <input value={newName} onChange={(e) => setNewName(e.target.value)}
            placeholder="渠道名称（必填，例如：某省住建厅公告）" style={{ ...$select, minWidth: 220 }}
            aria-label="渠道名称" />
          <input value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
            placeholder="链接（https://…）" style={{ ...$select, minWidth: 240 }}
            aria-label="渠道链接" />
          <input value={newNote} onChange={(e) => setNewNote(e.target.value)}
            placeholder="备注（为什么加它 / 谁维护）" style={{ ...$select, minWidth: 200 }}
            aria-label="备注" />
          <button type="button" onClick={() => void submitCreate()} disabled={mutating || newName.trim() === ''}
            style={$btn}>
            {mutating ? '提交中…' : '提交'}
          </button>
          <span style={{ color: FAINT }}>
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
            （渠道台账端点要宿主/引擎重启后才在线；若刚更新过而没重启，这里就会报错。）
          </span>
        </p>
      )}

      {data && rows.length === 0 && <p style={{ color: GRAY, margin: 0 }}>没有符合条件的渠道。</p>}

      {rows.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 11.5 }}>
            <thead>
              <tr style={{ color: FAINT, textAlign: 'left' }}>
                <th style={$th}>渠道</th>
                <th style={$th}>类别</th>
                <th style={$th}>接线</th>
                <th style={$th}>号段</th>
                <th style={$th}>有效性</th>
                <th style={$th}>上次成功(UTC)</th>
                <th style={$th}>失败原因</th>
                <th style={$th}>链接</th>
                <th style={$th}>维护</th>
              </tr>
            </thead>
            <tbody>
              {/* 分类（2026-09-22）：按类别分组展示——组序=类别声明序、组内=注意力序。 */}
              {groupRowsByCategory(rows).map((g) => (
                <Fragment key={g.key}>
                  <tr>
                    <td colSpan={9} style={{ ...$td, fontWeight: 600,
                      background: 'var(--dsw-alias-bg-layer-2, #f5f5f5)' }}>
                      {g.label}（{g.rows.length} 条）
                    </td>
                  </tr>
                  {g.rows.map((r) => (
                <tr key={r.channel_id} style={needsAttention(r) ? $trWarn : undefined}>
                  <td style={$td} title={r.note ?? undefined}>
                    {r.name}
                    {r.enabled === 0 ? <span style={{ color: FAINT }}>（已停用）</span> : null}
                  </td>
                  <td style={$td}>{CATEGORY_LABEL[r.category] ?? r.category}
                    {r.category_raw && r.category_raw !== r.category
                      ? <span style={{ color: FAINT }} title={`调研原文：${r.category_raw}`}>*</span>
                      : null}
                  </td>
                  <td style={$td} title={r.wiring === 'broken' ? (r.note ?? '') : undefined}>
                    {WIRING_LABEL[r.wiring] ?? r.wiring}
                  </td>
                  <td style={{ ...$td, maxWidth: 150 }}
                    title={'链按号段做加法（只加尾巴、不改顺序）：这些前缀命中的标准号会多问这条渠道一根。'
                      + '留空 = 不靠号段进链。'}>
                    {parseSegments(r.segments_json).length > 0
                      ? parseSegments(r.segments_json).map((s) => (
                        <code key={s} style={{ marginRight: 4 }}>{s}</code>
                      ))
                      : <span style={{ color: FAINT }}>—</span>}
                  </td>
                  <td style={$td}>{STATE_LABEL[r.state] ?? r.state}
                    {r.state === 'unknown' && r.has_probe_target === false
                      ? <span style={{ color: FAINT }} title="该渠道没有探针目标（代码仓库/我方代码通路等），不是'还没轮到它'">
                          （无探针）
                        </span>
                      : null}
                    {r.latency_ms != null ? <span style={{ color: FAINT }}> {r.latency_ms}ms</span> : null}
                  </td>
                  <td style={$td} title={r.last_ok_at ?? ''}>
                    {describeWhen(r.last_ok_at)}
                    {r.last_try_at && r.last_try_at !== r.last_ok_at
                      ? <span style={{ color: FAINT }}>（试过 {describeWhen(r.last_try_at)}）</span>
                      : null}
                  </td>
                  <td style={{ ...$td, color: r.last_error ? '#c0392b' : FAINT, maxWidth: 220 }}>
                    {r.last_error_code ? <code>{r.last_error_code}</code> : '—'}
                    {r.last_error ? <span> {r.last_error.slice(0, 60)}</span> : null}
                    {r.consecutive_failures > 1
                      ? <span style={{ color: FAINT }}>（连续 {r.consecutive_failures} 次）</span>
                      : null}
                  </td>
                  <td style={$td}>
                    {r.url
                      ? <a href={r.url.split(/[（\s]/)[0]} target="_blank" rel="noreferrer noopener"
                          style={{ color: 'var(--dsw-alias-link, #1565c0)' }}>打开</a>
                      : '—'}
                  </td>
                  <td style={{ ...$td, whiteSpace: 'nowrap' }}>
                    {/* 人工维护四件事：启停（停用不删）/ 改备注 / 删除（高风险，先确认） */}
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void toggleEnabled(r)}
                      title={r.enabled === 0 ? '重新启用这条渠道' : '停用（保留历史健康度，不删条目）'}>
                      {r.enabled === 0 ? '启用' : '停用'}
                    </button>
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void editNote(r)} title="改备注（会写审计痕迹）">
                      改备注
                    </button>
                    <button type="button" disabled={mutating} style={$mini}
                      onClick={() => void editSegments(r)}
                      title="改号段：这条渠道管哪些标准号前缀（逗号分开；会写审计痕迹）">
                      改号段
                    </button>
                    <button type="button" disabled={mutating} style={{ ...$mini, color: '#c0392b' }}
                      onClick={() => void remove(r)}
                      title="删除条目（引擎的审计痕迹里保留删除前整行；一般建议用「停用」）">
                      删除
                    </button>
                  </td>
                  </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ margin: 0, color: FAINT, lineHeight: 1.6 }}>
        时间列是 UTC（库内 `datetime('now')` 的既有口径），旁边按"多久之前"显示。
        「立即探测」只探配了探针目标的渠道（锚点必须实测看到过，不许凭想象写）；
        没配的显示 ⚪ 未探 —— 那是"还没测过"，不是"测过了没问题"；
        标了「（无探针）」的是按设计就没有探针目标（代码仓库、我方代码通路等），
        与"还没轮到它"不是一回事；
        还有一种 ⚪ 是能连通、但我们没给它配语义期望（失败原因列写 `no_anchor_configured`）
        —— 它同样不算「可抓」，但也不是欠账。
      </p>
    </div>
  )
}

const $select: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4, padding: '2px 6px', fontSize: 11.5,
}

/** 行内维护按钮（比工具行的按钮更小：一列三颗，不能撑破表格）。 */
const $mini: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 3, padding: '1px 6px', fontSize: 11, cursor: 'pointer', marginRight: 3,
}

const $btn: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4, padding: '2px 10px', fontSize: 11.5, cursor: 'pointer',
}

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
