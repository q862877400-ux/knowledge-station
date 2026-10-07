"""适配器：**湖南省生态环境厅**（湖南全省统一互动平台 hd.hunan.gov.cn）。

## 站点事实（2026-10-09 实测，证据 recon/hunan-verify.json）
 · 官网互动页 `https://sthjt.hunan.gov.cn/sthjt/hdjl/index.html` 是壳，
   列表由 `/sthjt/xhtml/js/hdjl_index.js` 调**全省统一平台**接口拉取；
 · `deptId = c0fc18f40e604da3a01460d02d731d45`（写死在该 JS 里）；
 · 平台口径 total=3830（含未公开/办理中，实际可采的公开已答复条数以采集为准）；
 · 抽样 100 条：100% 有答复、isPublish=1、状态=已办结；类型 咨询92/投诉6/感谢2。
"""
from __future__ import annotations

from adapters._hunan_hd_common import harvest_hunan

SITE = {
    "key": "hunan-st",
    "name": "湖南省生态环境厅",
    "kind": "api",
    "level": "province",
    "entry": "https://sthjt.hunan.gov.cn/sthjt/hdjl/index.html",
    "status": "ok",
    "note": "湖南统一互动平台 mailList2ie；deptId=c0fc18f4…；抽样答复覆盖率 100%",
}

DEPT_ID = "c0fc18f40e604da3a01460d02d731d45"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅问答（详见 _hunan_hd_common）。"""
    return harvest_hunan(fetch, SITE=SITE, DEPT_ID=DEPT_ID, limit=limit)
