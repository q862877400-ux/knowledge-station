"""江西数融互动 —— hygz 解析缺口 + 其它 channelCode/webSiteCode 探测。

目的（2026-10-09）：
 1. jx-zf 落盘 388 条（wxszj 259 满 / hygz 129），而 hygz 上游 total=430
    ⇒ 301 条被 `_one()` 丢掉。到底是真的没答复，还是答复在别的字段？
 2. jx-zmhd.js 里出现过 channelCode=['zxft']（在线访谈）—— jxsrmzf 还有哪些问答栏目？
 3. 34 个省直部门 webSiteCode 里，哪些也有互动问答栏目？

只探测、只打印、不落盘、不改任何共享文件。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))

import httpx  # noqa: E402

HOST = "https://www.jiangxi.gov.cn"
LIST_URL = HOST + "/queryList"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.6
OUT = HERE / "jx-hygz-probe.txt"

CANDIDATE_CHANNELS = [
    "hygz", "wxszj", "zxft", "wszx", "zxxx", "hdjl", "zjdc", "yjzj",
    "gzly", "lyxd", "zxly", "tsjb", "zmhd", "zjzj", "wtzx", "zxzx",
]


def query(cli: httpx.Client, web_site: str, channel: str, *, page: int = 1,
          size: int = 50) -> dict:
    data = {"current": page, "pageSize": size,
            "channelCode": [channel], "webSiteCode": [web_site]}
    r = cli.post(LIST_URL, data=data, headers={"User-Agent": UA,
                                               "Referer": HOST + "/"})
    if r.status_code != 200:
        return {"_http": r.status_code}
    try:
        d = r.json()
    except Exception as e:                                              # noqa: BLE001
        return {"_err": type(e).__name__}
    inner = d.get("data") or {}
    return {"total": inner.get("total"), "results": inner.get("results") or []}


def main() -> int:
    log = open(OUT, "w", encoding="utf-8")

    def say(s: str = "") -> None:
        print(s)
        log.write(s + "\n")

    with httpx.Client(timeout=40, follow_redirects=True, trust_env=False) as cli:
        # ---- 1. hygz 原始样本：看被丢掉的条目长什么样 --------------------
        say("=" * 78)
        say("【1】hygz 原始条目结构（page=1, size=50）")
        say("=" * 78)
        res = query(cli, "jxsrmzf", "hygz", page=1, size=50)
        say(f"HTTP/err: { {k: v for k, v in res.items() if k.startswith('_')} }  "
            f"total={res.get('total')}")
        items = res.get("results") or []
        say(f"本页 {len(items)} 条")
        no_answer, with_answer = 0, 0
        for it in items[:8]:
            src = it.get("source") or {}
            md_raw = src.get("metadata")
            try:
                md = json.loads(md_raw) if isinstance(md_raw, str) else (md_raw or {})
            except Exception:                                           # noqa: BLE001
                md = {}
            c = src.get("content")
            body = (c.get("content") if isinstance(c, dict) else c) or ""
            say("-" * 70)
            say(f"id={src.get('id')}  channelCode={src.get('channelCode')} "
                f"websiteCode={src.get('websiteCode')}")
            say(f"title={ (src.get('title') or '')[:60] }")
            say(f"metadata keys={sorted(md.keys())}")
            for k in sorted(md.keys()):
                v = md[k]
                if isinstance(v, str) and len(v) > 30:
                    say(f"   md[{k}] = {v[:120]}...")
                else:
                    say(f"   md[{k}] = {v}")
            say(f"content len={len(body)}  head={body[:150]!r}")
        # 统计整页「有答复 vs 无答复」
        for it in items:
            src = it.get("source") or {}
            md_raw = src.get("metadata")
            try:
                md = json.loads(md_raw) if isinstance(md_raw, str) else (md_raw or {})
            except Exception:                                           # noqa: BLE001
                md = {}
            c = src.get("content")
            body = (c.get("content") if isinstance(c, dict) else c) or ""
            has = bool((md.get("field_1596") or "").strip()) or ("答：" in body or "答:" in body)
            with_answer += 1 if has else 0
            no_answer += 0 if has else 1
        say("-" * 70)
        say(f"本页统计：有答复 {with_answer} / 无答复 {no_answer}（共 {len(items)}）")
        time.sleep(PAUSE)

        # ---- 2. jxsrmzf 上的候选栏目 -------------------------------------
        say("")
        say("=" * 78)
        say("【2】jxsrmzf 候选 channelCode 探测（total>0 即有效栏目）")
        say("=" * 78)
        for ch in CANDIDATE_CHANNELS:
            res = query(cli, "jxsrmzf", ch)
            t = res.get("total")
            extra = "" if not res.get("_http") else f" (HTTP {res['_http']})"
            mark = "★" if isinstance(t, int) and t > 0 else " "
            say(f" {mark} channelCode={ch:8s} total={t}{extra}")
            time.sleep(PAUSE)

    log.close()
    print(f"\n→ {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
