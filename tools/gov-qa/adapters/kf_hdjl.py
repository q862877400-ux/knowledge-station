"""适配器：**开封市·政民互动·信件公开**（`/uapi/mail/`，河南第 5 个可采市级源）。

## 站点事实（2026-10-10 实测）

配置与接口**全部从 `config.js` 抄到**（不是猜的）：

```js
var ajaxUrl = { sr: { hd: { mail: {
    list:   '/uapi/mail/list',      // 获取信件列表
    detail: '/uapi/mail/detail',    // 获取信件详情
}}}}
var defaultConfig = { userIdObj: {
    tenantId: '1735586219994349568', deptId: '1735588321223213056',
    siteId:   '1735601820788891648', qdId:   '1736686125818318848' }}
```

⚠⚠ **三个必须踩对的点**（第一版全错 ⇒ 返回 `total:0`，**看起来像"没有数据"**）：

1. `siteId` 参数传的是 **`qdId`**（`1736686125818318848`），**不是** `userIdObj.siteId`
   —— 从 `zmhd.js` 的 `getMailList` 抄到：
   `data = {current, pagesize, tenantId, siteId: defaultConfig.userIdObj.qdId, publicationFlag: 1}`
2. 必须带 **`publicationFlag: 1`**（只取"已公开"的）
3. 分页参数叫 **`current` / `pagesize`**（不是 page/size）

响应：`{"total":789,"page":1,"pagesize":10,"data":[{id,title,submitTime,…}]}`

**详情** `GET /uapi/mail/detail?id=<id>&tenantId=<tid>` 返回 21 个字段，含：
- `content` —— **提问正文**（HTML）
- `replyContent` —— **答复正文**（HTML）
- `submitTime` / `finishedTime` —— 提交/办结时间
- `aimName` —— 类型（如「咨询」）
- `metadataList` —— 答复单位等（JSON 字符串）

⇒ **一次调用拿全问答**，不需要额外请求。

## 质量（铁律第 6 条）

抽 3 条：`content` 149 字、`replyContent` 416 字（**答复非空**，含具体处理过程）。

## ⚠ 一个被否掉的入口

`/uapi/mail/list` 不带 `publicationFlag` 时也返回 200，但 **`total:0`**
⇒ 必须照 `zmhd.js` 的原样传参。
"""
from __future__ import annotations

import html as _html
import json
import re
import time

SITE = {
    "key": "kf-hdjl",
    "name": "开封市·政民互动·信件公开",
    "kind": "api",
    "level": "city",
    "region": "开封市",
    "entry": "https://www.kaifeng.gov.cn/kfsrmzfwz/hdjl/pc/list.html",
    "status": "ok",
    "note": "GET /uapi/mail/list（current/pagesize/tenantId/siteId=qdId/publicationFlag=1）"
            "+ /uapi/mail/detail?id=&tenantId=；响应自带 content+replyContent；实测 total=789",
}

BASE = "https://www.kaifeng.gov.cn"
LIST_API = BASE + "/uapi/mail/list"
DETAIL_API = BASE + "/uapi/mail/detail"
REFERER = BASE + "/kfsrmzfwz/hdjl/pc/list.html"
#: 从 `config.js` 的 `defaultConfig.userIdObj` 抄到
TENANT_ID = "1735586219994349568"
#: ⚠ 列表的 `siteId` 参数用的是 **`qdId`**，不是 `userIdObj.siteId`（见 `zmhd.js::getMailList`）
QD_ID = "1736686125818318848"
PAGE_SIZE = 50
PAUSE = 0.4
MAX_PAGES = 200

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
_BR = re.compile(r"(?i)<br\s*/?>")
_P = re.compile(r"(?i)</p>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s) -> str:
    if not s:
        return ""
    s = _COMMENT.sub(" ", str(s))
    s = _BR.sub("\n", s)
    s = _P.sub("\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _dept_of(metadata_list) -> str | None:
    """`metadataList` 是 JSON 字符串，找 `name == '答复单位'` 的那条。"""
    if not metadata_list:
        return None
    try:
        arr = json.loads(metadata_list) if isinstance(metadata_list, str) else metadata_list
    except Exception:                                                   # noqa: BLE001
        return None
    if not isinstance(arr, list):
        return None
    for it in arr:
        if isinstance(it, dict) and str(it.get("name") or "") == "答复单位":
            v = it.get("value") or it.get("data")
            if v:
                return _real(v)
    return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """翻列表（GET JSON）+ 逐条取详情。

    ⚠ 本接口是 **GET**，但参数多且必须原样照抄；用传入的 `fetch` 即可
    （它是 `client.get` 的包装）。

    ⚠⚠ **逐条取详情必须打进度点**（本模块为此踩过 5 次坑）。
    """
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    n_detail = n_fail = 0
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_API, params={"current": page, "pagesize": PAGE_SIZE,
                                        "tenantId": TENANT_ID, "siteId": QD_ID,
                                        "publicationFlag": 1},
                      headers={"Referer": REFERER})
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r,'status_code','?')}（停）")
            break
        try:
            d = r.json()
        except Exception:                                               # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] total={total}", flush=True)
        rows = d.get("data") or []
        print(f"    [{SITE['key']}] 列表第 {page} 页：{len(rows)} 条", flush=True)
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                break
            mid = str(it.get("id") or "")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            det = {}
            try:
                dr = fetch(DETAIL_API, params={"id": mid, "tenantId": TENANT_ID},
                           headers={"Referer": REFERER})
                if getattr(dr, "status_code", 0) == 200:
                    det = dr.json() or {}
            except Exception:                                           # noqa: BLE001
                det = {}
            n_detail += 1
            ans = _real(det.get("replyContent"))
            if not ans:
                n_fail += 1
                if n_detail % 25 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                          f"（无答复 {n_fail}）", flush=True)
                time.sleep(PAUSE)
                continue
            if n_detail % 25 == 0:
                print(f"    [{SITE['key']}] 明细进度 {n_detail}"
                      f"（无答复 {n_fail}）", flush=True)
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": f"{BASE}/kfsrmzfwz/mail/detail.html?id={mid}",
                "question": _real(det.get("content")) or _real(it.get("title")),
                "answer": ans,
                "asked_at": _real(det.get("submitTime")) or _real(it.get("submitTime")) or None,
                "answered_at": _real(det.get("finishedTime")) or None,
                "dept": _dept_of(det.get("metadataList")),
                "channel": "信件公开",
                "extra": {
                    "title": _real(det.get("title")) or _real(it.get("title")),
                    "msg_type": _real(det.get("aimName")) or None,
                    "mail_state": det.get("mailState") or it.get("mailState"),
                    "case_state": det.get("state") or it.get("state"),
                    "problem_area": _real(det.get("problemArea")) or None,
                    "platform": "开封市政府门户（uapi/mail）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
