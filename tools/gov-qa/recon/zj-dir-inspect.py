"""看浙江名录页（col/col1544854）里部门链接的真实形态。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

PAGE = "http://www.zj.gov.cn/col/col1544854/index.html"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(PAGE)
    t = r.text
    print("len", len(t))
    hrefs = re.findall(r'href="([^"]+)"', t)
    zj = [h for h in hrefs if ".zj.gov.cn" in h or "zj.gov.cn" in h]
    print(f"zj.gov.cn 链接 {len(zj)} 条，样例：")
    for h in zj[:15]:
        print("  ", h[:110])
    # 有没有 JS 渲染的列表（artitle/数据接口）
    for kw in ("artitleAdd", "xmlx", "json", "ajax", "webapp"):
        n = len(re.findall(kw, t, re.I))
        if n:
            print(f"{kw} x{n}")
    (HERE / "zj-dir-page.html").write_text(t, encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
