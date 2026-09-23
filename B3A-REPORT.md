# B3a 实施报告 —— 「补全分类号」引擎侧第二轮（CCS 自愈）

- 工作树（唯一）：`D:\AI\work space\zcode-b3a-ccs`，分支 `b3a-ccs-engine`，基点 `4ed4b0d`
- 提交（第一轮）：**`0f05026`**（引擎 + 接口）· **`180397f`**（18 条新用例）· **`72082a0`**（本报告）
- 提交（第二轮复核 F1–F4）：**`ffcb65e`**（引擎修复）· **`359ffac`**（4 条新用例 + 真值表改正）·
  本报告更新随第三笔提交 —— 见 **§9**
- 提交前/后 `git status --short` 均**空**；`plugin/` **零改动**（`git diff --stat 4ed4b0d..HEAD` 只列
  src 4 个 + tests 1 个 + 本报告）
- 真库（`%APPDATA%\KnowledgeStation\database\knowledge.db`）：**本次零访问**（没读也没写；
  所有用例与复现脚本都在自己的临时 `KS_DATA_DIR` 里跑）
- 未做：真库 330 篇回填（业主只授权做机制）· `scripts/run-gates.ps1` · `npm run smoke` · `plugin/**`（B3b）

## 0. 真跑出来的数字（原始输出摘抄）

| 跑的东西 | 命令（cwd = 我的树） | 结果 |
|---|---|---|
| 改前基线（单文件） | `python -m pytest tests/test_ccs_chain.py -q` | **36 passed**, 5 warnings in 1.84s |
| 第一轮后（单文件） | 同上 | **54 passed**, 5 warnings in 2.99s（+18 条新用例） |
| 第一轮后（全量） | `python -m pytest -q` | **2353 passed, 4 skipped**, 32 warnings in 281.60s，**exit 0** |
| 第二轮复核 F1–F4 后（单文件） | 同上 | **58 passed**, 5 warnings in 3.29s（再 +4 条） |
| 第二轮复核 F1–F4 后（全量） | `python -m pytest -q` | **2357 passed, 4 skipped**, 30 warnings in 277.05s，**exit 0** |
| HIGH-1 端到端复现（父代理的脚本） | `python var\tmp\repro-ccs-high1.py D:\AI\work space\zcode-b3a-ccs` | 见 §5.1（**PASS**，第二轮后复跑仍 PASS） |

全量里 0 failed ⇒ 我改到的 `ccs_store.apply_ccs_tag`（追加→替换、写路径严格化）/`ccs_backfill`/
CCS 路由 **没有打翻任何既有用例**（其余测试文件我一行没改）。

## 1. 补之前自动备份一次（业主点名第①条）

**做了什么**
- 新增 [`src/core/knowledge/ccs_undo.py`](src/core/knowledge/ccs_undo.py)：
  - `write_undo_journal(items, scope=…, force=…, limit=…, db_path=…)`：
    只记**这一批会改的那几篇**的旧值 —— `doc_id` / `standard_no` /
    `domain_tags`（**原文**，改前是 NULL 就记 null）/ `doc_ccs_state` **整行**（没有就 null）。
    落到 **`backup._backups_dir()`**（既有快照那个备份目录，**尊重 `KS_BACKUP_DIR`** ——
    本模块**不自己拼** `data_dir/backups`）。文件名 `ccs-undo-<YYYYmmdd-HHMMSS>-p<pid>.json`
    （看得出谁、什么时候；同秒多批加序号不覆盖），内容含 `kind`/`journal_version`/`created_at`/
    `pid`/`batch{scope,force,limit,doc_count}`/`records[]`。
  - 写盘是 **`.part` + `fsync` + `os.replace`**（原子：要么整份在、要么没有）；
    失败 ⇒ 抛 `KnowledgeStationError(code="ccs_undo_failed")`，并清掉半成品。
  - `revert_ccs_backfill_journal(journal_path=None, db_path=None)`：省略路径 = 备份目录里
    **最近那一份**。逐条按"库里现在的样子 vs 记录里的改前样子"**逐字比**：
    已经一样 ⇒ 记 `skipped`（理由"已经是改前的样子"）；`domain_tags` 不同 ⇒ 原文写回；
    台账改前没有 ⇒ **删掉那一行**；改前有 ⇒ 整行写回（含 `checked_at`/`applied_at`）；
    改前就没有这一篇 / 现在被删了 ⇒ `skipped` 并写明理由（**不重建**被删的文档）。
    返回**真做出来的数字**：`restored`/`skipped`/`restored_docs[]`/`skipped_docs[{doc_id,reason}]`/
    `skipped_reasons{原因:几篇}`。
