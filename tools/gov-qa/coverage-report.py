"""覆盖销号表 CLI —— spec 004 的 US2。

对应契约 `specs/004-*/contracts/coverage.md`。

## 它回答三个问题

1. **333 个地级行政区覆盖了几个？** → `PROV_TOTAL` / `CITY_TOTAL` + 状态分布
2. **云南还差多少？** → `--thin` 列出缺口数值
3. **云南缺什么渠道？** → `--region 云南省 --uncovered` 列出未建源渠道
   （只知道"数据少"没用，要知道"缺什么"才能补）

## 退出码

| 码 | 含义 |
|---|---|
| `0` | 报告生成成功（**不代表覆盖达标**） |
| `1` | **有 `none` 单元**（某地区完全没来源）—— 硬缺口 |
| `2` | 生成失败 |

> ⚠ 「有来源但数据少」（`thin`）**不**触发退出码 1 —— 那是深度问题，不是缺失问题。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from channel import load_channels                                     # noqa: E402
from common import ascii_kv, human                                    # noqa: E402
from coverage import (DEFAULT_THRESHOLD_CITY,                         # noqa: E402
                      DEFAULT_THRESHOLD_PROVINCE, STATUS_NONE,
                      STATUS_OK, STATUS_THIN, build_units, channel_city_map,
                      count_by_city, count_by_source, uncovered_for)

EXIT_OK = 0
EXIT_NONE_UNIT = 1
EXIT_FATAL = 2


def _missing_cities_detail(units) -> tuple:
    """算「334 市全名单里，数据口径下零记录的有哪些」。

    **这是"缺多少个市"的唯一出处** —— `--missing-cities` 与 `--quiet` 都调它，
    避免两条路各算各的（spec 005 T106 修的正是这个：同工具同数据两个结论）。

    返回 `(按省分组的缺失清单, 市总数, 缺失总数)`。
    """
    from regions import PROVINCE_CITIES                                 # noqa: E402
    covered = {u.name for u in units
               if u.level == "city" and max(u.total_records, u.data_records) > 0}
    # 通道/数据两侧都可能出现「去市」写法，做一次双向匹配
    bare = {n.rstrip("市") for n in covered}
    by_prov: dict[str, list[str]] = {}
    n_total = n_miss = 0
    for p, cities in PROVINCE_CITIES.items():
        miss = []
        for c in cities:
            n_total += 1
            if c in covered or c.rstrip("市") in bare:
                continue
            miss.append(c)
        n_miss += len(miss)
        if miss:
            by_prov[p] = miss
    return by_prov, n_total, n_miss


def _missing_city_count(units) -> int:
    """只要总数（给 `--quiet` 用）。"""
    try:
        return _missing_cities_detail(units)[2]
    except Exception:                                                   # noqa: BLE001
        return 0


def _scope_filter(scope: str):
    """口径过滤器（FR-034）。

    配合 GOAL.md 的「口径收窄」—— 分母可按新口径重算。
    这里实现一个**保守版**：只认记录里已带的 `extra.scope_tag`。
    更精确的口径判定在 `standards-audit/govstd/lawstd_filter.py`（另一个项目）。
    """
    if not scope:
        return None
    want = scope.strip()
    def _f(rec):
        ex = rec.get("extra") or {}
        return isinstance(ex, dict) and str(ex.get("scope_tag") or "") == want
    return _f


def main() -> int:
    ap = argparse.ArgumentParser(description="覆盖销号表（spec 004 US2）")
    ap.add_argument("--level", default="", choices=["", "province", "city", "other"])
    ap.add_argument("--thin", action="store_true", help="只看薄弱地区（按缺口降序）")
    ap.add_argument("--top", type=int, default=0, help="配合 --thin：只显示前 N 个")
    ap.add_argument("--region", default="", help="看某个地区（名称包含匹配）")
    ap.add_argument("--uncovered", action="store_true",
                    help="配合 --region：列出该地区**尚未建源的渠道**")
    ap.add_argument("--threshold-province", type=int, default=DEFAULT_THRESHOLD_PROVINCE)
    ap.add_argument("--threshold-city", type=int, default=DEFAULT_THRESHOLD_CITY)
    ap.add_argument("--scope", default="", help="按口径过滤（读 extra.scope_tag）")
    ap.add_argument("--no-city-data", action="store_true",
                    help="关掉「数据口径」的市级补建（退回旧的通道口径）")
    ap.add_argument("--missing-cities", action="store_true",
                    help="列出**数据口径下真正零记录**的地级市（按省分组）")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII 机器可读")
    args = ap.parse_args()

    try:
        channels = load_channels()
        sf = _scope_filter(args.scope)
        counts = count_by_source(scope_filter=sf)
        # ★ 数据口径：把「只在省级平台里出现过」的市补进来（见 coverage.CoverageUnit）
        ccounts = {} if args.no_city_data else count_by_city(
            channel_city_map(channels), scope_filter=sf)
        units = build_units(channels, counts,
                            threshold_province=args.threshold_province,
                            threshold_city=args.threshold_city,
                            city_counts=ccounts or None)
    except Exception as e:                                              # noqa: BLE001
        human(f"❌ 生成失败：{type(e).__name__}: {e}")
        return EXIT_FATAL

    # ---- 真正零记录的地级市（--missing-cities） --------------------------
    # 口径 = **数据**（max(total_records, data_records) == 0），不是「有没有专属通道」。
    # 动机：辽宁 12 个市的数据在省级 `ln-8890` 里，按通道口径会被误报成「缺来源」。
    if args.missing_cities:
        try:
            by_prov, n_total, n_miss = _missing_cities_detail(units)
        except Exception as e:                                          # noqa: BLE001
            human(f"❌ 读不到 regions.PROVINCE_CITIES：{e}")
            return EXIT_FATAL
        if args.quiet:
            ascii_kv({"CITY_TOTAL": n_total, "CITY_HAVE": n_total - n_miss,
                      "CITY_MISSING": n_miss})
        else:
            human(f"地级行政区 {n_total} 个｜**数据口径下有记录 {n_total - n_miss}**"
                  f"｜**零记录 {n_miss}**")
            human("")
            for p, cs in sorted(by_prov.items(), key=lambda kv: -len(kv[1])):
                human(f"  {p:16s} 缺 {len(cs):3d} 个："
                      f"{'、'.join(cs[:8])}{'…' if len(cs) > 8 else ''}")
        return EXIT_NONE_UNIT if n_miss else EXIT_OK

    # ---- 单地区查询（--region） ----------------------------------------
    if args.region:
        hit = [u for u in units if args.region in u.name]
        if not hit:
            human(f"⚠️  找不到地区：{args.region}")
            return EXIT_OK
        for u in hit:
            human(f"{u.name}（{u.level}）")
            human(f"  来源 {len(u.channels)} 个｜落盘 {u.total_records:,} 条"
                  f"｜达标线 {u.threshold:,}｜缺口 {u.gap:,}"
                  f"｜状态 {u.status}｜中位数比 {u.ratio_to_median}")
            if args.uncovered:
                miss = uncovered_for(u, channels)
                human(f"  未覆盖渠道：{'、'.join(miss)}")
                human(f"  已有来源：{'、'.join(u.channels) if u.channels else '（无）'}")
            if args.quiet:
                ascii_kv({"UNIT": u.name, "LEVEL": u.level,
                          "RECORDS": u.total_records, "GAP": u.gap,
                          "STATUS": u.status})
        return EXIT_NONE_UNIT if any(u.status == STATUS_NONE for u in hit) else EXIT_OK

    # ---- 汇总统计 ------------------------------------------------------
    sel = [u for u in units if not args.level or u.level == args.level]
    prov = [u for u in sel if u.level == "province"]
    city = [u for u in sel if u.level == "city"]

    def _cnt(us, st):
        return sum(1 for u in us if u.status == st)

    if args.quiet:
        ascii_kv({
            "PROV_TOTAL": len(prov), "PROV_OK": _cnt(prov, STATUS_OK),
            "PROV_THIN": _cnt(prov, STATUS_THIN), "PROV_NONE": _cnt(prov, STATUS_NONE),
            "CITY_TOTAL": len(city), "CITY_OK": _cnt(city, STATUS_OK),
            "CITY_THIN": _cnt(city, STATUS_THIN), "CITY_NONE": _cnt(city, STATUS_NONE),
            "CITY_DATA_ONLY": sum(1 for u in city
                                  if u.data_records > 0 and u.total_records == 0),
        })
        # ⚠⚠ **两个口径必须都说清，且退出码要一致**（spec 005 T106，2026-10-10 修）。
        #   实测矛盾：`--quiet` 报 `CITY_NONE=0` rc=0，而 `--missing-cities`
        #   报「零记录 182」rc=1 —— **同一工具、同一数据、两个结论**。
        #   根因：两条路算的**不是同一件事**：
        #     · `CITY_NONE` = 在**已建单元**里状态为 none 的个数
        #       （`build_units` 只为「有通道或有数据」的市建单元 ⇒ 天然接近 0）
        #     · `--missing-cities` = 拿 **334 市全名单**减「有数据的市」⇒ 真正缺多少个市
        #   ⇒ 前者恒小、后者才是有意义的缺口。**退出码按后者**（真实缺口）判，
        #     并把两个数**都打出来**，避免读者再被 `CITY_NONE=0` 误导成"覆盖完整"。
        n_missing = _missing_city_count(units)
        ascii_kv({"CITY_MISSING_FROM_334": n_missing})
        has_none = _cnt(sel, STATUS_NONE) > 0 or n_missing > 0
        return EXIT_NONE_UNIT if has_none else EXIT_OK

    human(f"覆盖销号表 —— 全国政务问答来源"
          f"（达标线：省级 {args.threshold_province:,} / 地级 {args.threshold_city:,}）")
    if args.scope:
        human(f"口径过滤：{args.scope}")
    human("")
    human("⚠ **两个口径**：`本级` = 只算省级门户；`含下属市` = 加上地级市的量。")
    human("   **薄弱省清单应看「含下属市」** —— 否则会误判（如甘肃省级 0 但市级有 9,659 条）。")
    human("")
    human("⚠ **市级状态按「数据口径」判**（`max(本级通道, extra.city 归属)`）——")
    human("   省级 12345 平台（如辽宁 `ln-8890`）的记录带 `extra.city`，"
          "一个通道覆盖全省的市；只按通道数会把它们误报 `none`。")
    n_data_only = sum(1 for u in city if u.data_records > 0 and u.total_records == 0)
    if n_data_only:
        human(f"   ⇒ 本轮有 **{n_data_only} 个市**是「无专属通道但有数据」，已不再计为 `none`。")
    human("")
    for label, us in (("省级", prov), ("地级", city)):
        if not us:
            continue
        human(f"【{label}】{len(us)} 个单元")
        human(f"  ✅ ok    {_cnt(us, STATUS_OK):3d} 个")
        human(f"  ⚠️  thin  {_cnt(us, STATUS_THIN):3d} 个")
        human(f"  ❌ none  {_cnt(us, STATUS_NONE):3d} 个")
        human("")

    # 缺口最大的（**按含下属市排**，那才是真实缺口）
    worst = sorted([u for u in sel if u.gap > 0],
                   key=lambda u: -u.total_incl_cities if u.level == "province"
                   else -max(u.total_records, u.data_records))
    if args.top:
        worst = worst[:args.top]
    if worst:
        human(f"缺口最大的 {len(worst)} 个：")
        for u in worst:
            miss = uncovered_for(u, channels)
            miss_s = "、".join(miss[:3])
            if u.level == "province":
                human(f"    {u.name:16s} 本级 {u.total_records:7,d}"
                      f"  含下属市 {u.total_incl_cities:8,d}"
                      f"  还差 {u.gap:7,d} 条  ← 缺 {miss_s}")
            else:
                eff = max(u.total_records, u.data_records)
                tag = "（数据口径）" if u.data_records > u.total_records else ""
                human(f"    {u.name:16s} {eff:8,d} 条{tag}"
                      f"  还差 {u.gap:7,d} 条  ← 缺 {miss_s}")

    n_none = _cnt(sel, STATUS_NONE)
    if n_none:
        human("")
        human(f"⚠️  有 {n_none} 个单元**完全没有来源** —— 这是硬缺口，不是深度问题。")
    return EXIT_NONE_UNIT if n_none > 0 else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
