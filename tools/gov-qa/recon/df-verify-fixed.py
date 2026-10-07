"""核对修好后的 df（地方流）数据：省市归属 + 答复是否为官方口吻。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "df-fixed-sample.txt"


def main() -> int:
    rows = []
    for p in DATA.glob("people-liuyan-df-*.jsonl"):
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    prov = Counter()
    for r in rows:
        pn = (r.get("extra") or {}).get("pForumNames") or []
        prov[pn[0] if pn else "（无归属）"] += 1
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"共 {len(rows)} 条；覆盖省级单位 {len(prov)} 个\n")
        f.write("分省条数：" + "、".join(f"{k} {v}" for k, v in prov.most_common()) + "\n\n")
        for r in rows[:6]:
            f.write(f"--- {r.get('id')} | 归属：{(r.get('extra') or {}).get('pForumNames')} | "
                    f"承办：{r.get('dept')}\n")
            f.write(f"问：{(r.get('question') or '')[:90]}\n")
            f.write(f"答：{(r.get('answer') or '')[:180]}\n")
            nc = (r.get("extra") or {}).get("netizen_comments") or []
            f.write(f"（附带网友跟帖 {len(nc)} 条，示例：{nc[0][:60] if nc else '—'}）\n\n")
    print("written", OUT, "rows", len(rows), "provinces", len(prov))
    return 0


if __name__ == "__main__":
    main()
