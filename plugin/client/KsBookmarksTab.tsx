/**
 * ks-dsh-plugin — client/KsBookmarksTab.tsx
 *
 * 增强③-A：🔖 收藏侧栏 tab（tab id `ks:bookmarks`，single）。列出引擎收藏的条款
 * （user_bookmark LEFT JOIN clause_revision/doc_meta），每条可：
 *   1) 点击 → 用 doc_id/page_start/clause_revision_id 拼证据锚点 URL（复用
 *      ksEvidence.ts 的 URL 契约，含 doc/page/rev），经 better-sidebar 打开并
 *      强制覆写单例 ks:pdf tab 的 path（`openTab` + `updateTab` 带单调 ksClick
 *      nonce），复用现有 [tab.path, tab.meta] effect 跳页；doc/page 缺失的条目
 *      置灰不可点。
 *   2) 「删除」→ 跨源 DELETE 引擎 /api/v1/bookmarks/{bookmark_id}（Bearer），
 *      成功后从列表移除；失败显示错误不崩。
 *
 * 数据与信任模型完全照抄 KsEvidenceTab / api.ts：
 *   - fetchSession() 同源 /ks/session 拿 port + token；
 *   - token 只经 fetchSession 拿、跨源只发给 127.0.0.1 引擎（同 fetchPdf）；
 *   - 401 → 重取 session 一次（EngineAuthError 判别）；非 200 → 显示错误 + 重试。
 * 不新增引擎端点；引擎已具备 GET /api/v1/bookmarks 与 DELETE /api/v1/bookmarks/{id}。
 */

import * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

import type { TabComponentProps } from 'dsh-better-sidebar/client/service'
import {
  EngineAuthError,
  deleteBookmark,
  fetchBookmarks,
  fetchSession,
  type KsBookmark,
} from './api'
import {
  KS_EVIDENCE_TAB_ID,
  evidenceUrlOf,
  nextEvidenceClick,
  type KsEvidence,
} from './ksEvidence'

/** Tab id this component is registered under (see client/entry.ts). */
export const KS_BOOKMARKS_TAB_ID = 'ks:bookmarks'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'error'; message: string }

