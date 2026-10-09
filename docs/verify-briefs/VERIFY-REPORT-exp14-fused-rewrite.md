# 独立复核报告 · exp-14-fused-rewrite

**批次**：`verify-freeze-exp14-fused-rewrite` → `da27368eeccce593aa85d83ad81c44fee2438bae`
**复核者**：general-purpose-1（独立 verifier，只读主仓，实验全在提取树）
**复核日期**：2026-10-09
**验证环境**：提取树 `D:/AI/verify-trees/exp14`（`git worktree add --detach da27368`）；解释器用主仓 `.venv`（fastembed/jieba/sqlite-vec），`sys.path` 首插提取树 src ⇒ 跑的是冻结树的代码。

---

## 0. 提取树首记

```
$ git rev-parse HEAD
da27368eeccce593aa85d83ad81c44fee2438bae
$ git status --short
（空）
```

改动面核实（`git show --stat da27368`）：**单提交 14 文件**，全部落在
`eval/recall-funnel/exp-14-fused-rewrite/**`、`tests/test_fused_rewrite_ruler.py`、5 个 docs、`eval/recall-funnel/README.md`。
`git show --name-only da27368 | grep '^\(src\|plugin\)/'` ⇒ **空**。**`src/` 与 `plugin/` 零改动确认。**
（注：`caffb46..da27368` 含 `tools/gov-qa/**` 改动，但那属 `935bc31` gov-qa 提交，非本批——已按提示排除。）

---

## 1. 读数逐格复算 —— ✅ 全部独立复现

自写脚本 `scripts/recompute.py`（**只读 `per-query.jsonl`，自己实现 hit_rate/median/mcnemar/flip，未复用作者 `aggregate_runs`**）：

| 项 | 我复算 | result.json | 判定 |
|---|---|---|---|
| headline 独立过滤（benchmark 171→120） | 120，i 集合与 per-query 完全一致 | 120 | ✅ |
| subset 计数 | 字面零重合 83 / 普通 35 / 短条款 2 | 同 | ✅ |
| A0 fused@20/@100/@1000/中位/池中位 | 8.33 / 11.67 / 11.67 / 9 / 40 | 同 | ✅ |
| B1 | 9.17 / 12.5 / 12.5 / 7 / 40，Δ+0.84 进1出0 p=1.0 | 同 | ✅ |
| C1 | 5.0 / 10.0 / 10.0 / 26 / 40，Δ−3.33 进0出4 p=0.125 | 同 | ✅ |
| D1 | 7.5 / 9.17 / 9.17 / 12 / 37，Δ−0.83 进1出2 p=1.0 | 同 | ✅ |
| by_subset_top20（4 臂 × 3 档） | 逐格一致 | 同 | ✅ |
| instrument_check.mismatch_count | 6 | 6 | ✅ |

**结论**：`result.json` 的每一个数值我都从原始 `per-query.jsonl` 重算并逐格命中，**零差异**。
结构性读数 `fused@1000 == fused@100`（四臂均成立）与 `池中位 40` 亦复现。

---

## 2. ★ 仪器对照失效的归因 —— ✅ 归因成立（非作者 bug）

**(a) 失配条数/明细（自数）**：`A0.fused.gold_rank` vs `funnel-per-query.jsonl` 的 `fused.gold_rank`
⇒ **6 / 120 失配**，与 result.json `mismatch_samples` 逐条一致：

```
i=87   funnel=29  exp14_A0=33
i=113  funnel=22  exp14_A0=32
i=130  funnel=6   exp14_A0=9
i=133  funnel=18  exp14_A0=28
i=166  funnel=22  exp14_A0=36
i=167  funnel=21  exp14_A0=None   （掉出池）
```
6 处**全部是"名次变差"**（数字变大 / 掉出），方向与"候选池变大、新竞争者把 gold 挤下去"一致。

**(b) FTS 候选池实量（`SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ?`，`_fts_query` 取自生产）**：

