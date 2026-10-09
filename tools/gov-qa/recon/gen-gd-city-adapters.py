"""从 `probe-gd-city-hdjlpt.py` 的实测结果，生成**广东地级市** hdjlpt 薄壳适配器。

## 为什么是这 8 个

`recon/probe-city-middleware.py` 归类出 **18 个市带 `广东hdjlpt` 指纹**，
但**指纹 ≠ 可采** —— `recon/probe-gd-city-hdjlpt.py` 逐个实测：
**只有 8 个市的 `/hdjlpt/letter/pubList` 真返回非空答复正文**。

| 市 | 入口 | 年窗 total |
|---|---|---|
| 深圳市 | http://www.shenzhen.gov.cn | **5,493** |
| 茂名市 | http://www.maoming.gov.cn | 68 |
| 潮州市 | https://www.chaozhou.gov.cn | 46 |
| 湛江市 | https://www.zhanjiang.gov.cn | 45 |
| 阳江市 | https://www.yangjiang.gov.cn | 35 |
| 汕尾市 | https://www.shanwei.gov.cn | 27 |
| 肇庆市 | https://www.zhaoqing.gov.cn | 17 |
| 云浮市 | https://www.yunfu.gov.cn | 16 |

**判死 10 个**（落地页 404 / 502，即该市未在自己域名下部署 hdjlpt）：
东莞 · 中山 · 佛山 · 惠州 · 汕头 · 江门 · 河源 · 珠海 · 韶关 · 常德（湖南，误报）

## 用法

```bash
.venv/Scripts/python.exe tools/gov-qa/recon/gen-gd-city-adapters.py
# 打印要手工插进 adapters/__init__.py 的 8 行（**不自动改共享文件**）
```
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTERS_DIR = HERE.parent / "adapters"

#: (key 后缀, 市名, base, 年窗 total) —— 只放**实测能出数据**的
CITIES = [
    ("shenzhen", "深圳市", "http://www.shenzhen.gov.cn", 5493),
    ("maoming", "茂名市", "http://www.maoming.gov.cn", 68),
    ("jieyang", "揭阳市", "http://www.jieyang.gov.cn", 53),
    ("chaozhou", "潮州市", "https://www.chaozhou.gov.cn", 46),
    ("zhanjiang", "湛江市", "https://www.zhanjiang.gov.cn", 45),
    ("yangjiang", "阳江市", "https://www.yangjiang.gov.cn", 35),
    ("shanwei", "汕尾市", "https://www.shanwei.gov.cn", 27),
    ("zhaoqing", "肇庆市", "https://www.zhaoqing.gov.cn", 17),
    ("yunfu", "云浮市", "https://www.yunfu.gov.cn", 16),
]

TEMPLATE = '''"""适配器：**{city}人民政府·政民互动**（广东 hdjlpt 同款平台）。

2026-10-10 实测：`{base}/hdjlpt/letter/pubList` 返回非空答复正文
（年窗 total={total}）。引擎见 `_gd_hdjlpt_common.py`（Laravel CSRF 握手）。
生成器 `recon/gen-gd-city-adapters.py`（勿手改本壳）。

⚠ 广东地级市**各自部署** hdjlpt，数据互不相通 ⇒ 按域名各采各的。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {{
    "key": "{key}",
    "name": "{city}人民政府·政民互动（hdjlpt）",
    "kind": "api",
    "level": "city",
    "entry": "{base}/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；实测年窗 total={total}",
}}

BASE = "{base}"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该市留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
'''


def main() -> int:
    lines = []
    for suffix, city, base, total in CITIES:
        key = f"gd-{suffix}"
        path = ADAPTERS_DIR / f"gd_{suffix}.py"
        path.write_text(TEMPLATE.format(city=city, key=key, base=base,
                                        total=total), encoding="utf-8")
        lines.append(f'    "{key}": "adapters.gd_{suffix}",  '
                     f'# {city}·政民互动（hdjlpt，年窗 {total}）')
        print(f"  + {path.name}  ({key} / {city} / {total})")

    print("\n请把这 8 行插进 adapters/__init__.py 的 ADAPTERS 字典"
          "（`gd-dva` 那行之后）：\n")
    for ln in lines:
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
