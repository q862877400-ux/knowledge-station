# -*- coding: utf-8 -*-
"""凭据存储的结构守卫与读取链单测（2026-09-11 「不要动系统层」改造后）。

背景（真实事故）：引擎曾把 API Key 写进 **Windows 系统层** `HKCU\\Environment`
（LLM 通道还是**裸全局名** `DEEPSEEK_API_KEY`）。而 DSH 把继承来的进程环境变量当
最高优先级且只读的凭据来源 → KS 一保存 Key，DSH 模型设置页的密钥输入框就被置灰。
业主裁决：「需要配置 key 那就在插件或者 DSH 内部配置，**不要动系统层**」。

现在锁住四件事：
1. **结构**：任何通道的变量名都必须 `KS_` 前缀，且旧名不再是写入名；
2. **写入**：保存只写**引擎加密存储**，写路径**一行 winreg 都不碰**；
3. **读取**：`KS_*` 环境变量覆盖 → 加密存储 → 旧系统层只读兼容 → 默认值；
4. **迁移**：搬进存储要**先核对再删**，冲突默认不覆盖、不删源，且绝不回显 Key 值。

隔离：`KS_DATA_DIR` 被整个模块重定向到 tmp（**不可能碰到真实 %APPDATA%**），
HKCU 一律用假 winreg（不会碰真实注册表）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

from src.core.config import get_settings, reset_settings
from src.core.settings import secret_store as ss

REPO = Path(__file__).resolve().parents[1]

LEGACY_NAMES = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")
#: 允许「提及」旧名的**代码**文件（必须逐个人工复核过用途；新增引用会红）
LEGACY_ALLOWED_FILES = {
    "src/core/config.py",                    # 只读回退读取链（deprecated 层）
    "src/core/settings/api_credentials.py",  # 只读回退 + 迁移源（绝不写入系统层）
    "src/core/llm/ks_answer.py",             # 仅「未配置」报错文案
    "src/core/llm/deepseek_client.py",       # 仅「未配置」报错文案
    "src/renderer/ApiConfigPanel.tsx",       # 旧 GUI 输入框占位提示
    "scripts/ks-credentials-migrate.py",     # 迁移工具（打印变量名，不回显值）
    "scripts/ks-credential-readers-scan.py",  # 读者排查工具（批 1b：检查旧名残留，只记存在性不记值）
    "scripts/make_handoff_zip.py",           # 交接清单文档字符串
    "scripts/_dl_diag.py",                   # 只读探测存在性
    "plugin/scripts/verify-answer.mjs",      # 假引擎桩里的报错文案
}
#: 扫描射程（verifier mut9：只扫 src/ 会漏掉脚本层的裸名写入）
CODE_SUFFIXES = (".py", ".ps1", ".bat", ".cmd", ".mjs", ".js", ".ts", ".tsx")
EXCLUDE_DIR_PARTS = {
    "node_modules", ".venv", "dist", "dist-electron", "var", "backups",
    ".zcode", ".pytest_cache", ".mimosa", "wheels_local", "_channel_probe",
    "tests",  # 测试自身会合法地拼这些字符串（假注册表 fixture、白名单常量）
}
_MAX_SCAN_BYTES = 1_500_000   # 跳过打包产物（client.js ~1.1MB 之类）


def _iter_code_files():
    for path in REPO.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
            continue
        rel = path.relative_to(REPO)
        if set(rel.parts[:-1]) & EXCLUDE_DIR_PARTS:
            continue
        try:
            if path.stat().st_size > _MAX_SCAN_BYTES:
                continue
        except OSError:
            continue
        yield path, rel.as_posix()


# ---------- 假注册表（隔离真实 HKCU）----------
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
    """够 api_credentials（模块属性替换）与 config（sys.modules 替换）两处用。"""

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
    """假 HKCU（读旧系统层 / 迁移源用）。"""
    fw = FakeWinreg()
    monkeypatch.setattr("src.core.settings.api_credentials.winreg", fw)
    monkeypatch.setitem(sys.modules, "winreg", fw)
    return fw


@pytest.fixture(autouse=True)
def store_dir(tmp_path, monkeypatch):
    """把加密存储重定向到 tmp —— 本文件任何测试都碰不到真实 %APPDATA%。"""
    monkeypatch.setenv("KS_DATA_DIR", str(tmp_path))
    reset_settings()
    yield tmp_path
    reset_settings()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for n in ("KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_BASE_URL",
              "KS_LLM_API_KEY", "KS_LLM_BASE_URL", "KS_LLM_MODEL",
              *LEGACY_NAMES):
        monkeypatch.delenv(n, raising=False)
    yield
    reset_settings()


# ---------- 1. 结构守卫 ----------
def test_every_channel_name_is_namespaced():
    """所有通道的所有变量名必须带 KS_ 前缀（这次事故的形态就是漏了前缀）。"""
    from src.core.settings.api_credentials import CHANNEL_VARS
    bad = [n for pair in CHANNEL_VARS.values() for n in pair
           if not n.startswith("KS_")]
    assert bad == [], f"通道变量名必须 KS_ 前缀，发现裸名: {bad}"


def test_legacy_names_disjoint_from_write_names():
    """旧名不能同时是写入名（否则等于一边叫它旧、一边继续用它）。"""
    from src.core.settings.api_credentials import CHANNEL_VARS, LEGACY_CHANNEL_VARS
    writes = {n for pair in CHANNEL_VARS.values() for n in pair}
    legacies = {n for pair in LEGACY_CHANNEL_VARS.values() for n in pair}
    assert writes & legacies == set()


def test_llm_reader_order_namespaced_first():
    from src.core.config import _LLM_KEY_VARS, _LLM_MODEL_VARS, _LLM_URL_VARS
    assert _LLM_KEY_VARS[0] == "KS_LLM_API_KEY"
    assert _LLM_URL_VARS[0] == "KS_LLM_BASE_URL"
    assert _LLM_MODEL_VARS[0] == "KS_LLM_MODEL"
    assert _LLM_KEY_VARS[-1] == "DEEPSEEK_API_KEY"     # 旧名只作兜底
    assert _LLM_URL_VARS[-1] == "DEEPSEEK_BASE_URL"


def test_no_source_writes_a_legacy_name_or_registry():
    """源码级扫描：**全仓库代码**里没有任何文件把旧全局名/注册表当写入目标。

    verifier mut9 的教训：原版只扫 `src/*.py`，于是把
    `os.environ["DEEPSEEK_API_KEY"] = ...` 植入 `scripts/std_bulk_import.py` 时
    **测试全绿**——而脚本/启动器层恰恰是本次事故的形态所在，所以射程必须覆盖
    scripts/、plugin/、根目录、.ps1/.bat/.cmd。

    「不要动系统层」之后这条更硬：连 `SetValueEx`（注册表写原语）也一并禁掉，
    整个引擎只允许**删除**注册表值（清理动作），不允许写。
    """
    write_tokens = ("SetValueEx", "setx ", "putenv", "SetEnvironmentVariable",
                    "os.environ[", "environ.setdefault")
    offenders: list[str] = []
    for path, rel in _iter_code_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            code = line.split("#", 1)[0]           # 注释里提到不算（文档必须能讲这件事）
            if any(tok in code for tok in write_tokens) and (
                    any(name in code for name in LEGACY_NAMES) or "SetValueEx" in code):
                offenders.append(f"{rel}:{i}: {line.strip()[:120]}")
    assert offenders == [], "源码里仍有系统层写入: " + "; ".join(offenders)


def test_legacy_names_appear_only_in_reviewed_files():
    """旧名出现的位置白名单化：新增引用会红，逼一次人工复核（防偷偷搬回裸名）。"""
    hits: set[str] = set()
    for path, rel in _iter_code_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"DEEPSEEK_(API_KEY|BASE_URL|MODEL)", text):
            hits.add(rel)
    assert hits <= LEGACY_ALLOWED_FILES, (
        f"未复核的旧名引用: {sorted(hits - LEGACY_ALLOWED_FILES)}；"
        f"白名单里已不存在的: {sorted(LEGACY_ALLOWED_FILES - hits)}")
    # 防空洞：扫描确实读到了文件并找到了已知命中，而不是「一个都没扫到」而通过
    assert {"src/core/config.py",
            "src/core/settings/api_credentials.py"} <= hits


# ---------- 2. 写入：只进加密存储，系统层零写入 ----------
def test_set_credential_writes_encrypted_store_not_registry(fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-new", base_url="https://llm.example")
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new"
    assert ss.read_value("KS_LLM_BASE_URL") == "https://llm.example"
    assert fake_reg.store == {}, "保存凭据不许再往系统层写任何东西"


def test_write_path_does_not_touch_winreg_at_all(monkeypatch, store_dir):
    """最强结构断言：把 winreg 换成"一碰就炸"，保存仍必须成功。"""
    class Exploding:
        def __getattr__(self, item):
            raise AssertionError(f"不该访问 winreg.{item}（系统层零写入是硬约束）")

    monkeypatch.setattr("src.core.settings.api_credentials.winreg", Exploding())
    monkeypatch.setitem(sys.modules, "winreg", Exploding())
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-no-registry", base_url="https://x")
    set_credential("mineru_cloud", api_key="tok-cloud")
    assert ss.read_value("KS_LLM_API_KEY") == "sk-no-registry"
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-cloud"


def test_dash_clears_store_value(fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-a", base_url="https://a")
    set_credential("llm", api_key="-", base_url="-")
    assert ss.read_value("KS_LLM_API_KEY") == ""
    assert ss.read_value("KS_LLM_BASE_URL") == ""
    assert fake_reg.store == {}


def test_blank_value_skips_without_clobbering(fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-keep-me")
    set_credential("llm", api_key="   ")            # 白空格=跳过，不得抹掉已配置
    assert ss.read_value("KS_LLM_API_KEY") == "sk-keep-me"


def test_unknown_channel_rejected():
    from src.core.settings.api_credentials import UnknownChannel, set_credential
    with pytest.raises(UnknownChannel):
        set_credential("tts", api_key="x")


def test_stored_channels_reports_booleans_only():
    from src.core.settings.api_credentials import set_credential, stored_channels
    set_credential("llm", api_key="sk-secret-marker")
    st = stored_channels()
    assert st["llm"]["api_key"] is True
    assert st["llm"]["base_url"] is False
    assert st["mineru_cloud"]["api_key"] is False
    assert "sk-secret-marker" not in repr(st)


# ---------- 3. 读取链：env 覆盖 → 存储 → 旧系统层 → 默认 ----------
def test_store_value_is_read(fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-from-store")
    reset_settings()
    assert get_settings().llm_api_key == "sk-from-store"


def test_env_override_beats_store(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-from-store")
    monkeypatch.setenv("KS_LLM_API_KEY", "sk-from-env")
    reset_settings()
    assert get_settings().llm_api_key == "sk-from-env"


def test_store_beats_legacy_system_layer(fake_reg, monkeypatch):
    """存储是权威：系统层里还有旧值也不该压过它（否则"设置页改了不生效"）。"""
    from src.core.settings.api_credentials import set_credential
    set_credential("llm", api_key="sk-from-store")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy-registry"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-legacy-env")
    reset_settings()
    assert get_settings().llm_api_key == "sk-from-store"


def test_legacy_system_layer_still_readable_for_backward_compat(fake_reg):
    """**关键兼容断言**：没迁移的老机器（系统层里只有旧名）必须照旧能跑。"""
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    reset_settings()
    assert get_settings().llm_api_key == "sk-legacy"


def test_legacy_env_still_readable(fake_reg, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-legacy-env")
    reset_settings()
    assert get_settings().llm_api_key == "sk-legacy-env"


def test_env_beats_legacy_registry_for_same_name(fake_reg, monkeypatch):
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy-registry"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-legacy-env")
    reset_settings()
    assert get_settings().llm_api_key == "sk-legacy-env"


def test_base_url_and_model_chain(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import set_credential
    fake_reg.store["DEEPSEEK_BASE_URL"] = "https://legacy.example"
    reset_settings()
    assert get_settings().llm_base_url == "https://legacy.example"

    set_credential("llm", base_url="https://store.example")
    reset_settings()
    assert get_settings().llm_base_url == "https://store.example"

    monkeypatch.setenv("KS_LLM_MODEL", "ks-model")
    reset_settings()
    assert get_settings().llm_model == "ks-model"


def test_cloud_channel_reads_from_store(fake_reg):
    from src.core.settings.api_credentials import set_credential
    set_credential("mineru_cloud", api_key="tok-cloud", base_url="https://cloud.example")
    reset_settings()
    s = get_settings()
    assert s.mineru_cloud_api_key == "tok-cloud"
    assert s.mineru_cloud_base_url == "https://cloud.example"


def test_defaults_when_nothing_configured(fake_reg):
    reset_settings()
    s = get_settings()
    assert s.llm_api_key == ""
    assert s.llm_base_url == "https://api.deepseek.com"
    assert s.llm_model == "deepseek-chat"
    assert s.mineru_cloud_base_url == "https://mineru.net"


# ---------- 4. 迁移：先核对再删、冲突不覆盖 ----------
def test_system_layer_status_reports_presence_without_values(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import system_layer_status
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-super-secret"
    monkeypatch.setenv("KS_MINERU_CLOUD_API_KEY", "tok-also-secret")
    rows = {r["name"]: r for r in system_layer_status()}
    assert rows["DEEPSEEK_API_KEY"]["in_registry"] is True
    assert rows["DEEPSEEK_API_KEY"]["length"] == len("sk-super-secret")
    assert rows["KS_MINERU_CLOUD_API_KEY"]["in_env"] is True
    assert "sk-super-secret" not in repr(rows) and "tok-also-secret" not in repr(rows)


def test_legacy_status_reports_presence_without_values(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import legacy_status
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-super-secret"
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://legacy.example")
    st = legacy_status("llm")
    assert st["present"] is True
    assert "sk-super-secret" not in repr(st) and "legacy.example" not in repr(st)


def test_adopt_legacy_moves_into_store_and_keeps_system_layer_by_default(fake_reg):
    from src.core.settings.api_credentials import adopt_legacy
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    fake_reg.store["DEEPSEEK_BASE_URL"] = "https://legacy.example"
    res = adopt_legacy("llm")
    assert sorted(res["copied"]) == ["KS_LLM_API_KEY", "KS_LLM_BASE_URL"]
    assert sorted(res["verified"]) == ["KS_LLM_API_KEY", "KS_LLM_BASE_URL"]
    assert res["deleted"] == []
    assert ss.read_value("KS_LLM_API_KEY") == "sk-legacy"
    assert fake_reg.store["DEEPSEEK_API_KEY"] == "sk-legacy"    # 默认不动系统层
    assert "sk-legacy" not in repr(res)                          # 不回显值


def test_adopt_legacy_delete_removes_registry_after_verify(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import adopt_legacy
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://legacy.example")
    res = adopt_legacy("llm", delete_legacy=True)
    assert res["deleted"] == ["DEEPSEEK_API_KEY"]
    assert "DEEPSEEK_API_KEY" not in fake_reg.store
    assert ss.read_value("KS_LLM_API_KEY") == "sk-legacy"
    # 只存在于进程环境变量里的删不掉 —— 如实上报，不谎报「已清理」
    assert res["env_untouched"] == ["DEEPSEEK_BASE_URL"]
    assert ss.read_value("KS_LLM_BASE_URL") == "https://legacy.example"


def test_adopt_legacy_never_clobbers_existing_store_value(fake_reg):
    """verifier P1 回归：存储里已有值（用户在设置页刚存的新 Key）绝不能被旧值冲掉。"""
    from src.core.settings.api_credentials import adopt_legacy, set_credential
    set_credential("llm", api_key="sk-new-fresh")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-old-stale"
    res = adopt_legacy("llm")
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new-fresh"
    assert res["copied"] == []
    assert res["skipped_kept"] == ["KS_LLM_API_KEY"]
    assert res["conflicts"] == ["DEEPSEEK_API_KEY"]
    assert "sk-old-stale" not in repr(res) and "sk-new-fresh" not in repr(res)


def test_adopt_legacy_delete_refuses_to_drop_conflicting_legacy(fake_reg):
    from src.core.settings.api_credentials import adopt_legacy, set_credential
    set_credential("llm", api_key="sk-new-fresh")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-old-stale"
    res = adopt_legacy("llm", delete_legacy=True)
    assert res["deleted"] == []
    assert fake_reg.store["DEEPSEEK_API_KEY"] == "sk-old-stale"   # 唯一样本保住
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new-fresh"


def test_adopt_legacy_force_discards_conflicting_legacy(fake_reg):
    from src.core.settings.api_credentials import adopt_legacy, set_credential
    set_credential("llm", api_key="sk-new-fresh")
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-old-stale"
    res = adopt_legacy("llm", delete_legacy=True, force=True)
    assert res["deleted"] == ["DEEPSEEK_API_KEY"]
    assert "DEEPSEEK_API_KEY" not in fake_reg.store
    assert ss.read_value("KS_LLM_API_KEY") == "sk-new-fresh"


def test_adopt_legacy_invalidates_settings_cache(fake_reg):
    """迁移后必须失效进程内缓存（verifier mut6 曾证明此处空洞）。"""
    from src.core.settings.api_credentials import adopt_legacy
    reset_settings()
    assert get_settings().llm_api_key == ""          # 先把「无 Key」缓存住
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    assert adopt_legacy("llm")["copied"] == ["KS_LLM_API_KEY"]
    assert get_settings().llm_api_key == "sk-legacy"  # 缓存失效才读得到


def test_adopt_legacy_noop_when_nothing_legacy(fake_reg):
    from src.core.settings.api_credentials import adopt_legacy
    res = adopt_legacy("llm", delete_legacy=True)
    assert res["copied"] == [] and res["deleted"] == []


def test_adopt_legacy_unknown_channel_rejected():
    from src.core.settings.api_credentials import UnknownChannel, adopt_legacy
    with pytest.raises(UnknownChannel):
        adopt_legacy("tts")


def test_import_system_layer_moves_same_named_vars(fake_reg, monkeypatch):
    """同名搬家：KS_MINERU_CLOUD_API_KEY 从系统层搬进加密存储。"""
    from src.core.settings.api_credentials import import_system_layer
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-registry"
    monkeypatch.setenv("KS_MINERU_CLOUD_BASE_URL", "https://cloud.example")
    res = import_system_layer("mineru_cloud")
    assert sorted(res["copied"]) == ["KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_BASE_URL"]
    assert sorted(res["verified"]) == sorted(res["copied"])
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-registry"


def test_import_system_layer_keeps_existing_store_value(fake_reg):
    from src.core.settings.api_credentials import import_system_layer, set_credential
    set_credential("mineru_cloud", api_key="tok-fresh")
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-stale"
    res = import_system_layer("mineru_cloud")
    assert res["skipped_kept"] == ["KS_MINERU_CLOUD_API_KEY"]
    assert res["conflicts"] == ["KS_MINERU_CLOUD_API_KEY"]
    assert ss.read_value("KS_MINERU_CLOUD_API_KEY") == "tok-fresh"


def test_clean_system_layer_deletes_only_named_targets(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import clean_system_layer
    fake_reg.store["DEEPSEEK_API_KEY"] = "sk-legacy"
    fake_reg.store["KS_MINERU_CLOUD_API_KEY"] = "tok-cloud"
    out = clean_system_layer(["DEEPSEEK_API_KEY"])
    assert out["deleted"] == ["DEEPSEEK_API_KEY"]
    assert "KS_MINERU_CLOUD_API_KEY" in fake_reg.store       # 不在目标里 → 不动
    assert "DEEPSEEK_API_KEY" not in fake_reg.store


def test_clean_system_layer_reports_env_untouched(fake_reg, monkeypatch):
    from src.core.settings.api_credentials import clean_system_layer
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-only")
    out = clean_system_layer(["DEEPSEEK_API_KEY"])
    assert out["deleted"] == []                              # 注册表里没有，删不掉
    assert out["env_untouched"] == ["DEEPSEEK_API_KEY"]       # 如实上报
