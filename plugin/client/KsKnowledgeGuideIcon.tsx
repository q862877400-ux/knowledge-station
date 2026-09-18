/**
 * ks-dsh-plugin — client/KsKnowledgeGuideIcon.tsx
 *
 * 「知识库」开始页卡片的图标（书架：两栏 + 右侧条目线）。
 *
 * 单一来源：**两处**都用它 ——
 *   ① `ksSidebar.ts` 的 `guide[].icon`（官方在 provider **没有**自定义卡时用它兜底）；
 *   ② `KsKnowledgeGuide.tsx`（我们实际画的那张卡）。
 * 若两处各画一个，兜底路径与正常路径的图标就会长得不一样。
 *
 * 约定照 `KsPdfGuideIcon`：`{ size, className }`，`stroke="currentColor"`
 * ⇒ 颜色跟随宿主文字色，深浅色/换肤自动正确，**不要**写死颜色。
 */

import type { ReactNode } from 'react'

import type { KsIconProps } from './ksSidebar'

/**
 * 画知识库图标。
 *
 * @param props - `size`（宿主按有无说明取 22 或 26）+ `className`（布局/着色类）。
 * @returns 一个 `currentColor` 描边的内联 SVG。
 */
export function KsKnowledgeGuideIcon({ size = 26, className }: KsIconProps): ReactNode {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H9v16H5.5A1.5 1.5 0 0 1 4 18.5z" />
      <path d="M11 4h7.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H11z" />
      <path d="M13.5 8.5h4M13.5 12h4" />
    </svg>
  )
}
