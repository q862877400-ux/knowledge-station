# 独立复核报告 · spec 003「向量通道范围下推修复」

> 复核者：**general-purpose-1（独立复核者）** ｜ 判定：**有条件 PASS**（P0 无；P1 1 条；P2 4 条）
> 所有读数均为**复核者本人实测**；凡未验者均在末节明写。

---

## 0. 冻结与基线（证明验的是冻结树、且未边改边验）

| 项 | 值 |
|---|---|
| 仓库 | `D:\AI\work space\zcode` |
| 冻结提交 | `f5fd5ce`（tag `verify-freeze-spec003-vecscope`） |
| 提取树 | `D:\AI\verify-trees\spec003-vecscope-gp1`（`git worktree add … verify-freeze-spec003-vecscope`，detached HEAD） |
| 冻结窗口 6 提交 | `2a3130a`（立项）/ `d07a32c`（实现）/ `25e17e7`（迁移+更正）/ `f5fd5ce`（归属层）= **本批 4 个**；`6d480ee` / `d5bc982` = **gov-qa 夹带，不在范围**（`git log --oneline d5bcc56..f5fd5ce` 实测） |
| 工具链 | 主仓 venv `python 3.12.14`｜`sqlite_vec 0.1.9`｜`pytest 9.1.1`｜`SQLite 3.53.1`（与 spec 钉的版本**完全一致**） |

**首（开工）**：`git rev-parse HEAD` = `f5fd5cea033b1683ae88e4c09ea60b3347d20f7b`；`git status --short` = **空**（干净冻结树）。
**尾（收工）**：`git rev-parse HEAD` = `f5fd5cea033b1683ae88e4c09ea60b3347d20f7b`；`git status --short -- src/ tests/ specs/ scripts/ pipeline/` = **空**（核心文件零改动）。
> 注：期间**主仓** HEAD 由 `f5fd5ce` 前进到 `f6bb3ef`（他人提交 `68e3574`/`46f45c6`/`f6bb3ef`，属冻结后的续作）。**我未对主仓做任何写操作**；主仓 spec003 三核心文件工作树无改动。

---

## 1. ★ 机制结论（本项复核重点）——**实施者更正后的说法成立；但其"≥2 个 id"旧说法仍残留在 6 处本批产物里**

### 1.1 我的独立判据与读数

复跑 `probes/probe-mechanism.py`（实施者脚本）：

```
近邻N    范围内有向量m | 旧写法 clause_revision_id IN | 新写法 doc_id IN
25/200/2000/20000/100000   1 | 0 行 ❌空   | 1 行 ✅
25/200/2000/20000/100000   5 | 5 行 ✅     | 5 行 ✅
```

⚠ 关键：`m=5` 时**范围子查询同样返回 5 个 id**，旧写法却 **5 行全回来** ⇒ 直接证伪"≥2 个 id 就坏"。
实施者脚本把「子查询返回几个 id（p）」与「其中在 vec 里有几个（q）」**绑在一起扫**（固定 p=5），所以它自己给不出这个区分。

**我另写探针把 p、q 拆开**（`_gp1-probe-mech-split.py` / `_gp1-probe-mech-v2.py`，本人实测）：

```
p      q      | 旧写法 clause_revision_id IN
1      1      | 1 行 ✅
2      2      | 2 行 ✅          ← 证伪"≥2 个 id"
3      3      | 3 行 ✅
5      5      | 5 行 ✅
10     10     | 10 行 ✅
50/100 50/100 | 20 行 ✅（=k 截断，两侧一致）
2      1      | 0 行 ❌（缺 1 个）
3      2      | 0 行 ❌
5      4      | 0 行 ❌
10     9      | 0 行 ❌
100    99     | 0 行 ❌（**只要缺 ≥1 个就整体返回空**）
1      0      | 0 行（正确：范围内本就无向量）
```

多文档形态（真库最可能的现实形态）：

