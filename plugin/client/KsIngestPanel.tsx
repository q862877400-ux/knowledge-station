/**
 * ks-dsh-plugin — client/KsIngestPanel.tsx
 *
 * 📥 入库预览面板（R27 Dry-Run 的人工确认界面；2026-11 由侧栏 tab 迁入设置
 * 栏目——用户拍板「全部进设置、类目全折叠」，收藏 tab 原样保留）。
 *
 * ## 它做什么
 *   1. 显示「待入库」目录（host 按需创建，浏览器无法浏览本机目录 → 必须给固定落点）；
 *   2. 列出目录里的 PDF（只列名/大小）；
 *   3. 「开始预览」→ 目录批量预览（决策 2：**先抽样几本**，默认 5），出 ✅/⚠️/❌ 三桶总账；
 *   4. 点某一行 → 拉该文件的 R27 完整报告（分级/裁决/前后 5 条样例/可疑清单/
 *      识别与版面指标/查重/标准号猜测）。
 *
 * 嵌入方式：由 KsSettingsSection 的「入库预览」<details> 类目承载——收起时
 * `visible=false` 挂载但零请求；展开即拉收件箱清单。
 *
 * ## 它**不**做什么（本轮边界，UI 上也要如实告诉用户）
 *   - **不落库**：预览只读，正式入库（确认后原子写入）是下一里程碑；
 *   - **默认不外发**：预览默认不调深度通道（该通道云优先）；扫描件因此只报"无文本层"，
 *     不会偷偷上传到云解析。**2026-09-17 D5/F1 起**：确需云深度解析时可由用户显式勾选
 *     「允许云深度解析」开启（`allow_deep`），此时报告会如实标注 `egress=deep_channel`
 *     ——**不禁止，但必须留痕、且必须由人显式选择**；
 *   - **不动文件**：不移动/复制/改名（判为 ❌ 的文件只标记候选，移动是正式批量入库的事）。
 *
 * 信任模型同 KsBookmarksTab：只跟同源 `/ks/*` 说话，token 由 host 持有。
 *
 * ## 第 5 步 5c：整页的取色/取间距方式换掉了（**不是**换语义）
 * 改前它整页 **0 个 `var(--dsw-*)` / `var(--ks-*)`、21 处硬编码色值**，按钮是 `border-radius:6px`
 * 的直角方框 —— 而宿主 `Button` 是 18px 胶囊 ⇒ 在设置栏目里它**看起来不像同一个产品**。
 * 现在：
 *   · 颜色全部走宿主活 token（`var(--dsw-alias-*)`，深浅色/换肤自动跟随）；语义色只用
 *     `--dsw-alias-state-{success,warn,error}-*`，**没有一个自己编的色值**；
 *   · 间距/圆角/字号全部走 `--ks-*`（第 5 步立的尺度 token；样式类在 `ksGuideStyles.ts`）；
 *   · 三个动作按钮换成宿主 `Button`（`primary`/`outline` 两档 + `size="sm"`）；
 *   · ⚠ **三色分级（可入库 / 需人工确认 / 不建议入库）的语义一个字没动** —— 换的只是它
 *     怎么取色（`VERDICT_META[].tone` 现在是类名，不是十六进制）。
 */

import * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@deepseek-ai/dsh-client-ui-primitives'

import { ensureKsStyles } from './ksGuideStyles'
import {
  abortIngestJob,
  fetchIngestBatch,
  fetchIngestInbox,
  fetchIngestInboxDefault,
  fetchIngestJob,
  fetchIngestPreview,
  startIngestJob,
  type KsIngestBatch,
  type KsIngestBatchRow,
  type KsIngestJobView,
  type KsIngestReport,
} from './api'

/** 面板 props：宿主是 KsSettingsSection 的折叠类目。visible 由 <details
 *  onToggle> 驱动——收起 = 挂载但零请求（懒加载门）。 */
export interface KsIngestPanelProps {
  visible: boolean
}

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'error'; message: string }

/**
 * 三色分级（**语义不许换**）：`tone` 决定走哪一族宿主状态色，
 * 真正的色值在 `ksGuideStyles.ts` 的 `.ks-ing-tone-*` 里（都是 `--dsw-alias-state-*`）。
 */
const VERDICT_META: Record<string, { icon: string; label: string; tone: string }> = {
  ok: { icon: '✅', label: '可入库', tone: 'ok' },
  warn: { icon: '⚠️', label: '需人工确认', tone: 'warn' },
  block: { icon: '❌', label: '不建议入库', tone: 'block' },
}

