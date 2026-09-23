# 独立复核报告 —— B1（重新解析丢目录归属）+ B2（叠字检查两个假绿洞）

复核树：`D:\AI\work space\zcode-verify-b1b2`（冻结 tag `verify-freeze-b1b2`）
区间：`4ed4b0d~1..verify-freeze-b1b2` = **3 笔**（`4ed4b0d` / `0b05841` / `113cb58`）

## 0. 机械动作（开工 / 收工）

```
开工：git rev-parse HEAD   -> 113cb5854df1be8a75823a46112a43508a0a5c0b
      git status --short   -> (空)
      git merge-base --is-ancestor 4ed4b0d verify-freeze-b1b2  -> exit 0   ✅ 方向成立
      git rev-list --count 4ed4b0d~1..verify-freeze-b1b2       -> 3          ✅ 与任务书一致
收工：git rev-parse HEAD   -> 113cb5854df1be8a75823a46112a43508a0a5c0b
      git status --short   -> ?? VERIFY-REPORT-b1b2.md   （**只有本报告这一份未跟踪文件**）
      git diff --stat verify-freeze-b1b2 -- .  -> (空)     ⇒ 跟踪文件一个字节都没动（所有变异已还原）
```

依赖两份都真拷贝：`plugin/node_modules`（9 项，LinkType 空 = 真目录）+ 仓库根 `node_modules`（42 项）。
本机浏览器 = `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（`ui-render-shot` 自己找得到）。
**没跑** `scripts/run-gates.ps1` / `smoke-all.mjs` / `pytest -q` 全量（父代理已跑，任务书禁止重复）。
跑过的最重的两条：`pytest tests/test_reingest_keeps_filing.py`（8 条）、`node plugin/scripts/ui-render-shot.mjs`（26 次）。
**没跑** `smoke-kb-pad-pixels.mjs`（任务书说它会取门禁锁；实测**它没有任何锁代码** —— 见 §4 第 1 条）。

---

## 1. B1 —— 结论：**PASS**（含 1 条 MED 缺口）

判据本体真跑（冻结树、未变异）：

```
$ pytest tests/test_reingest_keeps_filing.py -q --no-header -p no:cacheprovider
8 passed, 5 warnings in 70.96s        exit 0        （M0 与 M7 各跑一次，结果一致）
```

### 1.1 搬运一条不少、一条不多（PASS）

- 正向：`_members_of(new_doc) == old_members`（两条目录归属全搬）、`moved_members == 2`。
- 反向：`_file_member_rows(db) - {(a,new),(b,new)} == decoys_before`（别人的归属一条不动）、
  别人的状态行逐条比对、`item_kind='folder'` 的目录边集合逐条相等。
- 篇数：`list_folder(a).files_total` 重导前后同为 2、`file_count_direct/deep` 三档都相等。
- 我核了代码：`folder_member` PK = `(folder_id,item_kind,item_id)` + `INSERT OR IGNORE`
  ⇒ 幂等、不虚增（`tests/test_reingest_keeps_filing.py:343` 那条正向钉住 moved=0）。

### 1.2 `stage` 口径（PASS，且两条"照搬会造假话"的说法我核过）

四条分支在代码里就是这么写的（`src/core/knowledge/folder_store.py:1411`
`final_stage = "filed" if (moved and stage != "failed") else stage`），四条都有用例。
提交说"照搬旧 stage 会造两种假话" —— **两种我都回代码核了，成立**：

- `start_reingest` 在起线程前就把旧行写成 `recognizing`（`src/core/ingestion/reingest.py:150`），
  而快照是**之后**才拍的（`pipeline.py:2190`）⇒ 快照里的 `stage` 确实是 `recognizing`；
  照搬 = 新文档永久"识别中"。
- 旧行 `failed`、这次成功 ⇒ 照搬会把成功的重解析盖回"识别失败"（有用例钉住）。

### 1.3 "半路的目录被删"（PASS，护栏真在）

`folder_store.py:1402-1405`：先 `SELECT folder_id FROM folder`，只插**还在的**，其余进
`missing_folders` / `skipped_missing_folders` 如实计数；`filed` 的推导改看 `moved`。
我核了"什么算目录没了"：`folder` 表**没有软删列**，`delete_folder(purge)` 是硬删
（`folder_store.py:664-665` 同时删 `folder_member` 与 `folder`）⇒ 护栏的判据与真删除一致。

### 1.4 "没有要搬的" vs "搬运失败"（PASS）

`filing_assets_carry_error`（`pipeline.py:2327/2340/2408`）+ `reingest.py:112`，与 `carried is None`
分得开。我把这条**变异掉**（见 1.5 M5）→ 用例变红。

### 1.5 判据有没有牙 —— 六次变异，五次红、**一次没牙**

每次变异都从 `git status --short` 为空的树出发，备份在 `%TEMP%`，跑完 `Copy-Item` 还原，
收工 `git status --short` = 空。**还原用 `git status` 判，不用哈希**。

| # | 注入点（冻结树行号） | 注入内容 | 结果 |
|---|---|---|---|
| M1 | `src/core/ingestion/pipeline.py:2190` | 拍快照那句 → `_carried_assets = None` | **exit 1**，3 failed（`..._moves_every_membership...` / `..._of_failed_parse_marks_failed...` / `..._carry_failure_is_reported_not_silent`） |
| M2 | `src/core/storage/clause_repo.py:371` | `item_kind='file'` → `'__mut__'`（删不到任何行） | **exit 1**，2 failed |
| M3 | `src/core/storage/doc_delete.py:94` | 同上 | **exit 1**，1 failed |
| M4 | `src/core/knowledge/folder_store.py:1402` | `missing = []`（去掉"目录还在才搬"） | **exit 1**，1 failed（`..._skips_folders_deleted_after_the_snapshot`） |
| M5 | `src/core/ingestion/pipeline.py:2340` | `carry_error = None`（失败重新变成"没有要搬的"） | **exit 1**，1 failed（`..._carry_failure_is_reported_not_silent`） |
| M6 | `src/core/knowledge/folder_store.py:1411` | `moved` → `members`（commit 里明写改掉的那半个） | **exit 0，8 passed** ← **没有牙** |

原始红（M1，节选）：

```
##### M1-snapshot-shortcircuited  exit=1
E       AssertionError: 解析失败就不搬归属了？归属与解析成败无关
tests\test_reingest_keeps_filing.py:309: AssertionError
E       AssertionError: 搬运失败被静默成『没有要搬的』：None
tests\test_reingest_keeps_filing.py:378: AssertionError
FAILED tests/test_reingest_keeps_filing.py::test_reingest_moves_every_membership_and_touches_nothing_else
FAILED tests/test_reingest_keeps_filing.py::test_reingest_of_failed_parse_marks_failed_even_when_membership_carried
FAILED tests/test_reingest_keeps_filing.py::test_carry_failure_is_reported_not_silent
3 failed, 5 passed, 5 warnings in 65.07s
```

原始红（M4，节选）：

```
##### M4-no-missing-folder-guard  exit=1
E       AssertionError: {'doc_id': 'stale_dst', 'moved_members': 2, 'members': ['fld_...5','fld_...6'], 'stage': 'filed', ...}
tests\test_reingest_keeps_filing.py:410: AssertionError
FAILED tests/test_reingest_keeps_filing.py::test_restore_skips_folders_deleted_after_the_snapshot
1 failed, 7 passed, 5 warnings in 70.30s
```

原始"没牙"（M6，全文）：

```
##### M6-filed-derived-from-members  exit=0
8 passed, 5 warnings in 70.13s
```

### 1.6 棘轮盲区：断言有没有被放宽/换成恒真（**没有**）

- 这一批的判据是**新文件**（`tests/test_reingest_keeps_filing.py`，4ed4b0d 建 348 行、0b05841 追加 70 行），
  `git show` 逐行看是**纯追加**：没有删掉任何一条断言、没有把哪条改成 `assert True`、没有新增 skip。
- 没有依赖被"悄悄跳过"：8 条真的在跑（`8 passed`，不是 `skipped`）。
- 断言不是恒真：M1–M5 能把其中 7 条打红，说明它们真的挂在被改的代码上。

### 1.7 B1 缺陷 / 残余

**【MED-1】commit 明写的那半个改动没有任何判据钉住。**
`0b05841` 说"`stage` 的 `filed` 推导改成看**真的搬成了几条**（`moved`），目录全没了就不说它还归位在某个目录里" ——
代码确实这么写（`folder_store.py:1411`），但**没有任何一条用例**能区分 `moved` 与 `members`：
把它们换回来（M6）⇒ **8 passed / exit 0**。
现有用例只覆盖"部分目录被删"（`moved=1`，两者同判"filed"）；**"目录全被删"这个唯一能分开两者的形态没有用例**。
（`test_restore_refuses_a_missing_target_and_is_idempotent` 里第二次 restore 恰好是 `moved=0 && members=[f]`，
但它没有断言 `again["stage"]`。）⇒ 建议补一条：快照后把**全部**目录删掉 ⇒ `stage` 必须不是 `filed`。

**【LOW-2】残余名单只登记了 `suggested_folder_id`，`placed_folder_id` 同病未登记。**
`CARRY_STATE_FIELDS` 五个字段全是逐字 `UPDATE`，都不校验目录还在不在
（`folder_store.py:1365`-`1424`；`doc_filing_state` 也没有 FK —— 我核了 `schema.sql`）。
commit 的边界只写了 `suggested_folder_id`。`placed_folder_id` 指向已删目录时**界面读不到它**
（`plugin/client/**` 里没有 `placed_folder_id` 的渲染点，只有 `suggested_folder_id` 被用来拼
「按建议归位（X）」）⇒ 后果不可见，所以我判 LOW，不是新洞，是登记不全。

**【LOW-3】"失败要说出来"只到 API JSON，没有到人眼。**
`filing_assets_carry_error` 进了 `run_full_ingest` 返回值 + `reingest.py` 逐篇结果，
`GET /api/v1/kb/inbox/reingest/status`（`routes_kb_folders.py:499`）会把它原样吐出来 —— 这一层是通的。
但插件端**没有任何地方读它**（全仓 grep：`plugin/**` 零命中）⇒ 业主在界面上仍然看不到"这次归属搬炸了"。

**【LOW-4】快照只活在内存里。** 拍快照（`pipeline.py:2190`）→ 删旧文档（`:2192`）→ 入库事务
→ 落盘（`:2331`）之间若崩/写库失败，`clause_repo.delete_document` 现在**把归属一起删了**
（旧行为是留一堆指向已删文档的悬空行，反正 JOIN 看不见）⇒ 用户可见后果与改前相同（都丢），
但这条路上"快照"救不了任何东西。属设计边界，登记。

---

## 2. B2 —— 结论：**PASS（两个洞都真修上了）**，但新判据自己的"量不到就是红"有 **1 条 MED 缺口**

判据模型（`plugin/scripts/ui-render-shot.mjs`）：三张新表 `pieceOverlaps` / `ctrlHits` / `ctrlClips`
+ 三个计数 `ctrlCount` / `textCount` / `pieceCount`，Node 侧四条新断言
（`ui-render-shot.mjs:3544-3577`）。下面每条都是我亲手在**冻结树源码**上造形态量出来的。
**变异一律打在 `plugin/client/**`（脚本从源码 esbuild 打包，不是用 `client.js`），
每次从 `git status --short` 为空的树出发，跑完还原，收工 status 空。**

### 2.1 洞①「绝对定位的控件压在文件夹名那段文字上」：改前绿 / 改后红 ✅

我注入了两版，**第一版是无效对照，一并留痕**：

- **E1/E1b（不合格对照）**：按钮搬进 `ks-lhead-name` span 并 `position:absolute`，但盒子
  **没有完全包住**那段文字 ⇒ 改后红、**改前也红**（旧 `gaps` 表抓到 -35px / -96px 负间隙）。
  这两跑**不能**当"洞①存在"的证据 —— 我第一版的几何没命中作者说的那种。
- **E1c（合格对照）**：`left:0; top:0; width:136; height:22`（**完全包住**名字那段文字，
  于是文字项在摊平时被"被更大盒子包住"那条**剔掉**，`kept` 里只剩 3 件互不相干的东西）：

```
----- RUN E1c-hole1-current  script=ui-render-shot.mjs  width=520  exit=1
  ctrlCount=2 textCount=4 pieceCount=3
  ctrlHits=button.ks-export-effect[导出效力总览]|知识库|39x16.5
  problems=**控件压在文字上**：button.ks-export-effect[导出效力总览] 与文字「知识库」的矩形真相交（水平 39px × 垂直 16.5px）—— 绝对定位叠上去也算压字
----- RUN E1c-hole1-PREB2  script=verify-preb2-shot.mjs  width=520  exit=0
  checked=True
  stderr> · #listcap 自检通过：这一行 3 个可见成员、两两无重叠，相邻最小水平间隙 28px（下限 4px）；成员 ["button.ks-export-effect[导出效力总览]@204-340","button.Button_button[在此范围内提问]@368-492","span.ks-kb-hint[4 个子目录 · 0 篇文件]@204-316.7"]
```
（1300 档同样：改后 exit 1 / 改前 exit 0。）
我另外用 pre-B2 副本 dump 了 `pieces`/`kept` 取证，确认机理就是 commit 写的那句：
漏掉的那条文字 `#text.[知识库] x204-243 y205.5-222.5` 被 136×22 的按钮盒子**完全包住** ⇒ 不进 `kept`
⇒ 旧的两张表（`overlaps` 只算 members、`gaps` 只算 kept）**一条都不报**。
"改前"脚本 = `113cb58^:plugin/scripts/ui-render-shot.mjs`（blob `c3dc7da4`，262387 字节，
`git cat-file blob` 生成、用完删除，不在仓里留文件）。

### 2.2 洞②「控件被 overflow 裁到行外」：改前绿 / 改后红 ✅（一次就命中）

形态：行 `<div className="ks-list-cap" style={{overflow:'hidden'}}>` + 按钮
`style={{... position:'relative', left:2000}}`。

```
----- RUN E2-hole2-right-current  script=ui-render-shot.mjs  width=520  exit=1
  ctrlClips=button.ks-export-effect[导出效力总览]|box=66x16|vis=0x16|cut=1868
  problems=**控件被裁到行外**：button.ks-export-effect[导出效力总览] 的盒子 66x16px，落在这一行可见区里的只有 0x16px（被裁掉 1868px）
----- RUN E2-hole2-right-PREB2  script=verify-preb2-shot.mjs  width=520  exit=0
  checked=True
  stderr> · #listcap 自检通过：… 相邻最小水平间隙 82px（下限 4px）；成员 [...,"button.ks-export-effect[导出效力总览]@2294-2360",...]
```
1300 档同样（改后 exit 1 / cut=1747.3；改前 exit 0）。
注意"改前"那跑的成员表里按钮在 `@2294-2360`（早就跑到屏幕外两千多像素），旧判据照样判"通过"。

### 2.3 裁剪的四个方向（不是只测一个方向）✅

`ctrlClips` 的 `cutMax` 取四边最大值（`ui-render-shot.mjs:2140-2142`），我逐向实测：

| 方向 | 注入 | 结果 |
|---|---|---|
| 右 | `left:2000` | exit 1，`vis=0x16 cut=1868` |
| 左 | `left:-2000` | exit 1，`vis=0x16 cut=1910` |
| 下（行外） | `top:200` | exit 1，`vis=66x0 cut=170` |
| 上（行外） | `top:-200` | exit 1，`vis=66x0 cut=194` |

（"底边被裁"没单独造，但它与"上"是同一条表达式的镜像（`max(0, rect.b - cb.b)`）；
上/下两向都是 `vis=…x0` ⇒ 垂直方向真的并入了可见区计算。）

### 2.4 判据有没有被削弱（**没有**，逐行核过）✅

`git show 113cb58 -- plugin/scripts/ui-render-shot.mjs` 一共 **4 行删除**，逐行列出：

```
- *      之间 **0px** —— 两个东西贴成一个词，用户读不出这是两件事）。      ← 文档注释
- *   没有它 ⇒ 明说没判（skipReason），不静默通过。 */                     ← 文档注释
-    + `（下限 ${String(LISTCAP_MIN_GAP)}px）；成员 ${JSON.stringify(...)}`  ← stderr 成功文案
-    + '必须各自成件：既不许边框盒真重叠，也不许贴成 0px（…）。')          ← stderr 失败文案
```

⇒ **没有删掉/放宽任何一条断言**：`LISTCAP_MIN_GAP` 仍是 4、`lc.n < 2` 那条仍在
（`ui-render-shot.mjs:3530`）、`overlaps` 仍是"成员两两边框盒相交"、`gaps` 仍是"相邻 <4px 即红"，
新增的三张表与四个计数是**纯追加**（`listCapCheck` 里原来那几项一个没少）。

### 2.5 新判据自己守恒（没有为抓洞②到处假红）✅ —— 这是**抽样**

冻结树、无变异，逐跑（每跑都是 `exit 0` 且 `listCapCheck.checked=true`）：

| 组合 | 宽 | ctrlCount / textCount / pieceCount | overlaps / gaps |
|---|---|---|---|
| `kb|`（manage 默认） | 520 | 2 / 4 / 4 | 0 / 2 |
| `kb|` | 900 | 2 / 4 / 4 | 0 / 3 |
| `kb|` | 1300 | 2 / 4 / 4 | 0 / 3 |
| `kb|kb-inbox` | 520 | 2 / 4 / 4 | 0 / 2 |
| `kb|kb-ask` | 520 | 3 / 7 / 8 | 0 / 5 |
| `kb|kb-empty` | 520 | 2 / 4 / 4 | 0 / 2 |
| `kb|kb-level` | 520 | 2 / 4 / 4 | 0 / 2 |
| `kb|kb-files` | 1300 | 2 / 4 / 4 | 0 / 3 |

⚠ **这是抽样（8 个组合），不是作者报的 36/27 全覆盖**；我只挑了对新判据最可能假红的那些
（含"空目录"与"待分类"层，因为 `kb-empty` 是我怀疑 `ctrlCount>0` 会假红的那一档 —— 实测这一行
在空目录下照样有名字 span + 导出按钮 + 提问入口 + 计数，三个计数都 > 0，**没有假红**）。
另外 3 个面（渠道库/办事台/备料）结构上没有 `.ks-list-cap` ⇒ 走 `listCapSkipReason`，与改前一致。

### 2.6 第三条路：**"量不到就是红"只覆盖了半条路（MED-2）**

新写法声称"三张表**量不到就是红**（'没验到'不许渲染成'通过'）"。它的实现只挡得住
**"`#listcap` 这个键在、但表缺"**；下面两条路它挡不住：

