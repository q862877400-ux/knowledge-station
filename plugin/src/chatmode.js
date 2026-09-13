/**
 * ks-dsh-plugin — src/chatmode.js (2026-09-10; 2026-10 增收藏夹维度)
 *
 * 「📜 查法规模式」/「🔖 仅收藏」/「📁 收藏夹内提问」——**会话级**开关（决策 14/16 的 DSH 转生版；
 * 收藏夹维度是 2026-10 收藏目录功能的一部分）。
 *
 * 语义（决策 14/16 + 2026-10 业主批准）：
 * - 「📜 查法规模式」：打开后，该会话每次组装系统提示都会多出一段**取证纪律**
 *   （见 FORENSIC_PROMPT）——凡涉法规/国标/合规的问题必须走 ks_answer 取证链路、
 *   只引现行有效版本、三段式（依据/推导/结论）输出、证据用 evidence_url 渲染成
 *   可点 Markdown 链接；核验未通过必须如实说明。
 * - 「🔖 仅收藏」：**仅在查法规模式开启后才出现**；打开后检索范围压到用户收藏的
 *   条款。提示词只是"说明"，真正的强制在 index.js 的工具层（ks_answer 按会话
 *   强制 `bookmarks_only`；ks_resolve_clause 对收藏集外条款打标并禁止当依据）
 *   ——工具层与提示词层共用本模块的 `effectiveChatMode()` 作为**唯一真值来源**。
 * - 「📁 收藏夹内提问」（2026-10）：收藏目录树上每个收藏夹一个开关；开启后该会话
 *   检索限定在**该收藏夹的内容**内——夹内标准级收藏按整本标准计、条款级收藏按
 *   单条计（并集）。folderId 非空自动蕴含查法规模式（范围提问必然要求取证链路）。
 *   host 强制给 ks_answer 传 `folder_id`，ks_resolve_clause 对夹外条款打
 *   `folder_scope: "outside"` 标记。附加段优先级：夹范围段 > 仅收藏段。
 *
 * 为什么状态放 host 而不是会话日志：client 半只负责点按钮，真正生效的是 host 半
 * 注册的 `systemPrompt.section`——它的 text provider 每次组装提示都会重新求值，
 * 因此开关一落盘，下一轮请求立刻生效（无需重启、无需重开会话）。
 * 状态落盘 `ks-chatmode.json`（与 ks-inspection.json / ks-announce.json 并列，
 * 各自全量写互不覆盖），所以 dsh 重启后开关仍在；多个标签页共享同一份 host 状态。
 *
 * ── verifier 两轮审计后的加固（2026-09-10）────────────────────────────────
 * 1. **启动即加载**：段 provider 是同步函数、不能 await，只靠 client 的 GET 触发
 *    懒加载会让"落盘真值"在没有该 GET 的场景（CLI/ACP 客户端、dock 未挂载、GET 失败、
 *    dsh 重启后首轮提问先于 dock 挂载）静默失效。所以 `apply()` 里显式
 *    `ensureLoaded()` 预热，provider 侧再兜一次"未加载则触发加载"。
 * 2. **跨进程写锁 + 唯一 tmp + 基线 CAS**：全机（`%APPDATA%\KnowledgeStation`）可能同时有
 *    多个 dsh 进程。第一轮整改只做了"合并 + 固定名 .tmp"，verifier 二轮用双进程实测
 *    推翻了它（两个写者共用一个 tmp 名会互相截断/偷文件；无 CAS 的读-改-写会整批丢更新：
 *    实测 A 侧 54 次报成功、磁盘上 A 的会话 0/60）。第二轮先上"唯一 tmp + 基线 CAS +
 *    回读校验"，**双进程实测仍然收敛不了**（24 次报成功、10 条最终不在盘上——校验与 rename
 *    之间的窗口无法消除），于是最终落地为一枚**只持有几毫秒的跨进程锁文件**
 *    （`open(..., 'wx')` 原子抢占；等待有上限；mtime 超 5s 视为持有者已崩溃可抢走，
 *    因此不会永久死锁），锁内再做"读基线 → 合并 → rename → 回读校验"作第二道防线。
 *    双进程并发实测：24/24 报成功且 24/24 真在盘上。
 * 3. **读失败不再等于"空"**：只有 `ENOENT` 才算真空；JSON 损坏先备份 `.corrupt-<ts>`
 *    再按空处理（可恢复）；其他读错误（EACCES/EBUSY/EISDIR）标记 degraded 并**拒绝
 *    写盘**，绝不用一份"读不到"的空快照覆盖磁盘上完好的状态。该策略在**加载与
 *    合并两条路径上一致**（二轮审计抓到合并路径漏了这条）。degraded 随 GET/PUT 回显。
 * 4. **降级可恢复**：`_writesBlocked` 不再永久——下一次 PUT 会先做一次"重新加载"
 *    （`allowStateReload()`），瞬时占用（AV/索引器 EBUSY）不会再让本进程永久存不下。
 * 5. **`_touched` 用完即释放**：落盘成功且内存值未再变时释放该会话的所有权，
 *    否则"本进程改过 A → 他进程关了 A → 本进程写别的会话"会把 A 复活（二轮审计实证）。
 * 6. **子会话继承**：DSH 的子 agent 是**新会话**（`origin:'subagent'`），故默认查不到
 *    父会话开关。`effectiveChatMode()` 沿 `session.header.parentSession` 向上回溯
 *    （≤4 跳，经 index.js 注入的 resolver 解析），父开则子继承并显式标注"继承自父会话"。
 *    提示词层与工具层**共用**这一个函数——二轮审计抓到过"提示词说已强制、工具层没强制"
 *    的打脸组合。
 *
 * 已知边界（诚实标注）：
 * - DSH 的 `complete: true` 提示段会让最终 prompt **只剩该段**（persona preset 可启用），
 *   此时本段会被整体吞掉。所以本特性不把它当唯一护栏（工具层强制是主护栏）；
 * - 继承只在**父 agent 仍活跃**时成立（`ctx.agents.get(parent)` 解析父会话；冷父/已被
 *   回收的父会话静默不继承）；
 * - `apply()` 预热与"重启后第一个回合"之间仍有毫秒级窗口（磁盘读），该回合可能少注入
 *   一次纪律段；工具层门禁在调用时求值，不受影响；
 * - 状态只在**本进程启动时**读一次：别的 dsh 进程改了同一份文件，本进程的注入与回显
 *   会停在旧值直到重启（任何锁都治不了这一点，属设计取舍）；
 * - 继承是单向的（父 → 子），子会话的开关不会反向影响父会话；
 * - 段名重复注册会抛（cordis systemPrompt 契约），本模块只注册一次。
 *
 * Routes（统一被 trust.js 的同源栅栏覆盖）：
 *   GET /ks/chat-mode?session=<sessionId>   读该会话开关
 *   PUT /ks/chat-mode                       写该会话开关（body: {session, forensic?, bookmarksOnly?, folderId?, folderName?}）
 *                                                          folderId: null 关闭夹范围；'bmf_…' + folderName 开启
 */

