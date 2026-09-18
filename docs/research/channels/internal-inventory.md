# 内部渠道拆解（internal inventory）

> 用途：业主"法规标准巡检要覆盖尽可能多官方渠道 + 前端看每渠道的链接/有效性/上次成功查询"，
> 本文件是**统一渠道台账设计**的输入。**只读式拆解**：所有结论均带 `文件:行号` 证据，
> 代码里读不出来的（真实响应形状、线上可用性）一律写"未实测/未确认"，不猜。
>
> 拆解日期基准：以仓库当前工作树为准（`src/core/update/channels/*`、`src/core/update/inspector.py`、
> `src/core/update/announce.py`、`src/core/knowledge/law_source/*`）。
>
> **一句话结论先行**：注册在 `ADAPTER_CLASSES` 的适配器有 13 个，但巡检降级链
> （`routing.select_chain`）只会走到其中 **8 个**；而这 8 个里的 `web`、`govcn` 两个
> "兜底棒"在代码路径上只识别 mock 用的 dict 契约，**真实 HTTP 响应下恒为 miss**（见 §1.2 / §1.3）。
> 也就是说：今天巡检的真实取数能力 ≈ 权威渠道 + `official_gb`，兜底链是空的。

---

## 0. 阅读本文件需要的三条结构事实

> ⚠ **2026-09-18 更新（R5c/R6b 之后，本节原文已部分过期；原文保留在下面不删）**
> - 第 1 条里提到的遗留常量 **`inspector.CHAIN` 已被删除**（§11.0 R6b）：它当时确实在
>   `inspector.py:62`，但它与 `routing._FALLBACK` 是同一件事的两份；现在链的**唯一所有者**是
>   `routing.fallback_chain()`（返回同一个 tuple 对象），`inspector._FALLBACK_CHAIN` 向它取。
> - 第 1 条末尾的 `_FALLBACK = ("official_gb", "web", "govcn")` 也已过期：**`web` 已于 R5c
>   从链上摘除**（实测只解 mock 的 dict、打的是 bing HTML ⇒ 真实网络恒 miss），
>   现在是 `_FALLBACK = ("official_gb", "govcn")`。
> - 第 2、3 条今天仍然成立。

1. **降级链不是写死在 inspector 里的**。`inspector.CHAIN`（`inspector.py:62`）是遗留常量；
   真正决定走哪些渠道的是 `inspector._probe_number` 里的 `select_chain(no)`
   （`inspector.py:342-343`），链由 `routing.select_chain` 生成（`routing.py:34-48`）。
   无特征命中时返回 `_FALLBACK = ("official_gb", "web", "govcn")`（`routing.py:31`）。
2. **`ADAPTER_CLASSES`（`channels/__init__.py:41-57`）≠ 巡检可用渠道**。
   `inspector._build_adapters` 会把**全部** 13 个渠道都实例化（`inspector.py:396-406`），
   但链里没出现的渠道**永远不会被 `probe` 调用**（`inspector.py:349-352` 只遍历 `chain`）。
3. **"渠道台账"这个形态今天已经存在，但只覆盖公告源**：`announce.py` 用
   `app_config` 键 `announce.sources` 存用户配置的源 URL（`announce.py:60`），
   有增删改查（`announce.py:206-260`）、URL 纪律/SSRF（`announce.py:93-162`）、
   列表页启发式解析（`announce.py:279-317`）、逐源健康态
   （`status/reason`：`announce.py:466-468`、`476-495`）、最近快照
   （`app_config` 键 `announce.scan_state`：`announce.py:61`、`339-342`）、
   预算（源≤50 / 单页 15s·2MB / 每页≤50 条 / 源间 1s / 全程软上限 300s：`announce.py:62-68`）。
   **它是"巡检渠道台账"最现实的模板**（单元=URL、逐源 status+reason、快照可读），
   但它与查号巡检（单元=标准号）是两条独立流程（`announce.py:1-5`）。

---

## 1. 渠道适配器逐条记录（`ChannelAdapter`，共 13 个）

### official_gb（国家标准全文公开系统）
- 适配器文件: `src/core/update/channels/official_gb.py`（`OfficialGbAdapter` L35，`name="official_gb"` L38）
- 真实请求的端点: `GET https://openstd.samr.gov.cn/bzgk/std/std_list`
  （`SEARCH_URL` L41）· query 参数 `searchText=<标准号>`、`p.p1=0`、
  `p.p90=circulation_date`、`p.p91=desc`、**`p.p2=<标准号>`（真实查询键，L50-51）** ·
  header `User-Agent`（Chrome125 UA，L31-32）+ `Referer=SEARCH_URL`（L52）·
  另有调用间限速 `PAUSE_S=1.0`（L43、`_pace` L113-116，仅真实 transport 睡眠）
- 取数方式: **服务端渲染 HTML 结果表**（`<tr>` 表格，L62-81）。
  无 transport 注入时走 `default_transport()`（`base.py:295-305`）：
  优先 `curl_cffi` `Session(impersonate="chrome")`（`base.py:199-201`），
  不可导入才回退 `httpx`（`base.py:250-273`）。**transport 可注入**（`base.py:316-317`）。
- 响应怎么清洗: 纯正则逐 `<tr>`：`<td><a>…GB…</a>` 取标准号（L68）、
  `<td class="mytxt"><a>…` 取名称（L71）、`<span>现行|即将实施|被代替|废止</span>`
  取状态（L72）、`<td>YYYY-MM-DD</td>` 取**第一个**日期作施行日期（L73、L79）、
  `showInfo('ID')` 取证据锚点并**拼成伪协议字符串 `showInfo:<ID>`**（L74、L80）。
  号归一 `norm_no`（去空白/斜杠+大写，`base.py:89-91`）；行挑选 `pick_row_by_norm`
  （精确匹配优先，否则同主体去年代取号最大，`base.py:99-118`）；状态词表
  `STATE_TEXT_MAP`（`base.py:68-73`）
- 失败语义: 超时 → `UpdateError(UPD-1001)`（`base.py:329-333`）；
  其他异常 → `UPD-1004 channel_unreachable`（`base.py:334-335`）；
  **非 200 不抛错**，走 `_miss()` 记 `raw.http`（`base.py:351-358`；调用点 L87）；
  解析 0 条 → `_miss` + `note="matches=N"`（L87）；
  **验证码** → `ChannelResult(captcha=True)`、不写库、批次转 paused
  （L56-59 + `base.py:38 UPD-1002` + `inspector.py:365-369`）；
  非法状态串 → WARN `illegal_state_text`、`legal_status=None`（L92-95）
- 它回答哪类问题: 现行性（判据：`<span>` 状态串）· 发布（"即将实施"）·
  修订（版本号归一号不同 → `new_version`，`base.py:126-141`）·
  废止（"废止" → `withdrawn`）· 被代替（"被代替" → `superseded`）· 编号核验（号+年代）
- 覆盖范围: 国标全文公开系统收录的 **GB / GB-T / GB-Z**；
  scripts 实测覆盖 ~97% 存量（`scripts/std_status_check.py:9`）。
  **明确不覆盖**：GB 50xxx/55xxx 工程建设标准（该库目录外，实测诚实 miss，
  `std_samr_hb.py:12` + `scripts/std_status_check.py:12`）、行业标准、地方标准、
  团体标准、法规；**无废止日期列**（`scripts/std_status_check.py:10`）
- 反爬/依赖: 必须浏览器指纹（`base.py:186-189` 明示 openstd 按 JA3 在握手期掐 Python 客户端）→
  依赖 `curl_cffi`；UA + Referer + 1s 礼貌限速；适配器保留验证码半自动分支，
  而 `scripts/std_status_check.py:9` 记录该渠道实测"无验证码"。**不需要代理轮换**

### web（网络逐号补漏搜索）
- 适配器文件: `src/core/update/channels/web_fallback.py`（`WebFallbackAdapter` L41，`name="web"` L44）
- 真实请求的端点: `GET https://www.bing.com/search`（`SEARCH_URL` L45）·
  参数 `q="<标准号> <标准名>"`（L49-50）· **无 UA、无 Referer 头**
- 取数方式: 期望 `dict` 响应 `{"results":[{title,url,snippet}]}`（mock 契约，L6-8、L52-54）。
  **代码路径事实：`if isinstance(body, dict)` 之外没有任何解析分支（L52-61）**，
  而真实 Bing 返回的是 HTML 字符串 → `results` 恒 `[]` → 恒 `_miss`。
  （结论由代码路径得出；未联网实测真实响应，故保留"未实测"标记。）
  transport 可注入，同 base
- 响应怎么清洗: 命中判定 = 结果 `title` 归一去年代后**包含**目标主体
  （`core = strip_year(norm_no(no))`，L56-59，`base.py:94-96`）；
  版本用 `_STD_TOKEN_RE = [A-Z]{1,4}(/[A-Z]{1,4})?\s*\d{4,5}-\d{4}` 从 title 抽（L30、L64）；
  状态用关键词表 `_STATUS_HINTS`（废止 > 被代替 > 即将实施 > 现行，按序取第一个，L27-28、L67-71）；
  日期用 `\d{4}-\d{2}-\d{2}` 从 title+snippet 抽（L31、L77）；
  另有 mock 专用分支：`hit["status"]` 若是合法英文枚举直接采用（L73-75）
- 失败语义: 超时/不可达同 base（UPD-1001 / UPD-1004）；
  非 200 或 0 结果 → `_miss(note="matches=N")`（L60-61）；
  **解析 0 条在真实网络下是常态**；
  **无验证码判定分支**（`looks_like_captcha` 未被 import 调用）
- 它回答哪类问题: 发布 · 修订（`new_version`）· 废止/被代替（**仅靠网页关键词，非官方字段**）·
  日期。不回答权威"现行性"
