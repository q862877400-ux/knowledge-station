"""核验「市 → 域名」是否对得上，并给出候选修正（2026-11-02）。

## 为什么需要

`tools/gov-qa/recon/city-domains-all.json` 是当年用"首字母拼域名"猜出来的。
实测抓到 **31 个市指到了别的地方**，其中 4 个已经造成了数据串站
（清远市存了清原县 67 条、唐山市存了泰顺县 15 条、六盘水存了黎平县 12 条、
梅州存了绵竹市 6 条），已删除。

## 三种用法（同一份文件，避免三份重复实现）

    # ① 核验现状：抓每个市门户的标题，看是否含该市简称
    .venv\\Scripts\\python.exe scripts/verify-city-domains.py --verify

    # ② 给判错的市找候选域名（pypinyin 生成 全拼/首字母 × http/https）
    .venv\\Scripts\\python.exe scripts/verify-city-domains.py --fix

    # ③ 用字节解码复核（GBK 站会被 UTF-8 解码成乱码 ⇒ 假阳性）
    .venv\\Scripts\\python.exe scripts/verify-city-domains.py --reverify

## 关键实现细节（都踩过）

- **必须按字节取回再猜编码**：很多政务站是 GBK，按 UTF-8 解码成乱码后标题核验必错
  （大连/岳阳/湘潭/益阳就是这样被误判成"指到别处"）。
- 核验判据是**标题里出现该市简称**（去掉 市/地区/盟/自治州/自治县）。
- 只报不改：改哪条由人核验后的映射决定（本脚本只产出候选）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from curl_cffi import requests as creq

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "tools" / "gov-qa" / "recon" / "city-domains-all.json"
OUT_VERIFY = ROOT / "var" / "tmp" / "city-domain-verify.json"
OUT_FIX = ROOT / "var" / "tmp" / "city-domain-fix.json"
OUT_REVERIFY = ROOT / "var" / "tmp" / "city-domain-reverify.json"
SUFFIX = ("自治州", "自治县", "地区", "市", "盟")
SESSION = creq.Session(impersonate="chrome")


def short(city: str) -> str:
    """去掉行政级别后缀，留下用于核验的简称。"""
    for s in SUFFIX:
        if city.endswith(s) and len(city) > len(s) + 1:
            return city[: -len(s)]
    return city


def decode(data: bytes) -> str:
    """按字节猜编码（utf-8 → gb18030 → gbk）。"""
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore")


def title_of(url: str) -> tuple[str, str]:
    """(标题, 失败原因)。按字节取回，避免 GBK 站被解成乱码。"""
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
    """用拼音生成候选域名：全拼 / 首字母，各自 http 与 https。"""
    from pypinyin import lazy_pinyin
    py = lazy_pinyin(short(city))
    full = "".join(py)
    ini = "".join(p[0] for p in py if p)
    outs = []
    for host in (full, ini, full + "s", ini + "s"):
        outs.append(f"https://www.{host}.gov.cn/")
        outs.append(f"http://www.{host}.gov.cn/")
    return list(dict.fromkeys(outs))


def cmd_verify(limit: int = 0) -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    items = list(reg.items())[: limit or None]
    print(f"核验 {len(items)} 个市")

    def one(it):
        city, info = it
        title, why = title_of(info.get("url") or "")
        return {"city": city, "url": info.get("url"), "title": title[:60],
                "ok": bool(title) and short(city) in title, "why": why}

    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(one, it) for it in items]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 50 == 0:
                print(f"  {i}/{len(futs)}")
    bad = [r for r in rows if not r["ok"]]
    OUT_VERIFY.write_text(json.dumps(sorted(rows, key=lambda r: r["city"]),
                                     ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"对上 {len(rows) - len(bad)} / 对不上 {len(bad)}")
    for r in bad:
        print(f"  {r['city'][:10]:12} {str(r['url'])[:32]:34} "
              f"{r['title'][:26]} ({r['why']})")
    return 0


def cmd_fix(limit: int = 0) -> int:
    rows = json.loads(OUT_VERIFY.read_text(encoding="utf-8"))
    bad = [r for r in rows if not r["ok"]][: limit or None]
    fixed, failed = {}, []
    for r in bad:
        key = short(r["city"])
        got = None
        for u in candidates(r["city"]):
            title, _why = title_of(u)
            if key in title:
                got = {"city": r["city"], "url": u, "title": title[:50],
                       "old": r["url"], "old_title": r["title"]}
                break
        if got:
            fixed[r["city"]] = got
            print(f"  ✔ {r['city'][:10]:12} {got['url'][:34]:36} {got['title'][:24]}")
        else:
            failed.append({"city": r["city"], "old": r["url"]})
            print(f"  ✘ {r['city'][:10]:12} 候选都不对（旧地址：{r['title'][:20]}）")
    OUT_FIX.write_text(json.dumps({"fixed": fixed, "failed": failed},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"修复 {len(fixed)} / 未找到 {len(failed)}")
    return 0


def cmd_reverify(limit: int = 0) -> int:
    rows = json.loads(OUT_VERIFY.read_text(encoding="utf-8"))
    bad = [r for r in rows if not r["ok"]][: limit or None]
    out = []
    for r in bad:
        title, why = title_of(r["url"])
        ok = bool(title) and short(r["city"]) in title
        out.append({"city": r["city"], "url": r["url"], "title": title[:50],
                    "ok_after_decode": ok, "why": why})
        print(f"  {'✔' if ok else '✘'} {r['city'][:10]:12} "
              f"{str(r['url'])[:30]:32} {title[:26]} {why}")
    OUT_REVERIFY.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    print(f"解码后其实正确：{sum(1 for x in out if x['ok_after_decode'])}/{len(out)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--reverify", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if args.verify:
        return cmd_verify(args.limit)
    if args.fix:
        return cmd_fix(args.limit)
    if args.reverify:
        return cmd_reverify(args.limit)
    print("用法：--verify / --fix / --reverify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
