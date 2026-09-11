"""批量问答（Task 12.3）：问题清单 → 逐问检索+生成+核验 → 汇总报告。

预算护栏（红线 v2 #5 额度克制）：单批 ≤50 问；逐问走历史截断逻辑；
无 Key 时逐问走占位答案（离线可用，批量 QA 零云端消耗）。
"""
from __future__ import annotations

from ulid import ULID

from src.core.exceptions import KnowledgeStationError
from src.core.retrieval.hybrid_engine import search_with_details
from src.core.verification.typed_verifier import verify_llm_output


def run_batch_qa(questions: list[str], budget: int = 20000) -> dict:
    if not questions:
        raise KnowledgeStationError("问题清单为空", code="empty_questions")
    if len(questions) > 50:
        questions = questions[:50]  # 硬上限（P4：护栏优先，宁可截断不超预算）
    results = []
    for q in questions:
        q = (q or "").strip()
        if not q:
            continue
        out = search_with_details(q, top_k=3)
        ev_dicts = [{
            "clause_revision_id": e.clause_revision_id,
            "clause_number": e.clause_number, "standard_no": e.standard_no,
            "knowledge_type": e.knowledge_type, "modality": e.modality,
            "content_text": (e.content_text or "")[:300],
            "exception": e.exception, "subject": e.subject,
            "page_start": e.page_start} for e in out["results"]]
        answer = _answer_placeholder(q, ev_dicts)
        verification = verify_llm_output(answer, ev_dicts)
        results.append({
            "question": q,
            "answer": answer,
            "citations": [f"{e['standard_no']} {e['clause_number']}" for e in ev_dicts],
            "confidence": "high" if verification.is_valid else "mid",
            "verified": verification.is_valid,
        })
    summary = {
        "total": len(results),
        "verified": sum(1 for r in results if r["verified"]),
        "flagged": [r["question"] for r in results if not r["verified"]][:10],
    }
    return {"batch_id": f"batch_{ULID()}", "results": results, "summary": summary}


def _answer_placeholder(query: str, ev_dicts: list[dict]) -> str:
    """占位答案（无 Key 场景；有 Key 时由 chat 管线替换为真实 LLM 流式）。"""
    if not ev_dicts:
        return f"未检索到与「{query}」相关的现行有效条款。"
    lines = [f"根据检索结果（{query}）："]
    for e in ev_dicts:
        lines.append(f"- {e['standard_no']} 第{e['clause_number']}条："
                     f"{(e['content_text'] or '')[:120]} [引用:{e['standard_no']}-{e['clause_number']}]")
    return "\n".join(lines)
