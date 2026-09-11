# -*- coding: utf-8 -*-
"""法律/标准效力状态「到期翻转」决议（2026-08-27）。

用户需求：体检得知标准「即将实施(upcoming) + 实施日期(effective_from/a205)」后，
本地按实施日期到点自动把「尚未生效」翻成「现行(effective)」，不等下次巡检。

实现：**读取时惰性决议**（零写库、即时生效、无并发风险）——凡读取 legal_status 时
用 ``resolve_status`` 判定：upcoming 且 effective_from 日期已到 → 按 effective 返回；
effective 且 effective_from 未到 → 按 upcoming 返回（2026-08-29 补反向）；
否则原样返回。不改 doc_meta（schema 冻结、写队列纪律），展示/检索/导出一律实时正确。

日期判定：effective_from 为 ``YYYY-MM-DD``（cssn a205 / ndls a206 均此格式），
字符串字典序即日期序；非该格式 / 缺省 → 保持原状态（不猜测）。
"""
from __future__ import annotations

import re
from datetime import datetime

#: 严格实施日期格式（cssn a205 / ndls a206 均为 YYYY-MM-DD；其他格式不翻转）
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def resolve_status(legal_status: str | None,
                   effective_from: str | None) -> str | None:
    """到期/未到期双向惰性翻转（零写库、读取即正确）。

    - upcoming + 实施日期已到 → effective（2026-08-27 原规则）
    - effective + 实施日期未到 → upcoming（2026-08-29 补反向：入库从封面提取
      effective_from 后，GB 25596-2025 这类"已发布未实施"标准在 2027-03-16 前
      应显示"即将实施"，到点自动翻回"现行"——与原规则同一惰性决议哲学）
    - effective_from 非严格 ``YYYY-MM-DD``（或缺失）→ 不翻转（诚实保持原状态）
    """
    s = (effective_from or "").strip()
    if not _DATE_RE.match(s) or legal_status not in ("upcoming", "effective"):
        return legal_status
    today = datetime.now().strftime("%Y-%m-%d")
    reached = s <= today
    if legal_status == "upcoming":
        return "effective" if reached else legal_status
    return legal_status if reached else "upcoming"
