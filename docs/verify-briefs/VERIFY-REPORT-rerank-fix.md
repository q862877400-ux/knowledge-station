# 独立复核报告 · 批次 `rerank-fix`（施工总纲 P0·0.7 修复）

- **复核对象**：冻结 tag `verify-freeze-rerank-fix` → commit `ec32f93`（附注标签对象 `6ed6470`）
- **冻结窗口**：`3138898..ec32f93`，`git rev-list --count` = **1**（已独立复核，无夹带）
- **被复核内容**：`reranker.py::rerank` 返回形状缺陷（生产里 rerank 恒空转）的修复
- **复核者**：独立复核者 `verify-rerank-fix`
- **复核方式**：主仓只读；在隔离 worktree `D:/AI/verify-trees/_r10fix`（= 冻结 tag）里跑；真库 `mode=ro`；零网络（`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`）
- **环境**：Windows 11 / 项目 venv `D:/AI/work space/zcode/.venv/Scripts/python.exe` / 真实模型 `BAAI/bge-reranker-base`（本机 HF cache）
- **复核时点**：2026-10-09 13:0x–13:4x（单机单时点）
- **未跑**：`scripts/run-gates.ps1`、`npm run smoke`（按要求禁止并发门禁）；未跑全量 pytest（只跑 `tests/test_reranker.py`）

---

## 〇、总判定

| # | 复核项 | 判定 |
|---|---|---|
| 1 | 修复真的成立（返回形状：旧降序 / 新一一对应；调用方：旧恒等 / 新重排） | ✅ **成立** |
| 2 | 判据有牙（变异还原旧实现 ⇒ 红；SHA 还原 ⇒ 绿） | ✅ **成立**（**4 failed / 3 passed** → **7 passed**） |
| 3 | 那条"空判据"真的修好了（旧版 SKIP、新版真跑且旧实现下会红） | ✅ **成立** |
| 4 | exp-11 读数可复现 | ✅ **成立**（重跑 per-query **0 处变化**） |
| 5 | "逐位等价"（修复前 `rerank=True` ≡ `rerank=False`） | ✅ **成立** |
| 6 | D2 登记与代码一致（`_protect_exception_clauses` 恒不生效） | ✅ **成立** |
| 7 | 冻结哈希 7 文件 | ✅ **7/7 逐字符吻合** |
| 8 | 措辞残留 | ⚠ **冻结提交内 5 份文档全部正确标注**；另发现 2 条登记层小问题（见 §八） |

**总判定 = 通过（无 P0、无 P1）**。被复核者自报的每一条结论均**独立复现**。仅 4 条 **P2** 级登记项（口径/边界），不影响结论成立。

---

## 一、修复真的成立（主项）

**跑了什么**：在副本 `var/tmp/probe-rerank-order.py`（真实模型），直接调 `reranker.rerank(query, texts)` 与 `hybrid_engine._rerank_results(query, results, top_k=3)`；同一脚本加 `--old` 把 `rerank` 换回**旧降序实现**（照 `ec32f93` diff 里的 `-` 行原样还原）再跑一次。构造：正确条款（动火作业监护）**刻意放在下标 2**，另两条是无关干扰项。

**看到什么**：

| | `rerank()` 返回 | 是否降序 | argmax | `_rerank_results` 输出顺序 | 输出==输入 | `debug["rerank_score"]` |
|---|---|---|---|---|---|---|
| **旧** | `[9.6354, -0.9695, -4.0088]` | **True** | **0**（≠正确下标 2） | `[c0,c1,c2]` | **True（恒等）** | 9.6354 贴在 **c0**（错条款） |
| **新** | `[-4.0088, -0.9695, 9.6354]` | False | **2**（正确） | `[c2,c1,c0]` | **False（真重排）** | 9.6354 贴在 **c2**（对条款） |

**判定**：**成立**。旧版：`rerank` 返回已降序列表 ⇒ 调用方 `sorted(range(n), key=lambda i: scores[i], reverse=True)` 作用在降序输入上退化成**恒等置换** ⇒ 输出顺序 == 输入顺序（rerank 阶段恒空转），且分数贴到错条款。新版：一一对应、真的重排、分数贴对条款。**与声称完全一致**。

（真实模型确认：`is_available()=True`、`offline_reason=None`，分数是模型真实输出。）

---

## 二、判据有牙（变异）

**跑了什么**：把副本 `src/core/retrieval/reranker.py` 的 `rerank` 用 `Edit` 换回**旧降序实现** ⇒ `pytest tests/test_reranker.py -q`；随后 `git checkout HEAD -- src/core/retrieval/reranker.py` 还原（`git hash-object` 与冻结 blob `4a39cb7f…` 逐字符相同）⇒ 再跑一次。

