"""本地 reranker 阶段（Task 10.2）：六通道 RRF 融合后 top-N → rerank → top-K 进 LLM。

- 模型：fastembed TextCrossEncoder("BAAI/bge-reranker-v2-m3")，ONNX/CPU，与 embedding 同运行时。
- 降级（R30 语义）：模型未下载/加载失败/调用异常 → 返回原序，标记 rerank_offline=true，不阻塞。
- 例外/引用边扩入的证据由调用方保证不参与 rerank 淘汰（见 hybrid_engine）。
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# 选型记录（Task 10.2）：路线图指定的 BAAI/bge-reranker-v2-m3 不被 fastembed 0.8.0
# TextCrossEncoder 支持（list_supported_models 无此项），按"零迁移成本/同运行时"原则
# 选用同族中文候选 BAAI/bge-reranker-base；fastembed 升级支持 v2-m3 后按 Golden Set 门禁再评估。
RERANK_MODEL = "BAAI/bge-reranker-base"

_model = None
_lock = threading.Lock()
_load_error: str | None = None


def is_available() -> bool:
    try:
        _get_model()
        return True
    except Exception:
        return False


def _get_model():
    global _model, _load_error
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            settings = get_settings()
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            _model = TextCrossEncoder(RERANK_MODEL, cache_dir=str(settings.models_dir))
        except Exception as e:  # noqa: BLE001
            _load_error = str(e)
            logger.warning("reranker 加载失败（降级为原序）: %s", e)
            raise
    return _model


def rerank(query: str, texts: list[str], top_k: int | None = None) -> list[float]:
    """返回与 texts 等长的相关性分数（已按得分降序）。模型不可用时抛异常由调用方降级。"""
    model = _get_model()
    if not texts:
        return []
    scores = list(model.rerank(query, texts))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    sorted_scores = [scores[i] for i in order]
    if top_k is not None:
        return sorted_scores[:top_k]
    return sorted_scores


def offline_reason() -> str | None:
    return _load_error
