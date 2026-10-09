"""查拉萨 `hd_mailbox.js` —— 确认有无公开的来信列表接口。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.lasa.gov.cn"
H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": B + "/lasa/lxxd/hd_mailbox.shtml",
}


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for js in ("/lasa/xhtml/js/hd_mailbox.js", "/lasa/xhtml/js/page.js"):
            try:
                r = c.get(B + js)
            except Exception as e:                                      # noqa: BLE001
                print(f"{js} FAIL {type(e).__name__}")
                continue
            t = r.text or ""
            print(f"\n{js}  HTTP {r.status_code} len={len(t)}")
            # 所有 URL / .do / ajax
            urls = sorted(set(re.findall(r"[\"']([^\"']{5,110}(?:\.do|/email/|/comment/)[^\"']*)[\"']", t)))
            print(f"  URL 线索: {urls[:12]}")
            ajax = sorted(set(re.findall(r"url\s*[:=]\s*[\"']([^\"']+)[\"']", t)))
            print(f"  ajax url: {ajax[:10]}")
            # 有没有「列表」相关函数名
            fns = sorted(set(re.findall(r"function\s+(\w{3,30})", t)))
            print(f"  函数名（前 14）: {fns[:14]}")
            # 关键中文
            for kw in ("选登", "列表", "公开", "查询码", "手机"):
                if kw in t:
                    i = t.find(kw)
                    print(f"  [{kw}] {re.sub(chr(92)+'s+', ' ', t[max(0, i-70):i+70])[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
