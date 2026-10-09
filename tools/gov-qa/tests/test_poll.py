"""测试：增量轮询（T023–T027）。

对应 spec 004 的四条成功判据：
- SC-002 幂等
- SC-003 中断可续
- FR-006 水位损坏安全退化
- SC-012 故障隔离
- R7 并发锁

**这些测试全部用假 adapter 跑** —— 不打网络、不动真实数据。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import poll                                                        # noqa: E402
from state import WatermarkStore                                   # noqa: E402


class FakeAdapter:
    """可控的假 adapter：能模拟「有新增 / 无新增 / 抛异常」。"""

    def __init__(self, records, *, boom=False, pages=1):
        self._records = records
        self._boom = boom
        self.last_pages_fetched = pages

    def harvest(self, fetch, *, limit=None, **kw):
        if self._boom:
            raise RuntimeError("模拟网络失败")
        return list(self._records)


def _ch(key="fake-1", wtype="idset"):
    from channel import Channel
    return Channel(key, name=key, level="province", watermark_type=wtype)


def _rec(i):
    return {"source": "fake-1", "id": f"r{i}", "question": f"q{i}",
            "answer": f"a{i}", "extra": {}}


# ---------------------------------------------------------------- SC-002 幂等

def test_idempotent_second_run_adds_zero():
    """**SC-002**：连续两次轮询，第二次必须新增 0 条。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        data = d / "data"
        data.mkdir()
        store = WatermarkStore(d / "watermarks.json")

        recs = [_rec(1), _rec(2), _rec(3)]
        adapter = FakeAdapter(recs)
        ch = _ch()

        # 第一次
        r1 = poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                           site_name="fake")
        assert r1["added"] == 3, r1
        # 第二次（同样数据）
        r2 = poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                           site_name="fake")
        assert r2["added"] == 0, f"第二次应新增 0 条，实际 {r2['added']}"


def test_idempotent_with_real_files():
    """SC-002 的落盘侧：连续两次后文件里不得有重复 id。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "data").mkdir()
        store = WatermarkStore(d / "watermarks.json")

        # 临时把 poll 的 DATA_DIR 指到临时目录
        old = poll.DATA_DIR
        poll.DATA_DIR = d / "data"
        try:
            adapter = FakeAdapter([_rec(1), _rec(2)])
            ch = _ch()
            poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                          site_name="fake")
            poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                          site_name="fake")
            files = list((d / "data").glob("*.jsonl"))
            assert len(files) == 1
            lines = [json.loads(x) for x in files[0].read_text(encoding="utf-8").splitlines() if x.strip()]
            ids = [x["id"] for x in lines]
            assert len(ids) == len(set(ids)), f"有重复 id：{ids}"
            assert len(ids) == 2, f"应有 2 条，实际 {len(ids)}"
        finally:
            poll.DATA_DIR = old


# ---------------------------------------------------------------- SC-012 故障隔离

def test_failure_isolated():
    """**SC-012**：一个通道失败，不影响其他通道，且不抛异常。"""
    with tempfile.TemporaryDirectory() as d:
        store = WatermarkStore(Path(d) / "watermarks.json")
        bad = FakeAdapter([], boom=True)
        r = poll.poll_one(bad, _ch("bad"), store, dry_run=False,
                          force_full=False, site_name="bad")
        assert r["status"] == "failed"
        assert r["error"], "失败必须带原因"
        # 关键：不抛异常
        good = FakeAdapter([_rec(1)])
        r2 = poll.poll_one(good, _ch("fake-1"), store, dry_run=False,
                           force_full=False, site_name="fake")
        assert r2["status"] == "ok"


def test_failure_does_not_advance_watermark():
    """失败路径绝不能前移水位（FR-003）。"""
    with tempfile.TemporaryDirectory() as d:
        store = WatermarkStore(Path(d) / "watermarks.json")
        ch = _ch()
        # 先成功一次建立水位
        poll.poll_one(FakeAdapter([_rec(1)]), ch, store, dry_run=False,
                      force_full=False, site_name="fake")
        before = store.get(ch.key).value
        # 再失败
        poll.poll_one(FakeAdapter([], boom=True), ch, store, dry_run=False,
                      force_full=False, site_name="fake")
        assert store.get(ch.key).value == before, "失败后水位不得改变"
        assert store.get(ch.key).consecutive_failures == 1


# ---------------------------------------------------------------- FR-006 水位退化

def test_broken_watermark_degrades_not_crash():
    """**FR-006**：水位损坏时不崩溃，且标记退化。"""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "watermarks.json"
        p.write_text("{{{ 坏的", encoding="utf-8")
        store = WatermarkStore(p)
        assert store.broken
        r = poll.poll_one(FakeAdapter([_rec(1)]), _ch(), store, dry_run=True,
                          force_full=False, site_name="fake")
        assert r["status"] == "ok", r
        assert r.get("degraded"), "应标记「已退化」"


# ---------------------------------------------------------------- R7 并发锁

def test_lock_blocks_second_runner():
    """**R7**：抢不到锁时抛 LockBusy（调用方映射成退出码 3）。"""
    from common import LockBusy, file_lock
    with tempfile.TemporaryDirectory() as d:
        lp = Path(d) / ".lock"
        with file_lock(lp, timeout=0.0):
            try:
                with file_lock(lp, timeout=0.0):
                    pass
            except LockBusy:
                return
            raise AssertionError("第二次抢锁应抛 LockBusy")
    raise AssertionError("未进入锁上下文")


def test_lock_released_after_use():
    from common import file_lock
    with tempfile.TemporaryDirectory() as d:
        lp = Path(d) / ".lock"
        with file_lock(lp, timeout=0.0):
            assert lp.exists()
        assert not lp.exists(), "锁应在退出后释放"


# ---------------------------------------------------------------- T016 边采边落盘

def test_atomic_append_writes_immediately():
    """**T016/R3**：每条写入立即落盘（不是「跑完才写」）。"""
    from common import atomic_append_jsonl
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.jsonl"
        atomic_append_jsonl(p, {"id": "a"})
        assert p.exists() and p.read_text(encoding="utf-8").strip(), "写入后应立刻可读"
        atomic_append_jsonl(p, {"id": "b"})
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == "a"


# ---------------------------------------------------------------- T004 纯 ASCII

def test_ascii_kv_is_pure_ascii():
    """**T004/R5**：机器可读输出必须纯 ASCII（4 层 bug 的教训）。"""
    import io
    from common import ascii_kv
    buf = io.StringIO()
    ascii_kv({"total": 123, "note": "中文测试", "flag": True}, stream=buf)
    out = buf.getvalue()
    out.encode("ascii")            # 非 ASCII 会在这里抛异常
    assert "TOTAL=123" in out
    assert "中文" not in out, "中文必须被替换掉"
