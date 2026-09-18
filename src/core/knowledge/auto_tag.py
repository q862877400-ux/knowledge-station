"""入库自动标签管线（Task 11.3，v5 P2 入库便利）。

规则层（必做，确定性优先）：
  - standard_no / 年代号 / 代替关系 / 施行日期 正则提取；
  - 领域标签词表多选（建筑/消防/安全/环保/合同/数据/劳动/卫生/化工）。
LLM 层（云端，走 egress_audit）：domain_tags 分类增强、效力层级建议——置信度 <0.8 进待确认。
红线（P1 裁决）：标签只写 doc_meta 元数据，**永不改写条款原文/不进入引用路径**。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_STD_NO_RE = re.compile(
    r"(GB|GB/T|JGJ|JG|CJJ|DB\d{2}|DBJ|SH|HG|AQ|TSG)[/\s]*T?\s*\d{4,6}(?:[-—]\d{4})?")
_YEAR_RE = re.compile(r"(19|20)\d{2}")
_SUPERSEDE_RE = re.compile(r"代替\s*((?:GB|JGJ|GB/T|CJJ|DB)[/\s]*T?\s*\d{4,6}(?:[-—]\d{4})?)")
_EFFECTIVE_RE = re.compile(r"自\s*((?:19|20)\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)\s*起\s*施行")

_DOMAIN_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("建筑", ("建筑", "结构", "抗震", "幕墙", "混凝土", "钢结构")),
    ("消防", ("消防", "防火", "疏散", "灭火", "烟感", "喷淋", "火灾")),
    ("安全", ("安全", "危险", "防护", "应急", "隐患", "事故", "特种作业", "职业健康")),
    ("环保", ("环境", "污染", "排放", "污水", "废气", "固废", "噪声")),
    ("化工", ("化工", "化学品", "工艺", "反应", "储罐", "管道")),
    ("合同", ("合同", "债权", "租赁", "买卖", "担保")),
    ("数据", ("数据", "个人信息", "隐私", "网络安全", "信息安全")),
    ("劳动", ("劳动", "用工", "社保", "工资", "工时", "工伤")),
    ("卫生", ("卫生", "医疗", "食品", "饮用水")),
]


@dataclass
class AutoTags:
    standard_no: str | None = None
    year: str | None = None
    superseded: str | None = None      # 代替的旧标准号
    effective_from: str | None = None  # 施行日期（规范化 YYYY-MM-DD）
    domain_tags: list[str] = field(default_factory=list)
    legal_hierarchy_hint: str | None = None


def _normalize_eff(text: str) -> str | None:
    m = _EFFECTIVE_RE.search(text)
    if not m:
        return None
    digits = re.findall(r"\d+", m.group(1))
    if len(digits) == 3:
        y, mo, d = digits
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def auto_tag(text: str, filename: str = "") -> AutoTags:
    """对文档封面/前言文本打标签（只产出元数据，调用方负责落 doc_meta）。"""
    head = text[:4000]
    t = AutoTags()
    m = _STD_NO_RE.search(head)
    if m:
        t.standard_no = (m.group(0).replace(" ", "").replace("/", "")
                         .replace("—", "-").replace("–", "-"))
        y = _YEAR_RE.search(t.standard_no)
        if y:
            t.year = y.group(0)
    if not t.standard_no:
        fm = _YEAR_RE.search(filename)
        if fm:
            t.year = fm.group(0)
    sm = _SUPERSEDE_RE.search(head)
    if sm:
        t.superseded = sm.group(1).replace(" ", "").replace("/", "")
    t.effective_from = _normalize_eff(head)
    hits = set()
    for name, kws in _DOMAIN_KEYWORDS:
        if any(k in head for k in kws):
            hits.add(name)
    if filename:
        for name, kws in _DOMAIN_KEYWORDS:
            if any(k in filename for k in kws):
                hits.add(name)
    if not hits:
        hits.add("通用")
    t.domain_tags = sorted(hits)
    return t


def apply_tags_to_doc_meta(doc_id: str, tags: AutoTags) -> None:
    """标签落 doc_meta（红线：绝不触碰 clause_revision 原文）。"""
    from src.core.storage.sqlite_db import write_transaction
    sets = []
    params = []
    if tags.standard_no:
        # 存储形收口（§11.0 R6c-2d）：本处是 **UPDATE** 路径，走不到 `clause_repo.insert_document`，
        # 所以单独过同一个 helper。`_STD_NO_RE` 今天产不出全角，这一行是防"以后谁改了正则"。
        from src.core.text_utils import store_standard_no
        sets.append("standard_no=?"); params.append(store_standard_no(tags.standard_no))
    if tags.effective_from:
        sets.append("effective_from=?"); params.append(tags.effective_from)
    if tags.superseded:
        sets.append("superseded_by=?"); params.append(tags.superseded)
    if tags.domain_tags:
        import json
        sets.append("domain_tags=?"); params.append(json.dumps(tags.domain_tags, ensure_ascii=False))
    if not sets:
        return
    params.append(doc_id)
    with write_transaction() as conn:
        conn.execute(f"UPDATE doc_meta SET {', '.join(sets)}, updated_at=datetime('now')"
                     " WHERE doc_id=?", params)
