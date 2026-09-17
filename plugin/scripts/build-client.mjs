/**
 * ks-dsh-plugin — scripts/build-client.mjs
 *
 * 把 plugin/client/*（TS/TSX）打包成 DSH 浏览器 client 单文件 client.js：
 *   window.__ModuleLoader__.load({ id:'ks-dsh-plugin', factory:(require)=>{...}})
 * - react / react-dom / @deepseek-ai/* 保持 external（由 loader 的 require 提供）；
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
  bundle: true,
  format: 'cjs',
  platform: 'browser',
  target: ['es2020'],
  jsx: 'transform',
  jsxFactory: 'React.createElement',
  jsxFragment: 'React.Fragment',
  // loader 提供的外部模块：react、react-dom、@deepseek-ai/*
  external: ['react', 'react-dom', '@deepseek-ai/*'],
  // pdfjs-dist 打进产物（不 external）
  logLevel: 'warning',
})

let body = await readFile(TMP, 'utf8')
body = body.replace(/^"use strict";\s*/m, '')
const out = HEADER + body + FOOTER
await writeFile(OUT, out, 'utf8')
await rm(TMP, { force: true })
console.log(`client.js written: ${out.length} bytes`)
