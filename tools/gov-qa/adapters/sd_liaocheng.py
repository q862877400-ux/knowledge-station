"""适配器：**聊城市·政民互动·网上信箱（api.min.js 接口，列表自带答复）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city3-lc-api.js、sd-city3-聊城-*.html）
 · 门户 `www.liaocheng.gov.cn` 政民互动 `http://www.liaocheng.gov.cn/channel_t_156_11559/`；
   列表由 `/static/<hash>/dist/js/api.min.js` 的 `getDocListByApi` 拉取：
   `POST {RequestBasic}/public/email/paginate`，body JSON
   `{exclude:[], page:"N", per_page:"M", organization:"lcsrmzf"}`。
 · 页面内联定义：`RequestBasic='/api'`、`organization='lcsrmzf'`、
   `accessToken="Bearer "`（**空 token**，实测不带 Authorization 也 200）。
 · **列表条目自带答复**：`items[].reply.content` 即答复原文（含承办单位前缀），
   `reply.site`=答复单位、`reply._createtime`=答复时间；无需再取详情。
 · 实测 `total=1249`，`status="已办结"`，`content`=问题、`title`=标题、
   `submittime`=提问时间、`type`=类型。
 · ⚠ 注意：`Authorization: "Bearer "` 末尾带空格会被 httpx 拒（非法头），故**不设**该头。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "sd-liaocheng",
    "name": "聊城市·政民互动·网上信箱（api）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.liaocheng.gov.cn/channel_t_156_11559/",
    "status": "ok",
    "note": "POST /api/public/email/paginate（organization=lcsrmzf）；列表自带 reply.content；total≈1249",
}

BASE = "http://www.liaocheng.gov.cn"
API = BASE + "/api/public/email/paginate"
REFERER = BASE + "/channel_t_156_11559/"
ORG = "lcsrmzf"
PER_PAGE = 20
PAUSE = 1.2
TAG_RE = re.compile(r"<[^>]+>")


def clean(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", str(s))).strip()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采聊城网上信箱（列表自带答复，逐页翻）。"""
    out: list[dict] = []
    page = 1
    total = None
    while True:
        if limit and len(out) >= limit:
            break
        if total is not None and (page - 1) * PER_PAGE >= total:
            break
        body = {"exclude": [], "page": str(page), "per_page": str(PER_PAGE),
                "organization": ORG}
        try:
            r = fetch.post(API, json=body,
                           headers={"Referer": REFERER,
                                    "Content-Type": "application/json"})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页请求失败 {type(e).__name__}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            data = (r.json() or {}).get("data") or {}
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        if total is None:
            total = int(data.get("total") or 0)
            print(f"    [{SITE['key']}] total={total}")
        items = data.get("items") or []
        if not items:
            break
        got = 0
        for it in items:
            if limit and len(out) >= limit:
                break
            rp = it.get("reply")
            if isinstance(rp, list):
                rp = rp[0] if rp else None
            answer = clean((rp or {}).get("content")) if isinstance(rp, dict) else ""
            if len(answer) < 10:
                continue
            mid = str(it.get("id") or it.get("_id") or "")
            out.append({
                "source": SITE["key"],
                "id": mid,
                "url": f"{BASE}/channel_t_156_11571/?page=1&id={mid}",
                "question": clean(it.get("content")) or clean(it.get("title")),
                "answer": answer,
                "asked_at": it.get("submittime") or it.get("_createtime"),
                "answered_at": (rp or {}).get("_createtime") if isinstance(rp, dict) else None,
                "dept": (rp or {}).get("site") if isinstance(rp, dict) else None,
                "channel": "网上信箱·咨询投诉",
                "extra": {
                    "title": clean(it.get("title")),
                    "type": it.get("type"),
                    "state": it.get("status"),
                    "select_no": it.get("select"),
                    "platform": "聊城门户 api.min.js",
                    "answer_kind": "部门答复（reply.content 含承办单位）",
                },
            })
            got += 1
        print(f"    [{SITE['key']}] 第 {page} 页：{len(items)} 条（收 {got}，累计 {len(out)}）")
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
