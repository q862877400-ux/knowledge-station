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
 * - 继承只在**父 agent 仍活跃**时成立（`ctx.get('agents').get(parent)` 解析父会话；冷父/已被
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

import { mkdir, open, readdir, readFile, rename, stat, unlink, utimes, writeFile } from 'node:fs/promises'
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

/**
 * 「参考资料项目」附加段（`materialProjectId` 生效时追加）。
 *
 * 与「收藏夹内提问」并列，但语义**不同**：夹范围是"只在收藏集里找"，
 * 材料范围是"**另加**一个平面的证据"。故这里不说"检索限定在"，而说"另附"。
 *
 * 措辞纪律（照抄 folder 段的分寸）：host 能证明的只是"**已强制传参**"
 * （`answer_scope.material` 回显），**不能**证明材料一定进了提示词——
 * 项目里可能一条已批准材料都没有。真值在引擎返回的 `notes` 与 `material_usage` 里。
 */
export const FORENSIC_MATERIALS_PROMPT = [
  '6. 【参考资料项目】本会话已由 host 强制给 `ks_answer` 传 `params.material_project_id`（项目「{PROJECT_NAME}」），`answer_scope.material` 回显的只是 **host 是否强制传参**，它**不能**证明材料真的进了提示词——项目里可能一条已批准材料都没有。',
  '材料会以「参考资料（**非法规证据**）」另起一节出现，引用它必须用 `[[m:i]]`（法条用 `[[c:i]]`，两套编号别混）。材料按**承重能力**分组，必须照组说话：标为**本任务准则（轴 B）**的对其自身事项**优先于法条**，冲突时要**显式说明冲突**而不是静默取舍；**仅作线索**的不得单独支撑结论（引用须写明「（单一来源，未经互证）」）；**已知不可用**的不得用于结论。',
  '判断这一轮到底用上了什么，看**机器字段**：`material_usage.counts` 是各组条数、`usable_indices` 是可承重材料的编号、`material_project_id` 是绑定的项目；`notes` 里的【参考资料】条目会说明命中几条、或"没有命中"、或"项目**不存在**"、或"材料**载入失败**"——**这四种必须如实区分**，绝不能在载入失败或项目不存在时说成"项目里没有材料"。',
  '**评审是硬门**：只有 `review_status` 为 `approved` 的材料会进来。若用户问「我上传的材料呢」，用 `ks_materials` 查 `review_status`（本工具只读，**不能代批**）——有 pending 就如实说「尚未评审、不会进入结论」，由用户决定。',
  '7. 【自采】你可以用 **`ks_collect`** 自己搜集材料（业主裁定：采集**默认开**）：先用你自己的检索找到**原始出处**的网址，再一条一条登记。三条必须照说：① 采到的默认是 **T3=仅线索**，**不得单独支撑结论**（引用要写明「单一来源，未经互证」）；② 登记后是 **pending**，**不会**进入本轮结论——要**如实告诉用户**并请他去评审；③ 你**不能**批准，也**不能**自己声明来源层级（轴 A 由系统起 T3，改动是用户的事）。若项目里已批准的材料不足，宁可如实说「证据不足」，不要用采来的线索硬撑。',
].join('\n')

function renderMaterialsPrompt(name) {
  const safe = String(name ?? '').replace(/}/g, '）').replace(/{/g, '（')
  return FORENSIC_MATERIALS_PROMPT.replaceAll('{PROJECT_NAME}', safe)
}

/* ------------------------------------------------------------------ *
 * 状态（进程单写者 + 合并落盘 + 原子替换 + CAS；结构漂移安全网）
 * ------------------------------------------------------------------ */

/**
 * 全关基线。三个**独立维度**：forensic / bookmarksOnly / 范围（folderId 与
 * materialProjectId 是同一类的"范围"维度，各自独立、可同时开）。
 *
 * - folderId 非空 → 夹内提问激活：host 强制给 ks_answer 传 folder_id，
 *   且自动蕴含查法规模式（夹范围 ⊃ 取证纪律——范围提问必然要求取证链路）。
 * - folderName 是 folderId 的显示名快照（host 不查引擎也能渲染提示段与回执；
 *   引擎侧真值永远是 folder_id，名字漂移只影响文案不影响范围）。
 * - **materialProjectId（2026-09-17 材料平面）** 同款：非空 → host 强制给 ks_answer 传
 *   `material_project_id`，于是本会话的问答会带上该项目的**已批准**参考资料
 *   （分组承重：准则/可作依据/互证辅证/仅线索/不可用）。同样自动蕴含查法规模式，
 *   理由同 folderId：材料只在 ks_answer 这条链上参与作答。
 *   `materialProjectName` 与 folderName 一样只是**显示快照**，引擎侧真值永远是 id。
 */
