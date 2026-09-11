"""dbba适配器（2026-08 实测，巡检时效）。

地方标准信息服务平台（2026-08 实测）：POST https://dbba.sacinfo.org.cn/stdQueryList
→ JSON，结构与 hbba 完全同构（records 含 code/status/issueDate/actDate/fzDate/
reviseStdCodes/pk），仅域名不同；实现复用 ``hbba._SacinfoQueryAdapter``。

实测要点（2026-08）：
- DB11/T 3031-2022 实测：status="有更新版"（被 DB11/T 3031-2026 代替）→
  legal_status=superseded，change_type=superseded；reviseStdCodes=DB11/T 713-2010
  （该版自身所取代的更早版本号）。
- DB11/T 3049-2026 实测：status=现行，issueDate/actDate 为 epoch 毫秒（CST）。
- 证据链：详情页 https://dbba.sacinfo.org.cn/stdDetail/<pk>。

mock 应答契约（离线表驱动，同 hbba）：
``{"http":200,"body":{"total":N,"records":[{"code","status","issueDate",
"actDate","fzDate","pk"}]}}``。
"""
from __future__ import annotations

from src.core.update.channels.hbba import _SacinfoQueryAdapter


class DbbaAdapter(_SacinfoQueryAdapter):
    """dbba：地方标准信息服务平台（标准号级状态探测，同 hbba 结构）。"""

    name = "dbba"
    host = "dbba.sacinfo.org.cn"
