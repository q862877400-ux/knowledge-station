# 其他目录事实地图

> 调查范围：`eval/`、`tools/gov-qa/`、`wenjianmulu/`、`output/`、`pipeline/`、`.specify/`、`.codebuddy/`、`.dsh/`、`.zcode/`。
> 方法：只读文件 + `grep`/`Select-String`/`Get-ChildItem`/`git ls-files`。**没有跑门禁、没有跑 pytest、没有跑 npm。**
> 每条结论后面是**可搜索的文字 + 文件**；数不出来或没核的写「未读 / 未核，原因」。
> 调查时基准提交：`f3eee72f`；工作区**不干净**（`git status --short` → 42 modified + 752 untracked，非本次造成、本次未改任何文件）。
> ⚠ 本机 **`%APPDATA%\KnowledgeStation` 不存在**（`Test-Path "$env:APPDATA\KnowledgeStation"` 为假）⇒ 凡依赖「真库」的结论只能核到代码与文档，不能核到库内实况。

---

## 一、`eval/`（最详细）

### 1.1 一句话

**它是「检索质量的尺子」——不是产品代码，不是测试，是一堆**冻结的考卷 + 量法脚本 + 实验结果**，其中只有 `golden/` 那一小块进了门禁（且只在 `-Full` 里跑）。**

命令与数字：

```
Get-ChildItem eval -Recurse -File -Force        → 438 个文件
(Measure-Object Length -Sum).Sum                → 19.7 MB
git ls-files eval | Measure-Object              → 426 条受版本控制
扩展名分布：.py 167 / .json 141 / .md 54 / .jsonl 46 / .txt 13 / .pyc 7 / .gitignore 4 / .csv 2
            .db 1 / .db-shm 1 / .db-wal 1 / .log 1
```

根下三个文件：`README.md`（7,150 B，**全目录的归属层，混用前必读**）、`run_benchmark.py`（7,816 B，Golden Set 评测器）、`baseline.json`（263 B，门禁基线）。

### 1.2 目录结构：分 6 类

| 目录 | 文件数 | 干什么 | 归属层 |
|---|---|---|---|
| `golden/` | 5（10.2 MB） | **冻结的金标集**（96 条）+ 快照库 `knowledge-snapshot.db`（10,637,312 B）。防倒退的尺子，**不是难度尺子** | `build_golden.py` 的 docstring |
| `recall-funnel/` | 363（6.7 MB） | **六路召回漏斗诊断**：171 条考卷 × 6 通道逐条名次，外加 19 个 `exp-*` 实验目录 | `recall-funnel/README.md` |
| `lay-phrasing/` | 41 | **外行说法语料**（生成侧资产）。`gen-V2.jsonl` = 500 术语 / 1,832 条说法 | `lay-phrasing/README.md` |
| `bunny-benchmark/` | 6 | **正向考卷**（先有问法再配条文）：送审 150 ⇒ 可用 24 | `bunny-benchmark/README.md` |
| `reverse-benchmark/` | 7 | **反向考卷**（看着条文反推问法）：配对 310 ⇒ 可用 171 | `reverse-benchmark/README.md` |
| `real-question-ruler/` | 5 | **真人问答尺子 v1**：从 41.5 万条真人问答抽 500 条；**替代** `lay-phrasing/` 那条线 | `real-question-ruler/README.md` |
| `govqa-label-review/` | 7 | gov-qa 标签的 **AI 复核包**（不是人工确认） | `govqa-label-review/README.md` |

`recall-funnel/` 一级子目录**实测 22 个**（19 个 `exp-*` + `baseline-v0` + `clean-v3` + `regression-ingest`）：
`exp-1-contextual` / `exp-3-query-side` / `exp-3b-query-side-loo` / `exp-4-embedding-shadow` / `exp-4b-embedding-round2` / `exp-4c-embedding-1024` / `exp-5-real-questions` / `exp-6-cap` / `exp-7-rrm` / `exp-8-fullrank` / `exp-9-col-prior` / `exp-10-p4-feasibility` / `exp-11-rerank-fix` / `exp-12-long-clause-tail` / `exp-13-query-rewrite` / `exp-14-fused-rewrite` / `exp-15-pool-depth-fusion` / `exp-16-edge-expansion` / `exp-17-embedding-production-plan`。
⚠ `recall-funnel/README.md` 自述「本目录有 **23 个子目录**」——我数到 22（可能把那一个 `__pycache__` 算进去了）。**编号缺 exp-2**（`specs/002-recall-funnel/tasks.md` 提过 `exp-2-query-side/`，磁盘上没有）。

### 1.3 它被谁引用（全仓实测）

**结论：`src/` 与 `plugin/` 一行都不读它；只有 `tests/` 读，且读法分两种（import 模块 / 按路径当数据）。**

```
grep -r "from eval\|import eval"  src/ plugin/ scripts/   → 0 命中
grep -r "eval/"                   src/**/*.py             → 仅 3 处注释，无代码引用
grep -r "eval"                    plugin/*.js/ts/mjs      → 命中全是 retrieval / evaluate 之类的词
```

读它的 10 个 test 文件（可搜索文字逐条列出）：

| 文件 | 可搜索文字 | 读的是 |
|---|---|---|
| `tests/test_golden_gate.py` | `from eval.run_benchmark import run_benchmark`；`BASELINE = ROOT / "eval" / "baseline.json"`；`SNAPSHOT = ROOT / "eval" / "golden" / "knowledge-snapshot.db"` | 基线 + 快照库 |
| `tests/test_golden_criterion.py` | `from eval.run_benchmark import _hit`；`snap = ROOT / "eval" / "golden" / "knowledge-snapshot.db"` | 命中判据 + 快照库 |
| `tests/test_fused_rewrite_ruler.py` | `SCRIPT = REPO / "eval" / "recall-funnel" / "exp-14-fused-rewrite" / "run.py"`；`BENCH = REPO / "eval" / "recall-funnel" / "benchmark-v2.jsonl"` | exp-14 尺子 |
| `tests/test_pool_depth_ruler.py` | `SCRIPT = REPO / "eval" / "recall-funnel" / "exp-15-pool-depth-fusion" / "run.py"`；`EXP7 = REPO / "eval" / "recall-funnel" / "exp-7-rrm" / "run.py"` | exp-15 / exp-7 |
| `tests/test_query_rewrite_ruler.py` | `SCRIPT = REPO / "eval" / "recall-funnel" / "exp-13-query-rewrite" / "run.py"` | exp-13 |
| `tests/test_long_clause_tail_ruler.py` | `SCRIPT = REPO / "eval" / "recall-funnel" / "exp-12-long-clause-tail" / "measure.py"` | exp-12 |
| `tests/test_embedding_rebuild_resume.py` | `SCRIPT = REPO / "eval" / "recall-funnel" / "exp-17-embedding-production-plan" / "rebuild-shadow.py"` | exp-17 重建脚本 |
| `tests/test_govqa_label_review.py` | `HERE = Path(__file__).resolve().parents[1] / "eval" / "govqa-label-review"` | AI 复核包 |
| `tests/test_real_question_ruler.py` | `HERE = Path(__file__).resolve().parents[1] / "eval" / "real-question-ruler"` | 真人尺子 |

