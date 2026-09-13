/**
 * ks-dsh-plugin — client/entry.ts (the client half's cordis entry)
 *
 * Exports the cordis contract `{ apply, inject }` for the browser half. The
 * DSH client module loader loads this bundle (served as /plugins/ks-dsh-plugin/client.js),
 * then cordis calls `apply(ctx)` with the injected services.
 *
 * The better-sidebar service (a THIRD-PARTY plugin) is read at runtime through
 * `ctx.get('betterSidebar')` and is deliberately NOT in `inject` — an inject
 * hard-gate would let a rename/uninstall of that plugin silently kill this whole
 * client half, including features that don't use it (📜 查法规模式).
 * NOTE: `package.json dsh.client.inject` is **informational only** (preflight / HMR
 * diffing, per DSH packages/client/AGENTS.md) — it neither gates nor orders
 * activation, so tab registration additionally polls for the service to appear.
 *
 * 2026-09-05 修复：better-sidebar 内置链接拦截只把 URL 写入"新建"tab 的 path
 * （service.ts openTab：a FOCUS must never have its path overwritten）。本 tab
 * 声明 single:true → 同类型再次点击 = FOCUS 已有单例，新 URL 永不应用 = 点
 * 第二/第三个证据链接无反应。故这里自装 document 级 capture click listener：
 * 命中证据锚点 → preventDefault + openTab（建/聚焦）+ updateTab 强制覆写单例
 * path → KsEvidenceTab 的 [tab.path] effect 侦测变化 → 重新 loadEvidence 跳页。
 */

import { createElement } from 'react'
import type { TabDescriptor } from 'dsh-better-sidebar/client/service'

import { KsEvidenceTab } from './KsEvidenceTab'
import { KsBookmarksTab, KS_BOOKMARKS_TAB_ID } from './KsBookmarksTab'
import { KsSettingsSection } from './KsSettingsSection'

import { reportBetterSidebarCompat } from './bsContract'
import {
  isKsEvidenceUrl,
  KS_EVIDENCE_TAB_ID,
  nextEvidenceClick,
  parseEvidence,
} from './ksEvidence'

/** Minimal structural `Context` mirror (no hard dep on the client runtime). */
interface BetterSidebar {
  registerTab(descriptor: TabDescriptor): () => void
  openTab(seed: { type: string; url?: string; title?: string }): void
  /** Patch an open tab's display fields (a missing tab id is a no-op). */
  updateTab?(tabId: string, patch: { title?: string; path?: string; meta?: Record<string, unknown> }): void
}

interface Ctx {
  /** 注册随 fiber 撤销的副作用；cordis 的 ctx.effect 返回其 disposer。 */
  effect(fn: () => void | (() => void), label?: string): (() => void) | void
  /**
   * cordis 的"免 inject 读服务"：`ctx.get(name, strict=false)` 读不到时返回 undefined
   * 而不是抛错（`ctx.betterSidebar` 在**未 inject** 时会抛
   * `cannot get property "betterSidebar" without inject`）。
   * 本插件刻意**不** inject betterSidebar——否则第三方插件一改名/被卸载，cordis 会让
   * 本 entry 停在 pending，`apply()` 根本不执行，连与它无关的「查法规模式」开关都会
   * 一起消失（verifier 二轮 P1）。
   */
  get?(name: string, strict?: boolean): unknown
  /**
   * 订阅事件（门面白名单 verb 之一）。用 `internal/service` 做"服务出现即再探"，
   * 比定时轮询更贴 cordis 契约（cordis 4.0.2 在 provide/撤销时真发该事件）。
   */
  on?(event: string, listener: (...args: unknown[]) => void): unknown
  /** The client slot registry, provided by @deepseek-ai/dsh-client-ui-slots. */
  slots?: {
    inject(key: string, callback: () => () => void): () => void
    register(options: Record<string, unknown>, component: unknown): () => void
  }
}

/**
 * Services this client plugin needs. 只 inject 真实依赖：`slots`（DSH 官方）——
 * better-sidebar 是第三方，改成运行时探测 + 逐项降级（见上方 Ctx.get 注释）。
 */
export const inject = ['slots']

/** 「法规标准知识库」prefs namespace key (the plugin's settings blob in the
 *  shared Side card prefs doc). KsEvidenceTab and KsSettingsSection both use
 *  `pluginSettings['ks:settings']`. */
