# 法律法规官方来源获取方案（flk.npc.gov.cn + gov.cn）

> 状态：方案（2026-08-24 制定，待确认后实施）
> 关联：docs/ENCYCLOPEDIA.md（单一事实源台账）；替代原"law-text://inline 纯文本直灌"路线的后续扩展。

## 0. 目标与原则

1. **来源白名单**：法律法规只从两个官方源获取——
   - 国家法律法规数据库 `https://flk.npc.gov.cn/`（法律/行政法规/监察法规/司法解释/地方性法规，全国人大主办）
   - 国务院政策文件库 `https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm`（搜索后端 `https://sousuo.www.gov.cn/search-gov/data`）
   - 任何其他域（含各类"法规文字版"小站）一律拒绝。
2. **下载带格式 Word → 转 PDF**：以官方发布的 docx（带章/条/款层级、表格、正式版式）为唯一内容源头；转换出的 PDF 走现有标准件管线，预览/高亮/目录/编辑器/条款修正与国标完全同构。
3. **通用彻底**：不是逐部抓取的一次性脚本，而是「来源适配器」架构——任何法规/政策文件都能按关键词、文号、分类、机关检索→下载→入库；存量 `law-text://inline` 文档可一键从官方源重建为"有 PDF 原件 + 有 bbox"的标准文档。
4. **可追溯**：每份文件记录来源 URL、bbbs/文号、下载时间、内容哈希、时效状态。

## 1. 来源一：国家法律法规数据库 flk.npc.gov.cn

官方公开 API（无需登录/认证；接口状态已按 2026-06 实测核实）。

| 用途 | 接口 | 说明 |
|---|---|---|
| 分类/机关/时效枚举 | `GET /law-search/search/enumData` | 下拉字典（flfgCodeId / zdjgCodeId / sxx 等叶子 code） |
| 首页聚合 | `GET /law-search/index/aggregateData` | 分类计数、最新公布（更新检查用） |
| 搜索 | `POST /law-search/search/list` | JSON body，见下 |
| 详情 | `GET /law-search/search/flfgDetails?bbbs={id}` | 元数据 + 章/条结构化 content.children + ossFile 路径 |
| 命中展示 | `POST /law-search/search/hitDisplay` | 关键词命中法条片段 |
| 下载链接 | `GET /law-search/download/pc?format=docx\|pdf&bbbs={id}` | 返回签名 OSS URL（`data.url`），用其下载真实文件 |
| 批量下载 | `POST /law-search/download/batch` | `{"ids":[...]}` |

搜索 payload（已实测可用的结构）：

```json
{
  "searchRange": 1,          // 1=标题, 2=正文
  "searchType": 2,           // 1=精确, 2=模糊
  "searchContent": "消防法",
  "flfgCodeId": [],          // 分类叶子 code（enumData）
  "zdjgCodeId": [],          // 制定机关叶子 code
  "sxx": [],                 // 时效：3=有效
  "gbrq": [], "sxrq": [],    // 公布/施行日期区间 [start,end]
  "gbrqYear": [],
  "orderByParam": {"order": "-1", "sort": ""},   // sort: gbrq/sxrq/sxx/flxz/zdjg
  "pageNum": 1, "pageSize": 20                    // pageSize ≤ 100
}
```

详情响应要点：`title` / `flxz`（分类）/ `zdjgName`（机关）/ `gbrq`（公布日期）/ `sxrq`（施行日期）/ `sxx`（时效，3=有效）/ `ossFile`（ossWordPath / ossPdfPath / OFD）/ `content.children`（**章→条结构化**，可直接生成目录树）。

下载注意：
- 一律走 `download/pc` 接口拿签名 URL，**不要**直接拼 `ossFile` 路径（实测会返回 SPA 首页）。
- `format=pdf` 对部分法规返回 `code:200` 但 `data` 为空（无官方 PDF）→ **自动回退 docx**（我们本来就要 docx→PDF 自转，所以主请求 docx 即可）。
- 请求头：浏览器 UA + `Referer: https://flk.npc.gov.cn/detail?id={bbbs}`。

限速：≥0.5s/请求（参考社区官方 API 客户端惯例），失败指数退避重试（最多 3 次）。

### 1.1 ⚠ 反爬挑战页：HTTP 200 + HTML（2026-10-10 实测，本仓已修）

