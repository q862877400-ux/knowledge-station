// 渲染辅助纯函数（2026-08-26 从 App.tsx 抽出）：不依赖 App 状态，输入→JSX。
// 归位依据：渲染辅助与主组件分离（架构纪律），零 props 传递，可独立单测。
import type { ReactNode } from 'react';
import type { Evidence } from './App';

// 条款可信度徽章：悬停解释为什么（规则分型依据）
export function confBadge(ev: Evidence): ReactNode {
  if (ev.user_confirmed) {
    return <em className="badge ok" title="您已按原文核对确认，人工判定为可信">✅ 已核对</em>;
  }
  if (ev.is_suspicious) {
    return <em className="badge warn" title={'存疑原因：条款未识别到义务模态词（应/宜/严禁等）或数值单位，分型置信度仅 50%，可能为定义条款或解析碎片，建议核对原文'}>⚠存疑</em>;
  }
  const conf = Math.round((ev.type_confidence ?? 1) * 100);
  if (conf >= 85) {
    const why = ev.knowledge_type === 'data'
      ? '条款含数值/单位，规则分型命中'
      : '条款含义务模态词（' + (ev.modality || '应/宜') + '），规则分型命中';
    return <em className="badge ok" title={'高可信原因：' + why + '，分型置信度 ' + conf + '%（≥85% 判为高可信）'}>高可信</em>;
  }
  const whyMid = ev.knowledge_type === 'legal'
    ? '法律条文分型'
    : '分型未同时命中模态词与数值';
  return <em className="badge mid" title={'建议核对原因：' + whyMid + '，置信度仅 ' + conf + '%（未达 85% 高可信线）'}>建议核对原文</em>;
}

// 修订记录悬停提示：显示上次纠错的内容与原因
export function revisionTip(ev: Evidence): string {
  const recs = ev.patch_records || [];
  const ct = recs.find((r) => r.field_name === 'content_text');
  if (ct) {
    return '修订记录：' + (ct.patch_reason || '内容纠错') + ' → ' + ct.patched_value.slice(0, 70)
      + (ct.updated_at ? '（' + ct.updated_at + '）' : '');
  }
  return '存在修订记录：' + recs.map((r) => r.field_name).join('、');
}

// ========== 编号重复通用展示规则（2026-08-29 用户定稿）==========
// 文字版国标/法规 PDF 提取的条款正文天然以条款号开头（"3.1 一般要求…"，实测 GB 25596
// 47/47 条全部如此），与界面识别编号徽章（"第3.1条"/fulltext-cno/toc-no）重复展示。
// 规则：仅当正文开头编号与识别编号**精确一致**时，把正文开头这段编号**隐藏不显示**
// （display:none 的 span 包住，DOM 数据原样保留）；不一致或无编号 → 原样完整显示。
// 绝不硬删除字符——识别错误时正文开头几个字一个都不会丢，去掉隐藏即全部找回。
// 词边界 (?![\d.]) 防 "3.1" 误匹配 "3.10"；"1" 不误匹配 "100mg"/"12月龄"（数字边界）。

// 编号 → 正则源：字面转义 + 字符间允许排版空白（通用）。
// 依据：GB 文本层附录头/表格编号普遍带排版空格——"附 录 A"、"附　录　A"(全角)、
// "表A. 1"、"4. 1"（实测 GB 25596 入库文本即此形态）。字符间插 \s* 全覆盖；
// 点号不可省略（"4 1" 不匹配 "4.1"），词边界另行保证。
function escDupNo(no: string): string {
  return no.split('').map((c, i) => {
    const esc = c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return i < no.length - 1 ? esc + '\\s*' : esc;
  }).join('');
}

// 判定：text（允许字间空白）是否以识别编号 no 开头（返回编号段 match，不匹配返回 null）
export function dupNoMatches(text: string | null | undefined, no: string | null | undefined): RegExpMatchArray | null {
  if (!no || !text) return null;
  return text.trim().match(new RegExp('^(' + escDupNo(no) + ')(?![\\d.])'));
}

