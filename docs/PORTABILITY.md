# 便携与路径纪律

> **业主目标**（2026-10-17）：「便携版随时一拷贝就能走…不会产生对我当前环境有依赖的东西」。
> 本文是**判据**：运行时靠什么做到便携、以及**发现写死路径时怎么判该不该改**。
> 纪律本体在 [`AGENTS.md`](../AGENTS.md) §环境（那一条每轮注入）。

---

## 一、运行时靠什么做到便携（已实现）

| 环节 | 机制 | 在哪 |
|---|---|---|
| **插件找引擎** | 运行时**从插件自身位置往上找仓库标记**（`src/core/main.py`）；`$KS_ENGINE_ROOT` 可显式覆盖 | `plugin/src/engine.js` 的 `findEngineRoot` |
| **venv 的底座** | 拉起引擎前，若 `pyvenv.cfg` 的 `home` 指向不存在的目录，就找一个**随包走**的解释器（`services/*/python`）改过去；路径没变时**一个字节不改** | `plugin/src/engine.js` 的 `healVenvHome` |
| **模型** | 拉起引擎时注入三个环境变量，全部**从仓根算出来**：`KS_MODELS_DIR`、`MINERU_MODEL_SOURCE=local`、`MINERU_TOOLS_CONFIG_JSON`（配置文件也**运行时生成**）。外部已设的键**不覆盖** | `plugin/src/engine.js` 的 `modelsRoot` / `ensureMineruConfig` / `modelEnv` |
| **数据** | 默认值改成**包内** `<仓>/var/data`（不再落 `%APPDATA%`）。`KS_DATA_DIR` 仍是显式覆盖 | `src/core/config.py` 的 `_repo_root` / `_default_data_dir` / `_default_models_dir` |

**⚠ 数据这一条有个"两边必须同一口径"的硬约束**：引擎把 `engine.session.json`
写进**它**的数据目录，而插件去**它**的数据目录**读**同一个文件
（`plugin/src/engine.js` 的 `dataRoot`，与 Python 侧的取值顺序**逐字对齐**）。
两处口径一旦不一致，插件就**永远找不到**引擎留下的会话 ⇒ **每次都会重复拉起一个新引擎**
（表现为"引擎反复重启、端口一直变"）。改任何一边都要同时改另一边。

**为什么 venv 需要自愈**：Windows venv **不带标准库**（实测 `Lib/` 下只有 `site-packages`，
没有 `os.py`、没有 `python312.dll`），它靠 `pyvenv.cfg` 的 `home =` 找 base ——
**那是绝对路径**，整包一换盘符就失效。

**为什么模型必须进包**（业主 2026-10-18 点名 MinerU 的 OCR 模型）：
三套模型原先都在包外，而 `~/mineru.json` 把路径**写死** ⇒ 换机/换盘符后
**检索（向量/重排）与文档解析（MinerU）都会失效**。

| 模型 | 体积 | 原位置 | 谁用 |
|---|---|---|---|
| bge-reranker-base + bge-small-zh-v1.5 | 1,168 MB | `%APPDATA%\KnowledgeStation\models` | KS 向量/重排 |
| PDF-Extract-Kit-1.0 | 2,475 MB | `~\.cache\modelscope\...` | MinerU **pipeline**（默认 backend） |
| MinerU2.5-Pro-2605-1.2B | 2,220 MB | 同上 | MinerU `vlm-engine` |

**MinerU 怎么被指进包**（读 `mineru` 包源码得到，不是猜的）：
`mineru/utils/models_download_utils.py` 里 `if model_source == 'local': return
get_local_models_dir().get(repo_mode)`，而 `config_reader.py` 里
`MINERU_TOOLS_CONFIG_JSON` **可以是绝对路径**。
⇒ 设 `MINERU_MODEL_SOURCE=local` + 配置 `models-dir: {pipeline, vlm}` 即可，**完全不联网**。
（⚠ 2.x 读的是 `~/mineru.json`，**不是**旧的 `~/magic-pdf.json` —— 两个文件都在，生效的是前者。）

