"""生成 rd_*.py 适配器模块（人大·法规草案征求意见）。一次性脚本。"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapters.rd_common import SITES  # noqa: E402

TPL = '''"""适配器：**{name}**（人大系统·法规草案征求意见）。

由 `rd_common.harvest_rd` 驱动；本模块只声明 SITE。
⚠ 体裁是「草案全文 + 征求意见公告」，**不是问答** ⇒ 记录带
   `extra.content_kind = "立法征求意见"` 以与问答语料区分。
"""
from __future__ import annotations

from adapters.rd_common import SITES, harvest_rd

SITE = {{
    "key": "{key}",
    "name": "{name}",
    "kind": "html",
    "level": "province",
    "entry": "{entry}",
    "status": "ok",
    "note": "人大·法规草案征求意见（列表+详情，正文为草案全文）",
}}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 30) -> list[dict]:
    return harvest_rd(fetch, site_key=SITE["key"], limit=limit, max_pages=max_pages)
'''

here = Path(__file__).resolve().parent.parent / "adapters"   # ← adapters/ 而非 recon/
for key, s in SITES.items():
    path = here / (key.replace("-", "_") + ".py")
    path.write_text(
        TPL.format(key=key, name=s["name"], entry=s["entry"]),
        encoding="utf-8",
    )
    print(f"写入 {path.name}")
