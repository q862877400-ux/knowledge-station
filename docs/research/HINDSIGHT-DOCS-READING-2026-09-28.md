# Hindsight 官方文档 · 通读纪要（一手件，已核到行号）

> **2026-09-28 第二轮已完成：42 篇全部读完。**
> 逐篇一行表 = **§8**；本机实测对照 = **§9**；业主 §7 四问的答案 = **§10**；仍**没有**核的 = **§11**。
> ⚠ 下面 §1–§7 是**第一轮**写的，其中 §6 的"未读 35 篇"已完成、§7 的问题已在 §10 回答；
> §6 还有**一处误读已在 §8.3 第 1 条更正**（`oracle.md` 是 Oracle Database 部署指南，不是"oracle 基准"）。
> ⚠ §3 的三条结论里，第 2 条"撞上 PostgreSQL 硬墙"**仍然成立**；第 1 条方向对但第 1 轮的方法论错误已在 §0 记下。

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

---
---

# 第二轮（2026-09-28 续）：剩余 35 篇读完 + 本机实测 + §7 四问

> **本轮读法**：不再用关键词去官方文档里找东西（第一轮的错误，见 §0）。整站 42 篇按篇读。
> 上轮 §1 记了 4 篇全文 + `multilingual` 只扫结构；本轮把**其余全部读完**，并**重读** `multilingual` 全文。
> 表里的行号都是实际读过那一段才写的。标「子代理」的表由并行子代理读，行号由子代理核对，我抽查了其中承重的几条（见 §8.3）。

## §8 逐篇一行表（全 42 篇）

「关系」列口径：**能抄**＝官方已有、我们应该改用它；**冲突**＝它与我们硬约束或业务语义正面冲突；**无关**＝对我们当前形态没有决策价值。

| 文件 | 一句话讲什么 | 与我们的关系 | 证据行号 | 轮次 |
|---|---|---|---|---|
| developer__performance.md | 读写比 10:1 的召回优先架构，PostgreSQL+pgvector+HNSW，水平扩展要多实例+共享 PG | 冲突（守护进程）／规模数字为**厂商自报，无测试条件** | L16, L29–33, L49, L179–183, L215–219, L245 | 上轮 |
| developer__rag-vs-hindsight.md | 它自己的召回＝四路并行+RRF+重排；并明说"静态语料的文档问答该用 RAG" | **能抄（四路流水线）**＋自我否定 | L30–41, **L102**, L45–96 | 上轮 |
| developer__storage.md | 主存 PostgreSQL，"不做存储抽象是刻意取舍"；pg0 = 内嵌 PG | 冲突（"不引守护进程"这句话要改） | L4, L12, L28–40, L48–71 | 上轮 |
| developer__knowledge-pages.mdx | 知识页＝会自己重写的活文档；原文层是"说了什么"，页面层是"当前成立什么" | **能抄（正中业主设想）** | L4, L12, L16–19, L27, L38–41, **L49–51**, L61–67 | 上轮／本轮复核 |
| **developer__multilingual.mdx** | **多语言全靠提示词；BM25 对中文需要 pgroonga/pg_search，而这两个都不在 pg0 内嵌 PG 里** | **能抄（配置面）／冲突（部署形态）** | **L132–144, L156–182, L184–220, L224–250, L262–263** | 本轮补读 |
| **developer__oracle.md** | ⚠ **是 Oracle Database 23ai 的部署指南，不是"oracle 基准"** | 无关 | L2–19, L249–268 | 本轮 |
| **developer__monitoring.md** | Prometheus/OTel/Grafana 三件套；`/health/live` vs `/health/ready` 的分工；`no_facts` 与 `batch_failures` 是两个静默失效信号 | **能抄（可观测性现成）** | L4, L45–100, **L149–154**, **L182–199** | 本轮 |
| **developer__configuration.mdx** | 全站最大配置面（3,060 行）。检索/写入/观察/reflect/MCP/审计/控制面全在这里 | **能抄＋冲突混杂，逐条见 §8.2** | 见 §8.2 | 本轮 |
| **developer__api__memory-banks.mdx** | bank 隔离模型的全文：per-bank 配置、`entity_labels` 受控词表、directives、bank 搬运 | **能抄（entity_labels）／冲突（隔离模型）** | L22–38, **L148–231**, L290–372, **L713–737**, L909–916, L920–934 | 本轮 |
| **developer__api__knowledge-pages.mdx** | 知识页全套接口：树、建页、建夹、读、**整页混合检索**、改/移、删、导出 markdown 包 | **能抄** | L26–126, L130–276, **L388–452**, L505–512, L555–609, L624–635 | 本轮 |
| **developer__mcp-server.md** | 内置 MCP 服务：per-bank 端点、单库 27 工具／多库 30 工具、工具注解、触发器设置 | **能抄（DSH 工具面对照面）** | L8–23, L77–105, L107–121, L191–265, L362–408, L442–465, L666–753 | 本轮 |
| **developer__observations.mdx** | 观察＝从多条事实归并出的、带证据和计数的信念；矛盾不覆盖而是记演化；按 tag scope 分层 | **能抄（"派生记忆"的官方形状）** | L7, L15–28, L43–51, L85–118, L131–163, **L178–184, L213–274** | 本轮 |
| developer__retrieval.md | 四路召回的完整打分流水线：并行→RRF(k=60,等权)→重排(前 300)→recency/temporal/proof 乘性 boost→截断 | 能抄 | L22, L52–64, L216–236, L256, L268–269, L283–296, L351–387 | 子代理 |
| developer__api__recall.mdx | recall 全参数与返回形状；`temporal_window` 只排序不过滤；`min_scores` 不是结果谓词 | **冲突（不能当范围闸门/阈值）** | L115, L256–262, L325–327, L774–813, L865–874 | 子代理 |
| developer__retain.md | retain 把原文抽成结构化事实，按"谁在说"分 experience/world，建实体图与双时间轴 | **冲突（抽取会碎掉条文原文）** | L50–64, L176–260, L278–320, L339–363 | 子代理 |
| developer__api__retain.mdx | 写入端参数与投递形态：幂等 document_id、update_mode、tags、observation_scopes、批量接口 | 能抄 | L161–171, L230–249, L432–436, L653–665 | 子代理 |
| developer__reflect.mdx | reflect＝最多 10 轮、持工具的智能体循环；disposition 三性格 + directives 硬规则；按心智模型→观察→原始事实分层取证 | **冲突（指令层我们已有且更宽）** | L17–53, L92–191, L228–274 | 子代理 |
| developer__api__reflect.mdx | reflect 参数/返回/失败语义；`max_tokens` 只管末答案；取不到证据直接 500 | 冲突 | L62–103, L212–255, L343–430, L464–478 | 子代理 |
| developer__mental-models.mdx | 心智模型＝你定问题、后台写答案、常驻文档；只在自身范围内记忆变了才重写 | 能抄（与我们手写页重叠） | L5–9, L17–31, L37–41, L47–49, L53–61 | 子代理 |
| developer__api__mental-models.mdx | 心智模型全套接口 + 触发器 + full/delta + 过期判定 + dry-run + 变更历史 | 能抄（全按 bank 隔离） | L21–44, L107–114, L186–248, L279–337, L499–513, L581–594, L990–1018 | 子代理 |
| developer__models.mdx | 模型清单：LLM 供应商/向量/重排；**向量维度一旦存数据就锁死** | 能抄／**冲突（换模型＝整机蓝绿）** | L8–12, L20–24, L55, L86, L99–171, L883–906, **L942–944**, L1027–1108 | 子代理 |
| developer__api__memories.mdx | 记忆单元接口：列表/取/历史/改写/作废；「错了/过期了/重复了」各用哪个动作 | 能抄（我们完全没有的订正面） | L16–45, L172–198, L246–257, L320–327, L411–419 | 子代理 |
| developer__index.mdx | 概览：三类记忆 + **TEMPR** 四路检索 + 观察整合；mission/directives/disposition 只作用于 reflect | 能抄 | L10, **L42–53**, L55–76 | 子代理 |
| developer__development.md | 贡献者本地开发环境（Python 3.11+、uv、Docker 起 PG、pytest） | 无关 | L8–11, L24–34, L62–73 | 子代理 |
| developer__services.md | API/worker/控制台三件套，何时拆独立 worker | 无关（我们无 daemon 纪律） | L7, L23–25, L37–42, L55–59 | 子代理 |
| **developer__admin-cli.md** | 直连 PG 的运维 CLI；**`repair-bank` 补每库向量索引**；**换嵌入模型只能整机蓝绿** | **能抄（两条运维判据）** | **L74–93**, L146–156, L229, **L459–478**, L483–485 | 子代理 |
| developer__installation.md | 部署方式与硬件；含 Windows 原生安装与"国内网络"配方 | 能抄（Windows 原生） | L12–21, L38, L56–62, L307–321, L364–388 | 子代理 |
| developer__extensions.md | 四类服务端扩展点：租户(按 PG schema 隔离)/自定义端点/校验审计钩子/MCP 工具注册 | 能抄 | L10–19, L31–39, L43–85, L206–208, L294–342 | 子代理 |
| developer__memory-defense__index.md | 按库开关的 45 条正则脱敏（redact/block），命中记审计+发 webhook，**不回溯已存记忆** | 能抄 | L4, L8–21, L36–50, L136–141 | 子代理 |
| developer__api__quickstart.mdx | 60 秒上手，主体是安装样板 | 无关 | L24–34, L52–63, L177–183 | 子代理 |
| developer__api__main-methods.mdx | retain/recall/reflect 三法四语言对照 | 能抄（参数面） | L120–153, L165–181, L299–306 | 子代理 |
| developer__api__webhooks.mdx | 按库注册 webhook：6 次指数退避、至少一次投递需按 operation_id 去重、HMAC V2 | 能抄 | L8–22, L29–40, **L141**, L145–147, L168–181 | 子代理 |
| developer__api__operations.mdx | 单一 async_operations 队列的六类操作、生命周期、progress、worker 槽跨库轮转 | 能抄 | L4, L24, L30–40, L64–93, L259–267, L465–469 | 子代理 |
| developer__api__bank-templates.mdx | JSON 清单一次导入/导出整库配置+心智模型+指令，可复制成新库 | **能抄（每项目一份模板）** | L18–24, L30–46, L99–136, L283–288, L496–505 | 子代理 |
| developer__api__documents.mdx | 文档是保留内容的来源容器；改 tags 会作废派生观察并**重排同源记忆** | 能抄（改标签的连带代价） | L22–38, L243–247, **L331–337**, L396–398, L507–521 | 子代理 |
| sdks__cli.mdx | CLI 全量参考；含 knowledge-base 命令与 audit list | 能抄 | L184–239, L311–408 | 子代理 |
| sdks__embed.md | 零配置本地守护进程封装，自述不适合生产/多租户 | 无关 | L12–26, L149–151, L286–292 | 子代理 |
| sdks__go.md | OpenAPI 生成的 Go 客户端 | 无关 | L4–15, L54–63 | 子代理 |
| sdks__hindsight-all-npm.md | Node 侧托管封装：起 daemon、轮询 `/health` | 无关 | L4–8, L12–23, L61–74 | 子代理 |
| sdks__hindsight-all.md | Python 侧同上，profile = 独立 pg0 实例 | 无关 | L4–6, L12–17, L79–89 | 子代理 |
| sdks__nodejs.mdx | TS/JS 客户端；`getVersion().features.mcp` 探测服务端能力 | 能抄 | L4, L22–41, L57–91 | 子代理 |
| sdks__python.mdx | Python 客户端；同样有 `features.mcp` 探测 | 能抄 | L4–6, L56, L60–71, L110–152 | 子代理 |

