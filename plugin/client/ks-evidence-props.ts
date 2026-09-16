/**
 * ks-dsh-plugin — client/ks-evidence-props.ts
 *
 * KS 自有的证据 tab 组件 props 契约（2026-09-16 从第三方声明中剥离）。
 *
 * 为什么不再从 `dsh-better-sidebar/client/service` 取 `TabComponentProps`：
 * 该第三方包**已从 DSH profile 移除**，官方以 `dsh-client-ui-sidebar-right` 取代。
 * 组件的 props 现在由 `KsEvidenceHost`（官方座位适配器）构造，形状由本文件定义——
 * 于是"证据查看器需要什么"不再挂在某个第三方包的声明上（换上游不会连累组件）。
 *
 * 字段含义与迁移映射见 `ksSidebar.ts` 的文件头表。
 */
import type * as React from 'react'

/** 会话作用域（旧 better-sidebar 的 `scope`；官方模型里由座位注入的 sessionId 提供）。 */
export interface KsSessionScope {
  sessionId?: string
  cwd?: string
  repoRoot?: string
}

/** 证据 tab 记录（组件读 `path`/`meta`/`id`；`path` 现由 `navigation.address` 换算）。 */
export interface KsEvidenceTabRecord {
  id: string
  type: string
  title: string
  /** 证据锚点 href（`http://127.0.0.1:1/__ks_evidence__?...`）。 */
  path?: string
  /**
   * **重载 nonce**。
   *
   * 旧模型用 better-sidebar 的 `tab.meta` 承载一个单调计数器，使"路径值相同的
   * 再次点击"也能触发组件的 `[tab.path, tab.meta]` effect 重载。官方模型里
   * `tab.navigation.revision` 每次 `navigate` 必递增（`tab-domain.ts:130`），
   * 语义**完全对应**且更干净 —— `KsEvidenceHost` 直接把它透传到这里。
   */
  meta?: unknown
}

/**
 * 「法规标准知识库」设置里的 PDF 偏好（旧模型读共享 side-card prefs 的
 * `pluginSettings['ks:settings']`）。官方模型**没有**等价的共享 prefs 存储，
 * 故改由 `KsEvidenceHost` 以 props 注入（当前主机固定给默认值）。
 */
export interface KsEvidencePrefs {
  /** 是否显示红箭头（缺省 true）。 */
  showArrow: boolean
}

/**
 * **可选**的面板宽度能力（旧模型直接读写 better-sidebar 的 `state.width`）。
 *
 * 官方右侧栏**没有**对应的宽度读写面：它是可分屏/可浮动的 dock 列，尺寸由布局
 * 与用户拖拽决定，暴露的是 `split`/`float`/`dock` 而非"设定宽度"。故本能力改为
 * **可选对象**——宿主不提供时，"打开 PDF 自动拉宽侧栏"整条路径**自然不执行**，
 * 而不是留下一条永远拿不到 store 的死代码。
 *
 * 该体验特性（打开文档让位 / 关闭恢复）已按裁定记为**可复议项**：
 * 若将来官方提供宽度面，或我们改用 `split()` 表达"给 PDF 更多空间"，在此实现即可。
 */
export interface KsPanelWidthPort {
  /** 当前宽度（px）；不可读返回 null。 */
  getWidth(): number | null
  /** 写入宽度；不可写返回 false。 */
  setWidth(px: number): boolean
}

/** 旧 `TabComponentProps` 中本组件实际使用的成员（其余一律不声明）。 */
export interface KsEvidenceProps {
  tab: KsEvidenceTabRecord
  /** 本 tab 是否可见（面板展开且是本 tab）。不可见时暂停重绘。 */
  visible: boolean
  scope?: KsSessionScope
  /** 改本 tab 的标题（旧 `ctx.betterSidebar.updateTab(id,{title})`；省略则不改）。 */
  onUpdateTitle?: (title: string) => void
  /** 旧模型里"再从历史/收藏跳一条证据"以覆写单例 tab 实现；官方模型下由宿主注入。 */
  onOpenEvidence?: (evidenceUrl: string, title?: string) => void
  /** tab 仍存在于其会话里（卸载分诊用）；省略视为"仍打开"（绝不误改用户宽度）。 */
  tabOpen?: (sessionId: string, tabId: string) => boolean
  prefs: KsEvidencePrefs
  /** 可选的面板宽度能力；省略 = 不做自动让位（见 `KsPanelWidthPort`）。 */
  panel?: KsPanelWidthPort
}

/** tab body 的 React 组件签名。 */
export type KsEvidenceComponent = (props: KsEvidenceProps) => React.ReactElement
