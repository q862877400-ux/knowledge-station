"""探针：天水聚合列表页里「总页数」到底怎么表达。

adapter 的假设（`totalpage=(\d+)` 能从响应里抓到）**实测失败** ⇒ 只翻了 1 页。
本探针找真实的表达方式。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

BASE = "http://www.tianshui.gov.cn/zmhd/"
LIST_TPL = (BASE + "xj_list.jsp?totalpage={tp}&PAGENUM={p}"
            "&urltype=tree.TreeTempUrl&wbtreeid={col}")
COL = "3861"
H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Referer": "http://www.tianshui.gov.cn/zmhd.jsp?urltype=tree.TreeTempUrl&wbtreeid=1061",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for tp in (1, 99):
            url = LIST_TPL.format(tp=tp, p=1, col=COL)
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                print(f"tp={tp} FAIL {type(e).__name__}")
                continue
            t = r.text or ""
            print(f"\n{'=' * 56}\ntp={tp}  HTTP {r.status_code} len={len(t)}\n{'=' * 56}")

            # ① totalpage 出现处
            for m in re.finditer(r"totalpage[^&\"'\s<>]{0,40}", t, re.I):
                print(f"  totalpage 上下文: {m.group(0)[:80]}")
                break

            # ② 「共 N 页 / 页次 / 1/79」这类
            for pat in (r"共\s*<?[^>]*>?\s*(\d+)\s*页", r"(\d+)\s*/\s*(\d+)\s*页",
                        r"页次[:：]?\s*(\d+)\s*/\s*(\d+)", r"totalPage['\"]?\s*[:=]\s*(\d+)",
                        r"pageCount['\"]?\s*[:=]\s*(\d+)", r"共\s*(\d+)\s*条"):
                found = re.findall(pat, t, re.I)
                if found:
                    print(f"  [{pat[:28]}] → {found[:6]}")

            # ③ 分页链接形态
            links = sorted(set(re.findall(r'href="([^"]*PAGENUM=\d+[^"]*)"', t)))
            print(f"  分页链接 {len(links)} 个，前 3：")
            for l in links[:3]:
                print(f"    {l[:120]}")

            # ④ 本页条目数
            n_items = len(set(re.findall(r"leadermailid=([0-9A-Fa-f]{16,})", t)))
            print(f"  本页唯一 leadermailid: {n_items}")

            # ⑤ 所有 JS 变量里像页数的
            for m in re.finditer(r"(?:var|let|const)\s+(\w*(?:page|total|count)\w*)\s*=\s*([^;]{1,40});", t, re.I):
                print(f"  JS: {m.group(1)} = {m.group(2)[:40]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
