# KnowledgeStation 全仓摸底（新对话从这里开始）

> **这份文件写给谁**：**完全没有记忆的新对话**。读完这一份，你应当能回答：
> 这个项目是什么、怎么跑起来、代码分几块各干什么、数据在哪、哪里已经坏了、
> 哪些结论是实测的、哪些还是空白。
>
> **不许跳过 §0 和 §1**。§0 讲怎么在这个仓里干活（不做会踩的坑），
> §1 讲项目本体。其余按需要查。
>
> **最后更新**：2026-10-23 ｜ **基准提交**：`64f37707` ｜ **摸底方法**：4 个独立子代理
> 通读 + 主对话逐条抽查复核 + 自建量化尺子 + 一次完整真跑。**复核结果见
> [`00-review-of-surveys.md`](00-review-of-surveys.md)**（子代理报告里 2 条结论被我实测推翻/更正，
> 所以**不要直接引用子代理原文**，先看本文件的标记）。

---

## 0. 这个仓的硬规矩（不做会当场踩）

### 0.1 一条命令跑门禁，以退出码为准

```powershell
pwsh -File scripts/run-gates.ps1 -Quick     # 改动面（tsc / mypy / 命令契约 / 全链 smoke）
pwsh -File scripts/run-gates.ps1 -Full      # 全量（+ pytest / uvicorn / 真宿主 e2e / gov-qa 三条）
```

- **一次只跑一个**。脚本用锁文件把并发变成当场报错，**退出码 3 = 有人在跑，不是失败**。
- `-Full` 实测耗时：pytest 一步就要 **19 分钟**（3,076 条用例）。
- 跑完的汇总固定落在 `%TEMP%\ks-gates-last.txt`；每一步的完整日志在
  `%TEMP%\ks-gates-logs\<时间戳>-<步骤名>.log`。

### 0.2 测试基线只涨不跌（棘轮）

`scripts/gates-baseline.json` 记天花板。公式（`run-gates.ps1`）：

```
totalRan        = passed + skipped + failed + errors
totalForRatchet = totalRan − untracked_excluded      （口径生效时）
判红条件        = totalForRatchet < baseline.pytest_total
```

**⚠ 两条实测陷阱**：
1. **`failed` / `errors` 必须算进总账**。漏算会把"2 条失败"误报成"少收集了 2 条"，判据方向反了。
2. **记账也用棘轮口径**（减掉未跟踪用例），否则把未跟踪文件的用例钉进基线，
   那份文件一被删就假红；有人手工调低基线去躲 ⇒ 造出"可静默删用例"的余量。

### 0.3 临时文件必须放 `.tmp/`（2026-10-23 实测踩过）

`tests/test_credentials_namespace.py` 有一条**全仓源码扫描**，射程覆盖
`src` / `scripts` / `plugin` / 根目录 / `.ps1/.bat/.cmd`，排除 `node_modules` / `.venv` /
`var` / `tests` 等，**但不排除 `.tmp/`**（`.gitignore` 原来只忽略 `.tmp-*` 这种带后缀的名字）。

**实测后果**：我在 `.tmp/` 放了个临时探针脚本，里面含 `SetValueEx` 字样
⇒ 那条测试当场判红：`源码里仍有系统层写入: .tmp/calibrate.py:104`。
⇒ 已在 `.gitignore` 补 `.tmp/`。**但注意**：`.gitignore` 管不住这条测试（它扫磁盘不扫 git），
所以临时文件里**不许出现** `SetValueEx` / `os.environ[` / `setx ` / `putenv` /
`SetEnvironmentVariable` / `environ.setdefault` 这些字样。

### 0.4 便携是硬约束（业主 2026-10-17 亲定）

**代码里不许写死绝对路径**。路径一律运行时推导：
- 插件从自身位置往上找仓根（`plugin/src/engine.js` 的 `findEngineRoot`，认 `src/core/main.py`）
- venv 底座自愈（`healVenvHome()` 改写 `pyvenv.cfg` 的 `home`；Windows venv **不带标准库**，整包换盘符就不可用）
- 模型在 `var/models/`、数据在 `var/data/`（都可用 `KS_MODELS_DIR` / `KS_DATA_DIR` 覆盖）

**⚠ 发现写死路径时不要"把旧值换成新值"** —— 那只是把同一个病推迟到下次拷贝。
判据见 [`../PORTABILITY.md`](../PORTABILITY.md)。

### 0.5 说话规矩（业主亲下的最高指令）

要业主确认时必须**直白朴实**：说这东西能做什么、点下去会发生什么、代价是什么。
**禁止**表名/接口名/架构/抽象/复用/解耦/重构/幂等这类词，**禁止**打比方。
**不许迎合**：同意之前先找反证；业主给的前提也要核；错了只认错的那条。

---

## 1. 项目是什么

**KnowledgeStation** = 本地跑的中文国标与法律法规知识工作站。

用户问一句合规问题（例：「甲醇作业要不要做职业健康检查」），它做三件事：
1. 在**本地库**里找相关条款原文（不是调云端搜索）
2. 把找到的原文 + 问题交给大模型，产出**三段式**答案：`依据` → `推导` → `结论`
3. 每条依据带**可点的原文链接**（能翻到 PDF 的那一页那个位置）

