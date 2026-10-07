# 站点台账 —— 每个站怎么取、状态如何、下一个该试哪里

> **给接手扒"各省市"的人**：这一页是**已验证的清单**，别从零摸。
> 政务站**大量复用同一套中间件** —— **找到一个就等于找到一片**。

## 一、已跑通（代码在 `adapters/`）

| key | 站点 | 取法 | 量 | 接口 / 入口 |
|---|---|---|---|---|
| `mee` | **生态环境部** | **接口** | 163 条 | `GET https://www.mee.gov.cn/was5/web/search?channelid=232534&perpage=100&page=N` |
| `mem` | **应急管理部** | 静态列表 | 60 条 | `https://www.mem.gov.cn/hd/gzly/hdhdly/` + `index_1..9.shtml` |

## 二、已侦察、**接口没拿下**（下一个人接着做）

| 站点 | 状态 | 实测到什么 | 下一步该试什么 |
|---|---|---|---|
| **住房和城乡建设部** | ⚠ 入口没定 | 首页 200；`/hdjl/index.html` **404**；首页 JS 全是展示类（`jquery.SuperSlide`），**无接口线索** | 在首页找「互动」栏目的**真实链接**（市监的是 `/hd/index.html` 这种形态）；找到列表页再挖内联 JS |
| **国家市场监督管理总局** | ⚠ 走错路已排除 | · `xgzlyhd.samr.gov.cn/gjjly/` 是 **聊天机器人**（对话气泡 + `robot.js` + Vue）⇒ **对做考卷没用**<br>· 首页有 **`[互动] → /hd/index.html`** ⇒ 这才是入口 | 打开 `/hd/index.html`，找它下面的问答列表页；再挖接口 |
| **国家卫生健康委员会** | ⚠ **域名找错了** | · `www.nhc.gov.cn` 一律 **412**（反爬，与代理无关）<br>· **真入口在另一个域名**：**`zwfw.nhc.gov.cn`（政策咨询平台）→ HTTP 200 / 23.5 KB** | 在 `zwfw.nhc.gov.cn` 里找**咨询列表**（`/kzx/` 返回 728 字节空页，说明路径还要再找） |
| **国家消防救援局** | ⚠ 405 | `www.119.gov.cn` 及其 `/site1/hd/` 均返回 **405**（不是被墙，是**路径/方法不对**） | 按业主指示**用真浏览器**打开 `119.gov.cn`，找互动栏目真实 URL |

## 三、★ 怎么找 `channelid`（这是 WAS5 路线唯一的难点）

生态环境部的接口是 `/was5/web/search`，**难点不是接口，是那个 `channelid`**。方法：

1. 打开该站的**互动/问答栏目页**（如 `https://www.mee.gov.cn/hdjl/`）；
2. **把页面整个抓下来，找 `channelid` 这个词** —— 它通常**内联在页面的 `<script>` 里**，
   和一段叫 `interactionParams` / `leaveWordParams` 的参数对象放在一起：
   ```js
   var leaveWordParams = { channelid: 223015, keyword: '', orderby: '-DOCRELTIME',
                           perpage: 10, page: 1 }
   ```
3. 也可以先搜 **`ajax`** 这个词 —— 列表是哪个函数拉的、参数叫什么，都在同一段里。
   （生态环境部那段里就是 `.ajaxCjwtList` / `.ajaxCjwtPage`。）

**一条命令挖出这段**（把 URL 换成目标站）：
```powershell
.venv\Scripts\python.exe -c "import re,httpx;t=httpx.get('https://目标站/互动栏目/').text;b=re.findall(r'<script[^>]*>(.*?)</script>',t,re.S|re.I);[print(x[:800]) for x in b if 'channelid' in x or 'ajax' in x.lower()]"
```

⚠ **不带 `channelid` 调用时，连本站也返回 711 字节空页** ⇒
**不许**据"返回空页"判定某个站没有 WAS5（我犯过这个错，见 README 坑 3）。

## 四、两种问答站 —— **只有一种能当考卷**

| 型 | 特征 | 能不能当考卷 |
|---|---|---|
| **列表型** | 一条条"问题 + 官方答复"的列表，可翻页/分页 | ✅ **能**（答复里常点名依据文件）|
| **聊天机器人型** | 页面是**对话气泡**（Vue/React 单页），有 `robot.js` 之类；问答由模型现生成 | ❌ **不能** —— 没有固定的"官方答复"可依，**没有 gold** |

**怎么分辨**：抓下来看有没有 `v-for` + `fd-user-msg` / `fd-sys-msg` 这类气泡模板，
或者有没有 `robot.js`。市监的 `gjjly` 就是这一型。

## 五、省市站该从哪下手（**给接手的人的建议顺序**）

1. **先照搬同一套中间件**：在省/市的**生态环境厅**、**应急管理厅**站上试
   `GET https://<域名>/was5/web/search`。**省级站与部级站常是同一家做的。**
2. **按栏目名找入口**，常见叫法：`互动交流` / `公众参与` / `常见问题` / `留言选登` /
   `咨询投诉` / `在线咨询` / `政策咨询` / `回应关切`。
3. **找 `channelid`**：按上面第三节的办法。
4. **找不到接口就走真浏览器**（业主已授权）：`browser_*` 工具打开页面，
   看网络请求里那条 XHR 的 URL 与参数 —— 那是**最快**的找接口办法。
5. **拿下一个就先跑一遍 `measure-locate-rate.py`**，看这个站的**在库率**。
   **在库率低的站，爬再多也进不了考卷**（只会进补料清单）。

## 六、侦察原始证据

`recon/` 下是当时探测的原始响应与发现（接口线索、页面 JS 挖掘、代理对照），
**不要删** —— 它们是"为什么这么判断"的依据：

| 文件 | 是什么 |
|---|---|
| `qa-api-probe.json` | 各站列表页面的接口线索（HTML 里出现的 `ajax/json/api` 字样）|
| `qa-js-mine.json` | 抓 JS 挖接口的结果 |
| `inline-ajax.json` | **★ 挖到生态环境部接口的那一次**（页面内联 JS 原文）|
| `was5-try.json` | 第一次成功调到 WAS5 的响应 |
| `was5-capacity.json` | WAS5 的容量（两个频道的 `recordCount`、`perpage` 上限）|
| `probe-mohurd-samr.json` | 住建部 / 市监的入口侦察 |
| `was5-elsewhere.json` | ⚠ **一条作废的测试**（忘带 `channelid`，含对照，见 README 坑 3）|
