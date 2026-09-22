/**
 * ks-dsh-plugin — src/materials.js
 *
 * 材料平面的**只读**模型工具 `ks_materials`（Phase B 第二步的配套）。
 *
 * ## 为什么需要它（本模块存在的唯一理由）
 * 引擎侧已经能把"某个项目的已批准材料"喂进取证答案（`ks_answer` 的
 * `params.material_project_id`），但**模型无从得知项目 id** —— 插件原先只暴露
 * ks_ping / ks_resolve_clause / ks_answer / ks_effect_report，没有任何列项目的接口。
 * 于是"用我上传的财报做分析"这句话在模型那边是**接不上**的：它只能干等用户手抄一个
 * `prj_…`。本工具补的就是这一步：让模型能按名字发现项目、看清每份材料的评审状态。
 *
 * ## 为什么**不**暴露 批准/拒绝/扫描（这不是省事，是纪律）
 * 方案 §6 的评审闸门是**硬门**，且业主要求"**经用户评审确认参考资料可用后**再做分析"。
 * 把 `review` 开成模型工具，等于让模型自己给自己发许可 —— 闸门立刻形同虚设。
 * 故本工具**只读**：模型可以告诉用户"有 2 份还没批准"，但**不能**代他批准。
 * 收件（scan）同样是写操作，也留给人（或后续界面）。
 *
 * ## 与 `ks_answer` 的关系（写在描述里，免得模型误以为查了材料就等于用了材料）
 * 本工具只**看**；要让材料真的参与作答，必须把 `project_id` 作为
 * `ks_answer.params.material_project_id` 传下去。且只有 `review_status='approved'`
 * 的材料会进提示词。
 */

/** 材料条目的对外形状（只留模型判断需要的字段，别把整行塞进提示词）。 */
function trimMaterialRow(r) {
  if (!r || typeof r !== 'object') return null
  return {
    material_id: r.material_id ?? null,
    title: r.title ?? null,
    // 轴 A（来源可信度）与轴 B（任务内效力）**分开摆**——合成一个"可信度"必错
    source_tier: r.source_tier ?? null,
    tier_label: r.tier_label ?? null,
    tier_source: r.tier_source ?? null,
    task_role: r.task_role ?? null,
    review_status: r.review_status ?? null,
    chunk_count: typeof r.chunk_count === 'number' ? r.chunk_count : null,
    origin: r.origin ?? null,
    kind: r.kind ?? null,
    url: r.url ?? null,
    domain: r.domain ?? null,
    tier_reason: r.tier_reason ?? null,
  }
}

/* ------------------------------------------------------------------ *
 * 第 6 步 §1：`output.schema` 的形状（宿主注册期/取值期都吃它）
 *
 * 实测硬约束（`docs/research/STEP6-WORKORDER.md` §1【实测】表）：可空**只能**用
 * `oneOf:[{type:'<T>'},{type:'null'}]`（`type:[...]` 会被 register 期直接拒）；
 * `additionalProperties:false` 下**条件性出现的键也必须列进 `properties`**。
 * ------------------------------------------------------------------ */
const NULLABLE_STRING = { oneOf: [{ type: 'string' }, { type: 'null' }] }

/** `trimMaterialRow` 的对外形状（搜 `function trimMaterialRow`）——13 个键一个不缺。 */
const MATERIAL_ROW = {
  type: 'object',
  additionalProperties: false,
  properties: {
    material_id: NULLABLE_STRING,
    title: NULLABLE_STRING,
    source_tier: NULLABLE_STRING,
    tier_label: NULLABLE_STRING,
    tier_source: NULLABLE_STRING,
    task_role: NULLABLE_STRING,
    review_status: NULLABLE_STRING,
    chunk_count: { oneOf: [{ type: 'number' }, { type: 'null' }] },
    origin: NULLABLE_STRING,
    kind: NULLABLE_STRING,
    url: NULLABLE_STRING,
    domain: NULLABLE_STRING,
    tier_reason: NULLABLE_STRING,
  },
  required: ['material_id', 'title', 'source_tier', 'tier_label', 'tier_source',
    'task_role', 'review_status', 'chunk_count', 'origin', 'kind', 'url', 'domain', 'tier_reason'],
}

