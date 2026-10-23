# 摸底报告的主对话复核记录

> **这份文件的作用**：调查员（4 个独立子代理）交回的 4 份事实地图，
> 我（主对话）逐条抽查验证过。**对得上的记「已核实」，对不上的当场更正并留痕**。
> 本仓纪律：「打回的说法必须就地更正并留痕（含我自己写错的）」。

---

## 一、已核实的（抽样，不是全部）

| # | 调查员结论 | 我的复核命令 | 结果 |
|---|---|---|---|
| 1 | `resolve_clause` 年份宽容兜底会跨标准误命中 | 直接调 `ks_resolve_clause("GBZ 188-2025","5.22.3")` | **属实，且已拿到现场**：返回 `GB 6675.2-2025`（玩具标准）的条款正文 |
| 2 | 36 部标准号的兜底 token 抓到的是年份 | `.tmp/probe_fallback_surface.py` | **属实**：8,983 部里 36 部；实测 36 部中 9 部（25%）会误命中别家 |
| 3 | `standard_key` 会丢掉标准号前缀 | 直接调 `standard_key("GB 188-2025")` vs `standard_key("GBZ 188-2025")` | **属实**：两者都得 `188-2025`，撞车 |
| 4 | `auto_tag.py` 没 import `subscriptions` | `Select-String auto_tag.py -Pattern 'import\|subscriptions'` | **属实**：只有 `sqlite_db` / `text_utils`，无 `subscriptions` |
| 5 | `exceptions.py` 4 个异常类全仓零调用 | 逐名 grep `src/tests/scripts` | **属实**：`ConfigError`/`AuthError`/`RetrievalError`/`DuplicateDocumentError` 各仅 1 处（= 定义处本身） |
| 6 | `knowledge` ⇄ `exports` 双向 import | grep 两侧 import 行 | **属实**：`exports/effect_report.py:33-34` → knowledge；`knowledge/folder_store.py:936-937` → exports |
| 7 | `storage` ⇄ `retrieval` 双向 import | `clause_repo.py:13` `from src.core.retrieval import embedder`；`hybrid_engine.py:12` `from src.core.storage.clause_repo import fetch_full_clause` | **属实** |
| 8 | `server.py` 的 `_answer_confidence` / `_expand_title_clauses` 与 `ks_answer.py` 同名同职 | AST 提取两份函数体做 diff | **属实，且比调查员说的更严重**（见下 §三） |
| 9 | `tests/conftest.py` 把 `KS_DATA_DIR` 换成空临时目录 | 读 conftest + 实跑 `--collect-only` | **属实**：3,076 条用例收集，全部在空库上跑 |
| 10 | 6 处 `assert ... or True` 恒真断言 | 逐条读原文 | **属实**：6 个文件各 1 处，原文与调查员给的一致 |

## 二、我**推翻**的调查员结论（留痕）

### 2.1 「`xfail` 完全绕开棘轮，从总账里消失」——**方向错了**

调查员原话（`04-tests-tools-gates.md` §6.4 口子 C）：
> 「把一条用例改成 `pytest.xfail()`，它既不出现在总账里、也不出现在 skip 名单里 ⇒ **棘轮完全看不见**。」

**实测反驳**（`.tmp/probe_xfail2.py`，照抄 `run-gates.ps1` 第 388~436 行的判据）：

```
pytest 汇总行：  1 passed, 1 skipped, 1 xfailed
门禁四个正则：  passed=1  skipped=1  failed=None  errors=None
junit 解析：    全部节点 3 条，其中带 <skipped> 的 **2 条**
                  test_probe::test_is_skipped
                  test_probe::test_is_xfailed      ← xfail 在 junit 里也带 <skipped>
第 435 行判据： ⛔ junit 里认出 skipped=2 条，汇总说 skipped=1 条 ⇒ 判据不可信
                ⇒ 进 $why ⇒ $baselineDrop = true ⇒ **门禁判红**
```

**结论**：`pytest.xfail()` 在 junit 里**带 `<skipped>` 子节点**，而 `run-gates.ps1:398-400`
的 `skipNodeIds` 是按「有没有 `<skipped>`」收的 ⇒ 它**会被收进 skip 名单**。
于是第 435 行的 `skipNodeIds.Count -ne $pytestSkipped` 当场不等 ⇒ **判红**。

⇒ 真实后果**不是「隐身」，而是「假红」**（一条合法的 xfail 会让门禁报「判据不可信」）。
这仍然是个缺陷，但**性质和修法完全相反**：不是「堵漏」，而是「让 xfail 能被正确识别」。
调查员没有实跑（任务书禁止跑门禁），只按「总账公式里没有 xfail 这一项」推断，
漏掉了**第 435 行那条前置一致性判据**。

**保留调查员原话**（不许悄悄删）：原结论仍留在 `04-tests-tools-gates.md` §6.4 口子 C 里，
本条是它的更正。

### 2.2 「`-UpdateBaseline` 在红的跑里照样写基线」——**读代码的结论，我复核为「方向对，但要看门」

调查员自标「没实跑验证」。我复核代码结构：

- 第 614 行 `if ($UpdateBaseline) {` 确实**不在** `if ($why.Count -eq 0)` 里面；
- 但它受 `if ($null -ne $pytestPassed)` 罩着（第 558 行那层 `if` 的 else 分支在 603 行）。

