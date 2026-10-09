r"""通用端点测试器：GET/POST 一个 URL，dump 状态码 + Content-Type + 响应头 600 字符。

## 为什么要有它

探中间件时反复需要「试一个候选接口，看它到底返回什么」。
`probe-city-hd-api.py` 是**按页面**看的（抽链接/端点），
但拿到**具体接口 URL** 之后需要一个「**直接打它**」的工具 —— 本脚本就是。

⚠ **不接受「HTTP 200」当成功**：本工具只负责把响应原样 dump 出来，
判活/判死由调用者按 GOAL.md #6 自己看（`totalResults` 大 ≠ 有问答）。

## 用法

```bash
# GET
.venv/Scripts/python.exe tools/gov-qa/recon/probe-endpoint.py \
    --url "https://x.gov.cn/api/list" --param pageIndex=1 --param pageSize=10

# POST（表单）
... --url "https://x.gov.cn/api/list" --post --param sqly=29 --param page=1

# 批量（JSON：[{url, method, params, referer}, …]）
... --json probes.json
```

只读，不落盘。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _clean(s: str, n: int = 600) -> str:
    return re.sub(r"\s+", " ", (s or "")[:n])


def one(c: httpx.Client, spec: dict) -> "list[str]":
    url = spec["url"]
    method = (spec.get("method") or "GET").upper()
    params = spec.get("params") or {}
    referer = spec.get("referer") or ""
    h = {"User-Agent": UA, "Accept": "application/json, text/javascript, */*; q=0.01",
         "Accept-Language": "zh-CN,zh;q=0.9", "X-Requested-With": "XMLHttpRequest"}
    if referer:
        h["Referer"] = referer
    L = [f"\n{'=' * 70}", f"{method} {url}", f"  params={params} json={spec.get('json')} "
         f"referer={referer[:60]}", "=" * 70]
    try:
        if method == "POST":
            if spec.get("json") is not None:
                # ★ Spring Boot 的 `@RequestBody` 接口对表单编码回 **415 Unsupported Media Type**，
                #   必须发 `Content-Type: application/json`（实测惠州 `queryList.do` 就是）。
                r = c.post(url, json=spec["json"], headers=h, timeout=25)
            else:
                r = c.post(url, data=params, headers=h, timeout=25)
        else:
            r = c.get(url, params=params, headers=h, timeout=25)
    except Exception as e:                                            # noqa: BLE001
        L.append(f"  FAIL {type(e).__name__}: {str(e)[:70]}")
        return L
    L.append(f"  HTTP {r.status_code} ct={r.headers.get('content-type', '')[:40]} "
             f"len={len(r.text)}")
    try:
        j = r.json()
        if isinstance(j, dict):
            L.append(f"  JSON keys: {list(j.keys())[:16]}")
            for k in ("total", "totalCount", "count", "rows", "data", "list", "page"):
                if k in j:
                    v = j[k]
                    L.append(f"    {k} = "
                             f"{(str(v)[:150]) if not isinstance(v, list) else f'list[{len(v)}]'}")
        elif isinstance(j, list):
            L.append(f"  JSON list len={len(j)}; [0]={_clean(json.dumps(j[0], ensure_ascii=False), 200) if j else ''}")
    except Exception:                                                 # noqa: BLE001
        pass
    L.append(f"  body: {_clean(r.text)}")
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--param", action="append", default=[],
                    help="k=v，可重复")
    ap.add_argument("--referer", default="")
    ap.add_argument("--json", default="", help="批量：JSON 数组")
    args = ap.parse_args()

    specs: list[dict] = []
    if args.json:
        specs = json.loads(Path(args.json).read_text(encoding="utf-8"))
    elif args.url:
        params = {}
        for kv in args.param:
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k] = v
        specs = [{"url": args.url, "method": "POST" if args.post else "GET",
                  "params": params, "referer": args.referer}]
    else:
        print("❌ 需要 --url 或 --json", file=sys.stderr)
        return 1

    L: list[str] = []
    with httpx.Client(follow_redirects=True, trust_env=False, verify=False) as c:
        for s in specs:
            L += one(c, s)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
