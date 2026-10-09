# 独立复核报告 · E4c「同模型升维 512→1024」

- **复核者标识**：`general-purpose-1`（独立 verifier，非作者）
- **复核时间**：2026-10-09 11:09–11:16 (+0800)
- **被复核冻结 tag**：`verify-freeze-e4c-1024`（附注标签）
- **tag 解析出的提交**：`4b9e3e5aff2d0c42e0fccccd89bdab0ef2b951e1`
  - `git rev-list --count 4b9e3e5^..verify-freeze-e4c-1024` = **1**（区间仅此一提交，自核一致）
- **提取树路径**：`D:/AI/verify-trees/e4c`（`git worktree add ... verify-freeze-e4c-1024`）
- **被复核目录**：`eval/recall-funnel/exp-4c-embedding-1024/`
- **解释器**：主仓 `.venv`（`D:/AI/work space/zcode/.venv/Scripts/python.exe`），本机 GPU RTX 4080 SUPER

## 首尾状态（冻结提取树）

| | `git rev-parse HEAD` | `git status --short` |
|---|---|---|
| **首（建立后）** | `4b9e3e5aff2d0c42e0fccccd89bdab0ef2b951e1` | （空，干净） |
| **尾（全部复核完）** | `4b9e3e5aff2d0c42e0fccccd89bdab0ef2b951e1` | （空，干净） |

> 提取树里**没有** `exp.db`（5.7 GB，被 `.gitignore` 忽略）——已确认。本轮**未拷贝** `exp.db`；
> 仪器对照的 DB 读数一律用 **主仓 `exp.db` 只读**（`sqlite3.connect('file:...?mode=ro', uri=True)` + `load_vec_extension`）取得，
> 复跑 22/23 不需要 `exp.db`（只读 per-query/benchmark/result/cluster-ci/stop-loss），故无需符号链接即可复跑。
> 全程**未写** `exp.db` 之外的任何文件；真库只读。

---

## 逐条复核

### 1. 冻结提取树
- **复核项**：worktree 建立、首尾 HEAD/status、提取树内无 exp.db。
- **复核读数**：见上表。`D:/AI/verify-trees/e4c` 由 `verify-freeze-e4c-1024` 建立，detached HEAD = `4b9e3e5`；首尾 HEAD 相同、status 均空。`eval/recall-funnel/exp-4-embedding-shadow/` 内**无 `exp.db`**（仅脚本与 json）。
- **与作者自报是否一致**：一致（作者称提取树无 exp.db、需只读引用）。

### 2. 冻结哈希
- **复核项**：`stop-loss.json` sha256 = `2e4139b7…`；其 mtime 早于任何结果文件。
- **复核读数**：
  - 主仓工作文件 sha256 = `2e4139b7a002e7e404cde71b6714081d4f5df9d8c7adce14bbe5c13d54b45b15` ✅ 与 `stop-loss-freeze.txt` **逐字符相同**。
  - `git show 4b9e3e5:…/stop-loss.json | sha256sum` 亦 = `2e4139b7…`（= git blob，见发现 F2）。
  - mtime：`stop-loss.json` = **2026-10-09 09:54:45.08**，早于全部结果文件（`ab-1024-result.json` 11:04:04、`ab-1024-cluster-ci.json` 11:04:36、`verdict.json` 11:04:35）✅。
- **与作者自报是否一致**：一致。

### 3. 复跑判定链
- **复核项**：跑 `22-cluster-ci.py`、`23-verdict.py`，与冻结版逐字节比对；22 连跑两次逐字节相同（声称 `cd5fac79…`）。
- **复核读数**（CWD = 提取树，用主仓 `.venv` python）：
  - `22` 第 1 次 → `ab-1024-cluster-ci.json` sha256 = `cd5fac792feeff626e765dfd2c89659a2dfa5d2c086010e495168c5508ca0120`。
  - `22` 第 2 次 → 同 sha256；`diff` 与备份（冻结版）→ **IDENTICAL**。
  - `23` → `verdict.json` sha256 = `5410412f3e591bad424b28763ed89842eea447aaaef36ca331af2e47630c9805`，exit 0；`diff` 冻结版 → **IDENTICAL**。
  - 另：主仓 ↔ 提取树对 4 个结果文件原样 sha256 **完全相同**（见下表）。
