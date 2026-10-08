"""适配器：**中国气象局·回应关切（常见问题）**（静态列表 + 明细页，答复在明细里）。

## 站点事实（2026-10-09 实测，证据 recon/nat-cma-*）
 · 入口 `http://www.cma.gov.cn/wmhd/gzly/`（公众留言）。
   门户页只是「留言须知」：局长信箱要登录、其他留言走表单，**都不符合判据**；
   但页面里给了「我们梳理了一些网友常见问题并给予回复」→ **回应关切** `wmhd/gzly/cjwt/`。
 · 列表（**静态页**，免登录）：`http://www.cma.gov.cn/wmhd/gzly/cjwt/`
   页尾 `createPageHTML(2, 0, "index", "html")` ⇒ 共 **2 页**：
   p1=`.../cjwt/`（或 index.html），p2=`.../cjwt/index_1.html`。
   每条 `<a href="./YYYYMM/tYYYYMMDD_NNNNNNN.html">标题</a>`（在 `.con_list_news_zt` 里）。
 · 明细（**问答原文**）：`<div class="view TRS_UEDITOR …">` 内分段
   `内容：<问题>` + `回复：<答复>` + `留言日期：… 回复时间：… 回复单位：…`。
 · ⚠ 本栏目量小（约 30~40 条），但答复规范（科普部/宣传科普中心），属可用源。
 · 另有 `cmastd.cmatc.cn`（气象标准化网）用户留言板，答复为空/一句话，**未纳入**。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "nat-cma",
    "name": "中国气象局·回应关切",
    "kind": "static",
    "level": "national",
    "entry": "http://www.cma.gov.cn/wmhd/gzly/cjwt/",
    "status": "ok",
    "note": "静态列表 cjwt/（createPageHTML 2 页）+ 明细 .view.TRS_UEDITOR 内「内容：/回复：」",
}

BASE = "http://www.cma.gov.cn/wmhd/gzly/cjwt/"
PAUSE = 1.2

LINK_RE = re.compile(r'href="(\./\d{6}/t\d{8}_\d+\.html)"[^>]*>([^<]*)', re.I)
VIEW_RE = re.compile(r'<div[^>]*class="[^"]*TRS_UEDITOR[^"]*"[^>]*>(.*?)</div>', re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", re.S | re.I)
ID_RE = re.compile(r"t\d{8}_(\d+)\.html", re.I)


def _text(html: str | None) -> str:
    if not html:
        return ""
    t = SCRIPT_RE.sub(" ", html)
    t = re.sub(r"</?p[^>]*>", " ", t, flags=re.I)
    t = TAG_RE.sub(" ", t)
    t = t.replace("&nbsp;", " ").replace("&emsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def _parse_detail(html: str) -> dict:
    m = VIEW_RE.search(html)
    body = _text(m.group(1) if m else html)
    q = a = asked = answered = dept = None
    mq = re.search(r"内容[:：]\s*(.*?)\s*回复[:：]", body, re.S)
    if mq:
        q = mq.group(1).strip()
    ma = re.search(r"回复[:：]\s*(.*?)\s*(?:留言日期|回复时间|回复单位|$)", body, re.S)
    if ma:
        a = ma.group(1).strip()
    mt = re.search(r"留言日期[:：]\s*([\d\-./]+)", body)
    if mt:
        asked = mt.group(1)
    mt = re.search(r"回复时间[:：]\s*([\d\-./]+)", body)
    if mt:
        answered = mt.group(1)
    mt = re.search(r"回复单位[:：]\s*([^ ]{1,40})", body)
    if mt:
        dept = mt.group(1).strip()
    return {"question": q, "answer": a, "asked_at": asked, "answered_at": answered, "dept": dept}


def _list_page(fetch, url: str) -> list[tuple[str, str]]:
    r = fetch(url, headers={"Referer": SITE["entry"]})
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 列表 {url} HTTP {getattr(r, 'status_code', '?')}（停）")
        return []
    seen: dict[str, str] = {}
    for href, title in LINK_RE.findall(r.text or ""):
        full = urljoin(url, href)
        seen[full] = _text(title)
    return list(seen.items())


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取中国气象局回应关切（问题 + 答复原文）。"""
    # createPageHTML(2,…) ⇒ 2 页：p1=cjwt/，p2=cjwt/index_1.html
    urls = [BASE, urljoin(BASE, "index_1.html")]
    pairs: dict[str, str] = {}
    for i, u in enumerate(urls):
        for full, title in _list_page(fetch, u):
            pairs.setdefault(full, title)
        if i + 1 < len(urls):
            time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 列表 {len(pairs)} 条")
    out: list[dict] = []
    for url, title in pairs.items():
        if limit and len(out) >= limit:
            break
        time.sleep(PAUSE)
        d = fetch(url, headers={"Referer": BASE})
        if getattr(d, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 明细 {url[-40:]} HTTP {d.status_code}（跳过）")
            continue
        info = _parse_detail(d.text or "")
        if len(info["answer"] or "") < 10:
            print(f"    [{SITE['key']}] {url[-40:]} 未取到答复正文（跳过）")
            continue
        mid = ID_RE.search(url)
        out.append({
            "source": SITE["key"],
            "id": mid.group(1) if mid else url,
            "url": url,
            "question": info["question"] or title,
            "answer": info["answer"],
            "asked_at": info["asked_at"],
            "answered_at": info["answered_at"],
            "dept": info["dept"],
            "channel": "回应关切",
            "extra": {"title": title, "platform": "cma-static"},
        })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
