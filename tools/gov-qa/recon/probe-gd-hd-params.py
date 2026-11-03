"""探针：中山/河源 pubList 返 `errcode:0` 但 `total:0` —— 是参数错还是真没数据？

（2026-10-10 第 8 轮）

`probe-gd-hd-publist.py` 实测：中山 / 河源的 `POST /hdjlpt/letter/pubList`
返回 `{"errcode":0,"errmessage":"ok","data":{"total":0,"list":[]}}` —— 
**格式对（errcode 语义 = 真 hdjlpt），但 total=0**。

对照 GOAL.md #6 与惠州的教训：「**接口成功但 data 为空**」有两种可能：
 ① 真没公开信件；② **参数名/时间窗不对**（服务端静默返空）。
必须区分，否则又是一次误判。

本探针扫：
 · 时间窗：不传 / 近 30 天 / 近 1 年 / 近 3 年（hdjlpt 服务端通常限 1 年，但要看这里）
 · 参数名：`offset/limit`（已知）× `page/page_size` × `pageNum/pageSize` × `current/size`
 · 端点：`/hdjlpt/letter/pubList` × `/hdjlpt/pubList` × `/hdjlpt/letter/publishedList`
对每个组合打印 HTTP + total + list 长度。

⚠ 对照基准：拿一个**已知能采**的市（汕尾，hdjlpt 9 市之一）跑同一套组合，
   看它的 total 是多少 —— 若汕尾在「某些组合」下有数、某些组合下也 0，
   就说明这些组合的差异是**服务端行为**，不是参数错。

输出由 Python 自己写文件。只读。
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

#: (名, base)；含**已知能采**的汕尾作对照
TARGETS = [
    ("对照·汕尾(已知能采)", "https://www.shanwei.gov.cn"),
    ("广东·中山", "https://www.zs.gov.cn"),
    ("广东·河源", "https://www.heyuan.gov.cn"),
]

TOKEN_PAGE = "/hdjlpt/published?via=pc"

#: 端点候选
ENDPOINTS = ["/hdjlpt/letter/pubList", "/hdjlpt/pubList", "/hdjlpt/letter/publishedList"]

#: 参数名组合（列表接口的真名未知 ⇒ 全试）
PARAM_SETS = [
    ("offset/limit", "{off}"),
    ("page/page_size", "page={pg}&page_size={sz}"),
    ("pageNum/pageSize", "pageNum={pg}&pageSize={sz}"),
    ("current/size", "current={pg}&size={sz}"),
    ("pageIndex/pageSize", "pageIndex={pg}&pageSize={sz}"),
]

#: 时间窗
WINDOWS = [
    ("不传时间", None),
    ("近30天", 30),
    ("近1年", 365),
    ("近3年", 365 * 3),
]


def _token(c, base: str) -> str | None:
    try:
        r = c.get(base + TOKEN_PAGE, headers={
            "User-Agent": UA, "Referer": base + "/",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
    except Exception:                                                   # noqa: BLE001
        return None
    for ck in (r.cookies.jar or []):
        if ck.name == "XSRF-TOKEN":
            return unquote(ck.value)
    return None


def _try(c, base: str, token: str, ep: str, pname: str, ptpl: str, wname: str, days) -> str:
    now = int(time.time())
    if ptpl == "{off}":
        body = "offset=0&limit=10"
    else:
        body = ptpl.format(pg=1, sz=10)
    if days is not None:
        body += f"&time_from={now - days * 86400}&time_to={now}"
    hdr = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": base, "Referer": base + TOKEN_PAGE,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": UA,
    }
    if token:
        hdr["X-XSRF-TOKEN"] = token
    try:
        r = c.post(base + ep, content=body, headers=hdr)
    except Exception as e:                                              # noqa: BLE001
        return f"      [{ep} | {pname} | {wname}] FAIL {type(e).__name__}"
    t = r.text or ""
    summ = f"      HTTP {r.status_code} len={len(t)}"
    if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
        try:
            j = r.json()
            ec = j.get("errcode")
            d = j.get("data") or {}
            tot = d.get("total") if isinstance(d, dict) else None
            lst = d.get("list") if isinstance(d, dict) else None
            summ += f" errcode={ec} total={tot} list={len(lst) if isinstance(lst, list) else lst}"
            if isinstance(lst, list) and lst:
                it = lst[0]
                tx = lambda v, n: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(v or ""))).strip()[:n]
                summ += f"\n          ★ id={it.get('id')} title={tx(it.get('title'),50)} reply={tx(it.get('reply'),60)}"
        except Exception:                                               # noqa: BLE001
            summ += f" body={t[:80]}"
    else:
        summ += f" body={t[:80]}"
    return f"      [{ep} | {pname} | {wname}]\n{summ}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    lines: list[str] = []

    def say(s: str) -> None:
        lines.append(s)

    for name, base in TARGETS:
        say(f"\n{'=' * 74}")
        say(f"{name}   {base}")
        say("=" * 74)
        with httpx.Client(timeout=30, follow_redirects=True,
                          trust_env=False, verify=False) as c:
            tk = _token(c, base)
            say(f"  token={'OK' if tk else 'NONE'}")
            for ep in ENDPOINTS:
                for pname, ptpl in PARAM_SETS:
                    for wname, days in WINDOWS:
                        say(_try(c, base, tk, ep, pname, ptpl, wname, days))
                say("")

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
