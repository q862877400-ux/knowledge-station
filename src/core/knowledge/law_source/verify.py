"""法规效力「点开即核验」服务（任务 2，docs/REALTIME_VALIDITY_VERIFY_RESEARCH.md §2/§3）。

对外契约（唯一入口）::

    verify_law(bbbs: str) -> dict   # 绝不抛异常，任何失败都降级为 unverified

返回字段（API 端点 GET /api/v1/laws/verify?bbbs= 由集成者添加，透传本 dict）::

    {
      "status":       "effective|superseded|withdrawn|upcoming|unmarked|not_found|unverified",
      "status_text":  "现行有效|已修改|已废止|尚未生效|官方未标注效力状态|官方库未收录|未核验",
      "evidence_url": "https://flk.npc.gov.cn/detail?id=<bbbs>",
      "checked_at":   ISO8601（缓存命中时为当初核验时间）,
      "cached":       bool,
      "retryable":    bool（仅 unverified 为 True）,
      # 附加证据字段（有则透传，前端 tooltip 用）：title / issuer / published_date /
      # effective_date / sxx / source
    }

状态映射（权威表：研究报告 §2，与 channels/base.LEGAL_STATUSES 对齐）::

    flk sxx 1=已废止→withdrawn  2=已修改→superseded  3=现行有效→effective  4=尚未生效→upcoming
    详情 data 为空        → not_found（官方库查无此 bbbs）
    详情非空但 sxx 缺失   → unmarked（官方未标注效力状态；cn-law-hub 铁律：不从
                            可访问性/日期推断，只诚实标注「未明确标注」）
    sxx 存在但不在枚举内  → unverified + WARN 告警（不猜测，枚举扩展走 migration）

分级 TTL 缓存（研究报告 §3.3；内存为主 + 可选 JSON 落盘 <data_dir>/verify_cache.json 温启动）::

    effective 24h / superseded·withdrawn 7d / upcoming 6h / unmarked 12h /
    not_found 60s 负缓存 / unverified·异常·未知 sxx 一律不缓存

并发与预算::

    - 单飞锁：per-bbbs threading.Lock，同一 bbbs 并发请求合并为一次上游调用
    - 超时：单请求 5s、总预算 8s（含等锁时间）；交互档不自动重试（用户点重试按钮）
    - 底层 flk_client.detail 内部超时/重试不受本层控制（不可改其文件），
      故用一次性单线程 executor + future.result(timeout) 在本层强制截断；
      超时后残留线程随底层 HTTP 自然结束，结果被丢弃。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any

LOGGER = logging.getLogger("ks.law.verify")

# ---------------------------------------------------------------- 状态映射（冻结）
#: flk 整型时效码 → legal_status 枚举（对齐 channels/base.LEGAL_STATUSES；§2 权威表）
FLK_SXX_MAP: dict[int, str] = {
    1: "withdrawn",
    2: "superseded",
    3: "effective",
    4: "upcoming",
}

#: 全部状态 → 中文徽章文案（unmarked/not_found/unverified 为扩展态，灰徽章）
STATUS_TEXT: dict[str, str] = {
    "effective": "现行有效",
    "superseded": "已修改",
    "withdrawn": "已废止",
    "upcoming": "尚未生效",
    "unmarked": "官方未标注效力状态",
    "not_found": "官方库未收录",
    "unverified": "未核验",
}

#: 官方证据链接（点开即见原文页）
EVIDENCE_URL_TMPL = "https://flk.npc.gov.cn/detail?id={bbbs}"

# ---------------------------------------------------------------- 超时预算
REQUEST_TIMEOUT_S = 5.0    # 单请求上界（交互档；后台巡检 30s 档不归本模块管）
TOTAL_BUDGET_S = 8.0       # 总预算（含等锁）；超出即降级 unverified

# ---------------------------------------------------------------- 分级 TTL（秒）
TTL_HOUR = 3600
TTL_DAY = 24 * TTL_HOUR
TTL_SECONDS: dict[str, int] = {
    "effective": 24 * TTL_HOUR,       # 现行有效：效力变更是低频事件
    "superseded": 7 * TTL_DAY,        # 已修改不会自己复活，最值得长缓存
    "withdrawn": 7 * TTL_DAY,         # 废止同理
    "upcoming": 6 * TTL_HOUR,         # 尚未生效：有明确到期翻转点，短一些
    "unmarked": 12 * TTL_HOUR,        # 只是活性证明，别频繁戳官方
    "not_found": 60,                  # 负缓存：防止坏 bbbs 反复打官方站
    # unverified / 未知 sxx：无键 → 不缓存（下一轮重试）
}

# ---------------------------------------------------------------- 落盘缓存
CACHE_FILENAME = "verify_cache.json"
_MAX_PERSIST_ENTRIES = 2000   # 落盘条目上限（超出按 cached_at 淘汰最旧）
_PERSIST_DISABLED = os.environ.get("KS_VERIFY_CACHE_OFF", "") not in ("", "0")

# ---------------------------------------------------------------- 进程内状态
_MEM_LOCK = threading.Lock()
_MEM: dict[str, dict[str, Any]] = {}     # bbbs -> {"expires_at","cached_at","payload"}
_DISK_LOADED = False                     # 温启动懒加载标记（进程内一次）

_SF_GUARD = threading.Lock()
_SF_LOCKS: dict[str, threading.Lock] = {}  # bbbs -> 单飞锁


def evidence_url(bbbs: str) -> str:
    """官方证据页链接。"""
    return EVIDENCE_URL_TMPL.format(bbbs=bbbs)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _norm_sxx(v: Any) -> int | None:
    """sxx 归一为 int；无法安全转换返回 None（调用方告警不猜测）。bool 显式排除。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and float(v).is_integer():
        return int(v)
    if isinstance(v, str) and v.strip().isdigit():
        return int(v.strip())
    return None