**它跟普通问答的区别**：结论必须能追到原文。库里没有就明说"库里没有"，
不许编；引用了不在证据里的条款会被拦下来并如实告知。

### 1.1 两个进程

| 进程 | 是什么 | 入口 |
|---|---|---|
| **Python 引擎** | 检索 / 入库 / 更新 / 导出 / 大模型调用 | `python -m src.core.main`（FastAPI，默认端口由插件分配） |
| **DSH 插件**（Node） | 给 DeepSeek Harness 提供 6 个模型工具 + 侧栏界面 + 49 条 `/ks/*` 路由 | `plugin/`，由 DSH 加载 |

插件通过 HTTP 调引擎；引擎崩溃不影响 DSH 本身。

**平时怎么用**：启动 DSH 宿主即可。插件自动注册（侧栏出现「知识库」+ 6 个模型工具），
**引擎按需懒拉**（随机端口 + 一次性 token，**不需要手动启动引擎**）。

**开发时怎么验**（都要在仓根跑）：

```powershell
# 引擎类型
.venv\Scripts\python.exe -m mypy

# 客户端类型（只编 plugin/client，不编 plugin/src 那批 .js）
npx tsc --noEmit -p plugin/client

# 插件冒烟（44 套，全链）
cd plugin; npm run smoke

# 命令回归
cd plugin; npm run verify:commands

# 单个冒烟（调试时用）
node plugin/scripts/smoke-channels-routes.mjs

# 重编客户端产物（改了 plugin/client/*.tsx 之后必须跑）
node plugin/scripts/build-client.mjs
```

**⚠ 三个最容易卡住的点**：
1. **改了 `plugin/client/*.tsx` 必须重编**，否则 `client.js`（1,784 KB，**受版本控制**）
   与源码不一致，`smoke-build-purity` 会红。
2. **`plugin/src/*.js` 没有任何静态类型门禁**（`tsc` 只编 `plugin/client`，
   `mypy` 只扫 `src`）⇒ 那批 `.js` 的行为验证**全靠 smoke**。
3. **冒烟里有 3 套要真浏览器**（`smoke-kb-pad-pixels` / `smoke-kb-cols` / `ui-badge-pixels`），
   没装 Chromium/Edge 就是红，不是跳过。


### 1.2 数据在哪（**绝对不要删**）

```
var/data/database/knowledge.db     生产库 3.11 GB —— 8,983 部标准/法规 / 663,634 条条款 / 184 万条位置片段
var/data/parse_out/                35.79 GB  —— 解析产物（条款里的图、公式从这里取，被 src/core/api/server.py 14 处读取）
var/data/backups/                  23.87 GB  —— 13 个快照
var/models/ks/                     2.28 GB   —— 向量与重排模型（bge-small-zh / bge-reranker-base）
var/models/mineru/{pipeline,vlm}/  4.70 GB   —— PDF 解析模型（MinerU 2.x）
.venv/                             5.06 GB   —— Python 环境（48,040 文件）
```

`var/data` **就是生产库本身**，不是测试数据。判据：随机抽样都是真 GB 标准，
只有 190/8,983 个文档名含「测试」字样。

### 1.3 6 个模型工具（agent 能调的）

| 工具 | 干什么 |
|---|---|
| `ks_answer` | 取证问答，返回三段式答案 + 效力 + 核验结果。自己推理 ⇒ **几十秒**，超时给 ≥120s |
| `ks_resolve_clause` | 按「标准号 + 条款号」精确定位一条原文（引用兜底用） |
| `ks_ping` | 探活：引擎在不在、模型加载没加载 |
| `ks_effect_report` | 库内标准的效力总览（五色：已废止/即将实施/现行有效/状态未知/仅参考） |
| `ks_materials` | 列出参考资料项目与材料（只读，评审是用户的判断） |
| `ks_collect` | 抓一个网页登记为待评审材料（一次一条；不能自己批准） |

说明书真源：`docs/tool-catalog.md`（**生成物，手改必红**，
改完跑 `node plugin/scripts/smoke-tool-catalog.mjs --write`）。

---

## 2. 代码骨架（实测）

```
zcode/                                     HEAD 64f37707
├── src/core/          Python 引擎    155 py / 45,439 行 / 16 子系统 + 9 根文件
├── plugin/            DSH 插件       19 js (9,968 行) + 31 tsx/ts (1,167 KB) + 56 mjs
├── tests/             pytest         181 py / 3,076 条用例
├── scripts/           工具脚本       68 个（55 py / 9 ps1 / 4 mjs）
├── tools/gov-qa/      **另一条线**   3,427 文件 / 948.8 MB（634 MB 数据受版本控制）
├── docs/              文档           29 顶层 + archive 46 / research 97 / verify-briefs 21 / wiki 21
├── specs/             Spec Kit      15 个（**两组编号撞车**，见 §6.3）
└── var/               本地产物       模型 6.87 GB + 数据 72.32 GB（**不受版本控制**）
```

### 2.1 `src/core` 16 个子系统

