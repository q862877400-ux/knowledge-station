# ks-dsh-plugin (P0 bridge + P1b ks_answer)

把一个「法规国标强关联 RAG」Python 引擎（KnowledgeStation）桥接进 DeepSeek Harness：
插件在首次调用工具时**懒启动**本地引擎，并将引擎的鉴权 HTTP API 暴露成模型工具
`ks_ping` / `ks_resolve_clause` / `ks_answer`。本版本（0.0.1）在 P0 骨架之上追加了
**P1b `ks_answer` 取证答案工具**：把引擎侧同步端点 `POST /api/v1/ks/answer` 暴露成模型可调
工具，并返回**裁剪后的三段式取证答案**（依据区 → 推导区 → 结论区）。

- 插件名：`ks-dsh-plugin`
- 引擎仓库根：`D:\AI\work space\zcode`（只读，不改引擎代码/数据）
- 引擎入口：`.venv\Scripts\python.exe -m src.core.main`（cwd=仓库根）
- 会话文件：`%APPDATA%\KnowledgeStation\engine.session.json` = `{port, token, pid, started_at}`
- 鉴权：除 `GET /api/v1/health` 外所有 `/api/v1/*` 需要 `Authorization: Bearer <token>`；
  成功响应包裹 `{"code":200,"status":"success","data":...}`。
- 引擎侧取证答案端点（P1a 已合入）：`POST /api/v1/ks/answer`，Bearer 鉴权，body
  `{"query":str,"params":{...}|null,"query_mode":str}`，成功响应 `data` 为
  `{tier,evidence,derivation,conclusion,verification,notes,_meta}`。**本插件不真调该端点**
  （会消耗真实 LLM 额度）——只在真实 DSH host 会话内经模型调用时按需触发。

---

## 目录

```
plugin/
  package.json        # npm 清单（type=module, main=src/index.js, dsh.bundle.patch）
  cordis.patch.yml    # bundle patch：insert 一行 ks-engine -> ks-dsh-plugin
  src/index.js        # cordis 插件：apply(ctx,config) 注册 ks_ping / ks_resolve_clause / ks_answer
  src/engine.js       # EngineManager：单实例判定 + 懒 spawn + 健康轮询 + Stop-Process 清理 (+apiPost)
  scripts/smoke.mjs   # 独立 host 侧冒烟（不依赖 cordis）
  README.md
```

---

## 安装

**当前不要动 profile**（`C:\Users\Zegel\.dsh\profiles\web`）。你用下面的命令安装：

1. （可选）确认 DSH CLI 存在：`dsh plugin --help`
2. **坑（实测 2026-09-05）**：`dsh plugin add` 会按空格拆分参数——仓库路径含空格
   （`D:\AI\work space\zcode\plugin`）即使加引号也会被拆成假依赖 `plugin`/`work`。
   **必须用无空格路径安装**。本机做法：staging 目录为 junction，指向仓库源码，改仓库代码即生效：
   ```powershell
   cmd /c mklink /J "C:\Users\Zegel\dsh-ks-src\ks-dsh-plugin" "D:\AI\work space\zcode\plugin"
   dsh plugin --profile web add "C:\Users\Zegel\dsh-ks-src\ks-dsh-plugin"
   ```
3. 该命令会读包的 `dsh.bundle.patch` 声明，将 `ks-dsh-plugin` 加入 `web` profile 的
   bundle 栈；profile boot 时会合并 `cordis.patch.yml` 里的那一行 `- insert:
   {id: ks-engine, name: 'ks-dsh-plugin'}`。安装本身不修改任何引擎/仓库文件。
4. 重启 `dsh web`（host 行不热更）以装载插件。重启后确认 `ks_ping` /
   `ks_resolve_clause` / `ks_answer` 出现在工具清单里。

> 若你的 profile 里已有手写的同 id 行，先删掉再装（避免重复挂载两条 Node 半）。
> 本插件无 client 半（不声明 `dsh.client`），所以**不需要**前端重建/刷新 UI。
> 回滚：`dsh plugin --profile web remove ks-dsh-plugin`；profile 文件备份为
> `package.json.bak-ksdsh` / `cordis.patch.yml.bak-ksdsh`（如有）。

