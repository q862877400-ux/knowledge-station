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
    """监视任务目录，攒批窗口后直接写 done/error（不碰 mineru）。"""
    def run():
        while not stop.is_set():
            jobs = sorted(ds._job_dir().glob("*.job.json"))
            if len(jobs) >= 2 or (jobs and time.time() - jobs[0].stat().st_mtime > 0.2):
                for j in jobs:
                    spec = json.loads(j.read_text(encoding="utf-8"))
                    jid = spec["job_id"]
                    if fail:
                        ds._mark_error(ds._job_dir(), jid, "boom")
                    else:
                        (ds._job_dir() / f"{jid}.done.json").write_text(
                            json.dumps({"output_dir": spec["out_dir"]}),
                            encoding="utf-8")
                    j.unlink()
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
    _fake_daemon(stop)
    r = ds.deep_server_submit_and_wait(
        tmp_path / "a.pdf", tmp_path / "out1", timeout=10.0)
    stop.set()
    assert r == {"output_dir": str(tmp_path / "out1")}
    assert not list(ds._job_dir().glob("*.json")) or all(
        p.name == "server.json" for p in ds._job_dir().glob("*.json"))


def test_任务失败_返回_None_回退信号(tmp_path, monkeypatch):
    _bypass_alive(monkeypatch)
    stop = threading.Event()
    _fake_daemon(stop, fail=True)
    r = ds.deep_server_submit_and_wait(
        tmp_path / "b.pdf", tmp_path / "out2", timeout=10.0)
    stop.set()
    assert r is None


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
    monkeypatch.setattr(ds.time, "sleep", lambda s: None)
    sub = ds.deep_server_submit(tmp_path / "a.pdf", tmp_path / "out9")
    assert sub is not None
    # 任务文件立即在盘（不等 daemon）
    assert (ds._job_dir() / f"{sub['job_id']}.job.json").exists()
    stop = threading.Event()
    _fake_daemon(stop)
    r = ds.deep_server_wait(sub, timeout=10.0)
    stop.set()
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