| 子系统 | 干什么 | 文件 | 行数 | 写什么 |
|---|---|---|---|---|
| `update` | 去 13 个官网查标准/法规有没有新版、废止、公告 | 36 | 8,811 | 渠道表、公告表、检查批次 |
| `ingestion` | 把 PDF/docx/网页文本切成条款写进库 | 20 | 7,684 | `doc_meta` / `clause_revision` / `parse_out` |
| `knowledge` | 分类目录、CCS 分类号、法规官方来源、别名 | 22 | 6,769 | 目录树、别名、CCS 记录 |
| `api` | 176 条 HTTP 路由 + 鉴权 + 线程池闸门 | 10 | 6,086 | —（入口） |
| （根 9 文件） | `config` 配置 / `exceptions` / `main` 入口 / `supervisor` 看门狗 / `text_utils` 文本清洗 / `figure_locator`+`figure_redraw`+`formula_locator` 图公式 / `middle_geo` 坐标 | 10 | 3,821 | — |
| `storage` | 连接池、schema、各仓储、备份、写队列 | 13 | 3,198 | `knowledge.db` |
| `llm` | 取证问答、外发审计、Jev 判断 | 7 | 1,883 | 外发审计日志 |
| `materials` | 参考资料项目：抓取/查重/定位/转正 | 7 | 1,715 | 材料表 |
| `exports` | 效力报告、研究报告、引用导出、Office 往返 | 7 | 1,505 | `exports/` 目录 |
| `retrieval` | **六路**混合检索 + RRF + 重排 | 5 | 1,270 | —（只读） |
| `quality` `settings` `verification` `query` `domain` `compliance` `vision` | 体检分级 / 凭据加密 / 引用核验 / 意图识别 / 数据模型 / 差距分析 / 图片反查 | 25 | 3,695 | 各一小块 |

**六路检索**（`retrieval/hybrid_engine.py`，权重 RRF）：

| 通道 | 权重 | 干什么 |
|---|---|---|
| A `exact` | 2.0 | 条款号精确匹配 |
| B `fts` | 1.0 | 全文检索（jieba 分词 + FTS5） |
| C `vec` | 1.0 | 向量近义 |
| D `modality` | 0.8 | 「可/应/必须」这类模态 |
| E `legal_element` | 0.8 | 法律要素（主体/行为/条件） |
| F `behavior_scope` | 1.2 | 行为范围 |

融合：`W / (RRF_K + rank + 1)`，`RRF_K = 60`，证据上限 `EVIDENCE_CAP = 8`。

### 2.2 引擎 HTTP 端点：176 条，全在 `/api/v1/` 下

按业务域（第 4 段路径）分：

| 业务域 | 条数 | 主要文件 |
|---|---|---|
| `kb`（知识库目录） | 24 | `routes_kb_folders.py` |
| `update`（巡检） | 22 | `routes_update.py` |
| `materials`（材料） | 18 | `routes_materials.py` |
| `documents`（文档） | 14 | `server.py` |
| `clauses`（条款） | 11 | `server.py` |
| `channels`（渠道） | 10 | `routes_channels.py` |
| `ingest`（入库） | 10 | `routes_ingest_preview.py`(6) + `routes_update.py`(4) |
| `laws`（法规源） | 10 | `routes_law.py` |
| `bookmark-folders` / `bookmarks` / `doc-bookmarks` | 15 | `server.py` |
| `report`（报告） | 6 | `routes_report.py` |
| `discover`（发现） | 4 | `routes_update.py` |
| `projects` | 4 | `server.py` |
| `settings` / `annotations` / `compliance` / `snapshots` / `data` | 各 3 | 分散 |
| `export` / `egress` / `diagnostics` | 各 2 | `server.py` |
| `health` / `compare` / `operation-log` / `aliases` / `chat` / `ks` / `vision` | 各 1 | `server.py` |

**完整 176 条清单**在 `.tmp/routes-full.txt`（`python .tmp/routes3.py` 可重生成）。
⚠ `.tmp/` 不入库，要长期留就抄进这里。

**路由分布本身是个问题**：`server.py` 一个文件 194 KB 装了 **107 条**端点，
其余 8 个 `routes_*.py` 分装 69 条。

### 2.3 包级依赖矩阵（实测）

**双向依赖 8 对**（A→B 且 B→A 都有 import）：

| 对 | A→B | B→A |
|---|---|---|
| `exports` ⇄ `knowledge` | 2 行 | 2 行 |
| `ingestion` ⇄ `knowledge` | 13 行 | 3 行 |
| `ingestion` ⇄ `quality` | 5 行 | 2 行 |
| `ingestion` ⇄ `storage` | 17 行 | 2 行 |
| `ingestion` ⇄ `update` | 1 行 | 1 行 |
| `knowledge` ⇄ `storage` | 15 行 | 3 行 |
| `knowledge` ⇄ `update` | 9 行 | 1 行 |
| `retrieval` ⇄ `storage` | 3 行 | 2 行 |

入度最高 `storage`（被引 120 行）；出度最高 `api`（164 行，入度 0 = 顶层入口）。

**⚠ 一处已更正的子代理结论**：`storage ⇄ retrieval` **不是模块级真环**。
`clause_repo` import 的是 `retrieval.embedder`，`hybrid_engine` import 的是
`storage.clause_repo` —— 不是同一模块对；`embedder.py` 只依赖 `config`/`exceptions`。
**实测两种 import 顺序都 OK**，「靠 import 顺序侥幸」超出证据。

---

## 3. 已经坏掉的地方（按严重度，都有现场）

### 3.1 【最严重】`resolve_clause` 跨标准误命中 —— **已拿到现场**

