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
| `benchmark-v2.jsonl` | 清洗后的考卷（171 条，每条带 `v2.bucket` / `v2.flags`） | 复核 |
| `benchmark-v2-stats.json` | 考卷统计（唯一条款数 / 票型 / 标记数 / 移出样本与原因） | 复核 |
| `funnel-per-query.jsonl` | **逐条**漏斗原始记录（每条：六路各自的 gold 名次 + 并集 + 融合 + 一致性校验） | 复核、复算 |
| `funnel-summary.json` | 上面那份折出来的表（含全量 / 主结果 / 按类型三套） | 报告的数据源 |
| `failure-samples.jsonl` | 六路深读 1000 全未命中的问法（50 条）+ 当时六路返回的候选 | 下一阶段 |
| `lexical-overlap.json` | 问法与 gold 条文的**字面重合率**（"按字找"的先天天花板） | 报告 B 节 |
| `determinism.json` | 同一套设置跑两遍是否逐字一致 | 质量证据 |
| `config-inventory.md` | 任务 5：当前检索配置盘点（只读代码与库） | 业主 + 外部评估 |

---

## 二、口径（**读数字之前必须先读这一节**）

### 1. 两种口径必须分开

| 口径 | 定义 | 用途 |
|---|---|---|
| **生产口径** | 完全照 `hybrid_engine.perform_hybrid_search` 的现有参数：B（FTS5）`LIMIT 20`、C（向量）`k = 20`、F `LIMIT 20`；A/D/E 无上限 | 回答"**现在**这套东西能不能召回" |
| **深读口径（探针）** | 同一条 SQL、同一个排序，只把 B/C 的 `k` 放大到 100/1000 | 把"**召回不到**"与"**截断了**"分开 |

⇒ 生产口径下 `union@100` 与 `union@1000` **必然**等于 `union@20`（因为没有任何一路能出 20 条以外）。
看到三个数一样不是 bug，是**当前实现的硬上限**。

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

# 5) 两条质量证据
& .venv\Scripts\python.exe eval\recall-funnel\lexical-overlap.py    # 字面重合率
& .venv\Scripts\python.exe eval\recall-funnel\determinism.py --n 12 # 跑两遍是否一致
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
