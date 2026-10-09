"""探人大系统的「征求意见」栏目 —— M4 用。

目标：找到**公开的征求意见条目列表 + 详情**（可能有公众意见，也可能只有提交入口）。
按 GOAL.md 硬约束 6：判死前必须实测取一条详情确认正文非空。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

SEEDS = [
    ("全国人大", "http://www.npc.gov.cn"),
    ("北京人大", "http://www.bjrd.gov.cn"),
    ("上海人大", "http://www.shrd.gov.cn"),
    ("广东人大", "https://www.gdpc.gov.cn"),
    ("江苏人大", "https://www.jsrd.gov.cn"),
    ("山东人大", "http://www.sdrd.gov.cn"),
    ("河南人大", "http://www.hnrd.gov.cn"),
    ("四川人大", "http://www.scspc.gov.cn"),
]

#: 与「征求公众意见」相关的关键词
KW = ("征求意见", "法规草案", "立法建议", "公众参与", "意见征集", "草案征求意见", "立法征求")


def main() -> int:
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for name, base in SEEDS:
            try:
                r = c.get(base)
            except Exception as e:                                      # noqa: BLE001
                print(f"{name:8s} FAIL {type(e).__name__} {str(e)[:40]}")
                continue
            t = r.text or ""
            hits = [k for k in KW if k in t]
            print(f"{name:8s} HTTP {r.status_code} len={len(t):7d} 命中={hits}")
            if not hits:
                continue
            # 抓所有含关键词的 <a href>
            seen = set()
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                txt = re.sub(r"\s+", " ", txt).strip()
                if any(k in txt for k in KW) and href not in seen:
                    seen.add(href)
                    print(f"    → {txt[:38]:40s} {href[:90]}")
                if len(seen) >= 6:
                    break
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