### §8.1 承重的逐条摘录（我自己读的，附原话要点）

**多语言（最关键的一篇）**
- `L134`："Hindsight's multilingual support depends **entirely on your LLM's language capabilities**" —— 多语言不是靠分词库，是靠提示词。
- `L156`/`L171`：默认嵌入 `BAAI/bge-small-en-v1.5`、默认重排 `cross-encoder/ms-marco-MiniLM-L-6-v2`，**都是英文专用**。
- `L186`："BM25 is inherently within-language… The default `native` backend uses PostgreSQL's English dictionary, which produces poor results for non-English content (**and no useful tokenization at all for Chinese / Japanese / Korean**, which lack whitespace word boundaries)."
- `L197`：native 后端要支持中文得挂第三方词典 `zhparser`；`L200` pgroonga 开箱支持 CJK（`TokenBigram` + NFKC150）；`L201` pg_search 支持 `chinese_compatible`/`jieba`/`chinese_lindera`。
- 🔴 `L214–216`（note）：**"The `pgroonga` and `pg_search` backends depend on PostgreSQL extensions that are **not** bundled with the embedded `pg0` database Hindsight uses when `HINDSIGHT_API_DATABASE_URL` is unset. On that default single-container setup neither backend can be enabled."**
- `L237`：混语 bank 的推荐配方 = pgroonga + 不设 `LLM_OUTPUT_LANGUAGE`。
- `L246`：observation 的语言**按条**决定（不是按批），一条 observation 由多语事实构成时**多数语言胜出**。

**检索开关（configuration）**
- `L1648`："Recall runs four retrieval arms (semantic, BM25, graph, temporal) and then reranks the fused candidates with a cross-encoder."
- `L1659`：`HINDSIGHT_API_ENABLE_TEXT_SEARCH=false` → **纯向量**，"the arm is left out of the query entirely rather than filtered to nothing"。
- `L1671–1702`："Pairing with the retain side: plain-retrieval ('RAG') banks" —— `retain_extraction_mode: chunks` + `enable_observations: false` + 关掉时间/图/重排 = "chunks in, hybrid search out, **no LLM on either path**"。

