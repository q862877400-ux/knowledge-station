# B5 门禁复核报告 —— 「环境白名单只增不减」的修法（含门禁临时目录自清）

复核代理（独立，非本批作者）。冻结树 `D:\AI\work space\zcode-verify-b5`，tag `verify-freeze-b5-gate`。

## 0. 机械前提（先做，原始输出）

```
git merge-base --is-ancestor 4ed4b0d verify-freeze-b5-gate   →  ancestor_exit=0   ✅ 方向成立
开工 rev-parse HEAD : ae6470452da0956fdbb614eed557f513200b7e9c
开工 status --short : (空)
rev-list --count 4ed4b0d..verify-freeze-b5-gate = 3        ✅ 与任务书一致
收工 rev-parse HEAD : ae6470452da0956fdbb614eed557f513200b7e9c   （未变）
收工 status --short : (空)
收工 git diff --exit-code : diff_exit=0   （工作树与冻结 tag 字节一致）
区间改动面：scripts/run-gates.ps1 (+97/-3) · tests/test_gate_baseline_whitelist.py (新, 141 行)
```

复核手段：**唯一整脚本真跑**的是 3 次 `KS_GATES_SELFTEST` 注入档（快档，见 §3）；其余 .ps1 侧结论一律
是「**把关键几段原样抠出来** + 喂**真实输入**（真实 pytest 输出/junit/2341 条真实 node 表）」，每处都标了
「抠出来的」。提取树无 `.venv`/`node_modules` ⇒ 整条 `-Full` 跑不出（与任务书一致）。

---

## 1. A 组：幽灵判据「抓不抓得到 / 会不会误伤 / 会不会被整条绕过」

### A-1 抓得到吗 —— ✅ 成立（真跑）

静态判据实跑（本体，未变异）：

```
& 'D:\AI\work space\zcode\.venv\Scripts\python.exe' -m pytest tests/test_gate_baseline_whitelist.py -q --no-header -p no:cacheprovider
E  assert not ['environmental_skip_nodeids 里 `tests.test_compliance::test_behavior_review_face_collection`']
FAILED tests/test_gate_baseline_whitelist.py::test_gate_baseline_skip_lists_have_no_vanished_nodes
1 failed, 1 passed in 0.07s          ← 与父代理复跑一致
```

- **假阳性 = 0**：点名清单里**只有**那一条既有幽灵，白名单另外 5 条一条没被点名。
- 判据不是在跳过：该文件无 skip 标记，实测 `1 failed, 1 passed` ⇒ 2 条都真跑（棘轮「恒真」盲区那条已排）。

.ps1 侧判据（抠自 `run-gates.ps1:334-342`、`:403-406`）喂**真实全表**（`pytest --collect-only -q` 的 2341 条，
换算规则先对**真 junit** 自校过：40 条 0 差异）：

```
allNodeIds = 2341 条
环境白名单 6 条；判为幽灵 1 条：
  GHOST: tests.test_compliance::test_behavior_review_face_collection
```

⇒ 两条路**各自独立**都只抓到那 1 条。**无假阳性**。

### A-2 误伤吗（更危险的方向：删掉合法条目）—— ✅ 成立（真实三类条目全判「在」）

注入三类**真实存在**的条目，判据与剔除逻辑（抠出来的）判定：

```
alive=True   tests.test_pipeline::test_real_middle_json_integration                ① 普通模块级
alive=True   tests.test_answer_materials.TestAnswerIntegration::test_material_...  ② 类里的用例
alive=True   ::tests.test_b5_probe_modskip                                         ③ 收集期跳过（真形态）
剔除 0 条
```

②③ 的 junit 键形态是用**真跑**取证的（探针模块级 `pytest.skip(allow_module_level=True)`）：

```
classname='[]'                                             name='[tests.test_b5_probe_modskip]'      key='[::tests.test_b5_probe_modskip]'
classname='tests.test_answer_materials.TestNoScope...'      name='test_prompt_unchanged_without_materials'  key='tests....TestNoScope...::test_prompt...'
```

⇒ **这三类都不会被误判成幽灵**（HIGH 方向干净）。且配真实全表：6 条里只剔 1 条（那 1 条真幽灵），另 5 条保留。

### A-3 会不会被整条绕过 —— ✅ 不成立 HIGH（两条路不同源，一条被废另一条兜住）

变异：把 `run-gates.ps1:403` 的 `$ghostIds = @($envIds | Where-Object { -not (& $envIdAlive $_) })`
改成 `$ghostIds = @()`（恒不报），然后问「还有没有别的路」。