**看到什么**：
- 变异版：**`4 failed, 3 passed in 5.19s`**。红的正是预测的 4 条：
  `test_reranker_scores_align_with_input` / `test_reranker_rejects_length_mismatch` / `test_reranker_pipeline_reorders_by_score` / `test_reranker_real_model_reorders`。
  （真模型那条红的断言：`argmax=0`，分数 `[9.6354, -0.9695, -4.0088]` ⇒ `assert 0 == 2`。）
- 还原版：**`7 passed in 2.41s`**。

**判定**：**成立**。`4 failed / 3 passed` 与 `7 passed` 与声称**逐字吻合**，判据不是空闸门。

---

## 三、那条"空判据"真的修好了

**跑了什么**：`git checkout 3138898 -- tests/test_reranker.py src/core/retrieval/reranker.py` 取旧版（旧用例名 = `test_rerank_real_model_reorders`，注意**旧名不含子串 `reranker`**），单跑 `pytest tests/test_reranker.py::test_rerank_real_model_reorders -rs`。

**看到什么**：
- 旧版：`1 skipped`，skip 原因 = **"reranker 模型未下载，跳过真实模型用例"**（`-rs` 打印）。
- 新版（冻结）：在 §二 的变异运行里该用例**真的执行**（`AssertionError` 而非 skip），旧实现下**红**；还原后 **pass**。

**根因独立确认**：`tests/conftest.py::_rerank_offline_for_tests` 的豁免条件是 `if "reranker" in request.node.name`（**用例函数名**，非模块名）。旧名 `test_rerank_real_model_reorders` **不含 `reranker`** ⇒ 照常被强制离线（`is_available=False`）⇒ 恒 SKIP。新版改名 `test_reranker_real_model_reorders`（含 `reranker`）⇒ 豁免生效；且 `monkeypatch` 把 `get_settings` 指回真实 `%APPDATA%\KnowledgeStation\models` ⇒ 模型找到、用例真跑。

**判定**：**成立**。① 旧版确实**永远 SKIP**（长期假绿）；② 新版**真跑**且旧实现下**会红**。原版断言 `scores[0] > scores[2]` 在旧降序列表上**恒真**（空判据）—— 独立确认：旧探针返回 `[9.6354, -0.9695, -4.0088]`，`scores[0] > scores[2]` 与"哪条正确"无关，恒真。

---

## 四、exp-11 读数可复现

**跑了什么**：`var/tmp/recompute-exp11.py` 从 `per-query-before-fix.jsonl` / `per-query-after-fix.jsonl` 独立重算；再用副本冻结脚本重跑 after 臂：
`.venv/Scripts/python.exe eval/recall-funnel/exp-11-rerank-fix/measure-rerank-ab.py --out verify-after`（真库 `mode=ro`、零网络；`exit 0`，真库 mtime 未变）。

**看到什么**：

| 检查 | 独立读数 | 声称 | 判定 |
|---|---|---|---|
| 仪器对照 A 臂（`ids_a8`+`K8.hit_a`）修复前 vs 后不一致 | **0 / 171** | 0/171 | ✅ |
| 修复前 B 臂 == A 臂（K8 `same_order`） | **171 / 171** | 171/171 | ✅ |
| 修复后 B 臂 != A 臂（K8） | **171 / 171**（`same_order=0`） | 171/171 | ✅ |
| `n_reordered`（K8） | 修复前 **0/120、0/171** → 修复后 **120/120、171/171** | 同 | ✅ |
| 汇总（`hit_a/hit_b/delta_n/flip_in/flip_out/mcnemar_p/n_reordered`） | 重算 **逐格 == `result-*.json`**（before/after 各 4 格全 OK） | 同 | ✅ |
| 主终点 K8 翻进 / 翻出 | **2 / 0**（i=117、i=130，与 README 逐条相同） | 2/0 | ✅ |
| `rerank_offline` | **0** | 0 | ✅ |

**重跑 after 臂 vs 冻结 `result-after-fix.json`**：
- 汇总 JSON：`diff`（剔除 `out`/`generated_at`/`elapsed_s`/`p50`/`p90`/`max`）⇒ **无差异**。
- per-query 逐条比对（`ids_a8`/`ids_b8`/`n_candidates`/`n_kept`/`rerank_offline` + K8/K20 的 `hit_a/hit_b/same_order/rank_a/rank_b`）⇒ **全部 0 处变化**。
- 唯一变化：`latency_rerank_s`（p50 1.0702 vs 1.1006、p90 2.0038 vs 2.1469、max 2.5443 vs 3.0877）与 `elapsed_s`（413.6 vs 408.0）—— **负载噪声，非结构性**。

