"""重算 nat-mohurd 的 id —— 修 59 条 id 碰撞。

## 背景

`nat_mohurd.py` 原 id 方案是 `md5(question|asked_at)[:16]`。
**同一天重复提问会撞 id** ⇒ 671 行里只有 612 个唯一 id，59 行「同 id 不同内容」。

适配器已改为 `md5(question|asked_at|answer)[:16]`（2026-10-09），
但**已采的 671 条沿用旧 id**，去重脚本删不掉（内容不同）。

本脚本就地重算这 671 条的 id（用新方案），使全库唯一。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def main() -> int:
    targets = list(DATA.glob("nat-mohurd-*.jsonl"))
    if not targets:
        print("找不到 nat-mohurd 数据文件")
        return 1
    p = targets[0]
    rows = []
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip() or not line.lstrip().startswith("{"):
                continue
            try:
                rows.append(json.loads(line))
            except Exception:                                           # noqa: BLE001
                continue

    before = len({str(r.get("id")) for r in rows})
    changed = 0
    # ⚠ 同一 (question, asked_at, answer, user) 视为同一条 ⇒ 只保留首次出现。
    #   本站部分记录 question 为空，此时该四元组退化成 (空,日期,答复,空)，
    #   不同用户/不同页位置的记录会撞在一起（2026-10-10 发现 1 组）。
    seen: set[tuple] = set()
    kept: list[dict] = []
    dropped = 0
    for r in rows:
        ex = r.get("extra") or {}
        user = (ex.get("user") if isinstance(ex, dict) else "") or ""
        key = (r.get("question") or "", r.get("asked_at") or "",
               r.get("answer") or "", user)
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        new_id = hashlib.md5("|".join(key).encode("utf-8")).hexdigest()[:16]
        if r.get("id") != new_id:
            r["id"] = new_id
            changed += 1
        kept.append(r)
    rows = kept

    after = len({str(r.get("id")) for r in rows})
    with open(p, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"{p.name}")
    print(f"  {len(rows) + dropped} 行：唯一 id {before} → {after}"
          f"（重算 {changed} 条，按内容去重删 {dropped} 条）")
    print("  " + ("✅ 无碰撞" if after == len(rows) else f"❌ 仍有 {len(rows) - after} 条碰撞"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
