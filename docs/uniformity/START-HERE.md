# KnowledgeStation 上手（新人第一份读这个）

> **这份文件只有一件事**：让你从零跑起来，并且不踩这个仓的坑。
> 读完这一份（约 210 行）你就能动手；要查证据、重复实现清单、门禁真实边界、
> 明确未做清单，看 [README.md](README.md)（那份是证据与过程，约 760 行，按需查）。
>
> **顺序**：本文件 → [`../wiki/architecture.md`](../wiki/architecture.md)（项目目标与现状，长期维护的那份）
> → [`../wiki/components/`](../wiki/components/)（要改的那个子系统，文件级）。
> 完整定序见 [`../README.md`](../README.md) 顶部。

---

> **最后更新**：2026-10-23 ｜ **基准提交**：`64f37707` ｜ **摸底方法**：4 个独立子代理

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

**⚠ 数据获取曾经是循环引用 —— 2026-10-23 已解决**

原先只有两条路，**而两条都指向新克隆的人手上没有的东西**：
- 路 A「从旧副本拷回」—— 新克隆的人**没有旧副本**；
- 路 B「从 `var/data/backups/` 的 13 个快照恢复」—— `backups/` **就在 `var/data/` 里面**，
  而 `var/data` 正是缺的那个 ⇒ **循环**。

⇒ **现在有第三条路：随仓提交的种子库。**

| 项 | 值 |
|---|---|
| 位置 | `tests/fixtures/seed/knowledge-seed.db` |
| 体积 | **13.3 MB**（可以进版本控制） |
| 内容 | **82 部真实标准 / 4,809 条真实条款 / 16,198 条位置片段 / 1,127 个目录** |
| 怎么生成 | `python scripts/make-seed-db.py --docs 60`（需本机有 `var/data`） |
| 怎么用 | pytest fixture `seed_data_dir`（见 `tests/conftest.py`） |
| 回归护栏 | `tests/test_seed_db_guard.py`（6 条） |
| 真语料判据 | `tests/test_real_corpus_retrieval.py`（7 条） |

**它解决什么**：在这之前，「在真库上验证」在门禁里**结构上做不到**
（实测 3,076 条用例跑在真库上的是 0 条）。种子库让这件事第一次变成可能 ——
实测它已经复现并最终修掉了 `resolve_clause` 的跨标准误命中（wiki §四 #2）。

**它不解决什么**：82 部 ≠ 8,983 部。六路检索的**召回率与排序质量**、
`parse_out` 里的图片与公式、材料平面、巡检台账，仍只有完整库能验。
⇒ **要跑产品全貌还得有完整 `var/data`**；只是"能不能开发与回归"不再被它卡住。

**挑样本的判据不是「随便抽」**：`scripts/make-seed-db.py` 的 `MUST_INCLUDE` 钉了
**9 部受害标准 + 3 部被误命中的别家标准 + 2 部年份宽容正向样本**。
少任何一部，那条缺陷就复现不了。**为暴露缺陷挑样本，不是为产物好看。**

**剩下两条候选（未实施，需要就说）**：
1. 把 `var/data/backups/` 里最新的快照做成独立可分发的包（约 1~2 GB）—— 给"要完整库"的人；
3. 写从零抓取/入库的脚本链（`tools/gov-qa` 有采集能力，但抓的是政务问答不是标准全文）。

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

**探活**：`GET http://127.0.0.1:<port>/api/v1/health` —— **不需要 token**。

**⚠ 这里我原先写错了，留痕**：我写过「带 `Authorization: Bearer <token>`」，**那是错的**。
鉴权中间件（`server.py` 约 L317）把 `/api/v1/health` 和 `OPTIONS` **显式放行**：
```python
if request.url.path == "/api/v1/health":
    return await call_next(request)
if request.method == "OPTIONS":
    return await call_next(request)  # CORS 预检不带 token
```
⇒ **其余所有端点都要 token**，只有这两类不用。
`ks_ping` 工具就是这个端点的封装（所以它也不需要 token）。

其余端点探法：`Authorization: Bearer <token>`，token 从 `engine.session.json` 或启动 stdout 读。

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