**(a) 那一行**从 DOM 里消失 ⇒ 判据自己说"不适用"，`exit 0`。（**我没有注入任何异常**，
只是把那一行的类名改掉 —— 这是真实的 UI 回归形态）

```
----- RUN E6-row-class-renamed-current  script=ui-render-shot.mjs  width=520  exit=0     ← 假绿
  checked=False  skipReason=这一跑没有 .ks-list-cap（page=kb navPage=manage）—— 这一行不适用
  problems=
  stderr> · #listcap 自检：**这一跑不判**（这一跑没有 .ks-list-cap（page=kb navPage=manage）—— 这一行不适用）
----- RUN E6-row-class-renamed-current-ask  width=520 interact=kb-ask  exit=1
  stderr> ❌ --interact 有场景**没落地**（这一跑不算通过）：
```
默认组合（`kb|`）**exit 0**；只有 `kb-ask` 那一跑会红 —— 而它红的是 `askCheck`（"提问按钮必须落在
`.ks-list-cap` 那一行"），**不是**压字判据。所以"这一行的成员不压字"这件事，只要那一行消失，
就是静默通过。**根因**：`.ks-list-cap` **不在任何 `PAD_REQUIRED` 条目里**
（`ui-render-shot.mjs:2416-2472` 逐条看过）⇒ 没有"声明了就必须量到"的棘轮兜底。