### 可选 config（在 `cordis.patch.yml` 或 profile 的手写挂载行里给 `config:`）

```yaml
- insert:
    - id: ks-engine
      name: 'ks-dsh-plugin'
      config:
        engineRoot: 'D:\\AI\\work space\\zcode'
        python: 'D:\\AI\\work space\\zcode\\.venv\\Scripts\\python.exe'
        startupTimeoutMs: 60000
        idleTimeoutMs: 900000
```

缺省全部有内置默认值，不配即可跑。

---

## 工具（模型可见）

| 工具名 | 说明 | 鉴权 | 参数 |
|---|---|---|---|
| `ks_ping` | 探活引擎：返回引擎会话（port/pid/reused）+ `/api/v1/health` 数据 | 免 token | 无 |
| `ks_resolve_clause` | 引用解析：`standard_no` + `clause_number`，返回引擎查到的证据结构或明确未命中 | Bearer | `standard_no`、`clause_number`（均必填，工具自动 URL 编码） |
| `ks_answer` | 取证答案：`query`（必填）+ 可选 `params`（top_k/bookmarks_only/max_evidence）+ `query_mode`（default/thorough/quick/guess）→ 引擎三段式取证答案（裁剪后） | Bearer | `query`（必填）、`params`、`query_mode` |

三个工具都由 `src/engine.js` 的 `EngineManager` 支撑：

- **单实例**：每次调用先读 `engine.session.json` 并探活 `/api/v1/health`。已有健康实例
  就**复用**；没有才 spawn。spawn 用 env `KS_PYTHON`（缺省仓库 venv python），
  `cwd`=仓库根，`args=['-m','src.core.main']`，轮询到 session 文件出现且 `/health` 为
  200（超时约 60s）。
- **port/token 每次启动会变**：每次工具调用都重读 session 文件，绝不缓存死值。
- **只杀自己 spawn 的**：`ctx.effect()` 注册 dispose——空闲 30 分钟自动杀（2026-09-12 批3：
  15→30，`idleTimeoutMs` 可配；查法规模式有会话开着时 keepalive 续命）+ 退出清理；
  对**复用**的既有健康实例（spawn 前就健康）绝不杀。
- 失败返回明确错误（引擎未起 / 401 / 超时）。

---

## ks_answer 工具说明（P1b）

### 用途

`ks_answer` 把引擎侧的**取证答案链**（`POST /api/v1/ks/answer`）暴露给模型：模型给一个
合规/法规问题，引擎独立跑检索 + 自身 DeepSeek 推理 + typed_verifier 核验，返回**三段式**
取证答案。适合「合规判断 / 分级 / 数值限值 / 义务表述 / 新旧版废止」等需要权威溯源的场景。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `query` | string | ✅ | 合规问题，如「动火作业怎么分级」「气体探头装多高」。 |
| `params.top_k` | integer | ❌ | 检索 top-K（默认 8；工具钳制到 `1..50`）。 |
| `params.bookmarks_only` | boolean | ❌ | 只从收藏集检索（默认 false）。 |
| `params.max_evidence` | integer | ❌ | 返回证据上限（默认 8；引擎硬上限 8，工具钳制到 `1..8`）。 |
| `query_mode` | "default"\|"thorough"\|"quick"\|"guess" | ❌ | 问法/作答深度。缺省 `default`。 |

> 未在工具 schema 里暴露的 `params` 键（如 `channels`/`rerank`/`history`）会被**静默丢弃**，
> 不会传给引擎，从而不改变引擎检索语义、也不把模型字段泄漏进请求体。

### 返回（已裁剪）

引擎返回的 `data` 经 `trimAnswer()` 裁剪后，工具只把以下字段交给模型：

- `tier`：`direct | synthesis | reference`（direct=1 条实质直接命中；synthesis=≥2 条综合；
  reference=无直接现行规定/置信不足）。
