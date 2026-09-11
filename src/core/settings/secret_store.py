# -*- coding: utf-8 -*-
"""引擎侧密钥存储（**不再碰系统层**）。2026-09-11 立，业主指令：「不要动系统层」。

## 为什么要有这个模块
此前「设置→API 配置」把 API Key 写进 Windows **系统层** `HKCU\\Environment`（与 `setx`
同落点）。后果（真实事故，用户两次踩到）：DSH（DeepSeek Harness）把**继承来的进程环境
变量**当成最高优先级且只读的凭据来源，并在启动时冻结环境快照 —— 引擎一保存 Key，
DSH 的模型设置页密钥输入框就被永久置灰、写它自己的凭据文件也被静默遮蔽。
业主裁决：**密钥存在引擎自己这里，不要动系统层**。本模块就是那个"引擎自己这里"。

## 存储形态
`<data_dir>/secrets.json`（`data_dir` 同 `src.core.config`，可用 `KS_DATA_DIR` 重定向）：

    {"version": 1, "scheme": "dpapi-user",
     "values": {"KS_LLM_API_KEY": "<base64 密文>", ...}}

**值一律加密**（含 base_url —— 它也可能带 `user:pass@` 之类），文件里只有**变量名**是明文，
所以整份文件被看到/被备份走也不直接泄漏 Key（DPAPI 绑当前 Windows 用户）。

## 加密
stdlib `ctypes` 调 `Crypt32.dll` 的 `CryptProtectData`/`CryptUnprotectData`
（**用户态 DPAPI，零新依赖**；不依赖 pywin32/cryptography 是否装了），
entropy 固定为 `_ENTROPY`（把密文绑到本应用，别的程序拿去也解不开），
flags 带 `CRYPTPROTECT_UI_FORBIDDEN`（服务化场景绝不弹 UI）。

**DPAPI 解不开的场合**（设计上的已知边界，不是 bug）：换 Windows 用户、换机器、
漫游/临时配置文件、以别的服务账户运行。此时 `read_value()` 返回空串且不抛异常
（引擎降级成"未配置 Key"，**绝不把密文当明文吐出去**），`write` 才会抛 `SecretStoreError`。

## 原子性与并发
写：同目录临时文件 → `flush` + `fsync` → `os.replace`（同卷原子替换），
所以任何时刻磁盘上都是"旧完整版"或"新完整版"，不会半写。
并发：`.<name>.lock`（`O_CREAT|O_EXCL`）串行化，锁超过 `_LOCK_STALE_S` 视为残留并回收
（崩溃遗留不会永久卡死）；拿不到锁时重试 `_LOCK_RETRY_S`，仍失败则如实抛错。
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import time
from ctypes import wintypes
from pathlib import Path

#: DPAPI 的附加熵：把密文绑到本应用（换 entropy 即解不开）
_ENTROPY = b"KnowledgeStation/secret-store/v1"
#: CRYPTPROTECT_UI_FORBIDDEN —— 后台进程绝不弹交互 UI
_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_LOCK_STALE_S = 10.0
_LOCK_RETRY_S = 3.0
_LOCK_POLL_S = 0.05
MAX_VALUE_LEN = 8192          # 单值上限（防把文件当仓库塞）


class SecretStoreError(RuntimeError):
    """写入/加密失败。读取失败一律降级为「未配置」，不抛给调用方。"""


# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
def store_path(data_dir: Path | None = None) -> Path:
    """密钥文件路径。`data_dir` 缺省时与 `src.core.config._default_data_dir` 同规则。

    这里刻意**不 import config**（config 会懒 import 本模块，避免环形依赖）；两条
    路径规则的一致性由 `tests/test_secret_store.py::test_store_path_matches_config_data_dir`
    守着——规则漂移会让测试红。
    """
    if data_dir is None:
        override = os.environ.get("KS_DATA_DIR")
        if override:
            data_dir = Path(override)
        else:
            appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            data_dir = Path(appdata) / "KnowledgeStation"
    return Path(data_dir) / "secrets.json"


# --------------------------------------------------------------------------
# DPAPI（ctypes，零新依赖）
# --------------------------------------------------------------------------
class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


class _BlobHolder:
    """持有源缓冲区，避免 create_string_buffer 被 GC 掉（悬垂指针是真实的坑）。"""

    def __init__(self, data: bytes):
        self._buf = ctypes.create_string_buffer(data, len(data))
        self.blob = _DATA_BLOB(len(data),
                               ctypes.cast(self._buf, ctypes.POINTER(ctypes.c_char)))


def dpapi_available() -> bool:
    """当前平台/环境是否具备用户态 DPAPI（用于给用户一句人话解释，而不是猜）。"""
    try:
        _open_libs()
        return True
    except Exception:
        return False


def _open_libs():
    if os.name != "nt":                       # 非 Windows 平台没有 crypt32
        raise OSError("非 Windows 平台没有 DPAPI")
    return ctypes.WinDLL("crypt32", use_last_error=True), \
        ctypes.WinDLL("kernel32", use_last_error=True)


def protect(plaintext: str, *, entropy: bytes = _ENTROPY) -> str:
    """明文 → base64(DPAPI 密文)。失败抛 SecretStoreError（**绝不写明文兜底**）。"""
    if not isinstance(plaintext, str):
        raise SecretStoreError("protect 只接受 str")
    try:
        crypt32, kernel32 = _open_libs()
        holder = _BlobHolder(plaintext.encode("utf-8"))
        ent = _BlobHolder(entropy)
        out = _DATA_BLOB()
        ok = crypt32.CryptProtectData(ctypes.byref(holder.blob), None,
                                      ctypes.byref(ent.blob), None, None,
                                      _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
        if not ok:
            raise SecretStoreError(f"CryptProtectData 失败: {ctypes.WinError(ctypes.get_last_error())}")
        try:
            return base64.b64encode(ctypes.string_at(out.pbData, out.cbData)).decode("ascii")
        finally:
            kernel32.LocalFree(out.pbData)
    except SecretStoreError:
        raise
    except OSError as e:            # 非 Windows / 无 crypt32
        raise SecretStoreError(f"DPAPI 不可用: {e}") from e


def unprotect(ciphertext_b64: str, *, entropy: bytes = _ENTROPY) -> str:
    """base64(DPAPI 密文) → 明文。解不开一律返回空串（降级为「未配置」）。"""
    if not ciphertext_b64:
        return ""
    try:
        crypt32, kernel32 = _open_libs()
        raw = base64.b64decode(ciphertext_b64, validate=True)
        holder = _BlobHolder(raw)
        ent = _BlobHolder(entropy)
        out = _DATA_BLOB()
        ok = crypt32.CryptUnprotectData(ctypes.byref(holder.blob), None,
                                        ctypes.byref(ent.blob), None, None,
                                        _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
        if not ok:
            return ""
        try:
            return ctypes.string_at(out.pbData, out.cbData).decode("utf-8", errors="replace")
        finally:
            kernel32.LocalFree(out.pbData)
    except Exception:
        return ""


# --------------------------------------------------------------------------
# 文件读写
# --------------------------------------------------------------------------
def _load(path: Path) -> dict:
    """读文件；损坏/缺失一律当空库（**不抛**，避免一个坏文件把引擎打死）。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "scheme": "dpapi-user", "values": {}}
    except Exception:
        return {"version": 1, "scheme": "dpapi-user", "values": {}}
    if not isinstance(raw, dict) or not isinstance(raw.get("values"), dict):
        return {"version": 1, "scheme": "dpapi-user", "values": {}}
    return raw


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)                  # 同卷原子替换
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


