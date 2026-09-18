"""按问题选渠道（§11.0 R6c-3）：把"这一号该问谁"变成可调用的一层，**先只读**。

## 它和 `channel_answers.channels_for` 什么关系（同名，别混）
两个函数都叫 `channels_for`，但管的是**不同的两半**，故意分开：

| | `channel_answers.channels_for(cls, ...)` | `question_router.channels_for(classes, no, ...)` |
|---|---|---|
| 输入 | **一类** | **多类**（缺省=五类） |
| 回答 | "能力表里谁能答这一类" | "**这一号**该按什么顺序问谁" |
| 看链条 | 不看（不知道标准号） | 看（`routing.select_chain`） |
| 顺序 | 能力表登记顺序 | **链的顺序**（前缀专用渠道天然在前） |
| 缺省只滤死 | `only_ok=False`（只声明） | `only_ok=True`（要选就顺手滤死） |

本模块是**派生物**：能力（`channel_answers.json`）∩ 链（`routing`）——它自己**不**声明任何能力，
也**不**决定链长什么样（链的所有者是 `routing`，R6c-4 会把它换成台账驱动的链，
届时本模块靠 `chain=` 参数接住，选链逻辑不用改）。

## 规则（每条都有用例，见 `tests/test_question_router.py`）
1. 候选 = **能答这类**（能力表）∩ **在链上**（`chain` 或 `routing.select_chain(no)`）；
2. `only_ok=True` 再滤掉**探针判死**的（`state == "down"`）；
3. **顺序 = 链的顺序**（不是能力表登记顺序）；
4. 某类候选为空 ⇒ 调用方该写 `unanswerable`，**不是** `not_found`
   （`not_found` = 问了权威源、它说没有这个号；两者混起来会让业主以为"查过了"）；
5. `tool:` 类渠道**永不出现在候选里**——不是靠这里再加一道闸，而是它们的 `answers` 本来就是空的
   （规则 1 就排除了）；用例把这一点钉住，所以**表里要是哪天给 tool 填了能力，用例会先红**。

## 两个口径（沿用 R6c-1，别再吵）
- **`unknown` / 无探针的渠道不滤**：没有证据说它死了，滤掉等于**凭空缩链**（与台账的 ⚪ 口径一致）；
  只有 `state == "down"` 才滤。"今天能不能用"是台账的轴，"这条能不能答"是能力表的轴，两根轴分开记。
- **空候选有三种原因**，日志/证据里别写成同一个（`route_report` 把原因分开给）：
  `no_capability`（没有任何渠道声明能答这一类）/ `off_chain`（有渠道能答，但都不在这一号的链上）/
  `all_down`（在链上、能答，但今天全被判死）。三者**都是**"没答出来"，但只有前两种说明**结构性缺口**。
"""
from __future__ import annotations

from typing import Any, Iterable

from src.core.update import channel_answers as ca
from src.core.update.channels.routing import first_route, select_chain

#: 每类候选"为什么是空的"——词表封闭，日志/用例只许用这四个值
REASONS: tuple[str, ...] = ("ok", "no_capability", "off_chain", "all_down")


def _norm_classes(classes: Iterable[str] | None) -> list[str]:
    """归一类别入参：`None` = 五类全要；保序去重；不在词表内 ⇒ 抛。

    `classes="废止"` 这种写法会被逐字拆成 `'废'`/`'止'` 再报"不是五类之一"，
    排查时很费解，所以**先拦下来**并说清楚。**我自己先踩过这个坑**（把标准号写成了第一个位置参数）：
    所以提示里同时给出"单类怎么写"和"标准号该放哪儿"，别让下一个人再猜。
    """
    if classes is None:
        return list(ca.CLASSES)
    if isinstance(classes, str):
        raise TypeError(
            f"classes 要传类别列表，不是字符串：{classes!r}"
            f"（单类请写 [{classes!r}]；若这是标准号，请放第二个位置参数："
            f"channels_for([...], {classes!r})）"
        )
    out: list[str] = []
    for c in classes:
        if c not in ca.CLASSES:
            raise ValueError(f"不是五类之一：{c!r}（只能是 {list(ca.CLASSES)}）")
        if c not in out:
            out.append(c)
    return out


