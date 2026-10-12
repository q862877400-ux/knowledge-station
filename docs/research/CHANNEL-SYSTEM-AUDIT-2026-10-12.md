# 采集/更新通道系统核实报告（2026-10-12，纯读代码 + 读库）

业主问：「我不是做了一套自动嗅探各个网站的法规和标准的更新动态，然后根据更新动态去下载
附件区或者去标准网下载最新版本的国标或者法规的通道吗」

**答：做了，而且比业主记的还完整。但它有一个断点。**

---

## 一、那套通道系统确实存在（20 个适配器）

`src/core/update/channels/` 下 **20 个 .py**，覆盖业主说的所有来源：

| 适配器 | 管什么 |
|---|---|
| `official_gb.py` | **国家标准全文公开系统**（openstd.samr.gov.cn）主渠道 |
| `std_samr_hb.py` | 国标 + 行标 |
| `ndls.py` | 国家数字标准馆 |
| `cssn.py` | 标准全文检索（`a825`=CCS 码） |
| `dbba.py` | 地方标准 |
| `mohurd.py` | 住建部 |
| `govcn_announce.py` | 国务院政策文件库**公告** |
| `laws_db.py` / `mee.py` / `mem_gov.py` / `ttzb.py` / `hbba.py` | 法规库 / 生态环境部 / 应急部 / … |
| `web_fallback.py` | 通用网页兜底 |
| `proxy_rotate.py` / `routing.py` / `question_router.py` | 代理轮换 / 路由 / 问答路由 |

**降级链**（`inspector.py` 头注）：`official_gb → govcn`，单号探测预算 3 次。

---

## 二、「下载附件」这条能力**真做过**（不是设想）

`govcn_announce.py` L140 `archive_pdf()`，注释写着：

> 2026-08-26（P2-②）：实现真实下载（**curl_cffi chrome 指纹 + %PDF 魔数校验**），
> 取代旧"最小合法占位 PDF"

实现细节（L157-165）：`transport.fetch_bytes(url)` → 校验 `content[:4] == b"%PDF"`
**且** `len(content) > 1024` → 写盘 → `upd_log` 留痕。
**这正是"字节签名判据"，我上一轮说要新加的东西——早就有。**

有测试：`tests/test_govcn_archive.py`（真实下载测试）。

---

## 三、「自动入库」也接好了

`src/core/update/web_ingest.py` L4 自述：

> 抓详情页 → 抽正文 → 判效力档 → 调 `law_text.ingest_law_text()` **入库**（带来源 URL 溯源）

进的是 **`doc_meta`（标准库本体）**，不是材料平面。配套：
- `classify_status` / `classify_hierarchy` / `classify_change_signal` 自动判效力
- `pending_rows()` / `ingest_pending()` / `triage_pending()` 整套流程
- 去重判据：按 `doc_meta.source_url` **或** `standard_no`

端点齐备（`routes_update.py`）：
`/update/check`（一键巡检）、`/update/announce-scan`、`/update/announce-ingest`（批量入正文库）、
`/update/announce-ingest/pending`、`/update/announce-ingest/triage`、`/laws/search`、`/laws/ingest`。

---

## 四、★ 断点一：那套系统**没有任何东西在自动跑**

`server.py` 的 `run()`（唯一生产启动点，L3286-3304）只启动了两个后台线程：
1. `start_write_worker()`（写队列消费）
2. `start_law_refresh()`（**法规目录**定时刷新，spec 006）

**`src/core/update/scheduler.py` 的 `start()` 全仓无人调用** —— L3298 的注释自己写着：
> ⚠ 不走 `update/scheduler.py` —— 那个调度器的 `start()` 全仓无人调用（**死代码**）

⇒ **巡检（update/check）只能人工点按钮触发**，不是"自动嗅探"。业主记的"自动"，
实际是**手动一键**。

---

## 五、★ 断点二：入库的文档**没有 CCS 标签** ⇒ 不会自动进目录

实测按来源分（生产库只读）：

| 来源 | 总数 | 有 CCS 标签 | 占比 |
|---|---|---|---|
| 本地文件（`D:\...\标准\`） | 7,173 | 6,838 | **95.3%** |
| `lawrefbook://` | 1,430 | 0 | 0.0% |
| **`web://`（通道/网页入的）** | **380** | **0** | **0.0%** |

**根因**（已定位到代码）：填 CCS 的那段在 `pipeline.py` L2216-2224：

```python
if doc_type == "standard":
    ccs_lookup = resolve_ccs(standard_no, standard_name)
    ccs_tag = ccs_to_tag(ccs_lookup, standard_no)
    if ccs_tag and ccs_tag not in tags: tags.append(ccs_tag)
```

而 `web_ingest` 走的是 **`law_text.ingest_law_text()`** ——
`git grep resolve_ccs -- src/core/ingestion/law_text.py` **空命中**
⇒ **那条路完全不填 CCS** ⇒ 目录树（读时按 `CCS:xxx` 分类）认不出它们 ⇒ 落「其他标准」兜底桶。

---

## 六、★ 断点三：`archived_pdf_path` **0/6,471**，公告存档目录是空的

实测：
- `update_change_event.archived_pdf_path` 非空 = **0 / 6,471**
- `%APPDATA%\KnowledgeStation\announcements\` = **空目录**

**`archive_pdf` 的调用点只有测试**（`tests/test_govcn_archive.py`），**生产代码里没人调它**。

⇒ **"下载附件"这条能力做完了，但从来没接进生产链路。** 巡检发现"有新版本"后，
只写一条 `update_change_event`（`change_type='new_version'`，实测 3 条），
**不会去下载那份新版 PDF**。

`change_type` 实测分布：`no_change` 5,746 / `withdrawn` 600 / `not_found` 96 /
`superseded` 26 / **`new_version` 3**。

---

## 七、两套系统是**并行**的，各管一头（不重复）

| | 通道系统（`update/`） | `ks_collect`（宿主工具） |
|---|---|---|
| 触发 | **手动点按钮**（无自动） | 模型调用 → **弹框问人** |
| 单位 | **标准号 / 公告源** | **一个 URL** |
| 产出进 | **`doc_meta`（标准库）** | **`material`（材料库）** |
| 能力 | 20 适配器 + PDF 下载 + 正文入库 | 只收网页正文（5 种 mime） |
| 前端 | `KsChannelsPanel` / `KsSettingsSection` | 无（模型调） |

**⇒ 我前几轮把 `ks_collect` 当成唯一采集入口，是错的。**
业主说的"自动嗅探更新动态"= **通道系统**；`ks_collect` 是另一件东西（模型按需采一个网页）。

---

## 结论：要做的不是"新建能力"，是"接上三个断点"

| # | 断点 | 要做什么 | 是否碰安全面 |
|---|---|---|---|
| **1** | 通道系统无自动触发 | 把 `scheduler.start()` 接进 `run()`（或照 `law_refresh` 先例自建线程） | 否 |
| **2** | 通道入库不填 CCS ⇒ 不进目录 | 在 `law_text.ingest_law_text()` 补 CCS（复用 `ccs_fetcher`，与 `pipeline.py` 同一所有者） | 否 |
| **3** | `archive_pdf` 没接进生产 | 巡检判定 `new_version` 时调它下载新版 PDF | ⚠ **是**（自动下载，碰 `NOT-DOING` 第 20 条"不许演化成自动下载"） |

**⇒ 1 和 2 是纯技术缺口（业主授权范围内可做）。3 要业主明确批准**，
因为它正是 `NOT-DOING` 第 20 条禁止的"自动下载"——除非改成"下载前弹框问人"。
