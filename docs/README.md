# KnowledgeStation 文件地图

**这是什么**：仓库里**每一样东西在哪、用来干什么**。
**给谁看**：接手的 agent 与人。**读完这一页，你就知道该去哪找。**

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
| `docs/*.md` | **当前真源**：标准文档（全大写，如 `NOT-DOING.md` / `DEVELOPMENT-HISTORY.md`）+ 各专题计划 | ✅ |
| `docs/research/` | **外部研究**的结论（读别人的东西得到的） | ✅ |
| `specs/` | **Spec Kit 工作区**：规格 → 计划 → 任务。不是产品文档 | ✅ |
| `eval/` | 评测语料与脚本（如 `eval/golden/`、`eval/lay-phrasing/`） | ✅ |

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

## 三、已知的来历不明项（**待处置，别当成正常**）

| 条目 | 情况 | 状态 |
|---|---|---|
| `wenjianmulu/` | 中文目录名（"文件目录"），含 2 个受控文件 | ⏳ 待定性 |
| `stdscan/` | 3 个文件，0 个受控 | ⏳ 待定性 |
| `pipeline/` | 1 个文件，1 个受控 | ⏳ 待定性 |
| `.browser4-cli/` | 43 个文件，0 个受控（本机工具状态） | ⏳ 待定性 |
| `B3A-REPORT.md` / `B3B-REPORT.md` | 根目录两份实施报告（工作树产物） | ⏳ 待归位 |

**本节由本特征（`specs/001-project-consolidation`）负责清空。** 清完就删掉这一节。

---

## 四、维护

- **本文件与 `docs/wiki/` 由谁来改**：新增/移动顶层条目时**同步改本文件**。
  改了子系统代码，同步改 `docs/wiki/components/` 里对应的那一篇。
- **`docs/INDEX.md`** 是**机械生成**的（`scripts/docs/gen-doc-index.py`），**不要手改**。
- **断链检查**：`python scripts/docs/check-links.py`。**它独立于门禁**——门禁扫不到全部文档。
