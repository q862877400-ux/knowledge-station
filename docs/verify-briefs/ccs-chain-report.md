# 独立复核报告 —— 「分类号（CCS）三层查询链 + 补全自愈」

复核树（唯一读写面）：`D:\AI\work space\zcode-verify-ccs`（detached，标签 `verify-freeze-ccs-chain`）
冻结区间：`9653fe6~1..verify-freeze-ccs-chain`
主仓 `D:\AI\work space\zcode` 只用于拿 Python 解释器，**未读、未写、未做任何 git 操作**。

---

## 0. 冻结状态（首尾各一次）

### 开工快照
```
$ git -C "D:\AI\work space\zcode-verify-ccs" rev-parse HEAD
9460344281bd347e7afedbb7f061a7b58478ad5e

$ git -C "D:\AI\work space\zcode-verify-ccs" status --short
（空）

$ git -C "D:\AI\work space\zcode-verify-ccs" rev-list --count 9653fe6~1..verify-freeze-ccs-chain
5
```
⇒ 提交条数 5，与任务书一致（自己数的，未凭印象）。

### 收工快照
见本文件末尾 §7。

---

## 1. 基线（定向 pytest，未跑 `run-gates.ps1`）

```
$ Push-Location 'D:\AI\work space\zcode-verify-ccs'
$ & 'D:\AI\work space\zcode\.venv\Scripts\python.exe' -m pytest tests/test_ccs_chain.py -q --no-header -p no:cacheprovider
36 passed, 5 warnings in 2.17s
```
与父代理实测一致（36 passed / 2.39s）。**无 skipped** ⇒ 后文"用例真的在跑"这一条成立。

---

## 2. 结论清单

| # | 级别 | 标题 |
|---|---|---|
| HIGH-1 | **HIGH** | `force=True` 刷新会给同一篇追加**第二条** `CCS:` 标签；读侧仍取第一条 ⇒ 刷新静默无效、台账与分类树打架 |
| MED-1 | MED | 补全线程的 `except Exception` 把**任何非网络故障**记成 `network_failed` 并落台账 |
| MED-2 | MED | 该异常路径**零测试覆盖**：把它的台账写入删掉后 `36 passed`（变异存活） |
| MED-3 | MED | captcha/限流被记成 `parse_failed`，界面原因写"页面结构可能变了"；且 captcha 不短路，单篇查询打 8 次 |
| MED-4 | MED | "补全再跑一遍就是 0 篇"对**失败的篇**不成立：每次按都重查重写 |
| MED-5 | MED | `_run` 无 `try/finally`：循环体外异常 ⇒ `running` 与模块锁永久卡死 |
| MED-6 | MED | `9460344` 的核心数字与它自己的样本构成**算术不相容**，且取证文件不在冻结树里 |
| LOW-1 | LOW | 界面「没有建议」第 1 条分支自造原因，同段注释却声明"不自己推断"；该分支无任何断言 |
| LOW-2 | LOW | 按钮从不告诉用户"一次最多补 50 篇"（后端下发了 `max_batch`/`default_batch`，页面不用） |
| LOW-3 | LOW | 按钮 tooltip 把链说成三层，后端 `SOURCES` 是四层（含 `seed_file`） |
| LOW-4 | LOW | `ccs_backfill.py:151` `state = …` 赋值后从未使用（每篇一次多余查询） |
| LOW-5 | LOW | `_PROGRESS["last_error"]` 初始化后无任何写入点（死字段） |
| LOW-6 | LOW | `use_network=False` 未命中返回 `not_found`，reason 却说"答话的站点里都没有"（一个站点都没问） |
| LOW-7 | LOW | 409 `ccs_backfill_busy` 的 HTTP 映射只静态读过，未做 HTTP 级验证 |

---

## 3. 逐条证据

### HIGH-1 `force=True` 换来第二条 CCS 标签，读侧仍读旧的那条

