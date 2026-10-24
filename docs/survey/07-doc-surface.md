# 文档面

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

扫描 `docs/**/*.md`（含 archive）。链接用 markdown `[t](p)` 正则抽取；入链按「相对路径命中」或「文件名唯一命中」判定 —— **文件名不唯一时可能记到多个目标，这是近似，不是精确图**。

## 二、总账

| 项 | 数 |
|---|---:|
| `docs/` 下 `.md` | **244** |
| 其中受版本控制 | 227 |
| 链接总数 | 569 |
| **没有任何入链（孤儿）** | **113** |

## 三、孤儿文档（没有任何别的文档链到它）

> 这是**计数**，不是判断。孤儿不等于没用（`INDEX.md` 就是被脚本读的）。

- `docs/ANNOUNCE-MODULE-STATUS-2026-10-08.md`
- `docs/BROKEN-LINKS.md`
- `docs/CODE-REVIEW-CHECKLIST.md`
- `docs/ENCYCLOPEDIA.md`
- `docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md`
- `docs/GOVQA-UNWIRED-CHANNELS.md`
- `docs/HANDOVER-2026-10-09.md`
- `docs/INDEX.md`
- `docs/INTRODUCTION.md`
- `docs/PLAN-REAL-QUESTION-RULER.md`
- `docs/TEST-FLAKES.md`
- `docs/archive/handovers/HANDOVER-2026-09-23.md`
- `docs/archive/handovers/HANDOVER-2026-10-06.md`
- `docs/archive/impl-reports/B3A-REPORT.md`
- `docs/archive/impl-reports/B3B-REPORT.md`
- `docs/archive/old-plans/AUTO-DRAFT-PLAN.md`
- `docs/archive/old-plans/CHANNEL-R6C-DESIGN.md`
- `docs/archive/research-process/CHANNEL-PROBE-REPORT.md`
- `docs/archive/research-process/GOVQA-DIAGNOSIS-2026-10-10.md`
- `docs/archive/research-process/PROJECT-CONSOLIDATION-2026-10-05.md`
- `docs/archive/research-process/REALTIME-VALIDITY-VERIFY-RESEARCH.md`
- `docs/archive/research-process/STD-STATUS-CHANNELS.md`
- `docs/archive/research-process/WSL2-VLM-BACKEND-DECISION.md`
- `docs/archive/review-briefs/VERIFY-REPORT-ingest.md`
- `docs/archive/review-briefs/VERIFY-REPORT-jev-b1.md`
- `docs/archive/review-briefs/announce-nav-cleanup-20260924.md`
- `docs/archive/review-briefs/b1b2-brief.md`
- `docs/archive/review-briefs/b1b2-report.md`
- `docs/archive/review-briefs/b3a-engine-report.md`
- `docs/archive/review-briefs/b3b-ccs-ui-brief.md`
- `docs/archive/review-briefs/b3b-ccs-ui-report.md`
- `docs/archive/review-briefs/b5-gate-brief.md`
- `docs/archive/review-briefs/b5-gate-report.md`
- `docs/archive/review-briefs/b6-p0-report.md`
- `docs/archive/review-briefs/ccs-chain-report.md`
- `docs/archive/review-briefs/d508773-report.md`
- `docs/archive/workbuddy-memory/memory/2026-10-08.md`
- `docs/archive/workbuddy-memory/memory/2026-10-09.md`
- `docs/archive/workbuddy-memory/memory/2026-10-10.md`
- `docs/archive/workbuddy-memory/memory/AUTO-CHAIN-HANDOFF.md`
- `docs/archive/workbuddy-memory/memory/CHAIN-UNCLOSED-AUDIT.md`
- `docs/archive/workbuddy-memory/memory/HANDOFF-CHECKLIST.md`
- `docs/archive/workbuddy-memory/memory/MEMORY.md`
- `docs/archive/workbuddy-memory/memory/automations/1b206fd3-357f-47a1-bf5b-e17ec5c419a3/memory.md`
- `docs/archive/workbuddy-memory/memory/automations/3b1225b1-e2f4-4504-ad29-581309175fdb/memory.md`
- `docs/archive/workbuddy-memory/memory/automations/7d23d426-8743-431f-a95e-62a3e2a6af36/memory.md`
- `docs/research/ARROW-CONFLICT-AUDIT-2026-10-12.md`
- `docs/research/ARROW-ROOT-CAUSES-2026-10-12.md`
- `docs/research/CHANNEL-SYSTEM-AUDIT-2026-10-12.md`
- `docs/research/DECISION-TABLE-2026-09-28.md`
- `docs/research/FINDINGS-INBOX-2026-09-28.md`
- `docs/research/HANDOFF-external-solutions.md`
- `docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md`
- `docs/research/HINDSIGHT-DEPLOYMENT-STATUS-2026-09-30.md`
- `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md`
- `docs/research/MEMPALACE-REVIEW-2026-09-30.md`
- `docs/research/MODEL-AVAILABILITY-2026-09-28.md`
- `docs/research/PAPER-可信政务问答技术-软件学报2026.md`
- `docs/research/RETRIEVAL-LITERATURE-SCAN-2026-09-30.md`
- `docs/research/RETRIEVAL-RESEARCH-LEDGER-2026-09-30.md`
- `docs/research/REVIEW-PLAN-A-verification.md`
- `docs/research/REVIEW-PLAN-B-innovation.md`
- `docs/research/SELF-CONTAINED-求助外部AI-检索召回上不去.md`
- `docs/research/STANDARDS-AND-RETRIEVAL-DIRECTION-2026-10-05.md`
- `docs/research/TECH-PATH-2026-09-28.md`
- `docs/research/archify/01-archify-逆向.md`
- `docs/research/archify/02-ks-现状.md`
- `docs/research/archify/03-借鉴结论.md`
- `docs/research/channels/PATH-REGISTRY-2026-10-08.md`
- `docs/research/channels/REGISTRY-STATUS.md`
- `docs/research/channels/internal-inventory.md`
- `docs/research/channels/law-cn.md`
- `docs/research/channels/oss-decomposition.md`
- `docs/research/channels/std-cn.md`
- `docs/research/dsh-official/INGEST-LEDGER-docs-zh.md`
- `docs/research/dsh-official/INGEST-LEDGER-notes-client-ui.md`
- `docs/research/dsh-official/INGEST-LEDGER-notes-zh.md`
- `docs/research/dsh-official/INGEST-LEDGER-notes.md`
- `docs/research/dsh-official/INGEST-LEDGER-pkg-agents.md`
- `docs/research/dsh-official/INGEST-LEDGER-pkg-docs.md`
- `docs/research/dsh-official/INGEST-LEDGER-pkg-readme-zh.md`
- `docs/research/dsh-official/INGEST-LEDGER-pkg-readme.md`
- `docs/research/dsh-official/INGEST-LEDGER-repo-docs.md`
- `docs/research/dsh-official/INGEST-LEDGER-root.md`
- `docs/research/dsh-official/INGEST-LEDGER-skills.md`
- `docs/research/dsh-official/dshdocs-A.md`
- `docs/research/dsh-official/dshdocs-B.md`
- `docs/research/dsh-official/dshdocs-C.md`
- `docs/research/dsh-official/dshdocs-D.md`
- `docs/research/dsh-official/dshdocs-E.md`
- `docs/research/dsh-official/dshdocs-F.md`
- `docs/research/dsh-official/dshdocs-G.md`
- `docs/research/dsh-official/dshdocs-H.md`
- `docs/research/ks-fixes/01-d2-rootcause.md`
- `docs/research/ks-fixes/02-modality-residual.md`
- `docs/research/ks-fixes/03-waiting-feedback.md`
- `docs/research/lay-language-retrieval-evidence.md`
- `docs/research/plan-vs-reality.md`
- `docs/research/rag-encyclopedia-study.md`
- `docs/research/retrieval-pipeline-design-merge.md`
- `docs/research/solutions-for-open-problems.md`
- `docs/research/substitute-scan.md`
- `docs/research/vision-coverage-map.md`
- `docs/survey/01-inventory.md`
- `docs/survey/11-module-index.md`
- `docs/survey/12-config-surface.md`
- `docs/survey/13-table-io.md`
- `docs/verify-briefs/VERIFY-REPORT-govqa-data-forensics.md`
- `docs/verify-briefs/VERIFY-REPORT-spec003-vecscope.md`
- `docs/verify-briefs/VERIFY-REPORT-spec004-operationalization.md`
- `docs/verify-briefs/VERIFY-REPORT-spec008-icon-system.md`
- `docs/verify-briefs/VERIFY-REPORT-spec009-turn-evidence-ui.md`
- `docs/verify-briefs/VERIFY-REPORT-spec010-turn-tab-fixes.md`

