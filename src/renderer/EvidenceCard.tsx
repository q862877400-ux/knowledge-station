import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import type { Evidence } from './App';
import { normalizeWraps, stripEmbeddedTable } from './tableText';
import { hiddenDupNoText } from './renderHelpers';

/** 触发元素矩形快照（视口坐标，契约 §2.3/§2.4） */
export interface TriggerRect { left: number; top: number; width: number; height: number }
/** 问答左栏面板矩形（视口坐标；契约 §2.1：一切定位/拖拽/钳制的边界） */
export interface PaneRect { left: number; top: number; width: number; height: number }

const PAD = 8;      // 面板四周留白（契约 §2.1）
const GAP = 6;      // 卡片与触发链接的间距（契约 §2.3）
const DEF_W = 470;  // 默认宽度基准 min(470, paneWidth-16)（契约 §2.2）
const EST_H = 360;  // 未实测前的估高（契约 §2.3 下方空间判定用）
const DRAWER = 232; // 目录抽屉宽度（treeOpen 时卡片避让它，契约 §2.3）

interface EvidenceCardProps {
  ev: Evidence;
  /** floating=悬停浮卡（0.5s 渐隐）；pinned=固定卡（常驻、可多实例） */
  variant: 'floating' | 'pinned';
  /** 触发链接矩形快照（防遮挡用；浮动卡定位基准之一） */
  trigger?: TriggerRect | null;
  /** 鼠标锚点（跟随鼠标出卡：光标右下偏移为首选位，契约 §2.3 用户修订 2026-08-25） */
  anchor?: { x: number; y: number } | null;
  /** 初始位置（固定卡：📌 时记录的卡片位置） */
  initialPos?: { x: number; y: number } | null;
  paneRect: PaneRect | null;
  /** 目录打开时浮卡固定在目录抽屉右侧（契约 §2.3），同样受面板钳制 */
  treeOpen?: boolean;
  /** 内联 z-index：浮动 940 / 固定 950+stack（契约 §5） */
  zIndex: number;
  /** 浮动卡渐隐中（父层 scheduleHide 控制） */
  fading?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  /** 📌：浮动→转固定；固定→取消固定并关闭（语义由父层实现） */
  onPin: () => void;
  /** ✕ 关闭（仅固定卡渲染该按钮） */
  onClose?: () => void;
  /** 固定卡 mousedown 置顶（bring-to-front，契约 §4） */
  onFront?: () => void;
  /** 位置变化上报：父层同步固定卡坐标 / 记录浮动卡位置（📌 转固定用） */
  onMove?: (pos: { x: number; y: number }) => void;
  // —— 内容与行为由 App 注入，保持既有行为不变（定位原文/纠错/批注/收藏/可信切换等）——
  confBadge: (ev: Evidence) => ReactNode;
  revisionTip: (ev: Evidence) => string;
  renderContentHtml: (ev: Evidence) => ReactNode;
  renderTable: (ev: Evidence) => ReactNode;
  verdictLabel: (ev: Evidence) => string;
  onLocate: (ev: Evidence) => void;
  onEdit?: (ev: Evidence) => void;
  onAnnotate: (ev: Evidence) => void;
  onVerdict: (ev: Evidence) => void;
  onBookmark: (ev: Evidence) => void;
}

/** 矩形相交判定 */
function rectsHit(ax: number, ay: number, aw: number, ah: number, b: TriggerRect): boolean {
  return ax < b.left + b.width && ax + aw > b.left && ay < b.top + b.height && ay + ah > b.top;
}

/** 证据卡片：面板坐标系定位引擎 + 头部拖拽 + 固定/关闭（契约 §2~§4）。
 *  定位全部以 .left 面板矩形为边界——卡片天然不会遮挡右栏 PDF/目录/状态栏。 */
