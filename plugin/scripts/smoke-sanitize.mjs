/**
 * ks-dsh-plugin — scripts/smoke-sanitize.mjs
 *
 * 消毒器回归（verifier 2026-09-13 REJECT 修复的强制用例）：
 * sanitizeDocHtml 的白名单必须同时满足——
 *   P0-2 回归：img.fig-embed / img.table-embed 的 **class 存活**（接线选择器
 *             按 class 命中；剥 class = figure/table-image 永不请求）。
 *   P0-1 回归：**剥壳子树内的危险属性也被剥**（旧实现栈快照漏洞：上移的
 *             <img onerror>/<a href=javascript:> 永不被过滤 → 存储型 XSS）。
 *   P1-1 回归：**img.src 不改写成 data-ks-src**（断头占位属性零残留）。
 *   外链直挂：img src/srcset 一律剥除（引擎占位本就无 src）。
 *
 * 同时覆盖 wirePlaceholders 的选择器前提（class 命中 → fetch 参数正确）。
 *
 * 策略与暴露面（verifier 复审 B 项已裁可接受）：真实现是 browser 模块（顶层
 * import react/pdfjs-dist/'./api'），node 桩成本远超收益——本冒烟**手写微型 DOM
 * 复刻**真实现的算法（逐行同构：filterAttrs 在 pop 处调用 / 白名单孩子入栈 /
 * 剥壳上移孙节点入栈三路径），锁定的是算法语义。复刻与真实现的已知域差
 * （混排重排/注释/template 等 6 类，均比真实现宽松、现网语料 0 触发）见
 * DEVELOPMENT-HISTORY 第七节；真实现的回归锚由 tsc + E2E 兜底。
 *
 * 用法：node scripts/smoke-sanitize.mjs   （退出码 0 = 全通过）
 */

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------- 微型 DOM（只实现消毒器+断言用到的面） */

/** 微型 DOM：只实现消毒器+断言用到的面。 */
class MiniNode {
  constructor(tag) {
    this.tag = tag            // 小写标签名；'#text' = 文本
    this.attrs = new Map()    // name(小写) → value
    this.children = []        // MiniNode[]
    this.parent = null
    this.text = ''            // 仅 #text
  }
  get classList() {
    const self = this
    return {
      contains(cls) {
        return (self.attrs.get('class') ?? '').split(/\s+/).includes(cls)
      },
      remove(cls) {
        const cur = (self.attrs.get('class') ?? '').split(/\s+/).filter((c) => c !== cls && c !== '')
        if (cur.length > 0) self.attrs.set('class', cur.join(' '))
        else self.attrs.delete('class')
      },
    }
  }
}

/** 极简 HTML 解析（标签/属性/文本；自闭合与 < 嵌套按消毒器输入域够用）。 */
function parseMini(html) {
  const root = new MiniNode('#root')
  const stack = [root]
  let i = 0
  while (i < html.length) {
    const lt = html.indexOf('<', i)
    if (lt < 0) { appendText(stack[stack.length - 1], html.slice(i)); break }
    if (lt > i) appendText(stack[stack.length - 1], html.slice(i, lt))
    if (html.startsWith('<!--', lt)) { const end = html.indexOf('-->', lt); i = end < 0 ? html.length : end + 3; continue }
    const gt = html.indexOf('>', lt)
    if (gt < 0) { appendText(stack[stack.length - 1], html.slice(lt)); break }
    let inner = html.slice(lt + 1, gt)
    const selfClose = inner.endsWith('/')
    if (selfClose) inner = inner.slice(0, -1)
    // 闭合标签检测必须在 tagMatch 之前——'/li' 的首字符非字母，正则匹配 null
    // 会先走 `tagMatch===null` 分支把闭合标签整个跳过（弹栈永不发生，树形全错）。
    if (inner.startsWith('/')) {
      const closeTag = inner.slice(1).match(/^([a-zA-Z][a-zA-Z0-9-]*)/)
      if (closeTag !== null) {
        const idx = stack.map((n) => n.tag).lastIndexOf(closeTag[1].toLowerCase())
        if (idx > 0) stack.length = idx
      }
      i = gt + 1
      continue
    }
    const tagMatch = inner.match(/^([a-zA-Z][a-zA-Z0-9-]*)/)
    if (tagMatch === null) { i = gt + 1; continue }
    const tag = tagMatch[1].toLowerCase()
    const el = new MiniNode(tag)
    // 属性：name(="value"|='value'|=裸值|无值)。
    const attrRe = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g
    attrRe.lastIndex = tagMatch[1].length
    let m
    while ((m = attrRe.exec(inner)) !== null) {
      if (m[1] === undefined) continue
      el.attrs.set(m[1].toLowerCase(), m[2] ?? m[3] ?? m[4] ?? '')
    }
    stack[stack.length - 1].children.push(el)
    el.parent = stack[stack.length - 1]
    if (!selfClose && tag !== 'br' && tag !== 'img' && tag !== 'hr' && tag !== 'input') {
      stack.push(el)
    }
    i = gt + 1
  }
  return root
}
function appendText(parent, text) {
  if (text.length === 0) return
  const n = new MiniNode('#text')
  n.text = text
  n.parent = parent
  parent.children.push(n)
}

