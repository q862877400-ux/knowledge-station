# tests / tools / 门禁 事实地图

> 调查范围：`tests/`、`tools/`、`scripts/run-gates.ps1`、`scripts/gates-baseline.json`、`pyproject.toml`。
> 方法：只读文件 + `grep`/`Select-String`/`glob` + 两次 `pytest --collect-only`（不执行用例）+ 两次
> **点名 6~4 条用例**的抽样运行（下文逐处标注「抽样」）。**没有跑门禁、没有跑完整 pytest。**
> 每条结论后面括号里是**可搜索的文字 + 文件**。数不出来的写「未读，原因」。

---

## 一、tests 结构分组

### 1.1 文件构成（实测命令与数字）

```
Get-ChildItem -Path tests -Recurse -File | Measure-Object            → 370
  ├─ __pycache__/*.pyc                                               → 182
  └─ 其余 188
        ├─ tests/*.py                                               → 181（含 conftest.py、_kb_folder_api_fixtures.py）
        └─ tests/fixtures/*                                          → 7
```

`tests/fixtures/` 只有 7 个文件：`民法典节选.txt`、`discover_web.json`、`fake.docx`、`fake.pdf`、
`make_law_pdf.py`、`rental-contract.md`、`update_channels.json`。

**只有 2 个测试文件引用 `fixtures/`**（`Select-String -Path tests\*.py -Pattern 'fixtures[/\\]'`）：

- `test_update_channels.py:3` —「应答全部来自 ``tests/fixtures/update_channels.json``」
- `test_update_discover.py:4` —「应答数据来自 ``tests/fixtures/discover_web.json``」

⇒ **夹具库几乎不存在**。绝大多数测试的数据是**用例内现造**（`insert_document` / `insert_clauses` 之类）
或**读磁盘上的产物文件**（`var/`、`eval/`）。

### 1.2 按被测子系统分组

做法：对 181 个 `tests/*.py` 用 AST 抽出 `from src.core.<X>` / `import src.core.<X>`，按子包归类；
**一个文件可以同时属于多个组**（它 import 了多个子包）。下表「文件数」= import 了该子包的文件数。

| 子系统（src.core 子包） | 提到它的测试文件数 | 说明 |
|---|---|---|
| storage | 86 | 库表、连接、文件夹、写队列、备份、密钥 |
| ingestion | 48 | PDF/DOCX 解析、MinerU、条款切分、公式/表格/图注 |
| knowledge | 25 | 分类、标注、法条、`ks_answer`、变更信号 |
| retrieval | 24 | 混合检索、reranker、embedder、FTS、改写尺子 |
| update | 23 | 更新通道、发现、凭据、CCS |
| （src.core 根模块，如 `text_utils`/`config`/`exceptions`） | 23+18+12+11 | 被大量文件间接依赖 |
| domain | 18 | 数据模型 |
| llm | 17 | 模型调用、空返回重试 |
| api | 12 | FastAPI 路由、冷启动、静态资源 |
| materials | 10 | 参考资料收集/入库/去重 |
| settings | 9 | 设置项与覆盖 |
| exports | 8 | 导出、文档渲染 |
| verification | 6 | 校验类 |
| quality | 5 | 质量规则 |
| compliance / supervisor / query / vision / figure_locator | 各 1 | 几乎没覆盖 |

**18 个文件完全 import 不到 `src.core`**（不是孤儿，见 §3.2）：它们测的是 `scripts/`、`eval/`、
`tools/` 里的东西，或纯读已提交的产物文件。

### 1.3 用例总数（实测，不是抄基线）

```
.venv\Scripts\python.exe -m pytest --collect-only -q      → 3076 tests collected
  其中 tests/ 前缀         → 2900
  其中 tools/gov-qa/tests  → 176
```

`pyproject.toml` 的 `testpaths = ["tests", "tools/gov-qa/tests"]`（第 93 行）——gov-qa 的测试
**已经并入根 pytest**，`run-gates.ps1` 里那条注释也这么写。

> ⚠ 3076 ≠ 基线 3065。差额来自**未跟踪的测试文件**：`git status --short tests` 显示
> `?? tests/test_jev_cn_baseline.py`、`?? tests/test_llm_empty_retry.py`、
> `?? tests/test_modality_window_false_positive.py`（另有 `M tests/test_update_announce.py`）。
> 实测这三份的收集数：`--collect-only` 分别 **5 / 3 / 3** = 11 条。
> 3065 + 11 = 3076 ✔ 对得上。基线里 `untracked_excluded: 5` 是**记账那一刻**的数，
> 现在未跟踪的是 11 条 —— 这两个数不一致本身不影响判据（见 §六.4）。

---

## 二、conftest 布的是什么库

`tests/conftest.py` 只有 103 行，四个东西：

### 2.1 `_isolate_data_dir`（session 级、autouse）

```python
td = Path(tempfile.mkdtemp(prefix="ks_test_"))
old = os.environ.get("KS_DATA_DIR")
os.environ["KS_DATA_DIR"] = str(td)
from src.core import config
config.reset_settings()
```

**每一个 pytest 会话开头，把 `KS_DATA_DIR` 换成一个全新的空临时目录。** 收尾时
`close_thread_connection()` + `close_all_connections()` + `gc.collect()` 后删掉该目录，
删不掉就 `raise AssertionError`（注释原文：「清理失败**不许静默**」）。

⇒ **结论：门禁跑的 pytest，数据库永远是空库。** 这一点由代码自己写死在注释里
（`tests/test_catalog_hidden_retrieval.py` 的类注释）：「`tests/conftest.py` 的会话级 fixture 把
`KS_DATA_DIR` 指到**临时库**……⇒ 在 pytest 里，`get_settings().db_path` **永远不是生产库**
⇒ "拿真库跑检索"这件事**在测试套件里结构上做不到**。」

### 2.2 `db` fixture（函数级，非 autouse）

```python
init_schema()
ensure_additive_columns()          # clause_repo
ensure_material_columns()          # material_repo
yield get_db_connection()
```

