/**
 * ks-dsh-plugin — client/KsBookmarksTab.tsx (2026-10 收藏目录)
 *
 * 🔖 收藏目录视图 —— **PDF 查看器左列的第三种目录模式**（与 📚 文件目录 /
 * 📖 标题目录并列，同一悬浮左列内切换；2026-10-27 按用户指示从独立侧栏 tab
 * 迁入，独立 tab 已删）。整个视图就是一棵收藏目录树：
 *   收藏夹（自建，名字自定义）→ 夹内挂收藏文档的文件目录分类路径
 *   （L1→L2→L3/L4，复用 classify_document 口径，与文件目录同源）
 *   → 文档节点 → 条款级收藏叶子。
 *
 * 数据源：GET /api/v1/bookmark-folders/tree（夹列表 + 每夹 doc 节点 + 分类路径
 * + 条款收藏列表；未分类恒为末位伪夹）。
 *
 * 每个收藏夹的操作：
 *   💡 提问     → PUT /ks/chat-mode {folderId, folderName} 开「在本收藏夹内提问」；
 *                再点 / 点 ✕ 关（folderId:null）。激活后本会话每轮检索都限定在
 *                该夹内容（host 工具层强制 folder_id——见 src/index.js）。
 *   ✏️ 重命名   → PUT /api/v1/bookmark-folders/{id}（409 已存在提示）。
 *   🗑 删除      → DELETE /api/v1/bookmark-folders/{id}；**收藏不删**，全部回未分类
 *                （未分类伪夹不显示删除按钮）。
 *   ＋ 新建夹   → POST /api/v1/bookmark-folders（header 按钮）。
 *
 * 点文档/条款叶 → 经 props.onOpenEvidence 交宿主（KsEvidenceTab）直接加载该
 * 证据（本视图就在 PDF tab 内，无需 openTab）。
 *
 * 数据与信任模型照抄 KsFilesView / api.ts：fetchSession() 同源 /ks/session 拿
 * port + token；token 跨源只发给 127.0.0.1 引擎；401 → 重取一次（EngineAuthError）。
 */

import * as React from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  EngineAuthError,
  createBookmarkFolder,
  deleteBookmarkFolder,
  fetchBookmarkFolderTree,
  fetchChatMode,
  fetchSession,
  patchChatMode,
  renameBookmarkFolder,
  type KsFolderDocNode,
  type KsFolderTreeFolder,
} from './api'
import type { KsEvidence } from './ksEvidence'

/** 跳转意图：加载哪个证据（doc + 页 + 可选条款版本）。 */
export interface KsBookmarkJump {
  doc: string
  page: number
  rev?: string
}

/** 嵌入 PDF 查看器左列的收藏目录视图 props（由 KsEvidenceTab 挂载，同 KsFilesView 契约）。 */
export interface KsBookmarksViewProps {
  /** 视图是否激活（左列切到"收藏目录"模式）。变 true 时刷新数据。 */
  active: boolean
  /** 当前会话 id（💡提问 写 /ks/chat-mode 用；宿主从 scope 透传）。 */
  sessionId: string | null
  /** 点文档叶/条款叶 → 宿主加载该证据（PDF 跳页）。 */
  onOpenEvidence: (jump: KsBookmarkJump) => void
  /** 搜索词（2026-10-28 四宫格统一搜索：宿主持有，本视图受控过滤）。 */
  query: string
}

type LoadState =
  | { status: 'loading' }
  | { status: 'ready' }
  | { status: 'error'; message: string }

/** 夹头操作的确认相位（删夹）。 */
type FolderPhase = 'confirm-delete' | 'renaming' | null

/** 目录内一棵已组装的中间树节点（分类分组 + 文档叶）。 */
interface DocGroupNode {
  name: string
  /** 直接挂在本级的文档。 */
  docs: KsFolderDocNode[]
  /** 下一级分组。 */
  groups: DocGroupNode[]
}

