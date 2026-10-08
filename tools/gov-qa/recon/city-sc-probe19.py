"""city-sc-probe19：扒 JS 常量 —— 广安/资阳(config.js+commonApi+zmhd)、内江(zw_mailbox)、雅安(mail.js)、乐山(hdjl.js)、阿坝/广元。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# (标签, [js_url ...])
JSS = [
    ("广安-config", ["https://www.guang-an.gov.cn/gasrmzfw/pc2023/js/basehd/config.js",
                     "https://www.guang-an.gov.cn/default/libs/commonApi.js",
                     "https://www.guang-an.gov.cn/gasrmzfw/pc2023/js/hdjl2024.js"]),
    ("资阳-config", ["https://www.ziyang.gov.cn/default/libs/config.js",
                     "https://www.ziyang.gov.cn/zysrmzf/pc2024/js/commonApi.js",
                     "https://www.ziyang.gov.cn/zysrmzf/pc2024/js/zmhd.js"]),
    ("内江-mail", ["https://www.neijiang.gov.cn/njs/xhtml/mail/js/zw_mailbox.js",
                    "https://www.neijiang.gov.cn/njs/xhtml/js/zmhd_12345.js"]),
    ("雅安-mail", ["https://www.yaan.gov.cn/mail/v2/js/mail.js"]),
    ("乐山-hdjl", ["https://www.leshan.gov.cn/lsswszf/resource/js/hdjl.js"]),
    ("阿坝-common", ["https://www.abazhou.gov.cn/abazhou/xhtml/abzrmzf/pc2025/js/common.js"]),
    ("广元-common", ["https://www.gy.gov.cn/dist/js/common.js"]),
]
NEEDLES = ("openMailList", "ajaxUrl", "tenantId", "siteId", "qdId", "userId",
           "/api/", "list", "detail", "url:", "baseUrl", "interface", "sr.hd",
           "pageSize", "pagesize", "current", "mailType", "channelId", "do", "shtml", "jsp")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u):
    try:
        return requests.get(u, timeout=25, allow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    for label, urls in JSS:
        w(f"\n===== {label} =====")
        for u in urls:
            r = get(u)
            if not hasattr(r, "status_code"):
                w(f"  {u} -> ERR {r}")
                continue
            w(f"  {u} -> {r.status_code} len={len(r.text)}")
            if r.status_code != 200:
                continue
            txt = r.text
            # 提取所有字符串字面量里含 api/接口关键字的
            seen = set()
            for m in re.finditer(r'["\']([^"\']{2,150})["\']', txt):
                v = m.group(1)
                if v in seen:
                    continue
                if any(k in v for k in ("api", "openMail", "list", "List", "detail", "Detail",
                                        "mail", "Mail", "url", "Url", "URL", ".do", ".shtml", ".jsp")):
                    seen.add(v)
                    w("     " + v[:150])
            # ajaxUrl 对象块
            for m in re.finditer(r'ajaxUrl\s*[:=]\s*\{[^}]{0,600}\}', txt, re.S):
                w("     [ajaxUrl] " + re.sub(r"\s+", " ", m.group(0))[:400])
            for m in re.finditer(r'(tenantId|siteId|qdId|userId)\s*[:=]\s*["\']?([A-Za-z0-9_\-]+)', txt):
                w(f"     [{m.group(1)}] = {m.group(2)}")


if __name__ == "__main__":
    main()
