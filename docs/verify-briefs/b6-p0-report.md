# B6 定向独立复核 — 09-23 两提交（P0 黑屏修 / 棘轮基线记新）

复核树：`D:\AI\work space\zcode-verify-b6`（`git worktree add --detach`，冻结标签 `verify-freeze-b6-p0`）
复核范围：**只读/只写本树**。主仓 `D:\AI\work space\zcode` 未写入、未 `git add/commit/checkout`、未删任何 `%TEMP%` 旧目录。
未跑 `scripts/run-gates.ps1`，未跑 `plugin/scripts/smoke-all.mjs`。

## 冻结树状态（首）

```
$ git rev-parse HEAD
42523853ebc4eb61015b5ad05f19cbe07b03bdd7
$ git status --short
（空 —— 干净）
```

## 结论索引（13 条）

| # | 分级 | 一句话 |
|---|---|---|
| A1 | **HIGH** | 冻结区间取错：`verify-freeze-b6-p0` = B，**不含 A**；A 在其后 3 个提交 |
| A2 | **HIGH** | A 的修**真有牙**（运行时双向复现 #300/#310 → 改后全绿） |
| A3 | **HIGH** | A 的修**完整**（可达切面路径 5/5 绿；加强判据下全树 0 残留） |
| A4 | **HIGH** | A 的 `client.js` 是**真重建**（两侧逐字节复现，产物不陈旧） |
| A5 | **HIGH** | 父代理的证据命令 `--nav-page` 是**空闸门**（在有 bug 的树上也 exit 0） |
| A6 | MED | 方向说错：早退面→知识库 抛的是 **#310**，不是提交信息写的 #300 |
| A7 | MED | 观测：办事台面不渲染页内标签条；备料面无标签按钮（备料只能由宿主打开） |
| A8 | MED | 副作用=**无**（两个 useMemo 确在三个非知识库面执行，但纯、无错值、四面对照节点数相同） |
| A9 | LOW | 提交信息的复验行号与产物不符（一律差 6，方向仍成立） |
| A10 | MED | 父代理那条扫描**有假阴性**：我亲手做出绕过（扫描 NO-SUSPECT + 运行时 #300） |
| A11 | LOW | 全仓递归加强扫描 = 恰好 1 条（已知那条）；更强判据下"没有第二个同类"成立 |
| B1 | **HIGH** | B 的数字自洽，且能被真跑产生（junit 只读核对） |
| B2 | MED | `test_compliance::test_behavior_review_face_collection` 是**幽灵**，5 条其余白名单都真实存在 |
| B3 | MED | 幽灵**永远查不出来**：`-UpdateBaseline` 把白名单原样带过来，无判据校验其存在性 |

---

## A. `724b210` fix(P0·真凶): React #300 挂钩数不恒定=黑屏根因修

### A1（HIGH）冻结区间取错 —— A 不在这棵树里

冻结标签指的是 **B**（`4252385`），而 A（`724b210`）是它的**后代**：

```
$ git merge-base --is-ancestor HEAD 724b210 ; echo exit=$LASTEXITCODE
exit=0                      # HEAD 是 A 的祖先（A 不是 HEAD 的祖先）
$ git merge-base 724b210 HEAD
42523853ebc4eb61015b5ad05f19cbe07b03bdd7
$ git rev-list --count 4252385..724b210
3                           # 中间还有 303fcd1 / d23c4d7
$ git log --oneline --name-only 4252385..724b210
724b210 fix(P0·真凶): React #300 挂钩数不恒定=黑屏根因修（两个 useMemo 上移到所有早退之前）
plugin/client.js
plugin/client/KsKnowledgePage.tsx
d23c4d7 fix(P0·终案): 标签换页回到「页内四面」正统形态（ksSidebar 原案 :316 原文：二级页是同一 tab 的四个面）
plugin/client.js
plugin/client/KsKnowledgePage.tsx
303fcd1 fix(P0·三修): 三标签换页改走「打开」路（openTab 无 replaceTab）——业主线索「预览器能进」定的案
plugin/client.js
plugin/client/KsKnowledgePage.tsx
```

而且冻结树里的 `KsKnowledgePage.tsx` 与 **A 的父提交逐字节相同**（所以 A 的 diff 可无冲突套用，我也据此做了精确隔离）：

