"""流程图结构化识别与矢量重绘 v2（2026-08-29，GB/T 34406 图1 实测调参，语料级通用）。

v1 教训：箭头连线把框连成一个大连通体，RETR_EXTERNAL 外轮廓=整图边界，
框提取全灭（实测图1 只剩 2 个假节点=文字被 close 粘成的条）。

v2 核心：**内孔（hole）方案**——
- 空心闭合框（矩形/菱形）在二值化+闭运算后必然围出一个白区「内孔」，
  findContours(RETR_CCOMP) 层级里 hole 的 bbox ≈ 框内区；
- 箭头/连线不闭合 → 无孔；散点图坐标轴是 U 形（无顶边）→ 无孔；
  文字字符块太小被面积过滤 → 天然只剩「框」。结构判别力极强。
- 菱形判别：孔多边形面积 / 孔 bbox ≈0.5（菱形内切）vs ≈1.0（矩形）。

每步置信度门槛，任一环不达标整体回退 None → 端点落回 PNG 截图，
重绘永远不会比截图差。零文档特判，只依赖形态学。
"""
from __future__ import annotations

import threading
from typing import List, Optional

_ONE_SHOT = threading.Lock()
_OCR = None


def get_ocr():
    """RapidOCR 惰性单例（模型 ~2s 首载）。公共入口：图内文字识别的
    统一本地引擎（figure_redraw 框内认字 / local_vision 截图反查共用）。"""
    global _OCR
    if _OCR is None:
        with _ONE_SHOT:
            if _OCR is None:
                from rapidocr_onnxruntime import RapidOCR
                _OCR = RapidOCR()
    return _OCR


def _render_clip(pdf_path: str, page_no: int, rect):
    """clip 区域 300dpi 渲染 → 灰度 ndarray"""
    import fitz
    import numpy as np
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_no]
        pix = page.get_pixmap(clip=rect, dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)
        if pix.n >= 3:
            return img[:, :, :3].mean(axis=2)
        return img[:, :, 0].astype(float)
    finally:
        doc.close()


