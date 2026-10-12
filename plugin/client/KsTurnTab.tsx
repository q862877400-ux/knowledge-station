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
  /* ⚠ 2026-10-10（spec 009，**红箭头的第①②环**）：引擎新增这两个字段 ——
     箭头完全依赖 `bbox`（`KsEvidenceTab` 里 `const anchor = evidence.current?.bbox`），
     而原来**引擎不输出它、这里也不声明它** ⇒ 箭头永远不画（业主实测：能跳转、没箭头）。
     · `bbox`：PDF 用户空间 `[x0,y0,x1,y1]`（**左下原点**，与 ksEvidence 契约逐字一致）；
     · `bbox_page`：该 bbox 所在的页（渲染层只在这一页画箭头）。 */
  bbox?: unknown
  bbox_page?: unknown
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
  /* ⚠ 2026-10-10（spec 009，**红箭头的第②环**）：把 `bbox` / `bbox_page` 一并带上。
     原来这里**只传 doc/page/rev** ⇒ 即便引擎给了 bbox，也会在这一步丢掉。
     ⚠ `bbox` 必须原样是 4 个有限数才传 —— 交给 `isBbox`（在 evidenceUrlOf 里）把关，
     这里只做形状初筛，**不编造、不用 0 兜底**（0 会画出左上角一个错箭头）。 */
  const bboxRaw = ev.bbox
  const bbox = Array.isArray(bboxRaw)
    && bboxRaw.length === 4
    && bboxRaw.every((n) => typeof n === 'number' && Number.isFinite(n))
    ? (bboxRaw as [number, number, number, number])
    : undefined
  const bboxPageRaw = ev.bbox_page
  const bboxPage = typeof bboxPageRaw === 'number' && Number.isFinite(bboxPageRaw) && bboxPageRaw >= 1
    ? Math.floor(bboxPageRaw)
    : undefined
  const target: KsEvidence = {
    doc,
    page: typeof pageRaw === 'number' && pageRaw >= 1 ? Math.floor(pageRaw) : undefined,
    rev: str(ev.clause_revision_id).length > 0 ? str(ev.clause_revision_id) : undefined,
    bbox,
    bboxPage,
  }
  return evidenceUrlOf(target)
}

/**
 * 条款号排序键（**数值感知**，永不抛错）。
 *
 * ⚠ 2026-10-10（spec 009，业主要求"按先后顺序排列"）：
 *   业主原话只说"按先后顺序"，**没说按什么排**。我取**条款号升序** —— 这是最自然的读法
 *   （条款号本身就是文档内的先后），并在 `docs/UI-BASELINE.md` §5ac 登记为**我的判断**。
 *
 * ⚠ 为什么要"数值感知"：字典序下 `5.10.1` **小于** `5.2.3`（因为 `'1' < '2'`），
 *   而真实顺序相反 ⇒ 必须**逐段比数字**。
 * ⚠ 稳健性：条款号可能是 `第一条`、`8.1.1`、空串、纯中文。**一律不抛错** ——
 *   能切成数字段的比数值，切不出来的按原串比（中文用 `localeCompare`，中文排序正常）。
 */
export function clauseOrderKey(raw: unknown): { numeric: number[]; text: string } {
  const s = str(raw).trim()
  const parts = s.split(/[.．、\s]+/).filter((x) => x.length > 0)
  const numeric: number[] = []
  let allNumeric = parts.length > 0
  for (const p of parts) {
    const n = Number(p)
    if (Number.isFinite(n)) numeric.push(n)
    else { allNumeric = false; break }
  }
  return allNumeric ? { numeric, text: '' } : { numeric: [], text: s }
}

