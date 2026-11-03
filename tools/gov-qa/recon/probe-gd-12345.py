"""探针：广东 5 市「真正的公开留言栏目」实测（2026-10-10 第 8 轮）。

## 来源
`probe-gd-hd-entries.py` 从各市互动页扒出真入口（排除访谈/征集/问卷等非问答栏目）：

| 市 | 真入口 |
|---|---|
| 东莞 | `dg.gov.cn/12345/201801/page/order/wwqzbss_action.html`、`/12345/` |
| 韶关 | `12345.sg.gov.cn/gov/szhd.html`（市长信箱）、`12345.sg.gov.cn/201904/page/smsq/smsqlist.html` |
| 中山 | `12345.zs.gov.cn/ordernew/pact.do?index=1`、`12345.zs.gov.cn/order/pact.do?index=9` |
| 河源 | `heyuan.gov.cn/hd/hys12345/web/publicOrderList.html`、`.../web/kmIndex.html` |
| 珠海 | `zhuhai.gov.cn/hd/zxts/wyxx/index.html`（我要咨询）、`/zxts/zxfk/`、`/zxts/wyts/` |

本探针对每个入口：GET 页面 → 抓「列表条目链接 / 接口端点 / 分页参数」→ 判定：
 · **静态 SSR**（HTML 里直接有条目）⇒ 可复用 `_post_list_common` 类引擎
 · **JS/接口**（只有骨架，条目靠 ajax）⇒ dump 出 ajax 端点，下一步再打
 · **表单类**（"我要咨询"是**写信表单**，不是公开列表）⇒ 明确排除

⚠ 只读。输出由 Python 自己写文件。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: (市, 角色, url)
PAGES = [
    ("东莞", "12345-我要咨询", "http://www.dg.gov.cn/12345/201801/page/order/wwqzbss_action.html"),
    ("东莞", "12345-更多诉求", "http://www.dg.gov.cn/12345/201801/page/order/more_appeals_list.html"),
    ("东莞", "12345-门户", "http://www.dg.gov.cn/12345/"),
    ("韶关", "12345-市长信箱", "https://12345.sg.gov.cn/gov/szhd.html"),
    ("韶关", "12345-信件列表", "https://12345.sg.gov.cn/201904/page/smsq/smsqlist.html?code=&title=&queryStartTime=&queryEndTime="),
    ("韶关", "12345-知识库", "https://12345.sg.gov.cn/201904/page/km/interf/kmIndexNew.html"),
    ("中山", "12345-pact", "https://12345.zs.gov.cn/ordernew/pact.do?index=1&type=1"),
    ("中山", "12345-order9", "http://12345.zs.gov.cn/order/pact.do?index=9"),
    ("河源", "诉求公示", "http://www.heyuan.gov.cn/hd/hys12345/web/publicOrderList.html"),
    ("河源", "知识库", "http://www.heyuan.gov.cn/hd/hys12345/web/kmIndex.html"),
    ("河源", "政民互动", "http://www.heyuan.gov.cn/hd/hys12345/web/index.html"),
    ("珠海", "我要咨询", "https://www.zhuhai.gov.cn/hd/zxts/wyxx/index.html"),
    ("珠海", "咨询反馈", "https://www.zhuhai.gov.cn/hd/zxts/zxfk/index.html"),
    ("珠海", "投诉反馈", "https://www.zhuhai.gov.cn/hd/zxts/tsfk/index.html"),
]

#: 详情/条目链接特征
DETAIL_PAT = re.compile(
    r'href=["\']([^"\']*(?:content|detail|show|info|view|letter|order|appeal|sm|fj)[^"\']*'
    r'(?:\d{3,}|\.html|\.do)[^"\']*)["\']', re.I)

#: 接口端点特征
EP_PAT = re.compile(
    r'["\'](/?[A-Za-z0-9_\-./]*(?:query|list|page|search|ajax|api|do|json|action)'
    r'[A-Za-z0-9_\-./]*)["\']', re.I)

#: 「我要写信」表单特征（不是公开列表）
FORM_HINT = re.compile(r'(写信|提交|我要咨询|我要投诉|textarea|请填写|姓名|联系电话)', re.I)


def _probe(c, name: str, role: str, url: str) -> list[str]:
    out = [f"\n{'-' * 72}", f"[{name}] {role}", f"  {url}"]
    try:
        r = c.get(url, headers={**H, "Referer": url})
    except Exception as e:                                              # noqa: BLE001
        out.append(f"  FAIL {type(e).__name__}: {str(e)[:70]}")
        return out
    t = r.text or ""
    out.append(f"  HTTP {r.status_code} len={len(t)} ct={r.headers.get('content-type','')[:34]} "
               f"final={r.url}")

    # 1) 静态条目
    det = DETAIL_PAT.findall(t)
    det = list(dict.fromkeys(det))
    out.append(f"  -- 疑似条目/详情链接 {len(det)} 条 --")
    for d in det[:6]:
        out.append(f"     {urljoin(str(r.url), d)[:110]}")

    # 2) 接口端点
    eps = EP_PAT.findall(t)
    eps = [e for e in dict.fromkeys(eps) if len(e) > 6]
    out.append(f"  -- 接口端点候选 {len(eps)} 条 --")
    for e in eps[:10]:
        out.append(f"     {e[:100]}")

    # 3) 是否写信表单
    if FORM_HINT.search(t) and len(det) < 3:
        out.append("  ⚠ 疑似「写信表单」页（非公开列表）")

    # 4) 分页线索
    pg = re.findall(r'(pageNum|pageNum|pageIndex|pageNo|page|current|offset)\s*[=:]\s*\d+', t, re.I)
    if pg:
        out.append(f"  -- 分页参数线索: {list(dict.fromkeys(pg))[:8]}")

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    lines: list[str] = []

    with httpx.Client(timeout=30, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, role, url in PAGES:
            lines.extend(_probe(c, name, role, url))

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
