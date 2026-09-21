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
 *   `IconChevronDownOutline14` ← 同上
 *
 * ⚠ 边界（这条已真实踩过）：名字/取值写错**不会构建失败**（它是 external，esbuild 不校验命名导出），
 *    而是**运行时 undefined / 静默没有样式**。本文件曾把 Button 的 variant 写成
 *    `'secondary' | 'text'` —— 宿主**没有这两档**，写上去能过类型检查却拿不到填充。
 *    ⇒ 要用别的成员，**先读宿主源码确认导出名与取值**；冒烟另有一条钉住"我们只用了官方那 4 档"。
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

  /** 14px 下拉箭头，用于菜单触发器。 */
  export const IconChevronDownOutline14: ComponentType<{ readonly className?: string }>

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
  export const IconInfoOutline14: ComponentType<DshIconProps>
  /** 空态/补位卡用的「＋」与文件夹字形。 */
  export const IconPlusOutline16: ComponentType<DshIconProps>
  export const IconFolderOpenOutline16: ComponentType<DshIconProps>
  /** 危险动作（批量删除）用的垃圾桶。 */
  export const IconTrashOutline16: ComponentType<DshIconProps>
  /**
   * 行尾溢出菜单的「⋮」（P1-1，2026-09-20）。
   * 名字逐字核过宿主 `ui-primitives/src/icons/index.tsx` 的 `export const IconEllipsisOutline16`
   * 与 `lib/index.js` 的导出列表（**不是猜的**：这个包是 external，名字写错不会构建失败，
   * 只会运行时 undefined ⇒ 必须读源码/产物确认）。
   */
  export const IconEllipsisOutline16: ComponentType<DshIconProps>
  /** 筛选条的行首图标（P1-4；语义 = "这一排是筛选"，同法核过宿主 `icons/index.tsx`）。 */
  export const IconInspectOutline12: ComponentType<DshIconProps>
  /**
   * P2 头条（2026-09-20）新用的 4 个**行内文件图标** + 1 个搜索框放大镜。
   * 五个名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js`（**const 定义与
   * export 列表都在**，一条命令核的）：
   *   `const IconShieldOutline16 = ` / `export { … IconShieldOutline16 … }` 同理其余四个。
   * ⚠ 为什么必须核：这个包在我们的构建里是 **external** ⇒ 名字写错**不会构建失败**，
   *   只会在真机运行时变成 undefined（图标整块消失），见本文件顶部那条边界。
   *   `src/index.ts:77` 的 `export * from './icons/index.tsx'` 把它们抬到包根 ⇒ 可 import。
   */
  export const IconShieldOutline16: ComponentType<DshIconProps>
  export const IconChecklistOutline14: ComponentType<DshIconProps>
  export const IconListPenOutline16: ComponentType<DshIconProps>
  export const IconArchiveOutline20: ComponentType<DshIconProps>
  export const IconSearchOutline16: ComponentType<DshIconProps>
  /**
   * 5h（2026-09-20）卡片带**左右翻页**用的两个箭头。
   * 名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js`
   * （一条命令数出来的候选全集：`IconChevronDownOutline14` / `IconChevronLeftOutline14` /
   *  `IconChevronRightOutline14` / `IconChevronUpOutline14` —— 左右两枚**真的在**导出里，
   *  同法核过 `const IconChevronLeftOutline14` 的定义与 export 列表）。
   * ⚠ 同一条边界：写了不存在的名字**不会构建失败**，只会在真机变成 undefined（箭头整块消失）。
   */
  export const IconChevronLeftOutline14: ComponentType<DshIconProps>
  export const IconChevronRightOutline14: ComponentType<DshIconProps>
  /**
   * 第 3 步（2026-09-21）「刷新当前这一级」用的那枚。
   * 名字逐字核过宿主检出 `packages/client/ui-primitives/lib/index.js` 的
   * `const IconRefreshOutline16 = …` 与同一文件的 export 列表（两处都在）。
   * ⚠ 同一条边界：写了不存在的名字**不会构建失败**，只会在真机变成 undefined（按钮只剩文字）。
   */
  export const IconRefreshOutline16: ComponentType<DshIconProps>

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