```
变异后 git diff --stat : scripts/run-gates.ps1 | 2 +-   （1 行）
变异后静态判据实跑     : FAILED ...::test_gate_baseline_skip_lists_have_no_vanished_nodes
                        1 failed, 1 passed     EXIT=1   ← 仍判红
还原后 diff --exit-code : diff_exit=0
```

⇒ **至少一条兜住**，且证据在上：静态那条路用的是「模块文件 + `def`」的**静态扫描**，
.ps1 那条路用的是「这一跑真的收集到没有」的**运行时表**，两者不同源，同一变异废不掉两条。
⇒ 按任务书口径**不判 HIGH**。

---

## 2. B 组：剔除的前提条件 —— ⚠ **结论对、理由错**，并有一条真 HIGH

### B-1 收集错误 ⇒ 剔除不发生 ✅（真跑出现场）—— 但**承重墙不是 `errors==0`**

真实现场：临时造一个 import 崩的测试模块（已还原），用门禁同一套 argv 跑：

```
ImportError while importing test module ... ModuleNotFoundError: No module named 'ks_no_such_module_zzz_for_b5_probe'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.15s                                    EXIT=2
四条门禁正则：(\d+) passed => <no match>   (\d+) skipped => <no match>   (\d+) failed => <no match>   (\d+) error => [1]
junit：classname='[]' name='[tests.test_b5_probe_broken]'  key='[::tests.test_b5_probe_broken]'  error=True
```

⇒ **收集错误会让 pytest 中断整个会话**，输出里**没有 `N passed`** ⇒ `$pytestPassed=$null`
⇒ `:374 if ($null -ne $pytestPassed)` 为假 ⇒ **整块棘轮（含写基线那步 `:432`）都不执行** ⇒ 剔除不发生 ✅。

⚠ **反事实（若剔除真跑了）**：白名单 6 条会被判掉 **6 条**——这就是「收集不全时凭它剔会误删」的真实量级。
但挡住它的是 `$null -ne $pytestPassed`，**不是**新加的 `errors==0`。父代理给的理由（§1.3「剔除前提②没有收集错误」）
在**收集错误**这条路上不是承重的。

### B-2 `errors==0` 真正承重的场景 = **运行期 error**（fixture 崩）✅（真跑）

```
1 failed, 2 passed, 1 error in 0.13s
正则：passed=>[2]  failed=>[1]  error=>[1]
:449 剔除门 = (True) -and (True) -and ([int]errors(1) -eq 0) = False
⇒ 剔除**不发生**（0 条被剔）
```

⇒ 这条门槛**确实有活**，且只在「有 error 但 passed>0（pytest 没中断）」时才是唯一那道门。

### B-3 `errors==0` 而有用例失败 ⇒ 剔除应当仍发生 ✅（死循环确实被解开）

```
1 failed, 41 passed, 1 warning in 7.44s        ← 幽灵那条测试自己红
正则：passed=>[41]  failed=>[1]  error=><no match> ⇒ $pytestErrors 保持 $null
:449 剔除门 = (True) -and (True) -and ([int]errors(null) -eq 0) = True   ← [int]$null 就是 0
⇒ 剔除门打开
```

配**真实全表**跑同一段逻辑：剔 **1** 条（`tests.test_compliance::test_behavior_review_face_collection`），
剩 5 条。⇒ 父代理说的「用 failed 当门槛会变成死循环」成立，改判 `errors` 的**方向正确**。
（本节前一条命令里「剔掉 6 条」是小表子集输入，不是缺陷，见 §6 我自己的噪声。）

### B-4 🔴 **HIGH：剔除门不校验「这一跑收集到的是不是全表」⇒ 合法条目会被整批剔掉**

`errors==0` 只挡「收集**出错**」，挡不住「收集面**被缩小**而没有任何 error」。`PYTEST_ADDOPTS` 是现成的放大器：
门禁脚本**从不清它、也不设它**（`grep PYTEST_ADDOPTS scripts/run-gates.ps1` 唯一命中是 `:473` 的注释里那个
复核反例 `PYTEST_ADDOPTS='-p allskip_plugin'`；`:194` 的 argv 是写死的）。

**真跑**（完全用门禁 `:194` 同一套 argv，只加一个环境变量）：

