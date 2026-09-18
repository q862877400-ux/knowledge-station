# 法规/标准「渠道覆盖 + 巡检」改造方案（长周期 · 多轮次）

> **本文件是这条线的唯一进度真源（ledger）。** 每一轮开工先读它、收工必须改它。
> 不依赖任何对话记忆——上下文被压缩后，读这一个文件就能接着干。

## §0 业主原话（2026-09-18，逐字留档）

> 这些内容是我初步调研的，获取法规标准的发布、修订、废止、查是否现行、查编号的各种渠道和现成的项目
> 或者 Skill，你参照一下然后做一次独立调研，我想让我们的法规标准巡检能**绝对覆盖大量尽可能全的官方
> 渠道**，而且在**前端要能看到各种渠道的链接、有效性、上次成功查询**什么的，方便人工维护渠道。
> 其次你调研别的项目和 Skill 要进行**拆解式的调研**，直接看代码里是从哪里获取的，怎么爬数据，怎么清洗
> 数据之类的实现方式等等等任何需要了解的技术细节，最后给我一个**改造方案**，或者融入到现在的施工计划中。
> 注意这是**长周期多轮次**的活儿，你安排的时候看怎么**避免上下文压缩导致工作越做越粗**，毕竟肯定有大
> 量未命中缓存输入

业主随消息附了一份**他自己初步调研**的报告（法规类 9 个项目名称多为"未核实"、标准类 6+ 个已核实、
20+ 个官方渠道链接）。⚠ 那份报告**不作为依据**：其中大量条目业主自己标注了"未核实"，本轮必须重新核实。

## §1 现状：我们**已经有**什么（读代码得到，带证据）

⚠ 业主的直觉是"这块还没有"；实际是"**有相当厚的底座，但缺台账与覆盖率**"。先把事实摆清，避免重复造。

### 1.1 巡检本体 = **号码驱动**（`src/core/update/inspector.py`，37KB）

| 事实 | 位置 |
|---|---|
| 选待查标准号（tier0 领域订阅 / tier1 滚动） | `select_standard_nos()` :193 |
| 建批次 / 状态机 / 检查点 | `create_inspect_batch()` :229、`_transition_status()` :268 |
| 单号探测 → `ProbeOutcome`（判 current/superseded/withdrawn/编号变化） | `_probe_number()` :335、`judge_result()` :312、`ProbeOutcome` :294 |
| **渠道降级链** `official_gb → web → govcn`（权威渠道按号特征前置） | :61、:409、`channels/routing.select_chain` |
| 重试预算 3、并发 2、日预算默认 500（万级滚动 ≈ 70 天一轮） | `MAX_ATTEMPTS` :64、`CONCURRENCY` :66、`DEFAULT_DAILY_BUDGET` :68 |
| 暂停/恢复/验证码等待（人工介入点） | `request_pause` :524、`resume_batch` :569、`captcha_wait_events` :715 |
| 结论落到变更台账（带 `source_channel` + `evidence_url`） | `change_repo.py` :106-190 |

### 1.2 渠道适配器 = **13 个**（`src/core/update/channels/`，`ADAPTER_CLASSES` 见 `__init__.py:41`）

`official_gb`(国标全文公开系统) · `std_samr_hb`(行标) · `laws_db`(法规库) · `govcn_announce`(国务院公告) ·
`ndls`(发改委?) · `mee`(生态环境部) · `mem_gov`(应急管理部) · `mohurd`(住建部) · `cssn`(工程建设标准) ·
`hbba`/`dbba`(备案/地方?) · `ttzb`(?) · `web_fallback`(泛查兜底)

- 基座：`base.py`（`ChannelAdapter` :309、`ChannelResult` :161、`CurlCffiTransport` :182、
  `HttpxTransport` :250、`UpdateError`、`UPD_CHANNEL_TIMEOUT/ERROR`、`recordable`/`upd_log`）
- **反爬**：`proxy_rotate.py`（11KB）
- 失败语义统一（超时/非 200/解析 0 条分别归一）——这是既有纪律，扩展时必须沿用

### 1.3 已经有一份「渠道台账」——但只给**公告源**用（`src/core/update/announce.py`，32KB）

- 增删改：`add_source()` :206、`update_source()` :223、`remove_source()` :251
- URL 纪律：`normalize_url()` :93、`url_hash()` :121、`is_private_url()` :152（**SSRF 白名单/私网拒绝**）
- 列表页解析：`parse_list_page()` :279（日期抽取 `_parse_date()` :264）
- **健康态**：`get_scan_state()` :339（`never/running/done/skipped`）、每源 `status=failed + reason`、
  最小扫描间隔 `_min_interval_hours()` :330、僵尸扫描自愈（DB running 而进程已死）
- 语义纪律（模块头 :23）：**失败诚实**——WAF/验证码、JS 渲染壳、解析 0 条、超时都要按源记 reason
- 前端已有：设置 → 「公告发现」（列源、添加源、扫描公告源、导出 Excel）

⇒ **业主想要的那套"链接/有效性/上次成功查询"交互，本仓已经有一个可复制的形态**（公告源），
缺的是把它**提升为覆盖全渠道的一等公民**，并接上那 13 个代码适配器。

### 1.4 其它相关件（别重复实现）

| 件 | 作用 |
|---|---|
| `law_source/`（`flk_client.py` / `govcn_client.py` / `http.py` / `catalog.py`(23KB) / `verify.py`(15KB) / `update.py` / `ingest.py` / `convert.py`） | 国家法律法规数据库 + gov.cn 的客户端、**`law_catalog` 目录表（库内 29764 行）**、法规校验与入库 |
| `update/discover.py`（30KB） | 网络渠道发现/分类/watchlist（结果卡片） |
| `update/subscriptions.py` | 「领域订阅」（9 个领域词）——决定 tier0 纳哪些标准；**不是**渠道表 |
| `update/scheduler.py` / `report.py` / `data_package.py` | 定时、报告、数据包 |
| 前端 | 设置 → 每日巡检 / 公告发现 / 效力报告；`/api/v1/update/*` + 宿主 `plugin/src/{inspection,announce}.js` |

### 1.5 缺口（本方案要补的 + R1 拆解新发现的）

- **G1 渠道台账只覆盖公告源**：13 个代码适配器对用户**不可见**（没有链接、没有有效性、没有上次成功）。
- **G2 覆盖率未量化**：地标（31 省）、部委行标、团标、国际标准大多没有专用适配器；
  `web_fallback` 只是兜底，**不算"覆盖了某个渠道"**。
