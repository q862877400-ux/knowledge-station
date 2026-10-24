# 观察记录（中性，不下结论）

> ## 这份文件的规则（很重要，请遵守后再往下读）
>
> 1. **每条只是一次观察**，不是"缺陷"、不是"该修"、不分轻重、不排优先级。
> 2. 每条都带**复核方式** —— 你可以自己再算一遍。
> 3. 「同一件事有两份实现」是**描述**，不是"应该合并"。
>    「0 个调用方」是**计数**，不是"死代码"。
> 4. **我（做这份记录的人）不判断。** 该不该改、改了会不会坏事，是你的判断。

---

## 一、代码里观察到的事

### O-1 同一件事有两份实现（8 组，按证据强度）

| # | 同一件事 | 实现 A | 实现 B | 复核 |
|---|---|---|---|---|
| 1 | 「页码 + 标准号」页眉判据 | `pipeline.py` 的 `_STD_CODE_FRAG` / `_frag_key` / `_strip_foreign_frag` | `text_utils.py` 的 `_WM_STD_CORE` / `_RE_WM_HEADER` / `strip_watermark_lines` | `grep "第二份实现" ingestion/pipeline.py` |
| 2 | 图例判据 | `_is_figure_legend`（块级，条目只认数字） | `strip_figure_legend_segment`（文本级，含字母型） | `grep "_RE_LEGEND_ITEM" ingestion/pipeline.py` |
| 3 | HTML→纯文本 | `text_utils.html_to_text`（自称规范实现） | `server._html_to_text`、`ks_answer._html_to_text_compact`、`clause_health.clause_health_html_to_text` | `grep -rn "def .*html_to_text" src/` |
| 4 | 标准号归一/比较键 | `text_utils` 4 个（`canon_standard_no` / `standard_key` / `standard_no_key` / `store_standard_no`） | `channels/base.norm_no`、`ccs_fetcher._seed_key`、`clause_repo._standard_body`、`pipeline._hier_from_no`、`_frag_key` | `grep -rn "def .*standard\|def norm_no" src/` |
| 5 | 完整入库流程 | `pipeline.run_full_ingest`（12 步） | `law_text.ingest_law_text`（自建 model/边/doc 行） | `grep "两条入库路径行为不一致" knowledge/law_source/law_text.py` |
| 6 | app_config 读写 | `inspector.get_config` / `set_config` | `announce.py`、`discover.py`、`subscriptions.py` 各自直接写 SQL | `grep -rn "app_config" src/core/update/` |
| 7 | 页眉/水印近重复 | `text_utils._match_key`（被用 2 处） | `text_utils._match_std` | `grep -rn "_match_std" src/` |
| 8 | **已收口的一例（正面参照）** | `clause_repo._seg` → `from src.core.text_utils import segment_for_fts` | — | 注释写「实现只有一份」 |
| 9 | 后端置信度判据（**本检查期间已合并**） | `server._answer_confidence`（旧） | `ks_answer.answer_confidence` | 见 §五 |

**其中 3 组的代码注释自己提到了重复**（第 1、3、5 组）。

### O-2 被提到 1 次的符号：2,342 个（**拆开看，不是死代码清单**）

| 类别 | 个数 |
|---|---|
| 测试函数（pytest 按名字收集） | 1,985 |
| 测试文件里其他函数 | 164 |
| 非 `tests` 目录的 `test_*` 函数 | 146 |
| **非测试代码里的** | **31** |

那 31 个里，复核时能看到至少两类**不是没被用**：
- `visit_Name` / `visit_arg` 等 —— `ast.NodeVisitor` **动态派发**调用；
- 异常类（`ConfigError` 等）—— 定义处各一次，有没有被 `raise` 要另查。

复核：`python scripts/survey/01-symbols.py` → 看 `data/symbols_py.json` 的
`text_hits_1_breakdown`。

### O-3 模块没有 docstring

`data/symbols_py.json` 里 `summary.no_docstring`。复核：同上脚本。

### O-4 超过 100 行的函数

见 [`02-code-map.md`](02-code-map.md) §四（生成物，数字有准）。

---

## 二、接口里观察到的事

### O-5 11 条接口全仓零调用方

| 接口 |
|---|
| annotations ×3 |
| projects ×4 |
| `GET /documents/{id}/versions` |
| `/compare` |
| `documents/impact` |
| `DELETE /doc-bookmarks/{id}` |

