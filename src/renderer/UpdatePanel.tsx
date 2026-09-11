// UpdatePanel（F-01/F-04/F-05/F-13/F-26）：「更新」主视图（顶栏第三个功能入口）。
// 契约（pipeline/02 §3）：
// - POST /update/check 启动手动巡检批次 → onBatchStarted(batch_id) 拉起右下角 TaskCard；
// - GET /update/batches 最近批次列表，点行展开 GET /update/changes?batch_id= 变更明细（三色行）
//   + POST /update/report/{batch_id} 导出 Word 报告（经既有 /export/download 下载）；
// - 领域订阅开关：GET/PUT /api/v1/update/subscriptions（app_config 存储，缺省全开）；
// - POST /data/package/export·import 全量数据包导出/导入，成功 alert 七项简报计数。
import { useEffect, useRef, useState } from 'react';
import { apiFetch } from './api';
import DiscoverDialog from './DiscoverDialog';

interface EngineInfo { port: string; token: string }

interface BatchRow {
  batch_id: string;
  trigger_type: string;
  status: string;
  tier?: string | null;
  total: number;
  checked: number;
  red_count: number;
  yellow_count: number;
  green_count: number;
  gray_count: number;
  created_at?: string | null;
}

interface ChangeRow {
  change_id: string;
  standard_no: string;
  standard_name?: string | null;
  change_type: string;
  source_channel?: string;
  detected_at?: string;
}

interface UpdatePanelProps {
  engine: EngineInfo | null;
  /** 立即巡检成功后回调（App 据此挂载 TaskCard 轮询进度） */
  onBatchStarted: (batchId: string) => void;
}

const STATUS_LABEL: Record<string, string> = {
  pending: '排队中', running: '巡检中', paused: '已暂停', done: '已完成', failed: '失败',
};

function statusBadgeCls(status: string): string {
  if (status === 'done') return 'ok';
  if (status === 'failed') return 'warn';
  if (status === 'paused') return 'mid';
  if (status === 'running') return 'info';
  return 'gray';
}

// change_type → 三色语义（F-04：🔴在用已废止 🟡有新版 🟢现行；⚪=查无此号）
const CHANGE_META: Record<string, { icon: string; label: string }> = {
  superseded: { icon: '🔴', label: '在用已废止' },
  withdrawn: { icon: '🔴', label: '已撤回' },
  new_version: { icon: '🟡', label: '有新版' },
  no_change: { icon: '🟢', label: '无变化' },
  not_found: { icon: '⚪', label: '查无此号' },
};

function chgColorCls(changeType: string): string {
  if (changeType === 'superseded' || changeType === 'withdrawn') return 'v-red';
  if (changeType === 'new_version') return 'v-yellow';
  if (changeType === 'no_change') return 'v-green';
  return 'v-gray';
}

// F-26 简报七项（data_package.BRIEF_KEYS 冻结结构）
const BRIEF_KEYS: [string, string][] = [
  ['docs', '文档'], ['clauses', '条款'], ['annotations', '批注'], ['bookmarks', '收藏'],
  ['obligations', '义务'], ['changes', '变更'], ['announcements', '公告'],
];

function briefLine(counts: Record<string, number | undefined> | undefined): string {
  const c = counts ?? {};
  return BRIEF_KEYS.map(([k, label]) => `${label} ${c[k] ?? 0}`).join('｜');
}

// apiFetch 抛错格式为 `${status} ${text}`，text 通常为后端 JSON 错误体 → 提取 message 展示
function errText(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e);
  const m = /^\d+\s([\s\S]*)$/.exec(raw);
  const body = m ? m[1] : raw;
  try {
    const j = JSON.parse(body) as { message?: string };
    if (j && j.message) return j.message;
  } catch { /* 非 JSON 错误体，原样截断展示 */ }
  return body.slice(0, 200) || '请求失败';
}

