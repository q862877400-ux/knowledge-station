# 全量语料获取与自动更新 方案（FULL_LIBRARY_PLAN）

> 2026-08-26 制定。需求来源：用户要求"把所有国标、所有法律法规全扒一次"——覆盖
> 目录获取、正文全量、更新感知（新发布/修订/新版）、自动下载入库。
> 前置资产：`docs/OPEN_SOURCE_FUSION_SURVEY.md`（2026-08-25 开源调研）、
> `docs/LAW_SOURCE_PLAN.md`（官方源管线）、`docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md`（状态核验）、
> 更新巡检模块（8 渠道）、law_catalog（法规目录 29,764 条已抓）、law_source（flk/govcn 下载入库）。

## 0. 现状盘点（已有什么）

| 能力 | 状态 | 证据 |
|---|---|---|
| 法规目录全量 | ✅ 29,764 条（法律 473 / 行政法规 811 / 地方法规 25,131 / 司法解释 846…） | law_catalog 表（flk 全量抓取） |
| 法规正文入库 | ⚠ 仅 24 部 | doc_meta 24 行 |
| 法规下载→转换→入库管线 | ✅ | law_source（flk docx→LibreOffice/WPS→PDF→run_full_ingest） |
| 国标状态巡检 | ✅ 8 渠道 + 动态路由（ndls/std.samr/hbba/dbba/ttbz/mee/mem_gov/mohurd） | 已实测发现 AQ 3028 废止 |
| 打开即核验 | ✅ flk sxx 分级 TTL + 单飞 + 降级 | verify.py / ValidityBadge |
| 找标准（Discover） | ❌ **搜索渠道失效**：`SEARCH_URL=openstd/db/search` 实测 404 | 真实入口 `/bzgk/std/std_list`（official_gb 已用） |
| 更新自动入库 | ❌ 巡检发现变更 → 人工确认只落状态，**新版正文不自动下载** | mark_ack 闭环刚补（状态）；下载未接 |

## 1. 需求拆分（小点清单，供逐条检阅）

### A. 正文全量获取
- **A1 法规正文批量下载**：目录已有 → 按分类/效力分批下载官方 docx → 转换 PDF → 入库。
- **A2 国标全文获取**：GB 强制 + 非采标推荐免费（2025-02 起发布 20 工作日内公开）；采标无全文。
- **A2.5 OCR 瑕疵自动修复（LLM 辅助，2026-08-26 立项）**：批量入库后（国标 3 万 + 法规）的 OCR
  质量清洗——规则筛可疑 → LLM 给建议修正 → 人工批量确认 → 落补丁闭环（详见 §2 A2.5）。
- **A3 国标目录获取**：全量题录（标准号/名称/状态/日期/代替关系）。

### B. 更新感知（变更监测）
- **B1 新发布监测**：flk `aggregateData` 最新列表 / gov.cn `sort=pubtime` 每日比对目录 → 新条目。
- **B2 修订/新版监测**：sxx=2（已修改）/ new_version 检测 → 触发下载新版。
- **B3 废止/替代监测**：✅ 已有（巡检 8 渠道，AQ 3028 实证）。

### C. 自动下载与更新闭环
- **C1 变更 → 自动下载新版**：确认 new_version/已修改 → 自动 reingest 新版本正文。
- **C2 增量入库**：file_hash 防重 + reingest 语义（已有）。
- **C3 定时任务**：每日巡检 + 新发布扫描（复用 scheduler）。

### D. 找标准修复与开源加速
- **D1 找标准搜索修复**：SEARCH_URL 404 → 改真实入口 + 解析。
- **D2 开源语料接入**：lawtext / LawRefBook / just-laws（许可合规前提）。

## 2. 逐项方案

### A1 法规正文批量下载（复用 law_source + bulk 模式）
- 来源：flk 官方（已有 download/pc API + 转换链 + 入库），**白名单域合规**。
- 执行：仿 `ingestion/bulk.py` 三阶段（快扫建清单 → 后台异步下载转换 → 入库入列）；
  按效力分级优先（法律 > 行政法规 > 司法解释 > 部门规章 > 地方法规）；
  日预算、每 N 条快照、断点续跑、quarantine 隔离（损坏/转换失败）。
- 幂等：source_id（bbbs）唯一；重复下载跳过（law_source.ingest 已有 find_by_source）。
- 产出：~2500 部法规正文（法律+行政法规+司法解释为主；地方法规 2.5 万部按需分级）。
- 工作量：3-5 人日（复用管线，主要是编排器）。

