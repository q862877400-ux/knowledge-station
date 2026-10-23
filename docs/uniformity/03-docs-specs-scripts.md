# docs / specs / scripts 事实地图

> 调查范围：`docs/`（214 份 md）、`specs/`（15 个目录）、`scripts/`（68 个顶层受控脚本 + 3 个子目录）。
> 方法：只读 + `Get-ChildItem` / `git log -1 --format=%cs` / `git grep` / `Select-String`。
> **没有跑门禁、没有跑 pytest、没有跑 `snapshot-project.ps1`。**
> 每条结论后面括号里是**可搜索的文字 + 文件**；数不出来的写「未读，原因」。
> 统计口径注明「实测」的，命令写在该节第一行，可原样复跑。

**先纠正任务书里的两个数字**（都实测过，不是我猜）：

1. **顶层不是 30 份，是 29 份。**
   `Get-ChildItem docs -File -Filter *.md` → **29**。其中 **28 份受 git 跟踪**，1 份（`EXTERNAL-REVIEW-ARCHITECTURE-v4.md`）**未跟踪**（`git status --short docs/` 显示 `?? docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md`，`git ls-files` 对它返回空）。任务书列的名单本身是 29 个名字 —— 说明「30」是笔误。
2. **`measure-*.py` 是 11 个，不是 10 个。**
   `Get-ChildItem scripts -File -Filter 'measure-*.py'` → 11。

`docs/` md 分布（实测，与任务书给的数完全吻合）：顶层 29 + `archive/` 46 + `research/` 97 + `verify-briefs/` 21 + `wiki/` 21 = **214**。

---

## 一、docs 顶层 29 份总表

日期取 `git log -1 --format=%cs -- <file>`；大小取 `Length`（B，四舍五入到 KB）。

| 文件名 | 是什么 | 谁读 | 最后更新 | 大小 | 真源 or 历史 |
|---|---|---|---|---|---|
| `ANNOUNCE-MODULE-STATUS-2026-10-08.md` | 部委「公告栏/通知公告」监控模块的代码通读现状（两条独立流程、零 LLM 启发式解析、四类变更信号） | 改 `src/core/update/announce.py` 的人 | 2026-10-10 | 11 KB | **时点快照**（标题自带日期，正文写「模块现状（2026-10-08 代码通读）」），不是持续维护的真源 |
| `BROKEN-LINKS.md` | 已知断链台账：只登记「修复面在别的写入方手里、当场改会撞车」的断链，带归谁 + 复查判据 | 每次收工前跑 `check-links.py` 的人 | 2026-10-10 | 4 KB | **真源**（但当前读数「断链 0 处」，见 §三 第 8 组） |
| `CHANNEL-COVERAGE-PLAN.md` | 法规/标准「渠道覆盖 + 巡检」长周期方案 + **逐轮台账**（R1–R20 全部轮次的判据与读数） | 接渠道线的人 | 2026-10-11 | 244 KB / 2781 行 | **真源**（自称「本文件是这条线的唯一进度真源（ledger）」） |
| `CODE-REVIEW-CHECKLIST.md` | 评审七条（判据有牙 / 对账留痕 / 诚实边界 …）+ 必验五种并入版 | 每次自查与派复核前 | 2026-09-23 | 4 KB | **真源**（`AGENTS.md` 复核节直接链到它） |
| `DEVELOPMENT-HISTORY.md` | 开发简史：§一~§九 叙事 + §十 逐轮索引（10.1~10.251，单行极长） | 想知道「当初为什么这么做」的人 | 2026-10-18 | 331 KB / 524 行 | **真源**（AGENTS.md「做过什么 → 开发史」） |
| `ENCYCLOPEDIA.md` | 技术百科全书：架构 / 数据契约 / 检索 / 入库 / 坑全集 / 红线宪法（§1–§17 + 附录） | 要查**具体技术事实**的人 | 2026-10-11 | 78 KB / 926 行 | **真源**（自称「技术事实唯一权威」），**但已不是入口**（见 §三 第 9 组） |
| `EXTERNAL-REVIEW-ARCHITECTURE-v4.md` | 给外部高级 AI 的路线征询书：一页纸背景 + 名词 + 核验过的现状数字（每个数带口径）+ 一个主问题三个子问题 | 对外征询时发出去 | **无**（未跟踪，`git ls-files` 为空） | 23 KB | **草稿/一次性对外件**；`docs/README.md` 标它「受版本控制 ✅」是**错的**（见 §三 第 7 组） |
| `GOVQA-UNWIRED-CHANNELS.md` | 未接线渠道清单：什么叫「接线」+ 逐条清单 + 接线完成判据（自称自包含） | 接手 gov-qa 接线的人 | 2026-10-11 | 48 KB / 465 行 | **真源**，但数字与另两份冲突（§三 第 3 组） |
| `HANDOVER-2026-10-09.md` | 交接文档：项目是什么 / 现在在哪 / 下一步 / 禁碰边界 / 自动链说明 | **接手主体项目的人先读这一份** | 2026-10-11 | 19 KB | **时点交接**（正文写「下表是 2026-10-09 快照」），**已有明显过期项**（§三 第 2 组） |
| `INDEX.md` | 机械生成的 docs 总索引（文件名 / KB / 最后改 / 一句话） | 想按「一句话」找文件的人 | 2026-10-18 | 28 KB | **生成物**（「机械生成，勿手改」，`scripts/docs/gen-doc-index.py`），**当前已落后**（§三 第 6 组） |
| `INTERACTION-DESIGN.md` | 向 WeKnora 学什么、我们怎么重做（含「现在真跑着的是什么」一节） | 改 `plugin/client/` 界面的人 | 2026-10-11 | 63 KB / 738 行 | **半真源**：方案节是**方案**（正文自写「本文后面几节写的是方案。方案与代码会对不上」），现状节是真源 |
| `INTRODUCTION.md` | 产品介绍：是什么 / 解决什么问题 / 为什么可信 / 能力清单 | 业主、外部读者 | 2026-10-06 | 11 KB | **真源（对外）**，但数字最旧（§三 第 1/2 组） |
| `KB-FOLDER-PLAN.md` | 知识库多级目录施工单 + 逐轮施工记录（1630 行） | 改知识库目录功能的人 | 2026-10-11 | 154 KB / 1630 行 | **真源**（自称「本文件是这件事的唯一方案真源」） |
| `LAW-SOURCE-PLAN.md` | 法律法规官方来源获取方案（flk.npc.gov.cn + gov.cn 白名单、docx→PDF） | 改 `knowledge/law_source/` 的人 | 2026-10-10 | 21 KB | **真源**，但抬头还写着「状态：方案（2026-08-24 制定，**待确认后实施**）」—— 早已实施（spec 006 已 Closed） |
| `MATERIALS-PLANE-PLAN.md` | 材料平面与通用研究改造方案（v1 草案 + 逐轮追记，1394 行） | 改 `src/core/materials/` 的人 | 2026-10-11 | 154 KB / 1394 行 | **真源**，但抬头仍写「**待批准**」—— 正文自写「『一行代码都没写』—— **已被取代**」，说明早已落地 |
| `naming-convention.md` | 命名与分类规范正式件（规则本身，不含取舍理由） | 动任何文件名/目录名前 | 2026-10-10 | 5 KB | **真源**（自称「本文件是规则的唯一归属层」） |
| `NEXT-DEV-PLAN-2026-09-28.md` | 从总纲台账里抽出的「现在该做什么」清单（657 行，逐轮追记） | 想按优先级排活的人 | 2026-10-11 | 67 KB / 657 行 | **派生视图**（自写「不新增范围、不改优先级」「性质：从施工总纲抽出」），非独立真源 |
| `NOT-DOING.md` | 已否决 / 已作废台账（提案前必对一遍） | **任何人提新待办/计划/设计之前** | 2026-10-11 | 23 KB | **真源**（`AGENTS.md` 动手之前节强制） |
| `PLAN-REAL-QUESTION-RULER.md` | 用真人问答造新评测尺子的方案（三层尺子 + 三个坑 + 待拍板） | 做评测/召回度量的人 | 2026-10-12 | 15 KB | **真源但已实施**：抬头写「✅ 已实施（2026-10-12，spec 010）」，保留原文 + 就地留痕 |
| `PORTABILITY.md` | 便携与路径纪律：运行时靠什么做到拷贝即走 + 发现写死路径时怎么判 | 改路径解析/打包的人 | 2026-10-18 | 8 KB | **真源**（纪律本体在 `AGENTS.md` §环境，本文是判据） |
| `README.md` | **文件地图**：每一样东西在哪、用来干什么 | 所有人；接手的 agent 第一站 | 2026-10-17 | 14 KB / 156 行 | **真源**（自称「地图只住本文件，入口只住根 README」） |
| `REQUIREMENTS-v4.3.md` | 旧主计划 v4.3（需求 SSOT）：R1–R79 + R-L1~R14 + T00~T13 的权威出处 | 要查某个 R 编号**原文**的人 | 2026-10-10 | 208 KB / 3053 行 | **历史文档**（自写「本文件**不随代码更新**（历史需求文档）」）；2026-09-19 被删、2026-10-10 从 git 原样恢复 |
| `RETRIEVAL-LONG-RANGE-PLAN.md` | 检索与通用化长周期计划（施工总纲）+ 逐轮台账（1500 行） | 接检索线的人 | 2026-10-14 | 168 KB / 1500 行 | **真源**，但顶部三条 🔴 仍写「2026-10-05 开发暂停」，而 2026-10-12/14 又立了 010/013 两个 spec 在施工（§三 第 5 组） |
| `ROADMAP-CLIENT-VIEW.md` | 客户视角路线图（只看功能与效果） | 业主 | 2026-09-25 | 10 KB | **视图**（自写「本文不是进度真源，只是视图」），三条线之一已过期 |
| `TEST-FLAKES.md` | 已知偶发/竞态型测试 flake 清单（含机理、复现命令、处置） | 看到偶发红先查这一页 | 2026-10-18 | 11 KB | **真源**（`AGENTS.md` 复核节直接链到它） |
| `tool-catalog.md` | 6 个模型工具的说明书与参数表（生成物） | 查工具契约 / 改说明书后重生成 | 2026-09-24 | 6 KB | **生成物**（「手改必红」，由 `smoke-tool-catalog.mjs --write` 生成） |
| `UI-BASELINE.md` | UI 视觉基线（照 WeKnora 复刻）+ 逐面审查记录（2460 行） | 改 `plugin/client/` 样式的人 | 2026-10-12 | 256 KB / 2460 行 | **真源**（尺度与留边的唯一出处） |
| `UI-ICON-SYSTEM.md` | 图标体系规范（唯一真源，含例外表与诚实边界） | 改图标用法前 | 2026-10-10 | 6 KB | **真源**（自称「本文件是 KS 图标用法的唯一真源」） |
| `VISION-TREE.md` | 功能愿景（客户视角，每条标「今天点得到吗」🟢🟡⚪🔒） | 业主 | 2026-09-25 | 16 KB | **视图**，正文自写「本次只做三件事：把已过期的三处更正」 |

