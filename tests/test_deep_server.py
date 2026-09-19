"""deep_server 任务协议测试（假 daemon 线程，不启动真 GPU 进程）。

覆盖：提交→daemon 处理→done 返回 out_dir；error → None；
超时 → None 且任务文件清理；KS_DEEP_SERVER=0 不产生任务文件。
真 daemon（server_main）走战役集成验证，不在单测内加载 mineru。
"""
from __future__ import annotations

import json
import threading
import time

import pytest

from src.core.ingestion import deep_server as ds


@pytest.fixture(autouse=True)
def _job_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KS_DEEP_JOBS_DIR", str(tmp_path / "jobs"))
    monkeypatch.delenv("KS_DEEP_SERVER", raising=False)
    monkeypatch.delenv("KS_DEEP_BATCH_MIN", raising=False)
    monkeypatch.delenv("KS_DEEP_BATCH_WAIT", raising=False)


def _fake_daemon(stop: threading.Event, fail: bool = False) -> threading.Thread:
    """监视任务目录，攒批窗口后直接写 done/error（不碰 mineru）。

    ⚠ **目录必须在启动时捕获一次**（§10.93，修一条既存的时序假红）：
    `ds._job_dir()` 每次调用都**现读**环境变量 `KS_DEEP_JOBS_DIR`，而本文件的测试靠
    `monkeypatch.setenv` 给每个用例一个独立目录。原先这个线程在**循环里**每次调
    `ds._job_dir()` ⇒ 上一用例 `stop.set()` 之后、线程真正退出之前，monkeypatch 可能已经把
    环境变量切给了**下一个用例**，于是这个"残留 daemon"会去动**别人的**任务目录
    （`fail=True` 那个更狠：它会给下一个用例的任务写 `.error.json` ⇒ 那个用例的
    `deep_server_wait` 返回 None）。窗口只有几十微秒，所以表现为"全量跑里偶发红一次"。
    ⇒ 现在启动时捕获自己的目录；并且调用方在 `stop.set()` 之后**join 一下**，把窗口关死。
    """
    job_dir = ds._job_dir()          # ⚠ 只读一次：本线程只认**自己这个用例**的目录

    def run():
        while not stop.is_set():
            jobs = sorted(job_dir.glob("*.job.json"))
            if len(jobs) >= 2 or (jobs and time.time() - jobs[0].stat().st_mtime > 0.2):
                for j in jobs:
                    # ⚠ **真竞争，必须吞掉**（复核 v3，2026-09-20 定位）：客户端路径也会删任务文件
                    #   （`deep_server_wait` 成功后 `_cleanup` 先删、超时路径也删）。daemon 与它**同时**
                    #   动同一个文件 ⇒ ① `j.read_text()` 时文件已被删 ⇒ `FileNotFoundError`；
                    #   ② `j.unlink()` 时文件已被删 / 仍被别人持有 ⇒ `PermissionError`（Windows）。
                    #   原先没有 try ⇒ 线程**当场崩掉**：`fail=True` 的用例里它可能还没写 `.error.json`
                    #   就死了 ⇒ `deep_server_wait` 返回 None…而对**成功**用例则留下未清理的任务文件
                    #   ⇒ 下一个用例看到别人的残留。这一条比"自旋饿死 daemon"更可能是那次偶发的来源。
                    try:
                        spec = json.loads(j.read_text(encoding="utf-8"))
                        jid = spec["job_id"]
                        if fail:
                            ds._mark_error(job_dir, jid, "boom")
                        else:
                            (job_dir / f"{jid}.done.json").write_text(
                                json.dumps({"output_dir": spec["out_dir"]}),
                                encoding="utf-8")
                        j.unlink()
                    except (FileNotFoundError, PermissionError, json.JSONDecodeError):
                        continue        # 对手先动手了/文件半写：这一轮跳过，下一轮再看
            stop.wait(0.05)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def _bypass_alive(monkeypatch):
    monkeypatch.setattr(ds, "_alive_count", lambda _: 99)
    monkeypatch.setattr(ds, "_start_server", lambda: None)
    monkeypatch.setattr(ds, "_wait_first_heartbeat", lambda *_: None)


def test_提交_攒批_返回_output_dir(tmp_path, monkeypatch):
    _bypass_alive(monkeypatch)
    stop = threading.Event()
    t = _fake_daemon(stop)
    r = ds.deep_server_submit_and_wait(
        tmp_path / "a.pdf", tmp_path / "out1", timeout=10.0)
    stop.set()
    t.join(2.0)                      # §10.93：关死"残留 daemon 动下一个用例目录"的窗口
    assert r == {"output_dir": str(tmp_path / "out1")}
    assert not list(ds._job_dir().glob("*.json")) or all(
        p.name == "server.json" for p in ds._job_dir().glob("*.json"))


def test_任务失败_返回_None_回退信号(tmp_path, monkeypatch):
    _bypass_alive(monkeypatch)
    # ⚠ **双边断言**（复核 2026-09-20 打回）：原来的 `assert r is None` 是**单边**的 —— 它在
    #   ① 假 daemon 一次都没跑（线程早死，或每轮都被 `except` 吞掉）、② 客户端压根没提交任务
    #   这两种情形下**同样成立**。而紧邻的 `test_无服务超时_...` 正是一条**没有 daemon**、也断言
    #   `r is None` 的用例 ⇒ 只查这一边，`_mark_error` 这条协议等于**零验证**，"被吞掉的异常"
    #   会继续遮住"daemon 没干活"。⇒ 补上"错误标记**确实被写过**"的正面证据。
    marks: list[tuple[str, str]] = []
    real_mark_error = ds._mark_error

    def _spy(job_dir, jid, message):
        marks.append((str(jid), str(message)))
        return real_mark_error(job_dir, jid, message)

    monkeypatch.setattr(ds, "_mark_error", _spy)
    stop = threading.Event()
    t = _fake_daemon(stop, fail=True)
    r = ds.deep_server_submit_and_wait(
        tmp_path / "b.pdf", tmp_path / "out2", timeout=10.0)
    stop.set()
    t.join(2.0)
    assert r is None
    assert marks, "没有任何错误标记被写过 ⇒ 这条用例其实没验证 _mark_error 协议（假绿）"
    assert any("boom" == m for _, m in marks), f"错误标记的内容不对：{marks}"


