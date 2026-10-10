# Implementation Plan: UI 精修（spec 007）

**Feature**: `007-ui-polish` ｜ **Spec**: [spec.md](./spec.md)

**Created**: 2026-10-10

---

## 一、技术上下文

| 项 | 值 |
|---|---|
| 语言/框架 | TypeScript + React 18（客户端插件，ESM） |
| 样式通道 | 本仓是**仓外 bundle 插件**，样式在 `ksGuideStyles.ts` 的模板字符串 `KS_STYLES` 里（不是 CSS Modules —— 官方那套 `ui-theme` 全局表**不归我们**，见 `docs/UI-BASELINE.md` §四） |
| 交付产物 | `plugin/client.js`（由 `plugin/scripts/build-client.mjs` 从源码构建，**必须与源码同步**） |
| 判据通道 | ① 离屏真浏览器：`plugin/scripts/ui-render-shot.mjs`；② jsdom 行为：`smoke-kb-page-render.mjs`；③ 产物字面量/棘轮：`smoke-client-entry.mjs`；④ 尺度棘轮：`smoke-ui-scale.mjs` |
| 门禁 | `pwsh -File scripts/run-gates.ps1 -Quick`（改动面）/ `-Full`（收工） |

## 二、宪法检查（.specify/memory/constitution.md）

- **原则 VI「只做缝合不做发明」**：D1/D2 的修法是**补定义或删引用**，不是引入新机制。
- **原则「判据要有牙」**：每条修复都要配一条**能被变异打红**的判据。
- **「诚实边界」**：真宿主进不去的面，必须写明"没看到"。

## 三、阶段划分

### 阶段 0：取证与基线（本轮已完成大半）

- 真机审查设置面（✅ 已做，截图在手）
- 源码级 token 归属审计（✅ 已做，`var/tmp/token-ownership.py`）
- 官方规范逐条对照（✅ 已做，见 spec §三）

### 阶段 1：D1 + D2（token 缺口）—— 最便宜、最确凿，先做

**改法选择（要留痕）**：两个 token 有两条路 —— ① 补定义；② 删引用换现成值。

| token | 选哪条 | 理由 |
|---|---|---|
| `--ks-radius` | **补定义** | 它表达的是"标签页凸舌的圆角"，本仓圆角表里**没有**这一档的语义名；补一个 `--ks-radius: var(--ks-radius-md)` 既保留语义、又落在官方 `ui-radius.md` 的 token 上（**不许**写 10/14/18 这种本地值） |
| `--ks-font-mono` | **补定义** | 等宽字体档是**真实需求**（标准号徽章、失败编号都在用等宽），且本仓已有 `--ks-font-*` 家族；补 `--ks-font-mono` 到 `:root` 与家族并列 |

⚠ **两条都必须落回官方 token**：`ui-radius.md` 明写「Consume the named tokens instead of introducing
local values such as 10px, 14px, 18px, or 24px」。

### 阶段 2：D3（表单溢出）—— 有真机证据

**根因**：`flex` 容器里 `flex:1` 的项默认 `min-width:auto`，内容（placeholder 很长）撑住不缩
⇒ 整行溢出、最右的输入框被裁。

**改法（本仓已有的正确写法，直接沿用）**：给可收缩的那一项加 **`minWidth: 0`**，
并让外层容器**允许换行**（`flexWrap:'wrap'` 已有）。
⚠ 本仓 `ksGuideStyles.ts:312` 的注释就是这个坑的留痕（"flex-basis 必须与 min-width 同值"），
所以这次**不要**再发明第二种解法。

### 阶段 3：判据（每条修复配一条，且要有牙）

| 缺陷 | 判据落点 | 怎么判 | 变异验证（必须做） |
|---|---|---|---|
| D1/D2 | `plugin/scripts/smoke-ui-scale.mjs`（已在门禁链里） | 从 `ksGuideStyles.ts` 抠出**所有** `var(--ks-*)` 引用与 `--ks-*:` 定义，要求**引用 ⊆ 定义**（带兜底的允许放行并列出） | 删掉一条 `--ks-radius:` 定义 ⇒ 必红 |
| D3 | `plugin/scripts/ui-render-shot.mjs` 新增量点 + Node 侧判 | 真浏览器量"输入框右缘 ≤ 容器内容盒右缘"，溢出 > 1px 即红；量不到即红 | 把 `minWidth:0` 改回 ⇒ 必红 |

⚠ **D3 的判据要能在离屏渲染里跑到**：设置面在离屏渲染里**没有对应 page**
（`ui-render-shot` 的 `--page` 只有 `kb|ingest|capabilities|materials`）。
⇒ 两条路：① 给 `ui-render-shot` 加一个 `settings` 页（**加法式**，不影响既有场景）；
② 用 jsdom 冒烟量。**选 ①** —— 因为溢出是**布局**问题，jsdom 没有布局引擎，**量不出来**。

### 阶段 4：四个主面的逐态审查（留痕）

- 用 `ui-render-shot` 把每个面的每个交互态渲一遍，逐张 `read_image`。
- 结论写进 `docs/UI-BASELINE.md`（一个面一行）。

## 四、交付物

| 产物 | 落点 |
|---|---|
| 修复 | `plugin/client/ksGuideStyles.ts`（D1/D2）、`plugin/client/KsSettingsSection.tsx`（D3） |
| 交付产物 | `plugin/client.js`（重建） |
| 判据 | `plugin/scripts/smoke-ui-scale.mjs`（D1/D2）、`plugin/scripts/ui-render-shot.mjs`（D3 量点 + `settings` 页） |
| 留痕 | `docs/UI-BASELINE.md` §5aa、`docs/DEVELOPMENT-HISTORY.md` §10.232 |
| 证据 | `var/tmp/ui-shots/`（截图，不入库）+ 本 spec 的 `research.md` |

## 五、风险与对策

| 风险 | 对策 |
|---|---|
| 改 `KsSettingsSection.tsx` 误碰禁碰段（`AnnounceTriageSection`） | 改动前 `grep -n "function AnnounceTriageSection"` 定位行号区间；只改区间外的行 |
| 给 `ui-render-shot` 加 `settings` 页会打断既有的**冻结清单**（`EXPECTED_RUNS`/`MATRIX`） | 加页是**加法**；但若进 `MATRIX` 必须**同批**改 `EXPECTED_RUNS`（本仓有"声明了就必须有人跑"的棘轮）⇒ 先只加页、**不进 MATRIX**，用单独命令量 |
| 门禁被并行线占用（退出码 3） | 退出码 3 = "有人在跑"**不是失败**；等锁释放再跑，不并发 |
| 真宿主四个面进不去 | 写明边界，改用离屏证据，**不许**写成"已真机验证" |
