"""适配器：**湖南省卫生健康委员会**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-08 实测，证据 recon/hunan-dept-hunt.txt）
 · 与湖南省生态环境厅/应急管理厅**同一平台、同一接口**（mailList2ie），
   仅 `deptId` 不同；deptId 取自 `https://wjw.hunan.gov.cn/wjw/xhtml/js/hdjl_index.js`；
 · `deptId = b9cf0c9e8d9f4a959a4a048a5286fee1`；
 · 接口实测 total=100（含未公开/办理中，实际可采的公开已答复条数以采集为准）。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-wjw",
    "name": "湖南省卫生健康委员会",
    "kind": "api",
    "level": "province",
    "entry": "https://wjw.hunan.gov.cn/wjw/hdjl/index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=b9cf0c9e…；实测 total=100",
}

DEPT_ID = "b9cf0c9e8d9f4a959a4a048a5286fee1"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
