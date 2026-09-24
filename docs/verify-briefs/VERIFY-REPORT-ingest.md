# 独立复核报告 — `verify-freeze-ingest`（批次：`reference` 效力档 + 公告正文批量入库）

复核者：独立复核代理（证伪导向）。复核对象：冻结提交 `1da33f8`（tag `verify-freeze-ingest`），
基线 `4850f12`，区间 8 笔提交（`git rev-list --count 4850f12..verify-freeze-ingest` = 8，
`git merge-base --is-ancestor 4850f12 verify-freeze-ingest` ⇒ exit 0）。

**取证树（唯一被验的树）**：`D:\vwt-ingest`（`git worktree add D:\vwt-ingest verify-freeze-ingest`）。
依赖是**真拷贝**（非 junction）：`node_modules` 473 文件 / 88,007,819 字节、`plugin/node_modules`
1,635 文件 / 91,904,490 字节，两处 `LinkType` 均为空（= 真目录），与主仓逐字节计数一致
（真拷贝换来的直接收益：`smoke-client-entry` 的"交付产物 ↔ 现构建整份一致"**没有**假红，190/190 过）。
本机真浏览器：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` = True。

**报告首：取证树状态**

```
$ cd D:\vwt-ingest
$ git rev-parse HEAD
1da33f8e378680a2cd3b344a2125777f4f51dce0
$ git status --short
(空)
```

---

## 一、结论：**PASS-with-gaps**

**没有抓到"产品行为错"**：被验区间宣称的每一条功能行为，我都实测到了（含真库只读事实、
交付产物 `plugin/client.js` 与源码现构建逐字节一致、4 套相关冒烟全绿）。真库已被正确迁移、
三数自洽、`foreign_key_check` 干净、16 条 `reference` 与宣称完全对得上。

**但有 2 条 HIGH 与 5 条 MED 的"判据没牙/契约违背/门禁红"**：
- HIGH-1：**把一个会静默删掉 52 万行子表数据的改动放行了**——这正是本批次的主题
  （"判据/门禁"批次 + 触碰真数据）该守住的地方；
- HIGH-2：**冻结提交 `1da33f8` 上 `mypy` 判红（4 处 arg-type）** ⇒ 这个冻结区间
  **不可能门禁全绿**（我已独立复现；作者在**tag 之后**的 `1833281` 自曝并修好，所以**不必改代码**，
  但"全绿"这个记账/口径必须更正）。

另有两处**文档自相矛盾**（做过的事写成没做、被证伪的改法还留着）。

⇒ 建议：**按下面的"改哪一行"清单补判据、并把"冻结区间全绿"这个说法改掉之后再签**；
产品代码本身**不必回滚**（HIGH-2 的修法已在 master 上）。

---

## 二、逐条发现（每条带可复现命令 + 实测输出）

### 复核方法（变异纪律）

- 变异工具：`D:\vwt-tools\mutate.py`（文本级替换，按目标文件行尾折 `\n`；命中数 ≠ 1 即拒绝执行）
  + `D:\vwt-tools\run_mutations.py`（变异 → 跑测 → `git checkout --` → 打印 `git status --short`）。
- **变异/写文件一律绝对路径**；每次还原后 `git status --short` 都为空（见每条的 `status ''`）。
- 测试以**提取树为 CWD** 跑（`python -m pytest`，`sys.path[0] = CWD`），已实测 `src.__file__`
  落在 `D:\vwt-ingest\src`（不是主仓）。

**基线（未变异）**：`tests/test_announce_ingest.py test_legal_status_reference.py
test_effect_report.py test_web_ingest.py test_update_announce.py test_kb_folder_api.py
test_ks_answer.py test_api.py` ⇒ **119 passed**，`-rs` 无 skip 行（这些用例真在跑，不是被跳过）。

---

### HIGH-2 冻结提交 `1da33f8` 上 **`mypy` 判红（4 处 arg-type）** ⇒ 这个冻结区间**不可能门禁全绿**

`mypy` 是 `scripts/run-gates.ps1:215` 的一步，**`-Quick` 与 `-Full` 都跑它**。我在**冻结提交**上
用主仓的 venv（提取树里没有 `.venv`，见第五节）实跑：

```
$ git worktree add D:\vwt-mypy verify-freeze-ingest
$ cd D:\vwt-mypy && "D:\AI\work space\zcode\.venv\Scripts\python.exe" -m mypy
src\core\update\web_ingest.py:224: error: Argument 1 to "classify_scope" has incompatible type "Any | None"; expected "str"  [arg-type]
src\core\update\web_ingest.py:244: error: Argument 1 to "classify_scope" has incompatible type "Any | None"; expected "str"  [arg-type]
src\core\update\web_ingest.py:247: error: Argument 1 to "classify_status" has incompatible type "Any | None"; expected "str"  [arg-type]
src\core\update\web_ingest.py:304: error: Argument 1 to "classify_scope" has incompatible type "Any | None"; expected "str"  [arg-type]
Found 4 errors in 1 file (checked 147 source files)
mypy exit=1
```

这 4 处全在 `ae0d78c`（12:59，本批次新增的 `pending_rows`/`ingest_summary`/`ingest_pending`）里：
`row.get("title")` 的类型是 `Any | None`，而 `classify_scope(title: str)` / `classify_status(title: str)`
要 `str`。

**时间线（决定了该怎么记账）**：

| 时间 | 提交 | 事实 |
|---|---|---|
| 12:42 | `22acad1` | 记 `-Full 全绿`（总账 2380）——**这棵树上还没有那 4 处**，所以那次的绿是真的 |
| 12:59 | `ae0d78c` | 引入 `pending_rows/ingest_summary/ingest_pending` ⇒ 从此 **mypy 红**（只跑了 8 个文件单测） |
| 13:00 | `1da33f8` | **打了 `verify-freeze-ingest` tag** ⇒ 被冻结的就是这棵**mypy 红**的树 |
| 13:11 | `1833281` | **tag 之后**的修复：`row.get("title") or ""` 4 处；提交消息自曝"门禁 -Full 报 7/8 …**这是门禁第一次跑到这批 —— 前一笔提交时只单跑了 pytest**" |

⇒ 两条结论：① **§10.192 那条证据"单跑 … 141 通过"是真的、但它不是门禁**——本批次在 tag 之前
**从未跑过门禁**（作者自己在 `1833281` 里承认）；② 因此冻结区间内的"全绿"字样（`22acad1` 的
commit message / `gates-baseline.json` 的 `updatedAt: 12:42:51`）**只覆盖 tag 之前的那棵树**，
不能读成"被冻结的区间是绿的"。

**行动项（不改代码）**：给这一批的记账补一句"`1da33f8` 上 mypy 红 4 处，已在 `1833281` 修"；
`-Quick`/`-Full` 要在**冻结之后**再跑一次才能说这批绿。**若贵方把"冻结区间必须门禁全绿"当硬门槛，
这条按 HIGH 计是对的**（后果：任何照协议开工的复核者都会在 `-Quick` 上撞红，并误以为是自己的环境问题）。
`1833281` 的内容我核过：4 处 `or ""`，与 4 条报错一一对应，`git merge-base --is-ancestor 1833281 HEAD` 为真。

**附（同一批的第二个假红源，供复核者区分）**：提取树里 `.venv` 不存在 ⇒ `run-gates.ps1` 那一步会走
"命令不存在 ⇒ 判失败（exit 127）"（这是**设计如此**，见 `:252-267`）；要用主仓 venv 才能量到上面这 4 条真错。
再加上 MED-5 的 CRLF 假红 ⇒ **在提取树里跑 `-Quick` 必然红两次，且两次都不是被验代码的罪**
（其中一次不是本批次的罪、另一个是真错）。

---

---

### HIGH-1 `_ensure_legal_status_reference` 的 `PRAGMA foreign_keys=OFF` **零牙齿**：去掉它，整套迁移用例照样全绿；而实测它会**静默删光子表数据**

**变异（去掉 pragma）**

```
$ python D:\vwt-tools\run_mutations.py m5_fk_off_removed
### m5_fk_off_removed :: 去掉 PRAGMA foreign_keys=OFF（保留 finally 里的 =ON）
OK m5_fk_off_removed ...  [src/core/storage/sqlite_db.py]
    2 passed in 0.82s