def try_redraw(pdf_path: str, page_no: int, rect) -> Optional[str]:
    """对 clip 矩形（fitz.Rect，pt）尝试流程图矢量重绘。

    返回 SVG 字符串（成功）或 None（结构不达标 → 端点回退 PNG 截图）。
    """
    import cv2
    import numpy as np

    gray = _render_clip(pdf_path, page_no, rect)
    h, w = gray.shape
    if w < 120 or h < 120:
        return None
    scale = 300 / 72.0

    bw = (gray < 170).astype(np.uint8) * 255
    if bw.mean() < 3 or bw.mean() > 40:
        return None

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)

    # 1. 内孔检测（RETR_CCOMP：第二层 hole）→ 候选框
    contours, hierarchy = cv2.findContours(closed, cv2.RETR_CCOMP,
                                           cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return None
    hierarchy = hierarchy[0]
    nodes = []                       # (bbox, kind) bbox=框外缘（孔外扩线宽）
    for i, c in enumerate(contours):
        if hierarchy[i][3] < 0:      # 只看 hole（有父=孔）
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        ba = cw * ch
        # 孔尺寸门槛：≥0.15% 图面积、40x26 起；上限 45% 图高——散点图坐标轴
        # 若意外闭合，其孔占图 80%+，在此拦截
        if ba < 0.0015 * w * h or cw < 40 or ch < 26 or ch > 0.45 * h or cw > 0.8 * w:
            continue
        area = abs(cv2.contourArea(c))
        ratio = area / ba if ba else 0
        kind = "diamond" if ratio < 0.72 else "rect"
        # 孔 → 框外缘：外扩线宽+近邻文字余量（300dpi 线宽 ~4px）
        pad = 7
        nodes.append({"x": max(0, x - pad), "y": max(0, y - pad),
                      "w": min(w, x + cw + pad) - max(0, x - pad),
                      "h": min(h, y + ch + pad) - max(0, y - pad),
                      "kind": kind})
    if not (3 <= len(nodes) <= 24):  # 流程图至少 3 框（起→判→终）
        return None
    nodes.sort(key=lambda n: (n["y"], n["x"]))

    # 2. OCR 全图一次；文字按中心落框
    try:
        ocr = get_ocr()
        result, _ = ocr(gray.astype(np.uint8))
    except Exception:
        return None
    if not result:
        return None
    node_texts: List[List[tuple[float, float, str]]] = [[] for _ in nodes]
    loose_texts: List[tuple[float, float, str]] = []  # 框外文本（分支条件/是否标签候选）
    for box, text, conf in result:
        if conf < 0.55 or not text.strip():
            continue
        cx = float(np.mean([p[0] for p in box]))
        cy = float(np.mean([p[1] for p in box]))
        hit = None
        for i, nd in enumerate(nodes):
            if nd["x"] - 4 <= cx <= nd["x"] + nd["w"] + 4 and \
               nd["y"] - 4 <= cy <= nd["y"] + nd["h"] + 4:
                hit = i
                break
        t = text.strip()
        if hit is not None:
            node_texts[hit].append((cy, cx, t))
        elif len(t) <= 14:           # 框外短文本：分支条件（≥90.00）/是/否
            loose_texts.append((cx, cy, t))

    filled = sum(1 for t in node_texts if t)
    if filled / len(nodes) < 0.6:    # 空框过多=识别失败
        return None

    # 3. 连线：墨迹减全部框 bbox（膨胀4px）→ 长连通域=箭头
    mask = bw.copy()
    for nd in nodes:
        x0 = max(0, nd["x"] - 4); y0 = max(0, nd["y"] - 4)
        x1 = min(w, nd["x"] + nd["w"] + 4); y1 = min(h, nd["y"] + nd["h"] + 4)
        mask[y0:y1, x0:x1] = 0
    n_lab, labels = cv2.connectedComponents(mask, connectivity=8)
    raw_edges: list[tuple[int, int, None, int, tuple]] = []
    for lab in range(1, n_lab):
        ys, xs = np.where(labels == lab)
        if len(xs) < 60:
            continue
        span = max(xs.max() - xs.min(), ys.max() - ys.min())
        if span < 24:                # 残点（文字边角/噪点）
            continue
        cand = []
        for i, nd in enumerate(nodes):
            ncx, ncy = nd["x"] + nd["w"] / 2, nd["y"] + nd["h"] / 2
            d = np.sqrt((xs - ncx) ** 2 + (ys - ncy) ** 2).min()
            if d < max(nd["w"], nd["h"]) * 0.8 + 30:
                cand.append((d, i))
        cand.sort()
        uniq = []
        for _, i in cand:
            if i not in uniq:
                uniq.append(i)
            if len(uniq) == 2:
                break
        if len(uniq) != 2:
            continue
        a, b = uniq
        raw_edges.append((a, b, None, len(xs), (xs.min(), xs.max(),
                                                ys.min(), ys.max())))

    if len(raw_edges) < 2:           # 流程图至少主链 2 条边
        return None

    # 4. 同对节点去重（保留最长）——同一箭头被框 bbox 裁断会产生多段连通域，
    #    必须先归并到一条逻辑边，标签挂接才不会落到被丢弃的分段上
    seen: dict[tuple[int, int], int] = {}
    for k, (a, b, _l, _ln, _bb) in enumerate(raw_edges):
        key = (min(a, b), max(a, b))
        if key not in seen or raw_edges[k][3] > raw_edges[seen[key]][3]:
            seen[key] = k

    # 5. 框外短文本挂最近边（点到线段距离 <130px）：GB 流程图把分支条件
    #    （"相似度匹配值≥90.00"/"判别为"珍珠粉""/是/否）写在箭头旁——
    #    实测距边线段 76~121px
    import numpy as _np

    def _seg_dist(px, py, x1, y1, x2, y2):
        vx, vy = x2 - x1, y2 - y1
        L2 = vx * vx + vy * vy
        if L2 == 0:
            return _np.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L2))
        return _np.hypot(px - (x1 + t * vx), py - (y1 + t * vy))

    edge_label_map: dict[tuple[int, int], str] = {}  # seen key → 标签文本
    for (cx, cy, t) in loose_texts:
        best: Optional[tuple[int, int]] = None
        bd = 130.0
        for key, k in seen.items():
            a, b, _l, _ln, bb = raw_edges[k]
            na, nb = nodes[a], nodes[b]
            d = _seg_dist(cx, cy,
                          na["x"] + na["w"] / 2, na["y"] + na["h"] / 2,
                          nb["x"] + nb["w"] / 2, nb["y"] + nb["h"] / 2)
            # 标签常压在箭头侧旁：允许到线段距离 + 边 bbox 邻近双条件
            if d < bd and bb[0] - 90 <= cx <= bb[1] + 90 and \
               bb[2] - 90 <= cy <= bb[3] + 90:
                best, bd = key, d
        if best is not None:
            edge_label_map[best] = t if edge_label_map.get(best) is None \
                else edge_label_map[best] + t

    # 6. 方向：主流自上而下
    fin_edges = []
    for key, k in seen.items():
        a, b, _l, _ln, _bb = raw_edges[k]
        if nodes[a]["y"] > nodes[b]["y"] + 8:
            a, b = b, a
        fin_edges.append((a, b, edge_label_map.get(key)))

    return _build_svg(nodes, node_texts, fin_edges, w, h, scale)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _build_svg(nodes, node_texts, edges, w_px: int, h_px: int, scale: float):
    """节点/边 → SVG（pt 坐标）"""
    w_pt = w_px / scale
    h_pt = h_px / scale

    def pt(v):
        return round(v / scale, 1)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_pt:g} {h_pt:g}" '
           f'role="img" style="background:#fff">',
           '<defs><marker id="fa" markerWidth="7" markerHeight="7" refX="6" refY="3" '
           'orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#333"/></marker></defs>']

    def node_center(i):
        nd = nodes[i]
        return (nd["x"] + nd["w"] / 2, nd["y"] + nd["h"] / 2)

    def anchor(i, j):
        nd = nodes[i]
        cx, cy = node_center(i)
        tx, ty = node_center(j)
        hw, hh = nd["w"] / 2, nd["h"] / 2
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        if abs(dx * hh) > abs(dy * hw):
            ex = cx + (hw if dx > 0 else -hw)
            return ex, cy + dy * (hw / abs(dx)) * 0.35
        ey = cy + (hh if dy > 0 else -hh)
        return cx + dx * (hh / abs(dy)) * 0.35, ey

    for (a, b, label) in edges:
        x1, y1 = anchor(a, b)
        x2, y2 = anchor(b, a)
        out.append(f'<line x1="{pt(x1)}" y1="{pt(y1)}" x2="{pt(x2)}" y2="{pt(y2)}" '
                   f'stroke="#333" stroke-width="1.2" marker-end="url(#fa)"/>')
        if label:
            out.append(f'<text x="{pt((x1 + x2) / 2 + 8)}" y="{pt((y1 + y2) / 2 - 3)}" '
                       f'font-size="9" fill="#333">{_esc(label)}</text>')

    for i, nd in enumerate(nodes):
        x, y = pt(nd["x"]), pt(nd["y"])
        wp, hp = pt(nd["w"]), pt(nd["h"])
        if nd["kind"] == "diamond":
            cx, cy = pt(nd["x"] + nd["w"] / 2), pt(nd["y"] + nd["h"] / 2)
            pts = f"{cx},{y} {pt(nd['x'] + nd['w'])},{cy} {cx},{pt(nd['y'] + nd['h'])} {x},{cy}"
            out.append(f'<polygon points="{pts}" fill="#fff" stroke="#333" '
                       f'stroke-width="1.2"/>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{wp}" height="{hp}" fill="#fff" '
                       f'stroke="#333" stroke-width="1.2"/>')
        lines = [t for (_cy, _cx, t) in sorted(node_texts[i])]
        text = "".join(lines)
        if text:
            fs = 9.5
            max_chars = max(4, int(wp / (fs * 0.62)) - 1)
            chunks = [text[k:k + max_chars] for k in range(0, len(text), max_chars)][:4]
            ty0 = pt(nd["y"] + nd["h"] / 2) - (len(chunks) - 1) * fs * 0.62
            for k, seg in enumerate(chunks):
                out.append(f'<text x="{pt(nd["x"] + nd["w"] / 2)}" '
                           f'y="{round(ty0 + k * fs * 1.25, 1)}" text-anchor="middle" '
                           f'font-size="{fs}" fill="#111" '
                           f'font-family="SimSun,serif">{_esc(seg)}</text>')
    out.append("</svg>")
    return "\n".join(out)
