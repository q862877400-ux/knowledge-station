"""覆盖单元（CoverageUnit）—— 覆盖销号表的计算核心。

对应 spec 004 的 FR-007 ~ FR-011，数据结构见 `data-model.md` 的 E4。

## 为什么需要它

用户要求「**所有省、所有市**」。但现有 681 个来源是「能采就采」攒出来的，
**不是按名单销号推进的** —— 从来没有一张表能回答：

- 333 个地级行政区，**覆盖了几个**？
- 云南 84 条，**还差多少**？
- 云南**还缺哪些渠道**？（只知道"数据少"没用，要知道"缺什么"才能补）

## 三条设计决定（research.md R4）

1. **绝对阈值 + 相对中位数并列**
   绝对缺口（「还差 2,916 条」）**可执行**；比值（「中位数 0.03 倍」）**可判断结构**。
   只给一个都不够：绝对阈值会被极端值带偏（天津 63 万），比值则不够直观。

2. **状态是算出来的，不是存下来的**
   `ok` / `thin` / `none` 每次都从当前数据算 ⇒ 不会出现「状态与实际不一致」。

3. **`uncovered_channels` 不许留空**
   若某地区确实已无未覆盖渠道，显式写「已穷尽」——
   否则无法区分「查完没有」和「没查」。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common import iter_records                                       # noqa: E402

DATA_DIR = HERE / "data"

#: 达标下限（**假设值**，spec 的 Assumptions 已标注需用户确认；做成参数可调）
DEFAULT_THRESHOLD_PROVINCE = 3000
DEFAULT_THRESHOLD_CITY = 500

STATUS_OK = "ok"
STATUS_THIN = "thin"
STATUS_NONE = "none"

#: 31 个省级行政区（不含港澳台 —— 它们的政务问答体系不同，单列）
PROVINCE_NAMES = [
    "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
    "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
    "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省",
    "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
]


class CoverageUnit:
    """一个行政区或机构。字段见 data-model.md E4。"""

    __slots__ = ("name", "level", "parent", "channels", "total_records",
                 "threshold", "gap", "ratio_to_median", "status",
                 "uncovered_channels")

    def __init__(self, name: str, level: str, *, parent: str = "",
                 threshold: int = 0):
        self.name = name
        self.level = level
        self.parent = parent
        self.channels: list[str] = []
        self.total_records = 0
        self.threshold = threshold
        self.gap = 0
        self.ratio_to_median = 0.0
        self.status = STATUS_NONE
        self.uncovered_channels: list[str] = []

    def recompute(self) -> None:
        """按当前数据算状态与缺口（**状态是算出来的，不是存下来的**）。"""
        self.gap = max(0, self.threshold - self.total_records)
        if not self.channels:
            self.status = STATUS_NONE
        elif self.total_records < self.threshold:
            self.status = STATUS_THIN
        else:
            self.status = STATUS_OK

    def to_dict(self) -> dict:
        return {
            "name": self.name, "level": self.level, "parent": self.parent,
            "channels": self.channels, "total_records": self.total_records,
            "threshold": self.threshold, "gap": self.gap,
            "ratio_to_median": self.ratio_to_median, "status": self.status,
            "uncovered_channels": self.uncovered_channels,
        }

    def __repr__(self) -> str:                                          # pragma: no cover
        return (f"CoverageUnit({self.name!r}, {self.level}, "
                f"{self.total_records} 条, {self.status})")


# ---------------------------------------------------------------- 数据统计

def count_by_source(*, scope_filter=None) -> dict:
    """统计每个来源的落盘条数。

    `scope_filter` 可选：一个函数 `rec -> bool`，用于**按口径过滤**
    （配合 GOAL.md 的「口径收窄」，分母可按新口径重算 —— FR 里要求支持）。
    """
    counts: dict[str, int] = {}
    for rec in iter_records(str(DATA_DIR / "*.jsonl")):
        if scope_filter is not None:
            try:
                if not scope_filter(rec):
                    continue
            except Exception:                                           # noqa: BLE001
                continue
        src = str(rec.get("source") or "")
        if src:
            counts[src] = counts.get(src, 0) + 1
    return counts


def build_units(channels, counts: dict, *, threshold_province: int,
                threshold_city: int) -> "list[CoverageUnit]":
    """把通道 + 条数聚合成覆盖单元。

    - 省级单元：31 个行政区（**每个都有行**，哪怕一条数据都没有）
    - 地级单元：从 `channel.region` 里出现过的市名（动态发现）
    - 其它层级（national / other）：单列，不混进省市统计
    """
    # 省级
    prov: dict[str, CoverageUnit] = {
        n: CoverageUnit(n, "province", threshold=threshold_province)
        for n in PROVINCE_NAMES
    }
    # 省级别名 → 标准名（channel.infer_region 产出的是「云南」这种简称）
    alias = {n.rstrip("省市自治区"): n for n in PROVINCE_NAMES}
    alias.update({n[:2]: n for n in PROVINCE_NAMES})

    city: dict[str, CoverageUnit] = {}
    other: dict[str, CoverageUnit] = {}

    for c in channels:
        n = counts.get(c.key, 0)
        region = (c.region or "").strip()
        if c.level == "province" and region:
            std = alias.get(region) or alias.get(region[:2]) or region
            u = prov.get(std)
            if u is None:
                u = prov.setdefault(std, CoverageUnit(std, "province",
                                                      threshold=threshold_province))
            u.channels.append(c.key)
            u.total_records += n
        elif c.level == "city" and region:
            u = city.setdefault(region, CoverageUnit(
                region, "city", threshold=threshold_city))
            u.channels.append(c.key)
            u.total_records += n
        else:
            key = c.level
            u = other.setdefault(key, CoverageUnit(key, "other", threshold=0))
            u.channels.append(c.key)
            u.total_records += n

    units = list(prov.values()) + list(city.values()) + list(other.values())
    for u in units:
        u.recompute()

    # 算相对中位数（**同级比同级**，R4）
    for lvl in ("province", "city"):
        group = [u for u in units if u.level == lvl and u.total_records > 0]
        if not group:
            continue
        vals = sorted(u.total_records for u in group)
        n = len(vals)
        # 真中位数：偶数个取中间两个的平均（不是「上中位数」）
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        for u in units:
            if u.level == lvl:
                u.ratio_to_median = round(u.total_records / med, 3) if med else 0.0
    return units


# ---------------------------------------------------------------- 未覆盖渠道

#: 「该地区应该有哪些渠道」的**期望清单**（按层级）。
#: 这是判断 `uncovered_channels` 的依据 —— 没有期望清单就无从谈「缺什么」。
EXPECTED_CHANNELS = {
    "province": [
        ("门户·政民互动", ("hdjl", "zmhd", "互动", "政民")),
        ("12345 热线", ("12345",)),
        ("省长信箱", ("szxx", "省长", "信箱")),
        ("人大·法规征求意见", ("rd-",)),
    ],
    "city": [
        ("市长信箱", ("szxx", "市长", "信箱")),
        ("12345 热线", ("12345",)),
    ],
}


def uncovered_for(unit: CoverageUnit, channels) -> "list[str]":
    """列出该单元**尚未建立来源的渠道**（FR-010）。

    ⚠ 若期望清单里的渠道**全部**已有来源 ⇒ 返回 `["已穷尽"]`，
    而不是空列表 —— 否则无法区分「查完没有」和「没查」。
    """
    if unit.level not in EXPECTED_CHANNELS:
        return ["（该层级无期望清单）"]
    owned = set(unit.channels)
    # 该单元下所有通道的 key（用于匹配）
    names = [c.key for c in channels if c.key in owned]
    missing = []
    for label, marks in EXPECTED_CHANNELS[unit.level]:
        if not any(any(m in n for m in marks) for n in names):
            missing.append(label)
    return missing if missing else ["已穷尽"]
