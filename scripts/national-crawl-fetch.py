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
#: 站点接入配置（**可复用**：跑过标定的站把规则存这里，下次直接读，不再现场重猜）
SITE_RULES = ROOT / "docs" / "channels" / "data" / "site-rules.json"
OUTDIR = ROOT / "var" / "data" / "national"

LINK_RE = re.compile(
    r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"(20\d{2})[-/年.](\d{1,2})[-/月.](\d{1,2})")
#: 只有年月、没有日（实测中山市：日期被拆成「08」+「2026年10月」两段）
DATE_YM_RE = re.compile(r"(20\d{2})[-/年.](\d{1,2})\s*月?")
NAV_WORDS = ("首页", "上一页", "下一页", "尾页", "更多", "返回", "登录", "注册",
             "网站地图", "无障碍", "打印", "关闭", "分享", "搜索", "导航")
#: 条目级过滤：**要**这些词（条例/办法/规定/规范/标准/细则/规则/制度/决定/通知/意见）
KEEP_WORDS = ("条例", "办法", "规定", "规范", "标准", "细则", "规则", "制度",
              "决定", "通知", "意见", "命令", "方案", "规划", "规章", "准则",
              "指导意见", "实施细则", "暂行办法", "管理办法", "工作规程")
#: **不要**这些（人事/事务类，业主明确不要新闻公告）
DROP_WORDS = ("任免", "招聘", "招录", "表彰", "会议", "培训", "预算", "决算",
              "招标", "采购", "中标", "成交", "名单", "公示", "考察", "述职",
              "民主生活会", "党建", "党史", "工会", "共青团", "妇联",
              # 2026-11-02 抽检补：这些是**事务类/临时性**，不是规范性文件
              "试鸣", "防空警报", "演练", "演习", "放假", "节假日", "作息",
              "停水", "停电", "停气", "封路", "交通管制", "限行", "提示",
              "提醒", "天气", "灾害预警", "应急响应", "值班", "走访", "慰问",
              "座谈", "论坛", "展销", "促销", "消费券", "补贴发放", "摇号",
              "抽签", "报名", "笔试", "面试", "体检", "公示名单", "结果公布")
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
            ym = DATE_YM_RE.search(text_of(win))
            if ym:                              # 只有年月 → 记 YYYY-MM（不编造日）
                date = f"{ym.group(1)}-{int(ym.group(2)):02d}"
                items.append({"title": title, "url": url, "date": date})
            continue
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
    if kind == "path" and re.search(r"\.s?html?$", path):
        g = re.sub(r"/([^/]+)\.(s?html?)$", rf"/{n}.\2", path)
        return f"{u.scheme}://{u.netloc}{g}"
    return ""


#: 页面 JS 里常见的翻页写法：`location.href='...?pageNum='+n` / `xxx?page=' + i`
JS_TPL_RE = re.compile(
    r"""(?:location(?:\.href)?\s*=|window\.location\s*=|\.href\s*=)\s*"""
    r"""["']([^"']+?)["']\s*\+""", re.IGNORECASE)


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


def load_site_rules() -> dict[str, tuple]:
    """读站点规则表 → {站点名: (规则名, 参数)}。

    规则名对应 `PAGE_RULES` 里的 (kind, key)，例如 `("index", "_")`。
    读不到/格式不对一律返回空表（fail-open：退回现场标定，不报错中断）。
    """
    try:
        rows = json.loads(SITE_RULES.read_text(encoding="utf-8"))
    except Exception:                            # noqa: BLE001
        return {}
    out: dict[str, tuple] = {}
    for r in rows if isinstance(rows, list) else []:
        rule = r.get("rule")
        if isinstance(rule, list) and len(rule) == 2:
            out[str(r.get("site"))] = (str(rule[0]), str(rule[1]))
            continue
        if not isinstance(rule, str):
            continue
        for cand in PAGE_RULES:
            if cand[0] == rule:      # 兼容旧格式（只有 kind，参数名会丢）
                out[str(r.get("site"))] = cand
                break
    return out


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


