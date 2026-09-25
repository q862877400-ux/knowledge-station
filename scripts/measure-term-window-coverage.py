"""量：术语**定义正文的长短结构**，用来判"多向量/切片"这条改造值不值得做。

为什么要有这个脚本（2026-09-25）：计划 P1 的"下一刀"是**上游粗排**——真术语用现成
嵌入排到全库 42,181 个术语的前 50 只有 **25.7%**、前 5 只有 **8.6%**，这是当前唯一的
硬天花板；计划里列了三个**未试**选项：换更强的嵌入 / **多向量** / 领域内微调。

其中"多向量"最像有救，理由是 `term_bridge.py` 把**整段定义 → 一个向量**，
而嵌入窗口只有 512 token（P0.10 实测）⇒ 长定义的**尾巴没进向量**，切片多向量能把尾巴捞回来。

**但这个理由成立与否，取决于定义到底有多长**——所以先量，别先写代码。
本脚本就是那把尺子：先量长度分布，再算"切片多向量最多能影响多少条说法"。
⇒ 实测结论：**这条改造在本库上最多只能影响 0.6% 的说法 ⇒ 量掉了，不必实现。**

⚠ 本脚本只量**长度/覆盖**，**不**量任何检索效果。它回答的是"这条改造**有没有可能**
起作用"，不是"它一定有用/没用"。要看效果得在 `measure-term-selection.py` 上做对照。

⚠ 它**只反驳"表示被截断"这个机制**（长定义的尾巴丢了）。它**不反驳** token 级
late interaction（ColBERT 那类）作为**细粒度匹配**手段的可能——那是另一回事，
本脚本没有涉及，别把它读成"多向量被否了"。

用法：
    .venv\\Scripts\\python.exe scripts\\measure-term-window-coverage.py [--slice-chars 450] [--cases 路径]
只读术语表缓存（没有就现场建，约 531s）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np                                          # noqa: E402

from src.core.retrieval.term_bridge import TermIndex        # noqa: E402

CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice-chars", type=int, default=450,
                    help="切片宽度（字符）。⚠ 1 汉字≈1 token 是**推断**；450 < 512 留余量")
    ap.add_argument("--cases", default=str(CASES), help="说法 JSONL（用来算'答案术语'的覆盖）")
    args = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):       # pragma: no cover - 环境相关
            pass

    index = TermIndex.load(CACHE) if CACHE.exists() else TermIndex.build(_ro_conn())
    print(f"术语表：{len(index):,} 条")
    lens = np.asarray([len(e.definition or "") for e in index.entries])

    print()
    print("定义正文长度（字符）：")
    for q in (50, 75, 90, 95, 99):
        print(f"  p{q:<3} {int(np.percentile(lens, q)):>6}")
    print(f"  max   {int(lens.max()):>6}")
    over = int((lens > args.slice_chars).sum())
    print(f"  > {args.slice_chars} 字（切片多向量才可能改变它们）：{over:,} 条（{over/len(lens):.2%}）")

    n_slices = int(np.maximum(np.ceil(lens / args.slice_chars), 1).sum())
    print(f"  切片总数 ≈ {n_slices:,}（单向量是 {len(index):,}）⇒ 嵌入量 ×{n_slices/len(index):.2f}")

    p = Path(args.cases)
    if not p.exists():
        print(f"\n（没有说法集 {p} ⇒ 跳过'答案术语覆盖'那一段）")
        return 0
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    pos = {e.term: i for i, e in enumerate(index.entries)}
    gold = [pos[r["term"]] for r in rows if r["term"] in pos]
    gl = lens[gold]
    n_multi = int((gl > args.slice_chars).sum())
    print()
    print(f"答案术语命中术语表 {len(gold)}/{len(rows)}")
    print(f"它们定义长度：中位 {int(np.median(gl))}、p90 {int(np.percentile(gl, 90))}、max {int(gl.max())}")
    # 每条说法都挂在某个术语上 ⇒ 覆盖按"说法数"算是等权的（这里按术语数，平均 3.66 条/术语）
    print(f"其中有 >{args.slice_chars} 字定义的：{n_multi}/{len(gold)} = {n_multi/len(gold):.1%}")
    print()
    print(f"⇒ **切片多向量最多只能影响 {n_multi/len(gold):.1%} 的说法**；"
          f"超过这个比例的部分，瓶颈**不在表示长度上**。")
    print("⚠ 这**只**否掉'表示被截断'这个机制，**不**否掉 token 级 late interaction。")
    return 0


def _ro_conn():
    import sqlite3
    db = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


if __name__ == "__main__":
    raise SystemExit(main())
