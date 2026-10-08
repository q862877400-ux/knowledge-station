"""city-sc-probe37：达州 /xinxiang/ 内容；眉山 list_ldxx.jsp 表单+行结构。"""
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


def get(u, ref=None, **kw):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=25, allow_redirects=True, headers=h, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def post(u, data=None, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.post(u, data=data, timeout=25, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 达州 市长信箱 /xinxiang/ 全文（去标签）=====")
    r = get("https://www.dazhou.gov.cn/xinxiang/", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:900])
        w("  --- 链接 ---")
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1)
            if any(k in h for k in ("xinxiang", "mail", "letter", "detail", "list", "show", "index.php")):
                w("  H " + h[:140])
        w("  --- AJAX ---")
        for m in re.finditer(r"(\.ajax|url\s*:|/index\.php)", t):
            i = m.start()
            w(f"  [{m.group(1)}] " + re.sub(r"\s+", " ", t[max(0, i - 60):i + 240])[:300])

    w("\n===== 眉山 list_ldxx.jsp 表单字段 + 行结构 =====")
    u = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    r = get(u, ref="http://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        # 表单
        m = re.search(r"(?s)<FORM[^>]*leadermailform245916.*?</FORM>", t)
        if m:
            w("  [form head] " + re.sub(r"\s+", " ", m.group(0)[:400]))
            for inp in re.finditer(r"<INPUT[^>]*>", m.group(0), re.I):
                w("  INPUT " + re.sub(r"\s+", " ", inp.group(0))[:200])
        # 行（do_detail）
        w("  --- 行结构（do_detail 附近）---")
        for m in re.finditer(r"do_detail\(([^)]*)\)", t):
            i = m.start()
            w("  ROW " + re.sub(r"\s+", " ", t[max(0, i - 500):i + 120])[:600])
            break
        cnt = len(re.findall(r"do_detail\(", t))
        w(f"  do_detail 出现次数：{cnt}")
        # 所有 guid
        guids = re.findall(r"do_detail\('([^']+)'\)", t)
        w("  guid 样例：" + ", ".join(guids[:5]))

    w("\n===== 眉山 翻页（POST pageNumber245916=2）=====")
    r = post(u, data={"pageNumber245916": "2"}, ref=u)
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        guids = re.findall(r"do_detail\('([^']+)'\)", t)
        w(f"  page2 -> {r.status_code} len={len(t)} do_detail={len(guids)} 首 guid={guids[:3]}")
        m = re.search(r"共(\d+)条", t)
        w("  统计: " + (m.group(0) if m else "无"))

    w("\n===== 眉山 详情（POST guid=<首个guid>）=====")
    if guids:
        g = guids[0]
        r = post(u, data={"guid": g}, ref=u)
        if hasattr(r, "status_code") and r.status_code == 200:
            t = dec(r)
            w(f"  detail guid={g} -> {r.status_code} len={len(t)}")
            body = re.sub(r"(?s)<script.*?</script>", " ", t)
            body = re.sub(r"(?s)<style.*?</style>", " ", body)
            w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:1200])


if __name__ == "__main__":
    main()
