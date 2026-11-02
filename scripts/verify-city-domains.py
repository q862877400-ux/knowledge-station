"""核验「市 → 域名」是否对得上（2026-11-02）。

背景：`city-domains-all.json` 是当年用"首字母拼域名"猜出来的，
实测已发现 4 条串站（宿州→苏州、榆林→玉林、晋中→锦州、固原→涡阳），
其中宿州那条把苏州的 121 条数据记到了宿州名下。

做法：抓每个市的门户首页，取 `<title>`，检查里面是否出现该市名
（去掉「市/地区/盟/自治州/自治县」后缀）。对不上就记进报告，**不自动改**——
改哪个由人工核验过的映射决定。
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core.update.announce import default_transport  # noqa: E402

REG = ROOT / "tools" / "gov-qa" / "recon" / "city-domains-all.json"
OUT = ROOT / "var" / "tmp" / "city-domain-verify.json"
SUFFIX = ("自治州", "自治县", "地区", "市区", "市", "盟")


def short_name(city: str) -> str:
    for s in SUFFIX:
        if city.endswith(s) and len(city) > len(s) + 1:
            return city[: -len(s)]
    return city


def check(tr, item: tuple[str, dict]) -> dict:
    city, info = item
    url = info.get("url") or ""
    rec = {"city": city, "url": url, "province": info.get("province"),
           "title": "", "ok": None, "why": ""}
    if not url.startswith("http"):
        rec.update(ok=False, why="bad_url")
        return rec
    try:
        st, body = tr.fetch(url, timeout=20)
    except Exception as exc:                    # noqa: BLE001
        rec.update(ok=False, why=type(exc).__name__)
        return rec
    if st != 200 or not isinstance(body, str):
        rec.update(ok=False, why=f"http_{st}")
        return rec
    m = re.search(r"<title>(.*?)</title>", body, re.S | re.I)
    title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    rec["title"] = title[:60]
    rec["ok"] = short_name(city) in title
    if not rec["ok"]:
        rec["why"] = "title_mismatch"
    return rec


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    print(f"待核验 {len(reg)} 个市")
    tr = default_transport()
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(check, tr, it) for it in reg.items()]
        for i, fut in enumerate(as_completed(futs), 1):
            rows.append(fut.result())
            if i % 50 == 0:
                print(f"  {i}/{len(futs)}")
    bad = [r for r in rows if r["ok"] is False]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sorted(rows, key=lambda r: r["city"]),
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n核验完成：{len(rows)} 个市，**对不上 {len(bad)} 个**")
    for r in bad:
        print(f"  {r['city'][:10]:12} {r['url'][:34]:36} {r['title'][:30]}  ({r['why']})")
    print(f"\n明细 → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
