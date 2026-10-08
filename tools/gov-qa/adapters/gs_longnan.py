"""适配器：**陇南市·市长信箱（龙讯 CMS，label 8888）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 陇南门户 `www.longnan.gov.cn` 的「政民互动 → 市长信箱」列表由龙讯 CMS 的
   label 接口输出 JSON：
     GET https://www.longnan.gov.cn/site/label/8888?labelName=messageBoardPageList
         &pageIndex=<p>&pageSize=14&siteId=4448177&columnId=4450039
         &action=singleList&isJson=true
     → JSON `{"typeList":[…],"page":{"data":[…],"total":415,"pageIndex":…}}`。
 · ⚠ 须先 `GET https://www.longnan.gov.cn/zmhd/szxx/index.html` 建立会话
   （否则接口可能报「标签ID不存在」）；实测列表 `page.total=415`。
 · ⚠ **分页语义**：请求 `pageIndex=N`（1 起）返回第 N 页（回显 `pageIndex=N-1`，0 起），
   逐页不重叠。
 · 列表字段：`messageBoardContent`（问题）、`replyVOList[]`（答复，`replyContent` 为 HTML）、
   `receiveUnitName`（答复单位）、`className`（类型）、`baseContentId`（详情 id）、
   `addDate` / `replyVOList[].replyDate`。
 · ★ **实测列表答复与详情页答复完全一致**（长度相同、互相包含）⇒ **只翻列表即可**，
   无需逐条取详情页 `/content/article/<baseContentId>`。
"""
from __future__ import annotations

import re
import time

HOST = "https://www.longnan.gov.cn"
INDEX = f"{HOST}/zmhd/szxx/index.html"
LIST_TPL = (f"{HOST}/site/label/8888?labelName=messageBoardPageList"
            "&pageIndex={p}&pageSize={n}&siteId=4448177&columnId=4450039"
            "&action=singleList&isJson=true")
PAGE_SIZE = 14
PAUSE = 1.5
TAG_RE = re.compile(r"<[^>]+>")

SITE = {
    "key": "gs-longnan",
    "name": "陇南市·市长信箱",
    "kind": "api",
    "level": "city",
    "entry": f"{HOST}/zmhd/szxx/index.html",
    "status": "ok",
    "note": "龙讯 CMS label 8888；须先取 index 建会话；列表答复即答复原文（与详情页一致）；total=415",
}


def clean(html: str | None) -> str:
    """去标签 + 压空白（答复正文是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻页取陇南市长信箱已答复留言（问题 + 答复全文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（可调用 = GET）。
    """
    # 建会话（拿 WAF/session cookie）
    fetch(INDEX, headers={"Referer": f"{HOST}/"})
    out: list[dict] = []
    total = None
    page = 1
    while True:
        url = LIST_TPL.format(p=page, n=PAGE_SIZE)
        try:
            r = fetch(url, headers={"Referer": INDEX})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            page_obj = (r.json() or {}).get("page") or {}
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        rows = page_obj.get("data") or []
        if total is None:
            total = page_obj.get("total")
            print(f"    [{SITE['key']}] total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            bcid = it.get("baseContentId")
            replies = it.get("replyVOList") or []
            answer = clean(" ".join((x or {}).get("replyContent") or "" for x in replies))
            if len(answer) < 10:            # 未答复/办理中，跳过
                continue
            dept = it.get("receiveUnitName")
            if not dept and replies:
                dept = (replies[0] or {}).get("receiveName")
            answered = None
            if replies:
                answered = (replies[0] or {}).get("replyDate") or it.get("replyDate")
            out.append({
                "source": SITE["key"],
                "id": str(bcid),
                "url": f"{HOST}/content/article/{bcid}",
                "question": clean(it.get("messageBoardContent")) or clean(it.get("title")),
                "answer": answer,
                "asked_at": it.get("addDate") or it.get("createDate") or None,
                "answered_at": answered,
                "dept": dept or None,
                "channel": "政民互动·市长信箱",
                "extra": {
                    "title": clean(it.get("title")),
                    "class_name": it.get("className"),
                    "doc_num": it.get("docNum"),
                    "deal_status": it.get("dealStatus"),
                    "platform": "longxun-cms",
                },
            })
        if total is not None and page * PAGE_SIZE >= int(total):
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