**位置**
- `src/core/knowledge/ccs_store.py:113-125` —— `apply_ccs_tag` 只做 `tags.append(text)`，**没有任何"替换已有 CCS 条目"的逻辑**
- `src/core/knowledge/ccs_backfill.py:157` —— `if ccs_store.ccs_tag_of(row["domain_tags"]) and not it.get("force")` ⇒ `force=True` 正是**绕过**这道护栏的路径
- `src/core/knowledge/ccs_store.py:46-52` `ccs_tag_of` / `src/core/knowledge/doc_catalog.py:286` —— 读侧一律 `next(第一个以 CCS: 开头的条目)`
- 可达路径（本批交付的公开端点）：`src/core/api/routes_kb_folders.py:579` `force = bool(body.get("force"))`；`GET /api/v1/kb/ccs/plan?force=true` 同理
- `force` 的用途按 `ccs_backfill.py:79-80` 的原文是"**口径变化后刷新用**" —— 而"码变了"正是这一用途唯一有意义的场景

**最小复现**
```python
# 存成 repro_high1.py 后：& 'D:\AI\work space\zcode\.venv\Scripts\python.exe' repro_high1.py
import os, sys, json, tempfile, time
sys.path.insert(0, r'D:\AI\work space\zcode-verify-ccs')
os.environ['KS_DATA_DIR'] = tempfile.mkdtemp(prefix='ks_ccs_verify_')
from src.core import config; config.reset_settings()
from src.core.storage.sqlite_db import write_transaction, get_db_connection, init_schema
init_schema()
from src.core.storage import clause_repo
from src.core.knowledge import ccs_backfill as bf, ccs_store
import src.core.knowledge.ccs_fetcher as cfmod
with write_transaction() as conn:
    clause_repo.insert_document(conn, {'doc_id':'d1','standard_no':'GB/T 91002-2020',
        'standard_name':'x','short_code':'GB/T 91002-2020','current_revision_id':'r1',
        'doc_type':'standard','legal_hierarchy':'GB','standard_type':'mandatory',
        'domain_tags':['CCS:K41 变压器'],'file_path':'C:/tmp/d1.pdf','file_hash':'h1'})
cfmod.resolve_ccs = lambda no, name='', **kw: {'outcome':'found','code':'C65',
    'sub':'劳动安全技术','source':'official_api','keyword_form':'full',
    'matched_no':no,'attempts':[]}
bf.start_ccs_backfill(doc_ids=['d1'], force=True, pause_s=0.0)
while bf.ccs_backfill_status()['running']: time.sleep(0.05)
raw = get_db_connection().execute('SELECT domain_tags FROM doc_meta WHERE doc_id=?',('d1',)).fetchone()[0]
print('domain_tags =', json.loads(raw))
print('ccs_tag_of  =', ccs_store.ccs_tag_of(raw))
print('ledger code =', ccs_store.get_ccs_state('d1')['ccs_code'])
from src.core.knowledge.doc_catalog import classify_document
print('catalog lv4 =', classify_document({'standard_no':'GB/T 91002-2020','standard_name':'x',
    'doc_type':'standard','legal_hierarchy':'GB','domain_tags':json.loads(raw)})['level4'])
```

**原始输出**
```
=== B) already-tagged doc + force=True with a DIFFERENT code ===
  domain_tags = ['CCS:K41 变压器', 'CCS:C65 劳动安全技术']
  ccs_tag_of() read side (first) = CCS:K41 变压器
  ledger ccs_code = C65
  catalog level2 / level4 = K 电工 / K41 变压器
```

**后果**：`force` 刷新**静默不生效**（分类树仍读旧码 K41），而台账说新码 C65 —— 一个事实两个家，正是
`schema.sql:730-733` 声明要避免的"同一件事有两个家迟早打架"。同时该篇永久带两条互相矛盾的 CCS 标签。
真库实测当前 `docs with >1 CCS tag = 0`（我读的那一刻），所以这是**由 force 路径引入**的，不是既有数据。

**诚实边界**：界面按钮调 `startKbCcsBackfill(port, token, {})`（`KsKnowledgePage.tsx`），**不传 force** ⇒
业主点按钮碰不到；可达面是 `POST /kb/ccs/backfill {"force":true}` 与 `GET /kb/ccs/plan?force=true` 这两个本批新交付的端点。

---

### MED-1 非网络故障被记成 `network_failed`

