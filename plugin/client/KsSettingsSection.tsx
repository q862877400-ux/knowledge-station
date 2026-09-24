/**
 * ks-dsh-plugin — client/KsSettingsSection.tsx
 *
 * The「法规标准知识库」settings SECTION, contributed to the DSH Settings shell
 * as a TOP-LEVEL nav 栏目 (a `settings.section` registration) — the same
 * mechanism dsh-better-sidebar uses to contribute its own「侧边卡片」nav
 * (see its client/index.tsx `ctx.slots.inject('settings.section', …)`).
 *
 * WHY this instead of the previous hidden-tab card:
 *  - A `TabDescriptor` (even `hidden: true`) can ONLY ever render as a FEATURE
 *    CARD inside the「侧边栏内容」grid of the「侧边卡片」settings section. It
 *    cannot produce a distinct settings 栏目/nav entry. `hidden` is only
 *    filtered from the + menu (Sidebar.tsx buildNewTabOptions:172); the
 *    settings grid does NOT filter it (SideCardSection.tsx:982-997), so the
 *    hidden tab DID render — but buried at the bottom (tabOrder:112 sorts
 *    hidden last) and its config was behind a gear popup, so it never read as
 *    the「法规标准知识库」设置栏目 the user asked for.
 *  - This section renders the plugin's settings INLINE and VISIBLE (the
 *    showArrow switch is a plain row, not a popup), so the user sees the
 *    栏目 title AND the config item at once.
 *
 * PREF STORE: the setting lives in the shared Side card prefs document under
 * `pluginSettings['ks:settings']` — exactly where KsEvidenceTab reads it
 * (`store.getSnapshot().prefs.pluginSettings['ks:settings'].showArrow`).
 * Reads come from the reactive betterSidebar snapshot (so store commits from
 * the Side card page re-render this section); writes go through
 * dsh-better-sidebar's own fenced `/sidebar/api/settings.update` route
 * (same-origin, revision-guarded, merged into the SAME prefs doc).
 *
 * KNOWN NUANCE (documented honestly): a write performed by this standalone
 * section cannot also push through dsh-better-sidebar's internal
 * `store.setPrefs` (the API is not exposed on the service), so the switch
 * is OPTIMISTIC here and the value becomes store-visible on the next
 * store hydrate/commit (opening the Side card page, or a reload). Persistence
 * is durable either way.
 */

import * as React from 'react'
import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'

import {
  addAnnounceSource,
  exportAnnounceDiscovery,
  exportInspectionResult,
  fetchAnnounceIngestPending,
  fetchAnnounceSources,
  fetchAnnounceSummary,
  fetchApiConfig,
  fetchInspectionSummary,
  ingestAnnouncements,
  InspectionHttpError,
  type KsAnnounceIngestPending,
  type KsAnnounceIngestResult,
  type KsAnnouncePerSource,
  type KsAnnounceSource,
  type KsAnnounceSummary,
  type KsApiChannel,
  type KsApiConfigStatus,
  type KsInspectionSummary,
  removeAnnounceSource,
  runInspection,
  saveApiConfig,
  scanAnnounceSources,
  testApiChannel,
  updateAnnounceSource,
  updateInspectionSettings,
} from './api'
/* ⚠ S5-b：KsInspectionPanel / KsAnnounceSourcesSection **从这里导出**（定义原地不动、
   零面板内部改动——搬家批口径）；新家 = 知识库 ▾「渠道台账」页位。
   KsChannelsPanel 的 import 已随之移除（本文件不再挂载它——死导入不留）。 */
import {
  KS_PREFS_DEFAULT,
  getPrefsSnapshot,
  subscribePrefs,
  updatePrefs,
} from './ksPrefs'

/**
 * KS 自有的**证据导航端口**（2026-09-16 官方 sidebar 迁移）。
 *
 * 旧实现注入整个 `betterSidebar` 服务，只为两件事：读共享 prefs（红箭头开关）
 * 与"跳证据 PDF"。该包已被官方 `dsh-client-ui-sidebar-right` 取代：
 *   - 偏好 → 已迁到 `./ksPrefs`（KS 自有、本地持久化、可订阅）；
 *   - 跳证据 → 收敛成本端口（不把整个第三方服务面透进设置区）。
 *
 * 另：官方 `openResource` 对**同一恒定地址**天然幂等（同地址 = 同 tab，只聚焦不重开），
 * 且每次导航会把 `navigation.revision` +1 驱动组件重载 —— 故旧模型"openTab + updateTab
 * 覆写 path"的两步法**不再需要**，一次调用即可。
 */
export interface KsEvidenceNavPort {
  /** 打开（或复用）证据 PDF 并跳页。 */
  openEvidence: (evidenceUrl: string) => void
}

/** 设置区的注入面：只有 KS 自有的证据导航端口（其余能力走模块级 `./ksPrefs`）。 */
export interface KsSettingsSectionInjected {
  openEvidence: (evidenceUrl: string) => void
}

/** Prefs namespace (the plugin's settings blob key) + the key this section owns.
 *  ⚠ 这两个常量现在只作为**偏好的逻辑命名**保留（`./ksPrefs` 里以同名键导出、同一
 *  含义）；旧实现的宿主侧 side-card 存储与 `/sidebar/api/settings` 栅栏路由**已随
 *  better-sidebar 一起消失**，故本文件不再有读写偏好存储的代码。 */
export const KS_SETTINGS_PREFS_KEY = 'ks:settings'
export const KS_SHOW_ARROW_KEY = 'showArrow'

/**
 * The「法规标准知识库」settings section body. 所有类目一律 <details> 折叠
 * （2026-11 用户拍板：「里面塞的东西太多了」）——收起时零请求、零渲染负担；
 * summary 行给出一句副标帮助扫读。Registered via 官方 `settings.section`。
 *
 * 注入面（2026-09-16 迁移后）：只有一个 KS 自有的证据导航端口；偏好读写改走
 * `./ksPrefs`（模块级、可订阅），不再需要第三方服务。
 */

/** 类目 summary 的统一副标样式（收起/展开都可读）。 */
const SUMMARY_HINT: React.CSSProperties = {
  marginLeft: 8, fontSize: 11, fontWeight: 400,
  color: 'var(--dsw-alias-label-secondary, #888)',
}

/** 折叠类目包装：外框分隔线 + summary 标题行 + hint 副标。children 恒挂载
 *  （details 语义），请求门由各面板自己的 visible prop（由 onToggle 驱动）
 *  或各组的展开才拉模式保证。 */
function KsCategory({ title, hint, open, onToggle, children }: {
  title: string
  hint?: React.ReactNode
  open: boolean
  onToggle: (next: boolean) => void
  children: React.ReactNode
}): JSX.Element {
  return (
    <details
      open={open}
      /* ⚠ `data-ks-cat`（2026-09-21，第 4 步复核打回后加）：让"设置里有哪几个类目"
         成为**机械可抽**的事实（`smoke-settings.mjs` 按它比对**类目集合**，
         而不是去点名几个固定字符串 —— 复核实测"多一个未声明类目也会红"在那之前**不成立**：
         实际 7 组而只点名 5 个）。同 `data-on` / `data-current` / `data-depth` 的既有做法。 */
      data-ks-cat={title}
      onToggle={(e) => onToggle((e.currentTarget as HTMLDetailsElement).open)}
      style={{ borderTop: '1px solid var(--dsw-alias-border-l1, #eee)', marginTop: 4, paddingTop: 6 }}
    >
      <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)', fontSize: 13, padding: '4px 0' }}>
        {title}
        {hint !== undefined && hint !== null ? <span style={SUMMARY_HINT}>{hint}</span> : null}
      </summary>
      <div style={{ paddingTop: 2 }}>
        {children}
      </div>
    </details>
  )
}

