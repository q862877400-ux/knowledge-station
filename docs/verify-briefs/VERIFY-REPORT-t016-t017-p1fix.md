# 独立复核报告 — T016/T017 P1 修复批次（`doc_stds` 未定义）

- **复核批次**：`t016-t017-p1fix`（对上一批 P1-1 修复的**专项**复核；不重做第 1 批的全量产物读数核对）
- **冻结 tag**：`verify-freeze-t016-t017-p1fix`（annotated tag，`git cat-file -t` = `tag`）→ commit **`3138898020233e7ae23885e59db3fd8dd3db05f7`**
- **对照 tag（未修复）**：`verify-freeze-t016-t017-subsets` → `52a2bc9639c106af32c1182f2ff547db74097828`
- **隔离副本**：`D:/AI/verify-trees/_r9fix2`（`git worktree add` 自冻结 tag；**主仓只读**）
- **复核者**：general-purpose-1（独立复核者）
- **结论**：**PASS（放行）。** 修复真的有效、判据真的有牙、产物真的没变。附 **1 条 P2**（冻结窗口混入 1 个无关 gov-qa 提交）+ 若干登记。

### 首记（本次复核开始时）

```
$ git -C "D:/AI/work space/zcode" rev-parse HEAD
3138898020233e7ae23885e59db3fd8dd3db05f7
$ git -C "D:/AI/work space/zcode" status --short | wc -l
  （18 个已跟踪文件为 M；主仓工作区本就有大量与本批无关的改动 —— 见文末"环境观察"）
```

---

## ① P1-1 真的修好了吗 —— ✅ 是

**改的是什么（副本输入，非代码）**：备份 `eval/reverse-benchmark/benchmark-171.jsonl` 到 `D:/AI/verify-trees/_r9fix2-bench171.bak` 后，改了 2 条**输入**：

| 场景 | 改动 | 目的 |
|---|---|---|
| A（我的） | i=1 `query` → `按 GB 50016-2014 的要求，这个间距该留多少？`；i=2 `query` → `这个参数按 GB/T 99999-9999 该怎么取？` | 一条**库里有**的标准号 + 一条**库里没有**的标准号 |
| B（复现作者 §5.5） | i=1 `query` → 同上；i=2 `gold_std` → `GB/T 99999-9999` | 逐字复现作者 README §5.5 的端到端日志 |

**还原方式**：`restore` = 用 `.bak` **字节级覆盖回写**；之后 `git status --short eval/reverse-benchmark/benchmark-171.jsonl` **空**（无改动）。

### 读数

**场景 A**（`build-v2.py`，`exit=0`，无 Traceback）：

```
自检：带标准号判据可执行（合成提问抽出 1 个形态，验库后 verified=True；空表零命中 ✓）
i=1 aoc=False label=字面零重合 markers={short:False, zero:True, std_no:True,  std_verified:True}
i=2 aoc=False label=字面零重合 markers={short:False, zero:True, std_no:True,  std_verified:False}
markers_all={"short_clause":8,"zero_overlap_char":121,"has_standard_no":2,"has_standard_no_verified":1}
```

⇒ 含库内标准号 ⇒ `has_standard_no=True` **且** `has_standard_no_verified=True`；含库外标准号 ⇒ `has_standard_no=True` 但 `verified=False`。**与要求逐字相符。**

**场景 B**（复现作者 §5.5 日志，`exit=0`）：

```
i=1 aoc=False label=字面零重合 markers={short:False, zero:True, std_no:True,  std_verified:True}
i=2 aoc=True  label=字面零重合 markers={short:False, zero:True, std_no:False, std_verified:False}
counts.answer_out_of_corpus = 1
markers_all={short_clause:8, zero_overlap_char:121, has_standard_no:1, has_standard_no_verified:1}
partition_all={字面零重合:113, 短条款:8, 普通:50}
```

⇒ 与 `README.md §5.5` 里作者贴的那段日志**逐字段相同**（文档没有虚报）。

### 对照实验（证明"修复确实把崩溃变成了通过"）

用**修复前**（`52a2bc9` 版）的 `build-v2.py` 跑**同一份场景 A 输入**：

```
exit=1
  File ".../build-v2.py", line 170, in main
    _known_standard_keys({standard_key(s) for s in _std_form}, doc_stds))
                                                               ^^^^^^^^
NameError: name 'doc_stds' is not defined
```

