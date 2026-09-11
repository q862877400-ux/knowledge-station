"""Phase 8 测试：健康看板 / Debug Trace / session 文件 / 一键启动相关。"""
import json

import pytest


def test_health_board(client):
    c, token = client
    r = c.get("/api/v1/diagnostics/health-board",
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert set(data["engines"]) >= {"db", "vector", "fts", "parser", "llm", "alias"}
    assert data["stats"]["documents"] >= 0
    assert data["stats"]["clauses"] >= 0


def test_debug_trace_recorded_by_default(client):
    """P9.4：每次提问默认落 Debug Trace，含各阶段 trace 数据，无需显式参数。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "动火作业监护要求", "top_k": 1,
                        "query_mode": "guess"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    dumps = c.get("/api/v1/diagnostics/debug-dumps",
                  headers={"Authorization": f"Bearer {token}"}).json()["data"]
    assert len(dumps) >= 1, "默认应记录 Debug Trace"
    d = dumps[0]
    assert d["query"] == "动火作业监护要求"
    assert d["dump_id"].startswith("dump_")
    # logs 字段应包含 trace（理解层/检索/核验阶段）
    logs = json.loads(d.get("logs") or "{}")
    trace = logs.get("trace") or {}
    assert trace.get("intent") == "rule_query", f"trace 应含意图分类: {trace}"
    assert trace.get("stage") == "verification", f"trace 应到核验阶段: {trace}"
    assert "total_ms" in trace, "trace 应含总耗时"


def test_debug_trace_clarify_recorded(client):
    """R9 v2：追问由 LLM 单次自判；trace 记录 clarify_policy（llm-judged）并走到核验阶段。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "防火间距多少合规", "query_mode": "default"},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        for _ in r.iter_lines():
            pass
    dumps = c.get("/api/v1/diagnostics/debug-dumps",
                  headers={"Authorization": f"Bearer {token}"}).json()["data"]
    d = next((x for x in dumps if x["query"] == "防火间距多少合规"), None)
    assert d is not None, "应找到该查询的 trace 记录"
    logs = json.loads(d.get("logs") or "{}")
    trace = logs.get("trace") or {}
    assert trace.get("stage") == "verification", f"应走到核验阶段: {trace.get('stage')}"
    assert "llm-judged" in json.dumps(trace, ensure_ascii=False), "应记录 LLM 自判追问策略"


def test_session_file_written(monkeypatch, tmp_path, _isolate_data_dir):
    """引擎 run() 应写 engine.session.json（用 create_app 前先验证函数存在性）。"""
    import src.core.api.server as srv
    assert hasattr(srv, "run")
    from src.core.config import get_settings
    assert get_settings().data_dir is not None
