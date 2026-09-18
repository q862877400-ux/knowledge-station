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
| **R6** | **五类监控打通** + 巡检读台账选链 + 文档/验收 ⚠ 2026-09-18 拆段：**R6a/R6b = 渠道覆盖与"未探"的可见性收口**（R5 尾款，已完成，见 §6）；**R6c = 五类监控打通**（未开始） | inspector 改动 + 集成用例 + `DEVELOPMENT-HISTORY` | 五类各有一条端到端用例；巡检降级链来自台账 |

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
8. **门禁一次只跑一个**（2026-09-18 取证，§6 R6b 复核第二轮）：
   `smoke-chatmode` 两次假红（172/173）都发生在**与全量 pytest 并发**时，单独跑 4 次全绿；
   先前那次 pytest `1 failed` 同期也有一份并发的全量在跑。
   ⇒ **并发跑门禁会给自己制造假红**，而假红会污染"只涨不跌"的判断。跑门禁前先确认没有别的
   重活（含子代理在跑全量）在同时进行。

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

### §7 追加：R6a/R6b 期间由我（按业主"需要拍板就按你的推荐"的授权）决定的三件

- **D-a：tool 类的"链接可达性"不并进探针表。** 数据已量（16/18 个 URL 今天 200），
  理由是语义：探针表答"**采集通路**今天能不能抓到东西"，并进去会让面板的"🟢 可抓"把
  仓库链接算成渠道能力（R1 的 G5/G6 防的就是这种虚高，只是换了形状）。
  要做就单独做一组，别塞进同一列。
- **D-b：`cfsa` 的瞬时证书失败不做特殊处理。** 它的 `down → ok` 翻转交给
  `consecutive_failures` 与 `last_ok_at` 自然暴露；**不为一个会自愈的站点加机制**。
- **D-c：`ch:discover_search` 不拿我猜的地址去判它"不可用"。** 记录里的入口实测 404，
  但我没有证据说"这条渠道死了"——保持 ⚪（无探针）并登记"入口待重找"，
  比用一个猜测的 URL 造一个红要诚实。


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

---

### R4a（2026-09-18 完成）：宿主路由 + 引擎探测端点（面板的前置件）

**引擎侧**：`POST /api/v1/channels/probe`（`routes_channels.py`）——人工"立刻探一遍"：
- `ids`（省略 = **只探配了目标的 28 条**，绝不盲探 131 条）；`persist` 默认 true（false 只探不落库）；
- 返回 `{probed, results, counts, without_target, summary}`——**summary 与结果同一次返回**（两条口径不许分两次取）。
**宿主侧**：`plugin/src/channels.js`（两条 `kind:'exact'` 路由）：
- `GET /ks/channels`（query 白名单 `category/wiring/state/verification/enabled_only/limit`）；
- `POST /ks/channels/probe`（body 白名单 `ids/persist`，`persist` **严格布尔**；探针总超时 **150s**）。
- ⚠ **为什么探针必须留在宿主侧**：它会**对外发请求**（访问二十多个政府站）——浏览器侧发起的话，
  谁探了哪个站、探几次都不受控，`Referer/Origin` 还会带上 GUI 地址，对政府站反爬是无谓信号。
  （这与"大字体直连引擎取产物"那条**故意不同**，两条路径的取舍理由都写在文件头。）
**用例/门禁**：`plugin/scripts/smoke-channels-routes.mjs`（**15/15**，已进 `npm run smoke`，链 **22 段**）：
注册面/方法守卫/query 白名单（未知键丢弃）/body 白名单（`persist:"yes"` 不发 true）/引擎 404 原样透传/
5xx→502/不可达→503；引擎侧 `tests/test_channel_repo.py` **48 条**（含 `ids` 类型 422、只探有目标的渠道）。
**还没做**：**面板 UI（R4b）**——那是业主真正要"看见"的部分，排下一轮第一件。

---

### R4b（2026-09-18 完成）：**面板 UI** —— 业主"看得见"的那一半

- **客户端 API**（`plugin/client/api.ts`）：`fetchChannels()` / `runChannelProbe()` + 类型。
  走**同源宿主路由** `/ks/channels*`（不是直连引擎）——理由写在注释里：探针会对外发请求，
  必须在宿主侧受控。
- **面板**（`plugin/client/KsChannelsPanel.tsx`）：表格 7 列 —— 渠道 / 类别 / **接线** /
  **有效性** / 上次成功(UTC) / 失败原因（带错误码与连续失败次数）/ 链接（新标签打开）；
  顶部摘要**同时**显示"台账 N 条"与"能干活 M 条"，并把**接线 ≠ 有效性**这句话印在面板上；
  工具行有类别/有效性筛选 + 「⟳ 刷新」+ 「🩺 立即探测」（点击后回显
  `🟢/🟡/🔴/⚪` 计数，并把"未配探针的 N 条不参与"说清楚）。
- **挂载**：设置区新类目「渠道台账」（与「参考资料」相邻——两者都是"库里的东西要人工维护"的管理台），
  沿用 `<details>` 懒加载门（收起 = 零请求）。
- **纯函数导出**（为了离线可测）：`describeWhen`（**UTC→人话**）、`needsAttention`、`sortChannels`。
- **用例**：`smoke-catalog-ui.mjs` 26 → **43/43**（新增 17 条，含 UTC 解析、问题行判定、
  "有问题的排前面"、懒加载门、两列分列、设置区挂载）。
- ⚠ **面板今天看不到数据**：`/ks/channels` 要**宿主与引擎重启后**才在线（两者都启动于本轮之前）。
  面板对这种情况有明确文案（"渠道台账端点要宿主/引擎重启后才在线"），不会静默空白。
- ⚠ **没做**：行内"停用/编辑/改锚点"（写接口）——那要等 R3 的探针与"人工改锚点"的语义定清楚，
  否则会出现"能改但改了不知道有没有用"的空壳（原话记在 R2b 的取舍里）。

**R4b 真机复验（2026-09-18，CDP）**：刷新页面 → 设置 → 法规标准知识库 → 「渠道台账」
（`var/tmp/gui-channels-panel2.png`）——面板**确实挂上**：类目与提示语、两个筛选下拉
（10 个类别 / 4 个有效性）、「⟳ 刷新」、「🩺 立即探测」都在；端点未上线时显示
**「读取失败：HTTP 404（渠道台账端点要宿主/引擎重启后才在线；若刚更新过而没重启，这里就会报错。）」**
而不是空白 —— 这正是"懒加载门 + 诚实失败"该有的样子。
⚠ 顺带修掉我自己写的一个瑕疵：JSX 文本里的 `**强调**` 会**原样显示**（JSX 不渲染 markdown）——
已把本面板 7 处去掉（文档注释里的 markdown 保留）。**同一写法在既有面板里也存在**
（本次实测页面上还有 8 处，属**既有**风格），按"不夹带顺手改"的纪律**没动**他人文件。

---

### R3d（2026-09-18）：对**自己的结论**做了一次证伪（代理/传输层）——结论站得住，但捞出两个环境级发现

**为什么要做**：本轮发现 shell 里设着 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY=http://127.0.0.1:7897`，
而 `curl_cffi` 的 Session **默认尊重环境代理** ⇒ 我前面 28 条探针**都是走代理出去的**。
于是"渠道不可用"有可能是**测法**造成的（部分政府站对代理出口会更凶）。

**做法**（脚本 `var/tmp/probe-direct-vs-proxy.py`）：清空代理环境变量后**直连**，用同一个
transport 重测 5 条失败 + 2 条已知 ok 的对照。**结果与走代理时逐条一致**：

| 渠道 | 走代理 | 直连 | 结论 |
|---|---|---|---|
| 北京市司法局 | 404 | 404 | **真的没了**（不是我方被拦） |
| 上海市司法局 | 404 | 404 | 同上 |
| 广东人大（公报/公告） | 404 | 404 | 同上 |
| 上海市人大 | SSL 握手失败 | SSL 握手失败 | **是我方客户端指纹问题**（BoringSSL impersonate 被拒），与代理无关 |
| 浙江人大 / 应急部法规（对照） | 200 | 200 | 测法本身没问题 |

⇒ 台账里那 5 条 `down` 的判定**经受住了证伪**（两种测法同结论）。这条证伪本身写进 ledger，
是为了让以后读的人知道：**这些 404 不是"我们走代理被拦"**。

**G27（环境级，值得业主知道）**：`NO_PROXY` 里含 **`[::1]`**，而 **httpx 0.28.1 解析它会直接抛
`InvalidURL: Invalid port: ':1]'`**——也就是说**在这台机器上 httpx 发不出任何请求**。
后果：`channels/base.py` 的 `default_transport()` 在 `curl_cffi` 不可用时回退到 `HttpxTransport`
（只打一条 WARN）⇒ 那种情况下**所有渠道（含巡检）会全灭**，而现场只表现为"每条都失败"。
⇒ R5 待办：① 回退路径要**自检**（构造时探一次，失败就明说"两个栈都不可用"）；
② 或者修 `NO_PROXY` 的 `[::1]` 写法（`::1` 即可）。

**G28（口径级）**：探针/巡检**是否走环境代理**目前是隐式的（curl_cffi 默认吃 env）。
对**境内政府站**，走本地代理（Clash 之类）是无谓绕路，还可能被判定为异常出口。
⇒ R5 待办：探针与适配器都加一个**显式的出网模式**（direct / env-proxy），并在台账里**记下这次是怎么出去的**
（否则"有效性"这个数字的含义会随环境变而没人知道）。

---

### R5a（2026-09-18，**未完成**）：找回应急部「标准公告」新地址 —— 一次诚实的失败

**做法**（脚本 `var/tmp/find-mem-std-announce.py`）：从应急部「法律法规标准」频道页
`https://www.mem.gov.cn/fw/flfgbz/` 找候选链接 → 逐个探。
**结果**：该频道页 **HTTP 200 但只有 471 字、正文里一个链接都没有**（标题
「法律法规标准--中华人民共和国应急管理部」）⇒ **整站已改成 JS 渲染** ⇒ 从 HTML 里找子栏目
这条路走不通。
⚠ 但同一站点的**法规**子栏目是好的：`/fw/flfgbz/fg/index.shtml` 实测 200 / 69394 字 / 有链接
（已配探针且 `ok`）⇒ 只有「标准公告」那一路是 JS 壳。
**结论（写进台账，不改探针）**：`ch:mem_gov` 保持 `suspicious` —— 这就是它今天真实的处境。
**R5 下一步**：① 找该站的 XHR/接口（像 flk 那样从打包产物里挖）；② 或用检索式入口；
③ 或退而用 `std.samr.gov.cn`（行标目录，已 `ok`）覆盖 AQ 的状态核验——因为 `routing` 本来
就把 AQ 路由到 `ndls` 而不是 `mem_gov`（R1 的 G9），所以**这条渠道今天的实际影响有限**，
不必为此阻塞其它轮次。

---

### R5b（2026-09-18 完成）：**govcn 换棒** —— 三棒降级链从"只有一根在工作"变成"两根"

**改法**（`src/core/update/channels/govcn_announce.py`）：旧实现只解 `isinstance(body, dict)`
（mock 契约），而它打的 `sousuo/…/search.shtml` 是 **HTML 搜索页** ⇒ 真实网络**恒 miss**（R1 的 G6）。
换成政策文件库的**真 JSON 接口** `GET https://sousuo.www.gov.cn/search-gov/data?t=zhengcelibrary&q=…`，
并**复用** `law_source/govcn_client.parse_rows` 做解析（响应形状的唯一所有者，不在本文件再抄一份
字段映射）；mock 分支保留（离线 fixture 仍走它）。另外 `_pick` 现在**同时看标题与摘要**——
真接口按 `searchfield=content` 检索时，命中通常落在 `summary` 里，只看标题会把真命中判成 miss。

**真机验证**（`var/tmp/verify-govcn-swap.py`，不是 stub）：

| 查询 | 结果 |
|---|---|
| `安全生产法` | **命中**：`found=True`、`evidence_url=https://www.gov.cn/zhengce/202609/content_7080621.htm` |
| `GB/T 30871-2022` / `AQ 3028-2008` | 未命中（政策库不索引标准号） |

⇒ **诚实的能力边界**（写进台账 note）：这根棒现在答的是"**政策文件库里有没有提到 X**"，
不是"这个标准号现行吗"。法规类管用，标准号基本查不到——但**总比"恒 miss"强**，
而且它本来就只是**第三棒兜底**。

