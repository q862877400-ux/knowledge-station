"""常驻深度解析服务（GPU 攒批，2026-08-27）。

用户问题："GPU 占用不稳定，为啥不并行？"——
- 多进程同时上卡 = 多份模型显存副本，16GB 只容一份（~8GB），第二份必 OOM
  （此前三分片互踩实测）；
- 单文档单次 do_parse 时，mineru 管线的 CPU 阶段（PDF 渲染/后处理/JSON）
  与 GPU 阶段交替，GPU 占用忽高忽低；
- mineru 2.x 原生支持多文件窗口批处理（window_size=64, Batch Ratio 16）：
  把多本文档合并进一次 do_parse，GPU 拿到混合大批次 → 占用稳定且吞吐倍增。

架构：常驻 daemon 进程（模型只加载一次，~2.6s 热缓存）监视任务目录；
客户端把 PDF 任务写成 .job.json 后轮询 .done/.error。崩溃自愈：daemon
死亡 → 心跳过期 → 下一个客户端重新拉起；批量失败 → 逐任务标 error →
客户端回退旧版单文档 spawn 路径。环境开关 KS_DEEP_SERVER=0 全关。

v5（2026-08-28 双实例）：实测管线瓶颈在 CPU 侧后处理（435 页推理仅 12s
@36页/秒，整批却 270s @1.6页/秒），单实例喂不饱 GPU。改为双 daemon
（KS_DEEP_WORKERS，默认 2，显存账 2×~5GB+桌面 <16GB）：心跳按 pid 分记，
任务文件非阻塞抢占锁（谁锁上谁处理），A 实例推理时 B 实例消化后处理。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

JOB_POLL_S = 0.5
HEARTBEAT_STALE_S = 120.0
_SUBMIT_ENV = "KS_DEEP_JOBS_DIR"


def _job_dir() -> Path:
    d = Path(os.environ.get(_SUBMIT_ENV) or
             (Path(tempfile.gettempdir()) / "ks_deep_jobs"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _heartbeat_path(job_dir: Path) -> Path:
    """按实例心跳：server-{pid}.json（v5 多 daemon 并存，各自写各自的心跳）。"""
    return job_dir / f"server-{os.getpid()}.json"


def _server_alive(job_dir: Path) -> bool:
    return _alive_count(job_dir) > 0


def _alive_count(job_dir: Path) -> int:
    """新鲜心跳的 daemon 数（供多实例目标数判断）。"""
    n = 0
    for hb in job_dir.glob("server-*.json"):
        try:
            info = json.loads(hb.read_text(encoding="utf-8"))
            if time.time() - float(info["ts"]) > HEARTBEAT_STALE_S:
                continue
            import psutil
            if psutil.pid_exists(int(info["pid"])):
                n += 1
        except Exception:  # noqa: BLE001
            continue
    return n


def _target_workers() -> int:
    """常驻 daemon 目标数。默认 2：管线后处理是 CPU 串行瓶颈（实测 GPU
    推理 36 页/秒 vs 整批 1.6 页/秒），双实例让 A 的推理与 B 的后处理重叠。
    显存账：桌面 ~1.4GB + 模型 ~5GB/份 ×2 ≈ 11.5GB < 16GB；3 份会 OOM。"""
    try:
        return max(1, int(os.environ.get("KS_DEEP_WORKERS", "2")))
    except ValueError:
        return 2


def _start_server() -> None:
    """拉起常驻 daemon（脱离父进程组，随客户端崩溃不连坐）。

    cwd 必须是 repo 根（src/core/ingestion/deep_server.py 的 parents[3]），
    否则 `from src.core...` 导入失败、daemon 秒死——2026-08-27 实测教训。
    输出落 server.log 便于诊断（不再 DEVNULL 吞错）。
    """
    job_dir = _job_dir()
    creation = 0
    if sys.platform == "win32":
        creation = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    log_fh = open(job_dir / "server.log", "ab")  # noqa: SIM115 - daemon 生命周期
    subprocess.Popen(
        [sys.executable, "-c",
         "from src.core.ingestion.deep_server import server_main; server_main()"],
        cwd=Path(__file__).resolve().parents[3],  # repo root
        creationflags=creation,
        stdout=log_fh, stderr=log_fh,
    )


def _ensure_server(job_dir: Path) -> None:
    """确保常驻 daemon 达到目标数（跨进程单飞）。

    2026-08-27 实测教训：
    - 3 分片同时冷启动各 spawn 一个 daemon → 抢同一任务目录
      （任务双处理 + error.json PermissionError）→ 文件锁内二次确认；
    - v5 双实例：目标数 KS_DEEP_WORKERS（默认 2，显存上限），锁内补足差额，
      spawn 后原地等首跳心跳再放锁，防止下一客户端在心跳出现前重复 spawn。
    """
    if _alive_count(job_dir) >= _target_workers():
        return
    lock_fh = open(job_dir / ".spawn.lock", "ab")  # noqa: SIM115 - 短临界区
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 1)
        try:
            if _alive_count(job_dir) < _target_workers():  # 锁内二次确认
                _start_server()
                _wait_first_heartbeat(job_dir)
        finally:
            if sys.platform == "win32":
                try:
                    lock_fh.seek(0)
                    msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
    finally:
        lock_fh.close()


def _wait_first_heartbeat(job_dir: Path, timeout_s: float = 40.0) -> None:
    """spawn 后等首个心跳（daemon 首跳前 alive_count=0，会造成超额 spawn）。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if _alive_count(job_dir) >= 1:
            return
        time.sleep(0.5)


