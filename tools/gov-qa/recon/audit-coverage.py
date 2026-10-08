"""数据落盘核查 —— 对每个已登记适配器，核对它的数据文件里到底有多少条。

## 为什么需要它

本会话同一个失败模式出现了**三种形态**：
  1. 「适配器建好、抽验通过、已登记」但**从没启动采集**（worker-city 17 个市 / worker-national 3 个大源）
  2. 「采集任务已启动」但**被中断、没跑完**（四川第二批 10 个市只剩抽验的 3 条）
  3. 「文件存在」但里面是**抽验残留**，不是正式采集结果

⇒ 光看"任务已启动"、光看"文件存在"都不够。**唯一可信的判据是：数据文件里的行数。**

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/audit-coverage.py              # 全量核查（按省分组）
$P tools/gov-qa/recon/audit-coverage.py --empty      # 只看「零数据」的适配器
$P tools/gov-qa/recon/audit-coverage.py --thin 50    # 只看条数 < 50 的（疑似抽验残留）
$P tools/gov-qa/recon/audit-coverage.py --key js-    # 只看某前缀
```

**只读，不改任何文件。**
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/gov-qa/recon
ROOT = HERE.parent                              # tools/gov-qa
sys.path.insert(0, str(ROOT))


def count_lines(path: str) -> int:
    """数有效行（跳过采集进行中的半行）。"""
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip() and line.lstrip().startswith("{"):
                n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="数据落盘核查")
    ap.add_argument("--empty", action="store_true", help="只看零数据的适配器")
    ap.add_argument("--thin", type=int, default=0, help="只看条数 < N 的适配器")
    ap.add_argument("--key", default="", help="只看某前缀的 key")
    args = ap.parse_args()

    os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
    import adapters

    # 预先扫一遍 data/ 的条数（按文件名前缀聚合）
    counts: dict[str, int] = defaultdict(int)
    files: dict[str, list[str]] = defaultdict(list)
    for p in glob.glob(str(ROOT / "data" / "*.jsonl")):
        base = os.path.basename(p)
        n = count_lines(p)
        # 文件名形如 `<key>-<中文名>.jsonl`；取「第一个 '-' 之前」太粗（key 里也有 '-'）
        # ⇒ 用「最长前缀匹配」在下面按已登记 key 归类
        files[""].append(base)
        counts[base] = n

    keys = sorted(k for k in adapters.ADAPTERS if k.startswith(args.key) if True)
    rows = []
    for k in keys:
        mod = adapters.load(k)
        site = mod.SITE
        prefix = f"{site['key']}-"
        total = 0
        nf = 0
        for base in files[""]:
            if base.startswith(prefix):
                total += counts[base]
                nf += 1
        rows.append((k, site.get("name", ""), site.get("level", ""), total, nf))

    empty = [r for r in rows if r[3] == 0]
    thin = [r for r in rows if 0 < r[3] < (args.thin or 10**9)]

    print(f"已登记适配器 {len(rows)} 个；其中**零数据 {len(empty)} 个**、"
          f"薄（<{args.thin}）{len(thin) if args.thin else '-'} 个")
    print(f"数据总条数（按适配器聚合）：{sum(r[3] for r in rows):,}")
    print()

    if args.empty:
        print("=== 零数据（建好没采 / 采了没落盘）===")
        for k, name, lvl, tot, nf in empty:
            print(f"  {k:22s} {lvl:9s} {name}")
        return 0

    if args.thin:
        print(f"=== 薄数据（0 < 条数 < {args.thin}，疑似抽验残留）===")
        for k, name, lvl, tot, nf in thin:
            print(f"  {tot:6d}  {k:22s} {name}")
        return 0

    # 全量：按 level 分组
    for lvl in ("national", "province", "city", ""):
        grp = [r for r in rows if r[2] == lvl]
        if not grp:
            continue
        label = {"national": "国家级", "province": "省级", "city": "地市级", "": "其它"}[lvl]
        print(f"=== {label}（{len(grp)} 个，合计 {sum(r[3] for r in grp):,} 条）===")
        for k, name, _l, tot, nf in sorted(grp, key=lambda r: -r[3]):
            flag = "  ← 零数据" if tot == 0 else ("  ← 疑似抽验残留" if tot < 30 else "")
            print(f"  {tot:7d}  {k:24s} {name[:34]:36s}{flag}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
