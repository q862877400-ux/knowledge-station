/**
 * ks-dsh-plugin — client/ksSidebar.ts  (2026-09-16 官方 sidebar 迁移)
 *
 * KS 与**官方右侧栏**（`@deepseek-ai/dsh-client-ui-sidebar-right`）之间的唯一适配层。
 *
 * ## 为什么要迁移
 * 原实现建立在第三方 `dsh-better-sidebar` 上（imperative `registerTab`/`openTab`/
 * `updateTab` + 自定义 state）。该包**已从 DSH profile 移除**，官方以
 * `@deepseek-ai/dsh-client-ui-sidebar-*` 五包取代，扩展模型换成 VS Code 式的
 * 「声明 tab 类型 + 注册 resolver」两段式。结果：`probeBetterSidebar()` 探不到服务
 * → 静默跳过全部 tab 注册 → **PDF 证据 tab 整块不可用**
 * （Inspect 实测 `sidebar.right.pane.tab` 的 keyDomain = "none are taken yet"）。
 *
 * ## 官方模型（两段式）
 *   ① `ctx.sidebarRightTabs.register(def)` —— 声明类型（kind / 地址 glob / 标题）；
 *   ② `ctx.slots.register({ name:'sidebar.right.pane.tab', key: def.id }, Component)`
 *      —— 注册 body；打开用 `ctx.sidebarRight.openResource(address, {kind})`。
 *
 * ## 与旧模型的关键映射（本文件的价值所在）
 * | 旧（better-sidebar） | 新（官方） |
 * |---|---|
 * | `tab.path`（URL 落在 path 上） | `useTabInfo().tab.navigation.address` |
 * | `tab.meta` **nonce**（强制重载：同值 path 也要重载） | `tab.navigation.revision` —— `tab-domain.ts:130` 每次 `navigate` 都 `set({…, revision:+1})`，**更干净** |
 * | `updateTab(id,{title})` | 不需要：官方 tab 记录自带 `title`（**我们就是靠它**）。⚠ 2026-09-19 更正：原文接着说"且标题可注册 `sidebar.right.pane.tab.title` 座位" —— **那个座位我们从来没注册过**，标题因此是**静态**的（不会随页面变化，例如不会显示"第 12 页"）。宿主确实有该座位，要不要用见 EXECUTION-PLAN 的 UI 轮 |
 * | URL 拦截（`urlTarget`） | 直接 `openResource(address, {kind})`，伪源 hack 可留作兼容入口 |
 * | `store`（side-card prefs/width） | **无对应物** → 见 `KsEvidenceHost` 的 `prefs` 注入 |
 *
 * ## 诚实边界
 * 官方**没有**等价的"面板宽度读写"API（旧 `store.getSnapshot().state.width` +
 * `store.update(draft => draft.width=…)`）。故 `pdfPanel.ts` 的"打开 PDF 自动拉宽
 * 侧栏"**不再由本适配层驱动**（已按用户裁定记为可复议项）。官方提供的是
 * 分屏/浮动（`split`/`float`/`dock`），比拉宽更结构化。
 */

import type { ComponentType } from 'react'

import { KsKnowledgeGuideIcon } from './KsKnowledgeGuideIcon'

/** 本类型的实现身份（body/title 座位的 key）与类型判别符。 */
export const KS_EVIDENCE_IMPL_ID = 'ks-dsh-plugin/evidence-pdf'
export const KS_EVIDENCE_KIND = 'ks-evidence'

