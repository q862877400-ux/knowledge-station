# 当前检索配置盘点（任务 5：只读代码与库，不做任何修改）

> **这份是"现状是什么"，不是"应该怎样"。** 全部取自**只读**读取：源码文本 + 真库
> （`file:...?mode=ro`，WAL 只读打开）。
> **口径**：能引源码的引"文件 + 可搜索文本"，不写行号（行号会随改动漂移）。
> **真库**：`%APPDATA%\KnowledgeStation\database\knowledge.db`（2,283.6 MB，实测）。

---

## 一、向量嵌入

| 项 | 值 | 出处 |
|---|---|---|
| 模型 | `BAAI/bge-small-zh-v1.5` | `src/core/retrieval/embedder.py` 的 `_get_model` |
| 维度 | **512** | 同文件常量 `EMBEDDING_DIM = 512`；库表声明 `embedding FLOAT[512]` |
| 运行时 | fastembed `TextEmbedding`，**ONNX / CPU** | `_get_model` → `from fastembed import TextEmbedding` |
| 权重缓存 | `%APPDATA%\KnowledgeStation\models\models--Qdrant--bge-small-zh-v1.5` | `Settings.models_dir` |
| 查询侧 | `embed_query(text)` → 一条 512 维向量 | 同文件 |
| 建库侧 | `embed_batch(texts)` | 同文件 |
| 不可用时的行为 | 抛 `VectorEngineOfflineError` → 检索层降级（R30）；失败进 **60 秒冷却窗**（窗口内不重试） | `RETRY_COOLDOWN_S` |

**库侧规模（实测）**：`clause_vec` **522,021 行**。

**索引类型**：`sqlite-vec v0.1.9` 的 `vec0` 虚拟表，**暴力精确扫描**（`WHERE embedding MATCH ? AND k = ?`），
**没有近似索引（ANN）、没有倒排/量化结构**。
⇒ 所以"近似索引把答案漏掉了"这种失败**在本仓不存在**；"调 ANN 参数"不是一条可修的路径。

---

## 二、全文检索

| 项 | 值 | 出处 |
|---|---|---|
| 引擎 | SQLite **FTS5** 虚拟表 `clause_fts` | `src/core/storage/schema.sql` 的 `CREATE VIRTUAL TABLE … clause_fts` |
| 分词器 | `tokenize = 'ascii'` | 同上 |
| 被检索列 | `content_segmented`（通道 B）、`behavior_scope_segmented`（通道 F） | 同上 |
| 索引侧分词 | `text_utils.segment_for_fts` = **jieba `cut_for_search` + 空格连接** | `src/core/text_utils.py` |
| 查询侧表达式 | `text_utils.fts_match_expr` | 同文件 |
| **查询侧连接词** | **`OR`**（不是 AND） | `fts_match_expr` 返回 `" OR ".join(quoted)` |
| 排序 | `ORDER BY rank`（FTS5 内建 **bm25**），`LIMIT 20` | `hybrid_engine.py` `# 通道 B` |
| 词处理 | 每词加引号；丢掉单字符词；**纯字母、词面 ≥4、无内部大写、词干 ≥4** 的拉丁词换成 `"词干"*` 前缀查询 | `fts_match_expr` / `_latin_prefix_token` / `_MIN_STEM` |

**库侧规模（实测）**：`clause_fts` **522,021 行**；`content_segmented` 非空 521,978（43 行空）。

⇒ **通道 B 的实际形态是「宽 OR + bm25 排序 + 硬截断 20」**：一句外行话被 jieba 切成一串词后
用 OR 全连起来，命中池是"任意一个词出现过"的条款。实测命中池大小在**几百到几万条**之间
（本次 171 条问法逐条记了 `fts_pool`）。

---

## 三、Reranker（融合之后、给用户之前的那一步）

