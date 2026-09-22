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
import { useCallback, useEffect, useReducer, useState } from 'react'

import {
  collectMaterialUrl,
  createMaterialProject,
  exportResearchDraft,
  exportResearchReport,
  fetchExportBlob,
  fetchMaterialChunks,
  fetchMaterialInbox,
  fetchMaterialLocators,
  fetchMaterialProjects,
  fetchMaterialTiers,
  fetchMaterials,
  fetchProjectLocators,
  reverifyMaterialLocators,
  reviewMaterial,
  scanMaterialProject,
  setMaterialRole,
  setMaterialTier,
  type KsLocatorHealth,
  type KsMaterial,
  type KsMaterialChunk,
  type KsMaterialProject,
  type KsMaterialTierDef,
  type KsResearchDraft,
  type KsResearchReport,
} from './api'

export interface KsMaterialsPanelProps {
  /** 由 <details onToggle> 驱动——收起 = 挂载但零请求（懒加载门）。 */
  visible: boolean
  /** 把 `/materials use <prj_id>` 提示给用户（可选：宿主可把它写进输入框）。 */
  onUseProject?: (projectId: string, projectName: string) => void
}

/* ⚠ 2026-09-22 S3-a：写死色值换**宿主真 token**（F0 教训 + ui-audit 点名过本文件 ×6）——
   一个名字一处声明，值只许 var(...)，不许字面兜底。 */
const GREEN = 'var(--dsw-alias-state-success-primary)'
const RED = 'var(--dsw-alias-state-error-primary)'
const GRAY = 'var(--dsw-alias-label-tertiary)'

/** 评审状态的显示口径（**唯一一份**，别在别处再写一遍）。词照 v3 定稿：可作依据/待评审/不可用。 */
const REVIEW_LABEL: Record<string, { text: string; color: string }> = {
  approved: { text: '可作依据', color: GREEN },
  pending: { text: '待评审（不会进入作答）', color: 'var(--dsw-alias-state-warn-primary)' },
  rejected: { text: '不可用（不会进入作答）', color: RED },
}

const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: '未声明' },
  { value: 'criterion', label: '必须遵守（以此为准）' },
  { value: 'reference', label: '仅供参考' },
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
    border: '1px solid var(--dsw-alias-border-l2)',
    background: 'transparent',
    color: 'inherit',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  }
}

/**
 * 编译期穷尽性断言（复核 b11 的 LOW-4，2026-09-18）。
 *
 * 为什么需要它：后端的状态**取值域会增长**（`unknown` → 加 `no_locators` → 加 `health_error`），
 * 而界面过去是一串 `status === 'x' && <p/>`。新增一个取值却忘了加分支时，**什么都不报**
 * ——那一类材料在界面上**一个标记都没有**，读起来像"全都健康"（实测过：只改产物让条件
 * 永不成立时，离线门禁仍 71/71 全绿）。`tsc` 也**不会**报错（b11 的变异 M5b 证实：
 * 往 union 里加一个没人渲染的成员，`tsc` 仍 GREEN 0）。
 *
 * 用法：`switch` 的 `default` 里调它。只要 union 多出一个没人处理的成员，
 * `status` 在 default 分支里就**不再是 `never`** ⇒ 类型不匹配 ⇒ `npm run typecheck` 直接红。
 */
function assertNever(status: never): never {
  throw new Error(`未处理的锚点状态（新增取值必须同时加分支）: ${String(status)}`)
}

/**
 * 锚点标记（**唯一出口**）：`switch` + 穷尽性断言，见 `assertNever` 的注释。
 *
 * ⚠ 理由**照抄后端**（`locator.py` 的 `why`），界面**不自己解释 status**：
 * 早先这里写死过"解析器身份变了"，而 `stale` 有**两个**成因（解析器变了 / **源文件字节变了**，
 * 后者是**确定**失效不是"可能"）——写死一句就等于替后端下了它没下的结论。
 *
 * ⚠ **导出**只是为了离线**渲染级**冒烟（`scripts/smoke-anchor-mark.mjs` 用 `react-dom/server`
 * 真渲染它）——这就是 b11 建议"收编渲染用例"的**零依赖版本**：不装 jsdom，
 * 用仓库根 `node_modules` 里已有的 react/react-dom 做静态渲染。
 */
export function AnchorMark(props: { status?: KsLocatorHealth['status']; why?: string }): React.ReactElement | null {
  const why = props.why || '（后端未给原因）'
  switch (props.status) {
    // 没问题 / 没有区间可失效 ⇒ 不加噪声
    case undefined:
    case 'ok':
    case 'no_locators':
      return null
    case 'stale':
      return (
        <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--dsw-alias-state-warn-primary)' }}>
          ⚠ <strong>引用锚点需复算</strong>：{why}
          <br />（需复算**不代表已经坏了**。）点「复算锚点」用当前解析器重算比对。
        </p>
      )
    case 'unknown':
      return (
        <p style={{ margin: '4px 0 0', fontSize: 12, color: GRAY }}>
          ⚠ <strong>引用锚点未验证</strong>：{why}
          <br /><strong>不等于</strong>有问题，但引用位置<strong>未经确认</strong>。
        </p>
      )
    // ⚠ `health_error` **不是**健康状态，是"后端判据跑挂了"：不加这一支那种材料在界面上
    // **一个标记都没有**，读起来像"全都健康"。颜色用红：这不是材料的问题，是我们的问题。
    case 'health_error':
      return (
        <p role="alert" style={{ margin: '4px 0 0', fontSize: 12, color: RED }}>
          ⚠ <strong>锚点健康度算不出来</strong>：{why}
          <br />这是<strong>工具缺陷</strong>，<strong>不代表</strong>材料有问题——但它的引用位置
          目前<strong>未知</strong>。
        </p>
      )
    default:
      return assertNever(props.status)
  }
}

