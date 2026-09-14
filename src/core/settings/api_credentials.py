# -*- coding: utf-8 -*-
"""API 凭据存储（2026-08-27；2026-09-01 云解析换组；**2026-09-11 命名空间化**）。
设置→API 配置 的后端实现。

红线（security.md + 业主指令 2026-09-11「不要动系统层」）：
**Key 一律写引擎自己的加密存储** `secret_store`（`<data_dir>/secrets.json`，Windows DPAPI
用户态加密）——绝不写注册表、绝不写库、绝不写系统环境变量、绝不回显。
系统层（`HKCU\\Environment` / `DEEPSEEK_*` 进程变量）**只读**：迁移前兼容 +
迁移工具的读取源；唯一允许的写系统层操作是 `clean_system_layer()` 的**删除**
（先核对存储读回一致才删）。

通道（**一律 KS_ 前缀**）：
- mineru_cloud : KS_MINERU_CLOUD_API_KEY + KS_MINERU_CLOUD_BASE_URL
                 （云解析通道：已配置则导入文件**云优先、本地兜底**，
                    未配置则直接本地通道；产物归一化为本地同构布局）
- llm          : KS_LLM_API_KEY + KS_LLM_BASE_URL
                 （2026-09-11 起；旧名 DEEPSEEK_API_KEY/DEEPSEEK_BASE_URL 降级为**只读回退**）

## 为什么不能再碰系统层（真实事故 2026-09-11，用户两次踩到）
原实现把 LLM Key 写进**裸全局**变量 `DEEPSEEK_API_KEY`（后改为 KS_ 前缀仍写注册表）。
DSH（DeepSeek Harness）解析凭据时**继承来的进程环境变量优先级最高且只读**、且环境
快照在启动时冻结——KS 一保存 Key，之后启动的 DSH 就认定 Key「由启动环境提供」，
模型设置页的密钥输入框被置灰、写 `.credentials.yaml` 被静默遮蔽。业主裁决：
「需要配置 key 那就在插件或者 DSH 内部配置，**不要动系统层**」。
台账决策 20 的原话是「密钥引擎侧 DPAPI 加密，不绑全局」——这次改造是让实现
真正回到决策，而不只是躲开症状。

## 兼容（不迁移也不坏）
读取链（src/core/config.py `_read_secret`）：`KS_*` 环境变量（显式覆盖）→ 加密存储 →
旧系统层（`DEEPSEEK_*` 等，只读）。已有安装照常工作；要清掉系统层旧条目用
`scripts/ks-credentials-migrate.py`（默认只打印计划；`--apply --clean-system` 才动真，
先核对读回一致才删；删完须**重启 DSH 宿主**其密钥输入框才恢复可写）。

保存后调用方须 reset_settings() 让引擎进程内缓存立即失效。
"""
from __future__ import annotations

import os
import winreg

from src.core.config import reset_settings
from src.core.settings import secret_store

#: 通道 → (api_key 变量名, base_url 变量名)。
#: **所有通道都必须自带 KS_ 命名空间**——`tests/test_credentials_namespace.py` 会断言，
#: 防止再退化成裸全局名（那正是 2026-09-11 事故的形态）。
CHANNEL_VARS: dict[str, tuple[str, str]] = {
    "mineru_cloud": ("KS_MINERU_CLOUD_API_KEY", "KS_MINERU_CLOUD_BASE_URL"),
    "llm": ("KS_LLM_API_KEY", "KS_LLM_BASE_URL"),
}
#: 历史变量名 → 同一个 (api_key, base_url) 元组。**只读回退 + 可选迁移，绝不再写入**。
LEGACY_CHANNEL_VARS: dict[str, tuple[str, str]] = {
    "llm": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"),
}
#: 通道 → 额外非密变量（云解析通道无；llm 模型名走 env，不在此配置）
CHANNEL_EXTRA_VARS: dict[str, tuple[str, str]] = {}


class UnknownChannel(ValueError):
    pass


class InvalidModelVersion(ValueError):
    """云解析模式取值非法（官方契约三选一：pipeline / vlm / MinerU-HTML）。"""