---- exit=0 ----
reverted src/core/storage/sqlite_db.py
---- git status --short after revert ---- ''
```

被测用例：`tests/test_legal_status_reference.py`（就是为这次重建表写的那个文件，含"真删一行证明级联仍通"）。

**为什么不红（探针实证，不是推理）**

```
$ python D:\vwt-tools\probe_fk_off.py          # 代理连接吞掉 PRAGMA foreign_keys=OFF，其余原样
[BEFORE] doc_meta=1 clause_revision=3 foreign_keys=1
[AFTER ] rebuilt=1 swallowed_pragma_off=1 doc_meta=1 clause_revision=0 foreign_keys=1
[DDL   ] reference in doc_meta DDL = True
[CHECK ] foreign_key_check = []
[CASCADE] 删父行后 clause_revision=0
[VERDICT] 子表数据在迁移中丢失 = True
```

机制：FK 打开时 `DROP TABLE doc_meta` 会先做一次**隐式 DELETE**，`ON DELETE CASCADE` 当场把
`clause_revision / doc_page_geometry / watch_list / user_doc_bookmark` 的子行全部带走。迁移仍然
"成功"（`rebuilt=1`）、`foreign_key_check` 仍然干净、行数校验（只数 `doc_meta`）仍然通过。

用例⑤ 之所以形同虚设：它先 `DELETE FROM doc_meta WHERE doc_id='doc_keep_1'` 再断言子行 0 条——
而子行在**迁移那一步就已经被级联删空了**，`0 == 0` 恒真。用例**没有任何一处**断言"迁移后
`clause_revision` 的行还在"，而四个脚本（`migrate-real-db.py:79`、`apply-real-migration.py:56`、
`verify-real-migration.py:54`）都数了 `clause_revision`——也就是：**这次真库迁移是靠一次性脚本
的自查侥幸守住的，留在仓里的回归判据守不住它**。

真库规模说明代价：迁移前 `clause_revision` **520,504 行**（`var/tmp/migrate-rehearsal.log`），
本次复核只读实测现为 522,021 行。prod 代码目前**是对的**（pragma 在事务外、`commit()` 之后），
所以这不是现网缺陷，而是"下一次有人顺手简化就静默删 52 万行"的敞口。

**改哪一行 / 怎么补**：`tests/test_legal_status_reference.py` 里，迁移前先记
`n_clause = SELECT COUNT(*) FROM clause_revision`，迁移后**先**断言它没变（**在**做⑤那次删除之前），
再断言级联。变异复现：去掉 `src/core/storage/sqlite_db.py:182` 的
`conn.execute("PRAGMA foreign_keys=OFF")`，`python -m pytest tests/test_legal_status_reference.py -q`
现在 2 passed，补完判据后必须变红。

**附（同一句要求的另一半）**：把 pragma "挪进事务内"（删掉它前面的 `conn.commit()`，
`src/core/storage/sqlite_db.py:181`）**也不是有效变异** —— 实测同样 2 passed：
Python `sqlite3` 不对纯 SELECT 开隐式事务，那一刻连接上没有打开的事务，pragma 照样生效。
⇒ 这条 pragma 的**唯一**风险面就是"被删掉"，判据要钉的也正是这个。

**`status ''`（已还原）**

---

### MED-1 引擎侧新端点把校验错误写成 **HTTP 200 + 信封 `code:422`**，与同文件所有其它 4xx 不同口径；host 代理那条 "422 透传" 分支因此**不可达**，非法入参会被界面当成"成功、0 条"

实测（引擎）——`tests/test_announce_ingest.py:290-292` 自己把这条**钉死**了：

```
assert r3.status_code == 200 and r3.json()["code"] == 422      # ← 断言"HTTP 状态是 200"
assert r3.json()["error"] == "invalid_limit"
```

代码位置：`src/core/api/routes_update.py:377-378` 返回裸 dict，而**同一个 `register()` 里另外 20 多处**
4xx 全走 `json_error(...)`（`src/core/api/server.py:327-331`，返回 `JSONResponse(status_code=status…)`，
真 HTTP 状态）。这是本批次新引入的唯一一处偏离。

host 侧后果（`plugin/src/announce.js:681-681` 与 `:689-690`）：

```
if (out.status === 200 && out.body && typeof out.body === 'object') {
  jsonResponse(res, 200, { ok: true, data: out.body.data ?? {} })   // ← 422 信封也走这里，data 变 {}
  return
}
jsonResponse(res, out.status === 422 ? 422 : 502, ...)              // ← 对这条端点不可达
```

客户端 `plugin/client/api.ts` 只在 `!res.ok` 时抛错 ⇒ 界面拿到 `{ok:true, data:{}}` ⇒
显示"本次抓了 0 条…还剩 0 条没进库"，**不会**报错。当前界面固定 `limit: 10`（合法），所以
线上不可达；但这是**面向上线的契约**，任何第三方/脚本传 `limit:"10"` 都会得到假的成功。

复现（只读、不联网——路由用的是 monkeypatch 后的 `ingest_pending`）：

```
$ cd D:\vwt-ingest && python -m pytest tests/test_announce_ingest.py::test_routes_pending_and_ingest_wire -q
1 passed
# 把该用例第 291 行改成 assert r3.status_code == 422（期望的正确契约）⇒ 立刻红 ⇒ 说明当前契约是"200 带信封"
```

**改哪一行**：`src/core/api/routes_update.py:377` 用 `json_error(422, "invalid_limit", "limit 必须是整数")`
（`json_error` 在该 `register(app, json_error)` 作用域内已可用）；同步把
`tests/test_announce_ingest.py:291` 改成 `assert r3.status_code == 422`。host 侧 `announce.js` 的分支
不用改（改完就可达了）。

---

### MED-2 `INGEST_BATCH_MAX`（"条数上限 20"）**没有行为判据**

```
$ python D:\vwt-tools\run_mutations.py m8_no_batch_cap
### m8_no_batch_cap :: ingest_pending 去掉条数上限（只留 limit）
    7 passed, 1 warning in 8.03s
