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

## 0. 从零到能跑（新人第一步，**别跳过**）

> 这一节回答「我拿到这个仓，怎么让它跑起来」。**没有这一节，后面 12 节都用不上。**

### 0.0 前置：版本与平台

| 项 | 要求 | 出处 |
|---|---|---|
| Python | **≥ 3.12** | `pyproject.toml` `requires-python` |
| Node | **≥ 20** | `plugin/package.json` `engines.node` |
| 平台 | **只有 Windows 被验证过** —— 路径写法（`.venv\Scripts\python.exe`）、`pwsh`、`%TEMP%`、盘符、Chromium/Edge 全是 Windows。macOS/Linux **没有任何证据**支持 | 全仓 |

### 0.1 三样东西不在版本控制里 —— **这是最容易卡死的地方**

`var/data/`（72.32 GB）、`var/models/`（6.87 GB）、`.venv/`（5.06 GB）**都被 `.gitignore` 盖住**。
⇒ **新克隆下来是空库、没模型、没环境**，产品什么都不做。

| 缺什么 | 症状 | 怎么补 |
|---|---|---|
| `var/data/` | 引擎能起，但库里 0 篇文档，问什么都答"库里没有" | **见下方「⚠ 数据获取是循环引用」** |
| `var/models/` | 检索退化成只剩全文检索；PDF 解析不可用 | **见下方「模型怎么拿」** |
| `.venv/` | `python -m src.core.main` 直接报找不到模块 | `python -m venv .venv` + `.venv\Scripts\pip install -e .` |

**⚠ 数据获取是循环引用（本仓当前的真实缺口，未解决）**：

本文档能给的只有两条路，**而两条都指向新克隆的人手上没有的东西**：
- 路 A「从旧副本拷回」—— 新克隆的人**没有旧副本**；
- 路 B「从 `var/data/backups/` 的 13 个快照恢复」—— `backups/` **就在 `var/data/` 里面**，
  而 `var/data` 正是缺的那个 ⇒ **循环**。

⇒ **结论：新环境目前拿不到生产库，这一步没有可执行方案。**
这不是文档漏写，是**仓库本身缺一个"数据从哪来"的出口**（没有导出包、没有种子库、没有下载地址）。
**要补它需要拍板**，三条候选（**都未实施**）：
1. 把 `var/data/backups/` 里最新的一个快照做成独立可分发的包（体积约 1~2 GB）；
2. 建一个**缩小版种子库**（几百篇代表性文档）进版本控制，够跑通全流程与多数判据；
3. 写一个从零抓取/入库的脚本链（`tools/gov-qa` 那边有采集能力，但抓的是政务问答不是标准全文）。

**只想验证代码逻辑**可以跳过这一步：pytest 与门禁在空库上跑，能验大部分逻辑。

**模型怎么拿（本仓也未给可执行步骤）**：
`var/models/` 下是两组模型 —— `ks/`（bge-small-zh 向量 + bge-reranker-base 重排）
与 `mineru/{pipeline,vlm}/`（PDF 解析）。文档能确认的是：
- 插件启动时会自动生成 `var/models/mineru.json`（`model-source: local` + 两个子目录路径），
  **所以配置文件不用手写**；
- MinerU 的模型目录结构是 `pipeline/` 与 `vlm/` 两个子目录。
**但没有**：下载地址、命令、版本号、授权方式。**明确未做。**

**装依赖时要装哪些 extras**（`pyproject.toml` 里定义的）：

| extra | 装什么 | 不装会怎样 |
|---|---|---|
| `parser` | `mineru>=2.0`（PDF 深度解析） | 解析 PDF 不可用；已有 `parse_out` 的库仍能查 |
| `vision` | `numpy` / `opencv-python` / `rapidocr-onnxruntime`（图形重绘） | 流程图重绘自动降级成 PNG 截图 |
| `proc` | `psutil`（进程管理） | `parser_worker` / `deep_server` 的 psutil 调用降级 |
| `wincom` | `pywin32`（Word COM 往返） | Office 编辑往返不可用（仅 Windows） |
| `dev` | `pytest` / `pytest-timeout` / `mypy` | **跑不了测试与 mypy 门禁** |

⇒ **要跑测试就必须装 `dev`**（§0.4 让你跑 pytest，这不是"可选"）。

**⚠ 只想先看看代码、不跑数据**：可以只建 `.venv` + 装 `plugin/node_modules`，
跑 `pytest` 与门禁（**它们确定在临时空库上跑，已实测**）。但**冒烟碰不碰真库未验证** ——
见 §0.3，别在装着生产库的机器上直接跑 44 套冒烟。
任何「检索答得对不对」的验证都必须在真库上做。

### 0.2 引擎怎么起、端口在哪、怎么探活

**平时不需要手动起** —— 插件按需懒拉。要**手动**起（调试引擎侧问题时）：

```powershell
.venv\Scripts\python.exe -m src.core.main
```

它做这几件事（`src/core/api/server.py::run()`）：

1. `bind_random()` —— 绑 `127.0.0.1:0` 拿一个**随机空闲端口**，并生成一次性 token
2. 往 **stdout** 打两行：`KNOWLEDGE_STATION_PORT=<端口>` / `KNOWLEDGE_STATION_TOKEN=<token>`
3. 把同一份信息写进 **`<数据目录>/engine.session.json`**（字段：`port` / `token` / `pid` / `started_at`）
4. `uvicorn.run(app, host="127.0.0.1", port=<随机端口>, log_level="warning")`

⇒ **端口不是固定的**，要从上面两处读。插件侧读的是 `engine.session.json`
（`plugin/src/engine.js::sessionFilePath`，与引擎同一口径）。

**探活**：`GET http://127.0.0.1:<port>/api/v1/health`，带 `Authorization: Bearer <token>`。
或者直接调模型工具 `ks_ping`（它就是这个的封装）。