/** 比较两条依据的先后（数值段优先；一方纯数字、另一方不是 ⇒ 数字的在前）。 */
export function compareClauseOrder(a: KsTurnEvidenceItem, b: KsTurnEvidenceItem): number {
  const ka = clauseOrderKey(a.clause_number)
  const kb = clauseOrderKey(b.clause_number)
  const aNum = ka.numeric.length > 0
  const bNum = kb.numeric.length > 0
  if (aNum && bNum) {
    const n = Math.max(ka.numeric.length, kb.numeric.length)
    for (let i = 0; i < n; i += 1) {
      const x = ka.numeric[i] ?? -1
      const y = kb.numeric[i] ?? -1
      if (x !== y) return x - y
    }
    return 0
  }
  if (aNum !== bNum) return aNum ? -1 : 1
  return ka.text.localeCompare(kb.text, 'zh')
}

/**
 * 正文是否**自带**这条条款号（决定要不要单独显示条款号那一行）。
 *
 * 业主 2026-10-12 实跑截图后提出：「我红色框框选的这些标题都不需要，
 * 你没看到**正文本来就自带编号**了吗」—— 那行标题（如 `6.4.3.2`）与正文首行的
 * `6.4.3.2 …` 重复。
 *
 * **业主是对的**：真库抽样 3 万条，**98.2% 的正文以条款号开头**（29,473 条）。
 *
 * ⚠ 但**不能一律不显示**：那 1.8%（527 条）里是 `前置1`（封面/前言，294 条）、
 * `附录A`（189 条）这类 —— 正文**不含**这个编号（是"中华人民共和国国家标准…"或
 * "附 录 A"），删了就**丢掉"这是哪一条"**。⇒ 只有"正文确实自带"时才省。
 *
 * 比对做**宽松归一**：去掉所有空白与全角/半角标点差异后比前缀
 * （正文里条款号后常跟空格或换行，且 PDF 抽取可能把 `.` 抽成全角）。
 */
export function snippetCarriesClauseNo(ev: KsTurnEvidenceItem): boolean {
  const no = str(ev.clause_number).trim()
  const text = str(ev.snippet)
  if (no.length === 0 || text.length === 0) return false
  const norm = (s: string): string => s
    .replace(/\s+/g, '')
    .replace(/[．。]/g, '.')
    .replace(/[（]/g, '(')
    .replace(/[）]/g, ')')
  const nNo = norm(no)
  const nText = norm(text)
  if (nNo.length === 0) return false
  return nText.startsWith(nNo)
}

/** 一条依据按文件分组后的形状。 */
export interface KsTurnEvidenceGroup {
  /** 分组键（doc_id）；空 doc_id 的条目各自成组（`#i`），不许被合并成一组。 */
  key: string
  /** 组标题：标准号 + 文件名（同一文件**只显示一次**）。 */
  title: string
  /** 组内条款（**已按条款号升序**）。 */
  items: KsTurnEvidenceItem[]
}

/**
 * 把依据按文件分组（spec 009 业主要求 1）。
 *
 * 业主原话：「一个文件里的多个条款就不要重复文件标题了，一个文件标题下面多个条款按先后顺序排列。」
 * ⇒ 同一 `doc_id` **只出一遍标题**，条款按 `compareClauseOrder` 升序。
 *
 * ⚠ 无 `doc_id` 的条目：**各自成组**（键 `#<序号>`），不许把它们合并成一个"（无文件）"组
 *   —— 那会把不同文件的东西混在一起，比重复标题更糟。
 * ⚠ 组顺序：**按组内第一条的出现次序**（即检索给出的相关度次序）——
 *   不按标题字母序（那会把最相关的文件排到后面）。组**内**才排序。
 */
