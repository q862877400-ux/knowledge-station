"""入口：python -m src.core.main"""
import threading

from src.core.api.server import run


def _warmup_figure_ocr() -> None:
    """后台预热流程图重绘的 RapidOCR 模型（2026-08-29）。

    实测冷启动首图请求阻塞 ~60s（模型检索+加载在请求线程内），预热后
    首图 ~4s。失败静默——预热失败只影响首次响应速度，不影响正确性。
    """
    def _load():
        try:
            from src.core.figure_redraw import _get_ocr
            _get_ocr()
        except Exception:
            pass
    threading.Thread(target=_load, name="figure-ocr-warmup", daemon=True).start()


if __name__ == "__main__":
    _warmup_figure_ocr()
    run()
