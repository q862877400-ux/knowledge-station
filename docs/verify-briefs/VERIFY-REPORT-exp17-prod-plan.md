# 独立复核报告 · exp-17-embedding-production-plan（必验类别）

- **冻结 tag**：`verify-freeze-exp17-prod-plan`（annotated tag，deref → `5da2123`）
- **被复核 commit**：`5da21234aabcdfff631dc7625b0788797dbb1f59`（作者 Zegel，2026-10-09 17:11）
- **窗口**：`832550e..5da2123` = **1 个提交**（仅 `5da2123`；`832550e` 是 exp-16 别人的提交，不在窗口）
- **提取树**：`D:/AI/verify-trees/exp17`（`git worktree add` 于冻结 tag）
- **提取树首 HEAD**：`5da2123`，`git status --short` = **空**（干净）
- **提取树尾 HEAD**：`5da2123`，`git status --short` = ` M .../result.json`（= 我复跑 verify-resume.py 覆盖的读数文件，仅此一处；见 §B）
- **报告落盘**：本文件 `D:/AI/verify-trees/VERIFY-REPORT-exp17-prod-plan.md`

---

## 总判定

**有条件 PASS（无 P0；P1 项 = 3 处判据逃逸，其中 2 处有其它仪器兜住、1 处是测试钩子；建议补 2 条判据后转 PASS）**

- 五项验证（T1–T5）**独立复现，逐数命中**；真库 mtime/size/行数前后全同；`src/`、`plugin/` 零改动。
- T4 的"例外理由"经独立实验**站得住**（§C）。
- 唯一实质事实错误：文档反复写"`embed_query` 被**两处**调用"，实测是**三处**（§E）。结论不受影响。
- 自写 10 处变异：**7 抓 3 逃**（作者自报的是另一批 10 处，10/10 全抓，二者不矛盾）。

---

## A. 改动面与冻结

| 检查 | 读数 | 结论 |
|---|---|---|
| `git show --name-only 5da2123` 顶层目录 | 只有 `docs` / `eval` / `tests` | ✅ |
| `src/` + `plugin/` 是否零改动 | grep `^(src\|plugin)/` = **0 命中** | ✅ 零改动 |
| diffstat | 9 files changed, **+1322 / −0** | 与任务书 9 文件一致 |
| 窗口提交数 | `git rev-list --count 832550e..5da2123` = **1** | ✅ |

**关键文件哈希（走 `git show`，避开 CRLF 假红）**：

| 文件 | git-blob sha256 |
|---|---|
| `.../exp-17-embedding-production-plan/rebuild-shadow.py` | `c8dc12d6df5f70f8763241c2e97dfe7e949911c54bbc7ec9c5f1743920a26e8d` ✅ 与作者自报**一致** |
| `.../verify-resume.py` | `238c6d68ede7815e3463d63921506b80b198ffb7068668d9df5d56f844636bc1` |
| `.../result.json` | `29f45076bb9b4b1fb5382255de48a0141f5af566a8cd616af4f85c591cfbaaf2` |
| `.../README.md` | `61ff8e1e87446884e14838e40a1b8365394cadacd8519c387080644e49031b98` |
| `tests/test_embedding_rebuild_resume.py` | `f5931e71b42aa107d5b4885ad27a3d0879b4b52177f36e4f363d6d999f921bec` |

> ⚠ 工作区文件（CRLF）sha256 = `6167ec51e708e97de2f34cbfd4faa1dd9dcf5da093e97e5079c99af504080ca4`，与 git blob 不同（`core.autocrlf=true`）——作者报的 `c8dc12d6…` 是 **git blob**，核到一致；裸 `sha256sum` 对工作区文件会假红，已按纪律走 `git show`。

---

## B. 五项验证读数独立复跑

### B.1 复跑作者脚本（提取树内 `verify-resume.py`）
第二次运行 **5 项全 PASS**，`result.json` 与作者提交版**逐字段相同**：