**症状**：连续请求到某个量之后，接口**不再返回 JSON**，而是返回
**`HTTP 200` + `Content-Type: text/html`** 的一页
「Please enable JavaScript and refresh the page.」——**不是** 4xx/5xx。

**为什么这个形状特别坑**：`raise_for_status()` 会**放行**（200），
只有 `resp.json()` 抛 `JSONDecodeError` ⇒ 挑战被当成"普通网络错误"，
用亚秒退避重试 ⇒ **必然失败**，而错误信息里看不出"是被挡了"。

**实测读数**（2026-10-10，本机）：

| 实验 | 结果 |
|---|---|
| 每 0.6s 一页连打 | 第 **33** 页起被挡 |
| 被挡后等 60s 再试 | **1 分钟内自愈** |
| 带自适应退避（失败退避 20–120s）连打 **120** 页 | **0 次被挡** |
| 换全浏览器头（Sec-Fetch-*、Origin、Accept-Language） | **无效**（照样被挡） |
| 换 GET 首页预热（std-law-watch 记的"坑 1"） | **无效** |
| 直连 vs 走本机代理 `127.0.0.1:7897` | **一样被挡**（与代理无关） |

⇒ **判读**：这是**突发限速**（可变阈值、分钟级自愈），不是封 IP、不是头指纹问题。
**唯一有效的对策是拉长退避**，不是换头、不是预热、不是绕代理。

**本仓的修法**（`src/core/knowledge/law_source/http.py`）：
- 新增 `AntibotChallenge`（RuntimeError 子类）+ `_looks_like_antibot()`
  —— **判据以 `Content-Type` 为主**：`fetch_json` 的契约就是"拿 JSON"，
  所以**声明不是 JSON 的响应**本身就说明没拿到数据，一律走长退避重试；
- 反爬退避常量 `_ANTIBOT_BACKOFF = (5.0, 20.0, 45.0)`、`_ANTIBOT_TRIES = 4`
  —— 亚秒退避对"分钟级自愈"的挑战无效。

⚠ **第一版判据只查特征串**（`"Please enable JavaScript"`），实测**漏判**：
站点有时返回**另一种** HTML 页（正文里没有该串）⇒ 已改成 Content-Type 优先。

**取证**：`specs/006-law-catalog-refresh/research.md` R6；
测试 `tests/test_law_source_http_antibot.py`（含变异验证）。

### 1.2 接口事实（来自 `D:/AI/std-law-watch` 独立项目，**非本仓实测**）

以下四条来自另一个 Agent 建的 `D:/AI/std-law-watch`（2026-10-10），
**本仓未逐条复验**，登记备查——官方改版时能省一次重新摸索：

| # | 事实 | 说明 |
|---|---|---|
| 1 | **`POST /law-search/highSearch/highSearch`** | 该项目的**主力**高级检索端点。本仓**未使用**（本仓用 `search/list`），两者请求体形状不同 |
| 2 | **翻页 offset 上限 30,000** | `(pageNum-1)*pageSize >= 30000` ⇒ `{"code":500,"msg":"系统异常"}`。该项目实测 size=500 卡 page 60、size=100 卡 page 300、size=50 卡 page 600，**三种都恰好 30000**。⇒ 空条件直拉只能拿 29,992/30,910。⚠ **本仓 `catalog.py` 的分片策略（按叶子分类）不受此限**——实测各叶子分类 total 之和 = 30,909 ≈ 空条件 30,910 |
| 3 | **`flfg_code_id` / `zdjg_code_id` 传的是 `codeId` 不是 `id`** | 分类树里是 `{"id":14,"name":"行政法规","codeId":210}`；传 `id` ⇒ 0 条，传 `codeId` ⇒ 正确。⚠ 本仓 `catalog.py` 的 `_CODE_KEYS` 已含 `codeId` 优先 |
| 4 | **发文字号藏在详情接口的 `xgzl`（相关资料）里** | 列表接口**没有** `doc_no` 字段；详情返回 `xgzl: [{"fileId":...,"title":"中华人民共和国国务院令第847号","busiType":"国务院令","fileType":"docx"}]`。⇒ 要补文号只能逐条查详情 |

**另外两条本仓已用上的**（同源发现，本仓已实现）：
`sxx` 时效枚举（1废止/2已修改/3有效/4尚未生效）、`lsyg` 历史沿革（历次版本链）。

