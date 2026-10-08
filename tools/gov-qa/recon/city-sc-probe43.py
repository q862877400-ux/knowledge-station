"""city-sc-probe43：广元市长信箱突破口（qgj.cngy.gov.cn:9050 绕过瑞数）。"""
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASE = "http://qgj.cngy.gov.cn:9050"


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

    w("===== 突破口：主站瑞数 412 vs 信箱端口 9050 =====")
    for u in ["https://www.cngy.gov.cn/", "http://qgj.cngy.gov.cn:9050/ldxx/szxx/index"]:
        try:
            r = s.get(u, timeout=20)
            ti = ""
            m = re.search(r"<title>(.*?)</title>", dec(r), re.S)
            if m:
                ti = re.sub(r"\s+", " ", m.group(1))[:40]
            w(f"  {u} -> {r.status_code} len={len(r.content)} title={ti}")
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> ERR {type(e).__name__}")

    w("\n===== 列表 API：POST /ldxx/szxx/publish/data =====")
    r = s.get(BASE + "/ldxx/szxx/s/public", timeout=20, headers={"Referer": BASE + "/ldxx/szxx/index"})
    t = dec(r)
    tok = re.search(r"X-XSRF-TOKEN':\s*'([^']+)'", t)
    tok = tok.group(1) if tok else ""
    w(f"  X-XSRF-TOKEN = {tok}；cookies = {s.cookies.get_dict()}")
    r2 = s.post(BASE + "/ldxx/szxx/publish/data", data={"page": 1, "limit": 10},
                headers={"X-XSRF-TOKEN": tok, "Referer": BASE + "/ldxx/szxx/s/public"}, timeout=20)
    j = json.loads(dec(r2))
    w(f"  -> {r2.status_code} count={j.get('count')} rows={len(j.get('data', []))}")
    w("  首条：" + json.dumps(j["data"][0], ensure_ascii=False)[:300])

    w("\n===== 详情：GET /ldxx/szxx/publish/<id> =====")
    sid = j["data"][0]["id"]
    r3 = s.get(BASE + f"/ldxx/szxx/publish/{sid}", timeout=20)
    t3 = dec(r3)
    w(f"  -> {r3.status_code} len={len(t3)}")
    m = re.search(r"信件的处理结果.*?<td[^>]*class=\"detail-text\"[^>]*>(.*?)</td>", t3, re.S)
    w("  答复前 200：" + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))[:200] if m else "  未取到答复")


if __name__ == "__main__":
    main()
