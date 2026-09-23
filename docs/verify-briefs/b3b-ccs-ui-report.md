# 独立复核报告 —— B3b「补全分类号」的**界面半边**

- 冻结工作树：`D:\AI\work space\zcode-verify-b3b`（HEAD = `dec2cd4` = tag `verify-freeze-b3b`）
- 被验批次：`2d10e6c` + `f9116d3` + `aaad270`（base `12cb6b0`；`git rev-list --count 12cb6b0..aaad270` = **3**，
  实跑核过；`git merge-base --is-ancestor 12cb6b0 aaad270` ⇒ exit 0）
- 复核身份：**独立复核**。实施报告 `B3B-REPORT.md` 与父代理总结一律当**待核的说法**。

## 0. 首尾取证

**开工时**（本报告第一条命令）：

```
$ git -C "D:\AI\work space\zcode-verify-b3b" rev-parse HEAD
dec2cd4bfce5d87e7487da5cd7ad4e246790795b

$ git -C "D:\AI\work space\zcode-verify-b3b" status --short
?? VERIFY-REPORT-b1b2.md
```

**收尾时**（见 §7，报告落盘后补记）。

## 1. 总判定

**PASS-with-gaps**。

计数：**PASS 17 / FAIL 0 / UNVERIFIED 3**（逐条判定见 §3）；严重度 **HIGH 0 / MED 2 / LOW 3**。

- 12 条判据 N21–N32 **全部有牙**：我逐条造了真实的坏，**逐条都当场变红**，红的原文抄在 §4。
- 4 条"桩可控 + 反向"判据（N26/N28/N29/N31）**不是自己验自己**：机械反例见 §5.1。
- `--ccs` 开关确实是**纯加法且默认关**：字节级证明见 §5.3。
- 交付件 `plugin/client.js` 里**确有** B3b 的界面原文，"整份一致"是真**逐字符**比对：见 §5.2。
- **没找到假绿**（没有一条判据是恒真/放宽到失效的）。
- 2 条 MED 都是**覆盖缺口**（不是判据恒真）：见 §3 的 U1、U2 与 §6。

## 2. 我改了又还原的清单（全部用 `git status --short` 证明，**不用哈希**）

变异前先跑过一次 `git status --short`：`KsKnowledgePage.tsx` / `api.ts` 当时**都是干净的**
（输出只有 `?? VERIFY-REPORT-b1b2.md`），所以 `git checkout --` 不会吃掉未提交的改动。

| # | 变异文件（绝对路径） | 还原命令 | 还原后 `git status --short` |
|---|---|---|---|
| M1 | `D:\AI\work space\zcode-verify-b3b\plugin\client\KsKnowledgePage.tsx` | `git -C "D:\AI\work space\zcode-verify-b3b" checkout -- "D:\AI\work space\zcode-verify-b3b\plugin\client\KsKnowledgePage.tsx"` | `?? VERIFY-REPORT-b1b2.md` + `?? plugin/scripts/probe-ccs-tmp.mjs`（当时探针还在） |
| M2–M3 | 同上 | 同上 | `?? VERIFY-REPORT-b1b2.md` / `?? plugin/scripts/probe-ccs-tmp.mjs` |
| M4 | `...\plugin\client\api.ts` | `git -C "..." checkout -- "...\plugin\client\api.ts"` | 同上 |
| M5–M12 | `...\plugin\client\KsKnowledgePage.tsx` | 同 M1 | 同上 |

收尾时（探针文件已删）：

```
$ git -C "D:\AI\work space\zcode-verify-b3b" status --short
?? VERIFY-REPORT-b1b2.md
```

⇒ **12 次变异全部还原干净**，工作树与 `dec2cd4` 一致（只剩两个未跟踪文件：上一轮的
`VERIFY-REPORT-b1b2.md`（任务书要求别动）与本报告）。

