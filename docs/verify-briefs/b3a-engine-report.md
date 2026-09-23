# 独立复核报告 —— KnowledgeStation「补全分类号」引擎半边（B3a）两笔提交

* 复核树（唯一）：`D:\AI\work space\zcode-verify-b3a`
* 冻结 tag：`verify-freeze-b3a-engine`；区间 `4ed4b0d..verify-freeze-b3a-engine` = **2 笔**（`git rev-list --count` = 2）
  * `0f05026` fix(补全分类号/B3a)：引擎 + 路由
  * `180397f` test(补全分类号/B3a)：18 条新用例
* 方向机械核对：`git merge-base --is-ancestor 4ed4b0d verify-freeze-b3a-engine` → **exit 0**（前提成立；不是"tag 打在祖先上"那一次）
* 真库 `%APPDATA%\KnowledgeStation\database\knowledge.db`（2,340,388,864 B）**全程 mode=ro 只读**；
  探针前后对 `knowledge.db` 与 `knowledge.db-wal` 各做一次 sha256：**两者都一字未变**（原始输出见 §A.3）

---

## 报告首：git 记录（一）

```
$ git -C "D:\AI\work space\zcode-verify-b3a" rev-parse HEAD
180397fe64058ae5c7a99a028408593a6ac1edae
$ git -C "D:\AI\work space\zcode-verify-b3a" status --short
(空)
```

基线复现（父代理实测 54 passed）：
```
$ Push-Location 'D:\AI\work space\zcode-verify-b3a'
$ & 'D:\AI\work space\zcode\.venv\Scripts\python.exe' -m pytest tests/test_ccs_chain.py -q --no-header -p no:cacheprovider
54 passed, 5 warnings in 2.77s        [exit=0]
```

---

## 结论总表

| # | 判定 | 分级 |
|---|---|---|
| 1 | "补前一定有备份" **本树内成立**（备份前零写库、中途炸也覆盖整批） | 通过 |
| 2 | 回退**不是**"逐字回到改前"——`doc_meta.updated_at` 被改且没进记录、没被恢复 | **MED（F2）** |
| 3 | HIGH-1 **已堵死**（标签口唯一、活路径都走它、真库 0 篇两条）；入库侧残留一个非原子窗口 | 通过 / 残余 LOW（F7） |
| 4 | `stop_reason` 在 **勾选篇数 > limit** 时说假话（"勾选的跑完了"而确有勾选篇一行没动） | **MED（F1）** |
| 5 | `missing_split` 五桶恒等式（真库 330==330）与失败篇归类 **真** | 通过 |
| 6 | `all=true` 分页/硬上限/不重复查/按停 **真**（含"只剩多少"现算） | 通过 |
| 7 | MED-5（锁）**有判据钉住**（变异必红）——父代理的担心不成立 | 通过 |
| 8 | 不加第 6 个 `outcome` 的理由 **成立**（真库 CHECK 只有 5 枚举 + NOT NULL） | 通过 |
| 9 | 新用例有牙（3 个变异各自红）；但一条真值表把 F1 的错序**冻成了规格** | **LOW（F6）** |
| 10 | 声明的"没做"**确实没做**（零界面文件、无 captcha 短路、无回退 HTTP 端点、无 HTTP 级 409 用例） | 通过 |
| 11 | `db_path` 只喂给计划/备份，干活线程不认 ⇒ "备份对象 ≠ 被写对象"的陷阱 | **LOW（F3）** |
| 12 | `_as_list` 对"非空且非 JSON 数组"的 `domain_tags` 归零 ⇒ 会把别的标签整片覆盖 | **LOW（F4）**（真库 0 命中） |
| 13 | 第三处 CCS 码 `doc_meta.ccs_code` 仍是空的（0/6417），补全从不写它 | **MED（F5）**，不在本 2 笔 diff 内 |

---

# 逐条结论（每条：结论 / 分级 / 文件:行 / 最小复现 / 原始输出）

## ① "补前一定有备份"是不是真的 —— **是**（探针1、探针3）

**读代码定序**：`start_ccs_backfill` 里 `_LOCK.acquire` → `plan_ccs_backfill`（只读）
→ `ccs_undo.write_undo_journal(...)`（`ccs_backfill.py:468-486`）→ 才 `threading.Thread(target=_run)`（:501）。
`write_undo_journal` 自己 `open(tmp)`+`flush`+`fsync`+`os.replace`，写不成抛 `ccs_undo_failed`（`ccs_undo.py:126-138`）。