**位置**：`src/core/knowledge/ccs_backfill.py:191-199`
```python
        except Exception as exc:                             # noqa: BLE001
            logger.warning("补分类号失败 doc=%s", doc_id, exc_info=True)
            rec.update({"outcome": "network_failed",
                        "reason": f"补全中断（{type(exc).__name__}: {exc}）"})
```
`OUTCOME_LABELS[network_failed]`（`ccs_fetcher.py:89`）= "查询失败（网络不通/被拦，一个站点都没答上）"。
一个库错/代码错被记成"站点一个都没答上"，并进 `failures` 与计数器 —— 与模块头
（`ccs_fetcher.py:31-41`）立的"不许把 A 说成 B"是同一族毛病。

**最小复现**：把 HIGH-1 的脚本里 `cfmod.resolve_ccs` 换成
```python
def boom(no, name='', **kw): raise RuntimeError('模拟：非网络故障（例如库写坏）')
cfmod.resolve_ccs = boom
```
（`doc_ids=['d1']`、不带 force），再打印 `ccs_store.get_ccs_state('d1')`。

**原始输出**
```
=== C) resolve_ccs raises (non-network) -> ledger outcome ? ===
  ledger outcome = network_failed
  ledger reason  = 补全中断（RuntimeError: simulated non-network fault）
  failures[0].outcome = network_failed
  progress counters = {'found': 0, 'not_found': 0, 'network_failed': 1, 'parse_failed': 0, 'not_applicable': 0}
```

---

### MED-2 异常路径零测试覆盖（变异存活）

**变异**：把 `ccs_backfill.py` 异常处理里的台账写入
```python
                ccs_store.record_ccs_lookup(doc_id, {
                    "outcome": "network_failed", "reason": rec["reason"]})
```
改成 `pass  # MUTATION-M3-swallow`（即让"崩掉的查询在台账里**一个字都不留**"—— 正是本批要杀的"静默降级"）。

**命令**（绝对路径；改前 `git status --short` 为空）
```
$ & 'D:\AI\work space\zcode\.venv\Scripts\python.exe' -m pytest tests/test_ccs_chain.py -q --no-header -p no:cacheprovider
```

**原始输出**
```
=== M3: 异常路径的台账写入改成 pass（静默吞掉）===
M3 applied
--- pytest after M3 ---
36 passed, 5 warnings in 1.74s
M3 restored; status:            （git status --short 为空 ⇒ 已还原）
```
⇒ **变异存活**。全套用例里**没有任何一条**让 `resolve_ccs` 抛异常（`test_backfill_all_layers_dead_records_failure_in_db`
走的是"`resolve_ccs` **返回** network_failed"，不是异常），所以这条分支的"失败留痕"不受任何断言保护。
按 AGENTS.md「棘轮看不见"把断言换成恒真"」，这一类只能靠逐条看断言发现 —— 这里确实是空的。

**对照组（证明判据在别处是硬的）**
```
=== M1: 删掉 _run 里未命中的 record_ccs_lookup ===            → 1 failed, 35 passed
   FAILED tests/test_ccs_chain.py::test_backfill_all_layers_dead_records_failure_in_db
=== M2: _lookup_dict 的 source 写死 official_api ===          → 4 failed, 32 passed
   FAILED ...::test_official_empty_falls_back_to_web_scrape
   FAILED ...::test_local_table_hit_needs_no_network
   FAILED ...::test_seed_file_hit_needs_no_network
   FAILED ...::test_use_network_false_is_local_only
```
（M1/M2 变异后均已 `git checkout -- <绝对路径>` 还原，`git status --short` 为空。）

---

### MED-3 captcha/限流 ⇒ `parse_failed` + 界面原因说成"页面结构变了"；且不短路（单篇 8 次请求）

**位置**
- `src/core/knowledge/ccs_fetcher.py:456-460`（官方层）与 `:586-590`（网页层）：`looks_like_captcha(body)` ⇒ 记一条 `"result": "captcha"` 后 **`continue`**（只跳过当前**关键词形式**，不跳出本层，更不跳出整条链）
- `src/core/knowledge/ccs_fetcher.py:137-158` `_combine_verdict`：captcha 已置 `saw_response=True` ⇒ 落到第 3 条 ⇒ `parse_failed`
- `src/core/knowledge/ccs_fetcher.py:758-763` `_reason_text`：没有 `no_ccs_field` 时统一返回"解析失败：站点答了，但读不出条目（**页面结构可能变了**）"
- 界面拿这句当"为什么没有建议"显示：`routes_kb_folders.py` 的 `ccs_reason` → `KsKnowledgePage.tsx:1972`