- 覆盖范围: 名义上全类别兜底（`routing.py:31` 第二棒）。**实际不覆盖任何东西**（见上）。
  **明确不覆盖**：任何需要真实 HTML 解析的场景
- 反爬/依赖: 依赖默认 transport 的指纹；**无 Referer/UA**；无重试、无退避、无限速

### govcn（gov.cn 公告检索 + PDF 存档）
- 适配器文件: `src/core/update/channels/govcn_announce.py`（`GovcnAnnounceAdapter` L44，`name="govcn"` L47）
- 真实请求的端点: `GET https://sousuo.www.gov.cn/sousuo/search.shtml`（`SEARCH_URL` L48）·
  参数 `q="<标准号> <标准名>"`（L57-58）· **无 header 覆盖**；
  归档再用 `transport.fetch_bytes(pdf_url, timeout=30)`（L124-126）
- 取数方式: 期望 `dict` 响应 `{"announcements":[{title,url,date,pdf_url,no}]}`（mock 契约 L6-8、L60-62）；
  归档走**原始字节**（`fetch_bytes`，`base.py:220-226`）+ `%PDF` 魔数校验（L127）。
  端点是 `.shtml` 前端页 → 若真实响应为 HTML 则 `announcements` 恒空 → 恒 `_miss`
  （代码路径可证；**真实响应未实测**）
- 响应怎么清洗: `_pick` 按 title 归一后**包含**标准号或包含标准名（L92-104）；
  版本 = `hit["no"]` 归一，缺则从 title 正则抽 `_STD_TOKEN_RE`（L28、L68-70）；
  状态是**启发式**：title 含"废止" → `withdrawn`；否则版本==请求号 → `effective`；
  否则一律 `upcoming`（"新发布待施行"，L72-77）——**不是官方状态字段**
- 失败语义: 0 条 → `_miss(note="matches=N")`（L65）；`archive_pdf` 无命中 →
  `UpdateError(UPD-2004)`（`UPD_ANNOUNCEMENT_NOT_FOUND`，L115-116）；
  下载失败/非 200/非 `%PDF`/≤1024B → **回退写一个最小合法占位 PDF**
  （`_MINIMAL_PDF` L38-41，落盘 L147-150，WARN L133-143）→
  **"归档成功"不保证是真实公告 PDF**；
  **无验证码判定分支**
- 它回答哪类问题: 发布（公告）· 废止（标题含"废止"）· 现行性（弱启发式：号相同判 effective）
- 覆盖范围: 名义上 gov.cn 公告检索（F-03 公告存档）。**明确不覆盖**：标准号级官方状态字段、
  标准全文、地方公告；真实网络下（HTML 响应）不覆盖任何东西
- 反爬/依赖: 依赖默认 transport 指纹；**无 UA/Referer 覆盖**；无重试/退避/限速；
  PDF 字节下载有 30s 超时与魔数闸

### laws_db（国家法律法规数据库 / flk.npc.gov.cn）
- 适配器文件: `src/core/update/channels/laws_db.py`（`LawsDbAdapter` L28，`name="laws_db"` L31）
- 真实请求的端点: `POST https://flk.npc.gov.cn/law-search/search/list`（`SEARCH_URL` L32）·
  JSON body 逐字抄自浏览器真实载荷：`searchRange=1, sxrq=[], gbrq=[], sxx=[], searchType=2,
  xgzlSearch=false, searchContent=<标准名或号>, orderByParam={order:"-1",sort:""},
  flfgCodeId=[], zdjgCodeId=[], gbrqYear=[], pageNum=1, pageSize=20`（L36-42）·
  证据链 `DETAIL_BASE = https://flk.npc.gov.cn/detail?id=`（L33）+ 行内 `bbbs`（L85）
- 取数方式: **JSON**（真实解析，非 mock-only）。非 dict 响应 → `[]`（L44-45）。
  transport 可注入
- 响应怎么清洗: 行去 `<em class='highlight'>` 后压空白再比（L57-59）；
  匹配 = 请求串 ⊂ 标题 或 标题 ⊂ 请求串（L61）；
  确定性挑选 = `sxx==3` 优先，其次 `gbrq`（公布日期）新者（L66-67）；
  状态码表 `SXX_LEGAL`：1 已废止→withdrawn / 2 被修改→superseded / 3 有效→effective /
  4 尚未生效→upcoming（L20-25、L69）；日期 `sxrq` 优先、回退 `gbrq`（L84）
- 失败语义: 空 query → `_miss(note="empty_query")`（L52-53）；
  0 匹配 → `_miss(note="no_title_match rows=N")`（L62-64）；
  未知 `sxx` 码 → WARN `illegal_sxx_code`、`legal_status=None`（L70-72）；
  `upcoming` 不属 `change_type` 枚举 → 显式置 `None` 交聚合层（L74-78）；
  超时/不可达同 base（UPD-1001/UPD-1004，经 `_fetch`）；**无验证码分支**
- 它回答哪类问题: **现行性（权威 sxx）** · 废止 · 修订（被修改）· 发布（尚未生效）· 法规编号/标题核验
- 覆盖范围: flk 国家法律法规数据库全库（法律 / 行政法规 / 监察法规 / 军事法规 /
  司法解释 / 地方性法规 / 部门规章，见 `ingest.py:22-31` 的 `FLK_LEVEL_MAP`）。
  **明确不覆盖**：一切"标准"（GB/AQ/HJ/DB/T/ISO…）——该适配器 `standard_no` 形参实际承载"法规标题"
- 反爬/依赖: flk 有 **JA3/TLS 指纹 WAF**（`catalog.py:16-17` 自认本机 `requests` 握手可能
  `SSLEOFError`；`base.py:186` 把 flk.npc.gov.cn 与 openstd/std.samr 并列）→
  真实可用性依赖 `curl_cffi`。**无 UA/Referer 覆盖、无限速、无重试**
- **⚠ 巡检不可达**：`routing._PREFIX_ROUTE`（L20-28）与 `_FALLBACK`（L31）都不含 `laws_db`
  → `inspector` 永远不会调用它。它只在离线 fixture 里有 case（`tests/fixtures/update_channels.json`）

### ndls（国家数字标准馆 / 中国标准化研究院）
- 适配器文件: `src/core/update/channels/ndls.py`（`NdlsAdapter` L65，`name="ndls"` L68）
- 真实请求的端点: ① `POST https://ndls.cnis.ac.cn/api/standard/list`（`SEARCH_URL` L70），
  JSON body 与站点前端 `getSearchData(paramsType=1)` 同款（`_search_body` L141-153，
  含 `page/size/keyword` + 一串空过滤字段）；
  ② `GET https://ndls.cnis.ac.cn/api/standard/detail/<id>`（`DETAIL_URL` L71）；
  ③ 证据页 `https://ndls.cnis.ac.cn/standard/detail/<id>`（`EVIDENCE_URL` L72）；
  header：Chrome UA + `Accept: application/json…` + `Accept-Language` + `Referer`
  （按请求动态拼 `standard/index?keyword=` / `standard/detail/<id>`）+ `Origin` +
  **`X-Requested-With: XMLHttpRequest`**（L129-138）；限速 `PAUSE_S=1.0`（L74、L155-158）
- 取数方式: **JSON（两段：搜索 + 详情）**；`detail=False` 时有"体检模式"跳过详情，
  请求减半（L76-81、L102-108）。transport 可注入；**生产中由 scripts 注入带代理的 transport**（见反爬）
- 响应怎么清洗: 先 `code != 0` 直接降级（L183-185）；`data.results` 行挑选：
  长横/短横先归一为 `-`（`_dash_norm` L162-164）→ 精确匹配 `a100`，
  否则同主体去年代取号最大（L189-200）；
  状态词表 `NDLS_STATE_MAP`：现行→effective / 未生效→upcoming / 被代替→superseded /
  作废·废止·废止转行标→withdrawn / 已修订→superseded（L50-58，未知串 WARN 不猜 L166-173）；
  详情字段映射：`a000` 状态、`a100` 标准号、`a101` 发布、`a205` 实施、**`a206` 废止日期**、
  `a461list` 代替标准、`a462list` 被代替标准、`a298` 名称（L231-266）；
  关键日期优先级：废止→`a206`，否则 `a205`，再否则 `a101`（L244-250）；
  `_newer_version` 从代替链里取**同主体且年代更大**的号作为 `latest_version`（L268-292）
- 失败语义: 验证码 → `captcha=True`（L91-94）；
  搜索行无 id → `_miss(note="search_row_no_id")`（L99-101）；
  `data.results` 空 → `_miss(note="search_hits=0")`（L186-188）；
  `code != 0` → `_miss(note="api_code_X:msg")`（L183-185）；
  **详情不可用 → 降级用搜索行 + WARN `detail_unavailable_fallback_search_row`**
  （L117-124，`_from_row` L210-229，`note="detail_unavailable"`；此时 `evidence_url=None`）；
  未知状态串 → WARN `illegal_state_text`（L214-216、L236-237）；
  超时/不可达同 base（UPD-1001/UPD-1004）
- 它回答哪类问题: **现行性（跨门类权威）** · 废止（**含废止日期**）·
  修订/替代（含代替链 `a461list`/`a462list`）· 发布/实施日期 · 编号核验
- 覆盖范围: 国家数字标准馆跨门类目录（国标 + 行标 + 工程建设建标等；AQ 3028-2008 实测
  `a000=作废 / a206=2024-07-01`，GB 18218-2018 实测 `a000=现行 / a206=null`，L11-12）。
  **明确不覆盖**：法规（走 law_source）、废止/替代详情在站点不可达时（降级搜索行后无废止日期）