**TypeSafe / Jev 重排器（configuration）** ← 我们自己的东西被官方收编了
- `L1381–1385`：`# TypeSafe - relevance judged by a typed-decision model (Jev), not a /rerank endpoint`；
  `HINDSIGHT_API_RERANKER_TYPESAFE_MODEL=jev-latest`、`..._PRUNE_CANDIDATES=true`。
- `L1430`："TypeSafe is not a `/rerank` endpoint. It evaluates typed *questions* against a *state*, and this provider asks two of them."
- `L1433–1438`：**Rank** —— "A Choice returns a probability for every option… one call, however many candidates"，厂商自报 **LoCoMo 200 题 recall@1 0.94 vs 逐条调用 0.87，调用次数只有 1/30**（⚠ **厂商自报，无测试条件**）。
- `L1440`：Choice 上限 255 个选项，超了分轮排名、轮间概率不可直接拼接。
- `L1444–1456`：**Cut** —— 第二个问题问"相关性延伸到第几名"，`PRUNE_CANDIDATES` 落水后的直接砍掉；**没有"全都不相关"档**，所以至少留一条。用 Score 不用 Choice+空选项，是因为 "35 of 200 questions came back completely empty"。
- `L1462`：⚠ **"Scores are positions, not confidences"** —— 0.7 是"这堆里最好"，不是"相关"；跨池不可比；返回的是**名次**不是分数，砍掉的一律给 `0.0`。

**bank 隔离与 directives（api/memory-banks）**
- `L30`："Banks are **completely isolated** from each other — memories stored in one bank are not visible to another."
- `L34–38`：**只有写会建库**；读不存在的库返回 `404` 而不是空结果。
- `L148–231`：**`entity_labels` = 受控词表**，`key:value` 标签在 retain 时抽成实体；因为标签即实体，**它会自动把记忆连进知识图谱、同时改善语义与 BM25 检索**，`tag: true` 时还能用 `tags`/`tags_match` 过滤。类型有 `value` / `multi-values` / `text` / `multi-text` / `map`（嵌套 `key:field:value`）。
- `L215–216`：`multi-text` 的例子——"we deploy to EKS — the team usually just says k8s, or kube" ⇒ 抽出 `name:kubernetes` / `name:k8s` / `name:kube` 三个实体，**别名归一**。
- `L713–737`：directives 是 reflect 期间的**硬规则**；`L718` **"Directives only affect the `reflect` operation"**；无标签的永远生效，带标签的只在请求带匹配标签时生效，`apply_all_directives: true` 可强制全量。
- `L911–916`：directives（硬规则，可被拒答）vs disposition（软影响，只塑形）——"Directives vs Disposition"。
- `L920–932`：bank 搬运三个开关；`L930` **心智模型与知识页算"数据"不算"配置"**；`L932` **embeddings 与库内 id 永不携带**，落地端用自己的模型重嵌。

**控制面与配置分层（configuration）**
- `L2805`：**Global(env) → Tenant → Bank** 三级。
- `L2809–2829`：**类型安全访问**——从全局 config 读 bank 可配字段直接抛 `ConfigFieldAccessError`，强制走 `ConfigResolver.resolve_full_config(bank_id, ...)`。L2841 自称"making it impossible to make this mistake at compile/development time"。
- `L2847–2859`：字段分三类——可配（行为）／**凭据类永不暴露**（`*_api_key`、`*_base_url`）／静态（`database_url`、`port`、`llm_provider`、`llm_model`、性能调优）。
- `L2885–2899`：`HINDSIGHT_API_DEFAULT_BANK_TEMPLATE` 一次套到每个新库，且**不会在后续访问时重套**，所以不会盖掉用户的显式覆盖。

**观测（configuration / monitoring）**
- `L2271`：`HINDSIGHT_API_ENABLE_OBSERVATIONS` 默认 `true`。
- `L2292`：`HINDSIGHT_API_CONSOLIDATION_STRATEGIES` —— **"what lets a single bank be federated across user / team / company tag scopes: each scope is consolidated by its own LLM call, so each can follow a different brief"**。
- `L2294–2322`："Disabling a sweep stops scheduling, not execution" —— 把间隔调 0 **不会**让已排队的活停下来，要停得 `HINDSIGHT_API_WORKER_ENABLED=false`。
- `L2552`：**审计日志默认关闭**。
- `L2568`：LLM 请求追踪默认开，**只留 1 天**。
- `monitoring L149`：`outcome="no_facts"` = "a document was stored but produced no memories. Those documents are invisible to `recall` and `reflect`… **because the retain itself succeeded**"。
- `monitoring L182–188`：`failed_consolidation` 为 0 **不代表**归并健康——"a bank can look completely healthy while its supersession cleanup does nothing"。

**实体解析对中文的隐患（configuration）**
- `L1863–1873`：两阶段。阶段一用 pg_trgm（阈值 `0.15`）选候选；阶段二加权 ≥ `0.6` 才复用。
- `L1877`：名字相似度用的是 **`difflib.SequenceMatcher` 的字符序列比**，不是 trigram。
- `L1890–1895`：合并前还有一道**逐词一致**检查——"every word of the shorter name has to find a counterpart in the longer one"。⚠ 这条假设**按空格分词**；中文人名/机构名没有空格，这一关对中文近乎失效。
- `L1913–1917`：不想被模糊匹配的（如标准号），官方建议**做成 entity label** 或 `resolve_entities: false`。

### §8.2 configuration.mdx 里与我们直接相关的默认值（逐条，附行号）

| 变量 | 默认 | 我们的实际值 | 判读 |
|---|---|---|---|
| `HINDSIGHT_API_LLM_PROVIDER` / `_MODEL` (L274, L276) | `openai` / **`gpt-5-mini`** | `openai` / `space-bunny-free`（base_url `https://opencode.ai/zen/v1`） | 走的是本机自建端点 |
| `HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL` (L846) | **`BAAI/bge-small-en-v1.5`（英文）** | onnx `intfloat/multilingual-e5-small`，384 维，`query:`/`passage:` 前缀齐全 | ✅ **我们已经比默认好**，是官方文档 L1005/L1017 推荐的多语言档 |
| 默认重排 (multilingual L171) | `cross-encoder/ms-marco-MiniLM-L-6-v2`（英文） | `local` + **`BAAI/bge-reranker-base`** | ✅ 已是中文模型 |
| **重排 provider** (L1381–1385) | — | `local` | ⚠ **TypeSafe/Jev 那条路我们没走**（见 §9.3） |
| `HINDSIGHT_API_TEXT_SEARCH_EXTENSION` (L245) | **`native`** | **未设** | 🔴 见 §9.2 |
| `..._NATIVE_LANGUAGE` (L246) | **`english`** | **未设** | 🔴 见 §9.2 |
| `HINDSIGHT_API_ENABLE_OBSERVATIONS` (L2271) | `true` | **`false`** | 🔴 见 §9.4 |
| `HINDSIGHT_API_AUDIT_LOG_ENABLED` (L2560) | `false` | `false` | ⚠ 我们一条审计都没有 |
| `HINDSIGHT_API_ENABLE_TEXT_SEARCH` (L1659) | `true` | `true`（bank config 实测） | 臂开着，但后端是英文词典（见 §9.2） |
| `HINDSIGHT_API_RERANKER_MAX_CANDIDATES` (L1590) | `300` | 未设 | — |
| `HINDSIGHT_API_SEMANTIC_MIN_SIMILARITY` (L1594) | `0.3` | 未设 | ⚠ 官方 L1609–1613 明说：换嵌入模型后这**五个阈值都要重新标定** |
| `HINDSIGHT_API_ENABLE_BANK_LLM_HEALTH` (L2881) | `false` | 未设 | — |
| `HINDSIGHT_API_ENABLE_BANK_CONFIG_API` (L2880) | `true` | 未设 | — |

