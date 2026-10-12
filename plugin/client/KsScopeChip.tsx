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
  /** 输入坞 owner props 的输入状态（InputZone.input；草稿文本供合规哨兵预判据）。 */
  input?: { draft?: string; draftRev?: number }
}

/** dock 组件主体（不激活 = null）。 */
export function KsScopeChip(props: KsScopeChipProps): JSX.Element | null {
  const { sessionId } = props
  const [folderName, setFolderName] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  /* S2/C2-a 合规哨兵（2026-09-22）：草稿发**宿主**判（词表唯一在宿主，客户端零复制），
     命中 ⇒ 宿主打会话标记（提示段按需带 L1）。防抖 300ms。
     ⚠⚠ **2026-10-12（业主裁定，方案 A）：保留后台判断，删掉全部界面展示。**
       业主原话：「这个自动检测哨兵，你后台可以继续这样判断，但我不需要你在前台展示，
       也不要搞任何展示，就把它定回去，直接把展示相关的逻辑删掉就好了。」
       ⇒ 本次删掉：① 那句中间档轻提示（上一轮已删）；② **「⚖ 合规护航：待命」徽章**（本轮删）。
       ⇒ **保留**：这次 `POST /ks/compliance/ping` —— 它**不是展示**，而是**后台判断的唯一触发点**：
         宿主收到它才 `markComplianceTriggered()`，下一轮模型才会多拿到一段合规流程说明。
         **删掉它 = 后台判断一起死**（业主明确要保留后台判断，所以留着）。
       ⇒ 因此本次**只删 `sentry` 状态与它的渲染块**；这个 effect 仍发请求，但**不再 `setState`**、
         也不再读回执（回执里 `triggered` 只用来打宿主标记，界面不需要）。
       ⚠ 边界：客户端**零复制**词表、**零显示**；判据失效/未命中同样零界面开销。
       ⚠ 判据：`smoke-compliance-sentry.mjs` 钉"界面不显示徽章"（负向钉，防回潮）。 */
  const draft = props.input?.draft ?? ''
  useEffect(() => {
    if (sessionId === undefined || sessionId.length === 0) return
    if (draft.trim().length === 0) return
    const timer = setTimeout(() => {
      /* 只发不读：宿主据此打会话标记（后台判断），界面**不消费**回执。 */
      void fetch('/ks/compliance/ping', {
        method: 'POST',
        headers: { 'content-type': 'application/json', accept: 'application/json' },
        body: JSON.stringify({ session: sessionId, text: draft }),
      }).catch(() => {
        /* 判据口不可用：静默（哨句兜底），不打扰输入 */
      })
    }, 300)
    return () => clearTimeout(timer)
  }, [sessionId, draft])

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

  /* ⚠ 2026-10-12（业主裁定 A）：**本组件不再渲染任何合规相关的东西** ——
     只剩「收藏夹范围」胶囊。合规哨兵的判断仍在后台跑（上面那个 effect 照发请求），
     但界面**零展示**（徽章、提示全删）。
     ⇒ 未激活收藏夹时**恒返回 null**（不再有"因为哨兵命中所以占一行"的情况）。
     ⇒ 走到这里 `folderName` 必非 null ⇒ 直接返回胶囊本身，不再套外层 div
       （外层 div 是当年为"徽章 + 胶囊并排"准备的，现在只剩一个孩子）。 */
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
