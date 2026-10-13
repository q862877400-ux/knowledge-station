# 安徽省 16 个零记录市 —— 侦察线索（2026-10-10）

> 归属：Lead 的 M4 侦察。**只读探针**，未落库（除已打通的铜陵）。

## 为什么值得看（推翻一条被误读的负面结论）

`SITE-REGISTRY.md` 里对安徽的负面结论是：

> **负面（同批，别再试）**：云南 8 市、福建 7 市、新疆 4 市、河南 10 市、**安徽 7 市**、
> 河北 9 市、湖南 4 市、辽宁 3 市 —— **全部 NO/BLOCK，零命中**。
> ⇒ **IGI 不是全国通用平台，分布有明显地域性。**

**那条只证明这些市没有 IGI**，**不证明没有别的平台**。
河南就是靠这个判断翻出 **5 个可采市**（商丘/安阳/焦作/周口/开封）。

## 实测：安徽 14 个市的门户互动栏目

| 市 | 互动栏目 | 判定 |
|---|---|---|
| **铜陵市** | **`/tlsrmzf/hdjl/pc/list.html`**（领导信箱 + 12345）| ✅ **已打通**（`tl-hdjl`，2,604 条）|
| **池州市** | **互动 + 留言选登 `/InFeedback/showList/2/page_1.html`** | ✅ **已打通**（`cz-hdjl`，126 条）|
| **亳州市** | **`/InFeedback/showList/1/page_1.html`**（同族 CMS）| ✅ **已打通**（`bz-hdjl`，162 条）|
| 六安市 | 互动交流 `/hdjl/index.html` + 市长信箱 | 候选 |
| 安庆市 | 互动交流 `/zmhd/index.html` + 信件选登 | 候选 |
| 宿州市 | 政民互动 + 书记/市长/部门信箱 | 候选 |
| 淮北市 | 互动交流 + 市长信箱 + 12345热线 | 候选 |
| 淮南市 | 政民互动 `/zmhd/index.html` + 市长信箱 | 候选 |
| 滁州市 | 政民互动 + 回复选登 + 12345热线 | 候选 |
| 芜湖市 | 政民互动 + 信件选登 `/zmhd/12345zfztc/` | 候选 |
| 蚌埠市 | 互动交流 + 信件选登 `/hdjl/zmztc/` | 候选 |
| **宣城市** | `/InteractNew/` + `/InFeedback/showList/2/` | ⚠ 首页登录页，**但 `/InFeedback/` 值得单独试** |

⇒ **13/14 有可定位的互动栏目**，其中 **3 个已打通**（铜陵 2,604 + 池州 126 + 亳州 162）。

## ★★★ 最重要的一条：**"首页是登录页" ≠ 这个入口不可采**

**亳州**原本被我标成「⚠ 首页即登录页」、差点跳过。本轮实测：

- 首页正文**确实**含「账号登录/获取验证码」（那是**页头的用户入口**）
- 但 **`/InFeedback/showList/1/page_1.html` 完全公开** —— `total=163`、答复 900+ 字

⇒ **纪律：判"登录页"要看目标入口，不能只看首页。**
**方法**：不靠"首页判定"，而是**直接试那个具体入口**。

⚠ **同一纪律也适用于宣城**（上一轮我标它「登录页」）——
它也有 `/InFeedback/showList/2/`，**下一轮必须直接试**。

## ★★ 池州这条线的经验：**服务端渲染优先**

池州/亳州的 `/InFeedback/showList/` 是**服务端渲染**：
**不用挖 JS 接口、不用 CSRF token、不用管配置对象** —— 抓页面解析即可。
**成本远低于铜陵/开封那种"壳 + JS 接口"。**

## ★ 同族 CMS 的复用价值

`/InFeedback/showList/<栏目>/page_N.html` 在**池州与亳州都通**
（池州栏目 2 = 留言选登、亳州栏目 1 = 信件选登）。
⇒ 若更多市用这套 CMS，**一次写好、多处复用**。

**但两市的详情结构不同**：池州是 `message_con` 块（留言/回复），
亳州是**表格式**（`u-tit` 字段名 + 紧邻值格）⇒ **适配器不能直接照抄，但探测方法一样。**

## ★ 铜陵与开封是**同一套平台，但四处都不同**（最重要的经验）

| | 开封 | 铜陵 |
|---|---|---|
| 列表接口 | `/uapi/mail/list`（**带 `u`**）| `/api/mail/list`（**不带 `u`**）|
| 配置对象 | `defaultConfig.userIdObj` | **`window.useObj`** |
| 列表 `siteId` 参数 | 传 **`qdId`** | 传 **`useObj.siteId`**（铜陵**没有 `qdId`**）|
| `publicationFlag` | **必须 1** | **不需要** |

⇒ **不能因为"平台一样"就照抄适配器。** 四处全部要**从目标站自己的
`config.js` / `zmhd.js` 抄**。

