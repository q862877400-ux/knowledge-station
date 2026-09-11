# -*- coding: utf-8 -*-
"""Deterministic per-doc structural snapshot builder (loop2 step 1).

Reads ONLY (never writes): clause_revision + source_span + doc_page_geometry via
``get_db_connection()``, and the source PDF via PyMuPDF. Builds a machine-readable
structural snapshot of the PREVIEW (the right-pane ``.fulltext`` rebuild) so that
``oracle_score.py`` can compute deterministic, fail-closed fidelity metrics.

Design constraints honored:
  - No schema change (frozen schema untouched; reads only).
  - No bbox write / no H-y flip (bottom-origin contract untouched).
  - No evidence-text modification (content_text read verbatim).
  - No browser; no server dependency (the engine need not be running).
  - No absolute paths baked in (paths come from get_settings() or CLI).

Output (``snapshot.json``): doc id/std, doc page count + page geometry, per-clause
page endpoints + page_breaks, preview page->lines map, and (if a source PDF is
provided/found) the per-page original text layer + embedded image counts.

CLI:
  python scripts/loop2/oracle_snapshot.py --doc-id <id> [--pdf <abs.pdf>] [--out <dir>]
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Repo root (scripts/loop2/ -> repo root is two levels up).
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # noqa: E402
    sys.path.insert(0, str(REPO))

import fitz  # PyMuPDF  # noqa: E402

from src.core.config import get_settings  # noqa: E402
from src.core.storage.sqlite_db import get_db_connection  # noqa: E402
from src.core.text_utils import (  # noqa: E402
    _PUA_LATIN_MAP, normalize_pua_latin, strip_block_noise)

CONTENT_TYPES = ("normal", "附录")


def _norm(s: str) -> str:
    """Light normalization for text-fidelity comparison.

    NFKC + lowercase + strip all whitespace + keep alnum / CJK. Dropping whitespace
    makes the edit-distance comparison insensitive to line-wrap differences, which
    is exactly the kind of layout noise we do NOT want to report as a defect.
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = s.lower()
    return re.sub(r"\s+", "", s)


_RE_FOOTER = re.compile(
    r"^GB[\s\uff0f/]*(?:Z?[\s\uff0f/]*T)?\s*\d+(?:\.\d+)*[\s\u2014\u2013\-]{1,3}\d{4}\s*$")


def _strip_html(s: str) -> str:
    """Strip HTML tags from table markdown -> plain cell text (for the text path)."""
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))


def _strip_orig_noise(text: str) -> str:
    """Remove lines that appear in the PDF text layer but not in the preview's
    clause body (watermark URL, page numbers, and the standard footer like
    'GB/T 34406—2017'), so text_fidelity isn't dragged down by layout chrome."""
    if not text:
        return ""
    t = strip_block_noise(text)  # watermark-URL / page-number full lines
    out = [ln for ln in t.split("\n") if not _RE_FOOTER.match(ln.strip())]
    return "\n".join(out)


def _parse_page_breaks(raw) -> list[list[int]] | None:
    """page_breaks column is JSON text (or list). Returns None if absent/invalid."""
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if not isinstance(raw, list) or not raw:
        return None
    out = []
    for item in raw:
        if (isinstance(item, (list, tuple)) and len(item) == 2
                and isinstance(item[0], int) and isinstance(item[1], int)):
            out.append([item[0], item[1]])
    return out or None


def _rows_for_clause(content_text: str):
    return [ln for ln in (content_text or "").split("\n")]


def _content_pages_for_clause(page_breaks, page_start, page_end):
    """Set of PDF pages that carry clauses for one clause.

    With page_breaks (B3): the set of pdf_page values referenced.
    Without (pre-B3): fall back to the [page_start, page_end] range (coarse).
    """
    if page_breaks:
        return {p for _, p in page_breaks}
    ps = page_start or 1
    pe = page_end or ps
    return set(range(int(ps), int(pe) + 1))


def _assign_lines_to_pages(page_breaks, content_text, page_start, page_end):
    """page -> [lines] for one clause, in reading (line) order.

    page_breaks run-start: entry [row_idx, pdf_page] means content_text line
    ``row_idx`` (0-based) is the FIRST line of ``pdf_page``. Lines between two
    entries belong to the earlier page. With no page_breaks, whole clause is
    assigned to page_start (coarse).
    """
    lines = _rows_for_clause(content_text)
    if not lines:
        return {}
    if page_breaks:
        breaks = page_breaks
        # Normalize to a monotonic list of (row_idx, pdf_page).
        pb = sorted(breaks, key=lambda x: x[0])
        out: dict[int, list] = {}
        for i, (row, page) in enumerate(pb):
            bound = pb[i + 1][0] if i + 1 < len(pb) else len(lines)
            for ln in lines[row:bound]:
                out.setdefault(page, []).append(ln)
        return out
    return {int(page_start or 1): lines}


