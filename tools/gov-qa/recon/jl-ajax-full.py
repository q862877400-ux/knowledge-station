"""打印吉林 ajax 脚本全文（5KB，小），找 contextPath/siteId/appId 的真实取值。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

JS = "https://sthjt.jl.gov.cn/images/ajax_index_cmy_20211110.js"
OUT = HERE / "jl-ajax-full.js"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(JS)
        OUT.write_text(r.text or "", encoding="utf-8")
        # 同时取列表页里 contextPath 的定义
        p = c.get("https://sthjt.jl.gov.cn/zmhd/tzxx/lyxd/")
        html = p.text or ""
        import re
        lines = [l for l in html.splitlines() if "contextPath" in l or "siteId" in l or "appId" in l]
        Path(HERE / "jl-contextpath.txt").write_text("\n".join(lines[:20]), encoding="utf-8")
    print("written", OUT, "and jl-contextpath.txt")
    return 0


if __name__ == "__main__":
    main()
