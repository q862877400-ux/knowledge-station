"""看天水详情页的**原始 HTML**，找正文在哪（可能 JS 加载）。"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

B = "https://www.tianshui.gov.cn"
DETAIL = (B + "/zmhd/xj_info.jsp?urltype=leadermail.LeaderMailContentUrl"
          "&wbtreeid=1061&leadermailid=141AE5B40D694F6AADF59BF78C28DDD1")
H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": B + "/zmhd.jsp?urltype=tree.TreeTempUrl&wbtreeid=1061",
}


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        r = c.get(DETAIL)
        t = r.text or ""
        print(f"HTTP {r.status_code} len={len(t)}")

        # ① 找含中文的 div/td（正文容器）
        print("\n--- 含中文长度 >30 的标签块（前 8）---")
        n = 0
        for m in re.finditer(r"<(div|td|p|span)[^>]*>(.*?)</\1>", t, re.S):
            inner = re.sub(r"<[^>]+>", "", m.group(2))
            inner = re.sub(r"\s+", " ", inner).strip()
            if len(inner) > 30 and re.search(r"[\u4e00-\u9fa5]", inner):
                cls = re.search(r'class="([^"]*)"', m.group(0))
                print(f"  <{m.group(1)} class={cls.group(1) if cls else '-'}> {inner[:110]}")
                n += 1
                if n >= 8:
                    break

        # ② 找 AJAX / API
        print("\n--- 接口线索 ---")
        for pat in (r"url\s*[:=]\s*[\"']([^\"']+)[\"']",
                    r"\$\.(?:get|post|ajax)\s*\(\s*[\"']([^\"']+)[\"']",
                    r"[\"'](/[a-zA-Z0-9_\-/]{6,90}\.(?:jsp|do|action))[\"']"):
            hits = sorted(set(re.findall(pat, t)))[:8]
            if hits:
                print(f"  {pat[:30]}: {hits}")

        # ③ 找 leadermailid 相关变量
        for m in re.finditer(r"leadermailid[^,;]{0,120}", t):
            print(f"  {m.group(0)[:130]}")
            break

        # ④ 找 script src
        srcs = sorted(set(re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", t)))
        print(f"\n  script src: {srcs[:8]}")

        # ⑤ 直接看 body 里最长的中文段
        print("\n--- 全文最长中文片段 ---")
        plain = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain)
        segs = [s.strip() for s in re.split(r"[。！？\n]", plain) if len(s.strip()) > 25]
        segs.sort(key=len, reverse=True)
        for s in segs[:5]:
            print(f"  ({len(s)}字) {s[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
