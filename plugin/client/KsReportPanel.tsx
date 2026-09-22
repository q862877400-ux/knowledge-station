/**
 * ks-dsh-plugin — client/KsReportPanel.tsx
 *
 * 📋 效力报告面板（2026-11 由侧栏 tab 迁入设置栏目，用户拍板「全部进设置、
 * 类目全折叠」）：按文件目录分类体系组织的库内效力现状——**永不混排**（用户
 * 拍板）。两棵树与文件目录同构（std：CCS 大类→区间→类目；law：效力等级→
 * 部门→领域），每级头部四色小计（收起态也能扫读问题大类）；文档行带色点+
 * 状态徽标+日期（有则显），点行直达 PDF 原文（证据伪源锚点机制同 KsBookmarksTab）。
 *
 * 嵌入方式：由 KsSettingsSection 的「效力报告」<details> 类目承载——收起时
 * `visible=false`，挂载但零请求；展开（onToggle）即置 true 开始拉数据。
 * 不再是独立 tab（ks:report 注册已撤销；收藏 tab 依用户指示原样保留）。
 *
 * 数据流（设计定案两级接口——全量万级 2.5-6MB 超 payload 红线被否）：
 *   - 打开 / 切换 chips → GET /ks/report/effect（骨架+统计，30-300KB）
 *   - 展开 L4 类目 → GET /ks/report/effect/docs（瘦身行 ≤1000，按节点缓存于
 *     组件 state，切窗口即弃——报告无跨会话状态）
 * 全程零 LLM；状态口径 = resolve_status 惰性翻转（与决策 22"只引现行"同源）。
 */

import * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { evidenceUrlOf } from './ksEvidence'
import {
  exportEffectReport,
  fetchEffectDocs,
  fetchEffectReport,
  type KsEffectColors,
  type KsEffectDoc,
  type KsEffectReport,
  type KsEffectTreeNode,
  type KsEffectWindow,
} from './api'
// 2026-09-16 迁移后不再直接引用 ksEvidence 的 tab id / 点击 nonce：跳证据收敛为
// 宿主注入的 `openEvidence` 端口（见下方 props 注释）。

/** 面板 props：宿主是 KsSettingsSection 的折叠类目，不再是 better-sidebar tab。
 *  - visible：由 <details onToggle> 驱动——收起 = 挂载但零请求（懒加载门）。
 *  - openEvidence：**KS 自有的证据导航端口**（2026-09-16 迁移）——旧实现注入整个
 *    betterSidebar 服务，而该包已被官方 `dsh-client-ui-sidebar-right` 取代。
 *    省略时行仍可读，只是不可跳。 */
export interface KsReportPanelProps {
  visible: boolean
  openEvidence?: (evidenceUrl: string) => void
}

const WINDOWS: { key: KsEffectWindow; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'upcoming90', label: '即将实施 90 天' },
  { key: 'recent90', label: '最近实施 90 天' },
  { key: 'retired90', label: '近期废止 90 天' },
]

const COLOR_DOT: Record<keyof KsEffectColors, string> = {
  red: '#c0392b',
  yellow: '#b8860b',
  green: '#2e7d32',
  gray: '#888',
}

const STATUS_BADGE: Record<string, string> = {
  effective: '现行',
  upcoming: '即将实施',
  superseded: '被代替',
  withdrawn: '已废止',
}

type LoadState =
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'error'; message: string }

/** 节点唯一 key（路径 join）；L4 的 docs 缓存同 key。 */
function nodeKey(path: string[], name: string): string {
  return [...path, name].join('\u0001')
}

function ColorDots({ colors, size = 11 }: { colors: KsEffectColors; size?: number }): JSX.Element {
  const items: [keyof KsEffectColors, number][] = [
    ['red', colors.red], ['yellow', colors.yellow],
    ['green', colors.green], ['gray', colors.gray],
  ]
  return (
    <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
      {items.map(([c, n]) => n > 0 ? (
        <span key={c} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: COLOR_DOT[c], fontSize: size }}>
          <span style={{ width: size - 3, height: size - 3, borderRadius: '50%', background: COLOR_DOT[c], display: 'inline-block' }} />
          {n}
        </span>
      ) : null)}
    </span>
  )
}

