"""适配器：**陕西省·我向省长说句话·留言选登（门户 IGI 平台）**——IGI 中间件。

## 站点事实（2026-10-08 实测，证据 recon/waf-igi-sites.json 【shaanxi】）
 · 门户 `www.shaanxi.gov.cn`「政民互动 → 我向省长说句话 → 留言选登」
   （`/hd/wxszsjh/lyxd/`）的留言列表由 **IGI 平台**驱动，与 `_igi_common.py` 同构。
 · ★ 与既有 `sn-lyxd`（陕西省·我向省长说句话·留言选登，184 条）**是同名栏目的另一条通道**：
   本适配器走 IGI 开放接口，**实测 totalResults = 4097 条**，是原静态线的 20 倍以上。
 · 参数：
   · base `http://www.shaanxi.gov.cn/IGI`
   · siteId=**15**（枚举 1..60 唯一命中；order=1、appId 留空）
   · **须带 Referer** `http://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/`
   · ⚠ 服务端会 **301 跳到 https**，故客户端须开 `follow_redirects`（harvest.py 的
     httpx.Client 已开）。
 · 明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文，**质量极高**：
   样例「关于市政工程中 SP-Ⅳ 拉森钢板桩租赁定额费用单价的咨询」→
   答复引《陕西省市政工程消耗量定额》（2025）与《陕西省市政工程基价表》（2025）附录。
   ⇒ 典型的「可当考卷」素材。

## 教训
同一栏目可能有**多条并行通道**（静态列表 + IGI 接口）。发现栏目后可再试 `/IGI/`，
往往能拿到比静态线多得多的数据。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "sn-igi",
    "name": "陕西省·我向省长说句话（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/",
    "status": "ok",
    "note": "IGI 平台（www.shaanxi.gov.cn/IGI），siteId=15，totalResults=4097；"
            "须带 Referer；服务端 301 跳 https（须 follow_redirects）",
}

BASE = "http://www.shaanxi.gov.cn/IGI"
REFERER = "http://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/"
APP_ID = ""
GROUP_ID = None
SITE_ID = "15"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采陕西省门户 IGI 留言选登（含答复原文）。

    **可反复跑、逐轮推进**：先读已落盘 id 跳过（`limit` = 本轮新增条数）。
    陕西 totalResults=4097，一次性跑完要 ~2 小时 ⇒ 按 800/轮分块推进，每轮跑完即落盘。
    """
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit, max_pages=300,
                       skip_ids=existing_ids(SITE["key"]))
