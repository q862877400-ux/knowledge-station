"""字段体检 —— spec 004 的 US3。

对应 FR-015 / FR-016 / SC-008。

## 它要发现什么

**「整列全空」这类静默缺陷** —— 数据看起来有 36 万条，但某个关键字段其实全是空的，
或者「问题与答复同时为空」这种废记录混在里面。

实测已发现的例子：`nat-mohurd` 部分记录 `question` 为空（但 `answer` 有内容），
根因是明细页解析漏了问题正文。

## 用法

```bash
$P tools/gov-qa/recon/field-audit.py              # 人类可读
$P tools/gov-qa/recon/field-audit.py --quiet      # 纯 ASCII
$P tools/gov-qa/recon/field-audit.py --samples 5  # 附样本
```

**只读，不改任何数据。**
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import ascii_kv, human, iter_records                 # noqa: E402

DATA = ROOT / "data"

#: 关键字段（非空率必须关注）
KEY_FIELDS = ("source", "id", "question", "answer", "asked_at", "answered_at", "dept")


def main() -> int:
    ap = argparse.ArgumentParser(description="字段体检（spec 004 US3）")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII 机器可读")
    ap.add_argument("--samples", type=int, default=0, help="附 N 条异常样本")
    ap.add_argument("--by-source", action="store_true", help="按来源列出 q 为空的")
    args = ap.parse_args()

    total = 0
    nonempty: Counter = Counter()
    q_empty_a_ok: list[dict] = []          # question 空但 answer 有
    both_empty = 0                          # 问题与答复同时为空（SC-008 要求 0）
    q_empty_by_source: Counter = Counter()
    missing_id = 0

    for rec in iter_records(str(DATA / "*.jsonl")):
        total += 1
        for f in KEY_FIELDS:
            v = rec.get(f)
            if v not in (None, "", [], {}):
                nonempty[f] += 1

        q = (rec.get("question") or "").strip()
        a = (rec.get("answer") or "").strip()
        src = str(rec.get("source") or "?")
        if not q and not a:
            both_empty += 1
        elif not q and a:
            q_empty_by_source[src] += 1
            if len(q_empty_a_ok) < max(args.samples, 0):
                q_empty_a_ok.append(rec)
        if not str(rec.get("id") or "").strip():
            missing_id += 1

    if not total:
        human("无数据")
        return 0

    # ---- 纯 ASCII 输出 -------------------------------------------------
    if args.quiet:
        kv = {"TOTAL": total, "BOTH_EMPTY": both_empty, "MISSING_ID": missing_id,
              "Q_EMPTY_A_OK": sum(q_empty_by_source.values())}
        for f in KEY_FIELDS:
            kv[f"NONEMPTY_{f.upper()}"] = nonempty[f]
        ascii_kv(kv)
        return 0 if (both_empty == 0 and missing_id == 0) else 1

    # ---- 人类可读 ------------------------------------------------------
    human(f"字段体检 —— 共 {total:,} 条\n")
    human("字段非空率：")
    for f in KEY_FIELDS:
        pct = nonempty[f] / total * 100
        flag = " ⚠️ **整列异常**" if pct < 50 else ""
        human(f"  {f:14s} {nonempty[f]:9,d} / {total:,}  = {pct:6.2f}%{flag}")

    human("")
    human("异常检出：")
    human(f"  问题与答复**同时为空**：{both_empty:,} 条"
          f"{'  ✅' if both_empty == 0 else '  ❌ SC-008 要求 0'}")
    human(f"  id 为空：{missing_id:,} 条{'  ✅' if missing_id == 0 else '  ❌'}")
    n_qea = sum(q_empty_by_source.values())
    human(f"  问题为空但答复有内容：{n_qea:,} 条"
          f"{'  ✅' if n_qea == 0 else '  ⚠️ 需修（解析漏了问题正文）'}")

    if n_qea and args.by_source:
        human("")
        human("  按来源（前 15）：")
        for s, n in q_empty_by_source.most_common(15):
            human(f"    {s:26s} {n:7,d} 条")

    if q_empty_a_ok:
        human("")
        human(f"  样本（{len(q_empty_a_ok)} 条）：")
        for r in q_empty_a_ok:
            human(f"    [{r.get('source')}] url={(r.get('url') or '')[:70]}")

    return 0 if (both_empty == 0 and missing_id == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