我**新建又删掉**的临时文件（都在冻结树内，已清）：
`plugin\scripts\probe-ccs-tmp.mjs`（带探针的冒烟副本）、`plugin\scripts\probe-base-smoke-tmp.mjs`
（base 版冒烟副本）、`plugin\scripts\base12cb6b-ui-render-shot.mjs`（base 版截图脚本副本）；
截图/HTML 产物在 `var\tmp\b3b-shots\`（未跟踪，留在树里）。**主仓只写了报告第二落点**，
代码一个字节没动。

## 3. 逐条判定

| # | 要核的说法 | 判定 | 严重度 |
|---|---|---|---|
| C1 | 界面接线：N21–N32 这 12 条判据真的钉住了六条界面要求 | PASS | — |
| C2 | N21–N32 **逐条有牙**（改坏就红） | PASS | — |
| C3 | N26/N28/N29/N31 的"桩可控"不是自己验自己 | PASS | — |
| C4 | 交付件 `plugin/client.js` 里有 B3b 界面原文 | PASS | — |
| C5 | `smoke-client-entry` 的"交付件 == 从源码现构建"比的是**整份** | PASS | — |
| C6 | `--ccs` 是纯加法、默认关；不加开关行为不变 | PASS | — |
| C7 | `--ccs` 参数非法时干净报错，不静默降级 | PASS | — |
| C8 | 桩的字段名/取值与**引擎真代码**一致（不是照抄界面假设） | PASS | — |
| C9 | `B3B-REPORT.md` §2 的真跑数字（185/185、190/190） | PASS（数字细节更正，见下） | LOW |
| C10 | `B3B-REPORT.md` §3 的两条变异自证 | PASS（我复现了同族的更强变异） | — |
| C11 | `B3B-REPORT.md` §4 的四张截图 + `#listcap` 几何自检 | PASS | — |
| C12 | `B3B-REPORT.md` §6 tsc 干净（exit 0） | PASS | — |
| C13 | `B3B-REPORT.md` §1 引用的提交 id（`d35d1ca`/`8515ade`） | PASS（可溯源，但提醒：不在 master 历史） | LOW |
| U1 | `hard_capped=true` 那一支文案（"到一次最多能补的那条线就停"）**无真跑覆盖** | UNVERIFIED | MED |
| U2 | `pages > 1` 那句（"分 N 页串行跑"）**无真跑覆盖**（报告自己已登记） | UNVERIFIED | LOW |
| U3 | pytest 侧（引擎半边、五桶恒等式）**这棵树没有 `.venv` ⇒ 跑不了** | UNVERIFIED | MED |
| F1 | （顺手发现，**不属本批**）`befc595` 新增的 `.ks-list-cap` 源码文本判据偏弱 | FAIL（非本批） | LOW |

### C9 的数字更正（就地对账，不静默）

`B3B-REPORT.md` §2 写 `== kb-page-render smoke PASS (185/185) ==`。在**冻结树**上实跑是：

```
== kb-page-render smoke PASS (186/186) ==
```

差的 1 条来自**更晚的** `befc595`（不属被验的 3 笔）：它在最前面新增了一条
`B2·抓手仍在：…类名 ks-list-cap 必须还在`。静态 `check(` 计数实核（行首匹配）：

| 版本 | 静态 `check(` | 实跑 |
|---|---|---|
| base `12cb6b0` | 173 | `== kb-page-render smoke PASS (173/173) ==`（实跑） |
| B3b `aaad270` | 185 | 未单独实跑（= 173 + 12，与报告 185 一致） |
| 冻结 `dec2cd4` | 186 | `== kb-page-render smoke PASS (186/186) ==`（实跑） |

⇒ **B3b 恰好新增 12 条**（与"12 条新判据 N21–N32"相符），报告的 185/185 与 190/190
都是它自己那棵树上的数，**不算错**，此处只是标出冻结树是 186。

## 4. 逐条变异（12 次，覆盖 N21–N32 全部 12 条；任务书要求 ≥6，含 N26/N28/N29/N31）

判据分两条命令跑，一次一个变异，跑完立即 `git checkout --` 还原。
原始输出**逐字抄**（只做换行折行的排版，不改字）。

### M1 → N26（+N27）｜把"为什么停"里 `hard_cap` 那句话**写死**

```
$ node plugin/scripts/smoke-kb-page-render.mjs
FAIL  N26 **反向**：同一个停因（hard_cap）后端换了说法，界面跟着变（新句在场、**旧句不在场**）⇒ 原因文案来自后端注入的 label，不是界面自己推断/写死的 — 新句「为什么停：到了硬上限就停（还剩没补的，不是补完了）」/ 旧的 hard_cap 说法「到了硬上限就停（还剩没补的，不是补完了）」还在场=true（第一跑时同一行的位置上是「为什么停：到了这一批的量就停（剩下的下次再补）」）
FAIL  N27 撞硬上限时**不假装补完了**：照念后端的 `hard_cap` 说法（第一跑的收尾消息里同时说清"现在还剩多少"，数字 = 后端现算的 `missing`） — 停因「为什么停：到了硬上限就停（还剩没补的，不是补完了）」/ 第一跑消息里含"现在库里还缺 1 篇"=true
== kb-page-render smoke FAIL (184/186) ==
```
判定：**N26 真有牙**（红在两处：新句不是桩给的那句、旧句还在场）。