**独立仪器（不是采信作者的用例）**：我把 `ccs_undo.write_undo_journal` 包一层，在**真函数被调用那一瞬间**
用一条独立连接读回整批的 `domain_tags`/台账：

```
【探针1】假设：write_undo_journal 被调用的那一刻，整批的 domain_tags/台账都还是改前的样子（＝备份前零写库）
  批内篇 = ['p1_a', 'p1_b']  写记录那一刻库里与改前逐字相同 = True
  记录文件在调用瞬间已存在（上一份）= False  写完存在 = True
  结果: PASS
```

**中途炸掉**：第 2 篇时让 `_update_counts` 抛 `RuntimeError`（循环体外的异常路径），
回退记录仍然覆盖**整批 3 篇**，且回退把已改的 2 篇逐字退回、第 3 篇记为"已经是改前的样子"：

```
【探针3】queued = 3  stop_reason = error  last_error = 这一批自己出错了（RuntimeError: boom-探针3…）
  记录里的篇 = ['p3_a', 'p3_b', 'p3_c']
  中途写进去的篇 = ['p3_a', 'p3_b']
  revert = {'doc_count': 3, 'restored': 2, 'skipped': 1}
  三篇都逐字回到改前 = {'p3_a': True, 'p3_b': True, 'p3_c': True}
  结果: PASS
```
（`all=true` 同样一份记录覆盖**到上限为止选中的全部页**，不是一页一份：探针9b `pages=2`、`doc_count=2`。）

**变异1（"把备份那步短路"）⇒ 用例必红**（原文）：

```
$ & python -m pytest tests/test_ccs_chain.py -q -p no:cacheprovider -k "journal"     # 变异：短路 write_undo_journal
FAILED tests/test_ccs_chain.py::test_undo_journal_is_written_before_the_first_write
FAILED tests/test_ccs_chain.py::test_undo_journal_honours_ks_backup_dir - Ass...
FAILED tests/test_ccs_chain.py::test_backfill_refuses_to_start_when_journal_write_fails
3 failed, 51 deselected, 5 warnings in 0.61s
>       assert all(s["journals"] for s in seen), \
E       AssertionError: 第一次查询发生时回退记录还不在盘上：[{'no': 'GB/T 90300-2020', 'journals': [], ...
tests\test_ccs_chain.py:915: AssertionError
```
还原：`git checkout -- src/core/knowledge/ccs_backfill.py` → `git status --short` 空。

⚠ **但"补前有备份"这句话的外延比它听上去小**：这份记录只覆盖 `doc_meta.domain_tags` + `doc_ccs_state`，
而这一批**还会改 `doc_meta.updated_at`**（见 F2）；并且只在 `db_path` 一致时才是"同一份库"（见 F3）。

## ② 回退是不是真能退干净 —— **两处逐字能退；第三处（`updated_at`）退不回去**（**MED / F2**）

**文件:行**
* 改的地方：`src/core/knowledge/ccs_store.py:155` —— `UPDATE doc_meta SET domain_tags=?, updated_at=datetime('now')`
* 记录里没有它：`src/core/knowledge/ccs_undo.py:105-113`（每条只记 `doc_id/standard_no/existed/domain_tags/ccs_state`）
* 回退也不恢复它：`src/core/knowledge/ccs_undo.py:233` —— `UPDATE doc_meta SET domain_tags=? WHERE doc_id=?`

**最小复现**：探针2（把一篇的 `updated_at` 先压到 `2001-01-01`，跑一批，再回退）：
```
【探针2】
  改前 : {'tags': '["消防"]', 'updated_at': '2001-01-01 00:00:00', 'state': None}
  补后 : {'tags': '["消防", "CCS:K41 变压器"]', 'updated_at': '2026-09-23 17:45:50', ...}
  回退后: {'tags': '["消防"]', 'updated_at': '2026-09-23 17:45:50', 'state': None}  revert = {'restored': 1, 'skipped': 0}
  回退记录里记了什么键 = ['ccs_state', 'doc_id', 'domain_tags', 'existed', 'standard_no']
  tags 逐字回到改前 = True
  updated_at 回到改前 = False （改前 '2001-01-01 00:00:00' → 回退后 '2026-09-23 17:45:50'）
  updated_at 在记录里出现 = False
  结果: PASS
```
**其余回退判据我都独立跑过、都真**（探针10，原始输出）：
```
补后 q1 tags = ["消防", "通用", "CCS:K41 变压器"]  q2 tags = ["CCS:K41 变压器"]
revert#1 = {'doc_count': 2, 'restored': 2, 'skipped': 0}
  q1 逐字回到改前(含台账整行) = True
  q2 逐字回到改前(台账行删掉) = True  q2 台账 = None
  不在批里的 q3 一行没动 = True
  别的标签还在/顺序 = ['消防', '通用']
revert#2 = {'restored': 0, 'skipped': 2}  理由 = {'已经是改前的样子（不重复动）': 2}
  幂等（第二次一个没动） = True
```
⇒ "改前没有台账行 ⇒ 删掉"、"改前有台账行 ⇒ 整行（含 `checked_at`/`applied_at`/`reason`/`attempts_json`）写回"、
幂等、**反向**（批外篇一行不动）——**都真**。

