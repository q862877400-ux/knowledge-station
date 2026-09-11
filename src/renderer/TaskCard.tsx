// TaskCard（F-24）：右下角固定悬浮的巡检任务小卡片。
// 契约（pipeline/02 §3）：GET /api/v1/update/batch/{batch_id} 每 1s 轮询进度（不走 SSE）；
// 无活动批次（batchId 为空）时不渲染；批次进入终态 done/failed 后停止轮询并出现关闭按钮。
import { useEffect, useRef, useState } from 'react';
import { apiFetch } from './api';

interface EngineInfo { port: string; token: string }

interface BatchProgress {
  status?: string;
  total?: number;
  checked?: number;
  red_count?: number;
  yellow_count?: number;
  green_count?: number;
  gray_count?: number;
  pending?: number | null;
  pause_reason?: string | null;
}

interface TaskCardProps {
  engine: EngineInfo | null;
  batchId: string | null;
  onClose: () => void;
}

const STATUS_TEXT: Record<string, string> = {
  pending: '排队中',
  running: '巡检中',
  paused: '已暂停',
  done: '已完成',
  failed: '失败',
};

function statusBadgeCls(status: string): string {
  if (status === 'done') return 'ok';
  if (status === 'failed') return 'warn';
  if (status === 'paused') return 'mid';
  return 'info';
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
  return body.slice(0, 160) || '请求失败';
}

export default function TaskCard({ engine, batchId, onClose }: TaskCardProps) {
  const [b, setB] = useState<BatchProgress | null>(null);
  const [err, setErr] = useState('');
  const aliveRef = useRef(false);

  useEffect(() => {
    setB(null);
    setErr('');
    if (!engine || !batchId) return;
    aliveRef.current = true;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const tick = async () => {
      let status = '';
      try {
        const res = await apiFetch(engine.port, engine.token,
          `/api/v1/update/batch/${encodeURIComponent(batchId)}`);
        const body = (await res.json()) as { code?: number; data?: BatchProgress; message?: string };
        if (!aliveRef.current) return;
        if (body.code === 200 && body.data) {
          setB(body.data);
          setErr('');
          status = String(body.data.status ?? '');
        } else {
          setErr(body.message || '进度查询失败');
        }
      } catch (e) {
        // 引擎瞬断：保留卡片，下一轮继续重试
        if (!aliveRef.current) return;
        setErr(errText(e));
      }
      if (!aliveRef.current) return;
      if (status !== 'done' && status !== 'failed') {
        timer = setTimeout(() => void tick(), 1000);
      }
    };
    void tick();
    return () => { aliveRef.current = false; if (timer) clearTimeout(timer); };
  }, [engine, batchId]);

  if (!engine || !batchId) return null;

  const status = b?.status ?? '';
  const terminal = status === 'done' || status === 'failed';
  const total = b?.total ?? 0;
  const checked = b?.checked ?? 0;
  const pct = status === 'done' ? 100 : total > 0 ? Math.round((checked / total) * 100) : 0;

  return (
    <div className="task-card" role="status" aria-live="polite">
      <div className="task-head">
        <b>🔄 更新巡检</b>
        <em className={'badge ' + statusBadgeCls(status)}>{STATUS_TEXT[status] ?? (status || '…')}</em>
        {terminal && <button className="task-x" onClick={onClose} title="关闭任务卡片">✕</button>}
      </div>
      <p className="task-line">
        {!b ? '正在获取批次进度…'
          : status === 'running'
            ? <>正在查第 {checked}/{total} 个标准</>
            : status === 'paused'
              ? <>已暂停{b?.pause_reason ? `（${b.pause_reason}）` : ''} · 已查 {checked}/{total}</>
              : status === 'done'
                ? <>巡检完成 · 共查 {checked}/{total} 个</>
                : status === 'failed'
                  ? <>巡检失败 · 已查 {checked}/{total}</>
                  : <>批次排队中 · 计划巡检 {total} 个</>}
      </p>
      <div className="task-bar"><div className="task-bar-fill" style={{ width: pct + '%' }} /></div>
      <div className="task-counts">
        <span className="tc-red" title="在用已废止/被撤回">🔴 {b?.red_count ?? 0}</span>
        <span className="tc-yellow" title="有新版发布">🟡 {b?.yellow_count ?? 0}</span>
        <span className="tc-green" title="现行有效">🟢 {b?.green_count ?? 0}</span>
        <span className="tc-gray" title="渠道查无此号">⚪ {b?.gray_count ?? 0}</span>
      </div>
      {err && <p className="task-err">⚠️ {err}</p>}
    </div>
  );
}
