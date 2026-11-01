"""公告扫描**并行化**的判据（2026-11-02）。

## 为什么要这组测试

原来 `run_announce_scan` 是一个 `for` 循环**串行**跑全部源（实测 110 源 6.8 分钟）。
并行化改了三件事，每一件都必须有判据钉住，否则"改快了但改坏了"：

| 改了什么 | 判据 |
|---|---|
| 不同主机同时抓 | `test_different_hosts_overlap` |
| **同一主机永远串行**（多渠道不许并发打自己） | `test_same_host_never_overlaps` |
| `first_scan_done` 收归主线程（原读改写会覆盖） | `test_first_scan_marks_not_lost` |
| `per_source` 顺序仍是源顺序（并行完成会乱） | `test_per_source_keeps_source_order` |
| 软上限仍生效（超时源标 `skipped_timeout`） | `test_soft_cap_still_marks_skipped` |

## 事实口径

- 并发让**不同主机**同时请求；同一主机用 per-host 锁串行 + `SOURCE_GAP_S` 间隔。
- 测试注入 `transport` 时**跳过**礼貌间隔（否则用例要等 110 秒），这与原行为一致。
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from src.core.update import announce


class _ConcurrencyTransport:
    """记录「同时在飞的请求数」，并按主机统计最大重叠。

    注入 `delay` 让每个请求"占用"一段时间，才能观察到重叠；
    真实网络里重叠自然发生，但测试里必须人为制造窗口。
    """

    def __init__(self, pages: dict[str, tuple[int, str]], delay: float = 0.25):
        self.pages = pages
        self.delay = delay
        self.lock = threading.Lock()
        self.inflight = 0
        self.max_inflight = 0
        self.host_inflight: dict[str, int] = {}
        self.host_max: dict[str, int] = {}
        self.calls: list[str] = []

    def fetch(self, url: str, **kw):  # noqa: ANN003 — 测试桩，签名跟 transport 一致
        host = url.split("/")[2] if "//" in url else url
        with self.lock:
            self.calls.append(url)
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
            self.host_inflight[host] = self.host_inflight.get(host, 0) + 1
            self.host_max[host] = max(
                self.host_max.get(host, 0), self.host_inflight[host]
            )
        try:
            time.sleep(self.delay)
            return self.pages.get(url, (404, "not found"))
        finally:
            with self.lock:
                self.inflight -= 1
                self.host_inflight[host] -= 1


def _page(*links: tuple[str, str]) -> str:
    """最小列表页：`<a href>text</a>` 序列。"""
    return (
        "<html><body>"
        + "".join(f'<a href="{href}">{text}</a>' for href, text in links)
        + "</body></html>"
    )


def _allow_public(monkeypatch):
    """域名解析一律 mock 成公网地址（`add_source` 有 SSRF 守卫）。"""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, *a, **kw: [(socket.AF_INET, None, None, "", ("93.184.216.34", 0))],
    )


def _wait_done(timeout_s: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        state = announce.get_scan_state()
        if state.get("status") in ("done", "failed"):
            return state
        time.sleep(0.05)
    raise AssertionError(f"扫描未在 {timeout_s}s 内到终态: {announce.get_scan_state()}")


def _reset_sources() -> None:
    """清空公告源。

    ⚠ 必须显式清（2026-11-02 实测）：`db` 夹具在多个用例之间**不隔离 app_config**
    —— 前一个用例 `add_source` 的源会留在库里，后一个用例 `sources_done` 就变成
    "前面那些 + 我的"。第一版没清，5 条里 3 条红在"数量对不上"，不是并行的问题。
    """
    for s in list(announce.get_sources()):
        try:
            announce.remove_source(s["id"])
        except Exception:  # noqa: BLE001 — 清不干净也不该挡住用例
            pass


# ── 1. 不同主机确实并发 ──────────────────────────────────────────────
def test_different_hosts_overlap(db, monkeypatch):
    _reset_sources()
    """6 个不同主机 × 每个请求 0.25s：串行要 ≥1.5s；并行必须出现重叠。

    判据两条（缺一不可）：
      ① 观察到 `max_inflight > 1`（真并发了）；
      ② 总耗时不随源数线性增长（并行才有意义）。
    """
    _allow_public(monkeypatch)
    pages = {}
    for i in range(6):
        url = f"https://h{i}.example.com/ann/"
        pages[url] = (
            200,
            _page(
                (f"/a{i}", f"第{i}号公告事项标题 2026-09-0{i + 1}"),
            ),
        )
        announce.add_source(f"源{i}", url)
    tr = _ConcurrencyTransport(pages, delay=0.25)

    t0 = time.monotonic()
    announce.request_scan(force=True, trigger="manual", transport=tr)
    state = _wait_done()
    elapsed = time.monotonic() - t0

    assert state["status"] == "done"
    assert state["sources_done"] == 6
    # 判据只看「不同主机真的同时在飞」——**不看墙钟**。
    # 第一版写的是 `elapsed < 1.5s`（6×0.25 的串行下界），实测**抽风**：
    # 同一份代码一次红一次绿，机器负载一变就误判。判据必须与本机快慢无关。
    assert tr.max_inflight >= 2, (
        f"没有观察到跨主机并发（max_inflight={tr.max_inflight}）"
    )
    # 并发上限不超过配置（默认 8），且远小于串行的 6 个串行下界
    assert tr.max_inflight <= 8, f"并发超过上限（max_inflight={tr.max_inflight}）"
    print(f"  并发峰值 {tr.max_inflight} / 6 源，总耗时 {elapsed:.2f}s")


# ── 2. 同一主机永远串行 ──────────────────────────────────────────────
def test_same_host_never_overlaps(db, monkeypatch):
    _reset_sources()
    """同一主机挂 4 个源：该主机的并发**必须恒为 1**。

    这是并行化最容易踩的坑 —— 110 个公告源里 23 个主机挂了 2~5 个渠道，
    对同一站点并发请求等于自己把自己打成 WAF 目标。
    """
    _allow_public(monkeypatch)
    pages = {}
    for i in range(4):
        url = f"https://same.example.com/ann{i}/"
        pages[url] = (
            200,
            _page(
                (f"/a{i}", f"同主机第{i}号公告事项 2026-09-0{i + 1}"),
            ),
        )
        announce.add_source(f"同主机源{i}", url)
    tr = _ConcurrencyTransport(pages, delay=0.15)

    announce.request_scan(force=True, trigger="manual", transport=tr)
    state = _wait_done()

    assert state["status"] == "done"
    assert state["sources_done"] == 4
    assert tr.host_max.get("same.example.com") == 1, f"同一主机出现并发：{tr.host_max}"


# ── 3. first_scan_done 不丢（并行下读改写会互相覆盖）────────────────
def test_first_scan_marks_not_lost(db, monkeypatch):
    _reset_sources()
    """两个源同时首扫：扫描结束后**两个**都必须标上 `first_scan_done`。

    原来这步在工作线程里做 `get_sources() → 改 → _write_json_key()`，
    两个线程同时读写会丢一个标记 ⇒ 那个源下一轮又把已见条目当基线重算。
    """
    _allow_public(monkeypatch)
    pages = {}
    for i in range(2):
        url = f"https://f{i}.example.com/ann/"
        pages[url] = (
            200,
            _page(
                (f"/a{i}", f"首扫第{i}号公告标题 2026-09-0{i + 1}"),
            ),
        )
        announce.add_source(f"首扫源{i}", url)
    tr = _ConcurrencyTransport(pages, delay=0.1)

    announce.request_scan(force=True, trigger="manual", transport=tr)
    state = _wait_done()
    assert state["status"] == "done"

    done = {s["name"]: s.get("first_scan_done") for s in announce.get_sources()}
    assert done["首扫源0"] is True, done
    assert done["首扫源1"] is True, done
    # 首扫的条目算基线，不算"新"（两条源各 1 条）
    assert state["new_count"] == 0
    assert state["baseline_count"] == 2


# ── 4. per_source 顺序 == 源顺序 ─────────────────────────────────────
def test_per_source_keeps_source_order(db, monkeypatch):
    _reset_sources()
    """`per_source` 必须按源**注册顺序**排列，不能被完成先后打乱。

    为什么重要：界面渠道台账按这个顺序展示；测试也按它读。
    并行实现里若直接 append 完成结果，顺序会随网络快慢乱跳。
    """
    _allow_public(monkeypatch)
    pages = {}
    names = [f"序{i}" for i in range(5)]
    for i, name in enumerate(names):
        url = f"https://o{i}.example.com/ann/"
        pages[url] = (
            200,
            _page(
                (f"/a{i}", f"顺序第{i}号公告标题 2026-09-0{i + 1}"),
            ),
        )
        announce.add_source(name, url)
    # 让后注册的源**更快**返回，逼出"完成顺序 ≠ 注册顺序"
    tr = _ConcurrencyTransport(pages, delay=0.02)

    announce.request_scan(force=True, trigger="manual", transport=tr)
    state = _wait_done()
    assert state["status"] == "done"
    got = [p.get("name") for p in state["per_source"]]
    assert got == names, f"顺序被打乱：{got} != {names}"


# ── 5. 软上限仍然生效 ────────────────────────────────────────────────
def test_soft_cap_still_marks_skipped(db, monkeypatch):
    _reset_sources()
    """软上限到点后，剩下源必须如实标 `skipped_timeout`（不许静默跳过）。

    并行化后这条更容易出错：所有任务一次性提交，若不在工作单元里复查上限，
    超时的源会被照样抓完，`skipped_timeout` 这个诚实标记就消失了。
    """
    _allow_public(monkeypatch)
    pages = {}
    for i in range(3):
        url = f"https://s{i}.example.com/ann/"
        pages[url] = (
            200,
            _page(
                (f"/a{i}", f"时限第{i}号公告标题 2026-09-0{i + 1}"),
            ),
        )
        announce.add_source(f"时限源{i}", url)
    # 上限设成**负数** ⇒ 工作单元一进来就必然已超时。
    # 第一版写 0.001 秒，实测不成立：工作线程可能在 1 毫秒内就开始跑，
    # 于是"还没超时"⇒ 3 个源照样抓完，reason 全是 None。判据要确定性，不能赌时序。
    monkeypatch.setattr(announce, "_scan_soft_cap_s", lambda: -1.0)
    tr = _ConcurrencyTransport(pages, delay=0.05)

    announce.request_scan(force=True, trigger="manual", transport=tr)
    state = _wait_done()
    assert state["status"] == "done"
    reasons = [p.get("reason") for p in state["per_source"]]
    assert reasons.count("skipped_timeout") == 3, reasons
    # 一条都不该真抓
    assert tr.calls == [], tr.calls


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