function verdictMeta(v: string): { icon: string; label: string; tone: string } {
  return VERDICT_META[v] ?? { icon: '❔', label: v || '未知', tone: 'muted' }
}

function fmtSize(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

/** 三桶总账（决策 2 的"总账"视图）。 */
function BucketBar(props: { batch: KsIngestBatch }): JSX.Element {
  const { batch } = props
  return (
    <div className="ks-ing-buckets">
      {(['ok', 'warn', 'block'] as const).map((k) => {
        const meta = verdictMeta(k)
        return (
          <span key={k} className={`ks-ing-chip ks-ing-tone-${meta.tone}`}>
            {meta.icon} {meta.label} <b>{batch.buckets[k] ?? 0}</b>
          </span>
        )
      })}
      <span className="ks-ing-note">
        共评估 {batch.evaluated} 本
        {batch.unprocessed > 0 ? `（未处理 ${batch.unprocessed} 本）` : ''}
        {batch.truncated ? '（候选超出上限，已截断）' : ''}
        {batch.conservation_ok ? '' : ' ⚠️ 计数不守恒，请报告'}
        {' · '}耗时 {(batch.elapsed_ms / 1000).toFixed(1)}s
      </span>
    </div>
  )
}

/** 单本 R27 报告详情。 */
function ReportDetail(props: { report: KsIngestReport }): JSX.Element {
  const { report: r } = props
  const meta = verdictMeta(r.verdict)
  const rec = r.recognition ?? ({} as KsIngestReport['recognition'])
  const lay = r.layout ?? ({} as KsIngestReport['layout'])
  const dist = r.knowledge_type_distribution ?? {}
  return (
    <div className="ks-ing-card">
      <div className="ks-ing-h">
        <span className={`ks-ing-tone-${meta.tone}`}>{meta.icon}</span> {meta.label} · {r.grade} 级 · {r.status === 'ok' ? '解析成功' : '解析失败'}
        <span className="ks-ing-h-sub">{r.one_line ?? ''}</span>
      </div>
      <div className="ks-ing-note">
        {r.verdict_reasons.map((x) => `[${x.code}] ${x.reason}`).join(' · ')}
      </div>
      <div className="ks-ing-note">
        页数 {r.pages} · 条款 {r.total_clauses}
        {r.clauses_dropped_tiny > 0 ? `（丢弃碎片 ${r.clauses_dropped_tiny}）` : ''}
        {' · '}识别置信度 {r.doc_confidence}
        {' · '}文本层 {rec.text_layer_state || '-'}
        {rec.skew_measured ? ` · 倾斜 ${rec.skew_deg}°` : ' · 倾斜未测'}
        {' · '}每页 {lay.chars_per_page} 字
        {typeof lay.tables_rebuilt === 'number' && lay.tables_rebuilt > 0
          ? ` · 表格 ${lay.tables_rebuilt}` : ''}
        {' · '}
        {/* 不要直接把枚举值印给用户看（"外发 deep_channel" 读起来像"本次真的发出去了"）：
            egress=deep_channel 是**保守高报**——只表示本次**允许**了云深度通道，
            该文档是否需要深度解析是另一回事。措辞要如实反映这一点。 */}
        {r.egress === 'none'
          ? <span>不外发（未启用云深度通道）</span>
          : <span className="ks-ing-warn">
              已允许云深度通道——扫描件会上传云端（本次是否真的上传取决于该文档有无文本层；
              精确记录见外发审计）
            </span>}
      </div>
      <div className="ks-ing-note">
        标准号猜测 {r.standard_no_guess?.value ?? '（未识别）'}
        {' · '}名称 {r.standard_name_guess?.value ?? '（未识别）'}
        {' · '}分型 {Object.entries(dist).map(([k, v]) => `${k}${v}`).join(' ') || '-'}
      </div>
      {r.duplicate?.kind && r.duplicate.kind !== 'none' ? (
        <div className="ks-ing-note ks-ing-warn">
          库内重复（{r.duplicate.kind}）：{r.duplicate.message ?? ''}
        </div>
      ) : null}
      {r.head_samples?.length ? (
        <div>
          <div className="ks-ing-sub">前 {r.head_samples.length} 条样例</div>
          {r.head_samples.map((s) => (
            <div key={`h${s.ordinal}`} className="ks-ing-note">
              <span className="ks-ing-mono">{s.number}</span>
              {' · '}{s.knowledge_type}（{s.type_confidence ?? '-'}）
              {s.modality ? ` · 模态 ${s.modality}` : ''}
              {' · '}置信 {s.ocr_confidence}
              {s.suspicious ? ' · 可疑' : ''}
              <div className="ks-ing-indent">{s.head}</div>
            </div>
          ))}
        </div>
      ) : null}
      {r.ocr_suspects?.length ? (
        <div>
          <div className="ks-ing-sub ks-ing-warn">
            可疑条款 {r.ocr_suspects.length}{r.ocr_suspects_truncated ? '（已截断）' : ''}
          </div>
          {r.ocr_suspects.slice(0, 8).map((s) => (
            <div key={`s${s.ordinal}`} className="ks-ing-note">
              <span className="ks-ing-mono">{s.number}</span>
              {' · '}{s.ocr_confidence} · {s.reasons.join('/')}
            </div>
          ))}
        </div>
      ) : null}
      {r.collected_signals && Object.keys(r.collected_signals).length > 0 ? (
        <div className="ks-ing-note">
          体检标签：{Object.entries(r.collected_signals)
            .filter(([k]) => k !== 'table_anomaly_clauses')
            .map(([k, v]) => `${k}×${String(v)}`).join(' · ') || '（无）'}
        </div>
      ) : null}
    </div>
  )
}

export function KsIngestPanel(props: KsIngestPanelProps): JSX.Element {
  ensureKsStyles()
  const { visible } = props
  const abortRef = useRef<AbortController | null>(null)
  const [dir, setDir] = useState<string>('')
  const [dirInput, setDirInput] = useState<string>('')
  const [files, setFiles] = useState<Array<{ file_name: string; size: number; path: string }>>([])
  const [degraded, setDegraded] = useState<string | null>(null)
  const [listState, setListState] = useState<LoadState>({ status: 'idle' })
  const [batchState, setBatchState] = useState<LoadState>({ status: 'idle' })
  const [batch, setBatch] = useState<KsIngestBatch | null>(null)
  const [sample, setSample] = useState<number>(5)
  const [detail, setDetail] = useState<KsIngestReport | null>(null)
  const [detailName, setDetailName] = useState<string>('')
  const [detailState, setDetailState] = useState<LoadState>({ status: 'idle' })
  // 异步全量预览任务（L239）：job_id + 轮询状态 + 三桶总账
  const [job, setJob] = useState<KsIngestJobView | null>(null)
  const [jobError, setJobError] = useState<string | null>(null)
  /** 是否显式允许云深度解析（= 引擎的 allow_deep）。**默认 false = 不外发**（D5/F1）。 */
  const [allowDeep, setAllowDeep] = useState<boolean>(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const newController = useCallback(() => {
    abortRef.current?.abort()
    const c = new AbortController()
    abortRef.current = c
    return c
  }, [])

  const loadInbox = useCallback(async (override?: string) => {
    const c = newController()
    setListState({ status: 'loading' })
    try {
      const target = override ?? dir ?? ''
      const inbox = target
        ? await fetchIngestInbox(target, c.signal)
        : await (async () => {
          const d = await fetchIngestInboxDefault(c.signal)
          setDirInput(d)
          return await fetchIngestInbox(d, c.signal)
        })()
      setDir(inbox.dir)
      setDirInput(inbox.dir)
      setFiles(inbox.files ?? [])
      setDegraded(inbox.degraded ?? null)
      setListState({ status: 'ready' })
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') return
      setListState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [dir, newController])

  // 首次可见时加载（tab 未挂载前不发请求）
  useEffect(() => {
    if (!visible) return
    if (listState.status === 'idle') void loadInbox()
  }, [visible, listState.status, loadInbox])

  useEffect(() => () => abortRef.current?.abort(), [])

  const startBatch = useCallback(async () => {
    const c = newController()
    setBatchState({ status: 'loading' })
    setDetail(null)
    setDetailState({ status: 'idle' })
    try {
      const out = await fetchIngestBatch({ dir, sample, allowDeep }, c.signal)
      setBatch(out)
      setBatchState({ status: 'ready' })
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') return
      setBatchState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [dir, sample, allowDeep, newController])

  const openDetail = useCallback(async (row: KsIngestBatchRow) => {
    const c = newController()
    setDetailName(row.file_name)
    setDetail(null)
    setDetailState({ status: 'loading' })
    try {
      const rep = await fetchIngestPreview(row.path, { allowDeep, signal: c.signal })
      setDetail(rep)
      setDetailState({ status: 'ready' })
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') return
      setDetailState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [allowDeep, newController])

  // ---- 异步全量预览（L239）：启动 → 轮询 → 中断 ----
  const stopJobPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const pollJob = useCallback(async (jobId: string) => {
    try {
      const v = await fetchIngestJob(jobId)
      setJob(v)
      setJobError(null)
      if (v.status === 'done' || v.status === 'aborted' || v.status === 'failed') {
        stopJobPolling()
      }
    } catch (e) {
      // 轮询失败不立刻死：连续错误时如实显示（引擎可能重启中）
      setJobError(e instanceof Error ? e.message : String(e))
    }
  }, [stopJobPolling])

  const startFullJob = useCallback(async () => {
    setJobError(null)
    setJob(null)
    try {
      const v = await startIngestJob({ dir, allowDeep })
      setJob(v)
      stopJobPolling()
      pollRef.current = setInterval(() => void pollJob(v.job_id), 1500)
    } catch (e) {
      setJobError(e instanceof Error ? e.message : String(e))
    }
  }, [dir, allowDeep, pollJob, stopJobPolling])

  const abortFullJob = useCallback(async () => {
    if (!job) return
    try {
      await abortIngestJob(job.job_id)
      // 中断请求已发；状态由下一轮轮询刷新为 aborted
    } catch (e) {
      setJobError(e instanceof Error ? e.message : String(e))
    }
  }, [job])

  useEffect(() => () => stopJobPolling(), [stopJobPolling])

  const busy = listState.status === 'loading' || batchState.status === 'loading'
    || detailState.status === 'loading'

  return (
    <div className="ks-ing">
      <div className="ks-ing-note">
        只读预览：<b>不写库、不移动文件、默认不外发</b>。
        扫描件默认只报"无文本层"，<b>不会</b>偷偷上传到云解析；确需云深度解析时，
        勾选下面的<b>「允许云深度解析」</b>显式开启（会外发，报告里会如实标注 egress）。
        正式入库（确认后原子写入）是下一里程碑，此页不提供。
      </div>

      {/* 2026-09-17 独立复核 F1：原先桥这一层把 allow_deep 直接掐掉，
          引擎解开的云深度通道在界面上**点不到**。现补上开关，**默认关闭**，
          并把"会外发"写在标签里——不给开关和偷偷给开关都不对，要的是明说的开关。 */}
      <label className="ks-ing-note ks-ing-toggle">
        <input
          type="checkbox"
          checked={allowDeep}
          onChange={(e) => setAllowDeep(e.target.checked)}
          aria-label="允许云深度解析"
        />
        <span>
          允许云深度解析（<b>会把扫描件上传到云端</b>；默认关闭）。
          {allowDeep ? '本次预览将如实标注 egress=deep_channel。' : '本次预览不外发（egress=none）。'}
        </span>
      </label>

      <div className="ks-ing-row">
        <span className="ks-ing-note">待入库目录：</span>
        <input
          className="ks-ing-mono ks-ing-dir"
          value={dirInput}
          onChange={(e) => setDirInput(e.target.value)}
          spellCheck={false}
          aria-label="待入库目录"
        />
        <Button variant="outline" size="sm" disabled={busy} onClick={() => void loadInbox(dirInput)}>
          刷新列表
        </Button>
      </div>

      <div className="ks-ing-note">
        该目录下 PDF：<b>{files.length}</b> 个
        {degraded === 'engine_unavailable' ? '（引擎未启动：以下为 host 直接列目录的结果）' : ''}
      </div>
      {files.length === 0 ? (
        <div className="ks-ing-note">
          把要入库的 PDF 放进上面的目录，然后点「刷新列表」。
        </div>
      ) : (
        <div className="ks-ing-files">
          {files.slice(0, 12).map((f) => (
            <div key={f.path} className="ks-ing-mono">
              {f.file_name} <span className="ks-ing-size">{fmtSize(f.size)}</span>
            </div>
          ))}
          {files.length > 12 ? <div className="ks-ing-note">…还有 {files.length - 12} 个</div> : null}
        </div>
      )}

      <div className="ks-ing-row">
        <span className="ks-ing-note">抽样（本）</span>
        <input
          className="ks-ing-num"
          type="number"
          min={0}
          value={sample}
          onChange={(e) => setSample(Math.max(0, Number(e.target.value) || 0))}
          aria-label="抽样本数"
        />
        <span className="ks-ing-note">0 = 不抽样（全部，上限 200）</span>
        <Button
          variant="primary"
          size="sm"
          disabled={busy || files.length === 0}
          onClick={() => void startBatch()}
        >
          开始预览
        </Button>
        {batchState.status === 'loading' ? (
          <span className="ks-ing-note">预览中…（解析 + 体检，扫描件可能要几秒）</span>
        ) : null}
      </div>

      {batchState.status === 'error' ? (
        <div className="ks-ing-note ks-ing-err">
          预览失败：{batchState.message}
        </div>
      ) : null}

      {batch ? (
        <>
          <BucketBar batch={batch} />
          <div className="ks-ing-note">
            点文件名看该本的完整体检报告（分级/裁决理由/样例/可疑条款/查重）。
          </div>
          {batch.files.map((row, i) => {
            const meta = verdictMeta(row.verdict)
            return (
              <div key={row.path} className={i === 0 ? 'ks-ing-line ks-ing-line-first' : 'ks-ing-line'}>
                <span className={`ks-ing-icon ks-ing-tone-${meta.tone}`}>{meta.icon}</span>
                <div className="ks-ing-grow">
                  <button
                    type="button"
                    className="ks-ing-link"
                    onClick={() => void openDetail(row)}
                  >
                    {row.file_name}
                  </button>
                  <div className="ks-ing-note">
                    {row.grade} 级 · {row.pages} 页 · {row.total_clauses} 条
                    {' · '}{row.reasons.join('/') || 'OK'}
                    {row.error ? ` · ${row.error}` : ''}
                  </div>
                </div>
              </div>
            )
          })}
        </>
      ) : null}

      {/* ---------------- 异步全量预览（万级，L239） ---------------- */}
      <div className="ks-ing-async">
        <div className="ks-ing-sub">全量预览（异步，万级可用）</div>
        <div className="ks-ing-note">
          上面的同步预览单请求上限 200 本；这里走引擎后台任务，几万本也能跑——
          关掉浏览器 host 也会继续推进，回来时自动恢复进度显示。
        </div>
        <div className="ks-ing-row">
          <Button
            variant="outline"
            size="sm"
            disabled={job !== null && (job.status === 'running' || job.status === 'pending')}
            onClick={() => void startFullJob()}
          >
            对整个目录发起全量预览
          </Button>
          {job && (job.status === 'running' || job.status === 'pending') ? (
            <Button variant="ghost" size="sm" onClick={() => void abortFullJob()}>
              中断
            </Button>
          ) : null}
        </div>
        {jobError ? (
          <div className="ks-ing-note ks-ing-err">任务失败：{jobError}</div>
        ) : null}
        {job ? (
          <div>
            <div className="ks-ing-note">
              状态：<b>{job.status}</b>
              {' · '}已体检 {job.done}/{job.total}
              {job.stale === true ? ' · （引擎不可达：显示 host 镜像快照）' : ''}
              {job.error ? ` · ${job.error}` : ''}
            </div>
            {job.total > 0 ? (
              <div
                className="ks-ing-progress"
                role="progressbar"
                aria-label="全量预览进度"
              >
                <div
                  className="ks-ing-progress-fill"
                  style={{ width: `${Math.min(100, Math.round((job.done / job.total) * 100))}%` }}
                />
              </div>
            ) : null}
            {(job.status === 'done' || job.status === 'aborted' || job.status === 'failed') ? (
              <div className="ks-ing-note">
                三桶总账：✅ 可入库 <b>{job.buckets?.ok ?? 0}</b>
                {' · '}⚠️ 需处理 <b>{job.buckets?.warn ?? 0}</b>
                {' · '}❌ 阻断 <b>{job.buckets?.block ?? 0}</b>
                {job.status === 'aborted' ? '（已中断：以上为部分结果）' : ''}
              </div>
            ) : null}
            {job.rows && job.rows.length > 0 ? (
              <div>
                {job.rows.slice(0, 10).map((row) => {
                  const meta = verdictMeta(row.verdict)
                  return (
                    <div key={row.path} className="ks-ing-note">
                      <span className={`ks-ing-tone-${meta.tone}`}>{meta.icon}</span>
                      {' '}{row.file_name} — {row.one_line || `${row.grade} 级 · ${row.pages} 页`}
                    </div>
                  )
                })}
                {job.rows_count !== undefined && job.rows_count > 10
                  ? <div className="ks-ing-note">…共 {job.rows_count} 行（前 10 行预览）</div>
                  : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {detailState.status === 'loading' ? (
        <div className="ks-ing-note">加载 {detailName} 的报告…</div>
      ) : null}
      {detailState.status === 'error' ? (
        <div className="ks-ing-note ks-ing-err">
          {detailName} 报告失败：{detailState.message}
        </div>
      ) : null}
      {detail ? <ReportDetail report={detail} /> : null}
    </div>
  )
}
