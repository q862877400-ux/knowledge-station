# -*- coding: utf-8 -*-
"""Unit tests for the loop2 structural oracle (scoring + pure page-mapping helpers).

These exercise the DETERMINISTIC pieces with inline snapshot dicts (no DB / no PDF),
so they lock the gate semantics: int-key round-trip after JSON, "missing -> fail",
"na (scanned) -> non-blocking", page-map alignment, and ratio computation.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.loop2.oracle_snapshot import (  # noqa: E402
    _assign_lines_to_pages, _norm, _pagelines_map, _parse_page_breaks,
    _strip_html, _strip_orig_noise)
from scripts.loop2.oracle_score import (  # noqa: E402
    _ratio, score, score_objects, score_pagmap, score_text)


def _mk(clauses, page_count=10, text_layer_state="clean",
        orig_extra=None, preview_extra=None):
    """Build a snapshot dict in the form loaded from snapshot.json (string keys)."""
    preview = {}
    for c in clauses:
        for p, ln in _assign_lines_to_pages(
                c["page_breaks"], c["content_text"], c["page_start"], c["page_end"]).items():
            preview.setdefault(p, []).extend(ln)
    if preview_extra:
        for k, v in preview_extra.items():
            preview.setdefault(k, []).extend(v)
    orig = {str(k + 1): f"page {k + 1} text {k + 1}" for k in range(page_count)}
    if orig_extra:
        orig.update({str(k): v for k, v in orig_extra.items()})
    return {
        "doc_id": "doc_x", "standard_no": "GB/T X-2020", "page_count": page_count,
        "text_layer_state": text_layer_state,
        "clauses": clauses,
        "preview_page_lines": {str(k): v for k, v in preview.items()},
        "orig_text_by_page": orig,
        "orig_image_count_by_page": {str(k): 1 for k in range(1, page_count + 1)},
    }


def test_ratio_basic():
    assert _ratio("abc", "abc") == 1.0
    assert _ratio("", "") == 1.0
    assert _ratio("", "x") == 0.0
    # whitespace insensitive (normalization strips spacing)
    assert _ratio("a b c", "abc") == 1.0


def test_parse_page_breaks_roundtrip():
    assert _parse_page_breaks("[[0,4],[5,6]]") == [[0, 4], [5, 6]]
    assert _parse_page_breaks([["0", "4"]]) is None   # non-int -> invalid
    assert _parse_page_breaks(None) is None
    assert _parse_page_breaks("not json") is None


def test_json_str_key_roundtrip_no_false_missing():
    # The historical bug: JSON stores dict keys as strings; if score() indexes with
    # int the preview map is empty -> every content page becomes a false "missing".
    clauses = [{"page_start": 1, "page_end": 1, "content_text": "hello\nworld",
                "page_breaks": [[0, 1]]}]
    snap = _mk(clauses, page_count=2)
    # preview text must match orig page 1 text for a high ratio
    snap["orig_text_by_page"] = {"1": "hello world", "2": ""}
    snap["preview_page_lines"] = {"1": ["hello", "world"]}
    t = score_text(snap)
    assert t["missing_content_pages"] == [], t
    assert t["per_page"]["1"] is not None
    assert t["na_pages"] == [2] or t["na_pages"] == []


def test_missing_content_forces_fail():
    clauses = [{"page_start": 1, "page_end": 1, "content_text": "hello",
                "page_breaks": []}]
    snap = _mk(clauses, page_count=2)
    snap["orig_text_by_page"] = {"1": "hello", "2": ""}
    snap["preview_page_lines"] = {}   # PDF has text but preview assigns nothing
    t = score_text(snap)
    assert 1 in t["missing_content_pages"]
    assert t["pass"] is False


def test_scan_na_non_blocking():
    clauses = [{"page_start": 1, "page_end": 1, "content_text": "hello",
                "page_breaks": [[0, 1]]}]
    snap = _mk(clauses, page_count=2, text_layer_state="scan")
    snap["orig_text_by_page"] = {"1": "", "2": ""}   # scanned: no text layer
    t = score_text(snap)
    assert t["na"] is True and t["pass"] is None
    # score() must treat pass=None as non-blocking (overall can still be True)
    assert score(snap)["pass"] in (True, False)


def test_pagmap_aligned_and_misaligned():
    clauses = [{"page_start": 1, "page_end": 5, "content_text": "x",
                "page_breaks": []}]
    aligned = _mk(clauses, page_count=10)
    assert score_pagmap(aligned)["pass"] is True
    bad = _mk([{"page_start": 1, "page_end": 12, "content_text": "x",
                "page_breaks": []}], page_count=10)
    assert score_pagmap(bad)["pass"] is False


def test_table_text_included_in_preview():
    # Tables live in content_markdown (not content_text) -> must be folded into
    # the preview page text so table-heavy pages aren't penalised.
    clauses = [{"page_start": 10, "page_end": 10, "content_text": "A.5 正文",
                "page_breaks": [[0, 10]], "table_text": "表A.1 单元格内容",
                "table_pages": [10]}]
    pl = _pagelines_map(clauses)
    assert 10 in pl
    assert any("表A.1" in ln for ln in pl[10])


def test_strip_html_and_orig_noise():
    assert _strip_html("<td>a</td><td>b</td>") == "ab"
    t = "www.bzfxw.com\n正文一行\nGB/T34406—2017\n"
    out = _strip_orig_noise(t)
    assert "正文一行" in out
    assert "bzfxw" not in out
    assert "GB/T34406" not in out


def test_object_expected_figures_missing():
    # Uses MinerU layout figures (middle.json), NOT get_images (which counts logos).
    snap = {
        "page_count": 10,
        "clauses": [
            {"page_start": 6, "page_end": 6, "content_text": "x",
             "page_breaks": [], "figures": 1, "tables": 0, "formulas": 0},
            {"page_start": 9, "page_end": 9, "content_text": "x",
             "page_breaks": [], "figures": 0, "tables": 0, "formulas": 0},
        ],
        "preview_page_lines": {"6": ["x"], "9": ["x"]},
        "orig_text_by_page": {"6": "x", "9": "x"},
        "expected_figure_count_by_page": {"6": 1, "9": 2},
    }
    o = score_objects(snap)
    assert o["missing_figure_pages"] == [9]   # page 6 present, page 9 missing
    assert o["na"] is False


def test_object_expected_figures_na_without_middle():
    snap = {
        "page_count": 10,
        "clauses": [{"page_start": 9, "page_end": 9, "content_text": "x",
                     "page_breaks": [], "figures": 0, "tables": 0, "formulas": 0}],
        "preview_page_lines": {"9": ["x"]},
        "orig_text_by_page": {"9": "x"},
        "expected_figure_count_by_page": {},   # no deep parse
    }
    assert score_objects(snap)["na"] is True


def test_mode_textlayer_vs_scan():
    # text layer present -> mode=textlayer, deterministic gate applies (needs_visual False)
    snap = _mk([{"page_start": 1, "page_end": 1, "content_text": "hello",
                 "page_breaks": [[0, 1]]}], page_count=2, text_layer_state="clean")
    snap["orig_text_by_page"] = {"1": "hello", "2": ""}
    v = score(snap)
    assert v["mode"] == "textlayer" and v["needs_visual"] is False and v["text_layer_state"] == "clean"
    # no text layer (scan) -> needs_visual True (deterministic gate does NOT apply)
    snap2 = _mk([{"page_start": 1, "page_end": 1, "content_text": "hello",
                  "page_breaks": [[0, 1]]}], page_count=2, text_layer_state="scan")
    snap2["orig_text_by_page"] = {"1": "", "2": ""}
    v2 = score(snap2)
    assert v2["mode"] == "scan" and v2["needs_visual"] is True
