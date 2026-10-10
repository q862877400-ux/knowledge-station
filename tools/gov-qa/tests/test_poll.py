"""测试：增量轮询（T023–T027 + 本轮增量验证）。

对应 spec 004 的成功判据：
- SC-002 幂等 / SC-003 中断可续 / FR-006 水位退化 / SC-012 故障隔离 / R7 并发锁

## ⚠ 两条测试纪律（都是实测踩坑换来的）

1. **每个测试必须把 `poll.DATA_DIR` 指向临时目录。**
   否则 `poll_one` 会往**真实数据目录**写 `fake-1-fake.jsonl` ——
   第一次写这些测试时就污染了真实数据，手工删掉才恢复。

2. **假 adapter 必须尊重 `GOVQA_PAGE_FROM`。**
   `poll_one` 靠改这个环境变量推进页码（adapter 每次都从第 1 页开始，
   不认「从第 N 页开始」的入参）。假 adapter 不模拟这一点，
   就测不出「翻到已知位置就停」。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import poll                                                        # noqa: E402
from state import WatermarkStore                                   # noqa: E402


class FakeAdapter:
    """可控假 adapter。

    - `records`：固定返回这批（不分页）
    - `pages_data`：按 `GOVQA_PAGE_FROM` 返回对应页（模拟真实 adapter 的分页语义）
    - `boom`：抛异常
    """

    def __init__(self, records=None, *, boom=False, pages_data=None, page_size=1):
        self._records = records or []
        self._boom = boom
        self._pages_data = pages_data
        self._page_size = page_size
        self.last_pages_fetched = 0
        self.call_count = 0
        self.pages_requested: list[int] = []

    def harvest(self, fetch, *, limit=None, **kw):
        self.call_count += 1
        if self._boom:
            raise RuntimeError("模拟网络失败")

        if self._pages_data is None:
            # 非分页：每次都返回同一批
            self.last_pages_fetched = 1
            return list(self._records)

        # 分页：按 GOVQA_PAGE_FROM 定位（模拟真实 adapter 语义）
        page_from = max(1, int(os.environ.get("GOVQA_PAGE_FROM", "1")))
        self.pages_requested.append(page_from)
        idx = page_from - 1
        self.last_pages_fetched = self._page_size
        if idx >= len(self._pages_data):
            return []
        return list(self._pages_data[idx])


def _ch(key="fake-1", wtype="idset"):
    from channel import Channel
    return Channel(key, name=key, level="province", watermark_type=wtype)


def _rec(i, src="fake-1"):
    return {"source": src, "id": f"r{i}", "question": f"q{i}",
            "answer": f"a{i}", "extra": {}}


class _Isolated:
    """把 `poll.DATA_DIR` 指到临时目录的上下文管理器。

    **每个测试都必须用** —— 见模块文档第 1 条。
    """

    def __init__(self, root: Path):
        self.root = root
        self.old = None

    def __enter__(self):
        (self.root / "data").mkdir(parents=True, exist_ok=True)
        self.old = poll.DATA_DIR
        poll.DATA_DIR = self.root / "data"
        return self

    def __exit__(self, *a):
        poll.DATA_DIR = self.old
        return False


# ---------------------------------------------------------------- SC-002 幂等

def test_idempotent_second_run_adds_zero():
    """**SC-002**：连续两次轮询，第二次必须新增 0 条。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            recs = [_rec(1), _rec(2), _rec(3)]
            ch = _ch()
            # 第一次：注意 adapter 每次都返回同一批 ⇒ 第一批全新增，第二批全旧 ⇒ 停
            r1 = poll.poll_one(FakeAdapter(recs), ch, store, dry_run=False,
                               force_full=False, site_name="fake")
            assert r1["added"] == 3, r1
            r2 = poll.poll_one(FakeAdapter(recs), ch, store, dry_run=False,
                               force_full=False, site_name="fake")
            assert r2["added"] == 0, f"第二次应新增 0 条，实际 {r2['added']}"


