"""陇南：分页语义 + 列表答复 vs 详情答复 完整性对比。"""
from __future__ import annotations

import os
import re

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
TAG = re.compile(r"<[^>]+>")


def clean(h):
    return re.sub(r"\s+", " ", TAG.sub(" ", h or "")).strip()


def list_url(pi):
    return ("https://www.longnan.gov.cn/site/label/8888?labelName=messageBoardPageList"
            f"&pageIndex={pi}&pageSize=14&siteId=4448177&columnId=4450039"
            "&action=singleList&isJson=true")


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        cli.get("https://www.longnan.gov.cn/zmhd/szxx/index.html")
        seen = []
        for pi in (1, 2, 3):
            j = cli.get(list_url(pi)).json()
            page = j.get("page") or {}
            data = page.get("data") or []
            first = data[0].get("baseContentId") if data else None
            print(f"pageIndex={pi} -> 返回 pageIndex={page.get('pageIndex')} "
                  f"total={page.get('total')} 条数={len(data)} 首条bcid={first}")
            seen.append([x.get("baseContentId") for x in data])
        print("页1∩页2 =", len(set(seen[0]) & set(seen[1])))
        print("页2∩页3 =", len(set(seen[1]) & set(seen[2])))

        # 取前 4 条，比较列表答复 vs 详情答复
        j = cli.get(list_url(1)).json()
        for it in (j.get("page") or {}).get("data", [])[:4]:
            bcid = it.get("baseContentId")
            lst = " ".join(clean(x.get("replyContent")) for x in (it.get("replyVOList") or []))
            d = cli.get(f"https://www.longnan.gov.cn/content/article/{bcid}")
            # 详情页取「答复意见：」之后的正文
            text = re.sub(r"<script[\s\S]*?</script>", " ", d.text, flags=re.I)
            plain = clean(text)
            m = re.search(r"答复意见[:：]\s*(.*?)(?:中国政府网|省（区市）政府网站|网站地图)", plain)
            det = m.group(1).strip() if m else ""
            print(f"\nbcid={bcid}")
            print(f"  列表答复 len={len(lst)}: {lst[:100]}")
            print(f"  详情答复 len={len(det)}: {det[:100]}")
            print(f"  列表⊂详情? {lst[:60] in det}  详情⊂列表? {det[:60] in lst}")


if __name__ == "__main__":
    main()