def is_same_column(orig: str, cand: str) -> bool:
    """翻页候选**必须仍是同一栏目**，且不得丢掉原栏目的查询参数。

    ⚠ 为什么必须有这条（2026-11-02 R17 假绿教训）：我拼候选地址时丢掉了
    `?pageId=…`，抓到的是**另一个页面**（内容完全不同），却当成"翻到第 2 页"、
    "新增 4 条"记进了结论。加这条判据后，那种情况会被直接拒掉。

    判据：
      1. 同主机；
      2. 路径相同，或只在原文件名主干部位扩展（`index`→`index_2`、`x`→`x_2`）；
      3. 原栏目的每个查询参数（同名同值）都必须还在候选里 —— **不许丢参数**。
    """
    o, c = urlsplit(orig), urlsplit(cand)
    if o.netloc.lower() != c.netloc.lower():
        return False
    op, cp = o.path.rstrip("/"), c.path.rstrip("/")
    if op != cp:
        stem = op.rsplit(".", 1)[0]
        if not (cp.startswith(stem) or cp == op):
            return False
    from urllib.parse import parse_qsl
    oq = dict(parse_qsl(o.query, keep_blank_values=True))
    cq = dict(parse_qsl(c.query, keep_blank_values=True))
    for k, v in oq.items():
        if cq.get(k) != v:
            return False
    return True


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
            except Exception:  # noqa: BLE001, S112
                continue
            if st != 200 or not isinstance(body, str):
                continue
            if not is_same_column(board, u2):
                continue          # 换了栏目（丢参数/换页面）→ 不算翻页
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
        except Exception:  # noqa: BLE001, S112
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
                or re.search(r'class=["\'][^"\']*next', near, re.IGNORECASE)):
            continue
        href = href.strip()
        if href.lower().startswith("javascript"):
            # onclick/href 里可能塞了 URL
            mm = re.search(r"""(?:location(?:\.href)?\s*=|open\()\s*["']([^"']+)["']""",
                           near, re.IGNORECASE)
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
                         lambda mm, _n=n: f"index_{_n}.{mm.group(2)}", board)
        else:
            sep = "&" if "?" in board else "?"
            nxt = f"{board}{sep}page={n}"
        if nxt != board and nxt not in out:
            out.append(nxt)
    return out


#: 附件下载链接的**非扩展名**形态（政府站常见）
ATT_URL_RE = re.compile(
    r"(downfile\.jsp)|(/download(?:\.do|\.jsp|\.php)?\b)|(/attach(?:ment)?/)"
    r"|(getfile\.(?:jsp|do|php))|(fileDownload)|(downfile)",
    re.IGNORECASE)


# ---------------------------------------------------------------- 二进制下载
#: ⚠ **教训（2026-11-02 R10→R11）**：`announce.default_transport().fetch()` 返回的是
#: `resp.json()` 或 `resp.text` —— **永远不是字节**。所以附件（PDF/Word）拿到的是
#: 乱码字符串，被 `isinstance(ab, bytes)` 一律跳过 ⇒ 全量跑 129 站"附件 0 成功"。
#: 附件必须自己用 curl_cffi 取 `resp.content`。
try:
    from curl_cffi import requests as _creq
    _BIN_SESSION = _creq.Session(impersonate="chrome")
except Exception:                                # noqa: BLE001
    _BIN_SESSION = None


def fetch_bytes(url: str, referer: str | None = None,
                timeout: float = TIMEOUT_S) -> tuple[int, bytes, str]:
    """取二进制（附件用）。返回 (状态码, 字节, content-type)。

    带 Referer：实测丽江 `…/files` 不带来源页直接 **403**。
    """
    if _BIN_SESSION is None:
        return 0, b"", ""
    headers = {"Referer": referer} if referer else {}
    try:
        r = _BIN_SESSION.get(url, timeout=timeout, headers=headers,
                             allow_redirects=True)
    except Exception:                            # noqa: BLE001
        return 0, b"", ""
    return r.status_code, r.content or b"", (r.headers or {}).get("content-type", "")


