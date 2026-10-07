"""量化抽查：各源 answer 字段的污染面。

判据（本地启发式，只用于定位问题，不作最终结论）：
 · answer 以「问：」「您好，请问」等提问腔开头 → 疑似把问题当答复；
 · answer 含 `function(`/`var `/`<style`/`DD_belatedPNG` 等代码噪音 → 抓到页面壳；
 · answer 为空或过短（<40 字）→ 抓取失败。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

CODE_RE = re.compile(r"function\s*\(|var\s+\w+\s*=|DD_belatedPNG|<style|\.fix\(|getElementById")
ASK_RE = re.compile(r"^\s*(问：|请问|您好[，,]?\s*请问)")


def main() -> int:
    lines = ["# answer 字段污染面扫描（本地启发式）\n"]
    for f in sorted(DATA.glob("*.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not rows:
            continue
        n = len(rows)
        code = ask = short = empty = 0
        for r in rows:
            a = (r.get("answer") or "").strip()
            if not a:
                empty += 1
                continue
            if len(a) < 40:
                short += 1
            if CODE_RE.search(a):
                code += 1
            if ASK_RE.match(a):
                ask += 1
        tag = "⚠" if (code or ask or empty) else "✅"
        lines.append(f"{tag} {f.stem}: 共 {n}｜代码噪音 {code}｜提问腔开头 {ask}"
                     f"｜过短(<40字) {short}｜空 {empty}")
    out = HERE / "answer-pollution-scan.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\nwritten", out)
    return 0


if __name__ == "__main__":
    main()
