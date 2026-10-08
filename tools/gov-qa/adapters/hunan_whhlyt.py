"""适配器：**湖南省文化和旅游厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-08 实测，证据 recon/hunan-dept-hunt.txt）
 · 与湖南省生态环境厅/应急管理厅**同一平台、同一接口**（mailList2ie），
   仅 `deptId` 不同；deptId 取自 `https://whhlyt.hunan.gov.cn/whhlyt/xhtml/js/hdjl_index.js`；
 · `deptId = 4584f87ba0564414b45fe2c32835f68a`；
 · 接口实测 total=1189（含未公开/办理中，实际可采的公开已答复条数以采集为准）。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-whhlyt",
    "name": "湖南省文化和旅游厅",
    "kind": "api",
    "level": "province",
    "entry": "https://whhlyt.hunan.gov.cn/whhlyt/hdjl/index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=4584f87b…；实测 total=1189",
}

DEPT_ID = "4584f87ba0564414b45fe2c32835f68a"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
