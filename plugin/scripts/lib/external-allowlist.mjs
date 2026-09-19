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
import { realpathSync } from 'node:fs'

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
 * pnpm 的 `.pnpm/…/node_modules/<包>` 形态由"匹配**任意**一层 `node_modules`"自然覆盖
 * （`.pnpm/@deepseek-ai+dsh-util-values@1.0.0/node_modules/@deepseek-ai/dsh-util-values/…`）。
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
 * ⚠ **归一化是必需的，不是装饰**（第五轮 2026-09-20 实测，三种写法分别漏在不同层）：
 * - **8.3 短名**：`../NODE_M~1/@deepseek-ai/<pkg>/lib/index.js` —— esbuild 的 `build.resolve`
 *   返回的 `path` **保留短名**（`…\plugin\NODE_M~1\@deepseek-ai\…`），只有 `realpathSync`
 *   才把它变成 `…\plugin\node_modules\@deepseek-ai\…`；
 * - **尾随点**：`../node_modules./@deepseek-ai/<pkg>/…` —— `build.resolve` 成功（errs=0）但
 *   `realpathSync` **失败**（`ENOENT`），而 Win32 打开路径时会吃掉尾随的 `.` ⇒ 必须对**段**
 *   做 `去掉尾随 . 与空格`，否则文本里那个 `node_modules.` 逃掉；
 * - **junction / 符号链接**：`./dsh-util-values/lib/index.js`（`dsh-util-values` 是指向
 *   `node_modules/@deepseek-ai/dsh-util-values` 的 junction）—— esbuild 自己就报出了真身，
 *   realpath 再兜一层。
 *
 * ⚠ 大小写折小写：Windows / 常见 CI 的 FS 不区分大小写，`@DeepSeek-AI` 目录照样解析到同一份文件。
 * （去尾随点只会把 `node_modules.` 变成 `node_modules`，**不可能凭空造出** `@deepseek-ai/` 这一段，
 *  所以这条归一化不会制造误报 —— 它只能让漏掉的匹配上。）
 */
export function isHostProvidedResolvedPath(pathLike) {
  const p = String(pathLike).replace(/\\/g, '/')
    .split('/').map((seg) => seg.replace(/[. ]+$/, '')).join('/')
    .toLowerCase()
  return /(?:^|\/)node_modules\/(?:@deepseek-ai\/|react-dom(?:\/|$)|react(?:\/|$))/.test(p)
}

/**
 * 解析**失败**时的 fail-closed 判据：这条说明符文本"可疑"吗？
 * 可疑 = 含我们的 scope（`@deepseek-ai/`，带斜杠 —— `@deepseek-ai-evil/x` **不算**）、
 * 含 `node_modules`（含尾随点形态）、或指向 `react` / `react-dom` 目录。
 * `lodash` / `@deepseek-ai-evil/x` 这类**不可疑** ⇒ 照旧交给 esbuild 报 `Could not resolve`，
 * 门禁不越界（冒烟里有这两条负面对照）。
 */
export function isSuspiciousSpecifier(spec) {
  return /@deepseek-ai\/|node_modules|(?:^|[\\/])react(?:-dom)?(?:[\\/]|$)/i.test(String(spec))
}


