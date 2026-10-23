# archify 逆向：它靠什么产出「结构 + 证据指向」

> 取证对象：`tt-a1i/archify`，本地只读副本 `_research/archify`，HEAD = `654da74e084e5a1faf708779c23d6172766be9c1`（2026-10-19，`Merge pull request #1006 …v320-publication-followup`），远端 `https://github.com/tt-a1i/archify.git`。仓库是浅克隆（`.git/shallow` 存在），`git rev-list --count HEAD` = 1259，所以更早的历史我看不到。
>
> 本文所有路径均**相对 `_research/archify/` 仓库根**。引用只给文件 + 可搜索原文片段，不给行号。
>
> 本文是取证，不是提案。任何"该怎么做"的判断留给主代理。

---

## 一句话结论

archify 的「证据聪明」不在画得好看，而在于它把**每一句论断、每一个图节点都编译成一条可机器复核的引用**：正文用 `[](source:id)` 挂上标编号，图节点用行尾 `source:<id>` 单元格挂来源，来源本身要么是 URL，要么是「仓库路径 + 行区间 + 40 位 commit」，而 commit 固定这件事由 `git show <rev>:<path>` 在渲染前真读一遍字节来证明——读不到就整份产物不许出。

## 五条要点

1. **产物是单文件自包含 HTML，但不小**：一个原生图产物 813–864 KB，一个 explainer 页 516–533 KB；页内 0 个 `<script src=>`、0 个外部字体请求、图标是 `data:` URI，唯一的外链是正文里被引用的那些来源网址本身。
2. **中间表示有两层，不是一个 schema**：explainer 是「结论 + 理由 + 适用范围 + 面板 + 块 + 来源表」的文档 IR（`explainer.schema.json`，13 种块类型），原生图是 10 套各自独立的图 IR（节点集合 + 关系集合 + `meta.repository`）。两者共用同一套 `source` 概念，但**挂载位置不同**：explainer 挂在正文行内上标上，原生图挂在节点上。
3. **证据的"可核查"是编译期强制，不是写作规范劝告**：`@code` 块不接受作者手写的代码文本，只接受 `source=<id>`，而该 source 必须有 `path` + `lines`；渲染前用 `git show <revision>:<path>` 取出字节，切出行区间，算 sha256，写进 `dependencies[]`，再由 `check` 阶段重算一遍比对。
4. **闸门是四段式，且回执本身也是被校验的对象**：`finalize` 按 `deliver → check → browser-check` 顺序跑（`validate` 内嵌在 `deliver` 里），每段回执必须带 `artifact.sha256` + `bytes` + `receiptId` 且与本次产物一致；任何一段的 `supportedFixes` 都是"改哪一处"而不是"重跑试试"。
5. **渲染器不可复用，产物可复用**：`archify/package.json` 没有 `exports`/`main`、`"private": true`、只暴露 `bin`；渲染入口是直接读 `process.argv` 的脚本。但生成的 HTML 自带完整运行时（CSS/JS 全内联），能脱离工具单独分发、单独打开。所以「抄机制」可以，「接进去当库用」不行。

---

## 一、产物形态：一份 HTML 里到底有什么

### 1.1 explainer 页（一页式回答）

页面骨架（照抄自 `docs/cases/explainer/tls-first-visit.html` 的 body）：

```
<section id="answer" class="panel answer-panel span4" data-row="0" data-span-min="4">
  <header class="panel-head"><span class="panel-id answer-id" aria-hidden="true">A</span><h2>Answer</h2></header>
  <div class="panel-body"><p class="verdict">…</p><ol class="reasons">…</ol></div>
  <p class="answer-scope"><span class="scope-label">Applies to</span><span class="scope-chip">…</span></p>
</section>
<section class="panel span8 diagram-panel" id="wire" data-row="0" data-span-min="8" data-title="…">
```

要点：

- **结论区是独立面板**，不是正文开头的一段。它带三个子部件：`.verdict`（一句话结论）、`.reasons`（`<ol>`，schema 上限 4 条）、`.answer-scope`（"Applies to" + 用 `·` 切开的条件 chip）。scope 的切分规则在 `archify/explainer/render.mjs`：`function scopeParts(scope) { return scope.split(/\s+·\s+/)…`，注释写着 `// A scope written as "a · b · c" reads as separate conditions; anything else stays a sentence.`
- **面板按 12 栅格排**，`archify/explainer/layout.mjs` 文件头注释：`/** Order-preserving twelve-column packing. Explicit spans never change.`。结论面板的起始宽度是 `{id:'answer',span:5,min:4,…}`，实际排完可能被压窄——`tls-first-visit.html` 里落到 `class="panel answer-panel span4"`。作者写死的 `{#id span=7}` 不会被改（`item.explicit`）。
- **面板标题是问句**（`## What crosses the wire before the first request?`），面板号是 `<a class="panel-id" href="#wire">1</a>`，可点回自己。
- **内嵌图是静态 SVG 预览 + 按需解压的原生 Viewer**。`<div class="diagram-preview preview-tls-visit" role="img" …>` 里放一段被改写过 id 的静态 SVG；"Open interactive view" 按钮点开 `<dialog id="diagram-dialog">`，里面 `iframe` 的 `srcdoc` 来自 gzip 压缩的完整原生图 HTML。`archify/explainer/page-bundle.mjs` 注释：`// The native Viewer HTML is needed only when a reader opens "Explore", so the page stores it gzip-compressed and the reader inflates it on demand.`
- **图下面自动挂一个"图的结构"清单**：`<details class="diagram-semantics" open><summary>Diagram structure</summary>` 列出每个节点与每条边（`<code>browser</code> → <code>dns</code> · DNS query: example.com`）。这是给读屏器和"不想看图"的人的等价文本。
- **页脚是来源表**：`<section class="sources"><h2>Sources</h2><ol><li id="source-rfc8446" value="1"><a href="https://www.rfc-editor.org/rfc/rfc8446" …>RFC 8446…</a></li></ol></section>`。
- **页脚还有一个"可核查事实"条**（colophon）：`<p class="colophon-facts"><span>4 panels</span><span>1 diagram validated</span><span>1 source</span></p>`。中文页是 `4 个面板` / `1 张图已通过结构校验` / `1 个来源`（见 `render.mjs` 的 `dictionaries.zh.facts`）。
- **交互**（`archify/explainer/reader.js`，51,676 字节）：
  - 主题 `auto/light/dark`、样式 `clean/editorial/product/swiss`；
  - 导出菜单：长图 PNG / WebP / JPG + `打印 / PDF`；
  - 逐步看（`walk`）：步骤列表逐条点亮图中对应节点，`←/→` 移动、`Esc` 结束；
  - 文本 ↔ 图节点互相高亮（`linkTerms()`：`// A name in the text that is also a node label is linked to that node, once per panel, both ways`）；
  - 来源卡（`setupSourceCards()`）：悬停/聚焦上标或图节点弹出卡片；
  - 追问（`setupAsk()`）：把「页面 + 文件 + 面板号与 ID + 引用原文 + 问题」拼成一段可粘贴给 agent 的文字，还附一句 `请用 Archify 的面板替换（patch explainer）只更新这个面板，保留它的 ID。`；
  - 清单勾选持久化到 `localStorage`（key = `archify-checklist:${root.dataset.artifact}:${…}`）；
  - 打印时自动展开所有 `diagram-semantics`。

注意：explainer 页**没有** focus / reach / route / lens / map / presentation 这些原生图交互。我在这份 reader 里搜 `present`、`lens` 均 0 命中；`focus`/`route` 的命中是菜单键盘焦点、`.focusing` 类、以及 `openViewer`/`validHash` 那段"打开原生 Viewer 后往里投递 hash"的桥接代码，不是页内交互。这些交互属于图，不属于页。