**影响面（只读核过，不给它加戏）**：`doc_meta.updated_at` 在本树里**没有任何查询读它**；
但 `folder_store.py:1458` 用 `PRAGMA table_info(doc_meta)` 把**整行**列进文件列表 SQL
（`:1470 f"SELECT {dcols}, …"`），所以它会随接口下发到界面。⇒ 回退之后"这一篇看起来刚更新过"。
**别拿探针10 的 `updated_at` 相同当反证**：那两篇的改前值与补全发生在**同一秒**，是巧合，探针2 才是判据。

**修法**：`write_undo_journal` 多记一个 `updated_at`，`revert` 非空时一并写回（3 行）。

## ③ HIGH-1 是否真的堵死 —— **是**（活路径全收口）；残留一个非原子窗口（LOW / F7）

**已堵死的证据**
1. 写 `CCS:` 标签的**活路径只有一条**：`ccs_store.apply_ccs_tag`（:132-157 收口成"一条"）。
   入库那条路也走它：`src/core/ingestion/pipeline.py:2294`。
   另一个写 `domain_tags` 的函数 `auto_tag.apply_tags_to_doc_meta`（`auto_tag.py:103` 整列覆盖）
   在本树里**没有调用方**（`grep apply_tags_to_doc_meta` 只命中定义与一条"已过"注释）。
2. 非 CCS 标签与顺序：探针10 实测 `['消防','通用']` → `['消防','通用','CCS:K41 变压器']`，回退后原样。
   收多余条目只删 `positions[1:]`（`ccs_store.py:149`），`first` 之前的索引不动。
3. 标签与台账**同一个事务**：`apply_ccs_tag` 整段在一个 `write_transaction` 里（:132-184）✓（读代码）。
4. 真库只读核：**0 篇**存在 ≥2 条 CCS 标签（`json_each`）；即 HIGH-1 是**预防性的**，真库里还没有脏数据可修。
5. 作者给的 `repro-ccs-high1.py`，**我自己在这棵冻结树上跑了一遍**：
```
tree         = D:\AI\work space\zcode-verify-b3a
domain_tags  = ['CCS:C65 劳动安全技术']
CCS 条目数    = 1   (期望：刷新后仍是 1)
读侧 ccs_tag  = CCS:C65 劳动安全技术
台账 ccs_code = C65
分类树 level4 = C65 劳动安全技术
台账 / 读侧 / 分类树 一致 = True   (期望 True)
VERDICT = PASS（只有一条、三处一致）   [exit=0]
```
**变异3（把实现改回"追加"）⇒ 该批两条用例必红**（原文）：
```
E       AssertionError: ['消防', 'CCS:K41 变压器', 'CCS:C65 劳动安全技术综合']
E         Left contains one more item: 'CCS:C65 劳动安全技术综合'
tests\test_ccs_chain.py:1284: AssertionError
E       AssertionError: ['消防', 'CCS:K41 变压器', 'CCS:C65 劳动安全技术综合']
tests\test_ccs_chain.py:1320: AssertionError
FAILED tests/test_ccs_chain.py::test_apply_ccs_tag_replaces_instead_of_appending
FAILED tests/test_ccs_chain.py::test_force_refresh_tag_and_tree_read_the_same_code
2 failed, 52 deselected, 5 warnings in 0.43s
```
（旧实现确实是"追加"：`git show 0f05026 -- ccs_store.py` 删掉的是 `already = text in tags` / `tags.append(text)`。）

