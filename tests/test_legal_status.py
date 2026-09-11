# -*- coding: utf-8 -*-
"""legal_status 到期翻转决议测试（2026-08-27）。

场景：upcoming + effective_from 已到 → effective；未到 → upcoming；
缺日期/格式乱 → 保持；effective/superseded/withdrawn/None 不动。
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.knowledge.legal_status import resolve_status


def _today() -> str:
    return date.today().isoformat()


def test_upcoming_past_date_flips_to_effective():
    """upcoming + 实施日期在昨天 → 翻成 effective。"""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert resolve_status("upcoming", yesterday) == "effective"


def test_upcoming_today_flips_to_effective():
    """upcoming + 实施日期就是今天 → 翻成 effective（今天起施行）。"""
    assert resolve_status("upcoming", _today()) == "effective"


def test_upcoming_future_date_stays():
    """upcoming + 实施日期在未来 → 仍 upcoming。"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert resolve_status("upcoming", tomorrow) == "upcoming"


def test_upcoming_missing_date_stays():
    """upcoming + 缺实施日期 → 保持 upcoming（不猜）。"""
    assert resolve_status("upcoming", None) == "upcoming"
    assert resolve_status("upcoming", "") == "upcoming"


def test_upcoming_malformed_date_stays():
    """upcoming + 非 YYYY-MM-DD → 保持 upcoming。"""
    assert resolve_status("upcoming", "2022/03/15") == "upcoming"
    assert resolve_status("upcoming", "尽快") == "upcoming"


def test_effective_untouched():
    assert resolve_status("effective", None) == "effective"
    assert resolve_status("effective", "2026-01-01") == "effective"


def test_effective_future_date_flips_to_upcoming():
    """effective + 实施日期在未来 → 即将实施（2026-08-29 反向翻转：入库从封面
    提取 effective_from 后，已发布未实施标准如实显示，到点自动翻回现行）。"""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert resolve_status("effective", tomorrow) == "upcoming"
    assert resolve_status("effective", "2027-03-16") == "upcoming"


def test_effective_today_stays_effective():
    """effective + 实施日期就是今天 → 现行（今天起施行）。"""
    assert resolve_status("effective", _today()) == "effective"


def test_effective_malformed_date_stays():
    """effective + 非 YYYY-MM-DD → 保持（不猜）。"""
    assert resolve_status("effective", "尽快") == "effective"


def test_superseded_withdrawn_untouched():
    assert resolve_status("superseded", None) == "superseded"
    assert resolve_status("withdrawn", "2030-01-01") == "withdrawn"


def test_none_untouched():
    assert resolve_status(None, "2026-01-01") is None