### M2 → N28｜批大小/硬上限数字**写死成 50/200/2000**（等于第一跑桩值）

```
FAIL  N28 批大小与硬上限的**数字**也来自后端：换成 41 / 137 / 777（且还缺 900 篇 > 上限 777）之后，界面那两句跟着变（写死 50/200/2000 会红） — 含「一次默认补 41 篇」=false / 含「最多 137 篇」=false / 含「这次会补 777 篇」=false / 含「一次最多补 777 篇」=false
== kb-page-render smoke FAIL (185/186) ==
```

### M3 → N29｜层名**写死成旧的三层**

```
FAIL  N29 按钮提示里的"哪几层"直接用后端下发的 `sources` + `source_labels` 拼（换掉层名跟着变；以前界面写死三层、而后端是四项） — title「插件自己按「官方接口 → 网页抓取 → 本地对照表」逐篇查缺的分类号（全库还缺 900 篇；一次最多补 137 篇；一篇一到几秒，后台跑）」
== kb-page-render smoke FAIL (185/186) ==
```

### M4 → N31｜把请求体里的 `all:true` 去掉（`api.ts`）

```
FAIL  N31 点「全部补完」⇒ 真的发 `POST /kb/ccs/backfill` 且请求体带 `"all":true`（与上面那个"补一批"的按钮是两件事） — POST body={}
== kb-page-render smoke FAIL (185/186) ==
```
（红的原文就写着 `POST body={}` —— 是**真请求体**，不是回显常量。）

### M5 → N21｜永不显示后端给的回退路径（只在"读不到"那一支）

```
FAIL  N21 补之前那份**回退记录**的路径如实显示（`.ks-ccs-undo`＝「已存回退记录：<路径>」，路径就是后端给的那条 —— 不许编一句"已自动备份"糊过去） — .ks-ccs-undo 1 个 / 文字「已存回退记录：读不到（接口没给路径）」
== kb-page-render smoke FAIL (185/186) ==
```

### M6 → N22｜五桶合并成一句"部分失败"

```
FAIL  N22 「还剩多少」**拆开**成五桶逐桶显示（从没查过 17 / 查过没查到 11 / 查过失败 7 / 不适用 4 / 台账说补到了却没标签 3，和 = 42）—— 合并成一句"部分失败"就必然对不上 — 状态行：「还剩 42 篇没补：部分失败 7 篇。」
== kb-page-render smoke FAIL (185/186) ==
```

### M7 → N23（+N26/N27）｜界面**自己编**"为什么停"

```
FAIL  N23 「为什么停」＝后端下发的那句（`.ks-ccs-stop` 上就是桩给 `limit` 的那句话） — 「为什么停：树里没有对应的那一层（界面自己推断的原因）」
FAIL  N26 **反向**：同一个停因（hard_cap）后端换了说法，界面跟着变（新句在场、**旧句不在场**）⇒ 原因文案来自后端注入的 label，不是界面自己推断/写死的 — 新句「为什么停：树里没有对应的那一层（界面自己推断的原因）」/ 旧的 hard_cap 说法「到了硬上限就停（还剩没补的，不是补完了）」还在场=false（第一跑时同一行的位置上是「为什么停：树里没有对应的那一层（界面自己推断的原因）」）
FAIL  N27 撞硬上限时**不假装补完了**：照念后端的 `hard_cap` 说法（第一跑的收尾消息里同时说清"现在还剩多少"，数字 = 后端现算的 `missing`） — 停因「为什么停：树里没有对应的那一层（界面自己推断的原因）」/ 第一跑消息里含"现在库里还缺 1 篇"=true
== kb-page-render smoke FAIL (183/186) ==
```

### M8 → N24｜去掉"再按一次接着补"那句

