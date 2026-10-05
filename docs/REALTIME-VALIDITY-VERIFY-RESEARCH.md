# 法规/国标效力「打开即核验」实施细节报告

> 研究对象：**ZongziForu/cn-law-hub**（main，62★）与 **SocialSisterYi/OpenSTD_Spider**（main，91★）源码。
> 目的：为 KnowledgeStation 预览窗口的「打开即实时核验」（徽章 现行有效/已废止/已修改 + 官方证据链接）提供可直接照写的适配器细节。
> 所有端点/字段均标注来源文件与行号，便于回查。调研日期见 git 记录；外部站点字段可能漂移，接入时以一次真实抓包复核为准。

---

## 0. 结论摘要（TL;DR）

1. **显式效力状态只有三类源有**：
   - `flk.npc.gov.cn`：结构化整型字段 `sxx`（1=已废止 2=已修改 3=现行有效 4=尚未生效）——最强，直接给徽章；
   - `openstd.samr.gov.cn`：列表/详情页状态 `<span>` 文本（现行/即将实施/废止/暂不实施，KS 另观察到「被代替」）；
   - `xzfg.moj.gov.cn`：查询参数 `effect`（1=现行有效 2=已废止）+ 条目文本含「现行有效/已修改」。
   - **其余 7 个源（税务/党内/规章库/最高法/国防部/MEE/条约/政策文件库）都没有显式效力字段**。cn-law-hub 的铁律（SKILL.md L74-82）：无显式字段就必须输出「官方页面未明确标注效力状态」，**禁止从可访问性或发布日期推断**——这条应原样搬进我们的核验契约。
2. **打开即核验的路由**应以「入库时记录的来源渠道」为主路由、标题精确检索 flk 为兜底；无搜索 API 的静态站（12371/mod/court/mee/treaty）只做「证据链接活性检查」，不做实时状态判定。
3. **交互预算**：cn-law-hub 是批量爬虫语义（限速器 auto≤10 关闭），打开即核验是交互语义——单请求 5s 超时 + 总预算 8s + 失败返回灰色「未核验」徽章，绝不阻塞预览。
4. **反爬基座直接复用现有代码**：`base.py` 的 `CurlCffiTransport`（chrome 指纹）已点名覆盖 `openstd/std.samr/flk.npc.gov.cn` 的 JA3 WAF；`ChannelResult` 字段与徽章契约几乎一一对应。

---

## 1. 数据源逐个拆解（端点 + 参数 + 响应 + 状态映射）

### 1.1 国家法律法规数据库 flk.npc.gov.cn —— 徽章主数据源 ⭐

来源：`scripts/download.py`、`references/api_reference.md`

**详情接口（核验首选，单次调用出状态）**
```
GET https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs={bbbs}
```
响应 `data` 关键字段（api_reference.md L24-44）：

| 字段 | 含义 | 示例 |
|---|---|---|
| `bbbs` | 唯一 ID | `ff80808172b5f...` |
| `title` | 标题 | |
| `flxz` | 分类（法律/行政法规/…） | |
| `zdjgName` | 制定机关 | 全国人大常委会 |
| `gbrq` / `sxrq` | 公布日期 / 施行日期 | YYYY-MM-DD |
| `sxx` | **时效性状态码** | 见下表 |
| `ossFile.*` | docx/pdf/ofd 相对路径（不可直连，见坑） | |

**状态码权威映射**（download.py L73 `_SXX_MAP`；SKILL.md L39-46 同）：

| sxx | 含义 | → KS `legal_status` | 徽章 |
|---|---|---|---|
| 1 | 已废止 | `withdrawn` | 红 |
| 2 | 已修改 | `superseded` | 黄 |
| 3 | 现行有效 | `effective` | 绿 |
| 4 | 尚未生效 | `upcoming` | 蓝 |

> 注意 api_reference.md L46 有一处旧注释「1=?, 3=有效」，以 download.py 的 `_SXX_MAP` 为准（SKILL.md 状态过滤表完整列出四值）。

