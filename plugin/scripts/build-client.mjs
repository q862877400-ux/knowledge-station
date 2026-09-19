/**
 * ks-dsh-plugin — scripts/build-client.mjs
 *
 * 把 plugin/client/*（TS/TSX）打包成 DSH 浏览器 client 单文件 client.js：
 *   window.__ModuleLoader__.load({ id:'ks-dsh-plugin', factory:(require)=>{...}})
 * - react / react-dom / **允许清单内的** `@deepseek-ai/*` 保持 external（由 loader 的 require 提供）；
 *   ⚠ 清单内**没有**的 `@deepseek-ai/*` ⇒ **构建当场失败**（纯度门禁，见
 *   `scripts/lib/external-allowlist.mjs`）；以前是整片 `@deepseek-ai/*` external，引错包不报错。
 * - pdfjs-dist 打进产物（loader 不提供它）；worker 走 host 路由 /ks/assets/pdf.worker.min.mjs；
 * - **JSX 走 automatic runtime**（`react/jsx-runtime` 的 `_jsx`），**不是** classic
 *   `React.createElement`：本文件里的 `jsx:'transform'/jsxFactory` 只是 API 默认，
 *   会被 `client/tsconfig.json` 的 `"jsx": "react-jsx"` 覆盖（独立复核 2026-09-17 实测：
 *   产物里 9× `require("react/jsx-runtime")`、561× `_jsx`，只有 3× 手写的 `React.createElement`）。
 *   ⇒ 含 JSX 的模块**仍需** `import * as React from 'react'`（各组件本来就有），
 *   但**不要**以为产物里能看到 `React.createElement`。旧注释写的是 classic，与事实不符。
 * 用法：node scripts/build-client.mjs（cwd=plugin 根）。
 * ⚠ `KS_CLIENT_OUT` 可把产物写到别处（默认仍是 `plugin/client.js`）：这是给**冒烟**用的——
 *   `smoke-client-entry.mjs` 要"从源码现构建一份"来与仓库里的产物**比关键标记**，
 *   而**不能**在跑门禁时覆盖被跟踪的 `client.js`（复核 b11 的 LOW-3：只查产物里的文案
 *   是**空闸门**——把产物里的条件改掉、别的都不动，门禁照样全绿）。
 */
import { build } from 'esbuild'
import { readFile, writeFile, rm } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

import { classifyExternal, PURITY_ONRESOLVE_FILTER } from './lib/external-allowlist.mjs'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const TMP = join(root, '.client.tmp.js')
const OUT = process.env.KS_CLIENT_OUT
  ? resolve(process.env.KS_CLIENT_OUT)
  : join(root, 'client.js')
const entry = join(root, 'client', 'entry.ts')

const HEADER = `window.__ModuleLoader__.load({
  id: 'ks-dsh-plugin',
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
`
const FOOTER = `
    return module.exports;
  },
});
`

await build({
  entryPoints: [entry],
  outfile: TMP,
  // ⚠ **显式固定 `absWorkingDir`**（§10.99 实测的一个坑）：esbuild 会把**相对 `absWorkingDir`**
  // 的模块路径写进产物注释（`// client/entry.ts` vs `// plugin/client/entry.ts`）——而它默认取
  // **调用方的 cwd**。于是同一份源码在不同调用姿势下产出**不同字节**的 `client.js`：
  // `npm run build:client`（cwd=plugin）与 `node plugin/scripts/build-client.mjs`（cwd=仓库根）
  // 就差这一层前缀，害得"交付产物 ↔ 从源码现构建"的整份比较**假红**。
  // 固定成 root 之后，产物与调用方 cwd **无关**（可复现），这也正是"提交进仓库的构建产物"该有的性质。
  absWorkingDir: root,
  bundle: true,
  format: 'cjs',
  platform: 'browser',
  target: ['es2020'],
  jsx: 'transform',
  jsxFactory: 'React.createElement',
  jsxFragment: 'React.Fragment',
  // ⚠ **纯度门禁**（2026-09-19，DSH 适配积压第 4 条）：以前这里是
  //   `external: ['react', 'react-dom', '@deepseek-ai/*']` —— **整片 external**，
  //   于是引一个不存在的 `@deepseek-ai/xxx` 构建**不报错**、运行时才炸。
  //   现在改成 onResolve 逐条判定：允许清单内的保持 external，**不认识的 `@deepseek-ai/*` 当场抛**。
  //   名单与理由见 scripts/lib/external-allowlist.mjs（两份名单各有出处，且有冒烟对着 package.json 核）。
  plugins: [{
    name: 'ks-build-purity',
    setup(build) {
      // ⚠ filter 必须与 `classifyExternal` 同口径 —— 复核 2026-09-20 发现：这里原来**大小写敏感**
      //   （`/^(@deepseek-ai\/|...)/`），于是 `@DeepSeek-AI/x` **根本进不到判定函数里**，
      //   走普通解析。今天恰好 fail-closed（解析不到 ⇒ 构建失败），但 Windows 大小写不敏感，
      //   盘上真有那个包时宿主单例会被静默打进产物 ⇒ 加 `i` 让**所有**大小写变体都进判定，
      //   由 `classifyExternal` 显式拒绝（它现在对非全小写的 scope 直接抛）。
      // ⚠ **第二轮（2026-09-20，复核 r2）**：filter 原来锚在**原串开头**（`^(@deepseek-ai\/|…)`），
      //   于是 `x/../@deepseek-ai/dsh-util-values` **不命中** ⇒ esbuild 归一化后把盘上真包
      //   静默内联（复核实跑 +6785B）。⇒ filter 改成**共享常量** `PURITY_ONRESOLVE_FILTER`
      //   （定义在 `lib/external-allowlist.mjs`，与判定函数同一份文件，别再各写一份）：
      //   它宽到足以把任何"可能被归一化进受管范围"的 specifier 送进判定；命中的普通包
      //   由 `classifyExternal` 返回 `'bundle'` ⇒ onResolve 返回 undefined ⇒ 照旧默认解析。
      build.onResolve({ filter: PURITY_ONRESOLVE_FILTER }, (args) => {
        const verdict = classifyExternal(args.path)   // 不在清单里的 `@deepseek-ai/*` 会在这里抛
        return verdict === 'external' ? { path: args.path, external: true } : undefined
      })
    },
  }],
  // pdfjs-dist 打进产物（不 external；`classifyExternal` 对它返回 'bundle'）
  logLevel: 'warning',
})

let body = await readFile(TMP, 'utf8')
body = body.replace(/^"use strict";\s*/m, '')
const out = HEADER + body + FOOTER
await writeFile(OUT, out, 'utf8')
await rm(TMP, { force: true })
console.log(`client.js written: ${Buffer.byteLength(out, 'utf8')} bytes`
  + ` (${out.length} chars)`)   // ⚠ `out.length` 是**字符数**不是字节数：产物里有大量 CJK，
                                //    两者差 ~1500（§10.92 的复核 LOW 就是因为这里把字符数
                                //    当字节数打印，文档照抄后与 git blob 大小对不上）
