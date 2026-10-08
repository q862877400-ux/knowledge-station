"""适配器：**河北省数据和政务服务局 · 互动交流 · 留言公开**（EWB 平台接口型）。

## 形态（2026-10-08 实测，证据 recon/heb-hi-hunt.txt【二·C】/ recon/heb-adapters-probe.py）
入口 `http://szj.hebei.gov.cn/hdjl/006002/006002004/messageList.html`。
页面为「河北政务 webBuilder」（EWB）前端，全部数据走 XHR，服务端无渲染列表。

## 接口（三个都实测 HTTP 200）
 ① 匿名 token：`POST /EWB-FRONT/rest/getOauthInfoAction/getNoUserAccessToken`
      form 单字段 `params="{}"` → `custom.access_token` / `refresh_token`
 ② 列表：`POST /EWB-FRONT/rest/frontAppNotNeedLoginAction/getLetterListByCondition`
      **header `Authorization: Bearer <token>`**；form 单字段 `params=<JSON 串>`，其中
      `{siteGuid, subject, postName, replyContent, content, startTime, endTime,
        group, pageIndex(0 基), pageSize}`（搜索字段留空即可）
      → `custom.total=1043`，`custom.data[]={sequence, infoGuid, subject,
        postDate, handleDate, boxName, type, status}`
 ③ 明细：`POST .../getLetterDetail`，form `params={siteGuid, infoGuid}`
      → `custom.data={subject, content(问题), replycontent(答复 HTML),
        postdate, operatedate, rowguid, isFankui, fankui}`
  siteGuid = `645ad4ac-16b3-47d8-95bc-294a9052c6a2`（取自 `/js/webBuilderCommon.js` 的 siteInfo）

## ⚠ 三个坑（照着写，别踩）
 1. **必须 POST**：同 URL GET 返回 405。
 2. 参数放 **form 字段 `params=` 里塞 JSON 串**；把字段平铺、或改用 JSON body 都 400。
 3. 列表接口**必须带 Bearer token**（token 来自 ①）；缺 token 会被拒。

## EWB 可复用性
EWB 是河北政务通用中间件；若在其它站点发现 `siteGuid`，换 siteGuid 即可复用本引擎。
"""
from __future__ import annotations

import json
import re
import time

SITE = {
    "key": "heb-szj",
    "name": "河北省数据和政务服务局·留言公开",
    "kind": "api",
    "level": "province",
    "entry": "http://szj.hebei.gov.cn/hdjl/006002/006002004/messageList.html",
    "status": "ok",
    "note": "EWB 平台 POST 接口；token→列表→明细；实测 total=1043，答复含依据",
}

BASE = "http://szj.hebei.gov.cn"
API = BASE + "/EWB-FRONT/rest"
TOKEN_URL = API + "/getOauthInfoAction/getNoUserAccessToken"
LIST_URL = API + "/frontAppNotNeedLoginAction/getLetterListByCondition"
DETAIL_URL = API + "/frontAppNotNeedLoginAction/getLetterDetail"
SITE_GUID = "645ad4ac-16b3-47d8-95bc-294a9052c6a2"
PAGE_SIZE = 10
PAUSE = 1.5
TAG_RE = re.compile(r"<[^>]+>")


def _clean(html: str | None) -> str:
    """去标签 + 压空白（答复是 HTML 片段）。"""
    if not html:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", html)).strip()


def _post(fetch, url: str, payload: dict, token: str | None = None):
    """EWB 约定：POST + form 单字段 params=<JSON 串>（可带 Authorization）。"""
    headers = {"Authorization": "Bearer " + token} if token else None
    return fetch.post(url, data={"params": json.dumps(payload)}, headers=headers)


def _get_token(fetch) -> str:
    r = _post(fetch, TOKEN_URL, {})
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"token HTTP {getattr(r, 'status_code', '?')}")
    return ((r.json().get("custom") or {}).get("access_token") or "").strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """取匿名 token → 翻页列表 → 逐条取明细拿答复全文。"""
    out: list[dict] = []
    seen: set[str] = set()

    token = _get_token(fetch)
    if not token:
        print(f"    [{SITE['key']}] 未取到匿名 token（停）")
        return out
    print(f"    [{SITE['key']}] token ok")

    total = None
    for page in range(max_pages):
        if limit and len(out) >= limit:
            break
        if page:
            time.sleep(PAUSE)
        payload = {"siteGuid": SITE_GUID, "subject": "", "postName": "",
                   "replyContent": "", "content": "", "startTime": "", "endTime": "",
                   "group": "", "pageIndex": page, "pageSize": PAGE_SIZE}
        r = _post(fetch, LIST_URL, payload, token)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        custom = r.json().get("custom") or {}
        rows = custom.get("data") or []
        if total is None:
            total = custom.get("total")
            print(f"    [{SITE['key']}] 留言公开总数 total={total}")
        if not rows:
            break
        fresh = 0
        for it in rows:
            if limit and len(out) >= limit:
                return out[:limit]
            guid = str(it.get("infoGuid") or "").strip()
            if not guid or guid in seen:
                continue
            seen.add(guid)
            time.sleep(PAUSE)
            dr = _post(fetch, DETAIL_URL,
                       {"siteGuid": SITE_GUID, "infoGuid": guid}, token)
            data = ((dr.json().get("custom") or {}).get("data") or {}) \
                if getattr(dr, "status_code", 0) == 200 else {}
            question = _clean(data.get("content")) or _clean(it.get("subject"))
            answer = _clean(data.get("replycontent"))
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": guid,
                "url": f"{BASE}/messageDetail.html?infoGuid={guid}",
                "question": question,
                "answer": answer,
                "asked_at": (data.get("postdate") or it.get("postDate") or None),
                "answered_at": (data.get("operatedate") or it.get("handleDate") or None),
                "dept": None,
                "channel": "互动交流·留言公开",
                "extra": {
                    "title": _clean(data.get("subject") or it.get("subject")),
                    "box_name": it.get("boxName"),
                    "msg_type": it.get("type"),
                    "platform": "EWB(河北政务webBuilder)",
                    "site_guid": SITE_GUID,
                    "answer_kind": "办理答复（留言公开，常引政策文号）",
                },
            })
            fresh += 1
        print(f"    [{SITE['key']}] 第 {page + 1} 页：{len(rows)} 条，新增 {fresh}")
        if total and (page + 1) * PAGE_SIZE >= int(total):
            break
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