| i | 历史 fts_pool(10-06) | 当前 COUNT | 差 |
|---|---|---|---|
| 87 | 6,759 | 8,092 | +1,333 |
| 113 | 29,170 | 37,911 | +8,741 |
| 130 | 3,017 | 3,890 | +873 |
| 133 | 1,143 | 1,907 | +764 |
| 166 | 54,359 | 68,475 | +14,116 |
| 167 | 8,740 | 28,388 | +19,648 |

**全 120 条：上涨 120 / 持平 0 / 下降 0**。README 引用的四个数字（166→68,475、113→37,911、87→8,092、133→1,907）**逐字命中**。真库当前 `clause_revision = clause_vec = clause_fts = 663,634`。

**(c) 决定性复现（我自己重跑，非复用作者产物）**：用**生产函数**在**今天的活库**上对 6 条失配 i + 2 条对照重跑 A0 融合（`search_with_details(top_k=1000, rerank=False, boost_bookmarks=False, expand_chain=False)`，不装任何钩子）：

```
与 exp-14 A0 不同 = 0 / 8      ← 完全复现 exp-14（含 33/32/9/28/36/None）
与 funnel 历史不同 = 6 / 8     ← 只在 6 条失配 i 上≠历史
DB mtime 变 ? False
```

**⇒ exp-14 的 A0 读数今天可原样复现，与历史 funnel 的差只出现在那 6 条。** 结合：
- `funnel.py:304` 的 fused 调用与 exp-14 **逐字同一条**（已核）；
- 10-06(funnel) → 10-09(exp-14) 之间，**`src/core/retrieval/` 唯一改动是 `ec32f93`**，而其对 `hybrid_engine.py` 的改动**只有 docstring/注释**（真正的行为修复在 `reranker.rerank()`，只在 `rerank=True` 时生效；本批与 funnel 都用 `rerank=False`）⇒ **不构成代码漂移**；
- 期间另有大量 `src/core/ingestion/**` 切分修复 + gov-qa 数据入库 ⇒ **语料本身变了**。

**判定：6 处失配 = 参照物（10-06 的历史产物）过期，被活库/语料变化甩开；不是 exp-14 的 bug。**
README/§五 的归因**成立**，措辞（"不是本批的 bug""参照物必须是同期重跑"）**守得住**。
（一处吹毛求疵：README 把机制全归到"FTS 池上涨"，严格说 vec 池（新向量入 top-20）也可能是成因之一；但结论"活库变了"不受影响。）

---

## 3. 替代仪器对照 determinism —— ✅ 独立复现（子集）

自写 `scripts/my_determinism.py`（自己实现两遍/台账/泄漏比对），跑 **前 40 条 A0 两遍 + 前 20 条泄漏检查**：

```
同会话两遍不同          = 0 / 40
与 runs.jsonl 台账不同  = 0 / 40
钩子泄漏(A0装钩 vs 不装) = 0 / 20
DB mtime 变 ? False
```

与作者 `determinism.json`（120/120/20 全 0）**方向一致、无矛盾**。我未跑满 120（作者全量），但 40+20 的独立子集**零失配**。
**注**：`determinism.json` 声称的 120 全量**我未逐条复跑**（工具后台 timeout 上限 600 s 约束），仅子集独立复现 ⇒ 标注为**部分复现**。

---

## 4. 判据有没有牙（我自己做 6 处变异，不与作者重复）—— ⚠ 发现 2 处逃逸

在提取树里就地改 `run.py`（CRLF 行尾已处理），跑 `pytest`，**用备份字节 `write_bytes` 还原**（还原后 `git hash-object run.py` == `da27368:…run.py` blob，字节一致）：

| 变异（我自己选） | 结果 |
|---|---|
| MUT-A `pool_median` 取上中位数 | "被抓"，**但只是偶然**——命中的是 1 元素测试夹具触发 IndexError，**无任何判据断言 `pool_median` 的值** |
| **MUT-B `by_subset` 阈值 20→10** | **★逃逸**（10 passed）—— `by_subset_top20` 是被上报的副终点，**无判据覆盖** |
| MUT-C `_headline` 去掉 bucket 判据 | 被抓（`test_headline_excludes_multi_def_and_dup`） |
| MUT-D `arm_vec_query` 的 A0 返回 d1_query | 被抓（`test_a0_touches_nothing`） |
| MUT-E `delta_pt` 符号取反 | 被抓（`test_flip_and_delta_direction_on_asymmetric_sample`） |
| **MUT-F `fused_hit_n` 改成数 None 个数** | **★逃逸**（10 passed）—— `fused_hit_n` 无判据覆盖 |