| # | 项 | 我的复跑读数 | 作者自报 | 一致 |
|---|---|---|---|---|
| T1 | 一次跑完 vs 中断续跑 | 300/300，`n_diff=0`，digest `d1c1c06b…` | 同 | ✅ |
| T2 | 真强杀后续跑 | `killed_at=**2080**`，续到 20,000，`n_diff=0` | 2,080 | ✅ **逐数相同** |
| T3 | 幂等 | `rows_written=0`，digest 不变 | 同 | ✅ |
| T4 | 真模型 vs E4 冻结向量 | A **64/64**（cos_min=1.0、maxdiff=0）；B 16/64（maxdiff=8.392e-4） | 同 | ✅ |
| T5 | 真库未动 | mtime/size/663,634/663,634 前后全同 | 同 | ✅ |

> ⚠ **一处环境鲁棒性备注**：**第一次**跑 `verify-resume.py` 在 T2 的续跑处抛 `sqlite3.OperationalError: disk I/O error`（在 `_source_counts` 打开真库只读连接时）。**原样重跑即通过**。属真库（活库、WAL）在只读打开时的瞬时争用，不是脚本逻辑缺陷；但说明该验证脚本**不是一次必过**，复核/复跑要预留重试。

### B.2 我自写的独立复算（不调作者函数，自己按 (id, embedding bytes) 逐行比）
脚本 `D:/AI/verify-trees/_exp17-artifacts/indep_recompute.py`，读数 `indep-recompute.json`：

| 项 | 我自写的读数 | 判定 |
|---|---|---|
| T1 | `n1=n2=300`，`partial_after_stop=80`，`resume_wrote=220`，**`n_diff=0`**，digest1=digest2=`d1c1c06b…` | ✅ 独立复现 |
| T3 | `rows_written=0`，digest 前后相同 | ✅ |
| T2 | `killed_at=2000`（我轮询阈值 2000 触发），续写 18000，**`n_diff=0`**，`n1=n2=20000` | ✅ 独立复现 |

> **T2 是否真杀到**：是。作者版 `killed_at=2080`（>0），我版 `killed_at=2000`（>0），两次都在**子进程运行中 `terminate()`**，落盘行数 < 目标 ⇒ 本项**已真验证**（非 -1/0）。

---

## C. ★ T4 的仪器对照站不站得住（本轮最需独立判断的一条）

**结论：这条例外理由站得住。** 依据（全部为我独立实验，脚本 `C_t4_instrument.py` / `C2b_batch_invariance.py`）：

| 实验 | 我的读数 | 与作者对照 |
|---|---|---|
| exp.db 事实 | `clause_vec_qwen=521,978` = 非空正文 `521,978`；`clause_revision=522,021` | E4 冻结语料 ✅ |
| A：**复刻 E4 分批**（非空 + `ORDER BY rowid`，每批 16） | **64/64 逐字节相同**，`cos_min≈1.0`（0.9999999999999998），`maxdiff=0.0` | ✅ 命中 |
| B：**换分批**（一次喂 64） | **16/64** 相同，`maxdiff=8.392333984375e-4` | ✅ 逐数命中作者 8.4e-4 |
| 根因：fp16 批不变性 | fp16 `b16 vs b64` = **16/64**、maxdiff **8.392e-4**；fp32 `b16 vs b64` = 0/64、maxdiff **1.12e-6** | ✅ 根因 = **fp16 缺批不变性**（半精度累加顺序），不是口径错 |
| 语料一致性 | exp.db 前 64 非空（id, title, text）**== 真库当前前 64**（`first64_ids_same=True`、`first64_text_same=True`） | ✅ |
| 序列化 | sqlite-vec 把 `json.dumps(list)` 与 `array('f').tobytes()` 存成**逐字节相同的 2048 B** | ✅ 命中作者第 3 条新知识 |