export function KsBookmarksTab(props: TabComponentProps): JSX.Element {
  const { ctx, visible } = props

  const abortRef = useRef<AbortController | null>(null)
  const [bookmarks, setBookmarks] = useState<KsBookmark[]>([])
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [delError, setDelError] = useState<string | null>(null)

  const loadBookmarks = useCallback(async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoad({ status: 'loading' })
    setDelError(null)
    try {
      let session = await fetchSession(controller.signal)
      let list: KsBookmark[]
      try {
        list = await fetchBookmarks(session.engine.port, session.token, controller.signal)
      } catch (error) {
        // 401 → 会话可能已轮换：重取一次再试（镜像 fetchPdf/host bbox 语义）。
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          list = await fetchBookmarks(session.engine.port, session.token, controller.signal)
        } else {
          throw error
        }
      }
      if (controller.signal.aborted) return
      setBookmarks(list)
      setLoad({ status: 'ready' })
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
    }
  }, [])

  // 首次载入 + 每次 tab 激活（visible 变 true）都刷新（同 KsEvidenceTab 的
  // "每次载入重取 session" 前提：引擎 port/token 每次启动轮换）。
  useEffect(() => {
    if (visible) void loadBookmarks()
  }, [visible, loadBookmarks])

  const retry = useCallback(() => {
    void loadBookmarks()
  }, [loadBookmarks])

  /** 删除一条收藏（一次一个），成功后从本地列表移除。 */
  const deleteOne = useCallback(
    async (b: KsBookmark) => {
      if (deletingId !== null) return
      setDeletingId(b.bookmark_id)
      setDelError(null)
      const controller = new AbortController()
      try {
        let session = await fetchSession(controller.signal)
        try {
          await deleteBookmark(session.engine.port, b.bookmark_id, session.token, controller.signal)
        } catch (error) {
          if (error instanceof EngineAuthError) {
            session = await fetchSession(controller.signal)
            await deleteBookmark(session.engine.port, b.bookmark_id, session.token, controller.signal)
          } else {
            throw error
          }
        }
        setBookmarks((prev) => prev.filter((x) => x.bookmark_id !== b.bookmark_id))
      } catch (error) {
        setDelError(error instanceof Error ? error.message : String(error))
      } finally {
        setDeletingId(null)
      }
    },
    [deletingId],
  )

  /** 点击条目 → 拼证据锚点，复用 ks:pdf 单例跳页。 */
  const openBookmark = useCallback(
    (b: KsBookmark) => {
      const doc = typeof b.doc_id === 'string' && b.doc_id.length > 0 ? b.doc_id : null
      const page = typeof b.page_start === 'number' && b.page_start >= 1 ? Math.floor(b.page_start) : null
      if (doc === null || page === null) return // 置灰条目不会触发
      const ev: KsEvidence = { doc, page, rev: b.clause_revision_id ?? undefined }
      const url = evidenceUrlOf(ev)
      if (url === null) return
      const title = bookmarkTitle(b)
      try {
        // 同 entry.ts 证据点击拦截：open（建/聚焦）+ updateTab 强制覆写单例 path，
        // meta 带单调 nonce 保证同值 path 也触发 [tab.path, tab.meta] effect 重载。
        ctx.betterSidebar.openTab({ type: KS_EVIDENCE_TAB_ID, url, title })
        ctx.betterSidebar.updateTab?.(KS_EVIDENCE_TAB_ID, {
          path: url,
          title,
          meta: { ksClick: nextEvidenceClick() },
        })
      } catch (error) {
        setDelError(`跳转失败：${error instanceof Error ? error.message : String(error)}`)
      }
    },
    [ctx],
  )

  const ready = load.status === 'ready'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, fontSize: 12 }}>
      {/* header：标题 + 计数 + 刷新 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>收藏</span>
        <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>
          {ready ? `${bookmarks.length} 条` : ''}
        </span>
        <span style={{ marginLeft: 'auto' }}>
          <button type="button" onClick={retry} disabled={load.status === 'loading'} style={$btnPrimary}>
            刷新
          </button>
        </span>
      </div>

      {delError !== null && (
        <div style={{ padding: '6px 10px', color: 'var(--dsw-alias-danger, #c62828)', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', background: 'var(--dsw-alias-danger-bg, #fff0f0)', fontSize: 11, wordBreak: 'break-word' }}>
          {delError}
        </div>
      )}

      {/* body */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 10 }}>
        {load.status === 'loading' && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>载入收藏…（首次可能启动引擎，需要数秒）</div>
          </div>
        )}
        {load.status === 'error' && (
          <div style={{ ...$center, flexDirection: 'column', gap: 10 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', maxWidth: 480, textAlign: 'center', wordBreak: 'break-word' }}>
              {load.message}
            </div>
            <button type="button" onClick={retry} style={$btnPrimary}>重试</button>
          </div>
        )}
        {ready && bookmarks.length === 0 && (
          <div style={{ ...$center, flexDirection: 'column', gap: 6 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>暂无收藏</div>
            <div style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11, maxWidth: 380, textAlign: 'center', lineHeight: 1.5 }}>
              打开证据 PDF 后点右上角「🔖 收藏」，或让模型用 ks_answer 取证后收藏
              【依据】链接——收藏的条款会出现在这里，点击一键跳回原 PDF 页。
            </div>
          </div>
        )}
        {ready && bookmarks.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {bookmarks.map((b) => {
              const clickable = isClickable(b)
              const deleting = deletingId === b.bookmark_id
              return (
                <li key={b.bookmark_id} style={{ ...$item, opacity: clickable ? 1 : 0.62 }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <button
                      type="button"
                      disabled={!clickable || deleting}
                      onClick={() => clickable && openBookmark(b)}
                      style={{ ...$itemMain, cursor: clickable ? 'pointer' : 'not-allowed', ...(clickable ? {} : { color: 'var(--dsw-alias-label-tertiary, #999)' }) }}
                      title={clickable ? '打开 PDF 证据' : '缺少文档/页码，不可跳转'}
                    >
                      <div style={{ fontWeight: 600 }}>{titleLine(b)}</div>
                      {b.title !== null && b.title.length > 0 && (
                        <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', marginTop: 2 }}>{b.title}</div>
                      )}
                      {summarize(b) !== '' && (
                        <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', marginTop: 2, lineHeight: 1.4 }}>{summarize(b)}</div>
                      )}
                      <div style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 10, marginTop: 3 }}>
                        {formatTime(b.created_at)}
                      </div>
                    </button>
                    <button
                      type="button"
                      disabled={deleting}
                      onClick={() => void deleteOne(b)}
                      style={$btnDelete}
                      title="删除收藏"
                    >
                      {deleting ? '…' : '删除'}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

// ---- helpers (pure) --------------------------------------------------

function isClickable(b: KsBookmark): boolean {
  const doc = typeof b.doc_id === 'string' && b.doc_id.length > 0
  const page = typeof b.page_start === 'number' && b.page_start >= 1
  return doc && page
}

/** 主标题：标准号 · 条款号。 */
function titleLine(b: KsBookmark): string {
  return [b.standard_no, b.clause_number].filter(Boolean).join(' · ') || '（未命名条款）'
}

/** 跳转后 ks:pdf tab 的标题（doc + 页码）。 */
function bookmarkTitle(b: KsBookmark): string {
  const label = [b.standard_no, b.clause_number].filter(Boolean).join(' ')
  const base = `PDF 查看器${label ? ` · ${label}` : ''}`
  return b.page_start !== null && b.page_start >= 1 ? `${base} · 第${b.page_start}页` : base
}

/** 内容摘要（前端截断 ≤120 字）。 */
function summarize(b: KsBookmark): string {
  const t = b.content_text
  if (typeof t !== 'string' || t.length === 0) return ''
  const trimmed = t.trim()
  return trimmed.length > 120 ? `${trimmed.slice(0, 120)}…` : trimmed
}

function formatTime(iso: string | null): string {
  if (typeof iso !== 'string' || iso.length === 0) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  try {
    return d.toLocaleString()
  } catch {
    return iso
  }
}

// ---- small inline styles (mirrors KsEvidenceTab) ------

const $center: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  minHeight: 160,
}

const $btnPrimary: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '4px 14px',
  cursor: 'pointer',
}

const $item: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 6,
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  padding: 8,
}

const $itemMain: React.CSSProperties = {
  flex: 1,
  textAlign: 'left',
  border: 'none',
  background: 'transparent',
  padding: 0,
  font: 'inherit',
  color: 'var(--dsw-alias-label-primary, #111)',
}

const $btnDelete: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-danger, #c62828)',
  borderRadius: 4,
  padding: '2px 8px',
  cursor: 'pointer',
  fontSize: 11,
  whiteSpace: 'nowrap',
  flexShrink: 0,
}
