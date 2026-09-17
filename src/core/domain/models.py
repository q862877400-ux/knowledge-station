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
    legal_status: Optional[str] = "effective"
    # ⚠ `standard_type` 是**排序真的会看**的字段（2026-09-17 独立复核 b7 的 MEDIUM-4）：
    # `query/understanding.rank_with_hierarchy` 里那一项写的是
    # `getattr(c, 'standard_type', 'mandatory') == 'mandatory'`，而本模型**从前没有这个字段**
    # ⇒ `getattr` 恒取默认 `'mandatory'` ⇒ 该项对**所有**条款都算 0（**恒等，零区分度**），
    # 也就是说"按强制排前"这句话在排序里**从来没生效过**。
    # 现在补上字段、由 `fetch_full_clause` 从 `doc_meta.standard_type` 填；
    # **`None`（未登记，含采集件）判为"不优先"**（不知道就别替它加分——与 §10.39 同一原则）。
    standard_type: Optional[str] = None
    # ⚠ `Optional` 是**契约级**的诚实（2026-09-17 独立复核 b7 的 HIGH，§10.44）：
    # `doc_meta.legal_status` 允许 NULL（采集件走 Track L 入库时就是 NULL = **未核验**），
    # 而读路径 `clause_repo.fetch_full_clause` 以前写的是 `row["legal_status"] or "effective"`
    # —— 把 NULL **洗白成现行有效**，于是它通过 `ks_answer._is_effective`
    # （`== "effective"`）进证据、进提示词（`效力=effective`）：
    # **未核验的网页文本会被当现行法条引用**。
    # 写入方（docx/pipeline/law_text 的 `ClauseRevisionModel(...)`）不传该字段，
    # 因此**默认值仍是 "effective"**，既有入库行为一字未变；改变的是**读取**：
    # NULL 就是 NULL，由 `resolve_status` 原样返回、由 `_is_effective` 判为"不得入证"。
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
    #: 每条"证据外条款号"的**可操作说明**（2026-09-16 新增，见
    #: `typed_verifier._describe_unsupported`）。`unsupported_clauses` 保持原样
    #: 以兼容既有消费方（SSE 字段名与顺序**不变**，本字段是纯增量）。
    unsupported_context: List[dict] = []
    unverified_numbers: List[dict] = []
    modality_violations: List[ModalityViolation] = []
    legal_element_violations: List[dict] = []


# SSE 事件顺序契约（T00 冻结，见 docs/ENCYCLOPEDIA.md §11.3 与 pipeline/03-contract-delta.md）
SSE_EVENT_ORDER: List[str] = ['evidence', 'status', 'delta', 'verification', 'done']

# 六路检索通道枚举（T00 冻结）
SEARCH_CHANNELS: List[str] = ['exact', 'fts', 'vec', 'modality', 'legal_element', 'behavior_scope']