**台账口径随之更新**：`wired 6 → 7`、`broken 2 → 1`（只剩 `web`）。
⚠ 我**同时改了那条断言**：原用例写的是"`web` 与 `govcn` 都必须是 broken"——换棒之后若还这么断言，
等于"宁可显示失效也不承认修好了"，那同样是虚报（只是方向相反）。现在钉的是
**`web` 仍 broken + `govcn` 已 wired 且 note 写明了能力边界**。
`ch:govcn` 的探针目标也改成真接口（锚点 `searchVO`，真机探针 `ok` / 1027ms）。
**门禁**：pytest **1918 passed / 3 skipped / 0 failed**、mypy **138/0**；
本步**没动客户端**（tsc/smoke 与上一步同状态，故未重跑）。

---

### R5c（2026-09-18 完成）：把 `web`（bing，第三根棒）**摘出链外** —— 三棒故事收口

理由（R1 的 G6 + R5b 的实测）：`WebFallbackAdapter` 只解 `isinstance(body, dict)`（mock 契约），
而它打的是 bing 的 **HTML 搜索页** ⇒ 真实网络**恒 miss**：每次探测白花一次请求，而且
**搜索引擎不是官方源**（与"不依赖二手信息"的准则相冲突）。它的角色已被两根**真**棒覆盖：
`official_gb`（国标全文公开系统）+ `govcn`（政策文件库真接口，R5b 换棒）。

改法：`routing._FALLBACK` 由 `("official_gb","web","govcn")` 改为 **`("official_gb","govcn")`**；
`inspector._FALLBACK_CHAIN` 同步（它用于"全都失败"时归因，`[-1]` 现在归到 `govcn`，比归到一根
从不工作的棒更准）；模块 docstring 同步。`ADAPTER_CLASSES` 里**仍保留** `web`（不删代码），
只是**不进任何链** ⇒ 台账口径是「**未接线**」而不是「已知失效」——
"失效"是"在链上但不工作"，"摘除"是"不在链上"，两者不能混。

⚠ 顺手记一条**重复所有者**（`inspector.CHAIN` 与 `routing._FALLBACK` 是同一件事的两份）：
本轮**只对齐、没删**（删常量风险大于收益），并在注释里写明"降级链的唯一所有者是
`routing.select_chain`，本常量仅为兼容保留"。→ R6 待办：确认无人引用后删掉它。

**台账口径（实机库）**：`wired 7 / unwired 11 / broken **0** / seed_only 113`；
已实测 🟢 22 / 🟡 1 / 🔴 5 / ⚪ 未探 103。
**新增用例**：`test_降级链里不再有已知失效的渠道`（`broken` 必须为 0，且 `web` 不许回链）——
把"链上每一棒都必须能用"变成可断言的口径。
**门禁**：pytest **1919 passed / 3 skipped / 0 failed**、mypy **138/0**（本步未动客户端）。
⚠ 全量跑第一次是 **3 failed**——	ests/test_update_routing.py 把旧链**写死**在 TRAIL 里
（("official_gb","web","govcn")）。这正是"摘除一棒"必须付的代价，已同批改该文件
（并把"为什么摘 web"写进它的模块 docstring，免得下一个人以为是随手删的）。
`docs/research/channels/REGISTRY-STATUS.md` 已重生成。

---

### R5d（2026-09-18 完成）：httpx 回退**自检** —— 把"两个栈都不可用"从静默失败变成点名报错

**问题**（G27，我自己的登记）：`default_transport()` 在 `curl_cffi` 不可用时只打一条 **WARN**
就回退 httpx。而本机实测 **httpx 连 `Client()` 都构造不出来**
（`NO_PROXY` 含 `[::1]` ⇒ `InvalidURL: Invalid port: ':1]'`）⇒ 那种环境下**每个渠道都会失败**，
现场却只表现为"每条都失败"（症状离原因很远，最难查的一类）。

**改法**（`channels/base.py`）：新增 `httpx_usable() -> (可用, 原因)`（构造一次 `httpx.Client()`
再关掉，把任何异常翻成一句人话）；`default_transport()` 回退前先自检——
**能用 → 照旧 WARN；不能用 → ERROR 并点名两个栈 + 附带可操作成因**（`NO_PROXY` 的 `[::1]`
改成 `::1`）。刻意**不抛**：抛出去会让引擎起不来；巡检照跑，但原因当场写进日志。

**真机证据**：`httpx_usable()` 在本机 = `(False, "InvalidURL: Invalid port: ':1]'")` ✓
**用例**：+3（可用/不可用两态、不可用时必须 ERROR 且日志含可操作提示、可用时只 WARN）。
**门禁**：pytest **1922 passed / 3 skipped / 0 failed**、mypy **138/0**（本步未动客户端）。

---

### R6a（2026-09-18 完成）：探针判据扩容 + **第一波覆盖率**（未探 103 → 29）

**这一步要解决的问题**：面板上 131 条里有 **103 条是 ⚪ 未探**——业主最想看的"有效性"这一列，
79% 是空的。而"补探针"不是体力活就能凑数的：锚点必须**实测看到过**（R3 的纪律），
否则就是把"猜"洗成"实测"。

**① 判据扩容（`channel_probe.py`）**：期望值从"单一文本锚点"变成**可叠加**的两种——
`expect`（文本）与**新增** `min_links`（HTML 链接数下限），任一不满足即不算通过。
理由是一条实测：应急部频道页 **HTTP 200 / 471 字节 / 0 链接**（R5a），标题却是好的
⇒ 只看状态码或只看 `<title>` 都会判成"健康"。R6a 批量实测又发现 **12 条**是同一形态
（人社部 / 工信部 / 浙江人大 / 浙江政府 / 国家标准委 / 电子工业标准协会 / 应急部 等）。
⚠ 这 12 条里 **11 条今天仍判 🟡**（`probe_too_few_links`）；第 12 条是 `ch:mee`——
它是 JSP 报表页、**本来就没有 `<a>` 链接**，所以改用手工实测的文本锚点（不配 `min_links`）后为 🟢。
另修一条口径：**429 从 `down` 改判 `suspicious/rate_limited`**——限流是"稍后再来"，
不是"这条渠道死了"（两条 GitHub 工具渠道实测 429，判死会让人白换渠道）。

**② 批量实测 + 配目标（`var/tmp/measure-channel-anchors.py` → `channel_probes.json`）**：
103 条未探里 **96 条有具体 URL**；给其中 **70 条**配上目标（law 28 / std_hb 13 / std_db 10 /
std_gb 5 / std_tb 5 / std_intl 4 / aggregator 5），每条都带 evidence（实测时间 / 出口 /
字节 / 链接数 / title 原文）。**目标表 28 → 98 条**。
**不纳入的三类**（理由写进脚本与本节，不隐式过滤）：
- **tool 24 条**：代码仓库/工具（GitHub、npm、Skill 站），不是采集通路；实测里两条就是
  GitHub **429 限流**——把限流显示成"渠道不可用"是误导。它们的"有效性"该用另一类判据
  （链接可达性），**本轮不做**，登记为待办；
- **internal 9 条**：url 字段是**端点描述**（含 `<占位符>`/多行/method），批量脚本只能取到
  第一个 http 串 ⇒ 实测出来是 400/404（我第一次就是这么量错的），留到 R6b 手工设计；
- 4 条含占位符 + 2 条无 http URL。

**③ 落库实测（`var/tmp/r6a-run-probe.py`，70 条真机探测）**：
首探结果 ok 47 / suspicious 14 / down 8 / unknown 1。台账口径随之变化：

| 口径 | R5d 结束 | **R6a/R6b 结束（实机库，复探后）** |
|---|---|---|
| 台账条数 | 131 | 131 |
| 能干活（wired） | 7 | 7（broken **0**） |
| 🟢 可抓 | 22 | **78** |
| 🟡 可疑 | 1 | **11** |
| 🔴 不可抓 | 5 | **13** |
| ⚪ 未探 | 103 | **29**（= 24 tool + 5 internal，**全部是"按设计无探针"**） |
| 探针目标 | 28 | **102** |

⚠ 上表是**复探后**的数字：首轮落库后我把当时 `down` 的 14 条**用同样的目标再探了一遍**
（查"红是不是抖出来的"），只有 1 条翻转（`cfsa`：证书校验时好时坏）⇒ `ok 77→78 / down 14→13`，
其余 **13 条两轮错误码逐条一致**（404/403/412/SSL/ConnectionError/202），
即"这些红不是瞬时抖动"；台账里它们的 `consecutive_failures` 因此为 **2**。

⚠ **本轮结束时的实测事实**：**凡配了探针目标的都至少探过一次**（`unknown ∩ 有目标 = ∅`）。
⚠ 但这**不是**"不变量"（独立复核 b28 纠正了我的措辞）：表里有 8 条**只探连通性**
（省略 `expect`）的目标，它们一旦回 200 就**合法地**记 `unknown/no_anchor_configured`
（"能连通，但我们没给它配语义期望"）——那是有目标的 unknown，**不是** bug。
真正该当 bug 的只有一种：**探测跑过却连 `last_try_at` 都没动**。

**④ 真机发现（都是实测，写在这里给下一轮用）**：
- **12 条 JS 空壳**（HTTP 200 + 0 链接）——`min_links` 判据正是为它们加的；
- **4 条 TLS/连接失败**：上海市司法局、企业标准信息公共服务平台、金融标准化技术委员会
  （BoringSSL 握手被拒）、ccsainfo（empty reply）；**1 条证书校验失败**（cfsa，且**时好时坏**：
  18:08 量到 200/56778 字节，18:2x 探针又报 transport_error ⇒ 记进台账的 `consecutive_failures`）；
- **2 条 403 / 1 条 412**（住建部政策发布 / 卫健委 = WAF）、**1 条 404**（交通运输部政策解读）、
  **1 条 202**（IEC，空体）；
- **`ch:mem_gov` 形态变了**：R5a 时 `/fw/flfgbz/bz/bzgg/` 是 471 字节 0 链接的 JS 壳，
  R6 复测 **29285 字节 / 113 链接**，且栏目页标题改成了「制度文件--中华人民共和国应急管理部」
  ⇒ 锚点按当时的正文原样重取（`suspicious → ok`）。
- **红是否可复现（R6a 尾）**：把 `down` 的 14 条复探第二轮 ⇒ **13 条同码**（真红），
  1 条翻转（`cfsa` 证书校验时好时坏 = 瞬时）。⇒ 台账的 `down` 不是"测一次就下结论"，
  `consecutive_failures` 从这一轮起有真实数据（13 条 = 2）。
  ⚠ **这个对照只能在这两个文件里复核**：首轮 `var/tmp/r6a-probe-run.txt`、二轮
  `var/tmp/r6-reprobe-down.txt`——因为 `record_probe` 是**覆盖写**，库里只留最近一次错误码
  （独立复核 b28 因此判此项 `UNVERIFIABLE`，措辞已按此收紧）。

**⑤ 我自己的一次翻车（必须留档）**：批量脚本把 `<title>` 做了**实体解码 + 空白折叠**再当锚点，
于是 `全部文件&nbsp;&nbsp;广东省人民政府门户网站` 被写成 `全部文件 广东省人民政府门户网站`
——**正文里根本没有那个串** ⇒ 3 条广东渠道（省政府文件库 / 粤府令 / 省司法厅）被误判 `probe_no_anchor`。
根因不是判据错，而是**锚点不是正文的逐字子串**。处置：
- 4 条（含 `mem_gov`）按**逐字规则**重取锚点并复探 ⇒ 全部 `ok`；
- 新增 `scripts/channel-anchor-measure.py`：把这条纪律**做成可执行的**——从原样 `<title>`
  里挑最长的不含空白片段，**先自检"它真的在正文里逐字存在"**再输出可粘贴的目标；
  支持 `--repair [错误码]`（默认 `probe_no_anchor`）批量重走台账里被标该错误的渠道；
- R6b 里我又差点犯同类错：`ch:mee` 的锚点我**从 URL 抄**了 `xmlname=1520238134405`，
  正文里其实没有这个串（判 `suspicious`）⇒ 改为逐字校验过的 `国家环境保护标准` 后 `ok`。
  **两次都是同一条纪律**：锚点只能来自正文，不能来自我的推断。

**用例/门禁**：`tests/test_channel_probe.py` 23 → **34**（`min_links` 不足/够、两期望叠加、
链接计数大小写与换行、429 判可疑、坏 `min_links` 读表即抛）；
`tests/test_update_routing.py` +1（降级链**单所有者**，见下）；pytest **1935 passed / 3 skipped / 0 failed**、
mypy **138/0**、tsc **0**、smoke **EXIT=0**（22 段）、`verify:commands` **22/22**、
`verify-engine-uvicorn` **4/4**。

---

### R6b（2026-09-18 完成）：我方通路探针 + **"未探"的两种处境**看得见