⚠ **这些文件不能单独删**：`test_golden_gate.py` / `test_golden_criterion.py` 是 `import`（模块级依赖），其余 7 个是 `spec_from_file_location` 按路径加载（文件没了测试直接报错，不是 skip）。

**产品侧唯一沾边的一行**：`src/core/retrieval/hybrid_engine.py` 里 `"""设置/清除检索库路径覆盖（None=恢复默认）。仅 eval/测试使用。"""` —— 一个给 eval 用的测试钩子 `set_db_override`，产品逻辑不读 eval。

### 1.4 有没有口径说明？能不能重跑？

**有，而且是全仓写得最细的一处。** `eval/README.md` 开头就写明「**这份是 `eval/` 下所有评测资产的归属层**」，并从 §二 起钉死三条硬线（原文照抄）：

> 1. **不许把两批的通过率放在同一张表里比** —— 造法不同、样本量差 7 倍、判定稳定度不同。
> 2. **不许用正向那 24 条去量系统** —— 它自己的归属文档写着"只能算待复验"。
> 3. **用反向那 171 条时必须连带引用"循环论证"那条限制**。

它还把两批考卷的口径差异做成表格，并明确「**下一轮要量系统，只能用反向那 171 条**」。另外 §二 有一个指代更正块：「正向 24 条 ✅ 在」vs「正向 106 条 ❌ **不在** —— 那句自己写着"语料已用完"」——说明交接文档里曾把 106 当资产引用过。

**数据怎么生成 / 能不能重跑（逐目录核）：**

| 资产 | 生成方式（原文） | 本机能否重跑 |
|---|---|---|
| `golden/` | `build_golden.py` docstring：「从当前知识库抽取/合成问题-答案对，冻结落盘」「数据集固定为 `eval/golden/golden.json`（提交），benchmark 读盘评测，**不随库演化漂移**」 | **评测能**（快照库随仓：`& .venv\Scripts\python.exe eval\run_benchmark.py --db eval\golden\knowledge-snapshot.db`）。**重建不能**（`_load_real_clauses()` 要真库，本机无） |
| `recall-funnel/` | `README.md` 给了 8 条重跑命令（`build-v2.py` → `funnel.py` → `summarize.py` → …） | **不能**：`funnel.py` 写死 `DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"`，本机无此库 |
| `lay-phrasing/` | `gen-lay.py` 生成；README 记「2026-09-30 从 `var/tmp/` 迁入版本库」「**不可再生，最重要**」 | 需模型，未验证 |
| `bunny-` / `reverse-benchmark/` | `run-batch.py` / `generate.py` + `verify.py`（space-bunny-free 独立判 3 次） | 需外部模型，未验证 |
| `real-question-ruler/` | `build.py` 五道过滤 + 分层抽样（`specs/010-real-question-ruler/tasks.md` T001） | 依赖 41.5 万条真人问答语料 |

⇒ **一句话：本机唯一能跑的 eval 是「对快照库跑 golden 评测」。其余资产的重跑路径都断在「真库不在本机」或「要外部模型」。**

### 1.5 进版本控制吗？

```
git ls-files eval | Measure-Object   → 426
磁盘文件总数                          → 438
差额 12 = 4 个未跟踪工作文件 + 8 个被忽略的残留
```

- 未跟踪（`git status --short eval`）：`eval/golden/knowledge-snapshot.db-shm`、`...-wal`、`eval/recall-funnel/regression-ingest/funnel-per-query-cap100.jsonl`、`funnel-summary-cap100.json`。
- 被忽略（`git status --ignored eval`）：7 个 `__pycache__/` 下的 `.pyc` + `eval/recall-funnel/exp-4c-embedding-1024/embed1024.log`。
- **两个 10 MB 级大件受控**：`eval/golden/knowledge-snapshot.db`（10.6 MB，**是门禁的必需品**）、`eval/recall-funnel/` 的 46 个 `.jsonl`。
- 三个实验目录自带 `.gitignore` 把 `exp.db` 挡在外面（注释原文：「真库副本 2.2 GB + 新向量表 1.1 GB；它们是**可重建的运行产物**」）—— 那是这份 19.7 MB 没变成 15 GB 的原因。
- ✋ **本次调查发现 `eval/README.md` 处于「已修改未提交」状态**（`git status` 里是 ` M`）——不是我改的，我只读过。引用它的结论前先确认是谁在改。

### 1.6 门禁里有它吗？

```
Select-String -Path scripts/run-gates.ps1 -Pattern 'eval'  → 3 处，全部是 "retrieval" 里的子串
```

⇒ **`run-gates.ps1` 里没有任何 `eval` 步骤。** 它唯一的门禁入口是**间接**的：

```
scripts/run-gates.ps1:  if ($Full) { Add-Step 'pytest（引擎用例）' $py @('-m','pytest', ...) }
pyproject.toml:         testpaths = ["tests", "tools/gov-qa/tests"]
```

⇒ `tests/test_golden_gate.py` 属于 `tests` ⇒ **只在 `-Full` 会被跑，`-Quick` 跑不到它。**
（`run-gates.ps1` 文件头自述：「`-Full` 全量：**再加 pytest** / 引擎门禁 / 真宿主 e2e」。）

### 1.7 ⚠ 特别核查：`eval/golden/` 是 Golden Set 吗？现在还在用吗？

**是。而且在用，并且是全项目最强的那个约束。**

