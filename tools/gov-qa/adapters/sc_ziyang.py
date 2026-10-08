"""适配器：**资阳市·互动交流·书记市长信箱（数融 /api/mail）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe18~20.txt）
 · 互动栏目：`/zysrmzf/hdjl/pc/list.html`（政民互动），前端 `zmhd.js` 的
   `mailGetList(current,pageSize)` 调 `ajaxUrl.sr.hd.mail.list`。
 · `ajaxUrl` 常量在 `/default/libs/config.js` 展开为 **`/api/mail/list`**（列表）、
   **`/api/mail/detail`**（详情）—— 与自贡同款「数融」互动中间件。
 · 列表：`GET https://www.ziyang.gov.cn/api/mail/list`
     params: `tenantId=1817756538756743168`、`deptId=1817758019106979840`、
             `siteId=1823176537716752384`（=config.js userIdObj.zysrmzf.qdId）、
             `current`（页码,1 基）、`pagesize`、`sourceId=7`
   → JSON：`{"page":1,"pagesize":5,"total":87,"data":[{…}]}`
   条目字段：`id` 主键、`title` 标题、`submitTime` 来信、`finishedTime` 办结、
     `replyContent` **答复全文（HTML）**、`metadataList[].name=='答复单位'`、
     `mailState`/`state` 状态。
   ⚠ **列表已含 `replyContent`（答复全文），但不含问题正文**，问题正文在详情。
 · 详情：`GET https://www.ziyang.gov.cn/api/mail/detail?id=<id>` → **返回体即详情对象**
   （不在 `data` 里）：`content` 问题正文、`replyContent` 答复全文、`metadataList`。
 · 样例：id `2098316472604094464`「世界康养城市试点建议」→ 市民政局答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-ziyang",
    "name": "资阳市·互动交流·书记市长信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.ziyang.gov.cn/zysrmzf/hdjl/pc/list.html",
    "status": "ok",
    "note": "GET /api/mail/list（列表，自带答复）+ /api/mail/detail?id=（问题正文）；total≈87",
}

BASE = "https://www.ziyang.gov.cn"
LIST_URL = BASE + "/api/mail/list"
DETAIL_URL = BASE + "/api/mail/detail"
TENANT_ID = "1817756538756743168"
DEPT_ID = "1817758019106979840"
SITE_ID = "1823176537716752384"     # = config.js userIdObj.zysrmzf.qdId
SOURCE_ID = 7
REFERER = SITE["entry"]
PAUSE = 1.2
PAGE_SIZE = 20

_TAG = re.compile(r"<[^>]+>")


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def _dept(meta) -> str | None:
    for m in (meta or []):
        if isinstance(m, dict) and m.get("name") == "答复单位":
            v = (m.get("metadataValue") or "").strip()
            if v:
                return v
    return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取资阳书记市长信箱；列表自带答复，另取详情拿问题正文。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "tenantId": TENANT_ID, "deptId": DEPT_ID, "siteId": SITE_ID,
                "current": page, "pagesize": PAGE_SIZE, "sourceId": SOURCE_ID,
            }, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = r.json() or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("data") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            # 取详情拿问题正文（列表只有标题）
            content = ""
            dd: dict = {}
            try:
                dr = fetch(DETAIL_URL, params={"id": sid}, headers={"Referer": REFERER})
                dd = dr.json() or {}
                content = _clean(dd.get("content"))
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（仅用列表）")
            answer = _clean(it.get("replyContent") or dd.get("replyContent"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or dd.get("title") or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{BASE}/zysrmzf/mail/detail.html?id={sid}",
                "question": question,
                "answer": answer,
                "asked_at": (it.get("submitTime") or dd.get("submitTime") or None),
                "answered_at": (it.get("finishedTime") or dd.get("finishedTime") or None),
                "dept": _dept(it.get("metadataList")) or _dept(dd.get("metadataList")),
                "channel": "互动交流·书记市长信箱",
                "extra": {
                    "title": title,
                    "aim": dd.get("aimName"),
                    "mail_state": it.get("mailState"),
                    "platform": "资阳 数融 /api/mail（列表自带答复+详情问题正文）",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
