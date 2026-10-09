# VERIFY-REPORT — `exp-15-pool-depth-fusion` 独立复核（第 15 轮）

- 复核人：general-purpose-1（独立复核者）
- 复核日期：2026-10-09
- 冻结 tag：`verify-freeze-exp15-pool-depth-fusion` → `cc42d9f600b549ab28156dca36dadb57b18fccda`
- 提取方式：`git worktree add --detach D:/AI/verify-trees/exp15-tree cc42d9f`
- 只读核验；未改主仓任何文件；未碰 `tools/gov-qa/**`。

**报告首部**：worktree `git rev-parse HEAD` = `cc42d9f600b549ab28156dca36dadb57b18fccda`；`git status --short` = 空（干净）。
**报告尾部**：worktree `git rev-parse HEAD` = `cc42d9f600b549ab28156dca36dadb57b18fccda`；`git status --short` = 空；主仓 HEAD 仍 = `cc42d9f...`。

---

## 0. 总判定

**PASS —— 无 P0。**

主终点 `fused@20`（headline 120）的 **7 臂全部逐格复现**；oracle 三个数、`池里有 gold` 两组数、`42 条里 ≤20=14 条`、仪器对照（今天活库重跑 **14/14**）、17 条判据、**我自写的 10 处变异（10/10 被抓、逐字节还原）** 均独立成立。**判决「整格都不动」成立。**

但有 **2 条 P1 + 1 条 P2**（均不影响主终点与判决）：

- **P1-1**：`result.json` 与 `README` 表里的 **`@100`（及 `result.json` 的 `fused_top1000`）实为 `@20` 的复制**。聚合用「只存了 top-20 内名次」的 `rank` 字段去算 `@100/@1000`，**存了却从未使用** `hit@100`；真 `@100` 是 11.67/14.17/15.00/15.83/13.33/12.50/10.00%，与上报差最大 **+7.5pt**。这是预注册的副终点 `fused@100`，读数不真。
- **P1-2**：6 处文档的「与生产**逐条完全相同**」是**超出证据的全称句**。证据只有「翻进 0 / 翻出 0」（= 命中**状态**逐条相同）。我实算 top-20 **名单**：`A0_prod` vs `P1000_rrm60` 抽 14 条里 **5 条不同**（i=84 连 gold 名次都从 1→7），vs `P1000_doc3` 有 **7 条不同**。
- **P2-1**：3 处把归属层写成「开发史 **§10.223**」，实际是 **§10.224**（§10.223 是别人的未提交件，本提交未含）。

---

## 1. 冻结与改动面（逐条核）

| 核项 | 命令 | 结果 |
|---|---|---|
| tag→commit | `git rev-parse verify-freeze-...^{commit}` | `cc42d9f...` ✅ |
| 窗口提交数 | `git rev-list --count cc042eb..cc42d9f` | `1` ✅ |
| 改动面 | `git show --name-only cc42d9f` | 14 文件；**`src/`、`plugin/` 为空** ✅ |
| 未卷入 §10.223 | `git show cc42d9f:docs/DEVELOPMENT-HISTORY.md \| grep -c 10.223` | `0` ✅ |
| §10.224 在 | 同上 `grep -c 10.224` | `1` ✅ |

提交时间 `2026-10-09 16:31:58 +0800`；`stop-loss.json registered_at = 2026-10-09T16:21:36+0800` ⇒ 预注册**早于**提交 ~10 分钟 ✅（局限见 §6）。

---

## 2. 主终点独立重算（自写脚本，**不 import** 作者 `aggregate_runs`）

脚本 `D:/AI/verify-trees/recompute_exp15.py`（只读 `per-query.jsonl`，自实现 hit_rate/中位/翻进翻出/McNemar 精确/oracle）。**7 臂逐格对上作者声称**：

| 臂 | 池中位(我/称) | @20(我/称) | Δ@20(我/称) | 进/出(我/称) | p(我/称) |
|---|---|---|---|---|---|
| `A0_prod` | 40/40 | 8.33/8.33 | — | — | — |
| `P100_rrf60` | 197/197 | 10.00/10.00 | +1.67/+1.67 | 2/0 | 0.5 |
| `P1000_rrf60` | 1930/1930 | 10.00/10.00 | +1.67/+1.67 | 3/1 | 0.625 |
| `P1000_rrf200` | 1930/1930 | 8.33/8.33 | +0.00 | 5/5 | 1.0 |
| `P1000_rrf1000` | 1930/1930 | 6.67/6.67 | −1.66/−1.66 | 5/7 | 0.7744 |
| `P1000_rrm60` | 1930/1930 | 8.33/8.33 | +0.00 | 0/0 | 1.0 |
| `P1000_doc3` | 40/40 | 8.33/8.33 | +0.00 | 0/0 | 1.0 |

