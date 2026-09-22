/**
 * ks-dsh-plugin — client/KsCapabilityPage.tsx
 *
 * 「办事台」（S2，2026-09-22 业主批准 v3 形态 —— `docs/mockups/mockup-S2-office-v3.html`）。
 *
 * ⚠ 形态更正留痕（不删旧口径）：本文件 2026-09-19 版是**卡片 + 旋钮**（当时业主指定
 * 「一个功能一张卡、点开就是它自己的设置窗」）；2026-09-22 业主看图后裁定**废弃卡片式**：
 * 「有的卡片很空有的很满、密密麻麻的字不知道应该干什么」⇒ 定稿为**一列等高菜单行
 * （两行制）+ 点行进专门页面**，设置与说明全部搬进各自页面。
 *
 * 分批落地（小步走）：
 *   S2-a1（本批）= 菜单壳 + 8 行 v3 逐字文案 + 页面骨架；**未接线**功能的按钮灰 +
 *     「还没接上」小牌 —— **不给假入口**（业主 2026-09-22："没做完的不装样子"）。
 *   S2-a2+ = 每批翻一个真功能（外发审计 → 合同审查 → 检查表/差距分析/批量问答），
 *     真入口亮起即"开始：<动词>"。条款释义连引擎实现都没有 ⇒ 菜单行灰 + 「还没有」。
 */

import { useEffect, useState, type ComponentType, type ReactNode } from 'react'

import {
  Button,
  IconClockOutline16,
  IconListPenOutline16,
  IconPlanOutline14,
  Input,
  Tag,
} from '@deepseek-ai/dsh-client-ui-primitives'

import { buildEgressMarkdown, createClausePatch, deleteClausePatch, fetchEgressAudit, importInternalPolicy, listClausePatches, runGapAnalysis, type KsClausePatch, type KsEgressAuditRecord, type KsGapResult } from './api'
import { ensureKsStyles } from './ksGuideStyles'

/** 办事台的一件活（= 一行菜单 + 一个专门页面）。 */
export interface OfficeItem {
  readonly id: string
  readonly name: string
  /** 行上的一句短语（≤12 字，v3 原型逐字）。 */
  readonly hint: string
  readonly icon: ComponentType<{ size?: number }>
  /** `not-yet` = 功能还没做完（灰行 +「还没有」，不可点）；其余可点进页面。 */
  readonly status: 'ready' | 'not-yet'
  /** 页面上的动作词（「开始：<verb>」——亮起时用；S2-a1 全部灰）。 */
  readonly verb: string
  /** 页面上的一句说明（一屏一件事的那句）。 */
  readonly pageDesc: string
}

/** 八行文案**逐字**照 v3 定稿原型（冒烟钉死；改文案 = 改判据 + 业主过目）。 */
export const OFFICE_ITEMS: readonly OfficeItem[] = [
  { id: 'gap', name: '制度差距分析', hint: '内部制度比法规缺什么', icon: IconPlanOutline14, status: 'ready', verb: '上传制度比对', pageDesc: '上传内部制度，自动对比法定要求，逐条列出缺什么，出差距报告。' },
  { id: 'fix', name: '纠错修订', hint: '标记识别错的条款，可回退', icon: IconListPenOutline16, status: 'ready', verb: '打开原文页标记', pageDesc: '发现条款识别错了，在原文页标记并提交修改；每笔修改留痕、可回退。也可以在 PDF 阅读器的条款行「⋮」里点「这条识别错了」。' },
  { id: 'egress', name: '外发审计', hint: '每次外发记录，可查可导出', icon: IconClockOutline16, status: 'ready', verb: '查看外发记录', pageDesc: '每次调用云端的完整记录，可查可导出——数据出了本机一定留痕。' },
]

