# 中国标准类官方渠道实测调研

> 调研方式：本机 `curl.exe`（含 `--compressed` / `--data-urlencode`）与 PowerShell `Invoke-WebRequest` 直接抓取，
> 页面原文片段均来自本次实际响应体，不引用任何二手描述。
> 访问时间统一为 **2026-09-18**（Asia/Shanghai）。
> 三态标记：`✅ 已实测访问` / `⚠️ 未核实（只搜到名字）` / `❌ 实测打不开或不存在`。
> 每个渠道的"实测证据"字段给的是**页面/响应体里抓到的原文**，不是我的转述。

---

## 0. 本次调研最重要的三个发现（先看这个）

1. **`std.samr.gov.cn` 与 `*.sacinfo.org.cn` 暴露了免登录、免验证码的 JSON 接口**
   （`/gb/search/gbQueryPage`、`/hb/search/hbPage`、`/db/search/dbPage`、`/tb/search/tbPage`、
   `/noc/search/nocGBPage`、`dbba|hbba.sacinfo.org.cn/stdQueryList`）。
   这是整份报告里唯一"可直接适配"的一类渠道，其余绝大多数只能兜底抓取 HTML。
2. **国标的"废止/被代替"关系在 JSON 接口里拿不到**：`gbQueryPage` 只返回 `STATE`（现行/即将实施/废止），
   不含 `被代替` 字段；而地标/行标接口**有** `reviseStdCodes`。国标的替代关系要去
   `std.samr.gov.cn/gb/search/gbDetailed?id=<PROJECT_ID>` 详情页或 `openstd` 检索页解析 HTML。
3. **地方标准不该逐省适配**：`dbba.sacinfo.org.cn/stdQueryList` 一个 POST 端点即可按
   `industry=省名` + `status=现行|有更新版|废止` + `pubdate=近N月` 查询全国 31 省，
   本次实测 8 个省的 total 分别为 3929/2010/5689/2189/6359/2806/3954/3452，合计 117718 条。
   详见文末结论。

---

## 1. 国家标准（国标）

### 国家标准全文公开系统（openstd）
- 类别: 国标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://openstd.samr.gov.cn/bzgk/std/`（访问时间: 2026-09-18）
  - 注意：`https://openstd.samr.gov.cn/bzgk/gb/` 会 **302 跳转**到 `/bzgk/std/`，原 `/bzgk/gb/` 路径已迁移。
- 实测证据: HTTP 200，正文原文「`国家标准全文公开`」「`强制性国家标准 推荐性国家标准 指导性技术文件 国家标准外文版 (National standards in foreign language version)`」
- 内容形态: HTML 列表页（服务端渲染）+ 表单检索；**不是** JSON API
- 列表与分页:
  - 列表：`/bzgk/std/std_list_type?p.p1=1&p.p90=circulation_date&p.p91=desc`
    （`p.p1`：1=强制性、2=推荐性、3=指导性技术文件、6=外文版）
  - 检索：`/bzgk/std/std_list?p.p1=1&p.p90=circulation_date&p.p91=desc&p.p2=<关键词>`
    - 实测 `p.p2=30871` → 正文原文「`标准检索结果 ... 全部 2 强制性国家标准 2 ... 标准状态： 现行(1) 废止(1)`」
  - 分页：`p.p90` 为排序字段、`p.p91` 为 `desc`；实际翻页参数未逐页验证（未确认）
- 更新节奏 / 时效性: 与「国家标准公告」联动，每批公告后逐批公开全文；通知页 `/bzgk/std/notice` 实测原文
  「`关于公开2026年第34号中国国家标准公告中国家标准全文的通知 2026-08-25`」
- 反爬: 未遇到验证码；但 PowerShell `Invoke-WebRequest` 直连 `/bzgk/gb/` 报
  `Operation is not valid due to the current state of the object`（TLS/HTTP2 协商问题），
  **`curl.exe` 正常**，说明存在对非浏览器 TLS 指纹的差异化处理，用 curl 即可绕过
- 能回答: 发布? ✅（通知页） 修订? ⚠️（需详情页） 废止? ✅（筛选"废止"） 现行性? ✅（按标准号检索） 编号核验? ✅
- 结论: **只能兜底抓取**（HTML 解析，需要处理 302 与 TLS 指纹）

### 全国标准信息公共服务平台（std.samr.gov.cn）
- 类别: 国标 / 行标 / 地标 / 团标（统一入口）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://std.samr.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`国家标准目录查询- 全国标准信息公共服务平台 ... 国家标准 行业标准 地方标准 团体标准 企业标准 国际标准 国外标准`」
- 内容形态: **JSON API**（bootstrap-table 服务端分页）
- 列表与分页（★ 本次调研最有价值的产出）:

| 类别 | 端点 | 实测结果 |
|---|---|---|
| 国标 | `GET /gb/search/gbQueryPage` | `{"total":79311,...}` |
| 行标 | `GET /hb/search/hbPage` | `{"total":118946,...}` |
| 地标 | `GET /db/search/dbPage` | 返回 `{"total":0,...}`（见下方注意） |
| 团标 | `GET /tb/search/tbPage` | `{"total":7906,...}` |
| 国标公告 | `GET /noc/search/nocGBPage` | `{"total":542,...}` |

  参数（从各页内联 JS 的 `queryParams` / `resetTable()` 抄出，非猜测）：
  - `gbQueryPage`：`searchText`、`ics`（ICS 分类号，URL-fragment 形式如 `77_冶金/77.080_黑色金属`）、
    `state`、`ISSUE_DATE`、`pageSize`、`pageNumber`
    - ⚠️ **`state` 参数实测不生效**：传入 `state=现行 / 即将实施 / 废止`（含 URL 编码形式）服务端一律返回
      「`系统提示 ... 无法找到该页面`」。可行做法是拉全量按响应里的 `STATE` 字段在客户端过滤。
  - `hbPage` / `dbPage`：`searchText`、`op`（行业/地区）、`ISSUE_DATE`、`pageSize`、`pageNumber`
  - `tbPage`：`searchText`、`ICS`、`state`、`ISSUE_DATE`、`tbType`
  - 分页实测：`?pageSize=2&pageNumber=3` → 返回 `"pageNumber":3` 且是第 5、6 条记录，分页有效。
    `limit=/offset=` 被忽略（仍返回第 1 页 4 条）。
  - `dbPage` 注意：实测 `searchText=` 空、`searchText=a`、`searchText=` + `op=` 均返回 `total:0`；
    **地标请改用 `dbba.sacinfo.org.cn`**（同一平台的地方标准子站，见下）。
- 更新节奏 / 时效性:
  - 国标行标响应带 `SYS_INPUTIME`，实测抓到 `"SYS_INPUTIME":"2026-09-16 10:55:14"`（行标 YB/T 6557-2026），
    即**数据入库到 2 天前**，可当天发现新发布。
  - 国标 `ISSUE_DATE` 实测最新为 `2026-08-28`。
- 反爬: 未遇到验证码或 WAF；接口无鉴权要求。**实测到**首页存在 `用户/sacLoginByUUID.do` 等登录入口，
  但上表 5 个查询端点均**无需登录**即可返回数据
- 能回答: 发布? ✅（`ISSUE_DATE` + `nocGBPage` 公告） 修订? ⚠️（行标接口有 `HISTORY_VERSION`/`reviseStdCodes`） 废止? ✅（`STATE=废止` 客户端过滤） 现行性? ✅ 编号核验? ✅
- 结论: **可直接适配**

### 国家标准批准发布公告（"新发布"最一手来源）
- 类别: 国标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://std.samr.gov.cn/noc/nocGB`（访问时间: 2026-09-18）
- 实测证据: JSON 端点 `https://std.samr.gov.cn/noc/search/nocGBPage?pageSize=3&pageNumber=1&searchText=` 返回
  `{"CODE":"2026年第39号","NOTICE_DATE":"2026-08-31","TITLE":"关于批准发布《专用校车安全技术条件》等100项国家标准外文版的公告"}`、
  `{"CODE":" 2026年第38号","NOTICE_DATE":"2026-08-28","TITLE":"关于批准发布《钢铁及合金 镍含量的测定 分光光度法和重量法》等271项推荐性国家标准的公告"}`
- 内容形态: **JSON API**
- 列表与分页: `GET /noc/search/nocGBPage?searchText=<kw>&pageSize=<n>&pageNumber=<n>`；`total=542`
- 更新节奏 / 时效性: 公告号连载（2026 年第 39 号 / 08-31），**当天可发现**；实测最新一条距今 18 天（09-18 访问）
- 反爬: 无
- 能回答: 发布? ✅✅（一手公告） 修订? ✅（公告标题含"修订"字样可判） 废止? ⚠️（废止公告另见 `/noc/` 其他子栏） 现行性? ❌ 编号核验? ⚠️（公告标题里有标准名，正文 PDF 才有号）
- 结论: **可直接适配**（做"新发布"发现的首选）