**为什么这次连"小差异"都没有**：真库 `clause_revision` 本次实测 = **663,634**，与冻结 README 记的 **663,634 一致** ⇒ 复核窗口内**库未增长**。故结构性读数与逐条读数**完全复现**。（若库增长，按边界仍可能变，见 §九。）

**判定**：**成立**。结构性读数（`n_reordered` 等）**不变**，与声称一致。

---

## 五、"逐位等价"这个说法成不成立

**跑了什么**：`var/tmp/probe-equivalence.py`（真库只读）。在**旧实现**下对 15 条真实查询各跑两臂：`perform_hybrid_search(q, top_k=8, rerank=True)`（生产默认值）vs `rerank=False`，比 `clause_revision_id` 列表；再用**新实现**跑同 15 条作对照。

**看到什么**：
- **旧实现：`rerank=True` vs `rerank=False` 逐位不同 = 0 / 15** ⇒ **完全等价**。
- 新实现：**15 / 15 不同** ⇒ 重排真的发生（修复后不再等价）。

**调用点盘点**（全仓 `perform_hybrid_search(`/`search_with_details(`）：
- `src/core/api/server.py:1833`（`async def chat_completions`，主问答路径）→ 本批**显式 `rerank=False`**（修复前走默认 `True`）。
- `src/core/vision/local_vision.py:111` → 本批**显式 `rerank=False`**（修复前走默认 `True`）。
- `src/core/llm/ks_answer.py:663` → `rerank=rerank`，而 `ks_answer.py:623` 是 `bool(params.get("rerank", False))` ⇒ **默认 False**，且该文件**本批未改** ⇒ 它本来就没开重排。
- 其余调用点全在 `tests/`、`eval/`、`tools/`、`var/`（非生产运行路径）。
- `perform_hybrid_search` 函数签名默认 `rerank: bool = True`（`hybrid_engine.py:171`）确认。

**判定**：**成立**。修复前"默认 `rerank=True`"确实等价于关闭（恒等置换）；两处隐式 `True` 的调用点已 pin `False`；`ks_answer` 本就 `False`。**不构成新的生产行为改动**。声明与代码一致。

---

## 六、D2 登记与代码一致吗

**跑了什么**：`var/tmp/probe-exception-protect.py` 直接调 `hybrid_engine._protect_exception_clauses`，两种形态：
① **真实形态**：`kept` 初始长度 == `top_k`（= `_rerank_results` 里 `ordered[:top_k]` 的真实长度）；② **用例形态**：`kept` 初始长度 < `top_k`。

**看到什么**：

| 形态 | `kept` 初始长度 / `top_k` | 传入 kept | 返回 | 例外是否保留 |
|---|---|---|---|---|
| **真实形态** | 2 / 2 | `[c0,c1]`（c2 含但书） | `[c0,c1]` | **False**（被 `return kept[:top_k]` 切掉） |
| **用例形态** | 2 / 3 | `[a,b]`（c 含但书） | `[a,b,c]` | True |

**判定**：**成立**。真实路径 `kept` 长度**恒 == `top_k`**（`_rerank_results` 只传 `ordered[:top_k]`），于是 `_protect_exception_clauses` 里 append 的例外条款被最后一句 `return kept[:top_k]` **原样切掉** ⇒ **恒不生效**。既有用例 `test_rerank_exception_clause_kept` 用的 `kept` 长度 2 < `top_k` 3 是**真实路径不会出现的形态** ⇒ 那条判据测的是不存在的场景。**与 docstring 登记、README §五 逐字一致**。

**影响面**：本批决定 `rerank=False` 接生产 ⇒ `_protect_exception_clauses` 只在 `rerank=True` 时被调用 ⇒ **当前不可达、不产生新风险**；但它是"接重排进生产"的前置条件。登记正确。

---

## 七、冻结哈希（7 文件）

**跑了什么**：`git show verify-freeze-rerank-fix:<path> | sha256sum`（**不用工作区文件**，因 `core.autocrlf=true` 工作区是 CRLF）。

**看到什么**（前 16 位，全部**逐字符吻合**）：

