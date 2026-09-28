# Hindsight 官方文档 · 通读纪要（一手件，已核到行号）

> **本文是"读过的部分"的纪要**，供新对话直接接续，不必重读。**未读的 35 篇**在 §6 列出。
> **一手件**：`https://hindsight.vectorize.io/llms-full.txt`（全站正文，938,683 B，**生成时间 2026-09-28T19:18:34Z**，
> 自称 "complete Hindsight documentation for LLM consumption"）＋ `https://hindsight.vectorize.io/openapi.json`
> （603,960 B，**Hindsight HTTP API v0.10.1**，77 条路径 / 99 个操作）。
> **本机副本**：`C:\Users\Zegel\AppData\Local\Temp\hs-docs2\`
> ├ `llms-full.txt`（整站）　└ `split\`（**已按篇切开的 42 个 .md** ← 新对话直接读这个目录）
> 切分脚本：`var/tmp/hs-split.py`（在 `D:\AI\work space\zcode`，可直接重跑）。

---

## §0 取件过程中踩到的坑（留给新对话）

- 文档站是 **Docusaurus SPA**：`/docs/developer/api/retain`、`/docs/concepts` 等路径**全部返回同一个
  22,747 B、`<title>` 只有 "Hindsight" 的 404 壳**。⚠ **HTTP 200 但不是正文**——本项目已多次栽在这条上。
- `llms.txt` 也是 404 页（4 KB）。**只有 `llms-full.txt` 是真的**（938 KB）。
- 拿到整站正文后**不要再用关键词去搜**（我第一轮就是这么干的，等于拿二手材料的关键词去官方文档里找它，
  只能验证那份材料对不对，读不出 Hindsight 实际有什么 —— 业主当面指出过这个错）。

---

## §1 已通读的 6 篇（逐条给行号，逐字引用）

### 1.1 `developer/performance.md`（262 行）— **规模问题的正主**

| 行 | 逐字要点 |
|---|---|
| 16 | "architectured from the ground up to prioritize read performance over write performance…memories are written once but read many times"（读写比典型 **10:1 或更高**） |
| 29–33 | Recall **100–600ms**，瓶颈是 **CPU 上的 re-ranker**；Reflect 800–3000ms；Retain 500–2000ms/batch，瓶颈是 **LLM 事实抽取** |
| 49 | **"Hindsight Doesn't Need a Smart Model"** —— 事实抽取推荐 `gpt-oss-20b`（Groq） |
| 179–183 | 默认 rerank **最多 300 个候选**；`HINDSIGHT_API_RERANKER_MAX_CANDIDATES` 可调小 |
| 215–219 | 🔴 **PostgreSQL + pgvector，HNSW 索引**；"Typical query time: **10-50ms for vector search on 100K+ facts**"；"Scalability: **Tested with millions of facts per bank**" ⚠ **厂商自报，无测试条件、无"多少条↔多少延迟"对应** |
| 245 | 水平扩展 = **"Deploy multiple API instances behind a load balancer with shared PostgreSQL"** ⇒ **要守护进程** |

⚠ **第 90–192 行整段是"本地/小环境调优"**，与我们的部署形态（Windows 单机）**直接相关**，新对话必读：
`HINDSIGHT_API_LLM_MAX_CONCURRENT` 默认 32 → 本地要降到 **2**；
`HINDSIGHT_API_CONSOLIDATION_LLM_BATCH_SIZE` 默认 8 → 小模型降到 **2**；
reranker CPU 调优（FP16 在 Apple Silicon 快 27–36%、按长度分桶快 36–54%）、`flashrank` 轻量 ONNX 重排器。

### 1.2 `developer/rag-vs-hindsight.md`（112 行）— **它自己承认我们这种场景该用 RAG**

| 行 | 逐字要点 |
|---|---|
| 30–41 | 🔴 **它自己的召回流程**＝①解析查询（抽时间表达式/实体）②**四路并行：semantic、BM25、graph、temporal** ③**RRF 融合** ④**cross-encoder 重排** ⑤施加 disposition 三性（skepticism/literalism/empathy）⑥生成 |
| **102** | 🔴 **"Document Q&A over static corpus" ⇒ 推荐 RAG**；"AI assistants with persistent memory" ⇒ 才用 Hindsight |
| 45–96 | 它举的多跳/时间查询/实体理解四个例子，**全部是英文个人对话**（Alice、订阅、账务、Python→asyncio），**没有一条是法规/文档语料** |

⇒ **它的四路 ≈ 我们的六路**（我们：exact/fts/vec/modality/legal_element/behavior_scope）。
**我此前把 Hindsight 当"单路"是错的。**

### 1.3 `developer/storage.md`（91 行）— **"不做存储抽象"是明示取舍；pg0 就是内嵌 PG**

| 行 | 逐字要点 |
|---|---|
| 4 | 主存储 **PostgreSQL**（另有 Oracle AI Database） |
| 12 | 向量 = **pgvector + HNSW**；全文 = tsvector + GIN；图 = 递归 CTE |
| 28–40 | 🔴 **"Hindsight does not abstract storage behind a generic interface. This is a deliberate trade-off."** |
| 48–71 | 本地开发用 **pg0**（单二进制内嵌 PG，预装 pgvector，**端口 5555**，数据在 `~/.hindsight/pg0/`） |

⇒ ⚠ **我们本机那个 4.7 GB 的 `~/.pg0/instances/` 就是它。**
⇒ ⚠ **"我们不引守护进程"这句话需要修正**：我们现在跑的 Hindsight **本身已经依赖一个 PostgreSQL 进程**（pg0 打包的）。

### 1.4 `developer/knowledge-pages.mdx`（81 行）— **直接命中业主的原始设想**

| 行 | 逐字要点 |
|---|---|
| 4 | "**Knowledge pages are living documents a bank writes about itself.** Each page answers one question … and rewrites itself as the bank learns more. …**The shape is a wiki. The engine underneath is memory.**" |
| 12 | **一个 knowledge page 就是一个 mental model**（简化版） |
| 27 | 文件夹树，任意嵌套，**页名在文件夹内唯一，删文件夹即删子树**；例：`Architecture/`、`Runbooks/`、`Decisions/` |
| 38–41 | 🔴 **`hindsight fs mount --bank my-bank`** —— 把知识库**镜像成磁盘上真实的 markdown 文件（带 YAML frontmatter）**，后台循环保持更新；之后 `ls`/`cat`/`grep`/`rg`/编辑器/agent 文件工具都能用 |
| 49–51 | 🔴 页面检索 = **文档级**（整页返回 + 摘要），**全文 + 语义服务端融合、不过 rerank**；逐字：**"Search is a tool an agent chooses to call, visible in the transcript, rather than content pushed into its context on every turn. Retrieval the agent asked for informs what it's doing; retrieval it didn't ask for tends to derail it."** |
| 61–63 | 文件是"信息变老的地方，最后写的人赢，矛盾悄悄堆积"；**knowledge page 是处理后记忆的投影视图**，"like a database view is not a table"；"when a team decided X and later amended it to Y, **the page says Y — and can say why** — instead of preserving both a paragraph apart" |
| 65 | 🔴 **"Your raw documents remain the source of truth about *what was said*. The pages are the reconciled truth about *what holds*."** |
| 67 | 页面是**渲染不是存储** ⇒ 删掉一个 page 什么都不会丢，会从记忆重新投影 |
| 76 | agent 工具 `agent_knowledge_*`：会话中列出/读/建/更新自己的页面 |

### 1.5 `developer/multilingual.mdx`（284 行，**只扫了结构与中文关键行，正文未细读**）
章节：`How It Works` / `Retain with Non-English Content`（含 `Example: Chinese Content`）/ `Reflect with Non-English Queries`（含 `Example: Chinese Reflection`）/ `Mixed Language Content` / **`Supported Languages`** / `Configuring for Multilingual Use`（LLM 必配、**Embedding 推荐**、**Reranker 推荐**、**BM25/全文检索后端**）/ `Best Practices`（含"**查询语言与内容语言一致**"） / `Technical Details`。
⇒ **新对话必读的两处**：`Supported Languages`（L132）、`BM25 / Full-Text Search Backend`（L184）—— 后者对我们最关键（中文分词/全文后端怎么配）。

### 1.6 OpenAPI 端点盘面（v0.10.1，99 个操作，已全量列出）
关键分组：`memories`（retain / recall / reflect / list / curate / **history** / dry-run-extract / prompts-preview）、
`knowledge-base`（pages / folders / tree / **search**（BM25+vector）/ nodes 重命名移动删除 / **export 成 markdown 包**）、
`mental-models`（含 refresh / dry-run-refresh / history / clear）、
`consolidation`（consolidate / **strategies-preview** / **recover**）、
`directives`（增删改查，= 注入提示词的"最高指令"层）、
`documents` / `document-transfer`（导出导入）、
`stats` / `audit-logs` / `llm-requests` / `metrics`（**可观测性全套**）、
`operations`（异步作业，支持 **retry**）、`webhooks`、`aliases`、`clone` / `export` / `import` / `transfer`。

---

## §2 我们本机的现状（上一轮实测，与 §1 对照）

`http://127.0.0.1:8888`，bank `coding-agent::zcode`：114,970 条事实 / 5,337,849 条边 / 3,529 文档 /
**`pending_consolidation: 114970`（全部未归并）**、**`total_observations: 0`**、**`last_consolidated_at: null`**
⇒ **归并从未跑过**；知识页 8 篇（全在 Initiatives）；`directives` 上一轮我手工建过 1 条。

