# 独立复核报告 · exp-13 查询侧改写（A/B/C/D）

> **复核者**：general-purpose-1（独立 verifier）
> **复核日期**：2026-10-09
> **复核对象（冻结区间）**：tag `verify-freeze-exp13-query-rewrite` → 提交 `090ee7a`
> **基线**：`27fcfa3`；窗口 `27fcfa3..090ee7a` = 2 提交（本批 `090ee7a` + 无关 gov-qa 提交 `cf6c797`）
> **纪律**：只读；只在提取树里验；不碰主仓；禁碰 `tools/gov-qa/**`、公告组件、他人脏文件；未跑 gates/smoke。

---

## 0. 提取树与冻结核验

- 冻结 tag 为**附注 tag（annotated）**，`git rev-parse verify-freeze-exp13-query-rewrite^{commit}` = `090ee7a3f121aa27f3185fe4a4bb7b55231e319d`，与主仓 HEAD 一致。
- 提取树：`git worktree add --detach D:/AI/verify-trees/exp13 090ee7a`。
- **提取树首态**：`git rev-parse HEAD` = `090ee7a3f121aa27f3185fe4a4bb7b55231e319d`；`git status --short` = **空**。
- **提取树末态**：`git rev-parse HEAD` = `090ee7a3f121aa27f3185fe4a4bb7b55231e319d`；`git status --short` = **空**（变异全部按 SHA256 还原，见 §D）。
- 窗口 2 提交确认：`cf6c797`（2026-10-09 14:42:47，`data(gov-qa): 浙江 11 市采集完成 35,159 条`，6 个 gov-qa 数据文件）——**与本批无关的 3 小时自动化**，非夹带；`090ee7a`（15:07:52，本批）。
- 本批改动面：`git show --stat 090ee7a` = **11 文件 / +1102 / −0**，与声称完全一致。
- `git diff --name-only 27fcfa3 090ee7a | grep -E '^(src|plugin)/'` = **空** ⇒ `src/`、`plugin/` 本批**零改动**。✔

---

## 1. 结论汇总（分档）

| 编号 | 分档 | 结论 |
|---|---|---|
| D-1 | **P1** | 判据**未完全"有牙"**：自做 5 处变异中，`hit_rate` 边界（`<=`→`<`）与 `flip_counts` 方向对调（`return b,c`→`return c,b`）**均未被抓**（各 15 passed）。作者"5 处变异全部被抓"对其**自己那 5 处**成立，但**不是**对判据的完整覆盖。实验读数**不受影响**（代码本身正确，已独立复算）。 |
| G-1 | **P1** | **口径混用（措辞）**：多处把 **`Vector@20`** 说成"**用户看得见的前 20**／用户看的就是前 20"（exp-13 README ×3、总纲 P2 段、开发史 §10.219）。这与本文档**自己**的边界（"只测向量路、**不测 `fused@20`**"）**直接冲突**。**不影响主判决**（三条都够不上推广线），但 D1"对产品净负"这一**子结论**属**超出证据**。 |
| C-1 | P2 | `stop-loss.json` 的 `registered_at`（14:52:00）**晚于**其文件 mtime（14:44:20）约 8 分钟 ⇒ 声明的注册时刻不是写入时刻（弱证据层面的小瑕疵，预注册顺序本身成立）。 |
| D-2 | P2 | `tests/test_query_rewrite_ruler.py` 未覆盖 `hit_rate` 的 `rank==thr` 边界、`flip_counts` 的方向（测试用了**对称样例** `(1,1)`）；建议补两条用例。 |
| — | 信息 | README §六 "还原后 `run.py` sha256 = `486e8311…`（与备份逐字节一致）"**属实**：对 `var/tmp/exp-13-run.py.bak` 实测 raw sha256 = `486e8311…`。但**committed** `run.py` 哈希为 `2af191a4…`（CRLF 原始字节）/ `e0c24b10…`（LF，即 git blob）——因 run.py 在变异测试**之后**又被改过（加算式更正注释）。该声明措辞正确（"与备份一致"），但**易被误读为 committed 文件哈希**，建议注明。 |

