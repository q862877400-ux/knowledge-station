# -*- coding: utf-8 -*-
"""`scripts/ks-credentials-migrate.py` 单测（破坏性工具，必须测）。

2026-09-11「不要动系统层」改造后，这个脚本的职责变成：
**把系统层（HKCU\\Environment）里的旧条目搬进引擎加密存储，然后（可选）清掉系统层**。
契约：
1. 默认 = 只打印计划、**零写入**（存储与注册表都不动）；
2. `--clean-system` 缺 `--apply` 拒绝（返回 2）；`--force` 缺 `--clean-system` 也拒绝；
3. `--apply` 只写加密存储、默认保留系统层条目（可回退）；
4. `--apply --clean-system` **先核对再删**：只有读回一致的名字才删；
5. 存储里已有值时绝不覆盖；冲突时默认不删系统层那份旧值（要 `--force`）。

隔离：`KS_DATA_DIR` → tmp（加密存储），HKCU → 假 winreg。真实环境零接触。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from src.core.config import reset_settings
from src.core.settings import secret_store as ss

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "ks-credentials-migrate.py"


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

    def __init__(self, seed: dict | None = None):
        self.store: dict[str, str] = dict(seed or {})

    def CreateKeyEx(self, hive, path, reserved, access):
        return _FakeKey(self.store)

    def OpenKey(self, hive, path):
        return _FakeKey(self.store)

    def QueryValueEx(self, key, name):
        store = key._store if isinstance(key, _FakeKey) else self.store
        if name not in store:
            raise FileNotFoundError(name)
        return store[name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, type_, value):
        key.SetValueEx(name, reserved, type_, value)

    def DeleteValue(self, key, name):
        key.DeleteValue(name)


@pytest.fixture()
def fake_reg(monkeypatch):
    fw = FakeWinreg()
    monkeypatch.setattr("src.core.settings.api_credentials.winreg", fw)
    monkeypatch.setitem(sys.modules, "winreg", fw)
    return fw


@pytest.fixture(autouse=True)
def store_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    reset_settings()
    yield tmp_path
    reset_settings()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for n in ("KS_LLM_API_KEY", "KS_LLM_BASE_URL", "KS_LLM_MODEL",
              "KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_BASE_URL",
              "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(n, raising=False)
    yield
    reset_settings()


@pytest.fixture()
def migrate():
    spec = importlib.util.spec_from_file_location("ks_credentials_migrate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ks_credentials_migrate"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ---------- 只读默认 ----------
def test_dry_run_writes_nothing(migrate, fake_reg, store_dir, capsys):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    before = dict(fake_reg.store)
    assert migrate.main([]) == 0
    out = capsys.readouterr().out
    assert fake_reg.store == before                      # 注册表零写入
    assert not (store_dir / "secrets.json").exists()     # 存储零写入
    assert "sk-legacy" not in out                        # 绝不回显值
    assert "DSH" in out                                  # 收尾提示在（重启 DSH）


def test_nothing_to_migrate_is_clean_noop(migrate, fake_reg, store_dir, capsys):
    assert migrate.main([]) == 0
    assert "无可搬条目" in capsys.readouterr().out
    assert fake_reg.store == {} and not (store_dir / "secrets.json").exists()


def test_clean_system_without_apply_refused(migrate, fake_reg, capsys):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    assert migrate.main(["--clean-system"]) == 2
    assert fake_reg.store == {"DEEPSEEK_API_KEY": "sk-legacy"}
    assert "拒绝" in capsys.readouterr().out


def test_force_without_clean_system_refused(migrate, fake_reg):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    assert migrate.main(["--apply", "--force"]) == 2
    assert fake_reg.store == {"DEEPSEEK_API_KEY": "sk-legacy"}


# ---------- --apply ----------
def test_apply_migrates_into_encrypted_store_and_keeps_system_layer(migrate, fake_reg, capsys):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-cloud"
    assert migrate.main(["--apply"]) == 0
    out = capsys.readouterr().out
    assert ss.read_value("KS_LLM_API_KEY") == "sk-legacy"          # 改名搬家
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-cloud"  # 同名搬家
    assert fake_reg.store["DEEPSEEK_API_KEY"] == "sk-legacy"        # 默认保留（可回退）
    assert "sk-legacy" not in out and "tok-cloud" not in out


def test_apply_writes_no_plaintext(migrate, fake_reg, store_dir):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-plaintext-marker"
    assert migrate.main(["--apply"]) == 0
    raw = (store_dir / "secrets.json").read_text(encoding="utf-8")
    assert "sk-plaintext-marker" not in raw


# ---------- --apply --clean-system ----------
def test_clean_system_deletes_verified_entries(migrate, fake_reg, capsys):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-cloud"
    assert migrate.main(["--apply", "--clean-system"]) == 0
    out = capsys.readouterr().out
    assert "DEEPSEEK_API_KEY" not in fake_reg.store
    assert "KS_MINERU_CLOUD_API_KEY" not in fake_reg.store
    assert ss.read_value("KS_LLM_API_KEY") == "sk-legacy"
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-cloud"
    assert "重启 DSH 宿主" in out                       # 删完必须提示重启 DSH


def test_clean_system_two_pass_deletes_previously_migrated(migrate, fake_reg, capsys):
    """批2 真实踩到的回归：先 --apply（第一遍搬完），再 --apply --clean-system（第二遍）
    必须仍能删除系统层——否则 verify-before-delete 的 verified 集合在第二遍为空、
    删除段静默空转（真机上第一遍 --clean-system 删了 0 条）。
    """
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-cloud"
    assert migrate.main(["--apply"]) == 0                      # 第一遍：只搬
    capsys.readouterr()
    assert migrate.main(["--apply", "--clean-system"]) == 0    # 第二遍：搬+删
    out = capsys.readouterr().out
    assert "DEEPSEEK_API_KEY" not in fake_reg.store            # 旧名（改名迁移的源）
    assert "KS_MINERU_CLOUD_API_KEY" not in fake_reg.store     # 同名迁移的源
    assert ss.read_value("KS_LLM_API_KEY") == "sk-legacy"      # 加密存储仍是权威
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-cloud"
    assert "已从系统层删除" in out
    assert "sk-legacy" not in out and "tok-cloud" not in out


def test_clean_system_reports_env_only_entries(migrate, fake_reg, monkeypatch, capsys):
    """只在进程环境变量里的条目删不掉 —— 必须如实上报，不谎报已清理。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-only")
    assert migrate.main(["--apply", "--clean-system"]) == 0
    out = capsys.readouterr().out
    assert "本脚本删不掉" in out
    assert "DEEPSEEK_API_KEY" in out                     # 列在 env_untouched 里
    assert "sk-env-only" not in out