它**只建表，不填数据**。注释解释了为什么必须调 `ensure_additive_columns()`：
「生产是 `create_app()` → `init_schema()` → `ensure_additive_columns()`……这个 fixture 以前只做前两步，
于是 `catalog_hidden` 那类**不在 schema.sql 里**的追加列**不存在**——结果是一条**顺序依赖的假绿**」。

### 2.3 `client` fixture

`create_app(token)` + `TestClient`，token 固定 `"test-token-123"`，返回 `(client, token)`。
同样是空库。

### 2.4 `_rerank_offline_for_tests`（函数级、autouse）

```python
if "reranker" in request.node.name:  yield; return
monkeypatch.setattr(reranker, "is_available", lambda: False)
```

**除名字里带 `reranker` 的用例，全量测试的 reranker 被强制关掉**，走 R30 降级路径。

### 2.5 有多少用例摸过这个库

AST 统计（`def test*(...)` 的形参里是否有 `db` / `client` / `seeded_db`）：

| 分类 | 条数 |
|---|---|
| 全部 `def test*` 函数 | 2536 |
| 形参里带 `db` / `client` / `seeded_db` | **603** |
| 不带（纯函数、纯文件、纯静态扫描） | **1933** |

`seeded_db` 不是 conftest 提供的，它在 `tests/test_retrieval.py:23` 里**本地定义**，
数据也是用例自己 `insert_clauses` 灌的。

⇒ **这 603 条跑在「临时目录里的、schema 建全的、内容为空的库」上；那 1933 条连库都不碰。**

---

## 三、覆盖率缺口：0 测试的 src 模块清单

### 3.1 `src/core/` 模块清单与「0 命中」

```
Get-ChildItem src\core -Recurse -File -Filter *.py | 去掉 __pycache__   → 155
  其中 __init__.py                                                      → 18
  非 __init__ 模块                                                      → 137（basename 全部互不相同）
```

做法：取这 137 个 basename，逐个在 `tests/*.py` 的**全文**里做子串匹配（`Select-String -SimpleMatch`，
等价于对拼接全文跑正则）。命中数分布：

| 命中次数 | 模块数 |
|---|---|
| 0 | **8** |
| 1–2 | 16 |
| 3–5 | 15 |
| 6–20 | 37 |
| >20 | 62 |

**0 命中的 8 个模块（完全没有任何测试提到过它们）**：

| 模块 | 路径 | 是否活代码 |
|---|---|---|
| `figure_redraw` | `src/core/figure_redraw.py` | 活：`server.py:700`、`local_vision.py:72`、`main.py:46` |
| `formula_locator` | `src/core/formula_locator.py` | 活：`server.py:745` |
| `mohurd` | `src/core/update/channels/mohurd.py` | 活：`update/channels/__init__.py:52`、`plugin/scripts/smoke-channels-ai.mjs:120` |
| `proxy_rotate` | `src/core/update/channels/proxy_rotate.py` | **全仓 1 处引用**（自身模块名），疑似死代码 |
| `routes_law` | `src/core/api/routes_law.py` | 活：`server.py:3239/3241` |
| `routes_settings` | `src/core/api/routes_settings.py` | 活：`server.py:3253/3254` |
| `routes_update` | `src/core/api/routes_update.py` | 活：`server.py:3239/3240`、`scheduler_runner.py:11` |
| `span_verify` | `src/core/ingestion/span_verify.py` | 活：`pipeline.py:2374` |

**注意口径**：这里判的是「测试文本里有没有出现过这个名字」。8 个里 7 个是活代码、被 `server.py`
或 `pipeline.py` 调用 —— 也就是说它们**通过 API 端到端测试可能被间接执行到**，但**没有一条用例
是为它们写的**，也没有任何断言专门盯它们的行为。这是「间接跑到」不是「被测」。

**弱覆盖（只被提到 1–2 次）的 16 个**：`mem_gov`、`routes_channels`、`routes_ingest_preview`、
`routes_kb_folders`、`span_calibration`、`std_samr_hb`、`term_bridge`、`web_fallback`、
`write_queue_bootstrap`、`class_outcomes`、`docx_adapter`、`figure_locator`、`impact`、
`local_vision`、`middle_locator`、`routes_materials`。多数只有**一个 import 语句**命中
（例如 `routes_channels` 只在 `test_naming_convention_scanner.py:126` 作为字符串出现）。

### 3.2 孤儿测试：有测试、`src/` 里找不到对应模块

按「`from src.` / `import src.` 解析出的路径在 `src/` 下是否存在」判：

```
AST 抽出 1094 条 src.* import，去重 87 个不同模块
逐条 Test-Path 解析 .py / __init__.py           → 解析不到：0 条
```

**⇒ 严格意义上的孤儿测试：0 条。** 但有一类**名义上不孤儿、实际上没测本仓 `src/`** 的文件：
18 个文件全文不出现 `src.`（`grep -L 'src\.' tests/*.py`）。它们测的是别的东西：

| 文件 | 实际被测对象 |
|---|---|
| `test_credential_readers_scan.py` | `scripts/ks-credential-readers-scan.py` |
| `test_naming_convention_scanner.py` | `scripts/docs/scan-rename-targets.py` |
| `test_gates_tracked_total.py` | `scripts/gates-tracked-total.py` |
| `test_gate_baseline_whitelist.py` | `scripts/gates-baseline.json` 的静态扫描 |
| `test_run_gates_ratchet_wiring.py` | `scripts/run-gates.ps1` 的静态扫描 |
| `test_pool_depth_ruler.py` / `test_fused_rewrite_ruler.py` / `test_query_rewrite_ruler.py` | `eval/recall-funnel/exp-1x/run.py` |
| `test_embedding_rebuild_resume.py` | `eval/recall-funnel/exp-17-.../rebuild-shadow.py`（通过 `importlib` 加载） |
| `test_loop2_driver.py` / `test_loop2_oracle.py` / `test_loop2_vlm.py` | `scripts/loop2/*.py` |
| `test_real_question_ruler.py` | `eval/real-question-ruler/ruler-v1.jsonl` + `stats-v1.json`（**读产物，不跑 build**） |
| `test_jev_cn_baseline.py` / `test_label_gap_not_jev.py` / `test_rag_gate_not_adopted.py` / `test_measure_harness.py` / `test_long_clause_tail_ruler.py` / `test_govqa_label_review.py` | `var/tmp/` 下的量测产物 / `eval` 产物 |