- `evidence[]`：每条保留 `standard_no / clause_number / title / legal_status /
  legal_hierarchy / page_start / snippet / doc_id / clause_revision_id`（`snippet` 由引擎
  截断至 800 字，`evidence` 由引擎去重且上限 8——单次返回不会撑爆 prompt），外加
  **`evidence_url`**（P1c 增强①，2026-09-05）：可直接粘成 Markdown 链接的证据锚点
  （`http://127.0.0.1:1/__ks_evidence__?doc=…&page=…&rev=…`，无 doc 时为 `null`），
  编排把答案里的证据引用写成 `[依据](<evidence_url>)` 即可在 GUI 右栏打开原 PDF 定位。
  以及 **`bookmarked`（三态）**（2026-09-10）：`true` 在用户收藏集内 / `false` 不在 /
  **`null` = 未知**——收藏集查询失败时引擎**显式给 `null`**；旧引擎不带该字段时由 host 归一为
  `null`。用于判断「仅收藏」的范围过滤是否真的生效；host 只透传真值，**绝不把缺失强转成 `false`**。
- `derivation`：推导正文（含 `[[c:i]]` 引用标记）。
- `conclusion`：一句话结论。
- `verification`：`{is_valid, answer_confidence, confidence_reasons[], unsupported_clauses[],
  unverified_numbers[], modality_violations[], legal_element_violations[],
  citation_index_warnings[]}`——每类列表**截断/压缩**到 ≤8 项，对象项压缩为紧凑字符串。
- `notes[]`：即将生效版本等补充说明。
- `meta_summary`：`_meta` 折叠成的**一行摘要**（evidence_total / result_count /
  expanded_count / vector / rerank / llm_raw_len / llm_error）——不把 `_meta` 原样给模型。

**不返回模型**：`_meta` 原对象、`entity`/`table` 等超大冗余字段（均已折叠为
`meta_summary` 或裁剪）。

### 边界与错误语义（与 ks_resolve_clause 风格一致）

| 情形 | 行为 |
|---|---|
| 引擎未起 / spawn 失败 | `EngineManager.ensureLive` 抛错（引擎未就绪，含启动超时/解释器缺失），错误信息带 diag tail。 |
| HTTP 401 | 先**重读 session 文件并重试一次**（会话轮换）；仍 401 才抛错（token 可能错配）。 |
| HTTP 422 | 返回**结构化错误**对象（`ok:false, error:{code,message}`），不抛。 |
| HTTP ≥500 | 抛错（`engine error HTTP <n>: <msg>`）。 |
| HTTP 0（超时 / 断连 / abort） | 抛错，提示「引擎自带 LLM 推理可能 >120s，先 ks_ping 确认引擎在跑」。 |
| HTTP 200 但 `evidence` 为空 / tier=reference | 返回**结构化空结果**：`ok:true, found:false`，证据空、derivation/conclusion 由引擎给出（「依据不足」口径），**不抛错**。 |

> 关于超时：`ks_answer` 走引擎自己的 DeepSeek 推理，`timeoutMs` 设为 **120s**（详见
> `makeAnswerTool`）。若你的 DSH 会话对工具超时另有上限，请勿低于 120s，否则长推理会被杀掉。

### 成本与克制

`ks_answer` 每调用一次会消耗引擎侧真实 LLM 额度（走引擎自己的 LLM 凭据 + egress 审计；
2026-09-11 起变量名为 `KS_LLM_API_KEY` / `KS_LLM_BASE_URL`，旧的 `DEEPSEEK_*` 仍作只读回退，
详见引擎 `src/core/settings/api_credentials.py` 的模块说明）。**不是**零额度。用
`ks_retrieve`/`ks_resolve_clause` 能快速定位的简单引用问题，优先用便宜工具；只在需要
「权威取证三段式」时才用 `ks_answer`。

---

## 冒烟（证据）