**一句话概括这一节**：29 份里 **15 份自称「唯一真源/唯一归属层」**（BROKEN-LINKS、CHANNEL-COVERAGE、CODE-REVIEW、DEVELOPMENT-HISTORY、ENCYCLOPEDIA、GOVQA-UNWIRED、KB-FOLDER、LAW-SOURCE、MATERIALS-PLANE、naming-convention、NOT-DOING、PORTABILITY、README、TEST-FLAKES、UI-BASELINE、UI-ICON-SYSTEM），
**4 份是生成物/派生视图**（INDEX、tool-catalog、NEXT-DEV-PLAN、ROADMAP-CLIENT-VIEW、VISION-TREE），
**3 份是历史**（REQUIREMENTS-v4.3、ANNOUNCE-MODULE-STATUS、HANDOVER），**2 份是方案但已实施**（PLAN-REAL-QUESTION-RULER、LAW-SOURCE-PLAN 抬头未改）。

---

## 二、docs 子目录

### 2.1 `archive/`（46 份 md）

**里面是什么**：8 个按**性质**（不按时间）分的子目录，判据写在 `archive/README.md` §一：

| 子目录 | md 数 | 装什么 |
|---|---|---|
| `review-briefs/` | 14 | 已收口的复核任务书与报告（`b1b2-brief` / `b3a-engine-report` / `VERIFY-REPORT-ingest` …） |
| `workbuddy-memory/` | 11 | 已退役工具 WorkBuddy 的记忆与交接单（含 `memory/automations/*/memory.md` ×3） |
| `research-process/` | 9 | 调研过程记录（`GOVQA-DIAGNOSIS-2026-10-10.md`、`PROJECT-STATUS-2026-10-05.md` …） |
| `old-plans/` | 5 | 被取代的计划全文（`EXECUTION-PLAN.md`、`BASELINE-PLAN-2026-10-06.md` …） |
| `handovers/` | 2 | 旧交接（`HANDOVER-2026-09-23.md` / `HANDOVER-2026-10-06.md`） |
| `impl-reports/` | 2 | 一次性实施报告（`B3A-REPORT.md` / `B3B-REPORT.md`） |
| `history/` | 2 | 逐轮明细（`rounds-10.1-10.203.md`，从开发史拆出） |
| `old-baselines/` | 0 | 过期基线快照 —— **空目录**，只在 README 里有条目 |

**有没有过期声明**：**有，而且很硬**。`archive/README.md` 第 3 行逐字写着：

> **这里是历史，不是当前真源。** 现在该怎么做，看 [docs/README.md](../README.md)（大 map）与 [wiki](../wiki/)。

并且 §四 写死了「归档件不可逆地回到『当前真源』：**MUST NOT** 把归档件直接移回 `docs/` 当现状用」。
但**子目录内部的文件自身不带过期声明** —— 打开 `old-plans/EXECUTION-PLAN.md` 看到的是当年正文，没有任何「此文件已作废」的抬头。唯一的过期信号来自**目录位置**，不是文件内容。

**`archive/README.md` 的索引全不全**：**不全，而且是结构性的不全。**
实测：`archive/` 下除 README 外共 **42 份 md**（46 减去 4 个 README），把每个 `BaseName` 拿去 README 全文匹配，**只有 4 个命中**（`MEMORY`、`memory` 这类子串误命中），**38 个文件的名字在 README 里一次都没出现**：

```
HANDOVER-2026-09-23 / HANDOVER-2026-10-06 / rounds-10.1-10.203 /
B3A-REPORT / B3B-REPORT / AUTO-DRAFT-PLAN / AUTORUN-PLAN-2026-09-24 /
BASELINE-PLAN-2026-10-06 / CHANNEL-R6C-DESIGN / EXECUTION-PLAN /
BASELINE-DIAGNOSIS-2026-10-06 / CHANNEL-PROBE-REPORT / DSH-ALIGNMENT-AUDIT /
GOVQA-DIAGNOSIS-2026-10-10 / PROJECT-CONSOLIDATION-2026-10-05 /
PROJECT-STATUS-2026-10-05 / REALTIME-VALIDITY-VERIFY-RESEARCH /
STD-STATUS-CHANNELS / WSL2-VLM-BACKEND-DECISION /
announce-nav-cleanup-20260924 / b1b2-brief / b1b2-report / b3a-engine-report /
b3b-ccs-ui-brief / b3b-ccs-ui-report / b5-gate-brief / b5-gate-report /
b6-p0-report / ccs-chain-report / d508773-report / VERIFY-REPORT-ingest /
VERIFY-REPORT-jev-b1 / 2026-10-08 / 2026-10-09 / 2026-10-10 /
AUTO-CHAIN-HANDOFF / CHAIN-UNCLOSED-AUDIT / HANDOFF-CHECKLIST
```

`archive/README.md` **只按 8 个类别给了入口**（「旧计划全文 → `old-plans/`」这种），**没有逐文件清单**。它的自述是「**按用途能找到**」，所以这是**设计如此**，不是漏写；代价是「我想知道归档区里有没有 X」只能靠 `git grep`，README 帮不上。README §三 也确实给了替代路径：「某个词出现在哪 → 直接搜 `git grep -n "<词>" -- docs/archive/`」。
⇒ **结论：索引是「分类索引」不是「文件索引」，完整度按分类口径是 100%，按文件口径是 4/42。**

### 2.2 `research/`（97 份 md）

按目录分（实测 `Get-ChildItem -Recurse -Filter *.md`，合计 97）：

| 目录 | 份数 | 是什么 |
|---|---|---|
| 根（`docs/research/*.md`） | 54 | 混杂：学术调研、外部项目评估、证据报告、决策表 |
| `dsh-official/` | 23 | **DSH 官方文档精读**（8 份分片 `dshdocs-A~H` + 12 份 `INGEST-LEDGER-*` + `ERRATA-alpha.2.md` + `REALIGN.md` + `README.md`） |
| `channels/` | 6 | 渠道调研（`internal-inventory` / `law-cn` / `std-cn` / `oss-decomposition` / `PATH-REGISTRY-2026-10-08` / `REGISTRY-STATUS`） |
| `weknora-ui/` | 4 | WeKnora 界面源码精读（外壳/设置/引用/DSH 插件参考） |
| `archify/` | 3 | Archify 逆向 + KS 现状 + 借鉴结论（**未跟踪**，`git status` 显示 `?? docs/research/archify/`） |
| `ks-fixes/` | 3 | D2 冒烟根因 / 模态残留 / 等待反馈（**未跟踪**） |
| `weknora-kb-ui/` | 2 | WeKnora 知识库页面与视觉语言 |
| `hindsight-official/` | 1 | Hindsight 官方资料（只有 `README.md`，其余是 `llms-full.txt`/`openapi.json`） |
| `papers/` | 1 | 论文（只有 `README.md`，其余是 pdf/txt/html） |

**分几类**：按内容实际是**四类混在一个目录里**，目录结构只分了两个（`dsh-official` 外部、`weknora-*` 外部），其余全堆在根：

1. **DSH 官方研究**（23 + 根里若干）—— `dsh-official/` 是唯一有独立 README 的子目录，抬头写死版本口径：「下面的 8 份分片……都是按 `dsh-v0.1.6-alpha.1`（sha `0a15e36e7f`）写的」，业主已于 2026-09-19 升到 alpha.2，差异逐条在 `ERRATA-alpha.2.md`。**这是全 `research/` 里版本口径写得最严的一块。**
2. **外部项目评估** —— `weknora-assessment.md`（14 KB）、`weknora-ui-vs-ours.md`（83 KB）、`jev-mem-assessment.md`、`MEMPALACE-REVIEW-2026-09-30.md`、`wikiskill-integration-assessment.md`、`archify/`。判据在 `AGENTS.md`：「先查有没有现成的」。
3. **学术调研** —— `SURVEY-*` 9 份 + `RETRIEVAL-LITERATURE-SCAN-2026-09-30.md` + `PAPER-*`。**有汇总页**：`SURVEY-学术调研-总清单（要落地看这一页）.md` 自称「本页是『该做什么』的索引」。
4. **内部证据/诊断报告** —— `ARROW-ROOT-CAUSES-2026-10-12.md`、`CHANNEL-SYSTEM-AUDIT-2026-10-12.md`、`lay-gap-decomposition.md`（56 KB）、`FINDINGS-INBOX-2026-09-28.md`（66 KB）、`P0-4B-EVIDENCE-2026-10-14.md`、`golden-instrument-audit.md`。

**哪几份还是当前有效结论**：实测方法是「被 `docs/` 顶层或 `specs/` 或 `AGENTS.md` 按文件名引用」——
**94 / 97 份被引用**，只有 3 份完全没人引用，正是未跟踪的 `ks-fixes/` 三份（`01-d2-rootcause` / `02-modality-residual` / `03-waiting-feedback`）。
但「被引用」不等于「结论仍有效」：`RETRIEVAL-LITERATURE-SCAN-2026-09-30.md`、`MODEL-AVAILABILITY-2026-09-28.md`、`TECH-PATH-2026-09-28.md` 这类带日期的，被引用是因为**开发史里记录了当时的判断**，不是因为结论还算数。真正**当前有效**且被反复引用的只有几份：`plan-vs-reality.md`（R 编号对照）、`cross-language-retrieval-evidence.md`、`lay-gap-decomposition.md`、`dsh-official/ERRATA-alpha.2.md`、`channels/PATH-REGISTRY-2026-10-08.md`。
**⚠ `research/` 没有 `README.md`**（`Test-Path docs/research/README.md` → False），这是全 docs 里**唯一一个没有索引的顶层子目录**；`docs/README.md` 对它的描述只有一行「**外部研究**的结论（读别人的东西得到的）」。

### 2.3 `verify-briefs/`（21 份 md）

**这是什么**：独立复核报告与取证报告。**没有 README**（`Test-Path docs/verify-briefs/README.md` → False）。
命名统一 `VERIFY-REPORT-<主题>.md`，正文首行是「# VERIFY-REPORT · <主题>」，紧跟一段自述性质。

**给谁用**：给**下一次要派复核的人**看纪律与判据，给**收口时**当证据。`AGENTS.md` 复核节的写法是「报告首尾各记一次 `git rev-parse HEAD` + `git status --short`」，这些报告逐份照做。

**还有效吗 —— 分两半，这一半是本次调查最值得记的一条**：
21 份里有 **3 份是自查，不是独立复核**。判据是正文抬头逐字写着「**自查**（非独立第三方）」：