| 文件 | 实测 | 预期 |
|---|---|---|
| `src/core/retrieval/reranker.py` | `d37f72f4a89f1fe3` | `d37f72f4a89f1fe3` ✅ |
| `src/core/retrieval/hybrid_engine.py` | `f539e919d0667d4a` | `f539e919d0667d4a` ✅ |
| `src/core/api/server.py` | `510fec3f01b66d44` | `510fec3f01b66d44` ✅ |
| `src/core/vision/local_vision.py` | `8a4fa87138f122b6` | `8a4fa87138f122b6` ✅ |
| `tests/test_reranker.py` | `859edf6da5c4de48` | `859edf6da5c4de48` ✅ |
| `eval/recall-funnel/exp-11-rerank-fix/stop-loss.json` | `fc112b691540086b` | `fc112b691540086b` ✅ |
| `eval/recall-funnel/exp-11-rerank-fix/README.md` | `0736969c14c88ca6` | `0736969c14c88ca6` ✅ |

**判定**：**7/7 通过**。

---

## 八、措辞残留（含两条登记层发现）

**冻结提交 `ec32f93` 内**（`git show --stat ec32f93`）改动面：`docs/CHANNEL-COVERAGE-PLAN.md` / `docs/RETRIEVAL-LONG-RANGE-PLAN.md` / `docs/research/lay-gap-decomposition.md` / `docs/research/solutions-for-open-problems.md` + `eval/.../exp-11-rerank-fix/*` + 4 个 `src` 文件 + `tests/test_reranker.py`。

逐份读：

| 文档 | 是否还有未标注的旧话 | 备注 |
|---|---|---|
| `eval/.../exp-11-rerank-fix/README.md` | ❌ 无 | 缺陷/修法/读数/判决/D2 与实测逐条吻合 |
| `docs/RETRIEVAL-LONG-RANGE-PLAN.md` P0·0.7 段 | ❌ 无 | L119 `0.7` 标 `✅ 已修（2026-10-09）`；L120 `0.7-修` 详述；旧话原文保留 + 更正，符合本仓约定 |
| `docs/research/solutions-for-open-problems.md` F2b | ❌ 无 | F2 旧话保留（L96），F2b 更正（L97） |
| `docs/research/lay-gap-decomposition.md` | ❌ 无 | L443–451、L484–488 均带 `✅ 2026-10-09 就地更正` |
| `docs/CHANNEL-COVERAGE-PLAN.md` R15 | ❌ 无 | "渠道线零改动、仅登记"、"线上行为与 R14 逐位等价" |

### 发现 P2-1：两条"归属层"文件**不在冻结提交内**

`ec32f93` 的提交信息把 `docs/DEVELOPMENT-HISTORY.md §10.214` 与 `docs/NEXT-DEV-PLAN-2026-09-28.md 登记块` 列为**归属层**，但 `git show --stat ec32f93` **不含这两个文件**。

独立追查（`git log` 图：`3138898 → ec32f93 → 5c68f47 → 8d49641 → 82ed03d(HEAD)`）：
- 冻结 tag 下 `docs/DEVELOPMENT-HISTORY.md` **不存在 `§10.214`**（`git show verify-freeze-rerank-fix:... | grep "10.214"` 零命中）；`docs/NEXT-DEV-PLAN-2026-09-28.md` 亦**无 rerank/P0·0.7 登记块**（只命中 E4 行）。
- 二者由**紧接的下一提交 `5c68f47`** 加入（该提交 stat：`DEVELOPMENT-HISTORY.md +2`、`NEXT-DEV-PLAN +29`；其 diff 里确有 `§10.214` 全行与"🆕 2026-10-09…修总纲 P0·0.7"块）。
- 内容本身**正确、无旧话残留**（`§10.214` 说"修了但判决不接生产"，D2 标"本批未修、已登记"，与实测一致）。

⇒ 提交信息**声称的归属层与冻结提交实际内容不符**（文档晚一个提交落地）。属**追溯/口径**问题，不影响修复正确性与读数。**判 P2**（登记）。

### 发现 P2-2：`§10.214` 同一句里混用两套哈希约定

`§10.214` 的产物行写：`reranker.py（d37f72f4…）+ hybrid_engine.py（docstring，3d440400…）`。独立核：
- `reranker.py` 的 `d37f72f4…` = **git blob（LF）** 哈希（= `git show tag:path | sha256sum`）✅ 正确。
- `hybrid_engine.py` 的 `3d440400…` = **工作区（CRLF）** 哈希；其 **blob（LF）** 哈希是 **`f539e919d0667d4a`**（与冻结核对法一致）。出处见 `.workbuddy-ai/memory/AUTO-CHAIN-HANDOFF.md:270`（"工作区 `3d440400…` vs blob `f539e919…`"）。

⇒ **同一句里两个文件用了两套约定**，正是本仓 §10.210 F2 已登记的"冻结哈希对 EOL 敏感且两处约定不一致"那个跨批次通用坑。**判 P2**（登记；不影响冻结核对——我用 blob 法 7/7 全过）。

