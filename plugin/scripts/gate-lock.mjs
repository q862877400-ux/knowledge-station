/**
 * ks-dsh-plugin — scripts/gate-lock.mjs
 *
 * 门禁锁（**与 `scripts/run-gates.ps1` 共用同一个锁文件与同一套语义**）。
 *
 * ## 为什么冒烟自己也要拿锁（2026-09-19，有实测代价）
 * 锁此前只在 `run-gates.ps1` 里 ⇒ **绕过脚本直接跑冒烟就完全不受保护**。
 * 这一轮的 `-Full` 里 `smoke-chatmode` 红了 `172/173`（AGENTS.md 记录过的同型假红），
 * 事后追下来，当时机器上还有**复核子代理在并发跑冒烟** —— 它走的是 `npm run smoke` /
 * 单个 `node scripts/smoke-*.mjs`，**不经过 `run-gates.ps1`，所以锁根本拦不住它**。
 * ⇒ 结论：**假红的成因是机器级资源争用，锁就必须盖住"跑冒烟的每一条路"**，
 * 而不是只盖住"我们推荐的那一条路"。
 *
 * ## 语义（与 ps1 逐字一致，两个入口必须能互相看懂对方的锁）
 * - 锁文件：`$TEMP/ks-gates.lock`，内容 `{pid, startedAt, mode}`（JSON）；
 * - 持有者 pid **还活着** ⇒ 拒绝并返回「已被占用」；已不在 ⇒ 清掉陈旧锁再取；
 * - `KS_GATES_LOCK_HELD=1` ⇒ **不再取锁**：那是 `run-gates.ps1` 已经替我们拿过了
 *   （父进程拿锁、子步骤再拿一次会**自我阻塞**，这是必须留的再入开关）。
 */

import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

export const LOCK_PATH = join(tmpdir(), 'ks-gates.lock')

/** 进程是否还活着（`kill(pid,0)` 不发信号，只做权限/存在性检查）。 */
function alive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch (err) {
    // EPERM = 进程存在但不属于我（Windows 上少见）；ESRCH = 不存在
    return err?.code === 'EPERM'
  }
}

export function readLock() {
  try {
    return JSON.parse(readFileSync(LOCK_PATH, 'utf8'))
  } catch {
    return null
  }
}

/**
 * 取锁。返回 `{ok, held, release, holder}`：
 * - `ok=false` ⇒ 别人正拿着（调用方应**不跑**并以退出码 3 结束，与 ps1 同一约定）；
 * - `held=false` ⇒ 没取（再入：父进程已持有），`release` 是空操作，**别去删别人的锁**。
 */
export function acquireGateLock(mode) {
  if (process.env.KS_GATES_LOCK_HELD === '1') {
    return { ok: true, held: false, holder: null, release() {} }
  }
  const prev = readLock()
  if (prev && alive(Number(prev.pid))) {
    return { ok: false, held: false, holder: prev, release() {} }
  }
  mkdirSync(tmpdir(), { recursive: true })
  writeFileSync(LOCK_PATH, JSON.stringify({
    pid: process.pid,
    startedAt: new Date().toISOString().slice(0, 19),
    mode: mode ?? 'smoke',
  }), 'utf8')
  let released = false
  const release = () => {
    if (released) return
    released = true
    // 只删**自己**写的那把：父进程的锁（再入情形）不该被我们删掉。
    if (readLock()?.pid === process.pid) rmSync(LOCK_PATH, { force: true })
  }
  return { ok: true, held: true, holder: null, release }
}

/** 统一的拒绝文案（与 ps1 里那句同义，便于人一眼认出是同一件事）。 */
export function contentionMessage(holder) {
  return `⛔ 已经有一个门禁在跑（pid=${holder?.pid}，起于 ${holder?.startedAt}）。\n`
    + '   并发跑门禁会制造**假红**（见 AGENTS.md 的门禁一节）⇒ 这次**不跑**，退出码 3。'
}
