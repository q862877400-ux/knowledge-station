#!/usr/bin/env node
/**
 * 渲染级冒烟：把「知识库」页**真的挂进 DOM** 跑一遍，断言行为而不是字符串。
 *
 * ════════════ 2026-09-21（KB-FOLDER-PLAN 第 3 步）本文件**随功能一起重写** ════════════
 *
 * ## 为什么必须重写（不是"想过就改"）
 * 上一版（5h/5i/5j 的样板页）里有**大段断言判的是一个已经不存在的界面**：
 * 卡片带（`.ks-kbband` 的滚动几何 / 5 张卡等宽等高 / `BAND_STEP_WINDOW`）、
 * 文件勾选 + 悬浮批量条 + 批量删除、标签视图（`.ks-subtabs`/`.ks-tagrow`/检索语法回显）、
 * 状态筛选胶囊（`.ks-chip`）、以及一批**占位常量**（`SEED_DOCS` 的 15 篇假文档、
 * `STD_TREE`/`LAW_TREE`/`USER_FOLDERS` 的假目录）。任务书把它们列为
 * "**故意设计成会因这次改版变红的**，要随功能一起改成断言新的真实行为，
 * **严禁**删掉/注释掉/改成恒真/放宽"。
 *
 * ## 逐条对账（旧断言 → 新断言）
 * ⚠⚠ **条数（2026-09-21 复核 `verify-freeze-kb-ui3` 打回后**重数**，不许再抄历史快照）**：
 *   上一版运行时是 **98/98**（源文件 `check(` 字面量 95 处，其中 1 处在块注释里 ⇒ 94 处真调用；
 *   其中"模板名"那条在按库循环里复用了 4 次）；本版 **79/79**（静态 79 = 运行时 79，无死分支；
 *   ⚠ **这个数字会随改动漂，别抄它**：以脚本结尾打印的「== kb-page-render smoke PASS (N/N) ==」为准。
 *   ⚠ 第 5 步收尾时是 **130/130**、第 6 步加入 R1~R18 后是 **148/148**（每轮**实跑**出来的数）；
 *     2026-09-22 业主两条界面改动（删文件行图标 + 提问入口搬家）再加 B10/R5b/R5c，
 *     复核 MEDIUM-2 的运行时复现再加 R19a/R19b ⇒ 是 **153/153**；
 *     2026-09-22 业主改菜单文案那一轮（移动到 / 复制到 / 在此文件中提问 / 移出）**改判据不改条数**，
 *     外加新增 I5b（「⋮」按钮 title 里那句"文件不会删除"）+ P23b（移出后的消息）⇒ 现在是 **156/156**
 *     （以脚本结尾打印的为准）。
 *     2026-09-21 第二轮复核就是靠这条抓到头部三处旧数字没改干净 —— 写数字就要**当轮**改干净）
 *   ⇒ **少 30 条**，不是本文件上一版注释里写的"少 4 条"。
 *   **那句"72/72 / 少 4 条 / 每条都有替代"是错的，就地留痕更正**：72 是 `docs/UI-BASELINE.md`
 *   的历史快照（该文档后来记的是 73/73），**拿历史快照当"上一版运行时条数"是坏证据**
 *   （旧文件自己也警告过别这么引）。复核实测 98/98 跑了两遍。
 *   30 条的去向分三类（复核的报告 §④ 有逐条表，`var/tmp/verify-kb-ui3-report.md`）：
 *     · **A 保留**（判据等价或更硬）：页面挂载/样式/留边 9 条、目录层同构与 3 轨、列对齐、
 *       搜索过滤、详情字段、能力页 8 条 ……（`#dircols` 那条还从"两条声明相同"升级成真 Chrome 像素 + 冻结常数）；
 *     · **B 主体整块被删** ⇒ 用**负向断言**替代（`C1`/`C2`/`C3` 判"那些假动作真的没了"）：卡片带 11 条、
 *       卡片点击式导航 13 条、筛选胶囊/勾选框/批量条/标签视图 11 条 ……；
 *     · **C 主体仍在、断言却没了**：**13 条**（复核逐条点名）。这 13 条**本批已逐条处置**：
 *       ① 目录层列头文案「目录/篇数」→ **B7**（复核变异 M4 实测：清空前能全绿）；
 *       ② 文件层列头文案（文件名/效力/生效日期/处理状态）→ **E5**；
 *       ③ 目录层表头每一格 display 必须是 flex 不是 grid（「目录」只剩「目」那个坑）
 *          → `ui-render-shot.mjs` 的 `dirHeadCheck`（真浏览器；它由**冻结清单** `DIR_LAYER_COMBOS`
 *            决定"这一跑要不要判"，不是挂在 `rowCtrlsCheck` 旁边 —— 复核第 2 轮 `:33` 抓到我写错）
 *       ④ 目录行名字文本 == 它自己的 title → **B8**；
 *       ⑤ 搜索框 placeholder 口径 → **F1b**；
 *       ⑥ 每行行内**可见控件 ≤ 3**（P1-1 口径）→ `ui-render-shot.mjs` 的 `rowCtrlsCheck`（真浏览器，
 *          原来只在真 Chrome 里**量** `ctrls` 却 Node 侧零断言 ⇒ 量了不判）；
 *       ⑦ ~~每行有行内文件图标（`.ks-fileico` 里真 svg + 非空 title）~~ → **E6 已于 2026-09-22 就地翻面**：
 *          **文件行不许有**那个图标（业主："文件前面那个莫名其妙的图标可以删除"），
 *          **目录行必须有**文件夹图标（业主："文件夹前面一个小文件夹图标做得好"）→ **B10**
 *          （⚠ 图标**尺寸** 14/16/20 三档混用那条残余**随本次删除消失**，见方案文档 §十六的标注）；
 *       ⑧ 列头行与数据行是同一个容器的直接子元素 → **B9** / **E8**；
 *       ⑨ 每行菜单点开再点一次都收起 → **I6**；
 *       ⑩ 每行都有 ⋮ 触发器（一行一个）→ **E7**；
 *       ⑪ 搜索在库根/一级/二级各判一轮 → **G1b/G1c**（补最外层那一轮）；
 *       ⑫ 覆盖面防空转（"5 张卡都查得到"/"至少判过 3 次目录层"）→ **判定：可接受，不补**：本文件是
 *          **线性 79 条**（静态 79 = 运行时 79，无死分支、无可空转的循环），旧那两条是给一个会空转的
 *          `for` 循环兜底的，主体（卡片带）已不存在；
 *       ⑬ 第 54 条「切库 ⇒ 搜索词**清空**」→ **语义反转**：现在 **F6** 明确要求"换层后搜索词**留在框里**"
 *          （沿用 5i 的页面级过滤口径）。这是**产品口径变更**，本行就是它的登记（原对账表漏了它）。
 *
 * | 旧的（选它是因为它当时最硬） | 现在的（判**新的真实行为**） |
 * |---|---|
 * | 卡片带：5 张库卡一次渲染进同一滚动容器 | **卡片带整块没了**：`.ks-kbband*`/`.ks-kb-cards .ks-kb-card` 计数恒 0 |
 * | 卡片带：逐卡 computed `flex`/`min-height` 逐字相同 | **左列目录树的每一行**：computed `min-height` 逐字相同（同一个行高 token） |
 * | 卡片带（装假几何）：两端置灰 / `scrollLeft` 自夹 | **后端分页**：`has_more` 驱动的翻页条出现、点下一页真的发 `offset=50`、末页禁用 |
 * | 目录层是真列表（表头/行 cell 类名逐字相同） | **同一条判据、换到真数据**：右侧目录层表头与目录行 cell 类名序列逐字相同（且只列**这一级**） |
 * | 面包屑逐级可点 / 返回上一级 | **同一条判据、换到后端给的面包屑**：点第 0 段回最外层、末段不可点、返回按钮在最外层 disabled |
 * | 搜索框"每层常驻" + 真的过滤（目录名） | 同一条判据 + **文件层也过滤**（标准号/名称），并新增"本页筛出"口径 |
 * | 行内勾选框数 = 文档数 + 1 / 批量条 5 项 | **批量动作不在本批** ⇒ 勾选框 0 个、批量条 0 个（**这是删除，不是放宽**：它判的是"这些假动作真的没了"） |
 * | 行尾「⋮」菜单含「＋标签」与「详情」两项 | 菜单**只有「详情」**；「＋标签」是"只改内存"的假动作，本批拆除（同一条断言改成"它不在") |
 * | 标签视图跨文件夹定义 / 检索语法回显 | **标签视图整块删除**（没有落库的接口）；改用"页面文本里没有任何标签视图痕迹" |
 * | 详情含三个日期且是真值 | 同一条判据、换到**后端字段**（`published_at`/`effective_from`/`withdrawn_date`） |
 *
 * ## 新加的、**有牙**的那几条（区分"真接了库"与"还是样板"）
 * 本版第一次给这一页装了 **`globalThis.fetch` 桩**（以前它一个接口都不调，所以不需要）。
 * 桩按 `routes_kb_folders.py` 的**真实返回形状**回话，并**记下每一次请求** ⇒ 于是可以断言：
 *   1. 页面真的发起了 `GET /api/v1/kb/folders`（**不带 parent_id = 最外层**）；
 *   2. 桩里那 4 个顶层目录名（标准/法律法规/空目录/大批量）**真的出现在页面上**；
 *   3. 点一个目录 ⇒ 请求里**带上了 `parent_id=<它的 id>`**（= 按需展开，不是一次拉全库）；
 *   4. 点「下一页」⇒ 请求里带上 `offset=50`；
 *   5. 点「导入到这一层」⇒ 真的 `POST /api/v1/ingest/bulk`（引擎的**真导入**，
 *      不是 host 那套只读体检），完成后真的 `POST /api/v1/kb/inbox/confirm`
 *      且 `target_folder_id` = 当前目录（= 上传进这一级 + 标成已归位 = 不进自动识别）。
 * 这五条任何一条在"还是样板"的页面上都**必然红**（样板不发请求、也没有这些元素）。
 *
 * ## 2026-09-21（第 6 步）按**目录范围**提问：本文件又改了三处、新增 R1~R18
 * 业主口径：「每一级都能"在此范围内提问"，包括它下面所有层；多选几个目录 = 取并集」。
 * · **改的三处**（都是"菜单多了「在此范围内提问」"这一个原因的连带，**不是放宽**）：
 *     I5（目录里那篇文件的 ⋮ 菜单 4 → 5 样）、P25（最外层文件的 ⋮ 菜单 2 → 3 样）、
 *     P5（目录行的 ⋮ 菜单 5 → 6 样）、N6（兜底桶那一篇 3 → 4 样）。
 *     ⚠ **就地更正（2026-09-21，复核 LOW-6 打回）**：这一行原来写"**每一处都在原地留了原文**"
 *     —— 复核实测**只有 I5 真留了** `原文：…` 那一行。现在 P5/P25/N6 也各自补上了原文（四条齐）。
 * · **R1~R18 判的是四件真事**：① 请求里**真的带上范围**（`params.kb_folder_ids`/`kb_doc_ids`）；
 *   ② 最外层/「待分类」没勾选时按钮**禁用**且 title 说清为什么（不许悄悄变成全库提问）；
 *   ③ 范围的篇数来自引擎（`/kb/scope/resolve`），空范围如实说「范围内没有 + 一次检索都没做」；
 *   ④ 引擎回显说"没限定范围"而这次明明带了范围 ⇒ **当众标红**。
 *   ⚠ 桩新增两条路由（`/kb/scope/resolve`、`/ks/answer`），且**共用同一份范围算法** ——
 *     于是"chip 上的篇数 == 答案回显的篇数"是必然的，不等就是界面自己编的。
 *
 * ## 诚实的边界（别把它读成"像素已验证"）
 * - 宿主的 `ui-primitives` 是**按源码形状生成的桩**（成员名单从源码派生，见
 *   `scripts/lib/ks-primitives-stub.mjs`）；这里验的是**我们这一页的组装与行为**，
 *   不是宿主组件的内部实现，更不是视觉（像素由 `ui-render-shot.mjs` 在真浏览器里量）。
 * - 样式（`ksGuideStyles`）只验"注入了"与"声明与结构"，验不了"长什么样"。
 * - **引擎本身没有被调用**：本文件的全部 HTTP 都是**桩**（真引擎联调不在渲染冒烟里）。
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

import { ksClientPrimitivesAlias } from './lib/ks-primitives-stub.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

/** jsdom/React 的宿主检出（可用 `--harness` 或 `KS_HARNESS_DIR` 覆盖）。 */
const harness = (() => {
  const i = process.argv.indexOf('--harness')
  if (i !== -1 && process.argv[i + 1]) return process.argv[i + 1]
  return process.env.KS_HARNESS_DIR ?? 'D:\\AI\\DSH\\deepseek-harness'
})()
const jsdomDir = join(harness, 'node_modules', 'jsdom')
const webNodeModules = join(harness, 'packages', 'client', 'web', 'node_modules')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

// ── 缺件时**报错退出**，不静默跳过 ──
// 理由与本仓其它护栏一致：**"没跑" 不能渲染成 "通过"**。缺件就明确红，并告诉你怎么办。
const missing = []
if (!existsSync(join(jsdomDir, 'package.json'))) missing.push(`jsdom: ${jsdomDir}`)
if (!existsSync(join(webNodeModules, 'react', 'package.json'))) missing.push(`react: ${join(webNodeModules, 'react')}`)
if (!existsSync(join(webNodeModules, 'react-dom', 'package.json'))) missing.push(`react-dom: ${join(webNodeModules, 'react-dom')}`)
if (missing.length > 0) {
  console.error('❌ 渲染级用例**没跑**（缺件），这不是通过：')
  for (const m of missing) console.error(`   - ${m}`)
  console.error('   → 用 --harness <DSH 检出> 或设 KS_HARNESS_DIR 指向含 jsdom/react 的检出。')
  process.exit(1)
}

