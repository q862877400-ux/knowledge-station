"""阶段2.1 supervisor 测试：用假子进程模拟崩溃/恢复/熔断，不启动真引擎。"""
import pytest

from src.core.supervisor import EngineSupervisor


class FakeChild:
    """按脚本依次决定退出码的假引擎进程。"""

    def __init__(self, script: list[int], counter: list[int]):
        self._script = script
        self._counter = counter
        self.pid = 40000 + counter[0]
        self.exitcode: int | None = None

    def start(self) -> None:
        pass

    def join(self) -> None:
        idx = min(self._counter[0], len(self._script) - 1)
        self.exitcode = self._script[idx]
        self._counter[0] += 1

    def is_alive(self) -> bool:
        return False


def test_supervisor_restarts_then_clean_exit():
    script = [1, 1, 0]  # 崩 2 次后正常退出
    counter = [0]
    sup = EngineSupervisor(child_factory=lambda: FakeChild(script, counter),
                           max_retries=3, restart_delay=0)
    rc = sup.run()
    assert rc == 0
    assert sup.starts == 3 and sup.crashes == 2
    assert "engine_crashed code=1" in sup.events[1]
    assert "engine_stopped_clean" in sup.events[-1]


def test_supervisor_circuit_break():
    script = [137] * 10  # 一直崩
    counter = [0]
    sup = EngineSupervisor(child_factory=lambda: FakeChild(script, counter),
                           max_retries=3, restart_delay=0)
    rc = sup.run()
    assert rc == 2, "连续超过 max_retries 次崩溃应熔断"
    assert sup.crashes == 4  # 3 次重试机会用尽
    assert "circuit_break" in sup.events[-1]


def test_supervisor_no_restart_on_clean():
    script = [0]
    counter = [0]
    sup = EngineSupervisor(child_factory=lambda: FakeChild(script, counter),
                           max_retries=3, restart_delay=0)
    rc = sup.run()
    assert rc == 0 and sup.starts == 1 and sup.crashes == 0
