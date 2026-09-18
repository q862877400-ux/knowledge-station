/**
 * ks-dsh-plugin — client/KsKnowledgePage.tsx
 *
 * 「知识库」tab 的 body（业主 2026-09-19：「干脆直接把 UI 落地，只做 UI 后端先不做」）。
 *
 * ## 本轮的性质（必须先说清，免得后人以为它是完成态）
 * **只有 UI**：页面里的库、文件夹、文档、计数**全是本文件内的占位常量**，
 * **一个引擎接口都没调**（没有 `/ks/*`、没有 fetch、没有 token）。
 * 页首有一条黄条把这件事**写在界面上**，不让它冒充可用能力。
 *
 * ## 为什么这一页值得做（设计依据，非我杜撰）
 * 业主定调：「**法规标准的几级目录应该是对应知识库文件夹的不同层文件夹名**」。
 * ⇒ 页面上那棵树的每一层**就是**文件夹层级，且**层级名来自分类法**：
 *   标准：CCS 24 大类 → CCS 区间 → CCS 具体类目；
 *   法规：效力层级 → 法律部门 → 业务领域。
 *   后端 `GET /api/v1/documents/categories` **已经在产出**这条路径
 *   （`doc_catalog.classify_document` 返回 `{top, level2, level3, level4, order}`），
 *   所以这页将来是**接线**，不是重画分类法。
 *
 * ## 自建夹为什么和两棵树平级
 * 业主原话：「『公司制度』这类自建夹是跟自带两棵树**平级**，相当于就加在后面了」。
 * ⇒ 自带两棵是**分类法的投影**（不可改名/删除），自建夹是**真容器**（可建可删）。
 *   两者不是父子关系——见本文件的三段式布局。
 */

import { useState, type ReactNode } from 'react'

import { ensureKsStyles } from './ksGuideStyles'
import type { KsPaneBodyProps, KsKbInjected } from './ksSidebar'

/** 一个文档叶（占位）。`st` 是效力状态，决定徽章颜色。 */
interface MockDoc {
  readonly no: string
  readonly name: string
  readonly st: 'current' | 'upcoming' | 'withdrawn' | 'superseded'
}

/** 一个目录节点（占位）：名字**就是**文件夹名，children/docs 二选一或都有。 */
interface MockNode {
  readonly name: string
  readonly children?: readonly MockNode[]
  readonly docs?: readonly MockDoc[]
}

/** 自带「标准」树（层级名取自 `doc_catalog.py` 的权威 CCS 表，不是编的）。 */
const STD_TREE: readonly MockNode[] = [
  {
    name: 'P 土木、建筑',
    children: [
      {
        name: 'P15/19 工程抗震、工程防火、人防工程',
        children: [
          {
            name: 'P16 工程防火',
            docs: [
              { no: 'GB 50016-2014', name: '建筑设计防火规范', st: 'current' },
              { no: 'GB 55037-2022', name: '建筑防火通用规范', st: 'current' },
              { no: 'GB 50084-2017', name: '自动喷水灭火系统设计规范', st: 'current' },
              { no: 'GB 50016-2006', name: '建筑设计防火规范（2006 版）', st: 'withdrawn' },
            ],
          },
        ],
      },
    ],
  },
  {
    name: 'C 医药、卫生、劳动保护',
    children: [
      {
        name: 'C65/74 劳动安全技术',
        docs: [{ no: 'GB 30871-2022', name: '危险化学品企业特殊作业安全规范', st: 'current' }],
      },
    ],
  },
  {
    name: 'Z 环境保护',
    children: [
      {
        name: 'Z60/79 污染物排放标准',
        docs: [
          { no: 'GB 8978-1996', name: '污水综合排放标准', st: 'current' },
          { no: 'GB 3095-2012', name: '环境空气质量标准', st: 'upcoming' },
        ],
      },
    ],
  },
]

/** 自带「法律法规」树（效力层级 → 法律部门 → 业务领域，四级与标准树同深）。 */
const LAW_TREE: readonly MockNode[] = [
  {
    name: '法律',
    children: [
      {
        name: '宪法与行政法',
        children: [
          {
            name: '安全生产',
            docs: [
              { no: '', name: '中华人民共和国安全生产法', st: 'current' },
              { no: '', name: '中华人民共和国消防法', st: 'current' },
            ],
          },
        ],
      },
    ],
  },
  {
    name: '行政法规',
    children: [
      {
        name: '宪法与行政法',
        docs: [{ no: '', name: '危险化学品安全管理条例', st: 'current' }],
      },
    ],
  },
]

/** 自建夹（业主例子「公司制度」）；与上面两棵树**平级**。 */
const USER_FOLDERS: readonly { readonly name: string; readonly n: number; readonly desc: string }[] = [
  { name: '公司制度', n: 23, desc: '集团安全管理制度、责任制、考核办法' },
  { name: '内部操作规程', n: 11, desc: '各车间岗位操作规程与作业指导书' },
  { name: '供应商资料', n: 4, desc: '供应商资质与检测报告' },
]

const BADGE: Record<MockDoc['st'], { cls: string; text: string }> = {
  current: { cls: 'ks-kb-badge ks-kb-badge-ok', text: '现行' },
  upcoming: { cls: 'ks-kb-badge ks-kb-badge-warn', text: '即将实施' },
  withdrawn: { cls: 'ks-kb-badge ks-kb-badge-bad', text: '已废止' },
  superseded: { cls: 'ks-kb-badge ks-kb-badge-bad', text: '被替代' },
}

