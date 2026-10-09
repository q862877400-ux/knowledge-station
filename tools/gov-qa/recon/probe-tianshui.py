"""探针：甘肃·天水「政民互动」栏目结构（补甘肃的 `none` 单元）。

实测入口（2026-10-10）：
- `https://www.tianshui.gov.cn/zmhd.jsp?urltype=tree.TreeTempUrl&wbtreeid=1061`（政民互动）
- `https://www.tianshui.gov.cn/zmhd/lybpl_comprehensive.jsp?...wbtreeid=10192`（留言评论）

⚠ 这是 **WAS5 中间件**（`urltype=tree.TreeTempUrl&wbtreeid=`）——
GOAL.md 说过「省市的政府站大量使用同一套中间件，**找到一个就等于找到一片**」。
⇒ 如果天水能通，同样的模式可以套到其他 WAS5 站点。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.tianshui.gov.cn"
H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": B + "/",
}

PAGES = [
    ("政民互动", "/zmhd.jsp?urltype=tree.TreeTempUrl&wbtreeid=1061"),
    ("留言评论", "/zmhd/lybpl_comprehensive.jsp?urltype=tree.TreeTempUrl&wbtreeid=10192"),
]


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, path in PAGES:
            url = B + path
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                print(f"\n{name}\n  FAIL {type(e).__name__} {str(e)[:50]}")
                continue
            t = r.text or ""
            print(f"\n{'=' * 56}\n{name}  HTTP {r.status_code} len={len(t)}\n{'=' * 56}")

            # ① 条目链接（WAS5 常见形式）
            items = []
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                txt = re.sub(r"\s+", " ", txt).strip()
                if len(txt) >= 8 and re.search(r"\.jsp|\.do|wbtreeid|content|detail", href, re.I):
                    items.append((txt, href))
            print(f"  条目候选 {len(items)}，前 6：")
            for txt, href in items[:6]:
                print(f"    · {txt[:40]:42s} {href[:78]}")

            # ② 分页线索（WAS5 常见 `wbtreeid=…&pageNo=`）
            pg = sorted(set(re.findall(r"(pageNo|page|currentpage|pageno)[=_]?\d*", t, re.I)))[:6]
            print(f"  分页线索: {pg}")

            # ③ 其它 .jsp 路径
            jsps = sorted(set(re.findall(r"[\"'](/[a-zA-Z0-9_\-/]{4,80}\.jsp)[\"']", t)))[:10]
            print(f"  其它 .jsp: {jsps}")

            # ④ 关键词位置
            for kw in ("来信选登", "选登", "公开", "回复", "已办结", "总数"):
                if kw in t:
                    i = t.find(kw)
                    print(f"  [{kw}] {re.sub(r'\\s+', ' ', t[max(0, i-70):i+70])[:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