```
$ git rev-parse HEAD:plugin/client/KsKnowledgePage.tsx    # 8feb04ac984fb24e3c766809d407abbe06e92fa5
$ git rev-parse d23c4d7:plugin/client/KsKnowledgePage.tsx # 8feb04ac984fb24e3c766809d407abbe06e92fa5  ← 相同
$ git rev-parse 724b210:plugin/client/KsKnowledgePage.tsx # 3b0ccf62416d8f6ba9be98b731afbadafd77d3e6
```

**直接后果**：在**交付给我的冻结树**上跑父代理那条扫描，结果是 `SUSPECT`（不是它报的 `NO-SUSPECT`）：

```
$ node "%TEMP%\ks-hookscan.js" 'D:\AI\work space\zcode-verify-b6\plugin\client'
SUSPECT KsKnowledgePage.tsx  fn=KsKnowledgePage  firstReturn=L1797  hooksAfter=useMemo@1971,useMemo@2003
TOTAL-SUSPECTS 1
```

这一行与父代理对 `724b210~1` 报的那行**逐字相同** ⇒ 父代理的"扫当前 `plugin/client/*.tsx`（19 个文件）⇒ NO-SUSPECT"不可能是在这棵冻结树上得到的（它扫的是已含 A 的另一棵树）。**A 的任何结论都不能由冻结树的工作区文件直接背书**；本报告一律显式切换文件状态复验。

最小复现：
```
git -C 'D:\AI\work space\zcode-verify-b6' merge-base --is-ancestor HEAD 724b210; echo $LASTEXITCODE   # 0
node "%TEMP%\ks-hookscan.js" 'D:\AI\work space\zcode-verify-b6\plugin\client'                          # SUSPECT
```

### A2（HIGH）A 的修真有牙 —— 运行时、**双向**复现

单次渲染复现不出 #300（这一点我独立证实，见下"对照组"）。必须"同一实例第二次渲染"。**原脚本的 `--interact` 场景表里没有任何"切面"场景**，`--nav-page` 也根本不被读取，所以我自己造了切面探针。

探针：把 `plugin/scripts/ui-render-shot.mjs` 复制成一份，只加 `--face`（挂载后**真点**顶部标签 `.ks-tabfolder`）与 `--initial-face`（宿主打开 tab 时的 `params.page`），并加 `uncaughtException` / `console.error` 捕获。它不动原脚本、不改组件源码。探针文件（我在树里用完即删，副本留在临时目录）：
`%TEMP%\ks-b6-verify-p0\zz-b6-faceswitch.mjs`（sha256 `6D68DC0345C31B9137E4FC324E1C4BA7FD80D2D438CDBC3F4C8DB30DC4E24976`）

**改前（冻结树原状）**：

```
############ PRE-FIX  initial=manage  face=capabilities ############
B6-MOUNTED face-arg=capabilities tabs=[知识库|渠道库|办事台|预览器] active=[知识库]
Error: Minified React error #300; visit https://reactjs.org/docs/error-decoder.html?invariant=300 …
B6-AFTER-SWITCH active=[] nodes=0 capturedErrors=2
B6-ERR console.error: Error: Minified React error #300; …
B6-ERR uncaughtException: Minified React error #300; …
B6-VERDICT RED: React error after face switch
EXITCODE=1

############ PRE-FIX  initial=manage  face=channels ############
Error: Minified React error #300; …
B6-AFTER-SWITCH active=[] nodes=0 capturedErrors=2
B6-VERDICT RED: React error after face switch
EXITCODE=1

############ PRE-FIX  initial=materials  face=manage ############
Error: Minified React error #310; visit https://reactjs.org/docs/error-decoder.html?invariant=310 …
B6-AFTER-SWITCH active=[] nodes=0 capturedErrors=2
B6-VERDICT RED: React error after face switch
EXITCODE=1

############ PRE-FIX  initial=channels  face=manage ############
Error: Minified React error #310; …
B6-AFTER-SWITCH active=[] nodes=0 capturedErrors=2
B6-VERDICT RED: React error after face switch
EXITCODE=1
```

`nodes=0` = 整棵子树被卸载 —— 就是"面板崩=黑屏"的可量形态。**对照组**（证明"初次就渲染成早退面"抓不到）：

```
############ PRE-FIX  initial=capabilities  face=none ############
B6-NOSWITCH initial=capabilities nodes=42 capturedErrors=0
B6-VERDICT GREEN-NOSWITCH: single render, no error (this proves NOTHING about #300)
EXITCODE=0
```

