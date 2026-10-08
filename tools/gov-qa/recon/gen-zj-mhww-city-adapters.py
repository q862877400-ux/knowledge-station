"""生成浙江 11 个地级市的「民呼我为统一平台」适配器（薄适配器，共用 _zj_mhww_common）。

每个适配器 = 一个市（行政区划码），key `zj-<拼音>`，level=city。
用法：python recon/gen-zj-mhww-city-adapters.py
输出：adapters/zj_<拼音>.py × 11
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ADIR = HERE.parent / "adapters"

# (城市, 拼音, 行政区划码)
CITIES = [
    ("杭州", "hangzhou", "330100"),
    ("宁波", "ningbo", "330200"),
    ("温州", "wenzhou", "330300"),
    ("嘉兴", "jiaxing", "330400"),
    ("湖州", "huzhou", "330500"),
    ("绍兴", "shaoxing", "330600"),
    ("金华", "jinhua", "330700"),
    ("衢州", "quzhou", "330800"),
    ("舟山", "zhoushan", "330900"),
    ("台州", "taizhou", "331000"),
    ("丽水", "lishui", "331100"),
]

TEMPLATE = '''"""适配器：**{city}市·民呼我为统一平台·办理公开**（`code={code}`）。

## 站点事实（2026-10-09 实测，证据 recon/city-js-zj-zjmhww-probe.txt）
浙江省互动统一收敛到**浙江省民呼我为统一平台**（`zxts.zjzwfw.gov.cn/zwmhww/`）。
列表接口的 `code` 是**精确行政区划码**（非层级聚合）：
 · `330000`=省本级、`{code}`=**{city}市**、非法码=0 条 ⇒ 各市互不重叠。
本适配器复用省本级 `zj_mhww` 的字体反爬解码（glyph 名即真字），仅换 `code`。

## 接口
 · 列表 `POST {{BASE}}/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj`
     body `{{"code":"{code}","bt":"","bldw":"","pageNum":<n>,"pageSize":<m>}}` → `data.totalItem`
 · 明细 `GET  {{BASE}}/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid?storeId=<id>`
     → `dfyj`=答复原文、`nr`=问题、`dfdw`=答复单位、`fysj`/`dfsj`=反映/答复时间。

## 备注
 · 可反复跑（开跑跳过已落盘 id，`limit`=本轮新增）；`max_records` 默认 500 兜底。
 · 全量很大（{city} 实测 totalItem≈{total}），全采前请评估耗时。
"""
from __future__ import annotations

from adapters._zj_mhww_common import harvest_area

SITE = {{
    "key": "zj-{py}",
    "name": "{city}市·民呼我为·办理公开",
    "kind": "api",
    "level": "city",
    "entry": "https://zxts.zjzwfw.gov.cn/zwmhww/#/home/index/public",
    "status": "ok",
    "note": "浙江民呼我为统一平台 code={code}；文字 woff 字体混淆按 glyph 名解码；"
            "可反复跑（limit=本轮新增）",
}}

AREA = "{code}"


def harvest(fetch, *, limit: int | None = None, max_records: int = 500) -> list[dict]:
    """采{city}市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。"""
    return harvest_area(fetch, SITE=SITE, area=AREA, limit=limit,
                        max_records=max_records)
'''

TOTALS = {"330100": 61768, "330200": 13284, "330300": 8721, "330400": 5875,
          "330500": 2135, "330600": 5843, "330700": 5962, "330800": 3289,
          "330900": 1857, "331000": 2737, "331100": 2938}


def main() -> int:
    for city, py, code in CITIES:
        body = TEMPLATE.format(city=city, py=py, code=code, total=TOTALS[code])
        (ADIR / f"zj_{py}.py").write_text(body, encoding="utf-8")
        print("wrote", f"adapters/zj_{py}.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
