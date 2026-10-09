"""exp-14 的**替代仪器对照**（预注册的那条已失效，见 README §五）。

## 为什么需要替代
预注册写的是「A0 逐条 `fused.gold_rank` 必须与 `eval/recall-funnel/funnel-per-query.jsonl` 0 处不同」，
**实测失配 6/120**。查明原因是**参照物过期**：那份文件 mtime = **2026-10-06 18:06**，
而真库是**活的、会长**的 —— 同批提问的 FTS 候选池全线上涨（如 i=166 54,359 → **68,475**、
i=113 29,170 → **37,911**）⇒ 池子成分变了，`fused` 的名次自然跟着变。
⇒ **通用教训：仪器对照的参照物必须是"同期重跑"，不能是历史产物**（活库上历史读数不可复现）。

## 替代的两条（本脚本产出 `determinism.json`）
 1. **同会话确定性**：120 条 A0 各跑 **两遍**，两遍的 `fused` 名次必须**逐条相同**；
    并与 `runs.jsonl` 里已落盘的 A0 再比一次（三方一致）。
 2. **改写钩子零泄漏**：对 20 条，比较「装上 A0 改写钩子」与「**完全不装钩子**」的 `fused` ——
    必须逐条相同。A0 的钩子是恒等映射，若不相同 ⇒ 钩子污染了基线，后面所有 Δ 都不成立。

用法： `.venv\\Scripts\\python.exe eval\\recall-funnel\\exp-14-fused-rewrite\\determinism.py`
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
RUNS = HERE / "runs.jsonl"
OUT = HERE / "determinism.json"
LEAK_N = 20


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    import funnel
    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval import embedder

    RULER = _load("exp14_run_for_det", HERE / "run.py")
    E13 = RULER._load_e13()

    mtime0 = DB.stat().st_mtime
    conn = funnel.ro_conn(DB)
    he._conn = lambda: conn

    items = RULER._headline([json.loads(l) for l in
                             (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
                             .read_text(encoding="utf-8").splitlines() if l.strip()])
    d1_map = {json.loads(l)["i"]: json.loads(l)["d1_query"]
              for l in (ROOT / "eval" / "recall-funnel" / "exp-13-query-rewrite"
                        / "per-query.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    ledger = {}
    for l in RUNS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            if r["arm"] == "A0_raw":
                ledger[r["i"]] = r["fused_rank"]

    _orig_embed = embedder.embed_query
    _orig_fts = he._fts_query

    def fused_ids(raw: str, arm: str, d1_query: str, patch: bool) -> list[str]:
        if patch:
            vec_q = RULER.arm_vec_query(raw, arm, d1_query, E13)
            fts_q = RULER.arm_fts_query(raw, arm, d1_query)

            def _embed(q):
                return _orig_embed(vec_q if q == raw else q)

            def _fts(q):
                return _orig_fts(fts_q if q == raw else q)

            embedder.embed_query = _embed
            he._fts_query = _fts
        try:
            found = he.search_with_details(raw, top_k=1000, rerank=False,
                                           boost_bookmarks=False, expand_chain=False)
        finally:
            embedder.embed_query = _orig_embed
            he._fts_query = _orig_fts
        return [r.clause_revision_id for r in found["results"]]

    def rank(fused: list[str], gold: str):
        return (fused.index(gold) + 1) if gold in fused else None

    t0 = time.perf_counter()
    pass1, pass2, no_patch = {}, {}, {}
    for n, it in enumerate(items, 1):
        raw, gold, d1q = it["query"], it["v2"]["gold_cr_id"], d1_map[it["i"]]
        pass1[it["i"]] = rank(fused_ids(raw, "A0_raw", d1q, True), gold)
        pass2[it["i"]] = rank(fused_ids(raw, "A0_raw", d1q, True), gold)
        if n <= LEAK_N:
            no_patch[it["i"]] = rank(fused_ids(raw, "A0_raw", d1q, False), gold)
        if n % 20 == 0 or n == len(items):
            el = time.perf_counter() - t0
            print(f"[det] {n}/{len(items)} 用时 {el:.0f}s", flush=True)

    det_mism = [(i, pass1[i], pass2[i]) for i in pass1 if pass1[i] != pass2[i]]
    ledger_mism = [(i, ledger.get(i), pass1[i]) for i in pass1 if ledger.get(i) != pass1[i]]
    leak_mism = [(i, pass1[i], no_patch[i]) for i in no_patch if pass1[i] != no_patch[i]]

    print(f"[det] 两遍不同 = {len(det_mism)} 处")
    print(f"[det] 与 runs.jsonl 不同 = {len(ledger_mism)} 处")
    print(f"[det] 钩子泄漏（A0 装钩 vs 不装）= {len(leak_mism)} 处 / {len(no_patch)}")

    mtime1 = DB.stat().st_mtime
    OUT.write_text(json.dumps({
        "note": "exp-14 替代仪器对照：同会话确定性 + 改写钩子零泄漏（原预注册那条已失效，见 README §五）",
        "repeat_same_session": {"compared": len(pass1), "mismatch_count": len(det_mism),
                                "samples": det_mism[:5]},
        "ledger_consistency": {"compared": len(pass1), "mismatch_count": len(ledger_mism),
                               "samples": ledger_mism[:5]},
        "patch_leak_check": {"compared": len(no_patch), "mismatch_count": len(leak_mism),
                             "samples": leak_mism[:5]},
        "db_mtime_unchanged": mtime0 == mtime1,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[det] 已写 {OUT}")
    if det_mism or ledger_mism or leak_mism or mtime0 != mtime1:
        print("[det] ❌ 有失配")
        return 1
    print("[det] ✅ 三条全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
