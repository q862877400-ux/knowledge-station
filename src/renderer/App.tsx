import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import PdfViewer, { HighlightSpan } from './pdf/PdfViewer';
import TipTapEditor, { TipTapEditorHandle } from './TipTapEditor';
import { apiFetch, fetchPdf, saveEngineInfo } from './api';
import UpdatePanel from './UpdatePanel';
import ApiConfigPanel from './ApiConfigPanel';
import TaskCard from './TaskCard';
import { LawFetchPanel } from './LawFetchPanel';
import { LawCatalogPanel } from './LawCatalogPanel';
import { mdTablesToHtml } from './tableText';
import EvidenceCard from './EvidenceCard';
import type { PaneRect } from './EvidenceCard';
import { confBadge, renderContentHtml, renderTable, revisionTip, hideDupClauseNoHtml, cleanupDupNoSpan, dupNoMatches } from './renderHelpers';

// 图形截图 blob URL 会话级缓存（docId|figNo → blob: url，2026-08-29 fig-embed
// 填充 effect 用；同图跨重渲染/跨文档切换只拉一次，不 revoke——图就几张，量可忽略）
const figBlobCache = new Map<string, string>();

interface Annotation { annotation_id: string; content: string; annotation_type: string }
export interface Evidence {
  clause_revision_id: string; doc_id: string; clause_key: string;
  standard_no: string; clause_number: string; page_start: number;
  modality: string | null; modality_strength?: number | null; knowledge_type?: string | null;
  content_text: string; content_html?: string; patched_fields: string[];
  type_confidence?: number; is_suspicious?: boolean; user_confirmed?: boolean; bookmarked?: boolean;
  annotations?: Annotation[];
  patch_records?: PatchRecord[];
  table_md?: string;
  table_summary?: string | null;
  source_spans: { page_number: number; bbox: number[] }[];
}
interface Verification {
  is_valid: boolean;
  answer_confidence?: 'high' | 'mid' | 'low';
  confidence_reasons?: string[];
  unsupported_clauses: string[];
  unverified_numbers: { original: string; output: string }[];
  modality_violations: { source_modality: string; output_modality: string; violation_type: string }[];
  legal_element_violations: { violation: string }[];
}
interface Patch { patch_id: string; clause_revision_id: string; field_name: string; patched_value: string }
interface PatchRecord { field_name: string; patched_value: string; patch_reason: string | null; created_at: string; updated_at: string | null }
interface ChatItem { role: 'user' | 'assistant'; content: string; streaming?: boolean }
interface TreeItem { clause_number: string; title: string | null; hierarchy_path: string | null; page_start: number; level?: number }
interface OblGroup { group: string; items: { clause_revision_id: string; standard_no: string; clause_number: string; obligation_text: string; question?: string; checked: boolean }[] }

type Mode = '问答' | '审查' | '更新';
type ReviewTab = '合同审查' | '义务清单';

// 触发元素矩形快照（视口坐标）——证据卡片防遮挡定位基准（契约 §2.3/§2.4）
interface TriggerRect { left: number; top: number; width: number; height: number }
// 固定卡内存态（契约 §4：多实例、会话级，不持久化）
interface PinnedCard { id: string; ev: Evidence; x: number; y: number; z: number }

