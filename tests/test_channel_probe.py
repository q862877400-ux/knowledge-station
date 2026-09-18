# -*- coding: utf-8 -*-
"""渠道健康探针测试（`src/core/update/channel_probe.py`，§11.0 R3）。

守四件（每条都由 R1 的实测教训换来）：
  1. **"HTTP 200 ≠ 有数据"**：正文层也要判（`{"code":500}` / `{"msg":"系统异常"}` / 没有锚点）；
  2. **失败要分级**（WAF/端点没了/5xx/超时/传输异常），面板上"不可抓"必须带原因码；
  3. **`method` 必须真的传下去**（dry-run 实测：漏传就静默变 GET，而两层都是 HTTP 200）；
  4. **探针不落库是默认以外的显式选择**：`persist=False` 一个字都不写。

全部离线（假 transport），不触网——真机那一次由 `var/tmp/probe-dry-run.py` 留证据。
"""
from __future__ import annotations

import pytest

from src.core.storage import channel_repo as cr
from src.core.update import channel_probe as cp


class FakeTransport:
    """假传输：记录调用并回放预设的 `(status, body)` 或抛预设异常。"""

    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def fetch(self, url, **kw):
        self.calls.append((url, kw))
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def _clean(db):
    db.execute("DELETE FROM update_channel")
    db.commit()
    yield


class TestClassify:
    """判据表：这一组就是"有效性"三个字的定义。"""

    @pytest.mark.parametrize("status,body,expect,state,code", [
        # 正常
        (200, "…安全生产法…", "安全生产法", "ok", None),
        # 200 但没有锚点 = 本领域最常见的假可用（G14）
        (200, "<html>当前第0页，每页0条，共0条</html>", "标准", "suspicious", "probe_no_anchor"),
        # 200 但没配锚点 = 如实说"没做语义判定"
        (200, "whatever", None, "unknown", "no_anchor_configured"),
        # 正文层报错（dry-run 实测两种）
        (200, '{"msg": "系统异常", "code": 500}', "查询成功", "down", "api_error"),
        (200, '{"msg": "Request method \'GET\' not supported", "code": 500}', None, "down", "api_error"),
        # 反爬 / 死链 / 5xx / 其它
        (412, "blocked", None, "down", "blocked_by_waf"),
        (403, "forbidden", None, "down", "blocked_by_waf"),
        (404, "gone", None, "down", "endpoint_gone"),
        (500, "boom", None, "down", "server_error"),
        (302, "moved", None, "down", "http_302"),
    ])
    def test_判据表(self, status, body, expect, state, code):
        got_state, got_code, _ = cp._classify(status, body, expect)
        assert (got_state, got_code) == (state, code)

    def test_正文报错的措辞要提示先怀疑请求体(self):
        """实测教训：flk 的 500 是我**请求体**不对，不是渠道坏 —— 措辞必须能分开这两件事。"""
        _, _, msg = cp._classify(200, '{"msg": "系统异常", "code": 500}', "查询成功")
        assert "请求体" in msg


