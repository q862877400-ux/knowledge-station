"""台账驱动的降级链（§11.0 R6c，第一步**只算不改**）。

## 这一步要解决什么
今天巡检的兜底链是 `routing._FALLBACK` 里的**两个字面量**（`official_gb → govcn`）。
台账（`update_channel`）里每条渠道有 `enabled`（人工意图）、`wiring`（有没有接在链上）、
`state`（探针实测），但**链本身并不看台账**。R6c 的验收里写着"巡检降级链来自台账"。

## 第一版规则错在哪（**快照工具当场抓到的**，2026-09-18）
我最初写的是"台账里 `wiring='wired'` 且 `enabled=1` 的都进兜底链"。跑 `scripts/chain-snapshot.py`
立刻看到后果：**9/9 个样例号的链都变了**——因为 `wired` 里混着**前缀专用**渠道
（`dbba`/`hbba`/`mee`/`ndls`/`ttbz`），它们本该只在对应的号型上出现，却被拖进了泛查兜底链。
两个后果都是真问题：① 泛查链从 2 条变 7 条（每号最多 7 次请求，巡检预算与耗时都变）；
② 语义错位（`dbba` 只答 DB 地标号，拿它试 ISO 号是白跑）。
⇒ **"接在链上"（wired）与"是兜底成员"（roster）不是一回事**，台账今天**没有区分这两者的字段**。

## 因此本模块现在的规则（刻意保守）
- **成员名单（roster）来自显式参数**，缺省 = `routing.fallback_chain()`（就是今天那两棒）；
- **台账只做两件它能作准的事**：① **过滤**——`enabled=0`（人工停用）与 `wiring='broken'`
  （已知失效）**不进链**；② **报告**——把"台账里 wired 但不在 roster 里"的候选列出来，
  供下一步**显式**决定要不要提升为兜底成员（提升是行为改变，必须单独一步 + 快照差异）。
- **`state` 只报告不过滤**：探针判 `down` 的 13 条里至少有瞬时/WAF/我方 TLS 指纹三类
  （R3d、R6a 实测：`cfsa` 一翻转、4 条是 TLS 指纹问题）。按一次探针就把渠道踢出链，会让
  **链随探针抖动**，而"链变了"是巡检行为的改变——那需要更硬的证据（如连续 N 次 down）与单独的决策。

## ⚠ 循环问题（不写清就会做出一个"回声"）
台账的 `wiring` 是 R2 **反查 `routing` 得到**的 ⇒ 拿它当链的来源，链只能等于 routing 原来的链，
台账成了回声、不是所有者。所以本模块**不用 `wiring` 来决定"谁能进"**，只用它做两件不循环的事：
- `wiring='broken'` 是**人工/调研**写的"在链上但实测不工作"（R1 的 G6）⇒ 可以作过滤依据；
- `wiring='wired'` 只用来**找候选**（报告用），不用来直接改链。

## 现在的用法
只被 `scripts/chain-snapshot.py` 与用例使用：**算出"如果按台账，链会变成什么"**。
**巡检本身还没接**（接入是下一步，且要先看过快照差异）。
"""
from __future__ import annotations

from typing import Any

from src.core.storage import channel_repo as cr
from src.core.update.channels.routing import fallback_chain


def ledger_fallback_chain(rows: list[dict[str, Any]] | None = None, *,
                          roster: tuple[str, ...] | None = None,
                          known: set[str] | None = None) -> tuple[str, ...]:
    """按台账**过滤**兜底链（纯函数；`rows=None` 时才读库）。

    Args:
        rows: 台账行（`channel_repo.list_channels()` 的形状）；None ⇒ 读库。
        roster: 兜底成员名单与顺序；缺省 = `routing.fallback_chain()`（今天的两棒）。
            ⚠ **成员资格是显式数据**，不是"台账里 wiring=wired 的都算"——理由见模块 docstring。
        known: 代码里真实存在的渠道名（默认取 `ADAPTER_CLASSES` 的适配器名）；
            名单里有、代码里没有的名字**不会被静默丢掉**，而是由 `ledger_chain_report()` 报出来。
    """
    if rows is None:
        rows = cr.list_channels()
    by_id = {str(r.get("channel_id")): r for r in rows}
    names = roster if roster is not None else fallback_chain()
    _ = known if known is not None else _adapter_names()
    return tuple(name for name in names
                 if (row := by_id.get(_channel_id_of(name))) is None or not _is_excluded(row))