/** 等高菜单行（纯组件；两行制：名称在上、短语在下。冒烟钉结构与文案）。 */
export function KsOfficeRow(props: {
  item: OfficeItem
  onOpen?: (id: string) => void
}): ReactNode {
  const { item, onOpen } = props
  const grey = item.status === 'not-yet'
  const Icon = item.icon
  return (
    <button
      type="button"
      disabled={grey}
      onClick={() => { if (!grey && onOpen !== undefined) onOpen(item.id) }}
      title={grey ? '这个功能还没有做完，做完后这里可以点' : item.pageDesc}
      className="ks-off-row"
      style={{
        display: 'flex', alignItems: 'center', gap: 10, height: 62, padding: '0 14px',
        width: '100%', background: 'none', border: 'none', cursor: grey ? 'not-allowed' : 'pointer',
        borderBottom: '0.5px solid var(--dsw-alias-border-l1)', textAlign: 'left',
        color: grey ? 'var(--dsw-alias-label-tertiary)' : 'var(--dsw-alias-label-primary)',
      }}
    >
      <span
        style={{
          width: 28, height: 28, borderRadius: 8, flex: 'none', display: 'flex',
          alignItems: 'center', justifyContent: 'center', opacity: grey ? 0.6 : 1,
          background: 'var(--dsw-alias-bg-layer-1)', border: '0.5px solid var(--dsw-alias-border-l1)',
        }}
      >
        <Icon size={14} />
      </span>
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
          {item.name}
          {grey && <Tag tone="warning">还没有</Tag>}
        </span>
        <span style={{ display: 'block', color: 'var(--dsw-alias-label-secondary)', fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {item.hint}
        </span>
      </span>
      <span style={{ color: 'var(--dsw-alias-label-tertiary)', flex: 'none' }}>{grey ? '·' : '›'}</span>
    </button>
  )
}

/**
 * 专门页面（S2-a1 = 骨架：返回 + 标题 + 一句说明 + 动作位）。
 * ⚠ 动作按钮**灰 +「还没接上」**——S2-a2 起逐个翻真；不给假入口。
 */
function OfficePage({ item, onBack }: { readonly item: OfficeItem; readonly onBack: () => void }): ReactNode {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 14px 18px' }}>
      <button
        type="button"
        onClick={onBack}
        style={{ alignSelf: 'flex-start', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--dsw-alias-state-business-primary)', fontSize: 12 }}
      >
        ‹ 返回办事台
      </button>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{item.name}</div>
      <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>{item.pageDesc}</div>
      {/* 动作行 = 真实「页内按钮行」构件（.ks-kb-row：留边适用面之一；菜单态没有它，
          判据已在 PAD_REQUIRED 按设计声明——见 ui-render-shot 那行注释）。 */}
      <div className="ks-kb-row" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button variant="outline" size="sm" disabled>
          开始：{item.verb}
        </Button>
        <Tag tone="warning">还没接上</Tag>
      </div>
      <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 11.5, lineHeight: 1.6 }}>
        这一屏的流程正在接线（下一批翻真）；接好后按钮亮起、点下去直接进流程。不给假入口。
      </div>
    </div>
  )
}

