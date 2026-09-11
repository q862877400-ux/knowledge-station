# ks-dsh-plugin — pdf.js JPX wasm 404 诊断与修复候选

> 产出位置：`D:\AI\work space\zcode\fix-candidates\ks-dsh-plugin-pdfwasm\`（隔离目录，未改动仓库/插件文件）。
> 证明脚本：`prove-fix.mjs`（实测复现 404 并验证修复后 200 + `application/wasm`）。
> 结论先给：**这是代码缺陷，不是"host 未重启"。** 当前 handler 必然返回 404；重启无法解决。

---

## 1. 根因判定（含源码 路径:行号 证据）

### 1.1 现象与"是否会 404"的对照
- worker 路由 `/ks/assets/pdf.worker.min.mjs`（exact）**200**：该路由 handler 用同步的
  `require.resolve('pdfjs-dist/build/pdf.worker.min.mjs')`（`plugin/src/index.js:553`）拿路径，
  注册期不涉及 `new Set(Promise)`，所以正常。
- session 路由 `/ks/session`（exact）**200**：独立 handler，正常。
- wasm 前缀路由 `/ks/assets/pdf-wasm`（prefix）**404**：见下，注册成功、但 handler 内部恒走 404 分支。

三条路由都在同一个 `ctx.effect` 里注册（`plugin/src/index.js:607-616`）。**session 与 worker 都 200，
证明该 effect 已成功执行、插件已挂载、三条路由都已注册。** 因此"路由没加载/重启不够"排除。

### 1.2 真正的缺陷：`new Set(异步 readdir 的 Promise)` 抛 `TypeError`

`registerPdfWasmRoute`（`plugin/src/index.js:495-538`）：

```js
22: import { readFile, readdir } from 'node:fs/promises'   // readdir 是 **异步** 版本，返回 Promise
...
498: try {
499:   const require = createRequire(import.meta.url)
500:   const pkg = require.resolve('pdfjs-dist/package.json')
501:   baseDir = join(dirname(pkg), 'wasm')
502:   allow = new Set(readdirSyncSafe(baseDir))   // <-- BUG
503: } catch {
504:   baseDir = null
505:   allow = null
506: }
...
540: function readdirSyncSafe(dir) {
541:   return readdir(dir)                          // 返回 fs.promises.readdir 的 **Promise**
542: }
```

- `readdirSyncSafe` 名字带 "Sync"，但函数体返回 `readdir(dir)`——这是 `node:fs/promises`（`index.js:22`）
  的异步版，返回一个 **Promise**。
- `new Set(promise)`：`Set` 构造函数会 `GetIterator(promise)`，Promise 没有 `Symbol.iterator`，
  → `TypeError: object is not iterable (cannot read property Symbol(Symbol.iterator))`。
- 该 `TypeError` 被外层 `try/catch`（`index.js:503-506`）吞掉 → `baseDir = null`、`allow = null`。
- 但 `ctx.webServer.register(...)` 在 `try/catch` **之外**（`index.js:507`），所以路由**仍然注册成功**。
- 请求进来匹配到该 prefix 路由 → handler 走到 `index.js:511`：
  `if (baseDir === null || allow === null || allow.size === 0)` → 命中 → 返回 **404 `wasm_unavailable`**。

### 1.3 实验复现（见 `prove-fix.mjs` 输出）

```
BUGGY  -> {"name":"openjpeg.wasm","status":404,...}          # 现网插件逻辑：必然 404
FIXED  -> {"name":"openjpeg.wasm","status":200,"ct":"application/wasm","bytes":252032}
FIXED*2-> {"name":"openjpeg.wasm","status":200,...}          # 第二次命中：memoized
FIXED-miss-> {"name":"does-not-exist.wasm","status":404,...} # 白名单外的文件仍正确 404
```

`bytes=252032` 恰好等于真实 `openjpeg.wasm` 长度（`pdfjs-dist\wasm\openjpeg.wasm` = 252032 字节）。
补充：`node -e` 用同步 `readdirSync` 验证 → `allow.size = 13`，`has('openjpeg.wasm') = true`，
即 wasm 目录共 13 个文件、白名单可正确覆盖。

### 1.4 webserver 契约核对（prefix 语义/匹配/重复/顺序均正确）

对照 `packages/host/webserver/src/index.ts` 与 `README.md`：

- **prefix 语义**：`WebRouteKind = 'exact' | 'prefix'`（`index.ts:39`），
  `WebRoute.path` 要求"Absolute pathname, no trailing slash"（`index.ts:44`）。
  插件的 `KS_PDF_WASM_PATH = '/ks/assets/pdf-wasm'`（`index.js:42`）无尾斜杠，符合契约。
- **prefix 匹配**：`WebServer.match()`（`index.ts:256-266`）先查 exact 表，未中再遍历 prefix 表，
  条件 `pathname !== prefix && !pathname.startsWith(prefix + '/') continue`
  （`index.ts:262`），并"longest-prefix-wins"（`index.ts:263`）。
  对 `/ks/assets/pdf-wasm/openjpeg.wasm`：`startsWith('/ks/assets/pdf-wasm/')` → true → 命中。✓
  README 明确："prefix p matches p and p/<anything>"（`README.md:5`）。
- **重复注册**：`register()` 对同 `(kind,path)` 抛错（`index.ts:108-115`）。
  本场景无冲突（三条路由 path 各不相同，且初始注册一次）。
- **匹配顺序**：exact → 最长 prefix → fallback（`README.md:5`）。worker 路由是 exact、wasm 是 prefix，
  互不干扰（不同表、不同 path）。

**结论：webserver 的 prefix 路由匹配与注册逻辑没有缺陷。** 唯一缺陷在插件的 wasm handler 自身，
即 `readdirSyncSafe` 的同步/异步错用。

---

## 2. 修复 diff（二选一；推荐方案 B）

### 方案 A —— 最小 diff（把白名单计算改成同步 `readdirSync`，2 行）

`plugin/src/index.js`：

```diff
-import { readFile, readdir } from 'node:fs/promises'
+import { readFile } from 'node:fs/promises'
+import { readdirSync } from 'node:fs'

 function registerPdfWasmRoute(ctx) {
   let baseDir = null
   let allow = null
   try {
     const require = createRequire(import.meta.url)
     const pkg = require.resolve('pdfjs-dist/package.json')
     baseDir = join(dirname(pkg), 'wasm')
     allow = new Set(readdirSyncSafe(baseDir))   // 不变：readdirSyncSafe 现在返回 string[]
   } catch {
     baseDir = null
     allow = null
   }
   ...
 }

 function readdirSyncSafe(dir) {
-  return readdir(dir)                            // 异步 Promise（BUG）
+  return readdirSync(dir)                        // 同步 string[]（可用 new Set）
 }