复核方式：在 `plugin/src/` 与 `plugin/client/` 里 grep 这些路径。
⚠ 本检查**只查了前端的引用**；外部调用方（脚本、第三方）**没查**。

### O-6 一条接口能读到历史问答

`GET /api/v1/diagnostics/debug-dumps`

返回列：`dump_id, trigger_type, query, created_at, llm_output, logs`。
其中 `logs` 含证据/槽位；`llm_output` 是完整模型回答。
**`prompt` 与 `retrieval_result` 存在表里，但这个接口的 SELECT 没带**（不做过度陈述）。

令牌明文在 `engine.session.json`。产品侧对这个接口 0 调用。

复核：`grep -n "diagnostics/debug-dumps" -A 12 src/core/api/server.py`

### O-7 一个开关能让云调用不落审计

`POST /chat/completions` 的请求体字段 `dump`：

```
server.py:1733  dump_enabled = bool(body.get("dump", True))
if dump_enabled:   ← 3 处写 debug_dump 的唯一开关（L1930 / L1965 / L2032 附近）
```

`deepseek_client.py` 全文 **0 处** `record_egress`（只有 `jev_client.py` 那类非 chat
调用才登记）。`/ks/answer` 那条路没有这个开关。

复核：`grep -n "record_egress" src/core/llm/*.py` 与 `grep -n "dump_enabled" src/core/api/server.py`

### O-8 请求体缺字段的处理不一致

同一类"缺字段"：有的返回 422，有的直接 `body["k"]` 抛 `KeyError` → 500（12 处）。
另有 `create_patch` 是唯一「HTTP 200 但业务 code 466」的接口。

复核：`grep -n 'body\["' src/core/api/server.py`

### O-9 `except: pass` 15 处

其中 2 处（收藏/批注与补丁富化）会把结果静默清空；1 处把任意异常伪装成 404。
复核：`grep -n "pass$" src/core/api/server.py`

### O-10 闭包里 35 个函数没有定向测试

`create_app` 占 `server.py` 的 L278–3274（约 2,997 行），内嵌 103 个函数
= 67 路由 + 35 非路由。那 35 个里**零定向用例**的 6 个：

`_write_ks_answer_dump` / `_safe_count` / `_ev_dict` / `_full_evidence` /
`_placeholder_answer` / `_expand_title_clauses`

复核：`grep -n "^    def " src/core/api/server.py | head -60`

### O-11 `_expand_title_clauses` 有两份

`server.py` 与 `ks_answer.py` 各一份；差异是硬编码 `80` vs 常量、无/有 try-except。
唯一那条测试在测试文件里**重写了一遍正则**（两份实现都不执行）。

复核：`grep -rn "def _expand_title_clauses" src/`

### O-12 `_content_html` 518 行

位于 `server.py`（L2623 附近），做 11 件事。段落合并逻辑在 `_mrg_col` 与主循环各写一遍。

复核：用 `scripts/survey/02-surface.py` 的符号数据，或直接读那段。

---

## 三、前端观察到的事

> 依据：`docs/uniformity/06-frontend.md`（523 行，逐文件读过 31 个前端文件）

### O-13 `api.ts` 5,011 行的失败处理

| 观察 | 数量 |
|---|---|
| HTTP 失败处理策略 | 6 种 / 共 80 处，其中 **58 处逐字相同** |
| 硬编码同一句 401 文案 | **41 处** |
| 统一解包器 `ksJson` 覆盖 | 24 处 |
| 没走统一解包器的引擎直连 | 约 45 个（`body.ok !== true` 手写 19 次） |
| 同一个错误类写两遍 | `KsIngestHttpError` / `InspectionHttpError` |

### O-14 页壳手写 8 处 / 5 文件

`KsKnowledgePage.tsx` 一个文件里 5 遍 `.ks-page`（4 遍完整页壳）。
面包屑 89 行手写，而共用件 `KsCrumb`（23 行）已存在。

### O-15 样式没有统一约束

| 观察 | 数量 |
|---|---|
| 内联 `fontSize` | **229 处**（其中 28 处用的字号在 `--ks-fs-*` 表里不存在） |
| 内联 style | 455 处 |
| 跨文件逐字重复的 style | 21 组 |
| `smoke-ui-scale` 扫的文件 | **只 1 个**（`ksGuideStyles.ts`） |

### O-16 前端死件

`KsPdfGuideIcon.tsx` 全仓无人 import。

### O-17 一条冒烟读的是旧工作区

`plugin/scripts/smoke-kb-page-render.mjs:2629`