import { open, readdir, readFile, rename, stat, unlink, utimes, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

import { sessionFilePath } from './engine.js'
import { requireJsonBody } from './trust.js'

export const KS_CHAT_MODE_PATH = '/ks/chat-mode'

/**
 * 状态文件名（与 ks-inspection.json / ks-announce.json 并列）。
 *
 * 目录解析顺序：`$KS_CHATMODE_DIR` → `$KS_DATA_DIR`（经 engine.sessionFilePath）→
 * `%APPDATA%\KnowledgeStation`。为什么单独留一个环境变量：`$KS_DATA_DIR` 同时决定
 * **引擎自己的数据目录与库**，冒烟只想隔离"开关状态文件"却不想让引擎连到一个空库
 * （verifier 四轮实测：混用会让 live 通道打到刚 spawn 的空库上）。
 */
export function chatModeFilePath() {
  const dir = process.env.KS_CHATMODE_DIR
  if (typeof dir === 'string' && dir.length > 0) return join(dir, 'ks-chatmode.json')
  return join(dirname(sessionFilePath()), 'ks-chatmode.json')
}

/** 查法规模式的系统提示段名（唯一，重复注册会抛）。 */
export const FORENSIC_SECTION_NAME = 'ks:forensic-mode'
/**
 * 提示段顺序：工具指引占 100–199，本段排在同段末尾（199）。注意这**不保证**它
 * 是装配中的最后一段（部署可注册更高 order 或 complete 段），所以它是"当前装配中
 * 最靠后的段之一"，护栏不依赖顺序。
 */
export const FORENSIC_SECTION_ORDER = 199

/**
 * 会话 id 上限。形态校验刻意**不做** `^session-...$` 前缀正则：本仓库的会话 id
 * 不止一种形态——`import_chat` 导入的会话是 `import-<src>-<n>` / `import-<源 id>`，
 * DSH apiproxy 还接受调用方自带的 sessionId。硬锁前缀会把导入会话的开关写入全 400。
 * 这里只保证"非空、无空白/控制字符、长度受限"，且该 id 只当 JSON 键用（从不拼路径）。
 */
const MAX_SESSION_ID_LENGTH = 128
/** 状态文件条目上限（防无界增长）。 */
export const MAX_SESSIONS = 500
/** 残骸清理门槛（24h）：覆盖 .tmp、.corrupt-<ts> 与 .steal-<pid>-<ts> 三类自有临时文件。 */
const ARTIFACT_MAX_AGE_MS = 24 * 60 * 60 * 1000

/** 落盘 CAS 重试上限（多进程并发时的收敛预算）。 */
const PERSIST_ATTEMPTS = 5
/** 跨进程写锁：等待上限与"陈旧锁"判定（持有者崩溃后能被抢走，不会永久死锁）。 */
const LOCK_WAIT_MS = 3_000
const LOCK_STALE_MS = 5_000
/** Windows 上 rename 覆盖目标时的瞬时失败码（别人正打开/替换该文件、AV 扫描）。 */
const RENAME_TRANSIENT = new Set(['EPERM', 'EBUSY', 'EACCES', 'EEXIST'])

const sleep = (ms) => new Promise((resolve) => { setTimeout(resolve, ms) })

/**
 * rename 覆盖目标：Windows 上目标被另一进程短暂打开/替换时会瞬时 EPERM/EBUSY
 * （双进程实测：不做重试会有 ~15% 的写入被无谓地判失败），退避重试几次再放弃。
 */
async function renameWithRetry(tmp, file) {
  let lastError = null
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      await rename(tmp, file)
      return
    } catch (error) {
      lastError = error
      if (!RENAME_TRANSIENT.has(error?.code)) throw error
      await sleep(4 + attempt * 8)
    }
  }
  throw lastError
}

/**
 * 取证纪律提示词（只在查法规模式开启时注入）。措辞对齐项目 P1 准确性红线：
 * 只引现行版、查无即说查无、核验未通过不得隐去、工具失败不得说成"库内无"。
 */
export const FORENSIC_PROMPT = [
  '【查法规模式（本会话已开启）】',
  '本会话凡涉及法规、国家标准、行业标准与合规判定的问题，必须走本地法规库取证链路，禁止凭记忆或网络内容作答：',
  '1. 先调用 `ks_answer` 取证（它只引现行有效版本并自带核验）。需要精确定位条款号时用 `ks_resolve_clause`，但**必须核对它返回的 `legal_status`**：非 effective（已废止/被替代/即将实施）只能作历史沿革或预告说明，不得作为依据。它的命中体自带 `evidence_url`，链接就用它渲染；若返回 `bookmarks_scope: "outside"`（该条不在用户收藏集内）则**只能用于定位，不得写入依据区**。',
  '2. 答案固定三段式：**依据** → **推导** → **结论**。依据区逐条列出「标准号（含年份）+ 条款号 + 效力层级 `legal_hierarchy` + 页码 + 原文要点」，每条把该条的 `evidence_url` 渲染成 Markdown 可点链接（例：[依据：GB 30871-2022 8.1.3](<evidence_url>)）。若某条 `evidence_url` 为 null（无原件锚点），只写文字引用并在该条后标注「（无原件锚点）」，**不要**生成 `(null)` 之类的空链接。',
  '3. 证据区（`evidence`）的条款 `legal_status` 恒为 effective，不必逐条声明效力；但若 `notes` 里出现「【即将生效】」条目，必须在结论之后**单独加一句**：标准号 + 施行日期 + 届时将改变什么。该句是预告，不得作为本次依据。',
  '4. 若 `ks_answer` 返回 `verification.is_valid === false`，必须在答案末尾显式说明核验未通过及具体原因（如数字篡改、模态缺失），不得隐去或含糊带过；若 `verification` 为 null、`ok` 为 false 或响应信封异常，说明**取证本身失败**并如实报告失败原因，**不得**说成「库内无此条款」。',
  '5. 未开启「仅收藏」时，只有确属库里没有相关条款才回答「库内无此条款」；不要用记忆或网络内容冒充库内依据。若 `tier` 为 `reference` 或 `found` 为 false，结论区必须说明这是参考性口径/无直接规定。',
].join('\n')

/**
 * 「仅收藏」附加段（查法规模式 + 仅收藏同时开启时追加）。
 * 措辞纪律：host 能证明的是"**已强制传参**"（`answer_scope` 回显），不能证明引擎侧
 * 过滤一定生效（引擎过滤异常时会静默返回全库证据），所以不写"已生效"。
 */
export const FORENSIC_BOOKMARKS_PROMPT = [
  '6. 【仅收藏】本次检索已由 host 强制传参限定在用户收藏的条款内（`ks_answer` 的 `params.bookmarks_only = true`，返回值里的 `answer_scope` 回显的是 **host 是否强制传参**，它不能证明引擎侧过滤一定生效；`ks_resolve_clause` 命中收藏集外的条款会带 `bookmarks_scope: "outside"`）。',
  '本条第 5 条的「库内无此条款」在此**不适用**：收藏集内没有相关条款时，必须回答「**收藏集内无相关条款（库内可能仍有）**」，并询问用户是否解除「仅收藏」限制；绝不能说「库内无此条款」。',
  '判断范围过滤是否真的生效，用**机器字段**、不要猜：`evidence[]` 每条都有三态标记 `bookmarked`——`true`=在收藏集内；`false`=不在收藏集内（**仅收藏模式下不该出现**，出现即说明过滤未生效，必须如实说明，不得把结论说成"已限收藏集内"）；**`null`=引擎未提供该值（收藏集查询失败或引擎版本较旧），此时不得据此断言过滤是否生效**。引擎也会在 `notes` 里用【仅收藏】条目说明本轮是否真的限定了收藏集（写了"未能限定"就必须照实转述）。',
  '`ks_resolve_clause` 的 `bookmarks_scope` 只在**命中**时才非 null：查无此条时它是 null，按第 5 条如实回答即可，不要声称"该条不在收藏集内"；它返回的 `scope_notice` 是**禁令说明，不是依据**，不得引用。',
].join('\n')