export default function UpdatePanel({ engine, onBatchStarted }: UpdatePanelProps) {
  const [batches, setBatches] = useState<BatchRow[] | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [changes, setChanges] = useState<Record<string, ChangeRow[]>>({});
  const [checkErr, setCheckErr] = useState('');
  const [listErr, setListErr] = useState('');
  const [chgErr, setChgErr] = useState('');
  const [busyReport, setBusyReport] = useState('');       // 正在导出报告的 batch_id
  const [pkgBusy, setPkgBusy] = useState<'' | 'export' | 'import'>('');
  const [pkgErr, setPkgErr] = useState('');
  const [discOpen, setDiscOpen] = useState(false);
  // F-13 领域订阅：GET/PUT /api/v1/update/subscriptions
  const [subs, setSubs] = useState<{ tag: string; enabled: boolean }[] | null>(null);
  const [subBusy, setSubBusy] = useState(false);
  // 批量导入（pipeline/11）：POST /ingest/bulk 启动快扫 → GET 进度 → POST resume 解析
  const [bulkDir, setBulkDir] = useState('');
  const [bulkInfo, setBulkInfo] = useState<{
    batch_id: string; status: string; total: number; scanned: number;
    parsed: number; pending: number; errors: number; pause_reason?: string | null;
  } | null>(null);
  const [bulkBusy, setBulkBusy] = useState<'' | 'start' | 'resume'>('');
  const [bulkErr, setBulkErr] = useState('');
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function loadBatches() {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/update/batches?limit=10');
      setBatches(((await res.json()).data ?? []) as BatchRow[]);
      setListErr('');
    } catch (e) {
      setListErr(errText(e));
    }
  }

  async function loadSubs() {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/update/subscriptions');
      const data = (await res.json()).data as { domains: { tag: string; enabled: boolean }[] };
      setSubs(data.domains);
    } catch { setSubs([]); } // 订阅区显示"加载失败"态，不阻断主面板
  }

  async function abortBulk() {
    if (!engine || !bulkInfo) return;
    setBulkBusy('resume'); setBulkErr('');
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/ingest/bulk/${bulkInfo.batch_id}/abort`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const d = (await res.json()).data as { status: string };
      setBulkInfo({ ...bulkInfo, status: d.status });
    } catch (e) { setBulkErr(errText(e)); }
    finally { setBulkBusy(''); }
  }

  async function toggleSub(tag: string, on: boolean) {    if (!engine || !subs || subBusy) return;
    setSubBusy(true);
    try {
      const next = subs.map((d) => (d.tag === tag ? { ...d, enabled: on } : d));
      const res = await apiFetch(engine.port, engine.token, '/api/v1/update/subscriptions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: next.filter((d) => d.enabled).map((d) => d.tag) }),
      });
      const data = (await res.json()).data as { domains: { tag: string; enabled: boolean }[] };
      setSubs(data.domains);
    } catch (e) {
      setListErr('订阅保存失败：' + errText(e));
      void loadSubs(); // 回读还原
    } finally { setSubBusy(false); }
  }

  // ---- 批量导入（pipeline/11）----
  async function pollBulk(id: string) {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, `/api/v1/ingest/bulk/${id}`);
      setBulkInfo((await res.json()).data);
    } catch { /* 轮询失败静默，下轮再试 */ }
  }

  async function startBulk() {
    if (!engine) return;
    setBulkBusy('start'); setBulkErr('');
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/ingest/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ src_dir: bulkDir.trim() }),
      });
      const d = (await res.json()).data as { batch_id: string };
      setBulkInfo({ batch_id: d.batch_id, status: 'running', total: 0, scanned: 0,
        parsed: 0, pending: 0, errors: 0 });
      const timer = window.setInterval(() => {
        void pollBulk(d.batch_id);
      }, 1500);
      window.setTimeout(() => window.clearInterval(timer), 30000); // 快扫 30s 轮询窗口
    } catch (e) { setBulkErr(errText(e)); }
    finally { setBulkBusy(''); }
  }

  async function resumeBulk() {
    if (!engine || !bulkInfo) return;
    setBulkBusy('resume'); setBulkErr('');
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/ingest/bulk/${bulkInfo.batch_id}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const d = (await res.json()).data as { batch_id: string };
      const timer = window.setInterval(() => { void pollBulk(d.batch_id); }, 2000);
      window.setTimeout(() => window.clearInterval(timer), 60000);
    } catch (e) { setBulkErr(errText(e)); }
    finally { setBulkBusy(''); }
  }

  useEffect(() => { void loadBatches(); void loadSubs(); /* 引擎就绪后拉最近批次与订阅 */ }, [engine]);

  async function loadChanges(batchId: string) {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/update/changes?batch_id=${encodeURIComponent(batchId)}`);
      const rows = ((await res.json()).data ?? []) as ChangeRow[];
      setChanges((c) => ({ ...c, [batchId]: rows }));
      setChgErr('');
    } catch (e) {
      setChanges((c) => ({ ...c, [batchId]: [] }));
      setChgErr(errText(e));
    }
  }

  function toggleBatch(id: string) {
    const next = expanded !== id ? id : null;
    setExpanded(next);
    if (next && !changes[next]) void loadChanges(next);
  }

  // F-01 一键巡检：manual 批次立即返回 batch_id，后台执行；409=已有运行中的批次
  async function startCheck() {
    if (!engine) return;
    setCheckErr('');
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/update/check', {
        method: 'POST',
        body: JSON.stringify({ trigger: 'manual' }),
      });
      const d = (await res.json()).data as { batch_id?: string };
      if (d?.batch_id) onBatchStarted(d.batch_id);
      await loadBatches();
    } catch (e) {
      setCheckErr(errText(e));
    }
  }

  async function downloadByName(name: string) {
    if (!engine) return;
    const res = await apiFetch(engine.port, engine.token,
      `/api/v1/export/download?name=${encodeURIComponent(name)}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  // F-05 《更新检查报告》Word 版 → exports 目录 → 经既有下载端点取回
  async function exportReport(batchId: string) {
    if (!engine) return;
    setCheckErr('');
    setBusyReport(batchId);
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/update/report/${encodeURIComponent(batchId)}`, { method: 'POST' });
      const name = ((await res.json()).data as { name?: string }).name;
      if (name) await downloadByName(name);
    } catch (e) {
      setCheckErr(errText(e));
    } finally {
      setBusyReport('');
    }
  }

  // F-26 数据包导出：成功 alert 七项简报计数
  async function exportPackage() {
    if (!engine) return;
    setPkgErr('');
    setPkgBusy('export');
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/data/package/export', {
        method: 'POST',
        body: '{}',
      });
      const d = (await res.json()).data as {
        path?: string;
        manifest?: { counts?: Record<string, number> };
      };
      window.alert(`✅ 数据包已导出\n${d.path ?? ''}\n\n简报：${briefLine(d.manifest?.counts)}`);
    } catch (e) {
      setPkgErr(errText(e));
    } finally {
      setPkgBusy('');
    }
  }

  // F-26 数据包导入：<input type=file> 取本机路径名交后端（strict：目标库非空拒绝）
  async function importPackage(file: File | undefined) {
    if (!file || !engine) return;
    if (fileRef.current) fileRef.current.value = '';
    let srcPath = file.name;
    try { srcPath = (file as unknown as { path?: string }).path || file.name; } catch { /* 保底用文件名 */ }
    const ok = window.confirm(`确认导入数据包？导入为整体替换语义（目标库非空将被拒绝）：\n${srcPath}`);
    if (!ok) return;
    setPkgErr('');
    setPkgBusy('import');
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/data/package/import', {
        method: 'POST',
        body: JSON.stringify({ src_path: srcPath }),
      });
      const manifest = (await res.json()).data as {
        mode?: string;
        counts?: Record<string, number>;
      };
      window.alert(`✅ 数据包导入完成（${manifest.mode === 'strict' ? '严格校验' : manifest.mode ?? 'strict'}模式）\n简报：${briefLine(manifest.counts)}`);
    } catch (e) {
      setPkgErr(errText(e));
    } finally {
      setPkgBusy('');
    }
  }

  return (
    <div className="update-panel">
      <div className="upd-head">
        <b className="upd-title">🔄 更新 · 库内标准时效巡检与找标</b>
        <span className="flex-spacer" />
        <button className="upd-btn" disabled={!engine} onClick={() => setDiscOpen(true)}>🔎 找标准</button>
        <button className="upd-btn primary" disabled={!engine} onClick={() => void startCheck()}>⚡ 立即巡检</button>
      </div>
      {!engine && <p className="upd-error">引擎未连接，请先运行 scripts/dev_launcher.py 启动本地引擎。</p>}
      {checkErr && <p className="upd-error">❌ {checkErr}</p>}

      <div className="upd-card">
        <div className="upd-card-head">
          <b>📋 最近巡检批次</b>
          <span className="flex-spacer" />
          <button className="mini" onClick={() => void loadBatches()} disabled={!engine}>↻ 刷新</button>
        </div>
        {listErr && <p className="upd-error">❌ {listErr}</p>}
        {batches === null ? (
          <p className="upd-hint">加载中…</p>
        ) : batches.length === 0 ? (
          <p className="upd-hint">暂无巡检批次——点右上角「⚡ 立即巡检」，对库内全部 standard_no 到官方渠道做一次时效核查。</p>
        ) : (
          <div className="upd-batches">
            {batches.map((row) => (
              <div key={row.batch_id}>
                <div className="upd-batch-row" onClick={() => toggleBatch(row.batch_id)}>
                  <span className="toc-caret">{expanded === row.batch_id ? '▾' : '▸'}</span>
                  <span className="upd-batch-time">{row.created_at ?? ''}</span>
                  <em className={'badge ' + statusBadgeCls(row.status)}>{STATUS_LABEL[row.status] ?? row.status}</em>
                  <span className="upd-batch-trigger">
                    {row.trigger_type === 'scheduled' ? '定时' : '手动'}{row.tier ? ` · ${row.tier}` : ''}
                  </span>
                  <span className="upd-counts">
                    已查 {row.checked}/{row.total}
                    　🔴{row.red_count} 🟡{row.yellow_count} 🟢{row.green_count} ⚪{row.gray_count}
                  </span>
                </div>
                {expanded === row.batch_id && (
                  <div className="upd-changes">
                    <div className="upd-changes-head">
                      <span className="upd-hint">变更明细（🔴在用已废止 🟡有新版 🟢无变化 ⚪查无此号）</span>
                      <span className="flex-spacer" />
                      <button className="mini" disabled={busyReport === row.batch_id}
                        onClick={() => void exportReport(row.batch_id)}>
                        {busyReport === row.batch_id ? '报告生成中…' : '📄 导出 Word 报告'}
                      </button>
                    </div>
                    {chgErr && <p className="upd-error">❌ {chgErr}</p>}
                    {(changes[row.batch_id] ?? []).length === 0 ? (
                      <p className="upd-hint">{changes[row.batch_id] ? '该批次无变更事件' : '明细加载中…'}</p>
                    ) : changes[row.batch_id]!.map((ch) => (
                      <div key={ch.change_id} className="chg-row">
                        <span className={'chg-dot ' + chgColorCls(ch.change_type)}>
                          {CHANGE_META[ch.change_type]?.icon ?? '·'}
                        </span>
                        <span className="chg-no">{ch.standard_no}</span>
                        <span className="chg-name">{ch.standard_name ?? ''}</span>
                        <em className="badge gray">{CHANGE_META[ch.change_type]?.label ?? ch.change_type}</em>
                        <span className="chg-time">{ch.detected_at ?? ''}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* F-13 领域订阅：GET/PUT /api/v1/update/subscriptions；已订阅领域的标准进 tier0 高频巡检 */}
      <div className="upd-card upd-sub">
        <b>🔔 领域订阅</b>
        <p className="upd-hint">
          勾选关注的行业领域：已订阅领域的标准自动进入高频巡检（tier0），公告命中会出现在巡检结果里。
        </p>
        {!engine ? (
          <p className="upd-error">引擎未连接</p>
        ) : subs === null ? (
          <p className="upd-hint">加载中…</p>
        ) : subs.length === 0 ? (
          <p className="upd-error">订阅加载失败（引擎重启后自动恢复）</p>
        ) : (
          <div className="upd-sub-grid">
            {subs.map((d) => (
              <label key={d.tag} className="switch-toggle" title={`关注「${d.tag}」领域`}>
                <input type="checkbox" checked={d.enabled} disabled={subBusy}
                  onChange={(e) => void toggleSub(d.tag, e.target.checked)} />
                <span className="switch-track"><span className="switch-knob" /></span>
                {d.tag}
              </label>
            ))}
          </div>
        )}
      </div>

      {/* 万级批量导入（pipeline/11）：目录 → 快扫建目录 → 恢复解析 */}
      <div className="upd-card">
        <b>📥 批量导入（万级标准 PDF）</b>
        <p className="upd-hint">
          输入 PDF 目录后启动：先快扫建清单（秒级），再点「恢复解析」逐件全量入库（断点续跑、日预算 2000、
          每 5 件自动快照）。标准号首页可提取；无文本件自动进隔离区。
        </p>
        <div className="upd-actions">
          <input className="upd-dir" placeholder="例如 D:\standards\pdf"
            value={bulkDir} disabled={bulkBusy !== ''}
            onChange={(e) => setBulkDir(e.target.value)} />
          <button className="upd-btn" disabled={!engine || bulkBusy !== '' || !bulkDir.trim()}
            onClick={() => void startBulk()}>
            {bulkBusy === 'start' ? '快扫中…' : '🚀 启动导入'}
          </button>
          {bulkInfo && (
            <button className="upd-btn" disabled={bulkBusy !== '' || bulkInfo.status === 'done'}
              onClick={() => void resumeBulk()}>
              {bulkBusy === 'resume' ? '解析中…' : '▶️ 恢复解析'}
            </button>
          )}
          {bulkInfo && bulkInfo.status !== 'done' && bulkInfo.status !== 'failed' && (
            <button className="upd-btn upd-btn-danger" disabled={bulkBusy !== ''}
              onClick={() => void abortBulk()}
              title="终止后同目录可立即新建导入">
              ⏹ 终止批次
            </button>
          )}
        </div>
        {bulkInfo && (
          <p className="upd-hint">
            批次 {bulkInfo.batch_id}：{STATUS_LABEL[bulkInfo.status] ?? bulkInfo.status} ·
            扫描 {bulkInfo.scanned}/{bulkInfo.total} · 已解析 {bulkInfo.parsed} ·
            待处理 {bulkInfo.pending} · 错误 {bulkInfo.errors}
            {bulkInfo.pause_reason ? ` · ${bulkInfo.pause_reason}` : ''}
          </p>
        )}
        {bulkErr && <p className="upd-error">❌ {bulkErr}</p>}
      </div>

      <div className="upd-card">
        <b>📦 数据包备份 / 还原</b>
        <p className="upd-hint">
          全量打包知识库（文档、批注、收藏、设置等随快照带走）；导入为整体替换语义，
          目标库非空时被 strict 校验拒绝。
        </p>
        {pkgErr && <p className="upd-error">❌ {pkgErr}</p>}
        <div className="upd-actions">
          <button className="upd-btn" disabled={!engine || pkgBusy !== ''}
            onClick={() => void exportPackage()}>
            {pkgBusy === 'export' ? '导出中…' : '⬆️ 导出数据包'}
          </button>
          <button className="upd-btn" disabled={!engine || pkgBusy !== ''}
            onClick={() => fileRef.current?.click()}>
            {pkgBusy === 'import' ? '导入中…' : '⬇️ 导入数据包'}
          </button>
          <input ref={fileRef} type="file" className="upd-file"
            onChange={(e) => void importPackage(e.target.files?.[0])} />
        </div>
      </div>

      {discOpen && engine && (
        <DiscoverDialog engine={engine} onClose={() => setDiscOpen(false)} />
      )}
    </div>
  );
}
