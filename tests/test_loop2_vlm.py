# -*- coding: utf-8 -*-
"""Unit tests for the VLM candidate-difference checker (loop2 step 3).

No network / no real vision model: the HTTP call and egress_audit are injected/mocked.
Locks the key semantics: BOTH images must be in the payload (the historical bug),
structured JSON parse, retry, and "no key -> degrade, not raise".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.loop2.vlm_check as vl  # noqa: E402


def _mk_images(tmp_path):
    p1 = tmp_path / "orig.png"
    p2 = tmp_path / "prev.png"
    p1.write_bytes(b"ORIGDATA")
    p2.write_bytes(b"PREVDATA")
    return p1, p2


def test_both_images_sent_and_structured(monkeypatch, tmp_path):
    orig, prev = _mk_images(tmp_path)
    captured = {"payloads": [], "calls": 0}

    def fake(payload, key, endpoint, timeout):
        captured["calls"] += 1
        captured["payloads"].append(payload)
        return ('```json\n{"differences":[{"type":"missing","what":"图缺失",'
                '"severity":"high"}],"summary":"found"}\n```')

    monkeypatch.setattr(vl, "record_egress", lambda *a, **k: "dump_x")
    res = vl.vision_check(orig, prev, key="fake", call=fake, egress=True)

    assert res["ok"] is True
    assert res["hints"] == [{"type": "missing", "what": "图缺失", "severity": "high"}]
    # The fix: TWO image_url entries (orig + prev), NOT one.
    imgs = [c for c in captured["payloads"][0]["messages"][0]["content"]
            if c["type"] == "image_url"]
    assert len(imgs) == 2, "must send BOTH orig and prev"
    assert imgs[0]["image_url"]["url"] != imgs[1]["image_url"]["url"]
    # egress was recorded
    assert res["dump_id"] == "dump_x"


def test_retry_on_transient_error(monkeypatch, tmp_path):
    orig, prev = _mk_images(tmp_path)
    calls = {"n": 0}

    def flaky(payload, key, endpoint, timeout):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("transient")
        return '{"differences":[],"summary":"ok"}'

    monkeypatch.setattr(vl, "record_egress", lambda *a, **k: None)
    res = vl.vision_check(orig, prev, key="fake", call=flaky)
    assert res["ok"] is True
    assert calls["n"] == vl.RETRIES + 1


def test_no_key_degrades_not_raises(monkeypatch, tmp_path):
    orig, prev = _mk_images(tmp_path)
    monkeypatch.setattr(vl, "get_key", lambda: "")
    res = vl.vision_check(orig, prev)
    assert res["ok"] is False and res["error"].startswith("no MOONSHOT")
    assert res["hints"] == []


def test_parse_json_tolerates_fences():
    assert vl._parse_json('```json\n{"a":1}\n```') == {"a": 1}
    assert vl._parse_json("noise {\"b\":2} tail") == {"b": 2}
    assert vl._parse_json("garbage")["summary"] == "parse-error"
