# Implementation Plan: UI 图标体系与视觉规范收口（spec 008）

**Feature**: `008-icon-system` ｜ **Spec**: [spec.md](./spec.md)

**Created**: 2026-10-10

---

## 一、技术上下文

| 项 | 值 |
|---|---|
| 语言/框架 | TypeScript + React 18（客户端插件，ESM） |
| 图标来源 | **宿主的 `@deepseek-ai/dsh-client-ui-primitives`**（官方包，我们只消费、不改） |
| 图标契约 | `viewBox="0 0 16 16"`；`…Regular` = 1px 描边 / `…Medium` = 1.3px；**每个图标各自有默认 size（14 或 16）** |
| 类型声明 | `plugin/client/ksHostPrimitives.d.ts`（我们自己维护，因为宿主 `.d.ts` 只声明 15 个 Icon） |
| 交付产物 | `plugin/client.js`（`build-client.mjs` 构建，必须与源码同步） |
| 判据通道 | ① `ui-render-shot.mjs`（真浏览器 DOM 读数）；② `smoke-client-entry.mjs`（产物字面量 + 棘轮）；③ 新增 `smoke-icon-system.mjs`（源码级） |
| 门禁 | `pwsh -File scripts/run-gates.ps1 -Full` |

## 二、宪法检查（`.specify/memory/constitution.md`）

- **原则 VI「只做缝合不做发明」**：尺寸/描边都**用官方已有的**（16 基准 + Medium 档），不新造图形、不新造 token。
- **判据要有牙**：每条修复配一条能被打红的判据。
- **诚实边界**：改不动的（宿主默认值差异）要写明"由 KS 侧统一"，不冒充"宿主已修"。

## 三、阶段划分

### 阶段 0：取证（已完成，登记在 spec §二）

- 官方契约（画布/描边/默认值）—— `var/tmp/icon-contract-audit.py`、`icon-defaults.py`
- 现状（尺寸分布/混用/死声明/无障碍）—— `measure-icons.py`、`icon-system-audit.py`、`audit-icons.py`、`icon-a11y-audit.py`
- 外部规范调研 —— Ant Design 图标规范（平衡/韵律/偶数）、IBM App icons

### 阶段 1：D2（放法）—— 最根本，先做

**为什么先做它**：D1（尺寸不齐）的**根因**是"图标没走官方 `icon` 槽"。
先修放法，尺寸统一就是**顺带的结果**，而不是逐个打补丁。

**改法**：把 `<Button …><IconXxx />文字</Button>` 改成
`<Button icon={<IconXxx />} …>文字</Button>`（官方 JSDoc：*optional leading 16px icon node*）。

⚠ **但要注意**：官方 `.icon` 槽是 16×16 的**容器**，而图标**自己**仍按默认 size 渲染
（实测：套槽后仍是 16×16 —— 因为 `.icon` 的 16px 盒子里放 16 的 svg 正好）。
⇒ 对**默认 14** 的图标（`IconChevronLeft` 等），套槽**仍会是 14**
（svg 按自己的默认渲染，只是外面多了个 16 的盒子，**视觉上会偏小且不对齐**）。
⇒ **所以 D2 与 D1 必须一起做**：套槽 **+ 显式 `size={16}`**。

### 阶段 2：D1（尺寸统一到 16）

**逐处**处理 KS 里"默认 14"的 6 个图标：
`IconChevronDown/Left/Right` / `IconChecklist` / `IconInfo` / `IconQuestion`。

⚠ **每处改完必须实测几何**（`ui-render-shot` 的 `#kbtree` / `#dircols` / `#rows` 量点），
确认没撑破布局。撑破就**回退该处并登记为例外**（写进规范文档的例外表）。

### 阶段 3：D3（Medium 档用起来）

挑**一处**真正合适的（候选：左树**当前选中**行、或主操作按钮），
用 `…Medium`（1.3px），并**截图对照** Regular 版。

⚠ 若截图看下来 Medium 反而更差 ⇒ **如实登记"评估后不用"**，并把它从规范里去掉
（**不许**为凑判据而硬用）。

### 阶段 4：D4（清死声明）

从 `ksHostPrimitives.d.ts` 删 13 条没人用的声明（含 `IconProps` 等基名）。
⚠ 删之前**逐条 grep 确认**（`IconProps` 可能是类型别名、被间接用到 —— 要看清再删）。

### 阶段 5：规范文档 + 判据

**文档**：`docs/UI-ICON-SYSTEM.md`（唯一真源）。

**判据**：新增 `plugin/scripts/smoke-icon-system.mjs`，三组：
1. **尺寸**：KS 源码里所有 `<Icon…>` **必须显式给 `size`**（或用统一常量），
   且值 ∈ {16, 28}（16 基准 + 空态大图）。变异：删一处 size ⇒ 红。
2. **放法**：`<Button>` 的 children 里**不许**出现 `<Icon…>`。变异：塞回去 ⇒ 红。
3. **声明一致性**：`ksHostPrimitives.d.ts` 的图标集合 == 源码调用集合（**双向**）。
   变异：加一条死声明 ⇒ 红。

⚠ 该脚本进 `smoke-all.mjs` 的 `SUITES`（进冒烟链 = 进门禁）。

### 阶段 6：收口

- 重建 `plugin/client.js`
- 跑 `smoke-all` + `run-gates.ps1 -Full`
- 小提交 + 快照 + 开发史登记
- **派独立复核**（改了共享样式 + 新增判据 ⇒ 属必验类别）

## 四、交付物

| 产物 | 落点 |
|---|---|
| 修复 | `plugin/client/*.tsx`（图标放法与尺寸）、`plugin/client/ksHostPrimitives.d.ts`（清死声明） |
| 规范 | `docs/UI-ICON-SYSTEM.md`（新） |
| 判据 | `plugin/scripts/smoke-icon-system.mjs`（新）+ `smoke-all.mjs` 名单 |
| 留痕 | `docs/UI-BASELINE.md` §5ab、`docs/DEVELOPMENT-HISTORY.md` §10.234 |
| 证据 | `var/tmp/ui-shots/`（截图，不入库） |

## 五、风险与对策

| 风险 | 对策 |
|---|---|
| 统一 16 撑破紧凑布局 | 逐处实测几何；撑破就登记例外（**不许**硬改导致别的红） |
| `icon` prop 在 sm 档下的表现与预期不同 | **实测**（真浏览器量 svg 与按钮的关系），不靠推理 |
| 判据恒真 | 每条**逐条变异** |
| 改 `ksHostPrimitives.d.ts` 影响类型检查 | 改完跑 `tsc`；`IconProps` 之类先确认用途 |
| 门禁被并行线占用 | 退出码 3 = 有人在跑，**不并发**，等锁释放 |
