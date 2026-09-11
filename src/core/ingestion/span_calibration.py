"""span 坐标系通用自动校准（R-B，pipeline/13-round3.md）。

通解：对每页用 fitz words 按 y 聚类构建**文字行中心表**（顶部原点），对每个 span 的 bbox
中心取两种解释——「直读（顶部原点）」与「H−y 换算（底部原点）」——各找与最近文字行的距离，
**近者胜**（最近行匹配，解决 50140 碎片投票分裂的根因：旧法拿碎片中心比条款块首行，
碎片越靠后偏差越大）。文档级投票多数决，判为顶部原点则全量翻转 y'=H−y 归一为底部原点。

两个入口：
- ``calibrate``：存量校准（读库全部 span → 投票 → UPDATE by rowid + event_log 审计）；
  scripts/repair_span_origin.py 复用本函数。
- ``calibrate_new``：纯函数版（内存 span 列表投票归一为底部原点，不落库）；
  pipeline.run_full_ingest 写库前调用。已底部原点的文档投票全 bottom、零改动（幂等）。

坐标契约：归一目标 = **PDF 底部原点**（左下原点，y 向上），前端 pdfjs convertToViewport*
直接消费，见 PdfViewer.tsx bbox 契约注释。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from ulid import ULID

import fitz


def page_line_centers(page: fitz.Page) -> list[float]:
    """fitz words 按 y 聚类成行，返回每行中心 y（顶部原点，升序）。

    聚类容差 = max(2pt, 中位词高一半)：正文行距 ~1.2 倍字高不会误并，标题/表格小间隙不误拆。
    """
    words = page.get_text("words") or []
    if not words:
        return []
    heights = sorted(w[3] - w[1] for w in words)
    tol = max(2.0, 0.5 * heights[len(heights) // 2])
    centers = sorted((w[1] + w[3]) / 2.0 for w in words)
    lines: list[float] = []
    group: list[float] = [centers[0]]
    for cy in centers[1:]:
        if cy - group[-1] <= tol:
            group.append(cy)
        else:
            lines.append(sum(group) / len(group))
            group = [cy]
    lines.append(sum(group) / len(group))
    return lines


def _vote_from_centers(lines: list[float], page_h: float, bbox: Any) -> str | None:
    """给定行中心表的投票内核：bbox 中心直读 vs H−y 换算，距最近文字行近者胜。

    平票判 bottom（保守：翻转只在证据明确时发生）。无文字行返回 None。
    """
    if not lines:
        return None
    cy = (float(bbox[1]) + float(bbox[3])) / 2.0
    d_top = min(abs(cy - c) for c in lines)          # 直读解释（顶部原点）
    d_bot = min(abs((page_h - cy) - c) for c in lines)  # 换算解释（底部原点）
    return "bottom" if d_bot <= d_top else "top"


def vote_origin(page: fitz.Page, bbox: Any) -> str | None:
    """bbox 中心两种解释（直读 / H−y）各找最近文字行距离，近者胜；无行返回 None。"""
    return _vote_from_centers(page_line_centers(page), page.rect.height, bbox)


def band_text_hit(page: fitz.Page, bbox_raw: Any, content_text: str) -> bool:
    """带内文字真值最终裁决 v3（2026-08-25）：

    raw bbox 按「顶部原点」解释取带，带内文字取首/中 8 字窗口，命中条款正文即算命中
    （mid-block 片段的带内是条款中段文字，不含开头——v2 严格版在此大量误判"无法定位"）。
    带内无文字或窗口不命中 → False（错误解释的带会落在无关内容上，不会命中）。
    """
    frag = (content_text or "").replace(" ", "").replace("\n", "")
    if len(frag) < 8:
        return False
    r = fitz.Rect(*[float(v) for v in bbox_raw])
    txt = page.get_text("text", clip=r).replace(" ", "").replace("\n", "")
    if len(txt) < 6:
        return False
    windows = {txt[:8], txt[max(0, len(txt) // 2 - 4):][:8]}
    return any(len(w) >= 6 and w in frag for w in windows)


def _flip_bbox(bbox: Any, page_h: float) -> list[float]:
    """顶部原点 → 底部原点：y'=H−y（端点交换）。保留 x 与 2 位小数。"""
    b = [float(v) for v in bbox]
    return [b[0], round(page_h - b[3], 2), b[2], round(page_h - b[1], 2)]


def _span_get(span: Any, key: str, default: Any = None) -> Any:
    if isinstance(span, dict):
        return span.get(key, default)
    return getattr(span, key, default)


def _span_set(span: Any, key: str, value: Any) -> None:
    if isinstance(span, dict):
        span[key] = value
    else:
        setattr(span, key, value)


