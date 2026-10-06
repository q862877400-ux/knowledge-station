"""量化：**国标 OCR 的切分到底坏到什么程度**（决定这 799 本能不能直接入库）。

## 已知根因（上一轮诊断）
 ① `split_gb_text` 的正则只认 **带点的** `1.1 / 4.2.3`，**不认 `## 7 技术要求` 这种一级条款**
    ⇒ 一级条款被跳过、其内容被并进相邻条款 ⇒ 条款数骤减、内容错乱；
 ② 还出现过 `477.38` 这种**假条款号**（把数值当条号）；
 ③ MinerU 正文有**阅读顺序问题**（句内数字被搬到句后）。

## 本脚本量三件事（全量 799 本，只读源目录）
 · 每本：**可切位点数** vs **`split_gb_text` 实切数** ⇒ 漏切比例；
 · 有**多少本切出 0 条**（在真入库时就是 status=error）；
 · 切出的条款号里，有多少是**可疑的**（如 `477.38`、超出层次深度的）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\26-split-damage-scale.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "split-damage-scale.json"
sys.path.insert(0, str(ROOT))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"

#: 任意"行首数字"= 潜在条款位点（含 `## 7` 与 `1.2.1`）
ALL_NUM_LINES = re.compile(r"^#{0,6}\s*(\d+(?:\.\d+){0,3})\s+\S", re.M)
#: 一级条款（单个数字）= `## 7` 这类，当前切分函数**漏掉**的
TOP_LEVEL = re.compile(r"^#{1,6}\s*\d+\s+\S", re.M)


def main() -> int:
    from src.core.ingestion.law_text import split_gb_text

    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
            and (d / "markdown.md").exists()]
    print(f"[scale] 已出 markdown 的国标 = {len(dirs)} 本\n", flush=True)

    zero, ratios, rows = 0, [], []
    suspect = Counter()
    tot_sites = tot_got = tot_top = 0
    for d in dirs:
        t = (d / "markdown.md").read_text(encoding="utf-8", errors="ignore")
        sites = ALL_NUM_LINES.findall(t)
        tops = TOP_LEVEL.findall(t)
        gb = split_gb_text(t)
        n_s, n_g = len(sites), len(gb)
        tot_sites += n_s
        tot_got += n_g
        tot_top += len(tops)
        if n_g == 0:
            zero += 1
        if n_s:
            ratios.append(n_g / n_s)
        for no, _body in gb:
            # 可疑条号：段数 > 3，或末段是两位数以上（如 477.38）
            parts = no.split(".")
            if len(parts) > 3 or (len(parts) == 2 and len(parts[1]) >= 2):
                suspect["末段多位/层次过深"] += 1
        rows.append({"dir": d.name[:52], "sites": n_s, "top_level_heads": len(tops),
                     "split_gb": n_g, "ratio": round(n_g / n_s, 2) if n_s else None})

    n = max(1, len(dirs))
    print(f"[scale] 可切位点合计 {tot_sites}；split_gb_text 实切合计 {tot_got} "
          f"⇒ 总命中率 {tot_got/max(1,tot_sites):.0%}")
    print(f"[scale] 其中**一级条款标题**（`## 7` 这类，当前被漏）合计 {tot_top}")
    print(f"[scale] **切出 0 条**的本数：{zero}/{n} = {zero/n:.0%}  ← 这些入库时会 status=error")
    if ratios:
        print(f"[scale] 每本命中率：中位 {st.median(ratios):.0%} / 最低 {min(ratios):.0%} / "
              f"最高 {max(ratios):.0%}")
        for thr in (0.05, 0.2, 0.5, 0.8):
            k = sum(1 for r in ratios if r < thr)
            print(f"          命中率 < {thr:.0%} 的本数：{k} ({k/len(ratios):.0%})")
    print(f"[scale] 可疑条号合计 {sum(suspect.values())}：{dict(suspect)}")

    worst = sorted(rows, key=lambda x: (x["ratio"] if x["ratio"] is not None else 9))[:10]
    print("\n[scale] 最差的 10 本：")
    for r in worst:
        print(f"    位点 {r['sites']:4d}（一级 {r['top_level_heads']:3d}）⇒ 切出 {r['split_gb']:3d}  "
              f"{r['dir']}")

    OUT.write_text(json.dumps({
        "why": "量化国标 OCR 的切分损伤：可切位点 vs split_gb_text 实切",
        "docs": len(dirs),
        "totals": {"sites": tot_sites, "split_gb": tot_got,
                   "hit_rate": round(tot_got / max(1, tot_sites), 4),
                   "top_level_headings_missed": tot_top,
                   "docs_with_zero_clauses": zero},
        "ratio_stats": {"median": st.median(ratios) if ratios else None,
                        "min": min(ratios) if ratios else None,
                        "max": max(ratios) if ratios else None},
        "suspect_clause_numbers": dict(suspect),
        "worst10": worst, "per_doc_sample": rows[:40],
        "boundary": ["可切位点按『行首数字+空格+非空』正则统计，是**上界**（含少量非条款数字）；",
                     "本脚本只读源目录与切分函数，未写任何库。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