**搜索接口（由标题找 bbbs）**
```
POST https://flk.npc.gov.cn/law-search/search/list
Content-Type: application/json
Referer: https://flk.npc.gov.cn/search
```
payload（download.py L117-131 实测可用，api_reference.md L72-103 字段全解）：
```json
{"searchRange":1,"sxx":[],"searchType":1,"searchContent":"物业管理条例",
 "orderByParam":{"order":"-1","sort":""},"pageNum":1,"pageSize":20,
 "sxrq":[],"gbrq":[],"xgzlSearch":false,"flfgCodeId":[],"zdjgId":[],"gbrqYear":[]}
```
- `searchRange`: 1=标题 / 2=正文；`searchType`: **1=精确 / 2=模糊**（核验场景用 1）；`sxx` 数组可作状态过滤；
- 响应 `{code:200,total,rows:[{bbbs,title,flxz,zdjgName,gbrq,sxrq,sxx,...}]}` —— **rows 里就带 sxx**，多数情况搜索一步即可出徽章，不必再打详情；
- 辅助：`GET /law-search/search/enumData`（全部下拉枚举）、`GET /law-search/prompts/search?title=`（联想）、`POST /law-search/search/hitDisplay`（高亮命中）。

**官方原文下载**（api_reference.md L134-155；download.py L192-225）：
```
GET https://flk.npc.gov.cn/law-search/download/pc?format={docx|pdf}&bbbs={bbbs}
→ {code:200,data:{url:"https://flkoss.obs-bj2.cucloud.cn/...?X-Amz-Signature=...",urlIn:内网勿用}}
```
再 GET `data.url` 拿签名 OSS 文件。**必须带 `Referer: https://flk.npc.gov.cn/detail?id={bbbs}`**。

**已知坑**（照抄进我们的实现注释）：
- 详情里的 `ossFile` 相对路径直连会返回 SPA index 页（api_reference.md L208-221）→ 只走 download API；
- `format=pdf` 可能 code=200 但 `data` 为空 → 回退 docx（L154）；
- `orderByParam.order` 升序值会 500，固定用 `"-1"`（L96）；
- 响应若 `text/html 且 <5000B` = 被拦/异常（download.py L211-213 的守卫）。

**自研建议**：新建 `channels/flk_law.py`，`probe_law(title)`：精确标题搜索 → 唯一命中取 rows[0].sxx 出结果；多命中时按 `flxz`+最新 `gbrq` 挑选并把候选列表放 `raw`；零命中返回 found=False。evidence_url 固定 `https://flk.npc.gov.cn/detail?id={bbbs}`。

---

### 1.2 国家标准全文公开系统 openstd.samr.gov.cn（OpenSTD_Spider）

来源：`openstd_spider/request.py`、`parse/openstd.py`、`utils.py`、`schema.py`

**搜索接口**（request.py L75-89）：
```
GET https://openstd.samr.gov.cn/bzgk/gb/std_list        # spider 用路径
# KS ANOM-003 实测：/bzgk/gb/std_list 会重定向，真实列表为
GET https://openstd.samr.gov.cn/bzgk/std/std_list       # official_gb.py L35，推荐采用
```
参数映射（request.py L77-88，逐个对应）：

| 参数 | 含义 | wire 值 |
|---|---|---|
| `r` | 缓存穿透 | `random.random()` |
| `page` / `pageSize` | 分页 | pageSize 上限 50（cli.py L272 min=10 max=50） |
| `p.p1` | 类型 StdType | **0=全部 1=GB 2=GBT 3=GBZ**（schema.py L33-37） |
| `p.p2` | 关键词/标准号 | 如 `GB 18030-2022` |
| `p.p5` | 状态 StdStatus | **空/PUBLISHED/TOBEIMP/WITHDRAWN/NOTIMP**（schema.py L25-30） |
| `p.p6` / `p.p7` | 分类 / 日期 | 可空 |
| `p.p90` / `p.p91` | 排序字段/方向 | KS 现用 `circulation_date`/`desc` |

响应为服务端渲染 HTML，解析锚点（parse/openstd.py L52-77）：
- 结果表 `table.result_list > tbody:nth-of-type(2) > tr`；
- 每行列：td2=标准号链接，**hcno 从 `onclick` 提取：`row.a["onclick"][10:-3]`**（形如 `showInfo('XXXX')`；hcno 为 `[0-9A-F]{32}` 大写十六进制，utils.py L5）；
- td3=采标 span（有则 is_ref）、td4=中文名、td6=状态 span 文本、td7/td8=发布/实施日期 ISO；
- 页脚 `div.hidden-xs>table>tr>td:nth-of-type(1)>span` 的 strings 第 8/11/12 位 = 总条数/页码/总页数（L70-77，脆，可改用正则取「共 N 页」）。

