# 独立复核报告 · 批次 `p010-long-tail`

**复核对象**：总纲 P0·0.10「长条款的尾巴没进向量」只读量化（自动续接链第 11 轮）
**冻结 tag**：`verify-freeze-p010-long-tail` → `98aeb52`
**冻结窗口**：`f0062c0..98aeb52` = **1 个提交**（12 文件，见下）
**复核者**：general-purpose-1（独立于作者）
**复核时间**：2026-10-09
**结论**：**PASS（无 P0；1 条 P1、4 条 P2）** —— 作者的**全部关键读数逐位复现**；判据**有牙**（三处变异均被当场抓红并按 SHA256 还原）；判决由证据支持。P1 = 余弦复验组读数**无脚本落盘**、不可从冻结产物直接复跑（复核者自写脚本复现通过）。

---

## ① 复核对象与提取树（HEAD / status 首尾）

提取树：`git worktree add D:/AI/verify-trees/p010 98aeb52`

| 时点 | `git rev-parse HEAD` | `git status --short` |
|---|---|---|
| **首**（建树后，跑任何东西前） | `98aeb52da005e2a9f23318758287c8faafa627fe` | 空（干净） |
| **尾**（跑完尺子/探针/变异并还原后） | `98aeb52da005e2a9f23318758287c8faafa627fe` | 空（干净） |

```bash
cd "D:/AI/verify-trees/p010"
git rev-parse HEAD        # 98aeb52da005e2a9f23318758287c8faafa627fe（首尾一致）
git status --short        # 首尾均空
git worktree list | grep p010   # D:/AI/verify-trees/p010  98aeb52 (detached HEAD)
```

**主仓未被本次复核弄脏**：主仓 `HEAD` 仍 `98aeb52`，且 `git status --short -- eval/recall-funnel/exp-12-long-clause-tail/ tests/test_long_clause_tail_ruler.py docs/RETRIEVAL-LONG-RANGE-PLAN.md` **无输出**（我全部改动都只落在提取树里）。

**冻结窗口内容核对**（无夹带）：
```
$ git show --stat --oneline 98aeb52
12 files changed, 3642 insertions(+), 1 deletion(-)
 docs/CHANNEL-COVERAGE-PLAN.md        |  20 +
 docs/DEVELOPMENT-HISTORY.md          |   1 +
 docs/NEXT-DEV-PLAN-2026-09-28.md     |  25 +
 docs/RETRIEVAL-LONG-RANGE-PLAN.md    |   3 +-
 eval/recall-funnel/README.md         |  11 +
 .../exp-12-long-clause-tail/{README.md,measure.py,probe-tail-blindspot.py,
     result.json,probe-tail-blindspot.json,probe-tail-blindspot.v1.json}
 tests/test_long_clause_tail_ruler.py |  91 +
```
⇒ **只含作者自己的产物 + 归属层文档**；**未碰** `clause_repo.py` / `text_utils.py` 等生产代码，**未碰** `benchmark-v2.jsonl` / `funnel-summary.json` / `funnel-per-query.jsonl` 考卷数据（`git show --name-only 98aeb52` 逐一核过）。与"只读真库、不改 schema、不写库、零网络"的声称一致。

---

## ② 逐条复现表（作者数 vs 我实测数，逐位比）

真库 `%APPDATA%\KnowledgeStation\database\knowledge.db`，`mode=ro`。解释器 `D:/AI/work space/zcode/.venv/Scripts/python.exe`。
跑法：`cd /d D:/AI/verify-trees/p010 && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 <py> eval/recall-funnel/exp-12-long-clause-tail/measure.py`（35 s）与 `.../probe-tail-blindspot.py`（1 m 17 s）。