- 反爬/依赖: **Jiasule WAF（观察模式）**：浏览器 UA + 会话 cookie jar（默认 Session 维持）+
  1s 限速（L19-20）。**超阈值进入验证码惩罚期**（实测 100% 拦截、0.1s 内返回 code 5320、
  持续 30min+，`proxy_rotate.py:4-8`）→ **需要代理轮换**：
  `proxy_rotate.ClashRotator`（切 Clash Verge/mihomo 节点换出口 IP，`proxy_rotate.py:106-182`）
  或 `ProxyListPool`（静态代理文件，L186-210）+ `ProxyCurlTransport`（新 session=新 cookie，L214-250）
  + `random_gap` 间隔随机化（L43-47）。**但这套轮换只在 `scripts/std_status_check.py:49-53,220-228`
  接线，引擎侧（inspector）完全不接线** → 巡检跑 ndls 时没有换 IP 能力

### std_samr_hb（全国标准信息公共服务平台·行业标准目录）
- 适配器文件: `src/core/update/channels/std_samr_hb.py`（`StdSamrHbAdapter` L47，`name="std_samr_hb"` L50）
- 真实请求的端点: `GET https://std.samr.gov.cn/hb/search/hbPage`（`SEARCH_URL` L51）·
  参数 `searchText=<归一号 compact 形态>`、`op=""`、`ISSUE_DATE=""`（L63-68）·
  header Chrome UA + `Referer=https://std.samr.gov.cn/hb/hbQuery`（L53、L67）·
  详情 `https://std.samr.gov.cn/hb/search/stdHBDetailed?id={row.id}`（`DETAIL_URL` L52）·
  限速 `PAUSE_S=1.0`（L54、L109-112）
- 取数方式: **JSON（非 HTML，L5-7 明示）**；`body["rows"]`（L78-79）。transport 可注入
- 响应怎么清洗: **输入必须先 `norm_no` 归一为 compact 形态**——带空格/斜杠（如
  "GB/T 50493-2019"）会让后端退化成全库 match-all（`total≈107960`，L8-12、L58-66）；
  空号直接诚实 miss、不发请求（L59-61）；
  行挑选 `pick_row_by_norm(code_key="STD_CODE")`（L107）；
  状态取 `STATE`，回退 `G_STATE`，经 `map_state_text`（L85-86）；
  关键日期 `ACT_DATE`（实施）优先，回退 `ISSUE_DATE`（发布）（L98-99）
- 失败语义: 验证码 → `captcha=True`（L72-75）；
  0 行/无匹配 → `_miss(note="matches=N")`（L81-82）；
  空号 → `_miss(note="empty_standard_no")`（L59-61）；
  未知 STATE 串 → WARN `illegal_state_text`（L87-90）；
  超时/不可达同 base
- 它回答哪类问题: 现行性（STATE）· 废止（STATE=废止，**无废止日期**）· 修订 · 发布/实施日期 · 编号核验
- 覆盖范围: 行业标准目录（`total` 约 10.8 万，L6）。
  **明确不覆盖**：国标（GB/T 50493-2019 实测 `total=0`，诚实 miss，L12）、
  地方标准、团体标准、法规；**本库无废止日期字段**（L16-17）
- 反爬/依赖: UA + Referer + 1s 限速；`std.samr.gov.cn` 属 JA3 指纹 WAF 家族
  （`base.py:186` 与 openstd/flk 并列）→ 依赖 `curl_cffi`。**不需要代理轮换**
- **⚠ 巡检不可达**：`routing` 里没有任何前缀指向 `std_samr_hb`（L20-28）→ 巡检永不调用

### hbba（行业标准信息服务平台 sacinfo）
- 适配器文件: `src/core/update/channels/hbba.py`（共享基类 `_SacinfoQueryAdapter` L67，
  `HbbaAdapter` L139，`name="hbba"` L142，`host="hbba.sacinfo.org.cn"` L143）
- 真实请求的端点: `POST https://hbba.sacinfo.org.cn/stdQueryList`（L84）·
  **form-urlencoded** body：`current=1, size=20, key=<标准号>, ministry="", industry="",
  pubdate="", date="", status=""`（与 stdList 页 `queryParams` 原样同形，L86-88）·
  header `Referer=https://hbba.sacinfo.org.cn/stdList?key=<urlquote(号)>` +
  `X-Requested-With: XMLHttpRequest`（L89-90）
- 取数方式: **JSON**（`records` 行，L99-101）。transport 可注入
- 响应怎么清洗: 行挑选 `pick_row_by_norm(code_key="code")`（L136）；
  状态 `status` 经 `_sacinfo_state` = 平台独有词表 `_SACINFO_STATE_MAP{"有更新版": "superseded"}`
  （L42、L59-64）∪ `map_state_text`；**日期是 epoch 毫秒（北京时间 UTC+8）**→
  `_epoch_ms_to_date`（`datetime.fromtimestamp(ms/1000, tz=+8)`，L44-56）；
  关键日期：废止行取 `fzDate`（废止日期），否则 `actDate`（实施日期）（L114-119）；
  证据链 `https://hbba.sacinfo.org.cn/stdDetail/<pk>`（L128-129）
- 失败语义: 空号 → `_miss(note="empty_standard_no")`（L80-81）；
  验证码 → `captcha=True`（L94-97）；
  0 records → `_miss(note="matches=N")`（L103-104）；
  未知 status 串 → WARN `illegal_state_text`（L109-112）；
  超时/不可达同 base
- 它回答哪类问题: 现行性 · 废止（**含 `fzDate` 废止日期**，AQ 3028-2008 实测 2024-07-01，L13）·
  被代替（"有更新版"）· 发布/实施日期 · 编号核验
- 覆盖范围: 行业标准信息服务平台全库（MT/YB/JB/HG/QB/NY/SL/SN/SH/JG/CJ 等，
  由 `routing.py:27` 前缀表路由到此）。
  **明确不覆盖**：国标、地方标准（走 dbba）、团体标准、法规
- 反爬/依赖: **裸 nginx、零反爬**（L3）；只需 Referer + XHR 头。**不需要代理、无限速、无验证码**

### dbba（地方标准信息服务平台 sacinfo）
- 适配器文件: `src/core/update/channels/dbba.py`（`DbbaAdapter` L23，
  `name="dbba"` L26，`host="dbba.sacinfo.org.cn"` L27）——
  **实现完全复用 `hbba._SacinfoQueryAdapter`**（import L20），只有域名不同（L5）
- 真实请求的端点: `POST https://dbba.sacinfo.org.cn/stdQueryList`
  （host 拼装在 `hbba.py:84`，参数/头与 hbba 完全相同 L86-90）
- 取数方式 / 响应怎么清洗 / 失败语义: **与 hbba 逐字相同**（同一基类，`hbba.py:77-136`）
- 它回答哪类问题: 现行性 · 废止（`fzDate`）· 被代替（`reviseStdCodes`/有更新版）· 日期 · 编号核验
  （DB11/T 3031-2022 实测 status="有更新版" → superseded，L8-10）
- 覆盖范围: **地方标准信息服务平台**（DBxx/T）。
  **明确不覆盖**：省级自建的地方标准公开系统、国标、行标、团标、法规
- 反爬/依赖: 同 hbba（裸 nginx 零反爬）

### ttzb（全国团体标准信息平台）
- 适配器文件: `src/core/update/channels/ttzb.py`（`TtzbAdapter` L93，`name="ttzb"` L96）
- 真实请求的端点: ① `POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/
  getPortalStandardList`（`SEARCH_URL` L59-60；生产 `API_PREFIX=/cms-proxy`，本机 8080 时为空串，L6-8）·
  form body `pageNo=1, pageSize=20, searchKey=<标准号>`（L101-103）；
  ② 详情 `GET https://www.ttbz.org.cn/standardDetail/<standardUniqueId>.html`
  （伪静态路由，**缺 `.html` 返回 404**，L61-62）。**无 UA/Referer 头**
- 取数方式: **JSON（检索）+ 静态 HTML（详情，约 227KB）**，详情三处信号解析（L11-19）：
  JSON-LD、portal JSON blob、状态行 span。transport 可注入
- 响应怎么清洗: 检索 `result != False` 且 `data.rows`（L119-126）；
  号归一 `_canon` = `norm_no` + **长横 U+2014 → `-`**（L83-85）；
  `_core` 去年代（L88-90）；行挑选精确优先→同主体取号最大（L128-140）；
  详情三处：
  ① `<script type="application/ld+json">` 只取 `@type=TechArticle`（跳过 BreadcrumbList
     与尾逗号坏 JSON，`_extract_json_ld` L212-221）→ `identifier` 标准号 / `datePublished` 发布 /
     `dateModified` 文件公布日期 / `author.name` 团体；
  ② `<script type="application/json" id="portal-standard-detail-json">`（L65-67、L223-232）→
     `standardStatusName / publishDate / implementDate / filePublishDate / abolishDate /
     organName / isSale`；
  ③ 全页唯一 `<span class="el-tag…">现行|即将实施|被代替|废止</span>`（L69-70、L234-237）；
  状态优先级 **状态行 → portal → 检索行 `standardStatusName`**（L168-169）；
  `effective_date` 取 JSON-LD `datePublished`（与 official_gb `dates[0]` 口径一致，L29-30、L176-177）
- 失败语义: 验证码 → `captcha=True`（L106-109）；0 行 → `_miss(note="no_match rows=N")`（L113-115）；
  详情请求抛 `UpdateError` → **降级检索行** + WARN `detail_fetch_failed_fallback_row`（L154-159）；
  详情无任何可用信号 → `raw["note"]="detail_fallback:row"`（L206-208）；
  未知状态串 → WARN `illegal_state_text`（L170-175）
