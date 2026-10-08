"""生成四川 20 个市州的「省政务服务网·政民互动」薄适配器（共用 `_sczwfw_common`）。

背景：四川政务服务网政民互动按 `areaCode`（12 位区划码）过滤，除成都外 20 市州
仍有 **7,419 条净增量**（与各市本地门户**不重叠**）。见 `adapters/_sczwfw_common.py`。

key 用 `sc-<拼音>-zwfw`（**加 `-zwfw` 后缀**）以与本地门户源 `sc-<拼音>` 区分
（两套源 id 空间不同，不能混在一个 source 里）。

用法：python recon/gen-sc-zwfw-city-adapters.py
输出：adapters/sc_<拼音>_zwfw.py × 20
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
ADIR = HERE.parent / "adapters"

# (城市全名, 拼音, 12 位 areaCode, 净增量) —— 总量 2026-10-09 实测复核 = 7,419
CITIES = [
    ("自贡市", "zigong", "510300000000", 58),
    ("攀枝花市", "panzhihua", "510400000000", 1292),
    ("泸州市", "luzhou", "510500000000", 454),
    ("德阳市", "deyang", "510600000000", 268),
    ("绵阳市", "mianyang", "510700000000", 708),
    ("广元市", "guangyuan", "510800000000", 821),
    ("遂宁市", "suining", "510900000000", 209),
    ("内江市", "neijiang", "511000000000", 721),
    ("乐山市", "leshan", "511100000000", 68),
    ("南充市", "nanchong", "511300000000", 633),
    ("眉山市", "meishan", "511400000000", 308),
    ("宜宾市", "yibin", "511500000000", 203),
    ("广安市", "guangan", "511600000000", 536),
    ("达州市", "dazhou", "511700000000", 148),
    ("雅安市", "yaan", "511800000000", 237),
    ("巴中市", "bazhong", "511900000000", 72),
    ("资阳市", "ziyang", "512000000000", 289),
    ("阿坝藏族羌族自治州", "aba", "513200000000", 119),
    ("甘孜藏族自治州", "ganzi", "513300000000", 179),
    ("凉山彝族自治州", "liangshan", "513400000000", 96),
]

TEMPLATE = '''"""适配器：**{city}·政民互动（四川政务服务网平台，areaCode={code}）**。

## 站点事实
四川政务服务网「政民互动」按 `areaCode` 过滤，**{city}**（`areaCode={code}`）
净增量约 **{total} 条**（与本地门户源不重叠）。基座、列表/详情接口、
「不带 encrypt 头即回明文」的绕行细节见 `adapters/_sczwfw_common.py`。

## 为什么 key 带 `-zwfw` 后缀
本省门户（`sc-{pinyin}`）与省平台（本适配器）是**两套源**、id 空间不同，
用 `sc-{pinyin}-zwfw` 避免与本地源冲突。
"""
from __future__ import annotations

from adapters._sczwfw_common import harvest_sczwfw

SITE = {{
    "key": "sc-{pinyin}-zwfw",
    "name": "{city}·政民互动（四川政务服务网）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/interact.html?areaCode={code}",
    "status": "ok",
    "note": "四川政务服务网政民互动 areaCode={code}，净增量约 {total} 条（咨询10/建议15/投诉20）",
}}

AREA_CODE = "{code}"
CITY = "{city}"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    return harvest_sczwfw(fetch, source=SITE["key"], area_code=AREA_CODE, city=CITY, limit=limit)
'''


def main() -> int:
    for city, pinyin, code, total in CITIES:
        path = ADIR / f"sc_{pinyin}_zwfw.py"
        path.write_text(TEMPLATE.format(city=city, pinyin=pinyin, code=code, total=total),
                        encoding="utf-8")
        print(f"wrote {path.name}")
    print(f"共 {len(CITIES)} 个，净增量合计 {sum(c[3] for c in CITIES)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