**(b) 探针里抛一次异常**（我注入的，真机未观察到）⇒ 整段探针被 `catch` 吞掉，
`measured = {"error": ...}`（`ui-render-shot.mjs:2169-2170`），而 **Node 侧从不看 `measured.error`**
（全文件 grep：只有 `measured['#…']` 取值，没有一处判 `error`/`parse_error`）⇒
`#listcap` 消失 ⇒ 判据报"没有 `.ks-list-cap` —— 这一行不适用"（**把失败说成了没有**）。

```
----- RUN E4-probe-throw-current  script=ui-render-shot.mjs  width=520  exit=1
  checked=False  skipReason=这一跑没有 .ks-list-cap（page=kb navPage=manage）—— 这一行不适用
  stderr> ❌ 知识库页几何自检失败（左列并排 + 目录/文件两层行高一致）：
```
这一跑整体仍是 exit 1，但**红的不是它**（是另一条几何判据因为拿不到自己的键而红）——
即：**这一行的判据把自己的"没量到"说成"不适用"，靠别的判据误打误撞兜住**。
判别力上是"归因错误"，不是干净的假绿；但 (a) 那条是干净的假绿。

⇒ 建议（不在本轮替作者设计，仅指出形状）：`lc === undefined` 与 `measured.error` 必须分开处理 ——
有 `.ks-list-cap` 的**面**上键缺失 ⇒ 红；并把 `.ks-list-cap` 写进 manage 面各组合的 `PAD_REQUIRED`。