/** 递归渲染一个目录节点（`open` 是展开集合：默认把顶层展开，让层级一眼可见）。 */
function renderNodes(
  nodes: readonly MockNode[],
  open: ReadonlySet<string>,
  toggle: (name: string) => void,
  depth = 0,
): ReactNode {
  return nodes.map((node) => {
    const isOpen = open.has(node.name)
    const kids = node.children ?? []
    const leafCount = kids.length > 0 || (node.docs ?? []).length > 0
    return (
      <div key={node.name}>
        <div className="ks-kb-tline" role="button" tabIndex={0}
          onClick={() => { toggle(node.name) }}
          onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') toggle(node.name) }}
          style={{ paddingLeft: 6 + depth * 12 }}>
          <span className="ks-kb-tw">{leafCount ? (isOpen ? '▾' : '▸') : '·'}</span>
          <span className="ks-kb-tn" title={node.name}>{node.name}</span>
        </div>
        {isOpen && kids.length > 0 && renderNodes(kids, open, toggle, depth + 1)}
        {isOpen && (node.docs ?? []).map((doc) => (
          <div className="ks-kb-doc" key={node.name + doc.name} style={{ paddingLeft: 18 + depth * 12 }}>
            {doc.no !== '' && <span className="ks-kb-no">{doc.no}</span>}
            <span className="ks-kb-nm" title={doc.name}>{doc.name}</span>
            <span className={BADGE[doc.st].cls}>{BADGE[doc.st].text}</span>
          </div>
        ))}
      </div>
    )
  })
}

/** 一棵自带树的卡片外壳（标题 + 计数 + 树体）。 */
function LibCard({ title, sub, nodes, open, toggle }: {
  readonly title: string
  readonly sub: string
  readonly nodes: readonly MockNode[]
  readonly open: ReadonlySet<string>
  readonly toggle: (name: string) => void
}): ReactNode {
  return (
    <div className="ks-kb-card">
      <div className="ks-kb-row">
        <strong className="ks-kb-grow">{title}</strong>
        <span className="ks-kb-badge">自带</span>
      </div>
      <div className="ks-kb-hint" style={{ margin: '3px 0 6px' }}>{sub}</div>
      <div className="ks-kb-tree">{renderNodes(nodes, open, toggle)}</div>
    </div>
  )
}

/**
 * 知识库 tab 的 body。
 *
 * @param props - 框架给的运行时 props（含 `useTabInfo`）与本插件注入的面。
 * @returns 知识库管理页；`params.page` 指向尚未实现的页时给**诚实的占位**。
 */
export function KsKnowledgePage({ useTabInfo, dataSource }: KsPaneBodyProps & KsKbInjected): ReactNode {
  ensureKsStyles()
  const { tab } = useTabInfo()
  const page = (tab.navigation.params as { page?: string } | undefined)?.page ?? 'manage'
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(['P 土木、建筑', 'C 医药、卫生、劳动保护', 'Z 环境保护', '法律']),
  )
  const toggle = (name: string): void => {
    setOpen((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  if (page !== 'manage') {
    const LABELS: Record<string, string> = {
      ingest: '文件导入',
      report: '效力报告',
      channels: '渠道台账',
    }
    return (
      <div className="ks-kb">
        <div className="ks-kb-banner">
          <strong>UI 先行，后端未接。</strong>本页只落了入口与外壳，数据是页面内的占位常量。
        </div>
        <div className="ks-kb-card">
          <strong>{LABELS[page] ?? page}</strong>
          <div className="ks-kb-hint" style={{ marginTop: 6 }}>
            这一页尚未实现。它会落在同一个 tab 类型里（按 <code>params.page</code> 分发），
            所以入口现在是**真的**、内容是**空的**——而不是一个假按钮。
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="ks-kb">
      <div className="ks-kb-banner">
        <strong>UI 先行：数据是占位，后端接口未接</strong>（dataSource=<code>{dataSource}</code>）。
        层级名取自 <code>doc_catalog</code> 的权威 CCS 表；将来这页接
        <code> GET /api/v1/documents/categories</code> 即可，不必重画分类法。
      </div>

      <div className="ks-kb-row">
        <strong className="ks-kb-grow" style={{ fontSize: 14 }}>知识库</strong>
        <button type="button" className="ks-kb-btn ks-kb-btn-primary" disabled
          title="后端未接：文件夹目前是只读展示">＋ 新建文件夹</button>
      </div>

      <div className="ks-kb-sec">自带两棵树（不可改名/删除 —— 名字就是分类层级名）</div>
      <LibCard title="标准" sub="国家标准·行业标准·团体标准" nodes={STD_TREE} open={open} toggle={toggle} />
      <LibCard title="法律法规" sub="法律 / 行政法规 / 部门规章 / 地方性法规" nodes={LAW_TREE} open={open} toggle={toggle} />

      <div className="ks-kb-sec">我建的（真文件夹，可改名/删除；与上面两棵平级）</div>
      <div className="ks-kb-cards">
        {USER_FOLDERS.map((folder) => (
          <div className="ks-kb-card" key={folder.name}>
            <strong style={{ fontSize: 13 }}>{folder.name}</strong>
            <div className="ks-kb-hint" style={{ margin: '4px 0 6px' }}>{folder.desc}</div>
            <div className="ks-kb-hint">{folder.n} 篇</div>
          </div>
        ))}
      </div>
    </div>
  )
}
