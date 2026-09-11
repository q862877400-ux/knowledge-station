# -*- coding: utf-8 -*-
"""第二轮定点取证：附件链接明细 / 日期上下文 / ebook 壳 / ttbz 字段 / 列表页结构。"""
import re, json, sys
import requests, urllib3
urllib3.disable_warnings()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
H = {"User-Agent": UA,
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}

def get(url, **kw):
    return requests.get(url, headers=H, timeout=20, verify=False, allow_redirects=True, **kw)

def visible(text):
    t = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)

# ---------- 1. mohurd 标准公告页：附件/日期上下文 ----------
r = get("https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_17339_770016.html")
r.encoding = r.apparent_encoding or "gbk"
text = r.text
print("== mohurd_standard_page (req2) ==")
print("  [链接]")
for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
    hl = href.lower()
    if re.search(r"\.(pdf|doc|docx|zip|rar|wps)", hl) or "attach" in hl or "download" in hl or "fujian" in hl:
        print("   ", href[:120])
print("  [附件/日期上下文]")
for m in re.finditer(r"附件|发布|实施", text):
    s = max(0, m.start() - 60)
    seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text[s:m.end() + 80])).strip()
    if len(seg) > 15:
        print("   ...", seg[:160])
print()

# ---------- 2. mohurd 文告列表页：列表结构 ----------
r = get("https://www.mohurd.gov.cn/gongkai/zc/wgk/art/2024/art_004fc4271aae43bd90fe47449731f3c0.html")
r.encoding = r.apparent_encoding or "gbk"
text = r.text
print("== mohurd_list_page (req2) ==")
items = re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.S | re.I)
print("  <a> 总数:", len(items))
for href, t in items[:12]:
    t2 = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()
    if t2:
        print(f"   a> {t2[:70]} -> {href[:80]}")
print()

# ---------- 4. ebook 壳 ----------
r = get("https://ebook.chinabuilding.com.cn")
print("== ebook_chinabuilding (req2) ==")
print("  raw html:", repr(r.text[:620]))
print()

# ---------- 5. ttbz 详情页：状态字段 ----------
r = get("https://www.ttbz.org.cn/standardDetail/g345tim3dknec1smd2t1k0bj7k49a65.html")
text = r.text
print("== ttbz_detail (req2) ==")
for kw in ["公布日期", "实施日期", "状态", "废止", "现行", "被替代", "采标号", "标准状态", "T/ZSA 328"]:
    for m in list(re.finditer(kw, visible(text)))[:4]:
        s = max(0, m.start() - 40)
        print(f"  [{kw}] ...{visible(text)[s:m.end() + 90]}...")
        break
print()

# ---------- 7. qybz：curl 降级 ----------
print("== qybz (req2/3 via curl.exe) ==")