/* --------------------- 消毒器复刻（与 client/KsDocTextView.tsx 同算法） */
// 为什么复刻而不是 esbuild 打包真模块：真模块顶层 import react/pdfjs-dist/
// './api'（fetch 等 browser 全局）——node 桩成本远超复刻，而消毒器算法是
// 纯函数（本冒烟的价值在**用例矩阵**锁行为，实现漂移由 tsc+手测把关）。
// P0 修复后算法 = 待处理栈，保证上移节点必被访问。

const ALLOWED_TAGS = new Set([
  'p', 'br', 'b', 'strong', 'i', 'em', 'u', 'sub', 'sup', 'span',
  'div', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'caption',
  'img', 'figure', 'figcaption', 'blockquote', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre', 'code',
])
const ALLOWED_ATTRS = {
  img: new Set(['alt', 'loading', 'class']),
  span: new Set(['class']),
  table: new Set(['class']),
  div: new Set(['class']),
  p: new Set(['class']),
  td: new Set(['colspan', 'rowspan']),
  th: new Set(['colspan', 'rowspan']),
}

function sanitizeMini(root) {
  // 与真实现同步的核心不变量：属性过滤**只在节点被 pop 时**做——入栈路径
  // （白名单孩子 / 剥壳上移孙节点 / 根）不承担过滤职责。若把过滤放在父节点
  // 循环里，剥壳上移的节点会错过父节点的 children 快照（上移在快照之后）
  // → 自身属性永不被过滤（<unknown-tag><img onerror>… 剥壳后 onerror 存活）。
  const filterAttrs = (el) => {
    const tag = el.tag
    for (const name of [...el.attrs.keys()]) {
      if (tag === 'img' && (name === 'src' || name === 'srcset')) {
        el.attrs.delete(name)
        continue
      }
      const keep = (ALLOWED_ATTRS[tag]?.has(name) ?? false)
        || (name.startsWith('data-') && name !== 'data-src')
      if (!keep) el.attrs.delete(name)
    }
  }
  const stack = [root]
  while (stack.length > 0) {
    const node = stack.pop()
    filterAttrs(node)
    for (const child of [...node.children]) {
      if (child.tag === '#text') continue
      if (ALLOWED_TAGS.has(child.tag)) {
        stack.push(child)
      } else {
        const parent = child.parent
        if (parent === null) continue
        const at = parent.children.indexOf(child)
        for (const gc of child.children) if (gc.tag !== '#text') stack.push(gc)
        const keepKids = child.tag !== 'script' && child.tag !== 'style'
        parent.children.splice(at, 1, ...(keepKids ? child.children : []))
        for (const gc of child.children) gc.parent = parent
      }
    }
  }
  return root
}

/* --------------------------- 断言矩阵 */

function findFirst(node, tag, pred) {
  if (node.tag === tag && (pred === undefined || pred(node))) return node
  for (const c of node.children) {
    const hit = findFirst(c, tag, pred)
    if (hit !== null) return hit
  }
  return null
}
function findAll(node, tag, pred, acc = []) {
  if (node.tag === tag && (pred === undefined || pred(node))) acc.push(node)
  for (const c of node.children) findAll(c, tag, pred, acc)
  return acc
}
const attr = (el, name) => (el === null ? null : (el.attrs.get(name) ?? null))

// 样本 1：引擎真实占位（fig/table/katex）+ 危险混入。
const SAMPLE_ENGINE = `
<p class="clause">第4.1条：防护距离应符合 <span class="katex-formula" data-fno="1" data-clause="4.1" data-tex="d \\geq 3r">d ≥ 3r</span>。</p>
<p>结构示意见 <img class="fig-embed" data-fig="A.1" alt="图A.1">。</p>
<p>参数表见 <img class="table-embed" data-page="6" data-tbl="0">。</p>
<div><unknown-tag><img src="x" onerror="alert(1)" class="fig-embed" data-fig="B.9"></unknown-tag></div>
<figure><figcaption>原图</figcaption><img srcset="http://evil/x" class="fig-embed" data-fig="A.2"></figure>
<script>steal(document.cookie)</script>
<a href="javascript:alert(2)">外链</a>
<ul onmouseover="x()"><li>条款一</li></ul>
`

