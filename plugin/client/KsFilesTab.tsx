/**
 * ks-dsh-plugin — client/KsFilesTab.tsx
 *
 * 📚 文件目录视图（2026-09-06 起不再独立注册 tab：改为 PDF 查看器左列的
 * 「文件目录」模式视图 KsFilesView，由 KsEvidenceTab 挂载——active 变 true 时刷新，
 * 点文档经 onOpenDoc 交宿主加载 PDF）。UI 与原项目 App.tsx"文件目录"结构一致：
 *   - header「文件目录」+ 搜索框（「🔍 搜索国标名称/编号」，清空 ×）+ 多选工具行
 *     （☑ 编辑 → 🗑 删除(N) / ☑ 全选当前 / ✕ 取消）。
 *   - 4 级缩进树：L1(加粗) → L2(CCS 大类) → L3(区间/领域) → L4(具体类目)/叶文档；
 *     ▸/▾ caret + 点击行 toggle；搜索有词全自动展开、纯前端过滤；默认展开 L1。
 *   - 文档叶：法规(doc_type='法律法规')只显名称；国标显号+名+CCS meta；
 *     superseded/withdrawn → 灰+删除线+「废止」；hover title 带日期。
 *   - 多选删除：确认条 → batch-delete(confirm:true) → 成功/失败条 → 刷新树与列表。
 * 数据流照 api.ts 既有模式（fetchSession + 跨源 Bearer；401 → EngineAuthError 自愈一次）。
 */

import * as React from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  EngineAuthError,
  batchDeleteDocs,
  fetchCategories,
  fetchDocsFlat,
  fetchSession,
  type BatchDeleteResult,
  type KsCategoryNode,
  type KsDoc,
} from './api'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'error'; message: string }

/** 删除流程相位：confirm(确认条) → deleting → done | error(可重试)。 */
type DelPhase = 'confirm' | 'deleting' | 'done' | 'error' | null

/** 嵌入 PDF 查看器左列的文件目录视图 props（不再独立注册 tab，由 KsEvidenceTab 挂载）。 */
export interface KsFilesViewProps {
  /** 视图是否激活（PDF 查看器左列切到"文件目录"模式）。变 true 时刷新数据。 */
  active: boolean
  /** 点文档叶（非多选态）→ 由宿主加载 PDF（本组件不再自己 openTab）。 */
  onOpenDoc: (docId: string) => void
  /** 搜索词（2026-10-28 四宫格统一搜索：宿主持有，本视图受控过滤）。 */
  query: string
  onQueryChange: (v: string) => void
}

