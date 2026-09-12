// ApiConfigPanel（2026-08-27 v2；2026-09-01 v3 云解析换组）：设置→API 配置弹层。
// 云解析兜底通道（MinerU 官方云 API）：本地 MinerU 优先，本地不可用/跑不动时兜底走云。
// 红线：Key 输入框永远不回显已存值；保存后仅显示「已配置」布尔状态。
import { useEffect, useState } from 'react';
import { apiFetch, type EngineInfo } from './api';

interface ChanStatus { configured: boolean; base_url: string }
interface StatusResp { mineru_cloud: ChanStatus; llm: ChanStatus }
interface TestResult { ok: boolean; detail: string }

const EMPTY: StatusResp = {
  mineru_cloud: { configured: false, base_url: '' },
  llm: { configured: false, base_url: '' },
};

export default function ApiConfigPanel({ engine, onClose }: { engine: EngineInfo | null; onClose: () => void }) {
  const [status, setStatus] = useState<StatusResp>(EMPTY);
  const [cloudKey, setCloudKey] = useState('');
  const [cloudUrl, setCloudUrl] = useState('');
  const [llmKey, setLlmKey] = useState('');
  const [llmUrl, setLlmUrl] = useState('');
  const [busy, setBusy] = useState<'save' | 'test-cloud' | 'test-llm' | 'test-mineru_cloud' | null>(null);
  const [lastTest, setLastTest] = useState<Record<string, TestResult | null>>({ mineru_cloud: null, llm: null });
  const [err, setErr] = useState('');

  const loadStatus = async () => {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/settings/api-config');
      const j = (await res.json()) as StatusResp & { ok?: boolean };
      setStatus({ mineru_cloud: j.mineru_cloud ?? EMPTY.mineru_cloud, llm: j.llm ?? EMPTY.llm });
    } catch (e) { setErr(`读取状态失败：${(e as Error).message}`); }
  };
  useEffect(() => { void loadStatus(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const save = async () => {
    if (!engine) return;
    setBusy('save'); setErr('');
    try {
      const body: Record<string, { api_key?: string; base_url?: string }> = {};
      if (cloudKey.trim()) body.mineru_cloud = { ...(body.mineru_cloud ?? {}), api_key: cloudKey.trim() };
      if (cloudUrl.trim()) body.mineru_cloud = { ...(body.mineru_cloud ?? {}), base_url: cloudUrl.trim() === '-' ? '-' : cloudUrl.trim() };
      if (llmKey.trim()) body.llm = { ...(body.llm ?? {}), api_key: llmKey.trim() };
      if (llmUrl.trim()) body.llm = { ...(body.llm ?? {}), base_url: llmUrl.trim() === '-' ? llmUrl.trim() : llmUrl.trim() };
      const res = await apiFetch(engine.port, engine.token, '/api/v1/settings/api-config', {
        method: 'PUT', body: JSON.stringify(body),
      });
      const j = (await res.json()) as StatusResp & { ok?: boolean };
      setStatus({ mineru_cloud: j.mineru_cloud ?? EMPTY.mineru_cloud, llm: j.llm ?? EMPTY.llm });
      setCloudKey(''); setLlmKey('');
    } catch (e) { setErr(`保存失败：${(e as Error).message}`); }
    finally { setBusy(null); }
  };

  const testChannel = async (ch: 'mineru_cloud' | 'llm') => {
    if (!engine) return;
    setBusy(`test-${ch}`); setErr(''); setLastTest((p) => ({ ...p, [ch]: null }));
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/settings/api-config/test', {
        method: 'POST', body: JSON.stringify({ channel: ch }),
      });
      const j = (await res.json()) as { result: TestResult };
      setLastTest((p) => ({ ...p, [ch]: j.result }));
    } catch (e) { setLastTest((p) => ({ ...p, [ch]: { ok: false, detail: (e as Error).message } })); }
    finally { setBusy(null); }
  };

  const badge = (b: boolean) => (
    <em className={'badge ' + (b ? 'ok' : 'warn')} style={{ marginLeft: 8 }}>{b ? '✅ 已配置' : '⚠️ 未配置'}</em>
  );

  const fieldStyle = { flex: 1, padding: '4px 8px', fontSize: 13, border: '1px solid #d0d0d0', borderRadius: 6 } as React.CSSProperties;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300, background: 'rgba(20,20,28,.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div style={{
        width: 560, maxHeight: '86vh', overflowY: 'auto', background: '#fff',
        borderRadius: 12, padding: '18px 22px', boxShadow: '0 10px 40px rgba(0,0,0,.25)',
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>⚙️ API 配置</h3>
          <button className="mini" onClick={onClose}>关闭</button>
        </div>
        <p style={{ color: '#667', fontSize: 12, margin: '6px 0 12px' }}>
          Key 仅存入本机加密存储（Windows DPAPI，secrets.json），绝不入库/回显；保存立即生效，无需重启。
          导入文件时：已配置云 Key → 云解析优先、本地兜底；未配置 → 直接走本地通道（纯本地不外发）。
        </p>

        {/* ===== 云解析（已配置则优先） ===== */}
        <fieldset style={{ border: '1px solid #e2e2ea', borderRadius: 10, marginBottom: 14 }}>
          <legend><b>☁️ 云解析（MinerU 官方云 API）</b>{badge(status.mineru_cloud.configured)}</legend>
          <p style={{ color: '#889', fontSize: 12, margin: '6px 0' }}>
            配置 Key 后解析优先走云、失败自动回落本地（可设 KS_MINERU_CLOUD=0 禁用云）；
            云端返回结果会转成本地同构格式直接入库，无需额外配置。
          </p>
          <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
            <input type="password" placeholder={status.mineru_cloud.configured ? 'Key 已配置（留空保持不变）' : '官方 API Token（mineru.net 获取）'}
              value={cloudKey} onChange={(e) => setCloudKey(e.target.value)} style={fieldStyle} autoComplete="off" />
          </div>
          <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
            <input placeholder={`Base URL（当前 ${status.mineru_cloud.base_url || 'https://mineru.net'}；留空保持不变，输 "-" 恢复默认）`}
              value={cloudUrl} onChange={(e) => setCloudUrl(e.target.value)} style={fieldStyle} />
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="mini" disabled={busy !== null} onClick={() => void testChannel('mineru_cloud')}>
              {busy === 'test-mineru_cloud' ? '测试中…' : '🧪 测试连通'}
            </button>
            {lastTest.mineru_cloud && <span style={{ fontSize: 12, color: lastTest.mineru_cloud.ok ? '#177245' : '#b02a37' }}>{lastTest.mineru_cloud.ok ? '✅ ' : '❌ '}{lastTest.mineru_cloud.detail}</span>}
          </div>
        </fieldset>

        {/* ===== LLM ===== */}
        <fieldset style={{ border: '1px solid #e2e2ea', borderRadius: 10 }}>
          <legend><b>🤖 LLM 问答通道</b>{badge(status.llm.configured)}</legend>
          <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
            <input type="password" placeholder={status.llm.configured ? 'Key 已配置（留空保持不变）' : 'KS_LLM_API_KEY（兼容旧 DEEPSEEK_API_KEY）'}
              value={llmKey} onChange={(e) => setLlmKey(e.target.value)} style={fieldStyle} autoComplete="off" />
          </div>
          <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
            <input placeholder={`Base URL 覆盖（当前 ${status.llm.base_url || 'https://api.deepseek.com'}；留空保持不变，输 "-" 恢复默认）`}
              value={llmUrl} onChange={(e) => setLlmUrl(e.target.value)} style={fieldStyle} />
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button className="mini" disabled={busy !== null} onClick={() => void testChannel('llm')}>
              {busy === 'test-llm' ? '测试中…' : '🧪 测试连通'}
            </button>
            {lastTest.llm && <span style={{ fontSize: 12, color: lastTest.llm.ok ? '#177245' : '#b02a37' }}>{lastTest.llm.ok ? '✅ ' : '❌ '}{lastTest.llm.detail}</span>}
          </div>
        </fieldset>

        {err && <div style={{ marginTop: 10, color: '#b02a37', fontSize: 13 }}>{err}</div>}
        <div style={{ marginTop: 14, textAlign: 'right' }}>
          <button className="mini" disabled={busy !== null} onClick={() => void save()}>
            {busy === 'save' ? '保存中…' : '💾 保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