/**
 * `build-client.mjs` 的 esbuild `onResolve` filter —— **单一出处**（别再各写一份：filter 与判定
 * 口径一旦漂开，就会出现"判定函数认得、filter 却根本不触发"的绕过，`x/../...` 那次就是这样）。
 *
 * 它只需"**宽到足以把任何可能落到宿主单例上的说明符送进判定**"：filter 不命中 ⇒ esbuild 走默认
 * 解析（判定根本没机会说话）。命中的多数是普通模块（判定返回 `'bundle'` ⇒ onResolve 返回
 * undefined ⇒ 照旧默认解析），所以放宽它**不改变**正常构建。
 *
 * ⚠ **第五轮（2026-09-20）为什么又要放宽**（本轮实测：8 条绕过里有 **3 条**——R6 junction /
 * R7 `./node_modules/react/index.js` / R8 绝对路径——是**被旧 filter 整个挡在门外**的，
 * onResolve 压根没被调用，判定再对也没用）：
 * 旧 filter `/@deepseek-ai|\.\.|^react$|^react-dom$|^react\/|^react-dom\//i` 只认
 * "文本里带 `@deepseek-ai` / `..` / `^react`"的写法，于是
 * `./node_modules/react/index.js`（一个 `.` 段，既没 `..` 也不以 `react` 开头）**压根不触发回调**，
 * 而 `classifyExternal` 本来是认得出它的。⇒ 现在只要是"含路径分隔符 / 相对前缀 / 绝对路径 /
 * 短名标记 / 我们的 scope / react" **任何一条**就触发：
 * - `[\\/]`：任何带分隔符的路径（`./x`、`../x`、`x/../../y`、`D:\…`、`\\?\…`）——**junction 那条
 *   只能靠这一支**（`./dsh-util-values/lib/index.js` 文本里既没有 `@deepseek-ai` 也没有 `..`）；
 * - `node_modules`：含**尾随点**形态 `node_modules.`（`[\\/]` 也覆盖，双保险）；
 * - `@deepseek-ai` / `^react(?:-dom)?$`：裸 specifier（无分隔符）；
 * - `~[0-9]`：8.3 短名（`NODE_M~1`）的裸形态。
 *
 * ⚠ filter 只是"**要不要叫醒判定**"，**不许**在这里做结论 —— 结论一律由 `classifyExternal`
 * （文本层）+ `resolveLanding`（解析层）给，两者与本 filter 同在此文件。
 */
export const PURITY_ONRESOLVE_FILTER =
  /[\\/]|@deepseek-ai|node_modules|^\.|\.\.|^react(?:-dom)?$|~[0-9]/i

/** `pluginData` 上的重入标记：让"我们自己发起的那次解析"能立刻放手（见 `purityPlugin`）。 */
const PURITY_REENTRY = '__ksPurityReentry'

/**
 * `build-client.mjs` 用的纯度插件 —— **工厂也放在这里**（与 `classifyExternal` / filter / **接线**同一份文件）：
 * 判定、filter、接线三样必须在同一处，否则"各写一份"就有漏（`x/../…` 那次漏的是 filter；
 * corr3 A1 那次漏的是 `args.resolveDir` 接线）。
 * `smoke-build-purity.mjs` 直接 import 这个工厂，用**真 esbuild 构建**当反例（无门禁 BUILT / 有门禁被拦），
 * 所以这里不是"又一份接线"，而是**被冒烟 dogfood 的唯一一份**。
 *
 * ⚠ **第五轮（2026-09-20）从根上改**：不再只看 `args.path` 的**文本**，而是让 **esbuild 自己解析**
 * （`build.resolve`），拿**真实解析路径 + realpath** 再判落点。文本层（`classifyExternal`）留下，
 * 因为它能给出更准确的"写法不规范"诊断、并兜住"解析不出来"的写法；**落点**一律以解析结果为准。
 *
 * ⚠⚠ **递归陷阱（实测，不是推测）**：esbuild 文档原话 ——
 * *"There is currently no attempt made to detect infinite path resolution loops. Calling `resolve`
 *  from within `onResolve` with the same parameters is almost certainly a bad idea."*
 * 本轮实测确认：**照抄同一组参数**调 `build.resolve` 会**重入自己的 onResolve** 并无限递归
 * （探针在第 7 层被自己的守卫掐掉）。所以这里用 `pluginData` 打标记：重入时第一件事就是
 * `return undefined`，把解析交回 esbuild 的默认实现，递归**恰好终止在第二层**。
 *
 * ⚠⚠ **接线（`args.resolveDir`）必须传下去**（复核 corr3 A1 的第三处漏点）。第五轮起不只"传"，
 * 而是**缺了就当场炸**：相对 specifier 没有 `resolveDir` 时 esbuild **不做任何路径解析**
 * （文档："esbuild will still run onResolve plugin callbacks but will not attempt any path resolution
 * itself"）⇒ 落点无从得知 ⇒ 静静地放行正是要堵的漏。冒烟用 `../NODE_M~1/…` 与 junction 两条
 * 探针钉住"漏传就红"。
 */
