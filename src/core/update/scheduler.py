"""定时巡检调度器（阶段六·批次2）：沿用 watcher/单写者队列的轻量轮询线程模式。

- 2 秒轮询（P4 少依赖，不起 cron/watchdog），每 tick 检查 app_config：
  - ``update.schedule_days``：距上一 scheduled 巡检批次创建的天数 ≥ N 时自动建批
    （trigger='scheduled'）；≤0 视为关闭调度。
  - ``update.schedule_tiers``：JSON 数组，声明自动建批的层，默认 ["tier0","tier1"]
    （tier0 高频小批 + tier1 万级滚动大批，后者受日预算约束见 inspector）。
  - 预算停留的 tier1 批次（pause_reason='budget'）：新的一天且额度可用时由
    调度器恢复续跑；**验证码暂停（pause_reason='captcha'）绝不自动 resume**
    ——必须人工过点确认（pipeline/05 §3、INS-C-03）。
- 时间比较统一用 UTC（sqlite datetime('now') 即 UTC）；tick(now=...) 可注入假时钟。

调度器只负责「建批 / 恢复」，不直接执行批次——执行由 API 层或运维入口调用
``inspector.run_batch``（本批测试即直调），保持编排与执行分离。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from src.core.storage.sqlite_db import get_db_connection
from src.core.update import inspector
from src.core.update.channels.base import upd_log

#: 轮询周期（秒），与 watcher 的 2s 模式一致
POLL_INTERVAL_S = 2.0
DEFAULT_SCHEDULE_DAYS = 7
DEFAULT_SCHEDULE_TIERS = ("tier0", "tier1")


def _parse_created_at(raw: str | None) -> datetime | None:
    """sqlite datetime('now') 串 → UTC aware datetime；解析失败返回 None。"""
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None


def schedule_days() -> int:
    """读取调度周期天数；缺省 7，非法/≤0 返回 0 表示关闭。"""
    raw = inspector.get_config("update.schedule_days")
    if raw is None:
        return DEFAULT_SCHEDULE_DAYS
    try:
        days = int(float(raw))
    except (TypeError, ValueError):
        return 0
    return days if days > 0 else 0


def schedule_tiers() -> list[str]:
    """自动建批的层清单；非法 JSON 回退默认双层。"""
    raw = inspector.get_config("update.schedule_tiers")
    if not raw:
        return list(DEFAULT_SCHEDULE_TIERS)
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return list(DEFAULT_SCHEDULE_TIERS)
    if isinstance(data, str):
        data = [data]
    tiers = [t for t in (data or []) if t in ("tier0", "tier1")]
    return tiers or list(DEFAULT_SCHEDULE_TIERS)


class UpdateScheduler:
    """定时巡检轮询线程：start() 后台运行，tick() 可独立注入时钟测试。"""

    def __init__(self, poll_interval: float = POLL_INTERVAL_S,
                 resume_kwargs: dict | None = None):
        self._poll_interval = max(0.01, float(poll_interval))
        self._resume_kwargs = dict(resume_kwargs or {})
        self._cv = threading.Condition()
        self._thread: threading.Thread | None = None
        self._stop = False

    # ------------------------------------------------------------ 生命周期
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="ks-update-scheduler",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None

    def _run(self) -> None:
        while True:
            with self._cv:
                if self._stop:
                    return
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 — 调度线程必须吞异常存活（UPD-5001 口径）
                upd_log("-", "scheduler", "ERROR", "scheduler_crash",
                        err=f"{type(exc).__name__}: {exc}")
            with self._cv:
                self._cv.wait(self._poll_interval)

    # ------------------------------------------------------------ 编排逻辑
    def _last_scheduled_created_at(self) -> datetime | None:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT MAX(created_at) AS last_at FROM bulk_import_batch"
            " WHERE batch_kind='inspect' AND trigger_type='scheduled'").fetchone()
        return _parse_created_at(row["last_at"] if row else None)

    def _create_scheduled_batches(self, now: datetime) -> list[str]:
        """到期则按 schedule_tiers 各建一个 scheduled 批次，返回新批次 id。"""
        days = schedule_days()
        if days <= 0:
            return []
        last = self._last_scheduled_created_at()
        if last is not None and (now - last).total_seconds() < days * 86400:
            return []
        created = []
        for tier in schedule_tiers():
            batch = inspector.create_inspect_batch(tier=tier, trigger="scheduled")
            created.append(batch["batch_id"])
            upd_log(batch["batch_id"], "scheduler", "INFO", "scheduled_batch_created",
                    tier=tier, schedule_days=days)
        return created

    def _resume_budget_paused(self, now: datetime) -> list[str]:
        """跨日恢复预算停留批次：仅 budget 原因 + 今日有剩余额度才续跑。

        验证码暂停（captcha）在此被显式排除——定时器不得自动 resume，
        必须人工过点后调 resume_batch（INS-C-03 / pipeline/05 §3 熔断产品化）。
        """
        resumed: list[str] = []
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT batch_id, checkpoint_json FROM bulk_import_batch"
            " WHERE batch_kind='inspect' AND status='paused' AND tier='tier1'"
            " ORDER BY created_at").fetchall()
        for row in rows:
            try:
                ckpt = json.loads(row["checkpoint_json"] or "{}")
            except (TypeError, ValueError):
                ckpt = {}
            if ckpt.get("pause_reason") != "budget":
                continue  # captcha/user 暂停一律不动
            if inspector.budget_remaining() <= 0:
                break  # 今日额度已尽，其余批次留待次日
            queue_left = len(ckpt.get("queue") or [])
            if queue_left == 0:
                continue  # 无剩余任务，等待人工处理
            batch = inspector.resume_batch(row["batch_id"], **self._resume_kwargs)
            resumed.append(row["batch_id"])
            upd_log(row["batch_id"], "scheduler", "INFO", "budget_batch_resumed",
                    status=batch.get("status"))
        return resumed

    def tick(self, now: datetime | None = None) -> dict:
        """一次调度拍：返回本拍动作 {created:[...], resumed:[...]}（可注入假时钟）。"""
        moment = now or datetime.now(timezone.utc)
        created = self._create_scheduled_batches(moment)
        resumed = self._resume_budget_paused(moment)
        return {"created": created, "resumed": resumed}
