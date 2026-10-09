# 政务数据采集 · 经验与可复用资源

> **面向**：接手政府网站数据采集的人。这份文档的目标是让你**不用从零摸索** ——
> 中间件指纹、踩过的坑、可复用的工具，全在这里。
>
> **生成日期**：2026-10-09
> **基线**：**264,200 条** / **31 个省级行政区 + 国家级部委** / **569 个来源** / **320 个适配器**
>
> ⚠ 本文所有数字均由工具现算，不手写。复算命令见 §6。

---

## 一、最重要的一句话

**政府网站高度复用同一套中间件（CMS / 门户框架）。找到一个接口 = 找到一片站点。**

全国 31 个省级行政区、333 个地级行政区，实际用到的中间件产品**不超过 20 种**。
所以正确的工作顺序是：

1. **先认中间件**（看 URL 特征、看前端框架、看响应结构）
2. **套已知指纹**（80% 的站能直接命中）
3. 命中不了再从头挖

**反面教材**：本项目的第一个版本是"一个省一个省地啃门户首页"，效率极低。
改成"先认中间件"之后，同一个打法在四川、山东、江苏、浙江、甘肃直接复用。

---

## 二、中间件指纹库（核心资产）

### 2.1 接口型（有 JSON/JS 接口，最优先）

| 中间件 | 识别特征 | 列表接口 | 明细接口 | 备注 |
|---|---|---|---|---|
| **IGI**（用得最多） | URL 含 `/IGI/` | `{BASE}/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId=&order=1&appId=&pageIndex=&pageSize=20` | `method=viewGovmsgbox&metadataId=` | 答复在 `datas.REPLYS[].REPLYHTMLCONTENT`；**枚举 siteId 范围必须 ≥1..300** |
| **jact**（万户 hanweb） | URL 含 `/jact/front/` | `POST/GET /jact/front/dataproxy_mailpublist.do?startrecord=&endrecord=&perpage=&groupSize=3&sysid=` | `mailpubdetail.do?transactId=&sysid=` | **分页参数在 query string**；**标签用词因站而异（已见 4 套）** |
| **jpaas-jact 网关** | URL 含 `/api-gateway/jpaas-jact-web-server/` | `GET .../front/find-mail-pub-list?pageNum=&pageSize=&platformUid=` | `.../front/mail-pub-detail?iid=` | **⚠ 绝对不要传 `govOpen`**（济南 6654→250、烟台 101,152→0） |
| **EWB**（河北/徐州政务 webBuilder） | 接口含 `frontAppNotNeedLoginAction` | `POST .../getLetterListByCondition`，form 单字段 `params=<JSON 串>` + `Authorization: Bearer <token>` | `.../getLetterDetail` | **⚠ `pageIndex` 语义因站而异**（见 §3.6） |
| **Hanweb / 万户站群** | URL 含 `/u/search/` | `POST /u/search/ajaxlist?channel_id=` | 视站而定 | **0 基页码**，须 Referer |
| **龙讯 CMS** | URL 含 `/site/label/` | `GET /site/label/8888?labelName=...&pageIndex=&pageSize=&siteId=&columnId=&action=singleList&isJson=true` | 列表可能自带答复 | **⚠ 必须先 GET 栏目 index 页拿 cookie**，否则报「标签ID不存在」 |
| **JeecgBoot**（辽宁 8890 等） | 前端有 `_app.config.js`，含 `VITE_GLOB_API_URL` | 因站而异（辽宁：`/common/knowledge/page`、`/common/page_qa`） | 辽宁：`/common/get_qa_byId?id=` | **⚠ 业务代码在懒加载 chunk 里，入口 chunk 找不到 ≠ 没有** |
| **数融 CMS**（四川多市） | URL 含 `/api/mail` | `POST /api/mail/...`（`openMailList` / `list`，路径因站而异） | 有 | **⚠ 字段名是「回复单位」不是「答复单位」** |
| **通信平台 api-mailbox**（四川多市） | URL 含 `/communication/api-mailbox/` | `frontMail/mailList` | 有 | **签名因站而异**：绵阳要 AES-ECB、内江要签名、阿坝**不要** |
| **WCM「西部数通」站群** | URL 含 `urltype=tree.TreeTempUrl&wbtreeid=` | `GET ...?wbtreeid=&pageNumber=` | 有 | **⚠ 页面 JS 的翻页函数是 POST，但照抄会返回「暂无数据」⇒ 用 GET** |
| **ThinkPHP 站群** | 有 `js/publicity.js` / `js/letters.js` | 翻 JS 拿真实 API | 有 | 页面里的 `index.php?m=index` 会 403，**真 m 值在 js 里** |
| **enorth**（天津政民零距离） | `zw.enorth.com.cn/gov_open/` | `GET question/zero/list9a.jsp?deptId=&curpage=&rows=`（gb2312） | `GET /gov_open/<id>.html` | 静态 HTML、无需 cookie/Referer；**列表不含答复** |
| **RuoYi**（科技部等） | 前端有 `/prod-api/` 前缀 | 因站而异 | 有 | **⚠ 不能假设它真分页**（见 §3.7） |
| **新华伪数据源** | `ds_xxxxx.json` | `GET .../ds_xxxxx.json` | 同文件内 | 静态 JSON |
| **LetterBox / appeal**（四川泸州/德阳） | 服务端渲染 HTML | 列表页 `?page=N` | 静态明细页 | **纯 HTML 也是可采形态，别因为"不是 JSON"就放弃** |

