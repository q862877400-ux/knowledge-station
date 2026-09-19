/**
 * ks-dsh-plugin — client/ksSearchSyntax.ts
 *
 * 检索语法解析（业主 2026-09-19 亲定）：
 *   「多个关键词用 **+** 号链接，然后用 **-** 号连接关键词那就是屏蔽这个词，
 *     比如 **安全+半导体-冶金**」
 *
 * ⇒ `+` = 并且（AND），`-` 前缀 = 屏蔽（NOT）。
 *
 * ## 为什么单独抽一个纯函数模块
 * 1. 用户界面上要**当场显示解析结果**（「含 安全、半导体；排除 冶金」），
 *    否则用户没法确认自己那串符号被理解成了什么；
 * 2. 纯函数才好被冒烟**逐例钉住**（这页的其它部分都还是占位 UI，只有它是真逻辑）。
 *
 * ## 一个真陷阱：标准号里本来就有 `-`
 * `GB 30871-2022`、`GB/T 50016-2014` 里都有连字符。若把每个 `-` 都当"屏蔽"，
 * 用户搜标准号就会被**静默拆成两半**（搜不到还不报错）。所以规则是：
 * **`-` 只有在"不是紧跟在数字后面"时才是屏蔽符**。
 *   `半导体-冶金`  → `-` 前是「体」（非数字）⇒ 屏蔽「冶金」 ✓（业主的例子）
 *   `30871-2022`   → `-` 前是「1」（数字）  ⇒ 连字符**保留在词里** ✓
 *
 * ## 另一个已踩过的坑：全角符号
 * 本仓有过一次真事故：全角号导致请求发不出去（`DEVELOPMENT-HISTORY.md` §10.106）。
 * 中文输入法下打出 `＋`／`－`／全角空格是**常态**，所以这里一律先归一化。
 */

/** 解析结果。`include` 是必须全部命中的词，`exclude` 是要屏蔽的词。 */
export interface KsQuery {
  /** 必须命中的词（`+` 连接），按出现顺序去重。 */
  readonly include: readonly string[]
  /** 要屏蔽的词（`-` 前缀），按出现顺序去重。 */
  readonly exclude: readonly string[]
  /** 归一化后的查询串（全角符号已换成半角），供 UI 回显/调试。 */
  readonly normalized: string
}

/** 全角 → 半角（**中文输入法下这些是常态，不是边角情形**）。 */
function normalize(raw: string): string {
  return raw
    .replace(/\uFF0B/g, '+') // ＋
    .replace(/[\uFF0D\u2212\u2013]/g, '-') // － − –
    .replace(/\u3000/g, ' ') // 全角空格
    .trim()
}

/** 去重并保持顺序（空词丢掉）。 */
function pushUnique(list: string[], seen: Set<string>, value: string): void {
  const term = value.trim()
  if (term === '' || seen.has(term)) return
  seen.add(term)
  list.push(term)
}

/**
 * 解析检索串。
 *
 * @param raw - 用户输入的原串（可含全角符号）。
 * @returns 必含词、屏蔽词与归一化串；**任何输入都不抛异常**（空串给空结果）。
 */
export function parseKsQuery(raw: string): KsQuery {
  const normalized = normalize(raw)
  const include: string[] = []
  const exclude: string[] = []
  const seenIn = new Set<string>()
  const seenEx = new Set<string>()

  let buffer = ''
  let inExclude = false
  let prevChar = ''

  const flush = (): void => {
    if (inExclude) pushUnique(exclude, seenEx, buffer)
    else pushUnique(include, seenIn, buffer)
    buffer = ''
  }

  for (const ch of normalized) {
    if (ch === '+') {
      flush()
      // `+` 之后永远回到"必含"（`-a+b` 里的 b 是必含，不继承屏蔽）
      inExclude = false
    } else if (ch === '-' && !/[0-9]/.test(prevChar)) {
      // ⚠ 只有"前面不是数字"时才是屏蔽符 —— 见文件头 `GB 30871-2022` 的说明
      flush()
      inExclude = true
    } else {
      buffer += ch
    }
    prevChar = ch
  }
  flush()

  return { include, exclude, normalized }
}

/**
 * 把解析结果说成人话，供 UI 当场回显（省得用户猜自己那串符号被理解成了什么）。
 *
 * @param query - `parseKsQuery` 的结果。
 * @returns 例如 `含「安全」「半导体」；排除「冶金」`；两者皆空时给空串（由调用方决定怎么显示）。
 */
export function describeKsQuery(query: KsQuery): string {
  const parts: string[] = []
  if (query.include.length > 0) parts.push(`含 ${query.include.map((t) => `「${t}」`).join('')}`)
  if (query.exclude.length > 0) parts.push(`排除 ${query.exclude.map((t) => `「${t}」`).join('')}`)
  return parts.join('；')
}
