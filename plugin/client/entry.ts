/**
 * ks-dsh-plugin — client/entry.ts (the client half's cordis entry)
 *
 * Exports the cordis contract `{ apply, inject }` for the browser half. The
 * DSH client module loader loads this bundle (served as /plugins/ks-dsh-plugin/client.js),
 * then cordis calls `apply(ctx)` with the injected services.
 *
 * ## 右侧栏：官方两段式（2026-09-16 迁移）
 * 原实现建立在第三方 `dsh-better-sidebar` 上（imperative registerTab/openTab/updateTab）。
 * 该包**已从 DSH profile 移除**，官方以 `@deepseek-ai/dsh-client-ui-sidebar-*` 取代，
 * 扩展模型换成 VS Code 式的「声明 tab 类型 + 注册 resolver」两段式 —— 详见
 * `ksSidebar.ts` 的文件头（含新旧字段映射表与设计取舍）。
 *
 * ⚠️ 迁移的**关键动机**是旧实现的失效模式：探针拿不到 `betterSidebar` 时只
 * `console.warn` 然后整块 return → 官方顶替后 **PDF 证据 tab 静默消失**，
 * 用户只看到"点证据链接没反应"。新实现拿不到官方面时**点名报错**并说明后果。
 *
 * 两个官方面（`ctx.sidebarRight` / `ctx.sidebarRightTabs`）刻意**不写进 `inject`**：
 * 硬门禁会让官方列一改名/未挂载就把整个 client half 停在 pending，连与它无关的
 * 「📜 查法规模式」也一起消失（见下方 `Ctx.get` 注释）。
 */

import { createElement } from 'react'

import { KsEvidenceHost, type KsEvidenceHostInjected } from './KsEvidenceHost'
import { KsKnowledgeGuide } from './KsKnowledgeGuide'
import { KsKnowledgePage } from './KsKnowledgePage'
import { KsScopeChip } from './KsScopeChip'
import { KsSettingsSection } from './KsSettingsSection'
import { KsTurnTab, type KsTurnInjected } from './KsTurnTab'

import {
  KS_EVIDENCE_ADDRESS,
  KS_EVIDENCE_IMPL_ID,
  KS_EVIDENCE_KIND,
  KS_KB_IMPL_ID,
  KS_TURN_IMPL_ID,
  ksEvidenceDefinition,
  ksKbDefinition,
  ksTurnDefinition,
  toNavParams,
  type KsKbInjected,
  type KsSidebarRight,
  type KsTabRegistry,
} from './ksSidebar'
import { isKsEvidenceUrl, parseEvidence } from './ksEvidence'
import { ksWarnCssText } from './KsAnchorWarn'

/** 从事件里取证据锚点的 href（无锚点 / 非证据地址 → null）。点击拦截的两个通道共用它。 */
function evidenceHrefOf(event: MouseEvent): string | null {
  const target = event.target
  if (target === null || typeof (target as Element).closest !== 'function') return null
  const anchor = (target as Element).closest('a[href]') as HTMLAnchorElement | null
  if (anchor === null) return null
  try {
    if (!isKsEvidenceUrl(new URL(anchor.href))) return null
  } catch { return null }
  return anchor.href
}

/**
 * 证据链接打不开时的**可见**提示（诊断 A3：原来只写 console —— 用户点了没反应是最坏的反馈）。
 * 宿主 Toast 是 React 件、这里在 React 外 ⇒ 先用最小 token 样式的临时条；
 * 批3 若有更合适的官方非 React 提示件再换（登记在 ui-audit-D 清单里）。
 */
function notifyEvidenceUnavailable(): void {
  try {
    const el = document.createElement('div')
    el.setAttribute('role', 'alert')
    el.textContent = '证据原文暂时打不开：PDF 查看器（右侧栏）没挂上。请稍后重试；'
      + '若一直如此，请检查 DSH 的侧栏插件是否启用。'
    // 样式 token 与 KsAnchorWarn **同一出处**（ksWarnCssText —— 复核 F0 打回后立的规矩：
    // 自带第二份样式曾引用两个不存在的主题变量、静默落字面兜底，正是 P2 禁的写法）。
    el.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:9999;max-width:320px;padding:8px 12px;'
      + 'border-radius:6px;font-size:12px;line-height:1.6;'
      + ksWarnCssText()
    ;(document.body ?? document.documentElement).appendChild(el)
    setTimeout(() => { el.remove() }, 8000)
  } catch { /* 提示本身失败不该再抛 */ }
}