/**
 * 「收藏夹内提问」附加段（folderId 生效时追加，优先级高于「仅收藏」——
 * 夹范围是更具体的范围）。范围语义（业主批准）：夹内标准级收藏按**整本标准**计，
 * 条款级收藏按**单条**计，两者并集。
 */
export const FORENSIC_FOLDER_PROMPT = [
  '6. 【收藏夹内提问】本会话检索已由 host 强制传参限定在用户收藏夹「{FOLDER_NAME}」的内容内（`ks_answer` 的 `params.folder_id` 已由 host 合并，`answer_scope.folder` 回显的是 **host 是否强制传参**，不能证明引擎侧过滤一定生效）。范围语义：夹内**标准级**收藏按整本标准计（该标准全部条款都在范围内），**条款级**收藏按单条计，两者并集。',
  '本条第 5 条的「库内无此条款」在此**不适用**：夹内没有相关条款时，必须回答「**收藏夹「{FOLDER_NAME}」内无相关条款（库内可能仍有）**」，并询问用户是否解除夹范围限制；绝不能说「库内无此条款」。',
  '引擎会在 `notes` 里用【收藏夹】条目说明本轮是否真的限定了范围：写「未能限定」（收藏夹已被删除或范围查询失败）就必须照实转述，**绝不能把结论说成"已限收藏夹内"**；`ks_resolve_clause` 命中夹外条款会带 `folder_scope: "outside"` + `folder_notice`，该条款只能用于定位、不得写入依据区。',
].join('\n')

function renderFolderPrompt(name) {
  const safe = String(name ?? '').replace(/}/g, '）').replace(/{/g, '（')
  return FORENSIC_FOLDER_PROMPT.replaceAll('{FOLDER_NAME}', safe)
}

/* ------------------------------------------------------------------ *
 * 状态（进程单写者 + 合并落盘 + 原子替换 + CAS；结构漂移安全网）
 * ------------------------------------------------------------------ */

/**
 * 全关基线。folderId/folderName（2026-10 收藏目录）：
 * - folderId 非空 → 夹内提问激活：host 强制给 ks_answer 传 folder_id，
 *   且自动蕴含查法规模式（夹范围 ⊃ 取证纪律——范围提问必然要求取证链路）。
 * - folderName 是 folderId 的显示名快照（host 不查引擎也能渲染提示段与回执；
 *   引擎侧真值永远是 folder_id，名字漂移只影响文案不影响范围）。
 */
const MODE_OFF = { forensic: false, bookmarksOnly: false, folderId: null, folderName: null }
const SOURCE_NONE = 'none'

/** folderId 形态校验：引擎 ULID 形（bmf_…），非空、无空白、长度受限。 */
function normalizeFolderId(raw) {
  if (raw === null || raw === undefined || raw === false) return null
  const id = String(raw).trim()
  if (id.length === 0 || id.length > 64) return null
  // eslint-disable-next-line no-control-regex
  if (/[\s\u0000-\u001f]/.test(id)) return null
  return id
}

function normalizeFolderName(raw) {
  if (raw === null || raw === undefined) return null
  const name = String(raw).trim()
  if (name.length === 0 || name.length > 60) return null
  return name
}

/** sessionId → mode。进程内真值；落盘只是它的快照。 */
let _modes = new Map()
/** 本进程显式写过的会话 id：合并落盘时这些以本进程为准（其余取磁盘并集）。 */
let _touched = new Set()
/**
 * **显式关闭**意图（verifier 四轮 P1-B）：只有用户真的关掉某个会话时才进这里。
 * 为什么需要它与 `_touched` 分开：
 * - `_touched` 只表达"这个会话以本进程内存为准"；
 * - `_cleared` 才表达"用户明确要删掉磁盘上的这一条"。
 * 旧实现把"内存里没有"当成"用户关掉了"，于是任何让 `_modes` 变空的事件
 * （读失败后 ensureLoaded 的 catch）都会把磁盘上**别人写好的**条目当成待删项删掉。
 */
let _cleared = new Set()
let _loaded = null
let _persistChain = Promise.resolve()
let _tmpSeq = 0
/** null = 正常；字符串 = 降级原因（读损坏/读错误），随路由回显。 */
let _degraded = null
/** 读错误导致不可信时拒绝写盘（避免用空快照覆盖磁盘上的好数据）。 */
let _writesBlocked = false
let _logger = null

/** 让 host 注入 logger（可选）。 */
export function setChatModeLogger(logger) {
  _logger = logger ?? null
}

function warn(...args) {
  try {
    _logger?.warn?.(...args)
  } catch { /* 日志失败绝不影响开关语义 */ }
}

function normalizeMode(raw) {
  const forensic = raw?.forensic === true
  const folderId = normalizeFolderId(raw?.folderId)
  // 仅收藏依附于查法规模式：父开关关闭时自动降级（决策 16）。
  // 夹范围是独立维度：folderId 非空时 forensic 强制为 true（夹内提问必然要求
  // 取证链路——范围提问的答案必须带三段式与证据链接，这正是查法规模式的纪律）。
  return {
    forensic: forensic || folderId !== null,
    bookmarksOnly: (forensic || folderId !== null) && raw?.bookmarksOnly === true,
    folderId,
    folderName: folderId === null ? null : normalizeFolderName(raw?.folderName),
  }
}

/** 会话 id 形态校验：非空、无空白、无控制字符、长度受限（不锁前缀，见上方注释）。 */
export function normalizeSessionId(raw) {
  if (typeof raw !== 'string') return ''
  const id = raw.trim()
  if (id.length === 0 || id.length > MAX_SESSION_ID_LENGTH) return ''
  // eslint-disable-next-line no-control-regex
  if (/[\s\u0000-\u001f]/.test(id)) return ''
  return id
}

/** 解析状态文件文本 → {modes, skipped, corrupt}（只收开启态；非法条目跳过并计数）。 */
function parseState(text) {
  const out = new Map()
  let skipped = 0
  let parsed = null
  try {
    parsed = JSON.parse(text)
  } catch {
    return { modes: out, skipped, corrupt: true }
  }
  const sessions = parsed && typeof parsed === 'object' && parsed.sessions && typeof parsed.sessions === 'object'
    ? parsed.sessions
    : null
  if (sessions === null) return { modes: out, skipped, corrupt: false }
  for (const [sid, raw] of Object.entries(sessions)) {
    const id = normalizeSessionId(sid)
    if (id.length === 0) {
      skipped += 1
      continue
    }
    const mode = normalizeMode(raw)
    if (mode.forensic) out.set(id, mode) // 只落盘开启态：关掉的会话不留垃圾
  }
  return { modes: out, skipped, corrupt: false }
}

/** 读状态文件，套用统一的"读失败/损坏"政策。抛错 = 不可信（调用方决定是否拒写）。 */
async function readStateFile() {
  const file = chatModeFilePath()
  let text
  try {
    text = await readFile(file, 'utf8')
  } catch (error) {
    if (error?.code === 'ENOENT') return { modes: new Map(), text: null, missing: true }
    const reason = `read_failed:${error?.code ?? 'unknown'}`
    _degraded = reason
    _writesBlocked = true
    throw Object.assign(new Error(reason), { ksReason: reason })
  }
  const { modes, skipped, corrupt } = parseState(text)
  if (corrupt) {
    // verifier 三轮 P2 / 四轮 P2-F：备份不能"先判断后动手"（check-then-act 仍留窗口，
    // 会把别的进程刚写好的好文件挪成 .corrupt-*）。改成**先原子改名、再复核被改名的那份**：
    // 内容确实还是我们判损的损坏文本 → 备份成立；否则说明挪走的是好文件 → 立刻放回原位，
    // 并按"读失败"处理（degraded + 拒写），绝不丢别人的状态。
    const parked = `${file}.corrupt-${Date.now()}`
    try {
      await rename(file, parked)
    } catch {
      return { modes: new Map(), text: null, missing: false, corrupt: true }
    }
    const moved = await readFile(parked, 'utf8').catch(() => null)
    if (moved !== text) {
      await rename(parked, file).catch(() => {})
      const reason = 'read_changed_while_judging'
      _degraded = reason
      _writesBlocked = true
      throw Object.assign(new Error(reason), { ksReason: reason })
    }
    _degraded = 'corrupt_state_file'
    warn('ks-dsh-plugin: 查法规模式状态文件损坏，已备份为 .corrupt 并重置', file)
    return { modes: new Map(), text: null, missing: false, corrupt: true }
  }
  if (skipped > 0) warn(`ks-dsh-plugin: 查法规模式状态文件有 ${skipped} 条非法会话 id，已跳过`)
  return { modes, text, missing: false }
}