oracle（我自算）：`@20 = 15/120 = 12.5%`、`@100 = 26/120 = 21.67%`、`@1000 = 42/120 = 35.0%` ✅ 与声称逐格一致。
`池里有 gold`：`A0_prod(=oracle@20)=15`、`P1000(=oracle@1000)=42` ✅。
`42 条里 gold 最好深读名次`（min over fts/vec 的非空名次）：**≤20 有 14 条** ✅（我另算：20<x≤100 有 11、100<x≤1000 有 16、无 1，合计 42）。
**附带更正**：README §5.2 表头把这三个桶写成「≤100 / ≤1000」（读起来像累计），实为**互斥分桶**（14+11+16+1=42）；累计值应是 ≤100=25、≤1000=41。属表述，不属读数错。

## 2.1 ★ P1-1：`@100` 是 `@20` 的复制（聚合漏用 `hit@100`）

- 代码证据：`run.py:304` 每臂只存 `"rank": exp7.rank_of(gold, lst20)`（**top-20 内名次**）；`run.py:207` `rec = {f"fused_top{t}": _hit_rate(r, t) for t in (20,100,1000)}` 用这个 rank 算 `@100/@1000`。因 `rank` 只有 1..20 或 None ⇒ `fused_top100 ≡ fused_top20`。而 `run.py:305` 存了 `"hit@100"`，聚合**从未读取**。
- 我自算「真 @100」（用 `hit@100` 字段） vs 上报：`A0_prod 11.67 vs 8.33`、`P100 14.17 vs 10.00`、`P1000_rrf60 15.00 vs 10.00`、`rrf200 15.83 vs 8.33`、`rrf1000 13.33 vs 6.67`、`rrm60 12.50 vs 8.33`、`doc3 10.00 vs 8.33`。
- 合成数据直接证明（喂作者自己的 `aggregate_runs`：某条 `rank=None` 但 `hit@100=True`）：上报 `fused_top20=0.0 / fused_top100=0.0 / fused_top1000=0.0`，真 @100 应为 `100.0`。
- 影响：**主终点 `@20` 与判决不受影响**；但 `stop-loss.json` 明列 `fused@100` 为副终点，`result.json`/README 表在报它 ⇒ 读数不真，**须修**（把 `rank` 改存 `lst100`/`lst1000` 内名次，或聚合改读 `hit@100`）。

## 2.2 时效过滤不是「池 15 / 前 20 10」缺口的原因（排除了一个疑点）

我查了 oracle@20 为真的 15 条 gold 的 `legal_status`：**15 条全部 `effective`**，全库 120 条 gold **无一被时效过滤**。⇒ 池内 15 vs 前 20 10 的差**确系排序**，README 的机制叙述成立 ✅。

---

## 3. 仪器对照（独立复现，今天活库）

脚本 `D:/AI/verify-trees/repro_instrument.py`：`mode=ro` + `load_vec_extension` + `.venv` python；对 **14 条**（全部 10 条 `A0_prod` 命中 + 4 条未命中，跨 3 个 subset）用**生产函数** `search_with_details(top_k=20, rerank=False, channels=[exact,fts,vec,modality], boost_bookmarks=False)` 重跑，并自算 `A0_prod` 名单（`build_rankings + exp7.fuse(...,"A") + exp7.order(...,20)`）。

- **复现 14/14**：`prod_ids == a0` 全部 True；gold 名次逐一相等（12,3,1,7,2,10,2,9,2,2 + None×4）。
- 真库 `clause_vec` 行数 = **663,634**，与声称一致；跑前跑后 mtime **未变**。
- ⚠ 真库 mtime = `2026-10-09 16:30:56`，**晚于**台账（约 16:26）—— 期间库被 touch 过；但我的 14/14 复现说明**该变化未影响这批查询**。如实记录：库文件 mtime 已变，复现率仍 14/14。
- 附带复核 R19 的「模态触发 5/120」：我自数 `modality_filter` 非空 = **5/120** ✅。

---

## 4. 判据有牙（自写变异，作用在 worktree 副本）

脚本 `D:/AI/verify-trees/mutate_worktree.py`（**不碰主仓**）。10 处变异 **10/10 被抓**，`run.py` **逐字节还原**（`sha256` 前后一致 = `a22ed7b1...`，worktree `git status` 仍空）：

`M1 _hit_rate 闭→开`✅、`M2 翻进翻出方向对调`✅、`M3 exact 按 depth 截断`✅、`M4 A0_prod depth 20→25`✅、`M5 oracle_pool 漏 modality`✅、`M6 pool_median 上→下中位`✅、`M7 缺条不报错`✅、`M8 fused_hit_n 改数 @20`✅、`M9 identical_count 恒等 compared`✅、`M10 by_subset 阈值 20→10`✅。
（注：M2/M7 需处理 CRLF；作者脚本用 `read_bytes/write_bytes` 保 CRLF 的做法正确。）

