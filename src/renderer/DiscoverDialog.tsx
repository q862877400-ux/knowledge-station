// DiscoverDialog（F-15~F-18）：口语找标对话。
// 契约（pipeline/02 §3）：
// - POST /discover/classify {description} → {questions[],candidates[]|category_path,confidence}
//   （追问协议对齐问答追问 v2：单轮一次问完 ≤3 问；超过 3 轮仍返回追问时按首个候选直接检索）；
// - POST /discover/search {category_path,drill_level≤3} → 结果卡片列表（F-17 字段）；
// - POST /discover/watchlist {action:'add',standard_no,name} 加入待下载清单（F-18，幂等）；
// 追问气泡复用问答模块既有气泡样式类（.msg-row/.msg-avatar/.msg-user/.msg-assistant）。
import { useEffect, useRef, useState } from 'react';
import { apiFetch } from './api';

interface EngineInfo { port: string; token: string }

interface Candidate { code: string; name: string; path: string[] }
interface ClassifyData {
  category_path?: string[];
  confidence?: number;
  questions?: string[];
  candidates?: Candidate[];
}
interface StdCard {
  standard_no: string;
  name: string;
  status: string;
  mandatory: boolean;
  evidence_url?: string;
}
interface Bubble {
  role: 'user' | 'assistant';
  content: string;
  candidates?: Candidate[];
}

interface DiscoverDialogProps {
  engine: EngineInfo | null;
  onClose: () => void;
}

const MAX_ASK_ROUNDS = 3; // F-15：追问深度 ≤3 问

