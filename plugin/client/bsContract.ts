/**
 * ks-dsh-plugin — client/bsContract.ts (2026-09-09)
 *
 * 对第三方 `dsh-better-sidebar` 的依赖集中声明 + 运行时能力探测。
 *
 * 为什么需要（用户 2026-09-09 提出：「我们这一套建立在 better-sidebar 上，
 * 万一人家更新了怎么办」）：本插件客户端半的重头戏都挂在它上面——tab 注册、
 * 外链接管（urlTarget）、单例 tab 的 path 覆写（updateTab/meta）、侧栏宽度与
 * 偏好读写（state.width / pluginSettings）、tab 生命周期。它是**第三方插件**，
 * 升级可能改名、删方法、改 state 形状。散落各处的 `?.` 只能保证"不崩"，却
 * 不会告诉你"哪个能力没了、哪块功能静默退化"。
 *
 * 三道防线：
 *   1. **启动探测**（本文件）：用上游声明的单调能力表 `service.features` +
 *      方法存在性做一次体检——缺必需能力 → `console.error`；缺可选能力或
 *      版本漂移 → `console.warn` 并说明退化成什么样。
 *   2. **契约冒烟**（`scripts/smoke-bs-contract.mjs`，纳入 `npm run smoke`）：
 *      对**已安装版本**的类型声明逐条断言我们用到的方法/字段/常量还在不在。
 *      上游一升级，开发期立刻报红，而不是等用户点开 PDF 才发现。
 *   3. **逐调用降级**：每个可选 API 调用都走 `?.` + try/catch，缺了就少一个
 *      便利功能，绝不让 PDF 打不开（见 KsEvidenceTab / pdfPanel）。
 */

/** 我们验证过的 better-sidebar 版本（0.18.0）；升级后请跑 `npm run smoke:bs-contract`。 */
export const BS_TESTED_VERSION = '0.18.0'

/**
 * 必需方法：真正缺了就没法注册/打开 tab——这是唯一的"致命"判据。
 * 故意收得很紧：宁可注册后逐项降级，也不要因为一个可选 API 改名就整块功能消失。
 */
const REQUIRED_METHODS = ['registerTab', 'openTab'] as const

/** 可选方法：缺失即降级（不是错误，但要在控制台说清楚）。 */
const OPTIONAL_METHODS = [
  'updateTab',       // 单例 tab 的 path 覆写（连续跳多个证据的必要条件）
  'activateTab',
  'closeTab',
  'isTabEnabled',
  'getSnapshot',     // 侧栏宽度让位/偏好读取（pdfPanel、showArrow 订阅）
  'subscribeState',  // 偏好/状态订阅（showArrow 即时生效）
  'getPrefs',
] as const

/**
 * 我们真正依赖的能力名（`service.features`，上游 v0.12.0+ 的单调列表）。
 * 上游承诺"能力只增不减"，所以这些应当一直在；缺失只报警+降级，不阻断注册。
 */
const REQUIRED_FEATURES = [] as const
const OPTIONAL_FEATURES = ['tabMeta', 'updateTab', 'stateSubscription', 'pluginSettings', 'urlTarget'] as const

export interface BsCompat {
  /** 上游自报的 service 版本（旧版可能没有该字段）。 */
  version: string | null
  /** 必需方法/能力是否齐全。 */
  ok: boolean
  missingRequired: string[]
  missingOptional: string[]
  /** 与本插件验证过的版本是否不一致（不一致就要跑冒烟，而不是假定坏了）。 */
  versionDrifted: boolean
}

/** 探测一次 better-sidebar 的能力面（任何异常都视为"探不到"，不抛）。 */
export function checkBetterSidebar(service: unknown): BsCompat {
  const svc = (service ?? {}) as {
    version?: unknown
    features?: unknown
    [key: string]: unknown
  }
  const version = typeof svc.version === 'string' ? svc.version : null
  const features = Array.isArray(svc.features) ? svc.features.map(String) : null

  const missingRequired: string[] = []
  const missingOptional: string[] = []
  for (const m of REQUIRED_METHODS) {
    if (typeof svc[m] !== 'function') missingRequired.push(`service.${m}()`)
  }
  for (const m of OPTIONAL_METHODS) {
    if (typeof svc[m] !== 'function') missingOptional.push(`service.${m}()`)
  }
  for (const f of REQUIRED_FEATURES) {
    if (features !== null && !features.includes(f)) missingRequired.push(`feature:${f}`)
  }
  for (const f of OPTIONAL_FEATURES) {
    if (features !== null && !features.includes(f)) missingOptional.push(`feature:${f}`)
  }
  return {
    version,
    ok: missingRequired.length === 0,
    missingRequired,
    missingOptional,
    versionDrifted: version !== null && version !== BS_TESTED_VERSION,
  }
}

/**
 * 启动时汇报一次契约体检结果。返回 compat 以便调用方决定是否注册 tab。
 * 只在真的有问题时打印——版本漂移 + 能力齐全只给一条 warn（提示跑冒烟）。
 */
export function reportBetterSidebarCompat(service: unknown): BsCompat {
  let compat: BsCompat
  try {
    compat = checkBetterSidebar(service)
  } catch {
    return {
      version: null, ok: false,
      missingRequired: ['service(unreadable)'], missingOptional: [], versionDrifted: false,
    }
  }
  if (!compat.ok) {
    console.error(
      '[ks-dsh-plugin] better-sidebar 契约不满足：缺少必需能力 '
      + `${compat.missingRequired.join('、')}；PDF 查看器/收藏等 tab 功能将不可用。`
      + '请跑 `npm run smoke:bs-contract` 查看契约差异。',
    )
    return compat
  }
  if (compat.missingOptional.length > 0 || compat.versionDrifted) {
    console.warn(
      `[ks-dsh-plugin] better-sidebar 兼容性提示：`
      + `版本 ${compat.version ?? '未知'}（本插件验证于 ${BS_TESTED_VERSION}）`
      + (compat.missingOptional.length > 0
        ? `，以下可选能力缺失、相关功能将降级：${compat.missingOptional.join('、')}`
        : '')
      + '。建议跑 `npm run smoke:bs-contract` 复核。',
    )
  }
  return compat
}
