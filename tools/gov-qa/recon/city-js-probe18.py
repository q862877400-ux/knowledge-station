"""stage18：南通 getInteractiveJson 字段 + 常州 ajax.php(https) 列表结构 + 连云港重试。"""
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

    # ---------- 南通 ----------
    w("## 南通 getInteractiveJson")
    for sid in ("147d8e37-a461-4dbc-863d-0fa52d92bb44",
                "1f9dcfb8-d52d-46e6-83e7-479a46f2f74b"):
        for scheme in ("http", "https"):
            try:
                rr = c.get(f"{scheme}://www.nantong.gov.cn/truecms/visitorController/getInteractiveJson.do",
                           params={"numPerPage": 5, "siteId": sid}, timeout=30)
                try:
                    d = rr.json()
                except Exception:  # noqa: BLE001
                    w(f"  {scheme} siteId={sid} -> {rr.status_code} non-json len={len(rr.text)} "
                      f"{rr.text[:80]!r}")
                    continue
                cont = d.get("content") or {}
                lst = cont.get("list") or []
                w(f"  {scheme} siteId={sid} status={rr.status_code} n={len(lst)} "
                  f"contkeys={list(cont.keys())}")
                if lst:
                    w("  item keys=" + str(list(lst[0].keys())))
                    w("  item0=" + json.dumps(lst[0], ensure_ascii=False)[:700])
            except Exception as e:  # noqa: BLE001
                w(f"  {scheme} siteId={sid} -> {type(e).__name__} {str(e)[:70]}")

    # ---------- 常州 ----------
    w("\n## 常州 ajax.php（https）列表结构")
    for page in (1, 2):
        try:
            rr = c.get("https://www.changzhou.gov.cn/gova/letter/ajax.php",
                       params={"action": "list", "page": page},
                       headers={"Referer": "https://www.changzhou.gov.cn/"}, timeout=30)
            w(f"  page={page} status={rr.status_code} len={len(rr.text)}")
            w("  head=" + rr.text[:700].replace("\n", " "))
        except Exception as e:  # noqa: BLE001
            w(f"  page={page} -> {type(e).__name__} {str(e)[:70]}")

    # 常州：从页面找明细入口
    w("\n## 常州 letter 页面 URL")
    for u in ("https://www.changzhou.gov.cn/gova/letter/index.php",
              "https://www.changzhou.gov.cn/gova/letter/",
              "https://www.changzhou.gov.cn/gova/"):
        try:
            rr = c.get(u, timeout=30, allow_redirects=True)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
            for m in re.finditer(r"(ajax\.php|index\.php\?m=letter[^\"']*|show[^\"']*id=\d+)", rr.text):
                w("     " + m.group(0)[:120])
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:70]}")

    # ---------- 连云港 重试 ----------
    w("\n## 连云港 重试（http/https）")
    for scheme in ("http", "https"):
        try:
            rr = c.get(f"{scheme}://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do",
                       params={"pageNum": 1, "pageSize": 5}, timeout=30)
            w(f"  {scheme} -> {rr.status_code} len={len(rr.text)} {rr.text[:100]!r}")
        except Exception as e:  # noqa: BLE001
            w(f"  {scheme} -> {type(e).__name__} {str(e)[:70]}")


if __name__ == "__main__":
    main()
