# 召回漏斗诊断（recall-funnel）—— 阶段 0「只读体检」的产物

> **这是什么**：一次**只读**的现状体检，回答一个问题 ——
> **用户用大白话提问时，正确的条文到底有没有被第一跳召回？如果没有，是在哪一条通道、哪个截断位置丢的？**
>
> **这不是什么**：**不是**算法改造，**不是**长周期开发。本目录里没有一行改动生产检索行为的东西。
> 下一阶段（改什么、按什么顺序改）要等这次结果出来后再定。

---

## 一、产物

| 文件 | 是什么 | 谁看 |
|---|---|---|
| **`REPORT.md`** | **结论报告**：A 考卷 / B 六路 recall 表 / C 并集与融合漏斗 / D 独家贡献 / E 失败样本 / F 配置 | 业主 + 外部评估 |
| **`给外部评估的说明.md`** | **自包含**地讲清"这系统是什么、现在怎么找、这次量了什么、数字有什么缺陷、要请对方判什么"（对方不需要访问代码或库） | 直接发给外部 AI |
| `benchmark-v2.jsonl` | 清洗后的考卷（171 条，每条带 `v2.bucket` / `v2.flags` / **`v2.subset`**（难度子集）/ **`v2.answer_out_of_corpus`**） | 复核 |
| `benchmark-v2-stats.json` | 考卷统计（唯一条款数 / 票型 / 标记数 / **子集分布** / 移出样本与原因） | 复核 |
| `funnel-per-query.jsonl` | **逐条**漏斗原始记录（每条：六路各自的 gold 名次 + 并集 + 融合 + 一致性校验） | 复核、复算 |
| `funnel-summary.json` | 上面那份折出来的表（含全量 / 主结果 / 按类型 / **按难度子集**四套） | 报告的数据源 |
| `failure-samples.jsonl` | **同预算并集 @1000 未命中**的问法（50 条）+ 当时六路返回的候选 | 下一阶段 |
| `lexical-overlap.json` | 问法与 gold 条文的**字面重合率**（"按字找"的先天天花板） | 报告 B 节 |
| `query-preprocess.json` | 生产**实际喂给六路通道**的查询串逐条清单（与原始问法的差异） | 报告 §八 第 4 条 |
| `determinism.json` | 抽 12 条各跑两遍是否逐字一致 | 质量证据 |
| `rerun-consistency.json` | **全量**重跑对照（171 条 × 6 路 × 5 字段，基线由 `git show bd7516a:…` 取回，可复算） | 报告头部那条断言 |
| `config-inventory.md` | 任务 5：当前检索配置盘点（只读代码与库） | 业主 + 外部评估 |

---

## 二、口径（**读数字之前必须先读这一节**）

### 1. 并集的两种口径（**名字必须分开用**）

| 口径 | 定义 | 用途 |
|---|---|---|
| **同预算口径**（`union.same_budget`，**报告主口径**） | 每一路都只取**前 d 条**再取并集，`d ∈ {20,100,1000}`；`d>20` 时 B/C 用深读列表 | 把"**召回不到**"与"**被截断**"分开 |
| **生产上限口径**（`union.prod_caps`） | 照 `perform_hybrid_search` 的**真实限量**：A/D/E **取全量**、B/C/F 取前 20 | 回答"**系统手里到底有没有**这条条文" |

⚠ 两者**不是一回事**，也**不许混着叫**（2026-10-06 独立复核打回的就是这一点）：
生产口径下通道 D 一次能拉 14 万条，于是"gold 在候选池里"可能只是名次在**第 8 万位**、
RRF 权重约 `1e-5`（名义上有、实际等于没有）。**报告的主口径是同预算口径。**

### 2. "六路"在这个库里的实际状态（逐条实测，不是推断）