**我的判断（独立给出）**：
1. 本仓"仪器对照的参照物必须是**同期重跑**"这条纪律，防的是**名次读数**被历史产物污染。T4 **不是**名次读数，它比的是**嵌入函数的字节级输出**；而参照物（E4 冻结向量）恰好就是"被测对象"——若当前嵌入函数与 E4 有任何口径差异，T4 就该红。**这正是它要红的场合**，故例外成立。
2. **作者的对照设计是干净的**：他把"分批"这个唯一会引入 1e-4 差异的变量**复刻**了（E4 的 batch=16 / 非空 / `ORDER BY rowid`），并用 B 臂证明"换分批只 16/64" ⇒ 排除了"口径错"的误判。我读 `exp-4/01-embed-qwen.py` 核对：其 `BATCH=16`、`WHERE trim(coalesce(content_text,''))<>'' ORDER BY rowid`、`display_text`、`padding_side="left"`、`dtype=float16`、`[:, -1]` 末 token 池化、`[:, :512]` 截断后 L2 —— 与 `rebuild-shadow.py` 的 `real_embedder_factory` **逐字一致** ⇒ A 臂 64/64 不是巧合。
3. **"库长大了会不会拿错输入比"——不会**：T4 的**输入文本与参照向量都取自 exp.db 自身**（自洽）；且 exp.db 前 64 非空与真库当前前 64 **逐字段相同**。exp.db 冻结于 2026-10-07（521,978 条），真库现 663,591 条非空，但 T4 只取前 64，落在两者共有区间内。
4. **一条边界（不否定结论）**：T4 证明的是 `rebuild-shadow.py` 的嵌入函数 == `exp-4/01-embed-qwen.py` 的口径，**并不重新证明 E4 本身正确**（那是 E4 那一轮的事）。作为"新脚本 vs 已复核过的冻结产物"的交叉核对，这已经足够。

---

## D. 判据有牙（**我自写的 10 处变异**，非重复作者）

打在 `tests/test_embedding_rebuild_resume.py`（基线 **17 passed**）。逐字节还原，跑完 `rebuild-shadow.py` sha256 与改前**一致**（`6167ec51…`）。脚本 `D_mutations_one.py`。

| # | 我改了什么 | pytest 结果 | 被抓? |
|---|---|---|---|
| M1 | `ckpt_guard` 比较方向 `!=` → `==`（反转） | 3 failed（`ckpt_guard_allows_matching`、`resume…`、`rerun…`） | ✅ |
| M2 | checkpoint 的 `"done"` 写 `target` 而非 `done` | 2 failed（`resume…`、`checkpoint_never_drifts…`） | ✅ |
| **M3** | `--stop-after-batches` 边界 `>=` → `>`（差一批） | **17 passed** | ⛔ **逃逸** |
| **M4** | 取数 `LIMIT max(0,target-done)` → `LIMIT target` | **17 passed** | ⛔ **逃逸** |
| M5 | `display_text` 把 **title 也** `[:512]` | 1 failed（`display_text_matches_production_formula`） | ✅ |
| M6 | `fake_vector` 去掉 L2 归一化 | 1 failed（`fake_vector_is_deterministic_and_normalized`） | ✅ |
| **M7** | `real_embedder_factory` 池化取**首** token（`[:, -1]`→`[:, 0]`） | **17 passed** | ⛔ **逃逸** |
| M8 | 取数 `rowid > ?` → `rowid >= ?` | 1 failed（`resume_is_row_identical_to_one_shot`） | ✅ |
| M9 | `last_rowid` 写**批首**而非批尾 | 1 failed（`resume_is_row_identical_to_one_shot`） | ✅ |
| M10 | 取数**不过滤空正文** | 1 failed（`resume_is_row_identical_to_one_shot`） | ✅ |

> 说明：M10 正是作者 §九 说的"首轮逃逸已补牙"的那条 —— 我复现它**已被抓住**（判据比的是**集合本身**，报错 "影子表里混进了正文为空的条款"）。M5/M6 也证明 511/512/513 边界与归一化判据有牙。

**3 处逃逸的定级（我的判断）**：

| 逃逸 | 我的定级 | 理由 |
|---|---|---|
| **M4**（生产代码路径 `run()`） | **P1（按"逃逸=P1"的严格口径）**；实害被兜住 | `--limit < 非空总数` 且**续跑**时，`LIMIT target` 会多取行 ⇒ 影子表超出 target。**但** `verify-resume.py` 的 T1/T2 正是 `limit=300/20000` + 续跑，我实测这两项在 M4 下会红 ⇒ **该盲区被 T1/T2 兜住**。建议把"limit<非空 + 续跑"补进 pytest。 |
| **M7**（真嵌入口径） | **P1（同上口径）**；实害被兜住 | 17 条判据**不加载模型**（文件头已声明），故不覆盖池化/截断/归一化。**但** `verify-resume.py` 的 T4 会红（我实测 A 臂 64/64 依赖正确池化）⇒ 由 T4 兜住。建议加一条"真模型口径"的 pytest（或把 T4 设为门禁项）。 |
| **M3**（`--stop-after-batches` 边界） | **P2** | 该参数是**测试钩子**，不进生产；所有仪器都测不到它，且它错了也不影响生产正确性。 |

