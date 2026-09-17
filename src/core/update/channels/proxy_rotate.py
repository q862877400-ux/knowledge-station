# -*- coding: utf-8 -*-
"""代理轮换（IP 旋转）与请求间隔随机化（2026-08-27 实测定型）。

背景：ndls.cnis.ac.cn 的 Jiasule WAF 在请求过密 / 单 IP 超阈值后进入验证码惩罚期
（实测 100% 拦截、0.1s 内返回 code 5320、持续 30min+）。对策：
1) 被限即换出口 IP —— 本地 Clash Verge / mihomo 的 Windows named pipe RESTful API
   切换代理节点（不同国家落地 → 不同出口 IP），或静态代理列表文件兜底；
2) 请求间隔随机化 —— 均匀分布 [min_s, max_s]，打破固定节奏的风控模式识别。

Clash Verge（mihomo v1.19.29 实测）：
- named pipe: \\\\.\\pipe\\verge-mihomo（HTTP/1.1 请求 + chunked 响应）
- GET  /version | /proxies | /proxies/{group}
- PUT  /proxies/{group}  body {"name": "<节点或组>"} —— 切换即生效
- 出口统一 mixed-port 127.0.0.1:7897，换节点 = 换出口 IP
- rule 模式下实际出口由路由入口组（🚀节点选择 等 Selector）决定：
  把它切到不同国家组即可换 IP 段

组件：
- ClashRotator —— 切 Clash 节点（优先，零成本）
- ProxyListPool —— 静态代理列表文件兜底（数据区，用户维护，每行一个 proxy URL）
- ProxyCurlTransport —— 带代理的 curl_cffi transport（新 session = 新 cookie）
- random_gap(min_s, max_s) —— 请求间隔随机化（均匀分布）
"""
from __future__ import annotations

import json
import random
import time
import urllib.parse
from pathlib import Path
from typing import Any

#: verge-mihomo named pipe（Clash Verge Rev 默认；可被环境变量/参数覆盖）
DEFAULT_PIPE = r"\\.\pipe\verge-mihomo"
#: Clash mixed-port 出口（config.yaml 实测）
DEFAULT_PROXY_PORT = 7897
#: 路由入口组候选（rule 模式下切它即换实际出口；按常见订阅顺序）
ROUTE_GROUPS = ("🚀节点选择", "🐟漏网之鱼", "GLOBAL")
#: 具体国家落地组（轮换出口 IP 段）
COUNTRY_GROUPS = ("🇯🇵日本节点", "🇸🇬狮城节点", "🇺🇸美国节点", "♻️自动选择")


def random_gap(min_s: float, max_s: float) -> float:
    """请求间隔随机化：均匀分布 [min_s, max_s]（max_s<=min_s 时返回固定值）。"""
    if max_s <= min_s:
        return min_s
    return random.uniform(min_s, max_s)


# ---------------------------------------------------------------- named pipe HTTP
def _decode_chunked(payload: bytes) -> bytes:
    """HTTP chunked transfer 解码（mihomo pipe 响应实测为 chunked）。"""
    out = bytearray()
    i = 0
    while i < len(payload):
        j = payload.find(b"\r\n", i)
        if j < 0:
            break
        size = int(payload[i:j], 16)
        if size <= 0:
            break
        out += payload[j + 2: j + 2 + size]
        i = j + 2 + size + 2
    return bytes(out)


def pipe_http(pipe: str, method: str, path: str, body: str | None = None,
              timeout_s: float = 5.0) -> tuple[int, Any]:
    """经 Windows named pipe 调 mihomo RESTful API。

    返回 (http_status, json|str)。连接失败抛 ConnectionError（调用方判定不可用）。
    """
    body_bytes = body.encode("utf-8") if body else None
    req_head = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n"
    if body_bytes:
        # Content-Length 必须是 UTF-8 字节数（emoji 组名/节点名多字节，字符数会截断 body）
        req_head += f"Content-Type: application/json\r\nContent-Length: {len(body_bytes)}\r\n"
    req_head += "\r\n"
    try:
        with open(pipe, "rb+", buffering=0) as f:
            f.write(req_head.encode("utf-8") + (body_bytes or b""))
            chunks = []
            while True:
                data = f.read(65536)
                if not data:
                    break
                chunks.append(data)
    except OSError as e:
        raise ConnectionError(f"named_pipe_unavailable: {pipe} ({e})") from e
    raw = b"".join(chunks)
    head, _, payload = raw.partition(b"\r\n\r\n")
    try:
        status = int(head.split(b" ")[1]) if b" " in head else 0
    except ValueError:
        status = 0
    if "chunked" in head.decode("utf-8", "replace").lower():
        payload = _decode_chunked(payload)
    text = payload.decode("utf-8", "replace")
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