**① 顺手还掉 R5c 的欠账（降级链只剩一份）**：删掉 `inspector.CHAIN`（与 `routing._FALLBACK`
重复的字面量，已无人引用：只有 `update/__init__.py` 在转出它），并让
`inspector._FALLBACK_CHAIN` **向唯一所有者取**（新增 `routing.fallback_chain()`，返回同一个
tuple 对象）。R5c 那次"摘一棒要改两处"的教训由此变成**代码约束**：
新用例用 `is` 钉住同一对象，任何人再抄一份都会红。`src/core/update/__init__.py` 的 `__all__`
里保留了说明（为什么删、去哪取）。

**② 我方通路（internal）手工配探针**：新增 4 条**实测**目标，method/body **抄适配器里
实测跑通的那一版**（不是我想的）：

| 渠道 | 目标 | 锚点（逐字实测） |
|---|---|---|
| `ch:ndls` | `POST /api/standard/list`（JSON 体抄 `ndls.py:_search_body`） | `visitToken` |
| `ch:ttbz` | `POST …/getPortalStandardList`（表单 `pageNo/pageSize/searchKey`） | `standardUniqueId` |
| `ch:ccs_fetcher` | `GET /api/standards/list?keyword=GB%2030871` | `a104name` |
| `ch:mee` | `POST datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=…` | `国家环境保护标准` |

⚠ **第一次探 `ch:ndls` 用 GET 得到 404**——正是 R3 记过的"method 不传就静默变 GET"；
`ch:ccs_fetcher` 的台账 url 记错了（`/api/cssn/list` vs 实测 `/api/standards/list`），**顺手修正**。
**5 条按设计不探**（登记在报告第四节）：`ch:flk_client` / `ch:govcn_client`（与 `ch:laws_db` /
`ch:govcn` 是**同一端点**，重复探没有新信息）、`ch:announce_sources`（用户自配列表页，没有固定
目标）、`ch:web`（已从链上摘除）、`ch:discover_search`（记录里的 `openstd…/db/search` 实测 404，
入口地址待重找——**不拿我猜的地址去判它"不可用"**）。

**③ 把"⚪ 未探"拆成两个处境**（业主"人工维护"的直接需求）：
`GET /api/v1/channels` 每条新增 **`has_probe_target`**（按**探针目标表**算，不往数据库塞第二份真相），
单条详情同样带；面板在"有效性"列对 `unknown && has_probe_target === false` 标
**（无探针）**并说明"这不是'还没轮到它'"；`scripts/channel-status-report.py` 第四节也拆成
「已配探针、还没探过」与「按设计没有探针目标」两栏并列出后者。
**用例**：`test_channel_repo.py` +1（逐条与目标表对齐、两个方向都要有实例）；
smoke `catalog-ui` 43 → **45**（未探行的两种处境、api.ts 类型字段）。

**还没做**（留给下一轮，**不是本轮遗漏**）：
① tool 类 24 条的"链接可达性"判据——**本轮量了、但决定不并进探针表**（理由见下）；
② `ch:discover_search` 的入口地址重找；
③ 每轮探针的**出网模式**（direct/env-proxy）落进台账（G28，仍只在 evidence 文字里）；
④ §4 表里的 **R6c：五类监控打通**（发布/修订/废止/现行性/编号核验 + 巡检读台账选链）。

**R6c 前哨（tool 类，只量不配）**：`var/tmp/measure-tool-liveness.py` 对 24 条 tool 里的
**18 个不重复 URL**（覆盖 20 条渠道）各打了一次：
- **16 个今天 200**（GitHub 仓库页 / npm 包页 / clawhub Skill 页），且能取到**逐字**锚点
  （如 `LoyDgIk/GBMCP`、`govping-mcp-server`、`thp/urlwatch`）；
- **2 个是 GitHub 搜索链接**（`github.com/search?q=GovPing`、`?q=china-law-search`）——R1 当时按
  项目名没解析出仓库，于是记了搜索页；今天回 **429**。**这是"登记本身该修"，不是"渠道不可用"**。
- ⚠ 顺手抓到一类**锚点陷阱**：429 的错误页正文里也含 `requests` 这种词，脚本的兜底规则
  （取 `<title>` 最长片段）会给出**看起来像锚点、其实毫无判别力**的串
  （另一条给出了 `Security`）⇒ 规则已写死：**非 200 的正文一律不取锚点**。

**为什么本轮不把 tool 并进探针表**（决策记录）：探针表的语义是「**这个采集通路**今天能不能抓到
东西」；tool 是**代码仓库/工具站**，它答的只能是「这个链接还在不在」。并进去会让面板顶部的
"🟢 可抓"把仓库链接**算成渠道能力**——那正是 R1 的 G5/G6 要防的"覆盖率虚高"（形状换了一种）。
要做也应该是**另一组**（例如"链接可达性"单独一栏、或只在详情里显示），而不是塞进同一列。
数据已经量好（上面 16/18），要做随时可以，成本一轮。

**真机复验（CDP，`var/tmp/gui-channels-r6b.png`）**：刷新页面 → 设置 → 法规标准知识库 →「渠道台账」——面板仍正常挂载（引擎侧端点仍是旧进程 ⇒ 表格显示
`读取失败：HTTP 404（渠道台账端点要宿主/引擎重启后才在线…）`，不是空白）。
⚠ 顺手又抓到**我自己**在 R6b 新写的说明文案里把 markdown 粗体当成了渲染语法
（`**（无探针）**` 带星号原样显示——JSX 不渲染 markdown，这与 R4b 修过的 7 处是同一类问题）。
处置：改为「（无探针）」，并在 `smoke-catalog-ui.mjs` 加了**闸门**（去注释后源码不许出现 `**`），
用旧版源码做过**变异验证**（旧版命中 1 行 ⇒ 闸门会红）；catalog-ui 45 → **46**。



---

### R6b 复核（独立 verifier b28，2026-09-18）——6 条声明 5 成立、1 条"措辞比证据强"

报告：`var/tmp/VERIFY-b28.md`。**它抓到的两条是真问题**（都落在"我声明得比证据强"这一类）：

| 复核发现 | 处置 |
|---|---|
| **① `expect=""` 是假绿口子**：`_classify(200, "", "")` ⇒ `ok`（`"" in body` 恒真，连空正文都判可抓）。不是本次新引入（R6 前同款），但我说"没有假绿口子"是宽读法 | `load_targets` 新增**逐字段校验**：`expect` 必须是非空字符串或**省略**（"只探连通性"就别写 expect）；写成空串**读表即拒**。新增用例 10 条（含把"为什么必须拒"钉成证据的那条） |
| **② 目标形状不受校验**：把 target 写成**字符串**能静默过表，随后 `probe_channel` 抛 `AttributeError`；`expect=123` 抛 `TypeError` ⇒ "探针不抛异常"当时只对**恰好写对**的目标成立 | 同上：`_validate_target` 校验对象/`url`(http)/`method`(get,post)/`expect`/`min_links`/`form`/`json`/`headers`；并把 `probe_channel` 的 docstring 改成明说**契约前提**（未经校验的裸 dict 不保证不抛） |
| **③ "unknown ∩ 有目标 = ∅ 是不变量"是时点巧合**：表里 8 条只探连通性的目标一旦回 200，就会**合法地**记 `unknown/no_anchor_configured` | 措辞已收紧为"**本轮结束时的实测事实**"，并写明那是有目标的 unknown、**不是** bug；真正该当 bug 的只有"探过却连 `last_try_at` 都没动" |
| **④ 删 `inspector.CHAIN` 把 `docs/research/channels/internal-inventory.md:19` 变成错的**（它仍写"CHAIN 是遗留常量"） | 在该文件加 **2026-09-18 更新块**（说明 CHAIN 已删、唯一所有者是 `routing.fallback_chain()`；顺带注明同段的 `web` 已被 R5c 摘除），**原文保留不删**（它是 R1 当时的记录） |
| **⑤ `routes_channels.py` docstring 还写"只探配了目标的渠道（28 条）"**（本轮已 102） | 改成不写死数字："数量随目标表变（R3 时 28 条，R6 后 102 条）" |
| **⑥ 事故文档里的标记路径已过期**：处理完 `pending-incident.json` 被重命名为 `resolved-incident-<ts>.json`（复核实测）；"stderr 被覆盖"措辞也偏强 | 文档已注明重命名；措辞改为"**被复用而丢弃**（机制可证：三处传同一对路径；'当时确实写过内容'不可观测）" |
| **⑦ 它判 `UNVERIFIABLE`**：我说的"13/14 两轮逐条同码"无法从库复核（`record_probe` **覆盖写**，首轮错误码已不在库里） | 已在 ledger 明写：这个对照**只能**在两个 `var/tmp` 文件里核（`r6a-probe-run.txt` 首轮 / `r6-reprobe-down.txt` 二轮），措辞按此收紧 |

**它给出的旁证（值得留档，因为它独立跑过真机）**：
- 14 条真机重放**全中**；3 条广东锚点 `verbatim=true` 而"实体解码后的串 = false"⇒ **旧写法必错**（我的翻车被独立复现）；
- 9 条实测链接数与 `evidence` 记录**逐条一致**（77/78/108/113/146/185/54/0/0）；4 条 0 链接页去标签后只剩标题（**真壳**，不是假红）；
- 真库打真 API：131 条**全带** `has_probe_target`、与 `load_targets()` mismatch **0**、`PRAGMA table_info` 无此列；
- 坏 `min_links` 的 9 种写法（含 `[]`/`{}`/`False`）**全部读表时 ValueError**（比我只测的 5 类更宽）；
- 事故复盘：`Wait-Healthy` 第 105 行、日志路径 63–66 只算一次、快照 `20260905-110225-811` **全盘递归只剩 4 处引用、无目录** ⇒ 与"轮换删除"结论自洽，且原因与 `dsh-fuhuobi/src/engine.js` 的三级旋转 + `markReviveCoin` 删旧目录的代码对上。
**复核后的门禁（本步只动引擎侧校验 + 用例，未动客户端）**：pytest **1945 passed / 3 skipped / 0 failed**
（1935 → +10：坏形状 9 条 + "为什么必须拒"1 条）、mypy **138/0**。
⚠ 首次全量跑出现 **1 failed**（同一提交重跑 **1945 passed**）⇒ 判定为**既有 flake**，
但**我没抓到是哪条**（两次抓失败详情时把输出过滤掉了）——这是流程缺陷，
已在下一次全量里改成**整份输出落盘**（`var/tmp/pytest-full-captured.txt`）。
**收尾时改正的一条口径（实测）**：面板要看到 `has_probe_target`，需要的是**重启宿主**
（宿主插件 `plugin/src/channels.js` 是今天新加的，宿主的 `/ks/channels*` 路由不存在 ⇒
面板拿到的是**宿主** 404，引擎根本没被问到）。引擎是**按需懒启动**的，实测此刻**没有活着的引擎**
（session 文件指向 pid 30836 @18:17:07，进程已不在；端口 2036 无监听）⇒ 宿主重启后 spawn 出的是
**当前代码**的引擎。⚠ 只有"重启时恰好有旧引擎活着被复用"才需要再重启引擎。
（原先把这条写成"引擎+宿主重启"，是把宿主的问题错记成引擎的——已改。）
⚠ 补一条**证据耐久性**（自查）：上面说的两个对照文件在 `var/tmp/`，**没有进 git**
（该目录被忽略）⇒ 一旦被清理，这条"两轮同码"的对照就只剩本节文字，无法再复核。
结论已写全（13 条同码 / 1 条 cfsa 翻转），但**"原始输出"与"结论"的可信度不同**，故注明。

---

### R6b 复核第二轮（b28-fix，2026-09-18）：它抓到四条"**修完仍会误分类**"的，已全部修

第一轮修的是"会抛异常"；第二轮复核员把攻击面换成了"**不抛、但把配置错误记成渠道故障**"，
于是又抓到四条（报告 `var/tmp/VERIFY-b28-fix.md`）：