### 2.2 防护型（会拦你，要知道怎么绕）

| 防护 | 表现 | 绕法 |
|---|---|---|
| **瑞数动态防护（RiverSecurity）** | HTTP **412**，body 内联 `$_ts.cd` / `$_ss.cd` 混淆 JS，响应带 `Set-Cookie: azSs...` | ★ **只拦 HTML 页面路径，不拦 JSON 接口路径** —— 湖北门户根路径 412，但 `/IGI/` 返回 200（靠这条拿下 1 万条）。**但甘肃是反例：整域 412，连 `/IGI/` 也 412 ⇒ 逐站实测。** 另：**找同一部门的业务子站/非标端口**（广元信箱在 `qgj.cngy.gov.cn:9050`，无 WAF） |
| **IP 级反爬（形态一）** | `HTTP 200` + 273 字节空页，正文「系统检测到您的ip存在恶意请求…被拦截」 | 识别特征串后**立即停止**，冷却后重跑累积 |
| **IP 级反爬（形态二）** | `HTTP 200` + 图形验证码页（含 `createvisitcode`） | 同上 |
| **IP 级 403** | 短时约 30 个请求即 403（整站含 JSON） | `PAUSE ≥ 3s`、每批 ≤500 条、批间歇 ≥30 分钟 |
| **登录墙** | 302 跳 login / SPA 登录页 | **放弃**（拿不到） |
| **聊天机器人** | 答复现生成（调 `chatapi.xxx`） | **放弃**（非固定官方答复，不符合判据） |

### 2.3 省级「统一咨询投诉平台」（绕市级 WAF 的后门）

**这是本项目最有价值的发现之一。**

很多省的政务服务平台聚合了全省地市的咨询投诉，**按行政区划码过滤**，
可以**一次覆盖全省所有地市**，不用逐个啃门户。

| 省 | 平台 | 接口 | 规模 |
|---|---|---|---|
| **四川** | `www.sczwfw.gov.cn/cns-bmfw-websdt/` | `POST /rest/cnspublic/scwebsitecaseinfoaction/getInteractCaseInfoListByCondition`，body `{pageSize, currentPageIndex, rqstType("10"咨询/"15"建议/"20"投诉), areaCode(12位), iszwfw:"1"}`；明细 `getCaseInfoDeatil` | 全省 21 市 **50,324** |
| **辽宁** | `www.lnzwfw.gov.cn/8890/`（12345民心智慧听） | `/server-api/common/knowledge/page`、`/common/page_qa` + `/common/get_qa_byId?id=` | **21,748** |

**★ 关键经验：四川那个路径不是全国统一产品**（`cns-bmfw-websdt` 里的 `sc` 是四川简称，
浙江/江苏/山东/河南试同路径全部 404）。**各省要各自找，但「这个形态存在」是普遍的。**

**★ 加密接口先试「去掉加密头」**：四川平台前端默认 SM2 加密请求 + AES 解密响应，
但**请求不带 `encrypt` 头时服务端直接回明文 JSON** —— 省掉整套国密实现。

---

## 三、八条硬规则（全部踩出来的）

