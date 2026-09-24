/**
 * ks-dsh-plugin — client/KsTurnTab.tsx  （S1-a 空态 + S1-b 依据行，2026-09-22）
 *
 * 「本轮」tab 的 body：跟着当前回答走的**本轮依据**（这轮用了哪几条、核对结果、看原文）。
 * 业主批准形态：`docs/mockups/mockup-S1-turn-tab.html`（假数据原型）。
 *
 * 数据通路（S1-b，`design-S1-turn-data-mapping.md` §二）：
 *   宿主在 `ks_answer` 返回前暂存（`plugin/src/turn.js`）→ 这里经
 *   `GET /ks/turn/last?session=…` 读取（同源只读口）→ 渲染依据行。
 *   「看原文」走**既有** openEvidence 链路（S1-a 注册的单例证据 tab：跳页 + 红箭头），
 *   URL 由 `ksEvidence.evidenceUrlOf` 构造（一个出处，不自拼）。
 *   `navigation.revision` 变化即重读（S1-c 的"回答完自动切达"叠加其上）。
 *
 * 纯组件 `KsTurnEvidenceRow` / `KsTurnEmptyState` 独立导出：渲染级冒烟单独钉它们
 * （同 KsAnchorWarn / KsArrowOverlay 先例）。
 */
import * as React from 'react'

import { evidenceUrlOf, type KsEvidence } from './ksEvidence'

/** 框架按 hookContext 交给 body 的运行时面（同 KsEvidenceHost 的用法）。 */
export interface KsTurnTabRuntime {
  useTabInfo: () => {
    tab: {
      id: string
      kind: string
      title: string
      navigation?: { revision?: number }
      visible?: boolean
    }
  }
}

/** 本插件贡献给该 body 的注入面。 */
export interface KsTurnInjected {
  /** 本 tab 所属会话（取数键：GET /ks/turn/last?session=…）。 */
  sessionId: string
  /** 诊断标签（谁是数据来源；同 KsKnowledgePage 的 dataSource）。 */
  dataSource: string
  /** 看原文：复用既有证据链路（单例证据 tab：跳页 + 红箭头）。 */
  openEvidence: (evidenceUrl: string) => void
}

export type KsTurnTabProps = KsTurnTabRuntime & KsTurnInjected

/** 依据条目（引擎原始公开字段——`_clause_to_evidence` 的对外 JSON 面）。 */
export interface KsTurnEvidenceItem {
  doc_id?: unknown
  clause_revision_id?: unknown
  standard_no?: unknown
  clause_number?: unknown
  title?: unknown
  legal_status?: unknown
  legal_hierarchy?: unknown
  page_start?: unknown
  effective_from?: unknown
  snippet?: unknown
}

/** 暂存的一轮（`plugin/src/turn.js` 的 `turn` 负载，防御式读取）。 */
export interface KsTurnRecord {
  query?: unknown
  tier?: unknown
  verification?: unknown
  notes?: unknown
  scope?: unknown
  mode?: unknown
  evidence?: unknown
}

const str = (v: unknown): string => (typeof v === 'string' ? v : v === undefined || v === null ? '' : String(v))

/** 引擎公开字段 → 证据锚点（KsEvidence 形状，evidenceUrlOf 是唯一 URL 构造者）。 */
export function turnEvidenceHref(ev: KsTurnEvidenceItem): string | null {
  const doc = str(ev.doc_id)
  if (doc.length === 0) return null
  const pageRaw = ev.page_start
  const target: KsEvidence = {
    doc,
    page: typeof pageRaw === 'number' && pageRaw >= 1 ? Math.floor(pageRaw) : undefined,
    rev: str(ev.clause_revision_id).length > 0 ? str(ev.clause_revision_id) : undefined,
  }
  return evidenceUrlOf(target)
}