### 2.7 其他可能的第三/第四条路——我查了，**没找到**

- 控件×控件相交而无文字：被既有 `overlaps`（成员两两边框盒）挡住（两个控件都是成员）。
- 父子都跳过导致整块漏判：`ctrlHits` 只跳 `C.el.contains(T.node)`（自己的内容），
  祖先方向不跳；完全盖住的那种正是 E1c 抓到的。
- `rowClipOf` 的上溯：`guard<64` 且 `cur === capEl` 时先算这一行再 break ⇒ 行自己的
  `overflow:hidden` 算在内（E2 就是靠这一条）。控件没有可裁剪祖先时返回 `null` ⇒ 不判 ——
  这正是 commit 已登记的残余（"相对定位推出去但没有任何 overflow"，我**没有**去证伪它）。

---

## 3. 我明确**没能**验证的

1. **全量 pytest**（2362/3 那个数）没复跑 —— 任务书禁止；我只跑了本批 8 条 + 6 次变异 + 一次
   `--collect-only`（`2341 tests collected in 2.94s`）。
2. **真库端到端**（`var/tmp/b1-reingest-e2e.py`，真库副本 + 真 PDF `GB 11859.3-1989`）**没复跑**；
   真库 `%APPDATA%\KnowledgeStation\database\knowledge.db` 我一次都没碰（没读也没写）。