/**
 * **「这个状态要不要禁用『复算锚点』按钮」**——把这一处也纳入**穷尽性**保护
 * （2026-09-18 复核 b12 的 LOW-4b）。
 *
 * 为什么不留在调用点直接写"状态名相等比较"：`assertNever` 只保证 `AnchorMark`
 * 那个 `switch` 穷尽，面板里**另有一处**直接比较（`disabled={…}` 里的相等判断）——
 * 将来后端**新增一个状态**且它**也该**禁用按钮时，那一处**一声不响**（今天不是 bug：
 * 按设计只有 `no_locators` 禁用，因为只有它"没有任何区间可复算"）。这类"新增取值只在某几处
 * 生效"正是本文件一直在防的静默。
 * ⚠ 本注释**故意不写出那个比较表达式**（连注释里的字面量也算数）：离线冒烟有一条
 * `smoke-client-entry` 断言"面板源码里不许再出现 `no_locators` 的相等比较"——写进来会自己撞自己。
 *
 * 判据：**没有区间可复算** ⇒ 禁用（点它没有意义）；其余状态都能点（`stale` 正是要点它的时候，
 * `unknown`/`health_error` 点一次可能就变清楚，`ok` 重算一遍无害）。
 * 行为由 `scripts/smoke-anchor-mark.mjs` **逐档真渲染/真调用**验过；穷尽性由 `tsc` 保证
 * （往 union 加成员 ⇒ 这里 `default` 分支不再是 `never` ⇒ `npm run typecheck` 红）。
 */
export function statusDisablesReverify(status?: KsLocatorHealth['status']): boolean {
  switch (status) {
    case undefined:
    case 'ok':
    case 'stale':
    case 'unknown':
    case 'health_error':
      return false
    case 'no_locators':
      return true
    default:
      return assertNever(status)
  }
}

/**
 * 草稿能不能填进结论框（§10.97 的**唯一判据**；导出给冒烟做行为级验证）。
 *
 * 三条各自都必要：
 *   · `draft === null`：还没起草过 ⇒ 没得填；
 *   · `llm_called === false`：引擎因为"没有可承重材料"**一次模型都没调** ⇒ 那是"没起草"，
 *     不是"起草出了一段空话"；
 *   · `draft_md` 为空/纯空白：模型没产出结论段（引擎会另给 `derivation_md` 与警告）⇒
 *     **不许**把空串填进去（那会让用户以为"点过了就有结论"）。
 */
export function canApplyDraft(draft: KsResearchDraft | null): boolean {
  if (draft === null || draft.llm_called === false) return false
  return (draft.draft_md ?? '').trim() !== ''
}

/**
 * 结论框与草稿的**状态机**（§10.99，修复核 b26 的 F1）。
 *
 * ## 为什么把它做成纯函数 + 封闭动作集（而不是让面板里随手写状态）
 * §10.97 的"绝不自动填"判据是**字符串级的**（切片里找 setter 名 + 数它出现几次）。
 * 复核 b26 **构造出了绕过**：把 setter 赋给一个**声明在切片之外**的别名，再在起草响应里
 * 调用它 ⇒ 整条冒烟 **19/19 全绿**，而"自动填"**真的发生了**。⇒ 判据钉住的是**写法**，
 * 不是**性质**。
 *
 * 现在的三层：
 *   1. **语义层**（可被真的调用并断言）：`draftArrived` **不可能**改 `conclusionMd`
 *      （函数体里就没这个赋值）；`requestApplyDraft` 在结论框非空时**只进待确认、不写**
 *      （修复核 b26 的 F3：原先一键**静默覆盖**用户手写的字且不可撤销）；
 *      `confirmApplyDraft` 才是**唯一**写入路径。
 *   2. **类型层**：面板只能 `dispatch(动作)`，动作集是**封闭**的（`DraftAction`）⇒
 *      "写一个对象字面量"那条绕过**编译不过**（b26 的别名绕过就是这么被堵死的）。
 *   3. **窄写法判据**（冒烟）：到达路径**只许**出现 `arrived` 动作。
 *
 * ⚠ **残余风险（如实写）**：没人能自动证明"用户真的点过那一下"——别名 + 伪造 `confirmApply`
 *   动作仍可绕过前两层（冒烟只到"动作名"这一层）。要真防住那一条，需要 jsdom（**本仓未装**，
 *   属需决策项）或真机 E2E。已登记。
 */
export interface DraftFlow {
  /** 最近一次起草的返回（`null` = 还没起草过）。 */
  draft: KsResearchDraft | null
  /** 结论框里的字（**用户手写**，或他**点了确认**之后的结果）。 */
  conclusionMd: string
  /** 结论框非空时点「填进结论框」⇒ 进入这个状态等用户确认（**不是**已经写了）。 */
  pendingOverwrite: boolean
}

export const emptyDraftFlow: DraftFlow = { draft: null, conclusionMd: '', pendingOverwrite: false }

/** 起草响应到达：**只记草稿**，结论框与待确认状态原样（这一条就是"绝不自动填"）。 */
export function draftArrived(prev: DraftFlow, out: KsResearchDraft): DraftFlow {
  return { draft: out, conclusionMd: prev.conclusionMd, pendingOverwrite: false }
}

/** 点「用这段填进结论框」：空框 ⇒ 直接填；**非空 ⇒ 只进入待确认、不覆盖**。 */
export function requestApplyDraft(prev: DraftFlow): DraftFlow {
  if (!canApplyDraft(prev.draft)) return prev
  if (prev.conclusionMd.trim() !== '') {
    return { draft: prev.draft, conclusionMd: prev.conclusionMd, pendingOverwrite: true }
  }
  return { draft: prev.draft, conclusionMd: prev.draft?.draft_md ?? '', pendingOverwrite: false }
}

/** 用户在"要覆盖吗"里点了确认：**这才是唯一的写入路径**。 */
export function confirmApplyDraft(prev: DraftFlow): DraftFlow {
  if (!canApplyDraft(prev.draft)) return prev
  return { draft: prev.draft, conclusionMd: prev.draft?.draft_md ?? '', pendingOverwrite: false }
}

