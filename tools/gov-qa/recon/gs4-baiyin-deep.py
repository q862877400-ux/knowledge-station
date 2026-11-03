"""甘肃白银接口深探：比较变体、dump 字段、确认分页语义。"""
from __future__ import annotations

import json
import os

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://www.baiyin.gov.cn/api-gateway/jpaas-jact-web-server/front"
PID = "dc0a47c54dce496a9cc6321fac5a973a"


def dump(cli, tag, url):
    r = cli.get(url, headers={"Referer": "https://www.baiyin.gov.cn/"})
    print(f"\n===== {tag} HTTP {r.status_code}")
    try:
        j = r.json()
    except Exception as e:
        print("  JSON FAIL", e, r.text[:200]); return
    print(f"  top keys: {list(j.keys())}")
    print(f"  count = {j.get('count')}")
    data = j.get("data") or []
    print(f"  data 长度 = {len(data)}")
    if data:
        print(f"  记录字段: {list(data[0].keys())}")
        for it in data[:3]:
            print(f"   - iid={it.get('iid')} title={it.get('title')!r} "
                  f"transactNo={it.get('transactNo')} platformName={it.get('platformName')!r} "
                  f"stateName={it.get('stateName')!r} submitDate={it.get('submitDate')} "
                  f"handleTime={it.get('handleTime')} showHandleTime={it.get('showHandleTime')}")
            print(f"     opinion={str(it.get('opinion'))[:120]!r}")
            print(f"     frontOpinion={str(it.get('frontOpinion'))[:120]!r}")
    return j


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        dump(cli, "A page=1 limit=10", f"{BASE}/find-mail-pub-list?platformIid={PID}&page=1&limit=10")
        dump(cli, "A page=2 limit=10", f"{BASE}/find-mail-pub-list?platformIid={PID}&page=2&limit=10")
        dump(cli, "B pageNum=1 pageSize=10", f"{BASE}/find-mail-pub-list?platformIid={PID}&pageNum=1&pageSize=10")
        dump(cli, "B pageNum=2 pageSize=10", f"{BASE}/find-mail-pub-list?platformIid={PID}&pageNum=2&pageSize=10")
        dump(cli, "C platformUid orderType=2", f"{BASE}/find-mail-pub-list?platformUid={PID}&pageNum=1&pageSize=10&orderType=2")


if __name__ == "__main__":
    main()