class _Lock:
    """跨进程串行化（O_EXCL + 陈旧回收）。"""

    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None

    def __enter__(self):
        deadline = time.monotonic() + _LOCK_RETRY_S
        while True:
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode("ascii"))
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > _LOCK_STALE_S:
                        self.path.unlink()      # 残留锁回收（持锁进程已崩）
                        continue
                except OSError:
                    continue
                if time.monotonic() >= deadline:
                    raise SecretStoreError(f"获取密钥存储锁超时: {self.path}")
                time.sleep(_LOCK_POLL_S)

    def __exit__(self, *a):
        if self.fd is not None:
            try:
                os.close(self.fd)
            finally:
                self.fd = None
        try:
            self.path.unlink()
        except OSError:
            pass
        return False


def read_value(name: str, data_dir: Path | None = None) -> str:
    """读一个值；任何异常 → 空串（引擎降级为「未配置」，绝不因存储问题崩）。"""
    try:
        payload = _load(store_path(data_dir))
        cipher = payload.get("values", {}).get(name)
        if not isinstance(cipher, str):
            return ""
        return unprotect(cipher)
    except Exception:
        return ""


def has_value(name: str, data_dir: Path | None = None) -> bool:
    """是否存过该名字（**只看有没有密文，不解密**），供迁移/状态显示用。"""
    try:
        payload = _load(store_path(data_dir))
        return isinstance(payload.get("values", {}).get(name), str)
    except Exception:
        return False


def write_values(values: dict[str, str | None], data_dir: Path | None = None) -> None:
    """合并写入（`None` = 删除该名字）。

    加密失败**整体中止**，不落任何半成品；返回值只保证"要么都写要么都没写"。
    """
    if not values:
        return
    for name, val in values.items():
        if val is not None and len(val) > MAX_VALUE_LEN:
            raise SecretStoreError(f"{name} 超长（>{MAX_VALUE_LEN}），拒绝写入")
    path = store_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _Lock(path.with_name(path.name + ".lock")):
        payload = _load(path)                 # 锁内重读，避免覆盖并发写
        current = dict(payload.get("values", {}))
        for name, val in values.items():
            if val is None:
                current.pop(name, None)
            else:
                current[name] = protect(val)   # 抛错则整体不写
        payload["values"] = current
        payload["version"] = payload.get("version", 1)
        payload["scheme"] = "dpapi-user"
        _atomic_write(path, payload)


def stored_names(data_dir: Path | None = None) -> list[str]:
    """存储里已有哪些名字（**不解密**）。"""
    try:
        return sorted(_load(store_path(data_dir)).get("values", {}).keys())
    except Exception:
        return []