- **与作者自报是否一致**：一致（含 `cd5fac79…` 逐字节复现）。

| 文件 | 主仓 sha256 | 提取树 sha256 | 冻结比对 |
|---|---|---|---|
| `ab-1024-cluster-ci.json` | `cd5fac79…0120` | `cd5fac79…0120` | IDENTICAL |
| `ab-1024-per-query.jsonl` | `76c02c9f…d2ff` | `76c02c9f…d2ff` | — |
| `ab-1024-result.json` | `bce61caf…3946` | `bce61caf…3946` | — |
| `verdict.json` | `5410412f…9805` | `5410412f…9805` | IDENTICAL |

### 4. 判据有牙（变异测试，**仅在提取树内**）
- **复核项**：单侧变异后 `decision` 是否真会改变；变异后按 SHA256 还原、`git status` 干净。
- **复核读数**（decision 原文）：

| 变异 | 动作 | 产生的 decision | 是否改变 |
|---|---|---|---|
| 原状 | — | `放弃升维（低于半条分辨率线）` | 基线 |
| **M1** | 只把 `headline_120.d512.rank@1000` 改 0.3（单侧拉低对照臂） | `放弃升维（低于半条分辨率线）` | **不变**（见 F1） |
| **M2** | 把 `delta_pp.rank@1000` 改 31.67 | `达到分辨率线但簇级 CI 下界 <= 0 ⇒ 不能据此推进` | **改变** ✅ |
| **M3** | `delta_pp=31.67` + `cluster-ci.headline.ci95_pp=[5,20]` | `升维有可分辨收益 ⇒ 进生产评估` | **改变**（到另一极）✅ |
| **M4** | 把 `delta_pp.rank@1000` 改 5.0 | `灰区：有正向迹象但低于分辨率线 ⇒ 记录，不推进` | **改变** ✅ |
| **M5** | 只互换两臂原始 `rank@1000` 读数（不动 delta_pp） | `放弃升维（低于半条分辨率线）` | **不变**（见 F1） |

  ⇒ 四条决策分支全部可被触发，判据**不是恒判"放弃"**，有牙。
- **还原**：4 个产物从备份按 SHA256 还原，末态 sha256 = 冻结值（`cd5fac79…` / `76c02c9f…` / `bce61caf…` / `5410412f…`），`git status --short` **空**、HEAD 未变 ✅。
- **与作者自报是否一致**：作者未声称做过变异测试；本次为独立新增证据，结论支持"判据机械、有牙"。

### 5. 仪器对照与真库只读核对
- **复核项 A（结果 JSON 字段）**：`ab-1024-result.json.instrument_control` →
  `round1_selfcheck_mismatch_items=0` ✅、`fts_mismatch_items=0` ✅、`vec_set_bidirectional_except={only_512:0, only_1024:0}` ✅。
- **复核项 B（独立 sqlite 只读，load_vec_extension=True）**：
  - `clause_vec_qwen` 行数 = **521,978** ✅；`clause_vec_qwen1024` 行数 = **521,978** ✅。
  - 独立双向 EXCEPT（**集合法**，非脚本 SQL）：`only_512=0`、`only_1024=0`、`s512==s1024=True` ✅。
- **复核项 C（独立逐条核仪器对照 1/2）**：用 `ab-1024-per-query.jsonl` 对 `exp-4-embedding-shadow/ab-per-query.jsonl` 的 `ctx` 臂逐条比：
  - `d512.rank@1000` vs round1 `ctx.rank@1000` 不一致条目 = **0**；连 `rank@20/@100` 也 = **0**。
  - `fts@1000` 两臂差异条目 = **0** ✅。