---- exit=0 ----
```

变异体：`n = max(1, min(int(limit or 10), INGEST_BATCH_MAX))` → `n = max(1, int(limit or 10))`
（`src/core/update/web_ingest.py`）。整套 `tests/test_announce_ingest.py` 全绿。

原因：唯一相关断言是 `assert out2["tried"] <= web_ingest.INGEST_BATCH_MAX`（`:257`），而那一跑
待入库只剩 3 条 ⇒ `limit=999` 只抓 3 条，`3 <= 20` 恒真；`limit=999` 这条路**永远碰不到上限**。
`:255` 只断言常量等于 20。

**改哪一行**：`tests/test_announce_ingest.py:256` 的 `out2` 之前先造 >20 条待入库（例如 25 条
`_mk_observed`），然后断言 `out2["tried"] == web_ingest.INGEST_BATCH_MAX`（精确值，不用 `<=`）。

### MED-3 时间预算（`INGEST_BUDGET_S = 45`）**没有判据**；`stop_reason == "budget"` 这条分支**从未被跑过**

```
$ python D:\vwt-tools\run_mutations.py m9_no_budget
### m9_no_budget :: ingest_pending 去掉时间预算判定
OK m9_no_budget ...  [src/core/update/web_ingest.py]
    7 passed, 1 warning in 7.99s
---- exit=0 ----
```

变异体：`if _time.monotonic() - started > budget_s:` → `if False:`。全绿。
仓里对 `stop_reason` 的断言只有 `== "limit"` 与 `is None`（`tests/test_announce_ingest.py:152,253`），
`"budget"` 从未出现。宣称 #7 的三个词里，"时间预算"这一半目前是**纯自然语言宣称**。

**改哪一行**：加一条用例，注入一个"第一次 `_time.monotonic()` 就超预算"的桩（或传
`budget_s=0` 且带一条待入库），断言 `stopped_early is True and stop_reason == "budget" and tried == 0`。

### MED-4 宣称已修的"同一批里同一个 URL 只抓一次"**没有判据**

```
$ python D:\vwt-tools\run_mutations.py m12_no_batch_url_dedupe
### m12_no_batch_url_dedupe :: 去掉「同一次调用里同一 URL 只抓一次」
    7 passed, 1 warning in 8.12s
---- exit=0 ----
```

`grep -r seen_urls D:\vwt-ingest\tests` ⇒ 无匹配。§10.193 缺陷 #2 的修法有三条（加 `standard_no`
钥匙 + 判据按存储形折 + 同一调用同一 URL 只抓一次），前两条有牙（见下 A-3/A-4），**第三条没有**。

**改哪一行**：`tests/test_announce_ingest.py` 新增一条：往两个 `source_id` 下塞同一个 `url`
的 `announcement_observed` 行，跑 `ingest_pending`，断言 `items` 里第二条是
`status=="skipped", reason=="duplicate_url_in_batch"` 且 `tp.calls == [url]`（真只抓一次）。

### MED-5 批次自称"已重生成"的 `docs/tool-catalog.md` 在**提取树**上红 —— 根因是 CRLF（环境假红，非批次罪），但它同时暴露 `smoke-tool-catalog` 是**行尾敏感**的判据（既有脆性）

```
$ cd D:\vwt-ingest\plugin && node scripts/smoke-tool-catalog.mjs --check
FAIL  docs/tool-catalog.md 与真工具定义**漂移**（说明书改了没重新生成？）
  仓库 4526 字 / 生成 4467 字