| 文件 | 抬头原文 |
|---|---|
| `VERIFY-REPORT-spec008-icon-system.md` | 「# VERIFY-REPORT · spec 008（图标体系）—— **自查**（非独立第三方）」+「团队复核机制在本环境下**三次派发全部失败**」 |
| `VERIFY-REPORT-spec009-turn-evidence-ui.md` | 「# VERIFY-REPORT · spec 009（「本轮依据」三处改动）—— **自查**（非独立第三方）」+「连续五次派发全部失败」 |
| `VERIFY-REPORT-spec010-turn-tab-fixes.md` | 「# VERIFY-REPORT · spec 010（「本轮」页三处修正）—— **自查**（非独立第三方）」+「连续七次派发全部失败」 |

它们自己写清了弱点：「我对自己的实现有先入之见，**看不出的错就是看不出**」「**不能**替代独立复核」。
⇒ **`verify-briefs/` 里 18 份是独立复核、3 份是自查**。任何拿「有复核报告」当「已独立复核」的说法，对这 3 份是**不成立**的。这正是 `AGENTS.md` 复核节要防的那类事，而这 3 份**如实标了**，属于诚实做法，不是缺陷。

其余 18 份按主题：召回实验 7 份（`e4b-round2` / `e4c-1024` / `exp13` / `exp14` / `exp15` / `exp17-prod-plan` / `p010-long-tail`）、门禁自身 2 份（`ratchet-1` / `ratchet-2`）、gov-qa 2 份、spec 4 份（`spec003` / `spec004` / `spec007` / 加上自查的 3 份）、其它（`p32-classical-seg` / `e9-col-prior` / `rerank-fix` / `t016-t017-p1fix` / `govqa-data-forensics`）。

**日期**：2026-10-09（14 份）→ 2026-10-10（4 份）→ 2026-10-11（1 份）→ 2026-10-12（2 份）。**没有 2026-10-12 之后的**，即**最新一份距今已落后于 `src/` 的实际状态**（开发史 §10.250/§10.251 是 2026-10-18 的事）。

### 2.4 `wiki/`（21 份 md）

结构：`wiki/architecture.md`（1 份，166 行）+ `wiki/components/`（19 篇 + `README.md` 索引 + `.gitkeep`）。

**`wiki/architecture.md`**：自称入口 —— 「**这一页给接手的人**：读完能说出这个项目要做什么、现在做到哪、主要部件各干什么。」`README.md`（根）与 `ENCYCLOPEDIA.md` 都认它是入口。**但它带的数字是全场最旧的**（§三 第 2 组）。

**`wiki/components/` 覆盖度 —— 这是任务书点名要的数，我按「目录级」和「文件级」两个口径都数了**：

- **`src/core` 的实际一级子目录 = 16 个**（排除 `__pycache__`）：
  `api` `compliance` `domain` `exports` `ingestion` `knowledge` `llm` `materials` `quality` `query` `retrieval` `settings` `storage` `update` `verification` `vision`。
  **任务书说的「17 个子系统」不成立** —— 17 是**把 `__pycache__` 也数进去了**（`Get-ChildItem src/core -Directory` → 17 条，其中一条是 `__pycache__`）。
- **嵌套子目录只有 2 个**：`knowledge/law_source`、`update/channels`。
- **`wiki/components/` 的页面 = 19 篇**：16 个一级目录**全部有**（16/16），2 个嵌套子目录**全部有**（`law-source.md` / `update-channels.md`），再加 1 篇 `plugin-tools.md`（插件侧，不属于 `src/core`）。
- ⇒ **`src/core` 的 16 个一级目录 + 2 个嵌套子目录 = 18 个单元，18/18 全覆盖**。`wiki/components/README.md` 第 45 行自称「`src/core/` 的 **18 个组件**（16 个一级目录 + `knowledge/law_source`、`update/channels` 两个子目录）逐篇 + 插件侧 1 篇 = **19 篇**（SC-006 达成）」—— **这个自述与实际文件数一致，是对的**。
- **真正的问题不是覆盖数，是时效**：18 篇引擎页里 **17 篇的 git 日期都是 2026-10-05**（spec 001 一次性产物），只有 `vision.md` 是 2026-10-11。而 `src/core` 在 2026-10-09~10-18 之间被改过很多轮（`clause_vec` 加 `doc_id`、`catalog_hidden` 检索守卫、law_source 定时刷新……），**这些都没有回写进 components 页**。`wiki/components/README.md` 自己立了规矩「改了某个子系统的对外接口 ⇒ 同步改对应那篇」，但实测**没有执行**。
- **另一个口径冲突**：`docs/README.md` 说「`src/core/` | **Python 引擎**，**19 个子系统**」，然后列了 **18 个名字**（`api`…`update/channels`）+ 一个路径前缀 `src/core/`。反引号项数 = 19，其中 1 项是路径不是子系统 ⇒ **「19 个子系统」这句话自身就差 1**。而 `INTRODUCTION.md` 写「引擎 **16 个子系统模块**」。三个数：19 / 18 / 16（见 §三 第 4 组）。

---

## 三、文档重叠与冲突（9 组，全部带原文片段）

判据：同一件事写在 ≥2 处，且措辞/数字不一致。**每组标出哪个更新**（看 `git log -1 --format=%cs`）。

### 第 1 组：`schema.sql` 到底几张表 —— 34 / 38 / 60 / 62，四个数，实际 44

| 文件 | 原文（逐字） | 文件日期 |
|---|---|---|
| `docs/ENCYCLOPEDIA.md` §7.3 | 「`schema.sql` # **34 表**（32 CREATE TABLE + clause_fts/clause_vec 虚拟表）+ 索引（冻结）」 | 2026-10-11（但正文注「2026-09-16 实测」） |
| `docs/ENCYCLOPEDIA.md` §8 另一处 | 「**34 表 DDL 冻结于 `src/core/storage/schema.sql`**（**2026-09-16 实测**：32 个 `CREATE TABLE`」 | 同上 |
| `docs/INTRODUCTION.md` | 「引擎 16 个子系统模块，`schema.sql` 冻结 **38 张表对象**（35 实体 + 3 虚拟表：`clause_fts`/`clause_vec`/`material_fts`；另有 1 张 `law_catalog` 由法规源模块懒建）」 | 2026-10-06 |
| `docs/wiki/architecture.md` | 「sqlite（`schema.sql` 冻结 **38 张表对象**）」 | 2026-10-10 |
| `docs/wiki/components/storage.md` | 「（**38 张表对象**：35 实体 + 3 虚拟表 `clause_fts` / `clause_vec` / `material_fts`）。」 | 2026-10-05 |
| `docs/HANDOVER-2026-10-09.md` | 「`doc_meta` **8,983 篇** / `clause_revision` **663,634 条** / `clause_fts` 663,634 / **60 张表**」 | 2026-10-11 |
| `docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md` | 「663,634 条条款；数据库 **62 张表**，2.88 GB」 | 未跟踪，无日期 |

**实测（我数的）**：`src/core/storage/schema.sql` 里 `CREATE TABLE` **41** 处、`CREATE VIRTUAL TABLE` **3** 处 ⇒ **44 个表对象**（41 实体 + 3 虚拟）。
**哪个是新的**：按日期，`HANDOVER`（60，2026-10-11）和 `EXTERNAL-REVIEW`（62）最新，`INTRODUCTION`（38）次之，`ENCYCLOPEDIA`（34）最旧。**但四个数没有一个等于实测的 44** —— 说明**没有任何一份文档跟着 schema 改过**。`ENCYCLOPEDIA` 那句还自带「2026-09-16 实测」，即它数的是 2026-09-16 那天的 schema，之后加了 12 张表（含 `material*` 4 张、`folder*` 3 张、`doc_filing_state`、`doc_ccs_state`、`channel_test_case` 等）**一处都没回写**。

### 第 2 组：真库规模 —— 6,797 篇 / 522,021 条 vs 8,983 篇 / 663,634 条

| 文件 | 原文（逐字） | 文件日期 |
|---|---|---|
| `docs/wiki/architecture.md` L44 | 「\| 法规/国标语料 \| **6,797 篇 / 522,021 条条款** \|」 | 2026-10-10 |
| `docs/HANDOVER-2026-10-09.md` L57 | 「\| 规模 \| `doc_meta` **8,983 篇** / `clause_revision` **663,634 条** / `clause_fts` 663,634 / **60 张表** \|」 | 2026-10-11 |
| `docs/HANDOVER-2026-10-09.md` L63（**它自己点破了这个冲突**） | 「- 旧文档里的 **"6,797 篇 / 522,021 条"已过时** —— 真库一直在长（本日实测 8,983 / 663,634）。」 | 2026-10-11 |
| `docs/NEXT-DEV-PLAN-2026-09-28.md` | 「`doc_meta.legal_status`（doc 级） \| effective **8,963** / reference **16** / withdrawn **4** / **NULL 0**；合计 **8,983**」 | 2026-10-11 |
| `docs/PLAN-REAL-QUESTION-RULER.md` | 「**1,430 篇文档的 `standard_no` 里带着 `(OCR采集)` 后缀**（占 **8,983 篇的 15.9%**）」 | 2026-10-12 |

**哪个是新的**：**8,983 / 663,634 是新的**（2026-10-11 HANDOVER 明写「本日实测」），**6,797 / 522,021 是旧的**（HANDOVER 直接点名它过时）。
**冲突点**：`wiki/architecture.md` 是**接手第一站**、`docs/README.md` 说「想知道项目目标与现状，看 wiki/architecture.md」—— 结果**最该准的一页拿的是最旧的数**，而纠正它的那句话**藏在一份 19 KB 的交接文档正文里**，不在 wiki 里。
（注：这两个数我都**没有**去连生产库核对，因为本任务禁跑、且真库在 `%APPDATA%`；这里只判「文档之间谁新谁旧」。）

### 第 3 组：渠道台账几条 —— 131 / 280 / 286（且「没接线」273 与 262+11 对不上）

| 文件 | 原文（逐字） | 文件日期 |
|---|---|---|
| `src/core/update/channel_seed.json` | `"counts": {"total":131, "by_wiring":{"seed_only":113,"unwired":11,"wired":7}}`；`"generated_at": "2026-09-18 13:19:50"` | 2026-09-18 |
| `docs/CHANNEL-COVERAGE-PLAN.md` | 「- **种子**：`src/core/update/channel_seed.json`（**131 条**）」；「**131 条**（`inserted 131 / updated 0`）；`summary` = `wired 6 / unwired 10 / broken 2 / seed_only 113`」 | 2026-10-11 |
| `docs/wiki/architecture.md` L45 | 「\| 渠道台账 \| **131 条**（其中含 github 字样 19 条） \|」 | 2026-10-10 |
| `docs/research/channels/REGISTRY-STATUS.md` | 「台账 **280** 条 · 启用 278 条 · **能干活（wired）7** 条 · 已知失效 **0** 条 · 仅登记 262 条」（并自注「自动生成，勿手改」「生成时间：2026-10-08 18:13:24」） | 2026-10-11 |
| `docs/GOVQA-UNWIRED-CHANNELS.md` §二 | 「\| **`seed_only`（登记了，没接）** \| **262** \|」「\| **`unwired`（明确未接）** \| **11** \|」「\| （对照）`wired` 已接 \| 13 \|」「\| **合计** \| **286** \|」 | 2026-10-11 |

