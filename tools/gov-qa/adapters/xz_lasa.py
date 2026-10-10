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

## ⚠⚠ 2026-10-10 修：全源 1,030 条答复为空（spec 005 T201）

**症状**：`data/xz-lasa-*.jsonl` 里 1,030 条**答复全是空串**（100%），
而条数、标题、时间、部门都正常 —— 旧闸门只看条数，**完全看不见**。

**根因（实测）**：本适配器原本从**列表**接口取答复
（`it.get("replyContent") or it.get("content")`），
但列表接口 `/frontMail/mailList` 返回的 25 个字段里
**根本没有 `replyContent`，也没有 `content`** ⇒ 取到的一直是 `""`。

**真答复在详情接口**，且**参数名是 `mailId` 而不是 `id`**（实测：
传 `id` 返回 `errorCode 99001` 参数校验失败；传 `mailId` 返回 `status=success`）：
```
GET /communication/api-mailbox/frontMail/detail?mailId=<id>
→ data.content                       = 来信正文（问题）
  data.replyContents[].replyContent  = 答复正文   ← 要的就是它
  data.deptName / objectiveType / createTime ...
```
⇒ 现在**列表取元数据 + 逐条取详情补答复**。这是本适配器第一次真正拿到答复。

**代价**：每条约 0.5–1.2s（`PAUSE`），1,031 条约 20 分钟。可接受。

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
#: 详情接口（**答复正文在这里**）。⚠ 参数名是 `mailId`，不是 `id`。
DETAIL = BASE + "/communication/api-mailbox/frontMail/detail"
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


def fetch_detail(client, mail_id: str) -> dict:
    """取一条来信的详情（**答复正文在这里**）。

    ⚠⚠ 参数名必须是 **`mailId`**，不是 `id`（实测：传 `id` 返回
    `errorCode 99001` 参数校验失败 —— `{"phone":"手机号不能为空",...}`）。
    返回 `{"content": 问题正文, "reply": 答复正文, "reply_time": ..., "dept": ...}`；
    失败返回空 dict（**绝不抛出去**，单条失败只跳过这一条）。
    """
    try:
        r = client.get(DETAIL, params={"mailId": mail_id},
                       headers={"Referer": REFERER,
                                "X-Requested-With": "XMLHttpRequest"})
    except Exception:                                                   # noqa: BLE001
        return {}
    if getattr(r, "status_code", 0) != 200:
        return {}
    try:
        d = r.json() or {}
    except Exception:                                                   # noqa: BLE001
        return {}
    if d.get("status") != "success":
        return {}
    data = d.get("data") or {}
    # 答复可能在 replyContents[]（多条办理记录）—— 全并起来，别只取第一条
    replies = []
    for rc in (data.get("replyContents") or []):
        t = _clean(rc.get("replyContent"))
        if t:
            replies.append(t)
    reply_time = None
    for rc in (data.get("replyContents") or []):
        rt = rc.get("replyTime") or rc.get("createDate")
        if rt and (reply_time is None or str(rt) > str(reply_time)):
            reply_time = rt
    return {
        "content": _clean(data.get("content")),
        "reply": "\n\n".join(replies),
        "reply_time": reply_time,
        "dept": _clean(data.get("deptName")) or None,
        "objective_type": _clean(data.get("objectiveType")) or None,
        "status": data.get("status"),
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """翻页取拉萨来信选登：**列表取元数据 + 逐条取详情补答复**。

    ⚠ 本接口是 **POST + JSON body**，而 `harvest.py` 传进来的 `fetch` 是
    `client.get` 的包装（**不接受 `method=` 参数**，实测报
    `Client.get() got an unexpected keyword argument 'method'`）。
    ⇒ 本适配器**自建一个 httpx client** 发 POST，不用传入的 `fetch`。

    ⚠⚠ **逐条取详情这一阶段必须打进度点** —— 本模块为此踩过 5 次坑
    （天水 / 惠州 / `_jact_common` / `_post_list_common` / `_igi_common`：
    列表阶段有日志、明细阶段静默 ⇒ 被误判成"站点节流"）。
    ⇒ 每 25 条打一次，且**中途异常不冒泡**（单条失败只跳过）。
    """
    import httpx
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")
    n_detail = 0
    n_detail_fail = 0
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
                    break
                sid = str(it.get("id") or "").strip()
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                title = _clean(it.get("title"))
                if not title:
                    continue
                otype = _clean(it.get("objectiveType")) or None
                # ---- 逐条取详情补答复（旧版漏了这一步 ⇒ 全源答复为空）----
                det = fetch_detail(c, sid)
                n_detail += 1
                if not det.get("reply"):
                    n_detail_fail += 1
                if n_detail % 25 == 0:
                    print(f"    [{SITE['key']}] 明细进度 {n_detail} 条"
                          f"（无答复 {n_detail_fail}）", flush=True)
                time.sleep(PAUSE)
                out.append({
                    "source": SITE["key"],
                    "id": sid,
                    "url": f"{BASE}/lasa/lxxd/hd_mailbox_detail.shtml?mailId={sid}",
                    "question": det.get("content") or title,
                    "answer": det.get("reply") or "",
                    "asked_at": it.get("createTime") or None,
                    # 优先用详情里的答复时间；列表的 seeTime 是"查看时间"
                    "answered_at": det.get("reply_time") or it.get("seeTime") or None,
                    "dept": det.get("dept") or _clean(it.get("deptName")) or None,
                    "channel": "来信选登",
                    "extra": {
                        "title": title,
                        "objective_type": otype,
                        "content_type": _clean(it.get("contentType")) or None,
                        "status": det.get("status") or it.get("status"),
                        "is_public": it.get("isPublic"),
                        "platform": "拉萨 api-mailbox/frontMail/mailList + detail",
                        # ★ 站方标签直接当规范化标签（比模型可信）
                        **({"msg_type_norm": otype,
                            "msg_type_source": "source_label"} if otype else {}),
                    },
                })
            if limit and len(out) >= limit:
                break
            if total and page * PAGE_SIZE >= int(total):
                break
    print(f"    [{SITE['key']}] 收 {len(out)} 条；明细取 {n_detail} 条，"
          f"其中无答复 {n_detail_fail} 条")
    return out
