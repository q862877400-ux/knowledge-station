/**
 * ks-dsh-plugin — scripts/smoke-tool-catalog.mjs
 *
 * 尾件 1/4（批3，dsh-adopt §50.3）：**生成式工具目录 + 防漂移门禁**。
 * 目录 `docs/tool-catalog.md` **从真工具定义生成**（六件的 name/description/参数表——
 * 手抄件必然漂移，本仓教训史）；本脚本双模式：
 *   `node scripts/smoke-tool-catalog.mjs`        —— 生成 → 与仓库内目录**比对**，漂移即 exit 1；
 *   `node scripts/smoke-tool-catalog.mjs --write` —— 重新生成并写回（改了说明书就跑它）。
 * 判据即门禁：说明书改动后忘了更新目录 ⇒ 红（防漂移）；目录手改 ⇒ 红（生成物不许手编）。
 *
 * 用法：node scripts/smoke-tool-catalog.mjs [--write]   （退出码 0 = 无漂移）
 */
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const repoRoot = resolve(pluginRoot, '..')
const OUT = join(repoRoot, 'docs', 'tool-catalog.md')

const idx = await import('../src/index.js')
const collectMod = await import('../src/collect.js')
const materialsMod = await import('../src/materials.js')

const stub = {}
const tools = [
  idx.makeAnswerTool(stub, () => ({})),
  idx.makeResolveTool(stub, () => ({})),
  idx.makeEffectReportTool(stub, () => ({})),
  collectMod.makeCollectTool(stub, () => ({})),
  materialsMod.makeMaterialsTool(stub),
  idx.makePingTool(stub),
].sort((a, b) => a.name.localeCompare(b.name))

function paramsOf(tool) {
  const props = tool.parameters?.properties ?? {}
  const required = new Set(tool.parameters?.required ?? [])
  return Object.entries(props).map(([name, spec]) => {
    const type = Array.isArray(spec?.enum) ? `enum(${spec.enum.join('/')})` : (spec?.type ?? 'any')
    return `| \`${name}\`${required.has(name) ? '（必填）' : ''} | ${type} | ${String(spec?.description ?? '').replace(/\|/g, '\\|')} |`
  })
}

function buildCatalog() {
  const lines = []
  lines.push('# ks-dsh-plugin 工具目录（生成物——**手改必红**，改说明书后跑 `node plugin/scripts/smoke-tool-catalog.mjs --write`）')
  lines.push('')
  lines.push('> 六件模型工具的说明书与参数表，**从真工具定义生成**（防漂移门禁 = 本目录与定义逐字比对）。')
  lines.push('')
  for (const tool of tools) {
    lines.push(`## ${tool.name}（说明书 ${String(tool.description.length)} 字）`)
    lines.push('')
    lines.push(tool.description)
    lines.push('')
    lines.push('| 参数 | 类型 | 说明 |')
    lines.push('|---|---|---|')
    lines.push(...paramsOf(tool))
    lines.push('')
  }
  return lines.join('\n')
}

const generated = buildCatalog()
const writeMode = process.argv.includes('--write')
if (writeMode) {
  await writeFile(OUT, generated, 'utf8')
  console.log(`== tool-catalog 已写 ${OUT}（${String(generated.length)} 字）==`)
  process.exit(0)
}

let existing = null
try {
  existing = await readFile(OUT, 'utf8')
} catch {
  console.log('FAIL  docs/tool-catalog.md 不存在——先跑 --write 生成（生成物从真定义来，不许手写）')
  process.exit(1)
}
if (existing === generated) {
  console.log(`== tool-catalog smoke PASS（目录与真工具定义逐字一致，${String(tools.length)} 件）==`)
  process.exit(0)
}
console.log('FAIL  docs/tool-catalog.md 与真工具定义**漂移**（说明书改了没重新生成？）')
console.log(`  仓库 ${String(existing.length)} 字 / 生成 ${String(generated.length)} 字`)
console.log('  修法：node plugin/scripts/smoke-tool-catalog.mjs --write（生成物更新后一起提交）')
process.exit(1)
