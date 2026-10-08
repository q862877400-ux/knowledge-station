"""city-sc-probe30：乐山详情复核 + 凉山12345信件选登 + 雅安 mail 列表 API。"""
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


def get(u, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 乐山 信件选登 详情正文 =====")
    r = get("https://www.leshan.gov.cn/lsswszf/xlxxx/854517350903898.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = re.sub(r"(?s)<script.*?</script>", " ", r.text)
        t = re.sub(r"(?s)<style.*?</style>", " ", t)
        # 找正文容器
        for cls in ("article", "content", "xlxxx", "detail", "con", "zw"):
            for m in re.finditer(r'class="[^"]*' + cls + r'[^"]*"[^>]*>(.{0,1200})', t, re.S):
                seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))
                if len(seg.strip()) > 60:
                    w(f"  [{cls}] " + seg[:400])
                    break
        w("  全文前 400: " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:400])

    w("\n===== 凉山 12345 信件选登 链接 =====")
    r = get("http://12345.lsz.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', r.text):
            h = m.group(1)
            if any(k in h for k in ("notice", "xjxd", "letter", "mail", "xj")):
                w("  H " + h[:130])
        for kw in ("信件选登", "暂时还没有数据"):
            i = r.text.find(kw)
            if i > 0:
                w(f"  [{kw}] " + re.sub(r"\s+", " ", r.text[max(0, i - 200):i + 200]))
    # 试 信件选登 页面
    for u in ["http://12345.lsz.gov.cn/notice/xjxd/index.html",
              "http://12345.lsz.gov.cn/notice/letter/index.html",
              "http://12345.lsz.gov.cn/letter/index.html"]:
        rr = get(u, ref="http://12345.lsz.gov.cn/")
        if hasattr(rr, "status_code"):
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")

    w("\n===== 雅安 mail.js 全文（找列表接口）=====")
    r = get("https://www.yaan.gov.cn/mail/v2/js/mail.js")
    if hasattr(r, "status_code") and r.status_code == 200:
        w("  " + re.sub(r"\s+", " ", r.text)[:1500])
    w("\n===== 雅安 mail 页 列表容器 =====")
    r = get("https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        for m in re.finditer(r'(?s)<(ul|div)[^>]*(?:emailList|mail_list|letter_list|id="list)[^>]*>(.{0,800})', r.text):
            w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0)))[:300])
        for kw in ("/mail/", "ajax", "url:"):
            for m in re.finditer(re.escape(kw), r.text):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", r.text[max(0, i - 80):i + 160])[:240])
                break


if __name__ == "__main__":
    main()