class TestProbeChannel:
    def test_成功路径带延迟与证据头(self):
        t = FakeTransport((200, "…GB 30871-2022…"))
        out = cp.probe_channel("c", {"url": "https://x/", "expect": "30871"}, transport=t)
        assert out["state"] == "ok" and out["http"] == 200
        assert out["latency_ms"] is not None and out["latency_ms"] >= 0
        assert "30871" in out["body_head"]

    def test_dict_正文会被序列化后判锚点(self):
        t = FakeTransport((200, {"total": 5, "rows": [1, 2]}))
        out = cp.probe_channel("c", {"url": "https://x/", "expect": "rows"}, transport=t)
        assert out["state"] == "ok"

    def test_超时与传输异常都分级不抛(self):
        t = FakeTransport(error=TimeoutError("slow"))
        out = cp.probe_channel("c", {"url": "https://x/", "expect": "a"}, transport=t)
        assert (out["state"], out["error_code"]) == ("down", "timeout")
        t2 = FakeTransport(error=ConnectionResetError("reset"))
        out2 = cp.probe_channel("c", {"url": "https://x/", "expect": "a"}, transport=t2)
        assert (out2["state"], out2["error_code"]) == ("down", "transport_error")

    def test_没有_url_的渠道记_unknown_而不是_失败(self):
        out = cp.probe_channel("c", {}, transport=FakeTransport((200, "x")))
        assert (out["state"], out["error_code"]) == ("unknown", "no_probe_url")

    def test_POST_的_method_必须真的传下去(self):
        """⚠ dry-run 实测缺陷：漏传 `method` ⇒ transport 走 GET，而 flk/dbba **两层都回 200**
        ⇒ 只看状态码会把"方法错了"判成"渠道健康"。这条用例钉住这个 kwarg。"""
        t = FakeTransport((200, '{"records": []}'))
        cp.probe_channel("c", {"url": "https://x/", "method": "post",
                               "form": {"a": "1"}, "expect": "records"}, transport=t)
        _, kw = t.calls[0]
        assert kw.get("method") == "post"
        assert kw.get("data") == {"a": "1"}

    def test_POST_json_体与_headers_都传下去(self):
        t = FakeTransport((200, '{"msg": "查询成功"}'))
        cp.probe_channel("c", {"url": "https://x/", "method": "post", "json": {"pageNum": 1},
                               "headers": {"Referer": "https://x/search"},
                               "expect": "查询成功"}, transport=t)
        _, kw = t.calls[0]
        assert kw["method"] == "post" and kw["json"] == {"pageNum": 1}
        assert kw["headers"] == {"Referer": "https://x/search"}


class TestProbeChannels:
    def _seed(self, tmp_path, targets):
        import json
        p = tmp_path / "t.json"
        p.write_text(json.dumps({"targets": targets}, ensure_ascii=False), encoding="utf-8")
        cr.upsert_channel("c:ok", {"name": "甲", "category": "law"})
        cr.upsert_channel("c:bad", {"name": "乙", "category": "law"})
        return p

    def test_persist_true_写台账_persist_false_一个字都不写(self, tmp_path):
        p = self._seed(tmp_path, {
            "c:ok": {"url": "https://x/", "expect": "hit"},
            "c:bad": {"url": "https://y/", "expect": "hit"},
        })
        t = FakeTransport((200, "no anchor here"))
        dry = cp.probe_channels(path=p, transport=t, persist=False)
        assert dry["counts"] == {"suspicious": 2}
        assert cr.get_channel("c:ok")["state"] == "unknown"      # dry-run 不落库
        assert cr.get_channel("c:ok")["last_try_at"] is None

        cp.probe_channels(path=p, transport=FakeTransport((200, "hit!")), persist=True)
        row = cr.get_channel("c:ok")
        assert row["state"] == "ok" and row["last_try_at"] and row["last_ok_at"]
        assert row["latency_ms"] is not None

    def test_没配目标的渠道不在默认探测集里(self, tmp_path):
        p = self._seed(tmp_path, {"c:ok": {"url": "https://x/", "expect": "hit"}})
        out = cp.probe_channels(path=p, transport=FakeTransport((200, "hit")), persist=False)
        assert out["probed"] == 1
        assert "c:bad" in out["without_target"]

    def test_指定不存在的渠道要抛(self, tmp_path):
        p = self._seed(tmp_path, {"c:ok": {"url": "https://x/", "expect": "hit"}})
        with pytest.raises(ValueError, match="channel_not_found"):
            cp.probe_channels(ids=["c:nope"], path=p, transport=FakeTransport((200, "hit")))

    def test_目标表格式坏要抛(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="targets"):
            cp.load_targets(p)


class TestShippedProbes:
    """随包发布的探针目标表（`src/core/update/channel_probes.json`）的契约。"""

    def test_每个目标都有_url_与出处(self):
        targets = cp.load_targets()
        assert len(targets) >= 5, "R3 至少给最高价值的几条配上探针"
        for cid, t in targets.items():
            assert t.get("url", "").startswith("http"), f"{cid} 没有探针 URL"
            assert t.get("evidence"), f"{cid} 缺 evidence（锚点必须来自实测，不是想象）"

    def test_目标指向的渠道都在种子里(self):
        """探针目标不许指向一个台账里不存在的渠道（否则永远探不到、也没人发现）。"""
        ids = {r["channel_id"] for r in cr.load_seed()}
        missing = [cid for cid in cp.load_targets() if cid not in ids]
        assert not missing, f"这些探针目标不在渠道种子里：{missing}"
