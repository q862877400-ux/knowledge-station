// PDF 原件穿透区（R7 / v4.3）：连续滚动模式
// - 所有页垂直排列（连续阅读，非单页翻页）
// - 高亮用 pdfjs viewport.convertToViewportRectangle 变换
// - 跳转时高亮块滚动到视口垂直居中
// - 连续滚动同步（2026-09-02 用户契约）：悬停预览滚动 → 原件按页锚点实时跟随
//   （getSyncSource/syncSourceSeq）；悬停原件滚动 → 只滚原件，预览不动（无反向同步），
//   且单独滚动原件 = 手工校准两窗对应偏差，校准量被记住 —— 回预览滚动后从校准位置
//   继续联动，不被拽回标准映射位；显式跳页（目录/证据卡/黄标）/换文档/缩放时校准清零。
//   页容器在渲染前先按最终口径预置宽高 —— 总滚动高度从加载起即稳定（不再「边渲染边长高」）。
import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.js?url';
import { anchorClauseNumber } from './highlightAnchor';
import type { AnchorRect, AnchorToken } from './highlightAnchor';

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

export interface HighlightSpan {
  page_number: number;
  bbox: [number, number, number, number];
  cid?: string;
  /** 条款号（如 4.1）：存在时只框该条款号标题（短而唯一），缺省回退原 bbox 单框 */
  clauseNumber?: string;
}

interface Box { left: number; top: number; w: number; h: number; cid?: string }

interface Props {
  pdfBytes: ArrayBuffer | null;
  jumpToPage: number | null;
  highlights: HighlightSpan[];
  onSpanHover?: (cid: string, x: number, y: number) => void;
  // 目录/任意跳转的目标页：渲染队列优先渲染该页（否则等前序页渲染完，30 页 PDF 数秒才跳）
  priorityPage?: number | null;
  // 2026-08-26：文本搜索定位——某条款号在非建议页命中时回调真实页，跳转跟随
  onLocatePage?: (page: number) => void;
  // 连续滚动同步源（2026-09-02）：预览滚动容器取值器；syncSourceSeq 在预览挂载/条款集
  // 变化时递增以重挂监听。只做 预览→原件 单向跟随，原件滚轮回写预览（用户契约）。
  getSyncSource?: () => HTMLElement | null;
  syncSourceSeq?: number;
}

