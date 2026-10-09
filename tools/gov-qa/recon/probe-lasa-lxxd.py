"""探针：拉萨「来信选登」列表结构（`/lasa/lxxd/hd_mailbox.shtml`）。

这是**西藏第一条可用的公开问答通道** —— 值得深挖。
只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

FULL_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

BASE = "https://www.lasa.gov.cn"
LIST = BASE + "/lasa/lxxd/hd_mailbox.shtml"


def main() -> int:
    with httpx.Client(timeout=25, headers=FULL_HEADERS,
                      follow_redirects=True, trust_env=False, verify=False) as c:
        r = c.get(LIST)
        t = r.text or ""
        print(f"{LIST}\n  HTTP {r.status_code} len={len(t)}")

        # ① 找条目链接
        items = []
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
            href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
            txt = re.sub(r"\s+", " ", txt).strip()
            if len(txt) >= 8 and re.search(r"content|detail|/\d{6,}", href):
                items.append((txt, href))
        print(f"  条目候选 {len(items)} 条，前 6：")
        for txt, href in items[:6]:
            print(f"    · {txt[:44]:46s} {href[:76]}")

        # ② 找分页
        pg = sorted(set(re.findall(r"(index[_\-]?\d+\.s?html?|page[=_]?\d+|hd_mailbox_\d+)", t)))[:8]
        print(f"  分页线索: {pg}")

        # ③ 找接口
        api = sorted(set(re.findall(r"[\"'](/[a-zA-Z0-9_\-/\.]{8,90})[\"']", t)))[:12]
        print(f"  路径线索: {api}")

        # ④ 取一条详情看结构
        if items:
            href = items[0][1]
            if href.startswith("/"):
                href = BASE + href
            elif not href.startswith("http"):
                href = BASE + "/lasa/lxxd/" + href.lstrip("./")
            try:
                d = c.get(href)
                body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", d.text, flags=re.S | re.I)
                body = re.sub(r"<[^>]+>", " ", body)
                body = re.sub(r"\s+", " ", body).strip()
                print(f"\n  详情 {href}\n    HTTP {d.status_code} 正文约 {len(body)} 字")
                print(f"    片段: {body[:220]}")
            except Exception as e:                                      # noqa: BLE001
                print(f"\n  详情 FAIL {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
