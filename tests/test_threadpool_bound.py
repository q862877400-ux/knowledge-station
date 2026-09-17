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