def _to_channel_id(name: Any) -> str:
    """台账渠道 id 归一：适配器名 `ndls` ⇒ `ch:ndls`；已带前缀的原样返回。

    链（`routing.select_chain`）给的是**适配器名**，台账/能力表用的是**渠道 id**，
    两边差一个 `ch:` 前缀。R6c-4 接台账驱动的链时，链会直接给 `ch:` 开头的 id
    （或 `seed:`/`tool:` 这样的其它前缀）——所以这里两种写法都收，
    免得"换链源"那天因为一个前缀把整条链判成不在链上（现场表现是**候选全空**，很难看出来）。
    """
    s = str(name or "").strip()
    if not s:
        return ""
    return s if ":" in s else f"ch:{s}"


def _chain_ids(standard_no: str, chain: Iterable[Any] | None) -> tuple[str, ...]:
    """这一号的链（已归一成渠道 id、保序去重）。

    `chain=None` ⇒ 用 `routing.select_chain(standard_no)`（今天的唯一所有者）；
    传入则用传入的（R6c-4 的台账驱动链从这条路进来，本模块不用改）。
    """
    raw = select_chain(standard_no) if chain is None else chain
    out: list[str] = []
    seen: set[str] = set()
    for name in raw:
        cid = _to_channel_id(name)
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return tuple(out)


