"""Pydantic 域模型契约（T00 冻结）。对应主计划 v4.3 第 6 节。"""
from __future__ import annotations

from typing import List, Optional, Literal

from pydantic import BaseModel, Field

# v4.3 知识单元类型
KnowledgeType = Literal['data', 'rule', 'legal']
# v4.3 模态词
Modality = Literal[
    '严禁', '禁止', '不得', '不应', '不能',
    '应当', '应', '必须',
    '宜', '一般应', '原则上',
    '可以', '有权', '可',
    '鼓励', '提倡', '支持',
]

# v4.3 模态强度字典 (R4a) —— 权威常量，变更需走契约变更流程
MODALITY_STRENGTH: dict[str, int] = {
    '严禁': 5, '禁止': 5,
    '不得': 4, '不应': 4, '不能': 4,
    '应当': 3, '应': 3, '必须': 3,
    '宜': 2, '一般应': 2, '原则上': 2,
    '可以': 1, '有权': 1, '可': 1,
    '鼓励': 0, '提倡': 0, '支持': 0,
}


class PageGeometryModel(BaseModel):
    page_number: int
    width: float
    height: float
    rotation: int = 0
    crop_box: Optional[List[float]] = None
    media_box: Optional[List[float]] = None


class SourceSpanModel(BaseModel):
    span_id: str
    page_number: int = Field(..., description="PDF 物理页码，从 1 开始")
    bbox: List[float] = Field(..., min_length=4, max_length=4,
                              description="[x1,y1,x2,y2] PDF 坐标系 (左下原点)")
    span_type: str = "text"
    sort_order: int = 0


class ClauseRevisionModel(BaseModel):
    clause_revision_id: str
    doc_id: str
    clause_key: str
    standard_no: str
    clause_number: str
    title: Optional[str] = None
    content_text: str
    content_markdown: Optional[str] = None
    table_summary: Optional[str] = None
    # 2026-09-01 排版还原 C2：MinerU 预裁剪插图占位（<p class="fig-strip">，
    # 前端 apiFetch 拉 blob 填 src）。独立通道不进 content_markdown——编辑
    # 保存片段与 build 产物的 md 路径判定互不干扰。
    figure_html: Optional[str] = None
    formula_number: Optional[str] = None
    formula_desc: Optional[str] = None
    image_text: Optional[str] = None
    hierarchy_path: Optional[str] = None
    # 三型知识单元字段
    knowledge_type: KnowledgeType = 'rule'
    type_confidence: float = 1.0
    modality: Optional[Modality] = None
    modality_strength: Optional[int] = None
    modality_confidence: Optional[float] = None
    behavior_scope: Optional[str] = None
    subject: Optional[str] = None
    object: Optional[str] = None
    behavior: Optional[str] = None
    applicability_condition: Optional[str] = None
    restriction: Optional[str] = None
    exception: Optional[str] = None
    legal_refs: List[str] = []
    # 通用字段
    is_mandatory: bool = False
    is_suspicious: bool = False
    ocr_confidence: float = 1.0
    legal_status: str = "effective"
    legal_hierarchy: str = "GB"
    effective_from: Optional[str] = None   # 实施日期（到期翻转 upcoming→effective 依据）
    page_start: int
    page_end: int
    cross_refs: List[str] = []
    explanation_ref: Optional[str] = None
    # 2026-09-01 B3 页界入库（排版还原需求）：run-start 编码 [[行号, PDF页码], ...]，
    # 行号 = content_text 内 0-based 行索引（首个条目恒为 [0, 首行所在页]）。
    # 语义：行号 i 起（含）到下一页界前，正文行位于该 PDF 页。None = 存量未采集。
    page_breaks: Optional[List[List[int]]] = None
    source_spans: List[SourceSpanModel] = []
    # 阶段2.1 新增：人工纠错补丁标记（读路径覆写来源，UI 用于"已人工修正"徽章）
    patched_fields: List[str] = []


class DocumentMetaModel(BaseModel):
    doc_id: str
    standard_no: str
    standard_name: str
    short_code: str
    current_revision_id: str
    legal_status: str
    legal_hierarchy: str = "GB"
    standard_type: str = "mandatory"
    doc_type: str = "standard"
    quality_grade: str = "A"
    domain_tags: List[str] = []
    effective_from: Optional[str] = None
    superseded_by: Optional[str] = None
    normative_refs: List[str] = []
    file_path: str
    file_hash: str


class EvidenceEdgeModel(BaseModel):
    edge_id: str
    edge_type: Literal[
        'clause_relation', 'exception_relation', 'definition_relation',
        'reference_relation', 'correction_relation',
    ]
    source_clause_id: str
    target_clause_id: str
    confidence: float = 1.0
    status: Literal['active', 'pending', 'rejected'] = 'active'


class ReviewPointModel(BaseModel):
    point_id: str
    task_id: str
    point_type: str
    point_content: str
    matched_clause_ids: List[str] = []
    match_scores: dict = {}
    verdict: Literal['red', 'yellow', 'green']
    verdict_reason: str
    modality_comparison: Optional[dict] = None
    suggestion: Optional[str] = None


class ModalityViolation(BaseModel):
    clause_revision_id: str
    source_modality: str
    output_modality: str
    source_strength: int
    output_strength: int
    violation_type: Literal['modality_weakened', 'modality_strengthened', 'modality_missing']


class VerificationResult(BaseModel):
    is_valid: bool
    unsupported_clauses: List[str] = []
    unverified_numbers: List[dict] = []
    modality_violations: List[ModalityViolation] = []
    legal_element_violations: List[dict] = []


# SSE 事件顺序契约（T00 冻结，见 docs/onboarding/contract.md 第 3 节）
SSE_EVENT_ORDER: List[str] = ['evidence', 'status', 'delta', 'verification', 'done']

# 六路检索通道枚举（T00 冻结）
SEARCH_CHANNELS: List[str] = ['exact', 'fts', 'vec', 'modality', 'legal_element', 'behavior_scope']
