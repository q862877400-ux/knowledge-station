"""五类能力表（§11.0 R6c）：每条渠道能回答哪几类问题。

## 五类是什么（语义先钉死，别自己扩）
`发布`（什么时候发布的）/ `修订`（有没有新版、代替关系）/ `废止`（有没有废止日期或依据）/
`现行性`（**今天**的法律状态）/ `编号核验`（这个号是否存在于权威库、写法是否规范）。

## 数据从哪来（`channel_answers.json` 是**派生物**）
- 68 条来自 R1 调研的机器可读声明（`channel_seed.json` 的 `answers_json`）——标 `medium`：
  **调研期声明，本轮没有逐条复核**（要升 high 需要适配器代码级证据）；
- 1 条 + 44 条由 R6c-1 按调研文档/适配器代码逐条判（有 `basis`，可追回原处）；
- 18 条 `category='tool'` 按规则判"不参与五类"（代码仓库不是采集通路）。

## 两条口径（R6c-1 定的，写在这里免得后人重新吵）
1. **mock/fixture 才供数的字段不算能力**。反例：`discover.py` 的卡片契约里确实读
   `item["status"]`，但真实通路没有解析、只有离线 mock 会填 ⇒ 判 `answers: []`
   （R1 的 G6/G14 是同一条教训：看起来有字段 ≠ 真能拿到）。
2. **`answers: []` 有两种含义**：① 非状态渠道（聚合入口/原文下载/工具）；
   ② 页面取不到、能力**未证实**（403/404/JS 空壳）。分辨看 `basis` 与台账的 `state`——
   **别把 ② 读成"这条渠道没用"**，它只是"今天没证据说它能答"。

⚠ 本模块只**声明能力**，不回答"今天能不能用"——那是台账的 `state`（`channel_probe`）。
选渠道时两者都要看：`channels_for(cls, only_ok=True)` 就是"能答这一类 **且** 探针没判死"。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: 五类（顺序即展示顺序）
CLASSES: tuple[str, ...] = ("发布", "修订", "废止", "现行性", "编号核验")

#: 能力表路径
ANSWERS_PATH = Path(__file__).resolve().parent / "channel_answers.json"


def load_answers(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """读能力表；缺 `channels` → 抛 ValueError（不静默空跑）。"""
    p = path or ANSWERS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    table = data.get("channels")
    if not isinstance(table, dict):
        raise ValueError(f"五类能力表格式不对（缺 channels 对象）: {p}")
    return table


def answers_of(channel_id: str, table: dict[str, dict[str, Any]] | None = None) -> list[str]:
    """这条渠道能答哪几类；**没登记** ⇒ 空列表（"未登记" ≠ "不能答"，别反读）。"""
    entry = (table if table is not None else load_answers()).get(channel_id) or {}
    return list(entry.get("answers") or [])


def verdict_of(channel_id: str, cls: str,
               table: dict[str, dict[str, Any]] | None = None) -> str | None:
    """该渠道在该类上的**能力判定**：`"supported"` / `"partial"` / `None`（没有审计记录）。

    证据来自 b35 的逐条代码审计（写在各条的 `answers_detail` 里）。**读它的唯一入口就是这里**——
    别在别处直接翻 `answers_detail`（那会让"判定口径"有第二个所有者）。

    ⚠ 语义提醒：`supported` 只表示"这个渠道**能**给出这一类要的东西"，
    **不**表示它给的最全（例如 `official_gb` 对"废止"是 partial —— 只有状态串、没有废止日期）。
    `None`（113 条种子渠道没有审计）在**排序**里占**中间档**（复核 b38 的开放项②抓到我这里写反了）：
    排序键是 `supported=0 / None=1 / partial=2`，所以 `None` **既不会越过 supported，
    也不会被 partial 反超**（组内保持链序）。旧注释写的是"不参与排序"，与代码相反，已改。
    """
    entry = (table if table is not None else load_answers()).get(channel_id) or {}
    detail = entry.get("answers_detail") or {}
    v = (detail.get(cls) or {}).get("verdict")
    return str(v) if v else None


def channels_for(cls: str, *, table: dict[str, dict[str, Any]] | None = None,
                 rows: list[dict[str, Any]] | None = None,
                 only_ok: bool = False) -> list[str]:
    """能回答 `cls` 的渠道（按台账顺序）；`only_ok=True` 时再过滤掉探针判死的。

    Args:
        rows: 台账行；`only_ok=True` 且未传 ⇒ 读库。
    """
    if cls not in CLASSES:
        raise ValueError(f"不是五类之一：{cls!r}（只能是 {list(CLASSES)}）")
    tbl = table if table is not None else load_answers()
    ids = [cid for cid, entry in tbl.items() if cls in (entry.get("answers") or [])]
    if not only_ok:
        return ids
    if rows is None:
        from src.core.storage import channel_repo as cr
        rows = cr.list_channels()
    state = {str(r.get("channel_id")): r.get("state") for r in rows}
    return [cid for cid in ids if state.get(cid, "unknown") != "down"]


def coverage(table: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """给报告用的小结：每类多少条、每条能答几类、置信与来源分布。"""
    tbl = table if table is not None else load_answers()
    per_class = {c: sum(1 for e in tbl.values() if c in (e.get("answers") or [])) for c in CLASSES}
    dist: dict[int, int] = {}
    for e in tbl.values():
        n = len(e.get("answers") or [])
        dist[n] = dist.get(n, 0) + 1
    by_conf: dict[str, int] = {}
    by_src: dict[str, int] = {}
    for e in tbl.values():
        by_conf[str(e.get("confidence"))] = by_conf.get(str(e.get("confidence")), 0) + 1
        by_src[str(e.get("source"))] = by_src.get(str(e.get("source")), 0) + 1
    return {"total": len(tbl), "per_class": per_class,
            "answers_per_channel": dict(sorted(dist.items())),
            "by_confidence": by_conf, "by_source": by_src}