**残余（LOW / F7，读代码，未跑）**：入库侧 `pipeline.py:2208-2216` 是
`tags = list(domain_tags or [])` → `if ccs_tag and ccs_tag not in tags: tags.append(ccs_tag)`
（**只按精确串去重**），整列随 `insert_document` 在**事务内**落库（:2241-2251）；
而收口的 `apply_ccs_tag` 在**事务外**、异常只 `logger.warning`（:2289-2299）。
⇒ 只要调用方自带一个**不同**的 CCS 标签（`/api/v1/laws/ingest` 的 `domain_tags` 是请求参数，
`routes_law.py:102/110`；CLI `pipeline.py:2418` 是 `--domain-tags` 逗号串），
库上会短暂出现两条 `CCS:`，随后的收口是"尽力而为"。`reingest` 那条路不传 `domain_tags`（`reingest.py:99-100`），走不到。
**我没跑通这条端到端**，只读代码；真库当前 0 篇两条。

## ④ `stop_reason` 说实话吗 —— **七值单值、失败篇不被算成补完**；但 **`selected × truncated` 组合说假话**（**MED / F1**）

**问题**：优先级文档与实现相反。
* 文档（`ccs_backfill.py:397-403`）："… > ``limit``（这一批到量）> ``selected_done``（勾选的跑完）> ``exhausted``"
* 实现（`ccs_backfill.py:408-411`）：`scope == "selected"` 的判断**在** `truncated` **之前**
⇒ 勾选 60 篇、`limit` 默认 50 时，只跑 50 篇，`stop_reason` 却是 `selected_done`
（"勾选的那几篇跑完了（全库还有别的没补）"），剩下 10 篇**一行没动、没有任何提示**。
HTTP 也到得了：`routes_kb_folders.py:594` 永远把 `limit`（默认 50）传给 `start_ccs_backfill`，
`doc_ids` 只校验"≤200"（`plan_ccs_backfill` :148-149），没有"勾选数 ≤ limit"的护栏。

**最小复现**（探针4：3 篇勾选、`limit=2`）：
```
【探针4】假设：doc_ids 给了 >limit 篇时，只跑 limit 篇，stop_reason 却说 selected_done
  queued = 2  plan.total = 3  plan.truncated = True
  实际被查的 = ['GB/T 91030-2020', 'GB/T 91031-2020']
  stop_reason = selected_done  label = 勾选的那几篇跑完了（全库还有别的没补）
  没被碰到的勾选篇 = ['p4_c']
  结果: PASS（说了'勾选的跑完了'但确有勾选篇没跑）
```

**用例把它冻成了规格（LOW / F6）**：`tests/test_ccs_chain.py:1168-1171`
—— `truncated` 在 :1168 已置 `True`，:1170 再置 `scope="selected"`，:1171 断言 `STOP_SELECTED_DONE`。
也就是说真值表**要求**这个错序。同一条用例的 docstring（:1160-1161）说
"`exhausted`/`hard_cap`/`cancelled` 在会话级临时库里造不出稳定现场"——**这个理由不成立**：
我不用注入计划就造出了 `cancelled`（探针5）与 `exhausted`（探针8）；`hard_cap` 本就是本批用例用 monkeypatch 造的。

**判定为真的部分**（探针9a，原始输出）：
```
  a(ConnectionError): outcome='network_failed' reason='补全时网络层出错（ConnectionError: 断网（探针造的））'
  b(RuntimeError)   : outcome='parse_failed' reason='补全时内部出错（代码缺陷，不是网络问题、也不是查无）：RuntimeError: boom…'
  b 的 attempts_json = [{"layer": "internal", "keyword_form": null, "result": "internal_error", ...}]
  stop_reason = selected_done （单值？） True
  failures = [('p9_a', 'network_failed'), ('p9_b', 'parse_failed')]
  tags 没被写 = True
  missing_split 增量: checked_failed +2, never_checked +-2, total 2→2
  五桶和 == total = True
```
⇒ 失败的篇落 `failures` + 台账，`missing_split` 把它们从"没查过"挪进"查过失败"，
**没有被算成"补完了"**；`total` 不变。
（`cancelled` 真实现场：探针5 —— 第 1 篇查完按停 ⇒ `stop_reason=cancelled`、`skipped=2`、`done=1`、没轮到的篇一行没动。）

## ⑤ `missing_split` 五桶 —— **恒等式真**（临时库 + 真库都核）

