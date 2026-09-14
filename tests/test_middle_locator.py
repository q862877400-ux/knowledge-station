"""middle_locator 契约测试（OCR 循环轮次 1 根因修复配套）。

锁定：模式集顺序（老命名优先）、layout.json 识别、防重复、空目录行为。
云产物改名事件（2026-09-14）不再能静默打穿 3 个消费者。
"""
import json
from pathlib import Path

import pytest

from src.core.ingestion.middle_locator import (
    MIDDLE_PATTERNS, find_middle_files, iter_middle_files)


def _mk(d: Path, name: str) -> Path:
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"pdf_info": []}), encoding="utf-8")
    return p


class TestPatterns:
    def test_pattern_order_legacy_first(self):
        # 老命名优先——本地产物稳定在 layout 之前被找到
        assert MIDDLE_PATTERNS.index("*_middle.json") < MIDDLE_PATTERNS.index("layout.json")

    def test_layout_in_patterns(self):
        assert "layout.json" in MIDDLE_PATTERNS


class TestFind:
    def test_finds_legacy_middle(self, tmp_path):
        _mk(tmp_path, "auto/doc_middle.json")
        assert len(find_middle_files(tmp_path)) == 1

    def test_finds_layout_cloud_rename(self, tmp_path):
        # 云产物改名事件：layout.json 必须被识别（轮次 1 根因）
        _mk(tmp_path, "auto/doc_layout.json")
        files = find_middle_files(tmp_path)
        assert len(files) == 1 and files[0].name == "doc_layout.json"

    def test_finds_bare_middle(self, tmp_path):
        _mk(tmp_path, "middle.json")
        assert len(find_middle_files(tmp_path)) == 1

    def test_all_three_coexist_deduped(self, tmp_path):
        _mk(tmp_path, "a/doc_middle.json")
        _mk(tmp_path, "b/middle.json")
        _mk(tmp_path, "c/layout.json")
        assert len(find_middle_files(tmp_path)) == 3

    def test_legacy_first_when_both(self, tmp_path):
        _mk(tmp_path, "x_middle.json")
        _mk(tmp_path, "layout.json")
        assert find_middle_files(tmp_path)[0].name == "x_middle.json"

    def test_empty_or_missing_root(self, tmp_path):
        assert find_middle_files(tmp_path / "nope") == []
        assert find_middle_files(tmp_path) == []

    def test_sorted_within_pattern(self, tmp_path):
        _mk(tmp_path, "b_middle.json")
        _mk(tmp_path, "a_middle.json")
        names = [p.name for p in find_middle_files(tmp_path)]
        assert names == ["a_middle.json", "b_middle.json"]

    def test_iter_yields_same_as_find(self, tmp_path):
        _mk(tmp_path, "auto/doc_layout.json")
        assert list(iter_middle_files(tmp_path)) == find_middle_files(tmp_path)

    def test_nested_depth(self, tmp_path):
        _mk(tmp_path, "mineru/cloud_abc/auto/doc_layout.json")
        assert len(find_middle_files(tmp_path)) == 1

    def test_non_json_ignored(self, tmp_path):
        (tmp_path / "layout.txt").write_text("x", encoding="utf-8")
        assert find_middle_files(tmp_path) == []
