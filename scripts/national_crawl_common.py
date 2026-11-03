"""抓取公共件：合并存库 + 浏览器/调试端口 + CDP 客户端（2026-11-02）。

## 为什么要这份文件

抓取器有三个（静态 `national-crawl-fetch.py`、渲染 `national-crawl-browser.py`、
点击翻页 `national-crawl-cdp.py`），它们都需要：

1. **把条目并进 items.jsonl 并算新增**（同一口径，不能各写一份）；
2. **找本机浏览器、起带调试端口的无头浏览器**；
3. **通过 CDP 在页面里执行 JS**（点击"下一页"）。

仓库尺子的"跨文件同函数体"会把这些重复抓到（实测从 8 涨到 10）。
⇒ 统一收在这里，三个脚本都调用它。

## 实测要点（2026-11-02）

- `/json/new?url=` 建出来的标签页**不一定导航**（读到 39 字节空壳）⇒ 必须再发 `Page.navigate`；
- 有些政府站**永远 `readyState=loading`**（广告/统计脚本不结束）⇒ 判据是"能抽出条目"，不是"加载完成"；
- 未加 `--remote-allow-origins=*` 时 WebSocket 握手被拒（403）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "var" / "data" / "national"
PROFILE = ROOT / "var" / "tmp" / "cdp-profile"

#: 候选浏览器（按顺序取第一个存在的）
BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

def load_script(name: str, rel: str):
    """按路径加载同目录脚本。

    本仓脚本用连字符命名（`national-crawl-fetch.py`），不能直接 `import`。
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_browser() -> str | None:
    """本机可用的无头浏览器路径（找不到返回 None）。"""
    for p in BROWSERS:
        if Path(p).exists():
            return p
    return None


def merge_and_save(site: str, board: str, items: list[dict], *,
                   province: str = "未知", engine: str = "static",
                   extra: dict | None = None) -> dict:
    """按 URL 合并进该站 items.jsonl，刷新快照，返回 {items_total, items_new}。"""
    safe = str(site).replace("/", "_")
    if not province or province == "未知":
        # 已有同名目录就沿用它，避免同一站写出两份（实测：人社部被写成
        # `中央/` 与 `未知/` 两份，一份有正文、一份没有）
        for cand in OUTDIR.rglob(safe):
            if cand.is_dir():
                province = cand.parent.name
                break
    sdir = OUTDIR / str(province or "未知") / safe
    sdir.mkdir(parents=True, exist_ok=True)
    f = sdir / "items.jsonl"
    prev: list[dict] = []
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                prev.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    merged: dict[str, dict] = {x["url"]: x for x in prev if x.get("url")}
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    new_run = 0
    for x in items:
        if not x.get("url"):
            continue
        old = merged.get(x["url"])
        if old is None:
            x["first_seen"] = now
            new_run += 1
        else:
            x.setdefault("first_seen", old.get("first_seen") or now)
            if not x.get("text_file"):
                x["text_file"] = old.get("text_file")
                x["text_chars"] = old.get("text_chars")
            if not x.get("attachments"):
                x["attachments"] = old.get("attachments") or []
        merged[x["url"]] = x
    allitems = sorted(merged.values(), key=lambda y: (y.get("date") or ""),
                      reverse=True)
    f.write_text("\n".join(json.dumps(x, ensure_ascii=False)
                           for x in allitems) + "\n", encoding="utf-8")
    dates = [x.get("date") for x in allitems if x.get("date")]
    snap = {"site": site, "board": board, "status": "ok", "run_at": now,
            "items_total": len(allitems), "items_new_this_run": new_run,
            "prev_items_total": len(prev),
            "newest_date": max(dates) if dates else None,
            "oldest_date": min(dates) if dates else None, "engine": engine}
    if extra:
        snap.update(extra)
    (sdir / "site-state.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"items_total": len(allitems), "items_new": new_run}