### 1.2 原生图页（10 种图）

`archify/assets/template.html` 是模板（786,886 字节），渲染时替换 SVG 槽位与卡片槽位（`archify/renderers/shared/utils.mjs` 的 `applyTemplate`，靠 `<!-- ARCHIFY:SVG_SLOT_START -->` 这类哨兵注释定位）。

模板里的交互（按 i18n 键与 data 属性核对）：

| 交互 | 证据 |
|---|---|
| 主题 / 视觉预设（classic / signal-flow / blueprint / editorial） | `data-preset`、`viewer.preset.*` |
| Focus（聚焦节点，开 Semantic Passport） | `data-focus-selected`、`viewer.passport.*` |
| Semantic Lens | `data-lens-*`（模板内 59 处） |
| Route Probe（两节点间沿作者声明的关系找路） | `data-route-probe-*` |
| Reach（上游/下游可达闭包） | `data-reach-*`（模板内 65 处）、`viewer.passport.reach.*` |
| Node Finder（按标签或稳定 ID 搜） | `data-node-finder-*`、`viewer.finder.*` |
| Node Outline / Semantic Radar / Camera | `viewer/` 下 `node-outline.js`、`semantic-radar.js`、`viewer-camera.js` |
| Presentation Stage（`?present=1`） | `document.documentElement.setAttribute('data-present', 'true');` |
| Motion（Live/Still，默认 Still） | `viewer.motion.*`、`viewer/motion-governor.js` |
| 导出 PNG / JPEG / WebP / 双主题 SVG / WebM / Share Card | `viewer/export.js`、`viewer/export-cleanup.js` |

`archify/references/viewer-runtime.md` 明确说这些是**产物里已经有的**，生成时不用管：

> Read this only when the user asks for a reader-facing capability. Ordinary generation does not require implementing or re-documenting these features; they are already in the generated HTML.

（`meta.views` / guided views 已在 3.0 移除。`archify/schemas/README.md`：`\`meta.views\` is retired. The schemas still accept the old guided-view shape so existing files keep validating, but renderers ignore it; do not author it.`）

### 1.3 单文件？无外部依赖？体积多大？

**是单文件、自包含。** 实测（PowerShell 数正则，不是抽样）：

| 文件 | 字节 | `<script src=>` | 外部字体请求 | `<link>` |
|---|---|---|---|---|
| `archify/examples/web-app-rendered.html` | 825,776 | 0 | 0（6 个 woff2 以 `data:font/woff2;base64,` 内联） | 无 |
| `archify/examples/tree-archify-repository-rendered.html` | 856,939 | 0 | 0 | 无 |
| `archify/examples/class-payment-processors-rendered.html` | 854,615 | 0 | 0 | 无 |
| `archify/examples/waterfall-checkout-request-rendered.html` | 812,965 | 0 | 0 | 无 |
| `docs/cases/explainer/tls-first-visit.html` | 518,147 | 0 | 0（无 `data:font`，用系统字体栈） | 1 个，`rel="icon"`，`data:image/svg+xml` |
| `docs/cases/explainer/finalize-delivery.html` | 533,315 | 0 | 0 | 1 个，同上 |

在 `web-app-rendered.html` 里搜所有 `src=`/`href=` 且排除 `data:` 与 `#` 的值，只剩一条：`https://github.com/tt-a1i/archify`（页脚品牌链接）。explainer 页里除来源本身的 URL 外，也只有这一条。

体积为什么这么大：原生图页里 6 个 JetBrains Mono woff2 子集是内联的（模板注释 `/* JetBrains Mono variable WOFF2 subsets from Google Fonts service revision v24. … No local() source: an installed copy must not override the bundled font.`）；explainer 页里最大的那块是 gzip 压缩后 base64 的原生子图 HTML（`tls-first-visit.html` 的 `archify-explainer-prepared` payload 有 336,019 字符）。

---

## 二、中间表示（最关键）

### 2.1 explainer 文档 IR

`archify/schemas/explainer.schema.json`，标题 `"Archify Explainer v1"`，`additionalProperties: false`，必填 `["schema_version","diagram_type","meta","answer","panels","sources"]`。

**顶层四块**：

```json
"answer": { "required": ["summary"], "properties": { "summary": …, "reasons": { "maxItems": 4 }, "scope": … } }
"panels": { "minItems": 1, "maxItems": 500, "items": { "required": ["id","title","blocks"] } }
"sources": { "minItems": 0, "maxItems": 500 }
```

- `answer.summary` → `#/$defs/text`，即 `"minLength": 1, "maxLength": 20000` 的字符串。**只有 summary 是必填的**，reasons 与 scope 可省。
- `answer.reasons` → 字符串数组，**`"maxItems": 4`**，硬上限四条。
- `answer.scope` → 单条 text。
- `panels[].span` → `{"type":"integer","minimum":1,"maximum":12}`，对应 12 栅格；省略则由 `layout.mjs` 自动定。
- `panels[].blocks` → `"minItems": 1, "maxItems": 500`。

**13 种块类型**（`$defs/block` 的 `type` 枚举 + `allOf` 里的 if/then 派发）：

```
"prose", "list", "callout", "comparison", "facts", "metric",
"steps", "diagram", "code", "snippet", "chart", "diff", "image"
```

各块的关键字段（原文摘录）：

| 块 | 关键字段 | 原文片段 |
|---|---|---|
| `prose` | `id`,`text` | `"required": ["id","type","text"]` |
| `list` | `items`,`ordered`,`checklist` | `"ordered": { "type": "boolean" }, "checklist": { "type": "boolean" }` |
| `callout` | `level` ∈ `note`/`warning`/`open-question`，`title`,`text` | `"enum": ["note","warning","open-question"]` |
| `comparison` | `labelColumn`,`columns[]`,`rows[].cells[].{text,assessment,verdict}` | `"assessment": { "enum": ["good","caution","bad"] }` |
| `facts` | `entries[].{key,value}` | `"required": ["key","value"]` |
| `metric` | `label`,`value`,`limit`,`unit`,`note`,`typical` | `"limit": { "type": "number", "exclusiveMinimum": 0 }` |
| `steps` | `items[].{id,text,detail,target}`，`target` 含 `diagram`/`node`/`route`/`edges` | `"required": ["diagram"]`；`"route": { "prefixItems": […], "minItems": 2, "maxItems": 2 }` |
| `diagram` | `diagramType` ∈ 10 种、`spec` 或 `source` 二选一、`nodeSources`、`changes` | `"oneOf": [{ "required": ["spec"] }, { "required": ["source"] }]` |
| `code` | `source`（必须是某个 source 的 id）、`language` | `"required": ["id","type","source"]` |
| `snippet` | `language`,`title`,`text`（作者手写代码） | `"required": ["id","type","text"]` |
| `chart` | `title`,`text`（mermaid 围栏）或 `data{path,kind,x,y,unit}` | `"kind": { "enum": ["bar","line","pie"] }` |
| `diff` | `text`,`caption` | — |
| `image` | `path`,`alt`,`caption` | `"required": ["id","type","path","alt"]` |

注意 `code` 与 `snippet` 是**刻意分开的两种块**：`snippet` 允许作者手打代码（`"required": ["id","type","text"]`），`code` 不允许——它只有 `source` 一个来源字段。这条区分在写作规范里有对应条文（见第六节）。

`diagram` 块的 `nodeSources` 是"节点 → 来源 id"的映射：