exit=1
```

**已查清不是漂移**（三条机械事实）：

| 位置 | 字节 | 行尾 |
|---|---|---|
| 提取树磁盘 `docs\tool-catalog.md` | 6,552 | **59 个 CRLF** |
| 提交 blob（`git cat-file blob HEAD:docs/tool-catalog.md`） | 6,493 | 纯 LF |
| 主仓磁盘同路径（只读） | 6,493 | 纯 LF |

6,552 − 6,493 = **59** = 报告里的字数差（4526 − 4467）⇒ 差异 100% 来自行尾；
提交 blob（6,493 字节 / 4,467 **字符**）与生成器输出（4,467 字）**一致** ⇒ 作者的"已 --write 重生成"**属实**。
`git worktree add` 在 `core.autocrlf=true` 下把文本物化成 CRLF，而 `smoke-tool-catalog.mjs:79`
是 `existing === generated` 严格串比、**没有行尾归一**（对比：`smoke-client-entry` 那条有归一，
`plugin/client.js` 就不假红）。`smoke-tool-catalog.mjs` 在本区间**未被改动** ⇒ 既有脆性、非回归。
⇒ **我在提取树里无法复现"门禁全绿"这一步**（详细边界见第五节）。

**改哪一行（可选，防下一个人踩）**：`plugin/scripts/smoke-tool-catalog.mjs:79` 改成
`existing.replace(/\r\n/g,'\n') === generated`（与 `smoke-client-entry` 同口径）。

---

### 文档/数字类（LOW）

**LOW-1 §10.192 的残余清单把"做过的事"写成"还没做"。**
`docs/DEVELOPMENT-HISTORY.md:11286-11287`（冻结态）：

> 2. **抓取侧只做了一半**：翻页发现（切片①）+ 单条入库函数已就绪，**批量抓取 + 界面上那个
>    "入库"按钮还没做**（业主报的"大量应该入库的没入库"要靠它收口）。

而同文件 `:11327` 起 §10.193 正题就是"把已发现的公告批量入正文库"（真机 411 条、设置页新增一格、
两个端点）。第 1 条（真库迁移）被 `~~删除线~~ → 已迁` 就地更新过，第 2 条**没跟着更新**。

**LOW-2 §10.193 仍留着被 `1da33f8` 证伪的那句改法。**
`docs/DEVELOPMENT-HISTORY.md:11400`：

> 4. **宿主侧 `plugin/src/index.js` 还没重载**（`ks_effect_report` 工具少显示第五档）——
>    与 §10.192 第 5 条同一件事，**下次停用/启用 `include:ks-engine` 时一并生效**。

而同文件 `:11297-11299`（`1da33f8` 的就地更正）写着：

> ⇒ **停用/启用不重载宿主侧插件模块**（Node 的 ESM 缓存…）**正确改法是重启一次 DSH**。

`1da33f8` 只改了 §10.192 那一段（`git show 1da33f8 --stat` = 1 file, 8 insertions, 1 deletion），
§10.193 的句子一字未动；而更正段还写着"取证见 §10.193 的'宿主未加载'条"——**它指向的正是那句相反的
话**。任务书要核的"界面/文档说法与 `54059f9` 是否一致"：**界面侧一致**（
`plugin/client/KsSettingsSection.tsx` 404 分支直接说"请重启一次 DSH"），**文档侧自相矛盾**。

**LOW-3 "124 条行政事务被跳过"与实测/同文表格都不一致。**
`docs/DEVELOPMENT-HISTORY.md:11392` 写 **124**；同文件 `:11339` 的表格写 **126**（那是清理前）；
只读复算真库 ⇒ **125**（见第三节）。同一个数在文档里出现两个值、实测是第三个。

**LOW-4 证据数字"141 通过"不可复现。** §10.192 列的那 8 个文件
（`test_web_ingest / test_update_announce / test_legal_status_reference / test_effect_report /
test_kb_folder_api / test_ks_answer / test_api / test_contract`）：

```
$ (在 D:\vwt-f90 = f90bad2，也就是该证据写就的那棵树上)
142 passed, 29 warnings in 14.18s
$ (在冻结树 D:\vwt-ingest 上、同一组文件)
143 passed, 29 warnings in 14.34s
```

方向与量级都对（"~141"），但**没有任何一棵树能打出 141**。

**LOW-5 `effect_report` / 路由的**面向外部**说明还是"四色"。**
`src/core/api/routes_report.py:38`（"效力报告骨架+**四色**统计"）、
`:41`（"`color`：可选 CSV 子集（**red,yellow,green,gray**）"）、
`:58`（排序 "red→yellow→gray→green"）、`src/core/exports/effect_report.py:254`（同上）
—— 这些是 **OpenAPI 可见**的 docstring，`reference` 加档后没同步。功能没问题
（`_normalize_colors` 按 `COLOR_ORDER` 校验，`reference` 可筛），但照文档写客户端的第三方会漏一档。

**LOW-6 `sqlite_db.py:203` 的注释被插入动作撞坏。** 现在是：

```
#: 收藏夹迁移（2026-10 收藏目录）：既有 user_bookmark / user_doc_bookmark 补 folder_id#: 列。schema.sql …
```

`#: 列。` 被拼到了上一行尾（原文是两行）。纯注释错位，无功能影响。

**LOW-7 `var/tmp/migrate-real-db.py` 的 `--rehearse-only` 是**死旗标**。** docstring 第 9 行宣传
"用法：python var/tmp/migrate-real-db.py [--rehearse-only]"，但 `main()` 从不读 `sys.argv`
（全文没有 `sys.argv`），永远先 `make_pristine_backup()` ⇒ 想"只预演"的操作者会**照样写出一份
2.3 GB 快照**。这是**未跟踪的一次性脚本**（`var/*` 被 gitignore），不在仓里，故只登记不改。

**LOW-8 真库脚本报"假失败"的那个错**（作者已自曝，这里给实证 + 影响面）。
`var/tmp/migrate-real-apply.log`：

```
[12:44:12] init_schema() 完成 0.7s
[12:44:12] ❌ 真库迁移有问题：
[12:44:12]    - 数据变了：6417/[('effective', 6417)] → 6417/[<sqlite3.Row object at 0x…>]
```

`apply-real-migration.py:36-37` 用只读连接（`row_factory`=tuple）取 `st_before`，
用 `sqlite_db.get_db_connection`（`row_factory`=sqlite3.Row）取 `st_after`，`Row != tuple` 恒不等
⇒ 迁移**成功**却报失败并 `exit(2)`。**同一个根因还有一处没被自曝**：`migrate-rehearsal.log` 里
"状态分布：[<sqlite3.Row object at 0x…>]"（`migrate-real-db.py:81`）——那行本该是"迁移前后
状态分布不变"的证据，实测打出来的是**对象地址**（拿不到分布）。`verify-real-migration.py:28-30`
已经把两边归一成 tuple，是对的。
影响：这次真库迁移是**在报失败之后**由人再跑 `verify-real-migration.py` 才确认成功的；若换个
操作者信了 `exit 2`，可能去回滚一份**本来就成功**的迁移。

### INFO（不算缺陷，但复核者该知道）

- **INFO-1** 提取树里 `smoke-tool-catalog` 假红的机制已查清（MED-5 的表），
  这是 `git worktree` + `autocrlf=true` 的**提取树环境假红**，与 AGENTS.md 记的
  "junction ⇒ esbuild 打绝对路径 ⇒ `smoke-client-entry` 假红"同一类。
