"""按**来源前缀**抽查 IGI 整省源的 answer 质量与三级归属覆盖（通用版）。

## 为什么另写一个（而不是改 `audit-igi-new.py`）
`audit-igi-new.py` 把 4 个文件名**硬编码**在 `FILES` 里（2026-10-08 那批）。
IGI 整省源（`sx-igi` / `gx-igi` / `nx-igi` / `nmg-igi` / `gz-igi`）是**每个 siteId 一个文件**、
动辄几十上百个 ⇒ 必须按前缀 glob，不能枚举文件名。

判据沿用本模块已确立的（`SITE-REGISTRY` §一·补）：
空答复 / 答复 == 问题 / 答复 < 10 字 / 答复像问题 / 代码噪声 / 重复 id。
另统计 `extra.province/city/area` 的非空覆盖（三级归属是本模块唯一能扩「县」的来源）。

## 用法
```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe
$P tools/gov-qa/recon/audit-igi-prov.py nmg-igi gz-igi        # 指定前缀
$P tools/gov-qa/recon/audit-igi-prov.py nmg-igi --samples 3   # 另打 3 条疑点样本
```
**只读，不改任何文件**（不落盘报告；要留痕就把输出抄进台账 —— `recon/*.txt` 不在版本控制里）。
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

Q_END = re.compile(r"[?？]\s*$")
NOISE = re.compile(r"^\s*(function|var |<script|<!DOCTYPE|&nbsp;)", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prefixes", nargs="+", help="来源前缀，如 nmg-igi gz-igi")
    ap.add_argument("--samples", type=int, default=0, help="打印 N 条疑点样本")
    args = ap.parse_args()

    for prefix in args.prefixes:
        files = sorted(glob.glob(str(DATA / f"{prefix}-*.jsonl")))
        if not files:
            print(f"[{prefix}] 无数据文件")
            continue
        total = 0
        ids: dict[str, str] = {}
        dup = 0
        empty = eq = short = like_q = noise = 0
        geo = Counter()          # province/city/area 非空个数
        sources = Counter()
        samples: list[str] = []
        for fn in files:
            for line in Path(fn).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                total += 1
                sources[r.get("source", "?")] += 1
                rid = str(r.get("id"))
                if rid in ids:
                    dup += 1
                else:
                    ids[rid] = fn
                q = (r.get("question") or "").strip()
                a = (r.get("answer") or "").strip()
                e = r.get("extra") or {}
                for k in ("province", "city", "area"):
                    if (e.get(k) or "").strip():
                        geo[k] += 1
                bad = None
                if not a:
                    empty += 1
                    bad = "空答复"
                elif a == q:
                    eq += 1
                    bad = "答复==问题"
                elif len(a) < 10:
                    short += 1
                    bad = "答复<10字"
                elif Q_END.search(a) and not Q_END.search(q):
                    like_q += 1
                    bad = "答复像问题"
                elif NOISE.match(a):
                    noise += 1
                    bad = "代码噪声"
                if bad and len(samples) < args.samples:
                    samples.append(f"    [{bad}] {r.get('source')} id={rid} a={a[:60]!r}")

        print(f"[{prefix}] 文件 {len(files)} 个 / 记录 {total} 条 / 唯一 id {len(ids)} / 重复 {dup}")
        print(f"    疑点：空答复 {empty}｜答复==问题 {eq}｜<10字 {short}｜像问题 {like_q}｜噪声 {noise}")
        if total:
            print(f"    地域非空：province {geo['province']}（{geo['province']/total:.0%}）"
                  f"｜city {geo['city']}（{geo['city']/total:.0%}）"
                  f"｜area {geo['area']}（{geo['area']/total:.0%}）")
        print(f"    source 分布：{len(sources)} 个（top5 "
              f"{sources.most_common(5)}）")
        for s in samples:
            print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
