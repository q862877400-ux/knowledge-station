# Hindsight 部署：对一份外部 AI 分析报告的事实核查（2026-09-30）

> 核查对象：业主转来的一份 AI 分析报告（下称"该报告"），主题是本机 Hindsight 部署的"记忆变脏"风险。
> 核查方式：**不采信任何一方的叙述**，全部回到一手证据——正在运行的进程、实际安装的源码、实时 API、数据库里的行。
> 核查人：DSH 会话内代理。核查时间：2026-09-30。

---

## 零、核查用到的取证入口（可复现）

| 入口 | 具体值 |
|---|---|
| 运行版本 | `GET http://127.0.0.1:8888/version` → `api_version 0.10.0` |
| 运行源码 | `C:\Users\Zegel\AppData\Local\uv\cache\archive-v0\8Z31yI9uQIvHspI6\Lib\site-packages\hindsight_api\`（由进程 34660 的命令行反查得到） |
| 数据库 | 嵌入式 PG 18.1.0，实例 `hindsight-embed-dsh`，库/用户/口令均 `hindsight`（读 `~/.pg0/instances/hindsight-embed-dsh/instance.json`） |
| API 真实路径 | `GET /openapi.json`（71 条路径） |
| 生效配置 | `GET /v1/default/banks/{bank_id}/config` |
| 本次用到的 SQL | `var/hindsight-audit/factcheck{1..7}.sql` |

---

## 一、核查结论总表

| # | 该报告的说法 | 结论 | 依据 |
|---|---|---|---|
| 1 | 两个探针库未清理，混在生产库里 | **半对** | 库确实在（`probe-import-20` 7,608 / `probe-clean-20` 7,463），但它们是**独立 bank**，不是生产库里的行 |
| 2 | 它们会参与全局统计、可能被召回 | **不成立** | `/stats` 与 `bank_stats_cache` 都是**分库**的；插件的记忆库是按模板定的单库，无遍历所有库的行为 |
| 3 | 抽取模型 schema 静默失败，**正在持续产生垃圾数据** | **机制真实，本地不成立** | 上游 issue #3708 属实；但本机 3,534 篇文档中「有分块却零事实」= **0 篇** |
| 4 | 需要用 issue 的 13% / 85% 零事实率来推断本机 | **不成立** | 本机零事实文档 38 篇，占 1.08%，且全部是未分块的索引/模板类文档，全部集中在 2026-09-19 |
| 5 | `FAIL_ON_EXTRACTION_ERRORS` 是否可配置待查 | **可配置（源码已证）** | `config.py` L1025 / L5015，`memory_engine.py` L4155 |
| 6 | 11.9 万条事实从未归并 | **成立** | `total_observations=0`、`pending_consolidation=119,009`、`last_consolidated_at=null` |
| 7 | 生产库混了国标、历史文献、代码仓库，默认归并会产生跨域垃圾 | **不成立** | 生产库是本仓库自己的记忆（标签全是 `dsh-*`/`harness:dsh`/`source:*`/`knowledge:*`）；且全部 119,038 条事实已是 `observation_scopes="shared"` 单一作用域 |
| 8 | 标签策略完全缺失，正在走向"4 个词毁掉全库" | **不成立** | 实际在用 16 个标签，成体系且有用途 |
| 9 | 把 `TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE` 设为 `chinese` 可能恢复中文 BM25 | **有害，不能做** | 该变量被注入为 `to_tsvector('{lang}'::regconfig, …)`；实例里 30 个 regconfig **无 CJK**，设 `chinese` 会让 BM25 直接报错 |
| 10 | 中文分词是"等于没有"（出自交接说明） | **过强，应更正** | 实测：标点分段级中文**能命中**，只有段内子串不命中 |
| 11 | pgroonga 是唯一 CJK 出路 | **不成立** | 官方另有 ParadeDB `pg_search` 的中文分词器；但两者都**不在本机实例里** |
| 12 | 用 `budget=low` 降低重排延迟 | **机制错误** | 重排预筛上限与检索预算无关（交接说明 §7 已自行收回过）；正确杠杆是 `RERANKER_MAX_CANDIDATES_{LOW,MID,HIGH}` |
| 13 | `REFLECT_LLM_TIMEOUT` 仍为默认 30 秒 | **成立** | 未设该键；源码 `DEFAULT_REFLECT_LLM_TIMEOUT = 30.0` |
| 14 | `OPERATION_RETENTION_DAYS=0`，作业表只涨不删 | **成立** | 未设；默认 0；`async_operations` 现有 **12,499** 行 |
| 15 | 用 `DELETE /banks/...`、`/banks/{id}/documents/list` | **路径错误** | 实机是 `/v1/default/banks/{bank_id}`；文档列表是 `/documents`，**没有** `/documents/list` |
| 16 | 重启后查 `/version` 确认 `FAIL_ON_EXTRACTION_ERRORS` | **方法错误** | `/version` 只报特性开关，不报任意配置项；应查 `/v1/default/banks/{id}/config` |

---

## 二、逐条取证

### 2.1 探针库：在，但没在"污染"

实机 16 个库（`GET /v1/default/banks`）。两个探针库确认存在：

```
probe-clean-20    fact_count 7463   created 2026-09-29T10:06:02+08:00
probe-import-20   fact_count 7608   created 2026-09-29T04:02:15+08:00
```

该报告说"混在生产库里"。事实是：16 个库共用一张 `memory_units` 表，靠 `bank_id` 列区分。**它们是 16 个库中的 2 个，不是生产库内的行。**

该报告说"会参与全局统计、拉低 `/stats`"。事实是 `bank_stats_cache` **每库一行**：

```
bank_id | computed_at | payload keys
coding-agent::zcode | 2026-09-29 18:15:12+00 | bank_id, total_documents, total_observations, pending_consolidation, ...
probe-import-20     | 2026-09-29 03:57:58+00 | bank_id, total_documents, total_observations, pending_consolidation, ...
```

该报告说"如果你的 MCP 客户端存在遍历所有 bank 的行为，它们会直接被召回"。事实是插件按模板锁定单库：

```
~/.hindsight/coding-agent.json → "bankIdTemplate": "coding-agent::{gitProject}"
hindsight_diagnose()           → "bank_id": "coding-agent::zcode"
```

并核对插件产物 `dist/dsh.js`：**没有** `listBanks`、没有 `/banks?` 之类的枚举调用。

**真实代价（该报告没说的那部分）**：两个探针库在共享表上各自持有 3 个 HNSW 偏索引，占 48 个索引中的 6 个。清库会触发索引 DDL。所以"清理"是合理的内务，不是救火。

### 2.2 "schema 静默失败"：机制真实，但在本机不成立

**上游 issue 属实。** 核实到 [Issue #3708 "Retain completes with zero facts when extraction output fails schema validation"](https://github.com/vectorize-io/hindsight/issues/3708) 确实存在，标题与失败模式完全对得上。该报告引用它并非编造。
（该报告引用的 13% / 85% 两个具体数字，GitHub API 限流未能取回正文核对，**标为未核实**。）

**`FAIL_ON_EXTRACTION_ERRORS` 在 v0.10.0 确实存在**，该报告的"待查"可以结案：

```
config.py:1025  ENV_FAIL_ON_EXTRACTION_ERRORS = "HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS"
memory_engine.py:4155  fail_on_errors = get_config().fail_on_extraction_errors
memory_engine.py:4159  "marked failed because HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS is enabled."
```

**但本机数据不支持"正在持续产生垃圾数据"这个判断。** 四条独立证据：

**证据一——生产库零事实文档的分母与分子：**

```
docs=3534  chunks=15953  facts=119038
零事实文档 = 38 篇（1.08%）
```

**证据二——把"抽取出问题"和"压根没抽"分开：**

```
有分块但零事实的文档 = 0 篇
分块数 >=3 但事实数 <=2 的文档 = 0 篇

