/**
 * ks-dsh-plugin — client/pdfFit.ts (2026-09-09，规则三次修订，末次 2026-09-17)
 *
 * PDF 页「默认铺满」缩放规则。需求起点是"默认打开后 PDF 太小"，且要随窗口最大化 /
 * 侧栏拖宽 / 浏览器缩放自适应。**"铺满"的具体含义改过两次，以 v3 为准（见下）。**
 *
 * 演进：
 *   v1（fit-width）：只按容器**宽度**适配，纵向一大片留白；用户反馈"PDF 太小"。
 *   v2（2026-09-09，铺满 + 溢出预算）：`max(fitWidth, min(fitHeight, fitWidth×1.25))`
 *      —— 高度优先，允许横向溢出。副作用：只要侧栏"高瘦"（`fitHeight > fitWidth`）页宽就
 *      超出可视宽，溢出比例 `min(fitHeight/fitWidth, 1.25) − 1 ∈ (0, 25%]` —— 窄侧栏恒为
 *      满额 25%（400px 侧栏实测切 94px，每行末尾 20% 字符在滚动区外）。且只在
 *      翻页/切目录时重算，最大化窗口或拖宽侧栏都不会重绘（后由 ResizeObserver 解决）。
 *   v3（2026-09-17，现行）：用户据实反馈"自适应窗口模式下 PDF 的右边一部分显示不出来"
 *      并裁定 **"宽度铺满，高度不用管——万一 sidebar 拉得很宽，高度再怎么样都匹配不上"**。
 *      ⇒ 回到**纯 fit-width**，但保留 v2 引入的自适应重算能力。理由：长页本来就得
 *      纵向滚动，为"高度优先"牺牲横向完整性没有意义。规则见 fitPageScale 的注释。
 *
 * 纯函数、零 DOM 依赖：便于离线冒烟（scripts/smoke-pdf-fit.mjs）。
 *
 * ---- 2026-09-16 追加：缩放状态机（底部常驻栏的滑块 / 浏览比例下拉）----
 * 「翻页模式（单页|连续）」与「缩放来源（自适应|手动）」是**两个正交状态**，
 * 本文件只负责后者：`zoomScale()` 把 (ZoomState, 容器尺寸) 解算成实际 scale。
 *   · 默认 `{ source:'autoFit' }` → **宽度铺满**（2026-09-17 规则，见 fitPageScale）；
 *   · 一旦手动选百分比 / 拖滑块 → `{ source:'manual', percent }`，此后**不再读
 *     容器尺寸**（窗口拉伸不改缩放），只有再选「自适应窗口」才回到 autoFit。
 * 手动百分比钳制在 **[10, 500]**（不是 0——0% 会渲染成空白页，已与用户确认
 * 左端取最小可读值 10%，见 MANUAL_MIN_PERCENT）。
 * 2026-09-17：因自适应不再读高度，单页/连续两种翻页模式的定标**完全相同**，
 * 原先用于"把旧规则压回宽度适配"的 `continuousViewportHeight()` 已删除。
 */

/** 容器 padding（上下/左右各 12px）合计，需从可用空间里扣掉。 */
export const PAGE_PADDING = 24
/** 缩放下限：再小就看不清了，宁可横向滚动。 */
export const MIN_SCALE = 0.5
/** 缩放上限：避免容器极大时把页面拉成马赛克。 */
export const MAX_SCALE = 2.5
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
  /**
   * 由哪个方向决定缩放。2026-09-17 起**恒为 'width'**（高度不再参与定标）；
   * 保留该字段是因为 UI 文案（"宽度铺满"提示）与冒烟断言按它分支。
   */
  basis: 'width' | 'height'
  /** 是否被 MIN/MAX 钳制（钳制时 basis 仅供参考）。 */
  clamped: boolean
  /** 历史字段：旧规则里表示"本可按高度拉满但被横向预算拦住"。规则 v3 起恒为 false。 */
  cappedByBudget: boolean
}

