/**
 * ks-dsh-plugin — client/pdfPanel.ts (2026-09-09)
 *
 * PDF 查看器的「侧栏临时让位」协调器（用户 2026-09-09 需求）：
 *
 *   点证据链接（或从文件目录打开文档）落到 PDF 查看器时，把侧栏拉宽到"文档友好
 *   宽度"，保证 PDF 可读；**关闭 PDF 查看器时恢复到打开之前的宽度**——用户不该
 *   读完 PDF 还要手动把侧栏拖回去。
 *
 * 为什么用模块级 Map 而不是组件 state：宽度是**会话级**资源，而"恢复"这个动作
 * 发生在组件卸载之后（组件已经拿不到自己的 state 了）。
 *
 * 依赖面（2026-09-16 迁移后）：本地的 `PanelWidthPort`（`getWidth`/`setWidth`），
 * 由证据 tab 宿主注入。旧实现直接吃第三方 better-sidebar 的 store；该包已被官方
 * `dsh-client-ui-sidebar-right` 取代，且官方列**没有**宽度面，故解耦为可选端口——
 * 端口缺席时全部调用静默降级为"不动侧栏"，绝不因此让 PDF 打不开。见 ksSidebar.ts。
 */

/** better-sidebar 的面板宽度上限（PANEL_MAX，0.18.0 为 640）。 */
export const PANEL_MAX_WIDTH = 640
/** 面板最小可用宽度（上游 PANEL_MIN=280；我们至少保证 400）。 */
export const PANEL_MIN_WIDTH = 400
/** 打开文档时希望占用的窗口宽度比例（小屏不硬拉满，给对话区留位置）。 */
export const PANEL_WIDEN_RATIO = 0.42

/** sessionId → 打开 PDF 之前的宽度（仅第一次记录，恢复后删除）。 */
const savedWidths = new Map<string, number>()

function sessionKey(sessionId: string | undefined): string {
  return typeof sessionId === 'string' && sessionId.length > 0 ? sessionId : '(active)'
}

/**
 * 面板宽度能力端口（2026-09-16 官方 sidebar 迁移后新增）。
 *
 * 旧实现直接吃第三方 `dsh-better-sidebar` 的 store（`getSnapshot().state.width`
 * 读 + `update(draft=>draft.width=…)` 写）。该包已被官方取代，且官方右侧栏
 * **没有**宽度面（它是可分屏/浮动的 dock 列），故这里改为一个与上游解耦的
 * **可选端口**：由证据 tab 宿主（`KsEvidenceHost`）决定给不给。
 * 宿主不给 → 本模块的让位/恢复全部不执行（PDF 按当前列宽铺满）。
 */
export interface PanelWidthPort {
  /** 当前宽度（px）；不可读返回 null。 */
  getWidth(): number | null
  /** 写入宽度；不可写返回 false。 */
  setWidth(px: number): boolean
}

/** 读当前面板宽度；不可读 → null。 */
function readWidth(port: PanelWidthPort | undefined): number | null {
  try {
    const w = port?.getWidth()
    return typeof w === 'number' && Number.isFinite(w) ? w : null
  } catch {
    return null
  }
}

/** 写面板宽度；不可写 → false（调用方无需区分原因，静默降级）。 */
function writeWidth(port: PanelWidthPort | undefined, width: number): boolean {
  try {
    return port?.setWidth(width) === true
  } catch {
    return false
  }
}

/** 文档友好宽度：窗口宽的 42%，夹在 [PANEL_MIN_WIDTH, PANEL_MAX_WIDTH]。 */
export function pdfPanelTargetWidth(viewportWidth: number): number {
  const vw = Number.isFinite(viewportWidth) && viewportWidth > 0 ? viewportWidth : 1440
  return Math.min(PANEL_MAX_WIDTH, Math.max(PANEL_MIN_WIDTH, Math.floor(vw * PANEL_WIDEN_RATIO)))
}

/**
 * 打开文档时让位：第一次调用记住"打开前的宽度"，随后每次把面板拉到目标宽度。
 * 返回是否真的写入了（false = 已经够宽 / store 不可写）。
 */
export function widenPanelForPdf(store: PanelWidthPort | undefined,
                                 sessionId: string | undefined): boolean {
  const key = sessionKey(sessionId)
  const current = readWidth(store)
  // 只在第一次记录原始宽度——后续每次点证据都重新拉宽，但恢复目标始终是最初那个。
  if (current !== null && !savedWidths.has(key)) savedWidths.set(key, current)
  const target = pdfPanelTargetWidth(
    typeof window === 'undefined' ? 1440 : window.innerWidth,
  )
  if (current !== null && current >= target) return false
  return writeWidth(store, target)
}

/**
 * 关闭 PDF 查看器时恢复：把宽度还原成打开前那个值并清掉记录（幂等——重复调用
 * 不会覆盖用户之后的手动拖拽）。
 */
