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
 *
 * ## ⚠⚠ 本机环境事实：`spawnSync` 的 **stdin 不能是 pipe**（2026-10-09 第 17 轮实测）
 *
 * **现象**：`spawnSync(exe, args, { encoding: 'utf8' })`（= 默认 `stdio: 'pipe'`）在本机
 *   **恒返回 `{ status: null, error: { code: 'EBUSY' } }`** —— 子进程根本没起来、stdout 为空。
 *   实测：连跑 20 次 **20/20 EBUSY**；`execSync` / `execFileSync` 同样 EBUSY；
 *   **换成 async `spawn` 正常**；node **22.22.2 与 26.7.0 都一样**；沙箱内外都一样。
 *
 * ⚠⚠ **就地更正（2026-10-10）—— 上面那段是【当时】的观测，不是【恒成立】的定律。**
 *   当时我自己就在同一段末尾写了"**同一棵树不同时刻表现不同**"，两句并存会让后人
 *   把"今天不复现"读成"改错了"。**2026-10-10 复测（同一台机、node v26.7.0）：
 *   三种 `stdio` 形态各 20 次，全部 20/20 正常，EBUSY 出现 0 次**
 *   （默认 / 显式 `['pipe','pipe','pipe']` / `['ignore','pipe','pipe']`；
 *   子进程分别取"空脚本""真起 http server 的脚本""会读 stdin 的脚本"三种形态都试过）。
 *   探针：`var/tmp/probe-spawnsync.cjs` 与 `var/tmp/probe-spawnsync2.cjs`。
 *   ⇒ **能站住的是**：① 2026-10-09 19:05 那一跑确实 20/20 EBUSY（当时有读数）；
 *     ② 显式 `['ignore','pipe','pipe']` 是**安全的**（今天复测同样 20/20 正常）⇒ 保留它没有代价。
 *   ⇒ **站不住的是**："恒 EBUSY"这个**全称句**（已被 2026-10-10 复测证伪）。
 *     后人在**别的机器/别的时间**遇到 EBUSY 时，别把它当"本仓已知回归"，
 *     先按 `docs/TEST-FLAKES.md` 的纪律**取率**（N≥10）再定性。
 *   ⚠ 本轮**不改**这些调用点：`['ignore','pipe','pipe']` 复测无害，改了只会制造无谓 diff。
 *
 * **规避（已逐个落到调用点）**：把 `stdio` 显式写成 **`['ignore', 'pipe', 'pipe']`**
 *   （只让 **stdin** 不是 pipe；stdout/stderr 仍是 pipe，照旧能抓输出）⇒ 实测 5/5 正常。
 *   ⚠ **`stdin: 'ignore'` 这个简写【不管用】**（实测仍 EBUSY），必须写整个 `stdio` 数组。
 *
 * **为什么这些子进程可以不要 stdin**：本链里被 spawn 的都是"跑完就退出"的脚本/浏览器，
 *   没有一条读标准输入 ⇒ 这是**语义等价**的改动，**不是把断言放松**（断言一个字没动）。
 *
 * **受影响并已改的调用点**：`smoke-lifecycle.mjs`（D5/D6 子进程）、`smoke-build-purity.mjs`、
 *   `smoke-kb-cols.mjs`、`smoke-kb-pad-pixels.mjs`、`ui-badge-pixels.mjs`、`ui-render-shot.mjs`
 *   （`runBrowser`）。**本文件下面那个 `spawnSync` 不用改**：它给的是 `stdio: 'inherit'`。
 *
 * ⚠ **这是环境缺陷、不是本仓回归**：上一轮（16:58–17:20）同一棵树跑冒烟时这几套还能过，
 *   19:05 再跑就 100% EBUSY ⇒ 机器状态在这两小时里变了。改法是**让脚本对两种环境都能跑**。
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
  // 第 6 步 §1（2026-10）：6 个模型工具的 `output.schema` 契约（schema 在宿主支持的子集内
  // + 返回值满足自己声明的 schema + 无 undefined + render 给出非空 text 块）。
  // 位置按"最快能发现破坏的排前面"：它是纯离线契约检查（零引擎、秒级），而且红了说明
  // **真机上整个插件挂不上**或**每次调用都 isError**——比渲染类早发现得多。
  'scripts/smoke-tool-contract.mjs',
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
  // UI S1-b（2026-09-22）：「本轮」只读口的暂存/会话隔离/最近一次语义 + 无尾斜杠防呆。
  'scripts/smoke-turn-routes.mjs',
  // UI S1-b（2026-09-22）：「本轮」依据行/空态的渲染级判据（定稿文案逐字 + URL 契约 +
  // 无星号无字面色）。
  'scripts/smoke-turn-tab.mjs',
  // S3-b2（2026-09-22）：备料行级行为判据（免评审行无批准钮 / 地位胶囊真发 role /
  // 批量条逐字 + 逐项真调）。
  'scripts/smoke-materials-rows.mjs',
  // 合规护航 C1（2026-09-22）：哨句唯一出处 / 预判据三组 / 段文两态零增量 / 技能字节同步 /
  // L1 单一出处 / 标准号前缀表跨语言同步。
  'scripts/smoke-compliance-sentry.mjs',
  // 尾件 1/4（批3）：生成式工具目录防漂移（目录=真定义生成物，手改/漏更皆红）。
  'scripts/smoke-tool-catalog.mjs',
  // 渠道台账「分类 + AI 一键解决」（2026-09-22 业主点单）：分组纯函数 + 提示词六要素 + 真点击复制。
  'scripts/smoke-channels-ai.mjs',
  'scripts/smoke-anchor-mark.mjs',
  // UI 批0-a（2026-09-22）：诊断 A2 死开关的判据——设置「显示红色定位箭头」必须**真的**传到
  // 查看器（KsEvidenceHost→KsEvidenceTab 的 prefs 透传；桩回显 props 的行为判据，
  // 宿主写死 showArrow:true 当场红）。纯离线静态渲染，秒级。
  'scripts/smoke-evidence-prefs.mjs',
  // UI 批0-a A1/A8（2026-09-22）：引文坐标缺失/失败的**可见**提示行（渲染级，
  // 纯组件零依赖）。它红了说明"失败又静默了"。
  'scripts/smoke-evidence-warn.mjs',
  'scripts/smoke-class-summary.mjs',
  'scripts/smoke-kb-page-render.mjs',
  'scripts/smoke-ui-scale.mjs',
  /* ⚠ 2026-10-10（spec 008）：**图标体系判据**。
     为什么进链：实测发现 KS 用到的 17 个图标里，**宿主的默认 size 本身就分两档**
     （6 个默认 14、10 个默认 16，见 `ui-primitives/lib/index.js` 各 artwork 的 `size = N`）
     ⇒ 同一排按钮里「返回上一层」(14) 紧挨着「新建下级目录」(16)，**天生不齐**；
     而"记得传 size"这种纪律**已经失败过一次**（本次实测就是证据）。
     ⇒ 变成脚本、进链，不靠人记得。判据见 docs/UI-ICON-SYSTEM.md。 */
  'scripts/smoke-icon-system.mjs',
  // 5j-补（2026-09-20，复核 verify-freeze-5j 打回 E②/H③）：**两条要真浏览器的断言现在进链**。
  //   打回的原话是"`ksPadCheck` 这条像素断言不在任何门禁链里"⇒ 5j 在门禁内的实际保护只有 jsdom 那 5 条
  //   （jsdom 没有布局引擎，判不了"外缘到内容边多少像素"）。两条脚本的位置都放在渲染类之后
  //   （真浏览器，最慢）。
  //   ⚠ **2026-09-21（KB-FOLDER-PLAN 第 3 步）就地更正**：这条注释原来还举了"`.ks-batch` 折行
  //   只有 `--interact kb-select` 会触发"当例子 —— **那两样（批量条 / kb-select 场景）都已随本批删除**，
  //   例子过时了；但"像素断言必须进链"这个结论与代价没变（下面两句仍然成立）。
  //   ⚠ **代价与取舍（有意，别再当疏漏）**：门禁链从这一批起**需要本机有 Chromium/Edge**；
  //   没浏览器时 `ui-render-shot.mjs` 自己报错退出 ⇒ 这几套判失败（**不是跳过**）。
  //   理由：本仓是仓外 bundle，门禁只在本机跑；"浏览器缺了所以不判"正是复核打回的那类假绿。
  //   ⚠ 5j-补×9 起是**三套**（再加下面的 `ui-badge-pixels`）。
  'scripts/smoke-kb-pad-pixels.mjs',
  'scripts/smoke-kb-cols.mjs',
  // 5j-补×9（2026-09-20）：**第三套要浏览器的脚本进链** —— 复核 `verify-freeze-5jx7` 的残余①登记的：
  //   `ui-badge-pixels.mjs`（状态徽章可读性，跑 **light + dark**）一直是**手跑**的。它与刚补的
  //   "深色留边"是同一族缺口（"深浅两套里只有一套被断言"）。P2 那次它真的抓到过东西（深色下徽章文字
  //   与底色同色、可辨像素 6 ≈ 0）⇒ 它的判据是有牙的，只是从没进链。约 +2 次渲染（~20s）。
  'scripts/ui-badge-pixels.mjs',
  // 第 6 步 A 批（2026-10）：取消/超时可分辨 + 监听摘净（全离线、不 spawn 引擎），
  // 以及 6 个工具的 isConcurrencySafe 声明形态。两条都属"最快能发现破坏"那一档：
  // 前者红了说明排障时又分不清"用户点停止"和"引擎太慢"，后者红了说明并行静默失效。
  'scripts/smoke-cancel.mjs',
  'scripts/smoke-tool-concurrency.mjs',
  // 第 6 步 B 批（2026-10）：wire fixture 回放——6 个模型工具的出网请求与
  // `test/fixtures/ks-engine-wire.json` 逐条比对。它红了说明"我们发出去的调用"
  // 与"我们承诺的契约"分叉了（端点改名/多一个请求/少一个字段），真机才炸的那种。
  'scripts/smoke-wire-contract.mjs',
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