**最小复现**
```python
import sys; sys.path.insert(0, r'D:\AI\work space\zcode-verify-ccs')
from src.core.knowledge import ccs_fetcher as cf
class Captcha:
    def __init__(self): self.calls=[]
    def fetch(self, url, **kw):
        self.calls.append(url); return 200, '<html><body>请输入验证码 checkcode</body></html>'
tr = Captcha(); got = cf.resolve_ccs('GB/T 1094.3-2017', transport=tr)
print(got['outcome']); print(got['reason']); print(len(tr.calls))
print(sorted({a['result'] for a in got['attempts']}))
```

**原始输出**
```
=== D) captcha / rate-limit wall on BOTH layers ===
  outcome      = parse_failed
  reason       = 解析失败：站点答了，但读不出条目（页面结构可能变了）
  outcome label= 读不出来（站点答了，但没有分类号或读不出条目）
  attempt results = ['captcha', 'no_match', 'unavailable']
  n requests   = 8
```
**判读**：**没有**被记成"该标准没有分类号"（`not_found`）—— 点 2 最担心的那种错记**没有发生**（这一条是正面的）。
但"被限流/要过人机验证"被记成"读不出来 + 页面结构可能变了"，且 `_reason_text` 里那段把 captcha 归入
`network_failed` 的分支（`:754-755`）**永远走不到**（captcha 已把 `saw_response` 置真），所以"站点要求人机验证"
这条**只存在于 attempts_json，进不了界面那句人话**。
附带：8 次请求 = 4 关键词形式 × 2 层 —— 撞了 captcha 墙还把两个站点各打 4 次，与
`ccs_backfill.py:20-21`"几百篇连打就是攻击"的自律口径不一致。

---

### MED-4 "再跑一遍就是 0 篇"对失败的篇不成立

**位置**：`src/core/knowledge/ccs_backfill.py:24-26`（原文："候选由 … 算出来（不是记一份名单），**所以补全再跑一遍就是 0 篇**"）
与 `:70-71` `_MISSING_CCS_SQL` —— 候选判据是"**没有 CCS 标签**"，而失败（`not_found`/`network_failed`/…）
**不写标签** ⇒ 这些篇永远留在候选里。

**最小复现**：HIGH-1 脚本里 `resolve_ccs` 返回 `{'outcome':'not_found',...}`，连跑两次并打印第二次的 `queued`。

**原始输出**
```
=== A) failed doc: second press queued = 0 or 1 ? ===
  first  queued = 1   (ccs_backfill.py:24-26 says: second run = 0 docs)
  SECOND queued = 1
  checked_at 1st = 2026-09-23 17:27:15  2nd = 2026-09-23 17:27:16
  results rows after 2nd run = 1
```
**后果**：每次按"补全分类号"都会把**同一批失败的篇**重查一遍、重写台账（`checked_at` 会变）。
既有用例 `test_backfill_rerun_is_noop` 只覆盖**成功**路径，所以这句话没被测到。
不是理论问题：我读真库那一刻 `doc_type='standard'` 6417 篇、带 CCS 标签 6087 篇 ⇒ **330 篇缺**，
其中失败的篇按现判据会一直被反复重查。批量之间也**没有任何**跨批限速（只有单批内 `DOC_PAUSE_S`）。

**限速本身是好的（正面证据）**
```
=== J) 限速 ===
  CssnAdapter.PAUSE_S = 1.0
  _should_pace(real curl_cffi, None) = 1.0
  _should_pace(fake, None)            = 0.0
  _should_pace(fake, 0.25)            = 0.25
=== K) 每篇之间真的等 DOC_PAUSE_S ? （pause_s=None，3 篇，注入假链）===
  3 篇耗时 = 2.02 s  (DOC_PAUSE_S=1.0 ⇒ 两段间隔期望 ≈2.0s)
```

---

### MED-5 `_run` 无 `try/finally` ⇒ `running` 与锁可永久卡死