- 它回答哪类问题: 现行性 · 废止（状态字典仅 现行(1)/废止(2)，L20）· 发布/实施/文件公布日期 · 团体名
- 覆盖范围: 全国团体标准信息平台（`T/` 前缀，`routing.py:22`）。
  **明确不覆盖**：**废止标准不进入常规检索**——`getDisabledStandardList` 不接受过滤且
  `standardUniqueId` 恒 null，无法按号定位详情 → 废止在 ttzb 层按查无处理，交降级链（L21-23）；
  全文 `isSale:1` 付费/需登录，不做全文（L24）
- 反爬/依赖: 无 UA/Referer 覆盖、无限速、无重试；检索接口的 `searchKey` 是模糊 contains
  且 `data.total` **封顶 100** → 必须客户端按归一号精确挑选（L8-10）

### mee（生态环境部 HJ 标准）
- 适配器文件: `src/core/update/channels/mee.py`（`MeeAdapter` L123，`name="mee"` L126）
- 真实请求的端点: `POST http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1520238134405`
  （`QUERY_URL` L41-42）· **form body `doctitle=<标准号>`**（L131，可选 `bzys=标准要素 id` 未用）·
  header `Referer=https://www.mee.gov.cn/ywgz/fgbz/bz/`（L43、L132）；
  0 行时用"字母前缀 + 空格 + 余部"候选**重试一次**（≤2 请求/号，L22-23、L90-99、L144-150）
- 取数方式: **服务端渲染报告页 HTML（UTF-8）**（L5-6）。transport 可注入；无 UA 头
- 响应怎么清洗: 正则逐 `<tr>`（跳过含 `<th>` 的表头，L105-107）+
  `_cell_text` 按 `colid` 取单元格（剥标签/unescape/去空白，L58-64）；
  列号常量 `COL_NO=1 / COL_NAME=2 / COL_EFF=5 / COL_ABSTRACT=6 / COL_PDF=7`（L46-51，改版即失效，L46）；
  日期 `20\d{2}-\d{2}-\d{2}`（L54、L110）；
  **PDF 全文 URL 逆向**：colid=7 是 `display:none` 的隐藏单元格，**内嵌完整 PDF 地址** →
  `build_pdf_url`：优先 `href=`（排除 `javascript:` 壳），否则取可见文本 →
  `http://` 归一为 `https://` → 相对路径 `urljoin("https://www.mee.gov.cn/", …)`（L67-87）；
  英文/数字输入归一：`HJ819-2017` 查不到而 `HJ 819-2017` 命中（**空格敏感**，L22-23、L90-99）
- 失败语义: 验证码 → `captcha=True`（L134-137）；
  非 str body → `_miss(note="unexpected_body_type")`（L139-140）；
  0 行/无匹配 → `_miss(note="no_matching_row")`（L152-154）；
  **无状态列 → 显式 `legal_status=None` / `change_type=None`**，仅记 INFO `weak_status_only`
  （L19-20、L156-158，`_STATE_NOTE` L55）；
  超时/不可达同 base
- 它回答哪类问题: **发布/实施日期**（弱信号）· **全文 PDF 可获取性**（标准存在性证据）。
  **不回答**：废止、现行性、被代替——报告页没有状态列，明示交给聚合层判定（L19-20、L55）
- 覆盖范围: 生态环境部"国家环境保护标准"数据中心报告（HJ 系列）。
  **明确不覆盖**：现行性/废止判定、其他部委行业标准、国标、地方标准、法规
- 反爬/依赖: Referer + 默认 transport 指纹；**≤2 请求/号**；无 UA 头、无限速、无重试

### mem_gov（应急管理部 AQ 行业标准公告）
- 适配器文件: `src/core/update/channels/mem_gov.py`（`MemGovAdapter` L34，`name="mem_gov"` L37）
- 真实请求的端点: ① 公告列表 `GET https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/`
  （`LIST_URL` L23）；② 分页 `…/bzgg/index_N.shtml`（N=2..`_MAX_LIST_PAGES=2`，L24、L82）；
  ③ 逐条公告详情 `urljoin(LIST_URL, href)`（L90）·
  header 仅 `User-Agent`（Chrome126，L106、L128-130）
- 取数方式: **HTML 列表页 + HTML 详情页**（真实解析）。预算：列表 ≤2 页、
  详情 ≤`_MAX_DETAILS=8` 条/号（L25-27、L88-89）。transport 可注入
- 响应怎么清洗: 列表正则 `<a href="…\.html">标题</a>` 抽 `(href,title)`，
  只保留标题含 `标准/废止/批准/发布/公告` 的条目（L114-125）；
  详情：`norm_no(整页 HTML)` 或剥标签压空白后的整页文本**包含**目标号即命中（L94-96）；
  状态 = **公告标题语义**：`_TITLE_WITHDRAWN`（废止|替代|作废）→ withdrawn，
  `_TITLE_EFFECTIVE`（批准|发布|颁布）→ effective（L30-31、L97-100）
- 失败语义: 空号 → `_miss(note="empty_standard_no")`（L41-43）；
  任何异常（网络/解析/WAF）→ 归一 `_miss(note="fetch_failed")`（L45-48）；
  找不到 → `_miss(note="not_found_in_recent_announcements")`（L50-51）；
  非 200 → `_fetch_text` 返回 None 跳过（L109-110）；
  **无验证码判定分支**；**无 HTTP 状态码透传**（一律 200 记在 raw，L66）
- 它回答哪类问题: 发布（批准/发布/颁布）· 废止（公告标题语义）·
  **不回答**：废止日期（`effective_date=None`，L64）、现行性字段、版本号（`latest_version=None`，L63）
- 覆盖范围: 应急管理部 AQ 行业标准**公告**（最近 2 页列表 × 最多 8 条详情，L24-27）。
  **明确不覆盖**：AQ 标准目录全量（只覆盖公告里出现过的号）、废止日期；
  docstring 提到标准文本页 `…/bz/bzwb/index_N.shtml`（PDF 直链，L6）但**代码未实现**
- 反爬/依赖: 站点带 `Server: WAF` 头但浏览器 UA 可过、无验证码（L3）；无重试/退避/限速
- **⚠ 巡检不可达**：`routing.py:21` 把 `AQ/AQ/T` 前缀路由到 **ndls** 而不是 `mem_gov`；
  `mem_gov` 不在任何链中（`inspector.py:338-339` 的 docstring 声称"AQ→mem_gov"，与路由实现不一致）

### mohurd（住建部工程建设标准文告）
- 适配器文件: `src/core/update/channels/mohurd.py`（`MohurdAdapter` L29，`name="mohurd"` L32）
- 真实请求的端点: ① 文告列表 `GET https://www.mohurd.gov.cn/gongkai/zc/wgk/`（`LIST_URL` L21）；
  ② 分页 `…/wgk/index_N.shtml`（N=2..`_MAX_PAGES=2`，L22、L59）；
  ③ 文告详情 `urljoin(LIST_URL, href)`（L69，如
  `…/gongkai/zc/wjk/art/2024/art_17339_770016.html`，L4）· header 仅 UA（Chrome126，L84、L104-106）
- 取数方式: **HTML 列表页 + HTML 详情页**（真实解析；附件走 `/api-gateway` 网关，**未做全文**，L5）。
  预算：列表 ≤2 页、详情 ≤8 条/号（L22-23、L67-68）。transport 可注入
- 响应怎么清洗: 列表正则同 mem_gov，但关键词集不同：`标准/公告/通知/文告`（L92-101）；
  详情同 mem_gov（剥标签压空白 + `norm_no` 双路包含判定，L73-75）；
  状态 = 文告标题语义正则 `_TITLE_EFFECTIVE`（批准|发布|颁布|印发）/
  `_TITLE_WITHDRAWN`（废止|替代|作废）（L25-26、L76-79）
- 失败语义: 与 mem_gov 同形：空号 `_miss`（L36-38）· 异常 `_miss(note="fetch_failed")`（L39-42）·
  找不到 `_miss(note="not_found_in_recent_announcements")`（L43-44）· 非 200 → 跳过（L87-88）；
  **无验证码分支、无状态码透传**
- 它回答哪类问题: 发布（批准/发布/印发）· 废止（文告标题语义）·
  **不回答**：废止日期、现行性字段、版本号（`latest_version=None` L52、`effective_date=None` L53）
- 覆盖范围: 住建部文告列表**最近 2 页**。
  **明确不覆盖**：工程建设标准目录全量、GB 50xxx 的状态字段；附件全文（L5）
- 反爬/依赖: 静态可抓、无验证码（L3）；无重试/限速
- **⚠ 巡检不可达**：`routing.py:23` 把 `GB 50xxx/55xxx` 路由到 **ndls**；
  `mohurd` 不在任何链中（同上 docstring 与实现不一致）

### cssn（中国标准服务网）
- 适配器文件: `src/core/update/channels/cssn.py`（`CssnAdapter` L65，`name="cssn"` L68）
- 真实请求的端点: `GET https://www.cssn.net.cn/api/standards/list`
  （`SEARCH_URL` L69）· 参数 `keyword=<标准号>`（**保留原空格**，L76-77、L99-100）·
  header Chrome UA + `Referer=https://www.cssn.net.cn/cssn/index` + `Accept: application/json`
  （`INDEX` L70、L101-103）· 限速 `PAUSE_S=1.0`（L72、L120-123）；
  证据链拼法 `INDEX + "/list?keyword=" + quote(标准号)`（L193）——
  **⚠ 疑似拼错**（`INDEX` 已是 `/cssn/index`，拼出 `/cssn/index/list?keyword=`；未实测该 URL 是否可打开）
