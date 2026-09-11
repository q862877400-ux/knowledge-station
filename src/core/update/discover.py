"""找标子模块（阶段六·批次3）：口语找标的分类映射、网络检索与待下载清单。

职责（pipeline/02 §1 拓扑 discover.py；F-15~F-18）：
- ``classify(description)``：口语描述 → CCS 分类路径。命中唯一 →
  ``{"category_path": [...], "confidence": float}``；命中多个或过泛
  （如仅「安全」只映射到 C 大类且其子类 >5）→ ``{"questions": [...≤3],
  "candidates": [...]}``——追问风格对齐问答模块追问 v2（R9）：
  单轮一次问完、带候选项与「不确定可回复按…」兜底，绝不连环追问。
  规则分两级：leaf 具体词（消防/电线电缆…）优先并遮蔽 branch 大类词；
  branch 大类词（安全/食品…）仅在没有 leaf 命中时生效。
- ``search(category_path, drill_level, transport=None)``：经注入 transport 查询
  网络渠道（复用 channels/base 的 transport 注入模式与超时归一），返回结果卡片
  ``{standard_no, name, status, mandatory, evidence_url}``（F-17 卡片字段）。
  drill_level > 3 抛 UpdateError('UPD-3002')（pipeline/05 §2 校验层）。
  单测零联网：mock 表驱动 ``tests/fixtures/discover_web.json`` 由测试侧
  构造假 transport 注入，本模块只认 ``transport.fetch(url, **kw) -> (http, body)``
  契约（与 ChannelAdapter 同一约定，body.results[] 为结果数组）。
- 待下载清单（F-18「暂存批量处理」，契约端点 /api/v1/discover/watchlist）：
  ``download_later_add / remove / list`` 存 app_config 键
  ``'discover.download_later'``（JSON 数组 ``[{standard_no,name,added_at}]``），
  add 幂等（按 norm_no 归一号去重）；写路径走 ``write_transaction`` 单写者。

日志规约（pipeline/05 §1）：SPAN='discover'，TRACE 无批次上下文时段占位 '-'。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from src.core.config import get_settings
from src.core.storage.sqlite_db import write_transaction
from src.core.update.channels.base import (
    DEFAULT_TIMEOUT_S,
    UPD_CHANNEL_ERROR,
    UPD_CHANNEL_TIMEOUT,
    UpdateError,
    map_state_text,
    norm_no,
    upd_log,
)
from src.core.update.inspector import get_config

# ---------------------------------------------------------------- 常量
#: 种子树与本模块同目录（唯一允许的数据落点，source=seed 待权威入库扩充）
SEED_PATH = Path(__file__).with_name("ccs_seed.json")
#: 过泛阈值：仅映射到大类且子类数 >5 时必须追问收窄（批次3指令口径）
BROAD_CHILD_LIMIT = 5
#: 下钻深度上限（pipeline/02 §3 drill_level≤3）
MAX_DRILL_LEVEL = 3
UPD_DRILL_EXCEEDED = "UPD-3002"
#: 待下载清单 app_config 键（F-18）
DOWNLOAD_LATER_KEY = "discover.download_later"
#: 追问单轮最多问题数（对齐追问 v2：一次问完 ≤3 问，绝不连环）
MAX_QUESTIONS = 3
#: 网络检索入口（mock 表驱动下 URL 仅作调用记录，不真实触达）
SEARCH_URL = "https://openstd.samr.gov.cn/db/search"
#: 标准号识别（GB/T 3608-2008、GB 50348-2019、GB/T 1.1—2020 等）
_STD_TOKEN_RE = re.compile(r"[A-Z]{1,4}(?:/[TZ])?\s*\d{3,5}(?:\.\d+)?\s*[-—–]\s*\d{4}")
_RESULT_CARD_KEYS = ("standard_no", "name", "status", "mandatory", "evidence_url")

TRACE = "-"  # 找标无巡检批次上下文；inspector 接线后由调用方覆盖


# ================================================================ 种子树加载
_TREE_CACHE: dict | None = None


def load_seed(reload: bool = False) -> dict:
    """加载 CCS 二级种子树（进程内缓存；结构损坏大声报错不静默）。"""
    global _TREE_CACHE
    if _TREE_CACHE is None or reload:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        cats = data.get("categories")
        if not isinstance(cats, list) or not cats:
            raise RuntimeError(f"ccs_seed.json 结构损坏：categories 缺失 ({SEED_PATH})")
        _TREE_CACHE = data
    return _TREE_CACHE


def _children_of(major_code: str) -> list[dict]:
    for cat in load_seed()["categories"]:
        if cat["code"] == major_code:
            return cat.get("children") or []
    return []


def _major_name(major_code: str) -> str:
    for cat in load_seed()["categories"]:
        if cat["code"] == major_code:
            return cat["name"]
    return ""


# ================================================================ 关键词规则
# 两级规则表（keyword → 路径码）。leaf 命中即遮蔽全部 branch 命中；
# 路径必须存在于种子树（load 时校验，写错立刻炸出来而不是静默漏判）。
LEAF_RULES: tuple[dict, ...] = (
    # C 医药卫生与安全
    {"kw": ("消防", "灭火", "防火"), "path": ["C", "C80"], "conf": 0.95},
    {"kw": ("医疗器械", "医疗设备"), "path": ["C", "C30"], "conf": 0.95},
    {"kw": ("饮用水", "防疫", "公共卫生", "卫生"), "path": ["C", "C50"], "conf": 0.85},
    {"kw": ("高处作业", "特种作业", "劳动安全", "安全帽", "防护服",
            "劳保", "劳动保护", "劳动防护", "防护用品", "劳保用品",
            "安全鞋", "防护手套", "护目镜", "安全绳"),
     "path": ["C", "C60"], "conf": 0.90},
    {"kw": ("职业病", "职业健康", "尘肺"), "path": ["C", "C65"], "conf": 0.90},
    # A 综合
    {"kw": ("质量管理", "标准化"), "path": ["A", "A00"], "conf": 0.90},
    {"kw": ("包装", "标志包装"), "path": ["A", "A80"], "conf": 0.85},
    # B 农业
    {"kw": ("肥料", "土壤"), "path": ["B", "B10"], "conf": 0.85},
    {"kw": ("种子种苗", "粮食作物"), "path": ["B", "B20"], "conf": 0.85},
    {"kw": ("兽医", "畜牧"), "path": ["B", "B40"], "conf": 0.85},
    # D 矿业
    {"kw": ("煤炭", "煤矿"), "path": ["D", "D20"], "conf": 0.90},
    # E 石油
    {"kw": ("润滑油", "润滑脂"), "path": ["E", "E49"], "conf": 0.90},
    {"kw": ("汽油", "柴油", "燃料油"), "path": ["E", "E46"], "conf": 0.85},
    # F 能源核技术
    {"kw": ("节能", "能源管理"), "path": ["F", "F01"], "conf": 0.85},
    {"kw": ("辐射防护", "放射防护"), "path": ["F", "F50"], "conf": 0.90},
    {"kw": ("核反应堆", "核电"), "path": ["F", "F60"], "conf": 0.90},
    # G 化工
    {"kw": ("化肥",), "path": ["G", "G20"], "conf": 0.90},
    {"kw": ("农药",), "path": ["G", "G25"], "conf": 0.90},
    {"kw": ("化学试剂",), "path": ["G", "G60"], "conf": 0.95},
    {"kw": ("轮胎",), "path": ["G", "G41"], "conf": 0.90},
    # H 冶金
    {"kw": ("钢板", "钢带"), "path": ["H", "H52"], "conf": 0.85},
    {"kw": ("铁合金",), "path": ["H", "H40"], "conf": 0.85},
    # J 机械
    {"kw": ("阀门",), "path": ["J", "J16"], "conf": 0.95},
    {"kw": ("液压", "气动"), "path": ["J", "J20"], "conf": 0.90},
    {"kw": ("焊接",), "path": ["J", "J33"], "conf": 0.95},
    {"kw": ("泵",), "path": ["J", "J47"], "conf": 0.90},
    {"kw": ("起重机", "行车吊装"), "path": ["J", "J80"], "conf": 0.95},
    # K 电工
    {"kw": ("电线电缆", "电缆", "导线"), "path": ["K", "K13"], "conf": 0.95},
    {"kw": ("变压器",), "path": ["K", "K41"], "conf": 0.95},
    {"kw": ("断路器", "开关设备"), "path": ["K", "K43"], "conf": 0.90},
    {"kw": ("蓄电池", "电池"), "path": ["K", "K82"], "conf": 0.85},
    {"kw": ("电动机", "电机"), "path": ["K", "K21"], "conf": 0.85},
    # L 电子
    {"kw": ("软件", "软件工程"), "path": ["L", "L77"], "conf": 0.90},
    {"kw": ("信息安全", "网络安全", "等级保护"), "path": ["L", "L80"], "conf": 0.95},
    {"kw": ("集成电路", "芯片"), "path": ["L", "L56"], "conf": 0.90},
    # M 通信广播
    {"kw": ("移动通信", "5g"), "path": ["M", "M33"], "conf": 0.90},
    {"kw": ("光纤", "光通信", "光缆"), "path": ["M", "M21"], "conf": 0.90},
    # N 仪器
    {"kw": ("流量计", "流量仪表"), "path": ["N", "N13"], "conf": 0.90},
    {"kw": ("压力表", "压力仪表"), "path": ["N", "N12"], "conf": 0.90},
    # P 工程建设
    {"kw": ("给排水", "给水排水"), "path": ["P", "P40"], "conf": 0.90},
    {"kw": ("抗震", "防震"), "path": ["P", "P55"], "conf": 0.85},
    # Q 建材
    {"kw": ("水泥",), "path": ["Q", "Q11"], "conf": 0.95},
    {"kw": ("混凝土", "砂浆"), "path": ["Q", "Q13"], "conf": 0.90},
    {"kw": ("防水材料", "防水卷材"), "path": ["Q", "Q18"], "conf": 0.90},
    {"kw": ("玻璃",), "path": ["Q", "Q34"], "conf": 0.85},
    {"kw": ("陶瓷",), "path": ["Q", "Q31"], "conf": 0.85},
    # R 公路运输
    {"kw": ("桥梁养护", "道路养护"), "path": ["R", "R16"], "conf": 0.85},
    {"kw": ("客运", "货运", "物流运输"), "path": ["R", "R85"], "conf": 0.80},
    # S 铁路
    {"kw": ("铁路信号",), "path": ["S", "S40"], "conf": 0.90},
    {"kw": ("高铁", "铁路线路"), "path": ["S", "S10"], "conf": 0.80},
    # T 车辆
    {"kw": ("汽车发动机",), "path": ["T", "T20"], "conf": 0.90},
    {"kw": ("摩托车", "电动车两轮"), "path": ["T", "T30"], "conf": 0.85},
    {"kw": ("挂车", "半挂车"), "path": ["T", "T50"], "conf": 0.90},
    # U 船舶
    {"kw": ("救生衣", "救生设备"), "path": ["U", "U48"], "conf": 0.85},
    {"kw": ("船用柴油机", "船舶动力"), "path": ["U", "U30"], "conf": 0.85},
    # V 航空
    {"kw": ("航空发动机",), "path": ["V", "V35"], "conf": 0.90},
    {"kw": ("航电", "机载设备"), "path": ["V", "V50"], "conf": 0.85},
    # W 纺织
    {"kw": ("服装", "纺织品安全"), "path": ["W", "W60"], "conf": 0.90},
    {"kw": ("针织",), "path": ["W", "W40"], "conf": 0.85},
    # X 食品
    {"kw": ("食品安全",), "path": ["X", "X04"], "conf": 0.90},
    {"kw": ("食品添加剂",), "path": ["X", "X42"], "conf": 0.95},
    {"kw": ("乳制品", "牛奶", "乳品"), "path": ["X", "X16"], "conf": 0.90},
    {"kw": ("肉制品", "肉与肉制品"), "path": ["X", "X10"], "conf": 0.90},
    {"kw": ("茶叶",), "path": ["X", "X55"], "conf": 0.95},
    {"kw": ("罐头",), "path": ["X", "X80"], "conf": 0.90},
    {"kw": ("饮料", "酒"), "path": ["X", "X60"], "conf": 0.80},
    # Y 轻工环境
    {"kw": ("玩具",), "path": ["Y", "Y57"], "conf": 0.95},
    {"kw": ("家具",), "path": ["Y", "Y80"], "conf": 0.95},
    {"kw": ("化妆品", "洗涤用品"), "path": ["Y", "Y69"], "conf": 0.90},
    {"kw": ("造纸", "纸巾", "纸箱"), "path": ["Y", "Y30"], "conf": 0.85},
    {"kw": ("皮革", "皮具"), "path": ["Y", "Y45"], "conf": 0.85},
    # Z 环境保护
    {"kw": ("污水", "废水排放", "水污染"), "path": ["Z", "Z35"], "conf": 0.90},
    {"kw": ("废气", "大气污染", "排放烟尘"), "path": ["Z", "Z23"], "conf": 0.90},
    {"kw": ("噪声", "振动"), "path": ["Z", "Z32"], "conf": 0.90},
    {"kw": ("固废", "固体废物", "危险废物"), "path": ["Z", "Z70"], "conf": 0.90},
)

# branch 大类词：仅当无任何 leaf 命中时生效；大类子类 >BROAD_CHILD_LIMIT 即过泛追问
BRANCH_RULES: tuple[dict, ...] = (
    {"kw": ("安全", "劳保", "劳动保护", "防护用品"), "code": "C"},
    {"kw": ("质量", "综合管理"), "code": "A"},
    {"kw": ("农业", "种植", "养殖"), "code": "B"},
    {"kw": ("医药", "医院"), "code": "C"},
    {"kw": ("矿", "矿山", "采矿"), "code": "D"},
    {"kw": ("石油", "油气", "原油"), "code": "E"},
    {"kw": ("能源", "核技术", "核电"), "code": "F"},
    {"kw": ("化工", "化学", "化学品"), "code": "G"},
    {"kw": ("冶金", "钢铁", "金属"), "code": "H"},
    {"kw": ("机械", "机械设备"), "code": "J"},
    {"kw": ("电工", "电气", "电器"), "code": "K"},
    {"kw": ("电子", "信息技术"), "code": "L"},
    {"kw": ("通信", "广播"), "code": "M"},
    {"kw": ("仪器", "仪表", "测量仪表"), "code": "N"},
    {"kw": ("建筑", "建设", "工程", "施工"), "code": "P"},
    {"kw": ("建材", "建筑材料"), "code": "Q"},
    {"kw": ("公路", "道路", "交通运输"), "code": "R"},
    {"kw": ("铁路", "轨道交通"), "code": "S"},
    {"kw": ("汽车", "车辆", "机动车"), "code": "T"},
    {"kw": ("船舶", "造船", "航运"), "code": "U"},
    {"kw": ("航空", "航天", "飞机"), "code": "V"},
    {"kw": ("纺织", "面料", "布料"), "code": "W"},
    {"kw": ("食品", "饮品"), "code": "X"},
    {"kw": ("轻工", "日用品"), "code": "Y"},
    {"kw": ("环境", "环保", "环境保护", "排污"), "code": "Z"},
)


def _validate_rules() -> None:
    """规则路径必须能落到种子树节点（启动期一次性校验，fail-fast）。"""
    known_majors = {c["code"] for c in load_seed()["categories"]}
    for rule in BRANCH_RULES:
        if rule["code"] not in known_majors:
            raise RuntimeError(f"BRANCH_RULES 指向未知大类: {rule['code']}")
    for rule in LEAF_RULES:
        major, child = rule["path"]
        if major not in known_majors:
            raise RuntimeError(f"LEAF_RULES 指向未知大类: {rule['path']}")
        if all(ch["code"] != child for ch in _children_of(major)):
            raise RuntimeError(f"LEAF_RULES 指向未知子类: {rule['path']}")


def _candidate(code: str, name: str, path: list[str]) -> dict:
    return {"code": code, "name": name, "path": path}


# ================================================================ classify
#: 口语前缀/尾缀噪音清洗（2026-08-26：用户实测"找劳保穿戴的国标"、
#: "就是劳动保护用品相关的啊"因口语虚词未清洗而分类 miss——清洗只作用于关键词
#: 匹配，追问展示仍用原始描述）
_DESC_PREFIX = re.compile(
    r'^(我要|我想|帮我找|帮我|请帮我|给我|找一下|查找|查一下|有没有|找找|找|要|就是|是|请问|关于|下载)')
_DESC_SUFFIX = re.compile(
    r'(相关的|方面的|的国标|国标|的标准|标准|的法规|法规|的啊|啊|吧|呢|的|类|些|什么|一下|都要|相关)$')


def _clean_desc(text: str) -> str:
    """去口语虚词，返回清洗后文本（两轮剥前缀/尾缀，处理嵌套如"帮我找…的标准"）。"""
    t = (text or "").strip().lower()
    for _ in range(2):
        t = _DESC_PREFIX.sub("", t)
        t = _DESC_SUFFIX.sub("", t)
    return t.strip()


# ================================================================ LLM 按需分类
# 2026-08-26：规则词表穷举治标不治本（"测一个加一个词"），开放说法由 LLM 语义解析兜底。
# 经济性设计：① 仅规则 miss 时才调 LLM（高频词零成本零延迟）；② 结果 LRU 缓存（重复问零成本）；
# ③ max_tokens=200、温度 0；④ 每次调用走 egress_audit 外发审计（D2 红线）。
# 性能：规则 ms 级 / LLM 1~3s（找标为低频交互，busy 态可接受）；无 Key/失败/非法输出 → 追问兜底。
_LLM_CACHE: dict[str, dict] = {}
_LLM_CACHE_MAX = 200
_ENUM_CACHE: str | None = None

_LLM_SYSTEM = (
    "你是《中国标准文献分类法》(CCS) 分类映射器。用户给出口语化的找标准描述，"
    "你把它映射到最合适的 CCS 二级子类。\n"
    "规则：\n"
    "1. 只输出一个 JSON 对象，不要任何其它文字。\n"
    "2. 分类明确时输出 {\"code\":\"C60\",\"confidence\":0.9}（confidence 0~1）。\n"
    "3. 信息不足需追问时输出 {\"code\":null,\"questions\":[\"…\",\"…\"]}（≤2 问，一句话一问）。\n"
    "4. code 必须来自给定的 CCS 清单；含糊/无法确定时宁可不猜（code:null），绝不编造 code。\n"
    "5. 语义提示：劳保/防护用品/安全帽/防护服/坠落安全带 → C60 劳动安全；"
    "车辆安全带 → T26；食品添加剂 → X42；消防安全 → C80；电线电缆 → K13。\n"
)


def _ccs_enum() -> str:
    """CCS 二级子类紧凑清单（一次生成进程缓存，LLM prompt 用）。"""
    global _ENUM_CACHE
    if _ENUM_CACHE is None:
        lines = []
        for cat in load_seed()["categories"]:
            for ch in cat.get("children") or []:
                lines.append(f"{ch['code']} {ch['name']}")
        _ENUM_CACHE = "\n".join(lines)
    return _ENUM_CACHE


def _parse_llm_json(raw: str) -> dict | None:
    """从 LLM 输出容错提取首个 JSON 对象（容忍前后缀/代码块围栏）。"""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except ValueError:
        return None


def _validate_ccs_code(code: str) -> tuple[str, str] | None:
    """强校验 LLM 输出的 code ∈ 种子树二级子类；非法 → None（绝不信任 LLM 编造）。"""
    m = re.fullmatch(r"([A-Z]\d{2})", (code or "").strip().upper())
    if not m:
        return None
    full = m.group(1)
    major = full[0]
    if all(ch["code"] != full for ch in _children_of(major)):
        return None
    return major, full


def _llm_classify(description: str) -> dict | None:
    """LLM 按需分类（规则 miss 时调用）。无 Key/失败/非法输出 → None（调用方走追问兜底）。"""
    key = _clean_desc(description)
    if key in _LLM_CACHE:
        return _LLM_CACHE[key]
    settings = get_settings()
    if not settings.llm_api_key:
        return None
    from src.core.llm.deepseek_client import LLMError, chat_complete
    from src.core.llm.egress_audit import record_egress

    user = f"CCS 二级子类清单：\n{_ccs_enum()}\n\n用户描述：{description}"
    try:
        record_egress("deepseek", "discover/classify",
                      {"description": description, "endpoint": "discover/classify"},
                      query=description,
                      prompt_preview=f"[LLM 分类映射] {description}")
        raw = chat_complete(_LLM_SYSTEM, user, max_tokens=200, temperature=0.0)
    except LLMError as e:
        upd_log(TRACE, "discover", "WARN", "llm_classify_failed",
                error=str(e)[:120])
        return None
    parsed = _parse_llm_json(raw)
    if parsed is None:
        upd_log(TRACE, "discover", "WARN", "llm_classify_unparseable",
                raw=(raw or "")[:200])
        return None
    code = parsed.get("code")
    if code:
        got = _validate_ccs_code(str(code))
        if got is None:
            upd_log(TRACE, "discover", "WARN", "llm_classify_bad_code", code=code)
            return None
        major, child = got
        child_name = next((ch["name"] for ch in _children_of(major)
                           if ch["code"] == child), "")
        result = {"category_path": [major, child],
                  "confidence": round(float(parsed.get("confidence") or 0.7), 2)}
        upd_log(TRACE, "discover", "INFO", "classify_hit", mode="llm",
                category=f"{major}/{child}", confidence=result["confidence"],
                label=child_name)
    else:
        questions = [str(q).strip() for q in (parsed.get("questions") or [])
                     if str(q).strip()]
        if not questions:
            return None
        result = {"questions": questions[:MAX_QUESTIONS], "candidates": []}
    _LLM_CACHE[key] = result
    if len(_LLM_CACHE) > _LLM_CACHE_MAX:
        _LLM_CACHE.pop(next(iter(_LLM_CACHE)))
    return result


def classify(description: str) -> dict:
    """口语描述 → CCS 路径或一轮追问（协议见模块头注；纯函数零副作用）。"""
    _validate_rules()
    text = (description or "").strip()
    low = _clean_desc(text)

    leaf_paths: list[tuple[tuple[str, str], dict]] = []
    seen: set[tuple[str, str]] = set()
    conf_by_path: dict[tuple[str, str], float] = {}
    label_by_path: dict[tuple[str, str], str] = {}
    for rule in LEAF_RULES:
        if not any(kw in low for kw in rule["kw"]):
            continue
        major, child = rule["path"]
        key = (major, child)
        if key in seen:
            continue
        seen.add(key)
        child_name = next((ch["name"] for ch in _children_of(major)
                           if ch["code"] == child), "")
        leaf_paths.append((key, rule))
        conf_by_path[key] = float(rule["conf"])
        label_by_path[key] = child_name

    # ---- 唯一 leaf 命中：直接给路径（branch 词被遮蔽，如「消防安全」不问「安全」）
    if len(leaf_paths) == 1:
        (major, child), rule = leaf_paths[0]
        upd_log(TRACE, "discover", "INFO", "classify_hit",
                mode="leaf", category=f"{major}/{child}", confidence=rule["conf"])
        return {"category_path": [major, child], "confidence": round(conf_by_path[(major, child)], 2)}

    # ---- 多个 leaf 命中：一轮问完让用户二选一（候选=命中的具体子类）
    if len(leaf_paths) > 1:
        labels = [f"{key[1]} {label_by_path[key]}" for key, _rule in leaf_paths]
        candidates = [_candidate(key[1], label_by_path[key], [key[0], key[1]])
                      for key, _rule in leaf_paths]
        return _ask(
            [f"找到了多个可能的分类：{'、'.join(labels)}——你想找哪一个？"
             "（不确定可回复按候选逐个查看）"],
            candidates)

    # ---- 无 leaf：看 branch 大类词
    majors: list[str] = []
    for rule in BRANCH_RULES:
        if any(kw in low for kw in rule["kw"]) and rule["code"] not in majors:
            majors.append(rule["code"])

    if len(majors) == 1:
        code = majors[0]
        kids = _children_of(code)
        # 过泛（批次3指令示例：仅「安全」→ C 大类且子类 >5）→ 必须追问收窄
        if len(kids) > BROAD_CHILD_LIMIT:
            hint = "、".join(f"{ch['code']} {ch['name']}" for ch in kids[:5]) + "等"
            return _ask(
                [f"「{text}」涉及的范围较广，具体指哪个方向？（{hint}；"
                 f"不确定可回复按 {code} {_major_name(code)} 整个大类检索）"],
                [_candidate(ch["code"], ch["name"], [code, ch["code"]]) for ch in kids])
        upd_log(TRACE, "discover", "INFO", "classify_hit",
                mode="branch", category=code, confidence=0.60,
                children=len(kids))
        return {"category_path": [code], "confidence": 0.60}

    if len(majors) > 1:
        labels = [f"{c} {_major_name(c)}" for c in majors]
        return _ask(
            [f"这个需求可能落在多个领域：{'、'.join(labels)}——你想找哪一个？"
             "（不确定可回复补充更具体的行业或对象名称）"],
            [_candidate(c, _major_name(c), [c]) for c in majors])

    # ---- 完全未识别：先试 LLM 按需语义解析（规则词表穷举的兜底），仍无则单轮追问 ----
    llm = _llm_classify(text)
    if llm:
        return llm
    upd_log(TRACE, "discover", "INFO", "classify_miss", desc_len=len(text))
    return _ask(
        ["没有识别到明确的领域：请补充标准涉及的行业、对象或用途"
         "（例如：消防、电线电缆、食品添加剂），不确定可直接描述使用场景。"],
        [])


def _ask(questions: list[str], candidates: list[dict]) -> dict:
    """追问出口：单轮 ≤3 问一次问完；candidates 供前端气泡点选。"""
    assert len(questions) <= MAX_QUESTIONS, "追问 v2 契约：单轮最多 3 问"
    return {"questions": questions[:MAX_QUESTIONS], "candidates": candidates}


# ================================================================ search
def search(category_path: list[str], drill_level: int = 1,
           transport=None) -> list[dict]:
    """按分类路径查网络渠道，返回结果卡片列表（字段见模块头注，F-17）。

    - ``drill_level`` 为下钻深度，>MAX_DRILL_LEVEL(3) 或非法类型抛
      UpdateError('UPD-3002')；
    - ``transport=None`` 时退回内置 HttpxTransport（生产联调用；离线单测
      必须注入 mock，见 tests/fixtures/discover_web.json 表驱动）；
    - HTTP 非 200 不抛错返回 []（与 channels._miss 同语义）；
    - 结果按归一号去重保序，无法识别标准号的行跳过并告警。
    """
    if isinstance(drill_level, bool) or not isinstance(drill_level, int):
        raise UpdateError(f"illegal_drill_level: {drill_level!r}",
                          code=UPD_DRILL_EXCEEDED)
    if drill_level > MAX_DRILL_LEVEL:
        raise UpdateError(
            f"drill_level_exceeded(>{MAX_DRILL_LEVEL}): {drill_level}",
            code=UPD_DRILL_EXCEEDED)

    if transport is None:
        from src.core.update.channels.base import HttpxTransport
        transport = HttpxTransport()

    path = [str(p).strip() for p in (category_path or []) if str(p).strip()]
    query = " ".join([*path, "标准"]).strip()
    t0 = perf_counter()
    url = SEARCH_URL
    try:
        status, body = transport.fetch(url, timeout=DEFAULT_TIMEOUT_S,
                                       params={"q": query, "page": int(drill_level)})
    except TimeoutError as e:  # 与 base.ChannelAdapter._fetch 同一归一语义
        raise UpdateError(f"channel_timeout: {url}", code=UPD_CHANNEL_TIMEOUT) from e
    except Exception as e:
        if "timeout" in type(e).__name__.lower():
            raise UpdateError(f"channel_timeout: {url}",
                              code=UPD_CHANNEL_TIMEOUT) from e
        raise UpdateError(f"channel_unreachable: {url} ({type(e).__name__}: {e})",
                          code=UPD_CHANNEL_ERROR) from e

    if int(status) != 200:
        upd_log(TRACE, "discover", "WARN", "search_channel_miss",
                category="/".join(path), http=int(status),
                duration_ms=round((perf_counter() - t0) * 1000, 1))
        return []

    results: list[Any] = body.get("results") if isinstance(body, dict) else None
    results = results if isinstance(results, list) else []

    cards: list[dict] = []
    seen_nos: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        card = _to_card(item)
        if card is None:
            upd_log(TRACE, "discover", "WARN", "card_skip_no_stdno",
                    title=str(item.get("title"))[:80])
            continue
        if norm_no(card["standard_no"]) in seen_nos:
            continue
        seen_nos.add(norm_no(card["standard_no"]))
        cards.append(card)

    upd_log(TRACE, "discover", "INFO", "search_done",
            category="/".join(path), drill_level=drill_level,
            results=len(cards),
            duration_ms=round((perf_counter() - t0) * 1000, 1))
    return cards


def _to_card(item: dict) -> dict | None:
    """渠道原始结果行 → 结果卡片；识别不出标准号返回 None（调用方跳过）。"""
    title = str(item.get("title") or "").replace("—", "-").replace("–", "-")
    m = _STD_TOKEN_RE.search(title.upper())
    token = m.group(0) if m else ""
    standard_no = re.sub(r"\s+", " ", token.replace("-", "-")).strip()
    if not standard_no:
        return None

    raw_status = str(item.get("status") or "").strip()
    status = map_state_text(raw_status) or (raw_status or "unknown")

    name = str(item.get("name") or "").strip()
    if not name:
        name = title.upper().replace(standard_no.upper(), "", 1)
        name = name.strip(" -－—–《》　 ")

    upper_token = standard_no.upper()
    mandatory = "/" not in upper_token and upper_token.startswith("GB")

    return {
        "standard_no": standard_no,
        "name": name or title,
        "status": status,
        "mandatory": mandatory,
        "evidence_url": str(item.get("url") or "").strip(),
    }


# ================================================================ download_later
def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_items(raw: str | None) -> list[dict]:
    """app_config 原始串 → 清单条目；损坏数据告警清空（不猜测内容）。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        upd_log(TRACE, "discover", "WARN", "download_later_corrupt_reset")
        return []
    if not isinstance(data, list):
        upd_log(TRACE, "discover", "WARN", "download_later_corrupt_reset")
        return []
    return [it for it in data if isinstance(it, dict) and it.get("standard_no")]


