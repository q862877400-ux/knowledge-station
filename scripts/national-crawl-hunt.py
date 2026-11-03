"""逐站摸入口（hunt）：用无头浏览器在门户里**找出规范性文件栏目**（2026-11-02）。

## 解决什么问题

静态 HTTP 对 62 个市 / 17 个省 / 41 个部委**找不到栏目入口**（`no_board_found`），
因为它们把「政策文件 / 法规规章 / 规范性文件」放在脚本渲染的导航里，或藏在
「政务公开」下一层。这个脚本用渲染后的 DOM 去找，找到就写进发现表，交给抓取器。

## 判定「找到了」的标准（与发现器同口径，不放松）

1. 候选链接的锚文本或 URL 路径命中入口词（政策文件/法规规章/规范性文件/文件库/
   政府文件/规章/法规/条例/办法/标准）；
2. 渲染该候选页后，页面**像文件列表**：链接 ≥ 8 **且** 日期 ≥ 3 **且**
   （详情链接占比 ≥ 0.15 **或** 标题式占比 ≥ 0.35）；
3. 若候选是「大目录」（命中但不像列表），**再进一层**找它的子栏目（只下一层，防跑飞）。

## 断点续跑

每站结果立刻写 `var/tmp/hunt-progress.json`；`--resume` 跳过已处理过的站
（不论成功失败），失败原因也留着 —— 便于以后换方法重试。

## 用法

    # 处理所有「没找到栏目」的市级站，最多 10 个
    .venv\\Scripts\\python.exe scripts/national-crawl-hunt.py --status no_board_found --limit 10

    # 只处理省级
    .venv\\Scripts\\python.exe scripts/national-crawl-hunt.py --level province --limit 5

    # 指定站名
    .venv\\Scripts\\python.exe scripts/national-crawl-hunt.py --sites 乐山市 南充市
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ncb = _load("ncb", "scripts/national-crawl-browser.py")   # render / find_normative_column
ncd = _load("ncd", "scripts/national-crawl-discover.py")  # find_candidates / list_likeness
ncf = _load("ncf", "scripts/national-crawl-fetch.py")     # parse_items（硬验证用）

DISCOVER = ROOT / "docs" / "channels" / "data" / "national-discover.json"
PROGRESS = ROOT / "var" / "tmp" / "hunt-progress.json"

#: 入口词（比发现器的 STRONG 更宽：这里允许"文件""规章""条例"这类短词）
ENTRY_WORDS = ("政策文件", "法规规章", "规范性文件", "政府文件", "文件库", "规章库",
               "法律法规", "地方性法规", "政策法规", "规章", "法规", "条例",
               "办法", "标准", "规范性")

#: 「政务公开」这类枢纽入口（首页找不到规范文件时，进这层再找）
HUB_WORDS = ("政务公开", "信息公开", "政府信息公开", "法定主动公开", "公开目录",
             "信息公开目录", "政务公开专栏", "政务五公开")

#: 明确不要的（新闻/事务/人事）
BAD_WORDS = ("新闻", "要闻", "动态", "巡视", "巡察", "干部", "任免", "人事",
             "招聘", "招标", "采购", "会议", "活动", "解读", "图解", "公示",
             "通知公告", "公告公示")


def looks_like_entry(anchor: str, url: str) -> bool:
    a = anchor or ""
    if any(w in a for w in BAD_WORDS):
        return False
    if any(w in a for w in ENTRY_WORDS):
        return True
    path = url.lower()
    return any(w in path for w in ("zcfg", "zfwj", "gfxwj", "flfg", "fggw",
                                   "zcwj", "xzgfxwj", "gzk", "wjk", "gfwj"))



#: 展开式导航要点的词（JS 菜单常见：先点一级，二级链接才出现在 DOM 里）
MENU_WORDS = ("政务公开", "信息公开", "政策", "法规", "文件", "规章", "标准")


def cdp_expand_page(port: int, url: str, click_menus: int = 3,
                    budget_s: float = 12.0) -> str:
    """用 CDP 打开页面，**并点开菜单**，返回累计看到的 HTML。

    为什么需要（2026-11-02 实测）：多数市级门户的一级导航是 JS 菜单，
    只读一次渲染拿不到二级链接 —— 这正是 39 个市「找不到规范文件栏目」的一个原因。
    做法：点一个菜单词 → 等 → 再读一次 DOM，把多次读到的 HTML 拼起来交给候选查找。
    """
    page = ncb.CDPPage(port)
    out: list[str] = []
    try:
        page.open(url)
        deadline = time.time() + budget_s
        while time.time() < deadline:
            h = page.html()
            if h and len(h) > 2000:
                break
            time.sleep(0.5)
        out.append(page.html())
        clicks = 0
        for word in MENU_WORDS:
            if clicks >= click_menus:
                break
            js = ("(() => {const ns=[...document.querySelectorAll('a,li,span,div')];"
                  "for (const el of ns) {const t=(el.innerText||'').trim();"
                  f"if (t==='{word}' || t.startsWith('{word}')) {{el.click();"
                  "return 'ok';}}} return 'no';})()")
            if page.eval(js) != "ok":
                continue
            clicks += 1
            time.sleep(1.2)
            out.append(page.html())
    except Exception as exc:                     # noqa: BLE001
        print(f"  [warn] CDP 展开失败：{type(exc).__name__}")
    finally:
        page.close()
    return "\n<!--SPLIT-->\n".join(h for h in out if h)



def really_a_list(html: str, url: str, min_items: int = 5) -> bool:
    """候选栏目必须**真能解析出 >= min_items 条带日期的条目**才算数。

    为什么要这条（2026-11-02 实测）：`list_likeness` 只看链接数/日期数/细节页比例，
    会把**导航页**判成列表 —— 临汾市 `channels/19.html` 有 59 个链接、9 个日期，
    判据通过了，但抓下来 0 条。加上这条硬验证后，这类假阳性能当场挡掉。
    """
    try:
        return len(ncf.parse_items(html, url)) >= min_items
    except Exception:                            # noqa: BLE001
        return False


def hunt_one(exe: str, site: dict, budget_ms: int, depth2: bool = True,
             port: int | None = None) -> dict:
    """在一个门户里找规范性文件栏目。返回 {status, board_url, how, tried}。"""
    home = site.get("url") or site.get("home") or ""
    rec = {"site": site.get("site") or site.get("name"), "home": home,
           "status": None, "board_url": None, "how": None, "tried": 0,
           "reason": None, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not home.startswith("http"):
        rec["status"] = "bad_home"
        return rec

    def fetch(u: str):
        """取一页 HTML：CDP 模式会点开菜单，DOM 模式只读一次渲染。"""
        if port:
            h = cdp_expand_page(port, u)
            return bool(h), h, 0.0
        return ncb.render(u, exe, budget_ms)

    ok, html, secs = fetch(home)
    if not ok or not html:
        rec["status"] = "render_failed"
        rec["seconds"] = round(secs, 1)
        return rec

    host = ncd.urlsplit(home).netloc
    cands = ncd.find_candidates(html, home, host, top=12)
    ranked = [(u, sc, a) for u, sc, a in cands if looks_like_entry(a, u)]
    rec["candidates"] = len(ranked)

    for url, sc, anchor in ranked[:5]:
        rec["tried"] += 1
        ok2, html2, _ = ({"ok": True, "html": cdp_expand_page(port, url)}.get("ok"),
                         cdp_expand_page(port, url), 0.0) if port else ncb.render(
            url, exe, budget_ms)
        if not ok2 or not html2:
            continue
        lk = ncd.list_likeness(html2, url)
        if lk.get("ok") and really_a_list(html2, url):
            rec.update({"status": "ok", "board_url": url, "how": "direct",
                        "anchor": anchor, "likeness": lk})
            return rec
        if depth2:
            # 大目录再进一层（只一层）
            sub = ncd.find_candidates(html2, url, host, top=8)
            for u2, sc2, a2 in sub:
                if not looks_like_entry(a2, u2):
                    continue
                rec["tried"] += 1
                ok3, html3, _ = ncb.render(u2, exe, budget_ms)
                if not ok3 or not html3:
                    continue
                lk3 = ncd.list_likeness(html3, u2)
                if lk3.get("ok") and really_a_list(html3, u2):
                    rec.update({"status": "ok", "board_url": u2, "how": "depth2",
                                "anchor": a2, "likeness": lk3})
                    return rec
    # ── 首页找不到 → 进「政务公开 / 信息公开」枢纽页再找（2026-11-02 增）──
    hub_links = []
    for m in ncd.LINK_RE.finditer(html):
        href, inner = m.group(1), m.group(2)
        txt = ncd.text_of(inner).strip()
        if not any(w in txt for w in HUB_WORDS):
            continue
        u = ncd.urljoin(home, href.strip())
        if u.startswith("http") and u not in hub_links:
            hub_links.append(u)
        if len(hub_links) >= 3:
            break
    rec["hubs"] = len(hub_links)
    for hub in hub_links:
        okh, htmlh, _ = ncb.render(hub, exe, budget_ms)
        if not okh or not htmlh:
            continue
        cands_h = ncd.find_candidates(htmlh, hub, host, top=12)
        for url, sc, anchor in [(u, s, a) for u, s, a in cands_h
                                if looks_like_entry(a, u)][:5]:
            rec["tried"] += 1
            ok2, html2, _ = ({"ok": True, "html": cdp_expand_page(port, url)}.get("ok"),
                         cdp_expand_page(port, url), 0.0) if port else ncb.render(
            url, exe, budget_ms)
            if not ok2 or not html2:
                continue
            lk = ncd.list_likeness(html2, url)
            if lk.get("ok"):
                rec.update({"status": "ok", "board_url": url, "how": "via_hub",
                            "anchor": anchor, "likeness": lk})
                return rec

    rec["status"] = "no_entry_found"
    rec["reason"] = f"tried={rec['tried']},hubs={len(hub_links)}"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=[])
    ap.add_argument("--status", default="", help="按发现状态挑（如 no_board_found）")
    ap.add_argument("--level", default="", help="city / province / ministry")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--budget-ms", type=int, default=8000)
    ap.add_argument("--retry-failed", action="store_true",
                    help="忽略进度里的失败记录，重试那些站")
    ap.add_argument("--resume", action="store_true",
                    help="跳过 hunt-progress.json 里已处理过的站")
    ap.add_argument("--engine", default="dom", choices=["dom", "cdp"],
                    help="cdp=点开菜单后再找（JS 菜单门户）")
    ap.add_argument("--port", type=int, default=9344)
    ap.add_argument("--no-depth2", action="store_true")
    args = ap.parse_args()

    exe = ncb.find_browser()
    if not exe:
        print("找不到浏览器")
        return 2

    data = json.loads(DISCOVER.read_text(encoding="utf-8"))
    rows = data["results"]
    by_site = {r["site"]: r for r in rows}

    if args.sites:
        targets = [by_site.get(s, {"site": s, "url": ""}) for s in args.sites]
    else:
        targets = [r for r in rows
                   if (not args.status or r.get("status") == args.status)
                   and (not args.level or r.get("level") == args.level)]
    progress: dict[str, dict] = {}
    if PROGRESS.exists():
        try:
            progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            progress = {}
    # 从进度文件回填已命中但没写进发现表的站（防中途被杀丢结果）
    healed = 0
    for name, pr in progress.items():
        if pr.get("status") != "ok":
            continue
        rec = by_site.get(name)
        if rec is None or rec.get("status") == "ok":
            continue
        rec["board_url"] = pr.get("board_url")
        rec["status"] = "ok"
        rec["board_kind"] = "normative"
        rec["keyword"] = pr.get("anchor")
        rec["list_likeness"] = pr.get("likeness")
        rec["discovered_by"] = f"hunt/{pr.get('how')}"
        rec.setdefault("level", "city")
        healed += 1
    if healed:
        DISCOVER.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print(f"  从进度文件回填 {healed} 站")

    if args.retry_failed:
        targets = [t for t in targets
                   if progress.get(t["site"], {}).get("status") != "ok"]
    elif args.resume:
        targets = [t for t in targets if t["site"] not in progress]

    targets = targets[: args.limit]
    print(f"浏览器：{exe}")
    print(f"待摸入口 {len(targets)} 站")
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)

    proc = None
    port = None
    if args.engine == "cdp":
        proc = ncb.start_debug_browser(exe, args.port)
        if not ncb.wait_debug_port(args.port):
            print("调试端口没起来")
            return 3
        port = args.port
    ok_n = 0
    for i, site in enumerate(targets, 1):
        r = hunt_one(exe, site, args.budget_ms, depth2=not args.no_depth2,
                     port=port)
        progress[r["site"]] = r
        PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        mark = "✔" if r["status"] == "ok" else "✘"
        if r["status"] == "ok":
            ok_n += 1
            rec = by_site.get(r["site"])
            if rec is not None:
                rec["board_url"] = r["board_url"]
                rec["status"] = "ok"
                rec["board_kind"] = "normative"
                rec["keyword"] = r.get("anchor")
                rec["list_likeness"] = r.get("likeness")
                rec["discovered_by"] = f"hunt/{r['how']}"
                rec.setdefault("level", "city")
        if r["status"] == "ok":
            DISCOVER.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"  {mark} {i}/{len(targets)} {r['site'][:12]:14} {r['status']:16} "
              f"试{r.get('tried')}个 {str(r.get('board_url'))[:52]}")

    if proc is not None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:                        # noqa: BLE001
            proc.kill()
    DISCOVER.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n本轮摸到 {ok_n}/{len(targets)} 站；发现表已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