export default function App() {
  const [mode, setMode] = useState<Mode>('问答');
  const [showApiCfg, setShowApiCfg] = useState(false);
  // Task 12.4/12.5/12.7 前端项
  const [egressOpen, setEgressOpen] = useState(false);
  const [egressList, setEgressList] = useState<any[]>([]);
  const [engine, setEngine] = useState<{ port: string; token: string } | null>(null);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [timeWarnings, setTimeWarnings] = useState<string[]>([]);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [pdfBytes, setPdfBytes] = useState<ArrayBuffer | null>(null);
  const [jumpPage, setJumpPage] = useState<number | null>(null);
  const [spans, setSpans] = useState<HighlightSpan[]>([]);
  const [patches, setPatches] = useState<Patch[]>([]);
  const [patchFor, setPatchFor] = useState<Evidence | null>(null);
  const [patchText, setPatchText] = useState('');
  const [annFor, setAnnFor] = useState<Evidence | null>(null);
  const [annText, setAnnText] = useState('');
  const [toast, setToast] = useState('');
  // R60 多轮对话：历史 messages + 轮次（P9-2：localStorage 持久化，刷新不丢）
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>(() => {
    try { return JSON.parse(localStorage.getItem('ks.chat.history') ?? '[]'); } catch { return []; }
  });
  const [turnCount, setTurnCount] = useState(() => {
    try { return Number(localStorage.getItem('ks.chat.turns') ?? '0'); } catch { return 0; }
  });
  // 审查模式
  const [reviewTab, setReviewTab] = useState<ReviewTab>('合同审查');
  const [contractText, setContractText] = useState('');
  const [reviewOut, setReviewOut] = useState<string[]>([]);
  const [reviewTaskId, setReviewTaskId] = useState<string | null>(null);
  const [bizDesc, setBizDesc] = useState('');
  const [obligations, setObligations] = useState<OblGroup[]>([]);
  const [obligListId, setObligListId] = useState<string | null>(null);
  // 目录树
  const [treeOpen, setTreeOpen] = useState(false);
  const [tree, setTree] = useState<TreeItem[]>([]);
  const [treeDocId, setTreeDocId] = useState<string | null>(null);
  // 目录展开：有证据引用的标题前 ▸ → 点开显示该标题下所有条款编号（点击跳 PDF）
  const [tocExpanded, setTocExpanded] = useState<Record<string, boolean>>({});
  const [tocChildren, setTocChildren] = useState<Record<string, { clause_number: string; page_start: number }[]>>({});
  const [tocLoading, setTocLoading] = useState<Record<string, boolean>>({});
  // Phase 6：版本对比 / 更新日志 / 含已废止
  const [docs, setDocs] = useState<{ doc_id: string; standard_no: string; legal_status: string }[]>([]);
  // 当前查看文档的元数据（PDF 页首信息头：状态/发布/生效/CCS）
  const [curDocMeta, setCurDocMeta] = useState<any>(null);
  // 文件目录面板：库内文档按分类浏览（标准→CCS 大类/细分，法规→效力等级）
  const [fileNavOpen, setFileNavOpen] = useState(true);        // 面板整体折叠
  const [fileNavCats, setFileNavCats] = useState<any[]>([]);   // 分类树
  const [catOpen, setCatOpen] = useState<Record<string, boolean>>({});  // 分类展开
  const [catLoaded, setCatLoaded] = useState(false);
  // 文件目录多选批量删除（2026-08-31 用户要求；同日后端接入 POST /documents/batch-delete）：
  // catMulti 进入多选模式（条目变勾选、点击=选中而非打开）；selDocs 选中 doc_id 集合；
  // catDelPhase: null → 'confirm'（确认条）→ 'deleting'（请求中）→ 'done'（成功）| 'error'（失败可返回）
  const [catMulti, setCatMulti] = useState(false);
  const [selDocs, setSelDocs] = useState<Set<string>>(new Set());
  const [catDelPhase, setCatDelPhase] = useState<null | 'confirm' | 'deleting' | 'done' | 'error'>(null);
  const [catDelDone, setCatDelDone] = useState<{ docs: number; clauses: number } | null>(null);
  const [catDelErr, setCatDelErr] = useState('');
  const [catQuery, setCatQuery] = useState('');               // 文件目录搜索（国标名称/编号）
  const [cmpOpen, setCmpOpen] = useState(false);
  const [cmpA, setCmpA] = useState<string | null>(null);
  const [cmpB, setCmpB] = useState<string | null>(null);
  const [cmpResult, setCmpResult] = useState<any>(null);
  const [logOpen, setLogOpen] = useState(false);
  const [opLog, setOpLog] = useState<{ event_type: string; created_at: string; target_id: string }[]>([]);
  const [includeSuperseded, setIncludeSuperseded] = useState(false);
  // Phase 7：差距分析
  const [gapTab, setGapTab] = useState(false);
  const [policyText, setPolicyText] = useState('');
  const [policyName, setPolicyName] = useState('');
  const [gapResult, setGapResult] = useState<any>(null);
  // Phase 9.2：查询理解层
  const [clarify, setClarify] = useState<{ questions: string[]; hint?: string; detected_slots?: any } | null>(null);
  const [queryMode, setQueryMode] = useState('default');
  const [answerScope, setAnswerScope] = useState<'concise' | 'full'>('concise');
  // Phase 8：运维面板
  const [opsOpen, setOpsOpen] = useState(false);
  const [healthBoard, setHealthBoard] = useState<any>(null);
  const [dumps, setDumps] = useState<any[]>([]);
  // 阶段六批次6：更新模块——活动巡检批次 id（非空时右下角 TaskCard 以 1s 轮询展示进度）
  const [updBid, setUpdBid] = useState<string | null>(null);

  const sseRef = useRef<AbortController | null>(null);
  const answerRef = useRef('');   // delta 累积（R60 历史记录用，避免 setState 异步竞态）
  const evidencesRef = useRef<Evidence[]>([]);  // 自动跳首个引用用（避免 setState 异步）
  const [hoverEv, setHoverEv] = useState<{ ev: Evidence; trigger: TriggerRect; anchor: { x: number; y: number } } | null>(null);
  const [fading, setFading] = useState(false);
  // 证据卡面板坐标系（契约 §2.1）：实时跟踪 .left 矩形（窗口缩放/分割条拖动都反映到这里）
  const [paneRect, setPaneRect] = useState<PaneRect | null>(null);
  // 固定卡图层（契约 §4）：多实例、内存级，不持久化
  const [pinnedCards, setPinnedCards] = useState<PinnedCard[]>([]);
  const floatPosRef = useRef<{ x: number; y: number } | null>(null);   // 浮动卡最近渲染位置（📌 转固定用）
  // 纠错编辑器：左半边切换为 Univer Office 界面
  const [editingEv, setEditingEv] = useState<Evidence | null>(null);
  // Task 12.1 Office 往返编辑：导出 docx → 本机 Word/WPS 编辑 → 轮询解析 → 确认落库
  const [officeSession, setOfficeSession] = useState<any>(null);   // {session_id, has_changes, rejected_reason, proposed}
  const [officeErr, setOfficeErr] = useState<string | null>(null);
  const officeTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [qIssues, setQIssues] = useState<any[] | null>(null);
  const [qOpen, setQOpen] = useState(false);
  const editorRef = useRef<TipTapEditorHandle | null>(null);
  const chatRef = useRef<HTMLDivElement | null>(null);   // 聊天列表滚动锚点（编辑返回后滚到底部）
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [stdNos, setStdNos] = useState<string[]>([]);
  const resolveCache = useRef<Record<string, Evidence>>({});
  // 微信式聊天记录：提问+回答气泡（localStorage 持久化，刷新不丢）
  const [chatItems, setChatItems] = useState<ChatItem[]>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem('ks.chat.history') ?? '[]');
      return (Array.isArray(raw) ? raw : []).map((m: any) => ({ role: m.role, content: m.content }));
    } catch { return []; }
  });
  const chatStreamIdx = useRef<number>(-1);   // 当前流式回答所在 chatItems 下标
  // 分割线拖动：左栏宽度（px，null=默认 40%）
  const [splitW, setSplitW] = useState<number | null>(null);
  const dragRef = useRef<{ startX: number; startW: number } | null>(null);

  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault();
    const ws = document.querySelector('.workspace') as HTMLElement;
    const left = document.querySelector('.left') as HTMLElement;
    if (!ws || !left) return;
    dragRef.current = { startX: e.clientX, startW: splitW ?? left.getBoundingClientRect().width };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const w = Math.min(Math.max(dragRef.current.startW + ev.clientX - dragRef.current.startX, 280),
        ws.getBoundingClientRect().width - 360);
      setSplitW(w);
    };
    const onUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  // 右栏内部分栏可拖动：文件目录 / PDF目录 抽屉宽度（px，null=默认 176 紧凑）
  const [fileW, setFileW] = useState<number | null>(null);
  const [tocW, setTocW] = useState<number | null>(null);
  const startVResize = (ev: React.MouseEvent, which: 'file' | 'toc') => {
    ev.preventDefault();
    const startX = ev.clientX;
    const startW = which === 'file' ? (fileW ?? 176) : (tocW ?? 176);
    const onMove = (e: MouseEvent) => {
      const next = Math.min(Math.max(startW + e.clientX - startX, 150), 460);
      if (which === 'file') setFileW(next); else setTocW(next);
    };
    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  useEffect(() => {
    (async () => {
      // 引擎自动重连：依次探测 preload / URL 参数 / localStorage / vite env，
      // 取第一个健康可用的。URL 参数（?engine_port=&engine_token=）供 web 模式
      // 引擎重启后一键换绑（2026-08-29）：探测通过才写入 localStorage，并用
      // replaceState 从地址栏抹掉参数（token 不留历史/分享链接）。
      const q = new URLSearchParams(window.location.search);
      const qPort = q.get('engine_port') || '';
      const qToken = q.get('engine_token') || '';
      if (qPort && qToken) {
        window.history.replaceState({}, '', window.location.pathname);
      }
      let info: { port: string; token: string } | null = null;
      try { info = await (window as any).engine?.getInfo(); } catch { /* 非 Electron */ }
      // web dev 模式：问 vite 要当前引擎 session（vite.config configureServer 读
      // engine.session.json）——引擎重启轮换端口/token 后刷新页面即可自动换绑。
      let viteSession: { port?: string; token?: string } | null = null;
      try {
        const r = await fetch('/__engine_session');
        if (r.ok) viteSession = await r.json();
      } catch { /* 非 dev / vite 未带中间件 */ }
      const candidates = [
        { port: qPort, token: qToken },
        { port: viteSession?.port || '', token: viteSession?.token || '' },
        { port: info?.port || '', token: info?.token || '' },
        { port: localStorage.getItem('engine.port') || '', token: localStorage.getItem('engine.token') || '' },
        { port: import.meta.env.VITE_ENGINE_PORT || '', token: import.meta.env.VITE_ENGINE_TOKEN || '' },
      ].filter((c) => c.port && c.token);
      for (const c of candidates) {
        try {
          const res = await fetch(`http://127.0.0.1:${c.port}/api/v1/health`, {
            headers: { Authorization: `Bearer ${c.token}` } });
          if (res.ok) { saveEngineInfo(c); setEngine(c); return; }
        } catch { /* 探测失败，尝试下一个 */ }
      }
      if (candidates[0]) { saveEngineInfo(candidates[0]); setEngine(candidates[0]); }
    })();
  }, []);

  function flash(msg: string) { setToast(msg); setTimeout(() => setToast(''), 2500); }

  async function refreshPatches() {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/clauses/patches');
      setPatches((await res.json()).data ?? []);
    } catch { /* 引擎未起 */ }
  }
  useEffect(() => { if (engine) void refreshPatches(); }, [engine]);
  // 文件目录：引擎就绪后自动加载（修复"刚打开是空的，要关闭再打开才出来"）
  useEffect(() => { if (engine && !catLoaded) void loadFileNav(); }, [engine, catLoaded]);

  // 编辑态/Office 会话 → 返回聊天时，默认滚到底部（最新消息），不回到顶部（用户实测反馈 2026-08-23）
  useEffect(() => {
    if (editingEv === null && officeSession === null) {
      // 仅在"从编辑/Office 返回"时滚动（避免初始挂载/清空时误滚）
      const el = chatRef.current;
      if (el) requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
    }
  }, [editingEv === null, officeSession === null]);

  // Esc 关闭一切浮层（模态/浮动面板）；浮动证据卡一并关闭，固定卡不受影响（契约 §4）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpsOpen(false); setCmpOpen(false); setLogOpen(false);
        setPatchFor(null); setAnnFor(null);
        setEgressOpen(false);
        setHoverEv(null);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // 面板矩形跟踪（契约 §2.1）：ResizeObserver + 窗口 resize，覆盖分割条拖动后的尺寸变化
  useEffect(() => {
    const el = document.querySelector('.left') as HTMLElement | null;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setPaneRect({ left: r.left, top: r.top, width: r.width, height: r.height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener('resize', measure);
    return () => { ro.disconnect(); window.removeEventListener('resize', measure); };
  }, []);

  // Task 12.7 外发审计：拉取记录 + 导出
  async function openEgress() {
    setEgressOpen(true);
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/egress/audit?limit=50');
      const j = await res.json();
      setEgressList(j.data?.items ?? []);
    } catch { /* 引擎未起 */ }
  }
  async function exportEgress() {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/egress/audit/export');
      const data = (await res.json()).data;
      await downloadFile(data.name);
    } catch { /* 忽略 */ }
  }

  // 标准号列表：回答内所有「标准号-条款号」编号链接化用
  useEffect(() => {
    if (!engine) return;
    (async () => {
      try {
        const res = await apiFetch(engine.port, engine.token, '/api/v1/documents');
        const data = (await res.json()).data ?? [];
        setStdNos(data.map((d: any) => d.standard_no).filter(Boolean));
      } catch { /* 引擎未起 */ }
    })();
  }, [engine]);

  // 引用兜底：标准号+条款号 → 条款详情（resolve 接口，未进证据列表的引用可悬停/点击）
  async function resolveEv(standard_no: string, clause_number: string): Promise<Evidence | null> {
    if (!engine) return null;
    const key = standard_no + '|' + clause_number;
    if (resolveCache.current[key]) return resolveCache.current[key];
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/clauses/resolve?standard_no=${encodeURIComponent(standard_no)}&clause_number=${encodeURIComponent(clause_number)}`);
      const body = await res.json();
      if (body.code !== 200 || !body.data) return null;
      resolveCache.current[key] = body.data as Evidence;
      return body.data as Evidence;
    } catch { return null; }
  }

  // 卡片延迟消失：移开 0.5s 渐隐；鼠标在卡片上保持显示
  // trigger=触发链接矩形快照：异步 resolve 返回后仍用它定位（元素可能已移除，契约 §2.4）
  const showCard = (ev: Evidence, trigger: TriggerRect, anchor: { x: number; y: number }) => {
    // 已固定该证据：不再生成新浮动卡（用户：拖/固定后，同一证据链接不再产生新卡片）
    if (pinnedCards.some((c) => c.ev.clause_revision_id === ev.clause_revision_id)) return;
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setFading(false);
    setHoverEv({ ev, trigger, anchor });
  };
  const scheduleHide = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => {
      setFading(true);
      hideTimer.current = setTimeout(() => { setHoverEv(null); setFading(false); }, 500);
    }, 500);
  };
  // 鼠标进入浮动卡：取消渐隐计时（悬停保持）
  const keepFloatCard = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setFading(false);
  };

  // ===== 固定卡（契约 §4）=====
  // 新固定卡级联定位：与已有固定卡错开 +24px；越界回绕到面板左上 8,8 起
  const cascadePos = (candidate: { x: number; y: number }, cards: PinnedCard[], pane: PaneRect) => {
    let { x, y } = candidate;
    const hits = () => cards.some((c) => Math.abs(c.x - x) < 32 && Math.abs(c.y - y) < 32);
    for (let i = 0; i < 128 && hits(); i++) {
      x += 24; y += 24;
      if (x + 340 > pane.left + pane.width - 8 || y + 360 > pane.top + pane.height - 8) {
        x = pane.left + 8; y = pane.top + 8;
      }
    }
    return { x, y };
  };
  // 浮动卡 📌 → 转固定卡：位置 = 当前卡片位置（与已有卡重叠时级联错开）
  const pinFloatingCard = () => {
    if (!hoverEv) return;
    const cur = hoverEv.ev;
    setPinnedCards((cards) => {
      const pane = paneRect ?? { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight };
      const candidate = floatPosRef.current ?? { x: pane.left + pane.width / 2 - 200, y: pane.top + 60 };
      const p = cascadePos(candidate, cards, pane);
      const maxZ = cards.reduce((m, c) => Math.max(m, c.z), 949);
      return [...cards, { id: 'pin-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6), ev: cur, x: p.x, y: p.y, z: maxZ + 1 }];
    });
    setHoverEv(null);
  };
  const removePinned = (id: string) => setPinnedCards((cards) => cards.filter((c) => c.id !== id));
  // 最近交互（mousedown）的固定卡置顶
  const bringPinnedToFront = (id: string) => {
    setPinnedCards((cards) => {
      const maxZ = cards.reduce((m, c) => Math.max(m, c.z), 949);
      const me = cards.find((c) => c.id === id);
      if (!me || me.z === maxZ) return cards;
      return cards.map((c) => (c.id === id ? { ...c, z: maxZ + 1 } : c));
    });
  };

  // 统一文档加载入口（文件目录/证据卡片共用）：
  // 拉 PDF + 更新 treeDocId + 清空并重拉右侧文档目录（修复"换文档后目录不更新"）
  // 法规文本直灌文档（law-text://inline）无 PDF 原页：fetchPdf 返回 null → 清空 PDF 区并照常加载目录，
  // PDF 区显示占位说明（用户仍可用右侧目录浏览条文结构、在问答中检索引用）
  const [lawNoPdf, setLawNoPdf] = useState(false);
  // 文档全文富文本（页级文本预览主视图） + 看原件 PDF 浮层开关
  const [fullClauses, setFullClauses] = useState<any[]>([]);
  const [fullLoaded, setFullLoaded] = useState(false);   // false=请求在途 true=已应答（含空结果）
  const [showOriginal, setShowOriginal] = useState(false);
  // 全文档窗口编辑（Word 式）：editingWord=true 时全文可编辑，保存走补丁+校验
  const [editingWord, setEditingWord] = useState(false);
  // 当前证据卡要定位到的条款（点证据卡后滚动全文富文本到该条款）
  const [pendingEvCid, setPendingEvCid] = useState<string | null>(null);
  const loadingDocRef = useRef<string | null>(null);
  async function loadDocument(docId: string, jump?: number | null) {
    if (!engine || loadingDocRef.current === docId) return;
    loadingDocRef.current = docId;
    try {
      const bytes = await fetchPdf(engine.port, engine.token, docId);
      setLawNoPdf(!bytes);   // 无原页 = 法规直灌文档
      if (bytes) setPdfBytes(bytes);
      else setPdfBytes(null);
      setTreeDocId(docId);
      setJumpPage(jump ?? 1);
      setShowOriginal(false); setFullClauses([]); setFullLoaded(false);
      // 换文档必须重拉右侧目录（旧目录不随文档自动更新——用户反馈 bug）
      setTree([]);
      try {
        const res = await apiFetch(engine.port, engine.token, `/api/v1/documents/${docId}/tree`);
        const body = await res.json();
        setTree(body.code === 200 ? (body.data ?? []) : []);
      } catch { setTree([]); }
      // 全文富文本（主视图）：文档全条款，按 page_start 聚合页级文本
      try {
        const res2 = await apiFetch(engine.port, engine.token, `/api/v1/documents/${docId}/clauses`);
        const b2 = await res2.json();
        setFullClauses(b2.code === 200 ? (b2.data?.clauses ?? []) : []);
      } catch { setFullClauses([]); }
      finally { setFullLoaded(true); }   // 优雅降级：空结果也标记"已加载"，不再无限转圈
      // 文档元数据（表头：名称/状态/发布/生效/废止）——点文件目录或证据卡都要跟当前文档
      try {
        const r3 = await apiFetch(engine.port, engine.token, '/api/v1/documents');
        const b3 = await r3.json();
        const meta = (b3.data ?? []).find((x: any) => x.doc_id === docId);
        if (meta) setCurDocMeta(meta);
      } catch { /* 保留已有表头 */ }
      setTocExpanded({}); setTocChildren({});
      if (jump) setJumpPage(jump);
      setTreeOpen(true);
    } catch { /* 引擎未起 */ }
    finally { loadingDocRef.current = null; }
  }
  // 调试 harness 专用：暴露 loadDocument 供外部(browser4 eval)直接打开文档，
  // 绕开文件目录导航，服务逐页排版校验。对产品行为零影响。
  useEffect(() => {
    (window as any).__ksOpenDoc = (docId: string) => loadDocument(docId);
  });
  const fulltextRef = useRef<HTMLDivElement | null>(null);
  // 连续滚动同步源（2026-09-02）：预览滚动 → 原件实时跟随（单向，原件滚动不回写）。
  // useCallback 固定标识，避免 App 每次重渲染都重挂 PdfViewer 的 scroll 监听。
  const getSyncSource = useCallback(() => fulltextRef.current, []);
  // 点证据卡 → 全文富文本滚动到该证据所在条款（并短暂高亮）
  useEffect(() => {
    if (!pendingEvCid) return;
    const el = fulltextRef.current?.querySelector(`.fulltext-clause[data-clause-id="${pendingEvCid}"]`);
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'auto' });   // 卡片条款滚到屏幕正中
      el.classList.add('fulltext-active');
      setTimeout(() => el.classList.remove('fulltext-active'), 1600);
      setPendingEvCid(null);
    }
  }, [fullClauses, pendingEvCid]);
  useEffect(() => {
    // 标题目录点击 → 全文预览把对应条款滚到屏幕正中（2026-08-31 用户要求；
    // 不再要求先开「🔍 看原件」——全文是主预览，恒应响应目录跳转）
    const el = fulltextRef.current?.querySelector(`.fulltext-clause[data-page="${jumpPage}"]`);
    if (el) el.scrollIntoView({ block: 'center', behavior: 'auto' });
  }, [jumpPage, showOriginal, fullClauses]);
  // 图形/公式/插图内嵌截图填充（2026-08-29，GB/T 34406 图1/图A.1/图A.2 + 式(1)/(2)
  // 实测，语料级；2026-09-01 C2 增 asset-embed）：服务端注入无 src 占位
  // （fig-embed / formula-embed / asset-embed）——/figure /formula /assets 受
  // Bearer token 保护，<img src> 裸请求必 401；effect 用带 token 的 fetch 拉
  // blob 填 src（blob URL 会话级缓存，同图只拉一次）；404/网络失败 → 隐藏
  // 占位（无图无公式文档零破图）。全文列表恒渲染（showOriginal 只控 PDF 侧栏），
  // 不设 showOriginal 门控。
  useEffect(() => {
    if (!engine || !treeDocId) return;
    const imgs = Array.from(
      fulltextRef.current?.querySelectorAll(
        'img.fig-embed[data-fig]:not([src]), img.formula-embed[data-fno]:not([src]), img.asset-embed[data-asset]:not([src]), img.table-embed[data-tbl]:not([src])') ?? []) as HTMLImageElement[];
    if (!imgs.length) return;
    let alive = true;
    (async () => {
      for (const im of imgs) {
        const isFormula = im.classList.contains('formula-embed');
        const isAsset = im.classList.contains('asset-embed');
        const isTable = im.classList.contains('table-embed');
        const key = treeDocId + '|' + (isAsset
          ? `A|${im.getAttribute('data-asset') || ''}`
          : isFormula
          ? `F|${im.getAttribute('data-clause') || ''}|${im.getAttribute('data-fno') || ''}`
          : isTable
          ? `T|${im.getAttribute('data-page') || ''}|${im.getAttribute('data-tbl') || ''}`
          : (im.getAttribute('data-fig') || ''));
        const sub = isAsset
          ? `assets/${im.getAttribute('data-asset') || ''}`
          : isFormula
          ? `formula/${encodeURIComponent(im.getAttribute('data-fno') || '')}?clause=${encodeURIComponent(im.getAttribute('data-clause') || '')}`
          : isTable
          ? `table-image/${encodeURIComponent(im.getAttribute('data-page') || '')}/${encodeURIComponent(im.getAttribute('data-tbl') || '')}`
          : `figure/${encodeURIComponent(im.getAttribute('data-fig') || '')}`;
        let url = figBlobCache.get(key);
        if (!url) {
          try {
            const res = await apiFetch(engine.port, engine.token,
              `/api/v1/documents/${treeDocId}/${sub}`);
            if (!res.ok) { if (alive) im.style.display = 'none'; continue; }
            // 2026-09-02 原版比例还原（用户契约：截图尺寸/位置与原件一致）：
            // 服务端按 bbox/页宽返回 X-Frac-*，此处还原为相对正文宽度百分比
            // 与水平缩进 → 截图在预览里与原件同尺寸、同位（无头走默认 CSS）。
            const fw = parseFloat(res.headers.get('X-Frac-W') || '');
            const fx0 = parseFloat(res.headers.get('X-Frac-X0') || '');
            if (fw > 0 && fw <= 1 && !Number.isNaN(fx0)) {
              im.style.maxWidth = 'none';
              im.style.width = `${(fw * 100).toFixed(2)}%`;
              im.style.marginLeft = `${(fx0 * 100).toFixed(2)}%`;
              im.style.marginRight = '0';
              im.style.height = 'auto';
            }
            url = URL.createObjectURL(await res.blob());
            figBlobCache.set(key, url);
          } catch { if (alive) im.style.display = 'none'; continue; }
        }
        if (!alive) continue;
        im.src = url;
      }
    })();
    return () => { alive = false; };
  }, [engine, fullClauses, treeDocId]);
  // 式中 hat/bar 符号 KaTeX 渲染（2026-08-29 用户点名"特殊符号用专门的插件
  // 渲染"）：服务端把 ^Ci / C̄i 转 span.katex-sym[data-tex]（content_text 零
  // 污染，span 内保留原 token 作 fallback）；此处 katex.renderToString 出真
  // 排版（\hat{C}_i 宽帽 + 正确下标），渲染失败保留原 token 文本（渐进增强）。
  // 处理即移除 data-tex → 天然幂等，重渲染新挂载的 span 才会再处理。
  useEffect(() => {
    const spans = Array.from(
      document.querySelectorAll<HTMLSpanElement>('span.katex-sym[data-tex], span.katex-formula[data-tex]'));
    if (!spans.length) return;
    for (const el of spans) {
      const tex = el.getAttribute('data-tex');
      if (!tex) continue;
      el.removeAttribute('data-tex');
      const isFormula = el.classList.contains('katex-formula');
      try {
        // 2026-09-02 KaTeX 兼容清洗：OCR 逐字产物的 \mathrm{~d~}（~宽松空格在
        // \mathrm 内非法）→ \mathrm{d}；编号公式（含 \tag{166}）用 displayMode
        // 使编号右置（1032 大量公式此前 rrenderToString 抛错 → 全部 raw 直显）。
        const t2 = tex.replace(
          /\\mathrm\{~([^}]*?)~\}/g,
          (m, s) => '\\mathrm{' + s.replace(/~/g, '') + '}');
        const displayY = isFormula && /\\tag\{/.test(t2);
        const rendered = katex.renderToString(t2, {
          throwOnError: false,
          displayMode: displayY,
        });
        el.innerHTML = rendered;
        el.classList.add('katex-done');
        // 2026-09-02 公式整段：display 数学块（编号右置）或行内（句中紧跟）
        if (isFormula) {
          const k = el.querySelector('.katex');
          if (k) k.classList.add(displayY ? 'katex-display-formula' : 'katex-inline-formula');
        }
      } catch { /* 保留原 token 文本 */ }
    }
  }, [fullClauses, treeDocId, showOriginal]);
  // 重新拉全文（保存后刷新）
  async function refreshFull() {
    if (!engine || !treeDocId) return;
    try {
      const res = await apiFetch(engine.port, engine.token, `/api/v1/documents/${treeDocId}/clauses`);
      const b = await res.json();
      setFullClauses(b.code === 200 ? (b.data?.clauses ?? []) : []);
    } catch { /* keep */ }
    finally { setFullLoaded(true); }
  }
  // 图形点击放大（2026-08-29 散点图/流程图查看增强）：事件委托绑全文容器，
  // 点中 img.fig-embed → 拉高清版（dpi=240）弹全屏 overlay，点击任意处关闭
  const [figZoom, setFigZoom] = useState<{ url: string; loading: boolean } | null>(null);
  const figZoomRef = useRef(figZoom);
  figZoomRef.current = figZoom;
  useEffect(() => {
    const root = fulltextRef.current;
    if (!root || !engine || !treeDocId) return;
    const onClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      const im = t.closest?.('img.fig-embed, img.formula-embed, img.table-embed') as HTMLImageElement | null;
      if (!im || !im.src) return;
      e.preventDefault(); e.stopPropagation();
      setFigZoom({ url: im.src, loading: true });
      const isFormula = im.classList.contains('formula-embed');
      const isTable = im.classList.contains('table-embed');
      const sub = isFormula
        ? `formula/${encodeURIComponent(im.getAttribute('data-fno') || '')}?clause=${encodeURIComponent(im.getAttribute('data-clause') || '')}&dpi=240`
        : isTable
        ? `table-image/${encodeURIComponent(im.getAttribute('data-page') || '')}/${encodeURIComponent(im.getAttribute('data-tbl') || '')}?dpi=240`
        : `figure/${encodeURIComponent(im.getAttribute('data-fig') || '')}?dpi=240`;
      const cap = im.getAttribute('alt') || '';
      apiFetch(engine.port, engine.token,
        `/api/v1/documents/${treeDocId}/${sub}`)
        .then((r) => (r.ok ? r.blob() : Promise.reject(r.status)))
        .then((b) => { if (figZoomRef.current) setFigZoom({ url: URL.createObjectURL(b), loading: false }); })
        .catch(() => { if (figZoomRef.current) setFigZoom({ url: im.src, loading: false }); });
      void cap;
    };
    root.addEventListener('click', onClick, true);
    return () => root.removeEventListener('click', onClick, true);
  }, [engine, treeDocId, fullClauses]);
  // 全文档窗口保存：逐条款对比编辑后内容 → 补丁(带校验)落库
  async function saveWordEdit() {
    if (!engine || !editingWord || !fulltextRef.current) return;
    const blocks = fulltextRef.current.querySelectorAll('.fulltext-clause');
    let saved = 0;
    for (const blk of Array.from(blocks)) {
      const cid = blk.getAttribute('data-clause-id');
      if (!cid) continue;
      const body = blk.querySelector('.fulltext-body');
      const newText = (body?.textContent ?? '').trim();
      // 渲染层注入的"重复编号隐藏 span"在保存前还原为裸文本（编号重复通用展示规则，
      // 2026-08-29）——落库数据保持与库内原文同形态，span 永不进库
      const newHtml = cleanupDupNoSpan(body?.innerHTML ?? '');
      const orig = fullClauses.find((c) => c.clause_revision_id === cid);
      if (!orig) continue;
      if (!newText) { flash('条款内容不能为空（' + (orig.clause_number || '') + '）'); return; }
      // 规范化比较（去空白）：contenteditable 渲染后的空白与库内原文可能有差异，不能当改动
      const norm = (s: string) => (s || '').replace(/\s+/g, '');
      if (norm(newText) === norm(orig.content_text)) continue;   // 无实质改动跳过
      const okText = await postPatch(cid, 'content_text', newText, '窗口纠错');
      if (!okText) { flash('保存被拒绝/取消（' + (orig.clause_number || '') + '）'); return; }
      if (newHtml) {
        const okMd = await postPatch(cid, 'content_markdown', newHtml, '窗口纠错(富文本)');
        if (!okMd) return;
      }
      saved++;
    }
    setEditingWord(false);
    await refreshFull();
    flash(saved ? `已修正 ${saved} 处（含校验）` : '无改动');
  }

  async function openEvidence(ev: Evidence) {
    if (!engine) return;
    // 2026-08-26：跳转页 = 高亮 span 所在页（source_spans[0].page_number），
    // 不再用 page_start——多页条款/span 排序不同时两者不一致会导致"跳了但没有高亮"（实测反馈）。
    const targetPage = ev.source_spans[0]?.page_number ?? ev.page_start;
    setSpans(ev.source_spans.slice(0, 1).map((s) => ({
      page_number: s.page_number,
      bbox: s.bbox as [number, number, number, number],
      cid: ev.clause_revision_id,
      clauseNumber: ev.clause_number,
    })));
    setHoverEv(null);
    // 点证据卡 → 右侧全文富文本滚动定位到该证据所在条款（pendingEvCid 触发）
    setPendingEvCid(ev.clause_revision_id);
    // 同文档只跳页；换文档走统一加载（含目录重拉）
    if (treeDocId !== ev.doc_id || !pdfBytes) {
      await loadDocument(ev.doc_id, targetPage);
      // 换文档后 spans 是独立 state，保留；跳转页由 loadDocument 设置
    } else {
      setJumpPage(targetPage);
    }
  }

  async function toggleBookmark(ev: Evidence) {
    if (!engine) return;
    if (ev.bookmarked) {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/bookmarks');
      const list = (await res.json()).data as { bookmark_id: string; clause_key: string }[];
      const hit = list.find((b) => b.clause_key === ev.clause_key);
      if (hit) await apiFetch(engine.port, engine.token, `/api/v1/bookmarks/${hit.bookmark_id}`, { method: 'DELETE' });
      flash('已取消收藏');
    } else {
      await apiFetch(engine.port, engine.token, '/api/v1/bookmarks', {
        method: 'POST', body: JSON.stringify({ clause_key: ev.clause_key }) });
      flash('已收藏（后续检索加权）');
    }
    setEvidences((es) => es.map((e) => e.clause_revision_id === ev.clause_revision_id
      ? { ...e, bookmarked: !e.bookmarked } : e));
  }

  async function submitAnnotation() {
    if (!engine || !annFor || !annText.trim()) return;
    await apiFetch(engine.port, engine.token, '/api/v1/annotations', {
      method: 'POST', body: JSON.stringify({ clause_key: annFor.clause_key, content: annText }) });
    setEvidences((es) => es.map((e) => e.clause_revision_id === annFor.clause_revision_id
      ? { ...e, annotations: [...(e.annotations ?? []), { annotation_id: `local-${Date.now()}`, content: annText, annotation_type: 'personal' }] } : e));
    setAnnFor(null); setAnnText('');
    flash('批注已保存');
  }

  // 人工可信/存疑切换（补丁层覆写，可撤销）
  // 语义：建议核对 → 用户核对无误 → 标为可信（后台联动 is_suspicious=false + user_confirmed=true，
  // 徽章变 ✅ 已核对）；高可信/已核对 → 可标为存疑；存疑 → 标为可信。
  async function toggleVerdict(ev: Evidence) {
    if (!engine) return;
    let nextTrusted: boolean;
    if (ev.is_suspicious) nextTrusted = true;
    else if (ev.user_confirmed) nextTrusted = false;
    else nextTrusted = (ev.type_confidence ?? 1) < 0.85; // 建议核对→可信；高可信→存疑
    const reason = nextTrusted ? '人工核对确认' : '人工标存疑';
    const patch = async (field: string, value: string) => {
      try {
        await apiFetch(engine.port, engine.token, '/api/v1/clauses/patches', {
          method: 'POST',
          body: JSON.stringify({ clause_revision_id: ev.clause_revision_id,
            field_name: field, patched_value: value, patch_reason: reason }),
        });
      } catch { /* 引擎未起 */ }
    };
    await patch('is_suspicious', String(!nextTrusted));
    await patch('user_confirmed', String(nextTrusted));
    const next = { ...ev, is_suspicious: !nextTrusted, user_confirmed: nextTrusted,
      type_confidence: nextTrusted ? Math.max(ev.type_confidence ?? 1, 0.9) : ev.type_confidence };
    setEvidences((es) => es.map((e) => e.clause_revision_id === ev.clause_revision_id ? next : e));
    setHoverEv((h) => h && h.ev.clause_revision_id === ev.clause_revision_id ? { ...h, ev: next } : h);
    flash(nextTrusted ? '✅ 已核对，标为可信（后台同步）' : '已标为存疑');
  }
  // 卡片操作按钮文案：建议核对 → 已核对标为可信；其余按状态
  const verdictLabel = (ev: Evidence) => {
    if (ev.is_suspicious) return '🔓 标为可信';
    if (ev.user_confirmed) return '⚠ 标为存疑';
    return (ev.type_confidence ?? 1) < 0.85 ? '✅ 已核对，标为可信' : '⚠ 标为存疑';
  };

  // 提交单个补丁（含防乱检测交互）：
  // 422 = 拒绝（与原文无关/乱码）→ 红色提示，不落库
  // 466 = 可疑（长度/语言突变）→ confirm 二次确认后 force 重发
  async function postPatch(clauseId: string, field: string, value: string, reason: string): Promise<boolean> {
    if (!engine) return false;
    const send = (force: boolean) => apiFetch(engine.port, engine.token, '/api/v1/clauses/patches', {
      method: 'POST',
      body: JSON.stringify({ clause_revision_id: clauseId, field_name: field,
        patched_value: value, patch_reason: reason, force }),
    });
    let res = await send(false);
    let body = await res.json();
    if (body.code === 466) {
      const ok = window.confirm('⚠️ 检测到可疑修改：\n\n' + (body.data?.warnings ?? []).map((w: string) => '· ' + w).join('\n')
        + '\n\n确认这不是误粘贴，仍要保存吗？');
      if (!ok) return false;
      res = await send(true);
      body = await res.json();
    }
    if (body.code !== 200) {
      flash('❌ ' + (body.message || '修正被拒绝'));
      return false;
    }
    return true;
  }

  // 保存纠错：正文纯文本落 content_text（检索用）、完整富文本 html 落 content_markdown（卡片显示格式）
  // 富文本含 <sup>/<sub>/<b>/<i>/<table>——上下标/加粗/表格编辑全部保存
  // 内置防乱检测：与原文几乎无关/疑似误粘贴 → 后端拒绝；可疑修改 → 二次确认（patch guard）
  async function saveEdit() {
    if (!engine || !editingEv) return;
    const parts = editorRef.current?.getParts() ?? { text: '', tableMd: null, html: '' };
    const text = parts.text;
    if (!text.trim()) { flash('内容不能为空'); return; }
    const okText = await postPatch(editingEv.clause_revision_id, 'content_text', text, 'UI 纠错');
    if (!okText) return;   // 被拒绝或用户取消 → 停在编辑态
    if (parts.html) {
      const okMd = await postPatch(editingEv.clause_revision_id, 'content_markdown', parts.html, 'UI 纠错(富文本)');
      if (!okMd) return;
    }
    setEvidences((es) => es.map((e) => e.clause_revision_id === editingEv.clause_revision_id
      ? { ...e, content_text: text, content_html: parts.html || e.content_html, is_suspicious: false } : e));
    setEditingEv(null);
    await refreshPatches();
    flash('修正已生效（卡片修订记录可查看/撤销）');
  }

  async function submitPatch() {
    if (!engine || !patchFor || !patchText.trim()) return;
    await apiFetch(engine.port, engine.token, '/api/v1/clauses/patches', {
      method: 'POST',
      body: JSON.stringify({ clause_revision_id: patchFor.clause_revision_id, field_name: 'content_text', patched_value: patchText, patch_reason: 'UI 纠错' }),
    });
    setPatchFor(null); setPatchText('');
    await refreshPatches();
    flash('修正已生效（可随时撤销）');
  }

  // ===== Task 12.1 Office/WPS 往返编辑（D3：复杂编辑走本机 Office）=====
  // 交互模型（用户定版）：WPS 只是"填入手段"——编辑器原界面不动，
  // WPS 里保存/关闭后内容自动回填到编辑器，由用户在编辑器里检查后点💾保存（唯一保存出口）
  async function officeEditStart(ev: Evidence) {
    if (!engine) return;
    setOfficeErr(null);
    // 取左栏聊天框屏幕位置 → WPS 窗口对齐它
    let rect: { left: number; top: number; width: number; height: number } | null = null;
    const leftEl = document.querySelector('.left') as HTMLElement | null;
    if (leftEl) {
      const r = leftEl.getBoundingClientRect();
      rect = {
        left: Math.round(r.left + (window.screenX || 0)),
        top: Math.round(r.top + (window.screenY || 0)),
        width: Math.round(r.width),
        height: Math.round(r.height),
      };
    }
    try {
      const res = await apiFetch(engine.port, engine.token, `/api/v1/clauses/${ev.clause_revision_id}/office-edit`, {
        method: 'POST',
        body: JSON.stringify(rect ? { rect } : {}),
      });
      const body = await res.json();
      if (body.code !== 200) { setOfficeErr(body.message || '启动 Office 编辑失败'); return; }
      // 留在编辑器：只挂状态条，不切换界面
      setOfficeSession({ ...body.data, ev });
      if (officeTimer.current) clearInterval(officeTimer.current);
      officeTimer.current = setInterval(() => void officePoll(), 1500);
    } catch (e) {
      // apiFetch 对非 2xx 抛错（如导出失败 500）——显示真实原因而非误导性的"未连接"
      setOfficeErr('启动失败：' + (e instanceof Error ? e.message.slice(0, 120) : String(e)));
    }
  }
  // 从快速修改编辑栏升级到 Office（复用当前编辑中的条款）
  async function officeUpgradeFromEditor() {
    if (!engine || !editingEv) return;
    await officeEditStart(editingEv);
  }
  async function officePoll() {
    if (!engine || !officeSession?.session_id) return;
    try {
      const res = await apiFetch(engine.port, engine.token,
        `/api/v1/clauses/office-edit/poll?session_id=${encodeURIComponent(officeSession.session_id)}`);
      const body = await res.json();
      if (body.code === 200) {
        const data = body.data as { has_changes?: boolean; rejected_reason?: string | null;
          proposed?: { text?: string; table_html?: string | null } | null };
        if (data.has_changes && data.proposed && !data.rejected_reason) {
          // WPS 内容 → 自动回填编辑器（不直接落库；保存仍由编辑器的💾完成）
          backfillEditorFromOffice(data.proposed);
          // 会话使命完成：取消清理
          if (officeTimer.current) clearInterval(officeTimer.current);
          void apiFetch(engine.port, engine.token,
            `/api/v1/clauses/office-edit/${officeSession.session_id}`, { method: 'DELETE' });
          setOfficeSession(null);
          flash('✅ Word/WPS 内容已填入编辑器，请检查后点「💾 保存修正」');
        } else if (data.rejected_reason) {
          setOfficeSession((s: any) => ({ ...(s ?? {}), ...data, ev: s?.ev }));
        }
      } else if (body.code === 404) { // 会话已结束
        if (officeTimer.current) clearInterval(officeTimer.current);
        setOfficeSession(null);
      }
    } catch { /* 引擎瞬断，下轮再试 */ }
  }
  // WPS proposed（正文文本 + 表格 html）→ 回填 TipTap 编辑器
  function backfillEditorFromOffice(proposed: { text?: string; table_html?: string | null }) {
    const editor = editorRef.current;
    if (!editor) return;
    const text = (proposed.text ?? '').trim();
    const tableHtml = proposed.table_html || null;
    // 正文段落化 + 表格 html 拼接（与 textToHtml 同构；TipTap 可直接吃 <table>）
    const paras = text.split(/\n+/).filter(Boolean)
      .map((p) => '<p>' + p.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>').join('');
    editor.setHTML(paras + (tableHtml ?? ''));
  }
  function officeCancel() {
    if (officeTimer.current) clearInterval(officeTimer.current);
    setOfficeSession(null); setOfficeErr(null);
    if (officeSession?.session_id && engine) {
      void apiFetch(engine.port, engine.token, `/api/v1/clauses/office-edit/${officeSession.session_id}`, { method: 'DELETE' });
    }
  }

  async function rollbackPatch(id: string) {
    if (!engine) return;
    await apiFetch(engine.port, engine.token, `/api/v1/clauses/patches/${id}`, { method: 'DELETE' });
    await refreshPatches();
    flash('已回滚到原始快照');
  }

  async function exportCitations(copyOnly: boolean) {
    if (!engine || evidences.length === 0) return;
    const res = await apiFetch(engine.port, engine.token, '/api/v1/export/citations', {
      method: 'POST',
      body: JSON.stringify({ query, clause_revision_ids: evidences.map((e) => e.clause_revision_id) }),
    });
    const data = (await res.json()).data;
    if (copyOnly) {
      await navigator.clipboard.writeText(data.citation_text);
      flash('引用块已复制');
    } else if (data.docx) {
      await downloadFile((data.docx as string).split(/[\\/]/).pop()!);
    }
  }

  async function downloadFile(name: string) {
    if (!engine) return;
    const res = await apiFetch(engine.port, engine.token,
      `/api/v1/export/download?name=${encodeURIComponent(name)}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    flash(`已下载：${name}`);
  }

  async function exportReviewReport() {
    if (!engine || !reviewTaskId) return;
    const res = await apiFetch(engine.port, engine.token, `/api/v1/export/review/${reviewTaskId}`, { method: 'POST' });
    const data = (await res.json()).data;
    await downloadFile(data.name);
  }

  async function ask() {
    if (!engine?.port || !query.trim()) return;
    answerRef.current = '';  // 修复：新轮次清空累积（否则第二轮会拼上第一轮全文）
    setAnswer(''); setVerifying(true); setVerification(null); setEvidences([]); setTimeWarnings([]);
    setClarify(null);
    sseRef.current?.abort();
    const ac = new AbortController(); sseRef.current = ac;
    // 微信式聊天记录：追加提问 + 空回答气泡（流式填充）
    setChatItems((items) => {
      const next = [...items, { role: 'user' as const, content: query }, { role: 'assistant' as const, content: '', streaming: true }];
      chatStreamIdx.current = next.length - 1;
      return next;
    });
    try {
      const res = await fetch(`http://127.0.0.1:${engine.port}/api/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${engine.token}` },
        body: JSON.stringify({
          query, history: messages.slice(-8),
          top_k: answerScope === 'full' ? 5 : 3,
          include_superseded: includeSuperseded,
          query_mode: queryMode,
          answer_scope: answerScope,
        }),
        signal: ac.signal,
      });
      const reader = res.body!.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split('\n\n'); buf = parts.pop()!;
        for (const part of parts) {
          const ev = /event: (.+)/.exec(part)?.[1];
          const data = /data: (.+)/s.exec(part)?.[1];
          if (!ev || !data) continue;
          const payload = JSON.parse(data);
          if (ev === 'clarify') {
            // 追问轮计入历史（R-追问节制）：否则后端每轮都判定为"首轮"无限追问
            const qText = (payload.questions || []).join('；') || '请补充必要参数。';
            setMessages((m) => {
              const next = [...m,
                { role: 'user' as const, content: query },
                { role: 'assistant' as const, content: '（追问）' + qText }].slice(-10);
              localStorage.setItem('ks.chat.history', JSON.stringify(next));
              return next;
            });
            setClarify(payload); setVerifying(false); return;
          }
          if (ev === 'evidence') {
            const list = payload.evidences ?? [];
            evidencesRef.current = list;
            setEvidences(list);
            setTimeWarnings(payload.time_warnings ?? []);
          }
          if (ev === 'delta') {
            answerRef.current += payload.content;
            setAnswer(answerRef.current);
            setChatItems((items) => items.map((it, i) =>
              i === chatStreamIdx.current ? { ...it, content: answerRef.current } : it));
          }
          if (ev === 'verification') { setVerification(payload); setVerifying(false); }
          if (ev === 'done') {
            setVerifying(false);
            // 回答完成：结束流式标记 + 持久化聊天记录
            setChatItems((items) => items.map((it, i) =>
              i === chatStreamIdx.current ? { ...it, streaming: false } : it));
            // 回答完成：自动把第一个引用跳到右侧预览窗
            const first = evidencesRef.current[0];
            if (first) void openEvidence(first);
          }
        }
      }
      // R60：回答完成后把本轮 user/assistant 记入历史（供下一轮追问）+ 持久化
      const finalAnswer = answerRef.current + '';
      setMessages((m) => {
        const next = [...m, { role: 'user' as const, content: query }, { role: 'assistant' as const, content: finalAnswer }].slice(-10);
        localStorage.setItem('ks.chat.history', JSON.stringify(next));
        return next;
      });
      // 聊天记录同步持久化（含历史，最多保留 20 条）
      setChatItems((items) => {
        const snap = items.map((it) => ({ role: it.role, content: it.content }));
        localStorage.setItem('ks.chat.history', JSON.stringify(snap.slice(-20)));
        return items;
      });
      setTurnCount((n) => {
        const next = n + 1;
        localStorage.setItem('ks.chat.turns', String(next));
        return next;
      });
    } catch (e) { setAnswer(`请求失败: ${e}`); setVerifying(false); }
  }

  async function clearChat() {
    sseRef.current?.abort();
    answerRef.current = '';
    localStorage.removeItem('ks.chat.history');
    localStorage.removeItem('ks.chat.turns');
    setMessages([]); setTurnCount(0); setAnswer(''); setVerification(null);
    setEvidences([]); setTimeWarnings([]); setPdfBytes(null); setSpans([]);
    setChatItems([]); chatStreamIdx.current = -1;
  }

  async function runGap() {
    if (!engine || !policyText.trim() || !policyName.trim()) return;
    setGapResult(null);
    const r1 = await apiFetch(engine.port, engine.token, '/api/v1/compliance/policies', {
      method: 'POST', body: JSON.stringify({ policy_name: policyName, policy_text: policyText }) });
    const pid = (await r1.json()).data.policy_id;
    const r2 = await apiFetch(engine.port, engine.token, '/api/v1/compliance/gap-analysis', {
      method: 'POST', body: JSON.stringify({ policy_id: pid }) });
    setGapResult((await r2.json()).data);
  }

  async function exportObligationsDocx() {
    if (!engine || !obligListId) return;
    const res = await apiFetch(engine.port, engine.token,
      `/api/v1/export/obligations/${obligListId}`, { method: 'POST' });
    await downloadFile((await res.json()).data.name);
  }

  async function openOps() {
    if (!engine) return;
    setOpsOpen(true);
    const r1 = await apiFetch(engine.port, engine.token, '/api/v1/diagnostics/health-board');
    setHealthBoard((await r1.json()).data);
    const r2 = await apiFetch(engine.port, engine.token, '/api/v1/diagnostics/debug-dumps?limit=10');
    setDumps((await r2.json()).data);
  }

  async function openCompare() {
    if (!engine) return;
    const res = await apiFetch(engine.port, engine.token, '/api/v1/documents');
    const list = (await res.json()).data;
    setDocs(list);
    setCmpA(list[0]?.doc_id ?? null);
    setCmpB(list[1]?.doc_id ?? list[0]?.doc_id ?? null);
    setCmpResult(null);
    setCmpOpen(true);
  }

  async function runCompare() {
    if (!engine || !cmpA || !cmpB) return;
    const res = await apiFetch(engine.port, engine.token, '/api/v1/compare', {
      method: 'POST', body: JSON.stringify({ doc_a: cmpA, doc_b: cmpB }) });
    setCmpResult((await res.json()).data);
  }

  async function openLog() {
    if (!engine) return;
    const res = await apiFetch(engine.port, engine.token, '/api/v1/operation-log?limit=50');
    setOpLog((await res.json()).data);
    setLogOpen(true);
  }

  async function runReview() {
    if (!engine || !contractText.trim()) return;
    setReviewOut([]); setReviewTaskId(null);
    const res = await apiFetch(engine.port, engine.token, '/api/v1/compliance/review', {
      method: 'POST',
      body: JSON.stringify({ review_type: 'contract', object_name: '审查合同', object_content: contractText }),
    });
    const { task_id } = (await res.json()).data;
    setReviewTaskId(task_id);
    const stream = await fetch(`http://127.0.0.1:${engine.port}/api/v1/compliance/review/${task_id}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${engine.token}` },
      body: JSON.stringify({ confirmed_point_ids: null }),
    });
    const reader = stream.body!.getReader();
    const dec = new TextDecoder();
    let buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split('\n\n'); buf = parts.pop()!;
      for (const part of parts) {
        const ev = /event: (.+)/.exec(part)?.[1];
        const data = /data: (.+)/s.exec(part)?.[1];
        if (!ev || !data) continue;
        const p = JSON.parse(data);
        if (ev === 'point_verdict') {
          const icon = p.verdict === 'red' ? '🔴' : p.verdict === 'yellow' ? '🟡' : '🟢';
          setReviewOut((o) => [...o, `${icon} [${p.point_type}] ${p.point_content}\n   → ${p.reason}`]);
        }
        if (ev === 'report_ready') {
          setReviewOut((o) => [...o, `—— 报告完成：🔴${p.red_count} 🟡${p.yellow_count} 🟢${p.green_count} ——`]);
        }
      }
    }
  }

  async function genObligations() {
    if (!engine || !bizDesc.trim()) return;
    const res = await apiFetch(engine.port, engine.token, '/api/v1/compliance/obligations', {
      method: 'POST', body: JSON.stringify({ business_description: bizDesc }) });
    const data = (await res.json()).data;
    setObligations(data.groups ?? []); setObligListId(data.list_id);
  }

  async function toChecklist() {
    if (!engine || !obligListId) return;
    const res = await apiFetch(engine.port, engine.token, `/api/v1/compliance/obligations/${obligListId}/checklist`, { method: 'POST' });
    setObligations((await res.json()).data.groups ?? []);
  }

  async function checkItem(cid: string, checked: boolean) {
    if (!engine || !obligListId) return;
    setObligations((gs) => gs.map((g) => ({
      ...g, items: g.items.map((it) => it.clause_revision_id === cid ? { ...it, checked } : it),
    })));
    await apiFetch(engine.port, engine.token, `/api/v1/compliance/obligations/${obligListId}/check`, {
      method: 'POST', body: JSON.stringify({ clause_revision_id: cid, checked }) });
  }

  // 数据体检：拉取 OCR/切分质量问题，供集中纠错
  async function loadQuality() {
    if (!engine) return;
    setQOpen(true);
    if (qIssues === null) {
      try {
        const res = await apiFetch(engine.port, engine.token, '/api/v1/data/quality-issues');
        setQIssues((await res.json()).data ?? []);
      } catch { setQIssues([]); }
    }
  }
  const issueToEv = (it: any): Evidence => ({
    clause_revision_id: it.clause_revision_id, doc_id: '', clause_key: '',
    standard_no: it.standard_no, clause_number: it.clause_number, page_start: 0,
    modality: null, knowledge_type: 'rule', content_text: it.content_text,
    patched_fields: it.patched_fields ?? [], type_confidence: 1,
    is_suspicious: it.is_suspicious, user_confirmed: false, bookmarked: false, annotations: [],
    patch_records: [], table_md: it.table_md, table_summary: null, source_spans: [],
  });
  const editFromIssue = (it: any) => { setMode('问答'); setEditingEv(issueToEv(it)); };

  async function toggleTree() {
    if (!engine) return;
    const next = !treeOpen;
    setTreeOpen(next);
    if (next && treeDocId && tree.length === 0) {
      const res = await apiFetch(engine.port, engine.token, `/api/v1/documents/${treeDocId}/tree`);
      setTree((await res.json()).data ?? []);
    }
  }

  // 目录项 → 编号前缀：书签来源 clause_number 为空，从标题提取（"4 基本要求"→"4"，"2.1 术语"→"2.1"）。
  // 2026-08-29 提取边界放宽：书签标题存在无空格形态（"3技术要求"），编号后直跟
  // 中文/括号同样认可；纯数字年份（"2025年版"→"20"误报）由词边界排除。
  const tocNo = (t: TreeItem): string => {
    if (t.clause_number) return t.clause_number.trim();
    const m = (t.title ?? '').match(/^(\d{1,2}(?:\.\d{1,2})?)(?:\s+|(?=[\u4e00-\u9fff（(《]))/);
    return m ? m[1] : '';
  };
  // 目录标题去重（通用展示规则·隐藏版 2026-08-29）：书签/标题自带条款号（"3 技术要求"），
  // 编号徽章已渲染同一编号 → 重复的前缀**隐藏不显示**（display:none 的 span，DOM 原样保留
  // 字符，绝不硬删——识别错误时标题开头几个字一个不丢）；编号不一致 → 原样完整展示。
  const tocTitleSplit = (t: TreeItem): { hidden: string; rest: string } => {
    const no = tocNo(t);
    const title = (t.title ?? '').trim();
    const m = dupNoMatches(title, no);
    if (!m) return { hidden: '', rest: title };
    return { hidden: m[1], rest: title.slice(m[1].length).trimStart() || title };
  };
  // 某目录项下是否有证据卡片引用（当前问答 evidences 里 clause_number 以该编号开头）
  const tocHasEvidence = (t: TreeItem): boolean => {
    const no = tocNo(t);
    if (!no) return false;
    return evidences.some((e) => {
      const cn = e.clause_number ?? '';
      return cn === no || cn.startsWith(no + '.');
    });
  };
  // 点 ▸：懒加载该标题下所有条款
  async function toggleTocExpand(t: TreeItem) {
    const no = tocNo(t);
    if (!no || !engine || !treeDocId) return;
    const key = no;
    const next = !tocExpanded[key];
    setTocExpanded((s) => ({ ...s, [key]: next }));
    if (next && !tocChildren[key] && !tocLoading[key]) {
      setTocLoading((s) => ({ ...s, [key]: true }));
      try {
        const res = await apiFetch(engine.port, engine.token,
          `/api/v1/documents/${treeDocId}/clauses-by-prefix?prefix=${encodeURIComponent(no)}`);
        const body = await res.json();
        if (body.code === 200) setTocChildren((s) => ({ ...s, [key]: body.data ?? [] }));
      } catch { /* 引擎未起 */ }
      setTocLoading((s) => ({ ...s, [key]: false }));
    }
  }

  // 文件目录面板：加载分类树（标准→CCS，法规→效力等级；空分类不返回）
  async function loadFileNav() {
    if (!engine) return;
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/documents/categories');
      const body = await res.json();
      if (body.code === 200) {
        setFileNavCats(body.data ?? []);
        setCatLoaded(true);
        // 默认展开第一层（两个顶级分类）
        const first = (body.data ?? []).map((c: any) => 'T:' + c.name);
        setCatOpen((s) => {
          const next = { ...s };
          for (const k of first) next[k] = true;
          return next;
        });
      }
    } catch { /* 引擎未起 */ }
  }
  // 点分类名：展开/收起该分类文档列表
  function toggleCat(name: string) {
    setCatOpen((s) => ({ ...s, [name]: !s[name] }));
  }
  // 文件目录搜索：按国标名称/编号（含分类名）过滤整棵树；有词时全部自动展开。
  // 纯前端过滤——树已全量在内存，零请求即时响应；命中分支保留，未命中分支剔除。
  const catQ = catQuery.trim().toLowerCase();
  const catFiltered = useMemo(() => {
    if (!catQ) return fileNavCats;
    const docHit = (d: any) =>
      (d.standard_no ?? '').toLowerCase().includes(catQ) ||
      (d.standard_name ?? '').toLowerCase().includes(catQ);
    const nameHit = (s: any) => typeof s === 'string' && s.toLowerCase().includes(catQ);
    const map3 = (l3: any) => {
      if (nameHit(l3.name)) return { ...l3, docs: l3.docs ?? [], items: l3.items ?? [] };
      const docs = (l3.docs ?? []).filter(docHit);
      const l4s = (l3.items ?? [])
        .map((l4: any) => ({ ...l4, docs: nameHit(l4.name) ? (l4.docs ?? []) : (l4.docs ?? []).filter(docHit) }))
        .filter((l4: any) => l4.docs.length > 0);
      if (!docs.length && !l4s.length) return null;
      return { ...l3, docs, items: l4s };
    };
    const map2 = (l2: any) => {
      if (nameHit(l2.name)) return { ...l2, items: l2.items ?? [] };
      const l3s = (l2.items ?? []).map(map3).filter(Boolean);
      if (!l3s.length) return null;
      return { ...l2, items: l3s };
    };
    return fileNavCats
      .map((top: any) => {
        if (nameHit(top.name)) return { ...top, items: top.items ?? [] };
        const l2s = (top.items ?? []).map(map2).filter(Boolean);
        if (!l2s.length) return null;
        return { ...top, items: l2s };
      })
      .filter(Boolean);
  }, [catQ, fileNavCats]);
  const catMatchCount = useMemo(() => {
    if (!catQ) return 0;
    let n = 0;
    const walk = (items: any[]) => {
      for (const it of items) {
        n += (it.docs ?? []).length;
        if (it.items) walk(it.items);
      }
    };
    walk(catFiltered as any[]);
    return n;
  }, [catQ, catFiltered]);
  // 多选：当前可见（搜索过滤后）全部 doc_id——「全选当前」的数据源。
  // 无搜索词时 catFiltered=全树 → 全选即真的全选；有搜索词时=搜出来的全部。
  const catVisibleDocIds = useMemo(() => {
    const ids: string[] = [];
    const walk = (items: any[]) => {
      for (const it of items) {
        for (const d of (it.docs ?? [])) ids.push(d.doc_id);
        if (it.items) walk(it.items);
      }
    };
    walk(catFiltered as any[]);
    return ids;
  }, [catFiltered]);
  // 多选：切换单个文档选中
  function toggleSelDoc(docId: string) {
    setSelDocs((s) => {
      const next = new Set(s);
      if (next.has(docId)) next.delete(docId); else next.add(docId);
      return next;
    });
    setCatDelPhase(null); // 选择变化 → 撤回进行中的确认条
  }
  // 多选：全选当前（可见全集）；已是全选 → 清空（toggle 语义）
  function toggleSelAll() {
    const vis = catVisibleDocIds;
    const all = vis.length > 0 && vis.every((id) => selDocs.has(id));
    setSelDocs(all ? new Set() : new Set(vis));
    setCatDelPhase(null);
  }
  // 多选：退出多选模式（清空选择与确认状态）
  function exitCatMulti() {
    setCatMulti(false); setSelDocs(new Set()); setCatDelPhase(null);
    setCatDelDone(null); setCatDelErr('');
  }
  // 多选：点删除 → 确认条；确认 → 调后端批量删除（显式级联，2026-08-31 接线）
  function requestCatDelete() {
    if (selDocs.size === 0) return;
    setCatDelPhase('confirm');
  }
  async function confirmCatDelete() {
    if (catDelPhase === 'deleting') return;   // 防重复提交
    if (!engine) { setCatDelErr('引擎未连接'); setCatDelPhase('error'); return; }
    setCatDelPhase('deleting'); setCatDelErr('');
    try {
      const res = await apiFetch(engine.port, engine.token, '/api/v1/documents/batch-delete', {
        method: 'POST',
        body: JSON.stringify({ doc_ids: [...selDocs], confirm: true }),
      });
      const body = await res.json();
      const data = body.data ?? {};
      setCatDelDone({ docs: data.deleted_docs ?? 0, clauses: data.deleted_clauses ?? 0 });
      // 当前打开的文档被删 → 清文档态（目录树/正文/页首信息），避免悬空预览
      if (treeDocId && selDocs.has(treeDocId)) {
        setTreeDocId(null); setCurDocMeta(null); setFullClauses([]);
      }
      void loadFileNav();   // 刷新目录树（删除的文档从分类中消失）
      setCatDelPhase('done');
    } catch (e) {
      setCatDelErr(String(e)); setCatDelPhase('error');
    }
  }
  // 点文档：加载该文档 PDF + 打开右侧文档目录
  async function openDocFromNav(docId: string, meta?: any) {
    // 记录当前文档元数据（PDF 页首信息头用），无则用已有 fileNavCats 里找
    if (meta) setCurDocMeta(meta);
    await loadDocument(docId, 1);
  }

  // 文件目录叶节点（法规/国标）：法规只显示名称（其标准号字段即法规名，避免重复）；
  // 国标显示 标准号 + 名称（名称自动换行）。doc_type='法律法规' 视为法规。
  const docLeaf = (d: any) => {
    // 已废止/被替代 → 灰 + 删除线（用户要求：目录中已废止国标呈现灰色+删除线）
    const struck = d.legal_status === 'superseded' || d.legal_status === 'withdrawn';
    const wd = (d.legal_status === 'withdrawn' || d.legal_status === 'superseded') ? (d.withdrawn_date ?? '') : '';
    // 2026-08-29 用户定稿：文件目录条目不显示 发布/生效/废止 日期（占宽噪音）——
    // 完整日期信息保留在 hover title 里；条目行只留 CCS 分类
    const metaBits = [
      d.ccs_name ? (d.ccs_code ? `${d.ccs_code} ${d.ccs_name}` : d.ccs_name) : '',
    ].filter(Boolean);
    const dateBits = [
      d.published_at ? `发布 ${d.published_at}` : '',
      d.effective_from ? `生效 ${d.effective_from}` : '',
      wd ? `废止 ${wd}` : '',
      d.ccs_name ? (d.ccs_code ? `${d.ccs_code} ${d.ccs_name}` : d.ccs_name) : '',
    ].filter(Boolean);
    return (
    <div
      key={d.doc_id}
      className={'toc-child' + (struck ? ' superseded' : '') + (catMulti ? ' selecting' : '')}
      onClick={() => { if (catMulti) toggleSelDoc(d.doc_id); else void openDocFromNav(d.doc_id, d); }}
      title={d.standard_no + ' ' + (d.standard_name ?? '') + (struck ? '（已废止，仅供参考）' : '') +
        (dateBits.length ? '\n' + dateBits.join(' · ') : '')}
    >
      {catMulti ? (
        <span className={'doc-check' + (selDocs.has(d.doc_id) ? ' on' : '')} aria-checked={selDocs.has(d.doc_id)}>
          {selDocs.has(d.doc_id) ? '✓' : ''}
        </span>
      ) : null}
      {d.doc_type === '法律法规' ? (
        <span className="toc-no" style={{ minWidth: 'auto', fontWeight: 500 }}>{d.standard_name || d.standard_no}</span>
      ) : (
        <>
          <span className="toc-no" style={{ minWidth: 'auto', fontWeight: 500 }}>{d.standard_no}</span>
          {d.standard_name ? <span className="toc-name">{d.standard_name}</span> : null}
        </>
      )}
      {struck ? <span className="toc-page">废止</span> : null}
      {metaBits.length ? (
        <span className="toc-meta">{metaBits.join(' · ')}</span>
      ) : null}
    </div>
    );
  };

  // 引用 → 可交互链接：回答内所有「标准号-条款号」编号链接化
  // 命中证据列表的绑定 data-cid；未命中的走 resolve 兜底（data-resolve，悬停/点击时懒解析）
  // 条款号主分支必须收紧为纯数字点分(6.6/5.2.1/10.1.10)+前瞻 (?![0-9.])：
  // 旧实现 [0-9A-Za-z.]+ 贪婪会把相邻引用前缀吞进条款号
  // (如 [引用:A-6.6][引用:A-6.9] 剥括号后 "A-6.6A-6.9" → 整段 "6.6A" 当条款号，
  //  resolve 查无此条款 → 蓝色下划线但点击/悬停全部失效)
  // 2026-08-26：补中文条款号分支「第X条」（第二十一条/第四百九十六条）——
  // 旧版只认数字点分/表/附录，法律类回答（如 安全生产法(2021修正)-第二十一条）
  // 永远生成不了链接，用户无法点击跳原文（实测反馈）。
  const linkify = (text: string) => {
    let out = text.replace(/🔗/g, '').replace(/\[引用:([^\]]+)\]/g, '$1');
    // 2026-08-26：转义全部正则元字符——旧版只转义 "."，标准号含括号时
    // （如 安全生产法(2021修正)）"(2021修正)"被当捕获组，链接化永久失效（实测反馈）。
    const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    for (const std of [...stdNos].sort((a, b) => b.length - a.length)) {
      const re = new RegExp(esc(std) + '[-–]\\s*((?:[0-9]+(?:\\.[0-9]+)*)|表[0-9]+|附录[0-9A-Za-z]*|第[一二三四五六七八九十百千万零〇\\d]+条)(?![0-9.])', 'g');
      out = out.replace(re, (m: string, num: string) => {
        const key = std + '-' + num;
        const ev = evidences.find((e) => e.standard_no + '-' + e.clause_number === key);
        return ev
          ? '<span class="cite-link" data-cid="' + ev.clause_revision_id + '">' + m + '</span>'
          : '<span class="cite-link" data-resolve="' + std + '|' + num + '">' + m + '</span>';
      });
    }
    return out;
  };
  // 顺序：先转义原始回答文本，再链接化（linkify 生成的 span 不能被转义）
  const renderMsgHtml = (content: string) => linkify(
    mdTablesToHtml(
      content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    )
  ).replace(/\n/g, '<br/>');
  const answerHtml = renderMsgHtml(answer);

  // 事件委托：悬停出卡片（0.5s 渐隐）/ 点击跳预览窗
  const onAnswerHover = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('.cite-popover')) return;  // 鼠标在卡片上：保持显示
    const el = target.closest('.cite-link');
    if (!el) { scheduleHide(); return; }
    // 触发链接矩形快照（契约 §2.3/§2.4）：异步 resolve 返回后仍用它定位；锚点=鼠标位置（跟随鼠标出卡）
    const r = el.getBoundingClientRect();
    const snap: TriggerRect = { left: r.left, top: r.top, width: r.width, height: r.height };
    const anchor = { x: e.clientX, y: e.clientY };
    const cid = el.getAttribute('data-cid');
    const rk = el.getAttribute('data-resolve');
    if (cid) {
      const ev = evidences.find((x) => x.clause_revision_id === cid);
      if (ev) showCard(ev, snap, anchor);
      return;
    }
    if (rk) {
      const sep = rk.indexOf('|');
      const std = rk.slice(0, sep); const num = rk.slice(sep + 1);
      const cached = resolveCache.current[std + '|' + num];
      if (cached) { showCard(cached, snap, anchor); return; }
      void resolveEv(std, num).then((ev) => { if (ev) showCard(ev, snap, anchor); });
    }
  };
  const onAnswerClick = (e: React.MouseEvent) => {
    const el = (e.target as HTMLElement).closest('.cite-link');
    if (!el) return;
    const cid = el.getAttribute('data-cid');
    const rk = el.getAttribute('data-resolve');
    if (cid) {
      const ev = evidences.find((x) => x.clause_revision_id === cid);
      if (ev) void openEvidence(ev);
      return;
    }
    if (rk) {
      const sep = rk.indexOf('|');
      const std = rk.slice(0, sep); const num = rk.slice(sep + 1);
      void resolveEv(std, num).then((ev) => { if (ev) void openEvidence(ev); });
    }
  };

  // 渲染辅助（confBadge/revisionTip/renderContentHtml/renderTable）已抽至 renderHelpers.tsx
  // R24 答案层置信度徽章（悬停显示核验理由）
  const answerConfBadge = () => {
    const lv = verification?.answer_confidence;
    const reasons = (verification?.confidence_reasons || []).join('；') || '核验器综合判定';
    if (lv === 'high') return <em className="badge ok" title={'高可信原因：' + reasons}>✅ 高可信</em>;
    if (lv === 'mid') return <em className="badge mid" title={'建议核对原因：' + reasons}>🟡 建议核对（部分证据低可信）</em>;
    if (lv === 'low') return <em className="badge warn" title={'低可信原因：' + reasons}>⚠️ 低可信（核验未通过）</em>;
    return null;
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">⚖️</div>
          <div className="brand-text">
            <div className="brand-name">国标与法律法规 AI 知识工作站</div>
            <div className="brand-sub">KnowledgeStation · 可溯源合规问答</div>
          </div>
        </div>
        <nav className="mode-tabs">
          {(['问答', '审查', '更新'] as Mode[]).map((m) => (
            <button key={m} className={'seg-btn' + (mode === m ? ' active' : '')} onClick={() => setMode(m)}>{m}</button>
          ))}
        </nav>
        <div className="topbar-right">
          <button className="tool-btn" onClick={() => setShowApiCfg(true)}>⚙️ 设置</button>
          <button className="tool-btn" onClick={() => void openEgress()}>📤 外发审计</button>
          <button className="tool-btn" onClick={openCompare}>🔀 对比</button>
          <button className="tool-btn" onClick={openLog}>📜 更新日志</button>
          <button className="tool-btn" onClick={openOps}>🩺 运维</button>
          <span className={'engine-chip' + (engine ? ' on' : '')} title={engine ? '本地引擎已连接' : '引擎未连接，请运行 scripts/dev_launcher.py'}>
            <i className="dot" />{engine ? `引擎 :${engine.port}` : '引擎未连接'}
          </span>
        </div>
      </header>
      {showApiCfg && <ApiConfigPanel engine={engine} onClose={() => setShowApiCfg(false)} />}
      <div className="workspace">
        <section className="left" style={splitW ? { width: splitW } : undefined}>
          {mode === '更新' ? (
            <UpdatePanel engine={engine} onBatchStarted={setUpdBid} />
          ) : mode === '问答' ? (
            editingEv ? (
              <div className="edit-pane">
                <div className="edit-head">
                  <b>✏️ 编辑条款：{editingEv.standard_no} 第{editingEv.clause_number}条</b>
                  <span className="edit-hint">直接在此修改文字/表格；复杂内容可点「在 Word/WPS 中编辑」，改完自动填回这里</span>
                  <button className="mini" onClick={() => void officeUpgradeFromEditor()} title="导出到本机 Word/WPS 编辑，保存/关闭后自动填回此编辑器">📝 在 Word/WPS 中编辑</button>
                  <button className="mini" onClick={() => void saveEdit()}>💾 保存修正</button>
                  <button className="mini" onClick={() => { officeCancel(); setEditingEv(null); }}>取消</button>
                </div>
                {/* WPS 往返状态条（轻量，不切界面）：检测到 WPS 保存后自动回填下方编辑器 */}
                {officeSession && (
                  <div className="office-strip">
                    {officeSession.rejected_reason ? (
                      <>
                        <span className="office-err">⚠️ 越界编辑被拒绝：{officeSession.rejected_reason}——请删除图片/形状后重存，或放弃 WPS 改动直接在此编辑。</span>
                        <button className="mini" onClick={officeCancel}>知道了</button>
                      </>
                    ) : officeSession.has_changes ? (
                      <span className="edit-hint" style={{ color: 'var(--ok)' }}>✅ 检测到 WPS 保存，正在回填…</span>
                    ) : (
                      <span className="edit-hint">📝 Word/WPS 编辑中：改完 Ctrl+S 保存（或直接关闭），内容会自动填回下面这个编辑器，再点「💾 保存修正」入库</span>
                    )}
                    <button className="mini" onClick={officeCancel} style={{ marginLeft: 'auto' }}>放弃 WPS 改动</button>
                  </div>
                )}
                {officeErr && <p className="office-err">❌ {officeErr}</p>}
                <TipTapEditor ref={editorRef} value={editingEv.content_text} tableMd={editingEv.table_md} html={editingEv.content_html} />
              </div>
            ) : (
              <>
              <div className="chat" ref={chatRef}>
                {chatItems.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-logo">⚖️</div>
                    <div className="empty-title">向知识库提问，每条结论都可点回原文核对</div>
                    <div className="empty-sub">回答自动附标准号-条款号引用；悬停看证据卡片，点击跳到 PDF 原文黄框处。</div>
                    <div className="empty-chips">
                      {['动火作业如何分级？', '气体探测器安装高度要求？', '消防疏散宽度怎么计算？', '格式条款无效的情形有哪些？'].map((q) => (
                        <button key={q} className="ex-chip" onClick={() => setQuery(q)}>{q}</button>
                      ))}
                    </div>
                    <div className="empty-hint">提示：可用「[丙类厂房/高层/耐火二级] 疏散宽度」前置参数语法跳过追问</div>
                  </div>
                ) : (
                <div className="chat-meta">
                  <span className="turn-badge">{turnCount > 0 ? '第 ' + turnCount + ' 轮对话' : '新对话'}</span>
                  {turnCount > 0 && <button className="mini" onClick={clearChat}>🗑 清空对话</button>}
                </div>
                )}
                {chatItems.map((m, i) => (
                  <div key={i} className="msg-row">
                    {m.role === 'assistant' ? <div className="msg-avatar">🤖</div> : <div className="msg-avatar-space" />}
                    {m.role === 'user' ? (
                      <div className="msg-user">{m.content}</div>
                    ) : (
                      <div className={'msg-assistant' + (m.streaming ? ' streaming' : '')}
                        onMouseOver={onAnswerHover} onClick={onAnswerClick}>
                        {i === chatStreamIdx.current && verifying && <div className="watermark">核验中 · 通过前禁止复制</div>}
                        {i === chatStreamIdx.current && verification && !verification.is_valid && (
                          <div className="verify-fail">
                            ⚠️ 核验未通过：
                            {verification.unsupported_clauses.length > 0 && <div>· 编造条款号: {verification.unsupported_clauses.join('、')}</div>}
                            {verification.unverified_numbers.length > 0 && <div>· 数值被篡改: {verification.unverified_numbers.map((n) => n.original + '→' + n.output).join('；')}</div>}
                            {verification.modality_violations.length > 0 && <div>· 模态违规: {verification.modality_violations.map((v) => v.source_modality + '→' + v.output_modality + '(' + v.violation_type + ')').join('；')}</div>}
                            {verification.legal_element_violations.length > 0 && <div>· 法理要素缺失: {verification.legal_element_violations.map((v) => v.violation).join('；')}</div>}
                          </div>
                        )}
                        {i === chatStreamIdx.current && verification?.is_valid && <div className="verify-ok">✅ 核验通过，已解锁复制 {answerConfBadge()}</div>}
                        {i === chatStreamIdx.current && !verification?.is_valid && answerConfBadge() && <div className="verify-ok">{answerConfBadge()}</div>}
                        <p dangerouslySetInnerHTML={{
                          __html: i === chatStreamIdx.current ? answerHtml : renderMsgHtml(m.content),
                        }} />
                        {i === chatStreamIdx.current && (
                          <div className="a-actions">
                            <button disabled={verifying || !verification?.is_valid} onClick={() => navigator.clipboard.writeText(answer)}>复制</button>
                            <button disabled={evidences.length === 0} onClick={() => exportCitations(true)}>📋 复制引用块</button>
                            <button disabled={evidences.length === 0} onClick={() => exportCitations(false)}>📄 导出依据Word</button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {clarify && (
                  <div className="clarify-card">
                    <b>🤔 还差几个关键信息（请一次性补充，最多一轮）</b>
                    {clarify.questions.map((q: string, i: number) => (
                      <div key={i} className="clarify-q">{i + 1}. {q}</div>
                    ))}
                    {clarify.hint && <p className="clarify-hint">{clarify.hint}</p>}
                    <div className="review-actions">
                      <button onClick={() => { setQueryMode('guess'); void ask(); }}>按默认场景回答</button>
                    </div>
                  </div>
                )}
                {timeWarnings.map((w) => <div key={w} className="time-warning">{w}</div>)}
                {/* 证据卡片（契约重构）：浮动卡 + 固定卡图层 */}
                {hoverEv && (
                  <EvidenceCard
                    variant="floating"
                    ev={hoverEv.ev}
                    trigger={hoverEv.trigger}
                    anchor={hoverEv.anchor}
                    paneRect={paneRect}
                    treeOpen={treeOpen}
                    zIndex={940}
                    fading={fading}
                    onMouseEnter={keepFloatCard}
                    onMouseLeave={scheduleHide}
                    onPin={pinFloatingCard}
                    onMove={(p) => { floatPosRef.current = p; }}
                    confBadge={confBadge}
                    revisionTip={revisionTip}
                    renderContentHtml={renderContentHtml}
                    renderTable={renderTable}
                    verdictLabel={verdictLabel}
                    onLocate={(ev) => void openEvidence(ev)}
                    onAnnotate={(ev) => { setAnnFor(ev); setAnnText(''); }}
                    onVerdict={(ev) => void toggleVerdict(ev)}
                    onBookmark={(ev) => void toggleBookmark(ev)}
                  />
                )}
              </div>
              {!editingEv && (
              <div className="input-row">
                <input value={query} onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && ask()} placeholder="如：动火作业监护要求" autoFocus />
                <label className="switch-toggle" title="检索时包含已废止版本">
                  <input type="checkbox" checked={includeSuperseded}
                    onChange={(e) => setIncludeSuperseded(e.target.checked)} />
                  <span className="switch-track"><span className="switch-knob" /></span>
                  含已废止
                </label>
                <select className="mode-select" value={queryMode}
                  onChange={(e) => setQueryMode(e.target.value)} title="R9 追问档位">
                  <option value="default">正本清源（追问）</option>
                  <option value="thorough">打破沙锅</option>
                  <option value="quick">差不多就行</option>
                  <option value="guess">纯靠猜</option>
                </select>
                <label className="switch-toggle" title="回答覆盖范围（R59）：勾选后回答更全面（检索更多证据、回答更长）；不勾选为精简模式">
                  <input type="checkbox" checked={answerScope === 'full'}
                    onChange={(e) => setAnswerScope(e.target.checked ? 'full' : 'concise')} />
                  <span className="switch-track"><span className="switch-knob" /></span>
                  全面
                </label>
                <button className="send-btn" onClick={ask}>提问 ⏎</button>
              </div>
              )}
              </>
            )
          ) : (
            <div className="review-pane">
              <div className="review-tabs">
                {(['合同审查', '义务清单'] as ReviewTab[]).map((t) => (
                  <button key={t} className={reviewTab === t ? 'active' : ''} onClick={() => setReviewTab(t)}>{t}</button>
                ))}
                <button className={'q-btn' + (qOpen ? ' active' : '')} onClick={loadQuality}>
                  🔍 数据体检{qIssues !== null ? '（' + qIssues.length + '）' : ''}
                </button>
              </div>
              {qOpen && (
                <div className="quality-panel">
                  {qIssues === null ? <p className="q-hint">扫描中…</p> : qIssues.length === 0 ? (
                    <p className="q-hint">✅ 未发现明显 OCR/切分质量问题</p>
                  ) : (
                    <div className="q-list">
                      {qIssues.map((it: any, i: number) => (
                        <div key={i} className="q-row">
                          <b>{it.standard_no}-{it.clause_number}</b>
                          <span className="q-tags">{it.issues.join(' / ')}</span>
                          <span className="q-snip">{it.content_text.replace(/\n/g, ' ').slice(0, 60)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {reviewTab === '合同审查' ? (
                <>
                  <textarea value={contractText} onChange={(e) => setContractText(e.target.value)}
                    placeholder="粘贴合同全文，点击开始审查" rows={9} />
                  <div className="review-actions">
                    <button onClick={runReview}>开始合规审查</button>
                    <button disabled={!reviewTaskId} onClick={exportReviewReport}>📄 导出报告Word</button>
                  </div>
                  <pre className="review-out">{reviewOut.join('\n')}</pre>
                </>
              ) : (
                <>
                  <textarea value={bizDesc} onChange={(e) => setBizDesc(e.target.value)}
                    placeholder="描述业务活动，如：开一家餐饮店 / 运营收集个人信息的 App" rows={3} />
                  <div className="review-actions">
                    <button onClick={genObligations}>生成义务清单</button>
                    <button disabled={!obligListId} onClick={toChecklist}>☑ 转为检查表</button>
                    <button disabled={!obligListId} onClick={exportObligationsDocx}>📄 导出Word</button>
                    <button onClick={() => setGapTab(!gapTab)}>{gapTab ? '✕ 收起差距分析' : '🔍 差距分析'}</button>
                  </div>
                  {gapTab && (
                    <div className="gap-box">
                      <input value={policyName} onChange={(e) => setPolicyName(e.target.value)}
                        placeholder="制度名称，如：公司消防安全管理制度" />
                      <textarea value={policyText} onChange={(e) => setPolicyText(e.target.value)}
                        placeholder="粘贴内部制度全文（自动按章/节切分），点击开始差距分析" rows={5} />
                      <button onClick={runGap}>开始差距分析</button>
                      {gapResult && (
                        <div className="gap-result">
                          <p>🔴 {gapResult.counts.red} 缺失｜🟡 {gapResult.counts.yellow} 不完善｜
                            🟢 {gapResult.counts.green} 已覆盖</p>
                          {gapResult.results.slice(0, 20).map((r: any, i: number) => (
                            <div key={i} className="gap-row">
                              <span className={r.verdict === 'red' ? 'v-red' : r.verdict === 'yellow' ? 'v-yellow' : 'v-green'}>
                                {r.verdict === 'red' ? '🔴' : r.verdict === 'yellow' ? '🟡' : '🟢'}</span>
                              <span>{r.obligation}</span>
                              <em className="gap-sugg">{r.suggestion}</em>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="obligations">
                    {obligations.map((g) => (
                      <div key={g.group} className="ob-group">
                        <b>{g.group}</b>
                        {g.items.map((it) => (
                          <label key={it.clause_revision_id} className="ob-item">
                            <input type="checkbox" checked={it.checked}
                              onChange={(e) => void checkItem(it.clause_revision_id, e.target.checked)} />
                            <span>{it.question ?? it.obligation_text.slice(0, 100)}</span>
                            <em className="ob-src">{it.standard_no} {it.clause_number}</em>
                          </label>
                        ))}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </section>
        <div className={'divider' + (dragRef.current ? ' dragging' : '')} onMouseDown={startDrag} title="拖动调整左右宽度" />
        <section className="right">
          <div className="right-inner">
            {/* 文件目录抽屉：与 PDF 目录并列（同样式同宽度），4 级树
                标准：L1 大类 → L2 CCS大类 → L3 区间 → L4 具体类目+文档
                法规：L1 → L2 效力等级 → L3 领域 → L4 文档 */}
            {fileNavOpen && (
              <div className="toc-drawer" style={{ width: fileW ?? 176 }}>
                <b>📚 文件目录</b>
                <div className="toc-search">
                  <input
                    value={catQuery}
                    onChange={(e) => setCatQuery(e.target.value)}
                    placeholder="🔍 搜索国标名称/编号"
                    title="按标准号或名称过滤文件目录，即时生效"
                  />
                  {catQuery && (
                    <button className="toc-search-clear" onClick={() => setCatQuery('')} title="清空">×</button>
                  )}
                </div>
                {/* 多选工具行：多选 ⇄ (删除 / 全选当前 / 取消)；确认条与后端未接入提示 */}
                <div className="toc-multitool">
                  {!catMulti ? (
                    <button onClick={() => { setCatMulti(true); setCatDelPhase(null); }}
                      title="进入编辑模式：条目前出现勾选框，点击条目即选中/取消">
                      ☑ 编辑
                    </button>
                  ) : (
                    <>
                      <button className="danger" disabled={selDocs.size === 0}
                        onClick={requestCatDelete}
                        title={selDocs.size === 0 ? '先勾选要删除的文档' : `删除选中的 ${selDocs.size} 部文档`}>
                        🗑 删除{selDocs.size > 0 ? `(${selDocs.size})` : ''}
                      </button>
                      <button onClick={toggleSelAll}
                        title={catQ
                          ? (catVisibleDocIds.every((id) => selDocs.has(id)) && catVisibleDocIds.length > 0 ? '清空当前搜出的全部选中' : `全选搜出的 ${catVisibleDocIds.length} 部`)
                          : (catVisibleDocIds.every((id) => selDocs.has(id)) && catVisibleDocIds.length > 0 ? '清空全部选中' : `全选全部 ${catVisibleDocIds.length} 部`)}>
                        {catVisibleDocIds.length > 0 && catVisibleDocIds.every((id) => selDocs.has(id)) ? '◻ 取消全选' : '☑ 全选当前'}
                      </button>
                      <button onClick={exitCatMulti} title="退出编辑模式并清空选择">✕ 取消</button>
                    </>
                  )}
                </div>
                {catMulti && catDelPhase === 'confirm' && (
                  <div className="toc-delconfirm">
                    <div>⚠ 将永久删除选中的 <b>{selDocs.size}</b> 部文档及其全部条款/证据/向量，不可恢复。</div>
                    <div className="toc-delconfirm-btns">
                      <button className="danger" onClick={confirmCatDelete}>确认删除</button>
                      <button onClick={() => setCatDelPhase(null)}>再想想</button>
                    </div>
                  </div>
                )}
                {catMulti && catDelPhase === 'deleting' && (
                  <div className="toc-delconfirm">
                    <div>⏳ 正在删除选中的 <b>{selDocs.size}</b> 部文档…</div>
                  </div>
                )}
                {catMulti && catDelPhase === 'done' && catDelDone && (
                  <div className="toc-delstub">
                    ✅ 已删除 {catDelDone.docs} 部文档（{catDelDone.clauses} 条条款及其证据/向量已级联清除）。
                    <div className="toc-delconfirm-btns">
                      <button onClick={exitCatMulti}>完成</button>
                    </div>
                  </div>
                )}
                {catMulti && catDelPhase === 'error' && (
                  <div className="toc-delconfirm">
                    <div>❌ 删除失败：{catDelErr}</div>
                    <div className="toc-delconfirm-btns">
                      <button className="danger" onClick={() => setCatDelPhase('confirm')}>返回重试</button>
                      <button onClick={exitCatMulti}>取消</button>
                    </div>
                  </div>
                )}
                <div className="toc-list">
                  {!catLoaded ? <div className="toc-child-hint">加载中…</div> : fileNavCats.length === 0 ? (
                    <div className="toc-child-hint">库内暂无文档</div>
                  ) : catQ && catMatchCount === 0 ? (
                    <div className="toc-child-hint">没有匹配「{catQuery.trim()}」的文件</div>
                  ) : catFiltered.map((top) => {
                    const key1 = 'T:' + top.name;
                    const open1 = !!catQ || !!catOpen[key1];
                    return (
                      <div key={key1}>
                        <div className="toc-item lvl1" onClick={() => toggleCat(key1)}>
                          <span className="toc-caret">{open1 ? '▾' : '▸'}</span>
                          <span className="toc-title">{top.name}</span>
                        </div>
                        {open1 && (
                          <div className="toc-children">
                            {top.items.map((l2: any) => {
                              const key2 = key1 + '>' + l2.name;
                              const open2 = !!catQ || !!catOpen[key2];
                              return (
                                <div key={key2}>
                                  <div className="toc-item lvl2" onClick={() => toggleCat(key2)}>
                                    <span className="toc-caret">{open2 ? '▾' : '▸'}</span>
                                    <span className="toc-title">{l2.name}</span>
                                  </div>
                                  {open2 && (
                                    <div className="toc-children">
                                      {l2.items.map((l3: any) => {
                                        const key3 = key2 + '>' + l3.name;
                                        const open3 = !!catQ || !!catOpen[key3];
                                        return (
                                          <div key={key3}>
                                            <div className="file-sub-name" onClick={() => toggleCat(key3)}
                                              style={{ cursor: 'pointer', paddingLeft: 8 }}>
                                              <span className="toc-caret" style={{ marginRight: 4 }}>{open3 ? '▾' : '▸'}</span>
                                              {l3.name}
                                            </div>
                                            {open3 && (
                                              <div className="toc-children" style={{ paddingLeft: 14 }}>
                                                {(l3.docs ?? []).length > 0 ? (
                                                  /* 法规树：领域下直接是文档叶节点（法规名称不再作为目录级别） */
                                                  l3.docs.map((d: any) => docLeaf(d))
                                                ) : (
                                                  l3.items.map((l4: any) => (
                                                    <div key={l4.name} className="file-sub">
                                                      <div className="file-sub-name" style={{ paddingLeft: 4 }}>{l4.name}</div>
                                                      {l4.docs.map((d: any) => docLeaf(d))}
                                                    </div>
                                                  ))
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {fileNavOpen && (
              <div className="v-divider" onMouseDown={(e) => startVResize(e, 'file')} title="拖动调整宽度" />
            )}
            {treeOpen && (
              <div className="toc-drawer" style={{ width: tocW ?? 176 }}>
                <b>标题目录</b>
                <div className="toc-list">
                  {tree.map((t) => {
                    const no = tocNo(t);
                    const hasEv = tocHasEvidence(t);
                    const expanded = !!tocExpanded[no];
                    const children = tocChildren[no];
                    const loading = !!tocLoading[no];
                    const tt = tocTitleSplit(t);
                    return (
                      <div key={t.clause_number + (t.level ?? 1) + (t.title ?? '')}>
                        <div
                          className={'toc-item' + (t.level === 1 ? ' lvl1' : ' lvl2') + (hasEv ? ' has-ev' : '')}
                          onClick={() => setJumpPage(t.page_start)}>
                          {hasEv ? (
                            <span className="toc-caret"
                              onClick={(e) => { e.stopPropagation(); void toggleTocExpand(t); }}
                              title={expanded ? '收起该章条款' : '展开该章所有条款'}>
                              {expanded ? '▾' : '▸'}
                            </span>
                          ) : null}
                          <span className="toc-no">{t.clause_number || no}</span>
                          <span className="toc-title">
                            {tt.hidden ? <span className="dup-no-hidden">{tt.hidden}</span> : null}
                            {tt.rest.slice(0, 24)}
                          </span>
                          <span className="toc-page">p{t.page_start}</span>
                        </div>
                        {expanded && (
                          <div className="toc-children">
                            {loading ? <div className="toc-child-hint">加载中…</div> : null}
                            {!loading && (!children || children.length === 0) ? (
                              <div className="toc-child-hint">该标题下无子条款</div>
                            ) : null}
                            {children?.map((c) => (
                              <div key={c.clause_number} className="toc-child"
                                onClick={() => setJumpPage(c.page_start)}>
                                <span className="toc-no">{c.clause_number}</span>
                                <span className="toc-page">p{c.page_start}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {treeOpen && (
              <div className="v-divider" onMouseDown={(e) => startVResize(e, 'toc')} title="拖动调整宽度" />
            )}
            <div className="pdf-wrap">
              <div className="pdf-toolbar-extra">
                <button onClick={() => {
                  setFileNavOpen(!fileNavOpen);
                  if (!fileNavOpen && !catLoaded) void loadFileNav();
                }}>📚 文件目录</button>
                <button onClick={toggleTree} disabled={!treeDocId}>📖 目录</button>
              </div>
              {curDocMeta?.standard_no ? (
                <div className="pdf-header">
                  <div className="pdf-header-row1">
                    <span className="pdf-header-no">{curDocMeta.standard_no}</span>
                    <span className="pdf-header-name">{curDocMeta.standard_name}</span>
                    <span className={`pdf-header-status st-${curDocMeta.legal_status || 'unmarked'}`}>
                      {({ effective: '现行', upcoming: '尚未生效', superseded: '被替代', withdrawn: '已废止' } as Record<string, string>)[curDocMeta.legal_status] || ''}
                    </span>
                    <span className="pdf-header-spacer" />
                    {pdfBytes && !showOriginal ? <button className="pdf-header-btn" onClick={() => setShowOriginal(true)}>🔍 看原件</button> : null}
                    {!editingWord ? (
                      <button className="pdf-header-btn" onClick={() => setEditingWord(true)} title="整窗可编辑，对照原件修改保存走校验">✏️ 纠错</button>
                    ) : (
                      <>
                        <button className="pdf-header-btn" onClick={saveWordEdit}>💾 保存</button>
                        <button className="pdf-header-btn" onClick={() => setEditingWord(false)}>取消</button>
                      </>
                    )}
                  </div>
                  <div className="pdf-header-row2">
                    <span className="pdf-header-meta">发布 {curDocMeta.published_at ?? '—'}</span>
                    <span className="pdf-header-meta">生效 {curDocMeta.effective_from ?? '—'}</span>
                    <span className="pdf-header-meta">废止 {curDocMeta.withdrawn_date ?? '—'}</span>
                    {curDocMeta.ccs_name ? <span className="pdf-header-meta">{curDocMeta.ccs_code ? `${curDocMeta.ccs_code} ` : ''}{curDocMeta.ccs_name}</span> : null}
                  </div>
                </div>
              ) : null}
              <div className="doc-body">
                {!fullClauses.length ? (
                  <div className="law-placeholder">
                    <div className="empty-logo">{!fullLoaded ? (pdfBytes ? '⏳' : '📜') : (pdfBytes ? '📄' : '📜')}</div>
                    <div className="empty-title">
                      {!fullLoaded
                        ? (pdfBytes ? '正在加载全文条款…' : '法律法规文本直灌入库')
                        : (pdfBytes ? '该文档暂无结构化条款' : '该法规无 PDF 原件页')}
                    </div>
                    <div className="empty-sub">
                      {!fullLoaded
                        ? '正在从 /documents/<doc>/clauses 拉取全文。若一直停留在此，请重启引擎以加载最新后端代码（全文预览接口）。'
                        : pdfBytes
                          ? '条款解析尚未完成或解析失败（后台修复批次会自动补齐）。可先点击右上「🔍 看原件」直接浏览 PDF 原文，内容检索暂不可用。'
                          : '可用右侧「📖 目录」浏览条文结构，或在问答中检索引用（引用可溯源到条款号）。'}
                    </div>
                    {fullLoaded && pdfBytes ? (
                      <button className="pdf-header-btn" style={{ marginTop: 12 }} onClick={() => setShowOriginal(true)}>🔍 看原件</button>
                    ) : null}
                  </div>
                ) : (
                  <div className={'fulltext' + (editingWord ? ' editing' : '')} ref={fulltextRef}>
                    {fullClauses.map((c) => (
                      <div key={c.clause_revision_id} className="fulltext-clause"
                        data-page={c.page_start} data-clause-id={c.clause_revision_id}
                        contentEditable={editingWord} suppressContentEditableWarning
                        title={c.page_start ? `原件第 ${c.page_start} 页（滚动预览时原件实时联动）` : ''}>
                        {/* 2026-09-02：条款悬停/点击→跳页已退役（整页居中跳转与连续滚动同步互相打架，
                            且后台渲染期重触发导致弹回/跳顶）。滚动预览时原件经页锚点连续跟随；
                            显式跳转仍走 jumpPage（目录/证据卡/搜索定位）。 */}
                        <div className="fulltext-cno">
                          {c.clause_number}
                        </div>
                        {c.title ? <div className="fulltext-title">{c.title}</div> : null}
                        {c.content_html ? <div className="fulltext-body" dangerouslySetInnerHTML={{ __html: hideDupClauseNoHtml(c.content_html, c.clause_number) }} /> : null}
                      </div>
                    ))}
                  </div>
                )}
                {showOriginal && pdfBytes ? (
                  <div className="pdf-side">
                    <div className="pdf-side-bar">
                      <span>{curDocMeta?.standard_no ?? ''} 原件</span>
                      <button onClick={() => setShowOriginal(false)}>✕ 关闭</button>
                    </div>
                    <PdfViewer pdfBytes={pdfBytes} jumpToPage={jumpPage} highlights={spans}
                      priorityPage={jumpPage}
                      getSyncSource={getSyncSource} syncSourceSeq={fullClauses.length}
                      onLocatePage={(page) => setJumpPage(page)}
                      onSpanHover={(cid, x, y) => {
                        if (!cid) { setHoverEv(null); return; }
                        const ev = evidences.find((e) => e.clause_revision_id === cid);
                        setHoverEv(ev ? { ev, trigger: { left: x, top: y, width: 0, height: 0 }, anchor: { x, y } } : null);
                      }} />
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </section>
      </div>
      <footer className="statusbar">
        <span>⚙️ 本地知识库 · 云增强模式（LLM 仅接收问题与证据片段）</span>
        <span className="status-right">外发内容全程留痕 · 运维面板可回溯</span>
      </footer>
      {figZoom ? (
        <div className="fig-zoom-mask" onClick={() => setFigZoom(null)}>
          <img src={figZoom.url} alt="" className="fig-zoom-img" />
          {figZoom.loading ? <div className="fig-zoom-tip">加载高清版…</div> : null}
          <div className="fig-zoom-tip" style={{ top: 18 }}>点击任意处关闭</div>
        </div>
      ) : null}

      {/* 固定卡图层：根级渲染 → 跨模式常驻（切到审查/更新模式不消失，切回原位恢复）；
          坐标仍由组件钳制在左栏面板内（契约 R3：不遮 PDF/目录/状态栏） */}
      {pinnedCards.map((p) => (
        <EvidenceCard
          key={p.id}
          variant="pinned"
          /* 证据状态跟随 evidences 最新值（可信切换/收藏/批注后徽章即时刷新）；新问题清空列表时回退到固定时快照 */
          ev={evidences.find((e) => e.clause_revision_id === p.ev.clause_revision_id) ?? p.ev}
          initialPos={{ x: p.x, y: p.y }}
          paneRect={paneRect}
          zIndex={p.z}
          onPin={() => removePinned(p.id)}
          onClose={() => removePinned(p.id)}
          onFront={() => bringPinnedToFront(p.id)}
          onMove={(pos) => {
            if (pos.x !== p.x || pos.y !== p.y) {
              setPinnedCards((cards) => cards.map((c) => (c.id === p.id ? { ...c, x: pos.x, y: pos.y } : c)));
            }
          }}
          confBadge={confBadge}
          revisionTip={revisionTip}
          renderContentHtml={renderContentHtml}
          renderTable={renderTable}
          verdictLabel={verdictLabel}
          onLocate={(ev) => void openEvidence(ev)}
          onAnnotate={(ev) => { setAnnFor(ev); setAnnText(''); }}
          onVerdict={(ev) => void toggleVerdict(ev)}
          onBookmark={(ev) => void toggleBookmark(ev)}
        />
      ))}

      {opsOpen && (
        <div className="modal-mask" onClick={() => setOpsOpen(false)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><b>🩺 运维诊断</b><button className="modal-x" onClick={() => setOpsOpen(false)}>✕</button></div>
            {healthBoard && (
              <div className="ops-board">
                <div className="ops-engines">
                  {Object.entries(healthBoard.engines).map(([k, v]) => (
                    <span key={k} className={'engine-pill ' + (v === 'ok' || v === 'configured' || v === 'active' ? 'ok' : 'bad')}>
                      {k}: {String(v)}
                    </span>
                  ))}
                </div>
                <p className="ops-stats">
                  文档 {healthBoard.stats.documents}｜条款 {healthBoard.stats.clauses}｜向量 {healthBoard.stats.vectors}｜
                  补丁 {healthBoard.stats.patches}｜术语 {healthBoard.stats.aliases}｜审查 {healthBoard.stats.reviews}｜
                  Debug Dump {healthBoard.stats.debug_dumps}
                </p>
                <p className="ops-hint">重启服务：运行 scripts/dev_launcher.py（或 .venv/Scripts/python -m src.core.supervisor）</p>
                <details className="law-fetch-details">
                  <summary className="log-row"><span>📗 法规抓取（官方源：flk.npc.gov.cn / gov.cn）</span></summary>
                  {engine && <LawFetchPanel port={engine.port} token={engine.token} flash={flash} />}
                </details>
                <details className="law-fetch-details">
                  <summary className="log-row"><span>📘 法规总目录（flk 全量清单 · 点开即核验 · 按需下载）</span></summary>
                  {engine && <LawCatalogPanel port={engine.port} token={engine.token} flash={flash} onOpenDocument={(docId) => loadDocument(docId, 1)} />}
                </details>
              </div>
            )}
            <div className="log-list">
              {dumps.map((d) => (
                <details key={d.dump_id} className="dump-item">
                  <summary className="log-row">
                    <span className="log-time">{d.created_at}</span>
                    <span className="log-type">{d.trigger_type}</span>
                    <span className="log-target">{d.query}</span>
                  </summary>
                  <pre className="dump-detail">{JSON.stringify(d.logs ? JSON.parse(d.logs) : {}, null, 1).slice(0, 900)}</pre>
                </details>
              ))}
            </div>
          </div>
        </div>
      )}
      {cmpOpen && (
        <div className="modal-mask" onClick={() => setCmpOpen(false)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><b>🔀 条款对比（版本对照 / 跨标准）</b><button className="modal-x" onClick={() => setCmpOpen(false)}>✕</button></div>
            <div className="cmp-selects">
              <select value={cmpA ?? ''} onChange={(e) => setCmpA(e.target.value)}>
                {docs.map((d) => <option key={d.doc_id} value={d.doc_id}>{d.standard_no}</option>)}
              </select>
              <span> vs </span>
              <select value={cmpB ?? ''} onChange={(e) => setCmpB(e.target.value)}>
                {docs.map((d) => <option key={d.doc_id} value={d.doc_id}>{d.standard_no}</option>)}
              </select>
              <button onClick={runCompare}>开始对比</button>
            </div>
            {cmpResult && (
              <div className="cmp-result">
                <p>配对 {cmpResult.stats.paired} 条｜新增 {cmpResult.stats.added}｜删除 {cmpResult.stats.removed}｜
                  <b>模态变化 {cmpResult.stats.modality_changes}</b></p>
                {cmpResult.pairs.slice(0, 30).map((p: any, i: number) => (
                  <div key={i} className="cmp-pair">
                    <div className="cmp-no">
                      {p.clause_number}
                      {p.modality_changed && (
                        <em className="badge warn">模态 {p.modality_changed.old}→{p.modality_changed.new}</em>)}
                      {p.changed ? <em className="badge mid">有变化</em> : <em className="badge ok">未变</em>}
                    </div>
                    <div className="cmp-cols">
                      <div className="cmp-old">{p.old.content.slice(0, 200)}</div>
                      <div className="cmp-new">{p.new.content.slice(0, 200)}</div>
                    </div>
                  </div>
                ))}
                {(cmpResult.added_clause_numbers.length > 0 || cmpResult.removed_clause_numbers.length > 0) && (
                  <p className="cmp-addrem">
                    新增条款: {cmpResult.added_clause_numbers.join('、')}｜删除条款: {cmpResult.removed_clause_numbers.join('、')}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      {logOpen && (
        <div className="modal-mask" onClick={() => setLogOpen(false)}>
          <div className="modal wide" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><b>📜 知识库更新日志</b><button className="modal-x" onClick={() => setLogOpen(false)}>✕</button></div>
            <div className="log-list">
              {opLog.map((l, i) => (
                <div key={i} className="log-row">
                  <span className="log-time">{l.created_at}</span>
                  <span className="log-type">{l.event_type}</span>
                  <span className="log-target">{l.target_id}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      {patchFor && (
        <div className="float-panel" onMouseLeave={() => { if (!patchText) setPatchFor(null); }}>
          <b>✏️ 修正条款原文</b>
          <p className="modal-hint">{patchFor.standard_no} 第{patchFor.clause_number}条（原始快照不会被修改，可随时撤销）</p>
          <textarea rows={6} value={patchText} onChange={(e) => setPatchText(e.target.value)} />
          <div>
            <button onClick={submitPatch}>提交修正</button>
            <button onClick={() => setPatchFor(null)}>取消</button>
          </div>
        </div>
      )}
      {annFor && (
        <div className="float-panel" onMouseLeave={() => { if (!annText) setAnnFor(null); }}>
          <b>💬 添加批注</b>
          <p className="modal-hint">{annFor.standard_no} 第{annFor.clause_number}条（批注绑定条款，重新入库不丢失）</p>
          <textarea rows={4} value={annText} onChange={(e) => setAnnText(e.target.value)}
            placeholder="如：本项目按 4m 执行 / 该条在 XX 案中认定标准较严" />
          <div>
            <button onClick={submitAnnotation}>保存批注</button>
            <button onClick={() => setAnnFor(null)}>取消</button>
          </div>
        </div>
      )}
      {/* 阶段六批次6：巡检任务右下角小卡片（F-24），无活动批次时不渲染 */}
      <TaskCard engine={engine} batchId={updBid} onClose={() => setUpdBid(null)} />
      {toast && <div className="toast">{toast}</div>}

      {/* Task 12.7 外发审计面板（10.0 的 UI 面） */}
      {egressOpen && (
        <div className="modal-mask" onClick={() => setEgressOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><b>📤 外发审计（云增强模式 · 每次云调用全程留痕）</b>
              <button className="modal-x" onClick={() => setEgressOpen(false)}>×</button></div>
            <div className="egress-list">
              {egressList.length === 0
                ? <p className="modal-hint">暂无记录（问答会逐次落库；使用问答后刷新可见）</p>
                : egressList.map((e: any) => (
                    <div key={e.dump_id} className="egress-row">
                      <div><b>{e.service}</b> <span className="egress-time">{e.created_at}</span></div>
                      <div className="egress-q">问题：{e.query}</div>
                      <div className="egress-preview">{e.prompt_preview}</div>
                    </div>))}
            </div>
            <div className="modal-actions">
              <button className="mini" disabled={egressList.length === 0}
                onClick={() => void exportEgress()}>⬇️ 导出 JSON</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