/**
 * Build the read-only `ks_materials` tool.
 *
 * @param {object} manager EngineManager（与其它工具同一个；`ensureLive` 取 port/token）。
 */
export function makeMaterialsTool(manager) {
  return {
    name: 'ks_materials',
    description:
      // 批3-c 瘦身（2026-09-22）：≤10 行；硬门语义全留（原文 var/tmp/desc-before-materials.txt）。
      '列出参考资料项目与材料——只读。用户说"用我上传的财报/公司制度分析…"时，先按名字找 '
      + 'project_id，再作为 ks_answer 的 params.material_project_id 传下去（材料只有那样才进作答）。'
      + 'action：projects（默认，列项目）/ materials（列材料：review_status 三态、来源层级 T0~T4、'
      + '任务效力 criterion=本任务准则/reference、切片数 + 三态计数）/ inbox（参考资料文件夹里'
      + '尚未登记的文件）。只读：不能批/拒——评审是用户的判断（硬门）；有 pending 材料就如实'
      + '告知"未批准、不进结论"。只有 approved 的材料会进 ks_answer 提示词。',
    parameters: {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          enum: ['projects', 'materials', 'inbox'],
          description: 'projects（默认）=列项目；materials=列某项目材料；inbox=列未登记文件。',
        },
        project_id: {
          type: 'string',
          description: '项目 id（prj_…）。action=materials/inbox 时必填。',
        },
        status: {
          type: 'string',
          enum: ['pending', 'approved', 'rejected'],
          description: 'action=materials 时按评审状态过滤（省略=全列，含未批准）。',
        },
      },
      required: [],
      additionalProperties: false,
    },
    output: {
      // 第 6 步 §1：**三个 action 返回三套字段** ⇒ 按施工单 §1 的推荐形态：schema 列
      // **全部可能键**、`required` 只留永远存在的 `ok`/`action`（不做 `oneOf` 三支——
      // 三支的键大半重合，读起来反而看不出哪里是权限边界）。
      // 逐字段抄 `execute` 的三处 `return {...}`（搜 `action,`／`review_counts`／`files:`）。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          action: { type: 'string', enum: ['projects', 'materials', 'inbox'] },
          count: { type: 'number' },
          projects: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              properties: {
                project_id: NULLABLE_STRING,
                name: NULLABLE_STRING,
                // 引擎把它存成 JSON（`json.loads`），POST 侧校验"必须是对象"⇒ object|null。
                authority_policy: { oneOf: [{ type: 'object' }, { type: 'null' }] },
              },
              required: ['project_id', 'name', 'authority_policy'],
            },
          },
          hint: { type: 'string' },
          project_id: { type: 'string' },
          dir: NULLABLE_STRING,
          files: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              properties: {
                file_name: NULLABLE_STRING,
                size: { oneOf: [{ type: 'number' }, { type: 'null' }] },
              },
              required: ['file_name', 'size'],
            },
          },
          filtered_by: NULLABLE_STRING,
          review_counts: {
            type: 'object',
            additionalProperties: false,
            properties: {
              approved: { type: 'number' },
              pending: { type: 'number' },
              rejected: { type: 'number' },
            },
            required: ['approved', 'pending', 'rejected'],
          },
          materials: { type: 'array', items: MATERIAL_ROW },
          // ⚠ `note` 只在 action=materials 且 pending>0 时出现（字符串）。**2026-09-20 更正**：这条注释
          // 原文写着"pending=0 时字段值是 `undefined`（既有实现如此）"—— 那个"既有实现"**已被修掉**
          // （显式 undefined 会让宿主 lossless 快照判 INVALID_TOOL_OUTPUT ⇒ 真机 isError；见本文件
          // action==='materials' 那段的长注释）。现在是**省略键**，所以 schema 这里列而不 required 正合适。
          note: { type: 'string' },
        },
        required: ['ok', 'action'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 30_000,
    // 第 6 步 §3：**可并行**。三个 action 全是只读 GET（projects / materials / inbox），
    // `:106-166` 的落点全是局部变量；本模块**没有**模块级可变状态（不像 collect.js 的
    // `_collectedBySession`）。且"本工具只读、不能批准"是本文件的硬纪律（见头注）。
    isConcurrencySafe: () => true,
    async execute(args, exec) {
      const action = typeof args?.action === 'string' && args.action ? args.action : 'projects'
      const projectId = typeof args?.project_id === 'string' ? args.project_id.trim() : ''
      if (action !== 'projects' && projectId === '') {
        // 明确报错而不是替用户猜一个项目（猜错就是"用错了项目的制度"，比报错坏得多）
        throw new Error(`ks_materials: action="${action}" 需要 project_id（prj_…）`)
      }
      // `combineSignals` 现返回 `{ signal, dispose }`（第 6 步 §4B-1）。这里只喂了**一个**
      // signal ⇒ 实现不建中转 controller、不往任何 signal 上加监听，`dispose` 是空操作，
      // 所以本调用点不需要 try/finally。⚠ 若将来在这里合并**第二个** signal，
      // 必须补 `try { … } finally { dispose() }`（照 `index.js` 的 ks_effect_report 写）。
      const { signal } = combineSignals(exec?.signal)
      const session = await manager.ensureLive(signal)
      const get = apiGetData(session)

      if (action === 'projects') {
        const path = '/api/v1/materials/projects'
        const rows = expectArray(await get(path, signal), path)
        return {
          ok: true,
          action,
          count: rows.length,
          projects: rows.map((p) => ({
            project_id: p.project_id ?? null,
            name: p.name ?? null,
            authority_policy: p.authority_policy ?? null,
          })),
          hint: rows.length === 0
            ? '还没有任何参考资料项目。项目要先建（POST /api/v1/materials/projects）才能放材料。'
            : '要用某个项目的材料作答，把它的 project_id 传给 ks_answer 的 params.material_project_id。',
        }
      }

      if (action === 'inbox') {
        const path = `/api/v1/materials/projects/${encodeURIComponent(projectId)}/inbox`
        const data = expectObject(await get(path, signal), path)
        const files = Array.isArray(data.files) ? data.files : []
        return {
          ok: true,
          action,
          project_id: projectId,
          dir: data?.dir ?? null,
          count: files.length,
          files: files.map((f) => ({
            file_name: f.file_name ?? null,
            size: typeof f.size === 'number' ? f.size : null,
          })),
          hint: files.length === 0
            ? '该项目的参考资料文件夹里没有待扫描的文件。'
            : '这些文件**尚未登记为材料**（未扫描 ⇒ 不可能被批准 ⇒ 不会进入作答）。'
              + '需要用户/界面执行扫描后才成为待评审材料。',
        }
      }

      // action === 'materials'
      const qs = typeof args?.status === 'string' && args.status
        ? `?status=${encodeURIComponent(args.status)}` : ''
      const path = `/api/v1/materials/projects/${encodeURIComponent(projectId)}/materials${qs}`
      const rows = expectArray(await get(path, signal), path)
        .map(trimMaterialRow).filter(Boolean)
      const counts = { approved: 0, pending: 0, rejected: 0 }
      for (const r of rows) {
        if (r.review_status in counts) counts[r.review_status] += 1
      }
      /* ⚠⚠ 2026-09-20（第 6 步 §1 顺带抓到、本批修）：原来这里是
         `note: counts.pending > 0 ? '…' : undefined` —— **显式给一个 undefined 值**。宿主在
         `createSuccessResult` 里先做 lossless 快照（`snapshotToolValue`），**undefined 会被判成
         "不是无损失的 JSON"** ⇒ `INVALID_TOOL_OUTPUT` ⇒ 这一次调用整体 `isError`。
         实测（施工子代理的探针）：`findUndefined=$.note`、
         `validateJsonSchemaValue=["value" must be a lossless JSON object]`；`pending>0` 时干净。
         **既有冒烟夹具恰好 `pending=1`，所以这条一直没被量到** —— 新契约冒烟补了 `pending=0` 这一组。
         ⇒ 修法：**省略键**（不给 undefined）。schema 里 `note` 本来就是"条件键"（列 properties 不 required），
         与这个修法一致。 */
      const out = {
        ok: true,
        action,
        project_id: projectId,
        filtered_by: args?.status ?? null,
        count: rows.length,
        review_counts: counts,
        materials: rows,
      }
      // 措辞纪律：**不能**因为"列到了 approved"就说"答案已会用它们"——那取决于调用方
      // 有没有把 project_id 传给 ks_answer；也**不能**把 pending 说成不可信（它只是未评审）。
      if (counts.pending > 0) {
        out.note = `本项目有 ${counts.pending} 份材料**尚未评审**，它们不会进入作答；`
          + '是否批准由**用户**判断（本工具只读，不代批）。'
      }
      return out
    },
  }
}

