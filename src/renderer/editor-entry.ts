// 独立 Univer 编辑器入口（iframe 隔离用）：纯 Univer，不引入 React/App
// 通过 postMessage 与父窗口通信：{type:'init', text} 传入内容；父窗口调 getText
import '@univerjs/preset-docs-core/lib/index.css';
import { createUniver, defaultTheme, LocaleType, LogLevel, UniverInstanceType } from '@univerjs/presets';
import { UniverDocsCorePreset } from '@univerjs/preset-docs-core';

const created = createUniver({
  locale: LocaleType.ZH_CN,
  theme: defaultTheme,
  logLevel: LogLevel.VERBOSE,
  presets: [UniverDocsCorePreset({ container: 'univer-host' })],
});
const unitId = 'doc_edit';
let initText = '';

function createDoc(text: string) {
  initText = text;
  const bodyText = (text || '').replace(/\r\n/g, '\n') + '\n';
  (created.univer as any).createUnit(UniverInstanceType.UNIVER_DOC, {
    id: unitId,
    body: { dataStream: bodyText },
  });
}

function getText(): string {
  try {
    const doc = (created.univerAPI as any).getActiveDoc?.();
    const snap = doc?.getSnapshot?.();
    const ds = snap?.body?.dataStream ?? '';
    return ds.replace(/\r/g, '\n').replace(/\n+$/, '');
  } catch { return initText; }
}

// 父窗口通信
window.addEventListener('message', (ev) => {
  const d = ev.data || {};
  if (d.type === 'init') {
    createDoc(d.text || '');
  } else if (d.type === 'getText') {
    (ev.source as Window)?.postMessage({ type: 'text', text: getText() }, '*');
  }
});

// 直接打开时的默认内容
if (!window.parent || window.parent === window) {
  createDoc('（条款编辑入口：请在主应用中打开）\n');
}