export default function EvidenceCard(props: EvidenceCardProps) {
  const {
    ev, variant, trigger = null, anchor = null, initialPos = null, paneRect, treeOpen = false,
    zIndex, fading,
    onMouseEnter, onMouseLeave, onPin, onClose, onFront, onMove,
    confBadge, revisionTip, renderContentHtml, renderTable, verdictLabel,
    onLocate, onEdit, onAnnotate, onVerdict, onBookmark,
  } = props;

  const cardRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ x: number; y: number }>(() =>
    initialPos ?? { x: 40, y: 40 });
  const [sizeW, setSizeW] = useState(DEF_W);          // 宽度受控（保留手动 resize 结果并持续钳制）
  const [vh, setVh] = useState(() => window.innerHeight);
  const [dragging, setDragging] = useState(false);
  const draggedRef = useRef(false);                   // 用户拖过后定位引擎不再自动重摆
  const lastTrigRef = useRef<TriggerRect | null>(null);
  const paneRectRef = useRef<PaneRect | null>(paneRect);
  paneRectRef.current = paneRect;   // 每次渲染同步，回调/观察器里读最新值
  const anchorRef = useRef(anchor);
  anchorRef.current = anchor;       // 落位时读最新鼠标锚点；同一链接内移动不重摆（防抖动）

  /** 钳制进面板（含卡片尺寸），面板过窄时保底不越右/下界 */
  const clampPos = (p: { x: number; y: number }, w: number, h: number, pane: PaneRect) => ({
    x: Math.min(Math.max(p.x, pane.left + PAD), Math.max(pane.left + PAD, pane.left + pane.width - PAD - w)),
    y: Math.min(Math.max(p.y, pane.top + PAD), Math.max(pane.top + PAD, pane.top + pane.height - PAD - h)),
  });

  /** 契约 §2.3 第 5 步：钳制后仍与触发链接相交 → 沿垂直方向逐级让位至完全不相交 */
  const avoidTrigger = (x: number, y: number, w: number, h: number, pane: PaneRect, tr: TriggerRect) => {
    let ny = y;
    const trBottom = tr.top + tr.height;
    for (let i = 0; i < 200 && rectsHit(x, ny, w, h, tr); i++) {
      const roomBelow = pane.top + pane.height - PAD - (trBottom + GAP);
      const roomAbove = tr.top - GAP - (pane.top + PAD);
      ny += roomBelow >= roomAbove ? 8 : -8;
      ny = clampPos({ x, y: ny }, w, h, pane).y;
    }
    return ny;
  };

  /** 契约 §2.3 初始定位（2026-08-25 用户修订：跟随鼠标锚点）：
   *  首选光标右下 → 放不下翻光标上方 → 横向放不下翻光标左侧 → 出界钳制 → 防遮挡触发链接校验 */
  const placeFromTrigger = () => {
    const pane = paneRectRef.current;
    if (!pane || pane.width < PAD * 4 || pane.height < PAD * 4) return;
    const w = Math.min(DEF_W, pane.width - PAD * 2);
    const h = Math.min(EST_H, pane.height - PAD * 2);
    let x: number, y: number;
    if (treeOpen) {
      // 目录打开：固定在目录抽屉（232px）右侧、面板内垂直居中（旧行为），受面板钳制
      x = pane.left + DRAWER + PAD;
      y = pane.top + Math.max(PAD, (pane.height - h) / 2);
    } else if (anchorRef.current) {
      // 跟随鼠标：光标右下角偏移 14/16 起卡
      const a = anchorRef.current;
      x = a.x + 14;
      y = a.y + 16;
      if (y + h > pane.top + pane.height - PAD) y = a.y - h - 16;            // 下方放不下 → 光标上方
      if (x + w > pane.left + pane.width - PAD) x = a.x - w - 14;            // 右侧放不下 → 光标左侧
    } else if (trigger) {
      const trBottom = trigger.top + trigger.height;
      if (trBottom + GAP + h <= pane.top + pane.height - PAD) y = trBottom + GAP;              // ① 链接正下方
      else if (trigger.top - GAP - h >= pane.top + PAD) y = trigger.top - GAP - h;             // ② 正上方
      else y = pane.top + pane.height - PAD - h;                                               // ③ 贴底部
      x = trigger.left;                                                                        // 水平与链接左对齐
    } else {
      x = pane.left + (pane.width - w) / 2;
      y = pane.top + (pane.height - h) / 2;
    }
    // ④ 出界钳制
    ({ x, y } = clampPos({ x, y }, w, h, pane));
    // ⑤ 最终校验：钳制后仍压住触发链接 → 垂直让位至不相交
    if (trigger && !treeOpen) y = avoidTrigger(x, y, w, h, pane, trigger);
    setPos({ x, y });
  };

  // 浮动卡落位：新触发（换链接悬停）重置拖拽标记并重新定位；treeOpen/面板变化跟随旧版行为。
  // 固定卡不参与自动落位（位置归用户）。
  useLayoutEffect(() => {
    if (variant !== 'floating') return;
    if (trigger !== lastTrigRef.current) {
      draggedRef.current = false;
      lastTrigRef.current = trigger;
    }
    if (draggedRef.current) return;
    placeFromTrigger();
    // placeFromTrigger 经 ref 读最新状态；依赖数组为契约要求的落位时机
  }, [variant, trigger, treeOpen, paneRect]);

  /** 契约 §2.2：实测尺寸后二次钳制（内容撑高/手动缩放都不出面板） */
  const reclamp = () => {
    const pane = paneRectRef.current;
    const el = cardRef.current;
    if (!pane || !el || pane.width < PAD * 4 || pane.height < PAD * 4) return;
    const r = el.getBoundingClientRect();
    setSizeW((prevW) => {
      const w = Math.min(Math.max(r.width, 120), pane.width - PAD * 2);
      return Math.abs(w - prevW) < 1 ? prevW : w;
    });
    setPos((prev) => {
      let next = clampPos(prev, r.width, r.height, pane);
      if (variant === 'floating' && !draggedRef.current && trigger && !treeOpen) {
        next = { ...next, y: avoidTrigger(next.x, next.y, r.width, r.height, pane, trigger) };
      }
      return next.x === prev.x && next.y === prev.y ? prev : next;
    });
  };

  // 卡片自身尺寸观察（ResizeObserver）：内容撑高 / resize:both 手动缩放 → 重新钳制
  useLayoutEffect(() => {
    const el = cardRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => reclamp());
    ro.observe(el);
    const onWinResize = () => { setVh(window.innerHeight); reclamp(); };
    window.addEventListener('resize', onWinResize);
    return () => { ro.disconnect(); window.removeEventListener('resize', onWinResize); };
  }, []);

  // 面板矩形变化（分割条拖动 / 窗口缩放）→ 重新钳制；未拖拽过的浮动卡由上方落位 effect 重摆
  useLayoutEffect(() => { reclamp(); }, [paneRect]);

  // 位置上报：父层同步固定卡坐标（下一张级联）/ 记录浮动卡最近位置（📌 转固定用）
  useEffect(() => { onMove?.(pos); }, [pos]);

  /** 头部拖拽（契约 §3）：Pointer Events + setPointerCapture，全程钳制在面板内 */
  const headPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest('button')) return;   // 头部按钮（收藏/固定/关闭）不触发拖拽
    const el = cardRef.current;
    if (!el) return;
    e.preventDefault();
    const rect = el.getBoundingClientRect();
    const offX = e.clientX - rect.left;
    const offY = e.clientY - rect.top;
    draggedRef.current = true;
    setDragging(true);
    try { el.setPointerCapture(e.pointerId); } catch { /* 指针已失效则忽略 */ }
    const move = (pev: PointerEvent) => {
      const pane = paneRectRef.current;
      if (!pane) return;
      setPos(clampPos({ x: pev.clientX - offX, y: pev.clientY - offY }, rect.width, rect.height, pane));
    };
    const finish = () => {
      setDragging(false);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', finish);
      window.removeEventListener('pointercancel', finish);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', finish);
    window.addEventListener('pointercancel', finish);
  };

  const maxH = Math.min(vh * 0.76, (paneRect ? paneRect.height : vh) - PAD * 2);
  const cls = 'cite-popover ' + (variant === 'pinned' ? 'pinned' : 'floating') + (fading ? ' fade-out' : '');

  return (
    <div ref={cardRef} className={cls}
      style={{ left: pos.x, top: pos.y, zIndex, width: sizeW, maxHeight: Math.max(150, maxH) }}
      onMouseDown={variant === 'pinned' ? onFront : undefined}
      onMouseEnter={variant === 'floating' ? onMouseEnter : undefined}
      onMouseLeave={variant === 'floating' ? onMouseLeave : undefined}>
      {/* 头部 = 拖拽手柄（.ec-head）；按钮不触发拖拽 */}
      <div className={'ev-head ec-head' + (dragging ? ' dragging' : '')} onPointerDown={headPointerDown}>
        <b>🔗 {ev.standard_no} 第{ev.clause_number}条</b>
        {confBadge(ev)}
        {ev.patched_fields.length > 0 && <em className="badge patched" title={revisionTip(ev)}>📝 修订记录</em>}
        <button className="star" onClick={() => onBookmark(ev)}>{ev.bookmarked ? '★' : '☆'}</button>
        <button className="ec-pin-btn" onClick={onPin} aria-pressed={variant === 'pinned'}
          title={variant === 'pinned' ? '取消固定并关闭' : '固定卡片（鼠标移开不消失）'}>📌</button>
        {variant === 'pinned' && (
          <button className="ec-close" onClick={onClose} title="关闭">✕</button>
        )}
      </div>
      <div className="cite-popover-body">
        {renderContentHtml(ev) ?? (
          <div className="ev-text">{hiddenDupNoText(normalizeWraps(stripEmbeddedTable(ev.content_text, ev.table_md)), ev.clause_number, 300)}</div>
        )}
        {!ev.content_html?.includes('<table') && renderTable(ev)}
        {(ev.annotations ?? []).map((a) => (
          <div key={a.annotation_id} className="my-annotation">【我的批注】{a.content}</div>
        ))}
      </div>
      <div className="ev-actions">
        <button className="mini" onClick={() => onLocate(ev)}>📄 定位原文</button>
        <button className="mini" onClick={() => onAnnotate(ev)}>💬 批注</button>
        <button className="mini" onClick={() => onVerdict(ev)}>{verdictLabel(ev)}</button>
      </div>
    </div>
  );
}