事实/分块比分布：
  no chunks  38 篇
  ratio 1-3  63 篇
  ratio >=3  3433 篇
```

**没有任何一篇文档的产出比低于 1。** 抽取路径没有静默丢事实。

**证据三——那 38 篇零事实文档是什么：** 全部 `chunks = 0`（从未分块），全部创建于 **2026-09-19 同一天**，内容是一行索引页、GitHub issue 模板、Playwright 期望快照、指向 `AGENTS.md` 的 9 字符符号链接占位。**它们不是"抽了但抽空"，是"内容本身没有可抽的事实"。** 全表 3,534 篇里只有这 38 篇属于此类，且 09-19 之后再没出现过。

**证据四——最近的抽取调用记录（`llm_requests`）：**

```
operation              status   n     with_error
retain                 success  1370  0
refresh_mental_model   success    92  0
reflect                success    76  0
retain                 error      14  14
error 全文：APIConnectionError: Connection error.
```

失败全是**网络连接**，没有一条是 schema/JSON 校验失败。

**证据五——直接对当前模型链做一次真实抽取（`POST /memories/dry-run-extract`，只调用不落库）：**

```
输入：GB 30871-2022 第 5.2.3 条 / 第 5.2.4 条 两条正文
耗时 13.2 秒
输出：facts = 1 条，fact_type=world
     entities = [GB 30871-2022, 作业单位, 相关单位, 危险有害因素辨识, 安全措施]
     usage = input 3077 / output 148 / cached 2996
chunks = [{ fact_count: 1 }]
```

**链是通的。**

**该报告方向性的一处偏差：** 它要求"验证这三个模型是否严格支持 JSON Schema"。事实是本机**根本没有在要求严格 schema**：

```
config.py:1099  DEFAULT_LLM_STRICT_SCHEMA = False     # 默认走"schema 写进提示词"的软路径
dsh.env         未设 HINDSIGHT_API_LLM_STRICT_SCHEMA
```

所以问题不是"模型不支持 schema"，而是"我们本来就用软路径，而软路径实测能出事实"。

**必须写明的证据边界：** `llm_requests` 只保留约 24 小时（实测最早 2026-09-28 19:19 UTC、最新 2026-09-29 18:25 UTC），所以"最近一天没有 schema 失败"这句话只覆盖一天。**覆盖全历史的证据是证据一/二/三**（文档—分块—事实三张表的关系），那部分不受保留期影响。

### 2.3 归并：确实没跑，但该报告担心的机制已经被消掉了

```
bank_stats_cache(coding-agent::zcode):
  pending_consolidation = 119009
  total_observations    = 0
  last_consolidated_at  = null
  failed_consolidation  = 0
