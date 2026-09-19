"""台账驱动的降级链（§11.0 R6c，第一步**只算不改**）。

## 这一步要解决什么
今天巡检的兜底链是 `routing._FALLBACK` 里的**三个字面量**（`official_gb → ndls → govcn`；
`ndls` 于 2026-09-18 R6c-3b 插入，见 routing.py 里的实测理由）。
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
        known: 代码里真实存在的渠道名（默认取 `ADAPTER_CLASSES` 的适配器名）。
            ⚠ **代码里没有的名字一定不进链**（fail-closed）：链上挂一个没有适配器的名字，
            巡检走到它时只能失败——那是"配置错伪装成渠道故障"的又一例。
            被丢掉的名单成员**不会静默消失**：`ledger_chain_report()` 的 `roster_missing_in_code` 会点名。
            （独立复核 b29 抓到：这条承诺原先只写在 docstring 里、代码没实现，`known` 参数是死参数。）

    台账里**查不到**的成员**保留**（fail-open：没 seed 的库不该让巡检失去整条链）；
    要停用它请用 `enabled=0`（显式动作）。
    """
    if rows is None:
        rows = cr.list_channels()
    by_id = {str(r.get("channel_id")): r for r in rows}
    raw_roster = _as_tuple(roster if roster is not None else fallback_chain())
    names = _dedupe(raw_roster)
    in_code = known if known is not None else _adapter_names()
    return tuple(name for name in names
                 if name in in_code
                 and ((row := by_id.get(_channel_id_of(name))) is None or not _is_excluded(row)))


def chain_for_number(standard_no: str, rows: list[dict[str, Any]] | None = None, *,
                     known: set[str] | None = None) -> tuple[str, ...]:
    """某号**巡检实际会用**的链：`routing.select_chain(no)` 再按台账**硬过滤**。

    这是"台账可人工维护"真正落地的**那一半**：业主在台账里把某条渠道 `enabled=0`
    或标 `wiring='broken'`，巡检**就不再问它**——在此之前台账只是个观察面板，
    人工改动不影响巡检行为。

    ## ⚠ `rows=None` 时**不做任何 I/O**（返回未过滤的链）
    本函数被 `inspector._probe_number` 调用，而那个函数的既有纪律是「**只触网**」
    （台账行由 `run_batch` 一次读好传进来，见 `_probe_number` 的 docstring）。
    在这里顺手读库会让那条纪律名存实亡，并把 DB 故障变成热路径上的隐藏依赖。
    ⇒ **没有台账行 = 没有过滤**（fail-open），与 `ledger_fallback_chain` 对
    "台账里查不到该成员"的处理同一口径。

    ## 只做过滤，**不做提升**
    台账 `wiring='wired'` 但不在 `select_chain` 结果里的渠道（今天 4 条：
    `ttbz`/`dbba`/`mee`/`hbba` 在 GB/T 号上）**不会**因此进链——"提升为兜底成员"
    是行为改变（泛查链变长 = 每号更多请求），要单独一步决定。这里只做**减法**，不做加法。
    """
    from src.core.update.channels.routing import select_chain
    chain = select_chain(standard_no)
    if rows is None:
        return chain
    return ledger_fallback_chain(rows, roster=chain, known=known)