- **是什么**：`eval/golden/golden.json` 的 `meta` 写着 `{"source": "knowledge.db @ build time", "count": 96}`。96 条分型（`eval/README.md` §三）：`modality` 43 / `exact` 24 / `semantic` 20 / `legal_element` 3 / `modality_adversarial` 3 / `compliance` 3。
- **怎么用**：`run_benchmark.py` 对**快照库**跑（「默认对**快照库**跑（可复现、不依赖本机 `%APPDATA%`）」）；命中判据是 **(标准号, 条款号) 对**，不是只比条款号（「2026-09-24 改的」）。
- **谁在用它做门禁**：`tests/test_golden_gate.py`，文件头写得很清楚：

  > 「Golden Set CI 门禁（Task 10.1，红线 v2 #6）：**任何检索/核验改动不得回退**。」
  > 「⚠ 自豁免通道已关闭（2026-09-16）：旧实现在基线缺失时**自动写盘 + pytest.skip** ——删掉 `eval/baseline.json` 即可让整条门禁失效（**全项目唯一"一步可破坏"的防线**）。现在基线缺失 = **失败**。」

  三个用例：`test_golden_gate_baseline_present`（基线缺失 = `AssertionError`，只有 `KS_BASELINE_BOOTSTRAP=1` 才允许首次建立）、`test_golden_gate_no_regression`（受保护指标集 `KEYS = ("exact_hit@1", "recall@5", "recall@10", "modality_intercept_rate")`，任一指标 `delta_pp < -2.0` 即失败）、`test_golden_gate_minimums`（`modality_intercept_rate` 硬底线 0.9）。
- **当前基线读数**（`eval/baseline.json` 逐字）：`exact_hit@1 0.8889` / `recall@5 0.9778` / `recall@10 0.9889` / `modality_intercept_rate 1` / `n_search 90` / `n_adversarial 3`。
- **它自己的两个已知弱点（都在仓库里写明了，不是我判的）**：
  1. `eval/README.md` §三：「⚠ **它不含 `code_revision` 字段**（`contracts/baseline.schema.md` 要求有）⇒ **无法判断这几个数是哪一版代码跑出来的**。」
  2. 实测 `baseline.json` 的 `meta.golden` 写死旧绝对路径：`"D:\\AI\\work space\\zcode\\eval\\golden\\golden.json"` —— 便携版换盘符后这条元数据是错的（不影响判定，代码不用它，但会误导人）。
  3. 快照库本身很小：`docs/research/cross-language-retrieval-evidence.md` 写「门禁用的快照库（`eval/golden/knowledge-snapshot.db`，**19 篇 / 1,586 条**）」⇒ 96 条金标只落在 19 篇文档上，**它的绿不代表真实库的检索质量**，只代表"没倒退"。
- **一处历史残留**：`docs/archive/history/rounds-10.1-10.203.md` 记「金标里的 3 道**审查题**｜**保留为史料**：`eval/golden/golden.json` 至今有 3 条 `"type": "compliance"`…**评测器不再打它们**」。这与现在 `KEYS` 只有 4 个检索指标一致 —— 3 条 compliance 题在数据里但不在判据里。
- **`tests/test_golden_set.py` 不读 `eval/`** —— 它自带一份内联 `QA_GOLDEN` 列表（「T11 Golden Set：标准问答（GB30871 真实库）」），别把两者当同一件事。

### 1.8 `eval/` 的风险面（给业主看的三条）

1. **能整目录删掉吗？不能。** 删了 `eval/baseline.json` 或 `eval/golden/knowledge-snapshot.db`，`tests/test_golden_gate.py` 会红（前者硬失败、后者 skip 但会让门禁失去意义），而**这是全项目唯一防检索倒退的机械约束**。`specs/010-real-question-ruler/spec.md` 也写了「不删 `eval/lay-phrasing/`…归档还是删除由业主定」。
2. **可以删/可以不管的**：7 个 `.pyc`、1 个 `.log`（运行残留）；`eval/golden/knowledge-snapshot.db-shm/-wal`（打开快照库留下的 WAL 残渣，测试自己会拷到临时目录跑，这两个是历史残留）。`lay-phrasing/`（1,832 条 AI 生成说法）**业主已判"不需要了"**（`specs/010-real-question-ruler/README.md` 引业主 2026-10-11 原话），但归档还是删除**待业主定**。
3. **不可复现的地方**：除 golden 评测外，`recall-funnel` 的 171 条重跑、`bundle` 的生成，全部依赖本机不存在的真库或外部模型 ⇒ **这些数字只能引用，不能现场复算**。

### 1.9 未读（原因写清）

- `eval/recall-funnel/` 的 22 个子目录共 363 个文件：**只读了目录结构 + `README.md` 的总索引**（那份 README 的 §〇 自称「一行为一个实验，写清"试了什么 / 判决 / 去哪看"」），**没有逐个读各实验的 REPORT / verdict.json / 结果 json**。
- `eval/lay-phrasing/` 的 24 个 `.py` 探针脚本：只读了 README 的表格，没读脚本体。
- `eval/golden/golden.json` 全文：只读了前 40 行 + `meta.count`，没逐条读 96 题（`docs/RETRIEVAL-LONG-RANGE-PLAN.md` 记「读了…全部 96 条的提问原文（不是抽样，是逐条）」，那是别人做过的，我没重做）。

---

## 二、`tools/gov-qa/`（另一条线，948 MB）

### 2.1 它是什么

**政务问答采集器**：把部委/省市官网的「公众问答 / 留言答复」扒下来，整理成统一记录格式，再切成两类资产（能当考卷的 / 该补的料）。`README.md` 开头：「**这个页面就是交接说明。**」

大盘：**3,423 个文件 / 948.8 MB**，其中 `git ls-files tools/gov-qa` = **2,120** 条受控。

### 2.2 入口在哪

`README.md` §一「三十秒上手」三行命令（原文）：

```powershell
.venv\Scripts\python.exe tools\gov-qa\harvest.py --list      # ① 看有哪些站、什么状态
.venv\Scripts\python.exe tools\gov-qa\harvest.py --site mee  # ② 采一个站（按 id 去重、只追加新的）
.venv\Scripts\python.exe tools\gov-qa\measure-locate-rate.py # ③ 看这批货能不能当考卷
```

日常运维三个（§7.1）：`health.py`（能不能用）、`poll.py --all`（增量轮询）、`coverage-report.py --thin`（还缺哪里）。
**入口文件是 `harvest.py`（8,439 B），不是某个 main。**

### 2.3 目录分层（实测文件数）