| 复核发现 | 处置 |
|---|---|
| **N2 `url` 用 `startswith("http")` 前缀判断**：`"http"`/`"httpfoo"` 过表 ⇒ 记成 `down/transport_error`（**配置写错伪装成渠道挂了**）；反过来合法大写 `"HTTP://e.com"` 被**误拒** | 改用 `urlsplit` 判 scheme+netloc（大小写不敏感）⇒ 前者读表即拒、后者不再误拒 |
| **N3 `headers` 只校验"是对象"**：值为 list/dict 时过表 ⇒ 同样记成 `down` | 值必须是 `str→str`，且名/值都不含 CR/LF（**顺手堵住头注入**） |
| **N4 `json` 只允许 dict**：顶层是**数组**的 POST 体被误拒（今天 2 条都是 dict，无影响） | 允许 dict 或 list |
| **S1 `json.dumps` 在 `try` 之外**：transport 返回不可序列化 body 时会从 `probe_channel` **逃出去** | 移进 `try` ⇒ 记 `down/bad_body`；并把 docstring 的"不抛"契约补上**第二条前提**（响应体可序列化） |
| **N1 两处消费端仍按旧读法**：状态报告把"有目标但只探连通性"叫「还没实测/欠账」、面板表尾写"⚪ 未探 = 还没测过" | 报告改**三分**（欠账 / 只探到连通性（`no_anchor_configured`）/ 按设计无探针）；面板表尾补第三种 ⚪ 的说法 |
| 第 13 条：`probe_channels` docstring 写"没配的记 `unknown/no_probe_target`"，**代码里没有这条写入** | docstring 改为与代码一致：没配的被**跳过**、不写库、只出现在返回值的 `without_target` |
| 它的建议：**校验未知键**比"单独拒 `null`"更值（能一起抓 `expext` 这类拼错） | 采纳：新增 `_TARGET_KEYS` 白名单，未知键**读表即拒** |
| `expect: null` 的判定 | **保持合法**（→ `unknown/no_anchor_configured`，**不是**假绿）；复核实测发布表 22 条缺失**全是省略键**、显式 null **0 条**，8 条只探连通性的每条都有 note/evidence |

**闸门自证（第二轮）**：我新写的面板说明里**又**把 markdown 粗体当渲染语法 ⇒ R6b 加的那条闸门
**当场红**（46 项里 1 红，报出行号与原文），去掉后 46/46。**一条闸门连续两次抓到同一个我** ——
这就是它的价值。
**复核的回归**：三文件 104 passed（44+50+10；它按 brief 猜的 49 实际是 50）；全量两次
**1945/3/0** ⇒ 首跑那条 `1 failed` 未复现（**仍未点名，留作欠账**）；
本步加完用例后全量 **1959 passed / 3 skipped / 0 failed**、mypy **138/0**、tsc **0**、smoke **EXIT=0**。
**关于那条"已知 flake"，本轮终于有了更准的说法（证据）**：`smoke-chatmode` 失败**两次**都是在
**与全量 pytest 同时跑**的时候（172/173），而**单独跑 4 次全绿**（173/173，含整条 smoke 链
`EXIT=0`、14 段全 PASS）；本轮先前那次 pytest `1 failed` 也是在与**复核员的另一次全量**
并发时出现的。⇒ 说法收紧为：**这些 flake 与"同时跑多份重活"相关**（机制推测：文件锁/时序敏感，
未证实因果，样本 2 失败 vs 4 成功）。**操作纪律（写进本方案）**：
**门禁要一次只跑一个**——并发跑门禁会给自己制造假红。
**本轮（R6a/R6b）提交与快照索引**（下一轮要回看时按这个找）：
`e7fb13d` = R6a/R6b 主体（快照 `step-112-r6a-r6b-probes`）；
`5a214fc` = 面板文案 markdown 粗体修复 + 闸门（`step-113-r6b-caption-gate`）；
`c9f2987` = 复核 b28 第一轮的两条真问题（`step-114-b28-fixes`）；
`4512e97` = 复核 b28-fix 的四条误分类 + 两处消费端（`step-115-b28fix2`）；
`fcb0b59` = 事故复盘文档；其余为文档修正（口径/证据耐久性/门禁纪律）。

---

### R6b 复核第三轮（b28-fix2，2026-09-18）：一个**真反例** + 一个同类窄口 + 两处 doc 小口，已修

第三轮把攻击面再换一次：**"过表之后真请求会不会炸"**（不是"会不会抛"，而是"会不会在真机上变成
`down`"）。它跑了真 transport（还起了本机临时 HTTP server）来验，报告 `var/tmp/VERIFY-b28-fix2.md`。

| 复核发现 | 处置 |
|---|---|
| **NEW-A（本轮唯一真反例）header 值含非 ASCII**：`{"X":"中文值"}` 过表 → 真请求 `UnicodeEncodeError: 'latin-1'`；`{"X":"a\x85b"}` → `UnicodeDecodeError` ⇒ 记成 `down/transport_error`（**又是配置错伪装成渠道挂了**） | 值加 `value.isascii()`。⚠ 对照实测：`\t`/`\x0b`/`\x01`/`\x7f` 这些 ASCII 控制字符**发得出去、200** ⇒ **不动** C0 的既有宽松度（只禁 CR/LF + 要求 ASCII） |
| **NEW-B `http://:80/` / `http://e.com:99999/` / `http://e.com:port/`** 过表 → `down` | 改 `parts.hostname` 非空 + `try: parts.port`；并补 **6 个合法 URL 回归**（大写 scheme / userinfo / 中文域名 / 带端口 / 回环 / 查询串）钉住"不误伤" |
| 报告第四节标题写「**还没实测**的渠道」，里面却已装"探过、只探到连通性"这一类 | 标题改「**还没定论**的渠道」 |
| 两处注释/类型说明仍只写**两种**处境（`routes_channels.py`、`api.ts`） | 都改成三种，并写明 ②（`no_anchor_configured`）怎么与 ①③ 分辨 |
| **NEW-C（脚注）**：`bad_body` 分支里 `str(body)` 若对象 `__str__` 自己会抛，仍会逃逸 | 包一层 try，退化成 `<类型：连 str() 都抛异常>` |
| 既存脚注（非本次引入）：报告脚本传**相对**输出路径时 `relative_to(ROOT)` 抛 ValueError（文件已写出、退出码非 0） | 打印处包 try，**打印失败不影响产物** |
| `expect: null` 该不该关？复核员**两轮都判"不该"** | 采纳：保持合法（→ `unknown/no_anchor_configured`，**不是**假绿）；白名单已堵住真正的残留（拼错键静默退化），比单独拒 null 更值 |

**复核给的独立证据（值得留档）**：
- N1 的三分它在**隔离临时库**里端到端验过（建 3 条 → 真跑 `probe_channels(persist=True)` → 真跑报告脚本
  ⇒ 1/1/1 三分正确；且"用 `last_try_at is None` 判"与"用 `last_error_code` 判"**等价**）；
- N4 它用**本机临时 server** 证明 `json=[]`/`[[1]]`/`[{"a":1}]` **真的发出去了**（不是"没抛就算"）；
- 白名单与发布表实际 9 键**完全相同**，判定＝刻意的 fail-closed 过严（取舍正确）；唯一成本是新增字段要同步白名单；
- 把报告脚本对**真库**再生到 `var/tmp` 与提交里的 `REGISTRY-STATUS.md` 比对 ⇒ **除"生成时间"一行外逐行相同**
  （证明那份快照确实是脚本生成的，不是手改的）。

**门禁（按 §5 第 8 条**单独**跑，不并发）**：smoke 链 **EXIT=0**、pytest **1970 passed / 3 skipped / 0 failed**
（1959 → +11）、mypy **138/0**、tsc **0**。
索引续（第三/四步）：`5a923fd` = 复核 b28-fix2 的处置（快照 `step-116-b28fix3`，**标签已核对**）；
`8ca72e1` = 记录"commit 与 tag 同一行会让快照落到旧提交"这一坑。
⚠ 快照标签的核对方法：`git rev-parse --short <tag>` 必须等于 `git rev-parse --short HEAD`（本轮做过两次）。

---

### R6b 复核第四轮（b28-fix3，**收官**）：判定「R6 探针这块**可收口**」+ 三件边角收掉

| 边角（复核留的） | 处置 |
|---|---|
| `http://e.com:0/` 过表 ⇒ **必然** down（`urlsplit().port == 0` 在范围内不抛；0 是 IANA 保留、没有服务器能监听） | 拒掉（一行 `port < 1`）。⚠ 同时**保留**空端口 `http://e.com:/` 为合法——复核用 curl 实测它按默认 80 连（`127.0.0.1:/` → "Failed to connect to 127.0.0.1:80"），所以**不拒空端口**，并把这个取舍写进 docstring |
| host 混入空格 / `%zz` / 内部 tab 仍会过表 → down | **刻意不追**（要真正的 host 字符集/IDNA 校验，成本与收益不匹配；发布表 102 条里没有这种写法）⇒ 写进 `_validate_target` 的「已知边界」段，**不假装已解决** |
| `docs/research/channels/REGISTRY-STATUS.md` 自称"自动生成，勿手改"却**没随生成器再生**（真库再生后只差 2 行：生成时间 + 第四节旧标题） | 重新生成（第四节标题同步为「还没定论的渠道」） |

**复核给的独立证据（它自己动手验的）**：
- NEW-A **无误伤**：`\xff`/`\x80`/`\xe9`（latin-1 范围内、理论上可编码）在真 transport 下**也**一律
  `UnicodeDecodeError` ⇒ `isascii()` 这条线**没拒掉任何能用的值**（`\t`/`\x0b`/`\x01`/`\x7f` 照过且 200）；
- 隔离临时库 e2e：三种处境的真实行是 ① `has_probe_target=False / unknown / NULL`、
  ② `True / unknown / no_anchor_configured`、③ `True / unknown / NULL` ⇒ 与注释**逐条对得上**，
  报告脚本三分复算仍 1/1/1；
- 报告脚本传相对路径 → **EXIT=0** 且产物在；`__str__` 抛异常的对象 → 不逃逸（`bad_body` + 占位 body_head）；
- **真库全程未被改动**（复核前后 `summary` 都是 131/78/11/13/29，`max(last_try_at)` 仍是复探的 10:18:36）。

**收口**：三轮抓到的三处真反例（`expect=""` 假绿 / 目标形状不受校验 / 非 ASCII 头值）都已修并逐条复验；
三个"不抛但会误分类"的口也都堵住。⇒ **R6 探针这块收口**。
**门禁**：smoke 链 **EXIT=0**、pytest **1973 passed / 3 skipped / 0 failed**、mypy **138/0**、tsc **0**。

---

### R6c-1（2026-09-18 完成）：**五类能力表**补齐（68/131 → 131/131）+ 台账链的"只算不改"快照

**这一步解决问题的哪一半**：设计稿 §3.2 的前置欠账是"哪条渠道能答哪几类只覆盖一半"。
本轮补完，并顺手把 §3.1 的链规则**先算出来给人看**（不动巡检行为）。

**① 补齐方式（谁判、依据什么）**：63 条缺口按"能不能查"切成四组，A/B/C 三组**派子代理逐条判**
（各自只读调研文档 + 适配器代码 + 探针表，写 `var/tmp/answers-*-result.json`，父代理只读摘要），
D 组按规则判：

| 组 | 条数 | 结果 |
|---|---|---|
| A 法规族 | 18 | **17 条空**（403/404/JS 空壳/需浏览器会话态/转发器），1 条 `["发布"]`（浙江省人大，medium） |
| B 标准族 | 20 | **全空**——其中 18 条 `std-cn.md §7` 的机读附录**本来就写着 `"answers": []`**（B 组因此几乎没产出新声明（20 条里 18 条只是搬运，另 2 条确属新调研）） |
| C 其它/聚合 | 7 | **全空**（6 条 tool + 1 条聚合入口；原因：闭源/外法域/查无此物/无公开列表端点） |
| D 工具类 | 18 | 规则判"不参与五类"（不是采集通路） |

**合成产物**：`src/core/update/channel_answers.json`（131 条，每条带 `basis` + `confidence` + `source`）
+ `src/core/update/channel_answers.py`（`CLASSES`/`answers_of`/`channels_for(only_ok=)`/`coverage`）
+ `scripts/answers-matrix.py`（人可读矩阵：每类由谁答、今天活没活）。
**分布**：来源 `{R1-seed 68, R6c-1-A 18, R6c-1-B 20, R6c-1-C 7, R6c-1-D-rule 18}`；
每条能答几类 `{0类 62, 1类 24, 2类 15, 3类 9, 4类 9, 5类 12}`；
每类渠道数 `发布 64 / 修订 30 / 废止 27 / 现行性 26 / 编号核验 30`。

**② 本轮定的两条口径（写进设计稿 §3.2，免得后人重吵）**：
1. **mock/fixture 才供数的字段不算能力**。反例：`discover.py` 的卡片契约确实读 `item["status"]`，
   但只有离线 mock 会填、真实通路无解析 ⇒ `ch:discover_search` 判 `answers: []`（medium）。
   （同一条教训见 R1 的 G6/G14：**看起来有字段 ≠ 真能拿到**。）
2. `answers: []` 有两种含义——**非状态渠道**（聚合/下载/工具）与**页面取不到、能力未证实**
   （403/404/JS 空壳）；分辨看 `basis` 与台账 `state`，**别把后者读成"这条渠道没用"**。
