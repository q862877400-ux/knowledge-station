# -*- coding: utf-8 -*-
"""渠道时效巡检探测脚本：浏览器 UA 实测 7 个标准官方渠道。
每渠道 <=3 次请求。输出结构化证据。
"""
import re, sys, json, ssl, urllib3
import requests

urllib3.disable_warnings()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

CHANNELS = {
    "mohurd_standard_page": "https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_17339_770016.html",
    "mohurd_list_page": "https://www.mohurd.gov.cn/gongkai/zc/wgk/art/2024/art_004fc4271aae43bd90fe47449731f3c0.html",
    "govcn_policy": "https://www.gov.cn/zhengce/zhengceku/202504/content_7016620.htm",
    "ebook_chinabuilding": "https://ebook.chinabuilding.com.cn",
    "ttbz_detail": "https://www.ttbz.org.cn/standardDetail/g345tim3dknec1smd2t1k0bj7k49a65.html",
    "ttbz_home": "https://www.ttbz.org.cn",
    "qybz_home": "https://www.qybz.org.cn",
}

def probe(name, url, extra_headers=None, timeout=20):
    out = {"channel": name, "url": url, "requests": []}
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    try:
        r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True, verify=False)
        out["status"] = r.status_code
        out["final_url"] = r.url
        out["redirects"] = [(x.status_code, x.url) for x in r.history]
        out["content_type"] = r.headers.get("Content-Type", "")
        out["server"] = r.headers.get("Server", "")
        out["length"] = len(r.content)
        out["encoding"] = r.encoding
        text = r.text
        out["requests"].append({"status": r.status_code, "bytes": len(r.content)})

        # ---- 静态 HTML vs JS 壳判定 ----
        body_lower = text.lower()
        html_len = len(text)
        script_chars = sum(len(m) for m in re.findall(r"<script[^>]*>.*?</script>", text, re.S | re.I))
        style_chars = sum(len(m) for m in re.findall(r"<style[^>]*>.*?</style>", text, re.S | re.I))
        text_chars = len(re.sub(r"<[^>]+>", "", text))
        out["html_len"] = html_len
        out["script_chars"] = script_chars
        out["visible_text_chars"] = text_chars
        out["js_shell"] = text_chars < 200 and html_len > 1000

        # ---- title ----
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
        out["title"] = (m.group(1).strip()[:120] if m else "")

        # ---- 日期字段 ----
        dates = set()
        for pat in [r"20\d{2}[-/年\.]\d{1,2}[-/月\.]\d{1,2}",
                    r"20\d{2}[-/年]\d{1,2}",
                    r"发布[：:\s]*20\d{2}", r"实施[：:\s]*20\d{2}",
                    r"公布[：:\s]*20\d{2}", r"施行[：:\s]*20\d{2}",
                    r"现行[^<]{0,30}", r"废止[^<]{0,30}"]:
            for mm in re.findall(pat, text)[:8]:
                dates.add(mm.strip()[:60])
        out["date_matches"] = sorted(dates)[:15]

        # ---- 附件链接 ----
        links = []
        for href in re.findall(r'href=["\']([^"\']+)["\']', text, re.I):
            hl = href.lower()
            if re.search(r"\.(pdf|doc|docx|zip|rar|wps)(\?|#|$)", hl):
                links.append(href)
        out["attachment_links"] = links[:10]
        out["attachment_count"] = len(links)

        # ---- 登录 / 反爬标记 ----
        markers = []
        for kw in ["登录", "登陆", "验证码", "请先登录", "访问过于频繁", "拒绝访问",
                   "robot", "captcha", "waf", "access denied", "blocked",
                   "安全验证", "滑动验证", "人机验证", "webscan", "403 forbidden"]:
            if kw.lower() in body_lower:
                markers.append(kw)
        out["markers"] = markers

        # ---- 正文摘录（前 600 可见字符）----
        visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
        out["snippet"] = visible[:600]
        out["error"] = None
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        out["status"] = None
    return out

if __name__ == "__main__":
    results = {}
    for name, url in CHANNELS.items():
        results[name] = probe(name, url)
        r = results[name]
        print(f"\n=== {name} ===")
        print(f"  status={r.get('status')} final={r.get('final_url','')[:100]}")
        print(f"  ct={r.get('content_type','')} len={r.get('length')} title={r.get('title','')[:60]!r}")
        print(f"  error={r.get('error')}")
        if r.get("error") is None:
            print(f"  js_shell={r.get('js_shell')} visible_text={r.get('visible_text_chars')} attachments={r.get('attachment_count')}")
            print(f"  dates={r.get('date_matches')[:8]}")
            print(f"  markers={r.get('markers')}")
    with open("probe_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n[saved probe_results.json]")
