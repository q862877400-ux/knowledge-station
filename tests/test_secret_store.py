# -*- coding: utf-8 -*-
"""引擎侧密钥存储（`src/core/settings/secret_store.py`）单测。

核心命题只有一条：**密钥存在引擎自己的加密文件里，值不落明文、系统层零写入**。
所以除了功能（往返/原子/并发/损坏），这里还有几条"结构性"断言：
- 文件里**不出现明文**（直接读文件文本搜 Key）；
- 写入路径**不碰 winreg**（把 winreg 换成"一碰就炸"的假模块，写入仍必须成功）；
- 存储路径与 `config.data_dir` **规则一致**（防两条路径规则漂移）。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from src.core.settings import secret_store as ss


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """把存储重定向到临时目录（KS_DATA_DIR 是 config 与 secret_store 共用的开关）。"""
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import reset_settings
    reset_settings()
    yield tmp_path
    reset_settings()


class ExplodingWinreg:
    """任何属性访问都抛错：证明某条代码路径**一行 winreg 都没碰**。"""

    def __getattr__(self, item):
        raise AssertionError(f"不该访问 winreg.{item}（系统层零写入是硬约束）")


# ---------- 路径 ----------
def test_store_path_matches_config_data_dir(tmp_path, monkeypatch):
    """存储路径规则必须与 config._default_data_dir 一致（两份规则，一条断言钉住）。"""
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    from src.core.config import _default_data_dir
    assert ss.store_path() == _default_data_dir() / "secrets.json"
    assert ss.store_path() == tmp_path / "secrets.json"


def test_store_path_matches_config_WITHOUT_override(monkeypatch):
    """⚠ **缺口钉子（2026-10-18 补）**：**不设 `KS_DATA_DIR`** 时两边也必须一致。

    ## 为什么必须补这一条

    上面那条只测了"**设了** `KS_DATA_DIR`"的情形 —— 那种情形下两边都走覆盖值，
    **恒等**，所以它对"默认值漂移"**零分辨力**。

    实测后果（就是这条缺口放过去的）：业主令把 `config` 的默认值改成**包内**
    `<仓>/var/data` 之后，`secret_store` 里**重抄的**那份规则还指着
    `%APPDATA%\\KnowledgeStation` ⇒ **库落包内、密钥落包外**，而那条测试**照样绿**。
    现在 `secret_store` 改成**直接调 config 那一份**（不再抄），本钉子保证它别抄回去。
    """
    monkeypatch.delenv("KS_DATA_DIR", raising=False)
    from src.core.config import _default_data_dir
    assert ss.store_path() == _default_data_dir() / "secrets.json"
    # 反向钉子：默认必须落在**包内**（不含 AppData），防有人把规则抄回包外
    assert "AppData" not in str(ss.store_path()), str(ss.store_path())


# ---------- 加密往返 ----------
def test_protect_roundtrip_and_no_plaintext():
    cipher = ss.protect("sk-secret-marker-1234567890")
    assert "sk-secret-marker-1234567890" not in cipher
    assert ss.unprotect(cipher) == "sk-secret-marker-1234567890"


def test_unprotect_wrong_entropy_returns_empty():
    """别的程序（换 entropy）拿到密文也解不开 —— 但我们得**降级**而不是崩。"""
    cipher = ss.protect("x", entropy=b"another-app")
    assert ss.unprotect(cipher) == ""


def test_unprotect_garbage_returns_empty():
    assert ss.unprotect("not-base64!!") == ""
    assert ss.unprotect("") == ""
    assert ss.unprotect("QUJD") == ""          # 合法 base64 但不是 DPAPI 密文


def test_empty_plaintext_roundtrip():
    assert ss.unprotect(ss.protect("")) == ""


def test_protect_rejects_non_str():
    with pytest.raises(ss.SecretStoreError):
        ss.protect(b"bytes-not-str")           # type: ignore[arg-type]


def test_oversize_value_rejected(data_dir):
    with pytest.raises(ss.SecretStoreError):
        ss.write_values({"KS_LLM_API_KEY": "x" * (ss.MAX_VALUE_LEN + 1)})
    assert not ss.has_value("KS_LLM_API_KEY")


# ---------- 文件内容 ----------
def test_file_contains_names_but_no_plaintext(data_dir):
    ss.write_values({"KS_LLM_API_KEY": "sk-file-marker-abcd", "KS_LLM_BASE_URL": "https://x.example"})
    raw = (data_dir / "secrets.json").read_text(encoding="utf-8")
    assert "sk-file-marker-abcd" not in raw
    assert "x.example" not in raw              # base_url 也加密（可能带 user:pass@）
    assert "KS_LLM_API_KEY" in raw             # 只有名字是明文
    payload = json.loads(raw)
    assert payload["scheme"] == "dpapi-user"
    assert set(payload["values"]) == {"KS_LLM_API_KEY", "KS_LLM_BASE_URL"}


def test_write_is_merge_and_delete(data_dir):
    ss.write_values({"KS_LLM_API_KEY": "k1", "KS_LLM_BASE_URL": "https://a"})
    ss.write_values({"KS_MINERU_CLOUD_API_KEY": "k2"})
    assert ss.read_value("KS_LLM_API_KEY") == "k1"          # 合并不丢
    ss.write_values({"KS_LLM_BASE_URL": None})               # None = 删除
    assert ss.read_value("KS_LLM_BASE_URL") == ""
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "k2"
    assert "KS_LLM_BASE_URL" not in ss.stored_names()


def test_write_zero_values_is_noop(data_dir):
    ss.write_values({})
    assert not (data_dir / "secrets.json").exists()


def test_no_temp_files_left_behind(data_dir):
    ss.write_values({"KS_LLM_API_KEY": "k"})
    leftovers = [p.name for p in data_dir.iterdir() if ".tmp" in p.name or p.name.endswith(".lock")]
    assert leftovers == []


# ---------- 损坏与权限（失败模式） ----------
def test_corrupt_file_degrades_to_empty(data_dir):
    (data_dir / "secrets.json").write_text("{not json at all", encoding="utf-8")
    assert ss.read_value("KS_LLM_API_KEY") == ""
    assert ss.stored_names() == []
    # 而且还能恢复写（坏文件不该永久卡死）
    ss.write_values({"KS_LLM_API_KEY": "fresh"})
    assert ss.read_value("KS_LLM_API_KEY") == "fresh"


def test_wrong_shape_json_degrades(data_dir):
    (data_dir / "secrets.json").write_text('["a", "b"]', encoding="utf-8")
    assert ss.read_value("KS_LLM_API_KEY") == ""


def test_unwritable_dir_raises_on_write_but_read_still_safe(tmp_path, monkeypatch):
    """写失败必须**吵**（不能静默丢 Key）；读失败必须**静**（不能把引擎打死）。"""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("i am a file", encoding="utf-8")
    monkeypatch.setenv("KS_DATA_DIR", str(blocker / "sub"))
    with pytest.raises(Exception):
        ss.write_values({"KS_LLM_API_KEY": "k"})
    assert ss.read_value("KS_LLM_API_KEY") == ""


# ---------- 并发 ----------
def test_concurrent_writes_do_not_lose_values(data_dir):
    """两个线程各写一个通道名：锁必须让两个名字都留下（不能后写覆盖前写）。"""
    errors: list[Exception] = []

    def worker(name: str) -> None:
        try:
            ss.write_values({name: f"value-of-{name}"})
        except Exception as e:                      # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=worker, args=(f"KS_THREAD_{i}",)) for i in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errors == []
    names = ss.stored_names()
    for i in range(6):
        assert f"KS_THREAD_{i}" in names, names
        assert ss.read_value(f"KS_THREAD_{i}") == f"value-of-KS_THREAD_{i}"


def test_stale_lock_is_reclaimed(data_dir):
    """崩溃遗留的锁文件不能永久卡死写入。"""
    path = ss.store_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    lock.write_text("999999", encoding="utf-8")
    old = time.time() - (ss._LOCK_STALE_S + 5)
    import os
    os.utime(lock, (old, old))
    started = time.monotonic()
    ss.write_values({"KS_LLM_API_KEY": "after-stale-lock"})
    assert time.monotonic() - started < ss._LOCK_RETRY_S
    assert ss.read_value("KS_LLM_API_KEY") == "after-stale-lock"


# ---------- 结构性：写入路径不碰系统层 ----------
def test_write_path_never_touches_winreg(monkeypatch, data_dir):
    """把 winreg 换成"一碰就炸"，写入仍然成功 ⇒ 写路径一行 winreg 都没有。"""
    import sys
    monkeypatch.setitem(sys.modules, "winreg", ExplodingWinreg())
    monkeypatch.setattr("src.core.settings.api_credentials.winreg", ExplodingWinreg())
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-no-registry", base_url="https://x")
    assert ss.read_value("KS_LLM_API_KEY") == "sk-no-registry"
    assert ss.read_value("KS_LLM_BASE_URL") == "https://x"
