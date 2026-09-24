# -*- coding: utf-8 -*-
"""线程池容量必须**显式有界**（§10.81，独立复核 b13 的 MEDIUM-1）。

背景：§10.71–§10.80 把一批同步重活从"事件循环里串行跑"改成"线程池里跑"。改前它们的
**并发度天然是 1**；改后可以同时开满 anyio 的默认 **40** 个令牌 ⇒ 40 个 MinerU 解析子进程 /
40 份 PDF 渲染同时来（复核实测：池满后真实的 `def` 端点 `/ingest/preview/inbox` 从 1.4ms
被拖到 659ms）。所以"把活挪进线程池"这件事**必须**配套一个容量上限，否则是把
"事件循环被冻住"换成"资源风暴"。

判据是**确定性**的（不靠计时，避免 flaky）：
  1. 收窄函数真的把 limiter 设成常量（在事件循环里读回来核对）；
  2. 常量本身不超过 anyio 默认值（不许"收窄"成更大）；
  3. **每个请求**都会走一次收窄（拿替身记录调用）——这条挡的是"有人把中间件里那行删了"。
"""
from __future__ import annotations

import asyncio

HDR = {"Authorization": "Bearer test-token-123"}


def test_收窄函数真的把线程池设成常量():
    import anyio.to_thread

    from src.core.api import server

    async def check() -> int:
        # 先还原成 anyio 默认，确认函数的**效果**（而不是"本来就是 16"）
        anyio.to_thread.current_default_thread_limiter().total_tokens = 40
        server._bound_loops.clear()                 # §10.88：幂等标记现在**按事件循环**缓存
        server.bound_threadpool_once()
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    got = asyncio.run(check())
    assert got == server.THREADPOOL_TOKENS, (got, server.THREADPOOL_TOKENS)


def test_线程池收窄是按事件循环的():
    """§10.88（独立复核 b17 的 MEDIUM-1）：**第二个事件循环**也必须被收窄到 16。

    为什么必须有这条：anyio 的 `current_default_thread_limiter()` 是 **RunVar（按事件循环）**，
    而收窄函数原先用一个**进程级布尔**做幂等标记 ⇒ 第二个循环里它直接 `return`，
    池子停在 anyio 默认的 **40** —— "池子有界"从第二个循环起**静默失效**
    （b17 实测：loop#1=16、loop#2=40）。生产只有一条长驻循环所以没暴露，但这类
    "按 loop 的 RunVar + 按进程的幂等标记"错配是可复发的（b14 的 LOW-4 是同一族的另一处）。
    """
    import anyio.to_thread

    from src.core.api import server

    seen: list[int] = []

    def one_loop() -> None:
        async def check() -> None:
            anyio.to_thread.current_default_thread_limiter().total_tokens = 40   # 先还原成默认
            server.bound_threadpool_once()
            seen.append(anyio.to_thread.current_default_thread_limiter().total_tokens)

        asyncio.run(check())

    one_loop()
    one_loop()                                       # 第二个循环：旧实现会在这里停在 40
    assert seen == [server.THREADPOOL_TOKENS] * 2, (
        f"每个事件循环都必须被收窄到 {server.THREADPOOL_TOKENS}，实测 {seen}")


def test_常量不会比默认值更大():
    from src.core.api import server
    assert 0 < server.THREADPOOL_TOKENS <= 40, server.THREADPOOL_TOKENS
    assert server.THREADPOOL_TOKENS != 40, "收窄成 40 等于没收窄（anyio 默认就是 40）"


def test_每个请求都会尝试收窄(client, monkeypatch):
    """挡"有人把中间件里那一行删了"：拿替身记录它被调用过。"""
    from src.core.api import server

    calls = []
    monkeypatch.setattr(server, "bound_threadpool_once", lambda: calls.append(1))
    c, _ = client
    assert c.get("/api/v1/health").status_code == 200
    assert calls, "请求路径上没有调用 bound_threadpool_once（线程池就回到无界的 40）"