| 路径 | 文件数 | 体积 | 是什么 |
|---|---|---|---|
| 顶层 | **621** | — | 其中 **592 个是 `assets-*.json`**（切好的两类资产，一个站一个文件）。其余 29 个是代码与台账：`harvest.py` / `poll.py` / `health.py` / `coverage.py` / `state.py` / `channel.py` / `common.py` / `regions.py` / `query.py` / `userscript` 等 + `README.md` / `SITE-REGISTRY.md`(204,899 B) / `HANDOVER-FULL.md` / `PLAYBOOK.md` / `FIXES-2026-10-10.md` / `WRITE-SCOPE.md` / `MINISTRY-ENTRIES.md` / `NAT-ENTRIES.md` |
| `adapters/` | 740 | 2.6 MB | **371 个 `.py` + 369 个 `.pyc`**。`adapters/__init__.py` 的 `ADAPTERS` 登记表**实测 363 条**。README §二：「加一个新站点 = 写一个适配器（**不用改别的文件**）」 |
| `data/` | 686 | **644.2 MB** | 采到的问答，一行一条 |
| `recon/` | 1,318 | 100.4 MB | 侦察过程的原始证据：`.html` 328 / `.py` 275 / `.txt` 194 / `.log` 158 / `.js` 145 / `.json` 130 / `.sh` 47 / `.md` 16 / `.jsonl` 12 / `.jspx` 2 / `.woff` 2 / `.joblib` 1。子目录：`liuyan-js/`(2) 与 `state/`(1，7.5 MB) |
| `gate/` | 3 | 0.04 MB | `check.sh`(9,406 B) / `GOAL.md`(25,030 B) / `README.md`(2,151 B) |
| `state/` | 2 | 0.8 MB | `watermarks.json`(440 B) + `migration-backup-20261010-041212.jsonl`(862,532 B) |
| `tests/` | 46 | 0.6 MB | 23 个 `test_*.py` + 其余基建 |

### 2.4 它和主项目怎么交互？

**采集链完全独立；只有"能不能当考卷"的测量与召回评测要读主项目。**

README §六 边界第 2 条原文：「**只写 `data/`**：本模块**不碰数据库、不碰生产件**。」

实测支撑（`grep -r "from src\.\|import src\." tools/gov-qa` → 只有 4 行，全在**一个**文件里）：

| 文件 | 可搜索文字 | 性质 |
|---|---|---|
| `tools/gov-qa/run-real-recall.py` | `from src.core.storage.sqlite_db import load_vec_extension`<br>`from src.core.retrieval.hybrid_engine import search_with_details`<br>`from src.core.retrieval import hybrid_engine as he`<br>`from src.core.text_utils import standard_key` | 调**主项目检索代码**跑召回评测（只读） |
| `tools/gov-qa/run-real-recall.py` | `DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"` | 读**主项目真库**（只读） |
| `tools/gov-qa/measure-locate-rate.py` | 同上 `APPDATA` / `KnowledgeStation` / `database` / `knowledge.db` | 读真库判「在库率」 |
| `tools/gov-qa/recon/check-locate-rate-caliber.py` | 同上 | 口径复核，读真库 |

**回答三个问法**：
- 共用数据库？**不共用写入**（`data/` 是本地的 `.jsonl`）；**读取有 3 处**，都是 `mode=ro` 性质的只读测量。
- 共用渠道表？**不共用**。gov-qa 的"通道"是它自己的 `adapters/__init__.py` 的 `ADAPTERS` + `SITE-REGISTRY.md`；主项目的通道是 `src/core/retrieval/hybrid_engine.py` 的六路。两边同名不同物。
- 完全独立？采集/轮询/覆盖统计**完全独立**；只有"能不能当考卷"这一步跨过去调主项目。

另有一条**反向**耦合：主项目的门禁要跑 gov-qa 的脚本（见 2.5）。

### 2.5 它进本仓门禁的 4 处（逐条确认）

| # | 位置 | 原文 | 在哪个档位 |
|---|---|---|---|
| 1 | `pyproject.toml` | `testpaths = ["tests", "tools/gov-qa/tests"]` | pytest 步，**只在 `-Full`** |
| 2 | `scripts/run-gates.ps1` | `Add-Step 'gov-qa 质量闸门'  $py  @('tools/gov-qa/recon/gate-quality.py', '--quiet') $repo` | `if ($Full)` 内 |
| 3 | `scripts/run-gates.ps1` | `Add-Step 'gov-qa 幂等验证'  $py  @('tools/gov-qa/recon/verify-idempotent.py', '--quiet') $repo` | `if ($Full)` 内 |
| 4 | `scripts/run-gates.ps1` | `Add-Step 'gov-qa 通道台账最新'  $py  @('tools/gov-qa/recon/gen-channel-table.py', '--check', '--quiet') $repo` | `if ($Full)` 内 |

**四条全部只在 `-Full`**（`Add-Step` 上面那行就是 `if ($Full) {`）。`-Quick` 一条都不跑。
脚本注释还记了两件事：①「`tools/gov-qa/tests` 已并入**根 pytest** 的 `testpaths` ⇒ 上面那一步 `pytest` **已经跑了它**，这里**不再重复跑**」；② 冻结提交 `7bc67704` 实测「`tests` 2701 + `tools/gov-qa/tests` 102 = **2803**」。

### 2.6 `data/` 里 644 MB 是什么？受版本控制吗？

```
Get-ChildItem tools\gov-qa\data -File  → 686 个文件 / 644.2 MB
扩展名：.jsonl 594 / .cursor 90 / .rotation 2
git ls-files tools/gov-qa/data         → 686    ← 等于目录内文件总数
```

- **594 个 `.jsonl`** = 采到的问答，一行一条。口径见 `README.md` §二 的统一记录格式（`source` / `id` / `url` / `question` / `answer` / `asked_at` / `answered_at` / `dept` / `channel` / `extra`）。最大几个：`ln-8890-辽宁省·12345民心智慧听…jsonl` 31.09 MB、`sd-dongying…jsonl` 29.26 MB、`sd-yantai…jsonl` 27.63 MB、`nat-tax-国家税务总局·12366网上留言.jsonl` 25.50 MB。
- **`.cursor` 90 个**：**每个通道一个增量游标**，内容是**一个数字**。实测 `.people-liuyan-df.cursor` 的内容就是 `25671891`。它们是 `poll.py` 增量轮询的水位（和 `README.md` §7.2 的"从第 1 页开始翻、全已见过就停"配套）。
- **`.rotation` 2 个**：**未读**，原因：文件名像"轮转索引"，但没有任何文档说明它，读内容也判不出来源语义。
- **受版本控制：是，全部 686 个**（含 90 个 `.cursor`、2 个 `.rotation`）。⇒ **644 MB 的抓取语料进了 git**。`.gitignore` 对 gov-qa 只挡了一个文件：`tools/gov-qa/state/.poll.lock`。
- 另有一个不属 `data/` 但同类的东西：`state/watermarks.json`（440 B，通道水位）+ `state/migration-backup-20261010-041212.jsonl`（862,532 B，迁移备份）。

### 2.7 ⚠ 隐私抽样（3 个 `.jsonl`，663 条）——**这是抽样，不是全部**