def test_idempotent_no_duplicate_ids_on_disk():
    """SC-002 落盘侧：连续两次后文件里不得有重复 id。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            adapter = FakeAdapter([_rec(1), _rec(2)])
            ch = _ch()
            poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                          site_name="fake")
            poll.poll_one(adapter, ch, store, dry_run=False, force_full=False,
                          site_name="fake")
            files = list((d / "data").glob("*.jsonl"))
            assert len(files) == 1, f"应只有一个数据文件，实际 {files}"
            lines = [json.loads(x) for x in
                     files[0].read_text(encoding="utf-8").splitlines() if x.strip()]
            ids = [x["id"] for x in lines]
            assert len(ids) == len(set(ids)), f"有重复 id：{ids}"
            assert len(ids) == 2, f"应有 2 条，实际 {len(ids)}"


# ---------------------------------------------------------------- 增量真的会停

def test_incremental_stops_at_known_page():
    """**核心验证**：翻到「本页全部已见过」就停，不把后面的页也翻完。

    模拟按时间倒序的分页列表（`GOVQA_PAGE_FROM` 语义）：
      第1页 = [新, 新, 旧]   ← 有新 ⇒ 继续
      第2页 = [旧, 旧, 旧]   ← 全旧 ⇒ **停**（不翻第3页）
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            ch = _ch()
            # 先落盘 3 条「旧」记录
            seed = FakeAdapter([_rec(10), _rec(11), _rec(12)])
            poll.poll_one(seed, ch, store, dry_run=False, force_full=True,
                          site_name="fake")

            pages = [
                [_rec(1), _rec(2), _rec(12)],   # 页1：有新
                [_rec(10), _rec(11), _rec(12)],  # 页2：全旧 ⇒ 停
                [_rec(99), _rec(98)],            # 页3：不该被翻到
            ]
            adapter = FakeAdapter(pages_data=pages)
            r = poll.poll_one(adapter, ch, store, dry_run=False,
                              force_full=False, site_name="fake")
            assert r["status"] == "ok", r
            assert r["added"] == 2, f"应只新增 r1/r2，实际 {r['added']}"
            assert r["batches"] == 2, f"应在第2批就停，实际 {r['batches']} 批"
            assert adapter.pages_requested == [1, 2], \
                f"应只请求第1、2页，实际 {adapter.pages_requested}"


def test_incremental_restores_page_env():
    """`GOVQA_PAGE_FROM` 用完必须恢复 —— 不能污染调用方环境。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            os.environ.pop("GOVQA_PAGE_FROM", None)
            poll.poll_one(FakeAdapter([_rec(1)]), _ch(), store, dry_run=False,
                          force_full=False, site_name="fake")
            assert "GOVQA_PAGE_FROM" not in os.environ, "环境变量未恢复"


# ---------------------------------------------------------------- SC-012 故障隔离

def test_failure_isolated():
    """**SC-012**：一个通道失败，不影响其他通道，且不抛异常。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            bad = FakeAdapter(boom=True)
            r = poll.poll_one(bad, _ch("bad"), store, dry_run=False,
                              force_full=False, site_name="bad")
            assert r["status"] == "failed"
            assert r["error"], "失败必须带原因"
            good = FakeAdapter([_rec(1)])
            r2 = poll.poll_one(good, _ch(), store, dry_run=False,
                               force_full=False, site_name="fake")
            assert r2["status"] == "ok"


def test_failure_does_not_advance_watermark():
    """**FR-003**：失败路径绝不能前移水位。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            ch = _ch()
            poll.poll_one(FakeAdapter([_rec(1)]), ch, store, dry_run=False,
                          force_full=False, site_name="fake")
            before = store.get(ch.key).value
            poll.poll_one(FakeAdapter(boom=True), ch, store, dry_run=False,
                          force_full=False, site_name="fake")
            assert store.get(ch.key).value == before, "失败后水位不得改变"
            assert store.get(ch.key).consecutive_failures == 1


# ---------------------------------------------------------------- FR-006 水位退化

def test_broken_watermark_degrades_not_crash():
    """**FR-006**：水位损坏时不崩溃，且标记退化。"""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        p = d / "watermarks.json"
        p.write_text("{{{ 坏的", encoding="utf-8")
        store = WatermarkStore(p)
        assert store.broken
        with _Isolated(d):
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


# ---------------------------------------------------------------- T303 水位真读

def test_page_watermark_is_actually_read():
    """**T303**：`page` 型水位必须被**读** —— 不是只写不读的摆设。

    独立复核实测：手改水位为 999999，`pages requested` 仍是 `[1]`。
    修法是「起点从水位 +1 页算」。谁改回恒为 1，这条必红。
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            ch = _ch("fake-1", wtype="page")
            store.ensure(ch.key, "page")
            store.mark_success(ch.key, new_value=7, batch_count=1)

            adapter = FakeAdapter(pages_data=[[_rec(1)], [_rec(2)], []])
            r = poll.poll_one(adapter, ch, store, dry_run=False,
                              force_full=False, site_name="fake")
            # 水位是 7 ⇒ 应从第 8 页起翻
            assert adapter.pages_requested[0] == 8, \
                f"应从水位 7 的下一页(8)起，实际 {adapter.pages_requested}"


