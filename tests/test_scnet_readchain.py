# -*- coding: utf-8 -*-
"""std_bulk_import.py 的 SCNET 读链测试（整改批 4，问题清单 #5）。

契约（2026-09-12 批4 改造后）：
1. 读链顺序：进程环境 > **引擎加密存储**（SCNET_OCR_API_KEY / KS_SCNET_OCR_API_KEY）
   > HKCU\Environment / HKLM（只读覆盖链）；
2. 绝不把值**打印**出来（只报来源作用域）；
3. 注册表分支只读不写（结构性守卫已禁写，这里测行为）；
4. 全链找不到 → 返回 False，如实报告。

加载方式：AST 提取真实源文件里的 `_ensure_scnet_key` 函数体编译执行——
**测的是真源码**，不是复制粘贴副本；同时避开脚本模块级的
`sys.stdout = TextIOWrapper(...)`（它会在 pytest capsys 下关掉捕获流）。

隔离：KS_DATA_DIR → tmp（加密存储）；winreg → 假 winreg；真实环境零接触。
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "std_bulk_import.py"


def _load_ensure_scnet_key() -> "callable":
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    node = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_ensure_scnet_key"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ns: dict = {"os": os}
    exec(compile(module, str(SCRIPT), "exec"), ns)
    return ns["_ensure_scnet_key"]


@pytest.fixture()
def ensure_key(monkeypatch, tmp_path):
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SCNET_OCR_API_KEY", raising=False)
    monkeypatch.delenv("KS_SCNET_OCR_API_KEY", raising=False)
    fn = _load_ensure_scnet_key()
    yield fn
    os.environ.pop("SCNET_OCR_API_KEY", None)
    os.environ.pop("KS_SCNET_OCR_API_KEY", None)


class _FakeKey:
    def __init__(self, store):
        self._store = store

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def QueryValueEx(self, name):
        if name not in self._store:
            raise FileNotFoundError(name)
        return self._store[name], 1


class FakeWinreg:
    HKEY_CURRENT_USER = 1
    HKEY_LOCAL_MACHINE = 2
    KEY_WOW64_64KEY = 0x100
    KEY_READ = 0x1

    def __init__(self, user_store=None, machine_store=None):
        self.user = dict(user_store or {})
        self.machine = dict(machine_store or {})

    def QueryValueEx(self, key, name):
        return key.QueryValueEx(name)

    def OpenKey(self, hive, path, reserved=0, access=0):
        if hive == self.HKEY_CURRENT_USER and path == r"Environment":
            return _FakeKey(self.user)
        if hive == self.HKEY_LOCAL_MACHINE:
            return _FakeKey(self.machine)
        raise OSError(path)


def _use_fake_winreg(monkeypatch, **stores):
    fw = FakeWinreg(**stores)
    monkeypatch.setitem(sys.modules, "winreg", fw)


def test_reads_from_encrypted_store_first(ensure_key, monkeypatch, capsys):
    from src.core.settings import secret_store
    secret_store.write_values({"SCNET_OCR_API_KEY": "sk-from-store"})
    _use_fake_winreg(monkeypatch, user_store={"SCNET_OCR_API_KEY": "sk-from-registry"})
    assert ensure_key() is True
    assert os.environ["SCNET_OCR_API_KEY"] == "sk-from-store"
    out = capsys.readouterr().out
    assert "加密存储" in out
    assert "sk-from-store" not in out            # 值绝不回显


def test_env_var_wins_without_store(ensure_key, monkeypatch):
    monkeypatch.setenv("SCNET_OCR_API_KEY", "sk-from-env")
    assert ensure_key() is True       # 直接短路，不碰存储/注册表


def test_registry_fallback_still_works(ensure_key, monkeypatch, capsys):
    """加密存储没有 → 注册表覆盖链仍可用（只读，为 CI/老 setx 值保底）。"""
    _use_fake_winreg(monkeypatch, user_store={"SCNET_OCR_API_KEY": "sk-from-registry"})
    assert ensure_key() is True
    assert os.environ["SCNET_OCR_API_KEY"] == "sk-from-registry"
    out = capsys.readouterr().out
    assert "User 作用域" in out
    assert "sk-from-registry" not in out


def test_missing_everywhere_returns_false(ensure_key, monkeypatch):
    _use_fake_winreg(monkeypatch)
    assert ensure_key() is False


def test_ks_namespace_alias_in_store(ensure_key, monkeypatch):
    """加密存储里若用的是 KS_ 命名空间名，同样能取到（并存注入）。"""
    from src.core.settings import secret_store
    secret_store.write_values({"KS_SCNET_OCR_API_KEY": "sk-ks-namespace"})
    _use_fake_winreg(monkeypatch)
    assert ensure_key() is True
    assert os.environ["KS_SCNET_OCR_API_KEY"] == "sk-ks-namespace"