/**
 * 懒加载状态文件（首次访问时读一次）。只有 ENOENT 才算真空；损坏已备份；
 * 读错误置 degraded + 拒绝写盘。绝不抛：读失败不能影响开关本身。
 * 赋值时把**本进程已写过的会话**合并进来（避免加载结果覆盖刚写的开关——二轮审计
 * 指出的窄竞态：`setMode` 早于加载落地时会被整份覆盖）。
 */
export async function ensureLoaded() {
  if (_loaded !== null) return _loaded
  _loaded = (async () => {
    try {
      const { modes, corrupt } = await readStateFile()
      if (corrupt) {
        // 损坏文件解析出来是垃圾（空 Map）——**不动内存态**（verifier 五轮 P2-2：
        // 与"读失败不动 _modes"同一原则；清空内存会让用户开着的护栏静默关闭）。
        // 但这些"只存在于内存"的开关必须纳入所有权，否则下一次成功落盘不会把它们
        // 物化回磁盘 → 用户看到开着、重启却变关（verifier 六轮 P2-2）。
        for (const sid of _modes.keys()) {
          if (!_cleared.has(sid)) _touched.add(sid)
        }
        // 注意这里**不**提前 return：`sweepStaleArtifacts()` 在下面统一执行
        // （verifier 六轮 P2-1：提前 return 会让残骸清理在整个进程生命周期内一次都不跑）。
      } else {
        for (const sid of _touched) {
          const mine = _modes.get(sid)
          if (mine !== undefined) modes.set(sid, mine)
          // 只有**显式关闭**过的会话才从磁盘快照里删掉。内存里"没有"绝不等价于
          // "用户关掉了"——verifier 四轮 P1-B：旧写法在读失败把 _modes 清空后，
          // 下一次成功落盘会把磁盘上别人写的条目整条删掉。
          else if (_cleared.has(sid)) modes.delete(sid)
        }
        _modes = modes
      }
    } catch {
      /* 读失败：已置 degraded/writes_blocked。**不动 _modes**——内存态是真相，
         读失败不改变用户已经做出的选择（清空它会让开关蒸发，且带着 _touched 的
         所有权变成对磁盘条目的删除指令）。 */
    }
    sweepStaleArtifacts()
    return _modes
  })()
  return _loaded
}

/** 自己产生的临时/备份残骸清理（24h 前的 .tmp / .corrupt-* / .steal-*）；best-effort，绝不抛。 */
function sweepStaleArtifacts(nowMs = Date.now(), maxAgeMs = ARTIFACT_MAX_AGE_MS) {
  const file = chatModeFilePath()
  const dir = dirname(file)
  const base = (file.split(/[\\/]/).pop() ?? '') + '.'
  const cutoff = nowMs - maxAgeMs
  return (async () => {
    try {
      const names = await readdir(dir)
      for (const name of names) {
        if (!name.startsWith(base)) continue
        // verifier 四轮 P2-E3：抢锁用的 .steal-<pid>-<ts> 也是我们产生的残骸
        if (!/\.tmp$/.test(name) && !/\.corrupt-\d+$/.test(name) && !/\.steal-\d+-\d+$/.test(name)) continue
        const full = join(dir, name)
        try {
          const st = await stat(full)
          if (st.mtimeMs < cutoff) await unlinkWithRetry(full)
        } catch { /* 单个文件失败无所谓 */ }
      }
    } catch { /* 目录读不到：忽略 */ }
  })()
}

/**
 * 是否有**任何会话**开着查法规模式（批3 引擎 keepalive 判据，问题清单#12）。
 * 只读内存 map（getMode 已含"未加载则顺手触发加载"），不会拉起引擎、不落盘。
 * 引擎空闲回收前问一次：开着 → 续命，避免下一次 ks_* 调用承担 20s+ 冷启动。
 */
export function hasActiveForensicSessions() {
  if (_loaded === null) void ensureLoaded()
  return _modes.size > 0
}

/**
 * 允许下一次写操作重试一次加载（降级不是永久的：瞬时占用会自愈）。
 * **不动 `_modes`/`_touched`**：verifier 三轮指出——旧实现把它们清空，于是"降级期间
 * 用户已开、UI 已告知仅内存生效"的开关会在下一次点击时**提前蒸发**（提示层与工具层
 * 一起变回关闭，方向还是关护栏）。`ensureLoaded()` 本来就会把 `_touched` 覆盖到新读到
 * 的磁盘快照上，保留内存态是安全且语义正确的。
 */
export function allowStateReload() {
  if (!_writesBlocked) return false
  _loaded = null
  _degraded = null
  _writesBlocked = false
  return true
}

/** 当前状态健康度（随路由回显，便于用户/审计自证）。 */
export function stateStatus() {
  // health 是给客户端用的**分类**（verifier 六轮 P2-4：把读失败/写失败/损坏重置压进
  // 一个布尔会让"损坏已备份"被显示成"写不进盘"）。degraded 仍是原始原因串，便于排障。
  let health = 'ok'
  if (_writesBlocked) health = 'read_blocked'
  else if (_degraded === 'corrupt_state_file') health = 'corrupt_reset'
  else if (typeof _degraded === 'string') health = 'write_failed'
  return { health, degraded: _degraded, writes_blocked: _writesBlocked, sessions: _modes.size }
}

function tmpPathFor(file) {
  _tmpSeq += 1
  // 唯一 tmp 名：固定名会让两个进程互相截断/偷文件（二轮审计双进程实测）
  return `${file}.${process.pid}.${_tmpSeq}.tmp`
}

/**
 * 删除（释放）一个可能正被别的进程打开/抢占的文件，容忍 Windows 的瞬时失败。
 * 返回是否真的删掉了（或本来就不存在）。
 */
async function unlinkWithRetry(target) {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      await unlink(target)
      return true
    } catch (error) {
      if (error?.code === 'ENOENT') return true
      if (!RENAME_TRANSIENT.has(error?.code)) return false
      await sleep(3 + attempt * 6)
    }
  }
  return false
}

