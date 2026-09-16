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
 *
 * ---- 2026-09-16 追加：缩放状态机（底部常驻栏的滑块 / 浏览比例下拉）----
 * 「翻页模式（单页|连续）」与「缩放来源（自适应|手动）」是**两个正交状态**，
 * 本文件只负责后者：`zoomScale()` 把 (ZoomState, 容器尺寸) 解算成实际 scale。
 *   · 默认 `{ source:'autoFit' }` → 就是上面那套铺满规则（一字未改）；
 *   · 一旦手动选百分比 / 拖滑块 → `{ source:'manual', percent }`，此后**不再读
 *     容器尺寸**（窗口拉伸不改缩放），只有再选「自适应窗口」才回到 autoFit。
 * 手动百分比钳制在 **[10, 500]**（不是 0——0% 会渲染成空白页，已与用户确认
 * 左端取最小可读值 10%，见 MANUAL_MIN_PERCENT）。
 * 连续模式下"可视高"约束的是滚动窗口而非单页，故用 continuousViewportHeight()
 * 把逻辑高抬高、让同一个 fitPageScale 退化成"宽度适配 + 溢出预算"。
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

// ---------------------------------------------------------------- 缩放状态机
/**
 * 缩放来源（2026-09-16 用户需求：底部常驻栏的「浏览比例」下拉 + 拖动式滑块）。
 *
 *   'autoFit' = **自适应窗口**：跟着容器走（窗口拉伸 / 侧栏拖宽 / 目录列开合都重算），
 *               算法就是上面那套 fitPageScale「铺满 + 溢出预算」——**默认态**；
 *   'manual'  = 用户手选百分比或拖过滑块：此后容器尺寸变化**不再**改缩放，
 *               只有再点「自适应窗口」才恢复自动。
 *
 * 与「翻页模式」（单页 / 连续）**完全独立**——两者是正交的两个状态，不要合并：
 * 单页也能量手缩放，连续也能自适应。见 zoomScale()。
 */
export type ZoomSource = 'autoFit' | 'manual'

/** 缩放状态：autoFit 不携带百分比，manual 携带用户选的百分比。 */
export type ZoomState =
  | { source: 'autoFit' }
  | { source: 'manual'; percent: number }

/** 默认（打开即）自适应窗口。 */
export const ZOOM_AUTO: ZoomState = { source: 'autoFit' }

/**
 * 手动缩放的下限 —— **10%，不是 0%**。
 *
 * 用户需求（2026-09-16）原话是"最左 = 0% / 最右 = 500%"，但 0% 会让 pdf.js 渲染出
 * **空白页**（viewport 尺寸为 0，canvas 被清空且什么都画不出来），用户拖到最左就
 * 只能盲拖回来。**已与用户确认：左端钳制到最小可读值 10%**（任务 §5 选项 (a)）。
 * 滑块刻度仍按 0..500 显示，只是最左端落点是 10%。
 *
 * 注意它**不影响自适应**：fitPageScale 的 MIN_SCALE 仍是 0.5（极窄侧栏的兜底），
 * 手动下限只在用户主动输入百分比/拖滑块时生效。
 */
export const MANUAL_MIN_PERCENT = 10
/** 手动缩放的右端 = 500%（滑块最右）。 */
export const MANUAL_MAX_PERCENT = 500

/** 「浏览比例」下拉选项，最下方一项固定是「自适应窗口」。 */
export const ZOOM_PRESET_PERCENTS = [25, 50, 75, 100, 125, 150] as const

/** 把任意输入（滑块值 / 下拉值 / 界面上抄来的数字）钳到 [10, 500] 并取整。 */
export function clampManualPercent(percent: number): number {
  if (!Number.isFinite(percent)) return MANUAL_MIN_PERCENT
  return Math.max(MANUAL_MIN_PERCENT, Math.min(MANUAL_MAX_PERCENT, Math.round(percent)))
}

/** 手选/拖动一个百分比 → manual 状态（自动退出自适应）。 */
export function zoomForManual(percent: number): ZoomState {
  return { source: 'manual', percent: clampManualPercent(percent) }
}

