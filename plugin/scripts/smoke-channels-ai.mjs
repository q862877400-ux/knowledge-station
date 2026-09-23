/**
 * ks-dsh-plugin — scripts/smoke-channels-ai.mjs
 *
 * 渠道台账「分类 + AI 一键解决」判据（2026-09-22 业主点单）：
 *   ① 分类 = `groupRowsByCategory` 纯函数：组序=类别声明序、未知收尾、组内保持传入序；
 *   ② 「AI 一键解决」提示词 = `buildChannelFixPrompt` 纯函数：只列问题渠道、六要素逐字在
 *      （诊断为什么失败/怎么修才行/怎么长期有效/需要用户怎么协助/修复时用什么工具/边界纪律）、
 *      真路径在（CHANNEL-COVERAGE-PLAN / src/core/laws / channels/probe / 两条测试）；
 *   ③ 面板真点击：jsdom 挂载 + stub fetchChannels ⇒ 分组标题渲染、点「AI 一键解决」⇒
 *      剪贴板收到提示词 + 反馈「提示词已复制」；clipboard 缺席走 textarea 回退。
 * 变异口径：五要素删一行 ⇒ ②红；组序排序删除 ⇒ ①红；按钮不写剪贴板 ⇒ ③红。
 *
 * 用法：node scripts/smoke-channels-ai.mjs   （退出码 0 = 全绿）
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

let passed = 0
let failed = 0
function check(name, cond, detail = '') {
  if (cond) {
    passed += 1
    console.log(`PASS  ${name}${detail ? ` — ${detail}` : ''}`)
  } else {
    failed += 1
    console.log(`FAIL  ${name}${detail ? ` — ${detail}` : ''}`)
  }
}

// jsdom 本仓没装——照 smoke-turn-tab 惯用法从 DSH 检出引（KS_HARNESS_DIR 可覆盖）。
const harness = process.env.KS_HARNESS_DIR ?? 'D:\\AI\\DSH\\deepseek-harness'
const jsdomDir = join(harness, 'node_modules', 'jsdom')
const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {
  url: 'https://ks.test/',
  pretendToBeVisual: true,
})
// Node 26 的全局 navigator 是只读 getter ⇒ 一律 defineProperty 安全挂。
for (const [k, v] of Object.entries({
  window: dom.window, document: dom.window.document, navigator: dom.window.navigator,
  HTMLElement: dom.window.HTMLElement, MouseEvent: dom.window.MouseEvent,
})) {
  Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true })
}

let React, renderToStaticMarkup
try {
  React = (await import('react')).default ?? (await import('react'))
  ;({ renderToStaticMarkup } = await import('react-dom/server'))
} catch {
  console.log('skip: react 不可用（按门禁口径不算失败面）')
  process.exit(0)
}

// bundle 必须落**仓内**（node_modules/.tmp-*）：外部 react/react-dom 要能从仓根解析到，
// 放 %TEMP% 会 ERR_MODULE_NOT_FOUND（2026-09-22 实测）；.tmp 在 node_modules 下不脏树。
const tmp = await mkdtemp(join(pluginRoot, 'node_modules', '.tmp-channels-ai-'))
try {
  const entry = join(tmp, 'entry.mjs')
  await writeFile(entry,
    `export * from ${JSON.stringify(join(pluginRoot, 'client', 'KsChannelsPanel.tsx'))}\n`, 'utf8')
  const out = join(tmp, 'bundle.mjs')
  await build({
    entryPoints: [entry], bundle: true, outfile: out, format: 'esm', platform: 'node',
    external: ['react', 'react-dom', 'react-dom/server', 'react/jsx-runtime'],
    loader: { '.css': 'empty' }, jsx: 'automatic', logLevel: 'silent',
  })
  const mod = await import(pathToFileURL(out).href)

  /* ── ① 分类：groupRowsByOrgKind（业主定案：分类=主办单位性质，文件夹树） ── */
  const rec = (id, org_kind, state = 'ok', extra = {}) => ({
    channel_id: id, name: id, category: 'other', org_kind, wiring: 'wired',
    verification: 'verified', state, enabled: 1, consecutive_failures: 0, ...extra,
  })
  const groups = mod.groupRowsByOrgKind([
    rec('g2-row1', 'local_dept'), rec('law1', 'central'), rec('g2-row2', 'local_dept'),
    rec('odd1', null), rec('gb1', 'local_congress'),
  ])
  check('分类：组序 = 单位性质声明序（国家部委→地方人大→地方厅局），未分类收尾',
    groups.map((g) => g.key).join(',') === 'central,local_congress,local_dept,',
    groups.map((g) => g.key).join(','))
  check('分类：组内保持传入序 + 计数对',
    groups[2].rows.map((r) => r.channel_id).join(',') === 'g2-row1,g2-row2' && groups[2].rows.length === 2,
    JSON.stringify(groups.map((g) => `${g.label}:${g.rows.length}`)))
  check('分类：未分类组名就叫「未分类」（不编不存在的字段）',
    groups[3].label === '未分类', groups[3].label)

  /* ── ② 提示词：buildChannelFixPrompt ──────────────────────── */
  const rows = [
    rec('ok-clean', 'central', 'ok'),
    rec('坏渠道甲', 'local_dept', 'down', { url: 'https://a.example/坏', last_error: 'HTTP 404',
      last_error_code: 'http_404', consecutive_failures: 5, note: '改版了' }),
    rec('可疑乙', 'industry', 'suspicious', { consecutive_failures: 2 }),
    rec('未探丙', 'tool', 'unknown', { has_probe_target: true }),
  ]
  const prompt = mod.buildChannelFixPrompt(rows, {
    total: 4, by_state: { ok: 1, suspicious: 1, down: 1, unknown: 1 }, by_wiring: { wired: 4 },
  })
  check('提示词：三条问题渠道都在（down/suspicious/unknown）',
    ['坏渠道甲', '可疑乙', '未探丙'].every((n) => prompt.includes(n)),
    `len=${String(prompt.length)}`)
  check('提示词：干净的 ok 渠道不进问题清单', !prompt.includes('ok-clean'))
  check('提示词：问题条带真实错误与备注（喂的是台账真字段）',
    prompt.includes('http_404') && prompt.includes('改版了') && prompt.includes('https://a.example/坏'))
  check('提示词：六要素逐字在（诊断/修法/长期/协助/工具/边界）',
    prompt.includes('诊断为什么失败') && prompt.includes('怎么修才行')
    && prompt.includes('怎么长期有效') && prompt.includes('需要用户怎么协助')
    && prompt.includes('修复时用什么工具') && prompt.includes('边界与纪律'))
  check('提示词：真路径在（方案文档/适配器目录/探测端点/两条测试）',
    prompt.includes('docs/CHANNEL-COVERAGE-PLAN.md') && prompt.includes('src/core/laws/')
    && prompt.includes('POST /api/v1/channels/probe')
    && prompt.includes('tests/test_channel_repo.py') && prompt.includes('tests/test_ledger_chain.py'))
  check('提示词：纪律句在（修不动如实说 / 不替用户决定）',
    prompt.includes('如实说修不动') && prompt.includes('不要默默替他做决定'))

  /* ── ③ 面板真点击（jsdom 挂载 + stub 数据 + 剪贴板） ───────── */
  const { createRoot } = await import('react-dom/client')
  const { act } = await import('react')
  const host = dom.window.document.getElementById('root')
  const root = createRoot(host)
  const copied = []
  Object.defineProperty(dom.window.navigator, 'clipboard', {
    value: { writeText: async (t) => { copied.push(t) } }, configurable: true,
  })
  globalThis.fetch = async (url) => {
    const u = String(url)
    if (u.includes('/ks/channels')) {
      return { ok: true, status: 200, headers: { get: () => 'application/json' },
        json: async () => ({ ok: true, data: { summary: { total: 4,
          by_state: { ok: 1, suspicious: 1, down: 1, unknown: 1 }, by_wiring: { wired: 4 }, enabled: 4 },
          items: rows } }) }
    }
    return { ok: false, status: 404, headers: { get: () => 'application/json' },
      json: async () => ({ ok: false, message: 'no' }) }
  }
  await act(async () => {
    root.render(React.createElement(mod.KsChannelsPanel, { visible: true }))
  })
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
  const html = () => host.innerHTML
  check('正装：目录层=知识库同款机制（.ks-list-dirs 容器 + .ks-dir-open/.ks-dir-go 行件）',
    html().includes('ks-list-dirs') && html().includes('ks-dir-open') && html().includes('ks-dir-go'),
    '手搓回潮 ⇒ 本条红')
  check('面板：目录层按单位性质分行（名称 + 条数）',
    html().includes('国家部委/总局') && html().includes('地方厅局') && /\d+ 条/.test(html()),
    `组行数=${String((html().match(/ks-dir-row/g) ?? []).length)}`)
  const btn = [...host.querySelectorAll('button')]
    .find((b) => (b.textContent ?? '').includes('AI 一键解决'))
  check('面板：「AI 一键解决」按钮在', btn !== undefined, btn?.textContent?.trim() ?? '缺')
  await act(async () => { btn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })) })
  await act(async () => { await new Promise((r) => setTimeout(r, 10)) })
  check('点击：提示词进剪贴板（含失效渠道名）',
    copied.length === 1 && copied[0].includes('坏渠道甲'),
    `copies=${String(copied.length)} len=${String(copied[0]?.length ?? 0)}`)
  check('点击：反馈「提示词已复制」可见', html().includes('提示词已复制'))
  // 回退路：剪贴板缺席 ⇒ textarea+execCommand 仍成
  delete dom.window.navigator.clipboard
  dom.window.document.execCommand = () => true
  const ok2 = await mod.copyTextToClipboard('回退样本文本')
  check('复制回退：clipboard 缺席时 textarea+execCommand 仍成', ok2 === true)

  console.log(`\n== channels-ai smoke ${failed === 0 ? 'PASS' : 'FAIL'} (${passed}/${passed + failed}) ==`)
} finally {
  await rm(tmp, { recursive: true, force: true })
}
process.exit(failed === 0 ? 0 : 1)