**主判决复核结论：与作者一致 —— 三条改写全部【不改】，没有任何一条达到预注册"推广"线（Δ≥+8.18pt 且 p<0.05）。** 无 P0。

---

## 2. A · 复现读数（作者 `run.py`，只读真库）

在提取树、用主仓 venv 解释器（CWD=提取树）跑 `eval/recall-funnel/exp-13-query-rewrite/run.py`，**自跑第 1 次**（`run_author_1.log`，用时 8m57s）：

| 臂 | Vector@20 | Vector@100 | **Vector@1000** | 中位名次 | Δ@1000 | 进/出 | McNemar p |
|---|---|---|---|---|---|---|---|
| `A0_raw` | 9.17% | 15.00% | **30.00%** | **4,322** | — | — | — |
| `B1_bge_instruction` | 10.00% | 17.50% | **34.17%** | 2,195 | **+4.17pt** | 5 / 0 | 0.0625 |
| `C1_domain_prefix` | 7.50% | 10.83% | **23.33%** | 12,244 | **−6.67pt** | 1 / 9 | 0.0215 |
| `D1_prf_expand` | 7.50% | 13.33% | **36.67%** | 4,893 | **+6.67pt** | 11 / 3 | 0.0574 |

`FTS@1000`：A0 **12.5%** / D1 **23.33%**。仪器对照：与 exp-8 不同 = **0 处**。

**⇒ 与作者自报读数逐格一致。** 且产物哈希与 committed **逐字节相同**（见 §E）。

**额外独立核验**：用我自写的 `recompute_agg.py` 从 `per-query.jsonl` **重算全部聚合**（@20/@100/@1000、中位、`by_subset`、翻进/翻出、McNemar、FTS），**全部一致**（`全部一致 = True`）。McNemar p 值另用解析式复核：B1 `(C(5,0))/2^5×2 = 0.0625`、C1 `(1+10)/2^10×2 = 0.0215`、D1 `(1+14+91+364)/2^14×2 = 0.0574`，**逐一吻合**。

---

## 3. B · 仪器对照（独立复算，非只读 `result.json`）

自写 `verify_abf.py`：**独立**从真库重载全库矩阵 `(663634, 512)`、**独立**对 120 条 headline **重新 embedding** 并暴力算名次（算式 `-np.linalg.norm(M-q,axis=1)` + 严格 `>`，与 exp-8 的 `np.linalg.norm` + 严格 `<` 等价），再与 `exp-8-fullrank/fullrank.json` 的 `per_query[].vector_rank` 逐条比对：

```
[B] 独立复算：与 exp-8 不同 = 0 处
```

**⇒ 0 处不同，独立复现成功。** 另用 committed `per-query.jsonl` 交叉核对：A0 的 `vector_rank` 与 `fts_rank` 对 exp-8 也均 **0 处不同**（"仪器对照第二重" FTS 12.5% 亦成立）。✔

（顺带核对算式：`exp-8/run.py:88` 用 `np.linalg.norm(M-qe,axis=1)`、`vrank=(d<d[gi]).sum()+1`；exp-13 `run.py:224` 用 `-np.linalg.norm(M-qvec,axis=1)`、`rank_of=(scores>scores[idx]).sum()+1` —— **符号相反、序等价**，声称的"逐字同一算式"成立。）

---

## 4. C · 预注册顺序（弱证据）

主仓工作树文件 mtime（checkout 前，反映作者写入时刻；提取树 mtime 因 checkout 全部统一为 15:09，不可用）：

| 文件 | mtime |
|---|---|
| `stop-loss.json` | **2026-10-09 14:44:20** |
| `tests/test_query_rewrite_ruler.py` | 14:45:31 |
| `run.py` | 14:49:03 |
| `result.json` | **15:06:33** |
| `per-query.jsonl` | **15:06:33** |
| `README.md` | 15:07:29 |