**哪个是新的**：**286（含 13 条 wired）/ 280 是新的**（2026-10-11，`GOVQA-UNWIRED-CHANNELS` 自称「从真库 `update_channel` 表现读现算（不手写）」），**131 是旧的**（2026-09-18 的种子文件）。
**冲突点有两个**：
1. `131` 与 `286` 差一倍多，而 `wiki/architecture.md`（接手第一站）拿的还是 131。
2. **`GOVQA-UNWIRED-CHANNELS.md` 自己内部对不上**：§二 表说 `wired` = **13**，而 §一「样板」节说「这 **13** 条已经接好了」；但 `channel_seed.json` 的 `by_wiring` 写的是 `wired: 7`、`CHANNEL-COVERAGE-PLAN.md` 写的是 `wired 6 / unwired 10 / broken 2 / seed_only 113`（合计 131）。**「接线」这个词在同一批文档里对应 6 / 7 / 13 三个数。**

### 第 4 组：`src/core` 有几个子系统 —— 19 / 18 / 16

| 文件 | 原文（逐字） | 文件日期 |
|---|---|---|
| `docs/README.md` L25 | 「\| `src/core/` \| **Python 引擎**，**19 个子系统**：`api`（HTTP 端点）/ `ingestion`（解析入库）/ … / `law_source` / `update/channels` \| ✅ \|」 | 2026-10-17 |
| `docs/wiki/components/README.md` L45 | 「**✅ 覆盖率 100%**：`src/core/` 的 **18 个组件**（16 个一级目录 + `knowledge/law_source`、`update/channels` 两个子目录）逐篇 + 插件侧 1 篇 = **19 篇**（SC-006 达成）。」 | 2026-10-05 |
| `docs/INTRODUCTION.md` L153 | 「- 引擎 **16 个子系统模块**，`schema.sql` 冻结 **38 张表对象**」 | 2026-10-06 |

**实测**：`src/core` 一级子目录 **16**（排除 `__pycache__`）；嵌套子目录 **2**；`docs/README.md` 那句里的反引号项共 **19** 个，其中第一个是路径 `src/core/` 不是子系统 ⇒ **实际列了 18 个名字**。
**哪个是新的**：`docs/README.md`（2026-10-17）最新，但它那句**自身算术不对**（说 19、列 18）。`INTRODUCTION`（16）数的是**一级目录**，口径不同但没写明；`wiki/components/README`（18）口径最清楚（一级 + 嵌套），且与实测文件数一致。
⇒ **正确数是 18（16 一级 + 2 嵌套），而文档里最新、最显眼的那一处写的是 19。**

### 第 5 组：检索总纲「已暂停」vs 之后仍在施工的 spec

| 文件 | 原文（逐字） | 文件日期 |
|---|---|---|
| `docs/RETRIEVAL-LONG-RANGE-PLAN.md` L3–L6 | 「🔴 **2026-10-05 状态更新：开发暂停，卡在基础层（召回率不知道怎么保证）。**」「本文仍是"做什么、按什么顺序"的真源；**暂停的是执行，不是这份计划。**」 | 2026-10-14（文件本身在更新，暂停横幅没删） |
| `specs/010-real-question-ruler/spec.md` | 「**Input**: 业主 2026-10-11 令「我们现在已经有了这么多真人问答……」＋ 方案稿 `docs/PLAN-REAL-QUESTION-RULER.md` ＋ 业主本轮自主任期授权」 | 2026-10-12 |
| `specs/013-catalog-hidden-retrieval-guard/spec.md` | 「**Input**: 总纲 `docs/RETRIEVAL-LONG-RANGE-PLAN.md` §3 的 **P0.5**（测试假样本的处置）+ 业主令「继续施工」」 | 2026-10-14 |

**哪个是新的**：**spec 010 / 013（2026-10-12 / 10-14）是新的**，暂停横幅（2026-10-05）是旧的。
**冲突点**：同一份文件**既是「已暂停」的宣告处，又是「继续施工」的依据来源**（013 逐字引用它的 §3）。读的人先撞到「开发暂停」，再往下读 1500 行台账，才知道 10-12 之后又开工了 —— **暂停横幅没有「已恢复」的对应更新**，而这份文件 2026-10-14 明明被改过。

### 第 6 组：`docs/INDEX.md` 说 210 份，实际 214 份（且它自己缺自己）

| 出处 | 原文（逐字） |
|---|---|
| `docs/INDEX.md` L4 | 「> 共 **210 份** / **7338 KB**。」 |
| 实测 | `Get-ChildItem docs -Recurse -File -Filter *.md` → **214**（本轮调查开始时；现已 217，见下） |
| 实测 | INDEX 里的表格行 `^\| \`docs/…\`` → **210 行**（与它自称的份数一致） |

**差在哪（机械 diff，两边都列）**：
```
磁盘有、INDEX 没有（4 份）：
  docs/INDEX.md                      ← 索引不列自己
  docs/research/ks-fixes/01-d2-rootcause.md
  docs/research/ks-fixes/02-modality-residual.md
  docs/research/ks-fixes/03-waiting-feedback.md
INDEX 有、磁盘没有：0 份
```
`docs/research/ks-fixes/` 三份是**未跟踪**文件（`git status` 显示 `?? docs/research/ks-fixes/`，mtime 2026-10-21 22:29~22:31），**晚于 INDEX 的 mtime 2026-10-19 17:48** ⇒ **INDEX 落后是因为生成后又有新文件，且没重生成**。
**另一个矛盾**：`docs/README.md` §四 写「`docs/INDEX.md` 是**机械生成**的（`scripts/docs/gen-doc-index.py`），**不要手改**」，而 `git status --short docs/` 显示 **` M docs/INDEX.md`**（已修改未提交）—— 状态与「不要手改」的规矩**无法从仓库判断是否被手改过**。
**还有一处**：`docs/README.md` §1.2 表格把 `docs/INDEX.md` 排在第一行并标「✅ 受版本控制」，这没错；但它**没有出现在 INDEX 自己的 210 行里**，说明生成器明确跳过自己（`scripts/docs/gen-doc-index.py` L3：`docs = sorted(p for p in (root/"docs").rglob("*.md") if p.name != "INDEX.md")`）—— **这是设计，不是 bug**，但让「共 210 份」这句话永远比真实份数少 1（再加未跟踪文件）。

### 第 7 组：`docs/README.md` 标「受版本控制 ✅」，实际未跟踪

| 出处 | 原文（逐字） |
|---|---|
| `docs/README.md` L52 | 「\| **`docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md`** \| **给外部高级 AI 的路线征询（自包含）**… \| ✅ \|」（最后一列 = 「受版本控制」） |
| 实测 | `git ls-files docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md` → **空**；`git status --short` → **`?? docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md`** |
| 实测 | `git log -1 --format=%cs -- docs/EXTERNAL-REVIEW-ARCHITECTURE-v4.md` → **空**（无任何提交） |

**哪个是新的**：`docs/README.md`（2026-10-17）是最新一次改动，但这一行的「✅」与 git 状态矛盾。
**后果**：这份文件**没有历史、不能回滚、`check-links.py` 断了也没人补**；而 `docs/README.md` 恰恰教人「要请外部给下一步路线时，发这一份」。
**同族**：`docs/README.md` L63 说 `verify-briefs/` 是「**（17 份）**」，实测 **21 份**（`Get-ChildItem docs/verify-briefs -File -Filter *.md` → 21）。这是**同一张表里的第二个错数**。

### 第 8 组：`BROKEN-LINKS.md` 说「断链 0 处」，而它是「断链台账」

| 出处 | 原文（逐字） |
|---|---|
| `docs/BROKEN-LINKS.md` L19–L21 | 「## 一、当前在读：**0 处** ✅」「**2026-10-10 17:3x 实测**：`断链 0 处。`」 |
| 同文件 L5–L9 | 「**这一页就是那类断链的登记处**」「⚠ **纪律**：本页只登记**改不了的**。能当场改的一律**当场改掉**」 |
| 实测 | `docs/BROKEN-LINKS.md` 自己的 mtime/提交 = **2026-10-10**；此后 `docs/` 新增了至少 4 份 md（`research/ks-fixes/*` 3 份、`uniformity/*`、`research/archify/*` 3 份） |

**冲突点**：这份文件的**唯一功能**是「登记改不了的断链」，而它当前内容是「0 处」—— 即**它此刻没有任何登记项**，只剩「历史留痕」价值（§二 已修表、§三 误报表）。
**它还算不算真源**：算，但**它的「0 处」不能当「现在也 0 处」用** —— 这个读数带时点（2026-10-10 17:3x），而任务书给的外部实测是「断链 0 处（382 md / 660 链接 / 22 处跳过）」，**那份读数覆盖 382 份 md（全仓），比本文件的 docs 口径宽**。两处都是 0，但**口径不同**（docs 214 份 vs 全仓 382 份），而两份文档都没写清这个口径差。

### 第 9 组：三份文档都自称「接手先读这一份」（已更正，但痕迹散在三处）

| 文件 | 原文（逐字） | 日期 |
|---|---|---|
| `docs/ENCYCLOPEDIA.md` L10 | 「**本文件与 `docs/wiki/` 都曾自称"接手先读这一份"** ⇒ 新人拿到两个"第一步"，**这是重叠**。」 | 2026-10-11 |
| `docs/ENCYCLOPEDIA.md` L15 | 「\| **这个项目要做什么、现在做到哪、主要部件有哪些** \| **[`wiki/architecture.md`](../wiki/architecture.md)** ← **接手先读这一份** \| 一页（~145 行） \|」 | 同上 |
| `README.md`（根）L134/L138 | 「- **接手先读哪一份** ⇒ **[`docs/wiki/architecture.md`](docs/wiki/architecture.md)**」/「⚠ **它不是入口**（2026-10-10 更正）：本行原先写「接手先读哪一份 ⇒ ENCYCLOPEDIA」」 | 2026-10-17 |
| `docs/README.md` L13 | 「> 想知道**项目目标与现状**，看 [wiki/architecture.md](../wiki/architecture.md)。」 | 2026-10-17 |
| `docs/README.md` L49 | 「\| **`docs/HANDOVER-2026-10-09.md`** \| **最新交接文档**——**接手主体项目先读这一份**…」 | 2026-10-17 |

**这一组是「已解决但仍读得出矛盾」**：ENCYCLOPEDIA 与 wiki 的分工在 2026-10-10 已定案（wiki = 入口，ENCYCLOPEDIA = 查事实），**三处都留了更正痕迹**（这是本仓「打回的说法就地更正、不许悄悄删」原则的正确执行）。
**但 `docs/README.md` L49 又把 `HANDOVER-2026-10-09.md` 标成「接手主体项目先读这一份」** ⇒ **入口仍然有两个**（`wiki/architecture.md` 与 `HANDOVER-2026-10-09.md`），而且后者是**2026-10-09 的时点快照**（正文自写「下表是 2026-10-09 快照」），带 8,983/663,634 那组会继续过期的数。**这不是措辞不一致，是「谁是第一步」这个问题至今没答完。**