**这一类里有几条**是「测脚本/测产物」，**不是**测 `src/core/` 的行为。它们有效，但
`test_real_question_ruler.py` 自己的注释把代价写明了：「本测试**不能**发现 build.py 的代码被改坏了
但产物没重跑」。

---

## 四、门禁 12 步逐条

`scripts/run-gates.ps1` 共 815 行。`Add-Step` 调用实测如下（`Select-String -Pattern 'Add-Step'`）。

### 4.1 `-Quick`（4 步）+ `-Full`（12 步）

`-Full` 跑的是**前 4 步 + 后 8 步**；`-Quick` 只跑前 4 步。

| # | 步骤名（脚本原文） | 验的是什么 | 能不能被绕过 | 失败会拦什么 |
|---|---|---|---|---|
| 1 | `tsc（客户端类型）` | `npx tsc --noEmit -p plugin/client` —— 只编 `plugin/client` 下的 `*.ts`/`*.tsx`（`plugin/client/tsconfig.json` 的 `"include": ["*.ts", "*.tsx"]`） | **不能轻易绕**：`tsc` 退出码非 0 即红。但**只覆盖客户端**，`plugin/src/*.js` 完全没有类型检查 | 客户端类型错 ⇒ 整次门禁红 |
| 2 | `mypy（引擎类型）` | `python -m mypy`，`[tool.mypy] files = ["src"]`，非 strict（`check_untyped_defs`/`warn_redundant_casts`/`no_implicit_optional`） | **只覆盖 `src/`**。`tests/`、`scripts/`、`eval/`、`tools/` **零类型检查** | `src/` 类型错 ⇒ 红 |
| 3 | `verify:commands` | `npm run verify:commands` → `plugin/scripts/run-verify-commands.mjs` → 从 **DSH 检出**跑 `verify-commands-real.mjs`（要 `KS_DSH_CHECKOUT`，缺省 `D:\AI\DSH\deepseek-harness`） | 检出不存在时 `process.exit(2)` ⇒ **判红不跳过** | 检出不在 ⇒ 红（不是 skip） |
| 4 | `pssa-guard（命令层）` | PSScriptAnalyzer 只判**两条规则**：`PSUseDeclaredVarsMoreThanAssignments` + `Severity=ParseError/FileReadError`，只扫 `scripts/` 下的 `.ps1` | **覆盖极窄**，脚本自己写死了：「**只抓得住"7 个读取点全改回、只留赋值点"那一种**。实测：8 处里**任意一处**单独改回 `$totalRan` ⇒ **0 命中**」。PSSA 未装 ⇒ `exit 2` 判失败 | `run-gates.ps1` 里变量算了没人用 ⇒ 红 |
| 5 | `smoke（全链）` | `npm run smoke` → `plugin/scripts/smoke-all.mjs`（`plugin/scripts/` 下共 **56** 个 `.mjs`） | 走真浏览器/真链路的套件（`smoke-kb-pad-pixels`、`smoke-kb-cols`、`ui-badge-pixels`）**没浏览器就是红**（AGENTS.md 明写） | 任一冒烟套件失败 ⇒ 红 |
| 6 | `pytest（引擎用例）` | `python -m pytest -q -rs --durations=10 --junitxml=… --basetemp=…`，收集 `tests` + `tools/gov-qa/tests` | 见 §六.4 的棘轮分析 | 用例失败 / 棘轮被破 ⇒ 红 |
| 7 | `引擎门禁（uvicorn）` | `scripts/verify-engine-uvicorn.py`：真 socket + 真 uvicorn，验 `/health` 三态、并发下轻请求 p95、`FileResponse` 字节数与 sha256、坏 JSON 422 | 该脚本自己声明安全边界：「监听 `127.0.0.1` + **随机空闲端口**；`KS_DATA_DIR` 指向**临时目录**」 | 引擎层回归 ⇒ 红 |
| 8 | `verify-tools-real（真 ToolRuntime）` | `plugin/scripts/verify-tools-real.mjs`：用**检出里真** `@deepseek-ai/dsh-tools` 的 `ToolRuntime` 走真 `register()`/`schemas()`/`execute()` | 检出找不到**判红并明说**，「不许静默退回本仓那份 peer 副本」 | 工具 schema 被宿主拒 ⇒ 红 |
| 9 | `真宿主 e2e（临时 profile）` | `plugin/scripts/e2e-install-compose.mjs`：临时 `$DSH_HOME`、真 `dsh plugin add`、真假引擎 + 假 OpenAI 网关，断言 6 个 `ks_` 工具全被 offer、`ks_ping` 真执行 | 同上，需要检出 + `node` | 插件挂不上 / 工具没注册 ⇒ 红 |
| 10 | `gov-qa 质量闸门` | `tools/gov-qa/recon/gate-quality.py --quiet`：四项判据（答复为空 / 内容重复 / 时间倒置 / 标签口径分裂），「**只读，不写任何数据**」 | 见 §五 | 语料质量退化 ⇒ 红 |
| 11 | `gov-qa 幂等验证` | `tools/gov-qa/recon/verify-idempotent.py --quiet`：拿**已落盘真实语料**重放 `poll_one`，验连续两次轮询第二次 0 新增 | 同上 | 通道幂等失效 ⇒ 红 |
| 12 | `gov-qa 通道台账最新` | `tools/gov-qa/recon/gen-channel-table.py --check --quiet`：`SITE-REGISTRY.md` 的受管区块是否最新 | 同上 | 台账过期 ⇒ 红 |

### 4.2 `selftest（必失败）` 那两步是干什么的

**它们不在正式档里。** 脚本第 225–237 行：

```powershell
if ($env:KS_GATES_SELFTEST -eq '1') {
  Add-Step 'selftest（必失败）' $py @('-c', "print('FAIL  selftest-assertion'); import sys; sys.exit(7)") $repo
} elseif ($env:KS_GATES_SELFTEST -eq '2') {
  Add-Step 'selftest（命令不存在）' 'ks-no-such-command-xyz' @('--nope') $repo
} elseif ($env:KS_GATES_SELFTEST -eq '3') {
  Add-Step 'pssa-guard-selftest（门禁自测）' 'pwsh' @('-NoProfile','-File', scripts\pssa-guard-selftest.ps1) $repo
} else { …正式 4 步 + 8 步… }
```

