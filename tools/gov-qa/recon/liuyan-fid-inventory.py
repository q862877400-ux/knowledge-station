"""汇总已采留言板数据里出现过的全部版块（fid + 归属 + 承办单位），看编号分层结构。

产出：recon/liuyan-fid-inventory.md（按 fid 排序，标出省/市/县层级线索）
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "liuyan-fid-inventory.md"


def main() -> int:
    seen: dict[str, dict] = {}
    for f in sorted(DATA.glob("people-liuyan*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            extra = rec.get("extra") or {}
            fid = str(extra.get("fid") or "")
            if not fid:
                continue
            pn = extra.get("pForumNames") or []
            item = seen.setdefault(fid, {"fid": fid, "n": 0, "p": pn,
                                         "forum": rec.get("dept") or ""})
            item["n"] += 1
    rows = sorted(seen.values(), key=lambda x: int(x["fid"]))
    lines = ["# 留言板版块清单（来自已采数据）", "",
             f"共 {len(rows)} 个版块，fid 范围 {rows[0]['fid'] if rows else '-'} ~ "
             f"{rows[-1]['fid'] if rows else '-'}", "",
             "| fid | 层级线索(pForumNames) | 承办单位 | 已采 |", "|---|---|---|---|"]
    for r in rows:
        p = " > ".join(str(x) for x in (r["p"] or [])) or "-"
        lines.append(f"| {r['fid']} | {p} | {r['forum'][:28]} | {r['n']} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[inventory] 版块 {len(rows)} 个 → {OUT.name}")
    # 按 fid 段汇总
    bands: dict[int, int] = {}
    for r in rows:
        bands[int(r["fid"]) // 50 * 50] = bands.get(int(r["fid"]) // 50 * 50, 0) + 1
    print("  fid 段分布:", dict(sorted(bands.items())))
    return 0


if __name__ == "__main__":
    main()
