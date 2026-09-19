/**
 * ks-dsh-plugin — client/KsKnowledgeGuide.tsx
 *
 * 右侧栏**开始页**上我们自己那张卡（今天叫「PDF 查看器」，改为「知识库」+ 一个 ▾ 菜单）。
 *
 * ## 为什么能自己画卡（一手依据）
 * 官方 README（`ui-sidebar-right/README.zh.md:101`）：
 * > 「开始页按当前生效的**定义 id** 渲染 `sidebar.right.tab.guide.entry`…
 * >   **provider 可按自己的定义 id 注册自定义卡片**；未注册时使用默认图标与标题按钮。
 * >   侧栏负责宽度和排列，**自定义组件负责内部结构和交互**。」
 *
 * ⇒ 「新建终端」那张卡右边的 ▾ 就是这么来的（宿主自己的
 * `ui-sidebar-terminal/src/client/TerminalGuide.tsx` + `index.ts:62`），
 * 本文件**照它的结构**做同一件事：`Button`（主）+ `Menu`（▾）。
 *
 * ## 为什么直接用宿主的 `Button`/`Menu` 而不是自己糊
 * 业主的要求是「UI 设计要和 DSH 保持相同风格」。自己画一个下拉，就得追宿主的圆角/阴影/
 * 分组/键盘行为，且**换了皮肤就不同步**。而这三个成员在 client loader 的冻结模块表里
 * （`packages/client/web/src/seed.ts:36`），我们能 require 到 —— 于是菜单**就是宿主那个菜单**。
 */

import { useState, type ReactNode } from 'react'

import { Button, IconChevronDownOutline14, Menu } from '@deepseek-ai/dsh-client-ui-primitives'

import { ensureKsStyles } from './ksGuideStyles'
import { KsKnowledgeGuideIcon } from './KsKnowledgeGuideIcon'
import { KS_EVIDENCE_KIND, KS_KB_KIND, type KsGuideCardProps, type KsKbPage } from './ksSidebar'

/**
 * ▾ 菜单的项目（"刚刚说的东西"）。
 *
 * `pdf` 单列在末尾：卡片改名成「知识库」之后，PDF 阅读器从"开始页的一张卡"变成
 * "知识库这个入口下的一个去处"——**它本身没被删**，业主明确要求保留
 * （「我们的原件查看窗口 + 目录的形式还是要保留的」）。
 */
const MENU_ITEMS: readonly { readonly id: KsKbPage | 'pdf'; readonly label: string }[] = [
  { id: 'manage', label: '知识库管理' },
  { id: 'capabilities', label: '能力' },
  { id: 'ingest', label: '文件导入' },
  { id: 'report', label: '效力报告' },
  { id: 'channels', label: '渠道台账' },
  { id: 'pdf', label: '打开 PDF 查看器' },
]

/**
 * 开始页上的「知识库」入口卡（主按钮 + ▾ 菜单）。
 *
 * @param props - 框架转发给 guide 卡片的运行时 props（`title`/`description`/`kind`/`useTabInfo`）。
 * @returns 一张卡：左边点开知识库，右边 ▾ 开二级目录。
 */
export function KsKnowledgeGuide({ title, description, kind, useTabInfo }: KsGuideCardProps): ReactNode {
  ensureKsStyles()
  const { tab } = useTabInfo()
  const [open, setOpen] = useState(false)

  const go = (page: KsKbPage | 'pdf'): void => {
    setOpen(false)
    if (page === 'pdf') {
      // 保留的 PDF 阅读器：仍走它自己的 tab 类型（单例地址）。
      tab.actions.openTab(KS_EVIDENCE_KIND, { replaceTab: true })
      return
    }
    tab.actions.openTab(KS_KB_KIND, { replaceTab: true, params: { page } })
  }

  return (
    <div className="ks-guide-entry" data-sidebar-right-guide-entry={kind}>
      <Button variant="ghost" className="ks-guide-main" onClick={() => { go('manage') }}>
        <KsKnowledgeGuideIcon size={description === undefined ? 22 : 26} className="ks-guide-icon" />
        <span className="ks-guide-text">
          <span className="ks-guide-title">{title}</span>
          {description !== undefined && <span className="ks-guide-desc">{description}</span>}
        </span>
      </Button>
      <Menu
        open={open}
        portal
        autoFocus
        align="end"
        items={MENU_ITEMS}
        onClose={() => { setOpen(false) }}
        onSelect={(id) => { go(id as KsKbPage | 'pdf') }}
        anchor={(
          <Button
            variant="ghost"
            className="ks-guide-trigger"
            aria-label="知识库二级目录"
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={() => { setOpen((value) => !value) }}
          >
            <IconChevronDownOutline14 />
          </Button>
        )}
      />
    </div>
  )
}