```powershell
# Node 用 C:\Program Files\nodejs\node.exe；脚本不依赖 cordis
& "C:\Program Files\nodejs\node.exe" "D:\AI\work space\zcode\plugin\scripts\smoke.mjs"
```

它会：读 session → 健康则复用（不杀）否则 spawn → 打 `/health` 与 `/documents`（带 Bearer）
摘要 → 清理（只停自己 spawn 的）→ 退出码 0/1。判定标准：health 200 **且** 至少一个带 token
的端点（`/documents`）返回 HTTP 200 且响应体为 JSON。真实库可能为空或含文档——不假设具体
标准号存在。

> 冒烟脚本**不调用 `/ks/answer`**（那会消耗真实 LLM）；它只做 `/health`（免 token）与
> `/documents`（带 token）只读连通，用以验证鉴权通道可用。

### 当前门禁链（改动后必跑）

```powershell
cd "D:\AI\work space\zcode\plugin"
npm run smoke            # 八段：pdf-fit 19 · pdf-panel 29 · bs-contract 32 · settings SSR_OK · fence 20 · tool 49 · chatmode 125 · client-entry 27
npm run verify:commands  # 斜杠命令真注册表闸（需要 DSH 检出，见下）
```

`npm run verify:commands` 跑 `scripts/verify-commands-real.mjs`：用 **DSH 自己的 `CommandRuntime`**
（`new Context()` + `SessionStore` + `CommandRuntime` + `createScope`）注册并**真实派发**
`/forensic` 与 `/bookmarks`，断言真实 `register()` 接受定义、`ctx.commands.list(agent)`
（即 `/` 菜单的数据源）恰好含这两条、真实开关语义与会话日志 `command/run`+`command/done`、
dispose 不泄漏，并要求**护栏兜底零触发**。它必须在 DSH 检出根目录下运行（工作区包靠 tsx 读
`tsconfig.base.json` 的 paths 解析），包装器 `scripts/run-verify-commands.mjs` 负责切目录；
检出路径可用环境变量 `KS_DSH_CHECKOUT` 覆盖，缺失时退出码 2 并给指引。

**为什么不能只跑 smoke**：host 侧 `ctx.commands.register()` 会做 `normalizeDefinition` 校验并
**抛异常**，而该异常被 `registerKsChatModeCommands` 的逐条兜底接住后只剩一行 `console.error`
——定义写错的症状是「`/` 菜单里静悄悄没有这条命令」。所以这项验收必须在重启前离线做掉。

---

## 已知限制（P0 + P1b）

- **只注册了 3 个工具**，未接其它检索/问答端点、未接更好侧栏（client 半）。
- **无 client 半**：不提供侧栏/前端 UI，只在模型工具面生效。
- **单实例锁是「session 文件 + /health 探活」**，没有跨进程文件锁。极端并发（多个 DSH
  进程同时“无健康实例”）可能双双 spawn，属 P0 已知取舍。
- **`ctx.tools.register` 原始定义**（非 `defineTool`），工具参数校验由本插件自检（非空字符串、
  枚举钳制）。因未 import `@deepseek-ai/dsh-tools`，故插件运行时零 peer 依赖加载，但仍把该包
  列入 `peerDependencies` 以对齐惯例。
- **`ks_answer` 未在真实 DSH host 会话内验证**（P1b 已知遗留）：node --check 语法已过；
  但「模型真实调用并看到裁剪返回」需在**重启后的 dsh 会话**里让模型调用一次才能确认。
  **验证必做**：绝不为了“验证”而真调 `/api/v1/ks/answer`（会消耗真实 LLM 额度）；只读
  `/health` + `/clauses/resolve` 连通即可自证鉴权链路。
- **单次返回大小**：evidence ≤8 且每条 snippet ≤800 字由引擎保证，插件再做一次
  evidence 字段裁剪与 verification 压缩，单次返回不会撑爆模型 prompt。

---

## 安装与 host 验证状态（2026-09-05 实测）

