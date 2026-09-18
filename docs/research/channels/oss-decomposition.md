# 法规/标准获取与监控 · 开源项目**代码级**拆解

- **调研对象**：业主清单里的 8 个具名项目 + 10 条"未核实"条目，共 18 项
- **调研方式**：逐个**打开仓库页面/源码文件**（`gh api` 取仓库元数据与 tree，`raw.githubusercontent.com` 取源码正文），**不 clone**、**不写被调研仓库**
- **访问时间**：2026-09-18（本地 `Get-Date` = 2026-09-18T12:11+08:00）
- **使用的通道**：agent-reach → `dev`(GitHub / gh CLI，已认证用户 `q862877400-ux`) + `web`(直连 raw / Jina 未用到) ；辅助 `web_search`（仅用于定位"未核实"条目的**候选**，其结论一律回到仓库页面复核）
- **我们自己的基线**：本报告所有"可复用点"均以 `src/core/update/channels/` 的**实际代码**为准，不采信口头转述

> ⚠️ **对业主转述的一处更正（已核实）**：你写的 `UDP_CHANNEL_*` 确系手滑。`base.py` 中实际前缀是 **`UPD_CHANNEL_`**（常量）与 **`UPD-1xxx/2xxx/3xxx`**（错误码值）。
> 顺带一个**实测发现**：`base.py` 模块 docstring（第 14-21 行）把 `UPD-1003 rate_limited` 列为渠道层错误码，但文件里**只定义了 1001 / 1002 / 1004 三个常量**——`UPD-1003` 有文档、无常量、全仓无引用。这是一处**文档与实现的空洞**（见文末"最该警惕"）。

---

## 0. 真伪判定总表

| # | 清单名 | 判定 | 落点 |
|---|---|---|---|
| 1 | GBMCP | ✅ 已核实 | `LoyDgIk/GBMCP` |
| 2 | OpenSTD_Spider | ✅ 已核实 | `SocialSisterYi/OpenSTD_Spider` |
| 3 | gb-downloader | ✅ 已核实 | `suwadaimyojin/gb-downloader` |
| 4 | gb688_downloader | ✅ 已核实 | `inntran/gb688_downloader` |
| 5 | gbqw | ✅ 已核实（但**无取数价值**） | `RhettTien/gbqw` |
| 6 | changedetection.io | ✅ 已核实 | `dgtlmoon/changedetection.io` |
| 7 | urlwatch | ✅ 已核实 | `thp/urlwatch` |
| 8 | National Standard Monitor Skill | ⚠️ 页面已打开，**正文取不到** | clawhub.ai（SPA，无公开 API/raw） |
| 9 | Law-Crawler-RPA-RAG-MCP | ✅ 已核实 | `Yuhamixli/Law-Crawler-RPA-RAG-MCP` |
| 10 | legal-database | ❌ 查无此物（同名一堆，无权威那一个） | — |
| 11 | china-law-search | ❌ 查无此物 | — |
| 12 | policy-monitor | ❌ 查无此物 | — |
| 13 | GovPing | ⚠️ 半真：**npm 包存在，源码仓 404** | `npm:govping-mcp-server` |
| 14 | RegRadar | ⚠️ 多义：至少 6 个同名仓，无唯一权威 | — |
| 15 | regwatch-eu | ✅ 已核实 | `scka-de/regwatch-eu` |
| 16 | @sanmis/crawler | ⚠️ 半真：**npm 包存在，源码仓 404** | `npm:@sanmis/crawler` |
| 17 | at-ris-mcp | ✅ 已核实 | `paragraflabs/at-ris-mcp` |
| 18 | standards-version-check | ✅ 已核实（是 Skill，**但带真代码**） | `cuipointer/ageis` |

### 判定为"查无此物"的四条：我搜过的关键词（可复现）

```bash
gh api "search/repositories?q=<name>+in:name&per_page=5"     # 精确名搜索
gh search repos "<name>" --limit 8
```
- `china-law-search` → `in:name` **0 命中**。模糊搜索只返回**不同名**的近似物：`abcddcbaxxxx/chinese-law-mcp`、`changpx/Lawdown`、`malnlda/legal-research`、`junpe2022/ChineseLawsSearch`。**没有一个叫 china-law-search**。
- `policy-monitor` → `in:name` 仅返回**语义无关**的 `azure.policy.monitor`(Bicep)、`ads-policy-monitor`、`Windows-GroupPolicy-Monitor`（全是 IT/IAM 策略监控，与法规无关）。web_search 命中的是 `S1998raghu/policy-alert-system`、`ONS-Innovation/github-policy-dashboard` —— 同样不叫这个名字。
- `legal-database` → 同名仓 5+（`sublatesublate-design/`、`Wilson-wour/`、`Alxrosen/`、`RLAN4/`、`chiragalwani-EFI/`），**全是无关的通用法律案件库/APM 库**，星标 0-5，无可指认的"那一个"。
- `standards-version-check`（作为 **GitHub 仓库**）→ `in:name` **0 命中**；但它以 **Agent Skill** 形式真实存在（见 §18）。

> 结论：这四条**不是"打不开"，是"名字不对或压根不存在"**。建议业主核回原始出处链接。

---

## 1. GBMCP

- **仓库/页面**：https://github.com/LoyDgIk/GBMCP （访问时间: 2026-09-18）· Python · **许可证：GitHub API 报 `null`（根目录无 `LICENSE` 文件），但 `pyproject.toml` 声明 `license = "MIT"`** · 最近提交 **2026-06-05T14:00:19Z**（与创建时间 `2026-06-05T12:17:35Z` **同日**——一次性发布，此后无更新）· ★1 · 129 KB
- **数据源**（代码里真正请求的端点；这是本次调研**信息密度最高**的一个）：

  | 源文件 | 基础 URL | 真实端点 / 参数 |
  |---|---|---|
  | `sources/openstd.py` | `https://openstd.samr.gov.cn/bzgk/std/` | `GET std_list`：`r=random.random()`, `page`, `pageSize`, `p.p1=0`, `p.p2=<kw>`, `p.p5=<状态>`, `p.p6/p.p7/p.p90/p.p91=""`；`GET newGbInfo?hcno=<id>` |
  | `sources/samr_std.py` | `https://std.samr.gov.cn` | `GET /gb/search/gbAdvancedSearchPage`（**JSON**）、`GET /gb/search/gbDetailed?id=`、`GET /search?q=&tid=&page=&pageSize=` |
  | `sources/gsm.py` | `https://std.samr.gov.cn` | `GET /gsm/search/gsmPage`（**JSON**，`searchText/level/pageNumber/pageSize/state`）、`GET /gsm/search/gsmDetailed?id=` |
  | `sources/org.py` | `https://std.samr.gov.cn` | `GET /org/search/orgCommiteeInfoPage`（**JSON**）、`GET /search/orgDetailView?data_id=` |
  | `sources/ttbz.py` | `https://www.ttbz.org.cn` | `POST /cms-proxy/ms/portal/standardInfo/getPortalStandardList`、`.../getPortalStandardById`、`POST /cms-proxy/ms/bus/organList/portal/queryOrgan`、`.../load` |
  | `sources/foodmate.py` | `https://law.foodmate.net` / `https://down.foodmate.net` | `GET /rule/search.php`（`kw,fields,yxxzt,catid,order,page,fromtime,totime,sfromtime,stotime`）；`GET /standard/search.php`（`kw,fields,corpstandard,bzstatus,catid,...`）；下载 `/standard/down.php`、预览 `/standard/yulan.php` |
  | `sources/doc88.py` | `https://www.doc88.com` | 搜索 `GET /tag/<quote(q)>`；详情 `GET /p-<p_code>.html` |
  | 另有 | — | `sources/{cfsa,mee,mem,nhc,resmea,itu,foreign,international,catalog}.py` |

- **抓取方式**：`httpx.AsyncClient`（**没有** Selenium/Playwright）；OCR 走本地 `ddddocr`（`ocr/base.py`）；`_open_show_gb()` 始终带 `Referer: .../newGbInfo?hcno=<id>`；请求超时 **30s** 可配。
  - **验证码三步**（`downloaders/gb.py::_solve_captcha`）：`GET gc` → OCR → `POST verifyCode`（`data={"verifyCode":..,"agreeIECTips":"true"}`），判据是 `verify.text.strip() == "success"`；**重试 `captcha_retries` 次**后才抛 `CaptchaError`。
  - **OCR 是可插拔的**，且留了**外部命令钩子**：环境变量 `GBMCP_OCR_COMMAND`，命令行里的 `{image}` 会被替换成临时 PNG 路径（`ocr/base.py::_recognize_with_command`，`subprocess.run(..., timeout=20)`）。默认走本地 ddddocr。
- **清洗方式**：`BeautifulSoup(html, "html.parser")` + 选择器；**关键容错设计是"同一份页面同时支持 JSON 与 SSR 兜底"**——`ttbz.py` 先打 JSON 接口，失败则 `parse_detail_json(html, "portal-standard-detail-json")` 从 `<script id=...>` 里 `json.loads(unescape(node.string))` 抠内嵌 JSON。价格/标准号抽取用正则 `\[\s*(\d+)\s*条`、`约\s*(\d+)\s*个`。字段映射统一走 `_extract_key_values()`（遍历 `<tr>` 按 `td/th` 两两配对）+ `_extract_labeled_values()`（在整页纯文本里按标签位置切）双保险。
  - **编码**：`foodmate.py::response_text()` 对 `down.foodmate.net` 强制 `resp.content.decode("gb18030", errors="replace")`。
- **输出形态**：MCP 工具（`server.py` 41 KB，工具名如 `openstd_search_gb_downloadable` / `download_standard` / `batch_download_documents`）；下载文件命名 `safe_filename(f"{标准号} {中文名}") + ".pdf"`；`StdMeta` 用 `dataclasses_json` 序列化；配置落 `.gbmcp.json`。附带 `skills/gbmcp-standards/SKILL.md`（**这是提示词，不是代码**，只讲工具选型与下载边界）。
- **官方接口技巧**（本项目最值钱的部分）：
  1. **`viewGb?hcno=` 直出真 PDF，但要用 `%PDF-` magic 验收**：`_download_direct()` 同时查 `Content-Type` 含 `pdf` **或** `Content-Disposition` 以 `.pdf` 结尾，落盘后再 `path.read_bytes()[:5] != b"%PDF-"` 复核，**不是 PDF 就 `unlink` 并报错**。
  2. **片块预览图重组（CSS 精灵图还原）**：`showGb?type=online&hcno=<id>&request_locale=zh` 返回的 HTML 里，每页是 `div.page[bg]`，`bg` = 一张精灵图的资源名，页内每个 `span.pdfImg-<col>-<row>` 的 `style="background-position:-Xpx -Ypx"` 指出该块在精灵图里的**源坐标**。于是**按 10×10 网格切图再按 (col,row) 贴回**：

     ```python
     # downloaders/gb.py::_render_tiled_preview_page
     source_tile_width  = max(1, bg_image.width // 10)
     source_tile_height = max(1, round(source_tile_width * page.height / page.width))
     left, top     = round(page.width  * tile.col / 10), round(page.height  * tile.row / 10)
     right, bottom = round(page.width  * (tile.col+1) / 10), round(page.height * (tile.row+1) / 10)
     crop = bg_image.crop((tile.source_x, tile.source_y,
                           min(tile.source_x + source_tile_width,  bg_image.width),
                           min(tile.source_y + source_tile_height, bg_image.height)))
     rendered.paste(crop.resize((right-left, bottom-top)), (left, top))
     ```
     注意它比同类更严谨的三点：`pdfImg-(\d)-(\d)` 是**单数字**捕获（说明作者实测过网格只有 0-9）；**源块高度由宽高比推算**而不是硬编码 `/10`；源坐标用 `abs()` 归一化负偏移。
  3. **取预览图的隐藏要求**：`viewGbImg?fileName=<bg>` 必须同时带 `Referer` + **`Cache-Alive: chunked`**（`_get_preview_image_response`），否则拿不到字节。
  4. **同 host 多集合的 JSON 直连**：`std.samr.gov.cn` 的 `/gsm/search/gsmPage`、`/org/search/orgCommiteeInfoPage`、`/gb/search/gbAdvancedSearchPage` 都是**直接吐 JSON** 的 `pageNumber/pageSize` 分页接口——不用解析 HTML。
  5. **PDF 合成不依赖 reportlab**：直接 `PIL.Image.save(path, "PDF", save_all=True, append_images=rest, resolution=100.0)`。
- **可复用点**：
  - **`official_gb.py` 目前只探状态、不取文档**。GBMCP 的 `downloaders/gb.py` 正是我们缺的"状态→获取全文"那一环，且它的**三重验收**（Content-Type / Content-Disposition / `%PDF-` magic）可以直接搬进 `base.py` 作为 `fetch_bytes` 的通用后置校验——我们已经有 `fetch_page()` 暴露了 headers+raw bytes，正好够用。
  - 它的**"JSON 优先、SSR 内嵌 JSON 兜底"**模式，可直接套到 `ttzb.py`：我们现在只打 `cms-proxy` 一个接口（见 `ttzb.py:59`），GBMCP 多了一条 `<script id="portal-standard-detail-json">` 的离线兜底。
  - `parse_openstd_id()` 的正则 `([0-9A-F]{32})` 与我们的 hcno 处理同构，可对齐。
- **坑**：
  - **许可最麻烦**：根目录**没有 LICENSE 文件**，只有 `pyproject.toml` 里一行 `license = "MIT"`。**法律上不可直接抄代码**，只能抄思路，且需业主确认授权。
  - **一次性项目**：创建与最后提交同一天（2026-06-05），此后 3.5 个月零提交，★1。别指望上游修 bug。
  - **与我们的重叠面很大**：`openstd.py`↔我们的 `official_gb.py`（同为 `/bzgk/std/std_list`，参数**逐字相同**）；`ttbz.py`↔我们的 `ttbz.py`（同 `cms-proxy` 路径）；`mee.py`↔我们的 `mee.py`。**它是重叠，不是补充**——唯一真正的增量是"下载"。
  - 验证码依赖 `ddddocr`（本地 OCR，非打码平台），但**它把成功率交给重试次数**，无降级路径。
- **判定**：✅ 已核实

---

## 2. OpenSTD_Spider

- **仓库/页面**：https://github.com/SocialSisterYi/OpenSTD_Spider （访问时间: 2026-09-18）· Python · **GPL-3.0** · 最近提交 **2026-03-18T13:52:43Z** · ★98 · 103 KB（含 54 KB `pdm.lock`）
- **数据源**（`openstd_spider/request.py`，两个 DTO 各管一个站）：
  - `OpenstdDto`，base `https://openstd.samr.gov.cn/bzgk/gb/`
    - `GET /newGbInfo?hcno=<32位hex>`
    - `GET /std_list`：`r=random.random()`, `page`, `pageSize`, `p.p1=<类型>`, `p.p2=<关键字>`, `p.p5=<状态>`, `p.p6=<分类>`, `p.p7=<日期>`, `p.p90=<排序字段>`, `p.p91=<排序方向>`
  - `Gb688Dto`，base **`http://c.gb688.cn/bzgk/gb/`（注意是明文 HTTP）**
    - `GET /showGb?type=online&hcno=<id>`（带 `Referer: https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=<id>`）
    - `GET /viewGbImg?fileName=<img_id>`（带 `Cache-Alive: chunked`）
    - `GET /viewGb?hcno=<id>`（流式，真 PDF）
    - `GET /gc?_{毫秒时间戳}`（验证码图）、`POST /verifyCode`（`verifyCode`, `agreeIECTips=true`）
- **抓取方式**：`httpx.AsyncClient` + `aiofiles` 流式落盘（`aiter_bytes(1024*100)`）；**`follow_redirects=False`** 写在 `AsyncClient` 构造里（只有取图那次单独 `follow_redirects=True`）；UA 伪装成 **Edge 133**；下载进度回调 `cb(total, size)`。
  - 验证码：`ddddocr` + OpenCV 预处理（**本地 OCR，不是打码平台**）：
    ```python
    # openstd_spider/captcha.py
    img = cv2.imdecode(..., cv2.IMREAD_GRAYSCALE)
    _, img = cv2.threshold(img, 190, 255, cv2.THRESH_BINARY)
    img = cv2.bitwise_not(img)
    code = ocr.classification(cv2.imencode(".png", img)[1].tobytes())
    ```
  - **没有代理池、没有并发池、没有重试装饰器**——最朴素的串行版本。
- **清洗方式**：`BeautifulSoup(html, "lxml")`，选择器写得**极其具体**（可直接抄）：
  - 元数据：`div.bor2` → `table.tdlist`、`table.mk1 tr td h1`；发布日期/实施日期靠 `find(string=lambda x: "发布日期" in x).find_next().string`
  - 搜索行：`table.result_list>tbody:nth-of-type(2)>tr`，各列 `td:nth-of-type(N)`；**`hcno` 从 `onclick` 属性里切**：`row.select_one("td:nth-of-type(2)>a")["onclick"][10:-3]`
  - **分页终结判据**：`div.hidden-xs>table>tr>td:nth-of-type(1)>span` 的 `.strings` 列表，**按下标取值** `[8]=total_item`、`[11]=page`、`[12][3:]=total_page`（`[12]` 形如 `共N页`）
  - **未收录的判定**：标准号串以 `您所查询的标准系统尚未收录` 开头 → 抛 `NotFoundError`（比看 HTTP 状态可靠得多）
  - 状态词表（`utils.py`）：`现行/即将实施/废止/暂不实施` → `PUBLISHED/TOBEIMP/WITHDRAWN/NOTIMP`；类型 `GB=1/GBT=2/GBZ=3`