```
范围=[docA(2 条款,全有向量), docB(2 条款,全无向量)] → 旧写法 []（假报没有）｜新写法 ['a_1','a_0']
```

**我给出的判据**：
> **旧写法失效 ⇔ IN 列表里【同时】含「在 `clause_vec` 里有行的 id」与「在 `clause_vec` 里没有行的 id」（部分命中，且 present>0）。**
> 与表大小**无关**（p=q 大表也绿；p>q 小表也红）；与「子查询 vs 字面量」**无关**（两者同命）。

### 1.2 对实施者说法的判定

| 说法 | 我的判定 |
|---|---|
| 「真正的失效条件是**范围里的条款只有一部分在向量表里有向量**」 | ✅ **成立**（= 我的判据；且比"≥2 个 id"精确） |
| 「**与表大小无关**」 | ✅ 成立 |
| 「初版『≥2 个 id 就返回 `[]`』是错的、已自我推翻」 | ✅ **自我推翻正确**（我用旧形状表另证：5 条全有向量 ⇒ 返回 5 行） |
| team-lead 提的「第三种解释」（IN 列表里含 vec0 里没有对应行的 id） | ⚠ **是同一现象的更机械表述，不是竞争解释**；但单说它**略欠精确**——需补"同时有 present>0"（否则 p=1,q=0 会被误判为"坏"，其实返回空是对的）。**实施者的"一部分"措辞反而更准。** |

### 1.3 ★ P1：被自我推翻的说法仍留在 **6 处本批产物**里

`git log -S` 逐处溯源，**全部由 `d07a32c`（本批实现提交）引入**，而更正提交 `25e17e7` **只修了 research.md / spec 背景 / 大白话版 / pipeline 契约增量 / 探针 Q1**，**漏了下面 6 处**：

| # | 位置 | 原话 | 本批? |
|---|---|---|---|
| 1 | `src/core/retrieval/hybrid_engine.py:197` | **≥2 个 id 恒返回 `[]`** | d07a32c ✅ |
| 2 | `src/core/storage/schema.sql:123` | ≥2 个 id 恒返回 `[]` | d07a32c ✅ |
| 3 | `tests/test_contract.py:449` | ≥2 个 id 恒返回 `[]` | d07a32c ✅ |
| 4 | `specs/003-vec-scope-pushdown/plan.md:10` | **≥2 个 id 恒返回 `[]`** | d07a32c ✅ |
| 5 | `specs/003-vec-scope-pushdown/data-model.md:33` | ≥2 个 id 返回 `[]` | d07a32c ✅ |
| 6 | `tests/test_kb_scope_retrieval.py:366`（新多文档判据 docstring） | ≥2 个 id 时行为不同 | d07a32c ✅ |

另：`hybrid_engine.py:200` 把**已被作废的 Q1**（喂文档 id 比条款 id 的无意义查询）列为"复现证据"。
**主仓最新提交 `f6bb3ef` 里这 4 处源码/规格串仍在**（`git grep` 实测），即**冻结后也没修**。
（另有 1 处**属上一批**、非本批责任：`tests/test_kb_scope_retrieval.py:288`，由 `7b75dfa` 引入。）

**性质**：**纯文档/注释**，**不影响运行期正确性**（修复本身是对的）；但本批的**招牌就是"就地更正机制结论"**，留 6 处互相矛盾的说法，会让后来者拿到相反指引 ⇒ 判 **P1**。

---

## 2. 真库现状断言 —— **独立证实**

只读连真库（`sqlite3 uri=True&mode=ro`，读 `clause_vec` 前 `sqlite_vec.load`；脚本 `_gp1-realdb-check.py`，耗时约 3m50s）：

