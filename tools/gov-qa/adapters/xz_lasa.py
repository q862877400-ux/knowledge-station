"""适配器：**拉萨市·来信选登**（`/communication/api-mailbox/frontMail/mailList`）。

## 站点事实（2026-10-10 实测）

- 入口页 `https://www.lasa.gov.cn/lasa/lxxd/hd_mailbox.shtml`
- 前端 `hd_mailbox.js` 里的 `mailList()` 调：
  **`POST {同域}/communication/api-mailbox/frontMail/mailList`**
  body（JSON）：
  ```json
  {"pageNum":1,"pageSize":10,
   "sortMap":{"createTime":"desc"},
   "params":{"phone":"","searchCode":"","selfDeptId":"d548f0a35d60483c8c67bbb86f7a5723"}}
  ```
- 响应：`{"status":"success","data":{"total":N,"pageTotal":M,"rows":[…]}}`
- 条目字段：`id / objectiveType / contentType / deptName / title / createTime /
  seeTime / status / isPublic`

## ★ 为什么值得建

1. **这是西藏第一个可用源** —— 之前 `coverage-report.py` 报「西藏 0 条（none）」。
2. **站方直接给了类型标签**（`objectiveType`，实测值如「求助」）——
   比模型预测可信，直接写进 `msg_type_source="source_label"`。

## ⚠ 与西藏信访平台的区别

`xzxf.xizang.gov.cn`（自治区信访平台）**需要登录，判死**；
但**拉萨市**这个接口是**公开的**（`isPublic=1` 的条目才返回）。
⇒ **省级被拦/判死 ≠ 地市级也不行。** 这条经验值得记。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "xz-lasa",
    "name": "拉萨市·来信选登",
    "kind": "api",
    "level": "city",
    "entry": "https://www.lasa.gov.cn/lasa/lxxd/hd_mailbox.shtml",
    "status": "ok",
    "note": "POST /communication/api-mailbox/frontMail/mailList（JSON，公开列表含 objectiveType 类型标签）",
}

BASE = "https://www.lasa.gov.cn"
API = BASE + "/communication/api-mailbox/frontMail/mailList"
REFERER = SITE["entry"]
SELF_DEPT = "d548f0a35d60483c8c67bbb86f7a5723"
PAGE_SIZE = 20
PAUSE = 1.2

_TAG = re.compile(r"<[^>]+>")


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    return _html.unescape(s).strip()


def _body(page: int, size: int) -> dict:
    return {
        "pageNum": page,
        "pageSize": size,
        "sortMap": {"createTime": "desc"},
        "params": {"phone": "", "searchCode": "", "selfDeptId": SELF_DEPT},
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取拉萨来信选登。列表**自带标题**，无需逐条取详情（更快）。

    ⚠ 本接口是 **POST + JSON body**，而 `harvest.py` 传进来的 `fetch` 是
    `client.get` 的包装（**不接受 `method=` 参数**，实测报
    `Client.get() got an unexpected keyword argument 'method'`）。
    ⇒ 本适配器**自建一个 httpx client** 发 POST，不用传入的 `fetch`。
    """
    import httpx
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    with httpx.Client(timeout=30, headers={"User-Agent": ua},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                break
            try:
                r = c.post(API, json=_body(page, PAGE_SIZE),
                           headers={"Referer": REFERER,
                                    "Content-Type": "application/json",
                                    "X-Requested-With": "XMLHttpRequest"})
            except Exception as e:                                      # noqa: BLE001
                print(f"    [{SITE['key']}] 第 {page} 页失败 {type(e).__name__}: {e}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
                break
            try:
                d = r.json() or {}
            except Exception:                                           # noqa: BLE001
                print(f"    [{SITE['key']}] 第 {page} 页非 JSON（停）")
                break
            if d.get("status") != "success":
                print(f"    [{SITE['key']}] 第 {page} 页 status={d.get('status')}（停）")
                break
            data = d.get("data") or {}
            rows = data.get("rows") or []
            if total is None:
                total = data.get("total")
                print(f"    [{SITE['key']}] 来信总数 total={total}")
            if not rows:
                break
            for it in rows:
                if limit and len(out) >= limit:
                    return out
                sid = str(it.get("id") or "").strip()
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                title = _clean(it.get("title"))
                if not title:
                    continue
                otype = _clean(it.get("objectiveType")) or None
                out.append({
                    "source": SITE["key"],
                    "id": sid,
                    "url": REFERER,
                    "question": title,
                    "answer": _clean(it.get("replyContent") or it.get("content") or ""),
                    "asked_at": it.get("createTime") or None,
                    "answered_at": it.get("seeTime") or None,
                    "dept": _clean(it.get("deptName")) or None,
                    "channel": "来信选登",
                    "extra": {
                        "title": title,
                        "objective_type": otype,
                        "content_type": _clean(it.get("contentType")) or None,
                        "status": it.get("status"),
                        "is_public": it.get("isPublic"),
                        "platform": "拉萨 api-mailbox/frontMail/mailList",
                        # ★ 站方标签直接当规范化标签（比模型可信）
                        **({"msg_type_norm": otype,
                            "msg_type_source": "source_label"} if otype else {}),
                    },
                })
            if total and page * PAGE_SIZE >= int(total):
                break
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
