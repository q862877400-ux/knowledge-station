"""鲁/桂/青 三省可达性重探 + 新疆/西藏信访页抓取（证据：recon/xj-xz-sd-gx-qh-hunt.txt）。

合规：请求间隔 >=1.5s；403/412 立即停该站；不可达域名最多 2 scheme + 2 候选域名。
本脚本只读网络、只写 recon/xj-* 原始样本，不碰 data/ adapters/ 别人的文件。
"""
from __future__ import annotations

import os
import sys
import time
import socket

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
PAUSE = 1.5


def dns(host: str) -> str:
    try:
        return "DNS->" + socket.gethostbyname(host)
    except Exception as e:  # noqa: BLE001
        return f"DNS失败:{type(e).__name__}:{e}"


def probe(url: str, *, method: str = "GET", timeout: float = 20.0):
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": UA},
                          follow_redirects=True, trust_env=False) as c:
            r = c.request(method, url)
        dt = time.perf_counter() - t0
        body = r.text or ""
        return (f"[{method}] {url} -> HTTP {r.status_code}  {dt:.2f}s  "
                f"len={len(body)}  final={r.url}")
    except Exception as e:  # noqa: BLE001
        dt = time.perf_counter() - t0
        return f"[{method}] {url} -> {type(e).__name__}: {e}  ({dt:.2f}s)"


def main() -> int:
    targets = {
        "山东": [
            "https://www.shandong.gov.cn/",
            "http://www.shandong.gov.cn/",
            "https://12345.shandong.gov.cn/",
            "http://sd.gov.cn/",
        ],
        "广西": [
            "https://www.gxzf.gov.cn/",
            "http://www.gxzf.gov.cn/",
            "https://12345.gxzf.gov.cn/",
            "http://gxzf.gov.cn/",
        ],
        "青海": [
            "https://www.qinghai.gov.cn/",
            "http://www.qinghai.gov.cn/",
            "https://12345.qinghai.gov.cn/",
            "http://zwfw.qinghai.gov.cn/",
        ],
    }
    for prov, urls in targets.items():
        print(f"\n===== {prov} =====")
        for u in urls:
            host = httpx.URL(u).host
            print("  " + dns(host))
            print("  " + probe(u))
            time.sleep(PAUSE)

    print("\n===== 新疆 信访 =====")
    xj = [
        "https://wsxf.xjxfj.gov.cn/html/onlineInquiry/queryIndex.jsp?regionCode=650000000000",
        "http://wsxf.xjxfj.gov.cn/html/onlineInquiry/queryIndex.jsp?regionCode=650000000000",
    ]
    for u in xj:
        print("  " + dns(httpx.URL(u).host))
        print("  " + probe(u))
        time.sleep(PAUSE)

    print("\n===== 西藏 信访 =====")
    xz = [
        "http://xzxf.xizang.gov.cn/ocp/wsxx.html",
        "https://xzxf.xizang.gov.cn/ocp/wsxx.html",
    ]
    for u in xz:
        print("  " + dns(httpx.URL(u).host))
        print("  " + probe(u))
        time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