export function purityPlugin() {
  return {
    name: 'ks-build-purity',
    setup(build) {
      // 同一 (namespace, resolveDir, path) 只解析一次；值存 **Promise** 以便并发去重。
      const resolvedCache = new Map()
      const landingOf = (args) => {
        const key = `${args.namespace}\u0000${args.resolveDir}\u0000${args.path}`
        let hit = resolvedCache.get(key)
        if (hit === undefined) {
          hit = resolveLanding(build, args)
          resolvedCache.set(key, hit)
        }
        return hit
      }

      build.onResolve({ filter: PURITY_ONRESOLVE_FILTER }, async (args) => {
        // ① **重入**：这次解析是我们自己在 ③ 里发起的 ⇒ 立刻放手。
        //    不这样做就会无限递归（见上面工厂注释里的 esbuild 文档原话 + 本轮实测）。
        if (args.pluginData && args.pluginData[PURITY_REENTRY]) return undefined

        // ② **文本层**：写法不规范 / 清单外的 `@deepseek-ai/*` / 大小写变体 ⇒ 当场炸；
        //    清单内 ⇒ external（**不**再去解析：宿主模块本来就不在盘上，解析必然失败）。
        //    ⚠ 这里的 `args.resolveDir` 只为**诊断更准**（错误信息里能印出绝对落点）。
        //    **不是**防线的承载点：把它去掉（`classifyExternal(args.path)`）**不再**构成洞 ——
        //    第四轮那句"接线漏传也红"之所以是假绿，就是因为那时它是**唯一**的落点防线。
        //    现在承载接线的是 ④ 的 `resolveLanding()`（它直接从 `args` 取 `resolveDir` 交给
        //    `build.resolve`），冒烟里用 `../NODE_M~1/…` / junction 两条探针 + **变异测试**钉住。
        const verdict = classifyExternal(args.path, args.resolveDir)
        if (verdict === 'external') return { path: args.path, external: true }

        // ③ **接线自检**：相对 specifier 缺 `resolveDir` ⇒ 落点不可知 ⇒ fail-closed（别静默放行）。
        const relativeSpec = args.path.startsWith('./') || args.path.startsWith('../')
        if (relativeSpec && !args.resolveDir) {
          throw new Error(
            `构建纯度：相对说明符 '${args.path}' 没有 resolveDir ⇒ 落点无法判定。`
            + `这是**接线**漏了（onResolve 必须把 args.resolveDir 交给 build.resolve）；`
            + `缺了它 esbuild 不做任何路径解析，相对路径就会绕过落点检查被静默打进产物。`)
        }

        // ④ **解析层**：让 esbuild 自己解析，拿真实落点（+ realpath）判是不是宿主单例。
        const landing = await landingOf(args)
        if (landing.host) {
          throw new Error(
            `构建纯度：'${args.path}' 解析到宿主提供的单例上`
            + `${landing.via ? `（${landing.via}）` : ''}`
            + `${landing.esbuildPath && landing.esbuildPath !== landing.via ? `（esbuild 报的落点：${landing.esbuildPath}）` : ''}`
            + `。宿主单例被多打一份 ⇒ 插槽/服务注册静默失效那一类最难查的 bug。`
            + `改成裸 specifier 写法（如 '@deepseek-ai/<pkg>'），让允许清单来判它该 external 还是该报错。`
            + (landing.unresolved ? `（esbuild 解析失败：${landing.reason}）` : '')
            + (landing.note ? `〔${landing.note}〕` : ''))
        }
        return undefined
      })
    },
  }
}