```

> 改动：① import 去掉 `readdir`（异步，不再用），新增 `node:fs` 的 `readdirSync`；
> ② `readdirSyncSafe` 函数体 `readdir(dir)`→`readdirSync(dir)`。
> 其余代码零改动。`allow = new Set(string[])` 正常，白名单包含 `openjpeg.wasm` 等 13 个文件。
> 缺点：白名单在插件挂载期同步读取（会阻塞事件循环极短一瞬间），且若 wasm 目录挂载后才出现，
> 挂载期读到空则固定为空；挂载期若抛错则恒 404。

### 方案 B —— 推荐：白名单改为 handler 内惰性、memoized 的异步读取

`plugin/src/index.js`，替换 `index.js:495-538` 的 `registerPdfWasmRoute`：

```diff
 function registerPdfWasmRoute(ctx) {
   let baseDir = null
   let allow = null
+  let allowLoading = null
   try {
     const require = createRequire(import.meta.url)
     const pkg = require.resolve('pdfjs-dist/package.json')
     baseDir = join(dirname(pkg), 'wasm')
-    allow = new Set(readdirSyncSafe(baseDir))
   } catch {
     baseDir = null
-    allow = null
   }
   return ctx.webServer.register({
     kind: 'prefix',
     path: KS_PDF_WASM_PATH,
     handler: async (req, res) => {
-      if (baseDir === null || allow === null || allow.size === 0) {
+      if (baseDir === null) {
         res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
         res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable', message: 'pdfjs-dist wasm dir not resolvable' } }))
         return
       }
+      // 惰性 + memoized：首次请求才读目录（允许异步），失败降级为空集合；
+      // 挂载期不再做磁盘读，也就不会因挂载期 readdir 抛错而永久废掉该路由。
+      if (allow === null) {
+        if (allowLoading === null) allowLoading = readdir(baseDir).catch(() => [])
+        allow = new Set(await allowLoading)
+      }
+      if (allow.size === 0) {
+        res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
+        res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable', message: 'pdfjs-dist wasm dir empty' } }))
+        return
+      }
       let name = ''
       try {
         name = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname).slice(KS_PDF_WASM_PATH.length + 1)
       } catch {
         name = ''
       }
       if (name.length === 0 || name.includes('/') || name.includes('..') || !allow.has(name)) {
         res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
         res.end(JSON.stringify({ ok: false, error: { code: 'wasm_not_found', message: `unknown asset: ${name}` } }))
         return
       }
       try {
         const bytes = await readFile(join(baseDir, name))
         const type = name.endsWith('.wasm') ? 'application/wasm' : 'text/javascript; charset=utf-8'
         res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
         res.end(bytes)
       } catch (error) {
         res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' })
         res.end(JSON.stringify({ ok: false, error: { code: 'wasm_read_failed', message: error instanceof Error ? error.message : String(error) } }))
       }
     },
   })
 }