```

该报告说"生产库混了国标、历史文献、代码仓库，默认归并会产生跨域的、无意义的 observation"。两点都不成立：

**其一，生产库不是混合库。** `coding-agent::zcode` 是本仓库自己的记忆。它的标签分布是：

```
harness:dsh 118875 | source:upload 80783 | source:chat 38092 | dsh-notes 26945 | dsh-notes-zh 20490
dsh-pkg-readme 9498 | dsh-official-docs 6819 | … | knowledge:feature-work 163
```

最近写入的文档是 DSH 官方文档、会话记录、倡议标记、更正说明。含 GB 标准式样文本的文档只有 **14 / 3,534** 篇。国标语料实际在别处：`dsh-resources`（58 篇）、两个探针库（19 + 11 篇）。

**其二，跨域归并的前提已经被插件取消了。** 插件以 `observationScopes: "shared"` 写入，全部 119,038 条事实实测：

```
observation_scopes | n
"shared"           | 119038
```

即**每库一个全局无标签作用域**，不会按标签切成一堆互不相通的观察集，也不会跨域乱合。该报告建议的"先配 `observations_mission`"仍然是有价值的**质量调优**（该键现在确实是 `null`），但它不是"防止产生垃圾"的前提条件。

另：归并能力本身在本机是好的——5 个旧库 `dsh-*` 里共 **2,389 条 observation**。所以这是开关问题，不是功能问题。

### 2.4 标签：该报告的整节前提不成立

该报告称"你的交接说明里没有提到任何 tags 配置"⇒"你已经在走同一条路（固定标签毁库）"。

"交接说明没写"是真的；"所以标签策略缺失"是**推断**，而事实与推断相反。生产库在用 **16 个**标签，分三条轴：

- 来源轴：`source:upload` / `source:chat`
- 归属轴：`harness:dsh`
- 内容轴：`dsh-notes` / `dsh-notes-zh` / `dsh-pkg-readme` / `dsh-official-docs` / `knowledge:feature-work` …

并且这不是随手打的。插件文档 `README.md` L850-L857 明确：`source:` 与 `harness:` 是插件**保留**命名空间，用于标注"这条记忆是谁写的"，并**据此派生 observation 作用域**。

该报告唯一说对的一点——"不要把'现行有效'这种效力状态打成硬过滤 tag"——与本仓库 `交接说明 §5.2` 早就记下的判断一致，无需改动。

该报告建议改用 Entity Labels：该配置在 v0.10.0 确实存在（`GET …/config` 里 `entity_labels: null`，OpenAPI 有 `LabelGroup-Input`）。但它是可选优化，**不是当前问题的修复**。

### 2.5 中文检索：该报告给的方案会让检索直接坏掉

**该报告的建议：** 设 `HINDSIGHT_API_TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE=chinese`。

**这个变量是怎么用的（源码）：**

```python
# config.py:3797  只校验是不是合法的 PG 标识符
if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", self.text_search_extension_native_language): raise ...

