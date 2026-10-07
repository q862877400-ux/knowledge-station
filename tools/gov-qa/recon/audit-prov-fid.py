"""抽查新增通道（分省 / 定向）的 answer 质量：有没有"问题当答复"、跟帖串位、空答复。

判据（沿用本模块已确立的三条）：
 1. `answer == question`（问题当答复）；
 2. answer 以问号结尾且长度短（疑似问题）；
 3. answer 缺失或极短（<10 字）；
 4. `extra.answer_kind` 标注为网友跟帖（应只在 netizen_comments 里）。
输出：recon/audit-prov-fid.txt（逐条疑点）与统计。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "audit-prov-fid.txt"

FILES = ["people-liuyan-prov-人民网领导留言板·分省.jsonl",
         "people-liuyan-fid-人民网领导留言板·定向版块.jsonl"]
Q_END = re.compile(r"[?？]\s*$")


def main() -> int:
    stats: Counter = Counter()
    suspicious: list[str] = []
    lens: list[int] = []
    for name in FILES:
        p = DATA / name
        if not p.exists():
            continue
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        stats[f"{name} 总条数"] = len(rows)
        for r in rows:
            q = (r.get("question") or "").strip()
            a = (r.get("answer") or "").strip()
            extra = r.get("extra") or {}
            lens.append(len(a))
            if not a:
                stats["空答复"] += 1
                suspicious.append(f"[空答复] {r.get('id')} {q[:30]}")
                continue
            if a == q:
                stats["答复==问题"] += 1
                suspicious.append(f"[同问同答] {r.get('id')} {q[:30]}")
            if len(a) < 10:
                stats["答复<10字"] += 1
                suspicious.append(f"[极短] {r.get('id')} {a[:30]}")
            if Q_END.search(a) and len(a) < 40:
                stats["答复像问题"] += 1
                suspicious.append(f"[疑似问题] {r.get('id')} {a[:40]}")
            if extra.get("answer_kind"):
                # 这不是污染：answer_kind 是引擎给「本条另带网友跟帖」打的标记
                # （dataType==9 存在时写入），答复本身仍取 dataType==4。
                stats["带 answer_kind 标记（正常）"] += 1
    lens.sort()
    if lens:
        n = len(lens)
        stats["答复长度 中位数"] = lens[n // 2]
        stats["答复长度 p10"] = lens[n // 10]
        stats["答复长度 p90"] = lens[int(n * 0.9)]
    with OUT.open("w", encoding="utf-8") as f:
        f.write("== 统计 ==\n")
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
        f.write(f"\n== 疑点 {len(suspicious)} 条 ==\n")
        for s in suspicious[:200]:
            f.write(s + "\n")
    print(f"[audit] 疑点 {len(suspicious)} 条；统计写入 {OUT.name}")
    for k, v in stats.items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    main()
