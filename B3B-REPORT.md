# B3B-REPORT —— 「补全分类号」的**界面**半边（B3b）

- 工作树：`D:\AI\work space\zcode-b3b-ui`（分支 `b3b-ccs-ui`，起点 `0b05841`）
- 引擎半边只读参考树：`D:\AI\work space\zcode-b3a-ccs`（B3a 提交 `180397f`）—— **字段名以那棵树的代码为准**，逐条核过（见 §0）
- 提交：`d35d1ca`（界面接线 + 六条落地 + 重建交付件）、`8515ade`（12 条新判据）
- 本报告一笔：`B3B-REPORT.md` + `plugin/scripts/ui-render-shot.mjs`（只为出截图加的 `--ccs` 开关 + 一段默认关着的桩）

---

## 0. 先说字段名核对（任务书 §0 要求"别凭转述写代码"）

从 `D:\AI\work space\zcode-b3a-ccs` 的**代码**里逐条读出来的（不是抄任务书）：

| 我用到的字段 | 出处（B3a 那棵树里的行） | 形状 / 取值 |
|---|---|---|
| `missing_split` | `src/core/knowledge/ccs_backfill.py:178-209` | `{total, never_checked, checked_not_found, checked_failed, not_applicable, found_but_untagged}`；**五桶之和 == total** |
| `stop_reason` / `stop_reason_label` | `ccs_backfill.py:84-92`、`:541-542` | 七个互斥值 `no_candidates/exhausted/limit/hard_cap/selected_done/cancelled/error`；label 由后端查表给 |
| `stop_reason_labels`（整张表） | `routes_kb_folders.py:540`（`summary` 下发 `dict(bf.STOP_REASON_LABELS)`） | 值 → 中文话 |
| `undo_journal` | `ccs_backfill.py:107/431/486`、`ccs_undo.py:140`（`write_undo_journal` 返回 `{"path",…}`） | **一个路径字符串**（不是对象、不是列表） |
| `max_batch` / `default_batch` / `max_all` | `ccs_backfill.py:543-545` | 200 / 50 / 2000 |
| `scope` / `force` / `truncated` / `hard_capped` / `plan_total` / `page` / `pages` | `ccs_backfill.py:432-442` | 见代码 |
| `missing_error` | `ccs_backfill.py:552` | 读 `missing` 失败时的原话 |
| `all=true` | `ccs_backfill.py:448/466-477`、`routes_kb_folders.py:593` | 「全部补完」；与 `doc_ids` 互斥 |
| 起批返回 `undo_journal`/`pages`/`hard_capped` | `ccs_backfill.py:498-507` | 注意 `queued=0` 那一支返回的 `undo_journal` 是 `null` |
| `sources` / `source_labels` | `routes_kb_folders.py:539/541`（`ccs_fetcher.SOURCES`） | **四项**（含"本地种子文件"）—— 界面原来只写死三层 |

---

## 1. 逐条做了什么（任务书 §1 的 1–6）

| # | 要求 | 落点（文件:行） | 判据 |
|---|---|---|---|
| 1 | 补之前有备份 ⇒ 界面说得出 | `plugin/client/KsKnowledgePage.tsx:1735-1740`（派生 `ccsUndoLine`）、渲染 `:2931-2934` | **N21**（有路径时原样显示）+ **N30**（后端没给路径 ⇒ 说"读不到"，不许编"已自动备份"） |
| 2 | 还剩多少**拆开** | `KsKnowledgePage.tsx:1743-1751`（五桶逐桶）、渲染 `:2925-2926` | **N22**（五桶各一个数、和=42；合并成"部分失败"⇒ 红） |
| 3 | 为什么停（用后端说法） | `KsKnowledgePage.tsx:1520-1535`（`ccsStopText`/`ccsStopSentence`）、`1725-1728`、渲染 `:2921-2924`；收尾消息 `:1680-1692` | **N23** + **N26**（反向：后端换说法界面跟着变、旧句不许在）+ **N27**（硬上限照念 + 还剩多少） |
| 4 | 「再按一次」+ 一次最多多少 | `KsKnowledgePage.tsx:1577-1583`（`ccsBatchText`）、渲染 `:2927-2928` | **N24**（默认 50 / 最多 200 在场）+ **N28**（换成 41/137/777 ⇒ 界面跟着变） |
| 5 | 一次补完（`all=true`）+ 按下之前说清代价 | 入口 `KsKnowledgePage.tsx:2883-2898`、代价行 `:1548-1575`（`ccsWaitText` + `ccsAllCostText`，`ccsAllWillDo` `:1541-1546`）、起跑 `:1628-1655` | **N25**（代价行 + title 都写了"这次会补 N 篇 / 一篇一到几秒 / 大约要等多久"）+ **N31**（真发 `all:true`）+ **N32**（说"这次要补几篇"，不说"补完了"）+ **N27/N28**（硬上限） |
| 6 | tooltip 四层 | `KsKnowledgePage.tsx:1585-1597`（`ccsChainText` 用后端 `sources`+`source_labels`）、按钮 title `:2877` | **N29**（换成"桩层甲→乙→丙→丁"跟着变、旧的三层文案不许在） |
| 7 | 判据只增不减 | `plugin/scripts/smoke-kb-page-render.mjs` N21–N32（12 条） | 见 §2 的真跑数字 |

