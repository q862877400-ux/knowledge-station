// 表格展示统一层：卡片 / 编辑框 / 回答气泡共用
// 1) stripEmbeddedTable：正文里若已内嵌表格文本（table_md 的行），显示时剔除，避免重复
// 2) mdTablesToHtml：回答气泡里的 markdown 管道表格 → 真 <table>

// OCR 换行清理：原文一行的折行在识别后变成硬换行，若未写满则合并回连贯文本
// 规则：单换行拼接（CJK 直连、字母数字补空格）；仅当「句末标点 + 下一行是编号/表/注/第X条」才保留段落断行
export function normalizeWraps(s: string): string {
  const lines = (s || '').split('\n').map((l) => l.trim());
  const out: string[] = [];
  for (const l of lines) {
    if (!l) {
      if (out.length && out[out.length - 1] !== '') out.push('');
      continue;
    }
    const last = out.length ? out[out.length - 1] : null;
    if (last && last !== '') {
      const prevEnds = /[。！？；：]$/.test(last);
      const thisIsPara = /^(\d{1,2}(\.\d+)*\s*[、．.]?|（[一二三四五六七八九十]+）|[一二三四五六七八九十]+、|表\d+|附录|注[:：]?|第[一二三四五六七八九十]+[章条节]|图\d+)/.test(l);
      if (prevEnds && thisIsPara) {
        out.push(l);
      } else {
        const needSpace = /[A-Za-z0-9]$/.test(last) && /^[A-Za-z0-9]/.test(l);
        out[out.length - 1] = last + (needSpace ? ' ' : '') + l;
      }
    } else {
      out.push(l);
    }
  }
  return out.join('\n');
}

// 从正文中剔除与 table_md 重复的表格文本块，并去掉页脚/下节标题泄漏
export function stripEmbeddedTable(text: string, tableMd?: string | null): string {
  let t = text || '';
  if (tableMd) {
    const tokens = new Set(
      tableMd.split('\n').flatMap((r) => r.split('|').map((c) => c.trim())).filter(Boolean)
    );
    if (tokens.size > 0) {
      const lines = t.split('\n');
      const idx = lines.findIndex((l) => tokens.has(l.trim().replace(/\s+/g, ' ')));
      if (idx >= 0) t = lines.slice(0, idx).join('\n');
    }
  }
  // 页脚/下节标题泄漏：结尾形如 "5 GB 3608—2025" 或 "4 高处作业分级"
  t = t.replace(/\s+\d+\s+GB\s+[0-9—–-]+\s*$/g, '');
  t = t.replace(/\n+\s*\d{1,2}\s+[\u4e00-\u9fa5]{4,}\s*$/g, '');
  return t.trim();
}

// 回答文本中的 markdown 管道表格 → <table class="ans-table">（输入应为已转义文本）
export function mdTablesToHtml(s: string): string {
  const lines = s.split('\n');
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (l.includes('|') && l.trim().startsWith('|')) {
      const block: string[] = [];
      while (i < lines.length && lines[i].includes('|')) { block.push(lines[i]); i++; }
      out.push(blockToTable(block));
    } else { out.push(l); i++; }
  }
  return out.join('\n');
}

function blockToTable(block: string[]): string {
  const cells = (line: string) => line.split('|').slice(1, -1).map((c) => c.trim());
  const rows = block.map(cells);
  let header = false;
  if (rows[1] && rows[1].every((c) => /^:?-{2,}:?$/.test(c))) {
    header = true;
    rows.splice(1, 1);
  }
  const body = rows.map((r, ri) => {
    const tag = header && ri === 0 ? 'th' : 'td';
    return '<tr>' + r.map((c) => '<' + tag + '>' + (c || '&nbsp;') + '</' + tag + '>').join('') + '</tr>';
  }).join('');
  return '<table class="ans-table"><tbody>' + body + '</tbody></table>';
}

// pipe 表格（table_md 风格）→ HTML 表格（编辑框初始内容用）
// 去掉行尾空单元格（table_md 偶发尾部分隔符）
function dropTrailingEmpty(cells: string[]): string[] {
  const out = cells.slice();
  while (out.length > 1 && !out[out.length - 1]) out.pop();
  return out;
}

export function pipeTableToHtml(tableMd: string): string {
  const rows = tableMd.split('\n')
    .map((r) => dropTrailingEmpty(r.split('|').map((c) => c.trim())))
    .filter((r) => r.some((c) => c));
  return '<table><tbody>' + rows.map((r) =>
    '<tr>' + r.map((c) => '<td>' + escapeHtml(c) + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