⇒ **无 P0**；**P1 = 2 条**（M4、M7），均"判据集有洞但另有仪器兜住"，建议补判据后消项。

---

## E. 文本公式与生产逐字一致

**条文文本公式**（自己 grep `src/core/storage/clause_repo.py`）：

- `clause_repo.py:285`（`insert_clauses_in_txn`，`embed_batch`）：`f"{c.title or ''}\n{c.content_text[:512]}"`
- `clause_repo.py:426`（`_reindex_clause_indexes`，`embed_query`）：`f"{title or ''}\n{content_text[:512]}"`
- `rebuild-shadow.py` `display_text`：`f"{title or ''}\n{(body or '')[:512]}"`

⇒ 两处生产点**彼此一致**；重建版**多一层 `(body or '')`**（生产遇 `content_text=None` 会抛，重建不会）。在取数已过滤 `trim(coalesce(content_text,''))<>''` 的域内**逐字等价**。✅（`\n`、`[:512]`、`title or ''` 全对）

**★ `embed_query` 调用点核实（作者称"两处"，实测三处）**：

| 调用点 | 侧 | 是否在**生产检索路径** |
|---|---|---|
| `src/core/retrieval/hybrid_engine.py:310` | 查询侧 | ✅ 是 |
| `src/core/storage/clause_repo.py:426` | **条文侧**（补丁重算） | ✅ 是 |
| **`src/core/retrieval/term_bridge.py:160`** | 查询侧（术语桥 `TermIndex.select`） | ❌ 否（仅 `scripts/measure-term-bridge.py` 调 `bridge_search`） |

- 作者的**核心结论成立**：把指令前缀加进 `embed_query` 内部，会让 `clause_repo.py:426` 的**条文向量**吃进查询指令 ⇒ 两套文本口径混进一张表。**这一点我读码确认，是本轮最有价值的一条。**
- 但"**两处**"是**事实性错误**（三处），且 §一 触点表**未登记 `term_bridge.py:160`**。当前它不在生产检索路径上，所以**暂不构成实害**；但若将来 term_bridge 接入生产，按现方案会**静默漏加前缀**。⇒ **P2**。

---

## F. §一「触点清单」是否完整

自己全仓 grep `clause_vec`（`src/` `scripts/` `tests/` `plugin/`）：

**`src/` 全部触点 = 6 个，README §一 表**（第 1/3/4/5/6/7 行）**一个不漏**：

| 位置 | 动作 | README 行 |
|---|---|---|
| `hybrid_engine.py:312` | 读（KNN SELECT） | 行 1 ✅ |
| `clause_repo.py:332` | 写（入库） | 行 3 ✅ |
| `clause_repo.py:428` | 写（补丁重算） | 行 4 ✅ |
| `clause_repo.py:367` | 删 | 行 5 ✅ |
| `doc_delete.py:79` | 删 | 行 6 ✅ |
| `server.py:2501` | 计数 | 行 7 ✅ |

⇒ **写入/删除点全数登记，无遗漏**（漏写入点会 P1，这里**没有**）。

**次要缺口（P2，均非写点）**：
- `scripts/verify-dup-vectors.py`、`scripts/verify-dup-safety.py` **读** `clause_vec`，未登记（只读诊断脚本；方案 A 保留 `clause_vec`，故不失效）。
- `tests/test_contract.py:68`（`clause_vec` 出现在"必须存在的表名"冻结集里）、`test_doc_batch_delete.py:107`（表名元组）未登记 —— 均为**表名存在性检查**，非 INSERT/DELETE/COUNT；方案 A 保留旧表 ⇒ 仍通过。
- 行号全部核对**准确**（310/312/332/367/428/79/2501/55/67/76 逐个命中）。

---

## G. 成本账算术逐项复算

