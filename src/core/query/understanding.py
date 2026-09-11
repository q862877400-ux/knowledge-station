"""Query Understanding Layer（Phase 9.2，R9/R40/R41/R52/R53/R60 基础版）。

流程（R9 v4.3）：用户问题 → 问题分类 → 参数/要素槽位识别 → 缺失参数判断
→ 追问策略（四档）→ 知识检索 → 回答。

槽位 Schema：工程参数（建筑类型/火灾危险性/耐火等级/高度）+ 法律要素
（主体/客体/行为/同意状态）。追问严格基于 Schema，严禁编造。
"""
from __future__ import annotations

import re
from typing import Any

INTENTS = ['clause_lookup', 'data_query', 'rule_query', 'compliance_review',
           'interpretation', 'compare', 'general']

INTENT_KEYWORDS = [
    ('clause_lookup', ['第', '条', '查']),
    ('interpretation', ['什么意思', '释义', '解释', '含义', '怎么理解']),
    ('compare', ['区别', '不同', '对比', '比较', 'vs']),
    ('compliance_review', ['是否合法', '是否合规', '合规吗', '可以吗', '能不能', '违法吗',
                           '允许吗', '可不可以', '行不行', '是否违反']),
    ('data_query', ['不小于', '不应小于', '不得小于', '大于', '小于', '宽度',
                    '间距', '高度', '面积', '米', 'm']),
    ('data_query', ['多少']),  # '多少'兜底，但先排除分级问法
    ('rule_query', ['应当', '应', '严禁', '不得', '必须', '宜', '要求']),
]

def classify_intent(query: str) -> str:
    q = query.strip()
    if re.search(r'[0-9]+(?:[.][0-9]+)*[ ]*(条|款)', q):
        return 'clause_lookup'
    # 分级问法（高处作业分几级/多少级）→ 规则查询而非数据查询
    if re.search(r'(分|有|是)?[ ]*几?多少?[ ]*级', q) or '级' in q and '作业' in q:
        return 'rule_query'
    for intent, kws in INTENT_KEYWORDS:
        for kw in kws:
            if kw in q:
                return intent
    return 'general'

# ---------- 主题检测（R9 追问合理性：追问必须与问题主题相关） ----------
SPECIAL_WORK_KEYWORDS = ['高处作业', '动火作业', '受限空间', '吊装', '盲板抽堵', '临时用电',
                         '动土作业', '断路作业', '特殊作业', '硫化氢', '气体检测', '探头',
                         '报警仪', '氧含量', '作业高度', '离地']
BUILDING_KEYWORDS = ['防火间距', '疏散', '耐火', '消防', '建筑', '厂房', '仓库', '民用',
                     '住宅', '高层']
PRIVACY_KEYWORDS = ['个人信息', '人脸', '生物识别', '数据', '收集', '考勤', '员工信息']


def detect_theme(query: str) -> str:
    """主题：special_work / building / privacy / general。"""
    for kw in SPECIAL_WORK_KEYWORDS:
        if kw in query:
            return 'special_work'
    for kw in PRIVACY_KEYWORDS:
        if kw in query:
            return 'privacy'
    for kw in BUILDING_KEYWORDS:
        if kw in query:
            return 'building'
    return 'general'


ENGINEERING_SLOTS = {
    'building_type': {
        'label': '建筑类型',
        'keywords': ['高层民用', '多层民用', '民用建筑', '住宅', '公共建筑', '厂房',
                     '仓库', '工业建筑', '高层建筑', '高层'],
        'question': '建筑类型是？（民用住宅/公共建筑/厂房/仓库等，不确定可回复按常见民用建筑）',
    },
    'fire_risk': {
        'label': '火灾危险性类别',
        'keywords': ['甲类', '乙类', '丙类', '丁类', '戊类', '甲乙类', '甲、乙类'],
        'question': '火灾危险性类别是？（甲/乙/丙/丁/戊类，不确定可回复按丙类一般场景）',
    },
    'fire_resistance': {
        'label': '耐火等级',
        'keywords': ['耐火一级', '耐火二级', '耐火三级', '一级耐火', '二级耐火', '三级耐火'],
        'question': '耐火等级是？（一/二/三级，不确定可回复按二级常见场景）',
    },
    'height': {'label': '建筑高度', 'keywords': [],
               'question': '建筑高度约多少米？（不确定可回复按常见高度）'},
}