### 中国标准在线服务网（spc.org.cn）
- 类别: 国标（商业增值，非官方一手，但接口可用）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.spc.org.cn/standardonline/replace?type=0`（访问时间: 2026-09-18）
- 实测证据: HTTP 200 / 36518 bytes，正文原文「`被代替国家标准、已废止国家标准_标准下载、标准查询、标准阅读_中国标准在线服务网`」
- 内容形态: HTML（需登录才看完整列表，未登录只到导航层）
- 列表与分页: 导航里实抄到的路径：
  - 作废代替查询 `/standardonline/replace?type=0`
  - 标准引用查询 `/standardonline/replace?type=3`
  - 标准进度查询 `/stdlib/stdschedule`
  - 国家标准计划查询 `/revision/query`
  - 标准术语查询 `/myknowledge/termsearchnew`
  - 分页参数：未确认
- 更新节奏 / 时效性: 未确认
- 反爬: 未看到验证码；页面有 `登录/注册` 墙，未登录拿不到明细
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ✅（栏目名） 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（登录后才有数据，不适合做巡检主链）

### 国家标准化管理委员会（sac.gov.cn）
- 类别: 国标（政策/动态，非目录）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.sac.gov.cn/bzhdt/index.html`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`标准化动态 标准化动态`」；首页正文原文「`国家标准化管理委员会 ... 市场监管总局中央社会工作部民政部关于发布《行业协会商会收费行为合规指南》的公告`」
- 内容形态: HTML 列表页
- 列表与分页: 无独立 API；只有栏目页。`https://www.sac.gov.cn/zw/zfxxgk/fdzdgknr/` 实测 **404**（`页面不存在！3 秒后将返回首页。`）
- 更新节奏 / 时效性: 实测首页新闻日期 09-17 ~ 09-15，日更
- 反爬: 无
- 能回答: 发布? ⚠️（只有新闻，无标准目录） 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**（对"标准巡检"无结构化价值，只能当舆情源）

---

## 2. 行业标准（行标）

### 行业标准信息公共服务平台（hbba.sacinfo.org.cn）
- 类别: 行标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://hbba.sacinfo.org.cn/stdList`（访问时间: 2026-09-18）
- 实测证据: POST `https://hbba.sacinfo.org.cn/stdQueryList` 返回 `{"total":118946,"records":[{"code":"DL/T 5916—2026","chName":"电力建设工程新技术应用评价规范","chargeDept":"国家能源局","status":"现行","recordDate":1789488000000}]}`
- 内容形态: **JSON API**（POST，`application/x-www-form-urlencoded`）
- 列表与分页:
  - `POST /stdQueryList`，body：`current=<页码>&size=<每页>&key=<关键词>&ministry=<部委>&industry=<行业>&pubdate=<近N月>&date=&status=<现行|有更新版|废止>`
  - 子表：`POST /rtnQueryList`（月报）、`POST /snQueryList`（标准公告，参数 `snType`）
  - 实测：`current=1&size=3` → `{"current":1,"pages":39649,"size":3,"total":118946}`
  - 按部委分布（页面实抄）：工信部 43,385、公安部 2,934、生态环境部 1,350、住建部 1,119、交通运输部 1,365
- 更新节奏 / 时效性: `recordDate` 实测 `1789488000000` = 2026-09-16，即**备案后 2 天内可见**
- 反爬: 无验证码；`stdList` 的 HTML 页面带 `WEB 应用防火墙` 的**只是团标站**，此站实测直接可用
- 能回答: 发布? ✅ 修订? ✅（`reviseStdCodes` 字段，实测 `DB37/T 1850—2026` ← `DB37/T 1850-2011`） 废止? ✅（`status=废止` 实测返回 `fzDate` 废止日期） 现行性? ✅ 编号核验? ✅
- 结论: **可直接适配**（行标的最优解）

### 工信部标准信息服务平台（std.miit.gov.cn）
- 类别: 行标（工信部口径）
- 核实等级: ✅ 已实测访问（可打开，但**接口全需登录**）
- 实测链接: `https://std.miit.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: 首页 HTTP 200 / 2740 bytes，正文原文「`工业和信息化标准信息服务平台 We're sorry but vue3gch doesn't work properly without JavaScript enabled.`」；
  对 4 个候选 API 实测均被拒：
  `{"code":10005,"defExec":false,"isError":true,"isSuccess":false,"msg":"登录过期或失效，请重新登录"}`（`/kjsStandproject/front/project/projectInfo/queryProjectInfoByPageGuest`）
  `{"code":1,"msg":"Request method 'GET' not supported"}`（`/kjsStandproject/front/project/projectInfo/queryProjectInfoPublicity`）
- 内容形态: Vue3 SPA（需 JS 渲染）+ 后端 API **需登录态**
- 列表与分页: 从 `js/app-c3373795.01783cc6.js`（388KB）实抄到的命名空间：
  `/kjsStandproject/front/project/projectInfo/queryProjectInfoByPageGuest`、
  `/kjsStandproject/front/project/projectRevision/standardList`、
  `/kjsStandproject/front/project/projectInfo/queryStandardInfo`、
  `/kjsStandproject/front/project/projectInfo/queryProjectInfoPublicity`（POST）
- 更新节奏 / 时效性: 未确认（拿不到数据）
- 反爬: **实测到登录墙** —— 所有查询端点返回 `code:10005 登录过期或失效`。无验证码，但需要有效会话
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️（全部依赖登录）
- 结论: **不可程序化**（需登录态；如需工信部行标，改用 hbba.sacinfo.org.cn 的 `ministry=工业和信息化部`）

### 标准网（bzw.com.cn，中机生产力促进中心）
- 类别: 行标（工信部装备口）
- 核实等级: ✅ 已实测访问（**HTTP 可达，HTTPS 不可达**）
- 实测链接: `http://www.bzw.com.cn/`（访问时间: 2026-09-18）
  - ⚠️ `https://www.bzw.com.cn/` 与 `https://bzw.com.cn/` **实测 SSL 握手失败**，只能用 http
- 实测证据: HTTP 200，正文原文「`标准网 www.bzw.com.cn ... 首页 新闻资讯 标准公告 标准公示 征求意见 标准信息查询 政策文件 常用下载`」「`中华人民共和国工业和信息化部公告（2025年第41号）`」
- 内容形态: HTML 列表页（**列表内容由 JS 异步填充**）
- 列表与分页:
  - 标准公告 `/page/list1`（实测正文原文「`工业和信息化行业标准公告 国家标准公告 行业标准备案月报 当前第0页，每页0条 ，共0条`」—— 说明列表是 JS 填的，curl 拿不到条目）
  - 标准公示 `/page/list2`
  - 标准信息查询 `/page/bzSearch` —— 正文原文「`标准编号 验证码 查询 标准作废代替查询 标准编号 验证码 查询`」
  - 详情页 `/page/articledetail/<id>`、`/page/standardpublicitydetail/<id>`、`/page/standardplandetail/<id>`
  - 分页参数：未确认（需浏览器执行 JS）
- 更新节奏 / 时效性: 未确认
- 反爬: **实测到验证码** —— `/page/bzSearch` 的"现行标准查询"与"标准作废代替查询"两个表单都带 `验证码` 字段
- 能回答: 发布? ✅（公告页有，需 JS） 修订? ⚠️ 废止? ⚠️（"作废代替查询"有，但需验证码） 现行性? ⚠️ 编号核验? ⚠️
- 结论: **不可程序化**（列表 JS 渲染 + 查询表单强制验证码）

### 生态环境部 标准（mee.gov.cn / kjs.mee.gov.cn）
- 类别: 行标（HJ 系列）
- 核实等级: ✅ 已实测访问（**`kjs.mee.gov.cn` 打不开，正确域名是 `www.mee.gov.cn/ywgz/fgbz/bz/`**）
- 实测链接: `https://www.mee.gov.cn/ywgz/fgbz/bz/`（访问时间: 2026-09-18）
  - ❌ `https://kjs.mee.gov.cn/hjbhbz/` 实测 `The SSL connection could not be established`（证书/域名问题），**已迁移**
- 实测证据: HTTP 200，正文原文「`生态环境标准 ... 标准发布 标准解读 标准文本 标准修改与解释 标准征求意见 地方标准备案 标准管理 标准查询`」
- 内容形态: HTML 列表页（服务端渲染）
- 列表与分页（全部实测 200）:
  - 栏目根 `/ywgz/fgbz/bz/`
  - 标准发布 `/ywgz/fgbz/bz/bzfb/` —— 原文「`关于发布《环境空气和废气挥发性有机物便携式气相色谱仪技术要求》等10项国家生态环境标准的公告 2026-08-12`」
  - 标准文本 `/ywgz/fgbz/bz/bzwb/` —— 原文「`纺织工业水污染物排放标准GB4287—2026代替GB4287—2012、GB28936—2012等`」
  - 标准解读 `/ywgz/fgbz/bz/bzjd/`、征求意见 `/ywgz/fgbz/bz/bzzqyj/`、地方标准备案 `/ywgz/fgbz/bz/dfhjbhbzba/`
  - 分页参数：未确认（页面用静态路径 `t20260917_1166669.shtml`）
- 更新节奏 / 时效性: **实测到 2026-09-17 的条目**（`汽车大气污染物和温室气体排放测算方法（交通量法）HJ180—2026代替HJ/T180—2005`），可当天发现
- 反爬: 无
- 能回答: 发布? ✅ 修订? ✅（标题里显式写"代替 GB...") 废止? ⚠️ 现行性? ⚠️ 编号核验? ✅（标题含标准号）
- 结论: **只能兜底抓取**（HTML 解析；但"代替"关系写在标题里，正则很稳）

