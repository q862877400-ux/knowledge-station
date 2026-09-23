/**
 * ks-dsh-plugin — client/kbListUi.tsx
 *
 * **知识库列表机制的共用件**（2026-09-22 业主打回手搓后立的正道）：面包屑/列表头/列表容器
 * 的 JSX 结构一处所有——知识库管理与渠道台账**共用这一份**（一套代码=必然一个模样）。
 *
 * ⚠ 结构逐字对齐 `KsKnowledgePage` 的 `.ks-crumb`/`.ks-list`/`.ks-lhead` 机制与
 * `ksGuideStyles.ts` 的注释约定（`.ks-crumb-item` 与 `.ks-crumb-sep` 是**兄弟**；列宽唯一
 * 所有者是每层自己的 `--ks-cols`）。KsKnowledgePage 迁到本共用件 = 下一小批（登记）。
 */
import * as React from 'react'

/** 列定义：head=表头字（空串=占位格不印字）；key=格子类名后缀 `ks-col-<key>`。 */
export interface KbListCol {
  key: string
  head: string
}

/** 面包屑（`.ks-crumb`）：条目/分隔符兄弟排布；当前级用 `.ks-crumb-here`，可点级 `.ks-crumb-go`。 */
export function KsCrumb(props: {
  items: Array<{ name: string; onGo?: () => void }>
  n?: number
}): React.ReactElement {
  const { items, n } = props
  return (
    <nav className="ks-crumb" aria-label="位置">
      <span className="ks-crumb-path">
        {items.map((it, i) => (
          <React.Fragment key={`${String(i)}-${it.name}`}>
            {i > 0 ? <span className="ks-crumb-sep" aria-hidden="true">/</span> : null}
            <span className="ks-crumb-item">
              {it.onGo
                ? <button type="button" className="ks-crumb-go" onClick={it.onGo}>{it.name}</button>
                : <span className="ks-crumb-here">{it.name}</span>}
            </span>
          </React.Fragment>
        ))}
      </span>
      {n !== undefined ? <span className="ks-crumb-n">{String(n)} 条</span> : null}
    </nav>
  )
}

/** 列表题头行（`.ks-lhead`）：每格 `.ks-cell.ks-col-<key>` + `.ks-lhead-col` 表头字。 */
export function KsListHead(props: { cols: readonly KbListCol[] }): React.ReactElement {
  return (
    <div className="ks-lhead">
      {props.cols.map((col) => (
        <div key={col.key} className={`ks-cell ks-col-${col.key}`}>
          {col.head === '' ? null : <span className="ks-lhead-col">{col.head}</span>}
        </div>
      ))}
    </div>
  )
}