**⚠ 前提**：`.venv/` 与 `var/models/` **都必须随包走**。两者都被 `.gitignore` 盖住、
**不在版本控制里** ⇒ 用 git 拉代码**不会**带上它们，拷贝时要连它们一起拷。
`.venv/` 丢了就用包内 3.12 解释器重建（`services\hindsight\python\python.exe`）+ `pip install -e .`。

**判据**：`plugin/scripts/smoke-engine-guard.mjs` 第 6 组（9 条，路径/venv）+ 第 7 组
（12 条，模型）+ 变异自验 **12/12**。

---

## 二、发现写死路径时，怎么判该不该改

**核心判据一句话：这条路径会不会在另一台机器上被跑？**

| 类别 | 典型位置 | 改不改 | 为什么 |
|---|---|---|---|
| **运行时** | `plugin/src/**`、`src/**`、`scripts/run-gates.ps1`、`plugin/scripts/*.mjs` | **必须改** | 产品跑的就是它；不改则换机即坏 |
| **一次性研究脚本** | `eval/**`（实验驱动脚本） | **不改** | 它们**跑过一次、结论已入库**；改了会**篡改"当时到底跑的是什么"**的记录 |
| **归档** | `docs/archive/**` | **不改** | 冻结历史 |
| **历史数据** | 结果快照 `*.json`（如 `FREEZE.json` 的 `git_status_short`） | **不改** | 它记录的是"在哪台机器、什么状态下产出的"，是**证据** |
| **文档正文** | `docs/**/*.md` 里引用的路径 | **不改** | 同上 —— 记的是"当时在哪个路径下发生" |

⚠ **改了历史记录 = 丢证据**。本仓已有过教训：清掉复核对照树 ⇒ 原始 JSON 证据永久丢失。

---

## 三、怎么审计（可复算）

```powershell
# 只看**受版本控制**的文本文件（未跟踪的产物不算）
# 判据：代码扩展名 = 运行时面；.md/.txt = 历史记录面
python scripts/audit-hardcoded-paths.py
```

审计脚本把两类**分开报**：
- **代码里的写死**（真依赖）⇒ 逐条列出来给人看
- **文档里的引用**（历史记录）⇒ 只计数，**不改**

⚠ 脚本**排除它自己**（它里面就写着那些模式串，不排除会匹配到自己）。

**2026-10-18 实测读数**：

| 形态 | 代码里 | 文档里 |
|---|---|---|
| 旧工作区 `D:\AI\work space` | **139** | 261 |
| 新工作区 `D:\Agent-Studio` | **1** | 0 |
| 本机用户名 `Zegel` | 52 | 37 |
| 用户 `AppData` | 30 | 10 |

⚠ **代码里那 140 处（139 + 1）里有 2 处是注释，不是依赖**：
- `plugin/src/engine.js` 的 `findEngineRoot` 注释里写着「这一行原先写死成
  `D:\AI\work space\zcode`」—— **留痕**（记录 bug 长什么样）；
- 同文件的 `findEngineRoot` 注释里写着「包搬到 `D:\Agent-Studio\...` 后」——
  同一件事的**实测出处**。

⇒ **真正的运行时写死是 0 处**。⚠ 这两处注释**不许为了"让审计归零"而删掉** ——
审计的用途是**找依赖**，不是让数字好看；删了就把"这个 bug 长什么样"的证据丢了。

**代码里那 139 处的分布**：绝大多数在 `eval/**` 与 `docs/archive/**`（一次性脚本与归档），
**运行时关键只有 `plugin/src/engine.js` 的 `ENGINE_ROOT` 一处** —— 那一处已改成运行时推导。

⇒ **结论**：按上表判据，`eval/**` 与归档**保持原样**（它们是记录，不是依赖）；
**新写的代码不许再写死**。

---

## 四、发现写死路径时的正确改法

⚠ **不要"把旧值换成新值"** —— 那只是把同一个病推迟到下次拷贝。

| 场景 | 正确做法 |
|---|---|
| 要找仓库里别的东西 | 从**本模块自身位置**往上找标记，别写盘符 |
| 要找可执行文件/解释器 | 逐级回退（显式配置 → 包内 → PATH），别写死一个 |
| 确实需要固定位置 | 走**配置项**（如 `$KS_ENGINE_ROOT`），别写进源码 |
