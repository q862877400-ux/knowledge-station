"""city-sc-probe31：雅安 信箱列表 + 详情字段结构 + 分页 + 眉山/达州 复核。"""
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


def strip(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 雅安 mail/index.html 全部部门 uuid =====")
    r = get("https://www.yaan.gov.cn/mail/index.html")
    uuids = []
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for m in re.finditer(r"mailbox\.html\?id=([0-9a-fA-F\-]+)", t):
            if m.group(1) not in uuids:
                uuids.append(m.group(1))
        w(f"  发现 {len(uuids)} 个部门 uuid")
        for u in uuids[:5]:
            w("   uuid " + u)
    else:
        w(f"  index.html -> {getattr(r, 'status_code', r)}")

    if not uuids:
        w("  无 uuid，停")
        return

    uid = uuids[0]
    w(f"\n===== 雅安 mailbox 列表页（id={uid}）=====")
    r = get(f"https://www.yaan.gov.cn/mail/mailbox.html?id={uid}", ref="https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        # 链接到详情
        dets = []
        for m in re.finditer(r'view\.html\?id=([0-9a-fA-F\-]+)&(?:amp;)?mailid=([0-9a-fA-F]+)', t):
            dets.append((m.group(1), m.group(2)))
        w(f"  详情链接 {len(dets)} 条（去重前）")
        seen = []
        for a in dets:
            if a not in seen:
                seen.append(a)
        w(f"  去重后 {len(seen)} 条；前 3：")
        for a in seen[:3]:
            w("    " + a[0] + " / " + a[1])
        # 分页
        w("  --- 分页痕迹 ---")
        for kw in ("page=", "Page", "laypage", "count:", "pages:"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + strip(t[max(0, i - 100):i + 120])[:220])
                break
        # 列表行文字
        w("  --- 列表区域文字（前 600）---")
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        w("   " + strip(body)[:600])
    else:
        w(f"  mailbox -> {getattr(r, 'status_code', r)}")

    if seen:
        a = seen[0]
        w(f"\n===== 雅安 详情页（id={a[0]} mailid={a[1]}）=====")
        r = get(f"https://www.yaan.gov.cn/mail/view.html?id={a[0]}&mailid={a[1]}",
                ref=f"https://www.yaan.gov.cn/mail/mailbox.html?id={uid}")
        if hasattr(r, "status_code") and r.status_code == 200:
            t = dec(r)
            w(f"  len={len(t)}")
            body = re.sub(r"(?s)<script.*?</script>", " ", t)
            body = re.sub(r"(?s)<style.*?</style>", " ", body)
            # 找问答容器
            for cls in ("detail", "content", "con", "mail", "reply", "hf", "zw", "info", "answer"):
                for m in re.finditer(r'class="[^"]*' + cls + r'[^"]*"[^>]*>(.{0,1500})', body, re.S):
                    seg = strip(m.group(1))
                    if len(seg) > 60:
                        w(f"  [{cls}] " + seg[:400])
                        break
            w("  全文（去标签）前 900：")
            w("   " + strip(body)[:900])
        else:
            w(f"  view -> {getattr(r, 'status_code', r)}")

    w("\n===== 雅安 mailbox 分页测试 page=2 =====")
    r = get(f"https://www.yaan.gov.cn/mail/mailbox.html?id={uid}&page=2", ref="https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        dets2 = []
        for m in re.finditer(r'view\.html\?id=([0-9a-fA-F\-]+)&(?:amp;)?mailid=([0-9a-fA-F]+)', t):
            if (m.group(1), m.group(2)) not in dets2:
                dets2.append((m.group(1), m.group(2)))
        w(f"  page=2 详情 {len(dets2)} 条；与 page1 是否相同首条: {dets2[0] if dets2 else None} vs {seen[0] if seen else None}")
    else:
        w(f"  page=2 -> {getattr(r, 'status_code', r)}")

    w("\n===== 眉山 12345 复核 =====")
    for u in ["https://www.ms.gov.cn/", "http://www.ms.gov.cn/",
              "https://www.ms.gov.cn/mail12345/swmail.jsp",
              "https://www.ms.gov.cn/zmhd/index.html"]:
        rr = get(u)
        if hasattr(rr, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(rr), re.S)
            if mm:
                ti = strip(mm.group(1))[:40]
            w(f"  {u} -> {rr.status_code} len={len(rr.text)} title={ti}")

    w("\n===== 达州 复核 =====")
    for u in ["https://www.dazhou.gov.cn/", "http://www.dazhou.gov.cn/",
              "https://www.dazhou.gov.cn/zmhd/index.html"]:
        rr = get(u)
        if hasattr(rr, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(rr), re.S)
            if mm:
                ti = strip(mm.group(1))[:40]
            w(f"  {u} -> {rr.status_code} len={len(rr.text)} title={ti}")


if __name__ == "__main__":
    main()