**现象**：`ks_resolve_clause("GBZ 188-2025", "5.22.3")` 返回
**`GB 6675.2-2025`（玩具安全标准）** 的条款正文，且 `httpStatus=200, ok=true, found=true,
legal_status=effective`。调用方**无法从响应里看出拿错了标准**。

**根因**（`src/core/storage/clause_repo.py` 的 `resolve_clause`，年份宽容兜底）：

```python
m = _re.search(r"(\d{4,5})", standard_no.strip())
...
WHERE cr.clause_number = ? AND dm.standard_no LIKE ?
(..., "%" + m.group(1) + "%")
```

这个正则想抽「标准号主体」，但**先命中 4 位年份**：

| 输入 | 实际抽到的 token | 应抽 |
|---|---|---|
| `GBZ 188-2025` | **2025** | 188 |
| `GBZ 1-2010` | **2010** | 1 |
| `GB 30871-2022` | 30871 ✔ | 30871 |

⇒ 兜底变成 `LIKE '%2025%'`，捞出所有 2025 年的标准。

**量化**（真库 8,983 部）：
- 兜底 token ≠ 标准号主体的：**36 部**
- 拿不存在的条款号试这 36 部：**9 部（25%）误命中别家标准**
- 受害清单：`GBZ 188-2025` / `GBZ 24-2025` / `GBZ 215-2025` / `GBZ 336-2025` /
  `GBZ 337-2025` / `GBZ 15-2024` / `GBZ 37-2024` / `GB/T 144-2024` / `GB/T 150.4-2024`
- **全是职业健康/安全类标准**，正是本项目核心领域

**为什么活到今天**：门禁的 pytest 跑在 `conftest` 的**空临时库**上，
这条 SQL 在空库上永远返回 None ⇒ 走不到误命中分支（见 §5.1）。

### 3.2 【已修】`channels.js` 判据恒假 ⇒ 双重响应

**病灶**：`plugin/src/channels.js` 的 `readBodyOr400`（L136）两个失败分支都
`return null`，**永不返回 `undefined`**；而 `POST /{id}/test-case` 那处写
`if (raw === undefined) return` ⇒ 判据恒假 ⇒ 400 已写出，却继续 `proxyWrite(..., null)`
写第二次响应。

**同文件对照**：PATCH（L283）判 `null` ✔、enabled（L309）判 `null` ✔，只有 test-case 判 `undefined` ✘。

**覆盖缺口**：`smoke-channels-routes.mjs` 原只测合法 body 转发，**非法 JSON 分支零覆盖**。

**已修**：判据改 `null`；smoke 加 `invokeRaw`（发原始字节）+ `makeRes` 记 `writes` 次数
+ 5 条钉（test-case / PATCH / enabled / 数组 / 标量），每条同时断言
「400 + 引擎零调用 + 响应只写一次」。**实测 36/36 通过**。

### 3.3 【已确认，未修】`standard_key` 丢前缀 ⇒ 不同标准撞车

```
standard_key("GB 188-2025")  == "188-2025"
standard_key("GBZ 188-2025") == "188-2025"      ← 撞车
```
实测 4 组全撞：`GB/GBZ`、`GB/GB-T`、`GB/GBJ`、`AQ/GB`。

**设计意图**（`text_utils.py:1355` 注释）：它专门用于「从页眉里抽比较键」，
在页眉场景下**这个判据是对的**（要保住表格里引用的别的标准）。

**问题在调用点**：`retrieval/hybrid_engine.py:341` 用它筛「提问点名的标准」。
有 `_std_key_hits_doc` 做词边界包含，缓解了**后缀**碰撞（`2033-2008` vs `12033-2008`），
**前缀碰撞（GB vs GBZ）它管不了**。**实际漏多少未实测，明确未做。**

### 3.4 【已确认，未修】引擎 LLM 取证调用失败

上一轮实测：`ks_answer` 每次返回 `llm_error=DeepSeek 取证调用失败: Connection error.`，
`verification.is_valid=false`，`derivation`/`conclusion` 为空。**本轮未复测。**

### 3.5 【已确认，未修】门禁的 `xfail` 假红

`pytest.xfail()` 在 junit 里**带 `<skipped>` 子节点** ⇒ 被收进 `skipNodeIds`
⇒ `run-gates.ps1:435` 的 `skipNodeIds.Count -ne $pytestSkipped` 当场不等 ⇒ **判红**。

⇒ 后果不是「隐身」，而是**合法的 xfail 会让门禁报「判据不可信」**。
实测证据（照抄第 388~436 行判据）：
```
pytest 汇总：1 passed, 1 skipped, 1 xfailed
四个正则：  passed=1 skipped=1 failed=None errors=None
junit：     全部 3 条，带 <skipped> 的 **2 条**（含 xfail 那条）
第 435 行： ⛔ junit 认出 skipped=2，汇总说 skipped=1 ⇒ 判据不可信 ⇒ 判红
```
**⚠ 子代理原文说「xfail 完全绕开棘轮、从总账消失」—— 这条已被我实测推翻。**

---

## 4. 重复实现（业主的头号关切）

### 4.1 尺子读数

```
① ruff（两档校准后）        1053
② pyscn 行块克隆组数        132   （信息项，不判红 —— 每次纯格式改动都会涨）
③ 缺模块 docstring          2
④ 跨目录同名 .py            0
⑤ 跨文件同函数体（α-等价）  13
```