### §8.3 官方文档自己的三处内部矛盾 / 一处需要更正旧结论

1. ⚠ **更正上轮 §6 的一处误读**：`developer__oracle.md` **不是**"oracle 基准/500 候选 oracle 结果"，它是 **Oracle Database 23ai 的部署指南**（L2–7：「Hindsight uses PostgreSQL as its default storage backend, but it also runs on **Oracle Database 23ai**」）。上轮 §6 把它列为"与业主那句'500 候选是 oracle 结果'直接相关"是**错的**。该篇与我们的关系是**无关**。
2. **两份 reflect 文档的工具清单互相矛盾**：架构页列的是 `search_mental_models` / `read_mental_models` / `search_observations` / `recall` / `expand` / `done`（reflect.mdx L29–36）；API 页在描述 `trace.tool_calls[].tool` 时写的是 `lookup` / `recall` / `learn` / `expand`（api__reflect.mdx L464）。引用"reflect 会调哪些工具"必须二选一。
3. **`sdks__embed.md` L22 与 admin-cli/storage 的存储模型矛盾**：前者说"每个 bank 有自己的嵌入式 PostgreSQL 库"；后者说一个 PG、一个 schema 装多个 bank、向量维度按 schema 共享（admin-cli L18–23 / L478）。**按后者可信。**
4. **`models.mdx` 里查不到"默认 LLM 是哪家"**：两张表（Supported providers / Provider Default Models）在这个拆分文件里是空的（L20–24、L121–126）。真默认值只在 configuration.mdx L274/L276。

**我抽查过、确认子代理没编的承重条目**（各读原文核对）：
- `admin-cli L76` repair-bank 的"静默少召回"路径 —— 原文逐字核对 ✅
- `admin-cli L459–478` 换嵌入模型＝整机蓝绿 —— 原文逐字核对 ✅
- `models.mdx L942–944` 向量维度锁死 —— 原文逐字核对 ✅
- `index.mdx L42` "Multi-Strategy Retrieval (**TEMPR**)" —— 原文核对，**"TEMPR" 是官方用词，不是子代理的错别字** ✅
- `configuration L274/L276` 默认 `openai` / `gpt-5-mini` —— 原文核对 ✅

---

## §9 本机实测对照（2026-09-28，这是本轮最有价值的产出）

取证方式：读 `C:\Users\Zegel\.hindsight\profiles\dsh.env` 的生效项 + 打 `http://127.0.0.1:8888` 的 `/stats`、`/knowledge-base/tree`、`/config`。
bank = `coding-agent::zcode`。

### §9.1 基线数字（今天实测，与上轮 §2 有出入，以本轮为准）

| 指标 | 上轮 §2 | 本轮实测 |
|---|---|---|
| 事实条数 | 114,970 | **118,653** |
| 边 | 5,337,849 | **5,698,505** |
| 文档 | 3,529 | 3,531 |
| `total_observations` | 0 | **0** |
| `last_consolidated_at` | `null` | **`null`** |
| `pending_consolidation` | 114,970 | **118,653（= 全部，一条没归并）** |
| 失败作业 | — | 4 |

### §9.2 🔴 中文分词：我们四路里有一路是死的

- 我们**没有设** `HINDSIGHT_API_TEXT_SEARCH_EXTENSION`，也**没有设** `..._NATIVE_LANGUAGE` ⇒ 取默认 **`native` + `english` 词典**（configuration L245–246）。
- 官方对这件事的原话（multilingual L186）：`native` 用 PG 英文词典，"**no useful tokenization at all for Chinese / Japanese / Korean**"。
- 中文要真正可用的 BM25，只有两条官方路：`pgroonga`（multilingual L200）或 `pg_search` + `jieba`/`chinese_compatible`（L201）。
- 🔴 **但这两条我们现在都用不了**：multilingual **L214–216** 明确写着 pgroonga / pg_search 依赖的扩展**不在 pg0 内嵌 PG 里**，默认单容器部署下**两个都开不了**，必须把 `HINDSIGHT_API_DATABASE_URL` 指向装了扩展的**外部 PostgreSQL**。
- ⇒ **结论**：在"不引守护进程"这条硬约束下，**官方的中文 BM25 我们拿不到**。这不是我们没配好，是官方没给 pg0 形态的解法。
  唯一在现有形态下能做的补救是 `HINDSIGHT_API_ENABLE_TEXT_SEARCH=false`（configuration L1659，关掉后是纯向量召回，`search_vector` 索引仍维护，可随时切回）——但那等于承认我们只有三路。

### §9.3 嵌入与重排：我们已经比官方默认好（这条是好消息，别改）

- 实测生效：`EMBEDDINGS_PROVIDER=onnx` + `intfloat/multilingual-e5-small` + 384 维 + `query:`/`passage:` 前缀 + `NORMALIZE=true`。
  这正是 configuration L1005/L1017 列出的**多语言 E5 档**，前缀也按 L857–858 的要求配对了。
- 重排实测：`provider=local` + `BAAI/bge-reranker-base`（中文模型），不是官方的 `ms-marco`（英文）。
- ⇒ **不要因为"官方默认是英文模型"就去换**——我们已经换过了。⚠ 但 configuration L1609–1613 提醒：嵌入模型换了之后，**五个相似度阈值都要重新标定**（我们全用默认 0.3/0.3/0.1/0.7/`0.97`），这是一个未做的欠账。
- ⚠ **别碰嵌入模型**：models.mdx L942–944「Once memories are stored, you cannot change dimensions without losing data」＋ admin-cli L459–478 整机蓝绿 ⇒ 想换 BGE-M3（1024 维）的代价是**3,531 篇重灌 + 换实例**。
- 🔴 **一条真发现**：configuration **L1381–1385** 有 **`HINDSIGHT_API_RERANKER_TYPESAFE_MODEL=jev-latest`** 与 `..._PRUNE_CANDIDATES=true` —— **官方把 Jev（TypeSafe System One）做成了重排 provider**。它不是 `/rerank` 端点，而是"拿**带类型的问题**问一个**状态**"：一次 Choice 把所有候选当选项读出排序（L1433–1438），可选第二个问题问"相关性到第几名"来砍掉后面（L1444–1447）。
  ⚠ **但**：L1462 明写 **"Scores are positions, not confidences"** —— 0.7 只表示"这堆里最好"，跨池不可比；对我们做**绝对置信度判据**（如"≥0.9 才清"）**不能用**。
  ⇒ 我们在 `docs` 里那条"Jev ≥0.9 才清"的判据，**不能用 Hindsight 的 typesafe 重排分数来喂**，那是两个不同的量纲。

