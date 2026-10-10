/**
 * ks-dsh-plugin — client/ksHostPrimitives.d.ts
 *
 * 宿主 `@deepseek-ai/dsh-client-ui-primitives` 的**最小面声明**。
 *
 * ## 为什么需要这个文件（不是偷懒，是构建事实）
 * 1. 这个包**在运行时是有的**：DSH 的 client loader 只把 9 个"平台单例"模块共享给冻结模块表，
 *    它就在其中（一手：`packages/client/web/src/seed.ts:36`
 *    `'@deepseek-ai/dsh-client-ui-primitives': UiPrimitives`，
 *    注释原话 "These are the ONLY entities the shell shares into the frozen module table"）。
 *    因此 import 它**能跑**，且拿到的是宿主自己的组件 —— 视觉与官方卡片**同源**，
 *    这正是我们要的（"和 DSH 保持相同风格"不该靠我抄像素）。
 * 2. 但**我们的 `plugin/node_modules/@deepseek-ai/` 里没有它**（实测只有 cordis/dsh-agent/
 *    dsh-tools 等宿主侧包）⇒ 直接 `import` 会让 `tsc --noEmit` 报 "Cannot find module"，
 *    把门禁打红。
 *
 * ⇒ 故在此声明**我们实际调用的那几个成员**：运行时是真货，类型上自持。
 * 这与 `ksSidebar.ts` 对 `@deepseek-ai/dsh-client-ui-sidebar-right` 的处理是同一个手法
 * （"只声明我们调用的成员"）。
 *
 * ## 声明依据（一手：**逐个读宿主源码**，不是从 README 的目录名猜的）
 *   `Button`   ← `ui-primitives/src/Button.tsx`
 *                `variant?: 'primary'|'ghost'|'outline'|'toolbar'`（**默认 `ghost`**）
 *                `size?: 'md'|'sm'`（md=36px 胶囊 / sm=28px 紧凑）、`icon?`、其余透传原生 button 属性
 *   `Checkbox` ← `Checkbox.tsx`：**强制 `label`**（可见 + 可访问名都在它身上），
 *                渲染 `<label><input type=checkbox/><span>{label}</span></label>`
 *   `Tag`      ← `Tag.tsx`：**只读**徽章，无 `onClick`/`active`；`tone` 8 档
 *   `Pill`     ← `Pill.tsx`：24px 胶囊；**给了 `onClick` 才是按钮**，否则是静态 span
 *   `Input`    ← `Input.tsx`：单行输入；`icon` 可选；渲染成 `<span class=wrap><input/></span>`
 *   `Menu`     ← `ui-sidebar-terminal/src/client/TerminalGuide.tsx` 的真实用法
 *   `IconChevronDownOutlineRegular` ← 同上
 *
 * ⚠ 边界（这条已真实踩过）：名字/取值写错**不会构建失败**（它是 external，esbuild 不校验命名导出），
 *    而是**运行时 undefined / 静默没有样式**。本文件曾把 Button 的 variant 写成
 *    `'secondary' | 'text'` —— 宿主**没有这两档**，写上去能过类型检查却拿不到填充。
 *    ⇒ 要用别的成员，**先读宿主源码确认导出名与取值**；冒烟另有一条钉住"我们只用了官方那 4 档"。
 *
 * ## ⚠ 2026-10-09 更正（自动续接链第 17 轮）—— 图标名随 DSH 升级改名，本文件当时漏改
 *
 * **事实**：`dbe39bc`（2026-09-28「DSH 升级后图标导出改名」）把**调用点**的 74 处
 * `Icon<Base>Outline14|16` 改成了 `Icon<Base>OutlineRegular`（新版 `ui-primitives/lib/index.js`
 * 只导出 `…OutlineRegular` / `…OutlineMedium` 两档，旧的像素后缀名**已不存在**），
 * 但**本声明文件没跟着改** ⇒ 调用点要的名字这里没声明、这里声明的名字调用点已不用
 * ⇒ `tsc --noEmit -p plugin/client` **红在 3 个文件 21 条**（TS2724/TS2305），从 `dbe39bc` 起
 * **连续 8 轮被当成"已知环境漂移、别修"**（见 `CHAIN-UNCLOSED-AUDIT.md` E1）。
 * 本轮查实：**调用点是对的、本文件是旧的** —— 不是环境问题，是这处漏改。
 *
 * **改法**：把本文件里 23 个旧图标名逐一对位改成 `…OutlineRegular`（`IconChevronUpOutline14`
 * 只出现在注释里，一并改），**非图标成员（Button/Checkbox/Tag/Pill/Input/Menu/Switch/Modal/Toast）
 * 一个字没动**。改完 `tsc` **exit=0**。
 *
 * **对位依据**（一手）：`D:\AI\DSH\deepseek-harness\packages\client\ui-primitives\lib\index.js`
 * 的 `export {…}` 块（282 个导出，逐个核过）—— 23 个新名**全部在**该导出列表里。
 * ⚠ 另实测：调用点从该模块 import 的 **23 个符号全部在宿主导出里**（含 17 个图标），
 * 即**源码侧零残留**（全仓 grep 旧名只剩本文件，已清）。
 * ⚠ 遗留：`IconInspect/IconShield/IconArchive/IconQueue/IconNewChat` 的 Regular 档**调用点已不再用**
 * （那几处 UI 后来改了/删了）—— **本次保留声明**（宿主确实导出它们，留着零风险、删了也不减错）。
 */

