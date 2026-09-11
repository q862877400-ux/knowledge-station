# -*- coding: utf-8 -*-
"""Deterministic oracle scorer (loop2 step 1).

Consumes the ``snapshot.json`` produced by ``oracle_snapshot.py`` and computes THREE
fail-closed fidelity metrics, then emits ``verdict.json``:

  1. ``text_fidelity``       — per-page normalized edit-distance ratio of the PREVIEW
                              (clause content_text, page-mapped via page_breaks) vs the
                              ORIGINAL PDF text layer. Only content pages are compared;
                              pages whose PDF text layer is empty (scanned) are ``na``.
  2. ``page_map_fidelity``   — clause page endpoints vs doc page geometry alignment.
  3. ``object_presence``     — per-page figures/tables/formulas present in the preview vs
                              embedded images in the PDF. MARKED report-only in step 1
                              (noisy: logos/watermarks count as images) until calibrated.

All thresholds are configurable via env (defaults are deliberately conservative and
tagged ``calibration_pending``; step 2 sets the real cutoffs on real data).

CLI:
  python scripts/loop2/oracle_score.py [--snapshot <snapshot.json>] [--out <dir>] [--json]
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

# Repo root.
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # noqa: E402
    sys.path.insert(0, str(REPO))

from scripts.loop2.oracle_snapshot import _norm  # noqa: E402


def _threshold(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default


class Config:
    # TODO(calibrate, step 2): set real cutoffs on real data.
    TEXT_FIDELITY_MIN = _threshold("LOOP2_TEXT_FIDELITY_MIN", 0.90)  # calibration_pending
    PAGE_MAP_ON = True
    OBJECT_PRESENCE_GATE = _threshold("LOOP2_OBJECT_PRESENCE_GATE", 0.0)  # 0 = report-only


def _content_pages(snapshot: dict) -> set[int]:
    pages = set()
    for c in snapshot.get("clauses", []):
        pb = c.get("page_breaks")
        if pb:
            pages |= {p for _, p in pb}
        else:
            ps = int(c.get("page_start") or 1)
            pe = int(c.get("page_end") or ps)
            pages |= set(range(ps, pe + 1))
    return pages


def _ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def score_text(snapshot: dict) -> dict:
    # JSON round-trip stringifies dict keys; normalize both sides back to int pages.
    orig = {int(k): v for k, v in snapshot.get("orig_text_by_page", {}).items()}
    prev_map = {int(k): v for k, v in snapshot.get("preview_page_lines", {}).items()}
    content_pages = sorted(_content_pages(snapshot))
    per_page: dict[int, float] = {}
    missing: list[int] = []
    na: list[int] = []
    for p in content_pages:
        o = orig.get(p, "")
        prev_join = "\n".join(prev_map.get(p, []))
        if not o.strip():
            na.append(p)  # scanned / no text layer
            continue
        if not prev_join.strip():
            missing.append(p)  # PDF has text but preview assigned nothing -> real bug
            continue
        per_page[p] = round(_ratio(prev_join, o), 4)
    # fail-closed: PDF text exists but preview missing it => hard fail, regardless of
    # whether any page produced a measurable ratio.
    if missing:
        return {
            "content_pages": content_pages,
            "per_page": {str(k): v for k, v in per_page.items()},
            "na_pages": na,
            "missing_content_pages": missing,
            "min": round(min(per_page.values()), 4) if per_page else None,
            "mean": round(sum(per_page.values()) / len(per_page), 4) if per_page else None,
            "pass": False,
        }
    vals = list(per_page.values())
    # No measurable pages and no missing (all na because the source PDF has no text
    # layer) => the text-fidelity gate is not independently checkable: report
    # pass=None (non-blocking). Only once a page is measurable do we gate on ratio.
    if not vals:
        return {
            "content_pages": content_pages,
            "per_page": {},
            "na_pages": na,
            "missing_content_pages": [],
            "min": None,
            "mean": None,
            "na": True,
            "pass": None,
        }
    return {
        "content_pages": content_pages,
        "per_page": {str(k): v for k, v in per_page.items()},
        "na_pages": na,
        "missing_content_pages": [],
        "min": round(min(vals), 4),
        "mean": round(sum(vals) / len(vals), 4),
        "pass": (min(vals) >= Config.TEXT_FIDELITY_MIN),
    }


def score_pagmap(snapshot: dict) -> dict:
    doc_pc = snapshot.get("page_count")
    clauses = snapshot.get("clauses", [])
    starts = [int(c.get("page_start") or 1) for c in clauses]
    ends = [int(c.get("page_end") or (c.get("page_start") or 1)) for c in clauses]
    used_min = min(starts) if starts else None
    used_max = max(ends) if ends else None
    aligned = (doc_pc is not None
               and used_min is not None and used_min >= 1
               and used_max is not None and used_max <= doc_pc)
    return {
        "doc_page_count": doc_pc,
        "clause_page_min": used_min,
        "clause_page_max": used_max,
        "aligned": bool(aligned),
        "pass": bool(aligned) if Config.PAGE_MAP_ON else True,
    }


def score_objects(snapshot: dict) -> dict:
    # Preview: per-clause object counts assigned to their page_start.
    present = {"figures": {}, "tables": {}, "formulas": {}}
    for c in snapshot.get("clauses", []):
        p = int(c.get("page_start") or 1)
        for key in present:
            n = int(c.get(key) or 0)
            if n:
                present[key][p] = present[key].get(p, 0) + n
    # Expected figures from MinerU layout objects (middle.json). When absent (no deep
    # parse) we cannot determine what should be there => na (non-gating).
    expected_figs = {int(k): v for k, v in
                     snapshot.get("expected_figure_count_by_page", {}).items()}
    if not expected_figs:
        return {
            "present": present,
            "expected_figure_count_by_page": {},
            "missing_figure_pages": [],
            "na": True,
            "pass": True,
            "gated": False,
        }
    missing_fig_pages = sorted(
        p for p, n in expected_figs.items() if n > 0 and present["figures"].get(p, 0) == 0)
    report = {
        "present": present,
        "expected_figure_count_by_page": {str(k): v for k, v in expected_figs.items()},
        "missing_figure_pages": missing_fig_pages,
        "na": False,
    }
    # Step 1/2: report-only unless explicitly gated.
    report["pass"] = (Config.OBJECT_PRESENCE_GATE <= 0.0 or not missing_fig_pages)
    report["gated"] = Config.OBJECT_PRESENCE_GATE > 0.0
    return report


def score(snapshot: dict) -> dict:
    text = score_text(snapshot)
    pg = score_pagmap(snapshot)
    obj = score_objects(snapshot)
    # pass=None on text_fidelity => not gated (na), so it never blocks.
    text_ok = (text["pass"] if text["pass"] is not None else True)
    overall = text_ok and pg["pass"] and obj["pass"]

    # Deterministic gate applies to text-layer books. A SCANNED book (no text layer)
    # cannot be independently text/object-gated -> `needs_visual` tells the loop to
    # route it to VLM/visual verification (or the architecture block) instead of a
    # trivially "true" deterministic pass.
    tls = snapshot.get("text_layer_state")
    if tls in ("clean", "pua_mangled"):
        mode = "textlayer"
    elif tls == "scan":
        mode = "scan"
    else:
        mode = "scan" if text.get("pass") is None else "textlayer"
    needs_visual = mode == "scan"

    return {
        "doc_id": snapshot.get("doc_id"),
        "standard_no": snapshot.get("standard_no"),
        "page_count": snapshot.get("page_count"),
        "text_layer_state": tls,
        "mode": mode,
        "needs_visual": needs_visual,
        "text_fidelity": text,
        "page_map_fidelity": pg,
        "object_presence": obj,
        "pass": bool(overall),
        "thresholds": {
            "TEXT_FIDELITY_MIN": Config.TEXT_FIDELITY_MIN,
            "PAGE_MAP_ON": Config.PAGE_MAP_ON,
            "OBJECT_PRESENCE_GATE": Config.OBJECT_PRESENCE_GATE,
        },
        "calibration_pending": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", default=str(
        Path(os.environ.get("APPDATA", ".")) / "KnowledgeStation" / "loop2" / "snapshot.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", action="store_true", dest="as_json")
    a = ap.parse_args()
    snap_path = Path(a.snapshot)
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    verdict = score(snap)

    if a.as_json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    else:
        print(f"doc        : {verdict['doc_id']}  {verdict['standard_no']}")
        print(f"pages      : {verdict['page_count']}")
        t = verdict["text_fidelity"]
        print(f"text_fit   : min={t['min']} mean={t['mean']} "
              f"na={len(t['na_pages'])} missing={t['missing_content_pages']} pass={t['pass']}")
        m = verdict["page_map_fidelity"]
        print(f"page_map   : range=[{m['clause_page_min']},{m['clause_page_max']}] "
              f"aligned={m['aligned']} pass={m['pass']}")
        o = verdict["object_presence"]
        print(f"objects    : missing_fig_pages={o['missing_figure_pages']} "
              f"gated={o['gated']} pass={o['pass']}")
        print(f"PASS       : {verdict['pass']}   (calibration_pending)")

    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "verdict.json").write_text(
            json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
