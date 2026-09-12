# 法规总目录 + 打开即核验 + 按需下载 实施计划（待批准）

> 依据：docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md（核验细节）+ flk 批量爬取实施细节报告（lawtext/LawRefBook/just-laws 源码实读）。
> 范围：**仅法规侧**（国标维持现状：手动导入 PDF + 巡检三色报告；openstd 核验无验证码，列为可选）。
> 融合方式：全部自研实现进 `src/core/knowledge/law_source/` 与前端，不引第三方包、不做外部模块接口。

## 任务 1：法规总目录（只拉标题清单，不拉正文）

**做什么**：遍历 flk 官方库全量清单，录入本地「法规总目录」，前端目录树展示。

**实现要点**（源自 lawtext/LawRefBook 实测）：
- 全量列表：`POST /law-search/search/list`，`searchContent=""`（空词=全库）+ `flfgCodeId` 按分类枚举（enum_data 动态获取，勿硬编码）逐分类分页到尽；`order` 只用降序（升序会 500）
- **账本** `law_manifest.json`：每 bbbs 记 title/flxz/sxx/分类/抓取状态/时间（断点续传依据；`empty_url` 为终态避免无限重试）
- **对账**：`GET /law-search/index/aggregateData` 分类计数核对（防漏）
- 存储：SQLite `law_catalog` 表（title/bbbs/flxz/sxx/分类/公布日期/施行日期）
- 预计规模 ~2,500 部（lawtext 实测 total=2478；含已废止约 27%——**废止也收录**，标效力状态）
- 前端：目录树按分类分组 + 效力徽章 + 标题搜索

**验收**：目录 ≥2,000 条；aggregateData 对账一致；分类/效力分组与搜索可用。

## 任务 2：点开即核验（仅法规；国标可选）

**做什么**：用户点目录条目/打开已入库法规预览前，实时查效力状态，前端显示徽章。

**实现要点**（源自 cn-law-hub/OpenSTD_Spider 源码拆解）：
- 新适配器 `flk_law`（继承现有 ChannelAdapter + CurlCffiTransport，flk 的 JA3 WAF 已被覆盖）：`probe_law(title/bbbs)` → sxx 映射（1废止/2已修改/3现行/4未生效 → 现有 LEGAL_STATUSES）
- 端点 `GET /api/v1/laws/verify?bbbs=`：返回 `{status, evidence_url, checked_at}`
- **缓存分级 TTL**：现行 24h / 废止·已修改 7d / 未生效 6h / 未标注 12h / 查无 60s 负缓存 / 验证码不缓存；per-key 单飞锁
- **超时降级**：单请求 5s、总预算 8s；失败返回「未核验」灰徽章 + 重试按钮，**绝不阻塞预览**
- 国标（可选）：复用 official_gb 渠道（核验走 std_list/newGbInfo，**无验证码**——验证码只在全文下载）；默认关闭，你决定是否开

**验收**：点开预览显示效力徽章 + 官方证据链接；核验失败不阻塞预览；同文档短时间重复打开不重复打官方接口。

## 任务 3：按需下载预览

**做什么**：用户点目录条目 → 下载官方 docx → 转 PDF → 入库 → 打开预览；已入库直接打开。

**实现要点**：
- 复用已有 `law_source`（flk_client 下载 + convert 转换链 + run_full_ingest），零新管线
- 下载节奏：主站与 OBS 域分开限速（各 0.6s）、串行、`.part` 原子写（已有）
- **解析主路线**：flk 详情 `content.children` 官方章条树序列化（零解析错误）做结构对账；MinerU 管线出正文与 bbox（现状不变）
- 缓存：`law_source/flk/<bbbs>/` 已有目录结构复用——已下载直接打开（秒开）
- 前端：目录条目点击 → 校验徽章 → 「下载并打开」→ 进度提示 → 预览

**验收**：点目录条目全流程通（下载→入库→预览带高亮）；二次打开秒开；重复点击不重复下载。

## 工作量与顺序

| 任务 | 估时 | 依赖 |
|---|---|---|
| 1 法规总目录 | 2–3 人日 | 无 |
| 2 点开即核验 | 2–3 人日 | 无（可与任务 1 并行） |
| 3 按需下载预览 | 1–2 人日 | 任务 1（目录）+ 任务 2（核验） |

合计 **5–8 人日**。任务 1/2 可并行子代理开发，任务 3 收尾集成。

## 明确不做
- 国标打开时实时校验/按需下载（openstd 下载通道不稳定；时效由巡检三色报告覆盖；核验无验证码列为可选项）
- 第三波评测/审查（用户已否）
- 任何第三方包引入/外部模块接口（全部自研进 law_source/）

---

## 实施状态（实施中更新）

| 任务 | 状态 | 落点 |
|---|---|---|
| 1 法规总目录 | ✅ 完成 | `law_source/catalog.py`（refresh_catalog/query_catalog + law_catalog 表 + 账本 manifest）`tests/test_law_catalog.py`（10 用例全 mock 通过） |
| 2 点开即核验 | ✅ 完成 | `law_source/verify.py`（verify_law + 分级 TTL 缓存 + 单飞 + 超时降级）`tests/test_law_verify.py`、`renderer/ValidityBadge.tsx` |
| 3 按需下载 | ✅ 完成 | 前端 `renderer/LawCatalogPanel.tsx`（目录→核验→复用 `/laws/ingest`→打开）复用已有 ingest 管线，目录已入库秒开 |
| API 集成 | ✅ 完成 | `server.py` 增 `/api/v1/laws/catalog`(GET)、`/api/v1/laws/catalog/refresh`(POST)、`/api/v1/laws/verify`(GET)；`tests/test_law_source_api.py` 增 4 端点用例 |
| 前端挂载 | ✅ 完成 | `App.tsx` 运维诊断内新增「📘 法规总目录」`<details>`；`styles.css` 追加 `law-cat-*` 段 |

- 网络前提：flk 需在「规则模式」下直连（全局代理会掐 TLS 握手），见本计划 §任务1 与研究报告。
- 回归基线：全量 pytest 只涨不跌（本次新增 14 用例：catalog 10 + 端点 4）。
- 验收口径：目录刷新 ≥2,000 条、aggregateData 对账一致、分类/效力/搜索可用、点开显示徽章且不阻塞预览。