export function KsFilesView(props: KsFilesViewProps): JSX.Element {
  const { active, onOpenDoc, query } = props

  const abortRef = useRef<AbortController | null>(null)
  const [cats, setCats] = useState<KsCategoryNode[]>([])
  const [flatDocs, setFlatDocs] = useState<KsDoc[]>([])
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [catOpen, setCatOpen] = useState<Record<string, boolean>>({})
  const [catMulti, setCatMulti] = useState(false)
  const [selDocs, setSelDocs] = useState<Set<string>>(new Set())
  const [delPhase, setDelPhase] = useState<DelPhase>(null)
  const [delDone, setDelDone] = useState<{ docs: number; clauses: number } | null>(null)
  const [delErr, setDelErr] = useState<string>('')

  /**
   * 拉取分类树 + 平铺列表（静默，不置 loading 态）。删除后刷新用；也供初次载入复用。
   * 失败时抛出 → 由调用方决定展示（载入失败显示错误态 / 删除后刷新静默吞掉）。
   */
  const fetchTreeData = useCallback(async (signal?: AbortSignal): Promise<void> => {
    let session = await fetchSession(signal)
    let list: KsCategoryNode[]
    try {
      list = await fetchCategories(session.engine.port, session.token, signal)
    } catch (error) {
      // 401 → 会话可能已轮换：重取一次再试（镜像 fetchPdf/host bbox 语义）。
      if (error instanceof EngineAuthError) {
        session = await fetchSession(signal)
        list = await fetchCategories(session.engine.port, session.token, signal)
      } else {
        throw error
      }
    }
    if (signal?.aborted) return
    setCats(list)
    // 分类默认展开 L1（两个顶级：国家标准/法律法规）。
    setCatOpen((prev) => {
      const next = { ...prev }
      for (const c of list) next['L:' + c.name] = true
      return next
    })
    // 平铺列表（含全部 doc_meta；文档总数 + 删除后刷新用）。失败静默降级：树已就绪。
    try {
      const flat = await fetchDocsFlat(session.engine.port, session.token, signal)
      if (!signal?.aborted) setFlatDocs(flat)
    } catch { /* 静默：树仍可用 */ }
  }, [])

  const loadCategories = useCallback(async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoad({ status: 'loading' })
    setDelErr('')
    try {
      await fetchTreeData(controller.signal)
      if (controller.signal.aborted) return
      setLoad({ status: 'ready' })
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
    }
  }, [fetchTreeData])

  // 视图激活（active 变 true）时刷新（引擎 port/token 每次启动轮换）。
  useEffect(() => {
    if (active) void loadCategories()
  }, [active, loadCategories])

  const retry = useCallback(() => {
    void loadCategories()
  }, [loadCategories])

  // ---- 树展开/收起 ----
  const toggleCat = useCallback((key: string) => {
    setCatOpen((s) => ({ ...s, [key]: !s[key] }))
  }, [])

  // ---- 搜索：纯前端过滤整棵树；有词时全部自动展开 ----
  // （2026-10-28 四宫格统一搜索：catQuery 改由宿主受控传入。）
  const catQuery = query
  const catQ = catQuery.trim().toLowerCase()
  const catFiltered = useMemo(() => {
    if (!catQ) return cats
    const docHit = (d: KsDoc): boolean =>
      (d.standard_no ?? '').toLowerCase().includes(catQ) ||
      (d.standard_name ?? '').toLowerCase().includes(catQ)
    const nameHit = (s: string | null | undefined): boolean =>
      typeof s === 'string' && s.toLowerCase().includes(catQ)
    const map3 = (l3: KsCategoryNode): KsCategoryNode | null => {
      // 分支名命中 → 子全部保留（文档+类目都保留，不再细过滤）。
      if (nameHit(l3.name)) return { ...l3, docs: l3.docs, items: l3.items }
      const docs = l3.docs.filter(docHit)
      const l4s = l3.items
        .map((l4) => ({
          ...l4,
          docs: nameHit(l4.name) ? l4.docs : l4.docs.filter(docHit),
        }))
        .filter((l4) => l4.docs.length > 0)
      if (!docs.length && !l4s.length) return null
      return { ...l3, docs, items: l4s }
    }
    const map2 = (l2: KsCategoryNode): KsCategoryNode | null => {
      if (nameHit(l2.name)) return { ...l2, items: l2.items }
      const l3s = l2.items.map(map3).filter((n): n is KsCategoryNode => n !== null)
      if (!l3s.length) return null
      return { ...l2, items: l3s }
    }
    return cats
      .map((top) => {
        if (nameHit(top.name)) return { ...top, items: top.items }
        const l2s = top.items.map(map2).filter((n): n is KsCategoryNode => n !== null)
        if (!l2s.length) return null
        return { ...top, items: l2s }
      })
      .filter((n): n is KsCategoryNode => n !== null)
  }, [catQ, cats])

  const catMatchCount = useMemo(() => {
    if (!catQ) return 0
    let n = 0
    const walk = (items: KsCategoryNode[]): void => {
      for (const it of items) {
        n += it.docs.length
        if (it.items.length) walk(it.items)
      }
    }
    walk(catFiltered)
    return n
  }, [catQ, catFiltered])

  /** 当前可见（搜索过滤后）全部 doc_id ——「全选当前」的数据源。 */
  const catVisibleDocIds = useMemo(() => {
    const ids: string[] = []
    const walk = (items: KsCategoryNode[]): void => {
      for (const it of items) {
        for (const d of it.docs) ids.push(d.doc_id)
        if (it.items.length) walk(it.items)
      }
    }
    walk(catFiltered)
    return ids
  }, [catFiltered])

  const allVisibleSelected =
    catVisibleDocIds.length > 0 && catVisibleDocIds.every((id) => selDocs.has(id))

  // ---- 多选 ----
  const toggleSelDoc = useCallback((docId: string) => {
    setSelDocs((s) => {
      const next = new Set(s)
      if (next.has(docId)) next.delete(docId)
      else next.add(docId)
      return next
    })
    setDelPhase(null) // 选择变化 → 撤回进行中的确认条
  }, [])

  const toggleSelAll = useCallback(() => {
    const vis = catVisibleDocIds
    const all = vis.length > 0 && vis.every((id) => selDocs.has(id))
    setSelDocs(all ? new Set() : new Set(vis))
    setDelPhase(null)
  }, [catVisibleDocIds, selDocs])

  const exitCatMulti = useCallback(() => {
    setCatMulti(false)
    setSelDocs(new Set())
    setDelPhase(null)
    setDelDone(null)
    setDelErr('')
  }, [])

  const requestDelete = useCallback(() => {
    if (selDocs.size === 0) return
    setDelPhase('confirm')
  }, [selDocs.size])

  const confirmDelete = useCallback(async () => {
    if (delPhase === 'deleting') return // 防重复提交
    if (selDocs.size === 0) return
    setDelPhase('deleting')
    setDelErr('')
    const controller = new AbortController()
    try {
      let session = await fetchSession(controller.signal)
      let result: BatchDeleteResult
      try {
        result = await batchDeleteDocs(session.engine.port, [...selDocs], session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          result = await batchDeleteDocs(session.engine.port, [...selDocs], session.token, controller.signal)
        } else {
          throw error
        }
      }
      if (controller.signal.aborted) return
      setDelDone({ docs: result.deleted_docs, clauses: result.deleted_clauses })
      setDelPhase('done')
      // 删除后刷新树与平铺列表（静默，不闪 loading 态）。
      void fetchTreeData().catch(() => { /* 刷新失败不阻断删除成功条 */ })
    } catch (error) {
      if (controller.signal.aborted) return
      setDelErr(error instanceof Error ? error.message : String(error))
      setDelPhase('error')
    }
  }, [delPhase, selDocs, fetchTreeData])

  // ---- 点文档叶（非多选）→ 交宿主加载 PDF（KsEvidenceTab 左列宿主）----
  const openDoc = useCallback((d: KsDoc) => {
    try {
      onOpenDoc(d.doc_id)
    } catch (error) {
      setDelErr(`打开 PDF 失败：${error instanceof Error ? error.message : String(error)}`)
    }
  }, [onOpenDoc])

  const ready = load.status === 'ready'

  // ---- 文档叶节点（照原项目 docLeaf, App.tsx :1362-1406）----
  const renderLeaf = (d: KsDoc): JSX.Element => {
    const struck = d.legal_status === 'superseded' || d.legal_status === 'withdrawn'
    const wd = d.legal_status === 'withdrawn' || d.legal_status === 'superseded'
      ? (d.withdrawn_date ?? '')
      : ''
    const metaBits = [
      d.ccs_name ? (d.ccs_code ? `${d.ccs_code} ${d.ccs_name}` : d.ccs_name) : '',
    ].filter(Boolean)
    const dateBits = [
      d.published_at ? `发布 ${d.published_at}` : '',
      d.effective_from ? `生效 ${d.effective_from}` : '',
      wd ? `废止 ${wd}` : '',
      d.ccs_name ? (d.ccs_code ? `${d.ccs_code} ${d.ccs_name}` : d.ccs_name) : '',
    ].filter(Boolean)
    const checked = selDocs.has(d.doc_id)
    return (
      <div
        key={d.doc_id}
        onClick={() => {
          if (catMulti) toggleSelDoc(d.doc_id)
          else void openDoc(d)
        }}
        style={{
          ...$leaf,
          ...(struck ? $leafStruck : {}),
          ...(catMulti ? { cursor: 'pointer' } : {}),
        }}
        title={[
          (d.standard_no + ' ' + (d.standard_name ?? '')).trim() + (struck ? '（已废止，仅供参考）' : ''),
          dateBits.length ? dateBits.join(' · ') : '',
        ].filter(Boolean).join('\n')}
      >
        {catMulti ? (
          <span style={{ ...$docCheck, ...(checked ? $docCheckOn : {}) }} aria-checked={checked}>
            {checked ? '✓' : ''}
          </span>
        ) : null}
        {d.doc_type === '法律法规' ? (
          <span style={{ minWidth: 'auto', fontWeight: 500 }}>{d.standard_name || d.standard_no}</span>
        ) : (
          <>
            <span style={{ minWidth: 'auto', fontWeight: 500 }}>{d.standard_no}</span>
            {d.standard_name ? <span style={$leafName}>{d.standard_name}</span> : null}
          </>
        )}
        {struck ? <span style={$supBadge}>废止</span> : null}
        {metaBits.length ? <span style={$leafMeta}>{metaBits.join(' · ')}</span> : null}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, fontSize: 12 }}>
      {/* header：标题 + 文档总数 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>📚 文件目录</span>
        {ready && (
          catQ
            ? <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>匹配 {catMatchCount} 部</span>
            : flatDocs.length > 0
              ? <span style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>共 {flatDocs.length} 部</span>
              : null
        )}
      </div>

      {/* 搜索框已上移到目录列顶部四宫格（宿主 KsEvidenceTab 统一搜索，本视图受控过滤）。 */}

      {/* 多选工具行 */}
      <div style={$multiTool}>
        {!catMulti ? (
          <button
            type="button"
            style={$toolBtn}
            onClick={() => { setCatMulti(true); setDelPhase(null) }}
            title="进入编辑模式：条目前出现勾选框，点击条目即选中/取消"
          >
            ☑ 编辑
          </button>
        ) : (
          <>
            <button
              type="button"
              style={{ ...$toolBtn, ...$dangerBtn }}
              disabled={selDocs.size === 0}
              onClick={requestDelete}
              title={selDocs.size === 0 ? '先勾选要删除的文档' : `删除选中的 ${selDocs.size} 部文档`}
            >
              🗑 删除{selDocs.size > 0 ? `(${selDocs.size})` : ''}
            </button>
            <button
              type="button"
              style={$toolBtn}
              onClick={toggleSelAll}
              title={allVisibleSelected
                ? (catQ ? '清空当前搜出的全部选中' : '清空全部选中')
                : (catQ ? `全选搜出的 ${catVisibleDocIds.length} 部` : `全选全部 ${catVisibleDocIds.length} 部`)}
            >
              {allVisibleSelected ? '◻ 取消全选' : '☑ 全选当前'}
            </button>
            <button type="button" style={$toolBtn} onClick={exitCatMulti} title="退出编辑模式并清空选择">✕ 取消</button>
          </>
        )}
      </div>

      {/* 删除确认 / 进行中 / 成功 / 失败 条 */}
      {catMulti && delPhase === 'confirm' && (
        <div style={$delBar}>
          <div>⚠ 将永久删除选中的 <b>{selDocs.size}</b> 部文档及其全部条款/证据/向量，不可恢复。</div>
          <div style={$delBtns}>
            <button type="button" style={{ ...$toolBtn, ...$dangerBtn }} onClick={() => void confirmDelete()}>确认删除</button>
            <button type="button" style={$toolBtn} onClick={() => setDelPhase(null)}>再想想</button>
          </div>
        </div>
      )}
      {catMulti && delPhase === 'deleting' && (
        <div style={$delBar}>
          <div>⏳ 正在删除选中的 <b>{selDocs.size}</b> 部文档…</div>
        </div>
      )}
      {catMulti && delPhase === 'done' && delDone && (
        <div style={$delBar}>
          <div>✅ 已删除 {delDone.docs} 部文档（{delDone.clauses} 条条款及其证据/向量已级联清除）。</div>
          <div style={$delBtns}>
            <button type="button" style={$toolBtn} onClick={exitCatMulti}>完成</button>
          </div>
        </div>
      )}
      {catMulti && delPhase === 'error' && (
        <div style={$delBar}>
          <div>❌ 删除失败：{delErr}</div>
          <div style={$delBtns}>
            <button type="button" style={{ ...$toolBtn, ...$dangerBtn }} onClick={() => setDelPhase('confirm')}>返回重试</button>
            <button type="button" style={$toolBtn} onClick={exitCatMulti}>取消</button>
          </div>
        </div>
      )}

      {/* body：树 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 4 }}>
        {load.status === 'loading' && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>加载中…（首次可能启动引擎，需要数秒）</div>
          </div>
        )}
        {load.status === 'error' && (
          <div style={{ ...$center, flexDirection: 'column', gap: 10 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', maxWidth: 480, textAlign: 'center', wordBreak: 'break-word' }}>
              {load.message}
            </div>
            <button type="button" onClick={retry} style={$btnPrimary}>重试</button>
          </div>
        )}
        {ready && cats.length === 0 && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>库内暂无文档</div>
          </div>
        )}
        {ready && cats.length > 0 && catQ && catMatchCount === 0 && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>没有匹配「{catQuery.trim()}」的文件</div>
          </div>
        )}
        {ready && cats.length > 0 && (!catQ || catMatchCount > 0) && catFiltered.map((top) => {
          const key1 = 'L:' + top.name
          const open1 = !!catQ || !!catOpen[key1]
          return (
            <div key={key1}>
              <div style={{ ...$row, ...$rowL1 }} onClick={() => toggleCat(key1)}>
                <span style={$caret}>{open1 ? '▾' : '▸'}</span>
                <span style={{ fontWeight: 700 }}>{top.name}</span>
              </div>
              {open1 && (
                <div style={$children}>
                  {top.items.map((l2) => {
                    const key2 = key1 + '>' + l2.name
                    const open2 = !!catQ || !!catOpen[key2]
                    return (
                      <div key={key2}>
                        <div style={{ ...$row, ...$rowL2 }} onClick={() => toggleCat(key2)}>
                          <span style={$caret}>{open2 ? '▾' : '▸'}</span>
                          <span style={{ fontSize: 11.5 }}>{l2.name}</span>
                        </div>
                        {open2 && (
                          <div style={$children}>
                            {l2.items.map((l3) => {
                              const key3 = key2 + '>' + l3.name
                              const open3 = !!catQ || !!catOpen[key3]
                              return (
                                <div key={key3}>
                                  <div style={{ ...$row, ...$rowL3 }} onClick={() => toggleCat(key3)}>
                                    <span style={$caret}>{open3 ? '▾' : '▸'}</span>
                                    {l3.name}
                                  </div>
                                  {open3 && (
                                    <div style={{ paddingLeft: 14 }}>
                                      {l3.docs.length > 0 ? (
                                        /* 法规树：领域下直接是文档叶节点（法规名称不再作为目录级别） */
                                        l3.docs.map(renderLeaf)
                                      ) : (
                                        l3.items.map((l4) => (
                                          <div key={l4.name} style={$fileSub}>
                                            <div style={$fileSubName}>{l4.name}</div>
                                            {l4.docs.map(renderLeaf)}
                                          </div>
                                        ))
                                      )}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---- small inline styles (mirrors KsBookmarksTab / KsEvidenceTab; DSH CSS 变量近似值) ----