**判定**：作者"10 条全绿、8 处变异全部被抓"这句**我未逐条复现其 8 处**，但我自己的 6 处里 **4 被抓 / 2 逃逸**。
逃逸的两处（`by_subset_top20`、`fused_hit_n`）都是**被写进 `result.json` 的副终点**——
即尺子对"主终点 + 通道映射 + headline + 边界/方向/缺格 + 静态锚点"有牙，但对**副终点的取值**无牙。
**这不动摇本批主结论**（我已在 §1 从原始 `per-query.jsonl` 独立重算全部副终点并命中），
但作为判据完整性缺口**登记为 P2**（建议补 `by_subset`/`fused_hit_n` 各一条取值判据）。

---

## 5. 预注册顺序 —— ✅ 成立（附一处小瑕疵）

`da27368` 是同一次提交，`git log --format=%ct` 对批内各文件相同 ⇒ **git 无法区分批内先后**。
改用**主仓工作树 mtime**（`da27368` 是 HEAD 祖先、这些文件未被再检出，mtime 为作者真实写入时刻）：

| 文件 | mtime |
|---|---|
| `stop-loss.json` | **2026-10-09 15:36:43** |
| `runs.jsonl` | 15:48:25 |
| `run.py` | 15:52:02 |
| `per-query.jsonl` | **15:52:08** |
| `result.json` | **15:52:08** |
| `README.md` | 15:52:13 |
| `determinism.json` | 15:53:50 |

**`stop-loss.json` 早于 `result.json`/`per-query.jsonl` 约 15 分钟** ⇒ 预注册顺序**成立**。
**小瑕疵（P2）**：`stop-loss.json` 内 `registered_at = 2026-10-09T15:42:00`，却**晚于**该文件的 mtime(15:36:43)——
文件里出现了晚于其最后写入时刻的自称时间戳。不影响"跑前落盘"结论，但**登记为不一致**。

---

## 6. 诚实边界 —— ⚠ **发现一处 P1 过强断言（须更正）**

**★ P1：README 的结构性断言 #1「模态 0 触发 ⇒ 用户永远看不到第 41 条以后」被本批自己的数据证伪。**

README（及 5 个下游文档）称：

> 生产融合池 = 向量 `k=20` + FTS `LIMIT 20` + 精确/模态（**本轮 0 触发**）⇒ 池子就 40 条左右
> ⇒ **"用户能看到的范围"被硬限制在 ~40 条** …… ⇒ **用户永远看不到第 41 条以后**

**实测（来自 exp-14 自己的 `per-query.jsonl`）**：

- **模态通道本轮并非 0 触发**：headline 120 里 **i=142/153/155/163/167 共 5 题**模态通道触发
  （`funnel-per-query.jsonl` 记 `channels.modality.fires=True`，n=1,830 ~ 140,555）；
- 这 5 题的 **A0 融合池 `fused_n` = 1000**（不是 40）⇒ **"永远看不到第 41 条以后"为假**；
- 池深分布：`min 32 / p50 40 / max 1000`，**>40 的题 5 / 120**。

且该说法**与本仓既存事实自相矛盾**：`eval/recall-funnel/exp-7-rrm/VERDICT-融合算子.md:79` 早已登记
"融合候选池：中位数 40、**均值 1,668.7、最大 169,645**、最小 32"。

该断言是本批**新引入**（`git diff da27368^..da27368` 命中）并**扩散到 6 个文件**：
`exp-14-fused-rewrite/README.md`(L8/73/74)、`docs/CHANNEL-COVERAGE-PLAN.md:2707`、
`docs/RETRIEVAL-LONG-RANGE-PLAN.md:610`、`docs/NEXT-DEV-PLAN-2026-09-28.md:451`、
`eval/recall-funnel/README.md:312`、`docs/DEVELOPMENT-HISTORY.md §10.221`。