- **`selftest（必失败）`（`KS_GATES_SELFTEST=1`）**：故意跑一条 `sys.exit(7)` 的 python 命令。
  目的是验证**门禁自己**在失败时会不会打印「失败行 + 完整日志路径」。注释写得很直白：
  「第一版用 `cmd /c "… ; exit 7"`，cmd 不认 `;` 作分隔符，**第一版自检因此"通过"了**
  （自检工具自己不可信，等于没自检）」。
- **`selftest（命令不存在）`（`KS_GATES_SELFTEST=2`）**：故意用一个不存在的命令
  `ks-no-such-command-xyz`。治的是假绿：「原来直接 `& $s.exe @(…)`；命令不存在时它是
  **非终止错误**，不会写入 `$LASTEXITCODE` ⇒ `$code` 拿到的是**上一步残留的退出码**（常常是 0）
  ⇒ 这一步被判"通过"。受害面恰好是最要紧的地方：**提取树里没有 `.venv`**」。
- **`pssa-guard-selftest（门禁自测）`（`KS_GATES_SELFTEST=3`）**：跑 `scripts/pssa-guard-selftest.ps1`，
  给 pssa-guard 三条行为锁（T1 原样件 exit 0 / T2 注入未用变量 exit 1 且带文件名+行号 /
  T3 注入语法错误 exit ≠ 0）。注释：「只在自检档跑、**不进正式档**——它专门测门禁本身，
  每次门禁都自测会拖慢且无意义」。

⇒ **这三条不是"必失败的两步"，是三个互斥的自检开关。** 12 步正式档里一条都没有。

### 4.3 棘轮（不在 12 步里，但决定整体退出码）

脚本第 470–731 行是独立的「只涨不跌」判定块，**只对 `-Full` 生效**（`-Quick` 那行明写
「快档不含 pytest 棘轮」）。它判四件事：

1. `$totalForRatchet < $base.pytest_total` ⇒ 红
2. 出现基线里没有、也不在环境白名单里的 skip nodeid ⇒ 红
3. 环境白名单里有**这一跑根本没收集到**的节点（幽灵条目）⇒ 红
4. junit 解析失败 / junit 认出条数与汇总不符 ⇒ 红
5. `-Full` 下拿不到 `N passed` ⇒ 红（第 715–731 行）

---

## 五、tools/ 是什么

### 5.1 规模（实测）

```
Get-ChildItem tools -Recurse -File            → 3427 个文件，948.8 MB
```

### 5.2 是什么

`tools/gov-qa/` 是**另一条线**：政务问答语料采集。`tools/gov-qa/README.md` 开头：

> 把**部委 / 省市**官网上的「公众问答 / 常见问题 / 留言答复」扒下来，整理成**统一的记录格式**，
> 再切成**两类资产** —— ① 点名的依据**在我们库里**的 ⇒ **可当考卷**（测检索准不准）；
> ② 点名的依据**不在我们库里**的 ⇒ **补料清单**。

- 入口：`tools/gov-qa/harvest.py`（`--list` / `--site <key>`），另有 `measure-locate-rate.py`、
  `coverage.py`、`poll.py`、`health.py`、`state.py`、`channel.py`、`regions.py`。
- 自报规模（README）：「**40,943 条 / 94 个来源 / 覆盖 31 个省级行政区**」。
- 它自己的测试：`tools/gov-qa/tests/`，23 个 `.py`（**全部受 git 跟踪**），AST 统计 **176 个
  `def test*`**，与 `--collect-only` 数出的 176 条一致。

### 5.3 它凭什么进本仓门禁

三处接入，都是**明确的代码事实**：

1. **`pyproject.toml:93`**：`testpaths = ["tests", "tools/gov-qa/tests"]`。注释解释动机：
   「`tools/gov-qa/` 建了 4 天 297 个提交、39.5 万条数据，但**根 pytest 一步都不收它**……
   它的测试此前靠"人记得跑"。」
2. **`run-gates.ps1:266`**：`gov-qa 质量闸门` → `gate-quality.py --quiet`。**不是 pytest**，
   根 pytest 收不到。
3. **`run-gates.ps1:273`**：`gov-qa 幂等验证` → `verify-idempotent.py --quiet`。脚本注释写明
   为什么非要有它：「`tests/test_poll.py` 的假适配器用 `source == 通道 key` ⇒ **恰好命中旧判据**，
   抓不到"真实语料里 source 是子源"这个缺陷（实测该缺陷让 33 个通道、124,762 条记录的幂等性失效）」。
4. **`run-gates.ps1:279`**：`gov-qa 通道台账最新` → `gen-channel-table.py --check --quiet`。

另有 `tools/gov-qa/gate/check.sh`（bash 版验收闸门，退出码 0/1），**不在本仓 `run-gates.ps1` 里**
——它是 gov-qa 项目自己的 Stop hook 用的，`PROJ="D:/AI/work space/zcode"` 写死在脚本里。

### 5.4 948 MB 的构成，以及受不受版本控制

```
git -c core.quotepath=false ls-files tools   → 2124 个（注意：不加 -c core.quotepath=false 时，
                                                含中文名的文件会被转义，比对会全部失败 ——
                                                我第一次就踩了这个坑，得到 1364/2063 的错误结论）
```

| 分类 | 文件数 | 大小 |
|---|---|---|
| 全部 | 3427 | 948.8 MB |
| **受版本控制** | **2124** | **698.7 MB** |
| 未跟踪（`git status` 里的 `??`，共 740 条） | **1303** | **250.1 MB** |

按目录拆（`git ls-files` 集合 + 实际文件大小求和）：