HEIGHT_RE = re.compile(r'([0-9]+(?:[.][0-9]+)?)[ ]*(?:米|m)(?:以上|以下|左右)?')

LEGAL_SLOTS = {
    'subject': {
        'label': '行为主体',
        'keywords': ['企业', '公司', '个人', '经营者', '个人信息处理者', '员工', '消费者',
                     '用人单位', '劳动者', '平台'],
        'question': '行为主体是？（企业/个人/经营者/平台等）',
    },
    'object': {
        'label': '行为客体',
        'keywords': ['个人信息', '人脸', '生物识别', '合同', '数据', '劳动', '工资', '租金'],
        'question': '涉及的行为客体是？（个人信息/人脸/合同/劳动关系等）',
    },
    'behavior': {
        'label': '行为类型',
        'keywords': ['收集', '使用', '传输', '删除', '共享', '委托处理', '收集使用', '采集'],
        'question': '行为类型是？（收集/使用/传输/共享/删除等）',
    },
    'consent': {
        'label': '同意状态',
        'keywords': ['单独同意', '同意', '未取得同意', '未经同意', '明示同意'],
        'question': '是否已取得（单独）同意？',
    },
}

DECLARED_RE = re.compile(r'^[ ]*[\[【]([^\]】]+)[\]】][ ]*(.*)$')

def parse_declared(query: str) -> tuple[dict, str]:
    m = DECLARED_RE.match(query)
    if not m:
        return {}, query
    slots: dict[str, str] = {}
    schema = {**ENGINEERING_SLOTS, **LEGAL_SLOTS}
    for part in m.group(1).split('/'):
        part = part.strip()
        if not part:
            continue
        for name, s in schema.items():
            if name == 'height':
                if HEIGHT_RE.search(part):
                    slots[name] = part
                continue
            for kw in s['keywords']:
                if kw in part:  # 子串级：'丙类厂房' 同时命中 丙类 + 厂房
                    slots[name] = kw
                    break
    return slots, m.group(2).strip()

# 主题 → 允许提取的槽位类型（通用作用域，不按具体规范打标签）
# special_work/其他主题的数值（作业高度、间距、安装高度…）就在问题原文里，
# LLM 直接可见，无需槽位语义；只有建筑主题的高度才用于追问与场景注入。
THEME_SLOT_KEYS: dict[str, list[str] | None] = {
    'special_work': [],
    'building': ['building_type', 'fire_risk', 'fire_resistance', 'height'],
    'privacy': ['subject', 'behavior', 'object'],
    'general': None,  # 回退：全部槽位
}


def extract_slots(query: str, theme: str = 'general') -> dict[str, str]:
    """主题作用域槽位提取：仅提取当前主题相关的槽位（防跨主题污染）。"""
    slots: dict[str, str] = {}
    schema = {**ENGINEERING_SLOTS, **LEGAL_SLOTS}
    allowed = THEME_SLOT_KEYS.get(theme, None)
    for name, s in schema.items():
        if allowed is not None and name not in allowed:
            continue
        for kw in s['keywords']:
            if kw in query:
                slots[name] = kw
                break
    if allowed is None or 'height' in allowed:
        hm = HEIGHT_RE.search(query)
        if hm:
            slots['height'] = hm.group(0)
    return slots

# 主题 → 核心追问槽位（追问必须与主题相关：特殊作业分级/要求不依赖建筑参数）
# (v1 槽位表 CORE_SLOTS/THEME_CORE_SLOTS/missing_core_slots/build_clarify 已于 Task 13.1 删除——
# 追问 v2 由 LLM 单次自判，见 MAINTAINER-GUIDE §4.3；extract_slots 仅保留主题作用域槽位提取)

MUTEX = {
    'building_type': {
        '民用建筑': ['工业建筑', '厂房', '仓库'],
        '工业建筑': ['民用建筑', '住宅'],
        '住宅': ['公共建筑', '厂房'],
        '公共建筑': ['住宅'],
        '厂房': ['民用建筑', '住宅'],
    },
}