def test_clean_system_never_deletes_when_store_has_other_value(migrate, fake_reg, capsys):
    """verifier P1 的脚本层回归：存储里已有新 Key → 不覆盖，且不删冲突的系统层旧值。"""
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-new-fresh")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-old-stale"
    assert migrate.main(["--apply", "--clean-system"]) == 0
    out = capsys.readouterr().out
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new-fresh"
    assert fake_reg.store["DEEPSEEK_API_KEY"] == "sk-old-stale"   # 唯一样本保住
    assert "保持不动" in out
    assert "sk-new-fresh" not in out and "sk-old-stale" not in out


def test_force_discards_conflicting_system_layer_value(migrate, fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-new-fresh")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-old-stale"
    assert migrate.main(["--apply", "--clean-system", "--force"]) == 0
    assert "DEEPSEEK_API_KEY" not in fake_reg.store
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new-fresh"


# ---------- 脚本本身的守卫 ----------
def test_import_does_not_run_main(migrate, fake_reg, store_dir):
    assert fake_reg.store == {}
    assert not (store_dir / "secrets.json").exists()
    assert hasattr(migrate, "main")


def test_script_documents_dsh_restart_and_rollback():
    """文档级守卫：这几句不许被删（verifier 指出旧版全仓库都没写"必须重启 DSH"）。"""
    text = SCRIPT.read_text(encoding="utf-8")
    assert "重启 DSH 宿主进程" in text
    assert "launch-environment" in text        # 指向 DSH 侧冻结环境快照的依据
    assert "先核对再删" in text
    assert "回滚" in text and "备份" in text
