"""改后回归：用**生产代码**（不再走原型脚本）把真实 933 本国标跑一遍。

## 目的
修复前：`load_middle_items` 读 `mj.get("pdf_info", [])` ⇒ 4.0 产物**静默返回 0 条**（933/933 本 items=0）。
修复后：`middle_schema.load_middle_json` 把 4.0 归一成 3.4 形状 ⇒ 应当每本都切出条款。
本脚本走**生产路径**（`pipeline.load_middle_items`，无任何本地转换），确认修复真的生效。

对照基线 = 原型脚本 `30-adapter-prototype.py` 的结果：
 **933/933 成功、0 本切出 0 条、条款数中位 53、合计 69,517 条**。

只读源目录；不连库、不写库。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\32-regression-after-fix.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "regression-after-fix.json"
sys.path.insert(0, str(ROOT))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"


def main() -> int:
    from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses

    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
            and (d / "middle_json.json").exists()]
    print(f"[reg] 有 middle_json 的国标 {len(dirs)} 本\n", flush=True)

    ok, zero, err = 0, 0, 0
    counts: list[int] = []
    errors: list[dict] = []
    for i, d in enumerate(dirs, 1):
        try:
            items, _ = load_middle_items(d / "middle_json.json")
            split = split_items_into_clauses(items)
            ok += 1
            if not split:
                zero += 1
            counts.append(len(split))
        except Exception as e:                                              # noqa: BLE001
            err += 1
            errors.append({"dir": d.name[:58], "error": f"{type(e).__name__}: {e}"})
        if i % 100 == 0:
            print(f"    …{i}/{len(dirs)}  已切 {sum(counts)} 条", flush=True)

    n = max(1, ok)
    print(f"\n[reg] 成功 {ok}/{len(dirs)}；异常 {err}；**切出 0 条 {zero}/{n} = {zero/n:.1%}**")
    if counts:
        print(f"[reg] 条款数：中位 {int(st.median(counts))} / 最小 {min(counts)} / "
              f"最大 {max(counts)} / **合计 {sum(counts)}**")
        for thr in (1, 10, 50, 100):
            k = sum(1 for c in counts if c >= thr)
            print(f"        条款数 ≥ {thr:3d} 的本数：{k}/{n} ({k/n:.0%})")
    if errors:
        print("\n[reg] 异常样例（前 8）：")
        for e in errors[:8]:
            print(f"    {e['dir']}  ← {e['error'][:80]}")

    # 对照原型
    proto = HERE / "adapter-prototype.json"
    base = None
    if proto.exists():
        pj = json.loads(proto.read_text(encoding="utf-8"))
        base = {"success": pj.get("success"), "zero_clause": pj.get("zero_clause"),
                "clause_stats": pj.get("clause_stats")}
    OUT.write_text(json.dumps({
        "why": "修复后用生产代码回归 933 本国标（对照原型脚本的结果）",
        "production_path": "pipeline.load_middle_items → middle_schema.load_middle_json → split_items_into_clauses",
        "docs": len(dirs), "success": ok, "errors": err, "zero_clause": zero,
        "clause_stats": {"median": int(st.median(counts)) if counts else None,
                         "min": min(counts) if counts else None,
                         "max": max(counts) if counts else None,
                         "total": sum(counts) if counts else None},
        "prototype_baseline": base,
        "error_sample": errors[:20],
        "boundary": ["只读源目录；未连库、未写库。", "条款数只能证明'切出来了'，不等于内容正确。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
