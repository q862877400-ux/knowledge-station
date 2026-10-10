"""法规目录定时刷新测试（spec 006 T013）。

全程 mock 网络（`catalog.refresh_catalog` 被替换），零真实请求。

覆盖：
- `refresh_days()` 缺省 / 非法 / 关闭 三种读法；
- `refresh_catalog_if_due()` 到期触发 / 未到期跳过 / 关闭不触发；
- **失败不写 `last_refresh_at`**（否则一次失败会被当成"刷过了"）；
- 后台线程 start 幂等 / stop 干净 / 循环体吞异常存活；
- **生产启动点确实调了 `start_law_refresh`**（否则又是一个"接进去但没人拉"的假绿）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.core.knowledge.law_source import catalog, law_refresh

T0 = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)


def _set_cfg(key: str, value: str | None) -> None:
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as txn:
        if value is None:
            txn.execute("DELETE FROM app_config WHERE config_key=?", (key,))
        else:
            txn.execute(
                "INSERT INTO app_config(config_key, config_value) VALUES(?,?)"
                " ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value",
                (key, value))


@pytest.fixture()
def cfg(db):
    """清掉刷新相关配置，用例自己设（避免会话级共享库里的残留）。"""
    _set_cfg(catalog.REFRESH_DAYS_KEY, None)
    _set_cfg(catalog.LAST_REFRESH_KEY, None)
    yield
    _set_cfg(catalog.REFRESH_DAYS_KEY, None)
    _set_cfg(catalog.LAST_REFRESH_KEY, None)


def _fake_refresh(monkeypatch, calls: list):
    def fake(*a, **kw):
        calls.append(True)
        return {"total": 30900, "written": 1187, "skipped": 0,
                "by_category": {}, "warnings": [], "elapsed_sec": 0.1}
    monkeypatch.setattr(catalog, "refresh_catalog", fake)


# ---------------------------------------------------------------- refresh_days

def test_refresh_days_default_is_one(cfg):
    """未设 ⇒ 缺省 1 天。"""
    assert catalog.refresh_days() == 1


@pytest.mark.parametrize("raw,expect", [("7", 7), ("0", 0), ("-3", 0),
                                        ("abc", 0), ("", 0), ("2.9", 2)])
def test_refresh_days_values(cfg, raw, expect):
    _set_cfg(catalog.REFRESH_DAYS_KEY, raw)
    assert catalog.refresh_days() == expect


# ------------------------------------------------------- refresh_catalog_if_due

def test_due_when_never_refreshed(cfg, monkeypatch):
    """从没刷过 ⇒ 视为到期，触发刷新并写 last_refresh_at。"""
    calls: list = []
    _fake_refresh(monkeypatch, calls)
    out = catalog.refresh_catalog_if_due(now=T0)
    assert out["skipped"] is False and out["reason"] == "refreshed"
    assert calls == [True]
    assert out["result"]["total"] == 30900        # 明细在 result 里
    assert catalog._read_config(catalog.LAST_REFRESH_KEY)


def test_skips_when_not_due(cfg, monkeypatch):
    """刚刷过（1 天内）⇒ 跳过，且**不碰网络**。"""
    calls: list = []
    _fake_refresh(monkeypatch, calls)
    _set_cfg(catalog.LAST_REFRESH_KEY, (T0 - timedelta(hours=3)).isoformat())
    out = catalog.refresh_catalog_if_due(now=T0)
    assert out["skipped"] is True and out["reason"] == "not_due"
    assert calls == []


def test_due_again_after_period(cfg, monkeypatch):
    """超过周期 ⇒ 再次触发。"""
    calls: list = []
    _fake_refresh(monkeypatch, calls)
    _set_cfg(catalog.LAST_REFRESH_KEY, (T0 - timedelta(days=2)).isoformat())
    out = catalog.refresh_catalog_if_due(now=T0)
    assert out["skipped"] is False
    assert calls == [True]


def test_disabled_when_zero(cfg, monkeypatch):
    """周期 ≤0 ⇒ 关闭，不触发。"""
    calls: list = []
    _fake_refresh(monkeypatch, calls)
    _set_cfg(catalog.REFRESH_DAYS_KEY, "0")
    out = catalog.refresh_catalog_if_due(now=T0)
    assert out["skipped"] is True and out["reason"] == "disabled"
    assert calls == []


def test_naive_last_refresh_treated_as_utc(cfg, monkeypatch):
    """历史值无时区 ⇒ 按 UTC 解释，不得抛 TypeError。"""
    calls: list = []
    _fake_refresh(monkeypatch, calls)
    _set_cfg(catalog.LAST_REFRESH_KEY, (T0 - timedelta(hours=1)).replace(tzinfo=None).isoformat())
    out = catalog.refresh_catalog_if_due(now=T0)
    assert out["skipped"] is True and out["reason"] == "not_due"


def test_failure_does_not_stamp_last_refresh(cfg, monkeypatch):
    """★ 刷新失败 MUST NOT 写 last_refresh_at —— 否则一整个周期不再重试。"""
    def boom(*a, **kw):
        raise RuntimeError("官方接口不可达")
    monkeypatch.setattr(catalog, "refresh_catalog", boom)
    with pytest.raises(RuntimeError):
        catalog.refresh_catalog_if_due(now=T0)
    assert catalog._read_config(catalog.LAST_REFRESH_KEY) is None


# ---------------------------------------------------------------- 后台线程

def test_start_is_idempotent_and_stop_cleans(cfg, monkeypatch):
    """start 两次只起一个线程；stop 之后不在跑。"""
    _fake_refresh(monkeypatch, [])
    try:
        assert law_refresh.start_law_refresh(poll_interval=30.0) is True
        assert law_refresh.start_law_refresh(poll_interval=30.0) is False
        assert law_refresh.is_running() is True
    finally:
        law_refresh.stop_law_refresh()
    assert law_refresh.is_running() is False


def test_loop_survives_exception(cfg, monkeypatch):
    """循环体抛异常不得终止线程（后台线程必须存活）。"""
    state = {"n": 0}

    def flaky(*a, **kw):
        state["n"] += 1
        raise RuntimeError("boom")
    monkeypatch.setattr(catalog, "refresh_catalog", flaky)
    try:
        law_refresh.start_law_refresh(poll_interval=0.05)
        import time
        time.sleep(0.4)
        assert law_refresh.is_running() is True, "线程被异常打死了"
        assert state["n"] >= 2, "异常后没有再跑下一轮"
    finally:
        law_refresh.stop_law_refresh()
    assert state["n"] >= 2


def test_restart_after_stop_runs_again(cfg, monkeypatch):
    """stop 后能再 start，且新线程**真的在跑**（每次新 Event，旧线程不得复活）。

    ⚠ 这里数的是 `refresh_catalog_if_due` 的**调用次数**，不是 `refresh_catalog`
    —— 第一次跑已把 `last_refresh_at` 盖上，重启后循环会正确地判"未到期"而跳过。
    那正是期望行为，故不能拿 `refresh_catalog` 计数。
    """
    seen: list = []

    def spy(*a, **kw):
        seen.append(True)
        return {"skipped": True, "reason": "not_due", "refresh_days": 1}
    monkeypatch.setattr(catalog, "refresh_catalog_if_due", spy)
    import time
    try:
        law_refresh.start_law_refresh(poll_interval=0.05)
        time.sleep(0.2)
        law_refresh.stop_law_refresh()
        assert law_refresh.is_running() is False
        before = len(seen)
        assert before >= 1, "第一次 start 后循环没跑"
        assert law_refresh.start_law_refresh(poll_interval=0.05) is True
        time.sleep(0.3)
        assert len(seen) > before, "重启后新线程没有再跑"
    finally:
        law_refresh.stop_law_refresh()


def test_stop_timeout_does_not_lie_or_double_start(cfg, monkeypatch):
    """★ join 超时后：`is_running()` 不得假阴，`start` 不得再起第二个线程。

    独立复核 2026-10-10 P2-4：第一版 stop 无条件清 `_thread` ⇒
    明明还有线程在跑却报"已停"，紧接着 start 会**并发起第二个刷新线程**。
    这里用一个"卡住不退出"的假线程复现该窗口。
    """
    import threading
    import time as _t

    started = threading.Event()

    def stubborn(poll_interval, stop):
        started.set()
        while not stop.is_set():
            _t.sleep(0.01)
        _t.sleep(30)          # 置位后仍赖着不走，模拟 join 超时

    monkeypatch.setattr(law_refresh, "_run", stubborn)
    try:
        assert law_refresh.start_law_refresh(poll_interval=0.05) is True
        assert started.wait(2.0), "假线程没起来"
        _t.sleep(0.1)
        ok = law_refresh.stop_law_refresh(timeout=0.3)
        assert ok is False, "线程没退出，stop 不该报 True"
        # ★ 关键：不许谎报"已停"
        assert law_refresh.is_running() is True, "is_running 假阴了"
        # ★ 关键：不许再起第二个
        assert law_refresh.start_law_refresh(poll_interval=0.05) is False, \
            "停不掉却允许再起一个 ⇒ 会并发刷新"
    finally:
        # 真收尾：让假线程的 30s 等待走完
        law_refresh._stop.set() if law_refresh._stop else None
        th = law_refresh._thread
        if th is not None:
            th.join(timeout=40)
        with law_refresh._lock:
            law_refresh._thread, law_refresh._stop = None, None


def test_stop_returns_true_when_clean(cfg, monkeypatch):
    """正常退出 ⇒ stop 返回 True（与超时分支可区分）。"""
    _fake_refresh(monkeypatch, [])
    try:
        law_refresh.start_law_refresh(poll_interval=0.05)
        assert law_refresh.stop_law_refresh(timeout=5.0) is True
    finally:
        law_refresh.stop_law_refresh()


# ------------------------------------------------- 生产启动点（防"接进去没人拉"）

def test_run_starts_and_stops_law_refresh():
    """★ 生产启动点 `server.run()` 必须真的**调用** start / stop 刷新线程。

    这条防的是那个死调度器的坑重演：代码完整、测试全绿，但生产路径上没人拉它。

    ⚠ **第一版是假绿的（就地留痕）**：原实现是
    `assert "start_law_refresh" in inspect.getsource(server.run)` —— 只查**字符串**。
    实测变异（把调用换成 `pass`）**测不出来**，因为 `run()` 里那行
    `from ... import start_law_refresh` 本身就含这个字符串。
    ⇒ 改成 AST：必须存在一个**真的 Call**，函数名是 `start_law_refresh` / `stop_law_refresh`。
    """
    import ast
    import inspect
    from src.core.api import server

    tree = ast.parse(inspect.getsource(server.run))
    called = {node.func.id for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "start_law_refresh" in called, "run() 没有真正调用 start_law_refresh"
    assert "stop_law_refresh" in called, "run() 没有真正调用 stop_law_refresh"


def test_refresh_module_is_not_the_dead_scheduler():
    """★ 反向断言：刷新线程**不依赖**那个死调度器（它的 start() 无人调用）。

    若将来有人把刷新改回挂到它上面，这条会红。
    ⚠ 断言的是**可执行代码**里没有它——模块 docstring 里解释了为什么不接它，
    那是说明文字，不算依赖。
    """
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(law_refresh))
    # 只看 import 与函数体，跳过 docstring
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    assert "scheduler" not in names, "刷新线程不该 import 死调度器"
    assert "UpdateScheduler" not in names, "刷新线程不该依赖死调度器"
