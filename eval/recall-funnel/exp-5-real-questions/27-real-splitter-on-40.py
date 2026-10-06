"""关键实测：**生产切分器（读 `middle_json.json`）在 MinerU 4.0 产物上到底行不行。**

## 为什么必须做这一步（业主 2026-10-07 的线索）
业主说："这种后处理原先 KS 已经做了很多了，但是那时候 MinerU 还是 3.4 版本不是现在用的 4.0"。
⇒ 我上一轮试跑走的是 `law_text.py`（**法条纯文本通道**，读 `markdown.md`），
   **那不是国标的正经入库路径**。正经路径在 `pipeline.py`：
  `load_middle_items(middle_json)` → `split_items_into_clauses(items, standard_no=…)`，
  而且里面**本来就有** `_CHAPTER_CLAUSE`（章头 `7 技术要求`）、`_CLAUSE_APPENDIX`（`A.1`）、
  防误切闸门、目录/索引过滤，还有一句注释"还原 MinerU 吞点的条款号 41→4.1"。

本脚本：**直接拿 4.0 的 middle_json 喂给这套生产切分器**，量它切出多少条、有没有报错。
**只读源目录；不连库、不写任何东西。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\27-real-splitter-on-40.py --n 5
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "real-splitter-on-40.json"
sys.path.insert(0, str(ROOT))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    args = ap.parse_args()

    from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses

    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)]
    print(f"[real] MinerU 产物目录 {len(dirs)} 个\n", flush=True)

    ok, fail, rows = 0, 0, []
    for d in dirs[:args.n]:
        mj = d / "middle_json.json"
        if not mj.exists():
            print(f"    {d.name[:56]:56s} ⛔ 没有 middle_json.json")
            fail += 1
            continue
        # 先看 middle_json 的顶层结构（判断 4.0 与 3.4 是否同构）
        try:
            raw = json.loads(mj.read_text(encoding="utf-8", errors="ignore"))
            keys = list(raw.keys())[:8] if isinstance(raw, dict) else f"list[{len(raw)}]"
        except Exception as e:                                              # noqa: BLE001
            keys = f"解析失败 {type(e).__name__}"
        try:
            items, page_sizes = load_middle_items(mj)
            split = split_items_into_clauses(items)
            n_items, n_clauses = len(items), len(split)
            ok += 1
            head = [s[0] if isinstance(s, (list, tuple)) else getattr(s, "clause_number", "?")
                    for s in split[:8]]
            rows.append({"dir": d.name[:56], "middle_keys": keys, "items": n_items,
                         "clauses": n_clauses, "head": head})
            print(f"    {d.name[:52]:52s} items {n_items:5d} ⇒ 条款 {n_clauses:5d}  "
                  f"前几个号 {head}", flush=True)
        except Exception as e:                                              # noqa: BLE001
            fail += 1
            rows.append({"dir": d.name[:56], "middle_keys": keys,
                         "error": f"{type(e).__name__}: {e}",
                         "tb": traceback.format_exc()[-600:]})
            print(f"    {d.name[:52]:52s} ⛔ {type(e).__name__}: {str(e)[:90]}", flush=True)
        print(f"         middle_json 顶层键 = {keys}", flush=True)

    print(f"\n[real] 成功 {ok} / 失败 {fail}")
    OUT.write_text(json.dumps({
        "why": "实测生产切分器（读 middle_json）在 MinerU 4.0 产物上的表现",
        "note": "上一轮走的是 law_text.py（读 markdown.md），不是国标的正经入库路径",
        "success": ok, "fail": fail, "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