| 待核 | 我复算 | 判定 |
|---|---|---|
| 1.38 → 32.02 增量 | 32.02−1.38 = **30.64 ms** ≈ "+30.6 ms/问" | ✅ |
| "小 20–35 倍"（分母 606.0 / 1074.7） | 606.0/30.64 = **19.78≈20**；1074.7/30.64 = **35.07≈35** | ✅ |
| 663,591 × 2,048 B | = 1,359,034,368 B = **1.2658 GiB ≈ 1.27 GiB** = **1.359 GB ≈ 1.36 GB** | ✅ |
| 663,591 ÷ 164.4 | = **67.27 分钟 ≈ 67.3** | ✅ |
| 663,591 ÷ 189 | = **58.52 分钟 ≈ 58.5** | ✅ |
| `164.4` 能否自复现（跑 `--limit 2000`） | 我实跑 **2000 条 / 12.542 s = 159.5 条/s**（作者 164.4） | ✅ **~3% 内复现** |

**数字出处核对**（`exp-4b-embedding-round2/`）：`1.38`（`verdict.json:6`/`latency.json`）、`32.02`（`verdict.json:7`）、`5154.3`（`verdict.json:9`）、`1164.0`（`verdict.json:10`）、`1074.7`（`verdict.json:18`/`latency-real-db-scan.json`）、`2.98`（`verdict.json:19`）、`606.0`（`verdict.json:23`/`NEXT-DEV-PLAN §四`）—— **全部真实存在**，非杜撰。✅

**⚠ 特别查：有没有把"向量路内部占比"说成"端到端延迟占比"？——没有。** exp-17 README §三 第 3 点**明确写着**："这只是**向量路内部**的占比，**不是端到端延迟占比**（本仓没有端到端读数，不声称）"。✅ 这一条**做对了**（exp-4b README 也用"提问侧嵌入**占向量路**的 2.98%"的措辞）。

---

## H. 超证据 / 全称句自查

grep 本提交 5 个文档的全称词（永远/完全/所有/唯一/一定/全部/从来没…）：

| 断言 | 位置 | 判断 |
|---|---|---|
| `Vector@1000` 的 **+48.34pt** | README §二 L60、§10.226 | **已标"外推"**（"但那是**外推**，且终点是 `Vector@1000`"）✅ |
| 全量重建**约 1 小时** | README §4.3 / §八 / NEXT-DEV-PLAN / §10.226 | **已标"外推（不是实测）"** ✅ |
| +48.34pt 会不会被说成"用户会涨这么多" | README §七 | **没有** —— §七 明写"很可能在 `fused@20` 上**大幅缩水，甚至可能不动**"、"拿到 `fused@20` 之前**没有依据**" ✅ |
| "**唯一**已量出大收益的方向" | README §零 L11 | 强断言；与本仓既有记录（E4 三刀 + exp-6/7/8/9/13/14/15/16 的收益量级）一致，但未在本轮直接举证 ⇒ **P2 软提示** |
| "P1/P2 到目前为止**所有**提升都靠向量路" | README §三 L79 | 全称；括注限定在 `exp-13/14/15`，未穷举全部实验 ⇒ **P2 软提示** |
| "证据，**全部**已独立复核" | README §二 L49 | §二 表的数（E4 三轮 + exp-13）确有各自复核报告 ⇒ 基本成立，措辞偏满 ⇒ P2 |
| "**唯一**读点" | README §一 L23 | 限 `src/` 内成立 ✅ |
| "**两处**调用" | 4 个文档 | **事实错误**（三处），见 §E ⇒ **P2** |

⇒ **无超证据的硬伤**（+48.34pt 与 1 小时都标了外推；没有被说成"用户会涨这么多"）。

---

## I. 是否真的没碰生产

| 量 | 复核前 | 复核后 | 结论 |
|---|---|---|---|
| 真库 `mtime` | `1791534656.5820563` | `1791534656.5820563` | **未变** ✅ |
| 真库 `size` | `3105525760` | `3105525760` | **未变** ✅ |
| `clause_vec` 行数 | 663,634 | 663,634 | **未变** ✅ |
| `clause_revision` 行数 | 663,634 | 663,634 | **未变** ✅ |
| 非空正文行数 | 663,591 | 663,591 | **未变** ✅ |
| 真库有没有 `clause_vec_qwen` | — | **无此表** | ✅ 影子表没写进真库 |
| 真库 `-shm` | — | mtime 变 `17:26`（只读 WAL 打开触碰） | 非数据写入（既有报告同现象） |