/** 效力徽章（语言规范词汇 + 宿主真 token 色；无字面兜底——F0 的教训）。 */
function statusBadge(ev: KsTurnEvidenceItem): { text: string; color: string } {
  const s = str(ev.legal_status)
  if (s === 'effective') return { text: '现行有效', color: 'var(--dsw-alias-state-success-primary)' }
  if (s === 'upcoming') {
    const from = str(ev.effective_from)
    return { text: from.length > 0 ? `${from} 起实施` : '即将实施', color: 'var(--dsw-alias-state-warn-primary)' }
  }
  if (s === 'superseded') return { text: '已被替代', color: 'var(--dsw-alias-state-error-primary)' }
  if (s === 'withdrawn') return { text: '已废止', color: 'var(--dsw-alias-state-error-primary)' }
  /* ⚠ 2026-09-24 新增这一档（业主："征求意见稿也要入库，只是效力层级是参考资料"）：
     它**不是**现行依据 —— 徽章必须把"仅参考"说在字面上，别让它看起来像个有效档。 */
  if (s === 'reference') return { text: '参考资料（仅参考，非现行依据）', color: 'var(--dsw-alias-label-secondary)' }
  return { text: '状态未知', color: 'var(--dsw-alias-label-tertiary)' }
}

/** 「这一轮的口径」胶囊行（S1-c，**只读**——冻结快照；改口径仍走输入框那颗活胶囊）。 */
export function KsTurnModeChip(props: { mode: unknown; scope: unknown }): React.ReactElement | null {
  const m = (props.mode ?? {}) as {
    forensic?: unknown; bookmarksOnly?: unknown; folderName?: unknown; materialProjectName?: unknown
  }
  const scope = (props.scope ?? null) as { folder_count?: unknown; doc_count?: unknown } | null
  const pills: string[] = []
  // ⚠ 全部激活口径**都出词**（语言规范 §A4：不是互斥单选——夹内提问会连带开查法规，
  // 两颗胶囊都要在，用户才看得清自己开着什么）。2026-09-22 首版写成 else-if 被判据红出。
  if (m.forensic === true) pills.push('查法规模式')
  if (m.bookmarksOnly === true) {
    const name = str(m.folderName)
    pills.push(name.length > 0 ? `仅在『${name}』内提问` : '仅在收藏内提问')
  }
  const mat = str(m.materialProjectName)
  if (mat.length > 0) pills.push(`材料：${mat}`)
  if (scope !== null && (typeof scope.folder_count === 'number' || typeof scope.doc_count === 'number')) {
    pills.push(`范围：${str(scope.folder_count ?? 0)} 个目录 · ${str(scope.doc_count ?? 0)} 篇`)
  }
  if (pills.length === 0) return null
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {pills.map((p) => (
        <span
          key={p}
          style={{
            fontSize: 11, borderRadius: 999, padding: '2px 10px', color: 'var(--dsw-alias-label-secondary)',
            border: '0.5px solid var(--dsw-alias-border-l1)',
          }}
        >
          {p}
        </span>
      ))}
    </div>
  )
}

/** 定稿空态（原型"状态二"两句原话——冒烟钉死字面，不许再改成散文）。 */
export function KsTurnEmptyState(): React.ReactElement {
  return (
    <div
      style={{
        padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 4,
        alignItems: 'center', justifyContent: 'center', minHeight: 160, textAlign: 'center',
      }}
    >
      <div style={{ color: 'var(--dsw-alias-label-secondary)', fontSize: 13 }}>
        这一轮还没用到依据。
      </div>
      <div style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12, lineHeight: 1.6 }}>
        在对话里提问后，这里会列出这次答案用到的条款与核对结果。
      </div>
    </div>
  )
}