```json
"nodeSources": { "type": "object", "propertyNames": { "$ref": "#/$defs/id" }, "additionalProperties": { "$ref": "#/$defs/id" }, "maxProperties": 500 }
```

### 2.2 `sources[]` 与 `source` 的三种定位

`$defs/source`：

```json
"required": ["id","title"],
"properties": {
  "id": …, "title": { "$ref": "#/$defs/text" },
  "url": { "type": "string", "minLength": 1 },
  "path": { "$ref": "#/$defs/short" },
  "lines": { "prefixItems": [{ "type": "integer", "minimum": 1 }, { "type": "integer", "minimum": 1 }], "items": false, "minItems": 2, "maxItems": 2 },
  "revision": { "type": "string", "pattern": "^[a-fA-F0-9]{40}$" }
}
```

所以一条 source 有三种可能形态，且**只有 id 和 title 是必填的**：

1. **网址**：`url` 给 `https://…`。校验在 `archify/explainer/validate.mjs`：`Source URLs must be credential-free HTTP(S) links.`（禁止带用户名/密码、禁止控制字符）。
2. **仓库文件 + 行区间**：`path` + `lines=[start,end]`。`path` 必须是相对路径、正斜杠、无点段、不得是 `.git`、不得命中敏感文件名（`archify/explainer/sources.mjs` 的 `safePath`：`'Use a relative path with forward slashes and no dot segments.'`）。
3. **仓库文件 + 行区间 + 钉死 commit**：再加 `revision`（40 位 SHA）。规则是**同一文档内所有仓库来源必须用同一个 revision**——`sources.mjs`：`'All repository sources must use the document’s pinned revision.'`。

作者侧的简写是 `@source <id> title=… url=…|path=… lines=start:end`，解析在 `archify/explainer/parse.mjs`：

```
if (a.lines!==undefined) { const range=a.lines.match(/^(\d+):(\d+)$/u); if (!range) fail(at+1,type,'Repository lines require start:end.','lines=10:20'); … }
```

### 2.3 正文里怎么引用来源（上标编号规则）

这是业主最关心的那一层。原文（`archify/references/explainer-authoring.md`，照抄）：

> `[reference text](source:docs)` renders the text followed by a numbered superscript; `[](source:docs)` renders only the superscript. Numbers follow first appearance; uncited sources follow in declaration order. The footer lists titles with URLs or repository positions.

翻译成机制：

- **`[文字](source:id)`** → 文字后跟一个上标编号（`<sup class="cite"><a href="#source-id">1</a></sup>`）。
- **`[](source:id)`** → 只出上标，不出文字（"空 label"是唯一被允许的空链接文字，`archify/explainer/inline.mjs`：`if ((!label.trim() && reference?.kind !== 'source') || !reference) { … problem('target', …) }`）。
- **编号按首次出现顺序**：`archify/explainer/inline.mjs` 的 `renderInline` 里，`if (!citations.has(ref.id)) citations.set(ref.id, citations.size + 1);`。
- **未被正文引用的 source 按声明顺序排在后面**：`archify/explainer/render.mjs`：`for(const source of document.sources)if(!citations.has(source.id))citations.set(source.id,citations.size+1);`
- **按阅读顺序渲染**：`render.mjs` 的注释 `// Render in reading order so the first citation receives number one.`
- **页脚列标题 + 位置**：`render.mjs` 的 `sourceList` 里，`const location=source?.path ? \`<code>${escape(source.path)}${source.lines?':'+escape(source.lines.join('–')):''}${source.revision?' @ '+escape(source.revision):''}</code>\` : '';`，有 url 就把 title 做成 `<a>`。

真实产物里的样子（`docs/cases/explainer/finalize-delivery.html`）：

```html
<ol class="reasons"><li>三道门复用同一个 CLI；finalize 校验每份回执的类型、字节数与哈希。<sup class="cite"><a href="#source-finalize-mjs">1</a></sup></li>…</ol>
…
<section class="sources"><h2>来源</h2><ol>
<li id="source-finalize-mjs" value="1">runFinalize 编排器<code>archify/bin/finalize.mjs:722–1050</code></li>
<li id="source-commit" value="2">commitDeliveryPair：备份、提交、回滚<code>archify/bin/archify.mjs:3236–3624</code></li>
</ol></section>
```

### 2.4 10 种原生图里"节点怎么挂 source"

原生图不用 explainer 的 `sources[]`，而是每套 schema 各在自己的**主元素集合**上加一个 `sources` 数组，指向 `common.schema.json#/$defs/sourceReferences`：

```json
"sourceReferences": {
  "type": "array", "minItems": 1, "maxItems": 3,
  "items": { "required": ["path"],
    "properties": { "path": {…maxLength: 240}, "line": {"minimum":1}, "end_line": {"minimum":1}, "label": {"maxLength":48} } }
}
```

**上限是每个元素最多 3 段引用**。挂载位置（逐个 schema 核对）：

| 图类型 | 挂 `sources` 的集合 | 证据（`…/schemas/<type>.schema.json` 里 `sourceReferences` 前的最后一个集合名） |
|---|---|---|
| architecture | `components` | `"sources": { "$ref": "common.schema.json#/$defs/sourceReferences" }` |
| workflow | `nodes` | 同上 |
| dataflow | `nodes` | 同上 |
| tree | `nodes` | 同上 |
| sequence | `participants` | 同上 |
| lifecycle | `states` | 同上 |
| erd | `entities` | 同上 |
| class | `types` | 同上 |
| timeline | `events` | 同上 |
| waterfall | `spans` | 同上 |

而**关系类集合没有** `sources`（connections / edges / messages / flows / transitions / relationships 都没有）。这条是刻意的，`archify/references/repository-authoring.md` 原话：

> Only the primary elements carry `sources`, at most three ranges each: Architecture components, Workflow, Dataflow and Tree nodes, Sequence participants, Lifecycle states, ERD entities, Class types, Timeline events and Waterfall spans. Relationships, messages, flows and transitions have none: cite the call, write or transition site on the element that owns it (the caller, the writer, the state being left) and keep further evidence in a note or card.

钉 commit 的字段在 `meta.repository`（`common.schema.json#/$defs/repository`）：

```json
"required": ["url", "revision"],
"properties": { "url": {…}, "provider": { "enum": ["github","gitee","gitlab"] },
  "link_mode": { "enum": ["web","local-only"] },
  "revision": { "type": "string", "pattern": "^[a-fA-F0-9]{40}$" } }
```

---

## 三、校验闸门

### 3.1 finalize 串了哪几道

`archify/bin/finalize.mjs`：

```js
export const FINALIZE_STAGES = Object.freeze(['validate', 'deliver', 'check', 'browser-check']);
```

但实际执行循环是：

```js
for (const stage of (needsBrowser ? ['deliver', 'check', 'browser-check'] : ['deliver','check'])) {
```

而 `const needsBrowser = type !== 'explainer' || browserCheck;`。所以：

| 类型 | 默认跑的门 |
|---|---|
| 10 种原生图 | `deliver`（内嵌 validate）→ `check` → `browser-check` |
| explainer | `deliver`（内嵌 validate）→ `check`；加 `--browser-check` 才开浏览器门 |

`archify/references/explainer-authoring.md` 确认了这一点：`Finalize validates, atomically delivers and checks the HTML; it does not launch a browser, and its receipt records the browser gate as not run.`

### 3.2 各门查什么

**validate**（内嵌在 deliver 里，`archify/explainer/validate.mjs` + `archify/renderers/shared/validator.mjs`）：

