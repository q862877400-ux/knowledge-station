/**
 * ks-dsh-plugin — src/trim.js
 *
 * `ks_answer` 的**纯函数裁剪层**：把引擎返回的取证答案裁成"模型真正需要的那几项"。
 *
 * 为什么单独成模块（2026-09-17，Phase B）：这些函数**零依赖、纯函数**，但原先埋在
 * index.js 里（顶层 import engine/trust/inspection → 拉 DSH 包），node 冒烟无法直接
 * 调用真实现，只能"复刻算法"或"字符串匹配源码"——两者都会漂移。
 * 抽出来之后 `scripts/smoke-trim.mjs` 调用的是**真代码**，回归才真的锁得住。
 *
 * ## 本模块守的一条纪律：**算出来的东西不能悄悄丢掉**
 * 引擎侧算出的核验信息若在这里被白名单漏掉，模型就永远看不到它——
 * `unsupported_context`（D 线"资格声明"）已经这样丢过一次（见 DEVELOPMENT-HISTORY）。
 * 故：**新增核验字段时，必须同时进 `trimVerification` 的白名单 + 冒烟用例**。
 */

/** Cap for each verification list we hand back to the model. */
export const VERIFY_LIST_CAP = 8

/**
 * `unsupported_context[].reason` 的字符上限（比列表项的 160 宽得多）。
 *
 * 为什么单给一个上限：`reason` 是这条信息的**全部价值**所在——它回答"这个引用的
 * 条款号到底怎么了、我该去补什么"。原来走通用 `compact()`（JSON.stringify 后截 160）
 * 会把中文原因**切断在半句上**，正好复现该字段要修掉的那个毛病（告警不可执行）。
 */
export const REASON_CAP = 400

/** Compact a single verification-list item (string, number, or object). */
function compact(item) {
  if (item === null || item === undefined) return null
  if (typeof item === 'string') return item
  if (typeof item === 'object') {
    try {
      const s = JSON.stringify(item)
      return s.length > 160 ? `${s.slice(0, 157)}…` : s
    } catch {
      return String(item)
    }
  }
  return item
}

/** Truncate a verification list to a bounded, JSON-safe form. */
export function shortList(arr, cap = VERIFY_LIST_CAP) {
  if (!Array.isArray(arr) || arr.length === 0) return []
  return arr.slice(0, cap).map(compact)
}

/** 有界字符串：超长时截断并**显式标出被截断**（不假装完整）。 */
function boundedText(value, cap) {
  if (typeof value !== 'string') return null
  return value.length > cap ? `${value.slice(0, cap)}…[已截断]` : value
}

/**
 * `unsupported_context` 的**结构化**裁剪。
 *
 * 刻意**不走** `shortList`/`compact`：那条路把整个对象 JSON 成一行再截 160 字符，
 * 中文 reason 必被切断。这里**逐字段**取（4 个键与原契约一致），`verdict` 原样透出
 * （它是稳定枚举，下游可判），`reason` 单独给宽上限并标明截断。
 *
 * **不造字段**：引擎没给的一律 null，不推断、不补默认值——与本文件其他裁剪同纪律。
 *
 * @param {unknown} arr 引擎 `verification.unsupported_context`
 * @returns {Array<{clause_number:unknown, standard_no:unknown, verdict:unknown, reason:unknown}>}
 */
export function trimUnsupportedContext(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return []
  return arr.slice(0, VERIFY_LIST_CAP).map((c) => {
    if (!c || typeof c !== 'object') return null
    return {
      clause_number: c.clause_number ?? null,
      standard_no: c.standard_no ?? null,
      verdict: c.verdict ?? null,
      reason: boundedText(c.reason, REASON_CAP),
    }
  }).filter(Boolean)
}

/**
 * Trim the verification block: keep the verdict, truncate/compact the lists.
 *
 * ⚠ **白名单纪律**：这里是核验信息通往模型的**唯一一道门**。引擎 `verification`
 * 事件里的字段若没进本白名单，就等于没算（`unsupported_context` 的前车之鉴）。
 */
export function trimVerification(v) {
  if (!v || typeof v !== 'object') return null
  return {
    is_valid: !!v.is_valid,
    answer_confidence: v.answer_confidence ?? 'unknown',
    confidence_reasons: shortList(v.confidence_reasons),
    unsupported_clauses: shortList(v.unsupported_clauses),
    // D 线"资格声明"（契约增量 33 号）：`unsupported_clauses` 只说"引了证据外的号"，
    // 对使用者不可执行；`unsupported_context` 把每条升级为"属于哪部标准 / 是召回漏了
    // 还是模型越界 / 该补什么"。**它必须到模型眼前**，否则这个字段等于没做。
    unsupported_context: trimUnsupportedContext(v.unsupported_context),
    unverified_numbers: shortList(v.unverified_numbers),
    modality_violations: shortList(v.modality_violations),
    legal_element_violations: shortList(v.legal_element_violations),
    citation_index_warnings: shortList(v.citation_index_warnings),
  }
}