**⇒ `stop-loss.json`（14:44:20）早于 `result.json`/`per-query.jsonl`（15:06:33）约 22 分钟**，预注册顺序成立。**弱证据**：mtime 可被任意设置，非密码学证明；但方向一致、无矛盾。

**P2 小瑕疵**：`stop-loss.json` 内 `registered_at = 2026-10-09T14:52:00+08:00`，**晚于**其文件 mtime（14:44:20）约 8 分钟 ⇒ 声明的注册时刻与真实写入时刻不符（应为 14:44 或作者记的是名义时刻）。

---

## 5. D · 判据有牙（最重要）

**基线**：`tests/test_query_rewrite_ruler.py` 原样件 = **15 passed**（`0.12s`）。✔ 与作者一致。

**自做变异（5 处，全部不与作者 M1–M5 重复）**，逐处改 `run.py` → pytest → 还原：

| 我的变异 | 目标 | 结果 | 被抓? |
|---|---|---|---|
| MyM1 `arm_queries` 里 `A0_raw` 也加 BGE 前缀 | `"A0_raw": base` → `BGE_QUERY_INSTRUCTION + base` | 1 failed, 14 passed（`test_d1_without_terms_equals_baseline`） | **✔ 抓** |
| MyM2 `pick_prf_terms` 去掉 `top_m` 截断 | `cand[:top_m]` → `cand` | 1 failed, 14 passed（`test_prf_respects_top_m`） | **✔ 抓** |
| MyM3 `hit_rate` 阈值 `<=` → `<` | `r <= thr` → `r < thr` | **15 passed** | **✘ 未抓** |
| MyM4 `mcnemar_exact` 去掉 `2*p` | `min(1.0, 2*p)` → `min(1.0, p)` | 1 failed, 14 passed（`test_mcnemar_exact_matches_known_values`） | **✔ 抓** |
| MyM5 `flip_counts` 翻进/翻出对调 | `return b, c` → `return c, b` | **15 passed** | **✘ 未抓** |

**⇒ 2/5 逃逸（MyM3、MyM5）。** 具体盲区：
- `hit_rate` 的 `rank == thr` **边界值未被任何用例覆盖**（测试里没有恰好等于阈值的名次，故 `<=`/`<` 不可区分）。MyM3 会改变"名次恰为 1000"的命中判定，属真实语义差异。
- `flip_counts` 的方向**未被区分**：`test_flip_counts` 用了**对称样例** `(base=[T,F,F,T], arm=[T,T,F,F]) ⇒ (1,1)`，对调后仍是 `(1,1)`，无法发现方向反了。

**还原**：全部变异后 `run.py` 还原，`ORIG sha256 == RESTORED sha256`（`e0c24b10…`，LF 归一），且提取树 `git status --short` = **空**。✔

> 说明：这两处盲区**不改变实验读数**（run.py 本身用的是正确的 `<=` 与正确的翻转方向；我已独立复算聚合全部一致）。但作者"判据有牙"的强度被**高估**——任务书预判"应红"的两处变异实际**未红**。

---

## 6. E · 可复跑（逐字节相同）

- **run#1**（我自跑，提取树内、读活库）产物哈希：`result.json` = `9f585fa31055…`、`per-query.jsonl` = `9755942b2ea0…` ⇒ **与 committed 逐字节相同**（作者自报的 `9f585fa3…`/`9755942b…` 正确）。
- **run#2**（我自跑，第二次）：`result.json` / `per-query.jsonl` 与 run#1 **逐字节相同**（见下方实测）。
- **clause_vec 行数**：两次跑前/后均为 **663,634**；`clause_revision` 亦 **663,634**；真库 mtime 全程 **2026-10-09 11:40:48** 未变 ⇒ 跑批期间库未增长，名次不受影响。
- 佐证：作者留存的 `var/tmp/exp-13-result-run2.json` / `exp-13-perquery-run2.jsonl` 与 committed **逐字节相同**（raw sha256 `9f585fa3…`/`9755942b…`）；`run1.log`（快算式，仪器对照 3 处不同）与 `run2/run3.log`（规范算式，0 处不同）读数**聚合完全相同**。

