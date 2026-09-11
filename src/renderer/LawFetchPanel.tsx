// 法规抓取面板（LAW_SOURCE_PLAN P2）：官方源搜索候选 → 勾选导入。
// 来源白名单在引擎侧强制（http.py check_host），前端只做交互。
import { useState } from 'react';
import { apiFetch } from './api';

interface Candidate {
  bbbs?: string; url?: string; title: string; flxz?: string;
  zdjgName?: string; gbrq?: string; sxrq?: string; sxx?: number;
  pcode?: string; source?: string; pubtime?: string; category?: string;
}

export function LawFetchPanel({ port, token, flash }: {
  port: string; token: string; flash: (m: string) => void;
}) {
  const [source, setSource] = useState('flk');
  const [query, setQuery] = useState('');
  const [effective, setEffective] = useState(true);
  const [tags, setTags] = useState('消防,法律');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [searching, setSearching] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  async function doSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setCandidates([]); setChecked(new Set()); setResults([]);
    try {
      const body = source === 'flk'
        ? { source, query: query.trim(), effective }
        : { source, query: query.trim() };
      const res = await apiFetch(port, token, '/api/v1/laws/search', {
        method: 'POST', body: JSON.stringify(body) });
      const j = await res.json();
      setCandidates(j.data ?? []);
      flash(`找到 ${j.total ?? j.data?.length ?? 0} 条候选`);
    } catch (e: any) {
      flash(`搜索失败: ${e.message}`);
    } finally { setSearching(false); }
  }

  function key(c: Candidate) { return c.bbbs || c.url || c.title; }

  function toggle(c: Candidate) {
    setChecked((prev) => {
      const next = new Set(prev);
      const k = key(c);
      if (next.has(k)) next.delete(k); else next.add(k);
      return next;
    });
  }

  async function doIngest() {
    const sel = candidates.filter((c) => checked.has(key(c)));
    if (!sel.length) { flash('请先勾选候选'); return; }
    setIngesting(true);
    setResults([]);
    const tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);
    for (const c of sel) {
      const body = source === 'flk'
        ? { source, bbbs: c.bbbs, domain_tags: tagList, reingest: false }
        : { source, url: c.url, domain_tags: tagList, reingest: false };
      try {
        const res = await apiFetch(port, token, '/api/v1/laws/ingest', {
          method: 'POST', body: JSON.stringify(body) });
        const j = await res.json();
        setResults((rs) => [...rs, { title: c.title, ...j.data }]);
      } catch (e: any) {
        setResults((rs) => [...rs, { title: c.title, status: 'error', message: e.message }]);
      }
    }
    setIngesting(false);
    flash(`导入完成 ${sel.length} 部`);
  }

  return (
    <div className="law-fetch-panel">
      <div className="law-fetch-bar">
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="flk">📗 国家法律法规数据库</option>
          <option value="govcn">📕 国务院政策文件库</option>
        </select>
        <input value={query} placeholder="关键词（如：消防法 / 安全生产）"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()} />
        <label className="law-fetch-eff">
          <input type="checkbox" checked={effective}
            onChange={(e) => setEffective(e.target.checked)} /> 仅现行有效
        </label>
        <button onClick={doSearch} disabled={searching || !query.trim()}>
          {searching ? '搜索中…' : '搜索'}
        </button>
      </div>
      {candidates.length > 0 && (
        <>
          <div className="law-fetch-cands">
            {candidates.map((c, i) => (
              <label key={i} className="law-cand">
                <input type="checkbox" checked={checked.has(key(c))}
                  onChange={() => toggle(c)} />
                <span className="law-cand-body">
                  <b>{c.title}</b>
                  <em className="law-cand-meta">
                    {source === 'flk'
                      ? `[${c.flxz}] ${c.zdjgName ?? ''} 公布${c.gbrq ?? '?'} 施行${c.sxrq ?? '?'} ${c.sxx === 3 ? '有效' : 'sxx=' + c.sxx}`
                      : `[${c.pcode || c.category || ''}] ${c.source ?? ''} ${c.pubtime ?? ''}`}
                  </em>
                </span>
              </label>
            ))}
          </div>
          <div className="law-fetch-ingest">
            <input value={tags} placeholder="领域标签（逗号分隔，如：消防,法律）"
              onChange={(e) => setTags(e.target.value)} />
            <button onClick={doIngest} disabled={ingesting || checked.size === 0}>
              {ingesting ? '导入中（MinerU 解析较慢）…' : `导入勾选项（${checked.size}）`}
            </button>
          </div>
        </>
      )}
      {results.length > 0 && (
        <div className="law-fetch-results">
          {results.map((r, i) => (
            <div key={i} className={'law-result ' + (r.status === 'ok' ? 'ok' : 'err')}>
              <b>{r.title}</b>
              {r.status === 'ok'
                ? <span> ✓ {r.total_clauses ?? '?'} 条款 / {r.pages_parsed ?? '?'} 页
                    {r.converter ? `（${r.converter}）` : ''} <code>{r.doc_id}</code></span>
                : <span> ✗ {r.message}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