| 通道 | 生产问答路径会不会开 | 依据 |
|---|---|---|
| A 条款号精确 | 只在提问含条款号时 | `hybrid_engine` 通道 A 的 `if exact_no:` |
| B 全文 FTS5 | **恒开** | 无前置条件 |
| C 向量 | **恒开** | 需向量引擎可用 |
| D 模态 | 只在提问含模态词时 | `search_with_details` 用 `extract_modality_from_query` 推导 |
| E 法理要素 | **恒关** | 三个生产调用点都不传 `subject_filter`；且 `clause_revision.subject` 全库仅 2,171/522,021 非空 |
| F 行为客体 | **恒关** | 三个生产调用点都不传 `behavior_scope_filter`；且 `clause_fts.behavior_scope_segmented` **全库 0 行非空** |

### 3. 只读保证

- 真库以 `file:<path>?mode=ro` 打开（URI 只读），**不写库**；脚本开始/结束时核对文件 mtime。
- **不改任何源文件**（`funnel.py` 里对 `hybrid_engine._conn` 的赋值只是让生产函数跑在只读连接上，
  是**进程内替换**，不落盘、不影响任何别的调用者）。
- 逐条结果**边跑边写 + `fsync`**，中断后重跑自动跳过已完成项（断点续跑）。

### 4. 副本一致性校验（**这一步决定了上面那些数字可不可信**）

`funnel.py` 自带六路 SQL 的副本（因为生产函数**不返回**单通道候选列表，而漏斗必须逐路看名次）。
副本与生产实现之间可能漂移 ⇒ 每条问法都当场做一次比对：
把副本的单通道候选取前 20、按生产的结果循环（跳过 `fetch_full_clause` 取不到的和已废止/被替代的），
与 `perform_hybrid_search(q, channels=[单通道], top_k=20)` 的返回逐个比较。
**任何一条不一致都会写进 `funnel-summary.json` 的 `replica_check`**，不一致就是仪器坏了，结论作废。

⚠ **这层自检的覆盖面要说准**（独立复核指出初版说法过宽）：它只覆盖
**A / B / C / D 四路**（E/F 在生产路径上恒 0 候选，不参与），而且**只比前 20 条**。
**深读 1000 的名次不在这层自检里** —— 那部分由复核**独立重跑生产函数抽验 9 条问法**的名次（随机 5 条 + 针对性 4 条，含模态那一路第 80,101 名），全部一致。

---

## 三、怎么复跑

```powershell
# 0) 前置：真库在 %APPDATA%\KnowledgeStation\database\knowledge.db；模型权重已在本机缓存
cd 'D:\AI\work space\zcode'

# 1) 考卷轻清洗
& .venv\Scripts\python.exe eval\recall-funnel\build-v2.py

# 2) 六路漏斗（全量约 20 分钟；逐条落盘，中断可续跑）
& .venv\Scripts\python.exe -u eval\recall-funnel\funnel.py

# 3) 折表
& .venv\Scripts\python.exe eval\recall-funnel\summarize.py

# 4) 失败样本留证
& .venv\Scripts\python.exe eval\recall-funnel\failure-samples.py

# 5) 三条质量证据
& .venv\Scripts\python.exe eval\recall-funnel\lexical-overlap.py     # 字面重合率
& .venv\Scripts\python.exe eval\recall-funnel\determinism.py --n 12        # 抽 12 条跑两遍是否一致
& .venv\Scripts\python.exe eval\recall-funnel\rerun-consistency.py       # 全量重跑对照（需 git 里的旧记录）
& .venv\Scripts\python.exe eval\recall-funnel\preprocess-diff.py     # 生产实际搜索串清单
```

**先跑 3 条校验**（改脚本后必做）：`funnel.py --limit 3`，看 `replica_check` 是不是 `"ok"`。

---

## 四、边界与已知限制