扫描面 = `src` / `tests` / `scripts`。
`tools/gov-qa` **只测量不判红**（另一条线的活跃工作）：ruff 452、同函数体 32 组。

尺子：`scripts/check-repo-uniformity.py` + `scripts/uniformity-ast-dupes.py`，
天花板 `docs/uniformity/baseline.json`，首跑读数 `docs/uniformity/measure-01.json`。

### 4.2 ⑤ 的 13 组，逐组裁决

| # | 重复的东西 | 位置 | 裁决 |
|---|---|---|---|
| 1 | `_xlsx_header_style` | `exports/effect_report.py:325`、`update/announce.py:766`、`update/report.py:145` | **该合**（3 处逐字相同） |
| 2 | `_checksum` / `_file_sha256` | `storage/backup.py:43`、`update/data_package.py:97` | **该合**（后者注释自写「与 backup._checksum 同一口径」） |
| 3 | `_fetch_text` | `update/channels/mem_gov.py:103`、`mohurd.py:82` | **该合**（基类 `ChannelAdapter` 已有 `_fetch`） |
| 4 | `chunk_text` | `scripts/measure-classical-chinese-segmentation.py:82`、`measure-cross-language-fts.py:80` | 合（前者注释写「与另一把尺子逐字一致」） |
| 5 | `_db_stat` | `scripts/normalize-standard-no-slash.py:60`、`repair-missing-standard-no.py:55` | 合（一次性脚本，低优先） |
| 6–13 | `_write_pdf` / `synthetic_parser` / `_install` / `fake_reg` / `store_dir` / `QueryValueEx` / `data_dir` / `_load` | `tests/` 内 | **不合**（测试夹具各自独立更好，共享会把测试耦合） |

### 4.3 ⑤ 抓不到、人读发现的（更严重）

**A. 标准号归一有 11 个不同名字，散在 6 个模块**

| 名字 | 位置 | 干什么 |
|---|---|---|
| `canon_standard_no` | `text_utils.py:1280` | 比较用：全角→半角、折破折号、去空白斜杠、大写 |
| `store_standard_no` | `text_utils.py:1296` | **存储形**：只折全角 `/` `-`，其余不动 |
| `standard_key` | `text_utils.py:1358` | 压成 `号-年`（**丢前缀**，见 §3.3） |
| `standard_no_key` | `text_utils.py:1532` | 另一种比较键（**保留前缀**） |
| `clean_standard_name` | `text_utils.py:1954` | 从标准名里剥掉号前缀 |
| `clean_standard_no` | `knowledge/ccs_fetcher.py:250` | CCS 侧自己一份 |
| `norm_no` / `query_no` / `strip_year` | `update/channels/base.py:95/115/132` | 采集侧三件套 |
| `_norm_no` | `update/channel_test.py:47` | 第四份 |

**`text_utils.py:1283` 注释自写**：「与 `update.channels.base.norm_no` 同口径」
—— 作者**知道**有两份，选择不复用。该字段全仓 **1,472 处引用 / 152 文件**。

**B. `api/server.py` 两个函数与 `llm/ks_answer.py` 同名同职，但已分叉**

`_answer_confidence`（server.py:2559 / ks_answer.py:601）：
- 空证据：server **不特判**；ks_answer 特判 → `low`
- 字段名：server 用 `is_suspicious`/`type_confidence`；ks_answer 用 `_is_suspicious`/`_type_confidence`
- **实测后果**：把 server 形态数据喂给 ks_answer 版本 ⇒ 低可信证据被读成
  `{'level': 'high', 'reasons': ['核验通过且证据高可信']}`（**静默漏判**）

`_expand_title_clauses`（server.py:2525 / ks_answer.py:1113）：
- 子条款查询：server 裸调；ks_answer 有 `try/except`
- 长度阈值：server 硬编码 `80`；ks_answer 用常量 `TITLE_CLAUSE_MAXLEN`
- 取全文：`_fetch_clause` vs `fetch_full_clause`

**C. 这两个函数在 `create_app` 闭包内**（`create_app` 在 `server.py:278`，函数在 2525/2559）
⇒ 模块外 `ImportError` ⇒ **没法写单测** ⇒ 上述分叉**没有任何测试能发现**。

**D. `update/subscriptions.py` 注释称「单点同步，`auto_tag` 引用该处避免漂移」**
实测 `auto_tag.py` **没有 import `subscriptions`**（只 import `sqlite_db` / `text_utils`）
⇒ 两份硬编码领域词表。

**E. `exceptions.py` 10 个异常类里 4 个全仓零调用**：
`ConfigError` / `AuthError` / `RetrievalError` / `DuplicateDocumentError`（各仅定义处 1 处）。

**F. plugin 侧**（来自 `02-plugin.md`，主对话已验证 2 条）
- 宿主侧 18 条（S1–S18）、客户端 16 条（C1–C16）、脚本辅助 6 类 = **40 条**
- `api.ts` 里 **40 处逐字相同**的 401 抛错；**80 处**手写 `if (!res.ok)`；统一解包器 `ksJson` 只用了 25 处
- `KsKnowledgePage.tsx` 页壳**手写 4 遍**；面包屑手写 88 行，而 `kbListUi.tsx` 已有 55 行的 `KsCrumb`
- `smoke-ui-scale.mjs` 尺度棘轮**只扫 `ksGuideStyles.ts` 一个文件**；`tsx` 里 230 处内联
  `fontSize` 字面量、79 个局部样式常量、15 组跨文件逐字相同的 style 全在射程外