def test_idset_watermark_still_starts_at_page_one():
    """**反向用例**：`idset` 型不靠页码（靠 `seen` 去重）⇒ 仍从第 1 页起。

    修 T303 时不能把 `idset` 型也改坏 —— 它没有页号语义。
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            ch = _ch("fake-1", wtype="idset")
            store.ensure(ch.key, "idset")
            store.mark_success(ch.key, new_value=["old1", "old2"], batch_count=2)
            adapter = FakeAdapter(pages_data=[[_rec(1)], []])
            poll.poll_one(adapter, ch, store, dry_run=False,
                          force_full=False, site_name="fake")
            assert adapter.pages_requested[0] == 1, \
                f"idset 型应从第 1 页起，实际 {adapter.pages_requested}"


def test_next_value_page_records_real_page_not_increment():
    """**T303**：`page` 型水位记的是**本轮实际翻到的页号**，不是"每批 +1"。"""
    from state import Watermark
    wm = Watermark("k", "page", value=3, last_success_at=None, updated_at=None)
    got = poll._next_value(wm, [_rec(1)], need_full=False, page_reached=42)
    assert got == 42, f"应记真实页号 42，实际 {got}"

def test_existing_ids_reads_sub_source_records():
    """**子源**记录也必须被 `existing_ids` 读到（2026-10-10 修的真 bug）。

    ## 为什么必须单独钉这一条

    原判据是 `if str(rec.get("source")) == channel_key`。而**真实语料里 `source`
    常常是子源**（`cq-igi-156`），通道 key 是 `cq-igi` ⇒ **读不到**。

    实测后果：33 个通道（132,569 条）里只读到 7,807 条，**漏 124,762 条（94.1%）**；
    受控复现：预置 3 条子源记录后重跑 `poll_one` ⇒ `added=3`（应为 0）
    ⇒ 落盘 3 → 6 行，**重复 3 条**。SC-002 在这些通道上是坏的。

    ## 为什么原来的测试抓不到

    本文件其他用例的 `_rec(i)` 默认 `src="fake-1"`，而 `_ch()` 的 key 也是
    `fake-1` ⇒ **恰好命中旧判据**。只有把 `source` 写成子源才暴露。
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        with _Isolated(d):
            # 落盘一条"子源"记录：source='fake-1-99'，通道 key='fake-1'
            p = poll.data_path_for("fake-1", "假站点")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(_rec(1, src="fake-1-99"), ensure_ascii=False) + "\n",
                         encoding="utf-8")
            got = poll.existing_ids("fake-1")
            assert got == {"r1"}, (
                f"子源记录应被读到，实际读到 {got} —— "
                f"退回按 source == channel_key 过滤会漏掉全部子源")


def test_poll_one_is_idempotent_for_sub_source_records():
    """**SC-002 的端到端判据（子源形态）**：第二次必须 0 新增。

    这条与本文件的 `test_idempotent_second_run_adds_zero` **不同**：
    那条用的 `source == 通道 key`，这条用**子源**（真实语料的形态）。
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        store = WatermarkStore(d / "watermarks.json")
        with _Isolated(d):
            recs = [_rec(1, src="fake-1-99"), _rec(2, src="fake-1-99")]
            ch = _ch()
            r1 = poll.poll_one(FakeAdapter(recs), ch, store, dry_run=False,
                               force_full=True, site_name="假站点")
            assert r1["added"] == 2, f"第一次应新增 2，实际 {r1['added']}"
            r2 = poll.poll_one(FakeAdapter(recs), ch, store, dry_run=False,
                               force_full=False, site_name="假站点")
            assert r2["added"] == 0, (
                f"**子源**记录第二次应新增 0，实际 {r2['added']} —— "
                f"这是 SC-002 在真实语料形态上的判据")
