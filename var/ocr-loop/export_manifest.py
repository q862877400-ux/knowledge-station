# -*- coding: utf-8 -*-
"""导出「可入库清单」（主项目与本子项目之间的**通道**，见 CONTRACT.md §5）。

**为什么需要**：主项目**不应该理解本子项目的内部状态**。本脚本把 state 翻译成
一份**幂等、可重生成**的 manifest，主项目只读 manifest + 产物目录即可入库。

判据（"没问题"的口径，与 CONTRACT §5 一致）：
  · `status == ok`（或 textlayer，按需）；
  · 产物目录 `parse_out/_land_key(std_no)` 存在且**非空**（空目录是失败残留）；
  · 显式标注**有意排除**：巨型跳过、留出集（locked，本就不参与）。

只读 + 只写一份 manifest JSON；不写库、不动产物。
用法：
  python var/ocr-loop/export_manifest.py                # 写 evolve/ingest_manifest.json
  python var/ocr-loop/export_manifest.py --out X.json   # 指定输出
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import next_batch as NB      # noqa: E402
import vlm_ocr as V          # noqa: E402

STATE = HERE / "vlm_ocr_state.json"
EV = HERE / "evolve"


def land_ok(std_no: str) -> str:
    """产物落位目录（存在且非空才返回路径，否则返回空串）。"""
    d = V.parse_out() / V._land_key(std_no)
    try:
        if d.is_dir() and any(d.iterdir()):
            return str(d)
    except OSError:
        return ""
    return ""


def build(include_textlayer: bool = False) -> dict:
    st = json.loads(STATE.read_text(encoding="utf-8"))
    want = {"ok"} | ({"textlayer"} if include_textlayer else set())
    items, no_product = [], []
    for key, rec in st.items():
        if not isinstance(rec, dict):
            continue
        if rec.get("status") not in want:
            continue
        std = str(rec.get("std_no") or key)
        d = land_ok(std)
        if not d:
            no_product.append(std)
            continue
        items.append({"std_no": std, "product_dir": d,
                      "status": str(rec.get("status")),
                      "pages": rec.get("pages"),
                      "channel": rec.get("channel"),
                      "nonempty": True})
    # 有意排除（标注出来，避免被当成缺口）
    try:
        hold = json.loads((EV / "holdout.json").read_text(encoding="utf-8"))
        n_hold = len(hold.get("paths") or [])
    except Exception:  # noqa: BLE001
        n_hold = 0
    try:
        over = json.loads((HERE / "vlm_oversize_skipped.json").read_text(
            encoding="utf-8"))
        n_over = len(over)
    except Exception:  # noqa: BLE001
        n_over = 0
    try:
        by = {V._land_key(p.stem) for p in NB.CORPUS.rglob("*.pdf")}
        n_pdf = len(by)
    except Exception:  # noqa: BLE001
        n_pdf = 0
    return {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "var/ocr-loop",
        "contract": "var/ocr-loop/CONTRACT.md",
        "rule": "status=ok 且产物目录存在且非空；有意排除见 excluded",
        "corpus_pdf_files": n_pdf,
        "items": sorted(items, key=lambda x: x["std_no"]),
        "count": len(items),
        "ok_but_no_product": sorted(no_product),
        "excluded": {"holdout_locked": n_hold, "oversize_skipped": n_over,
                     "note": "留出集永久不参与；巨型为用户决定跳过"},
        "note": "入库前请按 doc_meta.file_path 去重（库内已用）",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EV / "ingest_manifest.json"))
    ap.add_argument("--textlayer", action="store_true",
                    help="把 textlayer 也算作可入库")
    a = ap.parse_args()
    m = build(include_textlayer=a.textlayer)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"可入库条目: {m['count']}")
    print(f"  ok 但产物缺失: {len(m['ok_but_no_product'])}")
    print(f"  有意排除: 留出集 {m['excluded']['holdout_locked']} · "
          f"巨型 {m['excluded']['oversize_skipped']}")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