**改后（套用 A 的 blob `3b0ccf62…`）—— 5/5 全绿**：

```
############ WITH A(724b210)  initial=manage      face=capabilities ############
B6-AFTER-SWITCH active=[] nodes=42 capturedErrors=0   → GREEN  EXITCODE=0
############ WITH A(724b210)  initial=manage      face=channels      ############
B6-AFTER-SWITCH active=[渠道库] nodes=50 capturedErrors=0   → GREEN  EXITCODE=0
############ WITH A(724b210)  initial=materials   face=manage        ############
B6-AFTER-SWITCH active=[知识库] nodes=222 capturedErrors=0  → GREEN  EXITCODE=0
############ WITH A(724b210)  initial=channels    face=manage        ############
B6-AFTER-SWITCH active=[知识库] nodes=222 capturedErrors=0  → GREEN  EXITCODE=0
############ WITH A(724b210)  initial=ingest      face=channels      ############
B6-AFTER-SWITCH active=[渠道库] nodes=50 capturedErrors=0   → GREEN  EXITCODE=0
############ WITH A(724b210)  initial=capabilities face=none         ############
B6-NOSWITCH initial=capabilities nodes=42 capturedErrors=0  → GREEN  EXITCODE=0
```

最小复现（**改动前**必须先在树里放好探针）：
```
$d = "$env:TEMP\ks-b6-verify-p0"
Copy-Item $d\zz-b6-faceswitch.mjs 'D:\AI\work space\zcode-verify-b6\plugin\scripts\'
cd 'D:\AI\work space\zcode-verify-b6'
node plugin/scripts/zz-b6-faceswitch.mjs --page kb --initial-face manage --face capabilities --width 1280 --out "$d\x.png"
# 冻结原状 ⇒ B6-VERDICT RED / exit 1；套用 git restore --source=724b210 --worktree -- plugin/client/KsKnowledgePage.tsx ⇒ GREEN / exit 0
```

### A3（HIGH）A 的修是**完整**的（不是只堵一半）

- 运行时：上表 5 条**可达**切面路径全绿（含 #300 方向两条、#310 方向两条、ingest 方向一条）。**若早退之后还留着别的挂钩，改后仍会红** —— 没红 ⇒ 就是这么两条。
- 静态：我写了加强版扫描器（下 A11），递归全树、解析别名。A 版本 ⇒ `NO-SUSPECT`。
- 顺序零扰动：改前 1796–1970 区间**没有任何挂钩调用**，所以"上移"没有跨过其它挂钩，知识库面上的挂钩序列逐位不变：

```
$ Select-String -Path plugin\client\KsKnowledgePage.tsx -Pattern '(^|[^A-Za-z0-9_$.])use(State|Memo|Effect|Callback|Ref|Reducer|Context)\s*[(<]' |
    Where-Object { $_.LineNumber -ge 1796 -and $_.LineNumber -le 1970 }
（空 = 该区间无挂钩）
```
- 位置核对（**以提交 blob 为准**，不是以工作区文本）：

```
$ git grep -n -E "const inboxShown|const pickBase|if \(page === 'capabilities'\)" 724b210 -- plugin/client/KsKnowledgePage.tsx
724b210:plugin/client/KsKnowledgePage.tsx:1805:  const inboxShown = useMemo(() => {
724b210:plugin/client/KsKnowledgePage.tsx:1818:  const pickBase = useMemo(() => {
724b210:plugin/client/KsKnowledgePage.tsx:1830:  if (page === 'capabilities') {
```

### A4（HIGH）A 的 `client.js` 是真重建 —— 这份修**真的会上线**

`plugin/client.js` 是宿主真正加载的产物；源码改了而产物陈旧 = 修没上线。用 `KS_CLIENT_OUT` 构建到临时路径（**不覆盖被跟踪的 `client.js`**），两侧各验一次：

```
=== build #1: FROZEN (pre-fix) source -> temp ===
client.js written: 1710452 bytes (1707103 chars)
built(pre-fix) = d598400835a8bd8f2bb49c38b697db7b2edd3c06
committed HEAD = d598400835a8bd8f2bb49c38b697db7b2edd3c06     MATCH = True

=== apply A's source, build #2 ===
client.js written: 1710452 bytes (1707103 chars)
built(from A source) = 6d6ce4461c8de985a4d147d45a9163c279a7ab16
committed A client.js = 6d6ce4461c8de985a4d147d45a9163c279a7ab16  MATCH = True
```