| 目录 | 文件 | 大小 | 受控 | 未跟踪 |
|---|---|---|---|---|
| `tools/gov-qa/data` | 686 | **644.2 MB** | **686 / 644.2 MB** | 0 |
| `tools/gov-qa/recon` | 1318 | 100.4 MB | 854 / 24.3 MB | 464 / 76.1 MB |
| `tools/gov-qa/assets-*.json`（大文件，如烟台 11 MB、东营 10.2 MB、税务总局 8.5 MB） | 各 1 | 数十 MB | 部分受控 | 部分未跟踪 |
| 其余（`adapters/`、`tests/`、`gate/`、顶层脚本与 md） | — | 约 4 MB | 大部分受控 | 少量 |

**634 MB 的数据，`git ls-files tools/gov-qa/data` = 686 个文件全部受版本控制。**
`.gitignore` 里**没有** `tools/gov-qa/data`（`git check-ignore -v tools/gov-qa/data/x.jsonl` 返回
rc=1，即未被忽略）；`tools/gov-qa/data/` 下是 **594 个 `.jsonl`**（实际语料）+ **90 个 `.cursor`**
（采集水位线）。

**该受吗？** 从本仓已有纪律看，答案是**不该**，证据有三条：

1. 本仓 AGENTS.md 的「搬运与记录」一节要求「一个事实一个归属层」；语料是**采集产物**，
   由 `harvest.py` 重跑即可再生，不是源码。
2. `tests/test_naming_convention_scanner.py` 的注释已经把这块当"外部拥有的数据"处理：
   「**采集数据目录不归命名规范管**（`tools/gov-qa/data/` 的"目录"其实是中文站点名的转义残留，
   **由另一个自动化拥有**）⇒ 必须剪掉」。
3. 现状本身在漏：`git status --short tools` 有 **767 行**（27 modified + 740 untracked），
   每次采集都会让工作树变脏；而 `gates-tracked-total.py` 那套"只算受版本控制的用例"的口径
   说明维护者已经在为"未跟踪文件进基线"付出代价。

⚠ **未读，原因**：这 634 MB 是否含个人隐私/个人信息，我没有逐条看内容，只看了文件名与条数。
语料是政府公开留言答复，风险由谁承担需要业主判断，不是我能从文件推出来的。

---

## 六、验证能力的真实边界

### 6.1 3062 个用例里，多少在真库上跑、多少在空库上跑

**答案：0 条在真库上跑。**

- `tests/conftest.py` 的 `_isolate_data_dir` 是 **session 级 autouse**，每次会话把 `KS_DATA_DIR`
  换成 `tempfile.mkdtemp(prefix="ks_test_")`。它没有开关，没有"如果设了真库就不换"的分支。
- 唯一能碰真库的通道是 `KS_REAL_DB` 环境变量，但用它的 3 个文件
  （`test_catalog_hidden_retrieval.py`、`test_change_signal.py`、`test_label_gap_not_jev.py`）
  **在门禁环境里必然 skip** —— 它们的 skip 文案自己写着「未显式点名真库（设 `KS_REAL_DB=<path>`
  才跑；门禁跑的是临时空库）」。
- 我用点名方式**抽样**跑了 6 条（`test_golden_set::test_qa_retrieval_hits_golden`、
  `test_pipeline::test_real_middle_json_integration`、`test_retrieval::test_vec_channel`、
  `test_catalog_hidden_retrieval::…那6篇真标准…`、`test_change_signal::test_real_db_…`、
  `test_label_gap_not_jev::test_facts_still_hold`）：结果 `2 passed, 4 skipped`。
  **这是抽样，不是全部。**

分类（AST 统计，见 §2.5）：

| 跑在什么上 | 条数 |
|---|---|
| 临时空库（`db`/`client`/`seeded_db` 形参） | **603** |
| 不碰库（纯函数 / 纯文件 / 静态扫描） | **1933** |
| 真库 | **0** |

### 6.2 「写了但永远会过」的测试

#### (a) 显式 `or True` 恒真断言 —— 8 处

`Select-String -Path tests\*.py -Pattern 'or\s+True'` 命中 8 行，其中 **7 行是活代码里的恒真断言**
（第 8 处是 `test_law_source.py:136-137` 的注释，说明那里**曾经**有一条已修）：

| 文件:行 | 原文 |
|---|---|
| `test_appendix_split.py:212` | `assert _CLAUSE_NO_APPENDIX_RE.search("5.2.1 条款内容") is None or True` |
| `test_patches.py:60` | `assert not any(r.clause_revision_id == "pc1" for r in before) or True  # 修正前可能不命中` |
| `test_phase4.py:59` | `assert ids.index("q2") <= ids.index("q1") or True  # 加分存在性由下条保证` |
| `test_phase6.py:195` | `assert "安全监护" in expand_with_alias("安全监护") or True  # 别名扩展本身非空即命中` |
| `test_reranker.py:127` | `assert not hybrid_engine._last_rerank_debug.get("rerank_offline") is False or True` |
| `test_research_report.py:241` | `assert "⚠锚点未验证" in md.split("三、依据")[0] or True` |

（`test_law_source.py:136` 的注释原文：「原来这里是 `assert find_libreoffice() is not None or True` ——
`X or True` **恒真**，是个**空判据**（看着在断言，其实什么都没断言）」。）

**⇒ 6 处活着的恒真空判据。** 它们所在用例的其他断言仍可能失败，但这几行本身**永远不会红**。

#### (b) 全文没有任何断言的测试函数 —— 13 条

做法：AST 遍历每个 `def test*`，检查函数体（含调用的模块级 helper，递归一层）里有没有
`assert` / `pytest.raises` / `pytest.fail` / `pytest.xfail` / `raise AssertionError`。

```
def test* 函数总数            2536
全文无任何断言                 13
断言在 helper 里（算有）         3
```

13 条清单：