function statusBadge(status: string): { cls: string; text: string } {
  const t = (status || '').trim();
  if (/废止|撤回|superseded|withdrawn/i.test(t)) return { cls: 'warn', text: t || '已废止' };
  if (/即将|未实施|upcoming/i.test(t)) return { cls: 'mid', text: t || '即将实施' };
  if (/现行|有效|effective|current/i.test(t)) return { cls: 'ok', text: t || '现行' };
  return { cls: 'gray', text: t || '状态未知' };
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

export default function DiscoverDialog({ engine, onClose }: DiscoverDialogProps) {
  const [thread, setThread] = useState<Bubble[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [cards, setCards] = useState<StdCard[] | null>(null);
  const [catLabel, setCatLabel] = useState('');
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [err, setErr] = useState('');
  const askRoundsRef = useRef(0);

  // Esc 关闭（与全站模态一致）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function runSearch(path: string[], note?: string) {
    if (!engine) return;
    if (note) setThread((ts) => [...ts, { role: 'assistant', content: note }]);
    const res = await apiFetch(engine.port, engine.token, '/api/v1/discover/search', {
      method: 'POST',
      body: JSON.stringify({ category_path: path, drill_level: 1 }),
    });
    const list = ((await res.json()).data ?? []) as StdCard[];
    setCatLabel(path.join(' / '));
    setCards(list);
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy || !engine) return;
    setInput('');
    setErr('');
    setBusy(true);
    setThread((ts) => [...ts, { role: 'user', content: q }]);
    try {
      // 2026-08-26：追问收窄必须带对话上下文——用户补充"就是劳动保护用品相关的啊"
      // 若只发当前句，后端 classify 对孤立补充句必然 miss（实测"不管问什么都同一句回答"）。
      // 把历史用户输入与当前句拼接后一次性分类。
      const history = thread.filter((m) => m.role === 'user').map((m) => m.content);
      const description = [...history, q].join('；');
      const res = await apiFetch(engine.port, engine.token, '/api/v1/discover/classify', {
        method: 'POST',
        body: JSON.stringify({ description }),
      });
      const d = ((await res.json()).data ?? {}) as ClassifyData;
      if (d.category_path && d.category_path.length > 0) {
        await runSearch(d.category_path);
        return;
      }
      askRoundsRef.current += 1;
      const questions = (d.questions ?? []).filter(Boolean).join('\n');
      if (askRoundsRef.current <= MAX_ASK_ROUNDS) {
        setThread((ts) => [...ts, {
          role: 'assistant',
          content: questions || '请补充标准涉及的行业、对象或用途。',
          candidates: d.candidates ?? [],
        }]);
        return;
      }
      // 已问满 3 轮仍是追问 → 不再连环追问，按首个候选分类直接检索（兜底）
      const first = (d.candidates ?? [])[0];
      if (first) {
        await runSearch(first.path,
          `已达追问上限（${MAX_ASK_ROUNDS} 问），先按「${first.code} ${first.name}」检索：`);
      } else {
        setThread((ts) => [...ts, {
          role: 'assistant',
          content: `连续 ${MAX_ASK_ROUNDS} 轮追问仍未定位到分类，请换个说法（更具体的行业/对象/用途）再试。`,
        }]);
      }
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusy(false);
    }
  }

  async function addToWatchlist(c: StdCard) {
    if (!engine || added.has(c.standard_no)) return;
    try {
      await apiFetch(engine.port, engine.token, '/api/v1/discover/watchlist', {
        method: 'POST',
        body: JSON.stringify({ action: 'add', standard_no: c.standard_no, name: c.name }),
      });
      setAdded((s) => new Set(s).add(c.standard_no));
    } catch (e) {
      setErr(errText(e));
    }
  }

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal wide disc-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <b>🔎 找标准（口语找标 · 分类映射 + 追问收窄）</b>
          <button className="modal-x" onClick={onClose}>✕</button>
        </div>
        <div className="disc-body">
          <div className="disc-thread">
            {thread.length === 0 && !busy && (
              <p className="upd-hint">
                用一句大白话描述你要找的标准，例如「我要安全的国标」「食品添加剂相关的标准」「电线电缆用什么国标」。
              </p>
            )}
            {thread.map((m, i) => (
              <div key={i} className="msg-row">
                {m.role === 'assistant'
                  ? <div className="msg-avatar">🤖</div>
                  : <div className="msg-avatar-space" />}
                {m.role === 'user' ? (
                  <div className="msg-user">{m.content}</div>
                ) : (
                  <div className="msg-assistant">
                    <p>{m.content}</p>
                    {(m.candidates?.length ?? 0) > 0 && (
                      <div className="disc-cands">
                        {m.candidates!.map((c) => (
                          <button key={c.code} className="ex-chip"
                            disabled={busy}
                            onClick={() => void send(`${c.code} ${c.name}`)}>
                            {c.code} {c.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="msg-row">
                <div className="msg-avatar">🤖</div>
                <div className="msg-assistant streaming"><p /></div>
              </div>
            )}
          </div>
          {err && <p className="upd-error">❌ {err}</p>}
          <div className="disc-inputrow">
            <input value={input} autoFocus
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void send(input)}
              placeholder="如：我要安全的国标" />
            <button className="upd-btn primary" disabled={busy || !input.trim()}
              onClick={() => void send(input)}>找标准</button>
          </div>
          {cards !== null && (
            <div className="disc-results">
              <p className="disc-cat">分类「{catLabel}」 · 结果 {cards.length} 条</p>
              {cards.length === 0 ? (
                <p className="upd-hint">该渠道未返回结果——可换更具体的描述重找，或稍后再试。</p>
              ) : cards.map((c) => {
                const sb = statusBadge(c.status);
                const isAdded = added.has(c.standard_no);
                return (
                  <div key={c.standard_no} className="disc-card">
                    <div className="disc-card-head">
                      <span className="disc-no">{c.standard_no}</span>
                      {c.mandatory && <em className="badge modality">强制性</em>}
                      <em className={'badge ' + sb.cls}>{sb.text}</em>
                      <span className="flex-spacer" />
                      <button className="mini" disabled={isAdded}
                        title={isAdded ? '已在待下载清单中（按标准号幂等去重）' : '暂存到待下载清单，批量处理'}
                        onClick={() => void addToWatchlist(c)}>
                        {isAdded ? '✓ 已加入清单' : '➕ 加入待下载清单'}
                      </button>
                    </div>
                    <p className="disc-name">{c.name || '（无名称）'}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