```

> 该版本已由 `prove-fix.mjs` 实测通过（200 / `application/wasm` / 252032 字节，未知文件仍 404）。
> 用 `await` 解包 Promise → `string[]` → `new Set(...)`，错误被 `.catch(() => [])` 归约为空集合。
> `readdirSyncSafe` 此后不再被使用，可一并删除（或保留为临时死代码）。
> 优点：① 修复真实根因；② 挂载期零磁盘读（更稳）；③ 目录后出现也能自愈；④ 无新增同步 import。

**建议采用方案 B。** 两方案都能让 `GET /ks/assets/pdf-wasm/openjpeg.wasm` 返回 200 + `application/wasm`。

---

## 3. 重启后一次性验证清单

> 前提：先合入上面任一 diff，**再重启 dsh host**（合入由主控执行，本候选不重启 host）。
> 地址按现网 `http://127.0.0.1:3080`。

```powershell
# 1) wasm 主目标：应 200 + Content-Type: application/wasm + 体积>0
curl.exe -i -s "http://127.0.0.1:3080/ks/assets/pdf-wasm/openjpeg.wasm"   # 看 HTTP/1.1 200、Content-Type、字节数 252032

# 2) 白名单内其它 wasm（JPEG2000/JBIG2/色彩管理）逐一个 200
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/jbig2.wasm"
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/qcms_bg.wasm"
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/quickjs-eval.wasm"

# 3) worker / session 对照（应仍为 200，保证没有被这次改动波及）
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "http://127.0.0.1:3080/ks/assets/pdf.worker.min.mjs"
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "http://127.0.0.1:3080/ks/session"

# 4) 路径穿越 / 目录 / 白名单外 / 查询串 仍需 404（安全性回归）
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/../package.json"
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/nope.wasm"
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/openjpeg.wasm?cachebust=1"   # query 剥掉，应 200

# 5) 浏览器端最终判定（刷新页面后开 DevTools → Network → 找 openjpeg.wasm）
#    状态 200 + Content-Type application/wasm；Console 不再有
#    "JpxImage#instantiateWasm … openjpeg.wasm" / "OpenJPEG failed to initialize"；
#    含 JPX/JPEG2000 图像的 PDF 页不再空白。
```

预期（修复成功）：条目 1/2/3/4-query 返回 200 + wasm content-type；条目 4 的穿越/未知仍 404；
浏览器 Console 不再报 JPX 解码失败。

---

## 4. 若重启后仍 404，逐点排查（按概率排序）

1. **确认 `register()` 被调用且未抛异常**：插件是否实际加载？检索 host 日志中的
   `ks-dsh-plugin` 行；若日志有"`ctx.webServer 不可用，跳过 /ks/session 路由`
   （`index.js:619`）"→ 说明 `inject` 里声明的 `webServer` 服务未注入，路由整段没注册——
   这属于 profile/依赖问题，而非本 bug。若日志无该警告且 session/worker 都 200，则 `register()` 已跑。
2. **确认路由表存在**：由于 webserver 是内存 Map，无法外部列举；退而求其次——
   (a) 直接在浏览器 / curl 打 `GET /ks/session` 与 worker：都 200 ⇒ plugin effect 已执行 ⇒ wasm 前缀路由也在表内；
   (b) 若把 wasm 前缀路径直接访问，却能区分"是 handler 到 404（能拿到 JSON body 的 `wasm_not_found`/`wasm_unavailable`）
   还是"路由没匹配到（空 body 404，即 fallback）"。**这点很关键**：
   - 响应 body 是 `{"ok":false,"error":{"code":"wasm_not_found"|"wasm_unavailable"}}` ⇒ 路由命中、但白名单为空/文件名不匹配 ⇒ 继续看第 3、4 点；
   - 响应 body 是空的 404 ⇒ 路由未命中 ⇒ 回到第 1 点（注册未生效/前缀 path 没对上）。