# ops_postgresql.py:58  直接塞进 regconfig
return f"to_tsvector('{config.text_search_extension_native_language}'::regconfig, {combined})"
```

**实例里有哪些 regconfig：**

```
arabic, armenian, basque, catalan, danish, dutch, english, estonian, finnish, french,
german, greek, hindi, hungarian, indonesian, irish, italian, lithuanian, nepali,
norwegian, portuguese, romanian, russian, serbian, simple, spanish, swedish, tamil,
turkish, yiddish        ← 共 30 个，没有任何 CJK
```

**直接试：**

```
select to_tsvector('chinese'::regconfig, '测试');
→ 错误: 文本搜寻配置 "chinese" 不存在
```

**结论：** 设成 `chinese` 不会改善中文，会让 BM25 每条查询都抛错。该报告第 5 节的动作 1 **不能执行**。

**同时，交接说明 §5.1 的"中文关键词检索等于没有"也过强，应更正。** 实测三种情形：

```
作业单位应组织对作业现场进行辨识 @@ to_tsquery(子串 '作业单位')          → f
作业单位应组织对作业现场进行辨识 @@ to_tsquery(整段 '作业单位应组织…辨识') → t
GB 30871-2022 …第5.2.3条：作业前，… @@ to_tsquery('作业前')               → t
```

准确表述是：**默认解析器按标点/非词字符切词，中文只能到"标点分段"这一粒度；段内子串查不到。** 既不是"没有"，也不是"配个语言就好"。

**该报告说"pgroonga 是唯一出路"——不成立。** 官方 `TEXT_SEARCH_EXTENSION_PG_SEARCH_TOKENIZER` 支持 `chinese_compatible / jieba / chinese_lindera`。但检查本机实例：

```
pg_available_extensions 共 62 个；已安装 3 个（pg_trgm, plpgsql, vector）
pgroonga / pg_search / zhparser / vchord / pg_textsearch —— 均不可用
```

所以无论走 pgroonga 还是 pg_search，都**必须换外部 PostgreSQL**。这与交接说明 §5.1 的结论一致，该报告"(换外部 PG 也解决不了)"这一否定是对的，但它给的理由（"只有 Docker 配方"）不是主因，主因是内嵌实例里没有这些扩展。

**优先级判断：** 交接说明 §7 自己实测过"精确条款命中，目标条款排第 1"。也就是说在标点分段粒度下，精确条款检索已经够用。中文分词是**已知上限**，不是当前瓶颈。

### 2.6 其余各条

**重排延迟（该报告 §6）：** 建议"对精确条款查询用 `budget=low` 减少候选集"。这是交接说明 §7 已经**自行收回过的错误机制**——官方 `retrieval.md` 明写重排预筛上限与检索预算无关。源码里的正确杠杆是：

```
HINDSIGHT_API_RERANKER_MAX_CANDIDATES       默认 300（平铺上限）
HINDSIGHT_API_RERANKER_MAX_CANDIDATES_LOW   默认 0  ← 按预算档缩放，本机未设
HINDSIGHT_API_RERANKER_MAX_CANDIDATES_MID   默认 0
HINDSIGHT_API_RERANKER_MAX_CANDIDATES_HIGH  默认 0
```

**`REFLECT_LLM_TIMEOUT`：** 成立。未设，源码 `DEFAULT_REFLECT_LLM_TIMEOUT = 30.0`。补充：`llm_requests` 里 reflect 最近 76 次调用**全部成功**，所以是潜在风险不是现行故障。

**`OPERATION_RETENTION_DAYS`：** 成立。未设，默认 0，`async_operations` 实测 **12,499** 行（`completed 12483 / failed 6 / pending 6 / processing 4`）。

**关于那 6 条失败（交接说明 §6 的"4 个卡满 3600 秒"）：** 数据库里是 6 行、实际是 **3 个作业**（`batch_retain` 与 `retain` 成对记录），全部创建于 2026-09-28，错误原文与交接说明 §6 引用的一致：

```
Task exceeded the 3600s wall-clock limit for 'batch_retain'
(stage=llm.openai.retain_extract_facts.attempt=2/4) and was cancelled.
```

交接说明写的"4 个"应更正为 **3 个作业（6 行）**。`LLM_MAX_RETRIES=0` 的处方方向正确。

---

## 三、真正的问题清单（按紧急度）

### P0 — 配置写进去了，但服务没读到（当前唯一的实质性故障）

| 证据 | 值 |
|---|---|
| `hindsight-api` 进程启动时间 | 2026-09-30 **01:03:17** |
| `~/.hindsight/profiles/dsh.env` 最后修改 | 2026-09-30 **02:13:18** |
| `GET /version` | `features.observations = false` |
| `GET …/banks/coding-agent::zcode/config` | `enable_observations = false` |
| 配置文件现状 | `HINDSIGHT_API_ENABLE_OBSERVATIONS=true`（**唯一一处生效**） |

判别性证据（排除"环境变量根本没被加载"这个竞争解释）：`HINDSIGHT_API_ENABLE_BANK_LLM_HEALTH` 的**默认值是 `False`**（`config.py:1478`），而运行中的服务报 `bank_llm_health = true`，配置文件里也有这一条 ⇒ **环境变量确实被读取了**。因此 `observations=false` 只能是"这一条是在进程启动之后才写进文件的"。

**后果**：四条待生效配置（`LLM_MAX_RETRIES=0` / `WORKER_ID=hindsight-dsh` / `LLM_TRACE_RETENTION_DAYS=90` / `ENABLE_OBSERVATIONS=true`）全部未生效。其中**最贵的一条是 `LLM_TRACE_RETENTION_DAYS`**：`llm_requests` 正在按 1 天滚动删除，每多等一天就永久少一天用量证据。

四条键的重复键问题已确认修好（各只有 1 处生效）：

```
HINDSIGHT_API_ENABLE_OBSERVATIONS        active=1  commented=1
HINDSIGHT_API_LLM_MAX_RETRIES            active=1
HINDSIGHT_API_WORKER_ID                  active=1
HINDSIGHT_API_LLM_TRACE_RETENTION_DAYS   active=1
```

### P1 — 内务与不可逆项

- 两个探针库共 15,071 条试验事实 + 6 个 HNSW 索引。删除**不可逆**。
- `OPERATION_RETENTION_DAYS=0`，作业表 12,499 行且只增不减。

### P2 — 需要花钱/花时间的决策

- 开启 observations 后，`enable_auto_consolidation` 已经是 `true`，`pending_consolidation = 119,009` 会开始被 LLM 归并。**成本与耗时官方未给数**，而主模型是限时免费窗口。
- 中文检索的改善只有换外部 PostgreSQL 一条路，且按现有实测优先级低。

### 不属于问题（明确否定）

- 抽取路径没有静默丢事实。
- 标签没有失控。
- 探针库没有污染生产库的召回或统计。
- 中文 BM25 不是"等于没有"。

---

## 四、修复方案

### 动作 A：重启 DSH，让四条配置生效（**需要业主批准**）

这是当前唯一能实质改善局面的动作，且**越早越省**（`llm_requests` 每天在删）。

- 重启方式：走 DSH 重启（生命周期插件拉起）。**绝不可手工跑 `hindsight-api.exe`** —— 交接说明 §2/§9 记录过：手工启动会绕开 `DSH_PARENT_PID` 绑定，且会连到空的 `hindsight` 实例。
- 重启前已核对：四条键各只有一处生效，无重复键。
- 重启后验证（正确方法）：
  - `GET http://127.0.0.1:8888/version` → `features.observations` 应为 `true`
  - `GET http://127.0.0.1:8888/v1/default/banks/coding-agent::zcode/config` → `enable_observations` 应为 `true`
- ⚠ 重启 DSH 会中断当前会话。

### 动作 B：重启时一并追加的低风险配置（**需要业主批准**）

