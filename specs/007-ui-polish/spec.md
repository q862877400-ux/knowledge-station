# Feature Specification: UI 精修 —— 真机逐面审查后的缺陷收口

**Feature Branch**: `007-ui-polish`

**Created**: 2026-10-10

**Status**: Draft

**Input**: 业主指令「你用 browser Use 的功能，直接开一个窗口去把每个按钮点一下，效果截图下来你自己看看，确保界面优雅整洁规范，而且符合 DSH 最新版的官方要求。你设置好这个目标，然后按照 spec 的规范全自动自己施工」

---

## 背景：为什么需要这个特性

业主连续两轮要求修 KS 的界面。上一轮（`fbcc603`）修的是**渲染级确证的字面 `**`**（伪粗体）。
本轮业主把要求提高了一档：**不是"有没有 bug"，而是"优不优雅、整不整洁、符不符合 DSH 官方规范"**，
并且指定了手段：**用浏览器真机逐个点开、自己看图**。

本节以下每条都是**实测**，不是推测。取证工具与复算命令随每条给出。

### 一、真机审查做了什么（口径）

| 项 | 值 |
|---|---|
| 宿主 | DSH Web GUI `http://127.0.0.1:3080`（真宿主、真插件、真主题、深色） |
| 插件 | `ks-dsh-plugin/client.js`（已在 `__DSH_BOOT__.entries` 里加载，实测确认） |
| 工具 | `browser_*` 注入工具（Agent Window，真浏览器） |
| 窗口 | 先 1018×853，后 `browser_assist resize` 到 1576×826（**两档都看**） |
| 看图 | 每张 `screenshot` 都 `read_image` **自己看**，把"看到的事实"写下来 |

⚠ **诚实边界（必须写在最前）**：KS 的**四个主面**（知识库 / 渠道库 / 办事台 / 备料）挂在**会话的右侧栏**，
而本机 GUI 的**会话树在这个窗口里渲染不出会话节点**（工作区能展开、`status` 节点一直空着）——
控制台有**宿主主包**自身的报错 `TypeError: Cannot read properties of undefined (reading 'startsWith')`
（`assets/index-*.js`，**不是**插件里的），所以我**没能**在真宿主里点进那四个面。
⇒ 那四个面的审查改用本仓既有的**离屏渲染**（`ui-render-shot.mjs`，真 Edge、真 CSS、真组件），
**这不是真宿主**，边界与 `docs/UI-BASELINE.md` §五 记的一致。
**能真机点到、且本轮真机点到的是：设置面（设置 → 法规标准知识库）**。

### 二、已确证的缺陷（每条都可复算）

#### D1 ❌ `--ks-radius` 引用了但从未定义 ⇒ 圆角静默失效

- **落点**：`plugin/client/ksGuideStyles.ts:507`
  `border-radius:var(--ks-radius) var(--ks-radius) 0 0`
- **后果**：变量不存在 ⇒ 该条声明**整条失效**，圆角变成 **0（直角）**，且**不报错**。
- **性质**：官方 `docs/web-styling.md` 明令「不要写死色值 / 用语义 token」，
  而"引用一个不存在的 token"比写死更糟 —— 写死至少看得见。
- **复算**：`python var/tmp/prove-token-gap.py`（同文件内 grep：使用 1 处、定义 0 处）

#### D2 ❌ `--ks-font-mono` 引用了但从未定义

- **落点**：`plugin/client/ksGuideStyles.ts:638`
  `font-family:var(--ks-font-mono,monospace)`
- **后果**：有兜底 `monospace` ⇒ **不致命**，但它是"写了一个本仓不存在的 token"的同类病，
  且掩盖了"我们到底有没有等宽字体档"这个问题。
- **复算**：同 `prove-token-gap.py`

#### D3 ❌ 设置面 API 配置表单：两个 `Base URL` 输入框被**右侧裁掉**

- **落点**：`plugin/client/KsSettingsSection.tsx:1501-1515`
  （外层 `display:flex; flexWrap:wrap`，内层 Key 框 `width:220`、
  Base URL 框 `flex:1; minWidth:200`，**没有 `minWidth:0`**）
- **真机证据（截图）**：`var/tmp/ui-shots/realhost/*.png`
  - 1018×853：Base URL 的 placeholder `（留空保持不变；输 "-" 恢复内置默认）` **右半截被切**；
  - **1576×826（加宽 55%）后仍然被切** ⇒ 不是"窗口太窄"，是**布局本身溢出**。
- **性质**：placeholder 是**填表说明**，被切掉 = 用户读不全怎么填。
- **机理（已定位到具体 CSS）**：flex 项默认 `min-width:auto`，
  在 `flex-wrap:wrap` 容器里"能不能放下"由 `flex-basis` 决定；
  Key 框固定 220 + Base URL 的 basis 200 + 模式下拉 + 两个按钮 > 容器宽 ⇒ 换行或溢出。
  **这是本仓踩过的同一个坑**（`ksGuideStyles.ts:312` 的注释逐字写着：
  「`flex-basis` 必须与 `min-width` 同值（本批真 Chrome 实测踩到，`levelCheck` 当场红）」）。
- **复算**：真机截图 + 源码逐行。

