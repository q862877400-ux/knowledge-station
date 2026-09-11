// 法规总目录面板（docs/LAW_CATALOG_ONDEMAND_PLAN.md 任务 1/3）。
// 展示 flk 全量清单（本地 law_catalog 表），点开即核验（GET /api/v1/laws/verify）
// + 按需下载入库（POST /api/v1/laws/ingest，source='flk'）。目录已入库时重复打开秒开。
import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from './api';
import ValidityBadge, { type ValidityStatus } from './ValidityBadge';

interface CatalogItem {
  title: string;
  bbbs: string;
  flxz?: string;
  sxx?: number | null;
  category?: string;
  gbrq?: string;
  sxrq?: string;
}

interface VerifyPayload {
  status: ValidityStatus;
  status_text?: string;
  evidence_url?: string;
  checked_at?: string;
  cached?: boolean;
  retryable?: boolean;
}

const SXX_TEXT: Record<number, string> = {
  1: '已废止', 2: '已修改', 3: '现行有效', 4: '尚未生效',
};

function sxxText(sxx: number): string {
  return SXX_TEXT[sxx] ?? `sxx=${sxx}`;
}

export function LawCatalogPanel({ port, token, flash, onOpenDocument }: {
  port: string;
  token: string;
  flash: (m: string) => void;
  onOpenDocument: (docId: string) => void;
}) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState<string[]>([]);
  const [q, setQ] = useState('');
  const [qInput, setQInput] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  // 核验结果缓存（bbbs -> payload）：已核验条目直接透出徽章，不重复打官方接口
  const [verifyMap, setVerifyMap] = useState<Record<string, VerifyPayload>>({});
  const [busy, setBusy] = useState<Record<string, 'verify' | 'ingest'>>({});

  const fetchCatalog = useCallback(async (params: { q?: string; category?: string }) => {
    setLoading(true);
    const sp = new URLSearchParams({ page: '1', page_size: '50' });
    if (params.q) sp.set('q', params.q);
    if (params.category) sp.set('category', params.category);
    try {
      const res = await apiFetch(port, token, `/api/v1/laws/catalog?${sp.toString()}`);
      const j = await res.json();
      setItems(j.data?.items ?? []);
      setTotal(j.data?.total ?? 0);
      setCategories(j.data?.categories ?? []);
    } catch (e: any) {
      flash(`目录加载失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [port, token, flash]);

  useEffect(() => { fetchCatalog({}); }, [fetchCatalog]);

  const doRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await apiFetch(port, token, '/api/v1/laws/catalog/refresh', { method: 'POST' });
      const j = await res.json();
      const d = j.data ?? {};
      flash(`目录已刷新：共 ${d.total ?? '?'} 部（新增 ${d.fetched ?? 0}，跳过 ${d.skipped ?? 0}）`);
      if (d.warnings?.length) {
        flash(`对账警告 ${d.warnings.length} 条：${String(d.warnings[0]).slice(0, 60)}`);
      }
      await fetchCatalog({ q, category });
    } catch (e: any) {
      flash(`目录刷新失败: ${e.message}`);
    } finally {
      setRefreshing(false);
    }
  };

  const doVerify = async (bbbs: string, force = false) => {
    if (!force && (verifyMap[bbbs] || busy[bbbs] === 'verify')) return;
    setBusy((b) => ({ ...b, [bbbs]: 'verify' }));
    try {
      const res = await apiFetch(port, token, `/api/v1/laws/verify?bbbs=${encodeURIComponent(bbbs)}`);
      const j = await res.json();
      if (j.data?.status) setVerifyMap((m) => ({ ...m, [bbbs]: j.data }));
    } catch {
      // 核验失败静默降级（不阻塞预览；徽章保持未核验态，用户可点「核验」重试）
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[bbbs]; return n; });
    }
  };

  const openLaw = async (item: CatalogItem) => {
    if (busy[item.bbbs] === 'ingest') return;
    setBusy((b) => ({ ...b, [item.bbbs]: 'ingest' }));
    void doVerify(item.bbbs);   // 并行核验（结果缓存，不阻塞打开）
    try {
      const res = await apiFetch(port, token, '/api/v1/laws/ingest', {
        method: 'POST',
        body: JSON.stringify({
          source: 'flk', bbbs: item.bbbs, domain_tags: [], reingest: false,
        }),
      });
      const j = await res.json();
      if (j.data?.status === 'ok' && j.data?.doc_id) {
        flash(`已就绪：${item.title}`);
        onOpenDocument(j.data.doc_id);
      } else {
        flash(`打开失败：${j.data?.message ?? j.data?.status ?? '未知'}`);
      }
    } catch (e: any) {
      flash(`打开失败: ${e.message}`);
    } finally {
      setBusy((b) => { const n = { ...b }; delete n[item.bbbs]; return n; });
    }
  };

  const actions = (item: CatalogItem) => {
    const v = verifyMap[item.bbbs];
    if (v) {
      return (
        <ValidityBadge
          status={v.status}
          statusText={v.status_text}
          evidenceUrl={v.evidence_url}
          checkedAt={v.checked_at}
          retryable={v.retryable}
          onRetry={() => doVerify(item.bbbs, true)}
        />
      );
    }
    return (
      <button type="button" className="law-cat-verify" onClick={() => doVerify(item.bbbs)}
        disabled={busy[item.bbbs] === 'verify'}>
        {busy[item.bbbs] === 'verify' ? '核验中…' : '核验'}
      </button>
    );
  };

  return (
    <div className="law-cat-panel">
      <div className="law-cat-bar">
        <select
          className="law-cat-select"
          value={category}
          onChange={(e) => { setCategory(e.target.value); fetchCatalog({ category: e.target.value }); }}
        >
          <option value="">全部分类</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input
          className="law-cat-search"
          value={qInput}
          placeholder="标题搜索（Enter）"
          onChange={(e) => setQInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { setQ(qInput.trim()); fetchCatalog({ q: qInput.trim() }); }
          }}
          onBlur={() => {
            const v = qInput.trim();
            if (v !== q) { setQ(v); fetchCatalog({ q: v }); }
          }}
        />
        <button className="law-cat-refresh" onClick={doRefresh} disabled={refreshing}>
          {refreshing ? '刷新中…' : '刷新目录'}
        </button>
      </div>

      <div className="law-cat-count">共 <b>{total}</b> 部法规</div>

      <div className="law-cat-list">
        {loading && <div className="law-cat-loading">加载中…</div>}
        {!loading && items.length === 0 && (
          <div className="law-cat-empty">目录为空，点击「刷新目录」从 flk 官方库全量抓取。</div>
        )}
        {!loading && items.map((it) => (
          <div key={it.bbbs} className="law-cat-row">
            <div className="law-cat-body">
              <div className="law-cat-title">{it.title}</div>
              <div className="law-cat-meta">
                <span className="law-cat-kind">[{it.flxz || it.category || '法规'}]</span>
                {it.gbrq && <span>公布 {it.gbrq}</span>}
                {it.sxrq && <span>施行 {it.sxrq}</span>}
                {it.sxx != null && <span>{sxxText(it.sxx)}</span>}
              </div>
            </div>
            <div className="law-cat-actions">
              {actions(it)}
              <button
                className="law-cat-open"
                onClick={() => openLaw(it)}
                disabled={busy[it.bbbs] === 'ingest'}
              >
                {busy[it.bbbs] === 'ingest' ? '导入中…' : '下载并打开'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