## 给下一轮

1. **优先试 `池州 / 芜湖 / 蚌埠`** —— 它们的路径（`/InFeedback/showList/`、
   `/zmhd/12345zfztc/`、`/hdjl/zmztc/`）看着像**服务端渲染列表**，
   成本最低（不用挖 JS 接口）。
2. **`六安 / 安庆 / 宿州 / 淮北 / 淮南 / 滁州`**：先抓首页引用的 JS 找接口。
3. **亳州 / 宣城**：首页是登录页 ⇒ 需要另找公开入口，**别在登录页上花时间**。
4. **许昌（河南）**：本机 ConnectTimeout，未验。

## 诚实边界

- 本页是**首页链接侦察**，**未逐个验证答复正文非空**
  ⇒ 按本模块铁律第 6 条，**没取到一条明细确认答复非空之前，不许写适配器**。
- 亳州/宣城的"登录页"判定依据是**首页正文含「账号登录/获取验证码/立即注册」**；
  **不排除**它们有别的公开入口。
- 只有 **14 个市**在 `city-domains-all.json` 里（安徽共 16 个地级市）⇒
  **2 个市域名未登记**，未验。

---

# ★★ 2026-10-13 第 8 轮补记：**还有 6 个市用同一套 `/site/label/8888` CMS**

芜湖（`wh-hdjl`）打通后，拿 `/site/label/8888` 当指纹扫了其余 10 个市 ——
**6 个命中**，这是「找到一个接口 = 找到一片站点」的又一次实证。

| 市 | 命中路径 | 该站自己的 `labelName` |
|---|---|---|
| **马鞍山** | `/hdjl/index.html` | `interviewInfoListByMonth` / `keyWordsHeatRank` |
| **淮北** | `/hdjl/index.html` | `interviewInfoList` / `publicInfoList` |
| **安庆** | `/zmhd/index.html` | **`messageBoardPageListFrom12345`** |
| **六安** | `/hdjl/index.html` | `collectInfoList` / `docList` / `mayorHotLineCount` / `surveyList` |
| **滁州** | `/zmhd/index.html` | `collectInfoList` / `keyWordsHeatRank` |
| **淮南** | `/zmhd/index.html` | `collectInfoList` / `mayorHotLineHfxdPageList` / `messageBoardTjByTimeType` |

**未命中**（探过 6 个路径）：合肥 / 黄山 / 宿州 / 宣城 / 阜阳。

## 安庆：**列表可采，明细不可达 ⇒ 判死（待复验）**

安庆的 label 叫 `messageBoardPageListFrom12345`（芜湖是 `messageBoardPageList`，**只差后缀**），
调用形态：

```
GET /site/label/8888?labelName=messageBoardPageListFrom12345&pageSize=9&queryType=0
    &isDate=4&isHit=true&length=25&dealStatus=1&dateFormat=yyyy-MM-dd
    &action=singleList&file=/c1/anqing/12345test0530/messageBoardInfoList_aq_12345new
    &fromArea=zmhdMainPage
```

**列表确实能拿到**（HTTP 200，3674 B），条目形如：

```html
<li>
  <div class="p1">26092520080011</div>                                  <!-- 信件编号 -->
  <div class="p2"><a href="/site/tpl/2000001371?id=28318412" title="…">…</a></div>
  <div class="p3">2026-09-29</div>                                      <!-- 日期 -->
  <div class="p4"><span class="responseYes">[已办结]</span></div>
</li>
```

**但明细 `/site/tpl/2000001371` 一律 HTTP 521**（Cloudflare「Web Server Is Down」）：

| 请求 | 结果 |
|---|---|
| `https://…/site/tpl/2000001371?id=28318412` | **521** |
| `https://…/site/tpl/2000001371?id=28307531`（换 id） | **521** |
| `http://…/site/tpl/2000001371?id=28307531`（换协议） | **521** |
| `https://…/site/tpl/2000001371`（不带 id） | **521** |
| `https://…/zmhd/index.html`（对照） | **200** |

补全浏览器头（UA/Accept/Accept-Language/Referer/Upgrade-Insecure-Requests）**无效**，重试 3 次全 521。

⇒ **按铁律第 6 条，取不到答复正文就不许写适配器** —— 硬建会变成零数据源污染判据②。
⇒ 记为 **判死（待复验）**。**复验方式**：换 IP / 走浏览器抓一次 `/site/tpl/…` 看是不是反爬；
若确认是反爬，需要带完整浏览器指纹或走 Playwright 才能采。

## 给下一轮的动作（按收益）

1. **先扫「同 CMS 家族」**：对这 6 个市，抓各自 `/hdjl/*` 或 `/zmhd/*` 页面里的
   **真实 ajax 调用块**（不是模板里的 `<?=…?>`），抄 `labelName` + `file` + `action` 三件套。
   **每站都要单独抄** —— 芜湖/蚌埠已经证明「同一个 `/site/label/8888`，参数四处全不一样」。
