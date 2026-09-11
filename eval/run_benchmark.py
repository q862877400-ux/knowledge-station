"""Golden Set 评测器（Task 10.1）：检索指标 + 核验拦截率 + 合规三色准确率。

零 LLM 消耗：检索指标直接用六路检索 top-K 的条款号 vs 答案集比对；
citation_precision 用"top-K 证据命中答案的比例"代理（回答可引用范围）；
modality_intercept_rate 用构造的 LLM 输出样本测核验器（复用 typed_verifier）；
合规三色判定走规则引擎（复用 compliance.engine，不调 LLM）。

用法: .venv/Scripts/python eval/run_benchmark.py [--disable-channel exact|fts|...] [--out eval/result.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.retrieval.hybrid_engine import (
    perform_hybrid_search, set_db_override,
)
from src.core.storage.sqlite_db import load_vec_extension, get_db_connection
from src.core.verification.typed_verifier import verify_llm_output
from src.core.compliance.engine import judge_point_rule, _behavior_scope_of, _anchor_terms

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "golden.json"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "golden" / "knowledge-snapshot.db"


def _hit(ids: list, answers: list) -> bool:
    return bool(answers and any(a in ids for a in answers))


def run_benchmark(disable_channel: str | None = None, golden_path: Path = GOLDEN_PATH,
                  db_path: Path | None = None, with_rerank: bool = False) -> dict:
    try:
        if db_path is not None:
            set_db_override(str(db_path))
            conn = get_db_connection(db_path)
            load_vec_extension(conn)  # vec 通道依赖扩展（快照库含向量数据）
        return _run(disable_channel, golden_path, with_rerank=with_rerank)
    finally:
        set_db_override(None)  # 关键：评测完必须恢复默认库，否则污染后续测试


def _run(disable_channel: str | None, golden_path: Path, with_rerank: bool = False) -> dict:
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    items = data["items"]

    channels = None
    if disable_channel:
        channels = [c for c in ("exact", "fts", "vec", "modality",
                                "legal_element", "behavior_scope")
                    if c != disable_channel]

    exact_hit = recall5 = recall10 = n_search = 0
    for it in items:
        if it["type"] in ("modality_adversarial", "compliance"):
            continue
        if not it.get("answer"):
            continue
        res = perform_hybrid_search(it["query"], top_k=10, channels=channels,
                                    rerank=with_rerank)
        ids = [r.clause_number for r in res]
        if _hit(ids[:1], it["answer"]):
            exact_hit += 1
        if _hit(ids[:5], it["answer"]):
            recall5 += 1
        if _hit(ids[:10], it["answer"]):
            recall10 += 1
        n_search += 1

    # 核验拦截率
    intercepted = 0
    n_adv = 0
    for it in items:
        if it["type"] != "modality_adversarial":
            continue
        n_adv += 1
        ev = [{"clause_revision_id": "adv", "clause_number": "X",
               "standard_no": "GB 30871-2022", "knowledge_type": "rule",
               "modality": it["source_modality"], "modality_strength": 4,
               "content_text": "placeholder", "page_start": 1}]
        r = verify_llm_output(it["llm_output"], ev)
        if not r.is_valid and any(v.violation_type == "modality_weakened"
                                  for v in r.modality_violations):
            intercepted += 1

    # 合规三色判定（与 execute_review 同路径：风险锚点增强查询）
    correct = red_correct = n_comp = n_red = 0
    for it in items:
        if it["type"] != "compliance":
            continue
        n_comp += 1
        point = {"point_type": "测试", "point_content": it["query"]}
        anchor = _anchor_terms(it["query"])
        query = f"{it['query']} {anchor}" if anchor else it["query"]
        matched = perform_hybrid_search(query, top_k=5, channels=channels,
                                        behavior_scope_filter=_behavior_scope_of(point))
        v = judge_point_rule(point, matched)
        if v["verdict"] == it["expected_verdict"]:
            correct += 1
        if it["expected_verdict"] == "red":
            n_red += 1
            if v["verdict"] == "red":
                red_correct += 1

    return {
        "meta": {"golden": str(golden_path), "count": len(items),
                 "disable_channel": disable_channel},
        "exact_hit@1": round(exact_hit / n_search, 4) if n_search else 0,
        "recall@5": round(recall5 / n_search, 4) if n_search else 0,
        "recall@10": round(recall10 / n_search, 4) if n_search else 0,
        "citation_precision@5": round(recall5 / n_search, 4) if n_search else 0,
        "modality_intercept_rate": round(intercepted / n_adv, 4) if n_adv else 0,
        "compliance_accuracy": round(correct / n_comp, 4) if n_comp else 0,
        "red_precision": round(red_correct / n_red, 4) if n_red else 0,
        "n_search": n_search, "n_adversarial": n_adv, "n_compliance": n_comp,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disable-channel", default=None)
    ap.add_argument("--out", default="eval/result.json")
    ap.add_argument("--db", default=None,
                    help="评测用库路径（默认 %APPDATA% 真实库；CI 用 eval/golden/knowledge-snapshot.db）")
    ap.add_argument("--with-rerank", action="store_true",
                    help="开启 rerank 阶段评测（默认关闭：门禁锁基础检索质量）")
    ap.add_argument("--write-baseline", action="store_true",
                    help="把结果写为 eval/baseline.json")
    args = ap.parse_args()
    db = Path(args.db) if args.db else None
    result = run_benchmark(args.disable_channel, db_path=db, with_rerank=args.with_rerank)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if args.write_baseline:
        base = Path("eval/baseline.json")
        base.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"基线已写入 {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