⚠ 68 条 R1 声明标 **medium**：**调研期声明，本轮未逐条复核**（升 high 需适配器代码级证据）。
这是诚实边界，不是偷懒——表里 `basis` 写明了它们没被本轮复核。

**③ 子代理顺手报回的两件事（登记不夹带）**：
- **重复行（G26 的实例）**：`seed:law-cn:浙江省人民政府-省政府文件` 与 `-省政府文件栏目`
  **同 URL 同 note**（探针表里也各有一条指同一 URL）；A 组还报出浙江人大一节
  "首页是 JS 空壳"的自我更正痕迹。**本轮不去重**（删台账行是数据变更，要单独决策），
  只登记；R6c 选渠道时按 URL/能力去重。
- **一条口径分歧点**：3 条（政策文件库检索 / 应急管理部-法律法规 / 浙江省司法厅）的调研文档
  "能回答"行带 ⚠️ 但同节实测**取不到条目** ⇒ A 组按"取不到就不写"判空。**我确认这个口径**
  （弱信号不算能力），并把这条写进 §3.2 的口径里。

**④ §3.1 的"只算不改"**：新增 `src/core/update/channels/ledger_chain.py`（纯函数：台账只做
**硬过滤** `enabled=0`/`wiring='broken'` 与**报告**，成员资格是**显式名单**）
+ `scripts/chain-snapshot.py`（今天的链 vs 按台账过滤后的链、被挡住的渠道、可提升的候选）。
**快照当场抓到我第一版规则的错**：把 `wiring='wired'` 全当兜底成员 ⇒ **9/9 个样例号的链都变**
（5 条前缀专用渠道被拖进泛查链，泛查链 2→7 条）。已改，并在模块 docstring 里写明
**"wired ≠ 兜底成员"**与**循环问题**（`wiring` 本是反查 routing 得到的，拿它当链来源就成了回声）。
现在真库快照：**过滤后 = 今天的链（0/9 变化）**，5 条候选被**列出来**而不是被悄悄提升。

**用例/门禁**：`tests/test_channel_answers.py` 13 条（覆盖齐全/词表封闭/两条口径/能力≠可用性）、
`tests/test_ledger_chain.py` 14 条（硬过滤、wired≠roster、候选报告、代码/台账不一致、真库无差异）；
全量 pytest **2000 passed / 3 skipped / 0 failed**（首跑 1999+1 flake，见下）、mypy **140/0**。

**门禁与一条 flake 的点名（本轮的重要副产品）**：
全量 pytest 第一次 **1999 passed + 1 failed**、第二次 **2000 passed / 3 skipped / 0 failed**、
mypy **140/0**。那条失败是
`tests/test_answer_materials.py::TestAnswerIntegration::test_scoped_answer_injects_materials_and_records_usage`
（`assert None == {"output_dir": "…/out9"}` ⇒ 一处快照产出没落地），**单独跑通过、第二次全量也通过**
⇒ 频率约 **1/3**，与本次渠道改动**无关**（它在文件顺序上**早于**本轮新增的两个测试文件）。
⚠ 这**很可能**就是我前几轮"知道有 flake 却叫不出名字"的那一条（当时没记名字 ⇒ **不能证实**），
今天这笔账**部分还清**：至少名字与现象钉住了。**不顺手改它**（属另一条线，且需要单独的根因分析）。

**复核 b29（独立 verifier，2026-09-18）**：6 条声明 **5 成立 + 1 条"措辞比证据强"**（报告 `var/tmp/VERIFY-b29.md`）。
它抓到两处，都已修：

| 发现 | 处置 |
|---|---|
| **① 引错证据行**：`seed:law-cn:浙江省人大` 的 `basis` 写"附录同条 answers=["发布"]"——law-cn.md §10 附录里 `浙江省人大` 是 `[]`，`浙江省人大-首页` 才是 `["发布"]`。**取值本身站得住**（§6 散文 L463 有实测），错的是引用 | 改引 §6 散文并写明"附录对应行是 -首页"；`var/tmp/merge-answers.py` 里加了 `BASIS_FIX` 覆盖，**重生成不会退回旧错** |
| **② docstring 承诺没实现**：`ledger_chain.py` 写"名单里有、代码里没有的名字会被报出来"，但 `known` 是死参数（`_ = known`）、`missing_in_code` 只看 `wiring=='wired'` 的台账行 ⇒ 显式名单里的 `nope_x` **静默留在链里** | 改成 **fail-closed**：名单里没有适配器的名字**不进链**，并由新增的 `roster_missing_in_code` **点名**（本地快照脚本也打印）；新增用例钉住 |

**它顺带纠正的两处口径（我采纳并已改文档）**：
- **C 组 7 条不等于全是工具**：其中 6 条是 tool 类、1 条是**聚合入口**（浙江省政策文件库）；
  "24 条 tool 全空"里 18 条走 D 规则、6 条走 C 组逐条判。
- **B 组那句"缺的不是调研而是搬运"要改成"主要缺的是"**：20 条里 18 条命中 `std-cn.md §7`
  机读附录（且附录里本来就是 `[]`），另 2 条（`ch:ccs_fetcher`/`ch:discover_search`）
  **确属新调研**。⚠ 附录行**没有 id**，靠 name 匹配（脆弱）——这是它的保留意见，我记下。
- 保留意见二：**R1 那 68 条的 `basis` 不指逐条证据**（只写"未逐条复核"）且标 medium ⇒ 表里
  "有出处"对这批是**弱的**。已在 JSON 的 `note` 里写明，不当作"已核"。

**复核的独立复现**（它自己跑的命令）：131=131 一一对应（seed-only/answers-only/dup 全 0）、
四字段缺 0、词表越界 0、来源与置信分布逐位相同；`discover.py:516-517` 只吃 dict 契约而
`:550-551` 确读 `status`、唯一填 `status` 的是 `tests/fixtures/discover_web.json` ⇒ **判空正确**；
抽查 **16 条**逐条对原始证据，**未发现站不住的声称**（方向普遍更保守）；R1 的 15 条 `ch:*` 与
internal-inventory 附录集合比对 **0 不一致**；链快照**过滤后=今天两棒、0/9 变化、候选正好 5 条**，
并**对抗性**验证了 `enabled=0`/`wiring='broken'` 会让成员掉出、`state='down'` **不会**。
**全量单跑 2000 passed / 3 skipped / 0 failed（199.45s），无 1 红**——那条 flake 本轮未复现，
它明确说"不能据此推断已消失"（我同意）。

**复核 b29 第二轮（b29-fix，2026-09-18）**：判 **R6c-1 可收口**，但又抓到一处——**我新写的那句 basis
"反向过度声称"**：我改成"其余四类该节明确 ❌"，而所引 law-cn.md §6 该小节原文是
「发布 ✅（经由 /sylf/fggg/）/ 其余 ⚠️」（该小节 ❌ 出现 **0** 次、⚠ 3 次）⇒
**把弱信号说成了硬否定**（与第一轮同一类错的反向复发）。已改为
「其余四类该节标 ⚠️（弱信号）⇒ 弱信号不算能力，故不声明」，并在 basis 里**写明这次更正本身**。
它另外确认了重生成不回退（把生成脚本拷到 var/tmp 重跑 ⇒ 与仓库 JSON **逐行 IDENTICAL**）。

**它给的 3 个小反例（都修了，不留给下一轮）**：
① 名单重复成员不去重不告警 ⇒ 现在**去重 + `roster_duplicates` 告警**；
② 名单成员在台账里没有行 ⇒ 保留（fail-open）但新增 `roster_not_in_ledger` **提一句**；
③ 值形状严格比较（`wiring='BROKEN'`/`'broken '`、`enabled='0'`）⇒ 现在**归一后判**
（`_wiring` 去空白+小写、`_enabled_off` 容忍 `0`/`'0'`/`False`，但**不**把 `None` 当停用）——
那正是"配置写错伪装成渠道可用"的又一例，收在函数边界上比留给巡检好。
用例：`tests/test_ledger_chain.py` 15 → **23**。

**它的保留意见（我照记）**：直接 `mypy .` 会被 `var/tmp/before-tree-b16` 那棵历史备份树绊倒
⇒ 项目门禁用的是 `files=["src"]`，**var/tmp 的残留不该进门禁**（下次清理时要留意）。

**复核 b29-fix2（第三轮，收官）**：判 **R6c-1 可以最终收口**。它只剩一处**同类小反例**并已被我修掉：
`_enabled_off` 的字符串分支漏了 `.lower()` ⇒ `enabled='FALSE'` 不算停用（而 `'false'`/`'False'` 算）
—— **同一个函数里两种口径**是最难查的那类不一致，已统一成"先去空白再小写"。
顺带修掉它记的两个潜在坑：① 报告字段对重复成员会重复列 ⇒ 改用**去重后的名单**；
② 传**生成器**当名单会让 report 后半段空掉、并把名单里的成员误报成"可提升候选" ⇒ 入口 `_as_tuple()` 固化。
用例：`tests/test_ledger_chain.py` 23 → **30**（含 `'FALSE'`/`' False '`、生成器名单、重复成员报告不重复列）。

**它核实了我的自记**：`4fcf89f` 是 `--amend`（前身 `9dd3dc7`），diff 正是那行去重写法；
它把同一个 idiom 放进最小文件**复现了 mypy 的 `func-returns-value`**，并确认旧写法**语义正确**（用例必绿）
⇒ "**用例全绿 ≠ 门禁全绿**"这个实例**站得住**，已写进文档。
**它的独立复现**：36 passed（23+13）、全量 **2009/3/0**（它跑的）、mypy 140 files 0 error、
快照仍 **0/9 + 候选 5 条**、生成脚本重跑与仓库 JSON **逐行 IDENTICAL**、131=131 与各计数不变。
**本步门禁**：pytest **2016 passed / 3 skipped / 0 failed**、mypy **140/0**。
⚠ **这一处 `.lower()` 未再派复核**：复核员已判定它"不构成阻塞、一行即可"，且我按它的建议逐字改（另有 7 条用例覆盖）。
**R6c-1 至此收口。**

---

### R6c-2a（2026-09-18）：**先量再决定**——量出来的结论是"提升渠道"这个杠杆**用错了**

**要决定的问题**：要不要把 `ndls` 这类**前缀专用**渠道提升为泛查兜底成员（好处：泛查更容易命中；
代价：每号最多 +5 次请求，万级巡检的预算与耗时都会变）。我的推荐是"先不提升、先量"，本步就是那次量。

**方法**（刻意可复现、不挑样本）：真库 `doc_meta` 里取**走泛查兜底**的号 → 按 `doc_id` 等距抽样 12 个 →
对每个号跑 3 根（`official_gb` / `govcn` / `ndls`），记录 `found/captcha/legal_status`。

**第一轮结果**：今天两棒答上 **1/12**；`ndls` **额外 0**；但 `ndls` 对其中 11 个**全部报错**。
⚠ 这个结果**本身不足以支持任何结论**（样本几乎全是同一种写法）——于是追查写法。

**普查（6417 条标准）**：**5879 条（92%）的标准号写的是全角斜杠 `／`（U+FF0F）**；
它是**唯一**的系统性异常字符（另有 11 条是法规名混进了 `doc_type='standard'`，属另一条线）。

**归一根因**：`norm_no()` 只剥半角 `/`：
`norm_no('GB／T 17098-1997') = 'GB／T17098-1997'` vs `norm_no('GB/T 17098-1997') = 'GBT17098-1997'`
—— **永不相等** ⇒ `pick_row_by_norm` 这类"按归一号挑行"的匹配**全线失手**。

**决定性 A/B**（同一批号，两种写法各跑一遍 `official_gb` + `ndls`）：

| 写法 | 任一渠道命中 | ndls 报错数 |
|---|---|---|
| 原样（全角 `／`） | **0 / 6** | 6 |
| 换成半角 `/` | **5 / 6** | 0 |

**处置（本步，一行 + 两条用例）**：`norm_no` 的字符类收进全角斜杠（`[\s/／]+`），
并加 `TestNormNoFullWidth`：① 两种写法归一到同一个号；② **全角目标能命中半角行**（匹配失手的最小复现）。

**结论对 R6c-2 的影响（这条比数字重要）**：**"提升渠道"不是该做的杠杆**。
在一个 92% 的号写错格式的库里加渠道，只会让每次巡检**白跑更多请求** ⇒ **先修格式，再谈覆盖**。
而且这条与"加不加 ndls"无关：**今天两棒的漏，主因也是格式**。