> 这八条有一个共同点：**都是「不报错、但结果不对」**。比崩溃危险得多。

### 3.1 采集后立刻 commit 数据文件

**事故**：绵阳 3,000 + 内江 3,000 条被重采脚本删除，而 git 里只有抽验阶段的 3 条
（正式采集从未 commit）⇒ **净损失约 6,000 条**。

⇒ **git 是唯一可靠的备份，`/tmp` 不是。破坏性重采之前必须先 commit。**

### 3.2 验收看「数据行数」，不是「适配器抽验通过」

同一失败模式出现过**四种形态**：

1. 适配器建好、抽验通过、已登记，但**从没启动采集**（17 个市 / 3 个大源）
2. 采集任务**已启动但被中断没跑完**（10 个市只剩抽验的 3 条）
3. 文件存在，但里面是**抽验残留**
4. 任务显示"完成"，但**落盘 0 条**（异常冒泡，见 3.3）

⇒ **唯一可信的判据是数据文件里的行数。** 用 `audit-coverage.py --empty` 核查。

### 3.3 适配器绝不能把异常冒泡出去

**事故**：`nat-tax` 跑 **63 分钟**后一条明细请求 `ReadTimeout`，异常冒泡到 `harvest.py`，
后者 `except` 后丢弃 ⇒ **整站零产出**（连续 3 批如此）。

**修法**：`harvest.py` 只在跑完时落盘 ⇒ 适配器必须
**「单条失败跳过 + 连续失败熔断 + 返回已收部分」**。

```python
try:
    d = fetch(DETAIL_API, params={"id": code})
except Exception as e:
    consec_fail += 1
    if consec_fail >= MAX_CONSEC_FAIL:      # 默认 8
        print(f"连续 {consec_fail} 次失败 ⇒ 熔断，返回已收 {len(out)} 条")
        return out                          # ★ 返回已收部分，不抛
    time.sleep(PAUSE * 3)
    continue
consec_fail = 0
```

**效果验证**：修复后税务总局 **10 个批次每批稳定产出约 2,000 条**（修复前零产出）。

### 3.4 「重采」不等于「覆盖」

`harvest.py` 的去重是 `(source, id)` 比对，**只追加、不更新**：

```python
fresh = [r for r in rows if (r["source"], str(r["id"])) not in done]
```

⇒ 重跑一遍时所有记录都命中已有 id ⇒ **新增 0 条、旧记录原样保留**。
日志显示「收 3000 条，新增 0 条」——**看起来正常，实际什么都没更新**。

**安全的「删除 + 重采」流程**：
1. 先 `git add` + commit 现有数据
2. **验证适配器修复真的生效**（直接调用适配器看目标字段有没有值，**不要只信 commit message**）
3. 删除数据文件
4. 重采

### 3.5 同一个站（同 source）只能有一路在采

`harvest.py` 的去重是**开跑时一次性读文件**建快照，之后只按快照过滤
⇒ **两路进程并发采同一个站时，双方读到同一初始状态，各写一份**。

**实测**：浙江金华被两路并发写 ⇒ **6,350 行里只有 3,351 唯一 id**；
全库扫描发现 **13 个来源、8,284 行重复**（最严重的 `gd-hr` 同一 id 被写了 **12 次**）。

⇒ 工具：`audit-coverage.py --dups` 检测、`dedup-data.py` 清理。

### 3.6 分页参数语义**必须逐站实测**（同族中间件也不行）

| 站 | `pageIndex` 语义 | 传错的后果 |
|---|---|---|
| 河北 `heb-szj`（EWB） | **记录偏移量**（`=0`→第0-9条，`=1`→第1-10条） | 传页码 ⇒ 每页只滑 1 条，1043 只收 **114**（漏 89%） |
| 江苏 `js-xuzhou`（EWB） | **0 基页码**（`offset=pageIndex×pageSize`） | 传 `page*10` ⇒ 每轮跳 10 页，1430 只收 **150**（漏 90%） |

**两者现象完全相同（数据严重偏少）、修法相反。**

**诊断法**：试 `pageIndex=0/1/2`，看返回的是**相邻页**还是**滑动窗口**。
**现象特征**：日志「每页 N 条、**新增 1 条**」或「新增恒定」⇒ 参数名或语义错了。

