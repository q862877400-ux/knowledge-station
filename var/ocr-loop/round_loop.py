# -*- coding: utf-8 -*-
"""⚠ **审计方草案（auditor draft）——未经所有者评审，未被任何循环步骤调用。**

本文件由**独立审计会话**写成，用于在审计中量化"问题文档全集 + 干净抽样"这条路是否走得通
（审计期实测：2,543 部全量评估约 5.5 分钟）。**它不是被审计系统的一部分**：没有接入
`batch_advance` / `watchdog`，也不在门禁里。所有者请二选一：
  ① **接管**（评审、改写、纳入门禁与文档，成为你自己的工具）；
  ② **删除**（保留则必须带着这个横幅，避免下一个接手者误以为它是既有机制）。
审计方**不会**再对它做后续开发（保持独立性）；它对**正在跑的循环零影响**。

---

业主原话：「每轮都要跑之前有问题的所有问题文档，然后没问题的文档抽几份重跑看会不会出现新问题」。

**为什么需要它（也是审计发现 H4 的修法）**：批次 2–6 的评估只写**单文件覆盖写**的
`evolve/scout.json`，没有逐文档记录 → 事后**不知道哪些文档出过问题**，业主这条指令
在那个状态下根本无法执行。本模块把"逐文档台账"变成 append-only，并在此之上提供
"问题全集 ∪ 干净抽样"的每轮清单。

**口径（三条，都是刻意的）**：
1. **只重跑评估，不重新 OCR**。本轮全部修复都在切分/清洗/判据层；重新 OCR 会**同时换掉输入**，
   把"修复是否有效"和"识别是否变化"两个变量混在一起，且烧云额度。
   若某类缺陷属**识别层**（VLM 产物本身错），报告会把它标出来，那时再用
   `python var/ocr-loop/vlm_ocr.py --reset …` 对这些文档单独重跑。
2. **问题文档 = 最近一次记录里 `verdict != ok` 或命中数 > 0**；其中只命中
   `fixed_classes.json` 登记为 `已知限制/不修` 的类，单独统计（不混进"必修"集合）。
3. **干净抽样是确定性的**：按 `sha1(SEED|std_no)` 排序取前 N，可复现、可复核；
   `holdout`（留出集）**可以**进回归样本——它只禁止参与修复决策，做回归验证正是它的用途。

命令：
```
build     从台账产出本轮清单（问题全集 ∪ 干净抽样）→ evolve/rounds_verify/<R>.list.json
run       评估该清单 → append-only 台账 + <R>.metrics.json
report    与上一轮逐文档记录对比 → 已修复 / 仍问题 / 新冒问题 → <R>.report.md
all       build + run + report（每轮一条命令）
bootstrap 对现有批次全部文档跑一次评估，建立初始台账（首次必跑）
```
只读产物；**不写** state / scout.json / rounds（避免与正在跑的批次互相覆盖）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\AI\work space\zcode")
HERE = ROOT / "var" / "ocr-loop"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import evolve as E                                            # noqa: E402
import artifact_index as AI                                   # noqa: E402

EV = HERE / "evolve"
LEDGER = EV / "doc_ledger.jsonl"
RV = EV / "rounds_verify"
SEED = "ks-round-2026"

#: 登记为"已知限制/不修"的类 → 单独统计，不驱动修复预算（来源：`fixed_classes.json`）。
KNOWN_LIMIT_MARKS = ("已知限制", "不修", "known limit", "not fix")


def known_limit_classes() -> set[str]:
    """从 `fixed_classes.json` 读"已知限制/不修"的类名（单一事实源）。"""
    p = HERE / "fixed_classes.json"
    if not p.exists():
        return set()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    out = set()
    items = d.items() if isinstance(d, dict) else [(x.get("class"), x) for x in d]
    for k, v in items:
        if not isinstance(v, dict) or not k:
            continue
        blob = json.dumps(v, ensure_ascii=False)
        if any(m in blob for m in KNOWN_LIMIT_MARKS):
            out.add(str(k))
    return out


def classify_rec(rec: dict, limits: set[str] | None = None) -> str:
    """`problem` / `known-limit` / `clean` / `gap`（**纯函数**，便于行为测试）。"""
    limits = limits or set()
    verdict = str(rec.get("verdict") or "")
    classes = rec.get("classes") or {}
    if verdict in ("GAP", "ERROR"):
        return "gap"
    if not classes:
        return "clean"
    limit_ids = {c.split("::")[-1] for c in classes}
    return "known-limit" if limit_ids and limit_ids <= limits else "problem"


def pick_clean_sample(clean: list[str], n: int, seed: str = SEED) -> list[str]:
    """确定性抽样：按 `sha1(seed|std_no)` 排序取前 n（纯函数）。

    **每轮换种子**（`seed = SEED|round`，见 `cmd_build`）：固定抽同一批 30 部，
    只能在那 30 部里发现回归；轮换抽样让"干净文档"的覆盖面随轮次扩大，
    而"确定性"仍然成立（种子记在清单文件里，可原样复现）。
    """
    ordered = sorted(clean, key=lambda s: hashlib.sha1(f"{seed}|{s}".encode()).hexdigest())
    return ordered[:max(0, n)]


def load_ledger(path: Path | None = None) -> dict[str, dict]:
    """逐文档台账 → `std_no -> 最近一条记录`（append-only，后写覆盖前）。"""
    p = path or LEDGER
    latest: dict[str, dict] = {}
    if not p.exists():
        return latest
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if r.get("std_no"):
            latest[str(r["std_no"])] = r
    return latest


def append_ledger(rows: list[dict], path: Path | None = None) -> None:
    p = path or LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def diff_rounds(base: dict[str, dict], cur: dict[str, dict],
                limits: set[str] | None = None) -> dict:
    """两轮逐文档对比 → 已修复 / 仍问题 / 新冒问题 / 新出现的类（纯函数）。

    · `fixed`   ：上一轮 problem，本轮 clean
    · `still`   ：两轮都 problem
    · `new`     ：上一轮 clean（或不在台账），本轮 problem ← **回归信号**
    · `new_classes`：本轮出现、上一轮从未出现过的类名（全局回归信号）
    """
    limits = limits or set()
    fixed, still, new = [], [], []
    base_classes, cur_classes = set(), set()
    for _, r in base.items():
        base_classes |= set((r.get("classes") or {}))
    for k, r in cur.items():
        cur_classes |= set((r.get("classes") or {}))
        c_now = classify_rec(r, limits)
        b = base.get(k)
        c_before = classify_rec(b, limits) if b else None
        if c_now == "problem":
            (still if c_before == "problem" else new).append(k)
        elif c_now == "clean" and c_before == "problem":
            fixed.append(k)
    return {"fixed": sorted(fixed), "still": sorted(still), "new": sorted(new),
            "new_classes": sorted(cur_classes - base_classes),
            "lanes": {k: classify_rec(v, limits) for k, v in cur.items()}}


def docs_from_paths(paths: list[str]) -> list[dict]:
    """路径 → `evaluate_doc` 需要的记录（与 `corpus_docs` 同形：doc_id 留空）。"""
    out = []
    for i, p in enumerate(paths):
        path = Path(p)
        if not path.is_file():
            continue
        out.append({"i": i, "std_no": path.stem, "std_name": path.stem,
                    "doc_id": "", "file_hash": "", "file_path": str(path)})
    return out


def evaluate_list(list_file: Path, rnd: str, src: str) -> list[dict]:
    """评估一个清单 → 逐文档记录（**只读产物**，不写 state/scout）。"""
    obj = json.loads(list_file.read_text(encoding="utf-8"))
    docs = docs_from_paths(list(obj.get("paths") or []))
    idx = AI.load()
    scratch = EV / "scratch"
    ambiguous = AI.ambiguous_stems(docs)
    rows = []
    t0 = time.time()
    for i, d in enumerate(docs, 1):
        try:
            rec = E.evaluate_doc(d, idx, scratch, ambiguous)
        except Exception as ex:  # noqa: BLE001
            rec = {"verdict": "ERROR", "classes": {}, "clauses": 0, "len": 0,
                   "error": f"{type(ex).__name__}: {str(ex)[:120]}"}
        art = rec.get("artifact") or {}
        rows.append({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "round": rnd,
                     "src": src, "std_no": d["std_no"], "path": d["file_path"],
                     "verdict": rec.get("verdict"), "classes": rec.get("classes") or {},
                     "hits": sum((rec.get("classes") or {}).values()),
                     "clauses": rec.get("clauses", 0), "len": rec.get("len", 0),
                     "low": rec.get("low", 0),
                     "backend": art.get("parse_backend", "unknown"),
                     "evidence": rec.get("evidence") or {}})
        if i % 25 == 0:
            print(f"    …{i}/{len(docs)}（{time.time()-t0:.0f}s）", flush=True)
    return rows


def cmd_bootstrap(a) -> int:
    """对现有批次全部文档跑一次评估，建立初始台账（首次必跑）。"""
    paths: list[str] = []
    for bn in [x.strip() for x in a.batches.split(",") if x.strip()]:
        f = EV / f"work_batch{bn}.json"
        if f.exists():
            paths += list(json.loads(f.read_text(encoding="utf-8")).get("paths") or [])
    print(f"bootstrap：{len(paths)} 部（来自批次 {a.batches}）")
    if a.limit:
        paths = paths[:a.limit]
    rows = evaluate_list(_write_tmp_list(paths), a.round, f"bootstrap:{a.batches}")
    append_ledger(rows)
    _summary(rows, "bootstrap")
    return 0


def _write_tmp_list(paths: list[str]) -> Path:
    RV.mkdir(parents=True, exist_ok=True)
    p = RV / "_tmp.list.json"
    p.write_text(json.dumps({"n": len(paths), "paths": paths}, ensure_ascii=False),
                 encoding="utf-8")
    return p


def cmd_build(a) -> int:
    """本轮清单 = 全部问题文档 ∪ 干净文档确定性抽样。"""
    latest = load_ledger()
    limits = known_limit_classes()
    lanes: dict[str, list[str]] = {"problem": [], "gap": [], "known-limit": [], "clean": []}
    state = json.loads((HERE / "vlm_ocr_state.json").read_text(encoding="utf-8"))
    for std, r in latest.items():
        lanes.setdefault(classify_rec(r, limits), []).append(std)
    sample = pick_clean_sample(lanes.get("clean", []), a.clean, f"{SEED}|{a.round}")
    pick = lanes.get("problem", []) + lanes.get("gap", []) \
        + lanes.get("known-limit", []) + sample
    paths = []
    for std in pick:
        rec = state.get(std) or {}
        p = rec.get("pdf")
        if p and Path(p).is_file():
            paths.append(p)
    RV.mkdir(parents=True, exist_ok=True)
    obj = {"built_at": time.strftime("%Y-%m-%d %H:%M:%S"), "round": a.round,
           "rule": "全部问题文档 ∪ 干净抽样（确定性）——业主 2026-09-16 指令",
           "clean_sample_size": a.clean, "seed": SEED,
           "counts": {k: len(v) for k, v in lanes.items()},
           "problem": lanes.get("problem", []), "gap": lanes.get("gap", []),
           "known_limit": lanes.get("known-limit", []), "clean_sample": sample,
           "n": len(paths), "paths": paths}
    out = RV / f"{a.round}.list.json"
    out.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"本轮清单 {out.name}：问题 {len(lanes.get('problem',[]))} · GAP {len(lanes.get('gap',[]))}"
          f" · 已知限制 {len(lanes.get('known-limit',[]))} · 干净抽样 {len(sample)}"
          f" → 可跑 {len(paths)} 部")
    return 0


def cmd_run(a) -> int:
    list_file = RV / f"{a.round}.list.json"
    if a.list:
        list_file = Path(a.list)
    print(f"run：评估 {list_file.name}")
    rows = evaluate_list(list_file, a.round, list_file.name)
    append_ledger(rows)
    metrics = _summary(rows, a.round)
    (RV / f"{a.round}.metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def _summary(rows: list[dict], rnd: str) -> dict:
    limits = known_limit_classes()
    lanes: dict[str, int] = {}
    classes: dict[str, int] = {}
    for r in rows:
        lanes[classify_rec(r, limits)] = lanes.get(classify_rec(r, limits), 0) + 1
        for c, n in (r.get("classes") or {}).items():
            classes[c] = classes.get(c, 0) + n
    print(f"  {rnd}：{len(rows)} 部 → "
          f"问题 {lanes.get('problem',0)} · 已知限制 {lanes.get('known-limit',0)}"
          f" · 干净 {lanes.get('clean',0)} · GAP {lanes.get('gap',0)}")
    if classes:
        print("  命中类：" + ", ".join(f"{k}×{v}" for k, v in
                                     sorted(classes.items(), key=lambda kv: -kv[1])[:8]))
    return {"round": rnd, "docs": len(rows), "lanes": lanes, "classes": classes,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S")}


def cmd_report(a) -> int:
    """本轮 vs 上一轮（逐文档）→ 已修复 / 仍问题 / 新冒问题。"""
    rounds = sorted({p.name.split(".")[0] for p in RV.glob("R*.metrics.json")})
    cur = a.round or (rounds[-1] if rounds else "")
    base = a.base or (rounds[rounds.index(cur) - 1]
                      if cur in rounds and rounds.index(cur) > 0 else "")
    if not cur:
        print("没有可报告的本轮（先 run）"); return 2
    cur_rows = _rows_of(cur)
    base_rows = _rows_of(base) if base else {}
    d = diff_rounds(base_rows, cur_rows, known_limit_classes())
    print(f"\n=== {cur} vs {base or '（无基线）'} ===")
    print(f"  已修复 {len(d['fixed'])} · 仍问题 {len(d['still'])} · "
          f"**新冒问题 {len(d['new'])}** · 新出现的类 {d['new_classes'] or '（无）'}")
    for k in d["new"][:15]:
        print(f"    ⚠ 新问题 {k[:60]} → {list((cur_rows[k].get('classes') or {}).keys())}")
    for k in d["still"][:10]:
        print(f"    · 仍问题 {k[:58]} → {list((cur_rows[k].get('classes') or {}).keys())}")
    md = [f"# 每轮回归报告 {cur}（基线 {base or '无'}）", "",
          f"- 已修复：**{len(d['fixed'])}** 部", f"- 仍问题：**{len(d['still'])}** 部",
          f"- 新冒问题：**{len(d['new'])}** 部", f"- 新出现的类：{d['new_classes'] or '（无）'}",
          "", "## 新冒问题（回归信号，优先处理）"]
    md += [f"- `{k}` → {list((cur_rows[k].get('classes') or {}).keys())}" for k in d["new"]] or ["- （无）"]
    md += ["", "## 仍问题"]
    md += [f"- `{k}` → {list((cur_rows[k].get('classes') or {}).keys())}" for k in d["still"]] or ["- （无）"]
    (RV / f"{cur}.report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"  → {RV / (cur + '.report.md')}")
    return 0


def _rows_of(rnd: str) -> dict[str, dict]:
    p = RV / f"{rnd}.metrics.json"
    if not p.exists():
        return {}
    out: dict[str, dict] = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines() if LEDGER.exists() else []:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if r.get("round") == rnd and r.get("std_no"):
            out[str(r["std_no"])] = r
    return out


def cmd_all(a) -> int:
    cmd_build(a)
    cmd_run(a)
    return cmd_report(a)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("build", cmd_build), ("run", cmd_run),
                     ("report", cmd_report), ("all", cmd_all),
                     ("bootstrap", cmd_bootstrap)):
        s = sub.add_parser(name)
        s.add_argument("--round", default="R001")
        s.add_argument("--base", default="")
        s.add_argument("--clean", type=int, default=30,
                       help="干净文档抽样部数（默认 30）")
        s.add_argument("--list", default="", help="run：指定清单文件")
        s.add_argument("--batches", default="2,3,4,5,6", help="bootstrap：批次号")
        s.add_argument("--limit", type=int, default=0, help="bootstrap：只跑前 N 部")
        s.set_defaults(func=fn)
    a = ap.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    main()