抽样对象与理由：一个留言板源（最可能有真人信息）、一个 12345 热线源、一个市长信箱源。

| 文件 | 条数 | 手机号(11位) | 身份证(18位) | 固话 | `X先生/X女士` |
|---|---|---|---|---|---|
| `data/people-liuyan-df-人民网领导留言板·地方.jsonl` | 490 | **5** | 1（**假阳性**） | 11 | 0 |
| `data/sd-12345-山东省·12345热线·典型留言.jsonl` | 71 | 0 | 100（**全是 `id` 字段**） | 0 | 80 |
| `data/hb-wuhan-25-武汉市人民政府·市长信箱（12345）·siteId=25.jsonl` | 102 | 0 | 0 | 6 | 64 |

**逐项甄别（不是只看命中数）：**

1. `people-liuyan-df` 的 5 个手机号 —— **是真手机号，但属于政府/社区工作人员，且是答复原文自己写出来的**：
   - `…可随时拨打我单位电话：18519295030进行咨询…`
   - `…工作人员手机号：18811686625；办公室电话：82619055，有事随时联系。`
   - `…欢迎直接拨打社区热线18519692843、18519698404、62934632…`
   18 位那 1 处是施工许可证号：`…建筑工程施工许可证（编号：110105202109070101）`。
   `联系人` 1 处是客服电话 `400-010-5508`。
2. `sd-12345` 的 100 个 18 位数字 —— **逐条比对，100/100 等于该行的 `"id"` 字段**（形如 `"id": "250715102511053200"`），**0 处是身份证号**。`X先生` 是称谓：「巩先生来电反映：…」。
3. `hb-wuhan-25` —— 群众手机号**已被站方脱敏**成 `1*********1`；出现的 6 个固话是执法单位办公电话（`027-82281572` 等）；出现 **执法人员全名**「执法人员唐建新用电话…」。

**结论（只对这三个文件成立）：**
- **抽样里没有身份证号、没有住址、没有群众的真实手机号**。
- **抽样里有：政府工作人员/执法人员的姓名与工作手机号、单位办公固话** —— 这些都是**网站自己公开的答复原文**，不是采集器额外扒的。
- 结构性原因：统一记录格式（`README.md` §二）**没有姓名/电话/身份证/住址字段**；但同一节明写「⚠ **`answer` 必须是答复原文**，**不要清洗、不要摘要**」⇒ **个人信息的唯一入口就是原文**，无法靠字段设计挡住。
- **未覆盖面**：594 个 `.jsonl` 只看了 3 个（663 条 / 语料总量按 `output/_answers.txt` 记的「总记录 393,914」算 ≈ 0.17%）。**不能拿这三条结论代表全库。**
- 另有一个相邻事实（来自 README，不是我的推论）：`assets-netizen-comments.jsonl` 专门收「留言板的**网友跟帖**（真实群众的建议/反问/诉苦）」，带 `kind=网友跟帖（非官方答复）` 标注 —— 那批更可能有真人表达，**本次未抽样**。

### 2.8 `gate/` 与 `output/` 的关系（容易搞错，单列）

`tools/gov-qa/gate/README.md` 是本次调查里**信息量最高的一页之一**，原文：

> 「`tools/gov-qa` 从 2026-10-07 建到 10-10（4 天 297 个提交），它的**唯一质量闸门**一直是 `D:/AI/output/check.sh` —— 而 `D:/AI/output/` **不是 git 仓库**。」
> 「`check.sh` | `D:/AI/output/check.sh` | **运行时真源**（Stop hook 实际调用的那份）｜`check.sh` | 本目录 | **纳管副本**（字节级相同，进版本控制，可 diff、可回退）」

它还自曝了四条闸门缺陷（原文摘要）：「① **能假绿**：适配器注册表导入失败时…`check.sh` 只 `grep '^EMPTY='` ⇒ **判据②报绿**。已实测复现。② 四项判据都不覆盖内容质量…**闸门全看不见**。③ **标签口径与 `health.py` 不一致**…④ **口径收窄未进判据**…命中率仅 1.95%，而闸门在它上面报"质量全绿"。」

⇒ **`/d/AI/output/` 是另一条线的运行时目录（不在本仓），本仓的 `output/` 是它的同形副本/实例**（两者同名文件不同内容，见第四节）。`gate/check.sh` 里还写死 `TRACE="/d/AI/output/check-trace.log"`。

### 2.9 未读（原因写清）

- `adapters/` 的 371 个 `.py`：只读了 `README.md` §二 的适配器模板与 `__init__.py` 的登记条数，**没有逐个读适配器实现**。
- `recon/` 的 1,318 个文件：只按扩展名与子目录统计，**没有读内容**。
- 顶层 592 个 `assets-*.json`：只看了文件名（省/市/部委 + 平台名），**没有读内容**。
- `SITE-REGISTRY.md`（204,899 B）：**未读**，只从 README 知道它是「站点台账：每个站的接口 / 状态 / 怎么找 channelid」。

---

## 三、`wenjianmulu/`（2 个 PDF，3.0 MB）

### 3.1 这两个 PDF 是什么

```
Get-ChildItem wenjianmulu -File
  中国标准文献分类法（中标分类CCS）.pdf   2,168,397 B   文件头 %PDF-1.5
  GBT+39910-2021.pdf                        970,090 B   文件头 %PDF-1.7

git ls-files wenjianmulu  → 2 条（**两个都受版本控制**）
```

- `GBT+39910-2021.pdf` = **GB/T 39910-2021 标准正文**。`scripts/check-fixture-leak.py` 的注释自己确认过：「实测：`wenjianmulu/GBT+39910-2021.pdf` 是**真的** GB/T 39910-2021」。
- `中国标准文献分类法（中标分类CCS）.pdf` = 中标分类法（CCS）的**权威文本**。`src/core/update/ccs_seed.json` 的 `_doc` 字段原文：「中标分类法(CCS)二级种子树 … 全部节点 source=seed：凭编码知识人工整理的近似版，**待 wenjianmulu/中国标准文献分类法.pdf 全量入库后扩充/校正（F-16 权威本体入库）**」。
  ⚠ 这里有个**轻微不一致**：种子注释写的文件名是 `中国标准文献分类法.pdf`，磁盘上是 `中国标准文献分类法（中标分类CCS）.pdf`（多了括号后缀）。如实记，未判谁对。

### 3.2 为什么说它们是「活数据、勿删」——证据链

**不是"重要所以别删"，是"生产库的字段指着它"。**

文档侧（原文）：