| # | 读数 | 作者 | 我实测 | 判 |
|---|---|---|---|---|
| 1 | `clause_revision` 总数 | 663,634 | **663,634** | ✅ |
| 1 | `content_text` >512 字 | 13,666 = 2.0593% | **13,666 = 2.0593%** | ✅ |
| 1 | >768 / >1000 / >2000 | 6,364 / 3,920 / 1,070 | **6,364 / 3,920 / 1,070** | ✅ |
| 1 | 最长 / 正文合计 | 4,006 / 68,800,657 | **4,006 / 68,800,657** | ✅ |
| 2 | 代码层截断 `content_text[:512]` | `clause_repo.py:285` / `:426` | **亲眼核：`src/core/storage/clause_repo.py:285` `f"{c.title or ''}\n{c.content_text[:512]}"`、`:426` `f"{title or ''}\n{content_text[:512]}"`** | ✅ |
| 2 | 模型层 `model_max_length` | 512 | **`tokenizer_config.json` = `"model_max_length": 512`** | ✅ |
| 3 | head+title token 中位 | 411 | **411** | ✅ |
| 3 | head+title 超 512 token | 2/4000 = 0.05% | **2/4000 = 0.05%**（新种子另测 1/4000、2/4000 ⇒ 量级稳健） | ✅ |
| 3 | 被丢 token 中位 / 总量 | 181 / 1,511,342 | **181 / 1,511,342** | ✅ |
| 3 | 去代码上限白捡 | 320,441 = 21.2% | **320,441 = 21.2%**（新种子 20.92%–21.28%） | ✅ |
| 3 | 模型窗口仍挡 | 1,190,901 = 78.8% | **1,190,901 = 78.8%** | ✅ |
| 4 | 有 ≥1 tail_only 词 | 13,329 = 97.534% | **13,329 = 97.534%** | ✅ |
| 4 | tail_only 中位 / 去重 | 36 / 117,654（中文≥2 字 70,756） | **36 / 117,654 / 70,756** | ✅ |
| 4 | 尾巴不进向量字符 | 6,627,412 = 9.63% | **6,627,412 = 9.63%**（6,627,412/68,800,657 = 0.09633） | ✅ |
| 5 | 171 条 gold 长度 min/med/p90/max | 31 / 77 / 134 / 270 | **31 / 77 / 134 / 270**（独立从 `v2.gold_cr_id` 查库重算） | ✅ |
| 5 | gold >512 字 | 0 / 171 | **0 / 171** | ✅ |
| 5 | "字面信号只在尾巴" | headline120 0、all171 0 | **headline120 0 / all171 0** | ✅ |
| 6 | `cos(全文, 前 800 字)` | 1.000000（5/5） | **1.000000（5/5）**（自写脚本，见 ③-未验/自证） | ✅ |
| 6 | `cos(全文, 前 512 字)` | 0.9649–0.9989（≠1） | **0.9779–0.9989（≠1）**（另 5 条，范围随样本变，结论"≠1"稳） | ✅ |
| 6 | 模型截断点 | 512 token ≈ 700–760 字 | **≈ 720 字=511 token（cos 0.9988）→ 740 字=531 token（cos 1.000000）** | ✅ |
| 7 | 探针 FTS@100 head / tail | 58.33%（中位 7）/ 75.0%（中位 12） | **58.33%（7）/ 75.0%（12）** | ✅ |
| 7 | 探针 向量@20 head / tail | 54.17% / 25.0% | **54.17% / 25.0%** | ✅ |
| 7 | 探针 向量中位名次 head / tail | 2 / 21 | **2 / 21** | ✅ |
| — | `result.json`（剔 `generated_at`） | — | **与作者提交版逐字段完全相同**（`author==mine: True`） | ✅ |
| — | `probe-tail-blindspot.json` | — | **与作者提交版逐字节相同**（`author==mine: True`） | ✅ |

**独立交叉核对**（不跑作者的 `measure.py`，自写 SQL + 真分词器，脚本 `D:/AI/verify-trees/_p010-scale-verify.py`）：
- 规模六项、gold 长度五项**全部独立复算吻合**；`benchmark 171 条、唯一 gold 79 个、查不到 0`。
- 换随机种子重抽 4000 条（`seed=12345/99999`）：head>512 = 1/4000、2/4000；gain 占比 21.28%、20.92% ⇒ 作者"2/4000"是单种子点估，**量级稳健**。

**逐条判定：全部关键读数复现通过。** 唯一非"逐位相等"的是 `cos(全文,前512字)` 的**下界**（作者 0.9649 / 我 0.9779）——**因样本不同**（作者取哪 5 条未写脚本），"≠1"这一结论不变。

---

## ③ 分级问题清单

### P1（必改）—— 余弦"机制复验"组读数**无脚本落盘**，不可从冻结产物直接复跑

