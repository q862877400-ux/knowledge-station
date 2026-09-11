"""找标子模块测试（阶段六·批次3；pipeline/02 §1、F-15~F-18）。

- 全部离线零联网（pipeline/05 §4-8）：search 走注入的表驱动 mock transport，
  应答数据来自 ``tests/fixtures/discover_web.json``；
- classify：过泛口语（「我要下载安全的国标」）必须一轮追问 ≤3 问而非硬选；
  具体词（「消防」）唯一命中路径；多命中/未识别均追问不猜测；
- search：drill_level>3 抛 UPD-3002；结果卡片五字段完整
  {standard_no,name,status,mandatory,evidence_url}；归一号去重、垃圾行跳过、
  HTTP 非 200 不抛错返回空、传输异常归一 UPD-1xxx；
- download_later：app_config 键 'discover.download_later'，add 幂等、remove 生效。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.update.discover import (
    DOWNLOAD_LATER_KEY,
    MAX_DRILL_LEVEL,
    _clean_desc,
    _llm_classify,
    _parse_llm_json,
    _validate_ccs_code,
    classify,
    download_later_add,
    download_later_list,
    download_later_remove,
    load_seed,
    search,
)
from src.core.update.channels.base import norm_no
import src.core.update.discover as discover_mod


@pytest.fixture(autouse=True)
def _no_llm_in_classify(monkeypatch):
    """classify 默认禁用 LLM 兜底（测试确定性；LLM 行为由专项用例显式 mock）。"""
    monkeypatch.setattr(discover_mod, "_llm_classify", lambda desc: None)
    yield

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "discover_web.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class DiscoverMockTransport:
    """表驱动 mock 传输（零联网）：按 params.q 包含 case.key 匹配应答。"""

    def __init__(self, data: dict):
        self._cases = data["cases"]
        self.calls: list[dict] = []

    def fetch(self, url: str, **kw):  # noqa: ANN001 — 与 transport 契约一致
        self.calls.append({"url": url, **kw})
        q = str((kw.get("params") or {}).get("q", ""))
        case = next((c for c in self._cases if c["key"] in q), None)
        if case is None:
            return 404, {}
        return int(case.get("http", 200)), {"results": case.get("results", [])}


# ================================================================ 种子树形态
def test_seed_tree_shape():
    """24 大类齐全，每类 3~8 个二级子类，全部节点 source=seed 待扩充。"""
    data = load_seed(reload=True)
    cats = data["categories"]
    assert len(cats) == 24
    assert [c["code"] for c in cats] == list("ABCDEFGHJKLMNPQRSTUVWX" "YZ")
    assert data.get("source") == "seed"
    for cat in cats:
        kids = cat.get("children") or []
        assert 3 <= len(kids) <= 8, f"{cat['code']} 子类数越界: {len(kids)}"
        assert cat.get("source") == "seed"
        for kid in kids:
            assert kid["code"].startswith(cat["code"]) and kid.get("source") == "seed"


# ================================================================ classify
def test_classify_broad_safety_asks_questions():
    """「我要下载安全的国标」→ 一轮追问 ≤3 问，绝不硬选大类。"""
    result = classify("我要下载安全的国标")
    assert "category_path" not in result          # 不硬选
    questions = result["questions"]
    assert isinstance(questions, list) and questions
    assert len(questions) <= 3                    # 追问 v2：一次问完且 ≤3 问
    candidates = result["candidates"]
    assert candidates                             # 候选=C 大类的二级子类
    assert all(cand["path"][0] == "C" for cand in candidates)


def test_classify_fire_hits_unique_path():
    """「消防」→ 唯一命中路径 C/C80 消防。"""
    result = classify("帮我找消防的标准")
    assert result["category_path"] == ["C", "C80"]
    assert 0 < result["confidence"] <= 1
    assert "questions" not in result


def test_classify_leaf_shadows_branch_keyword():
    """「消防安全」由 leaf 词遮蔽 branch 词，直接命中不追问。"""
    result = classify("消防安全方面的标准")
    assert result["category_path"] == ["C", "C80"]


def test_classify_multi_hit_and_miss_both_ask():
    """多 leaf 命中与完全未识别都走一轮追问，绝不猜测续跑。"""
    multi = classify("消防和电线电缆的标准都要")
    assert "category_path" not in multi
    assert len(multi["questions"]) <= 3
    paths = {tuple(cand["path"]) for cand in multi["candidates"]}
    assert ("C", "C80") in paths and ("K", "K13") in paths

    miss = classify("量子计算原型机")
    assert miss["questions"] and len(miss["questions"]) <= 3
    assert miss["candidates"] == []


def test_classify_labor_protection_hits_c60():
    """「劳保穿戴/劳动保护用品」→ 唯一命中 C/C60 劳动安全（2026-08-26 实测修复：
    此前词表无劳保类关键词 + 口语虚词未清洗 → 与用户补充句一样 miss）。"""
    for desc in ("找劳保穿戴的国标", "就是劳动保护用品相关的啊",
                 "找劳保穿戴的国标；就是劳动保护用品相关的啊"):
        result = classify(desc)
        assert result["category_path"] == ["C", "C60"], desc
        assert 0 < result["confidence"] <= 1


def test_classify_cleans_colloquial_noise():
    """口语虚词清洗只作用于关键词匹配，不破坏既有语义。"""
    assert _clean_desc("帮我找消防的标准") == "消防"
    assert _clean_desc("我要下载安全的国标") == "安全"
    assert _clean_desc("就是劳动保护用品相关的啊") == "劳动保护用品"


# ================================================================ LLM 按需分类
def test_llm_classify_hit_when_rules_miss(monkeypatch):
    """规则 miss 时 LLM 兜底：返回合法路径即采用（开放说法不再依赖词表穷举）。"""
    monkeypatch.setattr(discover_mod, "_llm_classify",
                        lambda desc: {"category_path": ["L", "L60"],
                                      "confidence": 0.8})
    result = classify("量子计算原型机")
    assert result["category_path"] == ["L", "L60"]


def test_validate_ccs_code_rejects_bad_codes():
    """LLM 输出的 code 必须 ∈ 种子树二级子类；编造/非法 → None（强校验防幻觉）。"""
    assert _validate_ccs_code("C60") == ("C", "C60")
    assert _validate_ccs_code("X42") == ("X", "X42")
    assert _validate_ccs_code("C99") is None      # 不存在的子类
    assert _validate_ccs_code("ZZ") is None       # 格式非法
    assert _validate_ccs_code("c80") == ("C", "C80")  # 大小写容忍


def test_parse_llm_json_tolerates_noise():
    """LLM 输出容错：代码块围栏/前后缀不影响 JSON 提取。"""
    assert _parse_llm_json('```json\n{"code":"C60"}\n```') == {"code": "C60"}
    assert _parse_llm_json('映射结果：{"code":"X42","confidence":0.9} 完毕') \
        == {"code": "X42", "confidence": 0.9}
    assert _parse_llm_json("没有 JSON") is None


def test_llm_classify_caches_repeat(monkeypatch):
    """同描述重复分类只调一次 LLM（LRU 缓存，重复问零成本）。"""
    calls = []

    def fake_chat(system, user, **kw):
        calls.append(user)
        return '{"code":"C60","confidence":0.9}'

    monkeypatch.setattr(discover_mod, "get_settings",
                        lambda: type("S", (), {"llm_api_key": "sk-test"})())
    monkeypatch.setattr("src.core.llm.deepseek_client.chat_complete", fake_chat)
    monkeypatch.setattr("src.core.llm.egress_audit.record_egress", lambda *a, **k: "dump_x")
    discover_mod._LLM_CACHE.clear()
    try:
        r1 = _llm_classify("找劳保穿戴的国标")
        r2 = _llm_classify("找劳保穿戴的国标")
        assert r1["category_path"] == ["C", "C60"]
        assert r2 == r1
        assert len(calls) == 1  # 缓存命中，未重复调 LLM
    finally:
        discover_mod._LLM_CACHE.clear()


# ================================================================ search
def test_search_rejects_drill_level_over_limit():
    """drill_level=4 拒绝：UpdateError 且错误码 UPD-3002（校验层）。"""
    for bad in (MAX_DRILL_LEVEL + 1, MAX_DRILL_LEVEL + 10, "2", None, True):
        with pytest.raises(Exception) as ei:
            search(["C", "C80"], bad, transport=DiscoverMockTransport(_load_fixture()))
        assert getattr(ei.value, "code", None) == "UPD-3002", f"bad={bad!r}"


def test_search_mock_three_cards_fields_complete():
    """mock 三条结果：卡片字段完整且与 fixture expect 逐位一致。"""
    data = _load_fixture()
    case = next(c for c in data["cases"] if c["key"] == "C C80")
    transport = DiscoverMockTransport(data)

    cards = search(["C", "C80"], 1, transport=transport)

    expect = case["expect"]
    assert len(cards) == expect["count"] == 3
    for card in cards:
        assert set(card.keys()) >= set(expect["card_keys"])
        assert card["standard_no"], "标准号不得为空"
        assert card["name"], "名称不得为空"
        assert card["status"] and card["status"] != "unknown"
        assert isinstance(card["mandatory"], bool)
        assert str(card["evidence_url"]).startswith("http")
    assert [c["standard_no"] for c in cards] == expect["standard_nos"]
    assert [c["mandatory"] for c in cards] == expect["mandatory"]     # GB 强标 / GB/T 推荐
    assert [c["status"] for c in cards] == expect["statuses"]         # 现行/被代替 → 枚举
    # 上游调用记录可断言（确定性）
    assert len(transport.calls) == 1
    assert "C C80 标准" in transport.calls[0]["params"]["q"]


def test_search_dedupes_and_skips_unparseable_rows():
    """同号重复行去重保序；无标准号的垃圾行跳过。"""
    data = _load_fixture()
    case = next(c for c in data["cases"] if c["key"] == "K K13")

    cards = search(["K", "K13"], 1, transport=DiscoverMockTransport(data))

    assert [c["standard_no"] for c in cards] == case["expect"]["standard_nos"]
    assert all(norm_no(c["standard_no"]) for c in cards)


def test_search_http_miss_returns_empty_not_raise():
    """HTTP 非 200 不抛错返回 []（与 channels._miss 同语义）。"""
    data = _load_fixture()
    assert search(["X", "X04"], 1,
                  transport=DiscoverMockTransport(data)) == []


def test_search_transport_failure_normalized_to_upd1xxx():
    """传输层异常归一：超时→UPD-1001，其余→UPD-1004。"""
    class BoomTransport:
        def __init__(self, exc: Exception):
            self._exc = exc

        def fetch(self, url: str, **kw):  # noqa: ANN001
            raise self._exc

    from src.core.update.channels.base import (
        UPD_CHANNEL_ERROR,
        UPD_CHANNEL_TIMEOUT,
        UpdateError,
    )

    with pytest.raises(UpdateError) as ei:
        search(["C", "C80"], 1, transport=BoomTransport(TimeoutError("t")))
    assert ei.value.code == UPD_CHANNEL_TIMEOUT

    with pytest.raises(UpdateError) as ei:
        search(["C", "C80"], 1, transport=BoomTransport(RuntimeError("boom")))
    assert ei.value.code == UPD_CHANNEL_ERROR


# ================================================================ download_later
def test_download_later_add_idempotent_then_remove(db):  # noqa: ARG001 — db 建 schema
    """加两次只一条（幂等）；再移除后为空；写路径落 app_config 单键。"""
    from src.core.storage.sqlite_db import get_db_connection
    from src.core.update.inspector import get_config

    assert download_later_list() == []

    first = download_later_add("GB 4715-2024", "点型感烟火灾探测器")
    assert len(first) == 1 and first[0]["added_at"]

    # 重复添加（同号不同排版）不产生重复条目
    again = download_later_add("GB  4715-2024", "点型感烟火灾探测器")
    assert len(again) == 1
    assert norm_no(again[0]["standard_no"]) == norm_no("GB 4715-2024")

    download_later_add("GB/T 5023.1-2008", "聚氯乙烯绝缘电缆 第1部分")
    listed = download_later_list()
    assert len(listed) == 2
    assert all(set(item) == {"standard_no", "name", "added_at"} for item in listed)
    assert get_config(DOWNLOAD_LATER_KEY)  # 确实落在 app_config 键上

    remaining = download_later_remove("GB4715-2024")   # 归一号匹配，无需排版一致
    assert [item["standard_no"] for item in remaining] == ["GB/T 5023.1-2008"]

    untouched = download_later_remove("GB 9999-9999")  # 移除不存在项 = 无操作
    assert untouched == remaining

    download_later_remove("gb/t 5023.1-2008")          # 大小写不敏感，归一号匹配
    assert download_later_list() == []
    conn = get_db_connection()
    row = conn.execute("SELECT config_value FROM app_config WHERE config_key=?",
                       (DOWNLOAD_LATER_KEY,)).fetchone()
    assert json.loads(row["config_value"]) == []
