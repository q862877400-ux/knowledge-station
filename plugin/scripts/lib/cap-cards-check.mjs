/**
 * plugin/scripts/lib/cap-cards-check.mjs — 「**办事台菜单行几何**」判据的**唯一所有者**
 *
 * ⚠ 形态更正留痕（2026-09-22）：本模块原判「能力页**卡片**几何」（2026-09-21：卡片等宽 +
 * 同排等高）。业主 2026-09-22 裁定**废弃卡片式**（办事台 = 等高菜单行）⇒ 判据翻成**行口径**；
 * 文件名 cap-cards-* 是历史遗留（更名归批3 文案清尾）。
 *
 * ## 它判什么（v3 定稿口径）
 *   ① **全部行等高**：菜单行高是 v3 的核心不变式（62px 固定 ⇒ 量出来全等；谁改成
 *      auto/参差立刻红）——取代旧"同排等高"（行是单列，"排"概念已死）；
 *   ② **防退化**：至少 **2 行**（退化成 1 行时 ① 恒真 = 没判）；
 *   ③ **防空转**：量到 **0 行 ⇒ 红**（不是静默跳过）。
 *
 * ⚠ 不冻结"8 行"：功能会增加（同旧"不钉 8 张"的纪律）。
 * ⚠ 适用面：只有 `capabilities` 页判（`.ks-off-row` 专有）；其余页面 `skipReason` 明说没判。
 *
 * ## 为什么单独一个模块
 * 像素判据的**变异自证**在 `%TEMP%` fixture 副本上做，`ui-render-shot.mjs` 与变异跑
 * **import 同一份**（不许抄第二份判据）。
 *
 * ## 输入契约（= `ui-render-shot.mjs` 探针写进 `#capcards` 的量值）
 * `{ n, lh: '逐行宽', pad: '逐行高', items: [{name,w,h,top}] }`（键名 #capcards 为历史遗留）。
 */
export const CAPCARDS_PAGE = 'capabilities'

/** 同排分组的 top 容差（保留导出兼容；行口径已不用分组，但变异跑可能引用）。 */
export const CAPCARDS_ROW_TOL = 1

/**
 * 判据主体（纯函数，无 IO）。
 * @param {Record<string, unknown>} measured 探针回传的对象（取 `#capcards`）
 * @param {string} page `--page` 的名字（只有 `capabilities` 判）
 */
export function checkCapCards(measured, page) {
  const capc = measured?.['#capcards']
  const items = Array.isArray(capc?.items) ? capc.items : []
  const problems = []
  let skipReason = null
  let rowsOut = null

  if (page !== CAPCARDS_PAGE) {
    skipReason = `本页不是办事台（page=${page}）—— .ks-off-row 是办事台专有形态，`
      + '菜单行等高这一跑不判'
  } else if (capc === undefined || items.length === 0) {
    problems.push(`**量到 0 行** .ks-off-row（#capcards = ${JSON.stringify(capc === undefined ? null : capc.n)}）：`
      + '办事台不可能一行菜单都没有 ⇒ 要么 fixture/DOM 里真的没了行，要么**探针 selector 坏了**。'
      + '这条**不许**当"本页不适用"静默放过（量不到就是红）。')
  } else if (items.length < 2) {
    problems.push(`只量到 **${String(items.length)} 行** .ks-off-row（"全部行等高"要 >=2 行才判得了）——`
      + ' fixture/DOM 退化成一行了，这条断言等于没判：' + JSON.stringify(items))
  } else {
    const badItems = items.filter((it) => !Number.isFinite(it.w) || !Number.isFinite(it.h) || !Number.isFinite(it.top)
      || it.w <= 0 || it.h <= 0)
    if (badItems.length > 0) {
      problems.push('有行的宽/高/排位量不到（<=0 或非数）：'
        + JSON.stringify(badItems.map((it) => `${it.name}=${String(it.w)}x${String(it.h)}@${String(it.top)}`)))
    } else {
      const perRow = items.map((it) => ({ name: it.name, w: it.w, h: it.h }))
      /* ① 全部行等高（v3 核心不变式）—— 值由 KsOfficeRow 的固定行高给，谁改成参差立刻红。 */
      const hs = items.map((it) => it.h)
      const hMin = Math.min(...hs)
      const hMax = Math.max(...hs)
      if (hMax - hMin > 1) {
        problems.push(`菜单行**高度不全等**：最矮 ${String(hMin)}px / 最高 ${String(hMax)}px（差 ${String(hMax - hMin)}px）；`
          + `逐行 ${JSON.stringify(perRow)}`
          + ' ⇒ 行高的声明应只有一处（KsOfficeRow 的固定行高）；改成 auto/参差就不再是"等高菜单行"。')
      }
      rowsOut = items.map((it) => ({ top: it.top, items: [it] }))
    }
  }

  return {
    checked: problems.length === 0 && skipReason === null,
    skipReason,
    problems,
    page,
    count: capc?.n ?? null,
    widths: capc?.lh ?? null,
    heights: capc?.pad ?? null,
    rowCount: rowsOut === null ? null : rowsOut.length,
    rows: rowsOut === null ? null : rowsOut.map((r) => ({
      top: r.top, names: r.items.map((it) => it.name), heights: r.items.map((it) => it.h),
    })),
    items: items.length === 0 ? null : items.map((it) => ({ name: it.name, w: it.w, h: it.h, top: it.top })),
  }
}
