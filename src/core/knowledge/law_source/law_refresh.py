"""法规目录定时刷新循环（spec 006）。

## 为什么单独一个模块，而不是接进 `src/core/update/scheduler.py`

原计划是把刷新接进既有的 `UpdateScheduler.tick()`。动手前核"它到底跑不跑"，
实测结论是**不跑**：`tick()` 只被 `_run()` 调、`_run()` 只被 `start()` 拉，
而 `start()` **全仓无人调用**（`git grep UpdateScheduler -- src` 只命中类定义与
re-export，其余命中全在测试）。`server.py` 的 `run()` 是唯一生产启动点，
里面只启动了 `start_write_worker()`。

⇒ 接进 `tick()` 等于**刷新永不执行**（又一个假绿）。故照抄
`write_queue_bootstrap.start_write_worker()` 的既有先例自建线程。

**为什么不去修那个死调度器**：启动它 = 每 7 天自动建巡检批、进日预算池，
那是业主没要求的行为变更。本轮只登记，不顺手实施。

## 线程模型

单 daemon 线程，按 `poll_interval` 唤醒一次，调
`catalog.refresh_catalog_if_due()`；是否真的刷新由 `law.catalog_refresh_days`
决定（缺省 1 天）。`start` 幂等、`stop` 可干净关停（测试要能收干净）。

每个线程持有**自己的** `Event`（不是模块级共享）——否则 stop 后立刻 start
会把新线程的 Event 清掉，旧线程随即"复活"再跑一轮。
"""

from __future__ import annotations

import logging
import threading

from src.core.knowledge.law_source import catalog

logger = logging.getLogger(__name__)

#: 线程唤醒间隔（秒）。⚠ 与"刷新周期"是两个概念：这是轮询心跳，
#: 刷新周期是 `law.catalog_refresh_days`（天级）。取 1 小时——
#: 刷新粒度是天，小时级心跳足够且几乎无开销（未到期时不碰网络）。
_POLL_INTERVAL_S = 3600.0

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop: threading.Event | None = None


def _run(poll_interval: float, stop: threading.Event) -> None:
    """循环体：直到本线程的 stop 被置位。单次异常不得终止循环。"""
    while not stop.is_set():
        try:
            out = catalog.refresh_catalog_if_due()
            if out.get("skipped"):
                logger.debug("法规目录刷新跳过: %s", out.get("reason"))
            else:
                res = out.get("result") or {}
                logger.info("法规目录刷新完成: total=%s written=%s",
                            res.get("total"), res.get("written"))
        except Exception as exc:  # noqa: BLE001 — 后台线程必须吞异常存活
            logger.warning("法规目录刷新失败（下个周期重试）: %s: %s",
                           type(exc).__name__, exc)
        stop.wait(poll_interval)


def start_law_refresh(poll_interval: float = _POLL_INTERVAL_S) -> bool:
    """拉起刷新线程；已在跑则不动（幂等）。返回是否**本次新起**了线程。"""
    global _thread, _stop
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        stop = threading.Event()
        _stop = stop
        _thread = threading.Thread(target=_run, args=(poll_interval, stop),
                                   name="ks-law-refresh", daemon=True)
        _thread.start()
        return True


def stop_law_refresh(timeout: float = 5.0) -> bool:
    """置位停止并等线程退出。返回**线程是否真的退出了**。

    未在跑 ⇒ 返回 True（幂等，无操作）。

    ⚠ **join 超时不许把引用丢掉**（2026-10-10 独立复核 P2-4 打回，已就地更正）：
    第一版无论如何都 `_thread = None`，于是——
    ① `is_running()` **假阴**（明明还有线程在跑）；
    ② 紧接着 `start_law_refresh()` 会**再起一个线程** ⇒ **两个线程并发刷新**。
    虽然刷新本身幂等（upsert）兜底、生产触发面也小（只在引擎关停路径），
    但"说停了其实没停"是**状态谎报**，必须修。

    现在：**只有 join 成功才清引用**；超时则保留（`is_running()` 继续报真、
    `start_law_refresh()` 会拒绝重复起线程），并把事件置位让它在下一拍自行退出。
    """
    global _thread, _stop
    with _lock:
        thread, stop = _thread, _stop
    if stop is not None:
        stop.set()
    if thread is None:
        return True
    thread.join(timeout=timeout)
    if thread.is_alive():
        # 没退干净：保留引用（不谎报"已停"），也不再接受新线程
        logger.warning("法规刷新线程 %.1fs 内未退出，保留引用避免并发起新线程", timeout)
        return False
    with _lock:
        # 只有当引用仍是这一个时才清（防期间被 start 换过）
        if _thread is thread:
            _thread, _stop = None, None
    return True


def is_running() -> bool:
    """线程是否在跑（测试与诊断用）。"""
    with _lock:
        return _thread is not None and _thread.is_alive()
