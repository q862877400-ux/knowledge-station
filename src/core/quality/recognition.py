"""识别与版面质量度量（R27 入库预览用）——纯函数 + 只读。

## 反熵边界
- **乱码判据**只复用 `mineru_adapter.is_weird_char`（异常字符）与
  `parse_pdf_with_mineru` 回报的 `text_layer_state`（PUA 错位是否可归一化修复），
  本模块**不重新定义**"什么叫乱码"。
- **不可打印字符率**复用 `patch_guard.nonprintable_ratio`。
- 注意 `is_weird_char` 把 0xFF00–0xFFEF 视为正常 → **替换字符 U+FFFD 不算异常字符**，
  所以替换字符率是独立度量（`replacement_ratio`），不是异常字符率的重复。

## 与"OCR 置信度"的关系（R27 的 "OCR 置信度 < 0.85"）
`clause_revision.ocr_confidence` 列**目前没有任何生产者**（落库恒为 1.0），直接读它做
可疑清单会永远为空（假绿，比没有更坏）。所以预览按下述**可解释规则**推导逐条置信度：

    置信度 = 1 − Σ(命中的扣分项)      （钳制到 [0, 1]）

扣分项与其阈值集中在 `grading.THRESHOLDS`（单一所有者）。这是"预览口径"，
与落库后的 `ocr_confidence` 字段解耦：本模块的输出**不写库**。
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

__all__ = [
    "PageLayoutMetrics",
    "SkewResult",
    "TextLayerMetrics",
    "clause_ocr_confidence",
    "measure_skew",
    "page_layout_metrics",
    "text_layer_metrics",
]

#: 中文标点/常见符号之外的 CJK 区间（判"是不是中文正文"用）
_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF))


def _cjk_ratio(s: str) -> float:
    if not s:
        return 0.0
    n = sum(1 for ch in s if any(lo <= ord(ch) <= hi for lo, hi in _CJK_RANGES))
    return n / len(s)


@dataclass(frozen=True)
class TextLayerMetrics:
    blocks: int = 0
    chars: int = 0
    weird_ratio: float = 0.0
    cjk_ratio: float = 0.0
    replacement_ratio: float = 0.0
    nonprint_ratio: float = 0.0


def text_layer_metrics(blocks: Iterable[dict[str, Any]]) -> TextLayerMetrics:
    """文本层整体度量。`blocks` 为 `parse_pdf_with_mineru` 返回的 blocks。"""
    from src.core.ingestion.mineru_adapter import is_weird_char
    from src.core.verification.patch_guard import nonprintable_ratio

    texts = [str(b.get("text") or "") for b in blocks]
    joined = "\n".join(texts)
    n = len(joined)
    if n == 0:
        return TextLayerMetrics(blocks=len(texts))
    weird = sum(1 for ch in joined if is_weird_char(ch))
    return TextLayerMetrics(
        blocks=len(texts),
        chars=n,
        weird_ratio=weird / n,
        cjk_ratio=_cjk_ratio(joined),
        replacement_ratio=joined.count("\ufffd") / n,
        nonprint_ratio=nonprintable_ratio(joined),
    )


@dataclass(frozen=True)
class PageLayoutMetrics:
    pages: int = 0
    chars_per_page: float = 0.0
    pages_no_text: int = 0
    pages_no_text_ratio: float = 0.0
    clauses_per_1000chars: float = 0.0
    rotation_anomaly_pages: list[int] = field(default_factory=list)
    page_size_outliers: int = 0


def page_layout_metrics(geometries: dict[int, dict[str, Any]],
                        blocks: Iterable[dict[str, Any]],
                        *, total_clauses: int = 0) -> PageLayoutMetrics:
    """版面度量：每页字符密度、空白页、旋转异常、页面尺寸离群。

    **哪些进 verdict**：只有 `chars_per_page`（B4「近乎空白」）与
    `clauses_per_1000chars`（W10「条款密度偏低」）参与判定。
    `rotation_anomaly_pages` / `page_size_outliers` 目前**只写进报告供人工查看，不参与判定**
    （2026-09-11 verifier 审计 P2-1 纠正：原注释称"用于 verdict"，与实现不符）。
    """
    pages = len(geometries)
    per_page: dict[int, int] = {}
    for b in blocks:
        p = int(b.get("page_number") or 0)
        per_page[p] = per_page.get(p, 0) + len(str(b.get("text") or ""))
    total_chars = sum(per_page.values())
    no_text = sum(1 for p in geometries if per_page.get(p, 0) == 0)

    rot_bad: list[int] = []
    sizes: list[tuple[float, float]] = []
    for p, geo in geometries.items():
        rot = int(geo.get("rotation") or 0)
        if rot % 90 != 0:
            rot_bad.append(int(p))
        sizes.append((float(geo.get("width") or 0.0), float(geo.get("height") or 0.0)))
    outliers = 0
    if len(sizes) >= 3:
        mw = statistics.median([s[0] for s in sizes])
        mh = statistics.median([s[1] for s in sizes])
        for w, h in sizes:
            if mw > 0 and mh > 0 and (abs(w - mw) / mw > 0.2 or abs(h - mh) / mh > 0.2):
                outliers += 1

    return PageLayoutMetrics(
        pages=pages,
        chars_per_page=(total_chars / pages) if pages else 0.0,
        pages_no_text=no_text,
        pages_no_text_ratio=(no_text / pages) if pages else 0.0,
        clauses_per_1000chars=(total_clauses / total_chars * 1000.0) if total_chars else 0.0,
        rotation_anomaly_pages=rot_bad,
        page_size_outliers=outliers,
    )


@dataclass(frozen=True)
class SkewResult:
    skew_deg: float | None = None
    measured_lines: int = 0
    measured_pages: int = 0
    skew_pages_ratio: float = 0.0
    measured: bool = False


def measure_skew(pdf_path: Path, *, max_pages: int = 40,
                 min_lines: int = 20) -> SkewResult:
    """测量 PDF 文本行的倾斜角（度）。**只读、本地、零依赖新增**（PyMuPDF 已在依赖内）。

    做法：对采样页 `get_text("rawdict")` 取每行字符的 `origin`，最小二乘拟合 y=ax+b，
    θ=atan(a)；取全体行 θ 的中位数作为文档倾角。`measured_lines < min_lines` 视为不可测
    （`measured=False`、`skew_deg=None`）——纯图像页没有字符坐标，倾斜判定无能为力，
    这时**不触发**倾斜判据（如实标注，不假装测过）。

    `skew_pages_ratio`（页级"倾斜页"占比）的判据阈值取 `THRESHOLDS["skew_block_deg"]`（3°）
    而**不是** warn 阈值（1°）：否则任何整份均匀轻度倾斜（如 2°）的文档都会 100% 页码
    命中该比例，把 warn 的存在意义架空（2026-09-11 实测抓到该自相矛盾）。
    """
    import fitz

    from src.core.quality.grading import THRESHOLDS

    angles: list[float] = []
    pages_measured = 0
    pages_skewed = 0
    with fitz.open(str(pdf_path)) as doc:
        total = len(doc)
        if total == 0:
            return SkewResult()
        step = max(1, math.ceil(total / max_pages))
        for pno in range(0, total, step):
            page = doc[pno]
            try:
                raw = page.get_text("rawdict")
            except Exception:  # noqa: BLE001 — 单页解析失败不影响整体测量
                continue
            page_angles: list[float] = []
            for blk in raw.get("blocks", []):
                if blk.get("type") != 0:
                    continue
                for line in blk.get("lines", []):
                    pts: list[tuple[float, float]] = []
                    for span in line.get("spans", []):
                        for ch in span.get("chars", []):
                            o = ch.get("origin")
                            if o:
                                pts.append((float(o[0]), float(o[1])))
                    if len(pts) < 5:
                        continue
                    n = len(pts)
                    sx = sum(p[0] for p in pts)
                    sy = sum(p[1] for p in pts)
                    sxx = sum(p[0] * p[0] for p in pts)
                    sxy = sum(p[0] * p[1] for p in pts)
                    den = n * sxx - sx * sx
                    if abs(den) < 1e-9:
                        continue
                    a = (n * sxy - sx * sy) / den
                    page_angles.append(math.degrees(math.atan(a)))
            if page_angles:
                pages_measured += 1
                mid = statistics.median(page_angles)
                if abs(mid) >= THRESHOLDS["skew_block_deg"]:
                    pages_skewed += 1
                angles.extend(page_angles)

    if len(angles) < min_lines:
        return SkewResult(measured_lines=len(angles), measured_pages=pages_measured,
                          measured=False)
    return SkewResult(
        skew_deg=round(statistics.median(angles), 3),
        measured_lines=len(angles),
        measured_pages=pages_measured,
        skew_pages_ratio=(pages_skewed / pages_measured) if pages_measured else 0.0,
        measured=True,
    )


def clause_ocr_confidence(content: str, *, page_skew_deg: float | None,
                          is_tiny: bool = False) -> tuple[float, list[str]]:
    """推导单条条款的识别置信度（R27 的 "OCR 置信度"），返回 (置信度, 扣分理由码)。

    阈值集中在 `src.core.quality.grading.THRESHOLDS`（单一所有者）。这里只做"命中即扣分"，
    不做任何文本改写（证据文本不可变红线）。
    """
    from src.core.ingestion.mineru_adapter import is_weird_char
    from src.core.quality.grading import THRESHOLDS
    from src.core.verification.patch_guard import nonprintable_ratio

    s = content or ""
    conf = 1.0
    reasons: list[str] = []
    n = len(s)
    if is_tiny:
        conf -= THRESHOLDS["p_clause_tiny"]
        reasons.append("P1")
    if n > 0:
        weird = sum(1 for ch in s if is_weird_char(ch)) / n
        if weird >= THRESHOLDS["clause_weird_ratio"]:
            conf -= THRESHOLDS["p_clause_weird"]
            reasons.append("P2")
        if s.count("\ufffd") / n >= THRESHOLDS["clause_replacement_ratio"]:
            conf -= THRESHOLDS["p_clause_replacement"]
            reasons.append("P3")
        if nonprintable_ratio(s) > 0:
            conf -= THRESHOLDS["p_clause_nonprint"]
            reasons.append("P4")
        if _cjk_ratio(s) < THRESHOLDS["clause_min_cjk_ratio"]:
            conf -= THRESHOLDS["p_clause_nocjk"]
            reasons.append("P5")
    if page_skew_deg is not None and abs(page_skew_deg) >= THRESHOLDS["skew_warn_deg"]:
        conf -= THRESHOLDS["p_clause_skew"]
        reasons.append("P6")
    return (max(0.0, min(1.0, round(conf, 4))), reasons)
