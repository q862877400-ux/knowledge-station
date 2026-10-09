"""测试：通道层（T013）。

验证通道清单覆盖全部 adapter，且推断结果合理。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from channel import (PROVINCES, Channel, group_by_level,       # noqa: E402
                     infer_region, load_channels)


def test_channels_cover_all_adapters():
    """**关键**：通道清单必须覆盖 `adapters.ADAPTERS` 里的每一个。

    漏一个的后果：那个 adapter 变成「隐身」的 —— 零数据检测也发现不了它。
    """
    import adapters
    chs = load_channels()
    keys = {c.key for c in chs}
    missing = set(adapters.ADAPTERS) - keys
    assert not missing, f"这些 adapter 没进通道清单：{sorted(missing)[:10]}"
    assert len(chs) == len(adapters.ADAPTERS)


def test_every_channel_has_valid_watermark_type():
    chs = load_channels()
    bad = [c for c in chs if c.watermark_type not in ("page", "since", "idset")]
    assert not bad, f"非法水位类型：{[(c.key, c.watermark_type) for c in bad][:5]}"


def test_unknown_adapter_load_failure_still_registered():
    """加载失败的 adapter 也要登记 —— 否则零数据检测会漏掉它。"""
    chs = load_channels()
    assert all(c.key for c in chs)


def test_infer_region_province():
    lvl, reg = infer_region({"name": "云南省人民政府·政民互动"})
    assert lvl == "province"
    assert "云南" in reg


def test_infer_region_national():
    lvl, reg = infer_region({"name": "生态环境部·互动交流"})
    assert lvl == "national"


def test_infer_region_explicit_level_wins():
    lvl, reg = infer_region({"name": "随便什么名字", "level": "city"})
    assert lvl == "city"


def test_group_by_level():
    chs = [Channel("a", level="province"), Channel("b", level="city"),
           Channel("c", level="province")]
    g = group_by_level(chs)
    assert len(g["province"]) == 2
    assert len(g["city"]) == 1


def test_provinces_list_is_complete():
    """31 个省级行政区 + 港澳台 = 34。"""
    assert len(PROVINCES) == 34, f"省级名单应为 34 项，实际 {len(PROVINCES)}"
