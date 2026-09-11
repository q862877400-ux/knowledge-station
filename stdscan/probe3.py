# -*- coding: utf-8 -*-
"""第三轮：c2 废止公告详情 / c4 会话预热+搜索API / c5 废止公告列表"""
import os, re, json
import requests, urllib3
urllib3.disable_warnings()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = r"D:\AI\work space\zcode\stdscan"
s = requests.Session()
s.headers.update({"User-Agent": UA,
                  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                  "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})

def show(tag, r, dec="utf-8"):
    print(f"HTTP {r.status_code} | CT: {r.headers.get('Content-Type','-')} | bytes: {len(r.content)} | final: {r.url}")
    fn = os.path.join(OUT, tag + ".bin")
    with open(fn, "wb") as f:
        f.write(r.content)
    try:
        t = r.content.decode(r.apparent_encoding or dec, errors="replace")
    except Exception:
        t = r.content.decode("utf-8", errors="replace")
    return t

# ---- c2: 废止公告详情（2025年第10号 废止3项行业标准）----
print("===== c2_detail 废止公告 =====")
try:
    r = s.get("https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/202601/t20260104_590747.shtml",
              timeout=25, verify=False)
    t = show("c2_detail", r)
    tc = re.sub(r"\s+", " ", t)
    print("标题:", re.search(r'<title[^>]*>(.*?)</title>', t, re.I | re.S).group(1)[:80] if re.search(r'<title[^>]*>(.*?)</title>', t, re.I | re.S) else "-")
    body = re.sub(r"<[^>]+>", " ", t)
    body = re.sub(r"\s+", " ", body)
    i = body.find("废止")
    print("正文(废止段):", body[max(0, i - 20): i + 300] if i >= 0 else body[:300])
    print("标准号命中:", re.findall(r"(AQ\s?\d{3,5}(?:-\d{4})?)", body)[:10])
except Exception as e:
    print("ERROR:", type(e).__name__, e)

# ---- c4: 预热 + 搜索API ----
print("\n===== c4_warmup =====")
try:
    r = s.get("https://jtst.mot.gov.cn/", timeout=25, verify=False)
    print(f"HTTP {r.status_code} | cookies: {dict(s.cookies)} | bytes: {len(r.content)}")
except Exception as e:
    print("ERROR:", type(e).__name__, e)

print("\n===== c4_std_api (带会话) =====")
try:
    r = s.get("https://jtst.mot.gov.cn/search/std?q=JT%2FT%20823-2016",
              headers={"Referer": "https://jtst.mot.gov.cn/",
                       "X-Requested-With": "XMLHttpRequest",
                       "Accept": "application/json, text/javascript, */*; q=0.01"},
              timeout=25, verify=False)
    t = show("c4_std_api2", r)
    if "json" in r.headers.get("Content-Type", "").lower():
        try:
            j = r.json()
            print("JSON keys:", list(j.keys()) if isinstance(j, dict) else type(j).__name__)
            print("JSON head:", json.dumps(j, ensure_ascii=False)[:700])
        except Exception:
            print("raw:", t[:700])
    else:
        print("body:", re.sub(r"\s+", " ", t)[:700])
except Exception as e:
    print("ERROR:", type(e).__name__, e)

# ---- c5: 行业标准废止公告（.htm 单页）----
print("\n===== c5_fzgg_htm =====")
try:
    r = s.get("http://www.nea.gov.cn/ztzl/nybz/bzgg/hybzfzgg.htm", timeout=25, verify=False)
    t = show("c5_fzgg_htm", r)
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*([^<]{4,80})', t)
    print("废止公告条目:", [(u, re.sub(r"\s+", " ", x)) for u, x in links if "htm" in u or "公告" in x][:12])
    print("日期命中:", re.findall(r"\d{4}-\d{2}-\d{2}", t)[:6])
except Exception as e:
    print("ERROR:", type(e).__name__, e)

print("\nDONE3")
