# Tasks: UI 图标体系与视觉规范收口（spec 008）

**Feature**: `008-icon-system` ｜ **Spec**: [spec.md](./spec.md) ｜ **Plan**: [plan.md](./plan.md)

**Created**: 2026-10-10

---

## 阶段 0：取证（已完成）

- [x] **T001** 官方图标契约取证（画布 / 描边档 / 默认尺寸）
  —— `var/tmp/icon-contract-audit.py` + `icon-defaults.py`。
  - **结果**：画布 `0 0 16 16`（94 次）；`Regular`=1px / `Medium`=1.3px；
    **17 个在用图标里 6 个默认 14、10 个默认 16** ⇒ D1 的根因。
- [x] **T002** 现状取证（尺寸分布 / 同容器混用 / 死声明 / 无障碍）
  —— `measure-icons.py` / `icon-system-audit.py` / `audit-icons.py` / `icon-a11y-audit.py`。
  - **结果**：kb 页 `{14:12, 16:17}`；同容器混用 1 处；死声明 13 条；**无障碍 0 处缺失**（合格）。
- [x] **T003** 外部规范调研（Ant Design / IBM）
  - **结果**：Ant Design「平衡」一节明写**弯曲/倾斜线条看起来更细需微调**、
    保持偶数去小数点；IBM 讲按用途选尺寸档。⇒ 只取方法论，**不搬素材**。

## 阶段 1+2：D2（放法）+ D1（尺寸）—— 必须一起做

- [x] **T010** 把进 `Button` 的图标改成走官方 `icon` prop（**25 处**，实测已改）
  —— `<Button icon={<IconXxx size={16} />} …>文字</Button>`。
  - **为什么与 T011 同批**：官方 `.icon` 槽是 16 的**容器**，图标**自己**仍按默认 size 渲染
    ⇒ 只套槽不传 size，默认 14 的图标**依旧 14**（外面多个 16 盒子反而更不对齐）。
  - **判据**：T012 的判据 ②。
- [x] **T011** KS 里所有图标**统一显式 `size`**（**43 处**："默认 14"的 6 类 + 其余没给 size 的）
  —— `IconChevronDown/Left/Right` / `IconChecklist` / `IconInfo` / `IconQuestion`。
  - **约束**：每处改完**实测几何**（`ui-render-shot` 的 `#kbtree` / `#dircols` / `#rows`）；
    撑破布局 ⇒ **回退该处并登记为例外**。
  - **判据**：T012 的判据 ①。
- [x] **T012** 新增 `plugin/scripts/smoke-icon-system.mjs`，三组判据（**已进 `smoke-all` 链**）
  —— ① 源码里所有 `<Icon…>` 必须显式给 `size`，且值 ∈ {16, 28}；
     ② `<Button>` 的 children 里不许有 `<Icon…>`（必须走 `icon` prop）；
     ③ `ksHostPrimitives.d.ts` 的图标集合 == 源码调用集合（**双向**）。
  - **判据**：进 `smoke-all.mjs` 的 `SUITES`（进门禁链）。
  - **变异**：三组**逐组**做（删一处 size / 塞回 children / 加一条死声明），各红一次。

## 阶段 3：D3（Medium 描边档）

- [x] **T020** 用 `…Medium`（1.3px）：左树**当前选中**行的文件夹图标（截图对照已做，见下）
  - **候选**：左树**当前选中**行图标、或主操作按钮。
  - **判据**：AC-3.2（使用处 > 0）。
  - ⚠ **若截图看下来 Medium 更差 ⇒ 如实登记"评估后不用"**，并把它从规范里去掉
    （**不许**为凑判据硬用）。

## 阶段 4：D4（清死声明）

- [x] **T030** 从 `ksHostPrimitives.d.ts` 删掉 **12 条**没人用的声明（第 13 条 `IconProps` 是类型、不是图标）
  —— `IconArchive*` / `IconChevronUpOutline14` / `IconChevronUpOutlineRegular` /
     `IconInspect*` / `IconNewChat*` / `IconQueue*` / `IconShield*` / `IconProps`。
  - **约束**：删前**逐条 grep**（`IconProps` 可能是类型别名、被间接引用 —— 看清再删）。
  - **判据**：`tsc` exit 0 + T012 判据 ③。

## 阶段 5：规范文档

- [x] **T040** 写 `docs/UI-ICON-SYSTEM.md`（图标体系唯一真源，含例外表与诚实边界）
  —— 尺寸档 / 描边档 / 放法 / 无障碍 / 例外表 / 判据入口。
  - **判据**：文档里每条规范都能在 `smoke-icon-system.mjs` 里找到对应判据（或**明确写明"暂无判据"**）。

## 阶段 6：收口

- [x] **T050** 重建交付产物 `plugin/client.js`；`tsc` exit 0。✅
- [x] **T051** 跑 `smoke-all`（**43/43**）+ `run-gates.ps1 -Full`（**10/10 · exit=0**）✅
  - ⚠ 门禁被占时退出码 3 = 有人在跑，**不并发**，等锁释放。
- [x] **T052** 小提交（`2c8fbf05` / `22ce077d` / `fd40b4e1`）+ 快照（`step-373-ui-icon-system-spec008`）+ 开发史 §10.234。✅
- [~] **T053** **派独立复核**（共享任务 `task-2`，冻结 `2c8fbf05`，`worker` 角色）⏳ 进行中
  —— 冻结 tag + 提取树；报告落 `docs/verify-briefs/`。
  - ⚠ **派活前先核对该角色的 deny 清单与任务书要求是否相容**（spec 007 的教训：
    派了 deny write/pwsh 的角色去做需要跑命令的复核）。

---

## 依赖关系

```
T001/T002/T003（取证）── 已完成
      ↓
T010 + T011（放法 + 尺寸，同批）→ T012（判据）
      ↓
T020（Medium 档）      T030（清死声明）
      ↓                    ↓
T040（规范文档）────────────────┘
      ↓
T050 → T051 → T052 → T053（收口）
```
