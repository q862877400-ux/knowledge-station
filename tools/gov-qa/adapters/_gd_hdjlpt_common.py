"""广东省级厅局「互动交流平台」（hdjlpt）· 共用采集引擎。

## 平台事实（2026-10-07 实测，两厅验证）
广东各厅局在自己域名下部署**同款** hdjlpt（Laravel 应用）：
 · 应急管理厅 `https://yjgl.gd.gov.cn/hdjlpt`（site_id=122）
 · 生态环境厅 `https://gdee.gd.gov.cn/hdjlpt`（同接口，年窗 211 条 vs 应急 36 条）
**每个厅域名单独部署、数据各自独立**；`pubList` 的 `site_id` 参数被服务端忽略
（120..130 同回应急厅数据，见 recon/gd-sitid-probe.txt）⇒ **按厅域名各采各的**。

## 接口
```
GET  {base}/hdjlpt/published?via=pc     # 落地页：种 Laravel 会话 Cookie
POST {base}/hdjlpt/letter/pubList       # 列表（表单编码）
     body = offset=N&limit=20&time_from=<unix>&time_to=<unix>
     header 必带 X-XSRF-TOKEN: <cookie XSRF-TOKEN 经 URL 解码>   ← Laravel CSRF
```
 · **时间窗服务端限 1 年**（更宽直接 404）⇒ 按 365 天窗自今向前扫，空窗即停。
 · `data.list[]` 每条自带问答全文（`title`/`content`/`reply` HTML/`reply_time`/
   `org_name`/`handle_code`/`pub_url`）——**无需再抓明细页**。
 · 答复质量高（点名 AQ 3067-2026、19 号令等依据条款）。

## 新增一个广东厅局 = 复制一个薄适配器
```python
from adapters._gd_hdjlpt_common import harvest_gd
SITE = {"key": "gd-xx", "name": "广东省某厅", ...}
BASE = "https://xx.gd.gov.cn"
def harvest(fetch, *, limit=None):
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
```
（域名清单见 SITE-REGISTRY「广东厅局 hdjlpt 域名探测」。）
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

PAGE_PATH = "/hdjlpt/published?via=pc"
API_PATH = "/hdjlpt/letter/pubList"
WINDOW_DAYS = 365
MAX_YEARS_BACK = 12
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

#: 统一字段之外的原始键进 extra
EXTRA_KEYS = ("handle_code", "nickname", "site_id")


def existing_ids(site_key: str) -> set:
    """读 `data/<site_key>-*.jsonl` 已有 id（供增量续采，与 `_igi_common.existing_ids` 同义）。

    ⚠ 为什么需要它：hdjlpt 的 `pubList` **只按 `offset` 翻页**、没有「从某条之后」的游标。
    若每轮都从头翻，`limit` 会把**已落盘的条数**算进去 ⇒
    「跑一次拿 6,000，再跑 `--limit 15000` 只多拿 9,000」—— 前 6,000 条白翻一遍。
    """
    ids: set = set()
    try:
        for p in DATA_DIR.glob(f"{site_key}-*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    mid = str(json.loads(line).get("id") or "").strip()
                    if mid:
                        ids.add(mid)
    except Exception:                                                       # noqa: BLE001
        pass
    return ids


def _text(html: str) -> str:
    t = TAG_RE.sub(" ", html or "")
    return re.sub(r"\s+", " ", t).strip()


def _ts(unix) -> str | None:
    if not unix:
        return None
    return datetime.fromtimestamp(int(unix)).strftime("%Y-%m-%d %H:%M:%S")


def _post_list(fetch, *, base: str, token: str, offset: int, limit: int,
               time_from: int, time_to: int) -> dict:
    body = f"offset={offset}&limit={limit}&time_from={time_from}&time_to={time_to}"
    r = fetch.post(base + API_PATH, content=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": base, "Referer": base + PAGE_PATH,
        "X-XSRF-TOKEN": token,
    })
    if getattr(r, "status_code", 0) != 200:
        raise RuntimeError(f"pubList HTTP {getattr(r, 'status_code', '?')}")
    return r.json()


def _xsrf_token(r0) -> str | None:
    """从落地页响应里取 XSRF-TOKEN（优先响应 cookie，兜底 set-cookie 头）。"""
    jar = getattr(getattr(r0, "cookies", None), "jar", None)
    for c in (jar or []):
        if c.name == "XSRF-TOKEN":
            return unquote(c.value)
    headers = getattr(r0, "headers", None)
    get_list = getattr(headers, "get_list", None)
    if get_list:
        m = re.search(r"XSRF-TOKEN=([^;]+)",
                      "; ".join(get_list("set-cookie")))
        if m:
            return unquote(m.group(1))
    return None


def harvest_gd(fetch, *, SITE: dict, BASE: str, limit: int | None = None,
               pause: float = PAUSE, per_page: int = 20,
               skip_ids: set | None = None) -> list[dict]:
    """按统一记录格式返回某广东厅局 hdjlpt 的留言选登（问题+答复全文）。

    ⚠ `fetch` 是 harvest.py 注入的 `_Fetcher`（用 `.post`）。

    ## ★ `skip_ids`（2026-10-10 第 7 轮新增）—— 修 O(n²) 的增量续采

    **问题**：本引擎原先**没有** `skip_ids`（`_igi_common.harvest_igi` 一直有）。
    列表接口按时间倒序、**没有「从某条之后」的游标** ⇒ 每次重跑都从头翻，
    `limit` 也把**已落盘的条数**算进去。实测深圳：`--limit 6000` 拿到 6,000 条，
    再跑 `--limit 15000` 只会多拿 9,000 条新的，**前面 6,000 条白翻 12 分钟**。

    **修法**：`skip_ids=None` 时自动取 `existing_ids(SITE['key'])`；
    命中已落盘的条目**直接跳过、且不计入 `limit`** ⇒ `limit` 语义变为
    「本轮**新增**条数」，可反复跑逐轮推进。
    要显式关掉（例如想重刷已落盘条目的内容）传 `skip_ids=set()`。

    ⚠ **不做「整窗已知就提前收工」** —— 那会漏掉「上轮只采到 limit、更老的窗口还没翻」的源。
    宁可多翻几页，也不要静默少采。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    # ① CSRF 握手
    r0 = fetch(BASE + PAGE_PATH)
    if getattr(r0, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 落地页 HTTP {getattr(r0, 'status_code', '?')}（停）")
        return []
    token = _xsrf_token(r0)
    if not token:
        print(f"    [{SITE['key']}] 未取得 XSRF-TOKEN（停）")
        return []

    out: list[dict] = []
    skipped = 0
    now = int(time.time())
    time_to = now
    for _year in range(MAX_YEARS_BACK):
        time_from = time_to - WINDOW_DAYS * 86400
        offset, window_total = 0, None
        while True:
            try:
                j = _post_list(fetch, base=BASE, token=token, offset=offset,
                               limit=per_page, time_from=time_from,
                               time_to=time_to)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 窗口 {time_from}-{time_to} "
                      f"offset={offset}：{type(e).__name__} {e}（停本窗）")
                break
            d = j.get("data") or {}
            items = d.get("list") or []
            if window_total is None:
                window_total = d.get("total") or 0
                print(f"    [{SITE['key']}] "
                      f"窗口 {datetime.fromtimestamp(time_from):%Y-%m-%d}"
                      f"~{datetime.fromtimestamp(time_to):%Y-%m-%d} "
                      f"total={window_total}")
            if not items:
                break
            for it in items:
                mid = str(it.get("id") or it.get("handle_code") or "")
                if mid and mid in skip_ids:
                    skipped += 1                    # 已落盘 ⇒ 不计入 limit
                    continue
                reply = _text(it.get("reply") or "")
                if not reply:
                    continue
                title = _text(it.get("title") or "")
                body = _text(it.get("content") or "")
                out.append({
                    "source": SITE["key"],
                    "id": mid,
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
                if mid:
                    skip_ids.add(mid)               # ★ 运行中也要并回去，防同窗重复
                if limit and len(out) >= limit:
                    print(f"    [{SITE['key']}] 达 limit={limit}"
                          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
                    return out
            offset += per_page
            if offset >= (window_total or 0):
                break
            time.sleep(pause)
        time.sleep(pause)
        if window_total == 0:
            break                       # 扫到空窗 = 历史尽头
        time_to = time_from
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