**其他已知参数名**：无锡 `page/size`、苏州 `currpage/pagesize`、宿迁 `currentPage`、
攀枝花 `pageIndex`（不是 `pageNum`）。

### 3.7 枚举 id 的范围必须给够，且必须实测列表接口

- **范围**：重庆因只枚举 `siteId 1..60` 被误判「无问答」，实际 **75 site / 32,580 条**（siteId 全在 150~300+）。
  山西（46 站 / 84,381）、广西（208 站 / 34,938）同样是「宽范围枚举」才发现的。
- **实测**：贵州门户 11 个 siteId 里 **6 个列表接口 404**，只有 5 个有效。
  **枚举出的 `totalResults` 是乐观值，必须实测列表接口。**
- **RuoYi 风格**：科技部 `commonQuestionlist` **忽略 `pageNum`**，任何页都返回同一批 15 条
  ⇒ 原 `while` 永不终止、卡死 15 分钟。**必须有 total 边界或「同页无新增即停」护栏。**

### 3.8 否定性结论必须用数据证伪

**事故**：worker 判定「宿迁不是 bug，41 条是上一轮中断残留」—— **错的**。
真因是**去重字段取错**：列表行 `it[1]` 是**部门 id**（全站只有 **41 个唯一值**），
`it[2]` 才是信件 guid（1,373 唯一）⇒ 旧版按部门去重，1373 行折叠成 41 行。

⇒ **「接口正常」≠「数据完整」。** 「不是 bug / 残留而已 / 接口正常」这类否定性结论，
   **必须用数据证伪，不能靠推理下结论。**

---

## 四、十二条侦察技巧

1. **★★ 不要从页面 HTML 猜参数名，去扒前端 bundle 里的 axios 调用点。**
   定位法：搜接口常量 + `Ms(RB,{…})` 调用点，或页内 `<script>` 里搜 `$.ajax` 的 `data:{}`。
2. **★★ SPA 先找 `baseURL`**（如南京 Vue SPA 的 `/prod-api/` 前缀）。
   ⚠ **同域路径返回 200 但 `content-type` 是 HTML = 假阳性** ⇒ 必须核 `content-type: application/json`。
3. **★★ JeecgBoot 懒加载：入口 chunk 找不到 API ≠ 没有。**
   要从 `basicplantform-online-vendor-*.js` 里挖**路由表**，再取业务 chunk。
4. **★★ 真实域名 ≠ 直觉域名** —— 自贡是 `www.zg.gov.cn`（不是 `www.zigong.gov.cn`）、
   绵阳是 `www.my.gov.cn`。**新站第一件事：试短域名。**
5. **★★ 判定站点归属必须核首页内容，不能只看域名缩写。**
   `www.gy.gov.cn` 是**安徽涡阳县**，不是四川广元（广元真域是 `www.cngy.gov.cn`）。
   ⚠ **这是数据完整性风险** —— 照域名缩写建适配器会把安徽涡阳的留言当成四川广元的，
   且 `source` 前缀是 `sc-guangyuan`，**后续按省筛选会静默算错**。
6. **★★ 200 + 结构正确 ≠ 有数据** —— 攀枝花「市长信箱」接口语法全对、返回 200，
   但**恒返回 `{"topics":[]}`**；真数据在另一个接口。**必须验证 `rows` 非空。**
7. **互动入口藏在 `href` 而非可见文字** —— 德阳首页可见文本**零**「互动/信箱」字样，
   但页脚 `href` 里有。⇒ **扫 `href` 全集，别只看 `<a>` 文本。**
8. **门户首页扫不到 ≠ 站死，要扫独立子域** —— 宜宾 12345 在
   `12345.zwfwhfgjjfzj.yibin.gov.cn`（服务端渲染 233 页），门户上完全无入口。
9. **https 失败 ≠ 站死，一定试 http** —— 山东 5 个市 https 全报 SSL 错、http 全通。
10. **服务端渲染 HTML 也是可采形态** —— 泸州（LetterBox）/德阳（appeal）纯 HTML，别放弃。
11. **接口签名要复刻** —— 绵阳 `sign=AES-ECB-Pkcs7(timestamp+key)`，
    key 在 `hd_common.js` 的 `getKeyVal/Encrypt`；请求体按名排序拼 `name+JSON.stringify(value)`。
