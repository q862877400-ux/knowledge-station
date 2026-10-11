# KnowledgeStation 文件地图

**这是什么**：仓库里**每一样东西在哪、用来干什么**。
**给谁看**：接手的 agent 与人。**读完这一页，你就知道该去哪找。**

> **与根 `README.md` 的分工（两处不许都写全文）** ✅ **2026-10-05 已归并**：
> 根 `README.md` 是**仓库入口**——项目是什么、怎么跑、**动之前勿删什么**、剩下的去哪读；
> **本文件是文件地图**——每一样东西在哪、干什么。
> 原来根 README 的「目录结构 / 文档地图」两节已并入本文件；**安全警告（勿删清单）留在根**，
> 因为那是人最先看的地方，**不该藏进二级文档**。
> **⇒ 从现在起：地图只住本文件，入口只住根 README。加内容时别加错地方。**

> 想知道**项目目标与现状**，看 [wiki/architecture.md](wiki/architecture.md)。
> 想知道**历史在哪**，看 [archive/README.md](archive/README.md)。
> 想知道**某个功能由哪块代码负责**，看 [wiki/components/](wiki/components/)。

---

## 一、顶层：仓库里有什么

### 1.1 代码

| 位置 | 是什么 | 受版本控制 |
|---|---|---|
| `src/core/` | **Python 引擎**，19 个子系统：`api`（HTTP 端点）/ `ingestion`（解析入库）/ `knowledge`（法规知识）/ `retrieval`（检索）/ `storage`（sqlite 存取）/ `update`（渠道巡检）/ `materials`（材料平面）/ `llm` / `exports` / `quality` / `verification` / `settings` / `compliance` / `domain` / `vision` / `query` / `law_source` / `update/channels` | ✅ |
| `plugin/` | **DSH 插件**（Node）：宿主桥 + 侧栏 React 界面 + 对 agent 暴露的 4 个工具 | ✅ |
| **`tools/`** | **独立工具与数据集**（**仓里最大的组件**）。目前只有一族：**`tools/gov-qa/`** —— 政务问答采集（347 通道 / 40,943 条 / **已进本仓门禁**）。**它是另一条线**，入口见 [`tools/gov-qa/README.md`](../tools/gov-qa/README.md)；**可复用资产清单见** [`REUSE-FOR-ANNOUNCEMENTS.md`](../tools/gov-qa/REUSE-FOR-ANNOUNCEMENTS.md) | ✅（数据 634 MB 亦在版本控制） |
| `tests/` | pytest 测试（约 163 个文件）；`tests/fixtures/` 放夹具 | ✅ |
| `scripts/` | 工具脚本：门禁 `run-gates.ps1`、快照 `snapshot-project.ps1`、文档工具 `docs/` | ✅ |

> **⚠ 关于 `tools/`（2026-10-10 补）**：它是**仓里最大的组件**（924 MB / 3,456 文件），
> 但此前**本文件与 `wiki/architecture.md` 都没提过它** —— 接手的人看不到它。
> 它**不属于主引擎**（不改 `src/`、不跑主检索），但**与主项目共用同一批政府站点**，
> 因此有**可直接复用的资产**（中间件指纹 / 可达性矩阵 / 水位三型 / 纯 ASCII 机器接口 /
> 地级市→省映射）。**要拿它的东西之前，先读 `REUSE-FOR-ANNOUNCEMENTS.md` 的「写入边界」节** ——
> 那个目录**由另一条自动化线高频写入**。

### 1.2 文档

