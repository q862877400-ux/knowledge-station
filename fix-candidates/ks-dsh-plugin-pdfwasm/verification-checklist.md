# 重启后一次性验证清单（ks-dsh-plugin pdf.js wasm 修复）

地址（现状）：`http://127.0.0.1:3080`
前提：已合入修复 diff 并**重启 dsh host**（合入/重启由主控执行；本候选不重启）。

```powershell
# 1) 主目标：200 + application/wasm + 体积>0（期望 size_download=252032）
curl.exe -i -s "http://127.0.0.1:3080/ks/assets/pdf-wasm/openjpeg.wasm"

# 2) 白名单内其它 wasm 逐一 200
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/jbig2.wasm"
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/qcms_bg.wasm"
curl.exe -s -o NUL -w "%{http_code} %{content_type} %{size_download}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/quickjs-eval.wasm"

# 3) worker / session 对照（应仍 200，证明未波及）
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "http://127.0.0.1:3080/ks/assets/pdf.worker.min.mjs"
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "http://127.0.0.1:3080/ks/session"

# 4) 安全回归：路径穿越 / 白名单外 / 目录 仍 404；query 串剥掉后仍 200
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/../package.json"   # 404
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/nope.wasm"          # 404
curl.exe -s -o NUL -w "%{http_code}\n" "http://127.0.0.1:3080/ks/assets/pdf-wasm/openjpeg.wasm?x=1" # 200

# 5) 浏览器最终判定：刷新页面 → DevTools Network 看 openjpeg.wasm=200/application-wasm；
#    Console 不再有 "JpxImage#instantiateWasm …openjpeg.wasm" / "OpenJPEG failed to initialize"；
#    含 JPX/JPEG2000 图像的 PDF 页不再空白（行高亮/文本/页码本来正常）。
```

预期：1/2/3/4-query=200，4-穿越与未知=404，浏览器无 JPX 解码错误、JPX 图片页正常。

---

## 若重启后仍 404，按概率逐点排查

- **看 404 响应体**：区分两类——
  (a) 有 JSON 体且 `error.code` 为 `wasm_not_found`/`wasm_unavailable` ⇒ 路由已命中，问题在「白名单为空 / 文件名不匹配 / baseDir 不可解析」→ 检查第 3、4 点；
  (b) **空 body 404** ⇒ 路由未命中（走 fallback）→ 回到「plugin effect 是否执行」。
- **plugin effect 是否执行**：`GET /ks/session` 与 worker 均 200 ⇒ effect 已执行、三条路由（含 wasm prefix）都在表内。若其 404 且日志有 `ctx.webServer 不可用，跳过 …`（`index.js:619`）⇒ webServer 未注入（profile/依赖问题）。
- **pdfjs-dist 可解析**：`require.resolve('pdfjs-dist/package.json')` 须命中 `plugin/node_modules/pdfjs-dist`（pnpm 摊平时也要能从插件模块解析到）。resolv不了 ⇒ baseDir=null ⇒ `wasm_unavailable`。
- **wasm 目录**：确认 `plugin/node_modules/pdfjs-dist/wasm/` 确有 `openjpeg.wasm`（已确认存在，13 文件）。
- **是否旧 bundle**：插件宿主侧改动需重启 host；若仍 `wasm_unavailable` 多半是改了没重启；若变 `wasm_not_found`（白名单非空）说明白名单生效但文件不在，查 baseDir 指向与大小写。
- **是否真的在 3080 上**：`netstat -ano | findstr :3080` 确认没有其它旧实例占端口。
