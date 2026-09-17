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
            elif self.path == "/redir":
                # 302 → **内网**地址：独立复核实测"跟随重定向"会真的连上 169.254.169.254。
                # 这里用它证明**没有**跟随（拿到的是 302 本身）。
                body, ctype, code = b"", "text/html", 302
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
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

    def test_it_calls_the_ssrf_owner_exactly_once_per_url(self, project, monkeypatch):
        """**行为**断言（不是"源码里有这个字符串"）：判据真的被调、且每跳都调。

        ⚠ 旧版本这条是**空转守卫**（只断言源码里出现 `_announce.is_private_url` 且没有
        `ipaddress`/`socket.`），独立复核 2026-09-17 的变异体 M7 能把它骗过（GREEN）。
        现在改成：包一层计数，断言"发起前问过判据"，并用**同一函数**的替身证明
        判据的结论真的会改变结果（否则计数可能来自无关调用）。
        """
        calls: list[str] = []
        real = hv._announce.is_private_url

        def spy(url):
            calls.append(url)
            return real(url)

        monkeypatch.setattr(hv._announce, "is_private_url", spy)
        out = hv.collect_url(project["project_id"], "http://127.0.0.1:9/x",
                             transport=object())
        assert calls == ["http://127.0.0.1:9/x"], calls
        assert out["collected"] is False and "SSRF" in out["reason"]
        assert mr.list_materials(project["project_id"]) == []

    def test_the_ssrf_verdict_actually_gates(self, project, monkeypatch):
        """判据的结论**真的**决定结果：换成"一律拒绝"的替身 ⇒ 连公网地址也不抓。

        这条与上一条互补：上一条证明"问了"，这条证明"问了算数"（否则计数是装饰）。
        """
        called: list[str] = []

        class Spy:
            def fetch(self, url, **_kw):
                called.append(url)
                return 200, "<html><body>正文</body></html>"

        monkeypatch.setattr(hv._announce, "is_private_url", lambda _u: True)
        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=Spy())
        assert out["collected"] is False and "SSRF" in out["reason"]
        assert called == [], "判据说拒，就一步都不许抓"

    def test_no_second_address_judgement_in_the_module(self):
        """粗护栏（**不是**上面那条行为断言的替代品）：本模块不自己解析地址。

        ⚠ 说明白它的边界：这是"源码里不许出现地址解析"的**粗**检查，
        一个把逻辑藏到别的模块再 import 进来的写法能绕过它。真正的保证来自
        `test_it_calls_the_ssrf_owner_exactly_once_per_url`（行为）与代码评审。
        """
        import inspect
        src = inspect.getsource(hv)
        body = src.split('"""', 2)[-1]          # 去掉模块 docstring（它在**讨论**这条纪律）
        assert "ipaddress" not in body and "socket." not in body