**顺带**（复核点名的 LOW-1，"不许界面自己推断原因"）：`KsKnowledgePage.tsx:2282-2309` 的
「有分类号却没有建议」那一格原来写死"**问题在于现有目录里没有对应的那一层**"，而同段注释自己
承认还有第二种可能（落进兜底桶）⇒ 这是界面替后端编原因。现在只说**事实**（有分类号 + 系统没给
建议的去向）与**后果**（只能手动指定去处），并明说"为什么没给，后端没有下发原因"。
**原文留痕在注释里**（没删）。

**交付件**：`plugin/client.js` 已重建（`node plugin/scripts/build-client.mjs`），
`smoke-client-entry` 的"交付产物与从源码现构建**整份一致**"那条绿。

---

## 2. 真跑数字（原样抄 stdout）

```
== kb-page-render smoke PASS (185/185) ==      [exit 0]      ← 改动前同一脚本是 173/173（桩里还没有 B3a 那些字段）
== client-entry   smoke PASS (190/190) ==      [exit 0]      ← 含"交付件 == 从源码现构建"那条
```

12 条新判据逐条的真跑输出（摘最有信息量的几行）：

```
PASS  N21 … — .ks-ccs-undo 1 个 / 文字「已存回退记录：D:\KnowledgeStation\backups\ccs-undo-20260924-101500.json」
PASS  N22 … — 状态行：「还剩 42 篇没补：从没查过 17 篇 · 查过没查到 11 篇 · 查过失败 7 篇 · 不适用 4 篇 · 台账说补到了却没标签 3 篇」
PASS  N23 … — 「为什么停：到了这一批的量就停（剩下的下次再补）」
PASS  N25 … — 按钮「全部补完」/ 代价行「「全部补完」这次会补 1 篇（一篇一到几秒，大约要等 1 秒~5 秒）。」/ title 同文
PASS  N26 … — 新句「为什么停：桩：后端换过的另一种说法（不是界面自己编的）」/ 旧的 hard_cap 说法还在场=false
PASS  N28 … — 含「一次默认补 41 篇」=true / 含「最多 137 篇」=true / 含「这次会补 777 篇」=true / 含「一次最多补 777 篇」=true
PASS  N29 … — title「插件自己按「桩层甲 → 桩层乙 → 桩层丙 → 桩层丁」逐篇查缺的分类号（全库还缺 900 篇；一次最多补 137 篇；…）」
PASS  N30 … — 「已存回退记录：读不到（接口没给路径）」
PASS  N31 … — POST body={"all":true}
PASS  N32 … — 消息「已开始「全部补完」：这次要补 2 篇；一篇一到几秒，跑完自动刷新。」
```

---

## 3. 变异自证（两条，都是**原始红**；跑完都还原了，`git status` 只剩当笔该提交的文件）

**M1 —— 界面自己编"为什么停"**（把 `ccsStopText` 改成返回一句写死的中文，不查后端那张表）：