/** 外发审计页（S2-a2：**第一个翻真**的专门页——只读列表 + 导出 Markdown）。 */
export function KsEgressPage({ item, onBack }: { readonly item: OfficeItem; readonly onBack: () => void }): ReactNode {
  const [total, setTotal] = useState<number | null>(null)
  const [items, setItems] = useState<KsEgressAuditRecord[]>([])
  const [phase, setPhase] = useState<'load' | 'ready' | 'error'>('load')
  const [errText, setErrText] = useState('')

  useEffect(() => {
    let cancelled = false
    setPhase('load')
    fetchEgressAudit({ limit: 50 })
      .then((out) => {
        if (cancelled) return
        setTotal(out.total)
        setItems(out.items)
        setPhase('ready')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setErrText(error instanceof Error ? error.message : String(error))
        setPhase('error')
      })
    return () => { cancelled = true }
  }, [])

  const exportMd = (): void => {
    const md = buildEgressMarkdown(total ?? items.length, items)
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `外发审计-${new Date().toISOString().slice(0, 10)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const str = (v: unknown): string => (typeof v === 'string' ? v : v === null || v === undefined ? '' : String(v))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 14px 18px' }}>
      <button
        type="button"
        onClick={onBack}
        style={{ alignSelf: 'flex-start', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--dsw-alias-state-business-primary)', fontSize: 12 }}
      >
        ‹ 返回办事台
      </button>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{item.name}</div>
      <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>{item.pageDesc}</div>

      {/* 动作行 = 真实「页内按钮行」构件（.ks-kb-row：留边适用面之一）。 */}
      <div className="ks-kb-row" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Button variant="outline" size="sm" disabled={phase !== 'ready' || items.length === 0} onClick={exportMd}>
          导出 Markdown
        </Button>
        {total !== null && (
          <span className="ks-kb-hint">共 {String(total)} 条{total > items.length ? `（本页显示 ${String(items.length)} 条）` : ''}</span>
        )}
      </div>

      {phase === 'load' && (
        <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12 }}>正在读取外发记录…</div>
      )}
      {phase === 'error' && (
        <div role="alert" style={{ color: 'var(--dsw-alias-state-error-primary)', fontSize: 12, lineHeight: 1.6 }}>
          读取失败：{errText}
        </div>
      )}
      {phase === 'ready' && items.length === 0 && (
        <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12 }}>
          还没有外发记录（每次调用云端都会在这里留痕）。
        </div>
      )}
      {phase === 'ready' && items.map((it, i) => (
        <div
          key={`${str(it.dump_id)}-${String(i)}`}
          className="ks-off-egress-row"
          style={{ border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}
        >
          <div style={{ display: 'flex', gap: 8, fontSize: 12, fontWeight: 600 }}>
            <span>{str(it.created_at) || '—'}</span>
            <span style={{ color: 'var(--dsw-alias-label-secondary)' }}>{str(it.service) || '—'}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--dsw-alias-label-tertiary)', fontWeight: 400 }}>
              {str(it.payload_bytes) || '—'} 字节
            </span>
          </div>
          <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>
            {str(it.query) || str(it.prompt_preview) || '—'}
          </div>
        </div>
      ))}
    </div>
  )
}

/** 三色词（引擎 verdict → 界面词与色；语言规范：状态词统一、颜色只用宿主真 token）。 */
const VERDICT_WORD: Record<string, { text: string; color: string }> = {
  red: { text: '风险', color: 'var(--dsw-alias-state-error-primary)' },
  yellow: { text: '需复核', color: 'var(--dsw-alias-state-warn-primary)' },
  green: { text: '合规', color: 'var(--dsw-alias-state-success-primary)' },
}

/** 制度差距分析页（S2-b2：登记制度 → 对比法定义务 → 缺什么/补什么）。 */
export function KsGapPage({ item, onBack }: { readonly item: OfficeItem; readonly onBack: () => void }): ReactNode {
  const [name, setName] = useState('')
  const [text, setText] = useState('')
  const [phase, setPhase] = useState<'input' | 'run' | 'done' | 'error'>('input')
  const [result, setResult] = useState<KsGapResult | null>(null)
  const [errText, setErrText] = useState('')
  const str = (v: unknown): string => (typeof v === 'string' ? v : v === null || v === undefined ? '' : String(v))

  const run = (): void => {
    setPhase('run')
    setErrText('')
    importInternalPolicy(name.trim() || '未命名制度', text.trim())
      .then((pol) => runGapAnalysis(pol.policy_id))
      .then((r) => { setResult(r); setPhase('done') })
      .catch((error: unknown) => {
        setErrText(error instanceof Error ? error.message : String(error))
        setPhase('error')
      })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 14px 18px' }}>
      <button type="button" onClick={onBack} style={{ alignSelf: 'flex-start', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--dsw-alias-state-business-primary)', fontSize: 12 }}>
        ‹ 返回办事台
      </button>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{item.name}</div>
      <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>{item.pageDesc}</div>

      {phase === 'input' && (
        <>
          <label className="ks-kb-hint" htmlFor="ks-gap-name">制度名称</label>
          <Input id="ks-gap-name" value={name} placeholder="例如：安全生产责任制" aria-label="制度名称" onChange={(e) => { setName(e.target.value) }} />
          <label className="ks-kb-hint" htmlFor="ks-gap-text">制度正文（粘贴或 .txt/.md 文件）</label>
          <textarea
            id="ks-gap-text"
            value={text}
            onChange={(e) => { setText(e.target.value) }}
            rows={6}
            style={{ width: '100%', boxSizing: 'border-box', font: 'inherit', fontSize: 12, padding: 8, border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 6, background: 'var(--dsw-alias-bg-layer-1)', color: 'var(--dsw-alias-label-primary)' }}
          />
          <div className="ks-kb-row" style={{ display: 'flex', gap: 8 }}>
            <Button variant="primary" size="sm" disabled={text.trim().length === 0} onClick={run}>开始：上传制度比对</Button>
          </div>
        </>
      )}

      {phase === 'run' && <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12 }}>正在逐条比对法定义务…</div>}
      {phase === 'error' && <div role="alert" style={{ color: 'var(--dsw-alias-state-error-primary)', fontSize: 12, lineHeight: 1.6 }}>出问题了：{errText}</div>}

      {phase === 'done' && result !== null && (
        <>
          <div style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary)' }}>
            结论：{String(result.counts.red)} 风险 · {String(result.counts.yellow)} 需复核 · {String(result.counts.green)} 合规（制度：{result.policy_name}）
          </div>
          {result.results.map((r, i) => {
            const w = VERDICT_WORD[str(r.verdict)] ?? { text: '需复核', color: 'var(--dsw-alias-state-warn-primary)' }
            return (
              <div key={`gap-${String(i)}`} style={{ border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
                  <span style={{ color: w.color, fontWeight: 600 }}>{w.text}</span>
                  <span style={{ color: 'var(--dsw-alias-label-secondary)' }}>{str(r.obligation).slice(0, 60)}</span>
                </div>
                <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12, lineHeight: 1.6 }}>{str(r.suggestion)}</div>
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}

/** 纠错修订页（S2-c：手动提交修订（466 防乱确认流）+ 修订台账 + 回退）。 */
export function KsFixPage({ item, onBack }: { readonly item: OfficeItem; readonly onBack: () => void }): ReactNode {
  const [rev, setRev] = useState('')
  const [fixed, setFixed] = useState('')
  const [patches, setPatches] = useState<KsClausePatch[]>([])
  const [warnText, setWarnText] = useState('')
  const [msg, setMsg] = useState('')
  const [errText, setErrText] = useState('')
  const str = (v: unknown): string => (typeof v === 'string' ? v : v === null || v === undefined ? '' : String(v))

  const reload = (): void => {
    listClausePatches({ limit: 50 })
      .then(setPatches)
      .catch((error: unknown) => { setErrText(error instanceof Error ? error.message : String(error)) })
  }
  useEffect(() => { reload() }, [])

  const submit = (force: boolean): void => {
    setErrText('')
    setMsg('')
    createClausePatch({ clause_revision_id: rev.trim(), field_name: 'content_text', patched_value: fixed, force })
      .then((out) => {
        if ('warned' in out) {
          setWarnText(out.warned)
          return
        }
        setWarnText('')
        setRev('')
        setFixed('')
        setMsg('修订已提交（原文仍在，随时可回退）。')
        reload()
      })
      .catch((error: unknown) => { setErrText(error instanceof Error ? error.message : String(error)) })
  }

  const revert = (patchId: string): void => {
    if (!window.confirm('回退这条修订？（滚回原始值；原文从不改动，这只是撤销更正）')) return
    setErrText('')
    deleteClausePatch(patchId)
      .then(() => { setMsg('已回退。'); reload() })
      .catch((error: unknown) => { setErrText(error instanceof Error ? error.message : String(error)) })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 14px 18px' }}>
      <button type="button" onClick={onBack} style={{ alignSelf: 'flex-start', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--dsw-alias-state-business-primary)', fontSize: 12 }}>
        ‹ 返回办事台
      </button>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{item.name}</div>
      <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>{item.pageDesc}</div>

      <label className="ks-kb-hint" htmlFor="ks-fix-rev">哪一条（条款版本号，可从原文页/本轮依据里复制）</label>
      <Input id="ks-fix-rev" value={rev} placeholder="rev_…" aria-label="条款版本号" onChange={(e) => { setRev(e.target.value) }} />
      <label className="ks-kb-hint" htmlFor="ks-fix-text">识别错了的正文，正确的应该是</label>
      <textarea
        id="ks-fix-text"
        value={fixed}
        onChange={(e) => { setFixed(e.target.value) }}
        rows={4}
        style={{ width: '100%', boxSizing: 'border-box', font: 'inherit', fontSize: 12, padding: 8, border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 6, background: 'var(--dsw-alias-bg-layer-1)', color: 'var(--dsw-alias-label-primary)' }}
      />
      <div className="ks-kb-row" style={{ display: 'flex', gap: 8 }}>
        <Button variant="primary" size="sm" disabled={rev.trim().length === 0 || fixed.trim().length === 0} onClick={() => { submit(false) }}>
          提交修订
        </Button>
      </div>
      {warnText !== '' && (
        <div role="alert" style={{ border: '0.5px solid var(--dsw-alias-state-warn-primary)', color: 'var(--dsw-alias-state-warn-primary)', borderRadius: 6, padding: '6px 10px', fontSize: 12, lineHeight: 1.6 }}>
          {warnText}
          <div className="ks-kb-row" style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <Button variant="outline" size="sm" onClick={() => { submit(true) }}>看过了，确认提交</Button>
          </div>
        </div>
      )}
      {msg !== '' && <div style={{ color: 'var(--dsw-alias-state-success-primary)', fontSize: 12 }}>{msg}</div>}
      {errText !== '' && <div role="alert" style={{ color: 'var(--dsw-alias-state-error-primary)', fontSize: 12, lineHeight: 1.6 }}>出问题了：{errText}</div>}

      <div style={{ fontSize: 12, fontWeight: 600, marginTop: 4 }}>修订台账（{String(patches.length)} 条，可回退）</div>
      {patches.length === 0 && (
        <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12 }}>还没有修订记录。</div>
      )}
      {patches.map((p, i) => (
        <div key={`${str(p.patch_id)}-${String(i)}`} className="ks-off-fix-row" style={{ border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', gap: 8, fontSize: 12 }}>
            <span style={{ fontWeight: 600 }}>{str(p.clause_revision_id) || '—'}</span>
            <span style={{ color: 'var(--dsw-alias-label-tertiary)' }}>{str(p.field_name) || '—'} · {str(p.created_at) || '—'}</span>
          </div>
          <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6 }}>{str(p.patched_value).slice(0, 120)}</div>
          <div>
            <Button variant="ghost" size="sm" onClick={() => { revert(str(p.patch_id)) }}>回退</Button>
          </div>
        </div>
      ))}
    </div>
  )
}

/**
 * 办事台页（原「能力」页；导出名保留 `KsCapabilityPage` = 挂载点零改动）。
 */
export function KsCapabilityPage(): ReactNode {
  ensureKsStyles()
  const [activeId, setActiveId] = useState<string | null>(null)
  const active = OFFICE_ITEMS.find((i) => i.id === activeId) ?? null

  return (
    <div className="ks-page">
      <div className="ks-kb">
        <header className="ks-page-head">
          <div className="ks-page-title">办事台</div>
          <div className="ks-page-sub">点一项，开始一件活。</div>
        </header>
        <div className="ks-page-rule" />
        {active !== null ? (
          active.id === 'egress'
            ? <KsEgressPage item={active} onBack={() => { setActiveId(null) }} />
            : active.id === 'fix'
              ? <KsFixPage item={active} onBack={() => { setActiveId(null) }} />
              : active.id === 'gap'
                ? <KsGapPage item={active} onBack={() => { setActiveId(null) }} />
                : <OfficePage item={active} onBack={() => { setActiveId(null) }} />
        ) : (
          <div role="menu" aria-label="办事台">
            {OFFICE_ITEMS.map((item) => (
              <KsOfficeRow key={item.id} item={item} onOpen={(id) => { setActiveId(id) }} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