真库只读（§A.3 原文）：
```
{"total": 330, "never_checked": 330, "checked_not_found": 0, "checked_failed": 0, "not_applicable": 0, "found_but_untagged": 0}
五桶和 = 330  total = 330  差 = 0
```
这能成立的结构前提我也核了：真库 `doc_ccs_state.outcome` 是
`TEXT NOT NULL CHECK(outcome IN ('found','not_found','network_failed','parse_failed','not_applicable'))`
（§A.1 原始 CREATE SQL）⇒ 不存在"落在五桶之外"的行。**临时库侧的五桶逐个归类**也是真的（作者用例的增量断言成立，我复跑到 54 passed）。

## ⑥ `all=true` 那条路 —— **通过**

* **分页真按 `MAX_BACKFILL_DOCS`**：`_paginate` 省参时**现读**模块常量（`ccs_backfill.py:264`），
  探针9b 把 `MAX_BACKFILL_DOCS=1`、3 篇候选 ⇒ `pages=2`（作者用例另一处 `pages==2` 亦然）。
* **硬上限如实、不说补完了**（探针9b 原文）：
```
  queued = 2  pages = 2  hard_capped = True
  plan.total = 5  回退记录里的篇数 = 2
  stop_reason = hard_cap  label = 到了硬上限就停（还剩没补的，不是补完了）
  status.missing = 3 （还剩多少，现算）
  没被选中的篇一行没动 = True
```
* **同一篇不被查两次**：候选名单只 `plan` 一次（`start_ccs_backfill:471-478`），页只是切片；
  作者用例用 spy 断言 `len(set(seen))==2`，我也复跑通过（54 passed）。
* **中途按停生效**：探针5。
* **到上限后没选中的篇一行没动**：探针9b（`plan.total=5` > `queued=2`，剩下 3 篇 `missing` 未降）
  + 作者用例的 `_tags_of(...) == []` / `missing_ccs_count() == before-2` 断言（我复跑通过）。
* ⚠ 口径提醒（不是缺陷）：`all` 模式下回退记录覆盖的是**到上限为止选中的那些**，
  不是"全部 5 篇候选"——这与 `write_undo_journal` docstring（"分页后一共要跑的那么多篇"）一致。

## ⑦ MED-5（锁）—— **有用例钉住，变异必红**（父代理的担心不成立）

```
$ & python -m pytest tests/test_ccs_chain.py -q -p no:cacheprovider -k "wedge"   # 变异：把 finally 整块换成 pass
FAILED tests/test_ccs_chain.py::test_run_loop_error_does_not_wedge_running_and_lock
tests\test_ccs_chain.py:1392: 
E       AssertionError: 条件在 5.0s 内没成真（用例不该挂在这里）
1 failed, 53 deselected, 5 warnings in 5.59s
```
（5.59s = `_wait_flag` 超时；即"`running` 永远是 True"被抓到。还原后 `git status --short` 空。）

## ⑧ 不加第 6 个 `outcome` 值的理由 —— **成立**（真库只读核，原文见 §A.1）

* `CREATE TABLE doc_ccs_state (… outcome TEXT NOT NULL CHECK(outcome IN ('found','not_found','network_failed','parse_failed','not_applicable')) …)`
  ⇒ **确实只有 5 个值**，且 `NOT NULL`（没有"第六种"，也没有 NULL 的缝）。
* 真库 `doc_ccs_state` 实际行数 50，**全部** `outcome='found'`（没有 NULL、没有越界值）。
* "代码缺陷落 `parse_failed` 但真话写进 reason/attempts"：探针9a 逐字证实
  （reason 里有"**内部出错（代码缺陷，不是网络问题、也不是查无）**"，
  attempts 里 `layer=internal` / `result=internal_error`）⇒ **没有伪装成"页面结构变了"**。
* ⚠ 我**没核**界面把 `parse_failed` 说成什么话（B3b 未做）——如果界面那侧把它译成"页面读不出来"，仍会盖住内部错误。

## ⑨ 新用例有没有牙 —— **有**（3 个变异各自红）；无恒真断言，但有一条把缺陷冻成规格

* 变异1（短路补前备份）⇒ 3 条红；变异2（拆掉 `finally`）⇒ 1 条红；变异3（标签改回追加）⇒ 2 条红。原始输出见 ①②③⑦。
* 逐条扫断言：**没有** `pytest.skip` / `xfail` / `assert True`（grep 空）；54 passed / **0 skipped**。
* 偏软的界（不是恒真）：`test_all_mode_pages_serially_and_stops_at_hard_cap` 的
  `assert len([no for no in mine if no in seen]) <= 2` 是个上界而非等号——不过它前面已有
  `len(seen)==2 and len(set(seen))==2` 与 `missing_ccs_count()==before-2`，实质仍被钉住。