```
PS> $env:PYTEST_ADDOPTS='-k test_gate_baseline_whitelist'
PS> python -m pytest -q -rs --durations=10 --junitxml=$env:TEMP\b5-verify\shrunk.xml
1 failed, 1 passed, 2339 deselected, 5 warnings in 0.97s        EXIT=1
junit：allNodeIds = 2 条（都来自 test_gate_baseline_whitelist.py）
正则：passed=>[1]  failed=>[1]  error=><no match>
```

喂给 `:449` 的同一段逻辑（抠出来的）+ **真实基线**：

```
总账 totalRan = 1 + 0 + 1 + 0 = 2  <  基线 2333      ⇒ 总账也判红
剔除门 = (True) -and (2 > 0) -and ([int]$pytestErrors() -eq 0) = True
⇒ -UpdateBaseline 会剔掉 6/6 条：
   - tests.test_compliance::test_behavior_review_face_collection      ← 真幽灵
   - tests.test_golden_set::test_qa_retrieval_hits_golden             ← 合法(还在)
   - tests.test_pipeline::test_real_middle_json_integration           ← 合法(还在)
   - tests.test_reranker::test_rerank_real_model_reorders             ← 合法(还在)
   - tests.test_retrieval::test_vec_channel                           ← 合法(还在)
   - tests.test_update_channels::test_live_openstd_homepage_default_transport_200 ← 合法(还在)
```

**5 条合法条目被剔掉 ⇒ 环境白名单被整份抹掉**（`scripts/run-gates.ps1:449`；写盘在 `:460-466`，
**不受 `$baselineDrop` 约束** ⇒ 红跑也照样改写基线文件，只有一行黄色「✅ 白名单剔除 N 条…」+ DarkGray 提示）。
后果是下一跑（不带那个环境变量）里那些**环境性**跳过（fastembed 缺失、模型没缓存、联网用例）
会变成「白名单外的新 skip nodeid」⇒ 红；而这次的门禁存在的意义正是别让这种事消耗人。

- 触发条件（说清楚，不夸大）：`PYTEST_ADDOPTS`（或任何让选择面缩小的机制：`-k` / `--deselect` /
  `--ignore` / `-m` / 改收集的 `-p` 插件）**且** 用 `-Full -UpdateBaseline`。
  **无害的** `PYTEST_ADDOPTS`（如 `-p no:cacheprovider`）不会缩表。
- 按任务书自己的口径「这一类如果剔了合法条目 ⇒ HIGH」⇒ 判 **HIGH**。
- 修法建议（供父代理定夺，我没改冻结树）：① 像钉 `PYTHONIOENCODING` 那样显式**清掉/拒绝**
  `PYTEST_ADDOPTS`（最贴合该脚本既有纪律）；② 或剔除前再加一道「看起来是全表」的校验
  （`$totalRan -ge $baseTotal`）。②的副作用要留意：真「删了用例」时 total 本来就会掉，那种情况恰恰需要剔除
  ⇒ ① 更稳。

---

## 3. C 组：临时目录自清 —— ✅ 三条边界都成立（含**整脚本真跑**）

在冻结树里临时注入 `KS_GATES_SELFTEST=3`（成功 + 自己建数据目录）与 `=4`（失败 + 自建目录）两档，
让**被验脚本自己**跑出成功/失败两条路（跑完已还原，`diff --exit-code=0`）：

```
跑 3（成功档）: MADE C:\...\Temp\ks-gates-data-35744 ; 1/1 步通过 ; EXITCODE(no pipeline) = 0
                ks-gates-data-* 剩几个: 0                       ⇒ 成功 ⇒ 目录**被收掉** ✅
跑 4（失败档）: MADE C:\...\Temp\ks-gates-data-40132
                ⛔ 失败步骤：selftest（失败 + 建自己的数据目录）
                （这一跑没成功 ⇒ 本次的数据目录留着供排查：C:\...\Temp\ks-gates-data-40132）
                EXITCODE(no pipeline) = 1
                留下: ks-gates-data-40132  files=1              ⇒ 失败 ⇒ 留着 + 打印路径 ✅
```

**反向边界（pid 复用）** ✅：把 `$ownDataDir` 变异成固定名 `ks-gates-data-b5probe` 并**跑前先建好** + 放哨兵文件，
再跑成功档：

```
固定目录还在? True   内容=sentinel-keep-me      ⇒ 跑前就存在的那份**一个字都没动** ✅
pid 目录剩几个: 0                               ⇒ 本次那份仍被收掉 ✅
```