### §9.4 🔴 归并被关掉了 ⇒ 8 张知识页**从 2026-09-25 起就不会再更新**

实测链条（每一步都有据）：
1. `HINDSIGHT_API_ENABLE_OBSERVATIONS=false`（env 级；`/config` 显示 `enable_observations: false`，且 `overrides: {}` ⇒ 来自 env，不是 bank 覆盖）。
2. 官方默认是 `true`（configuration L2271）⇒ **是我们这一侧关掉的**。
3. 观察层为空（`total_observations: 0`），`pending_consolidation` = 118,653 = 全部事实，一条没归并，`last_consolidated_at: null`。
4. 知识页的默认 trigger 是 `{"mode":"delta","fact_types":["observation"],"exclude_mental_models":true,"refresh_after_consolidation":true}`（api/knowledge-pages L244–251）。
   ⇒ 页面只读**观察**；观察不产 ⇒ 永不 stale ⇒ 永不刷新。
5. **实测吻合**：8 张页面 `is_stale` 全为 `false`，页面 `timestamp` 停在 **2026-09-25T13:51:17Z**，而 `last_memory_write_at` 是 **2026-09-28T18:22**。中间三天写进去的事实，页面一个字都没带上。

⇒ 这是"开了功能没用"的第二次实锤，位置很具体：**不是知识页坏了，是它的上游被关了**。
⚠ 顺带：即使开了归并，11.8 万条积压一次跑完的 LLM 花费官方**没有给数**（性能页那几个数字是**厂商自报，无测试条件**），要先小批量试。

### §9.5 审计是空的

- `audit_log_enabled: false`（configuration L2552 默认就是 `false`）⇒ `/audit-logs` 恒返回 `{"total":0}`。
- 但 **`HINDSIGHT_API_AUDIT_LOG_ENABLED` 是分层的、可按 bank 开，且按 bank 改立即生效不用重启**（L2554）⇒ 这是**零重启成本**就能补上的一格。
- `llm_requests` 默认开、只留 1 天（L2568/L2576）⇒ 想知道"上周花了多少"是查不到的，得先把 retention 提上去。

### §9.6 实体解析对中文有结构性隐患（未验证，只是读出来的风险）

- configuration L1890–1895 那道"逐词一致"检查假设**按空格分词**；中文人名/机构名无空格 ⇒ 这一关对中文近乎失效。
- 阶段一的 trigram 阈值 `0.15`、阶段二的 `0.6`，都是按英文名调的。
- 官方给的出路（L1913–1917）：**标准号这类绝不能被模糊匹配的东西，做成 `entity_labels` 的 `value` 枚举，或 `resolve_entities: false` 自己传。**
- ⚠ **未做验证**：我没有在真机上量过中文实体的误并率。这条只是读文档读出来的风险，不是实测结论。

### §9.7 两条运维判据（多库部署下必查）

- `hindsight-admin repair-bank --dry-run`（admin-cli L74–93）：一个库如果不是走建库时那条正常路径被填充的（逻辑恢复/跨版本升级/换向量后端），它永远拿不到按 `(bank, fact_type)` 建的局部索引，库内 recall **静默退化成"全局索引 + 事后过滤"，既更慢又会少召回**。我们 `coding-agent::<gitProject>` 是多库形态 ⇒ 定期跑一次 `--dry-run`。
- 我们目前**跑在 pg0 内嵌 PG 上**（storage L48–71 / profile `dsh.env`），所以上面那条"换嵌入模型=整机蓝绿"目前**不是我们的阻塞**——我们不会换。真正卡住我们的是 §9.2（BM25 后端）。

---

## §10 回答业主：他的结构真把"知识库 + skill"统一起来了吗？我们没有，真的没价值吗

> 原话：「我感觉他这个结构是把知识库、skill 统一起来管理了，我们现在没有，真的没有价值吗」

### §10.0 先纠一个前提（这条得说清，否则后面全是错的）

**他统一了一半，另一半他也没有。**

- **"知识库"这一半：他说对了，而且比我们自己做的强。**
  Hindsight 里"知识库"就是**活文档**：给它一个问题，它自己写、自己改、自己判断过时了（L12–21 knowledge-pages）；
  还能整棵树**映射成磁盘上真实的 markdown 文件**（L38–41），`ls`/`grep`/`rg`/编辑器/agent 文件工具直接用；
  还能**整页混合检索**（BM25+向量 RRF，不过重排，快到能当 agent 的第一个动作）（api/knowledge-pages L390）。
  我们现在是**手写**这 8 张页（实测 `timestamp` 停在 2026-09-25，之后没动过）。
- **"skill"这一半：官方文档里根本没有 skill 这个东西。**
  我在 938 KB 的整站正文里搜 `skill(s)`，只有 11 处命中：10 处是"preferences, **skills**, relationships"这种举例词，1 处是 GitHub Copilot 自带的 skill。
  **Hindsight 没有技能库、没有"按需调用的做法文档"这个概念。**
  它最接近 skill 的，是 **directives**（硬规则，注入提示词）——但那只是"必须遵守的规矩"，不是"怎么做事的流程"。

⇒ 所以正确的说法是：**他把"记忆 + 活文档知识库 + 硬规则"统一了，没有统一"技能"。** 业主的直觉对了一半，但"我们现在没有"这个前提要改：我们有 `AGENTS.md` 和技能目录，官方没有。

---

### §10.1 ① 我们自研的、应该停下来改用官方的

| 该停的 | 官方现成的 | 前提/代价（不能只说好处） |
|---|---|---|
| **常驻答案层（那 8 张页）** | knowledge pages：自带问题→答案、delta 增量改写、stale 判定、磁盘镜像、整页检索 | 🔴 **先决条件是开归并**（§9.4）。现在这 8 张页是死的，开归并前它们不会自己更新 |
| **"再加一路检索"的打算** | 它已经是**四路并行 + RRF + cross-encoder 重排**（configuration L1648），不是单路 | 无。我们那条"它是单路"的判断是错的（§1.2 已更正，此处再确认） |
| **记忆的订正/去重/作废** | memories 的 rewrite / invalidate / curate，retain 幂等，`retain_extraction_mode` 五档 | 无。我们这一面**基本是空的**，等于有 |
| **审计与成本台账** | `/audit-logs`、`/stats`、`/llm-requests`、Prometheus 全套（monitoring 全文） | 审计默认关（L2552），但可按 bank 开且**立即生效不用重启**（L2554）——零成本 |
| **"每项目一份记忆配置"** | bank template（JSON 清单，一次套到每个新库、且不盖用户覆盖，L2885–2899） | 无 |
| **入库即脱敏** | memory defense：45 条正则，redact/block，命中记审计+发 webhook | 官方 L136–141 明说**不回溯已存记忆** ⇒ 只对以后新写的生效 |
| **入库即打业务标签** | `entity_labels` 受控词表（受控枚举/自由文本/多别名/嵌套 map），标签即实体 ⇒ 自动连图谱 + 改善语义与 BM25（api/memory-banks L148–231） | 无。这是我们"六路检索"里 modality / legal_element / behavior_scope 三路**最像的现成件** |