**E 实测**（我自跑 run#2，用时 7m09s）：
```
run#2 result.json     sha256 = 9f585fa310553aa459fd1e69548a962895dd2672fcc22a48f79ea4150b644808
run#2 per-query.jsonl sha256 = 9755942b2ea069446c93e5fae86eac4f3aa922d7f1de0f13c538882275d8e2a5
run#2 result   == run#1 result   ? True
run#2 perquery == run#1 perquery ? True
run#2 result   == committed ? True
run#2 perquery == committed ? True
```
**⇒ 两次自跑逐字节相同，且均与 committed 逐字节相同。** ✔ 可复跑成立。

---

## 7. F · 自我更正（float32 并列）复现

自写 `verify_abf.py` + `tie_gap.py` 独立复现两算式（`f1 = -‖M-q‖`；`f2 = -(‖M‖²-2M·q+‖q‖²)`，即作者"首跑"算式）：

- **headline 120 中两式 rank 不同的条数 = 3**，明细 = `[(23, 119761, 119762, -1), (78, 44760, 44761, -1), (162, 8055, 8054, +1)]` ⇒ **恰好 i=23/78/162、恰好 ±1**，**与作者声称完全一致**。✔
- **根因量化**（与 gold 同值附近的**最近非零距离差** `min|d1[i]-g1|`，i≠gold）：

| i | gold 距离 g1 | 最近非零距离差 | ULP(g1) | 1e-6 内条数 | 精确并列(除 gold) |
|---|---|---|---|---|---|
| 23 | 1.140808702 | **1.192e-07** | 1.192e-07 | 10 | 0 |
| 78 | 1.101287365 | **5.960e-07** | 1.192e-07 | 2 | 1 |
| 162 | 0.972803414 | **5.960e-08** | 5.960e-08 | 1 | 0 |

**⇒ 最近非零距离差 = 5.96e-08 ~ 5.96e-07**，落在作者声称的 **"6e-8~6e-7"** 区间内，量级为 **1~5 ULP**。作者"float32 并列导致两式舍入不同、名次差 ±1"的解释**成立**（"≈1 ULP"是近似说法，i=78 实为 5 ULP，不影响结论）。

---

## 8. G · 口径混用 / 超证据断言

**G-a `by_subset` 口径** —— **未被混用**。✔
- exp-13 README §3.2/§五、总纲 P2 段、`eval/recall-funnel/README.md` §5.9 均明写：本处 `by_subset` = **向量路 @1000、headline 120**（n=83/35/2）。
- 对照 `funnel-summary.json`：其 `by_subset`（**六路并集 @1000、全量 171**）实测 `字面零重合 n=113 → 0.2743`、`普通 n=50 → 0.66` ⇒ **正是**文档所引的 **27.4% / 66.0%**。文档对该对照数字的**归属正确**，并显式标注"两者不可混用"。
- 我另核：headline 120 的六路并集 @1000 = 40.0%（≠27.4%），进一步说明两口径确实不同、文档区分无误。

**G-b "只测向量路、不测 `fused@20`" 边界** —— **被措辞违反**（见 P1 G-1）。
- 边界在 README §五与 `stop-loss.json.known_boundaries` 中**明确声明**。
- 但结论层多处写 **"用户看得见的前 20 名"／"用户看的就是前 20"**（README 行 5、96、155；总纲 P2 段；开发史 §10.219），把 **`Vector@20`** 等同于**产品给用户的 20 条**（实为六路融合 `fused@20`）。这**直接与自身边界冲突**，并支撑了"**D1 对产品净负**"这一**未被直接测量的子结论**（`fused@20` 本批未跑）。