def true_ext(data: bytes, ctype: str) -> str:
    """按文件头给正确扩展名（下载接口的 URL 常以 .jsp/.do 结尾，名字带不出类型）。"""
    low = (ctype or "").lower()
    if data[:5] == b"%PDF":
        return ".pdf"
    if data[:4] == b"PK\x03\x04":
        if b"word/" in data[:4000]:
            return ".docx"
        if b"xl/" in data[:4000]:
            return ".xlsx"
        return ".zip"
    if data[:4] == b"\xd0\xcf\x11\xe0":
        # OLE 复合文档：**必须看内部流名**，只看 content-type 会把 .doc 全判成 .xls
        # （2026-11-02 实测：一次清理把 83 个 Word 改名成了 Excel）
        # ⚠ 两条实测教训（2026-11-02 R12→R13）：
        #   ① OLE 目录项常在**文件尾部** ⇒ 只读前 400KB 会 0 命中；
        #   ② 目录项名字是 **UTF-16LE** ⇒ 搜 `b"WordDocument"` 永远搜不到。
        w = "WordDocument".encode("utf-16-le")
        x = "Workbook".encode("utf-16-le")
        bk = "Book".encode("utf-16-le")
        if w in data:
            return ".doc"
        if x in data or bk in data:
            return ".xls"
        return ".doc" if ("word" in low or "msword" in low) else ".xls"
    if data[:5] == b"{\\rtf":
        return ".rtf"
    return ""


def looks_like_file(data: bytes, ctype: str) -> bool:
    """判断下载到的是不是真文件（而不是 HTML 错误页/预览页）。"""
    low = (ctype or "").lower()
    if "text/html" in low:
        return False
    head = data[:8]
    if head.startswith((b"%PDF", b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"{\rtf")):
        return True                              # PDF / zip(docx,xlsx) / OLE / rtf
    head2k = data[:2000].lower()
    if any(m in head2k for m in (b"<html", b"<!doctype", b"<head", b"<body")):
        return False
    return len(data) > 1024 and "octet-stream" in low or len(data) > 4096


def find_attachments(html: str, base: str) -> list[str]:
    """详情页里的附件链接。

    两种形态都认（2026-11-02 R10 补）：
      1. **路径以扩展名结尾**：`.pdf .doc .xls .zip .ofd …`
      2. **下载接口形态**：`downfile.jsp?…`、`/download.do?…`、`/attach/0/…`、
         `getfile.jsp?…`、`fileDownload` —— 这些 URL 不以扩展名收尾，
         第一版只认扩展名，所以附件数一直是 0。
    """
    out: list[str] = []
    for href, _inner in LINK_RE.findall(html):
        url = urljoin(base, href.strip())
        if not url.startswith("http"):
            continue
        path = urlsplit(url).path.lower()
        if ((path.endswith(ATT_EXT) or ATT_URL_RE.search(url))
                and url not in out):
            out.append(url)
    return out


