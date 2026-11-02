"""给「域名指错」的市找正确门户 —— 修正版：按字节解码后再核验标题（2026-11-02）。

第一版用 `tr.fetch()` 拿到的是已解码的 `str`，而很多政务站是 **GBK**，
被按 UTF-8 解码成乱码 ⇒ 标题核验必然失败（岳阳/湘潭/清远/益阳等就是这样被误判）。
本版直接取字节，依次尝试 utf-8 / gbk / gb18030 解码。
"""
import json
import re
import sys
from pathlib import Path

from curl_cffi import requests as creq
from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "var" / "tmp" / "city-domain-verify.json"
OUT = ROOT / "var" / "tmp" / "city-domain-fix2.json"
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


def title_of(url: str) -> tuple[str, str]:
    """(标题, 失败原因)。按字节取回，按编码猜测解码。"""
    try:
        r = SESSION.get(url, timeout=20, allow_redirects=True)
    except Exception as exc:                     # noqa: BLE001
        return "", type(exc).__name__
    if r.status_code != 200:
        return "", f"http_{r.status_code}"
    html = decode(r.content or b"")
    m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    return (re.sub(r"\s+", " ", m.group(1)).strip() if m else ""), ""


def candidates(city: str) -> list[str]:
    py = lazy_pinyin(short(city))
    full = "".join(py)
    ini = "".join(p[0] for p in py if p)
    outs = []
    for host in (full, ini, full + "s", ini + "s"):
        outs.append(f"https://www.{host}.gov.cn/")
        outs.append(f"http://www.{host}.gov.cn/")
    return list(dict.fromkeys(outs))


def main() -> int:
    rows = json.loads(VERIFY.read_text(encoding="utf-8"))
    bad = [r for r in rows if r["ok"] is False]
    fixed, failed = {}, []
    for r in bad:
        city = r["city"]
        key = short(city)
        got = None
        tried = []
        for u in candidates(city):
            title, why = title_of(u)
            tried.append({"url": u, "title": title[:40], "why": why})
            if key in title:
                got = {"city": city, "url": u, "title": title[:50],
                       "old": r["url"], "old_title": r["title"]}
                break
        if got:
            fixed[city] = got
            print(f"  ✔ {city[:10]:12} {got['url'][:34]:36} {got['title'][:26]}")
        else:
            failed.append({"city": city, "old": r["url"], "tried": tried})
            print(f"  ✘ {city[:10]:12} 候选全不对（{len(tried)} 个）")
    OUT.write_text(json.dumps({"fixed": fixed, "failed": failed},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n修复 {len(fixed)} / {len(bad)}；未找到 {len(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