### 1.3 ★ flk 全文下载：**已实测仲裁 = 能下**（2026-10-10 收口轮）

**⚠ 三个来源曾给出互相矛盾的结论，本节把仲裁结果定下来。**

| 出处 | 原结论 |
|---|---|
| 本仓 `flk_client.py` 注释 | 「签名下载 URL（**主路径**，勿拼 ossFile）」 |
| 本仓 `docs/ENCYCLOPEDIA.md` | 「实测返回 SPA 首页」 |
| `std-law-watch` §6.7 | 「**有证据的判死**」：签名绑内网 + 桶非公开 + `permission.download=0` |

#### 实测（判据写在脚本 docstring，跑前定死）

**判据**：能下 = 响应体魔数是 docx（`PK\x03\x04`）或 pdf（`%PDF`）且体积 > 10KB；
再把 docx 真存盘，验证它是**可打开的 OOXML**（`zipfile` 能开 + 含 `[Content_Types].xml`
+ 含 `word/document.xml` + 能抽出中文正文 > 200 字）。

**读数**（`probe-download-pc.json` / `probe-download-verify.json`）：

| bbbs | format | `download/pc` | 下载 | 魔数 | 体积 | 判定 |
|---|---|---|---|---|---|---|
| 包头市水资源管理条例（2024 版） | docx | `code:200` 成功 | 200 | `504b0304` | 19,715 B | **DOCX_OK** |
| 同上 | pdf | `code:200` **无 url** | — | — | — | 无官方 PDF（按设计回退 docx） |
| 包头市水资源管理条例（2026 版） | docx | `code:200` 成功 | 200 | `504b0304` | 19,165 B | **DOCX_OK** |
| 同上 | pdf | `code:200` **无 url** | — | — | — | 无官方 PDF |
| 绍兴市大气污染防治条例（2026 版） | docx | `code:200` 成功 | 200 | `504b0304` | 21,756 B | **DOCX_OK** |
| 同上 | pdf | `code:200` 成功 | 200 | `25504446`(`%PDF`) | 283,626 B | **PDF_OK** |

**docx 真实性深验**（落盘 `var/tmp/flk-dl-check/sample.docx`，19,715 B）：

```
is_zip=True   has_content_types=True   has_document_xml=True
entries=18    text_len=3758（可读中文正文）
```

#### ⇒ 仲裁结论

**flk 全文能下。** 路径是 `GET /law-search/download/pc?format=docx|pdf&bbbs=`
→ 拿 `data.url`（签名 OSS，host `flkoss.obs-bj2.cucloud.cn`）→ 直接下载。
本仓 `flk_client.download()` 的实现（走 `download/pc` 拿签名 URL）**是对的**；
`ENCYCLOPEDIA.md` 那句「实测返回 SPA 首页」**不成立**。

**⚠ 仍未解释的部分（不装作已查清）**：
`std-law-watch` 记的三条反证（签名绑**内网**主机 `…-internal.cucloud.cn`、
OBS 桶直连 403、`permission` 字段 `download:0`）本轮**没有逐条复现**。
可能的解释是**它当时拿的是不同格式/不同 bbbs 的返回**，或**站点在此期间改了**——
**两种都可能，本轮证据不足以判定是哪一个**。
⇒ 本节只对**当前实测**负责：**今天、这三个 bbbs、docx/pdf 都能下**。

**对渠道台账的影响**：flk **应记 `ok`（全文可下）**，不是 `index-only`。

**覆盖率抽样**（`probe-download-coverage.json`，2026-10-10）：
从真库 30,953 条里随机抽 **40** 条（seed 固定可复现），逐条探测
`download/pc?format=docx` 是否返回非空 `data.url`（**只探测、不真下载**）：

```
有效探测 40 / 40（0 失败）   有 url 40 / 无 url 0
覆盖率点估计 = 100.0%   95% Wilson CI = [91.2%, 100.0%]
```

⇒ 台账现状**本来就对**：`ch:laws_db` 的 `state=ok`（2026-10-10 查真库确认），
**没有被误记成 `index-only`** ⇒ **无需改动**。

