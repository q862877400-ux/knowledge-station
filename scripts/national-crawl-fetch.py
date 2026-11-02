"""全国规范性文件栏目 —— 阶段 2/3：**抓列表 + 下附件**（2026-11-02）。

## 输入

`docs/channels/data/national-discover.json`（阶段 1 的发现结果）。
默认只抓 `status=ok` 且 `board_kind=normative` 的站（真·规范性文件栏目）。

## 每站做什么

1. 抓栏目列表页，翻页（`?page=N` / `index_N.html` 两种，最多 `--pages` 页）；
2. 从列表抽条目：标题 / 链接 / 日期（日期可能在链接外层的 `<span>` 里，
   所以取锚点前后 160 字符窗口一起看）；
3. **只留文件名式的条目**（标题 8~120 字，且不是导航词）；
4. 逐条抓详情页，抽附件链接（`.pdf .doc .docx .xls .xlsx .zip .rar .wps .ofd`）；
5. 下载附件：单文件 ≤ `--max-mb`，单站 ≤ `--max-files` 个；落盘
   `var/data/national/<省份>/<站点>/attachments/<sha256前16>_<原名>`；
6. 写 `items.jsonl`（每行一条：标题/日期/URL/附件清单）与 `site.json`（统计）。

## 硬约束

- 同主机串行 + 1 秒间隔；不同站可并行（`--concurrency`）。
- 遇验证码/WAF 记 `blocked` 并停，**不绕**。
- 不下载可执行文件；超限跳过并记 `too_large` / `too_many`。
- **不改生产库**：全部落文件，DB 导入另做（见计划 R5）。

## 用法

    .venv\\Scripts\\python.exe scripts/national-crawl-fetch.py --limit 5
    .venv\\Scripts\\python.exe scripts/national-crawl-fetch.py --pages 3 --max-files 30
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.update.announce import default_transport  # noqa: E402

DISCOVER = ROOT / "docs" / "channels" / "data" / "national-discover.json"
OUTDIR = ROOT / "var" / "data" / "national"

LINK_RE = re.compile(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})")
NAV_WORDS = ("首页", "上一页", "下一页", "尾页", "更多", "返回", "登录", "注册",
             "网站地图", "无障碍", "打印", "关闭", "分享", "搜索", "导航")
#: 条目级过滤：**要**这些词（条例/办法/规定/规范/标准/细则/规则/制度/决定/通知/意见）
KEEP_WORDS = ("条例", "办法", "规定", "规范", "标准", "细则", "规则", "制度",
              "决定", "通知", "意见", "公告", "命令", "方案", "规划")
#: **不要**这些（人事/事务类，业主明确不要新闻公告）
DROP_WORDS = ("任免", "招聘", "招录", "表彰", "会议", "培训", "预算", "决算",
              "招标", "采购", "中标", "成交", "名单", "公示", "考察", "述职",
              "民主生活会", "党建", "党史", "工会", "共青团", "妇联")
ATT_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".wps", ".ofd")
BLOCK_HINT = ("captcha", "验证码", "安全认证", "访问过于频繁", "Access Denied")

TIMEOUT_S = 25.0


def text_of(html: str) -> str:
    return " ".join(TAG_RE.sub(" ", html).split())


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def is_title(t: str) -> bool:
    """算不算「一条文件」的标题（长度 + 非导航 + 规范性文件词过滤）。"""
    if not (8 <= len(t) <= 120):
        return False
    if any(w in t for w in NAV_WORDS):
        return False
    if any(w in t for w in DROP_WORDS):
        return False
    return any(w in t for w in KEEP_WORDS)


def parse_items(html: str, base: str) -> list[dict]:
    """从列表页抽条目。日期取锚点前后窗口里的第一处。"""
    items: list[dict] = []
    seen: set[str] = set()
    for m in LINK_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        url = urljoin(base, href.strip())
        if not url.startswith("http"):
            continue
        title = norm_title(text_of(inner))
        if not is_title(title):
            continue
        if url in seen:
            continue
        seen.add(url)
        win = html[max(0, m.start() - 160): m.end() + 160]
        dm = DATE_RE.search(text_of(win))
        if not dm:
            # ⚠ **没有日期的一律不当条目**（2026-11-02 实测临汾）：
            #   不加这条，导航链接（「山西省人民政府网」「办公室文件」）会被当成文件，
            #   30 条"条目"里 0 条是真的，附件自然是 0 个。
            continue
        date = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        items.append({"title": title, "url": url, "date": date})
    return items


def main_text(html: str) -> str:
    """从详情页抽正文（去脚本/样式/标签，保留段落换行）。

    ⚠ 为什么正文字段是**主产物**（2026-11-02 实测）：这类规范性文件的正文
    直接就在网页里，抽查详情页 `.pdf`/`.doc`/`附件` 各出现 0 次 ——
    只盯附件会一无所获。
    """
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    h = re.sub(r"(?i)</(p|div|br|tr|li|h[1-6])>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"&nbsp;?", " ", h)
    h = re.sub(r"[ \t\u3000]+", " ", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


#: 页面尾部/头部样板（正文净化用）
BOILER = ("版权所有", "主办单位", "承办单位", "网站标识码", "ICP备", "公网安备",
          "网站地图", "联系我们", "关于我们", "中国政府网", "省政府", "市政府",
          "无障碍", "长者模式", "扫码", "关注我们", "返回顶部", "打印本页")


def clean_body(txt: str, title: str) -> str:
    """去掉导航/页脚样板，尽量只留正文。

    ⚠ 第一版直接全页去标签，实测 6330 字里前 300 字全是「中国政府网 | 山西省政府 |
    长治市政府 | 今天是…」这类导航。政府站正文夹在导航中间，需要按行过滤。
    """
    lines = [ln.strip() for ln in txt.splitlines()]
    # 去掉过短行（导航/按钮）与样板行
    kept = [ln for ln in lines
            if len(ln) >= 8 and not any(w in ln for w in BOILER)]
    if not kept:
        return ""
    # 若有标题行，从标题起截（很多页面正文以标题开头）
    key = title[:14]
    for i, ln in enumerate(kept):
        if key and key in ln:
            kept = kept[i:]
            break
    out = "\n".join(kept)
    return out[:20000]          # 单条上限 2 万字（防异常长页）


#: 翻页规则候选（**每站要标定**：2026-11-02 实测三亚 `?page=2` 与第 1 页 30/30 重合）
PAGE_RULES = (
    # ⚠ 2026-11-02 R6 实测：三门峡用 `?pageNum=`，我前一轮的 10 种里**没有它**
    #   （页面 JS 原文 `location.href = '/pageView/zcwjList.html?pageNum=' + n`）。
    ("query", "pageNum"),
    ("query", "page"),
    ("query", "curPage"),
    ("query", "pageNo"),
    ("query", "p"),
    ("query", "pn"),
    ("query", "currentPage"),
    ("query", "pageIndex"),
    ("query", "pageNo"),
    ("index", "_"),          # index_2.shtml
    ("suffix", "_"),         # zcwj.shtml → zcwj_2.shtml（政府站最常见）
    ("suffixdash", "-"),     # zcwj.shtml → zcwj-2.shtml
    ("path", ""),            # /2.html
)


def _page_url(board: str, rule: tuple, n: int) -> str:
    """按规则生成第 n 页 URL。"""
    kind, key = rule
    u = urlsplit(board)
    path = u.path
    if kind == "query":
        sep = "&" if u.query else "?"
        base = f"{u.scheme}://{u.netloc}{path}"
        return f"{base}{sep}{key}={n}"
    if kind == "index":
        if re.search(r"index(_\d+)?\.(s?html?)$", path):
            g = re.sub(r"index(_\d+)?\.(s?html?)$",
                       lambda m: f"index_{n}.{m.group(2)}", path)
            return f"{u.scheme}://{u.netloc}{g}"
        return ""
    if kind in ("suffix", "suffixdash"):
        if re.search(r"\.(s?html?)$", path):
            g = re.sub(r"\.(s?html?)$", f"{key}{n}.\\1", path)
            return f"{u.scheme}://{u.netloc}{g}"
        return ""
    if kind == "path":
        if re.search(r"\.s?html?$", path):
            g = re.sub(r"/([^/]+)\.(s?html?)$", rf"/{n}.\2", path)
            return f"{u.scheme}://{u.netloc}{g}"
    return ""


#: 页面 JS 里常见的翻页写法：`location.href='...?pageNum='+n` / `xxx?page=' + i`
JS_TPL_RE = re.compile(
    r"""(?:location(?:\.href)?\s*=|window\.location\s*=|\.href\s*=)\s*"""
    r"""["']([^"']+?)["']\s*\+""", re.I)


def js_page_template(html: str, base: str) -> str | None:
    """从页面 JS 里捞「翻页 URL 模板」。

    返回一个可以用 `%d` 填页号的模板（已转成绝对 URL），捞不到返回 None。
    实测样例：三门峡 `location.href = '/pageView/zcwjList.html?pageNum=' + n`
    ⇒ 模板 `https://www.smx.gov.cn/pageView/zcwjList.html?pageNum=%d`。
    """
    for m in JS_TPL_RE.finditer(html):
        frag = m.group(1).strip()
        if not frag or frag.startswith(("#", "javascript")):
            continue
        absu = urljoin(base, frag)
        # 模板必须以「=」或「/」结尾，页号才接得上
        if absu.endswith(("=", "/")) and "?" in absu or absu.endswith("/"):
            return absu + "%d"
    return None


def tpl_candidates(tpl: str, board: str) -> list[str]:
    """由 JS 模板 + 原栏目参数，生成可试的翻页模板。

    为什么需要（2026-11-02 R6→R7）：三门峡模板是 `…?pageNum=%d`，但真实请求还要带
    原栏目的 `lmid=8200&searchType=1`；只用模板本身会拿到空页，
    于是一直判「规则不成立」。
    """
    out = [tpl]
    q = urlsplit(board).query
    if q:
        # 模板里已带该参数就不重复拼
        extra = "&".join(pair for pair in q.split("&")
                         if pair.split("=")[0] not in tpl)
        if extra:
            out.append(tpl + "&" + extra)
    return list(dict.fromkeys(out))


def calibrate_pagination(transport, board: str, first_urls: set[str],
                         html: str | None = None) -> dict:
    """标定该站的翻页规则：找到能**真正换页**的那一种。

    先试**从页面 JS 提取的模板**（最可靠，是站点自己的写法），再退回猜参数。

    判据：第 2 页里**至少有一条**第 1 页没有的 URL，且不是同一批内容。
    返回 {rule, page2_url, overlap, ok}。
    """
    # ① 页面 JS 里提取的模板优先
    if html:
        tpl0 = js_page_template(html, board)
        for tpl in (tpl_candidates(tpl0, board) if tpl0 else []):
            u2 = tpl % 2
            try:
                st, body = transport.fetch(u2, timeout=TIMEOUT_S)
            except Exception:                   # noqa: BLE001
                continue
            if st != 200 or not isinstance(body, str):
                continue
            got = {x["url"] for x in parse_items(body, u2)}
            new = got - first_urls
            if new and len(got & first_urls) < len(got):
                return {"rule": ["jstpl", tpl], "page2_url": u2,
                        "overlap": len(got & first_urls), "new": len(new),
                        "ok": True}
    # ② 退回猜参数
    for rule in PAGE_RULES:
        u2 = _page_url(board, rule, 2)
        if not u2:
            continue
        try:
            st, body = transport.fetch(u2, timeout=TIMEOUT_S)
        except Exception:                       # noqa: BLE001
            continue
        if st != 200 or not isinstance(body, str):
            continue
        got = {x["url"] for x in parse_items(body, u2)}
        if not got:
            continue
        new = got - first_urls
        overlap = len(got & first_urls)
        if new and overlap < len(got):
            return {"rule": list(rule), "page2_url": u2,
                    "overlap": overlap, "new": len(new), "ok": True}
    return {"rule": None, "page2_url": None, "overlap": None, "new": 0, "ok": False}


#: 「下一页」的锚文本
NEXT_WORDS = ("下一页", "下页", "后一页", "Next", "next", "»")


def find_next(html: str, base: str) -> str | None:
    """从页面里找**下一页**的真实 URL。

    为什么用这个而不是猜参数（2026-11-02 实测）：10 种参数规则在这批政府站上
    **一种都没命中**（三亚 `?page=2` 与第 1 页 30/30 重合）。而页面自己一定有
    「下一页」链接（要么是静态 href，要么在 onclick 里）—— 跟着它走就不用猜。
    """
    for m in LINK_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        txt = text_of(inner).strip()
        near = html[m.start(): m.start() + 300]
        if not (any(w in txt for w in NEXT_WORDS)
                or re.search(r'class=["\'][^"\']*next', near, re.I)):
            continue
        href = href.strip()
        if href.lower().startswith("javascript"):
            # onclick/href 里可能塞了 URL
            mm = re.search(r"""(?:location(?:\.href)?\s*=|open\()\s*["']([^"']+)["']""",
                           near, re.I)
            if not mm:
                continue
            href = mm.group(1)
        if not href or href.startswith("#"):
            continue
        url = urljoin(base, href)
        if url != base:
            return url
    return None


def page_variants(board: str, pages: int) -> list[str]:
    """生成翻页 URL：`?page=N` 与 `index_N.html` 两种常见形态。"""
    out = [board]
    u = urlsplit(board)
    for n in range(2, pages + 1):
        if re.search(r"index(_\d+)?\.s?html?$", u.path):
            nxt = re.sub(r"index(_\d+)?\.(s?html?)$",
                         lambda mm: f"index_{n}.{mm.group(2)}", board)
        else:
            sep = "&" if "?" in board else "?"
            nxt = f"{board}{sep}page={n}"
        if nxt != board and nxt not in out:
            out.append(nxt)
    return out


def find_attachments(html: str, base: str) -> list[str]:
    """详情页里的附件链接（按扩展名）。"""
    out: list[str] = []
    for href, _inner in LINK_RE.findall(html):
        url = urljoin(base, href.strip())
        path = urlsplit(url).path.lower()
        if path.endswith(ATT_EXT) and url not in out:
            out.append(url)
    return out


def crawl_site(transport, rec: dict, *, pages: int, max_files: int,
               max_mb: float, per_site_items: int,
               barren_stop: int = 3) -> dict:
    """抓一个站：列表 → 详情 → 附件。返回统计（不抛异常）。"""
    site = rec["site"]
    board = rec.get("board_url") or ""
    prov = rec.get("province") or "未知"
    sdir = OUTDIR / str(prov) / str(site).replace("/", "_")
    adir = sdir / "attachments"
    stats = {"site": site, "province": prov, "board": board,
             "status": None, "pages": 0, "items": 0, "attachments": 0,
             "bytes": 0, "texts": 0, "text_chars": 0,
             "skipped": [], "error": None}
    if not board:
        stats["status"] = "no_board"
        return stats

    # 存量：先读上次的结果（**累积**，同时用于算增量）
    prev_items: list[dict] = []
    if (sdir / "items.jsonl").exists():
        for ln in (sdir / "items.jsonl").read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                try:
                    prev_items.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    started = time.strftime("%Y-%m-%d %H:%M:%S")

    seen: set[str] = set()
    items: list[dict] = []
    barren = 0
    # ── 第 1 页 + 翻页规则标定（**每站一条规则，记进 site-state 供复用**）──
    try:
        st0, b0 = transport.fetch(board, timeout=TIMEOUT_S)
    except Exception as exc:                      # noqa: BLE001
        stats.update({"status": "unreachable",
                      "error": f"{type(exc).__name__}: {str(exc)[:80]}"})
        return stats
    if st0 != 200 or not isinstance(b0, str):
        stats.update({"status": "unreachable", "error": f"http_{st0}"})
        return stats
    first_items = parse_items(b0, board)
    # 第 1 页的内容直接入列（省一次请求）
    for x in first_items:
        seen.add(x["url"])
        items.append(x)
    stats["pages"] = 1
    first_urls = {x["url"] for x in first_items}
    cal = calibrate_pagination(transport, board, first_urls, html=b0)
    stats["pagination"] = cal
    # ── 翻页：先按标定出的规则翻，规则不可用再跟「下一页」链接 ──
    n_pages = 1
    fetched = 0
    if cal.get("ok") and pages > 1:
        kind = cal["rule"][0]
        for n in range(2, pages + 1):
            u = (cal["rule"][1] % n) if kind == "jstpl" else _page_url(
                board, tuple(cal["rule"]), n)
            if not u:
                break
            fetched += 1
            try:
                st, body = transport.fetch(u, timeout=TIMEOUT_S)
            except Exception:                    # noqa: BLE001
                break
            if st != 200 or not isinstance(body, str):
                break
            fresh = [x for x in parse_items(body, u) if x["url"] not in seen]
            if not fresh:
                barren += 1
                if barren >= barren_stop:
                    break
            else:
                barren = 0
                for x in fresh:
                    seen.add(x["url"])
                    items.append(x)
                if per_site_items and len(items) >= per_site_items:
                    break
            n_pages = n
            stats["pages"] = n_pages
            time.sleep(1.0)
    else:
        nxt = find_next(b0, board)
        while nxt and n_pages < pages:
            try:
                st, body = transport.fetch(nxt, timeout=TIMEOUT_S)
            except Exception:                    # noqa: BLE001
                break
            if st != 200 or not isinstance(body, str):
                break
            fresh = [x for x in parse_items(body, nxt) if x["url"] not in seen]
            if not fresh:
                barren += 1
                if barren >= barren_stop:
                    break
            else:
                barren = 0
                for x in fresh:
                    seen.add(x["url"])
                    items.append(x)
                if per_site_items and len(items) >= per_site_items:
                    break
            n_pages += 1
            stats["pages"] = n_pages
            time.sleep(1.0)
            nxt = find_next(body, nxt)
    stats.setdefault("pagination", {"mode": "rule", "pages": n_pages,
                                    "reached_end": n_pages < pages})
    items = items[:per_site_items]
    stats["items"] = len(items)
    if not items:
        # 抽不到**带日期**的条目 ⇒ 那个栏目多半是 JS 渲染（临汾就是这种）
        stats["status"] = "js_unparsable"
        return stats

    # ── 详情 → 附件 ──
    sdir.mkdir(parents=True, exist_ok=True)
    n_files = 0
    total_bytes = 0
    tdir = sdir / "text"
    for it in items:
        try:
            st, body = transport.fetch(it["url"], timeout=TIMEOUT_S)
            if st != 200 or not isinstance(body, str):
                it["attachments"] = []
                it["text_chars"] = 0
                continue
            # 正文落盘（内容本体）
            txt = clean_body(main_text(body), it["title"])
            it["text_chars"] = len(txt)
            if len(txt) >= 40:
                tdir.mkdir(parents=True, exist_ok=True)
                key = hashlib.sha256(it["url"].encode()).hexdigest()[:16]
                tf = tdir / (key + ".txt")
                tf.write_text(txt, encoding="utf-8")
                it["text_file"] = str(tf.relative_to(ROOT))
            atts = find_attachments(body, it["url"])
            saved: list[dict] = []
            for a in atts:
                if n_files >= max_files:
                    stats["skipped"].append({"url": a, "why": "too_many"})
                    continue
                try:
                    ast, ab = transport.fetch(a, timeout=TIMEOUT_S)
                except Exception:              # noqa: BLE001
                    stats["skipped"].append({"url": a, "why": "fetch_failed"})
                    continue
                if ast != 200 or not isinstance(ab, (bytes, bytearray)):
                    stats["skipped"].append({"url": a, "why": f"http_{ast}"})
                    continue
                if len(ab) > max_mb * 1024 * 1024:
                    stats["skipped"].append({"url": a, "why": "too_large"})
                    continue
                h = hashlib.sha256(ab).hexdigest()
                name = Path(urlsplit(a).path).name or "file"
                fn = f"{h[:16]}_{name}"
                adir.mkdir(parents=True, exist_ok=True)
                (adir / fn).write_bytes(ab)
                n_files += 1
                total_bytes += len(ab)
                saved.append({"url": a, "file": str((adir / fn).relative_to(ROOT)),
                              "bytes": len(ab), "sha256": h})
            it["attachments"] = saved
        except Exception:                          # noqa: BLE001
            it["attachments"] = []
    stats["attachments"] = n_files
    stats["texts"] = sum(1 for x in items if x.get("text_file"))
    stats["text_chars"] = sum(int(x.get("text_chars") or 0) for x in items)
    stats["bytes"] = total_bytes
    stats["status"] = "ok"

    # ── 累积合并：上次的 + 本次的（按 URL 去重）──
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    merged: dict[str, dict] = {x["url"]: x for x in prev_items if x.get("url")}
    new_this_run = 0
    for x in items:
        old = merged.get(x["url"])
        if old is None:
            x["first_seen"] = now
            new_this_run += 1
        else:
            x.setdefault("first_seen", old.get("first_seen") or now)
            if not x.get("text_file"):
                x["text_file"] = old.get("text_file")
            if not x.get("attachments"):
                x["attachments"] = old.get("attachments") or []
        merged[x["url"]] = x
    allitems = sorted(merged.values(), key=lambda y: (y.get("date") or ""),
                      reverse=True)
    (sdir / "items.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in allitems) + "\n",
        encoding="utf-8")

    dates = [x.get("date") for x in allitems if x.get("date")]
    snapshot = {
        "site": site, "board": board, "status": stats["status"],
        "run_at": now, "run_started": started,
        "pages_this_run": stats["pages"], "items_seen_this_run": len(items),
        "items_total": len(allitems),
        "items_new_this_run": new_this_run,
        "newest_date": max(dates) if dates else None,
        "oldest_date": min(dates) if dates else None,
        "pagination": stats.get("pagination"),
        "texts": sum(1 for x in allitems if x.get("text_file")),
        "attachments": sum(len(x.get("attachments") or []) for x in allitems),
    }
    (sdir / "site-state.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    stats["items_total"] = len(allitems)
    stats["items_new"] = new_this_run
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--pages", type=int, default=200,
                    help="最多翻多少页（存量要翻到底，默认 200）")
    ap.add_argument("--barren-stop", type=int, default=3,
                    help="连续多少页没有新条目就停（默认 3）")
    ap.add_argument("--max-files", type=int, default=20)
    ap.add_argument("--max-mb", type=float, default=30.0)
    ap.add_argument("--items", type=int, default=5000,
                    help="单站条目上限（存量默认 5000，0=不限）")
    ap.add_argument("--kind", default="normative",
                    help="normative / hub / all")
    args = ap.parse_args()

    d = json.loads(DISCOVER.read_text(encoding="utf-8"))
    sites = [r for r in d["results"]
             if r.get("status") == "ok"
             and (args.kind == "all" or r.get("board_kind") == args.kind)]
    if args.limit:
        sites = sites[: args.limit]
    print(f"待抓 {len(sites)} 站（kind={args.kind}，页≤{args.pages}，"
          f"附件≤{args.max_files}/站，单件≤{args.max_mb}MB）")

    transport = default_transport()
    host_locks: dict[str, threading.Lock] = {}
    guard = threading.Lock()

    def lock_for(h: str) -> threading.Lock:
        with guard:
            return host_locks.setdefault(h, threading.Lock())

    def work(rec: dict) -> dict:
        h = urlsplit(rec.get("board_url") or "").netloc
        with lock_for(h):
            return crawl_site(transport, rec, pages=args.pages,
                              max_files=args.max_files, max_mb=args.max_mb,
                              per_site_items=args.items,
                              barren_stop=args.barren_stop)

    t0 = time.monotonic()
    results = []
    with ThreadPoolExecutor(max_workers=args.concurrency,
                            thread_name_prefix="nat-fetch") as pool:
        futs = {pool.submit(work, s): s for s in sites}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            results.append(r)
            if i % 5 == 0 or i == len(sites):
                items = sum(x.get("items", 0) for x in results)
                atts = sum(x.get("attachments", 0) for x in results)
                mb = sum(x.get("bytes", 0) for x in results) / 1048576
                print(f"  {i}/{len(sites)}  条目 {items}  附件 {atts} ({mb:.1f}MB)  "
                      f"{time.monotonic() - t0:.0f}s")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    rep = OUTDIR / "crawl-report.json"
    rep.write_text(json.dumps({"generated_by": "scripts/national-crawl-fetch.py",
                               "counts": {
                                   "sites": len(results),
                                   "items": sum(x.get("items", 0) for x in results),
                                   "attachments": sum(
                                       x.get("attachments", 0) for x in results),
                                   "bytes": sum(x.get("bytes", 0) for x in results),
                                   "texts": sum(x.get("texts", 0) for x in results),
                                   "text_chars": sum(x.get("text_chars", 0)
                                                     for x in results)},
                               "results": sorted(results, key=lambda x: x["site"])},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("\n状态：", dict(Counter(x.get("status") for x in results).most_common()))
    print(f"→ {rep.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