| 项 | 值 | 出处 |
|---|---|---|
| 模型常量 | `RERANK_MODEL = "BAAI/bge-reranker-base"` | `src/core/retrieval/reranker.py` |
| 注释里的说法 | 文件头简介写的是 `BAAI/bge-reranker-v2-m3`，同文件注释说明因 fastembed 0.8.0 不支持才换成 base | 同文件文件头与 `RERANK_MODEL` 上方注释 |
| ⚠ 不一致 | **文件头简介与实际常量不是同一个模型** —— 照实记录，未修改 | 同上 |
| 运行时 | fastembed `TextCrossEncoder`，ONNX / CPU | `_get_model` |
| 输入 | 融合后前 `rerank_n` 条（默认 **24**）的 `content_text[:512]` | `hybrid_engine._rerank_results` |
| 降级 | 模型不可用/异常 → **原序返回** + `rerank_offline=true`，不阻塞 | `reranker.rerank` 与 `_rerank_results` |
| 例外保护 | 含"但书/除外/另有规定"的候选被 rerank 挤出时**强制保留** | `_protect_exception_clauses` |
| 生产是否开 | **关闭** —— `ks_answer` 取 `params.get("rerank", False)`，默认 False | `src/core/llm/ks_answer.py` |

---

## 四、六条召回通道：怎么生成候选、各取多少

**实现位置：全部在 `src/core/retrieval/hybrid_engine.py` 的 `perform_hybrid_search` 里**
（逐条注释标记 `# 通道 A:` … `# 通道 F:`；通道名清单在 `src/core/domain/models.py` 的 `SEARCH_CHANNELS`）。

| 通道 | 名 | 怎么生成候选 | **触发条件** | **取回上限** |
|---|---|---|---|---|
| **A** | `exact` 条款号/法条号精确 | 从**提问**里正则认条款号（`_CLAUSE_NO_RE` / 附录号 `_CLAUSE_NO_APPENDIX_RE`）→ `WHERE cr.clause_number = ?`；认得出标准号时再按标准号筛（`_rows_matching_standard_keys`） | **提问里必须含条款号** | **无上限**（刻意不加，见该文件顶部长注释） |
| **B** | `fts` 全文 | `clause_fts MATCH fts_match_expr(query)`，`ORDER BY rank` | 恒（除非分词后为空串） | **`LIMIT 20`**（写死在 SQL 里） |
| **C** | `vec` 向量 | `embed_query(query)` → `clause_vec WHERE embedding MATCH ? AND k = 20` | 向量引擎可用时恒 | **`k = 20`**（写死） |
| **D** | `modality` 模态 | `WHERE cr.modality = ?`，值由**调用方**传 `modality_filter`；`search_with_details` 会用 `extract_modality_from_query` 从提问里认 | **调用方必须传 `modality_filter`** 且提问里有模态词 | **无上限** |
| **E** | `legal_element` 法理要素（义务主体） | `WHERE cr.subject = ? AND cr.knowledge_type='legal'`，值由**调用方**传 `subject_filter` | **调用方必须传 `subject_filter`** | **无上限** |
| **F** | `behavior_scope` 行为客体（合规审查专用） | `clause_fts MATCH fts_match_expr(behavior_scope_filter)` 匹配 **`behavior_scope_segmented`** 列 | **调用方必须传 `behavior_scope_filter`** | **`LIMIT 20`** |

### 生产问答路径实际传了哪些 filter（三个调用点全查过）

| 调用点 | 调用 | 传了 subject / behavior_scope？ | rerank 默认 | top_k 默认 |
|---|---|---|---|---|
| `src/core/llm/ks_answer.py` | `search_with_details(search_query, top_k, channels, include_superseded, rerank, doc_ids)` | **都没有** | `False` | **8** |
| `src/core/api/server.py` | 与上面同形 | **都没有** | 同上 | 同上 |
| `src/core/vision/local_vision.py` | `perform_hybrid_search(query, top_k=top_k)` | **都没有** | 引擎默认 `True` | 调用方给 |

⇒ **结论（实测，不是推断）**：在"用户用大白话提问"这条路上，
**通道 E、F 恒为 0 候选**；**通道 D 只在提问里出现模态词时才开**；
**通道 A 只在提问里出现条款号时才开**。
**恒常工作的只有 B（FTS）与 C（向量）两路。**

### 通道各自的"料"有多少（真库实测）

