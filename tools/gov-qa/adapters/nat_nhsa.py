"""适配器：**国家医疗保障局·交流公开**（自研 Vue 应用 + JSON 接口）。

## 站点事实（2026-10-09 实测，证据 recon/nat-nhsa-*）
 · 入口 `https://www.nhsa.gov.cn/col/col59/index.html`（互动交流 → 交流公开）。
   该栏目正文是一个 **iframe**：`https://cap.nhsa.gov.cn:7903/exchangeOpen.html`（Vue 应用）。
 · 接口基址写在 `:7903/assets/api/api.js` 里：`var production = "https://cap.nhsa.gov.cn:7913"`。
 · 列表（**POST，答复内联**，免登录）：
   `POST https://cap.nhsa.gov.cn:7913/open/netizen/openInfoList`
   body `{"page":N,"size":15}`（**必须带 Referer/Origin**，否则 500）。
   → `{flag,code:20000,data:{totalRows,totalPage,currentPage,pageSize,
        items:[{id,title,content,letterCode,letterFromTime,replyContent,replyDept,replyTime,createTime}]}}`
   `content`=问题原文，`replyContent`=答复原文（下游靠它抽文件号）。
 · 明细页（人看）：`https://cap.nhsa.gov.cn:7903/openDetail.html?id=<id>`（同接口 openInfoDetail）。
 · 实测答复点名《…通知》（例：《国家医疗保障局办公室关于基本医保药品目录内中药饮片部分名称变更的通知》）⇒ 优质考卷料。
 ⚠ 证书正常（verify 默认即可）；`:7913` 与 `:7903` 是**两个端口**，别混。
"""
from __future__ import annotations

import time

SITE = {
    "key": "nat-nhsa",
    "name": "国家医疗保障局·交流公开",
    "kind": "api",
    "level": "national",
    "entry": "https://www.nhsa.gov.cn/col/col59/index.html",
    "status": "ok",
    "note": "cap.nhsa.gov.cn:7913 /open/netizen/openInfoList（POST，答复内联 replyContent，totalRows≈37）",
}

LIST_API = "https://cap.nhsa.gov.cn:7913/open/netizen/openInfoList"
DETAIL_PAGE = "https://cap.nhsa.gov.cn:7903/openDetail.html?id="
REFERER = "https://cap.nhsa.gov.cn:7903/exchangeOpen.html"
ORIGIN = "https://cap.nhsa.gov.cn:7903"
PAGE_SIZE = 15
PAUSE = 1.5

_HEADERS = {
    "Content-Type": "application/json",
    "Referer": REFERER,
    "Origin": ORIGIN,
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE) -> list[dict]:
    """取国家医保局交流公开（问题 + 答复原文）。"""
    out: list[dict] = []
    page = 1
    total_pages = None
    while True:
        if limit and len(out) >= limit:
            break
        r = fetch.post(LIST_API, json={"page": page, "size": page_size}, headers=_HEADERS)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                                  # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页非 JSON（{type(e).__name__}，停）")
            break
        if j.get("code") != 20000:
            print(f"    [{SITE['key']}] 第 {page} 页 code={j.get('code')} msg={j.get('message')}（停）")
            break
        data = j.get("data") or {}
        items = data.get("items") or []
        if total_pages is None:
            total_pages = data.get("totalPage") or 0
            print(f"    [{SITE['key']}] totalRows={data.get('totalRows')} totalPage={total_pages}")
        if not items:
            break
        for it in items:
            if limit and len(out) >= limit:
                break
            answer = (it.get("replyContent") or "").strip()
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": str(it.get("id") or it.get("letterCode") or ""),
                "url": DETAIL_PAGE + str(it.get("id") or ""),
                "question": (it.get("content") or it.get("title") or "").strip(),
                "answer": answer,
                "asked_at": it.get("letterFromTime"),
                "answered_at": it.get("replyTime"),
                "dept": it.get("replyDept"),
                "channel": "交流公开",
                "extra": {
                    "title": it.get("title"),
                    "letter_code": it.get("letterCode"),
                    "create_time": it.get("createTime"),
                    "platform": "nhsa-cap",
                },
            })
        if total_pages and page >= total_pages:
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
