"""city-sc-probe23：乐山/宜宾/阿坝/广元/凉山 深挖（JS 常量 + 入口页结构）。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


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


def dump_js(name, u, kws):
    w(f"\n===== {name} {u} =====")
    r = get(u)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    w(f"  -> {r.status_code} len={len(r.text)}")
    if r.status_code != 200:
        return
    t = r.text
    for kw in kws:
        for m in re.finditer(kw, t):
            i = m.start()
            w(f"     [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 130):i + 180])[:320])
            break


def dump_html_hrefs(name, u, kwset):
    w(f"\n===== {name} {u} =====")
    r = get(u)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    w(f"  -> {r.status_code} len={len(r.text)}")
    if r.status_code != 200:
        return
    t = r.text
    seen = set()
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
        h = m.group(1).strip()
        if h in seen:
            continue
        if any(k in h.lower() for k in kwset):
            seen.add(h)
            w("     " + h[:150])


def main():
    OUT.write_text("", encoding="utf-8")
    dump_js("乐山-hdjl.js", "https://www.leshan.gov.cn/lsswszf/resource/js/hdjl.js",
            ["ajax", "url:", "url =", "/front/", "page", "list", "box"])
    dump_js("宜宾-interaction.js", "https://www.yibin.gov.cn/images/v2024-interaction.js",
            ["ajax", "url", "mail", "letter", "list", "page", "fsp"])
    dump_js("阿坝-abzlxxd.js", "https://www.abazhou.gov.cn/abazhou/xhtml/abzrmzf/pc2025/js/abzlxxd.js",
            ["ajax", "url", "mail", "list", "page"])
    dump_js("凉山-notice.js", "http://12345.lsz.gov.cn/notice/template/notice.js",
            ["ajax", "url", "list", "page", "api"])
    dump_html_hrefs("广元-首页", "https://www.gy.gov.cn/", ("hdjl", "zmhd", "szxx", "mail", "letter", "xfj", "12345", "hd", "zx"))
    dump_html_hrefs("乐山-zmhd", "https://www.leshan.gov.cn/lsswszf/zmhd/index.html", ("mail", "letter", "hdjl", "szxx", "zmhd", "front", "wyxx"))


if __name__ == "__main__":
    main()