### 应急管理部 标准（mem.gov.cn）
- 类别: 行标（AQ 系列）
- 核实等级: ✅ 已实测访问（可达但**内容为 JS 注入**）
- 实测链接: `https://www.mem.gov.cn/fw/flfgbz/bz/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，但响应体仅 465 bytes，正文原文只有「`标准--中华人民共和国应急管理部`」（标题）
- 内容形态: HTML，**列表由 JS 异步加载**
- 列表与分页: 未找到 JSON 端点（`/fw/flfgbz/bz/index_1.shtml` 返回 59022 bytes 但为样式表包裹的空壳）
- 更新节奏 / 时效性: 未确认
- 反爬: 未遇到验证码
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（需浏览器渲染；AQ 标准的现行性建议改走 hbba.sacinfo.org.cn 的 `ministry=应急管理部`）

### 住房和城乡建设部 标准公告（工程建设标准）
- 类别: 行标（工程建设口，含国标局部修订）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`标准公告 首页 > 公开 > 法定主动公开内容 > 标准公告 标准公告`」；
  首页实测抓到原文「`住房城乡建设部关于发布行业标准《住房公积金基础数据标准》的公告`」「`住房城乡建设部关于发布国家标准《医院洁净手术部建筑技术规范》局部修订条文的公告`」
- 内容形态: HTML 列表页（**列表项由 juba/JS 插件注入**）
  - 单页响应体是 gzip 且列表项需 JS；`index_1.html` 分页实测返回 548 bytes 空壳
- 列表与分页: 栏目 `/gongkai/fdzdgknr/bzgg/index.html`；
  条目形态 `/gongkai/zc/wjk/art/2026/art_<hash>.html`；**分页参数：未确认**
- 更新节奏 / 时效性: 实测公告含 2026 年条目，且有"局部修订条文"这类**修订**专用公告形态
- 反爬: 无验证码；`www.mohurd.gov.cn` 需 `curl --compressed`（响应为 gzip）
- 能回答: 发布? ✅ 修订? ✅（"局部修订条文的公告"是独立的公告类型） 废止? ✅（实测抓到「`住房城乡建设部关于废止部分文件的公告`」） 现行性? ⚠️ 编号核验? ✅（标题含标准名）
- 结论: **只能兜底抓取**（列表 JS 渲染；但公告标题结构极规整，HTML 正则可用）

### 工程建设标准化信息网（ccsn.org.cn）
- 类别: 行标（住建口镜像/汇总）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.ccsn.org.cn/News/More.aspx?ClassID=004001`（访问时间: 2026-09-18）
- 实测证据: HTTP 200 / 43648 bytes，**GB2312 编码**，正文原文「`标准发布公告`」「`标准征求意见`」「`标准年度计划`」「`住房城乡建设部关于发布国家标准《电化学储能电站设计标准》的公告`」「`我国全面清理地方标准已废止7400余项`」
- 内容形态: HTML（ASP.NET，**GB2312**，需按 936 代码页解码，否则全乱码）
- 列表与分页:
  - 标准发布公告 `/News/More.aspx?ClassID=004001`
  - 标准征求意见 `/News/More.aspx?ClassID=022`
  - 标准年度计划 `/News/More.aspx?ClassID=018`
  - 详情 `/News/ShowInfo.aspx?Guid=<uuid>`
- 更新节奏 / 时效性: 实测抓到 2026-09-15 的新闻，日更
- 反爬: 无；**唯一实测到的坑是 GB2312 编码**
- 能回答: 发布? ✅ 修订? ✅ 废止? ✅（实测到"已废止 7400 余项"条目） 现行性? ❌ 编号核验? ⚠️
- 结论: **只能兜底抓取**（编码需特殊处理；作为住建部公告的**可解析镜像**比主站更好用）

### 交通运输标准化信息系统（jtst.mot.gov.cn）
- 类别: 行标（JT 系列）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://jtst.mot.gov.cn/search/std?q=`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`标准检索 - 交通运输标准化信息系统`」；首页原文「`标准公开`→`https://jtst.mot.gov.cn/search/std?q=`」
- 内容形态: HTML 页 + 服务端检索路由（`/search/std?q=`、`/search/news?cate=&cateSelect=&menuSelect=`）
- 列表与分页: `/search/std?q=<关键词>`；国际标准化 `/search/news?cate=3&cateSelect=12&menuSelect=4`；业务办理 `/zxd`（需登录）
- 更新节奏 / 时效性: 实测首页动态日期为 2026 年，具体频率未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ✅（"标准检索"页面存在） 编号核验? ✅
- 结论: **只能兜底抓取**（HTML；搜索结果需进一步验证是否服务端渲染）

### 国家能源局（nea.gov.cn）
- 类别: 行标（NB/DL 系列）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.nea.gov.cn/policy/gg.htm`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`国家能源局—公告 您当前所在的位置: 首页 > 公告`」；
  首页实测原文「`国家能源局公告2026年第3号`」「`国家能源局综合司关于公开征求《GB26164.1-2010电力安全工作规程热力和机械部分（征求意见稿）》等2项国家强制性标准意见的通知`」
- 内容形态: HTML 列表页
- 列表与分页:
  - 公告 `/policy/gg.htm`
  - 新闻发布 `/xwfb/index.htm`、网上公示 `/hudong/gongshi/index.htm`
  - 能源行业标准化：`https://114.251.111.103:18080/portal` —— ❌ **实测 SSL 握手失败**（自签证书/IP 直连），只能浏览器访问
  - `/policy/index.htm` 实测 **404**（nginx），栏目已调整
- 更新节奏 / 时效性: 实测公告到 2026-09-14（`20260914/...`），可当天发现
- 反爬: 无
- 能回答: 发布? ✅ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ✅（公告标题含标准号）
- 结论: **只能兜底抓取**（公告页 HTML 好用；NB/DL 的现行性走 hbba.sacinfo.org.cn）

### 中国通信标准化协会（ccsa.org.cn）
- 类别: 团标/行标（通信口）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.ccsa.org.cn/standard`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`中国通信标准化协会 ... 公告通知 标准计划 无数据`」
- 内容形态: HTML + JS（页面残留 Vue 模板占位，`无数据` 表示列表由 JS 拉取）
- 列表与分页: 未找到公开 JSON 端点；导航有 `标准查询`、`公告通知`、`标准计划`、`工信部公示`
- 更新节奏 / 时效性: 未确认
- 反爬: 无验证码；有 `登录/注册` 入口
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（JS 渲染，需浏览器）

### 中国电子工业标准化技术协会（cesa.cn）
- 类别: 团标（电子信息口）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.cesa.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`中国电子工业标准化技术协会 We're sorry but 中国电子工业标准化技术协会 doesn't work properly without JavaScript enabled.`」（纯 SPA 壳）
- 内容形态: Vue SPA（需 JS）
- 列表与分页: 从 `static/js/app.13569769.js`（514KB）实抄到的 API 路径：
  `/cesa/commonStandard/findStandard`、`/cesa/cesaStandardInfo/findStandInfo`、
  `/cesa/interStandard/findInterStandard`、`/cesa/notice/selectList`、
  `/cesa/findAll/query`、`/cesa/findAll/findProjectList`、`/cesa/showApproval/findApprovalList`
  - 未逐个实测这些端点（未确认）
- 更新节奏 / 时效性: 未确认
- 反爬: 未遇到验证码
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（SPA；API 路径已知但未验证鉴权要求）

### 中国标准服务网 / 标准网等其他
- 类别: 行标
- 核实等级: ❌ 实测打不开
- 实测链接: `http://www.ccsainfo.com/`（访问时间: 2026-09-18）
- 实测证据: `The SSL connection could not be established`（https）/ 连接层失败（http）
- 反爬: —
- 结论: **不可程序化**（站点已失效，勿纳入渠道清单）

### 金融标准化技术委员会（cfstc.org）
- 类别: 行标（金融口）
- 核实等级: ❌ 实测打不开
- 实测链接: `http://www.cfstc.org/`（访问时间: 2026-09-18）
- 实测证据: HTTP `code=502`（`http://www.cfstc.org/`）；`https://www.cfstc.org/` 返回 `code=000`（连接失败）
- 内容形态: —
- 更新节奏 / 时效性: 不可用
- 反爬: —
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**（**新 URL 未找到**；金融口 JR/T 标准的现行性建议改走 hbba.sacinfo.org.cn 的 `ministry=中国人民银行`）

### 国家卫生健康委员会（nhc.gov.cn）
- 类别: 行标（WS/WST 系列）
- 核实等级: ✅ 已实测访问（但**被 WAF 拒绝**）
- 实测链接: `https://www.nhc.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **412**（`Precondition Failed`，响应体 0 字节）—— 对 `curl`/PowerShell 的非浏览器请求一律 412
- 内容形态: 需浏览器（JS + 可能的 JS 挑战）
- 列表与分页: 未取到；尝试的 `https://www.nhc.gov.cn/wjw/s9491/wsbzk.shtml`、`/wjw/wsbzxx/wsbz.shtml`、`/wjw/index.shtml` 全部 412
- 更新节奏 / 时效性: 未确认
- 反爬: **实测到 WAF 拦截（HTTP 412）**，对无浏览器 UA/JS 的客户端生效
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **不可程序化**（需浏览器/JS 挑战；WS 标准现行性可走 hbba.sacinfo.org.cn 的 `ministry=国家卫生健康委员会`）

### 国家食品安全风险评估中心（cfsa.net.cn）
- 类别: 行标（食品安全口辅助）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.cfsa.net.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`国家食品安全风险评估中心 ... 中心概况 机构简介 主要职能 机构设置 领导介绍 专家介绍`」
- 内容形态: HTML 门户
- 列表与分页: 未找到标准目录栏目；`https://sppt.cfsa.net.cn:8086/db`（企标备案）实测 **SSL 失败**
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**（对标准巡检无结构化价值）

### 中国标准化研究院（cnis.ac.cn）
- 类别: 行标/研究
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.cnis.ac.cn/wap/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`中国标准化研究院 ... 本院动态 标院新闻 科研动态 标准意见征求 协作机制动态 ... 中国标准服务网`」
- 内容形态: HTML 门户（首页 `/` 仅 860 bytes，为跳转壳）
- 列表与分页: 无标准目录
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**