const $center: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  minHeight: 160,
}

const $btnPrimary: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '4px 14px',
  cursor: 'pointer',
}

// （2026-10-28）$search/$searchInput/$searchClear 已删——搜索框上移到目录列
// 顶部四宫格，由宿主 KsEvidenceTab 持有；本视图经 props.query 受控过滤。

const $multiTool: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  margin: '4px 10px',
  flexWrap: 'wrap',
}

const $toolBtn: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '2px 8px',
  cursor: 'pointer',
  fontSize: 11,
  whiteSpace: 'nowrap',
}

const $dangerBtn: React.CSSProperties = {
  borderColor: 'var(--dsw-alias-danger, #c62828)',
  color: 'var(--dsw-alias-danger, #c62828)',
}

const $delBar: React.CSSProperties = {
  margin: '0 10px 6px',
  padding: '6px 8px',
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  fontSize: 11,
  lineHeight: 1.4,
  color: 'var(--dsw-alias-label-secondary, #666)',
}

const $delBtns: React.CSSProperties = {
  display: 'flex',
  gap: 6,
  marginTop: 5,
}

// ---- 树行样式 (参考 styles.css 的 .toc-* / .file-sub*) ----

const $row: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: '2px 4px',
  fontSize: 11.5,
  cursor: 'pointer',
  borderRadius: 4,
  alignItems: 'center',
  lineHeight: 1.4,
}