- **客户端 40 个端点绕过宿主代理**：`api.ts` 里 46 处 `http://127.0.0.1:${port}/…` 直连；
  `/api/v1/kb/*`(16)、`bookmarks*`(8)、`documents*`(6) 等在宿主 `src/` 里**引用数 0**。
  这与 `materials_routes.js` 头注「client 拿不到引擎 token，所以必须由 host 代理」
  **直接冲突**（token 就在浏览器内存里）⇒ **两套信任模型并存**

---

## 5. 门禁与验证能力的真实边界

### 5.1 conftest 布的是空库 —— **3,076 条用例里跑在真库上的是 0 条**

`tests/conftest.py` 的 `_isolate_data_dir` 是 session 级 autouse，把 `KS_DATA_DIR`
换成 `tempfile.mkdtemp()`，**无开关**。`db` fixture 只建表不填数据。

⇒ **所有依赖真实语料的判据在门禁里结构上做不到**。这解释了 §3.1 为什么能活到今天。

### 5.2 棘轮能被绕过吗（我实测的结论）

| 口子 | 子代理说法 | 我的复核 |
|---|---|---|
| A. `-UpdateBaseline` 在红的跑里也写基线 | 成立（读代码） | **成立**（`run-gates.ps1:614` 不受 `$why.Count` 约束），但受 `$null -ne $pytestPassed` 罩着。**未实跑** |
| B. 多加 skip 骗过 | 不能直接骗过 | **成立**：`run-gates.ps1:572` 的 `$newIds` 白名单判据会当场红 |
| C. `xfail` 完全隐身 | 隐身 | **❌ 推翻**：是**假红**，不是隐身（见 §3.5） |
| D. 口径没生效时判据变松 | 成立 | **成立**：`totalForRatchet = totalRan`（不减），补偿是「本跑不许记基线」 |

### 5.3 恒真断言 6 处（实测原文，永不红）

| 文件:行 | 原文 |
|---|---|
| `tests/test_appendix_split.py:212` | `assert _CLAUSE_NO_APPENDIX_RE.search("5.2.1 条款内容") is None or True` |
| `tests/test_patches.py:60` | `assert not any(...) or True  # 修正前可能不命中` |
| `tests/test_phase4.py:59` | `assert ids.index("q2") <= ids.index("q1") or True` |
| `tests/test_phase6.py:195` | `assert "安全监护" in expand_with_alias("安全监护") or True` |
| `tests/test_reranker.py:127` | `assert not hybrid_engine._last_rerank_debug.get("rerank_offline") is False or True` |
| `tests/test_research_report.py:241` | `assert "⚠锚点未验证" in md.split("三、依据")[0] or True` |

`assert True` / `try: ... except: pass` 包住断言：**0 处**（实测）。

### 5.4 `src/core` 零测试模块 8 个

`figure_redraw` / `formula_locator` / `mohurd` / `proxy_rotate` / `routes_law` /
`routes_settings` / `routes_update` / `span_verify`。
7 个是活代码（被 `server.py`/`pipeline.py` 调用），只有 `proxy_rotate` 全仓仅剩自身模块名。

**⚠「间接跑到」≠「被测」**：没有一条用例是为它们写的。

### 5.5 `tools/gov-qa` 634 MB 数据受版本控制

`tools/gov-qa/data`：686 文件 / 644.2 MB（594 个 `.jsonl` + 90 个 `.cursor`），
`.gitignore` 不排除它。**这是 `harvest.py` 可再生的采集产物。**
**是否含个人信息：未读内容，明确未做。**

---

## 6. 文档体系

### 6.1 顶层 29 份（不是 30）

`docs/` 顶层 **29 份 md**，其中 **28 受跟踪**；
`EXTERNAL-REVIEW-ARCHITECTURE-v4.md` **未跟踪**，而 `docs/README.md` 标它 ✅
—— **文档与事实不一致**。

### 6.2 九组冲突（子代理给数，未逐组复核）

| 冲突 | 数字 A | 数字 B | 实测 |
|---|---|---|---|
| 表数量 | 34 / 38 / 60 / 62 | — | **44** |
| 语料规模 | 6,797 | 8,983 | — |
| 渠道数 | 131 / 280 / 286 | — | — |
| 子系统数 | 19 / 18 / 16 | — | **16**（+9 根文件） |
| 总纲状态 | 「已暂停」 | 010/013 仍在施工 | — |
| `INDEX.md` | 210 | 磁盘 214 | — |
| `EXTERNAL-REVIEW-v4` | README 标 ✅ | 实为未跟踪 | **属实** |
| `BROKEN-LINKS` | 「0 处」 | — | — |
| 「接手先读这一份」 | wiki / HANDOVER / ENCYCLOPEDIA **三处都说自己** | — | — |

### 6.3 `specs/` 编号撞车 —— **核实为真，两组都真**

- `009-standard-no-ocr-suffix`（10-12 10:31 建）vs `009-turn-evidence-ui`（14:47 建）
- `010-real-question-ruler`（10:59）vs `010-turn-tab-fixes`（16:35）

