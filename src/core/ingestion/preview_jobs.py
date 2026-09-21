# -*- coding: utf-8 -*-
"""异步批量预览（全量万级）——进程内任务表 + 三端点（2026-09-12 施工，L239 设计）。

设计要点（全部来自 2026-09-11 夜定稿的范式核实）：

1. **为什么异步**：同步 `POST /api/v1/ingest/preview/batch` 的 `limit_files≤200`
   只防单请求内存/payload 膨胀，**不是超时保护**（单本负载下实测 135s）。
   3.5 万本全量必须进程内分批跑 + 进度可轮询 + 可中断。
2. **只读红线 → 不落库账本**：任务表是进程内 dict（`_preview_jobs`），不建表、
   不写 `update_check_batch`。代价（如实声明）：引擎重启丢任务——host 侧
   `ks-ingest.json` 会如实把它标成 stale（不假装仍在跑）。
3. **单件失败不中断整批**：逐件 try，沿用 `preview_batch` 的既有范式。
4. **外发口径**（2026-09-17 D5 修订）：默认 `deep_fallback=False` ⇒ **默认不外发**；
   调用方显式开启才允许走云优先的深度通道（同 `dry_run.preview_batch` 的口径与理由）。
5. **僵尸语义（照 announce.py 的"登记在而线程死 → 自愈"）**：
   进程内版本——GET 时发现 `status=='running'` 且 `thread_alive is False`
   → 标 failed（线程异常退出却没来得及写终态；照 announce 的口径如实报告，
   不留一个永远 running 的假任务）。
6. **abort 是协作式的**：worker 每 N 件检查一次 `_stop_flag`；中断后已完成的
   行保留（用户拿得到部分结果），状态标 `aborted`。
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List

from src.core.ingestion import dry_run

# 进程内任务表（只读红线：不落库）。key=job_id。
_preview_jobs: Dict[str, dict] = {}
_jobs_lock = threading.Lock()

# 任务保留上限（防内存膨胀：一个万级行表 ~ 几 MB；历史任务保留最近 5 个）
_JOBS_KEEP = 5
# worker 每处理多少件检查一次中断标志（万级下 abort 延迟 ≤ 16 件）
_ABORT_CHECK_EVERY = 16


def _prune_jobs_locked() -> None:
    """保留最近 _JOBS_KEEP 个任务（terminal 的旧任务先淘汰）。"""
    if len(_preview_jobs) <= _JOBS_KEEP:
        return
    terminal = [k for k, v in _preview_jobs.items() if v["status"] != "running"]
    # 淘汰最旧的 terminal 任务（created_at 升序）；_job_paths 跟随淘汰
    terminal.sort(key=lambda k: _preview_jobs[k]["created_at"])
    while len(_preview_jobs) > _JOBS_KEEP and terminal:
        dead = terminal.pop(0)
        _preview_jobs.pop(dead, None)
        _job_paths.pop(dead, None)


def create_job(paths: List[str], *, doc_type: str = "standard", deep_fallback: bool = False,
               sample: int = 0, batch_size: int = 0) -> dict:
    """创建异步预览任务并立即返回（worker 后台跑）。

    ``sample``/``batch_size`` 沿用同步接口语义：sample=0 全量（这正是本接口的
    用途）；batch_size>0 时只跑前 N 件（少量试跑）。
    ``deep_fallback`` 默认 ``False`` ⇒ 默认不外发（见模块 docstring 第 4 点 / D5）。
    """
    from ulid import ULID
    job_id = f"pjob_{ULID()}"
    all_paths = [Path(p) for p in paths]
    candidates = all_paths[:batch_size] if batch_size and batch_size > 0 else all_paths
    job = {
        "job_id": job_id,
        "status": "pending",          # pending → running → done/aborted/failed
        "total": len(candidates),
        "done": 0,
        "buckets": {"ok": 0, "warn": 0, "block": 0},
        "rows": [],                   # 瘦身行（同步接口同形态）
        "error": None,
        "doc_type": doc_type,
        "deep_fallback": bool(deep_fallback),   # 默认 False ⇒ 默认不外发（D5）
        "sample": 0,                  # 异步全量：恒 0（抽样是同步接口的事）
        "thread_alive": False,        # 僵尸判定：登记的线程是否还在
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "started_at": None,
        "finished_at": None,
        "stop_flag": False,           # abort 写、worker 读（协作式中断）
    }
    with _jobs_lock:
        _preview_jobs[job_id] = job
        _job_paths[job_id] = [str(p) for p in candidates]  # worker 暂存（同生命周期）
        _prune_jobs_locked()

    t = threading.Thread(target=_worker, args=(job_id,), daemon=True,
                         name=f"ks-preview-job-{job_id}")
    job["thread_ref"] = t             # daemon 线程 + 显式 alive 判定
    t.start()
    return _public_view(job)


def _worker(job_id: str) -> None:
    """后台 worker：逐件预览，单件失败不中断；协作式 abort 检查。"""
    with _jobs_lock:
        job = _preview_jobs.get(job_id)
    if job is None:
        return
    job["status"] = "running"
    job["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    job["thread_alive"] = True
    try:
        paths = [Path(p) for p in _candidate_paths(job_id)]
        doc_type = job["doc_type"]
        deep_fallback = bool(job.get("deep_fallback", False))
        for i, p in enumerate(paths):
            if i % _ABORT_CHECK_EVERY == 0 and job["stop_flag"]:
                job["status"] = "aborted"
                job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                return
            try:
                rep = dry_run.analyze_preview_report(p, doc_type=doc_type,
                                                     deep_fallback=deep_fallback)
            except Exception as e:  # noqa: BLE001 — 单件崩溃不得中断整批
                rep = {"status": "error", "error_code": "unexpected",
                       "verdict": "block", "error_message": f"{type(e).__name__}: {e}",
                       "grade": "D", "total_clauses": 0, "layout": {"pages": 0},
                       "ocr_suspects": [], "typing_quality": {"distribution": {}},
                       "verdict_reasons": [{"code": "B8", "reason": "未预期异常"}],
                       "source": {"file_name": p.name, "path": str(p)}}
            row = {
                "path": str(p), "file_name": p.name,
                "verdict": rep.get("verdict"), "grade": rep.get("grade"),
                "pages": rep.get("pages", 0),
                "total_clauses": rep.get("total_clauses", 0),
                # ⚠ 第 5 步（2026-09-21 复核 R4）：这里原来写 `.get("doc_confidence", 0.0)` ——
                #   于是**同一篇**在「异步全量预览」里崩掉时这一格是 `0.0`，而同步预览同一篇给
                #   `None`（"算不出来"）。0.0 会被读成"真算出来 0 分"，正是本批挂账 ③b 要统一的那件事。
                #   ⇒ 缺省给 `None`（"算不出来"），与 `dry_run` / `pipeline` 两侧同一口径。
                "doc_confidence": rep.get("doc_confidence"),
                "one_line": rep.get("one_line") or "",
                "reasons": [r.get("code") for r in (rep.get("verdict_reasons") or [])][:4],
                "error": rep.get("error_message"),
            }
            job["rows"].append(row)
            job["buckets"][str(row["verdict"] or "block")] = \
                job["buckets"].get(str(row["verdict"] or "block"), 0) + 1
            job["done"] = i + 1
        # 正常跑完（未被 abort）
        if job["status"] == "running":
            job["status"] = "done"
        job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:  # noqa: BLE001 — worker 顶层兜底：绝不让线程静默死
        job["status"] = "failed"
        job["error"] = f"{type(e).__name__}: {e}"
        job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    finally:
        job["thread_alive"] = False


# worker 需要拿到候选清单，但 job dict 里只放了 total（paths 不入 dict——
# 万级路径列表 ×5 任务会翻倍内存；用 job 私有暂存 _job_paths，同 _prune 生命周期）。
_job_paths: Dict[str, List[str]] = {}


def _candidate_paths(job_id: str) -> List[str]:
    return _job_paths.get(job_id, [])


def abort_job(job_id: str) -> dict | None:
    """协作式中断：置 stop_flag；worker 最多再跑 _ABORT_CHECK_EVERY 件后停。"""
    with _jobs_lock:
        job = _preview_jobs.get(job_id)
        if job is None:
            return None
        if job["status"] in ("done", "aborted", "failed"):
            return _public_view(job)   # 幂等：terminal 后 abort 是 no-op
        job["stop_flag"] = True
        return _public_view(job)


def _zombie_check(job: dict) -> None:
    """僵尸自愈（照 announce.py 口径）：登记 running 而线程已死 → 标 failed。

    只在 GET（读路径）做——写路径（worker）永远先于我们置 thread_alive=False，
    不存在把活任务误杀的竞态。**pending 不判僵尸**：create_job 在 start() 之前
    有一个极短窗口（thread_ref 已挂、线程未启动），此时 is_alive()=False 属
    正常，不是僵尸。
    """
    if job["status"] != "running":
        return
    if job.get("thread_alive", False):
        return
    # worker 启动后的正常间隙（GIL 切换点）：thread_ref 还活着就不动
    t = job.get("thread_ref")
    if t is not None and t.is_alive():
        return
    job["status"] = "failed"
    job["error"] = "工作线程已退出但未写终态（僵尸任务，已自愈标 failed）"
    job["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def get_job(job_id: str, *, rows_offset: int = 0, rows_limit: int = 200) -> dict | None:
    """读任务状态 + 进度 + 瘦身行分页（万级行表不能一次全量回）。"""
    with _jobs_lock:
        job = _preview_jobs.get(job_id)
        if job is None:
            return None
        _zombie_check(job)
        return _public_view(job, rows_offset=rows_offset, rows_limit=rows_limit)


def _public_view(job: dict, *, rows_offset: int = 0, rows_limit: int = 200) -> dict:
    """瘦身视图：不带 thread_ref/stop_flag 等内部字段；rows 分页。"""
    rows = job.get("rows", [])
    off = max(0, int(rows_offset))
    lim = max(0, int(rows_limit))
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "total": job["total"],
        "done": job["done"],
        "buckets": dict(job["buckets"]),
        "rows": rows[off:off + lim],
        "rows_count": len(rows),
        "rows_offset": off,
        "error": job["error"],
        "doc_type": job["doc_type"],
        # 外发标注（2026-09-17 独立复核 F3）：异步路径此前**不外露 egress**，而
        # routes 的 docstring 声称"响应里始终带 egress"——调用方开启外发后拿不到任何标注。
        # 与 dry_run 同口径（默认 none；允许深度通道即 deep_channel，保守高报）。
        "egress": "none" if not job.get("deep_fallback", False) else "deep_channel",
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
    }


def _reset_for_tests() -> None:
    """测试隔离：清空进程内任务表与暂存路径。"""
    with _jobs_lock:
        _preview_jobs.clear()
        _job_paths.clear()