第一跑是**程序自身的对照**（现构建 == 冻结提交产物）⇒ 构建环境可信；第二跑才是结论。两侧字节数同为 1710452、只有 blob 不同 ⇒ 与"纯搬位置、不增删代码"一致。

最小复现：
```
cd 'D:\AI\work space\zcode-verify-b6'
$env:KS_CLIENT_OUT = "$env:TEMP\ks-b6-verify-p0\b.js"; node plugin/scripts/build-client.mjs
git hash-object "$env:TEMP\ks-b6-verify-p0\b.js"; git rev-parse 724b210:plugin/client.js
```
（⚠ 这是本树 `plugin/node_modules` 为**真拷贝**才能成立的判据；junction 会让路径写进产物。）

### A5（HIGH）父代理的证据命令是**空闸门**

任务书引用的命令 `--page kb --nav-page capabilities --width 1280` 在脚本里**没有对应参数**，`arg()` 只找它明确问的名字，未知参数既不报错也不生效：

```
$ Select-String -Path plugin\scripts\ui-render-shot.mjs -Pattern "nav-page|arg\('nav"
（无输出 = 这个参数从未被读取）
```

在**有 bug 的冻结树上**跑父代理那条**原命令**：

```
$ node plugin/scripts/ui-render-shot.mjs --page kb --nav-page capabilities --width 1280 --out "$d\parent-cmd.png"
… "renderedChars": 34230, "browser": "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
· #kbtree/#levelrows 自检通过：左列右缘 204px ≤ 右栏左缘 212px…
· #dircols 自检通过：目录层 4 轨 "32px 860px 64px 28px"，铺满容器 1008px…
· #kspad 自检通过：宽档（页面根宽 1256px）留边 24px…
EXITCODE=0
```

注意输出里的 `comboKey=kb|` 与全部自检的 `page=kb`：**它从未离开 `manage` 面**。⇒ 父代理"跑通、png 生成、**没有** React 报错"是真的，但**不能**作为 A 的证据（空闸门恒绿）。这也解释了为什么它"实测可跑"却仍漏掉 #300。

### A6（MED）方向被说错：#310 不是 #300

| 切面路径 | 改前错误 | 机制 |
|---|---|---|
| 知识库 → 渠道库 | **#300** | 78 → 76（挂钩变少）|
| 知识库 → 办事台 | **#300** | 78 → 76 |
| 备料 → 知识库 | **#310** | 76 → 78（挂钩变多）|
| 渠道库 → 知识库 | **#310** | 76 → 78 |

提交信息只写了"78→76 ⇒ #300"，覆盖不到"从早退面进知识库"那一半（业主日志是 #300，与知识库→渠道库/办事台相符，所以**结论不受影响**，但机理描述不完整）。

### A7（MED）观测：面与标签条的可达性

```
PRE-FIX initial=capabilities face=manage  → tabs=[]  active=[]      ⇒ 页内标签条不存在，切不出去
PRE-FIX initial=manage      face=materials→ tabs=[知识库|渠道库|办事台|预览器] ⇒ 没有「备料」按钮
WITH-A  initial=materials   face=manage   → tabs=[知识库|渠道库|办事台|预览器] active=[]  （备料不是标签项）
```

- **备料面**只能由宿主以 `params.page='materials'` 打开（页内标签表 `KsKnowledgePage.tsx:217-222` 只有 知识库/渠道库/办事台/预览器）；所以"切到备料"这条路**不存在**，而"以备料打开后再切走"存在（这就是 #310 那条）。
- **办事台面**（`KsKnowledgePage.tsx:1796-1798`）返回 `<KsCapabilityPage />`，**自身不带标签条** ⇒ 从办事台无法用页内标签回知识库。
- ⚠ 范围声明：我只测了**页内**标签条。宿主侧（sidebar / tab 标题栏）有没有别的入口我没测，**不做结论**。

### A8（MED）副作用 = 无（父代理未验的那一半）

两个 useMemo 上移后，在 `capabilities`/`channels`/`materials` 三个面上**确实会执行**（改前这些面早退、根本不执行）。我把这点从"假设"变成证据：以 A 的文件为底，往 `inboxShown` 工厂第一行注入 `throw`：

