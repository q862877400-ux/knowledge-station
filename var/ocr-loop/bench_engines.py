"""三臂速度对比：本地 pipeline(ch_server) vs 本地 VLM(vlm-engine) vs 云 API VLM。

同一批小 PDF、同一进程串行跑（避免 GPU 争用污染计时），逐文档计时并汇总
pages/s。产物各自落独立目录，便于事后比对质量（条款数/审计类）。

用法：python var/ocr-loop/bench_engines.py [--docs 3] [--cloud-only] [--local-only]
结果写 var/ocr-loop/bench_engines.json
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
VARDIR = Path(__file__).resolve().parent
LIB = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT")


def pick_docs(n: int) -> list[Path]:
    cands = []
    for seg in LIB.iterdir():
        if seg.is_dir():
            for f in seg.glob("*.pdf"):
                sz = f.stat().st_size
                if 20_000 < sz < 600_000:
                    cands.append((sz, f))
    cands.sort()
    seen, out = set(), []
    for _sz, f in cands:                      # 同一标准的两份副本只取一份
        key = f.stem.split("(")[0][:28]
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
        if len(out) >= n:
            break
    return out


def pages_of(pdf: Path) -> int:
    import fitz
    with fitz.open(pdf) as d:
        return d.page_count


def run_local(arm: str, backend: str, lang: str, docs: list[Path]) -> dict:
    from mineru.cli.common import do_parse
    out_root = Path(tempfile.mkdtemp(prefix=f"ks_bench_{arm}_"))
    recs = []
    total_pages = 0
    t_all = time.monotonic()
    for pdf in docs:
        n = pages_of(pdf)
        total_pages += n
        t0 = time.monotonic()
        try:
            do_parse(str(out_root), [pdf.stem], [pdf.read_bytes()], [lang],
                     backend=backend, parse_method="auto",
                     f_draw_layout_bbox=False, f_draw_span_bbox=False,
                     f_dump_orig_pdf=False, f_dump_model_output=False)
            err = ""
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:160]}"
        wall = time.monotonic() - t0
        recs.append({"doc": pdf.name[:46], "pages": n, "wall_s": round(wall, 1),
                     "pages_per_s": round(n / wall, 3) if wall else None, "error": err})
        print(f"  [{arm}] {pdf.name[:40]} {n}页 {wall:.1f}s "
              f"({n/wall:.2f} p/s){' ERR:' + err if err else ''}", flush=True)
    return {"arm": arm, "backend": backend, "lang": lang, "docs": recs,
            "pages": total_pages, "wall_s": round(time.monotonic() - t_all, 1),
            "pages_per_s": round(total_pages / (time.monotonic() - t_all), 3),
            "out_dir": str(out_root)}


def run_cloud(docs: list[Path]) -> dict:
    from src.core.config import reset_settings
    from src.core.ingestion.mineru_cloud import (mineru_cloud_submit_and_wait,
                                                 _model_version)
    reset_settings()                       # 确保读到最新模式
    out_root = Path(tempfile.mkdtemp(prefix="ks_bench_cloud_"))
    recs = []
    total_pages = 0
    t_all = time.monotonic()
    for idx, pdf in enumerate(docs, 1):
        n = pages_of(pdf)
        total_pages += n
        t0 = time.monotonic()
        try:
            # 输出子目录名只用安全短名：文件名截断会产生「尾随空格 + 全角／」
            # 这类 Windows 路径坑，会把 bench 自身的产物写入搞坏（2026-09-14
            # 实测：带尾随空格的截断目录导致 zip 落位失败被误报为网络失败）。
            r = mineru_cloud_submit_and_wait(pdf, out_root / f"d{idx}")
            err = "" if r is not None else "返回 None（网络/超时/守卫失败）"
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:160]}"
        wall = time.monotonic() - t0
        recs.append({"doc": pdf.name[:46], "pages": n, "wall_s": round(wall, 1),
                     "pages_per_s": round(n / wall, 3) if wall else None, "error": err})
        print(f"  [cloud-{_model_version()}] {pdf.name[:40]} {n}页 {wall:.1f}s "
              f"({n/wall:.2f} p/s){' ERR:' + err if err else ''}", flush=True)
    return {"arm": f"cloud-{_model_version()}", "backend": "cloud-api",
            "model_version": _model_version(), "docs": recs,
            "pages": total_pages, "wall_s": round(time.monotonic() - t_all, 1),
            "pages_per_s": round(total_pages / (time.monotonic() - t_all), 3),
            "out_dir": str(out_root)}


def main() -> None:
    args = sys.argv[1:]
    n = int(args[args.index("--docs") + 1]) if "--docs" in args else 3
    docs = pick_docs(n)
    print(f"对比文档 {len(docs)} 份：{[d.name[:34] for d in docs]}")
    total = sum(pages_of(d) for d in docs)
    print(f"总页数 {total}\n")

    results = []
    if "--cloud-only" not in args:
        print("== 臂 A：本地 pipeline + ch_server（现状）==")
        results.append(run_local("local-pipeline", "pipeline", "ch_server", docs))
        print("\n== 臂 B：本地 VLM（vlm-engine + MinerU2.5-Pro-1.2B）==")
        results.append(run_local("local-vlm", "vlm-engine", "ch", docs))
    if "--local-only" not in args:
        print("\n== 臂 C：云 API VLM ==")
        results.append(run_cloud(docs))

    print("\n=== 汇总 ===")
    for r in results:
        print(f"  {r['arm']:16} {r['pages']:3}页 {r['wall_s']:7.1f}s "
              f"{r['pages_per_s']:6.3f} pages/s")
    ranked = sorted([r for r in results if r.get("pages_per_s")],
                    key=lambda r: -r["pages_per_s"])
    if ranked:
        print(f"\n最快：{ranked[0]['arm']}（{ranked[0]['pages_per_s']} pages/s）")
    (VARDIR / "bench_engines.json").write_text(
        json.dumps({"docs": [str(d) for d in docs], "total_pages": total,
                    "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已写 var/ocr-loop/bench_engines.json")


if __name__ == "__main__":
    main()