def _vote_spans(doc: "fitz.Document", spans: list[Any]) -> tuple[dict[int, list[float]], dict[int, float], int, int]:
    """全量 span 逐条投票（页级缓存行中心表/页高），返回 (行中心表, 页高, top 票, bottom 票)。"""
    centers_cache: dict[int, list[float]] = {}
    heights: dict[int, float] = {}
    votes_top = votes_bottom = 0
    for s in spans:
        pno = int(_span_get(s, "page_number", 0))
        if pno < 1 or pno > doc.page_count:
            continue
        if pno not in centers_cache:
            page = doc[pno - 1]
            centers_cache[pno] = page_line_centers(page)
            heights[pno] = page.rect.height
        v = _vote_from_centers(centers_cache[pno], heights[pno], _span_get(s, "bbox"))
        if v == "top":
            votes_top += 1
        elif v == "bottom":
            votes_bottom += 1
    return centers_cache, heights, votes_top, votes_bottom


def _stratified_sample(spans: list[Any], cap: int = 60) -> list[Any]:
    """均匀分层采样（前/中/后全覆盖），cap 封顶。spans 需已按 (page, sort_order) 排序。"""
    n = len(spans)
    if n <= cap:
        return spans
    step = n / cap
    return [spans[int(i * step)] for i in range(cap)]


def _direction_votes(doc: "fitz.Document", spans: list[Any],
                     groups: list[list[Any]] | None = None) -> tuple[int, int]:
    """同页多 span 条款的"阅读方向"判别（**无镜像对称**，v2 通解）：

    - 同一条款在同一页内 ≥2 个 span 时，底部原点坐标下 y 随 sort_order **严格递减**
      （y 向上）；顶部原点则**严格递增**。
    - 返回 (dec, inc)：y 严格递减的条款数 / y 严格递增的条款数。
    groups 缺省时按对象身份分组（每组 1 条 → 无方向信号，安全退化）。
    """
    if groups is None:
        groups = [[s] for s in spans]
    dec = inc = 0
    for g in groups:
        items = [s for s in g if 1 <= int(_span_get(s, "page_number", 0)) <= doc.page_count]
        if len(items) < 2:
            continue
        same_page = len({int(_span_get(s, "page_number", 0)) for s in items}) == 1
        if not same_page:
            continue
        ordered = sorted(items, key=lambda s: int(_span_get(s, "sort_order", 0) or 0))
        ys = [(float(_span_get(s, "bbox")[1]) + float(_span_get(s, "bbox")[3])) / 2.0
              for s in ordered]
        if all(b < a for a, b in zip(ys, ys[1:])):
            dec += 1
        elif all(b > a for a, b in zip(ys, ys[1:])):
            inc += 1
    return dec, inc


def _text_evidence(doc: "fitz.Document", sampled: list[Any]) -> tuple[int, int, int, int]:
    """带内文字真值统计（镜像不对称的强证据）：

    对每条采样 span，raw 解释与 H−y 解释各取带内文字：
    - top_only：仅 raw 命中 → 顶部原点证据；
    - bottom_only：仅 H−y 命中 → 底部原点证据；
    - both：两种解释都命中（页中部/大块 bbox 的镜像对称区）→ **不算任何一方**（旧法缺陷：
      both 计入 top 导致已正确文档被反复翻转，2026-08-25 安全生产法被翻 2 次的根因）；
    - none：无文字层/乱码 → 无文字证据。
    """
    top_only = bottom_only = both = none = 0
    for s in sampled:
        pno = int(_span_get(s, "page_number", 0))
        if pno < 1 or pno > doc.page_count:
            continue
        page = doc[pno - 1]
        H = page.rect.height
        bbox = _span_get(s, "bbox")
        head = _span_get(s, "head", None) or _span_get(s, "content_text", "") or ""
        raw_hit = band_text_hit(page, bbox, head)
        bb = [float(bbox[0]), H - float(bbox[3]), float(bbox[2]), H - float(bbox[1])]
        flp_hit = band_text_hit(page, bb, head)
        if raw_hit and flp_hit:
            both += 1
        elif raw_hit:
            top_only += 1
        elif flp_hit:
            bottom_only += 1
        else:
            none += 1
    return top_only, bottom_only, both, none


def _decide_origin(doc: "fitz.Document", spans: list[Any],
                   top_only: int, bottom_only: int, both: int, none: int,
                   groups: list[list[Any]] | None = None) -> tuple[str, dict]:
    """三层组合判定 → (verdict, stats)。

    verdict ∈ {'top_flip' | 'bottom_keep' | 'unknown'}：
    1. 带内文字证据（最强，镜像不对称）：top_only/bottom_only 有 ≥1 条且占优 → 定；
    2. 阅读方向证据（无镜像对称）：inc/dec 有 ≥2 条且占优 → 定；
    3. 否则 unknown（宁错不翻——翻错比不翻更糟）。
    """
    dec, inc = _direction_votes(doc, spans, groups=groups)
    stats = {
        "top_only": top_only, "bottom_only": bottom_only,
        "both": both, "none": none,
        "direction_dec": dec, "direction_inc": inc,
    }
    if top_only >= 1 and top_only > bottom_only:
        return "top_flip", stats
    if bottom_only >= 1 and bottom_only > top_only:
        return "bottom_keep", stats
    if inc >= 2 and inc > dec:
        return "top_flip", stats
    if dec >= 2 and dec > inc:
        return "bottom_keep", stats
    return "unknown", stats