| 文件 | 可搜索文字 |
|---|---|
| `docs/ENCYCLOPEDIA.md` | 「`wenjianmulu/` # GB/T 39910-2021.pdf 等——⚠ **生产库 doc_meta.file_path 指向这里，禁止删除/移动**」 |
| `docs/ENCYCLOPEDIA.md` | 「⚠ `file_path` 指向的文件是**证据 PDF 溯源载体**（证据 tab 预览/高亮打开它）——生产库现有两份指向仓库内部：`wenjianmulu/GBT+39910-2021.pdf` 与 `var/fixtures/测试法.pdf`…**删这些文件 = 该文档证据链断裂**」 |
| `docs/ENCYCLOPEDIA.md` | 「9. 生产库 doc_meta.file_path 指向的文件（wenjianmulu/、var/fixtures/、用户区标准目录）**禁止删除/移动**——删=证据链断裂。」 |
| `docs/README.md` / `README.md` | 「🔴 **生产库 `doc_meta.file_path` 指向这里的 PDF——活数据**。它是**证据 PDF 的溯源载体**（证据 tab 预览/高亮打开的就是它）…**MUST NOT 删、MUST NOT 移**。移了知识库的证据链就断」 |
| `docs/DEVELOPMENT-HISTORY.md` | 「**关键否决**（verifier 交叉核实价值体现）：`wenjianmulu/` 与 `var/fixtures/测试法.pdf` 是生产库 file_path 指向的**活数据**不删」 |

代码侧（这才是能搜到的、真的会执行的东西，`src/core/api/server.py`）：

| 位置 | 可搜索文字 | 缺文件时的行为 |
|---|---|---|
| PDF 原件端点 | `"SELECT file_path FROM doc_meta WHERE doc_id=?"` → `p = Path(row["file_path"])` → `return FileResponse(str(p), media_type="application/pdf", filename=p.name)` | `if not p.exists() …: return _json_error(404, "file_not_found", "PDF 原件不可用…")` |
| 图形端点 | 同一句 `SELECT file_path FROM doc_meta WHERE doc_id=?` → `locate_figure(...)` | 同样 404 `file_not_found` |
| 条款页码/书签端点 | `"SELECT standard_no, file_path FROM doc_meta WHERE doc_id=?"` → `if doc["file_path"] … and Path(doc["file_path"]).exists(): import fitz; pdf = fitz.open(doc["file_path"]); toc = pdf.get_toc()` | `Path(...).exists()` 为假 ⇒ **整段跳过**，回退到"策略 2"（法规类按条款号格式） |

### 3.3 删了会怎样？给证据

**会断，但不是"崩"——是静默降级 + 404。**

1. **证据 tab 打不开原件**：`/api/v1/documents/{doc_id}/file` 返回 404 `file_not_found`，文案「PDF 原件不可用（法律文本直灌文档无原页）」。用户看到的是"这篇文档没有原件"，**不是报错**——所以删了之后**门禁不会红、pytest 不会红**（没有任何测试读这两个 PDF，实测 `grep -r wenjianmulu tests/` 为空）。
2. **图出不来**：`/api/v1/documents/{doc_id}/figure/{fig_no}` 同样 404 `file_not_found`。
3. **条款页码/书签映射退化**：`fitz.open` 那段被跳过 ⇒ 该文档失去"PDF 自带书签 → 条款页码"这一层，只剩按条款号格式推断的回退路径。**这是最难发现的损失**：不报错，只是定位变差。
4. **CS 分类法入库（F-16）失去权威来源**：`src/core/update/ccs_seed.json` 明写种子是"近似版，待…全量入库后扩充/校正"——删了就没法校正。

**反过来说：这两个 PDF 受版本控制（`git ls-files` 2 条），所以就算工作区被删，`git checkout -- wenjianmulu/` 能拿回来。** 真正危险的是「git 里也删掉」或「整仓搬迁时漏拷」。

### 3.4 ⚠ 未核与文档矛盾

- **未核**：本机 `%APPDATA%\KnowledgeStation` **不存在** ⇒ 我**无法开库核对** `doc_meta` 里是否真有这两行、`file_path` 是否真指着这两个路径。所以 3.2 的证据是**代码读路径 + 文档声明**，不是库内实况。这一条要标记为"未在真库上验证"。
- **文档矛盾（实测）**：`specs/001-project-consolidation/rename-map.md` 写着
  「`wenjianmulu/` 及其中文目录 | **未跟踪**（不在版本控制里）；按 v2 §八 属 `var/` 同类的本机产物，不在本项目文件范围」
  —— 与 `git ls-files wenjianmulu`（**2 条**）直接矛盾。同目录的 `acceptance.md` 记过一次同类自相矛盾（「`docs/README.md` §1.4 表头写「本地产物（**不进版本控制**）」，表里却列着 `wenjianmulu/` `pipeline/`——而这两样**恰恰受版本控制**」）并说明已修 `docs/README.md`，但 `rename-map.md` 这一行**没跟着改**，至今仍是错的。

---

## 四、`output` / `pipeline` / `.specify` / `.codebuddy` / `.dsh` / `.zcode`

### 4.1 `output/` —— 自动化的本地草稿与状态

- **规模**：28 个文件 / 0.1 MB。`git ls-files output` = **0**（`.gitignore` 第 107 行 `/output/`）。
- **是什么**：主项目"门禁全绿"那条自动化的**作业单 + 取证记录 + 变异自验结果 + 心跳**：
  - `GOAL.md`（31,048 B）开头：「KnowledgeStation（`D:/AI/work space/zcode`）：按 **spec-kit 规范**持续施工，**并保持本仓门禁 `run-gates.ps1 -Full` 全绿**」+「✅ **里程碑已达成**：2026-10-10 **03:16** 首次拿到全绿（当时是 **9/9 · exit=0**；此前 00:06 是 8/9）」
  - `_answers.txt`（18,947 B）开头：「总记录 393,914　答复长度：min=1 p10=41 中位=152 p90=473 max=950789」→ **这是 gov-qa 语料的分析稿**
  - `_forensics{,2,3,4}.txt`（29,198 / 19,451 / 21,463 / 4,099 B）取证记录
  - `_*_mut.txt` / `_mutations*.txt` 变异自验结果；`_gatespot.py` / `_dupfix.py` 探针；`.work-heartbeat`(11 B) / `.work-start-ts`(11 B) 心跳与起始时间
