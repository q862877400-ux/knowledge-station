/**
 * ks-dsh-plugin — scripts/lib/external-allowlist.mjs
 *
 * **构建纯度**：哪些模块保持 `external`（由宿主 loader 的 `require` 提供），哪些必须打进产物。
 *
 * ## 为什么要有这个文件（2026-09-19，DSH 适配积压第 4 条）
 * 以前 `build-client.mjs` 写的是 `external: ['react', 'react-dom', '@deepseek-ai/*']` ——
 * **整片 external**。后果：代码里 `import ... from '@deepseek-ai/nonexistent'` **构建不报错**，
 * 产物里留一条 `require("@deepseek-ai/nonexistent")`，运行时才炸（而那时已经在用户机器上）。
 * 官方对仓内插件有"纯度"检查（只允许基线模块 + 自己声明注入的模块）—— 我们仓外，得自建。
 *
 * ## 两份名单，各有出处（别抄二手结论）
 * - `DSH_BASELINE_MODULES`：官方浏览器端**基线单例**表，出处
 *   `deepseek-harness/packages/client/web/src/seed.ts`（5 个模块，逐字抄自那里的 import/映射）。
 * - `PLUGIN_INJECT_MODULES`：**我们自己的** `plugin/package.json` 的 `dsh.client.inject`
 *   （声明了宿主必须给我们的模块）。**改 package.json 必须同步这里** ——
 *   `smoke-build-purity.mjs` 会对着 package.json 实测，两边不一致就红。
 * - `PLAIN_EXTERNALS`：`react` / `react-dom`（宿主提供；含子路径如 `react/jsx-runtime`）。
 */

/** 官方基线单例（`packages/client/web/src/seed.ts` 的 seed 映射键，逐字）。 */
export const DSH_BASELINE_MODULES = [
  '@deepseek-ai/cordis',
  '@deepseek-ai/dsh-client-store',
  '@deepseek-ai/dsh-client-ui-slots',
  '@deepseek-ai/dsh-client-ui-primitives',
  '@deepseek-ai/dsh-client-ui-dockkit',
]

/** 我们 `plugin/package.json` → `dsh.client.inject`（宿主必须提供的模块）。 */
export const PLUGIN_INJECT_MODULES = [
  '@deepseek-ai/dsh-client-runtime',
  '@deepseek-ai/dsh-client-locale',
  '@deepseek-ai/dsh-client-ui-slots',
  '@deepseek-ai/dsh-client-ui-conversation',
  '@deepseek-ai/dsh-client-modules',
  '@deepseek-ai/dsh-client-ui-sidebar-right',
]

/** 非 `@deepseek-ai/` 的宿主提供模块。 */
export const PLAIN_EXTERNALS = ['react', 'react-dom']

export const ALLOWED_DEEPSEEK_MODULES = new Set([
  ...DSH_BASELINE_MODULES,
  ...PLUGIN_INJECT_MODULES,
])

/**
 * 一个 specifier 该怎么处理：`'external'`（交给宿主 require）或 `'bundle'`（打进产物）。
 *
 * ⚠ **不认识的 `@deepseek-ai/*` 直接抛**（这就是纯度门禁）：写错的包名必须在**构建期**炸，
 * 而不是在用户机器上 `require` 时才炸。
 * ⚠ 只按 **scope + 包名**判（`@deepseek-ai/<pkg>`），子路径（`.../sub`）跟随其包；
 * **不**用 `startsWith('@deepseek-ai/')` 之外的模糊匹配 —— `@deepseek-ai-evil/x` 这种
 * 看着像但不是的 scope **必须**当普通包打进去（冒烟里有这条反例）。
 */
export function classifyExternal(spec) {
  if (PLAIN_EXTERNALS.includes(spec)) return 'external'
  // react 的子路径（react/jsx-runtime、react-dom/client …）也算宿主提供
  if (PLAIN_EXTERNALS.some((m) => spec.startsWith(m + '/'))) return 'external'

  const m = /^(@[^/]+\/[^/]+)(?:\/|$)/.exec(spec)
  if (!m) return 'bundle'
  const pkg = m[1]
  // ⚠ **大小写**（复核 2026-09-20 的对抗性发现）：scope 判定原来用 `pkg.startsWith('@deepseek-ai/')`
  //   —— **大小写敏感**，而 `build-client.mjs` 的 onResolve filter 也是。于是
  //   `@DeepSeek-AI/x` 被判 `bundle`、filter 根本不触发 ⇒ 走普通解析。今天**恰好**还 fail-closed
  //   （实跑：`Could not resolve "@DeepSeek-AI/dsh-client-ui-slots"` 构建失败），但那是**碰巧**：
  //   Windows 文件系统大小写不敏感，只要盘上真有那个包，宿主的**单例**就会被**静默打进产物**
  //   （多一份实例 ⇒ 插槽/服务注册静默失效那一类最难查的 bug）。Linux 上更是直接解析不到。
  //   ⇒ 现在：① 认 scope 时**先折小写**；② 只要**写法不是全小写**就**显式抛**（模块身份必须逐字节唯一，
  //     不接受大小写变体）。这条反例有冒烟钉着（`smoke-build-purity.mjs`）。
  const lower = pkg.toLowerCase()
  if (lower.startsWith('@deepseek-ai/')) {
    if (pkg !== lower) {
      throw new Error(
        `构建纯度：'${spec}' 的 scope/包名**大小写不规范**（应为全小写 '${lower}'）。`
        + `模块身份按字节比对、不接受大小写变体（Windows 不区分大小写 ⇒ 会静默多打一份宿主单例）。`
        + `改成全小写，或确认它到底该不该由宿主提供。`)
    }
    if (ALLOWED_DEEPSEEK_MODULES.has(pkg)) return 'external'
    throw new Error(
      `构建纯度：'${spec}' 不在允许清单里。要么它确实该由宿主提供 ⇒ 写进 package.json 的 `
      + `dsh.client.inject 并同步 external-allowlist.mjs；要么它是**打错/不存在**的包 ⇒ 修掉 import。`
      + `允许清单：${[...ALLOWED_DEEPSEEK_MODULES].join(', ')}`)
  }
  return 'bundle'
}

/**
 * ⚠ **这套门禁盖不到的地方**（复核 2026-09-20 实测，写在这里免得被当成"全覆盖"）：
 * 门禁是**在解析（onResolve）时**触发的 —— 于是**没有被产物引用**的 import（被 tree-shaking
 * 摇掉、或写在永不执行的分支里）**不会触发**它（实跑 exit 0）。所以它管的是"**产物里**不许出现
 * 清单外的 `@deepseek-ai/*`"，**不是**"源码里不许写错包名"。要覆盖后者得另做静态扫描（未做，别冒领）。
 */
