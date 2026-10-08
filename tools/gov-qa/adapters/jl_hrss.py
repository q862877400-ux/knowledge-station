"""适配器：**吉林省人力资源社会保障厅·厅长信箱（问政列表）**——IGI 平台，带省/市/区三级归属。

## 站点形态（2026-10-08 实探，证据 recon/hrss-home.html）
 · 首页 JS 直接写出接口参数：`var siteId = 117; var appId = 96; … groupId=170`（注释「问政列表」），
   接口基址是全省共用的海云平台 `https://haiyun.jl.gov.cn/IGI`（与吉林自然资源厅同一厂商平台）。
 · ⚠ 同页另有 `appId=575ecd…`（登录 iframe 的鉴权密钥）——正则粗抠会把 575 当 appId，
   实测该组合 `n=0`；**真实信箱参数是 appId=96，各部门靠 groupId 区分**
   （自然资源厅 172 / 人社厅 170 / 交通运输厅 159）。
 · 实测 `siteId=117&appId=96&groupId=170` 返回 200，记录含
   `PROVINCE=吉林省 / CITY=延边朝鲜族自治州 / AREA=延吉市`（**三级**）。
 · ⚠ 须带 `Referer`（该厅站点），否则 403。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "jl-hrss",
    "name": "吉林省人力资源社会保障厅·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://hrss.jl.gov.cn/",
    "status": "ok",
    "note": "海云平台（siteId=117, appId=96, groupId=170）；带省/市/区三级归属；须带 Referer",
}

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
GROUP_ID = "170"
REFERER = "https://hrss.jl.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 公共基座采吉林人社厅长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