export function KsBookmarksView(props: KsBookmarksViewProps): JSX.Element {
  const { active, sessionId, onOpenEvidence } = props

  const abortRef = useRef<AbortController | null>(null)
  const [tree, setTree] = useState<KsFolderTreeFolder[]>([])
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({})
  const [activeFolderId, setActiveFolderId] = useState<string | null>(null)
  const [opError, setOpError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [newName, setNewName] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [folderPhase, setFolderPhase] = useState<FolderPhase>(null)

  /** 拉收藏目录树（401 自愈一次）。 */
  const loadAll = useCallback(async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoad({ status: 'loading' })
    setOpError(null)
    try {
      let session = await fetchSession(controller.signal)
      let list: KsFolderTreeFolder[]
      try {
        list = await fetchBookmarkFolderTree(session.engine.port, session.token, controller.signal)
      } catch (error) {
        if (error instanceof EngineAuthError) {
          session = await fetchSession(controller.signal)
          list = await fetchBookmarkFolderTree(session.engine.port, session.token, controller.signal)
        } else {
          throw error
        }
      }
      if (controller.signal.aborted) return
      setTree(list)
      // 默认展开第一个夹（真实夹；未分类恒收起）。
      setOpenMap((prev) => {
        if (Object.keys(prev).length > 0) return prev
        const first = list.find((f) => f.folder_id !== null)
        return first !== undefined ? { ['F:' + (first.folder_id ?? '')]: true } : {}
      })
      setLoad({ status: 'ready' })
    } catch (error) {
      if (controller.signal.aborted) return
      setLoad({ status: 'error', message: error instanceof Error ? error.message : String(error) })
    }
  }, [])

  // 视图激活时刷新树 + 读当前会话开关（决定哪个夹的 💡 是亮的）。
  useEffect(() => {
    if (!active) return
    void loadAll()
    if (sessionId === null) return
    const controller = new AbortController()
    void (async () => {
      try {
        const mode = await fetchChatMode(sessionId, controller.signal)
        if (!controller.signal.aborted) setActiveFolderId(mode.folderId)
      } catch { /* 开关读取失败不阻断树；💡 退回未点亮态 */ }
    })()
    return () => controller.abort()
  }, [active, loadAll, sessionId])

  const retry = useCallback(() => { void loadAll() }, [loadAll])

  /** 引擎调用包装：401 自愈一次（所有夹操作共用）。 */
  const withSession = useCallback(async <T,>(
    fn: (port: number, token: string, signal: AbortSignal) => Promise<T>,
  ): Promise<T> => {
    let session = await fetchSession()
    try {
      return await fn(session.engine.port, session.token, new AbortController().signal)
    } catch (error) {
      if (error instanceof EngineAuthError) {
        session = await fetchSession()
        return await fn(session.engine.port, session.token, new AbortController().signal)
      }
      throw error
    }
  }, [])

  // ---- 夹操作 ----

  /** 💡 提问 toggle：开 = PUT folderId+folderName；关（同夹再点）= folderId:null。 */
  const toggleAskInFolder = useCallback(
    async (folder: KsFolderTreeFolder) => {
      if (busy || sessionId === null || folder.folder_id === null) return
      if (sessionId.length === 0) {
        setOpError('无法确定当前会话，不能切换夹内提问')
        return
      }
      setBusy(true)
      setOpError(null)
      try {
        const turningOff = activeFolderId === folder.folder_id
        const result = await patchChatMode(sessionId, turningOff
          ? { folderId: null }
          : { folderId: folder.folder_id, folderName: folder.folder_name })
        setActiveFolderId(result.mode.folderId)
        if (!result.persisted) {
          setOpError('⚠️ 开关仅本会话内生效（状态未能落盘，重启 dsh 后会丢失）')
        }
      } catch (error) {
        setOpError(error instanceof Error ? error.message : String(error))
      } finally {
        setBusy(false)
      }
    },
    [busy, sessionId, activeFolderId],
  )

  /** 新建夹（header 内联输入）。 */
  const createFolder = useCallback(async () => {
    const name = newName.trim()
    if (name.length === 0 || busy) return
    setBusy(true)
    setOpError(null)
    try {
      await withSession((port, token, signal) =>
        createBookmarkFolder(port, name, token, signal))
      setNewName('')
      setShowNew(false)
      void loadAll()
    } catch (error) {
      setOpError(error instanceof Error ? error.message : String(error))
    } finally {
      setBusy(false)
    }
  }, [newName, busy, withSession, loadAll])

  /** 重命名提交。 */
  const submitRename = useCallback(async () => {
    const id = renamingId
    const name = renameValue.trim()
    if (id === null || name.length === 0 || busy) return
    setBusy(true)
    setOpError(null)
    try {
      await withSession((port, token, signal) =>
        renameBookmarkFolder(port, id, name, token, signal))
      setRenamingId(null)
      setRenameValue('')
      // 夹名变了 → 开着的开关也要带上新名（host 提示段/胶囊要显示新名）。
      if (sessionId !== null && activeFolderId === id) {
        try {
          await patchChatMode(sessionId, { folderId: id, folderName: name })
        } catch { /* 开关名同步失败不阻断；下一次开关操作会带回真值 */ }
      }
      void loadAll()
    } catch (error) {
      setOpError(error instanceof Error ? error.message : String(error))
    } finally {
      setBusy(false)
    }
  }, [renamingId, renameValue, busy, withSession, loadAll, sessionId, activeFolderId])

  /** 删除夹（确认后执行；收藏回未分类）。 */
  const confirmDeleteFolder = useCallback(async () => {
    const id = deleteId
    if (id === null || busy) return
    setBusy(true)
    setOpError(null)
    try {
      await withSession((port, token, signal) =>
        deleteBookmarkFolder(port, id, token, signal))
      // 删的是正开着的提问夹 → 开关一起关（引擎侧范围已消失）。
      if (sessionId !== null && activeFolderId === id) {
        try {
          await patchChatMode(sessionId, { folderId: null })
        } catch { /* 状态同步失败不阻断删除完成 */ }
        setActiveFolderId(null)
      }
      setDeleteId(null)
      setFolderPhase(null)
      void loadAll()
    } catch (error) {
      setOpError(error instanceof Error ? error.message : String(error))
      setFolderPhase(null)
    } finally {
      setBusy(false)
    }
  }, [deleteId, busy, withSession, loadAll, sessionId, activeFolderId])

  // ---- 跳转（文档叶 / 条款叶 → 宿主加载证据） ----

  const jumpTo = useCallback(
    (docId: string, page: number | null, rev: string | null) => {
      if (page === null || page < 1) return
      onOpenEvidence({ doc: docId, page, rev: rev ?? undefined })
    },
    [onOpenEvidence],
  )

  const toggleOpen = useCallback((key: string) => {
    setOpenMap((s) => ({ ...s, [key]: !s[key] }))
  }, [])

  // ---- 搜索：纯前端过滤（夹名/标准号/标准名/条款号），有词全自动展开 ----
  // （2026-10-28 四宫格统一搜索：query 改由宿主受控传入。）
  const query = props.query
  const q = query.trim().toLowerCase()
  const filteredTree = useMemo(() => {
    if (!q) return tree
    const docHit = (d: KsFolderDocNode): boolean =>
      (d.standard_no ?? '').toLowerCase().includes(q) ||
      (d.standard_name ?? '').toLowerCase().includes(q) ||
      d.clause_bookmarks.some((cb) =>
        (cb.clause_number ?? '').toLowerCase().includes(q) ||
        (cb.title ?? '').toLowerCase().includes(q))
    return tree
      .map((f) => {
        const folderHit = f.folder_name.toLowerCase().includes(q)
        const docs = folderHit ? f.docs : f.docs.filter(docHit)
        return { ...f, docs }
      })
      .filter((f) => f.docs.length > 0 || f.folder_name.toLowerCase().includes(q))
  }, [q, tree])

  const ready = load.status === 'ready'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, fontSize: 12 }}>
      {/* header：标题 + 新建 + 刷新 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)' }}>收藏目录</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button type="button" onClick={() => { setShowNew((s) => !s); setNewName('') }} disabled={busy} style={$btn} title="新建收藏夹">＋ 新建夹</button>
          <button type="button" onClick={retry} disabled={load.status === 'loading'} style={$btn}>刷新</button>
        </span>
      </div>

      {/* 新建夹内联输入 */}
      {showNew && (
        <div style={{ display: 'flex', gap: 4, padding: '6px 10px', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)' }}>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') void createFolder(); if (e.key === 'Escape') setShowNew(false) }}
            placeholder="收藏夹名称（≤60 字）"
            autoFocus
            style={{ ...$input, flex: 1 }}
          />
          <button type="button" onClick={() => void createFolder()} disabled={busy || newName.trim().length === 0} style={$btn}>创建</button>
          <button type="button" onClick={() => setShowNew(false)} style={$btn}>取消</button>
        </div>
      )}

      {/* 搜索框已上移到目录列顶部四宫格（宿主 KsEvidenceTab 统一搜索，本视图受控过滤）。 */}

      {opError !== null && (
        <div style={{ padding: '6px 10px', color: 'var(--dsw-alias-state-error-primary)', borderBottom: '1px solid var(--dsw-alias-border-l1, #eee)', background: 'var(--dsw-alias-state-error-secondary)', fontSize: 11, wordBreak: 'break-word' }}>
          {opError}
        </div>
      )}

      {/* body：树 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 4 }}>
        {load.status === 'loading' && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>载入收藏目录…（首次可能启动引擎，需要数秒）</div>
          </div>
        )}
        {load.status === 'error' && (
          <div style={{ ...$center, flexDirection: 'column', gap: 10 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)', maxWidth: 480, textAlign: 'center', wordBreak: 'break-word' }}>
              {load.message}
            </div>
            <button type="button" onClick={retry} style={$btn}>重试</button>
          </div>
        )}
        {ready && tree.length === 0 && (
          <div style={{ ...$center, flexDirection: 'column', gap: 6 }}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>暂无收藏</div>
            <div style={{ color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11, maxWidth: 380, textAlign: 'center', lineHeight: 1.5 }}>
              点上方「☆ 收藏本标准」或页面左缘「收藏本条款」——收藏会按你自建的收藏夹归入目录。
            </div>
          </div>
        )}
        {ready && filteredTree.length === 0 && q && (
          <div style={$center}>
            <div style={{ color: 'var(--dsw-alias-label-secondary, #666)' }}>没有匹配「{query.trim()}」的收藏</div>
          </div>
        )}
        {ready && filteredTree.map((folder) => {
          const fid = folder.folder_id
          const key = 'F:' + (fid ?? '_unfiled')
          const open = !!q || !!openMap[key]
          const folderActive = fid !== null && activeFolderId === fid
          const renaming = renamingId === fid
          const confirming = deleteId === fid && folderPhase === 'confirm-delete'
          return (
            <div key={key}>
              {/* 夹头行 */}
              <div style={{ ...$row, fontWeight: 700, marginTop: 4, flexWrap: 'wrap' }}>
                <span style={$caret} onClick={() => toggleOpen(key)}>{open ? '▾' : '▸'}</span>
                <span onClick={() => toggleOpen(key)} style={{ cursor: 'pointer' }}>
                  {folder.folder_name}
                  <span style={{ fontWeight: 400, color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 10.5, marginLeft: 6 }}>
                    {folder.doc_count > 0 ? `${folder.doc_count} 文档` : ''}{folder.clause_count > 0 ? ` · ${folder.clause_count} 条款` : ''}
                    {folder.doc_count === 0 && folder.clause_count === 0 ? '（空）' : ''}
                  </span>
                </span>
                <span style={{ marginLeft: 'auto', display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                  {fid !== null && (
                    <>
                      <button
                        type="button"
                        onClick={() => void toggleAskInFolder(folder)}
                        disabled={busy || sessionId === null}
                        style={folderActive ? $askBtnOn : $askBtn}
                        title={folderActive
                          ? '正在本收藏夹内提问——点击关闭恢复全库'
                          : '在本收藏夹内提问：本会话每一轮检索都限定在该夹内容内（标准级收藏按整本计）'}
                      >
                        {folderActive ? '💡 已限定提问' : '💡 提问'}
                      </button>
                      <button type="button" onClick={() => { setRenamingId(renaming ? null : fid); setRenameValue(renaming ? '' : folder.folder_name); setFolderPhase(null) }} style={$miniBtn} title="重命名">✏️</button>
                      <button type="button" onClick={() => { setDeleteId(confirming ? null : fid); setFolderPhase(confirming ? null : 'confirm-delete') }} style={{ ...$miniBtn, color: 'var(--dsw-alias-state-error-primary)' }} title="删除收藏夹（收藏本身保留，全部回未分类）">🗑</button>
                    </>
                  )}
                </span>
              </div>
              {/* 重命名内联 */}
              {renaming && fid !== null && (
                <div style={{ display: 'flex', gap: 4, padding: '4px 0 4px 18px' }}>
                  <input value={renameValue} onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') void submitRename(); if (e.key === 'Escape') setRenamingId(null) }}
                    autoFocus style={{ ...$input, flex: 1 }} />
                  <button type="button" onClick={() => void submitRename()} disabled={busy || renameValue.trim().length === 0} style={$btn}>保存</button>
                  <button type="button" onClick={() => setRenamingId(null)} style={$btn}>取消</button>
                </div>
              )}
              {/* 删除确认内联 */}
              {confirming && fid !== null && (
                <div style={$confirmBar}>
                  <span>删除收藏夹「{folder.folder_name}」？夹内收藏<b>不会被删除</b>，将全部移入「未分类」。</span>
                  <span style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <button type="button" onClick={() => void confirmDeleteFolder()} disabled={busy} style={{ ...$btn, color: 'var(--dsw-alias-state-error-primary)', borderColor: 'var(--dsw-alias-state-error-primary)' }}>确认删除</button>
                    <button type="button" onClick={() => { setDeleteId(null); setFolderPhase(null) }} style={$btn}>再想想</button>
                  </span>
                </div>
              )}
              {open && <FolderBody folder={folder} onJump={jumpTo} />}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** 一个夹的树体：docs → 分类分组 → 文档叶（→ 条款叶）。 */
function FolderBody(props: {
  folder: KsFolderTreeFolder
  onJump: (docId: string, page: number | null, rev: string | null) => void
}): JSX.Element {
  const { folder, onJump } = props
  if (folder.docs.length === 0) {
    return (
      <div style={{ paddingLeft: 18, padding: '4px 0', color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 11 }}>
        空收藏夹——收藏时可选择放入此夹。
      </div>
    )
  }
  const roots = buildGroupTree(folder.docs)
  return <GroupList groups={roots} onJump={onJump} />
}

/** 递归渲染分组列表。 */
function GroupList(props: {
  groups: DocGroupNode[]
  onJump: (docId: string, page: number | null, rev: string | null) => void
}): JSX.Element {
  const { groups, onJump } = props
  return (
    <div style={{ padding: '1px 0 2px 14px' }}>
      {groups.map((g) => (
        <GroupRow key={g.name} group={g} onJump={onJump} />
      ))}
    </div>
  )
}

/** 一级分组行（递归 children + 文档叶）。 */
function GroupRow(props: {
  group: DocGroupNode
  onJump: (docId: string, page: number | null, rev: string | null) => void
}): JSX.Element {
  const { group, onJump } = props
  const [open, setOpen] = useState(false)
  const total = group.docs.length + group.groups.reduce((s, g) => s + g.docs.length, 0)
  return (
    <div>
      <div style={{ ...$row, fontSize: 11.5, fontWeight: 600, color: 'var(--dsw-alias-label-secondary, #666)' }} onClick={() => setOpen((s) => !s)}>
        <span style={$caret}>{total > 0 ? (open ? '▾' : '▸') : '·'}</span>
        <span>{group.name}</span>
        <span style={{ fontWeight: 400, color: 'var(--dsw-alias-label-tertiary, #999)', fontSize: 10 }}>
          {' '}({total})
        </span>
      </div>
      {open && (
        <div style={{ padding: '1px 0 2px 14px' }}>
          {group.docs.map((d) => (
            <DocLeaf key={d.doc_id} doc={d} onJump={onJump} />
          ))}
          {group.groups.length > 0 && <GroupList groups={group.groups} onJump={onJump} />}
        </div>
      )}
    </div>
  )
}

/** 文档叶：标准级收藏=整本（蓝色徽标整本）；条款级收藏=展开条款子叶。 */
function DocLeaf(props: {
  doc: KsFolderDocNode
  onJump: (docId: string, page: number | null, rev: string | null) => void
}): JSX.Element {
  const { doc, onJump } = props
  const [open, setOpen] = useState(false)
  const label = doc.standard_no ?? doc.standard_name ?? doc.doc_id
  const struck = doc.legal_status !== null && doc.legal_status !== 'effective'
  return (
    <div>
      <div style={{ ...$leaf, ...(struck ? { opacity: 0.7 } : {}) }}>
        <span
          style={{ cursor: 'pointer' }}
          onClick={() => onJump(doc.doc_id, 1, null)}
          title="打开标准（首页）"
        >
          {doc.standard_no ?? '（无编号）'} {doc.standard_name ?? ''}
          {doc.doc_bookmarked && (
            <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--dsw-alias-link, #1565c0)' }} title="标准级收藏——💡提问时整本入范围">整本</span>
          )}
        </span>
        {doc.clause_bookmarks.length > 0 && (
          <span
            style={{ marginLeft: 8, cursor: 'pointer', color: 'var(--dsw-alias-link, #1565c0)', fontSize: 10.5 }}
            onClick={() => setOpen((s) => !s)}
            title="展开条款收藏"
          >
            {open ? '▾' : '▸'} {doc.clause_bookmarks.length} 条
          </span>
        )}
      </div>
      {open && doc.clause_bookmarks.map((cb) => (
        <div key={cb.bookmark_id} style={{ ...$leaf, paddingLeft: 16, fontSize: 11 }}>
          <span
            style={{ cursor: 'pointer' }}
            onClick={() => onJump(doc.doc_id, cb.page_start, null)}
            title="打开 PDF 证据"
          >
            {cb.clause_number ?? '（条款）'} {cb.title ?? ''}
          </span>
        </div>
      ))}
    </div>
  )
}

// ---- helpers (pure) --------------------------------------------------

/**
 * 把夹内 docs 按分类路径组装成嵌套分组树。
 * 路径级数按 path 实有级渲染：l1 恒有（缺省「未分类领域」）；l2 缺省「其他」；
 * 有 l4 时 l3 作分组容器级、l4 是叶分组；无 l4 时 l3（若有）作为叶分组、文档直挂。
 */
function buildGroupTree(docs: KsFolderDocNode[]): DocGroupNode[] {
  const getOrCreate = (parent: DocGroupNode[], name: string): DocGroupNode => {
    const found = parent.find((g) => g.name === name)
    if (found !== undefined) return found
    const node: DocGroupNode = { name, docs: [], groups: [] }
    parent.push(node)
    return node
  }
  const roots: DocGroupNode[] = []
  for (const d of docs) {
    const p = d.path
    const g1 = getOrCreate(roots, p?.l1 ?? '未分类领域')
    const g2 = getOrCreate(g1.groups, p?.l2 ?? '其他')
    if (p?.l4 != null) {
      // l1 > l2 > l3(组) > l4(叶组) > doc
      const g3 = getOrCreate(g2.groups, p.l3 ?? p.l4)
      getOrCreate(g3.groups, p.l4).docs.push(d)
    } else if (p?.l3 != null) {
      // l1 > l2 > l3(叶组) > doc
      getOrCreate(g2.groups, p.l3).docs.push(d)
    } else {
      g2.docs.push(d)
    }
  }
  return roots
}

// ---- small inline styles (mirrors KsFilesTab / KsEvidenceTab) ------

const $center: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  minHeight: 160,
}

const $btn: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '4px 10px',
  cursor: 'pointer',
  fontSize: 11.5,
}