- **输出形态**：`dataclasses_json` 序列化的 `StdMetaFull` / `StdSearchResult`（`-j/--json` 直接吐 JSON）；PDF 文件名 `meta.std_code.replace("/", "") + ".pdf"`（即 `GBT3608-2008.pdf`）；中间产物 `P_<页号>.png`。
- **官方接口技巧**：
  1. **精灵图分块重组**（与 GBMCP 同源但更早、更简洁）：`parse/gb688.py::gb688_parse_page_sheet` 从 `span[class^="pdfImg"]` 的 class 名切 `(x,y)`、从 `background-position` 正则切源坐标；`gb688_reorganize_page` 用 `block_h = page.h // 10`、`block_w = page.w // 10` 切块回贴。**额外多一个透明通道处理** —— `image_paste_white()` 把带 alpha 的精灵图先合成白底再贴，避免透明块变黑：
     ```python
     alpha = img[:, :, 3].astype(float) / 255.0
     composite = (img[:, :, :3] * alpha[..., None] + bg * (1 - alpha[..., None])).astype(np.uint8)
     ```
  2. **同一 `img_id` 被多页复用**：`gb688_uniq_imgid()` 先 `set()` 去重再下载，**下载张数 << 页数**（这是"别重复请求同一资源"的正解）。
  3. **两级降级**：`download` 命令先看 `meta.allow_download`（`button.xz_btn` 存在）→ 走 `viewGb` 直下；否则看 `meta.allow_preview`（`button.ck_btn` 存在）→ 走精灵图重组。`--preview` 可强制走重组路线。
  4. **PDF 由图片重排生成**（`pdf.py`）：`reportlab` 的 `Canvas(A4)` + `drawImage(..., preserveAspectRatio=True)`，且**按 `min(page_w/img_w, page_h/img_h)` 等比缩放居中**，不留畸变。
- **可复用点**：
  - **`official_gb.py` 的分页终止条件可以直接换成它的 `total_page` 解析**——比"空页就停"更确定，也符合我们 `base.py` 强调的"确定性"。
  - **"未收录"文本判据** `您所查询的标准系统尚未收录` 是一个**比 404 更可靠的 not_found 信号**，建议进 `official_gb` 的 not_found 分支。
  - 它的 `follow_redirects=False` 默认值 + 仅在取图时开启，与我们 `base.py` 的 `allow_redirects` 设计**同源**——可作为我们"默认不跟随"的另一处佐证。
  - 状态词表里的 **`暂不实施`（NOTIMP）** 是我们 `STATE_TEXT_MAP`（只有 现行/即将实施/被代替/废止）**缺的第 5 态**。
- **坑**：
  - **GPL-3.0 强 copyleft**：抄进我们仓库会让整个分发受 GPL 传染。**只能读思路、不能抄代码**，除非业主接受 GPL。
  - base URL 是 **`http://`（明文）**，中间人可篡改；走我们自己的 `curl_cffi` transport 时应升级并注意它会如何重定向。
  - `c.gb688.cn` 与 `openstd.samr.gov.cn` **是两个不同的域**，我们在 `official_gb.py` 里只用了后者——**GB 的文档内容其实在 gb688**，这是域名层的知识缺口。
  - 无重试/无退避/无代理：被封就是硬失败。
- **判定**：✅ 已核实

---

## 3. gb-downloader

- **仓库/页面**：https://github.com/suwadaimyojin/gb-downloader （访问时间: 2026-09-18）· Python · **MIT** · 最近提交 **2025-04-25T08:46:32Z**（与创建同日，**单文件一次性脚本，已停更 ~17 个月**）· ★8 · **8 KB（整整 3 个文件：main.py / README.md / LICENSE）**
- **数据源**（`main.py`，全部硬编码）：
  - base `http://c.gb688.cn/bzgk/gb/`
  - `GET showGb?type=download&hcno=<硬编码 F60B16F6F204597DDAFD8CCCFC931E11>` ← **为拿 `Set-Cookie: JSESSIONID=`**
  - `GET gc` → 验证码图；`POST verifyCode`（`{verifyCode}`，**没带 `agreeIECTips`**）
  - `GET showGb?type=online&hcno=<目标>` → 文档 HTML
  - `GET viewGbImg?fileName=<bg>` → **302 到真实图片 URL**
- **抓取方式**：`requests.Session()`；`ddddocr`（本地 OCR，`DdddOcr()` 无参数，**也没做 OpenCV 预处理**——比 OpenSTD_Spider 弱）；验证码**失败重试 3 次**；
  - 手工处理 302：`allow_redirects=False` → 读 `response.headers["Location"]` → 拼绝对 URL 再下一次请求；
  - 请求头里留着 `Proxy-Connection: keep-alive`（**从某个代理环境抄来的残留**），`Host` 硬编码 `c.gb688.cn`。
- **清洗方式**：`BeautifulSoup(html, "html.parser")`；从 `div.page[bg]` 取 bg、从 `style` 正则取 `width/height`（**取不到就回退硬编码 2315×3274**）；从 `span` 的 class `pdfImg-(\d+)-(\d+)` 与 `style` 的 `background-position:\s*(-?\d+)px\s+(-?\d+)px` 取网格位与源偏移。标准号从 `<title>` 正则 `([A-Z]+/[A-Z]+\s+\d+-\d+|[A-Z]+\s+\d+-\d+)` 抠。
- **输出形态**：中间 PNG 到 `gb_standard_images/`（`unique_bg_<i>.png`、`reconstructed_page_<i>.png`）；最终 **`<标准号去斜杠去空格>.pdf`**，用 `img2pdf.convert()` 合成。
- **官方接口技巧**：
  1. **`viewGbImg` 是 302 跳转**，且**跳转目标不必带 cookie 也能下**——它显式走 `allow_redirects=False` 抓 `Location`，再给第二个请求补上 `Cache-Alive: chunked`。**这条比 OpenSTD_Spider 的"直接 follow_redirects=True"更能说明 gb688 的防盗链机制包含一次跳转**。
  2. **JSESSIONID 是独立前置步骤**：先用一次 `showGb?type=download` 从 `Set-Cookie` 里正则 `JSESSIONID=([^;]+)`，再写回 headers。**说明 gb688 的验证码校验绑定 session**。
  3. 精灵图 10×10 重组逻辑与 OpenSTD_Spider 等价，但用 `PIL` 而非 `numpy`：
     `dest_x = int(grid_x * (page_width / 10))`，`sprite.crop((sx, sy, sx + page_width//10, sy + page_height//10))`。
- **可复用点**：**唯一增量是"302 探测 + `Cache-Alive` 补头"这一对组合**，可作为我们 `base.py` 的 `fetch_bytes` 在 gb688 场景下的参数模板（`allow_redirects=False` 先探，再带 `Cache-Alive` 取）。其余全部被 OpenSTD_Spider 覆盖且更差。
- **坑**：
  - **它是 OpenSTD_Spider 的粗糙复刻**：同样是精灵图 10×10，但**源块尺寸硬编码为页面尺寸的 1/10**（OpenSTD_Spider 也是，但 GBMCP 改成了按宽高比推算），且网格位是 `\d+` 而非单数字——**遇到源精灵图不是正 10×10 时它会错位**。
  - **硬编码残留**：`get_jsessionid()` 里那个固定的 `F60B16F6F204597DDAFD8CCCFC931E11` 与**用户实际要下的标准无关**，纯属从抓包会话里漏下来的常量。
  - README 自称"只要是能预览就能下载"，但同时写"**仅用于学习和个人研究目的 / 请勿用于商业用途**"。
  - ★8、17 个月无提交、3 个文件——**不要指望维护**。
- **判定**：✅ 已核实

---

## 4. gb688_downloader

- **仓库/页面**：https://github.com/inntran/gb688_downloader （访问时间: 2026-09-18）· **GitHub 报 `language: null`** · **Apache-2.0** · 最近提交 **2020-06-18T09:05:19Z** —— ⚠️ **已停更 6 年 3 个月**（更怪的是 `created_at` = 2020-07-20，**晚于最后提交**，说明仓库是后来转移/重建的）· ★0 · 64 KB
- **数据源**：
  - `standard/GB.py`：`openstd.samr.gov.cn/bzgk/gb/std_list`、`.../newGbInfo?hcno=`、**`c.gb688.cn/bzgk/gb/viewGb?type=online&hcno=<hcno>`**
  - `standard/HDB.py`：`http://hbba.sacinfo.org.cn/stdQueryList`（POST）与 `http://dbba.sacinfo.org.cn/stdQueryList`（POST），参数
    `{current, size, key, status, ministry, industry, pubdate, date}`
  - `standard/HDB.py` 下载：`GET http://{hbba|dbba}.sacinfo.org.cn/attachment/downloadStdFile?pk=<pk>`
- **抓取方式**：`requests`（**全同步、无 session 复用**）；**没有验证码、没有 OCR、没有代理、没有重试**——因为这条路径**根本不需要验证码**。UA 伪装成 **iPad Safari 11**（这是关键）。
- **清洗方式**：
  - GB：`re.findall(r'<span class="badge">(\d+)</span>')` 取总数；`re.findall(r"<tr>([\s\S]*?)</tr>", text.replace('\r\n','').replace('\t',''))` 切行，再 `re.findall(r"<td([\s\S]*?)</td>", item)` 切列，**取 `items[5:-2]` 避开表头/表尾**；`hcno` 从 `showInfo\('(.+?)'\);` 抠；状态用 `re.findall('[\u4e00-\u9fa5]{2,4}', data[5])[0]` ← **用"连续 2-4 个汉字"猜状态**（脆弱）。
  - 日期：`datetime.fromisoformat(data[6][:-2].replace(">", ''))` ← **靠切掉尾部 2 个字符**。
  - 分页：`pages = 1 if total_size == size else (total_size // size + 1)`。
  - 文件名过滤：`BAN_LIST = ['\\','/',':','*','?','"','<','>','|']` 逐字符剔除。
- **输出形态**：`{标准号}({中文名}).pdf`（如 `GB 18218-2018(危险化学品重大危险源辨识).pdf`）；`format_search_api()` 另外产出**给前端用的扁平 JSON**：`{status, key(hcno/pk), name, standard_no, act_date(毫秒时间戳)}` ← **这个字段映射很值得抄**。
- **官方接口技巧（本项目最大的发现）**：

  **`viewGb?type=online&hcno=<id>` 会返回 base64 文本，分 10 段，拼起来直接就是完整 PDF——不需要验证码、不需要精灵图、不需要 OCR。**
  ```python
  # standard/GB.py::GBCore.get_bytes —— 注释原文：
  #   "这部分代码可以在对 http://openstd.samr.gov.cn/bzgk/gb/index 网站的手机版预览模式下抓包获得"

  headers = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 '
                            '(KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1'}
  text = ""
  for i in range(0, 10):
      if i == 0:
          url = f"http://c.gb688.cn/bzgk/gb/viewGb?type=online&hcno={hcno}"
      else:
          url = f"http://c.gb688.cn/bzgk/gb/viewGb?type=online&hcno={hcno}.00{i}"
      time.sleep(1)                      # ← 每段之间 sleep 1s，节流
      text += requests.get(url, headers=headers).text
  pdf_bytes = base64.standard_b64decode(text)   # ← 10 段 base64 拼接后整体解码
  ```
  三个要点：
  1. **分片约定**：第 1 段用裸 `hcno`，第 2-10 段用 `hcno + ".001"` ... `hcno + ".009"`。
  2. **必须伪装 iPad/移动端 UA**，才拿到"手机版预览模式"的 base64 通道（桌面 UA 走精灵图）。
  3. **base64 是跨段连续编码的**——必须先拼字符串**再** `b64decode`，逐段解码会失败。
  4. 段间 `time.sleep(1)` 是**作者自觉的节流**。

  另外 `can_download()` **用页面上有没有"在线预览"四个字**来判断能否下载（`if "在线预览" in r.text`）——比解析按钮可靠。
- **可复用点**：
  - **这条 base64 通道若在 2026 年仍有效，是我们 `official_gb.py` 性价比最高的一次升级**：一次性把"探测状态"扩展到"拿到全文"，且**完全绕开验证码/精灵图/OCR 三条重链路**。⚠️ 但它是 **2020 年的实测**，**必须先由业主用一次真实请求验证再落地**（本报告不代为断言其仍然有效）。
  - `HDB` 的 `hbba/dbba.sacinfo.org.cn` **正是我们 `hbba.py`/`dbba.py` 已经在用的 host**——但我们的适配器**只探状态**，而它给出了**下载直链** `GET /attachment/downloadStdFile?pk=<pk>`（`pk` 就是 `/stdQueryList` 返回行里的 `pk`）。这是**零新域名成本**的增量。
  - `format_search_api()` 的 `{status, key, name, standard_no, act_date}` 映射与我们 `ChannelResult` 的 `legal_status/latest_version/effective_date` 高度同构，可作字段对齐参考。
  - `HDB._search` 的 `pubdate` 参数支持 `''/-1/-3/-6/-12/-24`（月数）——**一个天然的"增量拉取"窗口**，可用于我们的公告扫描做增量而非全量。
  - HDB 的状态词表含 **`有更新版`** —— 又一处我们 4 态枚举之外的值。
- **坑**：
  - **6 年未更新**，`requests` + 正则解析 HTML 的写法在站点改版后必然失效；且**未经我实测**，不能当作可用接口。
  - `_search` 里 `p.p1: 0` 与 `sort_name='circulation_date'` 说明它知道排序字段，但**没有做成参数暴露**。
  - 状态靠"2-4 个汉字"正则猜，**遇到 `暂不实施`（4 字）与 `即将实施`（4 字）都可能误取**。
  - `language: null` + ★0 + created > pushed，仓库状态本身可疑。
- **判定**：✅ 已核实

---

## 5. gbqw

- **仓库/页面**：https://github.com/RhettTien/gbqw （访问时间: 2026-09-18）· **Java（Android）** · **MIT** · 最近提交 **2025-07-18T14:26:58Z** · ★0 · 1.16 MB
- **数据源**：**没有。** 没有 `OkHttp`/`HttpURLConnection`/任何 HTTP 客户端调用。
  - `HomeFragment.java` 从一个 **`SharedPreferences` 里可用户自定义的 URL**（默认值来自 `R.string.default_web_url`）加载到一个 `WebView`；
  - `DashboardFragment.java` 再加载同一个 URL；
  - 唯一"数据"是 **SQLite 收藏夹**（`db/DatabaseHelper.java`、`FavoriteDao`）。
- **抓取方式**：**`WebView` 人肉浏览**。全部"技术"是：
  - `settings.setUserAgentString("Mozilla/5.0 ... Chrome/120.0.0.0 ...")` 伪装桌面 UA；
  - `shouldOverrideUrlLoading` 里，如果 URL 以用户配置的 `default_jump_url` 开头，就 `navigate(R.id.navigation_dashboard, bundle)` 跳转到查看页；
  - `onReceivedTitle` 回调里用正则 `GB/?T?\s*\d+(\.\d+)?-?\d*` **从网页标题抽标准号**；标题拿不到时用 `evaluateJavascript("(function(){return document.title;})();")` 兜底。
- **清洗方式**：一条正则从 title 抽标准号。仅此。
- **输出形态**：Android SQLite 收藏表（title / standardNo / url）。无导出、无 JSON。
- **官方接口技巧**：**无。** 它是浏览器，不是爬虫。
- **可复用点**：**几乎没有。** 唯一可迁移的是那句"**标题里就带标准号，且格式是 `GB/T xxxxx-YYYY`**"的经验——可作我们 `web_fallback.py` 从搜索结果页抽标准号时的一个补充正则。
- **坑**：
  - **README 作者自己就说了**："其实，使用浏览器和收藏夹，效果也是一样的 QAQ"——**项目自认无价值**。
  - 关于页写明 "Powered by Claude"、README 写明 "完全使用 Cursor 辅助" —— 是 AI 生成的小玩具。
  - `static WebView` 静态持有 + 手动 `removeView` 的写法有内存泄漏风险（与取数无关，但说明工程质量）。
  - **★0，与"法规/标准获取"主题实质无关**——建议从清单中剔除。
- **判定**：✅ 已核实（**但结论是：不具取数价值**）

---

## 6. changedetection.io

- **仓库/页面**：https://github.com/dgtlmoon/changedetection.io （访问时间: 2026-09-18）· Python · **Apache-2.0** · 最近提交 **2026-09-18T00:24:54Z**（**就是今天，极度活跃**）· ★34312 · 46 MB
- **数据源**：任意用户配置 URL（无内置数据源）。抓取层是插件式：`content_fetchers/{requests,playwright,puppeteer,webdriver_selenium}.py`，另有 `screenshot_handler.py`。
- **抓取方式**（`content_fetchers/requests.py`，本报告**最值得逐行读**的文件）：
  1. **重试只在网络层，不在 HTTP 状态层**：
     ```python
     max_retries = int(os.getenv("REQUESTS_RETRY_MAX_COUNT", "6"))
     retry_strategy = Retry(total=max_retries, connect=max_retries, read=max_retries,
                            status=0,             # ← 明确不重试 HTTP 状态码
                            backoff_factor=0.5,   # 0.3s/0.6s/1.2s...
                            allowed_methods=["HEAD","GET","OPTIONS","POST"], raise_on_status=False)
     ```
  2. **重定向逐跳手工跟随 + 逐跳 SSRF 复检**（这正是我们 `base.py` 注释里担心的那条路）：
     ```python
     r = session.request(..., allow_redirects=False)
     for _ in range(10):
         if not r.is_redirect: break
         redirect_url = urljoin(current_url, r.headers.get('Location',''))
         if is_url_private_or_parser_confused(redirect_url):     # ← 每一跳都验
             raise Exception(f"Redirect blocked: ...")
         r = session.request('GET', redirect_url, ..., allow_redirects=False)
     else:
         raise Exception("Too many redirects")
     ```
  3. **编码嗅探按 WHATWG 优先级**：HTTP `charset` → **BOM** → **前 2KB 的 `<meta charset>`** → 最后才 `chardet`；XML/RSS 另外优先读 `<?xml ... encoding="...">`（注释说 chardet 会把 UTF-8 误判成 MacRoman）。
  4. `verify=False`（关闭 TLS 校验）；`is_binary` 时不跑编码嗅探（PDF 太慢）。