/** 点「自适应窗口」→ 恢复自动（此后容器变化重新驱动缩放）。 */
export function zoomForAutoFit(): ZoomState {
  return ZOOM_AUTO
}

/** 当前生效的缩放（scale）与它从哪来，供 UI 与画布共用同一份真值。 */
export interface ZoomView {
  /** **实际要应用的**缩放：manual = 用户百分比（已钳制）/100；autoFit = 上面那套铺满规则。 */
  scale: number
  source: ZoomSource
  /** 要回显给用户看的百分比（已四舍五入；manual 下等于用户选的值）。 */
  percent: number
  /** autoFit 才有意义：由哪个方向决定的（见 FitResult）。 */
  basis: 'width' | 'height' | null
  /** autoFit 才有意义：是否被上下限钳制。 */
  clamped: boolean
  /** autoFit 才有意义：是否被横向溢出预算拦住（见 fitPageScale）。 */
  cappedByBudget: boolean
}

/**
 * 把「缩放状态 + 容器实测尺寸」解算成一份可用的缩放。
 *
 * **手动百分比就是真值**：manual 下直接返回用户选的百分比，**不再看容器尺寸**
 * ——这正是"窗口拉伸后缩放不再自动变"的机制（窗口变化 → 容器尺寸变 → 这里
 * 仍然返回同一个 scale）。autoFit 下才走 fitPageScale（原规则一字未改）。
 *
 * 容器尚未布局（fitPageScale 返回 null）时不假装有值：scale 回落到自适应规则的
 * 下限 MIN_SCALE 并把 clamped 置真，调用方按既有 null 语义跳过本次绘制即可。
 */
export function zoomScale(state: ZoomState, input: FitInput): ZoomView {
  if (state.source === 'manual') {
    const percent = clampManualPercent(state.percent)
    return {
      scale: percent / 100,
      source: 'manual',
      percent,
      basis: null,
      clamped: false,
      cappedByBudget: false,
    }
  }
  const fit = fitPageScale(input)
  if (fit === null) {
    return {
      scale: input.minScale ?? MIN_SCALE,
      source: 'autoFit',
      percent: Math.round((input.minScale ?? MIN_SCALE) * 100),
      basis: null,
      clamped: true,
      cappedByBudget: false,
    }
  }
  return {
    scale: fit.scale,
    source: 'autoFit',
    percent: Math.round(fit.scale * 100),
    basis: fit.basis,
    clamped: fit.clamped,
    cappedByBudget: fit.cappedByBudget,
  }
}

/**
 * 连续（瀑布）模式下的"逻辑容器高度"。
 *
 * 连续模式是把 N 页**纵向堆叠**在一个滚动容器里——此时"可视高"约束的是**滚动窗口**
 * 而不是某一页，若照旧把容器高喂给 fitPageScale，窄侧栏会走到 `min(fitHeight, …)`：
 * 抽屉正好塞满一屏高，却比可视宽宽出 1.25 倍，堆叠后每页都要左右拖。
 *
 * 所以连续模式取"宽定标"：把逻辑高抬到远超任何一页的高度，让 fitPageScale 里的
 * `raw = max(fitWidth, min(fitHeight, widthCap))` 恒等于 `widthCap`（横向溢出预算），
 * 也就是**宽度适配 + 至多 25% 横向溢出**。
 *
 * 刻意不改 fitPageScale 本身（用户 2026-09-16 明确要求"不要顺带破坏这套规则"）：
 * 这只是喂给同一个纯函数的输入，规则一字未动。
 * 倍率 4 的余量：只要 `4 × availWidth ≥ availWidth/pageWidth × 1.25`，即
 * `pageWidth ≥ 0.3125`，宽就不会被高反超——pdf.js 的 viewport scale=1 尺寸（pt）
 * 最小也有几百，恒成立；真出现极窄长条页也只是退化为高度定标，不会算崩。
 */
export function continuousViewportHeight(availWidth: number): number {
  const w = Number.isFinite(availWidth) && availWidth > 0 ? availWidth : 1
  return w * 4
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
