// 条款号匹配高亮（取代"整段正文匹配"）：只框条款号数字本身，短而唯一、命中率高。
// 纯函数、无 pdfjs 依赖，便于单独审阅/测试。
// 矩形均为 **viewport 坐标**（左上原点 y 向下），由调用方转换后传入。

export interface AnchorToken {
  str: string;                                   // 单条文本项原文
  left: number; top: number; right: number; bottom: number; // viewport 矩形
}

export interface AnchorRect {
  left: number; top: number; right: number; bottom: number;
}

/** 归一化：小写 + 全角ASCII转半角 + 全半角标点归一并去掉所有空白。 */
export function normText(s: string): string {
  if (!s) return '';
  const PUNCT: Record<string, string> = {
    '～': '~', '−': '-', '–': '-', '—': '-', '－': '-',
    '（': '(', '）': ')', '：': ':', '；': ';', '，': ',', '。': '.',
    '“': '"', '”': '"', '‘': "'", '’': "'", '　': ' ',
  };
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0)!;
    if (c >= 0xff01 && c <= 0xff5e) { out += String.fromCharCode(c - 0xfee0); continue; }
    if (c === 0x3000) { out += ' '; continue; }
    if (c === 0x200b || c === 0x200c || c === 0x200d || c === 0xfeff || c === 0x00ad) continue;
    out += PUNCT[ch] ?? ch;
  }
  return out.toLowerCase().replace(/\s+/g, '');
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** 估算文本宽度"单位"：半角字符算 0.5，其余算 1（中文全角更宽）。仅用于框宽度占比。 */
function _units(s: string): number {
  let u = 0;
  for (const ch of s) {
    const c = ch.codePointAt(0)!;
    u += (c >= 0x20 && c <= 0x7e) ? 0.5 : 1;
  }
  return u;
}

/**
 * 在 tokens 里找以条款号开头的标题 token，返回**只框条款号数字部分**的小矩形。
 * 匹配带边界（`^条款号(?![.\d])`），防止 4.1 命中 4.10 / 4.1.2 之类子条款。
 * 未命中返回 null（由调用方回退原 bbox）。
 */
export function anchorClauseNumber(tokens: AnchorToken[], clauseNumber: string): AnchorRect | null {
  const num = normText(clauseNumber);
  if (!num || !tokens.length) return null;
  const re = new RegExp('^' + escapeRegex(num) + '(?![.\\d])');
  for (const t of tokens) {
    const tn = normText(t.str);
    if (!tn) continue;
    if (re.test(tn)) {
      // 框宽按"字符单位"占比估（数字半角窄、中文全角宽），只圈到数字尾巴
      const numUnits = _units(num);
      const totalUnits = Math.max(1, _units(t.str));
      const frac = Math.max(0.05, Math.min(1, numUnits / totalUnits));
      const w = t.right - t.left;
      return { left: t.left, top: t.top, right: t.left + frac * w, bottom: t.bottom };
    }
  }
  return null;
}