| 文件:行 | 函数 | 为什么它仍然是"会过"的 |
|---|---|---|
| `test_embedding_rebuild_resume.py:113` | `test_ckpt_guard_allows_matching` | 只是调用 `RS.ckpt_guard(dict(want), dict(want))`，注释写「不抛」；`ckpt_guard` 在不匹配时 `raise SystemExit`，所以"不抛=通过"**确实是个判据**，只是没写成断言 |
| `test_head_unit_fragment_gate.py:22/25/28/31/34/37/40` | `test_unit_slash_unit` 等 7 条 | 都只调 `self._rej(...)`；`_rej` 里是 `assert not _plausible_clause_head(...)` ⇒ **断言在 helper 里**，这 7 条**不是**空判据（我的第一版扫描把它们误报了，这里更正） |
| `test_middle_schema.py:241` | `test_cloud_guard_accepts_40` | 调 `_validate_middle(p)`，注释「不抛 = 通过」⇒ 有判据，只是隐式 |
| `test_mineru_cloud.py:46` | `test_validate_middle_passes` | 同上，「不抛即通过」 |
| `test_mineru_gpu_lock.py:33` | `test_gpu_lock_释放后_可再次获取` | 两次 `with _gpu_deep_lock(): pass`，「不抛即通过」 |
| `test_mineru_gpu_lock.py:40` | `test_gpu_lock_禁用开关_KS_GPU_LOCK_0_直通` | 嵌套 with，「不抛即通过」 |
| `test_vision.py:9` | `test_image` | **这是一个 `@pytest.fixture`**（第 7 行有 `@pytest.fixture()`），不是测试。我的 AST 过滤器只排除了带 `fixture` 装饰器的函数，这一条**漏网了**（装饰器写法被 `ast.unparse` 命中但没排除干净）——如实登记为**扫描误报** |

**⇒ 修正后的真实数字：「全文没有任何断言的测试函数」= 13 − 7（`_rej` helper 有断言）− 1（fixture 误报）
= 5 条，全部是「不抛即通过」形态**（`test_ckpt_guard_allows_matching`、`test_cloud_guard_accepts_40`、
`test_validate_middle_passes`、`test_gpu_lock_释放后_可再次获取`、`test_gpu_lock_禁用开关…`）。
这 5 条**有真实判据**（被测函数抛错就会红），只是没写成 `assert`。

#### (c) `try/except: pass` 包住断言 —— **0 处**

用脚本扫「`except` 行后面 3 行内同时出现 `pass` 和 `assert`」：`count=0`。

#### (d) `assert True` / `assert 1` —— **0 处**

`Select-String -Pattern '^\s*assert\s+(True|1)\s*(,.*)?$'`：无命中。
`assert not False`：无命中。

#### (e) 「用 `xfail` 把已知缺陷固化成期望」—— 1 处（有意为之，不是假绿）

`test_fts_latin_prefix.py:148` 的 `test_known_false_hit_proper_noun_is_pinned` 用
`pytest.xfail(...)`。注释解释了为什么：「硬断言会把 bug **固化成期望**——哪天规则真的能区分专名了，
那条断言会红、逼人去改测试而不是去欢迎改进。`strict=False` 下规则变好会以 **XPASS** 暴露给人看」。

⚠ **注意**：`pytest.xfail()` 在 pytest 里记为 **xfailed**，既不算 passed 也不算 skipped。
棘轮的总账是 `passed + skipped + failed + errors`（`run-gates.ps1:487`），**xfail 不在这四项里**
⇒ 这条用例**从总账里消失了**。这是口径上的一个真实缺口（见 §6.4）。

### 6.3 被 skip 掉但其实应该跑的：`environmental_skip_nodeids` 11 条逐条

`scripts/gates-baseline.json` 的 `environmental_skip_nodeids` 共 11 条。逐条判：

| # | nodeid | skip 触发条件 | 判定 | 证据 |
|---|---|---|---|---|
| 1 | `test_golden_set::test_qa_retrieval_hits_golden` | ① 装饰器 `skipif(not …exists() and False)` ⇒ **`and False` 恒为假 ⇒ 装饰器永不 skip**；② 函数体 `if not has_gb: pytest.skip("真实库无 GB30871（CI/新环境）")`，而 conftest 给的是空库 ⇒ `has_gb` 恒 False | **真跑不过**（结构上不可能通过） | 抽样实跑输出：`SKIPPED … test_golden_set.py:31: 真实库无 GB30871（CI/新环境）`。`test_golden_criterion.py` 头注把这叫「**三重死闸**」：`skipif` 恒真、conftest 空库、同时登记进两份白名单 ⇒「**它从不运行**」 |
| 2 | `test_pipeline::test_real_middle_json_integration` | `skipif(not Path("var/mineru_cli_out/GB30871-2022识别版/auto/…_middle.json").exists())` | **环境不具备**（本机文件存在 ⇒ 实际会跑） | `Test-Path` 实测 **True**。抽样实跑：`2 passed` 里就包含它（无 SKIPPED 行） |
| 3 | `test_reranker::test_reranker_real_model_reorders` | `if not reranker.is_available(): pytest.skip(offline_reason())` | **环境不具备**（本机模型在 ⇒ 实际会跑） | `var/models/ks/models--BAAI--bge-reranker-base/` 存在，`var/models/ks` 下 `*.onnx` 实测 **2** 个。抽样实跑：`1 passed` |
| 4 | `test_retrieval::test_vec_channel` | `pytest.importorskip("fastembed")` + `if not embedder.is_available(): pytest.skip("向量引擎不可用 (R30 降级路径)")` | **环境不具备** | `var/models/ks/models--Qdrant--bge-small-zh-v1.5` 存在。抽样实跑：`2 passed` 之一 |
| 5 | `test_update_channels::test_live_openstd_homepage_default_transport_200` | `@pytest.mark.skipif(not os.environ.get("RUN_LIVE"), …)` | **默认环境不具备**（要 `RUN_LIVE=1` + 联网） | 抽样实跑：`SKIPPED … test_update_channels.py:413: 可选联网用例：设 RUN_LIVE=1 才实跑`。这是**唯一一条真联网**的 |
| 6 | `test_catalog_hidden_retrieval.Test假样本不进检索::test_假样本不在检索结果里` | `if not os.environ.get("KS_REAL_DB"): pytest.skip("未显式点名真库…")` | **真跑不过**（门禁环境必然 skip） | 抽样实跑：`SKIPPED … test_catalog_hidden_retrieval.py:187` |
| 7 | `…Test那6篇真标准该挡而不是不该挡::test_那6篇真标准只有附录没有正文` | 同上 + `if not rows: pytest.skip("真库没有 catalog_hidden=1 的真标准")` | **真跑不过** | 抽样实跑：`SKIPPED … :146`（另一条同名分支） |
| 8 | `…Test隐藏集合本身被算出来::test_隐藏集合的行为` | 同 6 | **真跑不过** | 抽样实跑：`SKIPPED … :291` |
| 9 | `test_change_signal::test_real_db_backfilled_values_match_rule` | `if not explicit: pytest.skip(...)`；另需 `var/tmp/change-signal-backfill-plan.json` | **真跑不过** | 抽样实跑：`SKIPPED … test_change_signal.py:192: 未显式点名真库（设 KS_REAL_DB=<path> 才跑；门禁跑的是临时空库）` |
| 10 | `test_label_gap_not_jev::test_change_signal_column_exists_after_migration` | `if not _EXPLICIT: pytest.skip(...)` | **真跑不过** | 注释：「门禁的 pytest 跑在 `conftest` 的临时空库上，而本文件的判据全部建立在那 8,983 篇的**真库事实**上」 |
| 11 | `test_label_gap_not_jev::test_facts_still_hold` | 同 10 | **真跑不过** | 抽样实跑：`SKIPPED … test_label_gap_not_jev.py:79` |