**状态文本映射**（utils.py L21-46，双向）：

| 页面文本 | spider 枚举 | → KS `legal_status` | 徽章 |
|---|---|---|---|
| 现行 | PUBLISHED | `effective` | 绿 |
| 即将实施 | TOBEIMP | `upcoming` | 蓝 |
| 废止 | WITHDRAWN | `withdrawn` | 红 |
| 暂不实施 | NOTIMP | 无对应（建议 raw 留存 + 灰蓝「暂不实施」） | |
| 被代替 | （KS official_gb 观察到，STATE_TEXT_MAP 已有） | `superseded` | 黄 |

未知文本不猜测 → `legal_status=None` + WARN（official_gb.py L82-85 已是该行为，保持）。

**元数据接口**（核验时可二跳确认）：
```
GET https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno={hcno}
```
解析（parse/openstd.py L10-49）：标准号在 `div.bor2 h1`（前缀「标准号：」；若以「您所查询的标准系统尚未收录」开头 → NotFoundError，L17-18）；中/英文名称在 `table.tdlist` tr1/tr2；**状态在 tr3 的 span**；tr4 的 `button.ck_btn` 在=允许在线预览、`button.xz_btn` 在=允许下载；CCS/ICS/主管/归口/发布单位/备注在各 `div.row`。

**PDF/全文下载（本项目核验功能不需要，但记录备查）**：
- 直链 PDF：`GET http://c.gb688.cn/bzgk/gb/viewGb?hcno={hcno}`，校验 `Content-Disposition` 以 `.pdf` 结尾否则 DownloadError（request.py L160-171）；**下载前需过人机验证**：`GET /gc?_<毫秒时间戳>` 取图 → OCR → `POST /verifyCode` body `{verifyCode, agreeIECTips:"true"}`，响应字面 `"success"` 即过（request.py L180-204）；OCR 实现=cvtColor 灰度 + 阈值 190 二值化 + 反相 + ddddocr，最多重试 10 次（captcha.py 全文；`__init__.py` L16-25）。**核验状态本身（std_list/newGbInfo）无验证码**——我们不做下载就完全绕开这道坎。
- 仅预览标准的下载 = 图块重组：`showGb?type=online&hcno=` 带 `Referer: https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno={hcno}` 解析 `div#viewer div.page`（页号 id、bg=webp 图 id、宽高），每页内 `span[class^="pdfImg"]` 按 class 后两位与 background-position 把 10×10 图块拼回页面（parse/gb688.py L16-81），reportlab A4 居中合成 PDF（pdf.py）。透明通道先铺白底（image_paste_white）。

**自研建议**：official_gb 已覆盖 std_list 主链路；补两点——① `_pick_row` 的「去年代取最大号」策略保留（spider 只做精确匹配并要求用户输入完整编号，cli.py L73-86，我们的容错更强）；② 新增 `newGbInfo?hcno=` 二跳拿「是否允许预览/下载」与归口单位，供预览窗口展示「官方在线预览」按钮。

---

### 1.3 司法部行政法规库 xzfg.moj.gov.cn（行政法规兜底源）

来源：`scripts/moj_law_crawler.py`

- 服务端渲染 HTML，搜索就是带参 GET（L45-46, L82-89）：
  ```
  GET https://xzfg.moj.gov.cn/search2.html
      ?SearchWord={关键词}&pageIndex={页}&pageSize={10}
      &searchField={1=标题|2=正文}&effect={1=现行有效|2=已废止}   # STATUS_MAP L49-53
  ```
- 解析（L99-203）：条目容器多选择器降级 `.searching-results-list .list-item → li`；**状态直接子串匹配文本**：`"现行有效" in text → 现行有效`、`"已修改" in text → 已修改`（L186-189）；日期用正则 `(\d{4}-\d{2}-\d{2})公布` / `施行`（L174-184）；总页数取 `input#page-count[value]`（L113-119）。
- **无独立详情 API**，detail_url 就是列表里的 `<a href>`（urljoin 补全）。

