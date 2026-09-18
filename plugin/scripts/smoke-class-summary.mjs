/**
 * ks-dsh-plugin — scripts/smoke-class-summary.mjs
 *
 * 五类结论（发布/修订/废止/现行性/编号核验）**归组与落盘口径**的离线回归
 * （§11.0 R6e：把引擎从 R6c-4c 起就在记的 `latest_info.classes` 第一次显示到面板上）。
 *
 * 为什么要有这一条：这段逻辑决定面板上那个"X/Y"到底是什么意思。三个口径错一个，
 * 数字就会**看起来很有信息量、实际在骗人**：
 *   ① `classes` 键**不存在** ⇒ 计 `unreadable`、**不进**分母（那是"这批没记五类"，
 *      不是"答不出来"；R6c-4c 之前的事件、引擎读台账失败降级都是这个形状）；
 *   ② 某类**缺项** ⇒ 记 `absent`，**不许**冒充 `not_probed`（"没轮到问"是另一回事）；
 *   ③ `total` **只数有 classes 的条数**——分母混进没记录的号，就会出现
 *      "发布 3/500"这种把人吓一跳、其实什么都没说明的数字。
 *
 * 跑法：node scripts/smoke-class-summary.mjs   （退出码 0 = 全通过）
 */
import {
  byClassEmpty,
  emptyByClass,
  reduceOneClassRow,
  sanitizeLast,
} from '../src/inspection.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

const CLS = ['发布', '修订', '废止', '现行性', '编号核验']

/* ---------------------------- ① 空形态 ---------------------------- */
{
  const e = emptyByClass()
  check('空形态：total=0 / unreadable=0 / 五类键齐',
    e.total === 0 && e.unreadable === 0 && CLS.every((c) => e.classes[c] !== undefined
      && e.classes[c].answered === 0 && Object.keys(e.classes[c].reasons).length === 0),
    JSON.stringify(e))
}

/* ------------------- ② 没有 classes 键 ⇒ 不算分母 ------------------- */
{
  const bc = emptyByClass()
  reduceOneClassRow(bc, { change_type: 'no_change' })                       // 无字段
  reduceOneClassRow(bc, { latest_info_json: null })                         // null
  reduceOneClassRow(bc, { latest_info_json: '{不是 JSON' })                  // 坏 JSON
  reduceOneClassRow(bc, { latest_info_json: '{"version":"x"}' })            // 有 JSON 没 classes
  reduceOneClassRow(bc, { latest_info_json: '{"classes":null}' })           // classes 不是对象
  check('没记五类的条目：unreadable=5、total 不动、不产生任何"未答"',
    bc.unreadable === 5 && bc.total === 0
      && CLS.every((c) => bc.classes[c].answered === 0
        && Object.keys(bc.classes[c].reasons).length === 0),
    JSON.stringify(bc))
}

/* ------------- ③ 答了 / 没答（带原因）/ 缺项 → absent ------------- */
{
  const bc = emptyByClass()
  reduceOneClassRow(bc, {
    latest_info_json: JSON.stringify({
      classes: {
        发布: { status: 'answered', reason: 'ok', conclusion: { date: '2019-03-01' } },
        修订: { status: 'not_answered', reason: 'not_probed' },
        废止: { status: 'not_answered', reason: 'channel_gave_no_field' },
        现行性: { status: 'answered', reason: 'ok' },
        // 编号核验 整项缺失
      },
    }),
  })
  const c = bc.classes
  check('一条事件：答出 2 类、两类各记各的原因、缺项记 absent、total=1',
    bc.total === 1 && bc.unreadable === 0
      && c['发布'].answered === 1 && c['现行性'].answered === 1
      && c['修订'].reasons.not_probed === 1
      && c['废止'].reasons.channel_gave_no_field === 1
      && c['编号核验'].reasons.absent === 1,
    JSON.stringify(bc))

  // 同一原因跨条累加；answered 不会串到别的类上
  reduceOneClassRow(bc, {
    latest_info_json: { classes: { 发布: { status: 'not_answered', reason: 'not_probed' } } },
  })
  check('再一条（对象形 latest_info 也认）：发布 的 answered 保持 1、not_probed 累到 1、total=2',
    bc.total === 2 && c['发布'].answered === 1 && c['发布'].reasons.not_probed === 1,
    JSON.stringify(bc))
}

/* ------------------ ④ 未答原因缺失/非法 ⇒ unknown ------------------ */
{
  const bc = emptyByClass()
  reduceOneClassRow(bc, {
    latest_info_json: JSON.stringify({ classes: { 发布: { status: 'not_answered' } } }),
  })
  check('没写 reason 的未答 ⇒ 记 unknown（不许静默丢）',
    bc.classes['发布'].reasons.unknown === 1, JSON.stringify(bc))
}

/* -------------------- ⑤ 状态文件落盘口径（sanitize） -------------------- */
{
  const legacy = sanitizeLast({ batch_id: 'b1', status: 'done', total: 3 })
  check('旧状态文件（无 by_class）⇒ null（UI 只说"没取到"，不说"没有欠账"）',
    legacy.by_class === null, JSON.stringify(legacy.by_class))

  const dirty = sanitizeLast({
    batch_id: 'b2', status: 'done', total: 9,
    by_class: {
      total: '5', unreadable: -3,
      classes: {
        发布: { answered: '2', reasons: { not_probed: '1', bad: 0 } },
        废止: { answered: null, reasons: {} },
        未知类: { answered: 99, reasons: { x: 1 } },
      },
    },
  })
  const bc = dirty.by_class
  check('脏数字被夹住：total=5、unreadable=0、answered=2、reasons 只留正数',
    bc.total === 5 && bc.unreadable === 0
      && bc.classes['发布'].answered === 2
      && bc.classes['发布'].reasons.not_probed === 1
      && !('bad' in bc.classes['发布'].reasons),
    JSON.stringify(bc))
  check('未登记的类名被丢弃、五类键补齐',
    !('未知类' in bc.classes) && CLS.every((c) => bc.classes[c] !== undefined)
      && bc.classes['废止'].answered === 0,
    JSON.stringify(Object.keys(bc.classes)))
}

/* ---------------------- ⑥ byClassEmpty（自愈判据） ---------------------- */
{
  const onlyUnanswered = emptyByClass()
  onlyUnanswered.classes['发布'].reasons.not_probed = 3
  check('byClassEmpty：null/空 ⇒ true；只要有 answered 或 reason ⇒ false',
    byClassEmpty(null) === true && byClassEmpty(emptyByClass()) === true
      && byClassEmpty(onlyUnanswered) === false,
    `${byClassEmpty(null)} ${byClassEmpty(emptyByClass())} ${byClassEmpty(onlyUnanswered)}`)
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== class-summary smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
