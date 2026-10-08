"""适配器：**盐城市·政民互动·市长信箱（jact 平台，多 sysid）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-jact-scan.py 输出 / recon/city-js-probe2.txt）
 · 门户 `www.yancheng.gov.cn` 首页含 `jact/front/main.do?sysid=2`（该 sysid 是「依申请公开」，
   dataproxy 返回 totalRecord=0 —— **不能只看首页链接**）。
 · 按硬约束枚举 **sysid=1..120**，命中 22 个有数据的 sysid：
   `1(1865) 8(26) 13(148) 14(78) 15(109) 19(108) 20(95) 21(82) 23(46) 25(10) 29(253)
    31(26) 32(21) 37(1347) 38(661) 42(30) 54(584) 55(16) 56(34) 61(23) 65(77) 68(15)`
   —— **sysid=1 是「市长信箱」主信箱**，其余为各部门信箱。
 · 接口与山东 jact 同构（`_sd_jact.harvest_jact_sd`）：
   列表 `dataproxy_mailpublist.do`（**GET**，https 可用），明细 `mailpubdetail.do`。
   明细标签 `标题/内容/办件编号/提交时间/处理状态/回复单位/回复日期/内容回复`
   —— 命中 `_jact_common.LABEL_ALIASES` 默认别名。
 · 样例：办件 LM20260972204「了解物业服务相关的法律法规」→ 市住建局答复。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "js-yancheng",
    "name": "盐城市·政民互动·市长信箱（jact）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.yancheng.gov.cn/jact/front/mailpublist.do?sysid=1",
    "status": "ok",
    "note": "jact（https，GET 列表）；枚举 22 个 sysid，sysid=1 为市长信箱（≈1865）",
}

BASE = "https://www.yancheng.gov.cn"
# 枚举命中的 sysid（数字为枚举当日 totalRecord，采集时以接口为准）
SYSIDS = ["1", "37", "38", "54", "29", "13", "15", "19", "20", "21", "65",
          "14", "23", "56", "42", "8", "31", "61", "32", "55", "68", "25"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历盐城 jact 各 sysid，取已答复信件（问题 + 答复原文）。`limit` 为总数上限。"""
    out: list[dict] = []
    for sid in SYSIDS:
        if limit and len(out) >= limit:
            break
        rows = harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=sid,
                               list_method="GET",
                               limit=(limit - len(out)) if limit else None)
        for r in rows:                      # 基座默认口径按山东「信件公开」，本市改为市长信箱
            r["channel"] = "政民互动·市长信箱"
            r["extra"]["sysid"] = sid
        out.extend(rows)
    return out