/** 官方右侧栏导航面（`ctx.sidebarRight`）——由 `dsh-client-ui-sidebar-right` 提供。 */
type SidebarRightService = KsSidebarRight

interface Ctx {
  /** 注册随 fiber 撤销的副作用；cordis 的 ctx.effect 返回其 disposer。 */
  effect(fn: () => void | (() => void), label?: string): (() => void) | void
  /**
   * cordis 的"免 inject 读服务"：`ctx.get(name, strict=false)` 读不到时返回 undefined。
   *
   * 官方把这两个面用 `ctx.reflect.provide()` 注册（**不是** Cordis Service 类，
   * 见 `ui-sidebar-right/src/client/index.ts:108-109`），故它们**不进 Service 目录**，
   * 但 `ctx.get()` 能读到。刻意**不**写进 `inject`：inject 是硬门禁，官方列改名/
   * 未挂载会让整个 client half 停在 pending，连与它无关的「查法规模式」也一起消失。
   */
  get?(name: string, strict?: boolean): unknown
  /**
   * 订阅事件（门面白名单 verb 之一）。用 `internal/service` 做"官方面出现即再注册"，
   * 比定时轮询更贴 cordis 契约（服务 provide/撤销时真发该事件）。
   */
  on?(event: string, listener: (...args: unknown[]) => void): unknown
  /** The client slot registry, provided by @deepseek-ai/dsh-client-ui-slots. */
  slots?: {
    inject(key: string, callback: () => () => void): () => void
    register(options: Record<string, unknown>, component: unknown): () => void
  }
}

/**
 * Services this client plugin needs. 只 inject 真实依赖：`slots`（DSH 官方）。
 * 右侧栏两面（`sidebarRight` / `sidebarRightTabs`）是运行时探测 + 显式报错
 * ——见上方 `Ctx.get` 注释。
 */
export const inject = ['slots']

/** 「法规标准知识库」prefs namespace key（设置区的持久化 blob）。 */
export const KS_SETTINGS_TAB_ID = 'ks:settings'

/** Register the「法规标准知识库」settings SECTION — a top-level nav 栏目 in the
 *  DSH Settings shell, via the OFFICIAL `settings.section` slot
 *  (`@deepseek-ai/dsh-client-ui-settings`)。
 *
 *  ⚠ 2026-09-16 迁移：旧实现把 `betterSidebar` 服务作为 `{ service }` 注入，
 *  因为它要读写 better-sidebar 的共享 side-card prefs（`pluginSettings['ks:settings']`）
 *  并经其栅栏路由 `/sidebar/api/settings/update` 落库。该包已被官方
 *  `dsh-client-ui-sidebar-right` 取代、**且官方没有偏好存储面**，故偏好改由
 *  `./ksPrefs`（KS 自有、本地持久化、可订阅）承载 —— 设置区与服务组件的读写链路
 *  不再依赖任何第三方存储。
 *
 *  Returns the section disposer (no-op if the slot is unavailable, so a missing
 *  slot never breaks the tab registration). */
function registerKsSettingsSection(
  ctx: Ctx,
  openEvidence: (evidenceUrl: string) => void,
): () => void {
  const slots = ctx.slots
  if (slots === undefined) {
    console.warn('[ks-dsh-plugin] settings.section slot unavailable; 法规标准知识库 settings section not registered')
    return () => {}
  }
  try {
    return slots.inject('settings.section', () => slots.register({
      name: 'settings.section',
      id: 'ks-dsh-plugin',
      // 排在官方各栏目之后（官方 section 用 order 100 一带）。
      order: 101,
      label: () => '法规标准知识库',
      // 注入面：只有 KS 自有的证据导航端口（红箭头偏好走模块级 `./ksPrefs`）。
      inject: () => ({ openEvidence }),
    }, KsSettingsSection))
  } catch (error) {
    console.error('[ks-dsh-plugin] register settings.section failed', error)
    return () => {}
  }
}

/** User-facing tab title for an evidence anchor href (page only — no tech ids). */
function evidenceTitle(href: string): string {
  const ev = parseEvidence(href)
  return `PDF 查看器${ev?.page !== undefined ? ` · 第${ev.page}页` : ''}`
}


/**
 * Client entry. Registers the ks:pdf sidebar tab that renders evidence PDFs,
 * plus the ks:bookmarks tab that lists favorited evidence. Neither tab reads a
 * third party: they fetch the engine session via the SAME-ORIGIN /ks/session
 * route and then call the loopback engine directly, holding the bearer token
 * only in page memory.
 */