- **G3 五类监控没在同一体系里记账**：现行性/编号变化走 `inspector`（号码探测），
  发布/修订/废止公告走 `announce`（列表页），两边**互不知道对方的渠道是否活着**。
- **G4（上一轮发现）**：`law_catalog`（29764 行）**没有任何 UI 入口**（grep 无引用）。

以下为 R1 内部拆解（`docs/research/channels/internal-inventory.md`）新发现，**父代理已逐条读代码复核**：

- **G5「13 个适配器」是虚数：5 个永不被探测**。`routing.select_chain`（`routing.py:20-31`）只路由 8 个；
  `laws_db`/`mem_gov`/`std_samr_hb`/`mohurd`/`cssn` 虽在 `ADAPTER_CLASSES` 且被实例化
  （`inspector.py:396-406`），但永不进链 ⇒ **覆盖率统计若按"注册了几个"算，会虚报**。
- **G6 降级链的两根"兜底棒"在真实网络下恒 miss（= 死渠道）**。
  `web_fallback.py:53-54` 与 `govcn_announce.py:61-62` **只有 `isinstance(body, dict)` 一条解析分支**
  （mock 契约的形状），而它们实际请求的是 bing 搜索页
  （`https://www.bing.com/search`）与 gov.cn 搜索页（`https://sousuo.www.gov.cn/sousuo/search.shtml`）
  —— 真实响应是 **HTML 字符串** ⇒ `results=[]` ⇒ 直接 `_miss`。
  ⇒ **`official_gb → web → govcn` 三棒链实际只有第一棒在工作**（父代理已独立读代码确认）。
- **G7 巡检渠道没有任何"健康度"字段**：`update_change_event` 只有 `source_channel` + `evidence_url`
  （`inspector.py:438-446`）⇒ 台账要的"有效性/上次成功查询"**必须新建**；现成模板只有
  `announce.py` 的逐源 `status/reason` + `scan_state`。
- **G8 证据链接不可直接采信**：`official_gb` 的 `evidence_url` 是 `showInfo:<hcno>` **伪协议**
  （`official_gb.py:80`，只有 `scripts/std_status_check.py:84-88` 会转成真 URL）；`cssn` 证据 URL 疑似拼错
  （`cssn.py:193`）；`govcn` 下载失败会写**空占位 PDF**（`govcn_announce.py:147-150`）。
- **G9 人工体检与引擎巡检是两套渠道集**：`cssn` 是 `scripts/std_status_check.py:173` 的默认主渠道，
  引擎巡检却一次都不用；且 `inspector.py:338-339` 的 docstring（"AQ→mem_gov、工程建标→mohurd"）
  与 `routing.py:21,23`（两者都 → `ndls`）**自相矛盾** ⇒ 台账设计不能照抄 docstring。
- **G10 反爬能力没接在引擎上**：`proxy_rotate.py` 全仓只被 `scripts/*` 引用；`cssn.py:111-112`
  把验证码**吞成 miss**（F-11 半自动过点对 cssn 失效）；`ndls` 的 Jiasule 惩罚期（30min+ 全拦）
  在巡检侧只能记 `failed`。

以下为 R1 外部束（`docs/research/channels/oss-decomposition.md`，1267 行 / 18 项）新发现，
**父代理已复核 G11**：

- **G11 错误码表有文档没代码**（我方缺陷，已复核）：`base.py:14-16` 的 docstring 列了
  `UPD-1003 rate_limited`，但全文件只定义 `UPD-1001/1002/1004`（:37-39），全仓**唯一**出现
  "UPD-1003" 的地方就是那行文档 ⇒ 没有代码会产出它。
  ⚠ 而 G10 恰恰说明**限流是真实状态**（ndls 的 Jiasule 惩罚期、cssn 的验证码）⇒ R2.5 应
  **补上常量并在那两条路径上真的用它**，而不是删掉文档（删掉等于继续把限流伪装成"没搜到"）。
- **G12 我们只有"按号核验"，没有"发现未知新标准"**（能力缺口，最值得补的一条）：
  现有链路是 pull-by-key（拿库里的号去问渠道"还在吗"）；**没有 crawl-all-then-diff**
  （定期把渠道的公告页/列表页全量拉下来，与我们库比对，发现"我们根本不知道的新号"）。
  `regwatch-eu` 的极简 `Source` Protocol（`fetch(since, regulations) -> list[RawChange]`）
  是一个可直接照抄的接口形状 ⇒ R5 起要加一个平行的 `discover(since)` 协议。
- **G13 零新域名成本的增量**：`hbba/dbba` 用的 `*.sacinfo.org.cn/stdQueryList` 返回行里有 `pk`，
  而 `attachment/downloadStdFile?pk=<pk>` 能取**文档本体**（我们现在只探状态、不取文档）
  ⇒ 不新增任何域名就能把这两个渠道从"状态核验"升级为"能拿原文"。

以下为 R1 标准束（`docs/research/channels/std-cn.md`，38 条渠道：✅29 / ⚠1 / ❌8）新发现：

- **G14 ⚠「HTTP 200 ≠ 有数据」是本项目最大的假可用陷阱**（实测证据，直接决定 R3 的设计）：
  应急管理部标准页响应体**只有 465 bytes**（正文仅标题）；`bzw.com.cn` 列表页正文写着
  "当前第0页，每页0条，共0条"（JS 未执行）；住建部列表页条目由 JS 注入；`ccsa`/`cesa` 是纯 SPA 壳；
  北京市地标查询的后端 `innerapp.capital-std.com` **实测 502（死链）**。
  ⇒ **R3 的"语义探针"不是锦上添花，而是必需**：判活必须"抓到的页面里有没有预期锚点"，
  否则零产出要上线后才暴露（正好落在业主最在意的"人工维护渠道"上）。三态定义见 §7.3。
- **G15 31 省地标**：**不该逐省适配**（实测 8 省格式差异极大：江苏/广东**没有**标准公告栏目、
  山东 charset 写成非法的 `ISO-88509-1`（实为 GBK，须按 936 解码）、上海首页 75 个链接里
  **一个标准栏目都没有**且 6 个候选 URL 全 404、北京后端 502、浙江最规范）。
  **正解**：`POST dbba.sacinfo.org.cn/stdQueryList`（`industry=<省名>` + `status=现行|有更新版|废止`
  + `pubdate=近N月`）一个端点覆盖全国，`total=117718`；8 省实测（北京 3929 / 上海 2010 /
  江苏 5689 / 浙江 2189 / 山东 6359 / 广东 2806 / 辽宁 3954 / 四川 3452），细到**市一级**；
  权威性：国家标准化管理委员会主管、总局国家标准技术审评中心主办；时效性 `recordDate=2026-09-18`（当天）；
  且 `reviseStdCodes`（被代替号）+ `fzDate`（废止日期）+ `status` 三件套齐全。
  ⚠ 我们**已经有 `dbba.py`** ⇒ 这不是"新写 31 个适配器"，而是**把已有适配器的查询面用足**。
