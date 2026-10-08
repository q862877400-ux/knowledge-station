# 可复用资产索引 —— 给「政府公告」采集侧

> **写给另一个对话**：你抓政府公告，我们抓网友留言/政务问答。**目标站点高度重叠**（同一批省市政府网站），
> 差别只在**栏目**，不在**域名**。这份文档告诉你：我们这边哪些东西你能直接拿走用。
>
> 生成时间：2026-10-08 20:50　|　数据基线：**164 个数据文件 / 53,729 条问答记录**
>
> ⚠ **先读最后一节「写入边界」**，那个目录两个对话在共写，别踩。

---

## 0. 一句话结论

**政府网站高度复用同一套中间件（CMS/门户框架）。找到一个接口 = 找到一片站点。**
我们已把全国 31 个省级行政区的门户与厅局摸了一遍，**中间件指纹 + 可达性矩阵 + 逐省实测报告**都在
`recon/` 下。你要做的不是从零探，而是**拿我们的指纹清单去试同域的其他栏目路径**。

---

## 1. 最省时间的三份产物（先看这三份，10 分钟摸清全局）

| 文件（绝对路径） | 里面是什么 | 为什么对你有用 |
|---|---|---|
| `D:\AI\work space\zcode\tools\gov-qa\recon\waf-igi-probe-stage1.json` | **全国 34 省 × 4 条路径的可达性矩阵**：每省测 `http-igi` / `https-igi` / `http-root` / `https-root` 四个 URL 的 HTTP 状态码 | 一眼看出**哪个省门户根路径被 WAF 拦、但接口路径通**。公告栏目通常和留言栏目同域，这份直接告诉你该省能不能直接抓 |
| `D:\AI\work space\zcode\tools\gov-qa\recon\waf-igi-sites.json` | **11 个站的 siteId 枚举结果**：`{host, referer, scheme, sites:{sid: 条数}, total}` | 如果你发现同域也有 IGI 接口，**照这个 siteId 枚举法直接跑**，不用猜 |
| `D:\AI\work space\zcode\tools\gov-qa\recon\province-platform-hunt.txt` | **24 省六类结论汇总**：A 接口型可用 / B 列表型可采 / C 有线索未拿下 / D 问答不在门户 / E 反爬 412 / F 本机不可达 | 每省写明**用的是哪套中间件**、**入口在哪**。公告侧按图索骥 |

---

## 2. 中间件指纹清单（找「用什么接口」看这里）

政务站大量复用这几套系统。**你看到页面里有某个特征，就直接套对应的接口模板。**

### 2.1 IGI（用得最多，我们靠它拿下湖北 1 万条）

```
列表  {BASE}/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId={sid}&order=1&appId={app}&pageIndex={p}&pageSize=20
明细  {BASE}/nbhd/openGovmsgbox.do?method=viewGovmsgbox&metadataId={id}
```
- 响应是 JSON。列表数据在 `datas`；明细答复原文在 `datas.REPLYS[].REPLYHTMLCONTENT`
- 部分站要带 `Referer`；**湖北/武汉不需要**
- `BASE` 一般是 `http://{host}/IGI`（注意用 **http**，别用 https，见 §4 陷阱）
- 已实测跑通 IGI 的站：宁夏、山西、贵州（省直 27 + 门户 11）、吉林、广西、湖北（门户 15 site + 武汉 32 site）、西藏（8 site / 355 条）、陕西（siteId=15 / **4097 条**）、贵州门户（11 site / **2597 条**）、湖北人社（`rst.hubei.gov.cn` 487）、湖北卫健委（`wjw.hubei.gov.cn` 487）

### 2.2 其他中间件

| 中间件 | 接口特征 | 出处 |
|---|---|---|
| **TRS WAS5** | `/was5/web/search?channelid={cid}&perpage=100&page={n}` | 生态环境部 `channelid=232534`；云南门户也用 |
| **jact** | `POST /jact/front/dataproxy_mailpublist.do` + `mailpubdetail.do` | 江苏 |
| **Hanweb / 万户站群** | `POST /u/search/ajaxlist?channel_id={cid}`（**0 基页码**，须 Referer） | 海南 |
| **enorth webpublisher** | 静态分页文件（`index_1.shtml`、`index_2.shtml`…） | 青海 |
| **EWB（河北政务 webBuilder）** | `/EWB-FRONT/rest/frontAppNotNeedLoginAction/`，看 `siteGuid` 参数 | 河北（`heb-szj` 1043 条） |
| **广东 hdjlpt 平台** | `POST /hdjlpt/letter/pubList`（Laravel CSRF：先 GET 落地页拿 `XSRF-TOKEN` cookie，POST 带 `X-XSRF-TOKEN` 头） | 广东 **37 个厅局同款**，43 域名探测 37 命中，**31,092 条** |
| **湖南统一互动平台** | `https://hd.hunan.gov.cn/communication/api-mailbox/frontMail/mailList2ie`，参数 `deptId` | 湖南全省厅局共用，`deptId` 在各厅 `hdjl_index.js` 里 |
| **瑞数动态防护（WAF）** | 返回 **412**，body 内联 `$_ts.cd` / `$_ss.cd` 混淆 JS | 甘肃、湖北门户根路径 |