```
FAIL  N23 「为什么停」＝后端下发的那句（…） — 「为什么停：树里没有对应的那一层（界面自己推断的原因）」
FAIL  N26 **反向**：同一个停因（hard_cap）后端换了说法，界面跟着变（新句在场、**旧句不在场**）⇒ 原因文案来自后端注入的 label，不是界面自己推断/写死的 — 新句「为什么停：树里没有对应的那一层（界面自己推断的原因）」/ 旧的 hard_cap 说法「到了硬上限就停（还剩没补的，不是补完了）」还在场=false
FAIL  N27 撞硬上限时**不假装补完了**：照念后端的 `hard_cap` 说法（…） — 停因「为什么停：树里没有对应的那一层（界面自己推断的原因）」/ 第一跑消息里含"现在库里还缺 1 篇"=true
== kb-page-render smoke FAIL (182/185) ==
[exit code: 1]
```

**M2 —— 五桶合并成一句"部分失败"**（把 `ccsSplitLine` 改成只报一个合计）：

```
FAIL  N22 「还剩多少」**拆开**成五桶逐桶显示（…）—— 合并成一句"部分失败"就必然对不上 — 状态行：「还剩 42 篇没补：部分失败 7 篇。」
== kb-page-render smoke FAIL (184/185) ==
[exit code: 1]
```

还原判据：`git status --short`（**不用哈希** —— 本机 `core.autocrlf=true`）。

---

## 4. 真机截图（Edge 无头，全页；`ui-render-shot.mjs`，四张都 exit 0）

```
D:\AI\work space\zcode-b3b-ui\var\tmp\ui-shots-b3b\b3b-ccs-narrow-light.png   520×889    （窄档 520 · 浅色）
D:\AI\work space\zcode-b3b-ui\var\tmp\ui-shots-b3b\b3b-ccs-wide-light.png    1300×700    （宽档 1300 · 浅色）
D:\AI\work space\zcode-b3b-ui\var\tmp\ui-shots-b3b\b3b-ccs-narrow-dark.png    520×889    （窄档 520 · 深色）
D:\AI\work space\zcode-b3b-ui\var\tmp\ui-shots-b3b\b3b-ccs-wide-dark.png     1300×700    （宽档 1300 · 深色）
```

命令：`node plugin/scripts/ui-render-shot.mjs --page kb --interact kb-inbox --ccs --width <520|1300> --theme <light|dark> --out <png>`

**为什么是"两档宽 × 深浅两色"而不是"四个面"**：B3b 这一批的界面**只活在「待分类」那一层**
（`.ks-list-cap` 那一条 bar + 它下面那块状态行），另外三个面（渠道库 / 办事台 / 预览器）结构上
没有这一块；所以我拍的是**承载它的那一层**，档位取"宽窄 × 深浅"（这一页本来就有这两个维度，
`ui-render-shot` 的留边/列几何判据也是按这两维跑的）。

截图里一次能看全六条：`补全分类号（还缺 380 篇）` + `全部补完` ·
`已跑 50 / 50 篇 · 补到 47 篇（其中新写标签 47 篇）· 查无 2 篇 · 查询失败 1 篇 · 读不出来 0 篇 · 不适用 0 篇` ·
`为什么停：到了这一批的量就停（剩下的下次再补）` ·
`还剩 380 篇没补：从没查过 190 篇 · 查过没查到 120 篇 · 查过失败 41 篇 · 不适用 7 篇 · 台账说补到了却没标签 22 篇` ·
`再按一次接着补：一次默认补 50 篇、最多 200 篇。` ·
`「全部补完」这次会补 380 篇（一篇一到几秒，大约要等 6 分钟~32 分钟）。` ·
`已存回退记录：D:\KnowledgeStation\backups\ccs-undo-20260924-101402.json` ·
`▶ 没补到的 3 篇（逐篇原因）`。

**顺手量到的真几何**（脚本自检，四张都过）：
`#listcap 自检通过：这一行 5 个可见成员、两两无重叠，相邻最小水平间隙 8px（下限 4px）`
—— 新加的「全部补完」没有把那一行挤到压字。

### 4.1 为什么**必须**碰 `ui-render-shot.mjs`（任务书 §1.7 要求先说清）

那一段桩里**没有** `/kb/ccs/summary`（以前这一页调到它就是 `STUB_MISS`），不加桩的话截图里
按钮只会是「补全分类号（—）」、新界面**一个字都看不到** —— 截图就交不了差。
所以只做**加法**、且**默认关着**：

- 新增 `--ccs` 开关（**必须**与 `--interact kb-inbox` 同用；落在别的场景上 ⇒ `exit 2`，
  不许"给了却什么都没做"）；