const stubDir = await mkdtemp(join(tmpdir(), 'ks-render-'))
try {
  /* ── 1. 宿主 ui-primitives 的桩：**从源码派生**，单一所有者在 scripts/lib/ks-primitives-stub.mjs ── */
  const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, stubDir)

  /* ── 2. 测试入口：把"挂载"这件事暴露出来 ── */
  const entry = join(stubDir, 'entry.mjs')
  await writeFile(entry, `
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import * as React from 'react'
import { KsKnowledgePage, KB_PAGE_SEARCH } from ${JSON.stringify(join(pluginRoot, 'client/KsKnowledgePage.tsx'))}

export { createElement, React, KB_PAGE_SEARCH }
export function mount(container, props) {
  const root = createRoot(container)
  root.render(createElement(KsKnowledgePage, props))
  return root
}
`, 'utf8')

  const out = join(stubDir, 'bundle.mjs')
  // ⚠ **必须把 react/react-dom 固定成唯一一份**（alias 到绝对路径），否则 "Invalid hook call"。
  await build({
    entryPoints: [entry],
    bundle: true,
    platform: 'node',
    format: 'esm',
    outfile: out,
    jsx: 'automatic',
    alias: {
      ...primitivesAlias,
      react: join(webNodeModules, 'react', 'index.js'),
      'react/jsx-runtime': join(webNodeModules, 'react', 'jsx-runtime.js'),
      'react-dom': join(webNodeModules, 'react-dom', 'index.js'),
      'react-dom/client': join(webNodeModules, 'react-dom', 'client.js'),
    },
    define: { 'process.env.NODE_ENV': '"test"' },
  })

  /* ── 3. 真 jsdom 环境 ── */
  const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url: 'http://localhost/' })
  globalThis.window = dom.window
  globalThis.document = dom.window.document
  // ⚠ Node 26 的 `globalThis.navigator` 是**只读 getter**，直接赋值抛 TypeError ⇒ 必须 defineProperty。
  Object.defineProperty(globalThis, 'navigator', {
    value: dom.window.navigator, configurable: true, writable: true,
  })
  globalThis.HTMLElement = dom.window.HTMLElement
  globalThis.Node = dom.window.Node
  globalThis.Event = dom.window.Event
  globalThis.requestAnimationFrame = (cb) => setTimeout(() => { cb(Date.now()) }, 0)
  globalThis.cancelAnimationFrame = (id) => { clearTimeout(id) }

  /* ══════════════════ HTTP 桩（本版新增；这一页现在真的调引擎） ══════════════════
   * 形状**逐字照** `src/core/api/routes_kb_folders.py` 的 docstring + 代码：
   *   · `GET /api/v1/kb/folders?parent_id=&limit=&offset=` → `data.{folder,breadcrumb,
   *     subfolders,total,offset,limit,has_more}`（**省略 parent_id = 最外层**，`folder: null`）
   *   · `GET /api/v1/kb/folders/{id}/items` → `data.{items,total,...}`（最外层传 `root`）
   *   · `POST /api/v1/kb/inbox/confirm` → `data.{confirmed,removed_from_pending}`
   *   · 真导入走引擎的 `POST /api/v1/ingest/bulk` + `.../resume` + `GET .../bulk/{id}`
   * 每一次请求都记进 `calls`，供"页面到底发了什么"的断言用（那是本版**有牙**的地方）。 */
  const API = 'http://127.0.0.1:1234'
  const TOKEN = 'stub-token'
  const calls = []
  const json = (payload, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  })
  const shapeFolder = (id, name, parentId, direct, deep, foldersDeep) => ({
    folder_id: id, parent_id: parentId, name, sort: 0, created_at: '2026-09-21 10:00:00',
    file_count_direct: direct, file_count_deep: deep, folder_count_deep: foldersDeep,
  })
  const F = {
    std: shapeFolder('fld_std', '标准', null, 0, 14, 3),
    law: shapeFolder('fld_law', '法律法规', null, 0, 2, 1),
    empty: shapeFolder('fld_empty', '空目录', null, 0, 0, 0),
    big: shapeFolder('fld_big', '大批量', null, 120, 120, 0),
    p16: shapeFolder('fld_p16', 'P16 工程防火', 'fld_std', 4, 4, 0),
    cca: shapeFolder('fld_cca', '宪法与行政法', 'fld_law', 2, 2, 0),
  }
  /** 某一级的**下级目录**（键 = folder_id，`'root'` = 最外层）。 */
  const SUBFOLDERS = {
    root: [F.std, F.law, F.empty, F.big],
    fld_std: [F.p16],
    fld_law: [F.cca],
    fld_p16: [],
    fld_cca: [],
    fld_empty: [],
    fld_big: [],
  }
  /** 某一级的**面包屑**（从最外层到本级）。 */
  const CRUMB = {
    root: [],
    fld_std: [F.std],
    fld_law: [F.law],
    fld_empty: [F.empty],
    fld_big: [F.big],
    fld_p16: [F.std, F.p16],
    fld_cca: [F.law, F.cca],
  }
  /* ── 「待分类」层的桩（第 4 步）：形状逐字照 `routes_kb_folders.py` 的 kb_inbox ──
     四篇覆盖四种档位 + 兜底桶（没有建议的那一篇，界面上**不许**渲染接受建议）。 */
  const INBOX_ITEMS = [
    { doc_id: 'doc_in_q', standard_no: 'GB/T 90001-2020', standard_name: '排队中的一篇',
      stage: 'queued', stage_label: '排队中', confidence: null, failure_kind: null,
      suggested_folder_id: F.p16.folder_id, suggested_path: '标准 › P 土木、建筑 › P16 工程防火',
      suggest_new_parent_id: null, suggest_new_name: null, catalog_hidden: 0,
      ccs_tag: 'CCS:P16 工程防火', ccs_outcome: 'found', ccs_outcome_label: '已补全',
      ccs_reason: null, ccs_source: 'official_api', ccs_checked_at: '2026-09-22 09:00:00' },
    { doc_id: 'doc_in_rec', standard_no: 'GB/T 90002-2020', standard_name: '识别中的一篇',
      stage: 'recognizing', stage_label: '识别中', confidence: null, failure_kind: null,
      suggested_folder_id: null, suggested_path: null,
      suggest_new_parent_id: null, suggest_new_name: null, catalog_hidden: 0,
      /* 查过了、没查到 ⇒ 界面上要写清**为什么**没有建议（业主口径）。 */
      ccs_tag: null, ccs_outcome: 'not_found',
      ccs_outcome_label: '查无（答话的站点里都没有这个号）',
      ccs_reason: '查无：答话的站点里都没有这个标准号', ccs_source: null,
      ccs_checked_at: '2026-09-22 09:00:00' },
    { doc_id: 'doc_in_ok', standard_no: 'GB/T 90003-2020', standard_name: '待确认的一篇',
      stage: 'confirming', stage_label: '待确认', confidence: 0.93, failure_kind: null,
      suggested_folder_id: F.p16.folder_id, suggested_path: '标准 › P 土木、建筑 › P16 工程防火',
      suggest_new_parent_id: F.p16.folder_id, suggest_new_name: 'P16 工程防火（新）',
      catalog_hidden: 0,
      ccs_tag: 'CCS:P16 工程防火', ccs_outcome: 'found', ccs_outcome_label: '已补全',
      ccs_reason: null, ccs_source: 'web_scrape', ccs_checked_at: '2026-09-22 09:00:00' },
    { doc_id: 'doc_in_bad', standard_no: 'GB/T 90004-2020', standard_name: '识别失败的一篇',
      stage: 'failed', stage_label: '识别失败', confidence: 0.4,
      failure_kind: '解析失败（正文条款为零）',
      suggested_folder_id: null, suggested_path: null,
      suggest_new_parent_id: null, suggest_new_name: null, catalog_hidden: 1,
      /* ⚠ **还没查过**（`ccs_outcome: null`）⇒ 界面那句"为什么没有建议"必须是第三种说法
         （"还没查过分类号"），**不许**把 null 编成"查无"或"查询失败"。 */
      ccs_tag: null, ccs_outcome: null, ccs_outcome_label: null, ccs_reason: null,
      ccs_source: null, ccs_checked_at: null },
  ]
  /** 整棵目录树的扁平清单（选择器用）：真形状那四级 + 顶层。 */
  const FLAT_FOLDERS = [
    { folder_id: F.std.folder_id, parent_id: null, name: '标准', path: '标准', depth: 1 },
    { folder_id: 'fld_p', parent_id: F.std.folder_id, name: 'P 土木、建筑',
      path: '标准 › P 土木、建筑', depth: 2 },
    { folder_id: 'fld_p1519', parent_id: 'fld_p', name: 'P15/19 工程抗震、工程防火、人防工程',
      path: '标准 › P 土木、建筑 › P15/19 工程抗震、工程防火、人防工程', depth: 3 },
    { folder_id: F.p16.folder_id, parent_id: 'fld_p1519', name: 'P16 工程防火',
      path: '标准 › P 土木、建筑 › P15/19 工程抗震、工程防火、人防工程 › P16 工程防火', depth: 4 },
    { folder_id: F.law.folder_id, parent_id: null, name: '法律法规', path: '法律法规', depth: 1 },
  ]
  /** 「重来一次」的状态（桩：起手 running，读一次之后 done）。 */
  let reingestRunning = false
  const reingestSeen = []
  /* ── 「补全分类号」（2026-09-22 自愈机制）的桩：形状逐字照 `ccs_backfill.ccs_backfill_status` ── */
  let ccsRunning = false
  let ccsSeen = []
  let ccsPolls = 0
  const CCS_LABELS = {
    found: '已补全',
    not_found: '查无（答话的站点里都没有这个号）',
    network_failed: '查询失败（网络不通/被拦，一个站点都没答上）',
    parse_failed: '读不出来（站点答了，但没有分类号或读不出条目）',
    not_applicable: '不适用（这一篇的标准号不像标准号，分类号对它不适用）',
  }
  /** 补全状态的有效载荷（形状 = `ccs_backfill.ccs_backfill_status()`）。 */
  const ccsStatusPayload = () => ({
    running: ccsRunning, total: ccsSeen.length, done: ccsRunning ? 1 : ccsSeen.length,
    found: 1, not_found: ccsRunning ? 0 : 1, network_failed: 0, parse_failed: 0,
    not_applicable: 0,
    applied: 1, skipped: 0, cancel_requested: false, cancelled: false,
    started_at: '2026-09-22 09:00:00',
    finished_at: ccsRunning ? null : '2026-09-22 09:00:05',
    missing: ccsRunning ? 2 : 1,
    results: ccsSeen.map((id) => ({ doc_id: id, standard_no: 'GB/T 90002-2020',
                                    outcome: id === 'doc_in_bad' ? 'not_found' : 'found',
                                    source: 'official_api', keyword_form: 'full',
                                    reason: id === 'doc_in_bad' ? '查无：答话的站点里都没有这个标准号' : undefined })),
    failures: ccsRunning ? [] : ccsSeen.filter((id) => id === 'doc_in_bad')
      .map((id) => ({ doc_id: id, standard_no: 'GB/T 90002-2020', outcome: 'not_found',
                      reason: '查无：答话的站点里都没有这个标准号' })),
    skipped_list: [],
  })
  const deletedDocs = []
  /* ── 第 5 步：目录/文件 CRUD 的**请求记录**（判"真的发没发、发的什么"就靠它们）── */
  const madeFolders = []
  const renamedFolders = []
  const movedFolders = []
  const copiedFolders = []
  const deletedFolders = []
  const memberOps = []
  /** `GET /kb/folders/{id}/delete-preview` 的桩：三个形态各一（空 / 一级 / 非空两层）。 */
  const DELETE_PREVIEW = {
    fld_std: { is_empty: false, direct_subfolder_count: 1, direct_file_count: 0,
      subtree_folder_count: 2, subtree_file_count: 4, reparent_available: true,
      files_kept_elsewhere: 1, files_would_be_deleted: 3 },
    fld_law: { is_empty: false, direct_subfolder_count: 1, direct_file_count: 0,
      subtree_folder_count: 2, subtree_file_count: 2, reparent_available: false,
      files_kept_elsewhere: 0, files_would_be_deleted: 2 },
    fld_empty: { is_empty: true, direct_subfolder_count: 0, direct_file_count: 0,
      subtree_folder_count: 1, subtree_file_count: 0, reparent_available: true,
      files_kept_elsewhere: 0, files_would_be_deleted: 0 },
    fld_p16: { is_empty: false, direct_subfolder_count: 0, direct_file_count: 4,
      subtree_folder_count: 1, subtree_file_count: 4, reparent_available: true,
      files_kept_elsewhere: 0, files_would_be_deleted: 4 },
  }
  /** 批量导入**终态**里那两个新字段（③a）：默认 0；某条判据会把它改成 1 再看界面说没说。 */
  let bulkStateMissing = 0
  const doc = (id, no, name, extra = {}) => ({
    doc_id: id, standard_no: no, standard_name: name,
    legal_status: 'effective', legal_hierarchy: 'GB', doc_type: 'standard',
    ccs_code: 'P16', ccs_name: '工程防火', published_at: '2017-05-27',
    effective_from: '2018-01-01', withdrawn_date: null, superseded_by: null,
    stage: 'filed', confidence: 0.93, failure_kind: null, suggested_folder_id: null,
    ...extra,
  })
  /** 4 篇文件的测试层（文件名/标准号取自原占位数据，好让"喷水"这种搜索串继续有意义）。 */
  const P16_DOCS = [
    doc('doc_fire_50016', 'GB 50016-2014', '建筑设计防火规范'),
    doc('doc_fire_55037', 'GB 55037-2022', '建筑防火通用规范'),
    doc('doc_fire_50084', 'GB 50084-2017', '自动喷水灭火系统设计规范'),
    doc('doc_fire_old', 'GB 50016-2006', '建筑设计防火规范（2006 版）',
      { legal_status: 'withdrawn', withdrawn_date: '2015-05-01', stage: 'failed', failure_kind: '表格' }),
  ]
  const CCA_DOCS = [
    doc('doc_law_safety', '', '中华人民共和国安全生产法', { legal_hierarchy: '法律', stage: 'confirming' }),
    doc('doc_law_fire', '', '中华人民共和国消防法', { legal_hierarchy: '法律', stage: 'queued' }),
  ]
  /** 「大批量」那一层：120 篇，用来验后端分页（limit=50 + has_more + offset）。 */
  const BIG_DOCS = Array.from({ length: 120 }, (_, i) =>
    doc(`doc_big_${String(i)}`, `GB/T 90${String(i).padStart(2, '0')}-2020`, `批量测试标准 ${String(i)}`))
  const ITEMS = {
    root: [], fld_std: [], fld_law: [], fld_empty: [],
    fld_p16: P16_DOCS, fld_cca: CCA_DOCS, fld_big: BIG_DOCS,
  }
  /** 导入前的"库快照"（`GET /api/v1/documents`）—— 每起一个 bulk 批次就往里加两篇（模拟真导入）。 */
  let docsInLib = [doc('doc_existing', 'GB 1-2000', '库里原有的一篇')]
  let bulkSeq = 0
  /* ⚠⚠ **2026-09-21（第 5 步）就地改成"两段式"桩**：真接口的 `resume` docstring 明写
     「**快扫完成后调用**」，而旧 UI 是 start 完**紧跟**着 resume —— 那是一条**竞态**
     （两次 `fast_scan` 抢写 checkpoint：`parsed=0` 与 `parsed=1` 复核都实测到过），
     实测到的那一次会把快扫打断、把已排好的队列覆盖成空，界面还说"没有新增文件"。
     桩现在按真相位走：`resume` 之前先报 `running`（快扫中）、再报 `paused/scan_complete`
     （等 resume），`resume` 之后才报 `done` + 解析数字 —— 这样"顺序错"会**当场红**。
     `bulkAddsHidden` = 这一批进来的文档**不出现在 `/api/v1/documents`** 里
     （`catalog_hidden=1` 那类：正文条款为零、被挡在目录外，只在「待分类」里可见）。 */
  let bulkResumed = false
  let bulkStatusPolls = 0
  let bulkAddsHidden = false
  const hiddenDocs = []
  /** 让 `/kb/folders` 返回 500（错误态那一条用）。 */
  let failFolders = false
  /* ── 第 6 步：按**知识库目录范围**提问 ──
     `askAnswerMode` 是"引擎这次怎么答"的开关：`in`（范围内有依据）/ `noscope`
     （**装作没收到范围** —— 界面必须当众标红，不许静默当成范围内检索）。
     `answerHold`（2026-09-22，复核 MEDIUM-2）：把**下一次** `/ks/answer` 卡住不返回，
     用来复现"问 A（慢）→ 换范围问 B → B 先回 → A 后回 ⇒ A 的答案盖在 B 的范围上"。
     `answerHeldScope` 记录那次被卡住的请求是哪个范围（证明"A 真的在飞"）。 */
  let askAnswerMode = 'in'
  let answerHold = null
  let answerHeldScope = null
  /**
   * 一个范围的**权威规模**：这些目录**及其所有下级**里的目录集合 + 文件集合。
   * ⚠ `/kb/scope/resolve` 与 `/ks/answer` 的桩**共用这一份算法** ⇒ 界面 chip 上的篇数
   *   与答案里回显的篇数**必然相等**；不等就说明界面自己编了个数。
   */
  const scopeOf = (rootIds) => {
    const folderIds = new Set()
    const docIds = new Set()
    const walk = (fid) => {
      if (folderIds.has(fid)) return
      folderIds.add(fid)
      for (const d of (ITEMS[fid] ?? [])) docIds.add(d.doc_id)
      for (const kid of (SUBFOLDERS[fid] ?? [])) walk(kid.folder_id)
    }
    for (const r of rootIds) walk(r)
    return { folder_ids: [...folderIds].sort(), doc_ids: [...docIds].sort() }
  }
  const knownFolder = (fid) => Object.values(F).some((f) => f.folder_id === fid) || fid === 'root'

  const levelOf = (rawParent) => {
    const id = rawParent === null || rawParent === '' ? 'root' : rawParent
    return {
      code: 200, status: 'success',
      data: {
        folder: id === 'root' ? null : (Object.values(F).find((f) => f.folder_id === id) ?? null),
        breadcrumb: CRUMB[id] ?? [],
        subfolders: SUBFOLDERS[id] ?? [],
        total: (SUBFOLDERS[id] ?? []).length,
        offset: 0, limit: 200, has_more: false,
      },
    }
  }
  const itemsOf = (folderId, offset, limit) => {
    const key = folderId === 'root' || folderId === 'null' ? 'root' : folderId
    const all = ITEMS[key]
    if (all === undefined) return { code: 404, status: 'error', error: { code: 'folder_not_found', message: `目录不存在: ${folderId}` } }
    const page = all.slice(offset, offset + limit)
    return {
      code: 200, status: 'success',
      data: {
        folder: key === 'root' ? null : (Object.values(F).find((f) => f.folder_id === key) ?? null),
        breadcrumb: CRUMB[key] ?? [],
        items: page, total: all.length, offset, limit,
        has_more: offset + page.length < all.length,
      },
    }
  }

  globalThis.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : String(input?.url ?? input)
    const method = String(init?.method ?? 'GET').toUpperCase()
    const body = typeof init?.body === 'string' && init.body !== '' ? init.body : null
    calls.push({ method, url, body })
    if (url === '/ks/session') {
      return json({ ok: true, engine: { port: 1234, pid: 42, reused: false }, token: TOKEN })
    }
    if (url === '/ks/ingest/inbox-default') {
      return json({ ok: true, data: { dir: 'D:\\KnowledgeStation\\待入库' } })
    }
    if (!url.startsWith(API)) return json({ ok: false, error: { code: 'STUB_MISS', message: `未预料的请求：${url}` } }, 404)
    const u = new URL(url)
    const p = u.pathname
    /* S2-a2：外发审计只读列表（第一个翻真的专门页）。脱敏摘要行照引擎 _row_to_audit 的字段。 */
    /* S2-b1：合规审查两段式（建任务抽点 → SSE 逐条执行）。SSE 桩 = 真 ReadableStream，
       帧格式照引擎 `_sse`（event: 名 / data: json / 空行）。 */
    /* S2-b2：义务清单/检查表 + 制度差距分析（形状逐字段抄 obligation.py / gap_analysis.py）。 */
    if (p === '/api/v1/compliance/obligations' && method === 'POST') {
      return json({ code: 200, data: { list_id: 'lst_1', business_description: '高处作业', count: 2, groups: [
        { group: 'GB 30871', items: [
          { clause_revision_id: 'rev_a', standard_no: 'GB 30871-2022', clause_number: '第4.1.1条', obligation_text: '高处作业应办理作业票', group: 'GB 30871', checked: false },
          { clause_revision_id: 'rev_b', standard_no: 'GB 30871-2022', clause_number: '第5.2.2条', obligation_text: '脚手架应验收后使用', group: 'GB 30871', checked: false },
        ] },
      ] } })
    }
    if (p === '/api/v1/compliance/obligations/lst_1/checklist' && method === 'POST') {
      return json({ code: 200, data: { list_id: 'lst_1', count: 2, mode: 'checklist', groups: [
        { group: 'GB 30871', items: [
          { clause_revision_id: 'rev_a', standard_no: 'GB 30871-2022', clause_number: '第4.1.1条', obligation_text: '高处作业应办理作业票', group: 'GB 30871', checked: true, question: '是否已落实：高处作业应办理作业票？' },
          { clause_revision_id: 'rev_b', standard_no: 'GB 30871-2022', clause_number: '第5.2.2条', obligation_text: '脚手架应验收后使用', group: 'GB 30871', checked: false, question: '是否已落实：脚手架应验收后使用？' },
        ] },
      ] } })
    }
    if (p === '/api/v1/compliance/obligations/lst_1/check' && method === 'POST') {
      return json({ code: 200, data: { updated: true } })
    }
    if (p === '/api/v1/compliance/policies' && method === 'POST') {
      return json({ code: 200, data: { policy_id: 'pol_1', sections: ['总则'] } })
    }
    if (p === '/api/v1/compliance/gap-analysis' && method === 'POST') {
      return json({ code: 200, data: { task_id: 'task_g', policy_name: '安全生产责任制',
        counts: { red: 1, yellow: 1, green: 0 },
        results: [
          { obligation: '高处作业应办理作业票', verdict: 'red', hit: ['作业票'], ratio: 0.8, suggestion: '建议在制度中新增对应条款，明确落实：高处作业应办理作业票。', domain: '安全' },
          { obligation: '脚手架应验收后使用', verdict: 'yellow', hit: [], ratio: 0.1, suggestion: '建议完善相关章节（总则），补：脚手架应验收后使用。', domain: '安全' },
        ] } })
    }
    if (p === '/api/v1/compliance/review' && method === 'POST') {
      return json({ code: 200, data: { task_id: 'task_X', status: 'pending', extracted_points: [
        { point_id: 'pt_1', point_type: '安全条款', point_content: '高处作业应办理作业票' },
        { point_id: 'pt_2', point_type: '环保条款', point_content: '废弃物应分类存放' },
      ] } })
    }
    if (p === '/api/v1/compliance/review/task_X/execute' && method === 'POST') {
      const sseFrame = (name, obj) => `event: ${name}\ndata: ${JSON.stringify(obj)}\n\n`
      const sse = [
        sseFrame('point_verdict', { point_id: 'pt_1', point_type: '安全条款', point_content: '高处作业应办理作业票', verdict: 'red', reason: '未见作业票要求。', matched_clauses: [{ clause_revision_id: 'rev_1', doc_id: 'doc_1', standard_no: 'GB 30871-2022', clause_number: '第4.1.1条', modality: '应', page_start: 7 }] }),
        sseFrame('point_verdict', { point_id: 'pt_2', point_type: '环保条款', point_content: '废弃物应分类存放', verdict: 'yellow', reason: '未命中明确法条，需人工复核。', matched_clauses: [] }),
        sseFrame('report_ready', { red_count: 1, yellow_count: 1, green_count: 0, report_path: 'exports/review_x.md' }),
        sseFrame('done', {}),
      ].join('')
      return {
        ok: true,
        status: 200,
        body: new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode(sse)); c.close() } }),
        json: async () => ({}),
        text: async () => sse,
      }
    }
    if (p === '/api/v1/egress/audit' && method === 'GET') {
      return json({
        code: 200,
        data: {
          total: 2,
          items: [
            { dump_id: 'dump_1', created_at: '2026-09-22 15:00', service: 'deepseek-chat', endpoint: '/v1/chat/completions', query: '高处作业怎么分级', payload_bytes: 512, prompt_preview: '把这一段发出去了' },
            { dump_id: 'dump_2', created_at: '2026-09-22 15:06', service: 'deepseek-chat', endpoint: '/v1/chat/completions', query: '动火作业分级', payload_bytes: 480, prompt_preview: '又发了一段' },
          ],
        },
      })
    }
    if (p === '/api/v1/kb/folders' && method === 'GET') {
      if (failFolders) return json({ code: 500, status: 'error', error: { code: 'boom', message: '桩：引擎装作读不了目录' } }, 500)
      return json(levelOf(u.searchParams.get('parent_id')))
    }
    /* ── 第 5 步：建目录（`POST /kb/folders`，形状照路由的 docstring）── */
    if (p === '/api/v1/kb/folders' && method === 'POST') {
      const b = JSON.parse(body ?? '{}')
      madeFolders.push({ parent_id: b.parent_id ?? null, name: b.name })
      return json({ code: 200, status: 'success', data: {
        folder_id: `fld_made_${String(madeFolders.length)}`, name: b.name,
        parent_id: b.parent_id ?? null, sort: 0, created_at: '2026-09-21 10:00:00' } })
    }
    /* ── 第 5 步：挪 / 复制 / 删前预览（三个子路径，先于「改名」那条通用匹配）── */
    const mFoldOp = /^\/api\/v1\/kb\/folders\/([^/]+)\/(move|copy|delete-preview)$/.exec(p)
    if (mFoldOp !== null) {
      const fid = decodeURIComponent(mFoldOp[1])
      const op = mFoldOp[2]
      if (op === 'delete-preview') {
        const prev = DELETE_PREVIEW[fid] ?? {
          is_empty: true, direct_subfolder_count: 0, direct_file_count: 0,
          subtree_folder_count: 1, subtree_file_count: 0, reparent_available: true,
          files_kept_elsewhere: 0, files_would_be_deleted: 0 }
        const row = Object.values(F).find((f) => f.folder_id === fid)
        return json({ code: 200, status: 'success', data: {
          folder: row ?? { folder_id: fid, parent_id: null, name: fid, sort: 0, created_at: null },
          ...prev } })
      }
      const b = JSON.parse(body ?? '{}')
      if (op === 'move') {
        movedFolders.push({ folder_id: fid, from_parent_id: b.from_parent_id ?? null,
          to_parent_id: b.to_parent_id ?? null })
        return json({ code: 200, status: 'success', data: {
          folder_id: fid, name: '桩', parent_id: b.to_parent_id ?? null,
          from_parent_id: b.from_parent_id ?? null, to_parent_id: b.to_parent_id ?? null,
          updated_main_position: true, moved: true } })
      }
      copiedFolders.push({ folder_id: fid, to_parent_id: b.to_parent_id ?? null, name: b.name ?? null })
      return json({ code: 200, status: 'success', data: {
        folder_id: 'fld_copy_1', name: `${String(b.name ?? '副本')} (副本)`,
        parent_id: b.to_parent_id ?? null, sort: 0, copied_members: 1, copied_from: fid } })
    }
    /* ── 第 5 步：改名（PUT）/ 删（DELETE ?mode=）── */
    const mFolderId = /^\/api\/v1\/kb\/folders\/([^/]+)$/.exec(p)
    if (mFolderId !== null && method === 'PUT') {
      const fid = decodeURIComponent(mFolderId[1])
      const b = JSON.parse(body ?? '{}')
      renamedFolders.push({ folder_id: fid, name: b.name })
      return json({ code: 200, status: 'success', data: {
        folder_id: fid, name: b.name, parent_id: null } })
    }
    if (mFolderId !== null && method === 'DELETE') {
      const fid = decodeURIComponent(mFolderId[1])
      const mode = u.searchParams.get('mode')
      deletedFolders.push({ folder_id: fid, mode })
      return json({ code: 200, status: 'success', data: {
        folder_id: fid, mode: mode ?? 'empty', removed: true,
        reparented_subfolders: 0, reparented_files: 0, purged_folders: 1,
        unfiled_docs: 0, deleted_docs: 0 } })
    }
    /* ── 第 5 步：成员拿掉 / 挪 / 复制（`members/remove|move|copy`）── */
    const mMemberOp = /^\/api\/v1\/kb\/members\/(remove|move|copy)$/.exec(p)
    if (mMemberOp !== null && method === 'POST') {
      const b = JSON.parse(body ?? '{}')
      const op = mMemberOp[1]
      memberOps.push({ op, body: b })
      return json({ code: 200, status: 'success', data: {
        folder_id: b.folder_id ?? '', from_folder_id: b.from_folder_id ?? '',
        to_folder_id: b.to_folder_id ?? '', added: op === 'copy' ? (b.items ?? []).length : 0,
        skipped: 0, removed: op === 'remove' ? (b.items ?? []).length : 0,
        moved: op === 'move' ? (b.items ?? []).length : 0, total: (b.items ?? []).length } })
    }
    const mItems = /^\/api\/v1\/kb\/folders\/([^/]+)\/items$/.exec(p)
    if (mItems !== null) {
      const offset = Number(u.searchParams.get('offset') ?? '0')
      const limit = Number(u.searchParams.get('limit') ?? '50')
      const r = itemsOf(decodeURIComponent(mItems[1]), offset, limit)
      return json(r, r.code === 200 ? 200 : 404)
    }
    if (p === '/api/v1/kb/inbox/confirm') {
      const decisions = JSON.parse(body ?? '{}').decisions ?? []
      return json({ code: 200, status: 'success', data: { confirmed: decisions.length, removed_from_pending: 0 } })
    }
    /* ── 第 4 步的四条（形状逐字照 `routes_kb_folders.py` + `reingest.py`）── */
    if (p === '/api/v1/kb/inbox') {
      const limit = Number(u.searchParams.get('limit') ?? '50')
      const offset = Number(u.searchParams.get('offset') ?? '0')
      const page = INBOX_ITEMS.slice(offset, offset + limit)
      return json({ code: 200, status: 'success', data: {
        items: page, total: INBOX_ITEMS.length, offset, limit,
        has_more: offset + page.length < INBOX_ITEMS.length,
      } })
    }
    if (p === '/api/v1/kb/stage-labels') {
      return json({ code: 200, status: 'success', data: {
        labels: { queued: '排队中', recognizing: '识别中', confirming: '待确认',
                  filed: '已归位', failed: '识别失败' },
        stages: ['queued', 'recognizing', 'confirming', 'filed', 'failed'],
        unfiled: ['queued', 'recognizing', 'confirming', 'failed'],
      } })
    }
    if (p === '/api/v1/kb/folders/flat') {
      const qq = String(u.searchParams.get('q') ?? '').toLowerCase()
      const rows = qq === '' ? FLAT_FOLDERS
        : FLAT_FOLDERS.filter((f) => f.path.toLowerCase().includes(qq))
      return json({ code: 200, status: 'success', data: {
        items: rows, total: rows.length, offset: 0, limit: 0, sep: ' › ' } })
    }
    if (p === '/api/v1/kb/inbox/reingest' && method === 'POST') {
      const ids = JSON.parse(body ?? '{}').doc_ids ?? []
      reingestSeen.push(...ids)
      reingestRunning = true
      return json({ code: 200, status: 'success', data: {
        queued: ids.length,
        started: ids.map((id) => ({ doc_id: id, path: 'D:\\待入库\\x.pdf', standard_no: 'GB/T 1-2020' })),
        skipped: [],
      } })
    }
    if (p === '/api/v1/kb/inbox/reingest/status') {
      /* 桩：第一次读到 running=true，之后 done（界面据此从"进行中"走到"完成"）。 */
      const wasRunning = reingestRunning
      reingestRunning = false
      return json({ code: 200, status: 'success', data: {
        running: wasRunning, total: reingestSeen.length, done: wasRunning ? 0 : reingestSeen.length,
        results: wasRunning ? [] : reingestSeen.map((id) => ({ doc_id: id, status: 'ok' })),
        started_at: '2026-09-21 10:00:00', finished_at: wasRunning ? null : '2026-09-21 10:00:05',
      } })
    }
    /* ── 「补全分类号」（2026-09-22 自愈机制）四条桩：
          形状逐字照 `routes_kb_folders.py` 的 kb_ccs_* 与 `ccs_backfill.ccs_backfill_status` ── */
    if (p === '/api/v1/kb/ccs/summary') {
      return json({ code: 200, status: 'success', data: {
        missing: ccsRunning ? 2 : 3,
        by_outcome: { found: 1, not_found: 1, network_failed: 0, parse_failed: 0,
                      not_applicable: 0 },
        max_batch: 200, default_batch: 50,
        outcome_labels: CCS_LABELS,
        source_labels: { official_api: '官方接口', web_scrape: '网页抓取',
                         local_table: '本地对照表', seed_file: '本地种子文件' },
        sources: ['official_api', 'web_scrape', 'local_table', 'seed_file'],
        backfill: ccsStatusPayload(),
      } })
    }
    if (p === '/api/v1/kb/ccs/plan') {
      return json({ code: 200, status: 'success', data: {
        candidates: [{ doc_id: 'doc_in_rec', standard_no: 'GB/T 90002-2020',
                       standard_name: '识别中的一篇' }],
        total: 3, already_have: 6037, limit: 0, truncated: false,
      } })
    }
    if (p === '/api/v1/kb/ccs/backfill' && method === 'POST') {
      ccsSeen = ['doc_in_rec', 'doc_in_bad']
      ccsRunning = true
      ccsPolls = 0
      return json({ code: 200, status: 'success', data: {
        queued: ccsSeen.length,
        started: ccsSeen.map((id) => ({ doc_id: id, standard_no: 'GB/T 90002-2020' })),
        skipped: [], plan: { candidates: [], total: 3, already_have: 6037, limit: 50, truncated: true },
      } })
    }
    if (p === '/api/v1/kb/ccs/backfill/status') {
      /* 桩：第一次 running，第二次 done + 失败清单（界面据此从"进行中"走到"结束 + 清单"）。 */
      ccsPolls += 1
      if (ccsPolls >= 2) ccsRunning = false
      return json({ code: 200, status: 'success', data: ccsStatusPayload() })
    }
    if (p === '/api/v1/kb/ccs/backfill/cancel' && method === 'POST') {
      ccsRunning = false
      return json({ code: 200, status: 'success', data: {
        cancel_requested: true, running: false, done: 1, total: 2 } })
    }
    if (p === '/api/v1/documents/batch-delete' && method === 'POST') {
      const ids = JSON.parse(body ?? '{}').doc_ids ?? []
      deletedDocs.push(...ids)
      return json({ code: 200, status: 'success', data: { deleted: ids.length } })
    }
    if (p === '/api/v1/kb/members') {
      const items = JSON.parse(body ?? '{}').items ?? []
      return json({ code: 200, status: 'success', data: { folder_id: JSON.parse(body ?? '{}').folder_id, added: items.length, skipped: 0, total: items.length } })
    }
    if (p === '/api/v1/documents') {
      return json({ code: 200, status: 'success', data: docsInLib })
    }
    if (p === '/api/v1/ingest/bulk' && method === 'POST') {
      bulkSeq += 1
      bulkResumed = false
      bulkStatusPolls = 0
      const batchId = `bulk_${String(bulkSeq)}`
      const made = [doc(`${batchId}_a`, 'GB 70000-2026', `新导入的一篇 A（${batchId}）`),
        doc(`${batchId}_b`, 'GB 70001-2026', `新导入的一篇 B（${batchId}）`)]
      if (bulkAddsHidden) hiddenDocs.push(...made)      // 只在库里，不在 /documents 里
      else docsInLib = [...docsInLib, ...made]
      return json({ code: 200, status: 'success', data: { batch_id: batchId, total: 2 } })
    }
    if (/^\/api\/v1\/ingest\/bulk\/[^/]+\/resume$/.test(p)) {
      bulkResumed = true
      return json({ code: 200, status: 'success', data: { batch_id: p.split('/')[5] } })
    }
    if (/^\/api\/v1\/ingest\/bulk\/[^/]+$/.test(p)) {
      const common = {
        batch_id: p.split('/')[5], pause_reason: null,
        /* ③a（第 5 步）：终态里必须能看出"这批里有没有文件的状态没写进库"。 */
        filing_state_missing: bulkStateMissing,
        filing_state_missing_sample: bulkStateMissing > 0 ? ['missing.pdf'] : [],
        reingest: false,
      }
      if (!bulkResumed) {
        bulkStatusPolls += 1
        if (bulkStatusPolls < 2) {
          const running = { code: 200, status: 'success', data: {
            ...common, status: 'running', scanned: 0, total: 0, parsed: 0, pending: 0, errors: 0 } }
          /* ⚠ R2：把**响应体**挂到这一次请求记录上（K3b 要判"resume 之前到底看到了什么"）。 */
          calls[calls.length - 1].resp = running.data
          return json(running)
        }
        const scanned = { code: 200, status: 'success', data: {
          ...common, status: 'paused', pause_reason: 'scan_complete',
          scanned: 2, total: 2, parsed: 0, pending: 0, errors: 0 } }
        calls[calls.length - 1].resp = scanned.data
        return json(scanned)
      }
      return json({ code: 200, status: 'success', data: {
        ...common, status: 'done', total: 2, scanned: 2, parsed: 2, pending: 0, errors: 0 } })
    }
    /* ── 第 6 步：范围解析（`POST /kb/scope/resolve`；形状照 routes_kb_folders.py 的
          kb_scope_resolve：folder_ids 含所有下级、doc_ids 去重排序、任一目录不存在 ⇒ 404）── */
    if (p === '/api/v1/kb/scope/resolve' && method === 'POST') {
      const roots = JSON.parse(body ?? '{}').folder_ids ?? []
      const bad = roots.filter((r) => !knownFolder(r))
      if (bad.length > 0) {
        return json({ code: 404, status: 'error', error: {
          code: 'folder_not_found', message: `目录不存在: ${bad[0]}` } }, 404)
      }
      const sc = scopeOf(roots)
      return json({ code: 200, status: 'success', data: {
        folder_ids: sc.folder_ids, doc_ids: sc.doc_ids,
        folder_count: sc.folder_ids.length, doc_count: sc.doc_ids.length, roots } })
    }
    /* ── 第 6 步：取证答案（`POST /ks/answer`；形状照 server.ks_answer_endpoint 的 `{code,status,data}`）── */
    if (p === '/api/v1/ks/answer' && method === 'POST') {
      const pr = JSON.parse(body ?? '{}').params ?? {}
      const roots = Array.isArray(pr.kb_folder_ids) ? pr.kb_folder_ids : []
      const docs = Array.isArray(pr.kb_doc_ids) ? pr.kb_doc_ids : []
      const sc = scopeOf(roots)
      /* 篇数 = 目录子树里的 ∪ 显式文件（一篇挂多处只算一次 —— 与引擎同一口径）。 */
      const docCount = new Set([...sc.doc_ids, ...docs]).size
      const echo = { kind: 'kb', folder_ids: roots, folder_count: sc.folder_ids.length,
        doc_count: docCount, empty: docCount === 0 }
      if (askAnswerMode === 'noscope') {
        return json({ code: 200, status: 'success', data: {
          tier: 'reference', evidence: [], derivation: '', conclusion: '',
          notes: ['桩：引擎装作没收到范围'], scope: null } })
      }
      if (docCount === 0) {
        /* 空范围：**一次检索都不做**（引擎侧就是这么写的），如实说"范围内没有"。 */
        return json({ code: 200, status: 'success', data: {
          tier: 'reference', evidence: [], derivation: '', conclusion: '',
          notes: ['【知识库目录范围】范围内没有文件，没有做任何检索。'], scope: echo } })
      }
      /* ⚠ 结论里带上**这一篇/这个目录**的标记：这样 R19（慢答案 vs 新答案）能一眼看出
         屏幕上留着的答案到底是哪一次问的（A=fld_std / B=fld_law）。 */
      const rootTag = roots[0] ?? docs[0] ?? 'x'
      /* ⚠ MEDIUM-2 的复现开关：这一次请求**卡住不返回**（记下它是哪个范围，证明它真在飞）。 */
      if (answerHold !== null) {
        const gate = answerHold
        answerHold = null
        answerHeldScope = rootTag
        await gate
      }
      return json({ code: 200, status: 'success', data: {
        tier: 'standard',
        evidence: [{ clause_revision_id: `cr_${roots[0] ?? 'x'}`, doc_id: sc.doc_ids[0] ?? docs[0],
          standard_no: 'GB 55037-2022', clause_number: '5.2.3', title: '建筑防火通用规范',
          legal_status: 'effective', legal_hierarchy: 'GB', page_start: 12,
          snippet: '桩：这一条来自范围内那批文档。', effective_from: '2023-06-01' }],
        derivation: '桩推导：范围内的依据支持这个结论。',
        conclusion: `桩结论：范围内答得出（${rootTag}）。`,
        notes: ['【知识库目录范围】检索已在范围内限定。'], scope: echo } })
    }
    return json({ ok: false, error: { code: 'STUB_MISS', message: `未预料的请求：${url}` } }, 404)
  }

  const { mount, KB_PAGE_SEARCH } = await import(pathToFileURL(out).href)
  // ⚠ **刻意不用 `act`**（React 18.3 的 act 会把第二份 react/react-dom 引进来）。每次交互后 flush。
  const flush = async () => { await new Promise((r) => { setTimeout(r, 0) }) }
  /* ⚠ 第 5 步（2026-09-21）：导入那条路里页面**真的会等**（快扫握手 1s 一轮、解析 2s 一轮），
     而 `flush` 只推进一个 0ms 的宏任务 ⇒ 断言会跑在"正在快扫…"那一句上（本批实测：
     K3/K4/K6/K7/P30/P31 一起假红）。这里给一个"真等一会儿"的助手：只在导入那几跳用它。 */
  const waitMs = async (ms) => { await new Promise((r) => { setTimeout(r, ms) }) }

  const container = document.getElementById('root')
  /** 页面要的两个 prop：`useTabInfo`（框架给的运行时）与注入面 `dataSource`。 */
  const useTabInfo = () => ({ tab: { navigation: { params: { page: 'manage' } } } })

  const root = mount(container, { useTabInfo, dataSource: 'render-smoke' })
  await flush(); await flush(); await flush()

  const q = (sel) => [...container.querySelectorAll(sel)]
  const click = async (el) => {
    el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, cancelable: true }))
    await flush(); await flush()
  }
  const setInput = async (el, value) => {
    // ⚠ 受控 input 必须走**原生 setter**：直接 `el.value = x` 会被 React 的 value tracker
    //   判定为"没变化"而**不触发 onChange**。
    const nativeSetter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set
    nativeSetter.call(el, value)
    el.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
    await flush(); await flush()
  }
  /** 目录行（右侧列表里那一层）。 */
  const dirRows = () => q('.ks-dir-row')
  const dirNameOf = (row) => (row?.querySelector('.ks-col-dname .ks-dir-name')?.textContent ?? '').trim()
  const dirNamed = (text) => dirRows().find((row) => dirNameOf(row).includes(text))
  /** 文件行（右侧列表里的这一级文件）。 */
  const fileRows = () => q('.ks-item.ks-file-row')
  const fileNameOf = (row) => (row?.querySelector('.ks-item-name')?.textContent ?? '').trim()
  /** 面包屑的逐段文本与"哪些段可点"。 */
  const crumbItems = () => q('.ks-crumb-item').map((el) => ({
    text: (el.textContent ?? '').trim(),
    clickable: el.querySelector('.ks-crumb-go') !== null,
  }))
  const crumbText = () => crumbItems().map((c) => c.text).join('/')
  const backBtn = () => q('.ks-back')[0]
  const treeRows = () => q('.ks-tree-row')
  const treeNames = () => q('.ks-tree-name .ks-tree-label').map((el) => (el.textContent ?? '').trim())
  const searchInput = () => q('.ks-search input')[0]
  const clearSearch = async () => { if (searchInput() !== undefined) await setInput(searchInput(), '') }
  const callsOf = (needle) => calls.filter((c) => c.url.includes(needle))
  const lastCallOf = (needle) => callsOf(needle).slice(-1)[0]
  /** 子元素类名序列（按 `.ks-cell` 的类名算列身份）。 */
  const cellClasses = (row) => [...row.children].map((el) => el.className)

  // ── 断言 1：真渲染出来了（不是空壳） ──
  check('页面挂载成功且渲染出内容（真 DOM）',
    container.innerHTML.length > 500,
    `${container.innerHTML.length} 字符`)

  // ── 断言 2：样式确实被注入（运行时 <style>，我们的偏离方案） ──
  const styleEl = document.getElementById('ks-dsh-plugin-styles')
  /* ⚠ 判据必须是**真声明**（`选择器{属性:值`），不是"文本里出现过这个名字"：本文件第一版写的是
     `.includes('.ks-kb-tree')` —— 而**注释里**也写着这个类名 ⇒ 样式表被截断（CSS 整段没进产物）时
     它照样 PASS（本批实测：模板被行尾转义的反引号截断，`.ks-kb-tree` 之后的规则全丢，而这条断言是绿的）。
     ⇒ 现在钉两条真声明：左列目录树的 flex、以及列表容器的列变量。 */
  const styleText = styleEl?.textContent ?? ''
  check('运行时注入了样式表（id=ks-dsh-plugin-styles，含 `.ks-kb-tree{…flex:0 0 168px` 与 `.ks-list{--ks-col-status` 两条**真声明**）',
    styleEl !== null
    && /\.ks-kb-tree\s*\{[^}]*flex:0 0 168px/.test(styleText)
    && /\.ks-list\s*\{[^}]*--ks-col-status/.test(styleText),
    styleEl === null ? '没有 <style>' : `${styleText.length} 字符；`
      + `含 .ks-kb-tree 规则=${String(/\.ks-kb-tree\s*\{/.test(styleText))} / `
      + `含 .ks-list 规则=${String(/\.ks-list\s*\{/.test(styleText))}`)
  check('样式标签带 data-plugin + data-plugin-css（宿主的样式所有权按这两个属性认）',
    styleEl !== null
    && styleEl.dataset.plugin === 'ks-dsh-plugin'
    && styleEl.dataset.pluginCss === 'ks-dsh-plugin/ksGuideStyles.css',
    styleEl === null ? '没有 <style>' : `data-plugin=${styleEl.dataset.plugin} data-plugin-css=${styleEl.dataset.pluginCss}`)

  /* ══════════ 断言 3j：**页面留边**（5j，2026-09-20；业主：「窗口四周要留点边啊」） ══════════
   * ⚠ 本侧没有布局引擎（jsdom 的 getBoundingClientRect 恒 0）⇒ 只能钉**声明与结构**；
   *   **像素级**由 `ui-render-shot.mjs` 的 `ksPadCheck` 在真 Chrome 里判（两侧合起来才算钉住）。
   * ⚠ 期望值是**冻结的规范值**（与 ui-render-shot.mjs 顶部的 PAGE_PAD_* 必须同值），
   *   并与注入样式表里的 token 定义互相核对。 */
  const PAGE_PAD_X_NARROW = 16
  const PAGE_PAD_X_WIDE = 24
  const PAGE_PAD_BREAKPOINT = 660
  const pageWrap = q('.ks-page')
  const kbRoot = q('.ks-kb')[0] ?? null
  check('页面留边：页面根外面有一层 `.ks-page` 容器（宽/窄两档就是按**它**的宽度切的）',
    pageWrap.length === 1 && kbRoot !== null && kbRoot.parentElement === pageWrap[0],
    `根数 .ks-page=${pageWrap.length} / .ks-kb=${q('.ks-kb').length}；`
      + `.ks-kb 的父元素类名=${JSON.stringify(kbRoot?.parentElement?.className ?? null)}`)
  const rootCs = kbRoot === null ? null : dom.window.getComputedStyle(kbRoot)
  const rootPad = rootCs === null
    ? { l: null, r: null, t: null, b: null }
    : {
        l: rootCs.getPropertyValue('padding-left').trim(),
        r: rootCs.getPropertyValue('padding-right').trim(),
        t: rootCs.getPropertyValue('padding-top').trim(),
        b: rootCs.getPropertyValue('padding-bottom').trim(),
      }
  const padOk = (v) => v === 'var(--ks-page-pad-x)' || v === 'var(--ks-page-pad-y)'
    || v === `${String(PAGE_PAD_X_NARROW)}px` || v === `${String(PAGE_PAD_X_WIDE)}px`
  check('页面留边：页面根的 padding 四个方向都走留边 token（不是 0、不是现场拍的数字）',
    rootPad.l !== null && [rootPad.l, rootPad.r].every(padOk) && [rootPad.t, rootPad.b].every(padOk),
    `padding 左=${JSON.stringify(rootPad.l)} 右=${JSON.stringify(rootPad.r)} `
      + `上=${JSON.stringify(rootPad.t)} 下=${JSON.stringify(rootPad.b)}`)
  const sheetText = styleEl?.textContent ?? ''
  const tokenOf = (name) => {
    const m = new RegExp(`--${name}\\s*:\\s*(\\d+)px`).exec(sheetText)
    return m === null ? null : Number(m[1])
  }
  // ⚠ 只认**页面留边那一条** @container（body 里出现 .ks-page）：本表里另有一条给 .ks-list 切列档的。
  let bpFound = null
  for (const m of sheetText.matchAll(/@container\s*\(min-width:\s*(\d+)px\)\s*\{([^}]*)\}/g)) {
    if (m[2].includes('.ks-page')) { bpFound = Number(m[1]); break }
  }
  check('页面留边：注入样式表里的两档 token 与阈值 = 规范的冻结值（窄 16 / 宽 24 / 阈值 660）',
    tokenOf('ks-page-pad-x-narrow') === PAGE_PAD_X_NARROW
    && tokenOf('ks-page-pad-x-wide') === PAGE_PAD_X_WIDE
    && bpFound === PAGE_PAD_BREAKPOINT,
    `--ks-page-pad-x-narrow=${JSON.stringify(tokenOf('ks-page-pad-x-narrow'))} `
      + `--ks-page-pad-x-wide=${JSON.stringify(tokenOf('ks-page-pad-x-wide'))} `
      + `@container=${JSON.stringify(bpFound)}`)
  /* 适用面（与 UI-BASELINE 第二节逐条一致）：
     ⚠ **2026-09-21（第 3 步）就地更新**：卡片带 `.ks-kbband` 与批量条 `.ks-batch` **已删**
     （业主"大卡片去掉" + 批量动作不在本批）⇒ 从适用面里去掉；新增 `.ks-kb-tree`
     （左列目录树，必须不贴边）。三处副本（规范第二节 / ui-render-shot 的 PAD_SUBJECTS_ALL
     / smoke-kb-pad-pixels 的 SPEC_SUBJECTS）同批一起改 —— 这是那三处棘轮要求的。 */
  const PAD_SUBJECTS = ['.ks-kb-tree', '.ks-list', '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-empty-card']
  const outside = []
  const negMargin = []
  for (const sel of PAD_SUBJECTS) {
    for (const el of q(sel)) {
      if (pageWrap.length === 1 && !pageWrap[0].contains(el)) outside.push(sel)
      const cs = dom.window.getComputedStyle(el)
      for (const prop of ['margin-left', 'margin-right']) {
        const v = parseFloat(cs.getPropertyValue(prop))
        if (Number.isFinite(v) && v < 0) negMargin.push(`${sel} ${prop}=${String(v)}`)
      }
    }
  }
  const presentSubjects = PAD_SUBJECTS.filter((sel) => q(sel).length > 0)
  /* ⚠ "至少有一个"不算判过（5j-补复核打回 E① 的 M6：把 `.ks-dirs` 的类名改掉让它整个消失
     ⇒ 旧判据照样 PASS）⇒ 按**这一跑所处状态的声明集合**逐类判存在性。 */
  const PAD_REQUIRED_DEFAULT_STATE = ['.ks-kb-tree', '.ks-dirs', '.ks-page-head', '.ks-kb-row']
  const missingHere = PAD_REQUIRED_DEFAULT_STATE.filter((sel) => q(sel).length === 0)
  check('页面留边：默认态该有的适用面元素一个不少（.ks-kb-tree/.ks-dirs/.ks-page-head/.ks-kb-row）',
    missingHere.length === 0,
    missingHere.length === 0
      ? '4 类都在（本状态不判 .ks-list/.ks-empty-card：它们的存在性由本文件后面的断言强制）'
      : `**没量到**：${missingHere.join(' ')}（元素消失/改名 ⇒ 留边管不到它；量不到不算验过）`)
  check('页面留边：目录列/表格容器/页头/按钮行/空态卡**全都在页面根之内**（跑到容器外面就说明留边管不到它）',
    outside.length === 0,
    presentSubjects.length === 0
      ? '这一跑一个适用面元素都没出现（那这条断言等于没判）'
      : `这一跑出现 ${presentSubjects.length} 类：${presentSubjects.join(',')}；越界：${JSON.stringify(outside)}`)
  check('页面留边：适用面元素没有用负外边距把留边抵消掉（负 margin 是"绕过留边"的典型写法）',
    negMargin.length === 0,
    negMargin.length === 0 ? '无负 margin' : negMargin.join(' | '))

  /* ══════════ A. **有牙**：页面真的接了库（这一版的核心新断言） ══════════
   * 这三条是"真接了库"与"还是样板"的分水岭：样板页一个请求都不发、也不可能有后端给的名字。 */
  const rootFoldersCall = calls.find((c) => c.url.includes('/api/v1/kb/folders?'))
    ?? calls.find((c) => c.url.endsWith('/api/v1/kb/folders'))
  check('A1 页面真的发起了 `GET /api/v1/kb/folders`（不带 parent_id = 最外层）—— 样板页一个请求都不发',
    rootFoldersCall !== undefined && !rootFoldersCall.url.includes('parent_id='),
    `请求：${rootFoldersCall === undefined ? '(没发)' : rootFoldersCall.url}`)
  check('A2 真发了列表请求 + 文件请求（最外层传 folder_id=root）',
    calls.filter((c) => c.url.includes('/api/v1/kb/folders') && !c.url.includes('/items')).length >= 1
    && calls.some((c) => c.url.includes('/api/v1/kb/folders/root/items')),
    `folders 请求 ${String(calls.filter((c) => c.url.includes('/api/v1/kb/folders') && !c.url.includes('/items')).length)} 次 / `
      + `items 请求 ${String(calls.filter((c) => c.url.includes('/items')).length)} 次`)
  const stubTopNames = ['标准', '法律法规', '空目录', '大批量']
  const shownOnPage = stubTopNames.filter((n) => (container.textContent ?? '').includes(n))
  check('A3 桩里那 4 个顶层目录名**真的出现在页面上**（不再显示样板里的假目录/假文档）',
    shownOnPage.length === 4,
    `出现 ${shownOnPage.length}/4：${shownOnPage.join(' / ')}`)
  /* ⚠⚠ **2026-09-22（业主点名删"AI 味"文案）新增这条负向判据**（结构层，补字符串层那三条）：
     业主原话：「…这种话为什么要放进来，AI 味很重；还有这个 `真库：左边目录、右边当前这一层`
     这个放在这里干什么。把这种 AI 味道很重的、也没啥实际功能的描述都去掉。」
     ⇒ 顶部那两处**连同容器**都已删：标题下那行副标题（`.ks-page-sub`）与那条 ⓘ 说明条
     （`.ks-kb-banner`）。**判"容器真的没了"比判字符串更硬**：换个说法把说明条放回来也红。
     ⚠ 这两个类**没从样式里删**（能力页 `KsCapabilityPage` 与本页"尚未实现"的占位条仍在用）
     ⇒ 本条只判**这个页头里**没挂着它们；**标题本身必须还在**（别顺手把整块页头删了）。 */
  const headTitle = (q('.ks-page-title')[0]?.textContent ?? '').trim()
  check('A4 页头里**不再有**那两处"AI 味"文案的容器（`.ks-page-sub` 副标题 / `.ks-kb-banner` ⓘ 说明条）'
    + '，而页面标题仍在 —— 业主 2026-09-22 点名删',
    q('.ks-page-title').length === 1 && headTitle === '知识库'
    && q('.ks-page-sub').length === 0 && q('.ks-kb-banner').length === 0,
    `标题 ${String(q('.ks-page-title').length)} 个（文字=「${headTitle}」）`
      + ` / .ks-page-sub ${String(q('.ks-page-sub').length)} 个 / .ks-kb-banner ${String(q('.ks-kb-banner').length)} 个`)

  /* ══════════ B. 左列目录 + 右侧只显示当前这一级 ══════════ */
  /* ⚠⚠ **2026-09-21（第 4 步）就地改判据（原文见下）**：这一条原来钉的树形状是
     「最外层 / 标准 / 法律法规 / 空目录 / 大批量」（4 个一级目录）。
     第 4 步在左列加了**「待分类」那一行**（它是**页面上的一层**，不在 `folder` 表里；
     位置在最外层之后、一级目录之前）⇒ 树形状**多一行**。判据改成新的真形状，
     并且**额外要求那一行真的是"待分类"**（不是随便多了一行还能过）。 */
  check('B1 左列是**真目录列**（.ks-kb-tree + 最外层行 + 「待分类」层 + 4 个一级目录），可滚动容器在',
    q('.ks-kb-tree').length === 1 && q('.ks-tree-body').length === 1
    && q('.ks-tree-name-inbox').length === 1
    && treeNames().slice(0, 6).join('/') === '最外层/待分类/标准/法律法规/空目录/大批量',
    `树里：${treeNames().join(' / ')}`)
  check('B2 落在最外层：右侧只列**下级目录**（4 行）、0 行文件，且目录层是**与文件列表同构的列表**',
    dirRows().length === 4 && fileRows().length === 0
    && q('.ks-list-dirs.ks-dirs').length === 1 && q('.ks-list-dirs .ks-lhead').length === 1,
    `目录行 ${String(dirRows().length)} / 文件行 ${String(fileRows().length)} / `
      + `.ks-list-dirs ${String(q('.ks-list-dirs').length)}`)
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据**：目录层加了**勾选列**（`dpick`）——
     批量挪/复制/删目录要用它。列数因此 3 → 4（`DIR_COLUMNS` 里一条新声明）。
     判据本身（"表头与每一行的 cell 类名序列逐字相同"+"列数 = DIR_COLUMNS 的条数"）**一个字没放宽**，
     只是那个数跟着声明变了；谁单方面改声明（少写一列 / 多写一列）仍然红。 */
  check('B3 目录层：表头与每一行的 cell 类名序列**逐字相同**（两侧都按同一份 DIR_COLUMNS 渲染，列数 4）',
    q('.ks-list-dirs .ks-lhead').length === 1 && dirRows().length > 0
    && cellClasses(q('.ks-list-dirs .ks-lhead')[0]).join('|') === cellClasses(dirRows()[0]).join('|')
    && cellClasses(dirRows()[0]).length === 4,
    `表头 ${cellClasses(q('.ks-list-dirs .ks-lhead')[0]).join('|')} / 行 ${cellClasses(dirRows()[0]).join('|')}`)
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据**：目录行从 button 变成 div（行内要有勾选框 + ⋮ 两个
     真控件），"图标 + 名字"因此从 `.ks-col-dname` 的直接子元素变成**里面那个 `.ks-dir-open` 按钮**
     的子元素 ⇒ 旧断言 `children.length === 2` 不再成立。判的**意思没变**：名字那一格只有
     "图标 + 名字 + 进入箭头"三样，**不许印内部 key / 内部路径**（那个第二行早就删了）。 */
  check('B4 目录行显示"共多少篇"（来自后端 file_count_deep），且名字那一格只有图标+名字+进入箭头（不印内部 key/路径）',
    dirNamed('标准') !== undefined
    && (dirNamed('标准').textContent ?? '').includes('14 篇')
    && (dirNamed('标准').querySelector('.ks-col-dname .ks-dir-open')?.children.length ?? 0) === 3
    && (dirNamed('标准').querySelector('.ks-dir-name')?.textContent ?? '').trim() === '标准',
    `「标准」那一行的文本：${(dirNamed('标准')?.textContent ?? '').trim()}`)
  check('B5 顶层**如实**说"你在最外层"，返回按钮 disabled（没有上一级可回）',
    (container.textContent ?? '').includes('你在最外层')
    && backBtn() !== undefined && backBtn().disabled === true
    && crumbText() === '知识库' && crumbItems().every((c) => c.clickable === false),
    `面包屑「${crumbText()}」/ 返回 disabled=${String(backBtn()?.disabled)}`)
  check('B6 左列当前这一级**高亮**（最外层那行的 data-on=true，且只有它一个）',
    treeRows().filter((r) => r.dataset.on === 'true').length === 1
    && q('.ks-tree-row[data-on="true"] .ks-tree-label')[0]?.textContent?.trim() === '最外层',
    `高亮行：${q('.ks-tree-row[data-on="true"] .ks-tree-label').map((e) => e.textContent).join(',')}`)
  /* ⚠⚠ **2026-09-21 复核 `verify-freeze-kb-ui3` 打回 §④-C：这三条是"主体仍在、断言却没了"。**
     复核的变异 M4（把目录层列头 `head:'篇数'` 改成 `''`）⇒ 当时那一版 68/68 + 三档 + 14 组**全绿**，
     渲染里表头只剩「目录」—— 旧版第 25 条判的正是它。下面三条按**同一条纪律**补回来：
     判的是**当前页面上真的渲染出来的东西**（文案 / title / 同一个父元素），不是源码字面量。 */
  const dirHeadTexts = () => q('.ks-list-dirs .ks-lhead .ks-cell')
    .map((el) => (el.textContent ?? '').trim())
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据**：列头多了一个**无列头的勾选列**（在最前）⇒
     期望串从 `目录|篇数|` 变成 `|目录|篇数|`（末列仍是无列头的 ⋮ 操作列）。
     判的仍是"列头文案**逐字**就是这两样"—— 清空/改字仍然红（复核 M4 那一课不重演）。 */
  check('B7 目录层列头文案就是「目录 / 篇数」（勾选列与行尾操作列无列头）—— 复核 M4：清空列头曾能全绿',
    dirHeadTexts().join('|') === '|目录|篇数|',
    `列头=${JSON.stringify(dirHeadTexts())}`)
  check('B8 目录行：名字文本 == 它自己的 title（悬停提示与显示的名是同一个，不是各写一份）',
    dirRows().length === 4 && dirRows().every((r) => {
      const nameEl = r.querySelector('.ks-dir-name')
      return nameEl !== null && (nameEl.textContent ?? '').trim() === (nameEl.getAttribute('title') ?? '').trim()
        && (nameEl.textContent ?? '').trim() !== ''
    }),
    dirRows().map((r) => {
      const n = r.querySelector('.ks-dir-name')
      return `${(n?.textContent ?? '').trim()}=${(n?.getAttribute('title') ?? '').trim()}`
    }).join(' | '))
  check('B9 目录层：列头行与数据行是**同一个容器的直接子元素**（不是各挂一层，样式一改就错位）',
    q('.ks-list-dirs .ks-lhead').length === 1 && dirRows().length === 4
    && q('.ks-list-dirs .ks-lhead')[0].parentElement === dirRows()[0].parentElement,
    `表头父级=${String(q('.ks-list-dirs .ks-lhead')[0]?.parentElement?.className)} / `
      + `行父级=${String(dirRows()[0]?.parentElement?.className)}`)
  /* ⚠ **2026-09-22（业主界面要求）新增**：文件行的图标删掉之后，**目录行的文件夹图标必须还在**
     —— 业主原话「文件夹前面一个小文件夹图标做得好」（删的是**文件**前面那个）。
     两个方向都要判：只判"文件行没有"会把"顺手把目录行的也删了"放过去。 */
  check('B10 目录行前面的**文件夹图标还在**（业主说它做得好；删除只针对文件行那个）',
    dirRows().length === 4 && dirRows().every((r) => {
      const ico = r.querySelector('.ks-dir-open .ks-fileico')
      return ico !== null && ico.querySelector('svg') !== null
        && (ico.getAttribute('title') ?? '').trim() === '目录'
    }),
    `目录行图标：${dirRows().map((r) => (r.querySelector('.ks-dir-open .ks-fileico')?.getAttribute('title') ?? '(没有)')).join('/')}`)

  /* ══════════ C. 卡片带与"只改内存"的假动作**真的没了** ══════════
     ⚠⚠ **2026-09-21（第 4 步）就地改判据（原文保留在下面，别删）**：
     这两条原来判的是"`.ks-batch` 计数恒 0 + `input[type=checkbox]` 恒 0"
     （= 第 3 步按"不许留假动作"把**假的**批量条与勾选拆干净）。
     第 4 步把**真的**批量做回来了（每条动作都对应真接口：confirm / reingest /
     batch-delete）⇒ 那两句**不再成立**，但判据不许删、不许放宽，改成判**新的真行为**：
       · 卡片带仍然恒 0（那一块界面是真的没了，没变）；
       · **没勾选时批量条必须是 0**（挂着一条空条子就是"看着能点、其实没有对象"）；
       · 勾选列**只出现在「待分类」层**（目录层/文件层不许冒出勾选框 —— 那两层本批没做批量）。 */
  check('C1 卡片带**整块删除**（.ks-kbband* 恒 0）+ 没勾选时**没有**批量条（空的条子等于假动作）',
    q('.ks-kbband').length === 0 && q('.ks-kbband-clip').length === 0
    && q('.ks-kbband-nav').length === 0 && q('.ks-kbband .ks-kb-card').length === 0
    && q('.ks-batch').length === 0,
    `kbband=${String(q('.ks-kbband').length)} / clip=${String(q('.ks-kbband-clip').length)} / `
      + `nav=${String(q('.ks-kbband-nav').length)} / batch=${String(q('.ks-batch').length)}`)
  check('C2 "只改内存不落库"的那几样仍然一处不留（标签视图/筛选胶囊/占位视图）；三层勾选列**每行一个**（第 5 步）',
    q('.ks-subtabs').length === 0 && q('.ks-tagrow').length === 0 && q('.ks-parse').length === 0
    && q('.ks-chip').length === 0
    /* ⚠⚠ **2026-09-21（第 5 步）就地改判据（原文见下，别删）**：这一条原来判的是
       「目录层与文件层**不许**有勾选框」—— 那是第 4 步的边界（批量只做在「待分类」层）。
       第 5 步业主明说"文件操作要能批量做" ⇒ 目录层/文件层**各有一条勾选列**，
       那两句不再成立；判据改成**新的真行为**（不是删掉、也不是放宽）：
         · 目录层勾选框数 == 目录行数（每行一个，多一个少一个都红）；
         · 文件层：**这一跑在最外层 ⇒ 文件行 0 行**，所以这一半**恒真**（0 == 0）。
           ⚠ 复核 R6 点名了这一点，处置 = **在注释里写明恒真是设计** + 真判在**有文件行**的那一跑：
           `P18`（「大批量」那一级 50 行 / 50 个勾选框）与 `E2/E5`（文件层列头就是带勾选列的 6 列）。
           这里保留这一半是为了让"文件层冒出一个不该有的勾选框"在最外层也能被看见（1 != 0 会红）。
         · 「待分类」层的勾选在 N8 单独判（那一层这一跑不在屏上）。
       原文：`q('.ks-dirs input[type=checkbox]').length === 0
       && q('.ks-list:not(.ks-list-dirs):not(.ks-list-inbox) input[type=checkbox]').length === 0` */
    && q('.ks-list-dirs .ks-col-dpick input[type=checkbox]').length === dirRows().length
    && q('.ks-list:not(.ks-list-dirs):not(.ks-list-inbox) .ks-col-fpick input[type=checkbox]').length
      === fileRows().length,
    `subtabs=${String(q('.ks-subtabs').length)} tagrow=${String(q('.ks-tagrow').length)} `
      + `parse=${String(q('.ks-parse').length)} chip=${String(q('.ks-chip').length)} `
      + `目录层勾选=${String(q('.ks-list-dirs .ks-col-dpick input[type=checkbox]').length)}/${String(dirRows().length)} 行 `
      + `文件层勾选=${String(q('.ks-list:not(.ks-list-dirs):not(.ks-list-inbox) .ks-col-fpick input[type=checkbox]').length)}/${String(fileRows().length)} 行`)
  check('C3 页面文本里没有"占位"字样的假动作（新建文件夹占位 / 移动到某目录）',
    !(container.textContent ?? '').includes('新建文件夹')
    && !(container.textContent ?? '').includes('移动到')
    && !(container.textContent ?? '').includes('＋标签'),
    `页面含「新建文件夹」=${String((container.textContent ?? '').includes('新建文件夹'))} / `
      + `含「移动到」=${String((container.textContent ?? '').includes('移动到'))}`)

  /* ══════════ D. 点目录 = 只拉那一层（按需展开，不是一次拉全库） ══════════ */
  const callsBeforeEnter = calls.length
  await click(dirNamed('标准'))
  const enterCalls = calls.slice(callsBeforeEnter)
  check('D1 点目录 ⇒ 请求里**带上了 parent_id=fld_std**（按需展开；不是把全库 1127 个目录一次拉进来）',
    enterCalls.some((c) => c.url.includes('/api/v1/kb/folders?') && c.url.includes('parent_id=fld_std'))
    && enterCalls.every((c) => !c.url.includes('/api/v1/kb/folders?parent_id=&')),
    `这一跳的请求：${enterCalls.map((c) => c.url.replace(API, '')).join(' , ')}`)
  check('D2 右侧换成**这一级**：1 行下级目录（P16 工程防火）+ 0 行文件',
    dirRows().length === 1 && dirNameOf(dirRows()[0]).includes('P16 工程防火') && fileRows().length === 0,
    `目录行 ${String(dirRows().length)}（${dirRows().map(dirNameOf).join(',')}）/ 文件行 ${String(fileRows().length)}`)
  check('D3 面包屑变成**两段**（知识库 / 标准），前一段是真 button、末段不可点；返回按钮可用了',
    crumbText() === '知识库/标准'
    && crumbItems()[0].clickable === true && crumbItems()[1].clickable === false
    && backBtn()?.disabled === false,
    `面包屑「${crumbText()}」/ 可点=${JSON.stringify(crumbItems().map((c) => c.clickable))}`)
  check('D4 左列高亮跟着走（「标准」那一行 data-on=true，最外层不再是当前级）',
    q('.ks-tree-row[data-on="true"] .ks-tree-label')[0]?.textContent?.trim() === '标准'
    && treeRows().filter((r) => r.dataset.on === 'true').length === 1,
    `高亮：${q('.ks-tree-row[data-on="true"] .ks-tree-label').map((e) => e.textContent).join(',')}`)

  /* ══════════ E. 文件层：这一级直接放的文件（表头 + 行 + 真字段） ══════════ */
  await click(dirNamed('P16 工程防火'))
  check('E1 文件层：4 行文件 + **一个**文件表头（这一级没有下级目录 ⇒ 不渲染空的目录列表头）',
    fileRows().length === 4 && q('.ks-list .ks-lhead').length === 1 && q('.ks-list-dirs').length === 0,
    `文件行 ${String(fileRows().length)} / 表头 ${String(q('.ks-list .ks-lhead').length)} / `
      + `.ks-list-dirs ${String(q('.ks-list-dirs').length)}`)
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据**：文件层加了勾选列 ⇒ 5 列变 6 列
     （`COLUMNS` 里一条新声明）。判据本身没放宽，只是那个数跟着声明变。 */
  check('E2 文件层：表头与每一行的 cell 类名序列**逐字相同**（同一份 COLUMNS，列数 6）',
    cellClasses(q('.ks-list .ks-lhead')[0]).join('|') === cellClasses(fileRows()[0]).join('|')
    && cellClasses(fileRows()[0]).length === 6,
    `表头 ${cellClasses(q('.ks-list .ks-lhead')[0]).join('|')}`)
  check('E3 文件行显示**后端字段**：名字 + 标准号 + 效力徽章 + 生效日期 + 处理状态',
    fileRows()[0] !== undefined
    && (fileRows()[0].querySelector('.ks-item-name')?.textContent ?? '').includes('建筑设计防火规范')
    && (fileRows()[0].querySelector('.ks-item-meta')?.textContent ?? '').trim() === 'GB 50016-2014'
    && (fileRows()[0].querySelector('.ks-col-status')?.textContent ?? '').trim() === '现行'
    && (fileRows()[0].querySelector('.ks-col-date')?.textContent ?? '').trim() === '2018-01-01'
    && (fileRows()[0].querySelector('.ks-col-stage')?.textContent ?? '').trim() === '已归位',
    `第 1 行：${(fileRows()[0]?.textContent ?? '').trim()}`)
  check('E4 那一篇「识别失败」的行如实显示失败类型（不美化、不吞掉）',
    fileRows().some((r) => (r.querySelector('.ks-col-stage')?.textContent ?? '').includes('识别失败')),
    fileRows().map((r) => (r.querySelector('.ks-col-stage')?.textContent ?? '').trim()).join(' | '))
  /* ⚠⚠ **2026-09-21 复核 `verify-freeze-kb-ui3` 打回 §④-C**：下面四条也是"主体仍在、断言却没了"
     （列头文案 / 行内文件图标 / 逐行 ⋮ 触发器 / 表头与同一个父元素）。旧版第 64/67/58/65 条判的
     就是这些。判据一律判**当前页面真的渲染出来的东西**。 */
  const fileHeadTexts = () => q('.ks-list .ks-lhead .ks-cell').map((el) => (el.textContent ?? '').trim())
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据**：勾选列无列头（在最前）⇒ 期望串多一个前导 `|`。 */
  check('E5 文件层列头文案就是「文件名 / 效力 / 生效日期 / 处理状态」（勾选列与行尾操作列无列头）',
    fileHeadTexts().join('|') === '|文件名|效力|生效日期|处理状态|',
    `列头=${JSON.stringify(fileHeadTexts())}`)
  /* ⚠⚠ **2026-09-22（业主界面要求）：这条判据就地翻过来（原文留在下面，别删）**
     原文：`check('E6 每一行都有**行内文件图标**（.ks-fileico 里真 svg + 非空 title），4 行 4 个', …)`
     —— 它当时判的是"**每一行**都有那个图标"。业主看完真机图说：
     「文件夹前面一个小文件夹图标做得好，但是**文件前面那个莫名其妙的图标可以删除**」
     ⇒ 本条现在判**文件行不许有** `.ks-fileico`（把图标加回去 ⇒ 当场红，变异①）。
     目录行那一半（**文件夹图标仍在**）判在**目录层**那一跑（B10，这一级没有下级目录 ⇒ 这里没有对象）。 */
  check('E6 文件行**不再有**行内图标（业主 2026-09-22：文件前面那个图标删掉）',
    fileRows().length === 4 && fileRows().every((r) => r.querySelector('.ks-fileico') === null),
    `文件行里的 .ks-fileico：${fileRows().map((r) => (r.querySelector('.ks-fileico') === null ? '(无)' : '有')).join('/')}`)
  check('E7 每一行都有**行尾 ⋮ 触发器**（一行一个 = 4 个，不是只有某一行有）',
    fileRows().length === 4 && q('.ks-item-more button').length === 4,
    `⋮ 按钮 ${String(q('.ks-item-more button').length)} 个 / 文件行 ${String(fileRows().length)} 行`)
  check('E8 文件层：列头行与数据行是**同一个容器的直接子元素**',
    q('.ks-list .ks-lhead').length === 1 && fileRows().length === 4
    && q('.ks-list .ks-lhead')[0].parentElement === fileRows()[0].parentElement,
    `表头父级=${String(q('.ks-list .ks-lhead')[0]?.parentElement?.className)} / `
      + `行父级=${String(fileRows()[0]?.parentElement?.className)}`)

  /* ══════════ F. 搜索（每层常驻；目录按名字、文件按标准号/名称） ══════════ */
  check('F1 搜索框"在 / 不在"与声明 `KB_PAGE_SEARCH` 一致（删掉它就红，不是没人管）',
    (searchInput() !== undefined) === (KB_PAGE_SEARCH === true),
    `声明 KB_PAGE_SEARCH=${String(KB_PAGE_SEARCH)} / DOM 里在=${String(searchInput() !== undefined)}`)
  /* ⚠ **2026-09-21 复核 `verify-freeze-kb-ui3` 打回 §④-C**：旧版第 48 条判的是"placeholder 指向
     **文件口径**（标准号或名称）"—— 这条没了。补回来：placeholder 必须同时点到"目录名"与
     "标准号/名称"两个口径（这一页同一层里两种都能筛，见 B7/F2/F3 的判据）。 */
  check('F1b 搜索框 placeholder 写清了两个口径（目录名 + 标准号/名称），不是空着或只写一个',
    (() => {
      const ph = searchInput()?.getAttribute('placeholder') ?? ''
      return ph.includes('目录') && (ph.includes('标准号') || ph.includes('名称'))
    })(),
    `placeholder=${JSON.stringify(searchInput()?.getAttribute('placeholder') ?? null)}`)
  await setInput(searchInput(), '喷水')
  check('F2 文件层搜索真的过滤：4 行 →（「喷水」）1 行',
    fileRows().length === 1 && fileNameOf(fileRows()[0]).includes('自动喷水灭火系统设计规范'),
    `实际 ${String(fileRows().length)} 行：${fileRows().map(fileNameOf).join(' / ')}`)
  await setInput(searchInput(), 'GB 55037')
  check('F3 按标准号也能命中（同一口径）：4 行 →（「GB 55037」）1 行',
    fileRows().length === 1 && fileNameOf(fileRows()[0]).includes('建筑防火通用规范'),
    `实际 ${String(fileRows().length)} 行`)
  await setInput(searchInput(), '不存在的串')
  check('F4 筛空时给的是**搜索空态**（不是"这一层本来就没东西"），且给了「清除搜索」',
    fileRows().length === 0
    && (container.textContent ?? '').includes('这一层没有符合搜索的条目')
    && !(container.textContent ?? '').includes('这一层还没有东西'),
    `空态文案：${(q('.ks-empty-t')[0]?.textContent ?? '(没有空态卡)').trim()}`)
  const clearBtn = q('.ks-empty-card button').find((b) => (b.textContent ?? '').includes('清除搜索'))
  await click(clearBtn)
  check('F5 点「清除搜索」⇒ 框清空、行恢复 4 行（搜索没有留下副作用）',
    (searchInput()?.value ?? '') === '' && fileRows().length === 4,
    `框里「${searchInput()?.value ?? ''}」/ ${String(fileRows().length)} 行`)
  /* F6/F7：**换层保留搜索词**（沿用 5i 的既有口径：搜索是**页面级**的过滤条件），
     并且它在**目录层**过滤的是**目录名**。 */
  await setInput(searchInput(), '环境')
  await click(backBtn())
  check('F6 换层后搜索词**留在框里**、并继续生效（目录层按目录名筛：`环境` 在「标准」这一级 0 命中）',
    (searchInput()?.value ?? '') === '环境' && dirRows().length === 0 && fileRows().length === 0
    && (container.textContent ?? '').includes('这一层没有符合搜索的条目'),
    `框里「${searchInput()?.value ?? ''}」/ 目录行 ${String(dirRows().length)} / 文件行 ${String(fileRows().length)}`)
  await clearSearch()
  check('F7 清空后目录层恢复（「标准」这一级 1 行目录 P16）',
    dirRows().length === 1 && dirNameOf(dirRows()[0]).includes('P16 工程防火'),
    `实际 ${String(dirRows().length)} 行：${dirRows().map(dirNameOf).join(',')}`)

  /* ══════════ G. 返回上一层 + 面包屑逐级跳转 ══════════ */
  await click(backBtn())
  check('G1 点「返回上一层」⇒ 真的回到**最外层**（4 行目录、0 行文件），面包屑只剩「知识库」、返回 disabled',
    crumbText() === '知识库' && dirRows().length === 4 && fileRows().length === 0
    && backBtn()?.disabled === true,
    `面包屑「${crumbText()}」/ 目录行 ${String(dirRows().length)} / 返回 disabled=${String(backBtn()?.disabled)}`)
  /* ⚠ **2026-09-21 复核 `verify-freeze-kb-ui3` 打回 §④-C**：旧版第 50–53 条在**库根 / 一级目录层 /
     二级目录层**各判过一轮搜索；新版只在文件层与一级目录层判（F2–F7）⇒ 补一轮**最外层**。
     判据同 F2（真的过滤，不是只改框里的字）。 */
  await setInput(searchInput(), '法律')
  check('G1b 搜索在**最外层**也真的生效（4 行目录 →「法律」1 行 法律法规）',
    dirRows().length === 1 && dirNameOf(dirRows()[0]).includes('法律法规'),
    `实际 ${String(dirRows().length)} 行：${dirRows().map(dirNameOf).join(',')}`)
  await clearSearch()
  check('G1c 清空后最外层恢复 4 行目录（搜索没有留下副作用）',
    dirRows().length === 4 && (searchInput()?.value ?? '') === '',
    `实际 ${String(dirRows().length)} 行 / 框里「${searchInput()?.value ?? ''}」`)
  await click(dirNamed('法律法规'))
  await click(dirNamed('宪法与行政法'))
  check('G2 走到二级目录（法律法规 / 宪法与行政法）：面包屑 3 段，只有末段不可点',
    crumbText() === '知识库/法律法规/宪法与行政法'
    && crumbItems().map((c) => c.clickable).join(',') === 'true,true,false',
    `面包屑「${crumbText()}」/ 可点=${JSON.stringify(crumbItems().map((c) => c.clickable))}`)
  check('G3 二级目录里的文件也按后端字段显示（法规没有标准号 ⇒ 破折号，不是空白）',
    fileRows().length === 2
    && fileRows().every((r) => (r.querySelector('.ks-item-meta')?.textContent ?? '').trim() === '—')
    && fileRows().some((r) => (r.querySelector('.ks-col-stage')?.textContent ?? '').includes('待确认')),
    fileRows().map((r) => (r.querySelector('.ks-col-stage')?.textContent ?? '').trim()).join(' | '))
  await click(q('.ks-crumb-go')[0])
  check('G4 点面包屑第 0 段（知识库）⇒ 真的回到最外层（4 行目录、面包屑 1 段）',
    crumbText() === '知识库' && dirRows().length === 4,
    `面包屑「${crumbText()}」/ 目录行 ${String(dirRows().length)}`)

  /* ══════════ H. 后端分页（限制在这一批的"文件多了要能翻页"） ══════════ */
  await click(dirRows().find((r) => dirNameOf(r).includes('大批量')))
  check('H1 120 篇的那一级：第一页 50 行 + 出现分页条（第 1 / 3 页 · 共 120 篇）',
    fileRows().length === 50 && q('.ks-pager').length === 1
    && (q('.ks-pager-n')[0]?.textContent ?? '').includes('第 1 / 3 页')
    && (q('.ks-pager-n')[0]?.textContent ?? '').includes('共 120 篇'),
    `行 ${String(fileRows().length)} / 分页条「${(q('.ks-pager-n')[0]?.textContent ?? '(没有)').trim()}」`)
  const nextBtn = () => q('.ks-pager-btn')[1]
  const prevBtn = () => q('.ks-pager-btn')[0]
  check('H2 第一页：上一页 disabled、下一页可用', prevBtn()?.disabled === true && nextBtn()?.disabled === false,
    `上一页 disabled=${String(prevBtn()?.disabled)} / 下一页 disabled=${String(nextBtn()?.disabled)}`)
  const callsBeforePage = calls.length
  await click(nextBtn())
  const pageCalls = calls.slice(callsBeforePage)
  check('H3 点「下一页」⇒ 真的带 offset=50 重新请求这一级（不是前端切片）',
    pageCalls.some((c) => c.url.includes('/items?') && c.url.includes('offset=50'))
    && (q('.ks-pager-n')[0]?.textContent ?? '').includes('第 2 / 3 页'),
    `这一跳的请求：${pageCalls.map((c) => c.url.replace(API, '')).join(' , ')}`
      + ` / 分页条「${(q('.ks-pager-n')[0]?.textContent ?? '').trim()}」`)
  await click(nextBtn())
  check('H4 末页（第 3 页）：剩 20 行、下一页 disabled（`has_more=false` 驱动的）',
    fileRows().length === 20 && nextBtn()?.disabled === true
    && (q('.ks-pager-n')[0]?.textContent ?? '').includes('第 3 / 3 页'),
    `行 ${String(fileRows().length)} / 下一页 disabled=${String(nextBtn()?.disabled)}`)

  /* ══════════ I. 整行可点 → 详情（业主 2026-09-21 定；字段全部来自后端） ══════════ */
  await click(q('.ks-crumb-go')[0])
  await click(dirNamed('标准'))
  await click(dirNamed('P16 工程防火'))
  const row3 = fileRows().find((r) => fileNameOf(r).includes('自动喷水灭火系统设计规范'))
  await click(row3.querySelector('.ks-col-date'))
  const detail = q('.ks-detail')[0]
  check('I1 整行可点（点**非交互处**：生效日期格）⇒ 打开**那一篇**的详情（不是别人的）',
    detail !== undefined
    && (detail.textContent ?? '').includes('自动喷水灭火系统设计规范')
    && (detail.textContent ?? '').includes('GB 50084-2017'),
    detail === undefined ? '没开详情' : (detail.textContent ?? '').slice(0, 60))
  const detailFields = q('.ks-detail .ks-field-k').map((el) => (el.textContent ?? '').trim())
  check('I2 详情含 发布日期 / 生效日期 / 废止日期 三个字段（业主点名要的三个日期）',
    ['发布日期', '生效日期', '废止日期'].every((t) => detailFields.includes(t)),
    `详情字段：${detailFields.join(' / ')}`)
  const detailValues = q('.ks-detail .ks-field-v').map((el) => (el.textContent ?? '').trim())
  check('I3 详情里的日期/标准号是**后端真值**（不是占位破折号）',
    detailValues.includes('2017-05-27') && detailValues.includes('2018-01-01')
    && detailValues.includes('GB 50084-2017'),
    `详情值：${detailValues.join(' | ')}`)
  check('I4 详情里的"处理状态"来自后端 `stage`（这一篇是已归位 ⇒ 显示「已归位」）',
    (detail.textContent ?? '').includes('已归位'),
    `详情里含「已归位」=${String((detail.textContent ?? '').includes('已归位'))}`)
  const moreBtn = row3.querySelector('.ks-item-more button')
  await click(moreBtn)
  const menuItems = q('[role=menuitem]').map((el) => (el.textContent ?? '').trim())
  /* ⚠⚠ **2026-09-21（第 5 步）就地改判据（原文见下，别删）**：这一条原来判「菜单**只有**「详情」」
     —— 那是第 3/4 步的边界（文件层的操作还没接）。第 5 步把**真的**文件操作接上了
     （挪到…/复制到…/从这一层拿掉，全部对应真接口），所以菜单项集合跟着变。
     判据改成**新的真行为**（不是删掉、也不是放宽）：这一篇在**某个目录里**（P16 工程防火）
     ⇒ 菜单必须恰好是这四样、第一项仍是「详情」；而"只改内存"的假动作（＋标签）仍然一处不留。
     原文：`menuItems.length === 1 && menuItems[0] === '详情'` */
  /* ⚠⚠ **2026-09-21（第 6 步）就地改判据（原文见下，别删）**：第 6 步给**每一篇文件**加了
     「在此范围内提问」（`params.kb_doc_ids` = 只在这一篇里问）⇒ 菜单多一样。
     判据改成新的真行为（不是删掉、不是放宽）：这一篇在某个目录里 ⇒ 恰好这五样。
     原文：`menuItems.join('|') === '详情|挪到某个目录…|复制到某个目录…|从这一层拿掉'` */
  /* ⚠⚠ **2026-09-22（业主改文案）就地改判据（原文见下，别删）**：业主原话
     「复制到某个目录，直接就写**复制到**；挪到某个目录直接写**移动到**；在此范围内提问——
     如果是在**单个文件**上点开三个点，那就应该展示**在此文件中提问**；**从这一层拿掉**是啥意思，
     删除就说删除」。
     ⇒ 这一层（文件在某个目录里）菜单文案变成 **在此文件中提问 / 移动到 / 复制到 / 移出**。
     ⚠ 「移出」@这一层**不是删除**（只去掉这一处的归属，文件还在「待分类」里），所以文案叫「移出」
     而不是「删除」；"文件不会删"这句话挂在**触发行尾「⋮」按钮的 title** 上（DSH 的 `MenuItem` 没有
     `title` 字段 ⇒ 菜单项本身挂不了提示，见 ui 复核记录）。判据仍判**恰好这五样**（不是放宽）。
     原文：`menuItems.join('|') === '详情|在此范围内提问|挪到某个目录…|复制到某个目录…|从这一层拿掉'` */
  check('I5 行尾「⋮」菜单 = 详情 + 在此文件中提问 + 移动到/复制到/移出'
    + '（在目录里那一套；＋标签那种假动作仍然没有）',
    menuItems.join('|') === '详情|在此文件中提问|移动到|复制到|移出',
    `菜单项：${JSON.stringify(menuItems)}`)
  /* ⚠ **2026-09-22（业主改文案）新增**：菜单项里的「移出」字面上像"删掉" ⇒ **真相必须留在看得见的地方**。
     DSH 的 `MenuItem` **没有 `title` 字段**（只有 id/label/disabled/icon/danger/submenu，见 ui-primitives 的
     `Menu.tsx`）⇒ 菜单项本身挂不了提示；能挂的是**触发行尾「⋮」的那个按钮**。判据挂在那里。 */
  check('I5b 这一行的「⋮」按钮 title 里如实写着「移出」只移出、**文件不会删除**'
    + '（`MenuItem` 没有 title 字段 ⇒ 菜单项上挂不了提示，只能挂触发器）',
    (moreBtn.getAttribute('title') ?? '').includes('移出')
    && (moreBtn.getAttribute('title') ?? '').includes('文件不会删除'),
    `title：${moreBtn.getAttribute('title') ?? '(没有 title)'}`)
  await click(moreBtn)
  /* ⚠ **2026-09-21 复核 `verify-freeze-kb-ui3` 打回 §④-C**：旧版第 61 条判"点开再点一次都收起"——
     新版 I5 只判菜单项集合，**没判收起**。补回来：开合是**状态**，不是"点一次就永久张开"。 */
  check('I6 再点一次「⋮」⇒ 菜单**收起**（开合是状态，不是一次性张开）',
    q('[role=menuitem]').length === 0,
    `再点一次后菜单项 ${String(q('[role=menuitem]').length)} 个`)

  /* ══════════ J. 空目录如实说空 ══════════ */
  await click(q('.ks-crumb-go')[0])
  await click(dirNamed('空目录'))
  check('J1 空目录：显示"这一层还没有东西"（**不显示假文档**），且没有空的目录列表头',
    (container.textContent ?? '').includes('这一层还没有东西')
    && q('.ks-empty-card').length === 1 && dirRows().length === 0 && fileRows().length === 0
    && q('.ks-list-dirs').length === 0,
    `空态「${(q('.ks-empty-t')[0]?.textContent ?? '(没有)').trim()}」/ 目录行 ${String(dirRows().length)}`)

  /* ══════════ K. 每级上传（真导入接口 + 落位接口；**有牙**） ══════════ */
  await click(q('.ks-crumb-go')[0])
  const uploadOpenBtn = q('.ks-upload-open')[0]
  await click(uploadOpenBtn)
  check('K1 最外层点「上传到这一层」⇒ 面板出现，来源目录**默认填了 host 的待入库目录**',
    q('.ks-upload').length === 1
    && (q('.ks-upload-dir input')[0]?.value ?? '').includes('待入库'),
    `面板 ${String(q('.ks-upload').length)} 个 / 来源目录「${q('.ks-upload-dir input')[0]?.value ?? ''}」`)
  check('K2 最外层时**如实说**"文件会留在最外层（还没归位）"，不是含糊的"已放进某个目录"',
    (q('.ks-upload-note')[0]?.textContent ?? '').includes('留在最外层'),
    (q('.ks-upload-note')[0]?.textContent ?? '').trim().slice(0, 80))
  /* ⚠⚠ **2026-09-21 第 5 步复核 R3**：`KsIngestPanel` 的"复活"必须有**真判据**。
     复核的变异 V6（把 `{upPreview ? (` 改成 `{false ? (`，并重建 `client.js`）当时**全绿** ——
     四张清单只钉了"bundle 里有『逐篇看』这个字符串"。这里判**结构**（面板真的挂进 DOM + 自己的特征文案
     + `aria-expanded`），真 Chrome 侧由 `ui-render-shot` 的 `kb|kb-upload` 声明 `.ks-ing` 并量它的高度
     （`h > 0`）—— 两半合起来才是"点下去真的看得见"。 */
  await click(q('.ks-upload-preview-open')[0])
  await flush()
  const prevWrap = q('.ks-upload-preview')
  const prevIng = q('.ks-upload-preview .ks-ing')
  const prevText = prevIng[0]?.textContent ?? ''
  check('K8 点「逐篇看」⇒ **复活的入库预览面板真的挂进 DOM**（.ks-upload-preview + 里面的 .ks-ing + 面板自己的文案）',
    prevWrap.length === 1 && prevIng.length === 1 && prevText.includes('只读预览')
    && (q('.ks-upload-preview-open')[0]?.getAttribute('aria-expanded') ?? '') === 'true',
    `.ks-upload-preview ${String(prevWrap.length)} 个 / .ks-ing ${String(prevIng.length)} 个 / `
      + `文案含「只读预览」=${String(prevText.includes('只读预览'))}`)
  await click(q('.ks-upload-preview-open')[0])       // 收起来（别让它留在后面的判据里）
  await flush()
  check('K9 再点一次「逐篇看」⇒ 面板**收起**（开合是状态，不是一次性挂上）',
    q('.ks-upload-preview').length === 0
    && (q('.ks-upload-preview-open')[0]?.getAttribute('aria-expanded') ?? '') === 'false',
    `收起后 .ks-upload-preview ${String(q('.ks-upload-preview').length)} 个`)
  const beforeTopUpload = calls.length
  await click(q('.ks-upload-go')[0])
  await waitMs(2500); await flush(); await flush()
  const topUploadCalls = calls.slice(beforeTopUpload)
  check('K3 点「导入到这一层」⇒ 真的调**引擎的真导入**接口（POST /api/v1/ingest/bulk + resume），'
    + '而不是 host 那套只读的 /ks/ingest/preview',
    topUploadCalls.some((c) => c.method === 'POST' && c.url === `${API}/api/v1/ingest/bulk`)
    && topUploadCalls.some((c) => c.method === 'POST' && c.url.includes('/ingest/bulk/bulk_1/resume'))
    && !topUploadCalls.some((c) => c.url.includes('/ks/ingest/preview')),
    `这一跳：${topUploadCalls.map((c) => `${c.method} ${c.url.replace(API, '')}`).join(' , ')}`)
  /* ⚠⚠ **2026-09-21 第 5 步复核 R2（判据没接线，已修）**：这条原来只数"bulk 与 resume 之间
     poll 过 ≥1 次" ⇒ 复核的变异 V7（探一次就走 = **旧语义**）**128/128 且 K3b PASS**，
     等于本批最核心的那个修复**没有判据看着**。现在判**响应**：resume 之前必须**真的看到过**
     `pause_reason === 'scan_complete'` 那一次应答（桩把响应体挂在请求记录上）。 */
  check('K3b **两段式握手**：resume 之前必须**真的读到过 `scan_complete`**（不是"扫了一眼就往下走"）'
    + '—— 真接口的 resume docstring 就是这条；旧写法紧跟 start 就 resume，**有时**会把已排好的清单丢掉（竞态）',
    (() => {
      const iBulk = topUploadCalls.findIndex((c) => c.method === 'POST' && c.url === `${API}/api/v1/ingest/bulk`)
      const iResume = topUploadCalls.findIndex((c) => c.url.includes('/resume'))
      const polls = topUploadCalls.slice(iBulk + 1, iResume)
        .filter((c) => c.url.includes('/api/v1/ingest/bulk/') && c.resp !== undefined)
      return iBulk >= 0 && iResume > iBulk && polls.length >= 1
        && polls.some((c) => c.resp.pause_reason === 'scan_complete')
    })(),
    `resume 之前的应答：${JSON.stringify(topUploadCalls.slice(0, topUploadCalls.findIndex((c) => c.url.includes('/resume')))
      .filter((c) => c.resp !== undefined).map((c) => c.resp.pause_reason ?? c.resp.status))}
     ／这一跳：${topUploadCalls.map((c) => `${c.method} ${c.url.replace(API, '')}`).join(' , ')}`)
  check('K4 最外层导入**不调**落位接口（没有可挂的目录 —— 顶层在库里不是一行记录），并如实报"留在最外层"',
    !topUploadCalls.some((c) => c.url.includes('/kb/inbox/confirm'))
    && !topUploadCalls.some((c) => c.url.includes('/kb/members'))
    && (q('.ks-upload-msg')[0]?.textContent ?? '').includes('最外层'),
    `消息：${(q('.ks-upload-msg')[0]?.textContent ?? '(没有)').trim().slice(0, 90)}`)
  // 进一个真目录再上传：这次必须**落位**（挂进这一级 + 标成已归位 = 不进自动识别）
  // ⚠ 此刻停在**最外层**（导入完成后页面重读的就是这一级）⇒ 直接点「标准」这一行即可。
  // ⚠ **面板还开着**（`upOpen` 是页面级状态，换层不会关它）⇒ 不要再点一次「上传到这一层」
  //   （那会把它 toggle 关掉；本批第一次就是这么写错的，冒烟当场抓到）。
  await click(dirNamed('标准'))
  check('K5 目录里上传：面板说明写着"直接放进「标准」，不会进自动识别"，且换层后面板仍在',
    q('.ks-upload').length === 1
    && (q('.ks-upload-note')[0]?.textContent ?? '').includes('标准')
    && (q('.ks-upload-note')[0]?.textContent ?? '').includes('不会进自动识别'),
    (q('.ks-upload-note')[0]?.textContent ?? '(面板不在)').trim().slice(0, 80))
  const beforeDirUpload = calls.length
  await click(q('.ks-upload-go')[0])
  await waitMs(2500); await flush(); await flush()
  const dirUploadCalls = calls.slice(beforeDirUpload)
  const confirmCall = dirUploadCalls.find((c) => c.url === `${API}/api/v1/kb/inbox/confirm`)
  const confirmBody = confirmCall === undefined ? null : JSON.parse(confirmCall.body ?? '{}')
  check('K6 目录里导入 ⇒ 真的调 `POST /kb/inbox/confirm`，`target_folder_id` = **当前目录**、'
    + '每篇新文件一条 `action=existing`（挂进这一级 **且** 标成已归位 = 不进自动识别）',
    confirmBody !== null
    && confirmBody.decisions?.length === 2
    && confirmBody.decisions.every((d) => d.action === 'existing' && d.target_folder_id === 'fld_std'),
    confirmCall === undefined ? '(没调落位接口)' : (confirmCall.body ?? '').slice(0, 160))
  check('K7 导入完成后这一级**真的重读**（不是只改了内存）',
    calls.slice(beforeDirUpload).filter((c) => c.url.includes('/api/v1/kb/folders')).length >= 2,
    `重读次数：${String(calls.slice(beforeDirUpload).filter((c) => c.url.includes('/api/v1/kb/folders')).length)}`)

  /* ══════════ N. 「待分类」这一层（KB-FOLDER-PLAN 第 4 步）══════════
     这一节判的**全是真行为**：入口真的能进、状态如实上屏、处置动作真的打到接口。
     ⚠ 真浏览器里"看不看得见"的判据**不在这里**（jsdom 的 textContent 不算证据 ——
       第 3 步复核自己踩出来的洞）⇒ 那一条在 `ui-render-shot.mjs` 的 `inboxStageCheck`。 */
  const inboxRows = () => q('.ks-inbox-row')
  const inboxNames = () => inboxRows().map((r) => (r.querySelector('.ks-item-name')?.textContent ?? '').trim())
  const inboxStages = () => inboxRows().map((r) => (r.querySelector('.ks-col-istage')?.textContent ?? '').replace(/\s+/g, ' ').trim())
  const inboxDests = () => inboxRows().map((r) => (r.querySelector('.ks-col-idest')?.textContent ?? '').trim())
  /** 回到最外层（左列第一行），再点「待分类」那一行。 */
  const gotoInboxLayer = async () => {
    if (q('.ks-crumb-here')[0]?.textContent?.trim() !== '知识库') await click(q('.ks-crumb-go')[0])
    await click(q('.ks-tree-name-inbox')[0])
    await flush()
  }
  await gotoInboxLayer()
  check('N1 左列「待分类」那一行点得进去：右栏换成待分类列表（.ks-list-inbox）+ 面包屑「知识库/待分类」、末段不可点',
    q('.ks-list-inbox').length === 1 && inboxRows().length === 4
    && crumbText() === '知识库/待分类'
    && crumbItems()[0].clickable === true && crumbItems()[1].clickable === false,
    `列表 ${String(q('.ks-list-inbox').length)} 个 / 行 ${String(inboxRows().length)} / 面包屑「${crumbText()}」`)
  const inboxHeadTexts = () => q('.ks-list-inbox .ks-lhead .ks-cell').map((el) => (el.textContent ?? '').trim())
  check('N2 待分类层：列头文案就是「文件名 / 状态 / 建议去向」（勾选列与 ⋮ 列无列头），'
    + '且表头与每一行的 cell 类名序列**逐字相同**（5 列）',
    inboxHeadTexts().join('|') === '|文件名|状态|建议去向|'
    && cellClasses(q('.ks-list-inbox .ks-lhead')[0]).join('|')
      === cellClasses(inboxRows()[0]).join('|')
    && cellClasses(inboxRows()[0]).length === 5,
    `列头=${JSON.stringify(inboxHeadTexts())} / 行 cell=${cellClasses(inboxRows()[0]).join('|')}`)
  check('N3 每篇的状态**如实**上屏（四档各一行）：排队中 / 识别中 / 待确认 / 识别失败（带失败原因）',
    inboxStages().join(' || ').includes('排队中') && inboxStages().join(' || ').includes('识别中')
    && inboxStages().join(' || ').includes('待确认') && inboxStages().join(' || ').includes('识别失败')
    && inboxStages().join(' || ').includes('解析失败（正文条款为零）'),
    inboxStages().join(' || '))
  check('N4 识别率（后端 confidence）与"不在目录里"（catalog_hidden=1）都如实显示',
    inboxStages().some((t) => t.includes('识别率 93%'))
    && inboxStages().some((t) => t.includes('不在目录里')),
    inboxStages().join(' || '))
  check('N5 建议去向如实：有建议的显示**后端给的路径**、认不出的显示「没有建议」',
    inboxDests().some((t) => t.includes('标准 › P 土木、建筑 › P16 工程防火'))
    && inboxDests().filter((t) => t.includes('没有建议')).length === 2,
    inboxDests().join(' || '))
  /* 兜底桶那一篇（没有建议）的菜单里**不许**出现「按建议归位 / 在建议位置新建」——
     后端对它们回 422 no_suggestion，渲染出来就是死按钮。 */
  const badRow = inboxRows().find((r) => (r.querySelector('.ks-item-name')?.textContent ?? '').includes('识别失败的一篇'))
  await click(badRow.querySelector('.ks-item-more button'))
  const badMenu = q('[role=menuitem]').map((el) => (el.textContent ?? '').trim())
  await click(badRow.querySelector('.ks-item-more button'))
  /* ⚠ 第 6 步：待分类行的菜单也多了「在此范围内提问」（走 `kb_doc_ids`）⇒ 3 样变 4 样（就地改）。
     原文（复核 LOW-6 要求留痕）：`badMenu.length === 3 && …` —— 五样里没有这一条。 */
  /* ⚠⚠ **2026-09-22（业主改文案）就地改判据（原文见下，别删）**：待分类层（一篇文件）⇒
     「在此文件中提问」；而这一条是**真删文档**（不可逆 + 二次确认面板）⇒ 业主说"删除就说删除"，
     文案 =「删除」（原文：`{ id: 'delete', label: '删掉…' }`）。
     顺手从"长度 + some()"改成**整串相等**（更紧，不是放宽）：4 样一字不差。
     原文：`badMenu.length === 4 && …badMenu.some((t) => t.includes('在此范围内提问'))…includes('删掉')` */
  check('N6 兜底桶（没有建议）那一篇的 ⋮ 菜单里**没有**「按建议归位 / 在建议位置新建」（死按钮不许渲染）'
    + '，且恰好是「放进某个目录… / 在此文件中提问 / 重来一次（重新解析）/ 删除」四样（这是真删，文案就叫删除）',
    badMenu.join('|') === '放进某个目录…|在此文件中提问|重来一次（重新解析）|删除',
    `菜单项：${JSON.stringify(badMenu)}`)
  const okRow = inboxRows().find((r) => (r.querySelector('.ks-item-name')?.textContent ?? '').includes('待确认的一篇'))
  await click(okRow.querySelector('.ks-item-more button'))
  const okMenu = q('[role=menuitem]').map((el) => (el.textContent ?? '').trim())
  await click(okRow.querySelector('.ks-item-more button'))
  check('N7 有建议的那一篇菜单里**有**「按建议归位（带路径）」与「在建议位置新建 XXX」',
    okMenu.some((t) => t.includes('按建议归位') && t.includes('P16 工程防火'))
    && okMenu.some((t) => t.includes('在建议位置新建')),
    `菜单项：${JSON.stringify(okMenu)}`)
  /* 勾选 ⇒ 批量条出现；取消 ⇒ 消失。 */
  const pickBoxes = () => q('.ks-inbox-row .ks-col-pick input[type=checkbox]')
  check('N8 待分类行**每行一个勾选框**（4 行 4 个），没勾选时批量条是 0 条',
    pickBoxes().length === 4 && q('.ks-batch').length === 0,
    `勾选框 ${String(pickBoxes().length)} 个 / 批量条 ${String(q('.ks-batch').length)} 条`)
  await click(pickBoxes()[0])
  const batchBtns = () => [...q('.ks-batch button')].map((b) => (b.textContent ?? '').trim())
  check('N9 勾一篇 ⇒ 批量条真的出现（4 个动作 + 取消选择），四个动作都念得出来',
    q('.ks-batch').length === 1 && (q('.ks-batch-n')[0]?.textContent ?? '').includes('已选 1 篇')
    && ['接受建议', '放进同一目录', '重来一次', '删除'].every((t) => batchBtns().some((b) => b.includes(t))),
    `批量条：${JSON.stringify(batchBtns())}`)
  /* ⚠ 这一篇（排队中的那一篇）**有建议** ⇒ 「接受建议」可用；换选兜底桶那篇 ⇒ 必须**禁用**。 */
  const acceptBtn = () => [...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('接受建议'))
  const enabledWithSuggestion = acceptBtn()?.disabled === false
  await click(pickBoxes()[0])                    // 取消第一篇
  await click(pickBoxes()[3])                    // 选兜底桶那篇
  const disabledWithout = acceptBtn()?.disabled === true
  check('N10 「接受建议」只在**选中的确有建议**时可用：选兜底桶那篇 ⇒ 按钮禁用（按下去会 422）',
    enabledWithSuggestion && disabledWithout && acceptBtn() !== undefined
    && (acceptBtn().getAttribute('title') ?? '').includes('没给出建议'),
    `有建议时 disabled=${String(!enabledWithSuggestion)} / 无建议时 disabled=${String(disabledWithout)}`
      + ` / title=${(acceptBtn()?.getAttribute('title') ?? '(没有)').slice(0, 40)}`)
  /* 放进同一目录：真的开选择器，选一行 ⇒ 真的发 confirm(existing)。 */
  await click(pickBoxes()[3])
  await click(pickBoxes()[0])
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('放进同一目录')))
  await flush()
  check('N11 「放进同一目录」⇒ 真的打开目录选择器（整棵树扁平清单里按名字找 + 逐行可点）',
    q('.ks-act').length === 1 && q('.ks-act-item').length === 5
    && (q('.ks-act-search input')[0] !== undefined),
    `面板 ${String(q('.ks-act').length)} 个 / 目录行 ${String(q('.ks-act-item').length)}`)
  await click(q('.ks-act-item').find((el) => (el.textContent ?? '').includes('P16 工程防火')))
  const beforePlace = calls.length
  await click(q('.ks-act-go')[0])
  await flush(); await flush()
  const placeCall = calls.slice(beforePlace).find((c) => c.url === `${API}/api/v1/kb/inbox/confirm`)
  const placeBody = placeCall === undefined ? null : JSON.parse(placeCall.body ?? '{}')
  check('N12 选择器里选完点确认 ⇒ 真的发 `POST /kb/inbox/confirm`（action=existing、target=选中的那个目录）',
    placeBody !== null && placeBody.decisions?.length === 1
    && placeBody.decisions[0].action === 'existing'
    && placeBody.decisions[0].target_folder_id === 'fld_p16',
    placeCall === undefined ? '(没调 confirm)' : (placeCall.body ?? '').slice(0, 140))
  /* 重来一次：真的发 reingest，并把这一层重读一遍。 */
  const beforeRetry = calls.length
  await click(pickBoxes()[1])
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('重来一次')))
  await flush(); await flush()
  const retryCalls = calls.slice(beforeRetry)
  const retryCall = retryCalls.find((c) => c.url === `${API}/api/v1/kb/inbox/reingest`)
  check('N13 「重来一次」⇒ 真的发 `POST /kb/inbox/reingest`（带选中的 doc_id），并重读这一层',
    retryCall !== undefined
    && JSON.parse(retryCall.body ?? '{}').doc_ids?.includes('doc_in_rec')
    && retryCalls.filter((c) => c.url.includes('/api/v1/kb/inbox?')).length >= 1,
    `这一跳：${retryCalls.map((c) => `${c.method} ${c.url.replace(API, '')}`).join(' , ')}`)
  /* 删除的**二次确认**：点「删除」只是开确认面板，**不许**当场删；点「确认删除」才真删。 */
  const beforeDel = calls.length
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('删除')))
  await flush()
  const openedConfirm = q('.ks-act-del').length === 1
  const confirmText = (q('.ks-act-del')[0]?.textContent ?? '').replace(/\s+/g, '')
  const deletedBeforeConfirm = calls.slice(beforeDel).some((c) => c.url.includes('batch-delete'))
  await click([...q('.ks-act-del button')].find((b) => (b.textContent ?? '').includes('确认删除')))
  await flush(); await flush()
  const delCalls = calls.slice(beforeDel)
  const delCall = delCalls.find((c) => c.url === `${API}/api/v1/documents/batch-delete`)
  check('N14 删除**要二次确认**：点「删除」只开确认面板（此时一条删除请求都没发）；'
    + '点「确认删除」才真的发 `/documents/batch-delete`（confirm=true）',
    openedConfirm && deletedBeforeConfirm === false && delCall !== undefined
    && JSON.parse(delCall.body ?? '{}').confirm === true,
    `确认面板（点确认前）${String(openedConfirm)} / 确认前发过删除=${String(deletedBeforeConfirm)}`
      + ` / 删除请求：${delCall === undefined ? '(没有)' : (delCall.body ?? '').slice(0, 120)}`)
  check('N15 删除面板如实写明"不可撤销"与"收藏/批注不删"（不是一句含糊的"确定吗"）',
    confirmText.includes('不可撤销') && confirmText.includes('收藏') && confirmText.includes('批注'),
    `确认面板原话：${confirmText.slice(0, 90)}`)

  /* ══════ N16–N20. 「补全分类号」（2026-09-22 自愈机制）+「没有建议」把原因说清 ══════
     业主口径：「这 380 篇**不要手动去补**……要修的是**机制**，让插件**自己能靠自己的机制
     完成工作**」；「待分类里没有建议要**写明为什么**」。
     这一组判的全是**真行为**：按钮必须打到**真接口**（`/kb/ccs/backfill`），进度与失败清单
     必须来自**后端给的那些数**（桩里那两条：found 1 / not_found 1），失败清单必须逐篇带原因。 */
  const ccsBtn = () => [...q('.ks-list-cap button')].find((b) => (b.textContent ?? '').includes('补全分类号'))
  check('N16 「补全分类号」入口在「待分类」那一行（.ks-list-cap），按钮上写的是**后端现算的**还缺几篇',
    ccsBtn() !== undefined && (ccsBtn().textContent ?? '').includes('还缺 3 篇'),
    `入口 ${String(q('.ks-ccs-btn').length)} 个 / 文字=${(ccsBtn()?.textContent ?? '(没有)').trim()}`)
  const beforeCcs = calls.length
  await click(ccsBtn())
  await flush(); await flush()
  const ccsCall = calls.slice(beforeCcs).find((c) => c.url === `${API}/api/v1/kb/ccs/backfill`)
  check('N17 点它 ⇒ **真的发** `POST /kb/ccs/backfill`（后台跑，不是界面自己编进度）',
    ccsCall !== undefined && ccsCall.method === 'POST',
    ccsCall === undefined ? '(没调 backfill)' : `${ccsCall.method} ${ccsCall.url.replace(API, '')}`)
  /* 轮询到完成：界面每 3 秒问一次状态（桩是"第一次 running、第二次 done"）⇒ 等两轮。 */
  await waitMs(6500); await flush()
  const ccsBar = q('.ks-ccs-bar')[0]
  const ccsText = (ccsBar?.textContent ?? '').replace(/\s+/g, ' ')
  check('N18 补全的状态行如实分列：已跑 done/total + **补到 / 查无 / 查询失败 / 读不出来 / 不适用**各一个数',
    ccsBar !== undefined && ccsText.includes('已跑 2 / 2')
    && ccsText.includes('补到 1 篇') && ccsText.includes('查无 1 篇')
    && ccsText.includes('查询失败 0 篇') && ccsText.includes('读不出来 0 篇')
    && ccsText.includes('不适用 0 篇'),
    `状态行：${ccsText.slice(0, 160)}`)
  check('N19 失败清单逐篇带原因（"还剩哪些、为什么"看得见，不是一句"部分失败"）',
    q('.ks-ccs-fails').length === 1
    && (q('.ks-ccs-fails')[0].textContent ?? '').includes('没补到的 1 篇')
    && (q('.ks-ccs-fails')[0].textContent ?? '').includes('查无：答话的站点里都没有这个标准号'),
    `清单：${(q('.ks-ccs-fails')[0]?.textContent ?? '(没有)').replace(/\s+/g, ' ').slice(0, 140)}`)
  /* 「没有建议」三种原因各写各的（依据全来自后端那几个字段）：
     · doc_in_rec 查过了没查到 ⇒ 照念后端的 outcome_label；
     · doc_in_bad **还没查过** ⇒ 说"还没查过分类号"（**不许**把 null 编成"查无"）。 */
  const destOf = (id) => (inboxRows().find((r) => r.dataset.docId === id)
    ?.querySelector('.ks-col-idest')?.textContent ?? '').trim()
  check('N20 「没有建议」把原因说清（业主口径）：查过没查到 ⇒ 照念后端说法；'
    + '**还没查过** ⇒ 说"还没查过分类号"（不把 null 编成查无）',
    destOf('doc_in_rec').includes('没有分类号')
    && destOf('doc_in_rec').includes('查无')
    && destOf('doc_in_bad').includes('还没查过分类号'),
    `doc_in_rec=${destOf('doc_in_rec')} / doc_in_bad=${destOf('doc_in_bad')}`)

  /* ══════════ P. 第 5 步：目录/文件的「建 / 改名 / 挪 / 复制 / 删」+ 批量（2026-09-21）══════════
     这一节判的全是**真行为**：每个动作都必须打到**真接口**（桩把每次请求都记下来），
     并且做完之后**当前这一层被重读**（"看起来成功了但列表没变"是明文禁止的假动作）。
     ⚠ 真浏览器里"看得见吗"的判据不在这里（jsdom 不做布局）：列宽/勾选框可见性那几条在
       `ui-render-shot.mjs`（`dirColsCheck` / `dirHeadCheck` / `rowCtrlsCheck` + 截图）。 */
  await gotoInboxLayer()                       // 先离开「待分类」（上一条把删除确认面板留在那层）
  await click(q('.ks-crumb-go')[0])            // 回到最外层
  await flush()
  const mkdirBtn = () => q('.ks-mkdir-open')[0]
  const actGo = () => q('.ks-act-go')[0]
  const actInput = () => q('.ks-act-name input')[0] ?? q('input.ks-act-name')[0]
  const dirMoreBtn = (text) => dirNamed(text).querySelector('.ks-item-more button')
  check('P1 「新建下级目录」入口在（目录层工具栏上），点了就开出建目录面板（不是假的）',
    mkdirBtn() !== undefined && (mkdirBtn().textContent ?? '').includes('新建下级目录'),
    `入口 ${String(q('.ks-mkdir-open').length)} 个`)
  await click(mkdirBtn())
  check('P2 建目录面板：真开了（.ks-act）+ 有名字输入框，且写明"建在「知识库」下面"',
    q('.ks-act').length === 1 && actInput() !== undefined
    && (q('.ks-act')[0].textContent ?? '').includes('知识库'),
    `面板 ${String(q('.ks-act').length)} 个 / 输入框 ${String(q('.ks-act-name').length)} 个`)
  await setInput(actInput(), '2026 新目录')
  const beforeMkdir = calls.length
  await click(actGo())
  await flush(); await flush()
  check('P3 点「建这个目录」⇒ **真的发** `POST /kb/folders`（parent_id=null = 顶层、name=填的那个），并重读这一层',
    madeFolders.length === 1 && madeFolders[0].name === '2026 新目录'
    && madeFolders[0].parent_id === null
    && calls.slice(beforeMkdir).filter((c) => c.url.includes('/api/v1/kb/folders')).length >= 2
    && (q('.ks-ib-msg')[0]?.textContent ?? '').includes('已建目录'),
    `请求体 ${JSON.stringify(madeFolders)} / 消息：${(q('.ks-ib-msg')[0]?.textContent ?? '(没有)').trim().slice(0, 60)}`)
  /* 在**目录里**建 ⇒ parent_id 必须是**当前这一级**（不是顶层）。 */
  await click(dirNamed('标准'))
  await click(mkdirBtn())
  await setInput(actInput(), 'P16 下级')
  await click(actGo())
  await flush(); await flush()
  check('P4 在「标准」里建目录 ⇒ `parent_id` 就是**当前这一级**（fld_std），不是顶层',
    madeFolders.length === 2 && madeFolders[1].parent_id === 'fld_std',
    `第二次请求体 ${JSON.stringify(madeFolders[1] ?? null)}`)
  await click(q('.ks-crumb-go')[0])            // 回到最外层
  /* ── 改名（只改库里的名字）── */
  await click(dirMoreBtn('标准'))
  const renameItem = q('[role=menuitem]').find((el) => (el.textContent ?? '').includes('改名'))
  /* ⚠ 第 6 步给目录行加了「在此范围内提问」（在这一棵目录里问）⇒ 五样变六样（就地改，不是放宽）。
     原文（复核 LOW-6 要求留痕）：`q('[role=menuitem]').length === 5 && renameItem !== undefined`。 */
  const dirAskItem = q('[role=menuitem]').find((el) => (el.textContent ?? '').trim() === '在此范围内提问')
  /* ⚠⚠ **2026-09-22（业主改文案）就地改判据（原文见下，别删）**：目录行菜单的
     `挪到某个目录…` ⇒ **`移动到`**、`复制到某个目录…` ⇒ **`复制到`**（业主："直接就写移动/复制"）；
     「在此范围内提问」目录行**保持原样**（问的是那一棵目录）；`删掉这个目录…` 是真删目录 ⇒ 保持。
     ⇒ 六样一字不差（从"长度 6 + 两个 some()"改成整串相等，更紧不是放宽）。
     原文：`q('[role=menuitem]').length === 6 && renameItem !== undefined && dirAskItem !== undefined` */
  check('P5 目录行的 ⋮ 菜单恰好是「改名…/在这个目录下新建…/移动到/复制到/在此范围内提问/删掉这个目录…」六样'
    + '（目录操作接上了）',
    q('[role=menuitem]').map((el) => (el.textContent ?? '').trim()).join('|')
      === '改名…|在这个目录下新建…|移动到|复制到|在此范围内提问|删掉这个目录…'
    && renameItem !== undefined && dirAskItem !== undefined,
    `菜单项：${JSON.stringify(q('[role=menuitem]').map((el) => (el.textContent ?? '').trim()))}`)
  await click(renameItem)
  check('P6 改名面板**预填了当前名字**（改名前先看见它现在叫什么）',
    actInput() !== undefined && actInput().value === '标准',
    `输入框里「${actInput()?.value ?? ''}」`)
  await setInput(actInput(), '标准（改名）')
  await click(actGo())
  await flush(); await flush()
  check('P7 点「改名字」⇒ **真的发** `PUT /kb/folders/fld_std`（name = 新名）—— 只改库里的名字，不动磁盘文件',
    renamedFolders.length === 1 && renamedFolders[0].folder_id === 'fld_std'
    && renamedFolders[0].name === '标准（改名）',
    `请求：${JSON.stringify(renamedFolders)}`)
  /* ── 挪目录：选择器要**排除自己与自己的下级** ── */
  await click(dirMoreBtn('标准'))
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').trim() === '移动到'))
  await flush()
  const moveChoices = q('.ks-act-item').map((el) => (el.textContent ?? '').trim())
  check('P8 「移动到」的选择器**排除了自己与自己的下级**（只剩「法律法规」—— 点不到必然失败的去处）',
    q('.ks-act').length === 1 && q('.ks-act-item').length === 1
    && moveChoices[0].includes('法律法规'),
    `可选 ${String(q('.ks-act-item').length)} 个：${JSON.stringify(moveChoices)}`)
  await click(q('.ks-act-item')[0])
  await click(actGo())
  await flush(); await flush()
  check('P9 点确认 ⇒ **真的发** `POST /kb/folders/fld_std/move`（from_parent_id=null = 当前主位置，to=fld_law）',
    movedFolders.length === 1 && movedFolders[0].folder_id === 'fld_std'
    && movedFolders[0].to_parent_id === 'fld_law',
    `请求：${JSON.stringify(movedFolders)}`)
  /* ── 复制目录：共享成员（多一处位置） ── */
  await click(dirMoreBtn('法律法规'))
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').trim() === '复制到'))
  await flush()
  await click(q('.ks-act-item')[0])
  await click(actGo())
  await flush(); await flush()
  check('P10 目录「复制到…」⇒ **真的发** `POST /kb/folders/{id}/copy`（面板上写明"只是多了一处位置"）',
    copiedFolders.length === 1 && copiedFolders[0].folder_id === 'fld_law'
    && (q('.ks-ib-msg')[0]?.textContent ?? '').includes('只是多了一处位置'),
    `请求：${JSON.stringify(copiedFolders)} / 消息：${(q('.ks-ib-msg')[0]?.textContent ?? '').trim().slice(0, 70)}`)
  /* ── 删目录：三种情形各有各的问法 ── */
  await click(dirMoreBtn('空目录'))
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').includes('删掉这个目录')))
  await flush(); await flush()
  check('P11 删目录**先读影响**（真的调 `GET /kb/folders/fld_empty/delete-preview`），空目录只说一句"空目录"'
    + '且**不给**「移到上一层/连文件一起删」那两条（空目录没有那些选择）',
    callsOf('/delete-preview').length >= 1
    && (q('.ks-act-del')[0]?.textContent ?? '').includes('空目录')
    && q('.ks-act-del button').some((b) => (b.textContent ?? '').includes('删除这些空目录'))
    && !q('.ks-act-del button').some((b) => (b.textContent ?? '').includes('移到上一层'))
    && !q('.ks-act-del button').some((b) => (b.textContent ?? '').includes('连里面的文件一起删')),
    `delete-preview 调用 ${String(callsOf('/delete-preview').length)} 次 / `
      + `面板按钮 ${JSON.stringify(q('.ks-act-del button').map((b) => (b.textContent ?? '').trim()))}`)
  await click(q('.ks-act-del button').find((b) => (b.textContent ?? '').includes('删除这些空目录')))
  await flush(); await flush()
  check('P12 空目录：**直接删**（DELETE 不带 mode —— 后端对空目录忽略 mode），并重读这一层',
    deletedFolders.length === 1 && deletedFolders[0].folder_id === 'fld_empty'
    && deletedFolders[0].mode === null,
    `请求：${JSON.stringify(deletedFolders)}`)
  /* 一级目录（法律法规）：没有上一层 ⇒ 「移到上一层」必须**禁用**（不是点下去报错）。 */
  await click(dirMoreBtn('法律法规'))
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').includes('删掉这个目录')))
  await flush(); await flush()
  const reparentBtn = () => q('.ks-act-del button')
    .find((b) => (b.textContent ?? '').includes('移到上一层'))
  const purgeBtn = () => q('.ks-act-del button')
    .find((b) => (b.textContent ?? '').includes('连里面的文件一起删'))
  check('P13 一级目录（没有上一层）⇒「移到上一层」**禁用**且 title 说明原因；「连里面的文件一起删」仍可用',
    reparentBtn() !== undefined && reparentBtn().disabled === true
    && (reparentBtn().getAttribute('title') ?? '').includes('一级目录')
    && purgeBtn() !== undefined && purgeBtn().disabled === false,
    `移到上一层 disabled=${String(reparentBtn()?.disabled)} / title=${(reparentBtn()?.getAttribute('title') ?? '').slice(0, 50)}`)
  check('P14 影响数字**来自 delete-preview**（几个下级目录 / 几篇文件 / 几篇在别处也有 —— 不是前端猜的）',
    (q('.ks-act-del')[0]?.textContent ?? '').includes('整棵子树')
    && (q('.ks-act-del')[0]?.textContent ?? '').includes('只丢这里的归属'),
    (q('.ks-act-del')[0]?.textContent ?? '').replace(/\s+/g, ' ').slice(0, 120))
  await click(purgeBtn())
  await flush(); await flush()
  check('P15 点「连里面的文件一起删」⇒ **真的发** `DELETE /kb/folders/fld_law?mode=purge`',
    deletedFolders.length === 2 && deletedFolders[1].folder_id === 'fld_law'
    && deletedFolders[1].mode === 'purge',
    `请求：${JSON.stringify(deletedFolders)}`)
  /* 非空两级目录：两个选择都要在，选「移到上一层」⇒ mode=reparent。 */
  await click(dirMoreBtn('标准'))
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').includes('删掉这个目录')))
  await flush(); await flush()
  const reparentBtn2 = () => q('.ks-act-del button')
    .find((b) => (b.textContent ?? '').includes('移到上一层'))
  check('P16 非空两级目录：两个选择都在（「移到上一层」可用 + 「连里面的文件一起删」），且取消也在',
    reparentBtn2() !== undefined && reparentBtn2().disabled === false
    && q('.ks-act-del button').some((b) => (b.textContent ?? '').includes('取消')),
    `按钮：${JSON.stringify(q('.ks-act-del button').map((b) => (b.textContent ?? '').trim()))}`)
  await click(reparentBtn2())
  await flush(); await flush()
  check('P17 点「只删目录，里面的东西移到上一层」⇒ **真的发** `DELETE /kb/folders/fld_std?mode=reparent`',
    deletedFolders.length === 3 && deletedFolders[2].folder_id === 'fld_std'
    && deletedFolders[2].mode === 'reparent',
    `请求：${JSON.stringify(deletedFolders)}`)
  /* ── 文件层：勾选 + 批量（移动到 / 复制到 / 移出）──
     ⚠ **2026-09-22 业主改文案**：批量条从 `挪到…`/`从这一层拿掉` ⇒ **`移动到…`/`移出`**
     （业主："挪到某个目录直接写移动到"；"「从这一层拿掉」是啥意思" ⇒ 定词「移出」）。
     「移出」**不是删除**（只去掉这一处的归属，文件还在库里）—— 真相挂在它的 title 上。 */
  await click(dirNamed('大批量'))                 // 120 篇那一级，勾前两行
  const fileBoxes = () => q('.ks-col-fpick input[type=checkbox]')
  check('P18 文件层**每行一个勾选框**（50 行 50 个），没勾选时没有批量条',
    fileBoxes().length === fileRows().length && fileRows().length === 50
    && q('.ks-batch').length === 0,
    `勾选框 ${String(fileBoxes().length)} 个 / 文件行 ${String(fileRows().length)} 行 / 批量条 ${String(q('.ks-batch').length)} 条`)
  await click(fileBoxes()[0])
  await click(fileBoxes()[1])
  const batchTexts = () => [...q('.ks-batch button')].map((b) => (b.textContent ?? '').trim())
  check('P19 勾两篇 ⇒ 批量条出现：**已选 2 篇** + 移动到… / 复制到… / 移出 / 取消选择',
    (q('.ks-batch-n')[0]?.textContent ?? '').includes('已选 2 篇')
    && ['移动到…', '复制到…', '移出'].every((t) => batchTexts().some((b) => b.includes(t))),
    `批量条：${JSON.stringify(batchTexts())}`)
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('移动到…')))
  await flush()
  await click(q('.ks-act-item').find((el) => (el.textContent ?? '').includes('法律法规')))
  await click(actGo())
  await flush(); await flush()
  const moveOp = memberOps.find((o) => o.op === 'move')
  check('P20 批量「移动到…」⇒ **真的发** `POST /kb/members/move`（from=当前层 fld_big、to=选中目录、items=勾的那两条）',
    moveOp !== undefined && moveOp.body.from_folder_id === 'fld_big'
    && moveOp.body.to_folder_id === 'fld_law'
    && moveOp.body.items?.length === 2
    && moveOp.body.items.every((it) => it.kind === 'file'),
    `请求：${JSON.stringify(moveOp?.body ?? null)}`)
  check('P21 批量动作做完 ⇒ 勾选**清空**（批量条消失）—— 不许"看起来成功了但选中的还挂着"',
    q('.ks-batch').length === 0,
    `批量条 ${String(q('.ks-batch').length)} 条`)
  await click(fileBoxes()[0])
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('复制到…')))
  await flush()
  await click(q('.ks-act-item').find((el) => (el.textContent ?? '').includes('标准')))
  await click(actGo())
  await flush(); await flush()
  const copyOp = memberOps.find((o) => o.op === 'copy')
  check('P22 批量「复制到…」⇒ **真的发** `POST /kb/members/copy`（只要 to_folder_id —— 复制=多一处位置，不需要来源）',
    copyOp !== undefined && copyOp.body.to_folder_id === 'fld_std'
    && copyOp.body.from_folder_id === undefined && copyOp.body.items?.length === 1,
    `请求：${JSON.stringify(copyOp?.body ?? null)}`)
  await click(fileBoxes()[0])
  /* 「移出」这个词的字面意思会被读成"删掉" ⇒ 先把它按钮上的 title 抄下来（点完批量条就没了）。 */
  const rmBatchBtn = [...q('.ks-batch button')].find((b) => (b.textContent ?? '').trim() === '移出')
  const rmBatchTitle = rmBatchBtn?.getAttribute('title') ?? ''
  await click(rmBatchBtn)
  await flush(); await flush()
  const rmOp = memberOps.find((o) => o.op === 'remove')
  check('P23 「移出」⇒ **真的发** `POST /kb/members/remove`（folder_id = 当前层、items = 勾的那条）—— 只删归属行，不删文件'
    + '；且按钮 title 如实写着"文件不会删除"',
    rmOp !== undefined && rmOp.body.folder_id === 'fld_big' && rmOp.body.items?.length === 1
    && rmBatchTitle.includes('文件不会删除'),
    `请求：${JSON.stringify(rmOp?.body ?? null)} / 按钮 title：${rmBatchTitle}`)
  /* 动作**做完之后**再说一遍真相（业主："「从这一层拿掉」是啥意思" ⇒ 词压成「移出」之后，
     菜单项那两个字的歧义必须在消息里被消掉）：消息里必须出现「移出」+「文件没有删」，
     并且**不许**出现把它说成删除的说法。 */
  const rmMsg = (q('.ks-ib-msg')[0]?.textContent ?? '').trim()
  check('P23b 「移出」做完 ⇒ 消息里如实写「移出」+「文件没有删」（**不许**把这个动作说成删除）',
    rmMsg.includes('移出') && rmMsg.includes('文件没有删')
    && !rmMsg.includes('已删除') && !rmMsg.includes('删掉'),
    `消息：${rmMsg}`)
  /* ── 最外层那些"还没进任何目录"的文件：只有「放进某个目录…」，不给"挪"（没有来源目录）。
        （2026-09-22 动词族统一：原名「加进某个目录…」——下面 1815 的历史留痕保留旧字面。）── */
  ITEMS.root = [doc('doc_unfiled_1', 'GB 80001-2026', '还没进任何目录的一篇')]
  await click(q('.ks-crumb-go')[0])
  await flush()
  check('P24 最外层真的有"还没进任何目录"的文件行（桩里放了一篇）',
    fileRows().length === 1 && fileNameOf(fileRows()[0]).includes('还没进任何目录'),
    `文件行 ${String(fileRows().length)}：${fileRows().map(fileNameOf).join(' / ')}`)
  await click(fileRows()[0].querySelector('.ks-item-more button'))
  const topMenu = q('[role=menuitem]').map((el) => (el.textContent ?? '').trim())
  /* ⚠ 第 6 步：最外层那些"还没进任何目录"的文件也有「在此范围内提问」（走 `kb_doc_ids`）。
     原文（复核 LOW-6 要求留痕）：`topMenu.join('|') === '详情|加进某个目录…'`。
     ⚠ **2026-09-22（业主改文案）**：**单篇文件**上一律写「在此文件中提问」（"在单个文件上点开
     三个点，那就应该展示在此文件中提问"）⇒ 最外层这三样跟着变。 */
  check('P25 最外层文件的 ⋮ 菜单 = 详情 + 在此文件中提问 + 「放进某个目录…」'
    + '（**没有**"移动"，它没有来源目录 —— 不给死按钮）',
    topMenu.join('|') === '详情|在此文件中提问|放进某个目录…',
    `菜单项：${JSON.stringify(topMenu)}`)
  await click(q('[role=menuitem]').find((el) => (el.textContent ?? '').includes('放进某个目录')))
  await flush()
  await click(q('.ks-act-item').find((el) => (el.textContent ?? '').includes('标准')))
  const beforeAdd = calls.length
  await click(actGo())
  await flush(); await flush()
  const addCall = calls.slice(beforeAdd).find((c) => c.url === `${API}/api/v1/kb/members`)
  check('P26 点确认 ⇒ **真的发** `POST /kb/members`（folder_id=选中目录、items=这一篇 file）',
    addCall !== undefined
    && JSON.parse(addCall.body ?? '{}').folder_id === 'fld_std'
    && JSON.parse(addCall.body ?? '{}').items?.[0]?.kind === 'file',
    addCall === undefined ? '(没调 members)' : (addCall.body ?? '').slice(0, 140))
  /* ── 目录层批量：勾两个目录 ⇒ 批量条给的是"目录那一套"（移动/复制/删目录），**没有**"移出" ──
     ⚠ **2026-09-22 业主改文案**：`挪到…` ⇒ **`移动到…`**；文件专属的 `从这一层拿掉` ⇒ **`移出`**。 */
  const dirBoxes = () => q('.ks-list-dirs .ks-col-dpick input[type=checkbox]')
  await click(dirBoxes()[0])
  await click(dirBoxes()[1])
  const dirBatch = () => [...q('.ks-batch button')].map((b) => (b.textContent ?? '').trim())
  check('P27 目录层勾两个 ⇒ 批量条按**目录那一套**给动作（移动到… / 复制到… / 删掉目录…），'
    + '标签是「已选 2 个目录」，且**没有**「移出 / 删除文档」那种文件动作',
    (q('.ks-batch-n')[0]?.textContent ?? '').includes('已选 2 个目录')
    && ['移动到…', '复制到…', '删掉目录…'].every((t) => dirBatch().some((b) => b.includes(t)))
    && !dirBatch().some((b) => b.includes('移出') || b.includes('删除文档')),
    `批量条：${JSON.stringify(dirBatch())}`)
  const previewBefore = callsOf('/delete-preview').length
  await click([...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('删掉目录…')))
  await flush(); await flush()
  check('P28 批量删目录：**逐个**读影响（delete-preview 调用数 +2），面板里这两个目录都点名了',
    callsOf('/delete-preview').length === previewBefore + 2
    && (q('.ks-act-del')[0]?.textContent ?? '').includes('标准')
    && (q('.ks-act-del')[0]?.textContent ?? '').includes('法律法规'),
    `delete-preview 增 ${String(callsOf('/delete-preview').length - previewBefore)} 次 / `
      + `面板：${(q('.ks-act-del')[0]?.textContent ?? '').replace(/\s+/g, ' ').slice(0, 100)}`)
  await click(q('.ks-act-del button').find((b) => (b.textContent ?? '').includes('取消')))
  await flush()
  check('P29 点「取消」⇒ 面板关掉、**一条删除请求都没发**（取消是真取消，不是"先删了再说"）',
    q('.ks-act').length === 0 && deletedFolders.length === 3,
    `面板 ${String(q('.ks-act').length)} 个 / 已删目录 ${String(deletedFolders.length)} 个`)
  /* ── ③a：批次终态里"有文件的状态没写进库"必须能在界面上看出来 ── */
  const cancelPick = [...q('.ks-batch button')].find((b) => (b.textContent ?? '').includes('取消选择'))
  if (cancelPick !== undefined) { await click(cancelPick) }
  /* ⚠ 上传面板从 K 段起一直开着（`upOpen` 是页面级状态，换层不会关它）⇒ 先确认它真的在，
     再点导入（`.ks-upload-open` 是 **toggle**：多按一次就是把它关掉 —— 本批实测踩到过）。 */
  if (q('.ks-upload').length === 0) { await click(q('.ks-upload-open')[0]); await flush() }
  bulkStateMissing = 1
  await click(q('.ks-upload-go')[0])
  await waitMs(2500); await flush(); await flush()
  check('P30 批次终态报"有文件的状态没写进库"⇒ 导入面板**照实说出来**（带文件名样本），不粉饰',
    (q('.ks-upload-msg')[0]?.textContent ?? '').includes('处理状态没写进库')
    && (q('.ks-upload-msg')[0]?.textContent ?? '').includes('missing.pdf'),
    `消息：${(q('.ks-upload-msg')[0]?.textContent ?? '(没有)').trim().slice(0, 140)}`)
  bulkStateMissing = 0
  /* ── 第二处实测缺陷：`catalog_hidden=1` 的文档**不在** `/api/v1/documents` 里 ──
     旧代码拿"导入前后文档列表的差集"当"这一批进来了哪些"，于是正文条款为零的那一类
     （被 pipeline 挡在目录外、只在「待分类」里可见）会被算成"没有新增"⇒ 对业主说假话。
     桩这里把这一批放进 `hiddenDocs`（只在库里、不在 /documents）⇒ 界面必须照实说。 */
  bulkAddsHidden = true
  const beforeHidden = calls.length
  await click(q('.ks-upload-go')[0])
  await waitMs(2500); await flush(); await flush()
  const hiddenMsgs = q('.ks-upload-msg')[0]?.textContent ?? ''
  check('P31 这一批进来的文档**不在 /documents 里**（正文条款为零那类）时，界面**不许**说"没有新增文件"'
    + '—— 必须如实说"解析报成功 N 篇、但没出现在目录清单里，去「待分类」看得到"',
    hiddenMsgs.includes('没出现在目录清单里') && hiddenMsgs.includes('待分类')
    && !hiddenMsgs.includes('没有解析出任何文档')
    && !calls.slice(beforeHidden).some((c) => c.url.includes('/kb/inbox/confirm')),
    `消息：${hiddenMsgs.trim().slice(0, 140)}`)
  bulkAddsHidden = false
  if (q('.ks-upload').length > 0) { await click(q('.ks-upload-open')[0]); await flush() }

  root.unmount()
  await flush()

  /* ══════════════════ L. 读不到库时的诚实错误态（新容器重挂，不影响上面那棵树） ══════════════════ */
  failFolders = true
  const errContainer = document.createElement('div')
  document.body.appendChild(errContainer)
  const errRoot = mount(errContainer, { useTabInfo, dataSource: 'render-smoke' })
  await flush(); await flush(); await flush()
  check('L1 引擎读不了目录时给**错误条**（引擎原话 + 重试按钮），不静默留白',
    errContainer.querySelector('.ks-kb-err') !== null
    && (errContainer.textContent ?? '').includes('桩：引擎装作读不了目录')
    && [...errContainer.querySelectorAll('.ks-kb-err button')].some((b) => (b.textContent ?? '').includes('重试')),
    `错误条：${(errContainer.querySelector('.ks-kb-err')?.textContent ?? '(没有)').trim().slice(0, 80)}`)
  failFolders = false
  await click([...errContainer.querySelectorAll('.ks-kb-err button')].find((b) => (b.textContent ?? '').includes('重试')))
  check('L2 点「重试」⇒ 引擎恢复后真的读出内容（错误不是死状态）',
    errContainer.querySelector('.ks-kb-err') === null
    && [...errContainer.querySelectorAll('.ks-tree-label')].some((el) => (el.textContent ?? '').includes('标准')),
    `错误条还在=${String(errContainer.querySelector('.ks-kb-err') !== null)}`)
  errRoot.unmount()
  await flush()

  /* ══════════════════ R. 第 6 步：按**目录范围**提问（业主口径：每一级都能问、多选取并集） ══════════════════
   * 这一节判的是**四件真事**（不是"界面上有个按钮"）：
   *   ① 请求里**真的带上了范围**（`params.kb_folder_ids` / `kb_doc_ids`）—— 界面只改内存不发请求必红；
   *   ② 最外层/「待分类」没勾选时**不许**发起"不限定范围"的提问（按钮禁用 + 原话说清为什么）；
   *   ③ 范围里的篇数来自引擎（`/kb/scope/resolve`），空范围时如实说"范围内没有、一次检索都没做"；
   *   ④ 答案里的范围回显与**前端选的范围**两回事时必须当众标红（引擎说"没限定范围"那一条）。
   * ⚠ 用**新容器新挂一次**：这一节要在"最外层/某个目录/待分类"之间来回走，与上面那棵树的
   *   状态（改过名、删过目录的桩记录）互不干扰 —— 桩里的目录表本身没变（删除只是记了一笔）。 */
  const askContainer = document.createElement('div')
  document.body.appendChild(askContainer)
  const askRoot = mount(askContainer, { useTabInfo, dataSource: 'render-smoke' })
  await flush(); await flush(); await flush()
  const aq = (sel) => [...askContainer.querySelectorAll(sel)]
  const aDirRows = () => aq('.ks-dir-row')
  const aDirNamed = (text) => aDirRows().find((r) =>
    (r.querySelector('.ks-col-dname .ks-dir-name')?.textContent ?? '').includes(text))
  const aFileRows = () => aq('.ks-item.ks-file-row')
  const aAskBtn = () => aq('.ks-ask-open')[0]
  const aChip = () => aq('.ks-ask-chip')[0]
  const aAskInput = () => aq('.ks-ask-q input')[0]
  const aGo = () => aq('.ks-ask-go')[0]
  const aEvRows = () => aq('.ks-ask-evrow')
  const aText = () => (askContainer.textContent ?? '').replace(/\s+/g, ' ')
  const aAnswer = () => JSON.parse(lastCallOf('/api/v1/ks/answer')?.body ?? '{}')
  const aParams = () => aAnswer().params ?? {}
  const aSorted = (arr) => (Array.isArray(arr) ? [...arr].sort().join(',') : String(arr))
  /* ⚠ 范围规模与答案各是一次**异步**取数（`/kb/scope/resolve` → 状态 → 渲染）⇒ 这里必须
     真等一小会儿再断言；`flush` 只推进一个 0ms 宏任务，抓不到第二跳。 */
  const openAskAndSettle = async (el) => { await click(el); await waitMs(20); await flush() }
  const askOnce = async (text) => {
    await setInput(aAskInput(), text)
    await click(aGo())
    await waitMs(20); await flush(); await flush()
  }

  // R1：最外层（= 整个知识库）**不给**范围提问
  check('R1 最外层（本来就是整个知识库）⇒「在此范围内提问」按钮在但**禁用**，title 写清为什么'
    + '（绝不悄悄变成全库提问）',
    aAskBtn() !== undefined && aAskBtn().disabled === true
    && (aAskBtn().getAttribute('title') ?? '').includes('最外层就是整个知识库'),
    `按钮 ${String(aAskBtn() !== undefined)} / disabled=${String(aAskBtn()?.disabled)} / `
      + `title=${aAskBtn()?.getAttribute('title') ?? '(没有)'}`)

  // R2/R3/R4/R5：进到「标准」这一级 ⇒ 范围 = 它 + 全部下级（引擎给篇数）
  await click(aDirNamed('标准'))
  check('R2 进到「标准」这一级 ⇒ 按钮可用，且点**之前** title 就写清会在哪个范围里问'
    + '（当前这一级 = 它 + 全部下级）',
    aAskBtn().disabled === false
    && (aAskBtn().getAttribute('title') ?? '').includes('及其全部下级里提问'),
    `disabled=${String(aAskBtn()?.disabled)} / title=${aAskBtn()?.getAttribute('title') ?? '(没有)'}`)
  const beforeResolve = callsOf('/kb/scope/resolve').length
  await openAskAndSettle(aAskBtn())
  const resolveCall = lastCallOf('/kb/scope/resolve')
  check('R3 点它 ⇒ **真的**去问引擎"这个范围里有哪些文件"（`POST /kb/scope/resolve`，'
    + 'folder_ids=[当前这一级]）—— 篇数不是界面自己数的',
    callsOf('/kb/scope/resolve').length === beforeResolve + 1
    && aSorted(JSON.parse(resolveCall?.body ?? '{}').folder_ids) === 'fld_std',
    `请求体 ${resolveCall?.body ?? '(没发)'}`)
  check('R4 范围 chip 出现且信息是**引擎给的**：目录名 + 「2 个目录 · 4 篇」'
    + '（fld_std 子树 = 它自己 + P16 两级、4 篇文件），提问面板同时开着',
    aChip() !== undefined && (aChip().textContent ?? '').includes('标准')
    && (aChip().textContent ?? '').includes('2 个目录 · 4 篇')
    && aq('.ks-ask').length === 1,
    `chip=「${(aChip()?.textContent ?? '(没有)').trim()}」/ 面板 ${String(aq('.ks-ask').length)} 个`)
  check('R5 面板抬头写的是「在「标准」及其全部下级里提问」（发起前就知道范围）',
    (aq('.ks-ask-where')[0]?.textContent ?? '').includes('及其全部下级里提问'),
    `抬头：${(aq('.ks-ask-where')[0]?.textContent ?? '(没有)').trim()}`)

  /* ⚠⚠ **2026-09-22（业主界面要求）：提问入口**在哪一行**是判据的一部分。**
     业主原话："按钮改到搜索栏上面显示文件夹名称的 bar 上，这样就很清楚是在这个文件夹内进行搜索"
     ⇒ 它必须是**当前文件夹名那一行**（`.ks-list-cap`）的孩子，且**不许**再待在工具栏
       （`.ks-kb-row`）里。判据钉住"在哪一行"，所以"挪回旧的工具栏"这种改动**当场红**（变异②）。
     ⚠ 位置用 `closest()` 从**元素**上取，不靠"DOM 第几个"—— 顺序变了不该假红。 */
  const askBtnEl = aAskBtn()
  const inCap = askBtnEl !== undefined && askBtnEl.closest('.ks-list-cap') !== null
  const inToolbar = askBtnEl !== undefined && askBtnEl.closest('.ks-kb-row') !== null
  check('R5b 「在此范围内提问」在**当前文件夹名那一行**（.ks-list-cap，搜索框上面），'
    + '**不在**工具栏（.ks-kb-row）里 —— 业主 2026-09-22 亲定的位置',
    inCap && !inToolbar,
    `在 .ks-list-cap=${String(inCap)} / 在 .ks-kb-row=${String(inToolbar)}`)
  /* ⚠ 同一个位置要求也管 chip（业主："这一行挤不下就让它折行，别把 chip 挤没"）：
     收起提问面板之后 chip 必须**仍然看得见**（否则用户不知道自己在限定范围里）。 */
  await click(aq('.ks-ask-close')[0]); await flush(); await flush()
  check('R5c 收起提问面板之后，范围 chip **仍然在**（而且还在同一行里）—— '
    + '"发起前/发起后都看得见当前范围"这条在按钮搬家之后仍成立',
    aChip() !== undefined && aq('.ks-ask').length === 0
    && aChip().closest('.ks-list-cap') !== null,
    `chip ${String(aChip() !== undefined)} 个 / 面板 ${String(aq('.ks-ask').length)} 个 / `
      + `chip 在 .ks-list-cap=${String(aChip()?.closest('.ks-list-cap') !== null)}`)
  await openAskAndSettle(aAskBtn())   // 重新打开面板，后面的用例还要用

  // R6/R7：问一次 —— 范围必须随请求发出去；答案区回显引擎给的实际范围
  const beforeAnswer = callsOf('/api/v1/ks/answer').length
  await askOnce('动火作业怎么分级')
  const p6 = aParams()
  check('R6 点「问一问」⇒ 请求里**真的带上了范围**（params.kb_folder_ids=[当前这一级]），'
    + '并且**没有**混进 kb_doc_ids / 收藏夹的 folder_id（两种"夹"不许混）',
    callsOf('/api/v1/ks/answer').length === beforeAnswer + 1
    && aSorted(p6.kb_folder_ids) === 'fld_std' && p6.kb_doc_ids === undefined
    && p6.folder_id === undefined,
    `params=${JSON.stringify(p6)}`)
  check('R7 答案区如实写"这次实际范围"（引擎回显 2 个目录 / 4 篇）+ 结论与依据都出来了'
    + '（范围内答得出这一半）',
    aText().includes('这次实际范围') && aText().includes('4 篇')
    && aText().includes('桩结论：范围内答得出') && aEvRows().length === 1,
    `回显/结论/依据行：${String(aText().includes('这次实际范围'))} / `
      + `${String(aText().includes('桩结论：范围内答得出'))} / ${String(aEvRows().length)}`)

  // R8：**空范围**不许退化成全库（换成"空目录"那一级再问）
  await click(aq('.ks-ask-clear')[0]); await flush()
  await click(aq('.ks-crumb-go')[0]); await flush()
  await click(aDirNamed('空目录'))
  await openAskAndSettle(aAskBtn())
  check('R8 范围里一篇都没有（空目录）⇒ chip 如实写「0 篇」（不是"正在数…"、也不是编一个数）',
    (aChip()?.textContent ?? '').includes('0 篇'),
    `chip=「${(aChip()?.textContent ?? '(没有)').trim()}」`)
  await askOnce('这里面有什么')
  check('R9 空范围提问 ⇒ 界面说「范围内没有」+「一次检索都没做」，且**一条依据都不显示**'
    + '（绝不静默放宽成全库）',
    aText().includes('范围内没有') && aText().includes('一次检索都没做') && aEvRows().length === 0,
    `含"范围内没有"=${String(aText().includes('范围内没有'))} / `
      + `含"一次检索都没做"=${String(aText().includes('一次检索都没做'))} / `
      + `依据行 ${String(aEvRows().length)}`)

  // R10：引擎回显说"没限定范围" ⇒ 当众标红（前端不许替它圆场）
  askAnswerMode = 'noscope'
  await askOnce('再问一次')
  check('R10 这次带了范围、可引擎回显说**没有限定范围** ⇒ 界面当众标红'
    + '（这份答案可能来自整个知识库，不许当成范围内检索的结果）',
    aq('.ks-ask-msg-bad').length >= 1
    && (aq('.ks-ask-msg-bad')[0].textContent ?? '').includes('没有限定范围'),
    `标红条：${(aq('.ks-ask-msg-bad')[0]?.textContent ?? '(没有)').trim().slice(0, 90)}`)
  askAnswerMode = 'in'

  // R11：多选几个目录 = **取并集**（业主原话）
  await click(aq('.ks-ask-clear')[0]); await flush()
  await click(aq('.ks-crumb-go')[0]); await flush()
  const aDirBoxes = () => aq('.ks-list-dirs .ks-col-dpick input[type=checkbox]')
  await click(aDirBoxes()[0])
  await click(aDirBoxes()[1])
  check('R11 勾两个目录 ⇒ 按钮 title 就写着会在**这两个目录的并集**里问（点之前就知道）',
    (aAskBtn().getAttribute('title') ?? '').includes('2 个目录的并集'),
    `title=${aAskBtn()?.getAttribute('title') ?? '(没有)'}`)
  await openAskAndSettle(aAskBtn())
  const unionResolve = JSON.parse(lastCallOf('/kb/scope/resolve')?.body ?? '{}')
  check('R12 多选两个目录 ⇒ 去引擎问范围时**两个目录都在**（并集不是只取第一个），'
    + 'chip 写「4 个目录 · 6 篇」（= 两棵子树合起来的真实规模）',
    aSorted(unionResolve.folder_ids) === 'fld_law,fld_std'
    && (aChip()?.textContent ?? '').includes('2 个目录的并集')
    && (aChip()?.textContent ?? '').includes('4 个目录 · 6 篇'),
    `请求 folder_ids=${JSON.stringify(unionResolve.folder_ids ?? null)} / `
      + `chip=「${(aChip()?.textContent ?? '(没有)').trim()}」`)
  await askOnce('并集里有没有依据')
  check('R13 并集里提问：范围也随请求发出去（两个目录 id 都在 params.kb_folder_ids 里）',
    aSorted(aParams().kb_folder_ids) === 'fld_law,fld_std',
    `params=${JSON.stringify(aParams())}`)
  /* 清掉勾选：**不清**的话下一段（待分类）会拿这两个目录当范围，R15 就判不到"没勾选就禁用"。 */
  await click([...aq('.ks-batch button')].find((b) => (b.textContent ?? '').includes('取消选择')))
  await flush()

  // R14：**文件层**（一篇文件的范围，走 kb_doc_ids）
  await click(aDirNamed('标准')); await flush()
  await click(aDirNamed('P16 工程防火')); await flush()
  const fileRow0 = aFileRows()[0]
  const isFileRow = fileRow0 !== undefined
  await click(fileRow0?.querySelector('.ks-item-more button'))
  const aMenu = aq('[role=menuitem]').map((el) => (el.textContent ?? '').trim())
  /* ⚠ **2026-09-22（业主改文案）**：**单篇文件**上一律叫「在此文件中提问」
     （原话："在单个文件上点开三个点，那就应该展示在此文件中提问"）；行为一字未变。 */
  check('R14 文件行的 ⋮ 菜单里有「在此文件中提问」（一篇文件也是一个范围）',
    aMenu.includes('在此文件中提问'), `菜单项：${JSON.stringify(aMenu)}`)
  await click(aq('[role=menuitem]').find((el) => (el.textContent ?? '').trim() === '在此文件中提问'))
  await waitMs(20); await flush()
  check('R15 一篇文件的范围 ⇒ chip 写「1 篇文件」、抬头写「在这 1 篇文件里提问」'
    + '（与"某一级及其下级"是两种范围，界面上分得清）',
    (aChip()?.textContent ?? '').includes('1 篇文件')
    && (aq('.ks-ask-where')[0]?.textContent ?? '').includes('在这 1 篇文件里提问'),
    `chip=「${(aChip()?.textContent ?? '(没有)').trim()}」/ `
      + `抬头=${(aq('.ks-ask-where')[0]?.textContent ?? '(没有)').trim()}`)
  await askOnce('这一篇讲了什么')
  check('R16 一篇文件的范围随请求发出去 ⇒ `params.kb_doc_ids` 就是那一篇的 doc_id，'
    + '且**没有** kb_folder_ids（两种范围不混发）',
    isFileRow && aSorted(aParams().kb_doc_ids) === 'doc_fire_50016'
    && aParams().kb_folder_ids === undefined,
    `params=${JSON.stringify(aParams())}`)

  // R17/R18：**待分类层**（那一层的文件还没进任何目录 ⇒ 只能按勾选的文件给范围）
  await click(aq('.ks-tree-name-inbox')[0]); await flush(); await flush()
  check('R17 「待分类」层没勾选任何一篇 ⇒ 按钮**禁用**，title 说清"待分类不是目录、先勾几篇"'
    + '（不在这一层凭空造一个范围）',
    aAskBtn().disabled === true
    && (aAskBtn().getAttribute('title') ?? '').includes('待分类'),
    `disabled=${String(aAskBtn()?.disabled)} / title=${aAskBtn()?.getAttribute('title') ?? '(没有)'}`)
  const inboxBoxes = aq('.ks-inbox-row .ks-col-pick input[type=checkbox]')
  const isInboxRow = inboxBoxes.length > 0
  await click(inboxBoxes[0]); await flush()
  await openAskAndSettle(aAskBtn())
  await askOnce('这一篇是谁')
  check('R18 「待分类」里勾一篇 ⇒ 范围就是**那一篇**（`params.kb_doc_ids`），'
    + 'chip 上有篇数（引擎算的 1 篇）',
    isInboxRow && aSorted(aParams().kb_doc_ids) === 'doc_in_q'
    && (aChip()?.textContent ?? '').includes('0 个目录 · 1 篇'),
    `params=${JSON.stringify(aParams())} / chip=「${(aChip()?.textContent ?? '(没有)').trim()}」`)

  /* ══════════ R19（复核 MEDIUM-2）：**切范围时"旧答案覆盖新答案"** —— 运行时复现 ══════════
   * 复核是**读码结论、未复现**：`askSeqRef` 只护 chip 的篇数（`loadAskCounts`），
   * `runAsk` 里 `setAskRes/setAskPhase` **没有新鲜度检查**，而 `openAsk`/`clearAsk` 会把
   * `askPhase` 重置回 `idle` ⇒ "问 A（慢）→ 换范围再问 B → B 先回 → A 后回"时，
   * **A 的答案会盖在 B 的范围上**（chip 写的是 B）。
   *
   * 复现手法（不 mock 组件、只把**桩的响应卡住**）：
   *   ① 范围 = 标准（fld_std）⇒ 让下一次 `/ks/answer` **卡在闸门上**（桩记下它卡的是哪个范围）；
   *   ② 立刻**换成** 法律法规（fld_law）再问一次 ⇒ 这一次正常返回 ⇒ 屏幕上应当是 B 的答案；
   *   ③ 放闸 ⇒ A 的答案这时才回来 ⇒ **屏幕必须还是 B 的**（序号守卫把它整个丢弃）。
   * 桩给 A/B 的结论里各带自己的范围标记（`桩结论：范围内答得出（fld_std/fld_law）`）+
   * 回显的篇数也不同（fld_std 子树 4 篇 / fld_law 子树 2 篇）⇒ 一眼看得出谁盖了谁。 */
  const gate = {}
  const gatePromise = new Promise((resolve) => { gate.release = resolve })
  await click(aq('.ks-ask-clear')[0]); await flush()
  await click(aq('.ks-crumb-go')[0]); await flush()          // 回最外层
  await click(aDirNamed('标准')); await flush()               // 范围 A = 标准
  await openAskAndSettle(aAskBtn())
  answerHold = gatePromise                                   // 让 A 的响应卡住
  await setInput(aAskInput(), 'A 的问题')
  await click(aGo()); await flush(); await flush()
  const aHeld = answerHeldScope
  check('R19a 复现前提：A 那次请求**真的卡在闸门上**（桩记下了它卡的范围）',
    aHeld === 'fld_std' && aq('.ks-ask-go')[0]?.textContent?.includes('在问'),
    `卡住的范围=${String(aHeld)} / 按钮文字=「${(aq('.ks-ask-go')[0]?.textContent ?? '').trim()}」`)
  await click(aq('.ks-ask-clear')[0]); await flush()          // 换范围（B）
  await click(aq('.ks-crumb-go')[0]); await flush()           // ⚠ 先回最外层，才看得到「法律法规」
  await click(aDirNamed('法律法规')); await flush()
  await openAskAndSettle(aAskBtn())
  await setInput(aAskInput(), 'B 的问题')
  await click(aGo()); await flush(); await flush()
  const bEcho = aText().includes('2 个目录 · 2 篇') && aText().includes('（fld_law）')
  gate.release()                                              // 放闸：A 现在才回来
  await waitMs(30); await flush(); await flush()
  check('R19b 慢答案（A）回来时**不许覆盖**新答案（B）—— 屏幕仍应是 B 的范围与结论',
    bEcho && aText().includes('（fld_law）') && !aText().includes('（fld_std）')
    && aText().includes('2 个目录 · 2 篇') && !aText().includes('2 个目录 · 4 篇'),
    `B 先到的判断=${String(bEcho)} / 放闸后含 fld_std=${String(aText().includes('（fld_std）'))} / `
      + `含「2 个目录 · 4 篇」=${String(aText().includes('2 个目录 · 4 篇'))}`)
  askRoot.unmount()
  await flush()

  /* ══════════════════ M. 「不要两个页面」：原来的「文件导入」入口落到待分类层 ══════════════════ */
  const ingContainer = document.createElement('div')
  document.body.appendChild(ingContainer)
  const ingRoot = mount(ingContainer, {
    useTabInfo: () => ({ tab: { navigation: { params: { page: 'ingest' } } } }),
    dataSource: 'render-smoke',
  })
  await flush(); await flush(); await flush()
  const iq = (sel) => [...ingContainer.querySelectorAll(sel)]
  check('M1 `params.page=ingest`（开始页 ▾ 的「文件导入」）**直接落到「待分类」那一层**'
    + '—— 不再是一页"尚未实现"的占位（业主：不要两个页面）',
    ingContainer.querySelector('.ks-list-inbox') !== null
    && iq('.ks-inbox-row').length === 4
    && !(ingContainer.textContent ?? '').includes('这一页尚未实现'),
    `待分类列表 ${String(iq('.ks-list-inbox').length)} 个 / 行 ${String(iq('.ks-inbox-row').length)}`
      + ` / 含"尚未实现"=${String((ingContainer.textContent ?? '').includes('这一页尚未实现'))}`)
  /* 这一层上的导入面板：入口在、体检按钮在、覆盖开关在（默认**关**）。 */
  await click(iq('.ks-upload-open')[0])
  await flush()
  const reingestCb = iq('.ks-upload input[type=checkbox]')
  check('M2 待分类层上就是导入面板（来源目录 + 先体检 + 导入），"覆盖重导"开关默认**关**'
    + '（它会替换同号旧文档，不许替业主默认打开）',
    iq('.ks-upload').length === 1 && iq('.ks-upload-check').length === 1
    && iq('.ks-upload-go').length === 1
    && reingestCb.length === 1 && reingestCb[0].checked === false,
    `面板 ${String(iq('.ks-upload').length)} / 体检钮 ${String(iq('.ks-upload-check').length)}`
      + ` / 覆盖勾选 ${String(reingestCb.length)} 个（checked=${String(reingestCb[0]?.checked)}）`)
  ingRoot.unmount()
  await flush()

  /* ══════════════════ 办事台（S2-a1，2026-09-22）：等高菜单行 → 专门页面 ══════════════════
     ⚠ 形态更正留痕：本段原判"卡片 + 三组分组 + 一卡一窗旋钮"（2026-09-19 业主当时指定）；
     2026-09-22 业主裁定**废弃卡片式**（"有的空有的满、密密麻麻不知道干什么"）⇒ 定稿
     **等高菜单行（两行制）+ 点行进专门页面**。旧 7 条卡片断言**整段作废换新**（对账：
     删 7 增 8，形态变了判据跟着变，不放宽——新形态的牙口逐条见下）。 */
  const capContainer = document.createElement('div')
  document.body.appendChild(capContainer)
  const capRoot = mount(capContainer, { useTabInfo: () => ({ tab: { navigation: { params: { page: 'capabilities' } } } }), dataSource: 'render-smoke' })
  await flush(); await flush()

  const cq = (sel) => [...capContainer.querySelectorAll(sel)]
  const cClick = async (el) => {
    el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    await flush()
  }

  check('办事台：页头两句逐字（标题 +「点一项，开始一件活。」）',
    (capContainer.textContent ?? '').includes('办事台')
    && (capContainer.textContent ?? '').includes('点一项，开始一件活。'),
    (capContainer.textContent ?? '').slice(0, 40))

  const officeRows = cq('.ks-off-row')
  check('办事台：8 行等高菜单行（一个功能一行）', officeRows.length === 8, `实际 ${String(officeRows.length)} 行`)

  const officeTexts = officeRows.map((r) => (r.textContent ?? '').replace(/\s+/g, '').replace(/[›·]/g, ''))
  check('办事台：行文案逐字照 v3 定稿（名称+短语 8 对）',
    ['合同审查逐条比对法规，给三色结论',
      '义务清单→检查表抽出「应当/必须」，转检查表',
      '制度差距分析内部制度比法规缺什么',
      '批量问答一批条款，一次提问',
      '纠错修订标记识别错的条款，可回退',
      '外发审计每次外发记录，可查可导出',
      '取证问答去对话里提问',
      '条款释义还没有做完后这里可以点'].every((t, i) => officeTexts[i] === t),
    officeTexts.map((t) => t.slice(0, 14)).join(' | '))

  const officeExplain = officeRows[7]
  check('办事台：条款释义灰行（disabled + 「还没有」小牌），不给假入口',
    officeExplain.disabled === true && (officeExplain.textContent ?? '').includes('还没有'),
    `disabled=${String(officeExplain.disabled)}`)

  await cClick(officeRows[3])
  const officePageText = capContainer.textContent ?? ''
  check('办事台：点「批量问答」⇒ 进专门页面（标题 + ‹ 返回办事台 + 动作位；仍未翻真=灰态样板）',
    officePageText.includes('批量问答') && officePageText.includes('‹ 返回办事台')
    && officePageText.includes('开始：批量提问'),
    officePageText.slice(0, 60))
  const officeStartBtn = cq('button').find((b) => (b.textContent ?? '').includes('开始：'))
  check('办事台：S2-a1 动作钮**灰 +「还没接上」**（不给假入口；S2-a2 起逐个翻真）',
    officeStartBtn !== undefined && officeStartBtn.disabled === true && officePageText.includes('还没接上'),
    officeStartBtn === undefined ? '没找到动作钮' : `disabled=${String(officeStartBtn.disabled)}`)

  const officeBackBtn = cq('button').find((b) => (b.textContent ?? '').includes('返回办事台'))
  await cClick(officeBackBtn)
  check('办事台：点「‹ 返回办事台」⇒ 菜单回来（8 行）',
    cq('.ks-off-row').length === 8, `实际 ${String(cq('.ks-off-row').length)} 行`)

  /* ── S2-a2：外发审计翻真（第一个亮起的真入口）—— 列表真取数 + 导出 Markdown 真出文件 ── */
  const egressBefore = calls.length
  await cClick(cq('.ks-off-row')[5])
  await flush(); await flush()
  check('办事台·外发审计：点行进页 ⇒ 真发起 GET /api/v1/egress/audit（不是画上去的假页面）',
    calls.slice(egressBefore).some((c) => c.url.includes('/api/v1/egress/audit')),
    calls.slice(egressBefore).map((c) => c.url).join(' | ').slice(0, 80))
  const egressRows = cq('.ks-off-egress-row')
  check('办事台·外发审计：两条记录真渲染（时间/服务/字节/摘要在）',
    egressRows.length === 2
    && (capContainer.textContent ?? '').includes('2026-09-22 15:00')
    && (capContainer.textContent ?? '').includes('512'),
    `行 ${String(egressRows.length)}`)
  const exportBtn = cq('button').find((b) => (b.textContent ?? '').includes('导出 Markdown'))
  check('办事台·外发审计：「导出 Markdown」真按钮亮着（S2-a1 的灰态在此页已翻真）',
    exportBtn !== undefined && exportBtn.disabled === false,
    exportBtn === undefined ? '没找到导出钮' : `disabled=${String(exportBtn.disabled)}`)
  let capturedBlob = null
  const savedCreate = URL.createObjectURL
  const savedRevoke = URL.revokeObjectURL
  URL.createObjectURL = (b) => { capturedBlob = b; return 'blob:smoke' }
  URL.revokeObjectURL = () => {}
  await cClick(exportBtn)
  URL.createObjectURL = savedCreate
  URL.revokeObjectURL = savedRevoke
  const mdText = capturedBlob === null ? '' : await capturedBlob.text()
  check('办事台·外发审计：点导出 ⇒ 真生成 Markdown（共 2 条 + 逐条留痕编号；无字面星号）',
    mdText.includes('共 2 条外发') && mdText.includes('dump_1') && mdText.includes('# 外发审计记录')
    && !mdText.includes('**'),
    mdText.slice(0, 80))

  /* ── S2-b1：合同审查真流程（粘贴 → 抽审查点 → 逐条执行 SSE → 三色 + 看原文锚点）── */
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('返回办事台')))
  await cClick(cq('.ks-off-row')[0])
  const contractArea = capContainer.querySelector('#ks-contract-text')
  const contractStart = () => cq('button').find((b) => (b.textContent ?? '').includes('开始：上传合同比对'))
  check('办事台·合同审查：输入屏在（名称框 + 正文框 + 开始比对钮），空正文时钮**灰**',
    contractArea !== null && contractStart() !== undefined && contractStart().disabled === true,
    `正文框 ${contractArea === null ? 0 : 1} / 钮 ${contractStart() === undefined ? 0 : 1}`)
  const areaSetter = Object.getOwnPropertyDescriptor(dom.window.HTMLTextAreaElement.prototype, 'value').set
  areaSetter.call(contractArea, '高处作业应办理作业票。废弃物应分类存放。')
  contractArea.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
  await flush(); await flush()
  check('办事台·合同审查：有正文后开始钮亮（不是死按钮）', contractStart().disabled === false,
    `disabled=${String(contractStart().disabled)}`)
  await cClick(contractStart())
  await flush(); await flush()
  check('办事台·合同审查：真建任务（POST /api/v1/compliance/review）并渲染 2 个审查点',
    calls.some((c) => c.url.includes('/api/v1/compliance/review'))
    && (capContainer.textContent ?? '').includes('抽出 2 个审查点')
    && (capContainer.textContent ?? '').includes('高处作业应办理作业票'),
    (capContainer.textContent ?? '').slice(0, 60))
  const execBtn2 = cq('button').find((b) => (b.textContent ?? '').includes('逐条执行'))
  check('办事台·合同审查：执行钮带条数（2 条）', execBtn2 !== undefined && (execBtn2.textContent ?? '').includes('（2 条）'),
    execBtn2 === undefined ? '没找到执行钮' : (execBtn2.textContent ?? ''))
  await cClick(execBtn2)
  await flush(); await flush()
  check('办事台·合同审查：SSE 逐条三色真渲染（风险 + 需复核 两色词 + 汇总行逐字）',
    (capContainer.textContent ?? '').includes('风险')
    && (capContainer.textContent ?? '').includes('需复核')
    && (capContainer.textContent ?? '').includes('结论：1 风险 · 1 需复核 · 0 合规'),
    (capContainer.textContent ?? '').slice(-80))
  check('办事台·合同审查：「看原文」锚点真生成（evidenceUrlOf 契约：doc=doc_id + page + rev）',
    [...capContainer.querySelectorAll('a')].some((a) => {
      const href = a.getAttribute('href') ?? ''
      return href.includes('/__ks_evidence__') && href.includes('doc=doc_1') && href.includes('rev=rev_1') && href.includes('page=7')
    }),
    [...capContainer.querySelectorAll('a')].map((a) => a.getAttribute('href')).join(' | ').slice(0, 80))

  /* ── S2-b2：义务清单→检查表（真取数/真勾选/真转换/真导出）── */
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('返回办事台')))
  await cClick(cq('.ks-off-row')[1])
  const dutyArea = capContainer.querySelector('#ks-duty-desc')
  check('办事台·义务清单：输入屏在（业务描述框 + 生成钮空时灰）',
    dutyArea !== null
    && cq('button').find((b) => (b.textContent ?? '').includes('开始：生成义务清单')).disabled === true)
  areaSetter.call(dutyArea, '高处作业')
  dutyArea.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
  await flush(); await flush()
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('开始：生成义务清单')))
  await flush(); await flush()
  check('办事台·义务清单：真取数（POST /obligations）+ 2 条义务渲染（条款号+义务句）',
    calls.some((c) => c.url.includes('/api/v1/compliance/obligations'))
    && (capContainer.textContent ?? '').includes('抽出 2 条义务')
    && (capContainer.textContent ?? '').includes('高处作业应办理作业票'),
    (capContainer.textContent ?? '').slice(0, 60))
  const dutyBoxes = cq('input[type=checkbox]')
  await cClick(dutyBoxes[0])
  check('办事台·义务清单：勾选自查**真落库**（POST …/check）',
    calls.some((c) => c.url.includes('/api/v1/compliance/obligations/lst_1/check')),
    calls.slice(-3).map((c) => c.url.split('/').slice(-1)[0]).join(' | '))
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('转成检查表')))
  await flush(); await flush()
  check('办事台·义务清单：转检查表真出自查问句（是否已落实：…？）',
    (capContainer.textContent ?? '').includes('是否已落实：高处作业应办理作业票？'),
    (capContainer.textContent ?? '').slice(0, 60))
  let dutyBlob = null
  URL.createObjectURL = (b) => { dutyBlob = b; return 'blob:smoke2' }
  URL.revokeObjectURL = () => {}
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('导出 Markdown')))
  const dutyMd = dutyBlob === null ? '' : await dutyBlob.text()
  check('办事台·义务清单：导出 Markdown 真出文件（# 义务检查表 + 勾选态；无字面星号）',
    dutyMd.includes('# 义务检查表') && dutyMd.includes('- [x]') && !dutyMd.includes('**'),
    dutyMd.slice(0, 60))

  /* ── S2-b2：制度差距分析（登记 → 比对 → 缺什么/补什么）── */
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('返回办事台')))
  await cClick(cq('.ks-off-row')[2])
  const gapName = capContainer.querySelector('#ks-gap-name')
  const gapArea = capContainer.querySelector('#ks-gap-text')
  check('办事台·差距分析：输入屏在（制度名 + 正文框 + 开始钮空时灰）',
    gapName !== null && gapArea !== null
    && cq('button').find((b) => (b.textContent ?? '').includes('开始：上传制度比对')).disabled === true)
  setInput(gapName, '安全生产责任制')
  areaSetter.call(gapArea, '本制度规定安全生产责任。')
  gapArea.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
  await flush(); await flush()
  await cClick(cq('button').find((b) => (b.textContent ?? '').includes('开始：上传制度比对')))
  await flush(); await flush()
  check('办事台·差距分析：真登记 + 真比对（POST /policies + /gap-analysis 都发出）',
    calls.some((c) => c.url.includes('/api/v1/compliance/policies'))
    && calls.some((c) => c.url.includes('/api/v1/compliance/gap-analysis')),
    calls.slice(-4).map((c) => c.url.split('/').slice(-1)[0]).join(' | '))
  check('办事台·差距分析：结论行 + 建议逐条渲染（新增/完善两类建议都在）',
    (capContainer.textContent ?? '').includes('结论：1 风险 · 1 需复核 · 0 合规（制度：安全生产责任制）')
    && (capContainer.textContent ?? '').includes('建议在制度中新增对应条款')
    && (capContainer.textContent ?? '').includes('建议完善相关章节'),
    (capContainer.textContent ?? '').slice(-80))

  capRoot.unmount()
  await flush()

  /* ══════════ 主题 token 存在性：引用不存在的 token 会静默落到硬编码兜底色 ══════════ */
  const themeDir = join(harness, 'packages', 'client', 'ui-theme', 'src', 'styles')
  const { readdir: rd, readFile: rf } = await import('node:fs/promises')
  let themeCss = ''
  try {
    for (const f of await rd(themeDir)) {
      if (f.endsWith('.css')) themeCss += await rf(join(themeDir, f), 'utf8')
    }
  } catch (e) {
    console.error(`❌ 读不到主题 CSS（${themeDir}）：${String(e.message)}`)
    console.error('   渲染级用例依赖 DSH 检出；缺件时**报错**而不是静默跳过。')
    process.exit(1)
  }
  const defined = new Set([...themeCss.matchAll(/(--dsw-[a-z0-9-]+)\s*:/g)].map((m) => m[1]))
  const clientDir = join(pluginRoot, 'client')
  const referenced = new Map()
  for (const f of await rd(clientDir)) {
    if (!f.endsWith('.ts') && !f.endsWith('.tsx')) continue
    const text = await rf(join(clientDir, f), 'utf8')
    // ⚠ 必须要求 token 后面紧跟 `,` 或 `)`（= 真的是一个 var(--dsw-x) 调用），
    //   否则注释里的 `var(--dsw-alias-*)` 这种**通配写法**会被当成一个不存在的 token。
    for (const m of text.matchAll(/var\((--dsw-[a-z0-9-]+)\s*[,)]/g)) {
      if (!referenced.has(m[1])) referenced.set(m[1], new Set())
      referenced.get(m[1]).add(f)
    }
  }
  const ghostTokens = [...referenced.entries()].filter(([t]) => !defined.has(t))
  check(`我们引用的 ${referenced.size} 个 --dsw-* token **全部真实存在**（不存在 ⇒ 静默落到兜底色）`,
    ghostTokens.length === 0,
    ghostTokens.length === 0
      ? `主题里共定义 ${defined.size} 个 token`
      : ghostTokens.map(([t, fs]) => `${t}（${[...fs].join(',')}）`).join(' | '))
} finally {
  await rm(stubDir, { recursive: true, force: true })
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== kb-page-render smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
