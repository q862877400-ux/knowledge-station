# -*- coding: utf-8 -*-
"""云 VLM 健康探针：单次提交 + 记录耗时，追加到 `cloud_health.jsonl`。

**为什么单独做它**（2026-09-15 实测）：云侧会**整体降级**——任务被接受、返回任务号、
然后**永不完成**（轮询超时）。此时区分"服务降级"与"某份文档解析不了"是排期决策的
关键：前者只能等或转本地，后者换文档/换 key 即可。实测判据：
  - **同一份 5 页新文档 × 三个 key 全部 154s 超时** → 服务降级（与 key、文档无关）；
  - 单份文档超时但换一份就成功 → 文档/内容问题。
故探针**固定用一份小文档**（参数 `--pdf`，默认自动取语料里最小的一份），
让"耗时"只反映服务状态。

调用一次 = 一次探针（不做常驻循环，便于由定时任务/人工触发）。

用法：
  python var/ocr-loop/cloud_health.py                 # 自动挑一份小 PDF
  python var/ocr-loop/cloud_health.py --pdf <路径>     # 指定文档（回归对照用）
  python var/ocr-loop/cloud_health.py --timeout 120
  python var/ocr-loop/cloud_health.py --report        # 只看历史，不发请求
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("KS_VLM_ONLY", "1")

OUT = HERE / "cloud_health.jsonl"
CORPUS = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")


def _default_pdf() -> Path:
    """语料里最小的一份 PDF（小文档最能暴露"服务是否响应"）。"""
    best: tuple[int, Path] | None = None
    n = 0
    for p in CORPUS.rglob("*.pdf"):
        n += 1
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if 20_000 < sz < 2_000_000 and (best is None or sz < best[0]):
            best = (sz, p)
        if n > 4000:          # 抽样即可，不必扫全库
            break
    if best is None:
        raise SystemExit("语料里找不到合适的小 PDF，请用 --pdf 指定")
    return best[1]


def report() -> None:
    if not OUT.exists():
        print("尚无探针记录")
        return
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"共 {len(rows)} 条探针记录（最近 20 条）")
    ok = [r for r in rows if r.get("ok")]
    print(f"成功 {len(ok)}/{len(rows)}")
    for r in rows[-20:]:
        mark = "OK " if r.get("ok") else "FAIL"
        print(f"  {r.get('ts')}  {mark}  {r.get('secs'):>7}s  {str(r.get('note'))[:60]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    if a.report:
        report()
        return

    import vlm_ocr as V
    from src.core.ingestion import mineru_cloud as MC

    pdf = Path(a.pdf) if a.pdf else _default_pdf()
    pool = V.keys_pool()
    rec: dict = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "pdf": str(pdf), "pdf_kb": round(pdf.stat().st_size / 1024),
                 "keys": [al for al, _ in pool]}
    per_key = []
    ok_any = False
    for alias, key in pool:
        V.use_key(key)
        d = Path(tempfile.mkdtemp(prefix=f"ks_health_{alias}_"))
        t0 = time.time()
        try:
            r = MC.mineru_cloud_submit_and_wait(pdf, d, timeout=a.timeout)
            secs, ok = time.time() - t0, bool(r)
            note = "" if ok else "轮询超时（任务被接受但未完成）"
        except Exception as ex:  # noqa: BLE001
            secs, ok = time.time() - t0, False
            note = f"{type(ex).__name__}: {str(ex)[:80]}"
        per_key.append({"key": alias, "secs": round(secs, 1), "ok": ok, "note": note})
        ok_any = ok_any or ok
        print(f"  {alias:<8} {'OK ' if ok else 'FAIL'} {secs:7.1f}s  {note}")
    rec.update({"ok": ok_any, "per_key": per_key,
                "secs": min(k["secs"] for k in per_key),
                "note": ("服务正常" if ok_any else
                         "**三个 key 全部超时 → 服务侧降级**（与 key、文档无关）")})
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\n结论：{rec['note']}  → {OUT.name}")
    print(f"判定口径：三 key 全超时 = 服务降级；某 key 成功 = 服务在，问题在 key/文档")


if __name__ == "__main__":
    main()
