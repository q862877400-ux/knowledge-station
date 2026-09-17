/**
 * ks-dsh-plugin — client/KsMaterialsPanel.tsx
 *
 * 📚 参考资料面板（Phase B 第五步，2026-09-17）：**评审闸门的用户界面**。
 *
 * ## 为什么这个面板是整条链的关键
 * 方案 §6 把评审定为**硬门**——`review_status != 'approved'` 的材料不得进入检索、
 * 不得进入分析、不得出现在产出物引用里。但在本面板之前，**批准只能调 API**（curl），
 * 等于"硬门装了但没给钥匙"。这里补上那把钥匙。
 *
 * ## 面板只做**用户**能做的事（三条纪律）
 * 1. **批准/拒绝是用户动作**：面板没有"自动批准"、没有"全部通过"；每份材料逐个决定。
 * 2. **轴 A 与轴 B 分开摆，不合成一个"可信度"**：来源层级（T0~T4，业主明说用户可改）
 *    与任务内效力（criterion=本任务准则 / reference）并排显示、各自独立设置——
 *    合成一个分数就必然错一个（公司制度例）。
 * 3. **评审前必须能读到正文**：每份材料可就地展开切片（否则"批准"是盲签）。
 *
 * ## 嵌入方式
 * 与 `KsReportPanel` 同款：由 `KsSettingsSection` 的「参考资料」折叠类目承载，
 * 收起时 `visible=false`（挂载但**零请求**），展开才开始拉数据。
 *
 * 全程零 LLM；每次调用都现拉 host 代理（**无缓存**——宁愿慢，也不要因为"看到旧状态"
 * 就把一份材料批了或拒了）。
 */

import * as React from 'react'
import { useCallback, useEffect, useState } from 'react'

import {
  collectMaterialUrl,
  createMaterialProject,
  fetchMaterialChunks,
  fetchMaterialInbox,
  fetchMaterialProjects,
  fetchMaterialTiers,
  fetchMaterials,
  reviewMaterial,
  scanMaterialProject,
  setMaterialRole,
  setMaterialTier,
  type KsMaterial,
  type KsMaterialChunk,
  type KsMaterialProject,
  type KsMaterialTierDef,
} from './api'

export interface KsMaterialsPanelProps {
  /** 由 <details onToggle> 驱动——收起 = 挂载但零请求（懒加载门）。 */
  visible: boolean
  /** 把 `/materials use <prj_id>` 提示给用户（可选：宿主可把它写进输入框）。 */
  onUseProject?: (projectId: string, projectName: string) => void
}

const GREEN = '#2e7d32'
const RED = '#c0392b'
const GRAY = '#888'

/** 评审状态的显示口径（**唯一一份**，别在别处再写一遍）。 */
const REVIEW_LABEL: Record<string, { text: string; color: string }> = {
  approved: { text: '✅ 已批准（可进入作答）', color: GREEN },
  pending: { text: '⏳ 待评审（不会进入作答）', color: '#b8860b' },
  rejected: { text: '❌ 已拒绝（不会进入作答）', color: RED },
}

const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '未声明效力' },
  { value: 'criterion', label: '本任务准则（轴 B：以它为准绳）' },
  { value: 'reference', label: '参考（不作准绳）' },
]

function reviewLabel(status: string | null | undefined): { text: string; color: string } {
  return REVIEW_LABEL[status ?? ''] ?? { text: `未知状态（${status ?? 'null'}）`, color: GRAY }
}

/** 行内小按钮样式（与设置区其它面板保持同一视觉语言）。 */
function btnStyle(disabled = false): React.CSSProperties {
  return {
    padding: '3px 10px',
    fontSize: 12,
    borderRadius: 4,
    border: '1px solid var(--dsw-alias-border, #ccc)',
    background: 'transparent',
    color: 'inherit',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  }
}