def set_credential(channel: str, api_key: str | None = None,
                   base_url: str | None = None,
                   model_version: str | None = None) -> None:
    """把通道凭据写进**引擎自己的加密存储**（`secret_store`，DPAPI）。

    **2026-09-11 起不再写系统层**：此前这里写 `HKCU\\Environment`，而 DSH 把继承来的
    进程环境变量当最高优先级且只读的凭据来源 → 一保存 Key 就把 DSH 的密钥输入框锁死。
    业主裁决「不要动系统层」，所以写入落到 `<data_dir>/secrets.json`（值 DPAPI 加密）。

    值为 None 或空串的项跳过不覆盖（防误清空）；传 "-" 表示显式删除该值。
    verifier F13/F17（2026-09-08）：白空格 Key 曾会被写成空串、抹掉已配置的 Key
    → 与 base_url 同款守卫。

    model_version（2026-09-15，仅 mineru_cloud）：非密值，但同样入加密存储
    （引擎自有 KV，避免另立存储）；**值必须属于官方契约三选一**，非法即抛
    InvalidModelVersion（不回显 Key，也不让脏值进存储）。
    """
    if channel not in CHANNEL_VARS:
        raise UnknownChannel(f"未知通道: {channel}")
    key_name, url_name = CHANNEL_VARS[channel]
    changes: dict[str, str | None] = {}
    for name, val in ((key_name, api_key), (url_name, base_url)):
        if val is None or not val.strip():
            continue                       # 跳过（不覆盖）
        v = val.strip()
        changes[name] = None if v == "-" else v
    if model_version is not None and model_version.strip():
        if channel != "mineru_cloud":
            raise UnknownChannel(f"通道 {channel} 不支持 model_version")
        from src.core.config import (
            MINERU_CLOUD_MODEL_VERSIONS, MINERU_CLOUD_MODEL_VERSION_VAR)
        v = model_version.strip()
        hit = next((c for c in MINERU_CLOUD_MODEL_VERSIONS
                    if v.lower() == c.lower()), None)
        if hit is None:
            raise InvalidModelVersion(
                f"model_version 必须是 {'/'.join(MINERU_CLOUD_MODEL_VERSIONS)}"
                f" 之一，收到 {model_version!r}")
        changes[MINERU_CLOUD_MODEL_VERSION_VAR] = hit
    if changes:
        secret_store.write_values(changes)   # 加密失败会抛 SecretStoreError，整体不写


def import_system_layer(channel: str, *, force: bool = False) -> dict:
    """把系统层里**本通道自己的名字**（同名迁移）搬进加密存储。

    与 `adopt_legacy` 的区别：那个负责**改名**（`DEEPSEEK_*` → `KS_LLM_*`），
    这个负责**同名搬家**（`KS_MINERU_CLOUD_API_KEY` 从 HKCU 搬到加密存储）。
    两个一起跑才覆盖系统层全部条目。

    不覆盖：存储里已有值就保持不动（值不同记 `conflicts`）。先核对再删：只有
    "从存储读回来与源值一致"的名字才会出现在 `verified` 里，`delete_legacy=True`
    时也只删这些 —— 没验证成功的一个都不删。
    """
    if channel not in CHANNEL_VARS:
        raise UnknownChannel(f"未知通道: {channel}")
    names = list(CHANNEL_VARS[channel])
    to_store: dict[str, str | None] = {}
    skipped_kept: list[str] = []
    conflicts: list[str] = []
    for name in names:
        val = _read_any_var(name)
        if not val:
            continue
        if secret_store.has_value(name):
            skipped_kept.append(name)
            if secret_store.read_value(name) != val:
                conflicts.append(name)
            continue
        to_store[name] = val
    if to_store:
        secret_store.write_values(to_store)
    verified = [n for n, v in to_store.items() if secret_store.read_value(n) == v]
    # 2026-09-12 批2 修正：skipped_kept 里「存储值 == 系统层源值」的名字也算 verified——
    # 否则 --apply 跑完再 --apply --clean-system 时（第二次没东西可搬），verify-before-delete
    # 会因 verified 为空而拒删一切，删除段静默空转（真实踩到：批2 第一遍 --clean-system 删了 0 条）。
    # 语义不变：能删的前提始终是「存储里能读回、且与系统层源值一致」；这里只是把
    # 「上一轮已搬进并核对过」的名字补进核对集合，值不一致的仍留在 conflicts、绝不删。
    for name in skipped_kept:
        if name in conflicts:
            continue
        stored = secret_store.read_value(name)
        sysval = _read_any_var(name)
        if stored and sysval and stored == sysval:
            verified.append(name)
    for n in to_store:
        if n not in verified:
            conflicts.append(n)
    reset_settings()
    return {"channel": channel, "copied": list(to_store.keys()), "verified": verified,
            "skipped_kept": skipped_kept, "conflicts": conflicts}


def stored_channels() -> dict:
    """存储里各通道已配置了哪些名字（**只报布尔，不解密、不回显**）。"""
    names = set(secret_store.stored_names())
    return {ch: {"api_key": key in names, "base_url": url in names}
            for ch, (key, url) in CHANNEL_VARS.items()}