export function groupTurnEvidence(items: readonly KsTurnEvidenceItem[]): KsTurnEvidenceGroup[] {
  const order: string[] = []
  const map = new Map<string, KsTurnEvidenceItem[]>()
  items.forEach((ev, i) => {
    const doc = str(ev.doc_id)
    const key = doc.length > 0 ? doc : `#${String(i)}`
    if (!map.has(key)) {
      map.set(key, [])
      order.push(key)
    }
    map.get(key)?.push(ev)
  })
  return order.map((key) => {
    const group = map.get(key) ?? []
    const sorted = [...group].sort(compareClauseOrder)
    const first = sorted[0]
    const std = first === undefined ? '' : str(first.standard_no)
    const title = first === undefined ? '' : str(first.title)
    const label = std.length > 0 && title.length > 0 ? `${std}　${title}`
      : std.length > 0 ? std
        : title.length > 0 ? title : '（没有文件信息）'
    return { key, title: label, items: sorted }
  })
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

/** 条款行（纯组件）—— ⚠ spec 009 起它**不再重复文件标题**（标题由外层分组卡出一遍）。 */
export function KsTurnEvidenceRow(props: {
  ev: KsTurnEvidenceItem
  onLook?: () => void
  /** 组内第几条（从 1 起）。用于"条款按先后排列"的可读性，不参与排序。 */
  ordinal?: number
}): React.ReactElement {
  const { ev, onLook, ordinal } = props
  /* ⚠ 2026-10-12（spec 010）：`statusBadge` 不再在这里调用 —— 效力徽章已移到
     分组卡的**文件标题行**（业主：「现行有效是文件级别的」）。 */
  const href = turnEvidenceHref(ev)
  const clause = str(ev.clause_number)
  return (
    <div
      style={{
        border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8,
        padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 4,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* ⚠ 2026-10-12（spec 012，业主实跑截图反馈）：**正文自带条款号时，不再单出一行**。
            业主原话：「我红色框框选的这些标题都不需要，你没看到正文本来就自带编号了吗」
            实测支持业主：真库抽样 3 万条，**98.2% 的正文以条款号开头** ⇒ 那一行是重复。
            ⚠ 但**1.8% 例外**（`前置1` 封面 / `附录A` 等，正文不含该编号）仍要显示，
            否则用户看不出"这是哪一条" ⇒ 判据见 `snippetCarriesClauseNo`。
            ⚠ spec 009 的旧注释（"这里只显示条款号，不带 standard_no/title"）仍然成立：
            文件标题由外层分组卡出一次。 */}
        {ordinal !== undefined && (
          <span style={{ fontSize: 11, color: 'var(--dsw-alias-label-tertiary)', flex: 'none' }}>
            {String(ordinal)}.
          </span>
        )}
        {!snippetCarriesClauseNo(ev) && (
          <span style={{ fontWeight: 600 }}>
            {clause.length > 0 ? clause : '（无条款号）'}
          </span>
        )}
        {/* ⚠⚠ 2026-10-12（spec 010，业主实跑反馈 1）：**效力徽章从条款行移走**。
            业主原话：「现行有效是**文件级别**的，所以在文件名后面展示有效状态就行了」。
            **业主是对的，且与数据结构一致**：`legal_status` 存在 `doc_meta`（**文件级**），
            不在 `clause_revision`（条款级）。我上一批把它画在了条款级上。
            ⇒ 徽章现在挂在**分组卡的文件标题行**（见下面的分组渲染）。
            ⚠ 这里**不再调用 statusBadge**（`badge` 变量已移到分组卡里）。 */}
        {/* ⚠ 2026-10-10（spec 009，业主要求）：**不再显示 `legal_hierarchy`**。
            业主原话：「现行有效后面的 GB 字样删除。」
            理由（我的判定）：徽章已经说了"现行有效 / 已被替代"，
            再挂一个 `GB`（层级）对用户**没有增量信息**，只是噪声。
            ⚠ **只删显示，数据保留**：`KsTurnEvidenceItem.legal_hierarchy` 仍在接口上、
            仍在 `evidence` 里 —— 别的消费者（导出、审计）可能要用，本批不动数据。
            ⚠ 另登记（**不本批修**）：真库实测 1043 篇 `legal_hierarchy = 'GB'` 里，
            有 **19 篇**是法律/条例被默认值兜成 GB（`src/core/domain/models.ts:102` 同族的
            `src/core/domain/models.py:102` 的 `legal_hierarchy: str = "GB"`）—— 那是**数据层**问题。 */}
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
    /* ⚠⚠ 2026-10-12（spec 010，业主实跑反馈 2）：**本页原来没法滚动**。
       业主原话：「这个页面**没法翻页**」。
       根因：这个根容器原来**没有任何 overflow 设置** ⇒ 内容超过面板高度时被裁掉、滚不动
       （同插件其它面板都在内层做了 `overflow:'auto'` + `maxHeight`，本页漏了）。
       ⚠ 为什么用 `height:'100%'` + `overflowY:'auto'` 而不是 `maxHeight:<数字>`：
         · 面板高度由宿主决定（业主自己拖侧栏），**不能写死一个数字**；
         · `height:100%` 让本容器填满宿主给的高度，`overflowY:auto` 让超长内容**在本容器内滚**。
       ⚠ `minHeight:0` 是必需的：flex 子项默认 `min-height:auto` ⇒ 内容会**撑开**容器而不是
         在内部滚动（本仓 `ksGuideStyles.ts` 里 `.ks-main` 那条注释记的是同一个坑）。
       ⚠ `boxSizing:'border-box'` 让 padding 计入 100% 高度，避免多出 24px 溢出。 */
    <div
      style={{
        padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8,
        height: '100%', minHeight: 0, overflowY: 'auto', boxSizing: 'border-box',
      }}
    >
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

      {/* ⚠ 2026-10-10（spec 009，业主要求 1）：
          「一个文件里的多个条款就不要重复文件标题了，一个文件标题下面多个条款按先后顺序排列。」
          ⇒ 按 `doc_id` 分组：**一个文件出一个标题**，组内条款按条款号升序（`groupTurnEvidence`）。
          ⚠ 组**之间**保持检索给出的相关度次序（不按标题字母序排 —— 那会把最相关的文件挤到后面）。 */}
      {groupTurnEvidence(evidence).map((group) => {
        /* ⚠⚠ 2026-10-12（spec 010，业主实跑反馈 1）：**效力徽章挂在文件标题行**。
           业主原话：「现行有效是**文件级别**的，所以在文件名后面展示有效状态就行了」。
           **业主与数据结构一致**：`legal_status` 在 `doc_meta`（文件级）。
           ⚠ 但引擎是**逐条款**给的 `legal_status` ⇒ 同组理论上同值、异常时会不同。
             处置：取**第一条**的状态显示，若组内出现**两种以上**，在组下加一行小字如实说明
             （不许静默 —— 否则用户以为整组都是那个状态）。 */
        const statuses = [...new Set(group.items.map((x) => str(x.legal_status)).filter((x) => x.length > 0))]
        const head = group.items[0]
        const headBadge = head === undefined ? null : statusBadge(head)
        return (
        <div
          key={group.key}
          style={{
            border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 8,
            padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 6,
          }}
        >
          {/* 文件标题行：标题 + **效力徽章**（文件级，只出现这一遍） */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{group.title}</span>
            {headBadge !== null && (
              <span
                style={{
                  fontSize: 11, borderRadius: 999, padding: '1px 8px',
                  border: `0.5px solid ${headBadge.color}`, color: headBadge.color,
                }}
              >
                {headBadge.text}
              </span>
            )}
          </div>
          {statuses.length > 1 && (
            <div style={{ fontSize: 11, color: 'var(--dsw-alias-state-warn-primary)' }}>
              ⚠ 这个文件下的条款报了**不止一种**效力状态（{statuses.join(' / ')}），
              上面显示的是第一条的；逐条状态请看各条款自己的数据。
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {group.items.map((ev, i) => (
              <KsTurnEvidenceRow
                key={`${str(ev.doc_id)}-${str(ev.clause_revision_id)}-${String(i)}`}
                ev={ev}
                ordinal={group.items.length > 1 ? i + 1 : undefined}
                onLook={() => {
                  const href = turnEvidenceHref(ev)
                  if (href !== null) openEvidence(href)
                }}
              />
            ))}
          </div>
        </div>
        )
      })}

      {notes.map((n, i) => (
        <div key={`note-${String(i)}`} style={{ color: 'var(--dsw-alias-label-tertiary)', fontSize: 12, lineHeight: 1.6 }}>
          {n}
        </div>
      ))}
    </div>
  )
}