- JSON Schema 校验（用生成的校验器 `archify/renderers/shared/generated-validators.mjs`，1,020,040 字节，从 schema 生成）；
- ID 唯一性 + 保留字：`READER_IDS = new Set(['board','diagram-dialog','diagram-dialog-title','toast'])`，`'This identity is reserved for reader controls or generated footnotes.'`；
- 行内语言：`parseInline` 不接受裸 HTML、不接受 `![` 行内图、不接受 `~~`、不接受任意脚注，每种都有独立规则码（`explainer/inline-html`、`inline-image`、`inline-decoration`、`inline-footnote`…）；
- 引用可解析：`source:id` 必须存在于 `sources[]`，`block:id` 必须存在，`node:`/`route:` 必须指向该图里真实存在的节点/边；
- `code` 块必须指向**有 path 的** source：`'Code blocks require a repository source whose commit and lines can be checked.'`；
- 原生子图 spec 再跑一遍原生 schema：`try{validateSchema(block.diagramType,block.spec);}`；
- 写作规则（`archify/explainer/writing.mjs`，见第六节）。

**deliver**（`archify/bin/archify.mjs` 的 `commandDeliver`）：

- 拿目录级交付锁（`.archify-delivery-lock.json`，独占 `open(..., "wx")`）；
- 写 pending journal（`<stem>.delivery-pending.json`）；
- 在暂存目录渲染；
- 跑产物检查；
- 提交产物 + provenance 成对（`commitDeliveryPair`），失败回滚；
- 删 journal、放锁。

`archify/references/delivery-contract.md`：

> `deliver` acquires the lock by exclusive `open(..., "wx")` before creating or replacing the recovery journal. A successful exclusive create yields an internal opaque ownership capability bound to that attempt.

**check**（`archify/explainer/check.mjs` 或 `archify/scripts/check-render-output.mjs`）：

explainer 的 `checkExplainerHtml` 分四组自检（代码里的 `add(...)` 名字就是分组名）：

| 分组 | 查什么 |
|---|---|
| `explainer_structure` | `<html data-archify-artifact="explainer">` 家族标记；DOM ID 唯一；无 `on*` 内联事件；无 `<script src>`；无 `iframe/object/embed`；无 `javascript:`/`vbscript:` URL；`<img>` 必须 `data:image/…;base64`；所有 `#anchor` 必须能解析 |
| `explainer_payload_identity` | 两个 JSON payload（`archify-explainer-prepared` / `explainer-manifest`）各自只有一个、类型对、转义安全；bundle 的 `digest` 自洽；嵌入草稿重新解析后与 `document` 逐字节相等；`source.sha256`/`bytes` 对得上；`revision` 能重算且相等；`documentSha256` 相等；每个 panel/block/source 的 ID 都在 DOM 里 |
| `explainer_dependencies` | `dependencies[]` 每项的 `contentBase64` 解出来必须满足 `sha256` 与 `bytes`；图片资产必须与依赖绑定且 DOM 里的 `data:` 与冻结字节一致；代码摘录必须带 40 位 `revision` 且与依赖一致 |
| `explainer_native_diagrams` | 子图数量与 `diagram` 块数量一致；每个子图的 `html` sha256/bytes 与 manifest 一致；**把子图写进临时文件，spawn 一遍 `scripts/check-render-output.mjs` 做真检查** |

原生图的 `check-render-output.mjs` 是 9 项检查（`addCheck('single_svg', …)`、`finite_svg`、`orthogonal_arrows`、`label_route_clearance`、`relationship_crossings`、`relationship_corridors`、`container_border_runs`、`route_rhythm`、`legend_clearance`，外加条件性的 `svg_path_data`）。`delivery-contract.md` 明确"9 项才算过关"：

> A receipt with four artifact checks is basic validation, not showcase acceptance: require all nine checks, zero composition errors, and zero warnings.

**browser-check**（`archify/explainer/browser-check.mjs`，走 Chrome/Edge DevTools 管道）：

- explainer 页查 9 组：`containment` / `readability` / `viewerChrome` / `themeStates`（各 1280×900、1440×900 × light/dark）+ `commonQa` / `interactions` / `references` / `noJavaScript` / `print`；
- 具体项：横向溢出、键盘可达（`diagram-keyboard`）、点开图后原生 Viewer 是否真的聚焦到那一步的**精确节点与边**（`'The canonical Viewer did not focus the step’s exact nodes and edges.'`）、子图文字下限 10px 且 1440 宽时 ≥ 正文 75%（`'Native diagram text is below its viewport reading floor (10px; 75% of body at 1440).'`）、关 JS 时正文仍可读且交互控件隐藏、打印时正文完整且典型值脚注可点。

`finalize.mjs` 的 `validBrowserEvidence` 要求 viewport 覆盖**逐条精确匹配**：

```js
const viewports = [1280, 1440].flatMap(width => ['light', 'dark'].map(theme => ({ width, height: 900, theme })));
```

### 3.3 失败回执长什么样

诊断对象的最小形状（`archify/explainer/sources.mjs` 的 `fail` 就是模板）：

```js
throwDiagnosticError(message, [{ code: `explainer/${reason}`, severity: 'error', message,
  subject: location(document, pointer, component),
  evidence: { reason, example: example || examples[component] || examples.source }, supportedFixes: [fix] }]);
```

四要素：

1. **稳定规则码**：`explainer/source-path`、`explainer/secret-path`、`explainer/code-source`、`explainer/source-revision`、`explainer/repository-location`、`explainer/inline-html`、`explainer/writing-sentence-length`、`explainer/browser-diagram-text` …（码是"家族/规则"两段式，可 grep、可统计、可做修复率统计）。
2. **subject**：`{ line, column, component, path, panelId, input }` —— 指到草稿的具体位置，不是"某处有问题"。
3. **evidence**：`{ reason, example, …实测值 }`。实测值分情况：仓库证据失败带 `{ sourcePath, requestedLine, lineCount, revision }`；行数越界带 `{ sourcePath, requestedLine, lineCount, revision }`；写作规则带 `{ rule, matched, units, limit }`；浏览器门带 `{ measurement }`（含视口宽高、溢出元素、字号）。
4. **supportedFixes**：**只给渲染器真的支持的动作**。`archify/renderers/shared/repository-evidence.mjs` 里每种失败的 fix 都是具体的，例如 `'use a line range that exists at the pinned revision'`、`'fetch the pinned commit or pin an available full commit SHA'`、`'run \`git remote get-url origin\` inside --repo-root and declare that credential-free address'`。

`finalize` 层面还会把诊断压到 8 条（`compactFinalizeReceipt`：`const diagnosticLimit = 8;`），压法是三轮挑选：先按 `code` 去重各取一条，再按 `subject` 去重各取一条，最后按原序补齐；被压掉的按码计数写进 `diagnosticSummary.omittedByCode`。压缩回执还带 `nextAction`：

```js
compact.nextAction = { action: 'edit-in-place', candidate: …, constraint: 'Preserve unaffected semantics and geometry; apply each diagnostic\'s supportedFixes, or the fix its message names, and do not replace the whole candidate.', then: 'finalize-once' };
```

即：**不是"再跑一次"，而是"就地改一处，再跑一次"**。

### 3.4 为什么"原子替换 + 保留 last-good"

先说清楚它的实际做法，`archify/references/delivery-contract.md`：

> Publication is no-clobber and recoverable, not crash-atomic replacement of an existing target. To avoid overwriting a claimant that appears after the last identity check, Archify first retains the bound old file in a private recovery backup, removes the public name through identity-bound quarantine, and then creates the new public name with an exclusive hard link.