def apply_condition_filter(clauses: list[Any], slots: dict) -> list[Any]:
    if not slots:
        return clauses
    excluded: set[str] = set()
    for slot_name, value in slots.items():
        for v, excls in MUTEX.get(slot_name, {}).items():
            if v in value:
                excluded.update(excls)
    if not excluded:
        return clauses
    kept = [c for c in clauses if not any(t in ((getattr(c, 'content_text', '') or '')
             + (getattr(c, 'title', '') or '')) for t in excluded)]
    return kept or clauses

HIERARCHY_RANK = {
    '宪法': 1, '法律': 2, '行政法规': 3, '地方性法规': 4, '部门规章': 5,
    'GB': 6, 'JGJ': 7, 'DB': 8, 'T': 9, '企标': 10,
}

def rank_with_hierarchy(clauses: list[Any]) -> list[Any]:
    def key(c: Any):
        rank = HIERARCHY_RANK.get(getattr(c, 'legal_hierarchy', '') or '', 99)
        mandatory = 0 if getattr(c, 'is_mandatory', False) else 1
        std_type = 0 if getattr(c, 'standard_type', 'mandatory') == 'mandatory' else 1
        return (rank, mandatory, std_type)
    return sorted(clauses, key=key)

def hierarchy_label(c: Any) -> str | None:
    h = getattr(c, 'legal_hierarchy', '') or ''
    if h in HIERARCHY_RANK and HIERARCHY_RANK[h] <= 5:
        return '【' + h + '】'
    if getattr(c, 'is_mandatory', False) or getattr(c, 'standard_type', '') == 'mandatory':
        return '【★强制性条文】'
    return None

COMPLEX_INTENTS = {'data_query', 'rule_query', 'compliance_review', 'compare'}
SUFFICIENCY_NOTE = '【依据提示：当前问题较为复杂，现有依据可能不完全充分，建议结合具体专业参数/法律要素核对相关章节】'

def sufficiency_note(intent: str, n_evidence: int) -> str | None:
    if intent in COMPLEX_INTENTS and n_evidence <= 1:
        return SUFFICIENCY_NOTE
    return None

CORRECTION_RE = re.compile(r'不是[ ]*([\u4e00-\u9fffA-Za-z0-9]{2,12})(?:[，,]|$)(?:是[ ]*([\u4e00-\u9fffA-Za-z0-9]{2,12}))?')

# ---------- 检索查询精炼（口语清洗 + 问法关键词扩展） ----------
_NOISE_PREFIX = re.compile(r'^(我要搞个|我想|我想问|请问|帮我查下|帮我查查|咋看|怎么|如何|我想了解)')


_ARABIC_TO_ROMAN = {'1': 'Ⅰ', '2': 'Ⅱ', '3': 'Ⅲ', '4': 'Ⅳ', '5': 'Ⅴ',
                     '6': 'Ⅵ', '7': 'Ⅶ', '8': 'Ⅷ', '9': 'Ⅸ', '10': 'Ⅹ'}
_ROMAN_EXPAND = re.compile(r'([1-9]|10)级')


def refine_search_query(query: str, intent: str, theme: str) -> str:
    """清洗口语噪音并追加问法关键词，提升检索命中（分级/对比等）。"""
    q = _NOISE_PREFIX.sub('', query).strip()
    if not q:
        q = query
    # 分级问法 → 追加核心词
    if re.search(r'分几级|多少级|分几档|几个等级|几级', q):
        q = q + ' 分级 作业高度'
    # 阿拉伯数字级 → 同时追加罗马数字（表2 用 Ⅱ级 等罗马字，FTS 才能命中）
    q = _ROMAN_EXPAND.sub(lambda m: m.group(0) + ' ' + _ARABIC_TO_ROMAN.get(m.group(1), '') + '级', q)
    if intent == 'compare':
        q = q + ' 对比 要求'
    if theme == 'special_work':
        q = q + ' 特殊作业'
    return q


def detect_correction(query: str) -> dict | None:
    if ('不是' not in query) and ('不对' not in query) and ('我说的是' not in query):
        return None
    m = CORRECTION_RE.search(query)
    if m and m.group(1):
        return {'wrong': m.group(1), 'right': m.group(2)}
    m2 = re.search(r'(?:我说的是|我问的是|说的是)[ ]*([\u4e00-\u9fffA-Za-z0-9]{2,12})', query)
    if m2:
        return {'right': m2.group(1)}
    return None
