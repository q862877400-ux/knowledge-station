"""city-sc-probe7：攀枝花信箱列表接口 / 自贡zg.gov.cn / 绵阳my.gov.cn / 成都备域。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
KW = ("互动", "信箱", "12345", "热线", "留言", "诉求", "信访", "征集", "访谈", "问答", "咨询", "投诉", "建议")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(url, ref=None, **kw):
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if ref:
        c.headers["Referer"] = ref
    try:
        return c.get(url, timeout=25, allow_redirects=True, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def links(html):
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,40})</a>', html):
        txt = m.group(2).strip()
        if any(k in txt for k in KW):
            out.append((txt, m.group(1).strip()))
    return out


def main():
    OUT.write_text("", encoding="utf-8")

    # ---- 攀枝花 信箱页 完整 script ----
    w("## 攀枝花 /hdcy/szxx/szxx/index.shtml 全部 script src + 可见文本")
    r = get("http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml")
    if hasattr(r, "text"):
        t = r.text
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
            w("     SRC " + m.group(1))
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        txt = re.sub(r"<script[\s\S]*?</script>", " ", t)
        txt = re.sub(r"<style[\s\S]*?</style>", " ", txt)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        w("     VISIBLE=" + txt[:600])
        for m in re.finditer(r'(getAllSubOrgan|getMail|getLetter|mailbox/[a-zA-Z]+|listJson|ListJson)', t):
            w("     HIT " + m.group(0))

    # 攀枝花 试 mailbox 其他端点
    w("\n## 攀枝花 mailbox 端点穷举")
    for ep in ("/webapp/mailbox/getLetterList", "/webapp/mailbox/getMailboxLetters",
               "/webapp/mailbox/getAllMail", "/webapp/mailbox/getMailsByOrg",
               "/webapp/mailbox/getOrgMailList", "/webapp/mailbox/getLetters",
               "/webapp/mailbox/getLetter", "/webapp/mailbox/queryMail"):
        rr = get("http://www.panzhihua.gov.cn" + ep,
                 ref="http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                 params={"id": 2, "organId": 2, "pageIndex": 1, "pageSize": 5})
        if hasattr(rr, "text"):
            w(f"  {ep} -> {rr.status_code} len={len(rr.text)} {rr.text[:100]!r}")

    # ---- 自贡 zg.gov.cn ----
    w("\n## 自贡 www.zg.gov.cn 互动链接")
    r = get("https://www.zg.gov.cn/")
    if hasattr(r, "text"):
        for txt, href in links(r.text)[:40]:
            w(f"     [{txt}] {href}")
        if not links(r.text):
            w("     （无匹配，打印所有 nav a）")
            for m in list(re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,20})</a>', r.text))[:60]:
                w(f"     [{m.group(2).strip()}] {m.group(1)}")

    # ---- 绵阳 my.gov.cn ----
    w("\n## 绵阳 www.my.gov.cn 互动链接")
    r = get("https://www.my.gov.cn/")
    if hasattr(r, "text"):
        for txt, href in links(r.text)[:40]:
            w(f"     [{txt}] {href}")

    # ---- 成都备域 ----
    w("\n## 成都备域")
    for u in ("https://12345.chengdu.gov.cn/", "http://12345.chengdu.gov.cn/",
              "https://www.chengdu.gov.cn:443/", "https://cdzwfw.chengdu.gov.cn/"):
        rr = get(u)
        if hasattr(rr, "text"):
            ti = re.search(r"<title>([^<]*)</title>", rr.text)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)} title={ti.group(1)[:40] if ti else '?'}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__}")


if __name__ == "__main__":
    main()
