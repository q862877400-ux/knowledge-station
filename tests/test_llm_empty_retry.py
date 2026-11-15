"""空返回自动重试 —— 判据（2026-10-19）。

## 为什么要有这份判据

真机实测：免费 router 车道偶发「流式正文恒空、finish_reason=stop、reasoning 正常」。
同一道题重跑即成功 ⇒ 上游抖动。原实现一次空就降级成「大模型不可用」占位。

修复给 `ks_answer.answer()` 加了空返回重试。这份判据钉住三条行为：

1. **第一次空、第二次有** ⇒ 必须用第二次的结果，且**不能**标 `llm_unavailable`。
2. **一直空** ⇒ 仍然诚实降级，且文案里说明重试过（用户能区分"抖了一下"与"彻底坏了"）。
3. **配置类错误（LLMError）** ⇒ **不重试**（Key 错重试一百次也一样，白等）。

第 3 条最容易被写错：如果重试循环把 `except LLMError` 也包进去，Key 错时会
白等 max_attempts 倍的时间。这条判据就是防那个。
"""
import pytest


EV = [{
    "clause_revision_id": "c1",
    "clause_number": "5.2.1",
    "standard_no": "GB 30871-2022",
    "knowledge_type": "rule",
    "modality": "应",
    "content_text": "动火作业应有专人监护。",
    "exception": None,
    "subject": None,
    "page_start": 11,
}]


def _patch_stream(monkeypatch, outputs):
    """把 `_stream_llm` 换成一串预设输出；记录被调用了几次。"""
    calls = {"n": 0}

    def fake(messages, max_tokens=None, temperature=0.1):
        i = calls["n"]
        calls["n"] += 1
        item = outputs[i] if i < len(outputs) else outputs[-1]
        if isinstance(item, Exception):
            raise item
        yield from [item]

    monkeypatch.setattr("src.core.llm.ks_answer._stream_llm", fake)
    return calls


def _patch_retrieve(monkeypatch):
    """检索固定返回一条证据，把 LLM 之外的因素全部钉死。"""
    from src.core.llm import ks_answer as ka

    monkeypatch.setattr(ka, "_resolve_kb_scope", lambda params: (None, None))
    monkeypatch.setattr(
        ka, "perform_hybrid_search",
        lambda *a, **k: [_FakeClause()], raising=False)


class _FakeClause:
    clause_revision_id = "c1"
    clause_number = "5.2.1"
    standard_no = "GB 30871-2022"
    title = None
    legal_status = "effective"
    legal_hierarchy = "GB"
    page_start = 11
    content_text = "动火作业应有专人监护。"
    knowledge_type = "rule"
    modality = "应"
    modality_strength = 3
    exception = None
    subject = None
    content_markdown = None
    table_summary = None
    formula_number = None
    formula_desc = None
    image_text = None
    hierarchy_path = None
    behavior_scope = None
    object = None
    behavior = None
    applicability_condition = None
    restriction = None
    cross_refs = None
    explanation_ref = None
    page_end = 11
    bbox = None
    effective_from = None


GOOD = '{"derivation":"动火作业应有专人监护[[c:0]]。","conclusion":"应有专人监护。"}'


def test_empty_then_good_retries_and_succeeds(monkeypatch):
    """第一次空、第二次有 ⇒ 用第二次结果，不标 llm_unavailable。"""
    from src.core.llm import ks_answer as ka

    _patch_retrieve(monkeypatch)
    calls = _patch_stream(monkeypatch, ["", GOOD])

    res = ka.answer("动火作业有什么要求")
    assert calls["n"] == 2, f"应重试一次，实际调用 {calls['n']} 次"
    assert "llm_unavailable" not in (res.get("verification", {}).get("citation_index_warnings") or []), (
        "第二次成功了，不该再标 llm_unavailable"
    )
    assert "大模型不可用" not in (res.get("derivation") or ""), (
        f"不该降级成占位文字，实际 derivation={res.get('derivation')!r}"
    )


def test_always_empty_degrades_honestly(monkeypatch):
    """一直空 ⇒ 诚实降级，且说明重试过。"""
    from src.core.llm import ks_answer as ka

    _patch_retrieve(monkeypatch)
    calls = _patch_stream(monkeypatch, ["", ""])

    res = ka.answer("动火作业有什么要求")
    assert calls["n"] == 2, f"默认重试 1 次 ⇒ 共 2 次，实际 {calls['n']}"
    der = res.get("derivation") or ""
    assert "大模型不可用" in der, f"必须诚实降级，实际 {der!r}"
    assert "已重试" in der, f"要能区分'重试过还是空'与'一次就空'，实际 {der!r}"
    assert "llm_unavailable" in (res.get("verification", {}).get("citation_index_warnings") or [])


def test_llm_error_not_retried(monkeypatch):
    """配置类错误不重试 —— 否则 Key 错时会白等 max_attempts 倍。"""
    from src.core.llm import ks_answer as ka
    from src.core.exceptions import LLMError

    _patch_retrieve(monkeypatch)
    calls = _patch_stream(monkeypatch, [LLMError("DEEPSEEK_API_KEY 未配置")])

    res = ka.answer("动火作业有什么要求")
    assert calls["n"] == 1, f"LLMError 不许重试，实际调用 {calls['n']} 次"
    assert "大模型不可用" in (res.get("derivation") or "")