export const KS_SETTINGS_TAB_ID = 'ks:settings'

/** hidden 占位 tab 的 component（永不打开，仅供 registerTab 契约占位；真正的
 *  设置表面是 KsSettingsSection 的 settings.section 与这张卡的 pluginToggles）。 */
function KsSettingsPlaceholder(): JSX.Element {
  return createElement('div', { style: { display: 'none' } })
}

/** Register the「法规标准知识库」settings SECTION — a top-level nav 栏目 in the
 *  DSH Settings shell (the same `settings.section` mechanism dsh-better-sidebar
 *  uses for its own「侧边卡片」nav, see its client/index.tsx:430).
 *
 *  A `TabDescriptor` card (even `hidden: true`) can only ever appear as a
 *  FEATURE card in the「侧边栏内容」grid and cannot produce a distinct 栏目 —
 *  which is why the previous hidden-tab placeholder never read as the section
 *  the user asked for. Returns the section disposer (no-op if slots are
 *  unavailable, so a missing slot never breaks the tab registration). */
function registerKsSettingsSection(ctx: Ctx, bs: BetterSidebar): () => void {
  const slots = ctx.slots
  if (slots === undefined) {
    console.warn('[ks-dsh-plugin] settings.section slot unavailable; 法规标准知识库 settings section not registered')
    return () => {}
  }
  try {
    return slots.inject('settings.section', () => slots.register({
      name: 'settings.section',
      id: 'ks-dsh-plugin',
      // After dsh-better-sidebar's own section (order 100) so the newly-added
      // 栏目 slots in after「侧边卡片」.
      order: 101,
      label: () => '法规标准知识库',
      inject: () => ({ service: bs }),
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

  // 契约体检（2026-09-09）：better-sidebar 是第三方插件，升级可能改名/删方法。
  // 启动时探一次能力面：缺必需能力 → console.error 点名；缺可选能力或版本漂移
  // → console.warn 说明降级面。见 bsContract.ts（配套 `npm run smoke:bs-contract`
  // 会对已安装版本的类型声明做同源断言）。
  //
  // ⚠️ 这里只能用**门面允许的原语**。DSH 的客户端半拿到的不是内核 ctx，而是
  // cordis-client-runner 的受限门面（packages/extensions/cordis-client-runner/src/client/guard.ts）：
  //   - 白名单 verb 只有 effect/on/once/provide/timeout/interval/setTimeout/setInterval/
  //     throttle/debounce（`CTX_VERBS`，guard.ts:21-24）；
  //   - 非白名单属性走 denyRead → **直接抛错**（`dynamic ctx does not expose "..."`）。
  //     所以既不能读 `ctx.betterSidebar`（未声明 → 抛），也**不能读 `ctx.inject`**
  //     （不在白名单 → `typeof ctx.inject` 本身就抛）。verifier 三轮实测：踩这一条会让
  //     整个客户端半（四个 tab + 设置栏目 + 📜 查法规模式）全部不激活；
  //   - `ctx.get(name)` 是**允许**的（guard.ts:214 `readService(name, false)`，不要求声明），
  //     读不到就是 undefined。
  // 因此 better-sidebar 既不做注入门禁（那会让第三方插件一改名就整块消失），也不做
  // "等服务"（门面没有该原语、`ctx.inject` 会抛），而是**事件驱动 + 兜底轮询**：
  // cordis 提供服务时会 emit `internal/service`（`ctx.on` 在白名单里，cordis 4.0.2
  // lib/index.js:848 真发），兜底轮询只覆盖"提供早于我们 apply"这一种情况。
  // 探针随 fiber dispose 自行清理（标志位 + 句柄），绝不在 dispose 之后往失效 fiber 上
  // 注册（cordis 的 `ctx.effect` 会抛 INACTIVE_EFFECT，而那异常发生在定时器回调里）。
  let tabsRegistered = false
  let probeAttempts = 0
  let probeDisposed = false
  let probeTimer: ReturnType<typeof setTimeout> | undefined
  /** tab/设置栏目那次 effect 的 disposer（服务被撤销时要先撤掉再重注册）。 */
  let surfacesDispose: (() => void) | undefined
  const PROBE_INTERVAL_MS = 200
  const PROBE_MAX_ATTEMPTS = 15
  const probeBetterSidebar = (): void => {
    if (tabsRegistered || probeDisposed) return
    const bs = readService<BetterSidebar>(ctx, 'betterSidebar')
    if (bs === undefined) {
      probeAttempts += 1
      if (probeAttempts < PROBE_MAX_ATTEMPTS) {
        probeTimer = setTimeout(probeBetterSidebar, PROBE_INTERVAL_MS)
        return
      }
      console.warn(
        '[ks-dsh-plugin] 未检测到 better-sidebar：跳过 tab / 设置栏目注册'
        + '（📜 查法规模式与全部 host 功能照常工作；第三方插件稍后激活时刷新页面即可）',
      )
      return
    }
    const compat = reportBetterSidebarCompat(bs)
    if (!compat.ok) {
      console.error(
        '[ks-dsh-plugin] better-sidebar 契约不满足，跳过全部 tab 注册'
        + '（📜 查法规模式等不依赖它的功能照常工作）',
      )
      return
    }
    tabsRegistered = true
    if (probeTimer !== undefined) {
      clearTimeout(probeTimer)
      probeTimer = undefined
    }
    surfacesDispose = registerBetterSidebarSurfaces(ctx, bs)
  }
  ctx.effect(() => {
    ctx.on?.('internal/service', (name: unknown, value?: unknown) => {
      if (name !== 'betterSidebar') return
      // 服务被**撤销**（better-sidebar 卸载/热重载）→ 复位，等它再出现时重新注册；
      // 旧 surfaces 的 effect 先撤掉，避免点击监听器被叠加两次（verifier 五轮 P2-4：
      // 旧实现 `tabsRegistered` 一旦置位永不回退，服务重生后 tab 再也不出现）。
      if (value === undefined) {
        if (probeDisposed) return
        tabsRegistered = false
        // 没拿到 disposer 就不敢复位（否则旧 tab 未注销时会重复 registerTab 同 id）——
        // verifier 六轮 P2-5
        if (surfacesDispose !== undefined) {
          try { surfacesDispose() } catch { /* effect 可能已随 fiber 撤销 */ }
          surfacesDispose = undefined
        }
        probeAttempts = 0 // 复位探针预算，否则第二次探针一次都不轮询就放弃
        return
      }
      probeBetterSidebar()
    })
    return () => {
      probeDisposed = true
      if (probeTimer !== undefined) {
        clearTimeout(probeTimer)
        probeTimer = undefined
      }
    }
  }, 'ks-dsh-plugin: better-sidebar 探针')
  probeBetterSidebar()
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

/** better-sidebar 存在时才注册的表面：2 个 tab（证据 PDF / 收藏）+ 设置栏目（含
 *  效力报告与入库预览两个内嵌折叠面板，2026-11 迁入）+ 证据链接接管。 */
function registerBetterSidebarSurfaces(ctx: Ctx, bs: BetterSidebar): (() => void) | undefined {
  const disposer = ctx.effect(
    () => {
      const disposePdf = bs.registerTab({
        id: KS_EVIDENCE_TAB_ID,
        title: 'PDF 查看器',
        single: true,
        // 不设 icon：tab 标题即说明（用户反馈：勿再叠书本小图/重复符号）
        // Claim the pseudo-evidence link so better-sidebar opens a ks:pdf tab
        // (not its built-in browser) when the user clicks it.
        urlTarget: (url: URL) => isKsEvidenceUrl(url),
        component: (props) => createElement(KsEvidenceTab, props),
      })

      // 增强③-A: 收藏 tab（列出引擎收藏的条款，可跳转/删除）。图标 🔖 即语义，
      // 标题不带重复 emoji。（2026-11 效力报告/入库预览迁入设置栏目后，侧栏
      // tab 只剩证据 PDF 与收藏——收藏依用户指示原样保留不动。）
      const disposeBookmarks = bs.registerTab({
        id: KS_BOOKMARKS_TAB_ID,
        title: '收藏',
        single: true,
        icon: (size: number) => createElement('span', { style: { fontSize: size } }, '🔖'),
        component: (props) => createElement(KsBookmarksTab, props),
      })

      // 效力报告 / 入库预览（2026-11 迁移）：不再注册为侧栏 tab——用户拍板
      // 「全部放进设置的菜单里，类目全折叠」。两面板现在由 KsSettingsSection
      // 的同名 <details> 类目承载（懒加载：收起零请求，展开才拉数据）。
      // 引擎路由 /ks/report/*、/ks/ingest/* 与设置入口不变。

      // 「法规标准知识库」设置栏目的两处表面：
      //  (A) 顶层 `settings.section` —— 在 DSH 设置壳左侧新增一个名为「法规标准知识库」
      //      的独立 nav 栏目（用户真正要的「栏目」），showArrow 开关由 KsSettingsSection
      //      内联、可见地渲染。这是本修复的核心。
      //  (B) 一个 hidden tab 卡（保持原样）+ pluginToggles —— 它不算「栏目」，但它经由
      //      better-sidebar 的卡片→弹层写入路径调用 store.setPrefs，是一条存储一致
      //      且即时反应（KsEvidenceTab 的 useSyncExternalStore 订阅）的兜底写入通道。
      //      与 (A) 读写同一 key `pluginSettings['ks:settings']`，两者保持一致。
      const disposeSettingsCard = bs.registerTab({
        id: KS_SETTINGS_TAB_ID,
        title: '法规标准知识库',
        single: true,
        hidden: true,
        icon: (size: number) => createElement('span', { style: { fontSize: size } }, '⚖️'),
        component: () => KsSettingsPlaceholder(),
        settings: {
          pluginToggles: [
            {
              key: 'showArrow',
              title: '显示红色定位箭头',
              desc: '在 PDF 证据页用红箭头标出引用条款位置；关闭后仅跳页。',
            },
          ],
        },
      })
      // (C) 顶层 section 独立注册，见上方注释 (A)。
      const disposeSettings = registerKsSettingsSection(ctx, bs)
      // (D) 「📜 查法规模式 / 🔖 仅收藏」不再有输入框 UI：2026-10 按用户反馈删掉 dock，
      //     改由 host 的斜杠命令 /forensic、/bookmarks 调用（见 src/chatmode.js）。

      // 自足接管：single:true 单例的再次 openTab 只是 focus（URL 不应用），
      // 必须自己覆写 path 才能连续跳多个证据。capture 阶段先于内置拦截?
      // 否——本 listener 注册于 apply()，晚于 better-sidebar 的 document 级
      // capture，故以 bubble 收尾仍可能撞 defaultPrevented；这里不依赖先后：
      // 命中证据锚点即 preventDefault 并 openTab+updateTab，行为幂等。
      const onClick = (event: MouseEvent): void => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        const target = event.target
        if (target === null || typeof (target as Element).closest !== 'function') return
        const anchor = (target as Element).closest('a[href]') as HTMLAnchorElement | null
        if (anchor === null) return
        const href = anchor.href
        if (!isKsEvidenceUrl(new URL(href))) return
        // 无论 better-sidebar 内置拦截是否已接管（其 capture 更早，可能已
        // preventDefault + openTab focus），ks 链接一律归我们收尾：
        //   - 首次：openTab 建 tab（URL 写入 path）；
        //   - 再次：openTab 只 focus（single 单例不写 path）→ updateTab
        //     强制覆写 path → KsEvidenceTab 的 [tab.path] effect 触发重载跳页。
        // preventDefault 幂等；updateTab 对缺失 tab 是 no-op，无需先查。
        event.preventDefault()
        const title = evidenceTitle(href)
        bs.openTab({ type: KS_EVIDENCE_TAB_ID, url: href, title })
        try {
          // meta 带共享单调 nonce：即便 path 与上次相同（用户反复点同一条证据 /
          // 翻页后再点同一条），tab.meta 引用也变化 → KsEvidenceTab 的
          // [tab.path, tab.meta] effect 必然触发重载（否则 updateTab 同值
          // path 不产生状态变化，点多少次都不跳——实测回归）。
          bs.updateTab?.(KS_EVIDENCE_TAB_ID, {
            path: href,
            title,
            meta: { ksClick: nextEvidenceClick() },
          })
        } catch { /* updateTab 为可选 API；失败时首次 openTab 已能工作 */ }
      }
      document.addEventListener('click', onClick, true)

      return () => {
        document.removeEventListener('click', onClick, true)
        disposePdf()
        disposeBookmarks()
        disposeSettingsCard()
        disposeSettings()
      }
    },
    'ks-dsh-plugin: ks:pdf evidencetab + ks:bookmarks + ks:settings section + card',
  )
  return typeof disposer === 'function' ? disposer : undefined
}

export default { apply, inject }
