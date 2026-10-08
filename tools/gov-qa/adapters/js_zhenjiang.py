"""适配器：**镇江市·政民互动·12345 在线·信件公示**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe3.txt + recon/city-js-zhenjiang-list.html）
 · 门户 `www.zhenjiang.gov.cn` 「12345 在线」→
   `https://www.zhenjiang.gov.cn/zhenjiang/12345zx/xjgs_list.shtml`（xjgs=信件公示）。
   页面 JS `/zhenjiang/xhtml/js/xjgs_list.js` 调 `POST /u/wlwzZhenjiang/ajaxlistForWeb12345`。
 · 列表：`POST /u/wlwzZhenjiang/ajaxlistForWeb12345`
     form `{keywords:"", year:"", type:"", currentPage:<n>, number:<m>}`
     → `{"code":"0","data":{"list":[{id, queryNumber, theme, createDate, replyDate,
        wlwzLetterType:{name}, wlwzType:{name}, state,…}], …}}`。
 · 明细：`POST /u/wlwzZhenjiang/show/<id>`（JS `/default/xhtml/js/xjgs_detail.js`）
     → `{"code":"0","data":{"wlwzLetter":{theme, content, queryNumber, createDateFormat,
        extend3Name(答复单位)}, "replyList":[{content(答复), createTimeFormat}]}}`。
 · 样例：编号 20261004162518010「经开区政务服务中心国庆是否放假」→ 官方答复。
"""
from __future__ import annotations

import time

SITE = {
    "key": "js-zhenjiang",
    "name": "镇江市·12345 在线·信件公示",
    "kind": "api",
    "level": "city",
    "entry": "https://www.zhenjiang.gov.cn/zhenjiang/12345zx/xjgs_list.shtml",
    "status": "ok",
    "note": "POST ajaxlistForWeb12345（列表）+ POST /u/wlwzZhenjiang/show/<id>（明细）",
}

BASE = "https://www.zhenjiang.gov.cn"
LIST_URL = BASE + "/u/wlwzZhenjiang/ajaxlistForWeb12345"
DETAIL_TPL = BASE + "/u/wlwzZhenjiang/show/{id}"
REFERER = SITE["entry"]
PAUSE = 1.5
PAGE_SIZE = 20


def _clean(html: str | None) -> str:
    import html as _h
    import re
    if not html:
        return ""
    return _h.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))).strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 400) -> list[dict]:
    """翻页取镇江 12345 信件公示（问题 + 答复原文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch.post(LIST_URL, data={"keywords": "", "year": "", "type": "",
                                           "currentPage": page, "number": PAGE_SIZE},
                           headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = (r.json() or {}).get("data") or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("list") or []
        if total is None:
            total = (d.get("total") or d.get("totalRow") or d.get("allRow")
                     or d.get("count"))
            print(f"    [{SITE['key']}] 总数={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            rid = str(it.get("id") or "").strip()
            if not rid or rid in seen:
                continue
            seen.add(rid)
            time.sleep(PAUSE)
            try:
                dr = fetch.post(DETAIL_TPL.format(id=rid), headers={"Referer": REFERER})
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {rid}：{type(e).__name__}（跳过）")
                continue
            letter = dd.get("wlwzLetter") or {}
            replies = dd.get("replyList") or []
            answer = _clean((replies[0] or {}).get("content")) if replies else ""
            if len(answer) < 10:
                continue
            title = (letter.get("theme") or it.get("theme") or "").strip()
            content = _clean(letter.get("content"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": rid,
                "url": f"{SITE['entry'].split('_list')[0]}_detail.shtml?id={rid}",
                "question": question,
                "answer": answer,
                "asked_at": letter.get("createDateFormat") or it.get("createDate") or None,
                "answered_at": (replies[0] or {}).get("createTimeFormat")
                               or it.get("replyDate") or None,
                "dept": (letter.get("extend3Name")
                         or ((it.get("wlwzLetterType") or {}).get("name")) or None),
                "channel": "12345·信件公示",
                "extra": {
                    "title": title,
                    "query_number": letter.get("queryNumber") or it.get("queryNumber"),
                    "letter_type": (it.get("wlwzLetterType") or {}).get("name"),
                    "platform": "镇江 wlwz",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
