"""通道（Channel）—— 从现有 331 个 adapter 自动构建的通道清单。

对应 spec 004 的 FR-007 ~ FR-010，数据结构见 `data-model.md` 的 E1。

## 设计要点

**不重写 adapter，只在它们之上加一层**（research.md R6/plan 的「结构决策」）。
331 个 adapter 是项目最贵的资产，改造风险远大于收益。
本模块只做三件事：

1. **枚举**：从 `adapters.ADAPTERS` 拿到全部通道
2. **推断水位类型**（T010）：按 adapter 特征猜 `page` / `since` / `idset`，
   **猜不出默认 `idset`** —— 它最安全（保证不重复），只是慢
3. **推断地区归属**（T011）：从 `SITE["level"]` + `SITE["name"]` 解析出省/市，供覆盖销号表用

## 关于「水位类型推断」

这是**启发式**，不是精确判定。所以：
- 推断结果写进 `state/watermarks.json` 后**以存储值为准**（人工可覆盖）
- 推断错了的后果**只是慢**（退化成 `idset` 全量翻），**不会漏数据**
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

#: 中国省级行政区（用于从 SITE 名称解析归属）
PROVINCES = (
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
    "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
    "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
    "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
    "香港", "澳门", "台湾",
)

#: 国家部委/中央机构的关键词（用于 level=national 判定）
NATIONAL_MARK = (
    "部", "委", "总局", "国务院", "人大", "政协", "法院", "检察院",
    "气象局", "统计局", "知识产权局", "药监局", "标准委", "税务总局",
)


class Channel:
    """一个可采集的数据来源。字段见 data-model.md E1。"""

    __slots__ = ("key", "name", "level", "region", "entry",
                 "watermark_type", "self_reported_total", "cap", "status")

    def __init__(self, key: str, name: str = "", *, level: str = "other",
                 region: str = "", entry: str = "", watermark_type: str = "idset",
                 self_reported_total=None, cap=None, status: str = "ok"):
        self.key = key
        self.name = name
        self.level = level
        self.region = region
        self.entry = entry
        self.watermark_type = watermark_type
        self.self_reported_total = self_reported_total
        self.cap = cap
        self.status = status

    def __repr__(self) -> str:                                          # pragma: no cover
        return f"Channel({self.key!r}, {self.level}, wm={self.watermark_type})"


# ---------------------------------------------------------------- 水位类型推断

def infer_watermark_type(adapter, site: dict) -> str:
    """按 adapter 特征猜水位类型（T010）。

    **猜不出默认 `idset`** —— 它保证不重复，只是慢。宁可慢不可漏。
    """
    src = ""
    try:
        mod_file = Path(getattr(adapter, "__file__", "") or "")
        if mod_file.exists():
            src = mod_file.read_text(encoding="utf-8", errors="replace")[:20000]
    except Exception:                                                   # noqa: BLE001
        pass

    # ① 有明确的分页参数 ⇒ page 型
    if re.search(r"GOVQA_PAGE_FROM|page_from|--page|cur_page|pageNo|page_no|"
                 r"pageIndex|startrecord|current\s*=|pagesize|page_size", src, re.I):
        # 但要排除「只有时间字段没有页码」的情况
        if re.search(r"GOVQA_PAGE_FROM|cur_page|pageNo|page_no|pageIndex|"
                     r"startrecord|pagesize|page_size", src, re.I):
            return "page"

    # ② 有明确的时间字段且列表带时间 ⇒ since 型
    if re.search(r"submitTime|publishDate|pubDate|createTime|asked_at|"
                 r"releaseDate|updateTime", src):
        return "since"

    # ③ 兜底：idset（保证不重复）
    return "idset"


# ---------------------------------------------------------------- 地区归属推断

def infer_region(site: dict) -> tuple[str, str]:
    """从 SITE 解析 (level, region)（T011）。

    返回 `(level, region)`，`level` ∈ `national` / `province` / `city` / `other`。
    """
    name = str(site.get("name") or "")
    level = str(site.get("level") or "")

    # 显式 level 优先
    if level in ("national", "province", "city"):
        return level, _region_from_name(name, level)

    # 按名称推断
    if any(m in name for m in NATIONAL_MARK) and not any(p in name for p in PROVINCES):
        return "national", ""
    for p in PROVINCES:
        if p in name:
            # 「XX省」「XX市」都在名字里 ⇒ 看是否有「省」字样判定是省级还是市级
            if f"{p}省" in name or f"{p}市" in name and p in ("北京", "天津", "上海", "重庆"):
                return "province", f"{p}省" if f"{p}省" in name else f"{p}市"
            return "province", f"{p}省"
    return "other", ""


def _region_from_name(name: str, level: str) -> str:
    for p in PROVINCES:
        if p in name:
            if level == "city":
                # 取「XX市」形式的市名
                m = re.search(rf"({p}[\u4e00-\u9fa5]{{0,4}}市)", name)
                return m.group(1) if m else f"{p}省"
            return f"{p}省" if p not in ("北京", "天津", "上海", "重庆") else f"{p}市"
    return ""


# ---------------------------------------------------------------- 通道清单

def load_channels(*, load_adapters: bool = True) -> "list[Channel]":
    """从 `adapters.ADAPTERS` 构建全部通道（T009）。

    `load_adapters=False` 时只返回空列表 —— 供单元测试用（不依赖真实 adapter）。
    """
    if not load_adapters:
        return []
    sys.path.insert(0, str(HERE))
    try:
        import adapters
    except Exception:                                                   # noqa: BLE001
        return []

    out: list[Channel] = []
    for key in sorted(adapters.ADAPTERS):
        try:
            mod = adapters.load(key)
            site = dict(getattr(mod, "SITE", {}) or {})
        except Exception:                                               # noqa: BLE001
            # 加载失败的 adapter 也要登记 —— 否则「零数据」检测会漏掉它
            out.append(Channel(key, name="", level="other", status="blocked"))
            continue

        lvl, region = infer_region(site)
        out.append(Channel(
            key=key,
            name=str(site.get("name") or ""),
            level=lvl,
            region=region,
            entry=str(site.get("entry") or ""),
            watermark_type=infer_watermark_type(mod, site),
            status=str(site.get("status") or "ok"),
        ))
    return out


def group_by_level(channels) -> dict:
    """按层级分组，供覆盖销号表用。"""
    out: dict[str, list] = {}
    for c in channels:
        out.setdefault(c.level, []).append(c)
    return out
