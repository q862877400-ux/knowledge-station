/**
 * ks-dsh-plugin — client/KsEvidenceHost.tsx  (2026-09-16 官方 sidebar 迁移)
 *
 * 官方 `sidebar.right.pane.tab` 座位与 `KsEvidenceTab` 之间的**适配层**。
 *
 * ## 为什么要有这一层
 * `KsEvidenceTab` 是 1600+ 行的成熟实现，它的输入契约是旧的
 * `TabComponentProps`（`tab.path` / `tab.meta` / `scope` / `store` / `ctx`）。
 * 官方座位注入的是**另一套形状**（`useTabInfo()` + `inject(sessionId, actions)`）。
 * 让 1600 行组件跟着上游改名是**高风险低收益**；故在此把官方形状**映射成组件既有
 * 契约**，组件本体只改"取 props 的那几行"（见 `ks-evidence-props.ts`）。
 *
 * ## 字段映射（权威表见 `ksSidebar.ts` 文件头）
 * | 组件要的 | 官方来源 |
 * |---|---|
 * | `tab.path` | `useTabInfo().tab.navigation.params.url`（单例地址不带查询段，见 ksSidebar.ts 的"为什么地址必须恒定"） |
 * | `tab.meta`（重载 nonce） | `useTabInfo().tab.navigation.revision`（`navigate` 每次 +1） |
 * | `tab.id` | `useTabInfo().tab.id` |
 * | `visible` | `useTabInfo().tab.visible`（缺省 true —— 面板未展开时官方不给该字段） |
 * | `scope.sessionId` | 注入工厂的 `sessionId` |
 * | `prefs.showArrow` | 宿主固定默认（官方无共享 prefs 存储） |
 * | `panel`（宽度能力） | **不给** —— 官方右侧栏无宽度面，见 `ks-evidence-props.ts` |
 * | `onOpenEvidence` | `ctx.sidebarRight.openResource`（同一地址再导航 → revision +1 → 组件重载） |
 *
 * ## 为什么不用 `tab.actions`
 * 官方 `SidebarRightTabActions` 面向"改标题/关 tab"等布局动作；本组件需要的是
 * **再导航**，那属于 `ctx.sidebarRight` 服务面（已由宿主闭包持有），故不绕 actions。
 */
import * as React from 'react'

import { KsEvidenceTab } from './KsEvidenceTab'
import type { KsEvidenceProps } from './ks-evidence-props'
import type { KsEvidenceNavParams, UseKsTabInfo } from './ksSidebar'

/**
 * 官方 `sidebar.right.pane.tab` 座位注入给 body 的成员（我们用到的最小面）。
 *
 * `useTabInfo` 由宿主在注册时经 `inject: { hooks: { tabInfo } }` 提供
 * （官方 `sidebar.right.pane.tab` 座位声明带 `hookContext: TabHookContext`）。
 */
export interface KsEvidenceHostInjected {
  useTabInfo: UseKsTabInfo
  /** 再导航一条证据（把新 URL 送进同一个单例 tab）。 */
  openEvidence: (evidenceUrl: string) => void
}

/** 宿主组件：官方座位 props + 注入面。 */
export type KsEvidenceHostProps = KsEvidenceHostInjected

/**
 * 渲染证据 PDF tab。
 *
 * `sessionId` 不在此处取：官方 `inject` 工厂收到 sessionId，但 body 组件拿不到它
 * （`tab-info.ts` 的 `TabHookContext` 明确注释 "never passed as tab component props"）。
 * 本组件当前不需要 sessionId —— 旧代码里它只用于"面板宽度按会话记账"，而宽度能力
 * 已被移除（见文件头）；组件对 `scope` 缺失是安全的（`sessionId === undefined`
 * 时 `tabOpen` 分诊退化为"仍打开"，绝不误改宽度）。
 */
export function KsEvidenceHost(props: KsEvidenceHostProps): React.ReactElement {
  const { useTabInfo, openEvidence } = props
  const info = useTabInfo()
  const t = info.tab

  /** 证据 URL：单例地址不带查询段，真实证据在 `navigation.params` 里。 */
  const params = t.navigation?.params as KsEvidenceNavParams | undefined
  const evidenceUrl = typeof params?.url === 'string' ? params.url : undefined

  const evidenceProps: KsEvidenceProps = React.useMemo(() => ({
    tab: {
      id: t.id,
      type: t.kind,
      title: t.title,
      path: evidenceUrl,
      /**
       * 重载 nonce。旧模型是"共享单调计数器"（`nextEvidenceClick()`）；
       * 官方模型里 `navigation.revision` 由 `tab-domain.navigate` 每次 **必递增**，
       * 语义等价且无需我们自己维护计数器 —— 组件既有的
       * `[tab.path, tab.meta]` effect 因此照常触发（含"同一 URL 再点一次"）。
       */
      meta: { ksClick: t.navigation?.revision ?? 0 },
    },
    // 官方只在面板展开且是本 tab 时给 `visible: true`；字段缺席按"可见"处理，
    // 否则首次挂载会因 undefined 而整片不绘制。
    visible: t.visible !== false,
    prefs: { showArrow: true },
    onOpenEvidence: (url: string) => openEvidence(url),
  }), [t.id, t.kind, t.title, evidenceUrl, t.navigation?.revision, t.visible, openEvidence])

  return React.createElement(KsEvidenceTab, evidenceProps)
}