⚠ **这是抽样估计，不是全量**（40 / 30,953 ≈ 0.13%）。
区间下界 91.2% 意味着真实覆盖率可能低到九成——**但没有证据说它低**。
要坐实到全量需 3 万次请求（会触发限速），**不值当**。

## 2. 来源二：国务院政策文件库 gov.cn

搜索后端（公开，无需认证）：

```
GET https://sousuo.www.gov.cn/search-gov/data
```

| 参数 | 取值 | 说明 |
|---|---|---|
| `t` | `zhengcelibrary` | 政策文件库主题 |
| `q` | 关键词 | 必填 |
| `searchfield` | `title` / `content` | 标题 / 全文 |
| `sort` / `sortType` | `score` / `pubtime` | 相关度 / 时间 |
| `p` / `n` | 0 基页码 / 每页数 | 分页 |
| `childtype` | `gongwen` / `bumenfile` / `otherfile` | 国务院文件 / 部门文件 / 解读 |
| `pubtimeyear` | `2024` | 年份过滤 |
| `bmfl` | `国家发展和改革委员会` | 部门过滤 |
| `pcodeJiguan` / `pcodeYear` / `pcodeNum` | 文号 | 按文号精确定位 |
| `mintime` / `maxtime` | 日期 | 时间区间 |

响应：`searchVO.totalCount` + `catMap[type].listVO[]`，每项含 `title`、`pcode`（文号，如"国办发〔2022〕35号"）、`source`（发文机关）、`pubtime`、`piclinksurl`（**详情页 URL**）。

详情页（`https://www.gov.cn/...`）HTML 解析：
- 标题：`h1` / `.article-title`；正文：`.article-content` / `.pages_content`；日期、来源。
- **下载链接解析**：抓页面内 `a[href]` 中以下载扩展名结尾的官方文件链接（`.docx` / `.doc` / `.ofd` / `.wps`）→ 官方 Word 文件直链。
- 兜底：若详情页确实无下载链接（部分网页发布件），用正文 HTML 经 python-docx 生成 docx（保留段落层级），`meta.json` 标记 `content_origin: "web"`，仍记录官方来源 URL——**但绝不从第三方站取文字**。

限速：搜索 API 公开；详情页抓取 ≥1s/请求 + UA + 重试。

## 3. Word → PDF 转换（保留带格式版式）

转换器优先级（均可配置，自动探测）：

1. **LibreOffice headless（推荐主方案）**
   ```
   soffice --headless --convert-to pdf:writer_pdf_Export --outdir <out> <input.docx>
   ```
   批量、无 GUI、保真（中文字体跟随系统）；本机当前未装 → 一次性安装：
   `winget install TheDocumentFoundation.LibreOffice`（或官网安装包）。
2. **WPS COM 回退（本机已具备）**
   本机已装 WPS（docx 默认关联 `WPS.Docx.6`）。`pip install pywin32` 后：
   `win32com.client.Dispatch("KWPS.Application")` → `Documents.Open` → `ExportAsFixedFormat`（或 `SaveAs` 到 PDF）。
   WPS 安装路径从注册表 App Paths / `HKCU\...\FileExts\.docx\UserChoice` 探测。
3. **Word COM**：若探测到 MS Word 亦可用（`Word.Application`），作为第三回退。

**硬性规则：转换源头只能是官方 docx**；任何"网页文字版 → 排版 PDF"的路径都不允许（违背带格式原则）。

## 4. 条款文本与章结构（单一数据源）

- **结构骨架来自官方 docx 解析**（python-docx，已装 1.2.0）：
  标题段落（章/节，按 Heading 样式或大纲级别）→ 条款段落（"第X条"）→ 款/（一）（二）子项 → 表格 → 生成**章/条/款层级 + content_markdown（含表格）**。
- **正文与高亮来自转换 PDF**：走现有 `run_full_ingest` 管线（MinerU 解析）→ bbox + 文本 + 目录；与标准件完全同构 → PDF 预览、条款高亮、目录树、编辑器修正、WPS 回填全部复用既有链路。
- **对齐合并**：docx 结构树 与 MinerU 文本以「条款号」为权威键对齐（docx 结构为准，MinerU 文本补正文与 bbox）；不一致时记录到导入报告供人工复核。
- 由此 `law-text://inline` 不再需要新增——法规文档升级为"有 PDF 原件 + 有 bbox + 有章结构"的标准形态。