- **现象**：`exp-12/README.md §5`「机制复验（余弦）」的四组读数（`cos(全文,前800)=1.000000`、`cos(全文,前512)=0.9649–0.9989`、逐字加长 ⇒ 截断点 700–760 字）被 `docs/RETRIEVAL-LONG-RANGE-PLAN.md` 0.10-量化 行与 `docs/DEVELOPMENT-HISTORY.md §10.217` **当作已实测事实内联**；但 **exp-12 目录里没有任何计算余弦的脚本**：`grep -rln "cosine\|余弦\|cos(" eval/recall-funnel/exp-12-long-clause-tail/` 只命中 `measure.py`（**仅 docstring 提了一句背景**，代码里**根本没有 cos 计算**）与 `README.md`。`measure.py` 只数 token + 建 head/tail 词集；`probe-tail-blindspot.py` 只做 FTS/向量名次。**二者都不产出余弦读数。**
- **影响**：本批被列"必验类别"的**首要理由**正是"结论由作者自己的检查得出"；余弦组恰是**唯一没有落盘尺子**的那组 ⇒ 冻结产物**不足以自证**该组。
- **复核者自证（结论成立）**：我自写脚本 `D:/AI/verify-trees/_p010-cos-verify.py`（用生产 `embedder.embed_batch`，离线变量 `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`）独立重算：
  ```
  cos(全文, 前800字) = 1.000000  (5/5，1305–1437 字条款)
  cos(全文, 前512字) = 0.977906 / 0.987182 / 0.998908 / 0.977906 / 0.997665  (≠1)
  逐字加长(1390 字)：720 字=511 token cos=0.998840 → 740 字=531 token cos=1.000000
  ```
  ⇒ **读数本身复现通过**，但**证据未随冻结产物交付**。
- **建议**：把余弦复验写成 `exp-12/cosine-recheck.py`（或并入 `measure.py`）补进下一次提交；在那之前，0.10-量化 行/§10.217 里这组数应标"**复核者已独立复现，但原批未落脚本**"。

### P2-1（登记）—— `MODEL_WINDOW=512` 无任何判据钉住（判据盲点）

- **复现**：对 `measure.py` 施加作者**未列**的第 4 处变异 `MODEL_WINDOW = 512 → 256`：
  ```
  $ <py> -m pytest tests/test_long_clause_tail_ruler.py -q
  .....   5 passed in 0.60s        # ← 未被抓住
  ```
- **为什么**：`test_token_drop_partition_*` 都**显式传 `window=512`**（不读常量）；`test_production_still_uses_the_512_char_cap` 只锚 `HEAD_CHARS`（用 `clause_repo.py` 源码 grep）。⇒ `MODEL_WINDOW` 与模型 config 的一致性**无人守**。一旦有人误改，`78.8%` 这组读数会**静默漂移**而测试全绿。
- **建议**：加一条 `assert RULER.MODEL_WINDOW == 512` 或断言它与 `tokenizer_config.json` 的 `model_max_length` 相等（后者更贴近"第二道截断"的语义）。
- **注**：这不是作者"判据造假"——`HEAD_CHARS` 的契约锚（`test_production_still_uses_the_512_char_cap`）是**真锚**（M1 变异当场变红，见 ⑤）；只是**第二道截断**没享受到同等待遇。

### P2-2（登记）—— `gain + residual` 与 `dropped` 差 2，"总量可相加"少了前提

- **复现**：`result.json` 里 `token_gain_if_cap_removed_sum(320,443) + token_residual_loss_sum(1,190,901) = 1,511,344`，而 `token_dropped_sum = 1,511,342`，**差 2**。
- **根因**：恰是那 **2 条 `head_tokens > window`** 的条款——对它们 `dropped = full − head`，而 `gain+residual = 0 + (full − 512) = dropped + (head − 512)` ⇒ 每条多算 1。`measure.py:103-104` 的 docstring **已写明**前提"当 `head_tokens <= window`（实测 99.95%）时 `gain+residual == dropped`"，但 `README.md §二.1` 的表述是"总量**可相加**"，未带前提。
- **影响**：对 21.2%/78.8% 的百分比**无可见影响**（分母换 1,511,342 或 1,511,344 都四舍五入同值）。属**措辞**问题。
- **建议**：README 该句补"（除 2 条 head 自身超窗的条款外，误差 2）"。

### P2-3（登记）—— `result.json` 记录的 `6da94964…` 哈希**不可按常法复现**（口径未记明）

- **复现**：作者在 README §五/§10.217 记"`result.json` 连跑两次剔除 `generated_at` 后逐字节相同（sha256 `6da94964…`）"。我试了常见归一化口径，**没有一个**等于 `6da94964`：
  ```
  文本级删 generated_at 行   : e3eca726…
  json.dumps(indent=2,utf8)  : e3eca726…   (+尾换行 9ea13571…)
  ensure_ascii=True,indent=2 : 74304c40…   (ascii+compact 7dd6789e…)
  compact separators         : 034fc5f6…   sort_keys a88cb0f6…
  ```
