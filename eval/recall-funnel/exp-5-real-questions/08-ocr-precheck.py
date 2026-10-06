"""OCR 前置体检：**GB / GBZ 那 1,168 本里，多少是扫描件？**

## 为什么先量这个（业主 2026-10-07 提出"先把所有内容都 OCR 好再拿来用"）
业主的直觉是"OCR 做一次就不用再做"——**这个方向对**。但有三件事要先弄清：
 1. **源库的构成**：实测 `D:\\AI\\work space\\标准\\...` 共 35,244 个文件 / 151.8 GB，
    顶层是 **GBT 34,076 / GB 1,088 / GBZ 80** ⇒ **源库自己也 97% 是推荐性标准**，
    而真实提问缺的恰恰是 **GB 强制 + GBZ** ⇒ **全量 OCR 3.5 万本，补的是不缺的那一类**。
 2. **文字版 PDF 根本不需要 OCR**（直接抽文字**更准**）—— 混在一起 OCR 会白白降低质量、白花时间。
 3. 所以先量：**GB/GBZ 里有多少是扫描件**。

判据：用 PyMuPDF 抽文字，**每页可抽字符数**。
 · 中位每页 ≥ 100 字 ⇒ 有文字层（**文字版**）；
 · 中位每页 < 20 字 ⇒ 几乎抽不出字（**扫描件**，需要 OCR）。

只读源目录；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\08-ocr-precheck.py --n 40
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ocr-precheck.json"
SRC = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()

    import fitz  # PyMuPDF

    if not SRC.exists():
        print(f"⛔ 源目录不可达：{SRC}")
        return 1

    buckets = {}
    for sub in ("GB", "GBZ", "GBT"):
        d = SRC / sub
        fs = sorted(f for f in d.rglob("*.pdf")) if d.exists() else []
        buckets[sub] = fs
        print(f"[ocr] {sub}: {len(fs)} 个 PDF", flush=True)

    rnd = random.Random(20261007)
    result = {"source": str(SRC), "total_by_bucket": {k: len(v) for k, v in buckets.items()},
              "sampled": {}, "why": "量 GB/GBZ 里多少是扫描件（决定 OCR 值不值得、要多久）"}
    for sub, fs in buckets.items():
        if not fs:
            continue
        pick = rnd.sample(fs, min(args.n, len(fs)))
        per = []
        for f in pick:
            try:
                doc = fitz.open(f)
                npg = doc.page_count
                chars = sum(len(doc[i].get_text() or "") for i in range(min(npg, 5)))
                doc.close()
                cpp = chars / max(1, min(npg, 5))
                per.append({"file": f.name[:60], "pages": npg, "chars_per_page": round(cpp, 1),
                            "kind": "文字版" if cpp >= 100 else ("扫描件" if cpp < 20 else "混合/可疑")})
            except Exception as e:                                          # noqa: BLE001
                per.append({"file": f.name[:60], "error": f"{type(e).__name__}"})
        kinds = Counter(x["kind"] for x in per if "kind" in x)
        cpps = [x["chars_per_page"] for x in per if "chars_per_page" in x]
        result["sampled"][sub] = {
            "n": len(per), "kinds": dict(kinds),
            "chars_per_page_median": round(st.median(cpps), 1) if cpps else None,
            "pages_median": round(st.median([x["pages"] for x in per if "pages" in x]), 0) if per else None,
            "samples": per[:10],
        }
        print(f"[ocr] {sub} 抽样 {len(per)} 本：{dict(kinds)}；每页字数中位 {result['sampled'][sub]['chars_per_page_median']}",
              flush=True)

    # 折算：若 GB+GBZ 全部要 OCR，大概多少页
    tot_pages = 0
    for sub in ("GB", "GBZ"):
        s = result["sampled"].get(sub)
        if s and s.get("pages_median"):
            tot_pages += result["total_by_bucket"][sub] * s["pages_median"]
    result["estimate"] = {
        "GB_plus_GBZ_files": result["total_by_bucket"].get("GB", 0) + result["total_by_bucket"].get("GBZ", 0),
        "rough_total_pages": int(tot_pages),
        "note": "页数按抽样中位折算，仅供估量级；实际以逐本统计为准。",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "sampled"}, ensure_ascii=False, indent=1))
    for sub, s in result["sampled"].items():
        print(f"\n=== {sub}（抽 {s['n']} 本，每页字数中位 {s['chars_per_page_median']}）===")
        for x in s["samples"][:6]:
            print(f"   {x.get('kind', x.get('error')):8s} {x.get('chars_per_page')!s:>7s} 页/本={x.get('pages')!s:>5s}  {x['file']}")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
