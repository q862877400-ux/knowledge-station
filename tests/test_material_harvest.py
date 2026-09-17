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


#: 一张**真实**的 PNG（1×1）：用来证明"真实字节"的 magic 判据真的在工作
#: （`errors='replace'` 之后 PNG 的签名在文本里根本不存在——复核的 REFUTED 那条）。
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a4944415478da6360000002000154a24f6f0000000049454e44ae426082")

#: 假 PDF（ASCII 头 + 正文）：Content-Type 与字节两条路径都能认出它。
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nstream\nendstream\nendobj\n"


@pytest.fixture()
def site():
    """极简本地站点：正常页 / 各种"不是网页正文"的形态 / 302 / 无 Content-Type。"""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # 静音
            return

        def do_GET(self):  # noqa: N802
            omit_ctype = False
            if self.path == "/ok":
                body, ctype, code = PAGE.encode("utf-8"), "text/html; charset=utf-8", 200
            elif self.path == "/plain":
                body, ctype, code = "住宿标准每晚不超过八百元。".encode(), \
                    "text/plain; charset=utf-8", 200
            elif self.path == "/nomime":
                # 服务端**没给** Content-Type：白名单放行（None），由字节/文本判据兜底。
                body, ctype, code, omit_ctype = PAGE.encode("utf-8"), "", 200, True
            elif self.path == "/boom":
                body, ctype, code = b"err", "text/plain", 500
            elif self.path == "/empty":
                body, ctype, code = b"<html><body>   </body></html>", "text/html", 200
            elif self.path == "/pdf":
                body, ctype, code = PDF_BYTES, "application/pdf", 200
            elif self.path == "/pdf-mislabeled":
                # Content-Type 撒谎说自己是 html：只能靠**真实字节**认出来。
                body, ctype, code = PDF_BYTES, "text/html; charset=utf-8", 200
            elif self.path == "/png-mislabeled":
                body, ctype, code = PNG_BYTES, "text/html; charset=utf-8", 200
            elif self.path == "/js":
                body, ctype, code = b"var x = 1; console.log('hi');", "application/javascript", 200
            elif self.path == "/css":
                body, ctype, code = b".a { color: red }", "text/css", 200
            elif self.path == "/json":
                body, ctype, code = b'{"a": 1}', "application/json", 200
            elif self.path == "/jsonstr":
                body, ctype, code = b'"just a string"', "application/json", 200
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
            if not omit_ctype:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def page_transport(fn=None, *, ctype="text/html; charset=utf-8", raw=None):
    """把 `fn(url, **kw) -> (status, text)` 包成一个**最小 transport 替身**。

    ⚠ 采集走的是 `fetch_page`（一次请求要回 status/headers/text/raw 四样）——
    替身也必须实现它：合约是**严格**的，没有 `fetch_page` 的 transport 会被如实拒绝
    （那条本身有专门用例）。想造"旧式替身"就只写 `fetch`。
    """
    class T:
        def fetch_page(self, url, **kw):
            assert kw.get("allow_redirects") is False, "采集必须显式不跟随重定向"
            if fn is None:
                status, text = 200, PAGE
            else:
                status, text = fn(url, **kw)
            data = raw if raw is not None else text.encode("utf-8")
            return status, {"content-type": ctype} if ctype else {}, text, data

    return T()



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
        seen: list[str] = []
        tp = page_transport(lambda url, **_kw: (seen.append(url), (200, PAGE))[1])
        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=tp)
        assert seen == ["https://news.example/a"]
        assert out["collected"] is True

    def test_content_type_is_recorded_for_the_reviewer(self, project, site, allow_local):
        """Content-Type 进 `tier_reason`：判据**可见**，评审人能自己复核白名单判得对不对。"""
        out = hv.collect_url(project["project_id"], f"{site}/ok")
        assert "Content-Type: text/html" in (out["material"]["tier_reason"] or "")

    def test_missing_content_type_is_stated_honestly(self, project, site, allow_local):
        """服务端没给 Content-Type ⇒ 放行，但**如实写明"未给"**（不是假装检查过）。"""
        out = hv.collect_url(project["project_id"], f"{site}/nomime")
        assert out["collected"] is True, out
        assert "服务端未给 Content-Type" in (out["material"]["tier_reason"] or "")

    def test_text_plain_page_is_accepted(self, project, site, allow_local):
        """纯文本通知（`text/plain`）是**合法**的资料来源，白名单必须放它。"""
        out = hv.collect_url(project["project_id"], f"{site}/plain")
        assert out["collected"] is True, out
        body = "\n".join(c["text"] for c in mr.material_chunks(out["material"]["material_id"]))
        assert "住宿标准" in body


