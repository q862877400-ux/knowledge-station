# -*- coding: utf-8 -*-
"""**量具自己的闸门**：`scripts/measure-endpoint-blocking.py` 必须真的分得开
"把事件循环堵住了"与"没堵"（§10.73）。

为什么必须有这条：§10.73 起的每一个"改前/改后"数字都出自那把尺。**量具没有闸门的话**，
它坏掉的那天（心跳协程写错、`stop` 早置、样本没采到）所有"改后掉回噪声底"都会变成
**假绿**——而且是**最难发现**的那种假绿：数字看起来完全合理，只是永远是 0。

判据用**合成对照**（不依赖真实引擎、不依赖任何 fixture、~0.7s）：
  · 一条 `async def` 端点里 `time.sleep(0.3)` ⇒ 事件循环被堵 ⇒ `max_gap ≈ 0.3s`；
  · 一条 `def` 端点里同样 `time.sleep(0.3)`（Starlette 丢线程池）⇒ 心跳照跳 ⇒ `max_gap` 很小。
两条端点的**请求耗时相同**：这证明尺量的是"**谁被占住**"，不是"谁慢"。
"""
from __future__ import annotations

import asyncio
import importlib.util
import time
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "scripts" / "measure-endpoint-blocking.py"
_spec = importlib.util.spec_from_file_location("ks_measure_harness", _SRC)
assert _spec and _spec.loader
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)

SLEEP_S = 0.3


def _synthetic_app():
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/blocking")
    async def blocking():            # async def + 同步 sleep ⇒ 堵住事件循环
        time.sleep(SLEEP_S)
        return {"ok": True}

    @app.get("/threaded")
    def threaded():                  # def ⇒ Starlette 丢线程池 ⇒ 不堵
        time.sleep(SLEEP_S)
        return {"ok": True}

    return app


@pytest.fixture(scope="module")
def app():
    return _synthetic_app()


def test_尺能量出_async_def_把事件循环堵住(app):
    out = asyncio.run(harness.measure(app, "GET", "/blocking", headers={}))
    assert out["status"] == 200
    assert out["duration_s"] >= SLEEP_S * 0.8, out
    # 堵住了 ⇒ 最大空档≈整段耗时（放宽一点，容器/CI 上抖动大）
    assert out["max_gap_s"] >= SLEEP_S * 0.7, out
    assert out["blocked_s_lower_bound"] >= SLEEP_S * 0.6, out


def test_尺能量出_def_没有把事件循环堵住(app):
    out = asyncio.run(harness.measure(app, "GET", "/threaded", headers={}))
    assert out["status"] == 200
    assert out["duration_s"] >= SLEEP_S * 0.8, out          # 活照干，耗时一样
    # 没堵 ⇒ 空档回到心跳分辨率量级（远小于 0.3s）
    assert out["max_gap_s"] < SLEEP_S / 2, out
    assert out["samples"] >= 5, out                          # 心跳真的在跳（防"没采到样本"式假绿")


def test_两条端点的耗时同量级_证明尺量的是谁被占住而不是谁慢(app):
    blocking = asyncio.run(harness.measure(app, "GET", "/blocking", headers={}))
    threaded = asyncio.run(harness.measure(app, "GET", "/threaded", headers={}))
    assert abs(blocking["duration_s"] - threaded["duration_s"]) < SLEEP_S / 2, (blocking, threaded)
    assert blocking["max_gap_s"] > threaded["max_gap_s"] * 3, (blocking, threaded)