- 取数方式: **JSON**（`body["results"]`，L115-118）。transport 可注入（scripts 里会注入带代理的）
- 响应怎么清洗: `_pick` **跨前缀同主体挑选**：先精确 `a100`；否则按数字主体
  （`_CORE_RE` 去 GB/GBT/GBZ 前缀 + 年份，L58、L125-132）匹配，
  **同年份版优先**（强制 GB 转推荐后库内是 GB/T 版：GB 14048.1-2012 → GB/T 14048.1-2012），
  全年份缺失才取年代最大者（L134-163）；
  状态词表 `CSSN_STATE_MAP`：现行→effective / 未生效→upcoming / 被代替→superseded /
  作废·废止·废止转行标→withdrawn（L48-55，未知串 WARN `illegal_state_text` L166-181）；
  日期 `a205`（实施）优先、回退 `a101`（发布）（L182-183、L186-187）；
  raw **保留完整原始行**（a000/a100/a101/a205/a825 CCS/a825name/a826 ICS/a826name/a104/formats…，L195-198）
- 失败语义: **请求异常 → 归一为未命中** + WARN `fetch_error`（L105-108）；
  **验证码 → 直接返回 `(None, None)` 当 miss，`captcha` 标记不透传**
  （L111-112，源码注释自认"外层无法透传 captcha 标记 → 走 miss 且 WARN"）→
  **该渠道的验证码不会触发 UPD-1002 半自动暂停**；
  非 dict / `code not in (0, None)` → miss（L113-114）；0 命中 → `_miss(note="no_match")`（L78-79）
- 它回答哪类问题: **现行性（全覆盖）** · 废止/作废 · 被代替 · 发布/实施日期 ·
  编号核验（跨 GB/GB-T/GB-Z 前缀）· CCS/ICS 分类（raw 里带）
- 覆盖范围: **全门类国标**——含 `openstd`/`std.samr` 不收录的食品安全 GB 5009.x、
  工程建设 GB 5xxxx、强制 GB / 推荐 GB/T / 指导性 GB/Z
  （实测 GB 5009.247-2025、GB 14048.1-2012、GB 11859.1-1989、GB 12695-2016 全命中，L9-11）。
  **明确不覆盖**：行业标准、地方标准、团体标准、法规；**无废止日期列**（L186）
- 反爬/依赖: **无 Jiasule 验证码**（curl_cffi chrome 指纹实测 200 JSON，L16），
  但仍带 UA+Referer+1s 限速；`scripts/std_status_check.py:173` 把它设为**默认主渠道**
- **⚠ 巡检不可达**：`routing` 无任何规则指向 `cssn` → 巡检永不调用；
  它只在体检脚本里当主渠道（`scripts/std_status_check.py:46,173,226`）

---

## 2. 同源但**不是** `ChannelAdapter` 的通路（台账需一并登记）

这五条不是巡检渠道，但业主的"渠道台账"如果只登记 `ADAPTER_CLASSES`，会漏掉
现实中真正在用的取数路径（尤其 `flk_client`）。

### flk_client（国家法律法规数据库 · 官方源客户端）
- 文件: `src/core/knowledge/law_source/flk_client.py`（模块级函数，无类）
- 端点: `POST https://flk.npc.gov.cn/law-search/search/list`（L18）
  · `GET …/law-search/search/enumData`（分类/机关/时效枚举，L19）
  · `GET …/law-search/search/flfgDetails?bbbs=`（详情：元数据 + 章条结构 + ossFile，L20）
  · `GET …/law-search/download/pc?format=docx|pdf&bbbs=`（**签名下载 URL，主路径**，L21、L124-131）
  · header：UA + `Referer`（`/detail?id=<bbbs>` 或 `/`，L24-26）
- 取数方式: JSON API + 带签名的文件下载；统一经 `law_source/http.py`
  （`fetch_json` L71-90 / `download_file` L93-119）
- 清洗: `parse_rows` 精简为 `bbbs/title/flxz/zdjgName/gbrq/sxrq/sxx`（L69-82）；
  `FlkDetail` 数据类承载 `content` 章条结构与 `raw`（L89-117）
- 失败语义: `http.py` 三层——域白名单校验失败 `ValueError`（**不重试、语义透传**，L48-54、L62-63）；
  其他异常重试 3 次、退避 `0.8*2^i`（L57-68）；文件下载做**魔数校验**
  （docx/ofd = `PK\x03\x04`，pdf = `%PDF`，L122-135），不合格删除 `.part` 并抛错（L111-115）
- 回答: 法规 **发布 / 现行性（sxx）/ 修订 / 废止 / 全文**（`verify.py` 把 sxx 映射为
  effective/superseded/withdrawn/upcoming，L57-62）；**不回答标准（GB/DB/T…）**
- 覆盖: flk 全库；不覆盖任何标准体系
- 反爬: `http.py` 用 **plain `requests` + `verify=False`**（L82-84、L104-106），
  **没有 curl_cffi 指纹**；域白名单仅 5 个主机（L21-27）、按 host 0.6s 限速（L34、L39-45）。
  与 `channels/base.py` 的 HTTP 纪律**完全独立、互不共享**（白名单 vs 无白名单、指纹 vs 无指纹）

### govcn_client（国务院政策文件库 · 官方源客户端）
- 文件: `src/core/knowledge/law_source/govcn_client.py`
- 端点: `GET https://sousuo.www.gov.cn/search-gov/data`（L20）·
  参数 `t=zhengcelibrary, q, searchfield=title|content, sort, sortType=1, p, n,
  type=gwyzcwjk`（+可选 `childtype/pubtimeyear/bmfl/maxtime/mintime`，L37-51）；
  详情页用 `requests.get(url, verify=False)` + BeautifulSoup（L86-136）
- 取数方式: JSON（搜索）+ HTML（详情，`h1/.article-title` 等选择器 L99-104）
- 清洗: `parse_rows` 剥离 `<em>` 高亮、从 `searchVO.catMap.*.listVO` 摊平
  （取 `url` 而非常为空的 `piclinksurl`，L54-73）；下载链接**只留白名单域**（L122-135）
- 失败语义: JSON 非 dict → `ValueError`（`http.py:88-89`）；详情页 `raise_for_status`
  （L94-95）非 200 直接抛；无官方下载链接时**回退用正文生成 docx**
  （`ingest.py:154-186`，`content_origin="web"`）
- 回答: 法规 发布 / 全文；**不回答标准号级状态**
- 覆盖: 国务院文件 / 部门文件 / 解读（`CHILDTYPE` L26-30）；不覆盖标准体系
- 反爬: 白名单（`sousuo.www.gov.cn`、`www.gov.cn`、`gov.cn`）+ 0.6s 限速 + 3 次重试；
  无指纹模拟

### announce（用户自定义公告源——**台账形态本身**）
- 文件: `src/core/update/announce.py`
- 端点: **用户配置的任意公网 URL**（`app_config` 键 `announce.sources`，L60、L187-189）；
  抓取用 `default_transport()`（L411），**允许跟随重定向**（默认 `allow_redirects=True`）
- 取数方式: HTML 列表页（也容忍 JSON：`json.dumps` 后按 HTML 解析，L474-475）；
  预算：单页 15s / 2MB / 每页 ≤50 条 / 源间 1s / 全程软上限 300s / 源数 ≤50（L62-68）
- 清洗: `parse_list_page` 纯启发式（零 LLM，L279-317）：正则抽 `<a href>`（L85-86）→
  噪声词过滤（`_NOISE_RE` L73-77）→ JS 模板噪声过滤（`_JS_NOISE_RE` L79）→
  静态资源过滤（L88）→ URL 归一（去追踪参数/排序 query，L93-118）→
  标题尾部日期剥离（L81-82）→ 日期取**最后一个**合法年份（1990-2100，`_parse_date` L264-276）→
  标准号用 `govcn_announce._STD_TOKEN_RE`（L50、L307-308）；诊断
  `{parsed, truncated, js_shell_suspected}`（L313-317）
- 失败语义（**这是全仓最诚实的一处，可作为台账状态语义模板**）:
  非 200 → `status=failed, reason="http_<N>"`（L476-479）；
  验证码/风控或 403/429 → `reason="waf_captcha"`（L480-483）；
  解析 0 条 → `reason="js_shell_suspected"` 或 `"parse_empty"`（L490-494）；
  超时 → `reason="skipped_timeout"`（L420-424）；异常 → `reason="unreachable: …"`（L546-551）；
  另有 409 双闸（`UPD-2006`，L348-358）、僵尸扫描自愈（L352-356）
- 回答: **发布**（"看新公告"，首扫基线 `first_scan_done` 不计新，L16-17、L496、L517-525）；
  `standard_no` 与 `published_date` 为启发式识别字段；**不回答**现行性/废止/全文
- 覆盖: 用户添加的任何公网列表页（源数 ≤50）；**不覆盖**：无 feed 的 JS 渲染站、
  需登录站、内网（SSRF 严格版：仅 http/https，loopback/RFC1918/链路本地/云元数据/
  0.0.0.0/IPv6 本地/`.local` 一律 422，L18-20、L126-162）
- 反爬: 依赖默认 transport 指纹；无 UA/Referer 覆盖；无代理；1s 源间间隔

### ccs_fetcher（CCS 分类抓取 · 与 cssn 同主机另一端点）
- 文件: `src/core/knowledge/ccs_fetcher.py`
- 端点: `GET https://www.cssn.net.cn/api/cssn/list?keyword=<数字号>`（L17、L102）·
  header 仅 UA（L18）
- 取数方式: HTML 列表页（`httpx.Client`，超时 20s，跟随重定向，L100-103）
- 清洗: 按 `ph_img_contenta301">` 标题块切分（L74、L105-107）→ 块内
  `【CCS分类】</strong>([A-Z]\d{2}[^<]*)` 抽 CCS（L75）→ 标准号/名称匹配（L109-110）
- 失败语义: 任何失败返回 `None`，由调用方用本地映射表兜底（L7、L85）；
  另有种子文件 `KS_CCS_SEED_FILE` 命中即零网络返回（L20-54、L90-93）