class TestNotAPageIsRefused:
    """**独立复核 2026-09-17 的 MEDIUM**：以前 JS/CSS/JSON 接口会被当成网页正文登记。

    复核实测 11 条样本里 9 条溜过去。现在两条判据挡住它们：
    ① **Content-Type 白名单**（响应头，不是猜）；② **真实字节**的 magic
    （`errors='replace'` 之后的文本里 PNG/JPEG 的签名根本不存在 —— 复核的 REFUTED 那条）。
    """

    @pytest.mark.parametrize("path,needle", [
        ("/js", "不是网页正文"),
        ("/css", "不是网页正文"),
        ("/json", "不是网页正文"),
        ("/jsonstr", "不是网页正文"),
        ("/pdf", "不是网页正文"),            # application/pdf：白名单挡
    ])
    def test_non_page_content_types_are_refused(self, path, needle, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}{path}")
        assert out["collected"] is False, out
        assert needle in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []

    def test_real_bytes_gate_catches_a_mislabeled_png(self, project, site, allow_local):
        """**Content-Type 撒谎说自己是 html**：只有真实字节能认出 PNG。

        这条正是复核 REFUTED 的那件事：文本路径上 `\\x89PNG` **永远**不出现
        （首字节被 `errors='replace'` 换成 U+FFFD），所以以前这条能**注册成材料**。
        """
        out = hv.collect_url(project["project_id"], f"{site}/png-mislabeled")
        assert out["collected"] is False, out
        assert "真实字节" in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []

    def test_real_bytes_gate_catches_a_mislabeled_pdf(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/pdf-mislabeled")
        assert out["collected"] is False, out
        assert "真实字节" in out["reason"], out

    def test_the_type_gate_is_not_bypassed_by_a_title(self, project, site, allow_local):
        """调用方给了 title 也不能让"不是网页"的东西变成材料（标题不是通行证）。"""
        out = hv.collect_url(project["project_id"], f"{site}/js", title="看起来很正规的通知")
        assert out["collected"] is False and mr.list_materials(project["project_id"]) == []

    def test_content_type_header_key_case_does_not_skip_the_gate(self, project, allow_local):
        """响应头的**键名大小写**不许决定白名单是否生效（2026-09-17 复核 E 的 LOW）。

        默认传输会把键名小写化 ⇒ 生产路径没暴露；但**替身或未来的传输层**传
        `Content-Type` 时，第一版只查小写的 `content-type` ⇒ 白名单被**整道静默跳过**
        （表现是"JS/CSS 又能进材料了"，且没有任何报错）。
        """

        class UpperKey:
            def fetch_page(self, url, **kw):
                return 200, {"Content-Type": "application/json"}, '{"a": 1}', b'{"a": 1}'

        out = hv.collect_url(project["project_id"], "https://a.example/j",
                             transport=UpperKey())
        assert out["collected"] is False, out
        assert "不是网页正文" in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []


class TestTransportContractIsStrict:
    def test_transport_without_fetch_page_is_refused_loudly(self, project, allow_local):
        """**严格**契约：只有 `fetch`（拿不到 Content-Type/真实字节）的 transport ⇒ 拒绝。

        为什么不"退回 fetch 继续登记"：那等于**在不知道响应是什么的情况下**把材料
        送进评审队列——正是复核报的那条 MEDIUM。宁可抓不到，也不静默降级。
        """
        class Legacy:
            def fetch(self, url, **_kw):
                return 200, PAGE
        out = hv.collect_url(project["project_id"], "https://news.example/a",
                             transport=Legacy())
        assert out["collected"] is False
        assert "fetch_page" in out["reason"] and "抓取失败" in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []



class TestFailsLoudlyAndRegistersNothing:
    @pytest.mark.parametrize("path,needle", [
        ("/boom", "HTTP 500"),
        ("/empty", "没有可提取的正文"),
        ("/pdf", "不是网页正文"),
        ("/json", "不是网页正文"),
    ])
    def test_bad_responses_do_not_create_material(self, path, needle, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}{path}")
        assert out["collected"] is False
        assert needle in out["reason"], out
        assert mr.list_materials(project["project_id"]) == [], "失败不得留下材料"

    def test_transport_exception_is_reported_not_raised(self, project, allow_local):
        def boom(_url, **_kw):
            raise TimeoutError("模拟超时")

        out = hv.collect_url(project["project_id"], "https://news.example/a",
                             transport=page_transport(boom))
        assert out["collected"] is False and "抓取失败" in out["reason"]
        assert mr.list_materials(project["project_id"]) == []

    def test_404_does_not_register(self, project, site, allow_local):
        out = hv.collect_url(project["project_id"], f"{site}/missing")
        assert out["collected"] is False and out["status"] == 404


class TestTruncation:
    def test_long_page_is_truncated_and_says_so(self, project, allow_local, monkeypatch):
        monkeypatch.setattr(hv, "MAX_TEXT_CHARS", 120)
        long_body = "<html><title>长文</title><body>" + ("住宿标准" * 200) + "</body></html>"
        out = hv.collect_url(project["project_id"], "https://news.example/long",
                             transport=page_transport(lambda _u, **_k: (200, long_body)))
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
        """`allow_redirects=False` 是**承重**的（`page_transport` 内部就断言了这一点，
        这条再用一个显式记录的替身把实参留下来给报告看）。"""
        seen: list[dict] = []

        class Fake:
            def fetch_page(self, url, **kw):
                seen.append({"url": url, **kw})
                return 200, {"content-type": "text/html"}, PAGE, PAGE.encode("utf-8")

        out = hv.collect_url(project["project_id"], "https://news.example/a", transport=Fake())
        assert out["collected"] is True
        assert seen[0]["url"] == "https://news.example/a"
        assert seen[0]["allow_redirects"] is False, seen[0]

    def test_http_is_retried_on_https_same_host(self, project, allow_local):
        seen: list[str] = []

        def fn(url, **_kw):
            seen.append(url)
            if url.startswith("http://"):
                return 302, ""
            return 200, "<html><title>T</title><body>正文内容足够长。</body></html>"

        out = hv.collect_url(project["project_id"], "http://news.example/a?b=1",
                             transport=page_transport(fn))
        assert seen == ["http://news.example/a?b=1", "https://news.example/a?b=1"], seen
        assert out["collected"] is True
        # 留痕用**实际抓到的**地址（不是用户给的那个）——否则审计链说不清到底抓了谁
        assert out["material"]["url"] == "https://news.example/a?b=1"
        assert "同主机 http→https 升级后取到" in (out["material"]["tier_reason"] or "")

    def test_redirect_after_upgrade_is_refused_not_followed(self, project, allow_local):
        out = hv.collect_url(project["project_id"], "http://news.example/a",
                             transport=page_transport(lambda _u, **_k: (301, "")))
        assert out["collected"] is False and out["status"] == 301
        assert "重定向" in out["reason"] and "不跟随" in out["reason"], out
        assert mr.list_materials(project["project_id"]) == []

    def test_https_url_that_redirects_is_refused(self, project, allow_local):
        """https 没有可升级的空间 ⇒ 直接拒绝（不给"再试一次"的假动作）。"""
        seen: list[str] = []

        def fn(url, **_kw):
            seen.append(url)
            return 302, ""

        out = hv.collect_url(project["project_id"], "https://news.example/a",
                             transport=page_transport(fn))
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
        out = hv.collect_url(project["project_id"], "https://a.example/e",
                             transport=page_transport(lambda _u, **_k: (200, "   ")))
        assert out["collected"] is False and "响应为空" in out["reason"], out

    def test_tag_only_body_is_reported_as_converted_empty(self, project, allow_local):
        """**原文非空但转换后为空**（只有标签）→ 原因串必须说清是"转换后"为空。

        与上一条是**不同**的故障（一个是取回就没内容，一个是转换把它清空了），
        合并成一句话就会把排查方向带偏。
        """
        tp = page_transport(lambda _u, **_k: (200, "<html><body>   </body></html>"))
        out = hv.collect_url(project["project_id"], "https://a.example/t", transport=tp)
        assert out["collected"] is False
        assert "原文非空" in out["reason"] and "响应为空" not in out["reason"], out

    def test_nonempty_body_that_becomes_empty_after_conversion(self, project, allow_local):
        tp = page_transport(
            lambda _u, **_k: (200, "<html><body><script>var a=1;</script></body></html>"))
        out = hv.collect_url(project["project_id"], "https://a.example/s", transport=tp)
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
    """`_strip_script_style` 的边角语义（**两轮复核**都在这里抓到问题，故钉得细）。

    第一版是一句 `re.sub(r"<(script|style)\\b[^>]*>.*?</\\1>", …)`：未闭合时**匹配不上**
    ⇒ JS 留在材料里；属性里带 `>` 时**定位偏差** ⇒ 吃掉可见正文。
    第二版（2026-09-17 复核 D② 之后）改成：**先剥注释** + **结束标签放宽** +
    **自闭合按 HTML5 语义**（`<script/>` 里的 `/` 被忽略，**不是**自闭合）。
    ⚠ 第二轮复核提的两组边角（LEAK 与 OVERKILL）都在这条语义下修掉了；
    剩下的"未闭合就吞到末尾"是 **HTML5 的规则**，演示见最后两条。
    """

    def test_html5_semantics_slash_does_not_self_close(self):
        """**HTML5**：`<script src="a.js"/>` 里的 `/` 被忽略 ⇒ 到 `</script>` 之间是**脚本**。

        ⚠ 这条是**第二轮复核**（LEAK）之后**改过方向**的断言——第一版按 XHTML 把
        `<script …/>` 当自闭合，于是 `<script src="a.js"/>var x=1;</script>` 会把
        **JS 留在正文里**。两种读法直接冲突，本函数选 HTML5（浏览器怎么解析，正文就怎么算）；
        代价（XHTML 页面会丢一段正文）写在 `_strip_script_style` 的 docstring 里。
        """
        from src.core.text_utils import html_to_text
        out = html_to_text('<script src="a.js"/>var x=1;</script>可见')
        assert out == "可见", out
        assert "var x=1" not in out
        out2 = html_to_text('<script data-x=a/>var y=2;</script>后面')
        assert out2 == "后面", out2

    def test_style_self_closing_slash_also_does_not_self_close(self):
        """同一条语义的 style 版：`<style/>` 之后的可见文字**属于样式内容**，浏览器不显示。"""
        from src.core.text_utils import html_to_text
        assert html_to_text("<style/>可见") == ""
        assert html_to_text("<style/>隐藏</style>可见") == "可见"

    def test_html_comment_does_not_hide_a_script_from_the_sweep(self):
        """**OVERKILL-1**（复核 D②）：注释里的 `<script>` **不是标签**，不许吞掉其后正文。"""
        from src.core.text_utils import html_to_text
        out = html_to_text("<!-- <script> -->重要正文：住宿标准八百元。")
        assert "住宿标准八百元" in out, out
        out2 = html_to_text("<!-- 注释里的文字 -->正文")
        assert out2 == "正文", out2

    def test_end_tag_with_junk_is_recognized(self):
        """**OVERKILL-2**：`</script foo>` 是浏览器接受的结束标签，第一版认不出 ⇒ 吞掉其后正文。"""
        from src.core.text_utils import html_to_text
        assert html_to_text("<script>var a=1;</script foo>可见") == "可见"
        assert html_to_text("<script>var a=1;</SCRIPT >可见") == "可见"

    def test_literal_script_inside_an_attribute_is_not_a_tag(self):
        """**OVERKILL-3**：属性值里的字面 `<script>` 不是标签（否则其后正文被吞）。"""
        from src.core.text_utils import html_to_text
        out = html_to_text("<div title='<script>'>可见</div>")
        assert "可见" in out, out
        assert "<script>" not in out, out

    def test_literal_script_in_an_UNQUOTED_attribute_is_not_a_tag_either(self):
        """**OVERKILL-4**（2026-09-17 复核 LOW 顺带实测，v3 修）：**无引号**属性值同理。

        `<p title=<script> 可见甲</p><p>后</p>`：HTML5 里 `<` 在无引号属性值中是
        **属性值的一部分**（parse error 但继续），标签在下一个 `>` 处结束 ⇒
        `<p title=<script` 是完整标签、**"可见甲"是正文**。
        修前实测只留 `'前<p title='`（"可见甲"与"后"**整段丢掉**），是一条**静默的内容损失**。
        """
        from src.core.text_utils import html_to_text
        out = html_to_text("<p>前</p><p title=<script> 可见甲</p><p>后</p>")
        assert "可见甲" in out and "后" in out, out
        assert "script" not in out, out
        out2 = html_to_text("<p>前</p><p title=<style> 可见乙</p>")
        assert "可见乙" in out2, out2

    def test_a_bare_less_than_in_the_text_does_not_disable_the_sweep(self):
        """**上面那条守卫的风险方向**：正文里的裸 `<` **不许**让真 `<script>` 变成文本。

        守卫的判据是"未闭合的**标签开头**"（`<` 紧跟字母或 `/`）。`a < b` 里的 `<`
        后面是空格 ⇒ 不是标签开头 ⇒ `<script>` 仍是真标签、JS 仍被剥掉。
        ⚠ 若判据放宽成"有 `<` 就算在标签里"，**JS 会漏进正文**——那是本函数要防的方向，
        所以这条与上一条是**成对**的（一个防 OVERKILL，一个防 LEAK）。
        """
        from src.core.text_utils import html_to_text
        out = html_to_text("<p>前 3 < 5</p><script>var SECRET_JS=1;</script><p>后</p>")
        assert "SECRET_JS" not in out, out
        assert "前" in out and "后" in out, out
        # 引号里的 `>` 也算"标签已闭合" ⇒ 不能因此把后面的真 script 当文本
        out2 = html_to_text('<a title="a>b">x</a><script>var SECRET_JS=2;</script>后')
        assert "SECRET_JS" not in out2, out2

    def test_the_guard_runs_on_the_ORIGINAL_string_not_a_rewritten_one(self):
        """**顺序是承重的**（2026-09-17 独立复核 b7 的 MEDIUM）。

        `html_to_text` 里 `clean_eq_tags` / `</td>` / `</tr>` 三个替换**会删掉 `>`**；
        若它们在 `_strip_script_style` **之前**跑，原串里**已经闭合**的 `<b` / `<div`
        会变成"未闭合的标签开头" ⇒ 守卫误判 ⇒ **JS 反而漏进正文**
        （正是那个守卫要防的方向）。复核实测 4 组，这里逐组钉住。
        """
        from src.core.text_utils import html_to_text
        js = "var SECRET_JS=3;"
        for html in (
            f"<b</td>x<script>{js}</script>",              # </td> 替换删掉 >
            f"<td>a<b</td><script>{js}</script>",          # 同上（表格单元里未闭合的 <x）
            f"<b</tr>x<script>{js}</script>",              # </tr> 替换删掉 >
            f"<div <eq>x</eq><script>{js}</script>",        # clean_eq_tags 删掉 >
        ):
            out = html_to_text(html)
            assert "SECRET_JS" not in out, (html, out)

    def test_raw_text_families_that_browsers_do_not_render_are_stripped(self):
        """`script`/`style` 之外还有一族**浏览器不渲染**的元素（复核 b8 的 LOW-5）。

        复核实测这一族的内容**全部**进了正文。按"页面里看到什么就是正文"的定位，
        不渲染的就不该进来 ⇒ 一并剥掉：
        `iframe` / `xmp` / `noembed` / `noframes` / `plaintext`
        （`plaintext` 没有结束标签，其后全是 raw text ⇒ 走"找不到闭合就丢尾"那条逻辑）。

        ⚠ **故意保留** `noscript` / `textarea` / `title`：我们**不执行 JS**，
        所以 `<noscript>` 里那套"没有 JS 时的兜底内容"**恰恰是**我们会看到的东西；
        `textarea` 是表单默认值、`title` 是页面标题。这三条是**有意的决定**
        （登记在方案 §12 未决第 9 条），别当成漏掉的。
        """
        from src.core.text_utils import html_to_text
        for tag in ("iframe", "xmp", "noembed", "noframes"):
            out = html_to_text(f"<p>前</p><{tag}>SECRETLEAK</{tag}><p>后</p>")
            assert "SECRETLEAK" not in out, (tag, out)
            assert "前" in out and "后" in out, (tag, out)
        # plaintext：其后全部是 raw text（没有结束标签）
        assert "SECRETLEAK" not in html_to_text("<p>前</p><plaintext>SECRETLEAK")
        # 有意保留的三族：内容仍要在（不许"顺手"一起剥掉）
        for tag in ("noscript", "textarea", "title"):
            out = html_to_text(f"<p>前</p><{tag}>保留甲</{tag}><p>后</p>")
            assert "保留甲" in out, (tag, out)

    def test_guard_requirement_one_is_load_bearing(self):
        """守卫的**要求①**（`<` 之后必须紧跟字母或 `/`）是**承重的**，必须有正面用例。

        ⚠ 这一条是被**独立复核 b8 打回来的**（REFUTED）：§10.45 声称"新增的表格形态用例
        让『删掉要求①』这条变异有主"，实测那条变异**全绿**——而同一个改动**真的**新开了
        4 条"JS 进正文"。差别在这里：下面这些输入里，`<script>` 之前那个 `<` 后面跟的是
        **空格**（`a < b` / `3 < 5`），要求①把它判为"不是标签开头" ⇒ 真 `<script>` 仍被剥；
        一旦去掉要求①，"有一个未闭合的 `<`"成立 ⇒ 误判成"在标签里" ⇒ **JS 就漏了**。
        复核给的正是这四组（`probeG_req1.py`），这里逐组钉住。
        """
        from src.core.text_utils import html_to_text
        js = "var SECRET_JS=9;"
        for html in (
            f"<p>a < b<script>{js}</script>",
            f"<p>a < /b<script>{js}</script>",
            f"<p>3 < 5<script>{js}</script>",
            f"<p>a <= b<script>{js}</script>",
        ):
            out = html_to_text(html)
            assert "SECRET_JS" not in out, (html, out)

    def test_unclosed_script_swallows_the_tail_like_a_browser(self):
        """未闭合 ⇒ 其后全部是脚本文本（HTML5），**不得**把 JS 当正文留下来。

        ⚠ 这**不是**保守估计而是浏览器行为：正文里出现一个字面 `<script>`（没有闭合）
        在浏览器里同样会让后面全部不渲染。所以"吞掉"= 与浏览器一致；
        真要在这种脏页面上抢救正文，得引 HTML 解析器（未立项）。
        """
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
        assert html_to_text("正文<script>var SECRET=1;</script>后面") == "正文后面"

