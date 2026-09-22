/**
 * ks-dsh-plugin — src/collect.js
 *
 * 模型侧采集工具 `ks_collect`（Phase C-6：让"**自己能搜集材料**"这句话成真）。
 *
 * ## 为什么与 `ks_materials` 分成两个工具（不是把 action 塞进去）
 * `ks_materials` 的纪律是**只读**（那个模块的头注写着：批准/拒绝不能开给模型，
 * 否则模型自己给自己发许可、硬门形同虚设）。采集是**写**操作——把两种权限混进
 * 一个工具，会让"这个工具到底会不会改东西"变成要逐 action 判断的问题，
 * 复核者也难一眼看出边界。所以：**读一个工具、写一个工具**，名字即权限。
 *
 * ## 采集能做什么、绝不能做什么
 * - 能：把**一个** URL 的正文抓回来，登记成该项目的**待评审**材料（`pending`）。
 * - **不能**：批准/拒绝（本工具没有这条路径，引擎侧也没有给它留口子）、
 *   不能自 claim 可信度（**不发 `source_tier`**：轴 A 由系统判据起 T3，
 *   要改只能由用户在界面上改）、不能批量（方案 §11.4 的采集预算未定）。
 *
 * ## 为什么要强调"一条一条、且要原始出处"
 * 采到的东西默认 **T3（线索）**：按 `authority` 的绝对规则，**仅线索不得单独支撑结论**，
 * 且"身份未知（没有域名/URL）不能互证"。所以本工具在回执里**如实**告诉模型
 * "它现在只是线索、要用户批准才会被用到"，并把 `review_status` 原样带出来。
 *
 * ## 目标项目怎么定（**不猜**）
 * 优先用会话绑定的项目（`/materials use <prj_id>` 设的会话级真值，与 `ks_answer` 同源）。
 * 模型也可以显式给 `project_id`（用 `ks_materials` 查到的）。两者**冲突时报错**，
 * 不偷偷换项目——"材料进了别的项目"是一种静默失真，比报错坏得多。
 */

import { apiPost, combineSignals, originUrl } from './engine.js'

/**
 * **暂定**上限：一个会话最多采集多少次（方案 §11.4 的采集预算**尚未定案**）。
 *
 * 为什么要有一个：引擎端点只收**单条** URL，但模型可以**反复调用**本工具——
 * 于是"没有批量入口"在模型这一侧其实等于"可以无限次单条"。那不是批量入口，
 * 却同样能把机器变成一个不停往外抓的爬虫（也烧网络与时间）。
 * 所以在预算定案之前，给一个**宽松但有界**的默认值，并在超出时**响亮报错**。
 *
 * ⚠ **这是暂定值，不是产品决定**：业主定案后改这一行即可（回执里会显示已用/上限，
 * 让用户看得见节奏）。**不**做成"静默截断"——那会让模型以为采到了其实没有。
 */
export const MAX_COLLECT_PER_SESSION = 20

/** 会话级计数器（进程内；插件重载后归零——它不是账本，是**刹车**）。 */
const _collectedBySession = new Map()

