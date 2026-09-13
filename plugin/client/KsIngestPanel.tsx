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
 *   - **不外发**：预览禁用深度通道（该通道云优先）；扫描件因此只能报"无文本层"，
 *     不会偷偷上传到云解析；
 *   - **不动文件**：不移动/复制/改名（判为 ❌ 的文件只标记候选，移动是正式批量入库的事）。
 *
 * 信任模型同 KsBookmarksTab：只跟同源 `/ks/*` 说话，token 由 host 持有。
 */

import * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

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

const VERDICT_META: Record<string, { icon: string; label: string; color: string }> = {
  ok: { icon: '✅', label: '可入库', color: '#1a7f37' },
  warn: { icon: '⚠️', label: '需人工确认', color: '#9a6700' },
  block: { icon: '❌', label: '不建议入库', color: '#b42318' },
}

function verdictMeta(v: string): { icon: string; label: string; color: string } {
  return VERDICT_META[v] ?? { icon: '❔', label: v || '未知', color: '#57606a' }
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

const chipStyle: React.CSSProperties = {
  display: 'inline-block', padding: '1px 8px', borderRadius: 999,
  border: '1px solid #d0d7de', fontSize: 12, marginRight: 6,
}

const monoStyle: React.CSSProperties = {
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  fontSize: 12, wordBreak: 'break-all',
}

const noteStyle: React.CSSProperties = {
  fontSize: 12, color: '#57606a', lineHeight: 1.6,
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
    <div style={{ margin: '8px 0' }}>
      {(['ok', 'warn', 'block'] as const).map((k) => {
        const meta = verdictMeta(k)
        return (
          <span key={k} style={{ ...chipStyle, borderColor: meta.color }}>
            {meta.icon} {meta.label} <b>{batch.buckets[k] ?? 0}</b>
          </span>
        )
      })}
      <span style={{ ...noteStyle, marginLeft: 4 }}>
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
    <div style={{ border: '1px solid #d0d7de', borderRadius: 6, padding: 10, marginTop: 8 }}>
      <div style={{ fontSize: 13, fontWeight: 600 }}>
        {meta.icon} {meta.label} · {r.grade} 级 · {r.status === 'ok' ? '解析成功' : '解析失败'}
        <span style={{ ...noteStyle, fontWeight: 400, marginLeft: 8 }}>{r.one_line ?? ''}</span>
      </div>
      <div style={{ ...noteStyle, marginTop: 6 }}>
        {r.verdict_reasons.map((x) => `[${x.code}] ${x.reason}`).join(' · ')}
      </div>
      <div style={{ ...noteStyle, marginTop: 6 }}>
        页数 {r.pages} · 条款 {r.total_clauses}
        {r.clauses_dropped_tiny > 0 ? `（丢弃碎片 ${r.clauses_dropped_tiny}）` : ''}
        {' · '}识别置信度 {r.doc_confidence}
        {' · '}文本层 {rec.text_layer_state || '-'}
        {rec.skew_measured ? ` · 倾斜 ${rec.skew_deg}°` : ' · 倾斜未测'}
        {' · '}每页 {lay.chars_per_page} 字
        {typeof lay.tables_rebuilt === 'number' && lay.tables_rebuilt > 0
          ? ` · 表格 ${lay.tables_rebuilt}` : ''}
        {' · '}外发 {r.egress}
      </div>
      <div style={{ ...noteStyle, marginTop: 6 }}>
        标准号猜测 {r.standard_no_guess?.value ?? '（未识别）'}
        {' · '}名称 {r.standard_name_guess?.value ?? '（未识别）'}
        {' · '}分型 {Object.entries(dist).map(([k, v]) => `${k}${v}`).join(' ') || '-'}
      </div>
      {r.duplicate?.kind && r.duplicate.kind !== 'none' ? (
        <div style={{ ...noteStyle, marginTop: 6, color: '#9a6700' }}>
          库内重复（{r.duplicate.kind}）：{r.duplicate.message ?? ''}
        </div>
      ) : null}
      {r.head_samples?.length ? (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>前 {r.head_samples.length} 条样例</div>
          {r.head_samples.map((s) => (
            <div key={`h${s.ordinal}`} style={{ ...noteStyle, marginTop: 2 }}>
              <span style={monoStyle}>{s.number}</span>
              {' · '}{s.knowledge_type}（{s.type_confidence ?? '-'}）
              {s.modality ? ` · 模态 ${s.modality}` : ''}
              {' · '}置信 {s.ocr_confidence}
              {s.suspicious ? ' · 可疑' : ''}
              <div style={{ paddingLeft: 12 }}>{s.head}</div>
            </div>
          ))}
        </div>
      ) : null}
      {r.ocr_suspects?.length ? (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#9a6700' }}>
            可疑条款 {r.ocr_suspects.length}{r.ocr_suspects_truncated ? '（已截断）' : ''}
          </div>
          {r.ocr_suspects.slice(0, 8).map((s) => (
            <div key={`s${s.ordinal}`} style={{ ...noteStyle, marginTop: 2 }}>
              <span style={monoStyle}>{s.number}</span>
              {' · '}{s.ocr_confidence} · {s.reasons.join('/')}
            </div>
          ))}
        </div>
      ) : null}
      {r.collected_signals && Object.keys(r.collected_signals).length > 0 ? (
        <div style={{ ...noteStyle, marginTop: 8 }}>
          体检标签：{Object.entries(r.collected_signals)
            .filter(([k]) => k !== 'table_anomaly_clauses')
            .map(([k, v]) => `${k}×${String(v)}`).join(' · ') || '（无）'}
        </div>
      ) : null}
    </div>
  )
}