**状态映射**：现行有效→`effective`(绿)；已修改→`superseded`(黄)；查询参数筛 `effect=2` 得到的即 `withdrawn`(红)。文本没出现状态词 → None 不猜测。

**自研建议**：作为 flk 未命中行政法规时的第二跳；也可以反向用——`SearchWord=精确标题&effect=1` 若唯一命中即为「现行有效」证据，比解析更稳。

---

### 1.4 税务法规库 fgk.chinatax.gov.cn（KS 缺失源①）

来源：`scripts/tax_law_crawler.py`

- 列表 API 是 **www.chinatax.gov.cn 上的 POST JSON 接口**（注意域名不是 fgk）（L51）：
  ```
  POST https://www.chinatax.gov.cn/getFileListByCodeId
  Content-Type: application/json
  Referer: https://fgk.chinatax.gov.cn/zcfgk/{codeId}/listflfg.html
  {"codeId":"c102416","channelId":"<从页面发现>","page":1,"size":20,
   "sort":[],"relateSubChannels":false}
  ```
- **channelId 自发现**（L80-118）：GET 分类列表页（候选路径 `/zcfgk/{code}/listflfg.html`、`listflfg_fg.html`、`list_guizhang.html`，失败退首页），正则 `channelId\s*=\s*["']([^"']+)["']` 抽出并进程内缓存。
- **会话初始化**（L126-133）：requests.Session 先 GET `https://fgk.chinatax.gov.cn/` 拿 cookie 再调 API（SKILL.md L146「requires session cookie, auto-managed」）。
- 分类 codeId 表（L53-63）：法律 c100009 / 行政法规 c100010 / 国务院文件 c102440 / 税务部门规章 c100011 / 财税文件 c102416 / 税务规范性文件 c100012 / 其他文件 c100013 / 工作通知 c102424。
- 响应解析（L172-216）：`data.results.data.results[]`，字段 `titleHtml`、`subTitleHtml`、`url`（相对→urljoin）、`publishedTimeStr`；元数据在 `domainMetaList[] → {domainMetadataName, resultList:[{key,value}]}` 拍平，常用键：**`fz`/`writeno`=文号、`issuerDepartment`/`source`=发文机关、`effectivedate`=生效日期**。总数 `data.results.data.total`。
- 详情页 = 静态 `content.html`（如 `/zcfgk/c102416/c5250687/content.html`），h1/`.article-content` 多选择器抽取（L224-278）。
- **没有显式效力状态字段**（只有 effectivedate）→ 按 §0 铁律只能给「官方未标注」，evidence_url 给 content.html 链接。

**自研建议**：入库时若是税务渠道文档，保存 content.html 绝对 URL；核验时对该 URL 做 GET 活性 + 抽 `effectivedate` 元数据；状态徽章显示「收录于税务总局法规库（未标注时效）」。搜索是「拉列表后本地过滤标题」（L286-297），不适合实时逐次调用——**核验走「存储 URL 活性」而非「现场检索」**。

---

### 1.5 党内法规库 www.12371.cn（KS 缺失源②）

来源：`scripts/party_law_crawler.py`

- **完全没有搜索 API**（SKILL.md L144 明示「keyword filtering is client-side on titles only」）。
- 分类专题页：`https://www.12371.cn/special/dnfg/{cat}/`，cat ∈ zz 党章/tl 条例/gd 规定/bf 办法/gz 规则/xz 细则/zzfg 组织/ldfg 领导/zsjs 自身建设/jdbz 监督保障（L48-62）。
- 条目识别纯靠 URL 形状：href 匹配 `/\d{4}/\d{2}/\d{2}/` 且 `.shtml` 结尾、锚文本≥5 字符（L110-124）——如 `/2022/01/23/ARTI1642937162249109.shtml`。
- 详情解析 h1/.article-content；**发布日期兜底从 URL 路径抽** `/(\d{4})/(\d{2})/(\d{2})/`（L196-202）。无任何状态字段。

**自研建议**：定位为「证据链接 only」渠道——入库时保存文章 URL；核验 = URL 活性 + 标题一致性比对；徽章灰「党内法规库收录（无时效标注）」。绝不为它在打开预览时翻列表页（延迟不可接受）。

---

### 1.6 国家规章库 gov.cn/zhengce/xxgk/gjgzk（KS 缺失源③，成本最高的源）

