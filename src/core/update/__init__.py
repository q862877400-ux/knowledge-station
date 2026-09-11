"""「更新」模块（阶段六，pipeline/02 §1 拓扑）。

批次1交付：``channels/*``（四渠道适配器）＋ ``change_repo``（变更仓储）。
批次2交付：``inspector``（巡检编排：分层/并发/断点/验证码半自动/日预算）
＋ ``scheduler``（2s 轮询定时建批与预算恢复）。

原则：ULID 前缀、legal_status 枚举、写路径走 write_transaction 单写者、
event_log 审计——与本体规范统一，SSE 冻结不碰。
"""
from src.core.update.channels import (
    ADAPTER_CLASSES,
    ChannelAdapter,
    ChannelResult,
    UpdateError,
)
from src.core.update.channels.base import recordable, upd_log
from src.core.update.inspector import (
    CHAIN,
    CONCURRENCY,
    DEFAULT_DAILY_BUDGET,
    MAX_ATTEMPTS,
    ProbeOutcome,
    budget_remaining,
    budget_used_today,
    captcha_wait_events,
    create_inspect_batch,
    daily_budget_limit,
    get_config,
    get_inspect_batch,
    judge_result,
    pause_batch,
    request_pause,
    resume_batch,
    run_batch,
    select_standard_nos,
    set_config,
)
from src.core.update.scheduler import POLL_INTERVAL_S, UpdateScheduler

__all__ = [
    # channels（批次1 契约冻结面）
    "ADAPTER_CLASSES", "ChannelAdapter", "ChannelResult", "UpdateError",
    "recordable", "upd_log",
    # inspector（批次2 巡检编排）
    "CHAIN", "CONCURRENCY", "DEFAULT_DAILY_BUDGET", "MAX_ATTEMPTS",
    "ProbeOutcome", "budget_remaining", "budget_used_today",
    "captcha_wait_events", "create_inspect_batch", "daily_budget_limit",
    "get_config", "get_inspect_batch", "judge_result", "pause_batch",
    "request_pause", "resume_batch", "run_batch", "select_standard_nos",
    "set_config",
    # scheduler（批次2 定时调度）
    "POLL_INTERVAL_S", "UpdateScheduler",
]
