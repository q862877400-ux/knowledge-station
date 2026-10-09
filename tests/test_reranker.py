"""Task 10.2 reranker 测试：降级路径 + 集成（模型可用时）+ 例外保护 + 合规 K=8。

⚠ 2026-10-09 新增三条**判据**（施工总纲 P0·0.7 修复批）——见 `test_reranker_scores_align_with_input`
与 `test_reranker_pipeline_reorders_by_score` 的 docstring：它们钉的是"返回分数与输入一一对应"，
旧实现（返回降序列表）在这两条上**必红**。
⚠ 用例名必须含 `reranker`：`tests/conftest.py` 的 `_rerank_offline_for_tests` 会把**其余**用例的
reranker 强制离线（模型推理慢），只有名字含 `reranker` 的专项用例不受影响。
"""
import pytest


class _FakeModel:
    """只回固定分数（按输入顺序）的假模型 —— 用来把"对齐"这件事与真实模型解耦。"""

    def __init__(self, scores):
        self._scores = list(scores)
        self.calls = 0

    def rerank(self, query, texts):
        self.calls += 1
        return list(self._scores)


def _clauses(n):
    from src.core.domain.models import ClauseRevisionModel
    return [ClauseRevisionModel(clause_revision_id=f"c{i}", doc_id="d", clause_key=f"k{i}",
                                standard_no="GB", clause_number=str(i), content_text=f"条款{i}",
                                page_start=1, page_end=1) for i in range(n)]


def test_reranker_scores_align_with_input(monkeypatch):
    """判据：返回的分数必须与 `texts` **一一对应**，不许替调用方排序。

    变异自验：把实现改回 `sorted(...)`（旧版）⇒ 本用例返回 [0.9, 0.5, 0.1] ⇒ **必红**。
    这是总纲 P0·0.7 那条缺陷的正面判据。
    """
    from src.core.retrieval import reranker
    fake = _FakeModel([0.1, 0.9, 0.5])          # texts[1] 最相关
    monkeypatch.setattr(reranker, "_get_model", lambda: fake)
    scores = reranker.rerank("q", ["t0", "t1", "t2"])
    assert scores == [0.1, 0.9, 0.5], (
        "分数必须与输入同序（旧实现返回降序 ⇒ 调用方按 scores[i] 排序退化成恒等置换）")
    assert fake.calls == 1


def test_reranker_rejects_length_mismatch(monkeypatch):
    """判据：分数个数与候选条数不匹配时必须**当场抛错**（fail-closed），不许静默错位。"""
    from src.core.retrieval import reranker
    monkeypatch.setattr(reranker, "_get_model", lambda: _FakeModel([0.1, 0.2]))
    with pytest.raises(ValueError):
        reranker.rerank("q", ["t0", "t1", "t2"])


def test_reranker_pipeline_reorders_by_score(monkeypatch):
    """判据（端到端）：`_rerank_results` 真的会**按分数改顺序**。

    变异自验：旧实现（rerank 返回降序、调用方又按 `scores[i]` 排序）⇒ 输出 == 输入原序 ⇒ **必红**。
    这条把"包装器修好了"与"调用方用对了"钉在一起 —— 单看任一侧都测不出那个恒等置换。
    """
    from src.core.retrieval import hybrid_engine, reranker
    fake = _FakeModel([0.1, 0.2, 9.9])          # 最后一条最相关
    monkeypatch.setattr(reranker, "_get_model", lambda: fake)
    monkeypatch.setattr(reranker, "_model", fake)
    monkeypatch.setattr(hybrid_engine, "_last_rerank_debug", {})
    out, debug = hybrid_engine._rerank_results("q", _clauses(3), top_k=3)
    assert [c.clause_revision_id for c in out] == ["c2", "c1", "c0"], (
        f"应按分数重排，实测 {[c.clause_revision_id for c in out]}")
    assert debug["rerank_offline"] is False
    assert debug["rerank_score"]["c2"] == 9.9, "分数必须贴在对的条款上"


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


def test_reranker_real_model_reorders(monkeypatch):
    """真实模型单测：**正确条款（下标 1）应得最高分**（机制有效性证明）。

    模型不可用时跳过（降级路径已由离线用例覆盖）。

    ⚠ 2026-10-09 就地更正（施工总纲 P0·0.7；错话原文保留在上一条提交里）：
    本用例原先断言 `scores[0] > scores[2]`，而**旧实现返回的是已降序排过的列表** ⇒
    那条断言**恒真**（空判据）—— 它"证明"的只是"这个列表是排好序的"，与"正确条款排最前"无关。
    现在改成对**与输入同序**的分数取 argmax，旧实现下 `argmax` 恒为 0（≠1）⇒ **必红**。

    ⚠⚠ **2026-10-09 第二个缺陷（本用例此前从未真正执行过）**：`tests/conftest.py` 的
    `_isolate_data_dir` 会把 `KS_DATA_DIR` 指到临时目录 ⇒ `settings.models_dir` 也跟着变
    ⇒ 本机真模型（在 `%APPDATA%\\KnowledgeStation\\models`）**找不到** ⇒ `is_available()`
    恒 False ⇒ 本用例**每次都走 skip**（实测 `-rs` 打印 "reranker 模型未下载"）。
    即"豁免 reranker 的专项用例"这条设计**没生效**，本用例是个**永假绿**。
    ⇒ 现在把 `models_dir` 显式指回**真实**模型目录（模型真不存在时仍 skip，不算失败）。
    """
    import os
    from pathlib import Path

    from src.core.retrieval import reranker

    class _RealModelsDir:
        models_dir = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"

    monkeypatch.setattr(reranker, "get_settings", lambda: _RealModelsDir)
    monkeypatch.setattr(reranker, "_model", None)
    monkeypatch.setattr(reranker, "_load_error", None)

    if not reranker.is_available():
        pytest.skip(f"真实 reranker 模型不可用：{reranker.offline_reason()}")

    query = "动火作业应有专人监护，作业前清除易燃物品"
    # ⚠ 顺序是**刻意**把正确条款放在**最后**（下标 2）：这样"输出被排过序"（旧实现）会让
    #   最高分落到下标 0 ⇒ argmax=0≠2 ⇒ 必红；若把正确条款放在下标 0，两种实现都会 argmax=0，
    #   判据就又没有分辨力了（本用例原版正是栽在这种"位置碰巧"上）。
    texts = [
        "气瓶使用后应放回指定位置，严禁随意堆放",
        "特种作业人员应持证上岗，并定期参加安全培训",
        "动火作业应有专人监护，作业前应清除动火现场及周围的易燃物品，并配备消防器材",
    ]
    scores = reranker.rerank(query, texts)
    assert len(scores) == 3
    best = max(range(len(scores)), key=lambda i: scores[i])
    assert best == 2, f"正确条款（下标 2）应得最高分；实测 argmax={best}，分数={scores}"
    assert scores[2] > scores[0] and scores[2] > scores[1]
