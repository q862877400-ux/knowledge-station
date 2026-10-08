"""适配器：**湖南省教育厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-08 实测，证据 recon/hunan-dept-hunt.txt）
 · 与湖南省生态环境厅/应急管理厅**同一平台、同一接口**（mailList2ie），
   仅 `deptId` 不同；deptId 取自 `https://jyt.hunan.gov.cn/jyt/xhtml/js/hdjl_index.js`；
 · `deptId = bcfc26b5b7764a9e86fe47f425bdbb6d`；
 · 接口实测 total=187（含未公开/办理中，实际可采的公开已答复条数以采集为准）。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-jyt",
    "name": "湖南省教育厅",
    "kind": "api",
    "level": "province",
    "entry": "https://jyt.hunan.gov.cn/jyt/sjyt/hdjl/index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=bcfc26b5…；实测 total=187",
}

DEPT_ID = "bcfc26b5b7764a9e86fe47f425bdbb6d"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
