"""适配器：**农业农村部·留言回复**（部长信箱·网上信访，站内静态 JSON，答复内联）。

## 站点事实（2026-10-09 实测，证据 recon/nat-probe-moa-*）
 · 入口 `https://www.moa.gov.cn/hd/`（互动）→ `部长信箱·网上信访` → `网民互动`。
   门户页 `messageReply.html` 是「留言选登/留言回复/留言办理/留言统计」聚合壳。
 · ⚠ 两个易混栏目：
   - **留言选登** `netizen/publish.html` → `jsonFiles/publish.json`（**只有问题、无答复**，90 条）⇒ **不合格**；
   - **留言回复** `netizen/reply.html` → `jsonFiles/reply.json`（**问题 + 答复原文**，824 条）⇒ 本适配器用它。
 · 列表（**GET 静态 JSON，答复内联**，免登录）：
   `GET https://www.moa.gov.cn/bzxxlyhf/xfwy/jsonFiles/reply.json`
   → `[{strMinisterCode,strSubject,strLetter(问题),strContent(答复HTML),strHandleOrgName(回复司局),
        dtHandleStr(办理日期),replyState,…}]`
 · 明细页（人看）：`https://www.moa.gov.cn/bzxxlyhf/xfwy/netizen/replyDetail.html?strMinisterCode=<code>`。
 · 实测答复点名《…》（例：《农村综合统计调查制度》《农户和新型农业经营主体统计调查制度》）⇒ 优质考卷料。
"""
from __future__ import annotations

import re

SITE = {
    "key": "nat-moa",
    "name": "农业农村部·留言回复",
    "kind": "api",
    "level": "national",
    "entry": "https://www.moa.gov.cn/hd/",
    "status": "ok",
    "note": "站内静态 JSON jsonFiles/reply.json（824 条，问题+答复内联 strContent）",
}

LIST_API = "https://www.moa.gov.cn/bzxxlyhf/xfwy/jsonFiles/reply.json"
DETAIL_PAGE = "https://www.moa.gov.cn/bzxxlyhf/xfwy/netizen/replyDetail.html?strMinisterCode="
REFERER = "https://www.moa.gov.cn/bzxxlyhf/xfwy/netizen/reply.html"

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)


def _text(html: str | None) -> str:
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = re.sub(r"</?p[^>]*>", "\n", t, flags=re.I)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&emsp;", " ").replace("&#39;", "'").replace("&amp;", "&")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取农业农村部留言回复（问题 + 答复原文）。"""
    r = fetch(LIST_API, headers={"Referer": REFERER})
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] JSON HTTP {getattr(r, 'status_code', '?')}（停）")
        return []
    try:
        items = r.json()
    except Exception as e:                                                      # noqa: BLE001
        print(f"    [{SITE['key']}] 非 JSON（{type(e).__name__}，停）")
        return []
    print(f"    [{SITE['key']}] JSON {len(items)} 条")
    out: list[dict] = []
    for it in items:
        if limit and len(out) >= limit:
            break
        answer = _text(it.get("strContent"))
        if len(answer) < 10:
            continue
        code = str(it.get("strMinisterCode") or "")
        out.append({
            "source": SITE["key"],
            "id": code,
            "url": DETAIL_PAGE + code,
            "question": (it.get("strLetter") or it.get("strSubject") or "").strip(),
            "answer": answer,
            "asked_at": None,
            "answered_at": it.get("dtHandleStr"),
            "dept": it.get("strHandleOrgName") or it.get("strHandleMan"),
            "channel": "留言回复",
            "extra": {
                "title": it.get("strSubject"),
                "handle_type": it.get("intOneHandleStr"),
                "platform": "moa-reply-json",
            },
        })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