- **G16 可直接适配的免登录 JSON（"发布公告发现"的种子，接 G12）**：
  · 国标公告发现 `GET std.samr.gov.cn/noc/search/nocGBPage`（实测 total=**542**，最新 2026年第39号/08-31）
  · 行标 `POST hbba.sacinfo.org.cn/stdQueryList`（total=**118946**，`recordDate` 到 2026-09-16）
  · 团标 `GET std.samr.gov.cn/tb/search/tbPage`（total=7906；其 `HREF` 字段直接给 ttbz 详情页 URL，
    是**绕过 ttbz 滑块 WAF** 的关键）
  ⚠ **国标接口只给 `STATE`（现行/即将实施/废止），不给"被代替"关系** ⇒ 回答"GB 30871 编号是否变化"
  国标仍须回落 HTML 详情页；行标/地标才有结构化答案。**这是"五类监控"覆盖度的真实边界，不许写成全绿。**
- **G17 既有适配器里的死链/迁移要就地更正**：`kjs.mee.gov.cn/hjbhbz/` SSL 握手失败
  （正确域名 `www.mee.gov.cn/ywgz/fgbz/bz/`）；`openstd…/bzgk/gb/` 已 **302** 到 `/bzgk/std/`；
  `cfstc.org` 502；`ccsainfo.com` 连接层失败；`bzw.com.cn` **只有 http 可通**（https 握手失败）；
  **卫健委整站对非浏览器客户端一律 HTTP 412（WAF）** ⇒ 这几个今天在我们的适配器里属于
  "配着但可能永远失败"，R2.5/R3 必须按实测结果标注或修正。
- 唯一真实缺口：**住建工程建设标准的"任意标准现行性"**只能靠 `ccsn.org.cn/News/More.aspx?ClassID=004001`
  兜底（查不了任意标准）⇒ 这是台账上要**显式列为缺口**的一条，而不是假装覆盖。

以下为 R1 法规束（`docs/research/channels/law-cn.md`，1354 行 / 58 条：✅37 / ⚠1 / ❌20）新发现：

- **G18 ⭐现行性的机器判据找到了**：`flk.npc.gov.cn` 是 Vue SPA（`/api/` 全 404），真接口是
  **`POST https://flk.npc.gov.cn/law-search/search/list`**（实测 total=30598、pageSize=100 可用），
  四态字段 `sxx` 的枚举从打包产物里挖出并**用实测计数交叉验证**：
  `1 已废止 3177 / 2 已修改 7908 / 3 有效 17233 / 4 尚未生效 64`。
  ⚠ 三个坑必须写进适配器：`flfgCodeId` **只能用叶子码**（第三方文档写的 101/201/311 实测返回 0 条）、
  返回标题带 `<em class='highlight'>` 要剥离、存在 `sxx=null` 脏数据；响应头有网宿 WAF `WZWS-RAY`。
- **G19 「国家行政法规库」有两个，快的那个不是司法部那个**：`moj.gov.cn/.../flfggzflk/` 实测
  HTTP 200 但**响应体仅 118 字节**（全文是 `document.location.href="https://flk.npc.gov.cn/"`）；
  真库是 **`http://xzfg.moj.gov.cn/search2.html`**（现行有效 606 部，与 flk 计数一致），
  **实测最新 2026-09-06 vs flk 2026-08-30 ⇒ 快约 7 天**，且每条带"历史沿革"多日期
  （如某条例 2004/2016/2018/2024/2026 五个日期）= **修订沿革最好的一手源**。
  ⚠ 它的 `title=` 关键词检索**实测不生效**（仍返回 606 全量）⇒ 只能全量分页遍历。
- **G20 ⭐最快的"新发布"探针是静态 JSON**：`https://www.gov.cn/zhengce/zuixin/ZUIXINZHENGCE.json`
  （1096 条，字段 `TITLE/URL/DOCRELPUBTIME`，最新 **2026-09-17 = T-1**）⇒ 比 flk 快约 **19 天**。
  地方上：`gdpc.gov.cn/bascdata/`（广东，**唯一自带"时效性"列**的地方库）、
  `zjrd.gov.cn/sylf/fggg/`（浙江，395 条**内联在 HTML 里**，四省中最易抓）。
- **G21 flk 的覆盖边界（写进台账，不许写成全绿）**：**flk 不含部门规章与地方政府规章**
  ⇒ 这两类必须靠 xzfg / 部委 / 省政府补齐；而"编号核验"的稳定 ID 是 flk 的 `bbbs`
  （部令用"部令第N号"、省政府用"粤府令第323号"这类标题号）。
- **G22 20 条"不可程序化"要按原因分类记账**（不是笼统写"抓不到"）：
  JS 空壳/需渲染（gov.cn 国家规章库、最高检法规栏目、市场监管总局法规司、工信部政策文件
  —— 网关返 `code=601`、浙江政府规章与政策文件库）；**WAF 实测拒绝**（卫健委 412、住建部 403、
  人社部 JS 挑战 `EO_Bot_Ssid`、国务院公报年目录 403）；**检索需会话态**（gov.cn 政策文件库三种
  入口实测全返 0）；路径未定位（交通运输部、司法部备案审查）；SSL/重定向
  （`sft.sh.gov.cn`→正确是 `sfj.sh.gov.cn`、`rd.gd.cn` 只有 http、浙江政府重定向桩）。
  ⇒ 面板上的"不可抓"必须**带原因码**，人工维护才知道该等它修复还是该换渠道。