- ✅ 已安装：`dsh plugin --profile web add` 成功（staging junction 路径），`dsh.profile.bundles`
  含 `ks-dsh-plugin`；`web --dump-config` 合并树中 `ks-engine` 唯一且启用（bundle patch 生效）。
- ✅ 真实 host 加载：第二 `dsh web` 实例（`--port 0 --no-open`）干净启动、日志零错误——
  `apply()` 内多次 `ctx.tools.register`（ks_ping/ks_resolve_clause/[ks_answer]）无抛错。
- ✅ 引擎懒加载符合预期：验证实例未触发任何调用时，未 spawn 引擎（session 无新 pid）。
- ⏳ **待验证**：模型真实调用 `ks_ping`/`ks_resolve_clause`/`ks_answer`（需在重启后的 dsh
  会话里让模型调用一次并看返回）；HMR/重载行为。engine 侧 `/health`+`/documents`+`/clauses/resolve`
  冒烟已在 P0 交付时通过（`/ks/answer` 不真调）。
- 备注：验证中发现并修复了**既有环境坏点**——`dsh-plugin-llm-verifier`（D:\AI\dsh-plugin-llm-verifier）
  零依赖声明却 import `@deepseek-ai/{schemastery,dsh-tools,dsh-llm}`，任何新 boot 都会挂；
  已用 junction 补进其自身 node_modules（若重装该插件会丢，需重补）。
- 备注：同 profile **双实例**会被 `web-ui-task-board` 的进程独占 ledger 挡住（task-board ledger
  owned by process X）；验证多实例时需临时禁用该插件。

---

## P1c-RouteA（进行中 2026-09-05）— 可点击取证引用闭环

目标：`ks_answer` 证据在 DSH web 里变成可点击蓝链 → 打开原 PDF 跳页/bbox。分两段：

**① host 半（已合入，语法过）**
- 新增同源路由 `GET /ks/session`（`ctx.webServer.register`，exact）：调 EngineManager.ensureLive()（懒拉起/复用）
  → `200 {ok, engine:{port,pid,reused}, token}` / `503 {ok:false,error}` / 405。token 只给同源页面（webserver 默认 127.0.0.1），不持久化。
- 可选路由 `GET /ks/assets/pdf.worker.min.mjs`：读插件 node_modules 的 pdfjs worker（需 `pnpm add pdfjs-dist`，缺失 404 不影响其它）。
- 测试：dsh 重启后 `curl http://127.0.0.1:3080/ks/session` 应触发懒拉起并返回会话。