| 读数 | 我实测 |
|---|---|
| `clause_vec` 列 | `['clause_revision_id','doc_id','embedding']`（**有 doc_id**） |
| `clause_vec` 行数 | **663,634** |
| `clause_revision` 行数 | **663,634** |
| clause_revision 有、clause_vec 无的条款 | **0** |
| clause_vec 有、clause_revision 无的孤儿向量 | **0** |
| 有条款、**却一条向量都没有**的文档 | **0** |
| 有条款、**部分**有向量的文档（旧写法会假报没有） | **0** ← 关键 |
| `clause_vec.doc_id` 与 `clause_revision` 不一致 | **0** |
| 回滚源 `clause_vec_pre003`（普通表） | **663,634 行，保留** |

**抽样实跑**（`_gp1-realdb-sample.py`，抽 6 篇含大文档）：条款数 1859 / 1494 / 1480 / 2 / 2 / 2 ⇒ 旧写法**零越界、条数正确**（大文档 20 行=k 截断）。
⇒ **「旧写法现在工作正常」成立**；本项确为**潜在脆弱点**而非当前故障。实施者该断言**属实**。

---

## 3. 修法是否成立 —— **成立**；Q1「作废」判断**正确**

复跑 `probes/probe-vec-scope-fix.py`（本人实测）：

| 问 | 读数 | 判定 |
|---|---|---|
| Q1 `clause_revision_id IN (SELECT value FROM json_each(?))`，喂 `["in_doc"]` | 0 行 | **该查询无意义**（拿 clause_revision_id 去比 doc_id）⇒ **「作废」判断正确** ✅ |
| Q2a `doc_id IN (SELECT value FROM json_each(?))` | 1 行 `['in_weak']` | ✅ 下推成功 |
| Q2b `doc_id IN (?, ?)` 字面量 | 20 行，含 `out_hot1/out_bulk*` | ❌ **混进范围外** |
| Q2c `doc_id = ?` 单值 | 1 行 | ✅（仅单文档可用） |
| Q2d `(doc_id = ? OR doc_id = ?)` | 20 行，含范围外 | ❌ 混进范围外 |
| Q3 `rowid IN (…)` | **未捕获异常 `no such column: rowid`** | 与 docstring 一致，但**脚本崩在此处**（见 P2） |

⇒ **「只有 `doc_id IN (json_each 子查询)` 这一种写法能下推；字面量列表 / OR 会返回范围外」成立**。
复跑 `probes/probe-vec-scope-fix2.py`（本人实测）：Q5 范围 100 篇仍下推 ✅｜Q6 无范围路径旧/新表 top-20 **逐条相同** ✅｜Q7 纯拷贝 30 行**逐字节一致** ✅｜Q8 空文档返回空不报错 ✅｜Q9 无范围 KNN 1.04ms→1.00ms **无劣化** ✅。

**代码面**（`git diff d5bcc56 f5fd5ce`）：`schema.sql` 加 `doc_id TEXT`；`clause_repo.py` **两条写入路径**（`insert_clauses_in_txn` 入库 + `_reindex_clause_indexes` 补丁重算）**都带 doc_id**；向量通道改走 `_scope_vec()`，FTS 仍用 `_scope_clause()`。全仓 grep 确认**没有遗漏的向量范围写法**（`behavior_scope_segmented` 是 FTS5 非 vec0）。

---

## 4. 判据有没有牙（变异测试）——**有牙；实施者关于"②只有新判据抓得住"的说法成立**

基线：`pytest tests/test_kb_scope_retrieval.py -q` ⇒ **14 passed**。
变异前 sha256 `d1223e2fd8ae19642dc35abce47c521a70fff434283b127f11574b602e56d13d`（与实施者声称一致）。

| 变异 | 结果 | 实施者声称 | 判定 |
|---|---|---|---|
| ① `_scope_vec()` 改回旧写法 | **2 failed**（`test_vec_channel_is_restricted_without_the_model` + `test_vec_scope_holds_with_more_than_one_document`） | 2 failed | ✅ |
| ② `doc_id = (SELECT value FROM json_each(?))` | **1 failed**，且**只有新多文档判据**红；老 1 篇判据**绿** | 1 failed（新判据抓） | ✅ |

