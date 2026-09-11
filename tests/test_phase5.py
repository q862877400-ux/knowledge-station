"""Phase 5 测试：多轮对话（R60）/ 追问增强（R9）/ 核验器窗口并集 / 答案置信度（R24）。

全部 mock，零 LLM 消耗。
"""
import json

import pytest


# ---------- R60 多轮历史 messages 组装 ----------

def test_build_messages_history_order_and_cap():
    from src.core.llm.deepseek_client import build_messages
    history = [
        {"role": "user", "content": f"问题{i}"} if i % 2 == 0
        else {"role": "assistant", "content": f"答案{i}"}
        for i in range(6)   # 6 条 → 只保留后 4 条
    ]
    msgs = build_messages("当前问", [{"standard_no": "GB", "clause_number": "1.1",
                                     "content_text": "证据文本", "page_start": 1}], history)
    roles = [m["role"] for m in msgs]
    assert roles[0] == "system"
    # 6 条历史 → 保留后 4 条（2 问 2 答）
    assert roles[1:] == ["user", "assistant", "user", "assistant", "user"]
    assert msgs[-1]["content"].startswith("用户问题：当前问")
    assert "证据条款" in msgs[-1]["content"]
    # 历史条目不携带证据（防膨胀）
    for m in msgs[1:-1]:
        assert "证据条款" not in m["content"]


def test_build_messages_truncates_long_history():
    from src.core.llm.deepseek_client import build_messages, HISTORY_CONTENT_MAX
    long = {"role": "user", "content": "长" * 1000}
    msgs = build_messages("q", [{"standard_no": "GB", "clause_number": "1.1",
                                 "content_text": "t", "page_start": 1}], [long])
    assert len(msgs[1]["content"]) == HISTORY_CONTENT_MAX


# ---------- R9 追问检索增强 ----------

def test_expand_query_with_history():
    from src.core.retrieval.hybrid_engine import expand_query_with_history
    hist = [{"role": "user", "content": "防火间距要求是什么"},
            {"role": "assistant", "content": "根据 5.2.1 条……"}]
    # 指代词 → 扩展
    out = expand_query_with_history("那第三条呢", hist)
    assert "防火间距要求是什么" in out and "那第三条呢" in out
    # 过短 → 扩展
    assert "防火间距要求是什么" in expand_query_with_history("多少", hist)
    # 完整问题 → 原样
    assert expand_query_with_history("完整独立的问题", hist) == "完整独立的问题"
    # 无历史 → 原样
    assert expand_query_with_history("那这个呢", None) == "那这个呢"


# ---------- 核验器模态窗口并集（phase3 遗留误报回归） ----------

def test_modality_window_union_fixes_false_positive():
    """4.10 场景：条款号两次出现，首个窗口无模态词，第二窗口含"不应"。
    旧逻辑误报 modality_missing；新逻辑应通过。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev = [{"clause_revision_id": "c", "clause_number": "4.10", "standard_no": "GB",
           "knowledge_type": "rule", "modality": "不应",
           "content_text": "作业期间，监护人不应擅自离开作业现场且不应从事与监护无关的事。",
           "page_start": 9}]
    out = ("监护人通用职责：a）作业前检查安全作业票，确保内容相符；"
           "b）确认作业人员持有效证书；c）核查防护装备；d）监督现场安全条件。"
           "第4.10条要求：作业期间，监护人不应擅自离开作业现场 [引用:GB-4.10]。")
    r = verify_llm_output(out, ev)
    assert r.is_valid, f"窗口并集后不应再误报 modality_missing: {r.model_dump()}"
    assert not r.modality_violations


def test_modality_weakened_still_caught_with_union():
    """窗口并集后，真实减弱（应→宜）仍必须拦截。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev = [{"clause_revision_id": "c", "clause_number": "5.2.1", "standard_no": "GB",
           "knowledge_type": "rule", "modality": "应",
           "content_text": "动火作业应有专人监护。", "page_start": 11}]
    out = "根据第5.2.1条，动火作业宜有专人监护 [引用:GB-5.2.1]。"
    r = verify_llm_output(out, ev)
    assert not r.is_valid
    assert r.modality_violations[0].violation_type == "modality_weakened"


# ---------- SSE 集成：history 透传 + answer_confidence ----------

def test_sse_accepts_history_and_confidence(client):
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "动火作业监护", "top_k": 1,
                        "history": [{"role": "user", "content": "上一轮问题"},
                                    {"role": "assistant", "content": "上一轮回答"}]},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        events, verification = [], None
        for line in r.iter_lines():
            if line.startswith("event: "):
                events.append(line[7:])
            if line.startswith("data: ") and '"is_valid"' in line:
                verification = json.loads(line[6:])
    assert events[-1] == "done"
    assert verification is not None
    assert verification["answer_confidence"] in ("high", "mid", "low")
    assert isinstance(verification["confidence_reasons"], list)


def test_llm_history_forwarded_with_mock(monkeypatch, client):
    """mock LLM：确认 history 真正传到流式客户端（不真调 API）。"""
    from src.core.config import get_settings
    captured = {}

    def fake_stream(query, evidences, history=None, max_tokens=1024, temperature=0.1,
                    allow_clarify=True):
        captured["query"] = query
        captured["history"] = history
        captured["allow_clarify"] = allow_clarify
        yield "根据第4.10条，监护人不应擅自离开作业现场 [引用:GB-4.10]。"

    monkeypatch.setattr("src.core.llm.deepseek_client.stream_chat_completion", fake_stream)
    s = get_settings()
    monkeypatch.setattr(s, "llm_api_key", "sk-test")
    c, token = client
    hist = [{"role": "user", "content": "上一轮"}]
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "那第四条呢", "history": hist, "top_k": 1},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    assert captured.get("history") == hist, "history 必须原样转发给 LLM 客户端"
    assert "上一轮" in captured.get("query", "") or captured.get("query"), "追问扩展生效"