```
FAIL  N24 状态行写清「再按一次接着补」+ 一次默认几篇/最多几篇（数字来自后端 50 / 200） — 状态行：「补全分类号：已跑 2 / 2 篇 · 补到 1 篇（其中新写标签 1 篇） · 查无 1 篇 · 查询失败 0 篇 · 读不出来 0 篇 · 不适用 0 篇为什么停：到了这一批的量就停（剩下的下次再补）还剩 42 篇没补：从没查过 17 篇 · 查过没查到 11 篇 · 查过失败 7 篇 · 不适用 4 篇 · 台账说补到了却没标签 3 篇补全分类号：一次默认补 50 篇、最多 200 篇。「全部补完」这次会补 1 篇（一篇一到几秒，大」
== kb-page-render smoke FAIL (185/186) ==
```

### M9 → N25（+N28）｜把"全部补完"的代价行掏空

```
FAIL  N25 「全部补完」入口在，且**按下之前**那一行就把代价写清了（这次补 N 篇 / 一篇一到几秒 / 大约要等多久）—— 篇数就是后端现算的 `missing` — 按钮「全部补完」/ 代价行「「全部补完」：一次把库里还缺的都补上」/ title「「全部补完」：一次把库里还缺的都补上」
FAIL  N28 批大小与硬上限的**数字**也来自后端：换成 41 / 137 / 777（且还缺 900 篇 > 上限 777）之后，界面那两句跟着变（写死 50/200/2000 会红） — 含「一次默认补 41 篇」=true / 含「最多 137 篇」=true / 含「这次会补 777 篇」=false / 含「一次最多补 777 篇」=false
== kb-page-render smoke FAIL (184/186) ==
```

### M10 → N30｜后端没给路径时编一句"已自动备份"

```
FAIL  N30 后端没给回退记录路径时**如实说读不到**（不是编一句"已自动备份"） — 「已存回退记录：已自动备份（读到的路径没显示）」
== kb-page-render smoke FAIL (185/186) ==
```

### M11 → N32｜用"补完了"冒充结果

```
FAIL  N32 「全部补完」按下去之后界面说清"这次要补几篇"（不用"补完了"这种话冒充结果） — 消息「「全部补完」：补完了，跑完自动刷新。」
== kb-page-render smoke FAIL (185/186) ==
```

### M12 → N27｜不念"现在库里还缺 N 篇"

```
FAIL  N27 撞硬上限时**不假装补完了**：照念后端的 `hard_cap` 说法（第一跑的收尾消息里同时说清"现在还剩多少"，数字 = 后端现算的 `missing`） — 停因「为什么停：桩：后端换过的另一种说法（不是界面自己编的）」/ 第一跑消息里含"现在库里还缺 1 篇"=false
== kb-page-render smoke FAIL (185/186) ==
```

**变异小结**：12 次变异 ⇒ **N21–N32 十二条逐条都变红，无一恒真**。
每次变异后都 `git checkout -- <绝对路径>` 还原并看 `git status --short`（§2 表）。

## 5. 任务书点名的六件事，逐件交代

### 5.1 桩是不是承重的？——是。给一个**机械反例**（不是正例）

任务书要的正/反例，我给**反例**，因为反例才是"排除自己验自己"的证据：

- N28 的断言里写着**字面量** `41 / 137 / 777`（不是引用旋钮变量），而这三个数**只出现在第二跑的桩**里。
- 我做的 M2 变异正好是"界面写死**第一跑**桩给的那组数（50/200/2000）"——
  如果判据是"拿自己喂给桩的常量比自己"，这个变异**不可能红**（界面与桩同步）。
- 实测它**红了**，原文是 `含「一次默认补 41 篇」=false / …=false`。

⇒ 判据比的是**换过之后的桩值**，与第一跑喂进去的常量**不同源**。N26 同理：
断言里的新句取自被 `ccsStopLabels = {..., hard_cap: '桩：后端换过的另一种说法（不是界面自己编的）'}`
改过的那张表；M1（界面写死）与 M7（界面自编）**两次都红**，而"新句在场 + 旧句不在场"两条一起看，
写死/自编都过不去。

另一个**直接的桩可控证据**（我先怀疑、用探针查清后修正了自己的读法）：
我一开始读源码以为第二跑的 `ccsRan`（`total>0 || done>0`）会是 false ⇒ `.ks-ccs-undo` 根本不该渲染，
而 N30 却断言它存在。我加了一行探针（`plugin/scripts/probe-ccs-tmp.mjs`，拷自冒烟、只加一句 console.log，已删）实跑：

```
PROBE1 ccsSeen=["doc_in_rec","doc_in_bad"] polls=2 running=false undo=null bar=1 c2undo=["已存回退记录：读不到（接口没给路径）"] c2stop=["为什么停：桩：后端换过的另一种说法（不是界面自己编的）"]
```

