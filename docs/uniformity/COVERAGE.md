# 摸底完成度：哪些透了、哪些没透（滚动更新）

> **这份文件存在的唯一理由**：上下文会被压缩。压缩之后**不许靠印象说"摸透了"**，
> 照这张表说话。每行都有实测依据。
>
> **最后更新**：2026-10-24 ｜ **基准提交**：`f3eee72f`

---

## 一、总账

| 面 | 总量 | 摸到什么程度 | 依据 |
|---|---|---|---|
| `src/core` 代码 | 155 文件 / 45,542 行 | **结构与关键路径**，约 20% 的行被真正读过 | `01-core.md` |
| `src/core` 最大 10 个文件 | `server.py` **3,341** / `pipeline.py` **2,443** / `text_utils.py` **2,162** / `inspector.py` **937** … | **四个最大的全部已摸清**（2026-10-24）：`10-api-server.md` + `09-big-files.md` | `09` / `10` |
| `plugin/src` 宿主侧 | 19 js / 9,974 行 | **结构 + 关键路径** | `02-plugin.md` |
| `plugin/client` 前端 | 31 文件 / 1,167 KB（`api.ts` 5,011 行） | **已逐文件摸清职责**（2026-10-24 补） | `06-frontend.md` |
| `tests` | 184 py / 3,117 条用例 | **结构 + 覆盖率缺口 + 恒真断言** | `04-tests-tools-gates.md` |
| `scripts` | 68 个 | **分组 + 一次性/长期之分** | `03-docs-specs-scripts.md` |
| `docs` | **223 份** | 完整读过约 35 份（**16%**） | 本文件 §三 |
| `eval/` | 438 文件 / 19.7 MB | **已摸清**（2026-10-24 补） | `07-other-dirs.md` |
| `tools/gov-qa/` | 3,423 文件 / 948.8 MB | **结构与入口已摸清；内容抽样 3/594** | `07-other-dirs.md` |
| `wenjianmulu/` `output/` `pipeline/` `.specify/` `.codebuddy/` `.dsh/` `.zcode/` | 合计 68 文件 | **已摸清**（2026-10-24 补） | `07-other-dirs.md` |

---

## 二、明确还没读透的（不许说"全摸透了"）

| 文件 | 行数 | 状态 |
|---|---|---|
| ~~`src/core/api/server.py`~~ | ~~3,115~~ **3,341** | **已摸清（2026-10-24）**：`create_app` 闭包 2,997 行 / 103 个嵌套函数 / 35 个本该可单测却测不了的；67 条端点归类；5 个超 100 行函数；数据泄漏面 2 条。见 `10-api-server.md` |
| `src/core/ingestion/pipeline.py` | 2,254 | **只读了被引用的片段** |
| `src/core/text_utils.py` | 1,844 | 读了标准号归一相关的 5 个函数；**其余没读** |
| `src/core/knowledge/folder_store.py` | 1,331 | 只读了效力分色那一段 |
| `src/core/update/inspector.py` | 845 | **未读** |
| `plugin/client/api.ts` | 5,011 | 已摸清「117 导出 / 66 端点 / 6 种失败策略 80 次」等结构；**逐函数实现未读** |
| `plugin/client/KsEvidenceTab.tsx` | 2,695 | 已摸清子视图与可抽纯函数；**渲染细节未读** |

---

## 三、`docs/` 里读过 vs 没读

- **已读（约 35 份）**：`README.md`、`wiki/architecture.md`、`wiki/components/*`（20 份小篇）、
  `naming-convention.md`、`TEST-FLAKES.md`、`tool-catalog.md`、`NOT-DOING.md` 摘要、
  `PORTABILITY.md`、`uniformity/*`（自己写的 8 份）。
- **没读（约 188 份）**：`DEVELOPMENT-HISTORY.md`（339 KB）、`REQUIREMENTS-v4.3.md`（213 KB）、
  `UI-BASELINE.md`（262 KB）、`CHANNEL-COVERAGE-PLAN.md`（250 KB）、`RETRIEVAL-LONG-RANGE-PLAN.md`（172 KB）、
  `KB-FOLDER-PLAN.md`（157 KB）、`MATERIALS-PLANE-PLAN.md`（157 KB）、
  `archive/` 46 份、`research/` 97 份、`verify-briefs/` 21 份 的绝大部分。