- 不开它时那些路由照旧走 `STUB_MISS` ⇒ **别的场景一个字节都不变**。机械证据：
  用**起点 `0b05841` 的同一支脚本**与**改后的脚本**各跑一次
  `--page kb --interact kb-inbox --width 520`（都不加 `--ccs`），产出的 `.html`
  **逐字相同**：`identical=True lenA=273051 lenB=273051`。
- 没有进 `PAD_REQUIRED` / 没有加新场景名 ⇒ `smoke-kb-pad-pixels` 的
  "声明了就必须有人跑"棘轮、`smoke-kb-cols` 的列几何基线都**没被动**（这正是选
  `--ccs` 开关而不是新场景的原因：新场景会被那条棘轮要求同时改矩阵与 `EXPECTED_RUNS`）。

---

## 5. 我**明确没做**的（以及为什么）

1. **没跑** `scripts/run-gates.ps1` / `npm run smoke` / `plugin/scripts/smoke-all.mjs`
   —— 任务书 §2：全局锁归父代理，一次只许一个。我单跑的只有
   `smoke-kb-page-render.mjs` 与（顺带自检）`smoke-client-entry.mjs`，以及 `ui-render-shot.mjs` 四跑。
2. **没跑** `smoke-kb-cols` / `smoke-kb-pad-pixels` / `ui-badge-pixels` / `smoke-build-purity`。
   替代证据 = §4.1 那条"HTML 逐字相同"（那些脚本拿 `kb-inbox` 等场景当基线）。
   ⇒ 这一条是**抽样/间接证据，不是全量门禁**；全量留给父代理。
3. **没给** `smoke-client-entry.mjs` 的 `SPEC_STRINGS` 加新条目。理由（本仓已有明文教训）：
   那张表钉的是"**交付产物里出现这个字面量**"，而本仓产物**保留注释** —— 钉光秃秃的中文短语，
   会被我自己写的留痕注释喂绿（"看着有牙、其实恒真"）。这批新文案正是模板串里的中文短语
   （`为什么停：` 之类），而真正有牙的判据在 `smoke-kb-page-render` 的 N21–N32
   （跑真组件、整串比对、且第二跑换桩）。
4. **没动** `src/**`（引擎半边是 B3a 的事）；**没动** `docs/UI-BASELINE.md`（本批没有新增
   "留边适用面"，所以那四份副本棘轮一处都不用改）。
5. **没碰真库**：全程没有任何一次真回填（截图与冒烟里的引擎 HTTP 全是桩）；没有在真库上跑那
   330/380 篇。
6. **没做**「硬上限那一跑」真机截图：桩里那一跑是"刚跑完一批（到量停）"；
   `hard_cap` 那条路由**判据**（N27/N28）覆盖，没有单独出一张图。
7. 分页/`pages>1` 的文案（"分 N 页串行跑"）只有 `pages>1` 时才出现，本批桩给的是 `pages=1`
   ⇒ **那句没有真跑覆盖**（明确登记在此，没假装验过）。

---

## 6. 边界与纪律自查

- 只在 `D:\AI\work space\zcode-b3b-ui` 里读写/提交；主仓一个字没写、没 `git add/commit/checkout`
  （只用了它那里的 `node_modules` 真拷贝 —— 见下）。
- `plugin/node_modules` 与根 `node_modules` 都是**真拷贝**（不是 junction/符号链接）：
  否则 esbuild 会把绝对路径打进产物、制造"交付件≠现构建"的**假红**。
- 变异/写文件一律**绝对路径**；变异前先确认目标文件已提交（两处变异都在 `d35d1ca` 里），
  还原后看 `git status --short`。
- 临时产物只删了我自己刚建的那几个（`.tmp-b3b-base-ui-render-shot.mjs`、`_base/_new-inbox-520.*`）；
  更早的 `%TEMP%` 一个都没动。
- 样式只改在 `plugin/client/ksGuideStyles.ts` 的**模板串内部**（第一版我在注释里写了一个反引号，
  被 tsc 当场抓成 `TS1005` —— 已改成「」，并把"模板串里不许出现反引号"写进那条注释本身）。
- `node .\node_modules\typescript\bin\tsc --noEmit -p plugin/client/tsconfig.json` ⇒ **exit 0**。