**判读**：我们**不是"缺功能"，而是"开了功能没用"** —— 归并没跑、知识页没当常驻答案层、
没用 `audit-logs`/`stats`/`llm-requests` 管垃圾率与成本。

---

## §3 已经能下的三条结论

1. **业主"我们在造轮子"的直觉成立。** 上一轮我做的整轮外部调研（记忆系统家族 + 技能进化 + 派生层）
   **基本没查官方 API 本身** —— 这是方法论失误，违反本仓"通用层纯借鉴"与"先查官方文档"的纪律。
2. **但撞上一堵硬墙**：他们的一切建立在 **PostgreSQL + pgvector + HNSW** 上，且水平扩展要
   **多实例 + 共享 PG（守护进程）** ⇒ 与我们"**不引守护进程、不换栈**"的硬约束**正面冲突**。
   **"亿级召回"那块没有现成轮子可骑**（我们 sqlite-vec 官方自述 brute-force only）。
3. **他们自己说我们这种场景该用 RAG**（§1.2 第 102 行：Document Q&A over static corpus ⇒ RAG）。
   而 §1.4 的知识页模型（原文层=说了什么、页面层=当前成立什么、页面能被 agent 主动检索、能镜像成磁盘 markdown）
   **恰好就是业主从一开始描述的形态**。

