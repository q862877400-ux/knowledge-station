// TipTap 富文本编辑器（纠错用）：支持文字/上标/下标/表格增删行列/LaTeX 公式输入
import { forwardRef, useEffect, useImperativeHandle, useReducer, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table, TableCell, TableHeader, TableRow } from '@tiptap/extension-table';
import Superscript from '@tiptap/extension-superscript';
import Subscript from '@tiptap/extension-subscript';
import TextAlign from '@tiptap/extension-text-align';
import { stripEmbeddedTable, pipeTableToHtml, escapeHtml, normalizeWraps } from './tableText';

export interface TipTapEditorHandle {
  getText: () => string;
  getHTML: () => string;
  // 拆分编辑结果:正文纯文本 + 表格管道 markdown + 完整富文本 html
  // （富文本 html 含 <sup>/<sub>/<b>/<i>/<table> 落 content_markdown，卡片用它渲染格式）
  getParts: () => { text: string; tableMd: string | null; html: string };
  // 整体替换内容（Word/WPS 内容回填用）
  setHTML: (html: string) => void;
}

interface Props {
  value: string;
  tableMd?: string;
  // 编辑初始内容：已有富文本（含 <sup>/<sub>/表格）时直接加载，保留格式（上下标/加粗可再次编辑）
  html?: string;
  height?: number;
}

// 正文 + 表格文本 → HTML（编辑器初始内容；卡片与编辑器同源）
// 正文先剔除内嵌表格文本（与 table_md 重复的行），再追加独立表格，避免显示两份
function textToHtml(text: string, tableMd?: string, html?: string): string {
  if (html && /<p[ >]|<sup[ >]|<sub[ >]|<table/.test(html)) {
    return html;  // 已有富文本（编辑保存过格式的条款），原样加载
  }
  const clean = normalizeWraps(stripEmbeddedTable(text || '', tableMd || ''));
  const paras = clean.split(/\n+/).filter(Boolean).map((p) => '<p>' + escapeHtml(p) + '</p>').join('');
  const table = tableMd ? pipeTableToHtml(tableMd) : '';
  return paras + table;
}

// HTML → 纯文本（表格行转 "a | b" 管道文本；与卡片 table_md 同格式）
function htmlToPlain(html: string): string {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  const out: string[] = [];
  const walk = (node: Node) => {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === Node.TEXT_NODE) out.push(child.textContent || '');
      else if (child.nodeType === Node.ELEMENT_NODE) {
        const el = child as Element;
        const tag = el.tagName.toLowerCase();
        if (tag === 'table') { walk(el); out.push('\n'); }
        else if (tag === 'tr') { out.push('\n'); walk(el); }
        else if (tag === 'td' || tag === 'th') { out.push(' | '); walk(el); }
        else if (['p', 'div', 'br', 'h1', 'h2', 'h3', 'li'].includes(tag)) { walk(el); out.push('\n'); }
        else walk(el);
      }
    }
  };
  walk(tmp);
  return out.join('').replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n').replace(/^[ |]+|[ |]+$/gm, '').trim();
}

// HTML → (正文纯文本, 表格管道 markdown)：拆分编辑结果，表格独立成 table_md 风格管道行
// （表格必须落 content_markdown 才能被卡片/检索读到——saveEdit 需要两个补丁）
function htmlToParts(html: string): { text: string; tableMd: string | null } {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  const textParts: string[] = [];
  const tableRows: string[] = [];
  const walk = (node: Node) => {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === Node.TEXT_NODE) textParts.push(child.textContent || '');
      else if (child.nodeType === Node.ELEMENT_NODE) {
        const el = child as Element;
        const tag = el.tagName.toLowerCase();
        if (tag === 'table') {
          const rows: string[] = [];
          for (const tr of Array.from(el.querySelectorAll('tr'))) {
            const cells = Array.from(tr.children)
              .filter((c) => c.tagName === 'TD' || c.tagName === 'TH')
              .map((c) => (c.textContent || '').trim());
            if (cells.length) rows.push(cells.join(' | '));
          }
          tableRows.push(...rows);
          if (textParts.length && textParts[textParts.length - 1].endsWith(' ')) {
            // 表格后追加换行分隔（正文拼接时）
          }
        } else if (['p', 'div', 'br', 'h1', 'h2', 'h3', 'li'].includes(tag)) {
          walk(el); textParts.push('\n');
        } else if (tag === 'tr' || tag === 'td' || tag === 'th') {
          // 已在 table 分支处理，跳过
        } else {
          walk(el);
        }
      }
    }
  };
  walk(tmp);
  const text = textParts.join('').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n')
    .replace(/^\n+|\n+$/g, '').trim();
  return { text, tableMd: tableRows.length ? tableRows.join('\n') : null };
}

