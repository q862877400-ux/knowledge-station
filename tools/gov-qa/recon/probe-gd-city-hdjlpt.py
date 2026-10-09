r"""实测：广东各**地级市**的 hdjlpt 能不能采（GOAL.md #6：判死/判活前必须实测）。

## 背景

`recon/probe-city-middleware.py` 把 152 个零记录市门户归类，发现
**17 个市带 `广东hdjlpt` 指纹**（东莞/中山/云浮/佛山/惠州/汕头/汕尾…），
且它们的互动入口就在自己的域名下（如 佛山 `www.foshan.gov.cn/hdjlpt/zixun`）。

我们**已有** `adapters/_gd_hdjlpt_common.py`（广东 37 个厅局在用）。
⇒ 若市级也跑同款，加一个市 = **一个 4 行薄适配器**（换 BASE）。
这正是「找到一个接口 = 找到一片站点」。

## 本探针干什么

对每个候选市：
1. `GET {base}/hdjlpt/published?via=pc` —— 拿 Laravel `XSRF-TOKEN`
2. `POST {base}/hdjlpt/letter/pubList` —— `offset=0&limit=20&time_from&time_to`
3. **取第一条确认 `reply` 正文非空**（不接受「HTTP 200」当成功）

⚠ 只读，不落盘到 data/。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}
PAGE_PATH = "/hdjlpt/published?via=pc"
API_PATH = "/hdjlpt/letter/pubList"
TAG_RE = re.compile(r"<[^>]+>")


def _text(h: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h or "")).strip()


def _token(r0) -> str | None:
    jar = getattr(getattr(r0, "cookies", None), "jar", None)
    for c in (jar or []):
        if c.name == "XSRF-TOKEN":
            return unquote(c.value)
    return None


def probe_city(c: httpx.Client, city: str, base: str) -> dict:
    base = base.rstrip("/")
    out = {"city": city, "base": base, "page": 0, "api": 0, "total": None,
           "items": 0, "reply_len": 0, "sample": "", "note": ""}
    try:
        r0 = c.get(base + PAGE_PATH, timeout=15)
    except Exception as e:                                            # noqa: BLE001
        out["note"] = f"落地页 {type(e).__name__}"
        return out
    out["page"] = r0.status_code
    if r0.status_code != 200:
        out["note"] = f"落地页 HTTP {r0.status_code}"
        return out
    tok = _token(r0)
    if not tok:
        out["note"] = "无 XSRF-TOKEN"
        return out
    now = int(time.time())
    body = (f"offset=0&limit=20&time_from={now - 365 * 86400}&time_to={now}")
    try:
        r = c.post(base + API_PATH, content=body, timeout=20, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": base, "Referer": base + PAGE_PATH, "X-XSRF-TOKEN": tok})
    except Exception as e:                                            # noqa: BLE001
        out["note"] = f"pubList {type(e).__name__}"
        return out
    out["api"] = r.status_code
    if r.status_code != 200:
        out["note"] = f"pubList HTTP {r.status_code}"
        return out
    try:
        d = (r.json() or {}).get("data") or {}
    except Exception as e:                                            # noqa: BLE001
        out["note"] = f"JSON 解析失败 {type(e).__name__}"
        return out
    items = d.get("list") or []
    out["total"] = d.get("total")
    out["items"] = len(items)
    for it in items:
        rep = _text(it.get("reply") or "")
        if rep:
            out["reply_len"] = len(rep)
            out["sample"] = rep[:110]
            break
    if not out["reply_len"]:
        out["note"] = "有列表但**无答复正文**（空壳）"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mw", default=str(HERE / "city-middleware.json"))
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0, help="只测前 N 个市")
    args = ap.parse_args()

    mw = json.loads(Path(args.mw).read_text(encoding="utf-8"))
    cands = [(c, v["base"]) for c, v in sorted(mw.items())
             if "广东hdjlpt" in (v.get("middleware") or [])]
    if args.limit:
        cands = cands[:args.limit]

    L: list[str] = []

    def say(s: str = "") -> None:
        L.append(s)

    say(f"候选（带广东hdjlpt 指纹的市）{len(cands)} 个")
    ok = 0
    with httpx.Client(headers=H, follow_redirects=True, trust_env=False,
                      verify=False) as c:
        for city, base in cands:
            r = probe_city(c, city, base)
            good = r["reply_len"] > 0
            ok += 1 if good else 0
            say(f"  {city:10s} {r['base'][:36]:38s} page={r['page']} api={r['api']} "
                f"total={r['total']} items={r['items']} reply={r['reply_len']} "
                f"{'✅' if good else '❌'} {r['note']}")
            if good:
                say(f"      样例：{r['sample']}")
            time.sleep(0.8)
    say(f"\n⇒ **真能采的市：{ok}/{len(cands)}**")

    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
