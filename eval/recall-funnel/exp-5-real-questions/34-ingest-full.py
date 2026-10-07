"""全量入库器：**强制性国标 803 本 + 法律法规 1,563 个**（走生产入口，可续跑）。

## 业主指示
2026-10-07："OCR 好了，你把所有强制性国标和法律法规切分入库"。

## 安全设计（三层）
 ① **真库已备份**：`%APPDATA%\\KnowledgeStation\\backups\\knowledge-<时间戳>.db`（2.39 GB）⇒ 可一键退回；
 ② **跑在真库的干净副本上**：`KS_DATA_DIR=var/tmp/ingest-trial/data` ⇒ 引擎**根本不知道真库路径**；
 ③ **硬护栏**：开始前断言 `get_settings().db_path` 落在副本目录下，否则立刻退出。

## 走的是生产入口（没有另写一套）
 · **国标**：`pipeline.run_full_ingest(pdf_path, std_no, name, product_dir=<MinerU 产物目录>)`
   —— `product_dir` 是既有的"复用已有 OCR 产物、零重解析"通道；
 · **法规**：`law_text.ingest_law_text(text, std_no, name)`。

## 可续跑
每件处理完立刻追加一行到 `var/tmp/ingest-full/journal.jsonl`；重跑时跳过 `status=ok` 的件。

用法：
  .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\34-ingest-full.py --phase gb
  .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\34-ingest-full.py --phase law
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
JOURNAL_DIR = ROOT / "var" / "tmp" / "ingest-full"
JOURNAL = JOURNAL_DIR / "journal.jsonl"
SUMMARY = HERE / "ingest-full-summary.json"

# ⚠ 必须在 import src.* **之前**设好
os.environ["KS_DATA_DIR"] = str(TRIAL)
os.environ.setdefault("KS_MODELS_DIR", str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(ROOT))

GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
LAW_ROOT = Path("D:/AI/work space/标准/法律法规")
DB = TRIAL / "database" / "knowledge.db"
SUFFIX = ".mineru-4.0.10-vlm"
STD_RE = re.compile(r"^(GB(?:/T|/Z)?\s*\d+(?:\.\d+)?\s*-\s*\d{2,4})")


def _load_done() -> set[str]:
    done: set[str] = set()
    if JOURNAL.exists():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:                                               # noqa: BLE001
                continue
            if r.get("status") in ("ok", "duplicate", "standard_exists"):
                done.add(r["key"])
    return done


def _append(rec: dict) -> None:
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _guard() -> None:
    from src.core.config import get_settings
    dbp = get_settings().db_path.resolve()
    print(f"[guard] 引擎将写入：{dbp}", flush=True)
    if TRIAL.resolve() not in dbp.parents:
        print(f"[guard] ⛔ 目标不在副本下（应在 {TRIAL.resolve()} 之下）—— 拒绝执行")
        sys.exit(2)
    print("[guard] ✅ 在副本下；真库不会被写（且已另有备份）", flush=True)


def collect_gb() -> list[dict]:
    pdfs = [p for p in GB_ROOT.rglob("*") if p.suffix.lower() == ".pdf"]
    by_stem = {p.stem: p for p in pdfs}
    import sqlite3
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    have = {r[0] for r in c.execute("SELECT standard_no FROM doc_meta")}
    c.close()
    out = []
    for d in GB_ROOT.rglob("*"):
        if not (d.is_dir() and d.name.endswith(SUFFIX)) or not (d / "middle_json.json").exists():
            continue
        stem = d.name[: -len(SUFFIX)]
        m = STD_RE.match(stem)
        pdf = by_stem.get(stem)
        if not m or pdf is None:
            continue
        no = re.sub(r"\s+", " ", m.group(1)).strip()
        out.append({"key": f"gb::{no}", "std_no": no,
                    "name": stem[m.end():].strip() or no,
                    "pdf": str(pdf), "product_dir": str(d)})
    return out


def collect_law() -> list[dict]:
    out = []
    for p in sorted(LAW_ROOT.rglob("*.md")):
        if p.stem in ("README", "_index") or p.name.startswith("_"):
            continue
        # ⚠ **`案例/` 下不是法规，是判例简介**（"常某某诉许某网络服务合同案"）。
        #   2026-10-07 实测：它们既没有「第X条」也没有「一、二、三、」编号，
        #   按法规入库必然报"未识别到条文"（当时 18 件）。**如实排除，不硬塞。**
        rel = p.relative_to(LAW_ROOT).as_posix()
        if rel.startswith("案例/"):
            continue
        name = re.sub(r"\(\d{4}-\d{2}-\d{2}\)$", "", p.stem)
        m = re.search(r"\((\d{4}-\d{2}-\d{2})\)$", p.stem)
        out.append({"key": f"law::{rel}", "name": name, "path": str(p),
                    "date": (m.group(1) if m else None)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("gb", "law", "both"), default="both")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 件（0=全部，用于抽样验证）")
    args = ap.parse_args()

    _guard()
    import sqlite3
    from src.core.storage.sqlite_db import get_db_connection

    # busy_timeout（本仓踩过的坑：并发写会 database is locked）
    try:
        conn0 = get_db_connection()
        conn0.execute("PRAGMA busy_timeout=60000")
    except Exception as e:                                                  # noqa: BLE001
        print(f"[warn] busy_timeout 设置失败：{type(e).__name__}")

    done = _load_done()
    print(f"[run] 已完成（journal 记着）= {len(done)} 件", flush=True)

    results = {"phase": args.phase, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
               "ok": 0, "duplicate": 0, "standard_exists": 0, "error": 0, "skipped": 0,
               "errors": [], "by_phase": {}}

    def run_gb() -> None:
        items = collect_gb()
        if args.limit:
            items = items[: args.limit]
        print(f"\n[A] 国标：候选 {len(items)} 本", flush=True)
        from src.core.ingestion.pipeline import run_full_ingest
        ok = err = skip = 0
        for i, it in enumerate(items, 1):
            if it["key"] in done:
                skip += 1
                continue
            t0 = time.perf_counter()
            try:
                r = run_full_ingest(Path(it["pdf"]), it["std_no"], it["name"],
                                    doc_type="standard", legal_hierarchy="GB",
                                    product_dir=Path(it["product_dir"]))
                st = r.get("status", "?")
                rec = {"key": it["key"], "kind": "gb", "std_no": it["std_no"],
                       "status": st, "doc_id": r.get("doc_id"),
                       "clauses": r.get("total_clauses"), "sec": round(time.perf_counter() - t0, 1)}
                if st in ("ok", "duplicate", "standard_exists"):
                    ok += 1
                else:
                    err += 1
                    results["errors"].append({**rec, "message": str(r.get("message"))[:160]})
            except Exception as e:                                          # noqa: BLE001
                err += 1
                rec = {"key": it["key"], "kind": "gb", "std_no": it["std_no"],
                       "status": "exception", "error": f"{type(e).__name__}: {e}"[:200]}
                results["errors"].append(rec)
            _append(rec)
            if i % 25 == 0 or i == len(items):
                print(f"    {i}/{len(items)}  ok={ok} err={err} skip={skip}  "
                      f"最新：{it['std_no']} → {rec.get('status')}", flush=True)
        results["by_phase"]["gb"] = {"ok": ok, "err": err, "skip": skip, "total": len(items)}

    def run_law() -> None:
        items = collect_law()
        if args.limit:
            items = items[: args.limit]
        print(f"\n[B] 法规：候选 {len(items)} 个", flush=True)
        from src.core.ingestion.law_text import ingest_law_text
        ok = err = skip = 0
        for i, it in enumerate(items, 1):
            if it["key"] in done:
                skip += 1
                continue
            t0 = time.perf_counter()
            try:
                text = Path(it["path"]).read_text(encoding="utf-8", errors="ignore")
                r = ingest_law_text(text, standard_no=f"{it['name']}(OCR采集)",
                                    standard_name=it["name"], legal_hierarchy="法律",
                                    effective_from=it.get("date"),
                                    source_marker=f"lawrefbook://{Path(it['path']).name}",
                                    source_url="https://github.com/RanKKI/LawRefBook",
                                    # 2026-10-07：极少数**真的没有任何条款编号**的法规
                                    # （263 字一整段的批复、段内编号列表的罪名意见等，实测 8 件），
                                    # 走生产既有的"整篇作一条（编号=全文）"开关 ——
                                    # 宁可整篇可检索，也不要整件进不了库。
                                    fallback_single_clause=True)
                st = r.get("status", "?")
                rec = {"key": it["key"], "kind": "law", "name": it["name"], "status": st,
                       "doc_id": r.get("doc_id"), "clauses": r.get("total_clauses"),
                       "sec": round(time.perf_counter() - t0, 1)}
                if st in ("ok", "duplicate", "standard_exists"):
                    ok += 1
                else:
                    err += 1
                    results["errors"].append({**rec, "message": str(r.get("message"))[:160]})
            except Exception as e:                                          # noqa: BLE001
                err += 1
                rec = {"key": it["key"], "kind": "law", "name": it["name"],
                       "status": "exception", "error": f"{type(e).__name__}: {e}"[:200]}
                results["errors"].append(rec)
            _append(rec)
            if i % 100 == 0 or i == len(items):
                print(f"    {i}/{len(items)}  ok={ok} err={err} skip={skip}  "
                      f"最新：{it['name'][:26]} → {rec.get('status')}", flush=True)
        results["by_phase"]["law"] = {"ok": ok, "err": err, "skip": skip, "total": len(items)}

    if args.phase in ("gb", "both"):
        run_gb()
    if args.phase in ("law", "both"):
        run_law()

    # ---- 收尾统计 ----
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    counts = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("doc_meta", "clause_revision")}
    try:
        from src.core.storage.sqlite_db import load_vec_extension
        load_vec_extension(c)
        counts["clause_vec"] = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    except Exception as e:                                                  # noqa: BLE001
        counts["clause_vec"] = f"未取到：{type(e).__name__}"
    c.close()
    results["db_after"] = counts
    results["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    SUMMARY.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[run] 库现状 = {counts}")
    print(f"[run] 汇总 = {json.dumps(results['by_phase'], ensure_ascii=False)}")
    print(f"已写 {SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