### 附：第 10 组（编号体系层面的硬冲突）—— `R` 编号有两套互不相干的命名空间

| 出处 | 原文（逐字） |
|---|---|
| `docs/REQUIREMENTS-v4.3.md` L419 | 「### R6 接入 Win11 独立客户端」 |
| `docs/REQUIREMENTS-v4.3.md` L434 | 「### R7 溯源核对与原页黄框高亮」 |
| `docs/CHANNEL-COVERAGE-PLAN.md` L248 | 「\| **R6** \| **五类监控打通** + 巡检读台账选链 + 文档/验收 …\|」 |
| `docs/CHANNEL-COVERAGE-PLAN.md` L2312 | 「### R7（2026-09-19 完成）：**号段**字段——把「号段→渠道」从代码搬进台账」 |

**同一个 `R6` / `R7` 在两份文件里指四件不同的事**：REQUIREMENTS 的 R6 = Win11 客户端、R7 = 原页黄框高亮；CHANNEL-COVERAGE 的 R6 = 五类监控打通、R7 = 号段字段。
REQUIREMENTS 是「需求编号权威出处」（`docs/README.md` L45 逐字写「**要查某个 R 编号的原文，来这一份**」），CHANNEL-COVERAGE 的 R 编号是**它自己的轮次号**（R1–R20）。
**能引对，但只能靠上下文猜**：`docs/NEXT-DEV-PLAN-2026-09-28.md` L542 写「+ [渠道线 R20](../CHANNEL-COVERAGE-PLAN.md)」—— 加了「渠道线」三个字才不歧义；而 `docs/KB-FOLDER-PLAN.md` L793 写「按 **R30** 降级路径如实跳过」，R30 在 REQUIREMENTS 里是「检索故障降级」（对上了），但**同一句话里没有任何「哪套编号」的标记**。
**这一组的性质是「命名空间未登记」**：`docs/naming-convention.md` 是命名规范的唯一归属层，但它**只管文件名/目录名，不管编号前缀**（全文没有「R 编号」的规则）。`specs/` 目录名有 `001`~`013` 的编号，`REQUIREMENTS` 有 `R1`~`R79`，`CHANNEL-COVERAGE` 有 `R1`~`R20`，`T` 编号同时出现在 REQUIREMENTS（`T00~T13`）和 spec `tasks.md`（`T001`…）—— **四套编号，零处登记它们的关系**。

---

## 四、specs 15 个状态表 + 编号冲突核实

### 4.1 状态表

`tasks.md` 计数口径：只数**行首的列表项**（`^\s*-\s*\[[xX ]\]` 或 `[—]`），因为 `002`/`005` 的正文里会**引用** `[x]` 这个词（如「`[x]` = 已完成且可核」），全文正则匹配会把图例也算成任务（实测 `002` 全文匹配 48 个 `[x]`，行首只有 34 个）。

| spec 目录 | 功能名（spec.md 标题） | spec.md 状态 | plan.md | `[x]` | `[ ]` | `[—]` | 合计 | 完成率 | 最后更新 |
|---|---|---|---|---|---|---|---|---|---|
| `001-project-consolidation` | 项目整理与接手文档体系 | **Draft** | 有（6.8 KB） | 40 | 0 | 1 | 41 | **97.6%** | 2026-10-11 |
| `002-recall-funnel` | 召回漏斗诊断与第一轮改进 | **Draft** | 有（11.5 KB） | 34 | 0 | 2 | 36 | **94.4%** | 2026-10-09 |
| `003-vec-scope-pushdown` | 按目录范围提问时，向量通道要真的在范围内找 | **Draft** | 有（6.9 KB） | 31 | 0 | 0 | 31 | **100%** | 2026-10-10 |
| `004-govqa-operationalization` | 政务问答采集系统的可运维化 | **Draft** | 有（8.9 KB） | 53 | 0 | 4 | 57 | **93.0%** | 2026-10-10 |
| `005-govqa-conformance` | gov-qa 合规收口与目标达成 | **Draft** | 有（6.9 KB） | 67 | 0 | 5 | 72 | **93.1%** | 2026-10-12 |
| `006-law-catalog-refresh` | 法规目录补齐与定时刷新 + 历次版本链 | **Closed**（2026-10-10，含收口轮） | 有（11.2 KB） | 25 | 0 | 0 | 25 | **100%** | 2026-10-10 |
| `007-ui-polish` | UI 精修 —— 真机逐面审查后的缺陷收口 | **Draft** | 有（5.6 KB） | 14 | 0 | 0 | 14 | **100%** | 2026-10-10 |
| `008-icon-system` | UI 图标体系与视觉规范收口 | **Draft** | 有（5.6 KB） | 12 | 0 | 0 | 12 | **100%** | 2026-10-10 |
| `009-standard-no-ocr-suffix` | 标准号「(OCR采集)」显示污染清理 | **Draft** | 有（7.1 KB） | 13 | 0 | 0 | 13 | **100%** | 2026-10-12 |
| `009-turn-evidence-ui` | 「本轮依据」三处界面改动 | **Draft** | 有（5.2 KB） | 13 | 0 | 0 | 13 | **100%** | 2026-10-12 |
| `010-real-question-ruler` | 真人问答评测尺子（召回线） | **Draft** | 有（6.6 KB） | 14 | 0 | 0 | 14 | **100%** | 2026-10-12 |
| `010-turn-tab-fixes` | 「本轮」页三处修正（按业主实跑反馈） | **Draft** | 有（6.2 KB） | 19 | **3** | 0 | 22 | **86.4%** | 2026-10-12 |
| `011-channel-system-wiring` | 接上「法规/标准更新通道系统」的三个断点 | **Draft** | 有（7.4 KB） | 13 | 0 | 0 | 13 | **100%** | 2026-10-12 |
| `012-arrow-bbox-root-causes` | 红箭头画不出的五个根因 | **Implemented** | 有（5.9 KB） | 26 | **3** | 0 | 29 | **89.7%** | 2026-10-14 |
| `013-catalog-hidden-retrieval-guard` | 检索路径必须尊重 `catalog_hidden` | **Draft** | 有（3.0 KB） | 11 | **3** | 0 | 14 | **78.6%** | 2026-10-14 |

**plan.md 覆盖**：**15/15 全有**。
**spec.md 状态**：13 份写 `Draft`、1 份 `Closed`（006）、1 份 `Implemented`（012）。**「Draft」在这里不代表没做完**（7 份 100% 完成率也写 Draft）—— 说明**没人回填状态字段**，这个字段目前**不携带信息**。
**未勾的 9 条**（`010-turn-tab-fixes` 3 条、`012` 3 条、`013` 3 条）都写了理由：
- `010-turn-tab-fixes`：「- [ ] **T042** `smoke-all` + `run-gates.ps1 -Full`（**等门禁锁**：本轮被别的门禁占用，退出码 3）」「- [ ] **T043** 小提交 + 快照 + 开发史 §10.236 + UI-BASELINE §5ad」「- [ ] **T044** 派独立复核」
- `012-arrow-bbox-root-causes`：「- [ ] **T027** ⚠ **本 spec 三件套是补建的**（2026-10-14）—— 当时只写了根因报告」
- `013-catalog-hidden-retrieval-guard`：「- [ ] **不删任何文档**（不可逆）。」「- [ ] **不改那 6 篇的隐藏状态**。」「- [ ] **不改 `catalog_hidden` 的写入规则**。」← **这 3 条是「不许做」的边界，被写成 `[ ]` 未勾**，不是欠做。

### 4.2 编号撞号核实 —— **是真的，两组都真**

**核实方法**：`git log --diff-filter=A --reverse --format='%ci %h' -- specs/<dir>/spec.md`，取「spec.md 首次出现的提交时间」。

| 目录 | spec.md 首次提交 | 提交号 | 提交标题 |
|---|---|---|---|
| `009-standard-no-ocr-suffix` | **2026-10-12 10:31:49** | `eeba1dd5` | `feat(spec-009): 标准号「(OCR采集)」来源标记搬到 source 字段（1,430 篇）` |
| `010-real-question-ruler` | **2026-10-12 10:59:10** | `2aa5c15f` | `feat(spec-010): 真人问答召回尺子（500 条）+ 修两个真缺陷` |
| `009-turn-evidence-ui` | **2026-10-12 14:47:42** | `21a4972f` | `feat(UI/spec009): 「本轮依据」三处改动 —— 同文件条款归组 + 删 GB 字样 + 打通红箭头 bbox 链路` |
| `010-turn-tab-fixes` | **2026-10-12 16:35:19** | `6556224a` | `feat(UI/spec010): 「本轮」页三处修正 —— 徽章上移到文件标题 + 页面可滚动 + 红箭头如实降级` |

**⇒ 撞号是真的**：`009-*` 有两个目录，`010-*` 有两个目录。

**为什么撞 —— 三条证据，能定性**：

1. **时间上不是「同时误建」，是「后建的人没查」**。`009-standard-no-ocr-suffix` 建于 10:31，`009-turn-evidence-ui` 建于 14:47（晚 4 小时 16 分），**两者之间已有 010 建好**（10:59）。后建的人（14:47）当时 `specs/` 里已有 `001`~`008` + `009-standard-no-ocr-suffix` + `010-real-question-ruler`，**再建 009 是明显的覆盖**。`010-turn-tab-fixes`（16:35）同理：它建的时候 `010-real-question-ruler` 已在 5.5 小时前建好。
2. **两条线是不同的人/不同的上下文在推**，从提交标题的**前缀约定**就看得出来：
   - 数据/检索线用 `feat(spec-00N)` / `feat(spec-0NN)`（连字符，`spec-009` / `spec-010`）；
   - 界面线用 `feat(UI/spec00N)`（斜杠 + 无连字符，`UI/spec009` / `UI/spec010`）。
   **两套前缀 = 两套编号习惯**，各自从自己的序列里数数，于是撞在一起。
3. **工具本身有防撞机制，但被绕过了**。`.specify/scripts/powershell/create-new-feature.ps1` 里明确有冲突检测：
   - L234：`$specConflict = Test-SpecPrefixInUse -SpecsDir $specsDir -FeatureNum $featureNum`
   - L238–L250：一旦冲突，**自动往上找空号**并打警告 `"[specify] Warning: -Number $requestedNum conflicts with an existing spec directory; using $featureNum instead"`
   - L28 的帮助文本也写着「`-Number N`　Prefer a feature number (**auto-corrected if its specs prefix exists**)」

   ⇒ **撞号只能说明这两个目录不是走这个脚本建的**（或用了 `-AllowExistingBranch`，见 L233 的 `-not $AllowExistingBranch` 分支）。`specs/` 里**没有任何 README 或编号登记表**（`Test-Path specs/README.md` → False），`.specify/feature.json` 只记**当前**一个目录：`{"feature_directory":"specs\\013-catalog-hidden-retrieval-guard"}` —— **不记历史，无法据它发现撞号**。