const $rowL1: React.CSSProperties = {
  fontWeight: 700,
  color: 'var(--dsw-alias-label-primary, #111)',
  marginTop: 2,
}

const $rowL2: React.CSSProperties = {
  paddingLeft: 10,
}

const $rowL3: React.CSSProperties = {
  fontWeight: 600,
  color: 'var(--dsw-alias-label-secondary, #666)',
  fontSize: 11,
  paddingLeft: 8,
}

const $caret: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 14,
  height: 14,
  marginRight: 1,
  color: 'var(--dsw-alias-link, #1565c0)',
  cursor: 'pointer',
  fontSize: 11,
  borderRadius: 3,
  flexShrink: 0,
}

const $children: React.CSSProperties = {
  padding: '1px 0 2px 14px',
}

const $fileSub: React.CSSProperties = {
  marginTop: 0,
}

const $fileSubName: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--dsw-alias-label-secondary, #666)',
  padding: '1px 4px',
  fontWeight: 600,
  lineHeight: 1.4,
}

// ---- 文档叶节点样式 ----

const $leaf: React.CSSProperties = {
  display: 'block',
  padding: '2px 4px',
  fontSize: 11.5,
  cursor: 'pointer',
  borderRadius: 4,
  color: 'var(--dsw-alias-label-tertiary, #999)',
  lineHeight: 1.35,
}

const $leafStruck: React.CSSProperties = {
  color: 'var(--dsw-alias-label-tertiary, #999)',
  textDecoration: 'line-through',
  opacity: 0.75,
}

const $leafName: React.CSSProperties = {
  color: 'var(--dsw-alias-label-secondary, #666)',
  fontSize: 11,
  wordBreak: 'break-word',
  overflowWrap: 'anywhere',
  lineHeight: 1.35,
}

const $leafMeta: React.CSSProperties = {
  display: 'block',
  color: 'var(--dsw-alias-label-tertiary, #999)',
  fontSize: 10,
  marginTop: 1,
  lineHeight: 1.3,
}

const $supBadge: React.CSSProperties = {
  display: 'inline-block',
  marginLeft: 6,
  color: 'var(--dsw-alias-label-tertiary, #999)',
  fontSize: 10.5,
}

const $docCheck: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 12,
  height: 12,
  marginRight: 6,
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 3,
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  color: '#fff',
  fontSize: 9,
  lineHeight: 1,
  flexShrink: 0,
  verticalAlign: 'middle',
}

const $docCheckOn: React.CSSProperties = {
  background: 'var(--dsw-alias-danger, #c62828)',
  borderColor: 'var(--dsw-alias-danger, #c62828)',
}
