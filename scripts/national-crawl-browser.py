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
import urllib.request
from pathlib import Path

import websocket

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


def crawl_generic(site: str, rec: dict, page_source, next_action, pages: int,
                  engine: str = "headless-dom",
                  max_barren: int = 2) -> dict:
    """通用抓取循环：**取页**与**换页**都由外面传进来。

    `--dump-dom` 只能跟 `<a href>` 的下一页；JS 按钮换页要换成 CDP 点击。
    若为后者另写一个脚本，仓库尺子的「跨文件同函数体」会从 8 顶到 10（实测两次）。
    ⇒ 循环只留一份，不同引擎只提供两个小函数：

    - `page_source(url) -> (ok, html, seconds)`
    - `next_action(html, url) -> 下一页 URL | None`（返回同一 URL = 内容已换页）
    """
    board = rec.get("board_url") or ""
    prov = rec.get("province") or "未知"
    stats = {"site": site, "board": board, "status": None, "pages": 0,
             "items": 0, "seconds": 0.0, "error": None}
    if not board:
        stats["status"] = "no_board"
        return stats
    url = board
    seen: set[str] = set()
    items: list[dict] = []
    t_all = 0.0
    barren = 0
    for i in range(pages):
        ok, html, secs = page_source(url)
        t_all += secs
        if not ok or not html:
            stats["error"] = "render_failed"
            break
        fresh = [x for x in ncf.parse_items(html, url)
                 if x["url"] not in seen]
        for x in fresh:
            seen.add(x["url"])
            items.append(x)
        stats["pages"] = i + 1
        # ⚠ 空页容忍：有些站一页只有 4~10 条，偶尔出现"重复页"（点下一页后内容没变），
        #   一遇空页就停会把后面还有的页全丢掉（佛山实测：一遇空页停在 150 页，
        #   但手动连点 200 次仍能继续）。⇒ 连续 `max_barren` 页无新条目才停。
        barren = barren + 1 if not fresh else 0
        nxt = next_action(html, url)
        if not nxt or barren >= max_barren:
            break
        url = nxt
        time.sleep(1.0)
    stats["seconds"] = round(t_all, 1)
    stats["items"] = len(items)
    if not items:
        stats["status"] = "still_unparsable"
        return stats
    res = cmn.merge_and_save(
        site, board, items, province=prov, engine=engine,
        extra={"render_seconds": stats["seconds"],
               "pages_this_run": stats["pages"]})
    stats["status"] = engine + "_ok"
    stats["items_total"] = res["items_total"]
    stats["items_new"] = res["items_new"]
    return stats


def crawl_site(site: str, rec: dict, exe: str, pages: int,
               budget_ms: int) -> dict:
    """`--dump-dom` 引擎：渲染后跟「下一页」链接。"""
    return crawl_generic(
        site, rec,
        page_source=lambda u: render(u, exe, budget_ms),
        next_action=ncf.find_next,
        pages=pages, engine="headless-dom")



# ---------------------------------------------------------------- CDP 引擎
#: 在页面里点「下一页」（JS 按钮换页的站只能这样翻）
CLICK_NEXT_JS = """
(() => {
  const words = ['下一页', '下页', '后一页', 'Next', 'next', '»'];
  const nodes = Array.from(document.querySelectorAll('a,button,li,span,div'));
  for (const w of words) {
    for (const el of nodes) {
      const tx = (el.innerText || '').trim();
      if (tx === w || tx.startsWith(w)) {
        const off = el.disabled || el.classList.contains('disabled')
                  || el.getAttribute('aria-disabled') === 'true';
        if (off) continue;
        el.click();
        return 'clicked:' + tx.slice(0, 8);
      }
    }
  }
  const byClass = document.querySelector('a.next, .next a, [class*=nextPage]');
  if (byClass) { byClass.click(); return 'clicked:class'; }
  return 'no_next';
})()
"""