const TipTapEditor = forwardRef<TipTapEditorHandle, Props>(({ value, tableMd, html, height = 500 }, ref) => {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({ resizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      Superscript,
      Subscript,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
    ],
    content: textToHtml(value || '', tableMd, html),
    editorProps: {
      attributes: { class: 'tiptap-editor-body' },
    },
  });
  const valueRef = useRef(value);
  valueRef.current = value;

  // 外部 value 变化时（重新打开）重置内容
  useEffect(() => {
    if (editor && valueRef.current !== value) {
      editor.commands.setContent(textToHtml(value || '', tableMd, html));
      valueRef.current = value;
    }
  }, [value, tableMd, html, editor]);

  useEffect(() => {
    return () => { editor?.destroy(); };
  }, [editor]);

  // 选区/事务变化强制重渲染（isActive 状态随光标位置实时更新）
  const [, force] = useReducer((x: number) => x + 1, 0);
  useEffect(() => {
    if (!editor) return;
    const fn = () => force();
    editor.on('selectionUpdate', fn);
    editor.on('transaction', fn);
    return () => { editor.off('selectionUpdate', fn); editor.off('transaction', fn); };
  }, [editor]);

  useImperativeHandle(ref, () => ({
    // 保存：HTML → 纯文本（表格转管道行，与卡片同源展示）
    getText: () => htmlToPlain(editor?.getHTML() ?? ''),
    getHTML: () => editor?.getHTML() ?? '',
    getParts: () => {
      const html = editor?.getHTML() ?? '';
      return { ...htmlToParts(html), html };
    },
    setHTML: (html: string) => { editor?.commands.setContent(html); },
  }), [editor]);

  if (!editor) return <div className="tiptap-loading">编辑器加载中…</div>;

  const setTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 4, withHeaderRow: true }).run();
  };
  const isT = (k: string) => editor.isActive(k);
  // 光标是否处于表格内（沿选区祖先链判定，兼容 TipTap v3 isActive 时机问题）
  const inTable = (() => {
    const { from } = editor.state.selection;
    if (from == null) return false;
    const $from = editor.state.doc.resolve(from);
    for (let d = $from.depth; d > 0; d--) {
      const t = $from.node(d).type.name;
      if (t === 'table' || t === 'tableCell' || t === 'tableHeader' || t === 'tableRow') return true;
    }
    return false;
  })();

  const TBtn = ({ onClick, active, title, children }: any) => (
    <button type="button" className={'tt' + (active ? ' tt-on' : '')} onClick={onClick} title={title}>{children}</button>
  );

  return (
    <div className="tiptap-wrap">
      <div className="tiptap-toolbar">
        <TBtn onClick={() => editor.chain().focus().undo().run()} title="撤销">↶</TBtn>
        <TBtn onClick={() => editor.chain().focus().redo().run()} title="重做">↷</TBtn>
        <span className="tt-sep" />
        <TBtn onClick={() => editor.chain().focus().toggleBold().run()} active={isT('bold')} title="加粗"><b>B</b></TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleItalic().run()} active={isT('italic')} title="斜体"><i>I</i></TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleStrike().run()} active={isT('strike')} title="删除线"><s>S</s></TBtn>
        <span className="tt-sep" />
        <TBtn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={isT('heading', ) && editor.getAttributes('heading').level === 1} title="一级标题">H1</TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={isT('heading') && editor.getAttributes('heading').level === 2} title="二级标题">H2</TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} active={isT('heading') && editor.getAttributes('heading').level === 3} title="三级标题">H3</TBtn>
        <span className="tt-sep" />
        <TBtn onClick={() => editor.chain().focus().toggleBulletList().run()} active={isT('bulletList')} title="无序列表">•≡</TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={isT('orderedList')} title="有序列表">1≡</TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={isT('blockquote')} title="引用">❝</TBtn>
        <span className="tt-sep" />
        <TBtn onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.getAttributes('paragraph').textAlign === 'left'} title="左对齐">⬅</TBtn>
        <TBtn onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.getAttributes('paragraph').textAlign === 'center'} title="居中">⬌</TBtn>
        <TBtn onClick={() => editor.chain().focus().setTextAlign('right').run()} active={editor.getAttributes('paragraph').textAlign === 'right'} title="右对齐">➡</TBtn>
        <span className="tt-sep" />
        <TBtn onClick={() => editor.chain().focus().toggleSuperscript().run()} active={isT('superscript')} title="上标">x²</TBtn>
        <TBtn onClick={() => editor.chain().focus().toggleSubscript().run()} active={isT('subscript')} title="下标">x₂</TBtn>
        <span className="tt-sep" />
        <TBtn onClick={setTable} title="插入表格（插入后自动聚焦，可加行删行/加列删列）">⊞表格</TBtn>
        {inTable && (<>
          <TBtn onClick={() => editor.chain().focus().addRowAfter().run()} title="当前行后加行">＋行</TBtn>
          <TBtn onClick={() => editor.chain().focus().deleteRow().run()} title="删除当前行">－行</TBtn>
          <TBtn onClick={() => editor.chain().focus().addColumnAfter().run()} title="当前列后加列">＋列</TBtn>
          <TBtn onClick={() => editor.chain().focus().deleteColumn().run()} title="删除当前列">－列</TBtn>
          <TBtn onClick={() => editor.chain().focus().mergeCells().run()} title="合并单元格（先按住 Shift 拖选相邻 2 格以上）">合并</TBtn>
          <TBtn onClick={() => editor.chain().focus().splitCell().run()} title="拆分已合并单元格">拆分</TBtn>
          <TBtn onClick={() => editor.chain().focus().toggleHeaderRow().run()} title="切换表头行">表头</TBtn>
          <TBtn onClick={() => editor.chain().focus().deleteTable().run()} title="删除表格">删表</TBtn>
        </>)}
        <span className="tt-hint">公式可直接输入 LaTeX 文本（如 0.3m～0.6m、F=m·a）</span>
      </div>
      <EditorContent editor={editor} className="tiptap-content" />
    </div>
  );
});

TipTapEditor.displayName = 'TipTapEditor';
export default TipTapEditor;
