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


def rerank(query: str, texts: list[str]) -> list[float]:
    """返回与 `texts` **一一对应**的相关性分数：`scores[i]` 就是 `texts[i]` 的分，**未排序**。

    模型不可用时抛异常，由调用方降级（R30 语义）。排序是**调用方**的事 ——
    只有它知道下标对应哪个候选。

    ⚠ **2026-10-09 修（施工总纲 P0·0.7）**：旧版返回的是**已按分数降序**的列表，
    而唯一的调用方 `hybrid_engine._rerank_results` 把 `scores[i]` 当"第 i 条候选的分"用
    ⇒ 它那句 `sorted(range(n), key=lambda i: scores[i], reverse=True)` 作用在**降序输入**上
    会退化成**恒等置换** ⇒ **rerank 阶段从不改变顺序**（实测 `var/tmp/probe-rerank-order.py`：
    输出顺序 == 原始顺序），且 `debug["rerank_score"]` 把分数**贴到错的条款**上。
    旧版那个 `top_k` 参数**全仓无人传**，而它的切片语义正是破坏这个对应关系的元凶 ⇒ 一并删掉。
    """
    model = _get_model()
    if not texts:
        return []
    scores = [float(s) for s in model.rerank(query, texts)]
    if len(scores) != len(texts):
        # fail-closed：调用方按下标对齐，长度不符必须当场炸，不许静默错位
        raise ValueError(
            f"reranker 返回 {len(scores)} 个分数，与 {len(texts)} 条候选不匹配")
    return scores


def offline_reason() -> str | None:
    return _load_error