⇒ 真相是：**桩的 `ccsSeen` 在两次挂载之间没有被清空**，所以第二跑的 `total=2`、`stop_reason='hard_cap'` 都在，
N26/N27/N30 都跑在"被换过的桩值"上。**是我的读法错了，不是判据恒真** —— 就地对账，不静默。

**一处诚实的边界**：N32 断言的"这次要补 N 篇"里的 N 来自**同一个桩变量** `ccsSeen.length`
（断言读它算期望值）。它红的形态是"界面说'补完了'、不含那个数"（M11 实测红），**有牙**；
但它**不能**证明"界面显示的数 == 后端 `queued` 字段"——桩里两者是同一个东西。这是抽样级证据，不是全部。

### 5.2 交付件里真有这些字吗？——有；"整份一致"是真逐字符

`plugin/client.js` 是 esbuild 产物，**非 ASCII 全部走 `\uXXXX` 转义**（大写十六进制）。
第一次我用中文字面量直接搜，得到 0 命中 —— 那是**搜索形态不对，不是缺字**（就地对账：

```
$ Get-ChildItem plugin\client.js | Select-Object Length
Length : 1772865          # CRLF 形态
$ ([regex]::Matches($c,'\\u[0-9a-fA-F]{4}')).Count
30206
```

按转义形态搜（把每个字符转成 `\uXXXX`）：

```
已存回退记录：      => 3
为什么停：          => 2
全部补完            => 8
台账说补到了却没标签 => 1
再按一次接着补      => 1
读不到（接口没给路径） => 1
已开始「全部补完」   => 1
```

⇒ 交付件里**确有** B3b 的界面原文。`smoke-client-entry` 那条"整份一致"也实跑过：

```
$ node plugin/scripts/smoke-client-entry.mjs
PASS  ⚠ 交付产物与「从源码现构建」**整份一致**（改了 `client/` 却忘了 `build:client` ⇒ 这条红；复核 b26 的 F2） — 交付 1727868 字符 / 现构建 1727868 字符
== client-entry smoke PASS (190/190) ==
exit=0
```

**它比的是整份**（我读了实现，不是凭它的 check 名）：`smoke-client-entry.mjs` 里
`deliveredN === freshN` —— 两份**全文**经 `\r\n → \n` 归一化后做**字符串全等**比较，
不等就打印第 1 个差异位置。不是"只比长度"、也不是"只比 5 个标记"。

⚠ 附带提醒（不是本批的罪）：`plugin/client.js` 的**磁盘字节数**在 CRLF（1,772,865）与 LF 之间会变，
`client-entry` 打印的 1,727,868 是**归一化后的字符数**。拿字节数当"产物差异"是坏证据（本仓已有明文教训）。

### 5.3 `--ccs` 是纯加法且默认关吗？——是（字节级证明）

三条命令，产物 HTML：

```
$ node plugin/scripts/ui-render-shot.mjs --page kb --interact kb-inbox --width 520 --out var\tmp\b3b-shots\noflag.png
exit=0        # 产物 noflag.html = 326763 字节

# 同一跑，换成 **base 提交 12cb6b0 那一版的脚本**（git show 12cb6b0:plugin/scripts/ui-render-shot.mjs 落地成临时副本）
$ node plugin/scripts/base12cb6b-ui-render-shot.mjs --page kb --interact kb-inbox --width 520 --out var\tmp\b3b-shots\base.htmlx
exit=1        # ← 见下（它的量高步骤报错），但 HTML 已写出：base.htmlx = 326763 字节

$ node plugin/scripts/ui-render-shot.mjs --page kb --interact kb-inbox --ccs --width 520 --out var\tmp\b3b-shots\withflag.png
exit=0        # withflag.html = 328444 字节
```

```
noflag=326763 base=326763 withflag=328444
noflag==base : True        # ← 不加 --ccs：改后脚本与 base 脚本产出**逐字节相同**
noflag==withflag : False   # ← 加 --ccs：真的变了
```