**逐字节还原**：两轮变异后 `sha256sum` 均回到 `d1223e2f…`，`git status --short -- <file>` 为空 ⇒ **还原干净**。

---

## 5. 判据有没有被放宽 —— **没有**

`git diff d5bcc56 f5fd5ce -- tests/test_kb_scope_retrieval.py` 显示该用例**只改了 docstring 与夹具 INSERT 的列**（补 `doc_id`）；**断言一字未动**。
另用 `sed` 提取 `test_vec_channel_is_restricted_without_the_model` 的断言行逐字对比，两版**完全相同**：
```
assert ids, ("向量通道在范围内**一条都没返回**…")
assert not any(i.startswith("out_") for i in ids), f"向量通道没被范围堵住：{ids}"
```
（比较的是**内容**，未比裸哈希，规避 `core.autocrlf`。）⇒ **转绿来自修复，不是放宽判据** ✅。
连带测试 `pytest tests/test_contract.py tests/test_kb_scope_retrieval.py tests/test_doc_batch_delete.py tests/test_embedding_rebuild_resume.py -q` ⇒ **70 passed**（实施者另报三文件 49 passed，与之相容）。

---

## 6. 迁移安全性 —— happy path 全通；**但脚本对孤儿向量不健壮（安全失败）**

在**临时副本库**上复跑（`_gp1-migration-test.py`，用 `APPDATA` 重定向，**绝不动真库**）：

**① 无孤儿库**：`--dry-run` 不写库 ✅｜`--apply` rc=0、形状变 `['clause_revision_id','doc_id','embedding']`、行数 6、**字节不同 0、doc_id 不一致 0** ✅｜**幂等**（二次 `--apply` 输出"空操作"）✅｜脚本打印的三条**回滚 SQL 可执行**（回到 6 行、旧形状）✅。

**② 含孤儿向量的库**（`clause_vec` 有、`clause_revision` 无）：
```
✗ 迁移失败已回滚：OperationalError: Expected text for TEXT metadata column doc_id, received NULL
```
根因：vec0 的 **TEXT 元数据列不接受 NULL**；孤儿向量经 `LEFT JOIN` 得到 `doc_id=NULL` ⇒ 回灌时抛错。
**失败是安全的**：`BEGIN IMMEDIATE` + `ROLLBACK`，库**保持旧形状、行数不变、未留半成品表**（我实测前后一致）✅。
真库**孤儿=0**（第 2 节）所以当时跑通；但脚本自称通用工具，**对孤儿不健壮**，且 dry-run 已打印孤儿数却**不告警/不中止**（P2）。

---

## 7. 结论：**有条件 PASS**

**P0（阻断级）：无。** 修复正确、真库状态与断言相符、判据有牙且未被放宽、迁移 happy path 与回滚可执行、无数据丢失。

**P1（收口前应修）**
- **P1-1**：被本批**自我推翻**的「≥2 个 id 恒返回 `[]`」仍留在 **6 处本批产物**（`hybrid_engine.py:197`、`schema.sql:123`、`test_contract.py:449`、`plan.md:10`、`data-model.md:33`、`test_kb_scope_retrieval.py:366`），且 `hybrid_engine.py:200` 把**已作废的 Q1** 当"复现证据"。**纯文档/注释、无运行期影响**，但与更正后结论矛盾 ⇒ 建议统一改成"只有一部分条款有向量时失效"并去掉 Q1 引用。（主仓最新 `f6bb3ef` 仍在，冻结后未修。）