```js
readFileSync('D:/AI/work space/zcode/plugin/client/KsKnowledgeGuide.tsx', 'utf8')
```

事实：`D:\AI\work space\zcode` **仍在磁盘上**，且该文件与当前仓的
`KsKnowledgeGuide.tsx` **sha256 相同**（`67AE7732…`）。
⇒ 这条现在能过；如果旧目录被删/换机器，它会抛异常。

复核：
```powershell
Test-Path 'D:\AI\work space\zcode\plugin\client\KsKnowledgeGuide.tsx'
(Get-FileHash 'D:\AI\work space\zcode\plugin\client\KsKnowledgeGuide.tsx').Hash
(Get-FileHash 'plugin\client\KsKnowledgeGuide.tsx').Hash
```

### O-18 `smoke-sanitize` 复刻消毒算法而不打包真模块

它把消毒逻辑抄了一份来测。⇒ 真实模块变了，这条测不出来。

---

## 四、写死的绝对路径（13 处）

精确串 `D:/AI/work space` / `D:\AI\work space` 匹配结果：

| 类别 | 处数 | 位置 |
|---|---|---|
| **运行期真的去读** | **2** | `smoke-kb-page-render.mjs:2629`（`readFileSync`）<br>`verify-commands-real.mjs:34`（`pathToFileURL`） |
| 脚本里写死 `REPO` 常量 | 3 | `fix-dsh-icon-names.py:15`、`map-dsh-icons.py:13`、`pick-domain-terms.py:48` |
| 测试里写死 | 3 | `test_jev_cn_baseline.py:21`、`test_rag_gate_not_adopted.py:46`、`test_change_signal.py:175`（注释） |
| 注释/文档串 | 4 | 允许（讲历史） |
| 检查器自己的排除说明 | 1 | `audit-hardcoded-paths.py:41` |

复核：
```powershell
Select-String -Path src\*.py,src\core\**\*.py,scripts\*.py,plugin\src\*.js,plugin\scripts\*.mjs,tests\*.py -Pattern 'D:/AI/work space|D:\\AI\\work space'
```

> ⚠ 其他形态的绝对路径（比如别的盘符、`C:\Users\...`）**本检查没系统扫**。
> 我试写过一个通用扫描器，误报率 >90%（把 `[[m:\s*` 的 `m:`、`\tag{` 当成盘符），
> 已弃用。见 `docs/uniformity/08-why-contracts-rot.md` §七。

---

## 五、本检查期间改动过的代码（**我做的事，也记下来**）

| 提交 | 改了什么 | 为什么 |
|---|---|---|
| `6462d21f` | 修 `resolve_clause` 跨标准误命中 + 造种子库 | 9 部标准被误命中；造种子库后"真语料判据"才可能 |
| `cc74887c` | 合并 3 组重复（xlsx 表头样式 / 校验和 / 抓页面） | 统一化，带守恒证据 |
| `7372e760` | 合并 2 组脚本口径（切块 / 库指纹）+ 补 2 个模块 docstring | 同上 |
| `f3eee72f` | 合并 `_answer_confidence` 两份分叉实现 | **旧实现在 4 个场景自相矛盾**（空证据一处判 `high`、一处判 `low`） |
| `0336889b` | `lastEngine()` 空数组不再返回 undefined | 崩溃会吞掉后面 20 多条断言 |
| `51849d83` | 4 个脚本补 `sys.path` 引导 | 按文件路径加载时 import 不到同目录模块 |

⚠ 这些是**我改的**，不是"检查"的一部分。记在这里是为了让下一棒知道
「这份地图形成期间仓不是静止的」。

**另外**：`docs/uniformity/*` 里那份同型分叉（`_expand_title_clauses`）我**没有修**——
按业主令「检查优先，改错是别人的事」。

---

## 六、本检查**没有**覆盖的（明确列出来）

| 项 | 原因 |
|---|---|
| 运行时真实行为 | 静态检查看不到 |
| 测试运行期覆盖率 | 没取 coverage |
| `tools/gov-qa` 948 MB 内容细节 | 只查结构与归属；隐私是**抽样** 3/594 个文件 |
| 浏览器里的像素效果 | 需要真浏览器 |
| 除旧工作区之外的绝对路径 | 通用扫描器误报率过高，已弃用 |
| `var/data` 74 GB 真实数据逐部核 | 只做统计 |
| `ks_answer` 端到端 | 需模型密钥，未复测 |
| 外部调用方是否用那些"零调用"接口 | 只查了前端 |
