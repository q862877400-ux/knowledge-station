r"""抓「JSON 列表接口」型政府站的规范性文件（2026-11-05）。

## 为什么需要第五条线

前四条（静态 / CDP 渲染 / 摸入口 / 政府公报）都在跟 HTML 打交道。实测一批
市政府站（宜春 `yichun.gov.cn` 等）改用**数融 CMS**：首页是空壳，
列表由 JS 调同域 `POST /queryList` 拉 JSON，静态与 CDP 都只看到壳。

页面里的 `config.js` 明写接口路径，`list.html` 里明写 `websiteCode`，
`channelCode` 是栏目代码（如 `gfxwj`）。这些都是**公开配置，不是绕过反爬**。

## 用法

    .venv\Scripts\python.exe scripts/national-crawl-api.py \
        --site 宜春市 --base https://www.yichun.gov.cn \
        --website-code ycsrmzf --channel gfxwj --max-pages 20

## 纪律

- 只调公开列表接口，同主机串行、页间 1 秒；不猜令牌、不绕验证码
- 条目按 URL 去重合并，正文落盘（用接口自带的 `content.content`）
- 口径与静态管线一致：`ncf.is_title()` 过滤新闻/事务类
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests as creq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import national_crawl_common as ncs  # noqa: E402

_ncf = ncs.load_script("ncf", "scripts/national-crawl-fetch.py")

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def fetch_page(session, base: str, website: str, channel: str,
               page: int, size: int, referer: str) -> dict:
    """取一页 JSON。返回 `data` 字典，失败返回空字典。"""
    url = base.rstrip("/") + "/queryList"
    payload = {"current": page, "pageSize": size,
               "channelCode": [channel], "webSiteCode": [website]}
    try:
        r = session.post(url, json=payload, timeout=30,
                         headers={"Referer": referer,
                                  "Content-Type": "application/json"})
    except Exception as exc:                     # noqa: BLE001
        print(f"    第 {page} 页失败 {type(exc).__name__}")
        return {}
    if r.status_code != 200:
        print(f"    第 {page} 页 http {r.status_code}")
        return {}
    try:
        return (r.json() or {}).get("data") or {}
    except Exception:                           # noqa: BLE001
        return {}


def clean_html_text(html: str) -> str:
    """把接口里的正文 HTML 压成纯文本。"""
    if not isinstance(html, str):
        return ""
    h = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    h = re.sub(r"<(script|style)\b.*?</\1>", "", h, flags=re.DOTALL | re.IGNORECASE)
    h = re.sub(r"<(br|/p|/div|/li|/tr)\s*/?>", "\n", h, flags=re.IGNORECASE)
    t = TAG_RE.sub("", h)
    t = t.replace("&nbsp;", " ").replace("&ensp;", " ").replace("&emsp;", " ")
    t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return WS_RE.sub(" ", t).strip()


def result_to_item(base: str, site: str, src: dict) -> dict | None:
    """把一条 `results[].source` 转成标准条目。"""
    title = (src.get("title") or "").strip()
    title = TAG_RE.sub("", title).strip()
    if not title or not _ncf.is_title(title):
        return None
    pub = str(src.get("pubDate") or "")[:10].replace("/", "-")
    if not re.match(r"^20\d{2}-\d{2}-\d{2}$", pub):
        pub = None
    urls = src.get("urls")
    path = ""
    if isinstance(urls, dict):
        path = urls.get("pc") or urls.get("wap") or ""
    elif isinstance(urls, str):
        path = urls
    if not path:
        path = f"/content/{src.get('id')}.html"
    if path.startswith("http"):
        url = path
    else:
        url = base.rstrip("/") + "/" + path.lstrip("/")
    return {"title": title, "url": url, "date": pub, "source": site,
            "docno": "", "content_html": (src.get("content") or {}).get("content", "")
            if isinstance(src.get("content"), dict) else ""}


def save_texts(site: str, items: list[dict]) -> int:
    """把接口自带的正文落盘，写回 `text_file` / `text_chars`。"""
    out = ROOT / "var" / "data" / "national" / "api-text"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for x in items:
        txt = clean_html_text(x.pop("content_html", ""))
        if len(txt) < 80:
            continue
        key = hashlib.sha256(x["url"].encode()).hexdigest()[:16]
        f = out / f"{key}.txt"
        f.write_text(txt, encoding="utf-8")
        x["text_file"] = str(f.relative_to(ROOT))
        x["text_chars"] = len(txt)
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--base", required=True, help="站点根，如 https://www.yichun.gov.cn")
    ap.add_argument("--website-code", required=True)
    ap.add_argument("--channel", required=True)
    ap.add_argument("--referer", default="")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--page-size", type=int, default=20)
    ap.add_argument("--gap", type=float, default=1.0)
    args = ap.parse_args()

    referer = args.referer or args.base
    session = creq.Session(impersonate="chrome")
    items: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, args.max_pages + 1):
        data = fetch_page(session, args.base, args.website_code, args.channel,
                          page, args.page_size, referer)
        if not data:
            break
        if total is None:
            total = int(data.get("total") or 0)
            print(f"  {args.site}: 接口报共 {total} 条")
        got = 0
        for r in data.get("results") or []:
            src = r.get("source") or {}
            x = result_to_item(args.base, args.site, src)
            if not x or x["url"] in seen:
                continue
            seen.add(x["url"])
            items.append(x)
            got += 1
        print(f"    第 {page} 页 +{got} 条（累计 {len(items)}）")
        if not got or (total and len(items) >= total):
            break
        time.sleep(args.gap)
    if not items:
        print("结果: 0 条")
        return 1
    ntext = save_texts(args.site, items)
    res = ncs.merge_and_save(args.site, args.base + "/" + args.channel,
                             items, engine="json-api")
    summary = {"site": args.site, "items": len(items), "texts": ntext,
               "total": res["items_total"], "new": res["items_new"]}
    print("结果: " + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
