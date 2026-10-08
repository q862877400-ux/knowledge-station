"""适配器：**湖南省公安厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-08 实测，证据 recon/hunan-dept-hunt.txt）
 · 与湖南省生态环境厅/应急管理厅**同一平台、同一接口**（mailList2ie），
   仅 `deptId` 不同；deptId 取自 `https://gat.hunan.gov.cn/gat/xhtml/js/hdjl_index.js`；
 · `deptId = 0b560b592c68489c98481813f9ea779d`；
 · 接口实测 total=5721（含未公开/办理中，实际可采的公开已答复条数以采集为准）。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-gat",
    "name": "湖南省公安厅",
    "kind": "api",
    "level": "province",
    "entry": "https://gat.hunan.gov.cn/",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=0b560b59…；实测 total=5721",
}

DEPT_ID = "0b560b592c68489c98481813f9ea779d"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
