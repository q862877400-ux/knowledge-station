"""山东剩余 6 市（潍坊/泰安/临沂/德州/聊城/菏泽）第三轮：验证服务端渲染列表 + 详情答复字段。
用法：python recon/sd-city3-probe.py
输出：recon/sd-city3-probe.txt + sd-city3-*.html
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / "sd-city3-probe.txt"

# 服务端渲染候选：列表页 URL
LIST_CAND = [
    ("临沂", "linyi",
     "http://www.linyi.gov.cn/hd/szxx-list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1086"),
    ("临沂2", "linyi2",
     "http://www.linyi.gov.cn/hd/hygq.htm"),
    ("德州", "dezhou",
     "http://www.dezhou.gov.cn/n1480/n59452804/index.html"),
    ("聊城", "liaocheng",
     "http://www.liaocheng.gov.cn/channel_t_156_11559/"),
]

DETAIL_RE = re.compile(
    r'(?:href|url)\s*=\s*["\']([^"\']*(?:leadermailid|mailid|iid|id=|transactId)[^"\']*)["\']', re.I)
ANSWER_HINT = ("答复", "回复", "答复意见", "处理结果", "办理结果", "reply", "answer")


def find_items(text: str, base: str):
    """返回 (绝对链接, 锚文本) 列表。"""
    out = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         text, re.I | re.S):
        href, anchor = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href.lower().startswith(("javascript:", "#")):
            continue
        out.append((urljoin(base, href), anchor))
    return out


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      follow_redirects=True, timeout=20) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for label, abbr, url in LIST_CAND:
                f.write(f"\n## {label} {abbr}\n   LIST {url}\n")
                try:
                    r = c.get(url)
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"   → {type(e).__name__}: {str(e)[:70]}\n")
                    continue
                t = r.text or ""
                f.write(f"   → {r.status_code} ({len(t)} bytes)\n")
                if r.status_code != 200:
                    continue
                (HERE / f"sd-city3-{abbr}-list.html").write_text(t, encoding="utf-8")

                items = find_items(t, url)
                # 只保留像"详情"的链接（含 id 特征）
                detail = [(u, a) for u, a in items if DETAIL_RE.search(u)]
                f.write(f"   items={len(items)} detail_like={len(detail)}\n")
                for u, a in detail[:6]:
                    f.write(f"      · {a[:24]!r} → {u}\n")

                # 取第一个详情页验证答复字段
                if detail:
                    du, da = detail[0]
                    time.sleep(1)
                    try:
                        dr = c.get(du, headers={"Referer": url})
                        dt = dr.text or ""
                        f.write(f"   DETAIL {du}\n      → {dr.status_code} ({len(dt)} bytes)\n")
                        if dr.status_code == 200:
                            (HERE / f"sd-city3-{abbr}-detail.html").write_text(dt, encoding="utf-8")
                            hints = [h for h in ANSWER_HINT if h in dt]
                            f.write(f"      answer_hints={hints}\n")
                            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", dt, re.I | re.S)
                            cells = [re.sub(r"<[^>]+>", "", x).strip() for x in cells]
                            cells = [x for x in cells if x]
                            f.write(f"      cells({len(cells)})={cells[:24]}\n")
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"   DETAIL → {type(e).__name__}: {str(e)[:70]}\n")
                time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