**明确登记、本步不做**（都不擅自动真库）：
1. **查询侧**：适配器发给站点的查询串仍是**原始写法**（A/B 里换半角才命中正说明这一点）
   ⇒ 需要"查询用规范形"（`／`→`/`），可在 inspector 边界统一，或各适配器自建查询串时归一。
   预期收益按 A/B 是"这类号从 **0 命中 → 5/6 命中**"。
2. **存量数据**：5879 行 `standard_no` 仍是全角 ⇒ **一次性归一是一次数据变更**，需单独决定
   （我不会不打招呼就改真库）。
3. **入库侧**：新增的号在写库时就归一，防止继续产生全角行。
4. 11 条法规名混进标准表（`个人信息保护法(测试)` 等）——另一条线。

**复核 b30 的更正（独立 verifier，2026-09-18）**：6 条声明 **5 成立 + 1 部分成立**。
我上一段**机制说错了一处**，照实记：

- 对的方向：`official_gb.py:50-51` 确实把**原始号**放进 URL
  （实测 `…?searchText=GB%EF%BC%8FT+17098-1997`）；
- **说错的地方**：`ndls` 的 6/6「报错」**不是"站点查不到"**，而是 `ndls.py:89` 把原始号拼进
  **Referer**，HTTP 头按 latin-1 编码 ⇒ **请求发出之前**就抛 `UnicodeEncodeError`
  （JSON body 本身合法）。两者是完全不同的原因，现场都只表现为"每个号都失败"。
- 它还给了一处**反例**：`std_samr_hb.py:58` 用 `norm_no()` 查的是**规范形**
  ⇒ 我那句"适配器发给站点的查询串仍是原始写法"**不成立（不能一概而论）**。
- 小口径：5879/6417 = **91.62%**（我写 92% 是四舍五入）；那 11 条与含全角斜杠的行**有 1 条重叠**（不互斥）。
⇒ **待办①按渠道拆开写**（见下），不再整体断言。

**顺手修掉 ndls 那个真 bug（本步）**：Referer 里的关键词改用 `quote(...)`
（同仓 `hbba.py:89` 已有正确写法可参照），并加 2 条离线用例：
① 全角号不再在**发出请求前**炸（诚实 miss 而不是异常）；② Referer 是**纯 ASCII** 且
全角斜杠/空格都被百分号转义（`%EF%BC%8F`、`%20`）。

**修后复测（同一批号、同一 A/B 脚本）**：

| 写法 | 任一渠道命中 | official_gb | ndls | ndls 报错 |
|---|---|---|---|---|
| 原样（全角） | **0/6 → 5/6** | 仍 0/6 | **5/6** | **6 → 0** |
| 换成半角 | 5/6 | 5/6 | 5/6 | 0 |

⇒ **两个"一行修复"（`norm_no` + ndls 的非法头）就把这类号从"全灭"变成"5/6"**。
**剩下的是 `official_gb` 这一类**：它把原始号放进 **URL 查询串**（`searchText=`），原样写法仍 0/6
⇒ 待办①对它成立，**按 b30 点名的渠道**拆开：`official_gb` / `govcn` / `hbba` / `dbba` / `ttzb` /
`cssn` / `mee`（这些确实用原始写法）；**`std_samr_hb` 是已归一的例子**，不要算进去。

---

### R6c-2b（2026-09-18 完成）：**查询侧**统一用半角规范形——真机复测 **原样 0/6 → 5/6**

**做法**（纯代码、可回滚）：
- 新增 `query_no()`（`channels/base.py`）：**只换字符形状**（`／`→`/`、`－`→`-`），
  **保留空格**——cssn/mee 实测"带空格完整号"（`HJ 819-2017`）才排第一，归一化会把空格抹掉。
  ⚠ 与 `norm_no`（匹配用：去空格与斜杠、大写）**分工不同，别混用**，两者的 docstring 都写明了。
- 落到 **6 个查询点**：`official_gb`（`searchText`/`p.p2`）、`hbba`（`key` + Referer，**`dbba` 继承同一实现**）、
  `ttzb`（`searchKey`）、`cssn`（`keyword`）、`mee`（`doctitle`）、`govcn_announce`（`q`）。
  `std_samr_hb` **不用改**（它本来就用 `norm_no` 查——独立复核 b30 点名的正面例子）。
- **守卫用例** 8 条：逐渠道断言"**送出去的请求里没有全角斜杠**"（比"改了哪一行"更能防回归），
  外加 `query_no` 不打乱空格。⚠ 用例里踩到 G23 那个坑：**注册键是 `ttzb`、适配器 `name` 才是 `ttbz`**。

**真机复测（同一批号、同一 A/B 脚本）**：

| 写法 | 任一渠道命中 | `official_gb` | `ndls` |
|---|---|---|---|
| 原样（全角 `／`） | **0/6 → 5/6** | **0/6 → 5/6** | 5/6（头修复后已可发） |
| 换成半角 `/` | 5/6 | 5/6 | 5/6 |

⇒ R6c-2a + R6c-2b 三处修复（`norm_no` 归一、`ndls` 非法头、6 个查询点用规范形）合起来，
把"这类号全灭"变成"**5/6 命中**"。**剩余未命中是 1 条格式本身就不成号的 `GBZ／T`**（连号都没有）。

**本轮的一个诚实发现**：`text_utils.clean_standard_name`（2026-09-17）**早就修过"全角→半角"**，
而且它的 docstring 明确写着"库内 `standard_name` 是从**文件名派生**的，且各个调用方各派生各的
（`write_queue_bootstrap` 直接 `path.stem`；`scripts/_stdparse.derive_standard` 先清理又被原始 stem 覆盖；
`std_bulk_import` 用 manifest 的 name）⇒ **修数据前先把派生归一，否则灌一次库又脏一次**"。
⇒ **我这轮是在更外一层（标准号与查询串）重新发现了同一根因**——不是我发现了新问题，
而是同一类问题在**另一层**没被覆盖。这条写给下一轮：**修之前先搜"这层有没有人修过"**。

**登记不做（各有理由，都不擅自动）**：
1. **入库侧防新增**：标准号的派生路径**不止一处**（上面 docstring 点名的三处 + 批量导入），
   且改动影响 35k 行 → 应单独一轮（带复核），不塞在本轮尾。
   好在**查询侧修好后，存量全角写法已经不影响命中**（只影响展示形态）。
2. **存量 5879 行是否一次性归一**：仍是数据变更，**要业主点头**。
3. **两个归一函数的"同口径"是名不副实的**：`channels/base.norm_no` 与 `text_utils.canon_standard_no`
   的 docstring 都自称同口径，实测在 `—`（U+2014）与 `－`（U+FF0D）上**不一致**
   （`norm_no('GB/T—17098')='GBT—17098'` vs `canon='GBT-17098'`）。**登记为"重复所有者"**，
   与 R5c 的 `inspector.CHAIN` 同类——要不要合并由下一轮定。

---

### R6c-2c（2026-09-18）：存量全角斜杠——**先查清"还有没有活的产生路径"**，再决定动不动库

R6c-2a/2b 之后剩两件登记：① 入库侧防新增；② 存量 5879 行是否回填。**本轮先把"①到底还需不需要做"查清**：

**时间线（决定性）**：5879 条全角行**全部创建于 2026-09-16**（最新一条 `13:52:26`），
而**派生侧的归一在 2026-09-17 就做了**（`_stdparse.derive_standard:32` 与
`std_bulk_import:166` 都已 `／`→`/`）；实测 **2026-09-18 及以后新增的全角行 = 0**。
⇒ **① 不需要做**：没有活的路径在产生新脏行。这一条比"写一个归一函数"更值——
**先确认"要不要做"，再决定"怎么做"**。

**② 存量回填：碰撞分析先行**（`standard_no` 是查重依据，回填若制造重复就是**新**的脏）：
- 回填后**只有 1 处会撞车**：`GB／T 14308-2010` 与已存在的 `GB/T 14308-2010`
  是**同一标准的两个文件**（两条 `doc_meta`）；`short_code` 同样一处；
- `short_code` 是**紧凑形**（`GB／T10001.12023`，无空格无破折号），要单独按"只换字符形状"处理；
- `standard_name` 里也有 2 处全角。

**产物（脚本 + 用例，未写库）**：`scripts/normalize-standard-no-slash.py`
——默认 **dry-run**、`--apply` 才写；写出**完整变更清单**（doc_id/列/旧值/新值，可精确回滚）；
**撞车即跳过并列出**（不制造重复）；单事务；前后各跑一次 `integrity_check`。
dry-run 实测：**计划 11758 处**（standard_no 5878 + short_code 5878 + standard_name 2）、
**跳过 2 处**（同一对撞车）。用例 `tests/test_normalize_std_slash.py` 4 条（普通行、撞车必跳过、
无全角零变更、name 列）。
⚠ **本轮先不写库**：独立复核 b31 正在重跑 A/B（它要抽样这批全角行），
**在别人读库时改数据会让它的结论失真** ⇒ 等它回来再执行，并单独提交/快照。

---

**复核 b31（独立 verifier，2026-09-18）**：6 条声明 **4 成立 + 2 部分成立**。它抓到三类，都已处置：

1. **两处漏网**（"送出去的请求里没有全角"这条声明**不成立**）：`ndls` 的 **JSON 搜索体** `keyword`
   （**可达渠道**——routing 会把 AQ/GB 送过去）与 `web_fallback` 的 `q`（已不在链里）。
   已修：ndls 的搜索体也用 `query_no`、web 一并收口，补 2 条用例。
2. **一个我没提的真失配**：`norm_no` **不折连字符**（U+2014/U+2013/U+FF0D/U+2500），
   而 `query_no` 与 `canon_standard_no` **都折** ⇒ **只有匹配侧漏了**，表现为静默的
   "查得到但匹配不上"。已对齐（折同一组）+ 用例（并断言与 `canon_standard_no` 一致）。
3. **两处措辞比证据强**（我接受并改成更准的说法）：
   - 我引用的 A/B 脚本**证明不了前后对比**——修好之后"原样/半角"两路请求已被 `query_no` 折成同一个串；
     真正的 before/after 工具是**复核员的变异测试**（把各模块 `query_no` 换成恒等函数）；
   - **"原样任一 0/6"对 `ndls` 不成立**：那是 Referer 未转义那一版的现象，且**没有已提交的 artifact**
     （只有我的自述）。复核员换一批 12 个号实测：**修复前口径 `official_gb` 0/12 → 现代码 12/12**——
     方向一致且更强。⇒ 台账里引用"0/6"的地方，一律以"**0/12（复核员独立样本，变异测试口径）**"为准。

**复核后的门禁**：pytest **2038 passed / 3 skipped / 0 failed**、mypy **140/0**。

**R6c-2c 执行记录（已落库，2026-09-18 21:05）**：
- 计划 **11758 处**、**跳过 2 处**（`GB／T 14308-2010` 与已存在的半角行是**同一标准的两个文件**）；
- 写库后**逐条对账**（`var/tmp/r6c2c-verify.py`）：① 形状替换不纯净 **0**；
  ② **归一语义被改 0**（`norm_no(old)==norm_no(new)` 对全部 11758 条成立）；③ 库里与新值不一致 **0**；
  ④ 剩余全角 = **正好那 2 处跳过**；⑤ `integrity_check` **ok**；
- 清单 `var/backup/r6c2c-normalize-slash-20260918-210550.json`（含全部 doc_id/列/旧值/新值 ⇒ 可精确回滚）。
- ⚠ **我自己抓到并更正的一处错（不掩盖）**：清单里的 `db_after` 与 `db_before` **完全相同**——
  因为我在事务提交后**立即**取指纹，而那时改动还在 **WAL** 里、主库文件**一个字节都没变**。
  脚本已修（先 `PRAGMA wal_checkpoint(TRUNCATE)` 再关连接、最后取 stat），
  清单里补了 `db_after_checkpoint`（sha256 `5a775938a3d4…`）与 `correction_note`。
  ⇒ 教训：**"留了指纹"不等于"指纹有用"**——必须在数据真正落盘之后取；
  这正是复核员的收尾建议（"可回滚不能只是口头承诺"）要防的那种事，只不过这次是**我自己**先撞上。

---

### R6c-3（2026-09-18 完成）：**"这一号该问谁"**变成可调用的一层（只读，不改巡检行为）

设计稿 §3.2.1 的实现计划，**已交付**：

**新模块** `src/core/update/channels/question_router.py`：
- `channels_for(classes=None, standard_no="", *, rows, only_ok=True, table, chain)`
  —— 五类 → 候选渠道，**按链的顺序**排（前缀专用渠道天然在兜底棒前）；
- `route_report(...)` —— 同上一份，但**每类多给一个原因**：`ok` / `no_capability` /
  `off_chain` / `all_down`，外加 `declared` / `on_chain` / `dropped_down`；
