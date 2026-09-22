/**
 * ks-dsh-plugin — src/turn.js  （S1-b 宿主半批，2026-09-22）
 *
 * 「本轮」依据的**暂存 + 只读口**（`design-S1-turn-data-mapping.md` §二）：
 *   · `recordKsTurn(sessionId, payload)` —— `ks_answer` 成功返回前调用，按会话存**最近一次**；
 *   · `GET /ks/turn/last?session=…` —— 「本轮」tab 的取数口。
 *
 * 为什么在宿主侧：对话里的取证答案走**工具通道**，客户端面板看不见工具返回
 * （S1 设计修正——原稿"纯前端"不成立）⇒ 宿主在返回前顺手暂存一份给面板读。
 *
 * ⚠ 路由是 **exact、无尾斜杠**：channels/announce 那次"维护按钮整排死"的教训
 * （真派发器前缀判据 `pathname === prefix || startsWith(prefix + '/')`，带尾斜杠全部落兜底）。
 *
 * 边界（如实登记）：纯内存（插件重载 = 清空，「本轮」如实回空态）；每会话只留最近 1 次；
 * 会话数上限 32（本地单用户工具，超了丢最旧）。暂存的是**引擎原始公开字段**——
 * trim 层只留 4 个字段是给模型省 token 的，面板要的是 doc_id/rev/page/效力/摘要全量。
 */
import { errorBody, jsonResponse } from './route_util.js'

/** 只读口（exact；⚠ 不许加尾斜杠）。 */
export const KS_TURN_LAST_PATH = '/ks/turn/last'

const turns = new Map() // session -> { at, seq, session, turn }
const MAX_SESSIONS = 32
// 单调序号：同一毫秒记两条时时间戳会打平（实测踩到：全局最近取错）——序号裁决，时间戳只作显示。
let seqCounter = 0

/** 暂存一次「本轮」结果（幂等：同一会话后写覆盖先写）。 */
export function recordKsTurn(sessionId, payload) {
  const key = typeof sessionId === 'string' && sessionId.length > 0 ? sessionId : '(none)'
  turns.delete(key) // 保持"最近一次"在 Map 尾部，淘汰时从头部摘
  turns.set(key, { at: new Date().toISOString(), seq: ++seqCounter, session: key, turn: payload })
  while (turns.size > MAX_SESSIONS) {
    const oldest = turns.keys().next().value
    if (oldest === undefined) break
    turns.delete(oldest)
  }
}

/** 「本轮」只读路由（GET /ks/turn/last；?session= 缺省 = 全局最近一次）。 */
export function registerKsTurnRoutes(ctx) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_TURN_LAST_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const wanted = new URL(req.url || '/', 'http://localhost').searchParams.get('session')
      let entry = null
      if (wanted !== null && wanted !== '') {
        entry = turns.get(wanted) ?? null
      } else {
        // 不带 session = 全局最近一次（单用户工具的"刚才那轮"）；回执**带 session**，
        // 多会话混用时面板能看出它读的是谁的那轮。
        for (const v of turns.values()) {
          if (entry === null || v.seq > entry.seq) entry = v
        }
      }
      jsonResponse(res, 200, { ok: true, data: entry })
    },
  })
}
