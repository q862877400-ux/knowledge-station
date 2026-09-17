/**
 * ks-dsh-plugin — src/route_util.js
 *
 * host 侧 `/ks/*` 路由的**共用小工具**：JSON 响应、错误体、带上限的请求体读取、
 * query 白名单清洗、引擎探测结果映射。
 *
 * ## 为什么要有这个文件（以及为什么现在只有两个模块用它）
 * 2026-09-17 查了一遍：`jsonResponse` / `errorBody` / `readJsonBody` 在
 * **6 个模块**里各有一份私有拷贝（announce / chatmode / ingest / inspection /
 * report / settings），且 `BODY_CAP` 有 **3 个不同取值**（4096 / 16384 / 65536）。
 * 那是历史积累，一次性合并风险大于收益（每个 cap 都是当场选的）。
 *
 * 本模块的做法是**只把新代码统一到这里**：
 *   · 新模块（materials_routes.js）从这里取；
 *   · 顺手把**最接近的一份**（report.js，同 cap=65536、helpers 逐字相同）切过来，
 *     让这里不是一个"只有一个用户的假共享模块"。
 *   · 其余 4 个模块（announce/chatmode/ingest/inspection/settings）**仍带各自私有拷贝**，
 *     **未合并**——这是**登记在案的遗留**（见 DEVELOPMENT-HISTORY §10.18），
 *     不是"我忘了"。
 *
 * 依赖面：只用 node 内建 + 无 cordis（与 engine.js 同款，便于离线冒烟）。
 */

/** 请求体上限（与 report.js 一致；别的模块取值不同，故本模块不替它们决定）。 */
export const ROUTE_BODY_CAP = 65_536

/** 统一的 JSON 响应。 */
export function jsonResponse(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(body))
}

/** 统一的错误体形状（client 两个半边都按 `{ok:false,error:{code,message}}` 判）。 */
export function errorBody(code, message) {
  return { ok: false, error: { code, message } }
}

/**
 * 读请求体并解析 JSON（带大小上限；超限即销毁连接并在 promise 上拒绝）。
 * `cap` 显式传入而不吃模块常量——不同路由的合理上限不同。
 */
export function readJsonBody(req, cap = ROUTE_BODY_CAP) {
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
      if (size > cap) {
        fail(new Error('request body too large'))
        req.destroy()
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
        fail(err instanceof Error ? err : new Error(String(err)))
      }
    })
    req.on('error', fail)
  })
}

/**
 * query 白名单清洗：只保留允许键且值非空（未知键丢弃，防透传面扩大）。
 *
 * 用 `URLSearchParams` 解析——标准语义会把 `+` 还原为空格。真机回归教训（report.js
 * 原注释）：旧实现 `decodeURIComponent` 不还原 `+`，而 client 的 URLSearchParams 把
 * 空格编码为 `+`，含空格的类目名到引擎变成 `C+医药…`、精确匹配落空。
 */
export function pickQuery(reqUrl, allowed) {
  const out = {}
  const qs = (reqUrl || '').split('?')[1]
  if (!qs) return out
  for (const [k, v] of new URLSearchParams(qs).entries()) {
    if (allowed.includes(k) && v !== '') out[k] = v
  }
  return out
}

/**
 * 引擎 GET 探测结果 → 同源响应统一映射（401 自愈在调用方的重试里做）。
 *
 * `okData` 可给定一个"取哪些字段"的函数（默认 `body.data ?? {}`）：
 * 材料路由有些端点返回数组，直接透传更省事。
 */
export function mapProbe(res, probe, engineErrorStatus = 502, pick = null) {
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    const data = pick === null ? (probe.body.data ?? {}) : pick(probe.body)
    jsonResponse(res, 200, { ok: true, data })
    return
  }
  if (probe.status === 422) {
    const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
    const message = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message) : '非法参数'
    jsonResponse(res, 400, errorBody(typeof code === 'string' ? code : 'invalid_params', message))
    return
  }
  jsonResponse(res, engineErrorStatus, errorBody('engine_error',
    `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}`))
}