## 5. 入库与数据模型

- `doc_meta` 字段策略：
  - `file_path` → 转换 PDF 绝对路径（不再是 `law-text://inline`）
  - 新增：`source`（`flk` / `govcn`）、`source_id`（bbbs / 文号）、`source_url`、`downloaded_at`、`source_status`（flk `sxx`）
- 分类：flk 的 `flxz` / `zdjgCodeId` → 现有「L1 法律法规 → L2 效力等级 → L3 领域」树（`classify_document` 增加 flk 分类映射表；govcn 按 `childtype` + 机关映射）。
- 幂等：`source_id` 唯一；重复导入走 reingest 语义（先删旧文档再插入），绝不产生 UNIQUE 冲突或双份。
- 文件落盘：`<data_dir>/law_source/<source>/<source_id>/原始.docx + 转换.pdf + meta.json`。

## 6. 更新与变更检测

- **手动增量**：运维面板/脚本按关键词或「最近公布」拉取（flk `aggregateData` 最新列表；gov.cn `sort=pubtime` + `pubtimeyear`），与库内 `source_id` 比对 → 只提示新增/变更。
- **时效变更**：flk 详情 `sxx`（已修改/已废止）+ `xgwj`（相关文件）→ 提示用户重导最新版。
- **版本追溯**：`meta.json` 记录下载时间 + 内容哈希；重导时旧版本目录归档保留（`law_source_meta` 表或目录归档）。

## 7. 合规与安全

- 法律法规不适用著作权法保护（《著作权法》第五条）；官方公开渠道下载仅供本地个人研究，非商业用途。
- 只访问白名单域；下载文件校验：docx 必须为 ZIP 且含 `word/`，PDF 以 `%PDF` 开头；异常文件拒绝并告警。
- 控制请求频率（≥0.5s/请求），避免影响官方服务；失败退避重试。
- 每份入库文件记录 `source_url` + `downloaded_at`，全程可溯源。

## 8. 实施步骤（分阶段，待确认后执行）

| 阶段 | 内容 | 验收 |
|---|---|---|
| P1 核心抓取 | `src/core/knowledge/law_source/`：`flk_client.py`（搜索/枚举/详情/下载）、`govcn_client.py`（搜索/详情/下载链接）、`convert.py`（LibreOffice→WPS COM→Word COM 探测链）、`ingest.py`（docx 结构解析 + 调 `run_full_ingest`） | 命令行按关键词抓 1 部法：官方 docx 落盘 → PDF 生成 → 条款/章结构入库 → 预览高亮可用 |
| P2 接口与 UI | 运维面板「法规抓取」表单（关键词/文号/分类 → 候选列表 → 勾选导入）；`POST /api/v1/laws/fetch`（dry-run 搜索 + 确认导入） | 前端全程可操作，无命令行 |
| P3 存量重建 | （已完成，2026-08-24：7 部 `law-text://inline` 文档已从官方源重导为带 PDF 版本；一次性脚本 `scripts/reingest_laws.py` 已随冗余清剿删除） | 7 部全部有 PDF 预览 + 高亮 + 章结构 |
| P4 更新检查 | 接入更新检查批次（`law_source` 增量 + 时效变更提示） | 运维面板能报"新增/已修改/已废止" |

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| 官方接口变更 | 所有请求收敛在 `law_source/` 单模块；接口探测步骤文档化（DevTools 抓包法，见附 A） |
| 本机无 LibreOffice | 安装指引；WPS COM 回退（本机已有） |
| docx 版式与 MinerU PDF 版式差异 | 结构以 docx 为准、bbox/正文以 MinerU 为准，按条款号对齐；差异进导入报告 |
| flk 部分法规无官方 PDF | 无影响——我们本来就 docx→PDF 自转 |
| 抓取频率过高被封 | ≥0.5s 限速 + 退避 + 批量下载走 `download/batch` |

## 附 A：接口探测方法（官方站点改版后自救）

1. 浏览器打开 flk/gov.cn 页面 → F12 → Network → 执行搜索/点下载。
2. 过滤 Fetch/XHR，找到 `list` / `flfgDetails` / `download/pc` / `search-gov/data` 请求。
3. 右键 → Copy as Fetch → 在 Console 重放验证 → 更新 `law_source/` 客户端。
4. 对照本方案的 payload/参数表逐字段核对，变更点记入 ENCYCLOPEDIA 台账。