**位置**：`src/core/knowledge/ccs_backfill.py:137-211` —— 整个 `for` 循环**没有**外层 `try/finally`；
`_PROGRESS["running"] = False`（`:209`）与 `_release()`（`:211`）都在循环**之后**。
每篇的 `try`（`:149`）只保护单品内部；循环体里 `it["doc_id"]`、`_update_counts(rec)`、`time.sleep`
这些在 `try` **之外**。而 `start_ccs_backfill:260-264` 明确写了"别把「补全分类号」永久锁死"——
那条保护只盖住了**主线程**，没盖住**工作线程**。

**最小复现**（**我注入的异常**，见下"诚实边界"）：把 `bf._update_counts` 换成抛异常的 lambda 后起一批。

**原始输出**
```
=== E) worker loop-body failure OUTSIDE the per-item try -> lock/running stuck ? ===
  after fault: running = True / done = 1 / total = 1
  _LOCK.locked() = True
  second start: RuntimeError -> ccs_backfill_busy
```
**后果**：此后每次 POST 都 409，`/kb/ccs/backfill/status` 永远 `running: true`，界面按钮永远停在
"停止补全分类号"并每 3 秒轮询一次，**唯一出路是重启进程**。

**诚实边界**：这个故障点是我**人为注入**的（`_update_counts` 的 lambda），我**没有**在真机上观察到它自发发生 ——
它是一条**结构性（latent）**缺陷，不是已发生的事故。列 MED 而非 HIGH 就是这个原因。

---

### MED-6 `9460344` 的核心数字不可复核且与自己样本算术不相容

**位置**：`docs/KB-FOLDER-PLAN.md:1564-1572`（提交 `9460344` 唯一改动）
```
1564: **为此单独做了一次逐层独立覆盖实测**（只读真库，30 篇：7 篇法规 + 2 篇查无 +
1566: **① 官方接口独立命中 24/30，② 网页抓取独立命中 24/30，两层命中的是同一批 24 篇**
1572: 取证：`var/tmp/ccs-backfill-preview-20260922/layer_coverage.json`。
```

**命令与原始输出**
```
$ git show 9460344 --stat --format=''
 docs/KB-FOLDER-PLAN.md | 9 +++++++++

$ git check-ignore -v var/tmp/x.json
.gitignore:9:var/*	var/tmp/x.json

$ Test-Path 'var\tmp\ccs-backfill-preview-20260922\layer_coverage.json'
False
$ Get-ChildItem -Recurse -Filter 'layer_coverage*'      → 无结果
```
**两处问题**
1. **算术不相容**：30 篇 = 7 法规 + 2 查无 + 21 老标准。按本批**自己的**判据
   （`ccs_fetcher.py:78-82, 702-711`：不像标准号的字段 ⇒ `not_applicable`、**一次网络都不打**、
   "CCS 对法规**永远没有**"），那 7 篇法规命中数必为 0 ⇒ 30 篇里**最多 23 篇**可能命中。
   而提交说两层**各 24/30**。24 > 23 ⇒ 这组数字**不可能同时成立**。
   （要么那 7 篇里有 ≥1 篇被判成"命中"，即该实测用的语义与**出厂链路**不同 —— 那这份"逐层独立覆盖"
   就不描述出厂链路；要么样本构成那句话错了。两种都可能，但提交里没有任何一句话能消解它。）
2. **取证不在树上**：`var/*` 被 `.gitignore:9` 整目录忽略，该 JSON **不在冻结提交里** ⇒
   复核者（我）无法打开它核对数字。报告自称"只写证据够的那部分"，但它给的那个"证据"不随提交走。

**诚实性裁定（问题 6 的直接回答）**：**这句是诚实的，不是给未证实的东西镀金**。理由：
它主动写出对业主假设的**否定**结果（"业主说的'官方接口可能不返回一些老标准'这次没能复现"）、
主动把结论**限定**在证据够的部分、并明确写"**增量价值在现有数据上未被证实**"，
把保留第②层的理由退回到"通路是活的 + 有判据钉住"而不是"它更有用"。
问题不在措辞态度，而在**数字本身**（见上两条）。

---

### LOW-1 ~ LOW-7

