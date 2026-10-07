"""适配器：**湖南省应急管理厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-07 实测，证据 recon/hunan-verify.json）
 · 与湖南省生态环境厅**同一平台、同一接口**，只是 `deptId` 不同
   （写死在 `https://yjt.hunan.gov.cn/yjt/xhtml/js/hdjl_index.js`）；
 · `deptId = 5c24769298304cac9387087d8dd21334`；
 · 抽样 100 条：100% 有答复、isPublish=1、状态=已办结；类型 咨询94/投诉5/感谢1。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-yj",
    "name": "湖南省应急管理厅",
    "kind": "api",
    "level": "province",
    "entry": "https://yjt.hunan.gov.cn/yjt/hdjl/hdjl_index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=5c247692…；抽样答复覆盖率 100%",
}

DEPT_ID = "5c24769298304cac9387087d8dd21334"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