export function apply(ctx: Ctx): void {

  /**
   * 右侧栏可用时的"打开证据"实现；右侧栏未挂载/被撤销时为 null。
   *
   * 用**可变引用**是为了让设置栏目（在下方先注册）能在右侧栏迟到后自动拿到
   * 导航能力，而不必重新注册设置栏目。
   */
  const rightRef: { current: ((evidenceUrl: string) => void) | null } = { current: null }

  // 收藏夹范围提问胶囊（2026-10）：注册 conversation.input.dock（输入卡片
  // 上方全宽行）。夹内提问激活时显示「🔖 夹名 · 仅在本收藏夹内提问 ✕」。
  // 不依赖右侧栏——host 的 /ks/chat-mode 与输入框同属官方 shell。
  // slots 是本插件声明的 inject（见上方 export const inject），缺失时静默
  // 跳过（tab/其他表面照常）。
  try {
    const slots = ctx.slots
    if (slots !== undefined) {
      slots.inject('conversation.input.dock', () => slots.register({
        name: 'conversation.input.dock',
        id: 'ks-scope-chip',
        order: 10,
        inject: (sessionId: string) => ({ sessionId }),
      }, KsScopeChip))
    }
  } catch (error) {
    console.error('[ks-dsh-plugin] 注册收藏夹范围胶囊失败（不影响其他表面）', error)
  }

  // 「法规标准知识库」设置栏目：走官方 `settings.section`，**与官方右侧栏解耦**
  // —— 它只依赖 `ctx.slots`（我们声明的 inject），右侧栏缺席时它仍必须注册
  // （这是既有设计刻意保持的性质：右侧栏缺失不该连带弄丢设置面板）。
  //
  // `openEvidence` 经**可变引用**读取：右侧栏迟到时设置面板里的"点文档行跳 PDF"
  // 会在服务到位后自动生效，而无需重新注册设置栏目。
  try {
    const disposeSettingsEarly = registerKsSettingsSection(ctx, (url) => rightRef.current?.(url))
    if (typeof disposeSettingsEarly === 'function') {
      ctx.effect(() => disposeSettingsEarly, 'ks-dsh-plugin: 设置栏目')
    }
  } catch (error) {
    console.error('[ks-dsh-plugin] 注册设置栏目失败（不影响其他表面）', error)
  }

  // 证据锚点**兜底**接管（诊断 A3，2026-09-22）：正式拦截器随右侧栏注册——
  // 侧栏缺席/被撤销时证据链接**没人拦**，默认导航落到不可达伪源（127.0.0.1:1）死页。
  // 这里常驻一个兜底：右侧栏在场（rightRef 非空）就让路给正式接管者；不在场则
  // 拦下默认导航 + 给**可见**提示（不许只写 console）。
  const onEvidenceFallback = (event: MouseEvent): void => {
    if (rightRef.current !== null) return
    const href = evidenceHrefOf(event)
    if (href === null) return
    event.preventDefault()
    notifyEvidenceUnavailable()
  }
  document.addEventListener('click', onEvidenceFallback, true)
  document.addEventListener('auxclick', onEvidenceFallback, true)
  ctx.effect(() => () => {
    document.removeEventListener('click', onEvidenceFallback, true)
    document.removeEventListener('auxclick', onEvidenceFallback, true)
  }, 'ks-dsh-plugin: 证据锚点兜底')

  // ── 右侧栏：官方两段式注册（2026-09-16 迁移）──────────────────────────────
  //
  // 官方模型（`@deepseek-ai/dsh-client-ui-sidebar-right`，VS Code 式）：
  //   ① `ctx.sidebarRightTabs.register(def)` —— 声明 tab 类型（kind / 地址 / 标题）；
  //   ② `ctx.slots.register({name:'sidebar.right.pane.tab', key: def.id}, Body)`
  //      —— 注册 body；打开用 `ctx.sidebarRight.openResource(address, {kind, params})`。
  //
  // ⚠️ 这两个面由官方包用 `ctx.reflect.provide()` 注册（**不是** Cordis Service 类，
  // 见 ui-sidebar-right/src/client/index.ts:108-109），故 Service 目录里看不到它们，
  // 但 `ctx.get()` 能读到（guard.ts 白名单允许 `ctx.get`）。**刻意不写进 `inject`**：
  // 硬门禁会让官方列一改名/未挂载就把整个 client half 停在 pending，连与它无关的
  // 「📜 查法规模式」也一起消失（旧实现的教训，见下方 readService 注释）。
  //
  // 与旧实现的差异（**静默失效 → 显式报错**）：旧探针拿不到服务时只 console.warn
  // 然后整块跳过 —— 结果官方顶替后 tab 面静默消失，用户只看到"PDF 打不开"。
  // 现在：拿不到就在控制台**点名报错**并说明后果；同时**事件驱动重试**
  // （官方 provide/撤销时会 emit `internal/service`），服务迟到也能补注册。
  let registered = false
  let disposed = false
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let surfacesDispose: (() => void) | undefined
  const RETRY_INTERVAL_MS = 200
  const RETRY_MAX_ATTEMPTS = 15
  let attempts = 0

  const registerSurfaces = (): void => {
    if (registered || disposed) return
    const tabs = readService<KsTabRegistry>(ctx, 'sidebarRightTabs')
    const right = readService<SidebarRightService>(ctx, 'sidebarRight')
    if (tabs === undefined || right === undefined) {
      attempts += 1
      if (attempts < RETRY_MAX_ATTEMPTS) {
        retryTimer = setTimeout(registerSurfaces, RETRY_INTERVAL_MS)
        return
      }
      console.error(
        '[ks-dsh-plugin] 未检测到官方右侧栏（ctx.sidebarRight / sidebarRightTabs）'
        + '：PDF 证据查看器与「点证据链接跳页」将不可用。'
        + '该面由 @deepseek-ai/dsh-client-ui-sidebar-right 提供——'
        + '若它未随 DSH 一起挂载，请检查 DSH 版本或插件清单。'
        + '（「📜 查法规模式」与全部 host 侧模型工具不受影响。）',
      )
      return
    }
    registered = true
    if (retryTimer !== undefined) { clearTimeout(retryTimer); retryTimer = undefined }
    surfacesDispose = registerSidebarSurfaces(ctx, tabs, right, rightRef)
  }

  ctx.effect(() => {
    // 事件驱动：服务被撤销（官方列热重载）→ 撤销旧表面并等它重生时重注册。
    // 旧实现曾因"置位后永不回退"导致服务重生后 tab 再也不出现（verifier 五轮 P2-4）。
    const off = ctx.on?.('internal/service', (name: unknown, value?: unknown) => {
      if (name !== 'sidebarRight' && name !== 'sidebarRightTabs') return
      if (value === undefined) {
        if (disposed) return
        registered = false
        if (surfacesDispose !== undefined) {
          try { surfacesDispose() } catch { /* effect 可能已随 fiber 撤销 */ }
          surfacesDispose = undefined
        }
        attempts = 0
        return
      }
      registerSurfaces()
    })
    return () => {
      disposed = true
      void off
      if (retryTimer !== undefined) { clearTimeout(retryTimer); retryTimer = undefined }
    }
  }, 'ks-dsh-plugin: 官方右侧栏探针')

  registerSurfaces()
}