export function KsMaterialsPanel(props: KsMaterialsPanelProps): React.ReactElement {
  const { visible, onUseProject } = props
  const [projects, setProjects] = useState<KsMaterialProject[]>([])
  const [projectId, setProjectId] = useState<string>('')
  const [materials, setMaterials] = useState<KsMaterial[]>([])
  const [tiers, setTiers] = useState<KsMaterialTierDef[]>([])
  const [inbox, setInbox] = useState<{ dir: string; files: { file_name: string; size: number }[] }>(
    { dir: '', files: [] })
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState<string>('')          // 正在操作的材料/动作标签
  const [error, setError] = useState<string>('')
  const [notice, setNotice] = useState<string>('')
  /**
   * 第三条反馈通道（**琥珀色**）：请求本身成功，但结果**不是成功**。
   *
   * 为什么需要它：引擎刻意把"没采到"表达成 `HTTP 200 + collected:false + reason`
   * （原因要给**人**看），既不是异常也不该被读成成功。塞进 `error` 会把
   * "网址抓不到"与"引擎/网络挂了"混成同一种红字；塞进 `notice`（灰）又太弱。
   */
  const [warn, setWarn] = useState<string>('')
  const [newName, setNewName] = useState('')
  const [collectUrl, setCollectUrl] = useState('')
  const [collectNote, setCollectNote] = useState('')
  const [openChunks, setOpenChunks] = useState<Record<string, KsMaterialChunk[] | 'loading'>>({})

  const reloadProjects = useCallback(async (signal?: AbortSignal): Promise<KsMaterialProject[]> => {
    const list = await fetchMaterialProjects(signal)
    setProjects(list)
    return list
  }, [])

  const reloadMaterials = useCallback(async (pid: string, signal?: AbortSignal) => {
    const list = await fetchMaterials(pid, undefined, signal)
    setMaterials(list)
  }, [])

  const reloadInbox = useCallback(async (pid: string, signal?: AbortSignal) => {
    try {
      setInbox(await fetchMaterialInbox(pid, signal))
    } catch (err) {
      // ⚠ 这里原先**只清空不报错**，而注释却写着"但要**说**"——独立复核 2026-09-17 报的 LOW：
      // 收件箱读取失败会渲染成「未登记 0 个文件」，与"文件夹确实是空的"**长得一模一样**
      // （用户会以为文件没放对）。现在如实说，并把"0"的来源讲清楚。
      if (err instanceof Error && err.name === 'AbortError') return
      setInbox({ dir: '', files: [] })
      setError(`收件箱读取失败：${err instanceof Error ? err.message : String(err)}`
        + '（下面的"未登记"计数不可信——不是"没有文件"，是**没读到**）')
    }
  }, [])

  // 懒加载门：只有展开时才请求（与 KsReportPanel 同款）
  useEffect(() => {
    if (!visible) return undefined
    const ctl = new AbortController()
    let alive = true
    setLoading(true)
    setError('')
    void (async () => {
      try {
        const [list, tierDefs] = await Promise.all([
          reloadProjects(ctl.signal),
          fetchMaterialTiers(ctl.signal).catch(() => [] as KsMaterialTierDef[]),
        ])
        if (!alive) return
        setTiers(tierDefs)
        const first = list.length > 0 ? list[0].project_id : ''
        setProjectId((cur) => (cur !== '' && list.some((p) => p.project_id === cur) ? cur : first))
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => { alive = false; ctl.abort() }
  }, [visible, reloadProjects])

  // 选中项目后拉它的材料与收件箱
  useEffect(() => {
    if (!visible || projectId === '') {
      setMaterials([])
      setInbox({ dir: '', files: [] })
      return undefined
    }
    const ctl = new AbortController()
    let alive = true
    setLoading(true)
    setError('')
    void (async () => {
      try {
        await Promise.all([
          reloadMaterials(projectId, ctl.signal),
          reloadInbox(projectId, ctl.signal),
        ])
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => { alive = false; ctl.abort() }
  }, [visible, projectId, reloadMaterials, reloadInbox])

  /**
   * 统一的"做一件事 → 刷新 → 报错如实说"包装（避免每个按钮各写一遍 try）。
   *
   * ⚠ `refreshFor` 必须由调用方**显式给**要刷新的项目 id（独立复核 2026-09-17 报的 LOW）：
   * 原先这里闭包捕获 `projectId`，而「新建项目」在 `run` 内部才 `setProjectId(新 id)`，
   * 那个 setState 还没提交 ⇒ 刷新用的是**旧 id**，于是每建一个项目就白发一次
   * `GET /ks/materials/list?project_id=`（空 id，主机回 400），纯浪费往返。
   * 现在 `refreshFor: null` 表示"不需要刷新列表"（新建项目时列表本来就该空）。
   */
  const run = useCallback(async (
    label: string, fn: () => Promise<string>, refreshFor: string | null = null,
  ) => {
    setBusy(label)
    setError('')
    setNotice('')
    setWarn('')
    try {
      setNotice(await fn())
      if (refreshFor !== null) await reloadMaterials(refreshFor)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy('')
    }
  }, [reloadMaterials])

  const onCreate = useCallback(() => {
    const name = newName.trim()
    if (name === '') { setError('请先填项目名'); return }
    // 新建时**不刷新材料列表**（新项目必然没有材料；刷旧 id 只会白发一次请求）
    void run('create', async () => {
      const proj = await createMaterialProject(name)
      setNewName('')
      await reloadProjects()
      setProjectId(proj.project_id)
      return `已建项目「${proj.name}」。把材料文件放进它的参考资料文件夹后点「扫描收件」。`
    }, null)
  }, [newName, reloadProjects, run])

  const onScan = useCallback(() => {
    if (projectId === '') return
    void run('scan', async () => {
      const r = await scanMaterialProject(projectId)
      await reloadInbox(projectId)
      return `扫描完成：登记 ${r.registered} / 共 ${r.scanned} 个文件。**新登记的材料是待评审状态**，`
        + '需你在下方逐份批准后才会进入作答。'
    }, projectId)
  }, [projectId, reloadInbox, run])

  /**
   * 按网址**自采一份**（Phase D-3 的界面接线；纪律与主机/引擎同源）。
   *
   * 三条**刻意**的设计：
   * 1. **不提供任何"可信度"输入框**：轴 A 由系统判据起（T3=仅线索），
   *    要改只能采完之后在这里改（`onTier`）。给个下拉框等于让"自采"变成自评。
   * 2. **没采到走琥珀色 `warn`**（不是红）：原因要**显示给人看**（HTTP 404 / SSRF 拒绝 /
   *    不是文本 / 正文空），且这条**没有**登记成材料——不说清用户会以为白采了一次。
   * 3. **一次一条**：没有批量（方案 §11.4 的采集预算未定），界面也不暗示能批量。
   */
  const onCollect = useCallback(() => {
    if (projectId === '') return
    const url = collectUrl.trim()
    if (url === '') { setError('请先填网址（要**原始出处**的网页地址）'); return }
    void run('collect', async () => {
      const out = await collectMaterialUrl(projectId, {
        url, note: collectNote.trim() === '' ? undefined : collectNote.trim(),
      })
      if (!out.collected) {
        // 请求成功、结果不是成功 ⇒ 如实说，并明确"这次没有登记任何东西"
        setWarn(`没有采到：${out.reason ?? '原因未给'}`
          + (out.status !== undefined ? `（HTTP ${out.status}）` : '')
          + '。这条**没有**登记成材料——可以换个**原始出处**的网址再试，'
          + '或把正文粘贴/保存成文件放进上面的参考资料文件夹。')
        return ''
      }
      setCollectUrl('')
      const title = out.material?.title ?? '（标题取自页面）'
      const chunks = out.material?.chunk_count ?? 0
      return `已登记「${title}」（${chunks} 个切片，来源层级 **T3=仅线索**）`
        + (out.duplicate === true
          ? '——⚠ 这个网址的内容**与项目里已有的一份相同**，引擎**没有**重复登记。'
          : '。')
        + (out.truncated === true ? '⚠ 正文被截断到长度上限（不是全文）。' : '')
        + '它现在是**待评审**、**不会**进入任何结论，需你在下方批准（本面板不能代批）。'
    }, projectId)
  }, [collectNote, collectUrl, projectId, run])

  const onReview = useCallback((m: KsMaterial, decision: 'approved' | 'rejected') => {
    void run(`${decision}:${m.material_id}`, async () => {
      const out = await reviewMaterial(m.material_id, decision)
      const label = reviewLabel(out.review_status).text
      // ⚠ Track L 的**后果**必须让用户看到（方案 §7 可见性硬需求）：批准一份采到的
      // 标准/法规会**自动写进法条库**——那是批准的副作用，静默通过等于用户不知道
      // 库里多了东西。失败尤其要说（否则"批准成功"会被读成"入库成功"）。
      const tl = out.track_l ?? null
      const tlText = tl === null ? ''
        : tl.action === 'import' ? '；已自动入库为法条（Track L）'
          : tl.action === 'link' ? '；库内已有，已回指该法条'
            : tl.action === 'skip' ? '；未识别为法规/标准，未动法条库'
              : `；⚠ Track L 未完成（${tl.action ?? '未知'}）：${tl.why ?? '原因未给'}`
      return `「${m.title}」→ ${label}${tlText}`
    }, projectId)
  }, [projectId, run])

  const onTier = useCallback((m: KsMaterial, tier: string) => {
    void run(`tier:${m.material_id}`, async () => {
      // ⚠ 必须带 `reason`：引擎会把 `tier_reason` **写成**这个值，不带就把原判据擦成空
      // （独立复核 2026-09-17 实测的数据丢失）。带上"从哪改到哪"，审计链才不断。
      const out = await setMaterialTier(
        m.material_id, tier, `用户改级：${m.source_tier ?? '未判级'} → ${tier}`)
      return `「${m.title}」来源层级 → ${out.tier_label ?? out.source_tier}（已记为**用户改的**）`
    }, projectId)
  }, [projectId, run])

  const onRole = useCallback((m: KsMaterial, role: string) => {
    void run(`role:${m.material_id}`, async () => {
      await setMaterialRole(m.material_id, role === '' ? null : (role as 'criterion' | 'reference'))
      return `「${m.title}」任务内效力已更新`
    }, projectId)
  }, [projectId, run])

  const onToggleChunks = useCallback((m: KsMaterial) => {
    const cur = openChunks[m.material_id]
    if (cur !== undefined) {
      setOpenChunks((prev) => {
        const next = { ...prev }
        delete next[m.material_id]
        return next
      })
      return
    }
    setOpenChunks((prev) => ({ ...prev, [m.material_id]: 'loading' }))
    void (async () => {
      try {
        const page = await fetchMaterialChunks(m.material_id, 0, 20)
        setOpenChunks((prev) => ({ ...prev, [m.material_id]: page.chunks }))
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
        setOpenChunks((prev) => {
          const next = { ...prev }
          delete next[m.material_id]
          return next
        })
      }
    })()
  }, [openChunks])

  if (!visible) {
    return <p style={{ fontSize: 12, color: GRAY, margin: 0 }}>展开后加载参考资料（收起时不发任何请求）。</p>
  }

  const current = projects.find((p) => p.project_id === projectId)

  return (
    <div style={{ fontSize: 13 }}>
      <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
        <strong>评审是硬门</strong>：只有<strong>已批准</strong>的材料会进入作答与产出物。
        未批准的材料不会被检索、不会被引用。所有决定都由<strong>你</strong>做出（本面板没有"全部通过"）。
      </p>

      {/* ---------------------------------------------------- 项目 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span>参考资料项目</span>
            <select
              aria-label="参考资料项目"
              value={projectId}
              onChange={(e) => setProjectId(e.currentTarget.value)}
              style={{ padding: '3px 6px', fontSize: 12, maxWidth: 320 }}
            >
              <option value="">（未选择）</option>
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id}>{p.name}（{p.project_id}）</option>
              ))}
            </select>
          </label>
          <input
            aria-label="新建项目名"
            placeholder="新建项目名"
            value={newName}
            onChange={(e) => setNewName(e.currentTarget.value)}
            style={{ padding: '3px 6px', fontSize: 12, width: 160 }}
          />
          <button type="button" style={btnStyle(busy !== '')} disabled={busy !== ''} onClick={onCreate}>
            新建项目
          </button>
          {current !== undefined && (
            <button
              type="button"
              style={btnStyle(false)}
              title="把这个 id 交给会话级绑定（等效于输入 /materials use <id>）"
              onClick={() => onUseProject?.(current.project_id, current.name)}
            >
              在会话中使用
            </button>
          )}
        </div>
        {current !== undefined && (
          <p style={{ margin: '6px 0 0', fontSize: 12, color: 'var(--dsw-alias-label-secondary, #666)' }}>
            会话里问问题时想用本项目的材料，输入 <code>/materials use {current.project_id} {current.name}</code>
            （未绑定时材料<strong>完全不参与</strong>作答）。
          </p>
        )}
      </div>

      {/* ---------------------------------------------------- 收件 */}
      {projectId !== '' && (
        <div style={{ marginBottom: 12, padding: '8px 10px', border: '1px solid var(--dsw-alias-border, #e0e0e0)', borderRadius: 6 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <strong>参考资料文件夹</strong>
            <span style={{ fontSize: 12, color: GRAY }}>
              未登记 {inbox.files.length} 个文件
            </span>
            <button type="button" style={btnStyle(busy !== '')} disabled={busy !== ''} onClick={onScan}>
              扫描收件
            </button>
          </div>
          {inbox.dir !== '' && (
            <p style={{ margin: '6px 0 0', fontSize: 12, color: GRAY }}>
              把 PDF / DOCX / TXT / MD 放进 <code>{inbox.dir}</code> 再点「扫描收件」。
            </p>
          )}
          {inbox.files.length > 0 && (
            <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 12, color: GRAY }}>
              {inbox.files.slice(0, 10).map((f) => (
                <li key={f.file_name}>{f.file_name}</li>
              ))}
              {inbox.files.length > 10 && <li>… 另有 {inbox.files.length - 10} 个</li>}
            </ul>
          )}

          {/* ------------------------------------------------ 自采（按网址） */}
          <div style={{
            marginTop: 10, paddingTop: 8,
            borderTop: '1px dashed var(--dsw-alias-border, #e0e0e0)',
          }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <strong>自采一份</strong>
              <input
                aria-label="自采网址"
                placeholder="https://…（要「原始出处」的网页正文）"
                value={collectUrl}
                onChange={(e) => setCollectUrl(e.currentTarget.value)}
                style={{ padding: '3px 6px', fontSize: 12, width: 320 }}
              />
              <input
                aria-label="自采备注"
                placeholder="备注（可选，评审人会看到这条是怎么来的）"
                value={collectNote}
                onChange={(e) => setCollectNote(e.currentTarget.value)}
                style={{ padding: '3px 6px', fontSize: 12, width: 220 }}
              />
              <button
                type="button"
                style={btnStyle(busy !== '' || collectUrl.trim() === '')}
                disabled={busy !== '' || collectUrl.trim() === ''}
                onClick={onCollect}
              >
                自采一条
              </button>
            </div>
            <p style={{ margin: '6px 0 0', fontSize: 12, color: GRAY }}>
              采回来的是 <strong>待评审</strong>材料，来源层级由系统判为 <strong>T3=仅线索</strong>
              （<strong>不得单独支撑结论</strong>、不能与其它网页互证）；批准前<strong>不会</strong>进入作答或产出。
              {' '}只收<strong>一条</strong>（预算未定，没有批量），且只收<strong>网页正文</strong>：
              PDF / 图片 / 压缩包请下载后放进上面的文件夹。
            </p>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------- 动作反馈 */}
      {error !== '' && (
        <p role="alert" style={{ margin: '0 0 8px', color: RED, fontSize: 12 }}>
          操作失败：{error}
        </p>
      )}
      {warn !== '' && (
        <p role="status" style={{ margin: '0 0 8px', color: 'var(--dsw-alias-warn, #b8860b)', fontSize: 12 }}>
          ⚠ {warn}
        </p>
      )}
      {notice !== '' && (
        <p style={{ margin: '0 0 8px', color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 12 }}>
          {notice}
        </p>
      )}
      {loading && <p style={{ margin: '0 0 8px', fontSize: 12, color: GRAY }}>加载中…</p>}

      {/* ---------------------------------------------------- 材料表 */}
      {projectId === '' && (
        <p style={{ fontSize: 12, color: GRAY }}>先选一个项目（或在上面新建）。</p>
      )}
      {projectId !== '' && !loading && materials.length === 0 && (
        <p style={{ fontSize: 12, color: GRAY }}>
          这个项目里还没有已登记的材料：把文件放进参考资料文件夹后点「扫描收件」，
          或用上面的「自采一条」按网址抓一份网页正文（同样要**你**批准后才算数）。
        </p>
      )}

      {materials.map((m) => {
        const rev = reviewLabel(m.review_status)
        const chunks = openChunks[m.material_id]
        return (
          <div
            key={m.material_id}
            style={{
              border: '1px solid var(--dsw-alias-border, #e0e0e0)',
              borderRadius: 6, padding: '8px 10px', marginBottom: 8,
            }}
          >
            <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
              <strong>{m.title}</strong>
              <span style={{ fontSize: 12, color: rev.color }}>{rev.text}</span>
              <span style={{ fontSize: 12, color: GRAY }}>
                {m.chunk_count ?? 0} 个切片 · {m.origin ?? 'user'} / {m.kind ?? 'other'}
              </span>
            </div>

            {/* 两个轴**分开**摆：合成一个"可信度"就必然错一个（公司制度例） */}
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginTop: 6 }}>
              <label style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 12 }}>
                <span>轴 A 来源可信度</span>
                <select
                  aria-label={`来源层级 ${m.title}`}
                  value={m.source_tier ?? ''}
                  onChange={(e) => onTier(m, e.currentTarget.value)}
                  disabled={busy !== ''}
                  style={{ fontSize: 12, maxWidth: 260 }}
                >
                  {tiers.length === 0 && m.source_tier != null && (
                    <option value={m.source_tier}>{m.tier_label ?? m.source_tier}</option>
                  )}
                  {tiers.map((t) => (
                    <option key={t.tier} value={t.tier}>{t.tier} {t.label}</option>
                  ))}
                </select>
                {m.tier_source === 'user' && <span style={{ color: GRAY }}>（你改的）</span>}
              </label>
              <label style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 12 }}>
                <span>轴 B 任务内效力</span>
                <select
                  aria-label={`任务内效力 ${m.title}`}
                  value={m.task_role ?? ''}
                  onChange={(e) => onRole(m, e.currentTarget.value)}
                  disabled={busy !== ''}
                  style={{ fontSize: 12, maxWidth: 260 }}
                >
                  {ROLE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
            </div>

            {m.tier_reason != null && m.tier_reason !== '' && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: GRAY }}>判级说明：{m.tier_reason}</p>
            )}
            {m.source_tier === 'T4' && m.task_role === 'criterion' && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: RED }}>
                ⚠ 你把来源不可回溯（T4）的材料声明为准绳——按纪律它<strong>不会按准则承重</strong>，
                只列在「已知不可用」里。要让它承重，请先把它改成可回溯的来源层级。
              </p>
            )}

            <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                style={btnStyle(busy !== '' || m.review_status === 'approved')}
                disabled={busy !== '' || m.review_status === 'approved'}
                onClick={() => onReview(m, 'approved')}
              >
                批准（可进入作答）
              </button>
              <button
                type="button"
                style={btnStyle(busy !== '' || m.review_status === 'rejected')}
                disabled={busy !== '' || m.review_status === 'rejected'}
                onClick={() => onReview(m, 'rejected')}
              >
                拒绝
              </button>
              <button type="button" style={btnStyle(false)} onClick={() => onToggleChunks(m)}>
                {chunks === undefined ? '读正文（评审前必看）' : '收起正文'}
              </button>
            </div>

            {chunks === 'loading' && (
              <p style={{ margin: '6px 0 0', fontSize: 12, color: GRAY }}>读取切片…</p>
            )}
            {Array.isArray(chunks) && (
              <div style={{ marginTop: 6, maxHeight: 240, overflow: 'auto', fontSize: 12 }}>
                {chunks.length === 0 && (
                  <p style={{ margin: 0, color: GRAY }}>
                    没有切片——该文件可能没解析出文本（扫描件？）。<strong>没有正文就无法评审</strong>。
                  </p>
                )}
                {chunks.map((c, i) => (
                  <p key={`${c.char_start}-${i}`} style={{ margin: '0 0 4px' }}>
                    <span style={{ color: GRAY }}>
                      [{i}] {c.page != null ? `第${c.page}页 ` : ''}{c.char_start}-{c.char_end}
                    </span>
                    <br />
                    {c.text}
                  </p>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