⇒ **修复前当场崩、修复后 exit=0 且判据生效。P1-1 真的修好了。**

---

## ② 自检有牙吗 —— ✅ 三条腿全部有牙

在副本里对代码做 4 组变异，逐条给读数（每做完一组即 `git checkout --` 还原，见每组后"已还原"）：

| # | 变异 | 结果 | 拦在哪 |
|---|---|---|---|
| **M1** | 把 `doc_stds` **定义行改名**（`doc_stds_RENAMED`），其余引用不动 | `exit=1` | `line 86`（`std_of_key`）`NameError: name 'doc_stds' is not defined` |
| **M1b** | 外科式：把 `std_of_key` **还原成旧写法**（使 `doc_stds` 只剩"自检"一个引用；本批 0 命中 ⇒ 主循环里那条分支走不到） | `exit=1` | **`line 96`（自检本体）** `NameError` ⇒ **自检自己就拦得住** |
| **M2** | `_STD_IN_QUERY_RE` 改成**永不匹配**（`re.compile(r"NEVER_MATCH_XYZ_12345")`） | `exit=1` | `line 94`：`AssertionError: 自检失败：_STD_IN_QUERY_RE 认不出 GB 50016-2014（形态正则被改坏了？）` |
| **M3** | `_known_standard_keys` 改成**恒真**（`return set(want_keys)`，验库闸退化） | `exit=1` | `line 98`：`AssertionError: 自检失败：_known_standard_keys 对空 doc_stds 竟返回命中 ⇒ 验库闸没在筛` |

- **M1 的读法要说清**：单纯改名，失败点是 `line 86` 而不是自检 —— 因为修复把 `std_of_key` 也改成由 `doc_stds` 派生（一次查询两用），`doc_stds` 因此落到了**主路径**上，改名必然当场炸。这本身是好事（更早暴露），但它**不能单独证明自检有牙** ⇒ 所以才补做 M1b：把 `doc_stds` 逼回"只有自检引用"的状态，**自检仍在 `line 96` 当场拦截**。
- **结论**：正则坏掉（M2）、变量缺失（M1b）、验库闸退化（M3）三种失效模式，自检**各自当场失败、绝不静默通过**。**自检有牙。**
- 4 组变异后均 `git checkout --` 还原；收工时 `git status --short` 为空（见文末尾记）。

---

## ③ 产物真的没变吗 —— ✅ 是（逐行递归比 key 路径，0 差异）

**改动面（`git diff --name-only 52a2bc9 3138898`）**：

```
docs/DEVELOPMENT-HISTORY.md
eval/recall-funnel/README.md
eval/recall-funnel/REPORT.md
eval/recall-funnel/build-v2.py
specs/002-recall-funnel/tasks.md
"tools/gov-qa/data/hb-hdjl-湖北省人民政府·政民互动.jsonl"     ← 见 P2-1
```

- 限定在 `eval/recall-funnel/` 内：**只有** `README.md` / `REPORT.md` / `build-v2.py`（**文档 + 代码**）⇒ **本批 5 个产物一个都没进 diff**。`src/` / `plugin/` / `tests/` 区间内**零改动**。
- 区间共 **3 个提交**（`git rev-list --count 52a2bc9..3138898` = 3）：`8bb26a7`（纯文档）、`9bca65d`（gov-qa 数据，**无关**）、`3138898`（修复）。

**重跑三步链条**（副本，`build-v2.py` → `clean-v3/03-merge-tiers.py` → `summarize.py`，三步 `exit=0`），与**冻结产物**做"逐行 `json.loads` 后递归比 key 路径"（**不比字节、不看 git diff 行数**）：

| 产物 | 差异 |
|---|---|
| `benchmark-v2.jsonl`（171 行） | **0** |
| `benchmark-v3.jsonl`（171 行） | **0** |
| `benchmark-v2-stats.json` | **0**（ADDED/REMOVED/CHANGED 全 0） |
| `clean-v3/tier-stats.json` | **0** |
| `funnel-summary.json` | **1** —— 仅 `meta.source` 的**绝对路径**（我在副本里跑 ⇒ 路径不同，**预期内**）；其余逐键相同 |

⚠ 说明：本次真库在冻结前后**未增长**（`same_def_docs` 活计数一致），所以连那条"活计数"也没有差异 —— 比第 1 批的结论更强。

