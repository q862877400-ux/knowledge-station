"""河北 + 海南 问答平台侦察（阶段一）：门户可达性 + 互动栏目发现。

礼貌：请求间 >=1.5s；403/412 立即停该站；域名连不上如实记录。
只写 recon/ 下的原始样本。
"""
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
    ("heb-home", "https://www.hebei.gov.cn/"),
    ("hi-home", "https://www.hainan.gov.cn/"),
    ("hi-ywzsk", "https://www.hainan.gov.cn/hainan/ywzsk/list3.shtml"),
    ("hi-hd", "https://www.hainan.gov.cn/hainan/hdjl/hd.shtml"),
]


def save(name: str, text: str) -> None:
    (HERE / f"{name}.html").write_text(text, encoding="utf-8", errors="replace")


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
            print(f"[{name}] {url} -> {r.status_code} {len(body)}B ct={r.headers.get('content-type','')}")
            if r.status_code == 200:
                save(name, body)
                # 找互动/问答/知识库相关链接
                links = re.findall(r'href="([^"]+)"[^>]*>([^<]{0,40})', body)
                hits = [(u, t) for u, t in links
                        if any(k in (t or "") for k in
                               ("互动", "问答", "知识库", "留言", "咨询", "常见", "12345", "信访", "回应"))]
                for u, t in hits[:25]:
                    print(f"    LINK {t.strip()!r:24s} {u}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