def download_later_list() -> list[dict]:
    """待下载清单（读 app_config 'discover.download_later'）。"""
    return _parse_items(get_config(DOWNLOAD_LATER_KEY))


def download_later_add(standard_no: str, name: str = "") -> list[dict]:
    """加入清单（幂等：norm_no 相同视为同一标准，重复添加不产生重复条目）。"""
    key = norm_no(standard_no)
    if not key:
        raise UpdateError("illegal_standard_no", code="UPD-3007")
    with write_transaction() as txn:
        row = txn.execute(
            "SELECT config_value FROM app_config WHERE config_key=?",
            (DOWNLOAD_LATER_KEY,)).fetchone()
        items = _parse_items(row["config_value"] if row is not None else None)
        if all(norm_no(str(it.get("standard_no"))) != key for it in items):
            items.append({"standard_no": standard_no, "name": name,
                          "added_at": _now_iso()})
            txn.execute(
                "INSERT INTO app_config(config_key, config_value) VALUES(?,?)"
                " ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value,"
                " updated_at=datetime('now')",
                (DOWNLOAD_LATER_KEY, json.dumps(items, ensure_ascii=False)))
    return items


def download_later_remove(standard_no: str) -> list[dict]:
    """移出清单（不存在则为无操作；返回移除后的剩余清单）。"""
    key = norm_no(standard_no)
    with write_transaction() as txn:
        row = txn.execute(
            "SELECT config_value FROM app_config WHERE config_key=?",
            (DOWNLOAD_LATER_KEY,)).fetchone()
        items = _parse_items(row["config_value"] if row is not None else None)
        remaining = [it for it in items
                     if norm_no(str(it.get("standard_no"))) != key]
        if len(remaining) != len(items):
            txn.execute(
                "INSERT INTO app_config(config_key, config_value) VALUES(?,?)"
                " ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value,"
                " updated_at=datetime('now')",
                (DOWNLOAD_LATER_KEY, json.dumps(remaining, ensure_ascii=False)))
    return remaining
