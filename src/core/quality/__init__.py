"""质量判定域包：条款体检、识别/版面度量、分级与裁决的**唯一所有者**。

设计约束（与 `docs/DSH_REINCARNATION.md` 台账的入库预览条目一致）：
- 纯函数优先：零 DB、零 parser 依赖、零网络，便于离线单测与复用。
- 反熵：同一条质量规则只允许有一个所有者（如 6 标签只在 `clause_health`，
  乱码判据只复用 `mineru_adapter.text_layer_pua_mangled`，不另造）。
- 只读：本包不得写库、不得建表、不得移动用户文件。
"""

from src.core.quality.clause_health import (
    TABLE_MD_LIMIT,
    ClauseHealth,
    clause_health,
    clause_health_html_to_text,
)
from src.core.quality.grading import (
    THRESHOLDS,
    grade_document,
    legal_element_quality,
    one_line_summary,
    typing_quality,
    verdict_document,
)
from src.core.quality.recognition import (
    PageLayoutMetrics,
    SkewResult,
    TextLayerMetrics,
    clause_ocr_confidence,
    measure_skew,
    page_layout_metrics,
    text_layer_metrics,
)

__all__ = [
    "TABLE_MD_LIMIT",
    "THRESHOLDS",
    "ClauseHealth",
    "PageLayoutMetrics",
    "SkewResult",
    "TextLayerMetrics",
    "clause_health",
    "clause_health_html_to_text",
    "clause_ocr_confidence",
    "grade_document",
    "legal_element_quality",
    "measure_skew",
    "one_line_summary",
    "page_layout_metrics",
    "text_layer_metrics",
    "typing_quality",
    "verdict_document",
]