**退出码 3（已有门禁在跑）** ✅ 无「本次改动」的副作用：

```
EXITCODE(exit3, no pipeline) = 3
  ⛔ 已经有一个门禁在跑（pid=23124...）⇒ 这次**不跑**，退出码 3。
  锁还在? True        新建 ks-gates-data-* 了吗: 0
```

`$ownDataDir*` 三行捕获在 `:120-122`，`exit 3` 在 `:82`（在 `try/finally` 之前）⇒ 3 档路径根本进不了那段 ✓。

**环境变量恢复** ✅（`finally :540-561` **原样抠出**跑两分支）：

```
prev=哨兵 分支：DATA=[SENTINEL-DATA] MODELS=[SENTINEL-MODELS] HELD=[SENTINEL-HELD] TOKEN=[SENTINEL-TOKEN]
prev=null 分支：DATA=[] MODELS=[] HELD=[] TOKEN=[]        ⇒ 四种都符合预期 ✅
```

新增的收目录块插在「`KS_DATA_DIR` 恢复」与「`KS_MODELS_DIR` 恢复」之间，只读 `$ownDataDir`/`$ownDataDirRemovable`
两个捕获值，**不依赖环境变量、也不改环境** ⇒ 没破坏恢复顺序 ✓。

**⚠ LOW（区间外）：exit 3 仍会删 `ks-gates-junit-*.xml`。** 实测退出码 3 的那一跑打印了
「（清掉 1 份旧的 ks-gates-junit-*.xml）」、我的 dummy `ks-gates-junit-777777.xml` 被删（`Test-Path` → False）。
那段在 `:45-50`，`git diff 4ed4b0d..ae64704 -- scripts/run-gates.ps1 | grep junit` **为空** ⇒ **区间外的既有代码**。
危害窗口：运行中的那跑「pytest 写完 junit」到「棘轮读它」之间，另一次调用会把它删掉 ⇒ 那跑以
`$junitError`（`:324`）判红 = **假红**。登记残余，不在本批定责。

---

## 4. D 组：顺手更正的那段注释 —— ✅ **没写错**（两条都核到原始来源）

更正段在 `scripts/run-gates.ps1:132-138`，它点名两条用例「现在都不存在了」：

| 更正的说法 | 独立核验 | 结论 |
|---|---|---|
| ① `tests/test_compliance.py` **整个文件**随 2026-09-22 的删单批 `683c6f6` 被删除 | `Test-Path tests/test_compliance.py` → `False`；`git show --stat 683c6f6` → `tests/test_compliance.py \| 146 ----`；`git show -s --format=%ci 683c6f6` → `2026-09-22 21:59:13 +0800` | ✅ 准确 |
| ② `test_phase4.py::test_obligation_list_and_checklist` 也已不在（文件还在、那条没了） | `Test-Path tests/test_phase4.py` → `True`；`grep obligation_list_and_checklist tests/*.py` → 0 命中；`git show '683c6f6^:tests/test_phase4.py'` → `def test_obligation_list_and_checklist(rich_db):` 在；`git show --stat 683c6f6` → `tests/test_phase4.py \| 19 --` | ✅ 准确（**且是被同一个 `683c6f6` 删的**，更正里没点出这个因果，可以补） |

⇒ 「留在这里不改会把下一个人引去查一条不存在的用例」这个判断成立；那段更正**没说错**。

**⚠ LOW（文档精确度，`tests/test_gate_baseline_whitelist.py:14-17`）**：那里说幽灵
「被 2026-09-23 的 `-UpdateBaseline` (`4252385`) 原样抄了下来」。核验：

```
git log -S '"tests.test_compliance::test_behavior_review_face_collection"' -- scripts/gates-baseline.json
  → ea31479 fix(gate)+docs: compliance 环境门槛 ...      ← **首次进入**基线（那时用例还在，属合法登记）
git show '4252385^:scripts/gates-baseline.json' | grep test_behavior_review_face_collection
  → 命中 ⇒ 4252385 的**父提交里已经有**这条
```

⇒ 说 4252385「原样抄了下来」**不算错**（它确实又抄了一遍），但它**不是那次才进来的**——`ea31479` 登记、
`683c6f6` 删文件之后，至少 `4252385` 之前的那些 `-UpdateBaseline` 也都没剔。改写成「首次登记于 `ea31479`，
`683c6f6` 删了用例，之后若干次 `-UpdateBaseline` 原样抄回」更准。

---

## 5. 分级汇总

