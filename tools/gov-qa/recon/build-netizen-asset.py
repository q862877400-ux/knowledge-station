"""把「网友跟帖」（`extra.netizen_comments`）抽成**独立标注资产**。

**为什么单独做**：跟帖是**真人语言**（真实群众的建议、反问、诉苦），与「官方答复」是两种用途；
按 `SITE-REGISTRY` 的口径必须**单独标注、绝不混进 answer 字段**。

**为何不写进 `data/`**：`data/*.jsonl` 是统一问答格式，`measure-locate-rate.py` 会 glob 它；
把跟帖混进去会给测量制造假样本。本脚本产出**模块根目录**的
`assets-netizen-comments.jsonl`（每行一条跟帖，带归属与来源 tid）。

字段：`source / tid / url / province / city / dept / comment / asked_at`
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE.parent / "assets-netizen-comments.jsonl"


def main() -> int:
    n = 0
    prov = Counter()
    with OUT.open("w", encoding="utf-8") as w:
        for f in sorted(DATA.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                extra = rec.get("extra") or {}
                comments = extra.get("netizen_comments") or []
                if not comments:
                    continue
                pn = extra.get("pForumNames") or []
                for c in comments:
                    text = (c or "").strip()
                    if not text:
                        continue
                    w.write(json.dumps({
                        "source": rec.get("source"),
                        "tid": rec.get("id"),
                        "url": rec.get("url"),
                        "province": (pn[0] if pn and str(pn[0]).endswith(("省", "市", "自治区"))
                                     else None),
                        "city": (pn[1] if len(pn) > 1 else None),
                        "dept": rec.get("dept"),
                        "comment": text,
                        "asked_at": rec.get("asked_at"),
                        "kind": "网友跟帖（非官方答复）",
                    }, ensure_ascii=False) + "\n")
                    n += 1
                    if pn:
                        prov[str(pn[0])] += 1
    print(f"[netizen] 抽出 {n} 条网友跟帖 → {OUT.name}")
    for p, c in prov.most_common(10):
        print(f"   {p}: {c}")
    return 0


if __name__ == "__main__":
    main()