- **LOW-1** `plugin/client/KsKnowledgePage.tsx:1942-1943` 注释声明"三条分支的依据**全部来自后端**…界面**不自己推断**"；
  但 `:1955-1960` 第 1 条分支在只有 `ccs_tag` 的情况下把原因**写死**为"树里没有对应的那一层"
  （同一段注释 `:1945-1946` 自己承认还有第二种可能"或落进了兜底桶"）。
  `grep '没有对应的那一层' plugin/scripts/*.mjs` → **No matches** ⇒ 该分支无任何 smoke 断言
  （stub 里 `ccs_tag` 非空的两篇 `doc_in_q`/`doc_in_ok` 都**有**建议，走不到这一支）。
- **LOW-2** 按钮（`KsKnowledgePage.tsx:2544-2556`）只显示"还缺 N 篇"，从不显示一次最多补 50 篇；
  后端在 `/kb/ccs/summary` 里下发了 `max_batch`/`default_batch`（`routes_kb_folders.py:527-528`），
  `grep max_batch|default_batch KsKnowledgePage.tsx` → **无引用**。上限只在**按下之后**、且只在被截断时才说
  （"这一批先补一部分"）。
- **LOW-3** 按钮 tooltip 原文 `插件自己按「官方接口 → 网页抓取 → 本地对照表」逐篇查缺的分类号`（`:2550`），
  而后端 `SOURCES`（`ccs_fetcher.py:64-65`）是**四**项（含 `seed_file` / "本地种子文件"，并在 summary 里下发）。
- **LOW-4** `ccs_backfill.py:151` `state = ccs_store.get_ccs_state(doc_id)` —— 赋值后全文无引用（每篇白查一次库）。
- **LOW-5** `_PROGRESS["last_error"]` 在 `ccs_backfill.py` 全文出现 2 次，都是**写 None**
  （`:55` 初始化、`:249` 每批重置）⇒ 任何失败都不会填它，字段恒为 `None`。
- **LOW-6** `ccs_fetcher.py:723` `worst = _combine_verdict(facts) if use_network else OUTCOME_NOT_FOUND`，
  `_reason_text(OUTCOME_NOT_FOUND, …)` 返回"查无：**答话的站点里都没有**这个标准号" ——
  `use_network=False` 时一个站点都没问过。既有用例 `test_use_network_false_is_local_only` 只钉 `outcome`、不钉 `reason`。
  生产代码里 `use_network` 只出现在 `ccs_fetcher.py` 自身（`grep` 6 处，无调用方传 False）⇒ 目前不可达，故只记 LOW。
- **LOW-7** 409 映射（`routes_kb_folders.py:586-588`）我只**静态读过**：没有 HTTP 级用例；
  既有 `test_backfill_busy_is_refused_not_queued` 走的是函数级 `bf.start_ccs_backfill`。

---

## 4. 已核验通过的（正面证据，避免"只报坏消息"）

1. **链的层序与来源如实**（点 1 的核心）。用真实链（假 transport）验证：官方先试 3 种形式全 `no_match`，
   网页命中 ⇒ 返回值与**台账**都记 `web_scrape`，且 attempts 逐条留痕：
   ```
   === H) ===
     resolve_ccs: outcome = found / source = web_scrape / code = K73 / form = full
     official calls = ['GB/T 93001-2020', 'GBT93001-2020', '93001']
     scrape calls   = ['GB/T 93001-2020']
     attempts layers/results = [('official_api','no_match'), ('official_api','no_match'), ('official_api','no_match'), ('web_scrape','hit')]
     LEDGER source = web_scrape / keyword_form = full / ccs_code = K73
     domain_tags   = ["CCS:K73 特殊灯具"]
   ```
   官方命中后**不再**抓网页，由 `test_official_hit_never_calls_web_scrape` 钉住（我方跑，36 passed 内含）。
