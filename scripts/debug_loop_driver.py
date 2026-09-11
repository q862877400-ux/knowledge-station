# -*- coding: utf-8 -*-
"""Debug Loop 驱动：书序枚举、去重、pass/issue 登记、三振出局、停止判定。

状态落盘（数据区，可跨重启）：%APPDATA%/KnowledgeStation/debug_loop/
  - passed_manifest.json  : {"passed":[std_no...], "consecutive":int, "last_status"}
  - known_issues.json      : {"issues":[{type,count,first,pdfs,solution,recurred}],
                             "three_strikes":[{type,reflection,solution,date}],
                             "passes":[...]}
  - state.json             : {cursor_index, current_pdf, rounds[], started_at}
  - debug_log.txt          : 追加式日志

用法（模块内函数 + CLI）：
  python scripts/debug_loop_driver.py list            # 按文件名顺序枚举去重后的书单
  python scripts/debug_loop_driver.py next [--start N] # 下一条未通过书（std_no|pdf|rel）
  python scripts/debug_loop_driver.py pass --std <no> --pdf <path> --rounds N
  python scripts/debug_loop_driver.py issue --type <diff-type> --std <no> --pdf <path> --detail <s>
  python scripts/debug_loop_driver.py status           # 当前游标/连续数/停止判定
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._stdparse import _STD_RE, derive_standard  # noqa: E402

CAMP = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ROOT = Path(r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)")
STOP_CONSECUTIVE = 5

_PASSED = CAMP / "passed_manifest.json"
_ISSUES = CAMP / "known_issues.json"
_STATE = CAMP / "state.json"
_LOG = CAMP / "debug_log.txt"


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg: str):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def list_books() -> list[dict]:
    """按文件名顺序递归枚举，按标准号去重（同号取第一个），返回书单。"""
    # 确定性序：相对路径排序；体检结果等非国标目录排除
    pdfs = sorted([p for p in ROOT.rglob("*.pdf")
                   if "体检结果" not in p.parts], key=lambda p: str(p.relative_to(ROOT)))
    seen, books = set(), []
    for p in pdfs:
        std_no, _ = derive_standard(p)
        key = std_no or str(p.relative_to(ROOT))
        if key in seen:
            continue
        seen.add(key)
        books.append({"std_no": std_no, "pdf": str(p),
                      "rel": str(p.relative_to(ROOT))})
    return books


def next_book(start: int | None = None) -> dict | None:
    books = list_books()
    passed = set(_load(_PASSED, {"passed": []}).get("passed", []))
    st = _load(_STATE, {})
    idx = start if start is not None else st.get("cursor_index", 0)
    # 若游标处已通过，则顺延
    for i in range(idx, len(books)):
        b = books[i]
        if b["std_no"] and b["std_no"] in passed:
            continue
        if not b["std_no"] and b["rel"] in passed:
            continue
        st["cursor_index"] = i
        st["current_pdf"] = b["pdf"]
        _dump(_STATE, st)
        return b
    return None


def record_pass(std_no: str, pdf: str, rounds: int):
    pm = _load(_PASSED, {"passed": [], "consecutive": 0, "last_status": "init"})
    key = std_no or pdf
    if key not in pm["passed"]:
        pm["passed"].append(key)
        pm["consecutive"] += 1
    pm["last_status"] = "pass"
    _dump(_PASSED, pm)
    # 记录到 known_issues.passes
    ki = _load(_ISSUES, {"issues": [], "three_strikes": [], "passes": []})
    ki.setdefault("passes", []).append(
        {"std": std_no, "pdf": pdf, "rounds": rounds,
         "at": datetime.now().isoformat(timespec="seconds")})
    _dump(_ISSUES, ki)
    st = _load(_STATE, {})
    st["rounds"] = st.get("rounds", [])
    st["rounds"].append({"std": std_no, "pdf": pdf, "outcome": "pass",
                         "rounds": rounds})
    _dump(_STATE, st)
    log(f"PASS {key} rounds={rounds} consecutive={pm['consecutive']}")
    if pm["consecutive"] >= STOP_CONSECUTIVE:
        log(f"🚦 STOP CONDITION MET: {pm['consecutive']} 连续一次导入即完美")


def record_fail(std_no: str, pdf: str, rounds: int, note: str = ""):
    pm = _load(_PASSED, {"passed": [], "consecutive": 0, "last_status": "init"})
    pm["consecutive"] = 0
    pm["last_status"] = "fail"
    _dump(_PASSED, pm)
    st = _load(_STATE, {})
    st["rounds"] = st.get("rounds", [])
    st["rounds"].append({"std": std_no, "pdf": pdf, "outcome": "fail",
                         "rounds": rounds, "note": note})
    _dump(_STATE, st)
    log(f"FAIL {std_no} rounds={rounds} consecutive reset -> {note}")


def record_issue(issue_type: str, std_no: str, pdf: str, detail: str = ""):
    """登记差异类型；达 3 次触发三振出局（返回 True=本次触发）。"""
    ki = _load(_ISSUES, {"issues": [], "three_strikes": [], "passes": []})
    issues = ki.setdefault("issues", [])
    hit = next((x for x in issues if x["type"] == issue_type), None)
    now = datetime.now().isoformat(timespec="seconds")
    triggered = False
    if hit is None:
        hit = {"type": issue_type, "count": 1, "first": now, "pdfs": [pdf],
               "solution": None, "recurred": False, "detail": detail}
        issues.append(hit)
    else:
        hit["count"] += 1
        if pdf not in hit["pdfs"]:
            hit["pdfs"].append(pdf)
        hit["detail"] = detail
        if hit["count"] >= 3:
            ki["three_strikes"].append({"type": issue_type, "count": hit["count"],
                                        "first": hit["first"], "at": now})
            # 重置计数（待架构级泛解后由 solve_issue 清除）
            hit["count"] = 0
            hit["recurred"] = True
            triggered = True
    _dump(_ISSUES, ki)
    log(f"ISSUE[{issue_type}] n={(_load(_ISSUES,{})['issues'] and next((i['count'] for i in _load(_ISSUES,{})['issues'] if i['type']==issue_type),0))} "
        f"{std_no} {'→ 三振出局' if triggered else ''}")
    return triggered


def solve_issue(issue_type: str, solution: str):
    """三振出局后实施架构级泛解：标记该类型已根治，供回溯。"""
    ki = _load(_ISSUES, {"issues": [], "three_strikes": [], "passes": []})
    for x in ki["issues"]:
        if x["type"] == issue_type:
            x["solution"] = solution
            x["count"] = 0
    _dump(_ISSUES, ki)
    log(f"SOLVED[{issue_type}] {solution}")


def status():
    books = list_books()
    pm = _load(_PASSED, {"passed": [], "consecutive": 0})
    st = _load(_STATE, {})
    ki = _load(_ISSUES, {"issues": [], "three_strikes": []})
    print(f"book total      : {len(books)}")
    print(f"cursor_index    : {st.get('cursor_index', 0)}")
    print(f"current_pdf     : {st.get('current_pdf')}")
    print(f"passed count    : {len(pm.get('passed', []))}")
    print(f"consecutive     : {pm.get('consecutive', 0)} (stop at {STOP_CONSECUTIVE})")
    print(f"known issue types: {[ (i['type'], i['count']) for i in ki.get('issues', []) ]}")
    print(f"three strikes   : {[ t['type'] for t in ki.get('three_strikes', []) ]}")
    stop = pm.get("consecutive", 0) >= STOP_CONSECUTIVE
    print(f"stop condition  : {'MET' if stop else 'not yet'}")
    return stop


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p = sub.add_parser("next"); p.add_argument("--start", type=int)
    sub.add_parser("status")
    pp = sub.add_parser("pass"); pp.add_argument("--std"); pp.add_argument("--pdf"); pp.add_argument("--rounds", type=int, default=1)
    pi = sub.add_parser("issue"); pi.add_argument("--type"); pi.add_argument("--std"); pi.add_argument("--pdf"); pi.add_argument("--detail", default="")
    ps = sub.add_parser("solve"); ps.add_argument("--type"); ps.add_argument("--solution")
    pf = sub.add_parser("fail"); pf.add_argument("--std"); pf.add_argument("--pdf"); pf.add_argument("--rounds", type=int, default=1); pf.add_argument("--note", default="")
    a = ap.parse_args()

    if a.cmd == "list":
        for b in list_books()[:30]:
            print(f"  {b['std_no'] or '?'}\t{b['rel']}")
        print(f"... total {len(list_books())}")
    elif a.cmd == "next":
        b = next_book(a.start)
        print(json.dumps(b, ensure_ascii=False) if b else "NO_MORE_BOOKS")
    elif a.cmd == "status":
        status()
    elif a.cmd == "pass":
        record_pass(a.std or "?", a.pdf or "?", a.rounds)
    elif a.cmd == "fail":
        record_fail(a.std or "?", a.pdf or "?", a.rounds, a.note)
    elif a.cmd == "issue":
        record_issue(a.type, a.std or "?", a.pdf or "?", a.detail)
    elif a.cmd == "solve":
        solve_issue(a.type, a.solution)


if __name__ == "__main__":
    main()