// content_html 变换：首个标签（若有）之后的文本开头编号包进 display:none 的 span。
// 判定先行（去标签文本核对），不匹配（编号不一致/表格开头等）→ 原样返回，零副作用。
export function hideDupClauseNoHtml(html: string | null | undefined, no: string | null | undefined): string {
  if (!html || !no) return html ?? '';
  const m = dupNoMatches(html.replace(/<[^>]+>/g, ' '), no);
  if (!m) return html;
  return html.replace(
    new RegExp('(^\\s*(?:<[a-zA-Z][^>]*>)?\\s*)(' + escDupNo(no) + ')(?![\\d.])'),
    '$1<span class="dup-no-hidden">$2</span>',
  );
}

// 纯文本路径：开头编号用 display:none 的 span 包住再接剩余文本（不删字符）
export function hiddenDupNoText(text: string | null | undefined, no: string | null | undefined, maxLen = 300): ReactNode {
  const t = text ?? '';
  const m = dupNoMatches(t, no);
  if (!m) return <>{t.slice(0, maxLen)}…</>;
  const rest = t.slice(m[1].length).trimStart();
  return <><span className="dup-no-hidden">{m[1]}</span>{rest.slice(0, maxLen)}…</>;
}

// 保存前清洗：contentEditable 的 innerHTML 里被隐藏的编号 span 还原为裸文本，
// 保证补丁落库的数据与库内原文形态一致（渲染注入 → 保存还原，数据流闭环）。
export function cleanupDupNoSpan(html: string): string {
  return html.replace(/<span class="dup-no-hidden">([\s\S]*?)<\/span>/g, '$1');
}

// 卡片正文富文本渲染（content_html → 编号隐藏注入 → sanitize 白名单 → 摘要截断）
// 支持 <p>/<sup>/<sub>/<b>/<i>/<em>/<strong>/<br> 等内联格式与 <table>；脚本/事件属性一律剔除
export function renderContentHtml(ev: Evidence, maxLen = 300): ReactNode {
  const html = ev.content_html;
  if (!html) return null;
  // 注入在解析前：首个文本开头的重复编号包进隐藏 span（判定先行，不一致不注入）
  const tmp = document.createElement('div');
  tmp.innerHTML = hideDupClauseNoHtml(html, ev.clause_number);
  // 去掉脚本/样式/事件属性（本地库+编辑器来源，仍做纵深防御）
  for (const el of Array.from(tmp.querySelectorAll('script, style, iframe, [onclick], [onerror], [onload]'))) {
    el.remove();
  }
  // 文本截断：取纯文本长度 ≤ maxLen，保留标签结构
  const textLen = (tmp.textContent || '').length;
  if (textLen > maxLen) {
    // 截断路径：隐藏 span 经 textContent 往返会丢失标签形态 → 纯 React 文本重建，
    // 开头编号段用隐藏 span 包回（识别编号一致才包，与全文预览规则一致）
    let txt = tmp.textContent || '';
    const m = dupNoMatches(txt, ev.clause_number);
    let head: ReactNode = null;
    if (m) {
      head = <span className="dup-no-hidden">{m[1]}</span>;
      txt = txt.slice(m[1].length);
    }
    return <div className="ev-text">{head}{txt.slice(0, maxLen).trimStart()}…</div>;
  }
  return <div className="ev-text rich" dangerouslySetInnerHTML={{ __html: tmp.innerHTML }} />;
}

// 卡片内结构化渲染附表（table_md → 表格）
export function renderTable(ev: Evidence): ReactNode {
  const md = ev.table_md;
  if (!md) return null;
  const dropTail = (cells: string[]) => {
    const out = cells.slice();
    while (out.length > 1 && !out[out.length - 1]) out.pop();
    return out;
  };
  const rows = md.split('\n').map((r) => dropTail(r.split('|').map((c) => c.trim())))
    .filter((r) => r.some((c) => c));
  if (rows.length < 2) return null;
  return (
    <div className="ev-table-wrap">
      <table className="ev-table">
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
