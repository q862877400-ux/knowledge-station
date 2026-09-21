/**
 * plugin/scripts/lib/cap-cards-check.mjs — 「**能力页卡片几何**」判据的**唯一所有者**（2026-09-21）
 *
 * ## 它判什么（口径来源：父代理 2026-09-21 的裁定）
 * 能力页**不判"尺寸统一"** —— 上一轮**先量后判**的实测是：8 张 `.ks-cap-card` **宽全等**
 * （900 档 268×8 / 1300 档 236×8）、**高按组三档**（900 档 136×4 / 201×3 / 261×1），
 * 同排等高由 grid `align-items:stretch` 保证。业主那句"统一尺寸"指的是**知识库卡片带**
 * （`cardsCheck` 已钉那一处）⇒ 断言只写**站得住的两条**，且名字里不出现"统一/尺寸统一"：
 *
 *   ① **等宽**：本页所有 `.ks-cap-card` 宽度全等（差 >1px 即红；逐张报 {name,w,h} + 差异诊断）；
 *   ② **同排等高**：按 `getBoundingClientRect().top` 分组，**组内**高度必须全等
 *      —— 钉的是 `align-items:stretch` 这个不变式（改成 `start` 就会有一排参差）；
 *   ③ **防空转**：量到 **0 张 ⇒ 红**（不是静默跳过、也不是"本页不适用"）；
 *   ④ **排数 >= 2**：防 fixture 退化成一张/一排（那种退化下 ①② 会恒真）。
 *
 * ⚠ **不把"8 张"钉成冻结常量**：能力卡数量随功能增加 ⇒ 钉死会假红。下界只要求 >=1（由 ③ 给），
 *   "这确实是一张网格"由 ④ 给。
 * ⚠ 适用面：只有**能力页**判（`.ks-cap-card` 是这一页专有形态，kb 页一张都没有）；其余页面
 *   返回 `skipReason`（明说没判）。**能力页这一侧没有跳过分支**。
 *
 * ## 为什么单独一个模块（不是内联在 ui-render-shot.mjs 里）
 * 像素判据的**变异自证**必须在 `%TEMP%` 的 **fixture 副本**上做（本仓纪律：变异副本不进代码树），
 * 而 fixture 是脚本每次重新生成的 ⇒ 变异跑只能自己起浏览器量那份副本。
 * 把判据放在这里，**变异跑 import 的是同一份代码**（不是抄一份判据 —— 抄一份正是本仓最恨的
 * "两份各自漂移"）。`ui-render-shot.mjs` 与变异跑都从这里取。
 *
 * ## 输入契约（= `ui-render-shot.mjs` 探针写进 `<title>…|m={…}` 的 `#capcards`）
 * `{ n, lh: '逐张宽(逗号分隔)', pad: '逐张高', items: [{name,w,h,top}] }`
 * `measured` 就是那份解析出来的对象；`page` 是 `--page`。
 */
export const CAPCARDS_PAGE = 'capabilities'

/** 同排分组的 top 容差（1px：值已 Math.round，亚像素差 1 不算两排）。 */
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
    skipReason = `本页不是能力页（page=${page}）—— .ks-cap-card 是能力页专有形态，`
      + '能力卡等宽/同排等高这一跑不判'
  } else if (capc === undefined || items.length === 0) {
    problems.push(`**量到 0 张** .ks-cap-card（#capcards = ${JSON.stringify(capc === undefined ? null : capc.n)}）：`
      + '能力页不可能一张能力卡都没有 ⇒ 要么 fixture/DOM 里真的没了卡，要么**探针 selector 坏了**。'
      + '这条**不许**当"本页不适用"静默放过（量不到就是红）。')
  } else {
    const badItems = items.filter((it) => !Number.isFinite(it.w) || !Number.isFinite(it.h) || !Number.isFinite(it.top)
      || it.w <= 0 || it.h <= 0)
    if (badItems.length > 0) {
      problems.push('有卡的宽/高/排位量不到（<=0 或非数）：'
        + JSON.stringify(badItems.map((it) => `${it.name}=${String(it.w)}x${String(it.h)}@${String(it.top)}`)))
    } else {
      /* 逐张明细（{name,w,h}）—— 失败时这段话**就是诊断**：不用再去二进制里翻 BMP。 */
      const perCard = items.map((it) => ({ name: it.name, w: it.w, h: it.h }))
      const ws = items.map((it) => it.w)
      const wMin = Math.min(...ws)
      const wMax = Math.max(...ws)
      if (wMax - wMin > 1) {
        problems.push(`能力卡**宽度不全等**：最窄 ${String(wMin)}px / 最宽 ${String(wMax)}px（差 ${String(wMax - wMin)}px）；`
          + `逐张 ${JSON.stringify(perCard)}`
          + `（最宽的是 ${JSON.stringify(items.filter((it) => it.w === wMax).map((it) => it.name))}；`
          + `最窄的是 ${JSON.stringify(items.filter((it) => it.w === wMin).map((it) => it.name))}）`
          + ' ⇒ 卡宽的声明应只有一处（`.ks-kb-cards` 的 grid 列，能力页是 repeat(auto-fill,minmax(230px,1fr))）。')
      }
      /* 同排分组：按 top 升序，组内 top 差 <= 容差算一排。 */
      const rows = []
      for (const it of [...items].sort((a, b) => a.top - b.top)) {
        const row = rows[rows.length - 1]
        if (row !== undefined && Math.abs(it.top - row.top) <= CAPCARDS_ROW_TOL) row.items.push(it)
        else rows.push({ top: it.top, items: [it] })
      }
      rowsOut = rows
      if (rows.length < 2) {
        problems.push(`只量到 **${String(rows.length)} 排** .ks-cap-card（"同排等高"要 >=2 排才判得了）——`
          + ' fixture/DOM 退化成一张/一排了，这条断言等于没判：'
          + JSON.stringify(rows.map((r) => r.items.map((it) => it.name))))
      }
      for (const row of rows) {
        const hs = row.items.map((it) => it.h)
        if (Math.max(...hs) - Math.min(...hs) > 1) {
          problems.push(`**同一排**（top=${String(row.top)}px）的高度不全等：`
            + JSON.stringify(row.items.map((it) => `${it.name}=${String(it.h)}px`))
            + `（最矮 ${String(Math.min(...hs))} / 最高 ${String(Math.max(...hs))}）`
            + ' —— 同排等高是容器 `.ks-kb-cards{align-items:stretch}` 的不变式，改成 start/flex-start 就会这样。')
        }
      }
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
