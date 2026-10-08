"""city-sc-probe32：雅安详情页原始 HTML 片段（信件内容/办理情况容器）+ 分页总数。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")
    uid = "ca423879-4d66-49ab-a12b-660d68fcd612"
    mid = "d42c4e11d56c50ad88cd6b9246b46d6d"

    w("===== 雅安 详情页 原始 HTML 中「信件内容」「办理情况」附近 =====")
    r = get(f"https://www.yaan.gov.cn/mail/view.html?id={uid}&mailid={mid}",
            ref=f"https://www.yaan.gov.cn/mail/mailbox.html?id={uid}")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for kw in ("信件内容", "办理情况", "信件标题", "写信时间", "回复日期", "class=\"reply\""):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"\n  [{kw}] @" + str(i) + " 原始:")
                w("    " + t[max(0, i - 120):i + 700].replace("\n", " "))
                break
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")

    w("\n===== 雅安 列表页 分页总数（laypage count/pages）=====")
    r = get(f"https://www.yaan.gov.cn/mail/mailbox.html?id={uid}",
            ref="https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for kw in ("count", "pages", "laypage", "gotoPage", "totalPage", "total"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + t[max(0, i - 150):i + 200].replace("\n", " ")[:350])
                break
        # 编号列（第一列）
        ids = re.findall(r">(\d{8})<", t)
        w("  形如 8 位编号: " + ", ".join(ids[:8]))

    w("\n===== 雅安 各部门 uuid 对应部门名 =====")
    r = get("https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for m in re.finditer(r'(?:title="([^"]{2,30})"[^>]*)?href="/mail/mailbox\.html\?id=([0-9a-fA-F\-]+)"', t):
            w(f"  {m.group(2)}  <-  {m.group(1)}")


if __name__ == "__main__":
    main()