⇒ **作者"五个产物与修复前逐字段完全一致"属实**（除副本路径这一处预期差异）。

---

## ④ 文档措辞有无残留旧话 —— ✅ 无"与代码不符"的残留（1 条登记）

- **`eval/recall-funnel/README.md`**
  - §五 表：`带标准号` 一行已从"与通道 A 的真实触发条件同一把尺子"改成 **"复用生产通道 A 的两件：`_STD_IN_QUERY_RE` + `_known_standard_keys`；⚠ 本批提问命中 0/171 ⇒ 这条判据本批未行使"** ⇒ 与修复后代码**一致**。
  - §5.5：P1-1/P2-1/P2-2 三条 + 端到端日志 —— 日志我已**逐字段复现**（见 ① 场景 B），**未虚报**。
- **`specs/002-recall-funnel/tasks.md`** T016/T017：与代码一致；T016 含 P1-1 更正块、T017 含 P2-1 更正（`113→108/50→53` → `8→7/113→111/50→50`）。
- **`docs/DEVELOPMENT-HISTORY.md`**
  - §10.213（新增）：与代码一致。
  - §10.212：**保留了原句**"与通道 A 的真实触发条件同一把尺子"，但**同一格后文**明确更正为"本文前面写的'与通道 A 同一把尺子'**在代码里不成立**"（本仓"保留旧话 + 就地更正"惯例）⇒ 不构成"与代码不符"的**未更正**残留，但同格内一断言一更正、读起来略绕。**登记（P2-2 级，无碍放行）。**

**全仓 grep**：`同一把尺子` 在其它文件里命中均为**无关语境**（`docs/research/*`、`scripts/*`、`tests/*`），非本批残留。

---

## ⑤ 冻结哈希核法 —— ✅ 四个全部对上

命令（**按要求用 `git show <tag>:<path> | sha256sum`**，不碰工作区文件；本仓 `core.autocrlf=true`，工作区 CRLF / blob LF 会假红 —— 已实测：工作区 `sha256sum build-v2.py` = `21af2143…` ≠ blob `15e42e5a…`）：

| 文件 | `git show verify-freeze-t016-t017-p1fix:<path> \| sha256sum`（前16位） | 参考值 | 判定 |
|---|---|---|---|
| `eval/recall-funnel/build-v2.py` | `15e42e5a8bba8f69` | `15e42e5a…` | ✅ |
| `eval/recall-funnel/README.md` | `9c8422e6688cf487` | `9c8422e6…` | ✅ |
| `specs/002-recall-funnel/tasks.md` | `89357b6fa3ecb565` | `89357b6f…` | ✅ |
| `docs/DEVELOPMENT-HISTORY.md` | `fbdbd7e9186a51fb` | `fbdbd7e9…` | ✅ |

---

## ⑥ 孤立 stats 异常 —— ⚠ 机制已复现，但"第 1 批那一次"的具体触发**定不了**

**事实**：冻结产物（`3138898`）里 `benchmark-v2-stats.json` 的 `counts.answer_out_of_corpus = 0`，`benchmark-v2.jsonl` 的 `answer_out_of_corpus=True` 条数 = **0** ⇒ **两者自洽**（上一批冻结 `52a2bc9` 同样都是 0）。

**结构性论证**：`build-v2.py` 里 `counts.answer_out_of_corpus = sum(1 for r in out_lines if r["v2"]["answer_out_of_corpus"])`，而 `benchmark-v2.jsonl` 写的就是**同一份** `out_lines` ⇒ **单次运行内两者必一致**，"1 / 0"**不可能**在单次运行内产生 ⇒ 只能是**跨文件失步**。

**我确定性地复现了 1/0**（机制）：
1. 用场景 B 输入跑 `build-v2.py` ⇒ `stats.aoc = 1`、`jsonl aoc=True = 1`（一致）；
2. **只** `git checkout -- eval/recall-funnel/benchmark-v2.jsonl`（还原 jsonl、**不动 stats**）⇒ `stats.aoc = 1`、`jsonl aoc=True = 0` —— **精确复现"孤立 stats 异常"**。