def calibrate_new(pdf_path: str | Path, spans: list[Any],
                  groups: list[list[Any]] | None = None) -> list[Any]:
    """纯函数版校准（不落库）：入库前对内存中 span 列表文档级判定并归一为底部原点。

    支持 dict 或带 page_number/bbox 属性的对象（如 SourceSpanModel）；原地修改 bbox 并返回
    入参列表。判定：① 阅读方向（无镜像对称，groups 提供条款分组时生效）→ ② 最近行距离投票
    （保留，平票保守不翻）。幂等：已是底部原点则零改动。PDF 打不开时向上抛错由调用方降级。
    """
    items = list(spans or [])
    if not items:
        return items
    doc = fitz.open(str(pdf_path))
    try:
        page_h = {pno: doc[pno - 1].rect.height
                  for pno in {int(_span_get(s, "page_number", 0)) for s in items}
                  if 1 <= pno <= doc.page_count}
        dec, inc = _direction_votes(doc, items, groups=groups)
        if inc >= 2 and inc > dec:
            verdict = "top_flip"
        elif dec >= 2 and dec > inc:
            verdict = "bottom_keep"
        else:
            # 最近行距离投票兜底（简单多数；平票不翻。方向判别已在上面兜住
            # 多 span 场景，此处只处理无方向信号的少数文档）
            _, _, votes_top, votes_bottom = _vote_spans(doc, items)
            verdict = "top_flip" if votes_top > votes_bottom else "bottom_keep"
        if verdict == "top_flip":
            for s in items:
                pno = int(_span_get(s, "page_number", 0))
                if pno in page_h:
                    _span_set(s, "bbox", _flip_bbox(_span_get(s, "bbox"), page_h[pno]))
        return items
    finally:
        doc.close()


def calibrate(doc_id: str, pdf_path: str | Path, db_conn: sqlite3.Connection | None = None,
              *, apply: bool = True) -> dict:
    """存量校准：读该 doc 全部 span → 逐条 vote 文档级多数决 → 顶部原点则全量翻转。

    翻转按 source_span.rowid 精确 UPDATE，并写 event_log 审计（repair/span_origin_flipped）。
    apply=False 为 dry-run：只投票报告、零写库。db_conn 缺省连应用主库。

    返回 {"flipped": bool, "votes": {"top": int, "bottom": int}}。
    """
    if db_conn is None:
        from src.core.config import get_settings
        db_conn = sqlite3.connect(str(get_settings().db_path))
    rows = db_conn.execute(
        "SELECT s.rowid, s.page_number, s.bbox_json, s.sort_order,"
        " cr.clause_revision_id, cr.content_text"
        " FROM source_span s JOIN clause_revision cr"
        " ON cr.clause_revision_id = s.clause_revision_id"
        " WHERE cr.doc_id=? ORDER BY s.page_number, s.sort_order, s.rowid",
        (doc_id,)).fetchall()
    votes = {"top": 0, "bottom": 0}
    if not rows:
        return {"flipped": False, "votes": votes, "verdict": "unknown", "samples": {}}
    doc = fitz.open(str(pdf_path))
    try:
        spans = [{"rowid": r[0], "page_number": r[1], "bbox": json.loads(r[2]),
                  "sort_order": r[3] or 0, "clause_revision_id": r[4] or "",
                  "head": r[5] or ""} for r in rows]
        valid = [s for s in spans if 1 <= int(s["page_number"]) <= doc.page_count]
        # v2 判定（2026-08-26）：分层采样（前/中/后全覆盖，取代旧"前 2 条"——
        # 只采页首样本会漏掉页中部/页底的镜像对称条款）→ 三层组合判定：
        #   ① 带内文字真值（both-hit 不算任何一方，杜绝"已正确文档被反复翻转"）；
        #   ② 阅读方向单调性（无镜像对称）；
        #   ③ 两者都不足 → unknown 宁错不翻。
        sampled = _stratified_sample(valid, 60)
        top_only, bottom_only, both, none = _text_evidence(doc, sampled)
        from collections import defaultdict
        by_cid: dict = defaultdict(list)
        for s in valid:
            by_cid[s["clause_revision_id"]].append(s)
        verdict, stats = _decide_origin(doc, valid, top_only, bottom_only, both, none,
                                        groups=list(by_cid.values()))
        flipped = False
        if verdict == "top_flip" and apply:
            for s in spans:
                pno = int(s["page_number"])
                H = (doc[pno - 1].rect.height if 1 <= pno <= doc.page_count else 841.9)
                db_conn.execute(
                    "UPDATE source_span SET bbox_json=? WHERE rowid=?",
                    (json.dumps(_flip_bbox(s["bbox"], H)), s["rowid"]))
            db_conn.execute(
                "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                " target_id, after_state) VALUES (?,?,?,?,?,?)",
                (str(ULID()), "repair/span_origin_flipped", "system", "doc_meta",
                 doc_id,
                 json.dumps({"verdict": verdict, "samples": stats,
                             "spans": len(spans),
                             "script": "src/core/ingestion/span_calibration.py"},
                            ensure_ascii=False)))
            db_conn.commit()
            flipped = True
        return {"flipped": flipped, "verdict": verdict,
                "samples": stats, "votes": votes}
    finally:
        doc.close()
