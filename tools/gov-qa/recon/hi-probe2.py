"""海南 阶段二：抓问答候选栏目 + 业务知识库明细，判断是否 Q&A。"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.5

TARGETS = [
    ("hi-zcwd", "https://www.hainan.gov.cn/hainan/zcwd/zcwd.shtml"),
    ("hi-hygq", "https://www.hainan.gov.cn/hainan/hygq/list3.shtml"),
    ("hi-zjdc", "https://www.hainan.gov.cn/hainan/zjdc/dczj_list.shtml"),
    ("hi-ywzsk-detail", "https://www.hainan.gov.cn/hainan/ywzsk/202609/9f65a338002a422198dd00582bd258c6.shtml"),
    ("hi-pagejs", "https://www.hainan.gov.cn/hainan/xhtml/js/page.js"),
]


def main() -> int:
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, url in TARGETS:
            try:
                r = cli.get(url)
            except Exception as e:  # noqa: BLE001
                print(f"[{name}] {url} -> {type(e).__name__}: {e}")
                continue
            body = r.text or ""
            ext = "js" if name.endswith("js") else "html"
            (HERE / f"{name}.{ext}").write_text(body, encoding="utf-8", errors="replace")
            print(f"[{name}] {url} -> {r.status_code} {len(body)}B")
            if ext == "html" and r.status_code == 200:
                # 看列表条目形态
                items = re.findall(r'<a href="(/hainan/[^"]+\.shtml)"[^>]*>([^<]{2,60})</a>', body)
                for u, t in items[:8]:
                    print(f"    ITEM {t.strip()!r:50s} {u}")
                # 是否含问/答
                for kw in ("问：", "问:", "答：", "答:", "咨询", "提问"):
                    if kw in body:
                        print(f"    KW {kw} 出现 {body.count(kw)} 次")
                cp = re.search(r"createPageHTML\('page_div',(\d+)", body)
                if cp:
                    print(f"    分页 createPageHTML 共 {cp.group(1)} 页")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
