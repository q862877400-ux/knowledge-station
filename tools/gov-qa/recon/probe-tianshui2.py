"""探针：天水「政民互动」详情页结构 + 分页（WAS5 leadermail）。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.tianshui.gov.cn"
LIST = B + "/zmhd.jsp?urltype=tree.TreeTempUrl&wbtreeid=1061"
H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": B + "/",
}


def _plain(html: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</div>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        r = c.get(LIST)
        t = r.text or ""
        print(f"列表 HTTP {r.status_code} len={len(t)}")

        # 找 leadermailid 完整链接
        links = re.findall(r'href="([^"]*leadermailid=[^"]+)"', t)
        print(f"leadermailid 链接 {len(links)} 条，首条:")
        if links:
            first = links[0]
            if first.startswith("/"):
                first = B + first
            elif not first.startswith("http"):
                first = B + "/" + first
            print(f"  {first[:150]}")

            # 取详情
            d = c.get(first)
            body = _plain(d.text or "")
            print(f"\n详情 HTTP {d.status_code} 正文约 {len(body)} 字")
            print(f"  前 600 字:\n{body[:600]}")

            # 找关键字段
            for kw in ("问题", "答复", "回复", "来信人", "办理部门", "时间", "状态"):
                if kw in body:
                    i = body.find(kw)
                    print(f"  [{kw}] {re.sub(chr(10), ' ', body[max(0,i-30):i+90])[:130]}")

        # 分页：WAS5 常见 `wbtreeid=1061&pageNo=2` 或 `&page=2`
        for pat in (r"wbtreeid=1061&(?:amp;)?pageNo=(\d+)", r"pageNo=(\d+)",
                    r"currentpage=(\d+)", r"&(?:amp;)?page=(\d+)"):
            found = sorted(set(re.findall(pat, t)))
            if found:
                print(f"\n分页（{pat}）: {found[:8]}")
                break
        else:
            print("\n未找到分页参数（可能一页显示全部）")

        # 条目总数
        for m in re.finditer(r"(共|总计)\s*(\d+)\s*(条|项|页)", t):
            print(f"  总数线索: {m.group(0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
