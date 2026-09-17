# -*- coding: utf-8 -*-
"""向量引擎的**健康语义**与**失败冷却**（§10.74）。

这一组测试锁的是量具实测逼出来的两条纪律：
  1. **廉价路径不许触发加载**：`/health`、健康看板、检索 debug 只能读已有证据；
     "加载一个模型来判断它能不能加载"会把体检变成 6.6s 的阻塞重活（实测值）。
  2. **失败要进冷却窗口**：`_load_error` 原先只记不缓存 ⇒ 一次失败之后每次调用都重试。

判据都是**行为级**（计数替身 + 断言没被调用），不是"源码里有那个词"。
"""
from __future__ import annotations

import pytest

from src.core.retrieval import embedder as emb

HDR = {"Authorization": "Bearer test-token-123"}


@pytest.fixture()
def clean_embedder(monkeypatch):
    """把 embedder 的单例状态清干净，并在测试后恢复（模块级全局，必须自己收尾）。"""
    monkeypatch.setattr(emb, "_model", None)
    monkeypatch.setattr(emb, "_load_error", None)
    monkeypatch.setattr(emb, "_error_at", 0.0)
    return emb


class TestHealthIsCheap:
    """`health()` 三态**只读证据**，且**绝不触发加载**。"""

    def test_从没试过时是_unknown_而不是去加载(self, clean_embedder, monkeypatch):
        calls = []

        def _boom():
            calls.append(1)
            raise AssertionError("health() 不该触发加载")

        monkeypatch.setattr(emb, "_import_text_embedding", _boom)
        assert emb.health() == "unknown"
        assert calls == [], "健康判据触发了模型加载"

    def test_加载成功过才是_ok(self, clean_embedder):
        clean_embedder._model = object()          # 模拟"本进程真的加载成功过"
        assert emb.health() == "ok"

    def test_最近一次失败是_offline(self, clean_embedder, monkeypatch):
        def _boom():
            raise RuntimeError("模拟加载失败")

        monkeypatch.setattr(emb, "_import_text_embedding", _boom)
        assert emb.is_available() is False
        assert emb.health() == "offline"
        assert emb.offline_reason() and "模拟加载失败" in emb.offline_reason()


class TestFailureCooldown:
    """失败**进冷却窗口**：窗口内不重试，窗口过去后允许再试（不永久拉黑）。"""

    def test_窗口内不重试(self, clean_embedder, monkeypatch):
        calls = []

        def _boom():
            calls.append(1)
            raise RuntimeError("模拟加载失败")

        monkeypatch.setattr(emb, "_import_text_embedding", _boom)
        assert emb.is_available() is False
        assert emb.is_available() is False
        assert emb.is_available() is False
        assert len(calls) == 1, (
            f"冷却窗口内重试了 {len(calls)} 次——这正是'每次调用都付一次网络超时'的来源")

    def test_窗口过去后允许再试一次(self, clean_embedder, monkeypatch):
        calls = []

        def _boom():
            calls.append(1)
            raise RuntimeError("模拟加载失败")

        monkeypatch.setattr(emb, "_import_text_embedding", _boom)
        assert emb.is_available() is False
        assert len(calls) == 1
        # 把"上次失败时刻"拨回冷却窗口之外（等价于等满 60s，不真等）
        monkeypatch.setattr(emb, "_error_at", emb._error_at - emb.RETRY_COOLDOWN_S - 1.0)
        assert emb.is_available() is False
        assert len(calls) == 2, "窗口过去后应当再试一次（否则瞬时故障会永久拉黑向量引擎）"

    def test_成功之后清掉上次失败(self, clean_embedder, monkeypatch):
        """先失败、冷却过去、再成功 ⇒ `_load_error` 必须被清掉，`health()` 变 ok。"""
        state = {"fail": True, "calls": 0}

        class _FakeModel:
            def embed(self, texts):                       # pragma: no cover - 本用例不嵌入
                return [[0.0]]

        def _loader():
            state["calls"] += 1
            if state["fail"]:
                raise RuntimeError("模拟加载失败")
            return lambda **kw: _FakeModel()

        monkeypatch.setattr(emb, "_import_text_embedding", _loader)
        assert emb.is_available() is False
        assert emb.health() == "offline"
        monkeypatch.setattr(emb, "_error_at", emb._error_at - emb.RETRY_COOLDOWN_S - 1.0)
        state["fail"] = False
        assert emb.is_available() is True
        assert emb.health() == "ok"
        assert emb.offline_reason() is None, "成功之后必须清掉上次失败，否则 health 永远 offline"
        assert emb.is_available() is True and state["calls"] == 2

    def test_窗口长度是个正数秒的常量(self):
        assert isinstance(emb.RETRY_COOLDOWN_S, float) and emb.RETRY_COOLDOWN_S > 0


class TestHealthEndpointsDoNotLoad:
    """**HTTP 层**：健康类端点不许触发模型加载（判据 = 替身没被调用）。"""

    @pytest.mark.parametrize("path", ["/api/v1/health", "/api/v1/diagnostics/health-board"])
    def test_健康端点不加载向量模型(self, client, clean_embedder, monkeypatch, path):
        calls = []

        def _boom():
            calls.append(1)
            raise AssertionError("健康端点触发了向量模型加载")

        monkeypatch.setattr(emb, "_import_text_embedding", _boom)
        c, _ = client
        r = c.get(path, headers=HDR)
        assert r.status_code == 200, r.text
        assert calls == [], f"{path} 触发了向量模型加载（那会把引擎堵住数秒）"

    def test_health_的_vector_engine_取值在三态之内(self, client, clean_embedder):
        c, _ = client
        body = c.get("/api/v1/health", headers=HDR).json()
        assert body["vector_engine"] in ("ok", "offline", "unknown"), body

    def test_健康看板的_vector_同样在三态之内(self, client, clean_embedder):
        c, _ = client
        data = c.get("/api/v1/diagnostics/health-board", headers=HDR).json()["data"]
        assert data["engines"]["vector"] in ("ok", "offline", "unknown"), data["engines"]