**汇总：11 条里**

- **真跑不过（结构上在门禁环境永远 skip）：7 条** —— #1、#6、#7、#8、#9、#10、#11。
  其中 #1 是「三重死闸」，#6~#11 全部是「门禁跑的是 conftest 的临时空库 ⇒ 判据结构上做不到」。
- **环境不具备（本机条件满足时会真跑）：4 条** —— #2、#3、#4、#5。
  其中 #5 要 `RUN_LIVE=1` + 联网，是**唯一一条真联网**的；#2/#3/#4 在本机抽样里**真的跑了且通过**。

⚠ 抽样声明：11 条里我**实跑了 10 条**（第一批 6 条 → `2 passed, 4 skipped`；第二批 4 条 →
`1 passed, 3 skipped`）。**只差 #10**（`test_label_gap_not_jev::test_change_signal_column_exists_after_migration`）
没实跑，只做了 `--collect-only` 确认它存在。**这是抽样，不是全量。**

另：`skip_nodeids` 里还有 2 条（`test_golden_set::test_qa_retrieval_hits_golden`、
`test_update_channels::test_live_openstd_homepage_default_transport_200`），它们与白名单**重复登记**。

### 6.4 棘轮公式能不能被「多加 skip」绕过

#### 公式原文（`run-gates.ps1`）

```powershell
$totalRan = $pytestPassed + [int]$pytestSkipped + [int]$pytestFailed + [int]$pytestErrors   # 第 487 行
$totalForRatchet = if ($caliberOk) { $totalRan - $trackedExcluded } else { $totalRan }        # 第 557 行
if ($totalForRatchet -lt $baseTotal) { $why += "总账 {0} < 基线 {1}…" }                       # 第 563 行
```

#### 分析：**能被"多加 skip"绕过吗？答案是"部分能"，但有三道拦截，且拦截有真实缺口。**

**先看数学**：`$totalRan` 把 `skipped` **算进分子**。所以把一条用例从 `passed` 翻成 `skipped`，
总账**一分不变** ⇒ 公式本身**兜不住"passed → skipped"的翻转**。脚本注释自己承认这点：
「它**兜不住** `passed → skipped` 的翻转（那种翻转下总账恒等不变）——v2 曾把这条写成"总账兜翻转"，
数学上就是错的」。

**拦截 ①：skip nodeid 白名单**（第 572 行）

```powershell
$newIds = @($skipNodeIds | Where-Object { $knownIds -notcontains $_ -and $envIds -notcontains $_ })
if ($newIds.Count -gt 0) { $why += "出现基线里没有的 skip nodeid…" }
```

⇒ 新增一条 skip，nodeid 不在两份名单里 ⇒ **当场红**。这条**有效**。

**拦截 ②：白名单幽灵判据**（第 585 行）—— 防"白名单只增不减"，要求每一条白名单节点
**这一跑真的被收集到**。这条**有效**（`tests/test_gate_baseline_whitelist.py` 另有静态扫描兜底）。

**拦截 ③：`PYTEST_ADDOPTS` / `PYTEST_PLUGINS` 清空**（第 203–213 行）—— 防"从环境缩掉收集面"。
注释记录了复核实测：「只加这个环境变量就能让 `-UpdateBaseline` 把合法白名单条目当幽灵剔掉」。

#### 但真实的绕过口子（按危害排序）

**口子 A（最实用）：先 `pytest.skip()` 一条，再 `-UpdateBaseline` 把它写进白名单。**

流程：把某条用例的断言改成 `pytest.skip("环境不具备")` → 跑 `-Full`（红，因为新 skip nodeid）
→ 跑 `-Full -UpdateBaseline`（**红的跑也会改写基线**）。

证据：`run-gates.ps1` 第 614 行 `if ($UpdateBaseline) { … }` 这段**不在 `if ($why.Count -eq 0)` 里**，
它只受 `if ($null -ne $pytestPassed)` 罩着。第 660–698 行还专门写了「口径没生效时不许把实测总数
写进基线」的护栏，但**没有任何一行阻止"红的跑写基线"**。
`test_gate_baseline_whitelist.py` 的注释把这条**当作既成事实**描述：「`-UpdateBaseline` 把旧白名单
**逐字抄回** ⇒ 名单**只增不减**」，并给了实物标本（`tests/test_compliance.py` 整个文件被删、
名字还在白名单里，经历若干次 `-UpdateBaseline` 一次都没被剔掉）。

⚠ 我没有实跑验证"红的跑能写基线"（那要跑门禁，被任务书禁止）。**这一条是从代码结构读出来的，
不是实测的。**

**口子 B：`skip` 计数与总账**——把一个**大文件**的用例批量加 skip，总账不变、白名单增长。
拦截 ① 只能拦"白名单外的**新** nodeid"，但只要走一次 `-UpdateBaseline`，它们就合法了
（见口子 A）。⇒ **口子 A 是口子 B 的钥匙。**

