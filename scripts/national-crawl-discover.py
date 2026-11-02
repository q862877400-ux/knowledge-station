"""全国市级以上「规范性文件」栏目 —— 阶段 1：发现（2026-11-02）。

## 要什么、不要什么（业主原话，2026-11-02）

> 「这个公告主要是发法规标准地方条例地方办法之类的文件的那种公告，新闻公告我不要」

**要**：政策法规、法规规章、地方性法规、政府规章、规范性文件、政府文件、
地方标准、标准公告、法律法规、文件库 —— 即**规范性文件**栏目。

**不要**：新闻、要闻、工作动态、巡视巡察、干部任免、招标采购、会议活动、
发布会、信访留言 —— 新闻/事务类。

## 判据（可反驳）

一个页面算「像规范性文件列表」，需同时满足：

1. `<a>` 数量 ≥ 8；
2. **整页日期数 ≥ 5** 或 **详情页式链接占比 ≥ 0.30**（二者其一）。

> ⚠ **第一版判据错了**（2026-11-02 实测三亚）：我按「链接文本里带日期」判，
> `simple_list.shtml` 32 条链接的 date_ratio 只有 0.031 —— 政府站典型写法是
> `<li><a>标题</a><span>2026-09-01</span></li>`，**日期在链接外面**。
> 按锚文本判 ⇒ 真列表页被判成「不像列表」，6 站全 `no_board_found`（0/6）。

## 用法

    .venv\\Scripts\\python.exe scripts/national-crawl-discover.py --limit 6
    .venv\\Scripts\\python.exe scripts/national-crawl-discover.py
    .venv\\Scripts\\python.exe scripts/national-crawl-discover.py --resume

产物：`var/tmp/national-discover.json`
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.update.announce import default_transport  # noqa: E402

CITY_LIST = ROOT / "tools" / "gov-qa" / "recon" / "city-domains-all.json"
OUT = ROOT / "var" / "tmp" / "national-discover.json"

#: 强命中：出现即高度可能指向**规范性文件**栏目
STRONG = ("政策法规", "法规规章", "地方性法规", "政府规章", "规范性文件",
          "行政规范性文件", "规范性文件库", "政策文件", "政府文件", "文件库",
          "法律法规", "规章库", "政府规章库", "政策库",
          "地方标准", "标准公告", "标准发布", "标准目录")
#: 弱命中：可能是也可能不是
WEAK = ("政策", "法规", "规章", "规范性", "标准", "文件", "公开",
        "通知公告", "公告", "公示")
#: **出现即排除**：新闻 / 事务 / 人事 / 采购（业主明确不要）
EXCLUDE = ("新闻", "要闻", "动态", "媒体报道", "图片", "专题",
           "巡视", "巡察", "干部", "任免", "人事", "招聘", "招录", "考试",
           "招标", "采购", "中标", "成交", "会议", "活动", "直播", "访谈",
           "公示公告", "公告公示", "通知公告", "部门公告", "信访", "留言", "互动",
           "公共资源交易",
           # 2026-11-02 实测补：解读/图解是**评论**不是文件本体；转载是二手
           "解读", "图解", "转载", "媒体", "评论")

LINK_RE = re.compile(r"<a\b[^>]*?href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                     re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"(?:20\d{2}[-/年.]\d{1,2}[-/月.]\d{1,2}|\d{4}-\d{2}-\d{2})")
DETAIL_RE = re.compile(
    r"(/(?:19|20)\d{2}(?:0[1-9]|1[0-2])/)|(/art/\d{4}/)"
    r"|([?&](?:id|contentid|articleid)=\d+)|(/content_?\d+)"
    r"|(/\d{6,}\.(?:s?html?|jhtml))", re.I)
#: 「政务公开 / 信息公开」枢纽页关键词（第二级发现用，R1 实测 192 站需要）
HUB_WORDS = ("政务公开", "信息公开", "政务信息公开", "法定主动公开",
             "公开目录", "信息公开目录", "政务公开专栏", "政府信息公开")
#: 新闻/通知类路径（命中即**不当栏目**：业主明确不要新闻公告）
NEWS_PATH = re.compile(
    r"/(?:tzgg|gsgg|xwzx|zwzx|ywdt|gzdt|xw|news|zyzz|bmgg|mtbd)(?:/|$|\.)",
    re.I)
#: 强命中词（用来分档：真·规范性文件栏目 vs 政务公开大目录）
NORMATIVE_WORDS = ("政策法规", "法规规章", "地方性法规", "政府规章", "规范性文件",
                   "政策文件", "政府文件", "文件库", "法律法规", "规章库",
                   "地方标准", "标准公告", "标准发布", "标准目录", "法规文件")

BLOCK_HINT = ("captcha", "验证码", "安全认证", "请开启JavaScript", "访问过于频繁",
              "403 Forbidden", "Access Denied")

#: 导航词（出现在锚文本里就不算「文件标题」）
NAV_WORDS = ("首页", "上一页", "下一页", "尾页", "更多", "返回", "登录", "注册",
             "网站地图", "无障碍", "简体", "繁体", "English", "打印", "关闭",
             "分享", "搜索", "导航", "跳到", "查看全部")

TIMEOUT_S = 20.0
DEFAULT_CONCURRENCY = 10


def text_of(html: str) -> str:
    """去标签取纯文本。"""
    return " ".join(TAG_RE.sub(" ", html).split())


def score_link(anchor: str, url: str) -> int:
    """给一个链接打候选分。**锚文本命中 EXCLUDE 直接判 0**（新闻/事务类不要）。"""
    a = anchor.strip()
    for w in EXCLUDE:
        if w in a:
            return 0
    s = 0
    for w in STRONG:
        if w in a:
            s += 3
    for w in WEAK:
        if w in a:
            s += 1
    u = urlsplit(url)
    path = u.path + (("?" + u.query) if u.query else "")
    for w in STRONG:
        if w in path:
            s += 2
    return s


def list_likeness(html: str, base: str) -> dict:
    """判据：这个页面像不像**文件列表**。见模块 docstring。"""
    anchors = []
    for href, inner in LINK_RE.findall(html):
        t = text_of(inner).strip()
        if not t:
            continue
        anchors.append((urljoin(base, href.strip()), t))
    n = len(anchors)
    if n == 0:
        return {"ok": False, "n_links": 0, "page_dates": 0,
                "detail_ratio": 0.0, "med_len": 0}
    page_dates = len(DATE_RE.findall(text_of(html)))
    detail = 0
    for url, _t in anchors:
        u = urlsplit(url)
        path = u.path + (("?" + u.query) if u.query else "")
        if DETAIL_RE.search(path):
            detail += 1
    detail_ratio = detail / n
    lens = [len(t) for _, t in anchors]
    med = statistics.median(lens) if lens else 0
    # ── 标题式占比 ──
    # ⚠ R2 实测（2026-11-02）：临汾 `/channels/37.html` 52 链接、48 个日期，
    #   但 detail_ratio=0（详情 URL 不带日期段）；乌海同类。
    #   只用 URL 形态判会把**真栏目**否掉 ⇒ 再加一条「锚文本像不像文件标题」。
    titled = sum(1 for _u, t in anchors
                 if 8 <= len(t) <= 80 and not any(w in t for w in NAV_WORDS))
    title_ratio = titled / n
    # 顺序：链接数 → 日期数（最强的判别）→（详情链接 或 标题式）二者其一
    ok = (n >= 8 and page_dates >= 3
          and (detail_ratio >= 0.15 or title_ratio >= 0.35))
    return {"ok": ok, "n_links": n, "page_dates": page_dates,
            "detail_ratio": round(detail_ratio, 3),
            "title_ratio": round(title_ratio, 3), "med_len": med}


def find_candidates(html: str, base: str, host: str,
                     top: int = 3) -> list[tuple[str, int, str]]:
    """从一页里找「可能是规范性文件栏目」的候选。

    返回 [(url, 分数, 锚文本|命中词)]。
    """
    cands: dict[str, tuple[int, str]] = {}
    for href, inner in LINK_RE.findall(html):
        url = urljoin(base, href.strip())
        if not url.startswith("http") or urlsplit(url).netloc != host:
            continue
        a = text_of(inner).strip()
        sc = score_link(a, url)
        if sc <= 0:
            continue
        # ⚠ 详情页不可能是「栏目」（2026-11-02 R2 实测）：三明/七台河/三沙/三门峡
        #   的前 3 个候选**全是单篇文章**（锚文本里带"公告/政府信息公开"），
        #   把真正的栏目挤掉了，于是 161 站被记成 candidates_not_listlike。
        u = urlsplit(url)
        upath = u.path + (("?" + u.query) if u.query else "")
        if DETAIL_RE.search(upath):
            continue
        if NEWS_PATH.search(upath):
            continue          # 新闻/通知栏目：业主明确不要
        if url not in cands or sc > cands[url][0]:
            hit = next((w for w in STRONG if w in a), "")
            cands[url] = (sc, a[:40] + ("|" + hit if hit else ""))
    return [(u, v[0], v[1]) for u, v in
            sorted(cands.items(), key=lambda kv: -kv[1][0])[:top]]


def hub_links(html: str, base: str, host: str, top: int = 2) -> list[str]:
    """找「政务公开 / 信息公开」这类**门户枢纽页**（第二级发现用）。

    为什么需要（R1 实测）：192/274 站的首页没有直达规范性文件栏目的链接 ——
    政策文件藏在「政务公开 → 政策文件」下一层。只扫首页永远找不到它们。
    """
    out: list[str] = []
    seen: set[str] = set()
    for href, inner in LINK_RE.findall(html):
        url = urljoin(base, href.strip())
        if not url.startswith("http") or urlsplit(url).netloc != host:
            continue
        a = text_of(inner).strip()
        if not any(w in a for w in HUB_WORDS):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= top:
            break
    return out


def validate(transport, ranked: list[tuple[str, int, str]], rec: dict) -> tuple | None:
    """逐条抓取并验证候选；返回最强的那个 (url, score, anchor, likeness) 或 None。"""
    best = None
    for url, sc, a in ranked:
        try:
            st, body = transport.fetch(url, timeout=TIMEOUT_S)
        except Exception:                          # noqa: BLE001 — 单候选失败不致命
            continue
        if st != 200 or not isinstance(body, str):
            continue
        lk = list_likeness(body, url)
        rec["candidates"].append({"url": url, "anchor": a, "score": sc, **lk})
        if lk["ok"] and (best is None or sc > best[1]):
            best = (url, sc, a, lk)
    return best


def discover_one(transport, site: dict) -> dict:
    """发现一个站点的规范性文件栏目。**不抛异常**，失败也要有状态。

    两级：
      1. **首页**直接找候选并验证（R1：274 站里 76 站能这样找到）；
      2. 首页找不到 → 进「政务公开 / 信息公开」枢纽页（最多 2 个）再找一遍
         （R1 实测 192 站属于这一类）。
    """
    name = site.get("name") or site.get("host") or ""
    home = site.get("url") or ""
    rec = {"site": name, "province": site.get("province"), "home": home,
           "board_url": None, "status": None, "score": 0, "keyword": "",
           "list_likeness": None, "candidates": [], "error": None,
           "depth": None, "hub_tried": []}
    if not home.startswith("http"):
        rec["status"] = "bad_home"
        return rec
    try:
        st, body = transport.fetch(home, timeout=TIMEOUT_S)
    except Exception as exc:                      # noqa: BLE001 — 失败要具名
        rec["status"] = "unreachable"
        rec["error"] = f"{type(exc).__name__}: {str(exc)[:100]}"
        return rec
    if st != 200 or not isinstance(body, str):
        rec["status"] = "unreachable"
        rec["error"] = f"http_{st}"
        return rec
    low = body.lower()
    if any(h.lower() in low for h in BLOCK_HINT) and len(body) < 3000:
        rec["status"] = "blocked"
        rec["error"] = "waf_or_captcha"
        return rec

    host = urlsplit(home).netloc
    best = validate(transport, find_candidates(body, home, host), rec)
    depth = 1 if best else None

    if best is None:
        # ── 第二级：进「政务公开 / 信息公开」枢纽页再找 ──
        for hub in hub_links(body, home, host, top=2):
            try:
                st2, b2 = transport.fetch(hub, timeout=TIMEOUT_S)
            except Exception:                      # noqa: BLE001
                rec["hub_tried"].append({"url": hub, "error": "fetch_failed"})
                continue
            if st2 != 200 or not isinstance(b2, str):
                rec["hub_tried"].append({"url": hub, "error": f"http_{st2}"})
                continue
            rec["hub_tried"].append({"url": hub, "error": None})
            best = validate(transport, find_candidates(b2, hub, host), rec)
            if best:
                depth = 2
                break

    if best:
        anchor = best[2] or ""
        kind = ("normative"
                if any(w in anchor for w in NORMATIVE_WORDS) else "hub")
        # ── 三级：命中「政务公开」这类大目录时，**再钻一层**找它下面的
        #    规范性文件子栏目（2026-11-02 R2：81 站属于这一类）。
        if kind == "hub":
            try:
                st3, b3 = transport.fetch(best[0], timeout=TIMEOUT_S)
            except Exception:                      # noqa: BLE001
                st3, b3 = None, None
            if st3 == 200 and isinstance(b3, str):
                inner = validate(transport, find_candidates(b3, best[0], host), rec)
                if inner:
                    inner_anchor = inner[2] or ""
                    best = inner
                    anchor = inner_anchor
                    # ⚠ **不能无条件标 normative**（2026-11-02 自查）：
                    #   内层找到的也可能只是「政府信息公开指南」这类目录。
                    #   仍按锚文本判，避免把数量刷高。
                    kind = ("normative"
                            if any(w in inner_anchor for w in NORMATIVE_WORDS)
                            else "hub")
                    depth = (depth or 2) + 1
        rec.update({"board_url": best[0], "status": "ok", "score": best[1],
                    "keyword": best[2], "list_likeness": best[3], "depth": depth,
                    "board_kind": kind})
    else:
        # ⚠ 「地址找对了、但静态抓不到内容」要跟「根本没找到」分开记
        #   （2026-11-02 R2 实测中山市：`/zwgk/fggw/index.html` 锚文本就是「政策法规」，
        #     但页面回 0 链接 0 日期 —— JS 渲染）。合并成 no_board_found 会丢线索。
        shell = next((c for c in rec["candidates"]
                      if c.get("n_links") == 0 and c.get("score", 0) >= 3), None)
        if shell:
            rec.update({"board_url": shell["url"], "status": "js_rendered",
                        "score": shell.get("score", 0),
                        "keyword": shell.get("anchor", ""),
                        "error": "page_empty_or_js"})
        else:
            rec["status"] = "no_board_found"
            rec["error"] = ("candidates_not_listlike" if rec["candidates"]
                            else "no_keyword_link")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    raw = json.loads(CITY_LIST.read_text(encoding="utf-8"))
    sites = [{"name": k, **v} for k, v in raw.items()]
    print(f"站点清单：{len(sites)} 个（{CITY_LIST.relative_to(ROOT)}）")

    done: dict[str, dict] = {}
    if args.resume and OUT.exists():
        for r in json.loads(OUT.read_text(encoding="utf-8")).get("results", []):
            done[r["site"]] = r
        print(f"  --resume：已有 {len(done)} 条")

    todo = [s for s in sites if s["name"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"  本轮 {len(todo)} 站，并发 {args.concurrency}")

    transport = default_transport()
    results = list(done.values())
    host_locks: dict[str, threading.Lock] = {}
    guard = threading.Lock()

    def lock_for(h: str) -> threading.Lock:
        with guard:
            return host_locks.setdefault(h, threading.Lock())

    def work(s: dict) -> dict:
        h = urlsplit(s.get("url") or "").netloc
        with lock_for(h):                          # 同一主机串行（守礼）
            r = discover_one(transport, s)
            time.sleep(1.0)
            return r

    def dump() -> None:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        cnt = Counter(r.get("status") for r in results)
        OUT.write_text(json.dumps({
            "generated_by": "scripts/national-crawl-discover.py",
            "criteria": {
                "want": "规范性文件（法规/条例/办法/规章/标准）",
                "dont_want": "新闻/事务/人事/采购类公告",
                "strong": STRONG, "exclude": EXCLUDE,
                "list_likeness": ("links>=8 且 日期>=3 且 "
                                  "（详情链接>=0.15 或 标题式>=0.35）"),
            },
            "counts": {"sites": len(results), "by_status": dict(cnt),
                       "by_board_kind": dict(Counter(
                           r.get("board_kind") for r in results
                           if r.get("status") == "ok"))},
            "results": sorted(results, key=lambda x: x["site"]),
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency,
                            thread_name_prefix="nat-disc") as pool:
        futs = {pool.submit(work, s): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 20 == 0 or i == len(todo):
                ok = sum(1 for x in results if x.get("status") == "ok")
                print(f"  进度 {i}/{len(todo)}  找到栏目 {ok}  "
                      f"用时 {time.monotonic() - t0:.0f}s")
                dump()

    dump()
    cnt = Counter(r.get("status") for r in results)
    print(f"\n完成：{len(results)} 站，用时 {(time.monotonic() - t0) / 60:.1f} 分钟")
    print("状态分布：", dict(cnt.most_common()))
    print(f"→ {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