再按内容核（不是只看长度）：`base.htmlx` 与 `noflag.html` 里 `官方接口` / `本地种子文件`（四项层名的
**桩数据**）都是 `False`，只有 `withflag.html` 是 `True`；而 `ks-ccs-bar` 在三个文件里都是 `True` ——
那是 `ksGuideStyles.ts` 模板串里的 **CSS 规则与注释**（`/* 「已存回退记录：<路径>」… */`），
两版都有，**不是**界面块被渲染出来的证据。⇒ base 与改后在**同一场景**上同字节，
实施者"273051 == 273051"这条说法**方向正确**（字节数与我量到的不同，因为量的是不同的一跑/不同版本基线）。

⚠ **base 那一跑 exit 1 的诚实交代**：它红在
`❌ 量高失败（--dump-dom 里没有 <title>h=…|m=…</title>）`，stderr 尾是 Edge 的
`QQBrowser user data path not found`。这是**base 版脚本自己的量高步骤**在我这台的报错，
HTML 已先写出（326763 字节，逐字节等于改后不加开关那一份）。**这个 exit 1 不是被验批次的罪**，
也不是"加了 --ccs 才坏"——它与开关无关（那一跑没给 `--ccs`）。改后脚本同一跑是 exit 0。

### 5.4 `--ccs` 参数非法时干净报错吗？——是

```
$ node plugin/scripts/ui-render-shot.mjs --page kb --interact kb-files --ccs --width 520 --out var\tmp\b3b-shots\bad.png
❌ `--ccs` 只对 `--interact kb-inbox`（「待分类」那一层）有意义：这一跑的场景是 [kb-files]，那里没有「补全分类号」那一块。
   给了它却什么都不做 = 静默没做成，故按参数错退出（exit 2）。用法：--page kb --interact kb-inbox --ccs
exit_badcombo=2

$ node plugin/scripts/ui-render-shot.mjs --page kb --interact kb-nope --width 520 --out var\tmp\b3b-shots\bad2.png
❌ 未知的 --interact 场景名：kb-nope
   可用场景名（共 19 个）：kb-files / kb-level / … / office-page
   ⚠ 这不是"忽略一下继续跑"的情况：旧行为是**什么都不做还 exit 0**（复核 verify-freeze-5h 实测 --interact kb-empty ⇒ notes=[]、exit 0），那种静默本批已堵死。
exit_badname=2
```

⇒ 给错场景 **exit 2 且打印场景名**（不是静默降级）。顺带核了老的"未知场景名"那条路**也仍然 exit 2**。

### 5.5 "跑到了没跑"？——每条结论命令的输出里都有**标识被测路径**的东西

不靠退出码，逐条点出输出里能标识路径的字段：

| 结论 | 输出里标识被测路径的东西 |
|---|---|
| `--ccs` 默认关 | 三个 HTML 的**字节数与内容标记**（`官方接口`=False/True），以及 `#listcap 自检 …成员 [...[补全分类号（还缺 380 篇）]…[全部补完]…]` |
| 12 条判据有牙 | 每条 FAIL 行里带**实测到的界面原文**（面名 `.ks-ccs-stop` / `.ks-ccs-split` / `.ks-ccs-undo` / `.ks-ccs-allcost` / `POST body={}` / title 全文） |
| 交付件有字 | 转义形态计数（`已存回退记录：`=3 …），以及 `交付 1727868 字符 / 现构建 1727868 字符` |
| `#listcap` 几何 | `这一行 5 个可见成员、两两无重叠，相邻最小水平间隙 8px（下限 4px）；成员 ["span.ks-lhead-name[待分类]@204-360","button.Button_button[在此范围内提问]@368-492","button.Button_button[补全分类号（还缺 380 篇）]@204-372.7","button.Button_button[全部补完]@380.7-450.7","span.ks-kb-hint[4 篇还没归位]@204-273.8"]` |
| 第二跑真的换了桩 | 探针那行 `PROBE1 ccsSeen=[...] polls=2 running=false undo=null …` |

（对照本仓明文教训：`--nav-page` 那种"参数根本不读、exit 0 也算过"的空闸门，
这里没有踩到 —— `--ccs` 的错场景路径**当场 exit 2**。）

### 5.6 报告里我复现不了的 —— 见 §6（U1/U2/U3），不静默丢弃。

## 6. 我没验成的（及原因）