**口子 C：`xfail` 不在四项里。** 第 487 行的总账 = `passed + skipped + failed + errors`。
`pytest.xfail()` 的结果记为 **xfailed**，**不在任何一项里** ⇒ 把一条用例改成 `pytest.xfail()`，
它既不出现在总账里、也不出现在 skip 名单里 ⇒ **棘轮完全看不见**。
实证形态：`test_fts_latin_prefix.py:148` 已经在用 `pytest.xfail()`。
（`run-gates.ps1` 里搜不到 `xfail` / `xpassed` 任何字样。）

**口子 D：`$trackedExcluded` 是减项，口径没生效时 `$totalForRatchet = $totalRan`（更宽松）。**
脚本注释自己写：「按**实测总数**判（更宽松、**不会假红**）」。所以让口径助手失败
（比如 `git` 不可用、`unmapped > 0`）⇒ 判据自动变松。脚本的补偿是"本跑不许记基线"，
但**只补偿了记账，没有补偿判据本身**。

**口子 E（已堵）：`PYTEST_ADDOPTS`** —— 第 203–213 行清空 + 响亮告警。这条**已修**。

**结论**：
- **单纯"多加 skip"不能直接骗过判据** —— skip nodeid 白名单会当场红（拦截 ①）。
- **但 `-UpdateBaseline` 会把红跑的结果写进基线**（口子 A），于是"先制造 skip、再记账"是一条
  **完整可用的路径**，代价只是多跑一次门禁。
- **`xfail` 完全绕开棘轮**（口子 C），因为总账公式里没有它 —— 这是**公式本身的缺口**，
  比口子 A 更干净，不需要 `-UpdateBaseline`。

---

## 七、永远会过的测试清单

按「哪种形态、几条、在哪」汇总（口径见 §6.2）：

| 形态 | 条数 | 位置 |
|---|---|---|
| `assert … or True`（恒真，永不红） | **6** | `test_appendix_split.py:212`、`test_patches.py:60`、`test_phase4.py:59`、`test_phase6.py:195`、`test_reranker.py:127`、`test_research_report.py:241` |
| `assert True` / `assert 1` / `assert not False` | **0** | — |
| `try/except: pass` 包住断言 | **0** | — |
| 全文无断言、且无任何隐式判据 | **0** | — |
| 全文无断言、但「不抛即通过」有隐式判据 | **5** | `test_embedding_rebuild_resume.py:113`、`test_middle_schema.py:241`、`test_mineru_cloud.py:46`、`test_mineru_gpu_lock.py:33`、`test_mineru_gpu_lock.py:40` |
| 断言在模块级 helper 里（**不是**空判据） | 7 + 3 | `test_head_unit_fragment_gate.py` 的 7 条经 `_rej`；`test_folder_store.py` 经 `expect_code`、`test_bulk_import.py` 经 `_raises_upd` |
| `pytest.xfail` 把已知缺陷固化成期望（有意为之） | **1** | `test_fts_latin_prefix.py:148` |
| **结构上永远 skip 的用例** | **7** | 见 §6.3 的 #1、#6~#11 |
| 默认环境永远 skip（要 `RUN_LIVE=1` + 联网） | **1** | `test_update_channels.py:415` |

**「永远会过」的真实条数 = 6（恒真断言所在的用例）+ 7（结构上永远 skip 的用例）= 13 条**
（按用例算；若按"永远不红的断言行"算，是 6 行）。

⚠ 需要说清的边界：那 6 处 `or True` 所在的**用例**里通常还有其他有效断言，
所以"这条用例永远会过"这个说法**对其中大部分不成立**；成立的只是"**这一行断言永远不红**"。
真正**整条用例永远会过**的，是 §6.3 里那 7 条结构上永远 skip 的（它们连跑都不跑）。

---

## 八、我没搞清楚的

1. **`-UpdateBaseline` 在红的跑里到底写不写基线** —— 我按代码结构判断「写」（第 614 行的
   `if ($UpdateBaseline)` 块不受 `$why.Count` 约束），但**没有实跑验证**（任务书禁止跑门禁）。
   要确认只需：故意让一条用例失败 + 跑 `-Full -UpdateBaseline` + 看 `gates-baseline.json` 的
   `updatedAt` 有没有变。**未做。**

2. **`xfail` 到底在 junit 里怎么记、会不会影响 `skipNodeIds.Count -ne $pytestSkipped` 那条一致性判据**
   —— 我只确认了 `run-gates.ps1` 全文搜不到 `xfail`。`test_fts_latin_prefix.py` 那条 xfail
   如果哪天 XPASS，会变成 **xpassed**（也不在四项里），同样隐身。**未验证 junit 的实际记录形态。**

3. **`tools/gov-qa/data` 那 634 MB 语料是否含个人信息** —— 只看了文件名与条数，**没读内容**。
   该不该受版本控制，我只能从"可再生产物 + 本仓纪律"推出"不该"，但**隐私/合规风险**需要业主判断。

4. **`plugin/src/*.js` 的类型安全面** —— `tsc` 只编 `plugin/client`（`include: ["*.ts","*.tsx"]`），
   `mypy` 只扫 `src`。`plugin/src/` 那批 `.js` 与 `plugin/scripts/` 那 56 个 `.mjs` **没有任何静态类型门禁**。
   它们的行为验证全靠 `smoke` 与两条 `-Full` 的 node 脚本，但我**没有逐个数清**这些冒烟覆盖了
   哪些分支。**未读，原因：56 个 mjs + 34 套冒烟，超出本轮只读预算。**

5. **`src/core/` 里那 8 个 0 测试模块的"间接覆盖"到底有多少** —— 我确认了它们被 `server.py` /
   `pipeline.py` 调用，但**没有追**哪条 API 端到端用例会走到它们。要确认得给每个模块加
   coverage 或用 `--cov` 跑，本轮禁止跑完整 pytest。**未做。**

6. **`tests/` 下 3 个未跟踪测试文件（11 条用例）是谁、为什么没提交** —— 只看到
   `git status` 的 `??`。`test_jev_cn_baseline.py` 在 `gates-tracked-total.py` 的注释里被当作
   "定时炸弹"的标本提过，另两个（`test_llm_empty_retry.py`、`test_modality_window_false_positive.py`）
   没有找到任何说明。**未读，原因：没有 commit 就没有可查的动机。**