**G23（R2 落地时发现，父代理已复核代码）接线名字不一致 ⇒ 该渠道被静默跳过**：
`ADAPTER_CLASSES` 的键是 `"ttzb"`（`channels/__init__.py:53`，取自文件名 `ttzb.py`），
而适配器自己的 `name = "ttbz"`（`ttzb.py:96`），`routing._PREFIX_ROUTE` 里写的也是 `"ttbz"`；
`inspector._build_adapters` 按**键**建字典（`inspector.py:402-405`），`_probe_number` 按
`select_chain()` 的**值**去查（:343、:349）⇒ 查 `ttbz` 查不到 ⇒ **团体标准这一路永远走不到专用渠道**，
而且因为查不到时是继续下一棒（不抛），**现场只会表现为"没搜到"**。
⇒ 已写进渠道种子（`ch:ttbz` 的 `wiring='broken'` + 原因），并有用例守着
（`tests/test_channel_repo.py::TestShippedSeed::test_接线名字不一致的渠道在种子里被标出来`）。
**修法留给 R2.5**（与"两根死兜底棒"同一批：都是"在链上但实际不工作"）。

## §2 目标态（可验收的形状）

1. **渠道台账（channel registry）**：每个渠道一条记录，至少含
   `id / 名称 / 类别（法规·国标·行标·地标·团标·国际·公告页）/ 链接 / 抓取方式（json|html|pdf|rss）/
   探针（怎么判"有效"）/ 覆盖范围说明 / 使用它的适配器 / 当前状态 / 上次成功查询时间 / 上次失败原因 /
   连续失败次数 / 人工备注`。
2. **前端「渠道台账」面板**：表格 + 每行「立即探测」+ 新增/编辑/停用；**有效性、上次成功、失败原因
   必须是实测值**（不是配置里写的"应该能用"）；探测失败要给出可操作原因（被 WAF 挡 / 需要验证码 /
   结构变了 / 网络不通）。
3. **巡检消费它**：`inspector` 的降级链从"代码里写死的顺序"改为"读取台账中该类别**已验证可用**的渠道"
   （不可用的自动降级，且**记录降级原因**——不许静默）。
4. **覆盖率可量化**：一张随轮次更新的覆盖表（类别 × 渠道 × 是否有适配器 × 是否已验证），
   写进本文件 §6，作为"绝对覆盖"的可反驳证据。
5. **五类监控同源记账**：发布/修订/废止/现行性/编号核验的结论都落到 `change_repo`
   （已带 `source_channel` + `evidence_url`），并能在前端按渠道回看。

## §3 研究协议（"拆解式"调研的硬要求）

**每个渠道/项目都必须写成同一种记录**，否则结论不可比、不可复核：

```
渠道记录（外部）
- 名称 / 类别 / 链接（实测访问的那一个 URL，不是首页）
- 实测证据：HTTP 状态 + 抓到的关键片段（≥1 行原文）+ 访问时间
- 内容形态：JSON API / HTML 列表页 / PDF 公告 / RSS / 需 JS 渲染 / 需登录
- 分页与检索参数（能拿到的原样记下来，如 ?page=1&size=20、POST body 形状）
- 更新节奏（公告页多久出一批）+ 时效性（能否当天发现）
- 反爬：验证码 / WAF / 频率限制 / Referer 要求（实测到的才算）
- 可判定的问题类型：发布? 修订? 废止? 现行性? 编号核验?
- 结论：可直接适配 / 需 web_fallback / 不可程序化（写明为什么）

项目记录（开源项目 / Skill 的**代码级拆解**）
- 仓库与许可、语言、最近提交（判"还活着吗"）
- **数据源**：代码里真正请求的 URL / 端点 / 参数（贴代码位置或片段）
- **抓取方式**：HTTP 库、验证码处理、代理、并发、重试
- **清洗方式**：解析库、选择器/正则、字段映射、去重
- **输出形态**：JSON schema / Excel / SQLite / 文件命名
- **可复用点**：哪一段我们可以直接抄思路（尤其是"官方没有 API 时的取数技巧"）
- **坑**：许可、封禁风险、维护状态、与我们既有适配器的重叠
```

**核实纪律**（业主的"不依赖二手信息"）：
- 仓库/页面**必须实际访问**才算 ✅；只搜到名字没访问 = ⚠ **未核实**，且必须写明"未核实"。
- 每条记录带**访问时间**（研究文件按轮次分文件，时间写文件头）。
- 搜到的二手描述**不作为证据**；只能作为"去哪找"的线索。

## §4 轮次计划（每轮的交付物 + 退出判据）

| 轮 | 内容 | 交付物（磁盘） | 退出判据 |
|---|---|---|---|
| **R1**（进行中） | ①内部拆解：13 适配器 + `law_source/*` 的端点/参数/清洗/失败语义 → 覆盖清单；②外部核实：法规类渠道；③外部核实：标准类渠道（含 31 省地标）；④项目/Skill 代码级拆解 | `docs/research/channels/internal-inventory.md`、`law-cn.md`、`std-cn.md`、`oss-decomposition.md` | 四份文件齐；每渠道/项目都有 §3 格式记录；未核实的显式标注 |
| **R2a** ✅（2026-09-18 完成） | 台账**数据模型 + 种子 + 仓储 + 用例**：`update_channel` 表（schema.sql）；`src/core/storage/channel_repo.py`（类别归一/CRUD/健康度三态/种子导入）；`src/core/update/channel_seed.json`（131 条，wiring **由 routing 反查**得出） | 上列三件 + `tests/test_channel_repo.py`（**41 用例**） | ✅ 131 条入种子、类别收敛到 9 个 canonical、`wiring` 五态、**两根死棒标 broken**、种子导入不覆盖健康度、`pytest 1883/3/0`、`mypy 136/0`、smoke EXIT=0 |
| **R2b** ✅（2026-09-18 完成） | **只读 API + 真机落库**：`GET /api/v1/channels`（列表 + `summary` 同一次返回；非法筛选 422 而非空结果）与 `GET /api/v1/channels/{id}`（无则 404）；两个都是 **`def`**（走线程池，故名单制门禁无需申报）；把种子灌进**实机库** | `src/core/api/routes_channels.py` + 用例 + 落库记录 | ✅ 真机库 131 条；`summary` = wired **6** / unwired 10 / broken 2 / seed_only 113；`state` 全 `unknown`（探针还没跑，**如实**） |
| **R2.5** ✅（部分，2026-09-18 完成） | 修掉"在链上但实际不工作"的渠道：**G23 接线名字不一致**（`ADAPTER_CLASSES` 键 `ttzb` vs 适配器名 `ttbz`）⇒ `_build_adapters` 改为**按适配器 `name` 建表**（注册键作缺省），并加**数据驱动的不变量用例**（穷举 `_PREFIX_ROUTE` + `_FALLBACK`，任何"链里写了但表里没有"的名字都会红） | `inspector.py` 改动 + 2 条用例 + 种子重生成 | ✅ 团标渠道真的能用了（wired 5 → **6**）；两根死棒（`web`/`govcn`）**仍未修**——按"换棒而非修棒"的建议留到 R5 |
| **R2.5**（R1 新增，**建议先于 R5**） | **修两根死兜底棒**：给 `web`/`govcn` 补真实 HTML 解析（或如实降级为"仅 mock 可用"并从覆盖率里剔除）；顺带把 G8 的伪协议证据链接归一 | 适配器改动 + 契约用例（喂真实 HTML 片段） | 用**真 HTML 响应**（离线 fixture）验证能解析出条目；否则状态标"失效"且不计入覆盖率 |
| **R3** ✅（2026-09-18 完成；8/131 条配了探针） | **渠道健康探针**：`src/core/update/channel_probe.py` + `channel_probes.json`。判据=**HTTP 通 + 页面里真的出现期望锚点**，否则 `suspicious`；失败**分级**（`blocked_by_waf`/`endpoint_gone`/`server_error`/`timeout`/`transport_error`/`api_error`/`probe_no_anchor`）；`probe_channels(persist=)` 写台账 | 模块 + 目标表 + `tests/test_channel_probe.py`（**23 用例**）+ 真机落库记录 | ✅ 真机：**7 ok / 1 unknown**（`last_ok_at` 已落库）；123 条如实记"尚无探针" |
| **R4** | **宿主路由 + 前端面板**：表格（链接/类别/有效性/上次成功/失败原因/备注）+「立即探测」+ 增删改 | `/ks/channels*` + `KsChannelsPanel.tsx` + smoke | 真机 CDP 截图：面板可见、能探测、能编辑 |
| **R5** | **覆盖率扩展 + 发现能力**：按 R1 结论补/修渠道（**地标走 dbba 统一平台**、行标 hbba、团标 tbPage、国标公告 nocGBPage）；加 `discover(since)`（G12）；`web_fallback` 的"猜到"与"渠道确认"分开记 | 新/改适配器 + 覆盖表更新 | 覆盖表上"已验证可用"的渠道数明显增加，且**每条都有实测证据**；`discover` 至少发现过 1 条库里没有的新号 |
| **R6** | **五类监控打通** + 巡检读台账选链 + 文档/验收 | inspector 改动 + 集成用例 + `DEVELOPMENT-HISTORY` | 五类各有一条端到端用例；巡检降级链来自台账 |