**日志**：引擎走 uvicorn `log_level="warning"` ⇒ 正常运行时**几乎不打日志**。
排查要看的是：① 启动时那两行 stdout；② `engine.session.json`；③ 门禁日志
`%TEMP%\ks-gates-logs\`（只有跑门禁时才有）。

### 0.3 跑那些检查会不会写坏生产库

**这是不可逆风险，先说清**：

| 命令 | 碰不碰 `var/data` | 依据 |
|---|---|---|
| `pytest` | **不碰**。`tests/conftest.py` 的 `_isolate_data_dir` 把 `KS_DATA_DIR` 换成临时目录（session 级 autouse，无开关） | 实测（§6.1） |
| `run-gates.ps1 -Quick/-Full` | **不碰**。它自己也布一个临时 `KS_DATA_DIR`，跑完删掉；失败时留着供排查 | `run-gates.ps1` 的 `$ownDataDir` 段 |
| `npm run smoke`（44 套） | **未逐套确认**。冒烟是宿主侧的，多数用假引擎；但**没有任何一份文档声明它们全部不碰真库** ⇒ **未验证，别假设安全** | 明确未做 |
| `scripts/check-repo-uniformity.py` | **不碰**。纯静态扫描 | 实测 |

### 0.4 改完代码怎么验

```powershell
# 1) 最小证据（改动面）
pwsh -File scripts/run-gates.ps1 -Quick

# 2) 全量（收工前；pytest 一步就要 14~19 分钟）
pwsh -File scripts/run-gates.ps1 -Full

# 3) 只验某一面
.venv\Scripts\python.exe -m mypy                                    # 引擎类型
npx tsc --noEmit -p plugin/client                                    # 客户端类型
node plugin/scripts/smoke-channels-routes.mjs                        # 单个冒烟
.venv\Scripts\python.exe scripts/check-repo-uniformity.py            # 重复/违规读数