- **INFO-2** `_COLOR_RANK`/`_COLOR_CN`/`COLOR_LABELS`/`COLOR_MEANINGS`/`_empty_colors`
  是 5 处并列表，但都有判据压着（`test_eff_01` 断言 `set(colors)==set(COLOR_ORDER)`；
  `test_eff_08` 按 `COLOR_ORDER` 逐行对 Excel）⇒ 单一出处这条**站得住**，不另立发现。
- **INFO-3** `checklist` 第 6 条（真 token 无字面兜底）：新增的 `<details>` 用了
  `var(--dsw-alias-label-secondary, #666)`（与紧邻的既有 `<details>` 同形），
  新按钮走的是活 token；`smoke-client-entry` 的"写死颜色只许减"棘轮实测 **71 行 / 基线 115** ⇒
  这笔债本批次是**净减少**，不构成发现。

---

## 三、任务书逐条作答（含"能证 FAIL"的那些）

### A. 判据有没有牙 —— 逐条变异（全部实测；括号 = 变异前后）

| # | 变异 | 命令 | 实测 | 有牙？ |
|---|---|---|---|---|
| 1 | `classify_scope` 判序颠倒（排除词优先） | `run_mutations.py m1_scope_order` | **1 failed, 6 passed**（`test_announce_ingest.py:106`：`'non_normative' == 'normative'`） | ✅ |
| 2 | `looks_like_article` 去掉 `endswith("/")` | `... m2_article_no_trailing_slash` | **1 failed, 20 passed**（`test_update_announce.py:163`：多出 `/gk/tzgg/yjglbgg/`、`/fw/dzzz/`） | ✅ |
| 2b | 换成**更严**的规则（".html/.shtml 后缀 或 `t2026…` 文章名"，作者原文口径） | `... m2c_article_strict7` | **8 failed, 13 passed**（作者称 7 条既有用例） | 方向✅ 计数 8≠7 |
| 2c | 同上（我的另一版实现） | `... m2b_article_strict` | **8 failed, 13 passed** | 同上 |
| 3 | `_is_in_library` 去掉 `standard_no` 那把钥匙 | `... m3_is_in_library_no_stdno` | **1 failed**（`test_announce_ingest.py:215`：`pending==1`，`ingest_summary` 报 `{'total':2,'ingested':1,'pending':1}`） | ✅ |
| 4 | `duplicate`/`standard_exists` 改回 `ingested` | `... m4_status_map_ingested` | **2 failed**（`test_announce_ingest.py:198`、`test_web_ingest.py:101`） | ✅ |
| 5 | 去掉 `PRAGMA foreign_keys=OFF` | `... m5_fk_off_removed` | **2 passed, exit 0** | ❌ **HIGH-1** |
| 5b | 把该 pragma 挪进事务（删掉前面的 `commit()`） | `... m5b_fk_off_no_commit` | **2 passed, exit 0**（原因见 HIGH-1 附注：不是有效变异） | — |
| 6 | `STATUS_COLOR["reference"] = "gray"` | `... m6_reference_to_gray` | **3 failed, 47 passed** | ✅ |
| 7 | `folder_store.effect_deep` 改回写死四键 | `... m7_folder_hardcoded_keys` | **1 failed**：`KeyError: 'reference'`（作者称"真机会 KeyError"——**实测就是这么崩的**） | ✅ |
| 8 | 去掉条数上限 | `... m8_no_batch_cap` | **7 passed** | ❌ **MED-2** |
| 9 | 去掉时间预算 | `... m9_no_budget` | **7 passed** | ❌ **MED-3** |
| 10 | `server.py` 不给 `reference` 中文名 | `... m10_basis_label_missing` | **1 failed**（notice 里出现 `该条为「reference」`） | ✅ |
| 11 | `stop_reason` 归因反转 | `... m11_drop_budget_report` | **1 failed** | ✅ |
| 12 | 去掉"同一批同一 URL 只抓一次" | `... m12_no_batch_url_dedupe` | **7 passed** | ❌ **MED-4** |
| 13 | 去掉 `fallback_single_clause=True` | `... m13_no_fallback_single_clause` | **4 failed, 8 passed** | ✅ |

每次还原后 `git status --short` 均为空（工具会打印，且我在会话中另外单独核过若干次）。
"**全绿之后逐条还原**"：变异前 `D:\vwt-ingest` 是干净的（`git status --short` 空），
还原用 `git checkout -- <绝对路径>`，判干净用 `git status --short`（**没用哈希**）。

**作者三条附带宣称的核对**

- "真机因此空转 106 次" ✅：`var/tmp/real-ingest.log` 同一次跑里同时写着
  `合计：入库 478 · 跳过 0 · 失败 2` 与 `doc_meta 6422 → 6794（+372）`，差额 106。
- "372 篇被报成 478 篇" ✅ 同上（这是作者自己的日志，非独立数据源；独立面见第三节真库行数）。
- "更严的规则打红 7 条既有用例" ⚠ 方向属实、**计数 8**（我那版实现；作者没提交那个假想规则，
  无法逐字复现，故不计为缺陷，只登记计数差）。

### B. 断言有没有被换成恒真/放宽

- 新/改用例里**没有** `or True`；`grep -n "or True" tests/test_announce_ingest.py` 无匹配。
- 唯一的放宽型断言：`tests/test_announce_ingest.py:257` `assert out2["tried"] <= web_ingest.INGEST_BATCH_MAX`
  —— 已作为 **MED-2** 处理（它是"上限 20"唯一的行为断言，且恒真）。
- `test_update_announce.py::test_ann_n03b` 的 `looks_like_article(...) is True/False`：
  **不是**恒真（变异 #2 / #2b 都打红了它，且"不带尾斜杠的目录认不出来"这条限制被写成断言，诚实）。
- 精确集合没有被换成"非空"：`test_kb_folder_api.py` 是**整字典相等**
  `{"green":2,"red":1,"yellow":1,"gray":1,"reference":1}` + `sum(e.values())==file_count_deep`；
  `test_effect_report.py` 断言 `set(colors)==set(COLOR_ORDER)` 与 `reference==1 且 gray==1`（不并桶）；
  `test_legal_status_reference.py` 断言迁移前 `IntegrityError`、迁移后行数不变、索引名集合、
  `foreign_key_check` 空、幂等返回 0。⇒ 都是强断言。
