"""law_source 共享 HTTP 层：域白名单 / UA / 限速 / 重试 / 文件校验。

单一事实：本模块是「官方来源」策略的唯一出口——所有抓取请求必须经
fetch_json / download_file 发出；域白名单在此强制执行，杜绝第三方站。
"""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests
import urllib3

# 官方站证书链问题已知（参考实现同款 verify=False）；只抑制告警，不改变校验策略
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- 官方来源白名单（方案 LAW-SOURCE-PLAN §0）----
ALLOWED_HOSTS = frozenset({
    "flk.npc.gov.cn",          # 国家法律法规数据库（含 OSS 签名下载域 flkoss.obs-bj2.cucloud.cn 由签名 URL 携带，校验时放行 OBS 域）
    "sousuo.www.gov.cn",       # 国务院政策文件库搜索后端
    "www.gov.cn",              # 政策文件详情页 / 下载
    "gov.cn",                  # 政府网子域（详情页内嵌链接兜底）
    "flkoss.obs-bj2.cucloud.cn",  # flk 官方 OSS 文件存储（签名 URL）
})
# OBS 域名携带路径前缀 prod/...（详情 ossFile 路径相对 flk.npc.gov.cn 的直链不在白名单时拒绝）

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
       " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 请求间隔（秒），遵守官方公开接口使用节奏，避免影响服务
_MIN_INTERVAL = 0.6
_last_ts: dict[str, float] = {}
_lock = threading.Lock()


def _pace(host: str) -> None:
    with _lock:
        last = _last_ts.get(host, 0.0)
        gap = _MIN_INTERVAL - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)
        _last_ts[host] = time.monotonic()


def check_host(url: str) -> str:
    """域白名单校验；返回 host。非白名单域抛 ValueError（策略拒绝，不静默放行）。"""
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"来源域不在白名单，拒绝访问: {host}（仅允许 {sorted(ALLOWED_HOSTS)}）")
    return host


def _retry(fn: Callable[[], Any], tries: int = 3, desc: str = "请求") -> Any:
    last_err: Exception | None = None
    for i in range(tries):
        try:
            return fn()
        except ValueError:
            raise  # 策略拒绝（域白名单等）不重试、不包装，语义透传
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i < tries - 1:
                time.sleep(0.8 * (2 ** i))
    raise RuntimeError(f"{desc} 失败（重试 {tries} 次）: {last_err}")


def fetch_json(url: str, *, method: str = "GET", json_body: dict | None = None,
               params: dict | None = None, referer: str | None = None,
               timeout: int = 30) -> dict:
    """白名单内 JSON 请求（搜索/详情/下载链接接口）。"""
    host = check_host(url)
    headers = {"User-Agent": _UA, "Accept": "application/json"}
    if referer:
        headers["Referer"] = referer

    def _do() -> dict:
        _pace(host)
        resp = requests.request(method, url, json=json_body, params=params,
                                headers=headers, timeout=timeout, verify=False)
        resp.raise_for_status()
        return resp.json()

    out = _retry(_do, desc=f"{method} {url}")
    if not isinstance(out, dict):
        raise ValueError(f"非 JSON 对象响应: {url}")
    return out


def download_file(url: str, dest: Path, *, expected: str | None = None,
                  referer: str | None = None, timeout: int = 120) -> Path:
    """白名单内文件下载；expected 指定内容签名（'docx'|'pdf'）做魔数校验。"""
    host = check_host(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": _UA}
    if referer:
        headers["Referer"] = referer

    def _do() -> Path:
        _pace(host)
        with requests.get(url, headers=headers, timeout=timeout, verify=False,
                          stream=True) as resp:
            resp.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
        if expected:
            sig = _magic(tmp, expected)
            if not sig:
                tmp.unlink(missing_ok=True)
                raise ValueError(f"文件魔数校验失败（期望 {expected}）: {url}")
        tmp.rename(dest)
        return dest

    return _retry(_do, desc=f"下载 {url}")


_MAGIC = {
    "docx": (b"PK\x03\x04",),        # ZIP 容器（docx 为 OOXML ZIP）
    "pdf": (b"%PDF",),
    "ofd": (b"PK\x03\x04",),
}


def _magic(path: Path, kind: str) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return False
    return any(head.startswith(m) for m in _MAGIC.get(kind, ()))