> The portable Node.js filesystem API has no pathname compare-and-swap that both replaces an existing name atomically and refuses to overwrite a late claimant: `rename` would close the visibility gap only by overwriting that claimant.

动机链（前半是原文，后半是我的推断，已标注）：

1. **原文**：每道门的证据都绑定到"确切的产物字节"——`Browser evidence belongs to exact artifact bytes.`、`Earlier browser or visual evidence remains bound to its original artifact bytes and must not be treated as evidence for changed HTML:`。
2. **原文**：失败时不许把旧产物弄坏——`If a currently verified owner fails after an older HTML exists, Archify writes a new status: "failed" sidecar and leaves the journal until recovery is complete.`、`An unreadable old HTML does not prevent that marker`、`Archify keeps the prior sidecar rather than deleting evidence`。
3. **我的推断**：把 1 和 2 合起来，逻辑是——如果允许"写到一半的产物留在目标路径"，那么页面上那份 HTML 的 sha256 与任何一份回执都对不上，而所有回执校验都是按 sha256 做的，于是**所有历史证据同时失效，且无法区分"产物坏了"和"证据丢了"**。所以只能是二元状态：目标路径上要么是"通过全部门、且有一整套对得上的回执"的新产物，要么是"上一次通过全部门、且回执仍在"的旧产物。
4. **原文**（Last-Good Live Preview 是同一思路的连续版）：`Invalid, half-written, deleted, or superseded input leaves the previous verified revision on screen and on disk. Identical bytes do not rebuild or reload.`
5. **原文**（收据本身也不许被覆盖）：`A later claimant or changed parent stops publication and remains untouched.`、`The two receipts are published individually, not as a crash-atomic pair; only a completed passing command is a successful handoff.`

还有一条很实用的纪律，`delivery-contract.md`：

> Compare diagnostics by code, subject, stage, and evidence, never by declining error count alone. Track the repair limit per persistent issue, using that code, subject, stage, and evidence: a newly exposed issue starts its own repair sequence. If an issue survives two focused repairs, inspect measured geometry or the relevant contract; after one evidence-based retry, report the concrete gap.

即：**不许拿"错误数变少了"当修好了**，同一个 (码, 对象, 阶段, 证据) 连续修两次不动，就停下报缺口。

---

## 四、证据机制细节

### 4.1 节点行末尾的 `source:<id>` 怎么工作

作者侧：在 `@sequence` / `@workflow` / `@erd` / `@tree` 等的管道行里，多加一格 `source:<id>`。`archify/references/explainer-authoring.md`：

> Any node, actor or entity row may end with a `source:<id>` cell naming a declared `@source`; hovering that node shows the source, and for a repository file its pinned lines, so a code diagram doubles as a code tour.

解析（`archify/explainer/parse.mjs`，注释照抄）：

```js
// A "source:<id>" cell ties that row's node to a declared source; the reader shows it on hover.
for(const r of rows){const index=r.cells.findIndex(cell=>/^source:[A-Za-z][\w-]*$/u.test(cell));if(index<0)continue;const node=r.cells[0].replace(/^(?:actor|entity)\s+/u,'').trim();if(index>0&&!r.cells[0].includes('>'))(block.nodeSources||={})[node]=r.cells[index].slice(7);r.cells=r.cells.filter((_,i)=>i!==index);}
```

注意三个细节：
- 只对**节点/参与者/实体行**生效（`if(index>0&&!r.cells[0].includes('>'))`——带 `>` 的是边行，边不能挂来源）；
- 那一格会从行里**删掉**再交给图的编译器，所以原生图 spec 里看不到 `source:`；
- 结果落在 `block.nodeSources = { <nodeId>: <sourceId> }`，进 schema，进渲染。

渲染侧（`archify/explainer/render.mjs`）：`${block.nodeSources ? \` data-node-sources="${escape(JSON.stringify(block.nodeSources))}"\` : ''}` 挂在 `.diagram-preview` 上。

读侧（`archify/explainer/reader.js`）：

```js
all('.diagram-preview[data-node-sources]').forEach(preview=>{
  let map = {}; try { map = JSON.parse(preview.dataset.nodeSources); } catch {}
  all('[data-node-id]',preview).forEach(node=>{
    const id = map[node.dataset.nodeId]; if (!id) return;
    node.classList.add('has-source');
    node.addEventListener('mouseenter',()=>show(node,id)); node.addEventListener('mouseleave',hide);
```

`archify/explainer/reader.css` 给了可见提示：`.diagram-preview .has-source{cursor:help}` 和 `.diagram-preview .has-source:hover rect:not(.c-mask){stroke:var(--accent);stroke-width:2}`。

**这条机制在仓库自带的 4 个 explainer 案例里没有被使用**：我在 4 份 `docs/cases/explainer/*.html` 里搜 `data-node-sources`，只命中 reader.js 自己的那段源码，没有一处实际数据属性。也就是说它是"可用但样例未演示"的状态。

### 4.2 悬停显示什么

`archify/explainer/reader.js` 的 `setupSourceCards`，注释先给结论：

```js
// A repository source shows its pinned excerpt; a web page its host; any other note its text.
```

卡片内容：

- 头部：来源类型图标（`code` / `web` / `note`）+ 标题（`source.title || source.path || id`）+ 位置串；
- 位置串：`const where = source.path ? \`${source.path}${source.lines ? \`:${source.lines.join('–')}\` : ''}\` : host;`，`host` 是 URL 的主机名（去 `www.`）；
- 正文：**仓库来源展示前 14 行带行号的代码**——`<pre><code>${lines.slice(0,14).map((line,index)=>\`<span class="line"><i>${first + index}</i>${escapeText(line) || ' '}</span>\`)…`，超过 14 行加一个 `…`；网页来源没有摘录，只显示 `source.text`；
- 页脚：`Pinned at <rev 前 7 位>` + `Open source ↗`（有 url 才出）。

卡片是 `role="tooltip"`，`mouseenter`/`focus` 触发，`mouseleave` 后 160ms 隐藏，`Esc` 立即关。

### 4.3 仓库文件怎么钉到某个 commit 的某几行

三步，全部在 `archify/explainer/sources.mjs` 的 `resolveExplainerSources` 里：

**第一步：确定仓库身份与 commit。** 优先用作者声明的 `meta.repository`；没声明就从本地 checkout 推：

```js
const raw = gitBytes(document, repoRoot, ['remote', 'get-url', 'origin'], '/meta/repository').toString('utf8').trim();
…
const revision = gitBytes(document, repoRoot, ['rev-parse', '--verify', 'HEAD^{commit}'], '/meta/repository').toString('utf8').trim();
```

**第二步：用 git 真读一遍那个 commit 下的那个文件。** 注意读的是 `revision:path` 的对象，不是工作区：

```js
const bytes = gitBytes(context, repoRoot, ['show', `${repository.revision}:${entry.path}`], `/sources/${index}`);
```

`gitBytes` 调用时固定加 `--no-replace-objects`：`spawnSync('git', ['--no-replace-objects', '-C', repoRoot, ...args], …)`，避免 git replace 把对象换掉。

**第三步：切行区间 + 冻结字节。**

```js
result.text = text.split(/\r\n|\n|\r/).slice(entry.lines[0] - 1, entry.lines[1]).join('\n');
const frozen = digest(bytes);
Object.assign(result, { sha256: frozen.sha256, bytes: frozen.bytes });
dependencies.push(Object.freeze({ kind: 'repository', id: entry.id, path: entry.path, revision: repository.revision, ...frozen }));
```

注意冻结的是**整个文件**的 sha256/bytes，摘录只是 `text` 字段。

