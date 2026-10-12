"""更新巡检的定时线程（spec 011 第 ① 条）—— 把「已建成但没接线」的调度器接上生产。

## 为什么单独一个文件，而不是直接启动 `update/scheduler.py`

`scheduler.py` 的 `UpdateScheduler` **编排逻辑是对的**（建批 / 恢复预算暂停的批），
但它有两个缺口，本模块负责补上，而**不改它的编排语义**：

1. **没人启动它**：`UpdateScheduler.start()` 全仓无人调用 —— `server.py` 的注释
   自己写着"那个调度器的 `start()` 全仓无人调用（死代码）"。
2. **它只建批、不执行**：`tick()` 调 `inspector.create_inspect_batch()` 建出批次后
   就返回了，**批会一直躺在 `pending`**。真正的执行在 `routes_update.update_check`
   的 `_run()` 里（`inspector.run_batch`）。

⇒ 本模块照 `law_source/law_refresh.py` 的**既有先例**（单 daemon 线程 + 每线程自己的
`Event` + `start` 幂等 + `stop` 不谎报）自建线程，并在每次 tick 之后**把新批跑起来**。

## 线程模型

单 daemon 线程，按 `poll_interval` 唤醒一次：
① 调 `UpdateScheduler.tick()`（建批 / 恢复预算暂停的批）；
② 把 tick 返回的 `created` 批次**逐个执行**（`inspector.run_batch`）。

⚠ **执行是同步的**（`run_batch` 阻塞直到跑完），所以轮询间隔要够长 ——
`tick()` 本身很便宜（几次 SQL），但 `run_batch` 可能是分钟级。
⇒ 执行完立刻进下一次等待，不叠加。

⚠ **每个线程持有自己的 `Event`**（不是模块级共享）—— 否则 stop 后立刻 start
会把新线程的 Event 清掉，旧线程随即"复活"再跑一轮（`law_refresh.py` 实测踩过）。

## 为什么失败不阻塞

与 `law_refresh` 同口径：后台线程**必须吞异常存活**（调度线程崩了会让"自动巡检"
静默失效，那比一次巡检失败更糟）。每次异常写 `upd_log`，下一拍重试。
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from src.core.update import inspector
from src.core.update.channels.base import upd_log
from src.core.update.scheduler import POLL_INTERVAL_S, UpdateScheduler

logger = logging.getLogger(__name__)

#: 线程唤醒间隔（秒）。沿用 `scheduler.py` 的 2s —— 它的 tick 很便宜（未到期时
#: 只做几次 SQL 查询、不碰网络），真正的开销在 `run_batch`（执行完才进下一次等待）。
_POLL_INTERVAL_S = POLL_INTERVAL_S

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop: threading.Event | None = None


def _run_batches(batch_ids: list[str]) -> list[dict]:
    """把建出来的批逐个**执行**（现状缺口：`tick()` 只建不跑）。

    返回每个批的执行结果摘要（供日志与测试断言）。
    单个批失败**不影响**其余批（各自 try）。
    """
    out: list[dict] = []
    for bid in batch_ids:
        try:
            res = inspector.run_batch(bid)
            status = (res or {}).get("status")
            upd_log(bid, "scheduler", "INFO", "scheduled_batch_run",
                    status=status)
            out.append({"batch_id": bid, "status": status, "ok": True})
        except Exception as exc:  # noqa: BLE001 — 单批失败不拖累其余批
            upd_log(bid, "scheduler", "ERROR", "scheduled_batch_run_failed",
                    err=f"{type(exc).__name__}: {exc}")
            out.append({"batch_id": bid, "ok": False,
                        "err": f"{type(exc).__name__}: {exc}"})
    return out


def tick_and_run(sched: UpdateScheduler | None = None) -> dict:
    """一拍：建批/恢复 → **执行新批**。返回 `{created, resumed, ran}`。

    抽成公开函数是为了**可测**：测试注入假时钟的 `UpdateScheduler` 子类即可，
    不必真起线程。
    """
    s = sched if sched is not None else UpdateScheduler()
    out = s.tick()
    created = list(out.get("created") or [])
    ran = _run_batches(created) if created else []
    return {"created": created, "resumed": list(out.get("resumed") or []), "ran": ran}


#: 调度器工厂（**测试注入点**）。为什么要有它：生命周期判据（start 幂等 / stop 后
#: `is_running` 为假）不该依赖数据库 —— 而真实 `UpdateScheduler.tick()` 会查库。
#: 全量测试里若 DB 被别处占着，`tick()` 阻塞 ⇒ `stop()` 的 join 超时 ⇒
#: **生命周期判据假红**（2026-10-12 实测踩到）。测试把它换成"不碰库"的替身即可。
_sched_factory: Any = UpdateScheduler


def set_scheduler_factory(factory: Any) -> None:
    """测试用：替换调度器工厂（生产不调）。"""
    global _sched_factory
    _sched_factory = factory


def reset_scheduler_factory() -> None:
    """测试用：还原调度器工厂。"""
    global _sched_factory
    _sched_factory = UpdateScheduler


def _loop(poll_interval: float, stop: threading.Event) -> None:
    """循环体：直到本线程的 stop 被置位。单次异常不得终止循环。

    ⚠ **每拍先查 stop 再干活**：`tick()` 会查库、`run_batch` 可能跑几分钟
    ⇒ 若不等就进 tick，`stop()` 的 join 会**超时**（实测：全量测试里 DB 被别处
    占着时 `join(5s)` 超时 ⇒ `stop` 返回 False ⇒ 生命周期断言假红）。
    """
    sched = _sched_factory()
    while not stop.is_set():
        try:
            out = tick_and_run(sched)
            if out["created"]:
                logger.info("更新巡检：建批 %s，执行 %s",
                            out["created"], [r.get("status") for r in out["ran"]])
            if out["resumed"]:
                logger.info("更新巡检：恢复预算暂停批 %s", out["resumed"])
        except Exception as exc:  # noqa: BLE001 — 后台线程必须吞异常存活
            logger.warning("更新巡检失败（下个周期重试）: %s: %s",
                           type(exc).__name__, exc)
        stop.wait(poll_interval)


def start_update_scheduler(poll_interval: float = _POLL_INTERVAL_S) -> bool:
    """拉起巡检线程；已在跑则不动（幂等）。返回是否**本次新起**了线程。"""
    global _thread, _stop
    with _lock:
        if _thread is not None and _thread.is_alive():
            return False
        stop = threading.Event()
        _stop = stop
        _thread = threading.Thread(target=_loop, args=(poll_interval, stop),
                                   name="ks-update-scheduler", daemon=True)
        _thread.start()
        return True


def stop_update_scheduler(timeout: float = 5.0) -> bool:
    """置位停止并等线程退出。返回**线程是否真的退出了**。

    未在跑 ⇒ 返回 True（幂等，无操作）。

    ⚠ **join 超时不许把引用丢掉**（照 `law_refresh.stop_law_refresh` 的既有更正）：
    第一版若无论如何都 `_thread = None`，会造成 ① `is_running()` 假阴；
    ② 紧接着 `start()` 会**再起一个线程** ⇒ 两个线程并发巡检。
    现在：**只有 join 成功才清引用**；超时则保留（`is_running()` 继续报真、
    `start()` 拒绝重复起线程）。
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
        logger.warning("更新巡检线程 %.1fs 内未退出，保留引用避免并发起新线程", timeout)
        return False
    with _lock:
        if _thread is thread:
            _thread, _stop = None, None
    return True


def is_running() -> bool:
    """线程是否在跑（测试与诊断用）。"""
    with _lock:
        return _thread is not None and _thread.is_alive()