* **真缺陷**：`test_decide_stop_reason_truth_table:1168-1171` 把 F1 的错序断言成期望值（见 ④/F6）。

## ⑩ 它自己声明的"没做" —— **形式上都确实没做**

机械核对：
```
$ git diff --name-only 4ed4b0d verify-freeze-b3a-engine
src/core/api/routes_kb_folders.py
src/core/knowledge/ccs_backfill.py
src/core/knowledge/ccs_store.py
src/core/knowledge/ccs_undo.py
tests/test_ccs_chain.py
```
* **界面半边（B3b）**：上面 5 个文件里零界面/客户端文件 ⇒ 真没做。
* **MED-3（captcha/限流短路）**：`grep captcha src/core/knowledge/ccs_backfill.py` → **空**
  （`ccs_fetcher` 只把 captcha 记进 attempts，批次不会因此中止）⇒ 真没做。
* **LOW-7（409 的 HTTP 级用例）**：文件里 409 只出现在注释/引擎级用例
  （`test_ccs_chain.py:695-709` 是 `pytest.raises(RuntimeError, match="ccs_backfill_busy")`），
  没有 HTTP 状态码级用例 ⇒ 真没做。
* **回退函数只在引擎侧**：`routes_kb_folders.py` 里没有 undo/revert 端点
  （只有 `ccs_undo_failed`→500 的映射与 `undo_journal` 路径下发）⇒ 真没做。
* ⚠ **LOW-6 与 MED-3 的"条目原文"我在冻结树 docs 里没找到出处**（只有别轮次的同名编号），
  所以只能核"没做"这一形式，**条目内容未核**。

---

# 附：发现的三个新缺陷（文件:行 + 最小复现）

## F1（MED）勾选篇数 > limit 时 `stop_reason` 说"勾选的跑完了"
* `src/core/knowledge/ccs_backfill.py:408-411`（顺序）vs `:397-403`（文档声明的顺序相反）
* `src/core/api/routes_kb_folders.py:594,603-604`（路由永远把 `limit` 传下去，没有"勾选数 ≤ limit"的护栏）
* `tests/test_ccs_chain.py:1168-1171`（真值表把错序冻成规格）
* 最小复现：探针4 原文（见 ④）。修法：把 `truncated` 的判断挪到 `scope=="selected"` **之前**（一行），
  并让真值表同时置 `truncated=True` + `scope="selected"` 时断言 `limit`。

## F2（MED）`doc_meta.updated_at` 被改、没进回退记录、回退不恢复
* 写：`src/core/knowledge/ccs_store.py:155`；记：（缺）`src/core/knowledge/ccs_undo.py:105-113`；恢复：（缺）`:233`
* 最小复现：探针2 原文（见 ②）。

## F3（LOW）`db_path` 只喂给计划与备份，干活线程写到默认库
* `src/core/knowledge/ccs_backfill.py:471-472`（plan 收 `db_path`）、`:483-485`（备份收 `db_path`），
  但 `_run` 签名 `_run(pages, pause_s)` **没有** `db_path`（:284），
  线程内 `get_db_connection()`（:315）、`apply_ccs_tag`（:350）、`record_ccs_lookup`（:356/368）**全都不传**
* 最小复现（探针7-重做，Path 传参）：
```
【探针7-重做】
  默认库 = ('["CCS:K41 变压器"]', ('found', 'K41'))
  传进去的库 = ('[]', None)
  回退记录记的 domain_tags = []  ccs_state = None
  写落在默认库 = True  写落在传进去的库 = False
  结果: PASS（记录来自 A，写落在 B ⇒ 备份对象≠被写对象）
```
  生产路由不传 `db_path`（`routes_kb_folders.py:603-604`）⇒ 今天不可达；
  但"按签名用就会得到一份**描述了另一个库**的回退记录"。
  另：`db_path` 传 `str` 会在 `plan` 第一步炸
  （`sqlite_db.py:64 path.parent`，签名是 `Path | None`），本批把 `db_path: Any` 开到了 plan/undo 两个新口子上。

