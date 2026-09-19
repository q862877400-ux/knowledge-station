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

import { isAbsolute, resolve } from 'node:path'

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
 * 把 specifier 归一化成 **esbuild 实际会去解析的那个模块标识**：
 * 反斜杠 → 斜杠、折叠重复斜杠、**并消掉 `.`/`..` 段**。
 *
 * ⚠ **只用于识别，不用于"接受"**：识别到"归一化后落在宿主提供的模块范围内、而原写法不是规范形"
 * 就**当场抛**。因为 esbuild 会照着归一化后的路径去盘上找真包，找不到才报 `Could not resolve`。
 *
 * 三条真实的绕过（**这台 Windows 上逐个实测**，证据见 `docs/DEVELOPMENT-HISTORY.md` §10.140）：
 * - `@deepseek-ai//dsh-util-values`（重复斜杠）—— **真会**解析到盘上真包；
 * - `x/../@deepseek-ai/dsh-util-values`（`..` 段）—— **真会**（复核 r2 真构建复现，静默内联 +6785B）；
 * - `@deepseek-ai\dsh-util-values`（反斜杠）—— **真会**：esbuild 在 **Windows** 上把 `\` 与 `/`
 *   都当路径分隔符（metafile 实测 `node_modules/@deepseek-ai/dsh-util-values/lib/index.js`，
 *   产物 6946B）。⚠ **复核 r2 报的 `Could not resolve` 是针对 `@deepseek-ai\x`** —— 那个包名
 *   `x` 盘上**根本不存在**，所以"解析不到"的**原因是包不存在，不是反斜杠不被当分隔符**。
 *   差别在**平台**（POSIX 下 `\` 不是分隔符），别把这条写成"`//` 会、`\` 不会"。
 *   我们照样要拒它：同一份源码在 Windows 上会静默多打一份宿主单例。
 *
 * ⚠ **旧版为什么漏掉 `..`**：判定只在"**以 `@` 开头**的串"上做（正则锚 `^@`），
 *   于是 `x/../@deepseek-ai/<pkg>` 连 scope 都没认出来 ⇒ 判 `bundle` ⇒ 静默内联。
 *   现在判定建立在**归一化后的整串**上，锚不再是"原串开头"。
 */
export function normalizeSpecifier(spec) {
  const slashed = spec.replace(/\\/g, '/')
  const relative = slashed.startsWith('./') || slashed.startsWith('../') || slashed.startsWith('/')
  const parts = []
  for (const segment of slashed.split('/')) {
    if (segment === '' || segment === '.') continue
    if (segment === '..') {
      if (parts.length > 0 && parts[parts.length - 1] !== '..') parts.pop()
      else parts.push('..')
      continue
    }
    parts.push(segment)
  }
  const body = parts.join('/')
  return relative && body !== '' ? `./${body}` : body
}

/** 归一化后算不算"宿主提供的模块"（我们的 scope 或 react/react-dom 及其子路径）。 */
export function isGuardedSpecifier(canonical) {
  return /^@deepseek-ai\//i.test(canonical)
    || PLAIN_EXTERNALS.includes(canonical)
    || PLAIN_EXTERNALS.some((m) => canonical.startsWith(m + '/'))
}

/**
 * 同一条判定，但**先剥掉归一化后残留的前导 `../`**（`x/../../x/../@deepseek-ai/x` 这类写法
 * 归一化后是 `../@deepseek-ai/x`）。剥完仍落在受管范围 ⇒ 照样抛（fail-closed：
 * 没有正常源码会这么写，而它离"能解析到真包"只差 esbuild 补不补那几级）。
 */
function isGuardedAfterParentClimb(canonical) {
  return isGuardedSpecifier(canonical) || isGuardedSpecifier(canonical.replace(/^(?:\.\.\/)+/, ''))
}

/**
 * 一个**已解析的路径**（或一条说明符文本）是不是落在**宿主提供的单例**上：
 * `.../node_modules/@deepseek-ai/<pkg>`、`.../node_modules/react`、`.../node_modules/react-dom`。
 *
 * ⚠ **为什么需要它**（复核 `verify-freeze-corr3` A1，2026-09-20 第四轮 —— 本门禁的**真空洞**）：
 * 判定原来只看**裸** specifier（不以 `.`/`/` 开头），于是
 * `./../node_modules/@deepseek-ai/dsh-util-values/lib/index.js` 与 `../node_modules/...`
 * 这类**相对路径整条绕过门禁** —— 它在 filter 里**是**命中的（filter 含 `@deepseek-ai` 与 `\.\.`），
 * 但 `classifyExternal` 一认出"不是裸 specifier"就直接判 `bundle` ⇒ **静默内联宿主单例**。
 * 复核用 esbuild JS API + `metafile` 实测，**本轮自己复现**（证据见 §10.141）：
 * 有门禁时 `../node_modules/@deepseek-ai/dsh-util-crypto/lib/index.js` **BUILT 1068B**、
 * `./../node_modules/@deepseek-ai/dsh-util-values/lib/index.js` **BUILT 7377B**，
 * metafile input 就是那个宿主单例文件 —— 正是本门禁自述判据（"产物里不许出现清单外的
 * `@deepseek-ai/*`"）的**反例**。⇒ 现在按**落点**判并当场抛。
 *
 * ⚠ 大小写用 `i`：Windows / 常见 CI 的 FS 不区分大小写，`@DeepSeek-AI` 目录照样解析到同一份文件。
 */