declare module '@deepseek-ai/dsh-client-ui-primitives' {
  import type { ButtonHTMLAttributes, ComponentType, InputHTMLAttributes, ReactNode } from 'react'

  /**
   * 宿主 Button 的视觉族（`Button.tsx` 的 `ButtonVariant`，**逐字抄**）。
   * ⚠ 只有这 4 档；`secondary`/`text` **不存在**。
   */
  export type DshButtonVariant = 'primary' | 'ghost' | 'outline' | 'toolbar'

  /** 宿主 Button。默认 `variant='ghost'`、`size='md'`；原生 button 属性透传。 */
  export interface DshButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    readonly variant?: DshButtonVariant
    readonly size?: 'md' | 'sm'
    readonly icon?: ReactNode
  }
  export const Button: ComponentType<DshButtonProps>

  /** 下拉箭头，用于菜单触发器。
   *  ⚠ **2026-10-10（spec 008）更正**：原来声明成 `ComponentType<{ readonly className?: string }>`
   *  ——**漏了 `size`**。而 `DshIconProps`（下面那个接口）逐字写着 `size?: number`。
   *  漏 size 的后果：**调用点传 `size={16}` 会 `tsc` 报 TS2322**（"Property 'size' does not exist"），
   *  逼着这一处只能用宿主默认值（**14**）⇒ 正是"同一排图标不齐"的一部分。
   *  ⇒ 改成与其他图标同一个 `DshIconProps`，口径统一。 */
  export const IconChevronDownOutlineRegular: ComponentType<DshIconProps>

  /**
   * 宿主图标集（`ui-primitives/src/icons/`，`IconProps = { size?: number; className?: string }`，
   * 颜色走 `currentColor` ⇒ 跟着我们的 token 走）。
   * ⚠ 只声明**我们真调用**的那几个；名字逐个在宿主 `lib/icons/index.js` 与包根导出里核过
   *   （写错不会构建失败，只会运行时 undefined —— 见本文件顶部的边界那条）。
   */
  export interface DshIconProps {
    /** 方形边长 px；默认是字形自己的设计尺寸。 */
    readonly size?: number
    readonly className?: string
  }
  /** 单行告知条的行首图标（与宿主告示同一语义）。 */
  export const IconInfoOutlineRegular: ComponentType<DshIconProps>
  /** 空态/补位卡用的「＋」与文件夹字形。 */
  export const IconPlusOutlineRegular: ComponentType<DshIconProps>
  export const IconFolderOpenOutlineRegular: ComponentType<DshIconProps>
  /**
   * **Medium 档**（1.3px 描边）—— 2026-10-10（spec 008 D3）首次启用。
   *
   * 官方为**每个**图标提供两档描边：`…Regular` = `strokeWidth 1`、
   * `…Medium` = `ICON_MEDIUM_STROKE = 1.3`（`ui-primitives/lib/index.js`，逐字）。
   * ⚠ 用途（**唯一用途**）：**当前选中**的行 —— 底色 + 字重之外，图标也重一档。
   *   实测对照：`var/tmp/ui-shots/medium-vs-regular-2x.png`（1.3px 确实更实）。
   * ⚠ **不要**拿它当"随便加粗"用：Regular 是默认档，Medium 只给"当前项/主操作"这类语义。
   *   KS 此前一次没用过这一档 ⇒ "当前选中"少了一档表达手段（这是本批补上的）。
   */
  export const IconFolderOpenOutlineMedium: ComponentType<DshIconProps>
  /** 危险动作（批量删除）用的垃圾桶。 */
  export const IconTrashOutlineRegular: ComponentType<DshIconProps>
  /**
   * 行尾溢出菜单的「⋮」（P1-1，2026-09-20）。
   * 名字逐字核过宿主 `ui-primitives/src/icons/index.tsx` 的 `export const IconEllipsisOutlineRegular`
   * 与 `lib/index.js` 的导出列表（**不是猜的**：这个包是 external，名字写错不会构建失败，
   * 只会运行时 undefined ⇒ 必须读源码/产物确认）。
   */
  export const IconEllipsisOutlineRegular: ComponentType<DshIconProps>
  /** 筛选条的行首图标（P1-4；语义 = "这一排是筛选"，同法核过宿主 `icons/index.tsx`）。
   *  ⚠ **2026-10-10（spec 008 T030）**：`IconInspectOutlineRegular` 的**调用点已不存在**
   *  （筛选条后来改用了别的图标）⇒ 按"只声明我们真调用的"**删掉**。 */
  /**
   * P2 头条（2026-09-20）新用的**行内文件图标** + 搜索框放大镜。
   * ⚠ **2026-10-10（spec 008 T030）就地收窄**：本段原有 5 个名字，其中
   *   `IconShieldOutlineRegular` / `IconArchiveOutlineRegular` 的**调用点已不存在**
   *   （那几处 UI 后来改了/删了）⇒ 按本文件自己的纪律「只声明**我们真调用**的那几个」**删掉**。
   *   原话留在这里（本仓规矩：删了什么要留痕）：
   *     「遗留：IconInspect/IconShield/IconArchive/IconQueue/IconNewChat 的 Regular 档调用点已不再用
   *       —— 本次保留声明（宿主确实导出它们，留着零风险、删了也不减错）」。
   *   ⚠ 那条"删了也不减错"的理由**不成立**：留着会让"声明集合 == 调用集合"这条判据**永远红**
   *     （或反过来逼着判据放宽口径），而且下一个人看到声明会以为**还在用**。
   *   ⇒ 现在删掉；将来要用再加回一行（宿主确实导出它们，加回的成本是一行）。
   *   判据见 `plugin/scripts/smoke-icon-system.mjs` 的 ③（双向集合相等）。
   */
  export const IconChecklistOutlineRegular: ComponentType<DshIconProps>
  export const IconListPenOutlineRegular: ComponentType<DshIconProps>
  export const IconSearchOutlineRegular: ComponentType<DshIconProps>
  /** 「在此范围内提问」按钮的问号（诊断 J1 换图标；名字逐字核过宿主 icons/*.d.ts 全集，
   *  宿主无对话气泡类图标 ⇒ 问号=提问最贴）。同边界：写错名字不构建失败、真机变 undefined。 */
  export const IconQuestionOutlineRegular: ComponentType<DshIconProps>
  /** 官方 Toast（批3-b 换装 A3 自绘临时条用）：{text, icon?, anchor?, holdMs?, onDone?}——
   *  瞬时提示件、到时自消。名字/形状核过宿主 `ui-primitives/src/Toast.tsx`（2026-09-22）。 */
  export const Toast: ComponentType<{
    text: string
    icon?: unknown
    anchor?: unknown
    holdMs?: number
    onDone?: () => void
  }>
  /** S2 办事台菜单行新增的图标（2026-09-22；名字逐字核过宿主 icons/*.d.ts 全集）。
   *  ⚠ **2026-10-10（spec 008 T030）**：`IconQueueOutlineRegular` / `IconNewChatOutlineRegular`
   *  的**调用点已不存在** ⇒ 按"只声明我们真调用的"**删掉**（原声明见 git 历史）。
   *  ⚠ 这里原写"另 3 枚上面已有声明 —— 我第一版补声明时撞了重复，已去重"：
   *  那句话说的是**当时的**去重，与本批删死声明是两件事，保留原文不改。
   *  同边界：写错名字不构建失败、真机变 undefined ⇒ 用前先核全集。 */
  export const IconPlanOutlineRegular: ComponentType<DshIconProps>
  export const IconClockOutlineRegular: ComponentType<DshIconProps>
  /**
   * 5h（2026-09-20）卡片带**左右翻页**用的两个箭头。
   * 名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js`
   * （一条命令数出来的候选全集：`IconChevronDownOutlineRegular` / `IconChevronLeftOutlineRegular` /
   *  `IconChevronRightOutlineRegular` / `IconChevronUpOutlineRegular` —— 左右两枚**真的在**导出里，
   *  同法核过 `const IconChevronLeftOutlineRegular` 的定义与 export 列表）。
   * ⚠ 同一条边界：写了不存在的名字**不会构建失败**，只会在真机变成 undefined（箭头整块消失）。
   */
  export const IconChevronLeftOutlineRegular: ComponentType<DshIconProps>
  export const IconChevronRightOutlineRegular: ComponentType<DshIconProps>
  /**
   * 第 3 步（2026-09-21）「刷新当前这一级」用的那枚。
   * 名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js` 的
   * `const IconRefreshOutlineRegular = …` 与同一文件的 export 列表（两处都在）。
   * ⚠ 同一条边界：写了不存在的名字**不会构建失败**，只会在真机变成 undefined（按钮只剩文字）。
   */
  export const IconRefreshOutlineRegular: ComponentType<DshIconProps>
  /**
   * 第 4 步（2026-09-21）新用的两枚：动作面板的**关掉**（×）与删除二次确认的**警告**。
   * 名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js` 的两条
   * `const IconCloseOutlineRegular = jsx("svg"…` / `const IconWarningOutlineRegular = jsxs("svg"…`
   * 与同一文件末尾的 export 列表（两处都在；`IconWarningOutlineRegular` 的默认 size 是 14）。
   * ⚠ 同一条边界：写了不存在的名字**不会构建失败**，只会在真机变成 undefined（图标整块消失）。
   */
  export const IconCloseOutlineRegular: ComponentType<DshIconProps>
  export const IconWarningOutlineRegular: ComponentType<DshIconProps>

  /** 宿主 Menu 的一项。 */
  export interface DshMenuItem {
    readonly id: string
    readonly label: string
    readonly disabled?: boolean
  }

  /** 宿主 Menu（`anchor` + `portal` = 锚在触发器旁的门户浮层，样式由宿主负责）。 */
  export interface DshMenuProps {
    readonly open: boolean
    readonly portal?: boolean
    readonly autoFocus?: boolean
    readonly align?: 'start' | 'end'
    readonly className?: string
    readonly items: readonly DshMenuItem[]
    readonly selectedId?: string
    readonly anchor?: ReactNode
    readonly onClose?: () => void
    readonly onSelect?: (id: string) => void
  }
  export const Menu: ComponentType<DshMenuProps>

  /**
   * 宿主 Checkbox。**`label` 是必填**（它既是可见文字也是可访问名）。
   *
   * 官方只在"带标签的选项"场景用它（全体源码里只有 `ui-settings-models` 一处引用），
   * **没有"无标签行勾选"的先例** ⇒ 我们做列表多选时把**文件名当作它的 label**：
   * 可访问名 = 文件名，且名字只渲染一次（不重复）。
   */
  export interface DshCheckboxProps {
    readonly checked: boolean
    readonly onChange: (next: boolean) => void
    readonly label: string
    readonly disabled?: boolean
    readonly title?: string | undefined
    readonly className?: string | undefined
  }
  export const Checkbox: ComponentType<DshCheckboxProps>

  /** 宿主 Tag 的色调（`Tag.tsx` 的 `TagTone`，**逐字抄**）。 */
  export type DshTagTone =
    | 'outline' | 'solid' | 'neutral' | 'quiet'
    | 'success' | 'info' | 'warning' | 'danger'

  /** 宿主 Tag：**只读**胶囊徽章（11px）。要可点的用 `Pill`。 */
  export const Tag: ComponentType<{
    readonly tone?: DshTagTone
    readonly className?: string | undefined
    readonly children?: ReactNode
  }>

  /**
   * 宿主 Pill：24px 胶囊。**给了 `onClick` 才是 button**，否则渲染静态 span。
   * （注释原文：size 与交互性一起把 `Pill` 与 `Tag` 分开。）
   */
  export const Pill: ComponentType<{
    readonly active?: boolean
    readonly className?: string | undefined
    readonly children?: ReactNode
  } & ButtonHTMLAttributes<HTMLButtonElement>>

  /** 宿主 Input：单行输入（搜索框/行内表单）。多行输入**不是**这个原语。 */
  export const Input: ComponentType<{
    readonly icon?: ReactNode
    readonly className?: string
  } & InputHTMLAttributes<HTMLInputElement>>

  /**
   * 宿主 Switch：**完全受控**的开关（`Switch.tsx`）。
   * `label` 是**可访问名**（与 Checkbox 不同，它不渲染可见文字? —— 源码里它在 `<span>` 里）⇒ 必须传。
   */
  export interface DshSwitchProps {
    readonly checked: boolean
    readonly onChange: (next: boolean) => void
    readonly label: string
    readonly disabled?: boolean
    readonly title?: string | undefined
    readonly className?: string | undefined
  }
  export const Switch: ComponentType<DshSwitchProps>

  /**
   * 宿主 Modal：一个完整对话框（`Modal.tsx`）。
   * ⚠ 它用 `createPortal` 把内容投到 `document.body` ⇒ 断言"窗里有什么"时**别只查容器**。
   * ⚠ `closeLabel` **必填**（源码里没有默认值）：本地化后的关闭按钮可访问名。
   */
  export interface DshModalProps {
    readonly open: boolean
    readonly onClose: () => void
    readonly title: string
    readonly closeLabel: string
    readonly description?: string
    readonly children?: ReactNode
    readonly footer?: ReactNode
    readonly className?: string
    readonly contentClassName?: string
    readonly headless?: boolean
  }
  export const Modal: ComponentType<DshModalProps>
}