来源：`scripts/gov_rules_crawler.py`、`references/gov_rules_api_reference.md`

私有 **Athena API + 动态 RSA 鉴权**，四步（gov_rules_api_reference.md L11-50；crawler L64-107）：
1. GET `https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm?searchWord=`，正则取 `<script src="(index\.js\?...)">`；
2. 下载 JS bundle，正则抽三参数：
   `var s="(base)",o=encodeURIComponent(a("(pub)","(seed)")),c=encodeURIComponent("(name)")`；
3. app_key = RSA(**PKCS1v15**, pub 包 PEM) 加密 seed → base64 → urlencode；
4. 之后所有请求带头 `athenaappname: {name}`、`athenaappkey: {key}`、`Referer: https://www.gov.cn/`。

查询（L51-52, L135-201）：
```
POST {base}/athena/forward/BD8730CDDA12515E2D9E1B21AA11C0D6
{"code":"18258ab0ac9","tableName":"t_1860c735d31","pageNo":1,"pageSize":500,
 "granularity":"ALL","trackTotalHits":"true",
 "searchFields":[{"fieldName":"f_202321807875","searchWord":"部门规章","searchType":"TERM"},
                 {"fieldName":"f_202321360426","searchWord":"标题词","searchType":"TERM"}],
 "sorts":[{},{"sortField":"f_202321915922","sortOrder":"DESC"}],
 "resultFields":["f_202321360426","doc_pub_url", ...]}
→ {"resultCode":{"code":200},"result":{"data":{"list":[...],"pager":{"total","pageCount"}}}}
```
字段映射（api_reference L72-84）：f_202321807875=分类(部门规章/地方政府规章)、f_202321360426=标题、f_202321758948=正文摘要、f_202321423473=文号、f_20232380533=主题词、f_202328191239=发文机关、f_202344311304=公布文告、f_202321915922=发布时间、`doc_pub_url`=详情页 URL。详情页正文 `.pages_content`，附件选择器 `a[href][appendix="true"]`（L230-250）。
**请求的 resultFields 里没有效力字段**——该库详情页人工可见「时效性」，但 crawler 未提取；若要接，需抓一次详情页确认 DOM 锚点后再写适配器。

**坑**：JS bundle 参数会过期，长任务遇 401/403 必须重新 discover（SKILL.md L142、api_reference L135）；字段名随前端改版漂移。

**自研建议**：「不引入第三方依赖」约束下 RSA-PKCS1v15 是唯一障碍（Python 标准库无 RSA）。三个选项按优先级：① Windows 上经 PowerShell 走 .NET `System.Security.Cryptography.RSACryptoServiceProvider` 加密（零 pip 依赖）；② 该渠道降级为「doc_pub_url 活性检查」（搜索结果里的详情 URL 可直接 GET，不走 Athena）；③ 暂缓。推荐 ②，把工程花在回报更高的 flk/moj 上。

---

### 1.7 最高人民法院发布栏目 www.court.gov.cn（KS 缺失源④）

来源：`scripts/court_law_crawler.py`

- 栏目分页列表（L79-83）：第 1 页 `https://www.court.gov.cn/fabu/gengduo/{cat}.html`，第 N 页 `{cat}_{N}.html`；栏目号：司法解释 16、司法文件 17（另有 重大案件 15/通知 22 等，L48-59）。
- 条目 = href 含 `/fabu/xiangqing/` 的 `<a>`（如 `/fabu/xiangqing/504221.html`，L117-125）；总页数从分页链接 `_(\d+).html` 与「尾页」锚取最大值（L136-153）。
- 详情（L163-214）：h1 标题；正文 `div.detail/div.txt_txt/...`；`发布时间[：:]\s*(YYYY-MM-DD HH:mm)` 与 `来源[：:]` 正则抽取。
- **无搜索 API、无效力字段**。司法解释的废止信息散见于清理公告（也是普通文章），无法结构化关联。

**自研建议**：同 12371 —— 「证据链接 only」。司法解释核验可加一跳 flk（国家法律法规数据库收录「司法解释」分类，flxz 枚举里有），能拿到 sxx 就升级为真徽章。

---

### 1.8 其余三源速览（已有/低优先）

