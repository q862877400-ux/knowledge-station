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
                      CoverageUnit, build_units, uncovered_for)


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