**校验收在 `archify/renderers/shared/repository-evidence.mjs` 的 `verifyRepositoryEvidence`**，它把同一个"仓库 + 路径 + 行区间"当原生图的组件来源来验，等于复用原生图那套门。查的项（按失败码）：

`repository-evidence/repository-required` → `revision-invalid`（必须 40 位）→ `url-invalid`（不能是本地路径）→ `link-mode-invalid` → `provider-invalid` → `links-unsupported` → `root-required`（`--repo-root`）→ `root-unreadable` → `root-identity-indeterminate` → `root-not-top-level` → `origin-mismatch`（本地 origin 必须与声明 URL 同一身份）→ `revision-unavailable` → `object-unavailable` → `file-missing` → `line-required` → `line-range-invalid` → `line-out-of-range` → `file-unreadable` → `source-required`。

几个值得注意的实现细节（原文）：

- 只校验**已提交字节**：`Repository evidence is verified against committed bytes at the pinned revision, not working-tree edits`（`repository-authoring.md`）；
- 提交态与工作区不一致时，要求检查干净 checkout：`If the worktree is dirty, note the changed paths in your reply; the candidate has no field for them.`
- 敏感内容直接拒绝：`const SECRET_CONTENT = /-----BEGIN (?:[A-Z ]*PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|…/i;`，命中即 `explainer/secret-content`；
- 行数越界报的是实测值：`requests line ${requestedLine}, but ${source.path} has ${lineCount} lines at revision ${revision}`。

**渲染成网页链接**（`archify/renderers/shared/repository-location.mjs`）：

```js
if (provider !== 'gitlab') return `${url}/blob/${revision}/${encodedPath}${fragment}`;
return `${url}/-/blob/${revision}/${encodedPath}${plain}${fragment}`;
```

`fragment` 是 `#L<start>-L<end>`（GitHub）或 `#L<start>-<end>`（其他）；GitLab 的 Markdown 文件额外加 `?plain=1`，注释解释：`// GitLab renders Markdown blobs, where line anchors select nothing; the plain view keeps the cited lines highlighted.`

**一个必须说清的降级行为**：如果没有给 `--repo-root`，带 `path`+`lines` 的来源**不会报错**，而是静默退化成纯文字位置（页脚仍显示 `path:start–end`，但没有摘录、没有 commit、没有悬停代码）。`sources.mjs` 里那段 `cited` 循环是 `if (cited.length && repoRoot) { … try { … } catch {} }`——整个 catch 是空的。我实测了仓库自带的 4 个案例：`finalize-delivery.html` 的 5 个仓库来源，在 `explainer-manifest` 里**没有一个带 `revision` 字段**，`preparedSources.sources` 里也**没有 `text`**（只有 `id/title/path/lines`），而 `document.meta.repository` 里确实有 `"revision": "82c47ca31d83749020ff30d6b1172248e71d255d"`。也就是说：这份页面的来源是"位置声明"，不是"钉死并附摘录的证据"。写作规范承诺的 `With it, every cited repository source with a line range also shows its pinned lines when the reader hovers the citation` 只在带 `--repo-root` 时成立。

### 4.4 `SRC n` 徽标是什么（重要更正）

**文档说它有，HEAD 上的代码里已经没有这个徽标了——连那个 stub 方法也一起删掉了。**

文档与 CHANGELOG 的说法：

- `DESIGN.md`：`An evidence-backed node receives one viewer-only \`SRC n\` capsule in its upper-right corner. It inherits node state, adds no tab stop, and is stripped from every canonical visual export.`
- `CHANGELOG.md`（2.13.0 — 2026-08-03）：`**Verified Source Beacons.** Evidence-backed Architecture nodes now show one quiet viewer-only \`SRC n\` marker derived exclusively from the already verified repository payload.`
- `README_ZH.md`：`有证据的 Architecture 节点会显示 \`SRC n\`，并可打开由 Git 校验、固定到公开 commit 的文件与行号`
- `DESIGN.md` 至今仍保留 `### Verified Source Beacon` 一节；`viewer/README.md` 的 17 个小节里已经没有同名小节。

HEAD 上：`viewer/template.source.html`（被 `scripts/generate-viewer.mjs` 内联进 `archify/assets/template.html`）里搜 `installBeacons`，**0 处命中**。当前 `Archify.sourceEvidence` 模块的实际开头（照抄 `archify/assets/template.html`）：

```js
Archify.sourceEvidence = (function () {
  var element = document.getElementById('archify-source-evidence-data');
  var payload = null;
  if (element) { try { var parsed = JSON.parse(element.textContent || 'null'); if (parsed && parsed.verified === true && parsed.repository && parsed.nodes) payload = parsed; } catch (_) {} }
  // Keep verified evidence discoverable to screen readers without adding
  // visual marks. Restore first so repeated initialization never appends
  // another count or retains one after evidence becomes unavailable.
```

注释自己写着 `without adding visual marks`。

删除分两步，`git log -S` 可查：

1. 提交 `4bd3013`（`Refine Viewer reading scale, zoom and source presentation`，2026-10-07），该提交在 `viewer/template.source.html` 上 `3 insertions, 63 deletions`，删掉的正是可见徽标的绘制代码：

```
-      function installBeacons() {
-          if (!Array.isArray(sources) || !sources.length || node.querySelector('[data-source-evidence-beacon]')) return;
-          var label = viewerCount('viewer.passport.beacon', count);
-          var beacon = document.createElementNS(svgNamespace, 'g');
-          beacon.classList.add('source-evidence-beacon');
-          …
-    Archify.sourceEvidence.installBeacons();
```

2. 提交 `0942c7f`（`fix(viewer): preserve source accessibility and compact zoomed page flow`）删掉遗留的空壳 `-        installBeacons: function () { return 0; },`，把"留着假接口"这一步也清了。

配套测试也改了断言方向：`test/repository-evidence-types-browser.test.mjs` 里

```js
assert.equal(result.badgeCount, 0, type);
assert.match(result.sourceAria, /1 verified source reference/, type);
assert.equal(result.legacyMethodPresent, false, `${type}: obsolete beacon interface removed`);
```

`test/repository-evidence-browser.test.mjs` 同理：`assert.equal(observed.badges, 0);`。

**HEAD 上保留的是无障碍版本，不是可见徽标**：`Archify.sourceEvidence` 会给有来源的节点打 `data-source-evidence-count="<n>"` 并把 `aria-label` 拼上 `"{count} verified source reference"`（中文 i18n 键 `viewer.passport.sourceCount.*`）。我在整棵树里搜 `[data-source-evidence-count] {` 这种 CSS 规则，**0 处命中**——所以这个属性不产生任何可见图形。

旧实现还活在若干**冻结的历史产物**里（`docs/cases/shanghai-citywalk.html`、`docs/cases/job-search.lifecycle.html` 等仍有完整 `installBeacons()`），因为那些 HTML 是生成好就再不重渲染的。

真正的可见证据面在 **Semantic Passport**：`<div class="semantic-passport-evidence" id="focus-evidence" hidden aria-label="Verified source evidence">`，里面 `renderSourceEvidence(id)` 渲染 `repository.label + ' @ ' + repository.shortRevision` 与每条来源（`source.label || path 末段`、`L<start>–<end>`、有 href 就是链接）。`DESIGN.md` 的 `### Semantic Passport` 一节说它是"唯一的目的地"：

> One focused node opens one compact proof surface containing stable ID, authored metadata, relationships, and optional revision-pinned sources. It is the single destination for details; new capabilities should route here before proposing another panel.

