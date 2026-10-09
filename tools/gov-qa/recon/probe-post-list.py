r"""探针：广东「`content/post_<id>.html` 静态列表」这一族怎么翻页、怎么取正文。

## 背景

`recon/probe-city-hd-api.py` 探出广东剩 13 市里 **9 个**共用一套静态列表 CMS
（列表页 + `/content/post_<id>.html` 明细）：

| 市 | 留言选登列表 |
|---|---|
| 云浮 | `/hdjl/xyxd/index.html` |
| 惠州 | `/zmhd/ftjhyg/` |
| 揭阳 | `/hdjl/ldjf/` |
| 江门 | `/gzhd/lyxd/` |
| 珠海 | `/hd/mszx/ftyg/` |
| 韶关 | `/hd/jgfk/` |
| 河源 | `/zmhd/zjdc/jgfk/` |
| 中山 | （待定） |
| 汕尾 | `/shanwei/zmhd/gtjhyg/` |

**若翻页规律统一 ⇒ 写一个适配器覆盖一片**（GOAL.md 的「找到一个 = 找到一片」）。

## 本探针查什么

对每个列表 URL：
1. 页面上有多少 `content/post_<id>.html` 链接、标题长什么样
2. **翻页方式**：试 `index_1.html` / `index_2.html`、`list_1.html`、
   以及 JS 里的分页变量（`pageCount` / `totalPage` / `recordCount`）
3. 取**一条明细** dump 正文结构 —— 确认「问题 + 答复」都在同一页
   （GOAL.md #6：不看一条明细不许下结论）

⚠ 输出由 Python 自己写文件（`--out`）。只读，不落盘到 data/。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

TARGETS = {
    "云浮市": "https://www.yunfu.gov.cn/hdjl/xyxd/index.html",
    "惠州市": "http://www.huizhou.gov.cn/zmhd/ftjhyg/",
    "揭阳市": "http://www.jieyang.gov.cn/hdjl/ldjf/",
    "江门市": "http://www.jiangmen.gov.cn/gzhd/lyxd/",
    "珠海市": "https://www.zhuhai.gov.cn/hd/mszx/ftyg/",
    "韶关市": "https://www.sg.gov.cn/hd/jgfk/",
    "河源市": "http://www.heyuan.gov.cn/zmhd/zjdc/jgfk/",
    "汕尾市": "https://www.shanwei.gov.cn/shanwei/zmhd/gtjhyg/",
}

POST_RE = re.compile(r'href=["\']([^"\']*?/content/post_(\d+)\.html)["\']', re.I)
TAG_RE = re.compile(r"<[^>]+>")


def _t(f: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", f or "")).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    L: list[str] = []

    def say(s: str = "") -> None:
        L.append(s)

    with httpx.Client(headers=H, follow_redirects=True, trust_env=False,
                      verify=False) as c:
        for city, url in TARGETS.items():
            say(f"\n{'=' * 72}")
            say(f"{city}  {url}")
            say("=" * 72)
            try:
                r = c.get(url, timeout=20)
            except Exception as e:                                    # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:60]}")
                continue
            t = r.text or ""
            say(f"  HTTP {r.status_code} len={len(t)} final={r.url}")
            if r.status_code != 200:
                continue

            hits = POST_RE.findall(t)
            ids = [h[1] for h in hits]
            say(f"  content/post 链接 {len(hits)} 条｜id 样本 "
                f"{sorted(set(ids), key=int)[:5]}…{sorted(set(ids), key=int)[-3:] if ids else ''}")

            # 分页线索
            pg = re.findall(r"(?:pageCount|totalPage|pageNum|recordCount|total)\s*[:=]\s*['\"]?(\d+)",
                            t, re.I)
            say(f"  分页 JS 变量: {sorted(set(pg))[:8]}")
            plinks = sorted(set(re.findall(
                r"href=[\"']([^\"']*(?:index|list)_\d+\.html)[\"']", t, re.I)))
            say(f"  index_/list_ 页码链接: {plinks[:6]}")

            # 明细
            if hits:
                du = hits[0][0]
                du = du if du.startswith("http") else str(httpx.URL(url).join(du))
                try:
                    dr = c.get(du, timeout=20)
                    dt = dr.text or ""
                    body = _t(re.sub(r"(?is)<script.*?</script>", " ", dt))
                    say(f"  ---- 明细 {du} HTTP {dr.status_code} len={len(dt)} ----")
                    say(f"    正文片段: {body[300:1100]}")
                except Exception as e:                                # noqa: BLE001
                    say(f"  明细 FAIL {type(e).__name__}")

            # 试翻页
            base = url if url.endswith("/") else url.rsplit("/", 1)[0] + "/"
            for cand in (base + "index_1.html", base + "index_2.html",
                         base + "list_1.html"):
                try:
                    rr = c.get(cand, timeout=12)
                    n = len(POST_RE.findall(rr.text or ""))
                    say(f"    试 {cand.rsplit('/', 2)[-2] + '/' + cand.rsplit('/', 1)[-1]:24s}"
                        f" HTTP {rr.status_code} post 链接={n}")
                except Exception as e:                                # noqa: BLE001
                    say(f"    试 {cand[-24:]:24s} FAIL {type(e).__name__}")

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