- `unanswerable_classes(report)` —— 调用方据此写 `unanswerable`（**不是** `not_found`）。

**规则**（实现即设计稿 1–5 条）：候选 = 能答这类 ∩ 在链上；`only_ok=True` 再滤 `state=="down"`；
顺序 = 链的顺序；空候选交调用方写 `unanswerable`；`tool:` 靠"能力表判空"排除（用例钉住）。

**比设计稿多做/明确的三件（都写进了 docstring，免得后人重吵）**：
1. **"候选为空"必须分开记原因**（设计稿只说"记 unanswerable"）：`no_capability`/`off_chain`
   是**结构性缺口**，`all_down` 是"今天全挂"——写证据时合成一个理由，业主会以为"查过了"；
2. **链的两种写法都收**（`ndls` 与 `ch:ndls`）：R6c-4 要把链源换成台账驱动链（给的是 `ch:` 开头的 id），
   只认一种写法的话，换源那天现场表现是**候选全空**、很难看出来；
3. **不在这里滤 `enabled=0`/`wiring=broken`**：那是"链"的职责（`ledger_chain`），
   本模块只管"∩链 + 滤判死"。两处都滤就是两个所有者——**故意不做**。

**用例** `tests/test_question_router.py` **20 条**（设计稿验收 1–4 全部 + 第 5 条真机对照：
对真库 3 个号**独立复算**——直接读 JSON + `select_chain`，不用本模块的内部函数，并断言
路由结果是 `answers-matrix` 能力表的**子集**）。
**给人看的脚本** `scripts/question-route.py`（只读；支持 `--sample N` 从真库抽最近 N 个号、`--json`）。

**我自己踩的三个坑（都是用例/真机当场抓的，不掩盖）**：
- 我把**标准号写成了第一个位置参数**（`channels_for("HJ ...")`）⇒ 原来的报错只说"不是五类之一：'H'"，看不出是位置错了。
  已改：`classes` 传字符串时提示"单类怎么写 / 标准号该放第二个位置参数"，并补一条用例；
- 我在"已知缺口"用例里断言原因是 `off_chain`，**实际是 `all_down`**（能答的那根在链上、但今天死了）——
  被用例当场纠正，并把两种原因的区别写进注释；
- `--sample` 第一版查了 `documents` 表（真名是 `doc_meta`）且用了可写连接。已改：真名 + `mode=ro` 只读连接。
  ⇒ 顺带确认 `doc_meta.standard_no` 是 **UNIQUE**（这正是回填必须"撞车即跳过"的原因）。

**真机量到的三件事（本步最重要的产出，都是"下一步从哪儿省力"的依据）**：
1. **链只有 2–3 根棒**：`GB*` →（ndls, official_gb, govcn）；`GB/T*` →（official_gb, govcn）。
   五类在真实号上今天都**有候选**——但这是**因为 `official_gb` 声明了全部五类**；
   `mee`（HJ）只声明"发布"，所以 **`official_gb` 一判死，HJ 的"修订/编号核验"就没有候选**
   （已用一条**记录型用例**钉住，链一加宽它就红）。
2. **9 条渠道声明了五类能力、却没有任何号能路由到它**（全部 `wiring=unwired`；
   其中 `laws_db`/`std_samr_hb`/`mem_gov`/`mohurd`/`cssn` 的 `state=ok`）——
   这是 R6c-4"要不要把专用渠道提升进链"的**真实输入**。
3. ⚠ **GB/T 从来没被送进 ndls**：真库 6417 个号里 **6129 个（95.5%）是 `GB/T`**，
   而今天的前缀正则 `^GB\s?\d{4,5}\b` **不匹配 `GB/T`** ⇒ 它们只走（official_gb, govcn）。
   真机实测 ndls **答得出来**：`GB/T 38496-2020` → 现行、发布 2020-03-06、实施 2020-10-01、
   名称"消毒剂安全性毒理学评价程序和方法"；`GB/T 10001.1-2023` 同样答出。
   ⇒ **下一步 R6c-3b**（单独一步、单独复核）：把 `GB/T`/`GB/Z`/`GBZ` 补进前缀路由，
   并顺手修"**`select_chain` 是第 7 个读原始号的站点**"（`GB／T 14308-2010` 那条全角行今天匹配不上 GB 规则
   ——R6c-2b 统一了 6 个查询点，**漏了这条路由点**）。

---

### 复核 b32（独立 verifier，2026-09-18）：**它把我的"入库侧不用改"证伪了**（本轮最重要的一条）

对象 = R6c-2c 已执行的存量回填 + 回填脚本。**声明 1/2/3 成立**（逐条独立复算：
剩余全角 standard_no=1/short_code=1/standard_name=0、计划外不一致 0；11758 条 new 全部落库；
指纹与 `db_after_checkpoint` 完全一致，并且它**自己复算了 WAL 机制**——commit 后主库字节不变、
checkpoint 后才变 ⇒ 我那处自我更正成立；"映射造成的撞车恰好 1 处"复算一致）。
**声明 4/6 部分成立、声明 5 不成立**：

1. ⚠ **声明 5 被证伪（我错了）**：我写"没有活的派生路径产出全角 ⇒ 入库侧不需要改"。
   它找到**两条活的**：
   - `write_queue_bootstrap._ingest_doc`：`std = tags.standard_no or path.stem`，
     `auto_tag("")` 对空串恒 None ⇒ **原始文件名 stem** 进 `standard_no`。
     它在一次性库上**执行**得到 `stored standard_no='GB／T 10058-2023 电梯技术条件(1)'`；
   - `var/ocr-loop/ingest_from_manifest.py`：manifest **8205/8484 条带全角**，
     其中 **约 2322 条 PDF 尚未入库**；`split_std` 的前缀表漏了 `GBZ／T` ⇒ 号被压成裸 `GBZ／T`，
     **真库现存那一行就是它的指纹**（它已经往生产库写过脏号）。
   - 我的"日期论证"（09-18 之后 0 条新增）**不成立**：`created_at >= 2026-09-17` 的行数 = **0**，
     即这两天**压根没入库**——"0 条新增"是没数据，不是没脏数据。
2. **声明 4 的 4.4 有盲区，且它实测"制造了重复"**：判重用的 `existing` 是 **apply 前快照**，
   对"两行归一到同一个**尚不存在**的目标"看不见。它用**真脚本**在一次性库上跑出
   `计划4/跳过0` → 静默写入重复 `('GB/T33332003', 2)` 且报"写库完成 integrity ok"
   （真库 `short_code` **只有非唯一索引**；`standard_no` 才有 UNIQUE，会整批 rollback）。
3. 另外三条附带：**Ctrl-C 不回滚**（`KeyboardInterrupt` 不是 `Exception` ⇒ `write_transaction`
   的 `except Exception` 不触发，事务留在连接上，"写后核对"读的是**未提交状态**，可能报假成功）；
   `conn2.close()` 关掉了**线程局部共享连接**（同进程二次调用即 `ProgrammingError`）；
   回填**不 bump `updated_at`、不写 `event_log`** ⇒ 动真库在应用审计轨迹里**零痕迹**；
   还有"无 CAS/无 rowcount 校验"（计划与写入之间被并发改过会静默覆盖）。
4. **声明 6**：4 条用例全绿，但**挡不住**上面那类事故（只造了"目标已存在"一种场景，
   fixture 也没有 UNIQUE/索引差异）。

### R6c-2d（2026-09-18 完成）：**入库侧收口** + 脚本加固（承接 b32 的两条证伪）

- **存储形第一次有主**：新增 `text_utils.store_standard_no`（1:1 折 `／`→`/`、`－`→`-`；
  **不动**空格/大小写/年份 ⇒ `norm_no(旧)==norm_no(新)`）。与三个已有"归一"的分工写进 docstring：
  `canon_standard_no`/`standard_no_key` 是**比较键**（去空格去斜杠，**不是**存储格式）、
  `norm_no`/`query_no` 是**采集侧口径**。
- **收口落在写边界** `clause_repo.insert_document`（三个列都折）——因为 `short_code` 是从
  `standard_no` **派生**的（`pipeline:2169`/`docx_ingest:66`/`track_l:306`），逐个调用方折必然漏。
  另两个**裸写入口**（`bulk.py` 的 INSERT、`auto_tag.apply_tags_to_doc_meta` 的 UPDATE）过同一个 helper，
  入口清单写在 `_STORE_FORM_COLUMNS` 旁（b32 正是靠逐个点名入口找到漏口的）。
- **`write_transaction` 改 `except BaseException`**（中断→回滚→原样抛出）：这修的不只是我的脚本，
  而是**每个写者**在 Ctrl-C 时的语义（原来会留下未回滚事务 + 假诊断）。
- **回填脚本加固**（4.4/4.5/4.6）：判重加上"**本次计划内自撞**"（`planned` 表）+ 清单级断言
  `(列,目标值)` 不重复；每条 UPDATE 带 **CAS + rowcount 校验**，任一条对不上就**整批回滚**；
  不再 `conn2.close()`；写一条**汇总 `event_log`**（`standard_no_shape_fix`），
  并**刻意不 bump `updated_at`**（那会让"内容被改过"的 UI 信号说谎）。
- **加固后对真库 dry-run**：仍是 **计划 0 处、跳过 2 处**（与加固前一致 ⇒ 没改变真实数据的面貌）。
- 用例：`tests/test_store_standard_no.py`（14 条）+ `tests/test_normalize_std_slash.py`（8 条，
  补了 b32 点名的四类：计划内自撞 / 清单无重复目标 / 中断回滚 / 同进程二次调用）。

### R6c-2e（2026-09-18 完成）：**修那一行坏号**（b32 的"指纹行"）

`scripts/repair-missing-standard-no.py`（dry-run 默认；规则保守：号里没数字 → 从 `file_path`
文件名推号，首段必须在前缀白名单、拼出的号必须像号；撞车即跳过）。真库 dry-run = **修 1 行、跳 2 行**，
已 `--apply`：`'GBZ/T'` → **`'GBZ/T 160.27-2004'`**、`short_code` → `'GBZ/T160.272004'`、
`standard_name` 去掉开头那段号 → `'工作场所空气有毒物质测定硼及其化合物'`；
写后 `integrity_check=ok`、`updated_at` **未动**（刻意）、`event_log` 有该批次记录、
清单 `var/backup/r6c2e-repair-missing-no-20260918-212634.json`（含逐列 old/new ⇒ 可精确回滚）。
写后只读复核：号里没数字的行只剩那两条**法规**行（`个人信息保护法(测试)`/`中华人民共和国民法典`
——它们的"号"本来就是法规名，**故意不动**）；含全角行仍是**故意留的 1+1**。
库指纹：`5a775938a3d4…` → **`97f1dcb70e80…`**（size 不变、mtime `2026-09-18T21:26:45`）。

### 诚实边界（本步**没有**做到的，别读成做到了）

- **已执行的那次回填在应用 `event_log` 里仍然零痕迹**（只有 `var/backup/*.json` 与 git/文档）。
  我没有补写"追溯审计行"：事后补的行容易被后人误读成"当时记了"，所以宁可在这里写明缺口。
- **2322 条待入库的全角条目仍在**（`var/ocr-loop/evolve/ingest_manifest.json`）。
  收口之后它们**进库时会变成半角**，但"要不要跑这个循环、什么时候跑"是业主的操作决定，我不替他跑。
- ⚠ **行为变化（有意）**：折形状之后，"同一标准的第二份文件"会撞 `standard_no` 的 UNIQUE ⇒
  **报错而非静默写第二行**（真库现存那对 `GB／T 14308-2010` / `GB/T 14308-2010` 就是这么来的）。
  选"报错"是因为静默写第二行正是数据被污染的形态；但**跑 OCR 循环的人要知道这条**：
  遇到同号不同文件时会看到异常，而不是多出一行。

---

### R6c-3b（2026-09-18 完成）：兜底链**量完再改** —— `ndls` 插到 `govcn` 前 + 第 7 个读原始号的站点

R6c-3 量出两件事：**链只有 2–3 根棒**、**6129 个 `GB/T` 号从不进 `ndls`**。当时我的判断是
"这是覆盖缺口，把 `GB/T` 补进前缀路由"。**先量了，判断就变了**：

**量 1（`GB/T` 上谁更强，12 个真库号 A/B）**：`official_gb` 命中 **12/12**、`ndls` 命中 **12/12**，
两者都给出状态 ⇒ **在 `GB/T` 上这不是"能不能答"的缺口**，差别在**字段**：
`official_gb` 给的是它 HTML 表里的第一个日期（多处表现为**发布**日期）、无废止日期/代替链；
`ndls` 给的是**实施**日期 + 废止日期 + 代替关系。
而且 `ndls` 默认要发**两次**请求（搜索+详情）⇒ **不把 `ndls` 提到 `official_gb` 前面**
（谁在前不改变"能不能答"，却会让 6129 个号从 1 次请求变 2 次）。

