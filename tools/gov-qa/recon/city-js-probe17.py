"""stage17：连云港明细定位 + 南通 getInteractiveJson 字段 + 常州列表接口。"""
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
    REF = {"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"}

    # ---------- 连云港：抓列表页 + 内联脚本，找明细入口 ----------
    w("## 连云港 gzcy.html 全部 TrueCMS url + letterView 上下文")
    try:
        h = c.get("http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html",
                  headers=REF, timeout=30).text
        for m in re.finditer(r"TrueCMS/[A-Za-z0-9_/\.]+", h):
            w("  URL " + m.group(0))
        for m in re.finditer(r"letterView|getLetterList|letterContent|mailBox", h):
            s = max(0, m.start() - 120)
            w("  CTX ..." + h[s:m.end() + 160].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        w(f"  ERR {type(e).__name__} {e}")

    # ---------- 连云港：拿一条 id，试各种明细端点 ----------
    w("\n## 连云港 明细端点穷举")
    try:
        r = c.get("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do",
                  params={"pageNum": 1, "pageSize": 5}, headers=REF, timeout=30)
        lst = (r.json().get("content") or {}).get("list") or []
        if lst:
            lid = lst[0]["id"]
            w(f"  sample id={lid} subject={lst[0].get('subject')}")
            for path, params in [
                ("/TrueCMS/mailBoxLetterController/letterView.do", {"id": lid}),
                ("/TrueCMS/mailBoxLetterController/getLetterDetail.do", {"id": lid}),
                ("/TrueCMS/mailBoxLetterController/getLetterDetail.do", {"letterId": lid}),
                ("/TrueCMS/visitorController/letterView.do", {"id": lid}),
                ("/TrueCMS/mailBoxLetterController/getLetterContent.do", {"id": lid}),
                ("/TrueCMS/mailBoxLetterController/getLetter.do", {"id": lid}),
            ]:
                try:
                    rr = c.get("http://www.lyg.gov.cn" + path, params=params,
                               headers=REF, timeout=30)
                    w(f"  {path} {params} -> {rr.status_code} len={len(rr.text)} "
                      f"{rr.text[:120]!r}")
                except Exception as e:  # noqa: BLE001
                    w(f"  {path} {params} -> {type(e).__name__} {str(e)[:60]}")
    except Exception as e:  # noqa: BLE001
        w(f"  ERR {type(e).__name__} {e}")

    # ---------- 南通：getInteractiveJson 字段 ----------
    w("\n## 南通 getInteractiveJson")
    for sid in ("147d8e37-a461-4dbc-863d-0fa52d92bb44",
                "1f9dcfb8-d52d-46e6-83e7-479a46f2f74b",
                "1676b69c-9162-447f-a555-718bbe87cec4"):
        try:
            rr = c.get("http://www.nantong.gov.cn/truecms/visitorController/getInteractiveJson.do",
                       params={"numPerPage": 5, "siteId": sid},
                       headers={"Referer": "http://www.nantong.gov.cn/"}, timeout=30)
            d = rr.json()
            cont = d.get("content") or {}
            lst = cont.get("list") or []
            w(f"  siteId={sid} status={rr.status_code} n={len(lst)} "
              f"contkeys={list(cont.keys())}")
            if lst:
                w("  item keys=" + str(list(lst[0].keys())))
                w("  item0=" + json.dumps(lst[0], ensure_ascii=False)[:600])
        except Exception as e:  # noqa: BLE001
            w(f"  siteId={sid} -> {type(e).__name__} {str(e)[:80]}")

    # ---------- 常州：列表接口 ----------
    w("\n## 常州 gova/letter/ajax.php")
    for url, params in [
        ("http://www.changzhou.gov.cn/gova/letter/ajax.php", {"action": "list", "page": 1}),
        ("http://www.changzhou.gov.cn/gova/letter/ajax.php", {"action": "list", "page": 2}),
    ]:
        try:
            rr = c.get(url, params=params, headers={"Referer": "http://www.changzhou.gov.cn/"},
                       timeout=30)
            w(f"  {params} -> {rr.status_code} len={len(rr.text)} ctype={rr.headers.get('content-type')}")
            w("  head=" + rr.text[:400].replace("\n", " "))
        except Exception as e:  # noqa: BLE001
            w(f"  {params} -> {type(e).__name__} {str(e)[:80]}")


if __name__ == "__main__":
    main()