# ---------------------------------------------------------------- 重活专用闸门（§10.82）
class TestHeavyGate:
    """重活闸门：**重活路径**上必须 acquire/release，**轻活路径**不许碰它。

    为什么要这两条：闸门最容易坏的方式不是"算错令牌数"，而是**接线漏了**——
    路径表改了名、中间件那几行被顺手删掉，都会让"重活最多 4 条"**静默失效**
    （而失效的表现是"一切都正常，只是偶尔很慢"，最难发现）。
    """

    def test_重活路径表覆盖了那些被量出秒级的端点(self):
        from src.core.api import server
        for p in ("/api/v1/ingest/preview",
                  "/api/v1/documents/doc_x/figure/1",
                  "/api/v1/materials/projects/prj_x/scan",
                  "/api/v1/report/research",
                  "/api/v1/ks/answer",
                  # §10.93：这 5 条从 `async def + asyncio.to_thread` 改回 `def`（回到这口有界池）
                  # ⇒ 也必须吃重活令牌：分钟级全量爬取 / 下载+转 PDF+入库 / 逐次网络请求。
                  "/api/v1/laws/catalog/refresh",
                  "/api/v1/laws/ingest",
                  "/api/v1/laws/search",
                  "/api/v1/laws/check-updates",
                  "/api/v1/laws/verify",
                  # 2026-09-24（独立复核 MED-3）：合规护栏会在线程里打 **2s 外网**（Jev API），
                  # 缺令牌 ⇒ 每条用户消息都占 16 个池令牌之一、别的端点跟着排队。
                  "/api/v1/laws/compliance-guard"):
            assert server.is_heavy_path(p), p
        assert server.HEAVY_TOKENS < server.THREADPOOL_TOKENS, (
            "重活闸门必须**小于**线程池上限，否则等于没有给文件流留位")

    def test_laws_里两条廉价端点不被关进闸门(self):
        """§10.93：`/laws/*` **只逐条列重活**，不用前缀——否则会顺手把两条廉价端点也关起来。

        两条要**故意**留在闸门外的：
          · `GET /laws/catalog`：本地一读 + 索引已就绪的快路径（§10.88 起读路径不拿写锁）；
          · `GET /laws/sources`：纯静态字典。
        把它们排到一条分钟级爬取后面，正是 §10.82 记的"**闸门自己造排队**"那个坑。
        ⚠ 反面：若图省事写成前缀 `/api/v1/laws/` + 用 `/api/v1/laws/catalog` 去 `HEAVY_SKIP`，
        `startswith` 会**连 `/laws/catalog/refresh` 一起豁免**（把最重的那条放跑）——
        下面最后一条断言就是钉这个的。
        """
        from src.core.api import server
        assert not server.is_heavy_path("/api/v1/laws/catalog")
        assert not server.is_heavy_path("/api/v1/laws/sources")
        assert server.is_heavy_path("/api/v1/laws/catalog/refresh"), (
            "`/laws/catalog/refresh` 必须仍是重活（前缀写宽了就会漏掉它）")

    def test_asyncio_to_thread_绕过_anyio_闸门(self):
        """**§10.93 的立论**：`asyncio.to_thread` 不受 anyio 那道 16 令牌的约束（所以禁用）。

        这条是"判据的理由"，不是"判据"（判据是 `tests/test_material_api.py::
        test_端点上不许用_asyncio_to_thread` 的 AST 扫描）。做法：
        在**新事件循环**里把 anyio 默认 limiter 收到 **2**，再各起 8 条并发去跑同一个
        "睡 0.1s"的函数——`anyio.to_thread.run_sync` 的并发峰值必须 **≤ 2**，
        而 `asyncio.to_thread` 会明显超过它（它走 asyncio 默认执行器，
        worker 数 = `min(32, cpu+4) ≥ 5`）。

        ⚠ 为什么这条值得留着：两处注释（§10.81/§10.86）**早就写着**这个不对称，但直到 §10.93
        才把它变成判据——期间 `/laws/*` 五条一直"自称让出了事件循环"。这类
        "**文档知道、代码没管**"的缺口会复发，所以理由本身也要有回归锚。
        """
        import asyncio
        import os
        import threading
        import time

        import anyio.to_thread

        N = 8
        SLEEP = 0.1

        def _probe(runner) -> int:
            """跑 N 条并发，返回并发峰值。"""
            peak = {"live": 0, "max": 0}
            lock = threading.Lock()

            def work():
                with lock:
                    peak["live"] += 1
                    peak["max"] = max(peak["max"], peak["live"])
                try:
                    time.sleep(SLEEP)
                finally:
                    with lock:
                        peak["live"] -= 1

            async def main() -> None:
                anyio.to_thread.current_default_thread_limiter().total_tokens = 2
                assert anyio.to_thread.current_default_thread_limiter().total_tokens == 2
                await asyncio.gather(*[runner(work) for _ in range(N)])

            asyncio.run(main())
            return peak["max"]

        async def via_anyio(fn):
            return await anyio.to_thread.run_sync(fn)

        async def via_asyncio(fn):
            return await asyncio.to_thread(fn)

        workers = min(32, (os.cpu_count() or 1) + 4)
        peak_anyio = _probe(via_anyio)
        peak_asyncio = _probe(via_asyncio)
        assert peak_anyio <= 2, (
            f"anyio 池被设成 2 个令牌，并发峰值却是 {peak_anyio}（收窄没生效？）")
        assert peak_asyncio >= 4, (
            f"`asyncio.to_thread` 的并发峰值只有 {peak_asyncio}（默认执行器 worker={workers}）："
            "这条用例是在证明它**绕过** anyio 的令牌数；若它不再绕过，"
            "§10.93 的判据就该重新论证，而不是继续禁用")


    def test_轻活路径不占重活闸门(self, client, monkeypatch):
        from src.core.api import server

        events: list[str] = []

        class _Spy:
            def acquire(self):          # 中间件里是 `await limiter.acquire()`
                async def _a():
                    events.append("acquire")
                return _a()

            def release(self):
                events.append("release")

        monkeypatch.setattr(server, "_get_heavy_limiter", lambda: _Spy())
        c, _ = client
        assert c.get("/api/v1/health").status_code == 200
        assert c.get("/api/v1/documents", headers=HDR).status_code == 200
        assert events == [], f"轻活路径不该动重活闸门：{events}"

    def test_重活路径会_acquire_并_release(self, client, monkeypatch):
        from src.core.api import server

        events: list[str] = []

        class _Spy:
            def acquire(self):
                async def _a():
                    events.append("acquire")
                return _a()

            def release(self):
                events.append("release")

        monkeypatch.setattr(server, "_get_heavy_limiter", lambda: _Spy())
        c, _ = client
        # 走一条**存在**且轻量的重活路径（`/api/v1/snapshots` GET 列表）——我们测的是**接线**，
        # 不是端点的耗时；失败也无所谓（4xx 也会经过中间件）。
        r = c.get("/api/v1/snapshots", headers=HDR)
        assert r.status_code in (200, 404), r.status_code
        assert events == ["acquire", "release"], f"重活路径没有正确 acquire/release：{events}"

    def test_廉价的前缀例外不被关在闸门里(self):
        """`/ingest/preview/inbox` 只是列目录 ⇒ 必须在 `HEAVY_SKIP` 里（**闸门自己不许造排队**）。"""
        from src.core.api import server
        assert not server.is_heavy_path("/api/v1/ingest/preview/inbox")
        assert server.is_heavy_path("/api/v1/ingest/preview")          # 单文件预览仍是重活
        assert server.is_heavy_path("/api/v1/ingest/preview/batch")

    def test_重活闸门真的把并发卡在_HEAVY_TOKENS(self, tmp_path, monkeypatch):
        """**行为级**：真发 `HEAVY_TOKENS * 3` 条并发重活请求，并发峰值必须**恰好**是 `HEAVY_TOKENS`。

        为什么这条比"接线断言"更硬：接线对了但令牌数写成 40，前面几条全绿而闸门等于没有。
        这里用一个**替身**替换 `/ingest/preview` 真正调用的那个函数（模块级，端点内部
        `from ... import dry_run` ⇒ 补模块属性有效），替身记录"同时在跑几个"。

        ⚠ 独立性：这条（以及本类其余几条）**用真 app + 真中间件**，但走的是
        `httpx.ASGITransport`（进程内）——它**看得见非流式**的早放/漏放，看不见"流式响应
        期间令牌被提前放掉"（b14 的 MEDIUM-1：`BaseHTTPMiddleware.call_next` 在
        `http.response.start` 就返回）。流式那条由下面的
        `test_流式响应的令牌要等响应体发完才放` 用**假 ASGI app 直接驱动中间件**覆盖
        （为什么不走真端点：起一条真 SSE 流要种一整套合规评审数据，那是
        `tests/test_compliance.py` 的覆盖，这里只钉**闸门对流的时序**）。
        """
        import asyncio
        import threading
        import time

        import httpx

        from src.core.api import server
        from src.core.ingestion import dry_run

        peak = {"live": 0, "max": 0}
        lock = threading.Lock()

        def _slow(*_a, **_k):
            with lock:
                peak["live"] += 1
                peak["max"] = max(peak["max"], peak["live"])
            try:
                time.sleep(0.15)
                return {"status": "ok"}
            finally:
                with lock:
                    peak["live"] -= 1

        monkeypatch.setattr(dry_run, "analyze_preview_report", _slow)
        import fitz
        pdf = tmp_path / "gate.pdf"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(pdf))
        doc.close()

        n = server.HEAVY_TOKENS * 3

        async def main() -> None:
            # ⚠ token 必须与 HDR 一致：第一版写成 `create_app("t")` 而头里是
            # `test-token-123` ⇒ 12 条全部 401、替身根本没被调用（峰值 0），
            # 而断言看起来像"闸门没生效"。**401 也会经过中间件**，所以这类错最容易骗过接线断言。
            app = server.create_app("test-token-123")
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://gate") as c:
                await asyncio.gather(*[
                    c.post("/api/v1/ingest/preview", json={"path": str(pdf)}, headers=HDR)
                    for _ in range(n)])

        asyncio.run(main())
        assert peak["max"] == server.HEAVY_TOKENS, (
            f"{n} 条并发的并发峰值 = {peak['max']}，应为 {server.HEAVY_TOKENS}")

    # ------------------------------------------------ 流式响应必须把令牌**持到响应体发完**
    @staticmethod
    def _spy(server, monkeypatch):
        """一个记账替身 limiter + 让它成为闸门用的 limiter。"""

        class _Spy:
            def __init__(self) -> None:
                self.live = 0
                self.acquires = 0
                self.releases = 0

            def acquire(self):
                async def _a() -> None:
                    self.live += 1
                    self.acquires += 1
                return _a()

            def release(self) -> None:
                self.live -= 1
                self.releases += 1

        spy = _Spy()
        monkeypatch.setattr(server, "_get_heavy_limiter", lambda: spy)
        return spy

    def test_流式响应的令牌要等响应体发完才放(self, monkeypatch):
        """**为什么闸门必须是纯 ASGI**（b14 的 MEDIUM-1）。

        `BaseHTTPMiddleware.call_next` **只等到 `http.response.start` 就返回**，响应体的
        流式发送发生在那**之后** ⇒ `@app.middleware("http")` 里的 `finally: release()` 会在
        **响应体开流之前**跑完，SSE 重活（`/compliance/review/{id}/execute`、`/ks/answer`）
        的令牌**立刻被放掉**，闸门对它等于不存在（复核实测：非流式峰值 4、流式峰值 12）。

        判据用**假 ASGI app** 直接驱动真中间件，不靠计时：响应体分 3 块发，前两块
        `more_body=True` 期间闸门必须**仍持有**，最后一块（`more_body=False`）发完才归零，
        且**恰好释放一次**（多放会把闸门撑大 —— 同样是静默失效）。
        """
        import asyncio

        from src.core.api import server

        spy = self._spy(server, monkeypatch)
        sent: list[dict] = []
        live_at_send: list[int] = []

        async def fake_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            live_at_send.append(spy.live)
            await send({"type": "http.response.body", "body": b"a", "more_body": True})
            live_at_send.append(spy.live)
            await send({"type": "http.response.body", "body": b"b", "more_body": True})
            live_at_send.append(spy.live)
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            live_at_send.append(spy.live)

        async def send(message):
            sent.append(message)

        async def main() -> None:
            mw = server._HeavyGateMiddleware(fake_app)
            await mw({"type": "http", "path": "/api/v1/ingest/preview", "headers": []},
                     None, send)

        asyncio.run(main())
        assert (spy.acquires, spy.releases) == (1, 1), (
            "同一个请求只能 acquire 一次、release 一次（多放 = 闸门被撑大，"
            f"同样是静默失效）：{spy.acquires}/{spy.releases}")
        assert live_at_send == [1, 1, 1, 0], (
            f"流式期间令牌必须一直被持有，最后一块发完才放：{live_at_send}")
        assert spy.live == 0
        # 包装层不许改动/吞掉 ASGI 消息
        assert [m["type"] for m in sent] == [
            "http.response.start", "http.response.body",
            "http.response.body", "http.response.body"]
        assert [m.get("more_body") for m in sent[1:]] == [True, True, False]

    def test_异常或截断路径也必须释放且只放一次(self, monkeypatch):
        """`app` 中途抛错（或从不发最后一块）⇒ `finally` 兜底释放，**且只放一次**。

        为什么要有这条：闸门漏放 = 4 个令牌被永久吃掉 ⇒ 剩下 3 条重活（**越用越慢**，
        且没有任何报错）。而"释放两次"同样坏：令牌数会越放越多 ⇒ 闸门静默失效。
        """
        import asyncio

        import pytest as _pytest

        from src.core.api import server

        spy = self._spy(server, monkeypatch)
        sent: list[dict] = []

        async def boom_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"a", "more_body": True})
            raise RuntimeError("渲染中途炸了")

        async def send(message):
            sent.append(message)

        async def main() -> None:
            mw = server._HeavyGateMiddleware(boom_app)
            with _pytest.raises(RuntimeError, match="渲染中途炸了"):
                await mw({"type": "http", "path": "/api/v1/report/research", "headers": []},
                         None, send)

        asyncio.run(main())
        assert spy.acquires == 1 and spy.releases == 1, (spy.acquires, spy.releases)
        assert spy.live == 0
        assert [m["type"] for m in sent] == ["http.response.start", "http.response.body"]

    def test_闸门缓存不会把死循环留在字典里(self):
        """LOW-4：缓存键必须是**循环对象**（弱引用字典），不是 `id(loop)`。

        判据（行为级）：跑完一个事件循环后，缓存里**不该**多出它——`WeakKeyDictionary`
        随循环被回收而清场；而拿 `id(loop)` 做键的普通 dict 会**永久留着**那一项，
        且地址复用后新循环会拿到一个**绑在死循环上**的 limiter（anyio 的 limiter 内部是
        RunVar，只在创建它的循环上有效）⇒ 行为诡异而**不报错**。
        顺带钉住缓存真的在起作用：同一循环里两次取，必须是**同一个** limiter。
        """
        import gc

        from src.core.api import server

        async def main() -> None:
            a = server._get_heavy_limiter()
            b = server._get_heavy_limiter()
            assert a is b, "同一个事件循环里两次取到了不同的重活闸门（缓存没生效）"
            assert a.total_tokens == server.HEAVY_TOKENS

        gc.collect()
        before = len(server._heavy_limiters)
        asyncio.run(main())
        gc.collect()
        assert len(server._heavy_limiters) <= before, (
            "重活闸门缓存把已结束的事件循环留在字典里（键应改成弱引用的循环对象，"
            "不能用 id(loop)——地址复用会让新循环拿到死循环上的 limiter）")

    def test_非重活路径在中间件这一层就不碰闸门(self, monkeypatch):
        """轻活路径连 `acquire` 都不该调（不是"调了又立刻放"——那也会排队）。"""
        import asyncio

        from src.core.api import server

        spy = self._spy(server, monkeypatch)
        called: list[str] = []

        async def fake_app(scope, receive, send):
            called.append("app")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}", "more_body": False})

        async def send(message):
            pass

        async def main() -> None:
            mw = server._HeavyGateMiddleware(fake_app)
            await mw({"type": "http", "path": "/api/v1/health", "headers": []}, None, send)

        asyncio.run(main())
        assert called == ["app"]
        assert (spy.acquires, spy.releases, spy.live) == (0, 0, 0)