`pytest tests/test_pool_depth_ruler.py -q` → **17 passed** ✅（与声称「17 条」一致）。

## 4.1 「唯一变量」成立

`build_rankings`（`run.py:119-137`）在**每一条臂**里 `exact`/`modality` 都是 `list(deep[...])` 原样全量，只有 `fts`/`vec` 受 `depth`/`doc_div` 影响 ✅。单测 `test_exact_and_modality_are_never_truncated` 覆盖。

## 4.2 ★ P1-2：「逐条完全相同」超出证据

`flip_in=flip_out=0` 只证明**命中状态**逐条相同，**不等于名单相同**。我在活库重算 top-20 **名单**：`A0_prod` vs `P1000_rrm60` 抽 14 条中 **5 条不同**（i=13 全 20 位次序皆变；i=84 差 7 位、gold 名次 1→7）；vs `P1000_doc3` **7 条不同**。该措辞出现在 exp-15 README §5.3/§七、DEV-HISTORY §10.224、RETRIEVAL 第 4 刀、NEXT-DEV 第 15 轮块、CHANNEL R19、recall-funnel README §5.11 **共 6 处**。⇒ 若读作「名单相同」即与事实不符，**须改为「命中状态（@20）逐条相同」**。（若作者本意本就是「命中状态」，则降为 P2。）

---

## 5. 归属层六处一致性

六处（exp-15 README / DEV-HISTORY §10.224 / RETRIEVAL 第 4 刀 / NEXT-DEV 第 15 轮块 / CHANNEL R19 / recall-funnel README §5.11）的**数字与判决全部一致**：8.33/10.00/10.00/8.33/6.67/8.33/8.33、池中位 40/197/1930…/40、oracle 12.50/21.67/35.00、进-出、p、判决「整格都不动」、代价 717.5/738.6/1108.9。**未发现把 oracle 说成可实现、也未把 +1.67pt 说成「有效」**（反而明确判「放弃」）✅。§5.2 分桶表头的表述见 §2。

**P2-1**：`docs/RETRIEVAL-LONG-RANGE-PLAN.md:708`、`docs/CHANNEL-COVERAGE-PLAN.md:2748`、`exp-15 README:6` 均写「开发史 §10.223」；实际条目是 **§10.224**（`git show cc42d9f:docs/DEVELOPMENT-HISTORY.md | grep -c 10.223 = 0`）。§10.223 是别人的未提交件，本提交未含 ⇒ 三处为**错链**，须改 §10.224。

---

## 6. 预注册契约与代价

- `stop-loss.json.arms`（7 键）与 `run.py ARMS` **完全一致** ✅；`primary_endpoint` 以 `fused@20` 起 ✅；`registered_before_run=true`。
- `registered_at=2026-10-09T16:21:36+0800` **早于**提交时间 `16:31:58` ✅。**局限**：git 不保存文件 mtime，无法从冻结提交独立取到 `runs.jsonl`/`result.json` 的原始 mtime；只能以「提交时间 > registered_at」+ 文件内时间戳作旁证。
- 代价探针（我自写只读版 `D:/AI/verify-trees/probe_knn.py`）：`clause_vec` 行数 **663,634**（与声称一致）；p50 `k=20 906.4ms / k=100 914.2ms / k=1000 1298.0ms`，比值 `1.009 / 1.432`。**方向复现**（k=20≈k=100、k=1000 ≈1.4–1.55×），**绝对值不复现**（我的机器此刻更慢，属计时抖动）。

---

## 7. 我没能验的部分（不许当已验）

1. **名单级「完全相同」的否定**只覆盖抽样 14 条（未跑全 120）—— 但已足以否证全称句。
2. **真 @100/@1000 的逐臂数值**是我从 `per-query.jsonl.hit@100` 重算的；`hit@1000` 未存，故真 @1000 无法从台账算出。
3. **代价绝对值**未复现（机器负载相关）；只验了行数与比值方向。
4. **预注册的物理 mtime**无法从 git 独立取得（见 §6 局限）。
5. 未重跑 `run.py` 全量（约 4–5 分钟真库 KNN）；未跑重排器相关（本批不涉及）。

---

## 8. 建议处置

- **P1-1（必改）**：修正 `result.json`/README 的 `@100`（及 `fused_top1000`），并给尺子补一条牙（@100 必须来自 `hit@100`）。
- **P1-2（必改）**：6 处「逐条完全相同」改为「命中状态（@20）逐条相同」。
- **P2-1（可改）**：3 处 §10.223 → §10.224。
- 其余（主终点、oracle、仪器对照、判据、预注册、唯一变量、代价方向）**复核通过**。
