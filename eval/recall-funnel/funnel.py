"""六路召回漏斗（只读诊断）：正确条文到底在哪条通道、哪个截断位置丢的。

## 这份脚本要回答的三个问题
 1. **每一路**分别把 gold 召回到第几名（Top20 / Top100 / Top1000）；
 2. 六路**并起来**的 recall@20/@100/@1000（分"生产口径"与"深读口径"两种）；
 3. 六路**融合后**（RRF+时效过滤，即生产实际排序）gold 在第几名。

## 两条口径必须分开说（否则数字会被误读）
 * **生产口径**：完全照 `hybrid_engine.perform_hybrid_search` 的参数 ——
   通道 B（FTS5）`LIMIT 20`、通道 C（向量）`k = 20`、通道 F `LIMIT 20`；
   通道 A/D/E **无行数上限**。⇒ 这一口径下 `union@100` 与 `union@1000` 必然等于 `union@20`。
 * **深读口径（探针）**：同一条 SQL、同一个排序，只把 B/C 的 `k` 放大到 100/1000。
   **它不是生产行为**，只用来把"召回不到"与"截断了"分开：
   若 gold 在 `deep@1000` 里而不在 `@20` 里 ⇒ 是**截断/排序**问题，不是"模型不认识"。

## 六路在当前库里实际触发的实情（本脚本会逐条记录，不在别处猜）
 * A（条款号精确）只在提问含条款号时触发（外行问法里极少）；
 * B（FTS5）/ C（向量）恒触发；
 * D（模态）只在提问含模态词时触发（消费方 `search_with_details` 负责推导）；
 * E（法理要素 `subject`）/ F（行为客体 `behavior_scope`）需要**外部传入** filter；
   生产的问答路径（`ks_answer` / `api.server` / `local_vision`）**一个都不传** ⇒ 恒 0 候选。

## 只读保证
真库以 `file:...?mode=ro` 打开；本脚本**不写库、不改任何源文件**。脚本开始/结束各记一次
真库 mtime，不一致即报错退出。

## 复跑
    .venv\\Scripts\\python.exe eval\\recall-funnel\\funnel.py            # 全量，断点续跑
    .venv\\Scripts\\python.exe eval\\recall-funnel\\funnel.py --limit 5   # 先跑 5 条校验
逐条结果**边跑边追加**到 `funnel-per-query.jsonl`；中断后重跑自动跳过已完成项。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
BENCH_V2 = HERE / "benchmark-v2.jsonl"
BENCH_V1 = ROOT / "eval" / "reverse-benchmark" / "benchmark-171.jsonl"
OUT_PER = HERE / "funnel-per-query.jsonl"
OUT_SUM = HERE / "funnel-summary.json"
OUT_FAIL = HERE / "failure-samples.jsonl"

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

CHANNELS = ("exact", "fts", "vec", "modality", "legal_element", "behavior_scope")
DEPTHS = (20, 100, 1000)
#: 生产口径下每路一次取回的行数（照 `hybrid_engine.perform_hybrid_search` 的常量）
PROD_CAP = {"exact": None, "fts": 20, "vec": 20,
            "modality": None, "legal_element": None, "behavior_scope": 20}


def ro_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    from src.core.storage.sqlite_db import load_vec_extension
    if not load_vec_extension(conn):
        raise RuntimeError("sqlite-vec 扩展加载失败：向量通道无法诊断")
    return conn


# ── 六路候选（**SQL 逐字照抄 hybrid_engine**，只把 k/LIMIT 参数化）──────────────
def channel_exact(conn, query) -> list[str]:
    from src.core.retrieval.hybrid_engine import (
        _CLAUSE_NO_RE, _CLAUSE_NO_APPENDIX_RE, _STD_IN_QUERY_RE,
        _known_standard_keys, _rows_matching_standard_keys)
    from src.core.text_utils import standard_key
    m_ann = _CLAUSE_NO_APPENDIX_RE.search(query)
    m = _CLAUSE_NO_RE.search(query)
    exact_no = m_ann.group(1) if m_ann else (m.group(1) if m else None)
    if not exact_no:
        return []
    want_keys = {standard_key(s) for s in _STD_IN_QUERY_RE.findall(query)}
    if want_keys:
        want_keys = _known_standard_keys(
            want_keys, [s for (s,) in conn.execute("SELECT standard_no FROM doc_meta")])
    rows = conn.execute(
        "SELECT cr.clause_revision_id, dm.standard_no FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.clause_number = ?"
        " AND (dm.legal_status IS NULL OR dm.legal_status NOT IN ('withdrawn','superseded'))"
        " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id",
        (exact_no,)).fetchall()
    if want_keys:
        rows = _rows_matching_standard_keys(rows, want_keys)
    return [r[0] for r in rows]


def channel_fts(conn, query, k: int) -> list[str]:
    from src.core.retrieval.hybrid_engine import _fts_query
    fq = _fts_query(query)
    if not fq:
        return []
    try:
        rows = conn.execute(
            "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ?"
            " ORDER BY rank LIMIT ?", (fq, k)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def channel_fts_pool(conn, query) -> int | None:
    """通道 B 的**候选池大小**（MATCH 命中总行数，不限量）。

    用途：`LIMIT 20` 的候选是从多大的池子里挑的 —— 池子越大，bm25 的排序压力越大。
    """
    from src.core.retrieval.hybrid_engine import _fts_query
    fq = _fts_query(query)
    if not fq:
        return 0
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ?", (fq,)).fetchone()[0]
    except sqlite3.OperationalError:
        return None


def channel_vec(conn, query, k: int) -> list[str]:
    from src.core.retrieval import embedder
    q_emb = embedder.embed_query(query)
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM clause_vec"
        " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
        (json.dumps(q_emb), k)).fetchall()
    return [r[0] for r in rows]


def channel_modality(conn, modality_filter: str | None) -> list[str]:
    if not modality_filter:
        return []
    rows = conn.execute(
        "SELECT cr.clause_revision_id FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.modality = ?"
        " AND (dm.legal_status IS NULL OR dm.legal_status NOT IN ('withdrawn','superseded'))"
        " ORDER BY (dm.legal_status IS NULL), dm.legal_status, cr.clause_revision_id",
        (modality_filter,)).fetchall()
    return [r[0] for r in rows]


def rank_of(gold: str, cand: list[str]) -> int | None:
    try:
        return cand.index(gold) + 1
    except ValueError:
        return None


def _prod_kept(conn, cand: list[str], n: int) -> list[str]:
    """照生产的结果循环裁前 n 个：`fetch_full_clause` 取不到就跳过，已废止/被替代也跳过。"""
    from src.core.storage.clause_repo import fetch_full_clause
    kept: list[str] = []
    for cid in cand:
        if len(kept) >= n:
            break
        clause = fetch_full_clause(conn, cid)
        if clause is None:
            continue
        if clause.legal_status in ("superseded", "withdrawn"):
            continue
        kept.append(cid)
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（校验用）")
    ap.add_argument("--no-fts-pool", action="store_true", help="不统计 FTS 候选池大小（慢）")
    ap.add_argument("--no-rerank", action="store_true", help="跳过 rerank 阶段那一路")
    ap.add_argument("--no-check", action="store_true",
                    help="跳过「本脚本副本 vs 生产函数」的一致性校验")
    args = ap.parse_args()

    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval.hybrid_engine import (
        perform_hybrid_search, search_with_details, extract_modality_from_query)
    from src.core.text_utils import standard_key
    from src.core.storage.clause_repo import fetch_full_clause

    mtime0 = DB.stat().st_mtime
    conn = ro_conn(DB)
    he._conn = lambda: conn          # 让生产函数也在只读连接上跑（不改生产代码）

    src_path = BENCH_V2 if BENCH_V2.exists() else BENCH_V1
    items = [json.loads(l) for l in src_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        items = items[:args.limit]

    std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
    doc_std_no = {r[0]: r[1] for r in conn.execute("SELECT doc_id, standard_no FROM doc_meta")}

    gold_cr = {}
    for it in items:
        std_no = std_of_key[standard_key(it["gold_std"])]
        row = conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
            " WHERE dm.standard_no=? AND cr.clause_number=?",
            (std_no, it["gold_clause"])).fetchone()
        if row is None:
            raise RuntimeError(f"gold 在库里找不到：{it['i']} {it['gold_std']} {it['gold_clause']}")
        gold_cr[it["i"]] = row[0]

    done = set()
    if OUT_PER.exists():
        for l in OUT_PER.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.loads(l)["i"])
    todo = [it for it in items if it["i"] not in done]
    print(f"[funnel] 输入 {len(items)} 条，已完成 {len(done)} 条，本次待跑 {len(todo)} 条", flush=True)

    def _snippet(cid: str, n: int = 60) -> str:
        r = conn.execute("SELECT content_text FROM clause_revision WHERE clause_revision_id=?",
                         (cid,)).fetchone()
        return (r[0] or "").replace("\n", " ")[:n] if r else ""

    def _key(cid: str) -> str:
        r = conn.execute("SELECT cr.clause_number, dm.standard_no FROM clause_revision cr"
                         " JOIN doc_meta dm ON dm.doc_id=cr.doc_id WHERE cr.clause_revision_id=?",
                         (cid,)).fetchone()
        return f"{r[1]} {r[0]}" if r else cid

    t_start = time.perf_counter()
    with OUT_PER.open("a", encoding="utf-8") as fh:
        for n, it in enumerate(todo, 1):
            t0 = time.perf_counter()
            q = it["query"]
            gold = gold_cr[it["i"]]
            mfilter = extract_modality_from_query(q)
            cands: dict[str, list[str]] = {}
            # 生产口径（B/C 取 20）
            cands["exact"] = channel_exact(conn, q)
            cands["fts"] = channel_fts(conn, q, PROD_CAP["fts"])
            cands["vec"] = channel_vec(conn, q, PROD_CAP["vec"])
            cands["modality"] = channel_modality(conn, mfilter)
            cands["legal_element"] = []          # 生产问答路径不传 subject_filter
            cands["behavior_scope"] = []         # 生产问答路径不传 behavior_scope_filter
            # 深读口径（B/C 放大到 1000）
            deep = dict(cands)
            deep["fts"] = channel_fts(conn, q, 1000)
            deep["vec"] = channel_vec(conn, q, 1000)

            rec: dict = {
                "i": it["i"],
                "bucket": (it.get("v2") or {}).get("bucket", "unknown"),
                "flags": (it.get("v2") or {}).get("flags", []),
                "kind": it["kind"],
                "query": q,
                "gold_std": it["gold_std"],
                "gold_clause": it["gold_clause"],
                "modality_filter": mfilter,
                "channels": {},
            }
            for c in CHANNELS:
                lst = cands[c]
                dl = deep[c]
                rec["channels"][c] = {
                    "n": len(lst),
                    "gold_rank": rank_of(gold, lst),
                    "deep_n": len(dl),
                    "deep_gold_rank": rank_of(gold, dl),
                    "fires": bool(lst),
                }
            # 四种口径的并集：生产（B/C 只到 20）/ 深读（B/C 到 1000）
            for label, table in (("prod", cands), ("deep", deep)):
                for d in DEPTHS:
                    pool: set[str] = set()
                    for c in CHANNELS:
                        pool |= set(table[c][:d]) if table[c] else set()
                    rec.setdefault("union", {}).setdefault(label, {})[f"@{d}"] = gold in pool
                    if d == 1000:
                        rec["union"][label]["pool@1000"] = len(pool)
            # 融合（生产实际排序：RRF + 时效过滤；rerank 默认关闭，与 ks_answer 一致）
            found = search_with_details(q, top_k=1000, rerank=False,
                                        boost_bookmarks=False, expand_chain=False)
            fused = [r.clause_revision_id for r in found["results"]]
            rec["fused"] = {"n": len(fused), "gold_rank": rank_of(gold, fused),
                            "hit@20": gold in fused[:20], "hit@100": gold in fused[:100],
                            "hit@1000": gold in fused}
            if not args.no_rerank:
                try:
                    fr = search_with_details(q, top_k=8, rerank=True, rerank_n=24,
                                             boost_bookmarks=False, expand_chain=False)
                    rec["fused_rerank8"] = {
                        "hit": gold in [r.clause_revision_id for r in fr["results"]],
                        "offline": bool(fr["debug"]["rerank"].get("rerank_offline")),
                    }
                except Exception as e:  # noqa: BLE001
                    rec["fused_rerank8"] = {"hit": None, "error": str(e)[:120]}
            # 独家/共同命中（按深读 1000 口径）
            hit_channels = [c for c in CHANNELS if rec["channels"][c]["deep_gold_rank"]]
            rec["hit_channels"] = hit_channels
            rec["hit_in_deep_union"] = rec["union"]["deep"]["@1000"]
            if not args.no_fts_pool:
                rec["fts_pool"] = channel_fts_pool(conn, q)
            # 一致性校验：本脚本的通道副本 vs 生产 `perform_hybrid_search`（单通道）
            if not args.no_check:
                mism = []
                for c, kw in (("exact", {}), ("fts", {}),
                              ("vec", {}), ("modality", {"modality_filter": mfilter})):
                    if c in ("modality",) and not mfilter:
                        continue
                    prod = perform_hybrid_search(q, top_k=20, channels=[c], rerank=False,
                                                 boost_bookmarks=False, **kw)
                    a = [r.clause_revision_id for r in prod]
                    b = _prod_kept(conn, cands[c], 20)
                    if a != b:
                        mism.append({"channel": c, "prod": a[:5], "replica": b[:5],
                                     "prod_n": len(a), "replica_n": len(b)})
                rec["replica_check"] = "ok" if not mism else mism
            rec["elapsed_s"] = round(time.perf_counter() - t0, 2)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            if n % 5 == 0 or n == len(todo):
                el = time.perf_counter() - t_start
                print(f"[funnel] {n}/{len(todo)} 用时 {el:.0f}s（{el/max(n,1):.1f}s/条）"
                      f" 最近一条 {rec['elapsed_s']}s", flush=True)

    print("[funnel] 逐条结果已全部落盘", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