**② client 半（源码已就位 client/*.tsx，构建未做）**
- `client/`：entry.ts（apply+inject betterSidebar）、KsEvidenceTab.tsx（pdfjs 渲染+跳页+bbox 黄框+loading/error/重试）、api.ts（fetchSession/fetchPdf，token 仅内存）、ksEvidence.ts（urlTarget 认领 `/__ks_evidence__` 伪源）、pdf-configure.ts（worker 同源接线）。
- 未挂 `dsh.client`/未产出 `client.js`（client-modules 对声明无产物是硬失败——不可先行声明）；构建与真机点击验证 = 下一阶段。
**② client 半（已构建 2026-09-05）**：`client.js` 已由 `scripts/build-client.mjs` 产出（esbuild：react/@deepseek-ai 外置、pdfjs-dist 内联、__ModuleLoader__ 握手）；package.json 已挂 `dsh.client`（platform web, inject 含 dsh-better-sidebar）+ `exports["./client"]`。重建：`cd plugin && node scripts/build-client.mjs`（改 client/*.tsx 后需重建 + dsh 重启/刷新）。

**增强① 编排拼锚点（host 已合入 2026-09-05，待真机验证）**：`src/index.js`
- 新增 `evidenceAnchor()` + 常量 `KS_EVIDENCE_PATH` / `KS_EVIDENCE_ORIGIN`（URL 契约与
  `client/ksEvidence.ts` 完全一致：`http://127.0.0.1:1/__ks_evidence__?doc=…&page=…&rev=…`；
  **不含 bbox**——黄框推迟到收藏跳转一起做）。
- `trimEvidence` 每条 evidence 附加 `evidence_url`（无 doc → `null`）。
- `ks_answer` description 引导：把 `evidence_url` 渲染成 `[依据](<evidence_url>)` Markdown 链接。
- 自检：`node --check` 过；`evidenceAnchor` 5 分支冒烟全过（含编码/兜底）。
- **待真机验证**：dsh 重启后跑一次 `ks_answer`，确认返回每条 evidence 带 `evidence_url`，
  再在会话里把链接粘成 Markdown 点击 → 右栏 PDF 跳对应页。

**增强① 真机修复（2026-09-05，client 半）**：连续点击多个证据链接"无反应/同一页"——
better-sidebar `openTab` 对 `single:true` 单例 tab 只 **FOCUS** 不更新 path（service.ts
urlTarget 注释明示：the id safety net focuses the existing tab… the new URL is not
applied），首次点击建 tab 后再次点击全部落空。修复：`client/entry.ts` 自装 document 级
capture click listener 接管证据锚点 → `preventDefault` + `openTab`（建/聚焦）+
`updateTab` 强制覆写单例 path → KsEvidenceTab 的 `[tab.path]` effect 侦测变化即重新
loadEvidence 跳页（幂等；updateTab 对缺失 tab 是 no-op）。翻页后点同一条不跳（path 同值
无状态变化）→ updateTab 附 `meta:{ksClick:++n}` 单调 nonce 强制 `[tab.path, tab.meta]`
effect 重载。**重建 client.js 后浏览器硬刷新即可生效（client 半改动不需 dsh 重启）**。

**增强② bbox 轻端点 + 红箭头定位（2026-09-05 闭环，verifier 全程）**：黄框改红箭头
（用户拍板：不要黄框、做红箭头、粗、高≈一行字）。
- 引擎 `server.py`：只读 `GET /api/v1/clauses/{clause_revision_id}/spans` —— source_span
  的 bbox **底部原点原样透传零转换**（auth 由中间件统一挡）；404 clause_not_found /
  空 spans。schema/检索/SSE 零改动。
- host `index.js`：`GET /ks/bbox?rev=`（同源代理，token 不出 host）——401 重读重试、
  引擎 404 → `{ok:true,found:false,spans:[]}` 无框降级、缺 rev → 400、非 GET → 405。
- client：`loadEvidence` 在 `setLoad(ready)` 前经 `fetchBbox` 取锚行 bbox（目标页首条
  span）；`renderPage` 在锚行左缘画红色实心右箭头（data-URI SVG 2:1，高 clamp 10-56，
  尖端贴行首）；仅在 `evidence.current.page === 当前渲染页` 时显示。
- **根因修复（verifier 三路定案）**：箭头/黄框此前永不显示 = `viewport.convertToViewPoint`
  是 pdfjs **不存在**的方法名（真实名 `convertToViewportPoint` / `convertToViewportRectangle`
  / `convertToPdfPoint`；`.mjs` 运行时 + `.d.ts` + 全 build 扫描 + 真实 getDocument 探测
  四方互证）→ 运行时 TypeError 被 render effect 的 `.catch(()=>{})` 静默吞掉；PDF 正文在
  抛错前已渲染完，故跳页正常无报错。esbuild 不查类型故构建期拦不住。已改 `convertToViewportPoint`
  + 坐标契约注释（底部原点直接传入、禁 H−y 翻转）+ data-URI 前缀 `;charset=UTF-8,` +
  render 异常 `console.warn` 留痕。
- 验证：host 代理 curl 四边界全绿；**用户实测红箭头在目标页条款行显示成功**。

**增强③ 收藏 tab + 证据互跳 + 标准级收藏（2026-09-05 闭环，verifier 全程）**：
- **A 🔖 收藏 tab**：`client/KsBookmarksTab.tsx`（single `ks:bookmarks`）——列出条款收藏
  （标准号·条款号/标题/摘要/时间），点击拼证据锚点跳 ks:pdf 单例、逐条删除、空态引导、
  激活（visible）时自动刷新。注册在 `entry.ts`。
- **B PDF 查看器内互跳**：`KsEvidenceTab` 维护去重历史队列（≤20），header「最近证据…」
  下拉切回同文档旧证据（复用 [tab.path,tab.meta] nonce 重载）。
- **标准级收藏（schema 契约变更，全套流程）**：
  - schema.sql 新表 `user_doc_bookmark`（doc_bookmark_id/doc_id UNIQUE FK CASCADE/remark/
    created_at）；test_contract.py 表清单 + 列级测试；ENCYCLOPEDIA §4.3 登记。
  - `user_data.py`：add_doc_bookmark/remove_doc_bookmark/remove_doc_bookmark_by_doc/
    list_doc_bookmarks/bookmarked_doc_ids + remove_bookmark_by_clause_key。
  - 端点：GET/POST/DELETE `/api/v1/doc-bookmarks`、`DELETE .../by-doc/{doc_id}`、
    `DELETE /api/v1/bookmarks/by-clause/{clause_key}`；`clauses/{cid}/meta` 增
    `doc_bookmarked` / `clause_bookmarked` / `clause_bookmark_id` 真值。
- **UI（用户多轮打磨）**：条款收藏=竖排小标签贴红箭头左侧（页面左边注带 2..18px、
  箭头收窄 1.4×行高且 x≥18 让位，互不遮挡不压正文）；顶部按钮=「收藏本标准」（蓝/金
  toggle 换色）；PDF tab 更名「PDF 查看器」（去 📖 图标与 rev/doc 技术串；收藏 tab「收藏」
  🔖 仅图标）；条款/标准收藏均可再点取消；tab 重新可见时 refreshMeta 同步收藏真值
  （收藏 tab 删除后回 PDF 状态正确）；「已收藏条款」= header 金色下拉（本文档已收藏条款，
  选中跳转）。
- 验证：全量 **561 passed + 4 skipped**；引擎端点 curl 全链路（meta 真值 / by-clause /
  by-doc toggle 往返）；用户实测收藏/跳转/取消/跨 tab 同步。

**文件目录 + 标题目录移植（2026-09-06，verifier 全程）**：
- **📚 文件目录**：不再独立 tab——`KsFilesTab.tsx` 导出可复用视图 `KsFilesView`
  （props {active, onOpenDoc}，嵌入 PDF 查看器左列"文件目录"模式）。api.ts 补
  `fetchCategories`/`fetchDocTree`/`batchDeleteDocs`/`fetchDocsFlat` + 类型。保留原项目
  全功能：4 级分类树（标准→CCS、法规→效力等级叶）、搜索纯前端过滤+自动展开、多选/全选/
  批删（确认条 → confirm:true → 成功/失败条）、废止灰+删除线、点文档交宿主加载。
- **📖 标题目录**：PDF 查看器左侧内嵌窄列（~190px，数据 `GET /documents/{doc}/tree`），
  level1 章加粗 / level2 小节缩进，点条目跳页；「◀」收起回全宽。
- **左列双模式**：列头「📚 文件目录 | 📖 标题目录」（文件目录左、标题目录右，默认标题
  目录）；文件目录点文档 → 本 tab 直接加载 + 自动切回标题目录。右上角引擎状态行已移除。
- **「法规标准知识库」设置栏目**：`settings.section` 顶层 nav（settings 壳左侧栏目，
  better-sidebar「侧边卡片」同款机制）——`KsSettingsSection.tsx`（useSyncExternalStore
  响应式 + 内联开关）+ entry.ts `registerKsSettingsSection`（inject 增 'slots'）；
  首项「显示红色定位箭头」写读 `pluginSettings['ks:settings']`；KsEvidenceTab 响应式订阅
  即时生效。hidden 卡保留为一致写通道。**为何不用 hidden tab 卡**：tab 卡契约上只能成为
  feature 卡、无法成为设置栏目（verifier 定案，index.tsx:430 实证 settings.section 同款）。