---

## 四、已确认「不能删」的东西（删了会静默坏）

| 东西 | 删了会怎样 | 有没有测试会红 |
|---|---|---|
| `eval/baseline.json` + `eval/golden/knowledge-snapshot.db` | **全项目唯一防检索倒退的门禁消失**（且它只在 `-Full` 跑，`-Quick` 跑不到） | 无（基线缺失才是硬失败，删了就没了） |
| `wenjianmulu/` 两个 PDF | `/documents/{id}/file` 与 `/figure/{n}` 404；条款页码/书签映射**静默退化** | **没有任何测试会红**（`grep -r wenjianmulu tests/` 为空） |
| `var/data/` | 生产库本身（8,983 部 / 663,634 条） | — |
| `pipeline/03-contract-delta.md` | 改 schema 前的契约台账没了 | 无 |

## 五、已确认「可以删」的东西（本地产物，0 受控）

`output/`（**删前先抄 `GOAL.md`**，它和 `tools/gov-qa/gate/GOAL.md` 内容不同）、
`.codebuddy/`（已停用）、`.zcode/`、`.dsh/skills/speckit-*`（10 个用户级副本）。

## 六、已确认的风险

| 风险 | 证据 | 状态 |
|---|---|---|
| **12 处写死旧工作区路径** `D:/AI/work space/zcode` | `grep` 实测 | **未修**。其中 `smoke-kb-page-render.mjs:2629` 是**假绿**——它读外部旧副本，只因旧目录还在、内容恰好相同才通过 |
| **`tools/gov-qa/data/` 644 MB 全部进了 git** | `git ls-files` = 686 = 目录文件总数 | 未决，需业主拍 |
| 该目录含**政府工作人员姓名 + 工作手机号** | 抽样 3/594 个 jsonl / 663 条（**0.17%，是抽样不是全部**）：答复原文「工作人员手机号：18811686625」。**无身份证/住址/群众手机号** | 未决 |
| 🔴 **`GET /api/v1/diagnostics/debug-dumps` 能读光历史问答** | 实测 SELECT 是 `dump_id, trigger_type, query, created_at, llm_output, logs` ⇒ 返回**全部历史提问原文 + 完整模型输出 + 证据/槽位**；**产品侧 0 个调用方**，而 token 明文存在 `engine.session.json` ⇒ 谁拿到 token 谁就能读。⚠ **更正（我第一版写错）**：原写「还返回 `prompt`（最近 4 轮对话）」，**不准确** —— `prompt` / `retrieval_result` **确实写进表了**（`_write_debug_dump` 的 INSERT 带它们），但**这个端点的 SELECT 没带这两列** ⇒ 不走这条路漏出去。**错话原文保留于此。** | **未修** |
| 🔴 **`dump=false` 能让一次云模型调用在审计里彻底消失**（已自查，成立） | `server.py:1783` `dump_enabled = bool(body.get("dump", True))`，而 `if dump_enabled:` 是 **3 处写 debug_dump 的唯一开关**（L1980 / L2015 / L2082）⇒ 传 `dump=false` 则该次云调用**一行都不落库**。同时 `deepseek_client.py` **全文 0 处 `record_egress`**（只有 `jev_client.py` 那类非 chat 调用才登记）⇒ **没有兜底审计**。`/ks/answer` 那条路没有这个开关 ⇒ 两条路审计强度不同。与「每次云调用完整 payload 落库」的承诺冲突 | **未修** |
| 🟠 **重新入库会丢数据**（静态推断，**未验证**） | `reingest` **先删旧文档（独立事务）再写新文档** ⇒ 新事务失败或进程被杀就是「旧已删、新没进」，而**目录归属快照只在内存里**。另 `total_clauses` 报的是 `n_normal - n_pre`，实际入库是 `n_normal + n_pre + n_附录` ⇒ **算术可疑** | 未验证 |
| 🟠 **`_expand_title_clauses` 仍有两份实现**（和已修的 `_answer_confidence` 同型） | `api/server.py:2525` 与 `llm/ks_answer.py:1167`；差异是硬编码 `80` vs 常量、无/有 try-except；注释里明写「与另一处同步放宽」⇒ **改一处不会红**。唯一那条测试在测试文件里重写了一遍正则，**两份实现都不执行** | **未修** |
| 🟠 **11 条端点全仓零调用方** | annotations×3 / projects×4 / `documents/{id}/versions` / `/compare` / `documents/impact` / `DELETE doc-bookmarks/{id}`；另 20 条只有测试没有产品调用方（含那条 328 行的 SSE） | 未决 |
| **`ks_answer` 能不能用不知道** | 上一轮实测每次 `Connection error`；本轮未复测（要先配 LLM key） | **未复测** |