/**
 * 跨进程写锁（有界 + 陈旧自愈 + **原子抢夺**）。为什么最终还是要它：verifier 二轮的双进程
 * 实测证明"唯一 tmp + 基线 CAS + 回读校验"这套无锁方案**收敛不了**——两个写者读同一
 * 基线、各自 rename，后落地的把先落地的成批抹掉（实测 24 次报成功、10 条最终不在盘上；
 * 校验与 rename 之间存在不可消除的窗口）。所以加一把**只持有几毫秒**的文件锁：
 * - `open(lock, 'wx')`（O_CREAT|O_EXCL）是原子抢占；
 * - **抢陈旧锁也用原子 rename**（`rename(lock, lock.steal-…)` 只有一个进程会成功）——
 *   verifier 三轮实测：`stat → unlink → open` 这种"先删后建"的抢法存在 TOCTOU，
 *   两个进程可以同时进入临界区（在两进程同抢一枚陈旧锁的台架上，插入 2ms 调度间隙即
 *   4/6 次重叠），于是又回到"两个写者并写"的原点；
 * - 每轮循环都检查 deadline（超时抛 `state_lock_timeout`，由调用方如实报 persisted:false），
 *   不存在无上限热循环；
 * - 陈旧判据同时覆盖"未来 mtime"（时钟回拨/时区调整会让 `now - mtime` 变负，绝不能因此永久锁死）；
 * - 释放用 `unlinkWithRetry`；真释放不掉就把 mtime 归零，等于主动标记"可抢"；
 * - 锁内做"读基线 → 合并 → rename → 回读校验"，作为第二道防线。
 * 锁内只有本地 FS 操作（读/写/改名），状态上限 MAX_SESSIONS=500，持锁时间毫秒级。
 */
async function withStateLock(fn) {
  const file = chatModeFilePath()
  const lock = `${file}.lock`
  const deadline = Date.now() + LOCK_WAIT_MS
  const expired = () => Date.now() > deadline
  // 持有者身份：pid + 随机 nonce。释放前必须复核锁里写的还是自己的 nonce
  // （verifier 四轮 P2-E：持锁超过 LOCK_STALE_MS 时锁会被别人抢走，此时无条件
  //  unlink 删掉的就是**别人的**锁，第三个写者立刻进来 —— 双写者回归）。
  const token = `${process.pid}:${Math.random().toString(36).slice(2)}`
  let handle = null
  for (;;) {
    if (expired()) throw new Error('state_lock_timeout')
    try {
      handle = await open(lock, 'wx')
      break
    } catch (error) {
      if (error?.code !== 'EEXIST') throw error
      // 陈旧锁（持有者崩了 / mtime 在未来）→ **原子**抢过来：rename 只有一个赢家
      try {
        const st = await stat(lock)
        const age = Date.now() - st.mtimeMs
        if (age > LOCK_STALE_MS || age < -1_000) {
          const stolen = `${lock}.steal-${process.pid}-${Date.now()}`
          try {
            await rename(lock, stolen)
            await unlinkWithRetry(stolen)
          } catch { /* 别人先抢到了：继续等 */ }
          continue // 顶部会再查 deadline；这里不 sleep 是有意的（刚抢到就能试 open）
        }
      } catch {
        continue // 锁刚被释放（stat ENOENT）→ 立刻重试（同样受顶部 deadline 约束）
      }
      await sleep(4 + Math.floor(Math.random() * 12))
    }
  }
  // 写 token 也可能失败（ENOSPC/EPERM）——那种情况下锁文件是**我们建的但内容为空**，
  // 必须自己收拾掉；否则它会被后面的"所有权复核"误判成"他人接管"而留下 5 秒全局写阻塞，
  // 并且把自家故障归因给别人（verifier 五轮 P2-3）。
  try {
    await handle.writeFile(`${token}\n`, 'utf8')
  } catch (error) {
    await handle.close().catch(() => {})
    // 与正常释放路径同一条纪律：只删**自己的**锁（内容为空 = 我们刚建但没写进去；
    // 若已被别人判陈旧抢走并重建，就不能动）——verifier 六轮 P2-6
    const owner = await readFile(lock, 'utf8').catch(() => null)
    if (owner === null || owner.trim() === token || owner.trim() === '') {
      await unlinkWithRetry(lock)
    }
    throw error
  }
  try {
    return await fn()
  } finally {
    await handle.close().catch(() => {})
    // 只删自己的锁：内容不是我们的 nonce（说明已被判陈旧抢走）就什么都不做
    const owner = await readFile(lock, 'utf8').catch(() => null)
    if (owner !== null && owner.trim() !== token) {
      warn('ks-dsh-plugin: 查法规模式状态锁已被他人接管（本进程不再干预）')
    } else if (owner !== null && !await unlinkWithRetry(lock)) {
      // 释放不掉（别人正抢占同一路径）：把 mtime 归零，下一位立刻可抢，不会白等
      const epoch = new Date(0)
      await utimes(lock, epoch, epoch).catch(() => {})
    }
  }
}

/**
 * 一轮落盘：**在跨进程锁内**读基线 → 合并 → 写唯一 tmp → 比对基线 → rename →
 * 回读校验。任何一步发现"别人抢先"就重来（≤PERSIST_ATTEMPTS 轮）；始终冲突就
 * 如实抛错（调用方记 persisted:false），绝不假装成功。
 * @returns {Promise<'ok' | 'retry'>}
 */
async function persistAttempt(snapshot, touched, cleared) {
  const file = chatModeFilePath()
  const baseline = await readStateFile() // 读错误会抛（调用方记为 persisted:false）
  const merged = new Map(baseline.modes)
  for (const sid of touched) {
    const mode = snapshot.get(sid)
    // 内存里没有**且用户显式关过** → 才是删除指令（"内存丢了"不等于"用户关了"）
    if (mode === undefined) {
      if (cleared.has(sid)) merged.delete(sid)
      continue
    }
    merged.set(sid, mode)
  }
  const text = JSON.stringify({ sessions: Object.fromEntries(merged) }, null, 2)
  const tmp = tmpPathFor(file)
  let renamed = false
  try {
    await writeFile(tmp, text, 'utf8')
    // CAS：写完 tmp 后目标文件必须仍是我们读到的基线，否则丢弃重算
    const current = await readFile(file, 'utf8').catch((error) => {
      if (error?.code === 'ENOENT') return null
      throw error
    })
    if (current !== baseline.text) return 'retry'
    await renameWithRetry(tmp, file)
    renamed = true
    // 回读校验（锁内 + 锁外的写者都可能覆盖我们，所以这是第二道防线）
    const verify = parseState(await readFile(file, 'utf8'))
    const lost = [...touched].some((sid) => {
      const want = snapshot.get(sid)
      const got = verify.modes.get(sid)
      if (want === undefined) return cleared.has(sid) ? got !== undefined : false
      return got === undefined || got.forensic !== want.forensic
        || got.bookmarksOnly !== want.bookmarksOnly
        || (got.folderId ?? null) !== (want.folderId ?? null)
        || (got.folderName ?? null) !== (want.folderName ?? null)
    })
    return lost ? 'retry' : 'ok'
  } finally {
    if (!renamed) await unlinkWithRetry(tmp)
  }
}

/** 带重试的落盘（每轮都在跨进程锁内）。 */
async function persistRound(snapshot, touched, cleared) {
  let lastReason = 'cas_conflict'
  for (let attempt = 0; attempt < PERSIST_ATTEMPTS; attempt += 1) {
    try {
      const outcome = await withStateLock(() => persistAttempt(snapshot, touched, cleared))
      if (outcome === 'ok') return
      lastReason = 'cas_lost'
    } catch (error) {
      lastReason = error instanceof Error ? error.message : String(error)
      if (lastReason !== 'state_lock_timeout') throw error
    }
  }
  throw new Error(lastReason)
}

/**
 * 串行落盘（后写覆盖先写）。每次落盘前**重读磁盘合并**：
 * - 磁盘上存在、但本进程没碰过的会话 → 保留（别的 dsh 进程写的）；
 * - 本进程写过的会话（`_touched`）→ 以本进程内存为准（值以内存为准）；
 * - 只有**显式关闭**过的会话（`_cleared`）才从磁盘删掉。
 * 成功且内存值未再变时**释放所有权**（否则会把别进程关掉的会话复活）。
 * @returns {Promise<{persisted: boolean, error?: string}>}
 */