/** 依据行（纯组件；原型第一屏的每张小卡）。 */
export function KsTurnEvidenceRow(props: {
  ev: KsTurnEvidenceItem
  onLook?: () => void
}): React.ReactElement {
  const { ev, onLook } = props
  const badge = statusBadge(ev)
  const href = turnEvidenceHref(ev)
  return (
    <div
      style={{
        border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8,
        padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontWeight: 600 }}>
          {str(ev.standard_no)} {str(ev.clause_number)}
        </span>
        <span
          style={{
            fontSize: 11, borderRadius: 999, padding: '1px 8px',
            border: `0.5px solid ${badge.color}`, color: badge.color,
          }}
        >
          {badge.text}
        </span>
        {str(ev.legal_hierarchy).length > 0 && (
          <span style={{ fontSize: 11, color: 'var(--dsw-alias-label-tertiary)' }}>
            {str(ev.legal_hierarchy)}
          </span>
        )}
      </div>
      {str(ev.snippet).length > 0 && (
        <div
          style={{
            color: 'var(--dsw-alias-label-secondary)', fontSize: 12, lineHeight: 1.6,
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}
        >
          {str(ev.snippet)}
        </div>
      )}
      {href !== null && (
        <button
          type="button"
          onClick={() => { if (onLook !== undefined) onLook() }}
          style={{
            alignSelf: 'flex-start', background: 'none', border: 'none', padding: 0, cursor: 'pointer',
            color: 'var(--dsw-alias-state-business-primary)', fontSize: 12,
          }}
        >
          → 看原文（跳到那一页，红箭头指着）
        </button>
      )}
    </div>
  )
}

export function KsTurnTab(props: KsTurnTabProps): React.ReactElement {
  const info = props.useTabInfo()
  const revision = info.tab.navigation?.revision ?? 0
  const { sessionId, openEvidence } = props
  const [record, setRecord] = React.useState<KsTurnRecord | null>(null)
  const [loading, setLoading] = React.useState(true)

  // revision 变（回答完自动切达 / 同地址再导航）即重读——与证据 tab 的重载语义同源。
  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    const url = `/ks/turn/last?session=${encodeURIComponent(sessionId)}&r=${String(revision)}`
    fetch(url)
      .then((res) => (res.ok ? res.json() : null))
      .then((body: unknown) => {
        if (cancelled) return
        const data = (body as { data?: { turn?: KsTurnRecord } | null } | null)?.data ?? null
        setRecord(data === null ? null : (data.turn ?? null))
      })
      .catch(() => { if (!cancelled) setRecord(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [sessionId, revision])

  if (record === null) {
    return loading
      ? (
        <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--dsw-alias-label-tertiary)', fontSize: 12 }}>
          正在读取本轮…
        </div>
      )
      : <KsTurnEmptyState />
  }

  const evidence: KsTurnEvidenceItem[] = Array.isArray(record.evidence)
    ? (record.evidence as KsTurnEvidenceItem[])
    : []
  const verification = record.verification as {
    is_valid?: unknown
    confidence_reasons?: unknown
    cite_warnings?: unknown
  } | null
  const reasons: string[] = [
    ...(Array.isArray(verification?.confidence_reasons) ? verification.confidence_reasons : []),
    ...(Array.isArray(verification?.cite_warnings) ? verification.cite_warnings : []),
  ].map((x) => str(x)).filter((x) => x.length > 0)
  const notes: string[] = Array.isArray(record.notes) ? record.notes.map((x) => str(x)).filter((x) => x.length > 0) : []

  return (
    <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* 这一轮的口径（冻结快照，只读胶囊） */}
      <KsTurnModeChip mode={record.mode} scope={record.scope} />
      {/* 核对结果行（语言规范：失败写在脸上；这里按 is_valid 分成败两个色） */}
      {verification !== null && (
        <div
          role={verification.is_valid === true ? undefined : 'alert'}
          style={{
            fontSize: 12, lineHeight: 1.6, borderRadius: 6, padding: '4px 10px',
            border: `0.5px solid ${verification.is_valid === true ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-state-warn-primary)'}`,
            color: verification.is_valid === true ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-state-warn-primary)',
          }}
        >
          {verification.is_valid === true ? '✅ 核对通过' : '⚠ 核对提示'}
          {reasons.length > 0 ? `：${reasons.join(' · ')}` : ''}
        </div>
      )}

      {evidence.map((ev, i) => (
        <KsTurnEvidenceRow
          key={`${str(ev.doc_id)}-${str(ev.clause_revision_id)}-${String(i)}`}
          ev={ev}
          onLook={() => {
            const href = turnEvidenceHref(ev)
            if (href !== null) openEvidence(href)
          }}
        />
      ))}

      {notes.map((n, i) => (
        <div key={`note-${String(i)}`} style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12, lineHeight: 1.6 }}>
          {n}
        </div>
      ))}
    </div>
  )
}
