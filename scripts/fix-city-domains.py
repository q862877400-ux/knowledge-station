"""给「域名指错」的市找正确门户（2026-11-02）。

做法：用 pypinyin 生成候选域名（全拼 / 首字母 / 加 gov 组合），
逐个抓取并**用标题核验**（标题必须含该市简称），通过的才记录。
不通过的记 `not_found`，**不猜**。
"""
import json
import re
import sys
from pathlib import Path

from pypinyin import lazy_pinyin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core.update.announce import default_transport

VERIFY = ROOT / "var" / "tmp" / "city-domain-verify.json"
OUT = ROOT / "var" / "tmp" / "city-domain-fix.json"
SUFFIX = ("自治州", "自治县", "地区", "市", "盟")


def short(city: str) -> str:
    for s in SUFFIX:
        if city.endswith(s) and len(city) > len(s) + 1:
            return city[: -len(s)]
    return city


def candidates(city: str) -> list[str]:
    name = short(city)
    py = lazy_pinyin(name)
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
    tr = default_transport()
    fixed, failed = {}, []
    for r in bad:
        city = r["city"]
        key = short(city)
        got = None
        for u in candidates(city):
            try:
                st, body = tr.fetch(u, timeout=15)
            except Exception:                    # noqa: BLE001
                continue
            if st != 200 or not isinstance(body, str):
                continue
            m = re.search(r"<title>(.*?)</title>", body, re.DOTALL | re.IGNORECASE)
            title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
            if key in title:
                got = {"city": city, "url": u, "title": title[:50],
                       "old": r["url"], "old_title": r["title"]}
                break
        if got:
            fixed[city] = got
            print(f"  ✔ {city[:10]:12} {got['url'][:34]:36} {got['title'][:24]}")
        else:
            failed.append({"city": city, "old": r["url"],
                           "old_title": r["title"]})
            print(f"  ✘ {city[:10]:12} 候选都不对（旧地址指向：{r['title'][:22]}）")
    OUT.write_text(json.dumps({"fixed": fixed, "failed": failed},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n修复 {len(fixed)} / {len(bad)}；未找到 {len(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