### 2.3 ★★ 最关键的一条经验（务必转告）

**WAF（瑞数 / 412）只拦 HTML 页面路径，不拦 JSON 接口路径。**

- 实例：湖北门户 `http://www.hubei.gov.cn/` → **412**，但
  `http://www.hubei.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs&...` → **200**
  ⇒ 靠这条拿下湖北 **10,076 条**（`hb-hdjl` 3535 + `hb-wuhan` 6541）
- **但这不是普遍规律。** 甘肃是反例：整域 412，连 `/IGI/` 也 412
- ⇒ **必须逐省逐路径实测，不能假定**。`waf-igi-probe-stage1.json` 就是干这个的

---

## 3. 逐省原始实测报告（要细节看这些）

每份都是**一手实测**，含完整 URL + HTTP 状态码 + 响应片段 + 结论。

| 文件 | 覆盖 |
|---|---|
| `recon\province-platform-hunt.txt` | 24 省系统性重探（总纲，20KB） |
| `recon\xj-xz-sd-gx-qh-hunt.txt` | 新疆 / 西藏 / 山东 / 广西 / 青海 |
| `recon\heb-hi-hunt.txt` | 河北 / 海南 |
| `recon\gs-hb-hunt.txt` | 甘肃 / 湖北（含 WAF 突破全过程） |
| `recon\sh-zj-hunt.txt` | 上海 / 浙江 |
| `recon\jx-yn-hunt.txt` | 江西 / 云南 |
| `recon\bj-nmg-hunt.txt` | 北京 / 内蒙古 |
| `recon\js-jact-hunt.txt` | 江苏（jact 中间件） |
| `recon\hlj-fj-hn-hunt.txt` | 黑龙江 / 福建 / 河南 |
| `recon\tj-sn-cq-hunt.txt` | 天津 / 陕西 / 重庆 |
| `recon\ah-ln-hunt.txt` | 安徽 / 辽宁 |
| `recon\hunan-dept-hunt.txt` | 湖南省直厅局 |
| `recon\gz-igi-hunt-3.txt` | 贵州 |

（均在 `D:\AI\work space\zcode\tools\gov-qa\` 下）

---

## 4. ★ 我们踩过的坑（照抄能省你几天）

1. **https 假象** —— 我们一度判「鲁/桂/青 本机不可达」，后来发现三省 **http 明文全 200**，
   `ConnectError` 全是 **https** 失败。**不要因为 https 失败就判站死，一定试 http。**
2. **「门户无公开问答」≠「该省无公开问答」** —— 西藏原本判死，后在省门户 `/IGI/` 接口上
   **枚举 siteId 1..60**，捞到 8 个 siteId / 355 条（翻案）。**找不到入口时，瞎枚举 siteId / channelid。**
3. **同一栏目可能有多条并行通道** —— 陕西线上有静态页 `sn-lyxd`（184 条），
   同时 IGI 接口 `sn-igi` siteId=15 有 **4097 条**。两条都值得跑。
4. **服务端 301 跳转** —— 陕西 IGI 服务端 301 跳 https，客户端必须 `follow_redirects=True`，
   否则拿不到数据。参考 `adapters\sn_igi.py`。
5. **自签证书** —— 部分站证书有问题，探测时用 `verify=False`（我们 `waf-igi-sites.py` 就是这么写的）。
6. **403/412 限流** —— 探测脚本一律 **请求间隔 ≥1.5s**；撞 403/412 **立即停该站，不重试**，
   冷却后再来。硬刷只会越限流越猛。
7. **站点名绝不能含 `/`** —— 我们用站点名建文件名，含 `/` 会被当路径分隔符导致落盘失败。
   你的命名同理。

---

## 5. 代码级可复用件（要写代码就 import 这些）

| 文件 | 能拿来干什么 |
|---|---|
| `adapters\_igi_common.py` | **IGI 基座函数，可直接 import**。签名：`harvest_igi(fetch, *, SITE, base, site_id, app_id, group_id, referer, limit=None, max_pages=30)` |
| `adapters\hb_hdjl.py` | ★ **多 siteId 薄壳模板** —— 一个域里枚举几十个 siteId 的标准写法，直接照抄改 |
| `adapters\sn_igi.py` | 服务端 301 跳转的处理写法 |
| `adapters\xz_igi.py` / `adapters\gz_portal.py` | 同类薄壳的另两个实例 |
| `adapters\_gd_hdjlpt_common.py` | 广东 hdjlpt 平台引擎（37 个厅局薄壳由生成器产出，改引擎一处全生效） |
| `adapters\_liuyan_common.py` | 人民网留言板签名算法（`md5(路径+param+md5(appCode)[:16])`），含验证 |
| `adapters\_jact_common.py` / `_was5_common.py` / `_hunan_hd_common.py` | 对应中间件的公共引擎 |
| `harvest.py` | 采集主程序。**看 `main()` 里的 `_Fetcher` 协议**：`fetch(url, params=..., headers=...)` = GET，另有 `.post(...)`。⚠ **`_Fetcher` 是 `main()` 内的局部类，无法 import，要自测就自己复制一份** |
| `recon\waf-igi-probe.py` | 探「4 条路径可达性」的探针（34 省矩阵就是它跑的） |
| `recon\waf-igi-sites.py` | 枚举 IGI siteId 的脚本（`follow_redirects=True, verify=False`） |
| `recon\province-platform-hunt.py` + `-dig.py` | 「探门户 → 找互动栏目 → 挖接口」三阶段脚本 |

### 运行环境（照抄）
```
解释器：D:\AI\work space\zcode\.venv\Scripts\python.exe
```
⚠ **不要用 managed python**（`C:\Users\Zegel\.workbuddy-ai\binaries\...`），那个环境**缺 httpx**。

### 采集脚本的稳健跑法（★ 我们踩过「误判卡死」）
逐条抓明细的站**很慢**（每条一次详情请求）。别裸跑 `--limit 400` 然后以为卡死了 ——
那是**慢 + Python 输出块缓冲**，不是死。正确做法：
- **limit 给 100-200**，用「每站独立 `timeout`、超时即跳过」的 bash 脚本
- 模板：`recon\batch-harvest.sh`
- 同族：`recon\hb-harvest.sh`、`recon\sn-igi-harvest.sh`、`recon\xz-harvest.sh`、`recon\gz-portal-harvest.sh`

---

## 6. 逐站台账（要某个具体站的入口看这里）

- `D:\AI\work space\zcode\tools\gov-qa\SITE-REGISTRY.md` —— **逐站台账**：每个站怎么取、量多少、接口/入口是什么、状态如何。33KB，最全
- `D:\AI\work space\zcode\tools\gov-qa\HANDOVER.md` —— 接手须知 + 可执行命令
- `D:\AI\work space\zcode\tools\gov-qa\README.md` —— 模块说明

---

## 7. 关于 `data\*.jsonl`（格式不同，但有交叉价值）

`data\` 下 164 个 `.jsonl` 是**问答记录**，不是公告。统一格式：
```json
{"source": "...", "id": "...", "url": "...", "question": "...", "answer": "...",
 "asked_at": "...", "answered_at": "...", "dept": "...", "channel": "...", "extra": {}}
