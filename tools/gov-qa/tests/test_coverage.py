"""测试：覆盖销号表（US2）。

对应 spec 004 的 FR-007 ~ FR-011 / SC-004 ~ SC-006。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from channel import Channel, _city_from_name, _province_from_name, infer_region  # noqa: E402
from coverage import (DEFAULT_THRESHOLD_CITY, DEFAULT_THRESHOLD_PROVINCE,      # noqa: E402
                      PROVINCE_NAMES, STATUS_NONE, STATUS_OK, STATUS_THIN,
                      CoverageUnit, build_units, known_cities, merge_city_data,
                      norm_city, uncovered_for)


# ---------------------------------------------------------------- 名单完整性

def test_province_list_is_31():
    """**SC-004**：31 个省级行政区，一个不能少。"""
    assert len(PROVINCE_NAMES) == 31, f"应为 31，实际 {len(PROVINCE_NAMES)}"


def test_all_provinces_get_a_row():
    """**SC-004**：每个省级行政区都有销号行 —— 哪怕一条数据都没有。"""
    units = build_units([], {}, threshold_province=100, threshold_city=10)
    prov = [u for u in units if u.level == "province"]
    assert len(prov) == 31
    names = {u.name for u in prov}
    for n in PROVINCE_NAMES:
        assert n in names, f"{n} 缺行"


def test_province_without_channel_is_none():
    """无来源的省 ⇒ status=none（**硬缺口**，不是深度问题）。"""
    units = build_units([], {}, threshold_province=100, threshold_city=10)
    prov = [u for u in units if u.level == "province"]
    assert all(u.status == STATUS_NONE for u in prov)


# ---------------------------------------------------------------- 缺口计算

def test_gap_calculation():
    """**SC-005**：缺口 = max(0, 达标线 - 落盘量)，且 落盘量 + 缺口 ≥ 达标线。"""
    u = CoverageUnit("测试省", "province", threshold=1000)
    u.channels = ["k1"]
    u.total_records = 300
    u.recompute()
    assert u.gap == 700
    assert u.status == STATUS_THIN
    assert u.total_records + u.gap >= u.threshold


def test_meets_threshold_is_ok():
    u = CoverageUnit("测试省", "province", threshold=1000)
    u.channels = ["k1"]
    u.total_records = 1000
    u.recompute()
    assert u.gap == 0
    assert u.status == STATUS_OK


def test_threshold_is_adjustable():
    """达标线可调 ⇒ 所有 gap 同步变化（FR-033）。"""
    ch = [Channel("k1", level="province", region="云南省")]
    counts = {"k1": 500}
    a = [u for u in build_units(ch, counts, threshold_province=3000,
                                threshold_city=500) if u.level == "province"]
    b = [u for u in build_units(ch, counts, threshold_province=300,
                                threshold_city=500) if u.level == "province"]
    ya = next(u for u in a if u.name == "云南省")
    yb = next(u for u in b if u.name == "云南省")
    assert ya.gap == 2500
    assert yb.gap == 0
    assert ya.status == STATUS_THIN
    assert yb.status == STATUS_OK


# ---------------------------------------------------------------- 相对中位数

def test_ratio_to_median_is_same_level():
    """**R4**：比值必须**同级比同级**，不跨级。"""
    ch = [
        Channel("p1", level="province", region="云南省"),
        Channel("p2", level="province", region="四川省"),
        Channel("c1", level="city", region="大理市"),
    ]
    counts = {"p1": 100, "p2": 300, "c1": 50}
    units = build_units(ch, counts, threshold_province=1000, threshold_city=100)
    yn = next(u for u in units if u.name == "云南省")
    sc = next(u for u in units if u.name == "四川省")
    dl = next(u for u in units if u.name == "大理市")
    # 省级中位数 = 200（100 和 300 的中间）
    assert yn.ratio_to_median == 0.5, yn.ratio_to_median
    assert sc.ratio_to_median == 1.5, sc.ratio_to_median
    # 市级只有自己 ⇒ 比值 1.0（不能拿省级的 200 来除）
    assert dl.ratio_to_median == 1.0, dl.ratio_to_median


# ---------------------------------------------------------------- 未覆盖渠道

def test_uncovered_lists_missing_channels():
    """**SC-006**：能列出该地区**尚未建源的渠道**（不只是"数据少"）。"""
    ch = [Channel("yn-xf", level="province", region="云南省")]
    units = build_units(ch, {"yn-xf": 10}, threshold_province=3000,
                        threshold_city=500)
    yn = next(u for u in units if u.name == "云南省")
    miss = uncovered_for(yn, ch)
    assert "已穷尽" not in miss, "只有 yn-xf 一个来源，不该是已穷尽"
    assert any("12345" in m for m in miss), miss


def test_uncovered_exhausted_is_explicit():
    """**关键**：渠道全部覆盖时返回 `已穷尽`，**不留空** ——
    否则无法区分「查完没有」和「没查」。"""
    ch = [
        Channel("yn-hdjl", level="province", region="云南省"),   # 门户·政民互动
        Channel("yn-12345", level="province", region="云南省"),  # 12345
        Channel("yn-szxx", level="province", region="云南省"),   # 省长信箱
        Channel("rd-yn", level="province", region="云南省"),     # 人大
    ]
    units = build_units(ch, {}, threshold_province=3000, threshold_city=500)
    yn = next(u for u in units if u.name == "云南省")
    miss = uncovered_for(yn, ch)
    assert miss == ["已穷尽"], miss


# ---------------------------------------------------------------- 地区名提取

def test_city_extraction():
    """市级通道的名字不含省名 ⇒ 必须能独立提出市名（**实测踩过的坑**）。"""
    assert _city_from_name("宝鸡市·政民互动信箱（IGI）") == "宝鸡市"
    assert _city_from_name("武汉市人民政府·市长信箱（12345）") == "武汉市"
    assert _city_from_name("大理白族自治州·政民互动") == ""


def test_municipality_not_counted_as_city():
    """北京/天津/上海/重庆 是**省级**，不能算成地级市。"""
    assert _city_from_name("北京市·政民互动") == ""
    assert _city_from_name("上海市·市长信箱") == ""


def test_province_extraction():
    assert _province_from_name("云南省人民政府·政民互动") == "云南省"
    assert _province_from_name("内蒙古自治区人民政府") == "内蒙古自治区"
    assert _province_from_name("北京市人民政府") == "北京市"


def test_infer_region_city_level():
    lvl, reg = infer_region({"name": "宝鸡市·政民互动信箱（IGI）", "level": "city"})
    assert lvl == "city"
    assert reg == "宝鸡市"


# ================================================================ 数据口径
# 2026-10-10 第 7 轮：修「通道口径」漏计一整片市的问题。
# 实测动机：辽宁 14 个市里 12 个有数据（在省级 `ln-8890` 里，带 extra.city），
# 但只按通道数会被报成「13 个缺来源」。见 `CoverageUnit.data_records`。

def test_norm_city():
    """市名归一化：补「市」，但**自治州/地区/盟不得被补成市**。"""
    assert norm_city("洛阳市") == "洛阳市"
    assert norm_city("洛阳") == "洛阳市"
    assert norm_city(" 张掖市 ") == "张掖市"
    assert norm_city("昌吉回族自治州") == "昌吉回族自治州"
    assert norm_city("阿克苏地区") == "阿克苏地区"
    assert norm_city("锡林郭勒盟") == "锡林郭勒盟"
    assert norm_city(None) == ""
    assert norm_city("") == ""


def test_known_cities_covers_334():
    """334 个地级行政区的名单要能读到（`count_by_city` 用它过滤占位值）。"""
    ks = known_cities()
    assert len(ks) >= 330, f"名单过小：{len(ks)}"
    assert "鞍山市" in ks
    assert "昌吉回族自治州" in ks


def test_data_records_drive_city_status():
    """★ 核心修复：省级平台通道带 `extra.city` ⇒ 该市**不得**被判 `none`。

    复现：辽宁 `ln-8890`（省级 12345 平台）的 2,307 条鞍山记录。
    旧逻辑 `total_records == 0 and not channels` ⇒ `none`（错）。
    """
    u = CoverageUnit("鞍山市", "city", threshold=500)
    assert u.total_records == 0 and not u.channels
    u.recompute()
    assert u.status == STATUS_NONE, "没有数据时确实应为 none（前提校验）"

    u.data_records = 2307          # 数据来自省级通道
    u.recompute()
    assert u.status == STATUS_OK, "有数据就必须是 ok，不能再判 none"
    assert u.gap == 0


def test_data_records_thin_when_below_threshold():
    """数据口径同样走达标线判定 —— 低于线是 `thin`，不是 `ok`。"""
    u = CoverageUnit("抚顺市", "city", threshold=500)
    u.data_records = 100
    u.recompute()
    assert u.status == STATUS_THIN
    assert u.gap == 400


def test_merge_city_data_creates_units_for_data_only_cities():
    """只靠省级通道覆盖的市要被**补建**为市级单元，且 `total_records` 仍为 0。"""
    units = build_units([], {}, threshold_province=3000, threshold_city=500)
    added = merge_city_data(units, {"鞍山市": 2307, "抚顺市": 100})
    assert added == 2

    an = next(u for u in units if u.name == "鞍山市")
    assert an.data_records == 2307
    assert an.total_records == 0, "它确实没有专属通道，不能凭空记成通道产出"
    assert an.status == STATUS_OK

    fs = next(u for u in units if u.name == "抚顺市")
    assert fs.status == STATUS_THIN


def test_merge_does_not_inflate_province_total():
    """★ 防重复计数：补建市级单元**不得**改变省级 `total_incl_cities`。

    省级通道的记录本身已计入省级 `total_records`，再加一次会把省总量翻倍
    （辽宁 `ln-8890` 2 万条全带 `extra.city`）。
    """
    ch = [Channel("ln-8890", level="province", region="辽宁省")]
    base = build_units(ch, {"ln-8890": 20000},
                       threshold_province=3000, threshold_city=500)
    ln0 = next(u for u in base if u.name == "辽宁省")

    withdata = build_units(ch, {"ln-8890": 20000}, threshold_province=3000,
                           threshold_city=500,
                           city_counts={"鞍山市": 2307, "抚顺市": 2189})
    ln1 = next(u for u in withdata if u.name == "辽宁省")
    assert ln1.total_incl_cities == ln0.total_incl_cities, "省级总量被重复计数了"
    assert ln1.total_records == 20000


def test_count_by_city_filters_placeholder_and_falls_back(tmp_path, monkeypatch):
    """数据口径归属：优先 `extra.city`；缺失时按市级通道兜底；
    **`市辖区` 这类占位值必须被过滤**（否则会凭空造出「市辖区市」）。"""
    import json

    import coverage as cov

    rows = [
        {"source": "ln-8890", "extra": {"city": "鞍山市"}},
        {"source": "ln-8890", "extra": {"city": "鞍山市"}},
        {"source": "ln-8890", "extra": {"city": "市辖区"}},      # 占位值
        {"source": "ln-8890", "extra": {"city": "省直辖县级行政区划"}},
        {"source": "gs-zhangye", "extra": {}},                   # 无 city，靠通道兜底
    ]
    (tmp_path / "x.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    monkeypatch.setattr(cov, "DATA_DIR", tmp_path)

    got = cov.count_by_city({"gs-zhangye": "张掖市"})
    assert got == {"鞍山市": 2, "张掖市": 1}, got
    assert all("市辖区" not in k for k in got)


def test_count_by_city_extra_city_wins_over_channel(tmp_path, monkeypatch):
    """`extra.city` 优先于通道兜底 —— 否则省级通道会把记录全算到一个市上。"""
    import json

    import coverage as cov

    rows = [{"source": "ln-8890", "extra": {"city": "大连市"}},
            {"source": "ln-8890", "extra": {"city": "鞍山市"}}]
    (tmp_path / "y.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    monkeypatch.setattr(cov, "DATA_DIR", tmp_path)
    got = cov.count_by_city({})
    assert got == {"大连市": 1, "鞍山市": 1}, got