## 附 B：中国官方标准渠道全景（2026-08 四队并行调研，web_search 查证 + 官方页面实测）

> 认知纠偏：**openstd.samr.gov.cn 只有国家标准**（强制 GB/推荐 GB/T/指导性 GB/Z/外文版）。
> "国标+行标+地标+团标+企标+计划都有"的是 **std.samr.gov.cn 全国标准信息公共服务平台**
> （主管：市场监管总局/国家标准委；主办：国家标准技术审评中心，京ICP备18022388号-1）——
> 门户按门类导航到各子平台。均无公开 REST API；公告页/列表页/详情页为静态 HTML 可抓。

| 门类 | 官方渠道 | 主办 | 查状态 | 看全文 |
|---|---|---|---|---|
| 国标全文 | openstd.samr.gov.cn | 审评中心 | 部分 | ✅ 强制+非采标推荐免费（2025-02 起，发布 20 工作日内公开；采标仅题录） |
| 国标状态权威 | std.samr.gov.cn（/noc 公告 + /gb/gbProcessInfo 计划查询） | 审评中心 | ✅ 现行/废止/计划 | ✅ |
| **跨门类一站式** | **ndls.cnis.ac.cn 国家数字标准馆** | 中国标准化研究院 | ✅ **详情页直接标废止日期/代替关系** | 部分需登录 |
| 行业标准 | hbba.sacinfo.org.cn（备案/月报）+ std.samr.gov.cn/hb/hbQuery（行标目录） | 审评中心 | ✅ 备案/目录 | 部分 |
| 地方标准 | dbba.sacinfo.org.cn（备案状态）+ 省级平台（广东 bz360.org.cn、浙江 zlzx.zjamr.zj.gov.cn、山东 dzzz.amr.shandong.gov.cn、江苏 scjgj.jiangsu.gov.cn） | 审评中心/省局 | ✅ | 省级多数可看 |
| 团体标准 | ttbz.org.cn（T/××× 详情页现行/废止 + 自我声明公开预览） | 中国标准化研究院 | ✅ | 部分 |
| 企业标准 | qybz.org.cn | 审评中心 | ✅ | 公开 |
| 工程建设（GB 50/55 号段） | **mohurd.gov.cn 标准公告**（37 本强规全文 PDF 直连，URL 结构稳定）+ gov.cn 政策库转发 + 国标电子书库 ebook.chinabuilding.com.cn（需注册） | 住建部 | 靠公告 | ✅ 强规 |
| 应急管理（AQ） | mem.gov.cn（/fw/flfgbz/bz/bzwb/ 标准文本 + /gk/zfxxgkpt 废止公告） | 应急管理部 | ✅ 废止一手依据 | ✅ AQ 全文 PDF |
| 工信（YB/JB） | miit.gov.cn/jgsj/kjs/jscx/bzgf/（报批公示）；ythzxfw.miit.gov.cn（服务入口） | 工信部 | 部分 | ❌ 无统一全文库 |
| 能源（NB） | nea.gov.cn/ztzl/nybz/（公告）+ bz.creei.cn:8888（水电全文） | 能源局 | ✅ | ✅ 水电 |
| 生态环境（HJ） | mee.gov.cn/ywgz/fgbz/bz/ | 生态环境部 | ✅ 按号/名称查 | ✅ PDF |
| 交通（JT） | jtst.mot.gov.cn（文本/计划）+ xxgk.mot.gov.cn（公告） | 交通运输部 | ✅ | ✅ |

**实测发现（巡检相关）**：AQ 3028-2008《化学品生产单位受限空间作业安全规范》已被应急管理部
2024 年第 3 号公告"公告即废止"，国家数字标准馆标废止日期 2024-07-01——巡检"查无"根因可能是
标准已废止而非渠道缺失。ndls 是唯一跨门类且直接给废止日期的官方库，最适合接入时效巡检。

**推荐接入巡检优先级**：① ndls.cnis.ac.cn（跨门类状态+废止日期，免登录）② std.samr.gov.cn
（/noc + /hb/hbQuery，国标/行标状态权威）③ 部委公告（mem.gov.cn / mohurd.gov.cn / nea.gov.cn，
废止/发布一手依据；工程建标补住建部）。