| # | 限制 | 为什么不能靠这份数据说话 |
|---|---|---|
| 1 | **考卷是反推来的**（看着条文写问法） | 天然偏向"能读出问法的条文" ⇒ 用它算出来的召回率**偏向乐观**，只能当**相对比较工具**，不许包装成"系统召回率是 X%" |
| 2 | **171 条问法只落在 79 条独立条款 / 72 篇文档上** | 独立样本数远小于 171 ⇒ 不许拿百分比的小数位做文章 |
| 3 | **主结果只有 120 条**（171 条里 3/3 一致且 gold 在库里唯一的） | 其余 51 条要么判定不一致、要么 gold 在库里不唯一 ⇒ 已从主结果移出（样本仍留在文件里，带原因） |
| 4 | 融合那一路用的是**原始问法** | 生产实际喂给通道的是查询理解+别名扩展之后的串（171 条里 **13 条**不同）⇒ 融合名次与线上可能有极小差异 |
| 5 | 融合记录的是 `rerank=False` | 与 `ks_answer` 的默认一致（`params.get("rerank", False)`），但引擎自己的默认是 `True` ⇒ 换调用点会不同 |
| 6 | `boost_bookmarks=False` | 为了让结果可复现；生产默认 `True`（已收藏条款 +0.15）。本机收藏集为空时两者等价，**未逐条核对收藏集是否为空** |
| 7 | 没测"改一改会怎样" | 全程零改动：没换 embedding、没动切分、没动 `retrieval_text`、没调权重、没重算向量 |

---

## 五、四个难度子集（FR-005 / FR-009，2026-10-09 补）

**这一节是四个子集口径的唯一真源，别处只链接。** 标签由 `build-v2.py` 在**构建考卷时**算好，
写进每条记录的 `v2.subset`；`summarize.py` **只按标签分组**出 `funnel-summary.json` 的
`by_subset` / `by_subset_headline`（**不重算** —— 免得同一件事出现第二套口径）。
`v2.answer_out_of_corpus`（FR-006）同理：构建时标记，统计时**先排除再算所有分母**。

| 子集 | 判据 | 依据 |
|---|---|---|
| **短条款** | gold 条款 `content_text` < **40 字** | `specs/002-recall-funnel/spec.md` 边界条"短条款占 36.8%（<40 字的条款）" |
| **字面零重合** | 提问与 gold 条文**没有 ≥2 字的公共子串**（`overlap < 2`） | `docs/research/lay-phrasing-scaleup-test.md` L80 那张分解表（"与定义条款有 ≥2 字重合"= 否 ⇒ **53.0%** 那一档） |
| **带标准号** | 提问里出现标准号**形态**，且**库里真有对应文档** | 复用生产通道 A 的**两件**：`_STD_IN_QUERY_RE` + `_known_standard_keys`（`src/core/retrieval/hybrid_engine.py`）；⚠ 本批提问命中 **0/171** ⇒ 这条判据**本批未行使**（第 9 轮独立复核 P1-1：它当时还带着一个未定义变量，现已修 + 加回归自检，见 §5.5） |
| **普通** | 以上都不是 | —— |

⚠ **四个桶是互斥分区**（"普通"只有在互斥下才有意义）。spec 只**列举**了四个子集（`spec.md` FR-005）、
**没有规定优先级** ⇒ **优先级是选的**，这里取 spec 的列举顺序：
**短条款 → 字面零重合 → 带标准号 → 普通**。各标记的**独立命中条数**也一起存在 `v2.subset` 里，
想换优先级的人可以自己重算 —— `by_subset_sensitivity.partition_alt_priority` 就是换过优先级的对照。

⚠ **这条优先级的已知代价（第 9 轮登记）**：spec 的 Edge Case 说"提问里带明确标准号 ⇒ 这类要能单独切片，
它们是**'引用型通道'的适用对象**"。而在上面的顺序里 **"带标准号"排在"字面零重合"之后** ⇒
**一道既带标准号、字面又零重合的题会被判成"字面零重合"**，恰好丢掉 spec 最想要的那个信号
（本批 0 条带标准号，所以这个代价本批**没有显形**）。要按"引用型通道适用对象"切片时，
**请用标记 `has_standard_no_verified` 而不是 `label`**（标记是独立布尔，不受优先级影响）。

### 5.1 本批 171 条实测：**四个子集里有两个几乎不存在**

| 子集 | 全量 171 | 主结果 120 |
|---|---|---|
| 短条款 | **8**（4.7%） | 2 |
| 字面零重合 | **121**（70.8%；互斥分区里 113，另有 8 条被"短条款"优先取走） | 83 |
| **带标准号** | **0** | 0 |
| 普通 | 50 | 35 |

