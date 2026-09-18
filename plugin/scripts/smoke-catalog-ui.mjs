/**
 * ks-dsh-plugin — scripts/smoke-catalog-ui.mjs
 *
 * **目录 UI 两条报障**的契约冒烟（2026-09-18）：
 *
 *  A. 「目录浮层自动打开 + 关不掉 + 没开 sidebar 还浮着」（KsEvidenceTab）
 *  B. 「目录里密密麻麻的字，二级三级和文件名长得一样、最后一级没有计数」（KsFilesTab）
 *  C. 顺带钉住交付物按钮的两个**纯函数**（KsMaterialsPanel 的 deliverableKind/folderOf）
 *
 * ## 这层能证明什么、不能证明什么（照实写，免得被当成"证明界面守规矩"）
 * · **能**：纯函数行为（`countDocs` 的递归计数、扩展名→打开方式的映射）；
 *   以及"展开/收起的**唯一出口**"这种**结构级**判据（写法级，能挡误改，挡不住刻意绕过）。
 * · **不能**：真实 DOM 渲染与点击链路。那两条**已经用真机 CDP 验过**
 *   （2026-09-18：`var/tmp/cdp.mjs` + 截图 var/tmp/gui-04…12、report-html.png），
 *   离线门禁里没有浏览器，故这里只留可离线复现的部分。
 *
 * 用法：node scripts/smoke-catalog-ui.mjs   （退出码 0 = 全通过）
 */
import { readFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { rm } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/** 把某个 .tsx 打成 node ESM 再 import（react 走 external：本文件不渲染组件）。 */
async function loadModule(rel) {
  const outfile = join(pluginRoot, `.${rel.replace(/[^a-z0-9]/gi, '_')}.smoke.mjs`)
  await build({
    entryPoints: [join(pluginRoot, rel)],
    bundle: true, platform: 'node', format: 'esm', outfile,
    absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
    external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
    logLevel: 'warning',
  })
  const mod = await import(pathToFileURL(outfile).href)
  await rm(outfile, { force: true })
  return mod
}

const filesMod = await loadModule('client/KsFilesTab.tsx')
const panelMod = await loadModule('client/KsMaterialsPanel.tsx')

/* ------------------------------------------- A. 浮层：只由用户打开 + tab 不在屏上不渲染 */
{
  const src = await readFile(join(pluginRoot, 'client', 'KsEvidenceTab.tsx'), 'utf8')

  check('KsEvidenceTab 定义了 showLeftCol',
    /const showLeftCol =/.test(src))

  // A1 **显示判据三条全在**：用户意图（tocOpen）+ 官方可见性（visible）+ 几何（paneOnScreen）
  const showLine = (src.match(/const showLeftCol =[^\n]*/) ?? [''])[0]
  check('⚠ 浮层显示必须同时受"用户意图 + 官方 visible + 在屏上"三重约束',
    /tocOpen/.test(showLine) && /visible/.test(showLine) && /paneOnScreen/.test(showLine),
    showLine.trim())
  // ⚠ 只查**判据那一行**：文件里其它地方有注释在解释旧规则（含这些字面量），
  //   全文 grep 会把"文档"当成"代码"⇒ 假红（本轮就踩了一次，故收窄）。
  check('旧的"只要模式不是 toc 就显示"判据已从**显示判据**里删除（那正是自动打开的来源）',
    !/leftMode/.test(showLine), showLine.trim())

  // A2 **打开浮层只有一处出口**：`toggleToc(true)` 全文件恰好一次，且在 openLeftCol 里
  const openCalls = src.split('toggleToc(true)').length - 1
  const openFn = src.indexOf('const openLeftCol = useCallback')
  const openFnBlock = openFn >= 0 ? src.slice(openFn, openFn + 900) : ''
  check('⚠ 展开浮层只有 `openLeftCol` 一个出口（两处各写一份就会漂开——本次报障的教训）',
    openCalls === 1 && /toggleToc\(true\)/.test(openFnBlock),
    `toggleToc(true) 出现 ${openCalls} 次`)
  // 收起同理：两行式写法只允许出现在 closeLeftCol 里（头部按钮与 ◀ 都用它）
  const closeCalls = src.split('toggleToc(false)').length - 1
  const closeFn = src.indexOf('const closeLeftCol = useCallback')
  const closeFnBlock = closeFn >= 0 ? src.slice(closeFn, closeFn + 300) : ''
  check('收起浮层同样只有一个出口（closeLeftCol）',
    closeCalls === 1 && /toggleToc\(false\)/.test(closeFnBlock),
    `toggleToc(false) 出现 ${closeCalls} 次`)
  const idiom = (src.match(/setLeftMode\('toc'\)\s*\n\s*toggleToc\(false\)/g) ?? []).length
  check('两行式"回标题目录 + 合上"只出现在 closeLeftCol 里（别处一律调它）',
    idiom === 1 && /setLeftMode\('toc'\)\s*\n\s*toggleToc\(false\)/.test(closeFnBlock),
    `两行式出现 ${idiom} 次`)
  check('面板头部按钮与空态按钮都走这两个出口（不再各写一段）',
    src.includes('onClick={() => openLeftCol(\'files\')}') && src.includes('onClick={closeLeftCol}'))

  // A3 loadEvidence 不再碰列可见性/默认模式（自动打开的另一半来源）
  check('⚠ loadEvidence 里"无证据就把模式设成 files"的那段已删除（否则等于自动展开）',
    !src.includes('if (ev === null && !leftModeTouchedRef.current)'))

  // A4 收起按钮**无条件**渲染（idle 也必须有——否则浮层唯一的关闭入口消失了）
  const collapseIdx = src.indexOf('$tocCollapseBtn')
  const beforeCollapse = collapseIdx > 0 ? src.slice(Math.max(0, collapseIdx - 900), collapseIdx) : ''
  check('⚠ ◀ 收起按钮不再被 `load.status !== \'idle\'` 包着（用户就是卡在这里关不掉的）',
    collapseIdx > 0 && !/\{load\.status !== 'idle' && \(\s*$/.test(beforeCollapse.split('\n').slice(-2).join('\n'))
    && /onClick=\{closeLeftCol\}/.test(src))
}

/* ------------------------------------------- B. 目录计数（纯函数，行为级） */
{
  const f = filesMod.countDocs
  check('KsFilesTab 导出了 countDocs（每级计数的唯一算法）', typeof f === 'function')
  if (typeof f === 'function') {
    const leaf = (n) => ({ name: 'x', items: [], docs: new Array(n).fill({ doc_id: 'd' }) })
    const node = (items, docs = []) => ({ name: 'c', items, docs })
    check('叶子类目：计数 = 自己的文档数', f(leaf(3)) === 3)
    check('空类目 = 0（不是 undefined/NaN）', f(node([])) === 0)
    check('⚠ 父类目 = 自己 + 全部子类目（递归；只数一层就会让上级计数偏小）',
      f(node([leaf(2), node([leaf(4), leaf(1)])], [{ doc_id: 'a' }])) === 8,
      String(f(node([leaf(2), node([leaf(4), leaf(1)])], [{ doc_id: 'a' }]))))
    check('计数不看名字（未细分/未分类这类占位桶照样计数）',
      f({ name: '未细分', items: [], docs: [{ doc_id: 'z' }] }) === 1)
  }

  const src = await readFile(join(pluginRoot, 'client', 'KsFilesTab.tsx'), 'utf8')
  // 每级都要有计数：四级行 + 文档叶
  check('L1/L2/L3 每级都渲染计数（同一枚 $countChip）',
    (src.split('{$countChip}').length - 1) >= 3,
    String(src.split('{$countChip}').length - 1))
  check('L4 类目也渲染计数',
    src.includes('{$countChipL4}') && src.includes('l4.docs.length'))
  const usage = (src.match(/\{countDocs\(/g) ?? []).length
  check('四个层级都调 countDocs（父级计数靠它递归）', usage >= 4, String(usage))
}

/* ------------------------------------------- C. 交付物按钮的两个纯函数 */
{
  const k = panelMod.deliverableKind
  const fo = panelMod.folderOf
  check('KsMaterialsPanel 导出了 deliverableKind / folderOf',
    typeof k === 'function' && typeof fo === 'function')
  if (typeof k === 'function') {
    check('HTML/MD → 新标签直接看（page）',
      k('研究报告-x.html') === 'page' && k('x.htm') === 'page' && k('x.md') === 'page')
    check('Word/PPT → 只能下载一份（binary；浏览器渲染不了）',
      k('研究报告-x.docx') === 'binary' && k('x.pptx') === 'binary' && k('x.pdf') === 'binary')
    check('大小写不敏感（引擎给的名字带中文与大写扩展名都可能）',
      k('X.HTML') === 'page' && k('X.DOCX') === 'binary')
  }
  if (typeof fo === 'function') {
    check('文件夹 = 去掉最后一段（Windows 反斜杠）',
      fo('C:\\Users\\Zegel\\AppData\\Roaming\\KnowledgeStation\\exports\\a.html')
        === 'C:\\Users\\Zegel\\AppData\\Roaming\\KnowledgeStation\\exports',
      fo('C:\\Users\\Zegel\\AppData\\Roaming\\KnowledgeStation\\exports\\a.html'))
    check('文件夹 = 去掉最后一段（POSIX 斜杠）',
      fo('/home/u/exports/a.docx') === '/home/u/exports', fo('/home/u/exports/a.docx'))
  }

  const src = await readFile(join(pluginRoot, 'client', 'KsMaterialsPanel.tsx'), 'utf8')
  const idx = src.indexOf('const win = isPage ? window.open(')
  const awaitIdx = src.indexOf('await fetchExportBlob(name)')
  check('⚠ 新标签必须在**用户手势的同步段**里先占位（before await）——否则实测被弹窗拦截',
    idx > 0 && awaitIdx > 0 && idx < awaitIdx, `win=${idx} await=${awaitIdx}`)
  check('被拦截时退化成下载 **并显示原因**（绝不静默无反应）',
    src.includes('浏览器拦截了新窗口'))
  check('blob URL 会被撤销（但要延后：立刻撤会让新标签白屏）',
    (src.match(/revokeObjectURL/g) ?? []).length >= 2 && /120_000/.test(src))
}

/* ------------------------------------------- D. 渠道台账面板（§11.0 R4b） */
{
  const chan = await loadModule('client/KsChannelsPanel.tsx')
  const { describeWhen, needsAttention, sortChannels } = chan

  check('KsChannelsPanel 导出了 describeWhen / needsAttention / sortChannels',
    [describeWhen, needsAttention, sortChannels].every((f) => typeof f === 'function'))

  // D1 ⚠ UTC 解析：SQLite 的 datetime('now') 是 **UTC 且无时区标记**，
  //    直接 new Date() 会按本地时区解析（差 8 小时）⇒ 这里必须补 Z。
  const now = Date.parse('2026-09-18T05:00:00Z')
  check('describeWhen：UTC 串按 UTC 解析（04:47 距 05:00 应是 13 分钟前）',
    describeWhen('2026-09-18 04:47:00', now) === '13 分钟前',
    describeWhen('2026-09-18 04:47:00', now))
  check('describeWhen：空值 → —（不许显示 Invalid Date）', describeWhen(null) === '—')
  check('describeWhen：已带时区的串不再补 Z',
    describeWhen('2026-09-18T04:47:00Z', now) === '13 分钟前')
  check('describeWhen：小时/天粒度',
    describeWhen('2026-09-18 03:00:00', now) === '2 小时前'
    && describeWhen('2026-09-16 05:00:00', now) === '2 天前')

  // D2 需要关注的行：接线坏 / 不可抓 / 可疑 / 有连续失败
  const base = {
    channel_id: 'c', name: 'n', category: 'law', wiring: 'wired',
    verification: 'verified', state: 'ok', enabled: 1, consecutive_failures: 0,
  }
  check('needsAttention：一切正常 → false', needsAttention(base) === false)
  check('needsAttention：wiring=broken → true（在链上但实测不工作）',
    needsAttention({ ...base, wiring: 'broken' }) === true)
  check('needsAttention：state=down / suspicious → true',
    needsAttention({ ...base, state: 'down' }) === true
    && needsAttention({ ...base, state: 'suspicious' }) === true)
  check('needsAttention：有连续失败 → true',
    needsAttention({ ...base, consecutive_failures: 2 }) === true)
  check('needsAttention：仅登记且未探 → false（不是问题，只是还没接）',
    needsAttention({ ...base, wiring: 'seed_only', state: 'unknown' }) === false)

  // D3 排序：有问题的排前面（人工维护要从"有问题的那几条"看起）
  const rows = [
    { ...base, channel_id: 'ok1', name: '正常甲' },
    { ...base, channel_id: 'bad1', name: '坏了乙', wiring: 'broken' },
    { ...base, channel_id: 'bad2', name: '可疑丙', state: 'suspicious' },
  ]
  const ordered = sortChannels(rows).map((r) => r.channel_id)
  check('sortChannels：有问题的排前面', ordered[0] !== 'ok1' && ordered[2] === 'ok1',
    ordered.join(','))
  check('sortChannels：不改原数组（返回新数组）',
    rows[0].channel_id === 'ok1' && sortChannels(rows)[0].channel_id !== 'ok1')

  // D4 面板接线：懒加载门 + 摘要两个数都显示 + 两列分列 + UTC 标注（写法级窄判据）
  const src = await readFile(join(pluginRoot, 'client', 'KsChannelsPanel.tsx'), 'utf8')
  check('懒加载门：visible=false 时不请求（与其它面板同契约）',
    /if \(!visible\) return undefined/.test(src))
  check('摘要同时显示台账条数与能力条数（wired）',
    src.includes('s.by_wiring.wired') && src.includes('s.total'))
  check('接线与有效性**分列**（不许合成一个"有效"）',
    src.includes('WIRING_LABEL') && src.includes('STATE_LABEL'))
  check('时间列显式标注 UTC', src.includes('last_ok_at') && /UTC/.test(src))
  const settingsSrc = await readFile(join(pluginRoot, 'client', 'KsSettingsSection.tsx'), 'utf8')
  check('设置区挂了「渠道台账」类目（懒加载门由 details 驱动）',
    /title="渠道台账"/.test(settingsSrc)
    && /<KsChannelsPanel visible=\{channelsOpen\}/.test(settingsSrc))
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== catalog-ui smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
