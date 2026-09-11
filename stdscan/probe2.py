# -*- coding: utf-8 -*-
"""第二轮：验证全文/按号查询/状态字段"""
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

def get(tag, url, headers=None, timeout=25):
    print(f"\n===== {tag} =====")
    print("REQ:", url)
    try:
        r = s.get(url, headers=headers, timeout=timeout, verify=False)
        print(f"HTTP {r.status_code} | CT: {r.headers.get('Content-Type','-')} | bytes: {len(r.content)} | final: {r.url}")
        fn = os.path.join(OUT, tag + ".bin")
        with open(fn, "wb") as f:
            f.write(r.content)
        if "json" in r.headers.get("Content-Type", "").lower():
            try:
                print("JSON head:", json.dumps(r.json(), ensure_ascii=False)[:600])
            except Exception as e:
                print("JSON parse err:", e)
        else:
            for enc in (r.apparent_encoding, "utf-8", "gbk", "gb18030"):
                try:
                    t = r.content.decode(enc, errors="replace")
                    break
                except Exception:
                    t = r.content.decode("utf-8", errors="replace")
            print("TEXT head:", re.sub(r"\s+", " ", t)[:700])
            return r, t
        return r, None
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return None, None

# c1: 验证 PDF 全文可直接下载（Range 限定 1KB 判 content-type）
r, _ = get("c1_pdf_probe",
           "https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/201506/P020190327398828566738.pdf",
           headers={"Range": "bytes=0-1023"})

# c2: 标准公告首页（废止/批准公告）
r2, t2 = get("c2_bzgg", "https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/")
if t2:
    print("bzgg hrefs:", re.findall(r'href="([^"]+)"[^>]*>\s*([^<]{4,60})', t2)[:14])

# c3: HJ 按标准号查询（datacenter 标准查询）
print("\n===== c3_hj_query =====")
url3 = "http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1520238134405"
try:
    r3 = s.post(url3, data={"doctitle": "HJ 819-2017"}, timeout=30, verify=False,
                headers={"Referer": "https://www.mee.gov.cn/ywgz/fgbz/bz/"})
    print(f"HTTP {r3.status_code} | CT: {r3.headers.get('Content-Type','-')} | bytes: {len(r3.content)} | final: {r3.url}")
    with open(os.path.join(OUT, "c3_hj_query.bin"), "wb") as f:
        f.write(r3.content)
    t3 = r3.content.decode(r3.apparent_encoding or "utf-8", errors="replace")
    t3c = re.sub(r"\s+", " ", t3)
    print("TEXT head:", t3c[:800])
    print("状态词命中:", re.findall(r".{0,15}(现行|废止|发布|实施日期|标准号).{0,15}", t3c)[:8])
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

# c4: JT 标准 JSON 搜索接口
r4, t4 = get("c4_std_api", "https://jtst.mot.gov.cn/search/std?q=JT%2FT%20823-2016")

# c5: 能源局 行业标准废止公告列表
r5, t5 = get("c5_fzgg", "http://www.nea.gov.cn/ztzl/nybz/bzgg/hybzfzgg/index.htm")
if t5:
    print("废止公告条目:", re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{4,80})</a>', t5)[:10])

# c6: 能源水电标准全文 列表查询（keywords + status）
r6, t6 = get("c6_list",
             "http://bz.creei.cn:8888/default/pub/list.jsp?eventtype=1&clztype=1&keywords=DL%2FT&status=1&madeunit=&submadeunit=&starttime=&endtime=&clzids=")
if t6:
    print("list条目:", re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{4,90})</a>', t6)[:12])
    print("状态词命中:", re.findall(r".{0,12}(现行|废止|有效|替代).{0,12}", t6)[:6])

print("\nDONE2")
