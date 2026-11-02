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

DISCOVER = ROOT / "docs" / "channels" / "data" / "national-discover.json"
PROGRESS = ROOT / "var" / "tmp" / "hunt-progress.json"

#: 入口词（比发现器的 STRONG 更宽：这里允许"文件""规章""条例"这类短词）
ENTRY_WORDS = ("政策文件", "法规规章", "规范性文件", "政府文件", "文件库", "规章库",
               "法律法规", "地方性法规", "政策法规", "规章", "法规", "条例",
               "办法", "标准", "规范性")

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


def hunt_one(exe: str, site: dict, budget_ms: int, depth2: bool = True) -> dict:
    """在一个门户里找规范性文件栏目。返回 {status, board_url, how, tried}。"""
    home = site.get("url") or site.get("home") or ""
    rec = {"site": site.get("site") or site.get("name"), "home": home,
           "status": None, "board_url": None, "how": None, "tried": 0,
           "reason": None, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not home.startswith("http"):
        rec["status"] = "bad_home"
        return rec

    ok, html, secs = ncb.render(home, exe, budget_ms)
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
        ok2, html2, _ = ncb.render(url, exe, budget_ms)
        if not ok2 or not html2:
            continue
        lk = ncd.list_likeness(html2, url)
        if lk.get("ok"):
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
                if lk3.get("ok"):
                    rec.update({"status": "ok", "board_url": u2, "how": "depth2",
                                "anchor": a2, "likeness": lk3})
                    return rec
    rec["status"] = "no_entry_found"
    rec["reason"] = f"tried={rec['tried']}"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=[])
    ap.add_argument("--status", default="", help="按发现状态挑（如 no_board_found）")
    ap.add_argument("--level", default="", help="city / province / ministry")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--budget-ms", type=int, default=8000)
    ap.add_argument("--resume", action="store_true",
                    help="跳过 hunt-progress.json 里已处理过的站")
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

    if args.resume:
        targets = [t for t in targets if t["site"] not in progress]

    targets = targets[: args.limit]
    print(f"浏览器：{exe}")
    print(f"待摸入口 {len(targets)} 站")
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)

    ok_n = 0
    for i, site in enumerate(targets, 1):
        r = hunt_one(exe, site, args.budget_ms, depth2=not args.no_depth2)
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

    DISCOVER.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n本轮摸到 {ok_n}/{len(targets)} 站；发现表已更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
