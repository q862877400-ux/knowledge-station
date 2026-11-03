"""探针：对「hdjlpt 端点存在（pubList 返 405）但落地页非 200」的市，
**直接 POST `/hdjlpt/letter/pubList`** —— 不依赖落地页 200。

## 为什么写它（2026-10-10 第 8 轮）

上一轮 `probe-gd-city-hdjlpt.py` 用「落地页是否 200」判死了一批市。
本轮 `probe-gd-hd-403.py` 实测发现真响应是 **404/405/502**（不是 403），
其中 `/hdjlpt/letter/pubList` 返 **405 Method Not Allowed** = **端点存在、只收 POST**。

⇒ 本探针做**最终判据**（GOAL.md 硬约束 6：判死前必须取一条明细确认答复非空）：
**只要能拿到 XSRF-TOKEN，就直接 POST pubList，看 `data.list` 里有没有带 `reply` 的条目。**

拿 token 的策略（按顺序，任一成功即用）：
 1. `GET /hdjlpt/published?via=pc`
 2. `GET /hdjlpt`
 3. `GET /hdjlpt/letter/pubList`（405 响应也常带 set-cookie）
 4. `GET /`（首页）

⚠ 输出由 Python 自己写文件 —— 不经 PowerShell 管道。只读，不落盘 data/。
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

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

#: (市名, base) —— 本轮实测 pubList 返 405 的 5 个市（405 = 端点存在）
TARGETS = [
    ("广东·东莞(主站)", "https://www.dongguan.gov.cn"),
    ("广东·东莞(dg)", "https://www.dg.gov.cn"),
    ("广东·韶关", "https://www.sg.gov.cn"),
    ("广东·中山", "https://www.zs.gov.cn"),
    ("广东·河源", "https://www.heyuan.gov.cn"),
    ("广东·珠海", "https://www.zhuhai.gov.cn"),
]

TOKEN_PAGES = ["/hdjlpt/published?via=pc", "/hdjlpt", "/hdjlpt/letter/pubList", "/"]

LIST_PATHS = ["/hdjlpt/letter/pubList", "/hdjlpt/letter/list"]


def _token_from(r) -> str | None:
    for c in (getattr(getattr(r, "cookies", None), "jar", None) or []):
        if c.name == "XSRF-TOKEN":
            return unquote(c.value)
    hd = getattr(r, "headers", None)
    gl = getattr(hd, "get_list", None)
    if gl:
        m = re.search(r"XSRF-TOKEN=([^;]+)", "; ".join(gl("set-cookie")))
        if m:
            return unquote(m.group(1))
    return None


def _post_list(c, base: str, path: str, token: str | None, per_page: int = 5) -> list[str]:
    now = int(time.time())
    body = f"offset=0&limit={per_page}&time_from={now - 365 * 86400}&time_to={now}"
    hdr = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": base, "Referer": base + "/hdjlpt/published?via=pc",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": UA,
    }
    if token:
        hdr["X-XSRF-TOKEN"] = token
    out: list[str] = []
    try:
        r = c.post(base + path, content=body, headers=hdr)
    except Exception as e:                                              # noqa: BLE001
        return [f"    POST {path:26s} FAIL {type(e).__name__}: {str(e)[:60]}"]
    t = r.text or ""
    out.append(f"    POST {path:26s} HTTP {r.status_code} len={len(t)} "
               f"ct={r.headers.get('content-type', '')[:34]}")
    if r.status_code == 200:
        try:
            j = r.json()
        except Exception:                                               # noqa: BLE001
            out.append(f"      (not json) {t[:220]}")
            return out
        d = j.get("data") or {}
        lst = d.get("list") or []
        out.append(f"      total={d.get('total')} list={len(lst)} keys={list(j.keys())}")
        if lst:
            it = lst[0]
            def _tx(v, n):
                return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(v or ""))).strip()[:n]
            out.append(f"      ★ 首条 id={it.get('id')} time={it.get('time')} "
                       f"reply_time={it.get('reply_time')}")
            out.append(f"      ★ title={_tx(it.get('title'), 60)}")
            out.append(f"      ★ reply={_tx(it.get('reply'), 90)}")
            out.append(f"      ★ org={_tx(it.get('org_name'), 30)}")
        else:
            out.append(f"      body={t[:220]}")
    else:
        out.append(f"      body={t[:200]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)

    for name, base in TARGETS:
        say(f"\n{'=' * 74}")
        say(f"{name}   {base}")
        say("=" * 74)
        with httpx.Client(timeout=30, follow_redirects=True,
                          trust_env=False, verify=False) as c:
            # 先访问首页（种会话 cookie），再逐个试 token 页
            try:
                r0 = c.get(base + "/", headers={
                    "User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                })
                say(f"  GET / (预热)                 HTTP {r0.status_code} "
                    f"len={len(r0.text or '')} cookies={[k.name for k in r0.cookies.jar]}")
            except Exception as e:                                      # noqa: BLE001
                say(f"  GET / (预热) FAIL {type(e).__name__}: {str(e)[:50]}")

            token = None
            for p in TOKEN_PAGES:
                try:
                    r = c.get(base + p, headers={
                        "User-Agent": UA, "Referer": base + "/",
                        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    })
                except Exception as e:                                  # noqa: BLE001
                    say(f"  GET {p:28s} FAIL {type(e).__name__}: {str(e)[:50]}")
                    continue
                tk = _token_from(r)
                say(f"  GET {p:28s} HTTP {r.status_code} len={len(r.text or '')} "
                    f"cookies={[k.name for k in r.cookies.jar]} token={'YES' if tk else 'no'}")
                if tk and not token:
                    token = tk
                    break
            say(f"  ==> XSRF token: {'OK' if token else 'NONE'}")
            for lp in LIST_PATHS:
                for ln in _post_list(c, base, lp, token):
                    say(ln)

    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out} ({len(lines)} lines)")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