def crawl_site(transport, rec: dict, *, pages: int, max_files: int,
               max_mb: float, per_site_items: int,
               barren_stop: int = 3, list_only: bool = False,
               preset_rule: tuple | None = None) -> dict:
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
    if preset_rule:
        # 读配置：不再现场标定（这就是"可复用接入能力"落到实处）
        nxt_u = _page_url(board, preset_rule, 2)
        cal = {"rule": list(preset_rule), "ok": True, "source": "site-rules.json",
               "page2_url": nxt_u, "overlap": None, "new": None}
    else:
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
    if list_only:
        stats["status"] = "list_only_ok" if items else "js_unparsable"
        sdir.mkdir(parents=True, exist_ok=True)
        # ⚠ 只抓列表**也要合并**（2026-11-02 R20 修）：原来直接覆盖 items.jsonl，
        #   历史条目会被冲掉，也就永远算不出"本次新增"——增量监测就废了。
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        merged: dict[str, dict] = {x["url"]: x for x in prev_items if x.get("url")}
        new_run = 0
        for x in items:
            old_it = merged.get(x["url"])
            if old_it is None:
                x["first_seen"] = now
                new_run += 1
            else:
                x.setdefault("first_seen", old_it.get("first_seen") or now)
                x["text_file"] = old_it.get("text_file")
                x["text_chars"] = old_it.get("text_chars")
                x["attachments"] = old_it.get("attachments") or []
            merged[x["url"]] = x
        allitems = sorted(merged.values(), key=lambda y: (y.get("date") or ""),
                          reverse=True)
        (sdir / "items.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in allitems) + "\n",
            encoding="utf-8")
        prev_snap = {}
        sp = sdir / "site-state.json"
        if sp.exists():
            try:
                prev_snap = json.loads(sp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prev_snap = {}
        dates = [x.get("date") for x in allitems if x.get("date")]
        sp.write_text(json.dumps({
            "site": site, "board": board, "status": stats["status"],
            "run_at": now, "pages_this_run": stats["pages"],
            "items_seen_this_run": len(items),
            "items_total": len(allitems), "items_new_this_run": new_run,
            "prev_items_total": prev_snap.get("items_total"),
            "newest_date": max(dates) if dates else None,
            "oldest_date": min(dates) if dates else None,
            "pagination": stats.get("pagination"),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        stats["items_total"] = len(allitems)
        stats["items_new"] = new_run
        return stats
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


def text_only_site(transport, sdir: Path, max_files: int,
                   max_mb: float, att_only: bool = False) -> dict:
    """给一个站已有条目补正文与附件（不重抓列表）。"""
    f = sdir / "items.jsonl"
    items = [json.loads(x) for x in
             f.read_text(encoding="utf-8").splitlines() if x.strip()]
    tdir = sdir / "text"
    adir = sdir / "attachments"
    got_text = 0
    got_att = 0
    chars = 0
    for it in items:
        if att_only:
            if it.get("attachments"):
                continue                       # 已有附件，跳过
        elif it.get("text_file") and it.get("text_chars"):
            continue
        if not it.get("url"):
            continue
        try:
            st, body = transport.fetch(it["url"], timeout=TIMEOUT_S)
        except Exception:  # noqa: BLE001, S112
            continue
        if st != 200 or not isinstance(body, str):
            continue
        if att_only:
            txt = ""
        else:
            txt = clean_body(main_text(body), it.get("title") or "")
            it["text_chars"] = len(txt)
        if not att_only and len(txt) >= 40:
            tdir.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha256(it["url"].encode()).hexdigest()[:16]
            tf = tdir / (key + ".txt")
            tf.write_text(txt, encoding="utf-8")
            it["text_file"] = str(tf.relative_to(ROOT))
            got_text += 1
            chars += len(txt)
        saved = []
        for a in find_attachments(body, it["url"]):
            if got_att >= max_files:
                break
            st2, data, ct = fetch_bytes(a, referer=it["url"])
            if st2 != 200:
                continue
            if not looks_like_file(data, ct):
                # 预览页 → 页内再找一层真文件（实测呼伦贝尔/四平是这种）
                inner = find_attachments(data.decode("utf-8", "ignore"), a)
                if not inner:
                    continue
                st2, data, ct = fetch_bytes(inner[0], referer=a)
                if st2 != 200 or not looks_like_file(data, ct):
                    continue
            if len(data) > max_mb * 1048576:
                continue
            h = hashlib.sha256(data).hexdigest()
            name = Path(urlsplit(a).path).name or "file"
            ext = true_ext(data, ct)
            # URL 名不可信（`.jsp`/`.do` 下载接口），按真实类型改名
            if ext and not name.lower().endswith(ext):
                stem = re.sub(r"\.[a-z0-9]{1,5}$", "", name, flags=re.IGNORECASE)
                name = f"{stem}{ext}"
            adir.mkdir(parents=True, exist_ok=True)
            (adir / f"{h[:16]}_{name}").write_bytes(data)
            saved.append({"url": a, "bytes": len(data), "sha256": h,
                          "content_type": ct})
            got_att += 1
        if saved:
            it["attachments"] = saved
        time.sleep(0.4)
    f.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n",
                 encoding="utf-8")
    st_path = sdir / "site-state.json"
    snap = {}
    if st_path.exists():
        try:
            snap = json.loads(st_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            snap = {}
    snap.update({"site": sdir.name, "items_total": len(items),
                 "texts": sum(1 for x in items if x.get("text_file")),
                 "text_chars": sum(int(x.get("text_chars") or 0) for x in items),
                 "attachments": sum(len(x.get("attachments") or []) for x in items)})
    st_path.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"site": sdir.name, "new_texts": got_text, "new_attachments": got_att,
            "chars": chars}


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
    ap.add_argument("--att-only", action="store_true",
                    help="只给已有条目补附件（不重抓列表、不重抓正文）")
    ap.add_argument("--text-only", action="store_true",
                    help="只给已有 items.jsonl 补正文/附件，不重抓列表")
    ap.add_argument("--list-only", action="store_true",
                    help="只抓列表与翻页（不抓正文/附件），用于先量翻页成功率")
    ap.add_argument("--site", default="", help="只抓指定站点名（单站验证）")
    ap.add_argument("--export-rules", action="store_true",
                    help="把实测标定出的翻页规则写回 site-rules.json")
    ap.add_argument("--kind", default="normative",
                    help="normative / hub / all")
    args = ap.parse_args()

    if args.export_rules:
        # 生成**完整接入配置**：不只是翻页规则，还包括「这站要用哪个引擎、入口在哪、
        # 上次抓到多少、什么时候跑的」——这样别的流程只读这一个文件就能接手本站。
        disc = {}
        try:
            for r in json.loads(DISCOVER.read_text(encoding="utf-8"))["results"]:
                disc[r["site"]] = r
        except Exception:                        # noqa: BLE001
            disc = {}
        rows = []
        for f in sorted(OUTDIR.rglob("site-state.json")):
            st = json.loads(f.read_text(encoding="utf-8"))
            name = st.get("site") or f.parent.name
            pgn = st.get("pagination") or {}
            rule = pgn.get("rule")
            ref = disc.get(name) or {}
            engine = ("browser" if st.get("engine") == "headless-dom"
                      else "static")
            rows.append({
                "site": name,
                "level": ref.get("level") or "city",
                "board_url": st.get("board") or ref.get("board_url"),
                "engine": engine,
                "status": st.get("status"),
                "rule": rule if isinstance(rule, list) else None,
                "rule_source": pgn.get("source") or (
                    "measured" if isinstance(rule, list) else None),
                "pages_this_run": st.get("pages_this_run"),
                "items_total": st.get("items_total"),
                "items_new_this_run": st.get("items_new_this_run"),
                "newest_date": st.get("newest_date"),
                "oldest_date": st.get("oldest_date"),
                "run_at": st.get("run_at"),
                "render_seconds": st.get("render_seconds"),
                "discovered_by": ref.get("discovered_by") or "discover",
                "note": ("脚本渲染站：必须用 national-crawl-browser.py"
                         if engine == "browser" else
                         "静态可抓：用 national-crawl-fetch.py"),
            })
        SITE_RULES.write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        got = sum(1 for r in rows if r.get("rule"))
        br = sum(1 for r in rows if r.get("engine") == "browser")
        print(f"已导出接入配置 {len(rows)} 站 → {SITE_RULES.relative_to(ROOT)}")
        print(f"  其中静态 {len(rows) - br} 站 / 浏览器 {br} 站；有效翻页规则 {got} 条")
        return 0

    if args.text_only or args.att_only:
        dirs = sorted({f.parent for f in OUTDIR.rglob("items.jsonl")})
        mode = "只补附件" if args.att_only else "只补正文"
        print(f"{mode}：{len(dirs)} 站")
        transport = default_transport()
        t0 = time.monotonic()
        tot_t = tot_a = tot_c = 0
        with ThreadPoolExecutor(max_workers=args.concurrency,
                                thread_name_prefix="nat-text") as pool:
            futs = [pool.submit(text_only_site, transport, dd,
                                args.max_files, args.max_mb,
                                args.att_only) for dd in dirs]
            for i, fut in enumerate(as_completed(futs), 1):
                r = fut.result()
                tot_t += r["new_texts"]
                tot_a += r["new_attachments"]
                tot_c += r["chars"]
                if i % 10 == 0 or i == len(dirs):
                    print(f"  {i}/{len(dirs)}  正文 {tot_t} 篇 / {tot_c} 字  "
                          f"附件 {tot_a}  用时 {time.monotonic() - t0:.0f}s")
        print(f"完成：正文 {tot_t} 篇 / {tot_c} 字，附件 {tot_a}")
        return 0

    d = json.loads(DISCOVER.read_text(encoding="utf-8"))
    sites = [r for r in d["results"]
             if r.get("status") == "ok"
             and (args.kind == "all" or r.get("board_kind") == args.kind)]
    if args.site:
        sites = [s for s in sites if s.get("site") == args.site]
    if args.limit:
        sites = sites[: args.limit]
    print(f"待抓 {len(sites)} 站（kind={args.kind}，页≤{args.pages}，"
          f"附件≤{args.max_files}/站，单件≤{args.max_mb}MB）")

    transport = default_transport()
    rules = load_site_rules()
    if rules:
        print(f"  读到站点规则配置 {len(rules)} 条")
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
                              barren_stop=args.barren_stop,
                              list_only=args.list_only,
                              preset_rule=rules.get(str(rec.get("site"))))

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
