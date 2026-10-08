"""适配器：**广西壮族自治区·自治区人民政府信箱（留言选登）**——IGI 平台（与宁夏/山西/贵州/吉林同族）。

## 站点事实（2026-10-08 实测，证据 recon/xj-xz-sd-gx-qh-hunt.txt 【广西】）
 · 门户 `www.gxzf.gov.cn` 的「政民互动 → @自治区人民政府」`/hdjl/mailbox/index.shtml`
   （另有「留言选登」`/hdjl/mailbox/`、「桂在问」知识库 `/hdjl/guizaiwen/`）；
 · ⚠ **旧结论「广西 ConnectError」是 https 失败所致**：`https://www.gxzf.gov.cn` 证书
   主机名不匹配（`CERTIFICATE_VERIFY_FAILED`），而 **http 明文 200 可达**。
 · 留言列表由 `/jsq/2023gxzf/api_mailbox.js` 的 `getMailboxList(3, 133, ...)` 拉取，
   接口与 `_igi_common.py` **完全同构**（`/IGI/nbhd/openGovmsgbox.do`），**零改造复用**：
   · base `http://www.gxzf.gov.cn/IGI`
   · siteId=3, appId=133
   · **须带 Referer** `http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml`
 · 实测列表 200（`datas.data[]`），明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复
   （样例：洋浦星小区外五里亭西一巷车辆乱停 → 南宁市公安局交通管理支队答复）。
 · ★ **列表带 PROVINCE/CITY/AREA 三级归属**（如「广西壮族自治区 / 南宁市 / 西乡塘区」）
   ⇒ 与宁夏同为本模块**仅有的两条能扩「县」的通道**。
   ⚠ 新落 IGI 适配器**务必同步** `recon/coverage-matrix.py` 的 `PROVINCE_PREFIX`（加 `gx-`）。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gx-mailbox",
    "name": "广西壮族自治区·自治区人民政府信箱",
    "kind": "api",
    "level": "province",
    "entry": "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml",
    "status": "ok",
    "note": "IGI 平台（siteId=3, appId=133）；带省/市/区三级归属；须带 Referer；http 可达（https 证书不匹配）",
}

BASE = "http://www.gxzf.gov.cn/IGI"
SITE_ID = "3"
APP_ID = "133"
GROUP_ID = None
REFERER = "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采广西自治区人民政府信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
