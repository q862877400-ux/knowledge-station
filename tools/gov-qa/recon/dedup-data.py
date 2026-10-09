"""数据去重 —— 清理重复的 `(source, id)` 行。

## 背景

`harvest.py` 的去重是**开跑时一次性读文件**建 `done` 集合，之后只按该快照过滤。
以下情况会让它失效、导致同一 `(source, id)` 被写多次：

1. **两路进程并发采同一个站** —— 双方读到同一初始状态，各写一份
   （2026-10-09 实测：浙江金华被两路并发写 ⇒ 6350 行 / 只有 3351 唯一）
2. **反复重跑而去重未生效** —— 实测 `gd-hr` 同一 id 被写了 **12 次**
3. 适配器绕过 harvest.py 自己写文件

首次全库扫描：**13 个来源存在重复，合计 8,284 行重复**（约占语料 4%）。

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/dedup-data.py --dry-run     # 先看会删多少（不改文件）
$P tools/gov-qa/recon/dedup-data.py               # 执行去重（原地改写）
$P tools/gov-qa/recon/dedup-data.py --key gd-hr   # 只处理某前缀
```

**安全保证**：
- 只删「`(source, id)` 相同**且内容完全相同**」的行，保留第一条
- 若同一 `(source, id)` 的**内容不同**，**不删**，只打印告警（那可能是 id 冲突，需要人工判断）
- **执行前请先 `git add` + commit**（本脚本不自动备份）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"


def main() -> int:
    ap = argparse.ArgumentParser(description="清理重复的 (source,id) 行")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不改文件")
    ap.add_argument("--key", default="", help="只处理文件名以该前缀开头的文件")
    args = ap.parse_args()

    total_removed = 0
    total_files = 0
    conflicts = 0

    for p in sorted(glob.glob(str(DATA / "*.jsonl"))):
        base = os.path.basename(p)
        if args.key and not base.startswith(args.key):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines = [ln for ln in fh if ln.strip() and ln.lstrip().startswith("{")]

        seen: dict[tuple[str, str], str] = {}   # (source,id) -> 首次出现的整行
        out: list[str] = []
        removed = 0
        for ln in lines:
            try:
                r = json.loads(ln)
            except Exception:                                       # noqa: BLE001
                out.append(ln)          # 解析不了就原样保留
                continue
            k = (str(r.get("source") or ""), str(r.get("id")))
            if k in seen:
                if seen[k] == ln:
                    removed += 1        # 精确重复 ⇒ 删
                else:
                    conflicts += 1      # 同 id 不同内容 ⇒ 保留 + 告警
                    out.append(ln)
                    print(f"  ⚠ {base}: (source,id)={k} 内容不同，已保留（需人工判断）")
                continue
            seen[k] = ln
            out.append(ln)

        if removed:
            total_files += 1
            total_removed += removed
            print(f"  {base[:56]:58s} {len(lines):7,d} → {len(out):7,d}  (删 {removed:,})")
            if not args.dry_run:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.writelines(out)

    print()
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}处理 {total_files} 个文件，"
          f"删除重复 {total_removed:,} 行；同 id 内容冲突 {conflicts} 处（未删）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
