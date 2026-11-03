"""看「哪些地级市还没有来源」—— 这才是最大的覆盖缺口。

333 个地级行政区，目前只有 70 个有来源 ⇒ **263 个没有**。

只读，不落盘。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from channel import load_channels                                    # noqa: E402
from regions import PROVINCE_CITIES                                  # noqa: E402


def main() -> int:
    chs = [c for c in load_channels() if c.level == "city"]
    have = set()
    for c in chs:
        if c.region:
            have.add(c.region)
            have.add(c.region.rstrip("市"))

    total = 0
    missing_by_prov: dict[str, list[str]] = {}
    for prov, cities in PROVINCE_CITIES.items():
        miss = []
        for city in cities:
            total += 1
            if city in have or city.rstrip("市") in have:
                continue
            miss.append(city)
        if miss:
            missing_by_prov[prov] = miss

    n_miss = sum(len(v) for v in missing_by_prov.values())
    print(f"地级行政区总数 {total}｜已有来源 {total - n_miss}｜**缺来源 {n_miss}**")
    print()
    print("按省（缺得多的排前面）：")
    for prov, miss in sorted(missing_by_prov.items(), key=lambda kv: -len(kv[1]))[:15]:
        print(f"  {prov:16s} 缺 {len(miss):3d} 个：{'、'.join(miss[:6])}"
              f"{'…' if len(miss) > 6 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