- **谁用**：`tools/gov-qa/gate/check.sh` 两处：`START_FILE="output/.work-start-ts"`、`HB_FILE="output/.work-heartbeat"`（那一段注释：「起点记在 output/.work-start-ts（首次运行时创建）。这是**连续**时长」）。
- **能删吗**：**能**（0 受控、`.gitignore` 已挡）。代价是丢两样：① `output/GOAL.md` 与 `tools/gov-qa/gate/GOAL.md` **内容不同**（sha256 已比对：`3058A413…` vs `973CBE58…`；前者是主项目门禁自动化的作业单，后者是「GOAL — 全国政务问答通道打通 + 存量采集（长期无人值守）」）——删 `output/GOAL.md` 就丢了主项目那条线的作业单；② `check.sh` 的"连续工作时长"读数。

### 4.2 `pipeline/` —— 只有 1 个文件，但它是「改 schema 前必读」

- **规模**：`pipeline/03-contract-delta.md`，36,020 B，`git ls-files pipeline` = **1**（受控）。
- **是什么**：schema 契约增量台账。文件头：「**契约增量 03 · 更新模块数据契约落地**｜依据：`pipeline/02-architecture-contract.md` §2 数据契约｜红线流程：`contract.md` → `test_contract.py` → `schema.sql`」。每条含 DDL / 影响面 / 回滚 SQL。
- **谁用**：`docs/ENCYCLOPEDIA.md` 原文：「凡动 `schema.sql` / 通道枚举与 RRF 权重 / SSE 事件顺序 / 安全条款 → **必须先改 `pipeline/03-contract-delta.md`**（契约增量台账）+ `tests/test_contract.py`，再改实现，评审通过后方可合入。」`tests/test_contract.py` 里有三处注释指向它。
- **引用数**：`docs/README.md` 自述「**79 处引用**」。**我实测是 31 处**（`grep -r "pipeline/03-contract-delta"` 全仓 ripgrep，默认忽略规则）。口径差异**未查清**，两个数都不该直接引用。
- **内部断链（实测）**：文件第 3 行引用的 `pipeline/02-architecture-contract.md` **不存在**——`Get-ChildItem pipeline -Recurse` 只有 1 个文件；`docs/ENCYCLOPEDIA.md` 解释了原因：「pipeline/00~13 流水线文档（除 03）｜2026-09-12 冗余清剿（结论并入本文件；03 契约台账保留）｜git 历史」。
- **能删吗**：**不能**。它是"契约先行"这条红线的唯一落点，删了流程无处落地。

### 4.3 `.specify/` —— Spec Kit 工作区（脚手架 + 宪章）

- **规模**：21 个文件，`git ls-files .specify` = **20**（唯一不受控的是 `feature.json`，被 `.specify/.gitignore` 挡，注释：「Local pointer to the current feature directory. Rewritten every time you switch features」）。
- **是什么**：Spec Kit **1.0.13** 的项目工作区。`init-options.json`：「`"ai": "dsh"`, `"ai_skills": true`, `"feature_numbering": "sequential"`, `"speckit_version": "1.0.13"`」；`integration.json`：「`"integration": "dsh"`, `"script": "ps"`」。
  - `templates/` 5 个（spec / plan / tasks / checklist / constitution-template）
  - `scripts/powershell/` 6 个（`check-prerequisites.ps1` / `common.ps1`(35,295 B) / `create-new-feature.ps1` / `resolve-template.ps1` / `setup-plan.ps1` / `setup-tasks.ps1`）
  - `memory/constitution.md`（5,031 B）：头部自述「新增原则：共 7 条，全部自既有常驻规矩提取，**未发明新条款**」「来源：AGENTS.md「最高指令」一/二、动手之前、门禁、复核、诚实、搬运与记录」
  - `workflows/speckit/workflow.yml` + `workflow-registry.json`；`integrations/{dsh,speckit}.manifest.json`
- **谁用**：`speckit-*` 那 10 个 skill（`.dsh/skills/` 下同名副本）与 `specs/` 下的 feature 目录。`feature.json` 当前指 `specs\013-catalog-hidden-retrieval-guard`。
- **能删吗**：**不能删模板与脚本**（speckit-* skill 跑不动）。**能删的只有 `feature.json`**（本来就忽略、每次切 feature 重写）。

### 4.4 `.codebuddy/` —— 已停用的另一个 agent 工具的配置

- **规模**：4 个文件，`git ls-files .codebuddy` = **0**（`.gitignore` 第 110 行 `/.codebuddy/`）。
- **是什么**：CodeBuddy 的项目级配置。`settings.json.disabled` 内容是一个 `Stop` hook 调 `bash "$CODEBUDDY_PROJECT_DIR"/.codebuddy/hooks/goal-gate.sh`（`timeout: 300`）；另有 `settings.json.bak-20261010-011723`（256 B，同内容备份）；`hooks/check-full-green.sh`(5,340 B) 与 `hooks/goal-gate.sh`(3,638 B)。
- **状态**：**已停用** —— 文件名是 `settings.json.disabled`，不是 `settings.json`，所以 hook 不会触发。
- **能删吗**：**能**（本地产物、0 受控、已停用）。唯一值得留的是 `check-full-green.sh` 里的一条历史结论：「⚠⚠ **2026-10-10 修：原来写死 `9/9`，门禁一加步就【永久失效】。**…⇒ **本判据恒判"未达成"，无论门禁是绿是红**。那是**假红**」。这条与 `run-gates.ps1` 里"别写死步数"的更正同源，删之前值得先抄进 `docs/`。

### 4.5 `.dsh/` —— 项目级 skill 副本（混合归属）

- **规模**：11 个文件，`git ls-files .dsh` = **1**（只有 `.dsh/skills/compliance-qa/SKILL.md`）。
- **是什么**：11 个 skill 的项目级副本：`compliance-qa` + 10 个 `speckit-*`（`speckit-analyze` / `speckit-checklist` / `speckit-clarify` / `speckit-constitution` / `speckit-converge` / `speckit-implement` / `speckit-plan` / `speckit-specify` / `speckit-tasks` / `speckit-taskstoissues`）。
- **为什么只有 compliance-qa 受控**：它是被强制加进 git 的那一个（`git ls-files` 可验）。其余被 `.gitignore` 第 86 行 `.dsh/` 挡住——项目 `AGENTS.md` 的注释解释了原因：「项目级 `.dsh/`：skill 副本与本地状态，用户级 `~/.dsh/` 已有同一份」。
- **能删吗**：**`speckit-*` 那 10 个能删**（用户级有同一份，删了不影响本会话里已经加载的技能，但会改变优先级与"项目内覆盖"的能力）；**`compliance-qa` 不能删**（受控，是合规作答流程的载体，且它是本项目自定义的那一个）。

### 4.6 `.zcode/` —— 另一个 agent 工具的会话计划

