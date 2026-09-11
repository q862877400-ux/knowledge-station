# -*- coding: utf-8 -*-
"""ks-credential-reconcile.py 对账工具单测（批 2c）。

隔离：KS_DATA_DIR → tmp（引擎侧）；DSH 侧用 monkeypatch 假 home。
红线继承：断言里只允许出现指纹/名字，绝不出现明文值。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ks-credential-reconcile.py"


@pytest.fixture()
def reconcile(tmp_path, monkeypatch):
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import reset_settings
    reset_settings()
    spec = importlib.util.spec_from_file_location("ks_reconcile", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    yield mod
    reset_settings()


def _write_dsh_creds(home: Path, entries: dict[str, str]):
    d = home / ".dsh"
    d.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}: {v}" for k, v in entries.items()]
    (d / ".credentials.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_same_key_reports_consistent(reconcile, tmp_path, monkeypatch, capsys):
    from src.core.settings import secret_store
    secret_store.write_values({"KS_LLM_API_KEY": "sk-same-value"})
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_dsh_creds(fake_home, {"DEEPSEEK_API_KEY": "sk-same-value"})
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert reconcile.main() == 0
    out = capsys.readouterr().out
    assert "指纹一致" in out
    assert "sk-same-value" not in out          # 绝不泄值


def test_forked_key_reports_divergence(reconcile, tmp_path, monkeypatch, capsys):
    from src.core.settings import secret_store
    secret_store.write_values({"KS_LLM_API_KEY": "sk-engine-side"})
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _write_dsh_creds(fake_home, {"DEEPSEEK_API_KEY": "sk-dsh-side"})
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert reconcile.main() == 0
    out = capsys.readouterr().out
    assert "指纹不同" in out and "分叉" in out
    assert "sk-engine-side" not in out and "sk-dsh-side" not in out


def test_missing_dsh_file_is_honest(reconcile, tmp_path, monkeypatch, capsys):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert reconcile.main() == 0
    out = capsys.readouterr().out
    assert "空/文件不存在" in out or "两边都未配置" in out


def test_engine_only_side(reconcile, tmp_path, monkeypatch, capsys):
    from src.core.settings import secret_store
    secret_store.write_values({"KS_MINERU_CLOUD_API_KEY": "tok-engine"})
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    assert reconcile.main() == 0
    out = capsys.readouterr().out
    assert "引擎有、DSH 无" in out
    assert "tok-engine" not in out
