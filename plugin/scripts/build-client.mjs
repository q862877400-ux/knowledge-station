/**
 * ks-dsh-plugin — scripts/build-client.mjs
 *
 * 把 plugin/client/*（TS/TSX）打包成 DSH 浏览器 client 单文件 client.js：
 *   window.__ModuleLoader__.load({ id:'ks-dsh-plugin', factory:(require)=>{...}})
 * - react / react-dom / @deepseek-ai/* 保持 external（由 loader 的 require 提供）；
 * - pdfjs-dist 打进产物（loader 不提供它）；worker 走 host 路由 /ks/assets/pdf.worker.min.mjs；
 * - classic JSX（React.createElement），entry 与含 JSX 的模块需有 React 命名空间导入。
 * 用法：node scripts/build-client.mjs（cwd=plugin 根）。
 */
import { build } from 'esbuild'
import { readFile, writeFile, rm } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const TMP = join(root, '.client.tmp.js')
const OUT = join(root, 'client.js')
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