⇒ **机制 = "部分还原 / 部分覆写 / 并发写"导致 `benchmark-v2.jsonl` 与 `benchmark-v2-stats.json` 失步**（两者由同一脚本先后落盘，任何只碰其中一个的带外操作都会造成）。
**诚实边界**：我能复现**机制**，但**不能证明**第 1 批复核当时那一次就是它（那份沙箱状态已不存在）。**该异常不是冻结产物的缺陷**（冻结产物自洽，且第 1 批复核者自己也判为外部并发/陈旧读）。**此条我给"机制已定位、个例不可证"**。

---

## 发现分级汇总

| 级别 | 编号 | 内容 | 处置建议 |
|---|---|---|---|
| **P0** | —— | **无。** | —— |
| **P1** | —— | **无。** P1-1 已被本批修复并验证有牙。 | —— |
| **P2** | **P2-1** | **冻结窗口混入 1 个无关提交**：`52a2bc9..3138898` 区间含 `9bca65d`（`data(govqa): 湖北门户 hb-hdjl 缺口收口 2356 → 3461`，+1105 行），落在 `tools/gov-qa/data/`，**与本批无关**。⇒ 严格说 `git diff --name-only 52a2bc9 3138898` **出现了 1 个 `.jsonl`**（虽不是本批产物）。**本批 `eval/recall-funnel/` 内零 `.jsonl/.json` 改动**（已单列核对）。 | 登记。派复核时冻结窗口宜只含本批提交（或指明"无关提交不在此列"）。**不影响本批放行。** |
| **P2** | **P2-2** | `DEVELOPMENT-HISTORY.md §10.212` 同格内既保留旧断言"与通道 A 同一把尺子"、又更正为"在代码里不成立"，读起来略绕（本仓 append-only 惯例）。 | 登记，无碍。 |
| **登记** | **E-1** | **验证期间主仓被并发写入**：`src/core/retrieval/hybrid_engine.py`(12:54)、`reranker.py`(12:54)、`src/core/api/server.py`(12:57)、`src/core/vision/local_vision.py`(12:57)、`tests/test_reranker.py`(12:52)、新目录 `eval/recall-funnel/exp-11-rerank-fix/`(12:46–12:58) 等 —— **均非本复核所为**（我对主仓只跑只读 git 命令）。这佐证了本环境**确有并发写者**，与 ⑥ 的"外部失步"假设同源。 | 登记；对**本批无影响**（我在**钉死的 worktree** 里作业）。 |

---

## 诚实边界 / 明确未做

1. **本报告聚焦"修复有没有牙"**，**未重做**第 1 批的全量产物读数核对（按指示）。
2. **未跑** `scripts/run-gates.ps1` / `npm run smoke`（按硬约束）。
3. **未整跑六路漏斗**（`funnel.py` 等读模型/向量的脚本）；本批不需要。
4. ① 的变异是**改副本里的输入**（不是改代码）；② 的变异是**改副本里的代码**（每组已 `git checkout --` 还原，收工 `git status` 为空）。
5. ⑥ 只**复现了机制**，**未能**证明第 1 批那次个例的成因。
6. **真库只读证据**：全程 `uri=True&mode=ro`；`clause_revision = 663,634` 行、`doc_meta = 8,983` 行、主文件 **mtime = 2026-10-09 11:40:48**、size = 3,105,525,760 B —— 复核开始时（≈12:45）与结束时**均为该 mtime**（早于复核开始，未变）⇒ **真库未被写**（本仓一贯做法：行数 + mtime，**无内容哈希基线**）。
7. 报告为**单台机器、单一真库状态**的读数；真库增长会改变 `same_def_docs` 等活计数（本次未变）。

### 尾记（本次复核结束时）

```
$ git -C "D:/AI/verify-trees/_r9fix2" rev-parse HEAD
3138898020233e7ae23885e59db3fd8dd3db05f7
$ git -C "D:/AI/verify-trees/_r9fix2" status --short
  （空 —— 副本已还原到冻结态）
$ git -C "D:/AI/work space/zcode" rev-parse HEAD
3138898020233e7ae23885e59db3fd8dd3db05f7
$ git -C "D:/AI/work space/zcode" status --short | wc -l
  350   ← 较首记增加：均为**外部并发工作流**（rerank 修复）在复核期间写入，非本复核所为
```

**首尾 `HEAD` 一致（主仓 = 副本 = `3138898`）；副本首尾干净；主仓未被本复核改动（仅只读 git 命令）。**