#### D4 ⚠ 待判（本轮只登记，不改）：设置面字段密度

- 现象：`模式` 下拉 + `保存` + `先保存再测试` 挤在一行；说明文字与控件间距偏紧。
- 为什么不直接判缺陷：**间距是否有规范**要先对照官方 `ui-radius.md` 与主题 token，
  不能凭手感判。⇒ 列进下一阶段的取证项。

### 三、符合官方规范的部分（已核，不是"没查"）

| 官方要求（`docs/web-styling.md`） | KS 现状 | 判 |
|---|---|---|
| 颜色走 `--dsw-alias-*` 语义 token，不写死 | 新面（`ksGuideStyles.ts` + 知识库页）**0 处写死**；老面板仍有存量（见下） | 🟡 部分 |
| 中性边框 0.5px | 冒烟 `smoke-client-entry` 有一条「没有 `1px solid var(--dsw-alias-border-*)`」判据，实测 **0 处** | ✅ |
| 不给"中性边框 + elevation 阴影"配对 | 同上冒烟有一条，实测 **0 处** | ✅ |
| 复用 `ui-primitives` 而非手搓 | 已声明并使用了 `Button`/`Checkbox`/`Switch`/`Tag`/`Pill`/`Input`/`Menu`/`Modal`/图标等 | ✅ |
| 圆角按角色选 token | **D1 说明有一处根本没生效**；其余待逐条核 | ❌ 见 D1 |

**老面板的写死色值（存量，非本轮引入）**：`ui-audit.mjs` 实测 ——
`KsSettingsSection.tsx` 73 处、`KsScopeChip.tsx` 4、`KsBookmarksTab.tsx` 3、`KsChannelsPanel.tsx` 3、
`KsEvidenceTab.tsx` 3、`KsArrowOverlay.tsx` 1、`KsDocTextView.tsx` 1、`KsFilesTab.tsx` 1。
⚠ 其中 `KsArrowOverlay.tsx` 的 `#e02020` 是**红线**（红色定位箭头，`NOT-DOING` 第 2 条），**不许动**。

---

## 用户场景与验收

### US1（P1）：填表说明必须读得全

**作为**要在设置里填云 OCR 凭据的用户，**我要**看清 Base URL 该怎么填，**以便**知道留空与输 `-` 的区别。

- **AC-1.1** 在 1018×853 与 1576×826 两档窗口下，Base URL 的 placeholder **完整可见**（不被裁切）。
- **AC-1.2** 该修复有**判据**（不是改完就算）：真浏览器量"输入框右缘 ≤ 容器内容盒右缘"。
- **AC-1.3** 判据必须**有牙**：把修复改回去 ⇒ 判据必红。

### US2（P1）：不许引用不存在的 token

**作为**维护者，**我要**每个 `var(--ks-*)` 都有定义，**以便**样式不静默失效。

- **AC-2.1** KS 源码里引用的每一个 `--ks-*` 都在 `ksGuideStyles.ts` 里有定义（或显式带兜底并说明）。
- **AC-2.2** 该判据进**门禁链**（`smoke-ui-scale.mjs` 或同等），不靠人记得跑。
- **AC-2.3** 变异验证：删掉一个 token 定义 ⇒ 判据必红。

### US3（P2）：逐面审查留痕

**作为**接手者，**我要**知道每个面"谁看过、看到什么"，**以便**不重复劳动。

- **AC-3.1** 每个被审查的面，在 `docs/UI-BASELINE.md` 有一行：面名 / 截图路径 / 看到的事实 / 结论。
- **AC-3.2** 没看到的面**必须写明"没看到"**（不许拿"没发现问题"冒充"看过"）。

---

## 范围与边界

**做**：
- D1 / D2 / D3 的修复 + 各自的判据（含变异验证）。
- 四个主面的离屏逐态审查 + 留痕。

**不做**（本轮明确排除，理由逐条）：
- **老面板的写死色值存量**（共 89 处）：换 token 需要**逐处语义判断**（哪个是危险红、哪个是警告黄），
  且其中有 `#c0392b55` 这种**带 alpha** 的（换 token 会丢透明度、把深色改得更糟）。
  `smoke-client-entry` 已有**只减不增**的棘轮看着它 ⇒ 本轮不动，**登记**。
- **红色定位箭头的颜色**（`NOT-DOING` 第 2 条红线）。
- **结构性大改**（`NOT-DOING` 第 4 条：小改直接改，大的先问）。
- **`tools/gov-qa/**` / `scripts/run-gates.ps1` / `specs/004` / `specs/006` / 公告更新组件**（并行三条线的写入面）。

## 依赖与风险

- **风险 1**：`KsSettingsSection.tsx` 属"公告发现"禁碰区的一部分吗？
  ⇒ **不是**。禁碰的是该文件里 `AnnounceTriageSection` 那一段（公告发现）；
  本轮改的是 `ChannelCredsRow`（云 OCR / LLM 凭据），**不同段**。
  ⚠ 但仍要**逐行确认改动不落在 `AnnounceTriageSection` 内**。
- **风险 2**：真宿主四个面进不去 ⇒ 那四个面的结论**只能**用离屏证据，**必须写明**。
