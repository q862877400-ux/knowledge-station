/**
 * run-verify-commands.mjs — 从 DSH 检出根目录运行 verify-commands-real.mjs
 *
 * `verify-commands-real.mjs` 必须 import `@deepseek-ai/cordis`、`@deepseek-ai/dsh-commands`
 * 等工作区包，而它们靠 **tsx 读 DSH 根 tsconfig.base.json 的 paths** 解析（DSH 里根本没有
 * 这些包的 node_modules 软链）。所以 cwd 必须是 DSH 检出根目录 —— 这个包装器负责那件事，
 * 并把「检出不存在 / tsx 不可用」变成明确的错误，而不是一句模块找不到。
 *
 * 环境变量 KS_DSH_CHECKOUT 可覆盖检出路径。
 */

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const target = join(here, 'verify-commands-real.mjs')
const checkout = process.env.KS_DSH_CHECKOUT ?? 'D:\\AI\\DSH\\deepseek-harness'

if (!existsSync(checkout)) {
  console.error(`[verify:commands] DSH 检出不存在: ${checkout}\n`
    + '  设置 KS_DSH_CHECKOUT 指向 deepseek-harness 检出根目录后重试。')
  process.exit(2)
}
if (!existsSync(join(checkout, 'tsconfig.base.json'))) {
  console.error(`[verify:commands] ${checkout} 看起来不是 DSH 检出（缺 tsconfig.base.json）。`)
  process.exit(2)
}
const tsxCli = join(checkout, 'node_modules', 'tsx', 'dist', 'cli.mjs')
if (!existsSync(tsxCli)) {
  console.error(`[verify:commands] DSH 检出里没有 tsx（${tsxCli}）。先在检出根目录跑一次 pnpm install。`)
  process.exit(2)
}

const child = spawn(process.execPath, [join(checkout, 'node_modules', 'tsx', 'dist', 'cli.mjs'), target], {
  cwd: checkout,
  // 不经 shell：本仓库路径含空格（`...\work space\...`），走 shell 会被拆成两个参数
  // （实测 npx+shell:true 报 `ERR_MODULE_NOT_FOUND file:///D:/AI/work`）。
  stdio: 'inherit',
  shell: false,
})
child.on('error', (error) => {
  console.error('[verify:commands] 无法启动 tsx:', error.message)
  process.exit(2)
})
child.on('exit', (code) => process.exit(code ?? 1))
