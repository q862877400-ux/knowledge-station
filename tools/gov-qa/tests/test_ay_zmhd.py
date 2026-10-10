"""测试：`ay-zmhd`（安阳市·政民互动）适配器的解析与站点约束。

## 为什么

它是**河南第 2 个可采市级源**（第 1 个是商丘 `sq-szxx`）。
本模块的教训是"判据要咬对对象" ⇒ 这里用**真实响应片段**钉住解析。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent.parent / "adapters"


def _load():
    sys.path.insert(0, str(ADAPTERS))
    spec = importlib.util.spec_from_file_location("ay_zmhd_t", ADAPTERS / "ay_zmhd.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_systems_cover_the_three_observed_types():
    """实测只有 3 个非空 `systemType`（0/1/2），第 4 个是空的。

    谁把 `SYSTEMS` 改成包含 3，就会去翻一个恒空的分类（白跑 400 页上限）。
    """
    m = _load()
    assert set(m.SYSTEMS) == {0, 1, 2}, f"实测非空分类只有 0/1/2，实际 {set(m.SYSTEMS)}"
    assert m.SYSTEMS[1] == "市长电话" and m.SYSTEMS[2] == "市长信箱"


def test_clean_keeps_chinese_angle_brackets():
    """**反向用例**：`《出生证明》` 不得被当 HTML 标签吃掉。"""
    m = _load()
    assert "《出生证明》" in m._clean("请携带《出生证明》原件")


def test_real_treats_literal_null_as_absent():
    m = _load()
    assert m._real("null") == ""
    assert m._real(None) == ""
    assert m._real("真内容") == "真内容"


def test_norm_dt_converts_the_slash_format():
    """站点给 `2026/10/9 10:38:35`，本模块统一 `2026-10-09 10:38:35`。

    ⚠ **月/日要补零** —— 不补的话 `2026-10-9` 与本模块其它源格式不一致，
    下游按字符串比时间会出错（本模块已因"裸比字符串"踩过坑）。
    """
    m = _load()
    assert m._norm_dt("2026/10/9 10:38:35") == "2026-10-09 10:38:35"
    assert m._norm_dt("2026/9/28 8:06:56") == "2026-09-28 08:06:56"
    assert m._norm_dt("") is None
    assert m._norm_dt("不是时间") is None


def test_page_size_is_bounded():
    """**站点约束**：一页最多取多少条（防止把站点拖垮 / 自己内存爆）。

    实测站点接受 `size=20`；本适配器固定 20。
    """
    m = _load()
    assert 1 <= m.PAGE_SIZE <= 50, f"PAGE_SIZE={m.PAGE_SIZE} 不合理"


def test_pause_is_not_aggressive():
    """**站点约束**：请求间隔不得为 0（本模块在商丘因 1.0s 触发过全站 403）。"""
    m = _load()
    assert m.PAUSE >= 0.3, f"PAUSE={m.PAUSE} 太激进"
