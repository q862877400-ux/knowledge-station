# -*- coding: utf-8 -*-
"""第三轮：附件直连实测 / ebook SPA / ttbz 查询入口。"""
import re
import requests, urllib3
urllib3.disable_warnings()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
H = {"User-Agent": UA,
     "Accept": "*/*",
     "Accept-Language": "zh-CN,zh;q=0.9"}

def probe_download(url, label):
    print(f"== {label} (直连测试) ==")
    try:
        with requests.get(url, headers=H, timeout=25, verify=False, stream=True, allow_redirects=True) as r:
            ct = r.headers.get("Content-Type", "")
            cd = r.headers.get("Content-Disposition", "")
            cl = r.headers.get("Content-Length", "?")
            first = next(r.iter_content(64), b"")
            print(f"  status={r.status_code} final={r.url[:110]}")
            print(f"  ct={ct} cd={cd[:80]} len={cl}")
            print(f"  head_bytes={first[:32]!r}")
            # 是否登录墙
            print(f"  login_redirect={('login' in r.url.lower()) or ('login' in cd.lower())}")
    except Exception as e:
        print(f"  ERROR {type(e).__name__}: {e}")
    print()

# 1) mohurd 附件 api-gateway（req3）
probe_download(
    "https://www.mohurd.gov.cn/api-gateway/jpaas-web-server/front/document/download?fileUrl=YW5UzzlvCwcM%2FNHHX%2FtT6BJ6yM%2FAU1LVtmOVIvNjcuqxaLMLAlBp",
    "mohurd_standard_page req3")

# 2) ebook 真实应用页（req3）
try:
    r = requests.get("https://ebook.chinabuilding.com.cn/zbooklib/index?SiteID=1",
                     headers=H, timeout=25, verify=False, allow_redirects=True)
    print("== ebook /zbooklib/index (req3) ==")
    print(f"  status={r.status_code} final={r.url[:100]} len={len(r.content)}")
    text = r.text
    vis = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)))
    print(f"  visible_chars={len(vis)}")
    print(f"  title={re.search(r'<title[^>]*>(.*?)</title>', text, re.S | re.I).group(1)[:60] if re.search(r'<title[^>]*>(.*?)</title>', text, re.S | re.I) else ''}")
    print(f"  login_markers={[k for k in ['登录','注册','登录框','账号','密码','token','login'] if k in text.lower()][:6]}")
    print(f"  snippet={vis[:200]}")
except Exception as e:
    print(f"== ebook /zbooklib/index ERROR: {type(e).__name__}: {e}")
print()

# 3) ttbz 首页查询入口（req2）
try:
    r = requests.get("https://www.ttbz.org.cn", headers=H, timeout=25, verify=False)
    text = r.text
    print("== ttbz_home (req2: 查询入口) ==")
    for kw in ["标准查询", "搜索", "查询", "搜标准", "search", "keyword"]:
        idxs = [m.start() for m in re.finditer(kw, text, re.I)][:3]
        for i in idxs:
            seg = text[max(0, i - 120):i + 120]
            seg = re.sub(r"\s+", " ", seg)
            print(f"  [{kw}] ...{seg[:220]}...")
            break
    forms = re.findall(r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>', text, re.I)
    print(f"  forms_actions={forms[:6]}")
    print(f"  search_inputs={len(re.findall(r'<input[^>]*(?:search|keyword|标准)[^>]*>', text, re.I))}")
except Exception as e:
    print(f"== ttbz_home ERROR: {type(e).__name__}: {e}")
print()

# 4) gov.cn PDF 附件直连（req2）
probe_download(
    "https://www.gov.cn/zhengce/zhengceku/202504/P020250401157366903671.pdf",
    "govcn_policy req2")

# 5) ttbz 发布公告 PDF 直连（req3）
probe_download(
    "https://www.ttbz.org.cn/UploadFiles/StandardFpdFile/20260313134422484.pdf",
    "ttbz_detail req3")
