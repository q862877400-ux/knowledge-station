/**
 * ks-dsh-plugin — client/ksPrefs.ts  (2026-09-16 官方 sidebar 迁移)
 *
 * KS 自有的**侧栏偏好存储**，取代旧模型里寄存在 `dsh-better-sidebar` 的
 * side-card prefs（`pluginSettings['ks:settings']`）。
 *
 * ## 为什么必须自建
 * 旧实现把偏好写进 better-sidebar 的共享 prefs 文档（经其栅栏路由
 * `/sidebar/api/settings`，落宿主侧存储）。该包已被官方
 * `dsh-client-ui-sidebar-right` 取代，**官方右侧栏没有偏好存储面** ——
 * 旧路径整体消失。若不替换，设置区的红箭头开关及其对 `KsEvidenceTab` 的
 * 生效链路会一起失效。
 *
 * ## 选择本地持久化的理由
 * 偏好只有两个键、只在本浏览器生效、且**必须在 tab 组件重挂载后仍在**（旧实现
 * 能存活是因为宿主侧存储）。`localStorage` 同时满足"持久"与"同步可读"，且
 * 不引入任何新的宿主依赖 —— 与"KS 是本地单用户工具"的形态一致。
 *
 * ## 与旧行为的一处**差异（诚实标注）**
 * 旧实现经宿主存储，因此**同一 DSH 宿主的其他浏览器标签/窗口**也能共享该偏好；
 * 换成 `localStorage` 后共享范围是**同源同浏览器**。对单机单用户场景二者等价；
 * 若将来需要跨端一致，把本模块换成引擎侧 `app_config` 持久化即可（接口不变）。
 *
 * ## 为什么是可订阅的
 * 旧实现用 `service.subscribeState(cb)` 让设置区与 PDF 查看器**即时**响应开关。
 * 这里用模块级监听器集合复刻同一语义，并额外监听 `storage` 事件，使**同源其他
 * 标签页**的修改也能即时反映（比旧实现更即时）。
 */

/** 「法规标准知识库」偏好命名空间与键名（沿用旧值，便于迁移既有用户数据）。 */
export const KS_SETTINGS_PREFS_KEY = 'ks:settings'
export const KS_SHOW_ARROW_KEY = 'showArrow'

/** localStorage 的物理键（单一 blob，避免与我们自己的键名撞车）。 */
const LS_KEY = 'ks-dsh-plugin.prefs.v1'

/** 偏好形状（当前只有一个键；新增键在此扩展并保留旧键语义）。 */
export interface KsPrefs {
  /** 是否在 PDF 证据页显示红色定位箭头（缺省 true）。 */
  showArrow: boolean
}

/** 默认值（缺省开，与旧行为一致）。 */
export const KS_PREFS_DEFAULT: KsPrefs = { showArrow: true }

const listeners = new Set<() => void>()

/** 读存储（任何异常一律退回默认值——偏好坏了不该让 UI 崩）。 */
function readRaw(): KsPrefs {
  try {
    const s = globalThis.localStorage?.getItem(LS_KEY)
    if (s === null || s === undefined) return { ...KS_PREFS_DEFAULT }
    const o = JSON.parse(s) as Record<string, unknown>
    return {
      // 只有**显式 false** 才算关（`undefined`/缺失 = 开），与旧实现同口径。
      showArrow: o?.[KS_SHOW_ARROW_KEY] !== false,
    }
  } catch {
    return { ...KS_PREFS_DEFAULT }
  }
}

/** 当前快照。引用稳定：无变化时返回同一对象（`useSyncExternalStore` 要求）。 */
let snapshot: KsPrefs = readRaw()

function emit(): void {
  for (const fn of listeners) {
    try { fn() } catch { /* 监听器自身出错不影响其他监听器 */ }
  }
}

/**
 * 订阅偏好变化。
 * @param listener - 同步失效回调。
 * @returns 取消订阅。
 */
export function subscribePrefs(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

/**
 * 读偏好快照（稳定引用）。
 * @returns 当前偏好。
 */
export function getPrefsSnapshot(): KsPrefs {
  return snapshot
}

/**
 * 写偏好（浅合并）。
 * @param patch - 要改的键。
 */
export function updatePrefs(patch: Partial<KsPrefs>): void {
  const next: KsPrefs = { ...snapshot, ...patch }
  snapshot = next
  try {
    globalThis.localStorage?.setItem(LS_KEY, JSON.stringify(next))
  } catch { /* 隐私模式/配额满：内存态仍生效，仅不持久 */ }
  emit()
}

// 同源其他标签页改动 → 同步内存快照并通知（旧实现经宿主存储天然共享，这里补上）。
try {
  globalThis.addEventListener?.('storage', (e: StorageEvent) => {
    if (e.key !== null && e.key !== LS_KEY) return
    snapshot = readRaw()
    emit()
  })
} catch { /* 无 window（SSR/冒烟环境）：跳过，内存态仍可用 */ }