- 回答: **分类（CCS）**；不回答状态/效力
- 覆盖: CSSN 站点 CCS 分类；不覆盖其他分类体系（ICS 只在 `cssn.py` 的 raw 里顺带存在）
- 反爬: 无指纹、无白名单、无重试；与 `channels/cssn.py` **同主机不同端点**（见 §4 表 2）

### discover（找标检索 · openstd 另一端点）
- 文件: `src/core/update/discover.py`
- 端点: `GET https://openstd.samr.gov.cn/db/search`（L59-60）·
  参数 `q="<分类路径> 标准"`、`page=drill_level`（L495-500）
- 取数方式: 期望 `dict` 响应 `{"results":[…]}`（**mock 表驱动，真实解析同样缺失**，L16、L516-517）；
  `transport=None` 时**退回 `HttpxTransport`**（不是 `default_transport`，L490-492）
- 清洗: `_to_card` 转结果卡片；归一号去重保序；无法识别标准号的行跳过并 WARN（L480、L519-529）
- 失败语义: 非 200 返回 `[]`（不抛，L510-514）；超时 UPD-1001 / 不可达 UPD-1004（L501-508）；
  `drill_level>3` → UPD-3002（L485-488）
- 回答: **找标（分类→候选标准清单）**；不回答状态/效力
- 覆盖: 名义上 openstd 分类检索；**明确不覆盖**：真实网络（同 web/govcn 的 mock-only 问题）
- 反爬: 走 `HttpxTransport`（**无指纹模拟**）→ 对 openstd 这类 JA3 WAF 站更易被掐

---

## 3. 汇总表 1：渠道 × 类别 × 是否被 inspector 降级链使用 × 覆盖范围

| # | channel_id | 类别 | 在 `routing` 链里？ | 巡检实际可达？ | 覆盖范围（简） | 明确不覆盖 |
|---|---|---|---|---|---|---|
| 1 | `official_gb` | 国标（GB/GB-T/GB-Z） | ✅ 兜底第 1 棒（`routing.py:31`） | ✅ | 国标全文公开系统收录 GB 族 | GB 50xxx/55xxx、行标、地标、团标、法规；无废止日期 |
| 2 | `web` | 通用网页补漏 | ✅ 兜底第 2 棒 | ⚠️ **代码路径恒 miss**（只解析 mock dict，`web_fallback.py:52-61`） | 名义全类别 | 真实 HTML 响应——实际无覆盖 |
| 3 | `govcn` | 部委/国务院公告 | ✅ 兜底第 3 棒 | ⚠️ **代码路径恒 miss**（只解析 mock dict，`govcn_announce.py:60-65`） | 名义 gov.cn 公告检索 | 标准号级官方状态、真实 HTML 响应 |
| 4 | `laws_db` | 法规（flk） | ❌ `routing` 无规则 | ❌ | flk 全库法规（权威 sxx） | 一切"标准" |
| 5 | `ndls` | 跨门类标准（权威状态） | ✅ 首选：`AQ*`/`GB*`/`GB 50xx`(L21-24) | ✅ | 国标+行标+建标；含废止日期与代替链 | 法规；详情不可达时无废止日期 |
| 6 | `std_samr_hb` | 行业标准目录（JSON） | ❌ `routing` 无规则 | ❌ | std.samr 行业标准目录 ~10.8 万条 | 国标（total=0 诚实 miss）、地标、团标、法规；无废止日期 |
| 7 | `hbba` | 行业标准（sacinfo） | ✅ `MT/YB/JB/HG/QB/NY/SL/SN/SH/JG/CJ…`(L27) | ✅ | sacinfo 行业标准全库；含 `fzDate` 废止日期 | 国标、地标、团标、法规 |
| 8 | `dbba` | 地方标准（sacinfo） | ✅ `DB\d`(L26) | ✅ | sacinfo 地方标准全库 | 省级自建平台、国标、行标、团标、法规 |
| 9 | `ttzb` | 团体标准 | ✅ `^T/`(L22) | ✅ | 团标检索 + JSON-LD 详情 | 废止团标（无法按号定位，按查无处理）；付费全文 |
| 10 | `mee` | 生态环境 HJ | ✅ `^HJ`(L25) | ✅ | HJ 标准报告 + **全文 PDF 直链逆向** | 现行性/废止（无状态列）；其他部委、国标、地标、法规 |
| 11 | `mem_gov` | 应急部 AQ 公告 | ❌ `routing` 无规则（AQ 被路由到 ndls） | ❌ | 应急部公告（近 2 页 × ≤8 详情） | AQ 目录全量、废止日期、现行性字段；docstring 提到的全文页未实现 |
| 12 | `mohurd` | 住建部建标文告 | ❌ `routing` 无规则（GB 50xx 被路由到 ndls） | ❌ | 住建部文告（近 2 页 × ≤8 详情） | 建标目录全量、状态字段、附件全文 |
| 13 | `cssn` | 全门类国标（含 openstd 不收录者） | ❌ `routing` 无规则 | ❌ | **全门类国标**（食安 GB 5009.x、工程 GB 5xxxx、GB/Z） | 行标、地标、团标、法规；无废止日期；验证码被吞成 miss |

> 补充：`mem_gov`/`mohurd`/`std_samr_hb`/`laws_db`/`cssn` 这 5 个虽然不在链里，
> 仍会被 `_build_adapters` 实例化（`inspector.py:396-406`）——即"构造了但永不使用"。
> 其中 `cssn` 恰是工程脚本的**默认主渠道**（`scripts/std_status_check.py:173`），
> 也就是说"人肉跑的体检"和"引擎跑的巡检"用的是两套渠道集。

---

## 4. 汇总表 2：`law_source/*` 与 `update/channels/*` 的重叠与分工

| 同一来源 | 路径 A（巡检层） | 路径 B（法源/知识层） | 分工与重叠 |
|---|---|---|---|
| **flk.npc.gov.cn** | `channels/laws_db.py`（`POST /law-search/search/list`，只取 sxx 状态，`laws_db.py:32-42`） | `law_source/flk_client.py`（同端点 + `enumData` + `flfgDetails` + `download/pc`，`flk_client.py:17-21`）；`verify.py` 也直接打 `flfgDetails`（`verify.py:252-255`） | **同一端点的两条路**：A 是巡检用薄封装（且**未接线**），B 是入库/目录/核验的厚客户端。**状态映射表被维护了两份**：`laws_db.SXX_LEGAL`（L20-25）与 `verify.FLK_SXX_MAP`（L57-62）逐字相同但各自独立 |
| **sousuo.www.gov.cn** | `channels/govcn_announce.py`（`GET /sousuo/search.shtml`，页面 URL，`govcn_announce.py:48`）+ `announce.py`（用户自定义任意源，`announce.py:187-189`） | `law_source/govcn_client.py`（`GET /search-gov/data`，**真数据接口**，`govcn_client.py:20`） | **三条路打同一主机**，只有 B 命中真接口；A 的两条（govcn 适配器 / 用户源）都是"抓页面 + 启发式"，且 govcn 适配器在真实 HTML 下恒 miss |
| **www.cssn.net.cn** | `channels/cssn.py`（`GET /api/standards/list`，状态/CCS/ICS，`cssn.py:69`） | `knowledge/ccs_fetcher.py`（`GET /api/cssn/list`，只取 CCS，`ccs_fetcher.py:17`） | **同主机不同端点，功能重叠**：`cssn.py` 的 raw 已带 `a825/a825name/a826/a826name`（L195-198），本可取代 `ccs_fetcher`，但两者未接线（ccs_fetcher 是入库管线在用） |
| **openstd.samr.gov.cn** | `channels/official_gb.py`（`GET /bzgk/std/std_list`，状态核验，`official_gb.py:41`） | `update/discover.py`（`GET /db/search`，找标检索，`discover.py:59-60`） | 同主机不同端点，职责不同（状态 vs 找标）；**但 discover 走 `HttpxTransport`（`discover.py:491`）而非 `default_transport()`，对 JA3 WAF 站更脆弱** |
| **std.samr.gov.cn** | `channels/std_samr_hb.py`（`GET /hb/search/hbPage`，行业标准目录，`std_samr_hb.py:51`） | 无 | 无重叠（该渠道是独有来源），但**巡检不可达** |
| **HTTP 纪律本身** | `channels/base.py`：`curl_cffi` chrome 指纹（L199-201）、**无域白名单**、无重试、状态码不抛（L324-358） | `law_source/http.py`：域白名单 5 主机（L21-27）、按 host 0.6s 限速（L34-45）、3 次指数退避（L57-68）、下载魔数校验（L122-135）；**plain requests + verify=False**（L82-84） | **两套纪律不共享**：指纹与白名单互不覆盖。`announce.py` 又有第三套（SSRF 严格版 L152-162 + 重定向开关）。**台账若要统一"有效性探测"，必须先决定用哪套 HTTP 纪律** |

---

## 5. 汇总表 3：缺口清单（业主想覆盖但**没有专用适配器**的类别）

