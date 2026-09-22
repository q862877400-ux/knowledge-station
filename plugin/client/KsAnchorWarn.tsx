/**
 * ks-dsh-plugin — client/KsAnchorWarn.tsx
 *
 * 引文坐标（bbox）缺失/取失败的**可见**提示行（诊断 A1/A8：原实现只 `console.warn`，
 * 箭头悄悄不出现——「失败必须写在脸上」是 UI 语言规范 §二.5 的铁律）。
 *
 * 独立纯组件的理由：渲染级冒烟能**单独钉它**（同 `KsMaterialsPanel` 的 AnchorMark 先例）——
 * 把它内联在 KsEvidenceTab 里就得拖着 pdf.js 才能测，判据会贵到没人写。
 */
import * as React from 'react'

/**
 * 警示行/警示条**共用**的 token 样式（一个出处：本组件与 entry.ts 的提示条都用它）。
 * ⚠ token 必须是主题**真定义**的（判据目录 = DSH `ui-theme/src/styles`）：曾用过两个
 * **不存在**的 token（--dsw-alias-surface-raised / --dsw-alias-border-default）被复核 F0
 * 打回——不存在的 token = 背景裸奔 / 静默落字面兜底，恰是 P2 禁的写法。
 */
export const KS_WARN_STYLE: { color: string; background: string; border: string } = {
  color: 'var(--dsw-alias-state-warn-primary)',
  background: 'var(--dsw-alias-bg-layer-2)',
  border: '0.5px solid var(--dsw-alias-border-l1)',
}

/** 同一出处的 cssText 形态（entry.ts 的非 React 提示条用）。禁字面兜底（P2）。 */
export function ksWarnCssText(): string {
  return `color:${KS_WARN_STYLE.color};background:${KS_WARN_STYLE.background};border:${KS_WARN_STYLE.border};`
}

export function KsAnchorWarn(props: { message: string }): React.ReactElement {
  return (
    <div
      role="alert"
      style={{
        padding: '4px 8px', fontSize: 11.5, lineHeight: 1.6, borderRadius: 4,
        color: KS_WARN_STYLE.color,
        background: KS_WARN_STYLE.background,
        border: KS_WARN_STYLE.border,
      }}
    >
      ⚠ {props.message}
    </div>
  )
}