---

## §4 我**没有**核的（不许当已核）

- 官方**规模数字的测试条件**：`10-50ms @ 100K+`、`millions of facts per bank` 都是**厂商自报**，
  **无配置、无"多少条↔多少延迟"对应、无硬件说明**。
- `knowledge-base/search` 的**参数与返回形状**（只知摘要说 BM25+vector）。
- bank **模板 schema 的实际内容**（只知有 `GET /v1/bank-template-schema`）。
- 文档站**正文页**（SPA 壳）——我读的是 `llms-full.txt` 里的 mdx 源。
- 官方"控制面板支持中文"（未核，与本项目决策无关）。

---

## §5 顺带核出的一件事（那份二手材料的对错）

业主给的《亿级知识库召回难题》那份材料：**方向对、细节错**。
✅ 真的：bank 级导出/导入/克隆、Templates Hub 分享配置、bank 级 `mission` 字段（spec 中出现 9 次）。
❌ 错的：`retain` 单次请求**没有** `context` 参数（官方 `RetainRequest` 只有 `items`/`async`/`document_tags`/`operation_id`）；
**`extraction_mode`/`concise`/`verbose` 整个不存在**（整份 spec 0 次命中）。
⚠ 材料**漏了**对我们更要紧的 `knowledge-base/*` 与 `consolidation/*`。

---

## §6 未读的 35 篇（新对话从这里继续）

目录：`C:\Users\Zegel\AppData\Local\Temp\hs-docs2\split\`（`## File:` 切出 42 篇，我读了 6 篇）

**建议优先级**：
1. `developer__multilingual.mdx`（补 §1.5 未细读的两处：L132 支持语言、L184 BM25/全文后端）
2. `developer__oracle.md`（291 行）——**与业主那句"500 候选是 oracle 结果"直接相关**
3. `developer__monitoring.md`（409 行）——垃圾率/成本怎么管
4. `developer__mental-models.mdx` + `developer__api__mental-models.mdx`（4,533 + 56,544 字符）
5. `developer__configuration.mdx`（**254,113 字符，全站最大**）——配置面，改行为前必看
6. `developer__api__memory-banks.mdx`（67 KB）——bank 隔离模型（**这是与我们"一套库装全部"方向相反处**）
7. `developer__observations.mdx`（349 行）——观察/证据层
8. `developer__retrieval.md`（424 行）／`developer__api__recall.mdx`（901 行）
9. `developer__mcp-server.md`（768 行）——MCP 接入（我们 DSH 侧的工具面）
10. 其余：api/* 各篇、sdks/* 各篇、admin-cli、installation、models、services、development、extensions、memory-defense、webhooks、operations、documents、bank-templates、quickstart、main-methods

**读完的产出要求**：逐篇一行表（`文件 → 一句话它讲什么 → 与我们的关系：能抄/冲突/无关 → 证据行号`），
落盘 `docs/research/HINDSIGHT-DOCS-READING-2026-09-28.md`，并把 §7 的结论按新证据更新。

---

## §7 本任务要回答的业主问题（别跑偏）

> 「我感觉他这个结构是把知识库、skill 统一起来管理了，我们现在没有，真的没有价值吗？」

**要交付的**：一份**基于官方文档**的判断，明确回答——
① 我们自研的哪些应该停（改用官方既有）；② 哪些**不是**造轮子（官方也没解决）；
③ 「一套库装全部资料 + 跨项目派生记忆」与官方 **bank 隔离模型**的冲突怎么解；
④ 业主那句「他发现自己需要这个过程，其实就是一个检索的过程」官方怎么回的（已在 §1.4 第 49–51 行找到正面回答，展开即可）。

**边界**：本任务是**调研**，不是实施。产出落盘 + 提交，**不要改任何代码或判据**。