| 缺口类别 | 现状 | 证据 |
|---|---|---|
| **地方标准（省级自建平台）** | 只有 `dbba`（sacinfo 一个平台），routing 只认 `^DB\d`；各省市场监管局/地方标准公开系统零适配器 | `routing.py:26`、`dbba.py:23-27` |
| **团体标准（废止面）** | 只有 `ttzb`，且**废止团标无法按号定位**（按查无处理） | `ttzb.py:20-23` |
| **国际标准** | **零适配器**。ISO/IEC/EN/ANSI/JIS 无任何渠道；ISO 9001:2015 落 `official_gb→web→govcn` 兜底 | `tests/test_update_routing.py:54`（`select_chain("ISO 9001:2015") == TRAIL`）、`routing.py:20-31` |
| **各部委行业标准公告** | 只有 3 家：`mem_gov`（应急，且不可达）、`mohurd`（住建，且不可达）、`mee`（生态环境，无状态列）。交通/水利/农业/卫健/工信/能源/铁路/民航/粮食/烟草/计量等**全无** | `mem_gov.py:23`、`mohurd.py:21`、`mee.py:41`；`routing.py:20-28` 无对应前缀 |
| **行业标准号前缀未进 routing 表** | `JJF/JJG`（计量）、`GJB`（军标）、`RB/T`（认证认可）、`GA`（公安）、`TSG`（特种设备）、`NB`（能源）、`DL`（电力）、`SY`（石油）、`TB`（铁路）、`JTG/JT`（公路/交通）、`WS`（卫生）、`YY`（医药）、`LY`（林业）、`FZ`（纺织）等 → **全部落 `official_gb→web→govcn`** | `routing.py:27`（前缀表只列 `MT/YB/JB/HG/QB/NY/SL/SN/SH/JG/CJ`） |
| **发布公告页（国标委/部级标准发布公告）** | 无专用适配器。`sac.gov.cn` 国家标准公告、行业标准备案公告、地方标准发布公告均无渠道；`govcn_announce` 名义覆盖但真实解析缺失 | `govcn_announce.py:55-65` |
| **法规/标准的"发布公告"与"标准文本页"** | `mem_gov` docstring 提到的 `…/bz/bzwb/index_N.shtml`（标准文本 PDF 直链）**代码未实现**；住建部附件走 `/api-gateway` 未做 | `mem_gov.py:6`（docstring）vs `mem_gov.py:39-101`（实现）；`mohurd.py:5` |
| **今天只能靠 `web_fallback` 兜底的** | 上表所有未命中前缀的号 + 国际标准 + 全部"未知前缀"类别（`XYZ 9999-2099` 类）。**而 `web_fallback` 的真实路径恒 miss**（只解析 mock dict）→ 结论：**这些号今天在巡检里实际是"权威渠道查不到就 gray/not_found，没有真正的兜底网络"** | `routing.py:31,42-48`（无特征 → `_FALLBACK`）、`web_fallback.py:52-61` |
| **台账三列本身**（链接/有效性/上次成功查询） | ① **链接不可直接信**：`official_gb.evidence_url` 是 `showInfo:<hcno>` 伪协议（`official_gb.py:80`），只有 `scripts/std_status_check.py:84-88` 做了到 `newGbInfo?hcno=` 的转换；`cssn` 的证据 URL 疑似拼错（`cssn.py:193`）；`govcn_announce` 用 `_MINIMAL_PDF` 占位保证"有文件"（`govcn_announce.py:38-41,147-150`）。② **有效性无统一口径**：`announce.py` 有逐源 `status/reason`（可做模板），巡检渠道**没有任何 status/上次成功查询字段**——`update_change_event` 只有 `source_channel` 与 `evidence_url`（`inspector.py:438-446`） | 见左列行号 |

---

## 6. 拆解中发现的最该警惕的三件事（给台账设计者的警示）

1. **`web` 与 `govcn` 这两个"兜底棒"在真实网络下恒 miss。**
   `web_fallback.py:52-61` 与 `govcn_announce.py:60-65` 都只有 `if isinstance(body, dict)`
   一条解析分支（mock 契约），真实响应是 HTML → 0 条 → `_miss`。
   后果：`routing._FALLBACK`（`routing.py:31`）名义上是三棒降级链，
   实际只有第 1 棒 `official_gb` 在干活；"兜底"是设计幻觉。
   台账如果按"渠道数"统计覆盖率，会把两个空渠道算成能力。
2. **5 个已注册适配器永远不会被巡检调用，其中恰好包含团队实际在用的主渠道。**
   `laws_db` / `mem_gov` / `std_samr_hb` / `mohurd` / `cssn` 都不在 `routing` 的任何链上
   （`routing.py:20-31`），但都在 `ADAPTER_CLASSES` 里（`channels/__init__.py:41-57`）
   并被实例化（`inspector.py:396-406`）。更靠前的是：`cssn` 是
   `scripts/std_status_check.py:173` 的**默认主渠道**（团队体检用它跑全量国标），
   而引擎巡检一次都不会用它。**"人工体检"与"引擎巡检"用的是两套渠道集**，
   这会让"上次成功查询"这个台账字段在两条流程间不可比。
3. **代理轮换/限速随机化只活在脚本里，引擎里没有；且有两条渠道的反爬语义会骗过暂停机制。**
   `proxy_rotate.py` 全仓只被 `scripts/std_status_check.py:49-53` import；
   `inspector` 侧无任何代理/退避接线 → 巡检跑 `ndls`（Jiasule，超阈值后实测 100% 拦截
   30min+，`proxy_rotate.py:4-8`）只有"3 次尝试耗尽记 failed"（`inspector.py:344,390-393`）。
   同时 `cssn.py:111-112` **主动把验证码吞成 miss**（源码注释自认），
   于是 F-11 的"半自动过点"（`UPD-1002` → 批次 paused → 人工）对 cssn 完全失效；
   `govcn` 归档还会在下载失败时写一个**空占位 PDF** 并记为 `pdf_archived_placeholder`
   （`govcn_announce.py:147-150`）——三者合起来意味着
   **"渠道台账"的三列（链接 / 有效性 / 上次成功查询）今天都不能直接采信**。

---

## 7. 机器可读附录

