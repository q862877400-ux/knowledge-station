# law-source（官方法规来源管线）

**位置**：`src/core/knowledge/law_source/`
**一句话**：从官方站抓法规原文，走与标准件同一条入库链。

## 职责

**法规侧的数据源层**。链路：`flk.npc.gov.cn`（国家法律法规数据库）+ `gov.cn`（国务院政策文件库）→ 官方带格式 Word → LibreOffice / WPS 转 PDF → 现有 `run_full_ingest` 管线。产物**与标准件完全同构**（预览 / 高亮 / 目录 / 条款修正都是同一套）。

模块：`http.py`（共享 HTTP 层）、`flk_client.py` / `govcn_client.py`（两个来源客户端）、`catalog.py` 22.4 KB（全量编目）、`convert.py`（docx → PDF）、`ingest.py`（入库编排）、`verify.py` 15.2 KB（点开即核验）、`update.py`（时效比对）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 法规总目录拉取与查询 | `catalog.refresh_catalog()` / `query_catalog()` | `api/routes_law.py` |
| 两个来源客户端 | `flk_client.search()` / `detail()` / `download()`；`govcn_client.search()` / `fetch_detail()` | `api/routes_law.py` |
| 法规入库 | `ingest.ingest_law_from_flk(bbbs)` / `ingest_law_from_govcn(url)` / `find_by_source()` | `api/routes_law.py` |
| 效力「点开即核验」 | `verify.verify_law(bbbs)` | `api/routes_law.py`（端点由集成方加） |
| 时效变更比对 | `update.check_law_updates()` | `api/routes_law.py` |
| 统一抓取出口 | `http.fetch_json()` / `download_file()` | 本包内全部客户端 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `ingestion` 的 `run_full_ingest` | 同仓 | 完整入库管线（解析、预览、条款修正） |
| LibreOffice headless / WPS / Word COM | 外部程序 | docx → PDF 转换 |
| `storage` | 同仓 | 落库与溯源字段 |
| flk / gov.cn 官方接口 | 外部服务 | 清单与下载 |

## 明确不做什么

- 🔴 **MUST NOT 抓白名单以外的域**：域白名单、UA、限速、重试、文件校验**唯一出口是 `http.py`**；所有抓取必须经 `fetch_json` / `download_file`，别绕过去直接发请求。
- **不做「网页文字版重排版」**：转换源头**只允许官方 docx**（`convert.py` 头注写死）。
- **不做效力判定**：现行 / 废止 / 被代替的状态来自官方字段，本模块只映射与展示。
- **不做更新自动落库**：`update.py` 是**纯只读比对**，不落库、不删除。
- **不自己解析版面**：复用 `ingestion` 的管线，不另写解析。

## 关键数据

| 表/对象 | 关键字段 | 说明 |
|---|---|---|
| 本地法规目录（`catalog.ensure_catalog_schema` 建） | 分类 / 标题 / `bbbs` / `sxx` | 全量清单，正文按需下载 |
| `law_manifest.json` | `bbbs` → `title` / `sxx` / `fetched_at` | 编目账本：支持断点（分类级 done）与增量 |
| `doc_meta` 的来源字段 | `source` / `source_id` | 回查库内文档对应哪个官方源 |
| `verify` 磁盘缓存 | `bbbs` → 核验结果 | 带 TTL |

## 改了它会影响谁

- **`api/routes_law.py`**：法规侧全部端点（编目、导入、核验、更新）
- **库内法规文档**：`doc_meta` 溯源与条款坐标链
- **`ingestion` 管线**：两边同构，改一边 MUST 两边一起看

## 已知边界（诚实）

- **接口状态核实于 2026-06**（见 `docs/LAW-SOURCE-PLAN.md` §1/§2 与两个客户端的 docstring）——**官方接口可能已变**。
- **`verify_law()` 绝不抛异常**：任何失败都降级为 `unverified`，调用方按字段读，别指望它报错。
- **对账差异只记 warning 不失败**：编目计数与官方聚合数不一致时不中断。
- **代码注释引的 `LAW_CATALOG_ONDEMAND_PLAN.md` 已不在仓库**（未核：是否已迁到别处）。