```
--- WITH-A + throwing inboxShown factory, initial-face=materials (single render, no switch) ---
Error: B6-EXEC-PROBE: inboxShown factory ran on this face
B6-NOSWITCH initial=materials nodes=0 capturedErrors=1
B6-VERDICT RED-NOSWITCH            EXITCODE=1
--- initial-face=channels ---   Error: B6-EXEC-PROBE…  B6-VERDICT RED-NOSWITCH  EXITCODE=1
--- initial-face=capabilities --- Error: B6-EXEC-PROBE…  B6-VERDICT RED-NOSWITCH  EXITCODE=1
```

⇒ **前提成立**（三个面上真的执行了）。它**无害**，逐条判：

| | 工厂读什么 | 在这些面上的取值 | 会不会抛/算错 |
|---|---|---|---|
| `inboxShown` (A:1805-1813) | `inbox`(state,495)、`needle`(派生自 `search`,1559) | `[]`、`''`（`needle===''` 时直接 `return inbox`） | 纯函数；无 I/O、无副作用 ⇒ 否 |
| `pickBase` (A:1818-1829) | `action`(state,517)、`flatFolders`(state,532)、`folderIdsOf`(模块级,346) | `null` → `action?.targets ?? []` = `[]`；`[]` → 循环空转、`filter` 返回 `[]` | 纯函数 ⇒ 否 |

- **无 TDZ**：四个输入（`inbox` 495 / `action` 517 / `flatFolders` 532 / `needle` 1559）都声明在 1805 **之前**；`folderIdsOf` 是模块级 `KsKnowledgePage.tsx:346`。
- **无错值可见**：这三个面上返回值**根本不被消费**（早退在所有使用点之前）。
- **渲染对照**（同一探针，四个面各自单次渲染，改前 vs 改后）：

```
PRE-FIX capabilities -> nodes=42   |  WITH-A capabilities -> nodes=42
PRE-FIX channels     -> nodes=50   |  WITH-A channels     -> nodes=50
PRE-FIX materials    -> nodes=29   |  WITH-A materials    -> nodes=29
PRE-FIX ingest       -> nodes=179  |  WITH-A ingest       -> nodes=179
（四组两侧节点数相同、capturedErrors 全 0）
```

### A9（LOW）提交信息的复验行号与产物不符

信息写"grep 复验：inboxShown(:1811)/pickBase(:1824) 均在早退(:1836)之前"；提交 blob 实际是 **1805 / 1818 / 1830**（一律差 6）。"都在早退之前"这个**结论**成立，数字不成立。

### A10（MED）父代理那条扫描**有假阴性** —— 我亲手跑出绕过

`%TEMP%\ks-hookscan.js` 的判据是：把被调函数的**名字**拿去比 `/^use[A-Z]/`。因此**别名调用**结构上看不见。以 A 的**已修**文件为底，加两行：

```
L77  : const _b6h = useMemo                                  // 模块级别名
L1896: const _b6bypass = _b6h(() => 1, [])                   // 在所有早退**之后**（只有知识库路走到）
```

**同一个文件**，静态判据与运行时判据给出相反答案：

```
$ node "%TEMP%\ks-hookscan.js" "$d\bypassdir"
NO-SUSPECT                                   ← 单一文件
$ node "%TEMP%\ks-hookscan.js" 'D:\AI\work space\zcode-verify-b6\plugin\client'
NO-SUSPECT                                   ← 全目录（工具的真实用法）

$ node plugin/scripts/zz-b6-faceswitch.mjs --page kb --initial-face manage --face channels …
B6-MOUNTED … active=[知识库]
Error: Minified React error #300; …invariant=300…
B6-AFTER-SWITCH active=[] nodes=0 capturedErrors=2
B6-VERDICT RED: React error after face switch
EXITCODE=1
```

（React 按 dispatcher 调用计数，不看名字；别名 `_b6h` 照样算一次挂钩 ⇒ 79 vs 78。）其余**结构上看不见**的形态（同类，未逐一跑）：

