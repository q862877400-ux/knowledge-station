"""量准法规切分的两个已知问题（修之前先量，不凭印象）。

## 问题 1：正文里引用别条时**多切一刀**
`_LAW_SPLIT = re.compile(r"(?=第[…]+条)")` **不要求行首** ⇒
「依照本法第五十条规定…」里的「第五十条」也会被当成新条款的起点。
实测症状：劳动合同法实际 98 条、切出 126 条。

## 问题 2：**每条都背上"文件头/立法沿革"前缀**
`split_law_text` 把"第一个条文之前的全部内容"当章节上下文（截断 60 字），
**逐条前置**，而且**用过之后不重置** ⇒ 整部法律的每一条都带同一段文件头。

本脚本只读源目录，量：
 ① 全库法规里，「第X条」出现在**行首** vs **句子中间**各多少；
 ② 文件头（第一个条文之前的内容）有多长、长什么样；
 ③ 用"只认行首"当新的切分判据，条数会怎么变（与法律真实条数对照）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\37-measure-law-split.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "measure-law-split.json"
sys.path.insert(0, str(ROOT))
LAW_ROOT = Path("D:/AI/work space/标准/法律法规")

#: 现状：不要求行首
ANY = re.compile(r"第[一二三四五六七八九十百千零]+条")
#: 候选：只认行首（允许前置空格与 markdown 粗体）
LINE = re.compile(r"(?=^[ \t]*(?:\*\*)?第[一二三四五六七八九十百千零]+条)", re.M)
#: ⚠⚠ **同一个错我今天犯了第三次**：正则带 `^` 却漏 `re.M` ⇒ `^` 只匹配整串开头，
#: 于是"行首命中数"恒为 0，量出来的是假结论（本例第一次跑就报了"只认行首 = 0"）。
#: 凡是 `^`/`$` 用来匹配**每一行**的正则，必须带 `re.M`；带 `re.S` 的另说。
LINE_NO = re.compile(r"^[ \t]*(?:\*\*)?(第[一二三四五六七八九十百千零]+条)", re.M)

#: 有确定条数的样本（用于判"哪种切法更接近真实"）
KNOWN = {"劳动法": 107, "劳动合同法": 98, "行政处罚法": 86, "社会保险法": 98,
         "特种设备安全法": 101, "职业病防治法": 90, "环境保护法": 70, "矿山安全法": 50,
         "刑法": 452, "民法典": 1260}


def main() -> int:
    files = [p for p in sorted(LAW_ROOT.rglob("*.md"))
             if not p.name.startswith("_") and "案例/" not in p.relative_to(LAW_ROOT).as_posix()]
    print(f"[m] 法规文件 {len(files)} 个\n", flush=True)

    tot_any = tot_line = 0
    heads = []
    rows = []
    for p in files:
        t = p.read_text(encoding="utf-8", errors="ignore")
        a = len(ANY.findall(t))
        l = len(LINE_NO.findall(t))
        tot_any += a
        tot_line += l
        m = re.search(r"^[ \t]*(?:\*\*)?第[一二三四五六七八九十百千零]+条", t, re.M)
        if m:
            heads.append(m.start())
        name = re.sub(r"\(\d{4}-\d{2}-\d{2}\)$", "", p.stem)
        if name in KNOWN:
            rows.append({"name": name, "真实条数": KNOWN[name],
                         "现状(不认行首)": a, "候选(只认行首)": l})

    print(f"[m] 「第X条」出现次数：不认行首 = {tot_any:,} ；只认行首 = {tot_line:,}"
          f"  ⇒ 差 {tot_any - tot_line:,}（{1 - tot_line/max(1,tot_any):.1%} 是句子中间/引用）")
    if heads:
        print(f"[m] 文件头长度（第一个条文之前）：中位 {int(st.median(heads))} 字 / "
              f"最大 {max(heads)} / 为 0 的有 {sum(1 for x in heads if x == 0)} 个")

    print(f"\n[m] 与真实条数对照（{len(rows)} 部）：")
    print(f"    {'法律':14s} {'真实':>6s} {'现状':>6s} {'只认行首':>8s}  判读")
    for r in rows:
        d1 = r["现状(不认行首)"] - r["真实条数"]
        d2 = r["候选(只认行首)"] - r["真实条数"]
        tag = "✅ 更准" if abs(d2) < abs(d1) else ("同" if d2 == d1 else "更差")
        print(f"    {r['name']:14s} {r['真实条数']:>6d} {r['现状(不认行首)']:>6d} "
              f"{r['候选(只认行首)']:>8d}  {tag}（差 {d1:+d} → {d2:+d}）")

    # 文件头样例
    sample = None
    p0 = next((p for p in files if p.stem.startswith("劳动合同法")), None)
    if p0:
        t = p0.read_text(encoding="utf-8", errors="ignore")
        m = LINE_NO.search(t)
        sample = t[:m.start()] if m else t[:200]
    OUT.write_text(json.dumps({
        "why": "修法规切分两处已知问题前，先把问题量准",
        "files": len(files),
        "clause_occurrences": {"anywhere": tot_any, "line_start_only": tot_line,
                               "mid_sentence": tot_any - tot_line},
        "front_matter_chars": {"median": int(st.median(heads)) if heads else None,
                               "max": max(heads) if heads else None,
                               "zero": sum(1 for x in heads if x == 0)},
        "known_laws": rows,
        "front_matter_sample": sample,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[m] 文件头样例（劳动合同法）：\n{sample}")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
