# -*- coding: utf-8 -*-
"""凭据读者排查脚本回归测试（整改批 1b）。

只测纯函数与结构，不碰真实注册表/文件（扫描函数以 monkeypatch 注入假数据）。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ks-credential-readers-scan.py"


def _load():
    spec = importlib.util.spec_from_file_location("ks_readers_scan", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_findings_in_text_finds_old_and_new_names():
    m = _load()
    text = "api_key: $env:DEEPSEEK_API_KEY\nother: KS_LLM_BASE_URL"
    assert set(m._findings_in_text(text)) == {"DEEPSEEK_API_KEY", "KS_LLM_BASE_URL"}


def test_findings_in_text_empty():
    m = _load()
    assert m._findings_in_text("nothing here") == []


def test_old_new_name_lists_are_disjoint():
    m = _load()
    assert not (set(m.NAMES_OLD) & set(m.NAMES_NEW))


def test_scan_credential_files_reports_presence(monkeypatch, tmp_path):
    m = _load()
    cred = tmp_path / ".dsh" / ".credentials.yaml"
    cred.parent.mkdir()
    cred.write_text("keys:\n  DEEPSEEK_API_KEY: something\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    out = m.scan_credential_files()
    dsh = [x for x in out if ".credentials.yaml" in x["where"]][0]
    assert dsh["exists"] is True
    assert "DEEPSEEK_API_KEY" in dsh["names_found"]
    # 不存在值：names_found 只含名字，绝无真值
    assert all("something" not in str(x) for x in out)


def test_scan_credential_files_missing_home(monkeypatch, tmp_path):
    m = _load()
    empty = tmp_path  # 空 home
    monkeypatch.setattr(Path, "home", lambda: empty)
    out = m.scan_credential_files()
    assert all(x["exists"] is False for x in out)


def test_scan_shell_configs_autorun_absent(monkeypatch, tmp_path):
    m = _load()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    out = m.scan_shell_configs()
    # 全部不存在 + 不炸（cmd AutoRun 分支静默）
    assert isinstance(out, list)