/**
 * 证据地址的 scheme（**单例地址，不带查询段**）。
 *
 * ## 为什么地址必须恒定
 * 官方用 `(kind, contentId)` 判定"两个 tab 是不是同一个"，而 `contentId` **就是地址
 * 本身**（`tab-registry.ts:138-149` 的 `SidebarRightTabClaim` 注释：
 * "Two opens of the same address are the same tab, which is what makes opening
 * idempotent"）。若把 doc/page 编进地址，则每次点不同证据都会得到**不同地址** →
 * **开新 tab**，而 KS 的证据查看器是**单例**（旧模型 `single:true`）。
 *
 * 故：**地址恒定**为 `dsh-resource://ks-evidence`，证据本体走 `params`
 * （`openResource(address, {kind, params})`）。
 *
 * ## 重载由什么驱动
 * 官方 `tab-domain.ts:124-131` 的 `navigate()` 每次调用都
 * `existing.navigation.set({ …target, revision: revision + 1 })` —— 即**同一地址
 * 再次导航不会开新 tab，而是覆写导航并把 `revision` +1**。这正是旧模型
 * `tab.meta` 里那个单调 nonce 的官方对应物，且语义更明确。适配层把
 * `revision` 透传进组件的 `tab.meta`，组件既有的 `[tab.path, tab.meta]` 重载
 * effect **无需改动**即可继续工作。
 */
export const KS_EVIDENCE_RESOURCE_PREFIX = 'dsh-resource://ks-evidence'

/** 单例证据 tab 的地址（恒定，见上）。 */
export const KS_EVIDENCE_ADDRESS = KS_EVIDENCE_RESOURCE_PREFIX

/* ============================================================================
   「知识库」类型（2026-09-19 新增，业主指令：把开始页那张「PDF 查看器」卡改成
   「知识库」并加一个二级目录）。

   它与 PDF 证据 tab 是**两个类型**，刻意不合并：
   - `ks-evidence`（原有）：单例、地址恒定、**由证据链接驱动**（点引用跳那一页）；
   - `ks-knowledge`（新增）：知识库管理/导入/报告/渠道台账的**页面容器**，按
     `params.page` 分发四种页。
   合并会让"点证据跳页"和"打开管理页"抢同一个地址，重载语义立刻打结。
   ============================================================================ */

/** 知识库页的二级页（对应 ▾ 菜单里除 PDF 之外的项）。 */
export type KsKbPage = 'manage' | 'capabilities' | 'ingest' | 'report' | 'channels'

/** 知识库 tab 的实现身份与类型判别符。 */
export const KS_KB_IMPL_ID = 'ks-dsh-plugin/knowledge'
export const KS_KB_KIND = 'ks-knowledge'

/** 知识库 tab 的地址（与证据 tab 同理：地址恒定，二级页走 `params.page`）。 */
export const KS_KB_RESOURCE_PREFIX = 'dsh-resource://ks-knowledge'
export const KS_KB_ADDRESS = KS_KB_RESOURCE_PREFIX

/** 知识库 tab 的导航参数。 */
export interface KsKbNavParams {
  readonly page?: KsKbPage
}


/**
 * 一次证据导航的官方 `params`（`openResource` 的 `options.params`）。
 * 字段语义与 `ksEvidence.ts` 的 `KsEvidence` 一致，故解析仍是那一处所有者。
 */
export interface KsEvidenceNavParams {
  /** 证据锚点 href（`http://127.0.0.1:1/__ks_evidence__?doc=…`）。 */
  url: string
}

/** 官方 `sidebar.right.pane.tab` 座位注入的 hook 上下文（我们用到的最小面）。 */
export interface UseKsTabInfo {
  (): {
    tab: {
      id: string
      kind: string
      title: string
      /** 导航记录：地址 + 参数；`revision` 每次 navigate 递增 → 作为重载信号。 */
      navigation: {
        address: string
        revision: number
        params?: KsEvidenceNavParams | KsKbNavParams
      }
      /**
       * tab 级动作。**开始页的卡片必须用它**：官方 `GuideBody` 的胶囊被点后就是
       * `openTab(kind)`（见 `KsTabDefinition.guide` 的注释），而"卡片刻的画法"是
       * provider 自己负责的（官方 README 原话），所以从卡片里打开别的页也只能走这里。
       *
       * 形状取自宿主已发货的 `ui-sidebar-terminal/src/client/TerminalGuide.tsx`：
       * `tab.actions.openTab('terminal', { replaceTab: true, params: { shellPath } })`。
       */
      actions: {
        openTab(kind: string, options?: {
          replaceTab?: boolean
          params?: KsEvidenceNavParams | KsKbNavParams | Record<string, unknown>
        }): void
      }
      /** tab 记录生命周期的 AbortSignal（组件清理应挂它）。 */
      signal: AbortSignal
      visible?: boolean
    }
  }
}

