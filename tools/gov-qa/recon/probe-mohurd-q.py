"""探针：找出 nat-mohurd 列表页里 `Q_RE` 匹配失败的条目，看实际 HTML 结构。

只读，不落盘。用与 adapter 完全相同的 API 参数。
"""
import json
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

BASE = "https://www.mohurd.gov.cn"
API = BASE + "/api-gateway/jpaas-publish-server/front/page/build/unit"
REFERER = BASE + "/hudong/zwzx/index.html"
WEB_ID = "86ca573ec4df405db627fdc2493677f3"
TPL_SET_ID = "fc259c381af3496d85e61997ea7771cb"
PAGE_ID = "QydOZ61q6LsvHnuSdeecT"
TAG_ID = "内容列表"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

ITEM_SPLIT = re.compile(r'<div[^>]*class="[^"]*questionList-item[^"]*"[^>]*>', re.I)
Q_RE = re.compile(r'class="[^"]*question-title[^"]*"[^>]*>.*?</p>\s*<p>\s*<p[^>]*>(.*?)</p>',
                  re.S | re.I)


def fetch_page(c, page: int, size: int = 20):
    pj = json.dumps({"pageNo": page, "pageSize": size,
                     "loadEnabled": True, "search": "{}"}, ensure_ascii=False)
    r = c.get(API, params={"parseType": "bulidstatic", "webId": WEB_ID,
                           "tplSetId": TPL_SET_ID, "pageType": "column",
                           "tagId": TAG_ID, "editType": "null",
                           "pageId": PAGE_ID, "paramJson": pj},
              headers={"Referer": REFERER})
    if r.status_code != 200:
        return "", r.status_code
    return (r.json().get("data") or {}).get("html") or "", 200


def main() -> int:
    with httpx.Client(timeout=30, headers={"User-Agent": UA, "Referer": REFERER},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        total_ok = total_bad = 0
        shown = 0
        for page in (1, 2, 3, 5, 10, 31, 32):
            html, code = fetch_page(c, page)
            if code != 200:
                print(f"page {page}: HTTP {code}")
                continue
            parts = ITEM_SPLIT.split(html)[1:]
            ok = bad = 0
            for seg in parts:
                m = Q_RE.search(seg)
                if m and m.group(1).strip():
                    ok += 1
                else:
                    bad += 1
                    if shown < 2:
                        shown += 1
                        i = seg.find("question-title")
                        print(f"\n=== page {page} 匹配失败样本 ===")
                        print(seg[max(0, i - 120):i + 700] if i >= 0 else seg[:700])
            total_ok += ok
            total_bad += bad
            print(f"page {page}: 条目 {len(parts)}｜Q_RE 命中 {ok}｜失败 {bad}")
        print(f"\n合计：命中 {total_ok}｜失败 {total_bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
