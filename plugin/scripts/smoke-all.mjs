/**
 * ks-dsh-plugin — scripts/smoke-all.mjs
 *
 * **冒烟全链的唯一入口**（`npm run smoke` 现在就是它；名单的**唯一所有者**也在这里）。
 *
 * ## 为什么要把 `&&` 长链换成一个 runner（2026-09-19，有实测代价）
 * 原来的 `smoke` 是 package.json 里一条 25 段的 `&&` 链：**它不拿门禁锁**。
 * 于是"绕过 `run-gates.ps1` 直接跑冒烟"这条路完全不受保护 —— 而本轮的 `-Full` 里
 * `smoke-chatmode` 就红了 `172/173`，事后追出当时**复核子代理正在并发跑冒烟**，
 * 它走的正是这条路。⇒ 假红的成因是机器级资源争用，**锁就必须盖住跑冒烟的每一条路**。
 *
 * runner 做的三件事（都很小，但都是"靠人记得"换不来的）：
 *   1. **取锁**（与 `run-gates.ps1` 同一个锁文件、同一套语义；再入由 `KS_GATES_LOCK_HELD` 开关）；
 *   2. 顺序跑名单、**流式转发输出**（失败时人仍然看得到是哪一条红了）；
 *   3. 第一条失败即停、**以它的退出码退出**，并在 `finally` 里放锁。
 *      ⚠ 边界（复核 2026-09-19 指出我原来写过头了）：`finally` 覆盖的是**异常与 `return`**，
 *      **不覆盖**信号杀进程（Node 的默认 SIGINT 处理不走 JS 展开）⇒ 真 Ctrl-C 可能留下陈旧锁；
 *      代价可控：下次取锁会按 pid 判死清掉它（`gate-lock.mjs` 的 `alive()`）。**我没有在 Windows
 *      上实测过真 Ctrl-C**，所以这句只当"预期"读。
 *
 * ⚠ 名单顺序有含义：**最快能发现破坏的排前面**（类型/契约类在前，渲染类在后）。
 *   加新冒烟请加在这个数组里，别再往 package.json 里拼 `&&`。
 */

import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

import { acquireGateLock, contentionMessage } from './gate-lock.mjs'

/** 顺序即优先级：越早失败越省时间。 */
const SUITES = [
  'scripts/smoke-pdf-fit.mjs',
  'scripts/smoke-pdf-panel.mjs',
  'scripts/smoke-settings.mjs',
  'scripts/smoke-settings-guard.mjs',
  'scripts/smoke-effect-tool.mjs',
  'scripts/smoke-chatmode.mjs',
  'scripts/smoke-ingest.mjs',
  'scripts/smoke-lifecycle.mjs',
  'scripts/smoke-engine-guard.mjs',
  'scripts/smoke-client-entry.mjs',
  'scripts/smoke-build-purity.mjs',
  'scripts/smoke-docimage.mjs',
  'scripts/smoke-sanitize.mjs',
  'scripts/smoke-trim.mjs',
  'scripts/smoke-materials-tool.mjs',
  'scripts/smoke-materials-routes.mjs',
  'scripts/smoke-collect-tool.mjs',
  'scripts/smoke-collect-ui.mjs',
  'scripts/smoke-report-routes.mjs',
  'scripts/smoke-report-ui.mjs',
  'scripts/smoke-draft-ui.mjs',
  'scripts/smoke-catalog-ui.mjs',
  'scripts/smoke-channels-routes.mjs',
  'scripts/smoke-anchor-mark.mjs',
  'scripts/smoke-class-summary.mjs',
  'scripts/smoke-kb-page-render.mjs',
  'scripts/smoke-ui-scale.mjs',
  // 第 6 步 A 批（2026-10）：取消/超时可分辨 + 监听摘净（全离线、不 spawn 引擎），
  // 以及 6 个工具的 isConcurrencySafe 声明形态。两条都属"最快能发现破坏"那一档：
  // 前者红了说明排障时又分不清"用户点停止"和"引擎太慢"，后者红了说明并行静默失效。
  'scripts/smoke-cancel.mjs',
  'scripts/smoke-tool-concurrency.mjs',
]

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = dirname(here)

const lock = acquireGateLock('smoke')
if (!lock.ok) {
  console.error(contentionMessage(lock.holder))
  process.exit(3)
}

let failed = null
try {
  console.log(`=== smoke 全链：${SUITES.length} 套（锁 ${lock.held ? '已取' : '由父进程持有'}）===\n`)
  for (const suite of SUITES) {
    console.log(`── ${suite} ──`)
    const r = spawnSync(process.execPath, [join(pluginRoot, suite)], {
      cwd: pluginRoot, stdio: 'inherit', env: process.env,
    })
    if (r.status !== 0) {
      failed = { suite, code: r.status ?? 1 }
      break
    }
  }
} finally {
  lock.release()
}

if (failed) {
  console.error(`\n⛔ smoke 全链失败于 ${failed.suite}（exit=${failed.code}）`)
  process.exit(failed.code)
}
console.log(`\n✅ smoke 全链 ${SUITES.length}/${SUITES.length} 套全过`)