**量 2（兜底链该怎么排，按前缀分层抽 10 个真库号）**：
`official_gb` **4/10**、**`govcn` 1/10**、`ndls` **6/10**；`govcn` 那唯一一次命中是**法规**行
（`民法典`），标准号上 0/9；`govcn` 还最慢（未命中时见过 **7.1s**，`ndls` 1.2s）。
真例：`GBZ 37-2024`、`GBZ/T 160.27-2004` 都是 **`official_gb` miss 而 `ndls` 命中**
（后者 `ndls` 说 `withdrawn 2018-05-01`）。⇒ **`govcn` 排在第二棒就是在标准号上白打一次请求。**

**改动（三处，都很小）**：
1. `_FALLBACK`：`(official_gb, govcn)` → **`(official_gb, ndls, govcn)`**（`govcn` 不删：
   它是今天唯一能命中**法规名**行的那根）；
2. `select_chain` 用**存储形**折半角再匹配（**第 7 个读原始号的站点**——R6c-2b 统一了 6 个查询点，
   漏了这里）；
3. 新增 `first_route()`："前缀首选"的**唯一来源**。

**两条用例**如约变红并被我**有意**改写（这正是记录型用例的价值）：
`test_已知缺口_official_gb判死时_HJ会丢两类`（R6c-3 时用来钉"HJ 的单点故障"）现在断言**缺口已被补掉**
（`ndls` 在链上 ⇒ 不再 `unanswerable`）；`test_专用渠道在候选里而不在链里[ch:ndls]` 里
**`ndls` 毕业**了（从"可提升候选"变成"链上成员"），参数换成 `ch:dbba`/`ch:hbba` 并另加一条正面钉住毕业。

⚠ **我自己抓到并更正的两处（不掩盖）**：
- **一处措辞比证据强**：我原本写"库里那行全角 `GB／T 14308-2010` 在旧写法下掉了国标→状态权威的首选"。
  **那句是错的**——半角的 `GB/T …` 同样不匹配任何 GB 规则（`^GB\s?\d{4,5}` 要求 GB 后就是数字），
  两种写法**本来都走泛查兜底**，所以那一行没丢任何东西。**有真实差别的是"前缀规则里带斜杠"的号**：
  `T／ZSA 328-2026`（全角）匹配不上 `^T/\b` ⇒ 掉进泛查兜底、丢掉"团体标准→专门渠道"。
  docstring 与用例都按这个**准确**说法改了，并保留"折叠本身仍值得做"的理由。
- **量完之后才发现的一处假差异**：`scripts/chain-snapshot.py` 靠"`select_chain(no)[0]` 不在兜底名单里"
  反推"它是前缀首选"——`ndls` 进名单后，`GB`/`AQ` 这类以 `ndls` 打头的号被反推成"没有前缀首选"，
  快照把 **3 个样例误报成"⚠ 链会变"**。改成向路由本身要（`first_route`）之后，9 个样例全部"不变"。

**真机核对**：`select_chain` 逐号打印（含全角/无空格写法）与 `chain-snapshot.py`（台账过滤后 = 今天的链，
✅ 无差异）；`GBZ`/`GB/T`/`HJ`/`DB`/`T/`/`MT` 的链尾都出现了 `ndls`。

**诚实边界**：本轮**没有**跑一次真实巡检批次端到端（没让 inspector 去实际降级）；
"哪根棒能答"的证据是上面的 A/B 实测 + 台账探针，**不是**一次完整的巡检回放。

---

### R6c-3c（2026-09-18 完成）：**`official_gb` 把发布日期当实施日期存了**（P1 准确性，最常用的那根棒）

**怎么发现的**：R6c-3b 的 A/B 里注意到 `official_gb` 给的日期与 `ndls` 差几个月
（`GB/T 38496-2020`：`official_gb` 2020-03-06 vs `ndls` 2020-10-01）。顺手抓原始 HTML 逐格看，
`GB 18218-2018` 那一行是 `td[7]='2018-11-19'`（发布）、`td[8]='2019-03-01'`（实施），
而适配器的取法是 `dates[0]` ⇒ **存进 `effective_date` 的是发布日期**。

**证据（跨渠道交叉验证，不是推断）**：12 个真库 `GB/T` 号，
`dates[-1]` 与 `ndls` 的实施日期（a205）**12/12 一致**；`dates[0]` 只在"发布==实施"的 **2** 个号上一致。
（`ndls` 取 `impl or pub`、`cssn` 取 `impl or pub`、`hbba` 取 `actDate`、`std_samr_hb` 取 `ACT_DATE`、
`mee` 按"实施时间"列取——**只有 `official_gb` 这一根取错**，所以这不是"全库口径问题"，是一处实现错。）

**影响面**：`ChannelResult.effective_date` → `inspector.py:372` 的 `latest_info` →
`update_change_event.latest_info_json` → 面板/报告里显示的日期。
`official_gb` 是今天**最常用**的那根棒（`GB/T` 首选它、`GB` 也在链上），所以受影响的是大多数变更事件。

**修法**：新增 `official_gb._impl_date(dates)`：取**第 2 格**（实施日期），只有一格时如实取用。
取 `[1]` 而不是 `[-1]`：列**追加**比**重排**常见——将来多出"废止日期"列时 `[1]` 仍对、`[-1]` 就错了。

⚠ **一条老用例把 bug 钉住了**：`test_official_gb_parses_real_openstd_html` 断言
`effective_date == "2022-03-15"`（=发布），而它**上面两行的 fixture 注释**明明写着列序是
"发布日期 | 实施日期"。已改为 `2022-10-01` 并把证据写进注释；另补 4 条 `_impl_date` 单测。
⇒ 这条教训值得单记：**fixture 的注释是对的，断言是错的——两者不一致时，先信哪个？
要去看真实响应的逐格结构，而不是信断言。**

**登记一处同类可疑（本轮没修，因为它在今天语料上不活跃）**：`ttzb.py` 用
`datePublished`/`publishDate` 填 `effective_date`——也是**发布**语义；但 `T/` 类号今天库里没有
（语料是 6397 `GB*` + 12 `GBZ` + 7 条法规行），而且我还没核 ttzb 的响应里到底有没有"实施日期"字段。
⇒ 列为待办，**没有**当成已修。

**诚实边界**：修的是**解析**；已经写进 `update_change_event.latest_info_json` 的**历史事件**里那些日期
仍然是旧的（要不要回填历史事件是另一件事，**本轮不做**，也**没有**顺手做）。

---

### 复核 b33（独立 verifier，2026-09-18）—— 收口**结果**成立，但两处"我做过头/做漏了"被抓住

对象 = R6c-2d/2e（`520bb56`）。**声明 1（结果）/2/3/4/5/6 成立**：
它把**全部 tracked 文件**（含 `doc_meta` 的 121 个文件、语句级写者 24 处/13 处非测试、
`CREATE TRIGGER`=0、动态表名=0、API 对三列只读）逐条判完，**没找到第三条能把全角 `／` 写进这三列的活路径**；
端到端也验了"全角入参落库为半角 + 调用方 dict 未被动"；回填脚本的加固、CAS 回滚、中断回滚、
`ndls` 毕业、修复行的双证（文件名 + 外部页面 2004-05-21/2004-12-01）都对得上。

**它抓到的两条（都已修，见 R6c-3d）**：
1. ⚠ **最高风险：我给"名称"列折了连字符——那不是换形状，是改文字。**
   真库现存 **5 行**标准名拿全角 `－` 当**中文连接号**（`丙烯腈－丁二烯－苯乙烯（ABS）压力管道系统…`、
   `蒸馏－硝酸钍容量法`、`氢化物发生－原子荧光光谱法`…）⇒ 同一标准再入库会被写成半角，
   **新旧行名字不一致且无任何提示**。设计上我原本的理由是"1:1 换形状"，但那条理由**只对数字成立**。
2. ⚠ **次高：写边界折了形状，查重边界没折** ⇒ 全角重复件从"静默多一行"变成
   `run_full_ingest` 里**未捕获的 `IntegrityError`**。这是**我自己改出来的不对称**。
3. **措辞被证伪**：我写"写 `doc_meta` 那三列的**全部入口**"，实际至少 4 个写者不在清单里
   （`scripts/fix_standard_name_suffix.py` 直写 `standard_name`、`measure-endpoint-blocking.py` 与
   `verify-engine-uvicorn.py` 裸 INSERT、以及本轮新增的 `repair-missing-standard-no.py`）——
   而"入口清单"正是 b32 找到漏口的办法，一份自称完备却漏 4 条的清单会害下一个人。
4. 顺带更正一个数：待入库的全角条目它独立复算是 **2282–2283**（我写"约 2322"，口径差 ~1.7%，
   它用的是 PDF basename 代理指标而非 sha256）。

### R6c-3d（2026-09-18 完成）：按 b33 的两条改（名称折法拆开 + 查重侧同口径 + 清单措辞纠偏）

1. **拆折法**：`store_standard_no`（号/短码：折 `／` 与 `－`）与新增 `store_standard_name`
   （名称：**只折 `／`**）。`clause_repo` 改成"列 → 折法"的表（`_STORE_FORM_FOLDER`），
   `bulk.py` 的名列也随之改用名称折法。用例：真库那 5 行的写法**必须原样保留**。
2. **查重侧同口径**：6 处 `WHERE standard_no=?`（`pipeline`/`bulk`/`law_text`/`dry_run`/`smoke_ingest`）
   一律折存储形后再查 ⇒ 全角重复件被**正常判成 duplicate**，不再走到 INSERT 去撞 UNIQUE。
   用例：`_dup_probe(db, 新hash, 'GB／T …')` 必须认出库里那行半角 `GB/T …`。
3. **清单措辞纠偏**：`_STORE_FORM_COLUMNS` 旁不再说"全部入口"，改成"**已知入口** + 明确列出
   **不在收口路径上**的那三个脚本（并注明它们今天产不出全角、但不变量对它们不成立）"。
   用例断言源码里**不许再出现"全部入口"**、且必须点名 `fix_standard_name_suffix.py`。

**诚实边界**：这三处是**按复核意见改的**，改完**还没有**经过独立复核（下一轮 verifier 的活）；
b33 自己说过它没有跑端到端（没造 PDF 跑整条管线），我这轮也只做了语句级/单元级验证。

---

### R6c-4a（2026-09-18）：**先量再定计划**——量出来的结论把原计划改了

设计稿原计划是"每类沿候选链试 + **每类各记一条事件**"。动手前先量了三条：

1. **五类的"第一候选"几乎总是同一根棒**：按号段分层抽 11 个真库号，
   **11/11 都是"五类同一根第一候选"**（`GB/T`/`GBZ`→`official_gb`，`GB `→`ndls`）——
   因为这两根都**声明了全部五类**、又排在链首。⇒ 按类选渠道**今天不会让巡检去问不同渠道**，
   它买到的是**记账与如实**，**不是精度**。另一组量法（候选并集 vs 今天的链）16/16 完全相同
   ⇒ 按类问**也不增加请求**。
2. **事件量最多 ×5，且按现表结构会互相压掉**：`change_type` 有 CHECK（只 5 个值）、
   去重键是 `(doc_id, standard_no, change_type)` ⇒ 五类里同为 `no_change` 的会被压成一条、
   类的信息**静默丢失**；要分开就得改 CHECK（§3.3 明确不新增表/列）。
3. `unanswerable` 今天只是"调用方约定"，没有可算的判据。

⇒ **R6c-4 计划已改**（写进 `docs/CHANNEL-R6C-DESIGN.md` §3.2.2）：**不写"每类一条事件"**，
改为在那一条 judged 事件的 `latest_info` 里加 `classes` 映射（每类 `{channel, conclusion, reason,
unanswerable}`）——原意（每类各自记结论 + 可归属渠道）满足，且**不动 schema、不 ×5、不压掉**；
终态恒等式加"有 `unanswerable` 不算 done"；**真正提精度的活是能力表保真度**（把第一候选的声明
从 R1 的 medium 升到 high，要有适配器代码级证据），不是让路由去做实验。

⚠ **我自己的重复性错误（第三次犯，记在这里免得第四次）**：写探针时又在**双引号 CJK 字符串里放了
ASCII 双引号**（`print("\n===== 每号"要问几根"分布 =====")`），直接语法错。
这个错在本仓已经有过记录，我仍然犯了三次 ⇒ 规矩改成：**中文字符串里一律用「」**，不用 ASCII 引号。