## F4（LOW）`_as_list` 把"非空且非 JSON 数组"归零 ⇒ 覆盖整列
* `src/core/knowledge/ccs_store.py:62-72`（`except (TypeError, ValueError): return []`；
  JSON 非数组也 `return []`）+ `:141-142`（`tags = tags + [text]`）
* 最小复现（探针6）：
```
【探针6】改前 = 消防、通用  改后 = ["CCS:K41 变压器"]  applied = True
  别的标签还在吗 = False
  结果: PASS（原内容整片被覆盖）
```
* 真库只读核：`domain_tags` 非法 JSON **0 篇**、合法但非数组 **0 篇**（标准篇同样 0）
  ⇒ **今天 0 命中**，是潜伏口；一旦哪天有手工/迁移写入这种形状，第一次补全就把它抹掉。
  与 `ccs_store` 自己第 2 条纪律"绝不改写别的标签"直接冲突。

## F5（MED，**不在本 2 笔 diff 内**）第三处 CCS 码 `doc_meta.ccs_code/ccs_name` 仍是空的
* 补全只写 `domain_tags` 一条标签 + `doc_ccs_state`（`ccs_store.py:9-12` 明写"不写 `doc_meta.ccs_code`"），
  而 `/api/v1/documents` 与文档详情**按 `doc_meta.ccs_code/ccs_name` 下发**（`server.py:836-840`、`:1343-1344`）。
* 真库只读核：`doc_meta.ccs_code` 非空 = **0 / 6417**；有 CCS 标签的 standard = **6087 篇**
  ⇒ "补全分类号"之后，走 `ccs_code` 这个口子的地方依旧看不到分类号（台账/分类树/这一列三处里，第三处还是空）。
* 不是这 2 笔引入的、本批也声明了 schema 零变更；但它是"HIGH-1 已堵死"这句话的**边界**，值得登记。

---

# 我明确没能验证的

1. **真机 330 篇回填**：没跑（也不该跑）。所有引擎行为结论都来自会话级临时库；真库只做了只读统计与只读探针。
2. **改前树（`0f05026^`）上 `repro-ccs-high1.py` 真的 FAIL**：我**没有**独立跑改前那一半
   （纪律只许在本树内动，未另建 worktree）；我把它换成"读 diff 原文"来核
   （旧实现 `already = text in tags` / `tags.append(text)` 确实是追加）。
3. **F5 的界面后果**：我只核到接口会下发 `ccs_code` 且真库该列全空；
   界面是否真的显示它、显示成什么，未验（B3b 未做）。
4. **F7 入库侧两条 CCS 的非原子窗口**：读代码得出，**未跑端到端**。
5. **`updated_at` 的下游消费者**：我核到本树没有任何查询读它、但 `folder_store` 会把它随整行下发给界面；
   界面/别的系统拿它做什么，未验。
6. **MED-3 / LOW-6 / LOW-7 的条目原文**：冻结树 docs 里没找到这几条编号的出处（只有别轮同名编号），
   只核了"没做"这一形式。
7. **`repro-ccs-high1.py` 覆盖不到的情形**（父代理点名要说明）：
   它只覆盖"一篇已有旧 CCS 标签 → `force=True` 刷新成新号"这一条路（单进程、单事务、无并发、无异常）。
   它**覆盖不到**：入库侧 `pipeline.py:2215` 的整列写入窗口（F7）、`apply_ccs_tag` 抛异常后
   标签与台账会不会不一致、`_as_list` 的非法 JSON 分支（F4）、以及回退路径本身。

---

# 父代理 / 提交说明**说错了**的地方

1. **提交说明**："补前精确回退记录（只记这一批会改的那篇的旧 `domain_tags` + `doc_ccs_state` 整行）"
   —— 漏了**这一批还会改 `doc_meta.updated_at`**（`ccs_store.py:155`）。
   ⇒ "逐字恢复到改前"这句话有 **3 处改动、只记了 2 处**（F2）。**这是本条转述与代码事实的直接冲突。**
2. **提交说明 + 父代理转述**："七值真值表（含会话级库里**造不出稳定现场**的 exhausted / hard_cap / cancelled）"
   —— **理由不成立**：`cancelled` 与 `exhausted` 我用**不经注入**的真现场都跑出来了
   （探针5、探针8：`all_docs=True` 且候选数 < 硬上限 ⇒ `stop_reason=exhausted`）；
   `hard_cap` 本就是本批用例用 monkeypatch 造的。
   更值得说的是：这张真值表**把 F1 的错序断言成了期望值**（`test_ccs_chain.py:1168-1171`）。