| 位置 | 是什么 | 受版本控制 |
|---|---|---|
| **`docs/README.md`** | **本文件**——文件地图 | ✅ |
| **`docs/naming-convention.md`** | **命名与分类规范**（正式件）——文件/目录怎么命名、什么算"历史"该归档。**动任何文件名/目录名前先读它** | ✅ |
| **`docs/BROKEN-LINKS.md`** | **已知断链台账**——`check-links.py` 报了但**改不了**（写入面在别人手里）的断链登记处；含"改不了的为什么改不了 + 归谁 + 复查判据" | ✅ |
| **`docs/REQUIREMENTS-v4.3.md`** | **旧主计划 v4.3（需求 SSOT）**——`R1–R79 + R-L1~R14 + T00~T13` 的**权威出处**。⚠ 2026-09-19 曾被删，2026-10-10 **从 git 原样恢复**；文件自带注记写明哪些条目已作废。**要查某个 R 编号的原文，来这一份** | ✅ |
| `docs/wiki/` | **接手文档**：项目现状 `architecture.md` + 每套组件的职责/接口/依赖/非目标 | ✅ |
| `docs/archive/` | **历史**：旧计划 / 过期基线 / 调研过程 / 已完成复核 / **旧交接**。**索引见它自己的 README**（2026-10-11 扩容：又收了 16 份「已被取代」的） | ✅ |
| **`docs/ENCYCLOPEDIA.md`** | **技术百科全书**（架构 / 数据契约 / 检索 / 入库 / 坑全集 / 红线宪法）——**要查具体技术事实时的唯一权威**。⚠ **不是入口**（2026-10-10 更正：原先标「接手先读这一份」，与 `wiki/architecture.md` 重叠；现入口是 wiki，本文件降为"查事实"） | ✅ |
| **`docs/HANDOVER-2026-10-09.md`** | **最新交接文档**——接手主体项目先读这一份（项目是什么 / 现在在哪 / 下一步 / 禁碰边界 / 自动链说明） | ✅ |
| **`docs/PROJECT-STATE-FOR-EXTERNAL-AI-2026-10-11.md`** | **给外部高级 AI 的项目现状说明**（自包含：目标 / 已实现 / 数据实况 / 卡点 / 资源 / 待决策问题）。**要请外部出主意时，发这一份** | ✅ |
| **`docs/PLAN-REAL-QUESTION-RULER.md`** | **用真人问答造新评测尺子的方案**（三层尺子：召回 / 大白话 / 答对；三个必须先处理的坑；待业主拍板三件）。⚠ **方案，不是施工单** | ✅ |
| **`docs/GOVQA-UNWIRED-CHANNELS.md`** | **未接线渠道清单（273 条）**——给接线的对话用。**自包含**：什么叫「接线」/ 逐条清单 / 接线完成的判据 / 接线前必读 | ✅ |
| **`docs/EXTERNAL-REVIEW-ARCHITECTURE-v2.md`** | **总体架构方案征询（外部评审稿）**——按「外部评审稿」技能写：节 0 名词定义 + 摘要能独立成立 + 内嵌运行时拓扑 + Anti-Scope + 8 个待答问题（含篇幅与优先级）+ 真实样本附录 + 分批交付指引。**v2 已经过 5 路独立对抗审查并逐条回原始数据核实**（改了什么见文末「本次修订改了什么」）。**要请外部专家给架构方案时，发这一份** | ✅ |
| `docs/archive/handovers/` | **旧交接**（2026-09-23 / 10-06）——已被上面那份取代 | ✅ |
| `docs/INTRODUCTION.md` | 产品介绍（是什么 / 为什么可信 / 能力清单） | ✅ |
| `docs/VISION-TREE.md` | 功能愿景（客户视角：每条能力标注「今天点得到吗」） | ✅ |
| `docs/DEVELOPMENT-HISTORY.md` | 开发简史（§一~§九 叙事 + 203 轮索引；逐轮明细已入 `archive/history/`） | ✅ |
| `docs/*.md` 其余 | 各专题的当前真源（如 `NOT-DOING.md` 否决台账、`CHANNEL-COVERAGE-PLAN.md` 渠道台账、`MATERIALS-PLANE-PLAN.md` 材料平面方案） | ✅ |
| `docs/research/` | **外部研究**的结论（读别人的东西得到的） | ✅ |
| `specs/` | **Spec Kit 工作区**：规格 → 计划 → 任务。不是产品文档 | ✅ |
| `eval/` | 评测语料与脚本（`eval/golden/` 是门禁三件最小集，**⚠ 勿删**） | ✅ |
| **`tools/gov-qa/`** | **另一条线**（政务问答采集，**已进本仓门禁**）。**它的可复用资产清单** = [`REUSE-FOR-ANNOUNCEMENTS.md`](../tools/gov-qa/REUSE-FOR-ANNOUNCEMENTS.md)（中间件指纹 / 可达性矩阵 / 水位三型 / 纯 ASCII 接口 / 地级市→省映射）。**入口** = [`README.md`](../tools/gov-qa/README.md) | ✅ |
| **`docs/verify-briefs/`** | **独立复核与取证报告**（17 份）。⚠ 其中两份是 **2026-10-10 从仓库临时件字节级搬进来的**（原件在 `.tmp-*`，会被清）——`VERIFY-REPORT-govqa-data-forensics.md` / `VERIFY-REPORT-spec004-operationalization.md` | ✅ |