- **清洗方式**（`html_tools.py`，43 KB，工具极其齐全）：
  - **`include_filters` / `subtractive_css_selector` / `subtractive_xpath_selector` / `element_removal`**：正选与**负选**（`xpath:`、`xpath1:` 前缀或纯 CSS），负选**在比较前把元素摘掉**；
  - **`strip_ignore_text(content, wordlist, mode)`**：忽略易变文本，支持 **Perl 风格 `/regex/flags`**，并区分**单行正则**与**跨行正则**（`ignore_regex_multiline`）——用于整块屏蔽时间戳/浏览量；
  - `xpath_filter` 用 lxml 且 **`XMLParser(resolve_entities=False, no_network=True)`**（XXE 加固）；`get_safe_xpath3_parser()` 专门防 **XPath 3.0 读本地文件/环境变量**；
  - **`workarounds_for_obfuscations(content)`**：专门对付站点故意混淆（零宽字符之类）；
  - HTML→文本用 **`inscriptis`**（注释明确说正则剥标签不安全，会吞掉真实内容）；
  - `extract_json_blob_from_html(..., ensure_is_ldjson_info_type, json_filter)`：把页面里的 JSON-LD 抠出来再用 jq 过滤。
  - 另有 **`processors/restock_diff/pure_python_extractor.py`**：用标准库 `html.parser` 手写三个 `HTMLParser` 子类抓 **JSON-LD / OpenGraph / microdata**，再用 `jsonpath_ng` 的 `$..(price|Price)` **在整棵结构里任意位置找字段**（注释："covers 80%+ of modern sites"）；`lxml` 有内存泄漏所以刻意避开了 C 层解析。
- **输出形态**：`datastore` JSON（含每 watch 的历史快照），快照目录；`diff/` 做行diff/词diff/HTML diff；`processors/text_json_diff` / `restock_diff` / `image_ssim_diff`（**图像 SSIM 比较**，用 libvips 或 OpenCV）；`api/` 提供 REST；`blueprint/rss/` 导出 RSS。
- **官方接口技巧**：
  1. **二进制内容用 md5 当"内容"**：`self.content = hashlib.md5(r.content).hexdigest()`——文件型资源（PDF）不做文本 diff，直接用哈希判变更。
  2. **`etag` / `NotModifiedError`** 走条件请求，未变则完全跳过比对。
  3. **变更幅度阈值触发**（`conditions/plugins/levenshtein_plugin.py`）：用 `rapidfuzz.distance.Indel.normalized_similarity` 算相似度（注释说明**特意用 MIT 的 rapidfuzz 而不是 GPL 的 python-Levenshtein**，以保持依赖无强 copyleft），暴露 `levenshtein_ratio` / `levenshtein_distance` 作为**可编排的条件字段**；并有 `LEVENSHTEIN_MAX_LEN_FOR_EDIT_STATS = 100000` **超长直接跳过**的保护。
  4. **内容被刻意混淆时**有 `workarounds_for_obfuscations()` 兜底。
- **可复用点**（对我们 `base.py` / `web_fallback.py` 直接对口）：
  - **`strip_ignore_text` 的"单行/跨行双正则"模型** → 我们抓 gov 公告页时，"发布日期/浏览量/当前时间"必然抖动，导致 `no_change` 被误判成 `new_version`。这是**直接能抄的设计**。
  - **`element_removal` 的 `xpath:`/`xpath1:` 前缀约定** → 可以做成我们渠道适配器的一个可选 `prune` 配置项。
  - **重定向逐跳复检** → `base.py` 的 `allow_redirects` 注释里已经写明"`is_private_url` 只在发起前判过一次"，changedetection 给出了**每跳都判**的参考实现，补上即可闭环。
  - **编码嗅探顺序（BOM → meta charset → chardet）** → 我们 `fetch_page()` 已经暴露了 `headers` 与 `raw_bytes`，但没有编码决策逻辑；遇到 `gb18030` 站（如 `down.foodmate.net`、我们没覆盖的不少政府站）会乱码。**这条建议直接实现。**
  - **阈值化变更判定**（相似度 >X% 视为 no_change）→ 契合我们 `derive_change_type()` 目前只有"版本号不同= new_version"的粗判。
  - **retry `status=0`** → 与我们 `UPD_CHANNEL_TIMEOUT`(1001) / `UPD_CHANNEL_ERROR`(1004) 的分层一致：**HTTP 非 200 不重试、不抛**，交由降级链决策。这印证了我们 `_miss()` 的设计。
- **坑**：
  - 它解决的是"**页面变了没**"，**不是**"**标准号的新版是哪个**"。它**不认识** `GB/T` 语义、不懂"被代替"关系。**不能替代我们的渠道适配器**，只能**加固传输与预处理层**。
  - `verify=False` 是**有意的安全妥协**（自签站点），抄的时候要评估。
  - 46 MB 仓库、Web/API/UI/多处理器/LLM 集成——**依赖极重**，直接引入不现实，应**只取文件级思路**。
  - `image_ssim_diff` 用 libvips/OpenCV + 可能的子进程隔离，运维成本高。
- **判定**：✅ 已核实

---

## 7. urlwatch

- **仓库/页面**：https://github.com/thp/urlwatch （访问时间: 2026-09-18）· Python · **许可证：GitHub API 报 `NOASSERTION`；我实测 `raw/.../LICENSE` 返回 404**（根目录无 `LICENSE` 文件，授权条款需人工确认）· 最近提交 **2026-07-10T08:56:34Z**（约 2 个月前，**活着**）· ★3128 · 1.3 MB
- **数据源**：任意订阅 URL。Job 三型（`lib/urlwatch/jobs.py`）：**`ShellJob`（跑命令）、`UrlJob`（HTTP）、`BrowserJob`（浏览器自动化）**。
- **抓取方式**：`UrlJob` 带 `CHARSET_RE = re.compile('text/(html|plain); charset=([^;]*)')` 从响应头判编码；支持 **`etag` 条件请求**；`NotModifiedError` 短路；`ignore_connection_errors` / `ssl_no_verify` 可配。无重试装饰器、无并发池（**串行 worker**）。
- **清洗方式（本项目最值得抄的部分——一个 30+ 种的过滤器插件链）**：
  - 每种过滤器是一个 `FilterBase` 子类，带 `__kind__` 标识：`html2text`、`csv2text`、**`pdf2txt`**、`ical2txt`、`json`、`pretty-xml`、**`grep`**、**`grepskip`**(InverseGrep)、`strip`、`striplines`、**`element-by-id` / `element-by-class` / `element-by-style` / `element-by-tag`**、**`sha1`**、`hexdump`、**`css`**、**`xpath`**、`regex`(RegexSub/RegexFindall)、`sort`、**`remove-duplicate-lines`**、`reverse`、**`shellpipe`**、**`ocr`**、**`jq`**、`beautify`、`automatch`、`legacy-hooks`、`keep_lines_containing`
  - `css` / `xpath` 由同一个 `LxmlParser` 实现，`EXPR_NAMES = {'css': 'a CSS selector', 'xpath': 'an XPath expression'}`；
  - **两级过滤链**：`filter:`（作用于**抓回来的内容**）与 `diff_filter:`（作用于**生成的 diff**）——`handler.py::get_diff()` 会遍历 `job.diff_filter` 再滤一次 diff。**这个"先洗内容、再洗差异"的两段式，我们完全没做。**
- **输出形态**：`cache_storage` 快照 + `unified_diff` 文本；Report 有 `new / changed / unchanged / error` 四态；支持发邮件/XMPP/自定义 reporter；`util.py` 提供 `diff_tool` 外挂（如 `git diff --no-index`，**退出码 0=无变化、1=有差异、其他=错误**）。
- **官方接口技巧**：
  1. **`compared_versions`：和 N 个版本之前比，而不是只和上一次比**（`JobState.load()` 里 `get_history_data(guid, self.job.compared_versions)`）。这对**抖动页**是刚需——否则一次瞬时渲染差异就会误报。
  2. **`treat_new_as_changed`**：首次抓到就把 `old_data` 置为 `''`，**强制为"新增"生成 diff**（`handler.py::process()`）。解决了"新加的标准第一次探测不算变更"的经典漏报。
  3. **`sha1` 过滤器**：把整页内容先哈希再比较——**同一页只要有一字节变化就报**，但也**丢弃了"变了什么"**；适合纯监控。
  4. **`remove-duplicate-lines` + `sort`**：对付"列表顺序随机"或"内容相同但重复出现"的页面，**是解决"无序列表页误报"的标准答案**。
  5. **`shellpipe` / `OCRFilter`**：允许把内容管道给任意外部命令（含 OCR），**是"图片型页面/PDF 型页面"的逃生舱**。
- **可复用点**：
  - **"`filter` 洗内容 + `diff_filter` 洗差异"两段式** → 我们目前只有"解析成 `ChannelResult`"，**没有中间归一化层**。加一层"页面快照归一化"能直接压低 `new_version` 误报。
  - **`compared_versions`（和 N 版前比）** → 我们 `derive_change_type()` 是**无状态**的（只看本次请求结果与请求号比较），天然不会抖，但**也永远发现不了"官方把状态从 effective 改回 upcoming 又改回来"**这类来回。若要做趋势，这是参考模型。
  - **`sort` + `remove-duplicate-lines`** → 我们 `govcn_announce.py` / `mem_gov.py` 这类**列表页**扫描，若列表顺序不稳定会产生假变更；这两个过滤器是现成解法。
  - **`diff_tool` 退出码约定（0/1/其他）** → 和我们 `ChannelResult.change_type` 的 `no_change/new_version` 三态语义同构，可借其约定统一。
  - **`etag`/`NotModifiedError`** → 我们没有任何条件请求。对 `openstd` 这类大站，**加 If-None-Match 能显著降载、降风控暴露面**。
- **坑**：
  - **无 `LICENSE` 文件**（GitHub 报 NOASSERTION，raw LICENSE 404）→ **抄代码前必须先查清授权**。
  - **串行、无并发、无重试**：设计目标是"订阅几十个 URL 的个人工具"，不是"高频批量探测"。**架构上比 changedetection.io 弱**，但**代码小得多（1.3 MB vs 46 MB）**，思路更容易整段吸收。
  - 它是**通用网页监控**，同样**不理解标准号语义**——与 changedetection.io 同样的定位局限。
- **判定**：✅ 已核实

---

## 8. National Standard Monitor Skill

- **仓库/页面**：https://clawhub.ai/sereinone/skills/national-standard-monitor-skill/security-audit （访问时间: 2026-09-18）· 平台：ClawHub（Skill 托管站，**非 GitHub**）· 版本 **1.0.0** · 作者 `sereinone`
- **数据源**：**只有一句描述，无代码可读。** 页面 `<meta name="description">` / `og:description` 原文：
  > 「跟踪国家标准（GB/GB/T）更新变化，支持任意 ICS 分类。**从 openstd.samr.gov.cn 获取最新现行标准列表**，自动比对本地已下载标准，发现新增/废止/状态变更，支持批量下载 PDF。」

  即：数据源 = `openstd.samr.gov.cn`（与我们 `official_gb.py` **同一个站**）。
- **抓取方式 / 清洗方式 / 输出形态**：**无法核实**。见下。
- **官方接口技巧**：**无法核实**。
- **可复用点**：从描述能**推断**（但**未被验证**）两点设计意图：
  1. **"按 ICS 分类批量拉'最新现行标准列表'" + "和本地已下载集合做差集"** —— 即 **快照式（snapshot-diff）监控**，而不是我们现在的**按标准号逐个探测（probe-by-number）**。这是**两种根本不同的监控范式**：
     - 我们是 **pull-by-key**：已知标准号 → 问状态。适合"我库里已有 N 个标准，谁过期了"。
     - 它是 **crawl-all-then-diff**：拉全量列表 → 与上次快照比。适合"**发现我根本不知道的新标准**"。
     - **我们的渠道层目前完全不具备第二种能力**——这是一个**真实且重要的能力缺口**。
  2. "支持任意 ICS 分类" ⇒ 它大概用了 `std_list` 的 `p.p6`（分类）参数——**我们 `official_gb.py` 目前没传 `p.p6`/`p.p7`**。
- **坑**：
  1. **页面是纯客户端 SPA，我拿不到正文。** 实测以下路径**全部 404**：
     - `https://clawhub.ai/api/skills/sereinone/national-standard-monitor-skill`
     - `https://clawhub.ai/api/skill/sereinone/national-standard-monitor-skill`
     - `https://clawhub.ai/api/v1/skills/sereinone/national-standard-monitor-skill`
     - `https://clawhub.ai/api/download/sereinone/national-standard-monitor-skill`
     - `https://clawhub.ai/sereinone/national-standard-monitor-skill/raw`
     HTML 里只有 JS bundle 引用（`/assets/*.js`），无 SSR 正文。
  2. **页面上"技能"与"安全审计"是两件事**：我打开的 URL 是 `.../security-audit`，它认证的是**安全性**（是否越权、是否泄露凭据），**不认证功能正确性**，也不保证有可复用代码。
  3. **在没有正文的情况下，我无法判断它是"有代码的 Skill"还是"纯提示词 Skill"。** 参照 §18 的 `standards-version-check`（**有真 Python 工具**）与 §5 的 `gbqw`（**AI 写的玩具**），两种都可能。**不要默认它可用。**
  4. 托管在第三方 Skill 市场，**来源与持续性都不受控**（对比 GitHub 有 commit 历史可审）。★、fork、issue 一概不可见——**无法判断维护状态**。
- **判定**：⚠️ 未核实（页面可访问、功能描述可读；**Skill 正文与代码不可获取**）
- **业主若要推进**：唯一可行路径是**在浏览器里打开该页并人工下载 Skill 包**，或从作者处索取源码。**我这一侧不需要再重试**——SPA 客户端渲染，`web_fetch`/`Invoke-WebRequest` 都只能拿骨架。

---

## 9. Law-Crawler-RPA-RAG-MCP

- **仓库/页面**：https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP （访问时间: 2026-09-18）· Python · **MIT** · 最近提交 **2026-04-28T08:01:33Z**（约 5 个月前）· ★32 · 10.4 MB
- **数据源**：
  - **`config/known_urls.toml` —— 人工策展的"种子直链表"**（这是它的核心数据源策略）：每条 `{name, url, source, aliases=[...]}`，例如
    ```toml
    [[laws]]
    name = "建筑工程设计招标投标管理办法"
    url  = "https://www.gov.cn/gongbao/content/2017/content_5230272.htm"
    source = "中国政府网"
    ```
    `src/crawler/known_urls.py` 用 `tomllib`（`ModuleNotFoundError` 时回退 `toml`）加载，并**把 aliases 一并展平成 name→url 映射**，供精确/模糊匹配。
  - **搜索引擎**（`config/anti_detection.toml[search_engines]`）：`baidu_selenium`(enabled, priority 1)、`bing_selenium`(enabled, priority 2)、`baidu_requests`(**disabled，注释："暂时禁用，反爬严重"**，`https://www.baidu.com/s`)、`duckduckgo`(**disabled，注释："暂时禁用，连接超时"**，`https://html.duckduckgo.com/html/`)。
- **抓取方式**：
  - `httpx.AsyncClient`（`async with` 上下文管理器）+ **`tenacity` 重试**：`@retry(stop=stop_after_attempt(max_retries), wait=wait_exponential(multiplier=retry_delay, max=60))`；
  - **自实现令牌桶限速**（`_rate_limit`）：`if time_since_last < 60/rate_limit: sleep(60/rate_limit - t + random.uniform(0.5, 1.5))` —— **限速 + 随机抖动**；
  - **UA 轮换**：`fake_useragent.UserAgent()` + `random.choice(user_agents)`；
  - **Selenium** 配置里带 `--disable-blink-features=AutomationControlled`（**反自动化检测**）、`window_size_random`、`disable_images=true`（省带宽）、`headless=false`（注释说调试期建议非无头）、`max_instances=2`；
  - **代理池**：`[proxy_pool]` 配置了 `enabled=false`、`rotation_interval=5`（**每 5 个请求轮换**）、`proxies=[]`（**空列表 + 注释示例**，即**未真正启用**）。
