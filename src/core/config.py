"""配置中心。敏感值只从「环境变量覆盖 → 引擎加密存储 → 旧系统层兼容」读取，禁止落明文。

**2026-09-11 起密钥不再经系统层**（业主指令：「不要动系统层」）。此前 Phase 9.1 让
`llm_api_key` 回退读 `HKCU\\Environment`（setx 落点），设置页也往那里写 —— 这造成真实
事故：DSH（DeepSeek Harness）把**继承来的进程环境变量**当最高优先级且只读的凭据来源、
并在启动时冻结环境快照，于是引擎一保存 Key，DSH 的模型设置页密钥输入框就被置灰
（用户两次踩到）。现在：

- **权威存储**：`src/core/settings/secret_store.py`（`<data_dir>/secrets.json`，值用
  Windows DPAPI 用户态加密）—— 设置页保存的 Key 住在这里；
- **环境变量**（`KS_LLM_API_KEY` / `KS_LLM_BASE_URL` / `KS_LLM_MODEL`、
  `KS_MINERU_CLOUD_*`）只作**显式覆盖**（CI/脚本/临时调试），引擎**绝不写** env；
- **旧系统层**（`DEEPSEEK_*` 的 env 与 HKCU）保留**只读兼容**，已 deprecate ——
  老安装不迁移也能跑；`scripts/ks-credentials-migrate.py` 负责搬进存储并清掉系统层。

命名空间化的理由（仍然有效）：裸全局名会与别的产品的凭据名字**撞名**；`KS_` 前缀把
我们的变量圈在自己的命名空间里，即便有人在系统层设了 `KS_*`，也不会遮蔽 DSH。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _default_data_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    # 支持测试/开发重定向
    override = os.environ.get("KS_DATA_DIR")
    return Path(override) if override else Path(appdata) / "KnowledgeStation"


#: LLM 通道变量名：第一个是「显式覆盖名」（也是存储里的键名），其余只作旧系统层只读回退
_LLM_KEY_VARS = ("KS_LLM_API_KEY", "DEEPSEEK_API_KEY")
_LLM_URL_VARS = ("KS_LLM_BASE_URL", "DEEPSEEK_BASE_URL")
_LLM_MODEL_VARS = ("KS_LLM_MODEL", "DEEPSEEK_MODEL")
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"


def _read_env_or_registry(name: str, default: str = "") -> str:
    """通用取值链：进程环境变量 → HKCU\\Environment（setx 落点）→ default。"""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, name)
            return str(val).strip() or default
    except Exception:
        return default


def _read_first(names: tuple[str, ...], default: str = "") -> str:
    """按顺序逐个走 `_read_env_or_registry`，取第一个非空值（命名空间优先）。

    注意顺序语义：是「名的顺序」优先于「env 高于注册表」——即 `KS_LLM_API_KEY`
    的注册表值也压过 `DEEPSEEK_API_KEY` 的环境变量值。这是刻意的：用户一旦在
    KS 设置页保存过新名，旧全局变量就只是遗留污染，不该再影响引擎。
    """
    for name in names:
        v = _read_env_or_registry(name, "")
        if v:
            return v
    return default


def _read_secret(name: str, legacy_names: tuple[str, ...] = (),
                 default: str = "") -> str:
    """通道取值的**唯一入口**（2026-09-11「不要动系统层」改造后的链条）：

        1. `KS_*` **环境变量** —— 显式覆盖（CI/脚本/临时调试；只读，引擎绝不写 env）
        2. 引擎自己的**加密存储** `secret_store`（`<data_dir>/secrets.json`，DPAPI）
           —— 设置页保存的 Key 就住在这里，系统层不再存一份
        3. 旧系统层（`DEEPSEEK_*` 等的 env → HKCU\\Environment）：**只读兼容、已 deprecate**
           —— 老安装不迁移也能跑；`scripts/ks-credentials-migrate.py` 负责搬走并清掉
        4. `default`

    为什么 env 覆盖排在存储**之前**：环境变量是进程级的显式声明（"这次就用这个"），
    即时意图应压过持久配置，且它只影响**当前进程**，不会像写系统层那样污染别的产品。
    为什么不会造成「设置页改了却没生效」：设置页写的是存储，只要没人设 `KS_*` 环境变量，
    第 1 步就是空的，存储永远说了算；真有那种变量时
    `api_credentials.system_layer_status()` 会把它们列出来（看得见，不神秘）。
    """
    from src.core.settings import secret_store          # 懒 import：避免环形依赖
    for env_name in (name,):
        v = os.environ.get(env_name, "").strip()
        if v:
            return v
    v = secret_store.read_value(name)
    if v:
        return v
    return _read_first(legacy_names, default)


def _read_api_key() -> str:
    """LLM Key：`KS_LLM_API_KEY` env 覆盖 → 加密存储 → 旧系统层 `DEEPSEEK_API_KEY` 兼容。"""
    return _read_secret(_LLM_KEY_VARS[0], _LLM_KEY_VARS[1:], "")


def _read_llm_base_url() -> str:
    return _read_secret(_LLM_URL_VARS[0], _LLM_URL_VARS[1:], DEFAULT_LLM_BASE_URL)


def _read_llm_model() -> str:
    return _read_secret(_LLM_MODEL_VARS[0], _LLM_MODEL_VARS[1:], "deepseek-chat")


def _read_mineru_key() -> str:
    return _read_secret("KS_MINERU_CLOUD_API_KEY", (), "")


def _read_mineru_base_url() -> str:
    return _read_secret("KS_MINERU_CLOUD_BASE_URL", (), MINERU_CLOUD_DEFAULT_BASE_URL)


#: MinerU 云解析模型版本（官方 v4 契约：pipeline 默认 / vlm 推荐 / MinerU-HTML）。
#: 2026-09-15 加入设置项（用户要求「设置里除了填 KEY 还能选模式」）。
#: 非密值，但存同一加密存储（引擎自有 KV），env 可临时覆盖。
MINERU_CLOUD_MODEL_VERSIONS: tuple[str, ...] = ("pipeline", "vlm", "MinerU-HTML")
MINERU_CLOUD_DEFAULT_MODEL_VERSION = "pipeline"
#: 存储/环境变量名（api_credentials / routes_settings / 本模块共用同一常量）
MINERU_CLOUD_MODEL_VERSION_VAR = "KS_MINERU_CLOUD_MODEL_VERSION"


def _read_mineru_model_version() -> str:
    """读 MinerU 云模式；非法值回落到 pipeline（不因手填错值而让云请求 400）。"""
    raw = _read_secret(MINERU_CLOUD_MODEL_VERSION_VAR, (),
                       MINERU_CLOUD_DEFAULT_MODEL_VERSION).strip()
    for v in MINERU_CLOUD_MODEL_VERSIONS:          # 大小写不敏感归一（vlm/VLM）
        if raw.lower() == v.lower():
            return v
    return MINERU_CLOUD_DEFAULT_MODEL_VERSION


# 云解析通道（2026-09-01 架构反转；2026-09-08 用户裁决通道优先级）：
# 已配置云 Key → 云优先、本地兜底；未配置 → 直接本地通道（纯本地不外发）。
# Key 存引擎自己的加密存储（secret_store，DPAPI），**不落库、不落系统层**。
MINERU_CLOUD_DEFAULT_BASE_URL = "https://mineru.net"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    # DeepSeek 官方 API；本地 LM Studio 时改 base_url（存加密存储 / KS_LLM_BASE_URL 覆盖）
    llm_base_url: str = field(default_factory=_read_llm_base_url)
    llm_model: str = field(default_factory=_read_llm_model)
    # Key 存在引擎加密存储里；KS_ 环境变量可临时覆盖
    llm_api_key: str = field(default_factory=_read_api_key)
    # ===== 云解析通道（MinerU 官方云 API；已配置则云优先、本地兜底）=====
    mineru_cloud_api_key: str = field(default_factory=_read_mineru_key)
    mineru_cloud_base_url: str = field(default_factory=_read_mineru_base_url)
    # 模型版本：pipeline（默认）/ vlm（推荐）/ MinerU-HTML —— 官方 v4 契约
    mineru_cloud_model_version: str = field(default_factory=_read_mineru_model_version)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "database" / "knowledge.db"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_dirs()
    return _settings


def reset_settings() -> None:
    """测试用：清理缓存使环境变量生效。"""
    global _settings
    _settings = None

