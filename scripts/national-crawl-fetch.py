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
ATT_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".wps", ".ofd")
BLOCK_HINT = ("captcha", "验证码", "安全认证", "访问过于频繁", "Access Denied")

TIMEOUT_S = 25.0


def text_of(html: str) -> str:
    return " ".join(TAG_RE.sub(" ", html).split())


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def is_title(t: str) -> bool:
    """算不算「一条文件」的标题。"""
    if not (8 <= len(t) <= 120):
        return False
    return not any(w in t for w in NAV_WORDS)


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
               max_mb: float, per_site_items: int) -> dict:
    """抓一个站：列表 → 详情 → 附件。返回统计（不抛异常）。"""
    site = rec["site"]
    board = rec.get("board_url") or ""
    prov = rec.get("province") or "未知"
    sdir = OUTDIR / str(prov) / str(site).replace("/", "_")
    adir = sdir / "attachments"
    stats = {"site": site, "province": prov, "board": board,
             "status": None, "pages": 0, "items": 0, "attachments": 0,
             "bytes": 0, "skipped": [], "error": None}
    if not board:
        stats["status"] = "no_board"
        return stats

    seen: set[str] = set()
    items: list[dict] = []
    for i, url in enumerate(page_variants(board, pages)):
        try:
            st, body = transport.fetch(url, timeout=TIMEOUT_S)
        except Exception as exc:                  # noqa: BLE001
            if i == 0:
                stats.update({"status": "unreachable",
                              "error": f"{type(exc).__name__}: {str(exc)[:80]}"})
                return stats
            break
        if st != 200 or not isinstance(body, str):
            if i == 0:
                stats.update({"status": "unreachable", "error": f"http_{st}"})
                return stats
            break
        got = parse_items(body, url)
        fresh = [x for x in got if x["url"] not in seen]
        if not fresh:
            break
        for x in fresh:
            seen.add(x["url"])
            items.append(x)
        stats["pages"] = i + 1
        if len(items) >= per_site_items:
            break
        time.sleep(1.0)                            # 同站礼貌间隔

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
    for it in items:
        try:
            st, body = transport.fetch(it["url"], timeout=TIMEOUT_S)
            if st != 200 or not isinstance(body, str):
                it["attachments"] = []
                continue
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
    stats["bytes"] = total_bytes
    stats["status"] = "ok"

    (sdir / "items.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n",
        encoding="utf-8")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--max-files", type=int, default=20)
    ap.add_argument("--max-mb", type=float, default=30.0)
    ap.add_argument("--items", type=int, default=40)
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
                              per_site_items=args.items)

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
                                   "bytes": sum(x.get("bytes", 0) for x in results)},
                               "results": sorted(results, key=lambda x: x["site"])},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print("\n状态：", dict(Counter(x.get("status") for x in results).most_common()))
    print(f"→ {rep.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