function persist() {
  if (_writesBlocked) {
    return Promise.resolve({ persisted: false, error: _degraded ?? 'degraded' })
  }
  const snapshot = new Map(_modes)
  const touched = new Set(_touched)
  const cleared = new Set(_cleared)
  const round = _persistChain.then(async () => {
    await persistRound(snapshot, touched, cleared)
    // 这一轮成功了：清掉"上次操作有问题"的标记（`_degraded` 是**最近一次**状态改变的
    // 健康度，不是永久污点）
    _degraded = null
    // 释放所有权：只在"内存里没再改过这个会话"时
    for (const sid of touched) {
      const written = snapshot.get(sid)
      const live = _modes.get(sid)
      const same = written === undefined
        ? live === undefined
        : live !== undefined && live.forensic === written.forensic
          && live.bookmarksOnly === written.bookmarksOnly
          && (live.folderId ?? null) === (written.folderId ?? null)
          && (live.folderName ?? null) === (written.folderName ?? null)
      if (same) {
        _touched.delete(sid)
        if (written === undefined) _cleared.delete(sid) // 删除意图已落到盘上
      }
    }
  })
  // 串行链本身吞掉异常（否则一次失败会让后续所有落盘都被跳过），
  // 但**调用方拿到的是这一轮的真实结果**。
  _persistChain = round.catch(() => {})
  return round.then(() => ({ persisted: true })).catch((error) => {
    const reason = error instanceof Error ? error.message : String(error)
    // verifier 五轮 P2-1：**写**失败型降级也必须可见（旧实现只有**读**错误才置
    // degraded/writes_blocked，于是盘不可写时前端拿到 degraded:null/writes_blocked:false，
    // 显示"已保存"、重启却丢）。这里只置 degraded（不置 _writesBlocked——那会自锁成
    // "永远拒写"），前端以 degraded !== null 显示持续告警。
    _degraded = `persist_failed:${reason}`
    warn('ks-dsh-plugin: 查法规模式状态落盘失败（本次仅内存生效）', error)
    return { persisted: false, error: reason, degraded: _degraded }
  })
}

/**
 * 读某会话的开关（未开启 = 全关）。纯内存读——供提示词 provider 每次组装调用；
 * 若尚未加载过则顺手触发一次加载（provider 不能 await，首次可能读到"未开"）。
 */
export function getMode(sessionId) {
  const id = normalizeSessionId(sessionId)
  if (id.length === 0) return { ...MODE_OFF }
  if (_loaded === null) void ensureLoaded()
  return _modes.get(id) ?? { ...MODE_OFF }
}

/**
 * 写某会话的开关（部分更新）。
 *
 * folderId patch 语义（2026-10 收藏目录）：
 * - `folderId: 'bmf_…'` + `folderName: '收藏夹一'` → 开启夹内提问（forensic 自动 true）；
 * - `folderId: null` → 关闭夹范围。**显式传 null 才是关闭**；不传（undefined）= 不动该维度。
 * - 开启夹范围时保留 bookmarksOnly 原值（两个范围维度可叠加，引擎侧 folder 过滤
 *   在 bookmarks 过滤之后同链执行）；关闭夹范围只清 folderId，不动 forensic/bookmarksOnly。
 *
 * @returns {{mode: {forensic: boolean, bookmarksOnly: boolean, folderId: string|null, folderName: string|null}, persist: Promise<{persisted: boolean, error?: string}>}}
 */
export function setMode(sessionId, patch) {
  const id = normalizeSessionId(sessionId)
  if (id.length === 0) {
    throw new Error('session 必填且必须是不含空白的合法会话 id')
  }
  for (const key of ['forensic', 'bookmarksOnly']) {
    if (patch?.[key] !== undefined && typeof patch[key] !== 'boolean') {
      throw new Error(`${key} 必须是布尔值`)
    }
  }
  const patchFolderId = patch?.folderId === undefined ? undefined : normalizeFolderId(patch.folderId)
  if (patch?.folderId !== undefined && patch?.folderId !== null && patchFolderId === null) {
    throw new Error('folderId 必须是不含空白的合法收藏夹 id（bmf_…），或 null 表示关闭')
  }
  if (patchFolderId !== undefined && patchFolderId !== null
      && normalizeFolderName(patch?.folderName) === null) {
    throw new Error('开启夹范围时 folderName 必填（≤60 字符、非空白）')
  }
  const current = getMode(id)
  // folderId 维度：undefined = 不动；null = 显式关闭；字符串 = 开启
  const nextFolderId = patchFolderId === undefined ? current.folderId : patchFolderId
  const next = normalizeMode({
    forensic: patch?.forensic === undefined ? current.forensic : patch.forensic,
    bookmarksOnly: patch?.bookmarksOnly === undefined ? current.bookmarksOnly : patch.bookmarksOnly,
    folderId: nextFolderId,
    folderName: nextFolderId === null ? null
      : nextFolderId === current.folderId && patch?.folderName === undefined
        ? current.folderName
        : normalizeFolderName(patch?.folderName) ?? current.folderName,
  })
  if (next.forensic && !_modes.has(id) && _modes.size >= MAX_SESSIONS) {
    throw new Error(`开启查法规模式的会话已达上限（${MAX_SESSIONS}），请先关闭一些会话`)
  }
  if (next.forensic) {
    _modes.set(id, next)
    _cleared.delete(id)
  } else {
    _modes.delete(id)
    _cleared.add(id) // 显式关闭意图：合并落盘时才允许删掉磁盘上的这一条
  }
  _touched.add(id)
  return { mode: next, persist: persist() }
}

/**
 * 该会话**本轮实际生效**的开关——提示词层与工具层共用的唯一真值来源
 * （子会话继承在这里实现一次，避免"提示词说继承了、工具层没继承"的打脸组合）。
 * @param {string} sessionId
 * @param {{parentSessionOf?: (sessionId: string) => string | null, maxHops?: number}} [opts]
 * @returns {{forensic: boolean, bookmarksOnly: boolean, source: 'session'|'parent'|'none'}}
 */
export function effectiveChatMode(sessionId, opts = {}) {
  const id = normalizeSessionId(sessionId)
  if (id.length === 0) return { ...MODE_OFF, source: SOURCE_NONE }
  const own = getMode(id)
  if (own.forensic) return { ...own, source: 'session' }
  const parentOf = opts.parentSessionOf
  if (typeof parentOf !== 'function') return { ...MODE_OFF, source: SOURCE_NONE }
  const maxHops = Number.isInteger(opts.maxHops) && opts.maxHops > 0 ? opts.maxHops : 4
  let cursor = id
  for (let hop = 0; hop < maxHops; hop += 1) {
    let parent = null
    try {
      parent = parentOf(cursor)
    } catch {
      // 解析器不可用（agents 服务缺失/父会话已被回收）→ 静默不继承
      return { ...MODE_OFF, source: SOURCE_NONE }
    }
    const pid = normalizeSessionId(parent)
    if (pid.length === 0 || pid === cursor) return { ...MODE_OFF, source: SOURCE_NONE }
    const inherited = getMode(pid)
    if (inherited.forensic) return { ...inherited, source: 'parent' }
    cursor = pid
  }
  return { ...MODE_OFF, source: SOURCE_NONE }
}

