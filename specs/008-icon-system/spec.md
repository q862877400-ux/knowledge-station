# Feature Specification: UI 图标体系与视觉规范收口

**Feature Branch**: `008-icon-system`

**Created**: 2026-10-10

**Status**: Draft

**Input**: 业主指令「按照你推荐的方式改，调研图标美学设计的资料，按照 spec 规范，设置好目标，全自动推进…最后实现 UI 设计规范，使用方便，美观整洁」

---

## 背景：为什么需要这个特性

上一批（spec 007）修的是"**错了**"（不存在的 token、被截断的说明）。
业主这次把要求提到了**规范层**：**图标美学** + **UI 设计规范** + **使用方便、美观整洁**。

本节每条都是**实测**，不是推测。复算命令随条给出。

### 一、调研到的权威依据（不是我的口味）

| 来源 | 关键结论 | 对本项目的约束 |
|---|---|---|
| **DSH 官方 `ui-primitives` 实现**（`lib/index.js`，本项目**必须遵守**） | ① 每个图标是 `viewBox="0 0 16 16"` 的 **16 画布**（出现 94 次）；② 每个图形有**两档描边**：`…Regular`（strokeWidth **1**）与 `…Medium`（**1.3**）；③ **每个图标各自的默认 size 不同** | 尺寸与描边是**官方给的表达手段** |
| **官方 `Button.module.css`** | `.icon{width:16px;height:16px}` —— 官方按钮的图标槽**固定 16** | 放进 Button 的图标应走 `icon` prop |
| [Ant Design 图标规范](https://raw.githubusercontent.com/ant-design/ant-design/3592c00ac4f94d7a50bc50eff4094513884fbfec/docs/spec/icon.zh-CN.md) | **"平衡"**一节：**弯曲的线条比竖直的线条看起来细**、**倾斜的线条也比竖直的看起来细** ⇒ 需要**微调**；"形式/韵律/平衡/辨识"四原则；**保持偶数、去小数点** | 图标尺寸**必须是偶数**；不同形状要视觉补偿 |
| [IBM Design Language · App icons](https://www.ibm.com/design/language/iconography/app-icons/usage/) | 图标按**网格**设计、按**用途**选尺寸档 | 同一用途用同一档 |

> ⚠ 引用为**外部资料**，只取方法论（网格/偶数/视觉平衡），**不搬任何图形素材**。

### 二、实测：本项目的图标现状

#### 2.1 ✅ 健康的（不用改）

| 检查 | 结果 | 复算 |
|---|---|---|
| 调用了但宿主**没有**该图标 | **0** | `python var/tmp/audit-icons.py` |
| 调用了但自己**没声明** | **0** | 同上 |
| 纯图标按钮**缺无障碍标注**（无 `aria-label` 且无 `title`） | **0** | `python var/tmp/icon-a11y-audit.py` |

#### 2.2 ❌ D1：图标尺寸不成体系（**根因是宿主默认值不统一**）

**实测**（`python var/tmp/icon-defaults.py`）：KS 用到的 17 个图标里，

| 宿主默认尺寸 | 图标 | 个数 |
|---|---|---|
| **14px** | `IconChecklistOutline` / `IconChevronDownOutline` / `IconChevronLeftOutline` / `IconChevronRightOutline` / `IconInfoOutline` / `IconQuestionOutline` | **6** |
| **16px** | `IconClockOutline` / `IconCloseOutline` / `IconEllipsisOutline` / `IconFolderOpenOutline` / `IconListPenOutline` / `IconPlusOutline` / `IconRefreshOutline` / `IconSearchOutline` / `IconTrashOutline` / `IconWarningOutline` | **10** |

⇒ **同一个按钮排里，尺寸天生就不齐**：知识库页的
「返回上一层」（`IconChevronLeft`，**14**）紧挨着
「新建下级目录 / 上传到这一层 / 刷新」（`IconPlus` / `IconRefresh`，**16**）。

**实测分布**（`python var/tmp/measure-icons.py`）：kb 页 `{14: 12, 16: 17}`；
同一落点类名下混用两种尺寸 **1 处**（`ks-tree-name` = `{16:5, 14:1}`）。

⚠ **这是宿主的默认值差异，不是 KS 写错**。但**用户看到的是不齐** ⇒ KS 要负责统一。

#### 2.3 ❌ D2：官方 Button 的 `icon` 槽**从未被使用**

- 官方 `Button` 有 `icon` prop（JSDoc 逐字：*optional leading 16px icon node*），
  用它会自动套 `.icon`（16×16）槽。
- **KS 用了 0 处**（`grep '<Button[^>]*\bicon='` = 0），全部把图标塞进 `children`
  ⇒ 尺寸**完全取决于图标自己的默认值** ⇒ 直接导致 D1。

#### 2.4 ❌ D3：官方 `Medium` 描边档（1.3px）**从未被使用**

KS 调用的 17 个图标**全是 `…Regular`**（1px），`Medium` **0 处**。
⇒ 官方提供的"视觉更重"手段（1.3px 描边，用于**当前选中**、**主操作**等位置）
一次没用过 —— 这些位置现在只能靠颜色区分，**少了一档表达**。

#### 2.5 ⚠ D4：13 条**死图标声明**

`ksHostPrimitives.d.ts` 声明 30 个，实际只用 17 个 ⇒ **13 条没人用**：
`IconArchive` / `IconArchiveOutlineRegular` / `IconChevronUpOutline14` /
`IconChevronUpOutlineRegular` / `IconInspect` / `IconInspectOutlineRegular` /
`IconNewChat` / `IconNewChatOutlineRegular` / `IconProps` /
`IconQueue` / `IconQueueOutlineRegular` / `IconShield` / `IconShieldOutlineRegular`。

⚠ 该文件头自己写着纪律「**只声明我们调用的**」⇒ 这 13 条**违反了它自己的纪律**。

#### 2.6 ⚠ D5：`IconCapabilityPage` 的 `<Icon size={14} />` 是**奇数/非基准值**

`KsCapabilityPage.tsx:83` 显式传 `size={14}` —— 14 是**偶数**（合格），
但它**不是 16 画布的基准**。Ant Design 规范要求"保持偶数"它满足，
但"同一页面同用途用同一档"它不满足（该页其余图标是 16）。

### 三、要建立什么规范（本 spec 的产出）

**`docs/UI-ICON-SYSTEM.md`**（新文件，图标体系唯一真源），内容：

1. **尺寸档**：KS 只用 **16**（官方基准）一档；**例外**只有"空态大图标"（28，已有）与
   "办事台菜单行图标"（需定案）。
2. **描边档**：`Regular`（1px）为默认；**选中/主操作**可用 `Medium`（1.3px）——
   并**实际用起来**（至少一处示范）。
3. **放法**：进 `Button` 的图标**一律走 `icon` prop**（官方槽），不塞 `children`。
4. **无障碍**：纯图标按钮**必须**有 `aria-label`（现状已 100% 合格，写成规范防回退）。
5. **判据**：机械检查（见下）。

### 四、用户场景与验收

#### US1（P1）：同一排按钮的图标大小必须一致

**作为**使用者，**我要**同一排按钮的图标看起来一样大，**以便**界面显得整齐。

- **AC-1.1** kb 页工具栏那一排（返回上一层 / 新建下级目录 / 上传到这一层 / 刷新）
  图标**全部 16**。
- **AC-1.2** 该修复有**机械判据**：真渲染 DOM 里，同一 `ks-*` 容器下的 svg 尺寸**只有一种**。
- **AC-1.3** 判据**有牙**：把某处改回不传 size ⇒ 必红。

#### US2（P1）：图标放法走官方槽

- **AC-2.1** 进 `Button` 的图标使用 `icon` prop（官方 16px 槽）。
- **AC-2.2** 有机械判据：KS 源码里 `<Button ...>` 内含 `<Icon…>` 子元素的形式**归零**。

#### US3（P2）：描边档用起来

- **AC-3.1** 至少一处"选中/主操作"用 `Medium` 档，并在文档里说明为什么是它。
- **AC-3.2** 有判据：`Medium` 使用处 > 0（防"文档写了没人用"）。

#### US4（P2）：死声明清零

- **AC-4.1** `ksHostPrimitives.d.ts` 的声明集合 == 实际调用集合（**双向**）。
- **AC-4.2** 判据有牙：加一条死声明 ⇒ 必红。

### 五、范围与边界

**做**：D1–D5 的修复 + 规范文档 + 机械判据（含变异验证）+ 截图留痕。

**不做**：
- **不改宿主**（`ui-primitives` 是官方包，我们只消费）⇒ 14/16 的默认值差异**只能由 KS 侧统一**。
- **不搬任何外部图形素材**（Ant Design / IBM 只取方法论）。
- **不碰**并行线写入面（`tools/gov-qa/**`、`scripts/run-gates.ps1`、`specs/004`、`specs/006`、公告组件）。
- **不做结构性大改**（`NOT-DOING` 第 4 条）。

### 六、依赖与风险

| 风险 | 对策 |
|---|---|
| 统一到 16 会让某些紧凑处（如树箭头、目录箭头）变大、可能撑破布局 | 每处改完**实测几何**（`ui-render-shot` 已有 `#kbtree` / `#dircols` / `#rows` 量点）；撑破就回退该处并**登记为例外** |
| `Medium` 档引入新的视觉差异 | 只用在"选中/主操作"，且**截图对照** |
| 删死声明可能删掉"将来要用"的 | 按本仓纪律"只声明我们调用的"删；需要时再加回（一条 import 的成本） |
| 判据写成恒真 | 每条判据**逐条做变异** |