/* ------------------------------------------------------------------ *
 * 取数：直接用 engine.js 的同一套（无环、无注入）
 * ------------------------------------------------------------------ */

import { apiGet, combineSignals, originUrl } from './engine.js'

/** 返回一个 `(path, signal) => Promise<data>` 的取数器（信封不符即抛，不伪装空结果）。 */
function apiGetData(session) {
  return async (path, signal) => {
    const probe = await apiGet(originUrl(session.port), path, {
      token: session.token, signal, timeoutMs: 15_000,
    })
    // 与 ks_answer / ks_effect_report 同款加固：200 但信封缺 data ⇒ **抛错**。
    // 理由：把"引擎不可用/版本不匹配"伪装成"这个项目没有材料"，会让模型对用户
    // 断言"你还没上传材料"——一句可能完全错误的话（P1 准确性）。
    //
    // ⚠ 只查 `undefined` 不够：`data: null` 也会被下游 `Array.isArray()` 吃成空列表，
    // 于是**同样的伪装**从"缺字段"那条路漏进来。故形状校验放在**知道形状的调用点**
    // （见下面各 action 的 `expect*`），本层只管"字段在不在"。
    const env = probe.status === 200 && probe.body && typeof probe.body === 'object'
      ? probe.body : null
    if (!env || env.code !== 200 || env.data === undefined) {
      throw new Error(
        `ks_materials: ${path} 响应异常 HTTP ${probe.status || 'no-response'} `
        + `${probe.error || ''}（期望 {code:200,data:…}）。`
        + '请先 ks_ping 确认引擎版本/状态；**不要**把本次结果当成"没有材料"。')
    }
    return env.data
  }
}

/**
 * 形状守卫：期望什么形状就给什么形状，否则抛。
 *
 * 与"信封必须带 data"是两层不同的检查：那个管**有没有**，这个管**是不是**。
 * 少了这一层，`data: null` / `data: {}` 会被下游当成"空列表"，又变成一次静默伪装。
 */
function expectArray(data, path) {
  if (!Array.isArray(data)) {
    throw new Error(`ks_materials: ${path} 期望数组，收到 ${data === null ? 'null' : typeof data}`
      + '——不要把它当成"没有材料"。')
  }
  return data
}

function expectObject(data, path) {
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`ks_materials: ${path} 期望对象，收到 ${data === null ? 'null' : typeof data}`)
  }
  return data
}

