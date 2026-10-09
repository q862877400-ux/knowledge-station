"""构建 **city → 门户域名** 映射（M4 的根阻塞）。

## 为什么需要它

`coverage-report.py --missing-cities` 给出 193 个零记录地级市，
但**要采就得先知道域名**。全仓没有完整映射表。
（省政府门户首页**不列**地市链接 —— 已实测：广东/河南/安徽 5 省首页抽到 **0 个**市链接。）

## 假设（要实测验证，不是拍脑袋）

中国地级市政府门户**多数**用 `www.<市名全拼>.gov.cn`：
 · 芜湖市 → `www.wuhu.gov.cn` ✅ · 宜昌市 → `www.yichang.gov.cn` ✅
 · 佛山市 → `www.foshan.gov.cn` ✅ · 珠海市 → `www.zhuhai.gov.cn` ✅
 · **反例**：洛阳市 → `www.ly.gov.cn`（缩写，不是 luoyang）

⇒ 生成**多个候选**（全拼 / 首字母缩写 / http 与 https），**逐个实测**，
只把 **HTTP 200 的**写进结果。**不猜、不推断**（GOAL.md #7）。

## 输出

`recon/city-domains.json`：`{市名: {url, host, via, status}}`
`via` 记录是哪个候选命中（`pinyin` / `initials` / `known`），便于复盘。

只写 `recon/`，不碰 `data/`。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from regions import PROVINCE_CITIES                                   # noqa: E402

OUT = HERE / "city-domains.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: 去尾缀（顺序重要：先长后短）
SUFFIXES = ("特别行政区", "自治州", "地区", "盟", "市")
#: 民族修饰词（在「自治州」前）
ETHNIC = ("维吾尔", "哈萨克", "柯尔克孜", "蒙古", "回", "藏", "苗", "侗", "布依",
          "哈尼", "彝", "白", "傣", "景颇", "傈僳", "拉祜", "佤", "纳西", "羌",
          "土家", "朝鲜", "满", "瑶", "黎", "畲", "水", "仡佬", "壮", "土", "达斡尔",
          "鄂温克", "鄂伦春", "锡伯", "塔吉克", "乌孜别克", "俄罗斯", "裕固", "保安",
          "撒拉", "东乡", "普米", "怒", "德昂", "阿昌", "基诺", "门巴", "珞巴", "独龙")


def core_name(city: str) -> str:
    """取「专名」：`昌吉回族自治州` → `昌吉`；`阿克苏地区` → `阿克苏`；`洛阳市` → `洛阳`。"""
    c = city
    for s in SUFFIXES:
        if c.endswith(s):
            c = c[: -len(s)]
            break
    # 反复剥民族词（可能叠，如「蒙古族藏族自治州」）
    changed = True
    while changed:
        changed = False
        for e in ETHNIC:
            if c.endswith(e):
                c = c[: -len(e)]
                changed = True
    return c


def candidates(city: str) -> "list[tuple[str, str]]":
    """返回 `[(候选域名, via)]`。"""
    from pypinyin import lazy_pinyin

    core = core_name(city)
    if not core:
        return []
    py = "".join(lazy_pinyin(core)).lower()
    py = re.sub(r"[^a-z0-9]", "", py)
    ini = "".join(p[0] for p in lazy_pinyin(core) if p).lower()
    ini = re.sub(r"[^a-z0-9]", "", ini)
    out: list[tuple[str, str]] = []
    for v in (py, ini):
        if v and all(v != x[0] for x in out):
            out.append((v, "pinyin" if v == py else "initials"))
    return out


def probe(host: str, client: httpx.Client) -> "tuple[bool, str]":
    """实测域名是否可达。返回 `(ok, final_url)`。"""
    for scheme in ("https", "http"):
        url = f"{scheme}://www.{host}.gov.cn/"
        try:
            r = client.get(url, timeout=10)
            if r.status_code == 200 and len(r.text or "") > 500:
                return True, str(r.url)
        except Exception:                                               # noqa: BLE001
            continue
    return False, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only-missing", action="store_true",
                    help="只跑「数据口径下零记录」的市（默认跑全部 334）")
    args = ap.parse_args()

    # 已知映射（从既有 recon 里捞，作为第一优先候选）
    known: dict[str, str] = {}
    for f in HERE.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                                               # noqa: BLE001
            continue
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict) and isinstance(v.get("base"), str):
                    known.setdefault(k, v["base"])

    all_cities: list[tuple[str, str]] = []
    for prov, cities in PROVINCE_CITIES.items():
        for c in cities:
            all_cities.append((prov, c))

    if args.only_missing:
        try:
            sys.path.insert(0, str(ROOT))
            from coverage import channel_city_map, count_by_city            # noqa: E402
            from channel import load_channels                               # noqa: E402
            have = count_by_city(channel_city_map(load_channels()))
            have_bare = {k.rstrip("市") for k in have}
            all_cities = [(p, c) for p, c in all_cities
                          if c not in have and c.rstrip("市") not in have_bare]
        except Exception as e:                                          # noqa: BLE001
            print(f"  ⚠ --only-missing 计算失败，跑全部：{e}", file=sys.stderr)

    print(f"待测地级行政区 {len(all_cities)} 个；已知映射 {len(known)} 条", flush=True)

    result: dict[str, dict] = {}

    def work(item: tuple[str, str]) -> "tuple[str, dict | None]":
        prov, city = item
        cands = candidates(city)
        # ★ 既有 recon 里的已知映射（`igi-portal-sweep-city2.json` 等，键是拼音）
        #   作为**第一优先候选** —— 它已被前几轮实测过，比盲猜准。
        core = core_name(city)
        if core:
            from pypinyin import lazy_pinyin as _lp
            py = re.sub(r"[^a-z0-9]", "", "".join(_lp(core)).lower())
            if py in known:
                cands = [(py, "known")] + cands
        with httpx.Client(headers=H, follow_redirects=True,
                          trust_env=False, verify=False) as client:
            for host, via in cands:
                ok, final = probe(host, client)
                if ok:
                    return city, {"url": final, "host": host, "via": via,
                                  "status": 200, "province": prov}
        return city, None

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (city, info) in enumerate(ex.map(work, all_cities), 1):
            if info:
                result[city] = info
            if i % 25 == 0:
                print(f"  进度 {i}/{len(all_cities)}，命中 {len(result)}", flush=True)

    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")
    hit = len(result)
    print(f"完成：命中 {hit}/{len(all_cities)} → {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
