"""适配器：**湖南省交通运输厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-08 实测，证据 recon/hunan-dept-hunt.txt）
 · 与湖南省生态环境厅/应急管理厅**同一平台、同一接口**（mailList2ie），
   仅 `deptId` 不同；deptId 取自 `https://jtt.hunan.gov.cn/jtt/xhtml/js/hdjl_index.js`；
 · `deptId = f850d2ed4760439c95f545bc4fdd2690`；
 · 接口实测 total=5991（含未公开/办理中，实际可采的公开已答复条数以采集为准）。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-jtt",
    "name": "湖南省交通运输厅",
    "kind": "api",
    "level": "province",
    "entry": "https://jtt.hunan.gov.cn/jtt/hdjl/zxft/zxft_1/index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=f850d2ed…；实测 total=5991",
}

DEPT_ID = "f850d2ed4760439c95f545bc4fdd2690"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