**结论（对业主问题的直接回答材料）**：archify 现在**不再用图形徽标**提示"这里有证据"，而是把证据收进"点一下节点才出现的面板"。可见性换成了精确性——代价是读者得先知道要点。这是代码事实；至于作者是有意降级还是过渡态，我在 CHANGELOG 里没找到说明（见第七节第 6 条）。

---

## 五、可复用性判断（明确结论）

**结论：它的渲染器不是通用可复用组件，是绑死在它自己 CLI 上的产物生成器。可以抄机制，不能当库接进去。**

判断依据，逐条给证据：

### 5.1 没有对外 API 面

`archify/package.json` 全文关键字段：

```json
{
  "name": "archify",
  "version": "3.2.0",
  "private": true,
  "type": "module",
  "bin": { "archify": "./bin/archify.mjs" },
  "license": "MIT",
  "devDependencies": { "ajv": "^8.17.1", "simple-icons": "16.28.0" }
}
```

我核过：**没有 `exports` 字段，没有 `main` 字段，`private: true`**。唯一入口是 `bin`。`devDependencies` 只有构建期工具（ajv 用来生成校验器、simple-icons 用来生成品牌图标），运行期零依赖。

### 5.2 渲染入口是"读 argv 的脚本"，不是"接收参数的函数"

`archify/renderers/explainer/render-explainer.mjs` 整个文件 42 行，开头就是：

```js
const inputPath = path.resolve(process.argv[2]);
const sourceText = fs.readFileSync(inputPath, 'utf8');
```

`archify/renderers/shared/cli.mjs` 的 `loadDiagram` 也是 `argv[3]`、`process.env.ARCHIFY_REPO_ROOT`、`process.cwd()`。原生图渲染器同理（`render-architecture.mjs`、`render-erd.mjs` … 各自 `process.argv`）。也就是说：**想用它，就得 fork 一个 node 子进程、按它的命令行约定传文件路径**。

### 5.3 输入只能是它自己的 IR

- explainer 只吃 `candidate.archify.md`（它自有的受限 Markdown 方言）或它自己的 JSON；
- 原生图只吃 `schemas/*.schema.json` 那 10 套 IR；
- 没有任何"给我一堆数据，我帮你排成页面"的通用接口。`@chart` 算是唯一接近的——它读 CSV/JSON 文件出图——但也被绑在"草稿同目录 + `x`/`y` 列名 + 最多 60 行（饼图 12 行）"这套约定上：`The file is read and frozen at delivery, up to 60 rows (12 for a pie).`

### 5.4 唯一的"集成"只是注册一个 Skill 目录，不注册任何工具

`integrations/deepseek-harness/README.md` 原话：

> The adapter registers no native render/validate/deliver tools, custom Web client, Produced Files chips, telemetry, credentials handling, background services, or install hooks.

`integrations/deepseek-harness/lib/index.js` 全文只做一件事——从 DSH profile 解析出 `skills` 目录：

```js
export function resolveArchifySkillRoot(profileBaseUrl) { … return join(dirname(manifestPath), 'skills'); }
```

`cordis.patch.yml` 里靠 `bundledSkillDir` 挂一个 filesystem Skill provider。也就是说：**它给宿主的东西是"一份给 agent 读的说明书 + 一堆命令行"，不是"一套可调用的 API"**。

### 5.5 但产物是可复用的（这一半成立）

生成的 HTML 自带全部运行时：

- 0 个 `<script src=>`，CSS/JS 全内联（`archify/explainer/reader.css` 47,157 字节 + `reader.js` 51,676 字节；原生图侧是 `viewer/viewer.css` 183,092 字节 + 十几个 `viewer/*.js`，经 `scripts/generate-viewer.mjs` 按 `/* ARCHIFY:VIEWER_CSS */` 这类标记内联）；
- 字体以 `data:font/woff2;base64,` 内联，注释写明理由：`No local() source: an installed copy must not override the bundled font.`；
- 图片以 `data:image/…;base64,` 内联，且 `check` 阶段会验字节。

所以：**一份 archify 产出的 HTML 可以拷到任何地方双击打开、断网也能用、能当邮件附件发**。这一半是真本事，也是最值得抄的那一半。

### 5.6 许可证

`archify/LICENSE`：

```
MIT License

Copyright (c) 2026 tt-a1i (Archify)
Copyright (c) 2025 Cocoon AI
```

MIT ⇒ 法律上可以抄代码，但按本仓规矩（AGENTS.md「抄之前先核许可证并留出处」）需要随附版权声明。另外 `archify/THIRD_PARTY_NOTICES.md` 有第三方声明，内联的 Pele 图表库在 `archify/explainer/vendor/pele/LICENSE`（也需一并保留）。

---

## 六、写作规范原文摘录（`archify/references/explainer-authoring.md`）

逐条照抄，不转述。

### 6.1 结论先行

> An explainer turns an answer with a conclusion and some structure (an explanation, comparison, decision, diagnosis, review or plan) into one page. The page leads with the conclusion and shows the reasoning as panels: diagrams, tables, steps and short text.

> Write one Markdown file, `candidate.archify.md`. The first paragraph after the title is the direct conclusion. A flat list immediately after it gives up to four reasons. Each `##` heading starts a panel.

> The conclusion is read first; every panel after it supports, qualifies or applies it. Stop once nothing is left to support.

### 6.2 一屏一问

> Each panel takes one question and each sentence makes one claim. A claim a table or diagram already shows is not restated; the text adds its reason or exception.

> Prefer a specific question as each panel title. `{#id}` gives a stable ID for links and panel replacement; `{#id span=7}` fixes a width of 1–12 columns.

> A diagram replaces the paragraph that would describe it. When the answer involves relationships, a flow, an exchange over time, a hierarchy, a history or a data model, draw it. A typical page has the conclusion, one diagram and one or two tables or step lists.

> A small answer gets a small page: the conclusion plus one or two panels. A how-it-works, diagnosis or checklist question usually needs three to five.

> A document holds up to four native diagrams.

（"一屏一问"在代码里也有硬约束：schema `answer.reasons` 的 `"maxItems": 4`；写作 lint 的 `paragraph-length` 规则：`if (entry.component === 'prose' && (units(text) > 120 || sentenceCount > 4))` → `'Split the paragraph into a list, steps or a comparison; keep at most two or three short sentences of prose.'`）

### 6.3 每个论断可核查

> Cover what the reader needs to act on the answer: the mechanism behind the conclusion, how to check it, and the cases where it does not hold. The next question a careful reader would ask gets a panel, a table row or a line in scope; a fact the reader could get wrong without it is not optional.

> Give results with their evidence: a number with its unit, a file position, a source. When a value is unknown or estimated, say so in scope.

> Cite a `@source` for each claim the reader cannot check alone: protocol details, thresholds, benchmark figures, API behaviour. A rule of thumb without a source is labelled as one, or left out.

> `@code` obtains a real excerpt from the source's Git commit and line range; it accepts no authored code text.

> Pass `--repo-root /path/to/repository` for code excerpts. With it, every cited repository source with a line range also shows its pinned lines when the reader hovers the citation; a source that cannot be verified stays a plain reference. The tool resolves origin and HEAD, or accepts `@meta repo_url=... repo_revision=<full-commit>`. The commit, path and line range must exist; working-tree edits cannot replace committed bytes.

（仓库侧对应条文，`archify/references/repository-authoring.md`：）

> The source is the authority for responsibilities, calls, boundaries, and persistence. The diagram is complete when the requested meaning is covered and every asserted fact has supporting source evidence.

> **Name uncertainty.** Write unresolved questions beside the claim they affect: for example, "`writeFile` is called here; durability is unknown." Resolve a question by reading the next relevant source range or preserve it as an explicit unknown. Never turn a label, package description, or config value into an unobserved service or behavior.

