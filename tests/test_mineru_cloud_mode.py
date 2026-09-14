r"""MinerU 云解析「模式」设置项契约测试（2026-09-15 新增）。

用户要求：设置里除了填 KEY 还能**选模式**。官方 v4 契约（mineru.net 文档
「请求体参数说明」）：`model_version` 三选一 pipeline（默认）/ vlm /
MinerU-HTML；非 HTML 文件可选 pipeline 或 vlm。

本测试锁定四件事：
1. 读值归一（大小写不敏感；非法值回落 pipeline，不让脏值进请求体）
2. 写入校验（非法值抛 InvalidModelVersion；llm 通道不许带 model_version）
3. 状态暴露（get_status 给 model_version + model_versions，前端不硬编码契约）
4. **请求体真带 model_version**（monkeypatch httpx 捕获 body）——这是本改动的
   唯一目的：让云调用真的走 vlm
"""
from __future__ import annotations

import pytest

from src.core import config as cfg
from src.core.settings import api_credentials as cred


@pytest.fixture()
def clean_env(monkeypatch):
    """清掉 env 覆盖，保证读写只看存储。"""
    for name in ("KS_MINERU_CLOUD_MODEL_VERSION", "KS_MINERU_CLOUD_API_KEY",
                 "KS_MINERU_CLOUD_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    yield


class TestReadNormalization:
    def test_default_is_pipeline(self, clean_env, tmp_path, monkeypatch):
        monkeypatch.setattr(cfg, "_default_data_dir", lambda: tmp_path)
        assert cfg._read_mineru_model_version() == "pipeline"

    def test_case_insensitive(self, clean_env, monkeypatch):
        monkeypatch.setenv("KS_MINERU_CLOUD_MODEL_VERSION", "VLM")
        assert cfg._read_mineru_model_version() == "vlm"

    def test_illegal_falls_back(self, clean_env, monkeypatch):
        monkeypatch.setenv("KS_MINERU_CLOUD_MODEL_VERSION", "vlm-x")
        assert cfg._read_mineru_model_version() == "pipeline"

    def test_vm_html_kept(self, clean_env, monkeypatch):
        monkeypatch.setenv("KS_MINERU_CLOUD_MODEL_VERSION", "MinerU-HTML")
        assert cfg._read_mineru_model_version() == "MinerU-HTML"


class TestWriteValidation:
    def test_illegal_raises(self):
        with pytest.raises(cred.InvalidModelVersion):
            cred.set_credential("mineru_cloud", model_version="turbo")

    def test_llm_channel_rejects_mode(self):
        with pytest.raises(cred.UnknownChannel):
            cred.set_credential("llm", model_version="vlm")

    def test_unknown_channel_rejected(self):
        with pytest.raises(cred.UnknownChannel):
            cred.set_credential("nope", api_key="x")


class TestStatusExposure:
    def test_status_has_mode_and_choices(self):
        st = cred.get_status()
        assert st["mineru_cloud"]["model_version"] in cfg.MINERU_CLOUD_MODEL_VERSIONS
        assert st["mineru_cloud"]["model_versions"] == list(cfg.MINERU_CLOUD_MODEL_VERSIONS)
        # 非密值可回显；Key 仍不回显
        assert "api_key" not in st["mineru_cloud"]


class TestRequestBody:
    """本改动的核心断言：云请求体真的带上了所选模式。"""

    def _capture(self, monkeypatch, mode: str) -> dict:
        import httpx
        captured: dict = {}

        class _Resp:
            status_code = 200
            text = "{}"

            def json(self):
                return {"code": 0, "data": {"batch_id": "b" * 24,
                                            "file_urls": ["https://up.example/x"]}}

            def raise_for_status(self):
                return None

        def _fake_post(url, headers=None, json=None, timeout=None, **kw):
            captured["url"] = url
            captured["body"] = json
            return _Resp()

        monkeypatch.setattr(httpx, "post", _fake_post)
        monkeypatch.setattr("src.core.ingestion.mineru_cloud._resolve_settings",
                            lambda: ("fake-key", "https://mineru.net"))
        monkeypatch.setattr("src.core.ingestion.mineru_cloud._model_version",
                            lambda: mode)
        from src.core.ingestion import mineru_cloud as mc
        mc._apply_upload_url("fake-key", "https://mineru.net", "demo.pdf")
        return captured

    def test_upload_url_body_carries_vlm(self, monkeypatch):
        cap = self._capture(monkeypatch, "vlm")
        assert cap["body"]["model_version"] == "vlm"
        assert cap["body"]["files"][0]["name"] == "demo.pdf"
        assert cap["body"]["language"] == "ch"

    def test_upload_url_body_carries_pipeline(self, monkeypatch):
        cap = self._capture(monkeypatch, "pipeline")
        assert cap["body"]["model_version"] == "pipeline"

    def test_model_version_helper_reads_settings(self, monkeypatch):
        from src.core.ingestion import mineru_cloud as mc

        class _S:
            mineru_cloud_model_version = "vlm"

        monkeypatch.setattr(cfg, "get_settings", lambda: _S())
        assert mc._model_version() == "vlm"

    def test_model_version_helper_sanitizes(self, monkeypatch):
        from src.core.ingestion import mineru_cloud as mc

        class _S:
            mineru_cloud_model_version = "garbage"

        monkeypatch.setattr(cfg, "get_settings", lambda: _S())
        assert mc._model_version() == "pipeline"
