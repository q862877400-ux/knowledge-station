# DSH decision-record digest — third-party external client+host sidebar plugin
Repo `D:\AI\DSH\deepseek-harness`; all `file:line` are against that checkout. `.md` (English) only.

## 右侧栏契约的决策要点

A tab type = **one static registration + ordinary keyed Slot seats**. Nothing else composes a tab.

- `ctx.sidebarRightTabs.register(def) => disposer`; the type lives as long as the contributing fiber — hold it in `ctx.effect` (`.../2026-09-05-sidebar-tab-types-and-navigation.md:19`).
- `id` ≠ `kind`. `kind` = type discriminator (`openTab` names it; tab identity is built from it). `id` = one *implementation* of a kind, unique across every registration (a package name is natural). A kind is not unique: an `extension` may take over a `builtin`'s kind (`:24`, `:33`; `packages/client/ui-sidebar-right/src/client/tab-registry.ts:91-101`).
- Rejected registrations: a second `id`, a second registration in the same band of a kind, anything meeting a `fallback` of the same kind. Exactly one pair is accepted — `extension` over `builtin` — and the builtin resumes on unregister (`:33`).
- Bands are **literal strings, never a numeric priority or an exported constant**: `extension` (default, highest) / `builtin` / `fallback`; a type that declares nothing outranks every shipped viewer (`:37`, `:95`; `tab-registry.ts:51-58`, `:115`).
- Bodies and titles are **keyed Slots under the definition's own `id`**: `sidebar.right.pane.tab` (body) and `sidebar.right.pane.tab.title`. The seat resolves the tab's `kind` to the type in force and dispatches to that type's `id` (`:41-43`).
- A page type **omits `patterns`** and recognizes no address; it is opened by kind. `patterns` are resource-address globs matched by picomatch under VS Code's editor-resolver rule, with one local change: a pattern containing `:` matches the whole address, one without matches the URI path at any depth (`:35`).
- `title(address)` / `guide[].title()` / `guide[].description()` are **thunks**, read on every use — a language change needs no re-registration (`:39`).
- The registry is provided **without `Service.tracker`**: a tracker rebinds `this.ctx` to the caller, so a cross-package `register()` would add its effect to the caller's fiber while that fiber is the active scope, **stalling browser boot with no error** (`:39`).
- `ctx.sidebarRight` opens content in exactly two ways and otherwise only operates the layout: `openResource(address, {kind?, params?, paneId?, replaceTab?, revealIfOpened?})` and `openTab(kind, {params?, paneId?, replaceTab?, revealIfOpened?})`. **No layout snapshot, no subscription, no lookup by address** — "the face grants control over the layout, not a view of it" (`:57-59`, `:75`, `:108`).
- Page tabs are recorded under the internal `sidebar://<kind>` literal, composed in one place inside the Sidebar package; no caller composes it. Resource addresses are `dsh-resource://<type>/…` (built/parsed by `dsh-util-workspace-path`); any other scheme fails on the same path as an unclaimed address (`:62`, `:79`, `:97`).
- Placement is **the opener's business, never a type-level trait** — `opensInto` was rejected (`:64`, `:93`).
- Params are typed by **what is being opened** via two merge-extensible maps (`SidebarRightResourceParamsMap` keyed by resource type, `SidebarRightTabParamsMap` keyed by kind) (`:66-71`). A dropdown's selection must therefore travel as JSON params, not a closure.
- Occurrence info reaches bodies/titles through the **framework-injected `useTabInfo()` → `{ sidebar, panel, tab }`**; flat owner props were superseded (`:49`; `packages/client/ui-sidebar-right/src/client/index.ts:158-159`).
- One occurrence per committed record, with an `AbortController`, navigation snapshot and Session-bound actions; it **pins the address for the record's lifetime**; close aborts and releases (`:51`; `.../2026-09-05-client-resource-model.md:58`).
- Live data by address = the resource model: `ctx.resources` + global `useResource(address)`; identified by **address alone**; `none|loading|live|failed`; failure is an `ok: false` frame, never a rejection (`client-resource-model.md:15`, `:24-48`).
- Surface: `ui-dockkit` (static-linked, zero DSH deps) is the engine; `ui-sidebar-right` (dynamic plugin) owns `ctx.sidebarRight`, `ctx.sidebarRightTabs`, the tab domain and three extension seats. Product limit **two horizontal panes**, 20–80% divider; layout is **memory-only** (`.../feature/2026-09-04-right-sidebar-docking-infrastructure.md:21-22`, `:36`, `:42`).
- Default page is selected **from the registered guide-entry list**: exactly one entry opens that page; zero or multiple open the guide; resource viewers without guide entries do not affect the count (`.../feature/2026-09-08-sidebar-default-pages.md:13`). → a start-page type must contribute a `guide` entry.
- The extension seats, per source: `sidebar.right.tab.guide` (chain; first non-declining entry replaces the shipped guide body, not the tab), `sidebar.right.tab.guide.entry` (keyed, per guide box), `sidebar.right.tab.menu.item` (list, appended after the kit's layout actions) (`:43-45`; `ui-sidebar-right/src/client/contract/slots.ts:75-88`; reference implementation `packages/client/ui-sidebar-terminal/src/client/index.ts:47-76`).

**⚠ CURRENT-IMPLEMENTATION FLAGS (sidebar) — any of these means the plugin is out of contract:**
1. Reading the layout (snapshot, subscription, `find(address)`, `mode()`) — the face is control-only (`:99`, `:108`).
2. Registering the body/title under the `kind` string instead of the definition's unique `id` (`:41-43`, `:101`).
3. A numeric `priority`, or importing a band constant from the Sidebar package (`:95`).
4. Occurrence data via flat owner props instead of `useTabInfo()` (`:49`).
5. A body that fetches its own data instead of reading a resource by address — it cannot survive undo/redo/reload/HMR (`client-resource-model.md:9`, `:76`).
6. A panel header row, a rail item, or a per-type control placed on the strip rather than in the body (`...right-sidebar-docking-infrastructure.md:64-68`; `sidebar-tab-types-and-navigation.md:91`).

## UI 原语与样式

**Yes — there is an official, authoritative styling approach, and a plugin must follow it.**

- `docs/web-styling.md:11` — "Global style sheets belong in `ui-theme/src/styles/`. Component styles live beside their component as CSS Modules." Ownership: `ui-theme` owns the `--dsw-*` scale/aliases/typography/motion/shadows and light-dark preference; `ui-layout` applies the resolved snapshot; "Feature packages consume semantic aliases and do not define another global theme" (`:9`).
- Injected styles are a real channel **for a dynamic client bundle**, generated by the shared preset, not hand-rolled: "`x.module.css` yields its hashed class map and injects a tagged style at factory execution, while `x.css?inline` exports compiled text for a plugin-owned lifecycle effect" (`packages/client/tsdown.client.ts:5-9`). The tag is `data-plugin="<pkg id>"` / `data-plugin-css="<id>/<file>"`, appended at factory execution, duplicate-skipped (`tsdown.client.ts:43-53`); CSS Modules go through lightningcss with `pattern: '[hash]_[local]'` (`:510-533`); plain `.css` also auto-injects (`:550-564`); HMR removes owned `<style data-plugin>` tags (`2026-07-23-client-plugin-loading-model.md:83`).
- Primitive ownership: `ui-primitives` "is their only channel for sharing a React component" because client feature plugins "never import one another's values" (`.../2026-09-05-shared-client-control-primitives.md:9`). The README **component catalog** is the entry point, and lists the three confusable pairs (`:23`; `packages/client/ui-primitives/README.md:35`, `:60-64`); it is checklist step 1 (`packages/client/AGENTS.md:147`). `Button` (`variant`: `primary|ghost|outline|toolbar`) and `Menu` (items, separators, group labels, nested submenus) are catalogued exports (`ui-primitives/README.md:39`, `:42`).
- `ui-primitives` and `ui-slots` are **static assembly libraries / Web-shell build inputs**, therefore implicitly external for every dynamic bundle — never repeat them in a manifest (`packages/client/AGENTS.md:25`, `:77`).
- Cordis-free primitives "carr[y] no copy of [their] own" (`...shared-client-control-primitives.md:17`); product strings go through the typed locale dictionary (`packages/client/AGENTS.md:113`).

**⚠ FLAG (styling):** literal colours are forbidden and the violation was real — `...shared-client-control-primitives.md:72`: the plugin inventory tag read `var(--dsw-alias-state-warning-primary, #b45309)`, "no such alias exists — the real token is `--dsw-alias-state-warn-primary` — so both themes had been painting the hardcoded fallback that docs/web-styling.md forbids." An inline style encoding a theme branch is equally a violation (`docs/web-styling.md:21`).

## 客户端插件如何加载

- Layers: Web compilation shell (`apps/web`), framework-free startup kernel (`packages/client/web`, **not** a Loader entry), static assembly libraries (Cordis, `ui-primitives`, `ui-slots`), dynamic client packages (`.../2026-08-15-client-shells-and-dynamic-packages.md:21-27`).
- Arrival: bundles are built outside Vite's module graph, arrive as same-origin external classic scripts and only **register a lazy factory** (`window.__ModuleLoader__.load({id, factory})`); side effects — CSS injection included — run at **first materialization** (`2026-07-23-client-plugin-loading-model.md:37`; `tsdown.client.ts:577-579`).
- Division of labour: "**the module system owns module identity and bytes — how code arrives, registers, and becomes an exports; the Loader owns plugin lifecycle — when a plugin mounts, what it waits for, and how it is torn down.**" (`...client-plugin-loading-model.md:35`).
- HMR is coarse by design: "fresh fiber, fresh components, React state lost, data layer untouched — react-refresh-grade state preservation … is deliberately out" (`:89`). Changing a **static assembly** package (incl. `ui-primitives`, `ui-dockkit`) means a shell rebuild + full page reload; there is no HMR for it (`:89`; `...right-sidebar-docking-infrastructure.md:88`).
- **"Shells" vs "dynamic packages"**: shells own `index.html`/Vite/dist and boot; static assembly libraries "supply shared module identities and direct value APIs" (ESM `lib/index.js`, merged and chunked by Vite); dynamic packages declare `dsh.client`, emit a self-registering `lib/client.js`, and remain host-graph entries (`...client-shells-and-dynamic-packages.md:19-31`). `ui-primitives`/`ui-slots` are the two deliberate static exceptions (`:86`).
- **`inject` vs `external` are not interchangeable** (`packages/client/AGENTS.md:85-95`): Cordis service `inject` is a *runtime* edge, any plugin that provides the service may satisfy it (replaceable), an unsatisfied one leaves the fiber PENDING with no timeout, cycles allowed. Module-graph `external` is a *materialization* edge over a module specifier with **one** supplier (the module identity), not replaceable, **throws on the spot**, cycles rejected. `dsh.client.inject` is **informational only** — preflight display and HMR diffing; it does not sequence activation or apply order (`packages/client/AGENTS.md:140`).
- Baseline externals (React, Cordis, `client/store`, `ui-primitives`, `ui-slots`, `ui-dockkit`) are implicit and MUST NOT be repeated; only infrastructure/transport/generated assembly may add a non-baseline `dsh.client.external`, and silence means a private bundled copy (`packages/client/AGENTS.md:75-79`). Baseline lives in `packages/client/web/src/platform.ts` (`PLATFORM_MODULES`; `PRELOADED_CLIENT_EXTERNALS` reserved, currently empty) (`...client-shells-and-dynamic-packages.md:35`).
- Bundle purity gate: a client bundle may inline only `INLINE_SAFE` / vendored / generated-`/remote` wire layers; every other `@deepseek-ai/*` value import is a **build error** (`tsdown.client.ts:64`, `:490-508`).

**What an out-of-tree EXTERNAL plugin may / may not do** (`.../2026-09-08-desktop-bundled-runtime-and-external-plugins.md`):

- Supported: Desktop "loads enabled plugins from `$DSH_HOME/profiles/desktop`", and runtime preparation "boots the complete Host with an external plugin" (`:17`, `:27`).
- MUST: "External plugins declare shared host packages as peers"; ordinary dependencies stay plugin-owned and may differ from dsh's versions (`:31`).
- Validation **rejects** incompatible enabled peers, nested or aliased copies of shared packages, private package links, and dependency resolution through CLI or ancestor directories (`:31`).
- Host-wide instance identity must be added to the shared inventory explicitly: "matching version numbers alone are insufficient" (`:31`).
- Plugin packages survive upgrades, but preservation "is conditional on host API and native runtime compatibility" (`:59`); incompatible plugins are **not** silently deleted or auto-downgraded (`:45`); installed content is not checksum-verified at startup — "unusable modules fail when loaded" (`:49`).

## 被否决的做法（别再走一遍）

- **`rejected/2026-08-08-cordis-web-dynamic-packages.md`** — 提议: a full design for the temporary Cordis Host/Client dynamic runtime (packages, approval, version pointers, Inspect, Guards, tool cards). 否决: "closed as a proposal: the shipped `packages/extensions` runtime and its READMEs own the design" (`:3`). 含义: the temporary define/run runtime is a *different* product; read the shipped extensions package. Its still-load-bearing rules: plain JS only; `ctx.get()` for an optional service vs declared `inject` for a hard one; every reversible side effect through `ctx.effect()`/`ctx.on()`; timers are injected Cordis Services (`inject: ['timer']`), not globals (`:146-152`).
- **`rejected/2026-07-25-client-settings-locale-theme.md`** — 提议: a settings/locale/theme layering with a slot topology, `settings.general.item`, a `ui-settings-*` satellite package per feature, and a Sidebar-interior Settings. 否决: "closed as a proposal: the shipped ui-settings, locale, and ui-theme packages and their READMEs own the design" (`:3`). 含义: do not build a settings page, locale service, or theme registry in a plugin — the shipped packages own them.
- **Panel-header / rail / per-type strip controls** — a `sidebar.right.pane.tab.tools` seat shipped for one review round then removed: "it put type-private buttons on the panel's strip beside the split and collapse controls, where they read as panel chrome. A type's controls belong in its own body." Also rejected: a 32px rail, a header row on the panel, a per-chip `⋯` menu with copy/float, undo/redo buttons, the expand button as a `conversation.session.header.utilities` entry, empty panes as persistent state, and adopting a docking library or react-resizable-panels (`sidebar-tab-types-and-navigation.md:91`; `right-sidebar-docking-infrastructure.md:30`, `:54-74`). 含义: do not add chrome to the panel; a reload/wrap/dropdown control goes inside the body.
- **Type-level placement (`opensInto`) and a hidden sibling heuristic** — 否决: where a tab lands is the opener's business, exactly as VS Code's Explorer decides `sideBySide` itself (`:93`).
- **Extension lists and numeric priorities** — 否决: `claims.extensions` cannot express `.d.ts`, `Dockerfile`, a directory constraint or a scheme (a degenerate glob), and numeric priorities need an exported constant dynamic packages cannot import (`:95`).
- **One `open(address)` with a `sidebarAddress(kind)` helper** — 否决: both need a `sidebar://<kind>` literal or a helper from the Sidebar package, both forbidden by the value-import rule, and both leak a navigation scheme not yet designed (`:97`).
- **`?impl=`, `find(address)`, `mode()`/`setMode()`, a layout snapshot, a `features` list** — considered and left out (`:99`).
- **Slot priorities for extension-over-builtin, then registry-minted slot keys** — 否决: a value import across dynamic plugins plus a second rule system; then a two-step registration whose ordering mattered (`:101`).
- **Per-tab instance APIs** — a Cordis fiber per tab, an abstract base class, an `initial`/`create`+`dispose` instance, a set of `useTab*` hooks, a framework-managed `useTabResource(fetch)`, a `useTabStream`; each rejected, and `visible` was added as a prop rather than a hook. The rejection of occurrence-reading hooks is superseded by the tab-info decision; the instance/fiber/data-stream rationale still applies (`:87-89`; `client-resource-model.md:72`).
- **Resource-model rejected forms** — session-bound `(session, address)` identity; content inside the resource stream ("content can be arbitrarily large … a stream is for pushing change, not payload"); failure as a thrown error wrapped as `gateway/internal`; the `file:/…` and `file://<scope>/…` grammars; a hand-parsed scheme prefix (`client-resource-model.md:62-70`). 含义: read metadata from the stream and fetch content yourself; a provider throw is a bug, not a failure state; never mint a second address scheme.
- **Primitives rejected** — a `SettingsCard` primitive; a gate rejecting `role="switch"`/`.switch` outside `ui-primitives`; preserving every current appearance behind extra `Tag` props; extending `Pill` instead of adding `Tag`; a two-axis `variant × tone` API; putting the reuse rule in the root `AGENTS.md` (`shared-client-control-primitives.md:45-57`).
- **Loading-model rejected** — a hand-written loader as governor; reusing `@cordisjs/plugin-hmr` in the browser; module federation; import maps; full ctx-ification of React/libraries; eager instantiation with a frozen table; **fetch response text then inject an inline `<script>`**; a builder-push rebuild channel (`client-plugin-loading-model.md:107-115`).
- **Shell/packaging rejected** — converting every client package to a dynamic plugin; a separate `client-static.js`; compiling all shared modules into the Vite entry; a general module-provider declaration; hardcoding preload URLs in `index.html` (`client-shells-and-dynamic-packages.md:68-76`). Desktop: installing the offline seed at startup; linking all host deps into plugins; hardlinks; `NODE_PATH`/preserved symlink paths; keeping core packages in ASAR (`desktop-bundled-runtime-and-external-plugins.md:51-55`).

## 硬约束清单

> **A control that a second client package needs lives in `ui-primitives`.** … What the rule forbids is the copy — when a control already exists, the author either uses it or lifts the deliberate difference into a prop.
> — `2026-09-05-shared-client-control-primitives.md:15`

> Use CSS Modules and `clsx`; do not add a component library or Tailwind.
> — `docs/web-styling.md:16`

> Use `--dsw-alias-*` semantic tokens in feature components. Do not copy static palette values or write literal colors there.
> — `docs/web-styling.md:17`

> Keep theme selectors out of feature component CSS. Light/dark overrides belong to the theme owner.
> — `docs/web-styling.md:18`

> Put presentation in CSS. Inline React styles may pass component-local custom-property values but must not encode theme branches.
> — `docs/web-styling.md:21`

> **Baseline externals are implicit for every dynamic bundle.** Do not repeat React, Cordis, `client/store`, `ui-primitives`, `ui-slots`, or `ui-dockkit` in package manifests.
> — `packages/client/AGENTS.md:77`

> **`dsh.client.external` is not a feature-plugin dependency mechanism.** Only infrastructure, transport, or generated assembly may add a package-specific non-baseline value request whose dynamic row must be materialized through the module table.
> — `packages/client/AGENTS.md:78`

> **A feature plugin MUST NOT runtime-import or re-export another feature plugin's values, and MUST NOT declare `dsh.client.external` to obtain them.** Shared declarations use `import type`; behavior crosses packages through injected Cordis services, and UI crosses packages through slots. If neither fits, stop and escalate — do not add an export to unblock yourself.
> — `packages/client/AGENTS.md:36`

> **inject returns plain data and callbacks** from the apply closure's own ctx — no hand-made hooks, no ReactNode producers, no whole-service objects.
> — `packages/client/AGENTS.md:17`

> **A UI plugin exports no values beyond what cordis loading needs** … Adding any new value export requires user sign-off, not a matching consumer.
> — `packages/client/AGENTS.md:34`

> External plugins declare shared host packages as peers. … A third-party package requiring host-wide instance identity must be explicitly added to the runtime's shared inventory; matching version numbers alone are insufficient.
> — `2026-09-08-desktop-bundled-runtime-and-external-plugins.md:31`

> Values must be JSON-serializable, and a record must be rebuildable from address and parameters alone, because undo, redo, reload, and HMR rebuild tabs after the opener is gone.
> — `2026-09-05-sidebar-tab-types-and-navigation.md:73`

> A type's controls — a reload, a wrap toggle — live inside its own body; the strip belongs to the panel and carries only the panel's controls.
> — `2026-09-05-sidebar-tab-types-and-navigation.md:45`

> The face opens content in two ways and does nothing else with content.
> — `2026-09-05-sidebar-tab-types-and-navigation.md:55`

> Exactly one entry opens that entry's page; zero or multiple entries open the guide. Resource viewers without guide entries do not affect this count.
> — `2026-09-08-sidebar-default-pages.md:13`

> These contexts reduce misuse and provide instructional errors, but they are not security boundaries against malicious code.
> — `rejected/2026-08-08-cordis-web-dynamic-packages.md:146` (note status: rejected proposal; the sandbox statement matches the shipped runtime)

## 未解答

- Whether a **third-party external plugin may register a right-sidebar tab type at all** is not stated. The contracts exist so "plugins shipped from outside this repository will write against" them (`sidebar-tab-types-and-navigation.md:9`) and `extension` is "the band of a type from outside the product" (`:37`), but no record grants or withholds the capability on the Desktop external-plugin path.
- The roster: a client plugin is a **host-graph row** (`client-plugin-loading-model.md:55`) in `packages/bundle/web-app/cordis.patch.yml` (`packages/client/AGENTS.md:139`). None of these records say **how an out-of-tree plugin adds its own row**. This is the author's biggest unresolved dependency.
- No note relates `packages/extensions` (the shipped temporary runtime) to an external client+host plugin's registration surfaces; the rejected note defers entirely to it (`:3`).
- Whether an external plugin may contribute a **default page** under the one-guide-entry rule (`sidebar-default-pages.md:13`) without being a shipped builtin.
- `registerCloseHandler`, `openTabIn`, `tabDomain.occurrence` (used at `packages/client/ui-sidebar-terminal/src/client/index.ts:32-53`, `:85`) are absent from the note's list of fixed faces (`:110`) — public contract or internal is unstated here.
- `useTabInfo()`'s exact field set is deferred to `docs/subsystems/sidebar-right.md` (`:49`); not opened in this digest.
- z-index has **no token layer**: the panel, float host and tab menu use hard-coded values, and a token layer is deferred (`right-sidebar-docking-infrastructure.md:89`, `:97`). A plugin overlay cannot consume a z-index token because none exists.