/** 一个 tab 类型的静态声明（官方 `SidebarRightTabDefinition` 的最小面）。 */
export interface KsTabDefinition {
  readonly id: string
  readonly kind: string
  readonly multiple?: boolean
  readonly patterns?: readonly string[]
  readonly priority?: 'extension' | 'builtin' | 'fallback'
  readonly canOpen?: (address: string) => boolean
  readonly title: (address: string) => string
  /**
   * 侧栏**开始页**（「开始」tab）上的入口胶囊；不填就**不出现在开始页**。
   *
   * 官方 `GuideBody` 把每个已注册类型贡献的胶囊排成一列，点一个就
   * `openTab(kind)`（没有地址）在本栏里把它打开 —— 于是这正好是"手动入口"：
   * 不需要任何证据链接，也能把 PDF 阅读器点出来（我们的 tab 在无 `url` 参数时
   * 走 idle 态＝左列文件目录，见 `KsEvidenceHost`）。
   */
  readonly guide?: readonly KsGuideEntry[]
}

/** 图标组件的最小面（官方 `IconProps`：方形边长 + 布局 class；颜色随 currentColor）。 */
export interface KsIconProps {
  readonly size?: number
  readonly className?: string
}

/** 开始页上的一个入口胶囊（官方 `SidebarRightGuideEntry` 的最小面）。 */
export interface KsGuideEntry {
  /** 类型内唯一即可（官方按 `id` 校验同一类型内不重复）。 */
  readonly id: string
  /** **升序**排列（官方 `refresh()` 里 `.sort((l, r) => l.order - r.order)`）。 */
  readonly order: number
  readonly title: () => string
  readonly description?: () => string
  readonly icon?: ComponentType<KsIconProps>
}

/** 官方 tab 类型注册表（`ctx.sidebarRightTabs`）。 */
export interface KsTabRegistry {
  register(definition: KsTabDefinition): () => void
}

/** 官方右侧栏导航面（`ctx.sidebarRight`）——只声明我们调用的成员。 */
export interface KsSidebarRight {
  openResource(address: string, options?: {
    kind?: string
    params?: KsEvidenceNavParams
    revealIfOpened?: boolean
  }): void
}

/**
 * 把一条证据 URL 拼成官方导航参数。
 *
 * 入参沿用 `ksEvidence.ts` 的既有形态（`evidenceUrlOf()` 的输出：
 * `http://127.0.0.1:1/__ks_evidence__?doc=…`）——**不新增地址词表**，
 * 聊天里的证据锚点 href、host 侧 `KS_EVIDENCE_ORIGIN`、本函数三者一致。
 *
 * @param evidenceUrl - `evidenceUrlOf()` 产出的伪 URL。
 * @returns 官方 `params`。
 */
export function toNavParams(evidenceUrl: string): KsEvidenceNavParams {
  return { url: evidenceUrl }
}

/**
 * 资源地址判据：只认**本插件自己的**证据地址（避免接管外来链接）。
 * 因为地址恒定，"是不是我们的"只需比对前缀。
 */
export function isKsEvidenceResource(address: string): boolean {
  return address === KS_EVIDENCE_ADDRESS
    || address.startsWith(`${KS_EVIDENCE_ADDRESS}?`)
    || address.startsWith(`${KS_EVIDENCE_ADDRESS}/`)
}