- [`ccs_backfill.start_ccs_backfill`](src/core/knowledge/ccs_backfill.py#L445)（`:481-489`）：
  **起线程之前**写这份记录（"全部补完"时覆盖**整批**、不是一页一份），写不成 ⇒ **一篇都不写**、
  放锁、原样抛（路由映射 **500** `ccs_undo_failed`）。一篇候选都没有 ⇒ 不写空文件（没有要改的东西）。
  路径同时出现在**起跑返回值** `undo_journal` 与**状态** `status()["undo_journal"]` 里。
- 回退函数记的三处：`domain_tags` 原文 + `updated_at` 原文 + `doc_ccs_state` 整行
  （第三处是复核 F2 补的 —— 写标签那一步会刷 `updated_at`，只退前两处不算"逐字回到改前"）。
- 为什么不是 `create_snapshot()`：实测一份 = 2.2 GB，而这个动作可以按很多次 ⇒ 精确回退记录
  满足"补前有备份 + 留回退说明"，且不制造 2.2 GB×N（`ccs_undo.py` 模块头写了这段理由）。

**判据在哪**
- `tests/test_ccs_chain.py::test_undo_journal_is_written_before_the_first_write`（`:888`）：
  **第一次网络查询发生时**，记录已在盘上，且 `doc_ccs_u1`/`doc_ccs_u2` **都还是改前的原文**
  （一个字都没写库），记录内容 = 改前值、状态接口下发的路径 == 起跑返回的路径。
- `::test_undo_journal_honours_ks_backup_dir`（`:937`）：`KS_BACKUP_DIR` 指到别处 ⇒
  记录就落在那里（`p.parent == ext`）。
- `::test_backfill_refuses_to_start_when_journal_write_fails`（`:958`）：写不成 ⇒ 抛
  `ccs_undo_failed`、库里**没标签没台账**、锁已放掉、恢复后立刻还能起一批。
- `::test_revert_restores_tags_and_ledger_verbatim`（`:992`）：两种改前样子（无台账行 / 有台账行）
  都**逐字**回到改前（`_raw_tags` 比原文，台账比 11 列整行）。
- `::test_revert_twice_is_safe`（`:1031`）：第二次 `restored=0, skipped=1`，理由是
  "已经是改前的样子"，库内状态一字未变。
- **反向**：`::test_revert_does_not_touch_docs_outside_the_batch`（`:1053`）——
  同一批之外的两篇（一篇同样缺号、一篇已有号）的 `domain_tags` 原文与台账行**逐字未变**。

## 2. 界面要知道"还剩多少 / 为什么停"（业主点名第②条）

**做了什么**
- `stop_reason`（`ccs_backfill.py:74-93`，七个**互斥**值 + `STOP_REASON_LABELS` 中文说法）：
  `no_candidates`（一开始就没候选）/ `exhausted`（候选扫完了）/ `limit`（到量）/
  `hard_cap`（到硬上限）/ `selected_done`（勾选的那几篇跑完，全库还有别的）/
  `cancelled`（被按停）/ `error`（这一批自己出错）。决策函数
  `_decide_stop_reason()`（`:397`）优先级：`cancelled` > `hard_cap` > `selected_done` >
  `limit` > `exhausted`；`error` 由异常路径直接设。**不许合并成一个"结束"**。
  状态下发 `stop_reason` + `stop_reason_label`；`summary` 另外下发整张
  `stop_reason_labels`（界面照既有口径只兜底，不自己编话）。
- `missing`（保留，现算）拆开：`missing_split()`（`:178`）—— `never_checked`（台账里没这一行）/
  `checked_not_found`（`outcome='not_found'`）/ `checked_failed`
  （`outcome in (network_failed, parse_failed)`）/ `not_applicable`（号不像标准号，真库那 7 篇法规；
  **不并进"失败"** —— 那不是失败）/ `found_but_untagged`（台账说 `found`、标签却不在）。
  **五桶之和 == `total`**（恒等式有用例）。
- `summary` 另下发 `max_batch` / `default_batch` / `max_all`（`:533-540`）。

**判据在哪**
- `::test_missing_split_partitions_and_tracks_each_bucket`（`:1084`）：五桶各 +1（增量判，
  会话级库里还有别人的篇）、`五桶之和 == total == missing_ccs_count()`。
- `::test_stop_reason_limit_selected_done_and_no_candidates`（`:1120`）：三种真实现场各得各的值
  （`limit` 还断言 `truncated=True` 与 `plan_total>1`；`no_candidates` 还断言 `queued=0` 且
  `undo_journal=None`）。
- `::test_decide_stop_reason_truth_table`（`:1157`）：七值真值表（`exhausted`/`hard_cap`/`cancelled`
  在会话级库里造不出稳定现场 ⇒ 直接钉纯决策函数），并断言七个值两两不同、七句中文说法不重样。
- `::test_stop_reason_exhausted_when_plan_had_no_remainder`（`:1186`）：注入"没有剩余候选"的计划 ⇒
  `exhausted`，且 `missing_split.total == missing` 照样现算下发。

## 3. 「一次补完」的选择（业主点名第③条）

**做了什么**
- `MAX_BACKFILL_ALL = 2000`（`ccs_backfill.py:70`，带理由注释：真库 6417 篇/380 篇缺号，
  一篇一到几秒再加每篇 1s 间隔 ⇒ ≈3~5 小时；没上限就是关不掉的几小时后台进程）。
- `start_ccs_backfill(..., all_docs=True)`（`:445`）：取**全部候选**（`plan(limit=0)`），
  超过硬上限就截到 2000 并置 `hard_capped=True`；**按 `MAX_BACKFILL_DOCS`(200) 一页一页串行**
  （`_paginate()` `:264` → `_run(pages,…)`，状态里 `page`/`pages` 如实；页与页之间照样歇 1 秒）；
  到上限 ⇒ `stop_reason="hard_cap"` + `missing/missing_split` 说清**还剩多少**，**不假装补完**。
  仍受"同一时刻只跑一批"（409）与"按停"约束。
- 候选名单**只算一次**（不是每页重算）：失败的篇没有标签 ⇒ 永远是候选，逐页重算会把同一批失败篇
  反复捞回来、变成死循环（这条写进 `_run` 的注释）。
- 路由：`POST /kb/ccs/backfill {"all": true}`（`routes_kb_folders.py:593`）；默认仍是**一批 50**
  （`DEFAULT_BACKFILL_DOCS` 未动、路由默认值未动）；`all` 与 `doc_ids` 同时给 ⇒ **422**
  （"全部"与"只补勾选的这几篇"是两件事）；`all` 时 `limit` 不再被强制 1~200。
- **既有界面不受影响**：`plugin/client/api.ts` 只在显式传 `limit` 时才带 `limit`（读该文件确认），
  所以老调用照旧走默认 50；新字段是**只增**（`undo_journal`/`pages`/`hard_capped`），
  界面类型没读它们也不会坏。

**判据在哪**
- `::test_all_mode_pages_serially_and_stops_at_hard_cap`（`:1210`）：把 `MAX_BACKFILL_DOCS=1`、
  `MAX_BACKFILL_ALL=2` ⇒ `queued=2, pages=2, hard_capped=True, plan.total>2`；
  **反向三条**：① 同一篇**不许被查两次**（`len(set(seen))==2`）；② 到上限后**没被选中的篇一篇没动**
  （`missing` 净减 == 2，且未被选中的三篇标签仍 `[]`、台账仍 None）；③ 停的是 `hard_cap`，
  **不是** `exhausted`。
- `::test_all_mode_refuses_doc_ids_and_allows_zero_limit`（`:1257`）：`all+doc_ids` ⇒ `ValueError`；
  `all + limit=0` 能跑（不再 422）。
- `::test_api_ccs_backfill_all_flag`（`:1425`）：HTTP 级 —— `{"all":true,"limit":0}` ⇒ 200 且
  `hard_capped=True`、`undo_journal` 有值、跑到 `stop_reason=hard_cap`；`{"all":true,"doc_ids":[…]}`
  ⇒ **422**。
- `::test_api_ccs_summary_reports_stop_reasons_and_split`（`:1408`）：`max_all>0`、
  `stop_reason_labels` 七个键、`missing_split` 五桶恒等式、`backfill.undo_journal` 在位。

## 4. 更正那句不实的注释（复核 MED-4，留痕）

**做了什么**：`ccs_backfill.py` 模块头第 3 条**保留错话原文**并紧接"更正"，写清为什么：
错话「所以补全再跑一遍就是 0 篇；标签靠 `apply_ccs_tag` 追加，重复补同一个号不会写第二条」；
更正：那句话**只对补到的篇成立、对没补到的篇是假的** —— 复核实测第二次 `queued=1`、`checked_at`
被改写；`not_found`/`network_failed`/`parse_failed`/`not_applicable` **都会重查**（这正是"再点一次
重试失败篇"的机制），补到的篇才不重进候选（`force=True` 除外）。同时点明状态里 `missing_split`
把这个拆开如实下发。另外 `ccs_store.py` 模块头第 1/2 条也按同样方式留痕更正了"追加"的说法。

**判据在哪**：`::test_revert_twice_is_safe` / `::test_missing_split_partitions_and_tracks_each_bucket`
（拆分）；注释本身由 `::test_backfill_rerun_is_noop`（既有）+ `::test_stop_reason_*` 一起兜住
（"补到的篇再跑 = 0 篇"与"没补到的篇仍是候选"各有用例）。

## 5. 复核抓到的真缺陷

### 5.1 HIGH-1：`force=True` 刷新追加第二条标签 ⇒ 刷新静默无效

**做了什么**：[`ccs_store.apply_ccs_tag`](src/core/knowledge/ccs_store.py#L109) 改成
**一篇只保留一条 `CCS:` 标签**：没有 ⇒ 追加（别的位置的标签一个不动）；有且不同 ⇒ **就地替换**
（`replaced` 如实给旧值）；有且相同 ⇒ 一个字不改（`applied=False`）；历史遗留的多条 ⇒ 顺手收成一条。
`ccs_backfill._run` 把 `res["replaced"]` 记进逐篇结果。

**判据在哪**
- `::test_apply_ccs_tag_replaces_instead_of_appending`（`:1274`）：`["消防","CCS:K41…"]` + 新码
  ⇒ `["消防","CCS:C65…"]`（位置不变、只有一条 CCS、`消防` 没动）；同号重放 `applied=False`；
  两条遗留 CCS 也收成一条。
- `::test_force_refresh_tag_and_tree_read_the_same_code`（`:1300`）：`force=True` 刷新后
  **台账 `ccs_code` == 分类树 `level4` 的码**（旧实现下必红：树读第一条还是 K41）。

**端到端对照（父代理给的复现脚本，原样跑在我的树上）** —— 改前冻结树是 `FAIL`（两条 CCS），
我的树：

```
tree         = D:\AI\work space\zcode-b3a-ccs
domain_tags  = ['CCS:C65 劳动安全技术']
CCS 条目数    = 1   (期望：刷新后仍是 1)
读侧 ccs_tag  = CCS:C65 劳动安全技术
台账 ccs_code = C65
分类树 level4 = C65 劳动安全技术
台账 / 读侧 / 分类树 一致 = True   (期望 True)
VERDICT = PASS（只有一条、三处一致）
```

脚本**一个字没改**（只读跑，`var\tmp` 下的原件未动）。

### 5.2 MED-5：`_run` 没有 try/finally ⇒ `running` 与锁永久卡死

`_run`（`ccs_backfill.py:284`）整段包进 `try/except/finally`：`finally` 里**无论如何**都
`stop_reason`（没设就按决策函数定）+ `running=False` + `finished_at` + `_release()`；
循环体外的异常落 `stop_reason="error"` 并把异常话写进 `last_error`（**不冒充"补完了"**）。
判据 `::test_run_loop_error_does_not_wedge_running_and_lock`（`:1370`）：注入让 `_update_counts`
抛 `RuntimeError` ⇒ 5 秒内 `running` 必须变假、`_LOCK.locked() is False`、`stop_reason=="error"`，
并且**恢复后立刻还能再起一批**（`doc_ccs_lk1` 真落台账）。

### 5.3 MED-1 + MED-2：异常按类型如实归类 + 那条路径的用例

`classify_backfill_exception()`（`:232`）：`ConnectionError/TimeoutError/socket.gaierror/
socket.timeout` 与 `httpx.*`/`curl_cffi.*`（**按模块名判**，不 import httpx —— `ccs_fetcher`
的纪律是绝不碰 httpx 构造）⇒ `network_failed`；**其它一律** ⇒ `parse_failed`，
reason 逐字写"补全时内部出错（代码缺陷，不是网络问题、也不是查无）：RuntimeError: …"，
attempts 记 `{"layer":"internal","result":"internal_error"}`。

> ⚠ **为什么不新造第 6 个 outcome**：`doc_ccs_state.outcome` 有 **CHECK 约束**（`schema.sql:766`）、
> 真库**已建表**，加新值 ⇒ 老库写入时直接 `CHECK constraint failed`。这一批的承诺是
> "纯追加、真库零迁移"，所以选最近的那个桶、把真话写在 `reason`/`attempts` 里
> （与既有"内部不一致 ⇒ parse_failed"同一口径）。这是**有意为之的取舍**，登记在案。

判据 `::test_backfill_classifies_exceptions_by_type_not_all_network`（`:1331`）：同批两篇，
`ConnectionError` ⇒ 台账 `network_failed`；`RuntimeError` ⇒ 台账 `parse_failed` 且 reason 含
"内部出错"+`RuntimeError`、**不含**"网络层出错"，attempts 是 `internal/internal_error`；
状态 `failures` 两种结论各是各的；`last_error` 非空（顺手盖住 LOW-5）。
这条同时补上了复核说的"变异存活"（把该路径的台账写入改成 `pass` 现在必红）。

### 5.4 LOW-4 / LOW-5

- LOW-4：删掉了 `_run` 里 `state = ccs_store.get_ccs_state(doc_id)`（赋值后全文无引用，
  每篇白查一次库）—— 现在只 `SELECT domain_tags`（幂等护栏本来只要它）。
- LOW-5：`_PROGRESS["last_error"]` **真填**：逐篇失败时写 `"<标准号>：<原因>"`（第一条不覆盖），
  循环体外出错时写"这一批自己出错了（…）"。`::test_backfill_classifies_exceptions…` 与
  `::test_run_loop_error_…` 各断言一次。

## 6. 变异自证（两条，都真跑了、都红、都还原）

**规则遵守**：变异前 `git status --short` **空**（两笔提交都已落）；变异只在我的树里写（**绝对路径**）；
还原用 `git checkout -- <绝对路径>`；**用 `git status --short` 判还原**（不看哈希 —— 本机
`core.autocrlf=true` 会让哈希骗人），并额外 grep 变异标记确认残留为 0。

### 变异 A：把"写盘前先备份"那一步短路

改 `ccs_backfill.py`：`if items:` 里那段 `ccs_undo.write_undo_journal(...)` 换成 `pass`（标 `MUTATION-A`）。

```
$ python -m pytest tests/test_ccs_chain.py -q -k "undo_journal or refuses_to_start_when_journal"
        monkeypatch.setattr(_undo, "write_undo_journal", flaky_write)
>       with pytest.raises(KnowledgeStationError) as ei:
E       Failed: DID NOT RAISE KnowledgeStationError
tests\test_ccs_chain.py:975: Failed
FAILED tests/test_ccs_chain.py::test_undo_journal_is_written_before_the_first_write
FAILED tests/test_ccs_chain.py::test_undo_journal_honours_ks_backup_dir - Typ...
FAILED tests/test_ccs_chain.py::test_backfill_refuses_to_start_when_journal_write_fails
3 failed, 51 deselected, 5 warnings in 1.11s
```

还原后：`git status --short` 空 · `MUTATION-A 残留行数 = 0`。

### 变异 B：把 `try/finally` 去掉（except 里 `raise`，`finally:` → `if True:`）

```
$ python -m pytest tests/test_ccs_chain.py -q -k "run_loop_error"
E       AssertionError: 条件在 5.0s 内没成真（用例不该挂在这里）
tests\test_ccs_chain.py:1488: AssertionError
FAILED tests/test_ccs_chain.py::test_run_loop_error_does_not_wedge_running_and_lock
1 failed, 53 deselected, 6 warnings in 5.40s
（同一跑里还有 PytestUnhandledThreadExceptionWarning: Exception in thread ks-ccs-backfill
  ... _update_counts(rec) ... RuntimeError: boom —— 异常真的冒出了线程、running 与锁再没人放）
```

还原后：`git status --short` 空 · `MUTATION-B 残留行数 = 0` · `finally:` 回到 `:388`；
并且**重跑一遍**：`54 passed` + 复现脚本 `VERDICT = PASS`（还原是真还原，不是"看 git 说干净"）。

## 7. 我明确没做的（不许读成"做了"）

- **真库回填 330 篇**：没做（业主只授权做机制）。真库本次**零访问**（没读也没写）。
- **MED-3**（captcha/限流短路与归类）· **LOW-6**（`use_network=False` 的措辞）·
  **LOW-7**（409 的 HTTP 级用例）· **LOW-1/LOW-2/LOW-3**（界面侧）：**未做**，只登记。
- **界面（B3b）**：`plugin/**` 一行没改（本报告只**读过** `plugin/client/api.ts` 确认兼容性）。
- **回退函数没开 HTTP 端点**：只在引擎侧（任务书只要求"引擎侧 + 状态里下发路径"）。
- **未跑**：`scripts/run-gates.ps1`、`npm run smoke`、`plugin/scripts/smoke-all.mjs`（全量门禁归父代理）；
  node/浏览器侧一律没跑。
- **409 的 HTTP 级行为**：未测（LOW-7 登记在案；既有用例是函数级）。
- **schema 零变更**：没加列、没改 CHECK（因此也没有第 6 个 outcome）。
- 抽样声明：全量 `pytest` 是**真跑全量**（第二轮后 2357 passed），不是抽样；真机三层链/真网络**未测**。

## 8. 跨批次发现（只登记，不在本批顺手做）

1. **`doc_ccs_state.outcome` 的 CHECK 约束是"5 枚举"的硬闸**：任何新的查询结论都必须走
   "改 CHECK + 老库迁移"，否则真库写入时炸。⇒ 以后要给 CCS 结论加第 6 类，得单开一个
   schema 迁移批次（本批用 `parse_failed` + reason/attempts 区分，已写进代码注释）。
2. **`ccs_store.UNRESOLVED_OUTCOMES` 全仓只有定义处一个引用**（死常量）：与 LOW-4/LOW-5 同族，
   但不在本批任务书里 ⇒ 只登记。
3. **状态里 `page`/`pages` / `stop_reason` / `missing_split` / `undo_journal` 是新字段**，
   `plugin/client/api.ts` 的类型定义还没读它们 ⇒ B3b 要用得先补类型（本批不动 plugin）。
4. **F5（复核第二轮登记，批外，本批没动）**：真库 `doc_meta.ccs_code` **0/6417** 有值，
   而 **6087** 篇有 CCS 标签；`/api/v1/documents` 与详情按 `server.py:837-839` **下发这两列**
   ⇒ 界面/接口侧看到的分类号列是空的。它与 `ccs_store` 头部"标签的唯一所有者是
   `domain_tags`、**不写** `doc_meta.ccs_code`"的设计声明**冲突** ⇒ 该改的是**下发那一侧**
   （或明确弃用该列），**不属 B3a**。

## 9. 第二轮独立复核：F1–F4（改完再提交，2026-09-24）

复核判定第一轮的 **HIGH-1 与 MED-5 真通过**（并亲自跑了复现脚本 = PASS），另抓两条 MED 必改 +
两条 LOW 由我判断（我选**顺手修**）。**F5 在批外，只登记**（见 §8 第 4 条）。

### 9.1 F1（MED，必改 —— "界面会说假话"）

`_decide_stop_reason()` 以前把 `scope=='selected'` 判在 `truncated` **之前**，而函数自己的
docstring 写的优先级正好相反。路由**永远**把默认 `limit=50` 传给勾选批次
（`routes_kb_folders.py`）⇒ "勾 60 篇只跑 50 篇、剩 10 篇一行没动"时，状态却说 `selected_done`
「勾选的那几篇跑完了」。**改法**：`truncated` 判到前面（`ccs_backfill.py:436-441`），
`limit` 与 `selected_done` 各归各位。

⚠ 更糟的一半复核也点到了：`tests/test_ccs_chain.py` 的真值表**把错序冻成了规格**
（`truncated=True + scope=selected ⇒ SELECTED_DONE`），不改测试它就永远"绿"。已改：
真值表现在明确断言这一组合 = `limit`（`:1206-1211`），并新增端到端用例
`test_selected_batch_cut_by_limit_says_limit_not_selected_done`（`:1143`，3 篇勾选 + limit=2）。

**变异原始红**（把顺序改回错的，`scope` 判在前）：

```
$ python -m pytest tests/test_ccs_chain.py -q -k "selected_batch_cut or decide_stop_reason"
>       assert st["stop_reason"] == bf.STOP_LIMIT, st          # ← 不是 selected_done
E       AssertionError: {'running': False, 'total': 2, 'done': 2, 'found': 2, ...}
E       assert 'selected_done' == 'limit'
tests\test_ccs_chain.py:1177: AssertionError
>       assert bf._decide_stop_reason() == bf.STOP_LIMIT, \
E       AssertionError: 被 limit 截过的勾选批次说成了 selected_done（界面会说假话）
E       assert 'selected_done' == 'limit'
tests\test_ccs_chain.py:1210: AssertionError
FAILED ...test_selected_batch_cut_by_limit_says_limit_not_selected_done
FAILED ...test_decide_stop_reason_table
2 failed, 56 deselected, 5 warnings in 0.71s
```

还原后：`git status --short` 空 · `MUTATION-F1 残留行数 = 0`。

### 9.2 F2（MED，必改 —— "逐字回到改前"少了第三处）

这一批还会改 `doc_meta.updated_at`（`ccs_store.apply_ccs_tag` 的 UPDATE 带 `datetime('now')`），
而回退记录不记它、`revert` 也不恢复（复核现场：改前 `2001-01-01 00:00:00` → 补后 / 回退后
都是 `2026-09-23 17:45:50`）。**改法**：`write_undo_journal` 记 `updated_at` **原文**
（`ccs_undo.py:105-116`），`revert_ccs_backfill_journal` 一并写回（`:256-261`，进
`restored_docs[].restored`）；老格式记录缺这一项时用 `_UNSET` 哨兵**不碰那一列**。
复核那句提醒照办：**不拿"某次探针里它没变"当反证**（那是同秒巧合）⇒ 新用例把改前的
`updated_at` **钉到 2001 年**。

**判据**：`test_revert_also_restores_updated_at`（`:1226`）——先断言这一批**真的改过**它
（`!= before`），再断言回退后**逐字等于改前**，最后断言第二次回退幂等。

**变异原始红**（把回退 `updated_at` 那一步短路）：

```
$ python -m pytest tests/test_ccs_chain.py -q -k "revert_also_restores_updated_at"
        assert _raw_updated_at(db, "doc_ccs_ua1") != before, \
        assert res["restored"] == 1, res
>       assert "updated_at" in res["restored_docs"][0]["restored"], res
E       AssertionError: {'journal_path': '…\\ccs-undo-20260924-015227-p36784-2.json',
E        'doc_count': 1, 'restored': 1, 'skipped': 0, ...}
E       assert 'updated_at' in ['domain_tags', 'doc_ccs_state（改前没有这一行 ⇒ 删掉）']
tests\test_ccs_chain.py:1253: AssertionError
1 failed, 57 deselected, 5 warnings in 0.50s
```

还原后：`git status --short` 空 · `MUTATION-F2 残留行数 = 0` · `if not updated_same:` 回到 `:256`。

### 9.3 F3（LOW，顺手修）—— `db_path` 只喂给 plan 与备份，干活线程不认

**改法**：`_run(pages, pause_s, db_path)` 一路传到底（`get_db_connection(db_path)` +
`record_ccs_lookup(..., db_path=)` + `apply_ccs_tag(..., db_path=)` + 异常路径的台账写）；
再加 `_db_path()`（`ccs_backfill.py:117`）把 `str` 规整成 `Path`（以前会在 `sqlite_db` 的
`path.parent` 上 `AttributeError`），所有公开入口都过它。
**判据**：`test_db_path_is_honoured_by_the_worker_thread`（`:1262`）——开第二个库跑一批 ⇒
标签与台账落在**那个**库、**默认库一个字节没动**；`missing_ccs_count(db_path=str(...))` 也认。

### 9.4 F4（LOW，顺手修）—— 坏 `domain_tags` 会被"当空"从而冲掉别的标签

`_as_list` 对"非空且非 JSON 数组"归零 ⇒ 写 CCS 标签时把别的标签整片覆盖（复核探针 6：
`'消防、通用'` → `'["CCS:K41 变压器"]'`；真库当前 0 命中＝潜伏口）。**改法**：新增**写路径**严格版
`_as_list_for_write`（`ccs_store.py:75-105`）——非空却不是 JSON 数组 ⇒ 抛 `invalid_domain_tags`
**拒改**；**读路径** `_as_list` 保持宽松（界面照常显示）。整批跑时 `classify_backfill_exception`
为它单出一句"这一篇的 domain_tags 不是 JSON 数组……**拒绝改它**（怕把别的标签冲掉）"，
attempts 记 `domain_tags_unparsable`（**不是**网络问题、也不是代码缺陷）。
**判据**：`test_broken_domain_tags_is_refused_not_silently_wiped`（`:1295`）——直接调写路径抛错
且**原文一个字没变**；整批跑时这一篇落 `parse_failed` + 那句话，**旁边的正常篇照常补上**。
（顺带确认：`pipeline.run_full_ingest` 那条调用本来就在 `try/except` 里打日志
（`pipeline.py:2290-2299`）⇒ 更严格的写路径**不会**把入库搞失败。）

### 9.5 复核否掉的两处转述（照办：不必改）

- "exhausted/cancelled 造不出稳定现场"**不成立** —— 复核用真现场跑出来了。我原来的写法
  （真值表钉纯函数 + 端到端各有用例）**保留原样**，没有因为那句话删判据。
- 真库缺号是 **330** 篇（我正文里曾按"380 篇"转述业主原话）。本报告 §1/§7 用 330 记**复核核过的数**，
  380 只作为业主原话引用保留。
