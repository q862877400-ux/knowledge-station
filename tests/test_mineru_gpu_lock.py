"""GPU 深度解析排队锁（_gpu_deep_lock）行为测试。

背景：三分片并发上卡导致 CUDA OOM 瞬败（2026-08-27），修复为跨进程
文件锁串行化 do_parse。锁语义：互斥、等待超时抛 TimeoutError、
KS_GPU_LOCK=0 直通、持锁崩溃由 OS 释放（进程死亡自动解锁，此处以
正常释放路径覆盖）。
"""
from __future__ import annotations

import os

import pytest

from src.core.ingestion.mineru_adapter import _gpu_deep_lock


@pytest.fixture(autouse=True)
def _lock_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KS_GPU_LOCK_PATH", str(tmp_path / "gpu.lock"))
    monkeypatch.delenv("KS_GPU_LOCK", raising=False)
    monkeypatch.delenv("KS_GPU_LOCK_TIMEOUT", raising=False)


def test_gpu_lock_互斥_第二持锁者等待期间抢不到():
    with _gpu_deep_lock():
        os.environ["KS_GPU_LOCK_TIMEOUT"] = "0.6"
        with pytest.raises(TimeoutError):
            with _gpu_deep_lock():
                pass  # 不应到达
    del os.environ["KS_GPU_LOCK_TIMEOUT"]


def test_gpu_lock_释放后_可再次获取():
    with _gpu_deep_lock():
        pass
    with _gpu_deep_lock():  # 不抛即通过（无超时残留）
        pass


def test_gpu_lock_禁用开关_KS_GPU_LOCK_0_直通(monkeypatch):
    monkeypatch.setenv("KS_GPU_LOCK", "0")
    with _gpu_deep_lock():
        with _gpu_deep_lock():  # 直通模式可嵌套获取
            pass
