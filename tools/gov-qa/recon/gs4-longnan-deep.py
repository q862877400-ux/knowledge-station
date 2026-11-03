"""陇南深探：列表 JSON 结构 + 详情页结构。"""
from __future__ import annotations

import json
import os
import re

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
LIST = ("https://www.longnan.gov.cn/site/label/8888?labelName=messageBoardPageList"
        "&pageIndex=1&pageSize=14&siteId=4448177&columnId=4450039&action=singleList&isJson=true")


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        idx = cli.get("https://www.longnan.gov.cn/zmhd/szxx/index.html")
        print("index HTTP", idx.status_code, "cookies", dict(cli.cookies))
        r = cli.get(LIST, headers={"Referer": "https://www.longnan.gov.cn/zmhd/szxx/index.html"})
        j = r.json()
        print("top keys:", list(j.keys()))
        page = j.get("page") or {}
        print("page keys:", list(page.keys()))
        print("total =", page.get("total"), "pageIndex", page.get("pageIndex"),
              "pageSize", page.get("pageSize"), "totalPage", page.get("totalPage"))
        data = page.get("data") or []
        print("data 长度 =", len(data))
        if data:
            it = data[0]
            print("记录字段:", list(it.keys()))
            print("  baseContentId", it.get("baseContentId"), "id", it.get("id"),
                  "dealStatus", it.get("dealStatus"), "className", it.get("className"))
            print("  addDate", it.get("addDate"), "publishDate", it.get("publishDate"),
                  "replyDate", it.get("replyDate"))
            rvl = it.get("replyVOList") or []
            print("  replyVOList 长度", len(rvl))
            if rvl:
                print("  replyVO[0] 字段:", list(rvl[0].keys()))
                print("  replyContent:", str(rvl[0].get("replyContent"))[:200])
            # 详情页
            bcid = it.get("baseContentId")
            d = cli.get(f"https://www.longnan.gov.cn/content/article/{bcid}",
                        headers={"Referer": "https://www.longnan.gov.cn/zmhd/szxx/index.html"})
            print("\n详情 HTTP", d.status_code, "len", len(d.text))
            open("tools/gov-qa/recon/gs4-longnan-detail.html", "w", encoding="utf-8").write(d.text)
            text = re.sub(r"<script[\s\S]*?</script>", " ", d.text, flags=re.I)
            plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
            print("--- 详情去标签（前 1500）---")
            print(plain[:1500])


if __name__ == "__main__":
    main()
