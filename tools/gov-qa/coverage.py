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
    """一个行政区或机构。字段见 data-model.md E4。

    ## ★ `total_records` vs `total_incl_cities`（2026-10-10 新增）

    实测发现**省级口径会误导人**：甘肃省级显示 0 条，但实际该省已有 4 个市级源
    共 9,659 条。原因：省级只统计 `level=province` 的通道。

    ⇒ 两个数都给：
    - `total_records`：**只算本级的通道**（原口径，回答「省级门户本身有多少」）
    - `total_incl_cities`：**含下属地级市**（回答「这个省总共有多少」）

    **薄弱省清单应该看后者** —— 否则会误判「甘肃没数据」。

    ## ★★ `data_records`（2026-10-10 第 7 轮新增）—— 修「通道口径」的漏计

    实测发现**通道口径会漏计一整片市**：

    | 市 | 通道口径 | 数据口径 | 真相 |
    |---|---|---|---|
    | 鞍山市 | **0 个通道 ⇒ 判 `none`** | 2,307 条 | 数据在 `ln-8890`（**辽宁省级** 12345 平台）里，带 `extra.city` |
    | 抚顺市 | 0 个通道 | 2,189 条 | 同上 |
    | 张掖市 | 2 个通道 | 6,708 条 | 市、省两级都有 |

    原因：`ln-8890` / 湖南统一平台 / 广东 hdjlpt 这类**省级或平台级通道**，
    记录里带 `extra.city`（IGI 有 PROVINCE/CITY/AREA 三级归属），
    **一个通道就覆盖了全省的市**。而 `build_units` 只按 `channel.region` 建市级单元
    ⇒ 辽宁 14 个市里 12 个有数据，却被报成「13 个缺来源」。

    ⇒ `data_records` = **按记录 `extra.city` 归属统计**的条数（与通道层级无关）。
    `recompute()` 的**状态判定用 `max(total_records, data_records)`**
    （`total_records` 保持「只算本级通道」的原义，不破坏既有报表与 `total_incl_cities` 汇总，
    避免与省级通道重复计数）。
    """

    __slots__ = ("name", "level", "parent", "channels", "total_records",
                 "total_incl_cities", "data_records", "threshold", "gap",
                 "ratio_to_median", "status", "uncovered_channels")

    def __init__(self, name: str, level: str, *, parent: str = "",
                 threshold: int = 0):
        self.name = name
        self.level = level
        self.parent = parent
        self.channels: list[str] = []
        self.total_records = 0
        self.total_incl_cities = 0
        self.data_records = 0
        self.threshold = threshold
        self.gap = 0
        self.ratio_to_median = 0.0
        self.status = STATUS_NONE
        self.uncovered_channels: list[str] = []

    def recompute(self) -> None:
        """按当前数据算状态与缺口（**状态是算出来的，不是存下来的**）。

        ⚠ **状态用 `total_incl_cities` 判定**（含下属市）——
        否则「省级门户没建但地市级都有」的省会被误判为 `none`。

        ⚠ **地级市用 `max(total_records, data_records)`** ——
        见类文档 `data_records`：省级平台通道带 `extra.city` 时，
        市级没有专属通道但**确实有数据**，不能用 0 判 `none`。
        """
        # 兜底：`total_incl_cities` 不得小于 `total_records`
        # （单独构造 CoverageUnit 时不会走 build_units 的汇总逻辑）
        if self.total_incl_cities < self.total_records:
            self.total_incl_cities = self.total_records
        if self.level == "province":
            effective = self.total_incl_cities
        else:
            effective = max(self.total_records, self.data_records)
        self.gap = max(0, self.threshold - effective)
        if effective == 0 and not self.channels:
            self.status = STATUS_NONE
        elif effective < self.threshold:
            self.status = STATUS_THIN
        else:
            self.status = STATUS_OK

    def to_dict(self) -> dict:
        return {
            "name": self.name, "level": self.level, "parent": self.parent,
            "channels": self.channels, "total_records": self.total_records,
            "total_incl_cities": self.total_incl_cities,
            "data_records": self.data_records,
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


def norm_city(city: str | None) -> str:
    """归一化市名：去空白；自治州/地区/盟/特别行政区保持原样；其余补「市」。

    ⚠ **不要**把「自治州」也补成「市」—— `regions.PROVINCE_CITIES` 里
    新疆/云南/贵州的条目就是「昌吉回族自治州」「黔东南苗族侗族自治州」这种全称。
    """
    if not city:
        return ""
    c = "".join(str(city).split())
    for suf in ("特别行政区", "自治州", "地区", "盟"):
        if c.endswith(suf):
            return c
    return c if c.endswith("市") else c + "市"


def channel_city_map(channels) -> dict:
    """`{通道 key: 归一化市名}` —— 只含 `level == "city"` 且有 region 的通道。

    用于数据口径的**兜底归属**：记录没带 `extra.city` 时，
    若它来自某个市级通道，就归到那个市。
    """
    m: dict[str, str] = {}
    for c in channels:
        if c.level == "city" and (c.region or "").strip():
            m[c.key] = norm_city(c.region)
    return m


def known_cities() -> set:
    """334 个地级行政区的**全称集合**（来自 `regions.PROVINCE_CITIES`）。

    用途：`count_by_city` 用它**过滤占位值**。实测 IGI 的 `CITY` 字段
    常是 `市辖区` / `省直辖县级行政区划` 这类**非市名占位符**，
    不过滤就会凭空造出「市辖区市」这种假单元（第 7 轮实测：虚增 ~80 个）。
    """
    try:
        from regions import PROVINCE_CITIES
        out: set = set()
        for cities in PROVINCE_CITIES.values():
            out.update(cities)
        return out
    except Exception:                                                   # noqa: BLE001
        return set()


def count_by_city(channel_city: dict | None = None, *, scope_filter=None,
                  only_known: bool = True) -> dict:
    """**数据口径**：按记录归属的地级市统计条数（见 `CoverageUnit.data_records`）。

    归属规则（按优先级）：
      1. 记录带 `extra.city` ⇒ 归该市（IGI / 省级 12345 平台 / 广东 hdjlpt 都带）
      2. 否则，`source` 命中 `channel_city` ⇒ 归该市级通道的 region

    `only_known=True`（默认）：**只保留 334 个地级行政区里的市** ——
    过滤掉 IGI 的 `市辖区` 等占位值，避免造出假单元（见 `known_cities()`）。

    ⇒ 返回 `{归一化市名: 条数}`。**这是「这个市到底有没有数据」的唯一可信口径**，
    与「有没有注册一个叫该市的通道」是两件事。
    """
    channel_city = channel_city or {}
    known = known_cities() if only_known else set()
    counts: dict[str, int] = {}
    for rec in iter_records(str(DATA_DIR / "*.jsonl")):
        if scope_filter is not None:
            try:
                if not scope_filter(rec):
                    continue
            except Exception:                                           # noqa: BLE001
                continue
        extra = rec.get("extra")
        city = norm_city((extra or {}).get("city") if isinstance(extra, dict) else None)
        if not city:
            city = channel_city.get(str(rec.get("source") or ""), "")
        if not city:
            continue
        if only_known and city not in known and city.rstrip("市") not in known:
            continue
        counts[city] = counts.get(city, 0) + 1
    return counts


def merge_city_data(units: "list[CoverageUnit]", city_counts: dict,
                    *, threshold_city: int = DEFAULT_THRESHOLD_CITY) -> int:
    """把**数据口径**的市并入覆盖单元：已存在的填 `data_records`，缺失的**新建**。

    ⇒ 返回**新增**的市级单元数（= 只靠省级通道覆盖、此前被判 `none` 的市）。
    新建单元的 `total_records` 保持 0（它确实没有专属通道），
    但 `data_records > 0` ⇒ `recompute()` 会给出真实状态（`ok` / `thin`），不再误判 `none`。
    """
    city_units = {u.name: u for u in units if u.level == "city"}
    added = 0
    for name, n in city_counts.items():
        u = city_units.get(name)
        if u is None:
            u = CoverageUnit(name, "city", threshold=threshold_city)
            units.append(u)
            city_units[name] = u
            added += 1
        u.data_records = n
    for u in city_units.values():
        u.recompute()
    return added



def _count_for_channel(channel_key: str, counts: dict,
                       channel_keys: "set | None" = None) -> int:
    """某通道的数据量 = 它自己 + 所有以 `它-` 开头的子 source。

    ⚠ 为什么需要（spec 005 T602，2026-10-10 实测）：
    `counts` 的键是**数据文件里的 `source` 值**，通道的键是 `c.key`，两者不总是相等：
      · IGI 系：数据写 `sx-igi-24`，通道 key 是 `sx-igi`
      · 天津 enorth：数据写 `tj-enorth-wuqing`，通道 key 是 `tj-enorth`
      · `ln-8890-kb`：数据带 `-kb` 后缀，通道 key 是 `ln-8890`
    原来只 `counts.get(c.key, 0)` ⇒ 这些数据**在覆盖报表里隐形**
    （实测 393 个 source / 121,762 条）。

    ⚠ **必须做最长前缀消歧**：若同时登记了 `gx-igi` 与 `gx-igi-293` 两个**通道**，
    文件 `gx-igi-293-….jsonl` 会被两个都匹配到 ⇒ 重复计数。
    故对每个 source，先算它**最长匹配的通道 key**，只有那个通道吃它。

    ⚠ 关键：判定归属时比的是**通道 key 集合**，不是 `counts` 的键集合 ——
    `sx-igi-24` 只是数据里的 source（不是通道），它应归给通道 `sx-igi`。
    `channel_keys=None`（默认）时退化为"用 `counts` 的键当通道集合"，
    便于单测直接喂两个字典。
    """
    return _attribute_counts(channel_key, counts, channel_keys)[0]


def _attribute_counts(channel_key: str, counts: dict,
                      channel_keys: "set | None" = None) -> tuple:
    """把 `counts` 里每个 source 归给「最长匹配的通道 key」，返回本通道拿到的合计。

    `channel_keys=None` 时退化为"用 `counts` 的键当通道集合"（便于单测）。
    """
    keys = list(channel_keys) if channel_keys is not None else list(counts)
    total = 0
    n_src = 0
    for k, v in counts.items():
        owner = None
        for ck in keys:
            if k == ck or k.startswith(ck + "-"):
                if owner is None or len(ck) > len(owner):
                    owner = ck
        if owner == channel_key:
            total += v
            n_src += 1
    return total, n_src


def build_units(channels, counts: dict, *, threshold_province: int,
                threshold_city: int, city_counts: dict | None = None) -> "list[CoverageUnit]":
    """把通道 + 条数聚合成覆盖单元。

    - 省级单元：31 个行政区（**每个都有行**，哪怕一条数据都没有）
    - 地级单元：从 `channel.region` 里出现过的市名（动态发现）
    - 其它层级（national / other）：单列，不混进省市统计

    `city_counts`（2026-10-10 第 7 轮新增，可选）：`count_by_city()` 的**数据口径**结果。
    传入后，只靠省级平台通道覆盖的市会被**补建为市级单元**并填 `data_records`
    ⇒ 不再被误报 `none`（辽宁 12 个市就是这么被漏计的）。传 `None` = 旧行为不变。
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

    #: 通道 key 集合 —— 判定 source 归属时**只比这些**（见 `_attribute_counts`）
    channel_keys = {c.key for c in channels}

    for c in channels:
        # ⚠⚠ 2026-10-10（spec 005 T602）：**必须把「子 source」的数据也算进来**。
        #   实测：706 个有数据的 source 里 **393 个（121,762 条）不在销号表内** ——
        #   因为 `counts` 的键是**数据文件里的 `source` 值**，而通道的键是 `c.key`，
        #   两者不总是相等：
        #     · IGI 系（368 个）：数据里写 `sx-igi-24`（子 siteId），通道 key 是 `sx-igi`
        #     · 天津 enorth（24 个）：数据里写 `tj-enorth-wuqing` 等，通道 key 是 `tj-enorth`
        #     · `ln-8890-kb`（13,941 条）：数据里带 `-kb` 后缀，通道 key 是 `ln-8890`
        #   ⇒ 原来 `counts.get(c.key, 0)` 对它们**取到 0** ⇒ 那些数据在覆盖报表里**隐形**。
        #   ⇒ 现在按「最长匹配的通道 key」归集，且**只归一次**（防重复计数）。
        n, _n_src = _attribute_counts(c.key, counts, channel_keys)
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

    # ★ 把「地级市的量」汇总到所属省 ⇒ 得到 total_incl_cities
    #   实测动机：甘肃省级显示 0 条，但该省已有 4 个市级源共 9,659 条 ⇒ 口径误导。
    for u in units:
        u.total_incl_cities = u.total_records
    for c in city.values():
        parent = _province_of_city(c.name, alias)
        if parent and parent in prov:
            prov[parent].total_incl_cities += c.total_records

    for u in units:
        u.recompute()

    # ★ 数据口径：把「只在省级平台里出现过、没有专属通道」的市补建为市级单元
    #   ⚠ **不改 `total_incl_cities`** —— 那些记录的通道本身是省级/平台级，
    #   其条数**已经计入省级 `total_records`**，再加一次就是重复计数
    #   （辽宁 `ln-8890` 2 万条全带 `extra.city`，会把省总量翻倍）。
    #   `data_records` 只用于**市级状态判定**，不进省级汇总。
    if city_counts:
        merge_city_data(units, city_counts, threshold_city=threshold_city)

    # 算相对中位数（**同级比同级**，R4）
    for lvl in ("province", "city"):
        group = [u for u in units if u.level == lvl and
                 max(u.total_records, u.data_records) > 0]
        if not group:
            continue
        vals = sorted(max(u.total_records, u.data_records) for u in group)
        n = len(vals)
        # 真中位数：偶数个取中间两个的平均（不是「上中位数」）
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        for u in units:
            if u.level == lvl:
                v = max(u.total_records, u.data_records)
                u.ratio_to_median = round(v / med, 3) if med else 0.0
    return units


def _province_of_city(city_name: str, alias: dict) -> str | None:
    """由市名反查所属省。

    **优先用 `regions.py` 的精确映射表**（333 个地级行政区）——
    2026-10-10 之前靠「市名里含省名」猜，而**大多数市名不含省名**
    （宝鸡市 / 天水市 / 烟台市），导致汇总严重偏低。
    """
    try:
        from regions import province_of_city as _poc
        p = _poc(city_name)
        if p:
            return p
    except Exception:                                                   # noqa: BLE001
        pass
    # 兜底：市名里含省名（极少见，但保留）
    for p in PROVINCE_NAMES:
        if p in city_name or p.rstrip("省市自治区") in city_name:
            return p
    return None


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