### 1.3 工程配置

| 位置 | 是什么 |
|---|---|
| `pyproject.toml` | Python 工程配置（引擎） |
| `pelican-bike.html` | ⚠ **别人的未提交件**——既不属于本项目，也不是本会话产出的。**MUST NOT 动、MUST NOT 提交** |
| `package.json` / `package-lock.json` | Node 工程配置（插件） |
| `.gitignore` | 忽略规则 |
| `AGENTS.md` | **项目规矩**（每个会话都读的那一份） |
| `README.md` | 仓库入口 → 指向本文件 |
| `.specify/` | Spec Kit 脚手架（模板、脚本、宪法、工作流） |

### 1.4 本地产物与缓存（**不进版本控制，不是项目文件**）

> ⚠ **本表只列"不进版本控制"的东西。**
> `wenjianmulu/`（活数据）与 `pipeline/`（活真源）**受版本控制，不属本表**——它们在 §1.1/§1.2 与 §三。

| 位置 | 是什么 | 能不能删 |
|---|---|---|
| `var/` | 本机工作产物：`tmp/`（临时）、`fixtures/`、`ocr-loop/`、`backup/`、`cad/`、`articles/`、`hindsight-*/`、`mineru_cli_out/`、**`_trash-2026-10-05/`**、**`_trash-2026-10-11/`**（两个回收区） | ⚠ **只移不删**——它没有版本控制这个安全网 |
| `.venv/` | Python 虚拟环境 | 可重建 |
| `node_modules/` | Node 依赖 | 可重建 |
| `.mypy_cache/` `.pytest_cache/` | 工具缓存 | 可删 |
| `.dsh/` | 项目级 skill 副本与本地状态 | 可删（用户级 `~/.dsh/` 有同一份） |
| `.zcode/` `.browser4-cli/` | 本机工具状态 | 可删 |
| `stdscan/` | ✅ **已处置**：移到 `var/_trash-2026-10-05/` 并加进 `.gitignore`（见 §三） | 已不在顶层 |
| ~~**`.tmp-*`**~~（顶层 233 个） | ✅ **已归集（2026-10-11）**：移进 `var/_trash-2026-10-11/root-tmp/`（**只移不删**） | 已不在顶层 |
| **`.round-floor`** | gov-qa 的采集地板值（**另一个自动化维护**） | 🔴 **不动** |
| ~~**`recon/`**~~（顶层，4.6 MB） | ✅ **已归集（2026-10-11）**：`ln8890/` 的 32 个 JS 移进 `var/_trash-2026-10-11/recon-ln8890/` | 已不在顶层 |
| ~~**`.workbuddy-ai/`**~~ | ~~每轮交接单与记忆~~ | ✅ **已删（2026-10-10，业主令）**——WorkBuddy 已停用；内容**字节级归档**进 [`archive/workbuddy-memory/`](archive/workbuddy-memory/README.md)，**引用已同步改到归档位置** |
| **`var/_trash-2026-10-11/`** | **2026-10-11 全仓整理的回收区**（15.13 GB / 9,548 文件）：根目录 `.tmp-*`、`eval/` 三个可重建实验库、`var/tmp` 一次性产物、顶层 `recon/`。**判据与搬回方法见它自己的 README** | ⚠ **只移不删**——删前先确认没人在用（本仓为此丢过原始证据） |

> **⚠ 关于 `.tmp-*`（2026-10-10 补）**：它们**看着像杂物，实际是别人正在用的取证现场**。
> 其中**两份是实质报告**（数据质量取证 41 KB / spec 004 独立复核 36 KB），
> **已被字节级归档**进 `docs/verify-briefs/`（见 §1.2）——**原件仍不删**。
> 判定依据与读数见 [`specs/001-project-consolidation/top-level-inventory.md`](../specs/001-project-consolidation/top-level-inventory.md) §三。

---

## 二、一条规矩：东西该放哪

| 你手上的东西 | 放哪 |
|---|---|
| **现在是什么、该怎么做** | `docs/` |
| **给接手人看的说明** | `docs/wiki/` |
| **读别人的东西得到的结论** | `docs/research/` |
| **已经被取代的、过期的、过程的** | `docs/archive/` |
| **Spec Kit 的规格/计划/任务** | `specs/` |
| **本机产物** | `var/` |