/** 只留模型判断需要的字段（别把整行塞进上下文）。 */
function trimCollected(m) {
  if (!m || typeof m !== 'object') return null
  return {
    material_id: m.material_id ?? null,
    title: m.title ?? null,
    review_status: m.review_status ?? null,
    source_tier: m.source_tier ?? null,
    origin: m.origin ?? null,
    lifecycle: m.lifecycle ?? null,
    url: m.url ?? null,
    domain: m.domain ?? null,
    tier_reason: m.tier_reason ?? null,
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

/** `trimCollected` 的对外形状（搜 `function trimCollected`）——9 个键一个不缺。 */
const COLLECTED_MATERIAL = {
  type: 'object',
  additionalProperties: false,
  properties: {
    material_id: NULLABLE_STRING,
    title: NULLABLE_STRING,
    review_status: NULLABLE_STRING,
    source_tier: NULLABLE_STRING,
    origin: NULLABLE_STRING,
    lifecycle: NULLABLE_STRING,
    url: NULLABLE_STRING,
    domain: NULLABLE_STRING,
    tier_reason: NULLABLE_STRING,
  },
  required: ['material_id', 'title', 'review_status', 'source_tier', 'origin',
    'lifecycle', 'url', 'domain', 'tier_reason'],
}

/**
 * Build the writing `ks_collect` tool.
 *
 * @param {object} manager EngineManager（与其它工具同一个）。
 * @param {(exec: object) => object} chatModeOf 读本会话生效的 chatmode（取绑定的项目）。
 */
export function makeCollectTool(manager, chatModeOf) {
  return {
    name: 'ks_collect',
    description:
      // 批3-c 瘦身（2026-09-22）：≤10 行；五条纪律全留、废话压缩（原文 var/tmp/desc-before-collect.txt）。
      '抓取一个 URL 的正文，登记为该参考资料项目的一条待评审材料（pending）。先自己找原始出处'
      + '网址再登记，评审由用户决定。纪律：① 一次一条（会话级上限，超出报错）；'
      + '② 采到的是 T3=仅线索，不得单独支撑结论；③ 本工具不能批准——登记后如实告诉用户'
      + '"未评审、不进结论"，请他决定；④ 只收网页正文（Content-Type 白名单 + 真实字节签名'
      + '两道判据；PDF/图片/压缩包/JS/CSS/JSON 接口如实拒绝）——只给真正的网页地址，不给下载'
      + '链接、接口地址或附件直链；⑤ 优先原始出处（政府/机构/期刊原文），不用转载/聚合页/内容农场。'
      + '参数：url 必填；project_id 省略=本会话绑定项目（冲突时报错不代换）；title 自选；'
      + 'note 写清为什么值得采（评审人会看）。',
    parameters: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: '要采集的网页 URL（http/https；内网/保留地址会被 SSRF 纪律拒绝）。',
        },
        project_id: {
          type: 'string',
          description: '目标参考资料项目 id（prj_…）。省略=用本会话绑定的项目。',
        },
        title: {
          type: 'string',
          description: '材料标题（省略则取页面 <title>）。',
        },
        note: {
          type: 'string',
          description: '采集说明：为什么采它、它与本次问题的关系（评审人第一眼看的就是这个）。',
        },
      },
      required: ['url'],
      additionalProperties: false,
    },
    output: {
      // 第 6 步 §1：**两条**返回路径都要装得下（抓取失败是**结果**不是异常）——
      // 失败分支（搜 `collected: false`）与成功分支（搜 `collected: true`）共有的 6 个键
      // 进 `required`；`status`/`reason`（只失败分支有）与 `duplicate`/`truncated`/`material`
      // （只成功分支有）列进 `properties` 但不 required。
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          project_id: { type: 'string' },
          collected: { type: 'boolean' },
          status: { oneOf: [{ type: 'number' }, { type: 'null' }] },
          reason: NULLABLE_STRING,
          duplicate: { type: 'boolean' },
          truncated: { type: 'boolean' },
          material: { oneOf: [COLLECTED_MATERIAL, { type: 'null' }] },
          session_collected: { type: 'number' },
          session_limit: { type: 'number' },
          hint: { type: 'string' },
        },
        required: ['ok', 'project_id', 'collected', 'session_collected', 'session_limit', 'hint'],
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    timeoutMs: 60_000,
    // 第 6 步 §3：**故意不声明 `isConcurrencySafe`** ⇒ 官方语义下走 exclusive
    // ((DSH) `packages/core/tools/src/index.ts:1295`：没有 classifier 就是 exclusive)。
    // 理由是官方契约的正面违反（(DSH) `docs/subsystems/tools.md:66-70`
    // "Opted-in executions must not mutate parent-owned state"）：
    //   ① 它**写**：`POST …/collect` 会让引擎登记一条 pending 材料（有外部副作用）；
    //   ② 它改**父级共享可变状态**：`_collectedBySession`（`:45`）的
    //      "读限额(`:160-166`) → await → 写限额(`:210`)" 不是原子的，两条并发 collect
    //      会**同时通过**限额判断（正是官方点名的 TOCTOU）。
    // ⚠ **不要**"顺手统一"给它加 `() => false`：官方只把**恰好 `true`** 当并行，缺省/false
    // 都是 exclusive；多写一个 `false` 只会让复核以为这里也做过判断（假证据）。
    async execute(args, exec) {
      const url = typeof args?.url === 'string' ? args.url.trim() : ''
      if (url === '') throw new Error('ks_collect: 需要 url（要采集的网页地址）')
      // ⚠ 硬塞进来的 `source_tier` 必须**响亮拒绝**（不是静默忽略）：采集者不得自 claim
      // 可信度（2026-09-17 复核的 INFO）。schema 里没有这个键，但"模型/宿主绕过 schema"
      // 是现实存在的路径——静默忽略会让调用方以为自己设上了（`sanitizeParams` 同款坑）。
      if (args !== null && typeof args === 'object' && 'source_tier' in args) {
        throw new Error('ks_collect: 不接受 source_tier——采集不得自 claim 可信度'
          + '（轴 A 由系统判据起 T3，要改请让用户在界面上改 /ks/materials/tier）')
      }

      // 目标项目：会话绑定优先（那是**用户**设的），显式 id 次之；冲突**报错**。
      const bound = (() => {
        try {
          const id = chatModeOf(exec)?.materialProjectId
          return typeof id === 'string' && id.length > 0 ? id : ''
        } catch {
          return ''
        }
      })()
      const asked = typeof args?.project_id === 'string' ? args.project_id.trim() : ''
      if (bound !== '' && asked !== '' && bound !== asked) {
        throw new Error(
          `ks_collect: project_id（${asked}）与本会话绑定的参考资料项目（${bound}）**不一致**——`
          + '不替你换项目。要么去掉 project_id（用绑定的那个），要么请用户先 `/materials use '
          + `${asked}` + '`。')
      }
      const projectId = bound !== '' ? bound : asked
      if (projectId === '') {
        throw new Error(
          'ks_collect: 没有目标项目——本会话未绑定参考资料项目，调用时也没给 project_id。'
          + '请先用 ks_materials 的 action="projects" 查项目，或请用户 `/materials use <prj_id>`。')
      }

      const sessionId = (() => {
        try {
          const id = exec?.agent?.session?.id
          return typeof id === 'string' && id !== '' ? id : '_'
        } catch {
          return '_'
        }
      })()
      // ⚠ **上限判断必须在 `ensureLive()` 之前**（2026-09-17 复核 C4 的 LOW）：
      // 放在后面的话，超限的那次调用仍会把引擎**拉起来**（"不打扰引擎"就不成立了）。
      const used = _collectedBySession.get(sessionId) ?? 0
      if (used >= MAX_COLLECT_PER_SESSION) {
        throw new Error(
          `ks_collect: 本会话已采集 ${used} 次，达到**暂定**上限 ${MAX_COLLECT_PER_SESSION} 次`
          + '（采集预算尚未定案，方案 §11.4）。请停下并告诉用户：需要更多就由他决定'
          + '（继续请让他明说）。**不要**把它当成"已经采够了"或"没有更多资料"。')
      }
      // `combineSignals` 现返回 `{ signal, dispose }`（第 6 步 §4B-1）。只喂一个 signal
      // ⇒ `dispose` 是空操作（实现不建中转 controller、不加任何监听），这里不需要
      // try/finally。⚠ 将来若合并**第二个** signal，必须补 dispose（照 `index.js` 的
      // ks_effect_report 写）。
      const { signal } = combineSignals(exec?.signal)
      const session = await manager.ensureLive(signal)
      const path = `/api/v1/materials/projects/${encodeURIComponent(projectId)}/collect`
      // ⚠ **不发 `source_tier`**（引擎端点会 422；这里连试都不试）：
      // 采集者不得自 claim 可信度——轴 A 由系统判据起 T3，要改只能由用户在界面上改。
      const probe = await apiPost(
        originUrl(session.port),
        path,
        {
          token: session.token,
          signal,
          timeoutMs: 60_000,
          body: {
            url,
            title: typeof args?.title === 'string' && args.title !== '' ? args.title : null,
            note: typeof args?.note === 'string' && args.note !== '' ? args.note : null,
          },
        })

      const env = probe.status === 200 && probe.body && typeof probe.body === 'object'
        ? probe.body : null
      if (!env || env.code !== 200 || env.data === undefined) {
        // 与 `ks_materials` 同一套加固（那边踩过一次就写成纪律了）：**不得**把
        // "引擎版本不匹配/信封坏了"伪装成"没采到"或"已经采到了"。
        throw new Error(
          `ks_collect: ${path} 响应异常 HTTP ${probe.status || 'no-response'} `
          + `${probe.error || ''}（期望 {code:200,data:…}）。`
          + '请先 ks_ping 确认引擎版本/状态；**不要**把本次结果当成"已经采到了"。')
      }
      const data = env.data
      // ⚠ **"没有 `collected` 字段"是信封/版本问题，不是"没采到"**（2026-09-17 复核的
      // MEDIUM，且复核实测**文档与实现相反**：文档说抛、实现却回了 `collected:false`）。
      // 为什么必须抛：形状不认识时引擎可能**已经登记了**一条 pending 材料，而回
      // `collected:false` 会让模型对用户说"没采到"——一句可能是假的话（P1 准确性）。
      if (data === null || typeof data !== 'object' || data.collected === undefined) {
        throw new Error(
          `ks_collect: 引擎回了 HTTP 200 但响应**形状不认识**（${path} 的 data 里没有 `
          + '`collected` 字段）——这通常是**引擎版本/接口不匹配**，不是"没采到"。'
          + '请先 ks_ping 确认引擎状态；**不要**把它当成"没有采到材料"。')
      }
      // 计数的是"**发起到引擎的采集请求**"（无论抓到没有）——刹车宁可多算不可少算；
      // SSRF 被拒那种连网都没出的也计入，理由是"模型该停止反复试内网地址"。
      const usedNow = used + 1
      _collectedBySession.set(sessionId, usedNow)
      const budget = { session_collected: usedNow, session_limit: MAX_COLLECT_PER_SESSION }
      if (data.collected !== true) {
        // 抓取失败是**结果**不是异常：如实回报原因，让模型去换来源或告诉用户。
        return {
          ok: true,
          project_id: projectId,
          collected: false,
          status: typeof data.status === 'number' ? data.status : null,
          reason: data.reason ?? null,
          ...budget,
          hint: '这条**没有**登记成材料（原因见 reason）。不要把它算作已获取的证据；'
            + '可以换个**原始出处**的网址再试，或如实告诉用户没采到。',
        }
      }
      const material = trimCollected(data.material)
      return {
        ok: true,
        project_id: projectId,
        collected: true,
        duplicate: data.duplicate === true,
        truncated: data.truncated === true,
        material,
        ...budget,
        hint: (data.duplicate === true
          ? '这个网址的内容**与项目里已有的一份相同**（引擎按内容判重），没有重复登记。'
          : '已登记为**待评审**材料。')
          + '它现在是 **T3=仅线索**（不得单独支撑结论），**不会**进入任何结论——'
          + '必须由**用户**评审批准后才可能被用到（本工具不能代批）。'
          + '请如实告诉用户「我采了一条，还没评审」，并把 material.review_status 一起说清。',
      }
    },
  }
}