⚠ 轮次可拆可并（R3/R4 可能拆成两个小步）；**每轮结束必须**：小步提交 → `scripts/snapshot-project.ps1`
打快照 → 全门禁（pytest/mypy/tsc/smoke/verify:commands/uvicorn）只涨不跌 → 诚实边界写进
`docs/DEVELOPMENT-HISTORY.md` → 派独立 verifier（brief 放 `var/tmp/VERIFY-BRIEF-bNN.md`）。

## §5 反上下文压缩纪律（本方案的**核心工程约束**）

业主明确点出的问题：长周期 + 大量未命中缓存输入 ⇒ 必须让"进度"落在磁盘上、让每轮只读小文件。

1. **唯一真源 = 本文件**。轮次台账（§6）只写"做了什么 / 证据在哪 / 下一步"，**不抄正文**。
2. **一份文件一个主题**（`docs/research/channels/*.md` 每个 < 400 行）⇒ 下一轮只读需要的那一份，
   不把四份全拉进上下文。
3. **子代理写盘、父代理只读摘要**：重活（读 16 个渠道文件、翻 7 个开源仓库）派 subagent，
   **要求它把完整记录写进指定文件**，回复只给 ≤30 行摘要 ⇒ 大量内容不进父上下文。
4. **机器可读的中间产物**：R1 结论最终要落成 `docs/research/channels/registry.seed.json`
   （渠道记录数组），后续轮次**读 JSON 而不是读散文**；散文只作证据附录。
5. **每轮开头**：读本文件 §4/§6 + `git log --oneline -8` + `docs/research/channels/` 目录清单（三条命令），
   不重读历史长文。
6. **证据指纹**：外部渠道记录带访问时间；过期的（> 90 天）在下一轮标 `⏳ 待复检`，
   避免"用半年前的实测当今天的结论"。
7. **不做"顺手也改一下"**：跨轮次的额外发现只登记进 §6，不在当轮实施。

## §6 轮次台账（每轮收工追加；只写结论与证据位置）

### R1（2026-09-18 起）
- **开工**：读代码盘出 §1 的事实（13 适配器、号码驱动巡检、公告源台账、`law_catalog` 无入口）。
  已确认：**底座比业主预期厚**，改造重心是"台账 + 覆盖率 + 打通"，不是从零造爬虫。
- **已派**（4 个并行 subagent，各自写盘，父代理只读摘要）：
  1. `internal-inventory.md` ← 我们自己的 13 适配器 + `law_source/*` 拆解（端点/参数/清洗/失败语义/覆盖了什么）
  2. `law-cn.md` ← 法规类官方一手渠道（含业主列的未核实项的存在性判定）
  3. `std-cn.md` ← 标准类官方渠道（国标/行标/地标 31 省/团标/国际）
  4. `oss-decomposition.md` ← 开源项目与 Skill 的代码级拆解
- **下一步**：收四份文件 → 生成 `registry.seed.json` → 进 R2（台账数据模型）。

#### R1 收口进度
| 束 | 文件 | 状态 | 一句话结论 |
|---|---|---|---|
| ①内部 | `internal-inventory.md`（809 行 / 18 项 JSON） | ✅ 已收 | **13 个适配器只有 8 个在链上；三棒降级链实际只有 official_gb 在工作** |
| ②法规 | `law-cn.md`（1354 行 / 58 条：✅37 / ⚠1 / ❌20） | ✅ 已收 | **flk 隐藏 JSON 接口给出四态现行性判据（sxx 1/2/3/4）；最快的"新发布"探针是 gov.cn 的静态 JSON（T-1，比 flk 快 19 天）；flk 不含部门规章与地方政府规章** |
| ③标准 | `std-cn.md`（1145 行 / 38 条：✅29 / ⚠1 / ❌8） | ✅ 已收 | **31 省地标不该逐省适配（用 dbba 统一端点，total 117718）；HTTP 200 ≠ 有数据是本项目最大陷阱；国标接口没有"被代替"字段** |
| ④项目 | `oss-decomposition.md`（1267 行 / 18 项 JSON） | ✅ 已收 | **真伪判定：10 真实可读码 + 1 Skill（在 `cuipointer/ageis`，有真代码）+ 3 半真（npm 包在、源码仓 404；GovPing 更是自己不抓取、只连闭源服务）+ 3 查无此物 + 1 页面取不到正文** |