{
  const out = sanitizeMini(parseMini(SAMPLE_ENGINE))

  // ---- P0-2 回归：class 存活（接线前提）。
  const figs = findAll(out, 'img', (e) => e.classList.contains('fig-embed'))
  check('P0-2 img.fig-embed class 存活（≥3 处）', figs.length >= 3, `got ${figs.length}`)
  const tbls = findAll(out, 'img', (e) => e.classList.contains('table-embed'))
  check('P0-2 img.table-embed class 存活', tbls.length === 1)
  const katex = findAll(out, 'span', (e) => e.classList.contains('katex-formula'))
  check('P0-2 span.katex-formula class+data 存活',
    katex.length === 1 && attr(katex[0], 'data-fno') === '1' && attr(katex[0], 'data-clause') === '4.1')

  // ---- P0-1 回归：剥壳子树内危险属性被剥。
  //   <unknown-tag> 剥壳后其 <img> 上移 → onerror 必须被过滤。
  const lifted = figs.find((e) => attr(e, 'data-fig') === 'B.9')
  check('P0-1 剥壳上移的 img onerror 被剥', lifted !== null && attr(lifted, 'onerror') === null)
  //   src 直剥（P1-1：不是改写 data-ks-src，是删除）。
  check('P1-1 img.src 剥除（无 data-ks-src 残留）',
    lifted !== null && attr(lifted, 'src') === null && attr(lifted, 'data-ks-src') === null)
  const figcap = findFirst(out, 'img', (e) => attr(e, 'data-fig') === 'A.2')
  check('srcset 剥除', figcap !== null && attr(figcap, 'srcset') === null)
  //   javascript: href（<a> 非白名单 → 剥壳，文本保留，href 随壳消失）。
  check('javascript: 链接随非白名单壳剥除',
    findAll(out, 'a').length === 0 && findFirst(out, '#text', (n) => n.text.includes('外链')) !== null)
  //   白名单标签上的 on* 仍要剥（ul onmouseover）。
  const ul = findFirst(out, 'ul')
  check('白名单标签 on* 事件属性被剥', ul !== null && attr(ul, 'onmouseover') === null)
  //   script 全丢（含文本）。
  check('script 节点+文本全丢', findFirst(out, '#text', (n) => n.text.includes('steal')) === null)

  // ---- 文本保全（剥壳不剥内容）。
  check('正文文本保全（条款文字在）',
    findFirst(out, '#text', (n) => n.text.includes('第4.1条')) !== null
    && findFirst(out, '#text', (n) => n.text.includes('条款一')) !== null)
}

// 样本 2：表格与排版（白名单内应原样通过）。
{
  const out = sanitizeMini(parseMini(
    '<table class="std-table"><thead><tr><th colspan="2">项</th></tr></thead><tbody><tr><td>a</td><td rowspan="2">b</td></tr></tbody></table>',
  ))
  const table = findFirst(out, 'table')
  check('表格结构+colspan/rowspan 保全',
    table !== null && attr(table, 'class') === 'std-table'
    && attr(findFirst(out, 'th'), 'colspan') === '2'
    && attr(findFirst(out, 'td', (e) => attr(e, 'rowspan') === '2'), 'rowspan') === '2')
}

// 样本 3：嵌套危险（危险标签套危险标签——逐层上移都要过滤）。
{
  const out = sanitizeMini(parseMini(
    '<p>正常</p><bogus1><bogus2><img onerror="x" src="y" class="fig-embed" data-fig="1"></bogus2></bogus1>',
  ))
  const img = findFirst(out, 'img')
  check('双层剥壳后 onerror/src 仍被剥、class/data 存活',
    img !== null && attr(img, 'onerror') === null && attr(img, 'src') === null
    && img.classList.contains('fig-embed') && attr(img, 'data-fig') === '1')
}

// 样本 4：src 无值 / data-src（旧占位形态）不产生断头属性。
{
  const out = sanitizeMini(parseMini(
    '<div><img class="fig-embed" data-fig="2" src=""></div>',
  ))
  const img = findFirst(out, 'img')
  check('空 src 剥除且无 data-ks-src', img !== null && attr(img, 'src') === null && attr(img, 'data-ks-src') === null)
}

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-sanitize: ${failed.length}/${results.length} FAILED`)
  process.exit(1)
}
console.log(`\nsmoke-sanitize: ${results.length}/${results.length} PASS`)