12. **响应头无 charset + 声明 utf-8 ⇒ 库会误判 ISO-8859-1**（巴中）⇒ 必须
    `r.content.decode("utf-8")`，否则全乱码导致「页面无内容」**假阴性**（把好站判成死站）。

---

## 五、数据格式

统一记录格式（**`answer` 必须是答复原文，不清洗不摘要**）：

```json
{
  "source":   "gd-amr",              // 来源 key（用于判省、去重）
  "id":       "1234567",             // 站内 id；站内无稳定 id 时用内容指纹
  "url":      "https://...",         // 明细页
  "question": "问题原文",
  "answer":   "答复原文",
  "asked_at": "2026-05-13 16:33:23",
  "answered_at": "2026-05-14 09:12:00",
  "dept":     "广东省市场监督管理局",   // 答复单位
  "channel":  "互动交流·留言选登",
  "extra":    { "msg_type": "咨询", "platform": "IGI", "province": "...", "city": "...", "area": "..." }
}
```

**字段覆盖率**（全库实测）：`answer` 100% / `channel` 100% / `question` 99.8% /
`asked_at` 97.9% / `answered_at` 95.4% / `url` 92.0% / `dept` 89.9%

**可筛选维度**：

| 维度 | 覆盖率 | 机制 |
|---|---|---|
| **地区（省）** | **100%** | `source` 前缀映射 + `extra.pForumNames` + `extra.fid_label` |
| 来源站 | 100% | `source` |
| **问题类型** | ~19% | `extra.msg_type`（咨询/投诉/建议/表扬/求助…） |
| 答复部门 | 89.9% | `dept`（子串匹配，可当二级地区筛） |
| 时间窗 | 97.9% | `asked_at` |
| 关键词 | — | question + answer 全文 |

---

## 六、工具链（全部可复用）

| 工具 | 用途 |
|---|---|
| `harvest.py` | 采集主程序。`--site <key> --limit N`；`--list` 看站点；`--dry-run` 试跑 |
| **`recon/audit-coverage.py`** | ★ **体检五连**（见下） |
| `recon/dedup-data.py` | 清理重复 `(source,id)` 行（只删精确重复，同 id 不同内容保留并告警） |
| `recon/igi-chunked-harvest.py` | **IGI 分片驱动** —— 逐 siteId 落盘，中断只损失当前 siteId（含重试+冷却+熔断） |
| `query.py` | 语料筛选/导出（`--province` / `--type` / `--dept` / `--kw` / `--out` / `--csv`） |
| `recon/coverage-matrix.py` | 省级 × 来源矩阵 |
| `measure-locate-rate.py` | 量「答复点名依据率」（判断能否当考卷） |
| `recon/waf-igi-probe.py` | 探「34 省 × 4 条路径」的 IGI 可达性 |
| `recon/igi-siteid-scan-*.json` | 各省 IGI siteId 枚举结果（山西/广西/宁夏） |