- **为什么"带标准号"是 0**：考卷是**反推**出来的外行问法，提问里不会出现 `GB 50016` 这种串。
  **这正好解释了 `REPORT.md` §B 里通道 A 触发 0/171**（通道 A 还要求提问含条款号；实测含
  `\d+\.\d+` 形态的只有 **3** 条 —— i=141/144/151，全是"0.15%""0.5 个点"这类**小数**，
  取出来当条款号在库里 **0 命中** ⇒ 触发 0）。
  ⇒ `REPORT.md` §零 那句"外行不会说「查 GB 30871 第 5.2 条」"**现在是量出来的，不是推的**。
- **为什么"短条款"只有 8 条**：spec 那个 36.8% 是**语料级**的数。本批实测（2026-10-09，
  `clause_revision` **663,634** 行）：`LENGTH(content_text) < 40` = **223,181 行 = 33.63%**；
  抽条池 `var/tmp/clause-pool.jsonl` 10.45%；而考卷的 gold 是"**能读出外行问法**"的那一小撮 ⇒ 4.7%。
  ⚠ **36.8% 本轮没复现**（33.63% vs 36.8% 差 3.2pt）：库在这段时间从 522k 长到 663.6k、组成变了。
  **不猜**，登记在此。

### 5.2 子集的**分辨力**（这才是 FR-009 想要的东西）

全量 171 条、六路并集 @1000（`by_subset` 全表见 `funnel-summary.json`）：

| 子集 | n | 并集@1000 | L1（六路深读 1000 都没召回） |
|---|---|---|---|
| 字面零重合 | 113 | **27.4%** | 82（72.6%） |
| 普通 | 50 | **66.0%** | 17（34.0%） |
| 短条款 | 8 | 37.5% | 5 |
| （全体） | 171 | 39.2% | 104 |

⇒ **"字面零重合"那一档的召回率只有"普通"的 41%**（27.4% vs 66.0%）。这是本仓第一次把
"**词对不上**"与"**有词可对但排不上**"分开量到（`REPORT.md` §B 只有前者，且只有零重合率没有命中率）。
⚠ **短条款 n=8、带标准号 n=0 ⇒ 这两档不许下结论。**

### 5.3 两个"零重合"口径不许混（本仓已踩过一次）

| 口径 | 判据 | 全量 171 | 出处 |
|---|---|---|---|
| **字符级**（**本批标签口径**） | 无 **≥2 字**公共子串 | **121** | `lay-phrasing-scaleup-test.md` L80（53.0% 那一档） |
| 词级 | 与通道 B 同款分词下**无共同词** | **132** | `lexical-overlap.json`（`REPORT.md` §B 用的 77.2%） |

两个数**不是同一件事**（`clean-v3/CORRECTION-53pct-has-a-source.md` §三 已为此警告过一次）；
`by_subset_sensitivity` 把两个数都出。
⚠ 还有一层：本批考卷在**生成时**过滤掉了与条文有 **≥4 字**重合的问法（`generate.py` 的 `ov >= 4` 丢弃）
⇒ 这份考卷的"零重合率"**天然高于**抽条池 ⇒ **不许拿这里的 70.8% 去和池子的 53.0% 比**。

### 5.4 改动链条（改了 `build-v2.py` 就要按这个顺序重跑）

```powershell
& .venv\Scripts\python.exe eval\recall-funnel\build-v2.py                       # 1) 重出考卷 v2
& .venv\Scripts\python.exe eval\recall-funnel\clean-v3\03-merge-tiers.py        # 2) 重出 v3（纯合并，只用盘上 tier-labels.jsonl）
& .venv\Scripts\python.exe eval\recall-funnel\summarize.py                      # 3) 重出汇总
```
⚠ `benchmark-v2.jsonl` / `benchmark-v3.jsonl` 是**别处实验的冻结输入**（`exp-3/3b/4/4b/4c` 都读它）。
新增字段是**向后兼容**的，但**改它们要登记**：2026-10-09 那次（T016/T017）的改动面已逐字段核对 =
**只新增 `v2.subset` / `v2.answer_out_of_corpus` 两个键 + 2 条 `flag_detail.same_def_docs` 的活计数
（库长大所致：1,980 → 2,201）**，`v3` 层与 `tier-stats.json` **零变化**。

