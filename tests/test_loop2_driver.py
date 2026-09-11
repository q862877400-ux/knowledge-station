# -*- coding: utf-8 -*-
"""Unit tests for the bounded loop orchestrator (driver_v2).

These exercise the pure state-machine + registry + stop logic. State paths are
monkeypatched to a tmp dir so nothing touches the real campaign data. No DB/PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import scripts.loop2.driver_v2 as d  # noqa: E402


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(d, "STATE_DIR", tmp_path)
    monkeypatch.setattr(d, "QUEUE", tmp_path / "queue.json")
    monkeypatch.setattr(d, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(d, "PASSED", tmp_path / "passed.json")
    monkeypatch.setattr(d, "ISSUES", tmp_path / "issues.json")
    monkeypatch.setattr(d, "LOG", tmp_path / "debug_log.txt")
    monkeypatch.setattr(d, "STOP_CONSECUTIVE", 5)
    monkeypatch.setattr(d, "MAX_BLOCKED", 5)
    monkeypatch.setattr(d, "M_SILENCE", 5)
    return d


def test_consecutive_only_on_round1_pass(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert d.record_pass("A", 1)["consecutive"] == 1
    assert d.record_pass("B", 1)["consecutive"] == 2
    # multi-round pass still records but resets the "first-import-perfect" streak
    assert d.record_pass("C", 3)["consecutive"] == 0
    assert d.record_pass("D", 1)["consecutive"] == 1
    # D in passed set
    assert "C" in d._load(d.PASSED, {"passed": []})["passed"]


def test_fail_and_blocked_reset_consecutive(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    d.record_pass("A", 1)
    d.record_pass("B", 1)
    d.record_fail("C", 1, note="x")
    assert d._load(d.PASSED, {})["consecutive"] == 0
    d.record_pass("D", 1)
    d.record_pass("E", 1)
    d.record_blocked("F")
    assert d._load(d.PASSED, {})["consecutive"] == 0
    assert "F" in d._load(d.ISSUES, {})["blocked"]


def test_three_strike_arms_and_solve_clears(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert d.record_issue("rc:ingest-x", "A", "a.pdf")["armed"] is False
    assert d.record_issue("rc:ingest-x", "B", "b.pdf")["armed"] is False
    r = d.record_issue("rc:ingest-x", "C", "c.pdf")
    assert r["armed"] is True and r["count"] == 3
    iss = d._load(d.ISSUES, {})
    assert len(iss["three_strikes"]) == 1
    # armed stays; count keeps climbing until solve() clears it
    assert d.record_issue("rc:ingest-x", "D", "d.pdf")["count"] == 4
    d.solve_issue("rc:ingest-x", "unified figure abstraction")
    iss = d._load(d.ISSUES, {})
    assert iss["classes"]["rc:ingest-x"]["count"] == 0
    assert iss["classes"]["rc:ingest-x"]["armed"] is False


def test_converged_requires_5_round1_and_no_blocked(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert d.is_converged()["met"] is False
    for c in "ABCDE":
        d.record_pass(c, 1)
    assert d.is_converged()["met"] is True  # 5 consecutive round-1 passes
    d.record_blocked("Z")
    assert d.is_converged()["met"] is False  # blocked -> not converged


def test_build_queue_dedups(monkeypatch, tmp_path):
    # Build a fake tree with a duplicate standard_no filename (dedup by std_no).
    root = tmp_path / "lib"
    (root / "a").mkdir(parents=True)
    (root / "a" / "GB／T 9999-2020 测试.pdf").write_bytes(b"%PDF")
    (root / "a" / "GB／T 9999-2020 测试(1).pdf").write_bytes(b"%PDF")
    d.build_queue(root)
    q = d._load(d.QUEUE, {})
    assert len(q["books"]) == 1
    assert q["books"][0]["std_no"] == "GB/T9999-2020"


def test_seed_issues_populates_classes(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    res = d.seed_issues()
    assert res["seeded"] == len(d.SEED_ROOT_CAUSES)
    iss = d._load(d.ISSUES, {})
    for rc in d.SEED_ROOT_CAUSES:
        assert rc in iss["classes"]
        assert iss["classes"][rc]["count"] == 0