/**
 * 证据 tab 的**初始**标题（地址里没有页号，故给通用名）。
 *
 * 页号标题目前由**我们自己的组件内部**渲染（宿主 tab 的 `title` 是静态的）。⚠ 2026-09-19 更正：原文说"由 `sidebar.right.pane.tab.title` 座位按 `navigation` 渲染" —— 我们**没有**注册那个座位（这条是审计里 S1 抓到的"注释声称注册了其实没注册"）
 * （见 `KsEvidenceHost`）——注册该座位是本迁移的一部分，否则标题会一直停在
 * "PDF 查看器"（旧模型靠 `updateTab` 补，官方模型靠 title 座位补）。
 *
 * @param _address - 官方资源地址（本实现不使用，签名由契约规定）。
 * @returns 通用标题。
 */
export function evidenceTabTitle(_address: string): string {
  return 'PDF 查看器'
}

/**
 * 开始页入口胶囊的排序值。
 *
 * 官方开始页把各类型贡献的胶囊按 `order` **升序**排（`tab-registry.refresh()`：
 * `.sort((left, right) => left.order - right.order)`）。实测在用的值：
 * `ui-sidebar-files` = **10**（工作区文件夹）、`ui-sidebar-terminal` = **20**（新建终端）、
 * `ui-sidebar-browser` = **30**（浏览器）。
 *
 * 取 **25** ⇒ 夹在「新建终端」与「浏览器」之间：仍在终端下面（原需求），
 * 且**不与任何出货条目同号**。
 *
 * ⚠ **2026-09-19 实测教训**：本值原本取 **30**，当时无人占用；DSH 升到 **alpha.2 新增了
 * `ui-sidebar-browser`，它的 guide 也取 30**
 * （`packages/client/ui-sidebar-browser/src/client/definition.tsx`：`{ id: 'new', order: 30 }`）
 * ⇒ 两张卡**同号**，谁在前只由注册顺序（即 bundle 顺序）决定，**看上去是随机的**。
 * 旧注释写的「上游新增条目时可能需要重排」**应验了**。
 * 所以：① 本值必须避开出货条目占用的号；② **每次升级 DSH 后都要重新核对**
 * （`git grep -n "order:" <ref> -- packages/client/ui-sidebar-*`）。
 */
export const KS_GUIDE_ORDER_PDF = 25

/**
 * 开始页入口卡片的标题。
 *
 * ⚠ **2026-09-19 起不再与 tab 标题同源**（原来两处都走 `evidenceTabTitle`）。
 * 业主把开始页那张卡从「PDF 查看器」改成「**知识库**」——因为它现在是一个**入口**
 * （下挂知识库管理/文件导入/效力报告/渠道台账 + PDF 查看器），不再是 PDF 阅读器本身。
 * PDF 阅读器的 tab 标题**仍是**「PDF 查看器」（`evidenceTabTitle`），两者刻意分开：
 * 卡片管"进哪个门"，tab 标题管"我正看着什么"，混用会让用户以为卡片刻的就是 PDF。
 */
export function ksGuideEntryTitle(): string {
  return '知识库'
}

/**
 * 开始页入口卡片的说明（官方只在条目 ≤4 个时才显示说明，多了只留标题）。
 */
export function ksGuideEntryDescription(): string {
  return '法规标准与自有资料：目录、标签、导入、效力报告'
}

/**
 * 构造本 tab 类型的官方声明。
 *
 * - `patterns` 只匹配**本插件自己的**恒定地址；
 * - `canOpen` 再确认一次（双保险）；
 * - `priority: 'extension'`（外部类型最高档，也是默认值——显式写出以自文档化）；
 * - **不设 `multiple`**：证据查看器是单例（`contentId` 恒定本身就保证了幂等打开）；
 * - `guide`：在侧栏**开始页**贡献一个手动入口（order 25 = 「新建终端」(20) 与「浏览器」(30) 之间）。
 */
