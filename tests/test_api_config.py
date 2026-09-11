# -*- coding: utf-8 -*-
"""设置→API 配置（云解析/LLM 双通道）单测：注册表写入注入、脱敏、未知通道拒绝。

红线自检：任何断言不允许出现「状态响应包含明文 Key」。
"""
from __future__ import annotations

import sys

import pytest

from src.core.config import get_settings, reset_settings

# ---------- Fake winreg（隔离真实 HKCU，防污染开发机环境）----------
class _FakeKey:
    def __init__(self, store: dict):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def SetValueEx(self, name, reserved, type_, value):
        self._store[name] = str(value)

    def DeleteValue(self, name):
        self._store.pop(name, None)


class FakeWinreg:
    KEY_SET_VALUE = 0x2
    KEY_WOW64_64KEY = 0x100
    REG_SZ = 1
    HKEY_CURRENT_USER = -2147483647

    def __init__(self):
        self.store: dict[str, str] = {}

    def CreateKeyEx(self, hive, path, reserved, access):
        return _FakeKey(self.store)

    # 真实 winreg 的模块级调用风格：第一个参数是句柄
    def SetValueEx(self, key, name, reserved, type_, value):
        key.SetValueEx(name, reserved, type_, value)

    def DeleteValue(self, key, name):
        key.DeleteValue(name)


@pytest.fixture()
def fake_reg(monkeypatch):
    fw = FakeWinreg()
    monkeypatch.setattr("src.core.settings.api_credentials.winreg", fw)
    # 同时隔离 sys.modules["winreg"]：src.core.config 是在**函数内部** `import winreg` 的，
    # 只打 api_credentials 的模块属性挡不住它 → 未设 env 的用例会读真实 HKCU
    # （并顺带在真实 %APPDATA%\KnowledgeStation 上 ensure_dirs）。verifier 2026-09-11 指出。
    monkeypatch.setitem(sys.modules, "winreg", fw)
    return fw


@pytest.fixture(autouse=True)
def store_dir(tmp_path, monkeypatch):
    """把加密存储重定向到 tmp（2026-09-11 起凭据写 `secret_store`，不再是注册表）。"""
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    reset_settings()
    yield tmp_path
    reset_settings()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """每测清理所有相关变量与设置缓存。"""
    for n in ("KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_BASE_URL",
              "KS_LLM_API_KEY", "KS_LLM_BASE_URL", "KS_LLM_MODEL",
              "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(n, raising=False)
    yield
    reset_settings()


# ---------- 写入语义（2026-09-11：写引擎加密存储，系统层零写入）----------
def test_set_credential_writes_both_names(fake_reg):
    from src.core.settings import secret_store as ss
    from src.core.settings.api_credentials import set_credential
    set_credential("mineru_cloud", api_key="tok-test123",
                   base_url="https://cloud.example")
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-test123"
    assert ss.read_value("KS_MINERU_CLOUD_BASE_URL") == "https://cloud.example"
    assert fake_reg.store == {}, "不许再写系统层"


def test_set_credential_skips_blank_and_dash_clears(fake_reg):
    from src.core.settings import secret_store as ss
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-l", base_url="https://x")
    assert ss.read_value("KS_LLM_BASE_URL") == "https://x"
    set_credential("llm", api_key="")           # 空串=跳过不覆盖
    set_credential("llm", base_url="-")         # "-"=显式删除恢复默认
    assert ss.read_value("KS_LLM_API_KEY") == "sk-l"
    assert ss.read_value("KS_LLM_BASE_URL") == ""
    assert fake_reg.store == {}


def test_cloud_dash_clears_base_url(fake_reg):
    from src.core.settings import secret_store as ss
    from src.core.settings.api_credentials import set_credential
    set_credential("mineru_cloud", base_url="-")
    assert ss.read_value("KS_MINERU_CLOUD_BASE_URL") == ""
    assert fake_reg.store == {}


def test_unknown_channel_rejected():
    from src.core.settings.api_credentials import UnknownChannel, set_credential
    with pytest.raises(UnknownChannel):
        set_credential("tts", api_key="x")


# ---------- 脱敏 ----------
def test_status_never_leaks_key(monkeypatch):
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok-secret-leak-marker")
    # 旧名仍在用 → 只读回退必须仍然生效（2026-09-11 兼容断言）
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-llm-leak-marker")
    from src.core.settings.api_credentials import get_status
    st = get_status()
    dumped = repr(st)
    assert "tok-secret-leak-marker" not in dumped
    assert "sk-llm-leak-marker" not in dumped
    assert st["mineru_cloud"]["configured"] is True
    assert st["llm"]["configured"] is True
    assert isinstance(st["mineru_cloud"]["base_url"], str)


def test_status_accepts_namespaced_llm_key(monkeypatch):
    """新名（本机保存后的形态）必须让 configured 为真。"""
    monkeypatch.setenv("KS_LLM_API_KEY", "sk-namespaced-leak-marker")
    from src.core.settings.api_credentials import get_status
    st = get_status()
    assert "sk-namespaced-leak-marker" not in repr(st)
    assert st["llm"]["configured"] is True


# ---------- config 解析链 ----------
def test_settings_reads_cloud_key_from_env(monkeypatch):
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok-env")
    reset_settings()
    assert get_settings().mineru_cloud_api_key == "tok-env"


def test_settings_cloud_base_url_default():
    reset_settings()
    assert get_settings().mineru_cloud_base_url == "https://mineru.net"
