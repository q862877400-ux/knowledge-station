"""city-sc-probe18：四川第 7~21 市 互动入口深挖（扒 script/接口常量/中间件指纹）。

对每个候选入口页：抓 HTML → 列 <script src>、找 ajaxUrl/config.js/api 常量、
找中间件指纹（IGI/dataproxy/EWB/9050/数融 openMailList 等）。
"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# (城市, [候选入口 URL ...])
TARGETS = [
    ("广安", ["https://www.guang-an.gov.cn/gasrmzfw/hdjl/pc/list.html"]),
    ("资阳", ["https://www.ziyang.gov.cn/zysrmzf/hdjl/pc/list.html",
              "https://www.ziyang.gov.cn/zysrmzf/mail/notice.html?sourceId=7",
              "http://zymail.ziyang.gov.cn:9050/szweb/index"]),
    ("内江", ["https://www.neijiang.gov.cn/njs/mail/mail_list.shtml",
              "https://www.neijiang.gov.cn/njs/hdjl/zmhd.shtml"]),
    ("雅安", ["https://www.yaan.gov.cn/mail/index.html",
              "https://www.yaan.gov.cn/12345.html",
              "http://yamail.yaan.gov.cn:9050/szweb/index"]),
    ("乐山", ["https://www.leshan.gov.cn/lsswszf/zmhd/index.html"]),
    ("南充", ["https://www.nanchong.gov.cn/hdjl/szxx/"]),
    ("眉山", ["https://www.ms.gov.cn/mail12345/swmail.jsp?urltype=tree.TreeTempUrl&wbtreeid=5999",
              "https://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010"]),
    ("宜宾", ["https://www.yibin.gov.cn/hdjl/szywm/wyxx/"]),
    ("达州", ["https://www.dazhou.gov.cn/news-list-hdjl.html"]),
    ("巴中", ["https://www.cnbz.gov.cn/zmhd/ldxx/szxx/index.html"]),
    ("阿坝州", ["https://www.abazhou.gov.cn/abazhou/c101014/hd_mailbox.shtml",
                "https://www.abazhou.gov.cn/abazhou/rexian/12345rx.shtml"]),
    ("甘孜州", ["https://www.gzz.gov.cn/hdjl"]),
    ("凉山州", ["https://www.lsz.gov.cn/hdjl/"]),
    ("广元", ["http://www.guangyuan.gov.cn/", "http://www.gy.gov.cn/",
              "https://www.gy.gov.cn/", "http://guangyuan.gov.cn/"]),
]

SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
FINGERPRINTS = [
    ("数融openMailList", "openMailList"), ("数融api/mail", "/api/mail"),
    ("ajaxUrl", "ajaxUrl"), ("config.js", "config.js"),
    ("IGI", "openGovmsgbox"), ("IGI-appId", "IGI/"),
    ("dataproxy_mailpublist", "dataproxy_mailpublist"),
    ("jpaas-jact", "jpaas-jact"), ("EWB", "EWB-FRONT"), ("ewb", "ewb"),
    ("9050szweb", "9050/szweb"), ("szweb", "szweb"),
    ("Hanweb", "hanweb"), ("TrueCMS", "truecms"), ("jsp-mail", "mail"),
    ("lsswszf", "lsswszf"), ("zmhd", "zmhd"),
]


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u):
    try:
        r = requests.get(u, timeout=25, allow_redirects=True, headers={"User-Agent": UA})
        return r
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    for name, urls in TARGETS:
        w(f"\n===== {name} =====")
        for u in urls:
            r = get(u)
            if not hasattr(r, "status_code"):
                w(f"  {u} -> ERR {r}")
                continue
            ct = r.headers.get("content-type", "")
            w(f"  {u} -> {r.status_code} len={len(r.text)} ct={ct[:40]} final={r.url}")
            if r.status_code != 200:
                continue
            txt = r.text
            # script srcs
            for m in SCRIPT_RE.finditer(txt):
                src = m.group(1)
                if any(k in src.lower() for k in ("config", "mail", "hdjl", "szxx", "zmhd", "list", "api", "common")):
                    w("     [js] " + src[:160])
            # fingerprints
            for label, needle in FINGERPRINTS:
                idx = txt.find(needle)
                if idx >= 0:
                    seg = re.sub(r"\s+", " ", txt[max(0, idx - 60):idx + 90])
                    w(f"     [{label}] ...{seg}...")
            # api endpoints in text
            for m in re.finditer(r'["\'](/?[A-Za-z0-9_\-/]*(?:openMailList|list|List|search|page|Page|detail|Detail)[A-Za-z0-9_\-/]*(?:\.do|\.json|\.html)?)["\']', txt):
                pass


if __name__ == "__main__":
    main()