**P2（建议修）**
- **P2-1**：迁移脚本对**孤儿向量**直接失败（vec0 TEXT 元数据列拒 NULL）；虽**安全回滚**，但应显式检测孤儿并给出可执行处置（如先删孤儿/写占位），dry-run 见孤儿应告警。
- **P2-2**：迁移 docstring 写「自检（任一不过 ⇒ **整体回滚**、脚本非零退出）」，但**逐字节自检在 COMMIT 之后**（事务外）⇒ 该自检失败**不会自动回滚**，只打印回滚命令。docstring 与代码不符。
- **P2-3**：`probes/probe-vec-scope-fix.py` 在 **Q3 未捕获异常崩溃**（`no such column: rowid`），**Q4 从未跑到**，脚本以 rc=1 退出。Q3 行为本身与 docstring 相符，但探针不能端到端跑完。
- **P2-4**：`specs/003-vec-scope-pushdown/research.md:27` 引用的 `probe-scale-flip2.py` **不存在**（实际文件是 `probe-mechanism.py`）——引用断链。

---

## 8. 我实测的 / 我未验的

**已实测（本人读数/命令）**：机制拆分判据（p/q 独立扫）、旧形状表证伪"≥2 个 id"、真库只读体检 8 项、真库抽样 6 篇旧写法实跑、Q1 作废判断、Q2a–Q2d 下推形态、Q3 崩溃、probe-fix2 的 Q5–Q9、变异 ①②+sha256 还原、判据文件断言逐字对比、连带 70 passed、迁移 dry-run/apply/自检/幂等/回滚 + 孤儿安全失败、残留说法 6 处溯源。

**未验（明写）**：
1. **未跑 `scripts/run-gates.ps1`**（遵指示，避免与主仓门禁锁冲突）；故**全量门禁/tsc/smoke/e2e 未验**。
2. **未在真库上重跑迁移**（实施者已跑；我只读核了结果状态 + 在临时副本上复跑脚本逻辑）。
3. **未把 `node_modules` 拷进提取树**（本项复核为**纯 Python** 路径，未用到；如需前端/JS 验证请另跑）。
4. **未独立校验备份文件内容完整性**（只核了存在与大小 3,105,525,760 B ≈ 2,962 MiB，与提交信息一致）。
5. **未验 partition key 备选（Q4）**（探针在 Q3 已崩，未跑到）。
6. **未验**实施者提交信息里的迁移耗时「465 s」与「全库副本耗时」等性能数字。
7. **未验**冻结后的续作提交（`68e3574`/`46f45c6`/`f6bb3ef`）——复核范围**仅冻结树 `f5fd5ce`**。

---

## 9. 复现命令（均在提取树内，用主仓 venv 解释器）

```bash
cd "D:/AI/verify-trees/spec003-vecscope-gp1"
PY="D:/AI/work space/zcode/.venv/Scripts/python.exe"
$PY specs/003-vec-scope-pushdown/probes/probe-mechanism.py      # 实施者探针
$PY _gp1-probe-mech-split.py                                    # 本人：拆分 p/q
$PY _gp1-probe-mech-v2.py                                       # 本人：多文档部分缺失 + 字面量
$PY _gp1-oldshape-check.py                                      # 本人：旧形状证伪"≥2 个 id"
$PY specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix.py  # 会崩在 Q3（见 P2-3）
$PY specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix2.py
$PY _gp1-realdb-check.py                                        # 真库只读（~4 分钟）
$PY _gp1-realdb-sample.py                                       # 真库抽样
$PY -m pytest tests/test_kb_scope_retrieval.py -q
$PY -m pytest tests/test_contract.py tests/test_kb_scope_retrieval.py \
     tests/test_doc_batch_delete.py tests/test_embedding_rebuild_resume.py -q
$PY _gp1-migration-test.py                                      # 临时副本库（APPDATA 重定向）
```

**主仓改动**：**无**（一切操作在 `D:\AI\verify-trees\spec003-vecscope-gp1` 内；报告未搬入主仓）。
**提取树收尾**：报告写在本树；**尚未 `git worktree remove`**（因报告需留在此目录，且含我未纳入 git 的 `_gp1-*.py` 临时脚本）——如需清理请告知。