# ---------------------------------------------------------------- Clash 旋转
class ClashRotator:
    """通过 verge-mihomo named pipe 切换代理节点，换出口 IP。

    rotate() 轮换策略：把路由入口组（🚀节点选择 优先）切到不同国家落地组
    （日本→狮城→美国→自动选择 round-robin），国家组为 URLTest 自动选节点；
    入口组不可用时回退切 GLOBAL/第一个 Selector 组。
    """

    def __init__(self, pipe: str = DEFAULT_PIPE,
                 proxy_port: int = DEFAULT_PROXY_PORT) -> None:
        self.pipe = pipe
        self.proxy_url = f"http://127.0.0.1:{proxy_port}"
        self._groups: list[str] = []
        self._route_group: str | None = None
        self._country_i = -1
        self._last_switch_at = 0.0

    # ---------------------------------------------------------- 探测
    def available(self) -> bool:
        """pipe 可达且能拿到代理列表（Clash 运行中）。"""
        try:
            st, body = pipe_http(self.pipe, "GET", "/proxies")
        except (ConnectionError, OSError):
            return False
        if st != 200 or not isinstance(body, dict):
            return False
        proxies = body.get("proxies") or {}
        self._groups = [k for k, v in proxies.items()
                        if isinstance(v, dict) and v.get("type") in
                        ("Selector", "URLTest", "Fallback")]
        for name in ROUTE_GROUPS:
            if name in proxies and proxies[name].get("type") == "Selector":
                self._route_group = name
                break
        if self._route_group is None:
            self._route_group = next((g for g in self._groups
                                      if proxies[g].get("type") == "Selector"), None)
        return bool(self._groups)

    def _switch(self, group: str, target: str) -> bool:
        """切 group 的当前选择到 target（节点或组）；成功返回 True。"""
        path = "/proxies/" + urllib.parse.quote(group, safe="")
        st, body = pipe_http(self.pipe, "PUT", path,
                             body=json.dumps({"name": target}, ensure_ascii=False))
        return st in (200, 204)

    def rotate(self) -> str | None:
        """切到下一个国家落地组（round-robin），返回代理出口 URL；失败返回 None。

        切换后留 0.8s 让 mihomo 完成拨号（避免换组瞬间旧连接命中）。
        """
        if not self._groups:
            return None
        if time.monotonic() - self._last_switch_at < 0.5:
            time.sleep(0.5)
        # 国家组 round-robin；组内已由 URLTest 自动选节点
        hits = [g for g in COUNTRY_GROUPS if g in self._groups]
        pool = hits or self._groups
        self._country_i = (self._country_i + 1) % len(pool)
        target = pool[self._country_i]
        if self._route_group and self._route_group != target:
            if not self._switch(self._route_group, target):
                return None
        else:
            # 无路由入口组时直接切目标组本身（Selector 场景）
            proxies_ok = True
            try:
                st, body = pipe_http(self.pipe, "GET", "/proxies")
                p = (body or {}).get("proxies", {}).get(target) or {}
                proxies_ok = p.get("type") in ("Selector", "URLTest", "Fallback")
            except (ConnectionError, OSError):
                proxies_ok = False
            if proxies_ok:
                self._switch(target, str((p.get("now") or "")))
        self._last_switch_at = time.monotonic()
        time.sleep(0.8)
        return self.proxy_url


# ---------------------------------------------------------------- 静态代理文件池
class ProxyListPool:
    """静态代理列表（数据区文件，每行一个 proxy URL，空行/# 注释忽略）。

    文件示例（用户自行维护）：
        http://user:pass@host:8080
        socks5://127.0.0.1:1080
    """

    def __init__(self, path: str | Path) -> None:
        self._items: list[str] = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self._items.append(line)
        self._i = -1
        if not self._items:
            raise ValueError(f"proxies 文件无有效条目: {path}")

    def rotate(self) -> str:
        self._i = (self._i + 1) % len(self._items)
        return self._items[self._i]

    def __len__(self) -> int:
        return len(self._items)


# ---------------------------------------------------------------- 带代理 transport
class ProxyCurlTransport:
    """带代理的 curl_cffi transport（新实例 = 新 session = 新 cookie）。

    与 base.CurlCffiTransport 同契约：fetch(url, **kw) -> (status, body)。
    """

    def __init__(self, proxy: str) -> None:
        from curl_cffi import requests as cffi_requests
        self._session: Any = cffi_requests.Session(impersonate="chrome", proxy=proxy)

    def fetch(self, url: str, **kw: Any) -> tuple[int, Any]:
        timeout = kw.pop("timeout", 30)
        method = str(kw.pop("method", "get") or "get").lower()
        json_body = kw.pop("json", None)
        if method == "post":
            resp = self._session.post(url, json=json_body, timeout=timeout, **kw)
        else:
            resp = self._session.get(url, timeout=timeout, **kw)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text

    def fetch_bytes(self, url: str, **kw: Any) -> tuple[int, bytes]:
        timeout = kw.pop("timeout", 30)
        resp = self._session.get(url, timeout=timeout, **kw)
        return resp.status_code, resp.content

    def fetch_page(self, url: str, **kw: Any) -> tuple[int, dict[str, str], str, bytes]:
        """与 `base.CurlCffiTransport.fetch_page` 同契约（采集侧要 Content-Type 与真实字节）。"""
        timeout = kw.pop("timeout", 30)
        resp = self._session.get(url, timeout=timeout, **kw)
        return resp.status_code, {str(k).lower(): str(v) for k, v in resp.headers.items()}, \
            resp.text, resp.content


def build_rotator(proxies_file: str | None = None) -> Any | None:
    """按配置构建旋转器：--proxies 文件优先，否则尝试 Clash；都不可用返回 None。"""
    if proxies_file:
        try:
            return ProxyListPool(proxies_file)
        except (OSError, ValueError) as e:
            print(f"[rotate] 静态代理文件不可用: {e}", flush=True)
            return None
    rot = ClashRotator()
    if rot.available():
        print(f"[rotate] Clash 节点旋转可用（路由入口组={rot._route_group}，"
              f"组数={len(rot._groups)}）", flush=True)
        return rot
    print("[rotate] 无可用 IP 旋转源（未找到 Clash pipe，也未提供 --proxies 文件）", flush=True)
    return None