**撞号的代价（不是形式问题）**：
- `docs/DEVELOPMENT-HISTORY.md` 里「spec 009」指 `009-turn-evidence-ui`（§10.235 标题「「本轮依据」三处界面改动（spec 009）」），而 `docs/PLAN-REAL-QUESTION-RULER.md` 里「spec 009」指 `009-standard-no-ocr-suffix`（「### ✅ 已处置（2026-10-12，spec 009）」+ 链接 `../specs/009-standard-no-ocr-suffix/spec.md`）。**同一句「spec 009」在两份顶层文档里指两个不同的特性。**
- `docs/TEST-FLAKES.md` 写「2026-10-10 我收 spec 009 时踩到」—— 按日期这是 `009-turn-evidence-ui`（10-10 立项），但 `009-standard-no-ocr-suffix` 的 spec.md 是 10-12 才提交，**读的人无法从「spec 009」三个字判断是哪一个**。
- 好在**正文里的链接都写全了目录名**（`../specs/009-standard-no-ocr-suffix/spec.md`），所以**点得进去**；坏在**口语引用（「spec 009」）已经二义**。

---

## 五、scripts 68 个分组与一次性/长期之分

**口径先定死**（三个数不一样，别混）：

| 数 | 值 | 命令 |
|---|---|---|
| `scripts/` **顶层**受 git 跟踪 | **68** | `git ls-files scripts \| Where-Object { ($_ -split '/').Count -eq 2 }` |
| `scripts/` 顶层磁盘实际 | **69** | 多一个**未跟踪**的 `uniformity-ast-dupes.py`（`git status` → `?? scripts/uniformity-ast-dupes.py`） |
| `scripts/` 全部受跟踪（含子目录） | **80** | `git ls-files scripts` |

子目录：`scripts/docs/`（3：`check-links.py` / `gen-doc-index.py` / `scan-rename-targets.py`）、`scripts/loop2/`（4：`driver_v2.py` / `oracle_score.py` / `oracle_snapshot.py` / `vlm_check.py`）、`scripts/verify-seeds/`（4 + README）。

### 5.1 按用途分组（68 个顶层，每组一行一句话）

**A. 门禁与棘轮（长期，5 个）**
- `run-gates.ps1`（63 KB）—— 本仓**唯一**门禁入口，16 处 `Add-Step`，Quick 5 步 / Full 12 步
- `gates-baseline.json` —— 棘轮基线（当前 `pytest_passed: 3057` / `total: 3065`，`updatedAt: 2026-10-18T09:09:51`）
- `gates-tracked-total.py` —— 棘轮**口径**：只统计受版本控制的用例
- `pssa-guard.ps1` —— 命令层空验证的机械检测（PSScriptAnalyzer 单条规则）
- `pssa-guard-selftest.ps1` —— 上面那把尺自己的回归测试（T1/T2/T3 三档）

**B. 快照与引擎门禁（长期，3 个）**
- `snapshot-project.ps1` —— 打可回滚标签 + 可选实体备份
- `verify-engine-uvicorn.py` —— 在**真 uvicorn 下**验引擎（进程内 ASGI 量具覆盖不到的那层）
- `verify-pssa-command-layer.ps1` —— 独立复核：PSScriptAnalyzer 能不能抓到「命令层空验证」

**C. 测量尺（可复跑，11 个 `measure-*.py`）** —— 见 §5.3
`measure-classical-chinese-segmentation` / `measure-cross-language-fts` / `measure-endpoint-blocking` / `measure-material-bridge` / `measure-material-recall` / `measure-prefix-multiword` / `measure-term-aggregation` / `measure-term-bridge` / `measure-term-selection` / `measure-term-victim-side` / `measure-term-window-coverage`

**D. 只读审计与核查（长期可复跑，10 个）**
- `audit-async-endpoints.py` —— 哪些端点声明 `async def` 却在做同步重活
- `audit-hardcoded-paths.py` —— 便携化审计：把「代码里写死」与「文档里历史记录」分开
- `check-fixture-leak.py` —— 生产库卫生：测试夹具不许以「可见文档」身份留在库里
- `verify-answer-citations.py` —— `channel_answers.json` 的行号引用校验哨兵
- `verify-dup-safety.py` —— 重复向量落在哪些条款上、去重是否安全
- `verify-dup-vectors.py` —— 向量表里有多少逐字节相同的重复向量
- `verify_highlight.py` —— 高亮 bbox 离屏验证（底部原点 v5 契约）
- `ks-credential-readers-scan.py` —— 谁还在读那把旧 `DEEPSEEK_API_KEY`
- `ks-credential-reconcile.py` —— 引擎/DSH 凭据对账
- `probe-recall-latency.py` —— 真库规模下三条召回通道的耗时

**E. 一次性数据修复/迁移（18 个）** —— 见 §5.2

**F. 渠道台账与路由报告（6 个）**
- `answers-matrix.py` —— 五类能力矩阵（哪一类由谁答、今天活着吗）
- `chain-snapshot.py` —— 把「今天的链」与「按台账算出来的链」并排打出来
- `channel-anchor-measure.py` —— 给一条渠道量出可直接粘贴的探针目标
- `channel-status-report.py` —— 渠道台账导成人可读 Markdown
- `five-class-order-diff.py` —— 五类**排序**的差异哨兵
- `question-route.py` —— 给定标准号，打印五类各由谁答

**G. 法规/标准数据管道（5 个）**
- `fetch_law.py` —— 官方法规抓取 CLI（`LAW-SOURCE-PLAN` P1/P3）
- `std_status_check.py` —— 国标存量状态体检（openstd 主渠道）
- `std_status_import.py` —— 体检结果回流知识库
- `std_status_report.py` —— 体检结果汇总导出
- `_stdparse.py` —— **共享模块**：文件名 → 标准号/名称提取（被 G 组几个脚本复用）

**H. DSH 宿主 / 记忆（8 个）**
- `dsh-docs-delta.ps1` —— DSH 升级后列出要重新对齐的文档/契约（只读报告）
- `dsh-gui-e2e-ingest.ps1` —— 无头浏览器端到端验收「📥 入库预览」tab
- `dsh-host-restart.ps1` —— 带自愈的 dsh web 宿主重启
- `dsh-host-watchdog.ps1` —— 自主开发期间的宿主看门狗
- `dsh-session-dump.mjs` —— 读 DSH 会话日志（多帧 zstd）+ 活跃度判据
- `hindsight-reflect.mjs` —— 宽问题版 reflect，直连 Hindsight API
- `ingest-dsh-docs-into-memory.mjs` —— 把 DSH 官方文档逐字节灌进记忆库
- `update-dsh-navigation-entry.mjs` —— 更新 Hindsight 里 `dsh` 那条导航件

**I. 交接与辅助（3 个）**
- `make_handoff_zip.py` —— 生成交接包（源码+文档+测试+库快照）
- `pick-domain-terms.py` —— 从知识库机械抽「跨领域专业术语」清单
- `map-dsh-icons.py` + `fix-dsh-icon-names.py` —— 图标名映射与其批量替换（**唯一两个在 `scripts/` 外零引用的脚本**）

**J. 知识库归位（2 个，刻意成对）**
- `preview-folder-filing.py` —— 归位预览（**只读真库，绝不写入**）
- `apply-folder-filing.py`（75 KB，全目录第二大）—— 对真库落库

### 5.2 哪些是「一次性的」？—— **18 个**，名单如下（可原样复跑核对）

判据：名字是 `fix-*` / `fix_*` / `repair*` / `migrate*` / `backfill*` / `apply*` / `normalize*` / `rebuild*` / `convert*` / `ingest-*` / `restore*` 这类**动作已完成即无对象**的，或 docstring 自写「一次性」的。

| # | 脚本 | 依据（可搜索文字） |
|---|---|---|
| 1 | `fix_standard_name_suffix.py` | docstring：「**一次性维护**：清理 `doc_meta.standard_name` 结尾的**副本后缀**（`…(1)`）」 |
| 2 | `fix-standard-no-ocr-suffix.py` | docstring：「**一次性维护**：把 `doc_meta.standard_no` 尾部的「(OCR采集)」来源标记**搬**到 `source` 字段」 |
| 3 | `fix-dsh-icon-names.py` | 「把 `plugin/client/*.tsx` 里的旧图标名**批量替换**成新版 DSH 的 OutlineRegular 名」 |
| 4 | `repair_patch_watermarks.py` | 「修复：`clause_patch` 里被 `pypdf_backfill` 越界抽取污染的水印/页眉」（生产库实测 19,981 条中 14,906 条，修完即无对象） |
| 5 | `repair-missing-standard-no.py` | 「R6c-2e：修**号里没有数字**的坏行（从 `file_path` 的文件名推导真号）」 |
| 6 | `migrate-clause-vec-doc-id.py` | 「spec 003 · 迁移：给真库 `clause_vec` 加 `doc_id` 元数据列（**纯搬运，不重算向量**）」 |
| 7 | `ks-credentials-migrate.py` | 「把 API 密钥从 **Windows 系统层**搬进引擎自己的加密存储」 |
| 8 | `backfill-bbox-units.py` | 「回填 MinerU 4.0 那批的**坏 bbox**（spec 012 R2）」+「R1 修的是…那只对**以后**入库的生效」 |
| 9 | `normalize-standard-no-slash.py` | 「把库内**存量**全角斜杠归一」—— 针对**存量**，存量归完就完 |
| 10 | `apply-folder-filing.py` | 「对真库执行归位（KB-FOLDER-PLAN §五第 1 步的『落库』那一半）」 |
| 11 | `rebuild-reference-edges.py` | 「引用边批量重算（诊断 + 修复）—— 2026-10-09 真缺陷的批量修法」 |
| 12 | `convert-library-to-text.py` | 「把下载的论文/教材转成文本再入库 —— 绕过仓里那条抽不出文字的 PDF 路径」 |
| 13 | `ingest-library-text.py` | 「把『转换好的文献纯文本』入『参考资料』平面」 |
| 14 | `ingest-rag-study-materials.py` | 「『全部导入』：把学习材料…**一次性**入『参考资料』平面」（docstring 逐字写「一次性」） |
| 15 | `ks-credential-readers-scan.py` | 「凭据读者排查（整改批 1b）」—— 排查一次即出结论 |
| 16 | `ks-credential-reconcile.py` | 「引擎/DSH 凭据对账（整改批 2c）」—— 同上 |
| 17 | `std_bulk_import.py` | 「国标批量入库 v2（**覆盖式**）」—— 首灌用，之后走正常入库 |
| 18 | `restore_package.py` | 「数据包离线恢复 CLI」—— 只在灾备时用，**平时无对象**（但**必须留着**，见下） |