/** 免注入读一个服务；门面缺失/抛错一律当"没有"，绝不让它带崩 apply。 */
function readService<T>(ctx: Ctx, name: string): T | undefined {
  try {
    if (typeof ctx.get !== 'function') return undefined
    const value = ctx.get(name)
    return value === null || value === undefined ? undefined : value as T
  } catch {
    return undefined
  }
}

/** 官方右侧栏存在时才注册的表面（2026-09-16 迁移后的**两段式**）：
 *  ① tab 类型声明 → `ctx.sidebarRightTabs.register(...)`；
 *  ② body 座位注册 → `slots.register({name:'sidebar.right.pane.tab', key: id})`。
 *
 *  设置栏目**不在这里**——它走官方 `settings.section`、与右侧栏解耦，在 `apply`
 *  顶层就先注册（右侧栏缺席时它仍须工作）。
 *  （🔖 收藏目录已迁入 PDF 查看器左列第三种模式，不再是侧栏 tab——2026-10-27。） */
function registerSidebarSurfaces(
  ctx: Ctx,
  tabs: KsTabRegistry,
  right: SidebarRightService,
  rightRef: { current: ((evidenceUrl: string) => void) | null },
): (() => void) | undefined {
  /** 打开（或复用）单例证据 tab。
   *
   * 官方语义：地址恒定 → 同一 tab；每次导航把 `navigation.revision` +1
   * （`tab-domain.ts` 的 `navigate()`），组件据此重载 —— 等价于旧模型用
   * `updateTab({meta:{ksClick}})` 做的"同 URL 也要重载"。故这里**只需一次调用**，
   * 不再需要旧实现那套"openTab 建/聚焦 + updateTab 覆写 path"两步。 */
  const openEvidence = (evidenceUrl: string): void => {
    right.openResource(KS_EVIDENCE_ADDRESS, {
      kind: KS_EVIDENCE_KIND,
      params: toNavParams(evidenceUrl),
    })
  }
  // 供**先于本函数注册**的设置栏目调用（见 apply 里 rightRef 的注释）。
  rightRef.current = openEvidence

  const disposer = ctx.effect(
    () => {
      // ① 类型声明。`register` 抛错即接线错误（同 id/同 kind 重复注册），
      //    让它冒到下面的 catch 里点名，而不是静默少一个 tab。
      const disposeType = tabs.register(ksEvidenceDefinition())
      // ①b 「知识库」类型（2026-09-19）：开始页那张卡的落点，按 params.page 分发四个二级页。
      //     与证据类型**分开注册**的理由见 ksSidebar.ts 的 KS_KB_* 段注释。
      const disposeKbType = tabs.register(ksKbDefinition())
      // ①c 「本轮」类型（S1-a，2026-09-22）：右栏拆「本轮证据」+「知识库」（业主批准）。
      const disposeTurnType = tabs.register(ksTurnDefinition())

      // ② body 座位。**两个面必须分清**（2026-09-17 修空白 pane 的根因）：
      //    - `hookContext: TabHookContext`（座位契约）⇒ 框架把 `useTabInfo` **作为
      //      组件运行时 prop** 交给 body —— 我们**不需要**、也**拿不到**它；
      //    - `inject` 工厂的**第一个参数是 `sessionId`**，其**返回值**才是本插件贡献
      //      给组件的面（官方 `ui-sidebar-documentpreview/src/client/index.ts:104`
      //      写作 `inject: (sessionId, actions) => …`）。
      //    旧实现把第一参数当"聚合面"并断言 `hooks.tabInfo` —— 那值永远是 undefined，
      //    自设守卫于是挂载即抛 → 官方 `slot entry crashed` → **点进来全白**（真机实测）。
      let disposeBody: (() => void) | undefined
      let disposeKbBody: (() => void) | undefined
      let disposeTurnBody: (() => void) | undefined
      let disposeGuideCard: (() => void) | undefined
      if (ctx.slots !== undefined) {
        disposeBody = ctx.slots.inject('sidebar.right.pane.tab', () => ctx.slots!.register({
          name: 'sidebar.right.pane.tab',
          key: KS_EVIDENCE_IMPL_ID,
          // 只贡献我们自己的那一个面；`useTabInfo` 由框架按 hookContext 给。
          inject: (): KsEvidenceHostInjected => ({ openEvidence }),
        }, KsEvidenceHost))

        // ②b 「知识库」pane body。**2026-09-21（第 3 步）起它自己调引擎**：
        //     页面通过 `client/api.ts` 走 `/api/v1/kb/*`（列某一级 / 列文件 / 上传落位），
        //     注入面只剩一个**诊断标签** `dataSource`（谁是这一页的挂载者），不参与取数。
        //     `useTabInfo` 由框架按 hookContext 给（不在这里注入）。
        disposeKbBody = ctx.slots.inject('sidebar.right.pane.tab', () => ctx.slots!.register({
          name: 'sidebar.right.pane.tab',
          key: KS_KB_IMPL_ID,
          inject: (): KsKbInjected => ({ dataSource: 'engine' }),
        }, KsKnowledgePage))

        // ②c 「本轮」pane body（S1-a 注册；S1-b 取数+依据行）。
        //     sessionId 供取数（GET /ks/turn/last?session=…）；openEvidence = 既有跳页链路。
        disposeTurnBody = ctx.slots.inject('sidebar.right.pane.tab', () => ctx.slots!.register({
          name: 'sidebar.right.pane.tab',
          key: KS_TURN_IMPL_ID,
          inject: (sessionId: string): KsTurnInjected => ({
            sessionId, dataSource: 'host-stash', openEvidence,
          }),
        }, KsTurnTab))

        // ②c 开始页那张卡（「知识库」+ ▾ 二级目录）。
        //     官方 README：'开始页按当前生效的**定义 id** 渲染 sidebar.right.tab.guide.entry…
        //     provider 可按自己的定义 id 注册自定义卡片'。故 key 用**定义 id**（不是 kind）——
        //     与宿主 ui-sidebar-terminal/src/client/index.ts:62 的 `key: id` 同法。
        disposeGuideCard = ctx.slots.inject('sidebar.right.tab.guide.entry', () => ctx.slots!.register({
          name: 'sidebar.right.tab.guide.entry',
          key: KS_EVIDENCE_IMPL_ID,
        }, KsKnowledgeGuide))
      } else {
        console.error('[ks-dsh-plugin] slots 不可用：PDF 证据 tab body 未注册（tab 类型已注册但无内容）')
      }

      // ⚠ 已删除"目录常驻"的**自动开 tab**（2026-09-17）。原实现（2026-10-27）在
      //   `apply()` 里直接 `right.openResource(...)`，但那一刻**会话面还没挂载**，
      //   真机每次都抛 `sidebarRight: no session surface is mounted` 并留一条
      //   console.warn —— 也就是**它从来没有生效过**（只是每次加载吵一句）。
      //   而它的用途（"无证据也能进 PDF 阅读器"）现在由**侧栏开始页的手动入口胶囊**
      //   承担（见 `ksSidebar.ts` 的 `guide`）：胶囊是"门"，用户点才进；自动开反而会
      //   把开始页顶掉，与"开始页＝入口"的设计相冲突。
      //   若将来确实要"开局常驻 tab"，正确位置是**会话面挂载后的回调**，而不是这里。

      // 证据锚点接管：官方模型没有 `urlTarget` 那种"声明式认领外部链接"的面，
      // 故仍用 document 级 capture 监听——但它现在只做**一件事**：
      // 命中证据锚点 → 转成官方 `openResource`。不再需要"覆写单例 path"的收尾
      // （导航 revision 已保证重载），因此比旧实现短且无竞态假设。
      const onClick = (event: MouseEvent): void => {
        // 诊断 A3（2026-09-22）：**任何**点击形态（Ctrl/Shift/Alt/中键）都拦 ——
        // 修饰键的"新标签打开"对我们没有意义：伪源地址不可达，落给浏览器就是死页。
        // 一律转进侧栏；中键在现代浏览器走 auxclick，两个通道都接。
        const href = evidenceHrefOf(event)
        if (href === null) return
        // 合法证据锚点：拦掉默认导航（伪源 host 不可达），交给右侧栏打开。
        event.preventDefault()
        openEvidence(href)
      }
      document.addEventListener('click', onClick, true)
      document.addEventListener('auxclick', onClick, true)

      return () => {
        document.removeEventListener('click', onClick, true)
        document.removeEventListener('auxclick', onClick, true)
        // 撤销"打开证据"能力：设置栏目仍在（它不随右侧栏撤销），故必须清掉引用，
        // 否则它会调到一个已失效的 right（旧实现同类问题的教训）。
        rightRef.current = null
        disposeGuideCard?.()
        disposeTurnBody?.()
        disposeKbBody?.()
        disposeBody?.()
        disposeTurnType()
        disposeKbType()
        disposeType()
      }
    },
    'ks-dsh-plugin: 官方右侧栏证据 tab',
  )
  return typeof disposer === 'function' ? disposer : undefined
}

