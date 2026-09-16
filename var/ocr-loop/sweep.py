"""全量扫描（sweep）：对**库里所有文档**做一遍体检，存快照并与上次逐项对比。

设计要点（2026-09-15 收敛循环 v2，用户要求「每修一个 bug 就全量重扫、与上次对比」）：

1. **两层扫描**
   - `--tier db`（默认）：审**库里真实内容**（clause_revision）→ 这是"现在这库
     到底有没有问题"的权威口径，也是跨轮对比的基准。
   - `--tier project`：**不落库**地从缓存解析产物重跑切分（`_cached_parse_result`
     + `load_middle_items` + `split_items_into_clauses` + `build_clause_models` 的
     文本层），得到"若现在重导会是什么样"——用于预测修复收益、决定要不要重导。
2. **快照**：`var/ocr-loop/sweeps/<sweep_id>.json`，含
   - per-doc：条款数、低置信数、每类命中数、正文哈希（用于识别内容变化）
   - summary：类 → 命中文档数/条款数；检测器集哈希；库指纹
   - `latest.json` 指针（供 diff 找上一次）
3. **对比**（`--diff` 或每次自动）：与上一次快照比，输出
   - 类级：新增/清除（**只在检测器集未变时**才当作真实变化，否则标记"仪器变更"）
   - 文档级：新命中文档 / 已清除文档
   - 指标级：条款总数、低置信条数、各类总量
   - 结论：修复对全库是否有效
4. **收敛判据**：达线类（≥3 文档）为空 **且** diff 无新增类/新增文档。

用法：
  python var/ocr-loop/sweep.py                 # db 层扫描 + 与上次对比
  python var/ocr-loop/sweep.py --tier project  # 预测层（不落库）
  python var/ocr-loop/sweep.py --no-diff       # 只存快照
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VARDIR = Path(__file__).resolve().parent
ROOT = VARDIR.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(VARDIR))

import audit_text as A          # noqa: E402
import classify as C            # noqa: E402

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
SWEEPDIR = VARDIR / "sweeps"
LATEST = SWEEPDIR / "latest.json"
FIX_LINE = 3          # 同类 ≥3 部文档 = 达修复线（与循环协议一致）


def detector_hash() -> str:
    """检测器集指纹：源文本 + classify 的判据一起哈希（仪器变更要能被识别）。"""
    h = hashlib.sha256()
    for p in (VARDIR / "audit_text.py", VARDIR / "classify.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


def corpus_fingerprint() -> str:
    """库指纹：每文档 (standard_no, 条款数, 正文长度) 合并哈希——**内容变了才变**。

    2026-09-15（收敛循环 v2）：**不得把 doc_id 计入哈希**。全库复用重导会给
    每部文档分配新 ULID，doc_id 入哈希会让指纹每轮都变，把「身份换了」误读成
    「内容变了」，diff 全成噪声。
    """
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    h = hashlib.sha256()
    for r in conn.execute(
            "SELECT d.standard_no, COUNT(*) n, "
            "COALESCE(SUM(LENGTH(c.content_text)),0) ln "
            "FROM clause_revision c JOIN doc_meta d ON c.doc_id=d.doc_id "
            "GROUP BY d.standard_no ORDER BY d.standard_no"):
        h.update(f"{r['standard_no']}|{r['n']}|{r['ln']}".encode())
    conn.close()
    return h.hexdigest()[:12]


def _std_of(snap: dict) -> dict[str, str]:
    """doc_id → standard_no 映射。"""
    return {did: (d.get("standard_no") or did)
            for did, d in snap.get("docs", {}).items()}


def class_std_sets(snap: dict) -> dict[str, set[str]]:
    """类 → {standard_no}。

    **必须从全量逐文档数据算**：`summary.classes[*].doc_ids` 只保留前 60 个且按
    doc_id 排序，重导换 id 后窗口内成员会漂移，拿它做跨轮集合差会凭空造出
    「新增命中文档」，让收敛判据永远不成立。
    """
    out: dict[str, set[str]] = {}
    for did, d in snap.get("docs", {}).items():
        std = d.get("standard_no") or did
        for cls in d.get("classes", {}):
            out.setdefault(cls, set()).add(std)
    return out


def audit_db() -> dict:
    """tier=db：审库里全部正文条款。"""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT d.doc_id, d.standard_no, c.clause_number, c.content_text, "
        "c.ocr_confidence FROM clause_revision c JOIN doc_meta d ON c.doc_id=d.doc_id "
        "WHERE c.content_type='normal'").fetchall()
    conn.close()
    per_doc: dict[str, dict] = {}
    cls_docs: dict[str, set] = defaultdict(set)
    cls_clauses = Counter()
    for r in rows:
        doc = per_doc.setdefault(r["doc_id"], {
            "standard_no": r["standard_no"], "clauses": 0, "low": 0,
            "classes": Counter(), "len": 0})
        doc["clauses"] += 1
        doc["len"] += len(r["content_text"] or "")
        if (r["ocr_confidence"] or 1.0) < 0.85:
            doc["low"] += 1
        for cls in A.audit_clause(r["content_text"]):
            doc["classes"][cls] += 1
            cls_docs[cls].add(r["doc_id"])
            cls_clauses[cls] += 1
        for cls in C.classify_clause(r["clause_number"] or "",
                                     r["content_text"] or "",
                                     r["ocr_confidence"] or 1.0):
            doc["classes"][cls] += 1
            cls_docs[cls].add(r["doc_id"])
            cls_clauses[cls] += 1
    return _pack(per_doc, cls_docs, cls_clauses, tier="db")


def audit_project() -> dict:
    """tier=project：从缓存产物重跑切分（不落库），预测重导后的状态。"""
    import sqlite3 as sq
    from src.core.ingestion.pipeline import (
        _cached_parse_result, build_clause_models, load_middle_items,
        load_middle_items_from_blocks, split_items_into_clauses)
    conn = sq.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sq.Row
    docs = conn.execute("SELECT doc_id, standard_no, standard_name, file_path "
                        "FROM doc_meta").fetchall()
    conn.close()
    per_doc: dict[str, dict] = {}
    cls_docs: dict[str, set] = defaultdict(set)
    cls_clauses = Counter()
    skipped = []
    for d in docs:
        p = Path(d["file_path"] or "")
        if not p.exists() and p.suffix == "":
            p = Path(str(p) + ".pdf")
        if not p.exists():
            skipped.append(d["standard_no"])
            continue
        res = _cached_parse_result(ROOT and Path(os.environ["APPDATA"])
                                   / "KnowledgeStation" / "parse_out" / d["doc_id"], p)
        if res is None:
            skipped.append(d["standard_no"])
            continue
        try:
            if res.get("deep_output"):
                from src.core.ingestion.middle_locator import find_middle_files
                mids = find_middle_files(Path(res["deep_output"]))
                if not mids:
                    skipped.append(d["standard_no"])
                    continue
                items, page_sizes = load_middle_items(mids[0])
            else:
                items, _ = load_middle_items_from_blocks(res["blocks"])
                geos = res.get("geometries") or {}
                page_sizes = {int(k) - 1: (float(v["width"]), float(v["height"]))
                              for k, v in geos.items()}
            split = split_items_into_clauses(items)
            models, _ = build_clause_models("project", d["standard_no"], "standard",
                                            split, page_sizes)
        except Exception as e:  # noqa: BLE001
            skipped.append(f"{d['standard_no']}({type(e).__name__})")
            continue
        pd = per_doc.setdefault(d["doc_id"], {
            "standard_no": d["standard_no"], "clauses": 0, "low": 0,
            "classes": Counter(), "len": 0})
        for m in models:
            pd["clauses"] += 1
            pd["len"] += len(m.content_text or "")
            if (m.ocr_confidence or 1.0) < 0.85:
                pd["low"] += 1
            for cls in A.audit_clause(m.content_text):
                pd["classes"][cls] += 1
                cls_docs[cls].add(d["doc_id"])
                cls_clauses[cls] += 1
    out = _pack(per_doc, cls_docs, cls_clauses, tier="project")
    out["skipped_no_cache"] = skipped[:40]
    out["skipped_count"] = len(skipped)
    return out


def _pack(per_doc: dict, cls_docs: dict, cls_clauses: Counter, tier: str) -> dict:
    docs = {}
    for doc_id, d in per_doc.items():
        docs[doc_id] = {"standard_no": d["standard_no"],
                        "clauses": d["clauses"], "low": d["low"], "len": d["len"],
                        "classes": dict(d["classes"])}
    summary = {
        "docs": len(docs),
        "clauses": sum(d["clauses"] for d in docs.values()),
        "low": sum(d["low"] for d in docs.values()),
        "classes": {cls: {"docs": len(ids), "clauses": cls_clauses[cls],
                          "doc_ids": sorted(ids)[:60]}
                    for cls, ids in sorted(cls_docs.items(),
                                           key=lambda kv: -len(kv[1]))},
        "over_line": sorted([c for c, ids in cls_docs.items() if len(ids) >= FIX_LINE],
                            key=lambda c: -len(cls_docs[c])),
    }
    return {"sweep_id": time.strftime("%Y%m%d-%H%M%S"), "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tier": tier, "detector": detector_hash(),
            "corpus": corpus_fingerprint(), "summary": summary, "docs": docs}


def load_latest() -> dict | None:
    if LATEST.exists():
        try:
            return json.loads(LATEST.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def diff(cur: dict, prev: dict | None) -> dict:
    """与上次快照逐项对比；检测器集不同则标记仪器变更（避免误读成内容变化）。"""
    if prev is None:
        return {"first_sweep": True}
    same_detector = cur["detector"] == prev["detector"]
    cc, pc = cur["summary"]["classes"], prev["summary"]["classes"]
    new_classes, cleared, changed = {}, {}, {}
    for cls in sorted(set(cc) | set(pc)):
        nd = cc.get(cls, {}).get("docs", 0)
        od = pc.get(cls, {}).get("docs", 0)
        if nd and not od:
            new_classes[cls] = nd
        elif od and not nd:
            cleared[cls] = od
        elif nd != od:
            changed[cls] = {"before": od, "after": nd}
    newly_hit, healed = [], []
    # 2026-09-15：跨轮对比用 **standard_no**（稳定身份）。重导会给每部文档换
    # doc_id，按 doc_id 做集合差会把全体文档报成「新增命中」，收敛判据永不成立。
    cur_cls, prev_cls = class_std_sets(cur), class_std_sets(prev)
    for cls in set(cc) | set(pc):
        cd = cur_cls.get(cls, set())
        pd_ = prev_cls.get(cls, set())
        newly_hit += [f"{cls}:{i}" for i in sorted(cd - pd_)]
        healed += [f"{cls}:{i}" for i in sorted(pd_ - cd)]
    return {
        "first_sweep": False,
        "same_detector": same_detector,
        "instrument_changed": not same_detector,
        "corpus_changed": cur["corpus"] != prev["corpus"],
        "docs": {"before": prev["summary"]["docs"], "after": cur["summary"]["docs"]},
        "clauses": {"before": prev["summary"]["clauses"], "after": cur["summary"]["clauses"]},
        "low": {"before": prev["summary"]["low"], "after": cur["summary"]["low"]},
        "new_classes": new_classes, "cleared_classes": cleared,
        "changed_classes": changed,
        "newly_hit_docs": newly_hit[:60], "healed_docs": healed[:60],
        "still_over_line": cur["summary"]["over_line"],
    }


def converged(s: dict, d: dict) -> tuple[bool, str]:
    """收敛判据：达线类为空 且 无新增类/新增命中文档。"""
    over = s["summary"]["over_line"]
    if over:
        return False, f"仍有达线类：{', '.join(over)}"
    if not d.get("first_sweep"):
        if d.get("new_classes"):
            return False, f"出现新类：{', '.join(d['new_classes'])}"
        if d.get("newly_hit_docs"):
            return False, f"新增命中文档 {len(d['newly_hit_docs'])} 个"
    return True, "全库扫描无达线问题"


def main() -> None:
    args = sys.argv[1:]
    tier = args[args.index("--tier") + 1] if "--tier" in args else "db"
    snap = audit_db() if tier == "db" else audit_project()
    prev = load_latest() if tier == "db" else None
    d = diff(snap, prev)

    SWEEPDIR.mkdir(parents=True, exist_ok=True)
    (SWEEPDIR / f"{snap['sweep_id']}-{tier}.json").write_text(
        json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    if tier == "db" and "--no-diff" not in args:
        LATEST.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

    s = snap["summary"]
    print(f"=== 全量扫描 {snap['sweep_id']}（tier={tier}）===")
    print(f"文档 {s['docs']} · 条款 {s['clauses']} · 低置信(<0.85) {s['low']}")
    print(f"检测器 {snap['detector']} · 库指纹 {snap['corpus']}")
    if tier == "project":
        print(f"无缓存跳过 {snap.get('skipped_count', 0)} 部：{snap.get('skipped_no_cache', [])[:8]}")
    print("\n类 → 命中文档数 / 条款数")
    for cls, v in s["classes"].items():
        mark = " ★达线" if v["docs"] >= FIX_LINE else ""
        print(f"  {cls:26} {v['docs']:4} 部 / {v['clauses']:5} 条{mark}")

    if not d.get("first_sweep"):
        print("\n=== 与上次对比 ===")
        if d["instrument_changed"]:
            print("  ⚠ 检测器集已变（instrument_changed）——类级变化含仪器影响，勿直接归因于修复")
        print(f"  文档 {d['docs']['before']} → {d['docs']['after']} · "
              f"条款 {d['clauses']['before']} → {d['clauses']['after']} · "
              f"低置信 {d['low']['before']} → {d['low']['after']}")
        if d["cleared_classes"]:
            print(f"  已清除类：{d['cleared_classes']}")
        if d["changed_classes"]:
            print(f"  数量变化：{d['changed_classes']}")
        if d["new_classes"]:
            print(f"  ⚠ 新增类：{d['new_classes']}")
        if d["healed_docs"]:
            print(f"  已修复文档（{len(d['healed_docs'])}）：{d['healed_docs'][:12]}")
        if d["newly_hit_docs"]:
            print(f"  ⚠ 新命中文档（{len(d['newly_hit_docs'])}）：{d['newly_hit_docs'][:12]}")
    ok, why = converged(snap, d)
    print(f"\n收敛判定：{'✅ 收敛' if ok else '❌ 未收敛'} —— {why}")
    print(f"快照：var/ocr-loop/sweeps/{snap['sweep_id']}-{tier}.json")


if __name__ == "__main__":
    main()