**它们该留在 `scripts/` 还是进 `archive/`？—— 结论：18 个里 9 个必须留，9 个可议。**

**必须留（9 个）—— 因为它们被 pytest 钉住，删了测试就红**（判据：`git grep -l <name> -- tests/`）：

| 脚本 | 钉它的测试 |
|---|---|
| `apply-folder-filing.py` | `test_apply_folder_filing.py`、`test_filing_state_pipeline.py` |
| `fix_standard_name_suffix.py` | `test_store_standard_no.py` |
| `normalize-standard-no-slash.py` | `test_normalize_std_slash.py`、`test_store_standard_no.py` |
| `repair_patch_watermarks.py` | `test_watermark_own_standard.py` |
| `ks-credentials-migrate.py` | `test_credentials_migrate_script.py`、`test_credentials_namespace.py` |
| `ks-credential-reconcile.py` | `test_credential_reconcile.py`、`test_credentials_namespace.py` |
| `ks-credential-readers-scan.py` | `test_credential_readers_scan.py`、`test_credentials_namespace.py` |
| `std_bulk_import.py` | `test_credentials_namespace.py`、`test_scnet_readchain.py` |
| `restore_package.py` | `test_update_package.py` |

这些测试的引用方式都是**按路径动态加载**（例：`tests/test_normalize_std_slash.py` L23 `SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize-standard-no-slash.py"`；L28 `spec_from_file_location("_normalize_slash", SCRIPT)`）—— **脚本一挪，测试当场崩**。所以它们**不是「跑过一次就没用」，而是「跑过一次之后成了被测试覆盖的回归工具」**，`archive/` 装不了。

**可议（9 个）**：`fix-dsh-icon-names.py`、`fix-standard-no-ocr-suffix.py`、`migrate-clause-vec-doc-id.py`、`backfill-bbox-units.py`、`rebuild-reference-edges.py`、`convert-library-to-text.py`、`ingest-library-text.py`、`ingest-rag-study-materials.py`、`map-dsh-icons.py`。
它们**无测试、无门禁引用**，但：
- `migrate-clause-vec-doc-id.py` / `backfill-bbox-units.py` / `fix-standard-no-ocr-suffix.py` **是「对真库做过一次改动」的唯一可复算凭据** —— 开发史里大量「读数出自哪个脚本」的引用指向它们，挪走会断链（`docs/BROKEN-LINKS.md` 的规矩是「能改就改」，挪走就制造断链）。
- `map-dsh-icons.py` + `fix-dsh-icon-names.py` 是**唯一在 `scripts/` 之外零引用的一对**（`git grep -l` 对全仓、除 `scripts/` 外，两个都 0 命中）。

⇒ **建议（不是本次要做的）**：`scripts/` 里**按「被测试/门禁引用」与「仅历史凭据」分两层**比按 `archive/` 分更合适 —— 因为 `archive/README.md` §四 明写「归档件不可逆地回到『当前真源』」，而这些脚本随时可能被再次运行（真库再坏一次就要用）。**当前状态的问题不是「一次性脚本没归档」，是「一次性脚本与长期脚本混在同一层，看不出哪个能安全跑」。**

### 5.3 `measure-*.py` 11 个：测完结论存在哪？还能复跑吗？

**测完结论存在哪 —— 存在 `docs/` 的散文里，不是存在机器可读文件里。**
实测：11 个脚本里 **10 个 `json.dump` / 写文件 = 0**（只有 `measure-endpoint-blocking.py` 有 1 处写）。也就是说**尺子本身不落盘**，读数被手抄进文档。落点（`git grep -l <script>.py -- docs/ eval/`）：