### §10.2 ② 哪些**不是**造轮子（官方也没解决）

这七条是我们自研的，**官方确实没有**，不是我们懒：

1. **法规条款级的证据链**（标准号 + 条款号 + 可点原文 + 效力状态）。
   Hindsight 连"效力"这个概念都没有。更关键的是它**结构性地相反**：knowledge-pages L63 明写
   "when a team decided X and later amended it to Y, **the page says Y — and can say why — instead of preserving both**"。
   ⇒ **它的整个设计就是要抹平"两版并存"，而我们的业务核心恰恰是"作废/被代替/仅供参考"必须原样留着、必须能同时看到两版。** 这条不是我们多做，是我们**不能**用它的。
2. **精确条款命中**。它四路全是语义/BM25/图/时间，没有"标准号+条款号"这种结构化等值通道。我们的 exact 路是必要的。
3. **材料评审硬门**（approved / pending 才进结论）、**来源可信度分级**（T0–T4）。官方没有。
4. **中文 BM25**。见 §9.2：官方对 CJK 的 BM25 全部依赖第三方 PG 扩展，而扩展不在 pg0 里 ⇒ **在"不引守护进程"这条硬约束下，官方没给我们解法。**
5. **跨项目派生记忆**。见 §10.3，官方没有跨 bank 的任何东西。
6. **指令层比它宽**。官方 directives L718 明写 **"Directives only affect the `reflect` operation"** —— 只管 reflect，不管 recall，也不管 agent 自己的每一轮。我们的"每轮必读 AGENTS.md"它给不了。
7. **中文实体解析**（§9.6）——它那套阈值和"逐词一致"都是按英文设计的，我们没做中文适配。

### §10.3 ③「一套库装全部资料 + 跨项目派生记忆」与官方 bank 隔离怎么解

**先摆事实**（api/memory-banks L30）："Banks are **completely isolated** from each other — memories stored in one bank are not visible to another."
我在整站正文里搜过跨库查询：**没有**。官方给的是**搬**（document-transfer / clone / export-import，L920–932、L4746），不是**读**。

⇒ **冲突是真的，而且不是配置问题，是模型问题。**

**官方给出的解法形状（这是本轮最有价值的一条）**：
它的"跨范围派生"**不做在 bank 这一层，做在 bank 内部的 tag scope 层**。
observations L213–233 举的例子：一条事实打了 `user:dana` / `team:exec` / `company:acme` 三个标签，
三个 scope **各跑各的归并**，然后 `consolidation_strategies` 给 `company:*` 配一条更概括的 mission
（"只记行业级趋势，永远不要点名具体公司、金额、融资阶段"），
结果 Dana 那边保留"Acme 租了 4000 张卡的 3 年合同"，公司那边只得到"企业正在租 GPU 集群跑开放权重模型"。
configuration L2292 把它总结成一句：**"what lets a single bank be federated across user / team / company tag scopes: each scope is consolidated by its own LLM call, so each can follow a different brief."**

**⇒ 落到我们身上，是这样解的：**

- **不要**改成"一个全局 bank + 跨 bank 读"。官方没这个能力，我们自己造就是造轮子。
- **要**改成：**一个 bank 装全部资料，用 tag scope 分层。**
  - 资料层 = 事实（`world`/`experience`），带 `来源层级` / `效力档` / `号段` / `项目` 标签；
  - 派生层 = **另一个 scope 的 observations**，用更概括的 `observations_mission` 写出来的。
    **"跨项目派生记忆"＝ 公司/全局 scope 的 observation，不是另一个 bank 的记忆。**
- 这跟我们现在 `coding-agent::<gitProject>` 一项目一库的策略**正面冲突**：那是"多 bank"，上面要的是"单 bank + scope"。
  🔴 **但换过去有硬代价**：(a) bank 隔离没了，隔离要改用 tag 自己做；
  (b) `entity_labels` 那套受控词表要一次性把 11.8 万条历史事实的标签补齐，否则按 scope 分层会读空
  （api/mental-models L996–1018 明说：标签不匹配的模型刷新回来是 "I cannot find any information"）；
  (c) 归并得先开，且 11.8 万条积压的花费官方没给数。
- ⇒ **诚实的建议**：现在**不要**动库结构。先把两个零成本/低成本的前置补上（审计按 bank 打开；把 BM25 那路的真相定下来），
  拿这些结论去决定要不要动结构。**在没有实测过归并成本之前改库结构，是在拿唯一一份真数据赌。**

### §10.4 ④ 业主那句「他发现自己需要这个过程，其实就是一个检索的过程」——官方怎么回的

**原话在 `knowledge-pages L49–51`**（本轮已逐字复核）：

> "Pages are searchable at the **document level**: a query returns whole pages, ranked, with snippets. It combines full-text and semantic matching, fused server-side, with **no reranking step** — fast enough to be **the first thing an agent reaches for**.
>
> That last part matters. **Search is a tool an agent *chooses* to call, visible in the transcript, rather than content pushed into its context on every turn. Retrieval the agent asked for informs what it's doing; retrieval it didn't ask for tends to derail it.**"

**展开（这是他原话的直接回答，不是我的转述）：**

1. **他认了，而且把这句话写成了设计理由。** 检索是"agent 自己决定要不要调的一个工具，过程留在 transcript 里看得见"，**不是每轮硬塞进上下文的东西**。他给的理由是后半句：**没请自来的检索会把 agent 带偏。**
2. **他据此把检索拆成了两个入口：**
   - `knowledge-base/search`（api/knowledge-pages L388–452）：**文档级**——整页返回 + 摘要，BM25+向量 RRF，**不过重排**（所以快），`limit` 默认 10。L390 原话就是"快到能当 agent 的第一个动作"。
   - `recall`（api/recall）：**事实级**——查单条记忆。
   L53 把分工讲死："Use page search to **pick a document**; use recall for **a specific fact**."
3. **它和我们 AGENTS.md 里那条纪律是同一个判断的两面。** 我们写的是"工具目录越精简、每个工具的说明越像动词，模型越可能主动调它"；官方写的是"把检索做成**便宜到可以随手调**的入口，模型就会自己调"。**殊途同归：都是把成本压到不值得犹豫，而不是靠提示词去劝模型调。**
4. **对我们的落点（这条值得抄形态，不是抄实现）：**
   我们的 `ks_answer` 是**不问自来的检索**——每轮都在跑三段式检索 + 一次 LLM。
   官方的做法是：把"我要一份现成的答案"做成一个**极便宜、整页返回、不过重排**的入口，让模型自己决定要不要调；
   重推理那条路另开一个门。
   ⇒ **可以抄的是这个切分形态，不是把我们的检索换掉。**