- **复核项 D（真库）**：`%APPDATA%\KnowledgeStation\database\knowledge.db` 只读打开，`clause_vec` 行数 = **663,634** ✅；主文件 mtime = **2026-10-08 18:55:44**（早于本轮 2026-10-09 全流程）⇒ 本轮**未触碰真库** ✅。
- **与作者自报是否一致**：全部一致。

### 6. 作者的一处自我更正
- **复核项**：核 `22-cluster-ci.py` 的 p 是否已截断、`exp-4b/13-cluster-ci.py` 是否确实无截断且本轮零改动。
- **复核读数**：
  - `22-cluster-ci.py:63` = `round(min(1.0, 2 * min(le0, ge0)), 4)` —— **已截断** ✅（并在 60–62 行注释登记该缺陷与"不改已冻结的 13"）。
  - `exp-4b-embedding-round2/13-cluster-ci.py:64` = `round(2 * min(le0, ge0), 4)` —— **无截断** ✅。
  - 本轮零改动：`git diff --stat 4b9e3e5^..4b9e3e5 -- eval/recall-funnel/exp-4b-embedding-round2` = **空**；该文件最后一次改动在提交 `07c6a50`（E4 第二轮），非本轮 ✅。
  - **独立复算**（重放同一 seed=20261009 / 10000 次配对簇级 bootstrap）：
    - `all_171` 未截断 `2*min(le0,ge0)` = **1.079** → 截断后 1.0（与冻结 `ab-1024-cluster-ci.json` 的 `all_171.p_two_sided=1.0` 吻合）。
    - `headline_120` 未截断 = 0.7284 → 截断后仍 0.7284（与冻结值吻合）。
- **与作者自报是否一致**：**完全一致**——"首跑得 1.079"（来自 all_171 档）、"已改成 min(1.0,…)"、"13 同公式无截断且本轮未改"三句全部属实。

### 7. 诚实边界核对
- **复核项**：报告里的边界说法是否与代码一致。
- **复核读数**：
  - "语料 521,978 不是真库 663,634"：`21-ab-1024.py` 的 `cost_knn_scan_ms.corpus_rows = n512`（= `COUNT(clause_vec_qwen)` = 521,978）；真库独立读数 663,634 ⇒ 说法与脚本/DB 一致 ✅。
  - "未换模型"：`20`/`21` 均 `MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"`，两臂同模型 ✅。
  - "未加前缀"：`21.qvec(text)` 仅 `tok([text], …)`，**无任何指令前缀拼接**；`stop-loss.json` 亦将"两臂都不加前缀"列入 frozen_inventory ✅。
  - "未接生产链"：脚本只读真库（`mode=ro`）、只写 `exp.db` 副本的 `clause_vec_qwen1024`；无生产 embedding 代码改动、无 ANN/微调/RRF 调整 ✅。
- **与作者自报是否一致**：一致。

### 8. 改动面核对
- **复核项**：`git diff --stat 4b9e3e5^..4b9e3e5`，确认 `src/`、`plugin/`、`tests/` 零改动。
- **复核读数**：
  - 提交区间 = **19 文件 / +1401 −4**，全部落在 `eval/`（`exp-4c-embedding-1024/*`、`exp-4-embedding-shadow/README.md` 1 行状态更新）与 `docs/`（4 个 md）✅。
  - `git diff --stat 4b9e3e5^..4b9e3e5 -- src plugin tests` = **空** ✅。
  - `git diff --stat 4b9e3e5^..4b9e3e5 -- eval/recall-funnel/exp-4b-embedding-round2` = **空** ✅。
- **与作者自报是否一致**：一致。

---

## 结论

**放行（PASS）。**

