"""适配器：**泰州市·政民互动·留言选登（jpaas-jact）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe2.txt / city-js-taizhou-*.html）
 · 门户 `www.taizhou.gov.cn` 首页「留言选登」→
   `https://www.taizhou.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do?platformIid=YOSZfeTw2AKcbQaPTkHkJ`
   （`.do` 是门户 HTML 页；**真实数据接口**是去掉 `.do` 的 `front/find-mail-pub-list`）。
 · 列表：`GET /api-gateway/jpaas-jact-web-server/front/find-mail-pub-list?platformIid=<id>&pageNum=&pageSize=`
   → `{"count":3189,"data":[{iid,title,transactNo,submitDate,handleGroup,…}]}`。
 · 明细：`GET …/front/mail-pub-detail?iid=<iid>` → HTML 表格，标签
   `标题/内容/办件分类/办件编号/提交时间/处理状态/答复内容/答复部门/答复日期`。
   （⚠ 明细 **不是** JSON 接口 `find-transact-detail` —— 那个返回「无权限」。）
 · 样例：办件 SZ2026091800007「提取公积金」→ 市公积金中心答复（含 20 年/8 年政策口径）。
"""
from __future__ import annotations

from adapters._jpaas_jact_html_common import harvest_jpaas_html

SITE = {
    "key": "js-taizhou",
    "name": "泰州市·政民互动·留言选登（jpaas-jact）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.taizhou.gov.cn/api-gateway/jpaas-jact-web-server/front/"
             "mail-pub-list.do?platformIid=YOSZfeTw2AKcbQaPTkHkJ",
    "status": "ok",
    "note": "jpaas-jact：列表 JSON（count≈3189）+ 明细 HTML（mail-pub-detail?iid=）；"
            "标签 答复内容/答复部门/答复日期",
}

BASE = "https://www.taizhou.gov.cn"
# ⚠ 实测：门户链接写的是 `platformIid=`，但**列表接口只认 `platformUid=`**
#   （`platformIid` 会返回 `{"message":"参数设置为空","count":0}`）。
PLATFORM_KEY = "platformUid"
PLATFORM_VALUE = "YOSZfeTw2AKcbQaPTkHkJ"
REFERER = SITE["entry"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采泰州市「留言选登」（问题 + 答复原文）。"""
    return harvest_jpaas_html(fetch, SITE=SITE, base=BASE, platform_key=PLATFORM_KEY,
                              platform_value=PLATFORM_VALUE, referer=REFERER, limit=limit)