/**
 * 该会话本轮应注入的取证提示（关 → 空串，什么都不注入）。
 * 这是 systemPrompt.section 的 text provider 本体——每次组装提示都会重新求值。
 * 附加段优先级：夹范围段 > 仅收藏段（夹范围是更具体的范围；两者同时开启时
 * 引擎侧 folder 过滤在 bookmarks 过滤之后执行，提示段只讲最具体的范围以免
 * 模型在两套范围话术间摇摆）。
 */
export function forensicPromptFor(sessionId, opts = {}) {
  const eff = effectiveChatMode(sessionId, opts)
  if (!eff.forensic) return ''
  let body = FORENSIC_PROMPT
  if (eff.folderId !== null && eff.folderId !== undefined) {
    body = `${body}\n${renderFolderPrompt(eff.folderName ?? '')}`
  } else if (eff.bookmarksOnly) {
    body = `${body}\n${FORENSIC_BOOKMARKS_PROMPT}`
  }
  return eff.source === 'parent'
    ? `${body}\n（本纪律继承自父会话的「查法规模式」设置。）`
    : body
}

/**
 * 构造 systemPrompt.section 的声明（纯数据，便于离线冒烟直接喂 AssembleContext）。
 * text provider 从 `context.agent.session.id` 取会话 id —— 与 plan-mode 的
 * `plan:policy` 同款姿势（根上下文注册一次，按 agent 动态求值）。
 * @param {{parentSessionOf?: (sessionId: string) => string | null}} [opts]
 */
export function makeChatModeSection(opts = {}) {
  return {
    name: FORENSIC_SECTION_NAME,
    order: FORENSIC_SECTION_ORDER,
    text: (context) => {
      const sessionId = context?.agent?.session?.id
      if (typeof sessionId !== 'string') return ''
      const header = context?.agent?.session?.header
      // 默认只做一跳（子会话 → 父会话）：从 agent 自身能拿到的只有 header.parentSession；
      // 更深层由 index.js 经 ctx.agents 注入的 resolver 解析。
      const parentSessionOf = opts.parentSessionOf
        ?? ((sid) => (sid === sessionId ? header?.parentSession ?? null : null))
      return forensicPromptFor(sessionId, { parentSessionOf })
    },
  }
}

/** 供测试：按给定的"现在"跑一次残骸清理（默认仍是 24h 门槛）。 */
export function __sweepArtifactsForTests(nowMs = Date.now()) {
  return sweepStaleArtifacts(nowMs)
}

/* ------------------------------------------------------------------ *
 * 斜杠命令（2026-09-10，用户反馈：输入框上方的按钮太丑 → 改成 / 调用）
 *
 * DSH 的命令名契约是 `^[a-z][a-z0-9_-]*$`（**只允许小写 ASCII**，中文名注册会抛），
 * 所以用 `/forensic` 与 `/bookmarks`；描述与回执文案用中文，在 `/` 面板里可发现。
 * 命令走 host 的 `ctx.commands`：不进模型、不产生对话消息，只在会话日志留
 * `command/run` + `command/done` 两个事件（DSH 自带），结果由 composer 直接渲染。
 * 状态仍然是会话级（`invocation.agent.session.id`），与提示段/工具层同一份真值。
 * ------------------------------------------------------------------ */

/** 「查法规模式」命令名。 */
export const FORENSIC_COMMAND = 'forensic'
/** 「仅收藏」命令名。 */
export const BOOKMARKS_COMMAND = 'bookmarks'

const COMMAND_USAGE = '用法：`/forensic`（切换）· `/forensic on|off` · `/forensic bookmarks on|off` · `/forensic status`'

/** 命令回执里的一句状态摘要。 */
function modeSummary(mode) {
  if (!mode.forensic) return '📜 查法规模式：**已关闭**（本会话）'
  const folder = mode.folderId != null
    ? ` · 📁 收藏夹「${mode.folderName ?? mode.folderId}」内提问：**已开启**`
    : ''
  if (mode.folderId != null) {
    return `📜 查法规模式：**已开启**${mode.bookmarksOnly ? ' · 🔖 仅收藏：**已开启**' : ''}${folder}（检索限定在收藏夹内容内，由 host 强制）`
  }
  return mode.bookmarksOnly
    ? '📜 查法规模式：**已开启** · 🔖 仅收藏：**已开启**（检索限定在你的收藏条款内，由 host 强制）'
    : '📜 查法规模式：**已开启**（涉法规/国标问题将强制走 ks_answer 取证链路：三段式 + 只引现行版 + 可点证据链接）'
}

/** 解析 `on|off`（中英文都收）。返回 true/false，无法识别返回 null。 */
function parseToggle(word) {
  const w = String(word ?? '').trim().toLowerCase()
  if (w === 'on' || w === '开' || w === '开启' || w === 'true' || w === '1') return true
  if (w === 'off' || w === '关' || w === '关闭' || w === 'false' || w === '0') return false
  return null
}

/** 写开关并落盘；返回给用户看的回执文本（落盘失败如实说明，但模式已生效）。 */
async function applyAndReport(sessionId, patch) {
  const result = setMode(sessionId, patch)
  const mode = result.mode
  const persist = await result.persist
  const tail = persist.persisted
    ? ''
    : `\n\n⚠️ 状态未能落盘（${persist.error ?? '未知原因'}）——本会话内已生效，但重启 dsh 后会丢失。`
  return { mode, text: modeSummary(mode) + tail }
}

/**
 * 构造两条会话级开关命令（纯数据 + handler，便于离线冒烟直接调 handler）。
 * @param {{parentSessionOf?: (sessionId: string) => string | null}} [opts]
 */
export function makeChatModeCommands(opts = {}) {
  const resolve = async (invocation) => {
    const sessionId = normalizeSessionId(invocation?.agent?.session?.id)
    if (sessionId.length === 0) {
      return { error: { kind: 'error', text: '无法确定当前会话 id，命令未执行。' } }
    }
    await ensureLoaded()
    return { sessionId }
  }

  const forensicHandler = async (invocation) => {
    const { sessionId, error } = await resolve(invocation)
    if (error !== undefined) return error
    const words = String(invocation?.rawInput ?? '').trim().split(/\s+/).filter((w) => w.length > 0)
    const head = words[0]?.toLowerCase()

    if (head === undefined) {
      const { mode, text } = await applyAndReport(sessionId, { forensic: !getMode(sessionId).forensic })
      return { kind: 'success', text }
    }
    if (head === 'status' || head === '状态') {
      const eff = effectiveChatMode(sessionId, opts)
      const scope = eff.source === 'parent' ? '（继承自父会话）' : ''
      return { kind: 'success', text: modeSummary(eff) + scope }
    }
    if (head === 'bookmarks' || head === '收藏') {
      const want = words[1] === undefined ? !getMode(sessionId).bookmarksOnly : parseToggle(words[1])
      if (want === null) return { kind: 'error', text: `无法识别 "${words[1]}"。${COMMAND_USAGE}` }
      // 仅收藏依附父开关：这里明确把它一起打开，并说明原因（而不是让用户困惑为什么没生效）
      const { text } = await applyAndReport(sessionId, want
        ? { forensic: true, bookmarksOnly: true }
        : { bookmarksOnly: false })
      return { kind: 'success', text: want ? `已同时开启查法规模式（仅收藏在其内生效）。\n\n${text}` : text }
    }
    const toggle = parseToggle(head)
    if (toggle === null) return { kind: 'error', text: `无法识别 "${words[0]}"。${COMMAND_USAGE}` }
    const { text } = await applyAndReport(sessionId, { forensic: toggle })
    return { kind: 'success', text }
  }

  const bookmarksHandler = async (invocation) => {
    const { sessionId, error } = await resolve(invocation)
    if (error !== undefined) return error
    const words = String(invocation?.rawInput ?? '').trim().split(/\s+/).filter((w) => w.length > 0)
    const want = words[0] === undefined ? !getMode(sessionId).bookmarksOnly : parseToggle(words[0])
    if (want === null) return { kind: 'error', text: `无法识别 "${words[0]}"。用法：\`/bookmarks\`（切换）· \`/bookmarks on|off\`` }
    const { text } = await applyAndReport(sessionId, want
      ? { forensic: true, bookmarksOnly: true }
      : { bookmarksOnly: false })
    return { kind: 'success', text: want ? `已同时开启查法规模式（仅收藏在其内生效）。\n\n${text}` : text }
  }

  return [
    {
      name: FORENSIC_COMMAND,
      description: '📜 查法规模式：本会话法规/国标问题强制走取证链路（三段式 + 只引现行版 + 可点证据链接）',
      input: { hint: 'on | off | bookmarks on|off | status' },
      handler: forensicHandler,
    },
    {
      name: BOOKMARKS_COMMAND,
      description: '🔖 仅收藏：检索只在你收藏的条款内进行（由 host 强制，自动开启查法规模式）',
      input: { hint: 'on | off' },
      handler: bookmarksHandler,
    },
  ]
}