- `const { useMemo: um } = React; um(...)`（同一类别名，我的加强版已堵）
- **调用一个内部含挂钩的本地助手**（`helperHidden()` 里 `useMemo(...)`）—— 它不下钻子函数，看不见
- 只读 `.tsx` 且**非递归**：`plugin/client` 有 **12 个 `.ts`** 从不被扫；今天全仓 `.tsx` 恰好只在这一个目录（19 个），所以这一条**暂时不咬人**（我 grep 过 `.ts`，里面没有挂钩调用）
- `if (cond) { useMemo(...) }`（在第一个 `return` **之前**的条件挂钩）：不是"return 之后"⇒ 不判。这是**另一族** #300 机理，两个扫描器都不管（我**没有**为它扫，明确未做）

⇒ 父代理"这条判据有牙"只能算**半真**：它**确实**命中了那唯一一处真缺陷（A1 里那行），但**不 sound** —— 它能对一份真会黑屏的文件说 `NO-SUSPECT`。**"全仓没有第二个同类"这个结论，不能用这条判据来背书。**

### A11（LOW）加强版判据下，"没有第二个同类"成立

我另写了 `%TEMP%\ks-b6-verify-p0\hookscan2.js`：① 解析 `import { useMemo as um } from 'react'` 别名；② 解析 `const um = useMemo` / `const {useMemo: um} = React`（不动点）；③ 把"调用一个内部含挂钩的本地函数"也算挂钩点（3 轮不动点）；④ **递归**遍历全树每个 `.tsx`。它对自己造的绕过文件报 `SUSPECT`（自检有效）：

```
$ node hookscan2.js "$d\bypassdir"
SUSPECT KsKnowledgePage.tsx  fn=KsKnowledgePage  firstReturn=L1832  hooksAfter=_b6h@1896
TOTAL-SUSPECTS 1

$ node hookscan2.js 'D:\AI\work space\zcode-verify-b6'          # 冻结全树、递归
SUSPECT plugin\client\KsKnowledgePage.tsx  fn=KsKnowledgePage  firstReturn=L1797  hooksAfter=useMemo@1971,useMemo@2003
TOTAL-SUSPECTS 1

$ node hookscan2.js "$d\overlay-A"                              # 19 个 .tsx 的 overlay，只把 KsKnowledgePage.tsx 换成 A 的
NO-SUSPECT
```

⇒ 全仓**恰好一条**同类形态，A 把它清成 0。⚠ 范围：这是**静态**判据（且刻意过近似）；不改条件挂钩那一族。

---

## B. `4252385` chore(④): 棘轮基线记新

### B1（HIGH）三个数字自洽，且**能由真跑产生**

`scripts/gates-baseline.json`：

```
1 {
2   "pytest_total": 2333,
3   "pytest_skipped": 3,
…
18   "pytest_passed": 2330,
```

- 自洽：`2330 + 3 = 2333` ✓；与 `scripts/run-gates.ps1:333` 的口径一致（`totalRan = passed + skipped + failed + errors`，此处 failed/errors = 0）。
- 只读核对最近一次真跑的 junit（**未改、未删**）：

```
$ %TEMP%\ks-gates-junit-9088.xml   Length=297540   LastWriteTime=2026/9/24 1:01:15
<testsuite name="pytest" errors="0" failures="0" skipped="3" tests="2333" time="224.985"
           timestamp="2026-09-24T00:57:30.101927+08:00" hostname="DESKTOP-U18P3CQ">
testcase count=2333   skipped count=3   failure count=0   error count=0
--- skipped nodeids ---
tests.test_golden_set::test_qa_retrieval_hits_golden
tests.test_reranker::test_rerank_real_model_reorders
tests.test_update_channels::test_live_openstd_homepage_default_transport_200
```

**三条 skipped 与基线 `skip_nodeids`（第 13-15 行）逐字相同** —— 这一栏是 `-UpdateBaseline` 从跑结果现生成（`run-gates.ps1:326-327`、`380-381`），手写不出来 ⇒ 数字是机器产的。

⚠ 边界：该 junit 的 `timestamp`（2026-09-24 00:57）**晚于** B 提交（2026-09-23 19:18）。它证明"这组数字真跑得到、且与现实一致"，**不证明**"B 那次 `-UpdateBaseline` 跑的就是这一份"。我没有重跑 pytest（明确未做，见末节）。

### B2（MED）白名单里有一条**幽灵**

