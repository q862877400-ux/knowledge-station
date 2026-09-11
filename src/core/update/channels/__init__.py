"""更新渠道适配器包（可插拔，F-02/F-11/F-12）。

四渠道统一契约见 ``base.ChannelAdapter``；降级链 official_gb→web→govcn 由
inspector（后续批次）编排，本包只保证单渠道 ``probe`` 确定性。
"""
from src.core.update.channels.base import (
    CHANGE_TYPES,
    LEGAL_STATUSES,
    UPD_CHANNEL_TIMEOUT,
    UPD_CAPTCHA_BLOCKED,
    ChannelAdapter,
    ChannelResult,
    HttpxTransport,
    UpdateError,
    derive_change_type,
    looks_like_captcha,
    map_state_text,
    norm_no,
    recordable,
    upd_log,
)
from src.core.update.channels.govcn_announce import GovcnAnnounceAdapter
from src.core.update.channels.laws_db import LawsDbAdapter
from src.core.update.channels.official_gb import OfficialGbAdapter
from src.core.update.channels.web_fallback import WebFallbackAdapter


def _safe_import(name: str, class_name: str):
    """容错导入子代理正在实现的渠道（未完成/语法错不阻塞整体启动，记 warn）。"""
    import importlib
    import logging
    try:
        mod = importlib.import_module(f"src.core.update.channels.{name}")
        return getattr(mod, class_name)
    except Exception as e:  # noqa: BLE001
        logging.getLogger("ks.upd").warning("channel %s 暂不可用（实现中）: %s", name, e)
        return None


#: 渠道名 → 适配器类（channel 枚举与 update_change_event.source_channel 对齐）
ADAPTER_CLASSES = {
    "official_gb": OfficialGbAdapter,
    "web": WebFallbackAdapter,
    "govcn": GovcnAnnounceAdapter,
    "laws_db": LawsDbAdapter,
    # 2026-08 实测接入的渠道（子代理实现中，容错注册）
    "mem_gov": _safe_import("mem_gov", "MemGovAdapter"),
    "std_samr_hb": _safe_import("std_samr_hb", "StdSamrHbAdapter"),
    "hbba": _safe_import("hbba", "HbbaAdapter"),
    "dbba": _safe_import("dbba", "DbbaAdapter"),
    "ndls": _safe_import("ndls", "NdlsAdapter"),
    "mohurd": _safe_import("mohurd", "MohurdAdapter"),
    "ttzb": _safe_import("ttzb", "TtzbAdapter"),
    "mee": _safe_import("mee", "MeeAdapter"),
    # 2026-08-27 实测接入：中国大陆标准服务网（json API、全覆盖、无 Jiasule 验证码）
    "cssn": _safe_import("cssn", "CssnAdapter"),
}

__all__ = [
    "ADAPTER_CLASSES", "CHANGE_TYPES", "LEGAL_STATUSES",
    "ChannelAdapter", "ChannelResult", "HttpxTransport", "UpdateError",
    "OfficialGbAdapter", "WebFallbackAdapter", "GovcnAnnounceAdapter", "LawsDbAdapter",
    "UPD_CHANNEL_TIMEOUT", "UPD_CAPTCHA_BLOCKED",
    "derive_change_type", "looks_like_captcha", "map_state_text",
    "norm_no", "recordable", "upd_log",
]
