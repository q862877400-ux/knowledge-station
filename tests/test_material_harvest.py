# -*- coding: utf-8 -*-
"""网页采集器测试（`src/core/materials/harvest.py`，Phase C 第四步）。

守四件事：
  1. **SSRF 闸门真的挡在前面**（内网/保留地址**不抓**，且失败**不建材料**）；
  2. 抓回的正文**一律 pending**（走 `collect_text`，硬门不因"自动采集"而松）；
  3. 非 2xx / 非文本 / 空正文 ⇒ **如实失败、不建空材料**（空材料会变成盲签对象）；
  4. 复用既有所有者：SSRF 用 `announce.is_private_url`、抓取用可注入 transport、
     HTML→文本用 `text_utils.html_to_text`（不新写第二份）。

⚠ 测试要打**本地**服务，而 `is_private_url` **正是**要拒绝回环地址（无豁免开关）。
所以这里用 `monkeypatch` 换掉那个判据（**生产代码里没有开关**）——
这既测到了闸门本身，又能在真实 HTTP 上测通路。
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from src.core.materials import harvest as hv
from src.core.storage import material_repo as mr

PAGE = ("<html><head><title>关于住宿标准的通知</title>"
        "<style>p{color:red}</style></head>"
        "<body><h1>通知</h1><p>住宿标准每晚不超过八百元，自下月起执行。</p>"
        "<script>var tracker=1;</script></body></html>")


@pytest.fixture()
def project(db):
    return mr.create_project("采集器测试")


@pytest.fixture()
def site():
    """极简本地站点：/ok 正常页、/boom 500、/empty 空正文、/pdf 二进制、/json JSON。"""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # 静音
            return
        def do_GET(self):  # noqa: N802
            if self.path == "/ok":
                body, ctype, code = PAGE.encode("utf-8"), "text/html; charset=utf-8", 200
            elif self.path == "/boom":
                body, ctype, code = b"err", "text/plain", 500
            elif self.path == "/empty":
                body, ctype, code = b"<html><body>   </body></html>", "text/html", 200
            elif self.path == "/pdf":
                body, ctype, code = b"%PDF-1.7 not really", "application/pdf", 200
            elif self.path == "/json":
                body, ctype, code = b'{"a": 1}', "application/json", 200
            else:
                body, ctype, code = b"nope", "text/plain", 404
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture()
def allow_local(monkeypatch):
    """把 SSRF 判据换成"公网"以允许打本地站点。

    ⚠ 这**不是**生产开关：`harvest` 调的是 `announce.is_private_url`，
    这里换掉的是那个函数本身。生产代码里没有"允许内网"的参数可传。
    """
    monkeypatch.setattr(hv._announce, "is_private_url", lambda _u: False)


class TestSsrfGate:
    def test_loopback_is_refused_and_nothing_is_fetched(self, project, monkeypatch):
        """**最重要的一条**：内网地址在**抓取之前**就被拒，且不建材料。"""
        called: list[str] = []

        class Spy:
            def fetch(self, url, **_kw):
                called.append(url)
                return 200, PAGE

        out = hv.collect_url(project["project_id"], "http://127.0.0.1:9/x",
                             transport=Spy())
        assert out["collected"] is False
        assert "SSRF" in out["reason"]
        assert called == [], "被闸门拒掉的 URL **绝不能**真的去抓"
        assert mr.list_materials(project["project_id"]) == []

    @pytest.mark.parametrize("url", [
        "http://localhost/x", "http://10.0.0.1/x", "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data/",   # 云元数据端点
        "file:///etc/passwd", "ftp://example.com/x",
    ])
    def test_private_and_non_http_are_refused(self, url, project):
        out = hv.collect_url(project["project_id"], url, transport=object())
        assert out["collected"] is False, url
        assert "SSRF" in out["reason"], url

    def test_blank_url(self, project):
        assert hv.collect_url(project["project_id"], "   ")["collected"] is False


class TestHappyPath:
    def test_fetches_and_registers_as_pending(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/ok")
        assert out["collected"] is True, out
        assert out["status"] == 200
        m = out["material"]
        # 硬门不因"自动采集"而松
        assert m["review_status"] == "pending"
        assert m["origin"] == "collected"
        assert m["lifecycle"] == "ephemeral"
        # 来源留痕（含域名）
        assert m["url"] == f"{site}/ok"
        assert m["domain"] == "127.0.0.1"
        # 未批准 ⇒ 检索不到
        assert mr.search_materials(project["project_id"], "住宿标准") == []

    def test_title_comes_from_the_page(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/ok")
        assert out["material"]["title"] == "关于住宿标准的通知"

    def test_caller_title_wins(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/ok", title="我给的标题")
        assert out["material"]["title"] == "我给的标题"

    def test_script_and_style_do_not_become_content(self, project, site, allow_local):
        """页面里的 JS/CSS **不能**进正文（采集最脏的来源）。"""
        out = hv.collect_url(project["project_id"], f"{site}/ok")
        chunks = mr.material_chunks(out["material"]["material_id"])
        body = "\n".join(c["text"] for c in chunks)
        assert "住宿标准每晚不超过八百元" in body
        assert "tracker" not in body, "脚本内容不得进材料"
        assert "color:red" not in body, "样式不得进材料"

    def test_note_records_the_fetch(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/ok")
        assert "自采" in (out["material"]["tier_reason"] or "")
        assert "HTTP 200" in (out["material"]["tier_reason"] or "")

    def test_same_page_twice_is_a_duplicate(self, project, site, allow_local):
        first = hv.collect_url(project["project_id"], f"{site}/ok")
        second = hv.collect_url(project["project_id"], f"{site}/ok")
        assert second["collected"] is True and second["duplicate"] is True
        assert second["material"]["material_id"] == first["material"]["material_id"]
        assert len(mr.list_materials(project["project_id"])) == 1

    def test_injected_transport_is_used(self, project, allow_local):
        """不需要真网络：注入一个假 transport 就能测通路。"""
        class Fake:
            def __init__(self): self.seen = []
            def fetch(self, url, **_kw):
                self.seen.append(url)
                return 200, "<html><title>T</title><body>正文内容足够长。</body></html>"
        fake = Fake()
        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=fake)
        assert fake.seen == ["https://news.example/a"]
        assert out["collected"] is True


class TestFailsLoudlyAndRegistersNothing:
    @pytest.mark.parametrize("path,needle", [
        ("/boom", "HTTP 500"),
        ("/empty", "没有可提取的正文"),
        ("/pdf", "不是文本"),
        ("/json", "不是文本"),
    ])
    def test_bad_responses_do_not_create_material(self, path, needle, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}{path}")
        assert out["collected"] is False
        assert needle in out["reason"], out
        assert mr.list_materials(project["project_id"]) == [], "失败不得留下材料"

    def test_transport_exception_is_reported_not_raised(self, project, allow_local):
        class Boom:
            def fetch(self, url, **_kw):
                raise TimeoutError("模拟超时")
        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=Boom())
        assert out["collected"] is False and "抓取失败" in out["reason"]
        assert mr.list_materials(project["project_id"]) == []

    def test_404_does_not_register(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/missing")
        assert out["collected"] is False and out["status"] == 404


class TestTruncation:
    def test_long_page_is_truncated_and_says_so(self, project, allow_local, monkeypatch):
        monkeypatch.setattr(hv, "MAX_TEXT_CHARS", 120)
        long_body = "<html><title>长文</title><body>" + ("住宿标准" * 200) + "</body></html>"

        class Big:
            def fetch(self, url, **_kw):
                return 200, long_body
        out = hv.collect_url(project["project_id"], "https://news.example/long",
                             transport=Big())
        assert out["collected"] is True and out["truncated"] is True
        assert "截断" in (out["material"]["tier_reason"] or "")
        body = "\n".join(c["text"] for c in mr.material_chunks(out["material"]["material_id"]))
        assert len(body) <= 200, "正文必须真的被截断（不是只标个旗标）"


class TestNoProductionBypass:
    def test_collect_url_has_no_private_allow_switch(self):
        """**结构性约束**：不得存在"允许内网"之类的参数（那是给严格版开后门）。

        方向是**结构**检查（签名里不许出现 allow/private/local 这类词），
        因为它要防的正是"以后有人为了调试方便加一个开关"。
        """
        import inspect
        params = list(inspect.signature(hv.collect_url).parameters)
        banned = [p for p in params if any(k in p.lower() for k in ("allow", "private", "local", "unsafe"))]
        assert banned == [], f"不得提供绕过 SSRF 的参数: {banned}"

    def test_it_delegates_to_the_ssrf_owner(self):
        """SSRF 判据只有一个所有者：`announce.is_private_url`（本模块只调用它）。"""
        import inspect
        src = inspect.getsource(hv)
        assert "_announce.is_private_url" in src
        # 不得自己实现一份地址判断（socket/ipaddress 之类）
        assert "ipaddress" not in src and "socket." not in src


class TestHtmlToTextOwner:
    def test_equivalent_to_clause_health_without_script_or_style(self):
        """规范实现与既有 `clause_health_html_to_text` 在**无 script/style** 时逐字符等价。"""
        from src.core.quality.clause_health import clause_health_html_to_text
        from src.core.text_utils import html_to_text
        samples = [
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>",
            "<p>正文&amp;符号</p><eq>x^2</eq>",
            "", None, "<td>only</td>", "<tr><td>1</td></tr>",
        ]
        for s in samples:
            assert html_to_text(s, limit=400) == clause_health_html_to_text(s, limit=400), repr(s)

    def test_deliberate_difference_on_script_and_style(self):
        """**有意不同**：本函数丢掉 script/style 的**内容**（那三份不会）。

        钉住这条，免得有人发现"不等价"后当成 bug 把改进改回去。
        """
        from src.core.quality.clause_health import clause_health_html_to_text
        from src.core.text_utils import html_to_text
        s = "<style>p{color:red}</style><p>可见</p><script>var x=1;</script>"
        assert html_to_text(s) == "可见"
        assert "color:red" in clause_health_html_to_text(s)      # 旧实现把样式当正文
        assert "var x=1" in clause_health_html_to_text(s)
