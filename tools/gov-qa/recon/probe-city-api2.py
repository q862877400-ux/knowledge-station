"""探针：实测三市的**候选接口**，看哪个真能出数据（GOAL.md #6：判死前必须实测）。

## 三个候选（都来自上一轮 probe-city-interact.py 的**页面实证**）

| 市 | 候选 | 来源 |
|---|---|---|
| 宜昌 | `GET/POST /Szrx/lists` | 互动页 JS 里出现 `/Szrx/lists` |
| 洛阳 | `GET https://t.ly.gov.cn/consultview/api/view/selectsiteconsult?siteId=4103000021` | 网上咨询页链接 |
| 芜湖 | `GET /zmhd/` 翻页 + `/content/article/<id>` | 互动页明细链接 |

## 判定标准（**不接受「HTTP 200」当成功**）

接口必须返回**结构化的条目数组**，且**取一条明细确认正文非空**
（GOAL.md #6：`totalResults` 大 ≠ 有问答 —— 天津 IGI 14 万、知识产权局 1.4 万都是空壳）。

⚠ 输出由 Python 自己写文件（`--out`），不经 PowerShell 管道。只读。
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
H = {
    "User-Agent": UA,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}


def _head(s: str, n: int = 400) -> str:
    return re.sub(r"\s+", " ", (s or "")[:n])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)

    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        # ================= 宜昌 /Szrx/lists =================
        say("=" * 72)
        say("宜昌  /Szrx/lists")
        say("=" * 72)
        base = "http://www.yichang.gov.cn"
        for method, kw in (
            ("GET", {"params": {"page": 1, "limit": 20, "areaid": 1}}),
            ("GET", {"params": {"pageIndex": 1, "pageSize": 20, "areaid": 1}}),
            ("POST", {"data": {"page": 1, "limit": 20, "areaid": 1}}),
            ("POST", {"json": {"page": 1, "limit": 20, "areaid": 1}}),
        ):
            try:
                if method == "GET":
                    r = c.get(base + "/Szrx/lists", headers={"Referer": base + "/Szrx/"},
                              **kw)
                else:
                    r = c.post(base + "/Szrx/lists", headers={"Referer": base + "/Szrx/"},
                               **kw)
                say(f"  {method} {kw.get('params') or kw.get('data') or kw.get('json')}"
                    f"  HTTP {r.status_code} ct={r.headers.get('content-type','')[:32]} "
                    f"len={len(r.text)}")
                say(f"    head: {_head(r.text, 300)}")
            except Exception as e:                                    # noqa: BLE001
                say(f"  {method} FAIL {type(e).__name__}: {str(e)[:50]}")

        # ================= 洛阳 t.ly.gov.cn =================
        say("")
        say("=" * 72)
        say("洛阳  t.ly.gov.cn consultview / openview")
        say("=" * 72)
        for url in (
            "https://t.ly.gov.cn/consultview/api/view/selectsiteconsult?siteId=4103000021",
            "https://t.ly.gov.cn/openview/api/view/selectsiteopen?siteId=4103000021",
            "https://t.ly.gov.cn/consultview/api/view/selectsiteconsult?siteId=4103000021&pageIndex=1&pageSize=20",
        ):
            try:
                r = c.get(url, headers={"Referer": "https://www.ly.gov.cn/zmhd/wszx/"})
                say(f"  {url[:95]}")
                say(f"    HTTP {r.status_code} ct={r.headers.get('content-type','')[:32]} "
                    f"len={len(r.text)}")
                say(f"    head: {_head(r.text, 400)}")
                # 尝试解析 JSON 结构，报告顶层键
                try:
                    j = r.json()
                    if isinstance(j, dict):
                        say(f"    JSON keys: {list(j.keys())[:14]}")
                    elif isinstance(j, list):
                        say(f"    JSON list len={len(j)}; [0] keys="
                            f"{list(j[0].keys())[:14] if j and isinstance(j[0], dict) else '?'}")
                except Exception:                                     # noqa: BLE001
                    pass
            except Exception as e:                                    # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:50]}")

        # ================= 芜湖 =================
        say("")
        say("=" * 72)
        say("芜湖  /zmhd/ 翻页 + /content/article")
        say("=" * 72)
        for u in ("https://www.wuhu.gov.cn/zmhd/index.html",
                  "https://www.wuhu.gov.cn/content/article/41275486"):
            try:
                r = c.get(u)
                t = r.text or ""
                say(f"  {u}")
                say(f"    HTTP {r.status_code} len={len(t)}")
                # 明细页：看正文
                if "article" in u:
                    body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                                                      re.sub(r"(?is)<script.*?</script>", " ", t)))
                    say(f"    正文片段: {body[1000:1500]}")
                else:
                    # 列表页：找页码 / 明细
                    pg = re.findall(r"index[_-](\d+)\.html", t)
                    say(f"    页码样本: {sorted(set(pg))[:10]}")
                    art = re.findall(r"/content/article/(\d+)", t)
                    say(f"    article id 样本: {sorted(set(art))[:8]}（共 {len(set(art))}）")
            except Exception as e:                                    # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:50]}")

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
