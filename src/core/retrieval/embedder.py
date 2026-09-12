"""本地向量模型封装（fastembed bge-small-zh-v1.5, CPU/ONNX）。

模型权重置于 settings.models_dir，首次使用会自动下载一次；
此后离线可用。向量引擎不可用时抛 VectorEngineOfflineError，
由检索层降级（R30）。
"""
from __future__ import annotations

import threading
from typing import Sequence

from src.core.config import get_settings
from src.core.exceptions import VectorEngineOfflineError

EMBEDDING_DIM = 512  # bge-small-zh-v1.5

_model = None
_lock = threading.Lock()
_load_error: str | None = None


def _get_model():
    global _model, _load_error
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from fastembed import TextEmbedding  # type: ignore[import-untyped]  # fastembed 无稳定 stub；双保险
            settings = get_settings()
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            _model = TextEmbedding(
                model_name="BAAI/bge-small-zh-v1.5",
                cache_dir=str(settings.models_dir),
            )
        except Exception as e:  # noqa: BLE001
            _load_error = str(e)
            raise VectorEngineOfflineError() from e
    return _model


def embed_query(text: str) -> list[float]:
    m = _get_model()
    return [float(x) for x in next(iter(m.embed([text])))]


def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    m = _get_model()
    return [[float(x) for x in e] for e in m.embed(list(texts))]


def is_available() -> bool:
    try:
        _get_model()
        return True
    except VectorEngineOfflineError:
        return False


def offline_reason() -> str | None:
    return _load_error