class TestRedirectsAreNotFollowed:
    """**独立复核 2026-09-17 的 HIGH**：默认传输跟随 302，实测可把请求引向内网。

    这里两个方向都验：
      · **契约**（注入替身）：抓取时带 `allow_redirects=False`；http→https 同主机升级；
        第二跳仍是 3xx 就**如实拒绝**；
      · **真实传输**：用真 `default_transport()` 打本地 302 —— 拿到的是 **302 本身**
        （若跟随了，会是连接失败/超时或目标页，绝不会是 302）。
    """

    def test_contract_forwards_allow_redirects_false(self, project, allow_local):
        seen: list[dict] = []

        class Fake:
            def fetch(self, url, **kw):
                seen.append({"url": url, **kw})
                return 200, "<html><body>正文内容足够长。</body></html>"

        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=Fake())
        assert out["collected"] is True
        assert seen[0]["url"] == "https://news.example/a"
        assert seen[0]["allow_redirects"] is False, seen[0]

    def test_http_is_retried_on_https_same_host(self, project, allow_local):
        seen: list[str] = []

        class Fake:
            def fetch(self, url, **kw):
                seen.append(url)
                if url.startswith("http://"):
                    return 302, ""
                return 200, "<html><title>T</title><body>正文内容足够长。</body></html>"

        out = hv.collect_url(project["project_id"], "http://news.example/a?b=1",
                             transport=Fake())
        assert seen == ["http://news.example/a?b=1", "https://news.example/a?b=1"], seen
        assert out["collected"] is True
        # 留痕用**实际抓到的**地址（不是用户给的那个）——否则审计链说不清到底抓了谁
        assert out["material"]["url"] == "https://news.example/a?b=1"
        assert "同主机 http→https 升级后取到" in (out["material"]["tier_reason"] or "")

    def test_redirect_after_upgrade_is_refused_not_followed(self, project, allow_local):
        class Always302:
            def fetch(self, url, **kw):
                return 301, ""

        out = hv.collect_url(project["project_id"], "http://news.example/a",
                             transport=Always302())
        assert out["collected"] is False and out["status"] == 301
        assert "重定向" in out["reason"] and "不跟随" in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []

    def test_https_url_that_redirects_is_refused(self, project, allow_local):
        """https 没有可升级的空间 ⇒ 直接拒绝（不给"再试一次"的假动作）。"""
        seen: list[str] = []

        class R:
            def fetch(self, url, **kw):
                seen.append(url)
                return 302, ""

        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=R())
        assert out["collected"] is False and seen == ["https://news.example/a"], seen

    def test_https_upgrade_only_changes_the_scheme(self):
        assert hv._https_upgrade("http://a.example/x?y=1#z") == "https://a.example/x?y=1#z"
        assert hv._https_upgrade("http://a.example:80/x") == "https://a.example/x"
        assert hv._https_upgrade("http://a.example:8080/x") == "https://a.example:8080/x"
        assert hv._https_upgrade("https://a.example/x") is None
        assert hv._https_upgrade("ftp://a.example/x") is None
        assert hv._https_upgrade("not a url") is None

    def test_real_transport_does_not_follow_a_redirect(self, project, site, allow_local):
        """**真实传输**下的证明：本地 302（Location 指向内网元数据端点）拿到的是 **302 本身**。

        ⚠ 这里只在**传输层**断言，因为在本地 http 站点上 harvest 的"同主机 http→https 升级"
        必然失败（这台测试服务器没有 TLS），拿不到 302 —— 那会是一条**假的**期望。
        harvest 层的拒绝由注入替身的用例覆盖（判据/拒绝理由都验到了）。
        判据的意义：若跟随了重定向，`status` **不可能**还是 302（会变成目标端点的连接失败/超时
        或目标页），所以"拿到 302"就是"没跟随"的证据。
        """
        from src.core.update.channels import base
        tp = base.default_transport()
        status, _body = tp.fetch(f"{site}/redir", timeout=5.0, allow_redirects=False)
        assert status == 302, f"传输层没有关掉重定向（拿到 {status}）"
        # 不给"再试一次"留错觉：升级后的地址同样被拒（真实传输下是连接失败，也**绝不放行**）
        out = hv.collect_url(project["project_id"], f"{site}/redir")
        assert out["collected"] is False, out
        assert mr.list_materials(project["project_id"]) == []


class TestEmptyReasonDistinguishesTwoKinds:
    """两种"空"必须能区分（复核 2026-09-17 的归因误导）。"""

    def test_original_body_empty(self, project, allow_local):
        """**原文本身为空**（连标签都没有）→ 原因串说"响应为空"。"""

        class Empty:
            def fetch(self, url, **_kw):
                return 200, "   "

        out = hv.collect_url(project["project_id"], "https://a.example/e", transport=Empty())
        assert out["collected"] is False and "响应为空" in out["reason"], out

    def test_tag_only_body_is_reported_as_converted_empty(self, project, allow_local):
        """**原文非空但转换后为空**（只有标签）→ 原因串必须说清是"转换后"为空。

        与上一条是**不同**的故障（一个是取回就没内容，一个是转换把它清空了），
        合并成一句话就会把排查方向带偏。
        """

        class TagsOnly:
            def fetch(self, url, **_kw):
                return 200, "<html><body>   </body></html>"

        out = hv.collect_url(project["project_id"], "https://a.example/t",
                             transport=TagsOnly())
        assert out["collected"] is False
        assert "原文非空" in out["reason"] and "响应为空" not in out["reason"], out

    def test_nonempty_body_that_becomes_empty_after_conversion(self, project, allow_local):
        class OnlyScript:
            def fetch(self, url, **_kw):
                return 200, "<html><body><script>var a=1;</script></body></html>"

        out = hv.collect_url(project["project_id"], "https://a.example/s",
                             transport=OnlyScript())
        assert out["collected"] is False
        assert "原文非空" in out["reason"] and "脚本/样式" in out["reason"], out

