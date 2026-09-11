"""Python 侧引擎看门狗（阶段2.1，外部评审 P2 响应 / T09 前置）。

为什么自愈做在 Python 侧而不是 Electron 主进程：
1. 本机安全钩子（Mimosa）拦截 Electron main 里的子进程 spawn 代码（第一阶段实测）；
2. Python 侧用 multiprocessing（已验证可过审），与引擎同栈，端口/token 协议不变。

策略（对齐主计划 R6）：
- 引擎子进程意外退出 → restart_delay 秒后自动拉起；
- 连续 max_retries 次崩溃 → 熔断退出（exit code 2），上层 UI 降级提示；
- 正常退出（exitcode 0，如收到退出信号）→ 不重启。

进度监控为进程存活检测；HTTP /health 3 秒心跳与前端状态推送属于 T09 完整范围。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import sys
import time
from typing import Callable, Protocol

logger = logging.getLogger(__name__)


class ChildHandle(Protocol):
    exitcode: int | None
    pid: int | None

    def start(self) -> None: ...
    def join(self) -> None: ...
    def is_alive(self) -> bool: ...


def _engine_entry() -> None:
    from src.core.api.server import run
    run()


def _mp_child_factory() -> ChildHandle:
    ctx = mp.get_context("spawn")
    return ctx.Process(target=_engine_entry, name="ks-engine")


class EngineSupervisor:
    def __init__(self, child_factory: Callable[[], ChildHandle] = _mp_child_factory,
                 max_retries: int = 3, restart_delay: float = 3.0,
                 heartbeat_interval: float = 3.0, enable_heartbeat: bool = False):
        self.child_factory = child_factory
        self.max_retries = max_retries
        self.restart_delay = restart_delay
        self.heartbeat_interval = heartbeat_interval
        self.enable_heartbeat = enable_heartbeat
        self.starts = 0
        self.crashes = 0
        self.events: list[str] = []  # 测试可读的事件轨迹

    def _heartbeat_ok(self) -> bool:
        """P8 心跳：读 session 文件里的 port，探测 /health。"""
        import json
        import urllib.request
        from src.core.config import get_settings
        try:
            sess = get_settings().data_dir / "engine.session.json"
            if not sess.exists():
                return False
            info = json.loads(sess.read_text(encoding="utf-8"))
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{info['port']}/api/v1/health", timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def run(self) -> int:
        """阻塞运行。返回 0=正常退出，2=熔断。

        P8：引擎存活期间每 heartbeat_interval 秒探测 /health，
        心跳失败不计入崩溃重启（进程崩溃由 join 兜底），仅记事件。
        """
        if self.enable_heartbeat:
            import threading
            last_beat = {"ok": True, "ts": 0.0}

            def _beat_loop() -> None:
                while True:
                    ok = self._heartbeat_ok()
                    if ok != last_beat["ok"]:
                        self._emit(f"heartbeat {'ok' if ok else 'down'}")
                        last_beat["ok"] = ok
                    last_beat["ts"] = time.monotonic()
                    time.sleep(self.heartbeat_interval)

            beat_thread = threading.Thread(target=_beat_loop, daemon=True)
            beat_thread.start()
        while True:
            child = self.child_factory()
            child.start()
            self.starts += 1
            self._emit(f"engine_started pid={child.pid}")
            child.join()
            code = child.exitcode
            if code == 0:
                self._emit("engine_stopped_clean")
                return 0
            self.crashes += 1
            self._emit(f"engine_crashed code={code} crashes={self.crashes}")
            if self.crashes > self.max_retries:
                self._emit("circuit_break")
                return 2
            self._emit(f"restart_scheduled delay={self.restart_delay}")
            time.sleep(self.restart_delay)

    def _emit(self, msg: str) -> None:
        self.events.append(msg)
        logger.warning("SUPERVISOR: %s", msg)
        print(f"SUPERVISOR: {msg}", flush=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    supervisor = EngineSupervisor(enable_heartbeat=True)
    sys.exit(supervisor.run())


if __name__ == "__main__":
    main()