/**
 * 把两条命令注册进 host 的命令表。返回 disposer 数组（cordis effect 会调用）。
 *
 * 兜底是**唯一一处**（不在调用方再包一层不可测的外层 try）：
 *   1. 服务解析在循环外一次做完：`ctx.commands` 缺失/不是预期形状 → 吼日志后返回空数组；
 *   2. 逐条注册各自 try：`ctx.commands.register` 会走 host 侧 normalizeDefinition 校验，
 *      校验不过**抛异常**——只让失败的那条不注册，其余照常。
 * 这两条合起来保证：一条命令定义的失误不会冒出 apply()，把整个宿主半边
 * （全部 /ks/* 路由、提示段、模型工具）一起带走。
 *
 * @param {{commands?: {register?: Function}}} ctx
 * @returns {Array<() => void>} 已成功注册命令的 disposer
 */
export function registerKsChatModeCommands(ctx, opts = {}) {
  const disposers = []
  const table = ctx?.commands
  if (typeof table?.register !== 'function') {
    console.error('[ks-dsh-plugin] 命令服务不可用（ctx.commands.register 不存在），斜杠命令未注册；'
      + '查法规模式本体不受影响（提示段与工具层仍生效）')
    return disposers
  }
  for (const definition of makeChatModeCommands(opts)) {
    try {
      disposers.push(table.register(definition))
    } catch (error) {
      console.error(`[ks-dsh-plugin] 斜杠命令 /${definition.name} 注册失败（其余命令与查法规模式不受影响）:`, error)
    }
  }
  return disposers
}

/** 供测试复位内存态（不含落盘）。 */
export function __resetChatModeForTests() {
  _modes = new Map()
  _touched = new Set()
  _cleared = new Set()
  _loaded = null
  _persistChain = Promise.resolve()
  _degraded = null
  _writesBlocked = false
}

/* ------------------------------------------------------------------ *
 * 路由（纯 host 状态，不经引擎；同源栅栏由 index.js 的 webCtx 统一施加）
 * ------------------------------------------------------------------ */

const BODY_CAP = 4_096

class BodyTooLargeError extends Error {}

function jsonResponse(res, status, body) {
  // 状态端点绝不缓存：避免浏览器/中间层把开关状态缓存成陈旧值
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  })
  res.end(JSON.stringify(body))
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    let done = false
    const fail = (err) => {
      if (done) return
      done = true
      reject(err)
    }
    req.on('data', (chunk) => {
      if (done) return
      size += chunk.length
      if (size > BODY_CAP) {
        // 不要把连接 destroy 掉再写响应（客户端只会拿到 socket 错误）；
        // 停止累积、交给上层回一个明确的 413。
        fail(new BodyTooLargeError('body_too_large'))
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (done) return
      done = true
      try {
        const text = Buffer.concat(chunks).toString('utf8')
        resolve(text.length === 0 ? {} : JSON.parse(text))
      } catch (err) {
        reject(err)
      }
    })
    req.on('error', fail)
  })
}

/**
 * 注册会话级开关路由。返回 disposer（cordis effect 会调用）。
 * @param {{webServer: {register: Function}, logger?: any}} ctx 已被信任栅栏包过的 host 上下文
 */
export function registerKsChatModeRoutes(ctx) {
  setChatModeLogger(ctx?.logger)
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_CHAT_MODE_PATH,
    handler: async (req, res) => {
      if (req.method === 'GET') {
        const sessionId = normalizeSessionId(
          new URL(req.url ?? '/', 'http://localhost').searchParams.get('session') ?? '')
        if (sessionId.length === 0) {
          jsonResponse(res, 400, { ok: false, error: { code: 'missing_session', message: 'session 必填（不含空白的合法会话 id）' } })
          return
        }
        // verifier 四轮 P2-G：GET 也要给降级一次自愈机会——否则"降级期开的开关"在本进程
        // 里可能永远不再尝试落盘（用户不再点开关 = 永不再 PUT），重启即丢。
        if (allowStateReload()) {
          await ensureLoaded()
          // 自愈那次的写**不阻塞读**（verifier 六轮 P2-3：await 会让一次状态查询等锁+落盘，
          // 实测持活跃锁时 5s、上限约 15s；而 GET 会被 visibilitychange/focus/切会话频繁触发）。
          // 可见性不受影响：写失败仍会在 persist() 里置 `_degraded`，**下一次** GET 就能回显。
          if (_modes.size > 0) void persist()
        } else {
          await ensureLoaded()
        }
        jsonResponse(res, 200, {
          ok: true,
          session: sessionId,
          mode: getMode(sessionId),
          state: stateStatus(),
        })
        return
      }
      if (req.method === 'PUT') {
        // 写路由强制 application/json（挡 HTML 表单类简单请求；栅栏外的第二道）
        if (!requireJsonBody(req, res)) return
        let body
        try {
          body = await readJsonBody(req)
        } catch (error) {
          if (error instanceof BodyTooLargeError) {
            jsonResponse(res, 413, { ok: false, error: { code: 'body_too_large', message: `请求体不得超过 ${BODY_CAP} 字节` } })
            return
          }
          jsonResponse(res, 400, { ok: false, error: { code: 'bad_request', message: 'body 必须是合法 JSON' } })
          return
        }
        const sessionId = normalizeSessionId(body?.session)
        if (sessionId.length === 0) {
          jsonResponse(res, 400, { ok: false, error: { code: 'missing_session', message: 'session 必填（不含空白的合法会话 id）' } })
          return
        }
        // 降级不是永久的：用户每点一次开关，都给一次"重新加载"的机会（瞬时占用自愈）
        allowStateReload()
        await ensureLoaded()
        let mode
        let persistResult
        try {
          const result = setMode(sessionId, body)
          mode = result.mode
          persistResult = await result.persist
        } catch (error) {
          jsonResponse(res, 400, {
            ok: false,
            error: { code: 'bad_request', message: error instanceof Error ? error.message : String(error) },
          })
          return
        }
        // 落盘失败/被拒不再伪装成"保存成功"：如实带上 persisted/degraded 供 client 告警
        jsonResponse(res, 200, {
          ok: true,
          session: sessionId,
          mode,
          persisted: persistResult.persisted,
          ...(persistResult.error === undefined ? {} : { persist_error: persistResult.error }),
          state: stateStatus(),
        })
        return
      }
      jsonResponse(res, 405, { ok: false, error: { code: 'method_not_allowed', message: 'GET or PUT' } })
    },
  })
}