class TestHtmlToTextOwner:
    def test_equivalent_to_clause_health_without_script_or_style(self):
        """规范实现与既有 `clause_health_html_to_text` 逐字符等价——**除两条有意差异**。

        差异①（script/style）与②（大写表格标签）各有一条专门的测试；这里的样本
        刻意都避开这两条，用来钉住"其余的输入不许分叉"。
        """
        from src.core.quality.clause_health import clause_health_html_to_text
        from src.core.text_utils import html_to_text
        samples = [
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>",
            "<p>正文&amp;符号</p><eq>x^2</eq>",
            "", None, "<td>only</td>", "<tr><td>1</td></tr>",
            "<p>未闭合<b>粗体",
            "<div class='a>b'>x</div>",          # 两边同样粗（都不完美，故此处钉"一致"）
        ]
        for s in samples:
            assert html_to_text(s, limit=400) == clause_health_html_to_text(s, limit=400), repr(s)

    def test_deliberate_difference_on_uppercase_table_tags(self):
        """**有意差异②**：大写 `</TD>`/`</TR>` 在本函数里照样转表格分隔。

        ⚠ 这条是 2026-09-17 独立复核发现的：原 docstring 只说了一条差异（script/style），
        而这种输入下两者并不等价（`'甲 | 乙'` vs `'甲乙'`）。旧实现只认小写，
        真实页面两种大小写都有 ⇒ 保留本函数的行为，并把差异**写准 + 钉住**。
        """
        from src.core.quality.clause_health import clause_health_html_to_text
        from src.core.text_utils import html_to_text
        s = "<TABLE><TR><TD>甲</TD><TD>乙</TD></TR><TR><TD>丙</TD><TD>丁</TD></TR></TABLE>"
        assert html_to_text(s, limit=400) == "甲 | 乙\n丙 | 丁"
        assert clause_health_html_to_text(s, limit=400) == "甲乙丙丁"

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


class TestScriptStyleStrippingEdges:
    """`_strip_script_style` 的两种**真实页面**形态（独立复核 2026-09-17 的两个 HIGH 之一）。

    旧实现是一句 `re.sub(r"<(script|style)\\b[^>]*>.*?</\\1>", …)`，两种形态都错，
    且都是**静默**的：自闭合会吃掉可见正文（丢材料 + 归因误导），未闭合会把 JS 留在材料里。
    """

    def test_self_closing_script_does_not_eat_visible_text(self):
        from src.core.text_utils import html_to_text
        s = '<script src="a.js"/>重要正文：住宿标准八百元。<script>var t=1;</script>'
        out = html_to_text(s)
        assert "住宿标准八百元" in out, out
        assert "t=1" not in out, out

    def test_self_closing_style_tag(self):
        from src.core.text_utils import html_to_text
        assert html_to_text("<style/>可见") == "可见"

    def test_unclosed_script_swallows_the_tail_like_a_browser(self):
        """未闭合 ⇒ 其后全部是脚本文本（HTML 规则），**不得**把 JS 当正文留下来。"""
        from src.core.text_utils import html_to_text
        out = html_to_text("可见正文<script>var SECRET_JS = 1;")
        assert out == "可见正文", out

    def test_unclosed_style_swallows_the_tail(self):
        from src.core.text_utils import html_to_text
        assert html_to_text("可见<style>.x{color:SECRET_CSS}") == "可见"

    def test_uppercase_and_mixed_case_tags(self):
        """**大小写敏感性要有钉子**（独立复核 M3 变异体 GREEN：原先零覆盖）。"""
        from src.core.text_utils import html_to_text
        assert html_to_text("<SCRIPT>var a=1;</SCRIPT>可见") == "可见"
        assert html_to_text("<Style>.x{color:red}</Style>可见") == "可见"
        assert html_to_text("<ScRiPt>var a=1;</sCrIpT>可见") == "可见"

    def test_close_tag_inside_a_script_string(self):
        """脚本里的字符串含 `</p>` 这类片段**不能**骗过剥离（用闭合标签本身定位）。"""
        from src.core.text_utils import html_to_text
        assert html_to_text("<script>var s = '</p>';</script>可见") == "可见"

    def test_normal_closed_tags_still_work(self):
        from src.core.text_utils import html_to_text
        assert html_to_text('<script src="a.js"></script>可见') == "可见"
        assert html_to_text("<script>a</script>中间<style>b</style>后面") == "中间后面"