const MODE_OFF = {
  forensic: false, bookmarksOnly: false,
  folderId: null, folderName: null,
  materialProjectId: null, materialProjectName: null,
}
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

/**
 * materialProjectId 形态校验（2026-09-17）：引擎 ULID 形（`prj_…`）。
 *
 * ⚠ 与 folderId **分开**校验而不是共用一个 normalizeId：两者的前缀语义不同，
 * 且**必须能报错**（用户把收藏夹 id 当项目 id 传时要看得见，而不是静默不生效）。
 * 这里只做"形态合法"判定，前缀检查放在调用方（见 setMode 的报错）——
 * 本函数只回答"像不像一个 id"。
 */
function normalizeMaterialProjectId(raw) {
  if (raw === null || raw === undefined || raw === false) return null
  const id = String(raw).trim()
  if (id.length === 0 || id.length > 64) return null
  // eslint-disable-next-line no-control-regex
  if (/[\s\u0000-\u001f]/.test(id)) return null
  return id
}

function normalizeMaterialProjectName(raw) {
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
/**
 * **粘住**"当初为什么拒写"（2026-09-20，查一条真实偶发时补）。
 *
 * `_degraded` 是"**最近一次**改变健康度"的标记，会被一次**成功**落盘清成 `null`
 * （见 `persist()` 里那句"清掉上次操作有问题的标记"）。于是出现过这种最难查的组合：
 * `_writesBlocked === true`（仍在拒写）而 `_degraded === null` ⇒ `persist()` 如实返回
 * `persisted:false`，但 `error` 只能给一个**没有信息量**的 `'degraded'`，
 * 运维/冒烟都看不出"是为什么拒写的"（读失败？哪个 errno？）。
 * `_blockedReason` 只在"拒写"被建立时写入，**不随成功落盘清掉**，只由
 * `allowStateReload()` / `__resetChatModeForTests()`（即"重新建立可信度"的两个入口）清。
 */
let _blockedReason = null
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

/**
 * 拒写时出声（2026-09-20）。**没有 logger 时退化成 `console.warn`** —— 这条路径说的是
 * "从现在起所有状态都不落盘"，属于必须留下的现场；以前它只改内存标记、一个字都不打。
 */
function blockWarn(reason, file) {
  if (_logger?.warn) warn(`ks-dsh-plugin: 状态文件不可信 ⇒ 拒绝写盘（${reason}）`, file)
  else {
    try { console.warn(`ks-dsh-plugin: 状态文件不可信 ⇒ 拒绝写盘（${reason}）`, file) } catch { /* 同上 */ }
  }
}

function normalizeMode(raw) {
  const forensic = raw?.forensic === true
  const folderId = normalizeFolderId(raw?.folderId)
  const materialProjectId = normalizeMaterialProjectId(raw?.materialProjectId)
  // 仅收藏依附于查法规模式：父开关关闭时自动降级（决策 16）。
  // 任一**范围**维度非空时 forensic 强制为 true——这两个范围都只在 ks_answer 这条链上
  // 生效（材料靠 host 强制传 material_project_id），范围提问的答案必须带三段式与证据链接。
  const scoped = folderId !== null || materialProjectId !== null
  return {
    forensic: forensic || scoped,
    bookmarksOnly: (forensic || scoped) && raw?.bookmarksOnly === true,
    folderId,
    folderName: folderId === null ? null : normalizeFolderName(raw?.folderName),
    materialProjectId,
    materialProjectName: materialProjectId === null
      ? null : normalizeMaterialProjectName(raw?.materialProjectName),
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
    _blockedReason = reason
    // ⚠ 出声（2026-09-20 补）：这条路径原来**一声不吭**就把写盘关掉了 —— 只改内存标记，
    //   现场只剩一个 `persisted:false`，连"是读失败还是锁超时"都分不出来。
    blockWarn(reason, file)
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
      _blockedReason = reason
      blockWarn(reason, file)
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
  _blockedReason = null        // 重新建立可信度 ⇒ 旧的"为什么拒写"也该退休
  return true
}

/** 当前状态健康度（随路由回显，便于用户/审计自证）。 */
export function stateStatus() {
  // health 是给客户端用的**分类**（verifier 六轮 P2-4：把读失败/写失败/损坏重置压进
  // 一个布尔会让"损坏已备份"被显示成"写不进盘"）。degraded 仍是原始原因串，便于排障。
  // ⚠ `blocked_reason`：`degraded` 会被一次成功落盘清成 null，而"仍在拒写"这件事没被清
  //   ⇒ 只报 `degraded:null, writes_blocked:true` 时看不出原因（2026-09-20 补，见 `_blockedReason`）。
  let health = 'ok'
  if (_writesBlocked) health = 'read_blocked'
  else if (_degraded === 'corrupt_state_file') health = 'corrupt_reset'
  else if (typeof _degraded === 'string') health = 'write_failed'
  return { health, degraded: _degraded, writes_blocked: _writesBlocked,
    blocked_reason: _writesBlocked ? _blockedReason : null, sessions: _modes.size }
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
        || (got.materialProjectId ?? null) !== (want.materialProjectId ?? null)
        || (got.materialProjectName ?? null) !== (want.materialProjectName ?? null)
    })
    // ⚠ **第二道防线原来只看了 `touched`**（2026-09-20 复核打回后补）：
    //   一个**不持锁**的写者（老版本 / 别的工具 / 测试里那支"另一个进程"）如果把它的会话
    //   落在**我们的 CAS 读（:673 `readFile`）与 rename（:678）之间**，我们就会用**旧基线**合并、
    //   把它的会话整条覆盖掉 —— 而回读校验只看 `touched`，于是判 `'ok'`：**静默丢掉别人的状态**。
    //   实测：独立复核在冻结提交上跑 100 次冒烟红 2 次，红的正是"merge keeps the other process's
    //   sessions" ⇒ 这条窗口是真的、且会随机把 `-Full` 判红。
    //   ⇒ 现在把**基线里存在、我们没打算删、回读却没了**的会话也算"丢了"，返回 `'retry'`
    //     （重试会重新读基线，自然把对方那条合并回来）。
    const lostPeer = [...baseline.modes.keys()].some((sid) => {
      if (cleared.has(sid)) return false   // 我们本来就要删它
      if (touched.has(sid)) return false   // 归我们管，上面的 `lost` 已经覆盖
      return verify.modes.get(sid) === undefined
    })
    return (lost || lostPeer) ? 'retry' : 'ok'
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
    // ⚠ `error` 原来只会给 `'degraded'` —— 而 `_degraded` 可能已被一次**成功**落盘清成 null
    //   （见 `_blockedReason` 的注释）⇒ 现场看不出原因。现在把"粘住的拒写原因"带上。
    const reason = _degraded ?? (_blockedReason ? `writes_blocked:${_blockedReason}` : 'degraded')
    return Promise.resolve({ persisted: false, error: reason, blocked_reason: _blockedReason })
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
 * `materialProjectId` patch 语义（2026-09-17 材料平面）**完全同款**：
 * - `materialProjectId: 'prj_…'` + `materialProjectName: '财报分析'` → 绑定项目（forensic 自动 true）；
 * - `materialProjectId: null` → 解绑；不传 = 不动该维度。
 * - ⚠ id **必须**以 `prj_` 开头，否则**抛错**：把收藏夹 id 当项目 id 传时若静默通过，
 *   结果是"开着但永不生效"，而用户会以为材料已经参与作答了（最坏的一种）。
 *
 * @returns {{mode: {forensic: boolean, bookmarksOnly: boolean, folderId: string|null, folderName: string|null, materialProjectId: string|null, materialProjectName: string|null}, persist: Promise<{persisted: boolean, error?: string}>}}
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
  // materialProjectId 维度：与 folderId 同款语义（undefined=不动 / null=关闭 / 字符串=开启）。
  // ⚠ 前缀**必须**校验并报错：用户把收藏夹 id（bmf_…）当项目 id 传时，
  // 静默"开着但永不生效"是最坏的结果（他会以为材料已经参与作答了）。
  const patchMatId = patch?.materialProjectId === undefined
    ? undefined : normalizeMaterialProjectId(patch.materialProjectId)
  if (patch?.materialProjectId !== undefined && patch?.materialProjectId !== null
      && patchMatId === null) {
    throw new Error('materialProjectId 必须是不含空白的合法项目 id（prj_…），或 null 表示关闭')
  }
  if (patchMatId !== undefined && patchMatId !== null && !patchMatId.startsWith('prj_')) {
    throw new Error(`materialProjectId 必须以 prj_ 开头（收到 ${JSON.stringify(patchMatId)}）`
      + '——收藏夹 id（bmf_…）不是项目 id，项目 id 可用 ks_materials 的 projects 查到')
  }
  const patchMatName = patch?.materialProjectName === undefined
    ? undefined : normalizeMaterialProjectName(patch.materialProjectName)
  if (patchMatId !== undefined && patchMatId !== null && patchMatName === undefined
      && normalizeMaterialProjectName(patch?.materialProjectName) === null
      && getMode(id).materialProjectId !== patchMatId) {
    // 名字只是显示快照，但**换了项目却没给名字**会让回执与提示段显示旧项目的名字
    // ⇒ 宁可要求给名字（调用方总能拿到：ks_materials projects 里有 name）。
    throw new Error('开启材料范围时 materialProjectName 必填（≤60 字符、非空白）')
  }
  const current = getMode(id)
  // folderId 维度：undefined = 不动；null = 显式关闭；字符串 = 开启
  const nextFolderId = patchFolderId === undefined ? current.folderId : patchFolderId
  const nextMatId = patchMatId === undefined ? current.materialProjectId : patchMatId
  const next = normalizeMode({
    forensic: patch?.forensic === undefined ? current.forensic : patch.forensic,
    bookmarksOnly: patch?.bookmarksOnly === undefined ? current.bookmarksOnly : patch.bookmarksOnly,
    folderId: nextFolderId,
    folderName: nextFolderId === null ? null
      : nextFolderId === current.folderId && patch?.folderName === undefined
        ? current.folderName
        : normalizeFolderName(patch?.folderName) ?? current.folderName,
    materialProjectId: nextMatId,
    materialProjectName: nextMatId === null ? null
      : nextMatId === current.materialProjectId && patch?.materialProjectName === undefined
        ? current.materialProjectName
        : normalizeMaterialProjectName(patch?.materialProjectName) ?? current.materialProjectName,
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
 *
 * 「范围」附加段的选择（2026-09-17 加入材料范围后明确）：
 * - 夹范围段（folderId）与仅收藏段是**互斥**的：夹范围更具体，两者同开时只讲最具体的，
 *   免得模型在两套范围话术间摇摆（引擎侧两个过滤仍都执行）。
 * - 材料段（materialProjectId）**可以与上面任一段并存**，因为它不是"缩小检索范围"，
 *   而是"**另加一个证据平面**"——语义不同，所以不是 else-if，而是独立追加。
 *   这也意味着用户同时开夹范围与材料时会看到两个附加段，那是**如实**的。
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
  if (eff.materialProjectId !== null && eff.materialProjectId !== undefined) {
    body = `${body}\n${renderMaterialsPrompt(eff.materialProjectName ?? '')}`
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
      // 更深层由 index.js 经 ctx.get('agents') 注入的 resolver 解析。
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
 * 所以用 `/forensic` / `/bookmarks` / `/materials`；描述与回执文案用中文，在 `/` 面板里可发现。
 * 命令走 host 的 `ctx.commands`：不进模型、不产生对话消息，只在会话日志留
 * `command/run` + `command/done` 两个事件（DSH 自带），结果由 composer 直接渲染。
 * 状态仍然是会话级（`invocation.agent.session.id`），与提示段/工具层同一份真值。
 * ------------------------------------------------------------------ */

/** 「查法规模式」命令名。 */
export const FORENSIC_COMMAND = 'forensic'
/** 「仅收藏」命令名。 */
export const BOOKMARKS_COMMAND = 'bookmarks'
/** 「参考资料项目」命令名（2026-09-17 材料平面）。 */
export const MATERIALS_COMMAND = 'materials'

const COMMAND_USAGE = '用法：`/forensic`（切换）· `/forensic on|off` · `/forensic bookmarks on|off` · `/forensic status`'
const MATERIALS_USAGE = '用法：`/materials`（看当前绑定）· `/materials use <prj_id>` · `/materials off` · `/materials status`'

/** 命令回执里的一句状态摘要。 */
function modeSummary(mode) {
  if (!mode.forensic) return '📜 查法规模式：**已关闭**（本会话）'
  const folder = mode.folderId != null
    ? ` · 📁 收藏夹「${mode.folderName ?? mode.folderId}」内提问：**已开启**`
    : ''
  const mat = mode.materialProjectId != null
    ? ` · 📚 参考资料项目「${mode.materialProjectName ?? mode.materialProjectId}」：**已绑定**`
    : ''
  if (mode.folderId != null) {
    return `📜 查法规模式：**已开启**${mode.bookmarksOnly ? ' · 🔖 仅收藏：**已开启**' : ''}${folder}${mat}（检索限定在收藏夹内容内，由 host 强制）`
  }
  if (mode.materialProjectId != null) {
    return `📜 查法规模式：**已开启**${mode.bookmarksOnly ? ' · 🔖 仅收藏：**已开启**' : ''}${mat}`
      + '（本项目**已批准**的参考资料会随作答送入，按承重能力分组：准则/可作依据/互证辅证/仅线索/不可用）'
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

  /**
   * `/materials` —— 绑定/解绑本会话的参考资料项目（**用户**动作）。
   *
   * 为什么这条命令是**必要的**：引擎侧要按 `params.material_project_id` 用材料，
   * 但那个参数一直只能由模型猜或用户手抄 id。宿主绑定（见 index.js 的 makeAnswerTool）
   * 需要一个**会话级真值**，而唯一能可靠设置它的入口就是用户自己——故做成命令。
   *
   * 为什么**不**在这里做批准/拒绝：那是评审，是用户的判断（方案 §6 硬门）。
   * 命令只负责"用哪个项目"，不代替"批不批这份材料"。
   */
  const materialsHandler = async (invocation) => {
    const { sessionId, error } = await resolve(invocation)
    if (error !== undefined) return error
    const words = String(invocation?.rawInput ?? '').trim().split(/\s+/).filter((w) => w.length > 0)
    const head = words[0]?.toLowerCase()

    if (head === undefined || head === 'status' || head === '状态') {
      const eff = effectiveChatMode(sessionId, opts)
      if (eff.materialProjectId == null) {
        return { kind: 'success', text: '📚 参考资料项目：**未绑定**（本会话的问答不会使用任何项目材料）\n'
          + `用 \`/materials use <prj_id>\` 绑定。项目 id 与项目名可用 ks_materials（action=projects）查。` }
      }
      const scope = eff.source === 'parent' ? '（继承自父会话）' : ''
      return { kind: 'success', text: `📚 参考资料项目：**已绑定**「${eff.materialProjectName ?? eff.materialProjectId}」`
        + `（\`${eff.materialProjectId}\`）${scope}` }
    }
    if (head === 'off' || head === '关' || head === '关闭' || head === 'none' || head === '清空') {
      const { text } = await applyAndReport(sessionId, { materialProjectId: null })
      return { kind: 'success', text: `已解绑参考资料项目。\n\n${text}` }
    }
    if (head === 'use' || head === '用' || head === '绑定') {
      const id = words[1]
      if (id === undefined) return { kind: 'error', text: `缺少项目 id。${MATERIALS_USAGE}` }
      // 名字：`/materials use prj_x 财报分析` —— 名字只是显示快照，但换项目时必须给，
      // 否则回执/提示段会显示**上一个项目**的名字（见 setMode 的同款校验）。
      const name = words.slice(2).join(' ').trim()
      try {
        const { text } = await applyAndReport(sessionId, {
          materialProjectId: id,
          materialProjectName: name.length > 0 ? name : id,
        })
        return { kind: 'success', text: `已绑定参考资料项目。\n\n${text}` }
      } catch (e) {
        return { kind: 'error', text: `${e instanceof Error ? e.message : String(e)}\n\n${MATERIALS_USAGE}` }
      }
    }
    return { kind: 'error', text: `无法识别 "${words[0]}"。${MATERIALS_USAGE}` }
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
    {
      name: MATERIALS_COMMAND,
      description: '📚 参考资料项目：绑定某项目后，本会话问答会带上它**已批准**的材料'
        + '（按承重能力分组；仅线索/不可用两组不会支撑结论）',
      input: { hint: 'use <prj_id> [项目名] | off | status' },
      handler: materialsHandler,
    },
  ]
}

/**
 * 把两条命令注册进 host 的命令表。返回 disposer 数组（cordis effect 会调用）。
 *
 * 兜底是**唯一一处**（不在调用方再包一层不可测的外层 try）：
 *   1. 服务解析在循环外一次做完：`ctx.get('commands')` 缺失/不是预期形状 → 吼日志后返回空数组；
 *   2. 逐条注册各自 try：`commands.register` 会走 host 侧 normalizeDefinition 校验，
 *      校验不过**抛异常**——只让失败的那条不注册，其余照常。
 * 这两条合起来保证：一条命令定义的失误不会冒出 apply()，把整个宿主半边
 * （全部 /ks/* 路由、提示段、模型工具）一起带走。
 *
 * ⚠ `ctx.get('commands')`（不是 `ctx.commands`）：`commands` 已从 `inject` 移出
 * （复核 2026-09-19：它留在 inject 里，导致"真缺服务"时插件永远 PENDING、
 * 而这里这层兜底**永远够不着**）。官方 postmortem 的口径也是 use `ctx.get(name)`。
 *
 * @param {{get?: (name: string) => any}} ctx
 * @returns {Array<() => void>} 已成功注册命令的 disposer
 */
export function registerKsChatModeCommands(ctx, opts = {}) {
  const disposers = []
  const table = typeof ctx?.get === 'function' ? ctx.get('commands') : undefined
  if (typeof table?.register !== 'function') {
    console.error('[ks-dsh-plugin] 命令服务不可用（ctx.get("commands") 里没有 register），斜杠命令未注册；'
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
export function __resetChatModeForTests() {  _modes = new Map()
  _touched = new Set()
  _cleared = new Set()
  _loaded = null
  _persistChain = Promise.resolve()
  _degraded = null
  _writesBlocked = false
  _blockedReason = null
}

/**
 * **仅供测试**：像"另一个 dsh 进程"那样把给定的 JSON 文本写进状态文件，**并且持跨进程锁**。
 *
 * 为什么必须由模块提供（而不是测试自己 tmp+rename 一下）：
 *   真实的对端写者走的就是**同一套协议**（`withStateLock` → 读基线 → 写 tmp → rename）。
 *   测试如果自己原子写但**不持锁**，就会落在我们的 CAS 读与 rename 之间 ⇒ 被我们用旧基线
 *   合并覆盖（或反过来），表现为"另一个进程的会话偶发消失"。**协议只有一个所有者**（本模块），
 *   所以桩也得走它 —— 别在测试里复刻一份锁协议（复刻等于第二个所有者，改一边就漂）。
 *   2026-09-20：独立复核在冻结提交上 100 次跑红 2 次（`merge keeps the other process's sessions`），
 *   就是这条不持锁的写者。
 * @param {string} jsonText 要落盘的完整状态文件文本
 */
export async function __writeStateFileAsPeerForTests(jsonText) {
  const file = chatModeFilePath()
  await mkdir(dirname(file), { recursive: true })
  await withStateLock(async () => {
    const tmp = tmpPathFor(file)
    try {
      await writeFile(tmp, jsonText, 'utf8')
      await renameWithRetry(tmp, file)
    } finally {
      await unlinkWithRetry(tmp)
    }
  })
}

const BODY_CAP = 4_096

/* ------------------------------------------------------------------ *
 * 路由（纯 host 状态，不经引擎；同源栅栏由 index.js 的 webCtx 统一施加）
 * ------------------------------------------------------------------ */

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