### A2 国标全文
- 免费部分：openstd `/bzgk/std/std_list` 搜索 + `viewGb` 下载（**有人机验证**：验证码 OCR，
  OpenSTD_Spider 方案是 ddddocr 自动过码，最多重试 10 次——可作为子进程外挂，不并入代码，GPL 隔离）。
- 采标（ISO/IEC 采用）无全文：只存题录 + 状态。
- 量级：~7 万条题录，免费全文占比以实际统计为准。
- 工作量：5-8 人日（验证码过码是最大不确定）。

### A2.5 OCR 瑕疵自动修复（LLM 辅助，四层流水线）

> 背景：批量入库后 OCR 瑕疵大量存在（实测 `l5 m`（1→l）、`≤slant`（已修）、`100m2` 粘连、
> `m ＞ 1 0 0 t` 数字拆散等）。**LLM 能识别一部分，但不能盲改证据文本**（幻觉性修正风险：
> 会把正确的 1A/Ⅰ级/型号"修"错——标准条款是证据，改错一条 = 数据可信度崩塌）。

- **① 规则筛查（零成本，已有）**：数据体检 5 类（换行残留/英文粘连/页脚泄漏/表格列数/脏单元格）
  + `is_suspicious`（OCR 置信度低自动标记）→ 产出可疑条款清单。
- **② LLM 精判（新增）**：只对可疑条款调用 LLM，输出
  `{原文本, 建议修正, 理由, 置信度}`——**只给建议不写库**；走 egress_audit 外发审计；
  无 Key/失败降级跳过。LLM prompt 含"数字/字母混淆仅在有上下文证据时修、型号/罗马数字/编号
  不可动、不确定输出 confidence<0.5 且不改"约束。
- **③ 人工确认**：建议进"待确认"面板（复用补丁确认队列模式），用户按理由批量过/拒。
- **④ 落补丁闭环**：确认后走 `clause_patch`——快照不可变、可撤销、修订留痕；
  与现有纠错/核验门禁衔接（确认修正不绕过核验）。

- **红线**：LLM 输出不经人工确认不得改证据文本；确认前不落库；补丁可撤销。
- **成本**：只对可疑条款调 LLM（非全库）→ 数量可控，~1k token/条 ≈ 几分钱，可批量离线。
- **触发时机**：国标 3 万 / 法规批量入库完成后跑一轮；后续新入库增量触发。
- **工作量**：2-3 人日（体检增强 + LLM 建议端点 + 确认面板复用现有补丁机制）。

### A3 国标目录
- 渠道：ndls `/api/standard/list`（跨门类，含废止日期/代替关系——巡检已在用，可复用）+
  std.samr `/noc`（状态权威）。建 `std_catalog` 表（类比 law_catalog）。
- 工作量：2-3 人日。

### B1 新发布监测
- flk `GET /law-search/index/aggregateData`（最新公布列表）每日拉取 vs law_catalog 比对 → 新 bbbs 入
  `update_change_event`（change_type='new_version'/库内无 → 提示下载）。
- gov.cn 政策库 `sort=pubtime` 同法。
- 复用 `update/scheduler.py`（已有定时线程模式）。
- 工作量：1-2 人日。

### B2 修订/新版监测
- 巡检已能报 new_version/已修改；增强：检测到后自动把"可下载的新版"加入下载队列（连 C1）。
- 工作量：1-2 人日。

### C1 自动下载新版（闭环最后一段）
- 流程：巡检/新发布发现变更 → 用户在三色报告/更新面板确认 → 确认 new_version/已修改 →
  自动调 `law_source.ingest`（flk bbbs）或国标 openstd 下载 → reingest 新版 → 旧版状态
  superseded + 影响面分析（已有）。
- 复用：mark_ack（已落状态）、reingest_laws.py（存量重建）、impact.py（影响面）。
- 工作量：2-3 人日。

### D1 找标准修复（快修，1 项）
- `discover.SEARCH_URL` 从 `openstd/db/search`（404）改为 `/bzgk/std/std_list`，解析结果行
  （复用 official_gb 的 hcno 提取 + 状态映射逻辑）。
- 工作量：0.5-1 人日。**建议先行**（用户实测失效）。

