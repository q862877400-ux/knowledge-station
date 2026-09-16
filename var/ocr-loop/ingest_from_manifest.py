# -*- coding: utf-8 -*-
"""小批入库验证：用 manifest 的**已有产物目录**入库 N 部（默认 10），零重解析。

契约见 `var/ocr-loop/CONTRACT.md` §5；实现入口见
`src/core/ingestion/pipeline.run_full_ingest(..., product_dir=...)`（2026-09-16 新增）。

**必须有的 `__main__` 保护**：项目用 multiprocessing spawn 起解析子进程，
顶层直接跑会触发 `_check_not_importing_main()`（我上一版探针就栽在这）。

用法：
  python var/ocr-loop/ingest_from_manifest.py --limit 10
  python var/ocr-loop/ingest_from_manifest.py --limit 10 --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "var" / "ocr-loop"))

MAN = ROOT / "var" / "ocr-loop" / "evolve" / "ingest_manifest.json"


def find_pdf(std_no: str, corpus: Path) -> Path | None:
    for p in corpus.rglob("*.pdf"):
        if p.stem == std_no:
            return p
    return None


def split_std(std: str) -> tuple[str, str]:
    """`GB 11660-1989 炼铁厂…` → ('GB 11660-1989', '炼铁厂…')。

    标准号是**两段**（前缀 + 数字年份），只取第一段会得到 'GB'（我第一版就这么错了）。
    前缀族含全角斜杠 `／`（语料命名如此）。
    """
    toks = std.split(" ")
    head = ("GB", "GB／T", "GB/T", "GB／Z", "GB/Z", "GBZ", "GBT")
    if len(toks) >= 2 and toks[0] in head:
        return f"{toks[0]} {toks[1]}", " ".join(toks[2:]) or toks[1]
    return toks[0], " ".join(toks[1:]) or toks[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip", type=int, default=0, help="跳过前 N 条（续跑用）")
    ap.add_argument("--chunk", type=int, default=300,
                    help="每段处理 N 部后主动退出（分段回收内存）；0=不分段。"
                         "背景：实测长跑内存会累积（1,518 部时达 9GB，"
                         "另一段 30 部即 4.4GB），有 OOM 风险且会拖慢吞吐。"
                         "分段后由外层循环重启进程，累积状态定期清掉。")
    a = ap.parse_args()

    import next_batch as NB  # noqa: PLC0415
    from src.core.ingestion.pipeline import run_full_ingest  # noqa: PLC0415

    m = json.loads(MAN.read_text(encoding="utf-8"))
    items = m["items"][a.skip:a.skip + a.limit]
    print(f"manifest 共 {m['count']} 条；本批 {len(items)} 部"
          f"（skip={a.skip}, dry_run={a.dry_run}）")

    ok = err = dup = 0
    for i, it in enumerate(items, 1):
        std = it["std_no"]
        pd = Path(it["product_dir"])
        pdf = find_pdf(std, NB.CORPUS)
        if pdf is None:
            print(f"  [{i}] 跳过（语料里找不到 PDF）: {std[:50]}")
            err += 1
            continue
        parts = std.split(" ", 1)
        std_no, std_name = split_std(std)
        if a.dry_run:
            print(f"  [{i}] DRY {std_no} ← {pd.name[:46]}")
            ok += 1
            continue
        try:
            res = run_full_ingest(pdf, std_no, std_name,
                                  force_deep=False, product_dir=pd)
        except Exception as e:  # noqa: BLE001
            import traceback  # noqa: PLC0415
            print(f"  [{i}] ✗ 异常 {std_no}: {type(e).__name__}: {e}")
            print("      " + traceback.format_exc().replace("\n", "\n      ")[:1200])
            err += 1
            continue
        st = str(res.get("status"))
        if st in ("ok", "success"):
            ok += 1
            print(f"  [{i}] ✓ {std_no}  clauses={res.get('clauses')} "
                  f"doc_id={res.get('doc_id')}")
        elif st == "duplicate":
            dup += 1
            print(f"  [{i}] = 重复（已在库） {std_no}")
        else:
            err += 1
            print(f"  [{i}] ✗ {std_no} status={st} msg={str(res.get('message'))[:80]}")

        # **分段回收**：到量即主动退出，让外层重启一个干净进程。
        if a.chunk and i >= a.chunk:
            print(f"\n[分段回收] 本段已处理 {i} 部 → 主动退出（清掉累积内存）。"
                  f"\n  续跑：python -u var/ocr-loop/ingest_from_manifest.py "
                  f"--limit {a.limit} --skip {a.skip + i} --chunk {a.chunk}")
            break

    print(f"\n小批结果：成功 {ok} · 重复 {dup} · 失败 {err} / 共 {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