def _pagelines_map(clauses) -> dict[int, list]:
    """whole-doc page -> [lines] (reading order across clauses). Includes table text
    (stored in content_markdown, NOT in content_text) assigned to the table's page,
    so text-fidelity isn't penalised on table-heavy pages."""
    out: dict[int, list] = {}
    for c in clauses:
        for page, ln in _assign_lines_to_pages(
                c["page_breaks"], c["content_text"], c["page_start"], c["page_end"]).items():
            out.setdefault(page, []).extend(ln)
        ttxt = c.get("table_text") or ""
        if ttxt:
            tpages = c.get("table_pages") or [c.get("page_start") or 1]
            for tp in tpages:
                out.setdefault(int(tp), []).append(ttxt)
    return out


def _count_objects_clause(content_text, content_markdown, figure_html):
    """Best-effort deterministic object counts from stored columns."""
    ct = content_text or ""
    md = content_markdown or ""
    ff = figure_html or ""
    fig = 1 if re.search(r"<img|class=[\"']fig-strip|class=[\"']fig-embed|data-fig", ff) else 0
    fig += ff.count("<img")
    tbl = md.count("<table")
    # Formulas: stored as <eq>LaTeX</eq> (cleaned at render / KaTeX).
    form = (ct + md).count("<eq>")
    return {"figures": fig, "tables": tbl, "formulas": form}


def _pdf_orig(pdf_path: Path, n_pages: int):
    """Per-page original text layer + embedded image count, via PyMuPDF."""
    text_by_page: dict[int, str] = {}
    img_by_page: dict[int, int] = {}
    if not pdf_path or not pdf_path.exists():
        return text_by_page, img_by_page, None
    try:
        with fitz.open(str(pdf_path)) as doc:
            for i in range(min(n_pages, len(doc))):
                pg = doc[i]
                try:
                    text_by_page[i + 1] = pg.get_text()
                except Exception:
                    text_by_page[i + 1] = ""
                try:
                    img_by_page[i + 1] = len(pg.get_images(full=True))
                except Exception:
                    img_by_page[i + 1] = 0
            return text_by_page, img_by_page, len(doc)
    except Exception as e:  # noqa: BLE001
        return text_by_page, img_by_page, f"pdf-open-error: {e}"