| 键 | 建议值 | 理由 | 风险 |
|---|---|---|---|
| `HINDSIGHT_API_REFLECT_LLM_TIMEOUT` | `180` | 链上是慢速免费模型；官方要求按最慢的设 | 低。超时变长只影响卡死时的等待 |
| `HINDSIGHT_API_OPERATION_RETENTION_DAYS` | `30` | 作业表 12,499 行、默认永不清理 | 低。只删已终结的作业行 |
| `HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS` | `true` | 把"静默丢事实"变成"显式失败"，可被监控看见 | **中**。部分抽取失败会把整条 retain 标成 failed，免费模型偶发失败时会多出红色作业。这正是我们要的可见性，但要业主接受这个"变吵"的代价 |

### 动作 C：清理两个探针库（**不可逆，需业主明示批准**）

- 正确路径：`DELETE /v1/default/banks/probe-import-20`、`DELETE /v1/default/banks/probe-clean-20`
- 该报告写的 `DELETE /banks/probe-import-20` 在本机是 **404**（实机路径带 `/v1/default/` 前缀）。
- 不需要重启，可以单独做。
- 说明：这是内务，不是救火。删了不会让记忆变干净，因为记忆本来就没被它们弄脏。

### 动作 D：归并的启动方式（**需要业主决策**）

`observations` 一旦生效，11.9 万条待归并会开始被归并（`enable_auto_consolidation` 已为 `true`）。建议顺序：

1. 先给 `coding-agent::zcode` 配 `observations_mission`（当前 `null`），明确"这个库要合成什么样的通则"——这是质量调优，不是防垃圾。
2. **先在一个小库上验证归并输出质量**（例如拿一个探针库或临时库），再放开生产库。
3. 期间盯 `async_operations` 与 `bank_stats_cache.pending_consolidation` 的下降速度，估算全量成本。

### 动作 E：明确不做（避免被那份报告带着走）

- **不要**设 `HINDSIGHT_API_TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE=chinese` —— 会让 BM25 每条查询报错。
- **不要**为标签去加 Entity Labels —— 标签体系在正常工作，改它没有收益。
- **不要**用 `budget=low` 解决重排延迟 —— 机制不成立；要调就调 `RERANKER_MAX_CANDIDATES_LOW/MID/HIGH`。

### 动作 F：更正文档（低成本、应做）

`docs/research/HINDSIGHT-DEPLOYMENT-STATUS-2026-09-30.md` 中以下三处应按本文更正：

1. §5.1 "中文关键词检索等于没有" → 改为"中文关键词只能到标点分段粒度，段内子串不命中"。
2. §6 与 §9 "4 个作业卡满 3600 秒" → 更正为 **3 个作业（数据库 6 行，`batch_retain`/`retain` 成对）**。
3. §8 "中文分词未解决" → 补充"本机实例 62 个可用扩展中不含 pgroonga / pg_search / zhparser，改善必须换外部 PostgreSQL"。

---

## 五、重启与验证（2026-09-30 02:32–02:40，实测）

### 5.1 更正本文 §四 动作 A 的说法

本文 §四 动作 A 原文写的是"走 DSH 重启（生命周期插件拉起）"——**这是含糊的转述，等于没给**。本机指定的重启入口是：

```
C:\Users\Zegel\.dsh\tools\dsh-restart.ps1        （工具手册 §"重启 DSH 宿主" 指定：一律用 dsh-restart）
```

写本文时没有查过 `~/.dsh/tools/`、也没有打开 `~/.dsh/纪律/工具手册.md`（该手册第 8 行第一句就是这条规定）。**留痕：错话 + 更正**。

### 5.2 重启如何执行（含一处必须自己补的步骤）

旧宿主 pid 21580 被杀；新宿主 pid 9752 于 02:34:47 起；记忆服务 `uv` pid 34520 / `hindsight-api` pid 30092 **新起于 02:35:17 / 02:35:36** ⇒ 全新拉起，**不是复用**。`/health` 40.8 秒后就绪。

**必须自己补的那一步**：`dsh-restart.ps1` 只等 **3080**（DSH 网页端口）释放，**不等 8888**；而生命周期插件启动时「8888 已在监听就复用、不重启」。新宿主在杀掉后约 0.4 秒起来，`serve.mjs` 的 `watchParent` 却是 **5 秒**轮询一次。若不干预：旧记忆服务被新宿主判为"外部已有实例"而复用（配置不生效），随后又被 `serve.mjs` 的收摊逻辑杀掉 ⇒ **留下没人管的孤儿服务**。

因此在 `dsh-restart.ps1` 派发成功后、宿主被杀的 60 秒延迟内，先手工执行了：

```
node D:\AI\oss-research-and-deployments\hindsight-ov\app\stop-server.mjs   →  STOP_OK
```

（随后实测 8888 与 5432 均已释放。）这是本次重启唯一需要人工补齐的环节，建议以后固化进工具。

### 5.3 四条配置的核对结果

| 配置 | 结论 | 证据 |
|---|---|---|
| `ENABLE_OBSERVATIONS=true` | ✅ **已生效** | `GET /version` → `features.observations: true`；bank config → `enable_observations: true` |
| `WORKER_ID=hindsight-dsh` | ✅ **已生效** | `serve-out.log`：`Worker id: hindsight-dsh (source: HINDSIGHT_API_WORKER_ID)`；`Worker hindsight-dsh starting polling loop` |
| `LLM_MAX_RETRIES=0` | ⚠ **已加载，无法非破坏性观测** | 与上面两条同文件、同一次重启加载；要验证只能制造一次失败，**未做** |
| `LLM_TRACE_RETENTION_DAYS=90` | ⚠ **已加载，效果待判** | 见 5.4 |