2. **安庆**：先解决 521（反爬 or 真挂），再谈适配器。
3. **淮北/淮南/六安/滁州/马鞍山**：`collectInfoList` / `interviewInfoList` 这些名字
   **未必是信件问答**（可能是征集调查 / 在线访谈）⇒ **写适配器前必须先取一条明细确认是问答**。

---

# ★ 2026-10-13 第 8 轮补记之二：**淮南市 —— 已验可采，但服务器极慢**

**结论：数据质量是本项目目前见过最好的，但站点响应慢到需要专用超时策略。**

## 一、明细答复质量（铁律第 6 条 ✅ 已验）

抽 1 条（`/site/tpl/150847861?detailId=e4936b0a-af8a-4a22-bd4e-19d40eef1e7f`，
「谢家集区新家园A区房屋墙皮脱落相关问题」）：答复是**完整公文式**——

```
基本情况 / 调查情况 / 处理意见 / 回访情况
办理部门: 谢区房产服务中心   经办人:孙敏   联系方式:0554-********
回复单位：谢家集区房产管理中心  回复时间：2026-09-01 09:59
```
**另带「评价」与「二次评价」**（本例：二次评价=不满意，8月29日回访群众表示未解决）。
⇒ 这是**带办结闭环**的高档考卷料，比芜湖/蚌埠又高一档。

## 二、明细 HTML 结构 —— **与池州 `cz-hdjl` 逐字一致**（可复用解析）

```
<div class="message_con clearfix">
  <div class="message_title lx_title"><span>留言</span></div>
  <div class="message_nr">
    <div class="message_nr_text">…诉求正文…</div>
    <div class="message_info fr">
      <span class="lxr">留言类型：投诉</span><span class="lxsj">留言时间：2026-08-17 17:02</span>
    </div>
  </div>
</div>
<div class="message_con clearfix">
  <div class="message_title hf_title"><span>回复</span></div>   <!-- 回复正文在 message_nr_text -->
    <span class="lxr">回复单位：…</span><span class="lxsj">回复时间：…</span>
</div>
<!-- 还有 pj_title 评价 / 二次评价 两块（message_con 共 4 个） -->
```
⇒ **`cz_hdjl.py` 的 `_parse_detail` 逻辑可以直接搬**（class 名完全相同）。

## 三、两个列表入口（形态不同，都要）

| 入口 | 列表 | 明细 | 分页 |
|---|---|---|---|
| **市长信箱** | `/content/column/5002739?pageIndex=N`（**服务端渲染**）| `/content/article/<id>` | **17 页**（页面里 `pageCount:17`）|
| 市长热线回复选登 | `/site/label/8888?labelName=mayorHotLineHfxdPageList&pageSize=7&isPage=false&file=/c1/huainan/mayorHotLineHfxdPageList-new` | `/site/tpl/150847861?detailId=<uuid>` | **首页只给 7 条，无分页** |

市长信箱列表条目结构（服务端渲染，**静态可取**）：
```html
<li class="odd">
  <p class="p1">我要咨询</p>
  <p class="p2" title=" 市交通运输局 ">市交通运输局</p>
  <div class="p3 p"><a href="https://www.huainan.gov.cn/content/article/1261058139"
                      title="请问S19淮桐高速淮南段通车时间？">…</a></div>
  <p class="p4">2026-07-11</p>
</li>
```
⇒ 与芜湖的 `<th class="tit">/td` 完全不同，**要另写列表解析**。

## 四、⚠⚠ 站点极慢 —— 必须专用超时策略

| 请求 | 实测 |
|---|---|
| `/zmhd/index.html`（首页）| 快（~几秒，62 KB）|
| `mayorHotLineHfxdPageList` 默认参数（首页那套）| 快（缓存）|
| `mayorHotLineHfxdPageList` + `pageSize=100` | **ReadTimeout 90s** |
| 同上 + `isPage=true&pageIndex=1` | **ReadTimeout 90s** |
| 明细 `/site/tpl/150847861?detailId=…` | **时快时慢**：一次 ~5s 成功，另几次 **90s / 40s 超时** |
| `/content/column/5002739?pageIndex=1` | 多次 **90–400s 超时** |

⇒ **写适配器时必须**：`timeout` 给到 **60–120s**、`_get()` 重试 **4–5 次**、
`PAUSE` 放大到 **2–3s**、**必须分小块**（每块 100~200 条）并且**每块单独 commit**。

## 五、下一步（淮南）

1. 用 `cz_hdjl.py` 的明细解析 + 新写的列表解析，建 `hn-szxx`（市长信箱，17 页）。
2. 先只跑 **1 页**验证解析，再放量。
3. 若 `/content/column/` 持续超时 ⇒ 改走首页那个 `mayorHotLineHfxdPageList`（只 7 条，但明细质量最高）。
