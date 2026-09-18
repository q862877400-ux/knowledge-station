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
 *    因此 import 它**能跑**，且拿到的是宿主自己的 `Button`/`Menu` —— 视觉与官方卡片**同源**，
 *    这正是我们要的（"和 DSH 保持相同风格"不该靠我抄像素）。
 * 2. 但**我们的 `plugin/node_modules/@deepseek-ai/` 里没有它**（实测只有 cordis/dsh-agent/
 *    dsh-tools 等宿主侧包）⇒ 直接 `import` 会让 `tsc --noEmit` 报 "Cannot find module"，
 *    把门禁打红。
 *
 * ⇒ 故在此声明**我们实际调用的那几个成员**：运行时是真货，类型上自持。
 * 这与 `ksSidebar.ts` 对 `@deepseek-ai/dsh-client-ui-sidebar-right` 的处理是同一个手法
 * （"只声明我们调用的成员"，见其 `KsSidebarRight`/`KsTabRegistry`）。
 *
 * ## 声明依据（一手，不是猜的）
 * 形状逐条取自宿主**已发货的** `ui-sidebar-terminal/src/client/TerminalGuide.tsx`
 * —— 它就是用这三个成员做出「新建终端」那张带 ▾ 的卡（业主指名要照它做）：
 *   `<Button variant="ghost" className onClick>…</Button>`
 *   `<Menu open portal autoFocus align="end" items={[{id,label,disabled}]} selectedId onClose onSelect anchor />`
 *   `<IconChevronDownOutline14 />`
 *
 * ⚠ 边界：只声明了**用到的**成员。要用别的（如 `IconXxx16`）请**先读宿主源码确认导出名**——
 *    名字写错不会构建失败（它是 external，esbuild 不校验命名导出），而是**运行时 undefined**。
 */

declare module '@deepseek-ai/dsh-client-ui-primitives' {
  import type { ComponentType, CSSProperties, MouseEvent, ReactNode } from 'react'

  /** 宿主 Button。`variant="ghost"` 用于无底色可点区域（官方卡片的写法）。 */
  export interface DshButtonProps {
    readonly variant?: 'ghost' | 'primary' | 'secondary' | 'text'
    readonly className?: string
    readonly style?: CSSProperties
    readonly disabled?: boolean
    readonly onClick?: (event: MouseEvent<HTMLButtonElement>) => void
    readonly 'aria-label'?: string
    readonly 'aria-haspopup'?: 'menu' | boolean
    readonly 'aria-expanded'?: boolean
    readonly children?: ReactNode
  }
  export const Button: ComponentType<DshButtonProps>

  /** 14px 下拉箭头，用于菜单触发器。 */
  export const IconChevronDownOutline14: ComponentType<{ readonly className?: string }>

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
}
