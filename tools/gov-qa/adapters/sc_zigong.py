"""适配器：**自贡市·互动交流·市长信箱/来信选登（数融 /api/mail）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe7~13.txt）
 · ⚠ **自贡门户真实域名是 `www.zg.gov.cn`**（`www.zigong.gov.cn` 502/无法解析）。
 · 互动栏目：`/zgsrmzf/hdjl/pc/list.html`（互动交流）→ 子栏目
   `/zgsrmzf/szxx/pc/list.html`（市长信箱，会 302 到首个子栏目）
   `/zgsrmzf/lxxd/pc/list.html`（来信选登）、`/zgsrmzf/bmxx/pc/list.html`（部门信箱）、
   `/zgsrmzf/fwrx12345/pc/list.html`（12345 服务热线）。
 · 前端 `mail_list.js` 调 `ajaxUrl.sr.hd.mail.list`，该常量在 `/default/libs/config.js` 展开为
   **`/api/mail/openMailList`**（列表）、**`/api/mail/detail`**（详情）。
 · 列表：`GET https://www.zg.gov.cn/api/mail/openMailList`
     params: `tenantId=1889226377685270528`、`siteId=1892518439427633152`（=渠道 qdId）、
             `current`（页码,1 基）、`pagesize`、`sourceId=`
   → JSON：`{"page":1,"pagesize":10,"total":213,"data":[{…}]}`
   条目字段：`id` 主键、`title` 标题、`submitTime` 来信、`finishedTime` 办结、
     `metadataList[].name=='回复单位'` 答复单位、`mailState`/`state` 状态。
   ⚠ **列表不含答复正文**，需逐条取详情。
 · 详情：`GET https://www.zg.gov.cn/api/mail/detail?id=<id>` → **返回体即详情对象**
   （不在 `data` 里）：`content` 问题正文（HTML）、`replyContent` **答复全文（HTML）**、
     `title`、`submitTime`、`finishedTime`、`aimName`（类型：建议/咨询…）、`metadataList`。
 · 样例：id `2085029155435298816`「共享单车」→ 自贡市城市管理行政执法局答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-zigong",
    "name": "自贡市·互动交流·市长信箱（来信选登）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.zg.gov.cn/zgsrmzf/lxxd/pc/list.html",
    "status": "ok",
    "note": "GET /api/mail/openMailList（列表）+ /api/mail/detail?id=（详情含答复）；total≈213",
}

BASE = "https://www.zg.gov.cn"
LIST_URL = BASE + "/api/mail/openMailList"
DETAIL_URL = BASE + "/api/mail/detail"
TENANT_ID = "1889226377685270528"
SITE_ID = "1892518439427633152"     # = config.js userIdObj.zgsrmzf.qdId
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
        if isinstance(m, dict) and m.get("name") == "回复单位":
            v = (m.get("metadataValue") or "").strip()
            if v:
                return v
    return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取自贡来信选登；列表不含答复，逐条取详情。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "tenantId": TENANT_ID, "siteId": SITE_ID, "current": page,
                "pagesize": PAGE_SIZE, "sourceId": "",
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
            # 逐条取详情拿答复全文
            try:
                dr = fetch(DETAIL_URL, params={"id": sid},
                           headers={"Referer": REFERER})
                dd = dr.json() or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            answer = _clean(dd.get("replyContent"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or dd.get("title") or "").strip()
            content = _clean(dd.get("content"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": f"{BASE}/zgsrmzf/mail/detail.html?id={sid}",
                "question": question,
                "answer": answer,
                "asked_at": (it.get("submitTime") or dd.get("submitTime") or None),
                "answered_at": (it.get("finishedTime") or dd.get("finishedTime") or None),
                "dept": _dept(it.get("metadataList")) or _dept(dd.get("metadataList")),
                "channel": "互动交流·市长信箱·来信选登",
                "extra": {
                    "title": title,
                    "aim": dd.get("aimName"),
                    "mail_state": it.get("mailState"),
                    "platform": "自贡 数融 /api/mail（列表+详情）",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