- **U1（MED）｜`hard_capped=true` 那一支界面文案没有真跑覆盖。**
  `KsKnowledgePage.tsx:1638` 那一句 `res.hard_capped ? '（到一次最多能补的那条线就停，剩下的下次再点）' : ''`
  只在**起批返回** `hard_capped=true` 时出现，而冒烟的 `POST /kb/ccs/backfill` 桩**写死**
  `hard_capped: false`（`smoke-kb-page-render.mjs:776`）。N32 的断言也只匹配到
  `已开始「全部补完」：这次要补 2 篇；一篇一到几秒，跑完自动刷新。`（**没有**那半句）。
  ⇒ 撞硬上限时"界面对起批返回那一支怎么说"**本批无任何判据覆盖**，我只能证明
  **status 路径**那一支（N27）。另：报告 §5.6 只登记了"没为硬上限那一支出截图"，
  **没有登记"起批返回的 hard_capped 文案无用例"**，这一条是我补的。**不是判据失守，是覆盖缺口。**
- **U2（LOW）｜`pages > 1` 那句（"分 N 页串行跑"）无真跑覆盖。** 桩给 `pages: 1`
  （`smoke-kb-page-render.mjs:776`）。报告 §5.7 已自己登记，我复核后**确认这条登记属实**（不是漏报）。
- **U3（MED）｜pytest 侧完全没跑。** 这棵树没有 `.venv`（任务书 §5 明说），
  所以**引擎半边**（五桶恒等式"五桶之和 == total"、`STOP_REASON_LABELS` 七值互斥、
  `missing_ccs_split()` 的取值）**本报告一个字都没验**。我只做了**静态对读**（见 C8）：
  逐字段把桩/客户端的名字与 `src/core/knowledge/ccs_backfill.py`、`src/core/api/routes_kb_folders.py`
  的真实字段名对齐（`missing_split` 的五个桶名逐字相同：`total / never_checked / checked_not_found /
  checked_failed / not_applicable / found_but_untagged`；`stop_reason_labels` 七个键与七句中文逐字相同；
  `sources`+`source_labels` 四项逐字相同；`max_batch=200 / default_batch=50 / max_all=2000` 相同）。
  **静态对读不是实跑**，别当等价证据。
- 另：**`scripts/run-gates.ps1` 与 `plugin/scripts/smoke-all.mjs` 我没跑**（任务书 §5 明令），
  所以 `smoke-kb-pad-pixels` / `smoke-kb-cols` / `ui-badge-pixels` / `smoke-build-purity`
  这几条以及全局棘轮**本报告不覆盖**。我用 `--ccs` 那一跑的 `#kspad`/`#listcap` 自检
  做了**抽样替代**（见 5.5 表），那是抽样，不是全量。

## 7. C8 的机械取证（桩 ↔ 引擎真代码，防"桩照抄界面假设"）

这是本批最容易被忽略的假绿形状：**桩与界面互相印证、而真后端字段名不同** ⇒ 冒烟全绿、真机一行不显示。
核法：在**同一棵冻结树**里读引擎源码（不是读 B3a 那棵参考树、不是读报告的表）：

```
$ Select-String -Path src\core\knowledge\ccs_backfill.py -Pattern "stop_reason|undo_journal|missing_split|max_all|source_labels"
87:  STOP_REASON_LABELS: dict[str, str] = {
88-93: 七个键（no_candidates/exhausted/limit/hard_cap/selected_done/cancelled/error）+ 七句中文
541:  "undo_journal": None, "pages": 0, ...
587:  snap["max_all"] = MAX_BACKFILL_ALL

$ Select-String -Path src\core\api\routes_kb_folders.py -Pattern "kb_ccs_summary" -Context 0,30
531:  return {... "data": {
532:      "missing": bf.missing_ccs_count(),
533:      "missing_split": bf.missing_ccs_split(),
535:      "max_batch": bf.MAX_BACKFILL_DOCS,
536:      "default_batch": bf.DEFAULT_BACKFILL_DOCS,
537:      "max_all": bf.MAX_BACKFILL_ALL,
539:      "source_labels": dict(SOURCE_LABELS),
540:      "stop_reason_labels": dict(bf.STOP_REASON_LABELS),
541:      "sources": list(SOURCES),
542:      "backfill": bf.ccs_backfill_status()}}
```

桩（`smoke-kb-page-render.mjs:744-757`）与客户端归一化（`plugin/client/api.ts:4125-4160`）
**逐字段一致**；`STOP_REASON_LABELS` 七句中文、`SOURCE_LABELS` 四项中文**逐字一致**。
⇒ 没有"桩自证"的字段漂移。**（仍是静态对读；跑引擎要 `.venv`，见 U3。）**

## 8. 顺手发现、但不属于本批（单列，别混进结论）