/**
 * 让 **esbuild 自己**解析一条说明符，回答"它的**真实落点**是不是宿主单例"。
 *
 * 用的 API（esbuild **0.25.12**，`plugin/node_modules/esbuild/lib/main.d.ts:307` 的签名，
 * 逐个字段核过类型定义）：
 *   `build.resolve(path: string, options?: ResolveOptions): Promise<ResolveResult>`
 *   `ResolveOptions = { pluginName?, importer?, namespace?, resolveDir?, kind?, pluginData?, with? }`
 *   `ResolveResult  = { errors, warnings, path, external, sideEffects, namespace, suffix, pluginData }`
 * - `errors` 非空**不抛异常**（文档："This function does not always throw an error when it fails."）
 *   ⇒ 必须显式检查。
 * - `pluginData` 会原样传给被重入的 onResolve ⇒ 用它终止递归（`PURITY_REENTRY`）。
 * - 返回的 `path` **不是 realpath**（8.3 短名实测保留 `NODE_M~1`）⇒ 再叠 `realpathSync[.native]`。
 *
 * @returns `{ host: boolean, via?, esbuildPath?, reason?, unresolved?, note? }`
 */
async function resolveLanding(build, args) {
  let res
  try {
    res = await build.resolve(args.path, {
      resolveDir: args.resolveDir,
      importer: args.importer,
      kind: args.kind,
      namespace: args.namespace,
      pluginData: { [PURITY_REENTRY]: true },
    })
  } catch (e) {
    return unresolvedVerdict(args.path, String(e?.message ?? e))
  }
  if (!res || (res.errors && res.errors.length > 0)) {
    return unresolvedVerdict(args.path, (res?.errors ?? []).map((x) => x.text).join(' | ') || 'unknown')
  }

  // 候选落点：esbuild 报的路径 + 它的 realpath（两种实现都试）。
  // ⚠ 两个都要留：realpath 才能解 8.3 短名 / junction；而**尾随点**（`node_modules.`）realpath 会
  //   ENOENT，只有 esbuild 报的那条（经 `isHostProvidedResolvedPath` 的去尾随点归一化）能匹配。
  const candidates = [{ p: res.path, src: 'esbuild' }]
  for (const [name, fn] of [['realpathSync.native', realpathSync.native], ['realpathSync', realpathSync]]) {
    try { candidates.push({ p: fn(res.path), src: name }) } catch { /* 落点解不出来（尾随点形态）*/ }
  }
  const hit = candidates.find((c) => isHostProvidedResolvedPath(c.p))
  if (hit) {
    return { host: true, via: hit.p, esbuildPath: res.path, note: `落点由 ${hit.src} 判出` }
  }
  return { host: false, esbuildPath: res.path }
}

/**
 * 解析**失败**时的裁决：文本可疑（含我们的 scope / `node_modules` / `react`）⇒ fail-closed 判"有罪"。
 * 不可疑（`lodash`、`@deepseek-ai-evil/x`）⇒ 放过，让 esbuild 自己报 `Could not resolve`
 * （门禁**不越界**，冒烟里有这两条负面对照）。
 */
