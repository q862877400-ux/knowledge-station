"""用「字节解码」重新核验那些被判错的旧地址（2026-11-02）。

第一轮核验用 `tr.fetch()` 的已解码字符串，GBK 站会变成乱码 ⇒ 假阳性
（实测：清远、鄂州明明是本市，却被判成"指到别处"）。
本脚本对**同一个旧地址**用字节解码重判，把假阳性摘出来。
"""
import json
import re
import sys
from pathlib import Path

from curl_cffi import requests as creq

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "var" / "tmp" / "city-domain-verify.json"
OUT = ROOT / "var" / "tmp" / "city-domain-reverify.json"
SUFFIX = ("自治州", "自治县", "地区", "市", "盟")
SESSION = creq.Session(impersonate="chrome")


def short(city: str) -> str:
    for s in SUFFIX:
        if city.endswith(s) and len(city) > len(s) + 1:
            return city[: -len(s)]
    return city


def decode(data: bytes) -> str:
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


def main() -> int:
    rows = json.loads(VERIFY.read_text(encoding="utf-8"))
    bad = [r for r in rows if r["ok"] is False]
    out = []
    for r in bad:
        key = short(r["city"])
        title, why = "", ""
        try:
            resp = SESSION.get(r["url"], timeout=20, allow_redirects=True)
            if resp.status_code == 200:
                html = decode(resp.content or b"")
                m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
                title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
            else:
                why = f"http_{resp.status_code}"
        except Exception as exc:                 # noqa: BLE001
            why = type(exc).__name__
        ok = bool(title) and key in title
        out.append({"city": r["city"], "url": r["url"], "title": title[:50],
                    "ok_after_decode": ok, "why": why})
        print(f"  {'✔' if ok else '✘'} {r['city'][:10]:12} {r['url'][:30]:32} "
              f"{title[:28]}  {why}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    good = [x for x in out if x["ok_after_decode"]]
    print(f"\n解码后其实是正确的：{len(good)}/{len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
