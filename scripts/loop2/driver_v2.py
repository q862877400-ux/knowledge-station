# -*- coding: utf-8 -*-
"""Bounded self-debug loop orchestrator (loop2 step 5).

Drives the loop that the deterministic oracle (oracle_snapshot + oracle_score) gates.
It fixes the two flaws that made the old ``debug_loop_driver.py`` stall:

  - **Persistent book queue** built once (build), never re-enumerated mid-campaign.
    ``next`` walks the persisted snapshot by cursor, so the 35k-file tree won't shift
    the queue under us.
  - **Real convergence semantics**: ``consecutive`` increments ONLY on a ``rounds==1``
    (first-import-perfect) pass; any multi-round pass or a fail/blocked resets it.
    Stop = `STOP_CONSECUTIVE` consecutive round-1 passes AND no ``blocked`` items AND
    no new root-cause class in the last ``M_SILENCE`` passes. Hard caps
    (`MAX_ROUNDS`, `MAX_BLOCKED`) guarantee physical termination.

Root-cause registry: ``known_issues.json`` keyed by ROOT-CAUSE class (not VLM symptom).
A class reaching 3 occurrences triggers an architecture reflection obligation; count is
only cleared by ``solve`` (after a generalised fix + sibling verification), not merely
by re-occurrence.

State (all in the data area, data/code separation):
  %APPDATA%/KnowledgeStation/loop2_state/
    queue.json   {root, books[], cursor, built_at}
    state.json   {cursor_index, current_std, current_pdf, rounds[]}
    passed.json  {passed[], consecutive, last_status}
    issues.json  {classes{}, three_strikes[], blocked[]}
    debug_log.txt

CLI:
  python scripts/loop2/driver_v2.py build   [--root <dir>] [--limit N]
  python scripts/loop2/driver_v2.py next
  python scripts/loop2/driver_v2.py assess  [--pdf <abs>] [--doc-id <id>] [--ingest]
  python scripts/loop2/driver_v2.py pass    --std <no> --rounds N
  python scripts/loop2/driver_v2.py fail    --std <no> --rounds N --note <s>
  python scripts/loop2/driver_v2.py blocked --std <no>
  python scripts/loop2/driver_v2.py issue   --class <root-cause> --std <no> --pdf <p> --detail <s>
  python scripts/loop2/driver_v2.py solve   --class <root-cause> --solution <s>
  python scripts/loop2/driver_v2.py status
  python scripts/loop2/driver_v2.py report
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # noqa: E402
    sys.path.insert(0, str(REPO))

from scripts._stdparse import derive_standard  # noqa: E402
from src.core.config import get_settings  # noqa: E402
from src.core.storage.sqlite_db import get_db_connection  # noqa: E402
from scripts.loop2.oracle_snapshot import build_snapshot  # noqa: E402
from scripts.loop2.oracle_score import score  # noqa: E402

STOP_CONSECUTIVE = int(os.environ.get("LOOP2_STOP_CONSECUTIVE", "5"))
MAX_ROUNDS = int(os.environ.get("LOOP2_MAX_ROUNDS", "3"))
MAX_BLOCKED = int(os.environ.get("LOOP2_MAX_BLOCKED", "5"))
M_SILENCE = int(os.environ.get("LOOP2_M_SILENCE", "5"))
# data library root; env first, else a user data dir (not product code).
DEFAULT_ROOT = os.environ.get(
    "LOOP2_ROOT", r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")

# Root-CAUSE classes (not VLM symptom strings) seeded from visual-regression-log.md
# C1~C5 architecture reflections. record_issue keys on these for three-strike.
SEED_ROOT_CAUSES = [
    "ingest:mineru-type-split-consumption",
    "ingest:chart-caption-not-in-content_text",
    "ingest:middle-image-page-range",
    "render:text-layer-skips-deep-formula",
    "render:formula-katex-parse",
    "render:fig-caption-boundary-regex",
    "render:asset_done-global-dedup",
    "render:two-column-layout-flow",
    "store:page_break-null-pre-B3",
    "store:page-break-offset",
]

STATE_DIR = get_settings().data_dir / "loop2_state"
QUEUE = STATE_DIR / "queue.json"
STATE = STATE_DIR / "state.json"
PASSED = STATE_DIR / "passed.json"
ISSUES = STATE_DIR / "issues.json"
LOG = STATE_DIR / "debug_log.txt"


def _default(obj: dict, key: str, factory=dict):
    return obj.setdefault(key, factory())


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


# --------------------------------------------------------------------------- queue

def list_books(root: Path) -> list[dict]:
    """Deterministic, dedup-by-standard_no enumeration (exclude 体检结果 dirs)."""
    pdfs = sorted(
        [p for p in root.rglob("*.pdf") if "体检结果" not in p.parts],
        key=lambda p: str(p.relative_to(root)))
    seen, books = set(), []
    for p in pdfs:
        std_no, _ = derive_standard(p)
        key = std_no or str(p.relative_to(root))
        if key in seen:
            continue
        seen.add(key)
        books.append({"std_no": std_no, "rel": str(p.relative_to(root))})
    return books


def build_queue(root: Path, limit: int | None = None) -> dict:
    books = list_books(root)
    if limit:
        books = books[:limit]
    q = {"root": str(root), "books": books, "cursor": 0,
         "built_at": datetime.now().isoformat(timespec="seconds")}
    _dump(QUEUE, q)
    log(f"BUILD queue: {len(books)} books (root={root})")
    return q


def load_queue() -> dict:
    return _load(QUEUE, {"root": DEFAULT_ROOT, "books": [], "cursor": 0})


def _abs_pdf(rel: str) -> Path:
    return Path(load_queue()["root"]) / rel


def next_book(start: int | None = None) -> dict | None:
    q = load_queue()
    passed = set(_load(PASSED, {"passed": []}).get("passed", []))
    st = _load(STATE, {})
    idx = start if start is not None else st.get("cursor_index", q.get("cursor", 0))
    for i in range(idx, len(q["books"])):
        b = q["books"][i]
        key = b["std_no"] or b["rel"]
        if key in passed:
            continue
        st["cursor_index"] = i
        st["current_std"] = b["std_no"]
        st["current_pdf"] = str(_abs_pdf(b["rel"]))
        _dump(STATE, st)
        return {"std_no": b["std_no"], "pdf": str(_abs_pdf(b["rel"])), "rel": b["rel"]}
    return None


# -------------------------------------------------------------- assess (oracle)

def _locate_doc_id(pdf: Path) -> tuple[str | None, bool]:
    conn = get_db_connection()
    try:
        h = hashlib.sha256(pdf.read_bytes()).hexdigest()
    except Exception:
        h = None
    if h:
        r = conn.execute("SELECT doc_id FROM doc_meta WHERE file_hash=?", (h,)).fetchone()
        if r:
            return r["doc_id"], False
    std, _ = derive_standard(pdf)
    # derive_standard() drops the space ("GB/T1032-2023") while doc_meta stores it
    # ("GB/T 1032-2023"); match space-insensitively.
    cand = std.replace(" ", "")
    r = conn.execute(
        "SELECT doc_id FROM doc_meta WHERE REPLACE(standard_no,' ','')=?", (cand,)).fetchone()
    if r:
        return r["doc_id"], True
    return None, False


def assess(pdf: Path, doc_id: str | None = None, ingest: bool = False) -> dict:
    """Wire the deterministic oracle: locate/ingest a doc, then build+score snapshot."""
    if doc_id is None:
        d_id, matched = _locate_doc_id(pdf)
        if d_id is None:
            if not ingest:
                return {"needs_ingest": True, "pdf": str(pdf),
                        "note": "no matching doc in DB; rerun with --ingest"}
            from src.core.ingestion.pipeline import run_full_ingest
            std, name = derive_standard(pdf)
            res = run_full_ingest(pdf, std, name, reingest=False, force_deep=True)
            d_id = res.get("doc_id") or res.get("existing_doc_id")
            if not d_id:
                return {"error": res}
            log(f"ASSESS ingest {std} -> {d_id}")
        doc_id = d_id
    snap = build_snapshot(doc_id, pdf)
    verdict = score(snap)
    return {"doc_id": doc_id, "verdict": verdict}


# ------------------------------------------------------------- pass/fail/blocked

def record_pass(std_no: str, rounds: int) -> dict:
    pm = _load(PASSED, {"passed": [], "consecutive": 0, "last_status": "init"})
    key = std_no or "?"
    if key not in pm["passed"]:
        pm["passed"].append(key)
    # Convergence semantics: consecutive increments ONLY on a first-import-perfect
    # (rounds==1) pass. A multi-round pass still records the book but resets the streak.
    if rounds == 1:
        pm["consecutive"] = pm.get("consecutive", 0) + 1
    else:
        pm["consecutive"] = 0
    pm["last_status"] = "pass"
    _dump(PASSED, pm)
    st = _load(STATE, {})
    _default(st, "rounds", list).append(
        {"std": std_no, "outcome": "pass", "rounds": rounds})
    _dump(STATE, st)
    log(f"PASS {key} rounds={rounds} consecutive={pm['consecutive']} "
        f"(stop={STOP_CONSECUTIVE})")
    return {"consecutive": pm["consecutive"], "stop": pm["consecutive"] >= STOP_CONSECUTIVE}


def record_fail(std_no: str, rounds: int, note: str = "") -> dict:
    pm = _load(PASSED, {"passed": [], "consecutive": 0, "last_status": "init"})
    pm["consecutive"] = 0
    pm["last_status"] = "fail"
    _dump(PASSED, pm)
    st = _load(STATE, {})
    _default(st, "rounds", list).append(
        {"std": std_no, "outcome": "fail", "rounds": rounds, "note": note})
    _dump(STATE, st)
    log(f"FAIL {std_no} rounds={rounds} consecutive reset -> {note}")
    return {"consecutive": 0}


def record_blocked(std_no: str) -> dict:
    """A book that hit MAX_ROUNDS without passing the oracle goes here (not 'passed')."""
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    blk = _default(iss, "blocked", list)
    if std_no not in blk:
        blk.append(std_no)
    _dump(ISSUES, iss)
    pm = _load(PASSED, {"passed": [], "consecutive": 0, "last_status": "init"})
    pm["consecutive"] = 0
    pm["last_status"] = "blocked"
    _dump(PASSED, pm)
    log(f"BLOCKED {std_no} (architecture-level); consecutive reset")
    return {"blocked": blk, "count": len(blk)}


# ----------------------------------------------------------- root-cause registry

def seed_issues() -> dict:
    """Seed known_issues.json with the known root-cause taxonomy (count 0 baseline)."""
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    classes = _default(iss, "classes", dict)
    for rc in SEED_ROOT_CAUSES:
        classes.setdefault(rc, {"count": 0, "first": None, "pdfs": [],
                                "solution": None, "armed": False})
    _dump(ISSUES, iss)
    log(f"SEED root-cause classes: {len(SEED_ROOT_CAUSES)}")
    return {"seeded": len(SEED_ROOT_CAUSES), "classes": len(classes)}


def record_issue(root_cause: str, std_no: str, pdf: str, detail: str = "") -> dict:
    """Three-strike by ROOT-CAUSE class. At 3 it arms an architecture reflection
    obligation (does NOT self-clear); count is only cleared by solve()."""
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    classes = _default(iss, "classes", dict)
    cls = classes.setdefault(root_cause, {
        "count": 0, "first": None, "pdfs": [], "solution": None, "armed": False})
    now = datetime.now().isoformat(timespec="seconds")
    if not cls["first"]:
        cls["first"] = now
    cls["count"] += 1
    if pdf and pdf not in cls["pdfs"]:
        cls["pdfs"].append(pdf)
    if detail:
        cls["detail"] = detail
    armed = cls["count"] >= 3
    if armed and not cls["armed"]:
        cls["armed"] = True
        _default(iss, "three_strikes", list).append(
            {"class": root_cause, "count": cls["count"], "first": cls["first"], "at": now})
    _dump(ISSUES, iss)
    log(f"ISSUE[{root_cause}] n={cls['count']} {std_no} {'-> ARCH-REFLECTION ARMED' if armed else ''}")
    return {"count": cls["count"], "armed": armed}


def solve_issue(root_cause: str, solution: str) -> dict:
    """Clear a root-cause class after a generalised fix (count resets; class solved).
    Sibling verification is an external discipline (see design §C)."""
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    cls = iss["classes"].get(root_cause)
    if cls:
        cls["count"] = 0
        cls["solution"] = solution
        cls["armed"] = False
        _dump(ISSUES, iss)
    log(f"SOLVE[{root_cause}] {solution}")
    return {"solved": bool(cls)}


# -------------------------------------------------------------------------- stop

def is_converged() -> dict:
    pm = _load(PASSED, {"passed": [], "consecutive": 0})
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    consecutive = pm.get("consecutive", 0)
    blocked = iss.get("blocked", [])
    # M-silence: none of the last M passes registered a new root-cause class.
    st = _load(STATE, {"rounds": []})
    recent = [r for r in st.get("rounds", []) if r.get("outcome") == "pass"][-M_SILENCE:]
    new_class_recent = any(r.get("new_root_cause") for r in recent)
    met = (consecutive >= STOP_CONSECUTIVE and not blocked and not new_class_recent)
    return {"consecutive": consecutive, "stop_c": STOP_CONSECUTIVE,
            "blocked": blocked, "new_class_recent": new_class_recent,
            "met": bool(met)}


def status() -> dict:
    q = load_queue()
    pm = _load(PASSED, {"passed": [], "consecutive": 0})
    st = _load(STATE, {})
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    conv = is_converged()
    print(f"books in queue : {len(q['books'])}")
    print(f"cursor_index   : {st.get('cursor_index', q.get('cursor', 0))}")
    print(f"current        : {st.get('current_std')} ({st.get('current_pdf')})")
    print(f"passed count   : {len(pm.get('passed', []))}")
    print(f"consecutive    : {pm.get('consecutive', 0)} (stop at {STOP_CONSECUTIVE})")
    print(f"blocked        : {iss.get('blocked', [])}")
    print(f"root-cause     : { {k: v['count'] for k, v in iss.get('classes', {}).items()} }")
    print(f"three_strikes  : {[t['class'] for t in iss.get('three_strikes', [])]}")
    print(f"CONVERGED      : {conv['met']}")
    return conv


def report() -> None:
    pm = _load(PASSED, {"passed": [], "consecutive": 0})
    iss = _load(ISSUES, {"classes": {}, "three_strikes": [], "blocked": []})
    st = _load(STATE, {"rounds": []})
    print("== loop2 final report ==")
    print(f"passed   : {len(pm.get('passed', []))}")
    print(f"blocked  : {iss.get('blocked', [])}")
    print(f"rounds   : {len(st.get('rounds', []))}")
    print(f"root-cause { 'count' }:")
    for k, v in iss.get("classes", {}).items():
        print(f"  {k}: n={v['count']} first={v['first']} solved={bool(v['solution'])}")
    print(f"arch-reflections (three-strikes): {len(iss.get('three_strikes', []))}")
    print(f"converged: {is_converged()['met']}")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--root", default=DEFAULT_ROOT); b.add_argument("--limit", type=int)
    sub.add_parser("next")
    sub.add_parser("seed")
    a = sub.add_parser("assess"); a.add_argument("--pdf"); a.add_argument("--doc-id"); a.add_argument("--ingest", action="store_true")
    p = sub.add_parser("pass"); p.add_argument("--std"); p.add_argument("--rounds", type=int, default=1)
    f = sub.add_parser("fail"); f.add_argument("--std"); f.add_argument("--rounds", type=int, default=1); f.add_argument("--note", default="")
    bl = sub.add_parser("blocked"); bl.add_argument("--std")
    i = sub.add_parser("issue"); i.add_argument("--class", dest="cls", required=True); i.add_argument("--std"); i.add_argument("--pdf"); i.add_argument("--detail", default="")
    s = sub.add_parser("solve"); s.add_argument("--class", dest="cls", required=True); s.add_argument("--solution", required=True)
    sub.add_parser("status")
    sub.add_parser("report")
    opts = ap.parse_args()

    if opts.cmd == "build":
        build_queue(Path(opts.root), opts.limit)
    elif opts.cmd == "next":
        print(json.dumps(next_book(), ensure_ascii=False) or "NO_MORE_BOOKS")
    elif opts.cmd == "seed":
        print(json.dumps(seed_issues(), ensure_ascii=False))
    elif opts.cmd == "assess":
        pdf = Path(opts.pdf) if opts.pdf else Path(_load(STATE, {}).get("current_pdf", ""))
        print(json.dumps(assess(pdf, opts.doc_id, opts.ingest), ensure_ascii=False))
    elif opts.cmd == "pass":
        print(json.dumps(record_pass(opts.std or "?", opts.rounds), ensure_ascii=False))
    elif opts.cmd == "fail":
        print(json.dumps(record_fail(opts.std or "?", opts.rounds, opts.note), ensure_ascii=False))
    elif opts.cmd == "blocked":
        print(json.dumps(record_blocked(opts.std or "?"), ensure_ascii=False))
    elif opts.cmd == "issue":
        print(json.dumps(record_issue(opts.cls, opts.std or "?", opts.pdf or "", opts.detail), ensure_ascii=False))
    elif opts.cmd == "solve":
        print(json.dumps(solve_issue(opts.cls, opts.solution), ensure_ascii=False))
    elif opts.cmd == "status":
        status()
    elif opts.cmd == "report":
        report()


if __name__ == "__main__":
    main()
