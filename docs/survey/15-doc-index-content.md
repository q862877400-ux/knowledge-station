# 文档内容索引（每份讲什么）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

`summary` = 第一个 `# 标题` 之后、第一个非空且**不是** 引用/表格/列表/代码/图片 的行，上限 160 字。`h2_headings` 是全部二级标题（前 25 个）。**`summary` 为空说明该文档开头就是列表或表格**（比如索引类），不是它没内容。

## 二、总账

| 项 | 数 |
|---|---:|
| 文档 | **247** |
| 有首段摘要 | 241 |
| 没有（开头是列表/表格） | 6 |

## 三、每份文档讲什么

| 文件 | 行数 | 标题 | 首段 | 二级小节数 |
|---|---:|---|---|---:|
| `docs/ANNOUNCE-MODULE-STATUS-2026-10-08.md` | 164 | 部委公告监控 / 法规标准动态抓取 —— 模块现状（2026-10-08 代码通读） | 盯住用户配置的部委「公告栏 / 通知公告」列表页，**逐页翻**抓新公告 → 零 LLM 启发式解析 → | 8 |
| `docs/BROKEN-LINKS.md` | 66 | 已知断链台账（**不许静默忽略**） | 原先那两条（`tools/gov-qa/recon/ROUND-2026-10-08-{js,night}.md` 引 `SITE-REGISTRY.md` 少了 `../`） | 4 |
| `docs/CHANNEL-COVERAGE-PLAN.md` | 2,781 | 法规/标准「渠道覆盖 + 巡检」改造方案（长周期 · 多轮次） | 业主随消息附了一份**他自己初步调研**的报告（法规类 9 个项目名称多为"未核实"、标准类 6+ 个已核实、 | 8 |
| `docs/CODE-REVIEW-CHECKLIST.md` | 49 | 代码评审七条清单（含必验五种并入版） | 1. **判据有牙**：新增/修改的断言做过变异验证吗（改功能 ⇒ 断言必红）？有没有恒真/空过面 | 4 |
| `docs/DEVELOPMENT-HISTORY.md` | 524 | KnowledgeStation 开发历程简史 | 项目在无版本控制状态下从零建成：T00 契约冻结（SSE 顺序/六通道枚举/schema）→ 存储/检索/解析/核验逐层落地 → phase 1~14 全部完成，测试基线从 24  | 12 |
| `docs/ENCYCLOPEDIA.md` | 926 | KnowledgeStation 技术百科全书（ENCYCLOPEDIA） | 把**你机器上的本地资料**（法规标准 / **文献论文** / **开源项目文档与源码** / 公司制度 / 技术手册 / 个人笔记 —— **任何需要回头去查的资料**）变成* | 82 |
| `docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md` | 336 | 本地资料检索工具：下一步路线征询（v4） | （以下读数用的是旧题库中的 120 道题，即"headline 120"。） | 9 |
| `docs/GOVQA-UNWIRED-CHANNELS.md` | 465 | 未接线渠道清单（**给接线的对话用**） | 台账里每条渠道有两个**互相独立**的字段（这条纪律写在 `src/core/storage/channel_repo.py`）： | 6 |
| `docs/HANDOVER-2026-10-09.md` | 246 | 交接文档（2026-10-09 · KnowledgeStation 主体项目） | 你若同时手动开发，**先读它的交接单**（`archive/workbuddy-memory/memory/AUTO-CHAIN-HANDOFF.md`）再动手， | 13 |
| `docs/INDEX.md` | 291 | docs/ 总索引（机械生成，勿手改） | 生成命令（机械、可重跑）：`python scripts/docs/gen-doc-index.py` | 8 |
| `docs/INTERACTION-DESIGN.md` | 738 | 交互设计：向 WeKnora 学什么、我们怎么重做 | 本文后面几节写的是**方案**。方案与代码会对不上，所以这里单列"现在真跑着的是什么"： | 12 |
| `docs/INTRODUCTION.md` | 162 | KnowledgeStation 产品介绍 —— 让你自己机器上的资料，随问随查、点到原文 | 一篇论文 30 页，找「它用的学习率是多少」要从头读；一个开源项目的文档散在几十个文件里， | 8 |
| `docs/KB-FOLDER-PLAN.md` | 1,630 | 知识库多级目录 —— 施工单（业主 2026-09-21 定案） | 删除=**从这一处拿掉**，只有从所有目录都拿掉才真删。 | 34 |
| `docs/LAW-SOURCE-PLAN.md` | 307 | 法律法规官方来源获取方案（flk.npc.gov.cn + gov.cn） | 1. **来源白名单**：法律法规只从两个官方源获取—— | 12 |
| `docs/MATERIALS-PLANE-PLAN.md` | 1,394 | 材料平面与通用研究改造方案（v1 草案，待业主批准） | 必须同步更新的地方（**属红线/台账治理，需成组提交，不能零散改**）： | 13 |
| `docs/NEXT-DEV-PLAN-2026-09-28.md` | 657 | 后续开发计划（2026-09-28 会话收尾时制定） | 现状：门禁记账时会把**未跟踪文件里的用例**算进基线。那 5 条来自 `tests/test_jev_cn_baseline.py`（**git 不管它**）⇒ 文件一被删，棘轮 | 7 |
| `docs/NOT-DOING.md` | 126 | 已否决 / 已作废台账（**提任何新待办、计划、设计之前先对一遍这份**） | 先是"Word/PPT 交付物"，再是"bbox 高亮"（实际早就改成**红色定位箭头**）。 | 2 |
| `docs/PLAN-REAL-QUESTION-RULER.md` | 293 | 用真人问答造新评测尺子 —— 方案（草案 v1） | 并且**补上现有 96/171 条都没有的东西 —— 真实提问分布**。 | 9 |
| `docs/PORTABILITY.md` | 128 | 便携与路径纪律 | 写进**它**的数据目录，而插件去**它**的数据目录**读**同一个文件 | 4 |
| `docs/README.md` | 170 | KnowledgeStation 文件地图 | 下面是更正后的定性。** | 4 |
| `docs/REQUIREMENTS-v4.3.md` | 3,053 | 《通用国标与法律法规本地 AI 知识工作站 (Win11)》开发主计划 (v4.3) | 本套文档特点（v4.3 修订版）： | 12 |
| `docs/RETRIEVAL-LONG-RANGE-PLAN.md` | 1,500 | 检索与通用化：长周期计划 | 业主起点疑问：「用户不一定是专业人士…而且很多问题是隐性的」。 | 9 |
| `docs/ROADMAP-CLIENT-VIEW.md` | 120 | 路线图（客户视角）—— 短期 / 长期 / 效果 / 边界 | 项目 2026-09-17 已转向：从「法规问答工具」变成「**通用资料研究 + 交付工具**」，法条问答退成**其中一个数据源**。 | 8 |
| `docs/TEST-FLAKES.md` | 38 | 测试 flake 清单（已知偶发/竞态型，非回归勿背锅） | 1. 新偶发先跑 3 次单跑 + 1 次串行链——**单跑可复现 = 不是 flake**，按真缺陷查。 | 2 |
| `docs/UI-BASELINE.md` | 2,460 | UI 视觉基线（照 WeKnora 知识库管理复刻）—— 第 5 步的施工依据 | 上一轮 UI 难看的根因就是没有它）；③ 逐块映射到我们的页面/组件；④ DSH 宿主已提供、我们该用却没用（或手搓了） | 7 |
| `docs/UI-ICON-SYSTEM.md` | 130 | UI 图标体系（KnowledgeStation 插件） | KS **不自己画图标**，全部用宿主的 `@deepseek-ai/dsh-client-ui-primitives`。 | 6 |
| `docs/VISION-TREE.md` | 184 | KnowledgeStation 功能愿景（客户视角版） | ⚠ **另外两条本次一并澄清**（不属"过期"，属"口径要说准"）： | 12 |
| `docs/archive/README.md` | 68 | 归档区：这里放什么、怎么查 | 满足**其一**即进： | 5 |
| `docs/archive/handovers/HANDOVER-2026-09-23.md` | 57 | KnowledgeStation 交接文档（2026-09-23 晚） | 给接手的 AI 开发者。目标：把这个项目的收尾做完、把下面点名的问题修好。字数所限只给骨架；细读代码与 `docs/DEVELOPMENT-HISTORY.md`。 | 6 |
| `docs/archive/handovers/HANDOVER-2026-10-06.md` | 210 | 交接文档（2026-10-06 召回诊断） | 另加 1 条本轮新发现的**，然后逐条收口。 | 10 |
| `docs/archive/history/README.md` | 80 | 开发史明细归档（§10.1 – §10.203） | 逐轮明细**与 `git log` 高度重复**，读者要的是「从哪看起」，不是逐轮全文。 | 3 |
| `docs/archive/history/rounds-10.1-10.203.md` | 11,670 |  | `docs/MATERIALS-PLANE-PLAN.md` v1。方案里三处**经核实**的关键结论： | 136 |
| `docs/archive/impl-reports/B3A-REPORT.md` | 377 | B3a 实施报告 —— 「补全分类号」引擎侧第二轮（CCS 自愈） | 对照表与原因见 `docs/DEVELOPMENT-HISTORY.md` **§10.186**；`180397f` 另由 tag `verify-freeze-b3a-engi | 10 |
| `docs/archive/impl-reports/B3B-REPORT.md` | 188 | B3B-REPORT —— 「补全分类号」的**界面**半边（B3b） | 对照表与原因见 `docs/DEVELOPMENT-HISTORY.md` **§10.186**；这两笔另由 tag `prerebase-b3b` 保住，永远打得开。 | 7 |
| `docs/archive/old-plans/AUTO-DRAFT-PLAN.md` | 210 | 自动成文（系统起草结论）——立项论证与设计（2026-09-18） | 不建议做"全自动成文"（无人工确认直接落盘成报告）——理由见 §5。 | 10 |
| `docs/archive/old-plans/AUTORUN-PLAN-2026-09-24.md` | 103 | 自动执行清单（2026-09-24 全仓复盘后，业主授权全自动执行） | 按「必验五种」派独立复核（冻结 tag + 提取树 + 真拷贝两份 node_modules）→ 登记残余。 | 4 |
| `docs/archive/old-plans/BASELINE-PLAN-2026-10-06.md` | 225 | 基础层实验路线（2026-10-06 定） | 而是"**标题成为后代条文的上下文**"。这两个问题不同，后者便宜得多。 | 8 |
| `docs/archive/old-plans/CHANNEL-R6C-DESIGN.md` | 228 | R6c 设计：五类监控打通 + 巡检降级链来自台账（只出设计，不动代码） | ⇒ 结论：**零件差一层，且差一块数据**——缺的是"按问题选渠道"这一层； | 6 |
| `docs/archive/old-plans/EXECUTION-PLAN.md` | 78 | 执行计划（自主执行台账）—— 业主 2026-09-19 全权授权 | 或「⏸ 待做（原因）」。**它是进度的唯一真源**，细节在各步的归属文档里，不在这里抄。 | 2 |
| `docs/archive/research-process/BASELINE-DIAGNOSIS-2026-10-06.md` | 207 | 基础层诊断记录（2026-10-06） | 1. **规模是千万级，这是事实，不是假设。** | 9 |
| `docs/archive/research-process/CHANNEL-PROBE-REPORT.md` | 80 | 标准官方渠道时效巡检选型实测报告 | 测试方式：python requests 3.14 + curl.exe 8.21（Schannel），浏览器 UA（Chrome/126 Win64），每渠道 ≤3 次请求。 | 4 |
| `docs/archive/research-process/DSH-ALIGNMENT-AUDIT.md` | 160 | DSH 适配审计与整改清单（2026-09-19） | 「客户端半边 / 宿主半边 / 工程与流程」，每条都要**两侧 `file:line` + 官方原文引用**， | 3 |
| `docs/archive/research-process/GOVQA-DIAGNOSIS-2026-10-10.md` | 233 | gov-qa 模块全面诊断（2026-10-10） | 1. **它完全在门禁之外。** 本仓门禁（`scripts/run-gates.ps1`）**一步都不跑它**；根 pytest 的 `testpaths=["tests"]`  | 7 |
| `docs/archive/research-process/PROJECT-CONSOLIDATION-2026-10-05.md` | 146 | 项目盘整（2026-10-05）：第一性原理看文档与进度 | 113 份文档、5.3 MB，其中 **37 份只被引用过 1 次**，**13 份零引用**， | 7 |
| `docs/archive/research-process/PROJECT-STATUS-2026-10-05.md` | 120 | 项目状态与卡点（2026-10-05） | 它是三条总判据里前两条（**换词可对**、**排得上去**）的执行层。 | 6 |
| `docs/archive/research-process/REALTIME-VALIDITY-VERIFY-RESEARCH.md` | 381 | 法规/国标效力「打开即核验」实施细节报告 | 1. **显式效力状态只有三类源有**： | 6 |
| `docs/archive/research-process/STD-STATUS-CHANNELS.md` | 80 | 国标有效性查询源分类与多渠道备份矩阵（2026-08-27 实测定型） | （4/5/6 类）openstd 全部查无——此前 270 条 miss（53%）的根因。**cssn 一渠道覆盖 1-6 类**。 | 5 |
| `docs/archive/research-process/WSL2-VLM-BACKEND-DECISION.md` | 47 | 决策记录：WSL2 解锁 vlm/hybrid 本地后端 —— 否决（2026-09-14） | 评审 R6 指出：「无 WSL」被当作恒真约束，但「安装 WSL2 解锁 MinerU vlm/hybrid 本地后端」 | 4 |
| `docs/archive/review-briefs/README.md` | 104 | 复核任务书（VERIFY-BRIEF）与复核结论的归属层 | 此前任务书写在 `var/tmp/VERIFY-BRIEF-bNN.md`，而 `var/tmp/` 被 [.gitignore(../../../.gitignore) 整体忽略 | 3 |
| `docs/archive/review-briefs/VERIFY-REPORT-ingest.md` | 635 | 独立复核报告 — `verify-freeze-ingest`（批次：`reference` 效力档 | 复核者：独立复核代理（证伪导向）。复核对象：冻结提交 `1da33f8`（tag `verify-freeze-ingest`）， | 5 |
| `docs/archive/review-briefs/VERIFY-REPORT-jev-b1.md` | 568 | VERIFY-REPORT-jev-b1 | 冻结区间的主要新增判据不是恒真：本轮要求的 **9/9 必测变异全部变红**，额外“更宽词表”也变红；11 条 Python 用例真实执行、没有 skip；Jev/引擎不可用时宿主 | 12 |
| `docs/archive/review-briefs/announce-nav-cleanup-20260924.md` | 48 | 真库清理留档：22 条"栏目导航"型误发现（2026-09-24） | 而当时的日志写在 `var/tmp/real-cleanup.log` —— 那个目录被 `.gitignore` 挡着，收尾清树会连证据一起没 | 4 |
| `docs/archive/review-briefs/b1b2-brief.md` | 85 | 复核任务书 —— B1（重导丢归属）+ B2（叠字检查两个假绿洞） | `<<WORKTREE>>`（父代理用 `git worktree add --detach` 建好，冻结 tag `<<TAG>>` = `<<HEAD>>`）。 | 6 |
| `docs/archive/review-briefs/b1b2-report.md` | 345 | 独立复核报告 —— B1（重新解析丢目录归属）+ B2（叠字检查两个假绿洞） | 复核树：`D:\AI\work space\zcode-verify-b1b2`（冻结 tag `verify-freeze-b1b2`） | 6 |
| `docs/archive/review-briefs/b3a-engine-report.md` | 458 | 独立复核报告 —— KnowledgeStation「补全分类号」引擎半边（B3a）两笔提交 | 探针前后对 `knowledge.db` 与 `knowledge.db-wal` 各做一次 sha256：**两者都一字未变**（原始输出见 §A.3） | 21 |
| `docs/archive/review-briefs/b3b-ccs-ui-brief.md` | 101 | 独立复核任务书 —— B3b「补全分类号」的**界面半边** | `[Environment]::CurrentDirectory` ⇒ 用相对路径会写到主仓去）。 | 6 |
| `docs/archive/review-briefs/b3b-ccs-ui-report.md` | 467 | 独立复核报告 —— B3b「补全分类号」的**界面半边** | 实跑核过；`git merge-base --is-ancestor 12cb6b0 aaad270` ⇒ exit 0） | 11 |
| `docs/archive/review-briefs/b5-gate-brief.md` | 80 | 复核任务书 —— B5：门禁「环境白名单只增不减」的修法（含门禁临时目录自清） | `<<WORKTREE>>`（冻结 tag `<<TAG>>` = `<<HEAD>>`，`git worktree add --detach` 建的）。 | 6 |
| `docs/archive/review-briefs/b5-gate-report.md` | 332 | B5 门禁复核报告 —— 「环境白名单只增不减」的修法（含门禁临时目录自清） | 复核代理（独立，非本批作者）。冻结树 `D:\AI\work space\zcode-verify-b5`，tag `verify-freeze-b5-gate`。 | 10 |
| `docs/archive/review-briefs/b6-p0-report.md` | 466 | B6 定向独立复核 — 09-23 两提交（P0 黑屏修 / 棘轮基线记新） | 复核树：`D:\AI\work space\zcode-verify-b6`（`git worktree add --detach`，冻结标签 `verify-freeze-b6- | 7 |
| `docs/archive/review-briefs/ccs-chain-report.md` | 478 | 独立复核报告 —— 「分类号（CCS）三层查询链 + 补全自愈」 | 复核树（唯一读写面）：`D:\AI\work space\zcode-verify-ccs`（detached，标签 `verify-freeze-ccs-chain`） | 8 |
| `docs/archive/review-briefs/d508773-report.md` | 172 | 独立复核报告 — `d508773`（"③假绿补硬：复核点名三处验收牙加硬"） | 复核树：`D:\AI\work space\zcode-verify-d508`（冻结 tag `verify-freeze-d508773`）· 主仓只读 | 9 |
| `docs/archive/workbuddy-memory/README.md` | 59 | 归档：项目内 `.workbuddy-ai/`（WorkBuddy 自动链的记忆与交接） | 业主 2026-10-10：「**workbuddy 现在已经不用了**，要是没啥别的影响把这些东西删除掉好了」。 | 6 |
| `docs/archive/workbuddy-memory/memory/2026-10-08.md` | 26 | 2026-10-08 工作日志（workspace: zcode） | 「未归属」414 → 0；三级（省+市+县）归属 3,053 → **9,016 条**。 | 1 |
| `docs/archive/workbuddy-memory/memory/2026-10-09.md` | 2,110 | 2026-10-09 工作日志（workspace: zcode） | ① 主产品本体；② `tools/gov-qa` 政务问答采集（造考卷/补料清单，两个对话共写）； | 57 |
| `docs/archive/workbuddy-memory/memory/2026-10-10.md` | 135 | 2026-10-10 工作日志 | ⇒ 旧口径（`recurring` / `scheduledAt` / 自链）**整段作废**。 | 6 |
| `docs/archive/workbuddy-memory/memory/AUTO-CHAIN-HANDOFF.md` | 82 | AUTO-CHAIN 交接单（每轮覆盖写） | ✅ **门禁全绿**（最近一次 `-Full` = **12/12 · exit=0**，2026-10-10 15:53，pytest 2893 passed / 0 faile | 5 |
| `docs/archive/workbuddy-memory/memory/CHAIN-UNCLOSED-AUDIT.md` | 314 | 自动推进链「忽略 / 没收口」审计（2026-10-09 人工轮） | 总纲里那批"已登记的缺陷/待办"几乎原封不动** —— 其中有 3 条**连一句话都没被提过**。 | 10 |
| `docs/archive/workbuddy-memory/memory/HANDOFF-CHECKLIST.md` | 94 | 交接清单 · KnowledgeStation（`D:\AI\work space\zcode`） | ⚠ **门禁步数会变**（实测走过 **9 → 11 → 10 → 11 → 12**）⇒ **`9/9` 口径已作废，一律读 `N/N`**。 | 6 |
| `docs/archive/workbuddy-memory/memory/MEMORY.md` | 66 | 项目长期记忆（KnowledgeStation / D:\AI\work space\zcode） | — | 7 |
| `docs/archive/workbuddy-memory/memory/automations/1b206fd3-357f-47a1-bf5b-e17ec5c419a3/memory.md` | 457 | 自动续接链执行记忆（1b206fd3-357f-47a1-bf5b-e17ec5c419a3） | `scripts/verify-pssa-command-layer.ps1`、`scripts/pssa-guard.ps1`、 | 16 |
| `docs/archive/workbuddy-memory/memory/automations/3b1225b1-e2f4-4504-ad29-581309175fdb/memory.md` | 3 | 看门狗执行记录（KS 自动续接） | — | 0 |
| `docs/archive/workbuddy-memory/memory/automations/7d23d426-8743-431f-a95e-62a3e2a6af36/memory.md` | 477 | 自动化执行记忆：gov-qa 推进到全国省市全覆盖 | （`^{commit}` 已核 = `d5bc982` = HEAD）。 | 6 |
| `docs/naming-convention.md` | 115 | 命名与分类规范（正式件） | 按"文档全小写"去改它，会断掉每一个 `import`。 | 9 |
| `docs/research/ARROW-CONFLICT-AUDIT-2026-10-12.md` | 146 | 红箭头为什么"还是没生效"—— 旧代码与现状的对照核查（2026-10-12） | 业主令：「你先阅读那个最开始的代码，因为这个功能你刚开始是有的，最原始的设计， | 6 |
| `docs/research/ARROW-ROOT-CAUSES-2026-10-12.md` | 124 | 红箭头画不出 —— 全部根因（2026-10-12，逐条实测） | 业主令：「你先把所有根因都查清楚，然后一次性修复，设置好目标自动进行」 | 6 |
| `docs/research/CHANNEL-SYSTEM-AUDIT-2026-10-12.md` | 143 | 采集/更新通道系统核实报告（2026-10-12，纯读代码 + 读库） | 业主问：「我不是做了一套自动嗅探各个网站的法规和标准的更新动态，然后根据更新动态去下载 | 8 |
| `docs/research/DECISION-TABLE-2026-09-28.md` | 136 | 对策表：抄哪一处 / 不抄哪一处 / 我们独有的那一条 | ⚠ **F1–F4 的反面也要记**：Zeta Alpha 这类**已上线商业产品没有提问记录层、没有失效机制、记忆无上限常驻** ⇒ | 8 |
| `docs/research/FINDINGS-INBOX-2026-09-28.md` | 764 | 收件箱：调研线回传的"可借鉴结果"（我逐条读过并挑出来的） | 我此前对业主说"要抄旧依据不删、只标失效"。**这一步的做法不能抄。** | 5 |
| `docs/research/HANDOFF-external-solutions.md` | 276 | 交接任务书：把「我们当前未解的问题」的外部解法找齐 | 产出：**一张对策表，每行三栏 —— 抄哪一处 / 不抄哪一处 / 我们独有的那一条。** | 11 |
| `docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md` | 88 | Hindsight 官方能力核实 —— 「我们是不是在造轮子」 | 本机副本 `%TEMP%\hs-docs\openapi.json`；解析脚本 `var/tmp/hs-openapi-dump.py`（端点清单）、`hs-verify-clai | 6 |
| `docs/research/HINDSIGHT-DEPLOYMENT-STATUS-2026-09-30.md` | 213 | Hindsight 本机部署现状交接说明 | ⚠ **重要操作约束**（我今天踩过）： | 10 |
| `docs/research/HINDSIGHT-DOCS-READING-2026-09-28.md` | 996 | Hindsight 官方文档 · 通读纪要（一手件，已核到行号） | 22,747 B、`<title>` 只有 "Hindsight" 的 404 壳**。⚠ **HTTP 200 但不是正文**——本项目已多次栽在这条上。 | 18 |
| `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md` | 644 | Hindsight 部署：对一份外部 AI 分析报告的事实核查（2026-09-30） | 实机 16 个库（`GET /v1/default/banks`）。两个探针库确认存在： | 7 |
| `docs/research/MEMPALACE-REVIEW-2026-09-30.md` | 785 | MemPalace 调研 + B站介绍视频评论区核查 | 1. **它的架构方向，恰好是我们对 Hindsight 最不满意的那一条的反面**——它**原文一字不动地存**，不摘要、不抽取、不改写。Hindsight 是把原文抽成事实、并 | 10 |
| `docs/research/MODEL-AVAILABILITY-2026-09-28.md` | 73 | 调度记录：免费模型逐个真调（2026-09-28） | `stealth/space-bunny-alpha` 的错误逐字： | 5 |
| `docs/research/P0-4B-EVIDENCE-2026-10-14.md` | 233 | P0.4b 取证报告：通道 A/D/E 的排序键**到底有没有用** | P0.4b 那一行同时写着两组数（原话保留、更正在后）： | 6 |
| `docs/research/PAPER-可信政务问答技术-软件学报2026.md` | 126 | 论文精读：《大语言模型驱动的可信政务问答技术》（软件学报 2026） | · 用**上下文学习**（指令里带任务相关案例）；**服务场景更新时由领域专家加典型案例**即可适应。 | 5 |
| `docs/research/RETRIEVAL-LITERATURE-SCAN-2026-09-30.md` | 344 | 检索文献调研（2026-09-30）：我们这个问题在学界叫什么、已经做到哪一步 | 总览：[arXiv 2601.20671](https://arxiv.org/abs/2601.20671)（作者含 UNC / CMU / Jena）。 | 6 |
| `docs/research/RETRIEVAL-RESEARCH-LEDGER-2026-09-30.md` | 147 | 调研台账（防失忆）—— 2026-09-30 会话 | 当前停在「文献调研第二轮读完，等着决定要不要读剩下的页，以及要不要把'路由信号'那条登记进总纲 P4」。 | 8 |
| `docs/research/REVIEW-PLAN-A-verification.md` | 138 | 评审任务书 A：事实核查（交给能力一般的 AI） | 一个叫 KnowledgeStation 的中文法规/国标知识库（仓库 `D:\AI\work space\zcode`）， | 6 |
| `docs/research/REVIEW-PLAN-B-innovation.md` | 160 | 评审任务书 B：路线级独立评审与超越（交给最强的 AI） | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` 是这一条线的施工总纲（740 行，含全部历史实测与判据）；先读它的 §1.2 与 §1.4。 | 8 |
| `docs/research/SELF-CONTAINED-求助外部AI-检索召回上不去.md` | 424 | 一份自包含的求助文档：**我们的检索召回上不去，接下来该走哪条路？** | 用户用**大白话**提问（例如"车间墙角那个呼呼吸空气测细菌的小圆盒子，是干什么用的？"）， | 8 |
| `docs/research/STANDARDS-AND-RETRIEVAL-DIRECTION-2026-10-05.md` | 126 | 外部标准与检索方向调研（2026-10-05） | 1. **OKF 你的产品用不上；ARD 才可能真成标准，而跟它只需几行 JSON。** | 5 |
| `docs/research/STEP6-WORKORDER.md` | 1,043 | 第 6 步施工单 —— 插件侧借鉴 WeKnora 自带 DSH 插件的 6 条 | 直接决定第 1 条的形态——**不许**照抄 WK 的 141 行自制校验器，因为 DSH 有现成的（下 §1）。 | 10 |
| `docs/research/SURVEY-两条核实-GuRE语料性质与RefWalk表义.md` | 133 | 两条待核实的**核查结果**（GuRE 的语料性质 / RefWalk 的表义） | （基线是作者自己挑的，不是社区公认的强基线）。 | 4 |
| `docs/research/SURVEY-口径核查与多跳（回应业主两条批评）.md` | 179 | 他们的"有效"到底拿什么量的？（口径核查）+ **多跳这件事** | 我上一轮写「给条文加标题 = F2 +0.0840、占 40.5%」「GuRE nDCG@10 +32.96」， | 6 |
| `docs/research/SURVEY-学术界怎么设计政务问答（沿36条参考文献）.md` | 110 | 学术界的政务问答是怎么设计的（沿《可信政务问答技术》36 条参考文献调研） | 图书情报知识, 2023, 40(6): 98–111. doi: `10.13366/j.dik.2023.06.098`（武汉大学期刊站有全文） | 6 |
| `docs/research/SURVEY-学术调研-总清单（要落地看这一页）.md` | 115 | ★ 学术调研 · 总清单（四轮汇总，**要落地看这一页**） | · **出处**：arXiv `2406.15313`（*STARD: A Chinese Statute Retrieval Dataset with Real Queries  | 7 |
| `docs/research/SURVEY-学术调研-第1轮-排序与评测集.md` | 164 | 学术调研 · 第 1 轮：**排序/重排**与**评测集**（对应我们的判据①②） | （arXiv，`ar5iv.labs.arxiv.org/html/2606.29947`）。**我读到的是完整摘要**（正文未逐段读）。 | 5 |
| `docs/research/SURVEY-学术调研-第2轮-查询改写与官方标准.md` | 153 | 学术调研 · 第 2 轮：**LLM 查询改写**与**同类系统/官方评测标准** | （Natural Legal Language Processing workshop），`https://aclanthology.org/2025.nllp-1.31/`。 | 6 |
| `docs/research/SURVEY-学术调研-第3轮-还债与收敛.md` | 157 | 学术调研 · 第 3 轮：**还债 + 四条主线收敛** | （arXiv `2406.15313`；`ar5iv.labs.arxiv.org/html/2406.15313`，**我读了摘要全文**）。 | 6 |
| `docs/research/SURVEY-学术调研-第4轮-STARD可用率与总结论.md` | 189 | 学术调研 · 第 4 轮：★ **把 STARD 量成了我们现成的考卷** | Models**（NeurIPS 2023 Datasets & Benchmarks；arXiv `2308.11462`；`github.com/HazyResearch/le | 6 |
| `docs/research/SURVEY-学界做法值不值得抄-效果与工作量评估.md` | 172 | 学界做法**到底值不值得抄**：效果、工作量、能不能纯写代码 | 1. **加 RAG 的增益是 +0.002 ~ +0.046**（最大那条是 chatGPT+BM25 的 +0.046）； | 6 |
| `docs/research/SURVEY-标准与法规问答调研（含王芳2023全文精读）.md` | 198 | 扩大到"标准问答 / 法规问答"的调研（不限于政务问答） | doi `10.13366/j.dik.2023.06.098`。**PDF 已下载并抽全文**（14 页 / 40,524 字， | 7 |
| `docs/research/TECH-PATH-2026-09-28.md` | 213 | 技术路径：通用资料检索 + 派生记忆（2026-09-28 定稿） | 两块要裁决；**最便宜、已被本机证明的下一刀是 B3 修 rerank 恒等置换**（恢复 fastembed 契约）， | 7 |
| `docs/research/agent-memory-systems.md` | 544 | Agent 记忆系统：技术路径、实测效果、以及"RAG ↔ 记忆"的中间形态 | 这次调研给出的答案分三句：** | 7 |
| `docs/research/archify/01-archify-逆向.md` | 738 | archify 逆向：它靠什么产出「结构 + 证据指向」 | archify 的「证据聪明」不在画得好看，而在于它把**每一句论断、每一个图节点都编译成一条可机器复核的引用**：正文用 `[](source:id)` 挂上标编号，图节点用行尾 | 10 |
| `docs/research/archify/02-ks-现状.md` | 1,063 | 02 · KS 现状：问答 → 答案呈现 → 证据跳转（事实清单） | KS 的问答链路是「**引擎产出结构化 JSON（证据 + 两段自由文本 + 核验块）→ 模型自己按提示词写成 Markdown 三段式 → 宿主按 Markdown 渲染 → 证 | 9 |
| `docs/research/archify/03-借鉴结论.md` | 207 | archify 对比与借鉴结论 | 它把证据做得像证据，是因为它把编号、上标、页脚列表、结论先行、一屏一问都做成了可执行的编译期规则；而在「这条证据到底支不支持这句话」上，它只校验了**位置存在**（DOM 里有没有 | 8 |
| `docs/research/channels/PATH-REGISTRY-2026-10-08.md` | 428 | 法规/标准发布源路径总表（2026-10-08 实测） | 代码改动：`src/core/update/announce.py`（删 `SOURCES_MAX` + 新增 `_scan_soft_cap_s()` 可配置）、 | 8 |
| `docs/research/channels/REGISTRY-STATUS.md` | 378 | 渠道台账状态快照（自动生成，勿手改） | 它们不是「没轮到」，而是「这个对象没有独立可探的页面/接口」； | 3 |
| `docs/research/channels/internal-inventory.md` | 827 | 内部渠道拆解（internal inventory） | 1. **降级链不是写死在 inspector 里的**。`inspector.CHAIN`（`inspector.py:62`）是遗留常量； | 8 |
| `docs/research/channels/law-cn.md` | 1,354 | 中国法规类渠道调研报告（一手官方发布与查询渠道） | 1. [国家法律法规数据库（flk.npc.gov.cn）](#1-国家法律法规数据库flknpcgovcn) | 11 |
| `docs/research/channels/oss-decomposition.md` | 1,267 | 法规/标准获取与监控 · 开源项目**代码级**拆解 | 1. **`viewGb?hcno=` 直出真 PDF，但要用 `%PDF-` magic 验收**：`_download_direct()` 同时查 `Content-Type` | 22 |
| `docs/research/channels/std-cn.md` | 1,145 | 中国标准类官方渠道实测调研 | 1. **`std.samr.gov.cn` 与 `*.sacinfo.org.cn` 暴露了免登录、免验证码的 JSON 接口** | 9 |
| `docs/research/classical-chinese-segmentation-evidence.md` | 246 | 古籍/文言资料上的切分口径证据（P3.2） | 1. **计划里 P3.2 的那两个判据，只有后半截能定案。**「中文单字占比」是**机制代理量**： | 11 |
| `docs/research/cross-language-retrieval-evidence.md` | 305 | 非中文资料上的检索口径证据（英文开发文档 / 技术文档） | 根因是检索表用的 FTS5 分词器不做词形还原（`tokenize='ascii'`，`src/core/storage/schema.sql:107-117`）， | 12 |
| `docs/research/cross-plane-jump-assessment.md` | 283 | 跨平面交叉引用（法条 ↔ 你自己的文档）：评估与待决方案 | ⚠ **第三条收窄了现有纪律**：`docs/CODE-REVIEW-CHECKLIST.md` 把"**采集每次先问**／安全面只紧不松"列为评审面。 | 11 |
| `docs/research/dsh-official/ERRATA-alpha.2.md` | 322 | 勘误：`alpha.1 → alpha.2` 对 8 份分片与记忆条目的影响 | 下面逐条列**哪句话过期了、现在是什么**。没列到的，就是**核过没变**。 | 12 |
| `docs/research/dsh-official/INGEST-LEDGER-docs-zh.md` | 183 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-notes-client-ui.md` | 27 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-notes-zh.md` | 1,118 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-notes.md` | 1,122 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-agents.md` | 22 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-docs.md` | 29 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-readme-zh.md` | 363 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-readme.md` | 363 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-repo-docs.md` | 190 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-root.md` | 29 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER-skills.md` | 45 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/INGEST-LEDGER.md` | 188 | DSH 官方文档原文入库账本 | 核对方式：对每篇 `GET /documents/<id>` 取回 `original_text`，算 sha256 与磁盘文件的 sha256 比对（**逐字级证明**）。 | 0 |
| `docs/research/dsh-official/README.md` | 111 | DSH 官方文档精读（8 份分片） | 覆盖 `docs/`（基线时 167 篇英文正本 / 现 171 篇）与相关 `.agents/notes/`（2056 篇决策记录）中**与插件开发相关的部分**。 | 3 |
| `docs/research/dsh-official/REALIGN.md` | 284 | DSH 升级后：文档与记忆的重对齐手册 | 都是**对着某一个 DSH 版本**写的。升级后它们可能过期——而**过期不会报错**，只会让人写出对不上宿主的行为。 | 8 |
| `docs/research/dsh-official/dshdocs-A.md` | 87 | DSH 客户端插件（右栏 UI）开发摘要 | 阅读范围（仅英文原文）：`docs/subsystems/sidebar-right.md`、`web-client.md`、`client-modules.md`、`client | 5 |
| `docs/research/dsh-official/dshdocs-B.md` | 137 | DSH 插件作者摘要（Host + Client 两半） | `ctx.set` 只有提供者 fiber 能调，名字未提供时抛错（`context.md:279`）。 | 6 |
| `docs/research/dsh-official/dshdocs-C.md` | 173 | DSH 文档消化 · 面向「在 DSH 内做功能」的插件作者 | — | 6 |
| `docs/research/dsh-official/dshdocs-D.md` | 123 | DSH 官方文档消化：工具 / LLM / 会话 / 子代理 | 先查 `tool-catalog.md`（**生成物**：`scripts/gen-tool-catalog.ts`，`pnpm run gen-tool-catalog` 再生成 | 7 |
| `docs/research/dsh-official/dshdocs-E.md` | 149 | DSH 官方设施速查（插件作者版） | 来源：`D:\AI\DSH\deepseek-harness\docs\`。只读英文原本，跳过 `*.zh.md` / `*.i18n.yaml` / `persistence-c | 8 |
| `docs/research/dsh-official/dshdocs-F.md` | 81 | DSH 文档消化：插件作者防重复踩坑（F） | 覆盖范围：`docs/postmortem/`(5)、`docs/i18n/`(5)、`docs/persistence-changes/`(4，不含 `historical-fo | 6 |
| `docs/research/dsh-official/dshdocs-G.md` | 140 | DSH decision-record digest — third-party external  | Repo `D:\AI\DSH\deepseek-harness`; all `file:line` are against that checkout. `.md` (Engli | 6 |
| `docs/research/dsh-official/dshdocs-H.md` | 92 | DSH 官方技能与门禁摘要（H） | 源仓库根 `D:\AI\DSH\deepseek-harness`；下文所有 `file:line` 均相对该根。 | 5 |
| `docs/research/four-layer-pipeline-evidence.md` | 261 | 四层检索链路：别人怎么做 / 我们缺什么（对账单） | （最早的三层粗分、八份设计各自的 L0–L8、本文的四步、以及第 3 步内部的"第一层"）， | 8 |
| `docs/research/golden-instrument-audit.md` | 370 | 评价尺子审计：金标门禁测的不是产品所在的世界 | 命中判据**只比条款号**（不比是哪本标准的条款号）。**该缺陷已于同日修复**（见 §九）。 | 13 |
| `docs/research/hindsight-official/README.md` | 54 | Hindsight 官方文档本地副本 | 外加接口说明（OpenAPI）。共 42 篇，见 [`referenced-files.txt`](referenced-files.txt)。 | 3 |
| `docs/research/jev-mem-assessment.md` | 160 | Jev-Mem 影响评估（2026-09-24） | 把高频、输出有界的判断从大模型手里拿走。我们已用它做合规哨兵；这篇论文把它扩展到**检索路径**上 | 7 |
| `docs/research/ks-fixes/01-d2-rootcause.md` | 320 | D2 冒烟失败根因分析（只读分析，未改任何代码） | 1. **定性：既有缺陷，与 2026-10-19 超时/重试改动无关。** 本轮改动只碰 `plugin/src/index.js`（两处 `timeoutMs` 120s→30 | 7 |
| `docs/research/ks-fixes/02-modality-residual.md` | 555 | 模态核验残留误报：根因与修复方案（2026-10-19 真机实测） | 1. **「不应」被定得比「应」高，但这不是方向写反**：`MODALITY_STRENGTH` 里 `'应': 3`、`'不应': 4`。按表算 `应 -> 不应` 就是 `st | 22 |
| `docs/research/ks-fixes/03-waiting-feedback.md` | 322 | 等待期前台提示：现状盘点 + 外部借鉴（只分析，未改代码） | 1. **「完全没时间感」这个前提不成立**。宿主对话区（模型回答那个气泡）**已经有秒级计时**：`chat.deepDivingFor` = `"深度求索中，用时 {durat | 9 |
| `docs/research/lay-gap-decomposition.md` | 757 | 大白话那道缺口怎么拆、哪条路能走：四条实测 | 而且这一步**必须靠外部资源**——库内的证据只够覆盖缺口的 **20.9%**。 | 11 |
| `docs/research/lay-language-retrieval-evidence.md` | 175 | 用户用大白话提问时，检索怎么接住——外部证据 + 本库实测 | 另一侧反例：**BSARD**（法律、2.26 万条法条、**有监督微调**）稠密**显著赢**（74.8% R@100）——但规模比我们现在的库还小 20 倍，且有标注。 | 8 |
| `docs/research/lay-phrasing-prompt.md` | 91 | 「大白话 ↔ 行话」生成提示词（A 组：给术语写外行说法） | 这是**每个术语的属性**，只有加术语才能把它测准；加同术语的条数只增加噪声。 | 5 |
| `docs/research/lay-phrasing-retrieval-test.md` | 98 | 拿"大白话"真搜一遍：50 个术语 × 100 条外行说法 | 跨 19 个 CCS 领域（**不是**我手挑的）。 | 7 |
| `docs/research/lay-phrasing-scaleup-test.md` | 154 | 放大到 2000 条之后：50 术语那轮的结论哪些站住了、哪些变了 | ⚠ 两批**都是新版提示词（v2）的产物**（每条带 `register`、每术语 4 条）—— | 8 |
| `docs/research/papers/README.md` | 54 | 外部原件存放处（检索文献调研） | ⚠ **三条路里只有第三条通：** | 3 |
| `docs/research/plan-vs-reality.md` | 185 | 计划特性 × 谁做到了（逐条对照） | 共 **72 条 R 编号需求**（R1–R79，其中若干编号未使用）+ **14 条法规合规专项**（R-L1~R-L14）+ **六条 MUST NOT 红线**（§0.1）。 | 8 |
| `docs/research/rag-encyclopedia-study.md` | 220 | RAG 全景资料学习笔记：哪些能借、哪些是我们自己走出来的 | 业主转来的报告方向对，但**两处要改**： | 8 |
| `docs/research/retrieval-pipeline-design-merge.md` | 202 | 通用召回链路：8 方案评审与合并（目标链路 v1） | 合并后的骨架是：**判据先行 → 标识符精确通道（唯一硬门）→ 多字段词法主干 → 语义只作候选重排 → 名次融合 → 定位锚 → 拒答门**， | 10 |
| `docs/research/skill-knowledge-three-layer-reference.md` | 416 | Agent「技能 / 知识」三层结构 —— 四路调研参考材料 | 而每轮注入到会话里的技能清单只有约 20 条 ⇒ **另外 35 份在哪、归谁、是否过期，没有清单可查。** | 11 |
| `docs/research/solutions-for-open-problems.md` | 306 | 我们当前未解的问题：外部解法调研 | 来源三处，逐条对照过，不凭印象： | 4 |
| `docs/research/substitute-scan.md` | 273 | 替代品扫描（substitute scan）——"谁已经交付了同样的用户价值" | 我们靠渠道巡检拼出来的时效数据，**在覆盖面与权威性上很难超过 B 类**。 | 9 |
| `docs/research/vision-coverage-map.md` | 341 | 愿景对照矩阵：**我们的每一块愿景，谁已经实现了** | 1. **最小可用组装方案已经存在**： | 9 |
| `docs/research/weknora-assessment.md` | 155 | WeKnora（腾讯开源知识库）对我们的影响评估 | Postgres(ParadeDB)/Redis，可选 qdrant / milvus / weaviate / doris / neo4j / minio / searxng。 | 7 |
| `docs/research/weknora-kb-ui/01-pages-and-flows.md` | 840 | WeKnora「知识库管理」界面与流程记录 | 决策与影响评估在 [weknora-assessment.md](../weknora-assessment.md)（那里基于官方文档；本文件基于源码，两者互补）。 | 5 |
| `docs/research/weknora-kb-ui/02-components-and-visual-language.md` | 645 | WeKnora 知识库管理界面 —— 组件构成与视觉语言 | 1. 页面底：`--td-bg-color-page`（#eee / #181818）—— `theme.css:1`、深色 `:61` | 6 |
| `docs/research/weknora-ui-vs-ours.md` | 581 | 我们 vs WeKnora：知识库管理 UI 差距清单（**只诊断，不改代码**） | 逐页并排对照 → 最丑的 5 处（现象/根因/改法）→ 别乱改的地方 → 截图判不了的 → 优先级表。 | 8 |
| `docs/research/weknora-ui/00-index-and-proposal.md` | 191 | WeKnora 界面「抄 / 改着抄 / 不抄」清单（草稿 —— 等业主确认） | 逐块给出**抄 / 改着抄 / 不抄**的建议 + 理由 + 代价，交给业主点头。 | 5 |
| `docs/research/weknora-ui/01-chat-and-citations.md` | 731 | WeKnora 前端「问答 / 对话」整块精读 | 路由定义全部在 `src/router/index.ts`。与「问答」这块真正相关的只有下列几条： | 15 |
| `docs/research/weknora-ui/02-shell-and-other-pages.md` | 1,474 | WeKnora 前端精读 02 — 外壳与"知识库/问答之外"的全部界面 | WeKnora 的 SPA 是**"无顶栏、全高左侧栏 + 内容区"**的两栏壳（`views/platform/index.vue:249-269`）， | 15 |
| `docs/research/weknora-ui/03-dsh-plugin-reference.md` | 575 | dsh-weknora 精读：同宿主现成插件参考实现 | `dsh-weknora/src/index.ts` 只有三个导出有契约意义： | 12 |
| `docs/research/wikiskill-integration-assessment.md` | 371 | WikiSkill（arXiv 2608.27454）融合评估 | ⚠ **这一节本身就是"HTTP 200 ≠ 抓对了"的实例**：Jina Reader 那次返回 HTTP 200、正文长度看着正常， | 13 |
| `docs/survey/00-method.md` | 175 | 检查计划：怎么把整个项目「检一遍」并保证没有漏 | 含糊的「全面了解」不可验证。这里把「所有内容」拆成**九个可枚举的面**， | 7 |
| `docs/survey/01-inventory.md` | 83 | 全仓清单（四本账） | — | 5 |
| `docs/survey/02-code-map.md` | 210 | 代码地图（AST 级符号清单） | — | 5 |
| `docs/survey/03-cross-ref.md` | 42 | 引用关系 | `text_hits` = 该符号名在扫描面内全部 `.py` 文本里出现的次数（**含定义行本身**）。 | 3 |
| `docs/survey/04-data-shape.md` | 879 | 数据形状（表 / 列 / 索引） | 外键：`clause_revision_id` → `clause_revision.clause_revision_id` | 4 |
| `docs/survey/05-api-surface.md` | 253 | 接口面（后端 + 前端路由） | 后端 = `src/core/api/*.py` 里的 `@app.verb("path")` 装饰器，**逐条列出，不抽样**。前端 = `plugin/client/*.ts( | 5 |
| `docs/survey/06-test-surface.md` | 209 | 测试面 | 测试文件数 == tests/ 下 test_*.py + *_test.py 的实际数量。「引用了哪些源码模块」靠文件内出现的 `src.core.x.y` 字符串判定 —— * | 3 |
| `docs/survey/07-doc-surface.md` | 390 | 文档面 | 扫描 `docs/**/*.md`（含 archive）。链接用 markdown `[t](p)` 正则抽取；入链按「相对路径命中」或「文件名唯一命中」判定 —— **文件名不唯 | 4 |
| `docs/survey/08-gate-surface.md` | 111 | 门禁面 | 1. `selftest（必失败）` | 4 |
| `docs/survey/09-runtime.md` | 105 | 运行时：引擎怎么起、端口令牌在哪、数据放哪 | 门禁里那一步实测过三态： | 7 |
| `docs/survey/10-observed.md` | 246 | 观察记录（中性，不下结论） | 那 31 个里，复核时能看到至少两类**不是没被用**： | 6 |
| `docs/survey/11-module-index.md` | 1,346 | 模块职责索引 | `purpose` = 模块 docstring 的第一句（跳过标题行，按 `。`/`；`/换行切，上限 160 字）。**没有 docstring 的模块 purpose 为空* | 3 |
| `docs/survey/12-config-surface.md` | 89 | 配置面（环境变量 + 配置键） | 环境变量 = `os.environ.get/getenv/env[...]` 与 `process.env.X` 的字面量；配置键 = `_read_json_key` / `_ | 4 |
| `docs/survey/13-table-io.md` | 333 | 表读写关系 | 扫描 `src/**/*.py` 里的 SQL 字面量：写 = INSERT/REPLACE/UPDATE/DELETE 后面的表名；读 = FROM/JOIN 后面的表名。**只 | 4 |
| `docs/survey/14-test-index.md` | 3,651 | 测试索引（每个测试钉住了什么） | `tests` = 每个 `def test*` 的名字、所在类、行号，以及它的 **docstring 第一句**（很多测试没 docstring，那就空着）。**名字本身就是本 | 3 |
| `docs/survey/15-doc-index-content.md` | 602 | 文档内容索引（每份讲什么） | `summary` = 第一个 `# 标题` 之后、第一个非空且**不是** 引用/表格/列表/代码/图片 的行，上限 160 字。`h2_headings` 是全部二级标题（前  | 4 |
| `docs/survey/16-frontend.md` | 274 | 前端清单（文件 / 导出 / 说明） | `exports` / `declarations` 用**正则**抽取（没有 TS AST 工具链），**这是近似，不是完整符号表**。`header_note` 取文件开头 4 | 4 |
| `docs/survey/COVERAGE.md` | 51 | 覆盖对账（九个面） | 重跑四个生成器（合计约 30 秒），**不要手改 md**： | 4 |
| `docs/survey/README.md` | 65 | 项目现状地图 | 查表就知道东西在哪、长什么样、谁引用谁、验过没有。 | 6 |
| `docs/tool-catalog.md` | 59 | ks-dsh-plugin 工具目录（生成物——**手改必红**，改说明书后跑 `node plug | Forensic (取证) compliance Q&A against the local KnowledgeStation engine; returns three-part | 6 |
| `docs/uniformity/00-review-of-surveys.md` | 141 | 摸底报告的主对话复核记录 | 调查员原话（`04-tests-tools-gates.md` §6.4 口子 C）： | 4 |
| `docs/uniformity/01-core.md` | 1,064 | src/core 事实地图 | 调查日期：2026-10-20。范围：`src/core/` 全部 155 个 `.py` 文件（45,439 行 / 2,346 KB）。 | 7 |
| `docs/uniformity/02-plugin.md` | 586 | plugin/ 事实地图 | 调查对象：`plugin/`（DSH 插件，宿主侧 + 浏览器侧 + 验证脚本）。本文件只陈述读过源码后能指回具体文字的事实。 | 9 |
| `docs/uniformity/03-docs-specs-scripts.md` | 641 | docs / specs / scripts 事实地图 | 1. **顶层不是 30 份，是 29 份。** | 7 |
| `docs/uniformity/04-tests-tools-gates.md` | 621 | tests / tools / 门禁 事实地图 | `tests/fixtures/` 只有 7 个文件：`民法典节选.txt`、`discover_web.json`、`fake.docx`、`fake.pdf`、 | 8 |
| `docs/uniformity/05-verifier-findings.md` | 101 | verifier 抽查记录（2026-10-23） | 「核心量化骨架是硬的，错的两条属于统计口径没写清，不是编造。」 | 4 |
| `docs/uniformity/06-frontend.md` | 523 | plugin/client 事实地图 | 调查对象：`D:\Agent-Studio\Deepseek-Harness\DSH-Data\workspace\zcode\plugin\client\`。 | 9 |
| `docs/uniformity/07-other-dirs.md` | 432 | 其他目录事实地图 | 命令与数字： | 6 |
| `docs/uniformity/08-why-contracts-rot.md` | 263 | 为什么"约定了契约"还是会变乱 | 基线缺失 = 硬失败）。 | 8 |
| `docs/uniformity/09-big-files.md` | 609 | src/core 三个大文件事实地图 | 任务书给的 2,254 / 1,844 / 845 是**非空行**，不是文件行数。实测（`[IO.File]::ReadAllText` 按 `\n` 切分）： | 6 |
| `docs/uniformity/10-api-server.md` | 452 | api/server.py 事实地图 | `docs/uniformity/01-core.md` 与 `docs/DEVELOPMENT-HISTORY.md` 里出现过的「127 个端点」是**另一次口径** | 7 |
| `docs/uniformity/README.md` | 889 | KnowledgeStation 摸底：证据与过程 | 用户问一句合规问题（例：「甲醇作业要不要做职业健康检查」），它做三件事： | 13 |
| `docs/uniformity/START-HERE.md` | 249 | KnowledgeStation 上手（新人第一份读这个） | `var/data/`（72.32 GB）、`var/models/`（6.87 GB）、`.venv/`（5.06 GB）**都被 `.gitignore` 盖住**。 | 2 |
| `docs/uniformity/report.md` | 241 | 统一化报告（repo-uniformity-ratchet 留档） | ③④ 是「可归零」指标，**已是 0，无存量**。 | 8 |
| `docs/verify-briefs/VERIFY-REPORT-e4b-round2.md` | 308 | 独立复核报告：E4 第二轮验证（批次 `e4b-round2`） | 尾态各产物 SHA256 与冻结备份**逐一致**（见 §3、§4）。 | 12 |
| `docs/verify-briefs/VERIFY-REPORT-e4c-1024.md` | 137 | 独立复核报告 · E4c「同模型升维 512→1024」 | ⇒ 四条决策分支全部可被触发，判据**不是恒判"放弃"**，有牙。 | 5 |
| `docs/verify-briefs/VERIFY-REPORT-e9-col-prior.md` | 93 | 独立复核报告 · 批次 `e9-col-prior`（P2 诊断·第 1 刀） | 冻结事实自洽：tag→`db5c074`、`rev-list --count db5c074^..tag` = **1**、7 文件清单一致。 | 7 |
| `docs/verify-briefs/VERIFY-REPORT-exp13-query-rewrite.md` | 201 | 独立复核报告 · exp-13 查询侧改写（A/B/C/D） | 在提取树、用主仓 venv 解释器（CWD=提取树）跑 `eval/recall-funnel/exp-13-query-rewrite/run.py`，**自跑第 1 次**（` | 12 |
| `docs/verify-briefs/VERIFY-REPORT-exp14-fused-rewrite.md` | 230 | 独立复核报告 · exp-14-fused-rewrite | 改动面核实（`git show --stat da27368`）：**单提交 14 文件**，全部落在 | 10 |
| `docs/verify-briefs/VERIFY-REPORT-exp15-pool-depth-fusion.md` | 135 | VERIFY-REPORT — `exp-15-pool-depth-fusion` 独立复核（第  | 主终点 `fused@20`（headline 120）的 **7 臂全部逐格复现**；oracle 三个数、`池里有 gold` 两组数、`42 条里 ≤20=14 条`、仪器对 | 13 |
| `docs/verify-briefs/VERIFY-REPORT-exp17-prod-plan.md` | 263 | 独立复核报告 · exp-17-embedding-production-plan（必验类别） | 第二次运行 **5 项全 PASS**，`result.json` 与作者提交版**逐字段相同**： | 14 |
| `docs/verify-briefs/VERIFY-REPORT-govqa-conformance.md` | 660 | 独立复核报告 —— `verify-freeze-govqa-conformance` | 复核对象：冻结 tag `verify-freeze-govqa-conformance`（**annotated tag** `05d276a2a1affdf96d5b7ad5b | 11 |
| `docs/verify-briefs/VERIFY-REPORT-govqa-data-forensics.md` | 915 | 独立数据质量取证报告 —— `tools/gov-qa/` 政务问答语料 | 实测输出（原样）： | 5 |
| `docs/verify-briefs/VERIFY-REPORT-p010-long-tail.md` | 202 | 独立复核报告 · 批次 `p010-long-tail` | 提取树：`git worktree add D:/AI/verify-trees/p010 98aeb52` | 6 |
| `docs/verify-briefs/VERIFY-REPORT-p32-classical-seg.md` | 258 | 独立复核报告：P3.2 古籍/文言切分评估（批次 `p32-classical-seg`） | 本批**实际改动面**（`git diff --name-only 111e270^..<tag>`）： | 9 |
| `docs/verify-briefs/VERIFY-REPORT-ratchet-1.md` | 94 | 独立复核报告 —— ratchet-1 批次（复核员 general-purpose-1） | 复核者：**独立重跑取证，未修改主仓 `D:/AI/work space/zcode`**。所有变异件/探针建在系统临时目录 `D:/tmp`。 | 6 |
| `docs/verify-briefs/VERIFY-REPORT-ratchet-2.md` | 137 | 独立复核报告 —— ratchet-2 批次（复核员 general-purpose-1） | 补充核实： | 6 |
| `docs/verify-briefs/VERIFY-REPORT-rerank-fix.md` | 252 | 独立复核报告 · 批次 `rerank-fix`（施工总纲 P0·0.7 修复） | （真实模型确认：`is_available()=True`、`offline_reason=None`，分数是模型真实输出。） | 11 |
| `docs/verify-briefs/VERIFY-REPORT-spec003-vecscope.md` | 231 | 独立复核报告 · spec 003「向量通道范围下推修复」 | 复跑 `probes/probe-mechanism.py`（实施者脚本）： | 10 |
| `docs/verify-briefs/VERIFY-REPORT-spec004-operationalization.md` | 619 | 独立复核报告 —— `tools/gov-qa/` spec 004 可运维化层 | 15/16 个算法锚点变异即红；但 **CLI 退出码、契约字段、水位实际被读取这三大块，改坏了没有一条测试会红**。 | 18 |
| `docs/verify-briefs/VERIFY-REPORT-spec007-ui-polish.md` | 140 | VERIFY-REPORT · spec 007（UI 精修）第二轮独立复核 | 同时报出 **P1 × 1**（新发现的相邻缺陷：配置态 Key 框 placeholder 仍被截 3px——R3 修复让它从"恒不可见"变"可见"）与 **P2 × 6**。无 | 11 |
| `docs/verify-briefs/VERIFY-REPORT-spec008-icon-system.md` | 122 | VERIFY-REPORT · spec 008（图标体系）—— **自查**（非独立第三方） | 并在自查中**发现并修掉一个真漏洞**（见 §3），该修复**不在冻结点内**，已单独提交 `6f0fb9fd`。 | 10 |
| `docs/verify-briefs/VERIFY-REPORT-spec009-turn-evidence-ui.md` | 125 | VERIFY-REPORT · spec 009（「本轮依据」三处改动）—— **自查**（非独立第 | 变异全部还原后复跑 **pytest=0 / smoke=0**。 | 8 |
| `docs/verify-briefs/VERIFY-REPORT-spec010-turn-tab-fixes.md` | 164 | VERIFY-REPORT · spec 010（「本轮」页三处修正）—— **自查**（非独立第三 | 我用了 `SELECT bbox_json FROM source_span WHERE … LIMIT 200000` —— | 10 |
| `docs/verify-briefs/VERIFY-REPORT-t016-t017-p1fix.md` | 199 | 独立复核报告 — T016/T017 P1 修复批次（`doc_stds` 未定义） | ⇒ 含库内标准号 ⇒ `has_standard_no=True` **且** `has_standard_no_verified=True`；含库外标准号 ⇒ `has_stan | 8 |
| `docs/wiki/architecture.md` | 248 | KnowledgeStation：项目目标与现状 | 三条总判据（取自项目施工总纲 `docs/RETRIEVAL-LONG-RANGE-PLAN.md`）： | 6 |
| `docs/wiki/components/README.md` | 53 | 组件契约索引 | 1. **事实来自读代码与既有文档**，不许凭印象。不确定的标「未核」。 | 3 |
| `docs/wiki/components/api.md` | 88 | api（HTTP 端点） | 插件、外部系统、`ks_*` 工具最终都打到这里。 | 8 |
| `docs/wiki/components/compliance.md` | 67 | compliance（合规差距分析） | 判定是**可解释的规则式，不是 LLM**：命中率 ≥ 0.5 或绝对命中 ≥ 3 → green（已覆盖）；命中 ≥ 1 → yellow（不完善）；命中 0 → red（缺失） | 8 |
| `docs/wiki/components/domain.md` | 67 | domain（域模型契约） | 它是**同一进程内的类型依据**：子系统之间传的对象长什么样，以这里为准。 | 8 |
| `docs/wiki/components/exports.md` | 70 | exports（产出物组装与导出） | 接手的是**库内已成形的数据**（条款、材料、效力状态），交付的是 Markdown / Excel / 供用户编辑的临时 docx。 | 8 |
| `docs/wiki/components/ingestion.md` | 62 | ingestion（解析与入库） | 最大的是 `pipeline.py`；写 `doc_meta` / `clause_revision` / `parse_out` | 6 |
| `docs/wiki/components/knowledge.md` | 51 | knowledge（法规知识本体与分类） | 含 `law_source/` 子目录（法规官方源抓取） | 6 |
| `docs/wiki/components/law-source.md` | 60 | law-source（官方法规来源管线） | 模块：`http.py`（共享 HTTP 层）、`flk_client.py` / `govcn_client.py`（两个来源客户端）、`catalog.py` 22.4 KB（ | 7 |
| `docs/wiki/components/llm.md` | 76 | llm（模型调用与取证答案） | 接手的是**已排好序的候选条款**（`retrieval` 交付），交付的是**答案文本 + 核验结果**。 | 8 |
| `docs/wiki/components/materials.md` | 51 | materials（材料平面） | — | 6 |
| `docs/wiki/components/plugin-tools.md` | 62 | plugin-tools（插件对 agent 暴露的工具） | 插件把引擎的 HTTP 能力包成**模型可见的工具**。实测注册 **6 个**（`ctx.tools.register` × 6）： | 7 |
| `docs/wiki/components/quality.md` | 67 | quality（质量判定） | 接手的是**尚未落库或刚解析出来的结果**（入库预览 Dry-Run 与已入库体检共用同一实现），交付的是可解释的标签、度量与三态裁决。 | 8 |
| `docs/wiki/components/query.md` | 65 | query（查询理解） | 槽位 Schema 是两族：**工程参数**（建筑类型 / 火灾危险性 / 耐火等级 / 高度）+ **法律要素**（主体 / 客体 / 行为 / 同意状态）。追问严格基于 Sch | 8 |
| `docs/wiki/components/retrieval.md` | 71 | retrieval（检索） | 把结果讲成答案（`llm` + `api`）。 | 8 |
| `docs/wiki/components/settings.md` | 68 | settings（设置与凭据） | ⚠ 本子系统内有**零测试模块**：`routes_settings`（全仓没有任何一条用例是为它写的）。 | 8 |
| `docs/wiki/components/storage.md` | 115 | storage（存取与 schema） | （**44 张表对象**：`schema.sql` 里 `CREATE TABLE` 44 条，其中 3 张虚拟表 `clause_fts` / `clause_vec` / `m | 9 |
| `docs/wiki/components/update-channels.md` | 54 | update-channels（渠道适配器） | 配套：`routing.py`（按标准号特征选链）、`ledger_chain.py` 20.9 KB（台账驱动的降级链，**只算不改**）、`question_router.py | 7 |
| `docs/wiki/components/update.md` | 59 | update（渠道巡检与变更） | ⚠ 本子系统内有**零测试模块**：`proxy_rotate`、`channels/mohurd`（全仓没有任何一条用例是为它写的）。 | 6 |
| `docs/wiki/components/verification.md` | 63 | verification（核验与纠错守卫） | 两条互相独立的守卫： | 8 |
| `docs/wiki/components/vision.md` | 67 | vision（本地视觉反查） | 云通道已从这条链路退役（2026-09-01）：截图反查是用户主动操作，本模块**全程本地执行、零外发**。 | 8 |

## 四、二级小节最多的 15 份（结构最复杂的文档）

### `docs/archive/history/rounds-10.1-10.203.md`（136 个二级小节）

- §10.71 产出物那两条端点改 `def` —— 并把"审计调用方"从口头纪律做成工具（复核 b12 的 MEDIUM
- §10.72 收口复核 b12 的 LOW/INFO —— 一条假绿（C2）、一条真检测（anchorNote）、一处穷
- §10.73 造一把"引擎被堵多久"的尺，并用它做完第一批（`ingest/preview` 六条）——顺带量出一条审计
- §10.74 让健康检查回到"廉价"：`/health` 6.79s → 0.0064s；失败的加载不再无限重试 —— 
- §10.75 PDF 渲染/读盘族去阻塞化（5 条）+ 把"候选清单不是待办清单"写成结论
- §10.76 落盘/导出族去阻塞化（7 条）——并如实记下"这一族**没测出大收益**"
- §10.77 `dry_run` 同文件并发加锁 + 渲染端点补 HTTP 契约（两件小事，一次收口）
- §10.78 给审计补上"库内部重活"这一族（并修掉它的假阳性）——顺带重新盘点
- §10.79 T2 批次：25 条"只 await 一下 body 就在做重活"的端点改 `def` —— 并加了一条*
- §10.80 SSE 那条：把"没有 await 的异步生成器"修掉，并加第二条通则闸门
- §10.81 处理复核 b13 的发现：线程池容量有界（MEDIUM-1）+ 三处措辞更正 + 流程纪律加一条
- §10.82 重活专用闸门：让长活排队时**不占线程**，给文件流留出位子
- §10.83 `bulk-db` 一族：**先量了争用代价，再全部转 `def`** —— 并把通则收成"单一条规则"
- §10.84 真 uvicorn 下的引擎验证：进程内量具覆盖不到的那一层（4/4 PASS）
- §10.85 处理复核 b14 的发现：闸门对流式不生效（MEDIUM-1）、判据能被注释骗（MEDIUM-2）+ 4 
- §10.86 处理复核 b15：把判据从"看标记"换成"看有没有 await" —— 一次性消掉"零 await 占着事
- §10.87 处理复核 b16：**"async 必须显式申报"**（判据静态上判不准就改要申报）＋ 并发 DDL 竞态
- §10.88 处理复核 b17：线程池收窄的"按循环"错配（MEDIUM-1）、名单第二关的误红（MEDIUM-2/RE
- §10.89 处理复核 b18：**"误红"的那条其实是"正确但硌手"**（拿框架事实收口），+ 口径更正与死代码
- §10.90 处理复核 b19：核心前提被独立证实（G1），4 条 INFO 全收口
- §10.91 处理复核 b20：我自己写错的一条"坑"（N1）＋ 深度上限只钉住窗口（N2）＋ `.pyc` 变异陷阱（
- §10.92 产品侧：研究报告的第三种形态 Word（`.docx`）——同一份内容块，且失败不留半份产物
- §10.93 收口两个遗留结构洞：`/laws/*` 回到 `def`（`asyncio.to_thread` 全库清零
- §10.94 量具接名单（第二层）——**尺子抓出并修掉**了 `/chat/completions` 冷启动冻引擎 6
- §10.96 自动成文落地（D-5a）：结论**草稿**端点——零新提示词，且**更正了我上一节的形态取舍**

### `docs/ENCYCLOPEDIA.md`（82 个二级小节）

- 目录
- 1.1 一句话定位
- 1.2 目标用户与典型场景
- 1.3 痛点
- 1.4 产品形态（批 8 定稿）
- 1.5 产品承诺（验收红线 v2）
- 2.1 触发与模式
- 2.2 25 条决策台账（2026-09-05 逐项问答定稿，全部 ✅ 采纳）
- 2.3 明确不做（Non-goal）
- 3.1 六通道混合检索（契约冻结）
- 3.2 Rerank 标准阶段
- 3.3 通道消融结论（2026-08-23 实测，结论已固化）
- 3.4 Golden Set 门禁（红线 6）
- 4.1 调用链与凭据（权威表述——批 2/4 定稿）
- 4.2 SYSTEM_PROMPT 规则 1~9（用户实测调优产物，**只能增强不能回退**）
- 4.3 追问机制演进史（v1 → v2）
- 4.4 查询理解层（understanding.py）
- 4.5 Few-shot 注入（R17 轻量版）
- 5.1 三通道核验（typed_verifier.py）
- 5.2 核验报告
- 5.3 核验哲学 + 两轮误报修复判据（2026-09-06）
- 6.1 合规审查（compliance/engine.py）
- 6.2 义务清单与检查表（obligation.py）
- 6.3 制度差距分析（gap_analysis.py）
- 6.4 条款释义（interpretation.py）

### `docs/archive/workbuddy-memory/memory/2026-10-09.md`（57 个二级小节）

- 接手通读：摸清项目现状与开发目标（只读，未改任何文件）
- 追加：定位「主体项目的任务进度计划书」（业主指定：公告组件 / gov-qa 两条线不归我管）
- 追加 2：通读 spec 体系与「施工规范」
- 追加 3：搭「自动续接链」（业主 2026-10-09 指示，参考 D:\AI\SW\output\AUTO_CHAIN
- 第 1 轮（自动续接链）：做「甲」—— 给 run-gates.ps1 棘轮接线补单测
- 追加 4：显卡占用问题（业主问：本机有本地大模型占满显卡，施工要不要显卡）
- 追加 5：★ 更正 —— 显卡约束**已按业主指示撤回**（追加 4 的处置作废）
- 追加 6：补齐「开发规范/契约」阅读，并把"动手前必读契约源"写进自动化
- 追加 7：业主追加要求 —— 契约阅读提成**每轮开工的固定一步**
- 追加 8：业主追问"还有什么是必须读的" —— 补齐「规矩 / 归属层」，开工第二步扩成四块
- 追加 9：★ 链停摆（业主发现）—— 已重新上弦 + 加看门狗
- 追加 10：★ 更正 —— 看门狗是坏设计，已删；主任务改为「每小时循环」
- 追加 11：★ 再更正 —— 恢复参考方法（自链），我此前的判断证据不足
- 追加 12：★ 找到真根因 —— **自链余量 +1 分钟太紧**（调度器是好的）
- 追加 13：余量 +3 分钟**也没接上** → 业主定 **+15 分钟**
- 追加 14：常驻看门狗（业主指示）+ **发现数据库写入不生效**
- 第 2 轮（自动续接链）：收口「甲」的独立复核 + 「乙」P0.4b 诊断拍板
- 第 3 轮（自动续接链）：补「甲」的锚点存在性守卫（fail-open → fail-closed）
- 第 4 轮（自动续接链）：P2 诊断·第 1 刀 —— 候选列当"筛子"没有收益 ⇒ 决定不改
- 追加 15：P3.2 复核**已收口**（但交接单/日志当时没回写）—— 第 6 轮开工时才发现
- 第 6 轮（自动续接链）：**E4 第二轮验证 —— 提问侧成本不构成拦路虎 + 查询侧指令前缀 +15.84pt**
- 复核收口 —— `e4b-round2`（2026-10-09 04:19–04:34，第 6 轮的尾巴）
- gov-qa 政务问答采集 —— 自动化轮（早场 06:41–07:2x）
- KS 自动链 · 调度方式定稿（09:50，业主 09:49 发现停摆）
- KS 自动链 · 第 7 轮（09:56–11:30）：E4 第三刀「同模型升维 512→1024」—— 判决放弃升维

### `docs/KB-FOLDER-PLAN.md`（34 个二级小节）

- 一、定案（业主原话要点）
- 二、我自定的三条（业主未反对即生效）
- 三、数据形状（决定一切，先定死）
- 四、要做的能力（逐项，界面与接口一一对应）
- 五、分步（每步：小提交 + 真机验证 + 独立复核）
- 六、必须守住的既有约束
- 七、风险与回退
- 八、待查（第 1 步里一并查清）
- 九、第 1 步实测结果（2026-09-21，提交 `43d1fa5`/`44a6cfb`/`7991e8c`/`2d6
- 十、第 1 步顺带发现的缺陷（登记，待修，不在本步修）
- 十一、归位已写入真库 + 独立复核结论（2026-09-21，冻结 `verify-freeze-kb-filed` =
- 十二、第 2 步实测结果（2026-09-21，提交 `603b333` / `ecbb09f` / `d61a9be`
- 十二·补、复核打回后的四条修准（2026-09-21，独立复核报告 `var/tmp/verify-kb-api-rep
- 十三、父代理对"379 篇给不出建议"的裁定 + 两条登记（2026-09-21）
- 十四、第 2 步收尾：两处就地更正 + 一条我判复核误读（2026-09-21，提交 `22a0e03`）
- 十五、第 3 步实测结果：界面骨架接真库（2026-09-21）
- 十六、父代理对第 3 步的裁定 + 我补的一条判据（2026-09-21，提交 `4591e8c`）
- 十六·补、复核 `verify-freeze-kb-ui3` 的结论 + 就地修准（2026-09-21，提交 `459
- 十六·补2、第 2 轮复核（同一病根收口）与它挖出的一条**后端大缺口**（2026-09-21）
- 十七、那两篇被隐藏的文档：实测答案 + 我此前措辞的更正（2026-09-21）
- 十八、本机环境登记（会再咬人一次）
- 十九、第 4 步实测结果：「待分类」界面 + 后端「重来一次」（2026-09-21，实施子代理交付）
- 十九·补、第 4 步的独立复核结论 + 父代理的裁定（2026-09-21，冻结 `verify-freeze-kb-s
- 十九·补·实施代理对三条小修的处置（2026-09-21，提交 `ea31479`）
- 十九·补2、三条小修的第 2 轮复核（同一病根收口，2026-09-21，冻结 `verify-freeze-kb-st

### `docs/research/channels/oss-decomposition.md`（22 个二级小节）

- 0. 真伪判定总表
- 1. GBMCP
- 2. OpenSTD_Spider
- 3. gb-downloader
- 4. gb688_downloader
- 5. gbqw
- 6. changedetection.io
- 7. urlwatch
- 8. National Standard Monitor Skill
- 9. Law-Crawler-RPA-RAG-MCP
- 10. legal-database
- 11. china-law-search
- 12. policy-monitor
- 13. GovPing
- 14. RegRadar
- 15. regwatch-eu
- 16. @sanmis/crawler
- 17. at-ris-mcp
- 18. standards-version-check
- 19. 能直接抄的 5 个取数技巧
- 20. 机器可读附录
- 21. 方法学备忘（可复现）

### `docs/research/ks-fixes/02-modality-residual.md`（22 个二级小节）

- 一句话结论
- 五条要点
- 1.1 强度表原文
- 1.2 复现：那两题的窗口里到底有什么
- 1.3 主因定位：窗口方向错了（标记后置 vs 向后取窗）
- 1.4 放大器一：同一 `clause_number` 对应多条 evidence
- 1.5 放大器二：模型未引用的证据，窗口空 ⇒ 回退整篇
- 1.6 取词规则：不是「第一个」，是「词长降序」
- 1.7 另外两处小串（都在探针里复现了）
- 1.8 源侧问题：一条只存一个 `modality`
- 1.9 现有 3 条判据为什么全绿却没抓住
- 2.1 中文标准的能愿动词分级：应/不应**同档**，只有肯定否定之别
- 2.2 道义逻辑：禁止不是「更强的义务」，是「对否定的义务」
- 2.3 LegalRuleML：道义算子是**带主体**的定向算子
- 2.4 多模态同句：业界已从「整段分类」转向「按 span 抽取」
- 2.5 作用域绑定：用「终止词」而不是固定字数窗口
- 2.6 RFC 2119：也是成对定档，不是一条标量轴
- 3.1 方案 A（止血，只动 `typed_verifier.py`，可整体 revert）
- 3.2 方案 B（改契约，动 `models.py`；不建议现在做）
- 3.3 方案 C（改源侧，动 `classifier.py` + 表结构；代价最大）
- 3.4 现有 3 条判据够不够：不够，至少补 6 条
- 3.5 需要业主拍板的一条

### `docs/archive/review-briefs/b3a-engine-report.md`（21 个二级小节）

- 报告首：git 记录（一）
- 结论总表
- ① "补前一定有备份"是不是真的 —— **是**（探针1、探针3）
- ② 回退是不是真能退干净 —— **两处逐字能退；第三处（`updated_at`）退不回去**（**MED / F2*
- ③ HIGH-1 是否真的堵死 —— **是**（活路径全收口）；残留一个非原子窗口（LOW / F7）
- ④ `stop_reason` 说实话吗 —— **七值单值、失败篇不被算成补完**；但 **`selected × t
- ⑤ `missing_split` 五桶 —— **恒等式真**（临时库 + 真库都核）
- ⑥ `all=true` 那条路 —— **通过**
- ⑦ MED-5（锁）—— **有用例钉住，变异必红**（父代理的担心不成立）
- ⑧ 不加第 6 个 `outcome` 值的理由 —— **成立**（真库只读核，原文见 §A.1）
- ⑨ 新用例有没有牙 —— **有**（3 个变异各自红）；无恒真断言，但有一条把缺陷冻成规格
- ⑩ 它自己声明的"没做" —— **形式上都确实没做**
- F1（MED）勾选篇数 > limit 时 `stop_reason` 说"勾选的跑完了"
- F2（MED）`doc_meta.updated_at` 被改、没进回退记录、回退不恢复
- F3（LOW）`db_path` 只喂给计划与备份，干活线程写到默认库
- F4（LOW）`_as_list` 把"非空且非 JSON 数组"归零 ⇒ 覆盖整列
- F5（MED，**不在本 2 笔 diff 内**）第三处 CCS 码 `doc_meta.ccs_code/ccs_n
- 报告尾：git 记录（二）
- A.1 `doc_ccs_state` 的建表 SQL（CHECK 只有 5 个值）
- A.2 真库体检数字
- A.3 只读证明（探针前后 sha256 与长度）

### `docs/research/HINDSIGHT-DOCS-READING-2026-09-28.md`（18 个二级小节）

- §0 取件过程中踩到的坑（留给新对话）
- §1 已通读的 6 篇（逐条给行号，逐字引用）
- §2 我们本机的现状（上一轮实测，与 §1 对照）
- §3 已经能下的三条结论
- §4 我**没有**核的（不许当已核）
- §5 顺带核出的一件事（那份二手材料的对错）
- §6 未读的 35 篇（新对话从这里继续）
- §7 本任务要回答的业主问题（别跑偏）
- §8 逐篇一行表（全 42 篇）
- §9 本机实测对照（2026-09-28，这是本轮最有价值的产出）
- §10 回答业主：他的结构真把"知识库 + skill"统一起来了吗？我们没有，真的没价值吗
- §11 本轮核过、但仍然**没有**核的（不许当已核）
- §12 更正 §5：那份二手材料，**我第一轮判错了两处**（2026-09-28 第三轮）
- §13 20 篇实测：`document-transfer` 导入路能不能走（2026-09-29）
- §14 深读轮：33 篇补读（2026-09-29）
- §14 消融 + 文字 A/B：重排就是全部瓶颈，而它买的是"第一名"（2026-09-29）
- §15 候选池扫描：延迟能砍，但质量曲线**量不准**（2026-09-29）
- §16 🔴 事故留痕：手工重启 Hindsight 差点指向空库（2026-09-29）

### `docs/verify-briefs/VERIFY-REPORT-spec004-operationalization.md`（18 个二级小节）

- 变异总表（16 个锚点 + 26 个追加探针）
- 【高】1. 水位只写不读 —— 增量轮询对 `page`/`since` 型通道是**摆设**
- 【高】2. 覆盖闸门「判据有牙」是假的：`CITY_NONE=0` 与 182 个零记录市同时成立
- 【高】3. `health.py` 的 4 项判据里，**没有任何一项**被测试钉住
- 【中】4. 24 个通道（含 35,260 条记录）**完全落在销号表之外**
- 【中】5. `--scope law_std` 把「无此字段」误判成「硬缺口」（退出码 1）
- 【中】6. `common.py::human()` 的兜底分支自身会抛 `UnicodeEncodeError`
- 【中】7. spec-004 的**人读输出**确实复现了已知的 GBK 崩溃类；机器可读路径是干净的
- 【中】8. `poll.py --quiet` 的逐通道行绕过 `ascii_kv()`，且含一行死代码
- 【中】9. 契约与实现不符：3 个已写进契约的 CLI 开关不存在，机器可读格式也不符
- 【中】10. 退出码契约（`poll.py` 0/1/2/3、`coverage-report.py` 1）**零测试覆
- 【中】11. `health.py` 的「重复 id」只在**单文件内**检测，跨文件重复漏报
- 【中】12. `--missing-cities` 报 `CITY_TOTAL=334`，与契约/文档的 **333**
- 【低】13. `test_label_accuracy_refuses_without_human_check` 的断言
- 【低】14. `health.py` 把 0 字节数据文件当成「已采到数据」
- 【低】15. 锁文件无陈旧检测：进程被 kill 后锁永久占用，`poll.py` 恒返 3
- 【低】16. `tasks.md` 全部 57 个任务**没有一个**勾选，却与代码/文档口径矛盾
- 【低】17. 文档里三处「已验/已覆盖」的宣称超出证据

### `docs/archive/workbuddy-memory/memory/automations/1b206fd3-357f-47a1-bf5b-e17ec5c419a3/memory.md`（16 个二级小节）

- 第 1 轮 — 2026-10-09 00:34
- 第 2 轮 — 2026-10-09 00:44
- 第 3 轮 — 2026-10-09 01:05
- 第 4 轮 — 2026-10-09 01:28
- 第 4 轮续 — 2026-10-09 01:45（独立复核收口）
- 第 5 轮 — 2026-10-09 02:05
- 第 6 轮 — 2026-10-09 03:45
- 复核收口（`e4b-round2`）—— 2026-10-09 04:19–04:34
- 第 7 轮 — 2026-10-09 09:56
- 复核收口（`e4c-1024`）—— 2026-10-09 11:16–11:40
- 第 11 轮 — 2026-10-09 14:02
- 第 12 轮 — 2026-10-09 14:40
- 第 13 轮 — 2026-10-09 15:34
- 第 14 轮（2026-10-09 16:05–16:15）—— 复核回复轮：收下 exp-14 独立复核并逐条处置
- 第 15 轮（2026-10-09 16:20–16:40）—— P2 后半段·第三刀：池深 × 融合方式（`exp-1
- 第 15 轮复核回复轮（2026-10-09 16:44–16:57）—— 收 exp-15 复核，2 条 P1 + 1

### `docs/research/weknora-ui/01-chat-and-citations.md`（15 个二级小节）

- 0. 页面 / 路由清单表
- 1. 会话与导航
- 2. 提问区
- 3. 回答渲染
- 4. 引用与来源面板
- 5. 文档预览
- 6. 产物（artifacts）
- 7. 消息级操作
- 8. 状态与反馈（文案原文）
- 9. 接口清单（方法 + 路径 + 用途，逐条从 api 层核出）
- 10. 关键状态枚举（从代码常量/mapping 里找）
- 11. 组件清单（名称 / 文件:行 / 职责 / 关键 props 与事件）
- 12. 值得抄的（对我们有用的）
- 13. 建议不抄 / 抄不动
- 14. 我没查到 / 不确定

### `docs/research/weknora-ui/02-shell-and-other-pages.md`（15 个二级小节）

- 0. 一张图先看结论
- 1. 全站页面清单表
- 2. 一屏 ASCII 骨架
- 3. §1 全站外壳与导航
- 4. §2 登录与鉴权
- 5. §3 设置
- 6. §4 组织与权限
- 7. §5 Agent 与集成
- 8. §6 平台 / 系统 / 开发者页
- 9. §7 全局通用件
- 10. §8 国际化
- 11. §9 哪些是 OSS 核心、哪些是企业版/平台版
- 12. 值得我们抄的（10 条，每条一句理由）
- 13. 我们不抄 / 抄不动（9 条，每条一句理由）
- 14. 我没查到 / 不确定

### `docs/verify-briefs/VERIFY-REPORT-exp17-prod-plan.md`（14 个二级小节）

- 总判定
- A. 改动面与冻结
- B. 五项验证读数独立复跑
- C. ★ T4 的仪器对照站不站得住（本轮最需独立判断的一条）
- D. 判据有牙（**我自写的 10 处变异**，非重复作者）
- E. 文本公式与生产逐字一致
- F. §一「触点清单」是否完整
- G. 成本账算术逐项复算
- H. 超证据 / 全称句自查
- I. 是否真的没碰生产
- 明确「未验证」清单
- 非阻塞发现（P2）汇总
- 必改项（P1）
- 附：我的变异与实验产物（保留在 `D:/AI/verify-trees/`）

### `docs/HANDOVER-2026-10-09.md`（13 个二级小节）

- ⚠ 接手前先看这三条（顺序别乱）
- 一、一句话
- 二、项目是什么（说人话）
- 三、只有三条是别人没有的（2026-09-25 复核过）
- 四、真库与环境（**2026-10-09 实测**，引用前先复核）
- 五、权威文档地图（谁是真源，别混用）
- 六、现在在哪（进度一页 · 以总纲为准，下表是 2026-10-09 快照）
- 七、下一步该干什么（按依赖，先做前面的）
- 八、业主拍过板、**不许重开**的（要点；全表见 `docs/NOT-DOING.md`）
- 九、自动链（**重要：它会和你并行改同一批文件**）
- 十、硬约束（违反即失败）
- 十一、踩过的坑（**别再踩**）
- 十二、接手第一动作（可直接执行）

### `docs/MATERIALS-PLANE-PLAN.md`（13 个二级小节）

- 0. 业主已裁定的事项（本方案的前提，不是提议）
- 1. 定位变更（J1）与需要同步的文档
- 2. 外发政策变更（J7）—— 本次唯一"放松"的红线
- 3. 两轴权威模型（核心设计，J2 + J3 的直接推论）
- 4. 两条入库通道（J5）
- 5. 数据模型（材料平面）—— 法条链零改动
- 6. 流程与硬门
- 7. 可见性硬需求（从审计里学到的教训）
- 8. 交付物（**报告，Markdown**）
- 9. 分期与验收（每期独立可回滚）
- 10. 施工纪律（业主 2026-09-17 定）
- 11. 诚实边界与明确未做
- 12. 施工进度（每步一提交一快照，`docs/DEVELOPMENT-HISTORY.md` 有完整记录）