export function isHostProvidedResolvedPath(pathLike) {
  const p = String(pathLike).replace(/\\/g, '/')
  return /\/node_modules\/(?:@deepseek-ai\/[^/]+|react|react-dom)(?:\/|$)/i.test(p)
}

/**
 * `build-client.mjs` 的 esbuild `onResolve` filter —— **单一出处**（别再各写一份：filter 与判定
 * 口径一旦漂开，就会出现"判定函数认得、filter 却根本不触发"的绕过，`x/../...` 那次就是这样）。
 *
 * 它只需"**宽到足以把任何可能被归一化进受管范围的 specifier 送进 `classifyExternal`**"：
 * filter 不命中 ⇒ esbuild 走默认解析（`classifyExternal` 根本没机会说话）。命中的多数是
 * 普通包（`classifyExternal` 返回 `'bundle'` ⇒ onResolve 返回 undefined ⇒ 照旧默认解析），
 * 所以放宽它**不改变**正常构建。
 *
 * ⚠ **相对路径也在覆盖范围内**（复核 corr3 A1）：`../node_modules/@deepseek-ai/x` 命中的是这里的
 * `@deepseek-ai` 分支、`../x` 命中 `\.\.` 分支，所以只要落点检查放在 `classifyExternal` 里，
 * 就没有"filter 压根不触发"的洞。
 */
export const PURITY_ONRESOLVE_FILTER = /@deepseek-ai|\.\.|^react$|^react-dom$|^react\/|^react-dom\//i

/**
 * `build-client.mjs` 用的纯度插件 —— **工厂也放在这里**（与 `classifyExternal` / filter 同一份文件）：
 * 判定、filter、**接线**三样必须在同一处，否则"各写一份"就有漏（`x/../…` 那次就是 filter 那一半漏的）。
 * `smoke-build-purity.mjs` 直接 import 这个工厂，用**真 esbuild 构建**当反例（无门禁 BUILT / 有门禁被拦），
 * 所以这里不是"又一份接线"，而是**被冒烟 dogfood 的唯一一份**。
 */
export function purityPlugin() {
  return {
    name: 'ks-build-purity',
    setup(build) {
      build.onResolve({ filter: PURITY_ONRESOLVE_FILTER }, (args) => {
        // ⚠ `args.resolveDir` 必须传下去：**相对路径的落点只能靠它算出来**（复核 corr3 A1）。
        const verdict = classifyExternal(args.path, args.resolveDir)
        return verdict === 'external' ? { path: args.path, external: true } : undefined
      })
    },
  }
}

/**
 * 一个 specifier 该怎么处理：`'external'`（交给宿主 require）或 `'bundle'`（打进产物）。
 *
 * ⚠ **不认识的 `@deepseek-ai/*` 直接抛**（这就是纯度门禁）：写错的包名必须在**构建期**炸，
 * 而不是在用户机器上 `require` 时才炸。
 * ⚠ 只按 **scope + 包名**判（`@deepseek-ai/<pkg>`），子路径（`.../sub`）跟随其包；
 * **不**用 `startsWith('@deepseek-ai/')` 之外的模糊匹配 —— `@deepseek-ai-evil/x` 这种
 * 看着像但不是的 scope **必须**当普通包打进去（冒烟里有这条反例）。
 */