export default function PdfViewer({ pdfBytes, jumpToPage, highlights, onSpanHover, priorityPage, onLocatePage, getSyncSource, syncSourceSeq }: Props) {
  const docRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null);
  // 记录 docRef 对应的 pdfBytes 引用：渲染前校验，防止"旧 doc 渲染到新页容器"（换文档后需关开才显示）
  const docBytesRef = useRef<ArrayBuffer | null>(null);
  const pageEls = useRef<Map<number, HTMLDivElement>>(new Map());
  // 滚动容器引用：连续滚动同步的坐标基准（预览 scrollTop ↔ 原件页偏移映射）
  const pdfScrollRef = useRef<HTMLDivElement | null>(null);
  // 手动微调偏移（2026-09-02 用户契约）：悬停原件单独滚动 = 手工校准两窗对应偏差；
  // 校准量在此保存，回到预览滚动后映射在「校准后的相对位置」上继续联动，不被拽回标准位。
  // 清零时机：显式跳页（目录/证据卡/黄标定位）、换文档、页数或缩放变化（重绘 redrawTick 不清）。
  // lastWrittenRef：连续同步最近一次写入的 scrollTop——pdf scroll 事件与其吻合即程序滚动，
  // 不记偏移；programmaticUntilRef：scrollIntoView 跳页的时间窗守卫（落点值无法预知）。
  const manualOffsetRef = useRef(0);
  const lastWrittenRef = useRef(Number.NaN);
  const programmaticUntilRef = useRef(0);
  const offsetKeyRef = useRef('');
  // 2026-08-26：每页文本层 token 缓存（当前渲染批次内有效；跨页搜索条款号用，免重复提取）
  const pageTokensRef = useRef<Map<number, AnchorToken[] | null>>(new Map());
  const [pageCount, setPageCount] = useState(0);
  const [zoom, setZoom] = useState(1.25);
  const [rendered, setRendered] = useState<number[]>([]);
  // 2026-08-28 用户报告偶发"整页上下镜像"（本机三路复现均正立：fitz / headless / headed+GPU，
  // 渲染代码与 CSS 全量审计无任何翻转路径 → 高度疑似瞬时渲染异常或环境级因素）。
  // 一键重绘 = 清空渲染缓存 + 触发渲染 effect 重跑：用户遇任何显示异常可原地恢复，
  // 同时帮我们收集关键判据 —— 重绘后恢复 ⇒ 瞬时异常；重绘后仍镜像 ⇒ 环境级（浏览器/驱动）。
  const [redrawTick, setRedrawTick] = useState(0);
  const redrawAll = () => {
    renderedRef.current = new Set();
    pageTokensRef.current.clear();
    setBoxes({});
    setRendered([]);
    setRedrawTick((t) => t + 1);
  };
  const [boxes, setBoxes] = useState<Record<number, Box[]>>({});
  // 渲染语义（2026-08-24 两轮演进后定稿）：每次渲染只画**当前** highlights 的框，
  // 点新引用时旧框清除（用户只需提醒"这一条在哪"）；换文档时 boxMap 自然重建。
  const renderToken = useRef(0);
  const renderedRef = useRef<Set<number>>(new Set());
  useEffect(() => { renderedRef.current = new Set(); pageTokensRef.current.clear(); }, [zoom]); // 缩放变化需全量重渲染
  // 文本页自动方向纠正：按文本基线的旋转角度检测 90/180/270 度倒置页并自动补偿（无需手工按钮）
  const orientRef = useRef<Record<number, number>>({});
  const detectOrient = async (page: pdfjsLib.PDFPageProxy): Promise<number> => {
    try {
      const tc = await page.getTextContent();
      const buckets: Record<number, number> = { 0: 0, 90: 0, 180: 0, 270: 0 };
      let cnt = 0;
      for (const it of tc.items as any[]) {
        if (!it.transform) continue;
        const a = it.transform[0], b = it.transform[1];
        if (Math.abs(a) < 1e-9 && Math.abs(b) < 1e-9) continue;
        const norm = ((Math.round(Math.atan2(b, a) * 180 / Math.PI) % 360) + 360) % 360;
        const key = norm === 180 ? 180 : (norm === 90 || norm === 270) ? (norm === 90 ? 90 : 270) : 0;
        buckets[key] = (buckets[key] || 0) + 1;
        cnt++;
      }
      if (cnt < 10) return 0; // 无文本层或文本太少（纯扫描页）无法检测，保持原样
      let best = 0, bestN = 0;
      for (const k of [0, 90, 180, 270]) if (buckets[k] > bestN) { bestN = buckets[k]; best = k; }
      // 仅当绝大多数文本（≥90%）一致倾斜时才补偿，避免混合版面/表格页误判
      if (best === 0 || bestN < cnt * 0.9) return 0;
      // 把文本转到正立：180 补 180；90 补 270；270 补 90
      return best === 180 ? 180 : (360 - best) % 360;
    } catch { return 0; }
  };

  // 2026-08-26：与渲染循环一致的页 viewport（跨页文本搜索定位用；orientRef 已由渲染填充）
  const pageViewportOf = async (page: pdfjsLib.PDFPageProxy, n: number) => {
    if (orientRef.current[n] === undefined) {
      orientRef.current[n] = await detectOrient(page);
    }
    const extra = orientRef.current[n] || 0;
    const rot = (page.rotate + extra) % 360;
    const baseW = page.getViewport({ scale: 1, rotation: rot }).width;
    const scrollEl = pageEls.current.get(n)?.parentElement;
    const availW = (scrollEl ? scrollEl.clientWidth : 900) - 8;
    const scale = Math.max(0.5, Math.min(zoom, availW / baseW));
    return page.getViewport({ scale, rotation: rot });
  };

  // 页几何单一口径（2026-09-02 抽取）：预置尺寸遍历与渲染循环共用，防两处漂移
  const layoutOf = async (page: pdfjsLib.PDFPageProxy, n: number) => {
    if (orientRef.current[n] === undefined) {
      orientRef.current[n] = await detectOrient(page);
    }
    const extra = orientRef.current[n] || 0;
    const rot = (page.rotate + extra) % 360;
    const baseW = page.getViewport({ scale: 1, rotation: rot }).width;
    const container = pageEls.current.get(n);
    // 宽度适配：纵向连续阅读，页面宽度不超过容器（不产生横向滚动）
    const scrollEl = pdfScrollRef.current ?? container?.parentElement;
    const availW = (scrollEl ? scrollEl.clientWidth : 900) - 8;
    const scale = Math.max(0.5, Math.min(zoom, availW / baseW));
    return { rot, extra, viewport: page.getViewport({ scale, rotation: rot }) };
  };

  // 加载文档（序列化：只有最新一次加载生效；旧 doc 延迟到新 doc 就绪后再销毁，
  // 避免销毁在途渲染的 page 导致 pdfjs Transport destroyed → 后续加载永久 pending（卡死））
  const loadSeq = useRef(0);
  useEffect(() => {
    const seq = ++loadSeq.current;
    let cancelled = false;
    renderedRef.current = new Set();
    if (!pdfBytes) {
      setPageCount(0); setRendered([]); setBoxes({});
      docBytesRef.current = null;
      pageTokensRef.current.clear();
      return;
    }
    (async () => {
      try {
        const task = pdfjsLib.getDocument({ data: pdfBytes.slice(0) });
        const doc = await task.promise;
        if (cancelled || seq !== loadSeq.current) { doc.destroy(); return; }
        const old = docRef.current;
        docRef.current = doc;
        docBytesRef.current = pdfBytes;   // 绑定当前 bytes 引用（渲染前校验用）
        orientRef.current = {}; // 换文档必须清空方向缓存（页号会在不同文档间复用）
        setPageCount(doc.numPages);
        setRendered([]); setBoxes({});
        pageTokensRef.current.clear();
        // 清掉所有旧画布（换文档后页容器复用，杜绝上一个文档残留像素）
        pageEls.current.forEach((el) => {
          el.querySelector('canvas')?.remove();
          el.style.width = ''; el.style.height = '';
        });
        // 旧 doc 延迟销毁（给在途渲染一帧时间退出）
        if (old) setTimeout(() => { try { old.destroy(); } catch { /* 已销毁 */ } }, 300);
      } catch (e) { console.error('PDF 加载失败', e); }
    })();
    return () => { cancelled = true; };
  }, [pdfBytes]);

  // 分批渲染所有页（每帧 2 页，避免卡死）
  useEffect(() => {
    const doc = docRef.current;
    // 关键校验：docRef 必须对应当前 pdfBytes（换文档时旧 doc 可能尚未被销毁/替换，
    // 若用旧 doc 渲染到新页容器 → 画面空白/错乱）。校验失败安排一次重试兜底，
    // 防止加载完成早于本 effect 触发导致永远跳过（白屏卡死）。
    if (!doc || pageCount === 0 || docBytesRef.current !== pdfBytes) {
      const t = setTimeout(() => setRendered((r) => [...r]), 200);
      return () => clearTimeout(t);
    }
    const token = ++renderToken.current;
    let stop = false;
    (async () => {
      // 预置尺寸（2026-09-02）：先按最终渲染口径给全部页容器设宽高（纯取景，无光栅化，毫秒级）。
      // 总滚动高度从加载起即稳定 → 消除「边渲染边长高」造成的滚动位置漂移与跳顶，
      // 且未渲染页也有真实高度 → 预览→原件连续映射全程精确。
      for (let n = 1; n <= pageCount; n++) {
        if (stop || token !== renderToken.current) return;
        try {
          const page = await doc.getPage(n);
          const { rot, extra, viewport } = await layoutOf(page, n);
          const container = pageEls.current.get(n);
          if (container) {
            container.dataset.rot = String(rot);
            container.dataset.extra = String(extra);
            container.dataset.rotate = String(page.rotate);
            container.style.width = viewport.width + 'px';
            container.style.height = viewport.height + 'px';
          }
        } catch { /* 单页取景失败：渲染循环内再兜底 */ }
      }
      const done: number[] = [];
      // 只画当前证据的高亮：不再从旧的 boxes 合并（旧法会让多个引用/跨时间线的框累积）。
      // 点新引用时旧框清除，只保留当前条款的框（用户只需提醒"这一条在哪"）。
      const boxMap: Record<number, Box[]> = {};
      // 2026-08-26 跨页定位：本页未锚定的条款号入列，全文档渲染完后做文本搜索
      const pending: { page: number; bboxRect: AnchorRect; clauseNumber?: string; cid?: string }[] = [];
      // 高亮页 + priorityPage（目录点击）优先渲染（引用/目录跳转快速显示），其余按序补齐
      const hlPages = [...new Set(highlights.map((s) => s.page_number))];
      if (priorityPage && priorityPage >= 1 && priorityPage <= pageCount
          && !hlPages.includes(priorityPage)) {
        hlPages.push(priorityPage);
      }
      const order = [...hlPages];
      for (let n = 1; n <= pageCount; n++) {
        if (!order.includes(n)) order.push(n);
      }
      for (const n of order) {
        if (stop || token !== renderToken.current) return;
        const hsNow = highlights.filter((s) => s.page_number === n);
        // 已渲染且本页无高亮：跳过重渲染（避免每次点引用全量重画造成的抖动/乱跳）
        if (renderedRef.current.has(n) && hsNow.length === 0) continue;
        try {
          const page = await doc.getPage(n);
          const container = pageEls.current.get(n);
          // 几何与预置尺寸同一口径（layoutOf 单一 owner）
          const { rot, extra, viewport } = await layoutOf(page, n);
          if (container) {
            container.dataset.rot = String(rot);
            container.dataset.extra = String(extra);
            container.dataset.rotate = String(page.rotate);
            container.style.width = viewport.width + 'px';
            container.style.height = viewport.height + 'px';
            let canvas = container.querySelector('canvas') as HTMLCanvasElement | null;
            if (!canvas) {
              canvas = document.createElement('canvas');
              container.appendChild(canvas);
            }
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            canvas.style.width = viewport.width + 'px';
            canvas.style.height = viewport.height + 'px';
            await page.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise;
          }
          const hs = highlights.filter((s) => s.page_number === n);
          // bbox 契约（v5 实测修复）：MinerU middle.json 的 bbox 是 **PDF 底部原点**（左下，y 向上，
          // 页顶文本 y≈页高），pipeline 原样直存。pdfjs convertToViewportPoint 同样期望
          // PDF 底部原点坐标 —— 直接传入即可，**禁止再做 H−y 翻转**（会双重翻转导致黄标镜像）。
          //
          // 内容锚定（2026-08-25 改造）：不再"几何邻域 1.2x 加宽取并集"（旧法跨条/跨表疯涨）。
          // 文本项坐标同为 PDF 底部原点（与 bbox 同系），仍只经 convertToViewportRectangle 转换，
          // 禁止再做 H−y 翻转。
          const pageBoxes: Box[] = [];
          if (hs.length) {
            let items: any[] | null = null;
            try {
              const tc = await page.getTextContent();
              items = (tc.items as any[]).filter((it) => it.str && it.str.trim().length > 0);
            } catch { /* 无文本层：items=null 走回退 */ }
            // 文本项统一转成带 viewport 矩形的 token，供"条款号匹配"使用
            let tokens: AnchorToken[] | null = null;
            if (items && items.length) {
              tokens = items.map((it) => {
                const ir = viewport.convertToViewportRectangle([
                  it.transform[4], it.transform[5],
                  it.transform[4] + (it.width || 0), it.transform[5] + (it.height || 0),
                ]);
                return {
                  str: it.str,
                  left: Math.min(ir[0], ir[2]), top: Math.min(ir[1], ir[3]),
                  right: Math.max(ir[0], ir[2]), bottom: Math.max(ir[1], ir[3]),
                };
              });
            }
            pageTokensRef.current.set(n, tokens);
            for (const s of hs) {
              const [x1, y1, x2, y2] = s.bbox;
              const rr = viewport.convertToViewportRectangle(
                [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)]);
              const bboxRect: AnchorRect = {
                left: Math.min(rr[0], rr[2]), top: Math.min(rr[1], rr[3]),
                right: Math.max(rr[0], rr[2]), bottom: Math.max(rr[1], rr[3]),
              };
              // 定位主通道 = 文本层搜索条款号（短而唯一）：锚定即框住真实文字，不依赖 bbox。
              // 无文本层 → 直接 bbox 区域近似（乱码扫描件无法文字定位）。
              // 本页未命中 → 记 pending，循环后全文档搜索（条款号可能因数据错页在别的页）。
              let out: AnchorRect | null = null;
              if (tokens && s.clauseNumber && s.clauseNumber.trim()) {
                out = anchorClauseNumber(tokens, s.clauseNumber);
              }
              if (out) {
                pageBoxes.push({ left: out.left, top: out.top, w: out.right - out.left, h: out.bottom - out.top, cid: s.cid });
              } else if (!tokens) {
                pageBoxes.push({ left: bboxRect.left, top: bboxRect.top, w: bboxRect.right - bboxRect.left, h: bboxRect.bottom - bboxRect.top, cid: s.cid });
              } else {
                pending.push({ page: n, bboxRect, clauseNumber: s.clauseNumber, cid: s.cid });
              }
            }
          }
          if (pageBoxes.length) boxMap[n] = pageBoxes;
          renderedRef.current.add(n);
          done.push(n);
        } catch (e) {
          // 单页渲染失败：清掉该页画布，避免残留上一文档的像素
          const c = pageEls.current.get(n)?.querySelector('canvas');
          if (c) c.getContext('2d')?.clearRect(0, 0, c.width, c.height);
        }
        setRendered([...done]);
        if (Object.keys(boxMap).length) { setBoxes(boxMap); }
        // page.render 的 await 本身已让步主线程；不再额外等待（后台标签页定时器会被节流）
      }

      // ---- 跨页文本搜索定位（2026-08-26）：本页未命中条款号 → 全文档搜文本层 ----
      // 框=真实文字位置（与渲染同源坐标，绝不偏移）；bbox 只在无文本层时作区域近似。
      for (const p of pending) {
        if (stop || token !== renderToken.current) return;
        if (!p.clauseNumber) {  // 无条款号（理论不可达）：回退建议页 bbox
          boxMap[p.page] = [...(boxMap[p.page] || []),
            { left: p.bboxRect.left, top: p.bboxRect.top,
              w: p.bboxRect.right - p.bboxRect.left, h: p.bboxRect.bottom - p.bboxRect.top,
              cid: p.cid }];
          continue;
        }
        let hit: AnchorRect | null = null;
        let hitPage = -1;
        for (let q = 1; q <= pageCount && !hit; q++) {
          if (q === p.page) continue;
          let toks = pageTokensRef.current.get(q);
          if (toks === undefined) {
            try {
              const qpage = await doc.getPage(q);
              const qv = await pageViewportOf(qpage, q);
              const qitems = (await qpage.getTextContent()).items as any[];
              toks = qitems.filter((it) => it.str && it.str.trim().length > 0).map((it) => {
                const ir = qv.convertToViewportRectangle([
                  it.transform[4], it.transform[5],
                  it.transform[4] + (it.width || 0), it.transform[5] + (it.height || 0),
                ]);
                return { str: it.str, left: Math.min(ir[0], ir[2]), top: Math.min(ir[1], ir[3]), right: Math.max(ir[0], ir[2]), bottom: Math.max(ir[1], ir[3]) };
              });
            } catch { toks = null; }
            pageTokensRef.current.set(q, toks);
          }
          if (!toks) continue;
          hit = anchorClauseNumber(toks, p.clauseNumber);
          if (hit) hitPage = q;
        }
        if (hit && hitPage > 0) {
          boxMap[hitPage] = [...(boxMap[hitPage] || []),
            { left: hit.left, top: hit.top, w: hit.right - hit.left, h: hit.bottom - hit.top, cid: p.cid }];
          if (hitPage !== p.page) onLocatePage?.(hitPage);  // 跳转跟随真实页
        } else {
          boxMap[p.page] = [...(boxMap[p.page] || []),
            { left: p.bboxRect.left, top: p.bboxRect.top,
              w: p.bboxRect.right - p.bboxRect.left, h: p.bboxRect.bottom - p.bboxRect.top,
              cid: p.cid }];  // 回退区域近似
        }
      }
      if (Object.keys(boxMap).length) { setBoxes({ ...boxMap }); }
    })();
    return () => { stop = true; };
  }, [pageCount, zoom, pdfBytes, highlights, priorityPage, redrawTick]);

  // 跳页：等目标页渲染后滚动到视口垂直居中（黄标未渲染时反复轮询，避免跳到页首）
  // 用 behavior:'auto'（即时）替代 'smooth'——smooth 在大页距下要滚几秒，感知上"点一下好几秒才跳"（2026-08-23 修）
  // 依赖只留 jumpToPage（2026-09-02）：旧依赖含 boxes/rendered，后台分批渲染每帧 setState 都会
  // 重触发本 effect，把用户手动滚开的页面拽回居中位（「弹回」根因）；页容器已预置尺寸，
  // 目标元素首次尝试即命中真实高度，不再落顶。黄标跨页修正经 onLocatePage→jumpToPage 变化自然触发。
  useEffect(() => {
    if (!jumpToPage) return;
    // 显式跳页 = 绝对定位语义：清除用户手动微调偏移（校准只服务自由浏览，不覆盖跳页意图）
    manualOffsetRef.current = 0;
    const waitFor = (attempt: number) => {
      const el = pageEls.current.get(jumpToPage);
      const hl = el?.querySelector('.pdf-highlight') as HTMLElement | null;
      const target = hl ?? el;
      if (target) {
        // 已在视口中部附近就不再滚动（避免多轮 setState 触发反复滚动 = 乱跳）
        const r = target.getBoundingClientRect();
        const cy = r.top + r.height / 2;
        if (Math.abs(cy - window.innerHeight / 2) > 150) {
          // scrollIntoView 落点 scrollTop 无法预知 → 时间窗守卫，防被误记为手动微调
          programmaticUntilRef.current = performance.now() + 300;
          target.scrollIntoView({ block: 'center', behavior: 'auto' });
        }
        return;
      }
      if (attempt < 50) {
        setTimeout(() => waitFor(attempt + 1), 100);
      } else if (el) {
        programmaticUntilRef.current = performance.now() + 300;
        el.scrollIntoView({ block: 'center', behavior: 'auto' });
      }
    };
    waitFor(0);
  }, [jumpToPage]);

  // 连续滚动同步（2026-09-02 用户契约，单向 预览→原件）：
  // - 悬停预览窗格滚动（滚轮/拖滚动条/键盘）→ 预览原生滚动，本 effect 按页锚点把原件
  //   scrollTop 逐帧映射（rAF 合帧）→ 两窗实时同步滚动。
  // - 悬停原件窗格滚动 → 原件原生滚动，预览不动（无反向监听 → 无同步环路 → 不弹回）；
  //   同时把「实际位置 − 标准映射位」记为手动微调偏移，回预览滚动后从校准位置继续联动。
  // - 映射基准：预览内 [data-page] 锚点（条款 data-page + content_html 页界 div，页级
  //   一一对应）↔ 原件页容器；页内线性插值 f → 原件 scrollTop = 页顶 + f × 页跨
  //   （页跨取下一页容器顶差，含页间距，与视觉一致）。
  useEffect(() => {
    const pv = getSyncSource?.();
    const sc = pdfScrollRef.current;
    if (!pv || !sc || pageCount === 0) return;
    // 键控清零：换文档/页数/缩放变化后旧像素偏移失义；redrawTick 不在键内 → 一键重绘保留校准
    const offsetKey = `${syncSourceSeq ?? ''}|${pageCount}|${zoom}|${pdfBytes?.byteLength ?? 0}`;
    if (offsetKeyRef.current !== offsetKey) {
      manualOffsetRef.current = 0;
      offsetKeyRef.current = offsetKey;
    }
    let raf = 0;
    // 标准映射位（不含手动微调）：预览 scrollTop → 原件 scrollTop；未就绪返回 null
    const baseTarget = (): number | null => {
      const nodes = pv.querySelectorAll<HTMLElement>('[data-page]');
      if (!nodes.length) return null;
      const pvRect = pv.getBoundingClientRect();
      const anchors: { page: number; top: number }[] = [];
      const seen = new Set<number>();
      nodes.forEach((el) => {
        const p = parseInt(el.dataset.page || '', 10);
        if (!p || p < 1 || seen.has(p)) return;   // 同页多锚点取 DOM 首见（页内容起点）
        seen.add(p);
        anchors.push({ page: p, top: el.getBoundingClientRect().top - pvRect.top + pv.scrollTop });
      });
      if (!anchors.length) return null;
      anchors.sort((a, b) => a.top - b.top);
      const st = pv.scrollTop;
      let idx = 0;
      while (idx + 1 < anchors.length && anchors[idx + 1].top <= st) idx++;
      const a = anchors[idx];
      const spanPv = idx + 1 < anchors.length
        ? anchors[idx + 1].top - a.top
        : Math.max(1, pv.scrollHeight - pv.clientHeight - a.top);   // 末锚点后按剩余正文映射
      const f = Math.min(1, Math.max(0, (st - a.top) / spanPv));
      const pageEl = pageEls.current.get(a.page);
      if (!pageEl || pageEl.offsetHeight === 0) return null;   // 未预置尺寸（极端时序）：本帧不动
      const scRect = sc.getBoundingClientRect();
      const pageTop = pageEl.getBoundingClientRect().top - scRect.top + sc.scrollTop;
      const nextPage = pageEls.current.get(a.page + 1);
      const spanPdf = nextPage
        ? Math.max(1, nextPage.getBoundingClientRect().top - scRect.top + sc.scrollTop - pageTop)
        : Math.max(1, pageEl.offsetHeight);
      return pageTop + f * spanPdf;
    };
    const sync = (): boolean => {
      raf = 0;
      const base = baseTarget();
      if (base === null) return false;
      const target = base + manualOffsetRef.current;
      lastWrittenRef.current = target;
      sc.scrollTop = target;
      return true;
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(() => { sync(); }); };
    pv.addEventListener('scroll', onScroll, { passive: true });
    // 原件侧监听：区分程序写入（scrollTop 与 lastWritten 吻合 / 跳页时间窗内）与用户手动滚
    // ——只有手动滚才更新微调偏移（差额 = 当前实际位 − 标准映射位），预览侧零感知。
    const onPdfScroll = () => {
      if (performance.now() < programmaticUntilRef.current) return;
      if (Math.abs(sc.scrollTop - lastWrittenRef.current) < 2) return;
      const base = baseTarget();
      if (base === null) return;
      manualOffsetRef.current = sc.scrollTop - base;
    };
    sc.addEventListener('scroll', onPdfScroll, { passive: true });
    // 挂载/换文档/缩放后先对齐一次：打开「看原件」即落在预览当前位置对应的页。
    // 预置尺寸遍历是异步的（getPage 逐页取景）——页高未就绪时有界重试（≤40 帧 ≈ 0.7s）。
    let tries = 0;
    const align = () => {
      if (sync()) return;
      if (tries++ < 40) raf = requestAnimationFrame(align);
    };
    raf = requestAnimationFrame(align);
    return () => {
      pv.removeEventListener('scroll', onScroll);
      sc.removeEventListener('scroll', onPdfScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [getSyncSource, syncSourceSeq, pageCount, zoom, pdfBytes, redrawTick]);

  if (!pdfBytes) {
    return (
      <div className="pdf-placeholder">
        <div className="pdf-placeholder-icon">📖</div>
        <div className="pdf-placeholder-title">PDF 原件证据穿透区</div>
        <div className="pdf-placeholder-sub">点击回答中的引用，自动翻页并用黄框圈出原文位置</div>
      </div>
    );
  }

  return (
    <div className="pdf-outer">
      <div className="pdf-toolbar">
        <span>连续阅读</span>
        <button onClick={redrawAll} title="页面显示异常（空白/错乱/颠倒/镜像）时点此全部重绘"
          style={{ marginLeft: 10, cursor: 'pointer' }}>🔄 重绘</button>
        <div className="pdf-zoom-group">
          <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} title="缩小">−</button>
          <span className="pdf-zoom-label">{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(3, z + 0.25))} title="放大">＋</button>
        </div>
      </div>
      <div className="pdf-scroll" ref={pdfScrollRef}>
        {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => (
          <div key={n}
            ref={(el) => { if (el) pageEls.current.set(n, el); }}
            className="pdf-page">
            {(boxes[n] || []).map((b, i) => (
              <div key={i} className="pdf-highlight"
                style={{ left: b.left, top: b.top, width: b.w, height: b.h }}
                onMouseOver={(e) => { if (b.cid) onSpanHover?.(b.cid, e.clientX, e.clientY); }}
                onMouseOut={() => onSpanHover?.('', 0, 0)} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