- **"依赖可用时那条测试真在跑"**：`pytest -q -rs` 跑那 8 个文件 **119 passed，0 skipped**
  （`-rs` 会打印 skip 理由，一行都没有）。`test_legal_status_reference.py` 若 `sqlite-vec` 缺失会
  在 `executescript(legacy_ddl())` 抛 `no such module: vec0`（我探针第一版就是这么炸的）
  ⇒ 它**不会**被静默跳过，只会红。
- 门禁白名单**没有**被放宽：`scripts/gates-baseline.json` 的 `environmental_skip_nodeids`
  仍是原来那 5 条（只有键序变化），`pytest_skipped` 仍 3。

**测试总账机械对账**（checklist 第 2 条）
- 基线树 `D:\vwt-base`（4850f12）收集 **2375** 条；冻结树 `D:\vwt-ingest` 收集 **2388** 条 ⇒ **+13**。
- 逐 nodeid diff（`D:\vwt-tools\diff_collect.py`）：**+14 新增 / −1 改名**
  （`test_web_i05_draft_refused_honestly_and_failures` → `…_ingested_as_reference_and_failures`）⇒ 净 +13 ✅ 自洽。
- `gates-baseline.json` 记的是 2366 → 2380（**+14**）：那是 `22acad1`（12:42:51，`updatedAt` 可查）
  记的账，而 `ae0d78c`（12:59）之后才加了 8 条（`test_announce_ingest.py` 7 条 + `ann_03b` 1 条）
  ⇒ 冻结提交里的记账**比实际少 8 条**，方向是"棘轮安全侧"（只会提示 `-UpdateBaseline`），**不是**少跑用例。

### C. 真机 / 真数据（**全程只读**）

打开方式：`sqlite3.connect("file:C:/Users/Zegel/AppData/Roaming/KnowledgeStation/database/knowledge.db?mode=ro", uri=True)`
（脚本 `D:\vwt-tools\probe_real_db_ro.py`；任何写操作都会当场报 readonly）。**我没有对真库做任何写操作**。

```
== ① 规模 ==
doc_meta 行数 = 6797        clause_revision 行数 = 522021     announcement_observed 行数 = 536
== ② reference 在不在 DDL 里 ==
doc_meta DDL 含 'reference' = True
doc_meta CHECK 段 = legal_status TEXT CHECK(legal_status IN ('effective','upcoming','superseded','withdrawn','reference')),
update_change_event 含 'reference' = False        ← 作者宣称"故意不动" ✅ 属实
== ③ 四个子表外键仍 doc_meta/CASCADE ==
doc_page_geometry True | clause_revision True | watch_list True | user_doc_bookmark True
   （均为 (0,0,'doc_meta','doc_id','doc_id','NO ACTION','CASCADE','NONE')）
== ④ foreign_key_check ==  rows = 0 []
== ⑤ 索引 == ['idx_doc_file_hash','idx_doc_hierarchy','idx_doc_short_code', +2 autoindex]
== ⑥ mem.gov.cn 来源落库口径 ==
('effective','规范性文件',258) ('effective','其他',84) ('effective','部门规章',18)
('reference','征求意见稿',16) ('withdrawn','规范性文件',3) ('withdrawn','部门规章',1)
合计 = 380        全库 reference 行数 = 16
== ⑦ announcement_observed 三数自洽（用被验代码的判据复算）==
total=536 ingested=411 pending=0 pending_by_status={'effective':0,'reference':0,'withdrawn':0}
skipped_non_normative=125      自洽 = True
栏目导航型残留（url 以 / 结尾）在 observed 里还有: 0   其中已进 doc_meta 的: 0
```

**逐条对任务书的三个只读事实**：① `doc_meta` **6797** 行；② `reference` **在** DDL 里；
③ 四个子表外键**仍** `doc_meta … CASCADE`；④ `PRAGMA foreign_key_check` **干净**。全部 ✅。

**"411 条入库"的口径（重要）**：
- `doc_meta` 里 `source_url LIKE 'https://www.mem.gov.cn/%'` = **380 行**，分档如上（`reference` **16 行**，与宣称**完全一致**）；
- `announcement_observed` 的三数（536 / 411 / 0 / 125）与作者 `real-cleanup.log` 的最终进度**逐字相同**，且 `536 = 411 + 125` **自洽**；
- 但 **411 是"进度计数器"（按 URL 或标题存储形命中库里已有的行数），不是库里的行数增量**：
  真实增量是 **380**（`6797 − 6417 = 380`，恰好等于 mem 来源行数）。
  §10.193 的表格自己写了"`doc_meta` 6417 → **6797**（+380，含最开始的 5 条探针）"⇒ **文档口径是对的**；
  任务书里"入库 411 条公告"这句读起来像"库里多了 411 篇"，**按库核应是 380 篇**（差额 31 = 同一标题
  挂在多个 URL 下、按标题那把钥匙算作"已入库"的重复条目 + 最早 5 条探针）。⇒ 结论：**数字无误、口径要写清**。
- 导航型 URL（以 `/` 结尾）：`observed` 里 **0** 条残留、已进 `doc_meta` 的 **0** 条 ⇒ 22 条清理干净了。

**作者两个自曝错的核对**：
- ① `VACUUM INTO` 耗时 ✅ 属实：`var/tmp/migrate-rehearsal.log` = `快照完成 6.0s，2.30 GB`；
  脚本注释里写的是"（2.3GB，可能几分钟）"（`migrate-real-db.py:36`）⇒ 预估夸张一个量级，作者自曝成立。
- ② `sqlite3.Row` vs tuple 假报"数据变了" ✅ 属实（见 LOW-8，含**未被自曝的姊妹行**：
  状态分布打印成 `<sqlite3.Row object at 0x…>`）。
- 备份快照 ✅ 在：`…\database\backup\knowledge-before-reference-20260924-124338.db`，
  2,304,446,464 字节，`2026/9/24 12:43:42`。

**三个脚本我只"读"没有"跑"**（任务书允许"要么读、要么跑在副本上"；跑它会写 2.3 GB 快照/副本，
且 `--rehearse-only` 是死旗标，见 LOW-7）。`migrate-real-db.py` / `apply-real-migration.py` /
`verify-real-migration.py` 的逻辑逐行读过：预演确实在**快照的副本**上做、真库只读、六项核验齐
（数据/索引/四子表外键/新档可写/**级联真删**/幂等）⇒ 方法论**正确**，唯一的坑是 LOW-8 那个比较形状。

### D. 契约