/** 用户放弃覆盖：什么都不变（只是退出待确认）。 */
export function cancelApplyDraft(prev: DraftFlow): DraftFlow {
  return { draft: prev.draft, conclusionMd: prev.conclusionMd, pendingOverwrite: false }
}

/** 用户在结论框里自己打字（**用户输入**这一条路，与草稿无关）。 */
export function userTypedConclusion(prev: DraftFlow, text: string): DraftFlow {
  return { draft: prev.draft, conclusionMd: text, pendingOverwrite: false }
}

/** 封闭动作集（面板**唯一**能改变上述状态的方式；见本节 docstring 的三层说明）。 */
export type DraftAction =
  | { type: 'arrived'; out: KsResearchDraft }
  | { type: 'requestApply' }
  | { type: 'confirmApply' }
  | { type: 'cancelApply' }
  | { type: 'typed'; text: string }

/** 动作 → 状态转移（把四个纯函数与"用户打字"收进一个封闭集）。 */
export function draftReducer(prev: DraftFlow, action: DraftAction): DraftFlow {
  switch (action.type) {
    case 'arrived':
      return draftArrived(prev, action.out)
    case 'requestApply':
      return requestApplyDraft(prev)
    case 'confirmApply':
      return confirmApplyDraft(prev)
    case 'cancelApply':
      return cancelApplyDraft(prev)
    case 'typed':
      return userTypedConclusion(prev, action.text)
    default:
      return assertNever(action)
  }
}

/**
 * **锚点总览的后端说明**（`locator.py` 的 `note`）——一个**能单独渲染**的组件。
 *
 * 为什么要抽出来（2026-09-18，复核 b12 的 LOW-1 + 一次变异 AA5）：
 * 这段状态**曾经是死的**（b11 的 INFO-1：shell 两处写、零处读 ⇒ 后端的解释从没上过屏）。
 * 修好之后判据只是"源码里有没有 `anchorNote` 这串字"——于是把条件改成
 * `{false && (<p>{anchorNote}</p>)}`（永不上屏）时，源码里**照样"读"到了它** ⇒ 字符串级
 * 断言**看不见**。抽成组件后，这条断言变成**真渲染**：
 * `smoke-anchor-mark.mjs` 分别渲染 `note=''`（必须什么都不出）与 `note='后端原文'`
 * （必须**原样**出现那段字）——行为级，且不需要 jsdom。
 *
 * 语义与抽出来之前**逐字一致**：空串不渲染（避免占位空行），非空原样显示。
 */
export function AnchorNoteLine(props: { note?: string }): React.ReactElement | null {
  const note = props.note || ''
  if (note === '') return null
  return <p style={{ margin: '0 0 8px', fontSize: 12, color: GRAY }}>{note}</p>
}

