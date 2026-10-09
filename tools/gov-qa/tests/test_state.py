"""测试：水位层（T012）。

覆盖 data-model.md E2 的四条硬规则：
1. 水位只在成功后前移（FR-003）
2. 失败时 value 不动，只累加 consecutive_failures
3. 水位文件损坏 ⇒ 安全退化（FR-006）
4. idset 型 LRU 上限（防 JSON 无限膨胀）
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from state import IDSET_MAX, Watermark, WatermarkStore  # noqa: E402


def _store(tmp: Path) -> WatermarkStore:
    return WatermarkStore(tmp / "watermarks.json")


def test_serialize_roundtrip():
    w = Watermark("k1", "page", value=5, last_success_at=None, updated_at=None)
    w2 = Watermark.from_dict(w.to_dict())
    assert w2.channel_key == "k1"
    assert w2.type == "page"
    assert w2.value == 5


def test_invalid_type_rejected():
    try:
        Watermark("k", "nonsense")
    except ValueError:
        return
    raise AssertionError("非法水位类型应被拒绝")


def test_success_moves_watermark():
    with tempfile.TemporaryDirectory() as d:
        s = _store(Path(d))
        s.ensure("k", "page")
        s.mark_success("k", new_value=3, batch_count=10)
        assert s.get("k").value == 3
        assert s.get("k").last_batch_count == 10
        assert s.get("k").consecutive_failures == 0


def test_failure_does_not_move_watermark():
    """**FR-003 的核心**：失败绝不能前移水位。"""
    with tempfile.TemporaryDirectory() as d:
        s = _store(Path(d))
        s.ensure("k", "page")
        s.mark_success("k", new_value=7, batch_count=5)
        n = s.mark_failure("k")
        assert n == 1
        assert s.get("k").value == 7, "失败后 value 不得改变"
        s.mark_failure("k")
        assert s.get("k").consecutive_failures == 2
        assert s.get("k").value == 7, "连续失败后 value 仍不得改变"


def test_broken_file_degrades_safely():
    """**FR-006**：水位文件损坏时不得抛异常，且要标记需要全量。"""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "watermarks.json"
        p.write_text("{{{ 这不是合法 JSON", encoding="utf-8")
        s = WatermarkStore(p)
        assert s.broken is True
        assert s.needs_full("any-key") is True
        # 不抛异常即通过
        s.ensure("any-key", "idset")
        s.save()


def test_missing_file_is_not_broken():
    """文件不存在 ≠ 损坏（首次运行是正常状态）。"""
    with tempfile.TemporaryDirectory() as d:
        s = _store(Path(d))
        assert s.broken is False
        assert s.needs_full("k") is True


def test_idset_lru_cap():
    """idset 型必须有上限，否则 JSON 无限膨胀。"""
    with tempfile.TemporaryDirectory() as d:
        s = _store(Path(d))
        s.ensure("k", "idset")
        huge = [f"id{i}" for i in range(IDSET_MAX + 5000)]
        s.mark_success("k", new_value=huge, batch_count=len(huge))
        v = s.get("k").value
        assert isinstance(v, list)
        assert len(v) <= IDSET_MAX, f"应裁剪到 {IDSET_MAX}，实际 {len(v)}"
        assert len(set(v)) == len(v), "裁剪后不得有重复 id"


def test_type_change_invalidates_value():
    """adapter 改造导致水位类型变化 ⇒ 值作废，退回全量（宁可慢不可漏）。"""
    with tempfile.TemporaryDirectory() as d:
        s = _store(Path(d))
        s.ensure("k", "page")
        s.mark_success("k", new_value=9, batch_count=1)
        s.ensure("k", "since")
        assert s.get("k").value is None


def test_persistence():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "watermarks.json"
        s = WatermarkStore(p)
        s.ensure("k", "page")
        s.mark_success("k", new_value=42, batch_count=3)
        s.save()
        raw = json.loads(p.read_text(encoding="utf-8"))
        assert raw["k"]["value"] == 42
        s2 = WatermarkStore(p)
        assert s2.get("k").value == 42