| 源 | 端点要点 | 来源 | 效力字段 |
|---|---|---|---|
| 国务院政策文件库 | `GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=&searchfield=title\|content&sort=score\|pubtime&p=0起&n=10&type=gwyzcwjk&childtype=gongwen\|bumenfile\|otherfile&pubtimeyear=&bmfl=`；响应 `searchVO.catMap.{gongwen,bumenfile,otherfile}.listVO[{piclinksurl,pcode(文号),source,title(带<em>),pubtime(ms)}]`；无需鉴权 | gov_policy_api_reference.md 全文 | 无 |
| 外交条约库 | `https://treaty.mfa.gov.cn/web/allinfos.jsp?nPageIndex_={page}`（双边 shuangbian.jsp / 多边 duobian.jsp）；详情 `web/detail.jsp?treatyid=...`；纯 HTML | treaty_crawler.py L42-48 | 无 |
| 国防部法规文库 | `http://www.mod.gov.cn/gfbw/fgwx/index.html` 分类列表；条文 `gfbw/fgwx/flfg/{id}.html`；静态 HTML 无搜索 | mod_law_crawler.py L5,L46,L73-75 | 无 |
| 生态环境部 | `https://www.mee.gov.cn/ywgz/fgbz/{fl,xzfg,st hjshpczd→sthjshpczd,zfjs}/` + `/gzk/gz/`；静态列表 | mee_law_crawler.py L46-64 | 无（KS 已有 mee 渠道） |

---

## 2. 统一状态判定映射表（可直接抄成代码）

```python
# 归一枚举沿用 base.py LEGAL_STATUSES（schema CHECK 冻结）
FLK_SXX = {1: "withdrawn", 2: "superseded", 3: "effective", 4: "upcoming"}
OPENSTD_TEXT = {"现行": "effective", "即将实施": "upcoming", "废止": "withdrawn",
                "被代替": "superseded", "暂不实施": None}   # None → raw 留存+灰蓝徽章
MOJ_TEXT    = {"现行有效": "effective", "已修改": "superseded"}  # effect=2 查询 → withdrawn
NO_FIELD_SOURCES = {"tax", "party", "court", "mod", "mee", "treaty", "gov_policy",
                    "gov_rules"}   # 一律 legal_status=None + 「未标注」灰徽章
```

| 徽章 | 色 | 触发条件 | evidence_url |
|---|---|---|---|
| 现行有效 | 绿 | sxx=3 / 「现行」/「现行有效」 | flk detail?id= · openstd newGbInfo?hcno= · moj 详情 |
| 已废止 | 红 | sxx=1 / 「废止」/ effect=2 | 同上 |
| 已修改/被代替 | 黄 | sxx=2 / 「已修改」「被代替」 | flk detail（另查 xgwj 关联文件） |
| 尚未生效 | 蓝 | sxx=4 / 「即将实施」 | 同上 |
| 官方未标注效力状态 | 灰 | 无字段源找到原文 | 存量官方 URL |
| 未能核验 | 灰闪烁 | 超时/被拦/网络失败 | 无（提供重试按钮） |

cn-law-hub 的三条纪律必须写进核验服务（SKILL.md L76-82 原文精神）：① 只有官方页面/API 显式给出才允许宣称四种状态之一；② 无显式字段明说「未明确标注」；③ 永远返回 官方URL+文件类型+发布机关+发布日期+核验时间，即使状态缺失。

---

## 3. 「打开即核验」流程设计建议

### 3.1 时序

```
用户点开预览
  ├─ 前端立即渲染正文（不等核验）
  └─ 异步 GET /api/verify?doc_id=...
       后端 VerifyService：
       1) 查缓存（key=norm(no|title)+channel，见 3.3）→ 命中直接回
       2) 单飞锁：同 key 并发请求合并为一次上游调用
       3) 路由（按入库时记录的来源渠道 + 文档形状）：
          国标(GB/G B T/GBZ 号) ──► 复用 official_gb（std_list）→ 必要时 newGbInfo 二跳
          法律/行政法规/监察法规 ► flk_law：POST search/list(searchType=1,range=1)
                                        ├─ rows[].sxx 直接出状态
                                        └─ 行政法规未命中 → moj search2.html(effect=1)
          税务文档            ──► tax：存量 content.html 活性 + effectivedate
          党内/条约/司法/政策  ──► evidence-only：存量官方 URL 活性（HEAD/GET）
          其它/未知           ──► flk 标题精确检索兜底
       4) 组装 {status, status_raw, evidence_url, source_channel, checked_at, ttl}
       5) 写缓存
  └─ 前端徽章位渲染（骨架 → 徽章 / 灰「未能核验·重试」）
```