### 5.4 保留期为什么还不能下结论

保留清扫**每小时**一次。历史日志里每次都有删除量（16 / 50 / 65 / 108 / 136 / 303 行）：

```
2026-09-29 22:16:42  Retention sweep public.llm_requests: DELETE 16
2026-09-30 01:04:18  Maintenance: retention took 0.015s     ← 无 DELETE
2026-09-30 02:04:21  Maintenance: retention took 0.000s     ← 无 DELETE
2026-09-30 02:36:50  Maintenance: retention took 0.000s     ← 无 DELETE（重启后）
```

**这几行不足以当证据**：现存最老一行是 `2026-09-28 19:19:51 UTC`；清扫发生在 `2026-09-29 18:36:50 UTC`，若保留期为 1 天，截止线是 `2026-09-28 18:36:50 UTC`——最老一行比截止线**新**，两种保留期下都不该被删。

**唯一能判定的时点**：`2026-09-28 19:19:51 UTC` 这行跨过 1 天年龄线是在 **2026-09-29 19:19 UTC**。看它之后的下一次整点清扫：

- 被删 ⇒ 仍是 1 天，配置没生效
- 存留 ⇒ 90 天生效

### 5.5 已按业主选择按住生产库（成功）

`coding-agent::zcode` 重启后仍是 **0 条 observation / 119,061 条事实 / `last_consolidated_at` 为空**。`enable_auto_consolidation=false` 的 bank 覆盖挡住了 11.9 万条归并。

**但另外 10 个库在 02:36:50 被自动排了归并作业**（10 个 processing + 1 个 pending）：

```
probe-clean-20, coding-agent::DSH, coding-agent::DSH maintain, coding-agent::AI,
coding-agent::SW, coding-agent::ComfyUI_windows_portable,
coding-agent::oss-research-and-deployments, coding-agent::work space,
coding-agent::deepseek-harness, dsh-resources
```

截至 02:40 只产出 2 条 observation（`coding-agent::DSH`）。其中不小的几个：`probe-clean-20` 7,463 条、`dsh-resources` 5,620 条、`coding-agent::AI` 5,418 条。按住它们与按住 zcode 是同一招。

### 5.6 新发现：`WORKER_ID` 改动孤儿化了 3 个作业

新进程启动日志：

```
[WORKER_STATS] worker=hindsight-dsh ... others: DESKTOP-U18P3CQ:3
```

`DESKTOP-U18P3CQ` 是改动前的默认值（主机名）。这 3 个 `retain` 仍是 `processing`：

| bank | 建于 (UTC) |
|---|---|
| `coding-agent::DSH maintain` | 2026-09-29 18:18:14 |
| `coding-agent::DSH` | 2026-09-29 18:23:51 |
| `coding-agent::zcode` | 2026-09-29 18:33:36 |

**源码依据**（`worker/poller.py`）：回收 SQL 的条件是 `WHERE status = 'processing' AND worker_id = $1`，`$1 = self._worker_id` ⇒ **只回收自己的**。worker id 从 `DESKTOP-U18P3CQ` 改成 `hindsight-dsh` 之后，这 3 行不再属于任何活着的 worker，**不会被任何自动路径回收**。

讽刺之处：**若 worker id 维持主机名不变，这 3 个本来会在本次重启时被自动回收**。设稳定 id 对"以后的每次重启"是对的，代价是对"这次"收了一笔孤儿税。可用 `POST /v1/default/banks/{bank_id}/operations/{operation_id}/retry` 收掉。

### 5.7 重置工具的既有缺陷：插话通知失效

重启前对 3 个正在跑的会话发"请停下"，**全部返回**：

```
continue-session: token 没换来 cookie（HTTP 401）—— token 每次启动新生成，可能已过期
```

⇒ 它们**没收到通知**，是被直接打断的。脚本随后改用"日志文件是否还在增长"判定"全部已停下"就放行了——**通知失败时这个判定并不可靠**。

重启后的接上结果 `其它会话=partial`：6 个"已受理"、2 个"被拒(退出码 6)"（`session-3ea983cd-…`、`session-57ffd75a-…`）。

---

## 六、修复执行记录（2026-09-30 02:36–02:50）

业主指令"按照你推荐的修复问题"，本节记录实际做了什么、每一步的证据在哪。

### 6.1 清掉 `WORKER_ID` 改动留下的 3 个孤儿作业

**没有自己搓 SQL。** 先查现成工具，发现包自带 `hindsight-admin`：

```
hindsight-admin decommission-worker   Release all tasks owned by a worker (sets status back to pending).
hindsight-admin decommission-workers  Release all processing tasks from all workers.
hindsight-admin worker-status         Show all currently processing tasks grouped by worker.
```

注意**不能用复数那条** `decommission-workers`——它会把当时正在跑的 10 个归并作业一起释放掉。只释放死掉的那个 worker：

```
$ HINDSIGHT_API_DATABASE_URL=pg0://hindsight-embed-dsh hindsight-admin decommission-worker DESKTOP-U18P3CQ --yes
Decommissioning worker 'DESKTOP-U18P3CQ' (schema: public)...
Released 3 task(s) from worker 'DESKTOP-U18P3CQ'
```