def test_无服务超时_返回None并清理任务文件(tmp_path, monkeypatch):
    _bypass_alive(monkeypatch)
    t0 = time.monotonic()
    r = ds.deep_server_submit_and_wait(
        tmp_path / "c.pdf", tmp_path / "out3", timeout=1.5)
    assert r is None
    assert time.monotonic() - t0 >= 1.4
    assert not list(ds._job_dir().glob("*.job.json"))


def test_开关关闭_不提交任务(monkeypatch):
    monkeypatch.setenv("KS_DEEP_SERVER", "0")
    r = ds.deep_server_submit_and_wait(
        __import__("pathlib").Path("x.pdf"), __import__("pathlib").Path("y"),
        timeout=1.0)
    assert r is None  # 客户端直接短路径返回，交回旧版单文档路径


# ---- v3：预投递（submit/wait 拆分）+ spawn 单飞 ----

def test_提交与等待拆分_先投后收(tmp_path, monkeypatch):
    _bypass_alive(monkeypatch)
    # ⚠ 2026-09-19 修一处**偶发**（全量跑里挂过一次：`assert None == {...}`；单独跑 3/3 全过）：
    #   原来把 `time.sleep` 整个换成 no-op ⇒ `deep_server_wait` 成了**纯自旋**。
    #   ⚠ **更正（复核 v3，2026-09-20）**：这里原写"自旋 ⇒ GIL 轮不到假 daemon 线程 ⇒ 极端情况
    #   自旋到 10s 超时"，那句话**被实测否证**：CPython 按时间片让出 GIL，实测纯自旋时另一线程
    #   **9.6ms** 就跑了；并把 no-op 与原版各跑 20 次 —— **两边都 20/20 成功**（no-op mean 0.252s /
    #   原版 mean 0.250s，超时 10s）。⇒ **根因未定**，这次改动**未被证明有效**（它只是把 sleep
    #   收紧到 ≤10ms，保留让步点、读起来更保守）。更可能的来源是上面 `_fake_daemon` 里那个
    #   **unlink/read 真竞争**（已在 `_fake_daemon` 里加了 try/except）。
    real_sleep = time.sleep
    monkeypatch.setattr(ds.time, "sleep", lambda s: real_sleep(min(s, 0.01)))
    sub = ds.deep_server_submit(tmp_path / "a.pdf", tmp_path / "out9")
    assert sub is not None
    # 任务文件立即在盘（不等 daemon）
    assert (ds._job_dir() / f"{sub['job_id']}.job.json").exists()
    stop = threading.Event()
    t = _fake_daemon(stop)
    r = ds.deep_server_wait(sub, timeout=10.0)
    stop.set()
    t.join(2.0)
    assert r == {"output_dir": str(tmp_path / "out9")}
    assert not list(ds._job_dir().glob("*.job.json"))


def test_开关关闭_submit返回None(monkeypatch):
    monkeypatch.setenv("KS_DEEP_SERVER", "0")
    assert ds.deep_server_submit(
        __import__("pathlib").Path("x.pdf"),
        __import__("pathlib").Path("y")) is None
    assert ds.deep_server_wait(None, timeout=1.0) is None


def test_并发冷启动_按目标数拉起不超额(monkeypatch, tmp_path):
    """单飞锁：多客户端同时发现 daemon 不足，只补足 KS_DEEP_WORKERS 个，
    不超额 spawn（2026-08-27 双 daemon 抢目录事故回归测试）。"""
    state = {"alive": 0, "spawned": 0}

    monkeypatch.setattr(ds, "_alive_count", lambda _jd: state["alive"])
    monkeypatch.setattr(ds, "_wait_first_heartbeat", lambda *_: None)

    def fake_start():
        state["spawned"] += 1
        state["alive"] += 1          # daemon 起来后心跳可见

    monkeypatch.setattr(ds, "_start_server", fake_start)

    barrier = threading.Barrier(4)
    errors: list[Exception] = []

    def worker():
        try:
            barrier.wait()
            ds._ensure_server(ds._job_dir())
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert state["spawned"] == 2     # 目标 2 个，不多不少


def test_任务抢占_两个收集者不重叠(monkeypatch, tmp_path):
    """v5 抢占锁：daemon A 领走的任务，daemon B 的 _collect_jobs 拿不到。"""
    import json as _json
    for i in range(5):                # ≥ KS_DEEP_BATCH_MIN(4)，绕开攒批等待门
        (tmp_path / f"{i:024d}.job.json").write_text(_json.dumps({
            "pdf": f"p{i}.pdf", "out_dir": str(tmp_path / f"o{i}"),
            "job_id": f"{i:024d}"}), encoding="utf-8")
    a = ds._collect_jobs(tmp_path)
    b = ds._collect_jobs(tmp_path)
    ids_a = {p.name for p, _ in a}
    ids_b = {p.name for p, _ in b}
    assert len(a) == 5
    assert not (ids_a & ids_b)       # 无重叠
    assert not b                     # 全被 A 抢走
    for _, fh in a:
        fh.close()