---

## 3. 地方标准（地标）

### 地方标准信息公共服务平台（dbba.sacinfo.org.cn）★ 统一入口
- 类别: 地标（全国 31 省统一）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://dbba.sacinfo.org.cn/stdList`（访问时间: 2026-09-18）
- 实测证据:
  - 页面 HTTP 200，正文原文「`地方标准 标准查询 月报查询 标准公告查询 ... 省市区 全部 北京市 (2,195) 天津市 (727) 河北省 (3,421) ...`」
  - **API 实测**：`POST https://dbba.sacinfo.org.cn/stdQueryList`
    body `current=1&size=3&key=&ministry=&industry=&pubdate=&date=&status=` →
    `{"current":1,"pages":39240,"records":[{"code":"DB61/T 522-2020","chName":"地理标志产品  蒲城酥梨","industry":"陕西省","chargeDept":"陕西省市场监督管理局","status":"现行","issueDate":1582819200000,"actDate":1585324800000,"recordDate":1789660800000,"recordNo":"131298-2026","reviseStdCodes":"DB61/T 522-2011"}],"total":117718}`
  - 废止查询实测：`status=%E5%BA%9F%E6%AD%A2`（废止）→
    `{"code":"DB42/T 2554-2026","status":"废止","fzDate":1787068800000,"reviseStdCodes":null}`；
    另一条 `{"code":"DB37/T 1850—2026","status":"废止","reviseStdCodes":"DB37/T 1850-2011","fzDate":1786377600000}`
- 内容形态: **JSON API**（POST，`application/x-www-form-urlencoded`，响应 `Content-Type: text/json;charset=UTF-8`）
- 列表与分页:
  - 标准列表 `POST /stdQueryList`
    - `current`（页码）/ `size`（每页）
    - `key`（关键词，可填标准号）
    - `industry`（省/自治区/直辖市中文名，如 `上海市`）
    - `ministry`（发布机构名，如 `山东省市场监督管理局`；与 `industry` 互斥使用）
    - `pubdate`（`-1` 近一月 / `-3` 近三月 / `-6` 近半年 / `-12` 近一年 / `-24` 近两年 / `-36` 近三年）
    - `status`（`现行` / `有更新版` / `废止`）
    - `date`（未确认取值）
  - 标准公告 `POST /snQueryList`，参数 `current`、`size`、`key`、`snType`
    - 实测原文：`{"code":"2026年第35号","createRealname":"辽宁省市场监督管理局","recordCount":56,"releaseDate":1789488000000}`
  - 备案月报 `POST /rnQueryList`，参数 `current`、`size`、`key`
    - 实测原文：`{"title":"2026年第8号(总第313号)","content":"2026年8月国家标准委收到北京市、河北省、内蒙古自治区等12个省市区共发布标准382项。","stdCount":382}`
  - 详情页 `GET /stdDetail/<pk>`（`pk` 为 64 位 hex）
- 更新节奏 / 时效性: **实测 latest `recordDate` = 2026-09-18**（当天！）、前一条 2026-09-17，
  即地方标准备案后**最快当天可见**
- 反爬: 无验证码、无 WAF、无需登录。`/stdList` 页面的 HTML 里有 `WEB 应用防火墙` 字样的是**团标站**，本站实测无
- **31 省覆盖实测**（`industry=<省名>&status=` 的 `total`）：
  北京市 3929 / 上海市 2010 / 江苏省 5689 / 浙江省 2189 / 山东省 6359 / 广东省 2806 / 辽宁省 3954 / 四川省 3452；
  全量 `total` = 117718。页面左侧省市区清单同时列出北京(2,195)、天津(727)、河北(3,421)、石家庄(179)、唐山(202)、
  雄安新区等**省市两级**粒度
- 能回答: 发布? ✅（`issueDate` + `/snQueryList` 公告） 修订? ✅（`reviseStdCodes` 明确给出被代替标准号） 废止? ✅（`status=废止` + `fzDate`） 现行性? ✅ 编号核验? ✅
- 结论: **可直接适配** —— 这是 31 省地标的最优解

### 上海市市场监督管理局（scjgj.sh.gov.cn）
- 类别: 地标
- 核实等级: ⚠️ 未核实（站点可达，**未找到"地方标准批准发布/废止公告"栏目**）
- 实测链接: `http://scjgj.sh.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200 / 38403 bytes（**GB2312 编码**），首页 75 个 `<a>` 中**无任何"标准/公告"栏目链接**，
  唯一命中「`计量标准器具核准`」（政务服务事项，非标准公告）
- 尝试并失败的具体 URL（全部 404）：`/zhuanlan/`、`/col/col1000/index.html`、`/bzhcxfw/`、`/dfbz/`、`/bzcx/`、`/sitemap.html`（548 bytes 空壳）
- 内容形态: 首页 GB2312 HTML；栏目结构未摸清
- 列表与分页: 未找到
- 更新节奏 / 时效性: 未确认
- 反爬: 未遇到验证码
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️（建议走 dbba） 编号核验? ⚠️
- 结论: **只能兜底抓取**（且必须先人工定位栏目；短期建议直接用 dbba 统一平台，`industry=上海市` 实测返回 2010 条）

### 北京市市场监督管理局（scjgj.beijing.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问（找到了**在线查询服务入口**，但后端已失效）
- 实测链接: `https://scjgj.beijing.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200 / 259761 bytes，正文原文
  「`北京市地方标准信息查询` => `https://scjgj.beijing.gov.cn/cxfw/?serviceName=bzh_api_standard`」
- 内容形态: 查询服务是**外链的旧 Struts 应用**
- 列表与分页:
  - 入口 `https://scjgj.beijing.gov.cn/cxfw/?serviceName=bzh_api_standard`（HTTP 200，页面内嵌
    `http://innerapp.capital-std.com/outerApp/standardSearchAction.do`）
  - 后端 `http://innerapp.capital-std.com/outerApp/standardSearchAction.do` —— ❌ **实测 HTTP 502**
  - 另 4 条"标准/公告"栏目 URL 全部实测 **404**：`/zwgk/tzgg/`、`/zwgk/bzhgz/`、`/zwgk/zcwj/index.html`、`/col/col31/index.html`
- 更新节奏 / 时效性: 不可用（后端 502）
- 反爬: 未遇到验证码
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌（**后端已下线**）
- 结论: **不可程序化**（旧接口 502；北京地标改用 dbba，`industry=北京市` 实测 3929 条）

### 江苏省市场监督管理局（scjgj.jiangsu.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问
- 实测链接: `http://scjgj.jiangsu.gov.cn/col/col78963/index.html`（通知公告，访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`江苏省市场监督管理局 通知公告 ... 综合通知 质量抽查 食品抽检 政策文件 政策解读 法律法规 网站工作年度报表`」
- 内容形态: HTML 列表页（CMS `/col/col<id>/index.html` + `/art/<年>/<月>/<日>/art_<col>_<id>.html`）
- 列表与分页: 栏目 `/col/col78963/index.html`；实测抓到的相关条目
  「`拟成立江苏省脑机接口标准化技术...` => `/art/2026/9/14/art_78968_11829311.html`」、
  「`江苏省专业标准化技术委员会管理办法` => `/art/2025/12/23/art_78964_11697595.html`」
  - **无独立的"地方标准批准发布公告"栏目**（标准信息混在通知公告里），分页参数未确认
- 更新节奏 / 时效性: 实测到 2026-09-14 条目
- 反爬: 无
- 能回答: 发布? ⚠️（需关键词过滤） 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（无专用栏目；地标现行性建议用 dbba `industry=江苏省`，实测 5689 条）

### 浙江省市场监督管理局（zjamr.zj.gov.cn）+ 浙江标准在线
- 类别: 地标
- 核实等级: ✅ 已实测访问（**本批里面做得最规范的省份**）
- 实测链接: `http://zjamr.zj.gov.cn/col/col1228969897/index.html`（公告公示，访问时间: 2026-09-18）
- 实测证据:
  - 公告公示页 HTTP 200，正文原文「`公告公示 重要公告 食品安全抽检 产品质量安全监督抽查信息 地方标准信息 其他业务公告公示 网络食品交易第三方平台提供者备案信息公示 特种设备许可受理及发证`」
  - 子栏目实抄：`重要公告 => /col/col1229003052/index.html`；
    `地方标准信息 => https://zlzx.zjamr.zj.gov.cn/bzzx/`
- 内容形态: HTML 列表 + 独立标准门户（HTML 服务端渲染）
- 列表与分页:
  - 省局公告 `/col/col1228969897/index.html`
  - **浙江标准在线**（实测 HTTP 200）：
    - 地方标准 `/bzzx/public/news/list/lstd/ALL/1.html` —— 原文「`标准计划 征求意见 标准公示 标准公告 标准发布 浙江省市场监督管理局关于下达2026年第一批浙江省地方标准制修订计划的通知 2026-02-11`」
    - 标准查询 `/bzzx/public/std/list/ALL/1.html` —— 原文「`国际标准 国外标准 国家标准 行业标准 地方标准 团体标准 企业标准 ... 查询到相关标准10条 ... GB/T 47982-2026 实施日期：2026-11-01`」
    - 企业标准 `/bzzx/public/std/companyStdList/1.html`、团体标准 `/bzzx/public/std/organization/1.html`
    - 分页形态：`.../ALL/<页码>.html`（路径分页，非查询参数）
- 更新节奏 / 时效性: 实测列表含 2026 年条目；具体频率未确认
- 反爬: 无
- 能回答: 发布? ✅ 修订? ✅（有"标准计划/标准公示/标准公告"全流程） 废止? ⚠️ 现行性? ✅ 编号核验? ✅
- 结论: **只能兜底抓取**（HTML 路径分页，但结构最规整、可解析性最好；仍然是逐省适配，不划算）

