/**
 * ks-dsh-plugin — src/route_util.js
 *
 * host 侧 `/ks/*` 路由的**共用小工具**：JSON 响应、错误体、带上限的请求体读取、
 * query 白名单清洗、引擎探测结果映射。
 *
 * ## 为什么要有这个文件（以及为什么现在只有两个模块用它）
 * 2026-09-17 查了一遍，并把**计数核准**（独立复核复核过一遍，见下）：
 *   · `jsonResponse` / `readJsonBody` 私有拷贝在 **5 个模块**里
 *     （announce / chatmode / ingest / inspection / settings；report 已切走）；
 *   · `errorBody` 只在 **4 个**里（announce / ingest / inspection / settings）
 *     —— **chatmode 没有它**；
 *   · `BODY_CAP` 有 **3 个**取值（4096 chatmode / 16384 settings / 65536 其余）。
 *   · 另外 `trust.js` 有一个**同名但不同形状**的 `jsonResponse(res,status,code,message)`，
 *     不算拷贝。
 * 那是历史积累，一次性合并风险大于收益（每个 cap 都是当场选的）。
 *
 * 本模块的做法是**只把新代码统一到这里**：
 *   · 新模块（materials_routes.js）从这里取；
 *   · 顺手把**最接近的一份**（report.js，同 cap=65536、helpers 逐字相同）切过来，
 *     让这里不是一个"只有一个用户的假共享模块"。
 *   · 其余 **5 个**模块**仍带各自私有拷贝**，**未合并**——这是**登记在案的遗留**
 *     （见 DEVELOPMENT-HISTORY §10.18），不是"我忘了"。
 *   · 复核确认：那 5 份的 `end` 分支都直接用 `reject(err)`，**没有**本模块 §10.21
 *     修掉的那个"永不 settle"缺陷。
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
 *
 * ⚠ **只有一个出口**（`settle`）：本函数第一版让 `end` 回调自己 `done = true`，
 * 再把解析异常交给 `fail()` —— 而 `fail()` 见 `done` 已置位就**直接 return**，
 * 于是 promise **永不 settle**：畸形 JSON 会让请求永久挂住（独立复核 P0，实测
 * 连 `/ks/report/export` 这种既有路由都被打挂，客户端只能超时）。
 * 现在**任何**settle 都走同一个 `settle(fn, arg)`，先判重入再置位，
 * "置了位又走另一条路"这种顺序错误在结构上不可能再发生。
 */
export function readJsonBody(req, cap = ROUTE_BODY_CAP) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    let done = false
    /** 唯一出口：第一次调用生效，之后是 no-op。 */
    const settle = (fn, arg) => {
      if (done) return
      done = true
      fn(arg)
    }
    req.on('data', (chunk) => {
      if (done) return
      size += chunk.length
      if (size > cap) {
        settle(reject, new Error('request body too large'))
        // ⚠ **不要 `req.destroy()`**（独立复核 2026-09-17 实测的 INFO；`chatmode.js` 里
        // 也有同样的告诫）：destroy 会**重置连接**，调用方随后写的 400 送不到客户端
        // —— 调用者看到的是"连接被重置"，而不是"请求体太大"这条可读的错误。
        // 改成 `resume()`：剩余数据**读掉但不用**，连接保住，400 能发出去。
        req.resume()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (done) return
      try {
        const text = Buffer.concat(chunks).toString('utf8')
        settle(resolve, text.length === 0 ? {} : JSON.parse(text))
      } catch (err) {
        // **直接** settle 成 reject（不要再绕一个会自行判重入的 helper——
        // 那正是本函数第一版挂死的原因）
        settle(reject, err instanceof Error ? err : new Error(String(err)))
      }
    })
    req.on('error', (err) => settle(reject, err))
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
 *
 * ⚠ **404 原样透传**（2026-09-17 补）：引擎的 404 是"你要的东西不存在"
 * （项目/材料 id 写错了），把它翻成 `502 engine_error` 是**归因错误**——
 * 用户看到"引擎错误"会去查引擎，而真正的原因是他给了一个不存在的 id。
 * 与 `docimage` 那条路由的既有约定一致（引擎 404 → 404）。
 *
 * ⚠ **影响面要说清**（2026-09-17 复核 b7 的 LOW-4）：这是**共享**的映射器，
 * 因此这条改动**不是**只作用于当时那条材料路由——`materials_routes.js`、
 * `report.js`、`settings.js` 等**所有**用 `mapProbe` 的路由一起变了：
 * **凡是引擎回 404 的，主机现在也回 404**（以前是 502）。
 * 这是**有意的全局口径**（"目标不存在"不是"引擎坏了"），但当时没写出来 ⇒ 现在写上。
 * 若要回到旧行为，只能在**调用点**决定（别把共享映射器改成分支开关）。
 */
export function mapProbe(res, probe, engineErrorStatus = 502, pick = null) {
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    const data = pick === null ? (probe.body.data ?? {}) : pick(probe.body)
    jsonResponse(res, 200, { ok: true, data })
    return
  }
  const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
  const message = probe.body && typeof probe.body === 'object' && probe.body.message
    ? String(probe.body.message) : ''
  if (probe.status === 404) {
    jsonResponse(res, 404, errorBody(typeof code === 'string' ? code : 'not_found',
      message || '目标不存在'))
    return
  }
  if (probe.status === 422) {
    jsonResponse(res, 400, errorBody(typeof code === 'string' ? code : 'invalid_params',
      message || '非法参数'))
    return
  }
  jsonResponse(res, engineErrorStatus, errorBody('engine_error',
    `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}`))
}
