"""抽查 2026-10-08 四个新 IGI 通道（贵州商务 / 贵州自然资源 / 吉林人社 / 吉林交通运输）的 answer 质量。

判据（沿用本模块已确立的）：空答案 / 答案==问题 / 少于10字 / 代码噪声；
另统计三级归属（省/市/县）覆盖。
输出：recon/audit-igi-new.txt（逐条疑点）与统计。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "audit-igi-new.txt"

FILES = ["gz-swt-贵州省商务厅·厅长信箱.jsonl",
         "gz-zrzy-贵州省自然资源厅·厅长信箱.jsonl",
         "jl-hrss-吉林省人力资源社会保障厅·厅长信箱.jsonl",
         "jl-jt-吉林省交通运输厅·厅长信箱.jsonl"]
Q_END = re.compile(r"[?？]\s*$")
NOISE = re.compile(r"^\s*(function|var |<script|<!DOCTYPE|&nbsp;)", re.I)


def main() -> int:
    lines: list[str] = []
    suspects: list[str] = []
    stats: Counter = Counter()
    areas: dict[str, set[str]] = {}
    for fn in FILES:
        p = DATA / fn
        if not p.exists():
            lines.append(f"!! 缺文件 {fn}")
            continue
        recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        stats[fn] = len(recs)
        for r in recs:
            key = r.get("site") or fn
            ans = (r.get("answer") or "").strip()
            q = (r.get("question") or "").strip()
            if not ans:
                suspects.append(f"{key} {r.get('id')}  空答案")
            elif len(ans) < 10:
                suspects.append(f"{key} {r.get('id')}  过短: {ans[:40]}")
            elif ans == q:
                suspects.append(f"{key} {r.get('id')}  答案==问题: {ans[:40]}")
            elif NOISE.match(ans):
                suspects.append(f"{key} {r.get('id')}  噪声: {ans[:40]}")
            ex = r.get("extra") or {}
            pf = ex.get("pForumNames") or []
            if len(pf) >= 3:
                areas.setdefault(key, set()).add("/".join(pf))
    lines.append("== 条数 ==")
    for fn, n in stats.items():
        lines.append(f"  {fn}  {n}")
    lines.append("== 三级归属覆盖（省/市/县） ==")
    for key in sorted(areas):
        s = sorted(areas[key])
        lines.append(f"  {key}  {len(s)} 个县: " + "、".join(s[:40]) + ("…" if len(s) > 40 else ""))
    lines.append(f"== 疑点 {len(suspects)} 条 ==")
    lines.extend("  " + s for s in suspects)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:24]))
    print(f"疑点 {len(suspects)} 条，详见 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