# ---------------------------------------------------------------- 结果组装
def _result(status: str, *, bbbs: str, title: str = "", detail: Any = None,
            sxx: int | None = None) -> dict[str, Any]:
    """统一载荷形状：核心五字段 + 附加证据字段 + retryable（仅 unverified 为 True）。"""
    out: dict[str, Any] = {
        "status": status,
        "status_text": STATUS_TEXT.get(status, STATUS_TEXT["unverified"]),
        "evidence_url": evidence_url(bbbs),
        "checked_at": _now_iso(),
        "cached": False,
        "retryable": status == "unverified",
    }
    if title:
        out["title"] = title
    if detail is not None:
        for key, attr in (("issuer", "zdjgName"), ("published_date", "gbrq"),
                          ("effective_date", "sxrq")):
            val = str(getattr(detail, attr, "") or "").strip()
            if val:
                out[key] = val
    if sxx is not None:
        out["sxx"] = sxx
    return out


def _unverified(bbbs: str, reason: str) -> dict[str, Any]:
    out = _result("unverified", bbbs=bbbs)
    out["reason"] = reason
    return out


# ---------------------------------------------------------------- 缓存（内存 + 可选落盘）
def _cache_path():
    from src.core.config import get_settings
    return get_settings().data_dir / CACHE_FILENAME


def _load_disk_locked() -> None:
    """温启动：进程内首次触达时把落盘缓存里仍未过期的条目装回内存（坏文件静默跳过）。"""
    global _DISK_LOADED
    _DISK_LOADED = True
    if _PERSIST_DISABLED:
        return
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 文件不存在/损坏都当冷启动
        return
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return
    now = time.time()
    for k, v in entries.items():
        exp, payload = v.get("expires_at"), v.get("payload")
        if (isinstance(exp, (int, float)) and isinstance(payload, dict)
                and exp > now):
            _MEM[str(k)] = {"expires_at": float(exp),
                            "cached_at": float(v.get("cached_at") or exp),
                            "payload": payload}