3. **`smoke-kb-pad-pixels.mjs` 没跑**（父代理报 27 组全 PASS 我没独立复核）⇒ B2 的"无新假红"
   我只抽样了 8 个组合。
4. B2 的 (b) 那条（探针抛异常）**是我注入的**，真机未观察到；真机上我也没有触发过"探针异常"。
5. B1 的"半路目录被删"我是**照既有用例的形态**（直接删 folder 行）复现 + 用真 `delete_folder`
   的代码路径核对，**没有**在真解析跑到一半时手工删目录。
6. `placed_folder_id` 悬空在界面上的**可见**后果我没量（只核了界面代码里没有它的渲染点）。
7. B2 变异都在 **jsdom/无头 Edge 的假数据页面**上做的，**没上真机真库**。

---

## 4. 提交说明 / 父代理转述**说错了**的地方

1. **任务书 §3 写错了**：说 `plugin/scripts/smoke-kb-pad-pixels.mjs` **会取**那把门禁锁
   ⇒ 实测该脚本里**没有任何锁代码**（grep `lock` 零命中；它只 `spawnSync` 逐组跑 `ui-render-shot`，
   而 `ui-render-shot` 也不取锁）。父代理口述的"它不取锁"是对的，写进任务书的那句是错的。
   我因此没有跑它，代价是没独立复核那 27 组。