def _pid_alive(pid: int) -> bool:
    """跨平台进程存活探测（孤儿识别用：提交者死了 = 任务无人收割）。"""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        k32.CloseHandle(h)
        return True
    return False


def deep_server_submit(pdf_path: Path, out_dir: Path) -> Dict[str, Any] | None:
    """只提交不等待（预投递用）：把 PDF 任务写进队列立即返回句柄。

    返回 {"job_id", "done", "err", "job_dir"}；None = 服务被关闭
    （KS_DEEP_SERVER=0）。之后用 deep_server_wait 收割。
    """
    if os.environ.get("KS_DEEP_SERVER", "1") == "0":
        return None
    job_dir = _job_dir()
    _ensure_server(job_dir)
    job_id = f"{time.time_ns():024d}"
    (job_dir / f"{job_id}.job.json").write_text(json.dumps({
        "pdf": str(pdf_path), "out_dir": str(out_dir), "job_id": job_id,
        "client_pid": os.getpid(),
    }, ensure_ascii=False), encoding="utf-8")
    return {"job_id": job_id,
            "done": str(job_dir / f"{job_id}.done.json"),
            "err": str(job_dir / f"{job_id}.error.json"),
            "job_dir": str(job_dir)}


def deep_server_wait(sub: Dict[str, Any] | None,
                     timeout: float = 1800.0) -> Dict[str, Any] | None:
    """等待一个已提交任务的结果（与提交解耦，支持先投递后收割的流水线）。

    返回 {"output_dir": str} 成功；None = 超时/任务失败/服务死亡
    （调用方应回退旧版单文档路径）。
    """
    if not sub:
        return None
    done = Path(sub["done"])
    err = Path(sub["err"])
    job_dir = Path(sub["job_dir"])
    job_id = str(sub["job_id"])
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if done.exists():
            try:
                return json.loads(done.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return None
            finally:
                _cleanup(job_dir, job_id)
        if err.exists():
            _cleanup(job_dir, job_id)
            return None
        # 死服务早撤：daemon 30s 宽限后仍未起（心跳缺失/进程消失）→
        # 立刻回退旧版单文档路径，不空耗整个 timeout
        elapsed = time.monotonic() - t0
        if elapsed > 30.0 and not _server_alive(job_dir):
            _cleanup(job_dir, job_id)
            return None
        time.sleep(1.0)
    _cleanup(job_dir, job_id)
    return None


def deep_server_submit_and_wait(pdf_path: Path, out_dir: Path,
                                timeout: float = 1800.0) -> Dict[str, Any] | None:
    """提交一个深度任务并等待结果（旧接口，保留给逐本兜底路径）。

    返回 {"output_dir": str} 成功；None = 服务不可用/超时/任务失败
    （调用方应回退旧版单文档路径）。
    """
    sub = deep_server_submit(pdf_path, out_dir)
    return deep_server_wait(sub, timeout=timeout)


def _cleanup(job_dir: Path, job_id: str) -> None:
    for suffix in (".job.json", ".done.json", ".error.json"):
        try:
            (job_dir / f"{job_id}{suffix}").unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# daemon 侧
# ---------------------------------------------------------------------------

def server_main() -> None:  # pragma: no cover - 常驻进程，靠战役集成验证
    try:
        job_dir = _job_dir()
        hb = _heartbeat_path(job_dir)
        from src.core.ingestion.mineru_adapter import mineru_available
        if not mineru_available():
            print("[deep-server] mineru 不可用，退出", flush=True)
            return

        # 心跳独立线程：大批 do_parse 一跑 10-30 分钟，主循环内联心跳会停更
        # → 客户端误判 daemon 死亡 → 拉起第二个 daemon 抢显存 / 客户端提前
        # 弃队转逐本兜底（排队风暴）。2026-08-27 预投递上线当日实测风险。
        def _heartbeat_loop() -> None:
            while True:
                try:
                    hb.write_text(json.dumps(
                        {"pid": os.getpid(), "ts": time.time()}),
                        encoding="utf-8")
                except OSError:
                    pass
                time.sleep(2.0)

        threading.Thread(target=_heartbeat_loop, daemon=True,
                         name="deep-server-heartbeat").start()

        print(f"[deep-server] 启动 pid={os.getpid()} jobs={job_dir}", flush=True)
        while True:
            jobs = _collect_jobs(job_dir)
            if not jobs:
                time.sleep(JOB_POLL_S)
                continue
            _run_batch(job_dir, jobs)
    except Exception:  # noqa: BLE001 - 任何致命错误落日志后退出（客户端会回退）
        import traceback
        traceback.print_exc()
        raise


def _try_claim(path: Path):
    """任务文件抢占：非阻塞锁住首字节，抢到返回句柄（保持锁），抢到失败 None。

    v5 多 daemon 并存：两个 daemon 可能同时 glob 到同一任务文件——
    谁锁上谁处理，抢锁失败的跳过（锁随进程死亡自动释放，崩溃安全）。
    """
    try:
        fh = open(path, "r+b")
    except OSError:
        return None
    try:
        if sys.platform == "win32":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        return fh
    except OSError:
        fh.close()
        return None


def _collect_jobs(job_dir: Path) -> list:
    max_docs = int(os.environ.get("KS_DEEP_BATCH_MAX", "10"))
    min_docs = int(os.environ.get("KS_DEEP_BATCH_MIN", "4"))
    # 2026-08-27 实测：15s 窗口下扫描件到达速率 ~1本/分 → 每批只攒到 1 本，
    # GPU 每 8s 干一票歇半分钟（占空比 <5%）。等批窗拉到 120s 让批次吃满
    # （多文件 do_parse 合并推理，10 本一批 ≈ 每本 2s，比 1 本一批快 4 倍）。
    wait_s = float(os.environ.get("KS_DEEP_BATCH_WAIT", "120"))
    jobs = sorted(job_dir.glob("*.job.json"))
    # 2026-08-28 孤儿隔离（队头死堵防线）：done/error 已写但客户端 5 分钟
    # 未收割（活客户端 1s 轮询内必删），或提交者进程已死 → 任务删除永离
    # 队头。否则孤儿永远排在 sorted 队列最前，daemon 空转重跑同一批、
    # 新任务全部饿死（2026-08-28 实测 3.5h+）。
    if jobs:
        now_ts = time.time()
        alive: list = []
        for j in jobs:
            stem = j.name[:-len(".job.json")]
            orphan = False
            for sig_name in (f"{stem}.done.json", f"{stem}.error.json"):
                try:
                    sig = job_dir / sig_name
                    if sig.exists() and now_ts - sig.stat().st_mtime > 300:
                        orphan = True
                        break
                except OSError:
                    pass
            if not orphan:
                try:
                    pid = json.loads(
                        j.read_text(encoding="utf-8")).get("client_pid")
                    if pid and not _pid_alive(pid):
                        orphan = True
                except Exception:  # noqa: BLE001 - 损坏任务交由 claim 失败路径清理
                    pass
            if orphan:
                try:
                    j.unlink(missing_ok=True)
                except OSError:
                    alive.append(j)  # 删不掉（正被 claim）→ 视作仍在队列
                continue
            alive.append(j)
        jobs = alive
    if not jobs:
        return []
    oldest_age = time.time() - jobs[0].stat().st_mtime
    if len(jobs) < min_docs and oldest_age < wait_s:
        return []  # 攒批窗口：不够一撮且最老的还新鲜 → 再等
    claimed = []
    for j in jobs:
        if len(claimed) >= max_docs:
            break
        fh = _try_claim(j)
        if fh is not None:
            claimed.append((j, fh))
    return claimed


def _run_batch(job_dir: Path, claimed: list) -> None:  # pragma: no cover
    specs: List[Dict[str, str]] = []
    claim_fh: Dict[str, Any] = {}     # job_id -> 文件句柄（锁持满整批，防并发重抢）
    failed_claims: list = []
    for j, fh in claimed:
        try:
            fh.seek(0)
            spec = json.loads(fh.read().decode("utf-8"))
            spec["job_file"] = str(j)
            specs.append(spec)
            claim_fh[spec["job_id"]] = fh
        except Exception:  # noqa: BLE001
            failed_claims.append((j, fh))
    for j, fh in failed_claims:       # 读不出的直接放锁删文件（损坏任务）
        try:
            fh.close()
            j.unlink(missing_ok=True)
        except OSError:
            pass
    if not specs:
        return

    def _release(spec: Dict[str, str]) -> None:
        """批内该本收尾：先关句柄再删任务文件（顺序不可反）。

        2026-08-28 修复（队头死堵真凶）：Windows 上文件句柄未关时 unlink
        必然失败（Python open 不带 FILE_SHARE_DELETE），旧实现"先删后关"
        的删除永远静默失败 → 客户端死亡的孤儿任务永久占据 sorted 队头，
        daemon 每 ~100s 重跑同一批、新任务全部饿死。先关后删：close 与
        unlink 之间的微窗口即使他 daemon 重抢，也只是多算一次且其自己的
        close→unlink 会成功，有界自愈。
        """
        fh = claim_fh.pop(spec["job_id"], None)
        if fh is not None:
            try:
                fh.close()
            except OSError:
                pass
        try:
            Path(spec["job_file"]).unlink(missing_ok=True)
        except OSError:
            pass

    from mineru.cli.common import do_parse
    from src.core.ingestion.mineru_adapter import _gpu_deep_lock

    out_root = job_dir / "out"
    out_root.mkdir(parents=True, exist_ok=True)
    names = [s["job_id"] for s in specs]
    print(f"[deep-server] 批次开始 {len(specs)} 本："
          f"{[Path(s['pdf']).name[:40] for s in specs]}", flush=True)
    t0 = time.monotonic()
    try:
        with _gpu_deep_lock():
            do_parse(str(out_root), names,
                     [Path(s["pdf"]).read_bytes() for s in specs],
                     ["ch"] * len(specs), backend="pipeline",
                     parse_method="auto", f_draw_layout_bbox=False,
                     f_draw_span_bbox=False, f_dump_orig_pdf=False,
                     f_dump_model_output=False)
    except Exception as e:  # noqa: BLE001 - 整批失败 → 全部标 error，客户端回退
        import traceback
        # 2026-08-27 教训：静默标 error 让"锁函数忘 import"这种低级错
        # 吞掉全部批次半小时无人知晓——必须把失败原因打进 server.log
        print(f"[deep-server] 批次失败（{len(specs)} 本）: "
              f"{type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        for s in specs:
            _mark_error(job_dir, s["job_id"], str(e))
            _release(s)
        return
    print(f"[deep-server] 批次完成 {len(specs)} 本，用时 "
          f"{time.monotonic() - t0:.0f}s", flush=True)
    for s in specs:
        src = out_root / s["job_id"]
        dst = Path(s["out_dir"])
        try:
            if src.exists():
                dst.mkdir(parents=True, exist_ok=True)
                if (dst / src.name).exists():
                    shutil.rmtree(dst / src.name, ignore_errors=True)
                shutil.move(str(src), str(dst / src.name))
            (job_dir / f"{s['job_id']}.done.json").write_text(
                json.dumps({"output_dir": str(dst)}, ensure_ascii=False),
                encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            _mark_error(job_dir, s["job_id"], f"output move failed: {e}")
        finally:
            _release(s)


def _mark_error(job_dir: Path, job_id: str, message: str) -> None:
    (job_dir / f"{job_id}.error.json").write_text(
        json.dumps({"message": message}, ensure_ascii=False),
        encoding="utf-8")