export function classifyExternal(spec, resolveDir) {
  // ⚠ **先归一化，再判"写法规范不规范"**（复核 r2 2026-09-20 第三轮的对抗性发现）：
  //   `x/../@deepseek-ai/dsh-util-values` 被 esbuild 归一化成盘上真包并**静默内联**，
  //   而旧判定只在**以 `@` 开头**的串上认 scope ⇒ 判 `bundle`（绕过）。现在只要
  //   **归一化后**落在受管范围（我们 scope / react）/ 且裸 specifier 的写法变了，就当场抛。
  //   ⚠ 只对**裸 specifier**（不以 `.`/`/` 开头、也**不是绝对路径**）这样做：相对路径（`../ui/x`）不是包标识，
  //     归一化的形状差异（`./../ui/x`）没有语义，不能拿它当错误（第四轮 A1 起改为**按落点**判，见下）。
  const canonical = normalizeSpecifier(spec)
  // ⚠ "裸 specifier" 的判据必须把**绝对路径**也算进去：Windows 上 `D:\…\node_modules\@deepseek-ai\x.js`
  //   既不以 `.` 也不以 `/` 开头 ⇒ 只看这两个前缀的话它会被当成"裸包名" ⇒ 又漏一次（本轮冒烟实测
  //   NOT-THREW）。`isAbsolute` 是平台相关的（POSIX 上不认 `D:\`），所以再补一条盘符正则兜底。
  const bare = !spec.startsWith('.') && !spec.startsWith('/')
    && !isAbsolute(spec) && !/^[a-zA-Z]:[\\/]/.test(spec)
  if (bare && canonical !== spec && isGuardedAfterParentClimb(canonical)) {
    throw new Error(
      `构建纯度：'${spec}' 归一化后是 '${canonical}'（落在宿主提供的模块范围内），写法不规范。`
      + `esbuild 会把它归一化后解析到盘上的真包并**静默打进产物** ⇒ 宿主单例被多打一份。`
      + `改成规范写法 '${canonical}'。`)
  }

  // ⚠⚠ **相对/绝对说明符：按落点判，不是"不是裸 specifier 就放行"**（复核 `verify-freeze-corr3` A1，
  //   2026-09-20 第四轮 —— 这是本门禁的**真空洞**，原话保留在上面那句"只对裸 specifier 这样做"里）：
  //   改前 `./../node_modules/@deepseek-ai/dsh-util-values/lib/index.js` 与 `../node_modules/…`
  //   **有门禁时照样 BUILT**（本轮 metafile 实测：7377B / 1068B，input 就是宿主单例）。
  //   ⇒ 现在：`path.resolve(resolveDir, spec)` 算落点，落在 `node_modules/@deepseek-ai/**`
  //   （或 react / react-dom）就**当场抛**。
  //   `resolveDir` 由 onResolve 的 `args.resolveDir` 提供；单元级调用没给也**不能放行** ——
  //   退化成对 **spec 文本**本身做同一判定（fail-closed：不给"忘了传参就静默内联"留门）。
  if (!bare) {
    const abs = resolveDir ? resolve(resolveDir, spec) : null
    if ((abs !== null && isHostProvidedResolvedPath(abs)) || isHostProvidedResolvedPath(spec)) {
      throw new Error(
        `构建纯度：'${spec}' 是**相对/绝对路径**，但它解析到宿主提供的单例`
        + `${abs === null ? '' : `（${abs}）`}。相对路径不受允许清单管 ⇒ 宿主单例会被`
        + `**静默打进产物**（多一份实例 ⇒ 插槽/服务注册静默失效那一类最难查的 bug）。`
        + `改成裸 specifier 写法（如 '@deepseek-ai/<pkg>'），让允许清单来判它该 external 还是该报错。`)
    }
    return 'bundle'
  }

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
 * ⚠ **这套门禁盖不到的地方**（复核 2026-09-20 实测 + 第四轮 corr3 更新，写在这里免得被当成"全覆盖"）：
 * 1. 门禁是**在解析（onResolve）时**触发的 —— 于是**没有被产物引用**的 import（被 tree-shaking
 *    摇掉、或写在永不执行的分支里）**不会触发**它（实跑 exit 0）。所以它管的是"**产物里**不许出现
 *    清单外的 `@deepseek-ai/*`"，**不是**"源码里不许写错包名"。要覆盖后者得另做静态扫描（未做，别冒领）。
 * 2. filter 只覆盖"**说明符文本**里带 `@deepseek-ai` / `..` / `react`"的那些。落点检查（corr3 A1）
 *    是**跟在 filter 之后**的，所以：把宿主单例**拷进源码树**再用纯相对路径引
 *    （如 `./vendor/deepseek-ai-values.js`，文本里既没有 `@deepseek-ai` 也没有 `..`）**不触发**
 *    门禁 —— 那已经不是同一个模块路径了，属另一个口径（"源码里有没有第二份实现"），未做。
 *    —— 这条是 corr3 A1 的**边界**：它堵的是"相对路径**指向 node_modules 里的宿主单例**"，
 *    不是"任何相对路径"。别把 A1 的修法读成"相对路径全查了"。
 */