| 通道 | 依赖的列 | 非空行数 / 全库 522,021 | 说明 |
|---|---|---|---|
| D `modality` | `clause_revision.modality` | **215,597（41.3%）** | `应` 140,555 / `可` 23,798 / `不应` 15,338 / `可以` 9,566 / `宜` 5,826 / `不得` 4,820 / `不能` 4,690 |
| E `legal_element` | `clause_revision.subject` | **2,171（0.42%）** | 几乎没建起来 |
| F `behavior_scope` | `clause_fts.behavior_scope_segmented` | **0（0%）** | 🔴 **列全空** ⇒ 即便有人传 filter，F 也**结构上**匹配不到任何东西 |

---

## 五、最终融合

**位置**：`perform_hybrid_search` 尾部。

1. **通道内名次 → 分数**：`W / (RRF_K + rank + 1)`，`RRF_K = 60`，`rank` 从 0 起。
2. **通道权重**（`CHANNEL_WEIGHTS`）：

   | exact | fts | vec | modality | legal_element | behavior_scope |
   |---|---|---|---|---|---|
   | **2.0** | 1.0 | 1.0 | 0.8 | 0.8 | **1.2** |

3. **收藏加分**：已收藏条款 `+0.15`（`boost_bookmarks`，生产默认 `True`）。
4. **排序**：按总分降序（同分次序由 dict 插入序决定，不保证全序）。
5. **时效过滤**：逐条 `fetch_full_clause`，`superseded` / `withdrawn` 跳过（`include_superseded=False`）。
6. **截断**：`cap = rerank_n if (rerank and rerank_n > top_k) else top_k`，`rerank_n` 默认 24。
   - `rerank=False`（生产问答默认）⇒ **cap = top_k = 8**；
   - `rerank=True` ⇒ 先取 24，再过 cross-encoder，再裁到 `top_k`。

### 候选截断位置（一句话）

> **B/C/F 各自只出 20 条候选 → 全部拿去 RRF 打分 → 排序后按 `cap` 截断。**
> 生产问答路径下 `cap = 8` ⇒ **用户最终只看到 8 条**，而其中能进候选池的
> **只有 B 的 20 条 + C 的 20 条**（外加 A/D 偶尔开一次）。

### 检索之后还有一道后处理（不属于"六路"，但会改最终名次）

`ks_answer` 在拿到检索结果之后还会做：条件过滤 `qu.apply_condition_filter` →
效力置顶 `qu.rank_with_hierarchy` → 标题条款聚合 `_expand_title_clauses` →
`_filter_effective` → 按 `max_evidence` 截断。
检索**之前**还有：`qu.parse_declared` / `detect_theme` / `classify_intent` /
`refine_search_query` + `expand_with_alias`（别名扩展）+ `expand_query_with_history`（追问并入）。
⇒ **喂给六条通道的不是用户的原始问法，是这一串处理后的串**（本次 171 条里，
**13 条**处理后与原始问法不同）。

---

## 六、机器与库

| 项 | 值 |
|---|---|
| CPU / 内存 / GPU | i7-14700KF（20 核 28 线程）/ 63.8 GB / RTX 4080 SUPER |
| 库文件 | `%APPDATA%\KnowledgeStation\database\knowledge.db`，**2,283.6 MB** |
| journal_mode | `wal`（本次以 `mode=ro` 只读打开，前后 mtime 一致） |
| 条款 / 文档 | `clause_revision` **522,021** / `doc_meta` **6,797** |
| 条款级效力 | effective **521,984** / 已废止或被替代 **21** / reference **16** |
| 文档级效力 | effective 6,777 / reference 16 / withdrawn 4 |
| 知识类型 | `rule` 421,868 / `data` 97,621 / `legal` 2,532 |
| 条款内容类型 | `normal` 507,323 / `附录` 8,284 / `前置说明` 6,414 |

---

## 七、这份盘点的"没做"

- **没有改任何一行源码**，也没有改任何库数据（只读打开，已核对 mtime 未变）。
- **没有测**"把 B/C 的上限放开会怎样""换 embedding 会怎样""改融合权重会怎样"——
  这些都属于**下注**，要等漏斗结论出来再定。
- 通道 A/D/E 的"为什么刻意不加行数上限"是本仓一条**有记载的决定**（含复核实测：
  加 `LIMIT 500` 会把 384/6,793 篇文档的条款全砍光），**本次只引用、不重开**。