### 山东省市场监督管理局（amr.shandong.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问
- 实测链接: `http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002`（通知公告，访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`山东省市场监督管理局 通知公告 当前位置： 首页 > 政务公开 > 通知公告 通知公告`」；
  首页实测抓到**明确的废止公告原文**：
  「`山东省市场监督管理局关于废止《可燃液体、液化烃及液化毒性气体汽车装卸设施安全管理规范》山东省地方标准的公告` => `/art/2026/8/31/art_76510_10317243.html`」
- 内容形态: HTML 列表页（**返回头 charset 实测为 `ISO-88509-1`，非法编码名，实际是 GB2312/GBK —— 必须按 936 解码**）
- 列表与分页: 栏目 `/col/col76510/index.html?number=SD1002`；
  条目 `/art/<年>/<月>/<日>/art_76510_<id>.html`；分页参数未确认
- 更新节奏 / 时效性: 实测到 2026-09-17 条目（`/art/2026/9/17/art_76510_10317301.html`），**日更，可当天发现**
- 反爬: 无验证码；**编码问题**是唯一实测坑
- 能回答: 发布? ✅ 修订? ⚠️ 废止? ✅（有专门废止公告） 现行性? ⚠️ 编号核验? ✅
- 结论: **只能兜底抓取**（编码需 hack；废止公告是可用信号）

### 广东省市场监督管理局（amr.gd.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://amr.gd.gov.cn/zwgk/tzgg/index.html`（通知公告，访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`通知公告-广东省市场监督管理局网站 ... 政务公开 组织机构 通知公告 政策文件 政策解读 重点领域信息公开 数据发布 双公示`」
- 内容形态: HTML 列表页
- 列表与分页:
  - 通知公告 `/zwgk/tzgg/index.html`
  - 规范性文件 `/zwgk/zcfg/gfxwj/index.html`（HTTP 200）
  - 双公示 `/zwgk/sgs/index.html`
  - 条目形态 `/zwgk/tzgg/content/post_<id>.html`
- 更新节奏 / 时效性: 实测到 2026-09 条目；`省标准化研究院 => https://www.gdis.org.cn`（HTTP 200）
- 反爬: 无
- 能回答: 发布? ⚠️（需关键词过滤） 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（无专用标准公告栏目；用 dbba `industry=广东省`，实测 2806 条）

### 辽宁省市场监督管理局（scjg.ln.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml`（标准栏目，访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`辽宁省市场监督管理局 辽宁省人民政府 报送系统 无障碍浏览 ... 标准 ... 法律法规 政务公开重点工作 办事指南`」
- 内容形态: HTML 列表页（`.shtml` 静态化）
- 列表与分页:
  - 标准（服务-我要办）`/scjdglj/fw/wyb/bz/index.shtml`
  - 标准（服务-我要查）`/scjdglj/fw/wyc/bz/index.shtml`（HTTP 200）
  - 公示公告 `/scjdglj/fw/wyk/gsgg/index.shtml`
  - dbba 实测：`辽宁省市场监督管理局` 的标准公告 `{"code":"2026年第35号","recordCount":56}`
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（有专门"标准"栏目但内容需进一步解析；dbba `industry=辽宁省` 实测 3954 条）

### 四川省市场监督管理局（scjgj.sc.gov.cn）
- 类别: 地标
- 核实等级: ✅ 已实测访问
- 实测链接: `http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml`（公示公告，访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`公示公告 - 四川省市场监督管理局 ... 政策文件 政策解读 公示公告 人事信息 建议提案 政府采购 部门预决算`」；
  首页实测抓到「`省级地方标准草案征求意见` => `/scsjgj/zfbzzqyj/list.shtml`」
- 内容形态: HTML 列表页（`.shtml`）
- 列表与分页:
  - 公示公告 `/scsjgj/c104492/list.shtml`
  - 省级地方标准草案征求意见 `/scsjgj/zfbzzqyj/list.shtml`
  - 省标准化院 `https://www.scis.net.cn`（HTTP 200，四川省质量和标准化研究院）
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ⚠️（有草案征求意见栏目） 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️
- 结论: **只能兜底抓取**（dbba `industry=四川省` 实测 3452 条）

---

## 4. 团体标准（团标）

### 全国标准信息公共服务平台 · 团体标准（std.samr.gov.cn/tb/search/tbPage）★ 推荐
- 类别: 团标
- 核实等级: ✅ 已实测访问
- 实测链接: `https://std.samr.gov.cn/tb/search/tbPage?searchText=`（访问时间: 2026-09-18）
- 实测证据: `{"total":7906,"rows":[{"C_STD_CODE":"T/DZYX 005—2018","C_C_NAME":"贵金属与珠宝玉石饰品 标识","C_GROUP_NAME":"大连市珠宝玉石协会","ISSUE_DATE":"2019-04-08","HREF":"http://www.ttbz.org.cn/StandardManage/Detail/27795/","STD_DOMAIN":"团体标准"}]}`
- 内容形态: **JSON API**
- 列表与分页: `GET /tb/search/tbPage?searchText=&ICS=&state=&ISSUE_DATE=&tbType=&pageSize=&pageNumber=`
  - **`HREF` 字段直接给出团标原文详情页链接**（指向 ttbz.org.cn），这是绕过 ttbz WAF 的关键
- 更新节奏 / 时效性: 未确认（数据看起来是历史增量；`total=7906` 明显小于 ttbz 实际收录量）
- 反爬: 无
- 能回答: 发布? ✅（`ISSUE_DATE`） 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ✅
- 结论: **可直接适配（但有覆盖度疑点）** —— 只有 7906 条，远小于团标平台的实际规模，**不能当唯一来源**

### 全国团体标准信息平台（ttbz.org.cn / www.ttbz.org.cn）
- 类别: 团标
- 核实等级: ✅ 已实测访问（**可达，但关键列表页被 WAF 拦截**）
- 实测链接: `https://www.ttbz.org.cn/standard.html`（访问时间: 2026-09-18）
- 实测证据:
  - 首页 `https://www.ttbz.org.cn/`：HTTP 200 / 238889 bytes，正文原文
    「`全国团体标准信息平台 - 首页 ... 政策文件 团体新闻 综合新闻 ... 国家标准委关于开展团体标准规范发展优质发展试点工作的通知`」
  - `https://www.ttbz.org.cn/standard.html`：HTTP 200/419ms，正文原文
    「`全国团体标准信息平台 - 团体标准 {{$t('common.home')}} > {{$t('nav.standard')}} ...`」（Vue 模板未渲染）
  - ❌ `https://www.ttbz.org.cn/Home/Standard` 与 `http://www.ttbz.org.cn/Home/Standard`：
    正文原文「`WEB 应用防火墙 当前正在对访问请求进行人机识别检测，请稍等片刻，即将为您加载访问页面 . . . 确认 向右滑动填充拼图`」
    以及 `/Home/StandardList` 同样命中 WAF
  - ❌ `/Home/Index` 返回 `{"result":false,"msg":"资源不存在","code":404}`；
    `/api/standard/list`、`/portal/standard/list`、`/standard/list`、`/Home/GetStandardList` 均 404
- 内容形态: 新版为伪静态 HTML + Vue（`/standard.html`、`/standardDetail/<id>.html`、`/organizationDetail/<id>.html`）；
  旧版 `/Home/*` 路由命中 **WEB 应用防火墙（滑动拼图人机识别）**
- 列表与分页:
  - 新版入口 `/standard.html`（支持 hash 锚点 `#org_<base64(orgId)>`，见 `template/1/ttbz/js/url-utils.js` 实抄）
  - 详情 `/standardDetail/<id>.html`
  - PDF 预览统一入口 `/ms/pdf-preview`（需先写 `_pdf_preview` cookie，见 `url-utils.js`）
  - **检索 API：未确认**（未能从 `standard.html` / `url-utils.js` / `http.js` 中反解出 JSON 端点；
    `http.js` 里 `BASE_URL = ''`，说明是同源相对路径，被 WAF 挡住无法枚举）
- 更新节奏 / 时效性: 未确认
- 反爬: **实测到 WAF** —— `/Home/Standard`、`/Home/StandardList` 均返回
  「`WEB 应用防火墙 ... 人机识别检测 ... 向右滑动填充拼图`」；无头 curl 无法通过
- 能回答: 发布? ⚠️ 修订? ⚠️ 废止? ⚠️ 现行性? ⚠️ 编号核验? ⚠️（全部被 WAF 挡）
- 结论: **不可程序化**（需真实浏览器执行 JS + 通过滑块验证）。
  **规避建议：用 `std.samr.gov.cn/tb/search/tbPage` 拿元数据与 `HREF` 详情链接，不要硬刚 ttbz 的 WAF。**

### 企业标准信息公共服务平台（qybz.org.cn）
- 类别: 团标/企标（附带）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://www.qybz.org.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP 200 / 15641 bytes，正文原文「`企业标准信息公共服务平台 ... 受机房线路改造影响，企业标准信息公共服务平台计划于2022年10月15日至2022年10月24日期间对平台服务时间进行调整`」
- 内容形态: HTML 门户
- 列表与分页: 未找到公开 JSON
- 更新节奏 / 时效性: 页面上还挂着 2022 年的通知，**看起来长期未维护**
- 反爬: 无
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**（对标准巡检无价值）

---

## 5. 国际 / 国外标准

