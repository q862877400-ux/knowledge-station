"""Parser Worker 隔离（v4.3 第 8.2 节）：MinerU 在独立子进程运行，崩溃不污染主进程。"""
from __future__ import annotations

import multiprocessing as mp
import os
from pathlib import Path
from typing import Any

from src.core.exceptions import ParserTimeoutError, ParserError


def _parser_worker_main(pdf_path: str, output_dir: str, result_queue,
                        force_deep: bool = False,
                        deep_fallback: bool = True) -> None:  # noqa: ANN001
    try:
        from src.core.ingestion.mineru_adapter import parse_pdf_with_mineru
        result = parse_pdf_with_mineru(Path(pdf_path), Path(output_dir),
                                       force_deep=force_deep, deep_fallback=deep_fallback)
        payload: tuple[str, object] = ("success", result)
    except Exception as e:  # noqa: BLE001
        payload = ("error", f"{type(e).__name__}: {e}")
    # 先确保队列数据落盘，再硬退出：
    # mineru 内部持久线程池/进程池会阻止子进程正常退出并驻留 ~2GB 内存
    result_queue.put(payload)
    result_queue.close()
    result_queue.join_thread()
    try:
        import psutil
        for child in psutil.Process().children(recursive=True):
            child.kill()
    except Exception:
        pass
    os._exit(0)


def run_parser_isolated(pdf_path: Path, output_dir: Path, timeout: int = 900,
                        force_deep: bool = False,
                        deep_fallback: bool = True) -> dict[str, Any]:
    """启动子进程解析；超时强杀、崩溃可检测重启。

    注意: 必须先从队列取结果再 join —— 大结果集异步写入管道时,
    先 join 会与子进程的 feeder 线程互锁 (Windows spawn 下尤其明显)。

    deep_fallback=False（2026-09-11，R27 入库预览）：无文本层文档**不调深度通道**
    （云优先 → 会外发）；结果里带 text_layer_state / deep_fallback_skipped 供调用方判定。
    """
    ctx = mp.get_context("spawn")  # Windows 安全启动方式
    result_queue = ctx.Queue()
    proc = ctx.Process(target=_parser_worker_main,
                       args=(str(pdf_path), str(output_dir), result_queue,
                             force_deep, deep_fallback))
    proc.start()

    try:
        status, result = result_queue.get(timeout=timeout)
    except Exception as e:
        if proc.is_alive():
            proc.terminate()
        proc.join()
        raise ParserTimeoutError(timeout) from e
    proc.join(timeout=30)
    if proc.is_alive():
        proc.terminate()  # 兜底：worker 收尾被拖挂时强杀（结果已从队列取得）
        proc.join()

    if proc.exitcode not in (0, None):
        raise ParserError(f"Parser 子进程异常退出 (code={proc.exitcode})")
    if status == "error":
        raise ParserError(f"Parser 错误: {result}")
    return result
