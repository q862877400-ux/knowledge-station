# UI 图标体系（KnowledgeStation 插件）

> **本文件是 KS 图标用法的唯一真源**。改图标用法前先读它；改完跑
> `node plugin/scripts/smoke-icon-system.mjs`（已在门禁链里）。
>
> 归属层：**规范与例外 → 本文件**；做过什么/为什么 → [开发史](DEVELOPMENT-HISTORY.md)；
> 尺度与留边 → [UI-BASELINE](UI-BASELINE.md)。

---

## 一、图标从哪来（契约，逐字取自宿主实现）

KS **不自己画图标**，全部用宿主的 `@deepseek-ai/dsh-client-ui-primitives`。
它的图标契约（`packages/client/ui-primitives/lib/index.js`，实测）：

| 项 | 值 |
|---|---|
| 画布 | `viewBox="0 0 16 16"`（出现 94 次） |
| 描边两档 | `…Regular` = `strokeWidth 1`；`…Medium` = `ICON_MEDIUM_STROKE` = **1.3** |
| 默认尺寸 | **每个图标各自不同**（实测：KS 用到的 18 个里，**6 个默认 14**、**12 个默认 16**） |
| 颜色 | `currentColor` ⇒ 自动跟随我们的主题 token |

⚠ **"每个图标默认尺寸不同"是本文件存在的直接原因**（见第三节 D1）。

## 二、四条规范

### R1 尺寸：**只用 16**（唯一例外：空态大图 28）

- **16** = 官方画布基准档 ⇒ **每个 `<Icon…>` 都要显式写 `size={16}`**。
- **28** = 空态卡里的大图标（`.ks-empty-ico`），是**刻意的另一档**。
- ❌ **不许不写 size**：不写就会吃"那个图标自己的默认值"（14 或 16）⇒ 同一排里不齐。
- ❌ **不许写别的数**（14 / 18 / 20 / 24）：既不在官方档上，也会破坏同排一致性。

### R2 描边：`Regular` 是默认，`Medium` 只给**当前选中 / 主操作**

- 默认一律 `…Regular`（1px）。
- **`…Medium`（1.3px）只用于"当前项"这类需要更重的语义** ——
  例如左树**当前选中**那一行的文件夹图标（底色 + 字重之外，图标也重一档）。
- ❌ 不许拿 Medium 当"随便加粗"用。
- 实测对照图：`var/tmp/ui-shots/medium-vs-regular-2x.png`（1.3px 在同一形状上确实更实）。

### R3 放法：进 `Button` 的图标走官方 `icon` prop

```tsx
// ✅ 对：官方 icon prop（JSDoc 逐字：optional leading 16px icon node）
<Button icon={<IconPlusOutlineRegular size={16} />} variant="outline" size="sm">新建下级目录</Button>

// ❌ 错：塞进 children（尺寸完全取决于图标自己的默认值）
<Button variant="outline" size="sm"><IconPlusOutlineRegular size={16} />新建下级目录</Button>
```

- 官方 `Button` 有 `.icon` 槽（`width:16px;height:16px`），走 `icon` prop 才会用它。
- ⚠ 官方 `icon` 语义是 **leading**（图标在文字**前**）；图标在文字后的按钮**不适用**这条，
  按 R1 显式给 size 即可。

### R4 无障碍：纯图标按钮**必须**有 `aria-label`

- 只有图标、没有可见文字的按钮，必须有 `aria-label`（或 `title`）。
- 现状：**实测 0 处缺失**（合格）。写进规范是为了**防回退**。

## 三、为什么有这些规范（实测证据）

### D1 同一排图标不齐 —— 根因是**宿主默认值分两档**

实测（`var/tmp/icon-defaults.py`）：KS 用到的图标里

| 宿主默认 | 图标 |
|---|---|
| **14** | `IconChecklistOutline` / `IconChevronDownOutline` / `IconChevronLeftOutline` / `IconChevronRightOutline` / `IconInfoOutline` / `IconQuestionOutline` |
| **16** | 其余（`IconPlus` / `IconRefresh` / `IconFolderOpen` / `IconTrash` / …） |

⇒ 知识库页工具栏里「返回上一层」（`IconChevronLeft`，**14**）紧挨着
「新建下级目录 / 上传到这一层 / 刷新」（**16**）—— **用户看到的就是不齐**。

**这不是 KS 写错，是默认值差异**；但**用户不会管是谁的默认值** ⇒ KS 侧统一到 16。

**修前/修后实测**（`var/tmp/measure-icons.py`，kb 页）：

| | 14px | 16px |
|---|---|---|
| 修前 | 12 | 17 |
| 修后 | **0** | **29** |

### D2 `Button` 的 `icon` 槽从没被用过

实测：`grep '<Button[^>]*\bicon='` = **0 处**（修前）⇒ 图标尺寸完全失控。

### D3 `Medium` 档从没被用过

实测：KS 调用的图标**全是 `…Regular`**，`Medium` **0 处** ⇒
"当前选中"少了一档表达手段。本批**首次启用**（左树当前选中行）。

### D4 死声明

`ksHostPrimitives.d.ts` 曾声明 30 个、只用 17 个 ⇒ **13 条死声明**。
该文件头自己写着「只声明**我们真调用**的那几个」⇒ 违反了自己的纪律。已清零。

## 四、判据（机械检查，进冒烟链）

`plugin/scripts/smoke-icon-system.mjs` 三组：

| 组 | 判什么 | 变异验证（实测） |
|---|---|---|
| ① | 每个 `<Icon…>` 显式给 `size`，且值 ∈ {16, 28} | 删一处 size ⇒ **红** |
| ② | `Button` 的 children 里不许有 `<Icon…>` | 塞回 children ⇒ **红** |
| ③ | `ksHostPrimitives.d.ts` 的声明集合 **==** 源码调用集合（双向） | 加一条死声明 ⇒ **红** |

⚠ **判据③的口径**：只认真正的 `export const IconXxx` 行 ——
**注释里提到的名字不算声明**（第一版扫全文关键词，把留痕注释里的名字算成声明，
报出 12 条**并不存在**的死声明 = 假红；已修）。

## 五、例外表（**唯一允许偏离 R1/R2 的地方，逐条带理由**）

| 处 | 偏离 | 理由 |
|---|---|---|
| `.ks-empty-ico` 里的空态图标 | `size={28}` | 空态卡是**大留白**场景，16 在里面小到看不见；28 是刻意的大档（非默认值、非拍脑袋） |

⚠ 本表**目前只有这一条**。要加例外必须先证明"16 真的不能用"（撑破布局 / 看不见），
并在本表登记理由 —— **不许**为了让判据变绿而加。

## 六、诚实边界

1. **判据①只保证"显式给了 size 且在允许档里"，不保证渲染出来真的是那个尺寸**。
   真渲染尺寸由 `ui-render-shot.mjs` 的 DOM 读数负责（两者分工，见 UI-BASELINE §五）。
2. 图标读数来自**离屏渲染**（真 Edge + 真组件），**不是真宿主**（原因见 UI-BASELINE §五）。
3. **宿主自己的默认值差异不归我们改**（`ui-primitives` 是官方包，我们只消费）；
   本规范管的是"**KS 侧统一到 16**"。
4. 外部资料（[Ant Design 图标规范](https://raw.githubusercontent.com/ant-design/ant-design/3592c00ac4f94d7a50bc50eff4094513884fbfec/docs/spec/icon.zh-CN.md)、
   [IBM App icons](https://www.ibm.com/design/language/iconography/app-icons/usage/)）
   只取**方法论**（网格、偶数、视觉平衡、按用途选档），**不搬任何图形素材**。