```
$ Test-Path tests\test_compliance.py
False
$ git ls-files tests | Select-String compliance
（空）
$ git log --oneline --diff-filter=D -- tests/test_compliance.py
683c6f6 refactor(删单C3-后端): 三模块七路由下架 + 测试对账 + 金标评测台连带损失登记（NOT-DOING #16）
$ git merge-base --is-ancestor 683c6f6 HEAD; echo exit=$LASTEXITCODE
exit=0                                   # 删除已在冻结 HEAD 之前
$ git rev-list --count 683c6f6..HEAD
42                                       # 距冻结 HEAD 42 个提交 ⇒ B 提交时它早已不存在
$ git grep -n 'def test_behavior_review_face_collection'
（全仓 0 命中）
```

⇒ `scripts/gates-baseline.json:5` 的 `tests.test_compliance::test_behavior_review_face_collection` 是**幽灵**（父代理说法成立）。其余逐条核过，**都真实存在**：

```
OK   test_qa_retrieval_hits_golden -> tests/test_golden_set.py:23
OK   test_rerank_real_model_reorders -> tests/test_reranker.py:65
OK   test_live_openstd_homepage_default_transport_200 -> tests/test_update_channels.py:415
OK   test_real_middle_json_integration -> tests/test_pipeline.py:221
OK   test_vec_channel -> tests/test_retrieval.py:306
GHOST test_behavior_review_face_collection -> def not found in any tracked file
```

（5 条 real + 1 条 ghost = 6 条 `environmental_skip_nodeids`；3 条 `skip_nodeids` 全 real。）

### B3（MED）幽灵**永远查不出来**（判据洞，不是当轮假绿）

`scripts/run-gates.ps1:376-388` 在 `-UpdateBaseline` 时把环境白名单**原样搬进新基线**：

```
382:  environmental_skip_nodeids = $(if ($null -ne $base -and $base.environmental_skip_nodeids) {
383:      @($base.environmental_skip_nodeids) } else { @() })
```

它**从不重算**，而 `346-351` 只把它当"允许出现的 skip"用来**排除**报红：

```
346:  $envIds = @($base.environmental_skip_nodeids)
348:  $newIds = @($skipNodeIds | Where-Object { $knownIds -notcontains $_ -and $envIds -notcontains $_ })
```

⇒ ① 白名单只增不减、**没有任何判据校验某个 nodeid 是否还存在**（这就是幽灵能躺 42+ 个提交的原因，且与 B5「白名单只增不减」叠加会永久固化）；② 幽灵的方向只会**放宽**、不会误红，所以**今天是低危的潜在洞**，不是当前假绿：真正危险的是将来若有同 nodeid 的用例开始被 skip，它会被这条幽灵静默放行。

---

## 我明确**没能**验证的

1. **我没有自己跑 pytest**（禁止跑 `run-gates.ps1` / `smoke-all.mjs`；也未单独跑 `pytest`）。2333/2330/3 我是**只读**一份真 junit 核的，不是我自己跑出来的 ⇒ "这三个数可由一次真跑产生"成立；"B 提交那一次跑就是这一份"**未验证**。
2. **2317 → 2333 那 +16 的来源未核**（旧基线 `2314/2317` vs 新 `2330/2333`，差 16 条 passed）。我没去数这 16 条是哪些提交加的。
3. **条件挂钩族未扫**：`if (cond) { useMemo(...) }`（在第一个 return 之前）是另一族挂钩数不恒定，两个扫描器都不判，我**没有**为它写判据、也没有全仓排查。
4. **静态扫描器的完备性我没有证明**。我堵了别名与"本地含挂钩助手"两类，并**实测**了别名那一类的绕过；但"是否还有第三类绕过"我**没有**证明（我给的加强版是**更**有牙，不是**不可**绕过 —— 例如挂钩经对象属性间接调用、经 `.bind`、经动态 `require` 取名，都在它的视野之外，我未逐一实测）。
5. **宿主侧真实行为未测**。所有运行时证据都是 jsdom + 真 esbuild 产物 + 脚本的 fetch 桩；我的切面探针**在切面后立即退出**（不进真浏览器截图阶段），所以切面这些跑**没有 png**，判据是退出码 + React 原始报错文本（这是**有意**的：png 证明不了挂钩数）。真机、真宿主槽位（`sidebar.right.pane.tab`）崩溃**未复现**，只复现了同族错误码。A7 的面可达性也只覆盖**页内**标签条。
6. **`#300` 的"全死"（黑后全死）未验证** —— 我只观察到该面板子树被卸载（`nodes=0`）。
7. 未跑 `smoke-client-entry.mjs`；我用手工"现构建 ↔ 提交产物"逐字节比对**等价替代**（A4），但那不是那条门禁本身。

