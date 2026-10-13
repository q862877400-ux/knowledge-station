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
