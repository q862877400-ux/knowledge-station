"""巡检编排器（阶段六·批次2）：万级分层调度执行引擎。

职责（pipeline/02 §1、pipeline/06 §3、批次2指令）：
- ``create_inspect_batch``：在 bulk_import_batch 建 kind='inspect' 控制面批次，
  并在同一事务内以**同值 batch_id** 在 update_check_batch 写镜像锚行——
  update_change_event.batch_id 外键冻结指向 update_check_batch（29 号表），
  锚行保证 ``事件.batch_id == bul_ 批次 id`` 直查可用且外键零改动（pipeline/03 §6）。
- ``run_batch``：从 doc_meta 取 standard_no 清单做 tier 过滤
  （tier0 = watch_list ∪ user_doc_bookmark(标准收藏) ∪ 未首检；tier1 = 其余滚动），并发=2 线程池逐号走
  渠道降级链 official_gb→govcn（复用 channels 包 transport 注入）；web 已于 2026-09-18 摘除（§11.0 R5c）；
  单号探测尝试预算 3 次（INS-A-05「重试=3 次后记 failed」口径），耗尽即该号
  failed 不阻塞他号、不提前降级到下一渠道（INS-B-06 同源语义）。
- 判定映射（批次2指令为准）：现行→no_change/green；新版→new_version/yellow；
  废止/替代→superseded|withdrawn/**red**；查无→not_found/gray。
  注意：superseded 记红是本批指令的明确映射（持有被替代标准=高危），
  与 pipeline/04a §4 头注的 🟡 口径不同，以批次2指令为准。
- 结果写 update_change_event，双重防重：同批同号由仓储语义原位更新；
  跨批「同 doc 同 change_type 已存在则跳过」（避免万级滚动每日刷绿）。
- 终态恒等式（ANOM-001 回归）：04a §0「red+yellow+green+gray=total」绑定 done——
  队列跑空但存在未判定号（探测失败/提交隔离）时终态一律 failed，不做 done 假绿。
- 暂停/恢复：pause 在块边界落 checkpoint_json（剩余队列）；resume 从断点续扫，
  验证码挂起号置队列头优先补查，均不产生重复事件。
- 验证码半自动（F-11）：official_gb 返回 captcha=True → 聚合记一条
  event_log('update/captcha_wait', UPD-1002)、批次转 paused（pause_reason='captcha'）、
  该号不计四色不写事件；定时器绝不自动 resume 验证码批次（INS-C-03）。
- 万级预算：daily_full_sweep_budget=500（app_config inspect.daily_full_sweep_budget 可覆盖），
  仅 tier1 消耗额度；当日达预算即 paused（pause_reason='budget'）停留待次日。

并发与一致性：工作线程只跑渠道探测（零 DB 触碰）；每个号的
[事件落库+计数+断点推进] 在单个 write_transaction 内原子提交，
崩溃/暂停恢复均以 checkpoint 剩余队列为权威，天然幂等。

判定为 red 的 superseded 与 04a 文档的差异已在本文档化，其余歧义遵循批次2指令。
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from src.core.storage.sqlite_db import get_db_connection, write_transaction
from src.core.update.channels import ADAPTER_CLASSES, ChannelAdapter, ChannelResult
from src.core.update.channels.routing import fallback_chain
from src.core.update.channels.base import (
    UPD_BATCH_ALREADY_RUNNING,
    UPD_BATCH_NOT_FOUND,
    UPD_CAPTCHA_BLOCKED,
    UPD_ILLEGAL_BATCH_STATUS,
    CHANGE_TYPES,
    LEGAL_STATUSES,
    UpdateError,
    upd_log,
)

# ---------------------------------------------------------------- 编排常量
#: 单号探测尝试预算（含首次；INS-A-05「按重试=3 次后记 failed」）
MAX_ATTEMPTS = 3
#: 巡检并发（pipeline/06 §3 inspect.concurrency=2）
CONCURRENCY = 2
#: 万级全库滚动日预算默认值（35k ÷ 500 ≈ 70 天一轮）
DEFAULT_DAILY_BUDGET = 500

_TIER0_SQL = """
SELECT d.doc_id AS doc_id, d.standard_no AS standard_no,
       d.standard_name AS standard_name
FROM doc_meta d
WHERE d.doc_type = 'standard'
  AND (d.doc_id IN (SELECT doc_id FROM watch_list)
   OR d.doc_id IN (SELECT doc_id FROM user_doc_bookmark)
   OR NOT EXISTS (SELECT 1 FROM update_change_event e WHERE e.doc_id = d.doc_id))
"""
_TIER1_SQL = """
SELECT d.doc_id AS doc_id, d.standard_no AS standard_no,
       d.standard_name AS standard_name
FROM doc_meta d
WHERE d.doc_type = 'standard'
  AND d.doc_id NOT IN (SELECT doc_id FROM watch_list)
  AND d.doc_id NOT IN (SELECT doc_id FROM user_doc_bookmark)
  AND EXISTS (SELECT 1 FROM update_change_event e WHERE e.doc_id = d.doc_id)
