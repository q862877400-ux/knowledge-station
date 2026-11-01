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
BLOCK_HINT = ("captcha", "验证码", "安全认证", "请开启JavaScript", "访问过于频繁",
              "403 Forbidden", "Access Denied")

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
    # ⚠ 第一版用「或」：整页日期≥5 **或** 详情链接≥30%。实测三门峡时
    #   一篇文章（`/4120/2025/12/2234839.html`）靠导航链接和 5 个日期蒙过去了。
    #   改成**两条都要**：列表页既要有成排的详情链接，也要有成排的日期。
    ok = n >= 8 and detail_ratio >= 0.25 and page_dates >= 3
    return {"ok": ok, "n_links": n, "page_dates": page_dates,
            "detail_ratio": round(detail_ratio, 3), "med_len": med}


def discover_one(transport, site: dict) -> dict:
    """发现一个站点的规范性文件栏目。**不抛异常**，失败也要有状态。"""
    name = site.get("name") or site.get("host") or ""
    home = site.get("url") or ""
    rec = {"site": name, "province": site.get("province"), "home": home,
           "board_url": None, "status": None, "score": 0, "keyword": "",
           "list_likeness": None, "candidates": [], "error": None}
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
    cands: dict[str, tuple[int, str]] = {}
    for href, inner in LINK_RE.findall(body):
        url = urljoin(home, href.strip())
        if not url.startswith("http") or urlsplit(url).netloc != host:
            continue
        a = text_of(inner).strip()
        sc = score_link(a, url)
        if sc <= 0:
            continue
        if url not in cands or sc > cands[url][0]:
            hit = next((w for w in STRONG if w in a), "")
            cands[url] = (sc, a[:40] + ("|" + hit if hit else ""))
    ranked = sorted(cands.items(), key=lambda kv: -kv[1][0])[:3]
    if not ranked:
        rec["status"] = "no_board_found"
        rec["error"] = "no_keyword_link"
        return rec

    best = None
    for url, (sc, a) in ranked:
        try:
            st2, body2 = transport.fetch(url, timeout=TIMEOUT_S)
        except Exception:                          # noqa: BLE001 — 单候选失败不致命
            continue
        if st2 != 200 or not isinstance(body2, str):
            continue
        lk = list_likeness(body2, url)
        rec["candidates"].append({"url": url, "anchor": a, "score": sc, **lk})
        if lk["ok"] and (best is None or sc > best[1]):
            best = (url, sc, a, lk)
    if best:
        rec.update({"board_url": best[0], "status": "ok", "score": best[1],
                    "keyword": best[2], "list_likeness": best[3]})
    else:
        rec["status"] = "no_board_found"
        rec["error"] = "candidates_not_listlike"
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
                "list_likeness": ("links>=8 且 详情链接占比>=0.25 且 "
                                  "整页日期>=3（三条都要）"),
            },
            "counts": {"sites": len(results), "by_status": dict(cnt)},
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