**口诀**：**"交接时新人需要看它吗？"** 需要 ⇒ **不是** `var/`；不需要 ⇒ **不该在** `docs/`。

**一个事实一个归属层**：同一件事**只在它归属的那一份里写全文**，别处只链接。

---

## 三、几个容易被误判的条目（**别删**）

**⚠ 我之前把前两条误标成"来历不明／待处置"——那是错的。根 `README.md` 早就写明了它们是什么。
下面是更正后的定性。**

| 条目 | **实际是什么** | 处置 |
|---|---|---|
| **`wenjianmulu/`** | 🔴 **生产库 `doc_meta.file_path` 指向这里的 PDF——活数据**。它是**证据 PDF 的溯源载体**（证据 tab 预览/高亮打开的就是它）。现有两份：`中国标准文献分类法（中标分类CCS）.pdf`、`GBT+39910-2021.pdf`。**受版本控制** | **MUST NOT 删、MUST NOT 移**。移了知识库的证据链就断 |
| **`pipeline/03-contract-delta.md`** | 🔴 **schema 契约增量台账——活真源**（每次 schema 变更记录 DDL/影响面/回滚 SQL），**79 处引用**。**受版本控制**（`git ls-files` 可验） | **保留在原位**（它在仓库根不是 `docs/` 下，是历史原因）。改 schema 前必读 |
| `stdscan/` | 本机探测日志（3 个 `.log`，**0 个受版本控制**） | ✅ **已处置**：移到 `var/_trash-2026-10-05/stdscan/`（只移不删），并加进 `.gitignore` |
| `.browser4-cli/` | 浏览器工具的截图与快照（**0 个受版本控制**） | **已在 `.gitignore`（L40）**，无需处理 |
| ~~`B3A-REPORT.md` / `B3B-REPORT.md`~~ | 根目录两份实施报告（工作树产物） | ✅ **已归位**：移到 [`archive/impl-reports/`](archive/impl-reports/) |
| ~~`.workbuddy-ai/`~~ | 每轮交接单与记忆 | ✅ **已删（2026-10-10，业主令）**：WorkBuddy 已停用（应用 2026-10-10 19:47 退出）。内容**字节级归档**进 [`archive/workbuddy-memory/`](archive/workbuddy-memory/README.md)，**5 处引用已同步改到归档位置** |
| **`.tmp-*` / `recon/` / `.round-floor`** | **并行自动化的现场**（探针、commit 消息、JS 逆向产物、采集地板值） | 🔴 **不动**（见 §1.4 的详细判据） |

> **⚠ `.workbuddy-ai/` 的处置经过（2026-10-10）**：
> 上一轮（spec 001 §3.4）把它登记为「**待业主裁定**」——因为它**未被 `.gitignore` 盖住**，
> 每次 `git status` 带噪声、`git add -A` 会误扫。
> **业主 2026-10-10 裁定：WorkBuddy 已停用，删掉。**
> **删之前先做了两件事**（否则会留下断链与证据丢失）：
> ① **字节级归档** 13 个文件到 `archive/workbuddy-memory/`（逐文件 sha256 已核）；
> ② **同步改 5 处引用**（开发史 / NEXT-DEV-PLAN / HANDOVER-2026-10-09 / exp-12 README /
> VERIFY-REPORT-rerank-fix）指向归档位置 —— 按 `naming-convention.md` §九 第 3 条。
> ⚠ **用户级 `~/.workbuddy-ai/`（122 GB）按业主令保留**（不在本仓、不进版本控制）。

**教训（写给下次的我）**：**判一个条目"来历不明"之前，先读根 `README.md` 的「目录结构」一节。**
它逐条写了每个目录是什么、哪些是活数据。我这次没先读，差点把生产库的证据 PDF 当垃圾。

---

## 四、维护

- **本文件与 `docs/wiki/` 由谁来改**：新增/移动顶层条目时**同步改本文件**。
  改了子系统代码，同步改 `docs/wiki/components/` 里对应的那一篇。
- **`docs/INDEX.md`** 是**机械生成**的（`scripts/docs/gen-doc-index.py`），**不要手改**。
- **断链检查**：`python scripts/docs/check-links.py`。**它独立于门禁**——门禁扫不到全部文档。
