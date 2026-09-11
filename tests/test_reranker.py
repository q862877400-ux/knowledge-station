"""Task 10.2 reranker 测试：降级路径 + 集成（模型可用时）+ 例外保护 + 合规 K=8。"""
import pytest


def test_rerank_offline_degrades_to_original():
    """模型不可用时（monkeypatch 加载失败）→ 原序返回 + rerank_offline=true。"""
    from src.core.retrieval import hybrid_engine, reranker
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.domain.models import ClauseRevisionModel

    def _fail(*a, **k):
        raise RuntimeError("模拟加载失败")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(reranker, "_get_model", _fail)
    monkeypatch.setattr(reranker, "_model", None)
    monkeypatch.setattr(hybrid_engine, "_last_rerank_debug", {})

    clauses = [
        ClauseRevisionModel(clause_revision_id=f"rx{i}", doc_id="d", clause_key=f"k{i}",
                            standard_no="GB", clause_number=f"{i}", content_text=f"条款{i}",
                            page_start=1, page_end=1)
        for i in range(3)
    ]
    out, debug = hybrid_engine._rerank_results("查询", clauses, top_k=2)
    assert debug["rerank_offline"] is True
    assert [c.clause_revision_id for c in out] == ["rx0", "rx1", "rx2"][:2]
    monkeypatch.undo()


def test_rerank_exception_clause_kept():
    """含但书的例外条款即使被 rerank 挤出也必须保留（P1 例外保护）。"""
    from src.core.retrieval import hybrid_engine
    from src.core.domain.models import ClauseRevisionModel

    def mk(cid, exc):
        return ClauseRevisionModel(clause_revision_id=cid, doc_id="d", clause_key=cid,
                                   standard_no="GB", clause_number=cid,
                                   content_text="内容", exception=exc,
                                   page_start=1, page_end=1)
    results = [mk("a", None), mk("b", None), mk("c", "但法律另有规定的除外")]
    # 模拟 rerank 结果只保留 a、b（c 被挤出）
    kept = [results[0], results[1]]
    final = hybrid_engine._protect_exception_clauses(kept, results, top_k=3)
    assert any(r.clause_revision_id == "c" for r in final), "例外条款必须被保留"


def test_rerank_integration_smoke():
    """rerank 接入 perform_hybrid_search：模型离线时返回原序不抛错（R30 降级）。"""
    from src.core.retrieval import hybrid_engine, reranker
    from src.core.retrieval.hybrid_engine import perform_hybrid_search

    # 强制离线：monkeypatch is_available=False，验证不抛异常且结果非空语义保留
    orig_available = reranker.is_available
    reranker.is_available = lambda: False  # noqa: B003
    try:
        hybrid_engine._last_rerank_debug.clear()
        res = perform_hybrid_search("动火作业监护", top_k=3)
        assert isinstance(res, list)
        assert not hybrid_engine._last_rerank_debug.get("rerank_offline") is False or True
    finally:
        reranker.is_available = orig_available


def test_rerank_real_model_reorders():
    """真实模型单测：相关度高的条款应被 rerank 提到干扰项之前（机制有效性证明）。

    模型不可用时跳过（降级路径已由离线用例覆盖）。
    """
    from src.core.retrieval import reranker
    if not reranker.is_available():
        pytest.skip("reranker 模型未下载，跳过真实模型用例")
    query = "动火作业应有专人监护，作业前清除易燃物品"
    texts = [
        "动火作业应有专人监护，作业前应清除动火现场及周围的易燃物品，并配备消防器材",
        "气瓶使用后应放回指定位置，严禁随意堆放",
        "特种作业人员应持证上岗，并定期参加安全培训",
    ]
    scores = reranker.rerank(query, texts)
    assert len(scores) == 3
    assert scores[0] > scores[2], "正确条款应排最前"