### 发现 P2-3（观察）：`stop-loss.json` 的 `registered_at` 晚于其 mtime

主仓实测 mtime 顺序：`stop-loss.json 12:46:55` < `result-before-fix.json 12:56:48` < `result-after-fix.json 13:03:55` < 提交 `13:08:57` ⇒ **预注册顺序成立**（跑前落盘）。但 `stop-loss.json` 内 `registered_at` 写 `12:58`（晚于自身 mtime 12:46）。属字段口径小瑕疵（不影响"预注册早于读数"）。**判 P2**（登记）。注：mtime 是可被任意设置的弱证据，此处仅作**一致性**佐证。

### 发现 P2-4（观察）：`RETRIEVAL-LONG-RANGE-PLAN.md` L125–127 措辞略陈旧

L125 "不做：…不动 reranker"、L127 "真要动，先做 0.7" —— 在 0.7 已修的今天，"先做 0.7"这句略陈旧；但语义上"**生产行为**不动 reranker（`rerank=False`）"**仍然成立**（本批正是如此）。**判 P2**（登记）。

---

## 九、边界与未验（如实写）

- **单机单时点**：本报告是**一台机器、一个时点**（2026-10-09 13:0x–13:4x）的复核。
- **真库只读、规模会变**：本次实测 `clause_revision` = **663,634**（与冻结读数同，复核窗口内**未增长**）⇒ 依赖库内容的读数（如"翻进是哪两条"）本次**完全复现**；库一旦增长，`n_reordered` 这类**结构性**读数应稳，但"翻进集合/名次"可能变。
- **未跑门禁/变异并发**：按要求**未跑** `scripts/run-gates.ps1`、**未跑** `npm run smoke`。
- **未跑全量 pytest**：只跑 `tests/test_reranker.py`（7 条），未跑整仓回归。
- **模型**：真实模型 `BAAI/bge-reranker-base` 本机可用（`is_available=True`），未走降级。
- **"逐位等价"探针样本**：15 条真实查询（`benchmark-v2.jsonl` 前 15 条）；结论是**结构性**的（旧实现恒等置换），不依赖样本量。exp-11 的 before 臂 **171/171** 亦从另一侧印证。
- **D2 探针**：直接构造 `kept` 长度 == `top_k` 的形态调用，未走完整 `_rerank_results`（后者需模型+库）；但 `_rerank_results` 传 `kept = ordered[:top_k]` 使长度恒等于 `top_k`，已由源码 `hybrid_engine.py:480` 静态确认。
- **主仓**：全程只读，未 commit / 未 push / 未改任何主仓文件；隔离 worktree 已 `git worktree remove --force` + `prune` 清除。
- **证据留存**：探针脚本、运行日志、重跑产物（`result-verify-after.json` / `per-query-verify-after.jsonl`）已拷至 `D:/AI/verify-trees/_r10fix-artifacts/`。

---

## 十、附：复核用到的命令（可复跑）

```bash
# 冻结核
git rev-parse verify-freeze-rerank-fix            # 附注标签对象
git rev-list --count 3138898..ec32f93             # = 1
for f in src/core/retrieval/reranker.py src/core/retrieval/hybrid_engine.py \
         src/core/api/server.py src/core/vision/local_vision.py tests/test_reranker.py \
         eval/recall-funnel/exp-11-rerank-fix/stop-loss.json \
         eval/recall-funnel/exp-11-rerank-fix/README.md; do
  git show verify-freeze-rerank-fix:$f | sha256sum | cut -c1-16
done
# 隔离副本（独立命令，勿在主仓目录内跑）
git worktree add D:/AI/verify-trees/_r10fix verify-freeze-rerank-fix

# 探针（副本内，带离线环境变量）
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "D:/AI/work space/zcode/.venv/Scripts/python.exe" var/tmp/probe-rerank-order.py [--old]
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "D:/AI/work space/zcode/.venv/Scripts/python.exe" var/tmp/probe-equivalence.py
"D:/AI/work space/zcode/.venv/Scripts/python.exe" var/tmp/probe-exception-protect.py

# 变异 / 测试
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "D:/AI/work space/zcode/.venv/Scripts/python.exe" -m pytest tests/test_reranker.py -q
# 还原：git checkout HEAD -- src/core/retrieval/reranker.py

# 重跑 after 臂
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "D:/AI/work space/zcode/.venv/Scripts/python.exe" \
  eval/recall-funnel/exp-11-rerank-fix/measure-rerank-ab.py --out verify-after

# 清理
git worktree remove --force D:/AI/verify-trees/_r10fix && git worktree prune
```