要点：
- **复用 `ChannelAdapter` 但别破坏冻结接口**：`probe(standard_no)` 契约不动（official_gb 直接复用）；新增兄弟方法 `probe_law(title, doc_no="") -> ChannelResult` 放在新基类 `LawVerifyAdapter(ChannelAdapter)`，transport/`_fetch`/日志规约全部继承。`ChannelResult` 字段够用：`legal_status`+`evidence_url`+`raw`（status_raw 放 raw）。
- **传输层零改动**：flk 在 `CurlCffiTransport` 注释点名的 JA3 WAF 名单里（base.py L159-162），`fetch(method="post", json=...)` 已支持（L176）。UA 常量参考两家：spider 的 Chrome/Edg 133 UA（request.py L19）、cn-law-hub 的 Chrome 120+`cn-law-hub/1.0` 尾缀（constants.py L13-16）——建议我们用自己的产品尾缀 UA。
- **并发策略**：交互场景与爬虫相反——不是限速而是抢时间。主路由单发即可（flk 一次搜索通常 <1s）；不要并行打多个官方站（浪费且易触发 WAF），仅在同一渠道超时后才降级到备选。

### 3.2 超时与降级（硬指标）

| 项 | 值 | 依据 |
|---|---|---|
| 单请求超时 | 5s（交互档），后台巡检仍用 30s | cn-law-hub 默认 30s 是爬虫档（ratelimit/http_request L208）；交互不可照抄 |
| 总预算 | 8s（主路由 5s + 一次降级 3s） | |
| 失败语义 | 返回 `{status:"unverified"}`，HTTP 200；**绝不抛错阻塞预览** | KS `recordable()` 同哲学：captcha 只标记不落库 |
| 验证码/拦截 | `looks_like_captcha()`（base.py L120-132）命中 → unverified+captcha 标记，前端灰徽章「需人工校验」 | F-11 半自动降级复用 |
| 重试 | 交互档不自动重试（用户点重试按钮）；后台刷新档才用 MAX_RETRIES=4、指数退避 BASE 1.0s×2^n cap 30s +30% 抖动、RETRYABLE={408,429,500,502,503,504}，401/403/404 不重试 | constants.py L11-24；ratelimit.py `_backoff` L187-190、http_request L215-283 |
| 限速 | 全局每 host 令牌桶 1 rps（防用户快速连开多文档）；后台批刷用 cn-law-hub 的自适应思路（429 → rps×0.6，连续成功 → ×1.1，区间 1–8 rps） | ratelimit.py L105-143 |

### 3.3 缓存策略（关键：按结果分级 TTL）

cn-law-hub 的分层 TTL（SKILL.md L68-70：搜索 1h / 详情 24h / DOCX 7d）迁移到核验场景：

| 结果 | TTL | 理由 |
|---|---|---|
| `effective`（现行有效） | 24h | 与其 detail 缓存一致；效力变更是低频事件 |
| `withdrawn` / `superseded` | 7d | 废止不会复活；黄/红徽章最值得长期缓存 |
| `upcoming`（尚未生效） | 6h | 有明确的到期翻转点，短一些 |
| 找到原文但无状态字段 | 12h | 只是活性证明，别频繁戳官方 |
| not_found / error | 60s 负缓存 | 防止坏文档反复打官方站 |
| captcha 拦截 | **不缓存**（只记半自动标记） | 对齐 `recordable()`：captcha 绝不当 miss |

实现形态建议直接借 `cache.py`：文件缓存 `~/.cache/<ns>/`，key=`sha256("channel|norm_no|norm_title")[:16]`（cache.py L28-30 同构），JSON 体 `{_cached_at, payload}`；但交互路径前置一层进程内 dict/LRU，避免每次开预览都摸盘。**单飞**：per-key `asyncio.Lock` 合并并发。

