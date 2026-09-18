# 中国法规类渠道调研报告（一手官方发布与查询渠道）

- 调研用途：为"法规标准巡检"系统选渠道——需自动发现**新发布 / 修订 / 废止**，并核验法规**是否现行**、**编号/名称是否变化**。
- 调研方式：全部结论来自本机实际 HTTP 访问（PowerShell `Invoke-WebRequest` + 浏览器 UA），不采信任何文章/仓库的描述作为结论。
- 访问时间：**2026-09-18**（所有 URL 均为当日实测）。
- 核实等级三态：`✅ 已实测访问` / `⚠️ 未核实（只搜到名字）` / `❌ 实测打不开或不存在`

> **关于二手信息的定位**：调研中出现过第三方文档（如 `cn-law-hub` 仓库的 `api_reference.md`）描述了 flk 的检索载荷。它只被当作"去哪测"的线索；下文每一条 flk 结论都是我自己 POST 实测得到的，其中就有与那份文档**不一致**的地方（见 §1.5，`flfgCodeId` 必须用**叶子**码，文档里的 `101/201/311` 实测全部返回 0 条）。

---

## 目录

1. [国家法律法规数据库（flk.npc.gov.cn）](#1-国家法律法规数据库flknpcgovcn)
2. [中国政府网系列（gov.cn）](#2-中国政府网系列govcn)
3. [司法部（含国家行政法规库）](#3-司法部含国家行政法规库)
4. [最高人民法院 / 最高人民检察院 / 司法部备案审查](#4-最高人民法院--最高人民检察院--司法部备案审查)
5. [部委级栏目](#5-部委级栏目)
6. [地方：省级地方性法规 / 地方政府规章](#6-地方省级地方性法规--地方政府规章)
7. [聚合入口与 flk 的关系](#7-聚合入口与-flk-的关系)
8. [业主清单中未能核实项目的判定](#8-业主清单中未能核实项目的判定)
9. [最一手渠道结论](#9-最一手渠道结论)
10. [机器可读附录](#10-机器可读附录)

---

## 1. 国家法律法规数据库（flk.npc.gov.cn）

### 国家法律法规数据库 · 检索接口（核心）
- 类别: 法律 / 行政法规 / 地方性法规 / 司法解释 / 监察法规（**聚合入口，覆盖面最广的单一渠道**）
- 实测链接: `https://flk.npc.gov.cn/law-search/search/list`（POST；页面壳 `https://flk.npc.gov.cn/search`）（访问时间: 2026-09-18）
- 实测证据: HTTP **200**，`{"msg":"查询成功","code":200,...}`；抓到的原文片段：`电力安全事故应急处置和调查处理条例` / `行政法规` / `gbrq=2026-08-30` / `sxrq=2027-01-01` / `sxx=4`。空关键词时 `total=30598`。
- 内容形态: **JSON API**（页面本身是 Vue SPA：`/assets/index-BZ9XHUiV.js`，`document.title` 为"国家法律法规数据库"；**必须走 XHR，不能解析 HTML**）。`baseURL:""`，即同源相对路径。
- 列表与分页（实测有效）:
  - 端点 `POST https://flk.npc.gov.cn/law-search/search/list`
  - Content-Type: `application/json;charset=utf-8`；`Referer: https://flk.npc.gov.cn/search` 建议带上
  - 实测载荷（可直接复用，**这是我实测跑通的版本**）:
    ```json
    {
      "searchRange": 1, "sxrq": [], "gbrq": [], "sxx": [],
      "searchType": 2, "xgzlSearch": false, "searchContent": "",
      "orderByParam": {"order": "-1", "sort": ""},
      "flfgCodeId": [], "zdjgCodeId": [], "gbrqYear": [],
      "pageNum": 1, "pageSize": 100
    }
    ```
  - 分页参数：`pageNum`（页码）、`pageSize`（**实测 100 可返回 100 条**）。实测 `pageNum=2&pageSize=3` 返回第 2 页 [2026-08-28] 起的数据。
  - 排序参数：`orderByParam.order`，实测 **`"-1"` = 按公布日期倒序（最新在前）**，`"1"` = 正序（实测返回 1993/1999/2004/2018 等旧数据）。`orderByParam.sort` 实测传 `"gbrq"` 有值；传 `sort:"gbrq"` 且 `order:"1"` 时服务端返回空（未报错），**建议直接用 `sort:""` + `order:"-1"` 的实测组合**。
  - 关键词检索：`searchContent` 实测生效（`"住房公积金管理条例"` → `total=24324`），且返回标题中带高亮标记：`<em class='highlight'>住房公积金</em><em class='highlight'>管理条例</em>` —— **入库前必须剥离 HTML 标签**。
  - 分类筛选：`flfgCodeId` **必须用 enumData 的叶子码**，实测 `["110"]`→78 条、`["220"]`→3 条；而**父级码 `101`/`201`/`311`/`221` 实测全部返回 `total=0`**。
  - 制定机关筛选：`zdjgCodeId`（叶子码见下）。时效性筛选：`sxx`（数组）。
  - 完整叶子码表（由 `GET /law-search/search/enumData` 实测解析，可直接作为 `flfgCodeId`）：
    | 分类 | codeId | 分类 | codeId |
    |---|---|---|---|
    | 宪法 | 100 | 地方性法规 | 230 |
    | 宪法相关法 | 110 | 自治条例 | 260 |
    | 民法商法 | 120 | 单行条例 | 270 |
    | 行政法 | 130 | 经济特区法规 | 290 |
    | 经济法 | 140 | 浦东新区法规 | 295 |
    | 社会法 | 150 | 海南自由贸易港法规 | 300 |
    | 生态环境法 | 155 | 法规性决定 | 305 |
    | 刑法 | 160 | 修改、废止的决定（地方法规） | 310 |
    | 诉讼与非诉讼程序法 | 170 | 高法司法解释 | 320 |
    | 法律解释 | 180 | 高检司法解释 | 330 |
    | 有关法律问题和重大问题的决定（部分） | 190 | 联合发布司法解释 | 340 |
    | 修正案 | 195 | 修改、废止的决定（司法解释） | 350 |
    | 修改、废止的决定（法律） | 200 | 行政法规 | 210 |
    | 修改、废止的决定（行政法规） | 215 | 监察法规 | 220 |
  - `zdjgCodeId` 叶子码（实测）：全国人大=100、全国人大常委会=110、国务院=120、国家监察委员会=130、最高人民法院=140、最高人民检察院=150；省级按序：北京=170、天津=180、河北=190…上海=**250**、浙江=**270**、广东=**350**（完整表可由 enumData 自动拉取，**建议程序化读取而非硬编码**）。
- **时效性 `sxx` 语义（决定性发现，四态已确认）**：
  从打包产物中提取到前端枚举定义原文：`[{label:"尚未生效",key:4},{label:"有效",key:3},{label:"已修改",key:2},{label:"已废止",key:1}]`，并用实测计数交叉验证：

  | sxx | 含义 | 实测 total（访问当日） |
  |---|---|---|
  | 1 | 已废止 | 3177 |
  | 2 | 已修改 | 7908 |
  | 3 | 有效 | 17233 |
  | 4 | 尚未生效 | 64 |

  → **这是"现行性核验"最直接的机器可判据**：`sxx=3` 即现行有效，`sxx=1` 已废止，`sxx=2` 已修改，`sxx=4` 尚未生效。
  ⚠️ 但实测存在**脏数据**：分页时出现过 `sxx=`（null）的记录（如`全国人民代表大会常务委员会关于修改《中华人民共和国律师法》的决定`），**判定逻辑必须容忍 null**。
- 更新节奏: **批量、非每日**。实测最新 30 条公布日期分布为 `2026-08-30:1, 2026-08-28:5, 2026-08-26:1, 2026-08-17:1, 2026-08-15:22`，而当日为 2026-09-18 → **最新公布日期比当天晚约 19 天**，且单日最多堆积 22 条，判据为"一次全国人大常委会会议/国务院常务会议后集中入库"。**建议巡检频率：每日 1–2 次足够，不要期望小时级。**
- 反爬: 实测响应头含 **`WZWS-RAY: 1129-1789733678.184-s5zzuc`** → 网宿（Wangsu）WAF 已在链路中，但**实测未触发验证码/限速**（连续数十次 POST 全部 200）。**注意**：站点另有 `GET /law-search/index/captchaImage`，实测返回 `{"msg":"操作成功","img":"/9j/4AAQSkZJRgAB..."}`（**有效 base64 图形验证码**）——该端点存在但**检索接口当前未强制要求它**；存在随时被启用的风险。
- 能回答: 发布 ✅ / 修订 ✅（`sxx=2` 已修改 + `sort=sxrq`）/ 废止 ✅（`sxx=1`）/ 现行性 ✅（`sxx=3`）/ 编号核验 ✅（`bbbs` 稳定 ID + `title`）
- 结论: **可直接适配（首选主渠道）**

### 国家法律法规数据库 · 详情接口
- 类别: 同上
- 实测链接: `https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff8081819ff541ea01a07eb41e2709fb`（访问时间: 2026-09-18）
- 实测证据: HTTP **200**，`code=200`；抓到的原文片段：`title=电力安全事故应急处置和调查处理条例`、`flxz=行政法规`、`zdjgName=国务院`、`gbrq=2026-08-30`、`sxrq=2027-01-01`、`sxx=4`。
- 内容形态: JSON API。返回字段键名实测为：`bbbs, ossFile, xgwj, lsyg, xgzl, flfg, flxz, zdjgName, gbrq, sxrq, title, sxx, content, xfFlag`。
- 列表与分页: 无（单条）。参数 `bbbs` = 列表返回的稳定 ID。
- 更新节奏: 随列表同步。
- 反爬: 同主站（WZWS）。
- 能回答: 发布 ✅ / 修订 ✅（`lsyg` 历史沿革）/ 废止 ✅ / 现行性 ✅（`sxx`）/ 编号核验 ✅
- 结论: **可直接适配**。`xfFlag`（是否修订）与 `lsyg`（历史沿革）对"修订"识别尤其有用。

### 国家法律法规数据库 · 枚举与首页聚合接口
- 类别: 聚合入口（元数据）
- 实测链接: `https://flk.npc.gov.cn/law-search/search/enumData`、`https://flk.npc.gov.cn/law-search/index/aggregateData`（访问时间: 2026-09-18）
- 实测证据: 两者均 HTTP **200**，`code=200`。enumData 返回 7936 字节，原文片段：`{"id":1,"parentId":0,"name":"宪法","codeId":100,...},{"id":2,...,"name":"法律","codeId":101...}`。aggregateData 原文片段：`{"@type":"com.ruoyi.law.domain.FlfgCountVo","count":302,"id":2,"key":"法律"}`。
- 内容形态: JSON API（**GET，无需参数，无需登录**）。
- 列表与分页: 无分页。`aggregateData` 返回各分类计数：法律=302、行政法规=606、监察法规=2、地方法规=15713、司法解释=560、宪法=1；并含 `xfsd` 新法速递（字段 `bbbs,title,gbrq,score,flxz`）。
- 更新节奏: 随库更新（`xfsd` 反映最新批次）。
- 反爬: 与主站同。**实测无验证码要求**。
- 能回答: 发布 ✅（新法速递）/ 修订 ⚠️ 间接 / 废止 ⚠️ 间接 / 现行性 ⚠️ 间接 / 编号核验 ❌
- 结论: **可直接适配**，建议作为"全库统计基线 + 新法速递轻量轮询"入口。
  另注：后端包名为 `com.ruoyi.law.*` → 该库基于 **RuoYi** 框架（Java）构建，这也解释了 `POST /list` + `pageNum/pageSize` 的载荷风格。

---

## 2. 中国政府网系列（gov.cn）

### 中国政府网 · 最新政策静态 JSON（意外发现的高价值渠道）
- 类别: 规范性文件 / 行政法规 / 国务院文件（聚合）
- 实测链接: `https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json`（访问时间: 2026-09-18）
- 实测证据: HTTP **200**，**263929 字节**；抓到的原文片段：`{"TITLE": "国务院办公厅关于进一步加强烟花爆竹全链条安全监管的意见", "SUB_TITLE": "", "URL": "https://www.gov.cn/zhengce/content/202609/content_7081356.htm", "DOCRELPUBTIME": "2026-09-17"}`。
- 内容形态: **静态 JSON 文件**（非 API，可直接 GET；字段仅 `TITLE, SUB_TITLE, URL, DOCRELPUBTIME`）。该 JSON 的路径是从 `/zhengce/zuixin/` 页面 HTML 中发现的相对引用 `./ZUIXINZHENGCE.json`。
- 列表与分页: 无分页参数，**一次性返回全量 1096 条**（实测），覆盖 2020-01-05 → 2026-09-17。
- 更新节奏: **高频、近实时**。实测最新 5 条为 `2026-09-17 / 09-14 / 09-11 / 09-10 / 09-04`，**最新一条即调研前一日**（对比 flk 最新只到 2026-08-30 → **比 flk 快约 19 天**）。
- 反爬: 实测无验证码、无 WAF 拦截头。
- 能回答: 发布 ✅ / 修订 ⚠️（需比对标题关键词"修改/废止"）/ 废止 ⚠️（同上）/ 现行性 ❌ / 编号核验 ⚠️（仅标题）
- 结论: **可直接适配**，是**时效性最好的"新发布"探针**；但它不含时效性状态，**不能单独回答"是否现行"**，需与 flk 或 xzfg 交叉。

### 中国政府网 · 政策文件库 / 政策检索（⚠️ 检索接口实测不可程序化）
- 类别: 规范性文件 / 国务院文件
- 实测链接: `https://www.gov.cn/zhengce/xxgk/`、`https://www.gov.cn/zhengce/`、`https://sousuo.www.gov.cn/s.htm?t=zhengcelibrary`（访问时间: 2026-09-18）
- 实测证据: `https://www.gov.cn/zhengce/` HTTP **200** / 40401 字节，原文片段：`最新政策 国务院办公厅关于进一步加强烟花爆竹全链条安全监管的意见 2026-09-17`。`https://www.gov.cn/zhengce/xxgk/` HTTP **200** / 226263 字节，原文片段含 `抱歉，没有找到相关结果。建议：1. 请您检查输入是否错误`（未带查询参数时的默认空态）。
- 内容形态: HTML 列表页（服务端渲染，可抓）；但**检索走 JS**。
- 列表与分页: 页面脚本引用 `/images/jquery.pagination.js` 与 `ZUIXINZHENGCE.json`。站内检索入口形如 `http://sousuo.www.gov.cn/sousuo/search.shtml?code=17da70961a7&dataTypeId=107&searchWord=`（`dataTypeId=107`/`14` 两个）。
- 反爬: 实测无验证码。
- 能回答: 发布 ✅（列表页）/ 其余 ❌
- 结论: **只能兜底抓取**。**注意实测负面结果**：`https://sousuo.www.gov.cn/s.htm?...` 带参访问实测 **404**；`sousuo.www.gov.cn/sousuo/search.shtml?searchWord=安全生产&dataTypeId=107` 实测 HTTP 200 但正文明确返回 `相关结果：约 0 个 ... 抱歉，没有找到相关结果` → **该检索页对无浏览器会话的直连不返回结果，不可程序化**。
  另有 `https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=...` 实测返回 `{"code":200,...,"totalCount":0,"pageSize":0}`（**带 `q` 反而不返回；不带 `q` 时曾返回 43 条**）→ 判为**需浏览器会话态**，不可依赖。

### 中国政府网 · 国家规章库
- 类别: 部门规章 / 地方政府规章（聚合）
- 实测链接: `https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 21161 字节，页面原文片段：`国家规章库包含现行有效部门规章和地方政府规章，中国政府网与中国政府法制信息网（司法部官网）同步公布，动态更新。部门规章数据来源于国务院各部、委员会...地方政府规章数据来源于省、自治区、直辖市和设区的市、自治州的人民政府网站和地方政府公报。国家规章库的规章文本，是各规章制定单位根据《法规汇编编辑出版管理规定》、按照统一体例格式汇编的国家正式版本。`
- 内容形态: HTML，但**结果列表由 JS 渲染**（首屏正文里没有规章条目，只有"抱歉/排序/日期筛选"等控件文案）。
- 列表与分页: 页面内含 `./libs/paging.js`、`./libs/jquery-4.0.0.min.js`；**实测未发现可直连返回数据的 JSON 端点**（对 `index.htm?searchWord=...` 的请求实测仍返回同一份 21161 字节的页面壳）。检索页签有 `部门` / `目录导航` / `部门规章` / `地方政府规章` / `按相关度` / `按时间` / `全文`/`标题` / `一月内`/`一年内`/`不限`。
- 更新节奏: **声明"动态更新"**（页面原文），但**实测无法验证节奏**（列表是 JS 渲染，抓不到条目日期）。
- 反爬: 实测无验证码。
- 能回答: 发布 ⚠️ / 修订 ⚠️ / 废止 ⚠️ / 现行性 ✅（页面明示"包含**现行有效**部门规章和地方政府规章"）/ 编号核验 ⚠️
- 结论: **不可程序化（当前形态）**——必须 JS 渲染才能取到列表。**关键提示**：其数据源自述为"各部委网站 + 国务院公报"与"各省政府网站 + 地方政府公报"，因此**抓一手部委/省政府栏目比抓本页更可靠**。同时它声明与司法部官网**同步**（见 §3 的实测反例）。

### 中国政府网 · 国务院公报
- 类别: 行政法规 / 国务院文件（正式版本）
- 实测链接: `https://www.gov.cn/gongbao/`、`https://www.gov.cn/gongbao/2026/`（访问时间: 2026-09-18）
- 实测证据: `https://www.gov.cn/gongbao/` HTTP **200** 但**仅 898 字节**，正文只有 `中国政府网_中央人民政府门户网站 点击跳转` → **是一个 JS 跳转壳，不是列表页**。`https://www.gov.cn/gongbao/2026/` 实测 **HTTP 403 Forbidden**。
- 内容形态: 跳转壳（JS）/ 403。
- 列表与分页: **未确认**（403 未取到任何列表结构）。
- 更新节奏: **未确认**。
- 反爬: `/gongbao/2026/` 实测 **403**（直接按年路径访问被拒）。
- 能回答: 发布 ⚠️ / 修订 ❌ / 废止 ❌ / 现行性 ❌ / 编号核验 ⚠️
- 结论: **不可程序化（实测 403 + 跳转壳）**。建议改用 `ZUIXINZHENGCE.json` 或 flk/xzfg 替代，**不要**把公报年目录作为巡检入口。

---

## 3. 司法部（含国家行政法规库）

### 司法部 · 国家行政法规库（xzfg.moj.gov.cn）— 独立的一手库
- 类别: **行政法规**（独立库，非 flk 镜像）
- 实测链接: `http://xzfg.moj.gov.cn/search2.html`（**注意：仅 HTTP，无有效 HTTPS**）（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 52537 字节，标题 `国家行政法规库`；抓到的原文片段：`根据《行政法规制定程序条例》汇编国家正式版本并动态更新，中国政府网与中国政府法制信息网(司法部官网)同步公布`、`现行有效 606 部`、`市场监督管理所条例 ... 2026-09-06公布 2026-11-01施行`、`电力安全事故应急处置和调查处理条例 ... 2011-07-07 2026-08-30`。
- 内容形态: **HTML 列表页（服务端渲染，可直接抓）**。页面内含未渲染的模板占位 `${Data.TimelinessName}`（前端小瑕疵，说明部分字段由 JS 二次填充，但**标题/公布日期/施行日期已在 HTML 中**）。
- 列表与分页: 端点 `http://xzfg.moj.gov.cn/search2.html`，**GET，分页参数 `PageIndex`**（实测 `PageIndex=2`、`PageIndex=3` 均返回不同数据 → **分页有效**）。
  表单字段（实测抓取自 `<input name="...">`）：`title`、`content`、`timeliness`、`publishFileNumber`、`publishTimeStart`、`publishTimeEnd`、`implementDateStart`、`implementDateEnd`、`sortField`（默认值 `PublishTime`）、`ascOrDesc`（默认值 `desc`）。
  ⚠️ **重要负面实测**：以 `?title=住房公积金管理条例` 直接 GET，实测**仍返回"现行有效 606 部"全量列表，未过滤** → 文案检索参数**在无会话直连下不生效**，判为需 JS/会话。
  → 因此**可程序化的是"全量分页遍历 + 按公布日期倒序"**（`sortField=PublishTime&ascOrDesc=desc` 为该页默认值），**不是**服务端关键词检索。
- 更新节奏: **比 flk 更快**。实测该页最新为 `市场监督管理所条例 2026-09-06公布`，而同日 flk 列表最新只到 `2026-08-30` → **xzfg 领先约 7 天**。
- 反爬: 实测无验证码、无 WAF 拦截标头；`http://xzfg.moj.gov.cn/` 根路径仅 364 字节（`首页`）为跳转入口。
- 能回答: 发布 ✅ / **修订 ✅（关键：每条带"历史沿革"多日期，如 `病原微生物实验室生物安全管理条例` 显示 `2004-11-12 2016-02-06 2018-03-19 2024-12-06 2026-08-08`）** / 废止 ⚠️（时效性筛选项含"现行有效"，**实测该库口径为"现行有效 606 部"**，即不含已废止）/ 现行性 ✅（库自述仅收现行有效 + 时效性字段）/ 编号核验 ✅（`publishFileNumber` 公布文号）
- 结论: **可直接适配**（分级抓取 + 全量遍历）。这是**行政法规修订沿革最好的一手来源**。

### 司法部 · 部门规章栏目
- 类别: 部门规章
- 实测链接: `https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 41543 字节，抓到的原文片段：`首页 > 法律法规规章 > 部门规章`、`2026-06-05 外国医师来华短期行医暂行管理办法`、`2026-06-05 医师资格考试违纪违规处理规定`。
- 内容形态: HTML 列表页（服务端渲染，可直接抓）。
- 列表与分页: 栏目路径 `/pub/sfbgw/flfggz/` 下的同级栏目实测为：`flfggzbmgz`(部门规章)、`flfggzdfzwgz`(地方政府规章)、`flfggzfgjd`(法规解读)、`flfggzflk`、`flfggzflty`(法律条约)、`flfggzxzfg`。**分页参数未确认**。
- 更新节奏: **未确认**（首屏仅 4 条且日期均为 2026-06-05，疑似非严格时序或该栏目更新很慢）。
- 反爬: 实测无验证码。
- 能回答: 发布 ✅ / 修订 ⚠️ / 废止 ⚠️ / 现行性 ❌ / 编号核验 ⚠️
- 结论: **只能兜底抓取**。

### 司法部 · 法律法规规章其它子栏目（实测为空壳 / 重定向）
- 类别: 法律 / 国际条约 / 地方政府规章
- 实测链接: `https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/`、`.../flfggzflty/`、`.../flfggzxzfg/`、`.../flfggzdfzfgz/`（访问时间: 2026-09-18）
- 实测证据: `flfggzflk/` HTTP **200 但仅 118 字节**，**原始响应体为**：
  ```
  <SCRIPT LANGUAGE="JavaScript">
  	var htm = "https://flk.npc.gov.cn/";
          document.location.href=htm;
  </SCRIPT>
  ```
  `flfggzflty/` 同型（123 字节）；`flfggzxzfg/` HTTP 200 / 130 字节（空）；`flfggzdfzfgz/`（我按命名规律推测的路径）实测 **404**。
- 内容形态: JS 重定向壳 / 空响应 / 404。
- 列表与分页: 无。
- 更新节奏: 不适用。
- 反爬: 无。
- 能回答: 全部 ❌
- 结论: **不可程序化**。**最关键结论：司法部官网的"国家行政法规库"入口实质是把用户 JS 跳转到 `flk.npc.gov.cn`**；而**真正独立的行政法规库在 `xzfg.moj.gov.cn`**（§3 第一条）——两者不同，不要混淆。

---

## 4. 最高人民法院 / 最高人民检察院 / 司法部备案审查

### 最高人民法院 · 司法解释
- 类别: 司法解释
- 实测链接: `https://www.court.gov.cn/fabu/gengduo/16.html`（列表）、`https://www.court.gov.cn/fabu/xiangqing/1.html`（详情）（访问时间: 2026-09-18）
- 实测证据: 列表 HTTP **200** / 16934 字节，标题 `司法解释 - 中华人民共和国最高人民法院`，抓到的原文片段：`最高人民法院关于适用《中华人民共和国生态环境法典》时间效力的若干规定 2026-08-06`、`最高人民法院关于修改《最高人民法院关于审理船舶油污损害赔偿纠纷案件若干问题的规定》等九件司法解释的决定 2026-08-06`。详情页 HTTP **200** / 25177 字节，原文片段：`法释〔2009〕...`、`《最高人民法院关于审理侵犯专利权纠纷案件应用法律若干问题的解释》已于 2009 年 12 月 21 日由最高人民法院审判委员会第 1480 次会议通过，现予公布，自 2010 年 1 月 1 日起施行。`
- 内容形态: HTML 列表页 + HTML 详情页（服务端渲染，可直接抓）。
- 列表与分页: 栏目 ID 实测：`/fabu/gengduo/16.html` = **司法解释**；同族还有 `14, 15, 17, 21, 22, 79, 108, 662`（未逐一核对语义）。详情页为 `/fabu/xiangqing/{数字ID}.html`（实测 ID 如 `508041, 511931, 92392`，**非线性、不连续**）。列表页含"更多"分页。
- 更新节奏: **较新**。实测最新条目 `2026-08-06`（当日 2026-09-18，滞后约 6 周，符合司法解释发布节奏）。
- 反爬: 实测无验证码、无 WAF 头。
- 能回答: 发布 ✅ / 修订 ✅（实测有条目名为"关于修改...等九件司法解释的决定"）/ 废止 ⚠️（需标题关键词匹配）/ 现行性 ⚠️（页面标注施行日期，但无统一时效性字段）/ 编号核验 ✅（`法释〔年〕号`）
- 结论: **可直接适配**（HTML 解析即可；建议加"修改/废止"标题正则做变更识别）。

### 最高人民检察院 · 法律法规规范性文件
- 类别: 司法解释 / 规范性文件
- 实测链接: `https://www.spp.gov.cn/spp/flfgxwj/`、`https://www.spp.gov.cn/spp/flfgxwj/index.shtml`（访问时间: 2026-09-18）
- 实测证据: 两个 URL **均 HTTP 200，且字节数完全相同（72888）**，正文片段：`...检察业务 ... 法律政策研究 案件管理 ... 法律法规规范性文件` —— **正文等同于站点首页，未出现任何"法律法规规范性文件"条目**。
- 内容形态: HTML，但**该栏目路径返回的是首页内容（疑似 SPA/占位，栏目内容未服务端渲染）**。
- 列表与分页: **未确认**（路径未返回该栏目列表）。
- 更新节奏: **未确认**。
- 反爬: 实测无验证码。
- 能回答: 发布 ⚠️ / 修订 ❌ / 废止 ❌ / 现行性 ❌ / 编号核验 ❌
- 结论: **不可程序化（当前实测形态）**。若需最高检司法解释，**优先走 flk 的 `flfgCodeId=["330"]`（高检司法解释）或 `340`（联合发布）**，实测这两类在 flk 中是有数据的。

### 司法部 · 备案审查
- 类别: 备案审查（地方性法规/规章的合法性审查）
- 实测链接: **未能定位到独立的一手备案审查栏目 URL**（访问时间: 2026-09-18）
- 实测证据: 司法部首页 `https://www.moj.gov.cn/` HTTP **200** / 98266 字节，导航原文片段：`法律法规规章 法律 法律条约 行政法规 法规解读 部门规章 地方政府规章 --> 国家行政法规库 --> 政府信息公开`、`立法意见征集 进入征集系统` —— **导航中不存在"备案审查"独立入口**；实测按命名规律推测的 `.../flfggzdfzfgz/` 返回 **404**。
- 内容形态: 未确认。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: 未实测到。
- 能回答: 发布 ⚠️ / 修订 ❌ / 废止 ❌ / 现行性 ❌ / 编号核验 ❌
- 结论: **未确认（未找到公开的一手备案审查检索栏目）**。旁证：`广东人大网`（`https://www.gdpc.gov.cn/`）实测首页有新闻 `2026年部分地方备案审查工作座谈会暨备案审查工作培训班在广州举办`，说明备案审查属**工作动态**而非**可检索法规库**。**建议不要把它作为巡检渠道。**

---

## 5. 部委级栏目

### 应急管理部 · 规章（zfxxgkpt 法定主动公开内容）
- 类别: **部门规章**（本次调研中**最好用的部委级渠道**）
- 实测链接: `https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 18045 字节，抓到的原文片段：`煤矿企业安全生产许可证实施办法 （2026年8月31日应急管理部令第22号公布 自2027年1月1日起施行。）`、`煤矿重大事故隐患判定标准 （2020年11月20日应急管理部令第4号公布，2026年5月24日应急管理部令第21号修订。）`
- 内容形态: **HTML 列表页（服务端渲染，可直接抓）**；附件为**直接文件链接**（实测后缀 `.pdf` / `.doc` / `.docx` / `.wps`，形如 `https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/202609/P020260904609285161605.pdf`）。
- 列表与分页: **分页实测有效**：`.../gz11/index_1.shtml`（HTTP 200 / 18466 字节）、`.../gz11/index_2.shtml`（HTTP 200 / 19513 字节）。即 **`index_{n}.shtml` 模式**。实测页面**无 ajax/JSON 端点**（检测 `ajax|.json|fetch(` 结果为 NO）。
- 更新节奏: **很新**。实测首条为 `2026年8月31日应急管理部令第22号公布`（当日 2026-09-18，滞后约 2.5 周）。
- 反爬: 实测无验证码、无 WAF 拦截。
- 能回答: 发布 ✅ / **修订 ✅（正文明确写"第21号修订"）** / 废止 ⚠️（需关键词匹配）/ 现行性 ⚠️（除列出施行日期外无统一状态字段）/ **编号核验 ✅（部令编号如"应急管理部令第22号"直接写在标题行）**
- 结论: **可直接适配**。**这是"部令编号核验"最干净的样本**。

### 应急管理部 · 法律法规
- 类别: 法律 / 行政法规（转载栏目）
- 实测链接: `https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 72740 字节，标题 `法律法规`，抓到的原文片段：`首页 > 服务 > 法律法规标准 > 法律法...`
- 内容形态: HTML 列表页。
- 列表与分页: 未确认。**注意**：我曾按命名规律推测 `https://www.mem.gov.cn/fw/flfgbz/flfg/` → 实测 **404**；`https://www.mem.gov.cn/fw/flfgbz/`（仅 507 字节）与 `/bz/`（465 字节）均为**空壳**。
- 更新节奏: 未确认。
- 反爬: 无。
- 能回答: 发布 ⚠️ / 其余 ⚠️
- 结论: **只能兜底抓取**。

### 生态环境部 · 法规标准
- 类别: 法律 / 行政法规 / 规章 / 标准
- 实测链接: `https://www.mee.gov.cn/ywgz/fgbz/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 80593 字节，抓到的原文片段：`法规标准 法律 法律 行政法规 行政法规 规章 规章 标准 标准 ... 中华人民共和国生态环境法典 2026-03-13`、`中华人民共和国渔业法 2025-12-27`
- 内容形态: HTML 列表页（服务端渲染，可直接抓），文案为分类导航。
- 列表与分页: 未确认（未取到分页参数）。
- 更新节奏: **偏慢**。实测首条为 `2026-03-13`（当日 2026-09-18，滞后约 6 个月）→ 该栏目为"法规汇编式"而非"新闻式"更新。
- 反爬: 无。
- 能回答: 发布 ⚠️（滞后）/ 修订 ⚠️ / 废止 ⚠️ / 现行性 ❌ / 编号核验 ⚠️
- 结论: **只能兜底抓取**（不适合做"新发布"发现）。

### 住房和城乡建设部 · 政策发布
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.mohurd.gov.cn/`（首页，HTTP 200 / 78949 字节）；栏目 `https://www.mohurd.gov.cn/gongkai/zhengce/`（访问时间: 2026-09-18）
- 实测证据: 首页正文原文片段（首屏**无日期**，以要闻为主）：`全国住房城乡建设工作会议在京召开`、`时政要闻 领导动态 政策发布 建设要闻 地方信息`、`2026-09-18 习近平总书记指引民族团结进步事业高质量发展`。栏目路径 `/gongkai/zhengce/` 实测 **HTTP 403 Forbidden**。
- 内容形态: 首页 HTML 可抓；**目标栏目 403**。
- 列表与分页: **未确认**（403）。
- 更新节奏: 未确认。
- 反爬: **实测 `/gongkai/zhengce/` 返回 403**（反爬/权限已实测到）。
- 能回答: 发布 ⚠️ / 修订 ❌ / 废止 ❌ / 现行性 ❌ / 编号核验 ❌
- 结论: **不可程序化（实测 403）**。

### 国家市场监督管理总局 · 法规司
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200 但仅 3589 字节**，抓到的原文片段：`法规司 你的位置: 首页 > 政务 > 政府信息公开 > 法定主动公开内容 > 法规司 法规司` —— **只有栏目名，无任何文件条目**。
- 内容形态: **JS 空壳**（栏目框架存在，内容未服务端渲染）。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: 未实测到。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测为 JS 空壳）**。

### 交通运输部
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.mot.gov.cn/`（HTTP 200 / 92003 字节）；栏目 `https://www.mot.gov.cn/zhengcejiedu/`（访问时间: 2026-09-18）
- 实测证据: 首页原文片段：`交通运输部召开部安委会全体会议暨中秋国庆假期和四季度交通运输安全生产视频会议 2026-09-18`。栏目 `/zhengcejiedu/` 实测 **HTTP 404 Not Found**（我按命名规律推测的路径不存在）。
- 内容形态: 首页 HTML 可抓；**目标栏目 404**。
- 列表与分页: **未确认**（未定位到正确的规章栏目路径）。
- 更新节奏: 首页为高频（实测当日 2026-09-18 有稿）。
- 反爬: 无（首页）。
- 能回答: 发布 ⚠️ / 其余 ❌
- 结论: **不可程序化（未定位到栏目；推测路径实测 404）**。需人工在站内确认正确栏目名后重测。

### 国家卫生健康委员会
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.nhc.gov.cn/`、`https://www.nhc.gov.cn/fzs/`（访问时间: 2026-09-18）
- 实测证据: 两个 URL **均实测 `HTTP 412 Precondition Failed`**（响应状态码未指示成功）。
- 内容形态: **无法取得**（412）。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: **实测 412**（WAF/前置条件校验已实测到；对无浏览器指纹的直连直接拒绝）。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测 412）**。需带浏览器指纹/JS 挑战方能访问。

### 工业和信息化部 · 政策文件
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.miit.gov.cn/zwgk/zcwj/index.html`（访问时间: 2026-09-18）
- 实测证据: HTTP **200 但仅 2116 字节**，正文**只有标题** `政策文件`（无条目）。另实测其 JSON 网关 `https://www.miit.gov.cn/api-gateway/jpaas-web-server/frontDocument/list?...` 返回 `{"roles":null,"permissions":null,"success":false,"code":"601","data":{},"message":"您访问的URL不合规，请检查"}`。
- 内容形态: **JS 空壳** + 网关返回明确拒绝（`您访问的URL不合规`）。
- 列表与分页: 接口存在（`frontDocument/list`）但**实测被网关拒绝**，参数与鉴权未知。
- 更新节奏: 未确认。
- 反爬: **实测网关拒绝码 `601`**（已实测到）。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测空壳 + 网关 601 拒绝）**。

### 人力资源和社会保障部
- 类别: 部门规章 / 规范性文件
- 实测链接: `https://www.mohrss.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200 但仅 986 字节**，且**响应体是混淆的 JS 反爬脚本**，原文片段：`<script>function a(a){function n(){var a={wQzOV:_0x649a("0x4"),iTyzs:function(a,n){return a+n}}...`、`t+="EO_Bot_Ssid=";`。
- 内容形态: **JS 反爬挑战页**（需执行 JS 生成 `EO_Bot_Ssid` Cookie 后才能拿到真实内容）。
- 列表与分页: 未确认（无法穿透）。
- 更新节奏: 未确认。
- 反爬: **实测到 JS Cookie 挑战（`EO_Bot_Ssid`）**。
- 能回答: 全部 ❌
- 结论: **不可程序化（需无头浏览器执行 JS）**。若必须采集，只能上 Playwright/Puppeteer 类方案。

---

## 6. 地方：省级地方性法规 / 地方政府规章

> 一手性判定原则：**地方性法规**的一手来源是**本级人大**（法规公布栏目）；**地方政府规章**的一手来源是**本级政府门户**（文件库）；**司法厅**多为民俗普法/工作动态，通常**不是**法规条文的发布源。

### 上海市人大 · 法规公布（**上海市地方性法规一手来源**）
- 类别: **地方性法规**（含浦东新区法规）
- 实测链接: `https://www.shrd.gov.cn/shrd/fggb/fggb.html`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 11229 字节，标题 `上海人大`，抓到的原文片段：`人大首页 > 法规公布 法规公布 上海市人民代表大会常务委员会关于修改《上海市环境保护条例》等12件地方性法规的决定`、`上海市人民代表大会常务委员会关于修改《上海市市民体育健身条例》等4件地方性法规和废止《上海市酒类商品产销管理条例》的决定`
- 内容形态: HTML 列表页（服务端渲染，可直接抓）。
- 列表与分页: 同域栏目实测：`/shrd/fggb/fggb.html`（法规公布）、`/shrd/lfdt/lfdt.html`（立法动态）、`/shrd/lfdtej/lfdtej.html`、`/shrd/lfyjzq/lfyjzq.html`（立法意见征集）。**分页参数未确认**。备用同源镜像实测可用：`https://cms.odb.sh.cn/shrd/`（HTTP 200 / 96169 字节，内容与 `www.shrd.gov.cn` 一致）。
- 更新节奏: **未确认**（页面**不显示日期**，仅列标题）→ 巡检需靠"标题集合差分"而非日期。
- 反爬: 实测无验证码。注：`https://www.shrd.gov.cn/` 首页返回体中出现 SPA 标记词（JSAPP 命中），但 `/shrd/fggb/fggb.html` 栏目页为**真实服务端渲染 HTML**。
- 能回答: 发布 ✅ / **修订 ✅（原文"关于修改…等12件地方性法规的决定"）** / **废止 ✅（原文"…和废止《上海市酒类商品产销管理条例》的决定"）** / 现行性 ⚠️（需靠"修改/废止的决定"推断）/ 编号核验 ⚠️
- 结论: **可直接适配**。正文天然包含"修改/废止"字样，**对变更发现极其友好**，但**缺日期字段**是主要短板。

### 上海市司法局
- 类别: 地方性法规 / 地方政府规章（**非一手**）
- 实测链接: `https://sft.sh.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: 实测 **ERR: The SSL connection could not be established**（TLS 握手失败，未取得任何 HTTP 状态码）。
- 内容形态: 无法取得。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: **实测 TLS/SSL 连接失败**。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测 SSL 失败）**。即便是可访问，司法厅也**不是**地方性法规的一手来源，优先级低于人大。

### 上海市人民政府 · 近期信息公开（上海市政府规章/规范性文件入口）
- 类别: 地方政府规章 / 规范性文件
- 实测链接: `https://www.shanghai.gov.cn/nw12344/index.html`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 28269 字节，标题 `近期信息公开_上海市人民政府`，抓到的原文片段：`上海市人民政府关于加强第48届世界技能大赛期间无人机等航空器安全管理的通告 2026-09-17`、`上海市市场监督管理局关于印发《上海市撤销虚假企业登记实施办法》的通知 2026-09-15`
- 内容形态: HTML 列表页（服务端渲染，可直接抓），**带日期**。
- 列表与分页: 实测 `?tab=2` 参数**不改变返回内容**（返回体与无参完全一致，28269 字节）→ 判为 JS tab 切换，**服务端分页/筛选参数未确认**。
- 更新节奏: **高频**。实测最新 `2026-09-17`（当日 2026-09-18，滞后 1 天）。
- 反爬: 实测无验证码。
- 能回答: 发布 ✅ / 修订 ⚠️ / **废止 ⚠️（需关键词）** / 现行性 ❌ / 编号核验 ⚠️
- 结论: **可直接适配（用于"新发布"发现）**；**但需注意它混合了通告/通知/发布会等多种体裁，不是纯"地方政府规章"库**，入库需按文种过滤。

### 北京市人民政府 · 政策文件
- 类别: 地方政府规章 / 规范性文件
- 实测链接: `https://www.beijing.gov.cn/zhengce/zhengcefagui/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / **394586 字节**（篇幅最大），标题 `政策文件_首都之窗_北京市人民政府门户网站`，抓到的原文片段：`北京市文化和旅游局关于废止《北京市文化和旅游局关于印发...的通知》的通告 2026-09-17`、`北京市人民政府办公厅关于印发《北京市村民自建住宅消防安全管理办法》的通知 2026-09-16`
- 内容形态: HTML 列表页（服务端渲染，可直接抓）。条目带"是"字段（疑似"是否有效/主动公开"标志位，**语义未确认**）。
- 列表与分页: **未确认**（未取到分页参数）。
- 更新节奏: **高频**。实测最新 `2026-09-17`（当日 2026-09-18，滞后 1 天）。
- 反爬: 实测无验证码。
- 能回答: 发布 ✅ / 修订 ⚠️ / **废止 ✅（实测原文含"关于废止…的通告"）** / 现行性 ⚠️ / 编号核验 ⚠️
- 结论: **可直接适配**。

### 北京市人大
- 类别: 地方性法规
- 实测链接: `https://www.bjrd.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 66465 字节，标题 `北京市人民代表大会常务委员会`，抓到的原文片段：`市人大常委会会议闭幕 表决通过北京市测绘地理信息条例等法规 李秀领主持`、`市人大常委会召开会议 审议噪声污染防治条例草案等议题`
- 内容形态: HTML（服务端渲染）。
- 列表与分页: **未确认**（未定位到独立"法规公布"栏目页）。
- 更新节奏: 实测有 2026 年 9 月立法动态。
- 反爬: 无。
- 能回答: 发布 ⚠️（以新闻形式）/ 修订 ⚠️ / 废止 ⚠️ / 现行性 ❌ / 编号核验 ❌
- 结论: **只能兜底抓取**（北京人大首页以**立法新闻**为主，未见结构化"法规公布"列表；对比上海人大有专门 `/shrd/fggb/` 栏目，北京更弱）。

### 广东人大网（**广东省地方性法规一手来源**）
- 类别: 地方性法规
- 实测链接: `https://www.gdpc.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 109518 字节，标题 `广东人大网`，抓到的原文片段：`省十四届人大常委会第二十六次会议闭幕 黄楚平出席会议并讲话`、`2026年部分地方备案审查工作座谈会暨备案审查工作培训班在广州举办`
- 内容形态: HTML（服务端渲染）。
- 列表与分页: 栏目含 `权威发布` / `人大履职` / `信息公开`；**分页参数未确认**。
- 更新节奏: 实测有 2026 年 9 月常委会动态。
- 反爬: 无。**注意**：我最初误用了 `https://www.gzrd.gov.cn/`（实测 HTTP 200 但标题为 **`贵州省人民代表大会常务委员会`** —— **该域名属贵州而非广东**）。正确域名实测有两个：`https://www.gdpc.gov.cn/`（**可用**）与 `https://www.rd.gd.cn/`（实测 **SSL 连接失败**）。
- 能回答: 发布 ⚠️ / 修订 ⚠️ / 废止 ⚠️ / 现行性 ❌ / 编号核验 ❌
- 结论: **只能兜底抓取**。

### 广东省人民政府 · 文件库
- 类别: 地方政府规章 / 规范性文件（**含正式文号**）
- 实测链接: `https://www.gd.gov.cn/zwgk/wjk/`、`https://www.gd.gov.cn/zwgk/wjk/qbwj/`（访问时间: 2026-09-18）
- 实测证据: `/zwgk/wjk/` HTTP **200** / 99696 字节，标题 `文件库 广东省人民政府门户网站`，抓到的原文片段：`名称 文号 发布日期 广东省人民政府关于湛江市吴川市吴阳镇等5个历史文化名镇名村保护规划的批复 粤府函〔2026〕213号 2026-09-15`。`/zwgk/wjk/qbwj/`（全部文件）HTTP **200** / 62934 字节，原文片段：`全部文件 广东省人民政府门户网站 ... 广东省人民政府关于调整我省最低工资标准的通知 粤府函〔2026〕188号 2026-08-13`
- 内容形态: **HTML 列表页（服务端渲染）**，表格列为 `名称 / 文号 / 发布日期` —— **天然结构化**。
- 列表与分页: 分类页签实测：`政府文件` / `全部文件` / `粤府令` / `粤府` / `粤府函` / `粤府办` / `粤办函`。`/qbwj/` = 全部文件。**分页参数未确认**。
- 更新节奏: **高频**。实测最新 `2026-09-15`（当日 2026-09-18，滞后 3 天）。
- 反爬: 实测无验证码。
- 能回答: 发布 ✅ / 修订 ⚠️ / 废止 ⚠️ / 现行性 ❌ / **编号核验 ✅（`粤府函〔2026〕213号` 直接成列）**
- 结论: **可直接适配**，**文号列是编号核验的优质字段**。

### 浙江省司法厅
- 类别: 地方性法规 / 地方政府规章（**非一手**）
- 实测链接: `https://sft.zj.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 56726 字节，抓到的原文片段：`省司法厅召开律师行业高质量发展座谈会 2026-09-17`、`我省2026年国家统一法律职业资格考试客观题考试顺利完成 2026-09-14`
- 内容形态: HTML（服务端渲染），内容以**厅务动态**为主。
- 列表与分页: 未确认。
- 更新节奏: 高频（厅务新闻）。
- 反爬: 无。
- 能回答: 发布 ❌（无法规条文）/ 其余 ❌
- 结论: **不可程序化（作为法规渠道）**。实测证实司法厅是**工作动态**源，**不能替代人大/政府网**。

### 浙江省人大（**实测 JS 空壳**）
- 类别: 地方性法规
- 实测链接: `https://www.zjrd.gov.cn/`（访问时间: 2026-09-18）
- 实测证据: HTTP **200** / 58727 字节，但标题 `中国浙江人大`，**去标签后正文仅为**：`中国浙江人大 关闭 关闭`。
- 内容形态: **JS 空壳 / 框架页**（服务端未输出任何条目）。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: 未实测到（内容为空是先于反爬的问题）。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测无服务端内容）**。

### 浙江省人民政府 · 省政府文件（**实测 JS 空壳**）
- 类别: 地方政府规章 / 规范性文件
- 实测链接: `https://www.zj.gov.cn/col/col1229019364/index.html`（访问时间: 2026-09-18）
- 实测证据: HTTP **200 但仅 1750 字节**，标题 `省政府文件`，**去标签后正文仅为**：`省政府文件`（无任何条目）。
- 内容形态: **JS 空壳**。
- 列表与分页: 未确认。
- 更新节奏: 未确认。
- 反爬: 未实测到。
- 能回答: 全部 ❌
- 结论: **不可程序化（实测 JS 空壳）**。

---

## 7. 聚合入口与 flk 的关系

| 入口 | 实测性质 | 与 flk 的关系 |
|---|---|---|
| `flk.npc.gov.cn` | **本体**（RuoYi 后端，JSON API） | 覆盖法律/行政法规/地方性法规/司法解释/监察法规，实测 `total=30598` |
| 司法部「国家行政法规库」`moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/` | **JS 重定向壳**（118 字节，`document.location.href="https://flk.npc.gov.cn/"`） | **就是跳转到 flk，不是独立源** |
| 司法部 国家行政法规库 `xzfg.moj.gov.cn` | **独立真库**（606 部，服务端渲染） | **与 flk 不是同一套数据**：实测 xzfg 最新 `2026-09-06`，flk 最新 `2026-08-30` → **xzfg 更早/更快**，且提供"历史沿革"多日期 |
| 中国政府网「国家规章库」 | JS 渲染，页面自述"与司法部官网同步公布" | 自述同步**部门规章+地方政府规章**（这类**不在** flk 中，因为 flk 不含部门规章），是**互补**而非重复 |
| `aggregateData` 分类计数 | 实测：行政法规=**606** | **与 xzfg 的"现行有效 606 部"数值一致** → 两库在行政法规口径上互相印证 |

**结论**：flk 是**覆盖面最广的单一入口**（有统一的 `sxx` 时效性字段），但**不含部门规章与地方政府规章**；这两类必须靠 xzfg / 部委栏目 / 省政府文件库补齐。

---

## 8. 业主清单中未能核实项目的判定

> 判定方式：用 `gh api repos/{owner}/{repo}` 与 `gh search repos` **实际访问 GitHub**，逐条核实。

| 名称 | 判定 | 实测证据 | 说明 |
|---|---|---|---|
| `Law-Crawler-RPA-RAG-MCP` | **✅ 真实存在** | `gh api repos/Yuhamixli/Law-Crawler-RPA-RAG-MCP` → EXISTS，stars=**32**，最近推送 `2026-04-28`，描述"一个用于爬取中国法律法规并构建智能问答系统的项目。" | 全名 `Yuhamixli/Law-Crawler-RPA-RAG-MCP`。与本次调研主题高度相关，**值得人工细读其数据源**（本次未克隆代码，故其是否真用 flk 未核实） |
| `legal-database` | **⚠️ 存在同名仓库，但非本项目所需** | `gh api repos/sublatesublate-design/legal-database` → EXISTS，stars=**5**，**description 为空** | 名为 `legal-database` 的仓库在 GitHub 上很多（`cc-archive/legaldb` 65★、`berkmancenter/lumendatabase` 168★ 等均**非中国法规**）。**无法确认业主指的是哪一个** → 判为**名称有歧义，不构成可用渠道线索** |
| `china-law-search` | **❌ 未找到该名称的仓库** | `gh search repos "china-law-search"` → **无同名仓库命中**（返回的是 `chinese-law-mcp`、`Lawdown`、`ChineseLawsSearch` 等近似名，均非该名） | 仅搜到一个**同名技能页**（`skills.sh/nigo81/nigo-skills/china-law-search/security/...`），属第三方技能市场页面，**非仓库**。判为**未找到，疑似不存在或名称有误** |
| `GovPing` | **❌ 未找到，疑似不存在或名称有误** | `gh search repos "GovPing"` / `"govping"` → **零命中**；只返回 `govp-protocol/govp-js`、`gemacode/govp-for-woocommerce` 等 **GOVP 开源协议**（与"法规巡检"无关，是电商/协议验证领域） | 判为**未找到，疑似不存在或名称有误**。**警示**：`GovPing` 与 `GOVP` 只差两个字母，易被误当同一事物 |
| `RegRadar` | **✅ 名称真实存在，但与中国法规无关** | `gh api repos/kingabzpro/RegRadar` → EXISTS，stars=**2**，描述"RegRadar watches the worlds regulators so you dont have to."；`RahimAbbas55/RegRadar` → EXISTS，描述为 **FCA Handbook**（英国金融监管）RAG；`gh search` 另见 `Shivay00001/regradar`（**印度**监管）、`sidnov6/regradar`（**EU EUR-Lex**） | **"RegRadar"是被多个互不相关的项目复用的名字**，其中**没有一个是针对中国法规**的。若业主清单里指"中国法规雷达"，**该名称对不上** |
| `at-ris-mcp` | **✅ 真实存在，但用途完全不符（奥地利）** | `gh search repos "at-ris-mcp"` → `paragraflabs/at-ris-mcp`，stars=**1**，描述"MCP server & Python client for **Austria's** legal information system (RIS): federal & state law, case law, gazettes, change monitoring" | **这是本次最需警惕的一条**：`RIS` = 奥地利 Rechtsinformationssystem，`at-` = Austria。功能（change monitoring）看似贴切，**但对中国法规零覆盖**。**不可采用** |

**总体结论**：业主初步清单 6 项中，**2 项真实且相关（`Law-Crawler-RPA-RAG-MCP` 相关；`RegRadar` 真实但不相关）**，**1 项真实但同名歧义（`legal-database`）**，**1 项真实但国别完全错误（`at-ris-mcp`）**，**2 项未找到（`china-law-search`、`GovPing`）**。**没有一项是本次调研的权威一手渠道**——它们是工具/项目，不是发布源，**不应作为巡检系统的数据基座**。

---

## 9. 最一手渠道结论

> 原则：**法律/行政法规/地方性法规/司法解释 → flk（唯一有统一时效性字段的库）**；**行政法规的修订沿革 → xzfg**；**部门规章 → 部委站点直抓**；**地方政府规章 → 省政府文件库**；**最快"新发布"探针 → gov.cn 静态 JSON**。

| 类别 | 应该用哪个 URL | 为什么 |
|---|---|---|
| **法律** | `POST https://flk.npc.gov.cn/law-search/search/list`（`flfgCodeId` 取法律类叶子码；`sxx=3` 现行） | 唯一提供 `sxx` 现役性四态的库；实测 30598 条 |
| **行政法规（现行性）** | 同上（叶子码 `210`）+ `sxx=3` | 与 xzfg 的"606 部"口径实测一致 |
| **行政法规（修订沿革）** | `http://xzfg.moj.gov.cn/search2.html?PageIndex={n}` | 实测每条含"历史沿革"多日期，且**比 flk 新**（09-06 vs 08-30） |
| **司法解释** | `POST flk .../list`（叶子码 `320` 高法 / `330` 高检 / `340` 联合）；辅以 `https://www.court.gov.cn/fabu/gengduo/16.html` | flk 覆盖全且带 `sxx`；最高法栏目可交叉核验 |
| **部门规章** | 各部位站点直抓，模板样本：`https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/index_{n}.shtml` | 部委站点实测服务端渲染、**含部令编号与"修订"字样**；gov.cn 国家规章库为 JS 渲染不可程序化 |
| **地方性法规** | 省级人大栏目，样本：`https://www.shrd.gov.cn/shrd/fggb/fggb.html`、`https://www.gdpc.gov.cn/` | 人大是法定发布主体；上海栏目**原文即含"修改/废止"字样** |
| **地方政府规章** | 省级政府文件库，样本：`https://www.gd.gov.cn/zwgk/wjk/qbwj/`、`https://www.beijing.gov.cn/zhengce/zhengcefagui/` | 省政府门户**含文号列**（`粤府函〔2026〕213号`），结构化最好 |
| **新发布（最快探针）** | `https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json` | 静态 JSON、1096 条、实测 T-1 更新，**比 flk 快约 19 天** |
| **全库统计基线** | `GET https://flk.npc.gov.cn/law-search/index/aggregateData` | 各类计数 + 新法速递，零参数 |
| **分类/机关码字典** | `GET https://flk.npc.gov.cn/law-search/search/enumData` | **必须程序化读取**（叶子码会变，勿硬编码） |

**推荐的渠道分工（三路互补）**：
1. **发现新发布**：`ZUIXINZHENGCE.json`（T-1）+ `xzfg.moj.gov.cn`（T-7）+ 各部委/省栏目（T-1~T-3）
2. **判定现行性/修订/废止**：**flk `sxx` 字段**（唯一权威四态）+ 上海人大/北京政府的"修改·废止"标题
3. **编号核验**：部委"部令第N号" + 省政府"粤府函〔年〕号" + flk `bbbs` 稳定 ID

---

## 10. 机器可读附录

```json
[
  {
    "name": "国家法律法规数据库-检索列表",
    "category": "聚合入口",
    "url": "https://flk.npc.gov.cn/search",
    "fetch_kind": "json_api",
    "list_endpoint": "POST https://flk.npc.gov.cn/law-search/search/list",
    "params": "{\"searchRange\":1,\"sxrq\":[],\"gbrq\":[],\"sxx\":[],\"searchType\":2,\"xgzlSearch\":false,\"searchContent\":\"\",\"orderByParam\":{\"order\":\"-1\",\"sort\":\"\"},\"flfgCodeId\":[],\"zdjgCodeId\":[],\"gbrqYear\":[],\"pageNum\":1,\"pageSize\":100}",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "note": "实测 total=30598；sxx 四态已由打包产物枚举确认(1=已废止 2=已修改 3=有效 4=尚未生效)；pageSize=100 可用；flfgCodeId 必须用叶子码(101/201/311 实测返回0)；标题含 <em class='highlight'> 需剥离；存在 sxx=null 脏数据；响应头有 WZWS-RAY(网宿WAF)但未触发验证码；站点另有 captchaImage 端点存在未启用"
  },
  {
    "name": "国家法律法规数据库-详情",
    "category": "聚合入口",
    "url": "https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=ff8081819ff541ea01a07eb41e2709fb",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://flk.npc.gov.cn/law-search/search/flfgDetails",
    "params": "bbbs={列表返回的稳定ID}",
    "answers": ["发布", "修订", "废止", "现行性", "编号核验"],
    "verification": "verified",
    "note": "实测 code=200；字段 bbbs/ossFile/xgwj/lsyg/xgzl/flfg/flxz/zdjgName/gbrq/sxrq/title/sxx/content/xfFlag；lsyg=历史沿革、xfFlag=是否修订，对修订识别最有用"
  },
  {
    "name": "国家法律法规数据库-枚举字典",
    "category": "聚合入口",
    "url": "https://flk.npc.gov.cn/law-search/search/enumData",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://flk.npc.gov.cn/law-search/search/enumData",
    "params": "无(无需登录)",
    "answers": ["编号核验"],
    "verification": "verified",
    "note": "实测 7936 字节；flfgfl 叶子码 100/110/120/130/140/150/155/160/170/180/190/195/200/210/215/220/230/260/270/290/295/300/305/310/320/330/340/350；zdjgfl 机关叶子码(国务院=120 上海=250 浙江=270 广东=350)；建议程序化读取勿硬编码"
  },
  {
    "name": "国家法律法规数据库-首页聚合",
    "category": "聚合入口",
    "url": "https://flk.npc.gov.cn/law-search/index/aggregateData",
    "fetch_kind": "json_api",
    "list_endpoint": "GET https://flk.npc.gov.cn/law-search/index/aggregateData",
    "params": "无",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 code=200；分类计数 法律=302 行政法规=606 监察法规=2 地方法规=15713 司法解释=560 宪法=1；含 xfsd 新法速递(bbbs/title/gbrq/score/flxz)；后端包名 com.ruoyi.law.* 说明基于 RuoYi 框架"
  },
  {
    "name": "中国政府网-最新政策静态JSON",
    "category": "规范性文件",
    "url": "https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json",
    "fetch_kind": "json_static",
    "list_endpoint": "GET https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json",
    "params": "无(全量返回)",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 263929 字节 1096 条 2020-01-05~2026-09-17；字段仅 TITLE/SUB_TITLE/URL/DOCRELPUBTIME；最新一条 2026-09-17(T-1) 比 flk 快约 19 天；无时效性字段，不能单独判定现行性"
  },
  {
    "name": "中国政府网-政策文件库检索",
    "category": "规范性文件",
    "url": "https://www.gov.cn/zhengce/xxgk/",
    "fetch_kind": "html_list",
    "list_endpoint": "https://sousuo.www.gov.cn/sousuo/search.shtml?code=17da70961a7&dataTypeId=107&searchWord=",
    "params": "dataTypeId=107|14, searchWord",
    "answers": [],
    "verification": "broken",
    "note": "列表页 HTTP200/226263字节可抓，但检索不可程序化：sousuo.www.gov.cn/s.htm... 实测404；search.shtml?searchWord=安全生产 实测 HTTP200 但正文为『相关结果：约 0 个 抱歉，没有找到相关结果』；search-gov/data 带 q 返回 totalCount=0(不带 q 曾返回43条)，判为需浏览器会话态"
  },
  {
    "name": "中国政府网-国家规章库",
    "category": "部门规章",
    "url": "https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": ["现行性"],
    "verification": "broken",
    "note": "实测 HTTP200/21161字节，页面自述『包含现行有效部门规章和地方政府规章，与司法部官网同步公布，动态更新』『部门规章数据来源于国务院各部委网站和国务院公报，地方政府规章数据来源于省级政府网站和地方政府公报』；但首屏无任何条目、结果由 JS 渲染，实测未找到可直连 JSON 端点，故不可程序化；其数据源自述指向部委/省政府栏目，抓一手更可靠"
  },
  {
    "name": "国务院公报",
    "category": "行政法规",
    "url": "https://www.gov.cn/gongbao/",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "https://www.gov.cn/gongbao/ 实测 HTTP200 但仅898字节，正文只有『中国政府网_中央人民政府门户网站 点击跳转』=JS跳转壳；https://www.gov.cn/gongbao/2026/ 实测 HTTP403 Forbidden。不建议作为巡检入口"
  },
  {
    "name": "司法部-国家行政法规库(xzfg)",
    "category": "行政法规",
    "url": "http://xzfg.moj.gov.cn/search2.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET http://xzfg.moj.gov.cn/search2.html?PageIndex={n}",
    "params": "PageIndex; 表单字段 title/content/timeliness/publishFileNumber/publishTimeStart/publishTimeEnd/implementDateStart/implementDateEnd/sortField(默认PublishTime)/ascOrDesc(默认desc)",
    "answers": ["发布", "修订", "现行性", "编号核验"],
    "verification": "verified",
    "note": "实测 HTTP200/52537字节『现行有效 606 部』；最新 市场监督管理所条例 2026-09-06公布 比 flk(2026-08-30) 新约7天；每条带历史沿革多日期(如病原微生物实验室生物安全管理条例 2004-11-12/2016-02-06/2018-03-19/2024-12-06/2026-08-08)；PageIndex 分页实测有效；但 title= 关键词检索实测不生效(仍返回606部全量)，只能全量分页遍历；仅 HTTP 无有效 HTTPS"
  },
  {
    "name": "司法部-国家行政法规库入口(实为跳转flk)",
    "category": "行政法规",
    "url": "https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzflk/",
    "fetch_kind": "redirect_js",
    "list_endpoint": "无",
    "params": "无",
    "answers": [],
    "verification": "broken",
    "note": "实测 HTTP200 但仅118字节，响应体为 <SCRIPT>var htm=\"https://flk.npc.gov.cn/\";document.location.href=htm;</SCRIPT> → 司法部官网此入口就是 JS 跳转到 flk，不是独立源；同型 flfggzflty/ 123字节；flfggzxzfg/ 130字节空；推测的 flfggzdfzfgz/ 实测404"
  },
  {
    "name": "司法部-部门规章栏目",
    "category": "部门规章",
    "url": "https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/",
    "fetch_kind": "html_list",
    "list_endpoint": "https://www.moj.gov.cn/pub/sfbgw/flfggz/flfggzbmgz/",
    "params": "未确认",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 HTTP200/41543字节，原文『首页 > 法律法规规章 > 部门规章』『2026-06-05 外国医师来华短期行医暂行管理办法』；分页参数未确认；同级栏目 flfggzbmgz/flfggzdfzwgz/flfggzfgjd/flfggzflk/flfggzflty/flfggzxzfg"
  },
  {
    "name": "最高人民法院-司法解释",
    "category": "司法解释",
    "url": "https://www.court.gov.cn/fabu/gengduo/16.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.court.gov.cn/fabu/gengduo/16.html",
    "params": "栏目ID 16=司法解释(同族 14/15/17/21/22/79/108/662 语义未核对)；详情 /fabu/xiangqing/{数字ID}.html(ID 非线性不连续)",
    "answers": ["发布", "修订", "编号核验"],
    "verification": "verified",
    "note": "实测 HTTP200/16934字节；原文『最高人民法院关于适用《中华人民共和国生态环境法典》时间效力的若干规定 2026-08-06』『…关于修改《…船舶油污损害赔偿纠纷案件若干问题的规定》等九件司法解释的决定 2026-08-06』；详情页含 法释〔2009〕 文号；无统一时效性字段"
  },
  {
    "name": "最高人民检察院-法律法规规范性文件",
    "category": "司法解释",
    "url": "https://www.spp.gov.cn/spp/flfgxwj/",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 /spp/flfgxwj/ 与 /spp/flfgxwj/index.shtml 均 HTTP200 且字节数完全相同(72888)，正文等同站点首页，未出现任何该栏目条目 → 栏目未服务端渲染/占位；建议改用 flk 的 flfgCodeId=[330] 高检司法解释 / [340] 联合发布"
  },
  {
    "name": "司法部-备案审查",
    "category": "司法解释",
    "url": "https://www.moj.gov.cn/",
    "fetch_kind": "unknown",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测司法部首页 HTTP200/98266字节，导航为『法律法规规章 法律 法律条约 行政法规 法规解读 部门规章 地方政府规章 国家行政法规库 政府信息公开』，不存在独立备案审查检索入口；推测路径实测404。旁证：广东人大网首页有『2026年部分地方备案审查工作座谈会…』新闻，说明备案审查属工作动态非可检索法规库，不建议作为巡检渠道"
  },
  {
    "name": "应急管理部-规章(法定主动公开)",
    "category": "部门规章",
    "url": "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/gz11/index_{n}.shtml",
    "params": "index_{n}.shtml (n=1,2,... 实测均200)",
    "answers": ["发布", "修订", "编号核验"],
    "verification": "verified",
    "note": "实测 HTTP200/18045字节；原文『煤矿企业安全生产许可证实施办法 （2026年8月31日应急管理部令第22号公布 自2027年1月1日起施行。）』『煤矿重大事故隐患判定标准 （2020年11月20日应急管理部令第4号公布，2026年5月24日应急管理部令第21号修订。）』= 部令编号+公布日期+施行日期+修订信息齐全；附件为直链 .pdf/.doc/.docx/.wps(如 .../202609/P020260904609285161605.pdf)；实测无 ajax/JSON 端点"
  },
  {
    "name": "应急管理部-法律法规",
    "category": "法律",
    "url": "https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.mem.gov.cn/fw/flfgbz/fg/index.shtml",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "note": "实测 HTTP200/72740字节 标题『法律法规』；注：推测路径 /fw/flfgbz/flfg/ 实测404；/fw/flfgbz/ 仅507字节、/fw/flfgbz/bz/ 仅465字节均为空壳；分页参数未确认，只能兜底抓取"
  },
  {
    "name": "生态环境部-法规标准",
    "category": "部门规章",
    "url": "https://www.mee.gov.cn/ywgz/fgbz/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.mee.gov.cn/ywgz/fgbz/",
    "params": "未确认",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 HTTP200/80593字节；原文『法规标准 法律 行政法规 规章 标准 … 中华人民共和国生态环境法典 2026-03-13』；为法规汇编式栏目，最新条目 2026-03-13 滞后约6个月，不适合做新发布发现，只能兜底"
  },
  {
    "name": "住房和城乡建设部-政策发布",
    "category": "部门规章",
    "url": "https://www.mohurd.gov.cn/gongkai/zhengce/",
    "fetch_kind": "broken",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "首页 https://www.mohurd.gov.cn/ 实测 HTTP200/78949字节可抓；但栏目 /gongkai/zhengce/ 实测 HTTP 403 Forbidden(已实测到反爬/权限拒绝)，不可程序化"
  },
  {
    "name": "国家市场监督管理总局-法规司",
    "category": "部门规章",
    "url": "https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 HTTP200 但仅3589字节，正文只有『法规司 你的位置: 首页 > 政务 > 政府信息公开 > 法定主动公开内容 > 法规司 法规司』，无任何文件条目 = JS 空壳，不可程序化"
  },
  {
    "name": "交通运输部-政策解读",
    "category": "部门规章",
    "url": "https://www.mot.gov.cn/zhengcejiedu/",
    "fetch_kind": "broken",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "首页 https://www.mot.gov.cn/ 实测 HTTP200/92003字节；但推测栏目 /zhengcejiedu/ 实测 HTTP404，未定位到正确规章栏目路径，需人工在站内确认后重测"
  },
  {
    "name": "国家卫生健康委员会",
    "category": "部门规章",
    "url": "https://www.nhc.gov.cn/",
    "fetch_kind": "broken",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 https://www.nhc.gov.cn/ 与 https://www.nhc.gov.cn/fzs/ 均返回 HTTP 412 Precondition Failed，WAF 拒绝无浏览器指纹的直连，不可程序化"
  },
  {
    "name": "工业和信息化部-政策文件",
    "category": "部门规章",
    "url": "https://www.miit.gov.cn/zwgk/zcwj/index.html",
    "fetch_kind": "js_render",
    "list_endpoint": "https://www.miit.gov.cn/api-gateway/jpaas-web-server/frontDocument/list",
    "params": "实测被网关拒绝(webId/channelId/pageNo/pageSize 组合返回 code=601『您访问的URL不合规，请检查』)，正确参数未确认",
    "answers": [],
    "verification": "broken",
    "note": "栏目页实测 HTTP200 但仅2116字节，正文只有标题『政策文件』=JS 空壳；JSON 网关实测返回 success=false,code=601『您访问的URL不合规，请检查』，不可程序化"
  },
  {
    "name": "人力资源和社会保障部",
    "category": "部门规章",
    "url": "https://www.mohrss.gov.cn/",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 HTTP200 但仅986字节，响应体为混淆 JS 反爬脚本，原文含 <script>function a(a){..._0x649a(\"0x4\")...}</script> 与 t+=\"EO_Bot_Ssid=\" → 需执行 JS 生成 EO_Bot_Ssid Cookie，纯 HTTP 直连不可程序化(需无头浏览器)"
  },
  {
    "name": "上海市人大-法规公布",
    "category": "地方性法规",
    "url": "https://www.shrd.gov.cn/shrd/fggb/fggb.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.shrd.gov.cn/shrd/fggb/fggb.html",
    "params": "未确认(页面不显示日期，需靠标题集合差分)",
    "answers": ["发布", "修订", "废止"],
    "verification": "verified",
    "note": "实测 HTTP200/11229字节；原文『法规公布 上海市人民代表大会常务委员会关于修改《上海市环境保护条例》等12件地方性法规的决定』『…关于修改《上海市市民体育健身条例》等4件地方性法规和废止《上海市酒类商品产销管理条例》的决定』= 标题天然含修改/废止，变更发现友好；同域栏目 /shrd/lfdt/lfdt.html(立法动态) /shrd/lfdtej/ /shrd/lfyjzq/；镜像 https://cms.odb.sh.cn/shrd/ 实测200可用；主要短板是无日期字段"
  },
  {
    "name": "上海市司法局",
    "category": "地方性法规",
    "url": "https://sft.sh.gov.cn/",
    "fetch_kind": "broken",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 ERR: The SSL connection could not be established(TLS 握手失败，未取得 HTTP 状态码)；且司法厅本非地方性法规一手来源"
  },
  {
    "name": "上海市人民政府-近期信息公开",
    "category": "地方政府规章",
    "url": "https://www.shanghai.gov.cn/nw12344/index.html",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.shanghai.gov.cn/nw12344/index.html",
    "params": "?tab=2 实测无效(返回体与无参完全一致 28269 字节)",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 HTTP200/28269字节；原文『上海市人民政府关于加强第48届世界技能大赛期间无人机等航空器安全管理的通告 2026-09-17』『上海市市场监督管理局关于印发《上海市撤销虚假企业登记实施办法》的通知 2026-09-15』；最新 T-1；但混合通告/通知/发布会多体裁，入库需按文种过滤"
  },
  {
    "name": "北京市人民政府-政策文件",
    "category": "地方政府规章",
    "url": "https://www.beijing.gov.cn/zhengce/zhengcefagui/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.beijing.gov.cn/zhengce/zhengcefagui/",
    "params": "未确认",
    "answers": ["发布", "废止"],
    "verification": "verified",
    "note": "实测 HTTP200/394586字节(篇幅最大)；原文『北京市文化和旅游局关于废止《…的通知》的通告 2026-09-17』『北京市人民政府办公厅关于印发《北京市村民自建住宅消防安全管理办法》的通知 2026-09-16』= 含废止字样；最新 T-1；条目带『是』字段(语义未确认)"
  },
  {
    "name": "北京市人大",
    "category": "地方性法规",
    "url": "https://www.bjrd.gov.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.bjrd.gov.cn/",
    "params": "未确认",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 HTTP200/66465字节；原文『市人大常委会会议闭幕 表决通过北京市测绘地理信息条例等法规』；以立法新闻为主，未定位到独立结构化『法规公布』栏目(弱于上海人大的 /shrd/fggb/)，只能兜底"
  },
  {
    "name": "广东人大网",
    "category": "地方性法规",
    "url": "https://www.gdpc.gov.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.gdpc.gov.cn/",
    "params": "未确认",
    "answers": ["发布"],
    "verification": "verified",
    "note": "实测 HTTP200/109518字节 标题『广东人大网』；原文『省十四届人大常委会第二十六次会议闭幕』『2026年部分地方备案审查工作座谈会暨备案审查工作培训班在广州举办』；警示：https://www.gzrd.gov.cn/ 实测200但标题为『贵州省人民代表大会常务委员会』=属贵州非广东；https://www.rd.gd.cn/ 实测 SSL 连接失败"
  },
  {
    "name": "广东省人民政府-文件库",
    "category": "地方政府规章",
    "url": "https://www.gd.gov.cn/zwgk/wjk/qbwj/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://www.gd.gov.cn/zwgk/wjk/qbwj/",
    "params": "分类页签 政府文件/全部文件/粤府令/粤府/粤府函/粤府办/粤办函；分页参数未确认",
    "answers": ["发布", "编号核验"],
    "verification": "verified",
    "note": "实测 /zwgk/wjk/ HTTP200/99696字节 与 /zwgk/wjk/qbwj/ HTTP200/62934字节；表格列为 名称/文号/发布日期，原文『广东省人民政府关于湛江市吴川市吴阳镇等5个历史文化名镇名村保护规划的批复 粤府函〔2026〕213号 2026-09-15』= 文号直接成列，编号核验最佳；最新 T-3"
  },
  {
    "name": "浙江省司法厅",
    "category": "地方政府规章",
    "url": "https://sft.zj.gov.cn/",
    "fetch_kind": "html_list",
    "list_endpoint": "GET https://sft.zj.gov.cn/",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "note": "实测 HTTP200/56726字节，但内容为厅务动态(『省司法厅召开律师行业高质量发展座谈会 2026-09-17』)，无法规条文→作为法规渠道不可用；证实司法厅不是地方性法规/规章一手源"
  },
  {
    "name": "浙江省人大",
    "category": "地方性法规",
    "url": "https://www.zjrd.gov.cn/",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 HTTP200/58727字节，标题『中国浙江人大』，但去标签后正文仅为『中国浙江人大 关闭 关闭』= JS 空壳/框架页，无任何条目，不可程序化"
  },
  {
    "name": "浙江省人民政府-省政府文件",
    "category": "地方政府规章",
    "url": "https://www.zj.gov.cn/col/col1229019364/index.html",
    "fetch_kind": "js_render",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "broken",
    "note": "实测 HTTP200 但仅1750字节，去标签后正文仅为『省政府文件』，无任何条目 = JS 空壳，不可程序化"
  },
  {
    "name": "Law-Crawler-RPA-RAG-MCP",
    "category": "工具项目",
    "url": "https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP",
    "fetch_kind": "unknown",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "note": "gh api repos/Yuhamixli/Law-Crawler-RPA-RAG-MCP 实测 EXISTS，stars=32，最近推送 2026-04-28，描述『一个用于爬取中国法律法规并构建智能问答系统的项目』；真实存在且相关，但本次未克隆代码，其实际数据源未核实；属工具非一手发布源"
  },
  {
    "name": "legal-database",
    "category": "工具项目",
    "url": "https://github.com/sublatesublate-design/legal-database",
    "fetch_kind": "unknown",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "unverified",
    "note": "gh api repos/sublatesublate-design/legal-database 实测 EXISTS，stars=5，description 为空；GitHub 上同名仓库众多(cc-archive/legaldb 65★、berkmancenter/lumendatabase 168★ 等均非中国法规)，业主所指不明确→名称有歧义，不构成可用渠道线索"
  },
  {
    "name": "china-law-search",
    "category": "工具项目",
    "url": "https://github.com/search?q=china-law-search",
    "fetch_kind": "unknown",
    "list_endpoint": "无",
    "params": "无",
    "answers": [],
    "verification": "broken",
    "note": "gh search repos 'china-law-search' 实测无同名仓库命中(仅返回 chinese-law-mcp/Lawdown/ChineseLawsSearch 等近似名)；仅搜到第三方技能市场页面 skills.sh/nigo81/nigo-skills/china-law-search 而非仓库→未找到，疑似不存在或名称有误"
  },
  {
    "name": "GovPing",
    "category": "工具项目",
    "url": "https://github.com/search?q=GovPing",
    "fetch_kind": "unknown",
    "list_endpoint": "无",
    "params": "无",
    "answers": [],
    "verification": "broken",
    "note": "gh search repos 'GovPing'/'govping' 实测零命中，仅返回 govp-protocol/govp-js、gemacode/govp-for-woocommerce 等 GOVP 开源协议(电商/协议验证领域，与法规巡检无关)→未找到，疑似不存在或名称有误；GovPing 与 GOVP 仅差两字母易混淆"
  },
  {
    "name": "RegRadar",
    "category": "工具项目",
    "url": "https://github.com/kingabzpro/RegRadar",
    "fetch_kind": "unknown",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "note": "gh api repos/kingabzpro/RegRadar 实测 EXISTS stars=2『RegRadar watches the worlds regulators so you dont have to.』；RahimAbbas55/RegRadar 实测 EXISTS 但为英国 FCA Handbook RAG；gh search 另见 Shivay00001/regradar(印度)、sidnov6/regradar(EU EUR-Lex)→名称被多个互不相关项目复用，无一针对中国法规"
  },
  {
    "name": "at-ris-mcp",
    "category": "工具项目",
    "url": "https://github.com/paragraflabs/at-ris-mcp",
    "fetch_kind": "unknown",
    "list_endpoint": "未确认",
    "params": "未确认",
    "answers": [],
    "verification": "verified",
    "note": "gh search repos 'at-ris-mcp' 实测 paragraflabs/at-ris-mcp EXISTS stars=1，描述『MCP server & Python client for Austria's legal information system (RIS): federal & state law, case law, gazettes, change monitoring』→ RIS=奥地利 Rechtsinformationssystem，at-=Austria；功能(change monitoring)看似贴切但对中国法规零覆盖，不可采用"
  }
]
```

---

*报告生成时间: 2026-09-18 · 全部链接为当日实测 · 未改动仓库其它文件*
