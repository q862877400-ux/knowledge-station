/**
 * ks-dsh-plugin — client/dsh-better-sidebar.d.ts
 *
 * LOCAL ambient declaration for the third-party `dsh-better-sidebar` package
 * (the surface our client half imports: `TabDescriptor`, `TabComponentProps`).
 *
 * Why a local .d.ts instead of a dependency:
 *   - The plugin's client half runs INSIDE the DSH host, which provides
 *     `dsh-better-sidebar` at runtime from the host's own node_modules
 *     (e.g. ~/.dsh/profiles/web/node_modules/dsh-better-sidebar). Our repo
 *     must NOT list it as a dependency — it is a HOST-provided runtime
 *     surface, and installing a second copy would misstate which code
 *     actually executes.
 *   - Before 批 8（Electron 退役）the root package.json carried a large legacy
 *     dependency tree whose transitive deps incidentally made this module
 *     resolvable; that tree is now gone (root keeps only the plugin
 *     toolchain: react types, typescript, esbuild), so this file restores
 *     type resolution without reintroducing the dead tree.
 *
 * Fidelity discipline (pairs with the contract smoke scripts/smoke-bs-contract.mjs):
 *   - The shapes below are transcribed from the REAL installed upstream
 *     v0.18.0 (lib/types/client/{service,state,api}.d.ts + context-types.d.ts),
 *     the version pinned as BS_TESTED_VERSION in ./bsContract.ts.
 *   - Keep it MINIMAL: only the imported surface plus the skeleton types it
 *     references. Fields we never touch are omitted — the authoritative
 *     declaration is upstream's own d.ts, and the contract smoke asserts
 *     against the REAL installed package, so upstream drift is caught there.
 *   - When upstream ships a new version: bump BS_TESTED_VERSION and run the
 *     contract smoke; update this file only if the imported surface changed.
 */

declare module 'dsh-better-sidebar/client/service' {
  import type { ReactNode } from 'react'

  /** Upstream lib/types/client/state.d.ts — fields we read. */
  interface SidebarTab {
    id: string
    type: string
    title: string
    path?: string
    /** Plugin-owned state (v0.12.0+): JSON-serializable, persisted with layout. */
    meta?: unknown
  }

  /** Upstream lib/types/client/api.d.ts — session scope of one openTab request. */
  interface SessionScope {
    sessionId: string
    cwd?: string
    repoRoot?: string
  }

  /** Upstream lib/types/context-types.d.ts — the host cordis Context, carrying
   *  the `betterSidebar` service member (upstream declares it via
   *  `declare module '@deepseek-ai/cordis'` interface augmentation — non-
   *  optional, because the tab components only mount once the service that
   *  registered them exists). Opaque beyond what we touch. */
  interface Context {
    betterSidebar: BetterSidebarService
    [key: string]: unknown
  }

  /** Upstream lib/types/client/service.d.ts — the registry service published
   *  as `ctx.betterSidebar`. Only the members our client half calls. */
  interface BetterSidebarService {
    registerTab(descriptor: TabDescriptor): () => void
    openTab(seed: { type: string; url?: string; title?: string }): void
    /** Patch an open tab's display fields (a missing tab id is a no-op). */
    updateTab?(tabId: string, patch: { title?: string; path?: string; meta?: unknown }): void
    /** The plugin version this service instance was built from. */
    readonly version: string
    /** Monotonic capability list ('tabMeta' | 'updateTab' | …). */
    readonly features: readonly string[]
  }

  /** Upstream lib/types/client/state.d.ts — SidebarSnapshot, the fields we read
   *  (prefs.pluginSettings for the showArrow setting; state.width for the
   *  panel-width-following TOC column). */
  interface SidebarSnapshot {
    sessionId: string | undefined
    state: { panelOpen: boolean; width: number; [key: string]: unknown } | undefined
    prefs: { pluginSettings: Record<string, Record<string, unknown>>; [key: string]: unknown }
  }

  /** Upstream lib/types/client/state.d.ts — the per-session store handed to
   *  tab components. Only the members our client half calls. */
  interface SidebarStore {
    subscribe(listener: () => void): () => void
    getSnapshot(): SidebarSnapshot
    /** Whether a tab still exists in its session's state (unmount triage). */
    tabOpen(sessionId: string, tabId: string): boolean
    [key: string]: unknown
  }

  /** Upstream sidebar state vocabulary (only what our descriptors touch). */
  interface SidebarState {
    [key: string]: unknown
  }

  /** Props every tab component receives (upstream TabComponentProps, verbatim fields). */
  interface TabComponentProps {
    ctx: Context
    store: SidebarStore
    scope: SessionScope
    tab: SidebarTab
    /** Whether this tab is the active one AND the panel is open (live views pause otherwise). */
    visible: boolean
    /** The explorer's expanded directory set (ExplorerView). */
    expanded?: string[]
    /** The explorer's reveal-highlight set (ExplorerView). */
    revealed?: string[]
    onToggleDir?: (path: string) => void
    onReferenceFile?: (path: string, isDir: boolean) => void
    onOpenFile?: (path: string) => void
    onOpenDiff?: (tab: SidebarTab) => void
    onSubagentJump?: (childSessionId: string) => void
  }

  /** Describes one kind of sidebar tab (upstream TabDescriptor — the fields our descriptors set). */
  interface TabDescriptor {
    /** Unique id; also the `SidebarTab.type` value (e.g. 'ks:pdf'). */
    id: string
    title: string | (() => string)
    icon?: ReactNode | ((size: number) => ReactNode)
    /** + menu sort order (ascending); default 100. */
    order?: number
    /** Hide from the + menu (opened programmatically, not via the menu). */
    hidden?: boolean
    /** + menu disabled predicate. */
    available?: (ctx: Context, scope: SessionScope, state: SidebarState) => boolean
    /** Single-instance sugar: `true` == `dedupeKey: () => id`. */
    single?: boolean
    /** Dedup key resolver; `undefined` = always open a new tab. */
    dedupeKey?: (tab: SidebarTab) => string | undefined
    /** Custom tab creation (minting the tab + state patches); `null` refuses. */
    createTab?: (state: SidebarState) => { tab: SidebarTab; patch?: Partial<SidebarState> } | null
    /** External-link target claim (v0.13.0+): first registered match wins. */
    urlTarget?: (url: URL) => boolean
    /** Declarative settings shown in the Side card settings page. */
    settings?: unknown
    /** Tab-strip badge (v0.12.0+): number = count, string = as-is, nullish hides. */
    badge?: (ctx: Context, scope: SessionScope, state: SidebarState) => string | number | null | undefined
    /** Lifecycle callbacks (v0.12.0+), fired by the service paths only. */
    onOpen?: (tab: SidebarTab, scope: SessionScope) => void
    onActivate?: (tab: SidebarTab, scope: SessionScope) => void
    onClose?: (tab: SidebarTab, scope: SessionScope) => void
    component: (props: TabComponentProps) => ReactNode
  }
}