- **清洗方式**：`parse_date()` 试 5 种中文/西文日期格式（`%Y-%m-%d`、`%Y年%m月%d日`、`%Y.%m.%d`、`%Y/%m/%d`、`%Y-%m-%d %H:%M:%S`），**全失败则告警返回 None 而不猜**；`extract_law_type()` 用 `law_type_mapping` 做**子串包含**判定（简单粗暴）。
- **输出形态**：`examples/sample_crawl_result.json`；有 `docs/MCP_CLI_DESIGN.md`（MCP/CLI 双入口）、`.cursor/rules/*.mdc`（作者用 Cursor 开发）。
- **官方接口技巧**：
  - **"已知 URL 种子表 + 别名"** 而不是硬编码解析器 —— 把"法规名 → 权威直链"变成**可评审、可社区贡献的数据文件**（`known_urls.py` 注释："Keep this list small, public, and reviewable. Community contributions can add authoritative public URLs without changing Python code."）。**这是数据与代码分离的正面范例。**
  - **主力不是搜索，而是"Selenium 绕反爬 + 直链表兜底"**：注意到它把 `requests` 版的百度/DDG **都关了**，只留 Selenium —— **等于承认"纯 HTTP 打不动中文搜索引擎"**。
- **可复用点**：
  - **"种子 URL 表 + aliases"** 这个模式**非常适合我们**：我们的 `govcn_announce.py`、`mohurd.py`、`mem_gov.py` 等公告页是**按栏目列表抓**的；一旦栏目改版就全挂。把"**已知权威详情页直链**"抽成一份可评审的 TOML/YAML（并带 `aliases` 供标准名模糊匹配），能让**最关键的少数证据链 URL 不依赖列表页解析**。
  - **"限速 + 随机抖动"**：我们 `ndls.py` 已有 `PAUSE_S = 1.0` 的确定性限速（且**只在真实 transport 下 sleep**，mock 不睡，保测试速度——这个设计很干净）。它的加抖动版本可作为进阶，但**会牺牲确定性/可复现性**，与我们强调的"逐位可复现"矩阵有张力，**建议不抄抖动**。
  - **`tenacity` 的指数退避 + max=60 封顶**：可作为我们渠道层重试的参考实现（我们目前**完全没有重试**，`: `_fetch` 只做异常归一）。
- **坑**：
  - **`[proxy_pool] enabled = false` 且 `proxies = []`** —— 反检测配置是**摆设**，别被"有代理池配置"误导。
  - **反爬/反自动化手段密集**（`AutomationControlled` 关闭、窗口随机、UA 轮换、代理池位）→ **封禁与合规风险显著高于其他项目**。业主若打算用其思路，须评估目标站的服务条款。
  - 百度 `requests` 路径**已被作者实测判定不可用**（注释"反爬严重"）、DDG 路径"连接超时"——**说明这些路今天就走不通，不要重试**。
  - 10.4 MB、`crawler_manager.py` 单文件 34 KB（**上帝对象**），且用 `.cursor/rules/` —— **代码质量与可维护性一般**。
  - 它是**法律法规**（不是标准）方向，**法条正文与标准的自动化价值密度不同**（法条有 `flk.npc.gov.cn` 官方 API，我们 `laws_db.py` 已在用）。
- **判定**：✅ 已核实

---

## 10. legal-database

- **仓库/页面**：**无单一落点** —— 见下
- **判定过程**：`gh api "search/repositories?q=legal-database+in:name"` 返回 5 个同名仓，**全部与"法规/标准获取"无关或不可指认**：

  | 仓库 | 语言 | 最新提交 | ★ | 说明 |
  |---|---|---|---|---|
  | `sublatesublate-design/legal-database` | Python | 2026-02-27 | 5 | 无描述 |
  | `Wilson-wour/legal-database` | — | 2025-11-20 | 0 | 无描述 |
  | `Alxrosen/legal-database` | Python | 2026-06-19 | 0 | 无描述 |
  | `RLAN4/Legal-Database` | HTML | 2026-03-15 | 0 | "APM Legal Database"（**项目管理**用语） |
  | `chiragalwani-EFI/Legal-Database` | HTML | 2026-08-28 | 0 | 案件跟踪，OCR+Gemini（**司法案件**，非法规标准） |

  更早的模糊搜索还返回 `berkmancenter/lumendatabase`（Ruby，**Lumen 删除请求数据库**）、`cc-archive/legaldb`（Django，判例/学术）、`ciarrocki/LibreLaw`（**2020 年停更**）——**没有一个是"法规/标准获取与监控"**。
- **可复用点 / 官方接口技巧**：**无可拆解对象。**
- **坑**：`legal-database` 是一个**通用到失去指认性的名字**。业主清单里出现它，最可能是**从某个二手汇总里抄来的名字**，或指的是某个**私有/未开源**的东西。
- **判定**：❌ 不存在或打不开（**查无此物**）
- **搜过的关键词**：`legal-database`（`in:name`）、`legal database`。**建议业主补充**：该名字的原始出处链接，或它"属于哪个语言/哪个机构"。

---

## 11. china-law-search

- **仓库/页面**：**未找到**
- **判定过程**：`gh api "search/repositories?q=china-law-search+in:name"` → **0 命中**。模糊搜 `china law search` 返回的**全是不同名**项目：
  - `abcddcbaxxxx/chinese-law-mcp`（"Chinese law database covering cybersecurity, data protection, commercial law, and anti-monopoly legislation with full-text search"，★5，2026-03-11）
  - `changpx/Lawdown`（"Search and Download of Chinese Laws and Regulations"，★0）
  - `malnlda/legal-research`（元典开放平台技能序列：`yd-law-search` + `yd-case-search`，★2）
  - `junpe2022/ChineseLawsSearch`（iOS SwiftUI，1525 部法律全文检索，★0）
  - `law-star-cn/lawstar-mcp`（"LawStar legal-data MCP - cloud-hosted Streamable HTTP server"，★0）
  另 `web_search` 命中的也不同名：`ZongziForu/cn-law-hub`、`jianjuntsai/china-legal-toolkit`（均为 Agent Skill）。
- **可复用点 / 官方接口技巧**：**无可拆解对象。**
- **坑**：中文法规检索是**红海**（一晚能搜出十几个近乎同名项目），且**我们已经有官方路径** —— `laws_db.py` 直连 `https://flk.npc.gov.cn/law-search/search/list`（国家法律法规数据库，**官方**）。**任何第三方"china-law-search"都不如我们现有的官方接口。**
- **判定**：❌ 不存在或打不开（**查无此物**）
- **搜过的关键词**：`china-law-search`（`in:name`）、`china law search`、`Chinese law database`。

---

## 12. policy-monitor

- **仓库/页面**：**未找到**
- **判定过程**：`in:name` 搜索返回的**全部是 IT/IAM 的"策略监控"，与法规政策无关**：
  - `TaoYang-Cloud/azure.policy.monitor`（Bicep，★22，2023-01-16）
  - `google-marketing-solutions/ads-policy-monitor`（Python，★21）
  - `LouisMastelinck/Monitor-security-policy-changes-or-admin-activities`（★21）
  - `Raj-GT/Windows-GroupPolicy-Monitor`（PowerShell，★18，"monitor and automate GPO backups"）
  - `ArlanNugara/bicep-azure-policy-monitoring`（Bicep，★3）
  - 模糊搜还会命中 `ossec/ossec-hids`（入侵检测）、`iann0036/iamlive`（GCP/AWS IAM 策略）、`cea-hpc/robinhood`（文件系统）—— **语义完全跑偏**。
  web_search 另返回 `S1998raghu/policy-alert-system`（**这才是真方案**：ingests Federal Register documents + agentic LLM pipeline + Prometheus/Grafana）、`ONS-Innovation/github-policy-dashboard`（机构合规仪表盘）—— **同样不叫 policy-monitor**。
- **可复用点 / 官方接口技巧**：**无可拆解对象。**（若业主指的是 Federal Register 那类方向，**美国有官方 API**——`federalregister.gov/api/v1/`——但那与我们的中国法规/标准场景不同。）
- **坑**：`policy-monitor` 是**最容易被同名 IT 项目淹没**的名字之一。**业主引用时几乎肯定带上下文**（某个汇总页/某个 AI 的建议），而这个上下文丢了。
- **判定**：❌ 不存在或打不开（**查无此物**）
- **搜过的关键词**：`policy-monitor`（`in:name`）、`policy monitor government regulation`、`policy monitor regulation change`。

---

## 13. GovPing