def build_snapshot(doc_id: str, pdf_path: Path | None = None) -> dict:
    conn = get_db_connection()
    meta = conn.execute(
        "SELECT standard_no, standard_name, file_hash FROM doc_meta WHERE doc_id=?",
        (str(doc_id),)).fetchone()
    if meta is None:
        raise RuntimeError(f"no doc_meta for doc_id={doc_id}")

    rows = conn.execute(
        "SELECT cr.clause_revision_id, cr.clause_number, cr.title, cr.content_text,"
        " cr.content_markdown, cr.page_start, cr.page_end, cr.page_breaks, cr.figure_html"
        " FROM clause_revision cr WHERE cr.doc_id=?"
        " AND cr.content_type IN (%s) ORDER BY cr.rowid" % ",".join("?" * len(CONTENT_TYPES)),
        (str(doc_id), *CONTENT_TYPES)).fetchall()

    pages_meta = conn.execute(
        "SELECT page_number, width, height, rotation, media_box FROM doc_page_geometry"
        " WHERE doc_id=? ORDER BY page_number", (str(doc_id),)).fetchall()

    # Table spans -> exact page(s) each table occupies (for table-text placement).
    crids = [r["clause_revision_id"] for r in rows]
    tbl_pages: dict[str, list[int]] = {}
    if crids:
        ph = ",".join("?" * len(crids))
        for s in conn.execute(
                f"SELECT clause_revision_id, page_number FROM source_span"
                f" WHERE clause_revision_id IN ({ph}) AND span_type='table'"
                f" ORDER BY clause_revision_id, sort_order", crids):
            tbl_pages.setdefault(s["clause_revision_id"], []).append(s["page_number"])

    clauses = []
    for r in rows:
        clauses.append({
            "revision_id": r["clause_revision_id"],
            "clause_number": r["clause_number"],
            "title": r["title"],
            "content_text": r["content_text"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
            "page_breaks": _parse_page_breaks(r["page_breaks"]),
            "figures": _count_objects_clause(
                r["content_text"], r["content_markdown"], r["figure_html"])["figures"],
            "tables": _count_objects_clause(
                r["content_text"], r["content_markdown"], r["figure_html"])["tables"],
            "formulas": _count_objects_clause(
                r["content_text"], r["content_markdown"], r["figure_html"])["formulas"],
            "table_text": _strip_html(r["content_markdown"] or ""),
            "table_pages": tbl_pages.get(r["clause_revision_id"]),
        })

    doc_page_count = len(pages_meta) if pages_meta else None

    # === Original (PDF) side, optional ===
    orig_text_by_page: dict[int, str] = {}
    orig_img_by_page: dict[int, int] = {}
    pdf_error = None
    pdf_page_count = None
    if pdf_path:
        orig_text_by_page, orig_img_by_page, pdf_page_count = _pdf_orig(pdf_path, doc_page_count or 10 ** 6)

    # Text-layer state: detect PUA-mangled (形近字) and restore via
    # normalize_pua_latin ONLY when the mangled signature is present (it is NOT
    # idempotent-safe on clean text: it shifts 0x21-0x2A). Signature = any char in
    # _PUA_LATIN_MAP (e.g. 犐犆犛). Empty text across pages => scanned.
    text_layer_state = "clean"
    if orig_text_by_page:
        mangled = any(
            ch in _PUA_LATIN_MAP
            for t in orig_text_by_page.values() for ch in t)
        if mangled:
            orig_text_by_page = {
                p: normalize_pua_latin(t) for p, t in orig_text_by_page.items()}
            text_layer_state = "pua_mangled"
        elif not any(t.strip() for t in orig_text_by_page.values()):
            text_layer_state = "scan"

    # Strip layout chrome (watermark / footer / page numbers) so the text path
    # focuses on clause content; done AFTER mangling detection (which uses raw text).
    orig_text_by_page = {
        p: _strip_orig_noise(t) for p, t in orig_text_by_page.items()}

    # Resolve a canonical page count: prefer DB geometry, else pdf, else derived.
    page_count = doc_page_count or pdf_page_count or 0

    # Expected figures from MinerU middle.json layout objects (NOT get_images,
    # which counts logos / watermarks / page backgrounds). None => no deep parse =>
    # object_presence is na (not independently checkable).
    expected_figs: dict[int, int] = {}
    try:
        from src.core.middle_geo import load as _load_mid
        _mid = _load_mid(get_settings().data_dir / "parse_out" / str(doc_id))
        if _mid is not None:
            for _f in _mid.figures():
                _pg = int(_f.get("page") or 0)
                if _pg:
                    expected_figs[_pg] = expected_figs.get(_pg, 0) + 1
    except Exception:
        expected_figs = {}

    snapshot = {
        "doc_id": str(doc_id),
        "standard_no": meta["standard_no"],
        "standard_name": meta["standard_name"],
        "pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_error": pdf_error,
        "page_count": page_count,
        "pages_meta": [dict(p) for p in pages_meta],
        "text_layer_state": text_layer_state,
        "expected_figure_count_by_page": {str(k): v for k, v in expected_figs.items()},
        "clauses": clauses,
        "preview_page_lines": _pagelines_map(clauses),
        "orig_text_by_page": {str(k): v for k, v in orig_text_by_page.items()},
        "orig_image_count_by_page": {str(k): v for k, v in orig_img_by_page.items()},
    }
    return snapshot


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--pdf", default=None, help="absolute path to source PDF (orig side)")
    ap.add_argument("--out", default=None, help="dir for snapshot.json (default data_dir/loop2)")
    a = ap.parse_args()
    st = get_settings()
    out_dir = Path(a.out) if a.out else (st.data_dir / "loop2")
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = build_snapshot(a.doc_id, Path(a.pdf) if a.pdf else None)
    path = out_dir / "snapshot.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "doc_id": snap["doc_id"], "standard_no": snap["standard_no"],
        "page_count": snap["page_count"],
        "clauses": len(snap["clauses"]),
        "pages_with_preview": len(snap["preview_page_lines"]),
        "pages_with_orig_text": len(snap["orig_text_by_page"]),
        "snapshot": str(path),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
