"""找拉萨来信选登页面的 API 调用方式（`.do` 路径 404，需看真实调用）。"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}
B = "https://www.lasa.gov.cn"


def main() -> int:
    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        r = c.get(B + "/lasa/lxxd/hd_mailbox.shtml")
        t = r.text or ""
        print(f"页面 HTTP {r.status_code} len={len(t)}")

        # ① findDetailByQuery 的上下文
        i = t.find("findDetailByQuery")
        if i >= 0:
            print("\n--- findDetailByQuery 上下文 ---")
            print(re.sub(r"\s+", " ", t[max(0, i - 600):i + 400]))
        else:
            print("\n未找到 findDetailByQuery")

        # ② 所有 .do 引用
        dos = sorted(set(re.findall(r"[\"']([^\"']{4,90}\.do)[\"']", t)))
        print(f"\n所有 .do 引用（{len(dos)}）: {dos[:12]}")

        # ③ script src
        srcs = sorted(set(re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", t)))
        print(f"\nscript src（{len(srcs)}）: {srcs[:12]}")

        # ④ 页内 ajax / url 变量
        for m in re.finditer(r"(url\s*[:=]\s*[\"'][^\"']+[\"'])", t):
            print(f"  {m.group(1)[:120]}")

        # ⑤ 试抓一个 script 看有没有 API 封装
        for s in srcs[:4]:
            u = s if s.startswith("http") else B + ("/" + s.lstrip("/") if not s.startswith("/") else s)
            try:
                rr = c.get(u)
                body = rr.text or ""
                found = re.findall(r"[\"']([^\"']{6,90}\.do)[\"']", body)
                if found:
                    print(f"\n{s} 里找到 .do: {sorted(set(found))[:8]}")
            except Exception:                                           # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