export function restorePanelAfterPdf(store: PanelWidthPort | undefined,
                                     sessionId: string | undefined): boolean {
  const key = sessionKey(sessionId)
  // 关掉 PDF 查看器时目录列也随组件消失 → 它的扩宽记账一并作废（否则下次打开
  // PDF 再开目录列会重复累加，收不回到原宽度）。
  tocRestore.delete(key)
  const saved = savedWidths.get(key)
  if (saved === undefined) return false
  savedWidths.delete(key)
  return writeWidth(store, saved)
}

/** 仅供冒烟/诊断：当前是否处于"已让位未恢复"状态。 */
export function hasPendingPanelRestore(sessionId: string | undefined): boolean {
  return savedWidths.has(sessionKey(sessionId))
}

// ---------------------------------------------------------------- 标题目录列
/**
 * 标题目录列宽度（KsEvidenceTab 的 $tocColumn.width）。打开目录列时按这个宽度
 * **把侧栏整体向左扩**，而不是从 PDF 里切走一条（用户 2026-09-09：
 * 「点击标题目录的时候，要让 sidebar 向左扩张而不是压缩 PDF 的阅读空间」）。
 */
export const TOC_COLUMN_WIDTH = 190

/**
 * 顶开目录列时的宽度硬上限（绝对 px）。注意这**允许超过 PANEL_MAX_WIDTH(640)**：
 * 640 是上游 `setWidth`（拖拽手柄）的契约范围，但状态层与渲染层实际按
 * `[280, window.innerWidth]` 收敛——better-sidebar 0.18.0 的 `sanitizeState` 是
 * `Math.max(280, Math.min(record.width, window.innerWidth))`，面板渲染是
 * `Math.min(state.width, window.innerWidth)`，所以 640→830 能真的渲染出来。
 * 代价与兜底：① 用户下次拖拽手柄会被 `setWidth` 拉回 640（可接受）；
 * ② 上游若改成硬钳制，我们在下面**读回校验**会发现并自动退化为悬浮覆盖。
 */
export const TOC_PUSH_MAX_WIDTH = 900
/** 顶开时给对话区保留的最小宽度（不能为了看目录把对话挤没）。 */
export const MIN_CONVERSATION_WIDTH = 480

/** sessionId → 为了目录列扩宽前的原始宽度与已扩量（关闭时按此收回）。 */
const tocRestore = new Map<string, { from: number; gained: number }>()

/**
 * 打开目录列时向左扩张侧栏。返回 true = **完整**让出了目录列的宽度（PDF 阅读区
 * 寸土不失）；false = 空间不够（窗口太窄/已到硬上限）或 store 不可写——调用方
 * 应改用悬浮覆盖（见 KsEvidenceTab 的 tocOverlay），仍不压缩 PDF。
 *
 * 写入后**读回校验**：上游若把宽度钳制到自己的上限（例如未来把 PANEL_MAX 变成
 * 硬闸），这里会如实回报 false 而不是假装成功。
 */
export function growPanelForToc(store: PanelWidthPort | undefined,
                                sessionId: string | undefined): boolean {
  const key = sessionKey(sessionId)
  const current = readWidth(store)
  if (current === null) return false
  const viewport = typeof window === 'undefined' ? 1440 : window.innerWidth
  const ceiling = Math.max(PANEL_MIN_WIDTH, Math.min(TOC_PUSH_MAX_WIDTH,
    viewport - MIN_CONVERSATION_WIDTH))
  const target = Math.min(ceiling, current + TOC_COLUMN_WIDTH)
  const gained = target - current
  if (gained <= 0) return false
  if (!writeWidth(store, target)) return false
  const applied = readWidth(store)
  if (applied === null) return false
  const real = applied - current
  if (real <= 0) return false
  if (real < TOC_COLUMN_WIDTH - 1) {
    // 只能扩一小截（verifier P1-6）：push 必须**全有或全无**，否则会退化成
    // "面板微扩 + 目录列悬浮"的混用——那 190px 的布局宽度一帧内消失，
    // PDF 反而会瞬移一次。这里把这次写入回滚，交给调用方走悬浮覆盖。
    writeWidth(store, current)
    return false
  }
  const prev = tocRestore.get(key)
  tocRestore.set(key, { from: prev?.from ?? current, gained: (prev?.gained ?? 0) + real })
  return true
}

/** 关闭目录列时把之前扩出去的宽度收回（幂等；用户拖过侧栏也只收回我们加的那部分）。 */
export function shrinkPanelAfterToc(store: PanelWidthPort | undefined,
                                    sessionId: string | undefined): boolean {
  const key = sessionKey(sessionId)
  const rec = tocRestore.get(key)
  if (rec === undefined || rec.gained <= 0) return false
  tocRestore.delete(key)
  const current = readWidth(store)
  if (current === null) return false
  // 用户没动过 → 精确还原到扩宽前的宽度（可能低于我们的 400 软下限，
  // 上游面板下限是 280，不能因为我们而把用户拖窄的侧栏顶宽）；
  // 用户中途拖过 → 只收回我们加的那部分。
  const target = current === rec.from + rec.gained
    ? rec.from
    : Math.max(PANEL_MIN_WIDTH, current - rec.gained)
  return writeWidth(store, target)
}