**①内部束的结论（父代理已逐条读代码复核，见 §1.5 的 G5–G10）**：
- 「13 适配器」是注册数不是能力数（G5）；`web`/`govcn` 两根兜底棒在真实 HTML 下恒 miss（G6，**我复核过**）；
- 台账三列今天都不能直接采信（G7 无健康度字段 / G8 伪协议与空占位 PDF / G10 反爬没接在引擎上）；
- 人工体检脚本与引擎巡检用的是**两套渠道集**，且 `inspector.py:338-339` 的 docstring 与 `routing.py` 自相矛盾（G9）。

**⇒ 由 ① 得出的优先级修正（已写进 §4）**：新增 **R2.5「先修两根死兜底棒」**，排在 R5（扩覆盖）之前。
理由（P1 准确性）：**在两条死渠道上做覆盖率统计 = 自己骗自己**；先让"现有渠道是真的",
再去加新的。

**④项目束的结论（18 项，父代理复核了 G11）**：
- **真伪**：业主清单里 **3 条查无此物**（`legal-database` / `china-law-search` / `policy-monitor`）、
  3 条半真（`GovPing`、`@sanmis/crawler` 是"npm 包在、声明的源码仓 404"；`RegRadar` 8+ 个同名仓无权威）、
  1 条正文取不到（ClawHub 的 SPA）⇒ **业主初研里那批"未核实"确实不能当前提**，本轮的核实有价值。
- **许可红线**（只抄思路、**不抄代码**）：`GBMCP` 根目录**没有 LICENSE 文件**（只在 pyproject 写 MIT）、
  `urlwatch` NOASSERTION+raw LICENSE 404；`OpenSTD_Spider` 是 **GPL-3.0（有传染性）**。
- **别当资产**：`gb688_downloader` 停更 6 年 3 个月；`gbqw` 是 WebView 收藏夹（作者自己写"用浏览器收藏夹
  效果一样 QAQ"）⇒ 建议从调研清单剔除。另：**没有任何项目用付费打码平台**，全是本地 `ddddocr`。
- **可抄技巧（3 条）**：① `viewGb?type=online&hcno=` + **iPad UA** + 10 段 base64 拼接后整体解码
  （绕开验证码+精灵图+OCR，**2020 年实测、需复验**）；② **重定向逐跳复检 + WHATWG 编码嗅探**
  （BOM→meta→chardet，治 gb18030 站乱码；正好补 `is_private_url` 只在发起前判一次的缺口）；
  ③ **"洗内容 + 洗差异"两段式 + 易变文本双正则屏蔽**（治"公告页时间戳抖动 → 误判 new_version"）。

#### R1 收口（2026-09-18）
**四束全到手**，并已合成机器可读种子 **`docs/research/channels/registry.seed.json`**
（由 `var/tmp/build-registry-seed.py` 从四份文档的"机器可读附录"合并，**132 → 去重 131 条**；
解析失败即报错退出，不静默少一份）：

| 维度 | 数字 |
|---|---|
| 记录总数 | **131**（去重后；丢重复 1） |
| 内部适配器 | 18 条（`kind=adapter`，无 verification 字段） |
| 外部渠道 | 96 条（法规 58 + 标准 38），其中 **verified 78 / broken 29 / unverified 6**（含 18 条 n/a） |
| 项目/Skill | 18 条（`kind=project`） |
| 类别写法 | **30 种**（未归一，R2 必修：定 canonical enum + 映射） |

⇒ **R1 的退出判据满足**：四份文件齐、每渠道/项目都有统一格式记录、未核实的显式标注。
**下一步进 R2**（读 `registry.seed.json` 而**不读**那 4000+ 行散文）。

#### R2a（2026-09-18 完成，同一轮）
- **表**：`update_channel`（`schema.sql`）——`wiring`/`verification`/`state` 三列**刻意分开**
  （注册数、研究期实测、运行期健康度），另有 `category_raw`（保留调研原文，不丢证据）、
  `probe_url`/`probe_expect`（留给 R3）、`last_try_at` **与** `last_ok_at` 分开。
- **仓储**：`src/core/storage/channel_repo.py`——`CATEGORIES` 9 个 canonical + `_CATEGORY_MAP`
  （把 R1 的 30 种写法穷尽映射）、`upsert_channel`（未知字段**抛错**、不许拼错静默丢）、
  `record_probe`（**三态**：`ok` 清零 / `down`·`suspicious` 记失败计数 / `unknown` 只记"试过"）、
  `summary()`（**把注册数与能力数分开报**）、`load_seed`/`seed_channels`（幂等 + 默认不覆盖健康度）。
- **种子**：`src/core/update/channel_seed.json`（131 条）——`category` 已归一，
  `wiring` **由 `routing.py` 反查**（不是抄研究文档）：`wired 5 / broken 3 / unwired 10 / seed_only 113`。
  ⚠ `broken` 那 3 条正是本轮的实证缺陷：`web`、`govcn`（恒 miss）+ `ttbz`（G23 名字不一致）。
- **用例**：`tests/test_channel_repo.py`（**41 条**）。写这组用例时**先踩了一个坑**：
  测试库 data_dir 是会话级共享的，用例之间互相污染 ⇒ 第一轮 7 条假红（是测试隔离问题，
  **不是产品代码**），加了 autouse 清表 fixture 后 41/41。
- **门禁**：`pytest` **1883 passed / 3 skipped / 0 failed**（1842 → +41，正好是新用例数）、
  `mypy` **136/0**（+1 新模块）、smoke **EXIT=0**（客户端本轮未改）。
- **没做**（留给 R2b）：只读 API + 把种子灌进真机库。

#### R2b（2026-09-18 完成，同一轮）
- **只读 API**：`src/core/api/routes_channels.py`（`GET /api/v1/channels` + `/api/v1/channels/{id}`）。
  两条口径写进用例：**参数错要 422，不许返回空结果**（空结果会让人以为库里没这条）；
  **`summary` 与 `items` 同一次返回**（两个口径不同的数字最会骗人）。两个端点都是 `def`
  ⇒ 走线程池，名单制门禁（`_ASYNC_ENDPOINTS`）**无需新增条目**（`tests/test_material_api.py` 108 passed 佐证）。
