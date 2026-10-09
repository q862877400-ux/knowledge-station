"""探针：西藏信访平台 `xzxf.xizang.gov.cn` 是否有公开的来信选登。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

CANDIDATES = [
    "http://xzxf.xizang.gov.cn/ocp/wsxx.html",
    "http://xzxf.xizang.gov.cn/ocp/",
    "http://xzxf.xizang.gov.cn/",
]


def main() -> int:
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for url in CANDIDATES:
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                print(f"{url}\n  FAIL {type(e).__name__} {str(e)[:60]}")
                continue
            t = r.text or ""
            print(f"\n{url}\n  HTTP {r.status_code} len={len(t)}")
            # 找 API / 数据接口线索
            for pat, label in ((r"https?://[^\"'\s]{10,120}", "绝对 URL"),
                               (r"[\"'](/[a-zA-Z0-9_\-/\.]{6,80})[\"']", "相对路径"),
                               (r"(ajax|api|list|query|select)[A-Za-z_]*\s*[:(]", "接口线索")):
                hits = sorted(set(re.findall(pat, t)))[:6]
                if hits:
                    print(f"  {label}: {hits}")
            # 找关键词
            for kw in ("来信选登", "公开", "选登", "办理", "答复", "列表"):
                if kw in t:
                    i = t.find(kw)
                    seg = re.sub(r"\s+", " ", t[max(0, i - 60):i + 60])
                    print(f"  [{kw}] {seg[:130]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