| # | 级别 | 位置 | 结论 |
|---|---|---|---|
| 1 | 🔴 **HIGH** | `scripts/run-gates.ps1:449`（+`:460-466`） | 剔除门只以 `errors==0` 为前提，**不校验收集面是否完整**。`PYTEST_ADDOPTS` 缩小选择面（真跑，`2339 deselected`）时剔除门仍开 ⇒ `-UpdateBaseline` 把**5 条合法条目**当幽灵剔掉，环境白名单被整份抹掉；且基线文件在**红跑**下也被改写。 |
| 2 | 🟡 MED | `scripts/run-gates.ps1:334-342` | `$envIdAlive` 的「按模块兜住」分支是一条**假活**路径：模块以 `::<模块>` 形态在表里时（**收集期跳过**与**收集错误**实测都产生 `classname=""`），该模块内任意名字都判「在」⇒ 该模块里的幽灵不会被剔（方向与静态判据相反）。该兜底对防误伤是**必要**的（见 A-2），所以是「必要但开口」；今天套件里**不可达**（唯一 `importorskip` 在 `test_retrieval.py:307` **函数内**，不产生模块级键）。 |
| 3 | 🟡 MED | `tests/test_gate_baseline_whitelist.py:70-76` | 静态判据**不校验类段**：实测注入 `tests.test_answer_materials.TestNoScopeIsByteIdenticalRENAMED::test_prompt_unchanged_without_materials`（类名改过）后静态判据**不报**（只查模块文件 + `def` 名），而同一条 .ps1 侧判 `alive=False`（正确）⇒ 该盲区在 `-Full` 时被 .ps1 兜住，**不是静默洞**；但两条判据覆盖不同源，叠加 #2 时（模块级跳过 + 类名改过）会同时漏。 |
| 4 | 🟢 LOW | `scripts/run-gates.ps1:45-50`（**区间外**） | exit 3（已有门禁在跑）仍会删 `ks-gates-junit-*.xml`（实测 dummy 被删）⇒ 可能删掉在跑那跑的 junit 让它假红。 |
| 5 | 🟢 LOW | `scripts/run-gates.ps1:331-333` 注释 | 注释说 `::<模块>` 形态来自「**收集期跳过**」；实测**收集错误**也产生同样形态（`classname=''`/`name='tests.test_b5_probe_broken'`）⇒ 描述不全。 |
| 6 | 🟢 LOW | `tests/test_gate_baseline_whitelist.py:14-17` | 幽灵的**出处**写得比事实窄（见 §4）。 |
| — | ✅ 通过 | A-1/A-2/A-3、B-1/B-2/B-3、C 全部、D ①② | 见上文逐条原始输出。 |

**门禁的意义侧面**：`%TEMP%\ks-gates-data-*` 在**本报告开工时计数 = 0**，且 `%TEMP%\ks-gates-last.txt`
（我开工时的原件，已还原）显示 `2026-09-24T01:01:24 门禁（全量 档）· 8/8 步通过 · exit=0` ——
即主仓在 01:01 真跑过一次全量且自清成功。**但主仓此刻有别的代理在改，其源码不算证据**，故仅作为旁证登记。

---

## 6. 我明确**没能**验证的

1. **整条 `-Full` 没跑**（提取树无 `.venv`/`node_modules`，`tsc/mypy/smoke` 都会以「命令不存在」判红）。
   .ps1 侧除 §3 的 3 次 `KS_GATES_SELFTEST` 注入档（快档）外，**一律是抠出来的片段**，已在每处标注。
2. **没跑真库**，全程未碰 `%APPDATA%\KnowledgeStation\database\knowledge.db`。
3. `166 个 / 554 MB` 这个数字**无法独立复现**：开工时 `%TEMP%\ks-gates-data-*` 计数已是 **0**（被清过）。
   只能核到「现在计数 0」与代码里那段注释的存在。
4. **`finally` 里新增的 `Remove-Item -Recurse` 若抛终止错误**，会跳过其后的 `KS_MODELS_DIR`/`PYTHONIOENCODING`/
   控制台编码恢复：只有**代码推断**，我没构造出该终止错误（未跑）。`-ErrorAction SilentlyContinue` 吞的是
   非终止错误，理论上撑得住，但**这属于推断，不算证据**。
5. §5#2 的假活路径**今天不可达**（套件里没有模块级跳过模块）⇒ 判「未来可达」，**不是当前活洞**。
6. `$base` 缺文件 / junit 半截等边角没逐个造现场（`:421-430` 有「没基线 ⇒ 判红」的既有保护，读码确认，未跑）。

