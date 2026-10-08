"""适配器：**广安市·互动交流·书记市长信箱（数融 /api/mail）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe18~20.txt）
 · 互动栏目：`/gasrmzfw/hdjl/pc/list.html`（政民互动），前端
   `/gasrmzfw/pc2023/js/basehd/config.js` 里 `ajaxUrl.sr.hd.mail.list` =
   **`/api/mail/list`**、`detail` = **`/api/mail/detail`** —— 与自贡/资阳同款「数融」。
 · 列表：`GET https://www.guang-an.gov.cn/api/mail/list`
     params: `tenantId=1714599166008037376`、`siteId=1716750630131666944`（=config.js useObj.siteId）、
             `current`（页码,1 基）、`pagesize`、`sourceId=`
   → JSON：`{"page":1,"pagesize":5,"total":16,"data":[{…}]}`
   条目字段：`id` 主键、`title` 标题、`submitTime` 来信、`finishedTime` 办结、
     `replyContent` **答复全文（HTML）**、`serialNumber` 来信编号、`mailState`/`state`。
   ⚠ 列表 `replyContent` 可能为空壳（`<p>&nbsp;</p>`），问题正文需取详情。
 · 详情：`GET https://www.guang-an.gov.cn/api/mail/detail?id=<id>` → **返回体即详情对象**
   （不在 `data` 里）：`content` 问题正文、`replyContent` 答复全文、`aimName`、`metadataList`。
 · ⚠ `siteId12345=1692547633652551680`（config.js 的 12345 渠道）实测 `/api/mail/list` 恒
   `{"total":0}`，故只采主信箱 `siteId=1716750630131666944`。
 · 样例：id `2071049373198114816`「小轿车闯红灯」→ 已答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-guangan",
    "name": "广安市·互动交流·书记市长信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.guang-an.gov.cn/gasrmzfw/hdjl/pc/list.html",
    "status": "ok",
    "note": "GET /api/mail/list（列表）+ /api/mail/detail?id=（问题正文+答复）；total≈16",
}

BASE = "https://www.guang-an.gov.cn"
LIST_URL = BASE + "/api/mail/list"
DETAIL_URL = BASE + "/api/mail/detail"
TENANT_ID = "1714599166008037376"
SITE_ID = "1716750630131666944"     # = config.js useObj.siteId
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
    """翻页取广安书记市长信箱；逐条取详情拿问题正文+答复。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "tenantId": TENANT_ID, "siteId": SITE_ID,
                "current": page, "pagesize": PAGE_SIZE, "sourceId": "",
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
            dd: dict = {}
            try:
                dr = fetch(DETAIL_URL, params={"id": sid}, headers={"Referer": REFERER})
                dd = dr.json() or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            answer = _clean(dd.get("replyContent") or it.get("replyContent"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or dd.get("title") or "").strip()
            content = _clean(dd.get("content"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{BASE}/gasrmzfw/mail/detail.html?id={sid}",
                "question": question,
                "answer": answer,
                "asked_at": (it.get("submitTime") or dd.get("submitTime") or None),
                "answered_at": (it.get("finishedTime") or dd.get("finishedTime") or None),
                "dept": _dept(dd.get("metadataList")) or _dept(it.get("metadataList")),
                "channel": "互动交流·书记市长信箱",
                "extra": {
                    "title": title,
                    "aim": dd.get("aimName"),
                    "serial_number": it.get("serialNumber"),
                    "mail_state": it.get("mailState"),
                    "platform": "广安 数融 /api/mail（列表+详情）",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