```

**对你的交叉价值**：拿 `source` / `dept` / `url` 三个字段**反向定位公告栏目**。
问答和公告通常挂在同一个站群、同一中间件下 —— 顺着 `url` 的域，用 §2 的中间件指纹
去试同域的其他接口路径，命中率不低。

---

## 8. ★ 写入边界（这个必须先看，不然两边打架）

`D:\AI\work space\zcode\tools\gov-qa\WRITE-SCOPE.md` 是写入分工文档。核心：

**这个目录有两个对话在共写，已经出过两次事故**（一方 `git add` 整目录，把另一方写了一半的
11 个文件一起提交了）。规矩：

1. **`git add` 只加自己的文件，永不加整个目录。**
   ❌ `git add tools/gov-qa`　✅ `git add tools/gov-qa/你的文件.py`
2. **`git add` 后立刻 commit**，暂存区不隔轮存放（暂存区是全仓共享的，隔轮会被别人的提交带走）
3. **`adapters/__init__.py` 是共享文件** —— 只加自己那几行，不要重排、不要动别人的行
4. **`data/` 与 `recon/` 按文件名前缀分归属**
5. 提交前 `git status --short` 逐文件过一遍归属，发现别人的文件就 `git reset` 掉

**你（公告侧）该碰的文件**：`MINISTRY-ENTRIES.md`、`probe-ministries.py`、`adapters/mem_gov.py`、
`adapters/mee_gov.py` —— 这些是我们不碰的。
**我们（问答侧）的文件**：`adapters/*_igi.py`、`adapters/hb_*.py`、`adapters/gz_*.py`、
`recon/liuyan-*`、`recon/waf-igi-*`、`SITE-REGISTRY.md` 等。

> **本文件（`REUSE-FOR-ANNOUNCEMENTS.md`）是新建的交接文档，只读参考，你不需要改它。**

---

## 9. 你现在可以直接做的三件事

1. **读** `recon\waf-igi-probe-stage1.json` —— 找你要抓的省，看它的接口路径通不通
2. **抄** `adapters\hb_hdjl.py` 的薄壳结构 + `adapters\_igi_common.py` 的基座 —— 写你自己的公告适配器
3. **试** 同域其他路径 —— 拿到一个站，用 §2 的指纹表逐条试，命中就是一片

有任何具体站想确认，直接来问，我们这边有逐省实测数据可查。