- **F1（LOW，非本批）｜`befc595` 新加的那条 `.ks-list-cap` 判据偏弱。**
  `befc595` 的目的是堵"抓手被改名 ⇒ 像素判据退化成'这一跑不适用'而静默通过"。
  但它的实现是**源码文本**检查：

  ```
  check('B2·抓手仍在：… 类名 `ks-list-cap` 必须还在（像素判据靠它找行；改名 ⇒ 本条红）',
    srcKbTop.includes('className="ks-list-cap'),
  ```

  文本在场 **≠** 那个元素仍被渲染、**≠** 类名还在**那一行**上。它挡住"改名字"，
  挡不住"类名挪到别的元素上 / 那一行被删掉而字符串留在注释里"。
  该提交自己写了"**没有**把 `.ks-list-cap` 正式收编进必量清单…已登记为残余"——**登记属实**，
  我只是把它标成"弱判据"而不是"解决"。**按任务书要求单列，不计入 B3b 判定。**
- **F2（LOW，非本批）｜报告引用的提交 id 不在 master 历史里。**
  `B3B-REPORT.md` §头部写 `d35d1ca` / `8515ade`；被验的是 `2d10e6c` / `f9116d3`。
  我按本仓纪律核了：`git merge-base --is-ancestor d35d1ca HEAD` ⇒ **exit 1（不是祖先）**；
  但 `git tag -l` 有 `prerebase-b3b`（= `482283a`，报告第三笔的 prerebase 版），
  且 `git diff --stat d35d1ca 2d10e6c -- <五个界面文件>` 对
  `KsKnowledgePage.tsx / client.js / smoke-kb-page-render.mjs / api.ts` 全部 **IDENTICAL**
  （只有 `ui-render-shot.mjs` 差分 211 行，因为那棵 prerebase 树缺 B1+B2 那些较晚改动）。
  ⇒ 报告引用的 id **可溯源、内容对得上**（tag 保住了），**不算假绿**；
  但按本仓"引 id 前先核它在不在 master 历史"的纪律，报告里该同时写出主仓 id。登记为残余。
- **F3（LOW，非本批）｜脚本头部的条数注释已过期。**
  `smoke-kb-page-render.mjs` 头部注释仍写着历史快照（"第 6 步 = 148/148"、后面又写 156/156 等），
  而实跑是 **186/186**。脚本自己那句"以脚本结尾打印的为准"是对的，
  实施者/复核都**没有引错**（B3B-REPORT 引的是 185/185，它自己树的数）。
  只是那一段会误导后来者。登记，不属本批。

## 9. 收尾取证

见 §1 之前的"开工时"与本节：

```
$ git -C "D:\AI\work space\zcode-verify-b3b" rev-parse HEAD
dec2cd4bfce5d87e7487da5cd7ad4e246790795b

$ git -C "D:\AI\work space\zcode-verify-b3b" status --short
?? VERIFY-REPORT-b1b2.md
?? VERIFY-REPORT-b3b.md
```

（`VERIFY-REPORT-b3b.md` 就是本报告本身；`VERIFY-REPORT-b1b2.md` 是上一轮复核的报告，
任务书要求别动 —— 我没动它。除这两个未跟踪文件外，工作树**与 `dec2cd4` 一致**，
12 次变异全部还原。）

**还原之后复跑一次冒烟**（证明 12 次变异没在树里留残余）：

```
$ node plugin/scripts/smoke-kb-page-render.mjs
== kb-page-render smoke PASS (186/186) ==
exit=0
```

**主仓**（`D:\AI\work space\zcode`）代码区一个字节没动：

```
$ git -C "D:\AI\work space\zcode" status --short -- . ":(exclude)var/tmp"
（空）
```

报告两处落点**内容相同**（各 29,646 字节）：
`D:\AI\work space\zcode-verify-b3b\VERIFY-REPORT-b3b.md` 与
`D:\AI\work space\zcode\var\tmp\verify-reports\VERIFY-REPORT-b3b.md`。

## 10. 总判定（重复一次，收尾）

**PASS-with-gaps**。17 PASS / 0 FAIL / 3 UNVERIFIED；HIGH 0 / MED 2 / LOW 3。
12 条判据逐条有牙（12 次变异逐条变红，原文见 §4）；没找到假绿；
两个 MED 是覆盖缺口（起批返回的 `hard_capped` 文案无用例；pytest 侧跑不了），不是判据失守。