export function KsIngestPanel(props: KsIngestPanelProps): JSX.Element {
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
      const out = await fetchIngestBatch({ dir, sample }, c.signal)
      setBatch(out)
      setBatchState({ status: 'ready' })
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') return
      setBatchState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [dir, sample, newController])

  const openDetail = useCallback(async (row: KsIngestBatchRow) => {
    const c = newController()
    setDetailName(row.file_name)
    setDetail(null)
    setDetailState({ status: 'loading' })
    try {
      const rep = await fetchIngestPreview(row.path, { signal: c.signal })
      setDetail(rep)
      setDetailState({ status: 'ready' })
    } catch (e) {
      if ((e as { name?: string }).name === 'AbortError') return
      setDetailState({ status: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [newController])

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
      const v = await startIngestJob({ dir })
      setJob(v)
      stopJobPolling()
      pollRef.current = setInterval(() => void pollJob(v.job_id), 1500)
    } catch (e) {
      setJobError(e instanceof Error ? e.message : String(e))
    }
  }, [dir, pollJob, stopJobPolling])

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
    <div style={{ padding: '4px 0 2px', fontSize: 13 }}>
      <div style={noteStyle}>
        只读预览：<b>不写库、不移动文件、不外发</b>（深度通道已禁用）。
        扫描件会如实显示"无文本层"而不是偷偷上传到云解析。
        正式入库（确认后原子写入）是下一里程碑，此页不提供。
      </div>

      <div style={{ marginTop: 10 }}>
        <span style={noteStyle}>待入库目录：</span>
        <input
          value={dirInput}
          onChange={(e) => setDirInput(e.target.value)}
          spellCheck={false}
          style={{ ...monoStyle, width: '62%', padding: '2px 6px', marginRight: 6 }}
          aria-label="待入库目录"
        />
        <button
          type="button"
          style={btnStyle(busy)}
          disabled={busy}
          onClick={() => void loadInbox(dirInput)}
        >
          刷新列表
        </button>
      </div>

      <div style={{ ...noteStyle, marginTop: 8 }}>
        该目录下 PDF：<b>{files.length}</b> 个
        {degraded === 'engine_unavailable' ? '（引擎未启动：以下为 host 直接列目录的结果）' : ''}
      </div>
      {files.length === 0 ? (
        <div style={{ ...noteStyle, marginTop: 4 }}>
          把要入库的 PDF 放进上面的目录，然后点「刷新列表」。
        </div>
      ) : (
        <div style={{ ...noteStyle, marginTop: 4 }}>
          {files.slice(0, 12).map((f) => (
            <div key={f.path} style={{ ...monoStyle, marginTop: 2 }}>
              {f.file_name} <span style={{ color: '#57606a' }}>{fmtSize(f.size)}</span>
            </div>
          ))}
          {files.length > 12 ? <div>…还有 {files.length - 12} 个</div> : null}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <span style={noteStyle}>抽样（本）</span>
        <input
          type="number"
          min={0}
          value={sample}
          onChange={(e) => setSample(Math.max(0, Number(e.target.value) || 0))}
          style={{ width: 64, padding: '2px 6px', margin: '0 6px' }}
          aria-label="抽样本数"
        />
        <span style={{ ...noteStyle, marginRight: 8 }}>0 = 不抽样（全部，上限 200）</span>
        <button
          type="button"
          style={btnStyle(busy || files.length === 0)}
          disabled={busy || files.length === 0}
          onClick={() => void startBatch()}
        >
          开始预览
        </button>
        {batchState.status === 'loading' ? (
          <span style={{ ...noteStyle, marginLeft: 8 }}>预览中…（解析 + 体检，扫描件可能要几秒）</span>
        ) : null}
      </div>

      {batchState.status === 'error' ? (
        <div style={{ ...noteStyle, marginTop: 8, color: '#b42318' }}>
          预览失败：{batchState.message}
        </div>
      ) : null}

      {batch ? (
        <>
          <BucketBar batch={batch} />
          <div style={{ ...noteStyle, marginBottom: 4 }}>
            点文件名看该本的完整体检报告（分级/裁决理由/样例/可疑条款/查重）。
          </div>
          {batch.files.map((row) => {
            const meta = verdictMeta(row.verdict)
            return (
              <div
                key={row.path}
                style={{ borderTop: '1px solid #eaeef2', padding: '6px 0', display: 'flex', gap: 8 }}
              >
                <span style={{ color: meta.color, minWidth: 18 }}>{meta.icon}</span>
                <div style={{ flex: 1 }}>
                  <button
                    type="button"
                    onClick={() => void openDetail(row)}
                    style={{
                      border: 'none', background: 'none', padding: 0, cursor: 'pointer',
                      fontSize: 13, color: '#0969da', textAlign: 'left',
                    }}
                  >
                    {row.file_name}
                  </button>
                  <div style={noteStyle}>
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
      <div style={{ marginTop: 14, borderTop: '1px dashed #d0d7de', paddingTop: 10 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>全量预览（异步，万级可用）</div>
        <div style={noteStyle}>
          上面的同步预览单请求上限 200 本；这里走引擎后台任务，几万本也能跑——
          关掉浏览器 host 也会继续推进，回来时自动恢复进度显示。
        </div>
        <div style={{ marginTop: 8 }}>
          <button
            type="button"
            style={btnStyle(job !== null && (job.status === 'running' || job.status === 'pending'))}
            disabled={job !== null && (job.status === 'running' || job.status === 'pending')}
            onClick={() => void startFullJob()}
          >
            对整个目录发起全量预览
          </button>
          {job && (job.status === 'running' || job.status === 'pending') ? (
            <button
              type="button"
              style={{ ...btnStyle(false), marginLeft: 8 }}
              onClick={() => void abortFullJob()}
            >
              中断
            </button>
          ) : null}
        </div>
        {jobError ? (
          <div style={{ ...noteStyle, marginTop: 6, color: '#b42318' }}>任务失败：{jobError}</div>
        ) : null}
        {job ? (
          <div style={{ marginTop: 8 }}>
            <div style={noteStyle}>
              状态：<b>{job.status}</b>
              {' · '}已体检 {job.done}/{job.total}
              {job.stale === true ? ' · （引擎不可达：显示 host 镜像快照）' : ''}
              {job.error ? ` · ${job.error}` : ''}
            </div>
            {job.total > 0 ? (
              <div
                role="progressbar"
                aria-label="全量预览进度"
                style={{
                  marginTop: 6, height: 8, borderRadius: 4,
                  background: '#eaeef2', overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(100, Math.round((job.done / job.total) * 100))}%`,
                    height: '100%', background: '#0969da',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
            ) : null}
            {(job.status === 'done' || job.status === 'aborted' || job.status === 'failed') ? (
              <div style={{ ...noteStyle, marginTop: 6 }}>
                三桶总账：✅ 可入库 <b>{job.buckets?.ok ?? 0}</b>
                {' · '}⚠️ 需处理 <b>{job.buckets?.warn ?? 0}</b>
                {' · '}❌ 阻断 <b>{job.buckets?.block ?? 0}</b>
                {job.status === 'aborted' ? '（已中断：以上为部分结果）' : ''}
              </div>
            ) : null}
            {job.rows && job.rows.length > 0 ? (
              <div style={{ marginTop: 6 }}>
                {job.rows.slice(0, 10).map((row) => {
                  const meta = verdictMeta(row.verdict)
                  return (
                    <div key={row.path} style={{ ...noteStyle, marginTop: 2 }}>
                      <span style={{ color: meta.color }}>{meta.icon}</span>
                      {' '}{row.file_name} — {row.one_line || `${row.grade} 级 · ${row.pages} 页`}
                    </div>
                  )
                })}
                {job.rows_count !== undefined && job.rows_count > 10
                  ? <div style={noteStyle}>…共 {job.rows_count} 行（前 10 行预览）</div>
                  : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {detailState.status === 'loading' ? (
        <div style={{ ...noteStyle, marginTop: 8 }}>加载 {detailName} 的报告…</div>
      ) : null}
      {detailState.status === 'error' ? (
        <div style={{ ...noteStyle, marginTop: 8, color: '#b42318' }}>
          {detailName} 报告失败：{detailState.message}
        </div>
      ) : null}
      {detail ? <ReportDetail report={detail} /> : null}
    </div>
  )
}
