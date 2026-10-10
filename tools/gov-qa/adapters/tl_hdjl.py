"""适配器：**铜陵市·政民互动·信件公开**（`/api/mail/`，安徽第 1 个可采市级源）。

## 站点事实（2026-10-10 实测）

铜陵用的是与**开封同一套**"政务互动平台"，但**接口前缀与配置字段名不同**：

| | 开封 | 铜陵 |
|---|---|---|
| 列表 | `/uapi/mail/list`（**带 `u`**）| `/api/mail/list`（**不带 `u`**）|
| 详情 | `/uapi/mail/detail` | `/api/mail/detail` |
| 配置 | `defaultConfig.userIdObj` | **`window.useObj`** |
| 列表 `siteId` 参数 | 传 **`qdId`** | 传 **`useObj.siteId`**（铜陵**没有 `qdId`**）|
| `publicationFlag` | **必须 1** | **不需要**（带不带都 `total=2605`）|

⇒ **不能照抄开封的适配器** —— 接口前缀、配置对象名、`siteId` 取哪个字段、
要不要 `publicationFlag`，**四处都不同**。全部从铜陵自己的
`/tlsrmzf/pc2023/js/basehd/config.js` 与 `zmhd.js` 抄到。

响应：`{"total":2605,"page":1,"pagesize":5,"data":[{id,title,submitTime,…}]}`

**详情** `GET /api/mail/detail?id=<id>&tenantId=<tid>` 返回 **21 个字段**，含：
- `content` —— **提问正文**
- `replyContent` —— **答复正文**（HTML）
- `submitTime` / `finishedTime`
- `aimName` —— 类型（「咨询投诉」/「效能建设」/「问题反馈」/「在线咨询」）
- `metadataList` —— 答复单位等（**是 Python 风格的单引号字符串**，见 `_dept_of`）

⇒ **一次调用拿全问答**。

## 质量（铁律第 6 条）

抽 3 条：`content` 58/280/53 字，`replyContent` **624/133/187 字**（**答复非空**，
含具体批示人与办理过程）。

## ⚠ `metadataList` 不是标准 JSON

实测它的键值用**单引号**（`[{'metadataId': '…', 'metadataValue': '…'}]`）
⇒ `json.loads` 会失败 ⇒ 用正则兜底（见 `_dept_of`）。
"""
from __future__ import annotations

import ast
import html as _html
import json
import re
import time

SITE = {
    "key": "tl-hdjl",
    "name": "铜陵市·政民互动·信件公开",
    "kind": "api",
    "level": "city",
    "region": "铜陵市",
    "entry": "https://www.tl.gov.cn/tlsrmzf/hdjl/pc/list.html",
    "status": "ok",
    "note": "GET /api/mail/list（**无 u 前缀**，current/pagesize/tenantId/siteId）"
            "+ /api/mail/detail?id=&tenantId=；配置在 window.useObj；"
            "响应自带 content+replyContent；实测 total=2605",
}

BASE = "https://www.tl.gov.cn"
LIST_API = BASE + "/api/mail/list"
DETAIL_API = BASE + "/api/mail/detail"
REFERER = BASE + "/tlsrmzf/hdjl/pc/list.html"
#: 从 `/tlsrmzf/pc2023/js/basehd/config.js` 的 `window.useObj` 抄到
TENANT_ID = "1676766850592583680"
#: ⚠ 铜陵**没有 `qdId`**，列表 `siteId` 参数就用 `useObj.siteId`（与开封不同）
SITE_ID = "1691623558897848320"
PAGE_SIZE = 50
PAUSE = 0.4
MAX_PAGES = 200

_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_COMMENT = re.compile(r"<!--.*?-->|<![^>]*>", re.S)
#: ⚠⚠ **站方源码里的孤立闭合标签**（2026-10-10 实测）。
#:
#: 实测 `replyContent` 的**原始 HTML** 末尾就带着
#: `</铜陵市人民政府关于支持创业就业人员购(租)房的实施意见>`
#: —— 那是**站方自己**的畸形 HTML（一个只有闭合、没有开头的"标签"，
#: 内容是**中文文档名**）。**不是我的剥标签漏了**（我的正则确实剥掉了真标签）。
#:
#: 全库有 **32 条**这种。
#: ⇒ 单独一条正则把它清掉：**尖括号里以 `/` 开头且含中文**的那种。
#:   （正常 HTML 标签名只能是 ASCII 字母数字，不会是中文。）
_STRAY = re.compile(r"</[^<>]{0,80}?>")
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
    s = _STRAY.sub("", s)
    s = _html.unescape(s)
    s = s.replace("\xa0", " ")
    s = _WS.sub(" ", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


def _real(v) -> str:
    s = _clean(v)
    return "" if s.strip().lower() in ("null", "none", "undefined") else s


def _dept_of(metadata_list) -> str | None:
    """从 `metadataList` 取「答复单位」。

    ⚠ 实测它的键值用**单引号**（Python 字面量风格），`json.loads` 会失败
    ⇒ 先试 `ast.literal_eval`，再退回正则。
    """
    if not metadata_list:
        return None
    arr = metadata_list
    if isinstance(arr, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                arr = parser(arr)
                break
            except Exception:                                           # noqa: BLE001
                continue
        else:
            m = re.search(r"['\"]name['\"]\s*:\s*['\"]答复单位['\"]\s*,\s*"
                          r"['\"](?:metadataValue|value)['\"]\s*:\s*['\"]([^'\"]+)", arr)
            return _real(m.group(1)) if m else None
    if not isinstance(arr, list):
        return None
    for it in arr:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "")
        if name == "答复单位":
            for k in ("metadataValue", "value", "data"):
                if it.get(k):
                    return _real(it[k])
    return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = MAX_PAGES) -> list[dict]:
    """翻列表（GET JSON）+ 逐条取详情。

    ⚠ 用传入的 `fetch`（它是 `client.get` 的包装）—— 本接口是 GET。

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
                                        "tenantId": TENANT_ID, "siteId": SITE_ID},
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
                "url": f"{BASE}/tlsrmzf/mail/detail.html?id={mid}",
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
                    "platform": "铜陵市政务互动平台（api/mail）",
                },
            })
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，其中无答复 {n_fail} 条")
    return out
