"""适配器：**广东省应急管理厅**「互动交流平台」（hdjlpt）留言选登。

## 接口（2026-10-07 真浏览器抓包 + httpx 复现验证）
```
GET  https://yjgl.gd.gov.cn/hdjlpt/published?via=pc     # 落地页：种 Laravel 会话 Cookie
POST https://yjgl.gd.gov.cn/hdjlpt/letter/pubList       # 列表（表单编码，无签名）
     body = offset=0&limit=20&site_id=122
            &time_from=<unix>&time_to=<unix>
     header 必带 X-XSRF-TOKEN: <cookie 里 XSRF-TOKEN 经 URL 解码>   ← Laravel CSRF
```
 · **时间窗有服务端校验**：跨度 >1 年直接 404 ⇒ 按 365 天窗向前翻历史。
 · 响应 `data.list[]` **每条自带问答全文**：`title`/`content`(问题)/`reply`(答复 HTML)/
   `reply_time`/`org_name`/`handle_code`(受理编号)/`pub_url`(公开链接)——**无需再抓明细页**。
 · `site_id` 实测被服务端忽略（120..130 同回 36 条）——多厅局应是各厅自建实例，
   将来按厅域名复用本适配器模式。

## 语料质量（实测样本）
答复点名 `AQ 3067-2026`、应急管理部 19 号令等具体依据条款 —— 高档考卷料。

## 答复字段口径
`reply` 是 HTML（`<p><span style=…>`），与 hunan 基座同法：**去标签保文字、不摘要**。
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from urllib.parse import unquote

SITE = {
    "key": "gd-yj",
    "name": "广东省应急管理厅",
    "kind": "api",
    "level": "province",
    "entry": "https://yjgl.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList（Laravel CSRF 握手）；答复点名依据条款，高档考卷料；"
            "时间窗服务端限 1 年 ⇒ 按 365 天窗翻历史",
}

BASE = "https://yjgl.gd.gov.cn"
PAGE = f"{BASE}/hdjlpt/published?via=pc"
API = f"{BASE}/hdjlpt/letter/pubList"
SITE_ID = "122"
WINDOW_DAYS = 365
MAX_YEARS_BACK = 12
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")

#: 统一字段之外的原始键进 extra
EXTRA_KEYS = ("handle_code", "nickname", "site_id")


def _text(html: str) -> str:
    t = TAG_RE.sub(" ", html or "")
    return re.sub(r"\s+", " ", t).strip()


def _ts(unix) -> str | None:
    if not unix:
        return None
    return datetime.fromtimestamp(int(unix)).strftime("%Y-%m-%d %H:%M:%S")


def _post_list(fetch, *, token: str, offset: int, limit: int,
               time_from: int, time_to: int) -> dict:
    body = (f"offset={offset}&limit={limit}&site_id={SITE_ID}"
            f"&time_from={time_from}&time_to={time_to}")
    r = fetch.post(API, content=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE, "Referer": PAGE,
        "X-XSRF-TOKEN": token,
    })
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"pubList HTTP {getattr(r, 'status_code', '?')}")
    return r.json()


def harvest(fetch, *, limit: int | None = None, pause: float = PAUSE) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（用 `.post`）。
    先 GET 落地页拿 Laravel 会话与 XSRF cookie，再带 `X-XSRF-TOKEN` 头翻列表；
    按 365 天窗自今向前扫历史，空窗即停。
    """
    # ① CSRF 握手
    r0 = fetch(PAGE)
    if getattr(r0, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 落地页 HTTP {getattr(r0, 'status_code', '?')}（停）")
        return []
    cookies = getattr(getattr(r0, "cookies", None), "jar", None)
    raw = None
    for c in (cookies or []):
        if c.name == "XSRF-TOKEN":
            raw = c.value
    # httpx 的 fetch 返回体不带 jar（Client 持有）——从 r0.headers 的 set-cookie 兜底
    if raw is None:
        m = re.search(r"XSRF-TOKEN=([^;]+)", "; ".join(
            getattr(r0, "headers", {}).get_list("set-cookie") if hasattr(
                getattr(r0, "headers", None), "get_list") else []))
        raw = m.group(1) if m else None
    if not raw:
        print(f"    [{SITE['key']}] 未取得 XSRF-TOKEN（停）")
        return []
    token = unquote(raw)

    out: list[dict] = []
    limit_per_page = 20
    now = int(time.time())
    time_to = now
    for _year in range(MAX_YEARS_BACK):
        time_from = time_to - WINDOW_DAYS * 86400
        offset, scanned_all = 0, False
        while True:
            try:
                j = _post_list(fetch, token=token, offset=offset,
                               limit=limit_per_page,
                               time_from=time_from, time_to=time_to)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 窗口 {time_from}-{time_to} "
                      f"offset={offset}：{type(e).__name__} {e}（停本窗）")
                break
            d = j.get("data") or {}
            items = d.get("list") or []
            total = d.get("total") or 0
            if offset == 0:
                print(f"    [{SITE['key']}] 窗口 {datetime.fromtimestamp(time_from):%Y-%m-%d}"
                      f"~{datetime.fromtimestamp(time_to):%Y-%m-%d} total={total}")
            if not items:
                break
            for it in items:
                reply = _text(it.get("reply") or "")
                if not reply:
                    continue
                title = _text(it.get("title") or "")
                body = _text(it.get("content") or "")
                out.append({
                    "source": SITE["key"],
                    "id": str(it.get("id") or it.get("handle_code") or ""),
                    "url": it.get("pub_url"),
                    "question": title if not body else f"{title}\n{body}",
                    "answer": reply,
                    "asked_at": _ts(it.get("time")),
                    "answered_at": _ts(it.get("reply_time")),
                    "dept": _text(it.get("org_name") or ""),
                    "channel": it.get("type"),
                    "extra": {k: it.get(k) for k in EXTRA_KEYS
                              if it.get(k) is not None},
                })
                if limit and len(out) >= limit:
                    return out
            offset += limit_per_page
            if offset >= total:
                scanned_all = True
                break
            time.sleep(pause)
        time.sleep(pause)
        if scanned_all and total == 0:
            break                       # 扫到空窗 = 历史尽头
        time_to = time_from
    return out