---

## §11 本轮核过、但仍然**没有**核的（不许当已核）

- 官方规模数字（`10-50ms @ 100K+`、`millions of facts per bank`、TypeSafe 的 LoCoMo recall@1 0.94、
  批量接口省 50%、Bedrock flex 省 50%）：**全部是厂商自报，无测试条件、无硬件说明、无"多少条↔多少延迟"对应**。
- 11.8 万条积压归并一次跑完要多少钱、要多久：官方**没有给数**。
- pgroonga / pg_search 在中文上的**实测**效果：官方只有"支持"的说法（**厂商自报**），没有基准。
- `repair-bank --dry-run` 在我们这个 pg0 实例上跑出来是什么：我**没有跑**（只读研究）。
- 中文实体的误并率（§9.6）：**只是读文档读出来的风险，未实测**。
- Control Plane（官方 Web UI）能不能接中文界面：未核，与本项目决策无关。
- `HINDSIGHT_API_ENABLE_TEXT_SEARCH=false` 之后我们的召回会掉多少：未实测。

---

## §12 更正 §5：那份二手材料，**我第一轮判错了两处**（2026-09-28 第三轮）

§5 当时的结论是「**方向对、细节错**」，并点名两条"错"：

> ❌ 错的：`retain` 单次请求**没有** `context` 参数（官方 `RetainRequest` 只有 `items`/`async`/`document_tags`/`operation_id`）；
> **`extraction_mode`/`concise`/`verbose` 整个不存在**（整份 spec 0 次命中）。

### §12.1 核完的结论：**这两条"错"是我自己核错了，不是材料错**

在一手件 `llms-full.txt`（938,683 B，2026-09-28T19:18:34Z 生成）里机械计数：

| 检索串 | 命中 | §5 的说法 | 实情 |
|---|---|---|---|
| `retain_extraction_mode` | **19 次** | 「整个不存在」 | ❌ 存在 |
| `concise` | **19 次** | 「整个不存在」 | ❌ 存在（`retain_extraction_mode` 的枚举值之一） |
| `verbose` | **19 次** | 「整个不存在」 | ❌ 存在（同上） |
| `### context` | **2 次** | 「retain 没有 context 参数」 | ❌ 存在，是**正式参数小节** |
| `Category for the memory` | **2 次** | — | 存在（MCP + SDK） |

**逐条对照一手件：**

1. **`context` 确实是 REST retain 的正式参数**，不是 SDK 才有。`api/retain.mdx` **L173–177** 有独立小节 `### context`，原话：
   > "A short label describing the source or situation… **It is injected directly into the LLM prompt, so it actively shapes how facts are extracted.** The same sentence can mean something very different depending on context: 'the project was terminated' in a `'performance review'` context versus a `'product roadmap'` context produces different memories."
   ⇒ **那份材料第 323 行几乎是逐字转述这一段**（连"绩效评估 vs 产品路线图"这个例子都一样）。**材料引对了，是我的核法错了。**

2. **`concise` / `verbose` 确实存在**，是 `retain_extraction_mode` 的枚举值。`api/memory-banks.mdx` **L118–128** 列了五档：`concise`（默认）/ `verbose` / `custom` / `verbatim` / `chunks`；`mcp-server.md` **L632** 重列一次。

⇒ **§5 的标题结论「材料方向对、细节错」不成立。材料在我点名的两条"细节"上是对的。**

### §12.2 §5 的证据已经不在机器上，无法复验