export function KsSettingsSection(props: KsSettingsSectionInjected): JSX.Element {
  const { openEvidence } = props

  // 响应式读偏好：`./ksPrefs` 在任何一端写入后都会通知（含同源其他标签页的 storage 事件）。
  // 第三参（getServerSnapshot）：SSR/并发特性正确用法；客户端被忽略。
  // 缺它会让 scripts/smoke-settings.mjs 的 SSR 冒烟直接抛错（无法离线验证渲染）。
  const stored = useSyncExternalStore(
    subscribePrefs,
    () => getPrefsSnapshot().showArrow,
    () => KS_PREFS_DEFAULT.showArrow,
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const shown = stored

  // 六个类目各自的展开态（全默认收起）。展开过的数据留在组件 state 里，
  // 收起只是不再渲染/不再请求，不丢已拉到的快照。
  const [arrowOpen, setArrowOpen] = useState(false)
  const [apiOpen, setApiOpen] = useState(false)

  // 写偏好：本地存储写入是同步的，不再有"乐观覆盖 + 失败回退"的需要
  // （旧实现要它是因为写要跨到宿主侧栅栏路由，可能失败）。
  const onToggle = (next: boolean): void => {
    setError(null)
    setSaving(true)
    try {
      updatePrefs({ showArrow: next })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section style={{ padding: '8px 16px' }}>
      <p style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--dsw-alias-label-secondary, #666)' }}>
        配置「法规标准知识库」插件：证据 PDF 行为、效力报告、入库预览与巡检。
        各类目默认收起，点击展开。
      </p>

      <KsCategory title="证据查看器" open={arrowOpen} onToggle={setArrowOpen} hint="红箭头定位开关">
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>显示红色定位箭头</span>
            <span style={{ display: 'block', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
              在 PDF 证据页用红箭头标出引用条款位置；关闭后仅跳页。
            </span>
          </span>
          <input
            type="checkbox"
            checked={shown}
            disabled={saving}
            aria-label="显示红色定位箭头"
            onChange={(e) => onToggle(e.currentTarget.checked)}
          />
        </label>
        {error !== null && (
          <p role="alert" style={{ color: 'var(--dsw-alias-state-warn-primary)', fontSize: 12 }}>
            保存失败：{error}
          </p>
        )}
      </KsCategory>

      {/* ⚠ S4/S5 搬家留痕（2026-09-22）：「效力报告」→ 知识库 ▾「效力总览」页；
          「参考资料」→ 知识库 ▾「备料」页。设置只留**全局项**（业主批准的搬家批，
          搬家不改面板内部、数据口径零变化）。 */}

      {/* ⚠ S5-b 搬家留痕（2026-09-22）：渠道台账 / 每日巡检 / 公告发现（巡检族）三件
          聚进知识库 ▾「渠道台账」页位（页内三节，功能零增删）；「入库预览」撤组的原文
          留痕仍在下方（别删）。设置至此只留**全局项**：证据查看器 + API 配置。 */}

      {/* ⚠⚠ **2026-09-21（第 4 步）就地撤掉「入库预览」这一组**（原文保留在下面，别删）：
          它原来把 `KsIngestPanel`（只读体检 ✅/⚠️/❌ 分桶）挂在这里。
          业主：「不要两个页面」⇒ 导入这件事**只有一个落点**：知识库页 →「待分类」层上的
          导入面板（那里有「来源目录」+「先体检（只读）」+「导入到这一层」+「覆盖重导」）。
          这里再留一个入口就是第二个页面。**删掉的是入口，不是能力**：体检那一步已经并进
          待分类层的面板（`KsKnowledgePage.tsx` 的 `runCheck`，走同一条
          `/ks/ingest/preview/batch`，默认不外发）。
          ⚠ `KsIngestPanel.tsx` 本身**留在仓里**（它的渲染与路由判据还在
          `plugin/scripts/smoke-ingest.mjs` / `ui-render-shot.mjs` 的 `--page ingest` 上跑着）
          —— 属于"产品里已无入口、代码与判据暂留"的状态，登记在报告里；
          第 5 步若确认不再需要，连它的冒烟一起删。 */}
      <KsApiConfigSection open={apiOpen} onOpenChange={setApiOpen} />
    </section>
  )
}

/* ------------------------------------------------------------------ *
 * 「每日巡检」组（决策 19, P0 = 手动触发 + 逾期补跑；自动定时 P1 默认关）
 *
 * 数据全部来自 host 同源代理 /ks/inspection/summary（host 负责引擎保活/
 * 轮询/落盘；client 不直连引擎、不经手 token）。运行中每 ~2.5s 轮询一次
 * summary，直到批次离开 running。
 * ------------------------------------------------------------------ */

const COUNT_COLORS: Record<string, string> = {
  red: '#c0392b',
  yellow: '#b8860b',
  green: '#2e7d32',
  gray: '#888',
}

/** 红黄两色的 tooltip/图例说明（与引擎判定口径一致）。 */
const COUNT_LABELS: Record<string, string> = {
  red: '废止 / 被替代（需关注）',
  yellow: '新版（需关注）',
  green: '现行无变化',
  gray: '官方渠道查无此号',
}

/** 五类结论里"没答出来"的原因 → 人话。
 *  ⚠ 键必须与引擎 `src/core/update/channels/class_outcomes.py` 的 REASONS 对齐；
 *  最要紧的一对区别是「渠道无此字段」（问了、那根棒没这个字段）与「未轮到问」
 *  （链上有能答的棒，但这次是别的棒先命中）——**前者是能力缺口，后者不是欠账**。 */
const REASON_TEXT: Record<string, string> = {
  channel_gave_no_field: '渠道无此字段',
  not_probed: '未轮到问',
  no_capability: '没有渠道能答',
  off_chain: '能答的不在链上',
  all_down: '在链上但全挂',
  absent: '记录里没这一类',
  unknown: '原因未记',
}

/** 引擎 sqlite datetime 是 UTC 无时区（'YYYY-MM-DD HH:MM:SS'）→ 补 Z 转本地。 */
function fmtTs(value: string | null): string {
  if (!value) return ''
  const norm = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
    ? `${value.replace(' ', 'T')}Z`
    : value
  const d = new Date(norm)
  if (Number.isNaN(d.getTime())) return value
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

function statusText(s: KsInspectionSummary): { text: string; tone: string } {
  const last = s.last
  if (!last) return { text: '尚未巡检', tone: 'var(--dsw-alias-label-secondary, #666)' }
  switch (last.status) {
    case 'running':
      return {
        text: `巡检中 · ${last.checked}/${last.total}${last.total > 0 ? '' : '（准备中）'}`,
        tone: 'var(--dsw-alias-label-primary, #111)',
      }
    case 'done': {
      const base = fmtTs(last.finished_at) || fmtTs(last.started_at)
      const prefix = last.auto === true ? '今日自动巡检' : '上次巡检'
      return { text: base ? `${prefix} ${base}` : `${prefix}已完成`, tone: 'var(--dsw-alias-label-secondary, #666)' }
    }
    case 'failed':
      return { text: '上次巡检失败', tone: '#c0392b' }
    case 'paused':
      return {
        text: `上次巡检已暂停${last.pause_reason === 'budget' ? '（当日预算用尽）' : last.pause_reason === 'captcha' ? '（验证码，需人工处理）' : ''}`,
        tone: 'var(--dsw-alias-state-warn-primary)',
      }
    default:
      return { text: '上次巡检状态未知', tone: 'var(--dsw-alias-label-secondary, #666)' }
  }
}

export function KsInspectionPanel(props: { openedOnce: boolean }): JSX.Element {
  const { openedOnce } = props
  const [summary, setSummary] = useState<KsInspectionSummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expError, setExpError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState(false)

  const load = useCallback(async (): Promise<void> => {
    try {
      const s = await fetchInspectionSummary()
      setSummary(s)
      setLoadError(false)
    } catch {
      setLoadError(true)
      // 保留旧快照（可能正 running），轮询仍会重试
    }
  }, [])

  // 折叠语义（2026-11 类目全折叠）：收起零请求；首次展开才拉 summary。
  useEffect(() => {
    if (!openedOnce) return
    void load()
  }, [openedOnce, load])

  // Running 期间自动轮询（链式 setTimeout，不重叠；离开 running 即停）。
  const isRunning = summary?.last?.status === 'running'
  useEffect(() => {
    if (!isRunning) return
    let alive = true
    let timer: number | undefined
    const tick = (): void => {
      if (!alive) return
      fetchInspectionSummary()
        .then((s) => { if (alive) setSummary(s) })
        .catch(() => { /* 保留旧快照，下轮再试 */ })
        .finally(() => { if (alive) timer = window.setTimeout(tick, 2500) })
    }
    timer = window.setTimeout(tick, 1500)
    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [isRunning])

  const onRun = async (): Promise<void> => {
    if (busy || isRunning) return
    setBusy(true)
    setError(null)
    try {
      await runInspection()
      await load() // 立即反映 running → 上方轮询接管
    } catch (err) {
      if (err instanceof InspectionHttpError) {
        setError(err.message)
      } else {
        setError(err instanceof Error ? err.message : String(err))
      }
      void load()
    } finally {
      setBusy(false)
    }
  }

  const status = summary !== null ? statusText(summary) : null
  const last = summary?.last ?? null
  const overdue = summary?.overdue_days ?? 0

  /* ---- P1 每日自动巡检设置（host 状态文件为真值；乐观更新 + 失败回读） ---- */
  const settings = summary?.settings ?? null
  const [autoSaving, setAutoSaving] = useState(false)
  const [autoError, setAutoError] = useState<string | null>(null)

  const patchSettings = async (patch: { autoEnabled?: boolean; time?: string }): Promise<void> => {
    setAutoSaving(true)
    setAutoError(null)
    setSummary((prev) => (prev !== null ? { ...prev, settings: { ...prev.settings, ...patch } } : prev))
    try {
      const saved = await updateInspectionSettings(patch)
      setSummary((prev) => (prev !== null ? { ...prev, settings: saved } : prev))
    } catch (err) {
      setAutoError(err instanceof Error ? err.message : String(err))
      void load() // 失败回读真值
    } finally {
      setAutoSaving(false)
    }
  }

  /** 导出仅针对「已完成」的上一批次（running 中禁用；从未跑过无 last 也禁用）。 */
  const canExport = last !== null && last.status !== 'running'
  const onExport = async (): Promise<void> => {
    if (!canExport || exporting) return
    setExporting(true)
    setExpError(null)
    try {
      await exportInspectionResult()
    } catch (err) {
      setExpError(err instanceof Error ? err.message : String(err))
    } finally {
      setExporting(false)
    }
  }

  const colorDot = (c: string, n: number): React.ReactNode => (
    <span key={c} title={COUNT_LABELS[c]} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: c, fontSize: 12 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
      {n}
    </span>
  )

  return (
    <div style={{ borderTop: '1px solid var(--dsw-alias-border-l1, #eee)', marginTop: 4, paddingTop: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0 2px' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>每日巡检（关注标准）</span>
        {overdue > 0 && last?.status === 'done' && (
          <span style={{ fontSize: 12, color: '#b8860b', border: '1px solid #b8860b55', borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
            已逾期 {overdue} 天
          </span>
        )}
        {summary?.stale_run === true && (
          <span style={{ fontSize: 12, color: '#c0392b', border: '1px solid #c0392b55', borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
            上次疑似中断
          </span>
        )}
      </div>
      <p style={{ margin: '2px 0 8px', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
        对照官网公告检查关注标准/收藏标准是否出现新版、废止或替代；仅比对不改库，变更以三色列出。
      </p>

      {loadError && summary === null && (
        <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '0 0 6px' }}>
          巡检状态读取失败（host 路由不可用？请刷新重试）
        </p>
      )}

      {last !== null && last.status === 'failed' && (
        <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '0 0 6px' }}>
          {last.error ?? '巡检批次失败'}
        </p>
      )}

      {status !== null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 0 4px' }}>
          <span style={{ color: status.tone, fontSize: 13 }}>
            {isRunning ? '⏳' : last?.status === 'done' ? '✅' : last?.status === 'failed' ? '❌' : ''} {status.text}
          </span>
          {last !== null && last.total > 0 && last.status !== 'running' && (
            <span style={{ display: 'inline-flex', gap: 10 }}>
              {(['red', 'yellow', 'green', 'gray'] as const).map((k) => colorDot(k, last.counts[k]))}
            </span>
          )}
        </div>
      )}

      {/* 纵览统计：只给数字总览，不给逐条清单（万级明细在 UI 展开无意义——
          需要逐条看时用「导出巡查结果」拿 Excel）。 */}
      {last !== null && last.by_type !== null && last.status !== 'running' && (
        <div style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)', padding: '0 0 4px', lineHeight: '18px' }}>
          {(() => {
            const bt = last.by_type
            if (last.total === 0) {
              // tier0 = 关注面(收藏/盯板/订阅) ∪ 未首检；两者皆空 → 空转批次（正常语义）
              return '本次巡检清单为空：关注面暂无标准、也无新入库待首检文档——收藏标准或导入新文档后再巡检'
            }
            const sum = bt.new_version + bt.superseded + bt.withdrawn + bt.not_found + bt.no_change
            if (sum < last.total) {
              // 旧状态文件的细分缺失（全 0）且启动自愈尚未跑：不做"全部无变化"断言
              return `共检 ${last.total} 项 · 细分统计将在下次巡检时生成`
            }
            const attention = bt.superseded + bt.withdrawn + bt.new_version
            if (attention === 0 && bt.not_found === 0) {
              return `本次共检 ${last.total} 项 · 全部现行无变化`
            }
            const focus: string[] = []
            if (bt.withdrawn > 0) focus.push(`废止 ${bt.withdrawn}`)
            if (bt.superseded > 0) focus.push(`被替代 ${bt.superseded}`)
            if (bt.new_version > 0) focus.push(`新版 ${bt.new_version}`)
            const other: string[] = []
            if (bt.not_found > 0) other.push(`查无 ${bt.not_found}`)
            if (bt.no_change > 0) other.push(`无变化 ${bt.no_change}`)
            const focusText = focus.length > 0 ? ` · 需关注 ${attention} 项（${focus.join(' / ')}）` : ''
            const otherText = other.length > 0 ? ` · ${other.join(' / ')}` : ''
            return `共检 ${last.total} 项${focusText}${otherText}`
          })()}
        </div>
      )}

      {/* 五类结论：引擎从 R6c-4c 起就在每条变更事件里记「发布/修订/废止/现行性/编号核验」
          各自答没答、是哪根渠道答的、答得全不全——但**面板一直没读它**（数据在库里躺着）。
          这一行就是把它显示出来：每类"答出几个 / 一共几个有记录的"，外加未答主因。 */}
      {last !== null && last.status !== 'running' && last.by_class !== null
        && last.by_class !== undefined && (
        <div style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)',
                      padding: '0 0 4px', lineHeight: '18px' }}
             title={'分母只算记了五类结论的事件数；没记的如实单列'
               + `（本次 ${last.by_class.unreadable} 条没记）`}>
          {(() => {
            const bc = last.by_class
            if (bc.total === 0) {
              return `五类结论：本批没有记录（${bc.unreadable} 条事件未带五类信息）`
                + '——引擎侧读台账失败或旧数据时就是这样，不代表"都没有欠账"'
            }
            const order = ['发布', '修订', '废止', '现行性', '编号核验']
            const per = order
              .filter((c) => bc.classes[c] !== undefined)
              .map((c) => `${c} ${bc.classes[c]?.answered ?? 0}/${bc.total}`)
              .join(' · ')
            // 未答主因（跨类合计，取前 3）：区分"渠道没这个字段"与"这次没轮到问它"
            const totals: Record<string, number> = {}
            for (const c of order) {
              const st = bc.classes[c]
              if (!st) continue
              for (const [r, n] of Object.entries(st.reasons ?? {})) {
                totals[r] = (totals[r] ?? 0) + (Number(n) || 0)
              }
            }
            const top = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 3)
            const topText = top.length === 0
              ? '全部答出'
              : top.map(([r, n]) => `${REASON_TEXT[r] ?? r} ${n}`).join(' / ')
            const unread = bc.unreadable > 0 ? ` · 另有 ${bc.unreadable} 条未记五类` : ''
            return `五类结论：${per}（未答主因：${topText}）${unread}`
          })()}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => void onRun()}
          disabled={busy || isRunning || loadError}
          style={{
            padding: '4px 14px',
            borderRadius: 6,
            // 按钮配色成对固定，不拆开跟主题 token——背景与文字分属两个变量域时
            // 会在深色主题下撞成白字白底（用户实测）。浅底深字，黑白两种主题都清晰。
            border: `1px solid ${busy || isRunning || loadError ? '#c4c4c4' : '#7f7f7f'}`,
            background: busy || isRunning || loadError ? '#e9e9e9' : '#ffffff',
            color: busy || isRunning || loadError ? '#5a5a5a' : '#111111',
            cursor: busy || isRunning ? 'default' : 'pointer',
            fontSize: 13,
          }}
        >
          {busy ? '启动中…' : isRunning ? '巡检中…' : overdue > 0 ? '补跑今日巡检' : '今日巡检（tier0）'}
        </button>
        <button
          type="button"
          onClick={() => void onExport()}
          disabled={!canExport || exporting || loadError}
          title={canExport ? '导出上一次巡检结果（Excel：汇总/明细/趋势）' : '需先完成一次巡检'}
          style={{
            padding: '4px 14px',
            borderRadius: 6,
            border: `1px solid ${!canExport || exporting || loadError ? '#c4c4c4' : '#7f7f7f'}`,
            background: !canExport || exporting || loadError ? '#e9e9e9' : '#ffffff',
            color: !canExport || exporting || loadError ? '#5a5a5a' : '#111111',
            cursor: !canExport || exporting ? 'default' : 'pointer',
            fontSize: 13,
          }}
        >
          {exporting ? '导出中…' : '导出巡查结果（Excel）'}
        </button>
        {expError !== null && (
          <span role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{expError}</span>
        )}
        {error !== null && (
          <span role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{error}</span>
        )}
      </div>
      {/* P1 每日自动巡检设置：host 定时器消费（30s tick，到点即跑；dsh 晚开补当天一次） */}
      <div style={{ borderTop: '1px solid var(--dsw-alias-border-l1, #eee)', marginTop: 6, paddingTop: 2 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0 2px' }}>
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>
              每日自动巡检
            </span>
            <span style={{ display: 'block', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
              开启后每日 {settings?.time ?? '08:30'} 自动检查关注面；dsh 未开启时，下次启动补跑当天一次。
            </span>
          </span>
          <input
            type="checkbox"
            checked={settings?.autoEnabled === true}
            disabled={autoSaving || settings === null}
            aria-label="每日自动巡检"
            onChange={(e) => void patchSettings({ autoEnabled: e.currentTarget.checked })}
          />
        </label>
        {settings?.autoEnabled === true && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 0' }}>
            <span style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>每日时点</span>
            <input
              type="time"
              value={settings.time}
              disabled={autoSaving}
              aria-label="每日巡检时点"
              onChange={(e) => {
                const v = e.currentTarget.value
                if (/^([01]\d|2[0-3]):[0-5]\d$/.test(v)) void patchSettings({ time: v })
              }}
              style={{ fontSize: 12, padding: '2px 6px' }}
            />
            <span style={{ fontSize: 12, color: 'var(--dsw-alias-label-secondary, #999)' }}>
              周日 tier1 全库滚动（P2 开放）
            </span>
          </label>
        )}
        {autoError !== null && (
          <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '2px 0 0' }}>
            保存失败：{autoError}
          </p>
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * 「公告发现」组（语义 C：自定义公告源 → 随巡检定期"看新公告" → 轻通知）
 *
 * 数据来自 host 同源代理 /ks/announce/*：summary 为本地快照（绝不拉起引擎）；
 * 源管理 details 默认收起、展开才拉清单（打开设置页不拉起引擎）。running 期间
 * 2.5s 轮询同巡检模式。解析失败（WAF/JS 壳/0 条）按源诚实归因，绝不假装成功。
 * ------------------------------------------------------------------ */

const REASON_LABELS: Record<string, string> = {
  waf_captcha: 'WAF/验证码拦截',
  js_shell_suspected: '疑似 JS 渲染（无可解析链接）',
  parse_empty: '解析 0 条（页面结构不同）',
  skipped_timeout: '扫描超时跳过',
  unreachable: '网络不可达',
}

function sourceStatusText(p: KsAnnouncePerSource | undefined): string {
  if (p === undefined) return '本轮未扫'
  if (p.status === 'ok') {
    const parts: string[] = []
    if (p.baseline_items > 0) parts.push(`收录 ${p.baseline_items}`)
    if (p.new_items > 0) parts.push(`新 ${p.new_items}`)
    if (parts.length === 0) parts.push(`${p.items} 条已见`)
    return `✅ ${parts.join(' · ')}`
  }
  if (p.status === 'failed') {
    const label = p.reason !== null ? REASON_LABELS[p.reason] : undefined
    return `❌ ${label ?? p.reason ?? '失败'}`
  }
  return `⏸ ${p.reason ?? p.status}`
}

export function KsAnnounceSourcesSection(props: { openedOnce: boolean }): JSX.Element {
  const { openedOnce } = props
  const [summary, setSummary] = useState<KsAnnounceSummary | null>(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [sources, setSources] = useState<KsAnnounceSource[] | null>(null)
  const [sourcesError, setSourcesError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const load = useCallback(async (): Promise<void> => {
    try {
      const s = await fetchAnnounceSummary()
      setSummary(s)
      setLoadError(false)
    } catch {
      setLoadError(true) // 保留旧快照
    }
  }, [])

  // 折叠语义（2026-11 类目全折叠）：收起零请求；首次展开才拉 summary。
  // 源管理子 details 原本就是展开才拉清单，与此正交。
  useEffect(() => {
    if (!openedOnce) return
    void load()
  }, [openedOnce, load])

  // 扫描 running 期间自动轮询（链式 setTimeout 不重叠）
  const isRunning = summary?.last?.status === 'running'
  useEffect(() => {
    if (!isRunning) return
    let alive = true
    let timer: number | undefined
    const tick = (): void => {
      if (!alive) return
      fetchAnnounceSummary()
        .then((s) => { if (alive) setSummary(s) })
        .catch(() => { /* 保留旧快照 */ })
        .finally(() => { if (alive) timer = window.setTimeout(tick, 2500) })
    }
    timer = window.setTimeout(tick, 1500)
    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [isRunning])

  const onScan = async (): Promise<void> => {
    if (scanning || isRunning) return
    setScanning(true)
    setError(null)
    try {
      await scanAnnounceSources()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      void load()
    } finally {
      setScanning(false)
    }
  }

  const [exportingAnn, setExportingAnn] = useState(false)
  const [annExportError, setAnnExportError] = useState<string | null>(null)
  const onAnnExport = async (): Promise<void> => {
    if (exportingAnn) return
    setExportingAnn(true)
    setAnnExportError(null)
    try {
      await exportAnnounceDiscovery()
    } catch (err) {
      setAnnExportError(err instanceof Error ? err.message : String(err))
    } finally {
      setExportingAnn(false)
    }
  }

  /* ---- 正文入库（2026-09-24 切片②下半）：业主报"应该入库的怎么没入库"，这是收口处。
     进度是**展开这一格才拉**（与源管理同一纪律：打开设置页不拉起引擎、不抓网页）。 */
  const [ingestPending, setIngestPending] = useState<KsAnnounceIngestPending | null>(null)
  const [ingesting, setIngesting] = useState(false)
  const [ingestResult, setIngestResult] = useState<KsAnnounceIngestResult | null>(null)
  const [ingestError, setIngestError] = useState<string | null>(null)
  const [ingestForce, setIngestForce] = useState(false)

  const loadIngestPending = useCallback(async (): Promise<void> => {
    setIngestError(null)
    try {
      setIngestPending(await fetchAnnounceIngestPending())
    } catch (err) {
      const notLoaded = err instanceof InspectionHttpError && err.httpStatus === 404
      setIngestError(notLoaded
        ? '这个入口还没被主程序加载：请重启一次 DSH 再展开这里'
        : err instanceof Error ? err.message : String(err))
    }
  }, [])

  const onIngest = async (): Promise<void> => {
    if (ingesting) return
    setIngesting(true)
    setIngestError(null)
    try {
      const r = await ingestAnnouncements({ limit: 10, force: ingestForce })
      setIngestResult(r)
      await loadIngestPending()
      await load()
    } catch (err) {
      // ⚠ 404 这个错**不是**"抓取失败"：它多半是"宿主还没加载新加的那条通道"
      // （宿主侧的插件模块要 DSH 重启一次才会换成新的；引擎与界面是热更新的）。
      // 说清楚该干什么，比把 HTTP 404 扔给业主强。
      const notLoaded = err instanceof InspectionHttpError && err.httpStatus === 404
      setIngestError(notLoaded
        ? '这个入口还没被主程序加载：请重启一次 DSH，再回来点它（数据不会丢，公告都还在）'
        : err instanceof Error ? err.message : String(err))
      void loadIngestPending()
    } finally {
      setIngesting(false)
    }
  }

  const loadSources = useCallback(async (): Promise<void> => {
    setSourcesError(null)
    try {
      const d = await fetchAnnounceSources()
      setSources(d.sources)
    } catch (err) {
      setSourcesError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  const onAdd = async (): Promise<void> => {
    if (adding || !newName.trim() || !newUrl.trim()) return
    setAdding(true)
    setAddError(null)
    try {
      await addAnnounceSource(newName.trim(), newUrl.trim())
      setNewName('')
      setNewUrl('')
      await loadSources()
      await load()
    } catch (err) {
      setAddError(err instanceof Error ? err.message : String(err))
    } finally {
      setAdding(false)
    }
  }

  const onToggleEnabled = async (src: KsAnnounceSource, next: boolean): Promise<void> => {
    try {
      await updateAnnounceSource(src.id, { enabled: next })
      await loadSources()
    } catch (err) {
      setSourcesError(err instanceof Error ? err.message : String(err))
    }
  }

  const onRemove = async (src: KsAnnounceSource): Promise<void> => {
    if (!window.confirm(`删除公告源「${src.name}」？（历史公告记录保留）`)) return
    try {
      await removeAnnounceSource(src.id)
      await loadSources()
      await load()
    } catch (err) {
      setSourcesError(err instanceof Error ? err.message : String(err))
    }
  }

  const last = summary?.last ?? null
  const failedCount = last?.per_source.filter((p) => p.status === 'failed').length ?? 0

  return (
    <div style={{ borderTop: '1px solid var(--dsw-alias-border-l1, #eee)', marginTop: 4, paddingTop: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0 2px', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>公告发现（自定义公告源）</span>
        {summary?.stale_run === true && (
          <span style={{ fontSize: 12, color: '#c0392b', border: '1px solid #c0392b55', borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
            上次扫描疑似中断
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 0 4px', flexWrap: 'wrap', fontSize: 13 }}>
        {isRunning ? (
          <span style={{ color: 'var(--dsw-alias-label-primary, #111)' }}>
            ⏳ 扫描中 · {last?.sources_done ?? 0}/{last?.sources_total ?? 0} 源
          </span>
        ) : last?.status === 'done' ? (
          <>
            <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>
              最近扫描 {fmtTs(last.finished_at)}
            </span>
            {last.baseline_count > 0 && (
              <span style={{ color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 12 }}>
                收录 {last.baseline_count}
              </span>
            )}
            {last.new_count > 0 && (
              <span style={{ fontSize: 12, color: '#b8860b', border: '1px solid #b8860b55', borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
                新 {last.new_count} 条
              </span>
            )}
            {failedCount > 0 && (
              <span style={{ fontSize: 12, color: '#c0392b', border: '1px solid #c0392b55', borderRadius: 4, padding: '0 6px', lineHeight: '18px' }}>
                失败 {failedCount} 个源
              </span>
            )}
          </>
        ) : last?.status === 'failed' ? (
          <span style={{ color: '#c0392b', fontSize: 13 }}>
            上次扫描失败{last.error ? `：${last.error}` : ''}
          </span>
        ) : (
          <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>尚未扫描</span>
        )}
      </div>
      <p style={{ margin: '2px 0 8px', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
        添加官方公告列表页地址，随每日巡检自动检查新公告；仅支持公网 http/https，解析失败会如实显示原因。
      </p>

      {loadError && summary === null && (
        <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '0 0 6px' }}>
          公告状态读取失败（host 路由不可用？请刷新重试）
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
        <button
          type="button"
          onClick={() => void onScan()}
          disabled={scanning || isRunning || loadError}
          style={{
            padding: '4px 14px',
            borderRadius: 6,
            // 配色成对固定（同「今日巡检」按钮，黑白主题都清晰）
            border: `1px solid ${scanning || isRunning || loadError ? '#c4c4c4' : '#7f7f7f'}`,
            background: scanning || isRunning || loadError ? '#e9e9e9' : '#ffffff',
            color: scanning || isRunning || loadError ? '#5a5a5a' : '#111111',
            cursor: scanning || isRunning ? 'default' : 'pointer',
            fontSize: 13,
          }}
        >
          {scanning ? '启动中…' : isRunning ? '扫描中…' : '扫描公告源'}
        </button>
        <button
          type="button"
          onClick={() => void onAnnExport()}
          disabled={exportingAnn || loadError}
          title="导出公告发现 Excel（最近扫描源状态 + 公告明细全量）"
          style={{
            padding: '4px 14px',
            borderRadius: 6,
            border: `1px solid ${exportingAnn || loadError ? '#c4c4c4' : '#7f7f7f'}`,
            background: exportingAnn || loadError ? '#e9e9e9' : '#ffffff',
            color: exportingAnn || loadError ? '#5a5a5a' : '#111111',
            cursor: exportingAnn ? 'default' : 'pointer',
            fontSize: 13,
          }}
        >
          {exportingAnn ? '导出中…' : '导出公告发现（Excel）'}
        </button>
        {annExportError !== null && (
          <span role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{annExportError}</span>
        )}
        {error !== null && (
          <span role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{error}</span>
        )}
      </div>

      {/* 正文入库（切片②下半）：把"已发现但正文还没进库"的公告抓进来。
          ⚠ 这一格是**展开才拉进度**（与源管理同一纪律：打开设置页不抓网页）。 */}
      <details
        style={{ fontSize: 12, margin: '2px 0', color: 'var(--dsw-alias-label-secondary, #666)' }}
        onToggle={(e) => {
          if ((e.currentTarget as HTMLDetailsElement).open && ingestPending === null) {
            void loadIngestPending()
          }
        }}
      >
        <summary style={{ cursor: 'pointer' }}>
          把公告正文入库
          {ingestPending !== null ? `（还有 ${ingestPending.pending} 条没进库）` : '（展开加载）'}
        </summary>
        <div style={{ margin: '6px 0 0' }}>
          {ingestPending === null ? (
            <p style={{ margin: '0 0 6px' }}>加载中…</p>
          ) : (
            <p style={{ margin: '0 0 6px', lineHeight: '18px' }}>
              已发现 {ingestPending.total} 条，其中 {ingestPending.ingested} 条已经进库；
              还有 <b>{ingestPending.pending}</b> 条没进库
              （现行 {ingestPending.pending_by_status.effective} ·
              仅参考 {ingestPending.pending_by_status.reference} ·
              已废止 {ingestPending.pending_by_status.withdrawn}）。
              {ingestPending.skipped_non_normative > 0
                ? `另有 ${ingestPending.skipped_non_normative} 条按"不属法规标准"跳过（部门决算/公示/挂牌督办那类）。`
                : ''}
            </p>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '2px 0' }}>
            {/* ⚠ 这一格的颜色**全走活的主题 token**（不像上面两个老按钮写死十六进制）：
                `smoke-client-entry` 有一条"写死颜色只许减不许增"的棘轮，而业主明确要
                深浅两套配色 —— 新写的按钮就不该再往那笔债上加。禁用态用 `opacity` 表达，
                免得为一个状态再写死一组灰色。 */}
            <button
              type="button"
              onClick={() => void onIngest()}
              disabled={ingesting || (ingestPending !== null && ingestPending.pending === 0 && !ingestForce)}
              title="抓正文并进知识库（一次最多 10 条，可能要等十几秒；再点一次继续剩下的）"
              style={{
                padding: '4px 14px',
                borderRadius: 6,
                border: '1px solid var(--dsw-alias-border-l2)',
                background: 'var(--dsw-alias-bg-base)',
                color: 'var(--dsw-alias-label-primary)',
                opacity: ingesting ? 0.5 : 1,
                cursor: ingesting ? 'default' : 'pointer',
                fontSize: 13,
              }}
            >
              {ingesting ? '入库中…（正在抓正文）' : '把新公告入库（每次 10 条）'}
            </button>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <input
                type="checkbox"
                checked={ingestForce}
                onChange={(e) => { setIngestForce(e.target.checked) }}
              />
              连"部门决算/公示"那类也入
            </label>
          </div>
          {ingestError !== null && (
            <p role="alert" style={{ color: 'var(--dsw-alias-state-error-primary)', margin: '4px 0 0' }}>
              {ingestError}
            </p>
          )}
          {ingestResult !== null && (
            <p role="status" style={{ margin: '4px 0 0', lineHeight: '18px' }}>
              本次抓了 {ingestResult.tried} 条：入进知识库 {ingestResult.ingested} 条
              （现行 {ingestResult.by_status.effective} ·
              仅参考 {ingestResult.by_status.reference} ·
              已废止 {ingestResult.by_status.withdrawn}）
              {ingestResult.skipped > 0 ? `，跳过 ${ingestResult.skipped} 条（库里已经有、或不属于法规标准）` : ''}
              {ingestResult.failed > 0 ? `，失败 ${ingestResult.failed} 条（下次再点会重试）` : ''}
              。还剩 {ingestResult.pending_left} 条没进库
              {ingestResult.stop_reason === 'budget' ? '（这次时间到了、没做完，再点一次继续）' : ''}
              {ingestResult.stop_reason === 'limit' ? '（这一批抓满了，再点一次继续）' : ''}
              {ingestResult.failed > 0
                ? `　失败原因：${ingestResult.items
                  .filter((it) => it.status === 'failed')
                  .slice(0, 3)
                  .map((it) => `${it.title.slice(0, 18)}…（${it.reason ?? '未知'}）`)
                  .join('；')}`
                : ''}
            </p>
          )}
        </div>
      </details>

      <details style={{ fontSize: 12, margin: '2px 0', color: 'var(--dsw-alias-label-secondary, #666)' }}>
        <summary style={{ cursor: 'pointer' }}>最近公告（{last?.recent.length ?? 0} 条，点击展开）</summary>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {(last?.recent ?? []).map((r, i) => (
            <li key={`${r.url}-${i}`} style={{ lineHeight: '20px' }}>
              <a href={r.url} target="_blank" rel="noreferrer" style={{ color: 'var(--dsw-alias-label-primary, #111)' }}>
                {r.title}
              </a>
              <span style={{ color: 'var(--dsw-alias-label-secondary, #888)' }}>
                {r.source_name ? ` · ${r.source_name}` : ''}{r.published_date ? ` · ${r.published_date}` : ''}
              </span>
            </li>
          ))}
          {(last?.recent.length ?? 0) === 0 && <li style={{ listStyle: 'none', marginLeft: -18 }}>暂无记录（扫描后显示最近 5 条）</li>}
        </ul>
      </details>

      <details
        style={{ fontSize: 12, margin: '2px 0', color: 'var(--dsw-alias-label-secondary, #666)' }}
        onToggle={(e) => {
          if ((e.currentTarget as HTMLDetailsElement).open && sources === null) {
            void loadSources()
          }
        }}
      >
        <summary style={{ cursor: 'pointer' }}>
          源管理（{sources === null ? '展开加载' : `${sources.length} 个`}）
        </summary>
        {sources === null ? (
          <p style={{ margin: '6px 0 0' }}>加载中…</p>
        ) : sources.length === 0 ? (
          <p style={{ margin: '6px 0 0' }}>还没有公告源——在下方添加第一个。</p>
        ) : (
          <div style={{ margin: '6px 0 0' }}>
            {sources.map((src) => {
              const ps = last?.per_source.find((p) => p.id === src.id)
              return (
                <div key={src.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0', flexWrap: 'wrap' }}>
                  <input
                    type="checkbox"
                    checked={src.enabled !== false}
                    aria-label={`启用 ${src.name}`}
                    onChange={(e) => void onToggleEnabled(src, e.currentTarget.checked)}
                  />
                  <span style={{ color: 'var(--dsw-alias-label-primary, #111)', minWidth: 90 }}>{src.name}</span>
                  <span title={src.url} style={{ color: 'var(--dsw-alias-label-secondary, #888)', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {src.url}
                  </span>
                  <span>{sourceStatusText(ps)}</span>
                  <button
                    type="button"
                    onClick={() => void onRemove(src)}
                    style={{ border: '1px solid #c4c4c4', background: '#ffffff', color: '#5a5a5a', borderRadius: 4, fontSize: 11, padding: '1px 8px', cursor: 'pointer' }}
                  >
                    删除
                  </button>
                </div>
              )
            })}
          </div>
        )}
        {sourcesError !== null && (
          <p role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{sourcesError}</p>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
          <input
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
            placeholder="源名称（如 应急部标准公告）"
            style={{ fontSize: 12, padding: '3px 8px', width: 170 }}
          />
          <input
            value={newUrl}
            onChange={(e) => setNewUrl(e.currentTarget.value)}
            placeholder="https://…（公告列表页地址）"
            style={{ fontSize: 12, padding: '3px 8px', flex: 1, minWidth: 220 }}
          />
          <button
            type="button"
            onClick={() => void onAdd()}
            disabled={adding || !newName.trim() || !newUrl.trim()}
            style={{
              padding: '3px 14px', borderRadius: 6, fontSize: 12,
              border: `1px solid ${adding || !newName.trim() || !newUrl.trim() ? '#c4c4c4' : '#7f7f7f'}`,
              background: adding || !newName.trim() || !newUrl.trim() ? '#e9e9e9' : '#ffffff',
              color: adding || !newName.trim() || !newUrl.trim() ? '#5a5a5a' : '#111111',
              cursor: adding ? 'default' : 'pointer',
            }}
          >
            {adding ? '添加中…' : '添加源'}
          </button>
        </div>
        {addError !== null && (
          <p role="alert" style={{ color: '#c0392b', fontSize: 12 }}>{addError}</p>
        )}
      </details>
    </div>
  )
}

/* ------------------------------------------------------------------ *
 * 「API配置」组（2026-09-08）：云 OCR / LLM 凭据（可折叠，默认收起）
 *
 * 通道语义（用户修订）：导入文件时——配置了云 OCR Key → 云优先、本地兜底；
 * 未配置 → 直接本地通道（纯本地不外发）。凭据由引擎写入**加密存储**
 * （<data_dir>/secrets.json，Windows DPAPI；2026-09-12 迁移整改后注册表
 * 只作只读覆盖、引擎绝不写），前端与 host 均不回显 Key（只显示「已配置」状态）。
 * ------------------------------------------------------------------ */

/** 按钮成对固定配色（同巡检/公告按钮：白底深字，黑白主题都清晰）。
 *  注：曾误用 KsReportTab 里的同名局部 helper 导致 ReferenceError（栏目白屏，
 *  由 scripts/smoke-settings.mjs 的 SSR 冒烟抓出）——本文件的 helper 就地定义。 */
function btnStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '3px 12px', borderRadius: 6, fontSize: 12,
    border: `1px solid ${disabled ? '#c4c4c4' : '#7f7f7f'}`,
    background: disabled ? '#e9e9e9' : '#ffffff',
    color: disabled ? '#5a5a5a' : '#111111',
    cursor: disabled ? 'default' : 'pointer',
  }
}

function KsApiConfigSection(props: { open: boolean; onOpenChange: (next: boolean) => void }): JSX.Element {
  const { open, onOpenChange } = props
  const [status, setStatus] = useState<KsApiConfigStatus | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [cloudKey, setCloudKey] = useState('')
  const [cloudUrl, setCloudUrl] = useState('')
  // 2026-09-15：MinerU 云解析模式（用户要求「设置里除了填 KEY 还能选模式」）。
  // 空串 = 未改动（保存时不发 model_version，保持引擎现值）。
  const [cloudMode, setCloudMode] = useState('')
  const [llmKey, setLlmKey] = useState('')
  const [llmUrl, setLlmUrl] = useState('')
  const [tests, setTests] = useState<Record<string, { ok: boolean; detail: string } | null>>({})

  const load = useCallback(async (): Promise<void> => {
    try {
      setStatus(await fetchApiConfig())
      setErr(null)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    }
  }, [])

  // 首次展开才拉配置状态（原 details 上的展开才拉；2026-11 open 提升到父级
  // 后改由 props 驱动。收起零请求；再收起/再展开不重复拉）。
  const [openedOnce, setOpenedOnce] = useState(false)
  useEffect(() => {
    if (!open || openedOnce) return
    setOpenedOnce(true)
    void load()
  }, [open, openedOnce, load])

  const onSave = async (ch: KsApiChannel, key: string, url: string,
    mode?: string): Promise<void> => {
    const payload: {
      mineru_cloud?: { api_key?: string; base_url?: string; model_version?: string }
      llm?: { api_key?: string; base_url?: string }
    } = {}
    const sec: { api_key?: string; base_url?: string; model_version?: string } = {}
    if (key.trim()) sec.api_key = key.trim()
    if (url.trim()) sec.base_url = url.trim()
    // 模式只在该通道且确有改动时发（'' = 未改动，保持引擎现值）
    if (ch === 'mineru_cloud' && mode) sec.model_version = mode
    if (Object.keys(sec).length === 0) {
      setErr('请填写 Key / Base URL，或选择模式（留空表示保持现值）')
      return
    }
    payload[ch] = sec
    setBusy(`save-${ch}`)
    setErr(null)
    try {
      setStatus(await saveApiConfig(payload))
      // verifier F7：保存后旧探测结论已失效（它测的是旧凭据）→ 清掉，防误读
      setTests((prev) => ({ ...prev, [ch]: null }))
      if (ch === 'mineru_cloud') { setCloudKey(''); setCloudUrl('') } else { setLlmKey(''); setLlmUrl('') }
      // 模式提交后回到「未改动」态（下拉显示改为跟随 status 现值）
      setCloudMode('')
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(null)
    }
  }

  const onTest = async (ch: KsApiChannel): Promise<void> => {
    setBusy(`test-${ch}`)
    try {
      const r = await testApiChannel(ch)
      setTests((prev) => ({ ...prev, [ch]: r }))
    } catch (e) {
      setTests((prev) => ({ ...prev, [ch]: { ok: false, detail: e instanceof Error ? e.message : String(e) } }))
    } finally {
      setBusy(null)
    }
  }

  const chan = (ch: KsApiChannel, label: string, keyVal: string, setKey: (v: string) => void,
    urlVal: string, setUrl: (v: string) => void,
    modeSlot?: JSX.Element, modeDirty = false): JSX.Element => {
    const st = status?.[ch]
    const configured = st?.configured === true
    const t = tests[ch]
    // verifier F7：探测走的是**已保存**的凭据——有未保存输入时先拦住，
    // 否则用户会拿旧 Key 的探测结果去判断刚粘贴的新 Key（误判）。
    const dirty = keyVal.trim().length > 0 || urlVal.trim().length > 0 || modeDirty
    return (
      <div style={{ marginTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>{label}</span>
          <span style={{
            fontSize: 11, padding: '0 6px', lineHeight: '17px', borderRadius: 4,
            color: configured ? '#2e7d32' : '#888',
            border: `1px solid ${configured ? '#2e7d3255' : '#88888855'}`,
          }}>
            {configured ? '已配置' : '未配置'}
          </span>
          {st?.base_url && (
            <span style={{ fontSize: 11, color: 'var(--dsw-alias-label-secondary, #888)' }}>
              当前生效 {st.base_url}
            </span>
          )}
          {ch === 'mineru_cloud' && st?.model_version && (
            <span style={{ fontSize: 11, color: 'var(--dsw-alias-label-secondary, #888)' }}>
              · 模式 {st.model_version}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
          <input
            type="password"
            autoComplete="off"
            value={keyVal}
            onChange={(e) => setKey(e.currentTarget.value)}
            placeholder={configured ? 'Key 已配置（留空保持不变；输 "-" 清除）' : '粘贴 API Key'}
            style={{ fontSize: 12, padding: '3px 8px', width: 220 }}
          />
          <input
            value={urlVal}
            onChange={(e) => setUrl(e.currentTarget.value)}
            placeholder='Base URL（留空保持不变；输 "-" 恢复内置默认）'
            style={{ fontSize: 12, padding: '3px 8px', flex: 1, minWidth: 200 }}
          />
          {modeSlot}
          <button type="button" disabled={busy !== null}
            onClick={() => void onSave(ch, keyVal, urlVal,
              ch === 'mineru_cloud' && modeDirty ? effectiveCloudMode : undefined)}
            style={btnStyle(busy !== null)}>
            {busy === `save-${ch}` ? '保存中…' : '保存'}
          </button>
          <button type="button" disabled={busy !== null || dirty}
            title={dirty ? '有未保存的修改：先点「保存」再测试' : undefined}
            onClick={() => void onTest(ch)}
            style={btnStyle(busy !== null || dirty)}>
            {busy === `test-${ch}` ? '测试中…' : (dirty ? '先保存再测试' : '🧪 测试连通')}
          </button>
        </div>
        {dirty && (
          <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--dsw-alias-label-secondary, #888)' }}>
            探测使用已保存的凭据；新填的 Key / Base URL / 模式请先保存。
            留空表示保持不变，输入 <code>-</code> 表示清除该值（Key 清除后回到纯本地通道）。
          </p>
        )}
        {t && (
          <p style={{ margin: '3px 0 0', fontSize: 12, color: t.ok ? '#2e7d32' : '#c0392b' }}>
            {t.ok ? '✅ ' : '❌ '}{t.detail}
          </p>
        )}
      </div>
    )
  }

  // ---- 云 OCR 模式（MinerU v4：pipeline 默认 / vlm 推荐 / MinerU-HTML）----
  // 可选值由引擎给（前端不硬编码契约）；未改动时下拉跟随引擎现值。
  const cloudModes: string[] = status?.mineru_cloud.model_versions
    ?? ['pipeline', 'vlm', 'MinerU-HTML']
  const savedCloudMode = status?.mineru_cloud.model_version ?? 'pipeline'
  const effectiveCloudMode = cloudMode || savedCloudMode
  const cloudModeDirty = cloudMode !== '' && cloudMode !== savedCloudMode
  const MODE_HINT: Record<string, string> = {
    pipeline: 'pipeline（默认）：版面分析 + OCR 流水线，表格/公式各走专用模型，稳定可预期。',
    vlm: 'vlm（推荐）：端到端视觉大模型，复杂版式与扫描件更强；enable_formula 对 vlm 只影响行内公式，enable_table 仍生效。',
    'MinerU-HTML': 'MinerU-HTML：仅用于 HTML 源文件（PDF 请勿选）。',
  }
  const cloudModeSlot = (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
      <span style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>模式</span>
      <select
        value={effectiveCloudMode}
        onChange={(e) => setCloudMode(e.currentTarget.value)}
        title={MODE_HINT[effectiveCloudMode] ?? ''}
        style={{
          fontSize: 12, padding: '3px 6px',
          border: `1px solid ${cloudModeDirty ? '#c0392b' : '#b9b9b9'}`,
          borderRadius: 6, background: '#fff', color: '#111',
        }}
      >
        {cloudModes.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>
      {cloudModeDirty && (
        <span style={{ fontSize: 11, color: '#c0392b' }}>未保存</span>
      )}
    </span>
  )

  return (
    <details
      open={open}
      /* ⚠ `data-ks-cat`（2026-09-21，第 4 步复核打回后加）：让"设置里有哪几个类目"成为
         **机械可抽**的事实。这一组（API配置）**不走 KsCategory**（它有自己的一对
         open/onOpenChange），所以它必须自己带上这个锚点 —— 否则
         `smoke-settings.mjs` 的类目集合判据会把它算成"少了一组"（这正是它该有的行为：
         没锚点 = 判不出来 = 红）。 */
      data-ks-cat="API配置"
      onToggle={(e) => onOpenChange((e.currentTarget as HTMLDetailsElement).open)}
      style={{ borderTop: '1px solid var(--dsw-alias-border-l1, #eee)', marginTop: 4, paddingTop: 6 }}
    >
      <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)', fontSize: 13, padding: '4px 0' }}>
        API配置
        <span style={SUMMARY_HINT}>云 OCR / LLM 凭据（加密存储）</span>
        {status !== null && (
          <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 400, color: status.mineru_cloud.configured ? '#2e7d32' : '#888' }}>
            云 OCR {status.mineru_cloud.configured ? '已配置' : '未配置'}
          </span>
        )}
      </summary>
      <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
        配置云 OCR Key 后，导入文件优先走云解析、本地兜底；未配置则直接走本地通道（纯本地不外发）。
        <b>模式</b>对应 MinerU 官方 v4 的 <code>model_version</code>：<code>pipeline</code>（默认）／
        <code>vlm</code>（推荐，端到端视觉大模型）／<code>MinerU-HTML</code>（仅 HTML 源文件）。
        凭据只写入本机加密存储（Windows DPAPI，secrets.json），不回显、不入库。
      </p>
      {chan('mineru_cloud', '☁️ 云 OCR（MinerU 官方云）', cloudKey, setCloudKey, cloudUrl, setCloudUrl,
        cloudModeSlot, cloudModeDirty)}
      {chan('llm', '🤖 LLM 问答通道', llmKey, setLlmKey, llmUrl, setLlmUrl)}
      {err !== null && (
        <p role="alert" style={{ color: '#c0392b', fontSize: 12, margin: '6px 0 0' }}>{err}</p>
      )}
    </details>
  )
}

export default KsSettingsSection