### ISO（iso.org）
- 类别: 国际
- 核实等级: ✅ 已实测访问（**被 Cloudflare 拦截**）
- 实测链接: `https://www.iso.org/standards.html`（访问时间: 2026-09-18）
- 实测证据: HTTP **403**，正文原文「`Just a moment... Enable JavaScript and cookies to continue`」
- 内容形态: 需 JS 渲染 + Cloudflare 挑战
- 列表与分页: 无公开无鉴权 API（未确认）
- 更新节奏 / 时效性: 未确认
- 反爬: **实测到 Cloudflare JS 挑战（HTTP 403 + "Just a moment..."）**
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ⚠️（需浏览器） 编号核验? ⚠️
- 结论: **不可程序化**（需带浏览器指纹的抓取方案）

### IEC（iec.ch）
- 类别: 国际
- 核实等级: ✅ 已实测访问（**无内容返回**）
- 实测链接: `https://www.iec.ch/`（访问时间: 2026-09-18）
- 实测证据: HTTP **202**（Accepted）、响应体 0 字节，正文原文：（空）
- 内容形态: 疑似 JS 挑战/边缘节点排队（202 + 空体）
- 列表与分页: 无
- 更新节奏 / 时效性: 未确认
- 反爬: **实测到 HTTP 202 + 空响应**（典型 bot 缓解），`https://www.iec.ch/dyn/www/f?p=103:6:0` 同样 202/空
- 能回答: 发布? ❌ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **不可程序化**

### 全国标准信息公共服务平台 · 国际标准（std.samr.gov.cn/gj/）★ 中国官方汇总
- 类别: 国际（中国官方汇总入口）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://std.samr.gov.cn/gj/news?op=ISO`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`国际标准动态- 全国标准信息公共服务平台 ... 国际标准分类号（ICS） 01.综合、术语学、标准化、文献 ...`」；
  `https://std.samr.gov.cn/gj/` 原文「`国际标准 ... ISO标准动态 女性参与规则制定 消费者会更加受益 市场以信任为基石`」
- 内容形态: HTML 页；`op=ISO` / `op=IEC` 两个入口
- 列表与分页: `/gj/news?op=ISO`、`/gj/news?op=IEC`；页面有"查询"按钮，**未找到 JSON 端点**（未确认）
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **只能兜底抓取**（**只是动态新闻，不是 ISO/IEC 现行状态目录**；不能替代 ISO/IEC 官方查询）

### 全国标准信息公共服务平台 · 国外标准（std.samr.gov.cn/gw/）
- 类别: 国际（国外）
- 核实等级: ✅ 已实测访问
- 实测链接: `https://std.samr.gov.cn/gw/news?channelId=87`（访问时间: 2026-09-18）
- 实测证据: HTTP 200，正文原文「`国外标准动态- 全国标准信息公共服务平台 ... 标准动态 美国 欧洲 德国 英国 澳大利亚/新西兰 韩国 国外标准动态 查询 已选国家`」
- 内容形态: HTML 列表页
- 列表与分页: `/gw/news?channelId=87`、`88`、`89`、`90`、`91`、`92`（分别对应美/欧/德/英/澳新/韩，**映射未逐个确认**）
- 更新节奏 / 时效性: 未确认
- 反爬: 无
- 能回答: 发布? ⚠️ 修订? ❌ 废止? ❌ 现行性? ❌ 编号核验? ❌
- 结论: **只能兜底抓取**（动态新闻性质，非现行状态目录）

---

## 6. 汇总表：类别 × 最一手渠道

| 类别 | 最一手渠道 | 端点形态 | 当天可发现 | 现行性/编号核验 | 验证等级 |
|---|---|---|---|---|---|
| **国标（新发布公告）** | `std.samr.gov.cn/noc/search/nocGBPage` | JSON | ✅ | ❌ / ⚠️ | ✅ |
| **国标（目录+状态）** | `std.samr.gov.cn/gb/search/gbQueryPage` | JSON | ✅（`SYS_INPUTIME` 2 天内） | ✅ / ✅ | ✅ |
| **国标（全文）** | `openstd.samr.gov.cn/bzgk/std/std_list` | HTML | ⚠️ | ✅ / ✅ | ✅ |
| **行标** | `hbba.sacinfo.org.cn/stdQueryList` | JSON (POST) | ✅（`recordDate` 2 天内） | ✅ / ✅ | ✅ |
| **地标** | `dbba.sacinfo.org.cn/stdQueryList` | JSON (POST) | ✅（**当天**） | ✅ / ✅ | ✅ |
| **团标** | `std.samr.gov.cn/tb/search/tbPage` | JSON | ⚠️ | ⚠️ / ✅ | ✅ |
| **团标（原始平台）** | `www.ttbz.org.cn` | HTML + WAF | ❌ | ❌ | ✅（被拦） |
| **国际 ISO/IEC** | 中国官方渠道**无**现行状态目录 | — | ❌ | ❌ | ✅ |
| **行标（住建工程建设）** | `ccsn.org.cn/News/More.aspx?ClassID=004001` | HTML (GB2312) | ⚠️ | ❌ / ⚠️ | ✅ |
| **行标（生态环境）** | `mee.gov.cn/ywgz/fgbz/bz/bzfb/` | HTML | ✅ | ⚠️ / ✅ | ✅ |
| **行标（工信部）** | 登录墙，**无公开入口** | — | ❌ | ❌ | ✅（被拒） |

**明确结论：**

- **国标 / 行标 / 地标 / 团标这四类都各有一个可程序化的统一入口**（上表前 6 行），
  其中行标与地标共用 `sacinfo.org.cn` 系列平台的同一套 `POST /stdQueryList` 接口，可以合并成一个适配器。
- **"国际标准"没有统一入口**：ISO 被 Cloudflare 拦（403）、IEC 返回 202 空体，
  而中国官方渠道（`std.samr.gov.cn/gj/`、`/gw/`）**只是动态新闻，不含 ISO/IEC 标准的现行状态目录**。
  因此 ISO/IEC 的现行性核验**必须走境外浏览器抓取**，国内渠道无法兜底。
- **"行标"里有一个例外子类没有统一入口**：住建部的**工程建设标准**（GB 50xxx / JGJ / CJJ 系列）
  既不在 `hbba.sacinfo.org.cn` 的部委口径里完整覆盖，住建部主站又是 JS 渲染 ——
  只能靠 `ccsn.org.cn` 的公告镜像兜底，且只有"发布/修订/废止"公告，**查不了任意标准的现行性**。

---

## 7. 机器可读附录