# 4) 改了 plugin/client/*.tsx 必须重编产物（否则 smoke-build-purity 会红）
node plugin/scripts/build-client.mjs
```

**退出码是唯一判据**。`3` = 有人在跑门禁（不是失败）。

### 0.5 提交与留痕

- **每轮 = 小提交 + 快照**：`& .\scripts\snapshot-project.ps1 -Label <短名>`
- 提交消息写清「改了什么 / 为什么 / 边界」
- **一个事实一个归属层**：详细记录写进它的归属文档，别处只链接

---

## 1. 这个仓的硬规矩（不做会当场踩）

### 1.1 一条命令跑门禁，以退出码为准

```powershell
pwsh -File scripts/run-gates.ps1 -Quick     # 改动面（tsc / mypy / 命令契约 / 全链 smoke）
pwsh -File scripts/run-gates.ps1 -Full      # 全量（+ pytest / uvicorn / 真宿主 e2e / gov-qa 三条）
```

- **一次只跑一个**。脚本用锁文件把并发变成当场报错，**退出码 3 = 有人在跑，不是失败**。
- `-Full` 实测耗时：pytest 一步就要 **19 分钟**（3,076 条用例）。
- 跑完的汇总固定落在 `%TEMP%\ks-gates-last.txt`；每一步的完整日志在
  `%TEMP%\ks-gates-logs\<时间戳>-<步骤名>.log`。

### 1.2 测试基线只涨不跌（棘轮）

`scripts/gates-baseline.json` 记的是**下限**（不是上限）：测试条数不许低于它。
（⚠ 本文件另有一个**上限**意义上的"天花板"在 §5/§8 的重复指标基线
`docs/uniformity/baseline.json`。**两个文件方向相反，别混**：

| 文件 | 管什么 | 方向 |
|---|---|---|
| `scripts/gates-baseline.json` | 测试条数 | **下限**：低于它判红 |
| `docs/uniformity/baseline.json` | 重复/违规条数 | **上限**：高于它判红 |

）

公式（`run-gates.ps1`）：

```
totalRan        = passed + skipped + failed + errors     ← 四项都要算
totalForRatchet = totalRan − untracked_excluded           （口径生效时）
判红条件        = totalForRatchet < baseline.pytest_total
```

**⚠ 两条实测陷阱**：
1. **`failed` / `errors` 必须算进总账**。漏算会把"2 条失败"误报成"少收集了 2 条"，判据方向反了。
   （**我自己在这上面错过一次**，见 §9 的留痕。）
2. **记账也用棘轮口径**（减掉未跟踪用例），否则把未跟踪文件的用例钉进基线，
   那份文件一被删就假红；有人手工调低基线去躲 ⇒ 造出"可静默删用例"的余量。

### 1.3 临时文件必须放 `.tmp/`（2026-10-23 实测踩过）

`tests/test_credentials_namespace.py` 有一条**全仓源码扫描**，射程覆盖
`src` / `scripts` / `plugin` / 根目录 / `.ps1/.bat/.cmd`，排除 `node_modules` / `.venv` /
`var` / `tests` 等，**但不排除 `.tmp/`**（`.gitignore` 原来只忽略 `.tmp-*` 这种带后缀的名字）。

**实测后果**：我在 `.tmp/` 放了个临时探针脚本，里面含 `SetValueEx` 字样
⇒ 那条测试当场判红：`源码里仍有系统层写入: .tmp/calibrate.py:104`。
⇒ 已在 `.gitignore` 补 `.tmp/`。**但注意**：`.gitignore` 管不住这条测试（它扫磁盘不扫 git），
所以临时文件里**不许出现** `SetValueEx` / `os.environ[` / `setx ` / `putenv` /
`SetEnvironmentVariable` / `environ.setdefault` 这些字样。

### 1.4 便携是硬约束（业主 2026-10-17 亲定）

**代码里不许写死绝对路径**。路径一律运行时推导：
- 插件从自身位置往上找仓根（`plugin/src/engine.js` 的 `findEngineRoot`，认 `src/core/main.py`）
- venv 底座自愈（`healVenvHome()` 改写 `pyvenv.cfg` 的 `home`；Windows venv **不带标准库**，整包换盘符就不可用）
- 模型在 `var/models/`、数据在 `var/data/`（都可用 `KS_MODELS_DIR` / `KS_DATA_DIR` 覆盖）

**⚠ 发现写死路径时不要"把旧值换成新值"** —— 那只是把同一个病推迟到下次拷贝。
判据见 [`../PORTABILITY.md`](../PORTABILITY.md)。

### 1.5 说话规矩（业主亲下的最高指令）

要业主确认时必须**直白朴实**：说这东西能做什么、点下去会发生什么、代价是什么。
**禁止**表名/接口名/架构/抽象/复用/解耦/重构/幂等这类词，**禁止**打比方。
**不许迎合**：同意之前先找反证；业主给的前提也要核；错了只认错的那条。

---

## 2. 项目是什么

**KnowledgeStation** = 本地跑的中文国标与法律法规知识工作站。

用户问一句合规问题（例：「甲醇作业要不要做职业健康检查」），它做三件事：
1. 在**本地库**里找相关条款原文（不是调云端搜索）
2. 把找到的原文 + 问题交给大模型，产出**三段式**答案：`依据` → `推导` → `结论`
3. 每条依据带**可点的原文链接**（能翻到 PDF 的那一页那个位置）

**它跟普通问答的区别**：结论必须能追到原文。库里没有就明说"库里没有"，
不许编；引用了不在证据里的条款会被拦下来并如实告知。

### 2.1 两个进程

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


### 2.2 数据在哪（**绝对不要删**）

```
var/data/                          72.32 GB（合计，实测）
├── parse_out/                     34.95 GB  —— 解析产物（条款里的图、公式从这里取，被 src/core/api/server.py 14 处读取）
├── backups/                       23.31 GB  —— 13 个快照
├── database/knowledge.db          13.82 GB  —— 生产库（含 WAL/索引文件；单个 .db 文件 2.90 GB）
│                                  8,983 部标准/法规 / 663,634 条条款 / 1,842,493 条位置片段（实测）
└── 其余（coding-guidelines / debug_loop / materials / law_source / templates 等）合计约 0.2 GB

var/models/                        6.87 GB（合计，实测）
├── ks/                            2.28 GB  —— 向量与重排模型（bge-small-zh / bge-reranker-base）
└── mineru/{pipeline,vlm}/         4.59 GB  —— PDF 解析模型（MinerU 2.x）

.venv/                             5.06 GB  —— Python 环境（48,040 文件）
```

**⚠ 三者的可重建性不同，别一律说"不能删"**：

| 目录 | 删了会怎样 | 怎么回来 |
|---|---|---|
| `var/data` | **数据全没** —— 它是生产库本身，不是测试数据 | 从 `var/data/backups/` 的 13 个快照恢复，或从旧副本拷回（`README.md` §便携 有写：「从还在的旧副本拷回。引擎会如实显示空库」）。**没有自动重下** |
| `var/models` | 检索/解析不能用（向量、重排、PDF 解析都缺） | 重新下载（需联网）；`mineru.json` 由插件启动时自动生成 |
| `.venv` | Python 跑不起来 | 重建虚拟环境 + `pip install -e .`，约十几分钟 |

`var/data` **就是生产库本身**，不是测试数据。判据：随机抽样都是真 GB 标准，
只有 190/8,983 个文档名含「测试」字样。

### 2.3 6 个模型工具（agent 能调的）

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

## 3. 代码骨架（实测）

```
zcode/                                     HEAD 64f37707
├── src/core/          Python 引擎    155 py / 45,439 行 / 16 子系统 + 10 根文件
├── plugin/            DSH 插件       19 js (9,968 行) + 31 tsx/ts (1,167 KB) + 56 mjs
├── tests/             pytest         181 py / 3,076 条用例
├── scripts/           工具脚本       68 个（55 py / 9 ps1 / 4 mjs）
├── tools/gov-qa/      **另一条线**   3,427 文件 / 948.8 MB（634 MB 数据受版本控制）
├── docs/              文档           29 顶层 + archive 46 / research 97 / verify-briefs 21 / wiki 21
├── specs/             Spec Kit      15 个（**两组编号撞车**，见 §7.3）
└── var/               本地产物       模型 6.87 GB + 数据 72.32 GB（**不受版本控制**）
```

### 3.1 `src/core` 16 个子系统（数字已对账：合计 = 155 文件 / 45,439 行）

| 子系统 | 干什么 | 文件 | 行数 | 写什么 |
|---|---|---|---|---|
| `update` | 去 13 个官网查标准/法规有没有新版、废止、公告 | 36 | 8,811 | 渠道表、公告表、检查批次 |
| `ingestion` | 把 PDF/docx/网页文本切成条款写进库 | 20 | 7,684 | `doc_meta` / `clause_revision` / `parse_out` |
| `knowledge` | 分类目录、CCS 分类号、法规官方来源、别名 | 22 | 6,769 | 目录树、别名、CCS 记录 |
| `api` | 176 条 HTTP 路由 + 鉴权 + 线程池闸门 | 10 | 6,086 | —（入口） |
| `storage` | 连接池、schema、各仓储、备份、写队列 | 13 | 3,198 | `knowledge.db` |
| `llm` | 取证问答、外发审计、Jev 判断 | 7 | 1,883 | 外发审计日志 |
| `materials` | 参考资料项目：抓取/查重/定位/转正 | 7 | 1,715 | 材料表 |
| `exports` | 效力报告、研究报告、引用导出、Office 往返 | 7 | 1,505 | `exports/` 目录 |
| `retrieval` | **六路**混合检索 + RRF + 重排 | 5 | 1,270 | —（只读） |
| `quality` | 体检分级 | 5 | 826 | 质量规则 |
| `settings` | 设置项与凭据加密 | 3 | 684 | `settings` 表 |
| `verification` | 引用核验（答案里的条款/数值/模态是否越界） | 3 | 427 | —（只读） |
| `query` | 意图识别（判断问题该走哪条路） | 1 | 280 | —（只读） |
| `domain` | 数据模型（`ClauseRevisionModel` 等） | 2 | 186 | —（纯类型） |
| `compliance` | 差距分析 | 2 | 177 | —（只读） |
| `vision` | 图片反查 | 2 | 117 | —（只读） |
| **子目录合计** | | **145** | **41,618** | |
| **根文件**（10 个，见下） | `config` 配置 / `exceptions` / `main` 入口 / `supervisor` 看门狗 / `text_utils` 文本清洗 / `figure_locator`+`figure_redraw`+`formula_locator` 图公式 / `middle_geo` 坐标 / `__init__` | **10** | **3,821** | |
| **总计** | | **155** | **45,439** | |

**根文件 10 个的准确名字**（别写"9 个"）：
`__init__.py` `config.py` `exceptions.py` `figure_locator.py` `figure_redraw.py`
`formula_locator.py` `main.py` `middle_geo.py` `supervisor.py` `text_utils.py`

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

### 3.2 引擎 HTTP 端点：176 条，全在 `/api/v1/` 下

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

### 3.3 包级依赖矩阵（实测）

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

## 4. 已经坏掉的地方

### 4.0 两套排序，先说清（避免与 `wiki/architecture.md` 看起来冲突）

**本节按「证据充分度」排（有现场的先写），不是按「产品影响面」排。**

| 按**产品影响**排（`wiki/architecture.md` §四 用这个，**要动手看那张**） | 按**证据充分度**排（本节用这个） |
|---|---|
| 第 1：§4.4 引擎 LLM 取证调用失败（**主输出整体为空**，但状态未知） | 第 1：§4.1 `resolve_clause` 误命中（**有现场、有量化**） |
| 第 2：§4.1 `resolve_clause` 跨标准误命中 | 第 2：§4.2 `channels.js`（**已修**） |
| 第 3~8：见 `wiki/architecture.md` 的 8 行缺陷表 | 第 3~5：§4.3 / §4.4 / §4.5 |

**为什么故意不一致**：每条的证据强度不同 —— §4.1 有复现现场，§4.4 只是上一轮的观察。
混在一起排会让读者以为 §4.4 的证据也那么硬。
**⇒ 要按严重度动手，看 `wiki/architecture.md` §四那张 8 行表。**

### 4.1 【证据最充分】`resolve_clause` 跨标准误命中 —— **已拿到现场**

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
这条 SQL 在空库上永远返回 None ⇒ 走不到误命中分支（见 §6.1）。

### 4.2 【已修】`channels.js` 判据恒假 ⇒ 双重响应

**病灶**：`plugin/src/channels.js` 的 `readBodyOr400`（L136）两个失败分支都
`return null`，**永不返回 `undefined`**；而 `POST /{id}/test-case` 那处写
`if (raw === undefined) return` ⇒ 判据恒假 ⇒ 400 已写出，却继续 `proxyWrite(..., null)`
写第二次响应。

**同文件对照**：PATCH（L283）判 `null` ✔、enabled（L309）判 `null` ✔，只有 test-case 判 `undefined` ✘。

**覆盖缺口**：`smoke-channels-routes.mjs` 原只测合法 body 转发，**非法 JSON 分支零覆盖**。

**已修**：判据改 `null`；smoke 加 `invokeRaw`（发原始字节）+ `makeRes` 记 `writes` 次数
+ 5 条钉（test-case / PATCH / enabled / 数组 / 标量），每条同时断言
「400 + 引擎零调用 + 响应只写一次」。**实测 36/36 通过**。

### 4.3 【已确认，未修】`standard_key` 丢前缀 ⇒ 不同标准撞车

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

### 4.4 【**状态未知**】引擎 LLM 取证调用失败 —— **接手第一件事是复测它**

上一轮（2026-10-18 前后）实测：`ks_answer` **每次**返回
`llm_error=DeepSeek 取证调用失败: Connection error.`，`verification.is_valid=false`，
`derivation`/`conclusion` 为空，只剩证据区。**本轮（2026-10-23）未复测。**

**⚠ 为什么它的严重度可能高于 §4.1**：§4.1 是「偶发拿错标准」（36 部里有 9 部会，
且只在条款号查不到时才走兜底）；这一条是**产品主输出整体为空** ——
用户问一句，拿不到推导和结论，产品等于没工作。

**当前状态：未知**。本文档**不宣称它已恢复、也不宣称它仍然坏**。

**复测方法**（约 1 分钟）：
```powershell
ks_ping                                              # 1. 引擎活着吗
ks_answer("甲醇作业要不要做职业健康检查")              # 2. 问一个必定有答案的题
# 3. 看返回里这三项：
#    llm_error 是否为空 / verification.is_valid 是否 true / derivation 与 conclusion 是否有内容
```

**要修它需要先知道**（本文档**没有**这些信息，明确未做）：
LLM 的 key 配在哪、走不走代理、模型名在哪配。
`src/core/main.py` 的 `_normalize_no_proxy()` 注释说这个坑咬过 5 次
（`NO_PROXY` 里的 `[::1]` 让 OpenAI 客户端**构造时**就抛 `Invalid port`）——
**那可能是这一类故障的已知形态，但这是线索不是结论，未验证。**

### 4.5 【已确认，未修】门禁的 `xfail` 假红

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

## 5. 重复实现（业主的头号关切）

### 5.1 尺子读数

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

### 5.2 ⑤ 的 13 组，逐组裁决

| # | 重复的东西 | 位置 | 裁决 |
|---|---|---|---|
| 1 | `_xlsx_header_style` | `exports/effect_report.py:325`、`update/announce.py:766`、`update/report.py:145` | **该合**（3 处逐字相同） |
| 2 | `_checksum` / `_file_sha256` | `storage/backup.py:43`、`update/data_package.py:97` | **该合**（后者注释自写「与 backup._checksum 同一口径」） |
| 3 | `_fetch_text` | `update/channels/mem_gov.py:103`、`mohurd.py:82` | **该合**（基类 `ChannelAdapter` 已有 `_fetch`） |
| 4 | `chunk_text` | `scripts/measure-classical-chinese-segmentation.py:82`、`measure-cross-language-fts.py:80` | 合（前者注释写「与另一把尺子逐字一致」） |
| 5 | `_db_stat` | `scripts/normalize-standard-no-slash.py:60`、`repair-missing-standard-no.py:55` | 合（一次性脚本，低优先） |
| 6–13 | `_write_pdf` / `synthetic_parser` / `_install` / `fake_reg` / `store_dir` / `QueryValueEx` / `data_dir` / `_load` | `tests/` 内 | **不合**（测试夹具各自独立更好，共享会把测试耦合） |

### 5.3 ⑤ 抓不到、人读发现的（更严重）

**A. 标准号归一有 11 个不同名字，散在 6 个模块**

| 名字 | 位置 | 干什么 |
|---|---|---|
| `canon_standard_no` | `text_utils.py:1280` | 比较用：全角→半角、折破折号、去空白斜杠、大写 |
| `store_standard_no` | `text_utils.py:1296` | **存储形**：只折全角 `/` `-`，其余不动 |
| `standard_key` | `text_utils.py:1358` | 压成 `号-年`（**丢前缀**，见 §4.3） |
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

## 6. 门禁与验证能力的真实边界

### 6.1 conftest 布的是空库 —— **3,076 条用例里跑在真库上的是 0 条**

`tests/conftest.py` 的 `_isolate_data_dir` 是 session 级 autouse，把 `KS_DATA_DIR`
换成 `tempfile.mkdtemp()`，**无开关**。`db` fixture 只建表不填数据。

⇒ **所有依赖真实语料的判据在门禁里结构上做不到**。这解释了 §4.1 为什么能活到今天。

### 6.2 棘轮能被绕过吗（我实测的结论）

| 口子 | 子代理说法 | 我的复核 |
|---|---|---|
| A. `-UpdateBaseline` 在红的跑里也写基线 | 成立（读代码） | **成立**（`run-gates.ps1:614` 不受 `$why.Count` 约束），但受 `$null -ne $pytestPassed` 罩着。**未实跑** |
| B. 多加 skip 骗过 | 不能直接骗过 | **成立**：`run-gates.ps1:572` 的 `$newIds` 白名单判据会当场红 |
| C. `xfail` 完全隐身 | 隐身 | **❌ 推翻**：是**假红**，不是隐身（见 §4.5） |
| D. 口径没生效时判据变松 | 成立 | **成立**：`totalForRatchet = totalRan`（不减），补偿是「本跑不许记基线」 |

### 6.3 恒真断言 6 处（实测原文，永不红）

| 文件:行 | 原文 |
|---|---|
| `tests/test_appendix_split.py:212` | `assert _CLAUSE_NO_APPENDIX_RE.search("5.2.1 条款内容") is None or True` |
| `tests/test_patches.py:60` | `assert not any(...) or True  # 修正前可能不命中` |
| `tests/test_phase4.py:59` | `assert ids.index("q2") <= ids.index("q1") or True` |
| `tests/test_phase6.py:195` | `assert "安全监护" in expand_with_alias("安全监护") or True` |
| `tests/test_reranker.py:127` | `assert not hybrid_engine._last_rerank_debug.get("rerank_offline") is False or True` |
| `tests/test_research_report.py:241` | `assert "⚠锚点未验证" in md.split("三、依据")[0] or True` |

`assert True` / `try: ... except: pass` 包住断言：**0 处**（实测）。

### 6.4 `src/core` 零测试模块 8 个

`figure_redraw` / `formula_locator` / `mohurd` / `proxy_rotate` / `routes_law` /
`routes_settings` / `routes_update` / `span_verify`。
7 个是活代码（被 `server.py`/`pipeline.py` 调用），只有 `proxy_rotate` 全仓仅剩自身模块名。

**⚠「间接跑到」≠「被测」**：没有一条用例是为它们写的。

### 6.5 `tools/gov-qa` 634 MB 数据受版本控制

`tools/gov-qa/data`：686 文件 / 644.2 MB（594 个 `.jsonl` + 90 个 `.cursor`），
`.gitignore` 不排除它。**这是 `harvest.py` 可再生的采集产物。**
**是否含个人信息：未读内容，明确未做。**

---

## 7. 文档体系

### 7.1 顶层 29 份（不是 30）

`docs/` 顶层 **29 份 md**，其中 **28 受跟踪**；
`EXTERNAL-REVIEW-ARCHITECTURE-v4.md` **未跟踪**，而 `docs/README.md` 标它 ✅
—— **文档与事实不一致**。

### 7.2 九组冲突（子代理给数，未逐组复核）

| 冲突 | 数字 A | 数字 B | 实测 |
|---|---|---|---|
| 表数量 | 34 / 38 / 60 / 62 | — | **44** |
| 语料规模 | 6,797 | 8,983 | — |
| 渠道数 | 131 / 280 / 286 | — | — |
| 子系统数 | 19 / 18 / 16 | — | **16**（+10 根文件） |
| 总纲状态 | 「已暂停」 | 010/013 仍在施工 | — |
| `INDEX.md` | 210 | 磁盘 214 | — |
| `EXTERNAL-REVIEW-v4` | README 标 ✅ | 实为未跟踪 | **属实** |
| `BROKEN-LINKS` | 「0 处」 | — | — |
| 「接手先读这一份」 | wiki / HANDOVER / ENCYCLOPEDIA **三处都说自己** | — | — |

### 7.3 `specs/` 编号撞车 —— **核实为真，两组都真**

- `009-standard-no-ocr-suffix`（10-12 10:31 建）vs `009-turn-evidence-ui`（14:47 建）
- `010-real-question-ruler`（10:59）vs `010-turn-tab-fixes`（16:35）

原因：后建的人没查已有目录；两条线用两套提交前缀（`spec-009` vs `UI/spec009`）；
`.specify/scripts/powershell/create-new-feature.ps1` **本有撞号自动往上找空号的逻辑**，
说明这两个目录**没走该脚本**。`specs/` 无 README、`.specify/feature.json` 只记当前一个目录
⇒ 撞号无登记处。代价：「spec 009」在开发史与 `PLAN-REAL-QUESTION-RULER` 里指两个不同特性。

### 7.4 `scripts/` 68 个：一次性 18 个，其中 **9 个被 pytest 按路径钉住**

`Path(__file__).resolve().parents[1]/"scripts"/…` + `spec_from_file_location`
⇒ **不能整体归档**。另 9 个无测试无门禁引用（`map-dsh-icons` / `fix-dsh-icon-names`
是全仓零引用的唯一一对）。
`measure-*` **11 个**（不是 10），10 个不落盘、读数手抄进 `RETRIEVAL-LONG-RANGE-PLAN`；
只有 4 个有测试钉住尺子本身。

---

## 8. 尺子本身（怎么用、怎么信）

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

## 9. 本轮真跑记录（实测，不是推断）

| 跑的是什么 | 结果 | 耗时 |
|---|---|---|
| 完整 pytest（第 1 次，含 tools/gov-qa） | **1 failed / 3067 passed / 8 skipped** | 1,144.92s（19 分钟） |
| 上述失败原因 | **我自己的临时文件** `.tmp/calibrate.py` 被 `test_credentials_namespace.py` 全仓扫描抓到 | — |
| 删掉临时文件后单跑该文件 | **34 passed** | 34.64s |
| 完整 pytest（第 2 次，清理后） | **3068 passed / 8 skipped / 0 failed** | 865.33s（14 分钟） |
| `scripts/gates-tracked-total.py --junit ...` | `collected=3076 / untracked=11 / **tracked_total=3065**` = 基线，零松弛 | — |
| `node plugin/scripts/smoke-channels-routes.mjs` | **36/36 PASS**（含新加 5 条钉） | — |
| `python scripts/check-repo-uniformity.py --selftest` | **PASS**（③④⑤ 都抓到负例） | — |
| `python scripts/check-repo-uniformity.py --repeat-check` | **PASS**（两次读数一致） | — |
| `python scripts/uniformity-ast-dupes.py --selftest` | **PASS**（正例命中、两个反例未误判） | — |
| `python scripts/docs/check-links.py` | **断链 0 处**（394 md / 674 链接） | — |

**基线对账（已查清，结论：基线一直是对的）**：

```
门禁口径脚本 scripts/gates-tracked-total.py --junit .tmp/j2.xml --repo .
  → {"collected": 3076, "mapped": 3076, "unmapped": 0, "untracked": 11, "tracked_total": 3065}

两次完整 pytest 的总账都 = 3076：
  第 1 跑：1 failed + 3067 passed + 8 skipped + 0 errors = 3076
  第 2 跑：0 failed + 3068 passed + 8 skipped + 0 errors = 3076
减未跟踪 11 → 3065 = 基线 pytest_total 3065  ⇒ 零松弛，棘轮绿
```

**⚠ 我自己在这上面算错过两次，都留痕**：

1. 第一次把总账写成 `3067+8=3075`，据此说「会判红，差 1」。**错因**：漏了 `failed` 那 1 条
   （失败**既不在 passed 也不在 skipped**）。
2. 第一次的错还带出一个**编造**：我在 §13 写了判据「同时 4 条合法年份宽容用例仍要过」，
   而**全仓不存在这 4 条用例** —— `resolve_clause` 的年份宽容路径**零测试覆盖**
   （仅有的两个碰 `resolve_clause` 的测试文件里没有任何一条测它）。
   实测这条路径本身是好的（`GB 3608-2019/4.1 → GB 3608-2025`），但**没有测试守着**。

⇒ 教训：**复算基线必须抄脚本的公式**；**写判据时必须先确认那个东西真的存在**。

---

## 10. 明确未做 / 未验证（不许当成做过了）

| 事项 | 原因 |
|---|---|
| `-UpdateBaseline` 在红的跑里到底写不写基线 | 要跑 `-Full` 且会写基线，本轮不做 |
| `standard_key` 前缀碰撞在检索里实际漏多少 | 要在真库上跑检索对照，未做 |
| `tools/gov-qa/data` 634 MB 是否含个人信息 | 只看了文件名与条数，**没读内容** |
| `plugin/src/*.js` 与 56 个 mjs 的静态类型面 | 没有任何静态类型门禁（`tsc` 只编 `plugin/client`），未逐个数 |
| `src/core` 8 个零测试模块的间接覆盖有多少 | 要 `--cov` 跑完整 pytest |
| `tests/` 3 个未跟踪测试文件的来历 | 没有 commit 就没有可查的动机 |
| 引擎 LLM 取证调用失败（§4.4） | 本轮未复测 |
| `ui-render-shot.mjs`（328 KB / 4,517 行）内部结构 | 未读 |
| `KsEvidenceTab`（2,834 行）里还有多少可抽纯函数 | 未读 |
| 真库真实规模（8,983 部 / 663,634 条） | 上一轮实测，本轮未重核 |

---

## 11. 四份原始报告（按需深查）

| 文件 | 内容 | 可信度 |
|---|---|---|
| [`00-review-of-surveys.md`](00-review-of-surveys.md) | **主对话复核记录**：10 条已核实 / 2 条推翻 / 2 条更正 | ★★★ 先看这个 |
| [`01-core.md`](01-core.md) | `src/core` 16 子系统 + 10 根文件逐文件职责、入口、依赖、写什么 | ★★ 骨架可信，具体结论抽查过 |
| [`02-plugin.md`](02-plugin.md) | `plugin/` 宿主 19 js + 客户端 31 tsx + 56 mjs；40 条重复；端点清单 | ★★ 同上 |
| [`03-docs-specs-scripts.md`](03-docs-specs-scripts.md) | 29 顶层文档 + 9 组冲突 + specs 15 个 + scripts 68 个 | ★★ 同上 |
| [`04-tests-tools-gates.md`](04-tests-tools-gates.md) | tests 结构 + 覆盖率缺口 + 门禁 12 步 + 棘轮绕过分析 | ★★★ 唯一被推翻的是 xfail 那条（见 §4.5） |

**⚠ 引用子代理报告时先看 `00-review-of-surveys.md`**：
`04` 的「xfail 隐身」已被实测推翻；`01` 的「storage ⇄ retrieval 靠 import 顺序侥幸」
已被实测更正为「不构成模块级真环」。

---

## 12. 术语表（新对话最容易卡在这些词上）

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
| **核验** / verification | 答案写出来之后，回头查它引用的条款是否真在证据里、数值是否被篡改、模态是否被加强。判据在 `src/core/verification/typed_verifier.py`，结果落在 `verification.is_valid` / `unsupported_clauses` / `unverified_numbers` / `modality_violations` |
| **口径** | 统计时用的**计算规则**。本仓最重要的口径是"棘轮只算受版本控制的用例"（`scripts/gates-tracked-total.py`）。**同一个词在别处也指"判据/标准"** |
| **未跟踪** | `git` 没有纳入版本控制的文件。本仓有 3 个未跟踪测试文件贡献 **11 条用例**，棘轮会把它们扣掉 |
| **假红 / 假绿** | **假红** = 代码没坏但门禁报失败（如环境缺模型）；**假绿** = 代码坏了但门禁通过（本仓纪律：**假绿一律判 failed**） |
| **判红** | 门禁判为失败（退出码非 0） |
| **xfail** | pytest 的"预期失败"标记。**⚠ 在本仓它会引发假红**（§4.5）：junit 里带 `<skipped>` 子节点，与汇总行的 `skipped` 数不等 ⇒ 门禁报"判据不可信" |
| **junit** | pytest 写出的 XML 结果文件。门禁靠它拿每条用例的 nodeid（`run-gates.ps1` 用 `--junitxml=`） |
| **nodeid** | pytest 用例的唯一名字，形如 `tests.test_api::test_x`。棘轮的 skip 白名单就是按它判的 |
| **幂等** | 同一件事做两遍结果一样。本仓用它验"连续两次轮询第二次 0 新增"和"尺子跑两次同一个数" |
| **业主** | 这个项目的**所有者/出资人**，也就是提需求、拍板、定纪律的人。本仓所有"最高指令"都出自他 |
| **宿主 / 宿主侧** | 运行 DSH 的那个 Node 进程。它加载插件、注册工具与路由。"宿主侧"= `plugin/src/`（Node 进程内），"客户端"= `plugin/client/`（浏览器里跑的 React） |
| **客户端** / plugin/client | 侧栏界面，React + tsx，被 `build-client.mjs` 打成 `client.js` 后由宿主送进浏览器 |
| **`create_app` 闭包** | `src/core/api/server.py` 里 `def create_app(...)` 包住的整块。**里面定义的函数模块外拿不到** ⇒ 没法写单测（§5.3C 就是被这个困住的） |
| **转正** | 材料评审通过、从"待评审"变成"可进作答" |
| **外发审计** | 每次把内容发给外部大模型都留一条记录（发了什么、发给谁） |
| **Jev 判断** | 接 `TypeSafe System One`（Jev）做结构化判断，用在"合规触发"与"公告入库"两处。**本文档未深查它的现状** |
| **gov-qa** | `tools/gov-qa/` —— **另一条线**：政务问答语料采集（13 省市政民互动平台）。948 MB / 3,427 文件，其中 634 MB 数据受版本控制。**不属于主引擎，但与主项目共用同一批政府站点**。它的写入由另一条自动化线高频进行 |
| **位置片段** / source_span | 一条条款在 PDF 里的坐标（页码 + bbox），用来画红框、做可点链接。库里 1,842,493 条 |
| **真库 / 空库** | **真库** = `var/data/database/knowledge.db`（8,983 部 / 663,634 条）；**空库** = `conftest` 给测试布的临时目录，只有表没有数据 |
| **快照** | 本仓有两个意思：① `var/data/backups/` 里 13 个数据库备份；② `scripts/snapshot-project.ps1` 打的 git tag（回滚点）。**看上下文** |
| **兜底 / 宽容兜底** | 精确查不到时退一步用宽松判据再查一次。§4.1 那个 bug 就在这一层 |
| **命令契约** / `verify:commands` | 门禁的一步：验 22 条斜杠命令的行为没变（`plugin/scripts/run-verify-commands.mjs`） |
| **e2e / 真宿主 e2e** | 装进一个临时 DSH profile、真跑一遍的端到端验证（`plugin/scripts/e2e-install-compose.mjs`） |
| **mypy / tsc / ruff / pyscn** | `mypy` = 引擎（Python）类型检查；`tsc` = 客户端（TS）类型检查；`ruff` = Python 风格与命名检查；`pyscn` = 重复代码与复杂度检查 |
| **E501 / N802** | ruff 的规则号。`E501` = 行太长；`N802` = 函数名应小写（本仓对它们做了两档校准，见 §8） |
| **五色** | 效力总览的五个颜色：🔴在用已废止/被代替 · 🟡即将实施 · 🟢现行有效 · ⚪状态未知 · 🔵仅参考。**注意 `legal_status` 有 6 个值**（`superseded` 与 `withdrawn` 在五色里都归"已废止"） |

---

## 13. 下一步（按「先确认能验、再动手」排序）

> **排序原则（2026-10-23 修正）**：先解决「**能不能验证**」和「**产品活没活**」，
> 再解决具体缺陷。理由：不先解决这两件，改完也证明不了改对了。
> 我第一版把「业主头号关切（重复实现）」排第 4 却没解释，那是错的 —— 现补上说明：
> 重复实现**不会让产品给出错误答案**，前三条会让。

### 第 0 步（**先做这个**）：确认产品今天能不能用

**复测 §4.4**（LLM 取证调用）。它决定这个产品是"能用但有缺陷"还是"主输出为空"。
一条 `ks_answer` 就够，约 1 分钟。**在它明确之前，后面所有修复的优先级都是猜的。**

### 第 1 步：让"真库上的判据"变得可能（§6.1）

现在 `conftest` 把所有测试钉在**空临时库**上 ⇒ 所有依赖真实语料的判据**结构上做不到**。
这既是 §4.1 活到今天的原因，也是"改完怎么验"的根。

**可选做法（未定，需拍板）**：
- 加一个显式开关（如 `KS_REAL_DB=<path>`）让特定测试**在真库只读副本**上跑；
  仓库里已有 6 条测试用这个模式（`test_catalog_hidden_retrieval` / `test_change_signal` /
  `test_label_gap_not_jev`），**说明这个模式是现成的、只是没推广**。
- 或者建一个**缩小版真库夹具**（几百篇代表性文档）进版本控制，让多数判据能跑。

**判据**：§4.1 那 9 部受害标准能在门禁里被自动化验出"误命中"。

### 第 2 步：修 `resolve_clause` 年份兜底（§4.1）

已拿到现场、已量化、影响核心领域（9 部受害标准全是职业健康/安全类）。

修法：正则改成**先抽「字母前缀 + 数字主体」**，抽不到就不兜底。

**判据**：
- 那 9 部受害标准必须全部从「误命中」变成「404」；
- **年份宽容本身必须仍然生效** —— 实测这条路径目前是好的：
  `GB 3608-2019 / 4.1` → `GB 3608-2025`；`GB/T 3608-2008 / 4.1` → `GB 3608-2025`。
- **⚠ 这条路径全仓零测试覆盖**：`tests/test_resolve_clause_normalization.py` 与
  `tests/test_api.py` 是仅有的两个碰 `resolve_clause` 的文件，**没有任何一条测年份宽容**。
  ⇒ **修之前必须先补这条测试**，否则改坏了没人知道。
- 我先前写「同时 4 条合法年份宽容用例仍要过」是**编的** —— 全仓不存在这 4 条。已就地更正。

### 第 3 步：两个同名函数的行为分叉（§5.3B）

`_answer_confidence` / `_expand_title_clauses` 在 `server.py` 与 `ks_answer.py` 各一份，
**已经分叉**（字段名不同 ⇒ 把一方的数据喂给另一方会**静默判 high**）。
两者都在 `create_app` 闭包内 ⇒ 模块外拿不到 ⇒ **没法写单测** ⇒ 分叉没有测试能发现。

**顺序**：先移出闭包让它可测 → 再定字段名 → 最后合并。**不能直接合并**。

### 第 4 步：标准号归一 11 个名字收敛（§5.3A）

先出对应表，逐条判定哪个是唯一真源。这个字段全仓 **1,472 处引用 / 152 文件**，
改动面大，必须分批。

### 第 5 步：⑤ 的 3 组 `src/core` 重复合并（§5.2 #1#2#3）

`_xlsx_header_style`（3 处）、`_checksum`/`_file_sha256`（2 处）、
`_fetch_text`（2 处，基类已有 `_fetch`）。低风险、可验证。

### 第 6 步：门禁 `xfail` 假红（§4.5）

`pytest.xfail()` 会让门禁报「判据不可信」。要么让脚本识别 xfail、要么在脚本里禁用并写明。

---

## 14. 本文档自己的已知缺陷（诚实登记）

| 缺陷 | 状态 |
|---|---|
| 第一版把「4 条年份宽容用例」写进判据，而那 4 条**不存在** | **已更正**（§13 第 2 步） |
| 第一版把基线总账算成 3075（漏了 `failed`），据此说"会判红" | **已更正**（§9） |
| 第一版表格数字加不出合计（155/45,439 vs 162/46,437） | **已更正**（§3.1 已对账） |
| 第一版「根 9 文件」实为 10 个 | **已更正**（§3.1 列了准确名字） |
| 第一版说 `var/data` 里 `knowledge.db` 3.11 GB，实为 **13.82 GB**（目录含 WAL/索引），单文件 2.90 GB | **已更正**（§2.2） |
| 第一版用「天花板」同时指下限和上限 | **已更正**（§1.2 加了对照表） |
| 第一版**没有「从零到能跑」**一节 | **已补**（§0） |
| §7.2「九组冲突」只有 2 组标了实测，其余是子代理给数、我没复核 | **明确未做** |
| 本文档没有 UI 截图、没有页面清单 | **明确未做**（§10 已登记） |
| 「完整 176 条路由清单」只在 `.tmp/routes-full.txt`，不在仓里 | **明确未做** —— 要长期留需抄进本文档 |

**术语表缺的承重词**（§12 已补）：`口径` `xfail` `核验` `业主` `假红/假绿` `未跟踪` `天花板`。