8 项复核全部通过：冻结哈希与 mtime、判定链逐字节复现（22 两次相同 + 23 与冻结版 IDENTICAL）、判据有牙（四档均可触发）、仪器对照独立复现（行数 521,978×2、双向 EXCEPT=0、d512 复现 round1 ctx、FTS 两臂相同）、真库未触碰（663,634 / mtime 早于本轮）、自我更正属实（未截断 p=1.079 复算吻合）、诚实边界与代码一致、改动面仅 eval/ 与 docs/。作者自报的主结论（放弃升维，+1.67pt 不显著、代价 ×1.647）在只读复算下成立。

## 非阻塞发现（不影响放行）

1. **F1 · `23-verdict.py` 的 decision 依赖"预存 delta"而非重算。** `23` 直接读 `ab-1024-result.json.summary.headline_120.delta_pp.rank@1000` 来分档，**不从两臂原始 `d512/d1024` 读数重算**。因此 M1/M5 这类"只改两臂原始读数、不动 delta_pp"的变异**不会改变** decision（实测不变）。含义：阈值"防漂移"设计（从 stop-loss 抽边界）有效，但结果 JSON 内部"臂读数 ↔ delta_pp"若不一致，verdict 不会察觉。建议（非阻塞）：`23` 增加一条 `assert abs((d1024-d512)*100 - delta_pp) < 1e-6` 的自洽校验。
2. **F2 · 冻结哈希对行尾（EOL）敏感，且两处约定不一致。** `stop-loss.json` 记录的 `2e4139b7…` 是 **LF** 字节流的哈希（= git blob = 主仓工作文件）；在 Windows `core.autocrlf=true` 下，fresh checkout（如提取树）得到 **CRLF**，sha256 = `6968c2ac…`，`tr -d '\r'` 后回到 `2e4139b7…`（内容一致）。而结果文件的冻结哈希（如 `cd5fac79…`）是 **CRLF** 版本。复核/复现时需注意：**stop-loss 用 LF（或 `git show` blob），结果文件用 CRLF（或统一去 CR 归一化）**。建议（非阻塞）：冻结流程统一按 `git show <tag>:<path> | sha256sum`（blob/LF）记录，或在 `.gitattributes` 里对这些 json 固定 `-text`。
3. **F3 · `NOT EXISTS` 双向 EXCEPT 在 vec0 虚表上极慢（操作观察，非缺陷）。** 我用与 `21-ab-1024.py` 相同的 `NOT EXISTS` SQL 在只读连接上复现时 >45s 未完成（疑似退化为 O(n²)），改用**集合法**（取两侧 `clause_revision_id` 集合做对称差）1.1s 得 `only_512=only_1024=0`。结论一致；仅提示：该 SQL 模式在大表上不宜反复使用。
4. **F4 · 真库 `clause_vec` 行数 663,634 与 README/stop-loss 中"真库 663,634"一致**，但 README §七 表格写"真库未动（全程 mode=ro）"——本次独立核到的**唯一**证据是行数不变 + mtime（2026-10-08 18:55）早于本轮；未做真库内容哈希（3.1 GB，且无基线哈希可比）。属证据强度说明，非缺陷。

## 附件（本次复核产生的旁证，均在仓库之外）

- 冻结产物备份：`D:/AI/verify-trees/_e4c-frozen/`
- 复跑日志：`_e4c-run22-1.log`、`_e4c-run22-2.log`、`_e4c-run23.log`
- 变异日志：`_e4c-mut-M1.log`、`_e4c-mut-M2.log`、`_e4c-mut-M3.log`
- DB 核对脚本/日志：`_e4c-dbcheck.py`、`_e4c-realdbcheck.py`、`_e4c-realdbcheck.log`、`_e4c-except.log`
- 提取树：`D:/AI/verify-trees/e4c`（复核末态 `git status` 干净，HEAD = `4b9e3e5`）

> 本报告未修改被复核目录内的任何文件；所有变异已按 SHA256 还原。