原因：后建的人没查已有目录；两条线用两套提交前缀（`spec-009` vs `UI/spec009`）；
`.specify/scripts/powershell/create-new-feature.ps1` **本有撞号自动往上找空号的逻辑**，
说明这两个目录**没走该脚本**。`specs/` 无 README、`.specify/feature.json` 只记当前一个目录
⇒ 撞号无登记处。代价：「spec 009」在开发史与 `PLAN-REAL-QUESTION-RULER` 里指两个不同特性。

### 6.4 `scripts/` 68 个：一次性 18 个，其中 **9 个被 pytest 按路径钉住**

`Path(__file__).resolve().parents[1]/"scripts"/…` + `spec_from_file_location`
⇒ **不能整体归档**。另 9 个无测试无门禁引用（`map-dsh-icons` / `fix-dsh-icon-names`
是全仓零引用的唯一一对）。
`measure-*` **11 个**（不是 10），10 个不落盘、读数手抄进 `RETRIEVAL-LONG-RANGE-PLAN`；
只有 4 个有测试钉住尺子本身。

---

## 7. 尺子本身（怎么用、怎么信）

```powershell
# 判据模式（exit 0 = 全过，1 = 有回归或未下调）
.venv\Scripts\python.exe scripts\check-repo-uniformity.py

# 只看读数表
.venv\Scripts\python.exe scripts\check-repo-uniformity.py --report

# 降了之后写天花板（零松弛：天花板必须 == 实测值）
.venv\Scripts\python.exe scripts\check-repo-uniformity.py --write-baseline

# 验幂等（同一棵树跑两次同一个数）
.venv\Scripts\python.exe scripts\check-repo-uniformity.py --repeat-check

# 验判据真的会拦（拿坏样本确认 ③④⑤ 抓得到）
.venv\Scripts\python.exe scripts\check-repo-uniformity.py --selftest
```

**尺子四条自证**（缺一条就不可信）：
1. 一条命令出全部读数，exit code 即判据
2. 每条指标能指回权威源（文件头表格逐条列了出处）
3. 工具不可用时 **FAIL 不跳过**（`metric_ruff` 抛 `RuntimeError`）
4. 读数幂等（`--repeat-check` 实测两次一致）

**两条判据校准（先量后定，不是放水）**：
- `E501` **两档**：代码行 88 显示列 / 散文行 120 显示列。
  理由：5,096 条里 **4,684 条是中文散文**（88 列 = 44 汉字），按 88 判会把
  **判断依据本身**判成违规；改 120 档后散文行仍剩 **64 条** ⇒ 判据仍有效。
- `N802` **退出判据**：492 条里 **452 条是中文测试名**（`test_隐藏文档被排除`），
  19 条是 Windows API mock（必须同名），21 条是刻意强调写法。只打印不判红。

**⚠ 中文代码库必须用显示列**（`unicodedata.east_asian_width`），不能用 `len()`。
实测：50 个汉字 = 102 列（判超），50 个字母 = 52 列（不判）。

---

## 8. 本轮真跑记录（实测，不是推断）

| 跑的是什么 | 结果 | 耗时 |
|---|---|---|
| 完整 pytest（`-q -rs`，含 tools/gov-qa） | **1 failed / 3067 passed / 8 skipped** | 1,144.92s（19 分钟） |
| 上述失败原因 | **我自己的临时文件** `.tmp/calibrate.py` 被 `test_credentials_namespace.py` 全仓扫描抓到 | — |
| 删掉临时文件后单跑该文件 | **34 passed** | 34.64s |
| `node plugin/scripts/smoke-channels-routes.mjs` | **36/36 PASS**（含新加 5 条钉） | — |
| `python scripts/check-repo-uniformity.py --selftest` | **PASS**（③④⑤ 都抓到负例） | — |
| `python scripts/check-repo-uniformity.py --repeat-check` | **PASS**（两次读数一致） | — |
| `python scripts/uniformity-ast-dupes.py --selftest` | **PASS**（正例命中、两个反例未误判） | — |

**⚠ 基线数字待对账（明确未做）**：
本轮实测 `passed=3067`；基线记 `pytest_passed=3057` / `pytest_total=3065` /
`untracked_excluded=5`，而**实际未跟踪测试文件贡献 11 条**
（`test_jev_cn_baseline` 5 + `test_llm_empty_retry` 3 + `test_modality_window_false_positive` 3）。
按门禁口径：`totalRan=3075 − 11 = 3064 < 3065` ⇒ **会判红，差 1**。
**这 1 条差在哪，未查。**

---

## 9. 明确未做 / 未验证（不许当成做过了）

| 事项 | 原因 |
|---|---|
| `-UpdateBaseline` 在红的跑里到底写不写基线 | 要跑 `-Full` 且会写基线，本轮不做 |
| `standard_key` 前缀碰撞在检索里实际漏多少 | 要在真库上跑检索对照，未做 |
| `tools/gov-qa/data` 634 MB 是否含个人信息 | 只看了文件名与条数，**没读内容** |
| `plugin/src/*.js` 与 56 个 mjs 的静态类型面 | 没有任何静态类型门禁（`tsc` 只编 `plugin/client`），未逐个数 |
| `src/core` 8 个零测试模块的间接覆盖有多少 | 要 `--cov` 跑完整 pytest |
| `tests/` 3 个未跟踪测试文件的来历 | 没有 commit 就没有可查的动机 |
| 引擎 LLM 取证调用失败（§3.4） | 本轮未复测 |
| `ui-render-shot.mjs`（328 KB / 4,517 行）内部结构 | 未读 |
| `KsEvidenceTab`（2,834 行）里还有多少可抽纯函数 | 未读 |
| 真库真实规模（8,983 部 / 663,634 条） | 上一轮实测，本轮未重核 |
| 基线差的那 1 条（§8） | 未查 |

