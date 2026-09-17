/**
 * ks-dsh-plugin — client/KsPdfGuideIcon.tsx
 *
 * 侧栏**开始页**入口胶囊的图标（官方 `SidebarRightGuideEntry.icon`）。
 *
 * 契约（见官方 `ui-primitives/src/icons/props.ts` 的 `IconProps`）：组件收
 * `{ size?, className? }`，画出方形边长 `size` 的图形，**颜色随 `currentColor`**
 * （官方官方 tab 图标同款约定：开始页会在不同主题/选中态下改 `color`）。
 * 不传 `size` 时用 26（官方在"带说明"的胶囊上给 26，`EntryBox` 里 `description ===
 * undefined ? 22 : 26`）。
 *
 * 用 `createElement` 而非 JSX：与本目录既有 .tsx 的写法保持一致（KsEvidenceHost.tsx
 * 同样用 createElement），避免为一个小图标引入 JSX 运行时约定。
 */
import * as React from 'react'

import type { KsIconProps } from './ksSidebar'

/**
 * 文档 + 定位框：表达"按需翻到某一页的原文阅读器"。
 *
 * 画法保持极简（页面轮廓 + 折角 + 两行正文 + 一个定位方框），
 * 在 22–26px 下仍可辨认；线条统一 `stroke="currentColor"`、`fill="none"`。
 */
export function KsPdfGuideIcon({ size = 26, className }: KsIconProps): React.ReactElement {
  const s = String(size)
  return React.createElement(
    'svg',
    {
      width: s,
      height: s,
      viewBox: '0 0 24 24',
      fill: 'none',
      stroke: 'currentColor',
      strokeWidth: 1.6,
      strokeLinecap: 'round',
      strokeLinejoin: 'round',
      className,
      'aria-hidden': true,
      focusable: false,
    },
    // 页面轮廓（右上折角）
    React.createElement('path', { d: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z' }),
    React.createElement('path', { d: 'M14 3v5h5' }),
    // 正文两行
    React.createElement('path', { d: 'M9 13h6' }),
    React.createElement('path', { d: 'M9 17h3' }),
  )
}