- **引擎路径/方法**：`GET /api/v1/update/announce-ingest/pending`、`POST /api/v1/update/announce-ingest`
  已注册并可用（`tests/test_announce_ingest.py::test_routes_pending_and_ingest_wire` 1 passed）。
  错误码问题 = **MED-1**（HTTP 200 带 `code:422`）。
- **host 代理**：`GET /ks/announce/ingest/pending`（非 GET ⇒ 405）、`POST /ks/announce/ingest`
  （非 POST ⇒ 405；非法 JSON ⇒ 400 且不下发；引擎不可用 ⇒ 503）——均由 `smoke-lifecycle` C1–C5 覆盖。
- **C1–C5 变异验证（现场做，`D:\vwt-tools\run_plugin_mutations.py`）**：

| 变异 | 实测 | 抓得住？ |
|---|---|---|
| 引擎路径常量 `…/pending` → `…/pendingX` | **C2 PASS（全绿，exit 0）** | ❌ **C2 用 `url.includes('/api/v1/update/announce-ingest/pending')` 判**，后缀型写错是它的前缀 ⇒ 漏 |
| host 侧 `KS_ANNOUNCE_INGEST_PATH` → `…/ingestx` | **C1 FAIL（exit 1）** | ✅ |
| POST 体没转（恒传 `{}`） | **C3 FAIL**（`body={}`） | ✅ |
| POST 走成 GET | **C3 FAIL**（`body=undefined`） | ✅ |
| 去掉 POST-only 405 门 | **C5 FAIL**（200） | ✅ |
| 非法 JSON 当空体接受 | **C4 FAIL**（200, engineCalls=1）+ C5 FAIL | ✅ |

  ⇒ 宣称"能抓引擎路径常量写错/方法写错/请求体没转"**基本成立**，但**引擎路径那一条只对"前缀被改"
  有效**：`…/pending` 后面**追加**任何东西都不红（`/pending/`、`/pending2` 这类真实手滑形态会漏）。
  **改哪一行**：`plugin/scripts/smoke-lifecycle.mjs` 的 C2 把
  `engineCalls[0].url.includes('…/pending')` 换成 `new URL(engineCalls[0].url).pathname === '/api/v1/update/announce-ingest/pending'`
  （C3 那条 `!includes('/pending')` 也同理，但它是反向判据，风险低）。
- **`plugin/client.js` 与源码一致** ✅（这是任务书点名要的）：

```
$ cd D:\vwt-ingest\plugin && npm run build:client
client.js written: 1750074 bytes (1746548 chars)
# 提交 blob 与"从源码现构建"（都按 LF 归一后）：
#   blob 1750074 字节  SHA256 F67711C25E12113DEFDCD519D3AC35EAB7BE4D911C568E1E95186A92DA3E9997
#   rebuilt         SHA256 F67711C25E12113DEFDCD519D3AC35EAB7BE4D911C568E1E95186A92DA3E9997
identical(normalized)=True
$ node scripts/smoke-client-entry.mjs
== client-entry smoke PASS (190/190) ==   exit=0
```

  （工作区那份磁盘字节数 1,792,284 是 CRLF 物化，非产物差异；与 AGENTS.md 记的同形。）
  产物里**确实带了新功能**（按 esbuild 的 `\uXXXX` 转义形态查）：
  `把公告正文入库`×1、`把新公告入库`×1、`本次抓了`×1、`入库中…（正在抓正文）`×1、
  `ks/announce/ingest`×2、`ks/announce/ingest/pending`×1。
- **其余相关冒烟**（提取树实跑）：`smoke-effect-tool` **70/70 PASS**、`smoke-tool-contract`
  **136/136 PASS**、`smoke-kb-page-render` **188/188 PASS**、`smoke-lifecycle` exit 0（C1–C5 全 PASS）。
  `smoke-tool-catalog --check` 红 → **MED-5（环境假红）**。

### E. 作者的三处"我错了"

- **§10.192 的更正（`1da33f8`）**：`git show 1da33f8 --stat` = 只改 `docs/DEVELOPMENT-HISTORY.md`
  （8 insertions / 1 deletion），内容 = 把"停用/启用即可重载"就地更正为"**正确改法是重启一次 DSH**"，
  并留了错话原文与方法论（"我写那句改法时没先验，是猜的"）。**与 `54059f9` 一致**：
  `plugin/client/KsSettingsSection.tsx` 的两处 404 分支都写"请重启一次 DSH"。
  **但**：§10.193 `:11400` 还留着被证伪的那句（**LOW-2**）。我**没有**去重启宿主、也没动运行中的插件。
- **§10.193 的三条真机缺陷**：
  1. 假"入库成功" ✅ 代码（`already_in_library` + `ingest_kind`）+ 用例都有牙（变异 #4 = 2 failed）；
  2. 反复重抓 ✅ 两半有牙（变异 #3 = 1 failed；标题按 `store_standard_no` 折过也在用例里断言），
     第三半"同一批同一 URL 只抓一次"**没有判据**（**MED-4**）；
  3. 栏目导航当公告 ✅ 有牙（变异 #2 = 1 failed；真机 22/22 以 `/` 结尾、`observed` 里现已 0 残留）。
- **"明确未做/待业主定"清单**：① 124 条（实测 125，**LOW-3**）；② 25 页 510 条 vs 站点 `dataCount=849`
  （未联网核，登记为未验）；③ 84 篇 `其他`（✅ 实测 mem 来源 `其他`=84）；④ 宿主未重载（事实对、
  **改法自相矛盾 = LOW-2**，且**没有**把"已做"写成"没做"——它确实没做）；⑤ 界面入口没在真机点过
  （✅ 诚实，我也点不了）；⑥ 已派独立复核（= 本报告）。**但** §10.192 的残余第 2 条把**做过**的
  "批量抓取 + 入库按钮"写成**没做**（**LOW-1**）。

---

## 四、分级汇总

