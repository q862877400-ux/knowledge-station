"""用**数据本身**量「地级市覆盖」，而不是只看「注册了多少个 city 通道」。

## 为什么必须做这个（方法学问题）

`recon/missing-cities.py` 的口径是：**某地级市是否有一个 `level=city` 的通道**。
但 IGI / 广东 hdjlpt / 湖南统一平台这类**省级或平台级**通道，
**记录里带 `extra.city` 字段**（IGI 有 PROVINCE/CITY/AREA 三级归属）。

⇒ 可能出现「**数据里有柳州市的 500 条，但没有注册一个叫『柳州市』的通道**」
⇒ `missing-cities.py` 报「柳州缺来源」，但**实际上已经有柳州的数据**。

这直接决定 M4 的**分母**对不对 —— 是「262 个市真的零数据」，还是「262 个市没有**专属通道**」。
两者要做的事完全不同。

## 判定
- `by_city`：`extra.city` 归一化后（补「市」）的**记录数**
- 与 `regions.PROVINCE_CITIES`（334 个地级行政区）求交
- 输出：有数据的市 / 零数据的市 / 只靠省级通道覆盖的市

只读，不落盘。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa/recon
ROOT = HERE.parent                              # tools/gov-qa
sys.path.insert(0, str(ROOT))

from regions import PROVINCE_CITIES                                  # noqa: E402

DATA = ROOT / "data"


def _norm(city: str | None) -> str:
    """归一化市名：去空白、去「地区/自治州/盟」后缀差异尽量保留，缺「市」则补。"""
    if not city:
        return ""
    c = re.sub(r"\s+", "", str(city))
    for suf in ("特别行政区", "自治州", "地区", "盟"):
        if c.endswith(suf):
            return c
    if not c.endswith("市"):
        return c + "市"
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    by_city: dict[str, int] = defaultdict(int)
    by_prov_city: dict[str, set[str]] = defaultdict(set)
    total = 0
    with_city_field = 0

    files = sorted(DATA.glob("*.jsonl"))
    for p in files:
        try:
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                total += 1
                try:
                    r = json.loads(line)
                except Exception:                                        # noqa: BLE001
                    continue
                e = r.get("extra") or {}
                city = _norm(e.get("city"))
                prov = (e.get("province") or "").strip()
                if city:
                    with_city_field += 1
                    by_city[city] += 1
                    if prov:
                        by_prov_city[prov].add(city)
        except Exception as ex:                                          # noqa: BLE001
            # 单个文件读失败不能拖垮全局统计（文件可能正被另一个 agent 写）
            print(f"  ⚠ 跳过 {p.name}: {type(ex).__name__}", file=sys.stderr)

    # 全部地级行政区
    all_cities: list[tuple[str, str]] = []
    for prov, cities in PROVINCE_CITIES.items():
        for c in cities:
            all_cities.append((prov, c))

    have, zero = [], []
    for prov, c in all_cities:
        n = by_city.get(c) or by_city.get(c.rstrip("市")) or 0
        (have if n else zero).append((prov, c, n))

    L: list[str] = []

    def say(s: str = "") -> None:
        L.append(s)

    say(f"数据文件 {len(files)} 个｜总记录 {total:,}")
    say(f"带 extra.city 字段的记录 {with_city_field:,}（{with_city_field / max(total,1) * 100:.1f}%）")
    say(f"出现的**不同市名** {len(by_city):,} 个")
    say("")
    say(f"地级行政区总数 {len(all_cities)}｜"
        f"**数据里有记录 {len(have)}**｜**数据里零记录 {len(zero)}**")
    say("")
    say(f"—— 有数据的市（按记录数降序，前 {args.top}）——")
    for prov, c, n in sorted(have, key=lambda x: -x[2])[:args.top]:
        say(f"  {prov:14s} {c:10s} {n:>8,}")
    say("")
    say("—— 零数据的市（按省分组）——")
    byp: dict[str, list[str]] = defaultdict(list)
    for prov, c, _ in zero:
        byp[prov].append(c)
    for prov, cs in sorted(byp.items(), key=lambda kv: -len(kv[1])):
        say(f"  {prov:14s} {len(cs):3d} 个：{'、'.join(cs[:8])}{'…' if len(cs) > 8 else ''}")

    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