export function KsMaterialsPanel(props: KsMaterialsPanelProps): React.ReactElement {
  const { visible, onUseProject } = props
  const [projects, setProjects] = useState<KsMaterialProject[]>([])
  const [projectId, setProjectId] = useState<string>('')
  const [materials, setMaterials] = useState<KsMaterial[]>([])
  const [tiers, setTiers] = useState<KsMaterialTierDef[]>([])
  /**
   * 层级清单（T0–T4）**没读到**。
   *
   * ⚠ 这条是 2026-09-18 的**真机 e2e** 抓出来的（`scripts/e2e-materials-panel.mjs`，
   * 当时的真机主机还没挂载 `/ks/materials*`）：层级清单的失败原先被
   * `.catch(() => [])` **静默吞掉**，于是下拉框只剩"当前值"这一个选项——
   * 用户看到的是"这份材料只有一个层级可选"，而**真相是"这份清单没取到"**。
   * 请求失败被渲染成"功能就是这样"，正是 P1 准确性最不能接受的形状
   * （同一族的缺陷本战役已栽过一次：`legal_status` 的 NULL 洗白）。
   *
   * 纪律：**失败可以不阻塞**（清单失败不该挡住材料表），但**不能不说话**。
   */
  const [tierListFailed, setTierListFailed] = useState(false)
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
  // ---- 产出（Phase D-3b）：研究问题 + 结论（可选）+ 上一次的产出物 ----
  const [researchQuery, setResearchQuery] = useState('')
  /** 结论框 + 草稿的**同一个状态机**（`DraftFlow`）：这是"绝不自动填"从
   *  **字符串约定**升级为**函数语义 + 封闭动作集**的地方（§10.99，修复核 b26 的 F1）。 */
  const [flow, dispatch] = useReducer(draftReducer, emptyDraftFlow)
  const conclusionMd = flow.conclusionMd
  const draft = flow.draft
  const [report, setReport] = useState<KsResearchReport | null>(null)
  const [showReport, setShowReport] = useState(false)
  /**
   * 引用锚点健康度（**便宜**判据：只比指纹）。
   * ⚠ 只在**项目列表加载后**拉一次（`fetchProjectLocators`），材料行上按 id 显示缓存值
   * ——每行单独发请求会在有几十份材料时把面板变成请求风暴。
   */
  const [anchors, setAnchors] = useState<Record<string, KsLocatorHealth>>({})
  const [anchorNote, setAnchorNote] = useState('')
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
      // 两条请求**各自结算**。第一版把清单失败记在一个局部变量里、等
      // `Promise.all` 的 `await` 回来再落地——真机 e2e 当场证伪：项目列表
      // 也失败时 `Promise.all` 先 reject，函数直接跳进 catch，
      // 「清单没读到」**永远说不出口**（静默降级只是从一层挪到了另一层）。
      // 所以清单这条必须自己 then/catch、自己落地，与另一条的成败无关。
      void fetchMaterialTiers(ctl.signal)
        .then((defs) => { if (alive) { setTiers(defs); setTierListFailed(false) } })
        .catch(() => { if (alive) { setTiers([]); setTierListFailed(true) } })
      try {
        const list = await reloadProjects(ctl.signal)
        if (!alive) return
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
      setAnchors({})
      setAnchorNote('')
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
          // 锚点健康度：**一次请求拿全项目**（便宜判据，不重解析）
          fetchProjectLocators(projectId, ctl.signal).then((s) => {
            if (!alive) return
            // ⚠ `why` **必须来自后端**（`attention` 里就带着）：界面这一层不许自己解释
            // status。2026-09-18 之前这里写死 `why: ''`，于是界面只能说一句笼统的
            // "解析器身份变了"——而 `stale` 现在有**两个**成因（解析器变了 / **源文件字节变了**，
            // 后者是**确定**失效而非"可能"）。把后端的理由带出来，界面就不再替后端下结论。
            const why: Record<string, string> = {}
            for (const a of s.attention) why[a.material_id] = a.why
            const map: Record<string, KsLocatorHealth> = {}
            for (const [mid, status] of Object.entries(s.statuses)) {
              map[mid] = { material_id: mid, status, why: why[mid] ?? '' } as KsLocatorHealth
            }
            setAnchors(map)
            setAnchorNote(s.note)
          }).catch(() => { /* 锚点总览失败不该挡住材料列表 */ }),
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

  /**
   * 生成**研究报告**（Markdown + HTML 两种形态，本机落盘）。
   *
   * 三条与引擎同源的纪律，界面这一层也要守住：
   * 1. **引用警告必须显示**（`warnings`）：`[[m:i]]` 对不上、或落在"仅线索/不可用"上，
   *    引擎会把它列出来而**不是静默改掉**——不显示就等于用户以为引用都成立。
   * 2. **计数必须显示**（approved/pending/rejected）：报告里"待评审"是单列一节、
   *    **不进任何结论**，界面要让用户看见这个分离。
   * 3. **落盘路径必须显示**：产物在**本机**、不外发；用户得知道文件在哪。
   *
   * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原 `onExportSlides`（生成 PPT，
   * 走 `exportResearchSlides`）已随 PPT 交付物一并拆除——业主否决 Word/PPT 交付物
   * （`docs/NOT-DOING.md` 第 1 条）。
   */
  const onExportReport = useCallback(() => {
    if (projectId === '') return
    void run('report', async () => {
      const out = await exportResearchReport(projectId, {
        query: researchQuery.trim() === '' ? undefined : researchQuery.trim(),
        conclusionMd: conclusionMd.trim() === '' ? undefined : conclusionMd,
      })
      setReport(out)
      setShowReport(false)
      const bad = (out.warnings ?? []).length
      return `研究报告已生成（已批准 ${out.counts?.approved ?? 0} / 待评审 ${out.counts?.pending ?? 0}）`
        + (bad > 0 ? `——⚠ 有 ${bad} 条引用警告，见下方（报告里**原样保留**了那些引用）` : '')
    }, null)
  }, [conclusionMd, projectId, researchQuery, run])

  /**
   * **起草一段结论（草稿）**（Phase D-5b，§10.97）。
   *
   * 四条界面纪律（与引擎同源，少一条都会让"草稿"被误当成"已批准的结论"）：
   * 1. **必须显眼标明「未批准草稿」**（`status === 'unapproved_draft'` 是引擎契约）；
   * 2. **绝不自动填进结论框**——只有用户点「用这段填进结论框」才写（那个点击**就是**
   *    "用户批准后采用"这个动作）；
   * 3. `llm_called === false`（没有可承重材料 ⇒ 引擎一次模型都没调）**不是失败**，
   *    要按"没起草"如实说；
   * 4. **警告必须显示**（引用不成立 / 引用了仅线索的材料 / 模型没产出结论段）。
   */
  const onDraftConclusion = useCallback(() => {
    if (projectId === '') return
    const q = researchQuery.trim()
    if (q === '') {
      setNotice('起草结论要先填「研究问题」——草稿必须知道要回答什么。')
      return
    }
    void run('draft', async () => {
      const out = await exportResearchDraft(projectId, { query: q })
      dispatch({ type: 'arrived', out })
      if (out.llm_called === false) {
        return '没有可承重的已批准材料——引擎**没有起草**（一次模型都没调）'
      }
      const n = (out.warnings ?? []).length
      return '草稿已生成（**未经批准**，不得作为依据）'
        + (n > 0 ? `——⚠ ${n} 条提示，见下方` : '')
    }, null)
  }, [projectId, researchQuery, run])

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

  /** 勾选态（S3-a v3：多选批量设置地位）。 */
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const onRole = useCallback((m: KsMaterial, role: string) => {
    void run(`role:${m.material_id}`, async () => {
      await setMaterialRole(m.material_id, role === '' ? null : (role as 'criterion' | 'reference'))
      return `「${m.title}」任务内效力已更新`
    }, projectId)
  }, [projectId, run])

  /**
   * **重解析比对**（贵、显式动作，§10.49）：用当前解析器复算派生全文并比对。
   *
   * 三条结果**措辞不许混**（所有者是引擎的 `materials/locator.py`）：
   * `match` = 逐字节一致（这才是保证）；`mismatch` = **已存区间失效**（引用会指错）；
   * `unavailable` = **验不了**（网页件没有留存源文件）——**不是**"没问题"。
   */
  const onReverify = useCallback((m: KsMaterial) => {
    void run(`reverify:${m.material_id}`, async () => {
      const out = await reverifyMaterialLocators(m.material_id)
      if (out.status === 'match') return `「${m.title}」锚点复算：**逐字节一致**（区间仍有效）`
      if (out.status === 'mismatch') {
        return `「${m.title}」锚点复算：⚠ **已存区间已失效**（引用位置会指错）——`
          + '需要重建这份材料（重新解析并重建切片），或把它弃用'
      }
      return `「${m.title}」锚点复算：**验不了**（${out.why}）`
    }, null)
  }, [run])

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
    // ⚠ 5j（2026-09-20）：`.ks-page` 只做 container-type（页面留边的宽/窄两档靠它切；
    //    CSS 里容器不能用自己的宽度查自己 ⇒ 留边落在后代的 `.ks-mat` 上）。
    //    零内边距零外边距 ⇒ 不是"盒子套盒子"。里面的 JSX 缩进保持原样（本批不重排）。
    //    ⚠ 本组件**同时**被设置窗的 KsCategory 包着渲染 ⇒ 那处会多出这层留边（16px）：
    //      这是有意的（弹窗内容同样不该贴边），但它**不在**本轮的验收面上（见 UI-BASELINE 5j 边界）。
    <div className="ks-page">
    <div className="ks-mat" style={{ fontSize: 13 }}>
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
        <div style={{ marginBottom: 12, padding: '8px 10px', border: '1px solid var(--dsw-alias-border-l2)', borderRadius: 6 }}>
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
            borderTop: '1px dashed var(--dsw-alias-border-l2)',
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
        <p role="status" style={{ margin: '0 0 8px', color: 'var(--dsw-alias-state-warn-primary)', fontSize: 12 }}>
          ⚠ {warn}
        </p>
      )}
      {notice !== '' && (
        <p style={{ margin: '0 0 8px', color: 'var(--dsw-alias-label-secondary, #666)', fontSize: 12 }}>
          {notice}
        </p>
      )}
      {loading && <p style={{ margin: '0 0 8px', fontSize: 12, color: GRAY }}>加载中…</p>}

      {/* 锚点总览的**后端说明**（`locator.py` 的 `note`）：它解释 `unknown` 里包含哪几类、
          `health_error` 不是健康状态。⚠ 这段状态**曾经是死的**（shell 2 处写、0 处读 ⇒
          b11 的 INFO-1）：后端的解释从来没上过屏，而它正是"别把不知道当成没问题"那件事的说明。
          ⇒ 现在渲染出来（只在选了项目、拿到总览之后显示）。 */}
      <AnchorNoteLine note={anchorNote} />

      {/* 层级清单没读到（真机 e2e 抓出来的静默失败，见 `tierListFailed` 的注释）。
          **不加"选了项目才显示"的门**：失败是真实发生的事，闸门只会让它可被隐藏——
          而且真机 e2e 里"项目列表本身也没读到"（没有任何项目可选）正是要能断言它的场景。
          代价是没选项目时它描述的下拉还没上屏；宁可多说一句，也不静默降级。 */}
      {tierListFailed && (
        <p role="status" style={{ margin: '0 0 8px', color: 'var(--dsw-alias-state-warn-primary)', fontSize: 12 }}>
          ⚠ 来源层级清单（T0–T4）**没读到**：材料表里每份材料的「轴 A 来源可信度」下拉会只剩当前值、
          <strong>改不了级</strong>。这**不代表**材料没有层级，是这份清单没取到——
          重开面板或重启引擎后再试。
        </p>
      )}

      {/* ---------------------------------------------------- 材料表 */}
      {projectId === '' && (
        <p style={{ fontSize: 12, color: GRAY }}>先选一个项目（或在上面新建）。</p>
      )}
      {projectId !== '' && !loading && materials.length === 0 && (
        <p style={{ fontSize: 12, color: GRAY }}>
          这个项目里还没有已登记的材料：把文件放进参考资料文件夹后点「扫描收件」（人工上传免评审，就位即可用），
          或用上面的「自采一条」按网址抓一份网页正文（自采的要你批准后才算数）。
        </p>
      )}

      {/* S3-a 批量条（勾中浮现；与知识库页批量条同手感）。逐项真调 role 口（引擎无批量口）。 */}
      {picked.size > 0 && (
        <div className="ks-batch" data-ks-batch="on" style={{ position: 'sticky', bottom: 0, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', padding: '8px 10px', marginBottom: 8, border: '0.5px solid var(--dsw-alias-border-l1)', borderRadius: 6, background: 'var(--dsw-alias-bg-layer-2)' }}>
          <span style={{ fontSize: 12 }}>已选 {String(picked.size)} 项</span>
          <button type="button" style={btnStyle(busy !== '')} disabled={busy !== ''} onClick={() => { materials.filter((mm) => picked.has(mm.material_id)).forEach((mm) => onRole(mm, 'criterion')); setPicked(new Set()) }}>
            批量设为必须遵守
          </button>
          <button type="button" style={btnStyle(busy !== '')} disabled={busy !== ''} onClick={() => { materials.filter((mm) => picked.has(mm.material_id)).forEach((mm) => onRole(mm, 'reference')); setPicked(new Set()) }}>
            批量设为仅供参考
          </button>
          <button type="button" style={btnStyle(false)} onClick={() => { setPicked(new Set()) }}>
            取消选择
          </button>
        </div>
      )}
      {materials.map((m) => {
        const rev = reviewLabel(m.review_status)
        /* S3-b（业主裁定 NOT-DOING #15）：人工上传（origin=user）**免评审** —— 生而可作依据，
           没有批准步骤；自采/网页来源（origin=collected）照旧逐个批（硬门只管自采）。 */
        const isUpload = (m.origin ?? 'user') === 'user'
        const chunks = openChunks[m.material_id]
        return (
          <div
            key={m.material_id}
            style={{
              border: '1px solid var(--dsw-alias-border-l2)',
              borderRadius: 6, padding: '8px 10px', marginBottom: 8,
            }}
          >
            <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
              <input
                type="checkbox"
                aria-label={`勾选 ${m.title}`}
                checked={picked.has(m.material_id)}
                onChange={() => {
                  const next = new Set(picked)
                  if (next.has(m.material_id)) next.delete(m.material_id)
                  else next.add(m.material_id)
                  setPicked(next)
                }}
              />
              <strong>{m.title}</strong>
              <span style={{ fontSize: 12, color: rev.color }}>{rev.text}</span>
              <span style={{ fontSize: 12, color: GRAY }}>
                {m.chunk_count ?? 0} 个切片 · {m.origin ?? 'user'} / {m.kind ?? 'other'}
              </span>
            </div>

            {/* 两个轴**分开**摆：合成一个"可信度"就必然错一个（公司制度例） */}
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginTop: 6 }}>
              <label style={{ display: 'flex', gap: 4, alignItems: 'center', fontSize: 12 }}>
                <span>来源层级</span>
                <select
                  aria-label={`来源层级 ${m.title}`}
                  value={m.source_tier ?? ''}
                  onChange={(e) => onTier(m, e.currentTarget.value)}
                  // 清单没取到时**只有当前值一个选项**：留着可点会让"改不了级"看起来像
                  // "点了没反应"的 bug，而不是"清单没读到"。禁用并给出原因（见上面的琥珀提示）。
                  disabled={busy !== '' || tiers.length === 0}
                  title={tiers.length === 0 ? '来源层级清单没读到，暂时改不了级' : undefined}
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
              {/* S3-a v3：地位**行上直选**（业主："不弄第二屏，直接在行后加按钮"）——
                  胶囊点一下在「必须遵守」/「仅供参考」间切换（未声明首次点 → 必须遵守，
                  与"人工上传默认必须遵守"同一口径）。词换、语义不换（criterion/reference）。 */}
              <button
                type="button"
                aria-label={`地位 ${m.title}`}
                disabled={busy !== ''}
                onClick={() => { onRole(m, m.task_role === 'criterion' ? 'reference' : 'criterion') }}
                title={m.task_role === 'criterion' ? '必须遵守（以此为准）——点一下改为仅供参考' : '仅供参考——点一下改为必须遵守'}
                style={{
                  ...btnStyle(busy !== ''),
                  borderRadius: 999,
                  color: m.task_role === 'criterion' ? 'var(--dsw-alias-state-business-primary)' : 'var(--dsw-alias-label-secondary)',
                  border: `1px solid ${m.task_role === 'criterion' ? 'var(--dsw-alias-state-business-primary)' : 'var(--dsw-alias-label-tertiary)'}`,
                }}
              >
                {m.task_role === 'criterion' ? '必须遵守' : m.task_role === 'reference' ? '仅供参考' : '未声明'}
              </button>
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
            {/* 引用锚点标记：**唯一出口**是 `AnchorMark`（见文件下半部分）。
                为什么不在这里直接写 if：`AnchorMark` 用 `switch` + `assertNever` ⇒
                新增一个 `status` 却忘了加分支，会在 `npm run typecheck` **直接报错**，
                而不是在界面上**静默少一个标记**（复核 b11 的 LOW-4：加一个没人渲染的成员时
                `tsc` 仍 GREEN）。语义严格分开：需复算 ≠ 已坏；未验证 ≠ 有问题。 */}
            <AnchorMark status={anchors[m.material_id]?.status} why={anchors[m.material_id]?.why} />

            <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
              {/* S3-b：人工上传免评审 ⇒ 不给批准/拒绝钮（没有步骤就没有按钮，不装样子）。 */}
              {!isUpload && (
                <>
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
                </>
              )}
              {isUpload && (
                <span style={{ fontSize: 12, color: GRAY }}>人工上传：免评审，已就位即可用</span>
              )}
              <button type="button" style={btnStyle(false)} onClick={() => onToggleChunks(m)}>
                {chunks === undefined ? '读正文（评审前必看）' : '收起正文'}
              </button>
              <button
                type="button"
                style={btnStyle(busy !== '' || statusDisablesReverify(anchors[m.material_id]?.status))}
                disabled={busy !== '' || statusDisablesReverify(anchors[m.material_id]?.status)}
                title="用当前解析器重新解析源文件并比对派生全文（PDF 是子进程，可能要几十秒）"
                onClick={() => onReverify(m)}
              >
                复算锚点
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

      {/* ---------------------------------------------------- 产出（Phase D-3b）
          只吃**已批准**材料（硬门在引擎的检索里）；未批准的自会出现在报告的
          "尚未批准的材料（不会进入任何结论）"一节。 */}
      {projectId !== '' && (
        <div style={{
          marginTop: 12, padding: '8px 10px',
          border: '1px solid var(--dsw-alias-border-l2)', borderRadius: 6,
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <strong>产出</strong>
            <span style={{ fontSize: 12, color: GRAY }}>
              （只吃<strong>已批准</strong>材料；未批准的在报告里单列一节）
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
            <input
              aria-label="研究问题"
              placeholder="研究问题（可选；给了就按它检索已批准材料并分组）"
              value={researchQuery}
              onChange={(e) => setResearchQuery(e.currentTarget.value)}
              style={{ padding: '3px 6px', fontSize: 12, width: 340 }}
            />
          </div>
          <div style={{ marginTop: 6 }}>
            <textarea
              aria-label="结论正文"
              placeholder="结论（可选，Markdown）。里面可以用 [[m:编号]] 引用依据；编号对不上引擎会警告。"
              value={conclusionMd}
              onChange={(e) => dispatch({ type: 'typed', text: e.currentTarget.value })}
              rows={3}
              style={{ padding: '3px 6px', fontSize: 12, width: '100%', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <button
              type="button"
              style={btnStyle(busy !== '')}
              disabled={busy !== ''}
              onClick={onDraftConclusion}
            >
              起草结论（草稿）
            </button>
            <button
              type="button"
              style={btnStyle(busy !== '')}
              disabled={busy !== ''}
              onClick={onExportReport}
            >
              生成研究报告（Markdown/HTML）
            </button>
            {report?.markdown !== undefined && (
              <button
                type="button"
                style={btnStyle(false)}
                onClick={() => setShowReport((v) => !v)}
              >
                {showReport ? '收起 Markdown' : '看 Markdown'}
              </button>
            )}
          </div>
          {/* ---- 结论草稿（§10.97）：**只读**展示 + 「用这段填进结论框」这个显式动作 ----
              三条纪律都在这一块里可见：① 标"未批准草稿"；② 不自动填；③ 警告照显。 */}
          {draft !== null && (
            <div
              role="status"
              style={{
                marginTop: 6, padding: '6px 8px', borderRadius: 4,
                border: '1px dashed var(--dsw-alias-state-warn-primary)',
                background: 'var(--dsw-alias-bg-layer-2)',
              }}
            >
              <p style={{ margin: 0, fontSize: 12, color: 'var(--dsw-alias-state-warn-primary)' }}>
                ⚠ <strong>未批准草稿</strong>
                ——由系统基于<strong>已批准材料</strong>起草，<strong>不得作为依据</strong>；
                请先改/核，再点「用这段填进结论框」。
              </p>
              {draft.llm_called === false ? (
                <p style={{ margin: '4px 0 0', fontSize: 12, color: GRAY }}>
                  没有可承重的已批准材料，引擎<strong>没有起草</strong>（一次模型都没调）。
                </p>
              ) : (
                <>
                  <pre style={{
                    marginTop: 4, maxHeight: 200, overflow: 'auto', fontSize: 11,
                    whiteSpace: 'pre-wrap', background: 'var(--dsw-alias-bg-base)',
                    padding: 6, borderRadius: 4,
                  }}>{canApplyDraft(draft)
                      ? draft.draft_md
                      : '（模型没有产出结论段——见下方提示，可看 derivation_md）'}</pre>
                  {(draft.warnings ?? []).length > 0 && (
                    <p style={{ margin: '4px 0 0', fontSize: 12,
                      color: 'var(--dsw-alias-state-warn-primary)' }}>
                      ⚠ 起草提示（引用不成立 / 材料不足 / 模型输出问题，**原样列出、不静默改草稿**）：
                      <br />{(draft.warnings ?? []).join('；')}
                    </p>
                  )}
                  {/* ⚠ 结论框**非空**时不许一键静默覆盖（复核 b26 的 F3）：
                      先进入待确认，由用户点「确认覆盖」——**不可撤销的覆盖要两下**。 */}
                  {flow.pendingOverwrite ? (
                    <div style={{ marginTop: 4 }}>
                      <p style={{ margin: '0 0 4px', fontSize: 12,
                        color: 'var(--dsw-alias-state-warn-primary)' }}>
                        ⚠ 结论框里已有内容（可能是你自己写的）——填草稿会**覆盖**它，且**不能撤销**。
                        确认要覆盖吗？
                      </p>
                      <button
                        type="button"
                        style={{ ...btnStyle(false), marginRight: 6 }}
                        onClick={() => dispatch({ type: 'confirmApply' })}
                      >
                        确认覆盖
                      </button>
                      <button
                        type="button"
                        style={btnStyle(false)}
                        onClick={() => dispatch({ type: 'cancelApply' })}
                      >
                        取消（保留我写的）
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      style={{ ...btnStyle(!canApplyDraft(draft)), marginTop: 4 }}
                      disabled={!canApplyDraft(draft)}
                      onClick={() => dispatch({ type: 'requestApply' })}
                    >
                      {flow.conclusionMd.trim() === ''
                        ? '用这段填进结论框'
                        : '用这段填进结论框（将覆盖现有内容）'}
                    </button>
                  )}
                </>
              )}
            </div>
          )}
          {report !== null && (
            <p style={{ margin: '6px 0 0', fontSize: 12, color: GRAY }}>
              已批准 {report.counts?.approved ?? 0} / 待评审 {report.counts?.pending ?? 0} /
              已拒绝 {report.counts?.rejected ?? 0}；
              引用核验：材料引用 {report.citations?.checked_material_refs ?? 0} 条
              {report.citations?.unchecked_law_refs
                ? ` · 法规引用 ${report.citations.unchecked_law_refs} 条**本次无法核验**` : ''}
              {(report.citations?.unknown ?? 0) > 0
                ? ` · ${report.citations?.unknown} 条**无法判定**` : ''}
              {report.names !== undefined && report.names.length > 0 && (
                <Deliverables names={report.names} paths={report.files ?? []} />
              )}
            </p>
          )}
          {report !== null && (report.warnings ?? []).length > 0 && (
            <p role="status" style={{ margin: '6px 0 0', color: 'var(--dsw-alias-state-warn-primary)', fontSize: 12 }}>
              ⚠ 引用警告（这些引用**不成立**或无法核验，报告里也照原样列出了）：
              <br />
              {(report.warnings ?? []).join('；')}
            </p>
          )}
          {showReport && report?.markdown !== undefined && (
            <pre style={{
              marginTop: 6, maxHeight: 320, overflow: 'auto', fontSize: 11,
              whiteSpace: 'pre-wrap', background: 'var(--dsw-alias-bg-layer-2)',
              padding: 8, borderRadius: 4,
            }}>
              {report.markdown}
            </pre>
          )}
          <p style={{ margin: '6px 0 0', fontSize: 12, color: GRAY }}>
            报告只有<strong>一种内容</strong>、两种落盘形态（Markdown 是交付物本体，
            HTML 是同一份内容的界面预览形态），
            <strong>本机</strong>生成与保存、<strong>不外发</strong>。
          </p>
        </div>
      )}
    </div>
    </div>
  )
}

// ---------------------------------------------------------------- 交付物按钮组

/**
 * 一份产物的"能不能直接看"由**扩展名**决定（浏览器能力，不是我们的偏好）：
 * · `.html` / `.md` → 新标签里**直接渲染**（HTML 是同一份内容的界面预览形态）；
 * · 其余（如 `.xlsx`）→ 浏览器渲染不了 ⇒ 只能下载一份（或用户按下面给的目录自己打开）。
 *
 * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：`.docx`/`.pptx` 不再作为交付物产出
 * （业主否决 Word/PPT 交付物，`docs/NOT-DOING.md` 第 1 条）；本函数判据是**通用**的
 * （按扩展名分 page/binary），留着兜住 xlsx 那类产物，不必为撤销而改写。
 */
export function deliverableKind(name: string): 'page' | 'binary' {
  return /\.(html?|md|txt)$/i.test(name) ? 'page' : 'binary'
}

/** 路径 → 所在目录（`files` 是绝对路径，取第一份的目录即可）。 */
export function folderOf(path: string): string {
  return path.replace(/[\\/][^\\/]*$/, '')
}

/** blob URL → 触发一次"另存为"（浏览器渲染不了非网页形态的产物，只能给一份文件）。 */
function downloadBlob(url: string, name: string): void {
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
}

/**
 * **交付物按钮组**（2026-09-18 用户报障："设置里的导入只接受 PDF，还有 html 呢"）。
 *
 * 报障的真实缺口不是"导入"，而是**产物没法看**：面板当时只把三个绝对路径打成
 * `<code>`，用户拿不到手。这里给每条产物一个能点的按钮，并**如实说出**做不到的部分：
 * · `.html`/`.md` 用新标签渲染（`URL.createObjectURL` 的 blob，不落盘、不外发）；
 * · 非网页形态的产物（如 `.xlsx`）只能"下载一份"——**本机那份原件仍在下面显示的目录里**，
 *   "一键用系统默认程序打开"需要新增宿主路由（要重启宿主），本轮不做，所以不写这种按钮。
 *
 * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：`.docx`/`.pptx` 交付物已拆除，文案随之改准
 * （原来点名 Word/PPT，现在交付物里没有这两类了）。
 *
 * ⚠ 两个实现纪律：
 * 1. blob URL 用完要 `revokeObjectURL`，但**不能立刻 revoke**——新标签还要读它
 *    （立刻撤会白屏），故给一个延时。
 * 2. 失败**必须显示**（例如产物被清理 ⇒ 引擎 404）：否则按钮点了没反应，
 *    用户会以为是界面卡了。
 */
function Deliverables(props: { names: string[]; paths: string[] }): JSX.Element {
  const { names, paths } = props
  const [busy, setBusy] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [copied, setCopied] = useState<boolean>(false)

  const folder = paths.length > 0 ? folderOf(paths[0]) : ''

  const open = useCallback((name: string): void => {
    if (busy !== '') return
    setBusy(name)
    setError('')
    const isPage = deliverableKind(name) === 'page'
    /**
     * ⚠ **必须在用户手势的同步段里先开窗**（2026-09-18 真机实测的坑）：
     * 原先写成 `await fetchExportBlob(...)` 之后再 `window.open(blobUrl)`，
     * 实测**新标签不会出现**（`window.open` 返回 null = 被拦截）：本地取字节虽然通常
     * 只有几十毫秒，但引擎冷启动实测可以到 8 秒，瞬时激活早过期了。
     * 现在的形状：同步占一个 about:blank，拿到字节后 `location.replace(blobUrl)`。
     * 万一仍然被拦截（`win === null`）⇒ **退化成下载并如实说明**，绝不静默无反应。
     */
    const win = isPage ? window.open('about:blank', '_blank') : null
    void (async () => {
      try {
        const blob = await fetchExportBlob(name)
        const url = URL.createObjectURL(blob)
        if (!isPage) {
          downloadBlob(url, name)
          window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
        } else if (win !== null) {
          // 新标签要读这个 blob URL ⇒ 延后撤销（立刻撤会白屏）。
          win.location.replace(url)
          window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
        } else {
          downloadBlob(url, name)
          window.setTimeout(() => URL.revokeObjectURL(url), 30_000)
          setError('浏览器拦截了新窗口（弹出窗口设置）。已改为下载一份——'
            + '文件就在下面的保存目录里，双击即可看。')
        }
      } catch (e) {
        if (win !== null) win.close()
        setError(`${name}：${e instanceof Error ? e.message : String(e)}`)
      } finally {
        setBusy('')
      }
    })()
  }, [busy])

  const copyFolder = useCallback((): void => {
    if (folder === '') return
    void navigator.clipboard.writeText(folder).then(
      () => { setCopied(true); setError('') },
      (e: unknown) => setError(`复制失败，请手动选中下面的路径：${e instanceof Error ? e.message : String(e)}`),
    )
  }, [folder])

  return (
    <div style={{ margin: '6px 0 0', fontSize: 12 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
        <span style={{ color: GRAY }}>产物：</span>
        {names.map((n) => (
          <button
            key={n}
            type="button"
            disabled={busy !== ''}
            onClick={() => open(n)}
            title={deliverableKind(n) === 'page'
              ? `${n}：在新标签里直接打开（浏览器渲染）`
              : `${n}：浏览器渲染不了这种产物（如 xlsx），这里下载一份；本机原件在下面那个目录里`}
            style={{
              border: '1px solid var(--dsw-alias-border-l2, #ccc)',
              background: 'var(--dsw-alias-bg-layer-2, #fff)',
              color: 'var(--dsw-alias-label-primary, #111)',
              borderRadius: 4, padding: '2px 8px', fontSize: 11.5,
              cursor: busy !== '' ? 'default' : 'pointer',
            }}
          >
            {deliverableKind(n) === 'page' ? '👁 打开' : '⬇ 下载'} {n}
            {busy === n ? ' …' : ''}
          </button>
        ))}
      </div>
      {folder !== '' && (
        <div style={{ marginTop: 4, color: GRAY }}>
          保存目录：<code style={{ wordBreak: 'break-all' }}>{folder}</code>{' '}
          <button
            type="button"
            onClick={copyFolder}
            title="复制目录路径（粘到资源管理器/Win+R 即可打开本机原件）"
            style={{
              border: '1px solid var(--dsw-alias-border-l2, #ccc)',
              background: 'var(--dsw-alias-bg-layer-2, #fff)',
              color: 'var(--dsw-alias-label-primary, #111)',
              borderRadius: 4, padding: '1px 6px', fontSize: 11, cursor: 'pointer',
            }}
          >
            {copied ? '✓ 已复制' : '📋 复制目录'}
          </button>
        </div>
      )}
      {error !== '' && (
        <p role="alert" style={{ margin: '4px 0 0', color: RED, fontSize: 11.5 }}>
          打开失败：{error}
        </p>
      )}
      <p style={{ margin: '4px 0 0', color: GRAY, fontSize: 11 }}>
        非网页形态的产物（如 xlsx）浏览器渲染不了：上面给的是**下载一份**（本机原件仍在保存目录里）。
        「用系统默认程序一键打开」需要在宿主侧加路由（要重启宿主），本轮未做。
      </p>
    </div>
  )
}
