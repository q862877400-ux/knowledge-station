"""领域订阅存取（FRB F-13/A15）：app_config 键 update.domain_subscriptions（JSON 数组）。

领域词表与入库自动标签同源（src/core/knowledge/auto_tag.py _DOMAIN_KEYWORDS）：
建筑/消防/安全/环保/化工/合同/数据/劳动/卫生。订阅语义：tier0 巡检纳入已订阅领域的标准。
"""
from __future__ import annotations

import json
from typing import Any

from src.core.storage.sqlite_db import get_db_connection

KEY = "update.domain_subscriptions"

#: 与 auto_tag 词表保持一致（单点同步：此处为唯一常量，auto_tag 引用该处避免漂移）
DOMAIN_VOCAB: tuple[str, ...] = (
    "建筑", "消防", "安全", "环保", "化工", "合同", "数据", "劳动", "卫生",
)


def get_subscriptions() -> list[str]:
    """读取订阅列表；缺省（无配置行）=全部领域开启；显式空列表=全部关闭（区分两种语义）。"""
    row = get_db_connection().execute(
        "SELECT config_value FROM app_config WHERE config_key=?", (KEY,)).fetchone()
    if not row:
        return list(DOMAIN_VOCAB)
    try:
        value = json.loads(row["config_value"])
    except (TypeError, ValueError):
        return list(DOMAIN_VOCAB)
    if not isinstance(value, list):
        return list(DOMAIN_VOCAB)
    return [t for t in value if isinstance(t, str) and t in DOMAIN_VOCAB]


def set_subscriptions(tags: list[str]) -> list[str]:
    """全量替换式保存（幂等）；非法 tag 抛 ValueError（由 API 层转 422）。"""
    bad = [t for t in tags if t not in DOMAIN_VOCAB]
    if bad:
        raise ValueError(f"illegal_domain_tag: {bad}")
    from src.core.storage.sqlite_db import write_transaction

    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO app_config(config_key, config_value, updated_at) VALUES(?,?,datetime('now')) "
            "ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, "
            "updated_at=datetime('now')",
            (KEY, json.dumps(sorted(set(tags)), ensure_ascii=False)))
    return sorted(set(tags))


def subscriptions_as_tags() -> set[str]:
    """tier0 组装用：订阅 tag 集合（inspector 读取路径，轻量）。"""
    return set(get_subscriptions())