## 四、全部文档（按体积降序）

| 文件 | 体积 | 行数 | 入链 | 出链 | 标题 |
|---|---:|---:|---:|---:|---|
| `docs/archive/history/rounds-10.1-10.203.md` | 999 KB | 11,670 | 1 | 11 | 端点里嵌套的 async def 生成器（体内含 yield）若整段没有 Awa |
| `docs/DEVELOPMENT-HISTORY.md` | 331 KB | 524 | 12 | 46 | KnowledgeStation 开发历程简史 |
| `docs/UI-BASELINE.md` | 256 KB | 2,460 | 8 | 27 | UI 视觉基线（照 WeKnora 知识库管理复刻）—— 第 5 步的施工依据 |
| `docs/CHANNEL-COVERAGE-PLAN.md` | 244 KB | 2,781 | 6 | 53 | 法规/标准「渠道覆盖 + 巡检」改造方案（长周期 · 多轮次） |
| `docs/research/dsh-official/INGEST-LEDGER-notes-zh.md` | 231 KB | 1,118 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/research/dsh-official/INGEST-LEDGER-notes.md` | 225 KB | 1,122 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/REQUIREMENTS-v4.3.md` | 208 KB | 3,053 | 3 | 0 | 《通用国标与法律法规本地 AI 知识工作站 (Win11)》开发主计划 (v4. |
| `docs/archive/workbuddy-memory/memory/2026-10-09.md` | 178 KB | 2,110 | 0 | 0 | 2026-10-09 工作日志（workspace: zcode） |
| `docs/RETRIEVAL-LONG-RANGE-PLAN.md` | 168 KB | 1,500 | 13 | 51 | 检索与通用化：长周期计划 |
| `docs/survey/11-module-index.md` | 165 KB | 1,344 | 0 | 0 | 模块职责索引 |
| `docs/MATERIALS-PLANE-PLAN.md` | 154 KB | 1,394 | 2 | 6 | 材料平面与通用研究改造方案（v1 草案，待业主批准） |
| `docs/KB-FOLDER-PLAN.md` | 154 KB | 1,630 | 2 | 9 | 知识库多级目录 —— 施工单（业主 2026-09-21 定案） |
| `docs/research/channels/oss-decomposition.md` | 126 KB | 1,267 | 0 | 0 | 法规/标准获取与监控 · 开源项目**代码级**拆解 |
| `docs/research/weknora-ui/02-shell-and-other-pages.md` | 115 KB | 1,474 | 1 | 0 | WeKnora 前端精读 02 — 外壳与"知识库/问答之外"的全部界面 |
| `docs/research/channels/law-cn.md` | 112 KB | 1,354 | 0 | 0 | 中国法规类渠道调研报告（一手官方发布与查询渠道） |
| `docs/research/weknora-kb-ui/02-components-and-visual-language.md` | 87 KB | 645 | 2 | 0 | WeKnora 知识库管理界面 —— 组件构成与视觉语言 |
| `docs/research/weknora-kb-ui/01-pages-and-flows.md` | 86 KB | 840 | 2 | 1 | WeKnora「知识库管理」界面与流程记录 |
| `docs/research/weknora-ui/01-chat-and-citations.md` | 86 KB | 731 | 2 | 0 | WeKnora 前端「问答 / 对话」整块精读 |
| `docs/research/HINDSIGHT-DOCS-READING-2026-09-28.md` | 84 KB | 996 | 1 | 0 | Hindsight 官方文档 · 通读纪要（一手件，已核到行号） |
| `docs/research/weknora-ui-vs-ours.md` | 83 KB | 581 | 1 | 26 | 我们 vs WeKnora：知识库管理 UI 差距清单（**只诊断，不改代码** |
| `docs/research/STEP6-WORKORDER.md` | 82 KB | 1,043 | 1 | 4 | 第 6 步施工单 —— 插件侧借鉴 WeKnora 自带 DSH 插件的 6 条 |
| `docs/ENCYCLOPEDIA.md` | 78 KB | 926 | 0 | 9 | KnowledgeStation 技术百科全书（ENCYCLOPEDIA） |
| `docs/uniformity/03-docs-specs-scripts.md` | 74 KB | 641 | 1 | 6 | docs / specs / scripts 事实地图 |
| `docs/research/channels/std-cn.md` | 73 KB | 1,145 | 0 | 0 | 中国标准类官方渠道实测调研 |
| `docs/uniformity/01-core.md` | 70 KB | 1,064 | 1 | 0 | src/core 事实地图 |
| `docs/research/channels/internal-inventory.md` | 67 KB | 827 | 0 | 0 | 内部渠道拆解（internal inventory） |
| `docs/NEXT-DEV-PLAN-2026-09-28.md` | 67 KB | 657 | 2 | 46 | 后续开发计划（2026-09-28 会话收尾时制定） |
| `docs/uniformity/02-plugin.md` | 66 KB | 586 | 1 | 0 | plugin/ 事实地图 |
| `docs/research/FINDINGS-INBOX-2026-09-28.md` | 66 KB | 764 | 0 | 0 | 收件箱：调研线回传的"可借鉴结果"（我逐条读过并挑出来的） |
| `docs/INTERACTION-DESIGN.md` | 63 KB | 738 | 6 | 4 | 交互设计：向 WeKnora 学什么、我们怎么重做 |
| `docs/research/archify/01-archify-逆向.md` | 58 KB | 738 | 0 | 2 | archify 逆向：它靠什么产出「结构 + 证据指向」 |
| `docs/uniformity/README.md` | 56 KB | 889 | 13 | 19 | KnowledgeStation 摸底：证据与过程 |
| `docs/research/lay-gap-decomposition.md` | 55 KB | 757 | 1 | 2 | 大白话那道缺口怎么拆、哪条路能走：四条实测 |
| `docs/research/agent-memory-systems.md` | 53 KB | 544 | 2 | 1 | Agent 记忆系统：技术路径、实测效果、以及"RAG ↔ 记忆"的中间形态 |
| `docs/uniformity/09-big-files.md` | 52 KB | 609 | 1 | 0 | src/core 三个大文件事实地图 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-readme-zh.md` | 50 KB | 363 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/uniformity/06-frontend.md` | 48 KB | 523 | 1 | 0 | plugin/client 事实地图 |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-readme.md` | 48 KB | 363 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/research/weknora-ui/03-dsh-plugin-reference.md` | 48 KB | 575 | 2 | 24 | dsh-weknora 精读：同宿主现成插件参考实现 |
| `docs/GOVQA-UNWIRED-CHANNELS.md` | 48 KB | 465 | 0 | 0 | 未接线渠道清单（**给接线的对话用**） |
| `docs/research/MEMPALACE-REVIEW-2026-09-30.md` | 46 KB | 785 | 0 | 0 | MemPalace 调研 + B站介绍视频评论区核查 |
| `docs/archive/workbuddy-memory/memory/automations/1b206fd3-357f-47a1-bf5b-e17ec5c419a3/memory.md` | 45 KB | 457 | 0 | 0 | 自动续接链执行记忆（1b206fd3-357f-47a1-bf5b-e17ec5 |
| `docs/uniformity/07-other-dirs.md` | 44 KB | 432 | 1 | 0 | 其他目录事实地图 |
| `docs/research/archify/02-ks-现状.md` | 43 KB | 1,063 | 0 | 4 | 02 · KS 现状：问答 → 答案呈现 → 证据跳转（事实清单） |
| `docs/verify-briefs/VERIFY-REPORT-govqa-data-forensics.md` | 43 KB | 915 | 0 | 0 | 独立数据质量取证报告 —— `tools/gov-qa/` 政务问答语料 |
| `docs/archive/review-briefs/VERIFY-REPORT-ingest.md` | 42 KB | 635 | 0 | 0 | 独立复核报告 — `verify-freeze-ingest`（批次：`refe |
| `docs/uniformity/04-tests-tools-gates.md` | 41 KB | 621 | 1 | 0 | tests / tools / 门禁 事实地图 |
| `docs/archive/workbuddy-memory/memory/automations/7d23d426-8743-431f-a95e-62a3e2a6af36/memory.md` | 40 KB | 477 | 0 | 0 | 自动化执行记忆：gov-qa 推进到全国省市全覆盖 |
| `docs/uniformity/10-api-server.md` | 40 KB | 452 | 2 | 0 | api/server.py 事实地图 |
| `docs/survey/07-doc-surface.md` | 38 KB | 384 | 1 | 1 | 文档面 |
| `docs/verify-briefs/VERIFY-REPORT-spec004-operationalization.md` | 38 KB | 619 | 0 | 0 | 独立复核报告 —— `tools/gov-qa/` spec 004 可运维化层 |
| `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md` | 37 KB | 644 | 0 | 0 | Hindsight 部署：对一份外部 AI 分析报告的事实核查（2026-09- |
| `docs/research/channels/PATH-REGISTRY-2026-10-08.md` | 37 KB | 428 | 0 | 0 | 法规/标准发布源路径总表（2026-10-08 实测） |
| `docs/research/vision-coverage-map.md` | 36 KB | 341 | 0 | 2 | 愿景对照矩阵：**我们的每一块愿景，谁已经实现了** |
| `docs/research/channels/REGISTRY-STATUS.md` | 36 KB | 378 | 0 | 0 | 渠道台账状态快照（自动生成，勿手改） |
| `docs/research/ks-fixes/03-waiting-feedback.md` | 31 KB | 322 | 0 | 0 | 等待期前台提示：现状盘点 + 外部借鉴（只分析，未改代码） |
| `docs/research/dsh-official/INGEST-LEDGER-repo-docs.md` | 30 KB | 190 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/archive/workbuddy-memory/memory/CHAIN-UNCLOSED-AUDIT.md` | 30 KB | 314 | 0 | 6 | 自动推进链「忽略 / 没收口」审计（2026-10-09 人工轮） |
| `docs/verify-briefs/VERIFY-REPORT-govqa-conformance.md` | 30 KB | 660 | 1 | 0 | 独立复核报告 —— `verify-freeze-govqa-conforman |
| `docs/INDEX.md` | 30 KB | 276 | 0 | 0 | docs/ 总索引（机械生成，勿手改） |
| `docs/archive/review-briefs/b3b-ccs-ui-report.md` | 29 KB | 467 | 0 | 0 | 独立复核报告 —— B3b「补全分类号」的**界面半边** |
| `docs/research/dsh-official/ERRATA-alpha.2.md` | 29 KB | 322 | 5 | 1 | 勘误：`alpha.1 → alpha.2` 对 8 份分片与记忆条目的影响 |
| `docs/research/ks-fixes/02-modality-residual.md` | 29 KB | 555 | 0 | 0 | 模态核验残留误报：根因与修复方案（2026-10-19 真机实测） |
| `docs/archive/review-briefs/b3a-engine-report.md` | 29 KB | 458 | 0 | 0 | 独立复核报告 —— KnowledgeStation「补全分类号」引擎半边（B3 |
| `docs/research/weknora-ui/00-index-and-proposal.md` | 29 KB | 191 | 3 | 4 | WeKnora 界面「抄 / 改着抄 / 不抄」清单（草稿 —— 等业主确认） |
| `docs/archive/review-briefs/b6-p0-report.md` | 29 KB | 466 | 0 | 0 | B6 定向独立复核 — 09-23 两提交（P0 黑屏修 / 棘轮基线记新） |
| `docs/research/solutions-for-open-problems.md` | 29 KB | 306 | 0 | 0 | 我们当前未解的问题：外部解法调研 |
| `docs/research/skill-knowledge-three-layer-reference.md` | 29 KB | 416 | 1 | 3 | Agent「技能 / 知识」三层结构 —— 四路调研参考材料 |
| `docs/archive/review-briefs/ccs-chain-report.md` | 28 KB | 478 | 0 | 0 | 独立复核报告 —— 「分类号（CCS）三层查询链 + 补全自愈」 |
| `docs/archive/research-process/REALTIME-VALIDITY-VERIFY-RESEARCH.md` | 28 KB | 381 | 0 | 1 | 法规/国标效力「打开即核验」实施细节报告 |
| `docs/survey/04-data-shape.md` | 28 KB | 879 | 1 | 0 | 数据形状（表 / 列 / 索引） |
| `docs/research/dsh-official/dshdocs-C.md` | 28 KB | 173 | 0 | 1 | DSH 文档消化 · 面向「在 DSH 内做功能」的插件作者 |
| `docs/archive/impl-reports/B3A-REPORT.md` | 27 KB | 377 | 0 | 3 | B3a 实施报告 —— 「补全分类号」引擎侧第二轮（CCS 自愈） |
| `docs/research/SELF-CONTAINED-求助外部AI-检索召回上不去.md` | 26 KB | 424 | 0 | 0 | 一份自包含的求助文档：**我们的检索召回上不去，接下来该走哪条路？** |
| `docs/research/cross-language-retrieval-evidence.md` | 25 KB | 305 | 4 | 5 | 非中文资料上的检索口径证据（英文开发文档 / 技术文档） |
| `docs/research/wikiskill-integration-assessment.md` | 25 KB | 371 | 2 | 1 | WikiSkill（arXiv 2608.27454）融合评估 |
| `docs/research/golden-instrument-audit.md` | 25 KB | 370 | 1 | 3 | 评价尺子审计：金标门禁测的不是产品所在的世界 |
| `docs/research/dsh-official/INGEST-LEDGER-docs-zh.md` | 24 KB | 183 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/NOT-DOING.md` | 23 KB | 126 | 21 | 23 | 已否决 / 已作废台账（**提任何新待办、计划、设计之前先对一遍这份**） |
| `docs/research/dsh-official/INGEST-LEDGER.md` | 23 KB | 188 | 1 | 0 | DSH 官方文档原文入库账本 |
| `docs/research/dsh-official/dshdocs-G.md` | 23 KB | 140 | 0 | 0 | DSH decision-record digest — third-party |
| `docs/archive/review-briefs/b1b2-report.md` | 23 KB | 345 | 0 | 0 | 独立复核报告 —— B1（重新解析丢目录归属）+ B2（叠字检查两个假绿洞） |
| `docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md` | 23 KB | 336 | 0 | 0 | 本地资料检索工具：下一步路线征询（v4） |
| `docs/research/ks-fixes/01-d2-rootcause.md` | 23 KB | 320 | 0 | 0 | D2 冒烟失败根因分析（只读分析，未改任何代码） |
| `docs/research/RETRIEVAL-LITERATURE-SCAN-2026-09-30.md` | 22 KB | 344 | 0 | 0 | 检索文献调研（2026-09-30）：我们这个问题在学界叫什么、已经做到哪一步 |
| `docs/archive/review-briefs/b5-gate-report.md` | 22 KB | 332 | 0 | 0 | B5 门禁复核报告 —— 「环境白名单只增不减」的修法（含门禁临时目录自清） |
| `docs/archive/review-briefs/VERIFY-REPORT-jev-b1.md` | 22 KB | 568 | 0 | 0 | VERIFY-REPORT-jev-b1 |
| `docs/research/substitute-scan.md` | 22 KB | 273 | 0 | 0 | 替代品扫描（substitute scan）——"谁已经交付了同样的用户价值" |
| `docs/research/dsh-official/dshdocs-E.md` | 22 KB | 149 | 0 | 0 | DSH 官方设施速查（插件作者版） |
| `docs/research/dsh-official/dshdocs-F.md` | 21 KB | 81 | 0 | 2 | DSH 文档消化：插件作者防重复踩坑（F） |
| `docs/survey/05-api-surface.md` | 21 KB | 253 | 1 | 0 | 接口面（后端 + 前端路由） |
| `docs/LAW-SOURCE-PLAN.md` | 21 KB | 307 | 2 | 0 | 法律法规官方来源获取方案（flk.npc.gov.cn + gov.cn） |
| `docs/archive/research-process/DSH-ALIGNMENT-AUDIT.md` | 21 KB | 160 | 2 | 11 | DSH 适配审计与整改清单（2026-09-19） |
| `docs/research/rag-encyclopedia-study.md` | 21 KB | 220 | 0 | 1 | RAG 全景资料学习笔记：哪些能借、哪些是我们自己走出来的 |
| `docs/research/HANDOFF-external-solutions.md` | 21 KB | 276 | 0 | 0 | 交接任务书：把「我们当前未解的问题」的外部解法找齐 |
| `docs/research/dsh-official/dshdocs-H.md` | 21 KB | 92 | 0 | 0 | DSH 官方技能与门禁摘要（H） |
| `docs/verify-briefs/VERIFY-REPORT-exp17-prod-plan.md` | 20 KB | 263 | 1 | 0 | 独立复核报告 · exp-17-embedding-production-pla |
| `docs/research/cross-plane-jump-assessment.md` | 20 KB | 283 | 1 | 3 | 跨平面交叉引用（法条 ↔ 你自己的文档）：评估与待决方案 |
| `docs/verify-briefs/VERIFY-REPORT-e4b-round2.md` | 20 KB | 308 | 3 | 0 | 独立复核报告：E4 第二轮验证（批次 `e4b-round2`） |
| `docs/research/dsh-official/REALIGN.md` | 20 KB | 284 | 2 | 1 | DSH 升级后：文档与记忆的重对齐手册 |
| `docs/research/TECH-PATH-2026-09-28.md` | 20 KB | 213 | 0 | 0 | 技术路径：通用资料检索 + 派生记忆（2026-09-28 定稿） |
| `docs/archive/old-plans/CHANNEL-R6C-DESIGN.md` | 19 KB | 228 | 0 | 0 | R6c 设计：五类监控打通 + 巡检降级链来自台账（只出设计，不动代码） |
| `docs/research/four-layer-pipeline-evidence.md` | 19 KB | 261 | 2 | 2 | 四层检索链路：别人怎么做 / 我们缺什么（对账单） |
| `docs/verify-briefs/VERIFY-REPORT-rerank-fix.md` | 19 KB | 252 | 3 | 0 | 独立复核报告 · 批次 `rerank-fix`（施工总纲 P0·0.7 修复） |
| `docs/HANDOVER-2026-10-09.md` | 19 KB | 246 | 0 | 0 | 交接文档（2026-10-09 · KnowledgeStation 主体项目） |
| `docs/research/dsh-official/dshdocs-B.md` | 19 KB | 137 | 0 | 0 | DSH 插件作者摘要（Host + Client 两半） |
| `docs/archive/old-plans/EXECUTION-PLAN.md` | 19 KB | 78 | 7 | 7 | 执行计划（自主执行台账）—— 业主 2026-09-19 全权授权 |
| `docs/verify-briefs/VERIFY-REPORT-p010-long-tail.md` | 18 KB | 202 | 3 | 0 | 独立复核报告 · 批次 `p010-long-tail` |
| `docs/research/classical-chinese-segmentation-evidence.md` | 18 KB | 246 | 5 | 5 | 古籍/文言资料上的切分口径证据（P3.2） |
| `docs/verify-briefs/VERIFY-REPORT-spec007-ui-polish.md` | 18 KB | 140 | 1 | 0 | VERIFY-REPORT · spec 007（UI 精修）第二轮独立复核 |
| `docs/research/plan-vs-reality.md` | 18 KB | 185 | 0 | 2 | 计划特性 × 谁做到了（逐条对照） |
| `docs/verify-briefs/VERIFY-REPORT-p32-classical-seg.md` | 18 KB | 258 | 4 | 0 | 独立复核报告：P3.2 古籍/文言切分评估（批次 `p32-classical- |
| `docs/archive/old-plans/AUTO-DRAFT-PLAN.md` | 17 KB | 210 | 0 | 1 | 自动成文（系统起草结论）——立项论证与设计（2026-09-18） |
| `docs/research/DECISION-TABLE-2026-09-28.md` | 17 KB | 136 | 0 | 0 | 对策表：抄哪一处 / 不抄哪一处 / 我们独有的那一条 |
| `docs/research/dsh-official/dshdocs-D.md` | 17 KB | 123 | 0 | 0 | DSH 官方文档消化：工具 / LLM / 会话 / 子代理 |
| `docs/research/archify/03-借鉴结论.md` | 16 KB | 207 | 0 | 1 | archify 对比与借鉴结论 |
| `docs/wiki/architecture.md` | 16 KB | 248 | 5 | 13 | KnowledgeStation：项目目标与现状 |
| `docs/research/retrieval-pipeline-design-merge.md` | 16 KB | 202 | 0 | 1 | 通用召回链路：8 方案评审与合并（目标链路 v1） |
| `docs/VISION-TREE.md` | 16 KB | 184 | 1 | 5 | KnowledgeStation 功能愿景（客户视角版） |
| `docs/README.md` | 16 KB | 170 | 14 | 16 | KnowledgeStation 文件地图 |
| `docs/verify-briefs/VERIFY-REPORT-spec003-vecscope.md` | 16 KB | 231 | 0 | 0 | 独立复核报告 · spec 003「向量通道范围下推修复」 |
| `docs/uniformity/08-why-contracts-rot.md` | 16 KB | 263 | 1 | 0 | 为什么"约定了契约"还是会变乱 |
| `docs/PLAN-REAL-QUESTION-RULER.md` | 15 KB | 293 | 0 | 2 | 用真人问答造新评测尺子 —— 方案（草案 v1） |
| `docs/archive/workbuddy-memory/memory/MEMORY.md` | 15 KB | 66 | 0 | 0 | 项目长期记忆（KnowledgeStation / D:\AI\work spa |
| `docs/archive/impl-reports/B3B-REPORT.md` | 15 KB | 188 | 0 | 0 | B3B-REPORT —— 「补全分类号」的**界面**半边（B3b） |
| `docs/verify-briefs/VERIFY-REPORT-exp13-query-rewrite.md` | 15 KB | 201 | 3 | 0 | 独立复核报告 · exp-13 查询侧改写（A/B/C/D） |
| `docs/archive/research-process/GOVQA-DIAGNOSIS-2026-10-10.md` | 15 KB | 233 | 0 | 0 | gov-qa 模块全面诊断（2026-10-10） |
| `docs/research/SURVEY-标准与法规问答调研（含王芳2023全文精读）.md` | 14 KB | 198 | 1 | 0 | 扩大到"标准问答 / 法规问答"的调研（不限于政务问答） |
| `docs/research/weknora-assessment.md` | 14 KB | 155 | 3 | 2 | WeKnora（腾讯开源知识库）对我们的影响评估 |
| `docs/verify-briefs/VERIFY-REPORT-t016-t017-p1fix.md` | 14 KB | 199 | 2 | 0 | 独立复核报告 — T016/T017 P1 修复批次（`doc_stds` 未定 |
| `docs/research/jev-mem-assessment.md` | 14 KB | 160 | 1 | 0 | Jev-Mem 影响评估（2026-09-24） |
| `docs/archive/handovers/HANDOVER-2026-10-06.md` | 14 KB | 210 | 0 | 0 | 交接文档（2026-10-06 召回诊断） |
| `docs/uniformity/report.md` | 13 KB | 241 | 1 | 0 | 统一化报告（repo-uniformity-ratchet 留档） |
| `docs/uniformity/START-HERE.md` | 13 KB | 249 | 2 | 5 | KnowledgeStation 上手（新人第一份读这个） |
| `docs/research/lay-language-retrieval-evidence.md` | 13 KB | 175 | 0 | 0 | 用户用大白话提问时，检索怎么接住——外部证据 + 本库实测 |
| `docs/research/HINDSIGHT-DEPLOYMENT-STATUS-2026-09-30.md` | 13 KB | 213 | 0 | 0 | Hindsight 本机部署现状交接说明 |
| `docs/TEST-FLAKES.md` | 13 KB | 38 | 0 | 0 | 测试 flake 清单（已知偶发/竞态型，非回归勿背锅） |
| `docs/verify-briefs/VERIFY-REPORT-exp14-fused-rewrite.md` | 13 KB | 230 | 3 | 0 | 独立复核报告 · exp-14-fused-rewrite |
| `docs/archive/old-plans/AUTORUN-PLAN-2026-09-24.md` | 13 KB | 103 | 2 | 1 | 自动执行清单（2026-09-24 全仓复盘后，业主授权全自动执行） |
| `docs/survey/13-table-io.md` | 12 KB | 333 | 0 | 0 | 表读写关系 |
| `docs/archive/review-briefs/d508773-report.md` | 12 KB | 172 | 0 | 0 | 独立复核报告 — `d508773`（"③假绿补硬：复核点名三处验收牙加硬"） |
| `docs/research/dsh-official/dshdocs-A.md` | 12 KB | 87 | 0 | 0 | DSH 客户端插件（右栏 UI）开发摘要 |
| `docs/verify-briefs/VERIFY-REPORT-e4c-1024.md` | 12 KB | 137 | 3 | 0 | 独立复核报告 · E4c「同模型升维 512→1024」 |
| `docs/research/SURVEY-口径核查与多跳（回应业主两条批评）.md` | 12 KB | 179 | 1 | 0 | 他们的"有效"到底拿什么量的？（口径核查）+ **多跳这件事** |
| `docs/research/REVIEW-PLAN-B-innovation.md` | 12 KB | 160 | 0 | 0 | 评审任务书 B：路线级独立评审与超越（交给最强的 AI） |
| `docs/research/SURVEY-学术调研-第1轮-排序与评测集.md` | 12 KB | 164 | 2 | 0 | 学术调研 · 第 1 轮：**排序/重排**与**评测集**（对应我们的判据①② |
| `docs/survey/02-code-map.md` | 12 KB | 210 | 2 | 0 | 代码地图（AST 级符号清单） |
| `docs/research/P0-4B-EVIDENCE-2026-10-14.md` | 11 KB | 233 | 1 | 0 | P0.4b 取证报告：通道 A/D/E 的排序键**到底有没有用** |
| `docs/verify-briefs/VERIFY-REPORT-ratchet-2.md` | 11 KB | 137 | 3 | 0 | 独立复核报告 —— ratchet-2 批次（复核员 general-purpo |
| `docs/research/SURVEY-学界做法值不值得抄-效果与工作量评估.md` | 11 KB | 172 | 1 | 0 | 学界做法**到底值不值得抄**：效果、工作量、能不能纯写代码 |
| `docs/INTRODUCTION.md` | 11 KB | 162 | 0 | 1 | KnowledgeStation 产品介绍 —— 让你自己机器上的资料，随问随查 |
| `docs/research/SURVEY-学术调研-第4轮-STARD可用率与总结论.md` | 11 KB | 189 | 2 | 0 | 学术调研 · 第 4 轮：★ **把 STARD 量成了我们现成的考卷** |
| `docs/ANNOUNCE-MODULE-STATUS-2026-10-08.md` | 11 KB | 164 | 0 | 0 | 部委公告监控 / 法规标准动态抓取 —— 模块现状（2026-10-08 代码通 |
| `docs/archive/old-plans/BASELINE-PLAN-2026-10-06.md` | 11 KB | 225 | 2 | 1 | 基础层实验路线（2026-10-06 定） |
| `docs/research/SURVEY-学术调研-第2轮-查询改写与官方标准.md` | 11 KB | 153 | 2 | 0 | 学术调研 · 第 2 轮：**LLM 查询改写**与**同类系统/官方评测标准* |
| `docs/verify-briefs/VERIFY-REPORT-exp15-pool-depth-fusion.md` | 11 KB | 135 | 4 | 0 | VERIFY-REPORT — `exp-15-pool-depth-fusio |
| `docs/survey/10-observed.md` | 11 KB | 246 | 1 | 1 | 观察记录（中性，不下结论） |
| `docs/research/SURVEY-学术调研-第3轮-还债与收敛.md` | 11 KB | 157 | 2 | 0 | 学术调研 · 第 3 轮：**还债 + 四条主线收敛** |
| `docs/survey/06-test-surface.md` | 11 KB | 209 | 1 | 0 | 测试面 |
| `docs/research/dsh-official/README.md` | 11 KB | 111 | 14 | 3 | DSH 官方文档精读（8 份分片） |
| `docs/ROADMAP-CLIENT-VIEW.md` | 10 KB | 120 | 1 | 7 | 路线图（客户视角）—— 短期 / 长期 / 效果 / 边界 |
| `docs/archive/workbuddy-memory/memory/2026-10-10.md` | 10 KB | 135 | 0 | 0 | 2026-10-10 工作日志 |
| `docs/archive/research-process/BASELINE-DIAGNOSIS-2026-10-06.md` | 10 KB | 207 | 3 | 3 | 基础层诊断记录（2026-10-06） |
| `docs/survey/00-method.md` | 10 KB | 175 | 1 | 0 | 检查计划：怎么把整个项目「检一遍」并保证没有漏 |
| `docs/research/lay-phrasing-scaleup-test.md` | 10 KB | 154 | 2 | 3 | 放大到 2000 条之后：50 术语那轮的结论哪些站住了、哪些变了 |
| `docs/research/RETRIEVAL-RESEARCH-LEDGER-2026-09-30.md` | 9 KB | 147 | 0 | 0 | 调研台账（防失忆）—— 2026-09-30 会话 |
| `docs/uniformity/00-review-of-surveys.md` | 9 KB | 141 | 1 | 0 | 摸底报告的主对话复核记录 |
| `docs/verify-briefs/VERIFY-REPORT-spec010-turn-tab-fixes.md` | 9 KB | 164 | 0 | 0 | VERIFY-REPORT · spec 010（「本轮」页三处修正）—— ** |
| `docs/research/REVIEW-PLAN-A-verification.md` | 9 KB | 138 | 0 | 0 | 评审任务书 A：事实核查（交给能力一般的 AI） |
| `docs/archive/research-process/CHANNEL-PROBE-REPORT.md` | 9 KB | 80 | 0 | 0 | 标准官方渠道时效巡检选型实测报告 |
| `docs/archive/review-briefs/README.md` | 9 KB | 104 | 13 | 0 | 复核任务书（VERIFY-BRIEF）与复核结论的归属层 |
| `docs/research/SURVEY-学术界怎么设计政务问答（沿36条参考文献）.md` | 9 KB | 110 | 1 | 0 | 学术界的政务问答是怎么设计的（沿《可信政务问答技术》36 条参考文献调研） |
| `docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md` | 9 KB | 88 | 0 | 0 | Hindsight 官方能力核实 —— 「我们是不是在造轮子」 |
| `docs/research/SURVEY-学术调研-总清单（要落地看这一页）.md` | 8 KB | 115 | 1 | 7 | ★ 学术调研 · 总清单（四轮汇总，**要落地看这一页**） |
| `docs/PORTABILITY.md` | 8 KB | 128 | 2 | 1 | 便携与路径纪律 |
| `docs/archive/review-briefs/b3b-ccs-ui-brief.md` | 8 KB | 101 | 0 | 0 | 独立复核任务书 —— B3b「补全分类号」的**界面半边** |
| `docs/research/PAPER-可信政务问答技术-软件学报2026.md` | 8 KB | 126 | 0 | 0 | 论文精读：《大语言模型驱动的可信政务问答技术》（软件学报 2026） |
| `docs/research/STANDARDS-AND-RETRIEVAL-DIRECTION-2026-10-05.md` | 8 KB | 126 | 0 | 0 | 外部标准与检索方向调研（2026-10-05） |
| `docs/research/SURVEY-两条核实-GuRE语料性质与RefWalk表义.md` | 7 KB | 133 | 1 | 0 | 两条待核实的**核查结果**（GuRE 的语料性质 / RefWalk 的表义） |
| `docs/archive/review-briefs/b1b2-brief.md` | 7 KB | 85 | 0 | 0 | 复核任务书 —— B1（重导丢归属）+ B2（叠字检查两个假绿洞） |
| `docs/verify-briefs/VERIFY-REPORT-spec009-turn-evidence-ui.md` | 7 KB | 125 | 0 | 0 | VERIFY-REPORT · spec 009（「本轮依据」三处改动）—— * |
| `docs/research/lay-phrasing-retrieval-test.md` | 7 KB | 98 | 2 | 3 | 拿"大白话"真搜一遍：50 个术语 × 100 条外行说法 |
| `docs/archive/review-briefs/b5-gate-brief.md` | 7 KB | 80 | 0 | 0 | 复核任务书 —— B5：门禁「环境白名单只增不减」的修法（含门禁临时目录自清） |
| `docs/verify-briefs/VERIFY-REPORT-spec008-icon-system.md` | 7 KB | 122 | 0 | 0 | VERIFY-REPORT · spec 008（图标体系）—— **自查**（ |
| `docs/verify-briefs/VERIFY-REPORT-ratchet-1.md` | 7 KB | 94 | 3 | 0 | 独立复核报告 —— ratchet-1 批次（复核员 general-purpo |
| `docs/archive/handovers/HANDOVER-2026-09-23.md` | 7 KB | 57 | 0 | 2 | KnowledgeStation 交接文档（2026-09-23 晚） |
| `docs/research/lay-phrasing-prompt.md` | 7 KB | 91 | 2 | 2 | 「大白话 ↔ 行话」生成提示词（A 组：给术语写外行说法） |
| `docs/research/ARROW-CONFLICT-AUDIT-2026-10-12.md` | 7 KB | 146 | 0 | 1 | 红箭头为什么"还是没生效"—— 旧代码与现状的对照核查（2026-10-12） |
| `docs/archive/research-process/PROJECT-CONSOLIDATION-2026-10-05.md` | 6 KB | 146 | 0 | 0 | 项目盘整（2026-10-05）：第一性原理看文档与进度 |
| `docs/UI-ICON-SYSTEM.md` | 6 KB | 130 | 2 | 2 | UI 图标体系（KnowledgeStation 插件） |
| `docs/research/CHANNEL-SYSTEM-AUDIT-2026-10-12.md` | 6 KB | 143 | 0 | 0 | 采集/更新通道系统核实报告（2026-10-12，纯读代码 + 读库） |
| `docs/tool-catalog.md` | 6 KB | 59 | 1 | 1 | ks-dsh-plugin 工具目录（生成物——**手改必红**，改说明书后跑  |
| `docs/archive/research-process/PROJECT-STATUS-2026-10-05.md` | 6 KB | 120 | 2 | 2 | 项目状态与卡点（2026-10-05） |
| `docs/archive/research-process/STD-STATUS-CHANNELS.md` | 6 KB | 80 | 0 | 0 | 国标有效性查询源分类与多渠道备份矩阵（2026-08-27 实测定型） |
| `docs/uniformity/05-verifier-findings.md` | 6 KB | 101 | 1 | 0 | verifier 抽查记录（2026-10-23） |
| `docs/wiki/components/storage.md` | 6 KB | 115 | 1 | 0 | storage（存取与 schema） |
| `docs/wiki/components/plugin-tools.md` | 6 KB | 62 | 1 | 1 | plugin-tools（插件对 agent 暴露的工具） |
| `docs/verify-briefs/VERIFY-REPORT-e9-col-prior.md` | 6 KB | 93 | 2 | 0 | 独立复核报告 · 批次 `e9-col-prior`（P2 诊断·第 1 刀） |
| `docs/archive/workbuddy-memory/memory/AUTO-CHAIN-HANDOFF.md` | 6 KB | 82 | 0 | 0 | AUTO-CHAIN 交接单（每轮覆盖写） |
| `docs/research/dsh-official/INGEST-LEDGER-skills.md` | 5 KB | 45 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/survey/12-config-surface.md` | 5 KB | 89 | 0 | 0 | 配置面（环境变量 + 配置键） |
| `docs/archive/workbuddy-memory/memory/HANDOFF-CHECKLIST.md` | 5 KB | 94 | 0 | 0 | 交接清单 · KnowledgeStation（`D:\AI\work spac |
| `docs/naming-convention.md` | 5 KB | 115 | 1 | 2 | 命名与分类规范（正式件） |
| `docs/research/MODEL-AVAILABILITY-2026-09-28.md` | 5 KB | 73 | 0 | 0 | 调度记录：免费模型逐个真调（2026-09-28） |
| `docs/survey/09-runtime.md` | 5 KB | 105 | 1 | 0 | 运行时：引擎怎么起、端口令牌在哪、数据放哪 |
| `docs/wiki/components/llm.md` | 5 KB | 76 | 1 | 0 | llm（模型调用与取证答案） |
| `docs/wiki/components/exports.md` | 5 KB | 70 | 2 | 1 | exports（产出物组装与导出） |
| `docs/wiki/components/api.md` | 4 KB | 88 | 1 | 1 | api（HTTP 端点） |
| `docs/research/ARROW-ROOT-CAUSES-2026-10-12.md` | 4 KB | 124 | 0 | 0 | 红箭头画不出 —— 全部根因（2026-10-12，逐条实测） |
| `docs/wiki/components/quality.md` | 4 KB | 67 | 1 | 0 | quality（质量判定） |
| `docs/CODE-REVIEW-CHECKLIST.md` | 4 KB | 49 | 0 | 0 | 代码评审七条清单（含必验五种并入版） |
| `docs/BROKEN-LINKS.md` | 4 KB | 66 | 0 | 1 | 已知断链台账（**不许静默忽略**） |
| `docs/wiki/components/update-channels.md` | 4 KB | 54 | 1 | 1 | update-channels（渠道适配器） |
| `docs/wiki/components/law-source.md` | 4 KB | 60 | 1 | 0 | law-source（官方法规来源管线） |
| `docs/wiki/components/settings.md` | 4 KB | 68 | 1 | 0 | settings（设置与凭据） |
| `docs/survey/01-inventory.md` | 4 KB | 83 | 0 | 0 | 全仓清单（四本账） |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-docs.md` | 4 KB | 29 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/wiki/components/compliance.md` | 4 KB | 67 | 1 | 0 | compliance（合规差距分析） |
| `docs/wiki/components/domain.md` | 4 KB | 67 | 1 | 0 | domain（域模型契约） |
| `docs/survey/08-gate-surface.md` | 4 KB | 111 | 1 | 0 | 门禁面 |
| `docs/wiki/components/README.md` | 3 KB | 53 | 13 | 20 | 组件契约索引 |
| `docs/wiki/components/verification.md` | 3 KB | 63 | 1 | 0 | verification（核验与纠错守卫） |
| `docs/wiki/components/vision.md` | 3 KB | 67 | 1 | 0 | vision（本地视觉反查） |
| `docs/wiki/components/query.md` | 3 KB | 65 | 1 | 0 | query（查询理解） |
| `docs/archive/workbuddy-memory/README.md` | 3 KB | 59 | 13 | 0 | 归档：项目内 `.workbuddy-ai/`（WorkBuddy 自动链的记忆 |
| `docs/research/dsh-official/INGEST-LEDGER-notes-client-ui.md` | 3 KB | 27 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/archive/history/README.md` | 3 KB | 80 | 13 | 1 | 开发史明细归档（§10.1 – §10.203） |
| `docs/research/papers/README.md` | 3 KB | 54 | 13 | 0 | 外部原件存放处（检索文献调研） |
| `docs/wiki/components/retrieval.md` | 3 KB | 71 | 2 | 0 | retrieval（检索） |
| `docs/archive/README.md` | 3 KB | 68 | 13 | 2 | 归档区：这里放什么、怎么查 |
| `docs/wiki/components/update.md` | 3 KB | 59 | 2 | 0 | update（渠道巡检与变更） |
| `docs/research/hindsight-official/README.md` | 3 KB | 54 | 13 | 3 | Hindsight 官方文档本地副本 |
| `docs/survey/README.md` | 3 KB | 65 | 13 | 10 | 项目现状地图 |
| `docs/archive/review-briefs/announce-nav-cleanup-20260924.md` | 3 KB | 48 | 0 | 0 | 真库清理留档：22 条"栏目导航"型误发现（2026-09-24） |
| `docs/wiki/components/ingestion.md` | 3 KB | 62 | 1 | 0 | ingestion（解析与入库） |
| `docs/survey/COVERAGE.md` | 3 KB | 51 | 2 | 0 | 覆盖对账（九个面） |
| `docs/archive/research-process/WSL2-VLM-BACKEND-DECISION.md` | 2 KB | 47 | 0 | 0 | 决策记录：WSL2 解锁 vlm/hybrid 本地后端 —— 否决（2026- |
| `docs/wiki/components/materials.md` | 2 KB | 51 | 1 | 0 | materials（材料平面） |
| `docs/wiki/components/knowledge.md` | 2 KB | 51 | 1 | 0 | knowledge（法规知识本体与分类） |
| `docs/research/dsh-official/INGEST-LEDGER-root.md` | 2 KB | 29 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/survey/03-cross-ref.md` | 2 KB | 42 | 1 | 0 | 引用关系 |
| `docs/archive/workbuddy-memory/memory/2026-10-08.md` | 2 KB | 26 | 0 | 0 | 2026-10-08 工作日志（workspace: zcode） |
| `docs/research/dsh-official/INGEST-LEDGER-pkg-agents.md` | 2 KB | 22 | 0 | 0 | DSH 官方文档原文入库账本 |
| `docs/archive/workbuddy-memory/memory/automations/3b1225b1-e2f4-4504-ad29-581309175fdb/memory.md` | 0 KB | 3 | 0 | 0 | 看门狗执行记录（KS 自动续接） |