⚠ **冻结的是产物，不是输入**（第 9 轮复核 P2-2）：`summarize.py` 的**输入**是 `funnel-per-query.jsonl`
（171 行，六路逐条记录），它**没进**第 9 轮的冻结清单。它当时与 PRE 逐字节未变（`git diff --stat` 里没有它），
但**以后派复核要把"输入级"也列进去** —— 只改它就会让 `funnel-summary.json` 变而冻结哈希核不出来。

### 5.5 第 9 轮独立复核抓到的问题与处置（2026-10-09）

复核报告：`D:\AI\verify-trees\VERIFY-REPORT-t016-t017-subsets.md`（结论 = **有条件放行**）。

| 级别 | 问题 | 处置 |
|---|---|---|
| **P1-1** | `build-v2.py` 里 `_known_standard_keys(…, doc_stds)` 的 **`doc_stds` 从未定义** —— 本批 0/171 命中 `_STD_IN_QUERY_RE` ⇒ `bool(_std_form)` **短路**，那个名字从未被求值 ⇒ 既不报错也永不生效；**一旦新考卷有题带标准号就当场 `NameError`**（与 T017 想堵的"换考卷"直接冲突）。⇒ 之前文档里写的"与通道 A 同一把尺子"**在代码里不成立** | ✅ **已修**：补 `doc_stds = [s for (s,) in conn.execute("SELECT standard_no FROM doc_meta")]`（喂法照抄生产通道 A），`std_of_key` 改为由它派生（一次查询两用）；**并加回归自检** —— 用一条**合成提问**把同一段判据跑一遍（变量缺失/正则坏掉 ⇒ 构建当场失败），另加"喂空 `doc_stds` 必须零命中"钉住验库闸没退化 |
| **P2-1** | 作者报的"排除机制变异"桶数 **`113→108 / 50→53` 数学上不可能**（只排除 3 条只会减不会增） | ✅ **已更正为实测的 `8→7 / 113→111 / 50→50`**（分母 171→168 不变）。根因：作者的变异产物 `var/tmp/round8-bak/mutA/` 里**除 3 条 aoc 外还手改了 5 条 label**（i=1,2,6,8,9）⇒ **两件事被混成一组读数**。已在 `tasks.md` / 开发史 §10.212 更正 |
| **P2-2** | `funnel-per-query.jsonl`（`summarize.py` 的主输入）没进冻结清单 | ✅ 已登记（见上一段） |

**端到端复验（作者自做，隔离副本 `D:/AI/verify-trees/_r9fix`，主仓未被触碰）**：

```
patched: i=1 query → "按 GB 50016-2014 的要求，这个间距该留多少？"；i=2 gold_std → GB/T 99999-9999（库里没有）
$ .venv/Scripts/python.exe eval/recall-funnel/build-v2.py     # exit=0，无 Traceback
自检：带标准号判据可执行（合成提问抽出 1 个形态，验库后 verified=True；空表零命中 ✓）
i=1 aoc=False label=字面零重合  markers={short:False, zero:True, std_no:True, std_no_verified:True}
i=2 aoc=True  label=字面零重合  markers={short:False, zero:True, std_no:False, std_no_verified:False}
counts.answer_out_of_corpus = 1   markers_all={std_no:1, std_no_verified:1}   partition_all={零重合:113, 短条款:8, 普通:50}
```

⚠ 顺带暴露一个**设计代价**（已登记在上面的优先级说明里）：i=1 明明 `std_no_verified=True`，
`label` 却是**字面零重合**（优先级所致）⇒ 要按"引用型通道适用对象"切片请用**标记**而非 `label`。

**修复后重跑三步链条 ⇒ 五个产物与修复前【逐字段完全一致】**（`benchmark-v2.jsonl` / `benchmark-v3.jsonl` /
`clean-v3/tier-stats.json` / `benchmark-v2-stats.json` / `funnel-summary.json` 全部 `IDENTICAL`）
⇒ **冻结读数一个都没变**，变的只是"这条判据现在真的能跑"。