⇒ **成立的前提**是「pytest 这一步拿到了 `passed` 数字」。若 pytest 收集崩了（`passed` 抓不到），
整块不执行 —— 这条调查员自己也写了（引用了脚本第 626~629 行的自述）。

**我的判定**：这条**站得住**，但它是「**红的跑也能记账**」而不是「**任何红的跑都记账**」。
性质上仍是真缺口（先制造 skip → 跑红 → `-UpdateBaseline` 洗白），只是**代价是两次门禁**，
不是「一次就够」。**未实跑验证**（跑一次 `-Full` 约十几分钟，且会写基线，本轮不做）。

---

## 三、比调查员说的更严重的两处（我自己查出来的）

### 3.1 那两个同名函数**不是纯重复，是行为不一致**

AST diff（`.tmp/compare_funcs.py`）实测：

**`_answer_confidence`**（server.py:2559 / ks_answer.py:601）

| 差异点 | server.py | ks_answer.py | 后果 |
|---|---|---|---|
| 空证据 | **不特判**，往下走 | 特判 → `low`「无有效现行证据支撑」 | 同一场景两处给不同档 |
| 字段名 | `is_suspicious` / `type_confidence` | `_is_suspicious` / `_type_confidence`（带下划线） | 把 A 的数据喂给 B ⇒ **静默判 high**（实测：低可信证据被读成「核验通过且证据高可信」） |

**实测输出**（`ks_answer` 版本）：
```
空证据          -> {'level': 'low',  'reasons': ['无有效现行证据支撑（tier=reference）']}
低可信证据      -> {'level': 'mid',  'reasons': ['证据存疑/低可信: 5.22']}
用 server 字段  -> {'level': 'high', 'reasons': ['核验通过且证据高可信']}   ← 字段名不匹配导致漏判
```

⇒ 这不是「可以合并的重复」，是**同一判据两套字段名**。合并前必须先定字段名，
否则合并会把其中一条路的漏判带过去。

**`_expand_title_clauses`**（server.py:2525 / ks_answer.py:1113）

| 差异点 | server.py | ks_answer.py | 后果 |
|---|---|---|---|
| 子条款查询 | 裸 `conn.execute(...)` | `try/except Exception: subs = []` | 一份崩、一份静默降级 |
| 内容长度阈值 | 硬编码 `80` | 常量 `TITLE_CLAUSE_MAXLEN`（=80） | 现在同值，但改一处另一处不会跟 |
| 取全文 | `_fetch_clause(...)` | `fetch_full_clause(...)` | 同名不同实现，未比对 |

⇒ 「注释里写着互相镜像，实现已经分叉」—— 这是本仓最容易腐烂的一种重复。

### 3.2 `server.py` 里那两个函数**在 `create_app` 闭包内，模块外拿不到**

`create_app` 在 `server.py:278`，两个函数在 2525 / 2559 ⇒ 都在闭包里。
实测 `from src.core.api.server import _answer_confidence` ⇒ `ImportError`。

⇒ 后果：**这两条判据没法被单独测试**（拿不到就没法写单测），
所以「两处行为不一致」这件事**没有任何测试能发现**。这是 §3.1 的根因。

---

## 四、调查员明确标注「未做/未读」的（我也没做，如实登记）

| 事项 | 谁标的 | 状态 |
|---|---|---|
| `-UpdateBaseline` 在红的跑里到底写不写基线 | survey-tests | **未实跑**（要跑门禁，本轮不做） |
| `xfail` 的 junit 实际记录形态 | survey-tests | **我已补测**（见 §2.1），结论相反 |
| `tools/gov-qa/data` 634 MB 语料是否含个人信息 | survey-tests | **未读内容**，只看了文件名与条数 |
| `plugin/src/*.js` 56 个 mjs 的静态类型面 | survey-tests | **未读**，超出只读预算 |
| `src/core` 8 个零测试模块的「间接覆盖」有多少 | survey-tests | **未做**（要 `--cov` 跑完整 pytest） |
| `tests/` 3 个未跟踪测试文件是谁、为什么没提交 | survey-tests | **未读**，没有 commit 就没有可查的动机 |
| `storage ⇄ retrieval` 循环 import 的实际后果 | survey-core | 调查员称「靠 import 顺序侥幸」——**我实测两种 import 顺序都 OK**，见下 |

### 4.1 更正调查员的一处措辞

调查员写：「`clause_repo.py:13` 与 `hybrid_engine.py:12` 是**互相顶层 import**，能跑通靠 import 顺序侥幸。」

**实测**（两种顺序都试）：
```
python -c "import src.core.storage.clause_repo"                  → OK
python -c "import src.core.retrieval.hybrid_engine"              → OK
python -c "import hybrid_engine; import clause_repo"             → OK
```
原因：`clause_repo` import 的是 `retrieval.embedder`，`hybrid_engine` import 的是
`storage.clause_repo` —— **不是同一个模块对**，`embedder.py` 自己只依赖
`config` / `exceptions`，没有反向依赖 storage ⇒ **不构成真环**。

⇒ 「双向依赖」在**包级**成立（storage→retrieval 与 retrieval→storage 都有边），
但**不在模块级构成环**。调查员说的「靠 import 顺序侥幸」**超出了证据**，就地更正。
