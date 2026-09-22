/**
 * ks-dsh-plugin — client/KsTurnTab.tsx  （S1-a，2026-09-22）
 *
 * 「本轮」tab 的 body：跟着当前回答走的**本轮依据**（这轮用了哪几条、核对结果、看原文）。
 * 业主批准的形态见 `docs/mockups/mockup-S1-turn-tab.html`（假数据原型，已过目）。
 *
 * 本步（S1-a）只落：tab 注册 + **定稿空态**。数据通路与依据行在 S1-b
 * （宿主暂存 + `GET /ks/turn/last`，见 `var/tmp/design-S1-turn-data-mapping.md`），
 * 看原文/自动切换在 S1-c。**一步一提交**（业主 2026-09-22：小步走，不憋大招）。
 */
import * as React from 'react'

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

/** 本插件贡献给该 body 的注入面（现在只有诊断标签；S1-b 起取数走只读口）。 */
export interface KsTurnInjected {
  /** 谁是这一页的数据来源（诊断标签，不参与取数——同 KsKnowledgePage 的 dataSource）。 */
  dataSource: string
}

export type KsTurnTabProps = KsTurnTabRuntime & KsTurnInjected

export function KsTurnTab(_props: KsTurnTabProps): React.ReactElement {
  // S1-a：定稿空态（原型两屏中的"状态二"）。措辞一屏一事：说清为什么是空的、下一步做什么。
  return (
    <div
      style={{
        padding: '24px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 160,
        textAlign: 'center',
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