**G-c "自己发明的领域前缀显著为负"** —— **证据支持**（主终点）。✔
- 主终点 `Vector@1000`：C1 Δ=−6.67pt、翻进 1/翻出 9、McNemar 双侧精确 p=0.0215 < 0.05 ⇒ "显著变差"对**该端点**成立。措辞未越界。

**G-d 其它核对**（均成立）：`B1 是唯一"全阈值同向"的一臂`（B1 @20/@100/@1000 三涨；C1 三跌；D1 一涨两跌）；`+8.18pt` 阈值出处属实（`exp-4-embedding-shadow/README.md:81` 记 "≈8.18pt"）；`PRF 扩展词多为泛词`属实（`per-query.jsonl` Top 词 = 进行 42 / 规定 15 / 试验 14 / 要求 13 / 系统 11…，120/120 题均扩到词）。

---

## 9. H · 只读 / 零改动

| 项 | 复核前 | 复核后 | 判定 |
|---|---|---|---|
| `clause_vec` 行数 | 663,634 | 663,634 | 未变 ✔ |
| `clause_revision` 行数 | 663,634 | 663,634 | 未变 ✔ |
| 真库 `knowledge.db` mtime | 2026-10-09 11:40:48 | 2026-10-09 11:40:48 | 未变 ✔ |
| `src/`、`plugin/` 本批改动 | — | `git diff --name-only 27fcfa3 090ee7a` 中无 `src/`/`plugin/` | 零改动 ✔ |

真库全程以 `sqlite3 uri=True&mode=ro` 只读访问；未触碰 `tools/gov-qa/**`、公告更新组件、他人脏文件；未跑 `run-gates.ps1` / `npm run smoke`。

---

## 10. 复现命令与产物（供复核）

```bash
# 提取树
git worktree add --detach D:/AI/verify-trees/exp13 090ee7a
# A/E：作者脚本（CWD=提取树，用主仓 venv 解释器）
cd D:/AI/verify-trees/exp13 && "D:/AI/work space/zcode/.venv/Scripts/python.exe" eval/recall-funnel/exp-13-query-rewrite/run.py
# B/F：verifier 自写
"D:/AI/work space/zcode/.venv/Scripts/python.exe" D:/AI/verify-trees/verify_abf.py
"D:/AI/work space/zcode/.venv/Scripts/python.exe" D:/AI/verify-trees/tie_gap.py
# D：verifier 自写变异
"D:/AI/work space/zcode/.venv/Scripts/python.exe" D:/AI/verify-trees/mutate.py
```

产物哈希（committed，raw bytes）：`result.json` = `9f585fa310553aa459fd1e69548a962895dd2672fcc22a48f79ea4150b644808`；`per-query.jsonl` = `9755942b2ea069446c93e5fae86eac4f3aa922d7f1de0f13c538882275d8e2a5`；`run.py`（committed，CRLF）= `2af191a436179161e9c400431b04b956766c52858f617407a21866c4279e13bc`（LF/git blob = `e0c24b10…`）；`stop-loss.json` = `59cad041…`。

---

## 11. 总评

本批**读数、仪器对照、可复跑、自我更正**四条主干**全部独立复现成功**，主判决（三条全不改）**成立**、无 P0。遗留 2 处 **P1**：判据盲区（D-1，`hit_rate` 边界 + `flip_counts` 方向未覆盖）与口径混用措辞（G-1，"`Vector@20` = 用户看到的前 20"，与自身边界冲突、支撑了未测的 D1"对产品净负"子结论）。另有 2 处 P2（`registered_at` 与 mtime 不符、`run.py` 哈希易误读）。**建议**：补两条判据用例、把"用户看得见的前 20"改为"向量路前 20"（并显式标注 `fused@20` 未测）。
