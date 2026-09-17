# -*- coding: utf-8 -*-
"""异步批量预览（preview_jobs）引擎侧测试——L239 设计的验收网。

覆盖：状态机（pending→running→done）、进度推进、单件失败不中断整批、
abort 协作式中断（已完成的行保留）、幂等 abort、僵尸自愈（登记 running
而线程死 → GET 标 failed）、任务保留上限淘汰、_public_view 瘦身（不泄
thread_ref/stop_flag）、rows 分页。
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from src.core.ingestion import preview_jobs


@pytest.fixture(autouse=True)
def _isolate_jobs():
    preview_jobs._reset_for_tests()
    yield
    preview_jobs._reset_for_tests()


def _wait_terminal(job_id: str, timeout_s: float = 60.0) -> dict:
    """轮询到 terminal（done/aborted/failed）或超时——返回最后一次视图。"""
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = preview_jobs.get_job(job_id)
        assert last is not None
        if last["status"] in ("done", "aborted", "failed"):
            return last
        time.sleep(0.05)
    assert last is not None
    return last


def _make_pdf(path: Path, pages: int = 1) -> Path:
    """造一个最小可解析 PDF（pypdf/fitz 都能开）。"""
    import fitz
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


class TestStateMachine:
    def test_create_returns_pending_view_with_total(self, tmp_path):
        p = _make_pdf(tmp_path / "a.pdf")
        view = preview_jobs.create_job([str(p)])
        assert view["status"] in ("pending", "running")
        assert view["total"] == 1
        # 瘦身视图不泄内部字段
        assert "thread_ref" not in view
        assert "stop_flag" not in view

    def test_full_run_reaches_done_and_buckets_conserved(self, tmp_path):
        paths = [str(_make_pdf(tmp_path / f"{i}.pdf")) for i in range(3)]
        view = preview_jobs.create_job(paths)
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"
        assert fin["done"] == 3
        # 三桶守恒：ok+warn+block == done
        assert sum(fin["buckets"].values()) == 3

    def test_batch_size_truncates(self, tmp_path):
        paths = [str(_make_pdf(tmp_path / f"{i}.pdf")) for i in range(5)]
        view = preview_jobs.create_job(paths, batch_size=2)
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"
        assert fin["total"] == 2
        assert fin["done"] == 2

    def test_single_file_failure_does_not_break_batch(self, tmp_path):
        ok = _make_pdf(tmp_path / "ok.pdf")
        missing = tmp_path / "missing.pdf"  # 不存在——单件失败
        ok2 = _make_pdf(tmp_path / "ok2.pdf")
        view = preview_jobs.create_job([str(missing), str(ok), str(ok2)])
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"  # 整批仍 done
        assert fin["done"] == 3
        # 失败件进 block 桶
        assert fin["buckets"].get("block", 0) >= 1


class TestAbort:
    def test_abort_on_terminal_is_idempotent_noop(self, tmp_path):
        p = _make_pdf(tmp_path / "a.pdf")
        view = preview_jobs.create_job([str(p)])
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"
        v2 = preview_jobs.abort_job(view["job_id"])
        assert v2["status"] == "done"  # 不改状态

    def test_abort_running_marks_aborted_keeps_done_rows(self, tmp_path):
        # 造一批量较大、单件较慢的任务：100 件，abort 后 worker ≤16 件内停
        paths = [str(_make_pdf(tmp_path / f"{i}.pdf", pages=2)) for i in range(100)]
        view = preview_jobs.create_job(paths)
        job_id = view["job_id"]
        # 等 worker 真正开始跑**且至少完成 1 件**再 abort。
        # ⚠ 原先只等 `status == "running"` 就 abort，而 worker 是**先置 running、再处理第 1 件**
        # （见 preview_jobs worker 开头），于是 abort 常常落在第 1 件完成之前 → `done == 0`
        # → 下面的 `done >= 1` 变成**概率性失败**（独立复核实测约一半概率红；在改动前的提交上
        # 同样复现 ⇒ 既有 flaky，非本次引入）。本测试要证的是"**已完成的行被保留**"，
        # 那就必须先有已完成的行——等它是把不确定性消掉，不是放宽断言。
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            cur = preview_jobs.get_job(job_id)
            if cur["status"] == "running" and cur["done"] >= 1:
                break
            if cur["status"] in ("done", "aborted", "failed"):
                break
            time.sleep(0.02)
        r = preview_jobs.abort_job(job_id)
        assert r is not None
        fin = _wait_terminal(job_id, timeout_s=30)
        assert fin["status"] == "aborted", (
            f"没能在任务跑完前中断（status={fin['status']}, done={fin['done']}/100）——"
            "若机器快到 100 件跑完都没轮到 abort，请加大工作量而不是放宽断言")
        # 已完成的行保留（部分结果可拿）
        assert fin["done"] >= 1
        assert fin["done"] <= 100
        assert len(fin["rows"]) == fin["done"]
        assert sum(fin["buckets"].values()) == fin["done"]


class TestZombie:
    def test_zombie_running_thread_dead_becomes_failed(self, tmp_path):
        """伪造僵尸：直接往任务表塞 status=running + thread_alive=False。"""
        preview_jobs._preview_jobs["pjob_fake1"] = {
            "job_id": "pjob_fake1", "status": "running", "total": 5, "done": 2,
            "buckets": {"ok": 2, "warn": 0, "block": 0}, "rows": [],
            "error": None, "doc_type": "standard", "sample": 0,
            "thread_alive": False, "thread_ref": None,
            "created_at": "2026-09-12 00:00:00",
            "started_at": "2026-09-12 00:00:01", "finished_at": None,
            "stop_flag": False,
        }
        view = preview_jobs.get_job("pjob_fake1")
        assert view["status"] == "failed"
        assert "僵尸" in (view["error"] or "")

    def test_alive_thread_not_zombie(self, tmp_path):
        """thread_alive=False 但 thread_ref 活着（正常切换间隙）→ 不误杀。"""
        t = threading.Thread(target=lambda: (time.sleep(30)), daemon=True)
        t.start()
        preview_jobs._preview_jobs["pjob_fake2"] = {
            "job_id": "pjob_fake2", "status": "running", "total": 5, "done": 2,
            "buckets": {"ok": 2, "warn": 0, "block": 0}, "rows": [],
            "error": None, "doc_type": "standard", "sample": 0,
            "thread_alive": False, "thread_ref": t,
            "created_at": "2026-09-12 00:00:00",
            "started_at": "2026-09-12 00:00:01", "finished_at": None,
            "stop_flag": False,
        }
        try:
            view = preview_jobs.get_job("pjob_fake2")
            assert view["status"] == "running"
        finally:
            t.join(timeout=0)  # daemon：直接放弃


class TestRetentionPolicy:
    def test_prune_keeps_recent_jobs(self, tmp_path):
        p = _make_pdf(tmp_path / "a.pdf")
        for i in range(preview_jobs._JOBS_KEEP + 2):
            preview_jobs.create_job([str(p)])
        # 等全部 terminal
        time.sleep(0.5)
        assert len(preview_jobs._preview_jobs) <= preview_jobs._JOBS_KEEP


class TestPagination:
    def test_rows_pagination(self, tmp_path):
        paths = [str(_make_pdf(tmp_path / f"{i}.pdf")) for i in range(3)]
        view = preview_jobs.create_job(paths)
        fin = _wait_terminal(view["job_id"])
        jid = fin["job_id"]
        page1 = preview_jobs.get_job(jid, rows_offset=0, rows_limit=2)
        assert len(page1["rows"]) == 2
        assert page1["rows_count"] == 3
        page2 = preview_jobs.get_job(jid, rows_offset=2, rows_limit=2)
        assert len(page2["rows"]) == 1
        # 瘦身行不带内部字段
        for row in page1["rows"]:
            assert set(row.keys()) == {"path", "file_name", "verdict", "grade",
                                       "pages", "total_clauses", "doc_confidence",
                                       "one_line", "reasons", "error"}


class TestEgressContract:
    """异步路径的外发口径（2026-09-17 D5）：

    原口径是"零外发是**结构性事实**"——异步路径恒以 `deep_fallback=False` 调用，
    调用方**无从开启**。D5 改为「**默认安全 + 显式可开 + 如实标注**」，
    故这里钉住三件事：默认 False / 显式 True 真的透传到解析层 / 任务里记下了这个决定。
    """

    def test_default_job_is_no_egress(self, tmp_path, monkeypatch):
        from src.core.ingestion import dry_run
        seen: list[bool] = []

        def _fake(pdf_path, *, doc_type="standard", deep_fallback=False, **kw):
            seen.append(deep_fallback)
            return {"status": "ok", "verdict": "ok", "grade": "A", "pages": 1,
                    "total_clauses": 0, "doc_confidence": 1.0, "one_line": "",
                    "verdict_reasons": [], "layout": {"pages": 1},
                    "ocr_suspects": [], "typing_quality": {"distribution": {}},
                    "egress": "none" if not deep_fallback else "deep_channel"}

        monkeypatch.setattr(dry_run, "analyze_preview_report", _fake)
        p = _make_pdf(tmp_path / "a.pdf")
        view = preview_jobs.create_job([str(p)])
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"
        assert seen == [False], f"异步路径默认必须不外发，实测 {seen}"
        # 控制面必须能拿到外发标注（独立复核 F3：此前 _public_view 不外露 egress，
        # 而 routes 的 docstring 声称"响应里始终带 egress"）
        assert fin["egress"] == "none", fin.get("egress")

    def test_explicit_optin_reaches_parser_and_is_recorded(self, tmp_path, monkeypatch):
        from src.core.ingestion import dry_run
        seen: list[bool] = []

        def _fake(pdf_path, *, doc_type="standard", deep_fallback=False, **kw):
            seen.append(deep_fallback)
            return {"status": "ok", "verdict": "ok", "grade": "A", "pages": 1,
                    "total_clauses": 0, "doc_confidence": 1.0, "one_line": "",
                    "verdict_reasons": [], "layout": {"pages": 1},
                    "ocr_suspects": [], "typing_quality": {"distribution": {}},
                    "egress": "none" if not deep_fallback else "deep_channel"}

        monkeypatch.setattr(dry_run, "analyze_preview_report", _fake)
        p = _make_pdf(tmp_path / "a.pdf")
        view = preview_jobs.create_job([str(p)], deep_fallback=True)
        fin = _wait_terminal(view["job_id"])
        assert fin["status"] == "done"
        assert seen == [True], f"显式开启没有透传到解析层（假修）：{seen}"
        # 决定被记录在任务里（不是只存在于调用栈里）
        assert preview_jobs._preview_jobs[fin["job_id"]]["deep_fallback"] is True
        # 且控制面能看到它（F3）
        assert fin["egress"] == "deep_channel", fin.get("egress")

