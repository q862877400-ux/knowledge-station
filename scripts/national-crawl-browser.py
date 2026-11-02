"""全国规范性文件栏目 —— 阶段 2b：**浏览器渲染抓取**（2026-11-02）。

## 为什么需要它

有些政务站的列表是脚本渲染的：静态 HTTP 拿到的是 759B~1KB 的空壳
（实测中山市 `/zwgk/fggw/index.html` → 759B、0 条），
而**带脚本的浏览器**拿到 40 KB、20 个带日期的条目。

⇒ 这类站只能渲染后再抽条目。

## 做法

调本机 Edge/Chrome 的**无头 dump-dom**，把渲染后的整页 HTML **写到文件**，
再用 `national-crawl-fetch.py` 里同一套 `parse_items()` 解析
（解析器只有一份，不复制）。条目合并进 `items.jsonl`，更新 `site-state.json`。

## 为什么不改任何工具配置

`chrome-devtools` 的 MCP 配置里浏览器路径少一个空格
（`Program Files(x86)`），我没改它 —— 这里直接调可执行文件，
用 `--dump-dom` 拿渲染结果，属于本进程自用，不动系统与工具配置。

## 实测

- 中山市：直连 40KB/20 处日期；**走代理也是 40KB/20 处** ⇒ 拦的是无脚本客户端。
- 单页耗时 24~48 秒（含渲染等待），所以**串行、限站数**，不并发轰炸。

## 用法

    .venv\\Scripts\\python.exe scripts/national-crawl-browser.py --sites 中山市 厦门市
- 单页 24~50 秒（含渲染等待），所以**串行、限站数**，不并发轰炸。
    .venv\\Scripts\\python.exe scripts/national-crawl-browser.py --all-js --limit 5
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


_spec = importlib.util.spec_from_file_location(
    "ncf", ROOT / "scripts" / "national-crawl-fetch.py")
ncf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ncf)

_spec2 = importlib.util.spec_from_file_location(
    "ncd", ROOT / "scripts" / "national-crawl-discover.py")
ncd = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(ncd)

_spec3 = importlib.util.spec_from_file_location(
    "ncc", ROOT / "scripts" / "national_crawl_common.py")
cmn = importlib.util.module_from_spec(_spec3)
_spec3.loader.exec_module(cmn)

DISCOVER = ROOT / "docs" / "channels" / "data" / "national-discover.json"
OUTDIR = ROOT / "var" / "data" / "national"
TMP = ROOT / "var" / "tmp"

#: 候选浏览器（按顺序找第一个存在的）
find_browser = cmn.find_browser


def render(url: str, exe: str, budget_ms: int = 8000,
           timeout_s: int = 90) -> tuple[bool, str, float]:
    """无头渲染一页，返回 (成功, HTML 文本, 耗时秒)。HTML 只留在内存/临时文件。"""
    t0 = time.monotonic()
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=str(TMP))
    os.close(fd)
    try:
        cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--no-proxy-server", "--proxy-bypass-list=*",
               f"--virtual-time-budget={budget_ms}", "--dump-dom", url]
        with open(tmp, "wb") as fh:                 # 直接写盘，不经过对话上下文
            subprocess.run(cmd, stdout=fh, stderr=subprocess.DEVNULL,
                           timeout=timeout_s, check=False)
        html = Path(tmp).read_text(encoding="utf-8", errors="ignore")
        return True, html, time.monotonic() - t0
    except subprocess.TimeoutExpired:
        return False, "", time.monotonic() - t0
    except Exception:                               # noqa: BLE001
        return False, "", time.monotonic() - t0
    finally:
        # ⚠ Windows 下 Edge 的残留子进程可能还占着句柄（实测 WinError 32），
        #   删不掉不算失败：渲染结果已经读进内存了。留着由下次清理。
        try:
            Path(tmp).unlink(missing_ok=True)
        except PermissionError:
            pass


def find_normative_column(exe: str, hub_url: str, budget_ms: int) -> tuple[str, dict]:
    """渲染「政务公开大目录」，在里面找**规范性文件**子栏目。

    为什么必须渲染（2026-11-02 实测）：63 个大目录站用静态 HTTP 钻一层 0 转换，
    它们的子栏目链接是脚本渲染出来的，静态 HTML 里没有。
    """
    ok, html, _ = render(hub_url, exe, budget_ms)
    if not ok or not html:
        return "", {"why": "render_failed"}
    host = ncd.urlsplit(hub_url).netloc
    cands = ncd.find_candidates(html, hub_url, host, top=6)
    # ⚠ 单独的「规章」「法规」「规范性」也要算（2026-11-02 实测七台河：
    #   子栏目锚文本就叫「规章」，用 ncd.NORMATIVE_WORDS 那种长词匹配不到，于是 0 转换）
    hints = ("规章", "法规", "规范性", "政策文件", "政府文件", "文件库",
             "标准", "条例", "办法", "规范性文件")
    strong = [c for c in cands
              if any(w in (c[2] or "") for w in hints)]
    for url, sc, anchor in strong:
        ok2, html2, _ = render(url, exe, budget_ms)
        if not ok2 or not html2:
            continue
        lk = ncd.list_likeness(html2, url)
        if lk.get("ok"):
            return url, {"anchor": anchor, "score": sc, "likeness": lk}
    return "", {"why": "no_normative_column", "tried": len(strong)}


def crawl_site(site: str, rec: dict, exe: str, pages: int,
               budget_ms: int) -> dict:
    """渲染一个站并抽条目（含跟「下一页」链接）。"""
    board = rec.get("board_url") or ""
    prov = rec.get("province") or "未知"
    sdir = OUTDIR / str(prov) / str(site).replace("/", "_")
    sdir.mkdir(parents=True, exist_ok=True)
    stats = {"site": site, "board": board, "status": None, "pages": 0,
             "items": 0, "seconds": 0.0, "error": None}
    if not board:
        stats["status"] = "no_board"
        return stats

    url = board
    seen: set[str] = set()
    items: list[dict] = []
    t_all = 0.0
    for i in range(pages):
        ok, html, secs = render(url, exe, budget_ms)
        t_all += secs
        if not ok or not html:
            stats["error"] = "render_failed"
            break
        got = ncf.parse_items(html, url)
        fresh = [x for x in got if x["url"] not in seen]
        for x in fresh:
            seen.add(x["url"])
            items.append(x)
        stats["pages"] = i + 1
        nxt = ncf.find_next(html, url)
        if not nxt or not fresh:
            break
        url = nxt
        time.sleep(1.0)
    stats["seconds"] = round(t_all, 1)
    stats["items"] = len(items)

    if not items:
        stats["status"] = "still_unparsable"
        return stats

    res = cmn.merge_and_save(
        site, board, items, province=prov, engine="headless-dom",
        extra={"render_seconds": stats["seconds"]})
    stats["status"] = "browser_ok"
    stats["items_total"] = res["items_total"]
    stats["items_new"] = res["items_new"]
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=[])
    ap.add_argument("--status", default="js_unparsable",
                    help="按 site-state 状态挑站（默认 js_unparsable）")
    ap.add_argument("--all-js", action="store_true",
                    help="挑所有 js_unparsable + discover 里 js_rendered 的站")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--budget-ms", type=int, default=8000)
    ap.add_argument("--hub", action="store_true",
                    help="攻「政务公开大目录」站：先渲染找规范文件子栏目再抓")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    exe = find_browser()
    if not exe:
        print("找不到浏览器可执行文件（Edge/Chrome 均未找到）")
        return 2
    print("浏览器:", exe)

    disc = {r["site"]: r for r in
            json.loads(DISCOVER.read_text(encoding="utf-8"))["results"]}

    targets: list[tuple[str, dict]] = []
    if args.hub:
        targets = [(r["site"], r) for r in disc.values()
                   if r.get("board_kind") == "hub" and r.get("status") == "ok"]
        targets = targets[: args.limit]
    elif args.sites:
        targets = [(s, disc.get(s) or {}) for s in args.sites]
    else:
        for f in sorted(OUTDIR.rglob("site-state.json")):
            st = json.loads(f.read_text(encoding="utf-8"))
            name = st.get("site") or f.parent.name
            if args.all_js:
                if st.get("status") in ("js_unparsable",):
                    targets.append((name, disc.get(name) or st))
            elif st.get("status") == args.status:
                targets.append((name, disc.get(name) or st))
        if args.all_js:
            for r in disc.values():
                if r.get("status") == "js_rendered":
                    targets.append((r["site"], r))
        targets = list({t[0]: t for t in targets}.values())[: args.limit]

    disc_updates: list[dict] = []
    print(f"待渲染 {len(targets)} 站：", [t[0] for t in targets])
    if args.dry:
        return 0

    results = []
    for i, (site, rec) in enumerate(targets, 1):
        if args.hub:
            col, info = find_normative_column(exe, rec.get("board_url") or "",
                                              args.budget_ms)
            if col:
                rec = dict(rec)
                rec["board_url"] = col
                disc_updates.append({"site": site, "board_url": col, **info})
                r = crawl_site(site, rec, exe, args.pages, args.budget_ms)
                r["hub_column"] = col
            else:
                r = {"site": site, "status": "no_normative_column",
                     "items": 0, "info": info}
        else:
            r = crawl_site(site, rec, exe, args.pages, args.budget_ms)
        results.append(r)
        print(f"  {i}/{len(targets)} {site[:10]:12} {r['status']:18} "
              f"页={r.get('pages')} 条目={r.get('items')} "
              f"({r.get('seconds')}s)")
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "browser-crawl-report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    if disc_updates:
        (TMP / "hub-columns-found.json").write_text(
            json.dumps(disc_updates, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"  找到子栏目 {len(disc_updates)} 个 → var/tmp/hub-columns-found.json")
    ok = sum(1 for r in results if r.get("status") == "browser_ok")
    print(f"\n完成：{ok}/{len(results)} 站取到条目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