def _states(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    """渠道 id → 探针 state；未传 rows ⇒ 读库（只有 `only_ok=True` 才需要）。"""
    if rows is None:
        from src.core.storage import channel_repo as cr
        rows = cr.list_channels()
    return {str(r.get("channel_id")): r.get("state") for r in rows}


def _order_by_ability(cands: list[str], cls: str,
                      table: dict[str, dict[str, Any]] | None,
                      keep_first: str | None = None) -> list[str]:
    """同一类里把**能力判定为 `partial`** 的排到后面（组内保持链序）。

    ⚠ **前缀专用渠道永远留在最前**（`keep_first`）：`mee` 对 HJ 号就是专门渠道，
    而它的「发布」被判 `partial`（它给的是实施日期）；若按判定全局排序，
    HJ 号的"发布"就会先去问 `official_gb`——**把专门渠道降级**，与路由设计相悖。
    ⇒ 规则是"**专门渠道先，其余按能力排**"，不是"一律按能力排"。

    为什么需要按能力排（§11.0 R6c-4c，**模拟过再启用**）：`废止` 类上 `official_gb` 只有状态串
    （b35 判 `partial`）、`ndls` 有废止日期（`supported`）；对 `GB/T` 这种**没有前缀专门渠道**的号，
    链序是 `official_gb` 在前 ⇒ 按类问会问到那根答不全的棒。
    ⚠ 这一步**曾经会把 `发布` 类改坏**（`official_gb` 判 supported 却产出实施日期）——
    那是**判定过期**造成的，不是排序本身错：R6c-3e 补了 `published_date` 并重评「发布」判定后，
    重新模拟只剩 `废止` 那一类会翻（12 号 ×5 类 = 60 格里 8 格），才启用的。
    后来者若改动判定表，**请先重跑 `var/tmp/r6c5-sim.py` 看会不会翻别的类**。
    """
    head = [keep_first] if keep_first and keep_first in cands else []
    rest = [c for c in cands if c not in head]
    return head + sorted(rest, key=lambda cid: 1 if ca.verdict_of(cid, cls, table) == "partial" else 0)


def channels_for(classes: Iterable[str] | None = None, standard_no: str = "", *,
                  rows: list[dict[str, Any]] | None = None,
                  only_ok: bool = True,
                  table: dict[str, dict[str, Any]] | None = None,
                  chain: Iterable[str] | None = None) -> dict[str, list[str]]:
    """五类 → 候选渠道（**按链的顺序**排）。`classes` 缺省 = 五类全要。

    Args:
        classes: 要问的类别；缺省 `None` = `channel_answers.CLASSES` 五类全要。
        standard_no: 标准号（决定链；空号 = 兜底链）。
        rows: 台账行；`only_ok=True` 且未传 ⇒ 读库。
        only_ok: `True`（缺省）滤掉探针判死（`state == "down"`）的渠道。
        table: 能力表（离线测可注入）。
        chain: 手工指定链（归一后仍按传入顺序）；缺省用 `routing.select_chain`。

    Returns:
        `{类别: [渠道 id, ...]}`——某类为空列表 = 这一类**没答出来**，
        调用方据此写 `unanswerable`（要写原因请用 `route_report`）。
    """
    cls_list = _norm_classes(classes)
    tbl = table if table is not None else ca.load_answers()
    chain_ids = _chain_ids(standard_no, chain)
    first = _to_channel_id(first_route(standard_no)) if chain is None else None
    state = _states(rows) if only_ok else {}
    result: dict[str, list[str]] = {}
    for cls in cls_list:
        cands: list[str] = []
        for cid in chain_ids:
            entry = tbl.get(cid) or {}
            if cls not in (entry.get("answers") or []):
                continue
            if only_ok and state.get(cid, "unknown") == "down":
                continue
            cands.append(cid)
        result[cls] = _order_by_ability(cands, cls, tbl, keep_first=first)
    return result


def route_report(classes: Iterable[str] | None = None, standard_no: str = "", *,
                 rows: list[dict[str, Any]] | None = None,
                 only_ok: bool = True,
                 table: dict[str, dict[str, Any]] | None = None,
                 chain: Iterable[str] | None = None) -> dict[str, dict[str, Any]]:
    """同 `channels_for`，但**每类多给一个原因**（空候选别写成同一个理由）。

    每类返回：
        `channels`: 可用候选（= `channels_for` 的结果）
        `declared`: 能力表里声明能答这一类的**全部**渠道（不管在不在链上/死没死）
        `on_chain`: `declared` ∩ 链
        `dropped_down`: `on_chain` 里今天被判死而滤掉的
        `reason`: `ok` / `no_capability` / `off_chain` / `all_down`（见模块 docstring）
        `unanswerable`: 候选是否为空（`reason != "ok"`）——调用方据此写 `unanswerable`
    """
    cls_list = _norm_classes(classes)
    tbl = table if table is not None else ca.load_answers()
    chain_ids = _chain_ids(standard_no, chain)
    first = _to_channel_id(first_route(standard_no)) if chain is None else None
    state = _states(rows) if only_ok else {}
    report: dict[str, dict[str, Any]] = {}
    for cls in cls_list:
        declared = [cid for cid, entry in tbl.items() if cls in (entry.get("answers") or [])]
        declared_set = set(declared)
        declared_on_chain = [cid for cid in chain_ids if cid in declared_set]
        dropped = [cid for cid in declared_on_chain
                   if only_ok and state.get(cid, "unknown") == "down"]
        dropped_set = set(dropped)
        alive = [cid for cid in declared_on_chain if cid not in dropped_set]
        alive = _order_by_ability(alive, cls, tbl, keep_first=first)
        if alive:
            reason = "ok"
        elif not declared:
            reason = "no_capability"
        elif not declared_on_chain:
            reason = "off_chain"
        else:
            reason = "all_down"
        report[cls] = {
            "channels": alive,
            "declared": declared,
            "on_chain": declared_on_chain,
            "dropped_down": dropped,
            "reason": reason,
            "unanswerable": reason != "ok",
        }
    return report


def unanswerable_classes(report: dict[str, dict[str, Any]]) -> list[str]:
    """`route_report` 里候选为空的类（调用方据此写 `unanswerable`，**别写 `not_found`**）。

    只给"哪几类"，原因在 `report[cls]["reason"]`——写证据时请把原因带上，
    `no_capability`/`off_chain`（结构性缺口）与 `all_down`（今天全挂）不是一回事。
    """
    return [cls for cls, item in report.items() if item.get("unanswerable")]