补充设计点：
- **checked_at 必须下发并在徽章 tooltip 显示**（cn-law-hub Validity Rules 第 4 条：永远返回 retrieval date）；
- 夜间巡检批次（现有 inspector）顺路批量刷新高频文档徽章 → 白天打开基本全走热缓存，官方接口压力趋近于零；
- 多版本同名文档（flk 精确标题仍多命中）时：徽章显示最新公布版本的 sxx，`raw.candidates` 留全部命中，前端 tooltip 列出版本对照——对应 cn-law-hub 第 5 条「同名/多版本要显式标记歧义」。

### 3.4 前端契约（建议）

```jsonc
// GET /api/verify?doc_id=<id>
{"doc_id":"...", "status":"effective|withdrawn|superseded|upcoming|unmarked|unverified",
 "status_raw":"现行有效",              // 官方原文字段/文本，原样透传
 "evidence_url":"https://flk.npc.gov.cn/detail?id=...",
 "source_channel":"flk_law",           // 与 ChannelResult.channel 同名空间
 "issuer":"全国人民代表大会常务委员会",
 "published_date":"2012-06-30", "effective_date":"2013-07-01",
 "checked_at":"2026-08-24T10:30:00+08:00", "ttl_hours":24}
```

---

## 4. 风险与坑清单（合并两项目踩坑，接入前逐条对照）

| # | 坑 | 出处 | 对策 |
|---|---|---|---|
| 1 | flk `orderByParam.order` 非 "-1" 会 500 | api_reference.md L96 | 写死 "-1" |
| 2 | flk `ossFile` 相对路径直连返回 SPA 页 | api_reference.md L208-221 | 只走 download/pc API |
| 3 | flk pdf 格式可能 data 空 | api_reference.md L154 | 回退 docx |
| 4 | flk/openstd 对 Python TLS 指纹掐连接 | KS base.py L159-162 ANOM-002 | 强制 curl_cffi chrome |
| 5 | openstd `/bzgk/gb/std_list` 重定向 | KS official_gb.py L33-35 ANOM-003 vs spider request.py L16 | 采用 `/bzgk/std/std_list`；follow_redirects 保持 False 以便识别 302 |
| 6 | openstd hcno 大写 32 hex，藏在 onclick 里 | spider utils.py L5、parse L61 | `onclick[10:-3]` 或正则 `showInfo\('([0-9A-F]{32})'\)` |
| 7 | openstd 详情「尚未收录」文案 = NotFound | spider parse L17-18 | 当 not_found 处理，负缓存 |
| 8 | gb688 全文下载有人机验证（OCR 10 连击） | spider `__init__.py` L16-25 | 核验功能不碰下载 → 天然绕开 |
| 9 | 税务 API 要 cookie + Referer + channelId 三件套 | tax_crawler L65-166 | Session 先访问首页；channelId 进程内缓存 |
| 10 | 规章库 Athena JS 参数过期 → 401/403 | gov_rules reference L135 | 重新 discover；或干脆走 doc_pub_url 直连 |
| 11 | Athena 字段名随改版漂移 | gov_rules reference L136 | 字段映射集中一处常量 + 启动探针校验 |
| 12 | 12371/mod/court/mee/treaty 无搜索 API | SKILL.md Key Notes L143-148 | 入库存 URL，运行期只做活性，不现场翻页 |
| 13 | 状态文本可能新增（如「暂不实施」KS 映射缺） | spider utils L43-44 | map 失败 → None + WARN（official_gb L82-85 已是此行为），枚举扩展走 migration |

---

## 5. 落地顺序建议（投入产出排序）

1. **flk_law 适配器**（1 天级）：一个 POST 出 sxx，覆盖 法律+行政法规+监察法规+司法解释+地方性法规，是最强单点；
2. **VerifyService + 缓存 + 徽章 API**（1-2 天）：§3 全套，先只挂 official_gb 与 flk_law 两个渠道即可上线；
3. **moj 兜底 + tax 活性检查**（各半天）：补行政法规与税务文档；
4. **evidence-only 渠道改造**（半天）：入库管道顺手存官方 URL（12371/court/treaty/mod/policy）；
5. **国家规章库**：按 §1.6 选项 ②（doc_pub_url 直连）低成本接入或暂缓。

---
*报告生成：ox-alpha（DeepSeek Harness 子代理）。源码快照留存于临时目录 research-src/（会话结束即弃），本文已含全部必要摘录。*
