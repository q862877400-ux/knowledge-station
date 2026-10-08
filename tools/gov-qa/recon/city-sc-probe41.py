"""city-sc-probe41：眉山详情页原始 HTML 片段（标题/诉求/办理结果容器）。"""
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


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    ref = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    g = "c592f5c1-26f5-416b-9daa-2677c2eaad2c"
    u = ("http://www.ms.gov.cn/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl"
         f"&wbtreeid=7433&guid={g}")
    r = s.get(u, timeout=25, headers={"Referer": ref})
    t = dec(r)
    w(f"detail len={len(t)}")
    for kw in ("标题", "反映诉求", "办理结果", "承办部门", "回复时间", "编号"):
        for m in re.finditer(re.escape(kw), t):
            i = m.start()
            w(f"\n  [{kw}] @" + str(i))
            w("    " + re.sub(r"\s+", " ", t[max(0, i - 150):i + 500]))
            break

    w("\n===== 眉山 列表页原始行（do_detail 附近）=====")
    r = s.get(ref, timeout=25)
    t = dec(r)
    for m in re.finditer(r"do_detail\(", t):
        i = m.start()
        w("  " + re.sub(r"\s+", " ", t[max(0, i - 200):i + 400]))
        break


if __name__ == "__main__":
    main()