- **但实质结论成立**：我**直接比对**了作者提交版 `result.json` 与我**新鲜重跑**的 `result.json`，**剔除 `generated_at` 后逐字段完全相同**（`author==mine: True`）——这比"两个自跑样本相同"更强，已证明**尺子可复现**。
- **建议**：把"剔除 `generated_at`"的**具体归一化代码**（怎么剔、怎么序列化）写进 README，或干脆不记哈希、只记"两次运行内容一致"。

### P2-4（登记）—— 判决理由 ② 把"删一行"与"改 schema"的成本绑在一起，措辞易误读

- 任务点 C 问"有没有漏掉的更便宜修法被错理由否掉"。**核查结论：没有。**
  - 作者**确实**考虑了"只删 `[:512]`"这条更便宜的路，并**用实测**否掉它（只挽回 21.2%）。这是**基于价值**的否，理由成立。
  - 但理由 ② 的措辞"修法是**切子块/多向量**（动 schema + 重建 663,634 条索引）**不是删一行**"把两件事并列，**读起来像**"删 `[:512]` 也要改 schema"——实际删 `[:512]` **只改一行代码、不动 schema**，但仍需**重建 663k 向量**（重建才是主成本）。**判决不变**（重建成本 + 21.2% 低价值 + 向量路边际价值小），但建议把理由 ② 改成"删 `[:512]` 只挽回 21.2% 且**同样要重建 663k 向量**；改 schema 是另一条更贵但更彻底的路"。

### 边界确认（非问题，逐条核过）

- **"影响面 = 结构性零"是否越界**：**未越界**。README §3 标题写"**考卷结构上看不见它**"、正文写"**在当前考卷上**的影响面 = 结构性零"，§四又写"影响面是**上界**……本批考卷里这个上界恰好是 0"，`eval/recall-funnel/README.md §5.8` 亦写"**在当前考卷上**"。⇒ 均限定"当前考卷"，非"真实世界影响为零"。且"0/171"**确实**是"没有对象"（0 条长 gold ⇒ tail 恒空 ⇒ `q_tail_only` 恒 0），README 已明说"不是判据失效，是没有对象"。**诚实。**
- **"去掉 `[:512]` 只挽回 21.2%"是否纯推断**：**不是**。它依赖"模型会截到 512 token"，而该前提有**两处实测**支撑：① `tokenizer_config.json` 的 `model_max_length=512`；② 余弦逐字加长实测截断点 ≈512 token（复核者已独立复现）。⇒ 是**实测支撑的反事实估算**，README 也标为"若只去掉代码上限"。
- **探针构造性偏差**：README §四已自认"head 正是被嵌进去的那段 ⇒ 向量对 head 串更好**在构造上就成立**，探针主要是把机制**量化**、不是新发现"。**诚实。**

---

## ④ 如实登记"未验"的部分

| 项 | 为什么没验 | 证据强度 |
|---|---|---|
| `run-gates.ps1` / `npm run smoke` / 全量 pytest | 任务明令**禁跑**（禁并发、本批没碰那些面） | 未验（按要求） |
| `tools/gov-qa/**` | 任务明令**不碰**（别的自动化在写） | 未验（按要求） |
| 总纲旧读数 `10,892 条（2.087%）`（522k 库时） | 旧库快照不在，无法回溯核；只能确认"现库 13,666（2.0593%）" | 未验（不可回溯） |
| 判决理由 ② 的"≈46 分钟嵌入（E4c 实测 189 条/s）" | 引用自 E4c 实验，未在本批复跑 | 未验（引用值） |
| 判决理由 ④ 的"关掉向量问答指标不动、省 0.6 s" | 引用自 `NEXT-DEV-PLAN §四1`，未在本批复跑 | 未验（引用值） |
| `probe-tail-blindspot.v1.json` 的逐行明细 | v1 脚本未落盘（现 `.py` 是 v2）；只核了 4 组聚合读数与 README 一致（FTS head 20%/tail 20%、向量 head 26.67%/tail 6.67%） | 聚合已核；逐行未核 |
| `cos(全文, 前 512 字)` 的**精确区间** | 作者未落脚本、未记取样条款 ⇒ 区间随样本变（我 0.9779–0.9989，作者 0.9649–0.9989） | 结论"≠1"已核；区间下界不唯一 |

**关于"探针是机械挖的查询不是真实提问"**（任务点 F）：与代码一致 —— `probe-tail-blindspot.py` docstring 明写"query 是机械从原文挖的（不是真实提问）"、`pick_phrase` 从原文 `CJK_RUN` 抓串。README §四同步照抄。✅

---

