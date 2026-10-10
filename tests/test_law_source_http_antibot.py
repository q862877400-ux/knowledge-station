"""law_source HTTP 层的反爬挑战处理测试（spec 006）。

**为什么需要这组测试**：2026-10-10 实测发现 flk 站点在被突发限速时返回
**HTTP 200 + text/html** 的 JS 挑战页（不是 4xx/5xx）⇒
`raise_for_status()` 放行、`resp.json()` 抛 JSONDecodeError ⇒
挑战被当成普通错误，只用 0.8s/1.6s 重试 ⇒ **必然失败**。
实测该挑战约 1 分钟内自愈（research.md R6）。

全程 mock，零真实请求。
"""
from __future__ import annotations

import pytest
import requests

from src.core.knowledge.law_source import http as H

CHALLENGE = ('<!DOCTYPE HTML>\n<html><head><meta charset="utf-8"></head>'
             '<body><noscript><h1><strong>Please enable JavaScript and refresh'
             ' the page.</strong></h1></noscript></body></html>')


class _Resp:
    """最小响应替身：只要 status_code / headers / text / json()。"""

    def __init__(self, text: str, ctype: str = "text/html", code: int = 200):
        self.status_code = code
        self.headers = {"Content-Type": ctype}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        import json as _j
        return _j.loads(self.text)


def test_looks_like_antibot_detects_challenge():
    assert H._looks_like_antibot(CHALLENGE, "text/html") is True


def test_looks_like_antibot_ignores_json():
    """Content-Type 是 json 就不该被当挑战（即使正文里恰好含那串字）。"""
    assert H._looks_like_antibot('{"x":"Please enable JavaScript"}',
                                 "application/json") is False


def test_looks_like_antibot_ignores_normal_html():
    """非 JSON 声明的响应一律视为被挡（站点有时返回别的 HTML 页，无特征串）。"""
    assert H._looks_like_antibot("<html><body>hello</body></html>",
                                 "text/html") is True


def test_looks_like_antibot_empty_body_is_blocked():
    """空正文也算没拿到数据 ⇒ 走重试，而不是当场 JSONDecodeError。"""
    assert H._looks_like_antibot("", "text/html") is True


def test_json_or_challenge_raises_antibot():
    with pytest.raises(H.AntibotChallenge):
        H._json_or_challenge(_Resp(CHALLENGE))


def test_json_or_challenge_passes_json():
    out = H._json_or_challenge(_Resp('{"code":200,"total":7}', "application/json"))
    assert out["total"] == 7


def test_fetch_json_retries_through_challenge(monkeypatch):
    """★ 挑战页之后成功 ⇒ fetch_json 应当**穿过挑战**拿到 JSON（不是直接失败）。"""
    seq = [_Resp(CHALLENGE), _Resp(CHALLENGE),
           _Resp('{"code":200,"total":30910}', "application/json")]
    calls = {"n": 0}

    def fake_request(method, url, **kw):
        i = calls["n"]
        calls["n"] += 1
        return seq[min(i, len(seq) - 1)]

    monkeypatch.setattr(H.requests, "request", fake_request)
    monkeypatch.setattr(H.time, "sleep", lambda _s: None)      # 不真等
    out = H.fetch_json("https://flk.npc.gov.cn/x")
    assert out["total"] == 30910
    assert calls["n"] == 3


def test_fetch_json_uses_long_backoff_for_challenge(monkeypatch):
    """★ 挑战页必须走**秒级**退避（亚秒退避对它无效）——断言 sleep 参数。"""
    slept: list[float] = []
    monkeypatch.setattr(H.requests, "request",
                        lambda *a, **kw: _Resp(CHALLENGE))
    monkeypatch.setattr(H.time, "sleep", lambda s: slept.append(s))
    with pytest.raises(RuntimeError):
        H.fetch_json("https://flk.npc.gov.cn/x")
    assert slept, "一次都没睡？"
    assert max(slept) >= 5.0, f"退避太短，挑战不可能自愈: {slept}"
    assert any(s in H._ANTIBOT_BACKOFF for s in slept), \
        f"没走反爬退避常量: {slept}"
    # 2026-10-10 追加实测：持续猛打后封禁会变长 ⇒ 必须留分钟级退避
    assert max(H._ANTIBOT_BACKOFF) >= 60.0, "退避上限不足 1 分钟，长封禁扛不住"


def test_fetch_json_still_raises_on_real_error(monkeypatch):
    """真 5xx 不该被当挑战处理（保持既有语义：抛 RuntimeError）。"""
    monkeypatch.setattr(H.requests, "request",
                        lambda *a, **kw: _Resp("boom", "text/html", code=500))
    monkeypatch.setattr(H.time, "sleep", lambda _s: None)
    with pytest.raises(RuntimeError):
        H.fetch_json("https://flk.npc.gov.cn/x")


def test_mixed_failure_still_uses_long_backoff(monkeypatch):
    """★ 混合失败序列（挑战、挑战、连接错）**必须仍走长退避轮**。

    这是独立复核 2026-10-10 的 P2-3：第一版判据
    `isinstance(e.__cause__, AntibotChallenge) or "反爬挑战页" in str(e)` 两个分支都不可靠 ——
    `_retry` 没有 `from`（`__cause__` 恒 None），而字符串看的是**最后一条**错误，
    所以序列末位若不是挑战，**长退避整轮被漏掉**。
    """
    seq = [_Resp(CHALLENGE), _Resp(CHALLENGE), ConnectionError("网络断了")]
    calls = {"n": 0}

    def fake_request(method, url, **kw):
        i = calls["n"]
        calls["n"] += 1
        item = seq[min(i, len(seq) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    slept: list[float] = []
    monkeypatch.setattr(H.requests, "request", fake_request)
    monkeypatch.setattr(H.time, "sleep", lambda s: slept.append(s))
    with pytest.raises(RuntimeError):
        H.fetch_json("https://flk.npc.gov.cn/x")
    # 必须出现过反爬退避常量里的等待（否则长退避轮被漏掉）
    assert any(s in H._ANTIBOT_BACKOFF for s in slept), \
        f"混合序列漏掉了长退避轮，实际 sleep={slept}"


def test_pure_network_error_does_not_use_antibot_backoff(monkeypatch):
    """★ 反向：全程都不是挑战（纯连接错）⇒ **不该**拖进分钟级长退避。"""
    monkeypatch.setattr(H.requests, "request",
                        lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("断了")))
    slept: list[float] = []
    monkeypatch.setattr(H.time, "sleep", lambda s: slept.append(s))
    with pytest.raises(RuntimeError):
        H.fetch_json("https://flk.npc.gov.cn/x")
    assert not any(s in H._ANTIBOT_BACKOFF for s in slept), \
        f"纯网络错不该走反爬退避: {slept}"


def test_whitelist_rejection_not_retried(monkeypatch):
    """非白名单域必须**当场拒绝**、不重试（策略拒绝语义透传）。"""
    slept: list[float] = []
    monkeypatch.setattr(H.time, "sleep", lambda s: slept.append(s))
    with pytest.raises(ValueError):
        H.fetch_json("https://evil.example.com/x")
    assert slept == []
