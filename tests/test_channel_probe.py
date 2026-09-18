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

import json

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


class TestMinLinks:
    """R6 新增判据：**页面里有没有内容链接**（JS 空壳的照妖镜）。

    实测来源：应急管理部频道页 HTTP 200 / 471 字节 / **0 链接**（R5a），而它的 `<title>`
    是好的——只看状态码或只看标题都会判成"健康"，真相却是这里什么都抓不到。
    R6a 批量实测又发现 12 条渠道是同一形态，所以这条判据必须进判据表。
    """

    def test_链接数不足判可疑并点名(self):
        state, code, msg = cp._classify(200, "<html>只有壳，没有内容</html>", "只有壳",
                                        min_links=1)
        assert (state, code) == ("suspicious", "probe_too_few_links")
        assert "0 个链接" in msg and "≥1" in msg

    def test_链接数够且锚点在则通过(self):
        html = "只有壳" + '<a href="/x">x</a>'
        assert cp._classify(200, html, "只有壳", min_links=1)[:2] == ("ok", None)

    def test_两个期望可以叠加_任一不满足即不算通过(self):
        """锚点对、但页面没链接（或反之）都不算过——消息要把两条都列出来。"""
        html = "<html>标题在<a href='/a'>a</a></html>"
        _, code, msg = cp._classify(200, html, "锚点不在", min_links=5)
        assert code == "probe_no_anchor"
        assert "没有预期锚点" in msg and "只有 1 个链接" in msg

    def test_链接计数大小写与换行都算(self):
        html = '<A HREF="/a">a</A><a\nhref="/b">b</a>'
        assert cp._count_links(html) == 2

    def test_只配_url_不配期望仍记_unknown(self):
        assert cp._classify(200, "<html>x</html>", None)[:2] == ("unknown", "no_anchor_configured")

    def test_429_是限流不是死(self):
        """R6a 实测：GitHub 上两条被 429，判 down 会让业主以为该换渠道。"""
        state, code, msg = cp._classify(429, "Too many requests", None)
        assert (state, code) == ("suspicious", "rate_limited")
        assert "稍后重试" in msg

    @pytest.mark.parametrize("bad", [0, -1, "1", True, 1.5])
    def test_坏_min_links_在读表时就要抛(self, tmp_path, bad):
        """`probe_channel` 的契约是**不抛异常**——所以配置错误必须在读表时响亮报错。"""
        p = tmp_path / "t.json"
        p.write_text('{"targets": {"c:x": {"url": "https://e.com", "min_links": %s}}}'
                     % (f'"{bad}"' if isinstance(bad, str) else
                        ("true" if bad is True else bad)), encoding="utf-8")
        with pytest.raises(ValueError, match="min_links"):
            cp.load_targets(p)

    @pytest.mark.parametrize("target,pat", [
        ("https://e.com", "必须是对象"),                       # target 写成字符串
        ({"url": "/relative"}, "http"),                        # 没有可抓的绝对地址
        ({"url": "http"}, "绝对地址"),                          # ⚠ 只有 scheme：过表会伪装成"渠道挂了"
        ({"url": "httpfoo"}, "绝对地址"),
        ({"url": "ftp://e.com"}, "绝对地址"),
        ({"url": "https://"}, "绝对地址"),                      # 没有 netloc
        ({"url": "https://e.com", "method": "delete"}, "method"),
        ({"url": "https://e.com", "expect": ""}, "expect"),     # ⛔ 假绿：'' in body 恒真
        ({"url": "https://e.com", "expect": "   "}, "expect"),
        ({"url": "https://e.com", "expect": 123}, "expect"),
        ({"url": "https://e.com", "form": ["a"]}, "form"),
        ({"url": "https://e.com", "json": "x"}, "json"),        # 只允许对象/数组
        ({"url": "https://e.com", "headers": ["a"]}, "headers"),
        # N3：headers 只校验"是对象"时，值为 list/dict 会过表 ⇒ 记成 down（配置错伪装成渠道挂）
        ({"url": "https://e.com", "headers": {"X": ["a"]}}, "header 值"),
        ({"url": "https://e.com", "headers": {"X": {"a": 1}}}, "header 值"),
        ({"url": "https://e.com", "headers": {"X": 1}}, "header 值"),
        ({"url": "https://e.com", "headers": {"X": "v\r\nInjected: 1"}}, "header 值"),
        ({"url": "https://e.com", "headers": {"X\n": "v"}}, "header 名"),
        ({"url": "https://e.com", "headers": {"A:B": "v"}}, "header 名"),
        # 拼错的键：过去是**静默忽略**（比"拒 null"更值的一刀，b28-fix 的建议）
        ({"url": "https://e.com", "expext": "x"}, "不认识的键"),
        # NEW-B（b28-fix2）：netloc 非空还不够——空 host / 非法端口都会在真请求里变成 down
        ({"url": "http://:80/"}, "绝对地址"),
        ({"url": "http://e.com:99999/"}, "端口不合法"),
        ({"url": "http://e.com:port/"}, "端口不合法"),
        # NEW-A（b28-fix2，本轮唯一真反例）：非 ASCII 头值过表后真请求抛 UnicodeEncodeError
        ({"url": "https://e.com", "headers": {"X": "中文值"}}, "ASCII"),
        ({"url": "https://e.com", "headers": {"X": "a\x85b"}}, "ASCII"),
    ])
    def test_目标形状坏也在读表时抛(self, tmp_path, target, pat):
        """独立复核 b28 / b28-fix 的发现：原先只校验 `min_links` ⇒ 字符串 target **静默过表**，
        随后 `probe_channel` 抛 AttributeError；`expect=123` 抛 TypeError；
        修完一轮又抓到"不抛但**误分类**"的三类（url 前缀判断 / headers 值不校验 / JSON 数组被误拒）。
        这里把整形状钉住。
        """
        p = tmp_path / "t.json"
        p.write_text(json.dumps({"targets": {"c:x": target}}, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError, match=pat):
            cp.load_targets(p)

    def test_大写_scheme_的_url_不该被误拒(self, tmp_path):
        """反向：`startswith("http")` 会把合法的 `HTTP://e.com` 误拒（b28-fix 的 N2）。"""
        p = tmp_path / "t.json"
        p.write_text('{"targets": {"c:x": {"url": "HTTP://e.com/a", "expect": "x"}}}',
                     encoding="utf-8")
        assert cp.load_targets(p)["c:x"]["url"] == "HTTP://e.com/a"

    @pytest.mark.parametrize("url", [
        "https://e.com/a", "HTTP://E.com", "hTtPs://e.com:8443/x?y=1",
        "http://user:pw@e.com/p", "https://例子.中国/法", "http://127.0.0.1:8080/",
    ])
    def test_合法_url_仍然照过(self, tmp_path, url):
        """收紧 netloc/端口校验时最容易顺手误伤合法写法——这条钉住"12 个合法 URL 全照过"里的代表。"""
        p = tmp_path / "t.json"
        p.write_text(json.dumps({"targets": {"c:x": {"url": url, "expect": "x"}}}), encoding="utf-8")
        assert cp.load_targets(p)["c:x"]["url"] == url

    def test_JSON_顶层数组允许(self, tmp_path):
        """`json` 只允许 dict 会把"发一个数组"误拒（b28-fix 的 N4）。"""
        p = tmp_path / "t.json"
        p.write_text('{"targets": {"c:x": {"url": "https://e.com", "method": "post", '
                     '"json": [1, 2], "expect": "x"}}}', encoding="utf-8")
        assert cp.load_targets(p)["c:x"]["json"] == [1, 2]

    def test_响应体不可序列化也不抛(self):
        """S1（b28-fix）：`json.dumps` 原先在 try 之外 ⇒ 怪响应体会从 probe_channel 逃出去，
        把一个渠道的怪响应变成"整次体检没结果"。"""
        class WeirdTransport:
            def fetch(self, url, **kw):
                return 200, {"a": {1, 2}}          # set 不可 JSON 序列化

        out = cp.probe_channel("c:x", {"url": "https://e.com", "expect": "x"},
                               transport=WeirdTransport())
        assert (out["state"], out["error_code"]) == ("down", "bad_body")
        assert out["http"] == 200

    def test_空_expect_若绕过校验就是假绿(self):
        """把"为什么必须在读表时拒"钉成可执行的证据：空串锚点判恒真。"""
        assert cp._classify(200, "", "")[:2] == ("ok", None)  # 空正文也 ok —— 正是要拒的形状
        assert cp._classify(200, "<html>x</html>", None)[:2] == ("unknown", "no_anchor_configured")


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