## ⑤ 判据自验结果（变异 + 还原）

判据文件 `tests/test_long_clause_tail_ruler.py`（5 条）。基线 `5 passed in 0.56s`。
`measure.py` 原始：**工作区（CRLF）sha256 = `f7e9ea4a…`**、**git blob（LF）sha256 = `ce508e20…`**（与作者记录一致；本仓 §10.210 F2/§10.214 约定用 **blob 法**）。

| 变异 | 改法 | 结果 | 是否变红 |
|---|---|---|---|
| M1 | `HEAD_CHARS = 512 → 256` | **2 failed, 3 passed**（`test_head_tail_split_is_512_chars` + `test_production_still_uses_the_512_char_cap`） | ✅ 红 |
| M2 | `tail_only_words` 去掉 `| set(_tokens(title or ""))` | **1 failed, 4 passed**（`test_tail_only_excludes_head_and_title`） | ✅ 红 |
| M3 | `gain = max(0, min(...)-head) → min(...)-head` | **1 failed, 4 passed**（`test_token_drop_partition_never_negative`，`-88 != 0`） | ✅ 红 |
| **M4（复核者自加）** | `MODEL_WINDOW = 512 → 256` | **5 passed** | ❌ **未红**（⇒ P2-1 盲点） |

- M1/M2/M3 **与作者记录的失败条数逐条吻合**（2 / 1 / 1）⇒ **判据有牙，不是空判据**。
- **还原**：每次变异后从备份 `cp` 回原文件，末次还原后：
  ```
  sha256sum measure.py                 → f7e9ea4a…（工作区，与原始一致）
  git show HEAD:...measure.py|sha256sum → ce508e20…（blob，= 作者记录）
  pytest tests/test_long_clause_tail_ruler.py -q → 5 passed
  git status --short eval/.../measure.py → 空（干净）
  ```
  ⇒ **按 SHA256 还原成功、前后一致**，作者"还原后 `measure.py` sha256 = `ce508e20…`"**成立**（blob 口径）。

**`result.json` 可复现性**：作者提交版 vs 我新鲜重跑版，剔 `generated_at` 后**逐字段相同**（`author==mine: True`）——比作者自称的"连跑两次相同"**更强**（是"作者产物 vs 复核者产物"相同）。

---

## ⑥ 复核结论

- **读数**：作者声称的 **7 组关键读数全部复现通过**（规模 / 两道截断 / token 口径 / 尾巴独有词 / 影响面 / 余弦 / 探针），其中规模与 gold 长度**另用独立 SQL 交叉核对**吻合。
- **判据**：**有牙**（三处变异各被当场抓红并按 blob SHA256 还原）；但**第二道截断 `MODEL_WINDOW` 无判据**（P2-1）。
- **判决**："本轮不改 schema / 不加多向量"的四条理由**成立**；"只删 `[:512]`"这条更便宜的路**被作者实测 21.2% 后基于价值否掉，理由正确**（仅理由 ② 措辞建议澄清，P2-4）。
- **诚实边界**：与代码一致（抽样 4000/13666、探针 24 条、机械查询、影响面是上界且限定"当前考卷"）。
- **归属层**：总纲 0.10 行**保留旧话**并就地追加"🔬 已量化 + 原文状态保留"（更正留痕 ✅）；`CHANNEL-COVERAGE-PLAN R16` 明写"本文不抄正文（宪法原则 IV）"、**只登记指针**（✅）；`NEXT-DEV-PLAN`/`DEVELOPMENT-HISTORY`/`recall-funnel README §5.8` 均**带指针链接**（前者按本仓惯例内联读数，与 §10.214 同风格）。
- **总体**：**PASS**。**1 条 P1**（余弦组读数未随产物落脚本——复核者已独立复现，建议补脚本）、**4 条 P2**（MODEL_WINDOW 无判据 / gain+residual 差 2 的措辞 / result.json 哈希口径未记明 / 理由 ② 措辞）。**无 P0 阻塞**。

**产物（复核者，均在提取树外）**：
- 本报告 `D:/AI/verify-trees/VERIFY-REPORT-p010-long-tail.md`
- 复核脚本：`_p010-scale-verify.py`（独立 SQL+分词交叉核）、`_p010-cos-verify.py`（余弦独立复现）、`_p010-measure-orig.py`（变异还原备份）
- 日志：`_p010-ruler-run1.log`、`_p010-probe-run1.log`、`_p010-cos-verify.log`
- 对照快照：`_p010-author-result.json` / `_p010-mine-result.json` / `_p010-author-probe.json`
