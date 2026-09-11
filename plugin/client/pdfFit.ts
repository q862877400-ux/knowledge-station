/**
 * ks-dsh-plugin — client/pdfFit.ts (2026-09-09)
 *
 * PDF 页「默认铺满」缩放规则（用户反馈：默认打开后 PDF 太小，希望高度尽可能高，
 * 且要随窗口最大化 / 侧栏拖宽 / 浏览器缩放自适应）。
 *
 * 旧行为：只按容器**宽度**适配（fit-width）→ 侧栏 400px 时 A4 页只有 ~0.63 倍、
 * 纵向一大片留白；且只在翻页/切目录时重算，最大化窗口或拖宽侧栏都不会重绘。
 *
 * 新规则（铺满 + 溢出预算）：`scale = max(fitWidth, min(fitHeight, fitWidth × 1.25))`
 *   - 宽窗口（宽比高富余）：fitHeight 小于 fitWidth，取 fitWidth —— 等同传统
 *     fit-width，不产生横向滚动；
 *   - 侧栏够宽（fitHeight 在上限内）：取 fitHeight，页面纵向拉满 —— 即用户要的
 *     「高度尽可能高」；
 *   - 侧栏很窄（fitHeight 超上限）：退回「可视宽 +25%」，保证至少 80% 行宽可见。
 * 为什么必须有上限（verifier P1-2, 2026-09-09）：纯 cover 在 400px 侧栏（目录列
 * 展开时 PDF 区仅 ~186px）会把页面放到可视宽的 3.5 倍 —— 每行都要左右拖，且页面
 * 左缘的红箭头/收藏按钮直接滚出视野，定位功能退化。上限让「铺满」只在真的装得下
 * 时生效；面板拖到上限 640 时 fitHeight 恰好落在上限内 → 仍按高度拉满。
 *
 * 纯函数、零 DOM 依赖：便于离线冒烟（scripts/smoke-pdf-fit.mjs）。
 */

/** 容器 padding（上下/左右各 12px）合计，需从可用空间里扣掉。 */
export const PAGE_PADDING = 24
/** 缩放下限：再小就看不清了，宁可横向滚动。 */
export const MIN_SCALE = 0.5
/** 缩放上限：避免容器极大时把页面拉成马赛克。 */
export const MAX_SCALE = 2.5
/**
 * 允许的横向溢出倍率：页面最多比可视宽多 25%（≈80% 行宽始终可见）。
 * 1.25 的取舍见文件头——再大就该只按宽度适配了。
 */
export const MAX_WIDTH_OVERFLOW = 1.25
/**
 * canvas 后备位图像素上限（含 dpr 放大）。超限时降 dpr——否则 2.5 倍 × dpr 3
 * 的 A4 页会产生 ~9000×12000 的画布（浏览器直接拒绝或吃光内存）。
 */
export const MAX_BACKING_PIXELS = 24_000_000

export interface FitInput {
  /** 容器可用宽（已扣 padding），<=0 表示尚未布局。 */
  availWidth: number
  /** 容器可用高（已扣 padding），<=0 表示尚未布局。 */
  availHeight: number
  /** PDF 页原始宽（viewport scale=1 的 width）。 */
  pageWidth: number
  /** PDF 页原始高。 */
  pageHeight: number
  minScale?: number
  maxScale?: number
}

export interface FitResult {
  scale: number
  /** 由哪个方向决定缩放（'height' = 纵向拉满；'width' = 横向适配）。 */
  basis: 'width' | 'height'
  /** 是否被上下限钳制（钳制时 basis 仅供参考）。 */
  clamped: boolean
  /** 本可以纵向拉满，但被横向溢出上限拦住（退化为按宽适配）。 */
  cappedByBudget: boolean
}

/**
 * 计算「铺满」缩放。容器尚未布局（宽或高 <= 0）→ 返回 null，调用方应跳过本次
 * 绘制，等 ResizeObserver / visible 变化再画（绝不用 0 尺寸算出畸形缩放）。
 */
export function fitPageScale(input: FitInput): FitResult | null {
  const { availWidth, availHeight, pageWidth, pageHeight } = input
  const min = input.minScale ?? MIN_SCALE
  const max = input.maxScale ?? MAX_SCALE
  if (!(availWidth > 0) || !(availHeight > 0)) return null
  if (!(pageWidth > 0) || !(pageHeight > 0)) return null
  const fitWidth = availWidth / pageWidth
  const fitHeight = availHeight / pageHeight
  const widthCap = fitWidth * MAX_WIDTH_OVERFLOW
  // 先按高度拉满，再被横向预算压回；fitHeight < fitWidth（宽窗口）时 max 取 fitWidth。
  const raw = Math.max(fitWidth, Math.min(fitHeight, widthCap))
  const basis: 'width' | 'height' = raw === fitHeight ? 'height' : 'width'
  const scale = Math.max(min, Math.min(raw, max))
  return { scale, basis, clamped: scale !== raw, cappedByBudget: raw < fitHeight }
}

/**
 * 后备位图 dpr：优先用设备 dpr 保证清晰；像素总量超上限时按面积比降 dpr
 * （永远 >= 1，低于 1 会糊得比 CSS 像素还差）。
 */
export function backingStoreDpr(cssWidth: number, cssHeight: number, deviceDpr: number): number {
  const dpr = Number.isFinite(deviceDpr) && deviceDpr > 0 ? deviceDpr : 1
  const area = cssWidth * cssHeight
  if (!(area > 0)) return dpr
  const budget = Math.sqrt(MAX_BACKING_PIXELS / area)
  return Math.max(1, Math.min(dpr, budget))
}