| 级别 | 编号 | 一句话 |
|---|---|---|
| **HIGH** | HIGH-1 | 去掉 `PRAGMA foreign_keys=OFF` 后迁移用例**全绿**，而实测该变异会静默删光子表数据（真库 52 万行级）；用例⑤的级联断言恒真 |
| **HIGH** | HIGH-2 | **冻结提交上 `mypy` 红 4 处**（独立复现）⇒ 本冻结区间不可能门禁全绿；修法在 tag 之后的 `1833281`（作者已自曝），要改的是"全绿"这个记账 |
| MED | MED-1 | 新端点把 422 写成 HTTP 200 + 信封；host 代理的 422 分支不可达 ⇒ 非法入参被界面当"成功 0 条" |
| MED | MED-2 | "条数上限 20"无行为判据（去上限全绿） |
| MED | MED-3 | "时间预算 45s"无判据；`stop_reason=="budget"` 从未被跑过 |
| MED | MED-4 | "同一批同一 URL 只抓一次"无判据 |
| MED | MED-5 | `smoke-tool-catalog` 行尾敏感 ⇒ 提取树假红（既有脆性，非本批改动的罪，但会误导复核者） |
| LOW | LOW-1 | §10.192 残余第 2 条把"批量入库 + 界面按钮"写成还没做 |
| LOW | LOW-2 | §10.193 `:11400` 仍写"下次停用/启用时一并生效"，与 `1da33f8` 的更正相反 |
| LOW | LOW-3 | "124 条行政事务被跳过"（实测 125；同文表格写 126） |
| LOW | LOW-4 | 证据"141 通过"不可复现（f90bad2 实测 142、冻结树 143） |
| LOW | LOW-5 | `routes_report.py` / `effect_report.py` 的 OpenAPI docstring 仍是"四色 red,yellow,gray,green" |
| LOW | LOW-6 | `sqlite_db.py:203` 注释被插入撞坏（`补 folder_id#: 列。`） |
| LOW | LOW-7 | `migrate-real-db.py` 的 `--rehearse-only` 是死旗标（照写 2.3 GB 快照） |
| LOW | LOW-8 | `apply-real-migration.py` 的 Row/tuple 假失败（+ 姊妹行：状态分布打印成对象地址） |
| INFO | INFO-1~3 | 提取树 CRLF 假红的机制；五处并列表都有判据压着；写死颜色是净减少 |

**没抓到 FAIL 的理由**（诚实写明，不是"没查"）：被验的**产品行为**没有一条是错的 ——
生效档迁移在真库上正确落地（只读事实四条全对）、`doc_meta`/`observed` 三数自洽、
16 条 `reference` 与宣称逐字相同、交付产物与源码现构建逐字节一致、相关冒烟全绿。
上面这些是**判据的洞**与**文档的自相矛盾**，不是错误行为。
**唯一"真红"在冻结区间里的是 HIGH-2（`mypy` 4 处）** —— 但它已被 tag 之后的 `1833281` 修好，
且修法（补 `or ""`）与 4 条报错一一对应 ⇒ 归"记账/口径"而不是"要回滚的产品缺陷"。
另一处红（`smoke-tool-catalog --check`）已用三条机械事实证明是提取树行尾假红（INFO/MED-5）。

---

## 五、我**没有**验的部分（诚实列清）

1. **没有跑整条 `run-gates.ps1`**（`-Quick`/`-Full` 都不行）：主仓此刻在跑 `-Full`（锁只允许一次一个），
   我**不并发跑**、也**不绕过锁**跑 `smoke-all.mjs`。取而代之：① 独立跑了 `-Full` 与 `-Quick` **都包含**的
   `mypy` 那一步（用主仓 venv，见 **HIGH-2** ⇒ 冻结树上**红**）；② 跑了改动相关的 8 个测试文件单跑
   （119 passed / 0 skipped）；③ 跑了 4 套相关冒烟；④ 生成物比对；⑤ 交付产物现构建比对。
   所以"**整链全绿**"这句宣称在本报告里**既未证实也未证伪**，但其中**已知有一步是红的**。
   ⚠ 顺带：提取树里 `run-gates.ps1` 的 mypy 那一步会因 `.venv` 缺失而走"命令不存在 ⇒ exit 127"
   （设计如此），那是**环境红**，别与 HIGH-2 的真错混为一谈。
2. **没有**跑需要真浏览器的三套冒烟（`smoke-kb-pad-pixels` / `smoke-kb-cols` / `ui-badge-pixels`）
   ——本机有 Edge，但它们只在 `smoke-all` 名单里，见第 1 条。
3. **没有**在真机点设置页那一格（要求业主点一次才算真验；也不该为了复核去重启宿主）。
4. **没有**跑三个真库脚本（只读它们 + 只读核验真库本体）；因此"预演 2.4s / 真库 0.7s"这两个耗时
   引自作者日志，非我实测。真库上的**写路径**（探针插删/级联）我没重放——那要写真库，明令禁止。
5. **没有**联网核 `通知公告` 源 `dataCount=849` vs 25 页 510 条（"差的 339 条"）。
6. **没有**独立复现 `plugin_manager` 停用/启用**不**重载宿主插件模块这条（不许动运行中的宿主插件）；
   只核了"文档 vs 代码 vs 提交 `54059f9`"三者的一致性（发现 LOW-2）。
7. **没有**逐条重放区间里 8 笔提交的每一处 UI 像素（`KsKnowledgePage` 的五色灯只做了**源码级**核对：
   `:3577` 提示行含五档、`:3582` `edN('reference') ? ' 🔵N' : ''` 与非零才显示一致）。
8. §10.193 引用的真机数字里，凡是**只有作者日志**能给出的（478/372/106、各批耗时、失败原因
   `fetch_failed`），我只能核到"日志文本内部自洽 + 与库内行数一致"，**不能**算独立复现。

---

**报告尾：取证树状态**

```
$ cd D:\vwt-ingest
$ git rev-parse HEAD
1da33f8e378680a2cd3b344a2125777f4f51dce0
$ git status --short
(空)
```

（复核期间所有变异都在 `D:\vwt-ingest` 内完成并已 `git checkout --` 还原，`git status --short` 逐次为空；
辅助脚本落在仓外 `D:\vwt-tools\`（不在任何被验树里）；主仓代码**一个字节都没改**
——本报告写入 `var\tmp\verify-reports\`，该路径被 `.gitignore` 的 `var/*` 覆盖。
`D:\vwt-base`(4850f12)、`D:\vwt-f90`(f90bad2)、`D:\vwt-ingest`、`D:\vwt-mypy`(1da33f8，只用于跑 mypy)
四棵是我建的，收尾已 `git worktree remove`；`D:\AI\work space\zcode-verify-chans` 是**别人的**，我没碰。
主仓在我复核期间前进了 1 笔：`1833281`（`fix(mypy)`，即 HIGH-2 的修复），除此之外
`1da33f8..HEAD` 与冻结区间无关。）