def _read_registry_var(name: str) -> str:
    """读 HKCU\\Environment 单值；不存在/读取失败返回 ""（不打印、不外传）。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            val, _ = winreg.QueryValueEx(k, name)
            return str(val).strip()
    except Exception:
        return ""


def _read_any_var(name: str) -> str:
    """单个变量内部：进程环境变量 → 注册表（与 src.core.config 的同名语义一致）。

    注意：这**只是「同一个名字内部」的顺序**。跨名字时 `config._read_first` 是
    「名的顺序优先于来源顺序」。两处语义不同，别当成同一个东西（verifier 2026-09-11）。
    """
    return os.environ.get(name, "").strip() or _read_registry_var(name)


def legacy_status(channel: str = "llm") -> dict:
    """旧全局变量的现状：**只报存在性与来源，绝不回显 Key 的值**。

    用途：迁移前给用户看「旧名还在不在、在哪」，避免盲删。
    """
    if channel not in LEGACY_CHANNEL_VARS:
        return {"channel": channel, "legacy": [], "present": False}
    items = []
    for name in LEGACY_CHANNEL_VARS[channel]:
        in_env = bool(os.environ.get(name, "").strip())
        in_registry = bool(_read_registry_var(name))
        items.append({"name": name, "in_env": in_env, "in_registry": in_registry})
    return {"channel": channel, "legacy": items,
            "present": any(x["in_env"] or x["in_registry"] for x in items)}


# --------------------------------------------------------------------------
# 系统层现状与清理（业主指令：「不要动系统层」→ 已写进去的要能清掉）
# --------------------------------------------------------------------------
def system_layer_names() -> list[str]:
    """引擎**曾经**可能写进系统层的全部变量名（含 legacy 与各通道）。"""
    names: list[str] = []
    for pair in CHANNEL_VARS.values():
        names.extend(pair)
    for pair in LEGACY_CHANNEL_VARS.values():
        names.extend(pair)
    return sorted(set(names))


def system_layer_status() -> list[dict]:
    """系统层里这些名字的现状（**只报存在性/长度，绝不回显值**）。"""
    items = []
    for name in system_layer_names():
        in_env = bool(os.environ.get(name, "").strip())
        raw = _read_registry_var(name)
        items.append({"name": name, "in_env": in_env,
                      "in_registry": bool(raw), "length": len(raw) if raw else 0})
    return items


def clean_system_layer(names: list[str] | None = None) -> dict:
    """删除系统层（HKCU\\Environment）里的这些变量 —— **不可逆的破坏性操作**。

    只删注册表值；只存在于**进程环境变量**里的删不掉（本进程改不了别处的环境块），
    如实放进 `env_untouched`，绝不谎报「已清理」。
    """
    targets = names if names is not None else system_layer_names()
    deleted: list[str] = []
    env_untouched: list[str] = []
    for name in targets:
        if _read_registry_var(name):
            try:
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                        winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
                    try:
                        winreg.DeleteValue(k, name)
                    except FileNotFoundError:
                        pass
                deleted.append(name)
            except OSError:
                pass
        if os.environ.get(name, "").strip():
            env_untouched.append(name)
    from src.core.config import reset_settings
    reset_settings()
    return {"deleted": deleted, "env_untouched": env_untouched}


def adopt_legacy(channel: str = "llm", *, delete_legacy: bool = False,
                 force: bool = False) -> dict:
    """把旧全局变量的值迁到命名空间名（**返回值只含变量名/布尔，绝不含值**）。

    - `delete_legacy=False`（默认）：只复制，旧变量原样保留 → 无破坏性，随时可回退。
    - `delete_legacy=True`：复制成功后删除**注册表里**的旧变量（动全局环境变量，
      可能影响别的工具）→ 只由用户显式触发（scripts/ks-credentials-migrate.py）。

    ## 不覆盖原则（verifier P1，2026-09-11）
    只有**新名为空**时才复制。若 `KS_LLM_API_KEY` 已经有值，而旧名也有值且**两者不同**，
    那就是 `conflict`：此时

    * 不覆盖新名（否则会把用户在设置页刚保存的新 Key 冲回旧值）；
    * **即使 `delete_legacy=True` 也不删旧名**（旧名此刻是旧值的唯一样本，删了就永久丢失）。
      要强行丢弃旧值得显式 `force=True`。
    这条是verifier 复现出来的真实缺陷：原实现无条件 `_set_registry_value(new, old_val)`，
    于是「先存新 Key → 再跑迁移 → 加 --delete-legacy」会把新 Key 永久覆盖掉且不可恢复。

    ## 诚实上报
    只存在于**进程环境变量**里的旧值删不掉（本进程改不了别处的环境块），如实放进
    `env_untouched`；被跳过的名字放进 `skipped_kept`。绝不谎报「已清理」。
    """
    if channel not in LEGACY_CHANNEL_VARS:
        raise UnknownChannel(f"未知通道: {channel}")
    if channel not in CHANNEL_VARS:
        raise UnknownChannel(f"通道未配置命名空间: {channel}")
    old_key, old_url = LEGACY_CHANNEL_VARS[channel]
    new_key, new_url = CHANNEL_VARS[channel]
    copied: list[str] = []
    skipped_kept: list[str] = []
    conflicts: list[str] = []
    to_store: dict[str, str | None] = {}
    for old, new in ((old_key, new_key), (old_url, new_url)):
        old_val = _read_any_var(old)
        if not old_val:
            continue
        # 存储里已有值 → 绝不覆盖；值不同则记为冲突（只比较，不外传）
        if secret_store.has_value(new):
            skipped_kept.append(new)
            if secret_store.read_value(new) != old_val:
                conflicts.append(old)
            continue
        to_store[new] = old_val
    if to_store:
        secret_store.write_values(to_store)      # 加密失败会抛，整体不写
    # **先核对再删**：只有"从存储读回来的值与源值一致"的名字才允许删系统层
    copied = list(to_store.keys())
    verified = [n for n, v in to_store.items() if secret_store.read_value(n) == v]
    # 2026-09-12 批2 修正（与 import_system_layer 同源缺陷）：skipped_kept 且值一致
    # 的名字补进 verified——两遍式迁移（先 --apply 后 --apply --clean-system）时
    # 第二遍没有可搬条目、verified 为空，会导致删除段静默空转。
    for new in skipped_kept:
        if new in conflicts:
            continue
        old = old_key if new == new_key else old_url
        stored = secret_store.read_value(new)
        oldval = _read_any_var(old)
        if stored and oldval and stored == oldval:
            verified.append(new)
    for n in copied:
        if n not in verified:
            conflicts.append(n)                  # 读回不一致 → 冲突，绝不删源
    deleted: list[str] = []
    env_untouched: list[str] = []
    if delete_legacy:
        for old, new in ((old_key, new_key), (old_url, new_url)):
            if not _read_any_var(old):
                continue
            # 冲突且未显式 force → 不删（旧值是旧值唯一副本），如实上报
            if old in conflicts and not force:
                continue
            # 没能验证落地到存储的名字，同样绝不删源
            if new not in verified and new not in skipped_kept:
                continue
            if _read_registry_var(old):
                try:
                    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, "Environment", 0,
                                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
                        try:
                            winreg.DeleteValue(k, old)
                        except FileNotFoundError:
                            pass
                    deleted.append(old)
                except OSError:
                    pass
            if os.environ.get(old, "").strip():
                env_untouched.append(old)
    if copied or deleted or skipped_kept:
        reset_settings()
    return {"channel": channel, "copied": copied, "verified": verified,
            "skipped_kept": skipped_kept, "conflicts": conflicts,
            "deleted": deleted, "env_untouched": env_untouched, "ok": True}


def get_status() -> dict:
    """脱敏状态：只给 configured 布尔与 base_url，绝不回显 Key。

    2026-09-15：mineru_cloud 增加 `model_version`（**非密值**，可回显）与
    `model_versions`（可选值清单，供 UI 渲染下拉）——用户要求「设置里除了填
    KEY 还能选模式」（MinerU 官方 v4：pipeline / vlm / MinerU-HTML）。
    """
    from src.core.config import (
        MINERU_CLOUD_MODEL_VERSIONS, get_settings)
    s = get_settings()
    return {
        "mineru_cloud": {"configured": bool(s.mineru_cloud_api_key),
                         "base_url": s.mineru_cloud_base_url,
                         "model_version": s.mineru_cloud_model_version,
                         "model_versions": list(MINERU_CLOUD_MODEL_VERSIONS)},
        "llm": {"configured": bool(s.llm_api_key), "base_url": s.llm_base_url},
    }


def test_channel(channel: str) -> dict:
    """活体探测：真实调一次上游，返回 {ok, detail}（不含 Key）。"""
    if channel not in CHANNEL_VARS:
        raise UnknownChannel(f"未知通道: {channel}")
    if channel == "mineru_cloud":
        return _test_mineru_cloud()
    return _test_llm()


def _test_mineru_cloud() -> dict:
    """云解析通道探测：申请一次签名上传 URL 验证 token（不上传不启动任务）。"""
    from src.core.ingestion.mineru_cloud import probe_token
    return probe_token()


def _test_llm() -> dict:
    from src.core.config import get_settings
    s = get_settings()
    if not s.llm_api_key:
        return {"ok": False, "detail": "LLM Key 未配置"}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=s.llm_api_key, base_url=s.llm_base_url,
                        timeout=20.0, max_retries=0)
        models = client.models.list()
        names = [m.id for m in getattr(models, "data", [])][:3]
        return {"ok": True,
                "detail": ("连通成功" + (f"，示例模型: {', '.join(names)}" if names else ""))}
    except Exception as e:  # noqa: BLE001 —— 探测失败要透出真实原因给用户
        msg = str(e).strip().replace("\n", " ")[:200]
        return {"ok": False, "detail": msg or type(e).__name__}
