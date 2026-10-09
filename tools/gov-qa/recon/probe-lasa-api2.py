"""提取拉萨 `hd_mailbox.js` 里 `mailList` 函数的完整 URL。"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.lasa.gov.cn"
H = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
     "Referer": B + "/lasa/lxxd/hd_mailbox.shtml"}


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        r = c.get(B + "/lasa/xhtml/js/hd_mailbox.js")
        t = r.text or ""
        print(f"js HTTP {r.status_code} len={len(t)}\n")

        # ① ipUrl 定义
        for m in re.finditer(r"(var\s+)?ipUrl\s*=\s*[^;]{0,200};", t):
            print(f"ipUrl 定义: {re.sub(chr(92)+'s+', ' ', m.group(0))[:220]}")

        # ② mailList 函数体
        i = t.find("function mailList")
        if i >= 0:
            print("\n--- mailList 函数体 ---")
            print(re.sub(r"\s+", " ", t[i:i + 900]))

        # ③ 所有字符串字面量里的 URL 片段
        print("\n--- 所有疑似接口 ---")
        for m in re.finditer(r"[\"']((?:https?:)?//[^\"']{8,120}|/[a-zA-Z0-9_\-/]{6,120}\.(?:do|json|action))[\"']", t):
            print(f"  {m.group(1)[:130]}")

        # ④ 关键变量
        for name in ("ipUrl", "detailUrl", "listUrl", "baseUrl"):
            for m in re.finditer(rf"{name}\s*[:=]\s*[\"']([^\"']+)[\"']", t):
                print(f"  {name} = {m.group(1)[:130]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
