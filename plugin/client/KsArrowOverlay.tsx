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

/**
 * 半透明版箭头（**同轮其他被引用的条款**用，spec 012 R4，业主 2026-10-12 要求）。
 *
 * 业主原话：「我点的那一条条目它的箭头是红的，其他同一个文件里面其他的被引用上的条目，
 * 就变成半透明，把透明度降低一点的这个箭头」。
 *
 * 实现：同一个 path，`opacity="0.35"`（不用换颜色 —— 换色会让"红"这个产品记号分叉；
 * 透明度表达的是"也是同一轮的，但不是我点的那条"）。透明度是**唯一所有者** `KS_SIBLING_OPACITY`。
 */
export const KS_SIBLING_OPACITY = 0.35

/** 半透明红箭头（同轮其他条款）。 */
export const KS_ARROW_SVG_SIBLING = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><path d="M0 4h11V1l9 4-9 4V6H0z" fill="#e02020" opacity="${KS_SIBLING_OPACITY}"/></svg>`

/** 把一份箭头 SVG 变成可用的 background-image 值（唯一转换处，两个覆盖层共用）。 */
export function arrowBackground(svg: string): string {
  return `url("data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}")`
}

/** 覆盖层的公共样式（两个覆盖层共用，避免各写一份导致视觉漂移）。 */
function overlayStyle(svg: string): React.CSSProperties {
  return {
    position: 'absolute',
    display: 'none',
    pointerEvents: 'none',
    backgroundImage: arrowBackground(svg),
    backgroundRepeat: 'no-repeat',
    backgroundSize: '100% 100%',
  }
}

export const KsArrowOverlay = React.forwardRef<HTMLDivElement, object>(
  function KsArrowOverlay(_props, ref) {
    return <div ref={ref} aria-hidden="true" style={overlayStyle(KS_ARROW_SVG)} />
  },
)

/**
 * **同轮其他条款**的半透明箭头覆盖层（spec 012 R4）。
 *
 * 与主箭头**分离成两个 DOM 节点**（不是一个节点画多条）的理由：
 * 主箭头是"我点的这条"，几何由 `renderPage` 每帧现算并**独占**那个 `div.style`；
 * 兄弟箭头可能有 0~N 条、位置各不相同。若塞进同一个节点，
 * 就得在里面维护一串子元素，反而把"主箭头"这条既有链路改复杂。
 * 分成两个节点后：主箭头链路**一字未动**（既有判据全绿），兄弟箭头是纯增量。
 */
export const KsSiblingArrowsOverlay = React.forwardRef<HTMLDivElement, object>(
  function KsSiblingArrowsOverlay(_props, ref) {
    return <div ref={ref} aria-hidden="true" style={overlayStyle(KS_ARROW_SVG_SIBLING)} />
  },
)