function DocRow({ doc, onOpenDoc }: { doc: KsEffectDoc; onOpenDoc: (docId: string) => void }): JSX.Element {
  const color = COLOR_DOT[doc.color] ?? '#888'
  const badge = STATUS_BADGE[doc.status ?? ''] ?? '状态未知'
  const clickable = doc.doc_id !== null && doc.doc_id !== ''
  return (
    <div
      onClick={() => { if (clickable && doc.doc_id) onOpenDoc(doc.doc_id) }}
      style={{
        display: 'flex', alignItems: 'baseline', gap: 8, padding: '3px 0 3px 18px',
        fontSize: 12, cursor: clickable ? 'pointer' : 'default', flexWrap: 'wrap',
      }}
      title={clickable ? '点击在 PDF 查看器打开原文' : undefined}
    >
      <span style={{ width: 9, height: 9, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
      <span style={{ color: 'var(--dsw-alias-label-primary, #111)', fontFamily: 'monospace' }}>
        {doc.standard_no ?? '?'}
      </span>
      <span style={{ color: 'var(--dsw-alias-label-primary, #111)' }}>{doc.standard_name}</span>
      <span style={{
        fontSize: 11, color, border: `1px solid ${color}55`, borderRadius: 4,
        padding: '0 6px', lineHeight: '17px', flexShrink: 0,
      }}>{badge}</span>
      {doc.status === 'upcoming' && doc.effective_from ? (
        <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>
          实施 {doc.effective_from}（当前不可引用）
        </span>
      ) : null}
      {doc.status !== 'upcoming' && doc.effective_from ? (
        <span style={{ color: 'var(--dsw-alias-label-secondary, #888)' }}>实施 {doc.effective_from}</span>
      ) : null}
      {doc.published_at ? (
        <span style={{ color: 'var(--dsw-alias-label-secondary, #888)' }}>发布 {doc.published_at}</span>
      ) : null}
      {doc.superseded_by ? (
        <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>被代替为 {doc.superseded_by}</span>
      ) : null}
      {doc.withdrawn_date ? (
        <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>废止 {doc.withdrawn_date}</span>
      ) : null}
    </div>
  )
}

export function KsReportPanel(props: KsReportPanelProps): JSX.Element {
  const { visible, openEvidence } = props

  const abortRef = useRef<AbortController | null>(null)
  const [win, setWin] = useState<KsEffectWindow>('all')
  const [colorFilter, setColorFilter] = useState<string>('') // ''=全部；'red'|'yellow'|'green'|'gray'
  const [report, setReport] = useState<KsEffectReport | null>(null)
  const [loadState, setLoadState] = useState<LoadState>({ status: 'loading' })
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [docsCache, setDocsCache] = useState<Record<string, KsEffectDoc[]>>({})
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const load = useCallback(async (w: KsEffectWindow, color: string): Promise<void> => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac
    setLoadState({ status: 'loading' })
    try {
      const rep = await fetchEffectReport(w, ac.signal, color || undefined)
      if (ac.signal.aborted) return
      setReport(rep)
      setDocsCache({}) // 切窗口/色过滤即弃缓存（按节点缓存，报告无跨会话状态）
      setLoadState({ status: 'ready' })
    } catch (err) {
      if (ac.signal.aborted) return
      setLoadState({ status: 'error', message: err instanceof Error ? err.message : String(err) })
    }
  }, [])

  // 激活时加载；visible 关掉不重复拉。
  useEffect(() => {
    if (!visible) return
    void load(win, colorFilter)
    return () => { abortRef.current?.abort() }
  }, [visible, win, colorFilter, load])

  const onOpenDoc = useCallback((docId: string): void => {
    // 证据伪源锚点（仅 doc 参数 → PDF 查看器打开首页）；机制同 KsBookmarksTab。
    // 2026-09-16 迁移：不再注入第三方服务——宿主给 KS 自有的证据导航端口；
    // 省略时（面板单独挂载的测试场景）诚实降级为不可跳。
    // 官方 `openResource` 对恒定地址天然幂等，故旧模型"openTab + updateTab 覆写 path"
    // 的两步法不再需要（每次导航由 navigation.revision 驱动组件重载）。
    if (openEvidence === undefined) return
    // 批3-a（2026-09-22）：自拼 URL 收口 `evidenceUrlOf`（仓内唯一自拼点，两轮复核登记）——
    // 单一构造出处纪律（S2-b1 起全库只剩这一处，现清零）。
    const url = evidenceUrlOf({ doc: docId })
    if (url === null) return
    try {
      openEvidence(url)
    } catch { /* 导航失败：行仍可读，只是不跳 */ }
  }, [openEvidence])

  const toggle = (key: string): void => {
    setExpanded((prev) => {
      const next = { ...prev, [key]: !(prev[key] === true) }
      // 收起父级 = 整棵子树展开态复位（用户反馈：下级不应保留之前的展开样子）。
      // key 结构是 path join('\u0001')，子孙 key 必以父 key + 分隔符开头。
      if (next[key] === false) {
        const prefix = `${key}\u0001`
        for (const k of Object.keys(next)) {
          if (k.startsWith(prefix)) delete next[k]
        }
      }
      return next
    })
  }

  const onExport = async (): Promise<void> => {
    if (exporting) return
    setExporting(true)
    setExportError(null)
    try {
      await exportEffectReport(win, undefined, colorFilter || undefined)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err))
    } finally {
      setExporting(false)
    }
  }

  /** L4 节点展开 → 拉明细（缓存于 state）。
   *  cacheKey = 渲染层 path key（与 expanded 对齐）；params.topKey = 引擎树键
   *  （"std"/"law"——真机回归教训：曾误传顶层中文名 → E2 422 → 全显示"无文档"）。 */
  const useL4Docs = (params: { topKey: string; l2: string; l3: string; l4: string }, cacheKey: string): KsEffectDoc[] | undefined => {
    const [docs, setDocs] = useState<KsEffectDoc[] | undefined>(undefined)
    useEffect(() => {
      if (expanded[cacheKey] !== true || docsCache[cacheKey] !== undefined) return
      let alive = true
      void fetchEffectDocs({ top: params.topKey, l2: params.l2, l3: params.l3, l4: params.l4, window: win, color: colorFilter || undefined })
        .then((d) => {
          if (!alive) return
          setDocs(d.docs)
          setDocsCache((prev) => ({ ...prev, [cacheKey]: d.docs }))
        })
        .catch(() => { if (alive) setDocs([]) })
      return () => { alive = false }
    }, [cacheKey, expanded[cacheKey], docsCache[cacheKey]])
    return docsCache[cacheKey] ?? docs
  }

  const renderNode = (node: KsEffectTreeNode, path: string[], depth: number, topKey: string): React.ReactNode => {
    const key = nodeKey(path, node.name)
    const isOpen = expanded[key] ?? depth === 0 // L1 默认展开，L2+ 默认收起；均可切换
    const isLeaf = node.count !== undefined
    const children = node.items ?? []
    const rootKey = topKey || node.top || ''
    return (
      <div key={key} style={{ paddingLeft: depth === 0 ? 0 : 12 }}>
        <div
          onClick={() => toggle(key)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0',
            cursor: 'pointer', userSelect: 'none', flexWrap: 'wrap',
          }}
        >
          <span style={{ fontSize: 10, color: 'var(--dsw-alias-label-secondary, #666)', width: 10 }}>
            {isOpen ? '▾' : '▸'}
          </span>
          <span style={{
            fontWeight: depth <= 1 ? 600 : 500,
            color: 'var(--dsw-alias-label-primary, #111)', fontSize: depth <= 1 ? 13 : 12,
          }}>
            {node.name}
          </span>
          <ColorDots colors={node.colors} />
        </div>
        {isOpen && (
          <div>
            {children.map((child) => renderNode(child, [...path, node.name], depth + 1, rootKey))}
            {isLeaf && <L4Docs params={{
              topKey: rootKey, l2: path[1] ?? '', l3: path[2] ?? '', l4: node.name,
            }} cacheKey={key} useL4Docs={useL4Docs} onOpenDoc={onOpenDoc} />}
          </div>
        )}
      </div>
    )
  }

  // L4 文档行渲染为独立组件（hooks 只能在组件内——useL4Docs 是自定义 hook，
  // 不可在 renderNode 的循环里调用；拆一层组件让 hooks 合法）。
  function L4Docs({ params, cacheKey, useL4Docs: useDocs, onOpenDoc: open }: {
    params: { topKey: string; l2: string; l3: string; l4: string }
    cacheKey: string
    useL4Docs: (p: { topKey: string; l2: string; l3: string; l4: string }, cacheKey: string) => KsEffectDoc[] | undefined
    onOpenDoc: (docId: string) => void
  }): JSX.Element {
    const docs = useDocs(params, cacheKey)
    if (docs === undefined) {
      return <div style={{ padding: '2px 0 2px 30px', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #888)' }}>加载中…</div>
    }
    if (docs.length === 0) {
      return <div style={{ padding: '2px 0 2px 30px', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #888)' }}>（无文档）</div>
    }
    return (
      <div>
        {docs.map((d) => <DocRow key={d.doc_id ?? d.standard_no ?? Math.random()} doc={d} onOpenDoc={open} />)}
      </div>
    )
  }

  return (
    <div style={{ padding: '4px 0 2px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {report !== null && (
          <span style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
            共 {report.total} 部（标准 {report.std.total} · 法规 {report.law.total}）· {fmtGenerated(report.generated_at)}
          </span>
        )}
        <span style={{ flex: 1 }} />
        <button type="button" onClick={() => void load(win, colorFilter)} style={btnStyle(false)}>
          ⟳ 刷新
        </button>
      </div>

      {report !== null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0', flexWrap: 'wrap' }}>
          <ColorDots colors={report.colors} size={12} />
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '4px 0 10px', flexWrap: 'wrap' }}>
        {WINDOWS.map((w) => (
          <button
            key={w.key}
            type="button"
            onClick={() => setWin(w.key)}
            style={{
              padding: '2px 10px', borderRadius: 12, fontSize: 12, cursor: 'pointer',
              border: `1px solid ${win === w.key ? '#4a6da7' : '#c4c4c4'}`,
              background: win === w.key ? '#4a6da7' : '#ffffff',
              color: win === w.key ? '#ffffff' : '#333333',
            }}
          >
            {w.label}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        {/* 色过滤 chips（P1）：全局色清单视图——引擎 color 参数直透 */}
        {([
          ['red', '🔴 红'], ['yellow', '🟡 黄'], ['green', '🟢 绿'], ['gray', '⚪ 白'],
        ] as const).map(([c, label]) => (
          <button
            key={c}
            type="button"
            onClick={() => setColorFilter(colorFilter === c ? '' : c)}
            title={colorFilter === c ? '取消色过滤' : `只看${label.replace(/^\S+\s*/, '')}清单`}
            style={{
              padding: '2px 10px', borderRadius: 12, fontSize: 12, cursor: 'pointer',
              border: `1px solid ${colorFilter === c ? COLOR_DOT[c] : '#c4c4c4'}`,
              background: colorFilter === c ? COLOR_DOT[c] : '#ffffff',
              color: colorFilter === c ? '#ffffff' : '#333333',
            }}
          >
            {label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => void onExport()}
          disabled={exporting || loadState.status !== 'ready'}
          style={btnStyle(exporting || loadState.status !== 'ready')}
        >
          {exporting ? '导出中…' : '⬇ 导出 Excel'}
        </button>
      </div>
      {exportError !== null && (
        <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '0 0 8px' }}>{exportError}</p>
      )}

      {loadState.status === 'loading' && (
        <p style={{ color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 13 }}>
          正在聚合库内效力状态…（首次可能需要拉起引擎）
        </p>
      )}
      {loadState.status === 'error' && (
        <div>
          <p role="alert" style={{ color: '#c0392b', fontSize: 13 }}>{loadState.message}</p>
          <button type="button" onClick={() => void load(win, colorFilter)} style={btnStyle(false)}>重试</button>
        </div>
      )}
      {loadState.status === 'ready' && report !== null && report.total === 0 && (
        <p style={{ color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 13 }}>
          {win === 'all' ? '库内暂无文档' : '该时间窗内无文档（导出 Excel 可查看全量）'}
        </p>
      )}
      {loadState.status === 'ready' && report !== null && report.total > 0 && (
        <div>
          {report.tree.map((t) => renderNode(t, [], 0, t.top ?? ''))}
          <p style={{ margin: '10px 0 0', fontSize: 11, color: 'var(--dsw-alias-label-secondary, #888)' }}>
            口径注脚：状态以读取时惰性翻转（resolve_status）为准；⚪ = 库内未登记效力状态
            （与巡检「官方查无此号」语义不同）。黄行在实施日前不可引用。
          </p>
        </div>
      )}
    </div>
  )
}

function btnStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '3px 12px', borderRadius: 6, fontSize: 12,
    border: `1px solid ${disabled ? '#c4c4c4' : '#7f7f7f'}`,
    background: disabled ? '#e9e9e9' : '#ffffff',
    color: disabled ? '#5a5a5a' : '#111111',
    cursor: disabled ? 'default' : 'pointer',
  }
}

function fmtGenerated(v: string): string {
  const norm = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(v)
    ? `${v.replace(' ', 'T')}Z`
    : v
  const d = new Date(norm)
  if (Number.isNaN(d.getTime())) return v
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `生成于 ${hh}:${mi}`
}

export default KsReportPanel
