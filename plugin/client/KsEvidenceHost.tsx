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
 * | `prefs.showArrow` | **ksPrefs 本地偏好**（订阅式；设置区开关即时生效）——2026-09-22 修诊断 A2：曾写"宿主固定默认"并硬编码 `true`，设置里的开关因此是死的 |
 * | `panel`（宽度能力） | **不给** —— 官方右侧栏无宽度面，见 `ks-evidence-props.ts` |
 * | `onOpenEvidence` | `ctx.sidebarRight.openResource`（同一地址再导航 → revision +1 → 组件重载） |
 *
 * ## ⚠ `useTabInfo` 是**运行时 prop**，不是 inject 面（2026-09-17 修空白 pane）
 * 官方座位契约（`ui-sidebar-right/src/client/contract/slots.ts:50-54`）：
 * ```
 * 'sidebar.right.pane.tab': { hookContext: TabHookContext, inject: SidebarRightTabInjected }
 * ```
 * `hookContext: TabHookContext` ⇒ 框架把 `useTabInfo` **直接作为组件运行时 prop** 交给 body
 * （官方 `TextPreview.tsx:96`、`GuideBody.tsx:80` 都是这样解构的）。
 * `inject` 工厂的**第一个参数是 `sessionId`**（官方 `ui-sidebar-documentpreview/src/client/index.ts:104`
 * 写作 `inject: (sessionId, actions) => …`），其**返回值才是本插件贡献给组件的面**。
 *
 * 我们曾把 `inject` 的第一参数当成"聚合面"并断言 `hooks.tabInfo` 存在 —— 那个值**永远是
 * undefined**，于是自设的守卫在挂载时抛错 → 官方 `slot entry crashed` → **开始页点进来的
 * PDF pane 全白**（2026-09-17 真机实测：console 明确报此错）。修法见下：
 * `useTabInfo` 走 props，`openEvidence` 才是我们的 inject 面。
 *
 * ## 为什么不用 `tab.actions`
 * 官方 `SidebarRightTabActions` 面向"改标题/关 tab"等布局动作；本组件需要的是
 * **再导航**，那属于 `ctx.sidebarRight` 服务面（已由宿主闭包持有），故不绕 actions。
 */
import * as React from 'react'

import { KsEvidenceTab } from './KsEvidenceTab'
import type { KsEvidenceProps } from './ks-evidence-props'
import type { KsEvidenceNavParams, UseKsTabInfo } from './ksSidebar'
import { getPrefsSnapshot, subscribePrefs } from './ksPrefs'

/**
 * 官方座位**运行时**交给 body 的成员（框架给，不经 inject）。
 *
 * `hookContext: TabHookContext` 决定它：官方所有 pane body 都这样拿 `useTabInfo`。
 */
export interface KsEvidenceHostRuntime {
  useTabInfo: UseKsTabInfo
}

/** 本插件**贡献**给该座位的 inject 面（工厂返回值即此形状）。 */
export interface KsEvidenceHostInjected {
  /** 再导航一条证据（把新 URL 送进同一个单例 tab）。 */
  openEvidence: (evidenceUrl: string) => void
}

/** 宿主组件：运行时 props + 本插件的 inject 面。 */
export type KsEvidenceHostProps = KsEvidenceHostRuntime & KsEvidenceHostInjected

/**
 * 座位守卫：只在**契约被破坏**时显示一句人话。
 *
 * 为什么不在这里 `throw`：座位里抛错会被官方包成 `slot entry crashed`，用户看到的是
 * **空白面板**（2026-09-17 实测）。守卫的目的本来就是"别让用户看见无因的空白"，
 * 抛错恰好违背这个目的 —— 故改为**渲染可见的错误文案**。
 *
 * 为什么拆成两个组件：`useTabInfo()` 必须在 body 里**无条件**调用（React hooks 规则），
 * 而守卫要先判断它是不是函数。守卫自己不调 hook，body 无条件调 —— 顺序稳定。
 */
export function KsEvidenceHost(props: KsEvidenceHostProps): React.ReactElement {
  const { useTabInfo, openEvidence } = props
  if (typeof useTabInfo !== 'function') {
    return React.createElement(
      'div',
      { style: { padding: '12px', fontSize: '12px', lineHeight: 1.6, opacity: 0.8 } },
      '[ks-dsh-plugin] 官方 sidebar.right.pane.tab 座位未提供运行时 prop `useTabInfo`'
      + '——右侧栏契约可能已变更，PDF 证据查看器无法渲染。',
    )
  }
  return React.createElement(KsEvidenceBody, { useTabInfo, openEvidence })
}

/**
 * 渲染证据 PDF tab。
 *
 * `sessionId` 不在此处取：官方 `inject` 工厂收到 sessionId，但 body 组件拿不到它
 * （`tab-info.ts` 的 `TabHookContext` 明确注释 "never passed as tab component props"）。
 * 本组件当前不需要 sessionId —— 旧代码里它只用于"面板宽度按会话记账"，而宽度能力
 * 已被移除（见文件头）；组件对 `scope` 缺失是安全的（`sessionId === undefined`
 * 时 `tabOpen` 分诊退化为"仍打开"，绝不误改宽度）。
 */
function KsEvidenceBody(props: KsEvidenceHostProps): React.ReactElement {
  const { useTabInfo, openEvidence } = props
  const info = useTabInfo()
  const t = info.tab

  // 设置区「显示红色定位箭头」的偏好：订阅 ksPrefs（诊断 A2：这里曾硬编码 `showArrow: true`
  // ⇒ 设置里的开关是死的、查看器恒显箭头。偏好存储本来就是订阅式的，缺的只是这根线）。
  // ⚠ 两个读值回调**同源**（都读内存快照）：本插件纯客户端、没有 SSR，第三参数只会被
  // `renderToStaticMarkup` 类渲染使用（我们的冒烟）——若给它另一套"服务端默认值"，
  // 判据就只能看见默认值、看不见开关的真实效果（2026-09-22 实测踩过：断言恒真）。
  const showArrow = React.useSyncExternalStore(
    subscribePrefs,
    () => getPrefsSnapshot().showArrow,
    () => getPrefsSnapshot().showArrow,
  )

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
    prefs: { showArrow },
    onOpenEvidence: (url: string) => openEvidence(url),
  }), [t.id, t.kind, t.title, evidenceUrl, t.navigation?.revision, t.visible, openEvidence, showArrow])

  return React.createElement(KsEvidenceTab, evidenceProps)
}