/*
 * ⚠ **这里刻意没有 default 导出** —— 别再加回来。
 *
 * 本模块是官方所说的 *namespace plugin*：apply / inject（以及 name）是**并列的命名导出**。
 * 官方事故复盘 `docs/postmortem/0001-acp-default-export-drops-inject.md` 的根因 #1 就是
 * 一个多余的 `export default apply`：
 *
 *   unwrapExports(exports) { exports = exports.default ?? exports; … }
 *
 * cordis 的 Loader 逐个模块调 unwrapExports，**优先取 .default**；一旦有 default，
 * 它就**把整个模块命名空间丢掉** ⇒ inject / name / Config 全部消失，插件在不含任何
 * 注入服务的 fiber 里跑，第一行 ctx.xxx 就抛 "cannot get property … without inject"。
 * 症状极具迷惑性：**单元测试全绿**（它们绕过真实 Loader），真机上第一个请求就崩。
 *
 * 我们的历史版本写的是「默认导出 = { apply, inject }」—— 那个对象恰好把 inject 一起带了进去，
 * 所以当时没炸；但它仍然**丢掉了命名空间**（name、以及将来任何其它命名导出），
 * 只是把事故推迟到"哪天有人往里加一个命名导出"而已。官方的修法就是**删掉那一行**。
 * 冒烟里有一条断言钉住它（`entry.ts 没有 export default`），加回来会直接红。
 */
