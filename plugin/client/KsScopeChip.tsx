/**
 * ks-dsh-plugin — client/KsScopeChip.tsx (2026-10 收藏目录)
 *
 * 「在本收藏夹内提问」的前缀标记胶囊：注册在 conversation.input.dock
 * （输入卡片上方的全宽行），夹内提问激活时显示
 *   「🔖 收藏夹名 · 仅在本收藏夹内提问 ✕」
 * 点 ✕ → PUT /ks/chat-mode {folderId: null} → 恢复全库检索。
 * 未激活（folderId null）时渲染 null——不占行。
 *
 * 状态同步：挂载时 + 每次 sessionId 变化拉 GET /ks/chat-mode；✕ 关闭后用
 * PUT 返回的 mode 即时更新。不在 host 侧订阅推送（chatmode 是拉模型，
 * 每轮 PUT 后这里都会重拉/更新——收起 tab 或关闭胶囊都会走到这份数据）。
 *
 * props：slot 系统给 session-scope 组件的标准 kit 含 sessionId
 * （SessionStandardProps 运行时合并进来的 framework-supplied 成员）。
 */

import * as React from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchChatMode, patchChatMode } from './api'

export interface KsScopeChipProps {
  /** 当前会话 id（slot 框架注入；undefined 时胶囊隐藏）。 */
  sessionId?: string
}

/** dock 组件主体（不激活 = null）。 */
export function KsScopeChip(props: KsScopeChipProps): JSX.Element | null {
  const { sessionId } = props
  const [folderName, setFolderName] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // 拉当前开关：有 session 就读一次（+ sessionId 变化重读）。
  useEffect(() => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    if (sessionId === undefined || sessionId.length === 0) {
      setFolderName(null)
      return
    }
    void (async () => {
      try {
        const mode = await fetchChatMode(sessionId, controller.signal)
        if (controller.signal.aborted) return
        setFolderName(mode.folderId !== null ? mode.folderName : null)
      } catch {
        if (!controller.signal.aborted) setFolderName(null)
      }
    })()
    return () => controller.abort()
  }, [sessionId])

  // ✕ 关闭：PUT folderId:null（仅关夹维度——bookmarksOnly 等由 host 语义保留）。
  const close = useCallback(async () => {
    if (sessionId === undefined || busy) return
    setBusy(true)
    try {
      const result = await patchChatMode(sessionId, { folderId: null })
      setFolderName(result.mode.folderId !== null ? result.mode.folderName : null)
    } catch {
      /* 关闭失败：保持现状（胶囊还在），下次点击重试。不弹错误——
         host 端 chatmode 路由错误已经在会话流里可见。 */
    } finally {
      setBusy(false)
    }
  }, [sessionId, busy])

  if (folderName === null) return null
  return (
    <div
      data-ks-scope-chip=""
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 10px',
        margin: '0 2px 4px',
        width: 'fit-content',
        borderRadius: 999,
        border: '1px solid #d99000',
        background: '#fff8e6',
        color: '#7a4a00',
        fontSize: 11.5,
        lineHeight: 1.4,
      }}
      title={`本会话每一轮检索都限定在收藏夹「${folderName}」的内容内（标准级收藏按整本计）。点 ✕ 恢复全库。`}
    >
      <span aria-hidden>🔖</span>
      <span style={{ fontWeight: 600 }}>{folderName}</span>
      <span style={{ color: '#9c6b1f' }}>· 仅在本收藏夹内提问</span>
      <button
        type="button"
        onClick={() => void close()}
        disabled={busy}
        aria-label="关闭收藏夹范围提问（恢复全库）"
        title="关闭：恢复全库检索"
        style={{
          border: 'none',
          background: 'transparent',
          color: '#7a4a00',
          cursor: busy ? 'default' : 'pointer',
          fontSize: 13,
          lineHeight: 1,
          padding: '0 2px',
          fontWeight: 700,
          marginLeft: 2,
        }}
      >
        ✕
      </button>
    </div>
  )
}
