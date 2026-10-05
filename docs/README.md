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
| `tests/` | pytest 测试（约 163 个文件）；`tests/fixtures/` 放夹具 | ✅ |
| `scripts/` | 工具脚本：门禁 `run-gates.ps1`、快照 `snapshot-project.ps1`、文档工具 `docs/` | ✅ |

### 1.2 文档

| 位置 | 是什么 | 受版本控制 |
|---|---|---|
| **`docs/README.md`** | **本文件**——文件地图 | ✅ |
| `docs/wiki/` | **接手文档**：项目现状 `architecture.md` + 每套组件的职责/接口/依赖/非目标 | ✅ |
| `docs/archive/` | **历史**：旧计划 / 过期基线 / 调研过程 / 已完成复核。索引见它自己的 README | ✅ |
| **`docs/ENCYCLOPEDIA.md`** | **技术百科全书**（架构 / 数据契约 / 检索 / 入库 / 坑全集 / 红线宪法）——**接手先读这一份** | ✅ |
| `docs/INTRODUCTION.md` | 产品介绍（是什么 / 为什么可信 / 能力清单） | ✅ |
| `docs/VISION-TREE.md` | 功能愿景（客户视角：每条能力标注「今天点得到吗」） | ✅ |
| `docs/DEVELOPMENT-HISTORY.md` | 开发简史（§一~§九 叙事 + 203 轮索引；逐轮明细已入 `archive/history/`） | ✅ |
| `docs/*.md` 其余 | 各专题的当前真源（如 `NOT-DOING.md` 否决台账、`CHANNEL-COVERAGE-PLAN.md` 渠道台账、`MATERIALS-PLANE-PLAN.md` 材料平面方案） | ✅ |
| `docs/research/` | **外部研究**的结论（读别人的东西得到的） | ✅ |
| `specs/` | **Spec Kit 工作区**：规格 → 计划 → 任务。不是产品文档 | ✅ |
| `eval/` | 评测语料与脚本（`eval/golden/` 是门禁三件最小集，**⚠ 勿删**） | ✅ |

### 1.3 工程配置

| 位置 | 是什么 |
|---|---|
| `pyproject.toml` | Python 工程配置（引擎） |
| `package.json` / `package-lock.json` | Node 工程配置（插件） |
| `.gitignore` | 忽略规则 |
| `AGENTS.md` | **项目规矩**（每个会话都读的那一份） |
| `README.md` | 仓库入口 → 指向本文件 |
| `.specify/` | Spec Kit 脚手架（模板、脚本、宪法、工作流） |

### 1.4 本地产物与缓存（**不进版本控制，不是项目文件**）

| 位置 | 是什么 | 能不能删 |
|---|---|---|
| `var/` | 本机工作产物：`tmp/`（临时）、`fixtures/`、`ocr-loop/`、`backup/`、`cad/`、`articles/`、`hindsight-*/`、`mineru_cli_out/` | ⚠ **只移不删**——它没有版本控制这个安全网 |
| `.venv/` | Python 虚拟环境 | 可重建 |
| `node_modules/` | Node 依赖 | 可重建 |
| `.mypy_cache/` `.pytest_cache/` | 工具缓存 | 可删 |
| `.dsh/` | 项目级 skill 副本与本地状态 | 可删（用户级 `~/.dsh/` 有同一份） |
| `.zcode/` `.browser4-cli/` | 本机工具状态 | 可删 |
| `wenjianmulu/` `stdscan/` `pipeline/` | ⚠ **来历不明**，见 §三 |

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
| **`wenjianmulu/`** | 🔴 **生产库 `doc_meta.file_path` 指向这里的 PDF——活数据**。它是**证据 PDF 的溯源载体**（证据 tab 预览/高亮打开的就是它）。现有两份：`中国标准文献分类法（中标分类CCS）.pdf`、`GBT+39910-2021.pdf` | **MUST NOT 删、MUST NOT 移**。移了知识库的证据链就断 |
| **`pipeline/03-contract-delta.md`** | 🔴 **schema 契约增量台账——活真源**（每次 schema 变更记录 DDL/影响面/回滚 SQL），**79 处引用** | **保留在原位**（它在仓库根不是 `docs/` 下，是历史原因）。改 schema 前必读 |
| `stdscan/` | 本机探测日志（3 个 `.log`，**0 个受版本控制**） | ✅ **已处置**：移到 `var/_trash-2026-10-05/stdscan/`（只移不删），并加进 `.gitignore` |
| `.browser4-cli/` | 浏览器工具的截图与快照（**0 个受版本控制**） | **已在 `.gitignore`（L40）**，无需处理 |
| ~~`B3A-REPORT.md` / `B3B-REPORT.md`~~ | 根目录两份实施报告（工作树产物） | ✅ **已归位**：移到 [`archive/impl-reports/`](archive/impl-reports/) |

**教训（写给下次的我）**：**判一个条目"来历不明"之前，先读根 `README.md` 的「目录结构」一节。**
它逐条写了每个目录是什么、哪些是活数据。我这次没先读，差点把生产库的证据 PDF 当垃圾。

---

## 四、维护

- **本文件与 `docs/wiki/` 由谁来改**：新增/移动顶层条目时**同步改本文件**。
  改了子系统代码，同步改 `docs/wiki/components/` 里对应的那一篇。
- **`docs/INDEX.md`** 是**机械生成**的（`scripts/docs/gen-doc-index.py`），**不要手改**。
- **断链检查**：`python scripts/docs/check-links.py`。**它独立于门禁**——门禁扫不到全部文档。
