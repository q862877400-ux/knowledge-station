/**
 * ks-dsh-plugin — scripts/smoke-bbox-degenerate.mjs
 *
 * `/ks/bbox` 宿主代理的**退化框过滤**判据（spec 010）。
 *
 * 为什么需要它：业主实跑报「红色箭头还是没有」。查清的真因之一是
 * `GB 17681-2024` 这篇文档的 span **全是页面边缘碎片**
 * （宽 0.01–0.9pt、高 0.01–0.09pt）—— 原样给前端，箭头会画成**一个看不见的点**，
 * 等于骗用户"标好了"。修法 = 代理层过滤掉它们，让前端走既有的
 * "取不到坐标"可见提示（如实告知"只跳页、不画箭头"）。
 *
 * 钉三件事：
 *   ① 退化框（宽<5pt 或 高<3pt）**必须被滤掉**；
 *   ② 正常框（真实量级）**必须留下**（防阈值太松把正常行也滤了）；
 *   ③ 形状不对的（不是 4 个数 / 含非有限值）也要滤。
 *
 * ⚠ 判法：**静态读源码 + 抽出那段过滤逻辑真跑**。
 *   为什么不去起真宿主：那要起完整 DSH + 引擎，代价远大于这条判据的收益，
 *   而且本仓已有"读源码 + 抽出逻辑真跑"的先例（`smoke-ui-scale` 的 token 判据）。
 *   抽出方式是**执行源码里那段函数体**，不是重写一遍（重写就测不到真实现了）。
 *
 * 用法：node scripts/smoke-bbox-degenerate.mjs   （退出码 0 = 全通过）
 */
import { readFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')
const src = readFileSync(join(pluginRoot, 'src', 'index.js'), 'utf8')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ---- 从真源码里抽出那段 filter（不重写，保证测的是真实现） ---- */
const m = src.match(/const spans = spansRaw\.filter\(\(s\) => \{[\s\S]*?\n {8}\}\)/)
if (m === null) {
  check('能从 src/index.js 抽出 /ks/bbox 的退化框过滤逻辑', false,
    '没匹配到那段 filter（实现被改写了？）')
  console.log('\n== bbox-degenerate smoke FAIL ==')
  process.exit(1)
}
check('能从 src/index.js 抽出 /ks/bbox 的退化框过滤逻辑', true)

/* 执行抽出的那段：给它 spansRaw，拿回 spans。
   ⚠ 用 new Function 执行**真源码片段**（不是重写）。 */
const filterImpl = new Function('spansRaw', `${m[0]}\nreturn spans`)
const filter = (spans) => filterImpl(spans)

/* ---- ① 退化框必须被滤掉（业主那篇的真实值） ---- */
const DEGENERATE = [
  { page_number: 9, bbox: [0.1, 784.33, 0.88, 784.4], span_type: 'text' },     // 宽0.78 高0.07
  { page_number: 9, bbox: [0.12, 784.56, 0.18, 784.57], span_type: 'text' },   // 宽0.06 高0.01
  { page_number: 11, bbox: [0.1, 784.5, 0.77, 784.52], span_type: 'text' },    // 宽0.67 高0.02
]
check('① 退化框（业主那篇的真实值）被全部滤掉',
  filter(DEGENERATE).length === 0,
  `留下 ${String(filter(DEGENERATE).length)} 个`)

/* 只满足一个维度的也要滤 */
check('①b 宽 200pt 但高 0.5pt 的"一条线"被滤掉',
  filter([{ page_number: 1, bbox: [10, 100, 210, 100.5] }]).length === 0)
check('①c 高 13pt 但宽 2pt 的"一根竖线"被滤掉',
  filter([{ page_number: 1, bbox: [10, 100, 12, 113] }]).length === 0)

/* ---- ② 正常框必须留下（防阈值太松） ---- */
const NORMAL = [
  { page_number: 17, bbox: [73.0, 360.9, 334.0, 372.9], span_type: 'text' },   // 261×12（真库实测）
  { page_number: 1, bbox: [55.0, 160.9, 211.0, 172.9], span_type: 'text' },    // 156×12
  { page_number: 16, bbox: [54.0, 93.9, 520.0, 120.9], span_type: 'text' },    // 466×27
]
check('② 正常框（真库实测量级）全部留下',
  filter(NORMAL).length === 3, `留下 ${String(filter(NORMAL).length)} 个`)

/* 边界：恰好 5×3 应当留下（阈值是"小于"才滤） */
check('②b 恰好 5×3pt 留下（阈值语义是"小于"才滤）',
  filter([{ page_number: 1, bbox: [10, 10, 15, 13] }]).length === 1)

/* ---- ③ 形状不对的也要滤 ---- */
check('③ 不是 4 个数的被滤掉',
  filter([{ page_number: 1, bbox: [1, 2, 3] }]).length === 0)
/* ⚠⚠ **这条是我自己的变异④抓出来的假绿**（留痕）：
   原来只测 `[1,2,3]` —— 而 `box[3]` 是 undefined、`Math.abs(undefined-3)` 是 NaN、
   `NaN >= 3` 为 false ⇒ **即使去掉形状校验也碰巧被滤掉**，判据没牙。
   ⇒ 补一条**只有形状校验能挡住**的输入：**5 个数**且前 4 个是正常量级
     （`box[2]-box[0]` 与 `box[3]-box[1]` 都是正常尺寸 ⇒ 阈值那关过得去，
      只有 `length !== 4` 这关能挡住它）。 */
check('③a 5 个数（前 4 个正常量级）被滤掉 —— 只有形状校验能挡住它',
  filter([{ page_number: 1, bbox: [10, 100, 210, 113, 999] }]).length === 0,
  `留下 ${String(filter([{ page_number: 1, bbox: [10, 100, 210, 113, 999] }]).length)} 个`)
check('③b 含非有限值的被滤掉',
  filter([{ page_number: 1, bbox: [10, 10, Number.NaN, 100] }]).length === 0)
check('③c 含字符串数值的也要滤（不许把 "10" 当数字）',
  filter([{ page_number: 1, bbox: ['10', '100', '210', '113'] }]).length === 0,
  `留下 ${String(filter([{ page_number: 1, bbox: ['10', '100', '210', '113'] }]).length)} 个`)
check('③d 非对象 / null 被滤掉',
  filter([null, 'x', 42]).length === 0)

/* ---- ④ 混合：只滤坏的，留下好的 ---- */
const MIXED = [...DEGENERATE, ...NORMAL]
check('④ 混合输入：3 个退化被滤、3 个正常留下',
  filter(MIXED).length === 3, `留下 ${String(filter(MIXED).length)} 个`)

/* ---- ⑤ 与引擎侧常量同值（两边口径必须一致，否则"代理滤了引擎没滤"会打架） ---- */
{
  const py = readFileSync(join(pluginRoot, '..', 'src', 'core', 'llm', 'ks_answer.py'), 'utf8')
  const mw = py.match(/DEGENERATE_BBOX_MIN_W = ([\d.]+)/)
  const mh = py.match(/DEGENERATE_BBOX_MIN_H = ([\d.]+)/)
  const jsW = src.includes('Math.abs(box[2] - box[0]) >= 5')
  const jsH = src.includes('Math.abs(box[3] - box[1]) >= 3')
  check('⑤ 代理层阈值与引擎侧常量同值（5pt / 3pt，两边口径一致）',
    mw !== null && mh !== null && Number(mw[1]) === 5 && Number(mh[1]) === 3 && jsW && jsH,
    `引擎 W=${mw === null ? '?' : mw[1]} H=${mh === null ? '?' : mh[1]}｜代理 W=5? ${String(jsW)} H=3? ${String(jsH)}`)
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== bbox-degenerate smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