export function ksEvidenceDefinition(): KsTabDefinition {
  return {
    id: KS_EVIDENCE_IMPL_ID,
    kind: KS_EVIDENCE_KIND,
    patterns: [KS_EVIDENCE_ADDRESS],
    priority: 'extension',
    canOpen: isKsEvidenceResource,
    title: evidenceTabTitle,
    guide: [{
      id: 'kb',
      order: KS_GUIDE_ORDER_PDF,
      title: ksGuideEntryTitle,
      description: ksGuideEntryDescription,
      icon: KsKnowledgeGuideIcon,
    }],
  }
}

/**
 * 知识库 tab 的标题（恒定：二级页名走页面内标题，不进 tab 标题，
 * 否则同一 tab 在四个二级页之间切换时标题会跳）。
 */
export function ksKbTabTitle(_address: string): string {
  return '知识库'
}

/** 知识库地址判据（只认我们自己的地址，避免接管外来链接）。 */
export function isKsKbResource(address: string): boolean {
  return address === KS_KB_ADDRESS
    || address.startsWith(`${KS_KB_ADDRESS}?`)
    || address.startsWith(`${KS_KB_ADDRESS}/`)
}

/**
 * 构造「知识库」tab 类型的官方声明。
 *
 * 与证据 tab 的差别：**不设 `patterns` 到证据地址**，用自己的地址；
 * 同样不设 `multiple`（单例：二级页是同一 tab 的四个面，不是四个 tab）。
 */
export function ksKbDefinition(): KsTabDefinition {
  return {
    id: KS_KB_IMPL_ID,
    kind: KS_KB_KIND,
    patterns: [KS_KB_ADDRESS],
    priority: 'extension',
    canOpen: isKsKbResource,
    title: ksKbTabTitle,
    // 不出现在开始页：开始页只保留一张「知识库」卡（它就是本类型的门），
    // 否则同一个入口会在开始页出现两次。
  }
}

/**
 * 框架转发给**开始页卡片**组件的运行时 props（官方 `sidebar.right.tab.guide.entry` 座位）。
 *
 * 字段依据官方 README：「按当前生效的定义 id 渲染…传入入口 id、解析后的标题、
 * 可选描述，以及框架提供的 `useTabInfo` hook」。
 */
export interface KsGuideCardProps {
  /** 解析后的入口标题（来自我们声明的 `guide[].title()`）。 */
  readonly title: string
  /** 解析后的说明；官方在条目多时会**不给**这个字段。 */
  readonly description?: string
  /** 贡献这张卡的类型判别符（官方会写进 `data-sidebar-right-guide-entry`）。 */
  readonly kind: string
  readonly useTabInfo: UseKsTabInfo
}

/** 框架转发给 **pane body** 组件的运行时 props（官方 `sidebar.right.pane.tab` 座位）。 */
export interface KsPaneBodyProps {
  readonly kind: string
  readonly useTabInfo: UseKsTabInfo
}

/**
 * 「知识库」页当前注入的面。
 *
 * ⚠ **2026-09-21 就地更正（第 3 步「界面骨架」；错话保留在下面）**：
 *   **曾如此（错的）**：「本轮**只有 UI**：`dataSource` 恒为 `'mock'`，页面数据是组件内的
 *   占位常量，没有任何 `/ks/*` 调用。」
 *   **实测**：`KsKnowledgePage` 现在**真的**通过 `client/api.ts` 调引擎的 `/api/v1/kb/*`
 *   （列某一级、列文件、上传落位），页面里**一个占位常量都没有**（`SEED_DOCS` 等已随批删除）。
 *   `dataSource` 因此从"数据来源的**声明**"退化成"这一次是谁挂的页面"的**诊断标签**
 *   （冒烟会传自己的名字）⇒ 类型从字面量 `'mock'` 放宽成 `string`，取值在 `entry.ts`。
 */
export interface KsKbInjected {
  /** 谁挂的这一页（真宿主是 `'engine'`，冒烟各传自己的名字）——只用于诊断展示，不参与取数。 */
  readonly dataSource: string
}