function unresolvedVerdict(spec, reason) {
  if (isSuspiciousSpecifier(spec)) {
    return { host: true, unresolved: true, reason, note: '解析失败但文本可疑 ⇒ fail-closed' }
  }
  return { host: false, unresolved: true, reason }
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
  //   ⚠⚠ **第五轮（2026-09-20）更正上句的适用范围**（复核实测打回）：这句**只对"文本里含
  //     `node_modules` + 受管落点"的写法成立**。`resolve()` 是**纯字符串**运算 —— 它既不查盘、
  //     不解 8.3 短名、不解 junction/symlink，也不做扩展名补全。所以下面这支：
  //       · `../NODE_M~1/@deepseek-ai/<pkg>/lib/index.js` ⇒ 文本里没有字面 `node_modules` ⇒ 不抛；
  //       · `./dsh-util-values/lib/index.js`（junction）⇒ 文本里什么都没有 ⇒ 不抛；
  //       · `x/../../node_modules/@deepseek-ai/<pkg>` ⇒ 这一支抛（`resolve` 折叠 `..` 后命中）。
  //     ⇒ **别再把这一支当成"接线漏传也拦得住"的证据**。真正的落点判据是 `purityPlugin()` 里的
  //     `resolveLanding()`（esbuild 真解析 + realpath）；本支只是"没有 build 对象时"的粗兜底，
  //     供单元级调用与可读诊断用。
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
 * ⚠ **这套门禁盖不到的地方**（复核 2026-09-20 实测 + 第四轮 corr3 更新 + 第五轮 2026-09-20 更正，
 * 写在这里免得被当成"全覆盖"）：
 *
 * 1. ~~门禁是**在解析（onResolve）时**触发的 —— 于是**没有被产物引用**的 import（被 tree-shaking
 *    摇掉、或写在永不执行的分支里）**不会触发**它（实跑 exit 0）。~~ ⇒ **第五轮更正（本轮实跑，
 *    这句话把覆盖说小了、还把两种情形混为一谈）**：
 *      - **tree-shaken 的静态 `import`** —— **照样触发**门禁（实测 THREW）。tree-shaking 发生在
 *        **解析之后**（esbuild 必须先解析出模块才能判断有没有副作用），所以"源码里写了、产物里没用到"
 *        的静态 import **拦得住**；
 *      - **dead branch 里的动态 `import()`** —— **不触发**（实跑 exit 0）。这是**唯一**站得住的那种：
 *        死分支根本不进图，esbuild 压根不解析它。
 *      ⇒ 正确的边界：门禁管"**会被解析到的** import"，**不是**"产物里最终留下的"；也不是
 *        "源码里不许写错包名"（静态扫描仍未做，别冒领）。
 *
 * 2. ~~filter 只覆盖"**说明符文本**里带 `@deepseek-ai` / `..` / `react`"的那些。~~ ⇒ **第五轮更正**：
 *    那条 filter 已经**放宽**到"含路径分隔符/相对前缀/绝对路径/短名/我们的 scope/react"，
 *    并且判定改成"**让 esbuild 解析、按真实落点（realpath）判**"，所以下面这条**旧结论不成立**：
 *      - 旧话（错）：~~落点检查是**跟在 filter 之后**的，所以：把宿主单例**拷进源码树**再用纯
 *        相对路径引（如 `./vendor/deepseek-ai-values.js`）**不触发**门禁 —— 那已经不是同一个模块
 *        路径了，属另一个口径（"源码里有没有第二份实现"），未做。~~
 *      - 现状（对）：`./vendor/…` 这种**本地**相对路径**会**进 filter、**会**被解析，落点不在
 *        `node_modules/**` ⇒ 判 `bundle`、不误伤（冒烟有这条负面对照）。**仍然**盖不到的是
 *        "**把宿主单例的源码复制进源码树**"——那时**模块路径确实不是同一个**，属另一个口径
 *        （"源码里有没有第二份实现"，未做）。这条边界**没变**，变的只是"filter 盖不到相对路径"。
 *
 * 3. **junction / symlink**（第五轮更正：旧话把这判成"不是真洞"，是错的）：
 *    `./dsh-util-values/lib/index.js`（`dsh-util-values` = 指向 `node_modules/@deepseek-ai/dsh-util-values`
 *    的 **junction**）**当时确实是个洞**：esbuild 的 metafile 报出的 input **逐字就是**
 *    `node_modules/@deepseek-ai/dsh-util-values/lib/index.js` —— **同一个模块路径**，不是什么"另一个口径"。
 *    第五轮起由"解析 + realpath"覆盖（实测被拦）。
 *
 * 4. **仍未做**：源码级静态扫描（"源码里有没有第二份实现"/"有没有写错包名"，不管它会不会被解析到）。
 *    本门禁到"解析层"为止。
 */