### 体检五连（每次汇总前跑）

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/audit-coverage.py            # ① 条数（按 level 分组）
$P tools/gov-qa/recon/audit-coverage.py --empty    # ② 建好没采（零数据适配器）
$P tools/gov-qa/recon/audit-coverage.py --fields   # ③ 整列全空（静默字段缺陷）
$P tools/gov-qa/recon/audit-coverage.py --answers  # ④ 答复截断（短答复是长答复的前缀）
$P tools/gov-qa/recon/audit-coverage.py --dups     # ⑤ 重复 id（并发写）
```

### 关于「答复截断」检测的判据迭代（值得借鉴）

| 判据 | 结果 |
|---|---|
| ①「短答复」 | **误报太多** —— 吉林教育厅「您好，网上无法开具服刑证明。」是**真实简短答复** |
| ②「重复短答复」 | **仍误报** —— 「感谢您对市长信箱工作的关注！」×72 是**固定套话** |
| ③ **「短答复是同来源长答复的前缀」** | **40 个误报 → 5 个候选** ✓ |

⇒ **做数据质检工具，误报比漏报更致命** —— 误报多了就没人看了。

---

## 七、判死清单（避免重复劳动）

**这些站已核实拿不到，不用再试**（均有 URL + 状态码证据）：

| 站点 | 原因 |
|---|---|
| **国家信访局** `wsxf.gjxfj.gov.cn` | 纯表单，无公开答复 |
| **中国政府网「我向总理说句话」** | 需登录 |
| 自然资源部 `box.mnr.gov.cn` | 纯表单，需「编号+手机号」查个人留言 |
| 司法部 `chinalaw.gov.cn` | 登录墙 |
| 市场监管总局 | 登录墙 + 聊天机器人 |
| 国家统计局 | 聊天机器人（答复现生成） |
| 国家药监局 | 无公开问答列表 |
| 中央纪委 12388 | 举报通道，无答复文本 |
| **天津 IGI** | **14 万条但 `REPLYS` 恒为 null、明细 500「未找到该信件」⇒ 只有问题没答复** |
| 海南 / 江西 / 黑龙江 IGI | 平台在，但问答栏目未挂载（宽范围枚举 1..300 均为 0 site） |
| 淮安市 | 门户无政民互动/信箱入口 |
| 常州（明细） | 明细页 403 瑞数 WAF（列表可采、答复拿不到） |
| 成都 `www.chengdu.gov.cn` | 全站 412（已用四川省级平台绕过） |

⚠ **「条数大」不等于「可用」** —— 判一个源可用前必须验证**答复正文真能取到**，
不能只看 `totalResults`（天津 IGI 就是 14 万条的陷阱）。

---

## 八、文件地图

```
tools/gov-qa/
├── PLAYBOOK.md              ← 本文档（经验与可复用资源）
├── HANDOVER.md              ← 接手须知 + 可执行命令
├── README.md                ← 模块说明
├── SITE-REGISTRY.md         ← 逐站台账（79KB，最全）
├── NAT-ENTRIES.md           ← 国家部委逐条核验台账
├── MINISTRY-ENTRIES.md      ← 业主给的部委线索清单（另一对话维护）
├── WRITE-SCOPE.md           ← ⚠ 多对话共写的分工边界（先读）
├── REUSE-FOR-ANNOUNCEMENTS.md ← 给「政府公告采集侧」的可复用资产索引
├── harvest.py               ← 采集主程序
├── query.py                 ← 语料筛选/导出
├── adapters/                ← 320 个适配器
│   ├── _igi_common.py       ← IGI 基座
│   ├── _jact_common.py      ← jact 基座（含 LABEL_ALIASES 标签别名归一）
│   ├── _sd_jact_gw.py       ← jpaas-jact 网关基座
│   ├── _sczwfw_common.py    ← 四川省级平台基座
│   └── <前缀>_<站点>.py      ← 各省/市适配器
├── data/                    ← 442 个 .jsonl（264,200 条）
└── recon/                   ← 侦察证据 + 工具
    ├── *-hunt.txt           ← 逐省原始实测报告
    ├── igi-siteid-*.json    ← 各省 IGI siteId 枚举结果
    └── *.sh                 ← 采集脚本
```

**数据在 `data/`，一行一条 JSON。`source` 字段是主键的一半，`id` 是另一半。**

---

## 九、效率数据（给后来者一个预期）

| 项 | 实测 |
|---|---|
| 单条耗时 | **1.6–2.3 秒**（逐条抓明细）；列表自带答复的源快得多 |
| `harvest.py` 落盘时机 | **跑完才写**（第 127 行收全量、第 144 行才写）⇒ **中断即零产出** |
| 单源建议上限 | **2 万条**（边际价值在多样性，不在体量） |
| 每市建议上限 | 3,000 条（需逐条明细）／8,000 条（列表自带答复） |
| 超 2 小时的源 | **必须分块**（IGI 用 `igi-chunked-harvest.py`；其它加 `page_from` 参数） |

---

## 十、最后：三条元规则

1. **不要猜，要实测。** 参数名、语义、范围、编码、是否需要 cookie —— 全部实测。
   本项目的每一个大坑，根因都是「按常识推断」而不是「按数据验证」。
2. **不要信「看起来正常」。** 条数正常、字段非空、状态码 200 —— 都可能藏着
   截断、重复、空值、折叠。**只有对比（列表总数 vs 落盘数、字段分布、id 唯一性）才能发现。**
3. **把踩过的坑固化成规则和工具。** 本项目的八条规则 + 五连体检，
   价值高于任何一批具体数据 —— 数据可以重采，规则能复用。