## 父代理的说法被**推翻 / 需要修正**的地方

| 父代理说法 | 实测 | 判定 |
|---|---|---|
| "扫当前 `plugin/client/*.tsx`（19 个文件）⇒ `NO-SUSPECT`" | 在**交付的冻结树**上同一条命令 ⇒ `SUSPECT … firstReturn=L1797 hooksAfter=useMemo@1971,useMemo@2003` | **推翻**（它扫的不是这棵树；冻结标签指向 B，A 在后 3 个提交）|
| "`node ui-render-shot.mjs --page kb --nav-page capabilities …` 实测可跑 ⇒ 没有 React 报错" | 脚本**不读** `--nav-page`；在**有 bug 的**树上跑同一条命令 ⇒ `EXITCODE=0` 全绿（`comboKey=kb|`，从未离开 manage 面） | **推翻其证据力**（空闸门恒绿；观测本身为真但无意义）|
| "这条判据有牙" | 命中真缺陷为真；但我用同一判据对一份**真会黑屏**的文件（别名挂钩，`_b6h@1896`）得到 `NO-SUSPECT` | **半真 → 需修正为"能命中已知那一处，但不 sound，不能用它下'全仓没有第二个'的结论"** |
| "全仓没有第二个同类" | 用加强版判据（别名 + 本地含挂钩助手 + 递归全树）复核 ⇒ 恰好 1 条，A 清成 0 | **结论成立，依据换成加强判据**（原依据不成立）|
| "挂钩 78→76 ⇒ #300" | 78→76 确是 #300，但"切备料"到不了（无该标签）；反向（早退面→知识库）是 **76→78 ⇒ #310** | **需补正**（结论不受影响）|
| "两个 useMemo 上移到早退(:1836)之前，:1811/:1824" | 提交 blob 是 **1805 / 1818 / 1830**（一律差 6） | **数字需更正**（方向正确）|
| （未提）改后非知识库面也会执行这两个 useMemo | 我注入 throw 证实**确实执行**；纯函数、输入都是更早的 state、四面对照节点数相同 ⇒ **无害** | **补验通过** |
| （未提）`client.js` 是否真重建 | 双向逐字节复现：`6d6ce446…` == A 提交的 `client.js` | **补验通过（P0 关键项）** |

## 冻结树状态（尾）

```
$ git rev-parse HEAD
42523853ebc4eb61015b5ad05f19cbe07b03bdd7
$ git status --short
（空 —— 干净）
```

本树内我动过的文件**全部还原**（判据用 `git status --short`，不用哈希：本机 `core.autocrlf=true`）。逐次还原的 blob 复核：

- `git restore --source=724b210 --worktree -- plugin/client/KsKnowledgePage.tsx` —— 套用 A（共 3 次：A 复验 / client.js 现构建对照 / 四面渲染对照）
- 另 2 次是**直接写盘**的变异（别名绕过、执行探针），之后各 `git restore --worktree -- plugin/client/KsKnowledgePage.tsx` 还原
- 收工态：`git hash-object plugin/client/KsKnowledgePage.tsx` = `8feb04ac984fb24e3c766809d407abbe06e92fa5`（= 冻结原状）+ `git status --short` 空
- `plugin/client.js` **从未被改写**（`KS_CLIENT_OUT` 写到临时目录）

我建的东西与清理（只删自己刚建的那份）：

- 树内一次性探针 `plugin/scripts/zz-b6-faceswitch.mjs` —— **已删**；副本存 `%TEMP%\ks-b6-verify-p0\zz-b6-faceswitch.mjs`（sha256 `6D68DC0345C31B9137E4FC324E1C4BA7FD80D2D438CDBC3F4C8DB30DC4E24976`）
- 其余全在 `%TEMP%\ks-b6-verify-p0\`（我自己建的目录）：`patch.py`、`mutate_bypass.py`、`mutate_execprobe.py`、`hookscan2.js`、`bypassdir\`、`overlay-A\`、`matrix-prefix.txt`、`matrix-postfix.txt`、`sidenodes.txt`、若干 png
- **更早的 `%TEMP%` 目录一个都没动**（`ks-hookscan.js`、`ks-gates-junit-9088.xml` 均只读）
