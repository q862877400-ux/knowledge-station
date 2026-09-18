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
 * ⚠ R1 的实测教训（G5/G6）：13 个适配器只有 8 个在链上；在链上的 `web`/`govcn` 两根兜底棒
 * 在真实 HTML 下**恒 miss**（只解 mock 的 dict）。若把"接线"当"有效性"、或把"台账条数"当
 * "能力条数"，面板第一版就会虚报覆盖率。所以顶部摘要**两个数都显示**。
 *
 * ## 时间戳是 UTC（诚实标注）
 * `update_channel.last_*` 用 SQLite `datetime('now')` = **UTC**，与库内其它表一致。
 * 面板显式标注 UTC，并在前端换算成"几分钟前"，避免"04:47"被读成凌晨自动跑过。
 */
import * as React from 'react'
import { useCallback, useEffect, useState } from 'react'

import {
  fetchChannels,
  runChannelProbe,
  type KsChannelList,
  type KsChannelRecord,
} from './api'

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

export function KsChannelsPanel(props: KsChannelsPanelProps): JSX.Element {
  const { visible } = props
  const [data, setData] = useState<KsChannelList | null>(null)
  const [error, setError] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [probeBusy, setProbeBusy] = useState<boolean>(false)
  const [notice, setNotice] = useState<string>('')
  const [cat, setCat] = useState<string>('')
  const [state, setState] = useState<string>('')

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
      </div>

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
                <th style={$th}>有效性</th>
                <th style={$th}>上次成功(UTC)</th>
                <th style={$th}>失败原因</th>
                <th style={$th}>链接</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
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
                  <td style={$td}>{STATE_LABEL[r.state] ?? r.state}
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ margin: 0, color: FAINT, lineHeight: 1.6 }}>
        时间列是 UTC（库内 `datetime('now')` 的既有口径），旁边按"多久之前"显示。
        「立即探测」只探配了探针目标的渠道（锚点必须实测看到过，不许凭想象写）；
        没配的显示 ⚪ 未探 —— 那是"还没测过"，不是"测过了没问题"。
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