- **真机落库**：`var/tmp/seed-live-db.py` → 实机库 `C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db`
  **131 条**（`inserted 131 / updated 0`）；`summary` = `wired 6 / unwired 10 / broken 2 / seed_only 113`，
  `state` **全 `unknown`**（探针还没跑——台账**如实**说"还不知道"，而不是假装健康）；
  类别分布 law 45 / tool 24 / internal 18 / std_hb 13 / std_db 10 / aggregator 7 / std_gb 5 / std_tb 5 / std_intl 4。
  ⚠ 只是**新增一张表 + 131 行**（`CREATE TABLE IF NOT EXISTS` + 只写本表），与引擎启动时
  `init_schema()` 做的事相同；不碰任何既有表，`DELETE FROM update_channel` 即可回退。
  ⚠ **引擎当前进程仍不认识这张表**（它启动于本轮之前）⇒ 端点要等宿主/引擎重启后才对外可用。
- **门禁（R2a+R2b 合计）**：`pytest` **1889 passed / 3 skipped / 0 failed**（1842 → +47：
  41 条台账用例 + 4 条端点用例 + 2 条接线不变量）、`mypy` **137/0**、smoke **EXIT=0**、
  `tests/test_material_api.py`（async 名单制门禁）**108 passed**（新增端点都是 `def`，无需申报）。

#### R2.5 的一部分（2026-09-18 完成）：G23 修掉
`inspector._build_adapters()` 原先按 `ADAPTER_CLASSES` 的**键**建字典（键取自文件名 `ttzb`），
而 `routing.select_chain()` 返回的是**适配器名** `ttbz` ⇒ 查不到 ⇒ **静默跳过该渠道**。
改成**按适配器 `name` 建表**（类没声明 `name` 时退回注册键），并在 `tests/test_update_channels.py`
加两条：① **数据驱动不变量**——穷举 `_PREFIX_ROUTE` + `_FALLBACK` 的每个渠道名，任何一个
"链里写了但表里没有"都会红（以后加前缀也自动覆盖）；② 具体那条渠道 `ttbz` 取得到。
效果：`wired 5 → 6`（团标这一路真的能走到专用渠道了）。
⚠ 我**同时改了那条种子用例的判据**：R2 时它断言 `ch:ttbz` 是 `broken`，修完后必须断言 `wired`
**但仍要求 note 里写明"注册表键与适配器名不一致"**——修好不等于原本没问题，卫生问题仍要留痕。
⚠ **两根死兜底棒（`web`/`govcn`）本轮没动**：按 §6 的建议是"**换棒**"（`govcn` → `ZUIXINZHENGCE.json`；
`web` 降级为不计入覆盖率的显式最后兜底），那属于 R5 的量级，不该塞进 R2。

#### R3（2026-09-18 完成）：语义探针 —— 把"有效性"变成实测，而不是配置里的声明
- **模块**：`src/core/update/channel_probe.py`；**目标表**：`src/core/update/channel_probes.json`
  （8 条，每条都带 `evidence` = 锚点是从哪次实测看到的）。
- **判据表**（`_classify`，集中一处便于穷举）：403/412→`blocked_by_waf`；404/410→`endpoint_gone`；
  5xx→`server_error`；非 200→`http_<n>`；**HTTP 200 但正文 `code>=400` 或含"系统异常/不支持"→
  `api_error`**；200 且没配锚点→`unknown/no_anchor_configured`（如实说"只探通了"）；
  200 但锚点不在→`suspicious/probe_no_anchor`（G14 那一类）。
- **三个实测教训（都已固化成用例）**：
  1. **"HTTP 200 ≠ 有数据"在 JSON 接口上同样成立**：`flk` 检索接口在我第一版**自造请求体**下回
     `HTTP 200 + {"msg":"系统异常","code":500}`；换成 R1 文档里**实测跑通**的那版请求体后回
     `{"msg":"查询成功",...}` ⇒ 所以 `api_error` 的措辞刻意写"**先怀疑我们的请求体**，其次才是渠道"。
  2. **`method="post"` 必须显式传给 transport**：漏传 ⇒ 静默变 GET，而 flk 与 dbba **两层都回 200**
     （flk 回"Request method 'GET' not supported"、dbba 回一张 HTML 首页）⇒ 只看状态码会把"方法错了"
     判成"渠道健康"。有用例钉住这个 kwarg。
  3. **"渠道可用"与"适配器能解析"是两根轴**：探针只回答前者；`web`/`govcn` 的适配器恒 miss 由台账
     `wiring=broken` 表达。面板必须两列都显示——只显示一列就会给出错误结论（已写进模块 docstring）。
- **真机落库**：`var/tmp/probe-live.py` → 实机库 **7 ok / 1 unknown**（`govcn` 没配锚点，如实记
  "只探通了"），`last_ok_at` 写入。**123 条仍 `unknown`**——因为还没给它们配探针（下一步）。
- ⚠ **时间戳是 UTC**（SQLite `datetime('now')`，与库内既有表一致）⇒ R4 面板要么转本地时区、
  要么显式标注"UTC"，否则"上次成功 04:42"会让业主以为凌晨自动跑过。

#### R3b（2026-09-18 完成）：探针覆盖 8 → **17 条**（锚点全部来自实测）
第二批 9 条（法规/标准各半），锚点取自**实测看到的 `<title>`**（`var/tmp/probe-batch2-anchors.py`
一次抓齐）：`xzfg`→`国家行政法规库`、`mem 法律法规`→`法律法规`、`mem 规章`→`政府信息公开`、
`mee 法规标准`→`法规标准`、`zjrd`→`法规公告`、`gdpc`→`广东省法规规章规范性文件数据库`、
`cssn`→`standard`（JSON 字段名）、`mohurd`→`文告库`、`mem_gov`→**故意钉 `标准公告`**（见下）。

**真机结果（17 条）**：**15 `ok` / 1 `suspicious` / 1 `unknown`**，全部落库（`last_ok_at` 已写）。

**G24（探针当场抓到的一条真问题，值得业主知道）**：
`ch:mem_gov` 配的 `https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/`（**应急管理部标准公告**，
业主主监管部门的那条）今天仍然 HTTP 200、26755 字，但页面标题已变成
**「制度文件--中华人民共和国应急管理部」**，正文里**既没有「标准公告」也没有 `bzgg` 路径、也没有 AQ 号**
⇒ 用 `var/tmp/verify-memgov.py` 复核了页面结构（列出来的是站点导航）后确认：
**这条 URL 已经不是标准公告列表了**（栏目疑已搬迁）。
⇒ 这正是"渠道台账"要替人发现的事：**没有台账时，这条渠道会静静地"永远查不到新公告"，而没人知道**。
新 URL 待找，记入 R5。⚠ 本探针只证明"URL 还在但不是我们期望的内容"；
适配器今天的行为（抓到 0 条后算"无变更"还是算失败）**尚未实测**，属 R5。