## 7. 父代理（本批作者）**说错了**的地方

1. **§1.3「剔除前提②没有收集错误 ⇒ 收集不全时不会误删」**：只在**收集出错**时成立。**无错误但收集面被缩小**
   （`PYTEST_ADDOPTS`）时会误删 —— 真跑实测剔 6/6、其中 5 条合法（§2 B-4，HIGH）。
   这是本批最需要处理的一条。
2. **§2 B「构造收集错误 ⇒ 剔除必须不发生」的机制归因**：结论对，但承重墙是 `$pytestPassed=$null`
   （pytest 收集错误会**中断会话**、输出没有 `N passed`，`:374`/`:432` 整块不执行），**不是**他新加的
   `errors==0`。`errors==0` 真正承重的只有「运行期 error 且 passed>0」那一类（B-2）。
3. **§1.2「拿不到节点表时不判（已由 junitError 判红）」**：读码为真（`:400-401`），但 `:$449` 那条
   **剔除**门只看 `$null -ne $envIdAlive` + `Count>0`，**不看 `$junitError`** —— 即 junit 解析成功但
   `skipNodeIds.Count -ne $pytestSkipped`（`:328` 已置 `$junitError`、判据自认不可信）时，剔除**照样会跑**。
   未构造该现场（列在 §6#6），仅作提示。

## 8. 我自己造出来的两次噪声（留痕，别当缺陷读）

1. 第一次读退出码得过 `EXIT4=0`（失败档）——那是 `pwsh ... | Select-String | Select-Object -First N`
   导致的 `$LASTEXITCODE` 失真。**无管道干净复测 = 1**；exit 3 同样干净复测 = **3**。**不是脚本缺陷。**
2. harness-3 里「③ 收集期跳过 → alive=False」是我**输入**的瑕疵（`collect.txt` 采集于探针建立**之前**，
   表里没有那条键），把键放进表后 ③ = True。已更正，**不是判据缺陷**。

## 9. 最小复现命令（都在冻结树里跑）

```powershell
$tree='D:\AI\work space\zcode-verify-b5'; $py='D:\AI\work space\zcode\.venv\Scripts\python.exe'
# A-1 幽灵被抓到（红 + 只点名它）
Set-Location $tree; & $py -m pytest tests/test_gate_baseline_whitelist.py -q --no-header -p no:cacheprovider
# A-3 杀掉 .ps1 侧那条，静态那条仍红
(Get-Content "$tree\scripts\run-gates.ps1" -Raw) -replace [regex]::Escape('$ghostIds = @($envIds | Where-Object { -not (& $envIdAlive $_) })'),'$ghostIds = @()' |
  Set-Content "$tree\scripts\run-gates.ps1" -NoNewline -Encoding utf8
Set-Location $tree; & $py -m pytest tests/test_gate_baseline_whitelist.py -q --no-header -p no:cacheprovider   # 仍 1 failed
git -C $tree checkout -- scripts/run-gates.ps1
# B-4 HIGH：无错误但收集面缩小 ⇒ 合法条目被剔（剔除门仍开）
$env:PYTEST_ADDOPTS='-k test_gate_baseline_whitelist'
Set-Location $tree; & $py -m pytest -q -rs --durations=10 --junitxml="$env:TEMP\shrunk.xml"   # 1 failed,1 passed,2339 deselected
Remove-Item Env:\PYTEST_ADDOPTS
# 抠出来的判据与流程（原样代码在 $tree\var\tmp\b5-verify-harness*.ps1，可复跑）
pwsh -NoProfile -File "$tree\var\tmp\b5-verify-harness.ps1"    # 真实全表：只判出 1 条幽灵
pwsh -NoProfile -File "$tree\var\tmp\b5-verify-harness2.ps1"   # B 组三条控制流
pwsh -NoProfile -File "$tree\var\tmp\b5-verify-harness4.ps1"   # 恢复行为 + 三向
```

证据文件：`$tree\var\tmp\b5-verify-harness{,2,3,4}.ps1`（`var/*` 已被 gitignore，工作树保持干净），
`%TEMP%\b5-verify\`（真 junit/真输出文本/原件备份）。探针模块（3 个）、临时注入档、基线注入、
`%TEMP%\ks-gates-last.txt`、我自己建的 `ks-gates-data-*` 与失败日志**均已还原/清理**（见 §0 收工机械动作）。
