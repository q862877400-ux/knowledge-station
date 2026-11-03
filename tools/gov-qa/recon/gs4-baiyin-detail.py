"""白银详情页实测：抓一条 iid 看问答结构。"""
from __future__ import annotations

import os
import re

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://www.baiyin.gov.cn/api-gateway/jpaas-jact-web-server/front"
IID = "dfde7ca9463f48d9ad73226029f4e36c"


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        r = cli.get(f"{BASE}/mail-pub-detail?iid={IID}",
                    headers={"Referer": "https://www.baiyin.gov.cn/"})
        print("HTTP", r.status_code, "len", len(r.text))
        print("content-type:", r.headers.get("content-type"))
        body = r.text
        # 存原文件供后续解析参考
        open("tools/gov-qa/recon/gs4-baiyin-detail.html", "w", encoding="utf-8").write(body)
        # 打印所有标签文本，看问答结构
        text = re.sub(r"<script[\s\S]*?</script>", " ", body, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", text, re.I)
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        print("\n--- 去标签全文（前 2000） ---")
        print(plain[:2000])
        print("\n--- <td> 文本（前 40 个） ---")
        for i, c in enumerate(cells[:40]):
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            if t:
                print(f"  [{i}] {t[:160]}")


if __name__ == "__main__":
    main()