def ledger_chain_report(rows: list[dict[str, Any]] | None = None, *,
                        roster: tuple[str, ...] | None = None,
                        known: set[str] | None = None) -> dict[str, Any]:
    """给快照脚本用：链、被谁挡住、"可提升为兜底成员的候选"、以及代码/台账不一致。

    Returns:
        `{chain, excluded, roster_candidates, missing_in_code, roster_missing_in_code,
          roster_duplicates, roster_not_in_ledger, wired_but_probe_down}`
        （两个 `missing_*` 是两个方向：台账→代码、代码→台账）
    """
    if rows is None:
        rows = cr.list_channels()
    names_in_code = known if known is not None else _adapter_names()
    raw_roster = _as_tuple(roster if roster is not None else fallback_chain())
    deduped = _dedupe(raw_roster)
    by_id = {str(r.get("channel_id")): r for r in rows}
    chain = ledger_fallback_chain(rows, roster=deduped, known=names_in_code)

    excluded = []
    for r in rows:
        why = _exclusion_reason(r)
        if why:
            excluded.append({"channel_id": r.get("channel_id"), "name": r.get("name"),
                             "wiring": r.get("wiring"), "enabled": r.get("enabled"),
                             "state": r.get("state"), "reason": why})

    # 台账说 wired、代码里也有这个适配器，但**不在兜底名单**里 —— 它们是"要不要提升"的候选，
    # 不是"已经生效的兜底成员"。提升是行为改变 ⇒ 必须单独一步（带快照差异）决定。
    roster_ids = {_channel_id_of(n) for n in deduped}
    candidates = []
    for r in rows:
        cid = str(r.get("channel_id"))
        if _wiring(r) != "wired" or cid in roster_ids or _is_excluded(r):
            continue
        cands = _name_candidates(cid)
        if cands & names_in_code:
            candidates.append({"channel_id": cid, "name": r.get("name"),
                               "adapter": sorted(cands & names_in_code)[0],
                               "why": "台账 wired + 代码里有适配器，但不在兜底名单里"})

    missing = []
    for r in rows:
        if _wiring(r) != "wired":
            continue
        cands = _name_candidates(str(r.get("channel_id")))
        if cands and not (cands & names_in_code):
            missing.append({"channel_id": r.get("channel_id"), "name": r.get("name"),
                            "why": f"台账 wiring=wired，但 ADAPTER_CLASSES 里没有 {sorted(cands)}"})

    # 反方向：**名单里**有、代码里没有（独立复核 b29 抓到这条原先只在 docstring 里承诺过）。
    # fail-closed：它不进链；但必须点名，否则"配了个不存在的渠道"会表现为"这条链少了点什么"。
    roster_missing = [{"adapter": n, "why": "兜底名单里有、ADAPTER_CLASSES 里没有 ⇒ 没进链"}
                      for n in deduped if n not in names_in_code]
    # 名单里重复写（复核 b29-fix 的 a）：链已去重，但**不能静默**——重复意味着有人手滑。
    dups = sorted({n for n in raw_roster if list(raw_roster).count(n) > 1})
    # 名单成员在台账里**没有行**（复核 b29-fix 的 b）：按设计保留（fail-open），但要提一句，
    # 否则"这条兜底成员没有台账记录"就没人知道（它的 enabled/broken 也就无从过滤）。
    not_in_ledger = [{"adapter": n, "why": "兜底名单里有、台账里没有这一行 ⇒ 保留（fail-open），"
                                           "但其 enabled/known-broken 无从过滤"}
                     for n in deduped if _channel_id_of(n) not in by_id]

    dead = [{"channel_id": r.get("channel_id"), "name": r.get("name"), "state": r.get("state"),
             "last_error_code": r.get("last_error_code"),
             "consecutive_failures": r.get("consecutive_failures")}
            for r in rows if r.get("state") == "down" and _wiring(r) == "wired"]
    return {"chain": list(chain), "excluded": excluded, "roster_candidates": candidates,
            "missing_in_code": missing, "roster_missing_in_code": roster_missing,
            "roster_duplicates": dups, "roster_not_in_ledger": not_in_ledger,
            "wired_but_probe_down": dead}


def _as_tuple(roster: Any) -> tuple[str, ...]:
    """名单可以是任何可迭代（类型注解写 tuple，但**传生成器也照收**）。

    复核 b29-fix2 记的坑：生成器只能消费一次——`ledger_chain_report` 里要遍历它好几遍
    （去重、判缺失、判台账缺行），不先固化就会"前半段有、后半段空"，并把已在名单里的成员
    误报成"可提升候选"。所以入口处一律固化成 tuple。
    """
    return tuple(str(n) for n in roster)


def _dedupe(roster: tuple[str, ...]) -> tuple[str, ...]:
    """保序去重（重复成员由 `ledger_chain_report` 的 `roster_duplicates` 点名告警）。

    ⚠ 写成显式循环而不是 `if not (n in seen or seen.add(n))`——后者 **mypy 会报**
    `func-returns-value`（"add 只返回 None"），而用例是绿的：**用例全绿 ≠ 门禁全绿**。
    """
    seen: set[str] = set()
    out: list[str] = []
    for n in roster:
        if n in seen:
            continue
        seen.add(n)
        out.append(n)
    return tuple(out)


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


def _wiring(row: dict[str, Any]) -> str:
    """`wiring` 归一（去空白 + 小写）。

    ⚠ 为什么容忍形状（复核 b29-fix 的 c）：`rows` 参数接受任意 dict，而 `wiring='BROKEN'` /
    `'broken '` 这类**写法差异**会让"已知失效"的渠道**照旧留在链里**——那正是"配置写错伪装成
    渠道可用"。真库（SQLite 里由 seed 写入）不会出现，但函数是公开的、被脚本与用例调用，
    所以这里**按归一后的值判**，把这类写法差异收敛掉。
    """
    return str(row.get("wiring") or "").strip().lower()


def _enabled_off(row: dict[str, Any]) -> bool:
    """`enabled` 是否表示"人工停用"（容忍 `0` / `'0'` / `False`，但**不**把 `None` 当停用）。"""
    v = row.get("enabled")
    if isinstance(v, bool):
        return v is False
    if isinstance(v, (int, float)):
        return v == 0
    if isinstance(v, str):
        # ⚠ 与 `_wiring()` 同一口径：**先去空白再小写**。复核 b29-fix2 抓到 `'FALSE'` 过去
        #   不算停用（`'false'`/`'False'` 却算）——同一个函数里两种口径是最难查的那类不一致。
        return v.strip().lower() in {"0", "false", ""}
    return False


def _is_excluded(row: dict[str, Any]) -> bool:
    return _exclusion_reason(row) is not None


def _exclusion_reason(row: dict[str, Any]) -> str | None:
    """进不了链的原因（**人工意图与已知失效是硬过滤**；探针 state 不在此列）。"""
    if _enabled_off(row):
        return "人工停用（enabled=0）"
    if _wiring(row) == "broken":
        return "台账标 known-broken（在链上但实测不工作）"
    return None
