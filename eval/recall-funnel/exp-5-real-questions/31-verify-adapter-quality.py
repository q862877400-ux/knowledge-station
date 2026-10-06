"""核验适配层原型的**输出质量**：条款号像不像样、条文内容对不对。

上一轮原型已证明：**切出 0 条从 18% 降到 0%**，中位 52 条/本。
但那是**数量**；本脚本核**质量**：
 ① `SplitClause.number` 的形态（应为 `3.1` / `4.2.1` / `A.1` 这类）；
 ② 条文正文抽样（应是人能读的标准条文，不是乱码/空壳）；
 ③ 表格有没有绑上（`bind_table_number` / `table_html`）；
 ④ 与 `markdown.md` 那条路的产出对照（同样两本，看差多少）。

只读源目录；不连库、不写库。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\31-verify-adapter-quality.py --n 6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "adapter-quality.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"

from importlib import import_module                                   # noqa: E402
conv_mod = import_module("30-adapter-prototype") if False else None    # 占位，下面直接导入函数

# 直接复用 30 号脚本里的转换函数（文件名以数字开头，不能用 import 语句）
import importlib.util                                                 # noqa: E402
spec = importlib.util.spec_from_file_location("adapter30", HERE / "30-adapter-prototype.py")
adapter30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter30)
convert = adapter30.convert

NUM_OK = re.compile(r"^(\d+(\.\d+){0,4}|[A-Z]\.\d+(\.\d+){0,3})$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()

    from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses

    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
            and (d / "middle_json.json").exists()]
    # 挑安全类（与 EHS 提问相关）优先
    dirs.sort(key=lambda d: (0 if re.search(r"GB (30871|50016|39800|33625|15603|18218)", d.name) else 1,
                             d.name))
    tmpdir = Path(tempfile.mkdtemp(prefix="ks-40q-"))
    rows = []
    allnum = Counter()
    for d in dirs[:args.n]:
        mj = json.loads((d / "middle_json.json").read_text(encoding="utf-8", errors="ignore"))
        tf = tmpdir / (d.name[:60].replace(" ", "_") + ".json")
        tf.write_text(json.dumps(convert(mj), ensure_ascii=False), encoding="utf-8")
        items, _ = load_middle_items(tf)
        split = split_items_into_clauses(items)
        nums = [c.number for c in split]
        good = sum(1 for n in nums if NUM_OK.match(n or ""))
        with_tbl = sum(1 for c in split if c.table_html)
        bodies = []
        for c in split:
            t = " ".join(c.texts).strip()
            if len(t) > 40:
                bodies.append((c.number, t[:110].replace("\n", " ")))
        allnum.update(nums)
        rows.append({"dir": d.name[:52], "clauses": len(split),
                     "numbers_look_valid": f"{good}/{len(nums)}",
                     "with_table_html": with_tbl,
                     "sample_numbers": nums[:10],
                     "sample_bodies": bodies[:3]})
        print(f"\n=== {d.name[:60]} ===")
        print(f"    条款 {len(split)} 条；条款号形态合法 {good}/{len(nums)}；绑了表格的 {with_tbl} 条")
        print(f"    前 10 个条款号：{nums[:10]}")
        for no, t in bodies[:3]:
            print(f"      [{no}] {t}")

    # 条款号形态总览
    print("\n=== 全部条款号的形态（前 20 种）===")
    for k, v in allnum.most_common(20):
        print(f"    {k!r:12s} {v}")

    OUT.write_text(json.dumps({
        "why": "核验适配层原型的输出质量（条款号形态 + 条文正文 + 表格绑定）",
        "docs": rows,
        "number_distribution_top20": dict(allnum.most_common(20)),
        "boundary": ["只读源目录；未连库、未写库。", "条款号形态用正则判，不代表内容正确。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