2. **小写码折大写贯通到分类树**：站点给 `k73` ⇒ 标签 `CCS:K73 特殊灯具`（上一段原始输出）。
3. **失败三分类互斥**（`network_failed` / `not_found` / `parse_failed`）由 M1/M2 两个变异**当场打红**证明判据是硬的。
4. **schema 兼容与回退**（点 4，在私有临时库上做，真库只读）：
   ```
   === F) pre-batch schema -> "old DB" -> new init_schema upgrade ===
     old schema mentions doc_ccs_state? False
     old db has doc_ccs_state = 0
     old db doc_meta col count = 28 tail ['downloaded_at','source_status','created_at','updated_at']
     after upgrade: doc_ccs_state present = 1
     after upgrade: doc_meta col count = 28 | NEW COLUMNS on doc_meta = []
     after upgrade: legacy row = ('legacy1','GB/T 88888-2019','["x"]')
     after upgrade: doc_ccs_state cols = ['doc_id','outcome','source','keyword_form','matched_no','ccs_code','ccs_name','reason','attempts_json','checked_at','applied_at']
     ledger row written on upgraded db = [('legacy1','not_found','cha wu')]
   === G) rollback: old code against the upgraded DB ===
     old-code init on upgraded db OK, doc_meta cols unchanged = True
     old-code style SELECT = ('legacy1','GB/T 88888-2019','["x"]')
     doc_ccs_state still there (inert for old code) = ('doc_ccs_state',)
     old schema contains DROP TABLE? = False
   ```
   ⇒ 旧库直接升上来：**纯追加**（新表 1 张、`doc_meta` **零**新列）、旧行无损、`init_schema` 幂等（我连跑两次）；
   回退旧代码：多出的表是惰性的、旧 schema 无 `DROP TABLE` ⇒ **不会坏**。
   `git diff 9653fe6~1..9460344 -- src/core/storage/sqlite_db.py | grep _DOC_META_EXTRA_COLS` → 0 ⇒ 未动既有补列清单。
   另：`src/core/api/server.py:276` 在**任何请求之前**调 `init_schema()` ⇒ 接口路径上表必然存在。
   **本次探针的边界**：我建"旧库"时剔除了 `clause_vec`（裸 `sqlite3` 没有 `vec0` 扩展），
   只影响我这只临时库，与 `doc_ccs_state` 的结论无关。
5. **常量与父代理转述一致，无出入**：
   ```
   DEFAULT_BACKFILL_DOCS = 50 / MAX_BACKFILL_DOCS = 200
   bf.DOC_PAUSE_S = 1.0
   plan 201 ids -> ValueError : 一次最多 200 篇，收到 201 篇
   ```
   （源码 `ccs_backfill.py:41,43,45`；route 夹取 `routes_kb_folders.py:575-578`：`limit` 必须 1~200。）
   ⇒ **任务书里那两个数字是二手的，但回源码核过，对得上**，没有可报的出入。
6. **真库只读读数**（`file:…?mode=ro`，未写一个字节）：
   ```
   db: C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db size 2340388864
   doc_ccs_state table: [('doc_ccs_state',)]
   ccs_code nonnull: [(0,)]          ← schema.sql 的注释"该列全库为空"属实
   std total: [(6417,)]
   std with CCS tag: [(6087,)]
   docs with >1 CCS tag: [(0,)]
   ```

---

## 5. 我明确没能验证的

1. **真机（真网络）上的三层链行为**——一条都没验。全部网络层证据来自注入的假 transport；
   `test_ccs_chain.py:117-129` 的 `_no_real_network` fixture 也强制如此。所以
   "官方接口现在到底通不通""cssn 的 HTML 锚点 `ph_list_title` 现在是否仍是那个形状"**我无法判断**，
   本批对旧实现的三条真机缺陷指控（httpx 构造失败 / 抠成裸数字 / 锚错元素）我**没有**独立复现，只读了代码与注释。
2. **`9460344` 那次 30 篇逐层覆盖实测本身**——取证 JSON 不在冻结树（`.gitignore:9 var/*`），
   真库我按纪律**只读**、且那 30 篇的清单不在提交里 ⇒ 我无法重跑、无法核对命中集合。
   我只核到"该数字与它自己的样本构成算术不相容"这一层。
3. **界面渲染/交互的真实效果**——按任务书要求**只做静态阅读**，没跑 node 门禁
   （`smoke-kb-page-render.mjs` 的 N16–N20 我一行没执行）。LOW-1 的"该分支无断言"是 grep 结论，
   不是跑出来的。**"页面能正常渲染这个按钮"我未验证。**
4. **409 `ccs_backfill_busy` 的 HTTP 层行为**（LOW-7）：只静态读 `routes_kb_folders.py:586-588`。
5. **`plugin/client.js`（构建产物）与源码是否一致**——未跑 `build:client`，未比对。
   （改动面里有 `plugin/client.js` 352 行。）
