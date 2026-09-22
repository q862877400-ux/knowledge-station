/**
 * ks-dsh-plugin — client/KsArrowOverlay.tsx
 *
 * 红色定位箭头覆盖层——单页/连续两种模式**共用同一实现**（同一时刻只有一份在树上，
 * `bboxRef` 可共用）。纯展示组件：几何由 `KsEvidenceTab` 的 renderPage 直接写 style
 * （left/top/width/height/display）。
 *
 * 独立成文件的理由同 `KsAnchorWarn`：渲染级冒烟单独钉它——红箭头图形（产品头号卖点的
 * 视觉本体）不许悄悄消失/换样。
 *
 * 坐标契约（红线）：bbox 为 PDF **底部原点**，由 convertToViewportPoint 消化（见
 * KsEvidenceTab renderPage 的注释：禁止再做 H−y 翻转）。此处只管呈现。
 */
import * as React from 'react'

/** 箭头图形本体（红色实心右箭头，2:1）。改它 = 改产品卖点的视觉，冒烟盯着。 */
export const KS_ARROW_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><path d="M0 4h11V1l9 4-9 4V6H0z" fill="#e02020"/></svg>'

export const KsArrowOverlay = React.forwardRef<HTMLDivElement, object>(
  function KsArrowOverlay(_props, ref) {
    return (
      <div
        ref={ref}
        aria-hidden="true"
        style={{
          position: 'absolute',
          display: 'none',
          pointerEvents: 'none',
          // 红色实心右箭头（data-URI SVG，2:1），指向条款行左缘。
          backgroundImage: `url("data:image/svg+xml;charset=UTF-8,${encodeURIComponent(KS_ARROW_SVG)}")`,
          backgroundRepeat: 'no-repeat',
          backgroundSize: '100% 100%',
        }}
      />
    )
  },
)