| 脚本 | 结论落在哪（实测命中） |
|---|---|
| `measure-classical-chinese-segmentation.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/NEXT-DEV-PLAN-2026-09-28.md`、`docs/research/classical-chinese-segmentation-evidence.md`、`docs/research/cross-language-retrieval-evidence.md`、`docs/verify-briefs/VERIFY-REPORT-p32-classical-seg.md` |
| `measure-cross-language-fts.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/research/cross-language-retrieval-evidence.md` |
| `measure-endpoint-blocking.py` | `docs/CHANNEL-COVERAGE-PLAN.md`、`docs/MATERIALS-PLANE-PLAN.md`、`docs/archive/history/rounds-10.1-10.203.md` |
| `measure-material-bridge.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |
| `measure-material-recall.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |
| `measure-prefix-multiword.py` | `docs/research/cross-language-retrieval-evidence.md` |
| `measure-term-aggregation.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/research/lay-gap-decomposition.md` |
| `measure-term-bridge.py` | `docs/DEVELOPMENT-HISTORY.md`、`docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/research/lay-gap-decomposition.md`、`docs/verify-briefs/VERIFY-REPORT-exp17-prod-plan.md`、`eval/lay-phrasing/probe-*.py` ×3、`eval/recall-funnel/exp-17/README.md`、`eval/recall-funnel/exp-3-query-side/README.md` |
| `measure-term-selection.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md`、`docs/research/DECISION-TABLE-2026-09-28.md`、`FINDINGS-INBOX-2026-09-28.md`、`REVIEW-PLAN-A/B`、`TECH-PATH-2026-09-28.md`、`lay-gap-decomposition.md` |
| `measure-term-victim-side.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |
| `measure-term-window-coverage.py` | `docs/RETRIEVAL-LONG-RANGE-PLAN.md` |

⇒ **10/11 的结论落在 `docs/RETRIEVAL-LONG-RANGE-PLAN.md` 这一份里**（一份 168 KB 的散文台账）。这是本仓「一个事实一个归属层」的执行结果，代价是**要复算一个数，得在 1500 行里找那句读数**。

**还能复跑吗 —— 分三档，只有 4 个有闸门**：

| 档 | 脚本 | 依据 |
|---|---|---|
| **有测试钉住尺子本身**（4 个） | `measure-endpoint-blocking.py` | `tests/test_measure_harness.py` docstring 逐字：「**量具自己的闸门**：`scripts/measure-endpoint-blocking.py` 必须真的分得开「把事件循环堵住了」与「没堵」」 |
| | `measure-classical-chinese-segmentation.py` | `tests/test_classical_segmentation_ruler.py` |
| | `measure-cross-language-fts.py` | `tests/test_fts_latin_prefix.py` |
| | `measure-term-bridge.py` | `tests/test_term_bridge.py` |
| **无测试，但读只读库、可跑** | `measure-material-bridge` / `measure-material-recall` / `measure-prefix-multiword` / `measure-term-aggregation` / `measure-term-selection` / `measure-term-victim-side` / `measure-term-window-coverage` | 都是「只读打开生产库」型；`measure-term-victim-side` docstring 还写了依赖前置产物「`var/tmp/term-index-keepall.json`；没有就先跑…」 |
| **依赖本机临时产物，可能已不可复跑** | `measure-term-selection.py` | docstring：「`var/tmp/term-index-full.json`），没有就现场重建（约…）」—— **`var/` 不受版本控制**（`docs/README.md` §1.4），换机就没了 |

**一条具体的「测完没落盘」实例**（`docs/PLAN-REAL-QUESTION-RULER.md` 自述，属同族问题）：
> 「⚠ 实施中发现并修掉一个**真缺陷**：官方工具 `measure-locate-rate.py` 用 `read_text().splitlines()` 读 jsonl，而数据的 JSON 值里含 `U+2028` ⇒ 记录被从中间切开、**被静默丢掉**（实测 7 个源 40 处）⇒ 可用考卷 **28,597 → 28,601**。」

⇒ **尺子本身会静默错，而错的读数已经写进文档了**。这条被留痕并改正（原数不删），是正确做法；但它说明「`measure-*.py` 结论只在散文里」这个模式的风险：**尺子坏了，文档里的数是假的，而且没人能自动发现**。`tests/test_measure_harness.py` 的抬头就是为这条而写：「**量具没有闸门的话**，它坏掉的那天…所有『改后掉回噪声底』都会变成**假绿**」。

### 5.4 68 个里有没有功能重复？—— 有，三组硬的

**重复组 1：标准号规范化/清理 —— 6 个脚本 + 1 个真源，其中 2 个自建前缀表**

真源是 `src/core/text_utils.py`：`def canon_standard_no(s: str | None) -> str:`（L1280）、`def store_standard_name(value: str | None) -> str:`（L1330）。

| 脚本 | 是否复用真源 | 证据 |
|---|---|---|
| `fix_standard_name_suffix.py` | ✅ 复用 | L37 `from src.core.text_utils import strip_duplicate_suffix` |
| `fix-standard-no-ocr-suffix.py` | ✅ 复用 | L55 `from src.core.text_utils import strip_ocr_source_suffix` |
| `normalize-standard-no-slash.py` | ❌ 自己干 | 只 `from src.core.config import get_settings`（L52），斜杠替换自己写；docstring 自写「只改**字符形状**：`／`→`/`」 |
| `repair-missing-standard-no.py` | ❌ **自建前缀白名单** | L49 `HEAD = ("GB", "GB/T", "GB/Z", "GBZ", "GBZ/T", "GBT", …)`，注释自写「与 `var/ocr-loop/ingest_from_manifest.py::split_std` **同源**」 |
| `std_status_check.py` | ❌ **自建提取函数** | L70 `def extract_standard_no(filename: str) -> str | None:` |
| `_stdparse.py` | ⚠ 半复用 | L9「与 std_bulk_import.py 一致；兼容全角斜杠 ／、GB/GBZ」；L20「现统一走 `text_utils.clean_standard_name`」—— **同一个文件里两套说法** |

⇒ **「标准号怎么算」这件事，在 `src/core/text_utils.py` 有一份真源，`scripts/` 里另有 2 套独立实现（`repair-missing-standard-no.py` 的前缀表、`std_status_check.py` 的提取函数），外加 1 个共享模块 `_stdparse.py` 在「自建」与「复用」之间摇摆。** 这正是 `repair-missing-standard-no.py` 自己记录的那个 bug 的成因：docstring L4「`var/ocr-loop/ingest_from_manifest.py` 的 `split_std` 前缀表**漏了 `GBZ／T`**，于是…`standard_no` 被压成**裸 `GBZ／T`**」—— **同一件事多份实现，漏一处就产生坏数据**。

**重复组 2：图标名映射 —— 2 个脚本做同一件事**
- `map-dsh-icons.py`：「把本仓 tsx 里引用的 Icon* 逐个映射到新版 DSH ui-primitives 的真实导出」
- `fix-dsh-icon-names.py`：「把 `plugin/client/*.tsx` 里的旧图标名批量替换成新版…**规则来自 scripts/map-dsh-icons.py 的实测映射**」
⇒ 这是**刻意的两段式**（先测映射、再批量替换），不算冗余；但**两个都在 `scripts/` 之外零引用**（`git grep -l` 除 `scripts/` 外 0 命中），且 `fix-` 那个是标准的一次性脚本。**它们唯一的价值是「当时怎么映射的」留痕。**

**重复组 3：渠道/五类台账报告 —— 6 个脚本都在读同一张台账出不同视图**
`answers-matrix.py`（五类能力矩阵）、`chain-snapshot.py`（链快照）、`channel-status-report.py`（台账 Markdown）、`channel-anchor-measure.py`（探针目标）、`five-class-order-diff.py`（排序差异哨兵）、`question-route.py`（单号路由）。
6 个的 docstring **全部**引用同一个编号 `§11.0 R6c`（例：`answers-matrix.py`「五类能力矩阵（§11.0 R6c）」、`chain-snapshot.py`「链快照（§11.0 R6c 第一步）」、`question-route.py`「按问题选渠道（§11.0 R6c-3）」）。
⇒ **不是功能重复，是同一节需求拆出的 6 个视图**。但它们**共用一个数据源（`update_channel` 表 + `channel_answers.json`）却各写一份取数代码** —— 与「一个事实一个归属层」不一致。`docs/CHANNEL-COVERAGE-PLAN.md` 里「131 / 280 / 286」三个数对不上（§三 第 3 组），**很可能就是这个结构的下游症状**：6 个脚本各算各的。

**没有重复的组**（确认一下，免得看着像漏查）：`std_status_check` → `std_status_import` → `std_status_report` 是**三段流水线**（体检 → 回流 → 导出），不是重复；`preview-folder-filing` + `apply-folder-filing` 是**只读预览 + 写入落库**的刻意成对（后者的 docstring 逐字写「姊妹脚本 `scripts/preview-folder-filing.py` 是**只读预览**」）。

---

## 六、文档体系的整体问题（5 条，每条带证据）

### 问题 1：**「唯一真源」这个说法被用了 15 次，但没有任何机制保证它同步**

证据：29 份顶层文档里 15 份自称「唯一真源/唯一归属层/唯一权威」（§一 的表格）。规矩写在 `docs/README.md` §二：「**一个事实一个归属层**：同一件事**只在它归属的那一份里写全文**，别处只链接。」
但实测的反面：
- **表数量**：4 个不同的数（34/38/60/62），实测 44，**没有一份跟着 schema 改**（§三 第 1 组）。
- **语料规模**：2 个不同的数，纠正的那句藏在一份 19 KB 的交接文档正文里，而**接手第一站 `wiki/architecture.md` 拿的是旧数**（§三 第 2 组）。
- **渠道台账**：3 个不同的数（131/280/286），其中 `GOVQA-UNWIRED-CHANNELS.md` **自己内部** `wired` 就写了 13，而种子文件写 7（§三 第 3 组）。
- **子系统数**：19/18/16，且**最新那处（`docs/README.md`，2026-10-17）自身算术不对**（说 19、列 18）（§三 第 4 组）。

⇒ **「一个事实一个归属层」管住了「写在哪」，没管住「改了要回去改」。** 没有任何门禁检查「文档里的数 = 代码里的数」——`run-gates.ps1` 的 16 个 `Add-Step` 里**没有一条**是文档数字校验（我逐条看过 `Add-Step` 列表：tsc / mypy / verify:commands / pssa-guard / smoke / pytest / verify-engine-uvicorn / verify-tools-real / e2e / gov-qa 三项）。

### 问题 2：**入口有三个，而且「第一步」指向的那份带的是最旧的数**

证据：
- `README.md`（根）L134：「接手先读哪一份 ⇒ `docs/wiki/architecture.md`」
- `docs/README.md` L49：「`docs/HANDOVER-2026-10-09.md` \| **最新交接文档**——**接手主体项目先读这一份**」
- `docs/ENCYCLOPEDIA.md` L15：表格里「← **接手先读这一份**」指向 `wiki/architecture.md`

其中 `wiki/architecture.md` 的数字是 **6,797 / 522,021**，而 `HANDOVER` 同一件事写 **8,983 / 663,634** 并明写前者「已过时」。**新人照 `README.md` 的指引读 wiki，先拿到的是过时数；照 `docs/README.md` 的指引读 HANDOVER，拿到的是会继续过期的 2026-10-09 快照。**
`ENCYCLOPEDIA` L10 自己把这件事记成了「这是重叠」，但 2026-10-10 的更正**只解决了 wiki vs ENCYCLOPEDIA，没解决 wiki vs HANDOVER**。

### 问题 3：**`docs/` 里有一套「自己生成的索引」，但它不覆盖自己、且落后 4~7 份**

证据：`docs/INDEX.md` L4「共 **210 份** / **7338 KB**」；磁盘 **214 份**（现在 217）；机械 diff 出**缺 4 份**（`INDEX.md` 自己 + `research/ks-fixes/` 3 份，后者未跟踪、mtime 2026-10-21 晚于 INDEX 的 2026-10-19）。
`docs/README.md` §四 立规矩「`docs/INDEX.md` 是**机械生成**的…**不要手改**」，但 `git status` 显示 ` M docs/INDEX.md` —— **改没改过，从仓库里判断不出来**。
⇒ 一份自称「机械、可重跑」的索引，**没有进任何门禁**（`run-gates.ps1` 里没有 `gen-doc-index.py`；它只在 `scripts/docs/` 躺着，靠人记得跑）。这就是它落后的原因。

### 问题 4：**编号体系有 4 套并存，零处登记它们的关系，已经撞出两组同号目录**

证据：
- 4 套编号：`REQUIREMENTS-v4.3.md` 的 `R1~R79 + R-L1~R14 + T00~T13`（94 个 `### R…` 标题）；`CHANNEL-COVERAGE-PLAN.md` 自己的 `R1~R20`；`specs/` 的 `001~013`；各 `tasks.md` 的 `T001~T07x`。
- **同号不同义**：`R6` 在 REQUIREMENTS = 「接入 Win11 独立客户端」，在 CHANNEL-COVERAGE = 「五类监控打通」；`R7` 分别是「溯源核对与原页黄框高亮」与「号段字段」（§三 附组）。
- **同号不同目录**：`009-standard-no-ocr-suffix` / `009-turn-evidence-ui`；`010-real-question-ruler` / `010-turn-tab-fixes`，**两组都真撞**（§四 4.2，有四个首次提交时间）。
- **登记处为零**：`specs/` 没有 README（`Test-Path specs/README.md` → False）；`.specify/feature.json` 只记当前一个目录；`docs/naming-convention.md` 全文没有「编号前缀」规则。
- **工具本来能防**：`.specify/scripts/powershell/create-new-feature.ps1` L238–L250 有自动避开已用编号的逻辑，L28 帮助文本写「auto-corrected if its specs prefix exists」—— **撞号说明这两个目录没走这个脚本**。

### 问题 5：**「一次性脚本」与「长期脚本」混在同一层，唯一能区分它们的信号是「有没有被 pytest 按路径钉住」**

证据：68 个顶层脚本里 **18 个是一次性**（§5.2 名单），其中 **9 个被测试按路径钉住**（`Path(__file__).resolve().parents[1] / "scripts" / "xxx.py"` + `spec_from_file_location`），**9 个无测试无门禁引用**。
这意味着：
- **不能整体搬进 `docs/archive/`** —— `archive/README.md` §四 明写「归档件不可逆地回到『当前真源』」，而 `restore_package.py`（灾备恢复）必须随时可跑。
- **也没法从文件名判断** —— `restore_package.py` 听着像一次性，实际是**灾备工具**；`apply-folder-filing.py` 听着像长期，实际是**一次性落库**（已被 `test_apply_folder_filing.py` 覆盖）。
- **唯一可用的判据是「有没有测试钉住」**，而这个事实**没有任何文档登记**（`docs/README.md` L29 对 `scripts/` 的描述只有一句：「工具脚本：门禁 `run-gates.ps1`、快照 `snapshot-project.ps1`、文档工具 `docs/`」—— **68 个脚本只提了 2 个**）。

---

## 七、我没搞清楚的

1. **真库当前的真实规模**（`doc_meta` 篇数 / `clause_revision` 条数 / 表数量）—— **未读，原因：本任务禁跑门禁与 pytest，且真库在 `%APPDATA%\KnowledgeStation\database\knowledge.db`，我没有只读打开它**。所以 §三 第 1/2 组我只能判「文档之间谁新谁旧」，**不能判「谁对」**。若要定论，需一条只读 `SELECT COUNT(*)`。
2. **`EXTERNAL-REVIEW-ARCHITECTURE-v4.md` 为什么未跟踪** —— **未查清**。`docs/README.md` 标它「受版本控制 ✅」，`.gitignore` 里也没有它（我没找到匹配项），但 `git ls-files` 就是空。可能是「建了文件但忘了 `git add`」，也可能是「刻意不入库（要发给外部，不想进历史）」，两种解释**都没有证据**。
3. **`docs/research/` 里 97 份中「哪几份结论仍有效」的准确名单** —— 我只做到「94 份被引用、3 份零引用」。**「被引用」≠「仍有效」**：一份 2026-09-28 的调研被开发史引用，可能只是因为「当时的判断记录在案」。要判有效性得逐份读，**没读**（97 份里我只读了约 15 份的抬头）。
4. **`archive/old-baselines/` 为什么是空的** —— README 里有这个类别（「过期基线快照（旧 UI 基线、旧规模数字）」），但目录里 0 个文件。是「从来没有过」，还是「曾经有、被移走/删了」，**没查 git 历史**。
5. **`scripts/` 里 6 个渠道报告脚本（`answers-matrix` / `chain-snapshot` / `channel-status-report` / `channel-anchor-measure` / `five-class-order-diff` / `question-route`）各自算出的数是否一致** —— **未跑**（禁跑）。所以 §三 第 3 组的「131 / 280 / 286」我只能报「文档与种子文件对不上」，**不能证明是哪个脚本算错**。
6. **`specs/012-arrow-bbox-root-causes` 标 `Implemented` 但完成率 89.7%（3 条未勾）** —— 那 3 条里 1 条是「本 spec 三件套是补建的」，另外 2 条是「`GB 1886.368-2023` 的 50 条：MinerU 产物不在盘上」「7 条分散在 7 篇：匹配不上」。**这些是「做不了」还是「还没做」，我没读 plan.md 判**。
7. **`013-catalog-hidden-retrieval-guard` 那 3 条 `[ ]` 是「边界声明」还是「欠做」** —— 文字看着像边界（「**不删任何文档**（不可逆）」「**不改那 6 篇的隐藏状态**」），但格式是 `- [ ]`，**按 `tasks.md` 的图例会被读成「未完成」**。这是**格式与语义打架**，我判不了作者意图。

---

**调查边界声明**：本文只读文件、只用 `Get-ChildItem` / `git log` / `git grep` / `Select-String` / `Get-Content`。**没有修改任何已有文件**（唯一的写操作是新建本文件）。**没有跑门禁、没有跑 pytest、没有跑 `snapshot-project.ps1`**。凡是「实测」都是命令输出；凡是「文档之间谁新谁旧」都以 `git log -1 --format=%cs` 为准；凡是我判不了的，写在 §七 并注明原因。