3. **父代理转述**："真库 380 篇缺号" —— 真库**现算 330**（提交说明里写的也是 330；我实测 `missing_ccs_count = 330`）。
4. **父代理转述**："现成工具：改前树 = FAIL（两条标签 + 台账与分类树不一致）"
   —— 改前那一半我**未独立跑**（见"没验证的"第 2 条），冻结树这一半我跑出 **PASS**。
   所以这句里能站住的只有后者。
5. **父代理的担心**（第 6 条）："把 `try/finally` 变异掉 ⇒ 有没有任何用例会红？若没有 ⇒ 报 MED/HIGH"
   —— **会红**（`test_run_loop_error_does_not_wedge_running_and_lock`，5.59s 超时红，原始输出见 ⑦）。
   这条修复**已被判据钉住**，不必再报。
6. **查证后不成立的一条（我不打）**：提交说明"删掉赋值后无引用的 `get_ccs_state`（LOW-4）"
   容易读成"删了这个函数"，实际删的是 `ccs_backfill._run` 里那行未使用的赋值
   （`git show 0f05026 -- ccs_backfill.py` 里 `- state = ccs_store.get_ccs_state(doc_id)`），
   函数本体仍在 `ccs_store.py:189` 且被新用例使用。**说法与事实一致，只是措辞易误读。**

---

## 报告尾：git 记录（二）

```
$ git -C "D:\AI\work space\zcode-verify-b3a" rev-parse HEAD
180397fe64058ae5c7a99a028408593a6ac1edae
$ git -C "D:\AI\work space\zcode-verify-b3a" status --short
(空)
```
（三处变异全部 `git checkout --` 还原，逐次以 `git status --short` 判空；报告与本报告的探针脚本均在 `%TEMP%\b3a-verify-14732\`，
不在本树内 —— 本树除本报告外零改动。）

---

# §A 真库只读探针原始输出（节选；完整在 `%TEMP%\b3a-verify-14732\real_db_out.txt`）

## A.1 `doc_ccs_state` 的建表 SQL（CHECK 只有 5 个值）
```
col 1 outcome TEXT notnull=1 dflt=None
CREATE TABLE doc_ccs_state (
    doc_id TEXT PRIMARY KEY,
    outcome TEXT NOT NULL
        CHECK(outcome IN ('found','not_found','network_failed','parse_failed',
                          'not_applicable')),
    source TEXT, keyword_form TEXT, matched_no TEXT, ccs_code TEXT, ccs_name TEXT,
    reason TEXT, attempts_json TEXT,
    checked_at TEXT DEFAULT (datetime('now')),
    applied_at TEXT
)
```
列集合/顺序与 `ccs_undo._STATE_COLUMNS` **完全一致**（`列集合一致 = True  顺序一致 = True`）。

## A.2 真库体检数字
```
outcome='found' n=50      doc_ccs_state 总行数 = 50
有 >=2 条 CCS 标签的篇数 = 0
不是合法 JSON = 0      是合法 JSON 但不是数组 = 0
标准篇里非数组 = 0      标准篇里非法 JSON = 0
outcome='found' 但 ccs_code 为空 = 0
missing_ccs_count = 330     domain_tags LIKE '%"CCS:%' 的 standard 篇 = 6087
doc_meta.ccs_code 非空(全部) = 0          doc_meta.ccs_code 非空(standard) = 0
doc_meta 总数 = 6417        standard 总数 = 6417
doc_meta 列 = ['doc_id','standard_no',…,'domain_tags',…,'updated_at','ccs_code','ccs_name',…]
```

## A.3 只读证明（探针前后 sha256 与长度）
```
before db sha256 = fe9b8a17483851877b28d480a125fa34c9fc47c39deb491de8446854315f22db size = 2340388864
before wal sha256 = 58351f5fc40de6ec01f9e79785a618b418d68d8db69dac2c34a8966591f40244
after  db sha256 = fe9b8a17483851877b28d480a125fa34c9fc47c39deb491de8446854315f22db size = 2340388864
after  wal sha256 = 58351f5fc40de6ec01f9e79785a618b418d68d8db69dac2c34a8966591f40244
db 未变 = True  wal 未变 = True
```
（连接串 `sqlite3.connect("file:<path>?mode=ro", uri=True)`；全部语句都是 `SELECT`/`PRAGMA`。）