**⚠ 由 R1 得出的一个待业主确认的取舍**（比"修旧棒还是换新棒"更根本）：
`web`（bing 泛查）与 `govcn`（gov.cn 搜索）这两根"兜底棒"**今天在真实网络下恒 miss**（G6），
而 R1 找到了**真渠道**（`ZUIXINZHENGCE.json` T-1、`nocGBPage`、flk `sxx`）。
⇒ 我的建议从"修旧棒"改为 **"换棒"**：把 `govcn` 换成 `ZUIXINZHENGCE.json` 这类真接口、
把 `web` 降级为"**不得计入覆盖率**的显式最后兜底"（保留它只为"连官方渠道都没覆盖到的冷门号"
留一条探索路径，但台账上必须显示"未确认"而不是"已核验"）。

## §7 待业主裁定

1. **优先级**：R2–R4（先让台账+面板看得见）与 R5（先扩覆盖率）谁先？我推荐 **R2→R4 先做**
   （"能看见、能维护"是业主原话的第一诉求；覆盖率可以随后按台账逐条补，且补一条就能在面板上看到）。
2. **渠道台账的存储**：跟公告源一样放 `app_config`（JSON，简单、可导出）还是建独立表
   （可查询、可加索引）？我推荐**独立表 + 视图**，因为要按类别/有效性过滤，且要给巡检读。
3. **"有效性"的定义**（必须现在定，否则面板上的数字没有意义）：我推荐**三态**——
   `可抓（探针通过）/ 可疑（HTTP 200 但语义探针没命中预期的锚点）/ 不可抓（超时·WAF·结构变了）`，
   并**分开记**"最近一次成功"和"最近一次尝试"。
   ✅ **R1 标准束给了这条定义最硬的实测支撑（G14）**：应急部标准页 465 bytes、bzw 列表页"共0条"、
   住建部/ccsa/cesa 是 JS 壳、北京地标后端 502 —— **"HTTP 200"在这个领域几乎不能当判据**。
4. ~~地标 31 省要不要全上~~ → **R1 已给出可证伪的答案（G15）**：**不逐省适配**。
   用 `dbba.sacinfo.org.cn/stdQueryList`（`industry=<省名>`）做统一元数据层（覆盖发布/修订/废止/
   现行性/编号核验，细到市一级、当天数据）；省局栏目**只作公告原文 PDF 的补充**，且只补真正需要的少数省。
   ⚠ 我们已有 `dbba.py` ⇒ 这条从"写 31 个适配器"变成"把已有适配器的查询面用足"。
5. **要不要引入外部依赖**（如 `changedetection.io` 那种通用监控）：我**不推荐**在本仓引入——
   我们有 `proxy_rotate` + 13 适配器 + 公告源台账，通用工具反而增加一层不可控；
   但它的**思路**（页面选择器 + 差异通知）值得抄进 R3 的语义探针。

---

### R3c（2026-09-18 完成）：探针覆盖 17 → **28 条**；当场又抓出 5 条死链

批次3：从"已验证但未探"的 71 条候选里挑 GET 得动的 11 条（锚点同样取自**实测 `<title>`**，
脚本 `var/tmp/probe-batch3-scan.py`）：北京市司法局/人大/政府、上海市人大/政府规章库/近期信息公开/
司法局、司法部部门规章栏目、广东人大两个栏目等。

**真机结果（28 条）**：**21 `ok` / 5 `down` / 1 `suspicious` / 1 `unknown`**，全部落库。

**G25（探针当场抓到的 5 条 —— 都是 R1 文档里"看着合理"的 URL）**：

| 渠道 | 结果 |
|---|---|
| `seed:law-cn:北京市司法局-法律法规规章` | **HTTP 404** |
| `seed:law-cn:上海市司法局-规范性文件` | **HTTP 404** |
| `seed:law-cn:广东人大-常委会公报` | **HTTP 404** |
| `seed:law-cn:广东人大-权威发布公告通知` | **HTTP 404** |
| `seed:law-cn:上海市人大-法规公布` | **SSL 握手失败**（`curl: (35) BoringSSL SSL_ERROR`） |

⚠ 最后一条**不是死链**，是**我们的传输层与它的 TLS 指纹不兼容**（`curl_cffi` impersonate chrome 失败）
⇒ R5 要试 `HttpxTransport` 或走 `proxy_rotate`；**不许**把"我们连不上"记成"站点坏了"。
⚠ 前四条也只能说"**我们的 GET 拿到 404**"——有些政府站对 UA/Referer 敏感，R5 复检时要换传输再试一次。

⇒ 这三批合起来证明了一件事：**研究期的一次性核实与运行期的可重复探针是两种东西**：
前者会随站点改版过期，后者每次跑都是当下的真相。这正是业主要"前端能看到有效性"的根因。

**G26（台账去重判据，R4 前必须定）**：批次3 发现 `seed:law-cn:广东人大网`（`gdpc.gov.cn/bascdata/`）
与 `seed:law-cn:广东人大-广东省法规规章规范性文件数据库` **指向同一个库**（标题逐字相同）
⇒ 台账要按 `url` 归一后判重（否则面板上同一条渠道出现两次、覆盖率被重复计数）。
本轮**没有**把重复项加进探针（不制造第二个"渠道"），登记为 R4 待办。

### 当前覆盖率与"下一步"（R3 后的快照口径）

| 维度 | 数字 |
|---|---|
| 台账条数 | **131**（"我们知道多少渠道"） |
| 能干活（wiring=wired） | **6**（"今天真的能用几条"） |
| 已知失效（wired 但 broken） | **2**（`web`/`govcn`，R5 换棒） |
| 已实测有效性 | 🟢 21 / 🟡 1 / 🔴 5 / ⚪ 未探 **104** |
| 人可读快照 | `docs/research/channels/REGISTRY-STATUS.md`（`scripts/channel-status-report.py` 可重复生成） |

**下一步（按价值排序）**：① **R4 面板**（业主第一诉求；等宿主/引擎重启后端到端可见）；
② R5 修/换 `web`+`govcn`、找 `mem_gov` 新 URL、复检 4 条 404 与 1 条 SSL；
③ 继续补探针（104 条未探，锚点必须实测）；④ G26 判重。