- **仓库/页面**：
  - npm：`https://registry.npmjs.org/govping-mcp-server` （访问时间: 2026-09-18）· 最新 **1.0.3** · **MIT** · 最后发布 **2026-03-28T16:41:26Z**
  - 声明的源码仓：**`https://github.com/changeflowhq/govping-mcp` → `gh api` 返回 `HTTP 404 Not Found`**
  - 第三方目录页：[Official GovPing MCP Server | PulseMCP](https://www.pulsemcp.com/servers/govping)
- **数据源**：npm 元数据原文 ——
  > "GovPing MCP server - **free regulatory intelligence for AI agents. Search 27,000+ regulatory changes across 2,000+ government sources. ORCA-structured data.**"

  即：**它自己不抓取**，而是作为一个 **MCP 客户端**连接 GovPing 的**托管服务**（"free" 但也意味着**受制于人**）。2,000+ 政府源的采集**发生在服务端**，**不开源**。
- **抓取方式 / 清洗方式 / 输出形态**：**均不可得**（源码仓 404，包内容未展开）。可以确定的只有：`dist.tarball` 指向 npm 上的构建产物，`gitHead` 有值（说明**曾**从一个 git 仓发布过）。
- **官方接口技巧**：**不可得**。唯一的"技巧"是它的商业模式：**把多源采集做成中心化服务，用 MCP 协议卖给 Agent**。这**恰恰是我们不能抄的**——我们的价值主张是**自己持有取数链路**。
- **可复用点**：**几乎没有。** 唯一可借鉴的是它宣称的 **"ORCA-structured data"** 这个**统一输出结构**思路（把异构法规源归一成同一 schema）——**而这正是我们 `ChannelResult` 已经在做的事**。
- **坑**：
  - **源码仓 404** = 依赖一个**不可审计的闭源服务**。对"法规/标准"这种**要求可追溯、可举证**的场景，**这是硬伤**（我们的 `evidence_url` 契约要求点开即见原文 PDF，托管服务无法保证）。
  - npm 包存在但仓库消失 → **典型的"发完即弃"**。若服务下线，包立刻变砖。
  - "free" 是**营销词**，不是**授权**——免费额度/停服风险未声明。
- **判定**：⚠️ 未核实（**半真**：npm 包真实存在且可下载；**声明的 GitHub 源码仓不存在**，故**无代码可拆**）

---

## 14. RegRadar

- **仓库/页面**：**多义，无唯一权威落点。** `in:name` 搜索命中**至少 6 个同名仓**：

  | 仓库 | 语言 | 最新提交 | ★ | 描述 |
  |---|---|---|---|---|
  | `Shivay00001/regradar` | Python | **2026-09-10** | 3 | "Real-time AI-powered **Indian** Regulatory Intelligence Platform using FastAPI and **free/local AI models**" |
  | `kingabzpro/RegRadar` | Python | 2025-06-28 | 2 | "RegRadar **watches the worlds regulators** so you dont have to." |
  | `p-kowadkar/RegRadar` | Python | 2026-05-27 | 2 | 无描述 |
  | `gssasank/RegRadar` | TypeScript | 2026-04-12 | 0 | "AI-powered environmental compliance monitoring for NC hog farm CAFOs. **Scrapes federal regulations from the Federal Register**..." |
  | `faytonn/RegRadar` | — | 2025-08-25 | 0 | 无描述 |
  | `EvenSB1NM/RegRadar` | — | 2024-11-20 | 0 | "Hackathon RegRadar" |
  | `sidnov6/regradar` | Python | 2026-06-07 | 0 | "Agentic **EU** regulatory-impact engine — watches **EUR-Lex**... F1 0.957 on DORA" |
  | `McKnight108/Regradar` | Python | 2026-05-19 | 0 | "雷达数据质量控制项目"（**气象雷达**，完全无关） |

- **数据源 / 抓取 / 清洗 / 输出**：**因无法确定指认对象，不做拆解**（避免把 A 的实现安到 B 头上）。
  从描述可判定的**地域分野**：`Shivay00001`=印度、`gssasank`=美国 Federal Register、`sidnov6`=EU EUR-Lex、`kingabzpro`=泛全球。**没有一个是"中国法规/标准"**。
- **可复用点**：**若**业主指的是 EU 方向的 `sidnov6/regradar`，可参考其 **"watches EUR-Lex"** 思路——而 **§15 的 `scka-de/regwatch-eu` 同样盯 EUR-Lex 且是 Apache-2.0 可读源码**，**优先看后者**（我已实测拆解）。
- **坑**：**"RegRadar" 是一个被反复借用的名字**（含一次 hackathon、一个气象项目）。★ 最高仅 3，**全部是实习/演示级作品**。**没有成熟项目**。
  - 业主清单里它标注为"未核实"，**这个标注是准确的**——但问题不是"存不存在"，而是"**指的是哪一个**"。
- **判定**：⚠️ 未核实（**半真**：多个同名仓真实存在；**无一可指认为业主所指**，且全部为小星标演示项目）
- **搜过的关键词**：`RegRadar`（`in:name`）、`RegRadar regulatory`。

---

## 15. regwatch-eu

- **仓库/页面**：https://github.com/scka-de/regwatch-eu （访问时间: 2026-09-18）· Python · **Apache-2.0** · 最近提交 **2026-03-29T21:30:30Z**（创建于同日 `2026-03-29T18:14:31Z` → **一次性发布，此后无提交**）· ★0 · 59 KB
- **数据源**（`src/regwatch/sources/`，**三个源、三种完全不同的取数范式——这是它最大的教学价值**）：
  1. **`eurlex.py` —— SPARQL 查询官方知识图谱**（**不是爬页面**）
     - `POST https://publications.europa.eu/webapi/rdf/sparql`，`data={"query": <SPARQL>}`，`headers={"Accept": "application/sparql-results+json"}`，**`timeout=90.0`**
     - 查询体关键部分：
       ```sparql
       PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
       SELECT DISTINCT ?cellarURI ?title ?date ?celex WHERE {
         ?cellarURI cdm:work_date_document ?date .
         ?expression cdm:expression_belongs_to_work ?cellarURI .
         ?expression cdm:expression_uses_language <.../language/ENG> .
         ?expression cdm:expression_title ?title .
         OPTIONAL { ?cellarURI cdm:resource_legal_id_celex ?celex . }
         FILTER(?date > "…"^^xsd:date)
         FILTER(CONTAINS(LCASE(?title),"dora") || CONTAINS(LCASE(?title),"mica") || …)
       } ORDER BY DESC(?date) LIMIT 200
       ```
       —— **用关键词 `CONTAINS` 做过滤，而不是按法规编号查**；`LIMIT 200` + `ORDER BY DESC(?date)`。
     - 有 `_escape_sparql_string()` 防注入。
  2. **`esma.py` —— RSS 订阅**
     - `GET https://www.esma.europa.eu/rss.xml`（`timeout=30`）→ **`feedparser.parse()`**
     - **日期抽取是三级 fallback 链**（值得抄）：① `<time datetime="YYYY-MM-DD">` 正则 `_TIME_TAG_REGEX` → ② `"15 March 2026"` 式正则 `_DATE_REGEX` + `_MONTH_MAP` → ③ **最后才 `date.today()` 并 `logger.warning`**。
  3. **`eba.py`** —— 同构（另有独立测试 `tests/test_sources/test_eba.py`）
- **抓取方式**：`httpx`（同步），**每源独立 try/except，只把 `TimeoutException` 与 `HTTPStatusError` 分开记日志**，然后**重新 raise**（不吞错）。无重试、无代理、无并发。
- **清洗方式**：
  - `sources/_utils.py::strip_html()` —— **`re.sub(r"<[^>]+>"," ",text)` 再 `re.sub(r"\s+"," ")`**（极简、够用）；
  - `sources/base.py` 是一个 **`typing.Protocol`**：`Source` 协议只有 `id` / `name` / `fetch(since: date, regulations: list[Regulation]) -> list[RawChange]` —— **接口小到只有 1 个方法，这是它最好的一处设计**；
  - `regulations/{dora,mica,ai_act,psd3,amld6}.py` 各自声明**关键词表**（供 SPARQL 过滤复用）；
  - `classifier.py`（6.6 KB）做变更分类；`cache.py` 做去重缓存。
- **输出形态**：`models.RawChange`（`title, date, url, source, celex_id, description`）→ `classifier` 分类后落 cache；`cli.py` 提供命令行；有 `CHANGELOG.md`、CI、publish workflow。
- **官方接口技巧**：
  1. **它根本没"突破"任何东西 —— 因为 EUR-Lex 有官方 SPARQL 端点。** 这条经验比任何爬虫技巧都重要：**先找官方结构化接口，再考虑抓页面**。`publications.europa.eu/webapi/rdf/sparql` 是**公开、免费、有 schema** 的。
  2. **用"标题关键词 CONTAINS"而非"法规编号"来发现变更** —— 因为**新版本/新实施细则是未知编号**的。这是"**发现型**"而非"**核验型**"取数。与我们 `official_gb.py`（按标准号查）**正好互补**。
  3. **`since: date` 参数贯穿所有源** —— **增量拉取是一等公民**，不是事后过滤。
  4. **RSS 是最省事的官方变更流**：`esma.py` 只用 `feedparser` + 三级日期 fallback 就完成了一个源。
- **可复用点**：
  - **`Source` Protocol 的极简契约（`fetch(since, regulations) -> list[RawChange]`）**：我们的 `ChannelAdapter.probe(standard_no, standard_name)` 是**按编号**的；**可以平行增加一个 `discover(since) -> list[Item]` 协议**，把"核验型"与"发现型"分开——**这正是 §8 提到的能力缺口的技术落点**。
  - **RSS 优先**：我们扫的很多政府站**有 RSS/XML**（`govcn` 系、部委公告）。**先找 feed，再写 HTML 解析器**，能省掉大量脆弱选择器。
  - **三级日期 fallback + 最后 `warning` + `date.today()` 而非抛错** —— 保住了"至少能入库"，同时**留下可审计的告警**。与我们 `base.py` 的 `_miss(note=...)` 精神一致。
  - **`strip_html` 的极简实现**（两行正则）—— 我们若只需要"比标题更长的摘要"，**不需要上 BeautifulSoup**。
  - **每源独立的 `since` 增量 + cache 去重**：对我们 `govcn_announce` / `mem_gov` 的公告扫描，**加一个 `since` 水位线**就能把全量抓取变成增量。
- **坑**：
  - **一次性项目**：创建与最后提交同日（2026-03-29），★0，此后 5.5 个月无提交。**代码是"作品"不是"产品"**。
  - 它的**地域是 EU/US 金融监管**（DORA/MiCA/AI Act/PSD3/AMLD6），**与中国标准体系无关** —— **只有方法论可迁移，不能直接取数**。
  - `feedparser.parse(response.text)` **没有对 feed 内容做消毒**；且 `date.today()` 兜底会**污染"变更日期"语义**（把抓取日当发布日期）。
  - 无重试/无退避/无并发：**一源超时就少一源**。
- **判定**：✅ 已核实

---

## 16. @sanmis/crawler

- **仓库/页面**：
  - npm：`https://registry.npmjs.org/@sanmis%2Fcrawler` （访问时间: 2026-09-18）· 最新 **1.0.1**（`1.0.0` 发布于包内元数据）· **MIT** · **394 个文件，解包 930,206 字节**
  - 声明的源码仓：**`https://github.com/TaxWise/taxwise` → `gh api` 返回 `HTTP 404 Not Found`**
- **数据源**：npm 元数据的 `keywords` 原文（**这就是全部可得信息**）：
  > `["crawler","scraper","web-monitor","information-sync","tax","education","social-security","government","rss","declarative","dsl","llm","playwright","policy-monitoring"]`

  `homepage` 与 `bugs.url` 都指向已 404 的 `github.com/TaxWise/taxwise`。
- **抓取方式 / 清洗方式 / 输出形态**：**源码不可得**（仓库 404，未展开 tarball）。从 keywords 可**保守推断**（**未经源码验证**）：Playwright 浏览器自动化 + RSS + "declarative DSL"（声明式规则）+ LLM 参与 + 面向税务/教育/社保/政府（**中文政务场景**，`tax`/`social-security`）。
- **官方接口技巧**：**不可得。** 唯一值得注意的是它的**产品定位**：`declarative` + `dsl` —— 即**用声明式配置描述"抓什么、洗什么"**而不是写代码。这与 §9 `known_urls.toml`（数据与代码分离）、我们"每个渠道一个适配器类"是**三种不同的抽象层级**。
- **可复用点**：
  - **"声明式 DSL 描述抓取规则"这个方向**对我们的 `channels/` 目录有参考价值：目前我们每加一个站就要写一个 `ChannelAdapter` 子类（`ndls.py` 293 行、`cssn.py` 10 KB…）。**若把"URL 模板 + 选择器 + 字段映射"外置成声明式配置**，渠道数增长的成本会显著下降。**但这是架构建议，不是可抄的实现**（源码拿不到）。
- **坑**：
  - **源码仓 404** —— 与 §13 GovPing **完全相同的失效模式**：**包在、仓没了**。
  - **394 个文件 / 930 KB 的 npm 包**，但**无任何可审计的上游**。对一个要进生产取数链路的组件，**这是不可接受的风险**（供应链 + 无法修 bug）。
  - 名字里的 `@sanmis` scope 与仓库 `TaxWise` **不是同一个品牌** —— scope 与 owner 不一致，**来源可疑**。
  - 主分支 `dist/` 构建产物发布（`main: ./dist/cjs/index.js`），**无法确认发布物与任何源码的对应关系**。
- **判定**：⚠️ 未核实（**半真**：npm 包真实存在且可下载；**声明的 GitHub 源码仓不存在**，故**无代码可拆**）

---

## 17. at-ris-mcp

- **仓库/页面**：https://github.com/paragraflabs/at-ris-mcp （访问时间: 2026-09-18）· Python · **Apache-2.0** · 最近提交 **2026-07-25T07:08:24Z**（约 2 个月前，**活着**）· ★1 · 211 KB · 同时在 PyPI 有包（`pip install at-ris-mcp`）
- **数据源**：**奥地利 RIS（Rechtsinformationssystem des Bundes）的官方 OGD API**
  - 端点：**`https://data.bka.gv.at/ris/api/v2.6/`** —— README 明确标注 **"keyless OGD API"（无需 API Key）**
  - 覆盖的应用/集合：**Bundesrecht（联邦法，含 `BrKons` 合并版、`BgblAuth` 公报、`Begut` 草案、`RegV`）**、**Landesrecht（9 州，`LrKons`）**、**Judikatur（判例：OGH/VfGH/VwGH/BVwG/LVwG）**、**Erlaesse/Avsv（部令）**、**Bezirke/Bvb（区级）**、**Gemeinden/Gr/GrA（市镇）**
  - **变更/预警流**：`ris_list_changes` → **RIS History**（`fixtures/` 里有 `history_bundesnormen_soap.xml` → **是 SOAP**）
- **抓取方式**：`httpx` client（`src/ris_client/client.py`）+ `cache.py` + **`ratelimit.py`（有独立限流模块）** + `errors.py`；MCP 层是 `src/ris_mcp/server.py`，**FastMCP/stdio 薄包装**（README 原话："Contains no logic of its own"，HTTP/SSE 传输可选）。
- **清洗方式（**它最有价值的部分**）**：
  - `src/ris_client/textparse.py`：把 **RIS HTML 剥成干净 Markdown**。README 给了一个极具体的量化事实：
    > "RIS HTML (**≈40 KB of CSS boilerplate per document**) is stripped to the legal text, with a `raw` switch for the untouched original."
    即**每个文档约 40 KB 的 CSS 样板**要先扔掉 —— 不洗就是噪声淹没正文。
  - **章节级定位**：可只取单个 `§`/`Artikel`/`Anlage`（RIS 内部用 `Abschnitt.*` 参数）
  - **历史版本**：`Fassung.FassungVom` 参数 —— **"某日当时有效的那个版本"**
  - `citations.py` 处理 **ELI/ECLI** 标识符
  - 输出可切 `markdown | html | xml | raw` 四种
- **输出形态**：MCP 工具返回 + `models.py` 结构化对象；**关键工程资产是 `fixtures/` 目录：`brkons_search.json`(18KB)、`justiz_search.json`(25KB)、`case_text.html`(99KB)、`history_bundesnormen_soap.xml`(22KB)…** 外加 **`reference/` 目录：`xSD` 请求 schema（`OGD_Bundesrecht_Request.xsd` 等 3 个）+ `OGD-FAQ.txt` + `examples_get_post.txt`**。
- **官方接口技巧**：
  1. **最重要的不是技巧，是"官方给了什么"**：RIS 有**免 Key 的 OGD API**，并且**发布 XSD 请求 schema**。它**把 XSD 抄进仓库当参考**（`reference/xsd-request-schema/*.xsd`）—— **这是"先读官方 schema 再写客户端"的典范**。
  2. **`BrKons` vs 公报的区别**：公报（`BgblAuth`）是**增量诺维拉**，`BrKons` 是**合并后的现行有效全文**。**要"现行有效文本"就必须取合并版** —— 这是一个**跨法域通用的洞见**（中国的对应物：公告 vs 现行有效汇编）。
  3. **`Fassung.FassungVom` = 时点快照**：给定日期，返回**当日生效的版本**。**这才是"某法条在案发时是什么"的正确取法**，而不是查历史公告反推。
  4. **变更监控走独立的 History 通道**（SOAP），而不是轮询全文比对。
- **可复用点**：
  - **`fixtures/` 黄金样本目录** → **直接对口我们的"离线可测"要求**。我们 `ndls.py` 已经把 mock 契约写在 docstring 里（"mock 应答契约（离线表驱动，两段 respond 依次弹出）"），但**样本是内联在代码里的**；它把**真实响应原样存成 fixture 文件**，更适合做回归对比。**建议我们把 `ndls`/`official_gb` 的真实响应存一份 fixture。**
  - **`ratelimit.py` 独立成模块**（而非散在各源里）→ 我们 `ndls.py` 的 `PAUSE_S` 是类属性、`proxy_rotate.py` 另有一套；**收敛成 `base.py` 的一层限流**更干净。
  - **"剥 40 KB CSS 样板"这条经验直接适用**：我们抓 `mem_gov.py` / `mohurd.py` 的公告页时，`raw` 里塞的整页 HTML 会污染后续文本。**先量化"样板占比"，再决定抽取策略。**
  - **`Fassung.FassungVom` 时点快照思想** → 我们 `ChannelResult` 有 `effective_date`（实施日期），但**没有"as-of 某个日期时的状态"**。对"某事故发生时该标准是哪版"这类取证需求，这是缺口。
- **坑**：
  - **地域不匹配**：奥地利 RIS，**与中国标准/法规体系无关** —— **纯方法论参考**。
  - ★1、创建与首提交相隔不到 1 天（2026-07-24 → 07-25）、211 KB —— **个人作品**，非社区项目。
  - 依赖**官方 API 的稳定性**；一旦 `data.bka.gv.at` 改版，`reference/*.xsd` 会过期（**但它至少把 schema 留下来了，这是好习惯**）。
  - `ris_list_changes` 走 SOAP —— **SOAP 在现代 Python 里是运维负担**，我们不建议在自有链路引入。
- **判定**：✅ 已核实

---

## 18. standards-version-check

- **仓库/页面**：https://github.com/cuipointer/ageis （访问时间: 2026-09-18）· Python · **许可证：GitHub API 报 `null`（仓库无 license 字段，根目录未见 LICENSE）** · 最近提交 **2026-05-09T01:16:43Z** · ★0 · 181 KB · **Skill 路径：`.claude/skills/standards-version-check/SKILL.md`**（同一仓库里另有 8 个 skill 与 8 个 agent）
- **数据源（**这是本条最值得注意的地方**）**：
  - SKILL.md 自述的"**查询源**"是：
    - `knowledge/standards/index.yaml` —— **权威版本号**（本地单一真相源）
    - **飞书 sheet `TzRlsqLL8hG4I2t7DDFc968QnPg`** —— 原始版本号
  - 而 `tools/build_standards_index.py` 的**真实取数动作**是：
    ```python
    subprocess.run(["feishu", "sheet", "read", SHEET_TOKEN, f"{sheet_name}!A1:J100"],
                   capture_output=True, text=True)
    ```
    —— **它不爬任何标准网站**。它读的是**人工维护的飞书电子表格**。
  - **它唯一"联网"的部分是飞书 CLI**，**不是** openstd / ISO / CEN。
- **抓取方式**：`subprocess` 调 `feishu` CLI + `SHEET_TOKEN` 硬编码常量；无 HTTP 客户端、无重试、无代理。
- **清洗方式（**这一段是可迁移性最高的**）**：
  1. 从 CLI 输出里切 JSON：`raw.find("{")` / `raw.rfind("}")` 再 `json.loads`；
  2. **前向填充合并单元格**（中文表格的通病，**写得非常干净**）：
     ```python
     # 前向填充合并单元格
     last = [""] * 12
     for row in rows:
         r = row + [None] * (12 - len(row))
         cells = [_cell(c) for c in r[:12]]
         for j in range(len(cells)):
             if cells[j]: last[j] = cells[j]
             else:       cells[j] = last[j]
     ```
  3. **单元格取值容错**：`_cell()` 处理 `None` / 富文本 `list[{"text":...}]`；`_url()` 专门从 `[{"type":"url","link":...}]` 这类**富文本链接结构**里抠 URL —— **这正是飞书/钉钉/企微 API 的典型返回形状**。
  4. **状态建模比我们细**：`current` / **`current_no_version`**（sheet 里版本列留空时**不判 unknown，而判"现行但无版本号"**）/ `superseded`（版本列写"废止"）/ `unknown` / **`needs_verification`**。注释还解释了取舍理由：*"sheet 中版本列留空的多为现行标准，标为 current_no_version 而非 unknown"*。
  5. **别名/外部补丁合并**：`extras.yaml::standards` 用 `setdefault` **只补缺、不覆盖** sheet 来源；`extras.yaml::aliases.non_standard_refs` 登记"**看着像标准号但其实不是**"的串，防止审计误报。
- **输出形态**：`knowledge/standards/index.yaml`（含 `version/last_updated/source_sheet/stats/standards{cert,area,category,version,status,applies_to,url}`）；另有 `matrix.yaml`、`discrepancies.yaml`、`extras.yaml` 与每标准一个 Markdown 摘要。
- **官方接口技巧**（这个 Skill 的"技巧"很朴素，但很对）：
  1. **`--diff` 用退出码当变更信号**：
     ```python
     print(f"[diff] added={len(added)} removed={len(removed)} version_changed={len(version_changed)}")
     if added: print(f"  added: {sorted(added)}")
     if version_changed: print(f"  version_changed: {version_changed}")
     return 1 if (added or removed or version_changed) else 0     # ← 0=无变化 / 1=有变化
     ```
     **退出码 0/1 直接当 cron/CI 的"有无变更"判据**。
  2. **"不自动更新真相源"的纪律**（SKILL.md 明确写）：
     > "如发现版本变更：1. 写入 `docs/reports/standards-diff-YYYY-Q.md` 2. PushNotification 通知维护人员 **3. 不自动更新 index.yaml（避免未审核内容入库）**"
     —— **变更只报告、不自动落库**。这与我们 `UDP_CHANNEL` 里 `recordable()`（captcha 结果绝不写库）是**同一种克制**。
  3. **季度 routine**：cron `0 9 1 */3 *`（每季度首日 09:00）—— **法规/标准的复核节奏本来就该是季度级，不是分钟级**。
  4. **审计交叉验证**（`standards_tool.py::cmd_audit`）：把 `matrix.yaml` 里**被引用**的标准与 `index.yaml` 里**已登记**的标准做差集，用正则 `re.match(r"(EN\d|GB|YD|IEC|CISPR|FCC|ANSI|ISO|3GPP|ITU)", ...)` **只保留像标准号的**再报缺失 —— **"引用完整性检查"**。
- **可复用点**：
  - **"前向填充合并单元格"的 `_cell()` 清洗** → 我们 `mem_gov.py` / `mohurd.py` / `govcn_announce.py` 解析的中文公告表格**普遍有合并单元格**；这段 6 行代码可作通用工具进 `base.py`。
  - **富文本链接抠 URL 的 `_url()`** → 飞书/企微/钉钉 API 通用形状；若业主将来接协作平台，直接复用。
  - **`current_no_version` / `needs_verification` 两个补充状态** → 我们 `LEGAL_STATUSES = ("effective","upcoming","superseded","withdrawn")` 只有 4 态。它揭示了一个真实问题：**"现行但版本号不明"是一种独立状态，不该被压进 `effective` 或 `None`**。结合 §2 的 `暂不实施`、§4 的 `有更新版`、我们 `ndls.py` 的 `未生效/作废/废止转行标/已修订`，**状态枚举的缺口是系统性的**。
  - **`--diff` 退出码 + "只报告不落库"** → 与我们 `UPD_BAD_PAYLOAD` / `recordable()` 的校验层哲学一致，可作为**公告扫描通道**的输出契约。
  - **`extras.yaml` 的 `non_standard_refs` 白名单** → 治"正则误抓标准号"。我们 `norm_no()` + `STD_CODE_RE` 同样会误抓（如把 `GB 55037` 之外的串当标准号）；**加一张"已知非标准串"白名单**是低成本高收益。
- **坑**：
  - ⚠️ **它不是数据获取工具，是数据"校对"工具。** SKILL.md 描述的功能（"核对用户引用的标准版本号是否为现行版本"）**完全建立在人工维护的飞书表之上**。**指望它替你抓标准 = 完全错位。**
  - **硬编码飞书 token**（`SHEET_TOKEN = "TzRlsqLL8hG4I2t7DDFc968QnPg"`，另 `source_doc = "DrLedxhd2oUdTexqnpkcpIo4nVd"`）—— **跨组织不可用**。
  - **依赖外部 `feishu` CLI**（不在 `requirements` 里，靠 PATH），**换机器即断**。
  - ★0、无 license 字段、仓库是一个"个人 EMC/RSE 认证工程知识库"（`knowledge/standards/{ce,fcc,ccc}/…` 全是 EN301489/CISPR/FCC Part 15 等 EMC 标准）—— **与我们的法规/标准库主题只是"标准"两个字重合**。
  - **§8 的教训在此成立**：这个 Skill **确实有真代码**（`tools/standards_tool.py` 12 KB、`tools/build_standards_index.py` 9.5 KB），所以**"是 Skill"不等于"没代码"**；但**§5 的 gbqw 证明"有代码"也不等于"有用"**。**必须逐个打开看。**
- **判定**：✅ 已核实

---

## 19. 能直接抄的 5 个取数技巧

> 全部来自**我实际打开过的代码**；每条给出"出处项目 → 落地到我们哪一块"。

### 技巧 1️⃣ 用"单一精灵图 + 网格坐标"把预览图还原成整页，并用 `Cache-Alive: chunked` 拿图

**出处**：`OpenSTD_Spider`（`parse/gb688.py`，最完整）与 `GBMCP`（`downloaders/gb.py`，更严谨）、`gb-downloader`（`main.py`，PIL 版）。
**做法**：`showGb?type=online&hcno=` 返回的 HTML 里，每页一个 `div.page[bg]`（bg = 一张 10×10 精灵图的资源名），页内每个 `span.pdfImg-<col>-<row>` 的 `background-position:-Xpx -Ypx` 给出该块在精灵图中的**源坐标**；按 `page.width//10 × page.height//10` 切块、按 `(col,row)` 贴回。取图必须带 `Referer` + **`Cache-Alive: chunked`**。
**能解决我们的什么问题**：**我们 `official_gb.py` 只能探"状态"，拿不到标准文本**。这是把我们渠道层从"核验"扩展到"取全文"的**唯一自有路径**（不依赖任何第三方 OCR/打码服务）。GBMCP 版还多两处加固：源块高度按宽高比推算（而非硬编码 `/10`）、源坐标 `abs()` 归一化。
**注**：优先走 §技巧 2（更省），此技巧作为 `allow_download=False` 时的兜底。

### 技巧 2️⃣ `viewGb?type=online&hcno=<id>` 的 base64 分片通道：伪装 iPad UA，10 段拼接后再整体解码

**出处**：`gb688_downloader`（`standard/GB.py::GBCore.get_bytes`）。
**做法**：
```python
# UA 必须是 iPad/移动端，才进"手机版预览模式"的 base64 通道
headers = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) ... Version/11.0 Mobile/15A5341f Safari/604.1'}
text = ""
for i in range(10):
    url = f"http://c.gb688.cn/bzgk/gb/viewGb?type=online&hcno={hcno}" + ("" if i == 0 else f".00{i}")
    time.sleep(1)
    text += requests.get(url, headers=headers).text
pdf_bytes = base64.standard_b64decode(text)      # ← 必须先拼字符串，再整体解码
```
**能解决我们的什么问题**：**一次性绕开验证码 + 精灵图 + OCR 三条重链路**，直接得到完整 PDF。若有效，是我们 GB 取全文链路的**成本最优解**。
**⚠️ 使用前提**：这是 **2020 年的实测**，我**未代为验证其 2026 年仍有效**。落地前**必须由业主发一次真实请求确认**（这属于"上游接口可能已失效"的风险项，不是可直接落库的结论）。

### 技巧 3️⃣ 重定向"逐跳"复检 + 编码"按浏览器优先级"嗅探

**出处**：`changedetection.io`（`content_fetchers/requests.py`）。
**做法**：
- **重定向**：`allow_redirects=False` 起步，`for _ in range(10)` 手工跟随，**每一跳**都调 `is_url_private_or_parser_confused()`，命中私网/保留段就抛错；超 10 跳抛 `Too many redirects`。
- **编码**（WHATWG 顺序）：HTTP `charset` → **BOM**(`utf-8-sig`/`utf-16-le`/`utf-16-be`) → **前 2KB 的 `<meta charset>`** → 最后才 `chardet`；XML/RSS 先读 `<?xml encoding="...">`。
**能解决我们的什么问题**：两处**已知缺口**都被它精确命中。
1. 我们 `base.py::CurlCffiTransport` 的注释**自己就写了**：*"`is_private_url` 只在**发起前**判过一次"*，并靠 `allow_redirects=False` 让调用方自保 —— changedetection 给出了**闭环实现**（每跳都判）。
2. 我们 `fetch_page()` 已经把 `headers` 与 `raw_bytes` 都暴露出来了，**但没有任何编码决策逻辑**；`foodmate` 那类 `gb18030` 站会乱码（GBMCP 是靠**硬编码域名判断**绕过的，是下策）。**这条可以直接实现成 `fetch_page` 的一个后处理器。**

### 技巧 4️⃣ "洗内容 + 洗差异"两段式过滤链，与"屏蔽易变文本"的双正则模型

**出处**：`urlwatch`（`filters.py` 的 `filter:` / `diff_filter:` 两段链）+ `changedetection.io`（`html_tools.py::strip_ignore_text` / `element_removal`）。
**做法**：
- **两段式**：`filter` 作用于**抓回的内容**，`diff_filter` 再作用于**生成的 diff**（`handler.py::get_diff()` 会二次过滤）。
- **易变内容屏蔽**：`strip_ignore_text(content, wordlist, mode)` 支持 **Perl 风格 `/regex/flags`**，且**区分单行正则与跨行正则**（`ignore_regex_multiline`），用于整块摘掉时间戳/浏览量块；`element_removal` 支持 `xpath:` / `xpath1:` 前缀在**比较前**删元素。
- 配套：`sort` + `remove-duplicate-lines` 治"列表顺序随机导致假变更"。
**能解决我们的什么问题**：**我们渠道层目前没有任何"归一化中间层"** —— 页面直接解析成 `ChannelResult`。政府公告页上的**"发布时间 / 浏览次数 / 当前时间"**是天然抖动的，会导致 `derive_change_type()` 误判成 `new_version`。**加一层"页面快照归一化"（先摘易变块再比）能直接压低误报率**；`sort`/`remove-duplicate-lines` 对 `govcn_announce.py`、`mem_gov.py` 这类**列表页**尤其对症。

### 技巧 5️⃣ 官方接口优先：SPARQL / RSS / 免 Key OGD API，以及"增量是一等公民"

**出处**：`regwatch-eu`（`sources/eurlex.py` 的 SPARQL、`sources/esma.py` 的 RSS）+ `at-ris-mcp`（RIS 免 Key OGD API + 官方 XSD schema + `Fassung.FassungVom` 时点快照）。
**做法**：
- **先找结构化官方接口，再考虑抓页面**：EUR-Lex 有 `publications.europa.eu/webapi/rdf/sparql`（SPARQL + JSON 结果），ESMA 有 `rss.xml`，奥地利 RIS 有 `data.bka.gv.at/ris/api/v2.6/`（**免 Key**，且**发布 XSD 请求 schema**，at-ris-mcp 把 XSD 抄进 `reference/` 当参照）。
- **"发现型"与"核验型"取数是两种接口**：`fetch(since: date, regulations) -> list[RawChange]` 是**按日期窗口 + 标题关键词**拉"新出现的东西"（`CONTAINS(LCASE(?title),"dora")`），**不依赖已知编号**；我们 `probe(standard_no)` 是**按编号核验**。**两者互补，不可互相替代。**
- **`since` 参数贯穿所有源** —— 增量拉取是协议的一等公民，不是事后过滤。
- **RSS 的日期抽取用三级 fallback**：`<time datetime>` → `"15 March 2026"` 正则 → 最后 `date.today()` + `warning`（不抛错，保住入库，同时留审计线索）。
**能解决我们的什么问题**：
1. **补上一个真实的能力缺口**：我们只能回答"我已知的这个标准过期了吗"，**无法发现"我根本不知道的新标准"**。`regwatch-eu` 的 `Source` Protocol（只有一个方法的极简 `Protocol`）给出了**平行加一个 `discover(since)` 协议**的模板。
2. **降低成本**：我们扫的政府站里**有 RSS/XML 的应优先用 feed**，能省掉一堆脆弱选择器；`govcn_announce.py` / `mem_gov.py` 加 `since` 水位线即可从全量转增量。
3. **时点快照**：`Fassung.FassungVom`("某日当时有效的版本")提醒我们 `ChannelResult` 缺 **as-of 语义**——对"事故发生时该标准是哪版"的取证需求是硬缺口。

**（备选第 6 条，值得一提）**：`at-ris-mcp` 的 **`fixtures/` 黄金样本目录**（把真实响应原样存成 `*_search.json` / `*_text.html` / `*_soap.xml`）—— 我们 `ndls.py` 的 mock 契约是**内联在 docstring 里**的，存成 fixture 文件更利于回归对比，且天然满足我们"离线可测"的要求。

---

## 20. 机器可读附录

```json
[
  {
    "name": "GBMCP",
    "repo": "https://github.com/LoyDgIk/GBMCP",
    "lang": "Python",
    "license": "MIT-declared-in-pyproject-but-NO-LICENSE-file (GitHub API reports null)",
    "last_commit": "2026-06-05T14:00:19Z",
    "data_sources": [
      "GET https://openstd.samr.gov.cn/bzgk/std/std_list?r=&page=&pageSize=&p.p1=0&p.p2=&p.p5=&p.p6=&p.p7=&p.p90=&p.p91=",
      "GET https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=",
      "GET https://openstd.samr.gov.cn/bzgk/std/showGb?type=online|download&hcno=&request_locale=zh",
      "GET https://openstd.samr.gov.cn/bzgk/std/viewGb?hcno=",
      "GET https://openstd.samr.gov.cn/bzgk/std/viewGbImg?fileName= (needs Referer + Cache-Alive: chunked)",
      "GET/POST https://openstd.samr.gov.cn/bzgk/std/gc , /verifyCode (verifyCode + agreeIECTips=true)",
      "GET https://std.samr.gov.cn/gb/search/gbAdvancedSearchPage (JSON)",
      "GET https://std.samr.gov.cn/gsm/search/gsmPage (JSON) , /gsm/search/gsmDetailed?id=",
      "GET https://std.samr.gov.cn/org/search/orgCommiteeInfoPage (JSON) , /search/orgDetailView?data_id=",
      "POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPortalStandardList , /getPortalStandardById",
      "POST https://www.ttbz.org.cn/cms-proxy/ms/bus/organList/portal/queryOrgan , /load",
      "GET https://law.foodmate.net/rule/search.php?kw=&fields=&yxxzt=&catid=&order=&page=&fromtime=&totime=&sfromtime=&stotime=",
      "GET https://down.foodmate.net/standard/search.php?kw=&fields=&corpstandard=&bzstatus=&catid=&page=",
      "GET https://down.foodmate.net/standard/down.php , /standard/yulan.php",
      "GET https://www.doc88.com/tag/<query> , /p-<p_code>.html",
      "sources/{cfsa,mee,mem,nhc,resmea,itu}.py"
    ],
    "fetch_method": "httpx.AsyncClient (no browser automation); ddddocr local OCR with cv2 threshold(190)+bitwise_not; pluggable OCR via GBMCP_OCR_COMMAND env (subprocess, {image} placeholder); captcha retry loop; 30s timeout configurable; explicit Referer on showGb",
    "clean_method": "BeautifulSoup(html.parser); dual-path: JSON API first then SSR-embedded JSON fallback via json.loads(unescape(<script id=...>)); _extract_key_values() pairs td/th in <tr>; _extract_labeled_values() slices full-page text by label positions; totals via regex 共\\s*(\\d+)\\s*条 and 约\\s*(\\d+)\\s*个; gb18030 forced decode for down.foodmate.net",
    "reusable": [
      "Triple-verify downloaded PDFs: Content-Type contains pdf OR Content-Disposition ends .pdf, then confirm first 5 bytes == b'%PDF-' else unlink",
      "Sprite/tile reassembly with source tile height derived from aspect ratio (more robust than hardcoded /10)",
      "viewGbImg requires BOTH Referer and 'Cache-Alive: chunked' header",
      "JSON-first with SSR-embedded JSON fallback for ttzb (our ttzb.py only has the JSON path)",
      "Safe filename via safe_filename(); .gbmcp.json config file",
      "MCP tool split: search / get_detail / download as separate steps with explicit download boundaries in SKILL.md"
    ],
    "pitfalls": [
      "NO LICENSE file in repo root; only pyproject.toml declares MIT -> legally unsafe to copy code",
      "One-shot project: created and last pushed the same day (2026-06-05), no commits for 3.5 months, 1 star",
      "Heavy overlap with our existing channels: openstd.py == official_gb.py (identical std_list params), ttzb.py == our ttzb.py, mee.py == our mee.py - it is overlap, not complement",
      "Only real increment over us is the download path, which we lack entirely",
      "Captcha success relies purely on retry count; no degradation path"
    ],
    "verification": "verified"
  },
  {
    "name": "OpenSTD_Spider",
    "repo": "https://github.com/SocialSisterYi/OpenSTD_Spider",
    "lang": "Python",
    "license": "GPL-3.0",
    "last_commit": "2026-03-18T13:52:43Z",
    "data_sources": [
      "GET https://openstd.samr.gov.cn/bzgk/gb/std_list?r=&page=&pageSize=&p.p1=&p.p2=&p.p5=&p.p6=&p.p7=&p.p90=&p.p91=",
      "GET https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=<32-hex>",
      "GET http://c.gb688.cn/bzgk/gb/showGb?type=online&hcno= (Referer to openstd newGbInfo)",
      "GET http://c.gb688.cn/bzgk/gb/viewGbImg?fileName= (Cache-Alive: chunked)",
      "GET http://c.gb688.cn/bzgk/gb/viewGb?hcno= (streamed real PDF)",
      "GET http://c.gb688.cn/bzgk/gb/gc?_<ms timestamp> , POST /verifyCode (verifyCode + agreeIECTips)"
    ],
    "fetch_method": "httpx.AsyncClient + aiofiles streaming (aiter_bytes(1024*100)); follow_redirects=False by default, True only for image fetch; Edge 133 UA; ddddocr + cv2 threshold(190) + bitwise_not (local OCR, no paid captcha platform); NO proxy pool, NO concurrency, NO retry decorator",
    "clean_method": "BeautifulSoup(html, lxml) with very specific selectors: div.bor2 / table.tdlist / table.mk1 tr td h1 for metadata; table.result_list>tbody:nth-of-type(2)>tr rows; hcno sliced from onclick attribute [10:-3]; pagination terminal condition parsed positionally from div.hidden-xs span strings ([8]=total, [11]=page, [12][3:]=total_page); not-found detected by literal text '您所查询的标准系统尚未收录'; status word table 现行/即将实施/废止/暂不实施",
    "reusable": [
      "total_page positional parse as a deterministic pagination terminal condition for official_gb",
      "literal '尚未收录' text as a more reliable not_found signal than HTTP 404",
      "image_paste_white(): alpha-composite sprite blocks onto white background before pasting (avoids black tiles)",
      "gb688_uniq_imgid(): dedupe img_id set before downloading (downloads far fewer images than pages)",
      "Two-tier degradation: allow_download (button.xz_btn) -> direct viewGb; else allow_preview (button.ck_btn) -> tile reassembly",
      "reportlab Canvas(A4) + drawImage with min(w_ratio,h_ratio) centering to avoid distortion",
      "The 5th status 暂不实施 (NOTIMP) missing from our STATE_TEXT_MAP"
    ],
    "pitfalls": [
      "GPL-3.0 strong copyleft - reading for ideas only, copying code would infect our distribution",
      "Base URL is plaintext http:// (MITM-able)",
      "c.gb688.cn vs openstd.samr.gov.cn are DIFFERENT hosts; we only use the latter, so we lack the domain knowledge that document content lives on gb688",
      "No retry / no backoff / no proxy: a block is a hard failure",
      "98 stars but entirely serial single-threaded design"
    ],
    "verification": "verified"
  },
  {
    "name": "gb-downloader",
    "repo": "https://github.com/suwadaimyojin/gb-downloader",
    "lang": "Python",
    "license": "MIT",
    "last_commit": "2025-04-25T08:46:32Z",
    "data_sources": [
      "GET http://c.gb688.cn/bzgk/gb/showGb?type=download&hcno=<hardcoded F60B16F6F204597DDAFD8CCCFC931E11> (only to harvest JSESSIONID)",
      "GET http://c.gb688.cn/bzgk/gb/gc , POST /verifyCode (verifyCode only, no agreeIECTips)",
      "GET http://c.gb688.cn/bzgk/gb/showGb?type=online&hcno=<target>",
      "GET http://c.gb688.cn/bzgk/gb/viewGbImg?fileName=<bg> (302 redirect to real image)"
    ],
    "fetch_method": "requests.Session(); ddddocr DdddOcr() with NO image preprocessing; captcha retry max 3; manual 302 handling via allow_redirects=False then reading Location and re-requesting; leftover Proxy-Connection: keep-alive header",
    "clean_method": "BeautifulSoup(html.parser); width/height from div.page style regex with hardcoded 2315x3274 fallback; span class pdfImg-(\\d+)-(\\d+) for grid position; background-position regex for source offset; standard number from <title> regex",
    "reusable": [
      "302 probe then Cache-Alive header: viewGbImg redirects (allow_redirects=False to read Location) and the redirected request still needs Cache-Alive: chunked",
      "JSESSIONID harvested as an explicit precondition step from Set-Cookie of showGb?type=download, proving gb688 binds captcha validation to a session"
    ],
    "pitfalls": [
      "Rough re-implementation of OpenSTD_Spider with strictly less rigor",
      "Source tile size hardcoded as exactly page_width/10 and page_height/10, and grid regex uses \\d+ instead of single digit -> misaligns if the sprite is not exactly 10x10",
      "Hardcoded hcno F60B16F6F204597DDAFD8CCCFC931E11 leaked from a packet capture, unrelated to the user's target standard",
      "Only 3 files, 8 KB, 8 stars, ~17 months stale - single-session script published once",
      "README says 'learning and personal research only / do not use commercially'"
    ],
    "verification": "verified"
  },
  {
    "name": "gb688_downloader",
    "repo": "https://github.com/inntran/gb688_downloader",
    "lang": "Python (GitHub reports language: null)",
    "license": "Apache-2.0",
    "last_commit": "2020-06-18T09:05:19Z",
    "data_sources": [
      "GET http://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=<sort_name>&p.p91=<sort_type>&p.p2=<key>&page=&pageSize=",
      "GET http://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=",
      "GET http://c.gb688.cn/bzgk/gb/viewGb?type=online&hcno=<hcno> and hcno.001 ... hcno.009 (base64 PDF chunks)",
      "POST http://hbba.sacinfo.org.cn/stdQueryList (current,size,key,status,ministry,industry,pubdate,date)",
      "POST http://dbba.sacinfo.org.cn/stdQueryList",
      "GET http://hbba.sacinfo.org.cn/attachment/downloadStdFile?pk=<pk>",
      "GET http://dbba.sacinfo.org.cn/attachment/downloadStdFile?pk=<pk>"
    ],
    "fetch_method": "requests, fully synchronous, NO session reuse, NO captcha, NO OCR, NO proxy, NO retry (this path needs none). iPad Safari 11 User-Agent is essential to enter the mobile preview mode. Sleeps 1s between the 10 base64 chunk requests.",
    "clean_method": "regex-only, no BeautifulSoup: total via <span class=\"badge\">(\\d+)</span>; rows via <tr>([\\s\\S]*?)</tr> then items[5:-2] to skip header/footer; hcno from showInfo\\('(.+?)'\\); status guessed by re.findall('[\\u4e00-\\u9fa5]{2,4}') ; dates via datetime.fromisoformat(data[6][:-2].replace('>','')) ; pages = 1 if total==size else total//size+1 ; filename filtering by BAN_LIST char removal",
    "reusable": [
      "BASE64 CHUNK PDF TRICK: GET viewGb?type=online&hcno=<id> returns base64 text to be concatenated across 10 parts (bare hcno then .001-.009) and decoded ONCE as a whole - bypasses captcha, sprite reassembly and OCR entirely",
      "iPad/mobile UA is what selects this base64 channel instead of the desktop sprite channel",
      "can_download() checks for the literal text '在线预览' on the page, simpler and more reliable than parsing buttons",
      "hbba/dbba.sacinfo.org.cn download endpoint: GET /attachment/downloadStdFile?pk=<pk> using the pk from /stdQueryList rows - SAME HOST we already use in hbba.py/dbba.py, zero new-domain cost",
      "format_search_api() field mapping {status,key,name,standard_no,act_date} is isomorphic to our ChannelResult",
      "HDB pubdate parameter accepts ''/-1/-3/-6/-12/-24 months - a natural incremental-pull window",
      "HDB status vocabulary includes 有更新版, another value outside our 4-state enum"
    ],
    "pitfalls": [
      "6 years 3 months stale (2020-06) - requests + regex HTML parsing will break on any site redesign",
      "NOT verified by me as still working; treat every endpoint as unconfirmed",
      "created_at (2020-07-20) is LATER than pushed_at (2020-06-18), suggesting a fork/transfer; language: null, 0 stars",
      "Status guessed via a '2-4 Chinese characters' regex can mis-capture 暂不实施 or 即将实施",
      "Date parsing relies on slicing off the last 2 characters - extremely brittle"
    ],
    "verification": "verified"
  },
  {
    "name": "gbqw",
    "repo": "https://github.com/RhettTien/gbqw",
    "lang": "Java (Android)",
    "license": "MIT",
    "last_commit": "2025-07-18T14:26:58Z",
    "data_sources": [
      "None. No OkHttp/HttpURLConnection/http client anywhere. Loads a user-configurable URL (default from R.string.default_web_url) into a WebView; the only persisted data is a local SQLite favorites table."
    ],
    "fetch_method": "WebView human browsing. Sets a desktop Chrome 120 User-Agent; shouldOverrideUrlLoading intercepts URLs starting with the user-configured default_jump_url and navigates to the detail fragment; onReceivedTitle extracts the standard number via regex GB/?T?\\s*\\d+(\\.\\d+)?-?\\d* ; falls back to evaluateJavascript('(function(){return document.title;})();')",
    "clean_method": "One regex over the page title to extract the standard number. Nothing else.",
    "reusable": [
      "Only the observation that the page <title> already carries a GB/T xxxxx-YYYY standard number - usable as a supplementary regex in our web_fallback.py"
    ],
    "pitfalls": [
      "The README itself says '其实，使用浏览器和收藏夹，效果也是一样的 QAQ' (using a browser with bookmarks works just as well) - the author concedes it adds no value",
      "About screen says 'Powered by Claude', README says built entirely with Cursor - an AI-generated toy",
      "0 stars; topic is substantively unrelated to regulatory/standards data acquisition",
      "static WebView with manual removeView carries leak risk (engineering quality, not data quality)",
      "RECOMMEND REMOVING FROM THE LIST"
    ],
    "verification": "verified"
  },
  {
    "name": "changedetection.io",
    "repo": "https://github.com/dgtlmoon/changedetection.io",
    "lang": "Python",
    "license": "Apache-2.0",
    "last_commit": "2026-09-18T00:24:54Z",
    "data_sources": [
      "Any user-configured URL. Pluggable fetchers: content_fetchers/{requests,playwright,puppeteer,webdriver_selenium}.py plus screenshot_handler.py."
    ],
    "fetch_method": "requests fetcher: urllib3 Retry(total=6, connect=6, read=6, status=0, backoff_factor=0.5, allowed_methods=[HEAD,GET,OPTIONS,POST]) - explicitly does NOT retry HTTP status codes; verify=False; allow_redirects=False then manual per-hop redirect following with is_url_private_or_parser_confused() re-validation each hop, max 10 hops; WHATWG encoding sniffing (header charset -> BOM -> <meta charset> first 2KB -> chardet), XML/RSS reads <?xml encoding> first; binary content short-circuits encoding sniffing; is_binary content reduced to md5 hexdigest",
    "clean_method": "html_tools.py (43KB): include_filters / subtractive_css_selector / subtractive_xpath_selector / element_removal (xpath:/xpath1: prefixes or plain CSS, applied BEFORE comparison); strip_ignore_text(content, wordlist, mode) supports Perl-style /regex/flags and separates single-line from multiline regexes; XXE hardening via XMLParser(resolve_entities=False, no_network=True); get_safe_xpath3_parser() guards XPath 3.0 file/env reads; workarounds_for_obfuscations(); HTML->text via inscriptis (not regex); extract_json_blob_from_html with jq; restock_diff/pure_python_extractor.py implements JSON-LD/OpenGraph/microdata via stdlib html.parser + jsonpath_ng '$..(price|Price)' (deliberately avoids lxml C-layer memory leaks)",
    "reusable": [
      "Per-hop redirect re-validation closes the exact gap our base.py comment admits (is_private_url only checks once before the request)",
      "WHATWG encoding sniff order (BOM -> meta charset -> chardet) - we expose headers+raw bytes in fetch_page() but have NO encoding decision logic; gb18030 sites will be mojibake",
      "strip_ignore_text's single-line vs multiline dual-regex model for suppressing volatile page regions (timestamps, view counters) that cause false new_version",
      "element_removal's xpath:/xpath1: prefix convention as an optional per-adapter prune config",
      "Retry with status=0 matches our design: non-200 must not retry and must not throw, it goes to the degradation chain (our _miss())",
      "Levenshtein/Indel normalized similarity as a change-magnitude threshold to trigger notifications; LEVENSHTEIN_MAX_LEN_FOR_EDIT_STATS=100000 guard skips huge docs; deliberately uses MIT rapidfuzz instead of GPL python-Levenshtein to keep deps free of strong copyleft",
      "Binary resources detected by md5 instead of text diff (relevant for PDF-type sources)",
      "etag / NotModifiedError conditional requests to cut load and reduce WAF exposure"
    ],
    "pitfalls": [
      "Solves 'did the page change', NOT 'which version supersedes which' - it has no GB/T semantics and does not understand 被代替 relationships. It CANNOT replace our channel adapters, only harden the transport/preprocessing layer",
      "verify=False is a deliberate security compromise",
      "46 MB repo with Web/API/UI/multiple processors and LLM integration - far too heavy to adopt wholesale; take file-level ideas only",
      "image_ssim_diff pulls libvips/OpenCV with possible subprocess isolation - high ops cost"
    ],
    "verification": "verified"
  },
  {
    "name": "urlwatch",
    "repo": "https://github.com/thp/urlwatch",
    "lang": "Python",
    "license": "NOASSERTION (GitHub could not identify it; raw /LICENSE returns 404 - no LICENSE file at repo root, terms must be confirmed manually)",
    "last_commit": "2026-07-10T08:56:34Z",
    "data_sources": [
      "Any subscribed URL. Three job kinds in lib/urlwatch/jobs.py: ShellJob (runs a command), UrlJob (HTTP), BrowserJob (browser automation)."
    ],
    "fetch_method": "UrlJob with CHARSET_RE for text/(html|plain); charset= from headers; etag conditional requests; NotModifiedError short-circuit; configurable ignore_connection_errors / ssl_no_verify; NO retry decorator, NO concurrency, serial worker",
    "clean_method": "A 30+ item plugin-style filter chain, each a FilterBase subclass with __kind__: html2text, csv2text, pdf2txt, ical2txt, json, pretty-xml, grep, grepskip, strip, striplines, element-by-id/class/style/tag, sha1, hexdump, css, xpath, regex (sub/findall), sort, remove-duplicate-lines, reverse, shellpipe, ocr, jq, beautify, automatch, keep_lines_containing. css/xpath share one LxmlParser with EXPR_NAMES. TWO-STAGE: 'filter' cleans fetched content, 'diff_filter' then cleans the generated diff (handler.py::get_diff). Diff via difflib.unified_diff or external diff_tool.",
    "reusable": [
      "Two-stage filter chain (clean content, then clean the diff) - we have NO normalization layer between fetch and ChannelResult",
      "compared_versions: compare against N versions back rather than only the last one, preventing flapping from transient renders",
      "treat_new_as_changed: set old_data='' on first fetch so a newly added item still produces a change diff (fixes the classic first-poll miss)",
      "sort + remove-duplicate-lines: the standard fix for false changes on pages whose list order is unstable (directly applies to our govcn_announce.py / mem_gov.py list-page scans)",
      "diff_tool exit-code convention (0=no change, 1=differs, other=error) is isomorphic to our change_type tri-state",
      "sha1 filter for whole-page hash comparison when you only need a boolean 'changed'",
      "shellpipe / OCRFilter as escape hatches for image- or PDF-based pages",
      "etag / NotModifiedError to cut load (we do unconditional requests everywhere)"
    ],
    "pitfalls": [
      "NO LICENSE file at repo root (GitHub reports NOASSERTION, raw LICENSE 404) - must confirm terms before copying any code",
      "Serial, no concurrency, no retry: designed for a personal tool watching dozens of URLs, not high-frequency batch probing. Architecturally weaker than changedetection.io",
      "Generic web monitoring - like changedetection.io it does NOT understand standard-number semantics",
      "Upside: only 1.3 MB vs 46 MB, so ideas are easier to absorb wholesale"
    ],
    "verification": "verified"
  },
  {
    "name": "National Standard Monitor Skill",
    "repo": "https://clawhub.ai/sereinone/skills/national-standard-monitor-skill/security-audit",
    "lang": "unknown (ClawHub-hosted Skill, not a GitHub repo)",
    "license": "unknown",
    "last_commit": "unknown (version 1.0.0; no commit history visible on ClawHub)",
    "data_sources": [
      "openstd.samr.gov.cn (per the page's own og:description: '从openstd.samr.gov.cn获取最新现行标准列表') - the SAME site our official_gb.py already uses. No code was retrievable to confirm which endpoint."
    ],
    "fetch_method": "UNVERIFIABLE - page body is client-side rendered; no public API or raw endpoint returned content",
    "clean_method": "UNVERIFIABLE",
    "reusable": [
      "INFERRED ONLY, NOT VERIFIED: per-ICS-category bulk pull of the 'latest current standards list' compared against a local downloaded set = snapshot-diff monitoring, a fundamentally different paradigm from our pull-by-key probe(standard_no). It can discover standards you did not know existed; we structurally cannot",
      "INFERRED ONLY: 'supports any ICS category' suggests use of std_list's p.p6 (category) parameter, which our official_gb.py does not currently pass"
    ],
    "pitfalls": [
      "Page body NOT retrievable. All of these returned 404: /api/skills/<owner>/<slug>, /api/skill/<owner>/<slug>, /api/v1/skills/<owner>/<slug>, /api/download/<owner>/<slug>, /<owner>/<slug>/raw. HTML contains only JS bundle references with no SSR body",
      "The URL opened is the /security-audit page, which attests SECURITY (no privilege escalation, no credential leakage) - it does NOT attest functional correctness and does not guarantee reusable code exists",
      "Cannot determine whether it is a code-bearing Skill or a prompt-only Skill. Do not assume it is usable",
      "Hosted on a third-party Skill marketplace: no commit history, no stars, no issues, no forks - maintenance status is unknowable and sourcing is not auditable"
    ],
    "verification": "unverified"
  },
  {
    "name": "Law-Crawler-RPA-RAG-MCP",
    "repo": "https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP",
    "lang": "Python",
    "license": "MIT",
    "last_commit": "2026-04-28T08:01:33Z",
    "data_sources": [
      "config/known_urls.toml - curated seed direct-link table {name, url, source, aliases}, e.g. https://www.gov.cn/gongbao/content/2017/content_5230272.htm",
      "Search engines (config/anti_detection.toml): baidu_selenium (enabled, priority 1), bing_selenium (enabled, priority 2), baidu_requests (DISABLED, comment '反爬严重', https://www.baidu.com/s), duckduckgo (DISABLED, comment '连接超时', https://html.duckduckgo.com/html/)"
    ],
    "fetch_method": "httpx.AsyncClient as async context manager; tenacity @retry(stop_after_attempt, wait_exponential(multiplier, max=60)); self-implemented token-bucket _rate_limit() with random.uniform(0.5,1.5) jitter; fake_useragent UA rotation; Selenium with --disable-blink-features=AutomationControlled, window_size_random, disable_images, max_instances=2; proxy pool CONFIGURED BUT DISABLED ([proxy_pool] enabled=false, proxies=[])",
    "clean_method": "parse_date() tries 5 formats (%Y-%m-%d, %Y年%m月%d日, %Y.%m.%d, %Y/%m/%d, %Y-%m-%d %H:%M:%S) and warns + returns None rather than guessing; extract_law_type() by substring containment",
    "reusable": [
      "Curated seed-URL table with aliases: turns 'law name -> authoritative direct link' into a reviewable, community-contributable DATA file separate from code. Highly applicable to our govcn_announce/mohurd/mem_gov list pages: extract the few critical evidence-chain URLs so they stop depending on fragile list-page parsing",
      "tenacity exponential backoff capped at max=60 as a reference for adding retry to our channel layer (we currently have none - _fetch only normalizes exceptions)",
      "parse_date's 'try N formats, warn and return None instead of guessing' is consistent with our base.py _miss(note=...) philosophy",
      "Deliberately NOT copying: the rate-limit jitter sacrifices determinism and conflicts with our 'bit-for-bit reproducible' matrix requirement; our ndls.py PAUSE_S with mock-does-not-sleep is the better design"
    ],
    "pitfalls": [
      "proxy_pool is enabled=false with an empty list - the anti-detection config is decorative",
      "Dense anti-bot measures (AutomationControlled disabled, random window size, UA rotation, proxy slots) mean materially higher ban and compliance risk than other projects",
      "Author's own comments record that Baidu-via-requests is unusable ('反爬严重') and DuckDuckGo times out - do not retry these paths",
      "10.4 MB, crawler_manager.py is a 34 KB god object, developed with .cursor/rules/ - maintainability is mediocre",
      "It targets LAWS not STANDARDS; and for laws we already have the official flk.npc.gov.cn path in laws_db.py"
    ],
    "verification": "verified"
  },
  {
    "name": "legal-database",
    "repo": "(no single canonical repo found)",
    "lang": "n/a",
    "license": "n/a",
    "last_commit": "n/a",
    "data_sources": [],
    "fetch_method": "n/a",
    "clean_method": "n/a",
    "reusable": [],
    "pitfalls": [
      "gh api search/repositories?q=legal-database+in:name returns 5 same-named repos, ALL unrelated to regulatory/standards acquisition: sublatesublate-design/legal-database (Py, 5 stars, no description), Wilson-wour/legal-database, Alxrosen/legal-database, RLAN4/Legal-Database ('APM Legal Database' - project management), chiragalwani-EFI/Legal-Database (case tracker with OCR+Gemini - judicial, not regulatory)",
      "Fuzzy search also surfaced berkmancenter/lumendatabase (Lumen takedown DB), cc-archive/legaldb (case law), ciarrocki/LibreLaw (stale since 2020) - none is a regulatory/standards tool",
      "'legal-database' is too generic a name to be identifiable; likely copied from a second-hand list or refers to something private/unreleased"
    ],
    "verification": "broken"
  },
  {
    "name": "china-law-search",
    "repo": "(not found)",
    "lang": "n/a",
    "license": "n/a",
    "last_commit": "n/a",
    "data_sources": [],
    "fetch_method": "n/a",
    "clean_method": "n/a",
    "reusable": [],
    "pitfalls": [
      "in:name search returned ZERO hits. Fuzzy search returns only differently-named projects: abcddcbaxxxx/chinese-law-mcp, changpx/Lawdown, malnlda/legal-research, junpe2022/ChineseLawsSearch, law-star-cn/lawstar-mcp - none is called china-law-search",
      "Chinese legal retrieval is a red ocean; and we ALREADY have the official path: laws_db.py connects directly to https://flk.npc.gov.cn/law-search/search/list (National Laws and Regulations Database). Any third-party alternative is worse than our existing official interface"
    ],
    "verification": "broken"
  },
  {
    "name": "policy-monitor",
    "repo": "(not found)",
    "lang": "n/a",
    "license": "n/a",
    "last_commit": "n/a",
    "data_sources": [],
    "fetch_method": "n/a",
    "clean_method": "n/a",
    "reusable": [],
    "pitfalls": [
      "in:name search returns only IT/IAM policy monitoring, semantically unrelated: azure.policy.monitor (Bicep), ads-policy-monitor, Monitor-security-policy-changes-or-admin-activities, Windows-GroupPolicy-Monitor, bicep-azure-policy-monitoring",
      "Fuzzy search drags in ossec-hids (IDS), iamlive (cloud IAM), robinhood (filesystem policy engine) - completely off-topic",
      "web_search surfaced the actually-relevant S1998raghu/policy-alert-system (Federal Register + agentic LLM) and ONS-Innovation/github-policy-dashboard - but neither bears this name",
      "Very likely the name arrived without its original context (a summary page or an AI suggestion) and that context was lost"
    ],
    "verification": "broken"
  },
  {
    "name": "GovPing",
    "repo": "https://www.npmjs.com/package/govping-mcp-server (declared source repo https://github.com/changeflowhq/govping-mcp returns HTTP 404)",
    "lang": "unknown",
    "license": "MIT",
    "last_commit": "npm last published 2026-03-28T16:41:26Z (v1.0.3); declared GitHub repo does NOT exist (404)",
    "data_sources": [
      "None locally. npm description: 'GovPing MCP server - free regulatory intelligence for AI agents. Search 27,000+ regulatory changes across 2,000+ government sources. ORCA-structured data.' It is an MCP CLIENT to GovPing's hosted service; all collection happens server-side and is closed-source."
    ],
    "fetch_method": "Not obtainable (source repo 404). It does not fetch anything itself - it proxies a hosted API.",
    "clean_method": "Not obtainable. Claims 'ORCA-structured data' as a unified output schema - which is conceptually what our ChannelResult already does.",
    "reusable": [
      "Essentially nothing. The only transferable idea is the unification of heterogeneous regulatory sources into one schema - which we already implement via ChannelResult"
    ],
    "pitfalls": [
      "Declared source repo returns HTTP 404 -> depends on an unauditable closed-source service. For regulatory/standards work that demands traceability and evidence, this is disqualifying: our evidence_url contract requires clicking through to the original PDF, which a hosted service cannot guarantee",
      "Package exists but the repo is gone - the classic 'publish and abandon' pattern; if the service goes down the package becomes a brick",
      "'free' is marketing, not a license - quota and shutdown risk are undeclared",
      "Do NOT treat as a self-hostable component"
    ],
    "verification": "unverified"
  },
  {
    "name": "RegRadar",
    "repo": "(ambiguous - at least 6 same-named repos, no single authoritative one)",
    "lang": "Python / TypeScript (varies by repo)",
    "license": "Apache-2.0 (kingabzpro/RegRadar); others vary",
    "last_commit": "varies: Shivay00001 2026-09-10, sidnov6 2026-06-07, p-kowadkar 2026-05-27, McKnight108 2026-05-19, gssasank 2026-04-12, faytonn 2025-08-25, kingabzpro 2025-06-28, EvenSB1NM 2024-11-20",
    "data_sources": [
      "Cannot be stated: the referent cannot be identified, so attributing any one repo's implementation to 'RegRadar' would be fabrication. Descriptions indicate different jurisdictions: Shivay00001=India, gssasank=US Federal Register, sidnov6=EU EUR-Lex, kingabzpro=generic global"
    ],
    "fetch_method": "Not decomposed - referent unidentifiable",
    "clean_method": "Not decomposed - referent unidentifiable",
    "reusable": [
      "If the owner meant the EU-oriented dir, see scka-de/regwatch-eu instead (verified, Apache-2.0, real readable source, same EUR-Lex target)"
    ],
    "pitfalls": [
      "'RegRadar' is a recycled name: 8+ repos including a hackathon project and an unrelated weather-radar data-quality project (McKnight108/Regradar)",
      "Highest star count among candidates is 3 - all are intern/demo-grade; none is mature",
      "No candidate targets Chinese laws or standards",
      "The owner's 'unverified' flag was accurate, but the real problem is not existence - it is which one is meant"
    ],
    "verification": "unverified"
  },
  {
    "name": "regwatch-eu",
    "repo": "https://github.com/scka-de/regwatch-eu",
    "lang": "Python",
    "license": "Apache-2.0",
    "last_commit": "2026-03-29T21:30:30Z",
    "data_sources": [
      "POST https://publications.europa.eu/webapi/rdf/sparql with data={'query': <SPARQL>} and Accept: application/sparql-results+json, timeout 90s; query uses cdm: ontology, FILTER(?date > since^^xsd:date), FILTER(CONTAINS(LCASE(?title),'<keyword>') || ...), ORDER BY DESC(?date) LIMIT 200",
      "GET https://www.esma.europa.eu/rss.xml (RSS, parsed by feedparser, timeout 30s)",
      "src/regwatch/sources/eba.py (EBA, same shape)"
    ],
    "fetch_method": "httpx synchronous; each source wraps its own try/except, logging TimeoutException and HTTPStatusError separately and then RE-RAISING (errors are not swallowed); no retry, no proxy, no concurrency",
    "clean_method": "sources/_utils.py::strip_html() = re.sub('<[^>]+>',' ') then re.sub('\\\\s+',' ') (two lines, sufficient); sources/base.py is a typing.Protocol with a single method fetch(since: date, regulations) -> list[RawChange]; regulations/{dora,mica,ai_act,psd3,amld6}.py declare keyword tables reused as SPARQL filters; classifier.py categorizes changes; cache.py dedupes",
    "reusable": [
      "Find the official structured interface FIRST, then consider scraping: EUR-Lex exposes a public free SPARQL endpoint with a schema - this lesson outweighs any scraping trick",
      "Discover-type vs verify-type retrieval: filtering by title keyword CONTAINS rather than by known regulation id, because new versions and implementing rules have UNKNOWN ids. This is exactly the capability gap we have",
      "The minimal Source Protocol (one method, fetch(since, regulations) -> list[RawChange]) is a clean template for adding a parallel discover(since) protocol alongside our probe(standard_no)",
      "RSS first: prefer feeds over hand-written HTML parsers wherever a government site offers one; three-tier date fallback (<time datetime> -> 'DD Month YYYY' regex -> date.today() with a warning, never raising) keeps records flowing while leaving an auditable warning - consistent with our _miss(note=...)",
      "since is a first-class protocol parameter: an incremental water line turns our govcn_announce/mem_gov full scans into incremental pulls"
    ],
    "pitfalls": [
      "One-shot project: created and last pushed the same day (2026-03-29), 0 stars, no commits for 5.5 months - a portfolio piece, not a product",
      "Jurisdiction mismatch: EU/US financial regulation (DORA/MiCA/AI Act/PSD3/AMLD6), unrelated to the Chinese standards system - only methodology transfers",
      "feedparser.parse(response.text) applies no sanitization to feed content",
      "The date.today() fallback pollutes 'change date' semantics by recording the fetch date as the publication date",
      "No retry/backoff/concurrency: one timing-out source means one missing source"
    ],
    "verification": "verified"
  },
  {
    "name": "@sanmis/crawler",
    "repo": "https://www.npmjs.com/package/@sanmis/crawler (declared source repo https://github.com/TaxWise/taxwise returns HTTP 404)",
    "lang": "TypeScript (compiled to dist/cjs + dist/esm)",
    "license": "MIT",
    "last_commit": "npm v1.0.1; declared repo github.com/TaxWise/taxwise does NOT exist (404)",
    "data_sources": [
      "Not obtainable (source repo 404, tarball not expanded). npm keywords are the only available signal: crawler, scraper, web-monitor, information-sync, tax, education, social-security, government, rss, declarative, dsl, llm, playwright, policy-monitoring"
    ],
    "fetch_method": "Not obtainable. Keywords conservatively suggest Playwright browser automation + RSS + a 'declarative DSL' + LLM involvement, targeting tax/education/social-security/government (Chinese e-government), but this is INFERENCE, not source-verified.",
    "clean_method": "Not obtainable",
    "reusable": [
      "The declarative DSL direction is architecturally interesting for our channels/ directory: today every new site requires a hand-written ChannelAdapter subclass (ndls.py is 293 lines, cssn.py 10 KB). Externalizing 'URL template + selectors + field mapping' into declarative config would substantially lower the marginal cost of adding a channel. This is an ARCHITECTURE SUGGESTION, not a copyable implementation - the source is unavailable."
    ],
    "pitfalls": [
      "Declared source repo 404 - identical failure mode to GovPing: package published, repo gone",
      "394 files / 930 KB npm package with NO auditable upstream - unacceptable supply-chain and non-fixable-bug risk for a production data pipeline",
      "The '@sanmis' npm scope and the 'TaxWise' repo owner are different brands - provenance is suspicious",
      "Publishes dist/ build artifacts (main: ./dist/cjs/index.js) with no provable correspondence to any source"
    ],
    "verification": "unverified"
  },
  {
    "name": "at-ris-mcp",
    "repo": "https://github.com/paragraflabs/at-ris-mcp",
    "lang": "Python",
    "license": "Apache-2.0",
    "last_commit": "2026-07-25T07:08:24Z",
    "data_sources": [
      "https://data.bka.gv.at/ris/api/v2.6/ - Austrian RIS official OGD API, documented as KEYLESS (no API key)",
      "Collections: Bundesrecht (BrKons consolidated, BgblAuth gazettes, Begut drafts, RegV), Landesrecht (9 states, LrKons), Judikatur (OGH/VfGH/VwGH/BVwG/LVwG), Erlaesse/Avsv, Bezirke/Bvb, Gemeinden/Gr/GrA",
      "Change/early-warning feed: ris_list_changes -> RIS History, which is SOAP (fixtures/history_bundesnormen_soap.xml)"
    ],
    "fetch_method": "httpx client (src/ris_client/client.py) with dedicated cache.py, ratelimit.py and errors.py; MCP layer src/ris_mcp/server.py is a thin FastMCP/stdio wrapper ('Contains no logic of its own') with optional streamable HTTP or SSE transport",
    "clean_method": "textparse.py strips RIS HTML to clean Markdown; README quantifies the problem: approximately 40 KB of CSS boilerplate PER DOCUMENT must be discarded, with a raw switch to bypass. Section-precise retrieval of a single §/Artikel/Anlage via Abschnitt.* parameters; historical version via Fassung.FassungVom (the law as it stood on a given date); citations.py handles ELI/ECLI; output selectable among markdown|html|xml|raw",
    "reusable": [
      "fixtures/ golden-sample directory (brkons_search.json 18KB, justiz_search.json 25KB, case_text.html 99KB, history_bundesnormen_soap.xml 22KB) directly serves our offline-testability requirement - our ndls.py mock contract is inlined in a docstring, whereas storing real responses as fixture files is far better for regression comparison",
      "reference/ ships the official XSD request schemas (OGD_Bundesrecht_Request.xsd etc.) - the model habit of reading the official schema before writing a client",
      "ratelimit.py as a standalone module rather than scattered per-source (our ndls.py PAUSE_S is a class attribute while proxy_rotate.py has its own scheme - consolidating into one base.py rate-limit layer is cleaner)",
      "The 40 KB CSS boilerplate lesson applies directly to us: our mem_gov.py / mohurd.py announcement pages stuff whole-page HTML into raw, polluting downstream text. Quantify the boilerplate ratio before choosing an extraction strategy",
      "BrKons (consolidated, currently-effective text) vs gazette novellas is a jurisdiction-general insight - to get 'the currently effective text' you must take the consolidated version, not reconstruct it from gazettes",
      "Fassung.FassungVom as-of-date snapshots reveal that our ChannelResult lacks as-of semantics, a real gap for 'which version was in force when the incident happened' forensics"
    ],
    "pitfalls": [
      "Jurisdiction mismatch: Austrian RIS, unrelated to the Chinese standards/regulatory system - methodology only",
      "1 star, created 2026-07-24 and first pushed 2026-07-25, 211 KB - a personal project, not a community one",
      "Depends on the official API's stability; reference/*.xsd will age (though keeping the schema at all is good practice)",
      "ris_list_changes uses SOAP - an operational burden in modern Python; not recommended for our own pipeline"
    ],
    "verification": "verified"
  },
  {
    "name": "standards-version-check",
    "repo": "https://github.com/cuipointer/ageis (skill at .claude/skills/standards-version-check/SKILL.md)",
    "lang": "Python",
    "license": "unknown (GitHub API reports null; no LICENSE found at repo root)",
    "last_commit": "2026-05-09T01:16:43Z",
    "data_sources": [
      "knowledge/standards/index.yaml - the authoritative local version source",
      "Feishu sheet TZRlsqLL8hG4I2t7DDFc968QnPg (hardcoded SHEET_TOKEN) - the raw version source",
      "The ACTUAL fetch action in tools/build_standards_index.py is: subprocess.run(['feishu','sheet','read',SHEET_TOKEN,f'{sheet_name}!A1:J100']). It scrapes NO standards website. The only networked component is the Feishu CLI."
    ],
    "fetch_method": "subprocess call to the external 'feishu' CLI with a hardcoded SHEET_TOKEN; no HTTP client, no retry, no proxy",
    "clean_method": "Slice JSON from CLI stdout via raw.find('{')/raw.rfind('}') then json.loads; FORWARD-FILL MERGED CELLS (last=['']*12; if cells[j]: last[j]=cells[j] else cells[j]=last[j]); _cell() tolerates None and rich-text list[{'text':...}]; _url() extracts from rich-text link structures [{'type':'url','link':...}]; status model richer than ours: current / current_no_version (version column blank means current-but-unversioned, deliberately NOT unknown) / superseded / unknown / needs_verification; extras.yaml merged with setdefault so it only fills gaps and never overrides the sheet; extras aliases.non_standard_refs whitelists strings that look like standard numbers but are not",
    "reusable": [
      "Forward-fill of merged cells (6 lines) - Chinese government announcement tables in our mem_gov.py / mohurd.py / govcn_announce.py commonly use merged cells; this belongs in base.py as a shared helper",
      "_url() rich-text URL extraction is the standard shape for Feishu/WeCom/DingTalk APIs should we ever integrate a collaboration platform",
      "current_no_version and needs_verification reveal that 'current but version unknown' is a distinct state that should not be collapsed into effective or None. Combined with 暂不实施 (OpenSTD_Spider), 有更新版 (gb688_downloader) and ndls.py's 未生效/作废/废止转行标/已修订, our state-enum gap is systemic, not a one-off",
      "--diff uses the exit code as the change signal (return 1 if added or removed or version_changed else 0) so cron/CI can gate on it directly",
      "'Report but never auto-commit' discipline (SKILL.md step 3: do not auto-update index.yaml to avoid unreviewed content entering the store) mirrors our recordable() refusal to persist captcha results",
      "Quarterly cadence (cron 0 9 1 */3 *) - standards re-verification is inherently quarterly, not per-minute",
      "cmd_audit cross-checks matrix.yaml references against index.yaml and keeps only standard-looking tokens via a regex allowlist - a reference-integrity audit we could adopt; extras non_standard_refs is the low-cost fix for our own norm_no()/STD_CODE_RE false positives"
    ],
    "pitfalls": [
      "It is a version CHECKING tool, not a data ACQUISITION tool. Its advertised function rests entirely on a human-maintained Feishu table. Expecting it to fetch standards for you is a category error",
      "Hardcoded Feishu token (and source_doc id) - unusable across organizations",
      "Depends on an external 'feishu' CLI not declared in requirements; breaks on any other machine",
      "0 stars, no license field; the repo is a personal EMC/RSE certification knowledge base (knowledge/standards/{ce,fcc,ccc}/ holds EN301489/CISPR/FCC Part 15) - it overlaps with our topic only on the word 'standards'",
      "Important lesson: this Skill DOES contain real code (tools/standards_tool.py 12 KB, build_standards_index.py 9.5 KB), so 'it is a Skill' does NOT imply 'no code'; but gbqw proves 'has code' does NOT imply 'useful'. Every entry must be opened individually"
    ],
    "verification": "verified"
  }
]
```

---

## 21. 方法学备忘（可复现）

```bash
# 1) 存在性 & 元数据（不改任何仓库）
gh api "repos/<owner>/<repo>" --jq '{full:.full_name,lang:.language,lic:.license.spdx_id,pushed:.pushed_at,created:.created_at,stars:.stargazers_count,archived:.archived,size:.size}'

# 2) 文件树（挑要读的文件，不 clone）
gh api "repos/<owner>/<repo>/git/trees/HEAD?recursive=1" --jq '.tree[]|select(.type=="blob")|"\(.size)\t\(.path)"'

# 3) 读源码正文（raw，全在内存里）
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>"

# 4) 精确名搜索（判"查无此物"）
gh api "search/repositories?q=<name>+in:name&per_page=5" --jq '.items[]|"\(.full_name) | \(.language) | \(.pushed_at)"'

# 5) npm 包存在性（判"包在仓没"）
curl -s "https://registry.npmjs.org/<pkg>"      # scoped 包要 URL-encode 成 @scope%2Fname
```

- 全程**未 `git clone`**、**未写入任何被调研仓库**；唯一写入是本文件 `docs/research/channels/oss-decomposition.md`。
- 耗时最大的三处：`changedetection.io`（46 MB，需精选模块）、`GBMCP`（`server.py` 41 KB + `service.py` 43 KB + 15 个 source）、`gb688_downloader`（小但每个文件都藏着接口）。
- **未验证项已逐条标注**，未做任何推断性陈述（唯一的推断在 §8 与 §16，且均显式标注"**INFERRED / 未被验证**"）。