---

## 七、摸底还差什么（按价值排）

1. **`src/core` 剩下约 80% 的行**：`pipeline.py` 2,254 行、`inspector.py` 845 行、
   `text_utils.py` 其余 1,700 行 —— 这些是「解析入库」与「巡检」两条主线的心脏。
2. **`docs/` 那 188 份没读的**：其中 `REQUIREMENTS-v4.3.md` 是需求编号的权威出处，
   `DEVELOPMENT-HISTORY.md` 339 KB 记录 203 轮决策 —— **没读就没法判断"某个做法是定案还是临时"**。
3. **`tools/gov-qa` 的隐私面**：只抽了 3/594 个文件。
4. **真库实况**：本机 `%APPDATA%\KnowledgeStation` 不存在，
   所以 golden 重建、recall-funnel 重跑、两个 PDF 的 `doc_meta` 实况，都只能核代码不能核数据。

---

## 八、这份表怎么维护

- **每读透一块，就把它从 §二/§三 挪到 §一**，并写清读到什么程度。
- **不许**用"摸得差不多了"这种话；只写「读过」或「没读」。
- 数字变了就跟着改，并注明口径（工作树 / HEAD）。

---

## 九、`docs/` 没读的那 188 份：按「读了能回答什么」排序

**不要按大小读**（最大的 `archive/history/rounds-10.1-10.203.md` 999 KB 是历史归档，
读了也不能回答当前该怎么做）。按**"读它能决定什么"**排：

| 优先级 | 文件 | 大小 | 读了能回答什么 |
|---|---|---|---|
| ★★★ **1** | `REQUIREMENTS-v4.3.md` | 208 KB | **需求编号的权威出处**。现在代码注释里到处引 `R24` / `F-xx` / `NOT-DOING #16`，不读这份就不知道那些编号指什么、哪条被撤了 |
| ★★★ **2** | `DEVELOPMENT-HISTORY.md` | 331 KB | **203 轮决策的账本**。判断「某个做法是定案还是临时」只能靠它。⚠ 与 `archive/history/rounds-10.1-10.203.md`（999 KB）有重叠，先读这份 |
| ★★ **3** | `NOT-DOING.md` | — | **已否决台账**。`AGENTS.md` 明令提案前必须对一遍，否则会重复端上业主早就否掉的东西（已发生两次） |
| ★★ **4** | `CHANNEL-COVERAGE-PLAN.md` | 244 KB | 渠道巡检方案与轮次台账（一个事实一个归属层的指定归属地） |
| ★★ **5** | `UI-BASELINE.md` | 256 KB | 界面基线。改前端前该读，否则不知道哪些样子是钉死的 |
| ★ **6** | `RETRIEVAL-LONG-RANGE-PLAN.md` | 168 KB | 检索长线计划。判断 `eval/baseline.json` 那 4 个指标该往哪走 |
| ★ **7** | `KB-FOLDER-PLAN.md` / `MATERIALS-PLANE-PLAN.md` | 154 KB ×2 | 目录与材料两条线的设计 |
| — | `research/dsh-official/*`（97 份，含两份 230 KB 的 INGEST-LEDGER） | — | DSH 研究。写插件/前端前查，平时不用 |
| — | `archive/`（46 份） | — | **历史归档，不作为当前权威**（`AGENTS.md` 里 `archive/` 是冻结区） |
| — | `verify-briefs/`（21 份） | — | 历次复核任务书。查"某条结论当初怎么验的"用 |

**读法建议**：不要从头读。`REQUIREMENTS-v4.3.md` 先读目录 + grep 需求编号；
`DEVELOPMENT-HISTORY.md` 按关键词 grep（比如想知道"为什么门禁是 12 步"就 grep "12 步"）。
**全文通读 331 KB 是浪费**，只需要"按需定位到某条决策"。
