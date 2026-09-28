/**
 * ks-dsh-plugin — src/tool-details.js  （批3-c，2026-09-22：工具说明瘦身的"首次回执"侧）
 *
 * 省 token 硬约束（业主）：工具 `description` 是**每轮都随工具表进上下文**的——
 * ks_answer 原文 2156 字/轮。批3-c 把说明书压到 ≤10 行，**细节搬进首次调用回执**
 * （官方 `exec.deferContext`；只在本会话第一次调该工具时追加一次）。
 *
 * 单一出处纪律：回执全文 = 原说明书**逐字搬运**（改写处只在 description 侧）；
 * 本文件之外不许再长出第二份。resolve/ping/effect 三件的瘦身是**纯精简**（无实质细节外移），
 * 原文留档 var/tmp/desc-before-*.txt（报告引用）。
 */

/** ks_answer 首用回执 = 原说明书全文（2156 字，逐字搬运）。 */
export const KS_ANSWER_DETAIL = 'Run a forensic (取证) compliance question against the local KnowledgeStation engine and '
  + 'return a trimmed three-part answer: 依据区 evidence -> 推导区 derivation -> 结论区 conclusion, '
  + 'plus tier, verification confidence and notes. The engine runs its OWN DeepSeek inference '
  + 'behind this call, so it can take tens of seconds — the caller timeout is set high (>=120s). '
  + 'Prefer a cheap ks_resolve_clause first when a fast citation lookup is enough; use ks_answer '
  + 'only for a real forensic answer. Only current-effective clauses are cited; upcoming revisions '
  + 'are surfaced in notes. A "reference" tier or empty evidence means the engine found no direct '
  + 'current provision (returned as a structured empty result, not a hard error). '
  + 'When citing an evidence item in your answer, render its evidence_url as a clickable '
  + 'Markdown link, e.g. [依据：<standard_no> <clause_number>](<evidence_url>) — the GUI '
  + 'opens the original PDF at that page when the user clicks it. '
  + 'Scope: params.kb_folder_ids (folder ids: each means that folder AND all its children) and '
  + 'params.kb_doc_ids (explicit doc ids, for files not filed in any folder yet) restrict '
  + 'RETRIEVAL itself; several ids = the union, and the two knobs together are also a union. '
  + 'OMIT them for the whole library. An EMPTY array is NOT "no scope" and is not an acceptable '
  + 'scope input: the engine answers HTTP 422 and does no retrieval at all — it never falls back '
  + 'to the whole library. (Different case: a folder that exists but whose subtree is empty ⇒ '
  + 'HTTP 200, no retrieval, and an honest "nothing inside the scope".) '
  + 'IMPORTANT — verification.unsupported_context: if it lists a clause number you cited, '
  + 'that citation is NOT supported and you MUST disclose it in your own words rather than '
  + 'silently dropping it: name the standard, then say which case it is — '
  + 'same_standard_not_retrieved means the clause belongs to a standard that IS in the '
  + 'evidence but the clause itself was not retrieved (a retrieval gap, not a fabrication); '
  + 'outside_evidence_standard means it points at a standard outside the retrieved evidence '
  + '(out of scope, or possibly invented). Never present such a citation as support, and '
  + 'never omit the fact that it was raised.'

const DETAIL_BY_TOOL = {
  ks_answer: KS_ANSWER_DETAIL,
}

const seen = new Set() // `${tool}@${session}` — 每会话每工具只发一次
let detailSeq = 0

/**
 * 首次调用回执（`exec.deferContext(UserMessage)` 官方通道；消息必填 id+source——
 * F3 教训直接内建：inbox 按 id 去重）。`exec.deferContext` 是**可缺省**面 ⇒ 探针降级。
 * @param exec - 工具执行上下文。
 * @param toolName - 工具名（DETAIL_BY_TOOL 键）。
 */
export function firstUseReceipt(exec, toolName) {
  const detail = DETAIL_BY_TOOL[toolName]
  if (typeof detail !== 'string' || typeof exec?.deferContext !== 'function') return
  const key = `${toolName}@${exec?.agent?.session?.id ?? ''}`
  if (seen.has(key)) return
  seen.add(key)
  detailSeq += 1
  exec.deferContext({
    id: `ks-detail-${toolName}-${Date.now().toString(36)}-${String(detailSeq)}`,
    // v4 生产者合约：kind 是生产者自己的身份、plugin 字段被丢弃
    // （DSH `session-format-v3-to-v4/src/sources.ts` 的 rewritePluginSource 原文：
    //   "kind is the producer's own kind and whose `plugin` field is dropped"）
    source: { kind: 'plugin:ks-dsh-plugin' },
    role: 'user',
    content: [{ type: 'text', text: detail }],
  })
}
