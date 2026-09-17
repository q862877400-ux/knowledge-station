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
        server._bound_once = False
        server.bound_threadpool_once()
        return anyio.to_thread.current_default_thread_limiter().total_tokens

    got = asyncio.run(check())
    assert got == server.THREADPOOL_TOKENS, (got, server.THREADPOOL_TOKENS)


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
                  "/api/v1/compliance/review/t1/execute"):
            assert server.is_heavy_path(p), p
        assert server.HEAVY_TOKENS < server.THREADPOOL_TOKENS, (
            "重活闸门必须**小于**线程池上限，否则等于没有给文件流留位")

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
        """**行为级**：真发 10 条并发重活请求，并发峰值必须**恰好**是 `HEAVY_TOKENS`。

        为什么这条比"接线断言"更硬：接线对了但令牌数写成 40，前面几条全绿而闸门等于没有。
        这里用一个**替身**替换 `/ingest/preview` 真正调用的那个函数（模块级，端点内部
        `from ... import dry_run` ⇒ 补模块属性有效），替身记录"同时在跑几个"。
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