```json
[
  {
    "id": "official_gb",
    "name": "国家标准全文公开系统",
    "category": "国家标准",
    "adapter_file": "src/core/update/channels/official_gb.py",
    "endpoint": "GET https://openstd.samr.gov.cn/bzgk/std/std_list?searchText=<号>&p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=<号>",
    "fetch_kind": "服务端渲染 HTML 表格（curl_cffi chrome 指纹 transport）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "国标全文公开系统收录的 GB/GB-T/GB-Z（约 97% 存量）；状态取 span 状态串，无废止日期列",
    "gaps": "GB 50xxx/55xxx 工程建设标准、行业标准、地方标准、团体标准、法规；evidence_url 是 showInfo:<hcno> 伪协议不可直接点开",
    "needs_proxy": false
  },
  {
    "id": "web",
    "name": "网络逐号补漏搜索（Bing）",
    "category": "通用网页兜底",
    "adapter_file": "src/core/update/channels/web_fallback.py",
    "endpoint": "GET https://www.bing.com/search?q=<标准号 标准名>",
    "fetch_kind": "预期 JSON（mock）；实际响应为 HTML，代码无解析分支",
    "answers": ["发布", "修订", "废止"],
    "covers": "名义上全类别兜底；代码路径下真实响应恒 miss（仅解析 dict 契约）",
    "gaps": "真实 HTML 响应零解析；无 UA/Referer；无验证码判定；无重试限速",
    "needs_proxy": false
  },
  {
    "id": "govcn",
    "name": "gov.cn 公告检索 + PDF 存档",
    "category": "政府公告",
    "adapter_file": "src/core/update/channels/govcn_announce.py",
    "endpoint": "GET https://sousuo.www.gov.cn/sousuo/search.shtml?q=<标准号 标准名>；归档用 transport.fetch_bytes(pdf_url)",
    "fetch_kind": "预期 JSON（mock）HTML 未解析；PDF 走原始字节 + %PDF 魔数校验",
    "answers": ["发布", "废止", "现行性"],
    "covers": "名义上 gov.cn 公告检索；状态由标题含「废止」/版本号相等启发式判定",
    "gaps": "真实 HTML 响应恒 miss；无标准号级官方状态字段；下载失败会写空占位 PDF 并记成功",
    "needs_proxy": false
  },
  {
    "id": "laws_db",
    "name": "国家法律法规数据库（flk.npc.gov.cn）",
    "category": "法律法规",
    "adapter_file": "src/core/update/channels/laws_db.py",
    "endpoint": "POST https://flk.npc.gov.cn/law-search/search/list（JSON body，pageNum=1/pageSize=20）",
    "fetch_kind": "JSON 查询接口（真实解析）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "flk 全库法规；状态取行内 sxx 码（1废止/2被修改/3有效/4未生效）",
    "gaps": "一切「标准」不覆盖；不在 routing 降级链上，inspector 永不调用；flk 有 JA3 WAF",
    "needs_proxy": false
  },
  {
    "id": "ndls",
    "name": "国家数字标准馆（中国标准化研究院）",
    "category": "跨门类标准状态权威",
    "adapter_file": "src/core/update/channels/ndls.py",
    "endpoint": "POST https://ndls.cnis.ac.cn/api/standard/list（JSON）+ GET https://ndls.cnis.ac.cn/api/standard/detail/<id>",
    "fetch_kind": "JSON 查询接口（搜索 + 详情两段，可只发搜索）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "跨门类标准目录；含废止日期 a206 与代替链 a461list/a462list；AQ 与 GB 系首选状态源",
    "gaps": "法规不覆盖；Jiasule WAF 超阈值后 30min+ 全拦截；详情不可达时无废止日期；巡检侧无代理轮换",
    "needs_proxy": true
  },
  {
    "id": "std_samr_hb",
    "name": "全国标准信息公共服务平台·行业标准目录",
    "category": "行业标准",
    "adapter_file": "src/core/update/channels/std_samr_hb.py",
    "endpoint": "GET https://std.samr.gov.cn/hb/search/hbPage?searchText=<归一号>&op=&ISSUE_DATE=",
    "fetch_kind": "JSON 查询接口（真实解析）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "行业标准目录约 10.8 万条；STATE 状态 + ISSUE_DATE/ACT_DATE",
    "gaps": "国标（total=0 诚实 miss）、地方标准、团体标准、法规；无废止日期字段；不在 routing 链上巡检不可达；searchText 必须传归一号否则退化为全库 match-all",
    "needs_proxy": false
  },
  {
    "id": "hbba",
    "name": "行业标准信息服务平台（sacinfo）",
    "category": "行业标准",
    "adapter_file": "src/core/update/channels/hbba.py",
    "endpoint": "POST https://hbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20&key=<号>）",
    "fetch_kind": "JSON 查询接口（真实解析）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "sacinfo 行业标准全库；含 fzDate 废止日期与「有更新版」被代替语义；日期为 epoch 毫秒(CST)",
    "gaps": "国标、地方标准、团体标准、法规不覆盖",
    "needs_proxy": false
  },
  {
    "id": "dbba",
    "name": "地方标准信息服务平台（sacinfo）",
    "category": "地方标准",
    "adapter_file": "src/core/update/channels/dbba.py",
    "endpoint": "POST https://dbba.sacinfo.org.cn/stdQueryList（form: current=1&size=20&key=<号>）",
    "fetch_kind": "JSON 查询接口（真实解析，与 hbba 同一基类）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "sacinfo 地方标准全库；routing 按 ^DB\\d 路由；含 fzDate 与 reviseStdCodes",
    "gaps": "省级自建地方标准平台零适配器；国标、行标、团标、法规不覆盖",
    "needs_proxy": false
  },
  {
    "id": "ttzb",
    "name": "全国团体标准信息平台",
    "category": "团体标准",
    "adapter_file": "src/core/update/channels/ttzb.py",
    "endpoint": "POST https://www.ttbz.org.cn/cms-proxy/ms/portal/standardInfo/getPortalStandardList（form: pageNo=1&pageSize=20&searchKey=<号>）+ GET https://www.ttbz.org.cn/standardDetail/<sid>.html",
    "fetch_kind": "JSON 查询接口 + 静态 HTML 详情（JSON-LD / portal JSON / el-tag 状态行三处解析）",
    "answers": ["发布", "废止", "现行性", "编号核验"],
    "covers": "团体标准 T/ 检索与详情；日期含 publishDate/implementDate/filePublishDate/abolishDate",
    "gaps": "废止团标无法按号定位（getDisabledStandardList 的 standardUniqueId 恒 null，按查无处理）；付费全文不做",
    "needs_proxy": false
  },
  {
    "id": "mee",
    "name": "生态环境部 HJ 标准",
    "category": "部委行业标准（生态环境）",
    "adapter_file": "src/core/update/channels/mee.py",
    "endpoint": "POST http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1520238134405（form: doctitle=<号>）",
    "fetch_kind": "服务端渲染报告页 HTML（含隐藏列的全文 PDF 直链逆向）",
    "answers": ["发布"],
    "covers": "生态环境部国家环境保护标准报告；给出实施时间与全文 PDF URL（colid=7 隐藏列逆向，http→https）",
    "gaps": "报告页无状态列 → 不判现行性/废止/被代替；其他部委、国标、地方标准、法规不覆盖；doctitle 空格敏感（HJ819-2017 查不到）",
    "needs_proxy": false
  },
  {
    "id": "mem_gov",
    "name": "应急管理部 AQ 行业标准公告",
    "category": "部委行业标准公告",
    "adapter_file": "src/core/update/channels/mem_gov.py",
    "endpoint": "GET https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/（+ index_N.shtml 分页，逐条公告详情页）",
    "fetch_kind": "HTML 列表页 + HTML 详情页（正则解析，预算 2 页 × 8 详情）",
    "answers": ["发布", "废止"],
    "covers": "应急管理部标准公告（标题含批准/发布/废止），正文含标准号级清单",
    "gaps": "仅最近 2 页公告；AQ 目录全量、废止日期、现行性字段不覆盖；docstring 提到的标准文本页 bzwb/index_N.shtml 未实现；不在 routing 链上巡检不可达（AQ 被路由到 ndls）",
    "needs_proxy": false
  },
  {
    "id": "mohurd",
    "name": "住建部工程建设标准文告",
    "category": "部委行业标准公告",
    "adapter_file": "src/core/update/channels/mohurd.py",
    "endpoint": "GET https://www.mohurd.gov.cn/gongkai/zc/wgk/（+ index_N.shtml 分页，逐条文告详情页）",
    "fetch_kind": "HTML 列表页 + HTML 详情页（正则解析，预算 2 页 × 8 详情）",
    "answers": ["发布", "废止"],
    "covers": "住建部文告列表（标题含批准/发布/印发/废止），详情含标准号",
    "gaps": "仅最近 2 页；建标目录全量与状态字段不覆盖；附件走 /api-gateway 未做全文；不在 routing 链上巡检不可达（GB 50xx 被路由到 ndls）",
    "needs_proxy": false
  },
  {
    "id": "cssn",
    "name": "中国标准服务网",
    "category": "国家标准（全门类）",
    "adapter_file": "src/core/update/channels/cssn.py",
    "endpoint": "GET https://www.cssn.net.cn/api/standards/list?keyword=<标准号（保留空格）>",
    "fetch_kind": "JSON 查询接口（真实解析，跨 GB/GB-T/GB-Z 前缀同主体挑选）",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "covers": "全门类国标（含 openstd/std.samr 不收录的食品安全 GB 5009.x、工程建设 GB 5xxxx、GB/Z）；raw 带 CCS/ICS 分类",
    "gaps": "行业标准、地方标准、团体标准、法规不覆盖；无废止日期列；验证码被吞成 miss 不触发 UPD-1002 暂停；证据 URL 疑似拼错（/cssn/index/list?keyword=）；不在 routing 链上巡检不可达",
    "needs_proxy": false
  },
  {
    "id": "flk_client",
    "name": "国家法律法规数据库官方源客户端",
    "category": "法律法规（采集/核验，非 ChannelAdapter）",
    "adapter_file": "src/core/knowledge/law_source/flk_client.py",
    "endpoint": "POST /law-search/search/list · GET /law-search/search/flfgDetails?bbbs= · GET /law-search/download/pc?format=docx|pdf&bbbs=（host flk.npc.gov.cn）",
    "fetch_kind": "JSON API + 签名文件下载（law_source/http.py：域白名单 + 0.6s 限速 + 3 次退避 + 魔数校验）",
    "answers": ["发布", "修订", "废止", "现行性"],
    "covers": "flk 全库法规；verfy_law 把 sxx 映射为 effective/superseded/withdrawn/upcoming 并分级 TTL 缓存",
    "gaps": "任何标准（GB/DB/T/ISO）不覆盖；用 plain requests + verify=False 无指纹，flk 的 JA3 WAF 可能握手失败；sxx 映射表与 laws_db 重复维护两份",
    "needs_proxy": false
  },
  {
    "id": "govcn_client",
    "name": "国务院政策文件库官方源客户端",
    "category": "法律法规（采集/核验，非 ChannelAdapter）",
    "adapter_file": "src/core/knowledge/law_source/govcn_client.py",
    "endpoint": "GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=…&searchfield=title|content&type=gwyzcwjk；详情页 HTML 解析",
    "fetch_kind": "JSON 查询接口（真数据接口）+ HTML 详情页 + docx/ofd 下载",
    "answers": ["发布"],
    "covers": "国务院文件/部门文件/解读；详情页取正文并只保留白名单域下载链接；无下载链接时用正文生成 docx",
    "gaps": "标准号级状态不覆盖；与 govcn_announce 适配器打同一主机但只有本条命中真接口",
    "needs_proxy": false
  },
  {
    "id": "announce_sources",
    "name": "用户自定义公告源（现有台账形态）",
    "category": "用户配置公告源",
    "adapter_file": "src/core/update/announce.py",
    "endpoint": "用户配置的任意公网 http/https 列表页 URL（app_config 键 announce.sources）",
    "fetch_kind": "HTML 列表页启发式解析（零 LLM：正则抽 a 标签 + 噪声过滤 + 日期/标准号识别）",
    "answers": ["发布"],
    "covers": "源数 ≤50 的任意公网列表页；逐源 status/reason 健康态 + 最近快照 + Excel 导出；首扫基线语义",
    "gaps": "不覆盖无 feed 的 JS 渲染站、需登录站、内网（SSRF 严格版一律 422）；只回答「有没有新公告」，不回答现行性/废止/全文",
    "needs_proxy": false
  },
  {
    "id": "ccs_fetcher",
    "name": "中国标准服务网 CCS 分类抓取",
    "category": "分类号（非状态渠道）",
    "adapter_file": "src/core/knowledge/ccs_fetcher.py",
    "endpoint": "GET https://www.cssn.net.cn/api/cssn/list?keyword=<数字号>",
    "fetch_kind": "HTML 列表页正则解析（httpx，超时 20s）",
    "answers": [],
    "covers": "CSSN 站点 CCS 分类（【CCS分类】<code><名称>）；另支持 KS_CCS_SEED_FILE 种子零网络返回",
    "gaps": "不回答状态/效力；与 channels/cssn.py 同主机不同端点，功能与 cssn 的 raw 字段重叠但未接线",
    "needs_proxy": false
  },
  {
    "id": "discover_search",
    "name": "找标检索（openstd 分类检索）",
    "category": "找标（非状态渠道）",
    "adapter_file": "src/core/update/discover.py",
    "endpoint": "GET https://openstd.samr.gov.cn/db/search?q=<分类路径 标准>&page=<drill_level>",
    "fetch_kind": "预期 JSON（mock）；走 HttpxTransport（无指纹），真实响应无解析分支",
    "answers": [],
    "covers": "名义上按 CCS 分类路径出候选标准卡片（drill_level ≤3）",
    "gaps": "不回答状态/效力；真实 HTML 响应无解析；用 HttpxTransport 而非 curl_cffi，对 JA3 WAF 站更脆弱",
    "needs_proxy": false
  }
]
```