- 提取树 `git status --short`：**首=空、尾=仅 `result.json`**（我的复跑覆盖，非作者提交改动）✅。
- 我的全部脚本/产物都落在 `D:/AI/verify-trees/_exp17-artifacts/`（提取树之外）；变异只在提取树做并**逐字节还原**（`6167ec51…` 一致）✅。

---

## 明确「未验证」清单

1. **全量重建未跑**（663,591 条，约 1 小时）：与作者一致，只跑小样。1 小时是**外推**。
2. **`fused@20` 未测**：本轮完全没碰；"该不该切"仍无依据（作者已自认）。
3. **切换/回滚未演练**、**冷启动预热未验证**、**双写写入开销未量**：与作者诚实边界一致，我亦未做。
4. **真库内容哈希未做**：3.1 GB、无基线，只量了 mtime/size/行数（抽样口径）。
5. **T4 只抽前 64 条**：**这是抽样，不是全部 521,978 条**；A 臂 64/64 是全样本内的逐字节相等，但未覆盖全量。
6. **我未逐条核 exp-4b 的原始 latency 采集脚本**，只核了数字确在 JSON/README 里。

---

## 非阻塞发现（P2）汇总

1. **"`embed_query` 被两处调用"是事实错误**：实测**三处**（`hybrid_engine.py:310` / `clause_repo.py:426` / **`term_bridge.py:160`**）。核心结论（前缀不能加进 `embed_query` 内部）**成立**，但触点表漏登记 `term_bridge.py:160`（查询侧、当前不在生产检索路径）。**4 个文档都写了这句，需一并更正。**
2. **17 条 pytest 判据不覆盖"`limit < 非空总数` + 续跑"**（M4 逃逸；由 `verify-resume.py` T1/T2 兜住）。
3. **17 条 pytest 判据不覆盖真嵌入口径**（M7 逃逸；文件头已声明不加载模型；由 `verify-resume.py` T4 兜住）。
4. **`--stop-after-batches` 边界语义未钉住**（M3 逃逸；test-only 钩子，无生产影响）。
5. **触点清单漏 `scripts/verify-dup-vectors.py` / `verify-dup-safety.py`**（只读诊断）。
6. **`display_text` 用 `(body or '')`** 而生产用 `content_text[:512]`（域内等价；生产遇 `None` 会抛、重建不会）——建议在文档里点一句"域内等价"。
7. **`verify-resume.py` 首次运行遇真库瞬时 `disk I/O error`**（重跑即过）——复跑需预留重试。

## 必改项（P1）

1. **M4**：`run()` 的取数 `LIMIT max(0, target - done)` 在 `--limit < 非空总数` 且续跑时是**正确性关键**，17 条判据抓不住 ⇒ 补一条 pytest（小库 + `limit=某值<非空` + 续跑，断言 `shadow_rows == target` 且逐行一致）。
2. **M7**：真嵌入的池化/截断/归一化口径仅由 `verify-resume.py` T4 覆盖 ⇒ 建议把 T4 设为门禁项，或加一条轻量 pytest 断言 `real_embedder_factory` 源码里的 `[:, -1]`/`[:, :out_dim]`/`F.normalize` 静态锚点（比照 `test_production_source_still_has_the_same_formula` 的做法）。

> 两条均为"判据集有洞但另有仪器兜住"，**不否定本批读数**；补齐后本批可转**无条件 PASS**。

---

## 附：我的变异与实验产物（保留在 `D:/AI/verify-trees/`）

- `_exp17-artifacts/indep_recompute.py` + `indep-recompute.json`（B 独立复算）
- `_exp17-artifacts/C_t4_instrument.py` + `C-t4-instrument.json`、`C2b_batch_invariance.py` + `C2-batchinvariance.json`（C 仪器对照）
- `_exp17-artifacts/D_mutations_one.py` + `_mutout_*.txt`、`D-mutations.json`（D 变异）
- `_exp17-artifacts/verify-resume-rerun2.log`（B 复跑日志）
- `_exp17-artifacts/rebuild-shadow.pristine.py`（还原基准）