> Stop exploring when every requested responsibility, relationship, and boundary has supporting source entailment and the remaining unknowns cannot change that coverage. There is no node, edge, citation, view, card, or boundary count to hit. Do not add a summary step merely to signal completion.

### 6.4 数字必须能重算

> Recompute every derived number before delivery and show the arithmetic once: "990 of 1000 requests at 80 ms → P99 = 80 ms; 11 slow → P99 = 600 ms." Totals in tables add up.

> A chart states where its numbers come from the same way text does: measured, from a source, estimated or illustrative, in its caption or in scope.

> A blank value is an error, not zero: fill it in, or leave the row out and say so in the caption.

（第三条在 CHANGELOG 3.2.0 里也有对应修复条目：`**Blank chart data is an error, not zero.** An empty CSV cell, a JSON null or a missing field in a charted column no longer becomes a zero bar. Finalize names the column and row instead.`）

### 6.5 措辞与句长（中英各一套）

> Phrase an action as an imperative with its trigger in front: "If the migration reports a schema mismatch, roll it back before retrying."

> When the reader must act or verify, end with a checklist panel: `- [ ] item`, one concrete check per item. Readers tick items on the page.

> English: short sentences (under about 25 words), common words (use, before, to, because), active voice with a named actor.

> 中文：短句，每句不超过约 50 字；动词直接用（检查、决定，而不是进行检查、做出决定）；一句话里的"的"不超过两个；数字后写清边界（超过 3 次、不超过 1 秒）；用具体结果代替套话（赋能、全方位、至关重要）。

这些不是口号，是**可执行的 lint**。`archify/explainer/writing.mjs` 的 `RULES` 数组逐条给正则与修复话术，例如：

```js
{id: 'light-verb', pattern: /进行(?![中时])\p{Script=Han}{2}|(?:加以|予以|做出|作出)\p{Script=Han}{2}|\b(?:perform an analysis of|…)\b/giu,
  reason: 'A light-verb construction can obscure the action.', example: '进行检查 → 检查；做出决定 → 决定; make a decision → decide', fix: 'Use the direct action verb where it preserves the meaning; name who performs the action.'},
{id: 'cliche', pattern: /赋能|抓手|全方位|多维度|深度融合|至关重要|不可或缺|一站式|底层逻辑|…/giu,
  reason: 'This stock phrase gives little information about the concrete outcome.', example: '赋能业务 → 让客服查到订单状态; seamless → name what no longer needs a manual step', fix: 'Replace the stock phrase with the specific action or outcome the reader needs.'},
{id: 'number-boundary', pattern: /(?<=\d\s*(?:个|次|秒|天|分钟|小时|倍|人|条|项|%|ms|MB|GB|KB|QPS)?\s*)(?:以上|以下|以内)/gu,
  reason: '"以上/以下/以内" after a number leaves the endpoint unclear.', example: '3 次以上 → 超过 3 次 / 不少于 3 次；1 秒以内 → 不超过 1 秒', fix: 'Say whether the endpoint is included: 超过/不少于, 低于/不超过.'},
```

句长阈值写死在 `lintExplainerWriting`：`const limits = {zh: 50, en: 28, ...sentenceLimits};`，超出报 `explainer/writing-sentence-length`，严重度由 `--writing warn|strict|off` 控制（`strict` 时是 error，会挡住交付）。另有 `de-chain`（一句话里 ≥3 个"的"）、`verdict-emphasis`（结论里超过 60% 的字被加粗）、`scope-length`（scope 超过 50 个阅读单位）、`qualification`（把"示例/未实测/illustrative"写进正文而不是 scope）等规则。

写作规范里还有一句自陈：

> Each warning names the matched text and a repair; fix it when the repair keeps the meaning. `--writing warn|strict|off` sets the severity.

---

## 七、我没读到 / 未确认的部分

诚实标注，避免后面被当成结论用：

1. **`archify/assets/template.html` 的完整交互实现细节我没逐行读完**。它是 786,886 字节、约 8,200 行，我读的是它的骨架、`applyTemplate` 占位符约定、`Archify.sourceEvidence` 模块、`renderSourceEvidence`、以及各 `data-*` 属性的分布计数。focus / lens / route-probe / reach / radar / camera 的**具体算法**没有读（对应源在 `viewer/*.js`，共约 700 KB，我只读了 `viewer/README.md` 的契约描述）。
2. **`archify/renderers/shared/generated-validators.mjs`（1,020,040 字节）没读**。它是从 schema 生成的校验器，我按"它等价于 JSON Schema 校验"来理解，未验证生成器是否加了额外约束。
3. **`browser-check` 的 9 组检查我只读了代码结构，没有实跑**。本机没起 Chrome，也没有 archify 的 node_modules。所有 browser-check 的结论都来自读 `archify/explainer/browser-check.mjs` 与 `archify/bin/finalize.mjs` 的校验函数，不是实测回执。
4. **`finalize` 的完整回执样本我没找到现成的**。仓库里没有提交 `.finalize.json` / `.browser-check.json` 样例文件（`Get-ChildItem -Recurse -Include *.finalize.json,…` 无结果），所以第 3.3 节的回执形状是从代码里读出来的，不是从真回执里抄的。
5. **`docs/cases/explainer/finalize-delivery.archify.md` 里声明的 `repo_revision=82c47ca31d83749020ff30d6b1172248e71d255d` 在本机浅克隆里取不到**（`git cat-file -e` 失败）。这不影响结论，但意味着那份案例页的"钉死 commit"在本机无法复验。
6. **`SRC n` 徽标的移除是否是有意降级还是过渡态，我没找到作者说明**。CHANGELOG 里 2.13.0 有"新增"条目，但 3.0.0 / 3.1.0 / 3.2.0 的 Changed 里**没有**"移除 SRC 徽标"的记录，`DESIGN.md` 与 `viewer/README.md` 也仍保留旧描述。我只能确定代码事实（`installBeacons: function () { return 0; }`、测试断言 `badgeCount === 0`），不能确定作者的意图。

---

## 附：一句话回答业主的原话

业主说「它这个证据似乎要更聪明一点」。按上面读到的事实，它的"聪明"具体是三件事，都可以逐条指到代码：

1. **证据是编号的、可点的、有下标的**，不是一段"来源：某某文件"的文字。编号按首次出现自动生成，页脚自动列表，读的人不用自己数。
2. **证据的"钉住"是编译期证明的**：`git show <40位commit>:<path>` 真读一遍字节、切行、算 sha256、写进依赖清单，再由 `check` 阶段重算比对。作者想"凭印象引一行"是过不了门的——因为 `@code` 压根不接受手写代码文本。
3. **证据的"位置"是坐标化的**：`path` + `[start, end]` 行区间 + commit，三者齐了才能生成 `…/blob/<sha>/<path>#L10-L30` 这种链接；行数越界报的是"你要第 900 行，这文件在 commit X 上只有 640 行"。

而我们的红箭头指向的是**原 PDF 的某一页/某个坐标**，它指向的是**某个 commit 下某个文件的某几行**。两者的差别不在"哪个更聪明"，在**被指的那一端是否可被第三方独立复核**：PDF 页面任何人打开都是那一页，行号则要拿到那个 commit 才能核对——所以它才需要额外做"钉 commit + 冻结字节 + 重算 sha256"这一整套。这一整套是为"行号会漂"付的代价，不是它比我们聪明。这句判断我标注为**我的分析**，不是仓库原文。

---

（本文只做取证，不含方案。方案与取舍见 `03-借鉴结论.md`。）