6. **`close_connections_under`（`sqlite_db.py:185-238`）在真实多线程收尾下的效果**——只读了实现；
   `test_ccs_chain.py:54-103` 的模块级 fixture 会走到它，我跑用例时它**没报错**，
   但"只关自己那一份库"这个性质我**没有**独立做成实验（没构造"别的模块持连接"的现场）。
7. **`plugin/client/api.ts` 归一化器丢字段的风险**——静态核过 `normalizeCcsBackfillStatus`
   （`api.ts:3804-3821`）确实映射了 UI 用到的全部字段（含 `not_applicable`/`applied`/`cancelled`/`missing`/`skipped`），
   但**没在浏览器里跑过**，所以"字段到了 DOM 上没丢"未验证。
8. **`%TEMP%` 下大量陈旧 `ks_test_*` 目录**：我**一个都没动**（照纪律只删我自己建的
   `ks-verify-ccs-<pid>-<rand>`）。发现它们数量极多（`AGENTS.md` 记的"积压 1833 个"看起来仍成立），
   但那是既有状况，不属本批。

**任务书更正（不是提交说明的问题）**：任务书给我的真库路径
`%APPDATA%\KnowledgeStation\knowledge.db` **不存在**；实际路径是
`%APPDATA%\KnowledgeStation\database\knowledge.db`（`config.py:158`：`data_dir / "database" / "knowledge.db"`）。
我按实际路径只读探测，结论见 §4.6。

---

## 6. 我核了但提交说明说错了的地方

1. **`ccs_backfill.py:24-26` 的"补全再跑一遍就是 0 篇"**——对失败的篇**不成立**（MED-4 原始输出：
   `SECOND queued = 1`）。这句是**代码注释**（也是本批"幂等"口径的书面依据），不是提交消息，但它是
   提交消息之外**最容易被下一个人当成事实**的一句，且没有任何用例覆盖它的反例。
2. **`9460344` / `docs/KB-FOLDER-PLAN.md:1566` 的"两层各 24/30"**——与同句给出的样本构成
   （`7 篇法规 + 2 篇查无 + 21 篇老标准`）**算术冲突**（上限 23）。见 MED-6。
   （措辞态度本身是诚实的 —— 见 MED-6 末段裁定。）
3. **`ccs_fetcher.py:747-757` `_reason_text` 的 network_failed 分支**把 `captcha` 当作"网络不通或被拦"的
   首个原因输出，但 captcha 已把 `saw_response` 置真 ⇒ `_combine_verdict` 永远不会给出 `network_failed`
   ⇒ **那段 `captcha` 归因代码是死的**，实际 captcha 走的是"页面结构可能变了"（MED-3）。
4. `plugin/client/KsKnowledgePage.tsx:1942-1943` 的"三条分支的依据**全部来自后端**…界面**不自己推断**"
   —— 第 1 条分支是界面自己推断的（LOW-1）。
5. ⚠ 反过来说一句：任务书里**转述**的 `DEFAULT_BACKFILL_DOCS=50` / `MAX_BACKFILL_DOCS=200`
   **回源码核过是对的**（§4.5），不必当成二手结论打折。

---

## 7. 收工快照（与 §0 对照）

```
$ git -C "D:\AI\work space\zcode-verify-ccs" rev-parse HEAD
9460344281bd347e7afedbb7f061a7b58478ad5e

$ git -C "D:\AI\work space\zcode-verify-ccs" status --short
?? VERIFY-REPORT-ccs-chain.md

$ git -C "D:\AI\work space\zcode-verify-ccs" diff --stat
（空 ⇒ 已跟踪源码一个字节未改：三次变异均以绝对路径 git checkout -- 还原，
  按纪律用 git status 而非文件哈希判定）
```
`status --short` 里那**一条** `??` 就是本报告本身 —— 复核树唯一的产物，无其它新增/改动。
（对照 §0 开工时该命令为空。）
我建的临时探针目录：`%TEMP%\ks-verify-ccs-<pid>-<rand>\`（多条），**只删我自己这几份**，未触碰任何更早的 `%TEMP%` 内容。
