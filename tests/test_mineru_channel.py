# -*- coding: utf-8 -*-
"""深度解析通道选择测试（2026-09-08 用户修订：云优先 → 本地兜底）。

语义矩阵：
- 未配置云 Key → 纯本地（不触云）；
- 配置云 Key → 云优先；云失败 → 本地兜底；
- KS_MINERU_CLOUD=0 → 显式禁用云（纯本地）；
- KS_MINERU_LOCAL=0 + 云失败 → 无更多通道（None）；
- KS_MINERU_DEEP=0 → 整体跳过（None）。
全部打桩，零真实 GPU/网络。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.ingestion import mineru_adapter as ma


@pytest.fixture()
def stub(monkeypatch):
    """打桩四件事：本地可用性 / 云可用性 / 云提交 / 本地提交；记录调用顺序。"""
    calls: list[str] = []

    def fake_local_available() -> bool:
        return True

    def fake_local_submit(pdf_path, out_dir, **kw):  # noqa: ANN001, ANN003
        calls.append("local")
        return {"output_dir": str(out_dir)}

    def fake_cloud_submit(pdf_path, output_dir):  # noqa: ANN001
        calls.append("cloud")
        return {"output_dir": str(output_dir / "mineru")}

    state = {"cloud_ok": True, "cloud_raises": False, "cloud_returns_none": False,
             "local_raises": False}

    def fake_cloud_available():
        return (state["cloud_ok"], "https://mineru.net")

    def cloud_submit(pdf_path, output_dir):  # noqa: ANN001
        if state["cloud_returns_none"]:
            # 真实契约：网络/超时/HTTP 类失败 → 返回 None（不抛异常）
            calls.append("cloud-none")
            return None
        if state["cloud_raises"]:
            calls.append("cloud-fail")
            raise RuntimeError("cloud boom")
        return fake_cloud_submit(pdf_path, output_dir)

    def local_submit(pdf_path, out_dir, timeout=0):  # noqa: ANN001
        if state["local_raises"]:
            calls.append("local-fail")
            raise RuntimeError("local boom")
        return fake_local_submit(pdf_path, out_dir)

    monkeypatch.setattr(ma, "mineru_available", fake_local_available)
    monkeypatch.setattr(
        "src.core.ingestion.mineru_cloud.mineru_cloud_available", fake_cloud_available)
    monkeypatch.setattr(
        "src.core.ingestion.mineru_cloud.mineru_cloud_submit_and_wait", cloud_submit)
    monkeypatch.setattr(
        "src.core.ingestion.deep_server.deep_server_submit_and_wait", local_submit)
    monkeypatch.delenv("KS_MINERU_DEEP", raising=False)
    monkeypatch.delenv("KS_MINERU_LOCAL", raising=False)
    monkeypatch.delenv("KS_MINERU_CLOUD", raising=False)
    return {"calls": calls, "state": state}


def _run(tmp_path: Path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return ma._mineru_deep_analyze(pdf, tmp_path / "out")


def test_no_cloud_key_goes_local_only(stub, tmp_path):
    """未配置云 Key → 纯本地，绝不触云。"""
    stub["state"]["cloud_ok"] = False
    out = _run(tmp_path)
    assert stub["calls"] == ["local"]
    assert out is not None


def test_cloud_key_prefers_cloud(stub, tmp_path):
    """配置了云 Key → 云优先（本地不被调用）。"""
    out = _run(tmp_path)
    assert stub["calls"] == ["cloud"]
    assert out is not None


def test_cloud_failure_falls_back_to_local(stub, tmp_path):
    """云失败 → 本地兜底。"""
    stub["state"]["cloud_raises"] = True
    out = _run(tmp_path)
    assert stub["calls"] == ["cloud-fail", "local"]
    assert out is not None


def test_cloud_disabled_env_forces_local(stub, tmp_path, monkeypatch):
    """KS_MINERU_CLOUD=0 → 显式禁用云（即使 Key 已配置）。"""
    monkeypatch.setenv("KS_MINERU_CLOUD", "0")
    out = _run(tmp_path)
    assert stub["calls"] == ["local"]
    assert out is not None


def test_cloud_fail_and_local_disabled_returns_none(stub, tmp_path, monkeypatch):
    """KS_MINERU_LOCAL=0 且云失败 → 无更多通道（None），不抛异常。"""
    stub["state"]["cloud_raises"] = True
    monkeypatch.setenv("KS_MINERU_LOCAL", "0")
    assert _run(tmp_path) is None
    assert stub["calls"] == ["cloud-fail"]


def test_deep_disabled_skips_everything(stub, tmp_path, monkeypatch):
    """KS_MINERU_DEEP=0 → 整体跳过（云与本地都不触）。"""
    monkeypatch.setenv("KS_MINERU_DEEP", "0")
    assert _run(tmp_path) is None
    assert stub["calls"] == []


def test_local_failure_after_cloud_failure_returns_none(stub, tmp_path):
    """云失败 + 本地也失败 → None（不抛出，入库继续走文本层降级）。"""
    stub["state"]["cloud_raises"] = True
    stub["state"]["local_raises"] = True
    assert _run(tmp_path) is None
    assert stub["calls"] == ["cloud-fail", "local-fail"]


def test_cloud_silent_none_falls_back_to_local(stub, tmp_path):
    """P0 门禁（verifier F1）：云解析**返回 None**（网络/超时/HTTP 类失败的真实
    契约形态，不抛异常）时，必须继续本地兜底——否则配了云 Key 后任何云侧抖动
    都会让本机可用的 MinerU 完全不跑，扫描版 PDF 无法解析。"""
    stub["state"]["cloud_returns_none"] = True
    out = _run(tmp_path)
    assert stub["calls"] == ["cloud-none", "local"], "云返回 None 必须回落本地"
    assert out is not None


def test_cloud_none_and_local_disabled_returns_none(stub, tmp_path, monkeypatch):
    """云返回 None + KS_MINERU_LOCAL=0 → 无更多通道（None），不抛异常。"""
    stub["state"]["cloud_returns_none"] = True
    monkeypatch.setenv("KS_MINERU_LOCAL", "0")
    assert _run(tmp_path) is None
    assert stub["calls"] == ["cloud-none"]


def test_cloud_and_local_both_disabled_returns_none(stub, tmp_path, monkeypatch):
    """KS_MINERU_CLOUD=0 + KS_MINERU_LOCAL=0 → 两通道皆关（calls 为空、返回 None）。"""
    monkeypatch.setenv("KS_MINERU_CLOUD", "0")
    monkeypatch.setenv("KS_MINERU_LOCAL", "0")
    assert _run(tmp_path) is None
    assert stub["calls"] == []