### D2 开源语料（P0 加速，调研已完成待拍板）
| 项目 | ★ | 许可证 | 用法 |
|---|---|---|---|
| [lawtext/laws](https://github.com/lawtext/laws) | 88 | 官方文本自由用 | **2000+ 部法规 docx 原件** → 直接喂现有管线（零改造） |
| [LawRefBook](https://github.com/RanKKI/LawRefBook) | 1844 | 文本可用（代码勿抄） | 最大 markdown 法规库（司法解释/部门规章分类）→ 解析器 |
| [just-laws](https://github.com/ImCa0/just-laws) | 770 | MIT | 311 部现行法律 100% 基线 → 与 flk 对账（修订/废止核验） |
| [cn-law-hub](https://github.com/ZongziForu/cn-law-hub) | 62 | 非开源（借清单） | 10 源状态核验（已研究，自行适配） |
| [OpenSTD_Spider](https://github.com/SocialSisterYi/OpenSTD_Spider) | 91 | GPL-3 | openstd 搜索/元数据/全文（子进程外挂，不并码） |

- 法律文本不受著作权保护（《著作权法》第五条）→ 数据可吞；**AGPL/GPL 只借思想/子进程隔离，代码不并入**。
- P0 落地优先级：lawtext docx 批量（最快覆盖 2000+ 部）> LawRefBook 解析器 > just-laws 对账。
- 工作量：25-40 人日（调研文档已给，实际复用管线可压缩）。

## 3. 实施顺序建议（依赖驱动，分批交付）

| 阶段 | 内容 | 依赖 | 交付物 |
|---|---|---|---|
| 0 | **D1 找标准修复** | 无 | 找标准恢复可用 |
| 1 | A1 法规正文批量 + D2 lawtext 语料 | D1、law_source、bulk 模式 | ~2000+ 部法规正文入库 |
| 2 | A3 国标目录 + A2 免费全文 | 无 | 国标题录全量 + 免费全文 |
| 3 | **A2.5 OCR 瑕疵自动修复**（规则筛→LLM 建议→人工确认→补丁） | 阶段 1/2 入库后 | 批量清洗 OCR 瑕疵，补丁闭环 |
| 4 | B1/B2 监测 + C1 自动下载闭环 | 阶段 1/2 | 新发布/修订自动入库 |
| 5 | C3 定时 + 看板 | 阶段 4 | 无人值守 |

## 4. 风险与边界

- openstd 验证码：免费全文批量最大不确定（打码方案；失败转半自动队列）。
- 地方法规 2.5 万部：量大，按用户关注地域分级（用户画像 region）。
- 官方接口变更：全部收敛 law_source/channels 单点；接口探测法已文档化（LAW_SOURCE_PLAN 附 A）。
- 版权边界：官方文本自由用；开源代码按许可隔离；只存本地不对外分发。

## 5. 国标存量体检（用户手头 3 万+ 国标文件）

- 现状：用户已自行下载 3 万多条国标文件，疑大量过期。
- 目标：批量判定每份文件的现行/废止/即将实施/查无状态。
- 方案 A（一次性体检）：扫描文件清单（文件名/PDF 首页提取标准号，复用 auto_tag 正则）→
  批量调 ndls（`/api/standard/list` + `/api/standard/detail`，直接给废止日期/代替关系）→
  输出清单 `标准号|名称|状态|废止日期|代替标准`；限速 ≥0.6s/请求、断点续查、结果缓存 30 天。
- 方案 B（长期维持）：3 万文件导入后进现有 tier1 全库滚动巡检（日预算 500 → 70 天一轮，
  已实现于 inspector + channels/ndls）。A 先行（一次体检），B 常驻。
- 国标新发布/修订监测：std.samr 公告 + ndls 最新列表每日比对（对应法规侧 flk aggregateData）；
  修订检测 = ndls 代替关系变化 / std.samr 状态变化；自动下载 = openstd 免费全文（验证码）+ 政策公开。

## 6. 开源依赖风险策略（别人不更新怎么办）

- **唯一不可替代依赖 = 官方源**（flk/gov.cn/openstd/ndls/std.samr，政府网站）；开源项目 = 前期加速器。
- 三层解耦：① 开源数据拿来即落库，落库后与源头无关；② 抓取代码全部自研（law_source/8 渠道
  基于官方源，不调用开源爬虫）；OpenSTD_Spider 仅作可选验证码工具（子进程隔离，停更 → 手动队列）；
  ③ 开源停更 → 降级官方源自抓（慢但可靠），库内数据不受影响。
- lawtext/LawRefBook 停更 → flk 官方源兜底；just-laws 停更 → 与 flk 对账自维护。