"""


# ================================================================ app_config 工具
def get_config(key: str, default: str | None = None) -> str | None:
    """读 app_config 单值；缺键返回 default。"""
    conn = get_db_connection()
    row = conn.execute("SELECT config_value FROM app_config WHERE config_key=?",
                       (key,)).fetchone()
    return row["config_value"] if row is not None else default


def set_config(key: str, value: str) -> None:
    """upsert app_config 单值（短事务）。"""
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO app_config(config_key, config_value) VALUES(?,?)"
            " ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value,"
            " updated_at=datetime('now')", (key, value))


def _today() -> str:
    """本地日期串（预算按自然日滚动；测试可 monkeypatch）。"""
    return time.strftime("%Y-%m-%d")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- 日预算
def daily_budget_limit() -> int:
    """tier1 全库滚动日预算：app_config inspect.daily_full_sweep_budget 可覆盖。"""
    raw = get_config("inspect.daily_full_sweep_budget")
    try:
        return int(raw) if raw is not None else DEFAULT_DAILY_BUDGET
    except (TypeError, ValueError):
        return DEFAULT_DAILY_BUDGET


def budget_used_today() -> int:
    """今日已消耗额度（跨批次累计；日期翻转自动清零）。"""
    today = _today()
    if get_config("inspect.budget_date") != today:
        with write_transaction() as txn:
            txn.execute(
                "INSERT INTO app_config(config_key, config_value) VALUES('inspect.budget_date',?)"
                " ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value",
                (today,))
            txn.execute(
                "INSERT INTO app_config(config_key, config_value) VALUES('inspect.budget_used','0')"
                " ON CONFLICT(config_key) DO UPDATE SET config_value='0'")
        return 0
    try:
        return int(get_config("inspect.budget_used", "0") or 0)
    except (TypeError, ValueError):
        return 0


def budget_remaining() -> int:
    return max(0, daily_budget_limit() - budget_used_today())


def _consume_budget(txn, amount: int) -> None:
    """在既有写事务内累加今日消耗（调用方保证 tier1 才调用）。"""
    txn.execute(
        "INSERT INTO app_config(config_key, config_value) VALUES('inspect.budget_used',?)"
        " ON CONFLICT(config_key) DO UPDATE SET"
        " config_value=CAST(CAST(config_value AS INTEGER)+? AS TEXT)",
        (str(int(amount)), int(amount)))


# ================================================================ 数据访问
def _load_batch(batch_id: str) -> dict:
    """读 bulk_import_batch 控制面行；不存在或非 inspect 批次抛 UPD-2003。"""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM bulk_import_batch WHERE batch_id=?",
                       (batch_id,)).fetchone()
    if row is None:
        raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)
    d = dict(row)
    for key in ("total", "checked", "red_count", "yellow_count", "green_count",
                "gray_count"):
        d[key] = int(d.get(key) or 0)
    return d


def get_inspect_batch(batch_id: str) -> dict | None:
    """读单个巡检控制面批次；不存在返回 None。"""
    try:
        return _load_batch(batch_id)
    except UpdateError:
        return None


def _load_checkpoint(batch: dict) -> dict:
    raw = batch.get("checkpoint_json")
    if not raw:
        return {}
    try:
        ckpt = json.loads(raw)
        return ckpt if isinstance(ckpt, dict) else {}
    except (TypeError, ValueError):
        return {}


def select_standard_nos(tier: str = "tier1") -> list[dict]:
    """按层取巡检清单：tier0=watch_list∪标准收藏(user_doc_bookmark)∪未首检∪已订阅领域；
    tier1=其余滚动（确定性排序）。"""
    if tier not in ("tier0", "tier1"):
        raise UpdateError(f"非法 tier: {tier}", code=UPD_ILLEGAL_BATCH_STATUS)
    sql = _TIER0_SQL if tier == "tier0" else _TIER1_SQL
    conn = get_db_connection()
    rows = conn.execute(sql + " ORDER BY standard_no").fetchall()
    result = [{"doc_id": r["doc_id"], "standard_no": r["standard_no"],
               "standard_name": r["standard_name"]} for r in rows]
    if tier == "tier0":
        # 领域订阅（F-13/A15）：已订阅领域的**标准**并入 tier0 高频层（未在 SQL 集合内的补入）。
        # 法规不进查号巡检（无国标号，时效走 law_source/update.py flk 溯源检查）
        from src.core.update.subscriptions import get_subscriptions
        subs = set(get_subscriptions())
        if subs:
            existing = {r["doc_id"] for r in result}
            for d in conn.execute(
                    "SELECT doc_id, standard_no, standard_name, doc_type, domain_tags"
                    " FROM doc_meta").fetchall():
                if d["doc_type"] != "standard":
                    continue
                try:
                    tags = json.loads(d["domain_tags"] or "[]")
                except (TypeError, ValueError):
                    tags = []
                if d["doc_id"] not in existing and any(
                        isinstance(t, str) and t in subs for t in tags):
                    result.append({"doc_id": d["doc_id"],
                                   "standard_no": d["standard_no"],
                                   "standard_name": d["standard_name"]})
            result.sort(key=lambda r: r["standard_no"])
    return result


# ---------------------------------------------------------------- 创建/状态迁移
def create_inspect_batch(tier: str = "tier1", trigger: str = "manual",
                         items: list[dict] | None = None) -> dict:
    """新建巡检批次：bulk_import_batch 控制面行 + update_check_batch 同值锚行。

    items 为 None 时立即按 tier 圈定清单并快照进 checkpoint（total=清单长度）；
    传入空清单表示空转批次（total=0，run 后直接 done）。
    """
    if tier not in ("tier0", "tier1"):
        raise UpdateError(f"非法 tier: {tier}", code=UPD_ILLEGAL_BATCH_STATUS)
    if trigger not in ("manual", "scheduled"):
        raise UpdateError(f"非法 trigger_type: {trigger}", code=UPD_ILLEGAL_BATCH_STATUS)
    if items is None:
        items = select_standard_nos(tier)
    batch_id = f"bul_{ULID()}"
    queue = [{"doc_id": it["doc_id"], "standard_no": it["standard_no"],
              "standard_name": it.get("standard_name", "")} for it in items]
    ckpt = {"queue": queue, "captcha_pending": [], "errors": [], "pause_reason": None}
    actor = "user" if trigger == "manual" else "system"
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO bulk_import_batch (batch_id, batch_kind, trigger_type,"
            " status, total, tier, checkpoint_json) VALUES (?,'inspect',?,'pending',?,?,?)",
            (batch_id, trigger, len(queue), tier, json.dumps(ckpt, ensure_ascii=False)))
        # 镜像锚行：update_change_event 外键落点（同值 batch_id，pipeline/03 §6）
        txn.execute(
            "INSERT INTO update_check_batch (batch_id, trigger_type, status, total)"
            " VALUES (?,?,'pending',?)", (batch_id, trigger, len(queue)))
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "update/batch_created", actor, "bulk_import_batch",
             batch_id,
             json.dumps({"trigger": trigger, "tier": tier, "total": len(queue)},
                        ensure_ascii=False)))
    upd_log(batch_id, "inspector", "INFO", "batch_created",
            trigger=trigger, tier=tier, total=len(queue))
    return _load_batch(batch_id)


def _transition_status(batch_id: str, status: str,
                       checkpoint: dict | None = None) -> None:
    """状态迁移双写（控制面 + 锚行）；done/failed 盖 finished_at，running 盖 started_at。"""
    if status not in ("pending", "running", "paused", "done", "failed"):
        raise UpdateError(f"非法批次状态: {status}", code=UPD_ILLEGAL_BATCH_STATUS)
    started = ", started_at=COALESCE(started_at, datetime('now'))" if status == "running" else ""
    finished = ", finished_at=datetime('now')" if status in ("done", "failed") else ""
    ckpt_sql = ""
    args: list[Any] = [status]
    if checkpoint is not None:
        ckpt_sql = ", checkpoint_json=?"
        args.append(json.dumps(checkpoint, ensure_ascii=False))
    args.append(batch_id)
    with write_transaction() as txn:
        cur = txn.execute(
            f"UPDATE bulk_import_batch SET status=?{ckpt_sql}{started}{finished}"
            f" WHERE batch_id=?", args)
        if cur.rowcount == 0:
            raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)
        txn.execute(
            f"UPDATE update_check_batch SET status=?{started}{finished}"
            f" WHERE batch_id=?", (status, batch_id))


# ================================================================ 探测与判定
@dataclass
class ProbeOutcome:
    """单号编排结论：judged（已判定）/ failed（预算耗尽）/ captcha（验证码挂起）。"""

    kind: str                      # judged | failed | captcha
    standard_no: str
    doc_id: str | None = None
    standard_name: str = ""
    change_type: str | None = None
    legal_status: str | None = None
    color: str | None = None       # green | yellow | red | gray
    source_channel: str | None = None
    latest_info: dict = field(default_factory=dict)
    evidence_url: str | None = None
    error_code: str | None = None
    error_msg: str | None = None
    attempts: int = 0


def judge_result(requested_no: str, result: ChannelResult) -> tuple[str, str]:
    """渠道结果 → (change_type, 色)。映射以批次2指令为准：

    现行/upcoming→no_change|green；新版→new_version|yellow；
    废止/替代→superseded|withdrawn→red；查无→not_found|gray。
    渠道层 change_type 缺失时由 legal_status 兜底推导（不猜测非法枚举）。
    """
    if not result.found:
        return ("not_found", "gray")
    status = result.legal_status
    ctype = result.change_type
    if status == "withdrawn":
        return (ctype if ctype in ("withdrawn", "superseded") else "withdrawn", "red")
    if status == "superseded":
        return (ctype if ctype in ("superseded", "withdrawn") else "superseded", "red")
    if ctype in ("new_version",):
        return ("new_version", "yellow")
    if ctype in ("superseded", "withdrawn"):  # 状态缺失但渠道已给出废止/替代结论
        return (ctype, "red")
    # effective / upcoming / 有命中但无版本信息：按现行对待（INS-D-02 口径）
    return ("no_change", "green")


def _probe_number(adapters: dict[str, ChannelAdapter], item: dict,
                  ledger_rows: list[dict] | None = None) -> ProbeOutcome:
    """工作线程入口：单号走降级链，只触网不触 DB，异常归一为 Outcome。

    链按标准号特征由 `routing.select_chain` 生成（权威渠道前置，如 AQ→ndls、
    工程建标→ndls、团标→ttbz），其余泛查兜底；**再按台账硬过滤**——
    `enabled=0`（人工停用）与 `wiring='broken'`（已知失效）的渠道**不进链**
    （§11.0 R6h，`ledger_chain.chain_for_number`）。所以"台账里停用某条渠道"
    会**真的**停掉巡检对它的调用，而不只是让面板好看一点。

    `ledger_rows`：台账行（**由调用方一次读好传进来**，见 `run_batch`）——
    "这一号该问谁"按五类算（`question_router`），而算它需要台账的 `state`。
    把它做成参数而不是在这里查库，是为了**守住"本函数只触网"**这条既有纪律
    （§11.0 R6c-4c）。传 `None` 时仍能跑，只是不记五类（保持与旧调用兼容）。
    """
    no = item["standard_no"]
    # 链 = `routing.select_chain`（前缀权威前置 + 泛查兜底）**再按台账硬过滤**
    # （§11.0 R6c→R6h：`enabled=0` / `wiring='broken'` 的渠道不再被问）。
    # ⚠ 台账行是**调用方传进来的**，这里不读库 —— 本函数"只触网"的纪律不变；
    #   `ledger_rows=None` 时 `chain_for_number` 直接返回未过滤的链（fail-open，不 I/O）。
    from src.core.update.channels.ledger_chain import chain_for_number
    chain = chain_for_number(no, ledger_rows)
    # ⚠ **预算要够把链上的棒都问到，且"没问完"不许说成"查无此号"**（§11.0 R6c-3f，两轮复核逼出来）：
    #   回归史：① 原本 `attempts_left = MAX_ATTEMPTS`(3)，链变 4 根后**最后一棒永远探不到**
    #   （复核 b34 实测 [mee,official_gb,ndls]，govcn 消失）；② 我先改成
    #   `max(MAX_ATTEMPTS, len(可用链))`，只修了"池子比链短"；复核 b36 又实测出：
    #   这个池子仍是**全链共享**的 ⇒ 第 1 根抛 2 次异常就把预算吃掉，
    #   后两根从没被问过，**却照样返回 not_found/gray** ——把"没问"当成"没有"。
    #   ⇒ 两步一起做：
    #   (a) 预算 ≥ 可用链长（保证"没有异常时每根都问到"）；
    #   (b) 若预算被异常吃掉、**没能把每根都问到**，就不下 `not_found` 结论，改记 **failed**
    #       （"没问完"≠"查无此号"）。这一步同时**保住 INS-A-05 的冻结口径**：
    #       单根链上持续超时仍是"重试 3 次 → failed"，且**不降级**（异常不换棒——
    #       换棒会拿更弱的棒给出结论，那是更坏的错）。
    usable = [c for c in chain if adapters.get(c) is not None]
    budget = max(MAX_ATTEMPTS, len(usable))
    attempts_left = budget
    last_code: str | None = None
    last_msg: str | None = None
    used = 0
    miss_channel: str | None = None  # 最后一个给出干净未命中应答的渠道
    tried: list[str] = []            # 真的被问过的棒（按链序）
    for channel in chain:
        adapter = adapters.get(channel)
        if adapter is None:
            continue
        if attempts_left <= 0:
            break                    # 预算耗尽 ⇒ 后面的棒**没被问过**（下面据此不下 not_found）
        tried.append(channel)
        progressed_miss = False
        while attempts_left > 0 and not progressed_miss:
            attempts_left -= 1
            used += 1
            try:
                result = adapter.probe(no, item.get("standard_name", ""))
            except UpdateError as exc:
                last_code, last_msg = exc.code, str(exc)
                continue  # 同渠道重试，直至预算耗尽（**不换棒**：见上面的 INS-A-05 口径）
            except Exception as exc:  # noqa: BLE001 — 渠道意外异常归一，不让线程池炸
                last_code, last_msg = "UPD-1004", f"{type(exc).__name__}: {exc}"
                continue
            if result.captcha:
                return ProbeOutcome(kind="captcha", standard_no=no,
                                    doc_id=item.get("doc_id"),
                                    standard_name=item.get("standard_name", ""),
                                    source_channel=channel, attempts=used)
            if result.found:
                ctype, color = judge_result(no, result)
                info = {"version": result.latest_version,
                        "effective_date": result.effective_date,
                        # §11.0 R6c-3e：两个日期分开记。以前只记 effective_date，
                        # 而"发布"这一类（五类之首）因此没有数据来源。
                        "published_date": result.published_date,
                        # §11.0 R6c-7：废止日期也落事件（第三个日期槽）。
                        # 只有渠道真解析出来才有值（`ndls` a206 / `hbba`·`dbba` fzDate）；
                        # 没有就是"不知道"——**别拿 effective_date（实施日期）顶**。
                        "withdrawn_date": result.withdrawn_date}
                info = {k: v for k, v in info.items() if v is not None}
                # §11.0 R6c-4c：**五类结论**记进同一条事件的 latest_info
                # （不新增列、不写 ×5 条事件：理由见 channels/class_outcomes.py 与设计稿 §3.2.2）
                info.update(_classes_info(no, f"ch:{channel}", result, ledger_rows))
                return ProbeOutcome(
                    kind="judged", standard_no=no, doc_id=item.get("doc_id"),
                    standard_name=item.get("standard_name", ""),
                    change_type=ctype, legal_status=result.legal_status,
                    color=color, source_channel=channel, latest_info=info,
                    evidence_url=result.evidence_url, attempts=used)
            progressed_miss = True  # 干净未命中 → 降级下一渠道（不再烧本渠道预算）
            miss_channel = channel
    if miss_channel is not None and len(tried) == len(usable):
        # **每一根可用棒都问过了**，且至少一根给出确定性「查无」应答 → not_found/gray（INS-D-05）。
        return ProbeOutcome(kind="judged", standard_no=no, doc_id=item.get("doc_id"),
                            standard_name=item.get("standard_name", ""),
                            change_type="not_found", legal_status=None,
                            color="gray", source_channel=miss_channel, attempts=used,
                            # 灰号也要能说清"五类各自为什么没答"（§11.0 R6c-4c）
                            latest_info=_classes_info_for_miss(no, ledger_rows))
    # 到这里有两种情况，都是"没问完"：
    #   ① 预算被异常吃掉，后面的棒**从没被问过**（哪怕前面的棒给了"查无"）；
    #   ② 全程异常、没有任何一根给出确定性应答（INS-A-05 的 hard-fail）。
    # 两者都**不许**记成 not_found —— 那等于告诉业主"权威源说没有这个号"，而我们其实没问完。
    return ProbeOutcome(kind="failed", standard_no=no, doc_id=item.get("doc_id"),
                        standard_name=item.get("standard_name", ""),
                        source_channel=_FALLBACK_CHAIN[-1],
                        error_code=last_code or "UPD-1005",
                        error_msg=(f"预算 {budget} 次耗尽，只问到 {len(tried)}/{len(usable)} 根渠道"
                                   f"（没问完就不下「查无此号」结论）"
                                   if miss_channel is not None
                                   else (last_msg or "all channels exhausted")),
                        attempts=used)
    if miss_channel is not None:
        # 至少一个渠道给出了确定性「查无」应答 → not_found/gray（INS-D-05），
        # 与「全程异常无应答」的 hard-fail（INS-A-05）严格区分。
        return ProbeOutcome(kind="judged", standard_no=no, doc_id=item.get("doc_id"),
                            standard_name=item.get("standard_name", ""),
                            change_type="not_found", legal_status=None,
                            color="gray", source_channel=miss_channel, attempts=used)
    return ProbeOutcome(kind="failed", standard_no=no, doc_id=item.get("doc_id"),
                        standard_name=item.get("standard_name", ""),
                        source_channel=_FALLBACK_CHAIN[-1], error_code=last_code or "UPD-1004",
                        error_msg=last_msg or "all channels exhausted", attempts=used)


def _classes_info(no: str, channel_id: str, result: ChannelResult,
                  ledger_rows: list[dict] | None) -> dict:
    """五类结论 → 要并进 `latest_info` 的那几个键（§11.0 R6c-4c）。

    ⚠ **这里不做任何 DB 访问**：台账行是调用方传进来的（见 `_probe_number` 的 docstring）。
    ⚠ 台账没传 ⇒ 返回 `{}`（旧调用路径行为不变，不记五类），**不是**记一份假的"全没答"。
    ⚠⚠ **归因用 `only_ok=False`（不看台账 state）**——这是复核 b37 的 C 项抓到的口径错：
    我第一版按默认 `only_ok=True` 算候选，于是**台账把应答渠道记成 down、而它其实真答了**时
    （探针的 state 与"这一批到底问了谁"是两回事），`channel_id` 就不在候选里，
    五类会被记成"没问/答不出来"，还列出一串**从没被问过的**棒；
    极端情况（三棒全被记 down 却有一根答了）会给出 `classes_unanswerable=五类全 all_down`
    而该号明明是 green。⇒ **"这一类答没答"只取决于能力与链，与台账今天的 state 无关**；
    state 是**选谁去探**时的轴，不该参与**归因**。
    """
    if ledger_rows is None:
        return {}
    from src.core.update.channels import class_outcomes
    from src.core.update.channels import question_router as qr
    report = qr.route_report(standard_no=no, rows=ledger_rows, only_ok=False)
    built = class_outcomes.build_classes(report, channel_id=channel_id, result=result)
    out = {"classes": built["classes"]}
    if built["unanswered"]:
        out["classes_unanswered"] = built["unanswered"]
    if built["unanswerable"]:
        out["classes_unanswerable"] = built["unanswerable"]
    return out


def _classes_info_for_miss(no: str, ledger_rows: list[dict] | None) -> dict:
    """整链都没命中（灰号）时的五类记录：说清"每一类为什么没答"（§11.0 R6c-4c）。

    同样用 `only_ok=False`（见上一条的 ⚠⚠）：灰号该记的是"**链上有没有棒能答**"，
    不是"今天台账说哪几根活着"——后者会把"没问"写成"答不出来"。
    """
    if ledger_rows is None:
        return {}
    from src.core.update.channels import class_outcomes
    from src.core.update.channels import question_router as qr
    built = class_outcomes.build_classes_for_miss(
        qr.route_report(standard_no=no, rows=ledger_rows, only_ok=False))
    out = {"classes": built["classes"]}
    if built["unanswerable"]:
        out["classes_unanswerable"] = built["unanswerable"]
    return out


def _build_adapters(transport=None) -> dict[str, ChannelAdapter]:
    """构造全部渠道适配器（含 2026-08 新增的权威渠道）；transport 注入点即离线 mock 机制。

    任一渠道 import 失败（实现中）则跳过，不影响其余渠道运行。

    ⚠ **键必须用适配器自己的 `name`，不能用 `ADAPTER_CLASSES` 的键**（§11.0 R2 修）：
    `routing.select_chain()` 返回的是**适配器名**（如 `ttbz`），而注册表的键取自**文件名**
    （`ttzb`，见 `channels/__init__.py:53`）——两者在 `ttzb` 这一个渠道上不一致
    （`channels/ttzb.py:96` 写的是 `name = "ttbz"`）。原先按注册键建字典 ⇒ `_probe_number`
    按链里的名字查不到 ⇒ **团体标准一路永远走不到专用渠道，且现场只表现为"没搜到"**
    （那种"静默少一根渠道"最难查）。注册表键仍作缺省（类没声明 `name` 时）。
    """
    out: dict[str, ChannelAdapter] = {}
    for key, cls in ADAPTER_CLASSES.items():
        if cls is None:
            continue
        out[getattr(cls, "name", None) or key] = cls(transport=transport)
    return out


#: 泛查兜底链（official_gb→ndls→govcn）；权威渠道按标准号特征由 routing.select_chain 前置。
#: ⚠ 2026-09-18（§11.0 R5c）：**摘掉 web**（只解 mock dict、打的是 bing HTML ⇒ 恒 miss，
#:   且搜索引擎不是官方源）。_FALLBACK_CHAIN[-1] 用于「全都失败」时的归因 ⇒ 现在归到 govcn。
#: ⚠ 2026-09-18（§11.0 R6c-3b）：`ndls` 插到 `govcn` 前（量出来的：govcn 在标准号上 1/10、
#:   ndls 6/10）。这里只是注释跟随——链的顺序**唯一所有者仍是** `routing._FALLBACK`。
#: ⚠ 2026-09-18（§11.0 R6）：本常量**不再自己写字面量**，改为向唯一所有者
#:   `routing.fallback_chain()` 取（同一个 tuple 对象）——R5c 那次"摘一棒要改两处"的教训。
_FALLBACK_CHAIN: tuple[str, ...] = fallback_chain()


# ================================================================ 原子提交
def _commit_outcome(batch_id: str, tier: str, out: ProbeOutcome) -> None:
    """单号原子提交：事件（防重）+ 四色计数 + 断点推进 + 预算消耗，一事务完成。

    - judged 且跨批防重命中（同 doc 同 change_type 已存在）→ 只计数不重复建 chg_ 行；
    - failed → 不入四色不入事件表，仅审计 event_log('update/probe_failed') 并记账；
    - 断点权威 = bulk_import_batch.checkpoint_json.queue 弹出队头。
    """
    with write_transaction() as txn:
        if txn.execute("SELECT 1 FROM bulk_import_batch WHERE batch_id=?",
                       (batch_id,)).fetchone() is None:
            raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)

        color_cols = {"green": "green_count", "yellow": "yellow_count",
                      "red": "red_count", "gray": "gray_count"}
        delta = {col: 0 for col in color_cols.values()}
        if out.kind == "judged" and out.color in color_cols:
            delta[color_cols[out.color]] = 1
            skipped = txn.execute(
                "SELECT 1 FROM update_change_event WHERE IFNULL(doc_id,'')=?"
                " AND standard_no=? AND change_type=? LIMIT 1",
                (out.doc_id or "", out.standard_no, out.change_type)).fetchone()
            if skipped is None:
                change_id = f"chg_{ULID()}"
                txn.execute(
                    """INSERT INTO update_change_event
                       (change_id, batch_id, doc_id, standard_no, standard_name,
                        change_type, current_legal_status, latest_info_json,
                        source_channel, evidence_url, user_ack)
                       VALUES (?,?,?,?,?,?,?,?,?,?,0)""",
                    (change_id, batch_id, out.doc_id, out.standard_no,
                     out.standard_name or None, out.change_type, out.legal_status,
                     json.dumps(out.latest_info, ensure_ascii=False),
                     out.source_channel, out.evidence_url))
                txn.execute(
                    "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                    " target_id, after_state, metadata) VALUES (?,?,?,?,?,?,?)",
                    (str(ULID()), "update/change_detected", "system",
                     "update_change_event", change_id,
                     json.dumps({"change_type": out.change_type,
                                 "legal_status": out.legal_status},
                                ensure_ascii=False),
                     json.dumps({"batch_id": batch_id,
                                 "standard_no": out.standard_no,
                                 "source_channel": out.source_channel},
                                ensure_ascii=False)))
            else:
                upd_log(batch_id, "inspector", "INFO", "change_dedup_skipped",
                        standard_no=out.standard_no, change_type=out.change_type)
        elif out.kind == "failed":
            txn.execute(
                "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                " target_id, metadata) VALUES (?,?,?,?,?,?)",
                (str(ULID()), "update/probe_failed", "system", "bulk_import_batch",
                 batch_id,
                 json.dumps({"standard_no": out.standard_no,
                             "code": out.error_code, "msg": out.error_msg,
                             "attempts": out.attempts}, ensure_ascii=False)))

        # 计数双写（控制面 + 锚行），checked 含 failed 号（已处理即计入）
        sets = ", ".join(f"{col}={col}+?" for col in delta)
        counts_args = list(delta.values())
        txn.execute(
            f"UPDATE update_check_batch SET checked=checked+1{(',' + sets) if delta else ''}"
            f", started_at=COALESCE(started_at, datetime('now')) WHERE batch_id=?",
            [*counts_args, batch_id])
        txn.execute(
            f"UPDATE bulk_import_batch SET checked=checked+1{(',' + sets) if delta else ''}"
            f", started_at=COALESCE(started_at, datetime('now')) WHERE batch_id=?",
            [*counts_args, batch_id])

        # 断点推进：弹出队头（queue 头部恒为下一个待查号）
        row = txn.execute("SELECT checkpoint_json FROM bulk_import_batch"
                          " WHERE batch_id=?", (batch_id,)).fetchone()
        try:
            ckpt = json.loads(row["checkpoint_json"]) if row and row["checkpoint_json"] else {}
        except (TypeError, ValueError):
            ckpt = {}
        queue = [q for q in (ckpt.get("queue") or [])
                 if q.get("standard_no") != out.standard_no]
        ckpt["queue"] = queue
        if tier == "tier1":
            _consume_budget(txn, 1)
        txn.execute("UPDATE bulk_import_batch SET checkpoint_json=? WHERE batch_id=?",
                    (json.dumps(ckpt, ensure_ascii=False), batch_id))


def _debt_from_events(batch_id: str) -> list[str]:
    """从**本批已落库的事件**里回收结构性欠账（§11.0 R6c-4e，复核 b39 的 B②）。

    为什么不能只靠内存那份累积清单：欠账原来是**只在内存里**累积、只在暂停/终态时
    随断点落盘的。而 `_commit_outcome` 是第 5 个写断点的地方，它只推进队列、**不带欠账**；
    于是"号已提交、进程被杀（status 留 running）、随后 `pause_batch`→`resume_batch`"
    这条**生产恢复**路径上，已提交的号**不再入队**、内存清单也没了 ⇒ 批次照报 done，
    欠账静默消失（`error_trail` 是同一形状的既有缺陷，本步只收五类这一侧的欠账）。

    事件行是**持久**的：`latest_info_json.classes_unanswerable` 就在里面
    ⇒ 终态裁决前从库回收一遍，恢复路径与首次跑就不再有差别。

    ⚠ 只认 `classes_unanswerable`（结构性：`no_capability`/`off_chain`），
    **不认** `classes_unanswered`（含 `not_probed`＝"这次没轮到问"，不是答不出来）。
    ⚠ 读库失败**不抛**：回收不到就退回原来的内存口径，但要出声（`classes_debt_unreadable`），
    免得"读不到"与"本来就没有欠账"不可区分。
    """
    try:
        rows = get_db_connection().execute(
            "SELECT standard_no, latest_info_json FROM update_change_event"
            " WHERE batch_id=?", (batch_id,)).fetchall()
    except Exception as exc:  # noqa: BLE001 — 回收失败不该让批次炸
        upd_log(batch_id, "inspector", "WARN", "classes_debt_unreadable",
                note=f"从事件行回收五类欠账失败（终态退回内存清单口径）："
                     f"{type(exc).__name__}: {exc}")
        return []
    out: list[str] = []
    for r in rows:
        try:
            info = json.loads(r["latest_info_json"] or "{}")
        except (TypeError, ValueError):
            continue
        no = r["standard_no"]
        for cls in (info.get("classes_unanswerable") or []):
            out.append(f"{no}:{cls}")
    return sorted(set(out))


def _write_captcha_wait(batch_id: str, numbers: list[str]) -> None:
    """验证码聚合告警：一次暂停只落一条 update/captcha_wait（UPD-1002，不逐号刷屏）。"""
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, metadata) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "update/captcha_wait", "system", "bulk_import_batch",
             batch_id,
             json.dumps({"code": "UPD-1002", "standard_nos": numbers,
                         "message": "请过验证码后继续"}, ensure_ascii=False)))


# ================================================================ 运行句柄（暂停协调）
class _RunHandle:
    def __init__(self, batch_id: str):
        self.batch_id = batch_id
        self.pause_event = threading.Event()
        self.done = threading.Event()


_RUNS: dict[str, _RunHandle] = {}
_RUNS_LOCK = threading.Lock()


def request_pause(batch_id: str) -> bool:
    """非阻塞暂停请求（可在任意线程调用，含渠道 mock 回调）：置位即返。"""
    with _RUNS_LOCK:
        handle = _RUNS.get(batch_id)
    if handle is None:
        return False
    handle.pause_event.set()
    return True


def pause_batch(batch_id: str) -> dict:
    """暂停批次：运行中 → 块边界落断点后转 paused（阻塞至生效）；
    pending → 直接置 paused；paused 幂等返回同状态；终态批次原样返回（拒绝重启）。"""
    batch = _load_batch(batch_id)
    if batch["status"] == "running":
        with _RUNS_LOCK:
            handle = _RUNS.get(batch_id)
        if handle is not None:
            handle.pause_event.set()
            deadline = time.monotonic() + 30.0
            while not handle.done.is_set() and time.monotonic() < deadline:
                time.sleep(0.01)
            return _load_batch(batch_id)
        # running 但句柄丢失（进程重启残留）：直接标记 paused 保状态机闭合
        _transition_status(batch_id, "paused",
                           _merged_checkpoint(batch, pause_reason="user"))
        return _load_batch(batch_id)
    if batch["status"] == "pending":
        _transition_status(batch_id, "paused",
                           _merged_checkpoint(batch, pause_reason="user"))
        upd_log(batch_id, "inspector", "INFO", "batch_paused", where="pending")
        return _load_batch(batch_id)
    # paused / done / failed：幂等返回当前状态（INS-C-05 / INS-A-09）
    return batch


def _merged_checkpoint(batch: dict, *, pause_reason: str,
                       queue_head: list[dict] | None = None) -> dict:
    ckpt = _load_checkpoint(batch)
    if queue_head is not None:
        ckpt["queue"] = queue_head
    ckpt["pause_reason"] = pause_reason
    return ckpt


def resume_batch(batch_id: str, **run_kwargs: Any) -> dict:
    """恢复批次：仅 paused 可恢复（同步续跑到终态并返回摘要）。

    - 不存在 → UPD-2003（INS-A-06，404 语义）；
    - done/failed 终态 → UPD-3005 拒绝重启（INS-A-09）；
    - running/pending → 原样返回（resume 生效一次，扫描不重复执行，INS-C-05）。
    - ``run_kwargs`` 透传 run_batch（transport/max_workers 注入，离线测试与
      调度器自动恢复共用同一 mock 通道）。
    """
    batch = _load_batch(batch_id)  # 不存在在此抛 UPD-2003
    if batch["status"] in ("done", "failed"):
        raise UpdateError(f"批次已终态({batch['status']})，拒绝重启: {batch_id}",
                          code=UPD_ILLEGAL_BATCH_STATUS)
    if batch["status"] != "paused":
        return batch
    return run_batch(batch_id, **run_kwargs)  # run_batch 自身完成迁移，避免双写竞态


# ================================================================ 主流程
def run_batch(batch_id: str, transport=None, max_workers: int = CONCURRENCY) -> dict:
    """同步执行巡检批次至终态（done/paused），返回批次行。

    - pending/paused 可执行；done/failed 抛 UPD-3005（终态拒绝重启）；
      running 抛 UPD-2001（批次已在跑）。
    - 断点续扫：checkpoint.queue 为权威剩余队列；captcha 暂停时挂起号已置
      队列头并持久化，resume 原序续跑即优先补查（INS-C-02），全程不产生重复事件。
    - tier1 受日预算约束：额度归零即 paused(pause_reason='budget') 待次日。
    - max_workers 固定为 2（INS-A-02 峰值并发恒=2）；参数仅供测试注入。
    """
    batch = _load_batch(batch_id)
    if batch["status"] in ("done", "failed"):
        raise UpdateError(f"批次已终态({batch['status']})，拒绝重启: {batch_id}",
                          code=UPD_ILLEGAL_BATCH_STATUS)
    if batch["status"] == "running":
        raise UpdateError(f"批次正在运行: {batch_id}", code=UPD_BATCH_ALREADY_RUNNING)

    tier = batch.get("tier") or "tier1"
    ckpt = _load_checkpoint(batch)
    queue: list[dict] = list(ckpt.get("queue") or [])
    if not queue and batch["status"] == "pending":
        # 兼容手工建的裸批次：现圈清单并快照
        queue = select_standard_nos(tier)
        ckpt["queue"] = queue
    # 验证码暂停恢复：挂起号在暂停时已置于队列头（checkpoint 持久化顺序），
    # resume 原序续跑即天然「同号优先补查」，无需二次重排（INS-C-02）。
    if len(queue) != int(batch["total"]) and batch["status"] == "pending":
        with write_transaction() as txn:
            txn.execute("UPDATE bulk_import_batch SET total=?, checkpoint_json=?"
                        " WHERE batch_id=?",
                        (len(queue), json.dumps({**ckpt, "queue": queue},
                                                ensure_ascii=False), batch_id))
            txn.execute("UPDATE update_check_batch SET total=? WHERE batch_id=?",
                        (len(queue), batch_id))

    handle = _RunHandle(batch_id)
    with _RUNS_LOCK:
        _RUNS[batch_id] = handle
    adapters = _build_adapters(transport)
    # 台账行**一次读好**传给工作线程：`_probe_number` 要按五类算"这一号该问谁"，
    # 而它自己只触网不触 DB（§11.0 R6c-4c）。读失败不该让整批判失败 ⇒ 降级为 None，
    # 但**必须出声**：复核 b37 的 B 项指出"静默丢弃"——批次照报 done、四色照绿、
    # `latest_info` 只是**没有** `classes` 键，与"本来就不该记"完全不可区分。
    try:
        from src.core.storage import channel_repo as _cr
        ledger_rows: list[dict] | None = _cr.list_channels()
    except Exception as exc:  # noqa: BLE001
        ledger_rows = None
        upd_log(batch_id, "inspector", "WARN", "classes_ledger_unavailable",
                note=f"读台账失败 ⇒ 本批**不记五类结论**（latest_info 里不会有 classes 键）："
                     f"{type(exc).__name__}: {exc}")
    error_trail: list[dict] = [e for e in (ckpt.get("errors") or [])
                               if isinstance(e, dict)]
    # §11.0 R6c-4d：**"有结构性 `unanswerable` 的号不算 done"**（设计稿 §3.2.2 第 2 条）。
    # 与 `error_trail`（**未判定**号）**并列、不替代**：那些号是**判定了**、但五类里有
    # `no_capability`/`off_chain` 这种**结构性答不出来**（不是"没问"——`not_probed` 不算）。
    # 随断点持久化（否则 resume 会把之前那批的欠账丢掉）。
    unanswerable_nos: list[str] = [str(x) for x in (ckpt.get("unanswerable") or [])]
    # §11.0 R6c-4e：断点里没有、但**事件行里已经有**的欠账要收回来（复核 b39 的 B②：
    # "号已提交、进程被杀"那条恢复路径上，内存清单没了、已提交号也不再入队）。
    _recovered = [d for d in _debt_from_events(batch_id)
                  if d not in set(unanswerable_nos)]
    if _recovered:
        unanswerable_nos.extend(_recovered)
        upd_log(batch_id, "inspector", "INFO", "classes_debt_recovered",
                recovered=len(_recovered), sample=_recovered[:5])
    upd_log(batch_id, "inspector", "INFO", "batch_running",
            tier=tier, pending=len(queue))
    try:
        _transition_status(batch_id, "running")
        stop_reason: str | None = None
        with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as pool:
            while queue:
                if handle.pause_event.is_set():
                    stop_reason = "user"
                    break
                if tier == "tier1" and budget_remaining() <= 0:
                    stop_reason = "budget"
                    break
                take = max_workers
                if tier == "tier1":  # 万级预算：chunk 按剩余额度截断，杜绝超额
                    take = min(max_workers, budget_remaining())
                chunk, queue = queue[:take], queue[take:]
                futures: list[tuple[dict, Future]] = [
                    (item, pool.submit(_probe_number, adapters, item, ledger_rows))
                    for item in chunk]
                captcha_hits: list[ProbeOutcome] = []
                for item, fut in futures:  # 按清单序收敛，保证断点顺序确定
                    out: ProbeOutcome = fut.result()
                    if out.kind == "captcha":
                        captcha_hits.append(out)
                        continue
                    try:
                        _commit_outcome(batch_id, tier, out)
                        if out.kind == "failed":  # 失败记账单点在主循环（随终态落盘）
                            error_trail.append({"standard_no": out.standard_no,
                                                "code": out.error_code})
                        # §11.0 R6c-4d：这个号五类里有结构性答不出来的 ⇒ 记进"欠账"清单
                        for cls in (out.latest_info.get("classes_unanswerable") or []):
                            unanswerable_nos.append(f"{out.standard_no}:{cls}")
                    except Exception as exc:  # noqa: BLE001 — 单号提交异常隔离（INS-A-08）
                        # 提交失败该号不入账不入断点，留审计后继续，批次仍可达终态
                        error_trail.append({"standard_no": out.standard_no,
                                            "code": "UPD-5000",
                                            "msg": f"{type(exc).__name__}: {exc}"[:200]})
                        upd_log(batch_id, "inspector", "ERROR", "commit_failed",
                                standard_no=out.standard_no,
                                err=f"{type(exc).__name__}: {exc}"[:200])
                if captcha_hits:  # 验证码半自动熔断：聚合一条告警，整批暂停
                    stop_reason = "captcha"
                    hits = [{"doc_id": c.doc_id, "standard_no": c.standard_no,
                             "standard_name": c.standard_name} for c in captcha_hits]
                    queue = hits + queue  # 挂起号置队头，resume 后逐号优先补查
                    _write_captcha_wait(
                        batch_id, [c.standard_no for c in captcha_hits])
                    break
            if stop_reason == "captcha":
                _transition_status(batch_id, "paused",
                                   {"queue": queue, "captcha_pending": [],
                                    "errors": error_trail,
                                    "unanswerable": sorted(set(unanswerable_nos)),
                                    "pause_reason": "captcha"})
                upd_log(batch_id, "inspector", "WARN", "batch_paused_captcha")
            elif stop_reason == "budget":
                _transition_status(batch_id, "paused",
                                   {"queue": queue, "captcha_pending": [],
                                    "errors": error_trail,
                                    "unanswerable": sorted(set(unanswerable_nos)),
                                    "pause_reason": "budget"})
                upd_log(batch_id, "inspector", "INFO", "batch_paused_budget",
                        tier=tier)
            elif stop_reason == "user":
                _transition_status(batch_id, "paused",
                                   {"queue": queue, "captcha_pending": [],
                                    "errors": error_trail,
                                    "unanswerable": sorted(set(unanswerable_nos)),
                                    "pause_reason": "user"})
                upd_log(batch_id, "inspector", "INFO", "batch_paused", where="boundary")
            else:
                # 终态裁决（ANOM-001 回归·04a §0）：四色恒等式只对 done 批次承诺——
                # 凡存在未判定号（探测 failed / 提交隔离，均留痕 error_trail），
                # 一律终态 failed（finished_at 照盖、审计已在 event_log/checkpoint），
                # 绝不以 done 假报全绿。
                # §11.0 R6c-4d **附加条件（并列、不替代）**：五类里有**结构性答不出来**
                # （`no_capability`/`off_chain`）的号，同样**不算 done** ⇒ 也走 failed。
                # ⚠ 不把 `not_probed` 算进来：那是"这次没轮到问"，不是"答不出来"。
                if error_trail:
                    terminal = "failed"
                elif unanswerable_nos:
                    terminal = "failed"
                else:
                    terminal = "done"
                _transition_status(batch_id, terminal,
                                   {"queue": [], "captcha_pending": [],
                                    "errors": error_trail,
                                    "unanswerable": sorted(set(unanswerable_nos)),
                                    "pause_reason": None})
                if terminal == "done":
                    upd_log(batch_id, "inspector", "INFO", "batch_done")
                elif error_trail:
                    upd_log(batch_id, "inspector", "INFO",
                            "batch_failed_unjudged", unjudged=len(error_trail))
                else:
                    upd_log(batch_id, "inspector", "INFO",
                            "batch_failed_unanswerable",
                            unanswerable=len(set(unanswerable_nos)),
                            sample=sorted(set(unanswerable_nos))[:5])
    finally:
        handle.done.set()
        with _RUNS_LOCK:
            _RUNS.pop(batch_id, None)
    return _load_batch(batch_id)


# ================================================================ 审计辅助
def captcha_wait_events(limit: int = 20) -> list[dict]:
    """待人工过点的验证码告警（前端任务卡片数据源）。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT event_id, target_id, metadata, created_at FROM event_log"
        " WHERE event_type='update/captcha_wait'"
        " ORDER BY created_at DESC, event_id DESC LIMIT ?", (int(limit),)).fetchall()
    out = []
    for r in rows:
        try:
            meta = json.loads(r["metadata"] or "{}")
        except (TypeError, ValueError):
            meta = {}
        out.append({"event_id": r["event_id"], "batch_id": r["target_id"],
                    "standard_nos": meta.get("standard_nos", []),
                    "message": meta.get("message", ""), "created_at": r["created_at"]})
    return out