def _save_disk_locked() -> None:
    """写穿落盘（best-effort：任何 IO 失败只记日志，绝不影响核验主流程）。"""
    if _PERSIST_DISABLED:
        return
    try:
        now = time.time()
        live = {k: v for k, v in _MEM.items() if v["expires_at"] > now}
        if len(live) > _MAX_PERSIST_ENTRIES:
            keep = sorted(live.items(), key=lambda kv: kv[1].get("cached_at", 0.0),
                          reverse=True)[:_MAX_PERSIST_ENTRIES]
            live = dict(keep)
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(
            {"version": 1, "saved_at": _now_iso(), "entries": live},
            ensure_ascii=False, indent=0), encoding="utf-8")
        tmp.replace(path)  # 同卷原子替换，避免读到半截文件
    except Exception as e:  # noqa: BLE001
        LOGGER.debug("verify_cache_persist_failed error=%s:%s", type(e).__name__, e)


def _cache_get(bbbs: str) -> dict[str, Any] | None:
    """命中返回缓存条目（含 payload/expires_at），过期即清除并返回 None。"""
    now = time.time()
    with _MEM_LOCK:
        if not _DISK_LOADED:
            _load_disk_locked()
        ent = _MEM.get(bbbs)
        if ent is None:
            return None
        if ent["expires_at"] > now:
            return ent
        _MEM.pop(bbbs, None)
        return None


def _cache_put(bbbs: str, payload: dict[str, Any], ttl_s: int | None) -> None:
    """写入缓存（payload 剥离 cached 标记后存原始结果）；ttl None 表示不缓存。"""
    if not ttl_s or ttl_s <= 0:
        return
    clean = {k: v for k, v in payload.items() if k != "cached"}
    now = time.time()
    with _MEM_LOCK:
        _MEM[bbbs] = {"expires_at": now + ttl_s, "cached_at": now, "payload": clean}
        _save_disk_locked()


def reset_verify_cache() -> None:
    """清空进程内缓存并复位温启动标记（测试/运维钩子；不动磁盘文件）。"""
    global _DISK_LOADED
    with _MEM_LOCK:
        _MEM.clear()
        _DISK_LOADED = False


# ---------------------------------------------------------------- 上游调用（超时截断）
def _call_detail(bbbs: str):
    """worker 线程内执行：运行期属性访问 flk_client.detail，保证 monkeypatch 生效。"""
    from src.core.knowledge.law_source import flk_client
    return flk_client.detail(bbbs)


def _probe_with_budget(bbbs: str, deadline: float):
    """在剩余预算内调一次官方详情；返回 (detail, None)；超时/异常返回 (None, reason)。"""
    remaining = deadline - time.monotonic()
    wait_s = min(REQUEST_TIMEOUT_S, remaining)
    if wait_s <= 0:
        return None, "budget_exhausted"
    ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix="law-verify")
    try:
        fut = ex.submit(_call_detail, bbbs)
        try:
            return fut.result(timeout=wait_s), None
        except FutureTimeoutError:
            return None, "timeout"
        except Exception as e:  # noqa: BLE001 — flk 层任何异常（网络/HTTP/解析）都归一降级
            LOGGER.warning("verify_probe_error bbbs=%s error=%s:%s",
                           bbbs, type(e).__name__, e)
            return None, f"error:{type(e).__name__}"
    finally:
        # 不等待残留线程：底层 requests 自有超时，结束后线程自然退出，结果被丢弃
        ex.shutdown(wait=False, cancel_futures=True)


