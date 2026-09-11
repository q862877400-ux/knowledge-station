# -*- coding: utf-8 -*-
"""部委行业标准官方渠道探测：状态码 / 按号查询能力 / 状态字段 / 全文 / 反爬特征"""
import os, re, sys, json
import requests, urllib3
urllib3.disable_warnings()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
OUT = r"D:\AI\work space\zcode\stdscan"
os.makedirs(OUT, exist_ok=True)

s = requests.Session()
s.headers.update({
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
})

ANTI_MARK = ["验证码", "captcha", "安全验证", "滑动验证", "人机验证", "JSChallenge",
             "challenge", "waf", "WAF", "拦截", "访问过于频繁", "cf-chl", "ReCAPTCHA"]
JS_MARK = ["createApp", "new Vue", "webpackJsonp", "__NUXT__", "angular", "ReactDOM",
           "id=\"app\"", "window.__", "vite", "reactRoot", "echarts", "seajs", "requirejs"]

def probe(tag, url, headers=None, timeout=20, redirects=True, method="GET", data=None):
    print(f"\n===== {tag} =====")
    print("REQ:", method, url)
    try:
        kw = dict(headers=headers, timeout=timeout, allow_redirects=redirects, verify=False)
        if method == "GET":
            r = s.get(url, **kw)
        else:
            r = s.post(url, data=data, **kw)
        body = r.content
        ct = r.headers.get("Content-Type", "")
        print(f"HTTP {r.status_code} | final: {r.url}")
        print(f"CT: {ct} | enc(declared): {r.encoding} | apparent: {r.apparent_encoding} | bytes: {len(body)}")
        print(f"Server: {r.headers.get('Server','-')} | Via: {r.headers.get('Via','-')} | X-Pw: {r.headers.get('X-Powered-By','-')} | Set-Cookie: {'yes' if r.headers.get('Set-Cookie') else 'no'}")
        fn = os.path.join(OUT, tag + ".html")
        with open(fn, "wb") as f:
            f.write(body)
        text = None
        for enc in (r.apparent_encoding, "utf-8", "gbk", "gb18030"):
            try:
                text = body.decode(enc, errors="replace")
                break
            except Exception:
                continue
        if text is None:
            text = body.decode("utf-8", errors="replace")
        # 精简文本做特征匹配
        mini = re.sub(r"\s+", " ", text)[:40000]
        hit_anti = [m for m in ANTI_MARK if m.lower() in mini.lower()]
        hit_js = [m for m in JS_MARK if m.lower() in mini.lower()]
        has_form = bool(re.search(r"<form[\s>]", text, re.I))
        inputs = re.findall(r"<input[^>]*>", text, re.I)[:6]
        print(f"anti-mark: {hit_anti if hit_anti else '-'} | js-shell marks: {hit_js if hit_js else '-'} | <form>: {has_form}")
        print(f"inputs: {[i[:110] for i in inputs] if inputs else '-'}")
        print(f"title: {re.search(r'<title[^>]*>(.*?)</title>', text, re.I|re.S).group(1).strip()[:100] if re.search(r'<title[^>]*>(.*?)</title>', text, re.I|re.S) else '-'}")
        return r, text
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return None, None

def hrefs(text, pat=None):
    out = []
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', text):
        u = m.group(1)
        if pat and not re.search(pat, u, re.I):
            continue
        out.append(u)
    return out

# ================= Channel 1: 应急管理部 AQ 标准文本栏目 =================
r1, t1 = probe("c1_aq_list", "https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/index_11.shtml")
if t1:
    pdf = hrefs(t1, r"\.pdf")[:8]
    print("PDF links found:", pdf if pdf else "-")
    aq = hrefs(t1, r"(?i)aq")[:12]
    print("AQ-ish hrefs:", aq if aq else "-")
    allh = hrefs(t1)[:30]
    print("sample hrefs:", allh if allh else "-")

# ================= Channel 2: 应急管理部 公告 =================
r2, t2 = probe("c2_mem_notice", "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/")
if t2:
    links = hrefs(t2, r"(?i)(gg|announce|tzgg|zfxxgk)")[:15]
    print("announce-ish hrefs:", links if links else "-")
    print("废止/批准 mentions:", re.findall(r".{0,25}(废止|批准|现行|实施).{0,25}", t2)[:6] if re.search(r"废止|批准", t2) else "-")

# ================= Channel 3: 生态环境部 HJ 标准 =================
r3, t3 = probe("c3_mee_bz", "https://www.mee.gov.cn/ywgz/fgbz/bz/")
if t3:
    q = hrefs(t3, r"(?i)(query|search|chaxun|cx|bzwb|hjbz)")[:15]
    print("query-ish hrefs:", q if q else "-")
    print("标准相关 hrefs:", hrefs(t3, r"(?i)(hj|标准|bzwb)")[:15])

# ================= Channel 4: 交通运输部 JT 标准信息系统 =================
r4, t4 = probe("c4_jtst_main", "https://jtst.mot.gov.cn/")
if t4:
    print("jtst sample hrefs:", hrefs(t4)[:20])
    forms = re.findall(r"<form[^>]*>", t4, re.I)[:5]
    print("forms:", forms if forms else "-")

# ================= Channel 5: 能源局 能源标准专题 =================
r5, t5 = probe("c5_nea_bz", "http://www.nea.gov.cn/ztzl/nybz/")
if t5:
    print("nea hrefs:", hrefs(t5)[:25])
    print("废止/批准 mentions:", re.findall(r".{0,25}(废止|批准).{0,25}", t5)[:5] if re.search(r"废止|批准", t5) else "-")

# ================= Channel 6: 能源水电标准全文 =================
r6, t6 = probe("c6_creei_main", "http://bz.creei.cn:8888/default/pub/indexnew.jsp")
if t6:
    print("creei hrefs:", hrefs(t6)[:20])
    forms = re.findall(r"<form[^>]*>", t6, re.I)[:5]
    print("forms:", forms if forms else "-")
    print("废止/现行 mentions:", re.findall(r".{0,20}(废止|现行|替代).{0,20}", t6)[:5] if re.search(r"废止|现行|替代", t6) else "-")

print("\nDONE")