§5 写的依据是「整份 spec 0 次命中」，指 `openapi.json`（记为 603,960 B / v0.10.1）。
⚠ **本机现在没有这个文件**：`C:\Users\Zegel\AppData\Local\Temp\hs-docs2\` 下只有 `llms-full.txt`、`llms.txt`、`sitemap.xml` 和 `split\`。
⇒ 那次核验**不可复现**，且它的结论与一手件直接矛盾。

### §12.3 最可能的原因（**假设，未验证**）

§0 记着本文档站是 Docusaurus SPA，`/docs/*` 全返回同一个 22,747 B 的 404 壳、**HTTP 200 但不是正文**。
§5 要在"整份 spec 0 次命中"上得出"字段不存在"，如果当时取到的其实是**壳页或空文件**，"0 命中"就会被读成"字段不存在"。
⚠ **这只是假设**——我没法重跑那次核验（文件已不在）。
但**它与 §0 记的坑是同一类错误**，且本条与 §12.1 的实测结果方向一致，**足以把 §5 那两条判据整体作废**。

### §12.4 仍然成立的部分

§5 点名的另两条**经本轮复核仍然成立**：

- ✅ **bank 级导出/导入/克隆是真的**（`admin-cli L459–478`、`api/memory-banks L920–934`；`import-bank` 的 "Target bank must not exist" 见 `admin-cli L12536`）。
- ✅ **bank 级 `mission` 字段是真的**（`retain_mission` / `reflect_mission` / `observations_mission`，见 `api/memory-banks L107–116 / L280–290` 与 `configuration L2289 / L2372`）。

### §12.5 顺带：那份材料另一处**确实编了**的地方

材料第 17 行称「有一个叫 `reprocess_docs` 的后台任务，**每 15 分钟自动重试**抽取失败的文档」。
🔴 **官方没有这个东西。** 官方有的是**手动一次性**接口
`POST /v1/default/banks/{bank_id}/documents/{document_id}/reprocess`（`api/documents`，见 `llms-full.txt L967`），没有周期性后台重试任务。

### §12.6 这轮的教训（比结论重要）

§12.1 的错误和第一轮 §0 记的错误**是同一类**：**拿"检索没命中"当作"东西不存在"**。
第一次是拿二手材料的关键词去官方文档里找；这次是拿一次 grep 的 0 命中去否定材料。
⇒ **新增纪律**：凡是要说"官方没有 X"，**必须在两个独立一手件上都是 0 命中**才能这么写；
只有一份、或者那份的可信度存疑，**只能写"我没查到"，不能写"不存在"**。

**§5 那两条判据据此作废；该节的读者请以本节为准。**

---

## §13 20 篇实测：`document-transfer` 导入路能不能走（2026-09-29）

> **执行者**：本轮实跑。产物在 `var/tmp/hindsight-probe/`（`var/*` 已被 gitignore）。
> ⚠ **生产库 `coding-agent::zcode` 全程未碰**。导入目标是新建的独立库 `probe-import-20`，可随时删。

### §13.0 先修正一处：实机版本与文档不一致，路径也不一样

| | 文档（`llms-full.txt`） | **实机 v0.10.0** |
|---|---|---|
| 版本 | v0.10.1 | **v0.10.0** |
| 路径数 | 77 | **71** |
| 归档导入端点 | `POST /banks/{id}/transfer/import?mode=merge&document_conflict=replace` | 🔴 **`POST /banks/{id}/document-transfer?on_conflict=replace`** |

⚠ 实机上 `POST /banks/{id}/import` 是 **"Import bank template"**（收 JSON 配置模板），**不是**归档包——按文档的路径打过去得到 404。
⚠ 归档格式本身**通用**：`manifest.json` + `documents/<id>.json`；v0.10.1 的 `source_bank_id` 在实机 spec 里 0 命中，但解析器照样吃。

### §13.1 ✅ 走通了

| 项 | 实测 |
|---|---|
| 样本 | 20 篇真标准（从 `clause_fts` 按条款数 30–400 挑） |
| 事实数 | **7,608** |
| ZIP 大小 | 2,047.6 KB |
| 构建耗时 | 7.5 s（纯本地 SQLite 读 + 打包） |
| **导入端到端** | **140.7 s**（提交 0.5 s + 处理 140 s） |
| **LLM 调用** | **0 次** —— 官方原话 "no LLM call, no re-chunking"（`api/memory-banks.mdx L1094`）实测坐实 |
| 导入结果 | `documents_imported=20, facts_imported=7608, documents_skipped=0, observations_imported=0` |
| 边 | 7,608 条事实 → **578,775 条边**（≈76 边/事实） |

**外推全量**：522,021 条 ÷ 7,608 × 140.7 s ≈ **2.7 小时**（一次性，可后台）。

### §13.2 ✅ 精确命中保住了（最要紧的一条）

靶子：`GB 50208-2011` 第 `C.1.2` 条。

| 查询 | 返回 | 目标在结果里 | top-1 |
|---|---|---|---|
| `GB 50208-2011 第C.1.2条 <正文片段>` | 38 | ✅ | **就是目标条款** |
| `GB 50208-2011 C.1.2` | 22 | ✅ | **就是目标条款** |
| `GB 50208-2011`（裸标准号） | 31 | — | 同标准 1.0.1 条（合理） |

⇒ **条款号 + 标准号这条路能用**，且不需要 Hindsight 提供专门字段（我们把 `standard_no`/`clause_number`/`legal_status` 塞进 `metadata`，条款号进 `context`）。

### §13.3 ✅ 标签硬过滤生效

`tags=["mod:应"]` + `tags_match=all_strict` 取回 43 条，**不匹配标签的 0 条** ⇒ 真硬过滤。
样例返回项 `tags`：`['src:standard', 'st:unknown', 'mod:应']`。

⇒ 🔴 **`st:unknown` 是我脚本的 bug**：我按 `standard_no` 去 `doc_meta` 查 `legal_status`，
而 `clause_fts.standard_no` 与 `doc_meta.standard_no` **86% 写法不一致**（`GB／T` 用全角斜杠 `／`）。
归一化后命中率 **919/6,797 → 6,796/6,797**。

⚠⚠ **这不是 KnowledgeStation 的活缺陷**：KS 23 处连表**全部走 `doc_id`**
（`JOIN doc_meta dm ON dm.doc_id = cr.doc_id`，见 `clause_repo.py:449/560/631`、`hybrid_engine.py:250/328/359` 等），
**没有一处按 `standard_no` 连**。⇒ 只有拿 `standard_no` 连的外部脚本（如本探针）会踩；
**正确连法是 `clause_revision → doc_meta.doc_id`**。

### §13.4 ❌ 延迟 8–26 秒，这才是真正的拦路虎

| 查询 | 生产库 **118,653** 条 | 探针库 **7,608** 条 |
|---|---|---|
| `GB 50208-2011 C.1.2` | 18,629 ms | 20,614 ms |
| `防水工程验收` | 13,264 ms | 9,033 ms |
| `检索金标评测台` | 14,989 ms | 7,522 ms |

同题连跑 3–4 次，**不是首调预热**（20,060 / 25,056 / 20,079 ms 是稳定态抖动）。

**两个方向的读法都要写：**
- ✅ **延迟几乎不随库大小增长**：数据量差 **15.6 倍**，延迟只差 **1.1–2.0 倍**。
  ⇒ 全量灌 52 万条**不会**让召回线性变慢——这与"亿级召回"的直觉相反，是实测支持的。
- ❌ **8–26 秒本身不可用**。官方自称 Recall 100–600 ms（`performance.md L29–33`），
  即便按厂商自报也差 **15–100 倍**（那几个数字是**厂商自报、无测试条件**，见 §4）。

**可疑来源**：`HINDSIGHT_API_RERANKER_PROVIDER=local` + `BAAI/bge-reranker-base`（CPU ONNX）；
官方性能页自己说 Recall 瓶颈就在 CPU 上的 re-ranker。
🔴 **"关掉重排能降到多少"这个实验没跑完**——`PATCH /banks/{id}/config {"enable_reranking": false}` 报错（body 形状/端点未查）。
**这是下一步第一件该做、且该查清的事。**

### §13.5 ⚠ 我们自己的数据有两个坑（不是 Hindsight 的问题）

1. **条款正文被插了空格**：`clause_fts.content_segmented` 平均**每条 53.6 个空格**
   （`"C.1 . 2 地下 防水 水工 工程 …"`）。
   ⇒ **直接喂嵌入会掉质量。** 本探针照原样喂，**§13.2/§13.3 的召回结论因此打了折扣**。
   下一次必须先做去空格 A/B。
2. **六路里两路没有数据**：`subject` 填充率 **0.4%**（2,171/522,021）、
   `behavior_scope_segmented` **0.0%**（**0 行**）、`title` **0.0%**。
   ⇒ 只有 `exact`（标准号+条款号）与 `modality`（**41.3%**）两路真有结构化数据。
   🔴 **本轮此前曾说"模态/主体/适用范围三路都是独立字段"——错，已撤回。**

### §13.6 ❓ 有一项测了但不成立（不算结论）

"大白话"召回（`工地动火要怎么办` / `设备坏了谁负责修`）**返回的全不相关**（top-1 是跌落试验、舱室空调）。
**但这个结果不能作数**：我按"条款数最多"抽的 20 篇落在 GB/T 36416、GB/T 29819、GB 50208 地下防水等
**随机技术领域**，里面本来就没有"动火作业"内容。
⇒ **是样本选错了，不是检索不行。** 要测得按主题挑（消防/施工安全）重做。

### §13.7 本节结论（只说测到的）

| 判据 | 结果 |
|---|---|
| 归档导入路能不能走 | ✅ **能**（路径须按实机改） |
| 要不要花钱 | ✅ **零 LLM 成本** |
| 全量要多久 | **≈ 2.7 小时**（一次性） |
| 精确条款命中保不保得住 | ✅ **保得住**，且排第 1 |
| 标签硬过滤有没有用 | ✅ **有用**，0 条漏过滤 |
| 延迟能不能用 | ❌ **8–26 秒，现在不能用** |
| 全量后会不会更慢 | ✅ **实测不会**（15.6× 数据量，延迟只 1.1–2.0×） |

⇒ **一句话：路通、钱省、精确和标签都保住了；唯一真正卡住的是延迟，而延迟的下一个抓手（关重排）还没测成。**