def ledger_chain_report(rows: list[dict[str, Any]] | None = None, *,
                        roster: tuple[str, ...] | None = None,
                        known: set[str] | None = None) -> dict[str, Any]:
    """给快照脚本用：链、被谁挡住、"可提升为兜底成员的候选"、以及代码/台账不一致。

    Returns:
        `{chain, excluded, roster_candidates, missing_in_code, wired_but_probe_down}`
    """
    if rows is None:
        rows = cr.list_channels()
    names = known if known is not None else _adapter_names()
    base = roster if roster is not None else fallback_chain()
    chain = ledger_fallback_chain(rows, roster=base, known=names)

    excluded = []
    for r in rows:
        why = _exclusion_reason(r)
        if why:
            excluded.append({"channel_id": r.get("channel_id"), "name": r.get("name"),
                             "wiring": r.get("wiring"), "enabled": r.get("enabled"),
                             "state": r.get("state"), "reason": why})

    # 台账说 wired、代码里也有这个适配器，但**不在兜底名单**里 —— 它们是"要不要提升"的候选，
    # 不是"已经生效的兜底成员"。提升是行为改变 ⇒ 必须单独一步（带快照差异）决定。
    roster_ids = {_channel_id_of(n) for n in base}
    candidates = []
    for r in rows:
        cid = str(r.get("channel_id"))
        if r.get("wiring") != "wired" or cid in roster_ids or _is_excluded(r):
            continue
        cands = _name_candidates(cid)
        if cands & names:
            candidates.append({"channel_id": cid, "name": r.get("name"),
                               "adapter": sorted(cands & names)[0],
                               "why": "台账 wired + 代码里有适配器，但不在兜底名单里"})

    missing = []
    for r in rows:
        if r.get("wiring") != "wired":
            continue
        cands = _name_candidates(str(r.get("channel_id")))
        if cands and not (cands & names):
            missing.append({"channel_id": r.get("channel_id"), "name": r.get("name"),
                            "why": f"台账 wiring=wired，但 ADAPTER_CLASSES 里没有 {sorted(cands)}"})

    dead = [{"channel_id": r.get("channel_id"), "name": r.get("name"), "state": r.get("state"),
             "last_error_code": r.get("last_error_code"),
             "consecutive_failures": r.get("consecutive_failures")}
            for r in rows if r.get("state") == "down" and r.get("wiring") == "wired"]
    return {"chain": list(chain), "excluded": excluded, "roster_candidates": candidates,
            "missing_in_code": missing, "wired_but_probe_down": dead}


def _adapter_names() -> set[str]:
    from src.core.update.channels import ADAPTER_CLASSES
    return {getattr(cls, "name", None) or key for key, cls in ADAPTER_CLASSES.items() if cls}


def _channel_id_of(name: str) -> str:
    return f"ch:{name}"


def _name_candidates(channel_id: str) -> set[str]:
    """`ch:ndls` ⇒ {ndls}；`seed:law-cn:xxx`/`tool:xxx` 这类没有适配器名 ⇒ 空集。"""
    if channel_id.startswith("ch:"):
        return {channel_id[3:]}
    return set()


def _is_excluded(row: dict[str, Any]) -> bool:
    return _exclusion_reason(row) is not None


def _exclusion_reason(row: dict[str, Any]) -> str | None:
    """进不了链的原因（**人工意图与已知失效是硬过滤**；探针 state 不在此列）。"""
    if row.get("enabled") == 0:
        return "人工停用（enabled=0）"
    if row.get("wiring") == "broken":
        return "台账标 known-broken（在链上但实测不工作）"
    return None