2. **`0b05841` 的全量数字对不上父代理转述的**：commit 写"全量 ⇒ **2338 passed, 3 skipped**"，
   父代理说"合并态 **2362 passed / 3 skipped**"。我在**冻结树**上量 `--collect-only` = **2341**
   = 2338+3 ⇒ **commit 那个数与本冻结树自洽**，**2362 这个数在本树上收集不到**（差 24 条）。
   父代理的那一跑很可能是在**主仓**（有其他批次在飞、测试文件更多）里跑的 ⇒ **"合并态"这个词
   与实际跑的那棵树不是同一棵**，请核对后更正（我没有跑全量，所以不断言是 2362 错）。
3. **`0b05841` 的"stage 改看 `moved`"这半个改动，实际没有任何判据**（§1.5 M6 / §1.7 MED-1）
   —— commit 把它当成已钉住的一半来陈述（"连带一条：…改成看真的搬成了几条"），实际是**没牙的**。
4. **`113cb58` 的"三张表量不到就是红"这句宣称过宽**（§2.6）：它只覆盖"键在表缺"；
   `.ks-list-cap` 整行消失、或探针抛异常时，它会把自己的"没量到"渲染成"这一行不适用"（exit 0）。
5. 父代理转述的"两个洞各自改前绿" —— **洞② 我一次命中**；**洞① 我第一次造的形态改前也是红的**
   （旧 `gaps` 抓到负间隙），必须把控件盒子**完全包住**那段文字（我第二次的 E1c）才复现出
   "改前 exit 0"。父代理/作者那版变异①的描述里没有这句关键几何，**照它字面复现会得到假的"洞已修"结论**
   （因为改前也红，看起来像"老判据本来就能抓"）。

---

## 5. 最小复现命令

```powershell
$W='D:\AI\work space\zcode-verify-b1b2'
# B1 判据
& 'D:\AI\work space\zcode\.venv\Scripts\python.exe' -m pytest "$W\tests\test_reingest_keeps_filing.py" -q --no-header -p no:cacheprovider
# B2 判据（冻结树，无变异 ⇒ exit 0；含三张新表的实测值走 stderr）
node "$W\plugin\scripts\ui-render-shot.mjs" --page kb --width 520 --out "$env:TEMP\b2.png"
```
本轮的变异/复现脚本（都在 `var/tmp/`，被 `.gitignore` 的 `var/*` 盖住，收工时保留作取证）：
`verify-b1b2-mut.ps1`（B1 六变异）、`verify-b2-mut.ps1`（洞①②+四方向+探针异常+基线抽样）、
`verify-b2-mut2.ps1` / `verify-b2-mut3.ps1`（洞①合格对照 E1c + 行消失 E6）、`verify-b2-dbg.ps1`（pieces/kept 取证）。
