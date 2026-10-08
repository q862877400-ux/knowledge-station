"""stage20：南通 xxList.do 调用参数 + 南京 SPA 资源接口。"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})

    # ---------- 南通 xxList.do 调用上下文 ----------
    w("## 南通 sgkxj.html 内 xxList/toSeeLetterInfo 上下文")
    h = c.get("https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html", timeout=30).text
    for kw in ("xxList.do", "toSeeLetterInfo.do", "getMessageByCondition.do"):
        for m in re.finditer(re.escape(kw), h):
            s = max(0, m.start() - 350)
            w(f"--[{kw}]-- " + h[s:m.end() + 250].replace("\n", " "))
    # 页面里 data:{} / params 定义
    for m in re.finditer(r"\$\.(ajax|post|get)\(", h):
        s = max(0, m.start() - 60)
        w("AJAX ..." + h[s:m.start() + 500].replace("\n", " ")[:560])

    # ---------- 南通 直接试 xxList.do ----------
    w("\n## 南通 xxList.do 试参")
    base = "https://www.nantong.gov.cn/truecms/letterController/xxList.do"
    for params in ({}, {"pageNum": 1, "pageSize": 10}, {"page": 1, "rows": 10},
                   {"numPerPage": 10, "pageNum": 1}, {"currentPage": 1, "pageSize": 10}):
        try:
            rr = c.get(base, params=params, timeout=30)
            w(f"  {params} -> {rr.status_code} len={len(rr.text)} {rr.text[:120]!r}")
        except Exception as e:  # noqa: BLE001
            w(f"  {params} -> {type(e).__name__} {str(e)[:60]}")

    # ---------- 南京 SPA ----------
    w("\n## 南京 SPA")
    u = "https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx"
    try:
        rr = c.get(u, timeout=30)
        w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
        js = re.findall(r'(?:src|href)="([^"]+\.js)"', rr.text)
        w("  js=" + str(js))
        for j in js:
            ju = j if j.startswith("http") else "https://szxx.nanjing.gov.cn:32767" + (j if j.startswith("/") else "/" + j)
            try:
                jr = c.get(ju, timeout=30)
                w(f"  --- {ju} len={len(jr.text)}")
                for m in re.finditer(r'["\'](https?://[^"\']+|/[a-zA-Z][a-zA-Z0-9_/]*\.(?:do|json|action))["\']', jr.text):
                    w("     URL " + m.group(1)[:100])
                for m in re.finditer(r'(baseURL|process\.env|VUE_APP)', jr.text):
                    s = max(0, m.start() - 80)
                    w("     CFG ..." + jr.text[s:m.end() + 120].replace("\n", " "))
            except Exception as e:  # noqa: BLE001
                w(f"     {ju} -> {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        w(f"  {u} -> {type(e).__name__} {str(e)[:70]}")


if __name__ == "__main__":
    main()