- **规模**：1 个文件，`git ls-files .zcode` = **0**（`.gitignore` 第 29 行 `.zcode/`）。
- **是什么**：`.zcode/plans/plan-sess_737fd131-2285-4bd7-a362-de46f7cc3624.md`（4,751 B），内容是早期计划：「# 第一阶段实施计划（T00~T04 + MinerU 环境就绪 + 前端脚手架）｜工作目录：`D:\AI\work space\zcode`（当前为空，从零搭建）。项目代号 KnowledgeStation。」任务分解从「### T00 架构契约冻结」开始。
- **能删吗**：**能**（0 受控、本地产物）。内容是 2026-08 的早期计划 + 写死旧路径 `D:\AI\work space\zcode`，已被 `specs/` 与 `docs/DEVELOPMENT-HISTORY.md` 取代。

---

## 五、归属判定表

| 目录 | 属于谁 | 受版本控制 | 能不能删 | 依据（可搜索文字） |
|---|---|---|---|---|
| **`eval/`** | **主项目**（检索质量的尺子与考卷） | 426 / 438 | **不能整目录删**。`golden/`、`baseline.json`、被 test 引用的 `recall-funnel/exp-*` 都是硬依赖；`lay-phrasing/` 归档还是删除**待业主定** | `tests/test_golden_gate.py`「删掉 `eval/baseline.json` 即可让整条门禁失效」；`specs/010-real-question-ruler/spec.md`「不删 `eval/lay-phrasing/`…归档还是删除由业主定」 |
| **`tools/gov-qa/`** | **另一条线**（政务问答采集），但已被拉进本仓门禁 4 处 | 2,120 / 3,423 | **不能删**（门禁 4 处 + 主项目检索评测要用它）。⚠ **`data/` 644 MB 全进 git 这件事该不该继续，是待业主定的口径问题** | `pyproject.toml` `testpaths`；`run-gates.ps1` 三条 `Add-Step 'gov-qa …'` |
| **`wenjianmulu/`** | **主项目**（生产数据的证据载体） | 2 / 2 | **不能删、不能移** | `docs/ENCYCLOPEDIA.md`「生产库 doc_meta.file_path 指向这里，禁止删除/移动」 |
| **`pipeline/`** | **主项目**（契约台账） | 1 / 1 | **不能删** | `docs/ENCYCLOPEDIA.md`「凡动 schema.sql…必须先改 `pipeline/03-contract-delta.md`」 |
| **`.specify/`** | **主项目**（spec-kit 脚手架 + 宪章） | 20 / 21 | **不能删**（`feature.json` 例外） | `init-options.json`「`"speckit_version": "1.0.13"`」；`memory/constitution.md` |
| **`output/`** | **本地产物**（自动化草稿 + 状态），**不该进仓** | 0 / 28 | **能删**（代价：丢 `GOAL.md` 与 `check.sh` 的连续时长读数） | `.gitignore` `/output/`；`gate/check.sh`「`START_FILE="output/.work-start-ts"`」 |
| **`.codebuddy/`** | **本地产物**（已停用的另一个工具），**不该进仓** | 0 / 4 | **能删** | 文件名 `settings.json.disabled`；`.gitignore` `/.codebuddy/` |
| **`.dsh/`** | **混合**：`compliance-qa` 属主项目；`speckit-*` 是用户级副本 | 1 / 11 | **部分能删**（`speckit-*` 能，`compliance-qa` 不能） | `AGENTS.md`「项目级 `.dsh/`：skill 副本与本地状态，用户级 `~/.dsh/` 已有同一份」 |
| **`.zcode/`** | **本地产物**（另一个工具的早期计划），**不该进仓** | 0 / 1 | **能删** | `.gitignore` `.zcode/`；计划文件写死 `D:\AI\work space\zcode` |

**一句话归纳：**

- **主项目本体**：`eval/`、`wenjianmulu/`、`pipeline/`、`.specify/` + `.dsh/skills/compliance-qa/`。
- **另一条线（已半拉进本仓）**：`tools/gov-qa/`。
- **本地产物，不该进仓（也确实没进）**：`output/`、`.codebuddy/`、`.zcode/`、`.dsh/` 的 10 个 speckit 副本、`.specify/feature.json`。

---

## 六、我没搞清楚的

1. **真库不在本机**。`Test-Path "$env:APPDATA\KnowledgeStation"` 为假。因此三件事**未核**：① `eval/golden/golden.json` 重建（`build_golden.py` 要真库）；② `eval/recall-funnel/` 171 条重跑（`funnel.py` 写死 `%APPDATA%` 路径）；③ `wenjianmulu/` 两个 PDF 的 `doc_meta.file_path` 是否**现在**仍指着它们。真库到底在哪（是否 `KS_DATA_DIR` 指到别处）——**没找到**。
2. **`docs/README.md` 说 `pipeline/03-contract-delta.md` 有"79 处引用"，我数到 31 处**。差异原因未查清（我用的是 ripgrep 默认忽略规则，可能少算了被忽略目录；但 79 这个数也没给枚举命令）。**两个数都不该直接转述。**
3. **`eval/recall-funnel/` 22 个子目录 / 363 个文件，只读了 README 与结构**，没读各实验的 `REPORT.md` / `verdict.json` / 结果 json。所以"19 个实验各自试了什么、判决是什么"只有 README 索引级别的信息。
4. **gov-qa 隐私只抽了 3 / 594 个 `.jsonl`（663 条，约占 0.17%）**。结论只对这三个文件成立。`assets-netizen-comments.jsonl`（网友跟帖）**未抽样**，而那批更可能有真人表达。
5. **`data/*.rotation`（2 个文件）未读**，原因：没有任何文档说明它的语义，读内容也判不出来源。
6. **`tools/gov-qa/` 有大量未提交改动**（`git status --short tools/gov-qa` 里 `M` 与 `??` 混着几十项，含 `assets-*.json`、`recon/coverage-matrix.*`、`locate-rate.json`）。所以它的"当前状态"**不能当已提交状态引用**。
7. **`tools/gov-qa/gate/check.sh` 与运行时真源 `D:/AI/output/check.sh` 是否仍字节一致——未核**（那台路径不在本仓，本机 `D:/AI/output` 我没访问）。`gate/README.md` 自己给了一条同步判据：`(Get-FileHash D:/AI/output/check.sh).Hash -eq (Get-FileHash tools/gov-qa/gate/check.sh).Hash`。
8. **`eval/golden/` 是否历史上被用于调参** —— `docs/research/wikiskill-integration-assessment.md` 记「`eval/golden/golden.json` 是否**真的**在历史上被用于调参 ⇒ **未核**，我只核了它在仓内可读」。我同样未核。