def _map_detail(d: Any, bbbs: str) -> tuple[dict[str, Any], int | None]:
    """FlkDetail → (payload, ttl)。映射规则见模块 docstring（严格枚举，未知不猜测）。"""
    raw = getattr(d, "raw", None)
    sxx_raw = getattr(d, "sxx", None)

    # ① 详情 data 为空 → 官方库查无（60s 负缓存）；最小 mock 无 raw 且无 sxx 时同判
    if (raw is not None and not raw) or (raw is None and _is_blank(sxx_raw)):
        return _result("not_found", bbbs=bbbs), TTL_SECONDS["not_found"]

    # ② 详情非空但没有时效字段 → 诚实「未标注」，不从可访问性推断
    if _is_blank(sxx_raw):
        title = str(getattr(d, "title", "") or "")
        return (_result("unmarked", bbbs=bbbs, title=title, detail=d),
                TTL_SECONDS["unmarked"])

    # ③ 严格枚举映射；未知值告警降级，绝不猜
    key = _norm_sxx(sxx_raw)
    status = FLK_SXX_MAP.get(key) if key is not None else None
    if status is None:
        LOGGER.warning("illegal_flk_sxx bbbs=%s sxx=%r（不猜测，降级 unverified）",
                       bbbs, sxx_raw)
        return _unverified(bbbs, f"unknown_sxx:{sxx_raw!r}"), None

    title = str(getattr(d, "title", "") or "")
    return _result(status, bbbs=bbbs, title=title, detail=d, sxx=key), \
        TTL_SECONDS[status]


# ---------------------------------------------------------------- 单飞锁
def _sf_lock(bbbs: str) -> threading.Lock:
    with _SF_GUARD:
        lock = _SF_LOCKS.get(bbbs)
        if lock is None:
            lock = _SF_LOCKS[bbbs] = threading.Lock()
        return lock


# ---------------------------------------------------------------- 主入口
def verify_law(bbbs: str) -> dict:
    """核验单部法规的官方效力状态。绝不抛异常；详见模块 docstring 契约。

    流程：读缓存（内存→温启动落盘）→ per-bbbs 单飞锁（double-check）→
    预算内打一次 flk 详情 → 严格 sxx 映射 → 写分级 TTL 缓存 → 返回载荷。
    """
    bbbs = str(bbbs or "").strip()
    try:
        if not bbbs:
            out = _unverified("", "empty_bbbs")
            out["retryable"] = False   # 入参为空，重试同样无意义
            return out

        # ① 缓存命中直接回（checked_at 保持当初核验时间，cached=True）
        hit = _cache_get(bbbs)
        if hit is not None:
            out = dict(hit["payload"])
            out["cached"] = True
            return out

        # ② 单飞：同 bbbs 并发合并为一次上游调用；等锁也受总预算约束
        deadline = time.monotonic() + TOTAL_BUDGET_S
        lock = _sf_lock(bbbs)
        if not lock.acquire(timeout=max(0.05, deadline - time.monotonic())):
            LOGGER.warning("verify_singleflight_timeout bbbs=%s", bbbs)
            return _unverified(bbbs, "singleflight_timeout")
        try:
            # double-check：前一个持有者可能刚写好缓存
            hit = _cache_get(bbbs)
            if hit is not None:
                out = dict(hit["payload"])
                out["cached"] = True
                return out

            # ③ 预算内打一次官方详情
            d, reason = _probe_with_budget(bbbs, deadline)
            if d is None:
                LOGGER.warning("verify_degraded bbbs=%s reason=%s（不缓存）", bbbs, reason)
                return _unverified(bbbs, reason or "error")

            # ④ 映射 + 分级 TTL 缓存
            payload, ttl = _map_detail(d, bbbs)
            _cache_put(bbbs, payload, ttl)
            return payload
        finally:
            lock.release()
    except Exception as e:  # noqa: BLE001 — 最后防线：核验永不阻塞业务、从不上抛
        LOGGER.warning("verify_law_internal_error bbbs=%s error=%s:%s",
                       bbbs, type(e).__name__, e)
        return _unverified(bbbs, "internal_error")