释放前 `worker-status` 的证据（`DESKTOP-U18P3CQ` 的 3 个任务 `last_update` 等于认领时刻 ⇒ 自认领起就没动过；`hindsight-dsh` 的 10 个持续更新 ⇒ 是活的）：

```
Worker: DESKTOP-U18P3CQ (3 task(s))
  12298111  retain  bank=coding-agent::DSH maintain  running=0:18:01  last_update=0:18:01 ago
  882e1cc7  retain  bank=coding-agent::DSH           running=0:17:24  last_update=0:17:24 ago
  ba8f49a9  retain  bank=coding-agent::zcode         running=0:07:39  last_update=0:07:39 ago
```

⚠ 附带风险已核对：`hindsight-admin` 启动时会打印 `Starting embedded PostgreSQL`，但实测**复用已在跑的实例、退出时也没有带走它**（执行后 `/health` 仍 `healthy`）。变更是幂等可重复的。

### 6.2 给生产库配归并任务书

`coding-agent::zcode` 的 `observations_mission` 由 `null` 改为：

> 本库是 KnowledgeStation（zcode 仓库）编码代理的长期记忆。只合成"以后再做这个项目仍然有用"的通则。
>
> 值得合成：架构决定与约定（为什么这样做、边界在哪）；踩过的坑及其成因和正确做法；业主已否决或作废的做法（用于避免重复提案）；长期计划的目标、阶段与进度；环境或工具的硬约束。
>
> 不要合成：一次性调试过程与临时命令；会过期的具体数值（行号、条数、大小）；已被后续更正取代的旧说法（只留更正后的结论）；单纯的文件罗列或代码片段。

依据：`engine/consolidation/prompts.py:210 build_mission_section()` 把它作为 `## MISSION` 段注入归并提示词，且**MISSION 与后续处理规则冲突时以 MISSION 为准**。

### 6.3 `dsh.env` 追加三条配置

写在**文件末尾**（本文件按"后者胜"解析，末尾是唯一无歧义的位置）：

| 键 | 值 | 依据 |
|---|---|---|
| `HINDSIGHT_API_REFLECT_LLM_TIMEOUT` | `180` | 未设时默认 `30.0`（`config.py DEFAULT_REFLECT_LLM_TIMEOUT`），全局 `LLM_TIMEOUT=300` 管不到它 |
| `HINDSIGHT_API_OPERATION_RETENTION_DAYS` | `30` | 默认 `0` = 永不清理；实测 `async_operations` 12,499 行 |
| `HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS` | `true` | 把"静默丢事实"变成显式 failed（`memory_engine.py:4155`） |

写入后逐键核对，**每个键各有且仅有一处生效**：

```
HINDSIGHT_API_ENABLE_OBSERVATIONS        active=1  commented=1
HINDSIGHT_API_LLM_MAX_RETRIES            active=1
HINDSIGHT_API_WORKER_ID                  active=1
HINDSIGHT_API_LLM_TRACE_RETENTION_DAYS   active=1
HINDSIGHT_API_REFLECT_LLM_TIMEOUT        active=1
HINDSIGHT_API_OPERATION_RETENTION_DAYS   active=1  commented=1
HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS  active=1  commented=1
```

### 6.4 修 `~/.dsh/tools/dsh-restart.ps1`（四处）

原件备份：`dsh-restart.ps1.bak-20260930-024303-before-hindsight-prestop+token-staleness`。每处改动的动机都来自本文 §5 的实测，不是推测。

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | 重启只等 3080、不等 8888，而插件"8888 有人监听就复用" ⇒ 新宿主复用旧记忆服务，`dsh.env` 白改，随后旧服务被看管脚本杀掉变成孤儿 | 在杀掉宿主之后、拉起之前，显式跑 `stop-server.mjs` 并轮询等 8888 释放（至多 30 秒） |
| 2 | `Get-CurrentHostUrl` 无条件取最新的 `host-*.out.log`；那只有"由本工具启动过"的宿主才有，用户自己启动时它指向十几小时前的宿主 ⇒ token 必然 401 | 加**签发时刻判据**：来源时间必须晚于当前宿主进程的启动时刻，否则返回 null 并明确告警；新增第二来源（状态文件里的 url+urlAt） |
| 3 | 插话失败后脚本仍用"日志不再增长"判定"全部已停下"，等于没通知就把人打断 | 统计送达/未送达，失败时打印醒目告警，并把计数写进放行那一行 |
| 4 | 跑一次 `-DryRun` 会把 `restart-last-status.json` 里的"上次重启是成功还是失败"覆盖成 `dry-run-ok`；`url=` 也被抹掉 | `-DryRun` 改写到独立文件 `restart-last-dryrun.json`；`Save-Status` 额外记 `url` + `urlAt`（ISO），跨状态写入存活 |

验证方式（**没有真跑重启之前，只做了这些**）：PowerShell 语法解析通过；用真实数据单测过期判据；连续三次 `-DryRun` 核对计划输出与状态文件副作用。

### 6.5 重启并验证（第二次重启，用的是修好的工具）

真跑日志 `guard/logs/restart-20260930-024555.log`：

```
02:46:41 kill 宿主 pid=9752
02:46:45 端口已释放
02:46:46 HINDSIGHT: STOP_OK
02:46:48 HINDSIGHT: 8888 已释放 → 新宿主会用新配置重新拉起
02:46:48 RELAUNCH(primary) -> pid=13580
02:46:53 宿主已恢复：3s，pid=13580，兜底=False
```