const $miniBtn: React.CSSProperties = {
  border: 'none',
  background: 'transparent',
  cursor: 'pointer',
  fontSize: 12,
  padding: '1px 4px',
  lineHeight: 1.3,
}

const $askBtn: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  borderRadius: 4,
  padding: '1px 8px',
  cursor: 'pointer',
  fontSize: 10.5,
  whiteSpace: 'nowrap',
}

const $askBtnOn: React.CSSProperties = {
  ...$askBtn,
  // dark-theme paired fixed button colors（白底深字，两主题都读得清）
  background: '#fff',
  color: '#7a4a00',
  borderColor: '#d99000',
  fontWeight: 600,
}

const $input: React.CSSProperties = {
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  padding: '4px 8px',
  background: 'var(--dsw-alias-bg-layer-1, #fff)',
  color: 'var(--dsw-alias-label-primary, #111)',
  fontSize: 12,
  outline: 'none',
}

// （2026-10-28）$search/$searchInput/$searchClear 已删——搜索框上移到目录列
// 顶部四宫格，由宿主 KsEvidenceTab 持有；本视图经 props.query 受控过滤。

const $confirmBar: React.CSSProperties = {
  margin: '4px 0 4px 18px',
  padding: '6px 8px',
  border: '1px solid var(--dsw-alias-border-l2, #ccc)',
  borderRadius: 4,
  background: 'var(--dsw-alias-bg-layer-2, #fff)',
  fontSize: 11,
  lineHeight: 1.4,
  color: 'var(--dsw-alias-label-secondary, #666)',
}

const $row: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: '2px 4px',
  fontSize: 11.5,
  cursor: 'pointer',
  borderRadius: 4,
  alignItems: 'center',
  lineHeight: 1.4,
  color: 'var(--dsw-alias-label-primary, #111)',
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

const $leaf: React.CSSProperties = {
  padding: '2px 4px',
  fontSize: 11.5,
  borderRadius: 4,
  color: 'var(--dsw-alias-label-primary, #111)',
  lineHeight: 1.35,
  wordBreak: 'break-word',
  overflowWrap: 'anywhere',
}
