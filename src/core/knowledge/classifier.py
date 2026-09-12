"""三型知识单元分型 + 法理要素抽取（T05 规则版；LLM 半自动增强在 T06 之后接入）。

分型优先级（含数值的条款归 data，数值闭包核验是硬需求）：
  1. 含模态词 + 含数值量纲 → data（模态同时保留，供 R4a 核验）
  2. 含数值量纲，无模态    → data
  3. 法条模式（第X条 / 法定义主体）或 doc_type=法律法规 → legal
  4. 含模态词 → rule
  5. 其余 → rule（低置信，标 is_suspicious）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from src.core.domain.models import MODALITY_STRENGTH, Modality

# 数值 + 单位（工程量纲），R62 特殊字符已归一后匹配
_NUM_UNIT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:m²|m³|m\^?2|m\^?3|mm|cm|m|MPa|kPa|Pa|kV|V|A|kW|W|h|min|s|"
    r"℃|°C|%|kg|t|kN|N|L|dB|lx|MHz|Hz|MHz|万|亿|元|天|日|月|年|人|次|层|类|级|倍)")

# 模态词，长词优先
_MODAL_RE = re.compile("|".join(sorted(MODALITY_STRENGTH.keys(), key=len, reverse=True)))

# 单字模态词后随这些字时是复合词，不是模态（可燃/可能/应该/应急/宜于…）
_MODAL_COMPOUND_NEXT = {
    "可": "燃能见靠行得计算以",
    "应": "该急变力用付急变",
    "宜": "于",
}


def extract_modality(text: str) -> tuple[Modality | None, float]:
    """抽取首个有效模态词（跳过复合词误命中）。返回 (词, 置信度)。"""
    for word in sorted(MODALITY_STRENGTH.keys(), key=len, reverse=True):
        blocked = _MODAL_COMPOUND_NEXT.get(word, "")
        idx = text.find(word)
        while idx != -1:
            nxt = text[idx + len(word):idx + len(word) + 1]
            if nxt and nxt in blocked:
                idx = text.find(word, idx + 1)
                continue
            return word, 0.92  # type: ignore[return-value]  # word ∈ MODALITY_STRENGTH 键 = Modality 值域（pydantic Literal 与 dict 键双源，静态不可证）
    return None, 0.0

# 法条模式
_LAW_NUM = re.compile(r"第[一二三四五六七八九十百千]+条")

# 法定义主体（R-L1 义务主体高频词）
_ACTOR_SUFFIX = ("者", "人", "单位", "部门", "企业", "机构", "机关", "政府", "法院", "部门")
# 主体词典（阶段3 gazetteer 化）：正则推导会吞动词尾巴，词典命中优先、最长匹配
_ACTOR_GAZETTEER = (
    "个人信息处理者", "关键信息基础设施运营者", "网络运营者", "个人信息处理",
    "经营者", "消费者", "当事人", "出租人", "承租人", "买受人", "出卖人",
    "委托人", "受托人", "监护人", "被监护人", "代理人", "用人单位", "劳动者",
    "行政机关", "人民法院", "政府部门", "企事业单位", "金融机构", "平台内经营者",
    "电子商务平台经营者", "数据处理者", "任何单位和个人", "任何单位", "甲方", "乙方",
)
# 后缀锚定优先：xxx者/人/单位 + 义务动词（避免 lazy 捕获吞动词尾巴）
_SUBJECT_ANCHORED_RE = re.compile(
    r"([\u4e00-\u9fff]{2,12}(?:者|人|单位|部门|企业|机构|机关|政府|法院))"
    r"(?:应当|不得|严禁|禁止|必须|可以|有权)")
_SUBJECT_RE = re.compile(
    r"([\u4e00-\u9fff]{2,14}?)(?:应当|不得|严禁|禁止|必须|可以|有权)")

# 但书/例外（R-L 例外抽取）
_EXCEPTION_RE = re.compile(r"(但[^。；]{4,120}|除[^。；]{2,80}外|另有规定[^。；]{0,60})")

# 引用：内部条款（本规范/本法 第X条 或 裸条款号）与外部标准号
_REF_INTERNAL = re.compile(r"(?:本规范|本法|本条例|本标准)?\s*第?[一二三四五六七八九十百千\d]+条")
# 阶段3 放宽：覆盖"按 5.2.1 执行""应符合 6.4.2"等无"本规范"前缀的内部引用
_REF_INTERNAL_NUM = re.compile(
    r"(?:本规范|本法|本条例|本标准|本规程)?\s*"
    r"(?:第\s*(\d+(?:\.\d+){1,4})\s*条"
    r"|(?:按|依|遵|按照|依照|符合|执行)\s*第?\s*(\d+(?:\.\d+){1,4})\s*条?)")
# 法律文风的内部引用：依照本法第五条 / 按照本法第三条（中文条号，保留原样以匹配条款号）
_REF_INTERNAL_CN = re.compile(
    r"(?:依照|按照|依据|根据|适用|参照)?\s*(?:本法|本条例|本规范)?\s*"
    r"第([一二三四五六七八九十百千]+)条")
_REF_EXTERNAL = re.compile(r"(?:GB|JGJ|GB/T|JG|CJJ|DB)?/?\s*T?\s*\d{4,6}(?:[-—]\d{4})?")
# 条款号前缀剥离（法律条文主体抽取用）
_CLAUSE_NO_PREFIX = re.compile(r"^第[一二三四五六七八九十百千]+条\s*")

# E7 修订标记：条款号后的年份角标 / ※ / ＊
_REV_MARK = re.compile(r"^(※|＊|\*)\s*")
_YEAR_SUPER = re.compile(r"^(\d+(?:\.\d+)*)\s*[（(]?(19|20)\d{2}[）)]?")


@dataclass
class TypedClause:
    # 值域 = ClauseRevisionModel.knowledge_type 的 Literal（'data'|'rule'|'legal'，
    # 赋值点仅下方 4 处字面量）——收窄注解让入库管线零 cast 直传
    knowledge_type: Literal["data", "rule", "legal"] = "rule"
    type_confidence: float = 0.5
    # 值域 = models.Modality（extract_modality 只产 MODALITY_STRENGTH 键内词）
    modality: Modality | None = None
    modality_strength: int | None = None
    modality_confidence: float | None = None
    exception: str | None = None
    subject: str | None = None
    cross_refs: list[str] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)
    is_mandatory: bool = False
    is_suspicious: bool = False


def normalize_clause_number(raw: str) -> str:
    """E6 编号归一：全角→半角、去前导零、去空白。"""
    s = raw.strip().replace("．", ".").replace("。", ".")
    s = re.sub(r"\s+", "", s)
    parts = s.split(".")
    norm = ".".join(str(int(p)) if p.isdigit() else p for p in parts)
    return norm


def strip_revision_marks(text: str) -> str:
    """E7 修订标记剥离。"""
    return _REV_MARK.sub("", text)


def classify_clause(text: str, doc_type: str = "standard") -> TypedClause:
    tc = TypedClause()
    modality, mod_conf = extract_modality(text)
    m = modality
    has_num = bool(_NUM_UNIT.search(text))
    is_law_doc = doc_type in ("法律法规", "法律")

    if m:
        tc.modality = m
        tc.modality_strength = MODALITY_STRENGTH[m]
        tc.modality_confidence = mod_conf

    if has_num:
        tc.knowledge_type = "data"
        tc.type_confidence = 0.85 if not m else 0.75
    elif is_law_doc or _LAW_NUM.search(text):
        tc.knowledge_type = "legal"
        tc.type_confidence = 0.8 if is_law_doc else 0.7
        tc.modality_confidence = tc.modality_confidence or (0.9 if m else None)
    elif m:
        tc.knowledge_type = "rule"
        tc.type_confidence = 0.9
    else:
        tc.knowledge_type = "rule"
        tc.type_confidence = 0.5
        tc.is_suspicious = True

    # 法理要素（legal 型重点抽取，rule 型兜底）——从剥离条号后的正文提取
    if tc.knowledge_type in ("legal", "rule") and m:
        body = _CLAUSE_NO_PREFIX.sub("", text)
        # 词典最长匹配优先，正则锚定兜底
        sm = _SUBJECT_ANCHORED_RE.search(body) or _SUBJECT_RE.search(body)
        gazetteer_hit = next(
            (a for a in sorted(_ACTOR_GAZETTEER, key=len, reverse=True) if a in body), None)
        if gazetteer_hit:
            tc.subject = gazetteer_hit
        elif sm and (sm.group(1).endswith(_ACTOR_SUFFIX) or is_law_doc):
            tc.subject = sm.group(1)

    em = _EXCEPTION_RE.search(text)
    if em:
        tc.exception = em.group(1)[:120]

    refs_raw = [g for groups in _REF_INTERNAL_NUM.findall(text) for g in groups if g]
    # 中文条号引用：跳过句首（那是本条自己的条号，防自引用）
    refs_raw += [f"第{m.group(1)}条" for m in _REF_INTERNAL_CN.finditer(text)
                 if m.start() > 0]
    # 中文条号引用保持原样（匹配库内 clause_number），阿拉伯条号归一
    tc.cross_refs = list(dict.fromkeys(
        x if x.startswith("第") else normalize_clause_number(x) for x in refs_raw))
    tc.external_refs = list(dict.fromkeys(
        r.strip() for r in _REF_EXTERNAL.findall(text) if len(r.strip()) >= 4))[:10]

    tc.is_mandatory = ("★" in text) or ("强制性条文" in text)
    return tc


def build_hierarchy_path(clause_number: str) -> str:
    """E3 层级路径：5.2.1 → '5 > 5.2'（章-节-条）。"""
    parts = clause_number.split(".")
    if not all(p.isdigit() for p in parts) or len(parts) < 2:
        return ""
    return " > ".join(".".join(parts[:i + 1]) for i in range(len(parts) - 1))