---

## 10. 四份原始报告（按需深查）

| 文件 | 内容 | 可信度 |
|---|---|---|
| [`00-review-of-surveys.md`](00-review-of-surveys.md) | **主对话复核记录**：10 条已核实 / 2 条推翻 / 2 条更正 | ★★★ 先看这个 |
| [`01-core.md`](01-core.md) | `src/core` 16 子系统 + 9 根文件逐文件职责、入口、依赖、写什么 | ★★ 骨架可信，具体结论抽查过 |
| [`02-plugin.md`](02-plugin.md) | `plugin/` 宿主 19 js + 客户端 31 tsx + 56 mjs；40 条重复；端点清单 | ★★ 同上 |
| [`03-docs-specs-scripts.md`](03-docs-specs-scripts.md) | 29 顶层文档 + 9 组冲突 + specs 15 个 + scripts 68 个 | ★★ 同上 |
| [`04-tests-tools-gates.md`](04-tests-tools-gates.md) | tests 结构 + 覆盖率缺口 + 门禁 12 步 + 棘轮绕过分析 | ★★★ 唯一被推翻的是 xfail 那条（见 §3.5） |

**⚠ 引用子代理报告时先看 `00-review-of-surveys.md`**：
`04` 的「xfail 隐身」已被实测推翻；`01` 的「storage ⇄ retrieval 靠 import 顺序侥幸」
已被实测更正为「不构成模块级真环」。

---

## 11. 术语表（新对话最容易卡在这些词上）

| 词 | 在这个仓里具体指什么 |
|---|---|
| **条款** / clause | 标准或法规里带编号的一段原文（`5.22.1`）。一个文档切成几百到几千条 |
| **证据** / evidence | 检索出来、准备给大模型看的条款。上限 8 条 |
| **三段式** | `依据`（原文条款）→ `推导`（怎么从原文得出）→ `结论`。**不许跳步** |
| **取证** / forensic | 一种问答模式：必须先用库拿原文、必须给可点链接、核验不过必须如实说 |
| **效力** / legal_status | 一条条款现在算不算数：`effective`（现行）/ `superseded`（被代替）/ `withdrawn`（已废止）/ `upcoming`（即将实施）/ `reference`（仅参考）/ `NULL`（未核验） |
| **六路检索** | `exact` / `fts` / `vec` / `modality` / `legal_element` / `behavior_scope` 六个通道，按 RRF 融合 |
| **RRF** | 把多个通道的排名融合成一个排名的算法。`W / (60 + rank + 1)` |
| **通道** / channel | ⚠ **两个意思**：① 检索通道（上面六路）；② 采集通道（`update/channels/`，去 13 个官网抓数据的适配器）。**看上下文** |
| **巡检** / update | 定期去官网查「库里的标准有没有新版/废止/公告」 |
| **水位** / watermark | 巡检记的「上次抓到哪一条」，避免重复抓 |
| **材料** / material | 用户自己上传/采集的参考资料（财报、公司制度），评审通过后才能进作答 |
| **T0~T4** | 材料来源可信层级。T3 = 仅线索，不得单独支撑结论 |
| **棘轮** / ratchet | 测试基线只涨不跌。`gates-baseline.json` 记天花板 |
| **门禁** / gate | `scripts/run-gates.ps1` 那一串检查。**以退出码为准** |
| **spec** | Spec Kit 工作区 `specs/NNN-*/`，装规格/计划/任务。**不是产品文档** |
| **DSH** | DeepSeek Harness，宿主程序。本仓是它的一个插件 |
| **ctx / cordis** | DSH 的插件框架。`ctx.tools.register()` 注册模型工具，`ctx.effect()` 注册副作用 |
| **冒烟** / smoke | `plugin/scripts/smoke-*.mjs`，44 套，验宿主侧行为 |
| **`/ks/*`** | 插件注册给宿主的 HTTP 路由（49 条）。**与引擎的 `/api/v1/*` 是两套** |

---

## 12. 下一步（按「最大且可验证」排序，不是最容易）

1. **`resolve_clause` 年份兜底**（§3.1）—— 已拿到现场、已量化、影响核心领域。
   修法：正则改成先抽「字母前缀 + 数字主体」，抽不到就不兜底。
   判据：那 9 部受害标准必须全部从「误命中」变成「404」，同时 4 条合法年份宽容用例仍要过。
2. **`_answer_confidence` / `_expand_title_clauses` 两处分叉**（§4.3B）——
   先定字段名再合并；合并前必须先让它们**能被单测**（移出 `create_app` 闭包）。
3. **标准号归一 11 个名字收敛**（§4.3A）—— 先出对应表，逐条判定哪个是唯一真源。
4. **⑤ 的 3 组 `src/core` 重复合并**（§4.2 #1#2#3）—— 低风险、可验证。
5. **门禁 `xfail` 假红**（§3.5）—— 要么识别它、要么在脚本里禁用并写明。