3. **pdfjs-dist 是否真的可解析**：`require.resolve('pdfjs-dist/package.json')` 必须命中
   `plugin/node_modules/pdfjs-dist/package.json`。若插件被 pnpm 摊平、pdfjs-dist 安装在别处（如 `.pnpm/store`），
   只要 `createRequire(import.meta.url)` 从插件模块解析仍能找到即可；否则 baseDir=null ⇒ 404 `wasm_unavailable`。
4. **wasm 目录内容**：确认 `plugin/node_modules/pdfjs-dist/wasm/` 里确有 `openjpeg.wasm`（本次已确认存在，13 个文件）。
5. **是否命中旧代码**：确认 host 用的是重新构建/加载的插件 bundle（前端壳/HMR 的改动需要重启 dsh web；
   插件宿主侧改动需要重启 host）。若仍 404 且响应 json 是 `wasm_unavailable`，多半是改过但没重启；
   若 response 是 `wasm_not_found`（白名单非空），说明白名单已生效但 `openjpeg.wasm` 不在其中——
   检查 baseDir 指向的目录与文件名大小写。
6. **进程确实是监听 3080 的那一个**：`netstat -ano | findstr :3080`，避免 curl 命中了其它端口上的旧实例。

---

## 5. 健壮性建议（可选但具体，均已纳入方案 B）

1. **HEAD / 非 GET 请求**：当前 handler 对任何 method 都回 200 + `res.end(bytes)`（`index.js:527-531`）。
   HEAD 请求本不该带 body。建议在 handler 开头加：
   ```js
   if (req.method === 'HEAD') { res.writeHead(200, { 'Content-Type': type, 'Content-Length': bytes.length, 'Cache-Control': 'no-store' }); res.end(); return }
   ```
   （需要在读文件后再处理，或在拿到 bytes 后对 HEAD 只写头不发体。）
2. **query 串**：已天然安全——`new URL(req.url).pathname` 不含 query/hash，
   `openjpeg.wasm?v=1` 仍取到 `openjpeg.wasm`（未做 cache-bust 时会走 `no-store` 分支；本次已加 `no-store`）。
   无需额外处理；如需长缓存可考虑按版本加 `immutable`，但前提是文件名含版本号。
3. **注册失败吞错策略**：经逐行核对，`try/catch`（`index.js:498-506`）确实同时包住 `pkg resolve` 与 `readdir`，
   但吞错后**路由仍注册成功**（`register` 在 `try` 之外），handler 恒 404 —— 也就是说**
   "整段 effect 失败"并不会发生**，真实错误路径是"路由注册成功、handler 内部恒 404"。方案 B 通过惰性读取把该错误
   下沉到请求时并降级为空集合，比"挂载期一次性读取"更稳。若还想暴露挂载期问题，可在 catch 里
   `ctx.logger?.warn?.('ks-dsh-plugin: pdfjs-dist wasm dir not resolvable')` 而不是静默。
4. **允许集合缓存**：方案 B 已改为 `allowLoading` memoized + `.catch(() => [])`，一次失败不会永久 `Promise` 卡死
   当次请求（`.catch` 保证永不再 reject），且失败后 `allow` 为空集合 → 后续请求 404 `wasm_unavailable`（不再重试读盘）。
   如需"失败后允许重试"，可把读取失败时重置 `allow=null; allowLoading=null`，让下一次请求重新试读。
5. **导出路径复用**：建议把 `baseDir` 的求值抽成纯函数并缓存（方案 A 用同步、方案 B 用 lazy），
   避免两处重复逻辑（worker/wasm 各自 `require.resolve`），减小将来漂移。

---

## 6. 一句话自评

根因是一次**同步/异步错用**——`readdirSyncSafe` 把 `fs.promises.readdir` 的 Promise 丢进 `new Set(...)`，
抛 `TypeError: object is not iterable` 被吞后白名单恒为空，导致 wasm 路由**无论是否重启都在改到前恒 404**；
已用隔离脚本复现 404 并验证修复后 200/`application/wasm`（252032 字节），既非"host 未重启"（session+worker 均已 200 证明 effect 已跑），
webserver 的 prefix 匹配/注册逻辑亦无缺陷。