class CDPPage:
    """极简 CDP 页面：导航、等条目、点下一页。用完必须 close()。"""

    def __init__(self, port: int, timeout_s: float = 120.0):
        self.port = port
        self.timeout_s = timeout_s
        self._id = 0
        self.ws = None

    def open(self, url: str) -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/json/new?{url}", method="PUT")
        with urllib.request.urlopen(req, timeout=20) as r:
            info = json.loads(r.read().decode())
        self.ws = websocket.create_connection(
            info["webSocketDebuggerUrl"], timeout=self.timeout_s)
        self._send("Page.enable")
        # 实测：/json/new?url= 建出来的标签页不一定导航（读到 39 字节空壳）
        self._send("Page.navigate", url=url)

    def _send(self, method: str, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method,
                                 "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                return msg.get("result", {})

    def eval(self, expr: str):
        r = self._send("Runtime.evaluate", expression=expr,
                       returnByValue=True, awaitPromise=True)
        return r.get("result", {}).get("value")

    def html(self) -> str:
        return self.eval("document.documentElement.outerHTML") or ""

    def wait_items(self, parse, timeout_s: float = 30.0) -> str:
        """等到能抽出条目再返回（有站永远 readyState=loading，不能等 complete）。"""
        deadline = time.time() + timeout_s
        html = ""
        while time.time() < deadline:
            html = self.html()
            if html and parse(html):
                return html
            time.sleep(1.0)
        return html

    def click_next(self) -> bool:
        got = self.eval(CLICK_NEXT_JS)
        return isinstance(got, str) and got.startswith("clicked")

    def close(self) -> None:
        if self.ws is not None:
            try:
                self.ws.close()
            except Exception as exc:             # noqa: BLE001
                print(f"  [warn] 关闭 WS 失败：{type(exc).__name__}")
            self.ws = None


def start_debug_browser(exe: str, port: int) -> subprocess.Popen:
    """带调试端口的无头浏览器；调用方负责 terminate。"""
    profile = TMP / "cdp-profile"
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-proxy-server", "--proxy-bypass-list=*",
           f"--remote-debugging-port={port}", "--remote-allow-origins=*",
           f"--user-data-dir={profile}", "about:blank"]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def wait_debug_port(port: int, timeout_s: float = 40.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:                        # noqa: BLE001
            time.sleep(0.5)
    return False


def crawl_site_cdp(site: str, rec: dict, port: int, pages: int) -> dict:
    """CDP 引擎：点「下一页」抓取（JS 按钮换页的站用这个）。"""
    board = rec.get("board_url") or ""
    page = CDPPage(port)
    state = {"opened": False}

    def page_source(url: str):
        t0 = time.monotonic()
        if not state["opened"]:
            page.open(url or board)
            state["opened"] = True
        html = page.wait_items(lambda h: ncf.parse_items(h, board or url))
        return True, html, time.monotonic() - t0

    def next_action(html: str, url: str):
        return (board or url) if page.click_next() else None

    try:
        return crawl_generic(site, rec, page_source, next_action,
                             pages, engine="cdp")
    finally:
        page.close()


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
    ap.add_argument("--engine", default="dom", choices=["dom", "cdp"])
    ap.add_argument("--port", type=int, default=9333)
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
    proc = None
    if args.engine == "cdp":
        proc = start_debug_browser(exe, args.port)
        if not wait_debug_port(args.port):
            print("调试端口没起来")
            return 3
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
                r = (crawl_site_cdp(site, rec, args.port, args.pages)
                 if args.engine == "cdp"
                 else crawl_site(site, rec, exe, args.pages,
                                 args.budget_ms))
                r["hub_column"] = col
            else:
                r = {"site": site, "status": "no_normative_column",
                     "items": 0, "info": info}
        else:
            r = (crawl_site_cdp(site, rec, args.port, args.pages)
                 if args.engine == "cdp"
                 else crawl_site(site, rec, exe, args.pages,
                                 args.budget_ms))
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
    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:                        # noqa: BLE001
            proc.kill()
    ok = sum(1 for r in results
             if str(r.get("status", "")).endswith("_ok"))
    print(f"\n完成：{ok}/{len(results)} 站取到条目")
    return 0


if __name__ == "__main__":
    sys.exit(main())
