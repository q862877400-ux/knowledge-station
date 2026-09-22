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

export function KsAnchorWarn(props: { message: string }): React.ReactElement {
  return (
    <div
      role="alert"
      style={{
        padding: '4px 8px', fontSize: 11.5, lineHeight: 1.6, borderRadius: 4,
        // 颜色只走 token、**不带字面兜底**（ui-audit-D P2 点名的正是 `var(...,#hex)` 兜底：
        // 同一 token 的各家兜底互相矛盾、且深浅主题下静默回退）。缺 token 就该裸奔暴露。
        color: 'var(--dsw-alias-state-warn-primary)',
        background: 'var(--dsw-alias-surface-raised)',
      }}
    >
      ⚠ {props.message}
    </div>
  )
}