```json
[
  {
    "name": "全国标准信息公共服务平台-国家标准目录",
    "category": "国标",
    "url": "https://std.samr.gov.cn/gb/gbQuery",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://std.samr.gov.cn/gb/search/gbQueryPage",
    "params": "searchText, ics, state(实测无效), ISSUE_DATE, pageSize, pageNumber",
    "answers": ["发布", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "total=79311。state 参数实测不生效（传现行/废止均返回'无法找到该页面'），需拉全量按响应 STATE 字段客户端过滤。limit/offset 被忽略。SYS_INPUTIME 实测到 2026-09-16。"
  },
  {
    "name": "国家标准批准发布公告",
    "category": "国标",
    "url": "https://std.samr.gov.cn/noc/nocGB",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://std.samr.gov.cn/noc/search/nocGBPage",
    "params": "searchText, pageSize, pageNumber",
    "answers": ["发布", "修订"],
    "verification": "verified",
    "province": null,
    "note": "total=542。'新发布'最一手来源。实测最新 CODE=2026年第39号 NOTICE_DATE=2026-08-31 TITLE=关于批准发布《专用校车安全技术条件》等100项国家标准外文版的公告。"
  },
  {
    "name": "国家标准全文公开系统",
    "category": "国标",
    "url": "https://openstd.samr.gov.cn/bzgk/std/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://openstd.samr.gov.cn/bzgk/std/std_list?p.p1=<类别>&p.p90=circulation_date&p.p91=desc&p.p2=<关键词>",
    "params": "p.p1(1强制/2推荐/3指导性/6外文版), p.p2(关键词), p.p90(排序字段), p.p91(desc), p.p3(状态,未确认), 分页参数未确认",
    "answers": ["发布", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "/bzgk/gb/ 已 302 到 /bzgk/std/。实测 p.p2=30871 返回'全部 2 强制性国家标准 2 标准状态：现行(1) 废止(1)'。PowerShell Invoke-WebRequest 报 Operation is not valid，必须用 curl.exe。"
  },
  {
    "name": "中国标准在线服务网",
    "category": "国标",
    "url": "https://www.spc.org.cn/standardonline/replace?type=0",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.spc.org.cn/standardonline/replace?type=0 (作废代替) / /stdlib/stdschedule (进度) / /revision/query (计划)",
    "params": "type(0=作废代替, 3=引用查询); 分页参数未确认",
    "answers": ["修订", "废止"],
    "verification": "verified",
    "province": null,
    "note": "商业站，非官方一手。未登录只能拿到导航层，明细需登录。页面标题实测'被代替国家标准、已废止国家标准'。"
  },
  {
    "name": "国家标准化管理委员会",
    "category": "国标",
    "url": "https://www.sac.gov.cn/bzhdt/index.html",
    "fetch_kind": "html_list",
    "list_endpoint": "无（仅栏目页）",
    "params": "无",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "纯新闻动态，无标准目录。https://www.sac.gov.cn/zw/zfxxgk/fdzdgknr/ 实测 404。对标准巡检无结构化价值。"
  },
  {
    "name": "行业标准信息公共服务平台",
    "category": "行标",
    "url": "https://hbba.sacinfo.org.cn/stdList",
    "fetch_kind": "json_api",
    "list_endpoint": "POST https://hbba.sacinfo.org.cn/stdQueryList",
    "params": "current, size, key, ministry, industry, pubdate(-1/-3/-6/-12/-24/-36), date, status(现行/有更新版/废止)",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "total=118946。实测 recordDate=2026-09-16。行标最优解。子接口：POST /rnQueryList(月报)、POST /snQueryList(公告, 参数 snType)。内容形态 application/x-www-form-urlencoded，响应 text/json。"
  },
  {
    "name": "工信部标准信息服务平台",
    "category": "行标",
    "url": "https://std.miit.gov.cn/",
    "fetch_kind": "js_rendered",
    "list_endpoint": "POST /kjsStandproject/front/project/projectInfo/queryProjectInfoPublicity 等（全部需登录）",
    "params": "未确认（需登录态）",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "SPA + 登录墙。实测所有查询端点返回 {\"code\":10005,\"msg\":\"登录过期或失效，请重新登录\"}。规避：用 hbba.sacinfo.org.cn 的 ministry=工业和信息化部（实测 43385 条）。"
  },
  {
    "name": "标准网(中机生产力促进中心)",
    "category": "行标",
    "url": "http://www.bzw.com.cn/",
    "fetch_kind": "js_rendered",
    "list_endpoint": "GET /page/list1 (标准公告), /page/list2 (公示), /page/bzSearch (查询)",
    "params": "未确认（列表 JS 填充；查询表单强制验证码）",
    "answers": ["发布"],
    "verification": "verified",
    "province": null,
    "note": "只有 http 可用，https 实测 SSL 握手失败。列表页实测返回'当前第0页，每页0条'（JS 未执行）。/page/bzSearch 正文实测到'标准编号 验证码 查询 标准作废代替查询 标准编号 验证码 查询'。"
  },
  {
    "name": "生态环境部标准",
    "category": "行标",
    "url": "https://www.mee.gov.cn/ywgz/fgbz/bz/bzfb/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /ywgz/fgbz/bz/bzfb/ (发布) /bzwb/ (文本) /bzjd/ (解读) /bzzqyj/ (征求意见) /dfhjbhbzba/ (地标备案)",
    "params": "静态路径 t<yyyymmdd>_<id>.shtml；分页参数未确认",
    "answers": ["发布", "修订", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "kjs.mee.gov.cn/hjbhbz/ 已失效(SSL 握手失败)，正确域名是 www.mee.gov.cn/ywgz/fgbz/bz/。代替关系写在标题里，实测'纺织工业水污染物排放标准GB4287—2026代替GB4287—2012'，正则很稳。"
  },
  {
    "name": "应急管理部标准",
    "category": "行标",
    "url": "https://www.mem.gov.cn/fw/flfgbz/bz/",
    "fetch_kind": "js_rendered",
    "list_endpoint": "未找到（列表 JS 注入）",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "HTTP 200 但响应体仅 465 bytes，正文只有标题'标准--中华人民共和国应急管理部'。规避：用 hbba.sacinfo.org.cn 的 ministry=应急管理部。"
  },
  {
    "name": "住房和城乡建设部标准公告",
    "category": "行标",
    "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/bzgg/index.html",
    "fetch_kind": "js_rendered",
    "list_endpoint": "GET /gongkai/fdzdgknr/bzgg/index.html（列表项由 JS 注入）",
    "params": "分页参数未确认（index_1.html 实测为空壳 548 bytes）",
    "answers": ["发布", "修订", "废止", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "需 curl --compressed。实测抓到'住房城乡建设部关于发布国家标准《医院洁净手术部建筑技术规范》局部修订条文的公告'与'住房城乡建设部关于废止部分文件的公告'。"
  },
  {
    "name": "工程建设标准化信息网",
    "category": "行标",
    "url": "https://www.ccsn.org.cn/News/More.aspx?ClassID=004001",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /News/More.aspx?ClassID=004001 (标准发布公告) / 022 (征求意见) / 018 (年度计划)",
    "params": "ClassID；详情 /News/ShowInfo.aspx?Guid=<uuid>",
    "answers": ["发布", "修订", "废止"],
    "verification": "verified",
    "province": null,
    "note": "GB2312 编码，必须按 936 代码页解码。实测抓到'我国全面清理地方标准已废止7400余项'与多条住建部发布/局部修订公告。是住建部公告的可解析镜像。"
  },
  {
    "name": "交通运输标准化信息系统",
    "category": "行标",
    "url": "https://jtst.mot.gov.cn/search/std?q=",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /search/std?q=<关键词> ; /search/news?cate=<n>&cateSelect=<n>&menuSelect=<n>",
    "params": "q, cate, cateSelect, menuSelect",
    "answers": ["现行性", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "HTTP 200。业务办理 /zxd 需登录。搜索结果是否服务端渲染未确认。"
  },
  {
    "name": "国家能源局公告",
    "category": "行标",
    "url": "https://www.nea.gov.cn/policy/gg.htm",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /policy/gg.htm",
    "params": "静态路径 /<yyyymmdd>/<hash>/c.html",
    "answers": ["发布", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "实测到 2026-09-14 公告与'公开征求《GB26164.1-2010电力安全工作规程…》意见的通知'。/policy/index.htm 实测 404。能源行业标准化 https://114.251.111.103:18080/portal 实测 SSL 握手失败（IP 直连自签证书）。"
  },
  {
    "name": "中国通信标准化协会",
    "category": "团标",
    "url": "https://www.ccsa.org.cn/standard",
    "fetch_kind": "js_rendered",
    "list_endpoint": "未找到公开 JSON 端点",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "页面残留 Vue 模板'无数据'，列表 JS 拉取。导航含 标准查询/公告通知/标准计划/工信部公示。"
  },
  {
    "name": "中国电子工业标准化技术协会",
    "category": "团标",
    "url": "https://www.cesa.cn/",
    "fetch_kind": "js_rendered",
    "list_endpoint": "候选: /cesa/commonStandard/findStandard, /cesa/cesaStandardInfo/findStandInfo, /cesa/notice/selectList, /cesa/findAll/query",
    "params": "未确认（未逐个实测）",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "纯 Vue SPA 壳。API 路径从 static/js/app.13569769.js(514KB) 实抄，未验证鉴权要求。"
  },
  {
    "name": "全国团体标准信息平台",
    "category": "团标",
    "url": "https://www.ttbz.org.cn/standard.html",
    "fetch_kind": "js_rendered",
    "list_endpoint": "未确认（/Home/Standard 与 /Home/StandardList 均被 WAF 拦截）",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "实测 WAF：正文'WEB 应用防火墙 当前正在对访问请求进行人机识别检测…向右滑动填充拼图'。详情页 /standardDetail/<id>.html 可用。规避：用 std.samr.gov.cn/tb/search/tbPage 的 HREF 字段拿详情链接。"
  },
  {
    "name": "国家卫生健康委员会",
    "category": "行标",
    "url": "https://www.nhc.gov.cn/",
    "fetch_kind": "js_rendered",
    "list_endpoint": "未取到（全部 412）",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "实测 WAF：HTTP 412 Precondition Failed，响应体 0 字节。试过 /wjw/s9491/wsbzk.shtml、/wjw/wsbzxx/wsbz.shtml、/wjw/index.shtml 全部 412。规避：hbba.sacinfo.org.cn 的 ministry=国家卫生健康委员会。"
  },
  {
    "name": "金融标准化技术委员会",
    "category": "行标",
    "url": "http://www.cfstc.org/",
    "fetch_kind": "unknown",
    "list_endpoint": null,
    "params": null,
    "answers": [],
    "verification": "broken",
    "province": null,
    "note": "http 实测 code=502，https 实测 code=000（连接失败）。新 URL 未找到。金融口 JR/T 标准建议用 hbba.sacinfo.org.cn 的 ministry=中国人民银行。"
  },
  {
    "name": "中国标准服务网(ccsainfo)",
    "category": "行标",
    "url": "http://www.ccsainfo.com/",
    "fetch_kind": "unknown",
    "list_endpoint": null,
    "params": null,
    "answers": [],
    "verification": "broken",
    "province": null,
    "note": "https 实测 SSL 握手失败；http 连接层失败。站点已失效，勿纳入渠道清单。"
  },
  {
    "name": "地方标准信息公共服务平台",
    "category": "地标",
    "url": "https://dbba.sacinfo.org.cn/stdList",
    "fetch_kind": "json_api",
    "list_endpoint": "POST https://dbba.sacinfo.org.cn/stdQueryList",
    "params": "current, size, key, ministry, industry(省名), pubdate(-1/-3/-6/-12/-24/-36), date, status(现行/有更新版/废止)",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "★ 31 省统一入口。total=117718。实测 recordDate=2026-09-18(当天)。reviseStdCodes 给出被代替标准号，fzDate 给出废止日期。8 省实测 total：北京3929/上海2010/江苏5689/浙江2189/山东6359/广东2806/辽宁3954/四川3452。子接口 POST /snQueryList(公告)、POST /rnQueryList(月报)。"
  },
  {
    "name": "上海市市场监督管理局",
    "category": "地标",
    "url": "http://scjgj.sh.gov.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "未找到（首页 75 个 <a> 无任何标准/公告栏目）",
    "params": "未确认",
    "answers": [],
    "verification": "unverified",
    "province": "上海市",
    "note": "站点 HTTP 200 但 GB2312 编码，栏目结构未摸清。/zhuanlan/ /col/col1000/ /bzhcxfw/ /dfbz/ /bzcx/ /sitemap.html 全部 404。短期建议直接用 dbba，industry=上海市 实测 2010 条。"
  },
  {
    "name": "北京市市场监督管理局",
    "category": "地标",
    "url": "https://scjgj.beijing.gov.cn/",
    "fetch_kind": "unknown",
    "list_endpoint": "http://innerapp.capital-std.com/outerApp/standardSearchAction.do (已 502)",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "province": "北京市",
    "note": "首页实测抓到'北京市地方标准信息查询' => https://scjgj.beijing.gov.cn/cxfw/?serviceName=bzh_api_standard，但其后端 innerapp.capital-std.com 实测 HTTP 502。/zwgk/tzgg/ /zwgk/bzhgz/ /zwgk/zcwj/ /col/col31/ 全部 404。北京地标改用 dbba，industry=北京市 实测 3929 条。"
  },
  {
    "name": "江苏省市场监督管理局",
    "category": "地标",
    "url": "http://scjgj.jiangsu.gov.cn/col/col78963/index.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /col/col78963/index.html (通知公告)",
    "params": "条目 /art/<年>/<月>/<日>/art_<colid>_<id>.html；分页参数未确认",
    "answers": ["发布"],
    "verification": "verified",
    "province": "江苏省",
    "note": "HTTP 200。无独立的'地方标准批准发布公告'栏目，标准信息混在通知公告里，需关键词过滤。实测到 2026-09-14 条目。"
  },
  {
    "name": "浙江省市场监督管理局 / 浙江标准在线",
    "category": "地标",
    "url": "https://zlzx.zjamr.zj.gov.cn/bzzx/public/news/list/lstd/ALL/1.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /bzzx/public/news/list/lstd/ALL/<页码>.html (地方标准) ; /bzzx/public/std/list/ALL/<页码>.html (标准查询)",
    "params": "路径分页 ALL/<page>.html；分类 lstd(地标)/work(资讯)",
    "answers": ["发布", "修订", "现行性", "编号核验"],
    "verification": "verified",
    "province": "浙江省",
    "note": "★ 本批可解析性最好的省份。实测列表含'标准计划/征求意见/标准公示/标准公告/标准发布'全流程，标准查询页可检索标准号。省局公告公示页 /col/col1228969897/index.html（HTTP 200）。"
  },
  {
    "name": "山东省市场监督管理局",
    "category": "地标",
    "url": "http://amr.shandong.gov.cn/col/col76510/index.html?number=SD1002",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /col/col76510/index.html?number=SD1002 (通知公告)",
    "params": "条目 /art/<年>/<月>/<日>/art_76510_<id>.html；分页参数未确认",
    "answers": ["发布", "废止", "编号核验"],
    "verification": "verified",
    "province": "山东省",
    "note": "响应头 charset 实测为非法值 'ISO-88509-1'，实际是 GB2312/GBK，必须按 936 解码。实测到 2026-09-17 条目（日更）与专门废止公告。"
  },
  {
    "name": "广东省市场监督管理局",
    "category": "地标",
    "url": "https://amr.gd.gov.cn/zwgk/tzgg/index.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /zwgk/tzgg/index.html (通知公告) ; /zwgk/zcfg/gfxwj/index.html (规范性文件)",
    "params": "条目 /zwgk/tzgg/content/post_<id>.html；分页参数未确认",
    "answers": ["发布"],
    "verification": "verified",
    "province": "广东省",
    "note": "HTTP 200。无专用标准公告栏目。省标准化研究院 https://www.gdis.org.cn/ HTTP 200。"
  },
  {
    "name": "辽宁省市场监督管理局",
    "category": "地标",
    "url": "https://scjg.ln.gov.cn/scjdglj/fw/wyb/bz/index.shtml",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /scjdglj/fw/wyb/bz/index.shtml (标准) ; /scjdglj/fw/wyc/bz/index.shtml ; /scjdglj/fw/wyk/gsgg/index.shtml (公示公告)",
    "params": "未确认",
    "answers": ["发布"],
    "verification": "verified",
    "province": "辽宁省",
    "note": "HTTP 200，有专门的'标准'栏目。dbba 侧实测辽宁省市场监督管理局标准公告 CODE=2026年第35号 recordCount=56。"
  },
  {
    "name": "四川省市场监督管理局",
    "category": "地标",
    "url": "http://scjgj.sc.gov.cn/scsjgj/c104492/list.shtml",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /scsjgj/c104492/list.shtml (公示公告) ; /scsjgj/zfbzzqyj/list.shtml (省级地方标准草案征求意见)",
    "params": "未确认",
    "answers": ["发布", "修订"],
    "verification": "verified",
    "province": "四川省",
    "note": "HTTP 200。省标准化院 https://www.scis.net.cn/ HTTP 200。"
  },
  {
    "name": "全国标准信息公共服务平台-团体标准",
    "category": "团标",
    "url": "https://std.samr.gov.cn/tb/",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://std.samr.gov.cn/tb/search/tbPage",
    "params": "searchText, ICS, state, ISSUE_DATE, tbType, pageSize, pageNumber",
    "answers": ["发布", "编号核验"],
    "verification": "verified",
    "province": null,
    "note": "total=7906（覆盖度存疑，远小于团标平台实际规模，不能当唯一来源）。HREF 字段直接给出 ttbz.org.cn 详情页 URL，是绕过 ttbz WAF 的关键。"
  },
  {
    "name": "企业标准信息公共服务平台",
    "category": "团标",
    "url": "https://www.qybz.org.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "未找到公开 JSON",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "HTTP 200 但页面上仍挂着 2022-10 的机房改造通知，疑似长期未维护。对标准巡检无价值。"
  },
  {
    "name": "全国标准信息公共服务平台-地方标准(旧路径)",
    "category": "地标",
    "url": "https://std.samr.gov.cn/db/dbQuery",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://std.samr.gov.cn/db/search/dbPage",
    "params": "searchText, op, ISSUE_DATE, pageSize, pageNumber",
    "answers": [],
    "verification": "broken",
    "province": null,
    "note": "页面存在(HTTP 200)但接口实测恒返回 {\"total\":0,\"pageNumber\":1,\"rows\":[]}（试过 searchText=空/a、op=空）。地标请改用 dbba.sacinfo.org.cn。"
  },
  {
    "name": "ISO",
    "category": "国际",
    "url": "https://www.iso.org/standards.html",
    "fetch_kind": "js_rendered",
    "list_endpoint": null,
    "params": null,
    "answers": [],
    "verification": "broken",
    "province": null,
    "note": "实测 HTTP 403，正文'Just a moment... Enable JavaScript and cookies to continue'（Cloudflare JS 挑战）。需浏览器指纹方案。"
  },
  {
    "name": "IEC",
    "category": "国际",
    "url": "https://www.iec.ch/",
    "fetch_kind": "js_rendered",
    "list_endpoint": null,
    "params": null,
    "answers": [],
    "verification": "broken",
    "province": null,
    "note": "实测 HTTP 202 Accepted + 响应体 0 字节（bot 缓解）。https://www.iec.ch/dyn/www/f?p=103:6:0 同样 202/空。"
  },
  {
    "name": "全国标准信息公共服务平台-国际标准动态",
    "category": "国际",
    "url": "https://std.samr.gov.cn/gj/news?op=ISO",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /gj/news?op=ISO ; /gj/news?op=IEC",
    "params": "op=ISO|IEC",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "只是'国际标准动态'新闻，不含 ISO/IEC 标准现行状态目录，不能替代 ISO/IEC 官方查询。"
  },
  {
    "name": "全国标准信息公共服务平台-国外标准动态",
    "category": "国际",
    "url": "https://std.samr.gov.cn/gw/news?channelId=87",
    "fetch_kind": "html_list",
    "list_endpoint": "GET /gw/news?channelId=<87|88|89|90|91|92>",
    "params": "channelId（美/欧/德/英/澳新/韩 的具体映射未逐个确认）",
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "动态新闻性质，非现行状态目录。"
  },
  {
    "name": "国家食品安全风险评估中心",
    "category": "行标",
    "url": "https://www.cfsa.net.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "无标准目录栏目",
    "params": null,
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "HTTP 200，纯门户。https://sppt.cfsa.net.cn:8086/db（企标备案）实测 SSL 握手失败。对标准巡检无结构化价值。"
  },
  {
    "name": "中国标准化研究院",
    "category": "行标",
    "url": "https://www.cnis.ac.cn/wap/",
    "fetch_kind": "html_list",
    "list_endpoint": "无标准目录",
    "params": null,
    "answers": [],
    "verification": "verified",
    "province": null,
    "note": "HTTP 200 门户（首页 / 仅 860 bytes 跳转壳）。对标准巡检无结构化价值。"
  }
]
```

---

## 8. 给"标准巡检"系统的落地建议（一句话版）

1. **国标**：`nocGBPage`（发现新发布）+ `gbQueryPage`（现行性/编号核验）+ `openstd`（全文），三个端点覆盖全部需求。
2. **行标**：`hbba.sacinfo.org.cn/stdQueryList` 一个端点搞定（按 `ministry` 分口，绕开工信部/卫健委/应急部的登录墙与 WAF）。
3. **地标**：`dbba.sacinfo.org.cn/stdQueryList` 一个端点搞定 31 省，**不要逐省适配**。
4. **团标**：`std.samr.gov.cn/tb/search/tbPage` 拿元数据，`HREF` 跳 ttbz 详情，**不要硬刚 ttbz 的滑块 WAF**。
5. **国际**：国内渠道无统一入口，ISO/IEC 必须境外浏览器方案。
6. **住建工程建设标准**：唯一真实缺口（既不在 hbba 完整覆盖，主站又 JS 渲染），需单开 `ccsn.org.cn` 兜底适配器。