/**
 * 计算「自适应窗口」缩放。
 *
 * ---- 2026-09-17 规则变更（用户裁定："宽度铺满，高度不用管"）----
 * 现行规则只有一句：**`scale = 可用宽 / 页宽`**（再被 MIN/MAX 钳制），**高度完全不参与**。
 *
 * 为什么改：旧规则是 `max(fitWidth, min(fitHeight, fitWidth×1.25))`（"高度优先铺满 +
 * 1.25 横向溢出预算"）。它的副作用是：只要侧栏"高瘦"（`fitHeight > fitWidth`）页宽就超出
 * 可视宽，溢出比例 `min(fitHeight/fitWidth, 1.25) − 1 ∈ (0, 25%]` —— 窄侧栏恒为满额 25%，
 * 其余是递减到 0（A4、可视高 883 下的拐点在侧栏 ~648px）。用真实函数实测：
 *     侧栏 400 → scale 0.790 → 页宽 470 vs 可视 376 → **右侧切 94px（可视宽的 25%）**
 *     侧栏 520 → scale 1.042 → 页宽 620 vs 可视 496 → **右侧切 124px（同为满额 25%）**
 *     侧栏 709 → scale 1.151 → 页宽 685 vs 可视 685 → 不切
 * 用户据实反馈"自适应窗口模式下 PDF 的右边一部分显示不出来"，并裁定：
 * **"宽度铺满，高度不用管——万一 sidebar 拉得很宽，高度再怎么样都匹配不上"**。
 * 即：长页本来就得纵向滚动，为"高度优先"牺牲横向完整性没有意义。
 * ⇒ 旧规则里"按高度定标"与"1.25 溢出预算"一起退休；`MAX_WIDTH_OVERFLOW` 与
 *   `continuousViewportHeight`（后者本是为了把旧规则人为压回宽度适配）随之删除。
 *
 * 保留 `availHeight > 0` 的检查：它是**"容器已布局"的守卫**（0/负值 → 返回 null，
 * 调用方跳过本次绘制），不再参与缩放。
 *
 * `MIN_SCALE`(0.5) 仍是可读性下限：侧栏窄到 < ~322px（可用宽 < 297.6 = 0.5×595.28）时才钳到 0.5，那时会重新出现
 * 横向滚动——"看不清 vs 看不全"的取舍，取前者。
 */
export function fitPageScale(input: FitInput): FitResult | null {
  const { availWidth, availHeight, pageWidth, pageHeight } = input
  const min = input.minScale ?? MIN_SCALE
  const max = input.maxScale ?? MAX_SCALE
  if (!(availWidth > 0) || !(availHeight > 0)) return null
  if (!(pageWidth > 0) || !(pageHeight > 0)) return null
  // 宽度铺满；高度不参与（见上方 2026-09-17 规则变更）。
  const raw = availWidth / pageWidth
  const scale = Math.max(min, Math.min(raw, max))
  // basis / cappedByBudget 保留字段以兼容既有消费者，但在这条规则下恒为定值：
  // 定标永远来自宽度；也不存在"被横向预算拦住"这回事（预算已退休）。
  return { scale, basis: 'width', clamped: scale !== raw, cappedByBudget: false }
}

// ---------------------------------------------------------------- 缩放状态机
/**
 * 缩放来源（2026-09-16 用户需求：底部常驻栏的「浏览比例」下拉 + 拖动式滑块）。
 *
 *   'autoFit' = **自适应窗口**：跟着容器走（窗口拉伸 / 侧栏拖宽 / 目录列开合都重算），
 *               算法就是上面那套 fitPageScale「宽度铺满」——**默认态**；
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
  /** **实际要应用的**缩放：manual = 用户百分比（已钳制）/100；autoFit = 宽度铺满（见 fitPageScale）。 */
  scale: number
  source: ZoomSource
  /** 要回显给用户看的百分比（已四舍五入；manual 下等于用户选的值）。 */
  percent: number
  /** autoFit 才有意义：由哪个方向决定的（规则 v3 起恒为 'width'，见 FitResult）。 */
  basis: 'width' | 'height' | null
  /** autoFit 才有意义：是否被上下限钳制。 */
  clamped: boolean
  /** 历史字段（见 FitResult.cappedByBudget）：规则 v3 起恒为 false。 */
  cappedByBudget: boolean
}

/**
 * 把「缩放状态 + 容器实测尺寸」解算成一份可用的缩放。
 *
 * **手动百分比就是真值**：manual 下直接返回用户选的百分比，**不再看容器尺寸**
 * ——这正是"窗口拉伸后缩放不再自动变"的机制（窗口变化 → 容器尺寸变 → 这里
 * 仍然返回同一个 scale）。autoFit 下才走 fitPageScale（规则以 fitPageScale 的注释为准，
 * 2026-09-17 由「高度优先铺满」改为「宽度铺满」）。
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
