/**
 * ks-dsh-plugin — client/pdf-configure.ts
 *
 * pdf.js worker wiring for the DSH web environment.
 *
 * pdf.js NEVER renders without a loadable worker: even its "fake worker"
 * (main-thread) fallback pulls the worker module from `GlobalWorkerOptions.workerSrc`.
 * So the worker must be reachable at a URL.
 *
 * Deterministic choice for DSH web (single-file CJS bundle, no separate asset
 * channel): serve the pdf.js worker as an ESM asset from the same-origin DSH
 * web server via the host route /ks/assets/pdf.worker.min.mjs, then point
 * `GlobalWorkerOptions.workerSrc` at it. The URL ends in `.mjs`, so pdf.js
 * constructs a `{ type: 'module' }` worker and opens it same-origin (no CORS
 * on the worker script). This is the primary, deterministic path.
 *
 * ALTERNATIVE (no extra host route, but build-tool dependent): import the
 * worker source as a string (`pdfjs-dist/build/pdf.worker.min.mjs?raw`) and
 * build a Blob URL:
 *     import workerSource from 'pdfjs-dist/build/pdf.worker.min.mjs?raw'
 *     GlobalWorkerOptions.workerSrc = URL.createObjectURL(
 *         new Blob([workerSource], { type: 'text/javascript' }))
 * This works when the bundler emits the worker text into the single-file
 * bundle and pdf.js is happy with a module worker from a Blob. It is left OUT
 * of the shipped code because (a) DSH web bundles through tsdown/ModuleLoader
 * (raw-import support unverified), and (b) pdf.js v5's worker is ESM and a
 * Blob `new Worker(url, {type:'module'})` only works when the worker build is
 * fully self-contained. If you enable it, delete the host worker route and use
 * this helper instead — but VERIFY it in the real dsh first.
 *
 * Both paths are "must verify in the real dsh" items (see NOTES.md §verification).
 */

import { GlobalWorkerOptions } from 'pdfjs-dist'

/** The same-origin path the host serves the worker at (see src/index.js). */
export const PDF_WORKER_PATH = '/ks/assets/pdf.worker.min.mjs'
/** The same-origin DIRECTORY (trailing slash) hosting pdf.js wasm decoders
 *  (openjpeg.wasm / qcms_bg.wasm / jbig2.wasm …). pdf.js builds
 *  `${wasmUrl}${decoder}` — see the host route /ks/assets/pdf-wasm. */
export const PDF_WASM_DIR = '/ks/assets/pdf-wasm/'

let configured = false

/**
 * Idempotently set pdf.js's worker source to the same-origin host route. Call
 * before the first getDocument(); safe to call repeatedly.
 *
 * 批 8 勘误（2026-09-12，tsc -p plugin/client 首次纳入门禁时抓到）：本函数
 * 原有一段 `GlobalWorkerOptions.wasmUrl = …` —— 那是**死代码**：pdfjs 5.x 的
 * GlobalWorkerOptions 只有 workerPort/workerSrc 两个静态属性，wasmUrl 是
 * **DocumentInitParameters**（getDocument 的 per-document 参数）字段，不在
 * 全局 worker 选项上。旧写法读 GlobalWorkerOptions.wasmUrl 恒得 undefined，
 * `undefined === ''` 恒 false，赋值从未执行过；真正的 wasm 路径一直由
 * KsEvidenceTab 的 getDocument({ data, wasmUrl }) per-document 传入（那才是
 * 自始生效的通道）。删死代码，注释改为如实描述。
 *
 * GB/法规扫描 PDF 大量是 JPEG2000 —— wasm 解码器路径缺失会报
 * "OpenJPEG failed to initialize" 且整页空白；worker 源缺失则任何 PDF
 * 都无法渲染（连 fake worker 都要 workerSrc）。
 */
export function configurePdfWorker(): void {
  if (configured) return
  if (typeof window === 'undefined') return
  const origin = window.location.origin
  if (GlobalWorkerOptions.workerSrc === '') {
    GlobalWorkerOptions.workerSrc = new URL(PDF_WORKER_PATH, origin).href
  }
  configured = true
}