⇒ 新增的第 2b 步**确实执行且奏效**：记忆服务在拉起之前就停干净了。

**插话通知这次全部送达**（对比上一次全部 401）：

```
02:44:53  已插话通知 session-222a4a34-… 停下（退出码=0，用当前宿主地址）
02:44:53  已插话通知 session-a9874c65-… 停下（退出码=0）
02:44:54  已插话通知 session-c4265f00-… 停下（退出码=0）
02:44:54  已插话通知 session-cd4b9914-… 停下（退出码=0）
02:45:54 ACTIVE-SESSIONS: 全部已停下 → 放行（… 停机通知送达 4 个、未送达 0 个）
```

⇒ 四条会话是**收到通知后自己停下**的，不是被硬打断的。修复 2 和 3 都得到真机验证。

### 6.6 第二次重启后的核对结果

| 项 | 结果 | 证据 |
|---|---|---|
| 记忆服务全新拉起 | ✅ | `hindsight-api` 新起于 **02:47:18**（旧值 02:35:36）；与 `RELAUNCH` 02:46:48 对得上 |
| `observations` | ✅ 仍生效 | `/version` 无需再看（第一次已证）；生产库 `enable_observations=true` |
| `Worker id` | ✅ | `serve-out.log`：`Worker id: hindsight-dsh (source: HINDSIGHT_API_WORKER_ID)` |
| **归并作业被自动回收**（关键对照） | ✅ | `Worker hindsight-dsh recovered 11 stale tasks from previous run`——重启前正在跑的 10 个 consolidation + 1 个 retain 全部回到队列，`retry_count` 由 0 变 1（正是 `_reclaim_own_processing_tasks` 的签名） |
| `DESKTOP-U18P3CQ` 残留 | ✅ 只剩历史终态 | `status=failed` 3 行（2026-09-28 的超时失败记录），**无 processing**；poller 报 `others: none` |
| 生产库仍被按住 | ✅ | `coding-agent::zcode`：0 条 observation / 119,061 条事实 |
| 其余库归并产出 | 进行中 | 约 40 分钟累计 174 条 observation，9 个库；最慢的是 `dsh-resources` 17 条 |
| `LLM_TRACE_RETENTION_DAYS=90` | ⏳ **待判** | 见 6.7 |

**对照意义**：第一次重启（worker id 从 `DESKTOP-U18P3CQ` 改成 `hindsight-dsh`）留下 3 个孤儿；第二次重启（id 未变）11 个作业全部被自动回收。⇒ §5.6 的判断得到正面验证：设稳定 worker id 的价值就在这里，代价只是**第一次改名**时那笔孤儿税。

### 6.7 保留期为什么仍然待判（以及怎么判）

标记行是 `llm_requests` 里最老的一条：`2026-09-28 19:19:51.250979+00`。它满 1 天是在 **2026-09-29 19:19:51 UTC**（本地 09-30 03:19:51）。清扫每小时一次，首次跨线后的清扫在 **本地约 03:59–04:20**。

- 标记行**消失** ⇒ 仍是 1 天，配置没生效
- 标记行**存留** ⇒ 90 天生效

**已挂一个后台任务自动判定并写盘**：`var/hindsight-audit/retention-verdict.txt`（最晚本地 04:45 出结论）。

不能提前下结论的原因（本文 §5.4 已记过一次，这里再钉一遍）：现存最老行在判定时刻之前**本来就该存留**，两种保留期下表现完全相同，任何"看起来没删"的观察都不构成证据。

### 6.8 探针库已删除（业主 2026-09-30 明示）

业主看过通俗说明后指示"两个测试笔记本删了。小的笔记本弄完了再说"。删除前核对了两点：两个库各自只有一个**排队中**的 consolidation 作业（没有在跑的活，不会打断）；库名是手写的 `probe-*`，任何 `bankIdTemplate` 都不会落到它们身上。

```
DELETE /v1/default/banks/probe-import-20  → {"success":true,"deleted_count":7646}
DELETE /v1/default/banks/probe-clean-20   → {"success":true,"deleted_count":7544}
```

删除后核对（全部为零才算干净）：

| 检查 | 结果 |
|---|---|
| `memory_units` / `documents` / `banks` / `async_operations` 里 `bank_id like 'probe-%'` | **各 0 行** |
| `memory_units` 上 `indexdef like '%probe-%'` 的残留索引 | **0 个** |
| 库总数 | 16 → **14** |
| 全库事实总数 | ~158,400 → **143,350** |
| `/health` | `healthy` |

**业主同时决定：生产库的自动归并暂不放开**，等另外 10 个较小库跑完、看过产物质量再说。因此 `coding-agent::zcode` 的 `enable_auto_consolidation=false` 保持不动。

### 6.9 顺带实测到的归并速度（给"要不要放开生产库"当依据）

在不小于 10 分钟的三个窗口上测得的事实合并速率：

```
last 10 min  48 条
last 30 min 174 条
last 60 min 275 条
```

⇒ 约 **每小时 300 条**，窗口间基本稳定。生产库待合并 11.9 万条，按此速率外推约 **400 小时 ≈ 16–17 天**。

⚠ 这是**从约 1 小时数据外推**，不是实测跑完的结论；且它绑定当前模型链（限时免费）。免费窗口关掉，这件事会停在半路。

