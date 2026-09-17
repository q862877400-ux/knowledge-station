"""本地向量模型封装（fastembed bge-small-zh-v1.5, CPU/ONNX）。

模型权重置于 settings.models_dir，首次使用会自动下载一次；
此后离线可用。向量引擎不可用时抛 VectorEngineOfflineError，
由检索层降级（R30）。

## ⚠ 两条纪律（2026-09-18 §10.74，由"堵多久"量具实测逼出来）

**1. 廉价路径不许触发加载。** `health()` 是**只读既有证据**的三态判据；而
`is_available()` / `embed_*()` 会**真的加载**——首次 = 下载并装载模型。量具实测：
空缓存下一次加载 = **6.6s 且全程占着事件循环**（`/health` 原来是 `async def`，
相当于"每次体检都把引擎堵 6.6 秒"）。**健康检查/诊断一律用 `health()`**：
"加载一个模型来判断它能不能加载"是把体检本身做成了重活。

**2. 失败要进冷却窗口。** `_load_error` 原先**只记不缓存**（记了却不再用于判断）
⇒ 一次失败之后**每次调用都重试**。离线机器上这意味着**每次健康检查、每次检索**
都付一次网络超时；而现在健康检查根本不加载了，检索那条路仍然是每次付一次。
现在失败也被记住 `RETRY_COOLDOWN_S` 秒：窗口内直接复用"上次失败"这个结论，
窗口过去后允许再试一次（瞬时故障能在**一分钟内自愈**，不永久拉黑）。
"""
from __future__ import annotations

import threading
import time
from typing import Sequence

from src.core.config import get_settings
from src.core.exceptions import VectorEngineOfflineError

EMBEDDING_DIM = 512  # bge-small-zh-v1.5

#: 加载失败后的**冷却窗口**（秒）：窗口内**不再重试**（直接复用上次失败的结论）。
#: 取 60s 的理由：一次失败尝试的代价是**秒级到十秒级**（网络下载 / import 重包），
#: 而健康检查与检索都很频繁 ⇒ 60s 把"每次调用都付一次"压成"每分钟最多一次"，
#: 同时保证网络恢复后**一分钟内**自愈。
RETRY_COOLDOWN_S = 60.0

_model = None
_lock = threading.Lock()
_load_error: str | None = None
_error_at: float = 0.0          # time.monotonic() 时刻；仅当 _load_error 非空时有意义


def _import_text_embedding():
    """加载入口的**唯一缝**：测试拿它当替身，不必真装 fastembed、更不必连网。"""
    from fastembed import TextEmbedding  # type: ignore[import-untyped]  # fastembed 无稳定 stub；双保险
    return TextEmbedding


def _cooldown_active() -> bool:
    """上次失败是否仍在冷却窗口内（调用方需**已持有** `_lock`，或接受轻微竞态读）。"""
    return _load_error is not None and (time.monotonic() - _error_at) < RETRY_COOLDOWN_S


def _get_model():
    """取模型（**会加载**；失败抛 `VectorEngineOfflineError`）。

    ⚠ 两个"别退回去"的点（§10.74）：
    · 失败必须**记时刻**（`_error_at`），否则冷却窗口无从判断；
    · 冷却窗口内**不许重试**——那正是"每次调用都付一次网络超时"的来源。
    """
    global _model, _load_error, _error_at
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        if _cooldown_active():
            # 窗口内：复用上次失败，**不重试**（`from None` 不把内部异常挂上去）
            raise VectorEngineOfflineError() from None
        try:
            TextEmbedding = _import_text_embedding()
            settings = get_settings()
            settings.models_dir.mkdir(parents=True, exist_ok=True)
            _model = TextEmbedding(
                model_name="BAAI/bge-small-zh-v1.5",
                cache_dir=str(settings.models_dir),
            )
            _load_error = None            # 成功即清掉"上次失败"（下次失败会重新计时）
        except Exception as e:  # noqa: BLE001
            _load_error = str(e)
            _error_at = time.monotonic()
            raise VectorEngineOfflineError() from e
    return _model


def embed_query(text: str) -> list[float]:
    m = _get_model()
    return [float(x) for x in next(iter(m.embed([text])))]


def embed_batch(texts: Sequence[str]) -> list[list[float]]:
    m = _get_model()
    return [[float(x) for x in e] for e in m.embed(list(texts))]


def is_available() -> bool:
    """**会加载**（首次可能几秒并外发一次下载）——只给"真要拿模型"的路径用。

    健康检查/诊断用 `health()`；这条保留原语义（供 `hybrid_engine` 的向量通道与入库时判断），
    只是失败会进冷却窗口 ⇒ 离线机器上不再**每次**都付一次网络超时。
    """
    try:
        _get_model()
        return True
    except VectorEngineOfflineError:
        return False


def health() -> str:
    """**廉价**三态：`ok` / `offline` / `unknown`（**不加载模型**，只读已有证据）。

    - `ok`：本进程**真的加载成功过**——这是唯一能证明"能用"的证据；
    - `offline`：最近一次加载尝试**失败**（`offline_reason()` 给原因）。窗口内外都报它：
      这是我们手里**唯一**的证据，报"unknown"反而把已知信息丢掉；
    - `unknown`：本进程**还没试过**——如实说"没验证"，**不替它猜**（也绝不为了猜去加载）。

    为什么不让"未试过"也去加载一次：那会把每次健康检查变成长达几秒重活，而且
    **健康检查必须廉价**——真想确认能不能用，那是"做一次检索"或显式触发一次加载的事。
    """
    if _model is not None:
        return "ok"
    if _load_error is not None:
        return "offline"
    return "unknown"


def offline_reason() -> str | None:
    return _load_error