**为何算 P1**：它被作者列为"**本批真正的收获**"（§三.3、§七），并据此把 P2 靶子改写成
"先解决池子太小"。池子**中位**确是 40、`fused@1000==fused@100` 也确为真——
但"**永远**/**硬限制在 ~40**"是**全称过强**，被自己的 5/120 反例推翻。**须把"永远/0 触发/硬限制"
降为"多数题（115/120）池 ≈40，少数题（5/120，模态触发）池达 1000"**，并同步修 6 个文件。

**其余诚实边界核查（守得住 ✅）**：
- "融合比向量路前 20 差 1 条"——**措辞守住了**：明标"⚠ 单条差异、**不构成结论**、登记为观察；且两者时点不同"（README L77-79），
  且读数属实（exp-13 `A0 vector_top20=9.17%`=11 条 vs exp-14 `fused@20=8.33%`=10 条，差 1 条）✅
- "本批 A0=8.33%（库 663,634 条）"——库计数属实 ✅
- 仪器对照失效 + 更正——留痕完整、措辞不越界 ✅

---

## 7. 改动面 —— ✅ 确认

`da27368` 单提交 14 文件，`src/`、`plugin/` **零改动**（见 §0）。
`runs.jsonl` = 480 行（120×4，与 4 臂台账一致），`per-query.jsonl` = 120 行，`determinism.json` 三条 0 失配。

---

## 总判定

| 复核项 | 结果 |
|---|---|
| 1. 读数逐格复算 | ✅ **独立复现，零差异** |
| 2. ★ 仪器对照失效归因 | ✅ **归因成立**（今天重跑 8/8 复现 exp-14；非本批 bug；无代码漂移） |
| 3. 替代对照 determinism | ✅ **子集独立复现**（两遍 0/40、台账 0/40、泄漏 0/20）；全量 120 **未跑满**（未验满） |
| 4. 判据牙口 | ⚠ 4 被抓 / **2 逃逸**（`by_subset`、`fused_hit_n` 无判据）— P2 |
| 5. 预注册顺序 | ✅ 成立（stop-loss 15:36:43 < result 15:52:08）；`registered_at` 与 mtime 不一致 — P2 |
| 6. 诚实边界 | ⚠ **1 处 P1 过强断言**（"模态 0 触发 / 永远看不到第 41 条"）须更正并同步 6 文件 |
| 7. 改动面 | ✅ `src/`+`plugin/` 零改动 |

**主结论判定：主实验读数、判决（三条都不改）、仪器失效归因、确定性、预注册——全部独立复现，PASS。**
**但【打回一条 P1】**：README/6 文件的"模态 0 触发 ⇒ 用户永远看不到第 41 条以后"与作者自己的数据
（5/120 题池=1000）及 exp-7 既存登记相矛盾，属**超出证据的全称断言**，须更正后再放行。
两条 P2（判据逃逸、registered_at 与 mtime 不一致）建议一并处理。

**未验（明确登记）**：① `determinism.json` 的 120 全量三方比（我只独立跑了 40+20 子集）；
② 作者自报的 8 处变异（我未逐条复现其具体 8 条，只做了自选 6 条）；③ "471 s 跑完/被中断接续"（产物无时间戳，不可验）。

---

## 提取树尾记

```
$ git rev-parse HEAD
da27368eeccce593aa85d83ad81c44fee2438bae
$ git status --short
（空）
$ git hash-object eval/recall-funnel/exp-14-fused-rewrite/run.py   # 变异实验后还原校验
c292c5c7108c017c6553dfdb98655a0bf721c2c8
$ git rev-parse da27368:eval/recall-funnel/exp-14-fused-rewrite/run.py
c292c5c7108c017c6553dfdb98655a0bf721c2c8
```

（复核完成后已 `git worktree remove --force D:/AI/verify-trees/exp14` + `git worktree prune` 清理提取树。）
