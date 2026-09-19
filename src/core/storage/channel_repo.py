"""渠道台账仓储（`update_channel`，§11.0 R2）。

## 这张表为什么必须存在（而不是继续写在代码/JSON 里）
巡检的"渠道"过去只活在两处：`update/channels/*` 的 13 个适配器（**用户看不见**，
也没有任何"它今天还活着吗"的记录）与 `announce.py` 的公告源 JSON（只有它能被人工维护）。
业主的诉求是把"渠道"变成**可见、可维护、可追责**的一等公民。详见
`docs/CHANNEL-COVERAGE-PLAN.md`。

## 三条纪律（照 R1 的实测教训写死）
1. **注册 ≠ 能力**：`wiring` 与 `verification` 是两个独立字段。
   R1 实证：13 个适配器只有 8 个在 `routing` 链上；而在链上的 `web`/`govcn` 两根兜底棒
   在真实 HTML 下**恒 miss**（只解 mock 的 dict）⇒ 它们 `wiring='broken'`。
2. **研究结论与运行健康度分开**：`verification`（研究期一次性实测，来自研究文档）
   ≠ `state`（运行期探针）。把两者混成一列，就会出现"半年前的实测当今天的状态"。
3. **种子导入不得覆盖运行期健康度**：`seed_channels()` 只写"描述性字段"，
   `state/last_*/consecutive_failures` 一律不动（见 `_DESCRIPTIVE`）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ulid import ULID

from src.core.storage.sqlite_db import get_db_connection, write_transaction

#: canonical 类别（面板筛选用；`category_raw` 保留调研原文，两者都要）
CATEGORIES: tuple[str, ...] = (
    "law",          # 法规：法律/行政法规/部门规章/地方性法规/地方政府规章/司法解释/规范性文件
    "std_gb",       # 国家标准
    "std_hb",       # 行业标准（含部委行业标准公告）
    "std_db",       # 地方标准
    "std_tb",       # 团体标准
    "std_intl",     # 国际/国外标准
    "aggregator",   # 聚合入口（跨门类/跨地区）
    "tool",         # 工具与 Skill（可抄思路，不是发布源）
    "internal",     # 我们自己的适配器与采集通路
    "other",
)

#: 调研文档里的原始类别写法 → canonical。**穷尽 R1 的 30 种写法**；
#: 未命中一律 `other`（并把原文留在 `category_raw`，绝不静默丢）。
_CATEGORY_MAP: dict[str, str] = {
    # 法规
    "法律": "law", "行政法规": "law", "部门规章": "law", "地方性法规": "law",
    "地方政府规章": "law", "司法解释": "law", "规范性文件": "law",
    "法律法规": "law", "法律法规（采集/核验，非 ChannelAdapter）": "internal",
    "政府公告": "law",
    # 标准
    "国家标准": "std_gb", "国标": "std_gb", "国家标准（全门类）": "std_gb",
    "行标": "std_hb", "行业标准": "std_hb", "部委行业标准公告": "std_hb",
    "部委行业标准（生态环境）": "std_hb",
    "地标": "std_db", "地方标准": "std_db",
    "团标": "std_tb", "团体标准": "std_tb",
    "国际": "std_intl",
    # 聚合/工具/内部
    "聚合入口": "aggregator", "跨门类标准状态权威": "aggregator",
    "工具项目": "tool",
    "用户配置公告源": "internal", "通用网页兜底": "internal",
    "分类号（非状态渠道）": "aggregator", "找标（非状态渠道）": "aggregator",
}

WIRING: tuple[str, ...] = ("wired", "unwired", "broken", "user", "seed_only")
VERIFICATION: tuple[str, ...] = ("verified", "unverified", "broken")
STATE: tuple[str, ...] = ("unknown", "ok", "suspicious", "down")

#: 种子可写的**描述性**字段；运行期健康度字段**不在其中**（导入不覆盖实测结果）
_DESCRIPTIVE = (
    "name", "category", "category_raw", "url", "fetch_kind", "list_endpoint",
    "params_json", "answers_json", "covers", "gaps", "wiring", "verification",
    "probe_url", "probe_expect", "source_file", "note",
    # §11.0 R7（2026-09-19）：**号段**——"这条渠道管哪些标准号"，JSON 数组。
    # 为什么要它：R6g 量出"有适配器的 13 条里只有 3 条在链上"，根因是**号段→渠道**这件事
    # 此前只硬编码在 `routing._PREFIX_ROUTE` 里（代码），台账无从表达 ⇒ 业主无法人工维护
    # "某个号段该问谁"，那 10 条适配器也就永远接不回来。有了这个字段，号段→渠道成为**台账
    # 里的事实**（可人工增删），链按它做**加法**（见 `update/channels/ledger_chain.py`）。
    "segments_json",
)

#: 种子文件（引擎自有；由 docs/research/channels/registry.seed.json 归一而来）
SEED_PATH = Path(__file__).resolve().parent.parent / "update" / "channel_seed.json"

#: 人工维护时**不许**经 HTTP 写入的字段（运行期健康度）。
#: 为什么要在这一层再挡一次：仓库层为了兼容种子导入而允许这些键（`overwrite_health` 控制），
#: 但"人工在面板上填一个 `last_ok_at`"是**凭空造证据** —— 面板走的路由必须显式拒绝，
#: 不能靠 `overwrite_health=False` 的**静默丢弃**（静默丢弃会让人以为写成功了）。
HEALTH_FIELDS: tuple[str, ...] = (
    "state", "last_try_at", "last_ok_at", "last_error", "last_error_code",
    "consecutive_failures", "latency_ms",
)


def _audit(txn, *, event_type: str, target_id: str, before: Any, after: Any,
           metadata: dict[str, Any] | None = None, actor: str = "user") -> None:
    """人工维护渠道的**留痕**，与改动写在**同一个事务**里（§11.0 R6d）。

    为什么放在仓储层而不是路由层：
    - 路由不是唯一入口（脚本、将来的 CLI、测试也会调仓储）——而"人工改了台账却没痕迹"
      在这个产品里不可接受：审查场景要能回答"**谁**在什么时候把这条渠道改成了什么"；
    - 同一个事务 ⇒ 要么改动与痕迹都在，要么都不在（不留"改了但没记"的窗口）。
    `before/after` 存整行/字段子集的 JSON 快照：删除渠道时 `after=None`，但**改动前那一行**留在
    `before_state` 里 ⇒ 删掉一条渠道也不会把它的历史证据抹掉。
    """
    txn.execute(
        "INSERT INTO event_log (event_id, event_type, actor, target_type, target_id,"
        " before_state, after_state, metadata) VALUES (?,?,?,?,?,?,?,?)",
        (str(ULID()), event_type, actor, "update_channel", target_id,
         None if before is None else json.dumps(before, ensure_ascii=False, default=str),
         None if after is None else json.dumps(after, ensure_ascii=False, default=str),
         json.dumps(metadata or {}, ensure_ascii=False)))


def normalize_category(raw: str | None) -> str:
    """原始类别写法 → canonical；未知 → `other`（原文由调用方存 `category_raw`）。"""
    return _CATEGORY_MAP.get((raw or "").strip(), "other")


def _json_or_none(value: Any) -> str | None:
    if value is None or value == "" or value == []:
        return None
    return json.dumps(value, ensure_ascii=False)


def check_segments(value: Any) -> list[str]:
    """校验并归一**号段**（`segments_json`）的人工输入；不合法 ⇒ `ValueError`（出声拒绝）。

    ## 只管**形状**，不管语义
    "这个号段写法能匹配哪些号"是 `update/channels/routing.py` 的事（它持有标准号的折叠口径），
    这里只保证：① 是字符串数组；② 每项非空；③ 保序去重。
    ⚠ 为什么要**出声拒绝**而不是"过滤掉坏项"：一个拼错的号段会**永不命中**，现场表现是
    "这条渠道明明在台账里、却总也不进链"——那正是"配置错伪装成渠道故障"。
    更狠的是它**静默**：所以形状错当场报错，而"写法合法但匹配不到任何号"由
    `ledger_chain_report()` 的 `segments_dead` 点名（后者需要真库的号，属于报告不属于校验）。
    """
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError("segments_json 必须是字符串数组（号段前缀，如 [\"HJ\", \"GB 50\"]）")
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"号段必须是**非空字符串**（收到 {item!r}）")
        seg = item.strip()
        if seg in seen:
            continue
        seen.add(seg)
        out.append(seg)
    return out


def parse_segments(row: dict[str, Any]) -> tuple[str, ...]:
    """库里的行 → 号段元组。**坏值返回空元组、绝不抛**（读路径不该因为一行脏数据炸巡检）。

    与 `check_segments` 的分工：写路径**拒绝**坏值（人能改），读路径**容错**（不能因为历史
    脏数据就把整条链弄没）。两者都保留"坏值不静默"的告警面 —— 由 `ledger_chain_report` 报。
    """
    raw = row.get("segments_json")
    if raw is None or raw == "":
        return ()
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        try:
            items = json.loads(str(raw))
        except (TypeError, ValueError):
            return ()
    if not isinstance(items, list):
        return ()
    return tuple(str(i).strip() for i in items if isinstance(i, str) and str(i).strip())


def upsert_channel(channel_id: str, payload: dict[str, Any], *,
                   overwrite_health: bool = False,
                   actor: str | None = None) -> dict[str, Any]:
    """插入或更新一条渠道。

    Args:
        channel_id: 稳定 id（`ch:<adapter>` / `seed:<源文件>:<序号>` / `user:<hash>`）。
        payload: 字段子集；只认识的键会被写入，未知键**抛 ValueError**（防拼错静默丢字段）。
        overwrite_health: 只有"人工在面板上改"或运行期探针才置 True；
            种子导入必须保持 False ⇒ 不覆盖 `state/last_*/consecutive_failures`。
        actor: 传了就给这次改动写一条 `event_log`（`channel/created` 或 `channel/updated`），
            写在**同一个事务**里；`None`（默认）= 不写痕迹（种子导入走这条）。
    """
    allowed = set(_DESCRIPTIVE) | {
        # `channel_id` 允许出现在 payload 里（种子条目自带它）——但**不作为列**写入，
        # 身份一律取自本函数的参数（否则两条路径能给出两个不同的 id）。
        "channel_id",
        "state", "enabled", "last_try_at", "last_ok_at", "last_error",
        "last_error_code", "consecutive_failures", "latency_ms",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"unknown_channel_field: {sorted(unknown)}")
    data = {k: v for k, v in payload.items() if k != "channel_id"}
    if not overwrite_health:
        for k in ("state", "last_try_at", "last_ok_at", "last_error",
                  "last_error_code", "consecutive_failures", "latency_ms"):
            data.pop(k, None)
    if "name" not in data and not _exists(channel_id):
        raise ValueError("channel_name_required")
    cat_raw = data.get("category_raw")
    if "segments_json" in data:
        # 形状校验在**写路径**上出声拒绝（理由见 `check_segments`）；存进去的是归一后的 JSON。
        data["segments_json"] = _json_or_none(check_segments(data["segments_json"]))
    if "category" in data and data["category"] not in CATEGORIES:
        raise ValueError(f"illegal_channel_category: {data['category']}")
    if cat_raw is not None and "category" not in data:
        data["category"] = normalize_category(str(cat_raw))
    # 新增行**必须**给出 category（列是 NOT NULL）：人工在面板上加一条渠道时往往说不出
    # "这属于哪一类"，那就落到 `other`——**别让它变成一个 sqlite3.IntegrityError**
    # （那在面板上只是 500，看不出所以然；而"没分类"本身是一个正常状态）。
    # 为什么默认值放在仓储层而不是路由层：schema 不变量归所有者，任何调用方都不该能绕过它。
    if "category" not in data and not _exists(channel_id):
        data["category"] = normalize_category(cat_raw)

    cols = list(data)
    with write_transaction() as txn:
        existed = _exists(channel_id, txn=txn)
        before = dict(txn.execute("SELECT * FROM update_channel WHERE channel_id=?",
                                  (channel_id,)).fetchone() or {}) if existed else None
        if not existed:
            cols = ["channel_id", *cols]
            data = {"channel_id": channel_id, **data}
            sql = (f"INSERT INTO update_channel({', '.join(cols)}) "
                   f"VALUES ({', '.join('?' * len(cols))})")
        else:
            sql = (f"UPDATE update_channel SET {', '.join(f'{c}=?' for c in cols)},"
                   f" updated_at=datetime('now') WHERE channel_id=?")
        txn.execute(sql, [data[c] for c in cols] + ([] if sql.startswith("INSERT") else [channel_id]))
        if actor is not None:  # MUTATION-CHECK 结束：恢复真留痕
            _audit(txn,
                   event_type="channel/created" if not existed else "channel/updated",
                   target_id=channel_id, before=before,
                   after={k: data[k] for k in data if k != "channel_id"},
                   metadata={"fields": sorted(data), "existed": existed}, actor=actor)
    return get_channel(channel_id) or {}


def _exists(channel_id: str, txn=None) -> bool:
    conn = txn if txn is not None else get_db_connection()
    return conn.execute("SELECT 1 FROM update_channel WHERE channel_id=?",
                        (channel_id,)).fetchone() is not None


def get_channel(channel_id: str) -> dict[str, Any] | None:
    row = get_db_connection().execute(
        "SELECT * FROM update_channel WHERE channel_id=?", (channel_id,)).fetchone()
    return dict(row) if row else None


def list_channels(*, category: str | None = None, wiring: str | None = None,
                  state: str | None = None, verification: str | None = None,
                  enabled_only: bool = False) -> list[dict[str, Any]]:
    """按筛选条件列出渠道（面板表格的数据源）。按类别 + 名称排序，结果稳定。"""
    where, args = [], []
    for col, val in (("category", category), ("wiring", wiring),
                     ("state", state), ("verification", verification)):
        if val:
            where.append(f"{col}=?")
            args.append(val)
    if enabled_only:
        where.append("enabled=1")
    sql = "SELECT * FROM update_channel"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY category, name"
    return [dict(r) for r in get_db_connection().execute(sql, args).fetchall()]


def record_probe(channel_id: str, *, state: str, latency_ms: int | None = None,
                 error: str | None = None, error_code: str | None = None) -> dict[str, Any]:
    """运行期探针结果落库（R3 调用）。

    语义（三态 + 计数）：
    - `ok`：`last_ok_at` 前进、`consecutive_failures` 清零；
    - `down` / `suspicious`：计数 +1、记 `last_error`（**suspicious 也是失败**：
      "200 但没抓到预期内容"不能算成功——R1 的 G14）；
    - `unknown`：只更新 `last_try_at`（探针没给出结论，不许当成成功或失败）。
    """
    if state not in STATE:
        raise ValueError(f"illegal_channel_state: {state}")
    is_ok = state == "ok"
    is_fail = state in ("down", "suspicious")
    with write_transaction() as txn:
        if not _exists(channel_id, txn=txn):
            raise ValueError(f"channel_not_found: {channel_id}")
        txn.execute(
            # ⚠ `last_try_at` **任何状态都推进**（含 unknown）：它的语义是"我们试过一次"，
            #   与 `last_ok_at`（"成功过一次"）必须分开——面板上"上次成功查询"若被
            #   尝试时间顶替，就再也看不出这个渠道到底多久没成功了。
            "UPDATE update_channel SET state=?,"
            " last_try_at=datetime('now'),"
            " last_ok_at=CASE WHEN ? THEN datetime('now') ELSE last_ok_at END,"
            " latency_ms=COALESCE(?, latency_ms),"
            " last_error=?, last_error_code=?,"
            " consecutive_failures=CASE WHEN ? THEN 0"
            "   WHEN ? THEN consecutive_failures + 1 ELSE consecutive_failures END,"
            " updated_at=datetime('now') WHERE channel_id=?",
            (state, is_ok, latency_ms, error, error_code, is_ok, is_fail, channel_id))
    return get_channel(channel_id) or {}


def set_enabled(channel_id: str, enabled: bool, *, actor: str | None = None) -> dict[str, Any]:
    """人工启停一个渠道（停用的**不删**：历史健康度是要留的证据）。

    `actor` 传了 ⇒ 写一条 `channel/enabled` 痕迹（同一事务）。
    """
    with write_transaction() as txn:
        row = txn.execute("SELECT enabled FROM update_channel WHERE channel_id=?",
                          (channel_id,)).fetchone()
        if row is None:
            raise ValueError(f"channel_not_found: {channel_id}")
        cur = txn.execute(
            "UPDATE update_channel SET enabled=?, updated_at=datetime('now')"
            " WHERE channel_id=?", (1 if enabled else 0, channel_id))
        if cur.rowcount == 0:
            raise ValueError(f"channel_not_found: {channel_id}")
        if actor is not None:
            _audit(txn, event_type="channel/enabled", target_id=channel_id,
                   before={"enabled": int(row["enabled"] or 0)},
                   after={"enabled": 1 if enabled else 0}, actor=actor)
    return get_channel(channel_id) or {}


def delete_channel(channel_id: str, *, actor: str | None = None) -> bool:
    """删除一条渠道。`actor` 传了 ⇒ 写一条 `channel/deleted` 痕迹（**带改动前整行快照**）。

    为什么敢真删：痕迹里的 `before_state` 保留了删除前那一行（含 `state`/`last_*`），
    而"停用不删"（`set_enabled`）仍然是面板上的默认动作 —— 删除是**显式**的高风险动作。
    """
    with write_transaction() as txn:
        row = txn.execute("SELECT * FROM update_channel WHERE channel_id=?",
                          (channel_id,)).fetchone()
        if row is None:
            return False
        if actor is not None:
            _audit(txn, event_type="channel/deleted", target_id=channel_id,
                   before=dict(row), after=None, actor=actor)
        return txn.execute("DELETE FROM update_channel WHERE channel_id=?",
                           (channel_id,)).rowcount > 0


def summary() -> dict[str, Any]:
    """面板头部用的小结：**能力数**（wiring=wired）与**注册数**分开报。

    ⚠ 这是本模块最重要的一条口径：`total` 是"台账里有几条"，`wired` 才是"能干活几条"。
    R1 的教训（G5/G6）就是这两个数被混着看 ⇒ 覆盖率虚高。
    """
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) n FROM update_channel").fetchone()["n"]
    by = {c: conn.execute("SELECT COUNT(*) n FROM update_channel WHERE wiring=?",
                          (c,)).fetchone()["n"] for c in WIRING}
    states = {s: conn.execute("SELECT COUNT(*) n FROM update_channel WHERE state=?",
                              (s,)).fetchone()["n"] for s in STATE}
    return {"total": total, "by_wiring": by, "by_state": states,
            "enabled": conn.execute(
                "SELECT COUNT(*) n FROM update_channel WHERE enabled=1").fetchone()["n"]}


def load_seed(path: Path | None = None) -> list[dict[str, Any]]:
    """读渠道种子（引擎自有 JSON）。文件缺失 → 抛 FileNotFoundError（不静默空跑）。"""
    p = path or SEED_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    channels = data.get("channels") if isinstance(data, dict) else data
    if not isinstance(channels, list) or not channels:
        raise ValueError(f"渠道种子格式不对（需要非空 channels 数组）: {p}")
    return channels


def seed_channels(path: Path | None = None, *, overwrite_health: bool = False) -> dict[str, Any]:
    """把种子灌进台账（幂等；**默认不覆盖运行期健康度**）。返回 {inserted, updated, total}。"""
    channels = load_seed(path)
    inserted = updated = 0
    for item in channels:
        cid = str(item.get("channel_id") or "").strip()
        if not cid:
            raise ValueError("渠道种子里有条目缺 channel_id")
        existed = _exists(cid)
        upsert_channel(cid, item, overwrite_health=overwrite_health)
        inserted += 0 if existed else 1
        updated += 1 if existed else 0
    return {"inserted": inserted, "updated": updated, "total": len(channels)}
