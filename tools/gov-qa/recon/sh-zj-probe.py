"""上海/浙江问答平台侦察 · 第一轮可达性 + 形态探测。

用法：python recon/sh-zj-probe.py <stage>
  stage=sh1 上海候选入口   stage=zj1 浙江候选入口
每请求间隔 >=1.5s；403/412 记录后停该站；把响应头 + 关键片段落 recon/sh-zj-probe-<stage>.txt。
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.6

SH = [
    ("wsxf-list-https", "https://wsxf.sh.gov.cn/xf_swldxx/"),
    ("wsxf-list-http", "http://wsxf.sh.gov.cn/xf_swldxx/"),
    ("wsxf-root-https", "https://wsxf.sh.gov.cn/"),
    ("sh-zmhd", "https://www.sh.gov.cn/zmhd/"),
    ("sh-12345", "https://12345.sh.gov.cn/"),
    ("sh-zwdt", "https://zwdt.sh.gov.cn/"),
    ("sh-gov-root", "https://www.sh.gov.cn/"),
]

ZJ = [
    ("zjzwfw", "https://www.zjzwfw.gov.cn/"),
    ("zj-gov", "https://www.zj.gov.cn/"),
    ("zj12345", "https://www.zj12345.gov.cn/"),
    ("zj-sthjt", "https://sthjt.zj.gov.cn/"),
    ("zj-hdjl", "https://www.zj.gov.cn/col/col1229019488/"),
]

SH2 = [
    ("sh12345-http", "http://www.sh12345.gov.cn/"),
    ("sh12345-https", "https://www.sh12345.gov.cn/"),
    ("xfb-xfdt-http", "http://xfb.sh.gov.cn/xfb/xfdt/index.html"),
    ("xfb-xfdt-https", "https://xfb.sh.gov.cn/xfb/xfdt/index.html"),
    ("sh-dept-lyb", "https://www.sh.gov.cn/nw2/nw2314/nw38605/nw38651/index.html"),
    ("sh-dist-lyb", "https://www.sh.gov.cn/nw2/nw2314/nw38605/nw40906/index.html"),
    ("sh-zmhd-sub", "https://www.sh.gov.cn/nw2/nw2314/nw38605/index.html"),
    ("wsxf-rmyjzj", "http://wsxf.sh.gov.cn/xf_rmyjzj/index1.aspx"),
]

SETS = {"sh1": SH, "sh2": SH2, "zj1": ZJ}


def probe(name: str, url: str, c) -> str:
    try:
        r = c.get(url)
    except Exception as e:                                                  # noqa: BLE001
        return f"[{name}] {url}\n    EXC {type(e).__name__}: {e}\n"
    html = r.text or ""
    ct = r.headers.get("content-type", "")
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:80]
    hits = [k for k in ("互动", "留言", "问答", "信访", "信箱", "咨询", "答复", "12345")
            if k in html]
    return (f"[{name}] {url}\n    status={r.status_code} len={len(html)} "
            f"ct={ct[:40]} title={title!r} kw={hits}\n")


def main() -> int:
    import httpx
    stage = sys.argv[1] if len(sys.argv) > 1 else "sh1"
    urls = SETS[stage]
    lines = [f"=== sh-zj-probe stage={stage} ===\n"]
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=25, follow_redirects=True) as c:
        for name, url in urls:
            lines.append(probe(name, url, c))
            time.sleep(PAUSE)
    out = HERE / f"sh-zj-probe-{stage}.txt"
    out.write_text("".join(lines), encoding="utf-8")
    print("".join(lines))
    print(f"[probe] -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
